from __future__ import annotations

import copy
import hashlib
import itertools
import json
import os
import re
import subprocess
from datetime import date
from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest
import yaml

from spirallens.contexts import CaptureStage, ContextRole, load_context_bank
from spirallens.referents import validate_observation_partition

ROOT = Path(__file__).resolve().parents[1]
FREEZE_PATH = ROOT / "protocols/pythia70_gate_state_development_freeze_v0_1.json"
BANK_PATH = ROOT / "protocols/context_bank_pythia70_gate_state_v0_1.yaml"
PUBLIC_BANK_PATH = ROOT / "protocols/context_bank_example_v0_1.yaml"
ROUTE_PATH = ROOT / "protocols/pythia70_gate_state_reconnaissance_route_v0_1.json"
LAUNCH_PATH = (
    ROOT / "experiments/pythia/gate_state_development_v0_1/launch-authorization.json"
)
ATTEMPT_PATH = ROOT / "experiments/pythia/gate_state_development_v0_1/attempt.json"
TERMINAL_PATH = (
    ROOT / "experiments/pythia/gate_state_development_v0_1/terminal-result.json"
)
NEXT_HYPOTHESES_PATH = (
    ROOT / "experiments/pythia/gate_state_development_v0_1/next-hypotheses.json"
)
REPOSITORY_STATE_PATHS = (
    ("launch_authorization", LAUNCH_PATH),
    ("attempt_record", ATTEMPT_PATH),
    ("terminal_result", TERMINAL_PATH),
    ("next_hypotheses", NEXT_HYPOTHESES_PATH),
)
ALLOWED_REPOSITORY_STATES = {
    "0000": "unlaunched",
    "1000": "authorized_not_started",
    "1110": "terminal_projected_without_next_hypotheses",
    "1111": "terminal_projected_with_next_hypotheses",
}
POLICY_DOCUMENT_PATHS = frozenset(
    {
        "docs/EXPERIMENT_INTERPRETATION_LEDGER.md",
        "docs/ROADMAP.md",
        "docs/NEXT_EXPERIMENT_PREPARATION.md",
    }
)
EXPECTED_BANK_SOURCE = (
    3200,
    "2d16c7c77f8f39a4b89aa118c8f45eb567aa8ddd8c7f230167f17f3cb82e50df",
)
EXPECTED_ROUTE_SOURCE = (
    3466,
    "300c55f5dff5419975ddcc10dd915068ee03e82c5097743a2e76937b2add9853",
)
EXPECTED_FREEZE_SOURCE = (
    68375,
    "fe85ebb15e0a9794a02d72b4fdefd0178b52662528e8e066530d873516b52452",
)
EXPECTED_ROOT_KEYS = {
    "schema_version",
    "freeze_id",
    "status",
    "decision",
    "chronology",
    "route_amendment",
    "bindings",
    "input_plan",
    "derivation_plan",
    "graph_plan",
    "address_grid_baseline",
    "gate_state_contract",
    "lifecycle",
    "launch_authorization_contract",
    "terminal_result_contract",
    "artifact_coordinates",
    "resource_budget",
    "authorizations",
    "claim_boundary",
    "historical_exclusions",
}
EXPECTED_CONTEXT_IDS = (
    "gate-fit-bracket-a",
    "gate-eval-bracket-a",
    "gate-fit-prefix-b",
    "gate-eval-prefix-b",
    "gate-fit-suffix-c",
    "gate-eval-suffix-c",
    "gate-fit-bracket-d",
    "gate-eval-bracket-d",
)
EXPECTED_GATES = (
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
EXPECTED_RUNTIME_DEPENDENCIES = frozenset(
    {
        "huggingface_hub",
        "numpy",
        "safetensors",
        "scipy",
        "spirallens",
        "torch",
        "transformers",
    }
)


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _load_json(path: Path, *, canonical: bool = False) -> dict[str, object]:
    assert not path.is_symlink() and path.is_file()
    raw = path.read_bytes()
    assert raw.endswith(b"\n") and raw.count(b"\x00") == 0
    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_strict_object,
        parse_constant=lambda constant: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON constant {constant}")
        ),
    )
    assert isinstance(value, dict)
    if canonical:
        rerendered = (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
        assert raw == rerendered
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_blob(commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


def _assert_commit(commit: object) -> str:
    assert isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit)
    subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return commit


def _assert_ancestor(ancestor: str, descendant: str) -> None:
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _deep_exact_equal(left: object, right: object) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        assert isinstance(right, dict)
        return set(left) == set(right) and all(
            _deep_exact_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        assert isinstance(right, list)
        return len(left) == len(right) and all(
            _deep_exact_equal(one, two) for one, two in zip(left, right, strict=True)
        )
    return bool(left == right)


def _assert_exact(left: object, right: object) -> None:
    assert _deep_exact_equal(left, right)


def _validate_launch_document(
    freeze: dict[str, object], launch: dict[str, object]
) -> tuple[str, str]:
    contract = freeze["launch_authorization_contract"]
    bindings = freeze["bindings"]
    artifacts = freeze["artifact_coordinates"]
    budget = freeze["resource_budget"]
    claim = freeze["claim_boundary"]
    route = freeze["route_amendment"]
    assert all(
        isinstance(item, dict)
        for item in (contract, bindings, artifacts, budget, claim, route)
    )
    assert isinstance(contract, dict)
    assert isinstance(bindings, dict)
    assert isinstance(artifacts, dict)
    assert isinstance(budget, dict)
    assert isinstance(claim, dict)
    assert isinstance(route, dict)

    root_fields = contract["required_root_fields"]
    fixed = contract["required_fixed_values"]
    required_bindings = contract["required_bindings"]
    assert isinstance(root_fields, list)
    assert isinstance(fixed, dict)
    assert isinstance(required_bindings, dict)
    assert set(launch) == set(root_fields)
    for name, fields in required_bindings.items():
        value = launch[name]
        assert isinstance(value, dict) and isinstance(fields, list)
        assert set(value) == set(fields)
    for name in ("schema_version", "launch_id", "attempt_id", "status"):
        _assert_exact(launch[name], fixed[name])

    decision_date = launch["decision_date"]
    freeze_decision = freeze["decision"]
    assert isinstance(decision_date, str) and isinstance(freeze_decision, dict)
    parsed_launch_date = date.fromisoformat(decision_date)
    assert parsed_launch_date.isoformat() == decision_date
    assert parsed_launch_date >= date.fromisoformat(freeze_decision["decision_date"])

    _assert_exact(launch["execution_class"], route["execution_class"])
    _assert_exact(
        launch["freeze"],
        {
            "path": FREEZE_PATH.relative_to(ROOT).as_posix(),
            "source_sha256": _sha256(FREEZE_PATH),
            "freeze_id": freeze["freeze_id"],
        },
    )
    _assert_exact(launch["context_bank"], bindings["context_bank"])
    _assert_exact(
        launch["route"],
        {
            key: route[key]
            for key in ("path", "source_sha256", "route_id", "execution_class")
        },
    )
    frame = bindings["fundamental_frame"]
    policy = bindings["policy_documents"]
    assert isinstance(frame, dict)
    assert isinstance(policy, list) and len(policy) == 3
    assert all(isinstance(item, dict) for item in policy)
    _assert_exact(
        launch["frame"],
        {
            key: frame[key]
            for key in ("path", "source_sha256", "ledger_amendment_anchor")
        },
    )
    _assert_exact(
        launch["merged_policy_docs"],
        {
            "ledger_path": policy[0]["path"],
            "ledger_sha256": policy[0]["source_sha256"],
            "roadmap_path": policy[1]["path"],
            "roadmap_sha256": policy[1]["source_sha256"],
            "next_experiment_preparation_path": policy[2]["path"],
            "next_experiment_preparation_sha256": policy[2]["source_sha256"],
        },
    )

    runner = launch["runner"]
    command = launch["command"]
    runtime = launch["runtime"]
    assert isinstance(runner, dict)
    assert isinstance(command, dict)
    assert isinstance(runtime, dict)
    runner_path = runner["path"]
    assert runner_path == artifacts["prospective_runner_path"]
    assert isinstance(runner_path, str)
    current_runner = ROOT / runner_path
    assert not current_runner.is_symlink() and current_runner.is_file()
    assert runner["source_sha256"] == _sha256(current_runner)
    implementation_commit = _assert_commit(runner["implementation_commit"])
    _assert_ancestor(implementation_commit, "HEAD")
    assert _git_blob(implementation_commit, runner_path) == current_runner.read_bytes()

    python_executable = runtime["python_executable"]
    python_version = runtime["python_version"]
    dependencies = runtime["dependency_versions"]
    assert isinstance(python_executable, str) and Path(python_executable).is_absolute()
    assert os.path.normpath(python_executable) == python_executable
    assert isinstance(python_version, str)
    version_match = re.fullmatch(r"(3)\.(11|12|13)\.[0-9]+", python_version)
    assert version_match is not None
    assert isinstance(dependencies, dict)
    assert set(dependencies) == EXPECTED_RUNTIME_DEPENDENCIES
    assert all(type(value) is str and value for value in dependencies.values())
    working_directory = command["working_directory"]
    assert isinstance(working_directory, str) and Path(working_directory).is_absolute()
    assert os.path.normpath(working_directory) == working_directory
    _assert_exact(
        command,
        {
            "exact_argv": [
                python_executable,
                "-B",
                runner_path,
            ],
            "working_directory": working_directory,
        },
    )

    model = bindings["model"]
    assert isinstance(model, dict)
    _assert_exact(
        launch["model"],
        {
            "id": model["id"],
            "revision": model["revision"],
            "file_sha256_and_sizes": model["files"],
        },
    )
    repository_projections = [
        artifacts["attempt_record"],
        artifacts["terminal_result"],
        artifacts["next_hypotheses"],
    ]
    required_absence = [
        artifacts["external_staging_path"],
        artifacts["external_store_path"],
        artifacts["external_next_hypotheses_path"],
        *repository_projections,
    ]
    _assert_exact(
        launch["artifacts"],
        {
            "external_staging_path": artifacts["external_staging_path"],
            "external_store_path": artifacts["external_store_path"],
            "external_next_hypotheses_path": artifacts["external_next_hypotheses_path"],
            "repository_projection_paths": repository_projections,
        },
    )
    _assert_exact(
        launch["absence_precondition"],
        {
            "coordinates_required_absent": required_absence,
            "runner_must_observe_absence_and_exclusively_start_in_same_process": True,
        },
    )
    _assert_exact(
        launch["resource_budget"],
        {
            "wall_clock_seconds_hard": budget["wall_clock_seconds_hard"],
            "model_loads_maximum": budget["model_loads_maximum"],
            "forward_batches_maximum": budget["forward_batches_maximum"],
            "byte_limits": {
                key: budget[key]
                for key in (
                    "raw_capture_bytes_hard",
                    "terminal_result_bytes_hard",
                    "next_hypotheses_bytes_hard",
                    "max_estimated_peak_bytes",
                )
            },
        },
    )
    _assert_exact(
        launch["authorizations"],
        {
            "operator_authorized_exact_one_attempt": True,
            "execution_authorized": True,
            "model_access_authorized": True,
        },
    )
    _assert_exact(
        launch["claim_boundary"],
        {
            key: claim[key]
            for key in (
                "claim_ceiling",
                "claim_delta",
                "milestone_credit",
                "evidence_eligible",
            )
        },
    )
    return runner_path, implementation_commit


def _synthetic_launch_document(freeze: dict[str, object]) -> dict[str, object]:
    contract = freeze["launch_authorization_contract"]
    bindings = freeze["bindings"]
    artifacts = freeze["artifact_coordinates"]
    route = freeze["route_amendment"]
    budget = freeze["resource_budget"]
    claim = freeze["claim_boundary"]
    assert all(
        isinstance(item, dict)
        for item in (contract, bindings, artifacts, route, budget, claim)
    )
    assert isinstance(contract, dict)
    assert isinstance(bindings, dict)
    assert isinstance(artifacts, dict)
    assert isinstance(route, dict)
    assert isinstance(budget, dict)
    assert isinstance(claim, dict)
    frame = bindings["fundamental_frame"]
    policy = bindings["policy_documents"]
    model = bindings["model"]
    assert isinstance(frame, dict)
    assert isinstance(policy, list) and len(policy) == 3
    assert all(isinstance(item, dict) for item in policy)
    assert isinstance(model, dict)
    runner_path = artifacts["prospective_runner_path"]
    assert isinstance(runner_path, str)
    python_executable = "/opt/spirallens-python/bin/python3"
    working_directory = "/opt/spirallens-repository"
    fixed = contract["required_fixed_values"]
    assert isinstance(fixed, dict)
    return {
        "schema_version": fixed["schema_version"],
        "launch_id": fixed["launch_id"],
        "attempt_id": fixed["attempt_id"],
        "decision_date": freeze["decision"]["decision_date"],
        "status": fixed["status"],
        "execution_class": route["execution_class"],
        "freeze": {
            "path": FREEZE_PATH.relative_to(ROOT).as_posix(),
            "source_sha256": _sha256(FREEZE_PATH),
            "freeze_id": freeze["freeze_id"],
        },
        "context_bank": copy.deepcopy(bindings["context_bank"]),
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
            "path": runner_path,
            "source_sha256": _sha256(ROOT / runner_path),
            "implementation_commit": "a" * 40,
        },
        "command": {
            "exact_argv": [python_executable, "-B", runner_path],
            "working_directory": working_directory,
        },
        "runtime": {
            "python_executable": python_executable,
            "python_version": "3.13.0",
            "dependency_versions": {
                name: f"synthetic-{index}"
                for index, name in enumerate(sorted(EXPECTED_RUNTIME_DEPENDENCIES))
            },
        },
        "model": {
            "id": model["id"],
            "revision": model["revision"],
            "file_sha256_and_sizes": copy.deepcopy(model["files"]),
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
            "wall_clock_seconds_hard": budget["wall_clock_seconds_hard"],
            "model_loads_maximum": budget["model_loads_maximum"],
            "forward_batches_maximum": budget["forward_batches_maximum"],
            "byte_limits": {
                key: budget[key]
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
            key: claim[key]
            for key in (
                "claim_ceiling",
                "claim_delta",
                "milestone_credit",
                "evidence_eligible",
            )
        },
    }


def _mutate_launch_document(document: dict[str, object], case: str) -> None:
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
        document["runner"]["implementation_commit"] = "b" * 40
    elif case == "argv":
        document["command"]["exact_argv"] = []
    elif case == "working_directory":
        document["command"]["working_directory"] = "/tmp/../tmp"
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
    else:
        raise AssertionError(case)


@lru_cache
def _runtime_source_commit() -> str | None:
    state = "".join(
        "1" if os.path.lexists(path) else "0"
        for _coordinate, path in REPOSITORY_STATE_PATHS
    )
    assert state in ALLOWED_REPOSITORY_STATES
    if state == "0000":
        return None

    freeze = _load_json(FREEZE_PATH)
    launch = _load_json(LAUNCH_PATH, canonical=True)
    runner_path, implementation_commit = _validate_launch_document(freeze, launch)
    if state == "1000":
        return None

    attempt = _load_json(ATTEMPT_PATH, canonical=True)
    terminal = _load_json(TERMINAL_PATH, canonical=True)
    lifecycle = freeze["lifecycle"]
    launch_contract = freeze["launch_authorization_contract"]
    terminal_contract = freeze["terminal_result_contract"]
    assert isinstance(lifecycle, dict)
    assert isinstance(launch_contract, dict)
    assert isinstance(terminal_contract, dict)

    assert set(launch) == set(launch_contract["required_root_fields"])
    assert set(attempt) == set(lifecycle["attempt_record_contract"]["root_fields"])
    assert set(terminal) == set(terminal_contract["root_fields"])
    assert (
        attempt["schema_version"]
        == lifecycle["attempt_record_contract"]["schema_version"]
    )
    assert attempt["attempt_id"] == launch_contract["attempt_id"]
    assert attempt["launch_id"] == launch_contract["launch_id"]
    _assert_exact(attempt["artifact_coordinates"], freeze["artifact_coordinates"])
    _assert_exact(attempt["resource_budget"], freeze["resource_budget"])
    _assert_exact(attempt["claim_boundary"], freeze["claim_boundary"])

    bindings = attempt["bindings"]
    assert isinstance(bindings, dict)
    assert set(bindings) == set(lifecycle["attempt_record_required_bindings"])
    runtime_commit = _assert_commit(bindings["runtime_source_commit"])
    _assert_ancestor(runtime_commit, "HEAD")
    assert bindings["launch_authorization_sha256"] == _sha256(LAUNCH_PATH)
    assert bindings["freeze_source_sha256"] == _sha256(FREEZE_PATH)
    assert bindings["context_bank_source_sha256"] == _sha256(BANK_PATH)
    assert (
        bindings["context_bank_canonical_sha256"]
        == freeze["bindings"]["context_bank"]["canonical_sha256"]
    )
    assert bindings["route_source_sha256"] == _sha256(ROUTE_PATH)
    _assert_exact(bindings["exact_argv"], launch["command"]["exact_argv"])
    _assert_exact(bindings["runtime_versions"], launch["runtime"])
    _assert_exact(
        bindings["expected_model_file_sha256_and_sizes"],
        launch["model"]["file_sha256_and_sizes"],
    )
    _assert_exact(
        bindings["all_external_and_repository_coordinates"],
        freeze["artifact_coordinates"],
    )
    _assert_exact(bindings["resource_budget"], freeze["resource_budget"])
    _assert_exact(bindings["claim_boundary"], freeze["claim_boundary"])

    runner = launch["runner"]
    assert isinstance(runner, dict)
    current_runner = ROOT / runner_path
    runner_sha256 = _sha256(current_runner)
    _assert_ancestor(implementation_commit, runtime_commit)
    assert bindings["runner_source_sha256"] == runner_sha256
    assert bindings["runner_implementation_commit"] == implementation_commit
    assert _git_blob(implementation_commit, runner_path) == current_runner.read_bytes()
    assert _git_blob(runtime_commit, runner_path) == current_runner.read_bytes()

    launch_relative = LAUNCH_PATH.relative_to(ROOT).as_posix()
    assert _git_blob(runtime_commit, launch_relative) == LAUNCH_PATH.read_bytes()
    for _coordinate, path in REPOSITORY_STATE_PATHS[1:]:
        assert not _git_blob_exists(runtime_commit, path.relative_to(ROOT).as_posix())
    provenance = terminal["provenance"]
    assert isinstance(provenance, dict)
    assert set(provenance) == set(terminal_contract["provenance_fields"])
    assert terminal["schema_version"] == terminal_contract["schema_version"]
    assert terminal["freeze_id"] == freeze["freeze_id"]
    assert terminal["launch_id"] == launch_contract["launch_id"]
    assert terminal["attempt_id"] == launch_contract["attempt_id"]
    _assert_exact(terminal["claim_boundary"], freeze["claim_boundary"])
    assert provenance["runtime_source_commit"] == runtime_commit
    assert provenance["runner_path"] == runner_path
    assert provenance["runner_source_sha256"] == runner_sha256
    assert provenance["launch_authorization_sha256"] == _sha256(LAUNCH_PATH)
    assert provenance["attempt_record_sha256"] == _sha256(ATTEMPT_PATH)
    assert provenance["freeze_source_sha256"] == _sha256(FREEZE_PATH)
    assert provenance["context_bank_source_sha256"] == _sha256(BANK_PATH)
    assert (
        provenance["context_bank_canonical_sha256"]
        == freeze["bindings"]["context_bank"]["canonical_sha256"]
    )
    assert provenance["route_source_sha256"] == _sha256(ROUTE_PATH)
    assert provenance["model_id"] == launch["model"]["id"]
    assert provenance["model_revision"] == launch["model"]["revision"]
    _assert_exact(
        provenance["expected_model_file_sha256_and_sizes"],
        launch["model"]["file_sha256_and_sizes"],
    )
    _assert_exact(
        provenance["python_executable"], launch["runtime"]["python_executable"]
    )
    _assert_exact(provenance["python_version"], launch["runtime"]["python_version"])
    _assert_exact(
        provenance["dependency_versions"],
        launch["runtime"]["dependency_versions"],
    )
    _assert_exact(provenance["exact_argv"], launch["command"]["exact_argv"])
    _assert_exact(
        provenance["working_directory"], launch["command"]["working_directory"]
    )
    return runtime_commit


def _binding_sha256(path: Path) -> str:
    live = path.read_bytes()
    runtime_commit = _runtime_source_commit()
    if runtime_commit is None:
        return hashlib.sha256(live).hexdigest()
    relative = path.relative_to(ROOT).as_posix()
    historical = _git_blob(runtime_commit, relative)
    if relative in POLICY_DOCUMENT_PATHS:
        return hashlib.sha256(historical).hexdigest()
    assert live == historical
    return hashlib.sha256(live).hexdigest()


def _git_blob_exists(commit: str, path: str) -> bool:
    completed = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}:{path}"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return completed.returncode == 0


def _fold(states: tuple[str, ...]) -> str:
    if "fail" in states:
        return "fail"
    if "insufficient" in states or "not_run" in states:
        return "insufficient"
    assert states and set(states) == {"pass"}
    return "pass"


def _fold_cells(states: tuple[str, ...]) -> str:
    if "fail" in states:
        return "fail"
    if "insufficient" in states:
        return "insufficient"
    if states and set(states) == {"not_run"}:
        return "not_run"
    if states and set(states) == {"pass"}:
        return "pass"
    assert states and set(states) == {"pass", "not_run"}
    return "insufficient"


def test_freeze_binds_new_discovery_inputs_and_pre_access_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for path, (size, digest) in (
        (BANK_PATH, EXPECTED_BANK_SOURCE),
        (ROUTE_PATH, EXPECTED_ROUTE_SOURCE),
        (FREEZE_PATH, EXPECTED_FREEZE_SOURCE),
    ):
        assert path.stat().st_size == size
        assert _binding_sha256(path) == digest
    freeze = _load_json(FREEZE_PATH)
    assert set(freeze) == EXPECTED_ROOT_KEYS
    assert freeze["schema_version"] == (
        "spirallens.pythia70-gate-state-development-freeze.v0.1"
    )
    assert freeze["freeze_id"] == "pythia70-gate-state-development-v0.1"
    assert freeze["status"] == "frozen_not_run"

    decision = freeze["decision"]
    assert isinstance(decision, dict)
    assert decision == {
        "decision_date": "2026-08-14",
        "purpose": "bounded_negative_space_reconnaissance",
        "reason": (
            "open_one_claim_ineligible_development_lane_before_further_"
            "instrument_hardening"
        ),
        "development_only": True,
        "operator_attests_no_values_from_exact_new_observation_cells_accessed_before_freeze": True,
        "operator_prior_pythia70_outcome_exposure": True,
        "operator_attests_prior_outcome_values_not_used_to_select_new_contexts_formulas_graphs_or_thresholds": True,
        "cryptographic_unseen_proof": False,
        "outcome_conditioned_design_change_allowed": False,
    }
    assert freeze["chronology"] == {
        "novelty_projection_fields": [
            "model_revision",
            "context_input_sha256",
            "token_id",
            "layer_id",
            "capture_stage",
        ],
        "ordered_observation_ids_schema_version": "spirallens.observation-key.v1",
        "ordered_observation_ids_fields": [
            "schema_version",
            "model_id",
            "resolved_model_revision",
            "context_bank_sha256",
            "context_id",
            "context_role",
            "context_spec_sha256",
            "swept_token_id",
            "model_vocab_size",
            "tokenizer_addressable_size",
            "sweep_domain",
            "tokenizer_addressable",
            "sweep_position",
            "observation_position",
            "layer_index",
            "capture_stage",
        ],
        "expected_numeric_observation_cells": 4704,
        "expected_cell_product": (
            "8_contexts_times_49_tokens_times_6_layers_times_2_capture_stages"
        ),
        "observation_id_order": (
            "context_then_token_id_then_layer_id_then_resid_pre_resid_post"
        ),
        "ordered_observation_ids_sha256": (
            "47f70433a79542363675754e24d594b3b9bb2dd4f41ec78d0daccb4da411b441"
        ),
        "exact_new_context_input_sha256_overlap_with_public_example_bank": 0,
        "exact_new_numeric_observation_projection_overlap_with_public_example_bank": 0,
        "model_token_layer_axes_overlap_historical_pythia70_work": True,
        "operator_prior_pythia70_outcome_exposure": True,
        "operator_attests_prior_outcome_values_not_used_as_numeric_or_design_inputs": True,
        "cryptographic_unseen_proof": False,
        "exact_new_observation_value_access_under_this_freeze": False,
        "future_launch_must_bind_absence_and_exclusive_start_before_access": True,
    }
    assert freeze["route_amendment"] == {
        "path": "protocols/pythia70_gate_state_reconnaissance_route_v0_1.json",
        "source_sha256": _binding_sha256(ROUTE_PATH),
        "route_id": "pythia70-claim-ineligible-gate-state-reconnaissance-v0.1",
        "execution_class": "claim_ineligible_gate_state_reconnaissance",
        "relationship_to_voy_strict_route": (
            "parallel_development_lane_no_route_progress"
        ),
        "relationship_to_public_example_engineering": (
            "separate_context_identity_and_consumer_contract_no_artifact_reuse"
        ),
        "fundamental_frame_change_control": (
            "dated_ledger_amendment_without_rewriting_canonical_frame_bytes"
        ),
        "public_example_consumer_allowlist_changed": False,
        "current_execution_authorized": False,
        "separate_launch_authorization_required": True,
        "maximum_future_attempts": 1,
    }

    bindings = freeze["bindings"]
    assert isinstance(bindings, dict)
    baseline = bindings["pre_access_baseline_commit"]
    assert baseline == "3ad376e1162c78be739890ed3f69987f677bf84c"
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", baseline, "HEAD"],
        cwd=ROOT,
        check=True,
    )
    for relative in freeze["artifact_coordinates"].values():
        if isinstance(relative, str) and relative.startswith(("runs/", "experiments/")):
            assert not _git_blob_exists(baseline, relative)

    expected_sources = {
        "candidate_registry": "protocols/order_parameter_hypothesis_registry_v0_1.yaml",
        "referent_contract_set": "protocols/order_parameter_referent_contracts_v0_1.json",
        "numeric_reference_implementation": "src/spirallens/referents/numeric.py",
        "strict_route": "protocols/voy_v1_v9_strict_successor_route_v0_1.json",
        "claim_ladder": "docs/claim_ladder.md",
        "fundamental_frame": "docs/FUNDAMENTAL_FRAME.md",
    }
    for key, relative in expected_sources.items():
        binding = bindings[key]
        assert isinstance(binding, dict) and binding["path"] == relative
        assert binding["source_sha256"] == _binding_sha256(ROOT / relative)
    assert bindings["policy_documents"] == [
        {
            "path": "docs/EXPERIMENT_INTERPRETATION_LEDGER.md",
            "source_sha256": _binding_sha256(
                ROOT / "docs/EXPERIMENT_INTERPRETATION_LEDGER.md"
            ),
        },
        {
            "path": "docs/ROADMAP.md",
            "source_sha256": _binding_sha256(ROOT / "docs/ROADMAP.md"),
        },
        {
            "path": "docs/NEXT_EXPERIMENT_PREPARATION.md",
            "source_sha256": _binding_sha256(
                ROOT / "docs/NEXT_EXPERIMENT_PREPARATION.md"
            ),
        },
    ]
    assert bindings["public_example_comparator"] == {
        "path": "protocols/context_bank_example_v0_1.yaml",
        "source_sha256": _binding_sha256(PUBLIC_BANK_PATH),
        "canonical_sha256": load_context_bank(
            PUBLIC_BANK_PATH,
            allowed_roles={ContextRole.EXAMPLE},
        ).canonical_sha256,
        "bank_id": "pythia70-project-synthetic-example-v0.1",
        "comparison_only": True,
        "artifact_reuse_or_consumer_authority": False,
    }
    assert bindings["numeric_reference_implementation"]["required_callables"] == [
        "derive_f2_section",
        "derive_f4_spin_two",
        "validate_observation_partition",
    ]
    reference_bindings = bindings["graph_and_transport_reference_implementations"]
    assert [binding["path"] for binding in reference_bindings] == [
        "src/spirallens/graphs/common.py",
        "src/spirallens/graphs/contracts.py",
        "src/spirallens/graphs/constructors.py",
        "src/spirallens/gauge/procrustes_connection.py",
        "src/spirallens/holonomy/discrete.py",
        "src/spirallens/holonomy/metrics.py",
        "src/spirallens/topology/winding.py",
    ]
    for binding in reference_bindings:
        assert binding["source_sha256"] == _binding_sha256(ROOT / binding["path"])

    assert bindings["model"] == {
        "id": "EleutherAI/pythia-70m",
        "revision": "a39f36b100fe8a5377810d56c3f4789b9c53ac42",
        "architecture": "GPTNeoXForCausalLM",
        "num_layers": 6,
        "hidden_size": 512,
        "vocab_size": 50304,
        "files": {
            "config.json": {
                "sha256": "002050231a9b1ec3ac77aa6b9b3bbdc4d923f4068a7dd33b8da72a9bd6ad9a43",
                "size_bytes": 567,
            },
            "model.safetensors": {
                "sha256": "ebfa4e2f18696ebd83716a0d39fe2c025f2ff8483f72a83ca59c475692fc9d15",
                "size_bytes": 166029852,
            },
        },
    }

    registry = yaml.safe_load(
        (ROOT / expected_sources["candidate_registry"]).read_text(encoding="utf-8")
    )
    assert isinstance(registry, dict)
    registry_candidates = registry["hypotheses"]
    assert isinstance(registry_candidates, list)
    assert {candidate["hypothesis_id"] for candidate in registry_candidates} >= {
        "f2_local_covariant_section",
        "f4_spin_two_anisotropy",
    }
    assert registry["winner_selected"] is False
    assert bindings["candidate_registry"]["candidate_ids"] == ["F2", "F4"]
    assert bindings["candidate_registry"]["registry_hypothesis_ids"] == [
        "f2_local_covariant_section",
        "f4_spin_two_anisotropy",
    ]
    assert bindings["candidate_registry"]["winner_selected"] is False
    assert bindings["candidate_registry"]["candidate_advance_authorized"] is False

    synthetic_launch = _synthetic_launch_document(freeze)

    def synthetic_commit(value: object) -> str:
        assert value == "a" * 40
        assert isinstance(value, str)
        return value

    def synthetic_blob(commit: str, path: str) -> bytes:
        assert commit == "a" * 40
        assert path == freeze["artifact_coordinates"]["prospective_runner_path"]
        return (ROOT / path).read_bytes()

    monkeypatch.setitem(globals(), "_assert_commit", synthetic_commit)
    monkeypatch.setitem(globals(), "_assert_ancestor", lambda _one, _two: None)
    monkeypatch.setitem(globals(), "_git_blob", synthetic_blob)
    assert _validate_launch_document(freeze, synthetic_launch) == (
        freeze["artifact_coordinates"]["prospective_runner_path"],
        "a" * 40,
    )
    launch_adversaries = (
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
    )
    for case in launch_adversaries:
        forged = copy.deepcopy(synthetic_launch)
        _mutate_launch_document(forged, case)
        with pytest.raises((AssertionError, KeyError, TypeError, ValueError)):
            _validate_launch_document(freeze, forged)

    junk_launch = tmp_path / "junk-launch.json"
    junk_launch.write_bytes(b"{}\n")
    launch_target = tmp_path / "launch-target.json"
    launch_target.write_bytes(b"{}\n")
    symlink_launch = tmp_path / "symlink-launch.json"
    symlink_launch.symlink_to(launch_target)
    missing = tuple(tmp_path / f"missing-{index}.json" for index in range(3))
    for candidate in (junk_launch, symlink_launch):
        monkeypatch.setitem(globals(), "LAUNCH_PATH", candidate)
        monkeypatch.setitem(
            globals(),
            "REPOSITORY_STATE_PATHS",
            (
                ("launch_authorization", candidate),
                ("attempt_record", missing[0]),
                ("terminal_result", missing[1]),
                ("next_hypotheses", missing[2]),
            ),
        )
        _runtime_source_commit.cache_clear()
        with pytest.raises(AssertionError):
            _runtime_source_commit()
    _runtime_source_commit.cache_clear()


def test_route_amendment_is_versioned_and_grants_no_execution_or_stage_credit() -> None:
    route = _load_json(ROUTE_PATH)
    assert set(route) == {
        "schema_version",
        "route_id",
        "status",
        "decision_date",
        "execution_class",
        "base_strict_route",
        "fundamental_frame",
        "frozen_surface",
        "route_semantics",
        "authorization",
        "forbidden_progress",
        "claim_boundary",
    }
    assert route["schema_version"] == (
        "spirallens.pythia70-gate-state-reconnaissance-route.v0.1"
    )
    assert route["route_id"] == (
        "pythia70-claim-ineligible-gate-state-reconnaissance-v0.1"
    )
    assert route["status"] == "frozen_not_authorized"
    assert route["execution_class"] == ("claim_ineligible_gate_state_reconnaissance")
    base = route["base_strict_route"]
    assert base["source_sha256"] == _binding_sha256(ROOT / base["path"])
    frame = route["fundamental_frame"]
    assert frame["source_sha256"] == _binding_sha256(ROOT / frame["path"])
    assert frame["canonical_bytes_rewritten"] is False
    assert frame["ledger_source_sha256"] == _binding_sha256(
        ROOT / frame["ledger_amendment_path"]
    )
    surface = route["frozen_surface"]
    assert surface["gate_ids"] == list(EXPECTED_GATES)
    assert surface["numeric_observation_cells"] == 4704
    assert surface["gate_state_cells"] == 894
    assert surface["maximum_attempts"] == 1
    assert surface["network_access"] is False
    assert route["route_semantics"] == {
        "ledger_3_15_rejected_model_free_exploratory_alternative_reinterpreted": False,
        "discovery_role_is_a_non_scientific_storage_and_access_classification": True,
        "discovery_role_is_SCI_S2_admission": False,
        "route_local_diagnostic_exception_only": True,
        "qualification_and_scientific_graph_estimator_threshold_lift_trivialization_and_reference_choices_remain_unresolved_outside_this_identity": True,
        "public_example_consumer_allowlist_changed": False,
        "public_example_artifact_reuse_allowed": False,
    }
    assert route["authorization"]["execution_authorized_by_route_freeze"] is False
    assert route["authorization"]["model_access_authorized_by_route_freeze"] is False
    assert all(route["forbidden_progress"].values())
    assert route["claim_boundary"] == {
        "claim_ceiling": "level_0",
        "claim_delta": "none",
        "milestone_credit": "none",
        "evidence_eligible": False,
        "development_pass_has_scientific_effect": False,
        "negative_space_map_is_next_hypothesis_input_only": True,
    }


def test_context_bank_is_exact_discovery_pair_and_not_public_example_relabel() -> None:
    freeze = _load_json(FREEZE_PATH)
    binding = freeze["bindings"]["context_bank"]
    loaded = load_context_bank(BANK_PATH, allowed_roles={ContextRole.DISCOVERY})
    public = load_context_bank(PUBLIC_BANK_PATH, allowed_roles={ContextRole.EXAMPLE})

    assert binding == {
        "path": "protocols/context_bank_pythia70_gate_state_v0_1.yaml",
        "source_sha256": loaded.source_sha256,
        "canonical_sha256": loaded.canonical_sha256,
        "bank_id": loaded.bank.bank_id,
        "status": "frozen",
        "role": "discovery",
        "claim_eligible": False,
    }
    assert loaded.bank.claim_eligible is False
    model_binding = freeze["bindings"]["model"]
    assert loaded.bank.model.model_id == model_binding["id"]
    assert loaded.bank.model.resolved_revision == model_binding["revision"]
    assert loaded.bank.model.vocab_size == model_binding["vocab_size"]
    assert tuple(context.context_id for context in loaded.bank.contexts) == (
        EXPECTED_CONTEXT_IDS
    )
    assert freeze["input_plan"]["contexts"] == {
        "ordered_ids": list(EXPECTED_CONTEXT_IDS),
        "fit_indices": [0, 2, 4, 6],
        "evaluation_indices": [1, 3, 5, 7],
        "context_reuse_between_splits": False,
        "contexts_are_independent_semantic_populations": False,
        "contexts_are_repeated_measurements_not_independent_replications": True,
    }
    assert {context.input_sha256 for context in loaded.bank.contexts}.isdisjoint(
        context.input_sha256 for context in public.bank.contexts
    )
    new_projection = {
        (
            loaded.bank.model.resolved_revision,
            context.input_sha256,
            token_id,
            layer_id,
            stage.value,
        )
        for context in loaded.bank.contexts
        for token_id in range(49)
        for layer_id in range(6)
        for stage in (CaptureStage.RESID_PRE, CaptureStage.RESID_POST)
    }
    public_projection = {
        (
            public.bank.model.resolved_revision,
            context.input_sha256,
            token_id,
            layer_id,
            stage.value,
        )
        for context in public.bank.contexts
        for token_id in range(49)
        for layer_id in range(6)
        for stage in (CaptureStage.RESID_PRE, CaptureStage.RESID_POST)
    }
    assert new_projection.isdisjoint(public_projection)
    assert all(
        {value for value in context.template_ids if value is not None}.isdisjoint(
            range(49)
        )
        for context in loaded.bank.contexts
    )
    observation_ids = [
        loaded.bank.observation_key(
            context_id=context.context_id,
            role=ContextRole.DISCOVERY,
            swept_token_id=token_id,
            layer_index=layer_id,
            capture_stage=stage,
        ).observation_id
        for context in loaded.bank.contexts
        for token_id in range(49)
        for layer_id in range(6)
        for stage in (CaptureStage.RESID_PRE, CaptureStage.RESID_POST)
    ]
    observation_digest = hashlib.sha256(
        ("\n".join(observation_ids) + "\n").encode("utf-8")
    ).hexdigest()
    assert len(observation_ids) == 4704
    assert observation_digest == freeze["chronology"]["ordered_observation_ids_sha256"]


def test_value_free_derivation_graph_and_artificial_ring_plan_is_exact() -> None:
    freeze = _load_json(FREEZE_PATH)
    input_plan = freeze["input_plan"]
    token_selection = input_plan["token_selection"]
    token_ids = np.arange(49, dtype="<i8")
    assert token_selection["token_ids"] == token_ids.tolist()
    assert token_selection["token_ids_little_endian_int64_sha256"] == (
        hashlib.sha256(token_ids.tobytes(order="C")).hexdigest()
    )
    assert token_selection["decoded_strings_used"] is False
    assert token_selection["semantic_selection_used"] is False
    assert token_selection["seven_by_seven_geometry_inferred"] is False
    assert input_plan["capture"] == {
        "layer_ids": [0, 1, 2, 3, 4, 5],
        "capture_stages": ["resid_pre", "resid_post"],
        "layers_count_as_independent_replicates": False,
        "hidden_coordinate_slice": [0, 512],
        "hidden_coordinates_used": 512,
        "coordinate_truncation_used": False,
        "dtype": "float32",
        "device": "cpu",
        "batch_size": 7,
        "network_access": False,
        "local_files_only": True,
    }

    derivation = freeze["derivation_plan"]
    assert derivation["state"] == {
        "formula": (
            "arithmetic_mean_of_exact_four_fit_context_resid_pre_rows_then_"
            "subtract_layer_token_row_mean_then_rowwise_l2_normalize"
        ),
        "zero_norm_policy": (
            "if_any_row_norm_is_at_or_below_epsilon_no_row_is_dropped_or_zero_"
            "filled_and_all_graph_dependent_cells_for_that_layer_are_insufficient"
        ),
    }
    assert derivation["response"] == {
        "formula": "resid_post_minus_resid_pre",
        "split_reduction": (
            "arithmetic_mean_of_the_exact_four_context_responses_in_that_split"
        ),
        "consumer_scopes": {
            "global_reference_frame": (
                "fit_split_arithmetic_mean_response_per_token_for_that_layer_only"
            ),
            "F2": "requested_split_arithmetic_mean_response_per_token",
            "measurable_drift": ("requested_split_arithmetic_mean_response_per_token"),
            "local_frame": "all_exact_four_fit_context_response_rows_unreduced",
            "F4": (
                "all_exact_four_context_response_rows_for_the_requested_split_unreduced"
            ),
        },
        "fit_and_evaluation_splits_remain_separate": True,
        "cross_split_pooling_allowed": False,
    }
    fit_identities = np.column_stack(
        (token_ids, *(np.full(49, index, dtype="<i8") for index in (0, 2, 4, 6)))
    ).astype("<i8")
    evaluation_identities = np.column_stack(
        (token_ids, *(np.full(49, index, dtype="<i8") for index in (1, 3, 5, 7)))
    ).astype("<i8")
    partition = validate_observation_partition(
        fit_identities,
        evaluation_identities,
        row_identity_column=0,
    )
    assert derivation["observation_partition"] == {
        "row_identity_source": "input_plan.token_selection.token_ids",
        "row_identity_column": 0,
        "identity_width": 5,
        "fit_identity_matrix_formula": (
            "rows_equal_[token_id,0,2,4,6]_for_token_ids_0_through_48_dtype_"
            "little_endian_int64"
        ),
        "evaluation_identity_matrix_formula": (
            "rows_equal_[token_id,1,3,5,7]_for_token_ids_0_through_48_dtype_"
            "little_endian_int64"
        ),
        "fit_identity_matrix_raw_sha256": hashlib.sha256(
            fit_identities.tobytes(order="C")
        ).hexdigest(),
        "evaluation_identity_matrix_raw_sha256": hashlib.sha256(
            evaluation_identities.tobytes(order="C")
        ).hexdigest(),
        "call": (
            "partition=validate_observation_partition(fit_identity_matrix,"
            "evaluation_identity_matrix,row_identity_column=0)"
        ),
        "expected_partition_canonical_sha256": partition.canonical_sha256,
        "partition_proves_estimator_read_behavior": False,
    }
    f2 = derivation["F2"]
    assert set(f2) == {
        "registry_name",
        "canonical_local_section",
        "fit_in_sample_diagnostic",
        "development_trivialized_section",
        "consumer_bindings",
        "fit_and_evaluation_values_both_computed",
        "per_token_derived_values_persisted",
        "split_semantics",
        "field_status",
    }
    assert f2["registry_name"] == "f2_local_covariant_section"
    assert f2["canonical_local_section"] == {
        "symbol": "z",
        "split": "evaluation_only",
        "formula": (
            "z_evaluation=derive_f2_section(local_frames=U,evaluation_"
            "responses=s_evaluation,partition=partition,input_row_identities="
            "token_ids,amplitude_floor=1e-8).values"
        ),
        "amplitude_id": "f2_local_z_l2",
        "amplitude_formula": "sqrt(z0^2+z1^2)",
        "direction_formula": (
            "z_divided_by_amplitude_when_amplitude_strictly_greater_than_floor"
        ),
        "cross_vertex_phase_authorized": False,
    }
    assert f2["fit_in_sample_diagnostic"] == {
        "formula": "z_fit=U_transpose_times_s_fit_without_calling_derive_f2_section",
        "role": "in_sample_selection_diagnostic_not_referent_contract",
        "canonical_referent_claim": False,
    }
    assert f2["development_trivialized_section"] == {
        "symbol": "w",
        "formula": "w_i_split=B_transpose_times_U_i_times_z_i_split",
        "amplitude_id": "f2_development_w_l2",
        "amplitude_formula": "sqrt(w0^2+w1^2)",
        "direction_formula": (
            "w_divided_by_amplitude_when_amplitude_strictly_greater_than_floor"
        ),
        "complex_encoding": "w0+1j*w1",
        "canonical_local_f2_coordinate": False,
        "projection_is_norm_preserving": False,
        "basis_dependent_development_reference_only": True,
    }
    assert f2["consumer_bindings"] == {
        "f2_section_support": "f2_local_z_l2",
        "low_amplitude_set_repeatability": "f2_development_w_l2",
        "address_loop_support": "f2_development_w_l2",
        "address_ring_phase_resolution": "f2_development_w_complex",
        "negative_controls": "f2_development_w_complex",
    }
    assert f2["split_semantics"] == {
        "fit": "in_sample_selection_diagnostic_not_referent_contract",
        "evaluation": "cross_fit_referent_bound",
    }
    assert f2["fit_and_evaluation_values_both_computed"] is True
    assert f2["per_token_derived_values_persisted"] is False
    f4 = derivation["F4"]
    assert set(f4) == {
        "registry_name",
        "sample_set",
        "centering",
        "weights",
        "covariance_denominator",
        "derive_input",
        "traceless_tensor",
        "canonical_formula",
        "global_transport",
        "complex_encoding",
        "isotropic_policy",
        "reflection_policy",
        "fit_and_evaluation_values_both_computed",
        "per_token_derived_values_persisted",
        "same_tensor_amplitude_direction",
        "operation_order",
        "evaluation_call",
        "fit_in_sample_diagnostic",
        "split_semantics",
        "consumer_bindings",
        "field_status",
    }
    assert f4["registry_name"] == "f4_spin_two_anisotropy"
    assert f4["derive_input"] == "per_token_symmetric_covariance_before_detracing"
    assert f4["canonical_formula"] == {
        "real_component": "0.5*(T00-T11)",
        "imaginary_component": "T01",
    }
    assert f4["operation_order"] == [
        "project_exact_four_split_context_responses_into_frozen_local_frame",
        "subtract_exact_split_arithmetic_mean",
        "form_symmetric_covariance_dividing_by_three",
        "evaluation_only_call_derive_f4_spin_two_with_partition_token_ids_and_amplitude_floor",
        "take_returned_traceless_tensor",
        "transport_tensor_with_full_o2_Q_transpose_T_Q",
        "encode_real_half_diagonal_difference_and_imaginary_offdiagonal",
    ]
    assert f4["evaluation_call"] == (
        "derive_f4_spin_two(in_plane_symmetric_tensors=evaluation_covariance,"
        "partition=partition,input_row_identities=token_ids,amplitude_floor=1e-8)"
    )
    assert f4["fit_in_sample_diagnostic"] == {
        "formula": (
            "form_fit_covariance_then_detrace_then_apply_full_o2_Q_transpose_T_"
            "fit_Q_then_encode_without_calling_derive_f4_spin_two"
        ),
        "role": "in_sample_selection_diagnostic_not_referent_contract",
        "canonical_referent_claim": False,
    }
    assert f4["split_semantics"] == {
        "fit": "in_sample_selection_diagnostic_not_referent_contract",
        "evaluation": "cross_fit_referent_bound",
    }
    assert f4["sample_set"] == (
        "per_token_split_context_responses_projected_to_local_frame"
    )
    assert f4["centering"] == "subtract_per_token_split_context_mean"
    assert f4["weights"] == "uniform"
    assert f4["covariance_denominator"] == "context_count_minus_one"
    assert f4["traceless_tensor"] == (
        "covariance_minus_one_half_trace_times_identity_2"
    )
    assert f4["global_transport"] == (
        "T_global=Q_transpose_times_T_local_times_Q_where_Q_is_full_o2_"
        "procrustes_local_to_global"
    )
    assert f4["isotropic_policy"] == ("amplitude_at_or_below_floor_is_insufficient")
    assert f4["consumer_bindings"] == {
        "f4_tensor_support": "f4_local_traceless_spin_two_l2",
        "low_amplitude_set_repeatability": "f4_global_traceless_spin_two_l2",
        "address_loop_support": "f4_global_traceless_spin_two_l2",
        "address_ring_phase_resolution": "f4_global_spin_two_complex",
        "negative_controls": "f4_global_spin_two_complex",
    }
    assert f4["field_status"] == "development_candidate_not_registry_advance"
    assert f4["fit_and_evaluation_values_both_computed"] is True
    assert f4["per_token_derived_values_persisted"] is False
    assert f4["same_tensor_amplitude_direction"] is True
    assert f4["complex_encoding"] == "0.5*(T00-T11)+1j*T01"
    assert f4["reflection_policy"] == (
        "retain_full_o2_transport_and_mark_orientation_unresolved_cells_insufficient"
    )
    assert derivation["low_amplitude_sets"] == {
        "score_by_candidate": {
            "F2": "f2_development_w_l2",
            "F4": "f4_global_traceless_spin_two_l2",
        },
        "candidate_count_per_candidate": 10,
        "F2_and_F4_candidate_sets_are_selected_separately": True,
        "selection_order": "ascending_amplitude_then_ascending_token_id",
        "fit_evaluation_jaccard_pass_floor": 0.3,
        "fit_evaluation_jaccard_fail_ceiling": 0.1,
        "ground_truth_or_charge_used": False,
        "claim": "low_amplitude_address_set_repeatability_only",
        "order_parameter_field_constructed": False,
        "core_score_constructed": False,
        "core_candidate_constructed": False,
        "singular_set_localized": False,
    }
    procrustes = derivation["procrustes_plan"]
    assert set(procrustes) == {
        "require_proper_rotation",
        "global_alignment",
        "edge_transport",
        "orientation",
        "support_scope_by_gate",
    }
    assert procrustes["require_proper_rotation"] is False
    assert procrustes["global_alignment"] == {
        "call": (
            "Q_i=procrustes_connection(source_frame=U_i,target_frame=B,"
            "require_proper_rotation=False).rotation"
        ),
        "identity": "U_i_times_Q_i_approximates_B",
        "f2_global_projection": "w_i=B_transpose_times_U_i_times_z_i",
        "local_tensor_to_global": (
            "T_global_i=Q_i_transpose_times_T_local_i_times_Q_i"
        ),
        "minimum_singular_value_inclusive": 1e-6,
        "below_floor_state": "insufficient",
        "residual_frobenius_computed_but_not_persisted": True,
        "residual_threshold_applied": False,
        "reflection_retained": True,
        "required_by_gate_ids": [
            "low_amplitude_set_repeatability",
            "address_loop_support",
            "address_ring_phase_resolution",
            "graph_family_agreement",
            "negative_controls",
        ],
    }
    assert procrustes["edge_transport"] == {
        "call": (
            "T_i_to_j=procrustes_connection(source_frame=U_j,target_frame=U_i,"
            "require_proper_rotation=False).rotation"
        ),
        "coordinate_law": "z_j=T_i_to_j_times_z_i",
        "minimum_singular_value_inclusive": 1e-6,
        "below_floor_state": "insufficient",
        "reverse_call": (
            "T_j_to_i=procrustes_connection(source_frame=U_i,target_frame=U_j,"
            "require_proper_rotation=False).rotation"
        ),
        "reverse_recomputed_from_frames": True,
        "forward_inverse_reuse_for_reverse_forbidden": True,
        "path_order": "compose_edge_transports_in_declared_ring_edge_order",
        "required_by_gate_ids": [
            "address_loop_support",
            "continuous_holonomy_consistency",
            "address_ring_phase_resolution",
            "negative_controls",
        ],
    }
    assert procrustes["orientation"] == {
        "cycle_sign": "sign_of_determinant_of_composed_edge_transport",
        "negative_cycle_state": "insufficient",
        "per_edge_reflection_forced_to_so2": False,
    }
    assert procrustes["support_scope_by_gate"] == {
        "low_amplitude_set_repeatability": (
            "select_candidate_specific_top10_only_from_vertices_with_supported_"
            "local_frame_supported_global_alignment_and_finite_candidate_"
            "amplitude_including_values_at_or_below_amplitude_floor_with_fewer_"
            "than_10_eligible_vertices_as_insufficient"
        ),
        "graph_family_agreement": (
            "each_of_exact_three_compared_candidate_sets_uses_the_same_local_"
            "frame_global_alignment_and_finite_amplitude_eligibility_with_any_"
            "family_below_10_as_insufficient"
        ),
        "address_loop_support": (
            "all_ring_vertices_must_meet_global_alignment_and_amplitude_floors_"
            "and_all_consecutive_closing_graph_edges_must_exist_and_meet_edge_"
            "alignment_floor_else_insufficient"
        ),
        "address_ring_phase_resolution": (
            "all_ring_vertices_must_meet_global_alignment_and_amplitude_floors_"
            "and_all_consecutive_closing_graph_edges_must_exist_and_meet_edge_"
            "alignment_floor_else_insufficient"
        ),
        "continuous_holonomy_consistency": (
            "all_consecutive_closing_graph_edges_must_exist_and_meet_edge_"
            "alignment_floor_and_composed_cycle_determinant_must_be_positive_"
            "else_insufficient"
        ),
        "negative_controls": (
            "forward_and_recomputed_reverse_cells_must_each_meet_the_same_"
            "vertex_edge_amplitude_branch_and_positive_orientation_"
            "prerequisites_else_insufficient"
        ),
        "orientation_scope": (
            "negative_composed_cycle_determinant_makes_continuous_holonomy_and_"
            "negative_control_cells_insufficient_but_does_not_by_itself_change_"
            "address_loop_or_global_address_phase_cells"
        ),
    }
    identifiability_rules = [
        {
            "metric": "sigma2_divided_by_sigma1",
            "formula": "sigma2/sigma1",
            "comparator": "greater_than_or_equal",
            "floor": 1e-6,
            "zero_denominator_state": "insufficient",
        },
        {
            "metric": "first_axis_relative_gap",
            "formula": "(sigma1-sigma2)/sigma1",
            "comparator": "greater_than_or_equal",
            "floor": 1e-6,
            "zero_denominator_state": "insufficient",
        },
        {
            "metric": "second_axis_relative_gap",
            "formula": "(sigma2-sigma3)/sigma2",
            "comparator": "greater_than_or_equal",
            "floor": 1e-6,
            "zero_denominator_state": "insufficient",
        },
    ]
    assert derivation["global_reference_frame"] == {
        "formula": (
            "top_two_right_singular_vectors_of_token_centered_mean_fit_response"
        ),
        "scope": (
            "one_separately_fitted_B_per_layer_id_shared_across_all_three_graph_"
            "families_both_candidates_and_both_splits"
        ),
        "input_response": (
            "arithmetic_mean_of_exact_four_fit_context_responses_per_token_for_"
            "that_layer"
        ),
        "evaluation_responses_used_for_frame_fit": False,
        "sign_rule": (
            "for_each_vector_make_largest_absolute_coordinate_positive_with_"
            "lowest_index_tie_break"
        ),
        "identifiability_rules": identifiability_rules,
        "axis_or_subspace_degeneracy_policy": "insufficient",
        "basis_dependent_development_reference_only": True,
    }
    assert derivation["local_frame"] == {
        "sample_set": (
            "self_then_graph_neighbors_sorted_by_ascending_token_id_cross_exact_"
            "four_fit_context_responses"
        ),
        "sample_row_order": (
            "self_then_neighbors_ascending_token_id_each_with_fit_context_"
            "indices_0_2_4_6"
        ),
        "sample_row_count_formula": "4_times_one_plus_graph_degree",
        "centering": (
            "subtract_arithmetic_mean_across_all_sample_rows_per_hidden_coordinate"
        ),
        "formula": (
            "top_two_right_singular_vectors_of_the_exact_centered_sample_row_matrix"
        ),
        "sign_rule": "same_as_global_reference_frame",
        "minimum_distinct_vertices_including_self": 3,
        "minimum_response_rows": 12,
        "evaluation_responses_used_for_frame_fit": False,
        "identifiability_rules": identifiability_rules,
        "axis_or_subspace_degeneracy_policy": "cell_insufficient",
        "unsupported_policy": "cell_insufficient",
    }

    graph = freeze["graph_plan"]
    assert graph == {
        "input": "full_512_coordinate_normalized_fit_state",
        "metric": "canonical_coordinate_order_euclidean_float64",
        "families": [
            {
                "family": "mutual-knn",
                "spec_id": "pythia70-dev-mutual-knn-k4",
                "purpose": "field-estimation",
                "neighbor_count": 4,
            },
            {
                "family": "fixed-radius",
                "spec_id": "pythia70-dev-fixed-radius-0.75",
                "purpose": "field-estimation",
                "radius": 0.75,
            },
            {
                "family": "shared-neighbor",
                "spec_id": "pythia70-dev-shared-neighbor-k6-s2",
                "purpose": "field-estimation",
                "neighbor_count": 6,
                "minimum_shared_neighbors": 2,
            },
        ],
        "graph_output_may_select_candidate": False,
        "graph_output_may_change_thresholds": False,
        "rings_are_graph_derived_or_selected_cycles": False,
        "ring_identity_fixed_independently_of_graph": True,
        "predeclared_ring_support_diagnostic": {
            "ring_identity_fixed_before_graph_construction": True,
            "candidate_graph_adjacency_required_for_each_consecutive_and_closing_pair": (
                True
            ),
            "missing_edge_count_formula": (
                "count_of_declared_consecutive_and_closing_pairs_absent_from_"
                "candidate_graph"
            ),
            "any_missing_edge_state": "insufficient",
            "alternative_cycle_search_allowed": False,
            "edge_procrustes_evaluated_only_after_all_adjacencies_exist": True,
            "all_adjacencies_present_meaning": (
                "predeclared_path_is_an_evaluable_cycle_in_that_candidate_graph_only"
            ),
            "discovered_or_selected_cycle_claim": False,
            "model_native_topology_claim": False,
        },
        "field_by_cycle_crossed_design_established": False,
        "consecutive_and_closing_ring_edges_required_for_holonomy": True,
    }

    baseline = freeze["address_grid_baseline"]
    assert baseline == {
        "role": "artificial_projection_dependent_null_baseline",
        "model_native_geometry": False,
        "topology_or_homology_claim": False,
        "row_major_shape": [7, 7],
        "rings": [
            {
                "ring_id": "address-ring-r1",
                "ordered_token_ids": [16, 17, 18, 25, 32, 31, 30, 23],
            },
            {
                "ring_id": "address-ring-r2",
                "ordered_token_ids": [
                    8,
                    9,
                    10,
                    11,
                    12,
                    19,
                    26,
                    33,
                    40,
                    39,
                    38,
                    37,
                    36,
                    29,
                    22,
                    15,
                ],
            },
            {
                "ring_id": "address-ring-r3",
                "ordered_token_ids": [
                    0,
                    1,
                    2,
                    3,
                    4,
                    5,
                    6,
                    13,
                    20,
                    27,
                    34,
                    41,
                    48,
                    47,
                    46,
                    45,
                    44,
                    43,
                    42,
                    35,
                    28,
                    21,
                    14,
                    7,
                ],
            },
        ],
        "reverse_control": "retain_first_vertex_then_reverse_remaining_order",
        "center_address_control_token_id": 24,
        "off_ring_loop_claimed": False,
        "nested_ring_comparison": "r1_r2_r3_are_separate_cells_not_replicates",
    }


def test_terminal_result_schema_is_exact_and_distinguishes_infrastructure() -> None:
    result = _load_json(FREEZE_PATH)["terminal_result_contract"]
    assert set(result) == {
        "schema_version",
        "encoding",
        "root_fields",
        "execution_terminal_values",
        "complete_requirements",
        "infrastructure_error_requirements",
        "required_value_joins",
        "provenance_fields",
        "provenance_value_sources",
        "chronology_rule",
        "utc_timestamp_format",
        "model_file_observation_contract",
        "capture_manifest",
        "graph_receipts",
        "gate_record_fields",
        "cell_record_fields_source",
        "cell_metric_fields_by_gate",
        "cell_metric_value_domains",
        "cell_metric_value_domain_rules",
        "cell_support_count_and_coverage",
        "gate_support_aggregation",
        "record_state_nullability",
        "resource_use_fields",
        "resource_use_contract",
        "error_record_fields",
        "error_stage_values",
        "post_terminal_failure_rules",
        "infrastructure_partial_prefix_rules",
        "failure_classification",
        "unknown_or_extra_root_nested_capture_graph_gate_cell_metric_provenance_resource_or_error_fields_allowed",
        "canonical_bytes_must_strict_reload_and_rerender_identically",
    }
    assert result["schema_version"] == (
        "spirallens.pythia70-gate-state-development-result.v0.1"
    )
    assert result["encoding"] == "canonical_json_utf8_with_one_final_lf"
    assert result["root_fields"] == [
        "schema_version",
        "freeze_id",
        "launch_id",
        "attempt_id",
        "execution_terminal",
        "started_at_utc",
        "finished_at_utc",
        "provenance",
        "capture_manifest",
        "graph_receipts",
        "gate_records",
        "cell_records",
        "terminal_fold",
        "resource_use",
        "claim_boundary",
        "error",
    ]
    assert result["execution_terminal_values"] == [
        "complete",
        "infrastructure_error",
    ]
    assert result["complete_requirements"] == [
        "error_is_null",
        "both_model_file_observation_slots_are_verified_and_equal_expected_sha256_and_sizes",
        "capture_manifest_has_exact_16_arrays",
        "graph_receipts_have_exact_18_constructed_or_insufficient_slots",
        "gate_records_have_exact_10_gate_ids_once_in_frozen_order",
        "cell_records_have_exact_894_cell_ids_once_in_frozen_order",
        "each_gate_record_state_support_coverage_cell_ids_digest_and_cell_records_digest_recompute_from_its_exact_manifest_cells",
        "terminal_fold_recomputes_from_gate_records",
        "resource_use_hard_limit_breaches_is_empty_and_all_observed_values_are_within_budget",
    ]
    assert result["infrastructure_error_requirements"] == [
        "error_record_is_required",
        "capture_graph_gate_and_cell_records_are_empty_or_exact_ordered_prefixes",
        "missing_or_partial_records_never_default_to_pass",
        "terminal_fold_is_null",
        "resource_budget_error_stage_requires_exact_nonempty_hard_limit_breaches_for_every_observed_excess",
    ]
    assert result["required_value_joins"] == {
        "freeze_id": "freeze_document.freeze_id",
        "launch_id": "launch_authorization_contract.launch_id",
        "attempt_id": (
            "launch_authorization_contract.attempt_id_and_lifecycle.attempt_"
            "record_contract.attempt_id"
        ),
        "provenance": (
            "exact_values_from_attempt_record_launch_authorization_root_"
            "bindings_and_runtime_observation"
        ),
        "capture_manifest": (
            "exact_context_stage_order_shape_dtype_and_paths_from_terminal_"
            "result_contract.capture_manifest"
        ),
        "graph_receipts": (
            "exact_layer_family_order_specs_and_canonical_receipts_from_graph_plan"
        ),
        "gate_records": (
            "exact_gate_order_states_and_cell_id_digests_from_gate_state_contract"
        ),
        "cell_records": (
            "exact_cell_order_axes_states_and_metric_keys_from_gate_state_"
            "contract_and_terminal_result_contract"
        ),
        "resource_use": (
            "actual_observed_values_and_exact_hard_limit_breaches_under_terminal_"
            "result_contract.resource_use_contract"
        ),
        "claim_boundary": "exactly_equal_freeze_document.claim_boundary",
        "error": ("null_for_complete_or_exact_error_record_for_infrastructure_error"),
    }
    assert result["capture_manifest"] == {
        "array_count": 16,
        "order": "context_then_resid_pre_resid_post",
        "relative_path_pattern": "raw-captures/{context_id}/{capture_stage}.npy",
        "array_shape": [49, 6, 512],
        "dtype": "<f4",
        "c_contiguous": True,
        "numpy_save_allow_pickle": False,
        "record_fields": [
            "relative_path",
            "context_id",
            "capture_stage",
            "shape",
            "dtype",
            "finite",
            "raw_array_sha256",
            "file_sha256",
            "size_bytes",
        ],
    }
    assert result["graph_receipts"] == {
        "record_count": 18,
        "order": "layer_then_mutual_knn_fixed_radius_shared_neighbor",
        "record_fields": [
            "layer_id",
            "graph_family",
            "spec_id",
            "status",
            "reason_codes",
            "receipt",
            "receipt_canonical_sha256",
        ],
        "status_values": ["constructed", "insufficient"],
        "constructed_requires_nonnull_receipt_and_matching_canonical_sha256": True,
        "insufficient_requires_null_receipt_and_digest_and_nonempty_reason_codes": True,
        "state_zero_norm_or_graph_input_normalization_support_failure_is_insufficient_nonconstruction": True,
        "downstream_frame_degeneracy_retains_constructed_graph_receipt_and_only_marks_dependent_cells_insufficient": True,
        "canonical_graph_constructor_exception_is_infrastructure_error": True,
    }
    assert result["provenance_fields"] == [
        "runtime_source_commit",
        "runner_path",
        "runner_source_sha256",
        "launch_authorization_sha256",
        "attempt_record_sha256",
        "freeze_source_sha256",
        "context_bank_source_sha256",
        "context_bank_canonical_sha256",
        "route_source_sha256",
        "model_id",
        "model_revision",
        "expected_model_file_sha256_and_sizes",
        "observed_model_file_slots",
        "python_executable",
        "python_version",
        "dependency_versions",
        "exact_argv",
        "working_directory",
    ]
    assert result["provenance_value_sources"] == {
        "runtime_source_commit": "attempt_record.bindings.runtime_source_commit",
        "runner_path": "launch_authorization.runner.path",
        "runner_source_sha256": "attempt_record.bindings.runner_source_sha256",
        "launch_authorization_sha256": (
            "attempt_record.bindings.launch_authorization_sha256"
        ),
        "attempt_record_sha256": (
            "strict_canonical_sha256_of_sibling_attempt_record_bytes"
        ),
        "freeze_source_sha256": "attempt_record.bindings.freeze_source_sha256",
        "context_bank_source_sha256": (
            "attempt_record.bindings.context_bank_source_sha256"
        ),
        "context_bank_canonical_sha256": (
            "attempt_record.bindings.context_bank_canonical_sha256"
        ),
        "route_source_sha256": "attempt_record.bindings.route_source_sha256",
        "model_id": "launch_authorization.model.id",
        "model_revision": "launch_authorization.model.revision",
        "expected_model_file_sha256_and_sizes": (
            "attempt_record.bindings.expected_model_file_sha256_and_sizes"
        ),
        "observed_model_file_slots": (
            "post_start_model_file_observation_contract_before_model_load"
        ),
        "python_executable": "launch_authorization.runtime.python_executable",
        "python_version": "launch_authorization.runtime.python_version",
        "dependency_versions": ("launch_authorization.runtime.dependency_versions"),
        "exact_argv": "launch_authorization.command.exact_argv",
        "working_directory": "launch_authorization.command.working_directory",
    }
    assert result["chronology_rule"] == (
        "attempt_record.started_at_utc_equals_terminal.started_at_utc_less_than_"
        "or_equal_terminal.finished_at_utc_and_for_infrastructure_error_terminal."
        "started_at_utc_less_than_or_equal_error.caught_at_utc_less_than_or_"
        "equal_terminal.finished_at_utc_while_complete_error_is_null"
    )
    assert result["utc_timestamp_format"] == (
        "rfc3339_utc_with_exactly_six_fractional_second_digits_and_Z_suffix"
    )
    assert result["model_file_observation_contract"] == {
        "order": ["config.json", "model.safetensors"],
        "record_fields": [
            "relative_name",
            "status",
            "size_bytes",
            "sha256",
            "error_type",
            "error_message",
        ],
        "status_values": [
            "verified",
            "mismatch",
            "missing",
            "read_error",
            "not_run",
        ],
        "verified_rule": (
            "size_bytes_and_sha256_nonnull_error_fields_null_and_equal_expected_"
            "before_model_load"
        ),
        "mismatch_rule": (
            "observed_size_bytes_and_sha256_nonnull_error_fields_null_and_at_"
            "least_one_differs_from_expected"
        ),
        "missing_rule": (
            "size_bytes_sha256_and_error_type_null_error_message_equals_file_missing"
        ),
        "read_error_rule": (
            "size_bytes_and_sha256_nullable_error_type_and_error_message_nonnull"
        ),
        "not_run_rule": "all_value_and_error_fields_null",
        "after_first_nonverified_slot_all_later_slots_must_be_not_run": True,
    }
    assert result["gate_record_fields"] == [
        "gate_id",
        "state",
        "attempted",
        "evaluable",
        "support_count",
        "coverage_fraction",
        "reason_codes",
        "cell_ids_sha256",
        "cell_records_canonical_sha256",
    ]
    assert result["cell_record_fields_source"] == (
        "gate_state_contract.required_cell_record_schema"
    )
    assert result["cell_metric_fields_by_gate"] == {
        "capture_integrity": [
            "resid_pre_raw_sha256",
            "resid_post_raw_sha256",
            "shape",
            "dtype",
            "all_finite",
        ],
        "measurable_drift": ["median_token_l2_response"],
        "f2_section_support": [
            "split_semantics",
            "supported_token_count",
            "minimum_frame_identifiability_metric",
            "minimum_amplitude",
        ],
        "f4_tensor_support": [
            "split_semantics",
            "supported_token_count",
            "minimum_frame_identifiability_metric",
            "minimum_amplitude",
        ],
        "low_amplitude_set_repeatability": [
            "fit_token_ids",
            "evaluation_token_ids",
            "jaccard",
        ],
        "address_loop_support": [
            "ring_vertex_count",
            "supported_vertex_count",
            "minimum_amplitude",
            "minimum_edge_singular_value",
            "missing_edge_count",
        ],
        "continuous_holonomy_consistency": [
            "ring_edge_count",
            "supported_edge_count",
            "forward_determinant",
            "reverse_determinant",
            "forward_angle_rad",
            "reverse_angle_rad",
            "reverse_angle_error_rad",
            "reverse_matrix_frobenius_error",
        ],
        "address_ring_phase_resolution": [
            "ring_vertex_count",
            "supported_vertex_count",
            "unrounded_phase_total_cycles",
            "maximum_absolute_edge_increment_rad",
            "branch_margin_rad",
            "nearest_integer_residual_cycles",
        ],
        "graph_family_agreement": [
            "pairwise_jaccards",
            "minimum_pairwise_jaccard",
        ],
        "negative_controls": [
            "forward_angle_rad",
            "reverse_angle_rad",
            "reverse_angle_error_rad",
            "reverse_matrix_frobenius_error",
            "forward_unrounded_phase_total_cycles",
            "reverse_unrounded_phase_total_cycles",
            "reverse_phase_total_error_cycles",
        ],
    }
    assert result["cell_metric_value_domains"] == {
        "sha256_hex_string": ["resid_pre_raw_sha256", "resid_post_raw_sha256"],
        "exact_nonnegative_integer_list": ["shape"],
        "frozen_literal_string": ["dtype", "split_semantics"],
        "boolean": ["all_finite"],
        "ordered_token_id_list": ["fit_token_ids", "evaluation_token_ids"],
        "finite_numeric_list": ["pairwise_jaccards"],
        "finite_numeric_scalar": [
            "median_token_l2_response",
            "supported_token_count",
            "minimum_frame_identifiability_metric",
            "minimum_amplitude",
            "jaccard",
            "ring_vertex_count",
            "supported_vertex_count",
            "minimum_edge_singular_value",
            "missing_edge_count",
            "ring_edge_count",
            "supported_edge_count",
            "forward_determinant",
            "reverse_determinant",
            "forward_angle_rad",
            "reverse_angle_rad",
            "reverse_angle_error_rad",
            "reverse_matrix_frobenius_error",
            "unrounded_phase_total_cycles",
            "maximum_absolute_edge_increment_rad",
            "branch_margin_rad",
            "nearest_integer_residual_cycles",
            "minimum_pairwise_jaccard",
            "forward_unrounded_phase_total_cycles",
            "reverse_unrounded_phase_total_cycles",
            "reverse_phase_total_error_cycles",
        ],
    }
    assert result["cell_metric_value_domain_rules"] == {
        "every_required_metric_field_appears_in_exactly_one_domain": True,
        "shape_and_dtype_equal_capture_manifest_literals": True,
        "split_semantics_equal_derivation_plan_candidate_split_semantics": True,
        "ordered_token_id_lists_have_exactly_10_unique_ascending_ids_from_input_plan": (
            True
        ),
        "pairwise_jaccards_have_exactly_3_values_in_frozen_family_pair_order": True,
        "integer_valued_numeric_counts_are_nonnegative": True,
        "all_numeric_scalars_and_list_elements_are_finite": True,
    }
    metric_fields = {
        field
        for fields in result["cell_metric_fields_by_gate"].values()
        for field in fields
    }
    domain_fields = [
        field
        for fields in result["cell_metric_value_domains"].values()
        for field in fields
    ]
    assert len(domain_fields) == len(set(domain_fields))
    assert set(domain_fields) == metric_fields
    assert result["cell_support_count_and_coverage"] == {
        "capture_integrity": {
            "support_count": "finite_token_rows",
            "coverage_denominator": "49",
        },
        "measurable_drift": {
            "support_count": "finite_token_response_rows",
            "coverage_denominator": "49",
        },
        "f2_section_support": {
            "support_count": "frame_and_amplitude_supported_tokens",
            "coverage_denominator": "49",
        },
        "f4_tensor_support": {
            "support_count": "frame_and_amplitude_supported_tokens",
            "coverage_denominator": "49",
        },
        "low_amplitude_set_repeatability": {
            "support_count": "present_exact_top10_sets",
            "coverage_denominator": "2",
        },
        "address_loop_support": {
            "support_count": (
                "supported_ring_vertices_plus_supported_consecutive_and_closing_edges"
            ),
            "coverage_denominator": "two_times_ring_vertex_count",
        },
        "continuous_holonomy_consistency": {
            "support_count": "supported_consecutive_and_closing_edges",
            "coverage_denominator": "ring_edge_count_equal_ring_vertex_count",
        },
        "address_ring_phase_resolution": {
            "support_count": "supported_ring_vertices_plus_supported_phase_edges",
            "coverage_denominator": "two_times_ring_vertex_count",
        },
        "graph_family_agreement": {
            "support_count": "present_pairwise_candidate_set_comparisons",
            "coverage_denominator": "3",
        },
        "negative_controls": {
            "support_count": ("supported_reverse_angle_matrix_and_phase_comparisons"),
            "coverage_denominator": "3",
        },
    }
    assert result["gate_support_aggregation"] == {
        "support_count": (
            "count_of_corresponding_cells_with_evaluable_true_and_state_pass_or_fail"
        ),
        "coverage_denominator": ("required_cell_manifests_gate_id_expected_cell_count"),
        "coverage_fraction": "support_count_divided_by_coverage_denominator",
        "state": (
            "apply_gate_state_contract.per_gate_cell_fold_order_to_exact_ordered_"
            "cell_states"
        ),
        "cell_ids_sha256": (
            "must_equal_required_cell_manifests_gate_id_cell_ids_sha256"
        ),
        "cell_records_canonical_sha256": (
            "sha256_of_canonical_json_bytes_of_exact_ordered_cell_record_list"
        ),
        "reason_codes": "sorted_unique_union_of_cell_reason_codes",
    }
    assert result["record_state_nullability"] == {
        "not_run": (
            "attempted_false_evaluable_false_support_count_zero_coverage_zero_"
            "all_metric_values_null_reason_required"
        ),
        "insufficient": (
            "attempted_true_evaluable_false_support_count_and_coverage_recorded_"
            "unavailable_metric_values_null_reason_required"
        ),
        "pass_or_fail": (
            "attempted_true_evaluable_true_all_metric_values_nonnull_every_"
            "numeric_scalar_or_array_element_finite_and_nonnumeric_values_match_"
            "cell_metric_value_domains_reason_codes_list_recorded"
        ),
    }
    assert result["resource_use_fields"] == [
        "wall_clock_seconds",
        "model_loads",
        "forward_batches",
        "raw_capture_bytes",
        "terminal_result_size_verified_below_hard",
        "peak_bytes_estimated_not_measured",
        "hard_limit_breaches",
    ]
    assert result["resource_use_contract"] == {
        "wall_clock_seconds": "finite_nonnegative_actual_observation",
        "model_loads": "nonnegative_integer_actual_observation",
        "forward_batches": "nonnegative_integer_actual_observation",
        "raw_capture_bytes": "nonnegative_integer_actual_observation",
        "terminal_result_size_verified_below_hard": (
            "must_equal_true_for_any_published_terminal_after_final_serialization"
        ),
        "peak_bytes_estimated_not_measured": ("nonnegative_integer_frozen_estimate"),
        "hard_limit_field_to_budget_field": {
            "wall_clock_seconds": "wall_clock_seconds_hard",
            "model_loads": "model_loads_maximum",
            "forward_batches": "forward_batches_maximum",
            "raw_capture_bytes": "raw_capture_bytes_hard",
            "peak_bytes_estimated_not_measured": "max_estimated_peak_bytes",
        },
        "hard_limit_breaches": (
            "sorted_unique_list_of_exact_hard_limit_field_names_whose_actual_"
            "value_is_strictly_greater_than_its_mapped_budget"
        ),
        "complete_requires_empty_hard_limit_breaches": True,
        "infrastructure_error_may_record_over_budget_actual_values": True,
        "terminal_result_size_over_hard_cannot_publish_and_remains_consumed_"
        "unresolved": True,
    }
    assert result["error_record_fields"] == [
        "stage",
        "exception_type",
        "message",
        "caught_at_utc",
    ]
    assert result["error_stage_values"] == [
        "model_file_hash",
        "model_load",
        "capture",
        "raw_capture_persist",
        "graph_construction",
        "f2_f4_derivation",
        "gate_evaluation",
        "resource_budget",
        "terminal_serialization",
        "terminal_persistence",
    ]
    assert result["post_terminal_failure_rules"] == {
        "native_no_replace_promotion_failure": (
            "retain_stage_as_consumed_unresolved_with_existing_terminal_bytes_unchanged"
        ),
        "repository_projection_failure_after_promotion": (
            "external_store_terminal_remains_authoritative_and_unchanged"
        ),
        "later_repository_projection_repair": (
            "may_only_copy_strictly_reloaded_byte_identical_external_attempt_and_"
            "terminal_records_with_no_replace_and_without_model_access"
        ),
        "model_execution_retry_or_resume": False,
    }
    assert result["infrastructure_partial_prefix_rules"] == {
        "capture_manifest": (
            "empty_or_ordered_prefix_of_exact_16_context_stage_records"
        ),
        "graph_receipts": (
            "empty_or_ordered_prefix_of_exact_18_layer_family_records_after_"
            "complete_capture"
        ),
        "cell_records": (
            "empty_or_ordered_prefix_of_exact_894_cell_ids_after_complete_"
            "capture_and_graph_receipts"
        ),
        "gate_records": (
            "empty_or_ordered_prefix_of_exact_10_gate_ids_with_one_record_only_"
            "after_that_gate_full_contiguous_cell_block_is_present_and_folded"
        ),
        "phase_order": [
            "capture_manifest",
            "graph_receipts",
            "cell_records",
            "gate_records",
        ],
        "graph_prefix_nonempty_requires_complete_capture_manifest": True,
        "cell_prefix_nonempty_requires_complete_graph_receipts": True,
        "gate_record_count_equals_number_of_complete_leading_gate_cell_blocks": True,
    }
    assert result["failure_classification"] == {
        "model_or_cache_load_failure": "infrastructure_error",
        "capture_shape_dtype_nonfinite_missing_or_digest_failure": (
            "infrastructure_error"
        ),
        "graph_receipt_or_numeric_invariant_exception": "infrastructure_error",
        "terminal_serialization_or_persistence_failure": (
            "infrastructure_error_if_a_minimal_terminal_can_be_published_"
            "otherwise_consumed_unresolved"
        ),
        "native_no_replace_promotion_failure": (
            "consumed_unresolved_existing_terminal_bytes_not_rewritten"
        ),
        "repository_projection_failure_after_promotion": (
            "external_store_terminal_remains_terminal_and_repository_projection_"
            "is_incomplete"
        ),
        "wall_clock_or_resource_hard_limit_reached": (
            "stop_model_and_derivation_work_then_publish_infrastructure_error_"
            "with_actual_value_and_exact_hard_limit_breaches_if_a_bounded_"
            "terminal_can_be_published_otherwise_consumed_unresolved"
        ),
        "scientific_support_identifiability_coverage_or_resolution_below_floor": (
            "insufficient"
        ),
        "evaluable_frozen_consistency_or_negative_control_threshold_violation": (
            "fail"
        ),
        "unattempted_cell_before_catchable_scientific_completion": "not_run",
    }
    assert (
        result[
            "unknown_or_extra_root_nested_capture_graph_gate_cell_metric_"
            "provenance_resource_or_error_fields_allowed"
        ]
        is False
    )
    assert result["canonical_bytes_must_strict_reload_and_rerender_identically"]


def test_gate_state_lifecycle_and_claim_ceiling_cannot_launder_a_pass() -> None:
    freeze = _load_json(FREEZE_PATH)
    contract = freeze["gate_state_contract"]
    assert contract["per_gate_vocabulary"] == [
        "pass",
        "fail",
        "insufficient",
        "not_run",
    ]
    assert contract["terminal_vocabulary"] == ["pass", "fail", "insufficient"]
    assert contract["execution_terminal_vocabulary"] == [
        "complete",
        "infrastructure_error",
    ]
    assert contract["infrastructure_error_is_not_a_gate_state"] is True
    assert contract["gate_ids"] == list(EXPECTED_GATES)
    cell_manifests = contract["required_cell_manifests"]
    assert [cell["gate_id"] for cell in cell_manifests] == list(EXPECTED_GATES)
    assert [cell["expected_cell_count"] for cell in cell_manifests] == [
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
    ]
    assert sum(cell["expected_cell_count"] for cell in cell_manifests) == 894
    assert contract["total_required_cells"] == 894
    axes = contract["required_cell_axes"]
    assert axes["context"] == list(EXPECTED_CONTEXT_IDS)
    expected_manifest_axes = {
        "capture_integrity": ["context", "layer_id"],
        "measurable_drift": ["layer_id", "split"],
        "f2_section_support": ["graph_family", "layer_id", "split"],
        "f4_tensor_support": ["graph_family", "layer_id", "split"],
        "low_amplitude_set_repeatability": [
            "candidate",
            "graph_family",
            "layer_id",
        ],
        "address_loop_support": [
            "candidate",
            "graph_family",
            "layer_id",
            "ring_id",
            "split",
        ],
        "continuous_holonomy_consistency": [
            "graph_family",
            "layer_id",
            "ring_id",
        ],
        "address_ring_phase_resolution": [
            "candidate",
            "graph_family",
            "layer_id",
            "ring_id",
            "split",
        ],
        "graph_family_agreement": ["candidate", "layer_id", "split"],
        "negative_controls": [
            "candidate",
            "graph_family",
            "layer_id",
            "ring_id",
            "split",
        ],
    }
    assert {cell["gate_id"]: cell["axes"] for cell in cell_manifests} == (
        expected_manifest_axes
    )
    all_cell_ids: list[str] = []
    for manifest in cell_manifests:
        cell_ids = [
            manifest["gate_id"]
            + "|"
            + "|".join(
                f"{axis}={value}"
                for axis, value in zip(manifest["axes"], values, strict=True)
            )
            for values in itertools.product(*(axes[axis] for axis in manifest["axes"]))
        ]
        encoded = ("\n".join(cell_ids) + "\n").encode("utf-8")
        assert len(cell_ids) == manifest["expected_cell_count"]
        assert hashlib.sha256(encoded).hexdigest() == manifest["cell_ids_sha256"]
        all_cell_ids.extend(cell_ids)
    assert len(all_cell_ids) == len(set(all_cell_ids)) == 894
    assert contract["gate_formulas"] == {
        "capture_integrity": "exact_shape_dtype_finite_manifest_and_array_digest_rejoin",
        "measurable_drift": (
            "median_token_l2_norm_of_exact_split_arithmetic_mean_response_"
            "strictly_above_amplitude_floor_is_pass_else_insufficient"
        ),
        "f2_section_support": (
            "evaluation_cells_require_referent_bound_canonical_local_z_support_"
            "and_fit_cells_require_in_sample_non_referent_z_diagnostic_support_"
            "for_at_least_minimum_supported_tokens_else_insufficient"
        ),
        "f4_tensor_support": (
            "evaluation_cells_require_referent_bound_canonical_local_traceless_"
            "tensor_support_and_fit_cells_require_in_sample_non_referent_"
            "traceless_tensor_diagnostic_support_for_at_least_minimum_supported_"
            "tokens_else_insufficient"
        ),
        "low_amplitude_set_repeatability": (
            "candidate_specific_lowest_global_comparable_amplitude_fit_and_"
            "evaluation_top10_jaccard_uses_inclusive_pass_and_fail_floors_with_"
            "middle_insufficient"
        ),
        "address_loop_support": (
            "same_global_candidate_object_amplitude_is_strictly_above_floor_and_"
            "all_consecutive_closing_edges_meet_minimum_edge_procrustes_singular_"
            "value_inclusively_else_insufficient"
        ),
        "continuous_holonomy_consistency": (
            "full_o2_edge_transports_meet_minimum_singular_value_cycle_is_"
            "orientation_preserving_reverse_recomputed_matrix_matches_forward_"
            "inverse_within_frobenius_tolerance_and_reverse_angle_modulo_two_pi_"
            "error_meets_angle_tolerance"
        ),
        "address_ring_phase_resolution": (
            "same_global_candidate_complex_object_has_nonzero_amplitude_"
            "pi_minus_maximum_absolute_edge_increment_strictly_above_branch_"
            "margin_and_absolute_nearest_integer_residual_of_unrounded_closed_"
            "phase_total_within_tolerance_without_constructing_or_persisting_"
            "winding"
        ),
        "graph_family_agreement": (
            "minimum_of_exact_three_pairwise_jaccards_of_candidate_specific_low_"
            "amplitude_sets_uses_inclusive_pass_and_fail_floors_with_middle_"
            "insufficient"
        ),
        "negative_controls": (
            "for_each_split_reverse_recomputed_holonomy_modulo_two_pi_angle_"
            "error_and_inverse_matrix_frobenius_error_meet_exact_tolerances_and_"
            "absolute_sum_of_reverse_and_forward_unrounded_phase_total_cycles_"
            "meets_reverse_phase_total_tolerance_after_support_prerequisites"
        ),
    }
    assert contract["required_cell_record_schema"] == {
        "common_required_fields": [
            "cell_id",
            "gate_id",
            "axis_values",
            "state",
            "attempted",
            "evaluable",
            "support_count",
            "coverage_fraction",
            "reason_codes",
            "metrics",
        ],
        "axis_fields_source": "required_cell_manifests[gate_id].axes",
        "axis_values_keys_must_equal_manifest_axes": True,
        "unmanifested_axis_fields_allowed": False,
        "cell_id_must_equal_recomputed_manifest_cell_id": True,
    }
    assert contract["per_gate_cell_fold_order"] == [
        "any_fail_to_fail",
        "else_any_insufficient_to_insufficient",
        "else_all_not_run_to_not_run",
        "else_mixed_pass_and_not_run_to_insufficient",
        "else_all_expected_cells_pass_to_pass",
    ]
    assert contract["terminal_fold_order"] == [
        "any_gate_fail_to_fail",
        "else_any_gate_insufficient_or_not_run_to_insufficient",
        "else_all_gates_pass_to_pass",
    ]
    assert contract["every_manifest_cell_id_must_appear_exactly_once"] is True
    assert contract["missing_duplicate_or_unknown_cell_id_invalidates_attempt"] is True
    assert contract["required_fields_per_gate"] == [
        "gate_id",
        "state",
        "attempted",
        "evaluable",
        "support_count",
        "coverage_fraction",
        "reason_codes",
        "cell_ids_sha256",
        "cell_records_canonical_sha256",
    ]
    assert contract["thresholds"] == {
        "amplitude_floor": {
            "value": 1e-8,
            "supported_when": "strictly_greater",
            "otherwise_state": "insufficient",
        },
        "minimum_supported_tokens": {
            "value": 35,
            "pass_support_when": "greater_than_or_equal",
            "otherwise_state": "insufficient",
        },
        "minimum_global_procrustes_singular_value": {
            "value": 1e-6,
            "supported_when": "greater_than_or_equal",
            "otherwise_state": "insufficient",
        },
        "minimum_edge_procrustes_singular_value": {
            "value": 1e-6,
            "supported_when": "greater_than_or_equal",
            "otherwise_state": "insufficient",
        },
        "low_amplitude_set_jaccard": {
            "pass_floor_inclusive": 0.3,
            "fail_ceiling_inclusive": 0.1,
            "middle_state": "insufficient",
        },
        "graph_family_jaccard": {
            "aggregate": "minimum_of_exact_three_pairwise_values",
            "pass_floor_inclusive": 0.5,
            "fail_ceiling_inclusive": 0.2,
            "middle_state": "insufficient",
        },
        "reverse_angle_tolerance_rad": {
            "value": 1e-6,
            "pass_when_absolute_error": "less_than_or_equal",
            "numeric_violation_state": "fail",
            "missing_prerequisite_state": "insufficient",
        },
        "reverse_holonomy_matrix_frobenius_tolerance": {
            "value": 1e-6,
            "pass_when_frobenius_error": "less_than_or_equal",
            "numeric_violation_state": "fail",
            "missing_prerequisite_state": "insufficient",
        },
        "phase_residual_tolerance_cycles": {
            "value": 1e-6,
            "pass_when_absolute_residual": "less_than_or_equal",
            "numeric_violation_state": "fail",
        },
        "reverse_phase_total_tolerance_cycles": {
            "value": 1e-6,
            "pass_when_absolute_error": "less_than_or_equal",
            "numeric_violation_state": "fail",
            "missing_prerequisite_state": "insufficient",
        },
        "phase_branch_margin_rad": {
            "value": 1e-6,
            "supported_when": "strictly_greater",
            "otherwise_state": "insufficient",
        },
    }
    assert contract["address_ring_phase_output"] == {
        "persisted_fields": [
            "unrounded_phase_total_cycles",
            "maximum_absolute_edge_increment_rad",
            "nearest_integer_residual_cycles",
        ],
        "edge_increment_formula": (
            "atan2(imag(conjugate(psi_i)_times_psi_j),real(conjugate(psi_i)_"
            "times_psi_j))"
        ),
        "edge_increment_branch_cut_policy": (
            "an_exact_minus_pi_or_pi_increment_is_insufficient"
        ),
        "path_order": "declared_ring_consecutive_edges_then_closing_edge",
        "unrounded_phase_total_cycles_formula": (
            "sum_edge_increment_rad_divided_by_two_pi"
        ),
        "maximum_absolute_edge_increment_rad_formula": (
            "max_absolute_edge_increment_rad"
        ),
        "branch_margin_rad_formula": ("pi_minus_maximum_absolute_edge_increment_rad"),
        "branch_supported_when": (
            "branch_margin_rad_strictly_greater_than_phase_branch_margin_rad"
        ),
        "nearest_integer_residual_cycles_formula": (
            "abs(unrounded_phase_total_cycles-numpy.rint(unrounded_phase_total_cycles))"
        ),
        "resolve_sampled_winding_called": False,
        "sampled_winding_constructed": False,
        "winding_estimate_persisted": False,
        "nearest_integer_value_persisted": False,
    }
    assert contract["holonomy_reverse_comparison"] == {
        "forward_matrix": (
            "H_forward=compose_edge_transports_in_declared_ring_edge_order"
        ),
        "reverse_matrix": (
            "H_reverse=compose_recomputed_reverse_edge_transports_in_reverse_"
            "ring_edge_order"
        ),
        "matrix_error_formula": (
            "frobenius_norm_of_H_reverse_minus_numpy_linalg_inv_H_forward"
        ),
        "matrix_tolerance_key": "reverse_holonomy_matrix_frobenius_tolerance",
        "forward_angle_rad": ("theta_forward=principal_rotation_angle_2d(H_forward)"),
        "reverse_angle_rad": ("theta_reverse=principal_rotation_angle_2d(H_reverse)"),
        "modulo_two_pi_angle_error_formula": (
            "absolute_atan2_sin_theta_reverse_plus_theta_forward_cos_theta_"
            "reverse_plus_theta_forward"
        ),
        "angle_tolerance_key": "reverse_angle_tolerance_rad",
    }
    assert (
        contract[
            "nearest_integer_may_be_used_for_residual_only_but_must_not_be_persisted"
        ]
        is True
    )
    assert contract["missing_state_may_default_to_pass"] is False
    assert contract["development_pass_has_scientific_or_milestone_effect"] is False
    assert _fold(("pass",) * len(EXPECTED_GATES)) == "pass"
    assert _fold(("pass", "insufficient")) == "insufficient"
    assert _fold(("pass", "not_run")) == "insufficient"
    assert _fold(("insufficient", "fail")) == "fail"
    assert _fold_cells(("not_run", "not_run")) == "not_run"
    assert _fold_cells(("pass", "not_run")) == "insufficient"
    assert _fold_cells(("pass", "insufficient")) == "insufficient"
    assert _fold_cells(("pass", "fail")) == "fail"

    lifecycle = freeze["lifecycle"]
    assert lifecycle["current_state"] == "not_run"
    assert lifecycle["maximum_execution_attempts_per_freeze_id"] == 1
    assert lifecycle["retries"] == 0
    assert all(
        lifecycle[key] is False
        for key in (
            "resume_allowed",
            "reopen_allowed",
            "output_reuse_allowed",
            "same_identity_rescue_allowed",
            "post_outcome_threshold_or_graph_change_allowed",
        )
    )
    assert lifecycle["exclusive_start_must_precede_model_file_hash_or_model_load"]
    assert lifecycle["exclusive_start_or_model_access_failure_consumes_identity"]
    assert lifecycle["durable_external_stage_is_the_attempt_barrier"]
    assert lifecycle[
        "all_catchable_terminal_promotion_requires_native_no_replace_rename"
    ]
    assert lifecycle[
        "external_stage_is_never_deleted_or_reused_except_when_consumed_by_native_no_replace_promotion"
    ]
    assert lifecycle["stage_store_truth_table"] == {
        "stage_absent_store_absent": "unopened",
        "stage_present_store_absent": "consumed_unresolved_or_partial",
        "stage_absent_store_present": "terminal_consumed",
        "stage_present_store_present": "invalid_quarantine",
    }
    assert lifecycle["ordered_attempt_protocol"] == [
        "observe_stage_and_store_absent_then_exclusively_mkdir_fixed_stage_mode_0700_without_following_symlinks_and_fsync_parent",
        "write_canonical_attempt_record_with_O_CREAT_O_EXCL_then_fsync_file_and_stage_directory",
        "only_after_durable_attempt_record_hash_actual_model_files_and_require_exact_sha256_and_sizes_equal_bindings_model_files_before_model_load_with_mismatch_as_infrastructure_error",
        "retain_stage_without_cleanup_resume_or_retry_after_any_failure_that_prevents_catchable_terminal_publication_and_promotion",
        "for_complete_or_catchable_infrastructure_error_write_terminal_result_O_CREAT_O_EXCL_fsync_file_and_stage_then_native_RENAME_NOREPLACE_stage_to_store_and_fsync_parent",
        "for_uncatchable_failure_retain_start_only_stage_as_consumed_unresolved_evidence_not_a_result",
    ]
    assert lifecycle[
        "preflight_may_repeat_only_while_stage_and_store_are_absent_model_bytes_are_unread_and_inputs_are_unchanged"
    ]
    assert lifecycle["attempt_record_required_bindings"] == [
        "launch_authorization_sha256",
        "freeze_source_sha256",
        "context_bank_source_sha256",
        "context_bank_canonical_sha256",
        "route_source_sha256",
        "runner_source_sha256",
        "runner_implementation_commit",
        "runtime_source_commit",
        "exact_argv",
        "runtime_versions",
        "expected_model_file_sha256_and_sizes",
        "all_external_and_repository_coordinates",
        "resource_budget",
        "claim_boundary",
    ]
    assert lifecycle["attempt_record_contract"] == {
        "schema_version": ("spirallens.pythia70-gate-state-development-attempt.v0.1"),
        "attempt_id": "pythia70-gate-state-development-v0.1-attempt-1",
        "root_fields": [
            "schema_version",
            "attempt_id",
            "launch_id",
            "started_at_utc",
            "absence_and_reservation",
            "bindings",
            "artifact_coordinates",
            "resource_budget",
            "claim_boundary",
        ],
        "absence_and_reservation_fields": [
            "observed_at_utc",
            "observed_absent_coordinates",
            "reserved_at_utc",
            "stage_path",
            "stage_device",
            "stage_inode",
            "stage_mode",
            "parent_directory_fsynced",
        ],
        "observed_absent_coordinates_must_equal": [
            "external_staging_path",
            "external_store_path",
            "external_next_hypotheses_path",
            "attempt_record",
            "terminal_result",
            "next_hypotheses",
        ],
        "absence_and_reservation_equalities": {
            "observed_absent_coordinates": (
                "exactly_equal_observed_absent_coordinates_must_equal_in_frozen_order"
            ),
            "stage_path": ("exactly_equal_artifact_coordinates.external_staging_path"),
            "stage_device": (
                "nonnegative_integer_from_post_mkdir_nofollow_descriptor_and_path_"
                "identity_join"
            ),
            "stage_inode": (
                "positive_integer_from_post_mkdir_nofollow_descriptor_and_path_"
                "identity_join"
            ),
            "stage_mode": (
                "decimal_448_exactly_equal_posix_0700_permission_bits_with_"
                "directory_type_verified_separately"
            ),
            "parent_directory_fsynced": True,
            "descriptor_and_path_identity_equal_before_attempt_record_write": True,
        },
        "binding_fields_source": "lifecycle.attempt_record_required_bindings",
        "required_value_sources": {
            "schema_version": "lifecycle.attempt_record_contract.schema_version",
            "attempt_id": "launch_authorization.attempt_id",
            "launch_id": "launch_authorization.launch_id",
            "started_at_utc": ("must_equal_absence_and_reservation.reserved_at_utc"),
            "absence_and_reservation": (
                "same_process_runtime_observation_and_exclusive_stage_reservation"
            ),
            "bindings": (
                "exact_runtime_revalidation_of_launch_authorization_and_freeze_"
                "bound_sources"
            ),
            "artifact_coordinates": "freeze_document.artifact_coordinates",
            "resource_budget": "freeze_document.resource_budget",
            "claim_boundary": "freeze_document.claim_boundary",
        },
        "chronology_rule": (
            "observed_at_utc_less_than_or_equal_reserved_at_utc_equal_started_at_utc"
        ),
        "utc_timestamp_format": (
            "rfc3339_utc_with_exactly_six_fractional_second_digits_and_Z_suffix"
        ),
        "unknown_extra_or_duplicate_fields_are_rejected": True,
        "canonical_bytes_must_strict_reload_and_rerender_identically": True,
    }
    assert lifecycle[
        "repository_records_are_byte_identical_projections_not_the_attempt_barrier"
    ]
    assert lifecycle["launch_binding_requirements"] == {
        "runner_path_and_source_sha256": True,
        "freeze_source_sha256": True,
        "context_bank_source_and_canonical_sha256": True,
        "exact_argv_and_runtime_versions": True,
        "clean_source_commit_and_runner_blob_join": True,
        "attempt_raw_result_and_planning_path_absence": True,
        "separate_dated_launch_authorization_before_model_access": True,
    }

    coordinates = freeze["artifact_coordinates"]
    assert coordinates["external_staging_path"] == (
        "/Users/ryohiga/SpiralReality/"
        ".spirallens-pythia70-gate-state-development-v0-1-store.staging"
    )
    assert coordinates["external_store_path"] == (
        "/Users/ryohiga/SpiralReality/"
        "spirallens-pythia70-gate-state-development-v0-1-store"
    )
    assert coordinates["external_next_hypotheses_path"] == (
        "/Users/ryohiga/SpiralReality/"
        "spirallens-pythia70-gate-state-development-v0-1-next-hypotheses.json"
    )
    assert coordinates[
        "next_hypotheses_is_outside_terminal_store_and_published_later_with_no_replace"
    ]

    launch = freeze["launch_authorization_contract"]
    assert launch["path"] == (
        "experiments/pythia/gate_state_development_v0_1/launch-authorization.json"
    )
    assert launch["schema_version"] == (
        "spirallens.pythia70-gate-state-launch-authorization.v0.1"
    )
    assert launch["launch_id"] == "pythia70-gate-state-development-launch-v0.1"
    assert launch["attempt_id"] == "pythia70-gate-state-development-v0.1-attempt-1"
    assert launch["required_status"] == "authorized_not_started"
    assert launch["required_root_fields"] == [
        "schema_version",
        "launch_id",
        "attempt_id",
        "decision_date",
        "status",
        "execution_class",
        "freeze",
        "context_bank",
        "route",
        "frame",
        "merged_policy_docs",
        "runner",
        "command",
        "runtime",
        "model",
        "artifacts",
        "absence_precondition",
        "resource_budget",
        "authorizations",
        "claim_boundary",
    ]
    assert launch["required_fixed_values"] == {
        "schema_version": ("spirallens.pythia70-gate-state-launch-authorization.v0.1"),
        "launch_id": "pythia70-gate-state-development-launch-v0.1",
        "attempt_id": "pythia70-gate-state-development-v0.1-attempt-1",
        "status": "authorized_not_started",
        "execution_class_source": "route_amendment.execution_class",
        "decision_date_rule": "iso_8601_date_not_before_freeze_decision_date",
    }
    assert launch["required_bindings"] == {
        "freeze": ["path", "source_sha256", "freeze_id"],
        "context_bank": [
            "path",
            "source_sha256",
            "canonical_sha256",
            "bank_id",
            "status",
            "role",
            "claim_eligible",
        ],
        "route": ["path", "source_sha256", "route_id", "execution_class"],
        "frame": ["path", "source_sha256", "ledger_amendment_anchor"],
        "merged_policy_docs": [
            "ledger_path",
            "ledger_sha256",
            "roadmap_path",
            "roadmap_sha256",
            "next_experiment_preparation_path",
            "next_experiment_preparation_sha256",
        ],
        "runner": ["path", "source_sha256", "implementation_commit"],
        "command": ["exact_argv", "working_directory"],
        "runtime": [
            "python_executable",
            "python_version",
            "dependency_versions",
        ],
        "model": ["id", "revision", "file_sha256_and_sizes"],
        "artifacts": [
            "external_staging_path",
            "external_store_path",
            "external_next_hypotheses_path",
            "repository_projection_paths",
        ],
        "absence_precondition": [
            "coordinates_required_absent",
            "runner_must_observe_absence_and_exclusively_start_in_same_process",
        ],
        "resource_budget": [
            "wall_clock_seconds_hard",
            "model_loads_maximum",
            "forward_batches_maximum",
            "byte_limits",
        ],
        "authorizations": [
            "operator_authorized_exact_one_attempt",
            "execution_authorized",
            "model_access_authorized",
        ],
        "claim_boundary": [
            "claim_ceiling",
            "claim_delta",
            "milestone_credit",
            "evidence_eligible",
        ],
    }
    assert launch["required_equalities_to_freeze"] == {
        "freeze": [
            "path_equals_protocols/pythia70_gate_state_development_freeze_v0_1.json",
            "freeze_id_equals_root_freeze_id",
            "source_sha256_equals_runtime_sha256_of_exact_freeze_bytes",
        ],
        "context_bank": ["all_seven_fields_equal_bindings.context_bank"],
        "route": [
            "path_source_sha256_route_id_and_execution_class_equal_route_amendment"
        ],
        "frame": [
            "path_source_sha256_and_ledger_amendment_anchor_equal_bindings.fundamental_frame"
        ],
        "merged_policy_docs": [
            "ledger_path_and_sha256_equal_bindings.policy_documents_0",
            "roadmap_path_and_sha256_equal_bindings.policy_documents_1",
            "next_experiment_preparation_path_and_sha256_equal_bindings.policy_documents_2",
        ],
        "runner": [
            "path_equals_artifact_coordinates.prospective_runner_path",
            "source_sha256_equals_runtime_runner_bytes",
            "implementation_commit_contains_same_runner_blob_and_is_ancestor_of_runtime_source_commit",
        ],
        "model": ["id_revision_and_file_sha256_and_sizes_equal_bindings.model"],
        "artifacts": [
            "external_paths_equal_artifact_coordinates_external_staging_external_store_and_external_next_hypotheses",
            "repository_projection_paths_equal_artifact_coordinates_attempt_record_terminal_result_and_next_hypotheses",
        ],
        "absence_precondition": [
            "coordinates_required_absent_equal_external_stage_store_next_hypotheses_and_repository_projection_paths",
            "runner_must_observe_absence_and_exclusively_start_in_same_process_equals_true",
        ],
        "resource_budget": [
            "wall_clock_seconds_hard_model_loads_maximum_and_forward_batches_maximum_equal_resource_budget",
            "byte_limits_equal_resource_budget_raw_capture_terminal_result_next_hypotheses_and_max_estimated_peak_bytes",
        ],
        "authorizations": [
            "operator_authorized_exact_one_attempt_execution_authorized_and_model_access_authorized_all_equal_true"
        ],
        "claim_boundary": [
            "claim_ceiling_claim_delta_milestone_credit_and_evidence_eligible_equal_root_claim_boundary"
        ],
    }
    assert launch["equality_validation_implemented_by_this_freeze"] is False
    assert launch[
        "successor_runner_and_tests_must_fail_closed_on_every_required_equality_before_launch"
    ]
    assert launch[
        "root_and_nested_keys_must_equal_required_root_fields_and_required_bindings"
    ]
    assert launch["unknown_extra_or_duplicate_fields_are_rejected"]
    assert launch[
        "actual_absence_observation_is_recorded_by_attempt_and_joined_to_exclusive_start_in_one_process"
    ]
    assert launch["hostile_same_user_or_multihost_uniqueness_claimed"] is False

    authorizations = freeze["authorizations"]
    assert authorizations["separate_discovery_context_bank_definition_authorized"]
    assert authorizations["execution_authorized_at_freeze"] is False
    assert authorizations["model_access_authorized_at_freeze"] is False
    assert all(authorizations["prospective_capabilities_after_valid_launch"].values())
    assert all(
        authorizations[key] is False
        for key in (
            "public_example_atlas_or_receipt_reuse",
            "D7_verified_B_reexecution_or_reconstruction",
            "Pythia160_model_or_weight_access",
            "SCI_S1_progress",
            "SCI_S2_progress",
            "subject_preparation",
            "subject_execution",
            "candidate_winner_selection",
            "integer_or_topology_claim",
            "publication_or_release",
        )
    )
    assert freeze["claim_boundary"] == {
        "claim_ceiling": "level_0",
        "claim_delta": "none",
        "milestone_credit": "none",
        "evidence_eligible": False,
        "scientific_authority": False,
        "semantic_authority": False,
        "topology_authority": False,
        "integer_output_authority": False,
        "D7_state_change": False,
        "D8_state_change": False,
        "VOY_stage_change": False,
        "SCI_stage_change": False,
        "Pythia160_protocol_change": False,
        "support_compatibility_portability_or_API_claim": False,
        "negative_space_map_is_next_hypothesis_input_only": True,
        "order_parameter_field_constructed": False,
        "core_score_or_core_candidate_constructed": False,
        "sampled_winding_or_winding_estimate_constructed": False,
    }
    exclusions = freeze["historical_exclusions"]
    assert exclusions["D7_verified_B_disposition"] == "closed_insufficient_no_rerun"
    assert exclusions["Pythia160_gate_disposition"] == "unchanged_and_blocked"
