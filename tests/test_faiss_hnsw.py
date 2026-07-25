from __future__ import annotations

import hashlib
import importlib.util
import json
from types import SimpleNamespace

import numpy as np
import pytest

if importlib.util.find_spec("faiss") is None:
    pytest.skip("faiss optional dependency is absent", allow_module_level=True)

from spirallens.metrics import (  # noqa: E402
    CandidateSearchConfig,
    NeighborAuditConfig,
    NeighborAuditProtocolBinding,
    audit_neighbor_backend,
)
from spirallens.execution_freeze import (  # noqa: E402
    current_worker_runtime_contract,
)
from spirallens.neighbors._faiss_worker import (  # noqa: E402
    _range_search_in_calls,
)
from spirallens.neighbors import (  # noqa: E402
    FaissHNSWBackend,
    FaissHNSWConfig,
    NeighborQuery,
    canonical_json_sha256,
    validate_prepared_backend,
)
from spirallens.neighbors.faiss_hnsw import (  # noqa: E402
    FAISS_HNSW_RANGE_CALL_BACKEND_VERSION,
)
from spirallens.neighbors import faiss_hnsw as faiss_hnsw_module  # noqa: E402


def _row_identity() -> str:
    return hashlib.sha256(b"faiss-test-row-identity").hexdigest()


def _config(**overrides) -> FaissHNSWConfig:
    values = {
        "m": 4,
        "ef_construction": 40,
        "ef_search": 40,
        "query_batch_size": 2,
    }
    values.update(overrides)
    return FaissHNSWConfig(**values)


def _states() -> np.ndarray:
    return np.array(
        [
            [1.0, 0.0, 0.0],
            [1.0, 0.001, 0.0],
            [1.0, -0.001, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )


def _query(
    query_indices: tuple[int, ...] | None = None,
) -> NeighborQuery:
    return NeighborQuery(
        cosine_min=0.999,
        relative_norm_gap_max=0.05,
        min_state_norm=1e-8,
        epsilon=1e-12,
        query_indices=query_indices,
    )


class _OverriddenFaissSearch(FaissHNSWBackend):
    def iter_pairs(self, states, *, query):
        del states, query
        yield from ()


def test_faiss_hnsw_build_is_byte_deterministic_and_bound() -> None:
    states = _states()
    kwargs = {
        "row_identity_sha256": _row_identity(),
        "comparison_group": "layer_index=0",
        "config": _config(),
    }
    first = FaissHNSWBackend(states, **kwargs)
    second = FaissHNSWBackend(states, **kwargs)

    assert first.descriptor == second.descriptor
    assert first.export_index_bytes() == second.export_index_bytes()
    assert first.build_receipt.sha256 == second.build_receipt.sha256
    assert dict(first.descriptor.parameters)["normalized_states_sha256"]
    validate_prepared_backend(
        first,
        states=states,
        row_identity_sha256=_row_identity(),
        comparison_group="layer_index=0",
    )


def test_faiss_hnsw_range_pairs_are_canonical_and_query_scoped() -> None:
    states = _states()
    backend = FaissHNSWBackend(
        states,
        row_identity_sha256=_row_identity(),
        comparison_group="layer_index=0",
        config=_config(),
    )

    all_pairs = tuple(
        pair.key for pair in backend.iter_pairs(states, query=_query())
    )
    subset_pairs = tuple(
        pair.key
        for pair in backend.iter_pairs(
            states,
            query=_query((1,)),
        )
    )

    assert all_pairs == ((0, 1), (0, 2), (1, 2))
    assert subset_pairs == ((0, 1), (1, 2))


def test_faiss_hnsw_rejects_wrong_input_or_group() -> None:
    states = _states()
    backend = FaissHNSWBackend(
        states,
        row_identity_sha256=_row_identity(),
        comparison_group="layer_index=0",
        config=_config(),
    )
    permuted = states[::-1].copy()

    with pytest.raises(ValueError, match="prepared Faiss index"):
        tuple(backend.iter_pairs(permuted, query=_query()))
    with pytest.raises(ValueError, match="full input/group"):
        validate_prepared_backend(
            backend,
            states=states,
            row_identity_sha256=_row_identity(),
            comparison_group="layer_index=1",
        )


def test_faiss_hnsw_rejects_mismatched_worker_runtime() -> None:
    runtime = current_worker_runtime_contract(None)
    runtime["numpy_version"] = "forged"

    with pytest.raises(
        ValueError,
        match="differs from its contract",
    ):
        FaissHNSWBackend(
            _states(),
            row_identity_sha256=_row_identity(),
            comparison_group="layer_index=0",
            config=_config(),
            worker_runtime_contract=runtime,
        )


def test_faiss_hnsw_fails_closed_on_raw_hit_budget() -> None:
    states = np.ones((6, 3), dtype=np.float64)
    backend = FaissHNSWBackend(
        states,
        row_identity_sha256=_row_identity(),
        comparison_group="layer_index=0",
        config=_config(max_raw_hits=5),
    )

    with pytest.raises(RuntimeError, match="max_raw_hits"):
        tuple(backend.iter_pairs(states, query=_query()))


def test_faiss_hnsw_rejects_worker_state_cache_tamper() -> None:
    states = _states()
    backend = FaissHNSWBackend(
        states,
        row_identity_sha256=_row_identity(),
        comparison_group="layer_index=0",
        config=_config(),
    )
    np.save(
        backend._states_path,
        states[::-1].astype(np.float32),
        allow_pickle=False,
    )

    with pytest.raises(ValueError, match="worker state cache"):
        tuple(backend.iter_pairs(states, query=_query()))


def test_faiss_hnsw_runs_through_candidate_boundary_audit() -> None:
    states = _states()
    drifts = np.array(
        [
            [0.0, 1.0, 0.0],
            [0.0, -1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.1, 0.0, 0.0],
            [0.0, 0.1, 0.0],
        ],
        dtype=np.float64,
    )
    candidate_config = CandidateSearchConfig(
        cosine_min=0.999,
        relative_norm_gap_max=0.05,
        drift_relative_divergence_min=1.5,
        block_size=2,
    )
    audit_config = NeighborAuditConfig(
        boundary_shell_width=0.000999
    )
    protocol = NeighborAuditProtocolBinding(
        protocol_id="faiss-test-v0.1",
        status="preregistered-draft",
        source_sha256="a" * 64,
        candidate_config_sha256=canonical_json_sha256(
            candidate_config.to_dict()
        ),
        audit_config_sha256=audit_config.sha256,
        deviations=("synthetic_fixture",),
    )
    source = {
        "kind": "synthetic_fixture",
        "fixture_id": "faiss-candidate-boundary-v1",
        "row_identity_sha256": _row_identity(),
    }

    result = audit_neighbor_backend(
        states,
        drifts,
        subject_backend_factory=lambda snapshot: FaissHNSWBackend(
            snapshot,
            row_identity_sha256=_row_identity(),
            comparison_group="layer_index=0",
            config=_config(),
        ),
        protocol_binding=protocol,
        source_identity=source,
        candidate_config=candidate_config,
        audit_config=audit_config,
        group_key="layer_index=0",
    )

    assert result.status == "pass"
    assert result.subject_backend.kind == "approximate"
    assert result.candidate_boundary_recall == (1.0, 1.0)
    assert result.identity_dict()["subject_index_build_sha256"]


def test_frozen_audit_rejects_overridden_faiss_search() -> None:
    states = _states()
    drifts = np.zeros_like(states)
    candidate_config = CandidateSearchConfig(
        cosine_min=0.999,
        relative_norm_gap_max=0.05,
        drift_relative_divergence_min=1.5,
        block_size=2,
    )
    audit_config = NeighborAuditConfig(
        boundary_shell_width=0.000999
    )
    protocol = NeighborAuditProtocolBinding(
        protocol_id="faiss-exact-type-test-v0.1",
        status="frozen",
        source_sha256="a" * 64,
        candidate_config_sha256=canonical_json_sha256(
            candidate_config.to_dict()
        ),
        audit_config_sha256=audit_config.sha256,
    )

    with pytest.raises(TypeError, match="built-in FaissHNSWBackend"):
        audit_neighbor_backend(
            states,
            drifts,
            subject_backend_factory=lambda snapshot: (
                _OverriddenFaissSearch(
                    snapshot,
                    row_identity_sha256=_row_identity(),
                    comparison_group="layer_index=0",
                    config=_config(score_margin=0.000999),
                )
            ),
            protocol_binding=protocol,
            source_identity={
                "kind": "synthetic_fixture",
                "fixture_id": "overridden-faiss-search",
                "row_identity_sha256": _row_identity(),
            },
            candidate_config=candidate_config,
            audit_config=audit_config,
            group_key="layer_index=0",
        )


def test_faiss_hnsw_requires_single_thread() -> None:
    with pytest.raises(ValueError, match="thread_count must be 1"):
        FaissHNSWConfig(thread_count=2)


def test_explicit_range_call_batch_selects_v0_2_without_mutating_v0_1() -> None:
    legacy = FaissHNSWConfig(query_batch_size=512)
    qualified = FaissHNSWConfig(
        query_batch_size=512,
        range_call_batch_size=1,
    )

    assert legacy.backend_version == "0.1"
    assert "range_call_batch_size" not in legacy.to_dict()
    assert legacy.effective_range_call_batch_size == 512
    assert (
        qualified.backend_version
        == FAISS_HNSW_RANGE_CALL_BACKEND_VERSION
    )
    assert qualified.to_dict()["range_call_batch_size"] == 1
    assert qualified.effective_range_call_batch_size == 1


@pytest.mark.parametrize("value", [True, 0, 513])
def test_range_call_batch_size_is_strict(value: object) -> None:
    error = TypeError if value is True else ValueError
    with pytest.raises(error, match="range_call_batch_size"):
        FaissHNSWConfig(
            query_batch_size=512,
            range_call_batch_size=value,  # type: ignore[arg-type]
        )


def test_v0_2_backend_requires_qualification_before_build() -> None:
    with pytest.raises(ValueError, match="qualification receipt"):
        FaissHNSWBackend(
            _states(),
            row_identity_sha256=_row_identity(),
            comparison_group="layer_index=0",
            config=_config(range_call_batch_size=1),
        )


class _FakeRangeIndex:
    def __init__(self, row_count: int = 5) -> None:
        self.ntotal = row_count
        self.call_sizes: list[int] = []

    def range_search(
        self,
        queries: np.ndarray,
        radius: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        del radius
        self.call_sizes.append(int(queries.shape[0]))
        labels = np.arange(queries.shape[0], dtype=np.int64)
        return (
            np.arange(queries.shape[0] + 1, dtype=np.int64),
            np.ones(queries.shape[0], dtype=np.float32),
            labels,
        )


def test_range_calls_are_aggregated_after_single_query_native_calls() -> None:
    index = _FakeRangeIndex()
    queries = np.ones((3, 2), dtype=np.float32)

    limits, scores, labels = _range_search_in_calls(
        index,
        queries,
        radius=0.5,
        range_call_batch_size=1,
        max_native_call_hits=5,
        max_total_hits=10,
    )

    assert index.call_sizes == [1, 1, 1]
    assert limits.tolist() == [0, 1, 2, 3]
    assert scores.tolist() == [1.0, 1.0, 1.0]
    assert labels.tolist() == [0, 0, 0]


def test_native_hit_ceiling_is_checked_before_range_call() -> None:
    index = _FakeRangeIndex(row_count=5)
    queries = np.ones((2, 2), dtype=np.float32)

    with pytest.raises(ValueError, match="prebound hit ceiling"):
        _range_search_in_calls(
            index,
            queries,
            radius=0.5,
            range_call_batch_size=2,
            max_native_call_hits=9,
            max_total_hits=10,
        )

    assert index.call_sizes == []


class _MalformedRangeIndex(_FakeRangeIndex):
    def range_search(
        self,
        queries: np.ndarray,
        radius: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        del queries, radius
        return (
            np.array([0, 1], dtype=np.int64),
            np.array([np.nan], dtype=np.float32),
            np.array([self.ntotal], dtype=np.int64),
        )


def test_native_range_result_is_validated_before_aggregation() -> None:
    with pytest.raises(ValueError, match="malformed"):
        _range_search_in_calls(
            _MalformedRangeIndex(),
            np.ones((1, 2), dtype=np.float32),
            radius=0.5,
            range_call_batch_size=1,
            max_native_call_hits=5,
            max_total_hits=5,
        )


def test_preflight_uses_production_build_search_and_readback(
    tmp_path,
) -> None:
    output = tmp_path / "preflight.json"

    faiss_hnsw_module._run_worker(
        [
            "preflight",
            "--output",
            str(output),
            "--fixture-schema-version",
            "test-fixture-v0.1",
            "--row-count",
            "8",
            "--hidden-size",
            "4",
            "--cluster-size",
            "2",
            "--query-count",
            "4",
            "--fixture-seed",
            "1729",
            "--m",
            "2",
            "--ef-construction",
            "20",
            "--ef-search",
            "20",
            "--seed",
            "1729",
            "--query-batch-size",
            "4",
            "--range-call-batch-size",
            "1",
            "--cosine-min",
            "0.9",
            "--score-margin",
            "0.001",
            "--radius",
            "0.899",
            "--max-native-call-hits",
            "8",
            "--max-raw-hits",
            "100",
        ],
        runtime_contract=current_worker_runtime_contract(None),
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["result"]["limits_length"] == 5
    assert payload["result"]["raw_hit_count"] > 0
    assert payload["search"]["range_call_batch_size"] == 1


def test_worker_subprocess_environment_is_allowlisted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["environment"] = kwargs["env"]
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setenv("SPIRALLENS_FORBIDDEN_SECRET", "secret")
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    monkeypatch.setattr(
        faiss_hnsw_module.subprocess,
        "run",
        fake_run,
    )

    faiss_hnsw_module._run_worker(
        ["search"],
        runtime_contract={"runtime": "bound"},
    )

    environment = captured["environment"]
    assert isinstance(environment, dict)
    assert "SPIRALLENS_FORBIDDEN_SECRET" not in environment
    assert environment["PYTHONDONTWRITEBYTECODE"] == "1"
    allowed = {
        "PATH",
        "LANG",
        "LC_ALL",
        "TMPDIR",
        "PYTHONPATH",
        "PYTHONDONTWRITEBYTECODE",
        "PYTHONPYCACHEPREFIX",
        "SPIRALLENS_FAISS_WORKER_RUNTIME_CONTRACT",
    }
    assert set(environment) <= allowed
    assert {
        "PATH",
        "LANG",
        "LC_ALL",
        "TMPDIR",
        "PYTHONDONTWRITEBYTECODE",
        "SPIRALLENS_FAISS_WORKER_RUNTIME_CONTRACT",
    } <= set(environment)
