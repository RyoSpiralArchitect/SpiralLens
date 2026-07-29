from __future__ import annotations

import inspect
import json
import os
import stat
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from spirallens import qualification
from spirallens.qualification import advancement
from spirallens.qualification.advancement import (
    CARTESIAN_SELECTION_CONSTRUCTION_FAMILY_ID,
    D7_NOT_RUN_REASON_CODES,
    D8_NOT_RUN_REASON_CODES,
    SURROGATE_ADVANCEMENT_SCOPE,
    SURROGATE_PROFILE_ID,
    IndependentConfirmationAdmissionSpec,
    SelectionTerminalBinding,
    SurrogateAdvancementDecision,
    advancement_source_binding_sha256,
    build_current_advancement_source_binding,
    load_scope_limited_d6_decision,
    validate_advancement_decision_source,
)
from spirallens.qualification.common import (
    QualificationContractError,
    QualificationState,
)


def _binding() -> SelectionTerminalBinding:
    return SelectionTerminalBinding(
        protocol_id="d0-d5-f2-cartesian-selection-v0-1",
        protocol_source_sha256="1" * 64,
        protocol_canonical_sha256="1" * 64,
        selection_freeze_sha256="2" * 64,
        selection_attempt_claim_sha256="3" * 64,
        launch_authorization_sha256="4" * 64,
        result_id="d0-d5-f2-cartesian-selection-result-v0-1",
        result_sha256="5" * 64,
        result_evidence_root_sha256="6" * 64,
        terminal_manifest_sha256="7" * 64,
        consumption_sha256="8" * 64,
        selection_generator_family_id="cartesian-fourier-domain-v0.1",
        selection_construction_family_id=(
            CARTESIAN_SELECTION_CONSTRUCTION_FAMILY_ID
        ),
        surrogate_estimator_id=(
            "interleaved-first-harmonic-graph-local-direction-v0.4"
        ),
        surrogate_trivialization_id=(
            "cartesian-quadrature-pair-orientation-v0.2"
        ),
        selection_implementation_registry_sha256="e" * 64,
        graph_axes_sha256="9" * 64,
        required_cells_manifest_sha256="a" * 64,
        required_stress_strata_sha256="b" * 64,
        locked_thresholds_sha256="c" * 64,
        locked_aggregation_sha256="d" * 64,
        gate_states=tuple(
            (f"d{index}", QualificationState.PASS.value)
            for index in range(6)
        ),
        gate_claim_scopes=(
            ("d0", "engine-and-protocol-contracts"),
            ("d1", "cartesian-surrogate-and-representation-development"),
            ("d2", "cartesian-surrogate-only"),
            ("d3", "cartesian-surrogate-and-representation-development"),
            ("d4", "cartesian-surrogate-only"),
            ("d5", "cartesian-surrogate-only"),
        ),
    )


def _spec(
    binding: SelectionTerminalBinding | None = None,
) -> IndependentConfirmationAdmissionSpec:
    return IndependentConfirmationAdmissionSpec.from_selection(
        _binding() if binding is None else binding,
        admission_spec_id=(
            "cartesian-surrogate-independent-family-admission-v0-1"
        ),
    )


def _decision() -> SurrogateAdvancementDecision:
    binding = _binding()
    return SurrogateAdvancementDecision.seal(
        decision_id="cartesian-surrogate-d6-decision-v0-1",
        decision_source_commit="f" * 40,
        decision_source_binding_sha256="e" * 64,
        selection_terminal=binding,
        admission_spec=_spec(binding),
    )


def _git(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _source_repository(tmp_path: Path) -> tuple[Path, str]:
    repository = tmp_path / "source-repository"
    (repository / "src" / "spirallens" / "qualification").mkdir(
        parents=True
    )
    (repository / "scripts").mkdir()
    (repository / "src" / "spirallens" / "__init__.py").write_text(
        "__version__ = 'test'\n",
        encoding="utf-8",
    )
    (
        repository
        / "src"
        / "spirallens"
        / "qualification"
        / "advancement.py"
    ).write_text("SOURCE = 'test'\n", encoding="utf-8")
    (
        repository / "scripts" / "seal_d6_surrogate_advancement.py"
    ).write_text("raise SystemExit(0)\n", encoding="utf-8")
    _git(repository, "init", "-q")
    _git(repository, "config", "user.name", "SpiralLens Test")
    _git(repository, "config", "user.email", "test@spirallens.invalid")
    _git(repository, "add", "src", "scripts/seal_d6_surrogate_advancement.py")
    _git(repository, "commit", "-q", "-m", "freeze source surface")
    return repository, _git(repository, "rev-parse", "HEAD")


def test_decision_is_one_embedded_scope_limited_bundle() -> None:
    decision = _decision()
    document = decision.to_dict()

    assert document["selection_profile_id"] == SURROGATE_PROFILE_ID
    assert document["advancement_scope"] == SURROGATE_ADVANCEMENT_SCOPE
    assert document["d6"] == {
        "scope": SURROGATE_ADVANCEMENT_SCOPE,
        "state": "pass",
    }
    assert document["d7"] == {
        "state": "not_run",
        "reason_codes": list(D7_NOT_RUN_REASON_CODES),
    }
    assert document["d8"] == {
        "state": "not_run",
        "reason_codes": list(D8_NOT_RUN_REASON_CODES),
    }
    assert (
        document["confirmation_access_facts_are_external_attestations"]
        is True
    )
    assert document["cryptographic_confirmation_access_proof"] is False
    assert document["authoritative_commit_validation_required"] is True
    assert document["authoritative_commit_validation_embedded"] is False
    assert "confirmation_admission_spec" in document
    assert "confirmation_admission_spec_id" not in document
    assert set(document["authority"].values()) == {False}
    assert decision == SurrogateAdvancementDecision.from_dict(document)

    tampered = json.loads(decision.canonical_bytes)
    tampered["unexpected"] = False
    with pytest.raises(QualificationContractError, match="fields differ"):
        SurrogateAdvancementDecision.from_dict(tampered)


def test_terminal_binding_is_structural_until_authoritative_loader_rejoins_it() -> None:
    document = _binding().to_dict()

    assert document["historical_terminal_companion_validation_required"] is True
    assert document["historical_terminal_companion_validation_embedded"] is False
    assert "historical_terminal_verified" not in document
    assert document["current_engine_reexecution_verified"] is False


def test_admission_locks_estimator_trivialization_and_implementation_registry() -> None:
    binding = _binding()
    spec = _spec(binding)

    assert spec.required_surrogate_estimator_id == binding.surrogate_estimator_id
    assert (
        spec.required_surrogate_trivialization_id
        == binding.surrogate_trivialization_id
    )
    assert (
        spec.selection_implementation_registry_sha256
        == binding.selection_implementation_registry_sha256
    )
    mismatched = replace(
        spec,
        required_surrogate_estimator_id="different-estimator-v0.1",
    )
    with pytest.raises(
        QualificationContractError,
        match="differs from the selected terminal",
    ):
        SurrogateAdvancementDecision.seal(
            decision_id="cartesian-surrogate-d6-decision-v0-1",
            decision_source_commit="f" * 40,
            decision_source_binding_sha256="e" * 64,
            selection_terminal=binding,
            admission_spec=mismatched,
        )


def test_no_label_only_d7_or_caller_bytes_d8_execution_surface_is_exported() -> None:
    forbidden = {
        "validate_confirmation_family_candidate",
        "validate_d8_replay_promotion",
        "load_advancement_artifact",
        "write_advancement_artifact",
    }

    assert forbidden.isdisjoint(advancement.__all__)
    assert forbidden.isdisjoint(qualification.__all__)
    assert not hasattr(qualification, "validate_confirmation_family_candidate")
    assert not hasattr(qualification, "validate_d8_replay_promotion")
    assert not hasattr(qualification, "write_advancement_artifact")


def test_authoritative_surface_reloads_companions_internally() -> None:
    publish_parameters = inspect.signature(
        advancement.publish_scope_limited_d6_decision
    ).parameters
    load_parameters = inspect.signature(
        advancement.load_scope_limited_d6_decision
    ).parameters

    for forbidden in (
        "result",
        "protocol",
        "terminal_identity",
        "consumption",
        "admission_spec",
        "decision",
    ):
        assert forbidden not in publish_parameters
        assert forbidden not in load_parameters
    for required in (
        "launch_descriptor",
        "terminal_manifest_sha256",
        "terminal_result_sha256",
        "terminal_consumption_sha256",
    ):
        assert required in publish_parameters
        assert required in load_parameters


def test_source_binding_covers_complete_tracked_package_and_rejects_drift(
    tmp_path: Path,
) -> None:
    repository, commit = _source_repository(tmp_path)

    current_commit, digest = build_current_advancement_source_binding(
        repository_root=repository
    )
    assert current_commit == commit
    assert digest == advancement_source_binding_sha256(
        repository_root=repository,
        commit=commit,
    )

    injected = repository / "src" / "spirallens" / "injected.py"
    injected.write_text("INJECTED = True\n", encoding="utf-8")
    with pytest.raises(
        QualificationContractError,
        match="Python surface differs",
    ):
        build_current_advancement_source_binding(repository_root=repository)
    injected.unlink()

    tracked = repository / "src" / "spirallens" / "__init__.py"
    tracked.write_text("__version__ = 'dirty'\n", encoding="utf-8")
    with pytest.raises(
        QualificationContractError,
        match="not the clean current commit blob",
    ):
        build_current_advancement_source_binding(repository_root=repository)

    assert advancement_source_binding_sha256(
        repository_root=repository,
        commit=commit,
    ) == digest


def test_authoritative_loader_rejects_failed_current_source_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, _commit = _source_repository(tmp_path)
    persisted = advancement._write_advancement_artifact(
        tmp_path / "decision.json",
        _decision(),
    )
    monkeypatch.setattr(
        advancement,
        "_rebuild_selection_terminal_binding",
        lambda **_kwargs: (_binding(), repository),
    )

    def reject_current_source(
        *,
        repository_root: str | Path | None = None,
    ) -> tuple[str, str]:
        del repository_root
        raise QualificationContractError("injected dirty current source")

    monkeypatch.setattr(
        advancement,
        "build_current_advancement_source_binding",
        reject_current_source,
    )

    with pytest.raises(
        QualificationContractError,
        match="injected dirty current source",
    ):
        load_scope_limited_d6_decision(
            persisted.identity.path,
            expected_source_sha256=persisted.identity.source_sha256,
            expected_canonical_sha256=persisted.identity.canonical_sha256,
            expected_decision_id="cartesian-surrogate-d6-decision-v0-1",
            expected_admission_spec_id=(
                "cartesian-surrogate-independent-family-admission-v0-1"
            ),
            launch_descriptor=tmp_path / "unused-launch.json",
            launch_descriptor_source_sha256="0" * 64,
            launch_descriptor_canonical_sha256="0" * 64,
            terminal_manifest_sha256="0" * 64,
            terminal_result_sha256="0" * 64,
            terminal_consumption_sha256="0" * 64,
        )


def test_fabricated_source_binding_cannot_pass_authoritative_validation(
    tmp_path: Path,
) -> None:
    repository, _commit = _source_repository(tmp_path)

    with pytest.raises(
        QualificationContractError,
        match="does not resolve exactly",
    ):
        validate_advancement_decision_source(
            _decision(),
            repository_root=repository,
        )


def test_recorded_d6_bundle_authoritatively_reloads_from_committed_lineage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = Path(__file__).resolve().parents[1]
    source_gate_calls: list[tuple[str, str]] = []
    original_source_gate = (
        advancement.build_current_advancement_source_binding
    )

    def record_current_source_gate(
        *,
        repository_root: str | Path | None = None,
    ) -> tuple[str, str]:
        result = original_source_gate(repository_root=repository_root)
        source_gate_calls.append(result)
        return result

    monkeypatch.setattr(
        advancement,
        "build_current_advancement_source_binding",
        record_current_source_gate,
    )
    loaded = load_scope_limited_d6_decision(
        (
            repository
            / "experiments"
            / "qualification"
            / "d0_d5_f2_cartesian_selection_v0_1"
            / "d6-surrogate-advancement-decision.json"
        ),
        expected_source_sha256=(
            "c1c3fbbb9a06e8df120755dcf159e015"
            "636d96993bd6ec3a6792312618587a07"
        ),
        expected_canonical_sha256=(
            "c1c3fbbb9a06e8df120755dcf159e015"
            "636d96993bd6ec3a6792312618587a07"
        ),
        expected_decision_id="cartesian-surrogate-d6-decision-v0-1",
        expected_admission_spec_id=(
            "cartesian-surrogate-independent-family-admission-v0-1"
        ),
        launch_descriptor=(
            repository
            / "experiments"
            / "qualification"
            / "d0_d5_f2_cartesian_selection_v0_1"
            / "launch.json"
        ),
        launch_descriptor_source_sha256=(
            "a6a8f8a2c3c47cc76053646440cec94c"
            "6bf7da6a6794a2bdda2e4a2cfa28f300"
        ),
        launch_descriptor_canonical_sha256=(
            "a6a8f8a2c3c47cc76053646440cec94c"
            "6bf7da6a6794a2bdda2e4a2cfa28f300"
        ),
        terminal_manifest_sha256=(
            "518b66d715cf9bd05e12de62cb5681ec"
            "63ec7f978fd4d2538ba3c2594deed4b1"
        ),
        terminal_result_sha256=(
            "44749d8d237b8b35874099c605f8de3d"
            "76130691ce8beb92e1ccf80fa368c13a"
        ),
        terminal_consumption_sha256=(
            "a42ae9cffb6a2c87de6ed645e0982e85"
            "b09046a4ed5ad3f815a8a8ce38c0cadb"
        ),
    )

    assert loaded.committed_artifact_verified is True
    assert loaded.historical_terminal_companions_verified is True
    assert loaded.decision_source_surface_verified is True
    assert loaded.current_loader_source_surface_verified is True
    assert source_gate_calls == [
        (
            loaded.current_loader_source_commit,
            loaded.current_loader_source_binding_sha256,
        )
    ]
    assert loaded.embedded_admission_spec_verified is True
    assert loaded.current_source_compatibility_verified is False
    assert loaded.historical_engine_reexecution_verified is False
    assert loaded.historical_d1_recomputation_performed is False
    assert loaded.decision.d6_state == "pass"
    assert loaded.decision.d7_state == "not_run"
    assert loaded.decision.d8_state == "not_run"


def test_private_writer_returns_typed_visible_artifact_when_parent_fsync_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_fsync = os.fsync

    def fail_only_for_directory(file_descriptor: int) -> None:
        if stat.S_ISDIR(os.fstat(file_descriptor).st_mode):
            raise OSError("injected parent-directory fsync failure")
        original_fsync(file_descriptor)

    monkeypatch.setattr(advancement.os, "fsync", fail_only_for_directory)
    writer = advancement._write_advancement_artifact
    path = tmp_path / "decision.json"
    loaded = writer(path, _decision())

    assert loaded.identity.path == path
    assert loaded.identity.parent_directory_fsync_verified is False
    assert loaded.source_bytes == _decision().canonical_bytes
    with pytest.raises(TypeError):
        qualification.LoadedScopeLimitedD6Decision(loaded)  # type: ignore[call-arg]
    with pytest.raises(QualificationContractError, match="overwrite"):
        writer(path, _decision())
