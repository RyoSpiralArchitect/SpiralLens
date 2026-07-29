"""Development-only execution of the complete seed-free D7 topology.

The entry point accepts only permanently excluded development seeds.  It
prepares label-free estimator inputs without constructing oracle objects, then
executes the exact A/B graph topology, current development field estimator,
blind core kernel, and continuous sampled-loop kernel.  It stops at sealed
predictions.

This module cannot score a D7 gate, aggregate a qualification result, publish
a terminal artifact, admit a family, or execute an official confirmation
seed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from spirallens.core.canonical import canonical_json_sha256
from spirallens.graphs import BoundaryRefinementRule, GraphInput
from spirallens.synthetic.cartesian_fourier_domain_phantom import (
    CartesianFourierEstimatorInputs,
)
from spirallens.synthetic.cartesian_fourier_estimator import (
    CartesianFourierFieldEstimate,
    estimate_cartesian_fourier_field,
)
from spirallens.synthetic.spectral_moment_confirmation import (
    SpectralMomentConfirmationGenerator,
    SpectralMomentConfirmationSpec,
)

from .blind import SealedCorePrediction
from .common import (
    QualificationContractError,
    require_sha256,
    require_slug,
)
from .confirmation_execution_design import (
    D7ConfirmationExecutionDesignDraft,
    D7PrimaryUnitTemplate,
    require_d7_confirmation_development_seed,
)
from .crossed import (
    CrossedGraphExecution,
    build_crossed_blind_core_input,
    build_crossed_blind_loop_input,
    build_crossed_graph_execution,
    rectangular_grid_support_faces,
)
from .prerequisites import (
    CorePrerequisitePolicy,
    estimate_and_seal_core,
)
from .protocol import BoundaryTemplate, LoopRole, NumericStressLevel
from .winding import (
    LoopPhasePolicy,
    SealedLoopPrediction,
    estimate_and_seal_loop,
)

D7_DEVELOPMENT_PREDICTION_INVENTORY_SCHEMA_VERSION = (
    "spirallens.d7-development-prediction-inventory.v0.1"
)
_D7_DEVELOPMENT_CORE_PREDICTION_FACTORY_TOKEN = object()
_D7_DEVELOPMENT_LOOP_PREDICTION_FACTORY_TOKEN = object()
_D7_DEVELOPMENT_PRIMARY_PREDICTION_FACTORY_TOKEN = object()
_D7_DEVELOPMENT_INVENTORY_FACTORY_TOKEN = object()


def _numeric_level(
    values: tuple[NumericStressLevel, ...],
    *,
    level: str,
) -> float:
    matches = tuple(item.value for item in values if item.level == level)
    if len(matches) != 1:
        raise ValueError("stress level must resolve exactly one numeric value")
    return float(matches[0])


def _assignments(unit: D7PrimaryUnitTemplate) -> dict[str, str]:
    result = {item.axis_id: item.level for item in unit.stress_assignments}
    if set(result) != {
        "boundary",
        "state-geometry-warp",
        "structured-observation-perturbation",
    }:
        raise ValueError("primary unit does not carry the exact stress axes")
    return result


def _primary_boundary(
    design: D7ConfirmationExecutionDesignDraft,
    *,
    level: str,
) -> BoundaryTemplate:
    matches = tuple(
        item
        for item in design.stress_translation.primary_boundaries
        if item.level == level
    )
    if len(matches) != 1:
        raise ValueError("boundary level must resolve exactly one template")
    return matches[0]


def _support_faces(
    template: BoundaryTemplate,
) -> object:
    return rectangular_grid_support_faces(
        grid_side=7,
        x_min=template.x_min,
        y_min=template.y_min,
        x_max=template.x_max,
        y_max=template.y_max,
    )


def _crossed_execution(
    design: D7ConfirmationExecutionDesignDraft,
    *,
    graph_input: GraphInput,
    inputs: CartesianFourierEstimatorInputs,
    template: BoundaryTemplate,
) -> CrossedGraphExecution:
    domain = design.domain
    return build_crossed_graph_execution(
        graph_input=graph_input,
        graph_axes=design.graph_axes,
        oriented_faces=inputs.oriented_faces,
        support_face_indices=_support_faces(template),
        domain_id=domain.domain_id,
        cycle_class_spec_id=domain.boundary_class_id,
        matched_set_id=domain.support_id,
        refinement_rule=BoundaryRefinementRule(
            rule_id=domain.refinement_rule_id,
            max_domain_edges_per_graph_edge=(domain.max_domain_edges_per_graph_edge),
        ),
    )


def _policies(
    design: D7ConfirmationExecutionDesignDraft,
) -> tuple[CorePrerequisitePolicy, LoopPhasePolicy]:
    thresholds = design.thresholds
    return (
        CorePrerequisitePolicy(
            policy_id="d7-development-core-prerequisites-v0-1",
            core_amplitude_ceiling=thresholds.core_amplitude_ceiling,
            identifiability_floor=thresholds.identifiability_floor,
            edge_coherence_floor=thresholds.coherence_floor,
            minimum_support_count=thresholds.minimum_support_count,
            max_localized_core_fraction=(thresholds.max_localized_core_fraction),
            minimum_core_contrast_ratio=(thresholds.minimum_core_contrast_ratio),
        ),
        LoopPhasePolicy(
            policy_id="d7-development-loop-phase-v0-1",
            amplitude_floor=thresholds.core_amplitude_ceiling,
            identifiability_floor=thresholds.identifiability_floor,
            coherence_floor=thresholds.coherence_floor,
            branch_margin_radians=thresholds.branch_margin_rad,
            integer_residual_tolerance_cycles=(thresholds.loop_oracle_tolerance_cycles),
            nonzero_floor_cycles=thresholds.loop_nonzero_floor_cycles,
        ),
    )


@dataclass(frozen=True, slots=True, init=False)
class D7DevelopmentCorePrediction:
    core_cell_id: str
    field_graph_id: str
    field_estimate_fingerprint_sha256: str
    prediction: SealedCorePrediction

    def __init__(
        self,
        *,
        _factory_token: object = None,
        core_cell_id: str,
        field_graph_id: str,
        field_estimate_fingerprint_sha256: str,
        prediction: SealedCorePrediction,
    ) -> None:
        if _factory_token is not (_D7_DEVELOPMENT_CORE_PREDICTION_FACTORY_TOKEN):
            raise QualificationContractError(
                "D7DevelopmentCorePrediction must be produced by the "
                "development executor"
            )
        for name, value in (
            ("core_cell_id", core_cell_id),
            ("field_graph_id", field_graph_id),
            (
                "field_estimate_fingerprint_sha256",
                field_estimate_fingerprint_sha256,
            ),
            ("prediction", prediction),
        ):
            object.__setattr__(self, name, value)
        self.__post_init__()

    def __post_init__(self) -> None:
        require_slug(self.core_cell_id, label="core_cell_id")
        require_slug(self.field_graph_id, label="field_graph_id")
        require_sha256(
            self.field_estimate_fingerprint_sha256,
            label="field_estimate_fingerprint_sha256",
        )
        if not isinstance(self.prediction, SealedCorePrediction):
            raise TypeError("prediction must be SealedCorePrediction")

    def to_dict(self) -> dict[str, object]:
        return {
            "core_cell_id": self.core_cell_id,
            "field_graph_id": self.field_graph_id,
            "field_estimate_fingerprint_sha256": (
                self.field_estimate_fingerprint_sha256
            ),
            "prediction": self.prediction.to_dict(),
            "oracle_accessed": False,
        }


@dataclass(frozen=True, slots=True, init=False)
class D7DevelopmentLoopPrediction:
    loop_cell_id: str
    field_graph_id: str
    cycle_graph_id: str
    loop_role: LoopRole
    field_estimate_fingerprint_sha256: str
    prediction: SealedLoopPrediction

    def __init__(
        self,
        *,
        _factory_token: object = None,
        loop_cell_id: str,
        field_graph_id: str,
        cycle_graph_id: str,
        loop_role: LoopRole,
        field_estimate_fingerprint_sha256: str,
        prediction: SealedLoopPrediction,
    ) -> None:
        if _factory_token is not (_D7_DEVELOPMENT_LOOP_PREDICTION_FACTORY_TOKEN):
            raise QualificationContractError(
                "D7DevelopmentLoopPrediction must be produced by the "
                "development executor"
            )
        for name, value in (
            ("loop_cell_id", loop_cell_id),
            ("field_graph_id", field_graph_id),
            ("cycle_graph_id", cycle_graph_id),
            ("loop_role", loop_role),
            (
                "field_estimate_fingerprint_sha256",
                field_estimate_fingerprint_sha256,
            ),
            ("prediction", prediction),
        ):
            object.__setattr__(self, name, value)
        self.__post_init__()

    def __post_init__(self) -> None:
        for name in (
            "loop_cell_id",
            "field_graph_id",
            "cycle_graph_id",
        ):
            require_slug(getattr(self, name), label=name)
        if not isinstance(self.loop_role, LoopRole):
            raise TypeError("loop_role must be LoopRole")
        require_sha256(
            self.field_estimate_fingerprint_sha256,
            label="field_estimate_fingerprint_sha256",
        )
        if not isinstance(self.prediction, SealedLoopPrediction):
            raise TypeError("prediction must be SealedLoopPrediction")

    def to_dict(self) -> dict[str, object]:
        return {
            "loop_cell_id": self.loop_cell_id,
            "field_graph_id": self.field_graph_id,
            "cycle_graph_id": self.cycle_graph_id,
            "loop_role": self.loop_role.value,
            "field_estimate_fingerprint_sha256": (
                self.field_estimate_fingerprint_sha256
            ),
            "prediction": self.prediction.to_dict(),
            "oracle_accessed": False,
            "integer_output_present": False,
        }


@dataclass(frozen=True, slots=True, init=False)
class D7DevelopmentPrimaryPrediction:
    primary_unit_id: str
    seed_slot_id: str
    development_seed: int
    spec_receipt_sha256: str
    estimator_input_fingerprint_sha256: str
    graph_input_fingerprint_sha256: str
    primary_execution_fingerprint_sha256: str
    offcore_execution_fingerprint_sha256: str
    core_predictions: tuple[D7DevelopmentCorePrediction, ...]
    loop_predictions: tuple[D7DevelopmentLoopPrediction, ...]

    def __init__(
        self,
        *,
        _factory_token: object = None,
        primary_unit_id: str,
        seed_slot_id: str,
        development_seed: int,
        spec_receipt_sha256: str,
        estimator_input_fingerprint_sha256: str,
        graph_input_fingerprint_sha256: str,
        primary_execution_fingerprint_sha256: str,
        offcore_execution_fingerprint_sha256: str,
        core_predictions: tuple[D7DevelopmentCorePrediction, ...],
        loop_predictions: tuple[D7DevelopmentLoopPrediction, ...],
    ) -> None:
        if _factory_token is not (_D7_DEVELOPMENT_PRIMARY_PREDICTION_FACTORY_TOKEN):
            raise QualificationContractError(
                "D7DevelopmentPrimaryPrediction must be produced by the "
                "development executor"
            )
        for name, value in (
            ("primary_unit_id", primary_unit_id),
            ("seed_slot_id", seed_slot_id),
            ("development_seed", development_seed),
            ("spec_receipt_sha256", spec_receipt_sha256),
            (
                "estimator_input_fingerprint_sha256",
                estimator_input_fingerprint_sha256,
            ),
            (
                "graph_input_fingerprint_sha256",
                graph_input_fingerprint_sha256,
            ),
            (
                "primary_execution_fingerprint_sha256",
                primary_execution_fingerprint_sha256,
            ),
            (
                "offcore_execution_fingerprint_sha256",
                offcore_execution_fingerprint_sha256,
            ),
            ("core_predictions", core_predictions),
            ("loop_predictions", loop_predictions),
        ):
            object.__setattr__(self, name, value)
        self.__post_init__()

    def __post_init__(self) -> None:
        require_slug(self.primary_unit_id, label="primary_unit_id")
        require_slug(self.seed_slot_id, label="seed_slot_id")
        require_d7_confirmation_development_seed(self.development_seed)
        for name in (
            "spec_receipt_sha256",
            "estimator_input_fingerprint_sha256",
            "graph_input_fingerprint_sha256",
            "primary_execution_fingerprint_sha256",
            "offcore_execution_fingerprint_sha256",
        ):
            require_sha256(getattr(self, name), label=name)
        if len(self.core_predictions) != 3 or len(self.loop_predictions) != 18:
            raise ValueError(
                "development primary must contain exact 3 core and 18 loop predictions"
            )
        field_by_graph = {
            item.field_graph_id: item.field_estimate_fingerprint_sha256
            for item in self.core_predictions
        }
        if len(field_by_graph) != 3:
            raise ValueError(
                "development core predictions must cover exactly three A graphs"
            )
        for item in self.loop_predictions:
            if field_by_graph.get(item.field_graph_id) != (
                item.field_estimate_fingerprint_sha256
            ):
                raise ValueError(
                    "core and loop predictions do not share the same "
                    "A-bound field estimate"
                )
        loop_axes = {
            (
                item.field_graph_id,
                item.cycle_graph_id,
                item.loop_role,
            )
            for item in self.loop_predictions
        }
        if len(loop_axes) != 18:
            raise ValueError(
                "development loop predictions do not cover exact 3A-by-3B-by-2 roles"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": ("spirallens.d7-development-primary-prediction.v0.1"),
            "primary_unit_id": self.primary_unit_id,
            "seed_slot_id": self.seed_slot_id,
            "development_seed": self.development_seed,
            "development_seed_is_permanently_excluded": True,
            "spec_receipt_sha256": self.spec_receipt_sha256,
            "estimator_input_fingerprint_sha256": (
                self.estimator_input_fingerprint_sha256
            ),
            "graph_input_fingerprint_sha256": (self.graph_input_fingerprint_sha256),
            "primary_execution_fingerprint_sha256": (
                self.primary_execution_fingerprint_sha256
            ),
            "offcore_execution_fingerprint_sha256": (
                self.offcore_execution_fingerprint_sha256
            ),
            "core_predictions": [item.to_dict() for item in self.core_predictions],
            "loop_predictions": [item.to_dict() for item in self.loop_predictions],
            "core_and_loop_share_graph_input": True,
            "core_and_loop_share_a_bound_field_estimates": True,
            "oracle_truth_record_materialized": False,
            "d7_gate_scored": False,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


@dataclass(frozen=True, slots=True, init=False)
class D7DevelopmentPredictionInventory:
    design_sha256: str
    development_seeds: tuple[int, int]
    primary_predictions: tuple[D7DevelopmentPrimaryPrediction, ...]

    schema_version: ClassVar[str] = D7_DEVELOPMENT_PREDICTION_INVENTORY_SCHEMA_VERSION

    def __init__(
        self,
        *,
        _factory_token: object = None,
        design_sha256: str,
        development_seeds: tuple[int, int],
        primary_predictions: tuple[D7DevelopmentPrimaryPrediction, ...],
    ) -> None:
        if _factory_token is not _D7_DEVELOPMENT_INVENTORY_FACTORY_TOKEN:
            raise QualificationContractError(
                "D7DevelopmentPredictionInventory must be produced by the "
                "development executor"
            )
        object.__setattr__(self, "design_sha256", design_sha256)
        object.__setattr__(self, "development_seeds", development_seeds)
        object.__setattr__(
            self,
            "primary_predictions",
            primary_predictions,
        )
        self.__post_init__()

    def __post_init__(self) -> None:
        require_sha256(self.design_sha256, label="design_sha256")
        if (
            type(self.development_seeds) is not tuple
            or len(self.development_seeds) != 2
            or self.development_seeds != tuple(sorted(set(self.development_seeds)))
        ):
            raise ValueError("development_seeds must be two unique canonical seeds")
        for seed in self.development_seeds:
            require_d7_confirmation_development_seed(seed)
        if len(self.primary_predictions) != 64:
            raise ValueError(
                "development inventory requires exactly 64 primary predictions"
            )
        if any(
            not isinstance(item, D7DevelopmentPrimaryPrediction)
            for item in self.primary_predictions
        ):
            raise TypeError("primary_predictions must contain development predictions")
        identifiers = tuple(item.primary_unit_id for item in self.primary_predictions)
        if identifiers != tuple(sorted(set(identifiers))):
            raise ValueError(
                "development primary predictions must be unique and canonical"
            )
        seed_by_slot = {
            "confirmation-seed-slot-00": self.development_seeds[0],
            "confirmation-seed-slot-01": self.development_seeds[1],
        }
        if any(
            seed_by_slot.get(item.seed_slot_id) != item.development_seed
            for item in self.primary_predictions
        ):
            raise ValueError(
                "development prediction seed differs from its canonical slot"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "record_scope": ("in-memory-development-predictions-not-d7-evidence"),
            "design_sha256": self.design_sha256,
            "development_seeds": list(self.development_seeds),
            "primary_predictions": [
                {
                    "primary_unit_id": item.primary_unit_id,
                    "fingerprint_sha256": item.fingerprint_sha256,
                }
                for item in self.primary_predictions
            ],
            "counts": {
                "primary_units": 64,
                "core_predictions": 192,
                "loop_predictions": 1152,
            },
            "oracle_truth_record_materialized": False,
            "oracle_supplier_called": False,
            "gate_aggregate_produced": False,
            "qualification_result_produced": False,
            "terminal_artifact_produced": False,
            "d7_state": "not_run",
            "scientific_claim_eligible": False,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


def _execute_oracle_record_free_primary(
    design: D7ConfirmationExecutionDesignDraft,
    *,
    unit: D7PrimaryUnitTemplate,
    development_seed: int,
    spec: SpectralMomentConfirmationSpec,
    inputs: CartesianFourierEstimatorInputs,
) -> D7DevelopmentPrimaryPrediction:
    """Execute from numerical inputs without an oracle-truth record parameter."""

    assignments = _assignments(unit)
    graph_input = GraphInput(
        primary_unit_id=unit.primary_unit_id,
        vertex_ids=inputs.row_ids,
        states=inputs.states,
    )
    primary = _crossed_execution(
        design,
        graph_input=graph_input,
        inputs=inputs,
        template=_primary_boundary(
            design,
            level=assignments["boundary"],
        ),
    )
    offcore = _crossed_execution(
        design,
        graph_input=graph_input,
        inputs=inputs,
        template=design.stress_translation.offcore_boundary,
    )
    if any(attempt.binding is None for attempt in primary.cycle_attempts):
        raise ValueError("development primary boundary has an unmatched B graph")
    if any(attempt.binding is None for attempt in offcore.cycle_attempts):
        raise ValueError("development offcore boundary has an unmatched B graph")
    estimates = tuple(
        estimate_cartesian_fourier_field(inputs, graph)
        for graph in primary.field_graphs
    )
    estimate_by_graph: dict[str, CartesianFourierFieldEstimate] = {
        declaration.graph_id: estimate
        for declaration, estimate in zip(
            design.graph_axes.field_estimation,
            estimates,
            strict=True,
        )
    }
    primary_content_sha256 = canonical_json_sha256(
        {
            "schema_version": ("spirallens.d7-development-primary-content.v0.1"),
            "estimator_input_fingerprint_sha256": (inputs.fingerprint_sha256),
        }
    )
    core_policy, loop_policy = _policies(design)
    core_cells = {
        item.field_graph_id: item
        for item in design.inventory.core_cells
        if item.primary_unit_id == unit.primary_unit_id
    }
    core_predictions: list[D7DevelopmentCorePrediction] = []
    for field_graph_id, estimate in estimate_by_graph.items():
        cell = core_cells[field_graph_id]
        blind = build_crossed_blind_core_input(
            primary,
            estimate,
            primary_unit_sha256=primary_content_sha256,
        )
        prediction = estimate_and_seal_core(blind, core_policy)
        core_predictions.append(
            D7DevelopmentCorePrediction(
                _factory_token=(_D7_DEVELOPMENT_CORE_PREDICTION_FACTORY_TOKEN),
                core_cell_id=cell.core_cell_id,
                field_graph_id=field_graph_id,
                field_estimate_fingerprint_sha256=(estimate.fingerprint_sha256),
                prediction=prediction,
            )
        )
    loop_cells = tuple(
        item
        for item in design.inventory.loop_cells
        if item.primary_unit_id == unit.primary_unit_id
    )
    execution_by_role = {
        LoopRole.PRIMARY_BOUNDARY: primary,
        LoopRole.OFFCORE_CONTROL: offcore,
    }
    loop_predictions: list[D7DevelopmentLoopPrediction] = []
    for cell in loop_cells:
        estimate = estimate_by_graph[cell.field_graph_id]
        blind = build_crossed_blind_loop_input(
            execution_by_role[cell.loop_role],
            estimate,
            cycle_graph_id=cell.cycle_graph_id,
            primary_unit_sha256=primary_content_sha256,
        )
        prediction = estimate_and_seal_loop(blind, loop_policy)
        loop_predictions.append(
            D7DevelopmentLoopPrediction(
                _factory_token=(_D7_DEVELOPMENT_LOOP_PREDICTION_FACTORY_TOKEN),
                loop_cell_id=cell.loop_cell_id,
                field_graph_id=cell.field_graph_id,
                cycle_graph_id=cell.cycle_graph_id,
                loop_role=cell.loop_role,
                field_estimate_fingerprint_sha256=(estimate.fingerprint_sha256),
                prediction=prediction,
            )
        )
    return D7DevelopmentPrimaryPrediction(
        _factory_token=(_D7_DEVELOPMENT_PRIMARY_PREDICTION_FACTORY_TOKEN),
        primary_unit_id=unit.primary_unit_id,
        seed_slot_id=unit.seed_slot_id,
        development_seed=development_seed,
        spec_receipt_sha256=spec.receipt_sha256,
        estimator_input_fingerprint_sha256=inputs.fingerprint_sha256,
        graph_input_fingerprint_sha256=graph_input.fingerprint_sha256,
        primary_execution_fingerprint_sha256=primary.fingerprint_sha256,
        offcore_execution_fingerprint_sha256=offcore.fingerprint_sha256,
        core_predictions=tuple(
            sorted(
                core_predictions,
                key=lambda item: item.core_cell_id,
            )
        ),
        loop_predictions=tuple(
            sorted(
                loop_predictions,
                key=lambda item: item.loop_cell_id,
            )
        ),
    )


def execute_d7_confirmation_development_primary(
    design: D7ConfirmationExecutionDesignDraft,
    *,
    unit: D7PrimaryUnitTemplate,
    development_seed: int,
) -> D7DevelopmentPrimaryPrediction:
    """Prepare and seal one permanently excluded development unit."""

    if not isinstance(
        design,
        D7ConfirmationExecutionDesignDraft,
    ):
        raise TypeError("design must be D7ConfirmationExecutionDesignDraft")
    if not isinstance(unit, D7PrimaryUnitTemplate):
        raise TypeError("unit must be D7PrimaryUnitTemplate")
    seed = require_d7_confirmation_development_seed(development_seed)
    if unit not in design.inventory.primary_units:
        raise ValueError("unit is not a member of the supplied design")
    assignments = _assignments(unit)
    spec = SpectralMomentConfirmationSpec(
        seed=seed,
        state_geometry_warp_strength=_numeric_level(
            design.stress_translation.state_geometry_warp_levels,
            level=assignments["state-geometry-warp"],
        ),
        structured_observation_perturbation_scale=_numeric_level(
            design.stress_translation.structured_observation_perturbation_levels,
            level=assignments["structured-observation-perturbation"],
        ),
    )
    prepared = SpectralMomentConfirmationGenerator().prepare(spec)
    case = prepared.case(unit.case_id)
    return _execute_oracle_record_free_primary(
        design,
        unit=unit,
        development_seed=seed,
        spec=spec,
        inputs=case.estimator_inputs,
    )


def execute_d7_confirmation_development_inventory(
    design: D7ConfirmationExecutionDesignDraft,
    *,
    development_seeds: tuple[int, int],
) -> D7DevelopmentPredictionInventory:
    """Seal all 64 development units without constructing an oracle."""

    if not isinstance(
        design,
        D7ConfirmationExecutionDesignDraft,
    ):
        raise TypeError("design must be D7ConfirmationExecutionDesignDraft")
    if (
        type(development_seeds) is not tuple
        or len(development_seeds) != 2
        or development_seeds != tuple(sorted(set(development_seeds)))
    ):
        raise ValueError("development_seeds must be two unique canonical seeds")
    seeds = tuple(
        require_d7_confirmation_development_seed(seed) for seed in development_seeds
    )
    seed_by_slot = {
        "confirmation-seed-slot-00": seeds[0],
        "confirmation-seed-slot-01": seeds[1],
    }
    predictions = tuple(
        execute_d7_confirmation_development_primary(
            design,
            unit=unit,
            development_seed=seed_by_slot[unit.seed_slot_id],
        )
        for unit in design.inventory.primary_units
    )
    return D7DevelopmentPredictionInventory(
        _factory_token=_D7_DEVELOPMENT_INVENTORY_FACTORY_TOKEN,
        design_sha256=design.canonical_sha256,
        development_seeds=seeds,  # type: ignore[arg-type]
        primary_predictions=predictions,
    )


__all__ = [
    "D7_DEVELOPMENT_PREDICTION_INVENTORY_SCHEMA_VERSION",
    "D7DevelopmentCorePrediction",
    "D7DevelopmentLoopPrediction",
    "D7DevelopmentPredictionInventory",
    "D7DevelopmentPrimaryPrediction",
    "execute_d7_confirmation_development_inventory",
    "execute_d7_confirmation_development_primary",
]
