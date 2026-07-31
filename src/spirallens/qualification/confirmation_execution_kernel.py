"""Seed-slot prediction kernel for the seed-free D7 confirmation design.

The kernel accepts an explicitly supplied numerical seed and one member of the
factory-built seed-slot inventory.  It prepares estimator-visible arrays,
constructs the exact crossed A/B graphs, estimates one field per A graph, and
seals the core and continuous-loop predictions without constructing or
accepting an oracle-truth record.

This is an internal prediction surface, not a launch API.  Supplying a seed
does not prove that the seed was frozen, unopened, or authorized.  The kernel
does not score, aggregate, publish, admit a construction family, or create a
D7 result.  Development callers must enforce their own permanently-excluded
seed policy; a later official lifecycle must provide a separate authorization
and chronology before calling this source.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

import numpy as np

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
    SpectralMomentPreparedCase,
)

from .blind import BlindCoreInput, SealedCorePrediction
from .common import (
    QualificationContractError,
    level0_boundary,
    require_sha256,
    require_slug,
)
from .confirmation_execution_design import (
    D7ConfirmationExecutionDesignDraft,
    D7ConfirmationStressTranslation,
    D7PrimaryUnitTemplate,
)
from .crossed import (
    CrossedGraphExecution,
    build_crossed_blind_core_input,
    build_crossed_blind_loop_input,
    build_crossed_graph_execution,
    rectangular_grid_support_faces,
)
from .prerequisites import CorePrerequisitePolicy, estimate_and_seal_core
from .protocol import BoundaryTemplate, LoopRole, NumericStressLevel
from .winding import (
    BlindLoopInput,
    LoopPhasePolicy,
    SealedLoopPrediction,
    estimate_and_seal_loop,
)

D7_CONFIRMATION_CORE_POLICY_ID = "d7-confirmation-core-prerequisites-v0-1"
D7_CONFIRMATION_LOOP_POLICY_ID = "d7-confirmation-loop-phase-v0-1"
D7_SEED_SLOT_PRIMARY_PREDICTION_SCHEMA_VERSION = (
    "spirallens.d7-seed-slot-primary-prediction.v0.1"
)
D7_SEED_SLOT_PREDICTION_KERNEL_ID = (
    "oracle-free-spectral-moment-crossed-seed-slot-prediction-v0.1"
)

_PRIMARY_FACTORY_TOKEN = object()
_CORE_FACTORY_TOKEN = object()
_LOOP_FACTORY_TOKEN = object()
_RUNTIME_HANDOFF_FACTORY_TOKEN = object()


def _plain_seed(value: object) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value,
        (int, np.integer),
    ):
        raise TypeError("supplied_seed must be an integer")
    result = int(value)
    if result < 0 or result > np.iinfo(np.int64).max:
        raise ValueError("supplied_seed must be a non-negative signed-int64 value")
    return result


def _numeric_level(
    values: tuple[NumericStressLevel, ...],
    *,
    level: str,
) -> float:
    matches = tuple(item.value for item in values if item.level == level)
    if len(matches) != 1:
        raise QualificationContractError(
            "stress level must resolve exactly one numeric value"
        )
    return float(matches[0])


def _assignments(unit: D7PrimaryUnitTemplate) -> dict[str, str]:
    result = {item.axis_id: item.level for item in unit.stress_assignments}
    if set(result) != {
        "boundary",
        "state-geometry-warp",
        "structured-observation-perturbation",
    }:
        raise QualificationContractError(
            "primary unit does not carry the exact D7 stress axes"
        )
    return result


def _primary_boundary(
    design: D7ConfirmationExecutionDesignDraft,
    *,
    level: str,
) -> BoundaryTemplate:
    return _translated_primary_boundary(
        design.stress_translation,
        level=level,
    )


def _translated_primary_boundary(
    translation: D7ConfirmationStressTranslation,
    *,
    level: str,
) -> BoundaryTemplate:
    matches = tuple(
        item for item in translation.primary_boundaries if item.level == level
    )
    if len(matches) != 1:
        raise QualificationContractError(
            "boundary level must resolve exactly one template"
        )
    return matches[0]


def _support_faces(template: BoundaryTemplate) -> object:
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
            max_domain_edges_per_graph_edge=domain.max_domain_edges_per_graph_edge,
        ),
    )


def _policies(
    design: D7ConfirmationExecutionDesignDraft,
) -> tuple[CorePrerequisitePolicy, LoopPhasePolicy]:
    thresholds = design.thresholds
    return (
        CorePrerequisitePolicy(
            policy_id=D7_CONFIRMATION_CORE_POLICY_ID,
            core_amplitude_ceiling=thresholds.core_amplitude_ceiling,
            identifiability_floor=thresholds.identifiability_floor,
            edge_coherence_floor=thresholds.coherence_floor,
            minimum_support_count=thresholds.minimum_support_count,
            max_localized_core_fraction=thresholds.max_localized_core_fraction,
            minimum_core_contrast_ratio=thresholds.minimum_core_contrast_ratio,
        ),
        LoopPhasePolicy(
            policy_id=D7_CONFIRMATION_LOOP_POLICY_ID,
            amplitude_floor=thresholds.core_amplitude_ceiling,
            identifiability_floor=thresholds.identifiability_floor,
            coherence_floor=thresholds.coherence_floor,
            branch_margin_radians=thresholds.branch_margin_rad,
            integer_residual_tolerance_cycles=(thresholds.loop_oracle_tolerance_cycles),
            nonzero_floor_cycles=thresholds.loop_nonzero_floor_cycles,
        ),
    )


@dataclass(frozen=True, slots=True, init=False)
class D7SeedSlotCorePrediction:
    """One core prediction sealed from a shared A-bound field estimate."""

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
        if _factory_token is not _CORE_FACTORY_TOKEN:
            raise QualificationContractError(
                "D7SeedSlotCorePrediction must be produced by the "
                "seed-slot prediction kernel"
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
class D7SeedSlotLoopPrediction:
    """One continuous loop prediction sealed from the matching A estimate."""

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
        if _factory_token is not _LOOP_FACTORY_TOKEN:
            raise QualificationContractError(
                "D7SeedSlotLoopPrediction must be produced by the "
                "seed-slot prediction kernel"
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
        for name in ("loop_cell_id", "field_graph_id", "cycle_graph_id"):
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
class D7SeedSlotPrimaryPrediction:
    """Internal prediction payload before any D7 scoring or persistence."""

    primary_unit_id: str
    seed_slot_id: str
    supplied_seed: int
    spec_receipt_sha256: str
    estimator_input_fingerprint_sha256: str
    graph_input_fingerprint_sha256: str
    primary_execution_fingerprint_sha256: str
    offcore_execution_fingerprint_sha256: str
    core_predictions: tuple[D7SeedSlotCorePrediction, ...]
    loop_predictions: tuple[D7SeedSlotLoopPrediction, ...]

    schema_version: ClassVar[str] = D7_SEED_SLOT_PRIMARY_PREDICTION_SCHEMA_VERSION

    def __init__(
        self,
        *,
        _factory_token: object = None,
        primary_unit_id: str,
        seed_slot_id: str,
        supplied_seed: int,
        spec_receipt_sha256: str,
        estimator_input_fingerprint_sha256: str,
        graph_input_fingerprint_sha256: str,
        primary_execution_fingerprint_sha256: str,
        offcore_execution_fingerprint_sha256: str,
        core_predictions: tuple[D7SeedSlotCorePrediction, ...],
        loop_predictions: tuple[D7SeedSlotLoopPrediction, ...],
    ) -> None:
        if _factory_token is not _PRIMARY_FACTORY_TOKEN:
            raise QualificationContractError(
                "D7SeedSlotPrimaryPrediction must be produced by the "
                "seed-slot prediction kernel"
            )
        for name, value in (
            ("primary_unit_id", primary_unit_id),
            ("seed_slot_id", seed_slot_id),
            ("supplied_seed", supplied_seed),
            ("spec_receipt_sha256", spec_receipt_sha256),
            (
                "estimator_input_fingerprint_sha256",
                estimator_input_fingerprint_sha256,
            ),
            ("graph_input_fingerprint_sha256", graph_input_fingerprint_sha256),
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
        _plain_seed(self.supplied_seed)
        for name in (
            "spec_receipt_sha256",
            "estimator_input_fingerprint_sha256",
            "graph_input_fingerprint_sha256",
            "primary_execution_fingerprint_sha256",
            "offcore_execution_fingerprint_sha256",
        ):
            require_sha256(getattr(self, name), label=name)
        if len(self.core_predictions) != 3 or len(self.loop_predictions) != 18:
            raise QualificationContractError(
                "seed-slot primary requires exact 3 core and 18 loop predictions"
            )
        field_by_graph = {
            item.field_graph_id: item.field_estimate_fingerprint_sha256
            for item in self.core_predictions
        }
        if len(field_by_graph) != 3:
            raise QualificationContractError(
                "core predictions must cover exactly three A graphs"
            )
        if any(
            field_by_graph.get(item.field_graph_id)
            != item.field_estimate_fingerprint_sha256
            for item in self.loop_predictions
        ):
            raise QualificationContractError(
                "core and loop predictions must share each A-bound field estimate"
            )
        loop_axes = {
            (item.field_graph_id, item.cycle_graph_id, item.loop_role)
            for item in self.loop_predictions
        }
        if len(loop_axes) != 18:
            raise QualificationContractError(
                "loop predictions must cover exact 3A-by-3B-by-2 roles"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "kernel_id": D7_SEED_SLOT_PREDICTION_KERNEL_ID,
            **level0_boundary(),
            "primary_unit_id": self.primary_unit_id,
            "seed_slot_id": self.seed_slot_id,
            "supplied_seed": self.supplied_seed,
            "seed_freeze_or_authorization_attested": False,
            "chronology_attested": False,
            "spec_receipt_sha256": self.spec_receipt_sha256,
            "estimator_input_fingerprint_sha256": (
                self.estimator_input_fingerprint_sha256
            ),
            "graph_input_fingerprint_sha256": self.graph_input_fingerprint_sha256,
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
            "gate_scored": False,
            "result_produced": False,
            "scientific_claim_eligible": False,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


@dataclass(frozen=True, slots=True, init=False)
class _D7SeedSlotPrimaryRuntimeHandoff:
    """Private oracle-free objects retained after one primary is sealed."""

    prediction: D7SeedSlotPrimaryPrediction
    unit: D7PrimaryUnitTemplate
    stress_translation: D7ConfirmationStressTranslation
    spec: SpectralMomentConfirmationSpec
    prepared_case: SpectralMomentPreparedCase
    estimator_inputs: CartesianFourierEstimatorInputs
    graph_input: GraphInput
    primary_execution: CrossedGraphExecution
    offcore_execution: CrossedGraphExecution
    field_estimates: tuple[tuple[str, CartesianFourierFieldEstimate], ...]
    blind_core_inputs: tuple[tuple[str, BlindCoreInput], ...]
    blind_loop_inputs: tuple[tuple[str, BlindLoopInput], ...]
    core_policy: CorePrerequisitePolicy
    loop_policy: LoopPhasePolicy

    def __init__(
        self,
        *,
        _factory_token: object = None,
        prediction: D7SeedSlotPrimaryPrediction,
        unit: D7PrimaryUnitTemplate,
        stress_translation: D7ConfirmationStressTranslation,
        spec: SpectralMomentConfirmationSpec,
        prepared_case: SpectralMomentPreparedCase,
        estimator_inputs: CartesianFourierEstimatorInputs,
        graph_input: GraphInput,
        primary_execution: CrossedGraphExecution,
        offcore_execution: CrossedGraphExecution,
        field_estimates: tuple[tuple[str, CartesianFourierFieldEstimate], ...],
        blind_core_inputs: tuple[tuple[str, BlindCoreInput], ...],
        blind_loop_inputs: tuple[tuple[str, BlindLoopInput], ...],
        core_policy: CorePrerequisitePolicy,
        loop_policy: LoopPhasePolicy,
    ) -> None:
        if _factory_token is not _RUNTIME_HANDOFF_FACTORY_TOKEN:
            raise QualificationContractError(
                "D7 seed-slot runtime handoff must be produced by the "
                "seed-slot prediction kernel"
            )
        for name, value in (
            ("prediction", prediction),
            ("unit", unit),
            ("stress_translation", stress_translation),
            ("spec", spec),
            ("prepared_case", prepared_case),
            ("estimator_inputs", estimator_inputs),
            ("graph_input", graph_input),
            ("primary_execution", primary_execution),
            ("offcore_execution", offcore_execution),
            ("field_estimates", field_estimates),
            ("blind_core_inputs", blind_core_inputs),
            ("blind_loop_inputs", blind_loop_inputs),
            ("core_policy", core_policy),
            ("loop_policy", loop_policy),
        ):
            object.__setattr__(self, name, value)
        self._validate()

    @staticmethod
    def _validate_pairs(
        value: object,
        *,
        item_type: type[object],
        label: str,
    ) -> tuple[tuple[str, object], ...]:
        if type(value) is not tuple:
            raise TypeError(f"{label} must be a tuple")
        pairs = value
        if any(
            type(pair) is not tuple
            or len(pair) != 2
            or type(pair[0]) is not str
            or type(pair[1]) is not item_type
            for pair in pairs
        ):
            raise TypeError(f"{label} must contain exact identifier/object pairs")
        identifiers = tuple(pair[0] for pair in pairs)
        if identifiers != tuple(sorted(set(identifiers))):
            raise QualificationContractError(
                f"{label} identifiers must be unique and canonical"
            )
        return pairs

    def _validate(self) -> None:
        for name, expected_type in (
            ("prediction", D7SeedSlotPrimaryPrediction),
            ("unit", D7PrimaryUnitTemplate),
            ("stress_translation", D7ConfirmationStressTranslation),
            ("spec", SpectralMomentConfirmationSpec),
            ("prepared_case", SpectralMomentPreparedCase),
            ("estimator_inputs", CartesianFourierEstimatorInputs),
            ("graph_input", GraphInput),
            ("primary_execution", CrossedGraphExecution),
            ("offcore_execution", CrossedGraphExecution),
            ("core_policy", CorePrerequisitePolicy),
            ("loop_policy", LoopPhasePolicy),
        ):
            if type(getattr(self, name)) is not expected_type:
                raise TypeError(f"{name} must be {expected_type.__name__}")
        prediction = self.prediction
        if (
            type(prediction.core_predictions) is not tuple
            or any(
                type(item) is not D7SeedSlotCorePrediction
                or type(item.prediction) is not SealedCorePrediction
                for item in prediction.core_predictions
            )
            or type(prediction.loop_predictions) is not tuple
            or any(
                type(item) is not D7SeedSlotLoopPrediction
                or type(item.prediction) is not SealedLoopPrediction
                for item in prediction.loop_predictions
            )
        ):
            raise TypeError(
                "prediction children and sealed predictions must use exact types"
            )
        assignments = _assignments(self.unit)
        primary_boundary = _translated_primary_boundary(
            self.stress_translation,
            level=assignments["boundary"],
        )
        if (
            self.spec.state_geometry_warp_strength
            != _numeric_level(
                self.stress_translation.state_geometry_warp_levels,
                level=assignments["state-geometry-warp"],
            )
            or self.spec.structured_observation_perturbation_scale
            != _numeric_level(
                self.stress_translation.structured_observation_perturbation_levels,
                level=assignments["structured-observation-perturbation"],
            )
            or not np.array_equal(
                self.primary_execution.cycle_class.support_face_indices,
                _support_faces(primary_boundary),
            )
            or not np.array_equal(
                self.offcore_execution.cycle_class.support_face_indices,
                _support_faces(self.stress_translation.offcore_boundary),
            )
        ):
            raise QualificationContractError(
                "runtime objects differ from the unit stress assignments"
            )
        if (
            self.unit.primary_unit_id != prediction.primary_unit_id
            or self.unit.seed_slot_id != prediction.seed_slot_id
            or self.graph_input.primary_unit_id != prediction.primary_unit_id
            or self.spec.seed != prediction.supplied_seed
            or self.spec.receipt_sha256 != prediction.spec_receipt_sha256
            or self.estimator_inputs.fingerprint_sha256
            != prediction.estimator_input_fingerprint_sha256
            or self.graph_input.fingerprint_sha256
            != prediction.graph_input_fingerprint_sha256
            or self.primary_execution.fingerprint_sha256
            != prediction.primary_execution_fingerprint_sha256
            or self.offcore_execution.fingerprint_sha256
            != prediction.offcore_execution_fingerprint_sha256
        ):
            raise QualificationContractError(
                "runtime objects differ from the sealed primary prediction"
            )
        prepared_case = self.prepared_case
        expected_inputs = prepared_case.estimator_inputs
        if (
            prepared_case.case_id != self.unit.case_id
            or prepared_case.spec_receipt_sha256 != self.spec.receipt_sha256
            or expected_inputs is not self.estimator_inputs
            or expected_inputs.fingerprint_sha256
            != self.estimator_inputs.fingerprint_sha256
            or expected_inputs.to_dict() != self.estimator_inputs.to_dict()
            or any(
                not np.array_equal(
                    getattr(expected_inputs, name),
                    getattr(self.estimator_inputs, name),
                )
                for name in CartesianFourierEstimatorInputs._ARRAY_LAYOUT
            )
        ):
            raise QualificationContractError(
                "runtime estimator inputs differ from the exact spec and unit case"
            )
        if (
            self.primary_execution.graph_input.fingerprint_sha256
            != self.graph_input.fingerprint_sha256
            or self.offcore_execution.graph_input.fingerprint_sha256
            != self.graph_input.fingerprint_sha256
        ):
            raise QualificationContractError(
                "runtime executions differ from the shared GraphInput"
            )

        estimate_pairs = self._validate_pairs(
            self.field_estimates,
            item_type=CartesianFourierFieldEstimate,
            label="field_estimates",
        )
        core_input_pairs = self._validate_pairs(
            self.blind_core_inputs,
            item_type=BlindCoreInput,
            label="blind_core_inputs",
        )
        loop_input_pairs = self._validate_pairs(
            self.blind_loop_inputs,
            item_type=BlindLoopInput,
            label="blind_loop_inputs",
        )
        estimates = dict(estimate_pairs)
        core_inputs = dict(core_input_pairs)
        loop_inputs = dict(loop_input_pairs)
        core_predictions = {
            item.core_cell_id: item for item in prediction.core_predictions
        }
        loop_predictions = {
            item.loop_cell_id: item for item in prediction.loop_predictions
        }
        expected_field_ids = tuple(
            sorted(set(item.field_graph_id for item in prediction.core_predictions))
        )
        if tuple(estimates) != expected_field_ids:
            raise QualificationContractError(
                "field_estimates do not cover the exact prediction A axis"
            )
        if tuple(core_inputs) != tuple(sorted(core_predictions)):
            raise QualificationContractError(
                "blind_core_inputs do not cover the exact core cells"
            )
        if tuple(loop_inputs) != tuple(sorted(loop_predictions)):
            raise QualificationContractError(
                "blind_loop_inputs do not cover the exact loop cells"
            )

        primary_fields = {
            graph.specification.spec_id: graph
            for graph in self.primary_execution.field_graphs
        }
        for field_graph_id, estimate in estimates.items():
            graph = primary_fields.get(field_graph_id)
            if (
                graph is None
                or estimate.estimator_inputs.fingerprint_sha256
                != self.estimator_inputs.fingerprint_sha256
                or estimate.field_graph.fingerprint_sha256 != graph.fingerprint_sha256
            ):
                raise QualificationContractError(
                    "field estimate does not join the prepared input and A graph"
                )

        for core_cell_id, blind_input in core_inputs.items():
            sealed = core_predictions[core_cell_id]
            estimate = estimates[sealed.field_graph_id]
            if (
                blind_input.estimator_input_fingerprint_sha256
                != self.estimator_inputs.fingerprint_sha256
                or blind_input.field_graph_fingerprint_sha256
                != estimate.field_graph.fingerprint_sha256
                or blind_input.field_estimate_fingerprint_sha256
                != estimate.fingerprint_sha256
                or blind_input.fingerprint_sha256
                != sealed.prediction.blind_input_fingerprint_sha256
                or blind_input.primary_unit_sha256
                != sealed.prediction.primary_unit_sha256
                or sealed.field_estimate_fingerprint_sha256
                != estimate.fingerprint_sha256
                or sealed.prediction.policy_fingerprint_sha256
                != self.core_policy.fingerprint_sha256
            ):
                raise QualificationContractError(
                    "core runtime input does not join its sealed prediction"
                )

        execution_by_role = {
            LoopRole.PRIMARY_BOUNDARY: self.primary_execution,
            LoopRole.OFFCORE_CONTROL: self.offcore_execution,
        }
        for loop_cell_id, blind_input in loop_inputs.items():
            sealed = loop_predictions[loop_cell_id]
            estimate = estimates[sealed.field_graph_id]
            execution = execution_by_role[sealed.loop_role]
            cycle_graphs = {
                graph.specification.spec_id: graph for graph in execution.cycle_graphs
            }
            cycle_graph = cycle_graphs.get(sealed.cycle_graph_id)
            if (
                cycle_graph is None
                or blind_input.estimator_input_fingerprint_sha256
                != self.estimator_inputs.fingerprint_sha256
                or blind_input.field_graph_fingerprint_sha256
                != estimate.field_graph.fingerprint_sha256
                or blind_input.field_estimate_fingerprint_sha256
                != estimate.fingerprint_sha256
                or blind_input.cycle_graph_fingerprint_sha256
                != cycle_graph.fingerprint_sha256
                or blind_input.fingerprint_sha256
                != sealed.prediction.blind_input_fingerprint_sha256
                or blind_input.primary_unit_sha256
                != sealed.prediction.primary_unit_sha256
                or sealed.field_estimate_fingerprint_sha256
                != estimate.fingerprint_sha256
                or sealed.prediction.policy_fingerprint_sha256
                != self.loop_policy.fingerprint_sha256
            ):
                raise QualificationContractError(
                    "loop runtime input does not join its sealed prediction"
                )


def _execute_d7_seed_slot_primary_runtime(
    design: D7ConfirmationExecutionDesignDraft,
    *,
    unit: D7PrimaryUnitTemplate,
    supplied_seed: int,
) -> _D7SeedSlotPrimaryRuntimeHandoff:
    """Seal one primary and retain its private oracle-free runtime objects."""

    if not isinstance(design, D7ConfirmationExecutionDesignDraft):
        raise TypeError("design must be D7ConfirmationExecutionDesignDraft")
    if not isinstance(unit, D7PrimaryUnitTemplate):
        raise TypeError("unit must be D7PrimaryUnitTemplate")
    seed = _plain_seed(supplied_seed)
    if unit not in design.inventory.primary_units:
        raise QualificationContractError(
            "unit is not a member of the supplied seed-free design"
        )
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
    prepared_case = prepared.case(unit.case_id)
    inputs = prepared_case.estimator_inputs
    graph_input = GraphInput(
        primary_unit_id=unit.primary_unit_id,
        vertex_ids=inputs.row_ids,
        states=inputs.states,
    )
    primary = _crossed_execution(
        design,
        graph_input=graph_input,
        inputs=inputs,
        template=_primary_boundary(design, level=assignments["boundary"]),
    )
    offcore = _crossed_execution(
        design,
        graph_input=graph_input,
        inputs=inputs,
        template=design.stress_translation.offcore_boundary,
    )
    if any(attempt.binding is None for attempt in primary.cycle_attempts):
        raise QualificationContractError(
            "primary boundary has an unmatched cycle graph"
        )
    if any(attempt.binding is None for attempt in offcore.cycle_attempts):
        raise QualificationContractError(
            "offcore boundary has an unmatched cycle graph"
        )
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
            "schema_version": "spirallens.d7-seed-slot-primary-content.v0.1",
            "estimator_input_fingerprint_sha256": inputs.fingerprint_sha256,
        }
    )
    core_policy, loop_policy = _policies(design)
    core_cells = {
        item.field_graph_id: item
        for item in design.inventory.core_cells
        if item.primary_unit_id == unit.primary_unit_id
    }
    core_predictions: list[D7SeedSlotCorePrediction] = []
    blind_core_inputs: list[tuple[str, BlindCoreInput]] = []
    for field_graph_id, estimate in estimate_by_graph.items():
        cell = core_cells[field_graph_id]
        blind = build_crossed_blind_core_input(
            primary,
            estimate,
            primary_unit_sha256=primary_content_sha256,
        )
        blind_core_inputs.append((cell.core_cell_id, blind))
        core_predictions.append(
            D7SeedSlotCorePrediction(
                _factory_token=_CORE_FACTORY_TOKEN,
                core_cell_id=cell.core_cell_id,
                field_graph_id=field_graph_id,
                field_estimate_fingerprint_sha256=estimate.fingerprint_sha256,
                prediction=estimate_and_seal_core(blind, core_policy),
            )
        )
    execution_by_role = {
        LoopRole.PRIMARY_BOUNDARY: primary,
        LoopRole.OFFCORE_CONTROL: offcore,
    }
    loop_predictions: list[D7SeedSlotLoopPrediction] = []
    blind_loop_inputs: list[tuple[str, BlindLoopInput]] = []
    for cell in (
        item
        for item in design.inventory.loop_cells
        if item.primary_unit_id == unit.primary_unit_id
    ):
        estimate = estimate_by_graph[cell.field_graph_id]
        blind = build_crossed_blind_loop_input(
            execution_by_role[cell.loop_role],
            estimate,
            cycle_graph_id=cell.cycle_graph_id,
            primary_unit_sha256=primary_content_sha256,
        )
        blind_loop_inputs.append((cell.loop_cell_id, blind))
        loop_predictions.append(
            D7SeedSlotLoopPrediction(
                _factory_token=_LOOP_FACTORY_TOKEN,
                loop_cell_id=cell.loop_cell_id,
                field_graph_id=cell.field_graph_id,
                cycle_graph_id=cell.cycle_graph_id,
                loop_role=cell.loop_role,
                field_estimate_fingerprint_sha256=estimate.fingerprint_sha256,
                prediction=estimate_and_seal_loop(blind, loop_policy),
            )
        )
    prediction = D7SeedSlotPrimaryPrediction(
        _factory_token=_PRIMARY_FACTORY_TOKEN,
        primary_unit_id=unit.primary_unit_id,
        seed_slot_id=unit.seed_slot_id,
        supplied_seed=seed,
        spec_receipt_sha256=spec.receipt_sha256,
        estimator_input_fingerprint_sha256=inputs.fingerprint_sha256,
        graph_input_fingerprint_sha256=graph_input.fingerprint_sha256,
        primary_execution_fingerprint_sha256=primary.fingerprint_sha256,
        offcore_execution_fingerprint_sha256=offcore.fingerprint_sha256,
        core_predictions=tuple(
            sorted(core_predictions, key=lambda item: item.core_cell_id)
        ),
        loop_predictions=tuple(
            sorted(loop_predictions, key=lambda item: item.loop_cell_id)
        ),
    )
    return _D7SeedSlotPrimaryRuntimeHandoff(
        _factory_token=_RUNTIME_HANDOFF_FACTORY_TOKEN,
        prediction=prediction,
        unit=unit,
        stress_translation=design.stress_translation,
        spec=spec,
        prepared_case=prepared_case,
        estimator_inputs=inputs,
        graph_input=graph_input,
        primary_execution=primary,
        offcore_execution=offcore,
        field_estimates=tuple(sorted(estimate_by_graph.items())),
        blind_core_inputs=tuple(sorted(blind_core_inputs)),
        blind_loop_inputs=tuple(sorted(blind_loop_inputs)),
        core_policy=core_policy,
        loop_policy=loop_policy,
    )


def execute_d7_seed_slot_primary(
    design: D7ConfirmationExecutionDesignDraft,
    *,
    unit: D7PrimaryUnitTemplate,
    supplied_seed: int,
) -> D7SeedSlotPrimaryPrediction:
    """Seal one seed-slot prediction without oracle, scoring, or authority."""

    return _execute_d7_seed_slot_primary_runtime(
        design,
        unit=unit,
        supplied_seed=supplied_seed,
    ).prediction


__all__ = [
    "D7_CONFIRMATION_CORE_POLICY_ID",
    "D7_CONFIRMATION_LOOP_POLICY_ID",
    "D7_SEED_SLOT_PREDICTION_KERNEL_ID",
    "D7_SEED_SLOT_PRIMARY_PREDICTION_SCHEMA_VERSION",
    "D7SeedSlotCorePrediction",
    "D7SeedSlotLoopPrediction",
    "D7SeedSlotPrimaryPrediction",
    "execute_d7_seed_slot_primary",
]
