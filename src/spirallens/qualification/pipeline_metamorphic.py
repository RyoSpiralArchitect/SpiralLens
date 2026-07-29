"""Truth-free, end-to-end metamorphic checks for the Cartesian pipeline.

Unlike :mod:`spirallens.qualification.metamorphic`, this module does not only
check algebra on arrays supplied by a caller.  Every check starts from the
development Cartesian generator, constructs the declared graph cross, runs
the graph-local field estimator, builds an exact crossed loop input, and runs
the continuous sampled-phase estimator.  Transformed inputs are then sent
through the same factories again.

The resulting receipts are Level-0 development evidence.  They contain no
oracle label, anchor, charge, integer winding, topology claim, subject value,
or D3 gate verdict.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

import numpy as np
from numpy.typing import NDArray

from spirallens.core.canonical import canonical_json_sha256
from spirallens.graphs import (
    BoundaryRefinementRule,
    GraphFamily,
    GraphInput,
    GraphPurpose,
)
from spirallens.synthetic.cartesian_fourier_domain_phantom import (
    CartesianFourierDomainGenerator,
    CartesianFourierDomainSpec,
    CartesianFourierEstimatorInputs,
)
from spirallens.synthetic.cartesian_fourier_estimator import (
    CartesianFourierFieldEstimate,
    estimate_cartesian_fourier_field,
)

from .common import (
    AttemptStatus,
    QualificationContractError,
    QualificationState,
    array_fingerprint,
    level0_boundary,
    require_bool,
    require_enum,
    require_finite_real,
    require_plain_int,
    require_sha256,
    require_slug,
)
from .crossed import (
    CrossedGraphExecution,
    build_crossed_blind_loop_input,
    build_crossed_graph_execution,
    rectangular_grid_support_faces,
)
from .protocol import GraphAxes, GraphDeclaration
from .winding import (
    BlindLoopInput,
    LoopPhasePolicy,
    SealedLoopPrediction,
    build_blind_loop_input,
    estimate_and_seal_loop,
)

FloatArray = NDArray[np.float64]

PIPELINE_METAMORPHIC_DEVELOPMENT_SEED = 314159
PIPELINE_METAMORPHIC_TOLERANCE = 2e-11
PIPELINE_METAMORPHIC_RECEIPT_VERSION = (
    "spirallens.cartesian-pipeline-metamorphic-receipt.v0.1"
)


class PipelineMetamorphLaw(str, Enum):
    """Closed end-to-end transformation set for the D3 development check."""

    AMBIENT_SIGNED_PERMUTATION = "ambient_signed_permutation"
    REFERENCE_ROTATION = "reference_rotation"
    REFERENCE_REFLECTION = "reference_reflection"
    LOOP_REVERSAL = "loop_reversal"


_LAW_ORDER = (
    PipelineMetamorphLaw.AMBIENT_SIGNED_PERMUTATION,
    PipelineMetamorphLaw.REFERENCE_ROTATION,
    PipelineMetamorphLaw.REFERENCE_REFLECTION,
    PipelineMetamorphLaw.LOOP_REVERSAL,
)


def _maximum_error(left: object, right: object) -> float:
    left_array = np.asarray(left, dtype=np.float64)
    right_array = np.asarray(right, dtype=np.float64)
    if left_array.shape != right_array.shape:
        return math.inf
    if left_array.size == 0:
        return 0.0
    return float(np.max(np.abs(left_array - right_array)))


def _validated_sha256_fields(instance: object, names: tuple[str, ...]) -> None:
    for name in names:
        require_sha256(getattr(instance, name), label=name)


@dataclass(frozen=True, slots=True)
class PipelineSnapshot:
    """Fingerprints emitted by one actual estimator/graph/loop execution."""

    estimator_input_fingerprint_sha256: str
    graph_input_fingerprint_sha256: str
    crossed_execution_fingerprint_sha256: str
    field_graph_fingerprint_sha256: str
    cycle_graph_fingerprint_sha256: str
    field_estimate_fingerprint_sha256: str
    blind_loop_input_fingerprint_sha256: str
    sealed_loop_prediction_fingerprint_sha256: str

    def __post_init__(self) -> None:
        _validated_sha256_fields(
            self,
            (
                "estimator_input_fingerprint_sha256",
                "graph_input_fingerprint_sha256",
                "crossed_execution_fingerprint_sha256",
                "field_graph_fingerprint_sha256",
                "cycle_graph_fingerprint_sha256",
                "field_estimate_fingerprint_sha256",
                "blind_loop_input_fingerprint_sha256",
                "sealed_loop_prediction_fingerprint_sha256",
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "estimator_input_fingerprint_sha256": (
                self.estimator_input_fingerprint_sha256
            ),
            "graph_input_fingerprint_sha256": (self.graph_input_fingerprint_sha256),
            "crossed_execution_fingerprint_sha256": (
                self.crossed_execution_fingerprint_sha256
            ),
            "field_graph_fingerprint_sha256": (self.field_graph_fingerprint_sha256),
            "cycle_graph_fingerprint_sha256": (self.cycle_graph_fingerprint_sha256),
            "field_estimate_fingerprint_sha256": (
                self.field_estimate_fingerprint_sha256
            ),
            "blind_loop_input_fingerprint_sha256": (
                self.blind_loop_input_fingerprint_sha256
            ),
            "sealed_loop_prediction_fingerprint_sha256": (
                self.sealed_loop_prediction_fingerprint_sha256
            ),
        }

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


@dataclass(frozen=True, slots=True)
class PipelineMetamorphCheck:
    """One typed receipt for an actually rerun Cartesian transformation."""

    check_id: str
    law: PipelineMetamorphLaw
    state: QualificationState
    transformation_sha256: str
    base: PipelineSnapshot
    transformed: PipelineSnapshot
    inverse: PipelineSnapshot
    composition_sequential: PipelineSnapshot
    composition_direct: PipelineSnapshot
    expected_loop_orientation_sign: int
    maximum_distance_error: float
    maximum_field_law_error: float
    maximum_loop_law_error: float
    tolerance: float
    nonidentity_verified: bool
    inverse_verified: bool
    composition_verified: bool
    all_graph_adjacencies_verified: bool
    all_graph_edge_distances_bit_identical: bool
    claim_relevant_field_law_verified: bool
    continuous_loop_law_verified: bool
    pipeline_rerun_verified: bool
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        require_slug(self.check_id, label="check_id")
        require_enum(PipelineMetamorphLaw, self.law, label="law")
        require_enum(QualificationState, self.state, label="state")
        if self.state not in {
            QualificationState.PASS,
            QualificationState.FAIL,
        }:
            raise QualificationContractError(
                "pipeline metamorph state must be pass or fail"
            )
        require_sha256(
            self.transformation_sha256,
            label="transformation_sha256",
        )
        for label in (
            "base",
            "transformed",
            "inverse",
            "composition_sequential",
            "composition_direct",
        ):
            if not isinstance(getattr(self, label), PipelineSnapshot):
                raise TypeError(f"{label} must be a PipelineSnapshot")
        if self.expected_loop_orientation_sign not in {-1, 1}:
            raise QualificationContractError(
                "expected_loop_orientation_sign must be -1 or 1"
            )
        for label in (
            "maximum_distance_error",
            "maximum_field_law_error",
            "maximum_loop_law_error",
            "tolerance",
        ):
            require_finite_real(
                getattr(self, label),
                label=label,
                minimum=0.0,
            )
        flags = (
            "nonidentity_verified",
            "inverse_verified",
            "composition_verified",
            "all_graph_adjacencies_verified",
            "all_graph_edge_distances_bit_identical",
            "claim_relevant_field_law_verified",
            "continuous_loop_law_verified",
            "pipeline_rerun_verified",
        )
        for label in flags:
            require_bool(getattr(self, label), label=label)
        if not self.reason_codes or self.reason_codes != tuple(
            sorted(set(self.reason_codes))
        ):
            raise QualificationContractError(
                "reason_codes must be nonempty, unique, and canonical"
            )
        for index, reason in enumerate(self.reason_codes):
            require_slug(reason, label=f"reason_codes[{index}]")
        passed = (
            all(getattr(self, label) for label in flags)
            and self.maximum_distance_error <= self.tolerance
            and self.maximum_field_law_error <= self.tolerance
            and self.maximum_loop_law_error <= self.tolerance
        )
        if (self.state is QualificationState.PASS) != passed:
            raise QualificationContractError(
                "check state must equal the mechanically derived pipeline result"
            )
        expected_reasons = (
            ("pipeline_transformation_law_verified",)
            if passed
            else ("pipeline_transformation_law_failed",)
        )
        if self.reason_codes != expected_reasons:
            raise QualificationContractError(
                "reason_codes must equal the mechanically derived result"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": ("spirallens.cartesian-pipeline-metamorph-check.v0.1"),
            **level0_boundary(),
            "check_id": self.check_id,
            "law": self.law.value,
            "state": self.state.value,
            "transformation_sha256": self.transformation_sha256,
            "base": self.base.to_dict(),
            "transformed": self.transformed.to_dict(),
            "inverse": self.inverse.to_dict(),
            "composition_sequential": self.composition_sequential.to_dict(),
            "composition_direct": self.composition_direct.to_dict(),
            "expected_loop_orientation_sign": (self.expected_loop_orientation_sign),
            "maximum_distance_error": self.maximum_distance_error,
            "maximum_field_law_error": self.maximum_field_law_error,
            "maximum_loop_law_error": self.maximum_loop_law_error,
            "tolerance": self.tolerance,
            "nonidentity_verified": self.nonidentity_verified,
            "inverse_verified": self.inverse_verified,
            "composition_verified": self.composition_verified,
            "all_graph_adjacencies_verified": (self.all_graph_adjacencies_verified),
            "all_graph_edge_distances_bit_identical": (
                self.all_graph_edge_distances_bit_identical
            ),
            "claim_relevant_field_law_verified": (
                self.claim_relevant_field_law_verified
            ),
            "continuous_loop_law_verified": (self.continuous_loop_law_verified),
            "pipeline_rerun_verified": self.pipeline_rerun_verified,
            "reason_codes": list(self.reason_codes),
            "oracle_object_read": False,
            "case_id_read": False,
            "anchor_read": False,
            "charge_read": False,
            "subject_value_read": False,
            "sampled_continuous_observable_only": True,
            "integer_output_present": False,
            "topology_claimed": False,
            "d3_gate_advanced": False,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


@dataclass(frozen=True, slots=True)
class CartesianPipelineMetamorphicReceipt:
    """Aggregate truth-free D3 evidence, ready for a later gate adapter."""

    development_seed: int
    generator_spec_receipt_sha256: str
    source_estimator_input_fingerprint_sha256: str
    checks: tuple[PipelineMetamorphCheck, ...]
    state: QualificationState
    pipeline_rerun_verified: bool

    receipt_version: ClassVar[str] = PIPELINE_METAMORPHIC_RECEIPT_VERSION

    def __post_init__(self) -> None:
        seed = require_plain_int(
            self.development_seed,
            label="development_seed",
            minimum=0,
        )
        if seed != PIPELINE_METAMORPHIC_DEVELOPMENT_SEED:
            raise QualificationContractError(
                "pipeline metamorphic receipts are restricted to seed 314159"
            )
        require_sha256(
            self.generator_spec_receipt_sha256,
            label="generator_spec_receipt_sha256",
        )
        require_sha256(
            self.source_estimator_input_fingerprint_sha256,
            label="source_estimator_input_fingerprint_sha256",
        )
        if self.state not in {
            QualificationState.PASS,
            QualificationState.FAIL,
        }:
            raise QualificationContractError("aggregate state must be pass or fail")
        if tuple(check.law for check in self.checks) != _LAW_ORDER:
            raise QualificationContractError(
                "pipeline metamorphic checks must use the closed canonical order"
            )
        if len({check.check_id for check in self.checks}) != len(self.checks):
            raise QualificationContractError("check_id values must be unique")
        rerun = require_bool(
            self.pipeline_rerun_verified,
            label="pipeline_rerun_verified",
        )
        passed = all(check.state is QualificationState.PASS for check in self.checks)
        if rerun != all(check.pipeline_rerun_verified for check in self.checks):
            raise QualificationContractError(
                "aggregate pipeline_rerun_verified differs from its checks"
            )
        if (self.state is QualificationState.PASS) != (passed and rerun):
            raise QualificationContractError(
                "aggregate state must equal the mechanical check conjunction"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            **level0_boundary(),
            "development_seed": self.development_seed,
            "development_seed_only": True,
            "selection_seed_accessed": False,
            "generator_spec_receipt_sha256": (self.generator_spec_receipt_sha256),
            "source_estimator_input_fingerprint_sha256": (
                self.source_estimator_input_fingerprint_sha256
            ),
            "estimator_input_selection_rule": (
                "canonical-generator-observable-position-zero"
            ),
            "checks": [check.to_dict() for check in self.checks],
            "state": self.state.value,
            "pipeline_rerun_verified": self.pipeline_rerun_verified,
            "private_content_pseudonym_helper_imported": False,
            "content_pseudonym_receipt_algorithm_reimplemented": True,
            "content_pseudonym_dependency": (
                "cartesian-fourier-label-free-content-v0.1"
            ),
            "future_gate_evidence_adapter_required": True,
            "qualification_contract_module_imported": False,
            "oracle_object_read": False,
            "case_id_read": False,
            "anchor_read": False,
            "charge_read": False,
            "subject_value_read": False,
            "sampled_continuous_observable_only": True,
            "integer_output_present": False,
            "topology_claimed": False,
            "synthetic_qualification_advanced": False,
            "d3_gate_advanced": False,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


@dataclass(frozen=True, slots=True)
class _PipelineRun:
    inputs: CartesianFourierEstimatorInputs
    graph_input: GraphInput
    execution: CrossedGraphExecution
    estimate: CartesianFourierFieldEstimate
    loop_input: BlindLoopInput
    loop_prediction: SealedLoopPrediction

    @property
    def snapshot(self) -> PipelineSnapshot:
        return _snapshot(
            self,
            loop_input=self.loop_input,
            loop_prediction=self.loop_prediction,
        )


def _declaration(
    graph_id: str,
    family: GraphFamily,
    purpose: GraphPurpose,
    **parameters: float,
) -> GraphDeclaration:
    return GraphDeclaration(
        graph_id=graph_id,
        family=family,
        purpose=purpose,
        parameters=tuple(sorted(parameters.items())),
    )


def _graph_axes() -> GraphAxes:
    return GraphAxes(
        field_estimation=(
            _declaration(
                "d3-a-mutual",
                GraphFamily.MUTUAL_KNN,
                GraphPurpose.FIELD_ESTIMATION,
                neighbor_count=4,
            ),
            _declaration(
                "d3-a-radius",
                GraphFamily.FIXED_RADIUS,
                GraphPurpose.FIELD_ESTIMATION,
                radius=0.42,
            ),
            _declaration(
                "d3-a-shared",
                GraphFamily.SHARED_NEIGHBOR,
                GraphPurpose.FIELD_ESTIMATION,
                minimum_shared_neighbors=2,
                neighbor_count=4,
            ),
        ),
        cycle_construction=(
            _declaration(
                "d3-b-mutual",
                GraphFamily.MUTUAL_KNN,
                GraphPurpose.CYCLE_CONSTRUCTION,
                neighbor_count=4,
            ),
            _declaration(
                "d3-b-radius",
                GraphFamily.FIXED_RADIUS,
                GraphPurpose.CYCLE_CONSTRUCTION,
                radius=0.42,
            ),
            _declaration(
                "d3-b-shared",
                GraphFamily.SHARED_NEIGHBOR,
                GraphPurpose.CYCLE_CONSTRUCTION,
                minimum_shared_neighbors=1,
                neighbor_count=3,
            ),
        ),
    )


def _loop_policy() -> LoopPhasePolicy:
    return LoopPhasePolicy(
        policy_id="d3-pipeline-continuous-loop-v0.1",
        amplitude_floor=1e-10,
        identifiability_floor=1e-10,
        coherence_floor=0.05,
        branch_margin_radians=0.05,
        integer_residual_tolerance_cycles=1e-8,
    )


def _run_pipeline(
    inputs: CartesianFourierEstimatorInputs,
    *,
    primary_unit_id: str,
) -> _PipelineRun:
    """Run the full observable pipeline without opening its case wrapper."""

    graph_input = GraphInput(
        primary_unit_id=primary_unit_id,
        vertex_ids=inputs.row_ids,
        states=inputs.states,
    )
    execution = build_crossed_graph_execution(
        graph_input=graph_input,
        graph_axes=_graph_axes(),
        oriented_faces=inputs.oriented_faces,
        support_face_indices=rectangular_grid_support_faces(
            grid_side=7,
            x_min=2,
            y_min=2,
            x_max=4,
            y_max=4,
        ),
        domain_id="d3-cartesian-domain",
        cycle_class_spec_id="d3-central-boundary",
        matched_set_id="d3-central-matched",
        refinement_rule=BoundaryRefinementRule(
            rule_id="d3-forward-span-four",
            max_domain_edges_per_graph_edge=4,
        ),
    )
    estimate = estimate_cartesian_fourier_field(
        inputs,
        execution.field_graphs[0],
    )
    primary_unit_sha256 = canonical_json_sha256(
        {
            "domain_version": ("spirallens.pipeline-metamorphic-primary-unit.v0.1"),
            "estimator_input_fingerprint_sha256": inputs.fingerprint_sha256,
            "graph_input_fingerprint_sha256": graph_input.fingerprint_sha256,
            "boundary": "central-2-2-4-4",
        }
    )
    loop_input = build_crossed_blind_loop_input(
        execution,
        estimate,
        cycle_graph_id="d3-b-mutual",
        primary_unit_sha256=primary_unit_sha256,
    )
    loop_prediction = estimate_and_seal_loop(loop_input, _loop_policy())
    if (
        loop_prediction.observed_attempt_status is not AttemptStatus.EVALUABLE
        or loop_prediction.signed_total_cycles is None
    ):
        raise QualificationContractError(
            "development metamorphic loop must be evaluable"
        )
    return _PipelineRun(
        inputs=inputs,
        graph_input=graph_input,
        execution=execution,
        estimate=estimate,
        loop_input=loop_input,
        loop_prediction=loop_prediction,
    )


def _snapshot(
    run: _PipelineRun,
    *,
    loop_input: BlindLoopInput,
    loop_prediction: SealedLoopPrediction,
) -> PipelineSnapshot:
    return PipelineSnapshot(
        estimator_input_fingerprint_sha256=run.inputs.fingerprint_sha256,
        graph_input_fingerprint_sha256=run.graph_input.fingerprint_sha256,
        crossed_execution_fingerprint_sha256=(run.execution.fingerprint_sha256),
        field_graph_fingerprint_sha256=(run.estimate.field_graph_fingerprint_sha256),
        cycle_graph_fingerprint_sha256=(loop_input.cycle_graph_fingerprint_sha256),
        field_estimate_fingerprint_sha256=run.estimate.fingerprint_sha256,
        blind_loop_input_fingerprint_sha256=loop_input.fingerprint_sha256,
        sealed_loop_prediction_fingerprint_sha256=(loop_prediction.fingerprint_sha256),
    )


def _phantom_array_fingerprint(value: object) -> dict[str, object]:
    """Reimplement the public receipt layout; do not import its private helper."""

    array = np.asarray(value)
    descriptor = (
        f"{array.dtype.str}|{','.join(str(item) for item in array.shape)}|"
    ).encode("ascii")
    return {
        "dtype": array.dtype.str,
        "shape": list(array.shape),
        "sha256": hashlib.sha256(descriptor + array.tobytes(order="C")).hexdigest(),
    }


def _content_pseudonym(arrays: dict[str, object]) -> str:
    digest = canonical_json_sha256(
        {
            "domain_version": ("spirallens.cartesian-fourier-label-free-content.v0.1"),
            "observable_array_fingerprints": {
                name: _phantom_array_fingerprint(value)
                for name, value in arrays.items()
            },
        }
    )
    return f"cfi_{digest[:32]}"


def _rebuild_inputs(
    template: CartesianFourierEstimatorInputs,
    *,
    states: object | None = None,
    fit_angles_rad: object | None = None,
    evaluation_angles_rad: object | None = None,
) -> CartesianFourierEstimatorInputs:
    arrays: dict[str, object] = {
        "row_ids": template.row_ids,
        "states": template.states if states is None else states,
        "site_coordinates": template.site_coordinates,
        "oriented_faces": template.oriented_faces,
        "fit_sample_ids": template.fit_sample_ids,
        "fit_angles_rad": (
            template.fit_angles_rad if fit_angles_rad is None else fit_angles_rad
        ),
        "fit_values": template.fit_values,
        "evaluation_sample_ids": template.evaluation_sample_ids,
        "evaluation_angles_rad": (
            template.evaluation_angles_rad
            if evaluation_angles_rad is None
            else evaluation_angles_rad
        ),
        "evaluation_values": template.evaluation_values,
    }
    return CartesianFourierEstimatorInputs(
        input_id=_content_pseudonym(arrays),
        **arrays,  # type: ignore[arg-type]
    )


def _cyclic_signed_permutation(
    dimension: int,
    *,
    shift: int,
    sign_offset: int,
) -> FloatArray:
    matrix = np.zeros((dimension, dimension), dtype="<f8")
    for source in range(dimension):
        target = (source + shift) % dimension
        matrix[source, target] = -1.0 if (source + sign_offset) % 2 else 1.0
    return matrix


def _reference_matrix(handedness: int, offset: float) -> FloatArray:
    cosine = math.cos(offset)
    sine = math.sin(offset)
    return np.asarray(
        (
            (cosine, -float(handedness) * sine),
            (sine, float(handedness) * cosine),
        ),
        dtype="<f8",
    )


def _reference_transform(
    inputs: CartesianFourierEstimatorInputs,
    *,
    handedness: int,
    offset: float,
) -> CartesianFourierEstimatorInputs:
    return _rebuild_inputs(
        inputs,
        fit_angles_rad=(float(handedness) * inputs.fit_angles_rad + offset),
        evaluation_angles_rad=(
            float(handedness) * inputs.evaluation_angles_rad + offset
        ),
    )


def _compose_reference(
    first: tuple[int, float],
    second: tuple[int, float],
) -> tuple[int, float]:
    first_sign, first_offset = first
    second_sign, second_offset = second
    return (
        second_sign * first_sign,
        float(second_sign) * first_offset + second_offset,
    )


def _pairwise_distances(states: FloatArray) -> FloatArray:
    rows = states.shape[0]
    result = np.zeros((rows, rows), dtype="<f8")
    for row in range(rows):
        ordered = np.sort(
            np.abs(states - states[row]),
            axis=1,
            kind="stable",
        )
        result[row] = np.hypot.reduce(
            ordered,
            axis=1,
        )
    return result


def _graph_law(
    base: _PipelineRun,
    transformed: _PipelineRun,
) -> tuple[float, bool, bool]:
    base_distances = _pairwise_distances(base.graph_input.states)
    transformed_distances = _pairwise_distances(transformed.graph_input.states)
    distance_error = _maximum_error(base_distances, transformed_distances)
    graph_pairs = zip(
        (
            *base.execution.field_graphs,
            *base.execution.cycle_graphs,
        ),
        (
            *transformed.execution.field_graphs,
            *transformed.execution.cycle_graphs,
        ),
        strict=True,
    )
    adjacency = True
    edge_distances_bit_identical = np.array_equal(
        base_distances,
        transformed_distances,
    )
    for left, right in graph_pairs:
        adjacency = adjacency and np.array_equal(
            left.canonical_edges,
            right.canonical_edges,
        )
        edge_distances_bit_identical = edge_distances_bit_identical and np.array_equal(
            left.edge_distances,
            right.edge_distances,
        )
    for left_attempt, right_attempt in zip(
        base.execution.cycle_attempts,
        transformed.execution.cycle_attempts,
        strict=True,
    ):
        left_binding = left_attempt.binding
        right_binding = right_attempt.binding
        if left_binding is None or right_binding is None:
            adjacency = False
            continue
        adjacency = (
            adjacency
            and np.array_equal(
                left_binding.graph_cycle_vertex_rows,
                right_binding.graph_cycle_vertex_rows,
            )
            and np.array_equal(
                left_binding.lifted_boundary_offsets,
                right_binding.lifted_boundary_offsets,
            )
            and np.array_equal(
                left_binding.lifted_boundary_arcs,
                right_binding.lifted_boundary_arcs,
            )
        )
    return distance_error, adjacency, edge_distances_bit_identical


def _field_law_error(
    base: CartesianFourierFieldEstimate,
    transformed: CartesianFourierFieldEstimate,
    *,
    reference: FloatArray,
    second_reference: FloatArray,
) -> tuple[float, bool]:
    errors = (
        _maximum_error(
            transformed.fit_section_values,
            base.fit_section_values @ reference.T,
        ),
        _maximum_error(
            transformed.section_values,
            base.section_values @ reference.T,
        ),
        _maximum_error(
            transformed.second_harmonic_values,
            base.second_harmonic_values @ second_reference.T,
        ),
        _maximum_error(transformed.amplitude, base.amplitude),
        _maximum_error(
            transformed.first_harmonic_dominance_ratio,
            base.first_harmonic_dominance_ratio,
        ),
        _maximum_error(
            transformed.edge_coherence,
            base.edge_coherence,
        ),
        _maximum_error(
            transformed.split_disagreement,
            base.split_disagreement,
        ),
    )
    discrete = np.array_equal(
        transformed.support_count, base.support_count
    ) and np.array_equal(transformed.support, base.support)
    return max(errors), discrete


def _loop_law_error(
    base: _PipelineRun,
    transformed: _PipelineRun,
    *,
    expected_sign: int,
) -> tuple[float, bool]:
    left = base.loop_prediction
    right = transformed.loop_prediction
    if (
        left.signed_total_cycles is None
        or right.signed_total_cycles is None
        or left.max_abs_edge_increment_radians is None
        or right.max_abs_edge_increment_radians is None
        or left.nearest_integer_residual_cycles is None
        or right.nearest_integer_residual_cycles is None
    ):
        return math.inf, False
    error = max(
        abs(
            right.signed_total_cycles - float(expected_sign) * left.signed_total_cycles
        ),
        abs(right.max_abs_edge_increment_radians - left.max_abs_edge_increment_radians),
        abs(
            right.nearest_integer_residual_cycles - left.nearest_integer_residual_cycles
        ),
    )
    discrete = (
        left.observed_attempt_status is AttemptStatus.EVALUABLE
        and right.observed_attempt_status is AttemptStatus.EVALUABLE
        and np.array_equal(
            base.loop_input.ordered_loop_rows,
            transformed.loop_input.ordered_loop_rows,
        )
    )
    return error, discrete


def _runs_equivalent(
    left: _PipelineRun,
    right: _PipelineRun,
    *,
    tolerance: float,
) -> bool:
    input_float_fields = (
        "states",
        "site_coordinates",
        "fit_angles_rad",
        "fit_values",
        "evaluation_angles_rad",
        "evaluation_values",
    )
    input_int_fields = (
        "row_ids",
        "oriented_faces",
        "fit_sample_ids",
        "evaluation_sample_ids",
    )
    inputs_equal = all(
        _maximum_error(
            getattr(left.inputs, name),
            getattr(right.inputs, name),
        )
        <= tolerance
        for name in input_float_fields
    ) and all(
        np.array_equal(
            getattr(left.inputs, name),
            getattr(right.inputs, name),
        )
        for name in input_int_fields
    )
    distance_error, adjacency, edge_distances_exact = _graph_law(
        left,
        right,
    )
    field_error, field_discrete = _field_law_error(
        left.estimate,
        right.estimate,
        reference=np.eye(2, dtype="<f8"),
        second_reference=np.eye(2, dtype="<f8"),
    )
    loop_error, loop_discrete = _loop_law_error(
        left,
        right,
        expected_sign=1,
    )
    return (
        inputs_equal
        and distance_error <= tolerance
        and adjacency
        and edge_distances_exact
        and field_error <= tolerance
        and field_discrete
        and loop_error <= tolerance
        and loop_discrete
    )


def _pipeline_law_holds(
    base: _PipelineRun,
    transformed: _PipelineRun,
    *,
    reference: FloatArray,
    second_reference: FloatArray,
    expected_loop_sign: int,
    tolerance: float,
) -> bool:
    distance_error, adjacency, edge_distances_exact = _graph_law(
        base,
        transformed,
    )
    field_error, field_discrete = _field_law_error(
        base.estimate,
        transformed.estimate,
        reference=reference,
        second_reference=second_reference,
    )
    loop_error, loop_discrete = _loop_law_error(
        base,
        transformed,
        expected_sign=expected_loop_sign,
    )
    return (
        distance_error <= tolerance
        and adjacency
        and edge_distances_exact
        and field_error <= tolerance
        and field_discrete
        and loop_error <= tolerance
        and loop_discrete
    )


def _transformation_sha256(
    *,
    law: PipelineMetamorphLaw,
    payload: dict[str, object],
) -> str:
    return canonical_json_sha256(
        {
            "domain_version": ("spirallens.cartesian-pipeline-transformation.v0.1"),
            "law": law.value,
            **payload,
        }
    )


def _make_check(
    *,
    check_id: str,
    law: PipelineMetamorphLaw,
    transformation_sha256: str,
    base: _PipelineRun,
    transformed: _PipelineRun,
    inverse: _PipelineRun,
    composition_sequential: _PipelineRun,
    composition_direct: _PipelineRun,
    expected_loop_sign: int,
    reference: FloatArray,
    second_reference: FloatArray,
    tolerance: float,
    nonidentity: bool,
    inverse_verified: bool,
    composition_verified: bool,
) -> PipelineMetamorphCheck:
    distance_error, adjacency, edge_distances_exact = _graph_law(
        base,
        transformed,
    )
    field_error, field_discrete = _field_law_error(
        base.estimate,
        transformed.estimate,
        reference=reference,
        second_reference=second_reference,
    )
    loop_error, loop_discrete = _loop_law_error(
        base,
        transformed,
        expected_sign=expected_loop_sign,
    )
    field_verified = field_discrete and field_error <= tolerance
    loop_verified = loop_discrete and loop_error <= tolerance
    flags = (
        nonidentity,
        inverse_verified,
        composition_verified,
        adjacency,
        edge_distances_exact,
        field_verified,
        loop_verified,
        True,
    )
    state = (
        QualificationState.PASS
        if all(flags)
        and distance_error <= tolerance
        and field_error <= tolerance
        and loop_error <= tolerance
        else QualificationState.FAIL
    )
    return PipelineMetamorphCheck(
        check_id=check_id,
        law=law,
        state=state,
        transformation_sha256=transformation_sha256,
        base=base.snapshot,
        transformed=transformed.snapshot,
        inverse=inverse.snapshot,
        composition_sequential=composition_sequential.snapshot,
        composition_direct=composition_direct.snapshot,
        expected_loop_orientation_sign=expected_loop_sign,
        maximum_distance_error=distance_error,
        maximum_field_law_error=field_error,
        maximum_loop_law_error=loop_error,
        tolerance=tolerance,
        nonidentity_verified=nonidentity,
        inverse_verified=inverse_verified,
        composition_verified=composition_verified,
        all_graph_adjacencies_verified=adjacency,
        all_graph_edge_distances_bit_identical=edge_distances_exact,
        claim_relevant_field_law_verified=field_verified,
        continuous_loop_law_verified=loop_verified,
        pipeline_rerun_verified=True,
        reason_codes=(
            ("pipeline_transformation_law_verified",)
            if state is QualificationState.PASS
            else ("pipeline_transformation_law_failed",)
        ),
    )


def _ambient_check(
    source: CartesianFourierEstimatorInputs,
    *,
    tolerance: float,
) -> PipelineMetamorphCheck:
    dimension = source.states.shape[1]
    first = _cyclic_signed_permutation(
        dimension,
        shift=3,
        sign_offset=1,
    )
    second = _cyclic_signed_permutation(
        dimension,
        shift=5,
        sign_offset=0,
    )
    base = _run_pipeline(source, primary_unit_id="d3-ambient-pipeline")
    transformed_inputs = _rebuild_inputs(
        source,
        states=source.states @ first,
    )
    transformed = _run_pipeline(
        transformed_inputs,
        primary_unit_id="d3-ambient-pipeline",
    )
    inverse_inputs = _rebuild_inputs(
        transformed_inputs,
        states=transformed_inputs.states @ first.T,
    )
    inverse = _run_pipeline(
        inverse_inputs,
        primary_unit_id="d3-ambient-pipeline",
    )
    sequential_inputs = _rebuild_inputs(
        transformed_inputs,
        states=transformed_inputs.states @ second,
    )
    direct_inputs = _rebuild_inputs(
        source,
        states=source.states @ (first @ second),
    )
    sequential = _run_pipeline(
        sequential_inputs,
        primary_unit_id="d3-ambient-pipeline",
    )
    direct = _run_pipeline(
        direct_inputs,
        primary_unit_id="d3-ambient-pipeline",
    )
    return _make_check(
        check_id="d3-ambient-signed-permutation-pipeline",
        law=PipelineMetamorphLaw.AMBIENT_SIGNED_PERMUTATION,
        transformation_sha256=_transformation_sha256(
            law=PipelineMetamorphLaw.AMBIENT_SIGNED_PERMUTATION,
            payload={
                "first": array_fingerprint(first),
                "second": array_fingerprint(second),
                "row_vector_action": "states-right-multiply",
            },
        ),
        base=base,
        transformed=transformed,
        inverse=inverse,
        composition_sequential=sequential,
        composition_direct=direct,
        expected_loop_sign=1,
        reference=np.eye(2, dtype="<f8"),
        second_reference=np.eye(2, dtype="<f8"),
        tolerance=tolerance,
        nonidentity=(
            transformed.inputs.fingerprint_sha256 != base.inputs.fingerprint_sha256
            and not np.array_equal(first, np.eye(dimension))
        ),
        inverse_verified=_runs_equivalent(
            base,
            inverse,
            tolerance=tolerance,
        ),
        composition_verified=_runs_equivalent(
            sequential,
            direct,
            tolerance=tolerance,
        )
        and _pipeline_law_holds(
            base,
            direct,
            reference=np.eye(2, dtype="<f8"),
            second_reference=np.eye(2, dtype="<f8"),
            expected_loop_sign=1,
            tolerance=tolerance,
        ),
    )


def _reference_check(
    source: CartesianFourierEstimatorInputs,
    *,
    law: PipelineMetamorphLaw,
    handedness: int,
    offset: float,
    tolerance: float,
) -> PipelineMetamorphCheck:
    first = (handedness, offset)
    second = (1, math.pi / 11.0)
    inverse_transform = (handedness, -float(handedness) * offset)
    composed = _compose_reference(first, second)
    base = _run_pipeline(source, primary_unit_id=f"d3-{law.value}-pipeline")
    transformed_inputs = _reference_transform(
        source,
        handedness=first[0],
        offset=first[1],
    )
    transformed = _run_pipeline(
        transformed_inputs,
        primary_unit_id=f"d3-{law.value}-pipeline",
    )
    inverse_inputs = _reference_transform(
        transformed_inputs,
        handedness=inverse_transform[0],
        offset=inverse_transform[1],
    )
    inverse = _run_pipeline(
        inverse_inputs,
        primary_unit_id=f"d3-{law.value}-pipeline",
    )
    sequential_inputs = _reference_transform(
        transformed_inputs,
        handedness=second[0],
        offset=second[1],
    )
    direct_inputs = _reference_transform(
        source,
        handedness=composed[0],
        offset=composed[1],
    )
    sequential = _run_pipeline(
        sequential_inputs,
        primary_unit_id=f"d3-{law.value}-pipeline",
    )
    direct = _run_pipeline(
        direct_inputs,
        primary_unit_id=f"d3-{law.value}-pipeline",
    )
    reference = _reference_matrix(*first)
    second_reference = _reference_matrix(
        first[0],
        2.0 * first[1],
    )
    composed_reference = _reference_matrix(*composed)
    composed_second_reference = _reference_matrix(
        composed[0],
        2.0 * composed[1],
    )
    return _make_check(
        check_id=f"d3-{law.value.replace('_', '-')}-pipeline",
        law=law,
        transformation_sha256=_transformation_sha256(
            law=law,
            payload={
                "handedness": first[0],
                "offset_radians": first[1],
                "reference_matrix": array_fingerprint(reference),
                "second_reference_matrix": array_fingerprint(second_reference),
                "coordinate_action": (
                    "angle-prime-equals-handedness-angle-plus-offset"
                ),
            },
        ),
        base=base,
        transformed=transformed,
        inverse=inverse,
        composition_sequential=sequential,
        composition_direct=direct,
        expected_loop_sign=handedness,
        reference=reference,
        second_reference=second_reference,
        tolerance=tolerance,
        nonidentity=(
            transformed.inputs.fingerprint_sha256 != base.inputs.fingerprint_sha256
            and not np.array_equal(reference, np.eye(2))
        ),
        inverse_verified=_runs_equivalent(
            base,
            inverse,
            tolerance=tolerance,
        ),
        composition_verified=_runs_equivalent(
            sequential,
            direct,
            tolerance=tolerance,
        )
        and _pipeline_law_holds(
            base,
            direct,
            reference=composed_reference,
            second_reference=composed_second_reference,
            expected_loop_sign=composed[0],
            tolerance=tolerance,
        ),
    )


def _reversed_loop(
    source: BlindLoopInput,
    *,
    transform_id: str,
) -> BlindLoopInput:
    rows = np.asarray(source.ordered_loop_rows)[::-1]
    section = np.asarray(source.section_values)[::-1]
    amplitude = np.asarray(source.boundary_amplitude)[::-1]
    identifiability = np.asarray(source.boundary_identifiability_score)[::-1]
    coherence = np.asarray(source.boundary_coherence)[::-1]
    representative_sha256 = canonical_json_sha256(
        {
            "domain_version": ("spirallens.reversed-crossed-representative.v0.1"),
            "base_blind_loop_input_fingerprint_sha256": (source.fingerprint_sha256),
            "base_representative_content_sha256": (
                source.representative_content_sha256
            ),
            "transform_id": transform_id,
            "ordered_loop_rows": array_fingerprint(np.asarray(rows, dtype="<i8")),
        }
    )
    return build_blind_loop_input(
        primary_unit_sha256=source.primary_unit_sha256,
        estimator_input_fingerprint_sha256=(source.estimator_input_fingerprint_sha256),
        field_graph_fingerprint_sha256=(source.field_graph_fingerprint_sha256),
        field_estimate_fingerprint_sha256=(source.field_estimate_fingerprint_sha256),
        cycle_graph_fingerprint_sha256=(source.cycle_graph_fingerprint_sha256),
        cycle_binding_fingerprint_sha256=(source.cycle_binding_fingerprint_sha256),
        representative_content_sha256=representative_sha256,
        ordered_loop_rows=rows,
        section_values=section,
        boundary_amplitude=amplitude,
        boundary_identifiability_score=identifiability,
        boundary_coherence=coherence,
    )


def _loop_reversal_check(
    source: CartesianFourierEstimatorInputs,
    *,
    tolerance: float,
) -> PipelineMetamorphCheck:
    base = _run_pipeline(
        source,
        primary_unit_id="d3-loop-reversal-pipeline",
    )
    transformed_upstream = _run_pipeline(
        source,
        primary_unit_id="d3-loop-reversal-pipeline",
    )
    reversed_input = _reversed_loop(
        transformed_upstream.loop_input,
        transform_id="first-reversal",
    )
    reversed_prediction = estimate_and_seal_loop(
        reversed_input,
        _loop_policy(),
    )
    reversed_run = _PipelineRun(
        inputs=transformed_upstream.inputs,
        graph_input=transformed_upstream.graph_input,
        execution=transformed_upstream.execution,
        estimate=transformed_upstream.estimate,
        loop_input=reversed_input,
        loop_prediction=reversed_prediction,
    )
    inverse_input = _reversed_loop(
        reversed_input,
        transform_id="inverse-reversal",
    )
    inverse_prediction = estimate_and_seal_loop(
        inverse_input,
        _loop_policy(),
    )
    inverse_run = _PipelineRun(
        inputs=transformed_upstream.inputs,
        graph_input=transformed_upstream.graph_input,
        execution=transformed_upstream.execution,
        estimate=transformed_upstream.estimate,
        loop_input=inverse_input,
        loop_prediction=inverse_prediction,
    )
    base_total = base.loop_prediction.signed_total_cycles
    reversed_total = reversed_prediction.signed_total_cycles
    inverse_total = inverse_prediction.signed_total_cycles
    if base_total is None or reversed_total is None or inverse_total is None:
        raise QualificationContractError(
            "loop reversal development control must remain evaluable"
        )
    inverse_verified = (
        np.array_equal(
            inverse_input.ordered_loop_rows,
            base.loop_input.ordered_loop_rows,
        )
        and _maximum_error(
            inverse_input.section_values,
            base.loop_input.section_values,
        )
        <= tolerance
        and abs(inverse_total - base_total) <= tolerance
    )
    distance_error, adjacency, edge_distances_exact = _graph_law(
        base,
        reversed_run,
    )
    field_error, field_discrete = _field_law_error(
        base.estimate,
        reversed_run.estimate,
        reference=np.eye(2, dtype="<f8"),
        second_reference=np.eye(2, dtype="<f8"),
    )
    loop_error = max(
        abs(reversed_total + base_total),
        abs(inverse_total - base_total),
    )
    loop_verified = (
        reversed_prediction.observed_attempt_status is AttemptStatus.EVALUABLE
        and inverse_prediction.observed_attempt_status is AttemptStatus.EVALUABLE
        and loop_error <= tolerance
    )
    nonidentity = (
        reversed_input.fingerprint_sha256 != base.loop_input.fingerprint_sha256
        and not np.array_equal(
            reversed_input.ordered_loop_rows,
            base.loop_input.ordered_loop_rows,
        )
    )
    upstream_rerun = (
        transformed_upstream is not base
        and transformed_upstream.snapshot == base.snapshot
    )
    flags = (
        nonidentity,
        inverse_verified,
        inverse_verified,
        adjacency,
        edge_distances_exact,
        field_discrete and field_error <= tolerance,
        loop_verified,
        upstream_rerun,
    )
    state = (
        QualificationState.PASS
        if all(flags)
        and distance_error <= tolerance
        and field_error <= tolerance
        and loop_error <= tolerance
        else QualificationState.FAIL
    )
    return PipelineMetamorphCheck(
        check_id="d3-loop-reversal-pipeline",
        law=PipelineMetamorphLaw.LOOP_REVERSAL,
        state=state,
        transformation_sha256=_transformation_sha256(
            law=PipelineMetamorphLaw.LOOP_REVERSAL,
            payload={
                "base_exact_crossed_loop_input_sha256": (
                    base.loop_input.fingerprint_sha256
                ),
                "action": "reverse-all-ordered-loop-observable-arrays",
            },
        ),
        base=base.snapshot,
        transformed=reversed_run.snapshot,
        inverse=inverse_run.snapshot,
        composition_sequential=inverse_run.snapshot,
        composition_direct=base.snapshot,
        expected_loop_orientation_sign=-1,
        maximum_distance_error=distance_error,
        maximum_field_law_error=field_error,
        maximum_loop_law_error=loop_error,
        tolerance=tolerance,
        nonidentity_verified=nonidentity,
        inverse_verified=inverse_verified,
        composition_verified=inverse_verified,
        all_graph_adjacencies_verified=adjacency,
        all_graph_edge_distances_bit_identical=edge_distances_exact,
        claim_relevant_field_law_verified=(field_discrete and field_error <= tolerance),
        continuous_loop_law_verified=loop_verified,
        pipeline_rerun_verified=upstream_rerun,
        reason_codes=(
            ("pipeline_transformation_law_verified",)
            if state is QualificationState.PASS
            else ("pipeline_transformation_law_failed",)
        ),
    )


def run_cartesian_pipeline_metamorphic_checks(
    *,
    development_seed: int = PIPELINE_METAMORPHIC_DEVELOPMENT_SEED,
    tolerance: float = PIPELINE_METAMORPHIC_TOLERANCE,
) -> CartesianPipelineMetamorphicReceipt:
    """Run the closed, truth-free Cartesian pipeline metamorphic suite.

    Only the permanent development seed is accepted.  Selection or
    confirmation seeds cannot be routed through this function.
    """

    seed = require_plain_int(
        development_seed,
        label="development_seed",
        minimum=0,
    )
    if seed != PIPELINE_METAMORPHIC_DEVELOPMENT_SEED:
        raise QualificationContractError(
            "only the permanent development seed 314159 is allowed"
        )
    checked_tolerance = require_finite_real(
        tolerance,
        label="tolerance",
        minimum=0.0,
        minimum_inclusive=False,
    )
    if checked_tolerance != PIPELINE_METAMORPHIC_TOLERANCE:
        raise QualificationContractError(
            "tolerance must equal the frozen pipeline metamorphic tolerance"
        )
    spec = CartesianFourierDomainSpec(
        seed=seed,
        grid_side=7,
        ambient_dimension=12,
        samples_per_split=8,
        noise_scale=0.0,
        density_warp_strength=0.0,
    )
    generated = CartesianFourierDomainGenerator().generate(spec)
    # The wrapper's case_id and oracle_truth are deliberately never read.
    source = generated.cases[0].estimator_inputs
    checks = (
        _ambient_check(source, tolerance=checked_tolerance),
        _reference_check(
            source,
            law=PipelineMetamorphLaw.REFERENCE_ROTATION,
            handedness=1,
            offset=math.pi / 7.0,
            tolerance=checked_tolerance,
        ),
        _reference_check(
            source,
            law=PipelineMetamorphLaw.REFERENCE_REFLECTION,
            handedness=-1,
            offset=math.pi / 5.0,
            tolerance=checked_tolerance,
        ),
        _loop_reversal_check(source, tolerance=checked_tolerance),
    )
    rerun = all(check.pipeline_rerun_verified for check in checks)
    state = (
        QualificationState.PASS
        if rerun and all(check.state is QualificationState.PASS for check in checks)
        else QualificationState.FAIL
    )
    return CartesianPipelineMetamorphicReceipt(
        development_seed=seed,
        generator_spec_receipt_sha256=spec.receipt_sha256,
        source_estimator_input_fingerprint_sha256=(source.fingerprint_sha256),
        checks=checks,
        state=state,
        pipeline_rerun_verified=rerun,
    )
