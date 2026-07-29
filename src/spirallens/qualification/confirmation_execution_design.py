"""Seed-free D7 execution topology, explicitly not a freeze or admission.

This module reconstructs the complete D6 parent design from a strict
``LoadedQualificationProtocol`` and maps it onto a construction-diverse,
seed-slot-based confirmation inventory.  The mapping preserves the exact
64-primary / 192-core / 1,152-loop repeated-measures topology.

Two D6 bodies cannot be copied byte-for-byte into a new-seed confirmation:
the required-cell body contains selection seeds and seed-bearing identifiers,
and the required-stress body contains those same primary-unit identifiers in
its stratum memberships.  This module makes that incompatibility a first-class
record.  Structural projection equality is evidence for a proposed rebinding;
it is not satisfaction of the D6 v0.1 admission contract.

No concrete confirmation seed, result, gate aggregate, terminal writer,
family admission, model value, or subject value is accepted by this API.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import ClassVar

from spirallens.core.canonical import (
    CanonicalJsonError,
    canonical_json_bytes,
    canonical_json_sha256,
    parse_canonical_json,
    sha256_bytes,
)
from spirallens.synthetic.spectral_moment_confirmation import (
    SPECTRAL_MOMENT_AMBIENT_DIMENSION,
    SPECTRAL_MOMENT_CASE_REGISTRY,
    SPECTRAL_MOMENT_GENERATOR_FAMILY_ID,
    SPECTRAL_MOMENT_GRID_SIDE,
    SPECTRAL_MOMENT_SAMPLES_PER_SPLIT,
    SPECTRAL_MOMENT_STATE_NORMALIZATION_ID,
    SPECTRAL_MOMENT_STATE_NORMALIZATION_SCALE,
    SPECTRAL_MOMENT_STRESS_TRANSLATION_ID,
    spectral_moment_state_geometry_conformance,
)

from .advancement import (
    ConfirmationDesignBodySet,
    LoadedScopeLimitedD6Decision,
)
from .common import (
    CoreDisposition,
    LoopDisposition,
    QualificationContractError,
    require_sha256,
    require_slug,
)
from .confirmation_protocol import D7ParentD6Binding
from .persistence import LoadedQualificationProtocol
from .protocol import (
    BoundaryTemplate,
    CoveragePolicy,
    DomainDeclaration,
    GraphAxes,
    LoopRole,
    NumericStressLevel,
    StressAssignment,
    StressAxis,
    Thresholds,
    required_stress_stratum_id,
)

D7_CONFIRMATION_EXECUTION_DRAFT_SCHEMA_VERSION = (
    "spirallens.d7-confirmation-execution-design-draft.v0.1"
)
D7_CONFIRMATION_INVENTORY_SCHEMA_VERSION = (
    "spirallens.d7-confirmation-execution-inventory-template.v0.1"
)
D7_PARENT_PROTOCOL_DESIGN_BINDING_SCHEMA_VERSION = (
    "spirallens.d7-parent-protocol-design-binding.v0.1"
)
D7_PARENT_MANIFEST_COMPATIBILITY_SCHEMA_VERSION = (
    "spirallens.d7-parent-manifest-compatibility.v0.1"
)
D7_STRUCTURAL_PROJECTION_SCHEMA_VERSION = (
    "spirallens.d7-confirmation-structural-projection.v0.1"
)
D7_CONFIRMATION_STRESS_TRANSLATION_SCHEMA_VERSION = (
    "spirallens.d7-confirmation-stress-translation.v0.1"
)
MAX_D7_CONFIRMATION_EXECUTION_DRAFT_BYTES = 4 * 1024 * 1024

D7_CONFIRMATION_SEED_SLOT_IDS = (
    "confirmation-seed-slot-00",
    "confirmation-seed-slot-01",
)
D7_CONFIRMATION_PRIMARY_UNIT_COUNT = 64
D7_CONFIRMATION_CORE_CELL_COUNT = 192
D7_CONFIRMATION_LOOP_CELL_COUNT = 1152
D7_CONFIRMATION_EVENT_LANE_COUNT = 1344

_DEVELOPMENT_SEED_EXCLUSION_ENTRIES = (
    (11, "spectral generator family-identity development test"),
    (12, "spectral generator family-identity development test"),
    (9001, "spectral confirmation crossed-path development test"),
    (9002, "spectral confirmation full-inventory development test"),
)
D7_CONFIRMATION_DEVELOPMENT_SEEDS = tuple(
    seed for seed, _reason in _DEVELOPMENT_SEED_EXCLUSION_ENTRIES
)

_AUTHORITY = {
    "confirmation_family_admitted": False,
    "confirmation_values_accessed": False,
    "d6_admission_spec_satisfied": False,
    "d7_execution_authorized": False,
    "d7_result_produced": False,
    "d8_execution_authorized": False,
    "integer_output_authorized": False,
    "localized_core_loop_join_established": False,
    "model_access_authorized": False,
    "p0_winner_selected": False,
    "pythia_access_authorized": False,
    "representation_instrument_advanced": False,
    "semantic_authority": False,
    "subject_access_authorized": False,
    "synthetic_qualified": False,
    "topology_claim_authorized": False,
}
_D7_PARENT_PROTOCOL_BINDING_FACTORY_TOKEN = object()
_D7_CONFIRMATION_EXECUTION_DESIGN_FACTORY_TOKEN = object()


def _loaded_d6(value: object) -> LoadedScopeLimitedD6Decision:
    if not isinstance(value, LoadedScopeLimitedD6Decision):
        raise TypeError(
            "loaded_d6 must be an authoritative LoadedScopeLimitedD6Decision"
        )
    return value


def _loaded_parent(value: object) -> LoadedQualificationProtocol:
    if not isinstance(value, LoadedQualificationProtocol):
        raise TypeError("parent_protocol must be a strict LoadedQualificationProtocol")
    return value


def require_d7_confirmation_development_seed(value: object) -> int:
    """Accept only permanently excluded seeds on the development-only path."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("development_seed must be a plain integer")
    if value not in D7_CONFIRMATION_DEVELOPMENT_SEEDS:
        raise QualificationContractError(
            "development execution accepts only permanently excluded seeds"
        )
    return value


def _semantic_label(
    core: CoreDisposition,
    loop: LoopDisposition,
) -> str:
    mapping = {
        (
            CoreDisposition.LOCALIZED_CORE,
            LoopDisposition.NONZERO,
        ): "localized-core|nonzero",
        (
            CoreDisposition.LOCALIZED_CORE,
            LoopDisposition.NULL,
        ): "localized-core|null",
        (
            CoreDisposition.NO_CORE,
            LoopDisposition.NULL,
        ): "no-core|null",
        (
            CoreDisposition.PREREQUISITE_FAILURE,
            LoopDisposition.PREREQUISITE_FAILURE,
        ): "prerequisite-failure|prerequisite-failure",
    }
    try:
        return mapping[(core, loop)]
    except KeyError as error:
        raise QualificationContractError(
            "core/loop dispositions are outside the required D7 semantics"
        ) from error


def _case_by_semantic() -> dict[str, tuple[str, str, str, str, str]]:
    result = {item[1]: item for item in SPECTRAL_MOMENT_CASE_REGISTRY}
    if len(result) != 4:
        raise AssertionError("spectral case semantics must be unique")
    return result


def _stress_dict(
    assignments: tuple[StressAssignment, ...],
) -> list[dict[str, object]]:
    return [item.to_dict() for item in assignments]


def _sorted_records(
    records: list[dict[str, object]],
) -> list[dict[str, object]]:
    return sorted(records, key=canonical_json_bytes)


@dataclass(frozen=True, slots=True, init=False)
class D7ParentProtocolDesignBinding:
    """Exact full-body reconstruction of the D6 selection protocol."""

    protocol_id: str
    protocol_source_sha256: str
    protocol_canonical_sha256: str
    graph_axes_sha256: str
    required_cells_manifest_sha256: str
    required_stress_strata_sha256: str
    locked_thresholds_sha256: str
    locked_aggregation_sha256: str
    selection_implementation_registry_sha256: str
    selection_seed_count: int

    schema_version: ClassVar[str] = D7_PARENT_PROTOCOL_DESIGN_BINDING_SCHEMA_VERSION

    def __init__(
        self,
        *,
        _factory_token: object = None,
        protocol_id: str,
        protocol_source_sha256: str,
        protocol_canonical_sha256: str,
        graph_axes_sha256: str,
        required_cells_manifest_sha256: str,
        required_stress_strata_sha256: str,
        locked_thresholds_sha256: str,
        locked_aggregation_sha256: str,
        selection_implementation_registry_sha256: str,
        selection_seed_count: int,
    ) -> None:
        if _factory_token is not _D7_PARENT_PROTOCOL_BINDING_FACTORY_TOKEN:
            raise QualificationContractError(
                "D7ParentProtocolDesignBinding must be produced from the "
                "strict parent protocol and authoritative D6 decision"
            )
        for name, value in (
            ("protocol_id", protocol_id),
            ("protocol_source_sha256", protocol_source_sha256),
            ("protocol_canonical_sha256", protocol_canonical_sha256),
            ("graph_axes_sha256", graph_axes_sha256),
            (
                "required_cells_manifest_sha256",
                required_cells_manifest_sha256,
            ),
            (
                "required_stress_strata_sha256",
                required_stress_strata_sha256,
            ),
            ("locked_thresholds_sha256", locked_thresholds_sha256),
            ("locked_aggregation_sha256", locked_aggregation_sha256),
            (
                "selection_implementation_registry_sha256",
                selection_implementation_registry_sha256,
            ),
            ("selection_seed_count", selection_seed_count),
        ):
            object.__setattr__(self, name, value)
        self.__post_init__()

    def __post_init__(self) -> None:
        require_slug(self.protocol_id, label="protocol_id")
        for name in (
            "protocol_source_sha256",
            "protocol_canonical_sha256",
            "graph_axes_sha256",
            "required_cells_manifest_sha256",
            "required_stress_strata_sha256",
            "locked_thresholds_sha256",
            "locked_aggregation_sha256",
            "selection_implementation_registry_sha256",
        ):
            require_sha256(getattr(self, name), label=name)
        if self.selection_seed_count != 2:
            raise QualificationContractError(
                "D6 parent must contain exactly two selection seeds"
            )

    @classmethod
    def from_loaded(
        cls,
        loaded_d6: LoadedScopeLimitedD6Decision,
        parent_protocol: LoadedQualificationProtocol,
    ) -> D7ParentProtocolDesignBinding:
        d6 = _loaded_d6(loaded_d6)
        parent = _loaded_parent(parent_protocol)
        terminal = d6.decision.selection_terminal
        admission = d6.decision.confirmation_admission_spec
        protocol = parent.protocol
        if (
            terminal.protocol_id != protocol.protocol_id
            or terminal.protocol_source_sha256 != parent.source_sha256
            or terminal.protocol_canonical_sha256 != parent.canonical_sha256
        ):
            raise QualificationContractError(
                "strict parent protocol does not join the authoritative D6 "
                "selection-terminal binding"
            )
        bodies = ConfirmationDesignBodySet.from_protocol(protocol)
        observed = {
            "graph_axes_sha256": bodies.graph_axes_sha256,
            "required_cells_manifest_sha256": (bodies.required_cells_sha256),
            "required_stress_strata_sha256": (bodies.required_stress_sha256),
            "locked_thresholds_sha256": bodies.thresholds_sha256,
            "locked_aggregation_sha256": bodies.aggregation_sha256,
            "selection_implementation_registry_sha256": (
                canonical_json_sha256(protocol.implementation_registry.to_dict())
            ),
        }
        terminal_expected = {
            "graph_axes_sha256": terminal.graph_axes_sha256,
            "required_cells_manifest_sha256": (terminal.required_cells_manifest_sha256),
            "required_stress_strata_sha256": (terminal.required_stress_strata_sha256),
            "locked_thresholds_sha256": terminal.locked_thresholds_sha256,
            "locked_aggregation_sha256": terminal.locked_aggregation_sha256,
            "selection_implementation_registry_sha256": (
                terminal.selection_implementation_registry_sha256
            ),
        }
        admission_expected = {
            "graph_axes_sha256": admission.required_graph_axes_sha256,
            "required_cells_manifest_sha256": (
                admission.required_cells_manifest_sha256
            ),
            "required_stress_strata_sha256": (admission.required_stress_strata_sha256),
            "locked_thresholds_sha256": admission.locked_thresholds_sha256,
            "locked_aggregation_sha256": admission.locked_aggregation_sha256,
            "selection_implementation_registry_sha256": (
                admission.selection_implementation_registry_sha256
            ),
        }
        if observed != terminal_expected or observed != admission_expected:
            raise QualificationContractError(
                "full parent design bodies do not reconstruct every D6 hash"
            )
        return cls(
            _factory_token=_D7_PARENT_PROTOCOL_BINDING_FACTORY_TOKEN,
            protocol_id=protocol.protocol_id,
            protocol_source_sha256=parent.source_sha256,
            protocol_canonical_sha256=parent.canonical_sha256,
            selection_seed_count=len(protocol.selection.seeds),
            **observed,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "protocol_id": self.protocol_id,
            "protocol_source_sha256": self.protocol_source_sha256,
            "protocol_canonical_sha256": self.protocol_canonical_sha256,
            "graph_axes_sha256": self.graph_axes_sha256,
            "required_cells_manifest_sha256": (self.required_cells_manifest_sha256),
            "required_stress_strata_sha256": (self.required_stress_strata_sha256),
            "locked_thresholds_sha256": self.locked_thresholds_sha256,
            "locked_aggregation_sha256": (self.locked_aggregation_sha256),
            "selection_implementation_registry_sha256": (
                self.selection_implementation_registry_sha256
            ),
            "selection_seed_count": self.selection_seed_count,
            "full_parent_protocol_bytes_loaded": True,
            "historical_terminal_companions_verified_upstream": True,
            "terminal_result_bytes_direct_design_argument": False,
            "terminal_manifest_bytes_direct_design_argument": False,
            "terminal_consumption_bytes_direct_design_argument": False,
            "terminal_result_bytes_retained_by_design": False,
            "terminal_manifest_bytes_retained_by_design": False,
            "terminal_consumption_bytes_retained_by_design": False,
        }


@dataclass(frozen=True, slots=True)
class D7ConfirmationSeedPolicy:
    """Seed slots and chronology only; no concrete seed is accepted."""

    schema_version: ClassVar[str] = "spirallens.d7-confirmation-seed-policy.v0.1"
    seed_slot_ids: ClassVar[tuple[str, str]] = D7_CONFIRMATION_SEED_SLOT_IDS

    @property
    def development_exclusion_registry_sha256(self) -> str:
        return canonical_json_sha256(
            {
                "schema_version": ("spirallens.d7-development-seed-exclusion.v0.1"),
                "entries": [
                    {"seed": seed, "reason": reason}
                    for seed, reason in _DEVELOPMENT_SEED_EXCLUSION_ENTRIES
                ],
            }
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "seed_slot_ids": list(self.seed_slot_ids),
            "required_seed_count": 2,
            "concrete_seed_inventory_present": False,
            "seed_values_are_nonnegative_signed_int64": True,
            "seed_values_must_be_unique_and_canonically_sorted": True,
            "seed_supplier_must_follow_seed_free_source_readiness": True,
            "development_exclusion_registry_sha256": (
                self.development_exclusion_registry_sha256
            ),
            "parent_selection_seeds_must_be_excluded": True,
            "unseen_status": "external-attestation-required",
            "cryptographic_unseen_proof": False,
            "seed_inventory_frozen": False,
        }


@dataclass(frozen=True, slots=True)
class D7ConfirmationStressTranslation:
    """Exact parent stress values translated onto the spectral construction."""

    stress_axes: tuple[StressAxis, ...]
    structured_observation_perturbation_levels: tuple[NumericStressLevel, ...]
    state_geometry_warp_levels: tuple[NumericStressLevel, ...]
    primary_boundaries: tuple[BoundaryTemplate, ...]
    offcore_boundary: BoundaryTemplate
    locked_radius_graph_value: float

    schema_version: ClassVar[str] = D7_CONFIRMATION_STRESS_TRANSLATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if tuple(axis.axis_id for axis in self.stress_axes) != (
            "boundary",
            "state-geometry-warp",
            "structured-observation-perturbation",
        ):
            raise QualificationContractError(
                "D7 stress axes differ from the exact D6 axis order"
            )
        if tuple(item.to_dict() for item in self.state_geometry_warp_levels) != (
            {"level": "nominal", "value": 0.0},
            {"level": "stressed", "value": 0.1},
        ):
            raise QualificationContractError(
                "D7 state geometry warp levels differ from D6"
            )
        if tuple(
            item.to_dict() for item in self.structured_observation_perturbation_levels
        ) != (
            {"level": "nominal", "value": 0.0},
            {"level": "stressed", "value": 0.01},
        ):
            raise QualificationContractError(
                "D7 observation perturbation levels differ from D6"
            )
        if tuple(item.to_dict() for item in self.primary_boundaries) != (
            {
                "level": "central",
                "x_min": 2,
                "y_min": 2,
                "x_max": 4,
                "y_max": 4,
            },
            {
                "level": "wide",
                "x_min": 1,
                "y_min": 1,
                "x_max": 5,
                "y_max": 5,
            },
        ):
            raise QualificationContractError("D7 primary boundaries differ from D6")
        if self.offcore_boundary.to_dict() != {
            "level": "offcore",
            "x_min": 0,
            "y_min": 0,
            "x_max": 1,
            "y_max": 1,
        }:
            raise QualificationContractError("D7 offcore boundary differs from D6")
        if self.locked_radius_graph_value != 0.48:
            raise QualificationContractError(
                "D7 locked radius graph value differs from D6"
            )

    @classmethod
    def from_parent(
        cls,
        parent: LoadedQualificationProtocol,
    ) -> D7ConfirmationStressTranslation:
        protocol = _loaded_parent(parent).protocol
        cartesian = protocol.cartesian
        radius_values = tuple(
            float(dict(item.parameters)["radius"])
            for item in (
                *protocol.graphs.field_estimation,
                *protocol.graphs.cycle_construction,
            )
            if item.graph_id in {"a-radius", "b-radius"}
        )
        if radius_values != (0.48, 0.48):
            raise QualificationContractError(
                "parent radius graph declarations differ from D7 translation"
            )
        return cls(
            stress_axes=protocol.selection.stress_axes,
            structured_observation_perturbation_levels=(
                cartesian.structured_observation_perturbation_levels
            ),
            state_geometry_warp_levels=(cartesian.state_geometry_warp_levels),
            primary_boundaries=cartesian.primary_boundaries,
            offcore_boundary=cartesian.offcore_boundary,
            locked_radius_graph_value=radius_values[0],
        )

    def to_dict(self) -> dict[str, object]:
        conformance = []
        for level in self.state_geometry_warp_levels:
            receipt = spectral_moment_state_geometry_conformance(level.value)
            maximum = float(receipt["maximum_axis_adjacent_distance"])
            conformance.append(
                {
                    **receipt,
                    "stress_level": level.level,
                    "locked_radius_graph_value": (self.locked_radius_graph_value),
                    "adjacent_distance_margin_below_locked_radius": (
                        self.locked_radius_graph_value - maximum
                    ),
                    "axis_adjacent_distance_below_locked_radius": (
                        maximum < self.locked_radius_graph_value
                    ),
                }
            )
        return {
            "schema_version": self.schema_version,
            "translation_id": SPECTRAL_MOMENT_STRESS_TRANSLATION_ID,
            "stress_axes": [item.to_dict() for item in self.stress_axes],
            "state_geometry_warp": {
                "levels": [item.to_dict() for item in self.state_geometry_warp_levels],
                "formula": "q-plus-w-sin-pi-q-over-pi",
                "changes_states": True,
                "changes_site_coordinates": False,
                "changes_oracle_field": False,
            },
            "structured_observation_perturbation": {
                "levels": [
                    item.to_dict()
                    for item in self.structured_observation_perturbation_levels
                ],
                "formula": ("a-cos-sqrt-two-alpha-plus-row-seed-phase-37-1009"),
                "reuses_d6_nuisance_operator": True,
                "changes_fit_and_evaluation_values": True,
                "changes_states": False,
                "changes_oracle_field": False,
                "prerequisite_requested_assignment_retained": True,
                "prerequisite_effective_scale_zero": True,
            },
            "boundary": {
                "primary": [item.to_dict() for item in self.primary_boundaries],
                "offcore": self.offcore_boundary.to_dict(),
                "changes_generator_inputs": False,
                "selects_matched_cycle_support": True,
            },
            "state_normalization": {
                "normalization_id": (SPECTRAL_MOMENT_STATE_NORMALIZATION_ID),
                "scale": SPECTRAL_MOMENT_STATE_NORMALIZATION_SCALE,
                "rule": "one-over-square-root-of-ambient-dimension",
                "ambient_dimension": SPECTRAL_MOMENT_AMBIENT_DIMENSION,
                "development_result_tuned_threshold": False,
                "seed_free_distance_conformance": conformance,
            },
            "grid_side": SPECTRAL_MOMENT_GRID_SIDE,
            "samples_per_split": SPECTRAL_MOMENT_SAMPLES_PER_SPLIT,
            "stress_translation_implemented": True,
            "stress_translation_frozen": False,
        }

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


@dataclass(frozen=True, slots=True)
class D7PrimaryUnitTemplate:
    primary_unit_id: str
    seed_slot_id: str
    parent_control_id: str
    case_id: str
    case_semantics: str
    core_disposition: CoreDisposition
    loop_disposition: LoopDisposition
    stress_assignments: tuple[StressAssignment, ...]

    def __post_init__(self) -> None:
        require_slug(self.primary_unit_id, label="primary_unit_id")
        if self.seed_slot_id not in D7_CONFIRMATION_SEED_SLOT_IDS:
            raise QualificationContractError("primary unit has an unknown seed slot")
        require_slug(self.parent_control_id, label="parent_control_id")
        expected = _case_by_semantic().get(self.case_semantics)
        if (
            expected is None
            or expected[0] != self.case_id
            or expected[3] != self.core_disposition.value
            or expected[4] != self.loop_disposition.value
        ):
            raise QualificationContractError(
                "primary unit case metadata differs from the spectral registry"
            )
        if len(self.stress_assignments) != 3:
            raise QualificationContractError(
                "primary unit requires exactly three stress assignments"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "primary_unit_id": self.primary_unit_id,
            "seed_slot_id": self.seed_slot_id,
            "parent_control_id": self.parent_control_id,
            "case_id": self.case_id,
            "case_semantics": self.case_semantics,
            "core_disposition": self.core_disposition.value,
            "loop_disposition": self.loop_disposition.value,
            "stress_assignments": _stress_dict(self.stress_assignments),
        }


@dataclass(frozen=True, slots=True)
class D7CoreCellTemplate:
    core_cell_id: str
    primary_unit_id: str
    field_graph_id: str
    expected_core_disposition: CoreDisposition

    def __post_init__(self) -> None:
        require_slug(self.core_cell_id, label="core_cell_id")
        require_slug(self.primary_unit_id, label="primary_unit_id")
        require_slug(self.field_graph_id, label="field_graph_id")
        if not isinstance(
            self.expected_core_disposition,
            CoreDisposition,
        ):
            raise TypeError("expected_core_disposition must be CoreDisposition")

    def to_dict(self) -> dict[str, object]:
        return {
            "core_cell_id": self.core_cell_id,
            "primary_unit_id": self.primary_unit_id,
            "field_graph_id": self.field_graph_id,
            "expected_core_disposition": (self.expected_core_disposition.value),
        }


@dataclass(frozen=True, slots=True)
class D7LoopCellTemplate:
    loop_cell_id: str
    primary_unit_id: str
    field_graph_id: str
    cycle_graph_id: str
    loop_role: LoopRole
    expected_loop_disposition: LoopDisposition

    def __post_init__(self) -> None:
        for name in (
            "loop_cell_id",
            "primary_unit_id",
            "field_graph_id",
            "cycle_graph_id",
        ):
            require_slug(getattr(self, name), label=name)
        if not isinstance(self.loop_role, LoopRole):
            raise TypeError("loop_role must be LoopRole")
        if not isinstance(
            self.expected_loop_disposition,
            LoopDisposition,
        ):
            raise TypeError("expected_loop_disposition must be LoopDisposition")

    def to_dict(self) -> dict[str, object]:
        return {
            "loop_cell_id": self.loop_cell_id,
            "primary_unit_id": self.primary_unit_id,
            "field_graph_id": self.field_graph_id,
            "cycle_graph_id": self.cycle_graph_id,
            "loop_role": self.loop_role.value,
            "expected_loop_disposition": (self.expected_loop_disposition.value),
        }


@dataclass(frozen=True, slots=True)
class D7ExpectedStratumTemplate:
    stratum_id: str
    primary_unit_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        require_slug(self.stratum_id, label="stratum_id")
        if len(self.primary_unit_ids) != 32 or self.primary_unit_ids != tuple(
            sorted(set(self.primary_unit_ids))
        ):
            raise QualificationContractError(
                "each D7 stress stratum requires 32 canonical primary units"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "stratum_id": self.stratum_id,
            "evaluation_unit": "phantom_instance",
            "required": True,
            "primary_unit_ids": list(self.primary_unit_ids),
        }


@dataclass(frozen=True, slots=True)
class D7ConfirmationExecutionInventoryTemplate:
    primary_units: tuple[D7PrimaryUnitTemplate, ...]
    core_cells: tuple[D7CoreCellTemplate, ...]
    loop_cells: tuple[D7LoopCellTemplate, ...]
    expected_strata: tuple[D7ExpectedStratumTemplate, ...]

    schema_version: ClassVar[str] = D7_CONFIRMATION_INVENTORY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            len(self.primary_units) != D7_CONFIRMATION_PRIMARY_UNIT_COUNT
            or len(self.core_cells) != D7_CONFIRMATION_CORE_CELL_COUNT
            or len(self.loop_cells) != D7_CONFIRMATION_LOOP_CELL_COUNT
            or len(self.expected_strata) != 6
        ):
            raise QualificationContractError(
                "D7 inventory differs from 64/192/1152/six-strata"
            )
        for values, attribute in (
            (self.primary_units, "primary_unit_id"),
            (self.core_cells, "core_cell_id"),
            (self.loop_cells, "loop_cell_id"),
            (self.expected_strata, "stratum_id"),
        ):
            identifiers = tuple(getattr(item, attribute) for item in values)
            if identifiers != tuple(sorted(set(identifiers))):
                raise QualificationContractError(
                    f"{attribute} values must be unique and canonical"
                )
        primary = {item.primary_unit_id: item for item in self.primary_units}
        core_by_primary: dict[str, list[D7CoreCellTemplate]] = {
            key: [] for key in primary
        }
        loop_by_primary: dict[str, list[D7LoopCellTemplate]] = {
            key: [] for key in primary
        }
        for cell in self.core_cells:
            if cell.primary_unit_id not in primary:
                raise QualificationContractError(
                    "core cell does not join a primary unit"
                )
            core_by_primary[cell.primary_unit_id].append(cell)
            if (
                cell.expected_core_disposition
                is not primary[cell.primary_unit_id].core_disposition
            ):
                raise QualificationContractError(
                    "core cell disposition differs from its primary unit"
                )
        for cell in self.loop_cells:
            if cell.primary_unit_id not in primary:
                raise QualificationContractError(
                    "loop cell does not join a primary unit"
                )
            loop_by_primary[cell.primary_unit_id].append(cell)
        for primary_id, unit in primary.items():
            core = core_by_primary[primary_id]
            loops = loop_by_primary[primary_id]
            if (
                len(core) != 3
                or len({item.field_graph_id for item in core}) != 3
                or len(loops) != 18
                or len(
                    {
                        (
                            item.field_graph_id,
                            item.cycle_graph_id,
                            item.loop_role,
                        )
                        for item in loops
                    }
                )
                != 18
            ):
                raise QualificationContractError(
                    "each D7 primary requires exact 3A core and "
                    "3A-by-3B-by-2-role loop cells"
                )
            for loop in loops:
                expected = (
                    unit.loop_disposition
                    if loop.loop_role is LoopRole.PRIMARY_BOUNDARY
                    else (
                        LoopDisposition.PREREQUISITE_FAILURE
                        if unit.loop_disposition is LoopDisposition.PREREQUISITE_FAILURE
                        else LoopDisposition.NULL
                    )
                )
                if loop.expected_loop_disposition is not expected:
                    raise QualificationContractError(
                        "loop role disposition differs from its primary unit"
                    )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "primary_units": [item.to_dict() for item in self.primary_units],
            "core_cells": [item.to_dict() for item in self.core_cells],
            "loop_cells": [item.to_dict() for item in self.loop_cells],
            "expected_strata": [item.to_dict() for item in self.expected_strata],
            "counts": {
                "seed_slots": 2,
                "cases": 4,
                "stress_variants_per_seed_case": 8,
                "primary_units": 64,
                "core_cells": 192,
                "loop_cells": 1152,
                "event_lanes": 1344,
                "d2_boundary_collapsed_scientific_units": 32,
                "d2_boundary_collapsed_evaluable_units": 24,
                "d2_boundary_collapsed_prerequisite_units": 8,
                "d4_d5_scientific_execution_units": 64,
                "nonprerequisite_primary_denominator": 48,
                "prerequisite_primary_units": 16,
            },
            "repeated_measures": {
                "core_graphs": True,
                "graph_pairs": True,
                "loop_roles": True,
                "stress_variants": True,
                "seed_blocks_proved_independent": False,
                "event_lanes_are_iid_samples": False,
            },
            "concrete_seed_inventory_present": False,
            "execution_inventory_frozen": False,
        }

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


def _inventory_template(
    parent: LoadedQualificationProtocol,
    stress: D7ConfirmationStressTranslation,
) -> D7ConfirmationExecutionInventoryTemplate:
    protocol = _loaded_parent(parent).protocol
    cases = _case_by_semantic()
    primary_units: list[D7PrimaryUnitTemplate] = []
    core_cells: list[D7CoreCellTemplate] = []
    loop_cells: list[D7LoopCellTemplate] = []
    memberships: dict[str, set[str]] = {
        required_stress_stratum_id(axis.axis_id, level): set()
        for axis in stress.stress_axes
        for level in axis.levels
    }
    for (
        slot_index,
        control,
        boundary,
        warp,
        perturbation,
    ) in product(
        range(2),
        protocol.selection.controls,
        stress.stress_axes[0].levels,
        stress.stress_axes[1].levels,
        stress.stress_axes[2].levels,
    ):
        slot_id = D7_CONFIRMATION_SEED_SLOT_IDS[slot_index]
        slot_short = f"s{slot_index:02d}"
        semantics = _semantic_label(
            control.core_disposition,
            control.loop_disposition,
        )
        case = cases[semantics]
        primary_id = (
            f"d7-unit-{slot_short}-{control.control_id}-b-{boundary}-"
            f"sgw-{warp}-sop-{perturbation}"
        )
        assignments = (
            StressAssignment("boundary", boundary),
            StressAssignment("state-geometry-warp", warp),
            StressAssignment(
                "structured-observation-perturbation",
                perturbation,
            ),
        )
        unit = D7PrimaryUnitTemplate(
            primary_unit_id=primary_id,
            seed_slot_id=slot_id,
            parent_control_id=control.control_id,
            case_id=case[0],
            case_semantics=semantics,
            core_disposition=control.core_disposition,
            loop_disposition=control.loop_disposition,
            stress_assignments=assignments,
        )
        primary_units.append(unit)
        for assignment in assignments:
            memberships[
                required_stress_stratum_id(
                    assignment.axis_id,
                    assignment.level,
                )
            ].add(primary_id)
        for field_graph in protocol.graphs.field_estimation:
            core_cells.append(
                D7CoreCellTemplate(
                    core_cell_id=(f"core-{primary_id}-{field_graph.graph_id}"),
                    primary_unit_id=primary_id,
                    field_graph_id=field_graph.graph_id,
                    expected_core_disposition=(control.core_disposition),
                )
            )
            for cycle_graph in protocol.graphs.cycle_construction:
                for role in LoopRole:
                    expected = (
                        control.loop_disposition
                        if role is LoopRole.PRIMARY_BOUNDARY
                        else (
                            LoopDisposition.PREREQUISITE_FAILURE
                            if control.loop_disposition
                            is LoopDisposition.PREREQUISITE_FAILURE
                            else LoopDisposition.NULL
                        )
                    )
                    loop_cells.append(
                        D7LoopCellTemplate(
                            loop_cell_id=(
                                f"loop-{primary_id}-"
                                f"{field_graph.graph_id}-"
                                f"{cycle_graph.graph_id}-{role.value}"
                            ),
                            primary_unit_id=primary_id,
                            field_graph_id=field_graph.graph_id,
                            cycle_graph_id=cycle_graph.graph_id,
                            loop_role=role,
                            expected_loop_disposition=expected,
                        )
                    )
    return D7ConfirmationExecutionInventoryTemplate(
        primary_units=tuple(
            sorted(
                primary_units,
                key=lambda item: item.primary_unit_id,
            )
        ),
        core_cells=tuple(sorted(core_cells, key=lambda item: item.core_cell_id)),
        loop_cells=tuple(sorted(loop_cells, key=lambda item: item.loop_cell_id)),
        expected_strata=tuple(
            D7ExpectedStratumTemplate(
                stratum_id=stratum_id,
                primary_unit_ids=tuple(sorted(primary_ids)),
            )
            for stratum_id, primary_ids in sorted(memberships.items())
        ),
    )


def _unit_projection(
    *,
    seed_slot_id: str,
    case_semantics: str,
    stress_assignments: tuple[StressAssignment, ...],
) -> dict[str, object]:
    return {
        "seed_slot_id": seed_slot_id,
        "case_semantics": case_semantics,
        "stress_assignments": _stress_dict(stress_assignments),
    }


def _unit_projection_sha256(value: dict[str, object]) -> str:
    return canonical_json_sha256(value)


def _parent_structural_projection(
    parent: LoadedQualificationProtocol,
) -> dict[str, object]:
    protocol = _loaded_parent(parent).protocol
    seeds = tuple(protocol.selection.seeds)
    if len(seeds) != 2:
        raise QualificationContractError(
            "parent projection requires exactly two selection seeds"
        )
    seed_slots = {
        seed: D7_CONFIRMATION_SEED_SLOT_IDS[index] for index, seed in enumerate(seeds)
    }
    controls = {
        control.control_id: _semantic_label(
            control.core_disposition,
            control.loop_disposition,
        )
        for control in protocol.selection.controls
    }
    primary_meta: dict[str, dict[str, object]] = {}
    core_records: list[dict[str, object]] = []
    for cell in protocol.expected_core_cells:
        unit = _unit_projection(
            seed_slot_id=seed_slots[cell.selection_seed],
            case_semantics=controls[cell.control_id],
            stress_assignments=cell.stress_assignments,
        )
        prior = primary_meta.setdefault(cell.primary_unit_id, unit)
        if prior != unit:
            raise QualificationContractError(
                "parent core cells disagree on primary structure"
            )
        core_records.append(
            {
                **unit,
                "field_graph_id": cell.field_graph_id,
                "expected_core_disposition": (cell.expected_core_disposition.value),
            }
        )
    loop_records: list[dict[str, object]] = []
    for cell in protocol.expected_cells:
        unit = _unit_projection(
            seed_slot_id=seed_slots[cell.selection_seed],
            case_semantics=controls[cell.control_id],
            stress_assignments=cell.stress_assignments,
        )
        if primary_meta.get(cell.primary_unit_id) != unit:
            raise QualificationContractError(
                "parent core/loop cells disagree on primary structure"
            )
        loop_records.append(
            {
                **unit,
                "field_graph_id": cell.field_graph_id,
                "cycle_graph_id": cell.cycle_graph_id,
                "loop_role": cell.loop_role.value,
                "expected_loop_disposition": (cell.expected_loop_disposition.value),
            }
        )
    projected_by_parent_id = {
        primary_id: _unit_projection_sha256(unit)
        for primary_id, unit in primary_meta.items()
    }
    strata = [
        {
            "stratum_id": item.stratum_id,
            "evaluation_unit": item.evaluation_unit.value,
            "required": item.required,
            "projected_primary_units": sorted(
                projected_by_parent_id[primary_id]
                for primary_id in item.primary_unit_ids
            ),
        }
        for item in protocol.expected_strata
    ]
    return {
        "schema_version": D7_STRUCTURAL_PROJECTION_SCHEMA_VERSION,
        "seed_slot_count": 2,
        "stress_axes": [item.to_dict() for item in protocol.selection.stress_axes],
        "primary_units": _sorted_records(list(primary_meta.values())),
        "core_cells": _sorted_records(core_records),
        "loop_cells": _sorted_records(loop_records),
        "expected_strata": _sorted_records(strata),
    }


def _confirmation_structural_projection(
    inventory: D7ConfirmationExecutionInventoryTemplate,
    stress: D7ConfirmationStressTranslation,
) -> dict[str, object]:
    primary_meta = {
        item.primary_unit_id: _unit_projection(
            seed_slot_id=item.seed_slot_id,
            case_semantics=item.case_semantics,
            stress_assignments=item.stress_assignments,
        )
        for item in inventory.primary_units
    }
    primary_by_id = {item.primary_unit_id: item for item in inventory.primary_units}
    core_records = [
        {
            **primary_meta[cell.primary_unit_id],
            "field_graph_id": cell.field_graph_id,
            "expected_core_disposition": (cell.expected_core_disposition.value),
        }
        for cell in inventory.core_cells
    ]
    loop_records = [
        {
            **primary_meta[cell.primary_unit_id],
            "field_graph_id": cell.field_graph_id,
            "cycle_graph_id": cell.cycle_graph_id,
            "loop_role": cell.loop_role.value,
            "expected_loop_disposition": (cell.expected_loop_disposition.value),
        }
        for cell in inventory.loop_cells
    ]
    projected_by_id = {
        primary_id: _unit_projection_sha256(unit)
        for primary_id, unit in primary_meta.items()
    }
    strata = [
        {
            "stratum_id": item.stratum_id,
            "evaluation_unit": "phantom_instance",
            "required": True,
            "projected_primary_units": sorted(
                projected_by_id[primary_id] for primary_id in item.primary_unit_ids
            ),
        }
        for item in inventory.expected_strata
    ]
    if set(primary_by_id) != set(primary_meta):
        raise AssertionError("confirmation primary projection is incomplete")
    return {
        "schema_version": D7_STRUCTURAL_PROJECTION_SCHEMA_VERSION,
        "seed_slot_count": 2,
        "stress_axes": [item.to_dict() for item in stress.stress_axes],
        "primary_units": _sorted_records(list(primary_meta.values())),
        "core_cells": _sorted_records(core_records),
        "loop_cells": _sorted_records(loop_records),
        "expected_strata": _sorted_records(strata),
    }


@dataclass(frozen=True, slots=True)
class D7ParentManifestCompatibility:
    """Separate structural equality from impossible parent byte equality."""

    parent_required_cells_manifest_sha256: str
    parent_required_stress_strata_sha256: str
    confirmation_cells_manifest_sha256: str
    confirmation_stress_strata_sha256: str
    parent_structural_projection_sha256: str
    confirmation_structural_projection_sha256: str

    schema_version: ClassVar[str] = D7_PARENT_MANIFEST_COMPATIBILITY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in (
            "parent_required_cells_manifest_sha256",
            "parent_required_stress_strata_sha256",
            "confirmation_cells_manifest_sha256",
            "confirmation_stress_strata_sha256",
            "parent_structural_projection_sha256",
            "confirmation_structural_projection_sha256",
        ):
            require_sha256(getattr(self, name), label=name)
        if (
            self.parent_required_cells_manifest_sha256
            == self.confirmation_cells_manifest_sha256
            or self.parent_required_stress_strata_sha256
            == self.confirmation_stress_strata_sha256
        ):
            raise QualificationContractError(
                "D7 seed-slot manifests must not claim parent byte identity"
            )
        if (
            self.parent_structural_projection_sha256
            != self.confirmation_structural_projection_sha256
        ):
            raise QualificationContractError(
                "D7 structural projection differs from the D6 parent"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "parent_required_cells_manifest_sha256": (
                self.parent_required_cells_manifest_sha256
            ),
            "parent_required_stress_strata_sha256": (
                self.parent_required_stress_strata_sha256
            ),
            "confirmation_cells_manifest_sha256": (
                self.confirmation_cells_manifest_sha256
            ),
            "confirmation_stress_strata_sha256": (
                self.confirmation_stress_strata_sha256
            ),
            "structural_projection_schema_version": (
                D7_STRUCTURAL_PROJECTION_SCHEMA_VERSION
            ),
            "parent_structural_projection_sha256": (
                self.parent_structural_projection_sha256
            ),
            "confirmation_structural_projection_sha256": (
                self.confirmation_structural_projection_sha256
            ),
            "parent_manifests_contain_selection_specific_identities": True,
            "confirmation_manifests_use_seed_slots_and_spectral_cases": True,
            "exact_parent_cells_manifest_satisfied": False,
            "exact_parent_stress_manifest_satisfied": False,
            "structural_template_match_observed": True,
            "structural_match_is_exact_parent_hash_satisfaction": False,
            "silent_reinterpretation_allowed": False,
            "reviewed_structural_rebinding_amendment_published": False,
            "d6_admission_spec_satisfied": False,
            "resolution_required": "reviewed-successor-admission-contract",
        }


def _manifest_compatibility(
    parent: LoadedQualificationProtocol,
    parent_binding: D7ParentProtocolDesignBinding,
    inventory: D7ConfirmationExecutionInventoryTemplate,
    stress: D7ConfirmationStressTranslation,
) -> D7ParentManifestCompatibility:
    confirmation_cells = {
        "schema_version": ("spirallens.d7-required-confirmation-cells.v0.1"),
        "core_cells": [item.to_dict() for item in inventory.core_cells],
        "loop_cells": [item.to_dict() for item in inventory.loop_cells],
    }
    confirmation_stress = {
        "schema_version": ("spirallens.d7-required-confirmation-stress.v0.1"),
        "stress_axes": [item.to_dict() for item in stress.stress_axes],
        "expected_strata": [item.to_dict() for item in inventory.expected_strata],
    }
    parent_projection = _parent_structural_projection(parent)
    confirmation_projection = _confirmation_structural_projection(
        inventory,
        stress,
    )
    if parent_projection != confirmation_projection:
        raise QualificationContractError(
            "confirmation inventory is not structurally isomorphic to D6"
        )
    return D7ParentManifestCompatibility(
        parent_required_cells_manifest_sha256=(
            parent_binding.required_cells_manifest_sha256
        ),
        parent_required_stress_strata_sha256=(
            parent_binding.required_stress_strata_sha256
        ),
        confirmation_cells_manifest_sha256=canonical_json_sha256(confirmation_cells),
        confirmation_stress_strata_sha256=canonical_json_sha256(confirmation_stress),
        parent_structural_projection_sha256=canonical_json_sha256(parent_projection),
        confirmation_structural_projection_sha256=(
            canonical_json_sha256(confirmation_projection)
        ),
    )


@dataclass(frozen=True, slots=True, init=False)
class D7ConfirmationExecutionDesignDraft:
    """Canonical seed-free execution topology; never a D7 protocol freeze."""

    parent_d6: D7ParentD6Binding
    parent: D7ParentProtocolDesignBinding
    seed_policy: D7ConfirmationSeedPolicy
    graph_axes: GraphAxes
    domain: DomainDeclaration
    thresholds: Thresholds
    coverage_policy: CoveragePolicy
    stress_translation: D7ConfirmationStressTranslation
    inventory: D7ConfirmationExecutionInventoryTemplate
    manifest_compatibility: D7ParentManifestCompatibility

    schema_version: ClassVar[str] = D7_CONFIRMATION_EXECUTION_DRAFT_SCHEMA_VERSION
    draft_id: ClassVar[str] = "d7-spectral-moment-seed-free-execution-design-v0-1"
    status: ClassVar[str] = "seed-free-execution-design-not-frozen"
    claim_ceiling: ClassVar[str] = "level_0"

    def __init__(
        self,
        *,
        _factory_token: object = None,
        parent_d6: D7ParentD6Binding,
        parent: D7ParentProtocolDesignBinding,
        seed_policy: D7ConfirmationSeedPolicy,
        graph_axes: GraphAxes,
        domain: DomainDeclaration,
        thresholds: Thresholds,
        coverage_policy: CoveragePolicy,
        stress_translation: D7ConfirmationStressTranslation,
        inventory: D7ConfirmationExecutionInventoryTemplate,
        manifest_compatibility: D7ParentManifestCompatibility,
    ) -> None:
        if _factory_token is not (_D7_CONFIRMATION_EXECUTION_DESIGN_FACTORY_TOKEN):
            raise QualificationContractError(
                "D7ConfirmationExecutionDesignDraft must be produced by "
                "build_seed_free_d7_confirmation_execution_design or its "
                "strict canonical loader"
            )
        for name, value in (
            ("parent_d6", parent_d6),
            ("parent", parent),
            ("seed_policy", seed_policy),
            ("graph_axes", graph_axes),
            ("domain", domain),
            ("thresholds", thresholds),
            ("coverage_policy", coverage_policy),
            ("stress_translation", stress_translation),
            ("inventory", inventory),
            ("manifest_compatibility", manifest_compatibility),
        ):
            object.__setattr__(self, name, value)
        self.__post_init__()

    def __post_init__(self) -> None:
        if not isinstance(self.parent_d6, D7ParentD6Binding):
            raise TypeError("parent_d6 must be D7ParentD6Binding")
        if not isinstance(
            self.parent,
            D7ParentProtocolDesignBinding,
        ):
            raise TypeError("parent must be D7ParentProtocolDesignBinding")
        parent_d6_hashes = (
            self.parent_d6.required_graph_axes_sha256,
            self.parent_d6.required_cells_manifest_sha256,
            self.parent_d6.required_stress_strata_sha256,
            self.parent_d6.locked_thresholds_sha256,
            self.parent_d6.locked_aggregation_sha256,
            self.parent_d6.selection_implementation_registry_sha256,
        )
        protocol_hashes = (
            self.parent.graph_axes_sha256,
            self.parent.required_cells_manifest_sha256,
            self.parent.required_stress_strata_sha256,
            self.parent.locked_thresholds_sha256,
            self.parent.locked_aggregation_sha256,
            self.parent.selection_implementation_registry_sha256,
        )
        if parent_d6_hashes != protocol_hashes:
            raise QualificationContractError(
                "authoritative D6 identity does not bind the reconstructed "
                "parent protocol bodies"
            )
        if not isinstance(self.seed_policy, D7ConfirmationSeedPolicy):
            raise TypeError("seed_policy must be D7ConfirmationSeedPolicy")
        if canonical_json_sha256(self.graph_axes.to_dict()) != (
            self.parent.graph_axes_sha256
        ):
            raise QualificationContractError(
                "D7 graph axes differ from the exact parent bytes"
            )
        if canonical_json_sha256(self.thresholds.to_dict()) != (
            self.parent.locked_thresholds_sha256
        ):
            raise QualificationContractError(
                "D7 thresholds differ from the exact parent bytes"
            )
        if not isinstance(
            self.stress_translation,
            D7ConfirmationStressTranslation,
        ):
            raise TypeError(
                "stress_translation must be D7ConfirmationStressTranslation"
            )
        if not isinstance(
            self.inventory,
            D7ConfirmationExecutionInventoryTemplate,
        ):
            raise TypeError(
                "inventory must be D7ConfirmationExecutionInventoryTemplate"
            )
        if not isinstance(
            self.manifest_compatibility,
            D7ParentManifestCompatibility,
        ):
            raise TypeError(
                "manifest_compatibility must be D7ParentManifestCompatibility"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "draft_id": self.draft_id,
            "status": self.status,
            "claim_ceiling": self.claim_ceiling,
            "parent_d6": self.parent_d6.to_dict(),
            "parent": self.parent.to_dict(),
            "seed_policy": self.seed_policy.to_dict(),
            "confirmation_family": {
                "generator_family_id": (SPECTRAL_MOMENT_GENERATOR_FAMILY_ID),
                "family_admitted": False,
                "construction_diversity_reviewed": False,
                "committed_source_closure_verified": False,
            },
            "locked_parent_interface": {
                "graph_axes": self.graph_axes.to_dict(),
                "domain": self.domain.to_dict(),
                "thresholds": self.thresholds.to_dict(),
                "coverage_policy": self.coverage_policy.to_dict(),
                "graph_axes_byte_identity_verified": True,
                "thresholds_byte_identity_verified": True,
                "parent_aggregation_application_rebinding_reviewed": False,
                "selection_implementation_registry_reused_as_d7_registry": (False),
            },
            "stress_translation": self.stress_translation.to_dict(),
            "inventory": self.inventory.to_dict(),
            "manifest_compatibility": (self.manifest_compatibility.to_dict()),
            "implementation_status": {
                "seed_free_inventory_implemented": True,
                "boundary_translation_implemented": True,
                "state_geometry_warp_translation_implemented": True,
                "structured_observation_perturbation_implemented": True,
                "offcore_loop_control_implemented": True,
                "all_graph_pairs_and_loop_roles_implemented": True,
                "oracle_truth_record_free_blind_kernels_implemented": True,
                "core_and_loop_same_primary_support_join_implemented": True,
                "concrete_seed_inventory_frozen": False,
                "source_readiness_receipt_present": False,
                "launch_intent_present": False,
                "exclusive_attempt_claim_present": False,
                "output_namespace_absence_verified": False,
                "terminal_result_and_failure_schemas_present": False,
                "atomic_terminal_writer_present": False,
                "canonical_full_design_artifact_published": False,
                "pre_access_design_freeze_receipt_issued": False,
            },
            "d7_state": "not_run",
            "d8_state": "not_run",
            "authority": dict(sorted(_AUTHORITY.items())),
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_canonical_bytes(
        cls,
        source: bytes,
        *,
        expected_sha256: str,
        loaded_d6: LoadedScopeLimitedD6Decision,
        parent_protocol: LoadedQualificationProtocol,
    ) -> D7ConfirmationExecutionDesignDraft:
        expected = require_sha256(
            expected_sha256,
            label="expected_sha256",
        )
        if (
            not isinstance(source, bytes)
            or not source
            or len(source) > MAX_D7_CONFIRMATION_EXECUTION_DRAFT_BYTES
        ):
            raise QualificationContractError(
                "D7 execution draft must be nonempty bytes within the cap"
            )
        if sha256_bytes(source) != expected:
            raise QualificationContractError(
                "D7 execution draft source SHA-256 differs"
            )
        try:
            document = parse_canonical_json(
                source,
                label="D7 confirmation execution draft",
            )
        except CanonicalJsonError as error:
            raise QualificationContractError(str(error)) from error
        rebuilt = build_seed_free_d7_confirmation_execution_design(
            loaded_d6=loaded_d6,
            parent_protocol=parent_protocol,
        )
        if document != rebuilt.to_dict() or source != rebuilt.canonical_bytes:
            raise QualificationContractError(
                "D7 execution draft differs from authoritative reconstruction"
            )
        return rebuilt


def build_seed_free_d7_confirmation_execution_design(
    *,
    loaded_d6: LoadedScopeLimitedD6Decision,
    parent_protocol: LoadedQualificationProtocol,
) -> D7ConfirmationExecutionDesignDraft:
    """Build the exact seed-slot execution topology from authoritative inputs."""

    parent = _loaded_parent(parent_protocol)
    parent_binding = D7ParentProtocolDesignBinding.from_loaded(
        _loaded_d6(loaded_d6),
        parent,
    )
    parent_d6 = D7ParentD6Binding.from_loaded(loaded_d6)
    stress = D7ConfirmationStressTranslation.from_parent(parent)
    inventory = _inventory_template(parent, stress)
    compatibility = _manifest_compatibility(
        parent,
        parent_binding,
        inventory,
        stress,
    )
    protocol = parent.protocol
    return D7ConfirmationExecutionDesignDraft(
        _factory_token=_D7_CONFIRMATION_EXECUTION_DESIGN_FACTORY_TOKEN,
        parent_d6=parent_d6,
        parent=parent_binding,
        seed_policy=D7ConfirmationSeedPolicy(),
        graph_axes=protocol.graphs,
        domain=protocol.domain,
        thresholds=protocol.thresholds,
        coverage_policy=protocol.coverage_policy,
        stress_translation=stress,
        inventory=inventory,
        manifest_compatibility=compatibility,
    )


__all__ = [
    "D7_CONFIRMATION_CORE_CELL_COUNT",
    "D7_CONFIRMATION_DEVELOPMENT_SEEDS",
    "D7_CONFIRMATION_EVENT_LANE_COUNT",
    "D7_CONFIRMATION_EXECUTION_DRAFT_SCHEMA_VERSION",
    "D7_CONFIRMATION_INVENTORY_SCHEMA_VERSION",
    "D7_CONFIRMATION_LOOP_CELL_COUNT",
    "D7_CONFIRMATION_PRIMARY_UNIT_COUNT",
    "D7_CONFIRMATION_SEED_SLOT_IDS",
    "D7_PARENT_MANIFEST_COMPATIBILITY_SCHEMA_VERSION",
    "D7_PARENT_PROTOCOL_DESIGN_BINDING_SCHEMA_VERSION",
    "D7_STRUCTURAL_PROJECTION_SCHEMA_VERSION",
    "MAX_D7_CONFIRMATION_EXECUTION_DRAFT_BYTES",
    "D7ConfirmationExecutionDesignDraft",
    "D7ConfirmationExecutionInventoryTemplate",
    "D7ConfirmationSeedPolicy",
    "D7ConfirmationStressTranslation",
    "D7CoreCellTemplate",
    "D7ExpectedStratumTemplate",
    "D7LoopCellTemplate",
    "D7ParentManifestCompatibility",
    "D7ParentProtocolDesignBinding",
    "D7PrimaryUnitTemplate",
    "build_seed_free_d7_confirmation_execution_design",
    "require_d7_confirmation_development_seed",
]
