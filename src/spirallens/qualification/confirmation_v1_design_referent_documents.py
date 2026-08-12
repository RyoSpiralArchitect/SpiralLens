"""Pure canonical documents for the private D7 v1 design referents.

This module owns only the value types and deterministic document construction
for the six virtual full-design referents.  It performs no repository, Git,
filesystem, supplier, publication, chronology, or execution I/O.  The facade
authenticates S/C1/C2, the five scientific parents, and directly bound repository
sources; runtime and dependency authentication remain explicitly false.

A constructed virtual binding remains candidate-only.  It is not admission,
freeze, review, application, persistence, materialization, or authority.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import ClassVar, cast

from spirallens.core.canonical import (
    canonical_json_bytes,
    parse_canonical_json,
    sha256_bytes,
)

from .advancement import IndependentConfirmationAdmissionSpec
from . import confirmation_execution_design as execution_design
from . import confirmation_protocol
from . import confirmation_v1_records as records
from .common import QualificationContractError, require_sha256


__all__: tuple[str, ...] = ()


_EXECUTION_DESIGN_PATH = "src/spirallens/qualification/confirmation_execution_design.py"
_SUCCESSOR_LINEAGE_ID = "d7-spectral-moment-confirmation-v1"
_SEED_SLOT_IDS = (
    "confirmation-seed-slot-00",
    "confirmation-seed-slot-01",
)
_FUTURE_CHRONOLOGY_KEYS = (
    "artifact_only_commit_a_file_set_reference",
    "design_change_after_receipt_requires_new_version",
    "git_commit_sequence",
    "item23_values_may_select_contract",
    "later_descriptor_may_cure_missing_binding",
    "pre_item23_repository_publication_mode",
    "receipt_generated_last_within_pre_item23_set",
    "receipt_only_git_commit_used",
    "result_only_commit_b_file_reference",
    "same_identity_rescue_retry_allowed",
    "source_change_after_c2_invalidates_current_identity",
    "stages",
)
_FUTURE_CHRONOLOGY_STAGE_IDS = (
    "reviewed-source-commit",
    "stage-c1-seed-free-source-set-off-repository",
    "stage-c2-source-closure-receipt-off-repository",
    "open-external-staging-root-o-excl-and-fsync",
    "persist-external-exclusive-seed-supply-claim-and-fsync",
    "invoke-fresh-seed-supplier-exactly-once",
    "build-official-seed-inventory-and-embedded-full-design",
    "build-replay-target-and-full-design-freeze",
    "build-launch-intent",
    "persist-separate-domain-pre-start-attempt-reservation-and-fsync",
    "promote-external-store-no-replace-and-reverify-durable-bytes",
    "build-pre-item23-chronology-receipt-last",
    "run-staged-authoritative-joined-loader-hard-gate",
    "atomically-publish-exact-nine-file-repository-set-no-replace",
    "commit-pre-item23-artifact-only-a",
    "run-commit-a-verifier-and-authoritative-joined-loader-hard-gate",
    "fresh-descriptive-result-no-replace-publication",
    "commit-descriptive-result-only-b",
    "run-commit-b-verifier-after-commit-b",
)
_PARENT_ROLES = (
    "parent-protocol",
    "parent-result",
    "parent-manifest",
    "parent-consumption",
    "parent-d6-decision",
)
_ROOT_KEYS = frozenset(
    {
        "schema_version",
        "contract_id",
        "artifact_role",
        "successor_lineage_id",
        "derivation",
        "payload",
        "typestate",
        "claim_boundary",
    }
)
_ROLE_SPECS = MappingProxyType(
    {
        "confirmation-family": (
            "spirallens.d7-v1-confirmation-family-descriptor.v0.1",
            "d7-v1-confirmation-family-descriptor-v0-1",
        ),
        "family-admission": (
            "spirallens.d7-v1-family-admission-candidate.v0.1",
            "d7-v1-family-admission-candidate-v0-1",
        ),
        "confirmation-protocol": (
            "spirallens.d7-v1-confirmation-protocol-candidate.v0.1",
            "d7-v1-confirmation-protocol-candidate-v0-1",
        ),
        "source-graph": (
            "spirallens.d7-v1-source-graph.v0.1",
            "d7-v1-source-graph-v0-1",
        ),
        "graph-case-stress-aggregation": (
            "spirallens.d7-v1-graph-case-stress-aggregation.v0.1",
            "d7-v1-graph-case-stress-aggregation-v0-1",
        ),
        "lifecycle": (
            "spirallens.d7-v1-lifecycle-policy.v0.1",
            "d7-v1-lifecycle-policy-v0-1",
        ),
    }
)
_INVENTORY_FIELDS = MappingProxyType(
    {
        "family_binding": "confirmation-family",
        "admission_binding": "family-admission",
        "protocol_binding": "confirmation-protocol",
        "source_graph_binding": "source-graph",
        "graph_case_stress_aggregation_binding": ("graph-case-stress-aggregation"),
        "lifecycle_binding": "lifecycle",
    }
)
_CLAIM_BOUNDARY = MappingProxyType(
    {
        "claim_ceiling": "level_0",
        "claim_delta": "none",
        "authority_granted": False,
        "execution_authorized": False,
        "scientific_claim_eligible": False,
    }
)
_TYPESTATE = MappingProxyType(
    {
        "virtual_referent_derived": True,
        "binding_resolved": True,
        "binding_authenticated": False,
        "admitted": False,
        "frozen": False,
        "reviewed": False,
        "applied": False,
        "instantiated": False,
        "persisted": False,
    }
)


def _mapping(value: object, *, label: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise QualificationContractError(f"{label} must be a JSON object")
    return cast(dict[str, object], value)


def _sequence(value: object, *, label: str) -> list[object]:
    if type(value) is not list:
        raise QualificationContractError(f"{label} must be a JSON array")
    return cast(list[object], value)


def _string(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise QualificationContractError(f"{label} must be a non-empty string")
    return value


def _plain_int(value: object, *, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise QualificationContractError(f"{label} must be an integer >= {minimum}")
    return value


def _binding_document(binding: records.D7V1ArtifactBinding) -> dict[str, object]:
    if not isinstance(binding, records.D7V1ArtifactBinding):
        raise TypeError("binding must be D7V1ArtifactBinding")
    return binding.to_dict()


def _record_binding(
    record: records.D7V1C1SourceSetRecord | records.D7V1C2SourceClosureReceipt,
) -> records.D7V1ArtifactBinding:
    return records.D7V1ArtifactBinding.from_record(record)


def _parse_exact_canonical(source: bytes, *, label: str) -> dict[str, object]:
    if type(source) is not bytes or not source:
        raise QualificationContractError(f"{label} must be nonempty bytes")
    value = parse_canonical_json(source, label=label)
    document = _mapping(value, label=label)
    if canonical_json_bytes(document) != source:
        raise QualificationContractError(f"{label} canonical round-trip differs")
    return document


@dataclass(frozen=True, slots=True, init=False)
class D7V1TypedScientificParentAdapter:
    """Value-free typed projection of exactly five joined scientific parents."""

    parent_bindings: Mapping[str, records.D7V1ArtifactBinding]
    confirmation_admission: Mapping[str, object]
    execution_design: object
    parent_join_sha256: str

    exact_five_parent_read: ClassVar[bool] = True
    parent_byte_identities_verified: ClassVar[bool] = True
    parent_cross_joins_verified: ClassVar[bool] = True
    parent_result_values_retained: ClassVar[bool] = False
    historical_plan_read: ClassVar[bool] = False
    negative_or_predecessor_d7_read: ClassVar[bool] = False
    launch_artifact_read: ClassVar[bool] = False

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise QualificationContractError(
            "D7V1TypedScientificParentAdapter requires the closed five-parent "
            "adapter minted only by the authenticated provenance facade"
        )


def _validated_parent_adapter_fields(
    *,
    parent_bindings: Mapping[str, records.D7V1ArtifactBinding],
    confirmation_admission: Mapping[str, object],
    execution_design: object,
    parent_join_sha256: str,
) -> tuple[
    Mapping[str, records.D7V1ArtifactBinding],
    Mapping[str, object],
    object,
    str,
]:
    if tuple(parent_bindings) != _PARENT_ROLES:
        raise QualificationContractError(
            "typed scientific parent adapter requires exact ordered five roles"
        )
    admission_document = IndependentConfirmationAdmissionSpec.from_dict(
        confirmation_admission
    ).to_dict()
    if admission_document != dict(confirmation_admission):
        raise QualificationContractError(
            "typed scientific parent adapter admission differs from canonical form"
        )
    if not hasattr(execution_design, "to_dict") or not hasattr(
        execution_design, "canonical_sha256"
    ):
        raise TypeError("execution_design has the wrong closed return surface")
    require_sha256(parent_join_sha256, label="parent_join_sha256")
    return (
        MappingProxyType(dict(parent_bindings)),
        MappingProxyType(admission_document),
        execution_design,
        parent_join_sha256,
    )


@dataclass(frozen=True, slots=True, init=False)
class D7V1CanonicalDesignReferent:
    """One exact canonical, candidate-only virtual full-design referent."""

    artifact_role: str
    artifact_contract_id: str
    canonical_bytes: bytes
    canonical_sha256: str
    byte_count: int

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise QualificationContractError(
            "D7V1CanonicalDesignReferent requires the closed derivation minted "
            "only by the authenticated provenance facade"
        )

    @property
    def document(self) -> dict[str, object]:
        return _parse_exact_canonical(
            self.canonical_bytes,
            label=f"{self.artifact_role} canonical referent",
        )

    @property
    def binding(self) -> records.D7V1ArtifactBinding:
        return records.D7V1ArtifactBinding(
            artifact_role=self.artifact_role,
            artifact_contract_id=self.artifact_contract_id,
            canonical_sha256=self.canonical_sha256,
            byte_count=self.byte_count,
        )


def _validated_canonical_referent_fields(
    *,
    artifact_role: str,
    document: Mapping[str, object],
) -> tuple[str, str, bytes, str, int]:
    if artifact_role not in _ROLE_SPECS:
        raise QualificationContractError("unknown full-design referent role")
    canonical = canonical_json_bytes(dict(document))
    parsed = _parse_exact_canonical(
        canonical,
        label=f"{artifact_role} canonical referent",
    )
    schema, contract_id = _ROLE_SPECS[artifact_role]
    if set(parsed) != _ROOT_KEYS:
        raise QualificationContractError(
            f"{artifact_role} referent root keyset differs"
        )
    if (
        parsed["schema_version"] != schema
        or parsed["contract_id"] != contract_id
        or parsed["artifact_role"] != artifact_role
        or parsed["successor_lineage_id"] != _SUCCESSOR_LINEAGE_ID
    ):
        raise QualificationContractError(f"{artifact_role} referent header differs")
    if parsed["typestate"] != dict(_TYPESTATE) or parsed["claim_boundary"] != dict(
        _CLAIM_BOUNDARY
    ):
        raise QualificationContractError(
            f"{artifact_role} referent non-authority boundary differs"
        )
    return artifact_role, schema, canonical, sha256_bytes(canonical), len(canonical)


@dataclass(frozen=True, slots=True, init=False)
class D7V1FullDesignReferentSetCandidate:
    """Closed six-referent candidate derived from one exact S/C1/C2 join."""

    source_commit: str
    parent_adapter: D7V1TypedScientificParentAdapter
    referents_by_role: Mapping[str, D7V1CanonicalDesignReferent]
    bindings_by_inventory_field: Mapping[str, records.D7V1ArtifactBinding]

    source_reviewed: ClassVar[bool] = False
    source_selected: ClassVar[bool] = False
    source_closure_established: ClassVar[bool] = False
    source_tree_authenticated: ClassVar[bool] = False
    runtime_environment_authenticated: ClassVar[bool] = False
    runtime_dependency_closure_verified: ClassVar[bool] = False
    external_bindings_authenticated: ClassVar[bool] = False
    confirmation_family_admitted: ClassVar[bool] = False
    confirmation_protocol_frozen: ClassVar[bool] = False
    aggregation_rebinding_reviewed: ClassVar[bool] = False
    aggregation_rebinding_applied: ClassVar[bool] = False
    lifecycle_instantiated: ClassVar[bool] = False
    official_embedded_full_design_created: ClassVar[bool] = False
    official_embedded_full_design_frozen: ClassVar[bool] = False
    materialization_authorized: ClassVar[bool] = False
    materialized: ClassVar[bool] = False
    publication_authorized: ClassVar[bool] = False
    artifacts_published: ClassVar[bool] = False
    authority_granted: ClassVar[bool] = False
    execution_authorized: ClassVar[bool] = False
    execution_started: ClassVar[bool] = False
    supplier_invoked: ClassVar[bool] = False
    seed_values_present: ClassVar[bool] = False
    official_callable_invoked: ClassVar[bool] = False
    result_produced: ClassVar[bool] = False
    chronology_orchestrated: ClassVar[bool] = False
    chronology_receipt_created: ClassVar[bool] = False
    chronology_receipt_persisted: ClassVar[bool] = False
    scientific_claim_eligible: ClassVar[bool] = False

    resolution_status: ClassVar[str] = "six-virtual-bindings-resolved"

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise QualificationContractError(
            "D7V1FullDesignReferentSetCandidate requires the closed builder in the "
            "authenticated provenance facade"
        )

    @property
    def family_binding(self) -> records.D7V1ArtifactBinding:
        return self.bindings_by_inventory_field["family_binding"]

    @property
    def admission_binding(self) -> records.D7V1ArtifactBinding:
        return self.bindings_by_inventory_field["admission_binding"]

    @property
    def protocol_binding(self) -> records.D7V1ArtifactBinding:
        return self.bindings_by_inventory_field["protocol_binding"]

    @property
    def source_graph_binding(self) -> records.D7V1ArtifactBinding:
        return self.bindings_by_inventory_field["source_graph_binding"]

    @property
    def graph_case_stress_aggregation_binding(
        self,
    ) -> records.D7V1ArtifactBinding:
        return self.bindings_by_inventory_field["graph_case_stress_aggregation_binding"]

    @property
    def lifecycle_binding(self) -> records.D7V1ArtifactBinding:
        return self.bindings_by_inventory_field["lifecycle_binding"]


def _validated_referent_set_fields(
    *,
    source_commit: str,
    parent_adapter: D7V1TypedScientificParentAdapter,
    referents_by_role: Mapping[str, D7V1CanonicalDesignReferent],
) -> tuple[
    str,
    D7V1TypedScientificParentAdapter,
    Mapping[str, D7V1CanonicalDesignReferent],
    Mapping[str, records.D7V1ArtifactBinding],
]:
    if tuple(referents_by_role) != tuple(_ROLE_SPECS):
        raise QualificationContractError(
            "full-design referent set requires exact ordered six roles"
        )
    bindings = {
        field: referents_by_role[role].binding
        for field, role in _INVENTORY_FIELDS.items()
    }
    return (
        source_commit,
        parent_adapter,
        MappingProxyType(dict(referents_by_role)),
        MappingProxyType(bindings),
    )


def _derivation_document(
    *,
    source_commit: str,
    c1: records.D7V1C1SourceSetRecord,
    c2: records.D7V1C2SourceClosureReceipt,
    adapter: D7V1TypedScientificParentAdapter,
) -> dict[str, object]:
    return {
        "derivation_id": "d7-v1-five-parent-source-joined-referents-v0-1",
        "source_commit": source_commit,
        "c1_binding": _binding_document(_record_binding(c1)),
        "c2_binding": _binding_document(_record_binding(c2)),
        "scientific_parent_bindings": [
            _binding_document(adapter.parent_bindings[role]) for role in _PARENT_ROLES
        ],
        "scientific_parent_join_sha256": adapter.parent_join_sha256,
        "approved_callable": {
            "module": execution_design.__name__,
            "qualname": "build_seed_free_d7_confirmation_execution_design",
            "repository_path": _EXECUTION_DESIGN_PATH,
            "five_parent_seed_free_scientific_projection_only": True,
            "authority_transfer_allowed": False,
            "persistence_transfer_allowed": False,
            "schema_transfer_allowed": False,
        },
        "read_contract": {
            "exact_scientific_parent_count": 5,
            "historical_plan_read": False,
            "negative_or_predecessor_d7_read": False,
            "launch_artifact_read": False,
            "parent_result_values_retained": False,
        },
    }


def _document(
    role: str,
    *,
    derivation: Mapping[str, object],
    payload: Mapping[str, object],
) -> dict[str, object]:
    schema, contract_id = _ROLE_SPECS[role]
    return {
        "schema_version": schema,
        "contract_id": contract_id,
        "artifact_role": role,
        "successor_lineage_id": _SUCCESSOR_LINEAGE_ID,
        "derivation": dict(derivation),
        "payload": dict(payload),
        "typestate": dict(_TYPESTATE),
        "claim_boundary": dict(_CLAIM_BOUNDARY),
    }


def _referent_payloads(
    *,
    protocol: object,
    source_commit: str,
    c1: records.D7V1C1SourceSetRecord,
    adapter: D7V1TypedScientificParentAdapter,
) -> Mapping[str, Mapping[str, object]]:
    design = adapter.execution_design
    design_document = design.to_dict()
    admission = _mapping(
        design_document.get("parent_d6"),
        label="execution design parent D6",
    )
    inventory = design.inventory.to_dict()
    counts = _mapping(inventory.get("counts"), label="D7 inventory counts")
    repeated = _mapping(
        inventory.get("repeated_measures"),
        label="D7 repeated-measures policy",
    )
    expected_counts = {
        "seed_slots": 2,
        "cases": 4,
        "primary_units": 64,
        "core_cells": 192,
        "loop_cells": 1152,
        "event_lanes": 1344,
        "required_strata": 6,
    }
    observed_counts = {
        "seed_slots": counts.get("seed_slots"),
        "cases": counts.get("cases"),
        "primary_units": len(design.inventory.primary_units),
        "core_cells": len(design.inventory.core_cells),
        "loop_cells": len(design.inventory.loop_cells),
        "event_lanes": counts.get("event_lanes"),
        "required_strata": len(design.inventory.expected_strata),
    }
    if observed_counts != expected_counts:
        raise QualificationContractError(
            "approved scientific inventory differs from 2/4/64/192/1152/1344/6"
        )
    c1_payload = _mapping(c1.to_dict().get("payload"), label="C1 payload")
    source_members = _sequence(
        c1_payload.get("source_members"),
        label="C1 source members",
    )
    source_member_sha = sha256_bytes(
        canonical_json_bytes(
            {
                "schema_version": "spirallens.d7-v1-source-member-set.v0.1",
                "source_members": source_members,
            }
        )
    )
    confirmation_family = _mapping(
        design_document.get("confirmation_family"),
        label="confirmation family",
    )
    locked_parent_interface = _mapping(
        design_document.get("locked_parent_interface"),
        label="locked parent interface",
    )
    if (
        confirmation_family.get("family_admitted") is not False
        or confirmation_family.get("construction_diversity_reviewed") is not False
        or confirmation_family.get("committed_source_closure_verified") is not False
        or locked_parent_interface.get(
            "parent_aggregation_application_rebinding_reviewed"
        )
        is not False
    ):
        raise QualificationContractError(
            "approved design family or aggregation review boundary differs"
        )
    confirmation_admission = _mapping(
        dict(adapter.confirmation_admission),
        label="fresh confirmation admission spec",
    )
    source_derived_family_proposal = confirmation_protocol.D7ConfirmationFamilyProposal(
        selection_generator_family_id=_string(
            confirmation_admission.get("selection_generator_family_id"),
            label="admission selection_generator_family_id",
        ),
        selection_construction_family_id=_string(
            confirmation_admission.get("selection_construction_family_id"),
            label="admission selection_construction_family_id",
        ),
    ).to_dict()
    case_ids = sorted({unit.case_id for unit in design.inventory.primary_units})
    observed_seed_slots = tuple(
        sorted({unit.seed_slot_id for unit in design.inventory.primary_units})
    )
    if (
        len(case_ids) != 4
        or observed_seed_slots != _SEED_SLOT_IDS
        or source_derived_family_proposal.get("confirmation_generator_family_id")
        != confirmation_family.get("generator_family_id")
        or source_derived_family_proposal.get("selection_generator_family_id")
        != admission.get("selection_generator_family_id")
        or source_derived_family_proposal.get("selection_construction_family_id")
        != admission.get("selection_construction_family_id")
        or source_derived_family_proposal.get("confirmation_generator_family_id")
        == source_derived_family_proposal.get("selection_generator_family_id")
        or source_derived_family_proposal.get("confirmation_construction_family_id")
        == source_derived_family_proposal.get("selection_construction_family_id")
    ):
        raise QualificationContractError(
            "approved design family cases, slots, or construction diversity differ"
        )
    family_payload = {
        "descriptor_id": "d7-v1-spectral-moment-confirmation-family-candidate",
        "generator_family_id": confirmation_family["generator_family_id"],
        "case_ids": case_ids,
        "case_count": len(case_ids),
        "seed_slot_ids": list(_SEED_SLOT_IDS),
        "identifier_difference_observed": True,
        "identifier_difference_proves_construction_diversity": False,
        "source_derived_family_proposal": source_derived_family_proposal,
        "execution_design_confirmation_family": dict(confirmation_family),
    }
    admission_payload = {
        "admission_candidate_id": "d7-v1-family-admission-candidate",
        "status": "candidate-not-issued",
        "parent_d6_binding": dict(admission),
        "fresh_confirmation_admission_spec": dict(confirmation_admission),
        "admission_issued": False,
        "all_requirements_reviewed": False,
        "policy_override_allowed": False,
        "post_selection_exclusion_allowed": False,
    }
    protocol_payload = {
        "protocol_candidate_id": "d7-v1-confirmation-protocol-candidate",
        "status": "seed-free-execution-design-not-frozen",
        "execution_design_schema_version": design.schema_version,
        "execution_design_sha256": design.canonical_sha256,
        "seed_policy": design.seed_policy.to_dict(),
        "graph_axes": design.graph_axes.to_dict(),
        "domain": design.domain.to_dict(),
        "thresholds": design.thresholds.to_dict(),
        "coverage_policy": design.coverage_policy.to_dict(),
        "stress_translation": design.stress_translation.to_dict(),
        "manifest_compatibility": design.manifest_compatibility.to_dict(),
        "execution_design": design_document,
        "protocol_frozen": False,
    }
    source_graph_payload = {
        "source_graph_id": "d7-v1-source-graph-candidate",
        "source_commit": source_commit,
        "source_members": source_members,
        "source_member_count": len(source_members),
        "source_member_set_sha256": source_member_sha,
        "git_declared_source_members_only": True,
        "runtime_dependency_closure_verified": False,
        "source_graph_authenticated": False,
    }
    aggregation_payload = {
        "aggregation_id": "d7-v1-graph-case-stress-aggregation-candidate",
        "inventory": inventory,
        "locked_parent_interface": dict(locked_parent_interface),
        "parent_locked_aggregation_sha256": admission["locked_aggregation_sha256"],
        "scientific_inventory_counts": expected_counts,
        "field_graph_count": len(design.graph_axes.field_estimation),
        "cycle_graph_count": len(design.graph_axes.cycle_construction),
        "loop_role_count": 2,
        "core_cells_per_primary_unit": 3,
        "loop_cells_per_primary_unit": 18,
        "graph_case_stress_cells_are_repeated_measures": True,
        "repeated_measures": repeated,
        "event_lanes_are_independent_samples": False,
        "aggregation_rebinding_reviewed": False,
        "aggregation_rebinding_applied": False,
    }
    protocol_document = getattr(protocol, "document", None)
    if type(protocol_document) is not dict:
        raise QualificationContractError(
            "materialization protocol document must be a JSON object"
        )
    protocol_future_chronology = _mapping(
        protocol_document.get("future_chronology"),
        label="protocol future_chronology",
    )
    chronology_stages = tuple(
        _mapping(item, label="protocol future chronology stage")
        for item in _sequence(
            protocol_future_chronology.get("stages"),
            label="protocol future chronology stages",
        )
    )
    observed_stages = tuple(
        (
            _plain_int(stage.get("sequence"), label="chronology stage sequence"),
            _string(stage.get("stage_id"), label="chronology stage_id"),
        )
        for stage in chronology_stages
    )
    if (
        tuple(protocol_future_chronology) != _FUTURE_CHRONOLOGY_KEYS
        or any(set(stage) != {"sequence", "stage_id"} for stage in chronology_stages)
        or observed_stages != tuple(enumerate(_FUTURE_CHRONOLOGY_STAGE_IDS, start=1))
        or len(
            _sequence(
                protocol_future_chronology.get("git_commit_sequence"),
                label="protocol future chronology git_commit_sequence",
            )
        )
        != 3
    ):
        raise QualificationContractError(
            "protocol future chronology differs from exact 19-stage policy"
        )
    lifecycle_payload = {
        "lifecycle_id": "d7-v1-prospective-lifecycle-policy",
        "status": "prospective-not-instantiated",
        "protocol_future_chronology": dict(protocol_future_chronology),
        "ordering_is_policy_only": True,
        "external_store_observed": False,
        "external_namespace_reserved": False,
        "seed_claim_created": False,
        "official_seed_inventory_created": False,
        "official_embedded_full_design_created": False,
        "official_embedded_full_design_frozen": False,
        "launch_intent_created": False,
        "attempt_reserved": False,
        "chronology_receipt_created": False,
        "official_execution_started": False,
        "lifecycle_instantiated": False,
    }
    return MappingProxyType(
        {
            "confirmation-family": family_payload,
            "family-admission": admission_payload,
            "confirmation-protocol": protocol_payload,
            "source-graph": source_graph_payload,
            "graph-case-stress-aggregation": aggregation_payload,
            "lifecycle": lifecycle_payload,
        }
    )
