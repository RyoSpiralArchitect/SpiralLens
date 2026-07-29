from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest

from spirallens.core.canonical import (
    canonical_json_bytes,
    canonical_json_sha256,
)
from spirallens.qualification import advancement
from spirallens.qualification.advancement import (
    CARTESIAN_SELECTION_CONSTRUCTION_FAMILY_ID,
    ConfirmationDesignBodySet,
    IndependentConfirmationAdmissionSpec,
    LoadedAdvancementArtifact,
    LoadedScopeLimitedD6Decision,
    PersistedAdvancementIdentity,
    SelectionTerminalBinding,
    SurrogateAdvancementDecision,
)
from spirallens.qualification.common import (
    QualificationContractError,
    QualificationState,
)
from spirallens.qualification.confirmation_execution_design import (
    D7_CONFIRMATION_CORE_CELL_COUNT,
    D7_CONFIRMATION_LOOP_CELL_COUNT,
    D7_CONFIRMATION_PRIMARY_UNIT_COUNT,
    MAX_D7_CONFIRMATION_EXECUTION_DRAFT_BYTES,
    D7ConfirmationExecutionDesignDraft,
    build_seed_free_d7_confirmation_execution_design,
)
from spirallens.qualification.confirmation_protocol import (
    D6_DECISION_REPOSITORY_PATH,
)
from spirallens.qualification.persistence import LoadedQualificationProtocol
from spirallens.qualification.preparation import (
    build_closed_d0_d5_selection_protocol,
)
from spirallens.qualification.protocol import (
    EngineBinding,
    ModuleDigest,
    RegistryBinding,
)


def _parent_protocol(
    *,
    selection_seeds: tuple[int, int] = (400001, 400002),
) -> LoadedQualificationProtocol:
    protocol = build_closed_d0_d5_selection_protocol(
        engine=EngineBinding(
            repository="RyoSpiralArchitect/SpiralLens",
            commit="1" * 40,
            modules=(
                ModuleDigest(
                    "spirallens.qualification.runner",
                    "2" * 64,
                ),
            ),
        ),
        registry=RegistryBinding(
            registry_source_sha256="3" * 64,
            registry_canonical_sha256="4" * 64,
            referent_canonical_sha256="5" * 64,
        ),
        selection_seeds=selection_seeds,
    )
    return LoadedQualificationProtocol(
        protocol=protocol,
        source_path=Path("/tmp/d7-test-parent-protocol.json"),
        source_bytes=protocol.canonical_bytes,
        source_sha256=protocol.canonical_sha256,
        canonical_sha256=protocol.canonical_sha256,
    )


def _authoritative_d6(
    parent: LoadedQualificationProtocol,
    *,
    decision_id: str = "d7-test-authoritative-d6-decision-v0-1",
    decision_source_commit: str = "d" * 40,
) -> LoadedScopeLimitedD6Decision:
    protocol = parent.protocol
    bodies = ConfirmationDesignBodySet.from_protocol(protocol)
    implementation = protocol.implementation_registry
    terminal = SelectionTerminalBinding(
        protocol_id=protocol.protocol_id,
        protocol_source_sha256=parent.source_sha256,
        protocol_canonical_sha256=parent.canonical_sha256,
        selection_freeze_sha256="6" * 64,
        selection_attempt_claim_sha256="7" * 64,
        launch_authorization_sha256="8" * 64,
        result_id="d0-d5-test-terminal-result-v0-1",
        result_sha256="9" * 64,
        result_evidence_root_sha256="a" * 64,
        terminal_manifest_sha256="b" * 64,
        consumption_sha256="c" * 64,
        selection_generator_family_id=implementation.generator_family_id,
        selection_construction_family_id=(CARTESIAN_SELECTION_CONSTRUCTION_FAMILY_ID),
        surrogate_estimator_id=implementation.surrogate_estimator_id,
        surrogate_trivialization_id=(implementation.surrogate_trivialization_id),
        selection_implementation_registry_sha256=(
            canonical_json_sha256(implementation.to_dict())
        ),
        graph_axes_sha256=bodies.graph_axes_sha256,
        required_cells_manifest_sha256=bodies.required_cells_sha256,
        required_stress_strata_sha256=bodies.required_stress_sha256,
        locked_thresholds_sha256=bodies.thresholds_sha256,
        locked_aggregation_sha256=bodies.aggregation_sha256,
        gate_states=tuple(
            (f"d{index}", QualificationState.PASS.value) for index in range(6)
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
    admission = IndependentConfirmationAdmissionSpec.from_selection(
        terminal,
        admission_spec_id="d7-test-confirmation-admission-v0-1",
    )
    decision = SurrogateAdvancementDecision.seal(
        decision_id=decision_id,
        decision_source_commit=decision_source_commit,
        decision_source_binding_sha256="e" * 64,
        selection_terminal=terminal,
        admission_spec=admission,
    )
    loaded_artifact = LoadedAdvancementArtifact(
        artifact=decision,
        identity=PersistedAdvancementIdentity(
            path=(Path("/tmp/d7-test-repository") / D6_DECISION_REPOSITORY_PATH),
            source_sha256=decision.canonical_sha256,
            canonical_sha256=decision.canonical_sha256,
            byte_count=len(decision.canonical_bytes),
            parent_directory_fsync_verified=True,
        ),
        source_bytes=decision.canonical_bytes,
    )
    return advancement._build_authoritative_loaded_d6_decision(
        loaded_artifact,
        current_loader_source_commit="f" * 40,
        current_loader_source_binding_sha256="0" * 64,
    )


def _loaded_inputs() -> tuple[
    LoadedScopeLimitedD6Decision,
    LoadedQualificationProtocol,
]:
    parent = _parent_protocol()
    return _authoritative_d6(parent), parent


def _build_design() -> D7ConfirmationExecutionDesignDraft:
    loaded_d6, parent = _loaded_inputs()
    return build_seed_free_d7_confirmation_execution_design(
        loaded_d6=loaded_d6,
        parent_protocol=parent,
    )


def test_seed_free_design_has_exact_repeated_measures_inventory() -> None:
    design = _build_design()
    inventory = design.inventory
    primary_ids = {item.primary_unit_id for item in inventory.primary_units}

    assert len(primary_ids) == D7_CONFIRMATION_PRIMARY_UNIT_COUNT == 64
    assert len(inventory.core_cells) == D7_CONFIRMATION_CORE_CELL_COUNT == 192
    assert len(inventory.loop_cells) == D7_CONFIRMATION_LOOP_CELL_COUNT == 1152
    assert Counter(item.primary_unit_id for item in inventory.core_cells) == Counter(
        {primary_id: 3 for primary_id in primary_ids}
    )
    assert Counter(item.primary_unit_id for item in inventory.loop_cells) == Counter(
        {primary_id: 18 for primary_id in primary_ids}
    )
    assert len(inventory.expected_strata) == 6
    assert all(len(item.primary_unit_ids) == 32 for item in inventory.expected_strata)

    document = design.to_dict()
    assert document["status"] == "seed-free-execution-design-not-frozen"
    assert document["d7_state"] == "not_run"
    assert document["d8_state"] == "not_run"
    assert set(document["authority"].values()) == {False}
    assert document["seed_policy"]["concrete_seed_inventory_present"] is False
    assert document["inventory"]["execution_inventory_frozen"] is False


def test_design_joins_every_full_parent_body_without_relabeling_manifests() -> None:
    loaded_d6, parent = _loaded_inputs()
    design = build_seed_free_d7_confirmation_execution_design(
        loaded_d6=loaded_d6,
        parent_protocol=parent,
    )
    bodies = ConfirmationDesignBodySet.from_protocol(parent.protocol)
    terminal = loaded_d6.decision.selection_terminal
    admission = loaded_d6.decision.confirmation_admission_spec
    binding = design.parent

    assert binding.protocol_source_sha256 == parent.source_sha256
    assert binding.protocol_canonical_sha256 == parent.canonical_sha256
    assert binding.graph_axes_sha256 == bodies.graph_axes_sha256
    assert binding.required_cells_manifest_sha256 == (bodies.required_cells_sha256)
    assert binding.required_stress_strata_sha256 == (bodies.required_stress_sha256)
    assert binding.locked_thresholds_sha256 == bodies.thresholds_sha256
    assert binding.locked_aggregation_sha256 == bodies.aggregation_sha256
    assert (
        binding.required_cells_manifest_sha256
        == terminal.required_cells_manifest_sha256
        == admission.required_cells_manifest_sha256
    )
    assert (
        binding.required_stress_strata_sha256
        == terminal.required_stress_strata_sha256
        == admission.required_stress_strata_sha256
    )

    compatibility = design.manifest_compatibility.to_dict()
    assert compatibility["structural_template_match_observed"] is True
    assert (
        compatibility["parent_structural_projection_sha256"]
        == compatibility["confirmation_structural_projection_sha256"]
    )
    assert compatibility["exact_parent_cells_manifest_satisfied"] is False
    assert compatibility["exact_parent_stress_manifest_satisfied"] is False
    assert compatibility["structural_match_is_exact_parent_hash_satisfaction"] is False
    assert compatibility["d6_admission_spec_satisfied"] is False
    assert (
        compatibility["parent_required_cells_manifest_sha256"]
        != compatibility["confirmation_cells_manifest_sha256"]
    )
    assert (
        compatibility["parent_required_stress_strata_sha256"]
        != compatibility["confirmation_stress_strata_sha256"]
    )


def test_strict_reload_reconstructs_authority_and_rejects_mutation() -> None:
    loaded_d6, parent = _loaded_inputs()
    design = build_seed_free_d7_confirmation_execution_design(
        loaded_d6=loaded_d6,
        parent_protocol=parent,
    )

    restored = D7ConfirmationExecutionDesignDraft.from_canonical_bytes(
        design.canonical_bytes,
        expected_sha256=design.canonical_sha256,
        loaded_d6=loaded_d6,
        parent_protocol=parent,
    )
    assert restored == design

    with pytest.raises(QualificationContractError, match="SHA-256"):
        D7ConfirmationExecutionDesignDraft.from_canonical_bytes(
            design.canonical_bytes,
            expected_sha256="1" * 64,
            loaded_d6=loaded_d6,
            parent_protocol=parent,
        )

    mutated = design.to_dict()
    mutated["status"] = "caller-claimed-frozen"
    mutated_bytes = canonical_json_bytes(mutated)
    with pytest.raises(
        QualificationContractError,
        match="authoritative reconstruction",
    ):
        D7ConfirmationExecutionDesignDraft.from_canonical_bytes(
            mutated_bytes,
            expected_sha256=hashlib.sha256(mutated_bytes).hexdigest(),
            loaded_d6=loaded_d6,
            parent_protocol=parent,
        )

    noncanonical = design.canonical_bytes.replace(b"{", b"{ ", 1)
    with pytest.raises(QualificationContractError, match="not canonical"):
        D7ConfirmationExecutionDesignDraft.from_canonical_bytes(
            noncanonical,
            expected_sha256=hashlib.sha256(noncanonical).hexdigest(),
            loaded_d6=loaded_d6,
            parent_protocol=parent,
        )

    duplicate_key = b'{"schema_version":"one","schema_version":"two"}'
    with pytest.raises(QualificationContractError, match="duplicate JSON key"):
        D7ConfirmationExecutionDesignDraft.from_canonical_bytes(
            duplicate_key,
            expected_sha256=hashlib.sha256(duplicate_key).hexdigest(),
            loaded_d6=loaded_d6,
            parent_protocol=parent,
        )

    oversized = b" " * (MAX_D7_CONFIRMATION_EXECUTION_DRAFT_BYTES + 1)
    with pytest.raises(QualificationContractError, match="within the cap"):
        D7ConfirmationExecutionDesignDraft.from_canonical_bytes(
            oversized,
            expected_sha256=hashlib.sha256(oversized).hexdigest(),
            loaded_d6=loaded_d6,
            parent_protocol=parent,
        )


def test_parent_protocol_substitution_is_rejected_before_design_build() -> None:
    loaded_d6, _parent = _loaded_inputs()
    substituted = _parent_protocol(
        selection_seeds=(500001, 500002),
    )

    with pytest.raises(
        QualificationContractError,
        match="does not join",
    ):
        build_seed_free_d7_confirmation_execution_design(
            loaded_d6=loaded_d6,
            parent_protocol=substituted,
        )


def test_design_binds_the_exact_authoritative_d6_identity() -> None:
    parent = _parent_protocol()
    first_d6 = _authoritative_d6(parent)
    second_d6 = _authoritative_d6(
        parent,
        decision_id="d7-test-alternate-d6-decision-v0-1",
        decision_source_commit="a" * 40,
    )
    first = build_seed_free_d7_confirmation_execution_design(
        loaded_d6=first_d6,
        parent_protocol=parent,
    )
    second = build_seed_free_d7_confirmation_execution_design(
        loaded_d6=second_d6,
        parent_protocol=parent,
    )

    assert first.parent == second.parent
    assert first.parent_d6.d6_decision_id != second.parent_d6.d6_decision_id
    assert first.canonical_sha256 != second.canonical_sha256
    with pytest.raises(
        QualificationContractError,
        match="authoritative reconstruction",
    ):
        D7ConfirmationExecutionDesignDraft.from_canonical_bytes(
            first.canonical_bytes,
            expected_sha256=first.canonical_sha256,
            loaded_d6=second_d6,
            parent_protocol=parent,
        )


def test_live_design_cannot_be_reconstructed_with_substituted_members() -> None:
    design = _build_design()

    with pytest.raises(
        QualificationContractError,
        match="must be produced from",
    ):
        replace(
            design.parent,
            protocol_id="unbound-parent-protocol",
        )
    with pytest.raises(
        QualificationContractError,
        match="must be produced by",
    ):
        replace(
            design,
            domain=replace(
                design.domain,
                domain_id="unbound-domain",
            ),
        )
