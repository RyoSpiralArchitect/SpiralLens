from __future__ import annotations

import ast
import builtins
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
from typing import Any

import pytest

from spirallens._repository_context import RepositoryContext
from spirallens.core.canonical import (
    canonical_json_bytes,
    parse_canonical_json,
    sha256_bytes,
)
from spirallens.qualification import confirmation_v1_materialization as materialization
from spirallens.qualification import confirmation_v1_post_d6_descriptive as descriptive
from spirallens.qualification import confirmation_v1_records as records
from spirallens.qualification import confirmation_v1_official_execution as official
from spirallens.qualification.common import QualificationContractError


REPOSITORY = Path(__file__).resolve().parents[1]
OFFICIAL_MODULE = (
    REPOSITORY
    / "src"
    / "spirallens"
    / "qualification"
    / "confirmation_v1_official_execution.py"
)
PREPARER = REPOSITORY / "scripts" / "prepare_d7_v1_launch.py"
RUNNER = REPOSITORY / "scripts" / "run_d7_v1.py"
OFFICIAL_REPOSITORY_ROOT = (
    REPOSITORY / "experiments" / "qualification" / "d7_spectral_moment_confirmation_v1"
)
OFFICIAL_EXTERNAL_STAGING = Path(
    "/Users/ryohiga/SpiralReality/.spirallens-d7-v1-store.staging"
)
OFFICIAL_EXTERNAL_STORE = Path("/Users/ryohiga/SpiralReality/spirallens-d7-v1-store")
OFFICIAL_PATHS = (
    OFFICIAL_REPOSITORY_ROOT,
    OFFICIAL_EXTERNAL_STAGING,
    OFFICIAL_EXTERNAL_STORE,
)
RESULT_PATH = (
    "experiments/qualification/d7_spectral_moment_confirmation_v1/"
    "post-d6-descriptive-analysis-result.json"
)


def _load_script(path: Path, *, name: str) -> dict[str, Any]:
    before = tuple(sys.path)
    loaded = runpy.run_path(str(path), run_name=name)
    assert tuple(sys.path) == before
    return loaded


def _call_names(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            names.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            names.append(node.func.attr)
    return tuple(names)


def _import_names(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names.append(module)
            names.extend(
                f"{module}.{alias.name}" if module else alias.name
                for alias in node.names
            )
    return tuple(names)


def _path_snapshot(path: Path) -> tuple[object, ...]:
    try:
        stat = path.lstat()
    except FileNotFoundError:
        return ("absent",)
    if path.is_symlink():
        return ("symlink", stat.st_dev, stat.st_ino, os.readlink(path))
    if path.is_file():
        source = path.read_bytes()
        return (
            "file",
            stat.st_dev,
            stat.st_ino,
            stat.st_mode,
            len(source),
            hashlib.sha256(source).hexdigest(),
        )
    entries = tuple(sorted(item.name for item in path.iterdir()))
    return ("directory", stat.st_dev, stat.st_ino, stat.st_mode, entries)


def _official_path_snapshot() -> tuple[tuple[object, ...], ...]:
    return tuple(_path_snapshot(path) for path in OFFICIAL_PATHS)


def _run_script(
    path: Path, *arguments: str, cwd: Path = REPOSITORY
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        (sys.executable, str(path), *arguments),
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def _git_blob(commit: str, repository_path: str) -> bytes:
    return subprocess.run(
        ("git", "show", f"{commit}:{repository_path}"),
        cwd=REPOSITORY,
        check=True,
        capture_output=True,
    ).stdout


def _synthetic_binding(role: str, marker: str) -> records.D7V1ArtifactBinding:
    return records.D7V1ArtifactBinding(
        artifact_role=role,
        artifact_contract_id=records._INTERNAL_ROLE_SCHEMAS[role],
        canonical_sha256=marker * 64,
        byte_count=1,
    )


def _attempt_and_receipt() -> tuple[
    records.D7V1OfficialExecutionAttemptReservation,
    records.D7V1PreItem23ChronologyReceipt,
]:
    source_commit = "a" * 40
    launch = _synthetic_binding(records.D7V1LaunchIntent.artifact_role, "1")
    replay = _synthetic_binding(records.D7V1ReplayTarget.artifact_role, "2")
    claim = _synthetic_binding(records.D7V1ExclusiveSeedSupplyClaim.artifact_role, "3")
    derivation = {
        "domain": records.D7_V1_ATTEMPT_KEY_DOMAIN,
        "external_attempt_path": (
            "/Users/test/SpiralReality/spirallens-d7-v1-store/"
            "d7-v1-attempt-evidence/official-execution-attempt-reservation.json"
        ),
        "launch_intent_sha256": launch.canonical_sha256,
        "replay_target_sha256": replay.canonical_sha256,
        "reviewed_source_commit": source_commit,
        "seed_claim_sha256": claim.canonical_sha256,
    }
    root = "experiments/qualification/d7_spectral_moment_confirmation_v1"
    attempt = records.D7V1OfficialExecutionAttemptReservation._create(
        record_id="d7-v1-test-attempt",
        payload={
            "repository_path": (
                f"{root}/pre-item23/official-execution-attempt-envelope.json"
            ),
            "launch_intent_binding": launch.to_dict(),
            "replay_target_binding": replay.to_dict(),
            "seed_claim_binding": claim.to_dict(),
            "attempt_key_derivation": derivation,
            "attempt_key_sha256": sha256_bytes(canonical_json_bytes(derivation)),
            "external_store_path": ("/Users/test/SpiralReality/spirallens-d7-v1-store"),
        },
    )

    inventory = {
        role: f"{root}/test-{sequence:02d}-{role}.json"
        for sequence, role in enumerate(records._PRE_ITEM23_FILE_ROLES, start=1)
    }
    inventory[records.D7V1OfficialExecutionAttemptReservation.artifact_role] = (
        f"{root}/pre-item23/official-execution-attempt-envelope.json"
    )
    inventory[records.D7V1PreItem23ChronologyReceipt.artifact_role] = (
        f"{root}/pre-item23-chronology-receipt.json"
    )
    predecessor_bindings = {
        role: (
            records.D7V1ArtifactBinding.from_record(attempt)
            if role == attempt.artifact_role
            else _synthetic_binding(role, f"{sequence:x}"[-1])
        )
        for sequence, role in enumerate(records._PRE_ITEM23_FILE_ROLES, start=4)
        if role != records.D7V1PreItem23ChronologyReceipt.artifact_role
    }
    absence = records.D7V1NamespaceAbsenceObservation(
        repository_path=RESULT_PATH,
        observed_at_reviewed_source_commit=source_commit,
    )
    receipt = records.D7V1PreItem23ChronologyReceipt.create(
        record_id="d7-v1-test-receipt",
        repository_path=inventory[records.D7V1PreItem23ChronologyReceipt.artifact_role],
        predecessor_bindings=predecessor_bindings,
        pre_item23_file_inventory=inventory,
        descriptive_result_namespace_absence=absence,
    )
    return attempt, receipt


@pytest.fixture(scope="module")
def historical_sources() -> tuple[bytes, ...]:
    return tuple(
        _git_blob(spec.source_commit, spec.repository_path)
        for spec in descriptive._INPUT_SPECS
    )


@pytest.fixture(scope="module")
def attempt_and_receipt() -> tuple[
    records.D7V1OfficialExecutionAttemptReservation,
    records.D7V1PreItem23ChronologyReceipt,
]:
    return _attempt_and_receipt()


def _derive_result(
    sources: tuple[bytes, ...],
    parents: tuple[
        records.D7V1OfficialExecutionAttemptReservation,
        records.D7V1PreItem23ChronologyReceipt,
    ],
) -> records.D7V1PostselectionDescriptiveResult:
    attempt, receipt = parents
    return descriptive._derive_d7_v1_post_d6_descriptive_result(
        historical_plan_source=sources[0],
        parent_protocol_source=sources[1],
        parent_result_source=sources[2],
        parent_manifest_source=sources[3],
        parent_consumption_source=sources[4],
        parent_d6_decision_source=sources[5],
        parent_attempt=attempt,
        chronology_receipt=receipt,
    )


def _verify_result(
    candidate: records.D7V1PostselectionDescriptiveResult,
    sources: tuple[bytes, ...],
    parents: tuple[
        records.D7V1OfficialExecutionAttemptReservation,
        records.D7V1PreItem23ChronologyReceipt,
    ],
) -> records.D7V1PostselectionDescriptiveResult:
    attempt, receipt = parents
    return descriptive._verify_d7_v1_post_d6_descriptive_result(
        candidate,
        historical_plan_source=sources[0],
        parent_protocol_source=sources[1],
        parent_result_source=sources[2],
        parent_manifest_source=sources[3],
        parent_consumption_source=sources[4],
        parent_d6_decision_source=sources[5],
        parent_attempt=attempt,
        chronology_receipt=receipt,
    )


@pytest.fixture(scope="module")
def descriptive_result(
    historical_sources: tuple[bytes, ...],
    attempt_and_receipt: tuple[
        records.D7V1OfficialExecutionAttemptReservation,
        records.D7V1PreItem23ChronologyReceipt,
    ],
) -> records.D7V1PostselectionDescriptiveResult:
    return _derive_result(historical_sources, attempt_and_receipt)


def test_v1_entrypoint_sources_are_fresh_source_only_coordinates() -> None:
    forbidden_import_fragments = (
        "confirmation_official_execution",
        "confirmation_fused_",
        "confirmation_attempt_",
        "confirmation_authoritative_start_persistence",
        "confirmation_preseed_authority",
        "confirmation_seed_supply_contracts",
        "confirmation_source_closure",
        "confirmation_terminal_operations",
    )
    forbidden_calls = {
        "generate",
        "_supply_official_seed_values",
        "_execute_d7_seed_slot_primary_runtime",
        "run_d7_fused_verify_start_and_terminal_no_replace",
        "persist_d7_authoritative_start_transaction_no_replace",
        "persist_d7_prepared_terminal_no_replace",
        "_publish_d7_v1_pre_item23_records_no_replace",
        "produce_d7_official_result",
    }

    for path in (OFFICIAL_MODULE, PREPARER, RUNNER):
        imports = _import_names(path)
        assert not any(
            fragment in imported
            for imported in imports
            for fragment in forbidden_import_fragments
        )
        assert forbidden_calls.isdisjoint(_call_names(path))

    assert "produce_d7_v1_official_result" not in _call_names(PREPARER)
    assert "produce_d7_v1_official_result" not in _call_names(RUNNER)
    assert official.__all__ == ()


def test_importing_v1_entrypoints_restores_sys_path_and_has_no_official_side_effect() -> (
    None
):
    before_paths = _official_path_snapshot()

    _load_script(PREPARER, name="d7_v1_preparer_import_test")
    _load_script(RUNNER, name="d7_v1_runner_import_test")

    assert _official_path_snapshot() == before_paths


@pytest.mark.parametrize("path", (PREPARER, RUNNER))
def test_v1_entrypoint_bootstrap_failure_restores_sys_path(
    path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = tuple(sys.path)
    original_import = builtins.__import__

    def failing_import(
        name: str,
        globals: dict[str, object] | None = None,
        locals: dict[str, object] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name == "spirallens._repository_context":
            raise ImportError("test bootstrap failure")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", failing_import)
    with pytest.raises(ImportError, match="test bootstrap failure"):
        runpy.run_path(str(path), run_name=f"{path.stem}_bootstrap_failure")

    assert tuple(sys.path) == before


@pytest.mark.parametrize("path", (PREPARER, RUNNER))
def test_v1_entrypoint_help_is_read_only(path: Path) -> None:
    before_paths = _official_path_snapshot()

    completed = _run_script(path, "--help")

    assert completed.returncode == 0, completed.stderr
    assert "usage:" in completed.stdout
    assert _official_path_snapshot() == before_paths


@pytest.mark.parametrize("path", (PREPARER, RUNNER))
def test_v1_entrypoints_reject_the_wrong_cwd_without_side_effect(
    path: Path,
    tmp_path: Path,
) -> None:
    before_paths = _official_path_snapshot()

    completed = _run_script(path, cwd=tmp_path)

    assert completed.returncode != 0
    assert "requires the exact repository cwd" in completed.stderr
    assert _official_path_snapshot() == before_paths


def test_v1_preparer_rejects_route_drift_before_publication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_script(PREPARER, name="d7_v1_preparer_route_drift_test")
    verification = module["verification"]
    original = verification._expected_route_coordinates
    before_paths = _official_path_snapshot()

    def drifted(route: object) -> tuple[Path, Path, str, str]:
        store, staging, _runner, callable_name = original(route)
        return store, staging, "scripts/not-the-frozen-runner.py", callable_name

    monkeypatch.setattr(verification, "_expected_route_coordinates", drifted)
    monkeypatch.chdir(REPOSITORY)

    with pytest.raises(QualificationContractError, match="coordinates differ"):
        module["main"]([])
    assert _official_path_snapshot() == before_paths


def test_v1_runner_rejects_route_drift_before_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_script(RUNNER, name="d7_v1_runner_route_drift_test")
    verification = module["verification"]
    original = verification._expected_route_coordinates
    before_paths = _official_path_snapshot()

    def drifted(route: object) -> tuple[Path, Path, str, str]:
        store, staging, runner, _callable_name = original(route)
        return store, staging, runner, "spirallens.invalid:producer"

    monkeypatch.setattr(verification, "_expected_route_coordinates", drifted)
    monkeypatch.chdir(REPOSITORY)

    with pytest.raises(QualificationContractError, match="coordinates differ"):
        module["main"]([])
    assert _official_path_snapshot() == before_paths


def test_v1_preparer_fails_closed_without_calling_publisher_or_producer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_script(PREPARER, name="d7_v1_preparer_closed_test")
    publication = module["publication"]
    producer = module["official"]
    calls: list[str] = []

    def forbidden_call(*_args: object, **_kwargs: object) -> None:
        calls.append("called")
        raise AssertionError("an official operation was entered")

    monkeypatch.setattr(
        publication,
        "_publish_d7_v1_pre_item23_records_no_replace",
        forbidden_call,
    )
    monkeypatch.setattr(producer, "produce_d7_v1_official_result", forbidden_call)
    monkeypatch.chdir(REPOSITORY)
    before_paths = _official_path_snapshot()

    with pytest.raises(RuntimeError, match="source-only and blocked"):
        module["main"]([])
    assert calls == []
    assert _official_path_snapshot() == before_paths


def test_v1_runner_fails_closed_without_calling_the_official_producer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_script(RUNNER, name="d7_v1_runner_closed_test")
    producer = module["official"]
    calls: list[str] = []

    def forbidden_call(*_args: object, **_kwargs: object) -> None:
        calls.append("called")
        raise AssertionError("the official producer was entered")

    monkeypatch.setattr(producer, "produce_d7_v1_official_result", forbidden_call)
    monkeypatch.chdir(REPOSITORY)
    before_paths = _official_path_snapshot()

    with pytest.raises(RuntimeError, match="official dispatch is blocked"):
        module["main"]([])
    assert calls == []
    assert _official_path_snapshot() == before_paths


def test_v1_official_callable_is_a_non_authorizing_block() -> None:
    before_paths = _official_path_snapshot()

    with pytest.raises(
        QualificationContractError,
        match="launch-authority or execution-start transition",
    ):
        official.produce_d7_v1_official_result()

    assert _official_path_snapshot() == before_paths


def test_v1_descriptive_source_has_no_predecessor_result_or_code_dependency() -> None:
    source = Path(descriptive.__file__).read_text(encoding="utf-8")
    imports = _import_names(Path(descriptive.__file__))
    forbidden_paths = (
        "experiments/qualification/d7_spectral_moment_confirmation_v0_1/"
        "post-d6-descriptive-analysis-result.json",
        "experiments/qualification/d7_spectral_moment_confirmation_v0_1/"
        "post_d6_code/_post_d6_outputs_01_12.py",
        "experiments/qualification/d7_spectral_moment_confirmation_v0_1/"
        "post_d6_code/_post_d6_outputs_13_27.py",
        "experiments/qualification/d7_spectral_moment_confirmation_v0_1/"
        "post_d6_code/confirmation_post_d6_descriptive.py",
    )

    assert all(path not in source for path in forbidden_paths)
    assert all("post_d6_code" not in imported for imported in imports)
    assert "open" not in _call_names(Path(descriptive.__file__))
    assert "read_bytes" not in _call_names(Path(descriptive.__file__))
    assert "write_bytes" not in _call_names(Path(descriptive.__file__))


def test_v1_descriptive_result_closes_exact_six_reads_and_27_outputs(
    descriptive_result: records.D7V1PostselectionDescriptiveResult,
) -> None:
    document = descriptive_result.to_dict()
    payload = document["payload"]
    assert isinstance(payload, dict)
    trace = payload["read_trace"]
    outputs = payload["outputs"]
    bindings = payload["output_bindings"]
    assert isinstance(trace, list)
    assert isinstance(outputs, dict)
    assert isinstance(bindings, dict)

    assert [item["sequence"] for item in trace] == list(range(1, 7))
    assert [item["artifact_binding"]["artifact_role"] for item in trace] == [
        spec.role for spec in descriptive._INPUT_SPECS
    ]
    assert [item["artifact_binding"]["canonical_sha256"] for item in trace] == [
        spec.canonical_sha256 for spec in descriptive._INPUT_SPECS
    ]
    assert set(outputs) == set(descriptive._OUTPUT_IDS)
    assert set(bindings) == set(descriptive._OUTPUT_IDS)
    assert len(outputs) == 27
    for output_id, output in outputs.items():
        assert output["schema_version"] == (
            "spirallens.d7-v1-post-d6-descriptive-output.v0.1"
        )
        assert output["output_id"] == output_id
        assert bindings[output_id]["json_pointer"] == (f"/payload/outputs/{output_id}")
        assert (
            bindings[output_id]["target_schema_version"] == (output["schema_version"])
        )
        embedded = canonical_json_bytes(output)
        assert bindings[output_id]["byte_count"] == len(embedded)
        assert bindings[output_id]["canonical_sha256"] == sha256_bytes(embedded)


def test_v1_descriptive_retains_one_blocked_output_as_insufficient(
    descriptive_result: records.D7V1PostselectionDescriptiveResult,
) -> None:
    payload = descriptive_result.to_dict()["payload"]
    assert isinstance(payload, dict)
    outputs = payload["outputs"]
    assert isinstance(outputs, dict)
    blocked = [
        output_id
        for output_id, output in outputs.items()
        if output["status"] == "blocked"
    ]

    assert payload["status"] == "insufficient"
    assert blocked == ["amplitude-identifiability-support-separation"]
    assert all(
        output["status"] == "available"
        for output_id, output in outputs.items()
        if output_id not in blocked
    )
    blocked_data = outputs[blocked[0]]["data"]
    assert blocked_data["rerun_authorized"] is False
    assert blocked_data["persisted_representation"] == "dtype-shape-sha256-only"


def test_v1_descriptive_collapses_d2_boundary_repeats_and_retains_not_run(
    descriptive_result: records.D7V1PostselectionDescriptiveResult,
) -> None:
    payload = descriptive_result.to_dict()["payload"]
    assert isinstance(payload, dict)
    outputs = payload["outputs"]
    assert isinstance(outputs, dict)

    core_matrix = outputs["core-no-core-abstain-matrix"]["data"]
    assert core_matrix["source_boundary_repeat_row_count"] == 64
    assert core_matrix["unit_count"] == 32
    assert core_matrix["boundary_repeat_collapsed"] is True
    assert sum(row["count"] for row in core_matrix["rows"]) == 32
    assert sorted(row["count"] for row in core_matrix["rows"]) == [8, 8, 8, 8]

    repeat = outputs["boundary-repeat-exact-agreement"]["data"]
    assert repeat["paired_unit_count"] == 32
    assert repeat["exact_agreement_count"] == 32
    assert repeat["all_pairs_exact"] is True
    assert repeat["graph_cell_payload_byte_equality_claimed"] is False
    assert "max_candidate_symmetric_difference_rows" in repeat["agreement_scope_fields"]

    prerequisite = outputs["mandatory-prerequisite-failure-table"]["data"]
    assert prerequisite["core_primary_unit_count"] == 8
    assert prerequisite["loop_primary_unit_count"] == 16

    typed = outputs["typed-failure-coverage"]["data"]
    not_run_rows = [row for row in typed["rows"] if row["status"] == "not_run"]
    assert {(row["surface"], row["gate_id"]) for row in not_run_rows} == {
        ("advancement-decision", "d7"),
        ("advancement-decision", "d8"),
    }
    assert typed["not_run_row_count"] == 2
    assert typed["not_run_retained_as_distinct_status"] is True

    reference = outputs["reference-o2-error"]["data"]
    assert reference["obligation_ids"] == [
        "local-frame-gauge",
        "reference-orientation",
        "reference-reflection",
        "reference-rotation",
        "spin-two-double-angle",
    ]
    assert {row["obligation_id"] for row in reference["rows"]} == set(
        reference["obligation_ids"]
    )


def test_v1_descriptive_result_round_trips_under_the_large_record_cap(
    descriptive_result: records.D7V1PostselectionDescriptiveResult,
) -> None:
    reloaded = records.D7V1PostselectionDescriptiveResult.from_canonical_bytes(
        descriptive_result.canonical_bytes,
        expected_sha256=descriptive_result.canonical_sha256,
    )

    assert reloaded.canonical_bytes == descriptive_result.canonical_bytes
    assert reloaded.to_dict() == descriptive_result.to_dict()
    assert reloaded.byte_count <= records.D7_V1_POSTSELECTION_RESULT_MAX_RECORD_BYTES
    boundary = reloaded.to_dict()["claim_boundary"]
    assert boundary["claim_ceiling"] == "level_0"
    assert boundary["claim_delta"] == "none"
    assert not any(
        value
        for key, value in boundary.items()
        if key not in {"claim_ceiling", "claim_delta"}
    )


def test_v1_descriptive_exact_derivation_is_deterministic_and_verifies(
    historical_sources: tuple[bytes, ...],
    attempt_and_receipt: tuple[
        records.D7V1OfficialExecutionAttemptReservation,
        records.D7V1PreItem23ChronologyReceipt,
    ],
    descriptive_result: records.D7V1PostselectionDescriptiveResult,
) -> None:
    repeated = _derive_result(historical_sources, attempt_and_receipt)
    verified = _verify_result(
        descriptive_result,
        historical_sources,
        attempt_and_receipt,
    )

    assert repeated.canonical_bytes == descriptive_result.canonical_bytes
    assert repeated.canonical_sha256 == descriptive_result.canonical_sha256
    assert verified is descriptive_result


def test_v1_descriptive_rederivation_rejects_schema_valid_generic_outputs(
    historical_sources: tuple[bytes, ...],
    attempt_and_receipt: tuple[
        records.D7V1OfficialExecutionAttemptReservation,
        records.D7V1PreItem23ChronologyReceipt,
    ],
) -> None:
    attempt, receipt = attempt_and_receipt
    generic = records.D7V1PostselectionDescriptiveResult.create(
        record_id="d7-v1-generic-schema-valid-fake",
        repository_path=RESULT_PATH,
        parent_binding=records.D7V1ArtifactBinding.from_record(attempt),
        chronology_receipt_binding=records.D7V1ArtifactBinding.from_record(receipt),
        read_trace=tuple(
            records.D7V1ReadTraceEntry(
                sequence=sequence,
                artifact_binding=spec.binding(),
            )
            for sequence, spec in enumerate(descriptive._INPUT_SPECS, start=1)
        ),
        status="complete",
        outputs=tuple(
            records.D7V1DescriptiveOutput.create(
                output_id=output_id,
                status="available",
                data={"generic_schema_valid_placeholder": True},
            )
            for output_id in descriptive._OUTPUT_IDS
        ),
    )

    with pytest.raises(QualificationContractError, match="fresh six-input derivation"):
        _verify_result(generic, historical_sources, attempt_and_receipt)


def test_v1_descriptive_rederivation_rejects_rebound_output_tamper(
    historical_sources: tuple[bytes, ...],
    attempt_and_receipt: tuple[
        records.D7V1OfficialExecutionAttemptReservation,
        records.D7V1PreItem23ChronologyReceipt,
    ],
    descriptive_result: records.D7V1PostselectionDescriptiveResult,
) -> None:
    document = descriptive_result.to_dict()
    payload = document["payload"]
    assert isinstance(payload, dict)
    outputs = payload["outputs"]
    bindings = payload["output_bindings"]
    assert isinstance(outputs, dict)
    assert isinstance(bindings, dict)
    output_id = "parent-identity-table"
    output_document = outputs[output_id]
    assert isinstance(output_document, dict)
    output_data = output_document["data"]
    assert isinstance(output_data, dict)
    output_data["self_consistent_but_false_addition"] = True
    rebound_output = records.D7V1DescriptiveOutput.from_dict(output_document)
    bindings[output_id] = records._descriptive_output_binding(rebound_output).to_dict()
    changed = canonical_json_bytes(document)
    rebound_candidate = records.D7V1PostselectionDescriptiveResult.from_canonical_bytes(
        changed,
        expected_sha256=sha256_bytes(changed),
    )

    with pytest.raises(QualificationContractError, match="fresh six-input derivation"):
        _verify_result(rebound_candidate, historical_sources, attempt_and_receipt)


def test_v1_materialization_rejects_adjacent_descriptive_import_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = RepositoryContext(root=REPOSITORY)
    original = RepositoryContext.matches_imported_file

    def adjacent_for_descriptive(
        self: RepositoryContext,
        *,
        imported_file: str | Path | None,
        repository_path: str,
    ) -> bool:
        if repository_path == materialization._DESCRIPTIVE_MODULE_PATH:
            return False
        return original(
            self,
            imported_file=imported_file,
            repository_path=repository_path,
        )

    monkeypatch.setattr(
        RepositoryContext,
        "matches_imported_file",
        adjacent_for_descriptive,
    )

    with pytest.raises(
        QualificationContractError, match="descriptive module import origin"
    ):
        materialization._require_import_origins(repository)


def test_v1_descriptive_rejects_input_digest_tamper_before_parse(
    historical_sources: tuple[bytes, ...],
) -> None:
    original = historical_sources[0]
    tampered = bytes([original[0] ^ 1]) + original[1:]

    with pytest.raises(QualificationContractError, match="digest differs before parse"):
        descriptive._load_pinned(tampered, descriptive._INPUT_SPECS[0])


def test_v1_descriptive_rejects_noncanonical_historical_input(
    historical_sources: tuple[bytes, ...],
) -> None:
    document = parse_canonical_json(
        historical_sources[0], label="historical plan test source"
    )
    noncanonical = json.dumps(document, indent=2, sort_keys=True).encode("utf-8")
    spec = replace(
        descriptive._INPUT_SPECS[0],
        canonical_sha256=sha256_bytes(noncanonical),
        byte_count=len(noncanonical),
    )

    with pytest.raises(QualificationContractError, match="canonical"):
        descriptive._load_pinned(noncanonical, spec)


def test_v1_descriptive_rejects_a_pinned_input_schema_change(
    historical_sources: tuple[bytes, ...],
) -> None:
    document = parse_canonical_json(
        historical_sources[0], label="historical plan test source"
    )
    assert isinstance(document, dict)
    document["schema_version"] = "spirallens.invalid-plan.v0.1"
    changed = canonical_json_bytes(document)
    spec = replace(
        descriptive._INPUT_SPECS[0],
        canonical_sha256=sha256_bytes(changed),
        byte_count=len(changed),
    )

    with pytest.raises(QualificationContractError, match="schema differs"):
        descriptive._load_pinned(changed, spec)


def test_v1_descriptive_rejects_output_binding_drift(
    descriptive_result: records.D7V1PostselectionDescriptiveResult,
) -> None:
    document = descriptive_result.to_dict()
    payload = document["payload"]
    assert isinstance(payload, dict)
    outputs = payload["outputs"]
    assert isinstance(outputs, dict)
    output = outputs["parent-identity-table"]
    assert isinstance(output, dict)
    data = output["data"]
    assert isinstance(data, dict)
    data["tampered_after_binding"] = True
    changed = canonical_json_bytes(document)

    with pytest.raises(QualificationContractError, match="output_bindings"):
        records.D7V1PostselectionDescriptiveResult.from_canonical_bytes(
            changed,
            expected_sha256=sha256_bytes(changed),
        )


def test_v1_descriptive_result_digest_is_checked_before_parse(
    descriptive_result: records.D7V1PostselectionDescriptiveResult,
) -> None:
    source = descriptive_result.canonical_bytes
    tampered = bytes([source[0] ^ 1]) + source[1:]

    with pytest.raises(QualificationContractError, match="digest differs before parse"):
        records.D7V1PostselectionDescriptiveResult.from_canonical_bytes(
            tampered,
            expected_sha256=descriptive_result.canonical_sha256,
        )
