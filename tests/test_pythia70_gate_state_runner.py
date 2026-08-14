from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
import math
import os
import platform
import socket
import sys
import time
from collections import Counter
from pathlib import Path
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest

from spirallens.core.canonical import canonical_json_bytes

ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts/run_pythia70_gate_state_development.py"
FREEZE_PATH = ROOT / "protocols/pythia70_gate_state_development_freeze_v0_1.json"
MODEL_IMPORT_PREFIXES = ("huggingface_hub", "safetensors", "torch", "transformers")
EXPECTED_RUNNER_SOURCE_SHA256 = (
    "fb92565229d75d0b4dd14c268db8091379b08dbcdec73dda033439aca3b00517"
)


def _load_runner() -> tuple[ModuleType, frozenset[str]]:
    before = frozenset(sys.modules)
    name = "_spirallens_pythia70_gate_state_runner_test_target"
    spec = importlib.util.spec_from_file_location(name, RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module, frozenset(sys.modules) - before


RUNNER, IMPORTED_BY_RUNNER = _load_runner()


def _freeze() -> dict[str, object]:
    value = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _canonical(document: object) -> bytes:
    return (
        json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def _valid_launch(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[dict[str, object], dict[str, object]]:
    freeze = _freeze()
    bindings = freeze["bindings"]
    assert isinstance(bindings, dict)
    artifacts = freeze["artifact_coordinates"]
    assert isinstance(artifacts, dict)
    route = freeze["route_amendment"]
    assert isinstance(route, dict)
    runner_source = RUNNER_PATH.read_bytes()
    implementation_commit = "a" * 40
    dependencies = {
        name: f"test-{index}"
        for index, name in enumerate(sorted(RUNNER._DEPENDENCY_DISTRIBUTIONS))
    }
    monkeypatch.setattr(RUNNER, "_dependency_versions", lambda: dependencies)

    def fake_git(*arguments: str, binary: bool = False) -> bytes | str:
        assert arguments[:2] == ("cat-file", "blob") and binary
        assert arguments[2] == f"{implementation_commit}:{RUNNER._RUNNER_RELATIVE}"
        return runner_source

    monkeypatch.setattr(RUNNER, "_git", fake_git)
    monkeypatch.setattr(
        RUNNER.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=b"", stderr=b""),
    )
    policy = bindings["policy_documents"]
    assert isinstance(policy, list) and len(policy) == 3
    frame = bindings["fundamental_frame"]
    context_bank = bindings["context_bank"]
    model = bindings["model"]
    assert isinstance(frame, dict)
    assert isinstance(context_bank, dict)
    assert isinstance(model, dict)
    launch = {
        "schema_version": "spirallens.pythia70-gate-state-launch-authorization.v0.1",
        "launch_id": "pythia70-gate-state-development-launch-v0.1",
        "attempt_id": "pythia70-gate-state-development-v0.1-attempt-1",
        "decision_date": "2026-08-14",
        "status": "authorized_not_started",
        "execution_class": route["execution_class"],
        "freeze": {
            "path": RUNNER._FREEZE_RELATIVE,
            "source_sha256": hashlib.sha256(FREEZE_PATH.read_bytes()).hexdigest(),
            "freeze_id": freeze["freeze_id"],
        },
        "context_bank": dict(context_bank),
        "route": {
            key: route[key]
            for key in ("path", "source_sha256", "route_id", "execution_class")
        },
        "frame": {
            key: frame[key]
            for key in ("path", "source_sha256", "ledger_amendment_anchor")
        },
        "merged_policy_docs": {
            "ledger_path": policy[0]["path"],
            "ledger_sha256": policy[0]["source_sha256"],
            "roadmap_path": policy[1]["path"],
            "roadmap_sha256": policy[1]["source_sha256"],
            "next_experiment_preparation_path": policy[2]["path"],
            "next_experiment_preparation_sha256": policy[2]["source_sha256"],
        },
        "runner": {
            "path": artifacts["prospective_runner_path"],
            "source_sha256": hashlib.sha256(runner_source).hexdigest(),
            "implementation_commit": implementation_commit,
        },
        "command": {
            "exact_argv": [
                sys.executable,
                "-B",
                RUNNER._RUNNER_RELATIVE,
            ],
            "working_directory": str(ROOT),
        },
        "runtime": {
            "python_executable": sys.executable,
            "python_version": platform.python_version(),
            "dependency_versions": dependencies,
        },
        "model": {
            "id": model["id"],
            "revision": model["revision"],
            "file_sha256_and_sizes": model["files"],
        },
        "artifacts": {
            "external_staging_path": artifacts["external_staging_path"],
            "external_store_path": artifacts["external_store_path"],
            "external_next_hypotheses_path": artifacts["external_next_hypotheses_path"],
            "repository_projection_paths": [
                artifacts["attempt_record"],
                artifacts["terminal_result"],
                artifacts["next_hypotheses"],
            ],
        },
        "absence_precondition": {
            "coordinates_required_absent": [
                artifacts["external_staging_path"],
                artifacts["external_store_path"],
                artifacts["external_next_hypotheses_path"],
                artifacts["attempt_record"],
                artifacts["terminal_result"],
                artifacts["next_hypotheses"],
            ],
            "runner_must_observe_absence_and_exclusively_start_in_same_process": True,
        },
        "resource_budget": {
            "wall_clock_seconds_hard": freeze["resource_budget"][
                "wall_clock_seconds_hard"
            ],
            "model_loads_maximum": freeze["resource_budget"]["model_loads_maximum"],
            "forward_batches_maximum": freeze["resource_budget"][
                "forward_batches_maximum"
            ],
            "byte_limits": {
                key: freeze["resource_budget"][key]
                for key in (
                    "raw_capture_bytes_hard",
                    "terminal_result_bytes_hard",
                    "next_hypotheses_bytes_hard",
                    "max_estimated_peak_bytes",
                )
            },
        },
        "authorizations": {
            "operator_authorized_exact_one_attempt": True,
            "execution_authorized": True,
            "model_access_authorized": True,
        },
        "claim_boundary": {
            key: freeze["claim_boundary"][key]
            for key in (
                "claim_ceiling",
                "claim_delta",
                "milestone_credit",
                "evidence_eligible",
            )
        },
    }
    return freeze, launch


def _mutate_launch(document: dict[str, object], case: str) -> None:
    if case == "missing_root":
        document.pop("status")
    elif case == "unknown_root":
        document["unknown"] = False
    elif case == "status":
        document["status"] = "authorized"
    elif case == "decision_date":
        document["decision_date"] = "2026-8-14"
    elif case == "execution_class":
        document["execution_class"] = "other"
    elif case == "freeze":
        document["freeze"]["source_sha256"] = "0" * 64
    elif case == "context_bank_type":
        document["context_bank"]["claim_eligible"] = 0
    elif case == "route":
        document["route"]["route_id"] = "other"
    elif case == "frame":
        document["frame"]["source_sha256"] = "0" * 64
    elif case == "policy":
        document["merged_policy_docs"]["roadmap_sha256"] = "0" * 64
    elif case == "runner_path":
        document["runner"]["path"] = "scripts/other.py"
    elif case == "runner_sha":
        document["runner"]["source_sha256"] = "0" * 64
    elif case == "runner_commit":
        document["runner"]["implementation_commit"] = "not-a-commit"
    elif case == "argv":
        document["command"]["exact_argv"] = []
    elif case == "working_directory":
        document["command"]["working_directory"] = "/tmp"
    elif case == "python":
        document["runtime"]["python_executable"] = "/tmp/python"
    elif case == "python_alias":
        document["runtime"]["python_executable"] = "/usr/bin/../bin/python"
    elif case == "python_version":
        document["runtime"]["python_version"] = "0.0.0"
    elif case == "dependency":
        document["runtime"]["dependency_versions"]["unknown"] = "1"
    elif case == "model":
        document["model"]["revision"] = "0" * 40
    elif case == "artifacts":
        document["artifacts"]["repository_projection_paths"].reverse()
    elif case == "absence":
        document["absence_precondition"]["coordinates_required_absent"].reverse()
    elif case == "budget":
        document["resource_budget"]["model_loads_maximum"] = 2
    elif case == "authorization_type":
        document["authorizations"]["execution_authorized"] = 1
    elif case == "claim":
        document["claim_boundary"]["evidence_eligible"] = True
    else:  # pragma: no cover - the parametrization is closed below.
        raise AssertionError(case)


def test_runner_import_is_model_cache_and_network_inert() -> None:
    assert RUNNER_PATH.is_file() and not RUNNER_PATH.is_symlink()
    assert not any(
        name == prefix or name.startswith(prefix + ".")
        for name in IMPORTED_BY_RUNNER
        for prefix in MODEL_IMPORT_PREFIXES
    )
    assert hashlib.sha256(RUNNER_PATH.read_bytes()).hexdigest() == (
        EXPECTED_RUNNER_SOURCE_SHA256
    )
    assert RUNNER._FREEZE_SHA256 == hashlib.sha256(FREEZE_PATH.read_bytes()).hexdigest()
    assert RUNNER._GATE_IDS == (
        "capture_integrity",
        "measurable_drift",
        "f2_section_support",
        "f4_tensor_support",
        "low_amplitude_set_repeatability",
        "address_loop_support",
        "continuous_holonomy_consistency",
        "address_ring_phase_resolution",
        "graph_family_agreement",
        "negative_controls",
    )


def test_launch_validator_accepts_only_exact_canonical_frozen_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    freeze, launch = _valid_launch(monkeypatch)
    source = _canonical(launch)

    RUNNER._validate_launch(freeze, launch, source)
    assert RUNNER._canonical_json_bytes(launch) == source
    assert launch["command"] == {
        "exact_argv": [sys.executable, "-B", RUNNER._RUNNER_RELATIVE],
        "working_directory": str(ROOT),
    }

    noncanonical = json.dumps(launch, indent=2, sort_keys=True).encode() + b"\n"
    with pytest.raises(RUNNER._PreflightError, match="canonical"):
        RUNNER._validate_launch(freeze, launch, noncanonical)


@pytest.mark.parametrize(
    "case",
    (
        "missing_root",
        "unknown_root",
        "status",
        "decision_date",
        "execution_class",
        "freeze",
        "context_bank_type",
        "route",
        "frame",
        "policy",
        "runner_path",
        "runner_sha",
        "runner_commit",
        "argv",
        "working_directory",
        "python",
        "python_alias",
        "python_version",
        "dependency",
        "model",
        "artifacts",
        "absence",
        "budget",
        "authorization_type",
        "claim",
    ),
)
def test_launch_validator_rejects_each_adversarial_axis(
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    freeze, launch = _valid_launch(monkeypatch)
    forged = copy.deepcopy(launch)
    _mutate_launch(forged, case)

    with pytest.raises(RUNNER._PreflightError):
        RUNNER._validate_launch(freeze, forged, _canonical(forged))


@pytest.mark.parametrize(
    "source",
    (
        b'{"x":1,"x":2}\n',
        b'{"x":NaN}\n',
        b"[]\n",
        b"\xff",
    ),
)
def test_strict_json_rejects_duplicate_nonfinite_nonobject_and_non_utf8(
    source: bytes,
) -> None:
    with pytest.raises(RUNNER._PreflightError):
        RUNNER._strict_json_bytes(source, label="adversary")


def test_exact_cell_manifest_and_state_folds_recompute_without_model() -> None:
    freeze = _freeze()
    cells = RUNNER._required_cell_manifest(freeze)
    counts = Counter(cell.gate_id for cell in cells)
    assert len(cells) == len({cell.cell_id for cell in cells}) == 894
    assert tuple(counts[gate] for gate in RUNNER._GATE_IDS) == (
        48,
        12,
        36,
        36,
        36,
        216,
        54,
        216,
        24,
        216,
    )
    assert RUNNER._fold_cell_states(("pass", "pass")) == "pass"
    assert RUNNER._fold_cell_states(("not_run", "not_run")) == "not_run"
    assert RUNNER._fold_cell_states(("pass", "not_run")) == "insufficient"
    assert RUNNER._fold_cell_states(("pass", "insufficient")) == "insufficient"
    assert RUNNER._fold_cell_states(("pass", "fail")) == "fail"
    assert RUNNER._terminal_fold([{"state": "pass"}] * 10) == "pass"
    assert (
        RUNNER._terminal_fold([{"state": "pass"}] * 9 + [{"state": "fail"}]) == "fail"
    )
    assert (
        RUNNER._terminal_fold([{"state": "pass"}] * 9 + [{"state": "insufficient"}])
        == "insufficient"
    )

    forged = copy.deepcopy(freeze)
    forged["gate_state_contract"]["required_cell_manifests"][0][
        "expected_cell_count"
    ] += 1
    with pytest.raises(RUNNER._RunError, match="manifest differs"):
        RUNNER._required_cell_manifest(forged)


def test_cell_records_phase_and_tensor_helpers_preserve_frozen_boundaries() -> None:
    freeze = _freeze()
    manifest = RUNNER._required_cell_manifest(freeze)[0]
    metrics = {
        "resid_pre_raw_sha256": "1" * 64,
        "resid_post_raw_sha256": "2" * 64,
        "shape": [49, 6, 512],
        "dtype": "<f4",
        "all_finite": True,
    }
    passed = RUNNER._cell_record(
        freeze,
        manifest,
        state="pass",
        support_count=49,
        coverage_denominator=49,
        metrics=metrics,
    )
    assert passed["attempted"] is passed["evaluable"] is True
    insufficient = RUNNER._cell_record(
        freeze,
        manifest,
        state="insufficient",
        support_count=0,
        coverage_denominator=49,
        reasons=("missing", "missing"),
    )
    assert insufficient["reason_codes"] == ["missing"]
    assert set(insufficient["metrics"].values()) == {None}
    with pytest.raises(RUNNER._RunError):
        RUNNER._cell_record(
            freeze,
            manifest,
            state="pass",
            support_count=49,
            coverage_denominator=49,
            metrics={},
        )
    drift_manifest = next(
        cell
        for cell in RUNNER._required_cell_manifest(freeze)
        if cell.gate_id == "measurable_drift"
    )
    normalized = RUNNER._cell_record(
        freeze,
        drift_manifest,
        state="pass",
        support_count=1,
        coverage_denominator=1,
        metrics={"median_token_l2_response": -0.0},
    )["metrics"]["median_token_l2_response"]
    assert normalized == 0.0
    assert math.copysign(1.0, normalized) == 1.0

    phase = np.exp(2j * np.pi * np.arange(8, dtype=np.float64) / 8.0)
    forward = RUNNER._phase_diagnostics(phase, tuple(range(8)))
    reverse = RUNNER._phase_diagnostics(phase, (0, 7, 6, 5, 4, 3, 2, 1))
    assert forward.total_cycles == pytest.approx(1.0)
    assert reverse.total_cycles == pytest.approx(-1.0)
    assert forward.residual_cycles == pytest.approx(0.0)
    tensor = RUNNER._detrace(np.asarray([[[3.0, 1.0], [1.0, 1.0]]]))
    assert np.trace(tensor[0]) == pytest.approx(0.0)
    assert RUNNER._jaccard((1, 2), (2, 3)) == pytest.approx(1.0 / 3.0)


def test_terminal_prefix_contract_is_exact_16_18_10_894() -> None:
    freeze = _freeze()
    contexts = freeze["input_plan"]["contexts"]["ordered_ids"]
    cells = RUNNER._required_cell_manifest(freeze)
    state = SimpleNamespace(
        freeze=freeze,
        capture_manifest=[
            {"context_id": context, "capture_stage": stage}
            for context in contexts
            for stage in RUNNER._STAGES
        ],
        graph_receipts=[
            {"layer_id": layer, "graph_family": family}
            for layer in range(6)
            for family in RUNNER._FAMILIES
        ],
        cell_records=[{"cell_id": cell.cell_id} for cell in cells],
        gate_records=[{"gate_id": gate} for gate in RUNNER._GATE_IDS],
    )
    RUNNER._validate_terminal_prefixes(state, complete=True)
    state.graph_receipts[0]["graph_family"] = "forged"
    with pytest.raises(RUNNER._RunError, match="graph receipt prefix"):
        RUNNER._validate_terminal_prefixes(state, complete=True)


@pytest.mark.parametrize(
    "occupied",
    (
        "external_staging_path",
        "external_store_path",
        "external_next_hypotheses_path",
        "attempt_record",
        "terminal_result",
        "next_hypotheses",
    ),
)
def test_required_absence_checks_each_coordinate_without_model_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    occupied: str,
) -> None:
    paths = {
        name: tmp_path / name
        for name in (
            "external_staging_path",
            "external_store_path",
            "external_next_hypotheses_path",
            "attempt_record",
            "terminal_result",
            "next_hypotheses",
        )
    }
    monkeypatch.setattr(RUNNER, "_artifact_paths", lambda _freeze: paths)
    assert RUNNER._observe_required_absence({}) == tuple(paths)
    paths[occupied].touch()
    with pytest.raises(RUNNER._PreflightError, match="already exists"):
        RUNNER._observe_required_absence({})


def test_exclusive_file_and_stage_reservation_are_exactly_once(
    tmp_path: Path,
) -> None:
    parent_fd = os.open(tmp_path, RUNNER._DIRECTORY_FLAGS)
    try:
        descriptor = RUNNER._write_exclusive_at(
            parent_fd,
            "record.json",
            b"{}\n",
            maximum=16,
            stage="terminal_persistence",
        )
        os.close(descriptor)
        with pytest.raises(FileExistsError):
            RUNNER._write_exclusive_at(
                parent_fd,
                "record.json",
                b"forged\n",
                maximum=16,
                stage="terminal_persistence",
            )
        assert (tmp_path / "record.json").read_bytes() == b"{}\n"
    finally:
        os.close(parent_fd)

    freeze = _freeze()
    freeze["artifact_coordinates"]["external_staging_path"] = str(tmp_path / "stage")
    freeze["artifact_coordinates"]["external_store_path"] = str(tmp_path / "store")
    stage, metadata = RUNNER._reserve_stage(freeze)
    assert metadata.st_mode & 0o777 == 0o700
    stage.close()
    assert (tmp_path / "stage").is_dir()
    with pytest.raises(RUNNER._RunError):
        RUNNER._reserve_stage(freeze)


def test_npy_sink_persists_exact_float32_rows_and_digest(tmp_path: Path) -> None:
    parent_fd = os.open(tmp_path, RUNNER._DIRECTORY_FLAGS)
    sink = RUNNER._NpySink.create(parent_fd, "capture.npy")
    values = np.arange(49 * 6 * 512, dtype="<f4").reshape(49, 6, 512)
    try:
        for start in range(0, 49, 7):
            sink.write_rows(start, values[start : start + 7])
        record = sink.finish(
            relative_path="raw-captures/context/resid_pre.npy",
            context_id="context",
            capture_stage="resid_pre",
        )
    finally:
        sink.close()
        os.close(parent_fd)
    source = (tmp_path / "capture.npy").read_bytes()
    reloaded = np.load(io.BytesIO(source), allow_pickle=False)
    assert np.array_equal(reloaded, values)
    assert record["raw_array_sha256"] == hashlib.sha256(values.tobytes()).hexdigest()
    assert record["file_sha256"] == hashlib.sha256(source).hexdigest()
    assert record["size_bytes"] == len(source)


def test_model_file_observation_uses_only_bounded_synthetic_members(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "cache" / "snapshots" / "revision"
    snapshot.mkdir(parents=True)
    source = b"synthetic model member"
    (snapshot / "config.json").write_bytes(source)
    expected = {
        "size_bytes": len(source),
        "sha256": hashlib.sha256(source).hexdigest(),
    }
    verified = RUNNER._bounded_model_file_observation(snapshot, "config.json", expected)
    assert verified == {
        "relative_name": "config.json",
        "status": "verified",
        "size_bytes": len(source),
        "sha256": expected["sha256"],
        "error_type": None,
        "error_message": None,
    }
    mismatch = RUNNER._bounded_model_file_observation(
        snapshot,
        "config.json",
        {"size_bytes": len(source), "sha256": "0" * 64},
    )
    assert mismatch["status"] == "mismatch"
    assert (
        RUNNER._bounded_model_file_observation(snapshot, "missing", expected)["status"]
        == "missing"
    )
    outside = tmp_path / "outside"
    outside.write_bytes(source)
    (snapshot / "escape").symlink_to(outside)
    escaped = RUNNER._bounded_model_file_observation(snapshot, "escape", expected)
    assert escaped["status"] == "read_error"


def test_attempt_and_infrastructure_terminal_are_canonical_and_claim_ineligible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    freeze, launch = _valid_launch(monkeypatch)
    runner_source = RUNNER_PATH.read_bytes()
    preflight = RUNNER._Preflight(
        freeze=freeze,
        launch=launch,
        freeze_source=FREEZE_PATH.read_bytes(),
        launch_source=_canonical(launch),
        launch_sha256=hashlib.sha256(_canonical(launch)).hexdigest(),
        runner_source=runner_source,
        runtime_source_commit="b" * 40,
        no_replace_primitive="test.no-replace",
    )
    timestamp = "2026-08-14T00:00:00.000000Z"
    attempt = RUNNER._build_attempt_record(
        preflight,
        observed_at_utc=timestamp,
        reserved_at_utc=timestamp,
        stage_metadata=tmp_path.stat(),
    )
    attempt_source = _canonical(attempt)
    assert RUNNER._canonical_json_bytes(attempt) == attempt_source
    assert set(attempt["bindings"]) == set(
        freeze["lifecycle"]["attempt_record_required_bindings"]
    )
    state = RUNNER._RunState(
        preflight=preflight,
        stage=SimpleNamespace(),
        started_at_utc=timestamp,
        started_monotonic=time.monotonic(),
        attempt_source=attempt_source,
        attempt_sha256=hashlib.sha256(attempt_source).hexdigest(),
    )
    monkeypatch.setattr(RUNNER, "_utc_now", lambda: timestamp)
    terminal, terminal_source = RUNNER._build_terminal_result(
        state,
        error=RUNNER._RunError("model_file_hash", "synthetic failure"),
        caught_at_utc=timestamp,
    )
    assert terminal_source == _canonical(terminal)
    assert terminal["execution_terminal"] == "infrastructure_error"
    assert terminal["terminal_fold"] is None
    assert terminal["claim_boundary"] == freeze["claim_boundary"]
    assert terminal["error"]["stage"] == "model_file_hash"
    assert terminal["capture_manifest"] == []
    assert terminal["graph_receipts"] == []
    assert terminal["gate_records"] == []
    assert terminal["cell_records"] == []


def test_full_synthetic_numeric_route_recomputes_exact_terminal_without_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model_modules_before = {
        name
        for name in sys.modules
        if any(
            name == prefix or name.startswith(prefix + ".")
            for prefix in MODEL_IMPORT_PREFIXES
        )
    }

    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("synthetic route crossed a model/cache/network boundary")

    monkeypatch.setattr(RUNNER, "_resolve_and_verify_model_files", forbidden)
    monkeypatch.setattr(RUNNER, "_load_exact_model", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    freeze = _freeze()
    interfaces = RUNNER._load_bound_numeric_interfaces(freeze)
    model = freeze["bindings"]["model"]
    launch = {
        "launch_id": "L",
        "attempt_id": "A",
        "runner": {"path": RUNNER._RUNNER_RELATIVE},
        "command": {
            "exact_argv": ["python3", RUNNER._RUNNER_RELATIVE],
            "working_directory": str(ROOT),
        },
        "runtime": {
            "python_executable": sys.executable,
            "python_version": ".",
            "dependency_versions": {},
        },
        "model": {"id": model["id"], "revision": model["revision"]},
    }
    preflight = RUNNER._Preflight(
        freeze=freeze,
        launch=launch,
        freeze_source=FREEZE_PATH.read_bytes(),
        launch_source=b"launch",
        launch_sha256="1" * 64,
        runner_source=RUNNER_PATH.read_bytes(),
        runtime_source_commit="8" * 40,
        no_replace_primitive="test.no-replace",
    )
    timestamp = "2026-08-14T00:00:00.000000Z"
    artifact_coordinates = freeze["artifact_coordinates"]
    attempt = {
        "schema_version": freeze["lifecycle"]["attempt_record_contract"][
            "schema_version"
        ],
        "attempt_id": "A",
        "launch_id": "L",
        "started_at_utc": timestamp,
        "absence_and_reservation": {
            "observed_at_utc": timestamp,
            "observed_absent_coordinates": freeze["lifecycle"][
                "attempt_record_contract"
            ]["observed_absent_coordinates_must_equal"],
            "reserved_at_utc": timestamp,
            "stage_path": artifact_coordinates["external_staging_path"],
            "stage_device": 1,
            "stage_inode": 1,
            "stage_mode": 448,
            "parent_directory_fsynced": True,
        },
        "bindings": {
            "launch_authorization_sha256": "1" * 64,
            "freeze_source_sha256": "2" * 64,
            "context_bank_source_sha256": "3" * 64,
            "context_bank_canonical_sha256": "4" * 64,
            "route_source_sha256": "5" * 64,
            "runner_source_sha256": "6" * 64,
            "runner_implementation_commit": "7" * 40,
            "runtime_source_commit": "8" * 40,
            "exact_argv": launch["command"]["exact_argv"],
            "runtime_versions": launch["runtime"],
            "expected_model_file_sha256_and_sizes": model["files"],
            "all_external_and_repository_coordinates": artifact_coordinates,
            "resource_budget": freeze["resource_budget"],
            "claim_boundary": freeze["claim_boundary"],
        },
        "artifact_coordinates": artifact_coordinates,
        "resource_budget": freeze["resource_budget"],
        "claim_boundary": freeze["claim_boundary"],
    }
    attempt_source = _canonical(attempt)
    state = RUNNER._RunState(
        preflight=preflight,
        stage=SimpleNamespace(),
        started_at_utc=timestamp,
        started_monotonic=time.monotonic(),
        attempt_source=attempt_source,
        attempt_sha256=hashlib.sha256(attempt_source).hexdigest(),
        model_loads=1,
        forward_batches=56,
        raw_capture_bytes=9_633_792,
    )
    expected_files = freeze["bindings"]["model"]["files"]
    state.observed_model_file_slots = [
        {
            "relative_name": name,
            "status": "verified",
            "size_bytes": expected_files[name]["size_bytes"],
            "sha256": expected_files[name]["sha256"],
            "error_type": None,
            "error_message": None,
        }
        for name in ("config.json", "model.safetensors")
    ]
    cube = (
        np.random.default_rng(115)
        .normal(scale=0.05, size=(8, 2, 49, 6, 512))
        .astype("<f4")
    )
    contexts = freeze["input_plan"]["contexts"]["ordered_ids"]
    for context_index, context_id in enumerate(contexts):
        for stage_index, capture_stage in enumerate(RUNNER._STAGES):
            array = np.asarray(cube[context_index, stage_index], dtype="<f4", order="C")
            raw = array.tobytes(order="C")
            state.capture_manifest.append(
                {
                    "relative_path": f"raw-captures/{context_id}/{capture_stage}.npy",
                    "context_id": context_id,
                    "capture_stage": capture_stage,
                    "shape": [49, 6, 512],
                    "dtype": "<f4",
                    "finite": True,
                    "raw_array_sha256": hashlib.sha256(raw).hexdigest(),
                    "file_sha256": "0" * 64,
                    "size_bytes": len(raw),
                }
            )
    signals = RUNNER._SignalLatch()
    response = np.asarray(cube[:, 1], dtype="<f8") - np.asarray(cube[:, 0], dtype="<f8")
    graphs = RUNNER._construct_graph_layers(
        state,
        response,
        np.asarray(cube[:, 0], dtype="<f8"),
        interfaces,
        signals,
    )
    candidates = RUNNER._derive_candidates(
        freeze,
        response,
        graphs,
        interfaces,
        signals,
        state,
    )
    RUNNER._evaluate_cells(state, cube, response, candidates, interfaces, signals)
    assert len(state.capture_manifest) == 16
    assert len(state.graph_receipts) == 18
    assert len(state.gate_records) == 10
    assert len(state.cell_records) == 894
    offset = 0
    manifests = freeze["gate_state_contract"]["required_cell_manifests"]
    for gate_record, manifest in zip(state.gate_records, manifests, strict=True):
        count = manifest["expected_cell_count"]
        block = state.cell_records[offset : offset + count]
        source = canonical_json_bytes(block)
        digest = hashlib.sha256(source).hexdigest()
        assert not source.endswith(b"\n")
        assert gate_record["gate_id"] == manifest["gate_id"]
        assert gate_record["cell_records_canonical_sha256"] == digest
        assert digest != hashlib.sha256(source + b"\n").hexdigest()
        offset += count
    assert offset == 894
    terminal, terminal_source = RUNNER._build_terminal_result(
        state,
        error=None,
        caught_at_utc=None,
    )
    assert terminal["execution_terminal"] == "complete"
    assert terminal["terminal_fold"] == "fail"
    assert (
        600_000
        < len(terminal_source)
        < freeze["resource_budget"]["terminal_result_bytes_hard"]
    )
    assert terminal["resource_use"]["terminal_result_size_verified_below_hard"] is True
    assert terminal_source == _canonical(terminal)
    mutated = cube.copy()
    mutated.view(np.uint8).flat[0] ^= 1
    with pytest.raises(RUNNER._RunError) as caught:
        RUNNER._evaluate_cells(
            state,
            mutated,
            response,
            candidates,
            interfaces,
            signals,
        )
    assert caught.value.stage == "capture"
    assert model_modules_before == {
        name
        for name in sys.modules
        if any(
            name == prefix or name.startswith(prefix + ".")
            for prefix in MODEL_IMPORT_PREFIXES
        )
    }


def test_validate_only_dispatch_never_enters_attempt_or_model_path(
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    freeze = _freeze()
    preflight = RUNNER._Preflight(
        freeze=freeze,
        launch={"launch_id": "pythia70-gate-state-development-launch-v0.1"},
        freeze_source=b"freeze",
        launch_source=b"launch",
        launch_sha256="1" * 64,
        runner_source=b"runner",
        runtime_source_commit="2" * 40,
        no_replace_primitive="test.no-replace",
    )
    monkeypatch.setattr(RUNNER, "_preflight", lambda **_kwargs: preflight)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("validate-only crossed the exclusive-start/model boundary")

    monkeypatch.setattr(RUNNER, "_reserve_stage", forbidden)
    monkeypatch.setattr(RUNNER, "_resolve_and_verify_model_files", forbidden)
    monkeypatch.setattr(RUNNER, "_run_started_attempt", forbidden)
    assert RUNNER._run(validate_launch_only=True) == 0
    receipt = json.loads(capfd.readouterr().out)
    assert receipt == {
        "schema_version": "spirallens.pythia70-gate-state-launch-validation.v0.1",
        "status": "validated_not_started",
        "freeze_id": freeze["freeze_id"],
        "launch_id": "pythia70-gate-state-development-launch-v0.1",
        "runtime_source_commit": "2" * 40,
        "runner_source_sha256": hashlib.sha256(b"runner").hexdigest(),
        "launch_authorization_sha256": "1" * 64,
        "no_replace_primitive": "test.no-replace",
        "model_or_cache_accessed": False,
    }
