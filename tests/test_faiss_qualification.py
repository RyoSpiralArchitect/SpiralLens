from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

if importlib.util.find_spec("faiss") is None:
    pytest.skip("faiss optional dependency is absent", allow_module_level=True)

from spirallens.execution_freeze import (  # noqa: E402
    current_worker_runtime_contract,
)
from spirallens.neighbors import canonical_json_sha256  # noqa: E402
from spirallens.neighbors import NeighborQuery  # noqa: E402
from spirallens.neighbors.faiss_hnsw import (  # noqa: E402
    FAISS_HNSW_BACKEND_ID,
    FAISS_HNSW_RANGE_CALL_BACKEND_VERSION,
    FaissHNSWBackend,
    FaissHNSWConfig,
)
from spirallens.neighbors import faiss_qualification as qualification  # noqa: E402
from spirallens.neighbors.faiss_qualification import (  # noqa: E402
    QUALIFICATION_COLD_RUNS,
    QUALIFICATION_FIXTURE_SCHEMA_VERSION,
    QUALIFICATION_HIDDEN_SIZE,
    QUALIFICATION_ROW_COUNT,
    QUALIFICATION_SCHEMA_VERSION,
    FaissHNSWQualificationReceipt,
    load_faiss_hnsw_qualification_receipt,
    run_faiss_hnsw_qualification,
)


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _source() -> dict[str, str]:
    return {
        "repository": (
            "https://github.com/RyoSpiralArchitect/SpiralLens.git"
        ),
        "branch": "SpiralReality/pythia70-subject-audit-v03",
        "implementation_commit": "a" * 40,
        "spirallens_package_tree": "b" * 40,
    }


def _fixture() -> dict[str, object]:
    return {
        "schema_version": QUALIFICATION_FIXTURE_SCHEMA_VERSION,
        "generator": (
            "numpy.pcg64.standard_normal.float32.cluster-repeat"
        ),
        "seed": 1729,
        "row_count": qualification.QUALIFICATION_ROW_COUNT,
        "hidden_size": qualification.QUALIFICATION_HIDDEN_SIZE,
        "cluster_size": qualification.QUALIFICATION_CLUSTER_SIZE,
        "query_count": qualification.QUALIFICATION_QUERY_COUNT,
        "states_sha256": "1" * 64,
        "normalized_states_sha256": "2" * 64,
        "query_indices_sha256": "3" * 64,
    }


def _result(*, index_sha256: str = "4" * 64) -> dict[str, object]:
    return {
        "index_sha256": index_sha256,
        "limits_sha256": "5" * 64,
        "scores_sha256": "6" * 64,
        "labels_sha256": "7" * 64,
        "raw_hit_count": qualification.QUALIFICATION_QUERY_COUNT,
        "limits_length": qualification.QUALIFICATION_QUERY_COUNT + 1,
    }


def _receipt_payload(
    runtime: dict[str, str],
    *,
    fixture: dict[str, object] | None = None,
    results: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    fixture_payload = _fixture() if fixture is None else fixture
    cold_runs = (
        [_result() for _ in range(QUALIFICATION_COLD_RUNS)]
        if results is None
        else results
    )
    return {
        "schema_version": QUALIFICATION_SCHEMA_VERSION,
        "status": "pass",
        "backend": {
            "backend_id": FAISS_HNSW_BACKEND_ID,
            "backend_version": FAISS_HNSW_RANGE_CALL_BACKEND_VERSION,
        },
        "source": _source(),
        "fixture": fixture_payload,
        "fixture_sha256": canonical_json_sha256(fixture_payload),
        "search": qualification._expected_search(),
        "runtime": runtime,
        "cold_runs": cold_runs,
    }


def _fake_worker(
    *,
    change_second_run: bool = False,
):
    calls = 0

    def run(arguments, *, runtime_contract):
        nonlocal calls
        calls += 1
        output_index = arguments.index("--output") + 1
        output = Path(arguments[output_index])
        index_sha256 = (
            "8" * 64
            if change_second_run and calls == 2
            else "4" * 64
        )
        payload = {
            "fixture": _fixture(),
            "search": qualification._expected_search(),
            "runtime": dict(runtime_contract),
            "result": _result(index_sha256=index_sha256),
        }
        output.write_bytes(_canonical_bytes(payload))

    return run


def _patch_fixture_regeneration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        qualification,
        "_regenerated_fixture_digests",
        lambda: {
            "states_sha256": "1" * 64,
            "normalized_states_sha256": "2" * 64,
            "query_indices_sha256": "3" * 64,
        },
    )


def _patch_source_capture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        qualification,
        "_pushed_source_contract",
        lambda *args, **kwargs: _source(),
    )


def test_qualification_run_is_exclusive_canonical_and_reloadable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fixture_regeneration(monkeypatch)
    _patch_source_capture(monkeypatch)
    monkeypatch.setattr(
        qualification,
        "_run_worker",
        _fake_worker(),
    )
    output = tmp_path / "qualification.json"

    receipt = run_faiss_hnsw_qualification(output)

    assert output.read_bytes() == receipt.canonical_bytes
    assert receipt.status == "pass"
    assert receipt.backend_id == FAISS_HNSW_BACKEND_ID
    assert (
        receipt.backend_version
        == FAISS_HNSW_RANGE_CALL_BACKEND_VERSION
    )
    assert receipt.search["range_call_batch_size"] == 1
    assert len(receipt.cold_process_runs) == QUALIFICATION_COLD_RUNS
    assert receipt.search_sha256 == canonical_json_sha256(receipt.search)
    assert load_faiss_hnsw_qualification_receipt(
        output,
        receipt.sha256,
    ) == receipt


def test_qualification_source_change_leaves_terminal_reservation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fixture_regeneration(monkeypatch)
    monkeypatch.setattr(
        qualification,
        "_run_worker",
        _fake_worker(),
    )
    captures = 0

    def changing_source(*args, **kwargs):
        nonlocal captures
        del args, kwargs
        captures += 1
        source = _source()
        if captures == 2:
            source["branch"] = "changed-after-workers"
        return source

    monkeypatch.setattr(
        qualification,
        "_pushed_source_contract",
        changing_source,
    )
    output = tmp_path / "qualification.json"

    with pytest.raises(ValueError, match="source changed"):
        run_faiss_hnsw_qualification(output)

    assert output.read_bytes().startswith(
        b"spirallens-faiss-hnsw-qualification-reservation"
    )


def test_qualification_receipt_requires_git_source_identity() -> None:
    payload = _receipt_payload(current_worker_runtime_contract(None))
    payload.pop("source")

    with pytest.raises(ValueError, match="receipt fields"):
        FaissHNSWQualificationReceipt.from_payload(payload)


def test_qualification_receipt_validates_backend_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fixture_regeneration(monkeypatch)
    _patch_source_capture(monkeypatch)
    runtime = current_worker_runtime_contract(None)
    receipt = FaissHNSWQualificationReceipt.from_payload(
        _receipt_payload(runtime)
    )
    config = FaissHNSWConfig(
        m=32,
        ef_construction=200,
        ef_search=256,
        seed=1729,
        thread_count=1,
        query_batch_size=512,
        range_call_batch_size=1,
        score_margin=0.0001,
        max_raw_hits=20_000_000,
    )

    receipt.validate_for_backend(
        config=config,
        row_count=QUALIFICATION_ROW_COUNT,
        hidden_size=QUALIFICATION_HIDDEN_SIZE,
        runtime_contract=runtime,
    )
    receipt.validate_search_radius(
        cosine_min=0.995,
        score_margin=0.0001,
        radius=qualification._qualification_radius(),
    )

    with pytest.raises(ValueError, match="qualification receipt"):
        receipt.validate_for_backend(
            config=config,
            row_count=QUALIFICATION_ROW_COUNT - 1,
            hidden_size=QUALIFICATION_HIDDEN_SIZE,
            runtime_contract=runtime,
        )


def test_persisted_qualification_is_consumed_by_v02_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(qualification, "QUALIFICATION_ROW_COUNT", 5)
    monkeypatch.setattr(qualification, "QUALIFICATION_HIDDEN_SIZE", 3)
    monkeypatch.setattr(qualification, "QUALIFICATION_CLUSTER_SIZE", 1)
    monkeypatch.setattr(qualification, "QUALIFICATION_QUERY_COUNT", 2)
    monkeypatch.setattr(
        qualification,
        "QUALIFICATION_MAX_NATIVE_CALL_HITS",
        5,
    )
    _patch_fixture_regeneration(monkeypatch)
    _patch_source_capture(monkeypatch)
    monkeypatch.setattr(
        qualification,
        "_run_worker",
        _fake_worker(),
    )
    output = tmp_path / "qualification.json"
    generated = run_faiss_hnsw_qualification(output)
    loaded = load_faiss_hnsw_qualification_receipt(
        output,
        generated.sha256,
    )
    states = np.array(
        [
            [1.0, 0.0, 0.0],
            [1.0, 0.001, 0.0],
            [1.0, -0.001, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    backend = FaissHNSWBackend(
        states,
        row_identity_sha256=hashlib.sha256(
            b"qualified-row-identity"
        ).hexdigest(),
        comparison_group="layer_index=0",
        config=FaissHNSWConfig(
            m=32,
            ef_construction=200,
            ef_search=256,
            seed=1729,
            thread_count=1,
            query_batch_size=2,
            range_call_batch_size=1,
            score_margin=0.0001,
            max_raw_hits=20_000_000,
            max_proposed_pairs=10_000_000,
        ),
        qualification_receipt=loaded,
    )

    parameters = dict(backend.descriptor.parameters)
    assert backend.descriptor.backend_version == "0.2"
    assert (
        parameters["qualification_receipt_sha256"]
        == generated.sha256
    )
    assert parameters["qualification_fixture_sha256"] == (
        generated.fixture_sha256
    )
    pairs = tuple(
        backend.iter_pairs(
            states,
            query=NeighborQuery(
                cosine_min=0.995,
                relative_norm_gap_max=0.05,
                min_state_norm=1e-8,
                epsilon=1e-12,
            ),
        )
    )
    assert pairs


def test_loader_rejects_runtime_drift_before_fixture_use(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fixture_should_not_run() -> dict[str, str]:
        raise AssertionError("fixture regeneration ran after runtime drift")

    monkeypatch.setattr(
        qualification,
        "_regenerated_fixture_digests",
        fixture_should_not_run,
    )
    runtime = current_worker_runtime_contract(None)
    runtime["numpy_version"] = "forged"
    source = _canonical_bytes(_receipt_payload(runtime))
    path = tmp_path / "forged-runtime.json"
    path.write_bytes(source)

    with pytest.raises(ValueError, match="runtime differs"):
        load_faiss_hnsw_qualification_receipt(
            path,
            hashlib.sha256(source).hexdigest(),
        )


def test_loader_regenerates_and_rejects_fixture_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fixture_regeneration(monkeypatch)
    _patch_source_capture(monkeypatch)
    fixture = _fixture()
    fixture["states_sha256"] = "9" * 64
    source = _canonical_bytes(
        _receipt_payload(
            current_worker_runtime_contract(None),
            fixture=fixture,
        )
    )
    path = tmp_path / "forged-fixture.json"
    path.write_bytes(source)

    with pytest.raises(ValueError, match="differs from regeneration"):
        load_faiss_hnsw_qualification_receipt(
            path,
            hashlib.sha256(source).hexdigest(),
        )


def test_qualification_cold_run_mismatch_leaves_terminal_reservation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fixture_regeneration(monkeypatch)
    _patch_source_capture(monkeypatch)
    monkeypatch.setattr(
        qualification,
        "_run_worker",
        _fake_worker(change_second_run=True),
    )
    output = tmp_path / "qualification.json"

    with pytest.raises(ValueError, match="cold subprocesses differ"):
        run_faiss_hnsw_qualification(output)

    assert output.read_bytes().startswith(
        b"spirallens-faiss-hnsw-qualification-reservation"
    )
    with pytest.raises(FileExistsError):
        run_faiss_hnsw_qualification(output)


def test_loader_rejects_wrong_digest(
    tmp_path: Path,
) -> None:
    path = tmp_path / "receipt.json"
    path.write_text('{"status": "pass"}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="differs from its expected"):
        load_faiss_hnsw_qualification_receipt(path, "0" * 64)


def test_loader_rejects_symlink_receipt(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target.json"
    target.write_bytes(b"{}")
    linked = tmp_path / "linked.json"
    linked.symlink_to(target)

    with pytest.raises(ValueError, match="must not contain symlinks"):
        load_faiss_hnsw_qualification_receipt(
            linked,
            hashlib.sha256(b"{}").hexdigest(),
        )
