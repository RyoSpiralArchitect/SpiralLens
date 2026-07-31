"""Deep-internal exact D7 spectral-moment producer and aggregation.

The sole producer has no arguments and reads one fixed, future, committed
fused-authority descriptor.  No descriptor, seed, invocation, or result is
created by this module.  Until that descriptor exists at the canonical path,
the producer fails closed before reconstructing C1 or touching a generator.

The numeric execution path deliberately has two global phases: all 64 blind
primary predictions are sealed first, and only then may any spectral oracle be
materialized.  The returned payload remains Level-0 synthetic evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import FunctionType
from typing import Mapping

import numpy as np

from spirallens.core.canonical import (
    canonical_json_bytes,
    canonical_json_sha256,
)
from spirallens.synthetic.cartesian_fourier_domain_phantom import (
    evaluate_oracle_sampled_response,
)
from spirallens.synthetic.spectral_moment_confirmation import (
    SPECTRAL_MOMENT_GENERATOR_FAMILY_ID,
    SpectralMomentConfirmationGenerator,
)

from . import confirmation_attempt_records as ar
from . import confirmation_fused_authority as fused_authority
from . import confirmation_fused_start as fused_start
from . import confirmation_result_component_validation as component_validation
from . import confirmation_result_components as components
from .aggregation import (
    materialize_expected_cells,
    materialize_expected_core_cells,
    collapse_core_primary_units,
    collapse_primary_units,
)
from .common import (
    AttemptStatus,
    CoreDisposition,
    CorePredictionClass,
    EvaluationUnit,
    LoopDisposition,
    LoopPredictionClass,
    ObligationMode,
    QualificationContractError,
    QualificationState,
    array_fingerprint,
)
from .confirmation_attempt_authority import (
    D7AuthorityArtifactBinding,
    D7OfficialSeedInventoryRecord,
)
from .confirmation_c1 import D7C1SeedFreeSourceSet, D7_C1_BUNDLE_REPOSITORY_PATH
from .confirmation_execution_design import (
    D7_CONFIRMATION_CORE_CELL_COUNT,
    D7_CONFIRMATION_EVENT_LANE_COUNT,
    D7_CONFIRMATION_LOOP_CELL_COUNT,
    D7_CONFIRMATION_PRIMARY_UNIT_COUNT,
    D7_CONFIRMATION_SEED_SLOT_IDS,
    D7ConfirmationExecutionDesignDraft,
    D7PrimaryUnitTemplate,
    _build_recorded_c1_d7_confirmation_execution_design,
)
from .confirmation_execution_kernel import (
    _D7SeedSlotPrimaryRuntimeHandoff,
    _execute_d7_seed_slot_primary_runtime,
)
from .confirmation_replay_contracts import (
    D7_RECORDED_C1_CANONICAL_SHA256,
    load_d7_replay_attempt_contract_foundation,
)
from .confirmation_runner import D7ScientificProducerOutput
from .contracts import (
    CoreCellSummary,
    CorePrimaryUnitSummary,
    CrossedCellSummary,
    PrimaryUnitSummary,
    StratumSummary,
)
from .persistence import load_qualification_protocol
from .prerequisites import (
    REASON_CORE_AMPLITUDE_NOT_LOCALIZED,
    REASON_EMPTY_GRAPH,
    build_core_oracle_truth,
    score_core_prediction,
)
from .protocol import (
    ExpectedCell,
    ExpectedCoreCell,
    ExpectedStratum,
    LoopRole,
    required_stress_stratum_id,
)
from .winding import (
    REASON_BOUNDARY_AMPLITUDE_FLOOR,
    REASON_BOUNDARY_COHERENCE_FLOOR,
    REASON_BOUNDARY_IDENTIFIABILITY_FLOOR,
    REASON_LOOP_ROWS_REPEATED,
    REASON_LOOP_SUPPORT,
    build_loop_oracle_truth,
    score_loop_prediction,
)

__all__: tuple[str, ...] = ()

D7_OFFICIAL_PRODUCER_ID = "d7-spectral-moment-official-producer-v0-1"
D7_OFFICIAL_PRODUCER_MODULE = "spirallens.qualification.confirmation_official_execution"
D7_OFFICIAL_PRODUCER_QUALNAME = "produce_d7_official_result"
D7_OFFICIAL_FUSED_DESCRIPTOR_REPOSITORY_PATH = (
    "experiments/qualification/d7_spectral_moment_confirmation_v0_1/launch.json"
)
D7_OFFICIAL_PARENT_PROTOCOL_REPOSITORY_PATH = (
    "protocols/d0_d5_f2_cartesian_selection_v0_1.json"
)
D7_OFFICIAL_PARENT_PROTOCOL_SHA256 = (
    "9908bb83bb5ff5642416aa09d9e468e0a9499185cec9305e69a54143f2578bd1"
)
D7_RECORDED_C1_AGGREGATION_APPLICATION_SHA256 = (
    "d616cd063a87103c558fa33ce23514dab70abb59483d3d303ba1f475a6881435"
)
D7_RECORDED_C1_AGGREGATION_APPLICATION_SCHEMA_VERSION = (
    "spirallens.d7-confirmation-aggregation-application.v0.1"
)
D7_RECORDED_C1_AGGREGATION_APPLICATION_BYTE_COUNT = 5034
D7_RECORDED_C1_LOCKED_AGGREGATION_SHA256 = (
    "0f3abb2fdea20f21a3460454bad77e6a86aba47db47ec34389729a468f9ecc8e"
)
D7_RECORDED_C1_LOCKED_AGGREGATION_SCHEMA_VERSION = (
    "spirallens.d7-locked-confirmation-aggregation.v0.1"
)
D7_RECORDED_C1_LOCKED_AGGREGATION_BYTE_COUNT = 1093
D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_SHA256 = (
    "f73f0945ad59430ad75bde932acb2822e164140e06cd12428ef8b6167e1dca18"
)
D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_SCHEMA_VERSION = (
    "spirallens.d7-confirmation-implementation-registry.v0.1"
)
D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_BYTE_COUNT = 5302
D7_OFFICIAL_FULL_INVENTORY_SCHEMA_VERSION = "spirallens.d7-official-full-inventory.v0.1"
D7_OFFICIAL_FULL_DESIGN_SCHEMA_VERSION = "spirallens.d7-official-full-design.v0.1"
D7_OFFICIAL_AGGREGATION_SCHEMA_VERSION = "spirallens.d7-official-exact-aggregation.v0.1"
D7_OFFICIAL_GATE_MANIFEST_SCHEMA_VERSION = (
    component_validation.D7_EXACT_GATE_MANIFEST_SCHEMA_VERSION
)

_EXPECTED_COUNTS = {
    "seed_slots": 2,
    "primary_units": D7_CONFIRMATION_PRIMARY_UNIT_COUNT,
    "core_cells": D7_CONFIRMATION_CORE_CELL_COUNT,
    "loop_cells": D7_CONFIRMATION_LOOP_CELL_COUNT,
    "required_strata": 6,
    "event_lanes": D7_CONFIRMATION_EVENT_LANE_COUNT,
}
_CONTEXT_FACTORY_TOKEN = object()


def _repository_root() -> Path:
    root = Path(__file__).resolve().parents[3]
    if not (root / "pyproject.toml").is_file():
        raise QualificationContractError(
            "official producer source does not resolve a SpiralLens repository"
        )
    return root


def _official_descriptor_path(root: Path) -> Path:
    return root / D7_OFFICIAL_FUSED_DESCRIPTOR_REPOSITORY_PATH


def _seed_by_slot(
    inventory: D7OfficialSeedInventoryRecord,
) -> dict[str, int]:
    if type(inventory) is not D7OfficialSeedInventoryRecord:
        raise TypeError("official seed inventory must have the exact D7 type")
    result = {item.seed_slot_id: item.seed for item in inventory.seeds}
    if tuple(result) != D7_CONFIRMATION_SEED_SLOT_IDS:
        raise QualificationContractError(
            "official seed inventory differs from the frozen slot order"
        )
    return result


def _paired_case_id(unit: D7PrimaryUnitTemplate) -> str:
    if type(unit) is not D7PrimaryUnitTemplate:
        raise TypeError("paired case identity requires an exact primary template")
    return (
        "d7-pair-"
        + canonical_json_sha256(
            {
                "schema_version": "spirallens.d7-paired-case-identity.v0.1",
                "parent_control_id": unit.parent_control_id,
                "case_id": unit.case_id,
                "case_semantics": unit.case_semantics,
                "stress_assignments": [
                    item.to_dict() for item in unit.stress_assignments
                ],
            }
        )[:32]
    )


def _expected_manifests(
    design: D7ConfirmationExecutionDesignDraft,
    official_seed_inventory: D7OfficialSeedInventoryRecord,
) -> tuple[
    tuple[ExpectedCoreCell, ...],
    tuple[ExpectedCell, ...],
    tuple[ExpectedStratum, ...],
]:
    seed_by_slot = _seed_by_slot(official_seed_inventory)
    primary = {item.primary_unit_id: item for item in design.inventory.primary_units}
    core = tuple(
        ExpectedCoreCell(
            core_cell_id=item.core_cell_id,
            primary_unit_id=item.primary_unit_id,
            selection_seed=seed_by_slot[primary[item.primary_unit_id].seed_slot_id],
            control_id=primary[item.primary_unit_id].parent_control_id,
            stress_assignments=primary[item.primary_unit_id].stress_assignments,
            field_graph_id=item.field_graph_id,
            expected_core_disposition=item.expected_core_disposition,
        )
        for item in design.inventory.core_cells
    )
    loop = tuple(
        ExpectedCell(
            cell_id=item.loop_cell_id,
            primary_unit_id=item.primary_unit_id,
            selection_seed=seed_by_slot[primary[item.primary_unit_id].seed_slot_id],
            control_id=primary[item.primary_unit_id].parent_control_id,
            stress_assignments=primary[item.primary_unit_id].stress_assignments,
            field_graph_id=item.field_graph_id,
            cycle_graph_id=item.cycle_graph_id,
            loop_role=item.loop_role,
            expected_loop_disposition=item.expected_loop_disposition,
            stratum_ids=tuple(
                sorted(
                    required_stress_stratum_id(assignment.axis_id, assignment.level)
                    for assignment in primary[item.primary_unit_id].stress_assignments
                )
            ),
        )
        for item in design.inventory.loop_cells
    )
    strata = tuple(
        ExpectedStratum(
            stratum_id=item.stratum_id,
            evaluation_unit=EvaluationUnit.PHANTOM_INSTANCE,
            required=True,
            primary_unit_ids=item.primary_unit_ids,
        )
        for item in design.inventory.expected_strata
    )
    return core, loop, strata


def build_d7_official_full_inventory_document(
    *,
    design: D7ConfirmationExecutionDesignDraft,
    official_seed_inventory: D7OfficialSeedInventoryRecord,
) -> dict[str, object]:
    """Materialize the exact seed-bearing 64/192/1152/six inventory."""

    if type(design) is not D7ConfirmationExecutionDesignDraft:
        raise TypeError("design must be the exact D7 design type")
    seed_by_slot = _seed_by_slot(official_seed_inventory)
    core, loop, strata = _expected_manifests(design, official_seed_inventory)
    primary_units = [
        {
            **unit.to_dict(),
            "paired_case_id": _paired_case_id(unit),
            "official_seed": seed_by_slot[unit.seed_slot_id],
            "core_cell_ids": [
                item.core_cell_id
                for item in design.inventory.core_cells
                if item.primary_unit_id == unit.primary_unit_id
            ],
            "loop_cell_ids": [
                item.loop_cell_id
                for item in design.inventory.loop_cells
                if item.primary_unit_id == unit.primary_unit_id
            ],
        }
        for unit in design.inventory.primary_units
    ]
    document: dict[str, object] = {
        "schema_version": D7_OFFICIAL_FULL_INVENTORY_SCHEMA_VERSION,
        "inventory_id": "d7-spectral-moment-official-full-inventory-v0-1",
        "claim_ceiling": "level_0",
        "seed_free_design_sha256": design.canonical_sha256,
        "official_seed_inventory_sha256": (official_seed_inventory.canonical_sha256),
        "seed_slot_ordinal_mapping": [
            {
                "ordinal": ordinal,
                "seed_slot_id": slot,
                "official_seed": seed_by_slot[slot],
            }
            for ordinal, slot in enumerate(D7_CONFIRMATION_SEED_SLOT_IDS)
        ],
        "primary_units": primary_units,
        "expected_core_cells": [item.to_dict() for item in core],
        "expected_loop_cells": [item.to_dict() for item in loop],
        "expected_strata": [item.to_dict() for item in strata],
        "counts": dict(_EXPECTED_COUNTS),
        "graph_cells_are_repeated_measures": True,
        "seed_blocks_proved_independent": False,
        "inferential_sample_size_claimed": False,
        "policy_override_allowed": False,
        "post_selection_exclusion_allowed": False,
    }
    canonical_json_bytes(document)
    return document


def _gate_definitions() -> tuple[dict[str, object], ...]:
    return component_validation._d7_exact_gate_definitions()


def build_d7_official_aggregation_document(
    *, implementation_registry_sha256: str
) -> dict[str, object]:
    """Return the exact C1-bound four-gate aggregation application."""

    if (
        type(implementation_registry_sha256) is not str
        or len(implementation_registry_sha256) != 64
        or any(c not in "0123456789abcdef" for c in implementation_registry_sha256)
    ):
        raise QualificationContractError(
            "implementation_registry_sha256 must be lowercase SHA-256"
        )
    gate_manifest = component_validation._d7_exact_gate_manifest()
    return {
        "schema_version": D7_OFFICIAL_AGGREGATION_SCHEMA_VERSION,
        "application_id": "d7-spectral-moment-official-exact-aggregation-v0-1",
        "claim_ceiling": "level_0",
        "producer_id": D7_OFFICIAL_PRODUCER_ID,
        "implementation_registry_sha256": implementation_registry_sha256,
        "recorded_c1_aggregation_application_sha256": (
            D7_RECORDED_C1_AGGREGATION_APPLICATION_SHA256
        ),
        "recorded_c1_locked_aggregation_sha256": (
            D7_RECORDED_C1_LOCKED_AGGREGATION_SHA256
        ),
        "gate_manifest": gate_manifest,
        "gate_manifest_sha256": canonical_json_sha256(gate_manifest),
        "coverage_policy": {
            "worst_case_required_strata": True,
            "full_coverage_required": True,
            "zero_abstention_required": True,
            "all_expected_primary_units_must_pass": True,
            "minimum_recall": 1.0,
            "minimum_specificity": 1.0,
            "prerequisite_failures_mandatory_and_not_excluded": True,
            "policy_override_allowed": False,
            "post_selection_exclusion_allowed": False,
        },
        "four_state_gate_vocabulary": [
            "pass",
            "fail",
            "insufficient",
            "not_run",
        ],
        "gate_aggregation_precedence": [
            "any-fail-to-fail",
            "else-any-insufficient-or-not-run-to-insufficient",
            "else-pass",
        ],
    }


def build_d7_official_full_design_document(
    *,
    design: D7ConfirmationExecutionDesignDraft,
    official_seed_inventory: D7OfficialSeedInventoryRecord,
    full_inventory_sha256: str,
    implementation_registry_sha256: str,
    aggregation_sha256: str,
) -> dict[str, object]:
    """Return the exact seed-bearing full-design binding document."""

    for name, value in (
        ("full_inventory_sha256", full_inventory_sha256),
        ("implementation_registry_sha256", implementation_registry_sha256),
        ("aggregation_sha256", aggregation_sha256),
    ):
        if (
            type(value) is not str
            or len(value) != 64
            or any(c not in "0123456789abcdef" for c in value)
        ):
            raise QualificationContractError(f"{name} must be lowercase SHA-256")
    return {
        "schema_version": D7_OFFICIAL_FULL_DESIGN_SCHEMA_VERSION,
        "design_id": "d7-spectral-moment-official-full-design-v0-1",
        "claim_ceiling": "level_0",
        "generator_family_id": SPECTRAL_MOMENT_GENERATOR_FAMILY_ID,
        "seed_free_design_sha256": design.canonical_sha256,
        "official_seed_inventory_sha256": (official_seed_inventory.canonical_sha256),
        "full_inventory_sha256": full_inventory_sha256,
        "implementation_registry_sha256": implementation_registry_sha256,
        "aggregation_sha256": aggregation_sha256,
        "result_payload_schema_sha256": (
            ar.D7_SCIENTIFIC_RESULT_IMPLEMENTATION_SCHEMA_SHA256
        ),
        "producer": {
            "producer_id": D7_OFFICIAL_PRODUCER_ID,
            "module": D7_OFFICIAL_PRODUCER_MODULE,
            "qualname": D7_OFFICIAL_PRODUCER_QUALNAME,
            "parameters": [],
        },
        "counts": dict(_EXPECTED_COUNTS),
        "oracle_materialization_barrier": "after-all-64-primary-predictions-sealed",
        "policy_override_allowed": False,
        "post_selection_exclusion_allowed": False,
    }


def _recorded_c1_design(root: Path) -> D7ConfirmationExecutionDesignDraft:
    # This verifies the pinned C1/C2 Git lineage before current bytes are used.
    load_d7_replay_attempt_contract_foundation(repository_root=root)
    c1_path = root / D7_C1_BUNDLE_REPOSITORY_PATH
    source = c1_path.read_bytes()
    c1 = D7C1SeedFreeSourceSet.from_canonical_bytes(
        source,
        expected_sha256=D7_RECORDED_C1_CANONICAL_SHA256,
    )
    document = c1.to_dict()
    try:
        implementation_component = document["components"]["implementation_registry"]
        aggregation_component = document["components"]["aggregation_application"]
        recorded_design = document["components"]["seed_free_execution_design"]["body"][
            "seed_free_execution_design"
        ]
    except (KeyError, TypeError) as error:
        raise QualificationContractError(
            "recorded C1 lacks the embedded seed-free execution design"
        ) from error
    if not isinstance(recorded_design, Mapping):
        raise QualificationContractError("recorded C1 design must be a mapping")
    if not isinstance(implementation_component, Mapping) or not isinstance(
        aggregation_component, Mapping
    ):
        raise QualificationContractError(
            "recorded C1 lacks implementation or aggregation components"
        )
    implementation_body = implementation_component.get("body")
    aggregation_body = aggregation_component.get("body")
    if not isinstance(implementation_body, Mapping) or not isinstance(
        aggregation_body, Mapping
    ):
        raise QualificationContractError(
            "recorded C1 implementation or aggregation body is malformed"
        )
    locked_aggregation = aggregation_body.get("locked_aggregation")
    if not isinstance(locked_aggregation, Mapping):
        raise QualificationContractError(
            "recorded C1 aggregation lacks its locked successor body"
        )
    pinned_components = (
        (
            "implementation registry",
            implementation_component,
            implementation_body,
            D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_SCHEMA_VERSION,
            D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_SHA256,
            D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_BYTE_COUNT,
        ),
        (
            "aggregation application",
            aggregation_component,
            aggregation_body,
            D7_RECORDED_C1_AGGREGATION_APPLICATION_SCHEMA_VERSION,
            D7_RECORDED_C1_AGGREGATION_APPLICATION_SHA256,
            D7_RECORDED_C1_AGGREGATION_APPLICATION_BYTE_COUNT,
        ),
        (
            "locked aggregation",
            {"canonical_sha256": D7_RECORDED_C1_LOCKED_AGGREGATION_SHA256},
            locked_aggregation,
            D7_RECORDED_C1_LOCKED_AGGREGATION_SCHEMA_VERSION,
            D7_RECORDED_C1_LOCKED_AGGREGATION_SHA256,
            D7_RECORDED_C1_LOCKED_AGGREGATION_BYTE_COUNT,
        ),
    )
    for label, component, body, schema, digest, byte_count in pinned_components:
        if (
            body.get("schema_version") != schema
            or component.get("canonical_sha256") != digest
            or canonical_json_sha256(body) != digest
            or len(canonical_json_bytes(body)) != byte_count
        ):
            raise QualificationContractError(f"recorded C1 {label} differs")
    bindings = aggregation_body.get("bindings")
    if (
        not isinstance(bindings, Mapping)
        or bindings.get("implementation_registry_sha256")
        != D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_SHA256
        or bindings.get("successor_locked_aggregation_sha256")
        != D7_RECORDED_C1_LOCKED_AGGREGATION_SHA256
    ):
        raise QualificationContractError(
            "recorded C1 aggregation bindings differ from pinned components"
        )
    parent = load_qualification_protocol(
        root / D7_OFFICIAL_PARENT_PROTOCOL_REPOSITORY_PATH,
        expected_source_sha256=D7_OFFICIAL_PARENT_PROTOCOL_SHA256,
        expected_canonical_sha256=D7_OFFICIAL_PARENT_PROTOCOL_SHA256,
    )
    return _build_recorded_c1_d7_confirmation_execution_design(
        parent_protocol=parent,
        recorded_document=recorded_design,
    )


def _require_official_producer_identity(candidate: object) -> FunctionType:
    expected = globals().get("_OFFICIAL_PRODUCER_FUNCTION")
    if (
        type(candidate) is not FunctionType
        or candidate is not expected
        or candidate.__module__ != D7_OFFICIAL_PRODUCER_MODULE
        or candidate.__qualname__ != D7_OFFICIAL_PRODUCER_QUALNAME
        or candidate.__code__.co_argcount != 0
        or candidate.__code__.co_posonlyargcount != 0
        or candidate.__code__.co_kwonlyargcount != 0
        or candidate.__closure__ is not None
    ):
        raise QualificationContractError("official producer identity differs")
    return candidate


def _require_exact_artifact_binding(
    binding: D7AuthorityArtifactBinding,
    *,
    role: str,
    contract_id: str,
    canonical_sha256: str,
    byte_count: int,
) -> None:
    if type(binding) is not D7AuthorityArtifactBinding or (
        binding.artifact_role,
        binding.artifact_contract_id,
        binding.canonical_sha256,
        binding.byte_count,
    ) != (role, contract_id, canonical_sha256, byte_count):
        raise QualificationContractError(f"{role} binding differs from exact bytes")


@dataclass(frozen=True, slots=True, init=False)
class _D7OfficialProducerContext:
    design: D7ConfirmationExecutionDesignDraft
    official_seed_inventory: D7OfficialSeedInventoryRecord
    replay_target_sha256: str
    full_inventory_sha256: str
    aggregation_sha256: str
    gate_manifest_sha256: str

    def __init__(
        self,
        *,
        design: D7ConfirmationExecutionDesignDraft,
        official_seed_inventory: D7OfficialSeedInventoryRecord,
        replay_target_sha256: str,
        full_inventory_sha256: str,
        aggregation_sha256: str,
        gate_manifest_sha256: str,
        _factory_token: object,
    ) -> None:
        if _factory_token is not _CONTEXT_FACTORY_TOKEN:
            raise QualificationContractError(
                "official producer context requires the fixed descriptor loader"
            )
        for name, value in (
            ("design", design),
            ("official_seed_inventory", official_seed_inventory),
            ("replay_target_sha256", replay_target_sha256),
            ("full_inventory_sha256", full_inventory_sha256),
            ("aggregation_sha256", aggregation_sha256),
            ("gate_manifest_sha256", gate_manifest_sha256),
        ):
            object.__setattr__(self, name, value)
        if type(self.design) is not D7ConfirmationExecutionDesignDraft:
            raise TypeError("context design has the wrong exact type")
        if type(self.official_seed_inventory) is not D7OfficialSeedInventoryRecord:
            raise TypeError("context official seed inventory has the wrong type")


def _load_official_producer_context() -> _D7OfficialProducerContext:
    root = _repository_root()
    descriptor_path = _official_descriptor_path(root)
    if not descriptor_path.is_file() or descriptor_path.is_symlink():
        raise QualificationContractError(
            "official D7 fused descriptor is absent; execution is not authorized"
        )
    snapshot = fused_authority.load_d7_fused_authority_snapshot(descriptor_path)
    if snapshot.repository_root != root or snapshot.descriptor_path != descriptor_path:
        raise QualificationContractError(
            "official descriptor does not resolve the producer repository"
        )
    producer = _require_official_producer_identity(produce_d7_official_result)
    # Reobserve the exact function object against the descriptor-bound identity.
    fused_start._observe_execution(snapshot, producer)

    design = _recorded_c1_design(root)
    target = snapshot.replay_target
    inventory = snapshot.bundle.official_seed_inventory
    _require_exact_artifact_binding(
        target.official_seed_inventory_binding,
        role="official-seed-inventory",
        contract_id=inventory.schema_version,
        canonical_sha256=inventory.canonical_sha256,
        byte_count=inventory.byte_count,
    )
    implementation_sha256 = target.implementation_registry_binding.canonical_sha256
    _require_exact_artifact_binding(
        target.implementation_registry_binding,
        role="implementation-registry",
        contract_id=D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_SCHEMA_VERSION,
        canonical_sha256=D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_SHA256,
        byte_count=D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_BYTE_COUNT,
    )
    if implementation_sha256 != D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_SHA256:
        raise QualificationContractError(
            "target implementation registry differs from recorded C1"
        )
    aggregation = build_d7_official_aggregation_document(
        implementation_registry_sha256=implementation_sha256
    )
    aggregation_sha256 = canonical_json_sha256(aggregation)
    _require_exact_artifact_binding(
        target.aggregation_binding,
        role="aggregation",
        contract_id=D7_OFFICIAL_AGGREGATION_SCHEMA_VERSION,
        canonical_sha256=aggregation_sha256,
        byte_count=len(canonical_json_bytes(aggregation)),
    )
    result_schema_document = ar._result_schema_descriptor()
    result_schema_sha256 = canonical_json_sha256(result_schema_document)
    if result_schema_sha256 != ar.D7_SCIENTIFIC_RESULT_IMPLEMENTATION_SCHEMA_SHA256:
        raise QualificationContractError(
            "current result schema descriptor differs from its implementation digest"
        )
    _require_exact_artifact_binding(
        target.result_payload_schema_binding,
        role="result-payload-schema",
        contract_id=ar.D7_RESULT_SCHEMA_DESCRIPTOR_VERSION,
        canonical_sha256=result_schema_sha256,
        byte_count=len(canonical_json_bytes(result_schema_document)),
    )
    target_design = target.full_design_binding
    if (
        target_design.official_seed_inventory_sha256 != inventory.canonical_sha256
        or target_design.implementation_registry_sha256
        != D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_SHA256
        or target_design.aggregation_sha256 != aggregation_sha256
        or target_design.result_payload_schema_sha256 != result_schema_sha256
    ):
        raise QualificationContractError(
            "target full-design leaf digests differ from exact execution referents"
        )
    full_inventory = build_d7_official_full_inventory_document(
        design=design,
        official_seed_inventory=inventory,
    )
    full_inventory_sha256 = canonical_json_sha256(full_inventory)
    _require_exact_artifact_binding(
        target_design.inventory_binding,
        role="full-inventory",
        contract_id=D7_OFFICIAL_FULL_INVENTORY_SCHEMA_VERSION,
        canonical_sha256=full_inventory_sha256,
        byte_count=len(canonical_json_bytes(full_inventory)),
    )
    if full_inventory_sha256 != target_design.inventory_sha256:
        raise QualificationContractError(
            "target full-inventory digest differs from exact reconstruction"
        )
    full_design = build_d7_official_full_design_document(
        design=design,
        official_seed_inventory=inventory,
        full_inventory_sha256=full_inventory_sha256,
        implementation_registry_sha256=implementation_sha256,
        aggregation_sha256=aggregation_sha256,
    )
    full_design_sha256 = canonical_json_sha256(full_design)
    _require_exact_artifact_binding(
        target_design.design_binding,
        role="full-design",
        contract_id=D7_OFFICIAL_FULL_DESIGN_SCHEMA_VERSION,
        canonical_sha256=full_design_sha256,
        byte_count=len(canonical_json_bytes(full_design)),
    )
    return _D7OfficialProducerContext(
        design=design,
        official_seed_inventory=inventory,
        replay_target_sha256=target.canonical_sha256,
        full_inventory_sha256=full_inventory_sha256,
        aggregation_sha256=aggregation_sha256,
        gate_manifest_sha256=canonical_json_sha256(aggregation["gate_manifest"]),
        _factory_token=_CONTEXT_FACTORY_TOKEN,
    )


def _rows_fingerprint(rows: object) -> str:
    return canonical_json_sha256(array_fingerprint(np.asarray(rows, dtype="<i8")))


def _independent_core_prerequisite_reasons(
    *,
    oracle: object,
    handoff: _D7SeedSlotPrimaryRuntimeHandoff,
    field_graph_id: str,
) -> tuple[str, ...]:
    field_support = getattr(oracle, "field_support_mask", None)
    first_moment = getattr(oracle, "first_moment_field", None)
    if (
        getattr(oracle, "case_semantics", None)
        != "prerequisite-failure|prerequisite-failure"
        or not isinstance(field_support, np.ndarray)
        or not isinstance(first_moment, np.ndarray)
        or np.any(field_support)
        or np.any(first_moment)
    ):
        raise QualificationContractError(
            "core prerequisite oracle is not the zero-support spectral control"
        )
    estimate = dict(handoff.field_estimates)[field_graph_id]
    reasons = {REASON_CORE_AMPLITUDE_NOT_LOCALIZED}
    if estimate.field_graph.canonical_edges.shape[0] == 0:
        reasons.add(REASON_EMPTY_GRAPH)
    return tuple(sorted(reasons))


def _independent_loop_prerequisite_reasons(
    *, oracle: object, blind_input: object
) -> tuple[str, ...]:
    field_support = getattr(oracle, "field_support_mask", None)
    first_moment = getattr(oracle, "first_moment_field", None)
    if (
        getattr(oracle, "case_semantics", None)
        != "prerequisite-failure|prerequisite-failure"
        or not isinstance(field_support, np.ndarray)
        or not isinstance(first_moment, np.ndarray)
        or np.any(field_support)
        or np.any(first_moment)
    ):
        raise QualificationContractError(
            "loop prerequisite oracle is not the zero-support spectral control"
        )
    rows = tuple(int(item) for item in blind_input.ordered_loop_rows)
    reasons = {
        REASON_BOUNDARY_AMPLITUDE_FLOOR,
        REASON_BOUNDARY_IDENTIFIABILITY_FLOOR,
        REASON_BOUNDARY_COHERENCE_FLOOR,
    }
    if len(set(rows)) < 3:
        reasons.add(REASON_LOOP_SUPPORT)
    if len(set(rows)) != len(rows):
        reasons.add(REASON_LOOP_ROWS_REPEATED)
    return tuple(sorted(reasons))


def _score_handoff(
    handoff: _D7SeedSlotPrimaryRuntimeHandoff,
    *,
    oracle: object,
    expected_core: tuple[ExpectedCoreCell, ...],
    expected_loop: tuple[ExpectedCell, ...],
) -> tuple[
    tuple[CoreCellSummary, ...],
    CorePrimaryUnitSummary,
    tuple[CrossedCellSummary, ...],
    PrimaryUnitSummary,
]:
    prediction = handoff.prediction
    if getattr(oracle, "case_semantics", None) != handoff.unit.case_semantics:
        raise QualificationContractError(
            "materialized oracle semantics differ from the frozen primary unit"
        )
    core_inputs = dict(handoff.blind_core_inputs)
    loop_inputs = dict(handoff.blind_loop_inputs)
    estimates = dict(handoff.field_estimates)
    core_predictions = {
        item.core_cell_id: item.prediction for item in prediction.core_predictions
    }
    loop_predictions = {
        item.loop_cell_id: item.prediction for item in prediction.loop_predictions
    }
    anchor_rows = oracle.row_ids[oracle.core_anchor_mask]

    core_cells: list[CoreCellSummary] = []
    for expected in expected_core:
        blind = core_inputs[expected.core_cell_id]
        sealed = core_predictions[expected.core_cell_id]
        estimate = estimates[expected.field_graph_id]
        reasons = (
            _independent_core_prerequisite_reasons(
                oracle=oracle,
                handoff=handoff,
                field_graph_id=expected.field_graph_id,
            )
            if expected.expected_core_disposition
            is CoreDisposition.PREREQUISITE_FAILURE
            else ()
        )
        truth = build_core_oracle_truth(
            blind_input=blind,
            policy=handoff.core_policy,
            expected_disposition=expected.expected_core_disposition,
            anchor_rows=anchor_rows,
            expected_prerequisite_reasons=reasons,
            obligation_mode=ObligationMode.INDIVIDUALLY_REQUIRED,
            evaluation_unit=EvaluationUnit.CORE,
        )
        evaluation = score_core_prediction(sealed, truth)
        difference = tuple(
            sorted(
                {int(item) for item in sealed.candidate_rows}
                ^ {int(item) for item in anchor_rows}
            )
        )
        core_cells.append(
            CoreCellSummary(
                core_cell_id=expected.core_cell_id,
                primary_unit_id=expected.primary_unit_id,
                field_graph_id=expected.field_graph_id,
                expected_disposition=expected.expected_core_disposition,
                field_graph_fingerprint_sha256=(
                    estimate.field_graph.fingerprint_sha256
                ),
                field_estimate_fingerprint_sha256=estimate.fingerprint_sha256,
                blind_input_fingerprint_sha256=blind.fingerprint_sha256,
                prediction_fingerprint_sha256=sealed.fingerprint_sha256,
                oracle_fingerprint_sha256=truth.fingerprint_sha256,
                candidate_fingerprint_sha256=_rows_fingerprint(sealed.candidate_rows),
                oracle_anchor_fingerprint_sha256=_rows_fingerprint(anchor_rows),
                candidate_anchor_symmetric_difference_rows=difference,
                attempt_status=evaluation.observed_attempt_status,
                prediction_class=sealed.prediction_class,
                state=evaluation.gate_verdict,
                reason_codes=evaluation.reason_codes,
            )
        )

    loop_cells: list[CrossedCellSummary] = []
    for expected in expected_loop:
        blind = loop_inputs[expected.cell_id]
        sealed = loop_predictions[expected.cell_id]
        reasons = (
            _independent_loop_prerequisite_reasons(
                oracle=oracle,
                blind_input=blind,
            )
            if expected.expected_loop_disposition
            is LoopDisposition.PREREQUISITE_FAILURE
            else ()
        )
        expected_cycles = (
            None
            if expected.expected_loop_disposition
            is LoopDisposition.PREREQUISITE_FAILURE
            else evaluate_oracle_sampled_response(
                oracle.first_moment_field,
                blind.ordered_loop_rows,
            )
        )
        truth = build_loop_oracle_truth(
            blind_input=blind,
            policy=handoff.loop_policy,
            expected_disposition=expected.expected_loop_disposition,
            expected_sampled_cycles=expected_cycles,
            expected_prerequisite_reasons=reasons,
            obligation_mode=ObligationMode.INDIVIDUALLY_REQUIRED,
        )
        evaluation = score_loop_prediction(sealed, truth)
        loop_cells.append(
            CrossedCellSummary(
                cell_id=expected.cell_id,
                primary_unit_id=expected.primary_unit_id,
                field_graph_id=expected.field_graph_id,
                cycle_graph_id=expected.cycle_graph_id,
                loop_role=expected.loop_role,
                expected_disposition=expected.expected_loop_disposition,
                field_graph_fingerprint_sha256=(blind.field_graph_fingerprint_sha256),
                cycle_graph_fingerprint_sha256=(blind.cycle_graph_fingerprint_sha256),
                field_estimate_fingerprint_sha256=(
                    blind.field_estimate_fingerprint_sha256
                ),
                cycle_binding_fingerprint_sha256=(
                    blind.cycle_binding_fingerprint_sha256
                ),
                representative_content_sha256=(blind.representative_content_sha256),
                blind_input_fingerprint_sha256=blind.fingerprint_sha256,
                prediction_fingerprint_sha256=sealed.fingerprint_sha256,
                oracle_fingerprint_sha256=truth.fingerprint_sha256,
                attempt_status=evaluation.observed_attempt_status,
                prediction_class=sealed.prediction_class,
                state=evaluation.gate_verdict,
                continuous_signed_total_cycles=sealed.signed_total_cycles,
                oracle_absolute_error_cycles=evaluation.signed_error_cycles,
                reason_codes=evaluation.reason_codes,
            )
        )

    first_core = expected_core[0]
    core_status = (
        AttemptStatus.INSUFFICIENT
        if first_core.expected_core_disposition is CoreDisposition.PREREQUISITE_FAILURE
        else AttemptStatus.EVALUABLE
    )
    core_prediction = {
        CoreDisposition.LOCALIZED_CORE: CorePredictionClass.LOCALIZED_CORE,
        CoreDisposition.NO_CORE: CorePredictionClass.NO_CORE,
        CoreDisposition.PREREQUISITE_FAILURE: CorePredictionClass.ABSTAIN,
    }[first_core.expected_core_disposition]
    primary_sha256 = core_inputs[first_core.core_cell_id].primary_unit_sha256
    core_template = CorePrimaryUnitSummary(
        primary_unit_id=first_core.primary_unit_id,
        selection_seed=first_core.selection_seed,
        control_id=first_core.control_id,
        expected_disposition=first_core.expected_core_disposition,
        stress_assignments=first_core.stress_assignments,
        d2_scientific_input_fingerprint_sha256=primary_sha256,
        domain_instance_fingerprint_sha256=(
            handoff.primary_execution.domain.fingerprint_sha256
        ),
        support_instance_fingerprint_sha256=(
            handoff.primary_execution.cycle_class.fingerprint_sha256
        ),
        attempt_status=core_status,
        prediction_class=core_prediction,
        state=QualificationState.PASS,
        max_candidate_symmetric_difference_rows=0,
        reason_codes=(),
        core_cell_ids=tuple(item.core_cell_id for item in expected_core),
    )
    boundary_disposition = next(
        item.expected_loop_disposition
        for item in expected_loop
        if item.loop_role is LoopRole.PRIMARY_BOUNDARY
    )
    loop_status = (
        AttemptStatus.INSUFFICIENT
        if boundary_disposition is LoopDisposition.PREREQUISITE_FAILURE
        else AttemptStatus.EVALUABLE
    )
    loop_prediction = {
        LoopDisposition.NONZERO: LoopPredictionClass.NONZERO,
        LoopDisposition.NULL: LoopPredictionClass.NULL,
        LoopDisposition.PREREQUISITE_FAILURE: LoopPredictionClass.ABSTAIN,
    }[boundary_disposition]
    first_loop = expected_loop[0]
    loop_template = PrimaryUnitSummary(
        primary_unit_id=first_loop.primary_unit_id,
        selection_seed=first_loop.selection_seed,
        control_id=first_loop.control_id,
        expected_disposition=boundary_disposition,
        stress_assignments=first_loop.stress_assignments,
        domain_instance_fingerprint_sha256=(
            handoff.primary_execution.domain.fingerprint_sha256
        ),
        support_instance_fingerprint_sha256=(
            handoff.primary_execution.cycle_class.fingerprint_sha256
        ),
        attempt_status=loop_status,
        prediction_class=loop_prediction,
        state=QualificationState.PASS,
        continuous_total_span_cycles=0.0,
        reason_codes=(),
        crossed_cell_ids=tuple(item.cell_id for item in expected_loop),
    )
    return (
        tuple(sorted(core_cells, key=lambda item: item.core_cell_id)),
        core_template,
        tuple(sorted(loop_cells, key=lambda item: item.cell_id)),
        loop_template,
    )


def _joined_state(
    core: CorePrimaryUnitSummary, loop: PrimaryUnitSummary
) -> ar.D7GateState:
    if any(
        item in {QualificationState.FAIL, QualificationState.FAIL_GRAPH_DEPENDENCE}
        for item in (core.state, loop.state)
    ):
        return ar.D7GateState.FAIL
    if all(item is QualificationState.PASS for item in (core.state, loop.state)):
        return ar.D7GateState.PASS
    if all(item is QualificationState.NOT_RUN for item in (core.state, loop.state)):
        return ar.D7GateState.NOT_RUN
    return ar.D7GateState.INSUFFICIENT


def _joined_status(
    core: CorePrimaryUnitSummary, loop: PrimaryUnitSummary
) -> AttemptStatus:
    if (
        core.attempt_status is AttemptStatus.NOT_RUN
        and loop.attempt_status is AttemptStatus.NOT_RUN
    ):
        return AttemptStatus.NOT_RUN
    if (
        core.attempt_status is AttemptStatus.EVALUABLE
        and loop.attempt_status is AttemptStatus.EVALUABLE
    ):
        return AttemptStatus.EVALUABLE
    return AttemptStatus.INSUFFICIENT


def _gate_outcomes(
    *,
    primary_units: tuple[components.D7JoinedPrimaryUnitOutcome, ...],
    strata: tuple[StratumSummary, ...],
) -> tuple[components.D7AggregateGateOutcome, ...]:
    return component_validation._derive_exact_d7_gate_outcomes(
        primary_units=primary_units,
        strata=strata,
    )


def _event_lane(
    *,
    context: _D7OfficialProducerContext,
    lane_kind: components.D7ExecutionLaneKind,
    cell_id: str,
    outcome: CoreCellSummary | CrossedCellSummary,
) -> components.D7ExecutionEventLaneOutcome:
    lane_id = f"{lane_kind.value}.{cell_id}"
    payloads = component_validation._d7_event_stage_payload_sha256s(
        replay_target_sha256=context.replay_target_sha256,
        full_inventory_sha256=context.full_inventory_sha256,
        aggregation_sha256=context.aggregation_sha256,
        lane_id=lane_id,
        lane_kind=lane_kind,
        cell_id=cell_id,
        outcome=outcome,
    )
    previous = components._GENESIS_STAGE_BINDING_SHA256
    bindings: list[components.D7ExecutionEventStageBinding] = []
    for stage, payload_sha256 in zip(
        tuple(components.D7ExecutionStage), payloads, strict=True
    ):
        binding = components.D7ExecutionEventStageBinding(
            stage=stage,
            payload_sha256=payload_sha256,
            previous_stage_binding_sha256=previous,
        )
        bindings.append(binding)
        previous = binding.binding_sha256
    return components.D7ExecutionEventLaneOutcome(
        lane_id=lane_id,
        lane_kind=lane_kind,
        cell_id=cell_id,
        stage_bindings=tuple(bindings),
    )


def _component_binding(value: object) -> ar.D7ResultComponentBinding:
    return ar.D7ResultComponentBinding(
        component_id=value.component_id,
        component_contract_id=value.component_contract_id,
        component_canonical_sha256=value.canonical_sha256,
        byte_count=len(value.canonical_bytes),
        record_count=len(value.records),
    )


def _seal_all_primary_handoffs(
    design: D7ConfirmationExecutionDesignDraft,
    *,
    seed_by_slot: dict[str, int],
) -> tuple[_D7SeedSlotPrimaryRuntimeHandoff, ...]:
    """Seal the complete primary inventory without materializing an oracle."""

    if type(design) is not D7ConfirmationExecutionDesignDraft:
        raise TypeError("design must be the exact D7 execution design")
    if type(seed_by_slot) is not dict or tuple(seed_by_slot) != (
        D7_CONFIRMATION_SEED_SLOT_IDS
    ):
        raise QualificationContractError(
            "seed_by_slot differs from the exact official ordinal mapping"
        )
    handoffs = tuple(
        _execute_d7_seed_slot_primary_runtime(
            design,
            unit=unit,
            supplied_seed=seed_by_slot[unit.seed_slot_id],
        )
        for unit in design.inventory.primary_units
    )
    if (
        len(handoffs) != D7_CONFIRMATION_PRIMARY_UNIT_COUNT
        or any(type(item) is not _D7SeedSlotPrimaryRuntimeHandoff for item in handoffs)
        or tuple(item.unit.primary_unit_id for item in handoffs)
        != tuple(item.primary_unit_id for item in design.inventory.primary_units)
    ):
        raise QualificationContractError(
            "global prediction barrier did not seal the exact 64-primary inventory"
        )
    return handoffs


def _execute_official_context(
    context: _D7OfficialProducerContext,
) -> D7ScientificProducerOutput:
    if type(context) is not _D7OfficialProducerContext:
        raise TypeError("context must be the exact official producer context")
    design = context.design
    seed_by_slot = _seed_by_slot(context.official_seed_inventory)
    expected_core, expected_loop, _expected_strata = _expected_manifests(
        design,
        context.official_seed_inventory,
    )
    core_by_primary = {
        unit.primary_unit_id: tuple(
            item
            for item in expected_core
            if item.primary_unit_id == unit.primary_unit_id
        )
        for unit in design.inventory.primary_units
    }
    loop_by_primary = {
        unit.primary_unit_id: tuple(
            item
            for item in expected_loop
            if item.primary_unit_id == unit.primary_unit_id
        )
        for unit in design.inventory.primary_units
    }

    # Global oracle barrier: this entire tuple must finish successfully before
    # the first call to SpectralMomentConfirmationGenerator.generate below.
    handoffs = _seal_all_primary_handoffs(
        design,
        seed_by_slot=seed_by_slot,
    )

    generator = SpectralMomentConfirmationGenerator()
    core_cells: list[CoreCellSummary] = []
    loop_cells: list[CrossedCellSummary] = []
    core_templates: list[CorePrimaryUnitSummary] = []
    loop_templates: list[PrimaryUnitSummary] = []
    for handoff in handoffs:
        bundle = generator.generate(handoff.spec)
        cases = {item.case_id: item for item in bundle.cases}
        if tuple(cases) != tuple(item.case_id for item in bundle.cases):
            raise QualificationContractError(
                "materialized spectral case registry contains duplicate IDs"
            )
        case = cases.get(handoff.unit.case_id)
        if (
            case is None
            or case.spec.receipt_sha256 != handoff.spec.receipt_sha256
            or case.estimator_inputs.fingerprint_sha256
            != handoff.estimator_inputs.fingerprint_sha256
            or case.estimator_inputs.to_dict() != handoff.estimator_inputs.to_dict()
        ):
            raise QualificationContractError(
                "materialized oracle does not rejoin the sealed estimator input"
            )
        scored_core, core_template, scored_loop, loop_template = _score_handoff(
            handoff,
            oracle=case.oracle_truth,
            expected_core=core_by_primary[handoff.unit.primary_unit_id],
            expected_loop=loop_by_primary[handoff.unit.primary_unit_id],
        )
        core_cells.extend(scored_core)
        loop_cells.extend(scored_loop)
        core_templates.append(core_template)
        loop_templates.append(loop_template)

    materialized_core = materialize_expected_core_cells(expected_core, core_cells)
    materialized_loop = materialize_expected_cells(expected_loop, loop_cells)
    collapsed_core = collapse_core_primary_units(
        expected_core,
        materialized_core,
        core_templates,
        candidate_difference_tolerance_rows=(
            design.thresholds.core_candidate_difference_tolerance_rows
        ),
    )
    collapsed_loop = collapse_primary_units(
        expected_loop,
        materialized_loop,
        loop_templates,
        graph_total_tolerance_cycles=(design.thresholds.graph_total_tolerance_cycles),
    )
    core_primary = {item.primary_unit_id: item for item in collapsed_core}
    loop_primary = {item.primary_unit_id: item for item in collapsed_loop}
    unit_by_id = {item.primary_unit_id: item for item in design.inventory.primary_units}
    joined: list[components.D7JoinedPrimaryUnitOutcome] = []
    for primary_unit_id in sorted(unit_by_id):
        unit = unit_by_id[primary_unit_id]
        core = core_primary[primary_unit_id]
        loop = loop_primary[primary_unit_id]
        state = _joined_state(core, loop)
        joined.append(
            components.D7JoinedPrimaryUnitOutcome(
                primary_unit_id=primary_unit_id,
                seed_slot_id=unit.seed_slot_id,
                official_seed=seed_by_slot[unit.seed_slot_id],
                case_id=_paired_case_id(unit),
                case_semantics=unit.case_semantics,
                core_summary=core,
                loop_summary=loop,
                attempt_status=_joined_status(core, loop),
                state=state,
                reason_codes=()
                if state is ar.D7GateState.PASS
                else tuple(
                    sorted(
                        {
                            reason
                            for summary in (core, loop)
                            if summary.state is not QualificationState.PASS
                            for reason in summary.reason_codes
                        }
                    )
                ),
            )
        )
    joined_units = tuple(joined)
    strata = component_validation._derive_exact_d7_required_strata(
        design.inventory.expected_strata,
        joined_units,
    )

    coordinates = {
        "replay_target_sha256": context.replay_target_sha256,
        "full_inventory_sha256": context.full_inventory_sha256,
        "aggregation_sha256": context.aggregation_sha256,
    }
    core_component = components.D7CoreCellOutcomesPayload(
        records=materialized_core, **coordinates
    )
    loop_component = components.D7LoopCellOutcomesPayload(
        records=materialized_loop, **coordinates
    )
    primary_component = components.D7PrimaryUnitOutcomesPayload(
        records=joined_units, **coordinates
    )
    stratum_component = components.D7RequiredStratumOutcomesPayload(
        records=strata, **coordinates
    )
    gate_rows = _gate_outcomes(primary_units=joined_units, strata=strata)
    gate_component = components.D7AggregateGateOutcomesPayload(
        gate_manifest_sha256=context.gate_manifest_sha256,
        records=gate_rows,
        **coordinates,
    )
    lanes = tuple(
        sorted(
            (
                *(
                    _event_lane(
                        context=context,
                        lane_kind=components.D7ExecutionLaneKind.CORE,
                        cell_id=item.core_cell_id,
                        outcome=item,
                    )
                    for item in materialized_core
                ),
                *(
                    _event_lane(
                        context=context,
                        lane_kind=components.D7ExecutionLaneKind.LOOP,
                        cell_id=item.cell_id,
                        outcome=item,
                    )
                    for item in materialized_loop
                ),
            ),
            key=lambda item: item.lane_id,
        )
    )
    event_component = components.D7ExecutionEventLedgerPayload(
        records=lanes, **coordinates
    )
    ordered_components = (
        event_component,
        core_component,
        loop_component,
        primary_component,
        stratum_component,
        gate_component,
    )
    gate_summary = ar.D7GateOutcomeSummary.from_gate_states(
        gate_manifest_sha256=context.gate_manifest_sha256,
        gate_states=tuple(item.state for item in gate_rows),
        gate_results_component_sha256=gate_component.canonical_sha256,
    )
    result_reasons = tuple(
        sorted(
            {
                reason
                for item in gate_rows
                if item.state is not ar.D7GateState.PASS
                for reason in item.reason_codes
            }
        )
    )
    result_payload = ar.D7ScientificResultPayload(
        state=gate_summary.aggregate_state,
        reason_codes=result_reasons,
        gate_summary=gate_summary,
        component_bindings=tuple(
            _component_binding(item) for item in ordered_components
        ),
        **coordinates,
    )
    component_validation.validate_d7_result_component_bundle(
        event_ledger=event_component,
        core_cells=core_component,
        loop_cells=loop_component,
        primary_units=primary_component,
        required_strata=stratum_component,
        aggregate_gates=gate_component,
        result_payload=result_payload,
    )
    return D7ScientificProducerOutput(
        event_ledger=event_component,
        core_cells=core_component,
        loop_cells=loop_component,
        primary_units=primary_component,
        required_strata=stratum_component,
        aggregate_gates=gate_component,
        result_payload=result_payload,
    )


def produce_d7_official_result() -> D7ScientificProducerOutput:
    """Run the one fixed official D7 producer; no caller input is accepted."""

    return _execute_official_context(_load_official_producer_context())


_OFFICIAL_PRODUCER_FUNCTION = produce_d7_official_result
