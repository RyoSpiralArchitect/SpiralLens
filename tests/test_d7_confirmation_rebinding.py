from __future__ import annotations

import hashlib
import inspect
from dataclasses import replace
from pathlib import Path

import pytest
from test_d7_confirmation_execution_design import (
    _authoritative_d6,
    _loaded_inputs,
    _parent_protocol,
)

import spirallens
from spirallens import qualification
from spirallens.core.canonical import canonical_json_bytes, sha256_bytes
from spirallens.qualification.advancement import (
    LoadedScopeLimitedD6Decision,
)
from spirallens.qualification.common import QualificationContractError
from spirallens.qualification.confirmation_execution_design import (
    D7ConfirmationExecutionDesignDraft,
    build_seed_free_d7_confirmation_execution_design,
)
from spirallens.qualification.confirmation_rebinding import (
    MAX_D6_D7_STRUCTURAL_REBINDING_AMENDMENT_BYTES,
    D6D7StructuralRebindingAmendment,
    build_d6_d7_structural_rebinding_amendment,
)
from spirallens.qualification.persistence import LoadedQualificationProtocol


def _inputs() -> tuple[
    LoadedScopeLimitedD6Decision,
    LoadedQualificationProtocol,
    D7ConfirmationExecutionDesignDraft,
]:
    loaded_d6, parent = _loaded_inputs()
    design = build_seed_free_d7_confirmation_execution_design(
        loaded_d6=loaded_d6,
        parent_protocol=parent,
    )
    return loaded_d6, parent, design


def _amendment() -> D6D7StructuralRebindingAmendment:
    loaded_d6, parent, design = _inputs()
    return build_d6_d7_structural_rebinding_amendment(
        loaded_d6=loaded_d6,
        parent_protocol=parent,
        seed_free_design=design,
    )


def test_amendment_separates_exact_carry_forward_from_structural_rebinding() -> None:
    amendment = _amendment()
    document = amendment.to_dict()
    exact = document["exact_carry_forward"]
    structural = document["structural_rebinding"]
    historical = document["historical_d6"]

    assert document["schema_version"] == (
        "spirallens.d6-d7-structural-rebinding-amendment.v0.1"
    )
    assert document["amendment_id"] == (
        "d6-v0-1-to-d7-spectral-moment-structural-rebinding-v0-1"
    )
    assert document["status"] == (
        "structural-rebinding-proposal-encoded-not-reviewed-or-published"
    )
    assert document["record_scope"] == ("d7-spectral-moment-cells-and-stress-only")
    assert document["seed_free_design"]["design_schema_version"] == (
        "spirallens.d7-confirmation-execution-design-draft.v0.2"
    )
    assert document["seed_free_design"]["draft_id"] == (
        "d7-spectral-moment-seed-free-execution-design-v0-2"
    )
    assert amendment.canonical_sha256 == (
        "2fac7476a27b5474e04461e8498201b7db8b1dcc9a53b0963acf4f0cb3971677"
    )
    assert len(amendment.canonical_bytes) == 8885
    assert exact["graph_axes_exact_match"] is True
    assert exact["thresholds_exact_match"] is True
    assert exact["parent_graph_axes_sha256"] == exact["successor_graph_axes_sha256"]
    assert exact["parent_thresholds_sha256"] == exact["successor_thresholds_sha256"]
    assert structural["cells_exact_match"] is False
    assert structural["stress_exact_match"] is False
    assert structural["structural_projection_match"] is True
    assert (
        structural["parent_structural_projection_sha256"]
        == structural["successor_structural_projection_sha256"]
    )
    assert structural["successor_fulfillment_rule_encoded"] is True
    assert structural["successor_fulfillment_rule_reviewed"] is False
    assert structural["successor_fulfillment_rule_published"] is False
    assert structural["effective_for_admission"] is False
    assert structural["rebinding_satisfies_historical_exact_hashes"] is False
    assert historical["decision_bytes_mutated"] is False
    assert historical["admission_bytes_mutated"] is False
    assert historical["historical_admission_reinterpreted"] is False
    assert historical["d6_admission_spec_satisfied"] is False


def test_amendment_binds_every_authoritative_identity_and_keeps_work_open() -> None:
    loaded_d6, parent, design = _inputs()
    amendment = build_d6_d7_structural_rebinding_amendment(
        loaded_d6=loaded_d6,
        parent_protocol=parent,
        seed_free_design=design,
    )
    document = amendment.to_dict()
    parent_d6 = document["parent_d6"]
    parent_protocol = document["parent_protocol"]
    deferred = document["deferred"]

    assert parent_d6["d6_decision_canonical_sha256"] == (
        loaded_d6.identity.canonical_sha256
    )
    assert parent_d6["admission_spec_sha256"] == (
        loaded_d6.decision.confirmation_admission_spec.canonical_sha256
    )
    assert parent_protocol["protocol_canonical_sha256"] == (parent.canonical_sha256)
    assert document["seed_free_design"]["canonical_sha256"] == (design.canonical_sha256)
    assert deferred["d7_implementation_registry_bound"] is False
    assert deferred["d7_aggregation_application_bound"] is False
    assert deferred["construction_diversity_reviewed"] is False
    assert deferred["source_closure_verified"] is False
    assert deferred["family_admitted"] is False
    assert document["canonical_artifact_published"] is False
    assert document["d7_successor_admission_complete"] is False
    assert document["d7_state"] == "not_run"
    assert document["d8_state"] == "not_run"
    assert set(document["authority"].values()) == {False}


def test_amendment_contains_no_parent_seed_values_or_seed_accepting_api() -> None:
    amendment = _amendment()
    document = amendment.to_dict()

    assert b"400001" not in amendment.canonical_bytes
    assert b"400002" not in amendment.canonical_bytes
    assert set(
        inspect.signature(build_d6_d7_structural_rebinding_amendment).parameters
    ) == {"loaded_d6", "parent_protocol", "seed_free_design"}
    assert document["mapping_rules"]["seed_mapping"] == [
        {
            "parent_seed_ordinal": 0,
            "successor_seed_slot_id": "confirmation-seed-slot-00",
        },
        {
            "parent_seed_ordinal": 1,
            "successor_seed_slot_id": "confirmation-seed-slot-01",
        },
    ]
    assert len(document["mapping_rules"]["case_mapping"]) == 4
    assert document["mapping_rules"]["numeric_parent_seed_values_retained"] is False
    assert document["seed_and_execution"] == {
        "concrete_seed_inventory_present": False,
        "seed_inventory_frozen": False,
        "confirmation_values_accessed": False,
        "launch_authorized": False,
        "execution_authorized": False,
        "result_authorized": False,
    }


def test_strict_reload_reconstructs_authority_and_rejects_mutation() -> None:
    loaded_d6, parent, design = _inputs()
    amendment = build_d6_d7_structural_rebinding_amendment(
        loaded_d6=loaded_d6,
        parent_protocol=parent,
        seed_free_design=design,
    )

    restored = D6D7StructuralRebindingAmendment.from_canonical_bytes(
        amendment.canonical_bytes,
        expected_sha256=amendment.canonical_sha256,
        loaded_d6=loaded_d6,
        parent_protocol=parent,
        seed_free_design=design,
    )
    assert restored == amendment

    with pytest.raises(QualificationContractError, match="SHA-256"):
        D6D7StructuralRebindingAmendment.from_canonical_bytes(
            amendment.canonical_bytes,
            expected_sha256="1" * 64,
            loaded_d6=loaded_d6,
            parent_protocol=parent,
            seed_free_design=design,
        )

    mutated = amendment.to_dict()
    mutated["structural_rebinding"]["successor_fulfillment_rule_encoded"] = (
        False
    )
    mutated_bytes = canonical_json_bytes(mutated)
    with pytest.raises(
        QualificationContractError,
        match="authoritative reconstruction",
    ):
        D6D7StructuralRebindingAmendment.from_canonical_bytes(
            mutated_bytes,
            expected_sha256=hashlib.sha256(mutated_bytes).hexdigest(),
            loaded_d6=loaded_d6,
            parent_protocol=parent,
            seed_free_design=design,
        )

    noncanonical = amendment.canonical_bytes.replace(b"{", b"{ ", 1)
    with pytest.raises(QualificationContractError, match="not canonical"):
        D6D7StructuralRebindingAmendment.from_canonical_bytes(
            noncanonical,
            expected_sha256=hashlib.sha256(noncanonical).hexdigest(),
            loaded_d6=loaded_d6,
            parent_protocol=parent,
            seed_free_design=design,
        )

    duplicate_key = b'{"schema_version":"one","schema_version":"two"}'
    with pytest.raises(QualificationContractError, match="duplicate JSON key"):
        D6D7StructuralRebindingAmendment.from_canonical_bytes(
            duplicate_key,
            expected_sha256=hashlib.sha256(duplicate_key).hexdigest(),
            loaded_d6=loaded_d6,
            parent_protocol=parent,
            seed_free_design=design,
        )

    oversized = b" " * (MAX_D6_D7_STRUCTURAL_REBINDING_AMENDMENT_BYTES + 1)
    with pytest.raises(QualificationContractError, match="within the cap"):
        D6D7StructuralRebindingAmendment.from_canonical_bytes(
            oversized,
            expected_sha256=hashlib.sha256(oversized).hexdigest(),
            loaded_d6=loaded_d6,
            parent_protocol=parent,
            seed_free_design=design,
        )


def test_parent_d6_protocol_and_design_substitution_are_rejected() -> None:
    loaded_d6, parent, design = _inputs()
    alternate_parent = _parent_protocol(
        selection_seeds=(500001, 500002),
    )
    alternate_d6 = _authoritative_d6(
        parent,
        decision_id="d7-rebinding-alternate-d6-v0-1",
        decision_source_commit="a" * 40,
    )

    with pytest.raises(
        QualificationContractError,
        match="does not join",
    ):
        build_d6_d7_structural_rebinding_amendment(
            loaded_d6=loaded_d6,
            parent_protocol=alternate_parent,
            seed_free_design=design,
        )

    with pytest.raises(
        QualificationContractError,
        match="authoritative reconstruction",
    ):
        build_d6_d7_structural_rebinding_amendment(
            loaded_d6=alternate_d6,
            parent_protocol=parent,
            seed_free_design=design,
        )


def test_builder_revalidates_the_authoritative_admission_semantics() -> None:
    loaded_d6, parent, design = _inputs()
    admission = loaded_d6.decision.confirmation_admission_spec
    object.__setattr__(
        admission,
        "required_case_semantics",
        tuple(reversed(admission.required_case_semantics)),
    )

    with pytest.raises(
        QualificationContractError,
        match="required_case_semantics",
    ):
        build_d6_d7_structural_rebinding_amendment(
            loaded_d6=loaded_d6,
            parent_protocol=parent,
            seed_free_design=design,
        )


def test_amendment_identity_is_stable_across_loader_only_descendants() -> None:
    parent = _parent_protocol()
    first_d6 = _authoritative_d6(parent)
    descendant_d6 = _authoritative_d6(
        parent,
        current_loader_source_commit="1" * 40,
        current_loader_source_binding_sha256="2" * 64,
    )
    first_design = build_seed_free_d7_confirmation_execution_design(
        loaded_d6=first_d6,
        parent_protocol=parent,
    )
    descendant_design = build_seed_free_d7_confirmation_execution_design(
        loaded_d6=descendant_d6,
        parent_protocol=parent,
    )
    first = build_d6_d7_structural_rebinding_amendment(
        loaded_d6=first_d6,
        parent_protocol=parent,
        seed_free_design=first_design,
    )
    descendant = build_d6_d7_structural_rebinding_amendment(
        loaded_d6=descendant_d6,
        parent_protocol=parent,
        seed_free_design=descendant_design,
    )

    assert first.canonical_bytes == descendant.canonical_bytes
    assert first.canonical_sha256 == descendant.canonical_sha256
    for ephemeral_name in (
        b"current_loader_source_commit",
        b"current_loader_source_binding_sha256",
        b"current_loader_source_surface_verified",
    ):
        assert ephemeral_name not in first.canonical_bytes
    restored = D6D7StructuralRebindingAmendment.from_canonical_bytes(
        first.canonical_bytes,
        expected_sha256=first.canonical_sha256,
        loaded_d6=descendant_d6,
        parent_protocol=parent,
        seed_free_design=descendant_design,
    )
    assert restored == descendant


def test_historical_d6_artifact_bytes_remain_unchanged() -> None:
    repository = Path(__file__).resolve().parents[1]
    d6_path = (
        repository
        / "experiments"
        / "qualification"
        / "d0_d5_f2_cartesian_selection_v0_1"
        / "d6-surrogate-advancement-decision.json"
    )
    before = d6_path.read_bytes()

    _amendment()

    after = d6_path.read_bytes()
    assert after == before
    assert sha256_bytes(after) == (
        "c1c3fbbb9a06e8df120755dcf159e015636d96993bd6ec3a6792312618587a07"
    )


def test_factory_protection_rejects_direct_or_modified_records() -> None:
    loaded_d6, _parent, design = _inputs()

    with pytest.raises(
        QualificationContractError,
        match="authoritative builder",
    ):
        D6D7StructuralRebindingAmendment(
            source_design=design,
            source_admission=(
                loaded_d6.decision.confirmation_admission_spec
            ),
        )

    amendment = _amendment()
    forged_exact = replace(
        amendment.exact_carry_forward,
        parent_graph_axes_sha256="a" * 64,
        successor_graph_axes_sha256="a" * 64,
    )
    object.__setattr__(
        amendment,
        "exact_carry_forward",
        forged_exact,
    )
    with pytest.raises(
        QualificationContractError,
        match="differ from the source design",
    ):
        amendment.__post_init__()

    with pytest.raises(
        QualificationContractError,
        match="design_schema_version differs",
    ):
        replace(
            amendment.seed_free_design,
            design_schema_version="spirallens.fake-design.v9",
        )
    with pytest.raises(
        QualificationContractError,
        match="structural projection schema differs",
    ):
        replace(
            amendment.structural_rebinding,
            structural_projection_schema_version=(
                "spirallens.fake-projection.v9"
            ),
        )


def test_rebinding_contract_is_not_exported_from_public_namespaces() -> None:
    assert not hasattr(
        spirallens,
        "D6D7StructuralRebindingAmendment",
    )
    assert not hasattr(
        qualification,
        "D6D7StructuralRebindingAmendment",
    )
