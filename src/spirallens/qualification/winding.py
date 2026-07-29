"""Truth-blind sampled-phase qualification and its separate oracle scorer.

The estimator in this module observes one ordered representative loop and
returns an unrounded, continuous signed phase total in cycles.  Synthetic
expected outcomes are introduced only after that prediction has been sealed.

This is an in-memory Level-0 numerical qualification kernel.  It does not
produce an integer winding, a topological charge, or a topology certificate.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import ClassVar

import numpy as np
from numpy.typing import NDArray

from .common import (
    AttemptStatus,
    EvaluationUnit,
    FloatArray,
    Int64Array,
    LoopDisposition,
    LoopPredictionClass,
    ObligationMode,
    QualificationContractError,
    QualificationState,
    array_fingerprint,
    fingerprint_mapping,
    float_matrix,
    float_vector,
    int64_vector,
    level0_boundary,
    require_enum,
    require_finite_real,
    require_plain_int,
    require_sha256,
    require_slug,
)
from .metamorphic import sampled_phase_total

BLIND_LOOP_INPUT_VERSION = "spirallens.blind-loop-input.v0.3"
LOOP_PHASE_POLICY_VERSION = "spirallens.loop-phase-policy.v0.3"
SEALED_LOOP_PREDICTION_VERSION = "spirallens.sealed-loop-prediction.v0.1"
LOOP_ORACLE_TRUTH_VERSION = "spirallens.loop-oracle-truth.v0.1"
LOOP_CASE_EVALUATION_VERSION = "spirallens.loop-case-evaluation.v0.1"
LOOP_PHASE_ESTIMATOR_ID = "truth-blind-sampled-phase-total-v0.2"

REASON_BOUNDARY_AMPLITUDE_FLOOR = "boundary_amplitude_at_or_below_floor"
REASON_BOUNDARY_COHERENCE_FLOOR = "boundary_coherence_at_or_below_floor"
REASON_BOUNDARY_IDENTIFIABILITY_FLOOR = "boundary_identifiability_at_or_below_floor"
REASON_BRANCH_AMBIGUITY = "phase_edge_inside_branch_margin"
REASON_LOOP_ROWS_REPEATED = "representative_loop_rows_repeated"
REASON_LOOP_SUPPORT = "representative_loop_has_fewer_than_three_unique_rows"
REASON_PHASE_RESIDUAL = "sampled_phase_total_outside_integer_residual_band"

_BLIND_LOOP_INPUT_FACTORY_TOKEN = object()
_SEALED_LOOP_PREDICTION_FACTORY_TOKEN = object()
_LOOP_ORACLE_TRUTH_FACTORY_TOKEN = object()
_LOOP_CASE_EVALUATION_FACTORY_TOKEN = object()


def _canonical_reasons(value: tuple[str, ...], *, label: str) -> tuple[str, ...]:
    reasons = tuple(value)
    if reasons != tuple(sorted(set(reasons))):
        raise QualificationContractError(
            f"{label} must be unique and in canonical order"
        )
    for index, reason in enumerate(reasons):
        require_slug(reason, label=f"{label}[{index}]")
    return reasons


def _optional_nonnegative_real(value: object, *, label: str) -> float | None:
    if value is None:
        return None
    return require_finite_real(value, label=label, minimum=0.0)


@dataclass(frozen=True, slots=True, init=False)
class BlindLoopInput:
    """Factory-only loop observable with no expected outcome or anchor."""

    primary_unit_sha256: str
    estimator_input_fingerprint_sha256: str
    field_graph_fingerprint_sha256: str
    field_estimate_fingerprint_sha256: str
    cycle_graph_fingerprint_sha256: str
    cycle_binding_fingerprint_sha256: str
    representative_content_sha256: str
    input_id: str
    ordered_loop_rows: Int64Array
    section_values: FloatArray
    boundary_amplitude: FloatArray
    boundary_identifiability_score: FloatArray
    boundary_coherence: FloatArray

    receipt_version: ClassVar[str] = BLIND_LOOP_INPUT_VERSION

    def __init__(
        self,
        *,
        _factory_token: object = None,
        primary_unit_sha256: str,
        estimator_input_fingerprint_sha256: str,
        field_graph_fingerprint_sha256: str,
        field_estimate_fingerprint_sha256: str,
        cycle_graph_fingerprint_sha256: str,
        cycle_binding_fingerprint_sha256: str,
        representative_content_sha256: str,
        input_id: str,
        ordered_loop_rows: NDArray[np.generic],
        section_values: NDArray[np.generic],
        boundary_amplitude: NDArray[np.generic],
        boundary_identifiability_score: NDArray[np.generic],
        boundary_coherence: NDArray[np.generic],
    ) -> None:
        if _factory_token is not _BLIND_LOOP_INPUT_FACTORY_TOKEN:
            raise QualificationContractError(
                "BlindLoopInput must be produced by build_blind_loop_input"
            )
        object.__setattr__(
            self,
            "primary_unit_sha256",
            require_sha256(
                primary_unit_sha256,
                label="primary_unit_sha256",
            ),
        )
        for name, value in (
            (
                "estimator_input_fingerprint_sha256",
                estimator_input_fingerprint_sha256,
            ),
            (
                "field_graph_fingerprint_sha256",
                field_graph_fingerprint_sha256,
            ),
            (
                "field_estimate_fingerprint_sha256",
                field_estimate_fingerprint_sha256,
            ),
            (
                "cycle_graph_fingerprint_sha256",
                cycle_graph_fingerprint_sha256,
            ),
            (
                "cycle_binding_fingerprint_sha256",
                cycle_binding_fingerprint_sha256,
            ),
            (
                "representative_content_sha256",
                representative_content_sha256,
            ),
        ):
            object.__setattr__(
                self,
                name,
                require_sha256(value, label=name),
            )
        object.__setattr__(
            self,
            "input_id",
            require_slug(input_id, label="input_id"),
        )
        object.__setattr__(
            self,
            "ordered_loop_rows",
            int64_vector(ordered_loop_rows, label="ordered_loop_rows"),
        )
        object.__setattr__(
            self,
            "section_values",
            float_matrix(section_values, label="section_values", width=2),
        )
        object.__setattr__(
            self,
            "boundary_amplitude",
            float_vector(boundary_amplitude, label="boundary_amplitude"),
        )
        object.__setattr__(
            self,
            "boundary_identifiability_score",
            float_vector(
                boundary_identifiability_score,
                label="boundary_identifiability_score",
            ),
        )
        object.__setattr__(
            self,
            "boundary_coherence",
            float_vector(boundary_coherence, label="boundary_coherence"),
        )
        row_count = self.ordered_loop_rows.shape[0]
        for label, value in (
            ("section_values", self.section_values),
            ("boundary_amplitude", self.boundary_amplitude),
            (
                "boundary_identifiability_score",
                self.boundary_identifiability_score,
            ),
            ("boundary_coherence", self.boundary_coherence),
        ):
            if value.shape[0] != row_count:
                raise QualificationContractError(
                    f"{label} must align with ordered_loop_rows"
                )

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            **level0_boundary(),
            "primary_unit_sha256": self.primary_unit_sha256,
            "estimator_input_fingerprint_sha256": (
                self.estimator_input_fingerprint_sha256
            ),
            "field_graph_fingerprint_sha256": (self.field_graph_fingerprint_sha256),
            "field_estimate_fingerprint_sha256": (
                self.field_estimate_fingerprint_sha256
            ),
            "cycle_graph_fingerprint_sha256": (self.cycle_graph_fingerprint_sha256),
            "cycle_binding_fingerprint_sha256": (self.cycle_binding_fingerprint_sha256),
            "representative_content_sha256": (self.representative_content_sha256),
            "input_id": self.input_id,
            "input_scope": ("one-ordered-representative-loop-and-boundary-observables"),
            "ordered_loop_rows": array_fingerprint(self.ordered_loop_rows),
            "section_values": array_fingerprint(self.section_values),
            "boundary_amplitude": array_fingerprint(self.boundary_amplitude),
            "boundary_identifiability_score": array_fingerprint(
                self.boundary_identifiability_score
            ),
            "boundary_coherence": array_fingerprint(self.boundary_coherence),
            "same_object_amplitude_and_direction": True,
            "expected_outcome_present": False,
            "integer_output_present": False,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return fingerprint_mapping(self.to_dict())


def build_blind_loop_input(
    *,
    primary_unit_sha256: str,
    estimator_input_fingerprint_sha256: str,
    field_graph_fingerprint_sha256: str,
    field_estimate_fingerprint_sha256: str,
    cycle_graph_fingerprint_sha256: str,
    cycle_binding_fingerprint_sha256: str,
    representative_content_sha256: str,
    ordered_loop_rows: object,
    section_values: object,
    boundary_amplitude: object,
    boundary_identifiability_score: object,
    boundary_coherence: object,
) -> BlindLoopInput:
    """Normalize one label-free representative loop and bind its arrays."""

    primary_digest = require_sha256(
        primary_unit_sha256,
        label="primary_unit_sha256",
    )
    provenance = {
        name: require_sha256(value, label=name)
        for name, value in (
            (
                "estimator_input_fingerprint_sha256",
                estimator_input_fingerprint_sha256,
            ),
            (
                "field_graph_fingerprint_sha256",
                field_graph_fingerprint_sha256,
            ),
            (
                "field_estimate_fingerprint_sha256",
                field_estimate_fingerprint_sha256,
            ),
            (
                "cycle_graph_fingerprint_sha256",
                cycle_graph_fingerprint_sha256,
            ),
            (
                "cycle_binding_fingerprint_sha256",
                cycle_binding_fingerprint_sha256,
            ),
            (
                "representative_content_sha256",
                representative_content_sha256,
            ),
        )
    }
    rows = int64_vector(ordered_loop_rows, label="ordered_loop_rows")
    values = float_matrix(section_values, label="section_values", width=2)
    amplitude = float_vector(
        boundary_amplitude,
        label="boundary_amplitude",
    )
    identifiability = float_vector(
        boundary_identifiability_score,
        label="boundary_identifiability_score",
    )
    coherence = float_vector(
        boundary_coherence,
        label="boundary_coherence",
    )
    row_count = rows.shape[0]
    for label, value in (
        ("section_values", values),
        ("boundary_amplitude", amplitude),
        ("boundary_identifiability_score", identifiability),
        ("boundary_coherence", coherence),
    ):
        if value.shape[0] != row_count:
            raise QualificationContractError(
                f"{label} must align with ordered_loop_rows"
            )
    expected_amplitude = np.linalg.norm(values, axis=1)
    expected_amplitude[expected_amplitude == 0.0] = 0.0
    if not np.array_equal(amplitude, expected_amplitude):
        raise QualificationContractError(
            "boundary_amplitude must derive from the same section_values"
        )
    if np.any(identifiability < 0.0):
        raise QualificationContractError(
            "boundary_identifiability_score must be non-negative"
        )
    if np.any((coherence < 0.0) | (coherence > 1.0)):
        raise QualificationContractError("boundary_coherence must lie in [0, 1]")
    content = {
        "primary_unit_sha256": primary_digest,
        **provenance,
        "ordered_loop_rows": array_fingerprint(rows),
        "section_values": array_fingerprint(values),
        "boundary_amplitude": array_fingerprint(amplitude),
        "boundary_identifiability_score": array_fingerprint(identifiability),
        "boundary_coherence": array_fingerprint(coherence),
    }
    input_id = f"qli_{fingerprint_mapping(content)[:32]}"
    return BlindLoopInput(
        _factory_token=_BLIND_LOOP_INPUT_FACTORY_TOKEN,
        primary_unit_sha256=primary_digest,
        estimator_input_fingerprint_sha256=provenance[
            "estimator_input_fingerprint_sha256"
        ],
        field_graph_fingerprint_sha256=provenance["field_graph_fingerprint_sha256"],
        field_estimate_fingerprint_sha256=provenance[
            "field_estimate_fingerprint_sha256"
        ],
        cycle_graph_fingerprint_sha256=provenance["cycle_graph_fingerprint_sha256"],
        cycle_binding_fingerprint_sha256=provenance["cycle_binding_fingerprint_sha256"],
        representative_content_sha256=provenance["representative_content_sha256"],
        input_id=input_id,
        ordered_loop_rows=rows,
        section_values=values,
        boundary_amplitude=amplitude,
        boundary_identifiability_score=identifiability,
        boundary_coherence=coherence,
    )


@dataclass(frozen=True, slots=True)
class LoopPhasePolicy:
    """Frozen thresholds for one continuous sampled-phase estimate."""

    policy_id: str
    amplitude_floor: float
    identifiability_floor: float
    coherence_floor: float
    branch_margin_radians: float
    integer_residual_tolerance_cycles: float
    nonzero_floor_cycles: float = 0.5

    receipt_version: ClassVar[str] = LOOP_PHASE_POLICY_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "policy_id",
            require_slug(self.policy_id, label="policy_id"),
        )
        object.__setattr__(
            self,
            "amplitude_floor",
            require_finite_real(
                self.amplitude_floor,
                label="amplitude_floor",
                minimum=0.0,
            ),
        )
        object.__setattr__(
            self,
            "identifiability_floor",
            require_finite_real(
                self.identifiability_floor,
                label="identifiability_floor",
                minimum=0.0,
            ),
        )
        object.__setattr__(
            self,
            "coherence_floor",
            require_finite_real(
                self.coherence_floor,
                label="coherence_floor",
                minimum=0.0,
                maximum=1.0,
                maximum_inclusive=False,
            ),
        )
        object.__setattr__(
            self,
            "branch_margin_radians",
            require_finite_real(
                self.branch_margin_radians,
                label="branch_margin_radians",
                minimum=0.0,
                maximum=math.pi,
                minimum_inclusive=False,
                maximum_inclusive=False,
            ),
        )
        object.__setattr__(
            self,
            "integer_residual_tolerance_cycles",
            require_finite_real(
                self.integer_residual_tolerance_cycles,
                label="integer_residual_tolerance_cycles",
                minimum=0.0,
                maximum=0.5,
                maximum_inclusive=False,
            ),
        )
        object.__setattr__(
            self,
            "nonzero_floor_cycles",
            require_finite_real(
                self.nonzero_floor_cycles,
                label="nonzero_floor_cycles",
                minimum=0.0,
                maximum=1.0,
                minimum_inclusive=False,
                maximum_inclusive=False,
            ),
        )
        if self.nonzero_floor_cycles <= self.integer_residual_tolerance_cycles:
            raise QualificationContractError(
                "nonzero_floor_cycles must exceed integer_residual_tolerance_cycles"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            **level0_boundary(),
            "policy_id": self.policy_id,
            "amplitude_floor": self.amplitude_floor,
            "identifiability_floor": self.identifiability_floor,
            "coherence_floor": self.coherence_floor,
            "branch_margin_radians": self.branch_margin_radians,
            "integer_residual_tolerance_cycles": (
                self.integer_residual_tolerance_cycles
            ),
            "nonzero_floor_cycles": self.nonzero_floor_cycles,
            "floor_comparison": "at_or_below_is_insufficient",
            "branch_comparison": "at_or_inside_margin_is_insufficient",
            "sampled_continuous_observable_only": True,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return fingerprint_mapping(self.to_dict())


@dataclass(frozen=True, slots=True, init=False)
class SealedLoopPrediction:
    """Immutable continuous loop estimate sealed before oracle access."""

    blind_input_fingerprint_sha256: str
    primary_unit_sha256: str
    policy_fingerprint_sha256: str
    estimator_id: str
    observed_attempt_status: AttemptStatus
    prediction_class: LoopPredictionClass
    reason_codes: tuple[str, ...]
    signed_total_cycles: float | None
    max_abs_edge_increment_radians: float | None
    nearest_integer_residual_cycles: float | None
    comparison_tolerance_cycles: float
    oracle_read: bool

    receipt_version: ClassVar[str] = SEALED_LOOP_PREDICTION_VERSION

    def __init__(
        self,
        *,
        _factory_token: object = None,
        blind_input_fingerprint_sha256: str,
        primary_unit_sha256: str,
        policy_fingerprint_sha256: str,
        estimator_id: str,
        observed_attempt_status: AttemptStatus,
        prediction_class: LoopPredictionClass,
        reason_codes: tuple[str, ...],
        signed_total_cycles: float | None,
        max_abs_edge_increment_radians: float | None,
        nearest_integer_residual_cycles: float | None,
        comparison_tolerance_cycles: float,
    ) -> None:
        if _factory_token is not _SEALED_LOOP_PREDICTION_FACTORY_TOKEN:
            raise QualificationContractError(
                "SealedLoopPrediction must be produced by the loop estimator"
            )
        for label, value in (
            (
                "blind_input_fingerprint_sha256",
                blind_input_fingerprint_sha256,
            ),
            ("primary_unit_sha256", primary_unit_sha256),
            ("policy_fingerprint_sha256", policy_fingerprint_sha256),
        ):
            object.__setattr__(
                self,
                label,
                require_sha256(value, label=label),
            )
        object.__setattr__(
            self,
            "estimator_id",
            require_slug(estimator_id, label="estimator_id"),
        )
        status = require_enum(
            AttemptStatus,
            observed_attempt_status,
            label="observed_attempt_status",
        )
        predicted = require_enum(
            LoopPredictionClass,
            prediction_class,
            label="prediction_class",
        )
        reasons = _canonical_reasons(reason_codes, label="reason_codes")
        total = (
            None
            if signed_total_cycles is None
            else require_finite_real(
                signed_total_cycles,
                label="signed_total_cycles",
            )
        )
        maximum = _optional_nonnegative_real(
            max_abs_edge_increment_radians,
            label="max_abs_edge_increment_radians",
        )
        residual = _optional_nonnegative_real(
            nearest_integer_residual_cycles,
            label="nearest_integer_residual_cycles",
        )
        if residual is not None and residual > 0.5:
            raise QualificationContractError(
                "nearest_integer_residual_cycles must be at most 0.5"
            )
        comparison_tolerance = require_finite_real(
            comparison_tolerance_cycles,
            label="comparison_tolerance_cycles",
            minimum=0.0,
            maximum=0.5,
            maximum_inclusive=False,
        )
        if status is AttemptStatus.EVALUABLE:
            if (
                predicted
                not in {
                    LoopPredictionClass.NONZERO,
                    LoopPredictionClass.NULL,
                }
                or reasons
                or total is None
                or maximum is None
                or residual is None
            ):
                raise QualificationContractError(
                    "evaluable loop predictions require complete diagnostics"
                )
        elif status is AttemptStatus.INSUFFICIENT:
            if predicted is not LoopPredictionClass.ABSTAIN or not reasons:
                raise QualificationContractError(
                    "insufficient loop predictions must abstain with reasons"
                )
        elif (
            predicted is not LoopPredictionClass.NONE
            or reasons
            or total is not None
            or maximum is not None
            or residual is not None
        ):
            raise QualificationContractError(
                "not-run loop predictions cannot contain observations"
            )
        object.__setattr__(self, "observed_attempt_status", status)
        object.__setattr__(self, "prediction_class", predicted)
        object.__setattr__(self, "reason_codes", reasons)
        object.__setattr__(self, "signed_total_cycles", total)
        object.__setattr__(
            self,
            "max_abs_edge_increment_radians",
            maximum,
        )
        object.__setattr__(
            self,
            "nearest_integer_residual_cycles",
            residual,
        )
        object.__setattr__(
            self,
            "comparison_tolerance_cycles",
            comparison_tolerance,
        )
        object.__setattr__(self, "oracle_read", False)

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            **level0_boundary(),
            "blind_input_fingerprint_sha256": (self.blind_input_fingerprint_sha256),
            "primary_unit_sha256": self.primary_unit_sha256,
            "policy_fingerprint_sha256": self.policy_fingerprint_sha256,
            "estimator_id": self.estimator_id,
            "observed_attempt_status": self.observed_attempt_status.value,
            "prediction_class": self.prediction_class.value,
            "reason_codes": list(self.reason_codes),
            "signed_total_cycles": self.signed_total_cycles,
            "max_abs_edge_increment_radians": (self.max_abs_edge_increment_radians),
            "nearest_integer_residual_cycles": (self.nearest_integer_residual_cycles),
            "comparison_tolerance_cycles": self.comparison_tolerance_cycles,
            "oracle_read": self.oracle_read,
            "sealed_before_oracle_score": True,
            "sampled_continuous_observable_only": True,
            "integer_output_present": False,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return fingerprint_mapping(self.to_dict())


def _static_prerequisite_reasons(
    blind_input: BlindLoopInput,
    policy: LoopPhasePolicy,
) -> tuple[str, ...]:
    reasons: set[str] = set()
    unique_count = len({int(row) for row in blind_input.ordered_loop_rows})
    if unique_count < 3:
        reasons.add(REASON_LOOP_SUPPORT)
    if unique_count != blind_input.ordered_loop_rows.shape[0]:
        reasons.add(REASON_LOOP_ROWS_REPEATED)
    if np.any(blind_input.boundary_amplitude <= policy.amplitude_floor):
        reasons.add(REASON_BOUNDARY_AMPLITUDE_FLOOR)
    if np.any(
        blind_input.boundary_identifiability_score <= policy.identifiability_floor
    ):
        reasons.add(REASON_BOUNDARY_IDENTIFIABILITY_FLOOR)
    if np.any(blind_input.boundary_coherence <= policy.coherence_floor):
        reasons.add(REASON_BOUNDARY_COHERENCE_FLOOR)
    return tuple(sorted(reasons))


def _edge_increments(section_values: FloatArray) -> FloatArray:
    unit = section_values / np.linalg.norm(section_values, axis=1)[:, None]
    following = np.roll(unit, -1, axis=0)
    cross = unit[:, 0] * following[:, 1] - unit[:, 1] * following[:, 0]
    dot = np.einsum("ni,ni->n", unit, following, optimize=False)
    return np.asarray(np.arctan2(cross, dot), dtype="<f8")


def _estimate_loop_observables(
    blind_input: BlindLoopInput,
    policy: LoopPhasePolicy,
) -> tuple[tuple[str, ...], float | None, float | None, float | None]:
    reasons = set(_static_prerequisite_reasons(blind_input, policy))
    if reasons:
        return tuple(sorted(reasons)), None, None, None
    increments = _edge_increments(blind_input.section_values)
    maximum = float(np.max(np.abs(increments)))
    if maximum >= math.pi - policy.branch_margin_radians:
        reasons.add(REASON_BRANCH_AMBIGUITY)
        return tuple(sorted(reasons)), None, maximum, None
    loop_indices = np.arange(
        blind_input.section_values.shape[0],
        dtype="<i8",
    )
    total = sampled_phase_total(blind_input.section_values, loop_indices)
    residual = abs(total - float(np.rint(total)))
    if residual > policy.integer_residual_tolerance_cycles:
        reasons.add(REASON_PHASE_RESIDUAL)
    return tuple(sorted(reasons)), total, maximum, residual


def estimate_and_seal_loop(
    blind_input: BlindLoopInput,
    policy: LoopPhasePolicy,
) -> SealedLoopPrediction:
    """Compute and seal one truth-blind continuous sampled-phase total."""

    if not isinstance(blind_input, BlindLoopInput):
        raise TypeError("blind_input must be a BlindLoopInput")
    if not isinstance(policy, LoopPhasePolicy):
        raise TypeError("policy must be a LoopPhasePolicy")
    reasons, total, maximum, residual = _estimate_loop_observables(
        blind_input,
        policy,
    )
    if reasons:
        status = AttemptStatus.INSUFFICIENT
        prediction_class = LoopPredictionClass.ABSTAIN
    else:
        assert total is not None
        status = AttemptStatus.EVALUABLE
        prediction_class = (
            LoopPredictionClass.NONZERO
            if abs(total) >= policy.nonzero_floor_cycles
            else LoopPredictionClass.NULL
        )
    return SealedLoopPrediction(
        _factory_token=_SEALED_LOOP_PREDICTION_FACTORY_TOKEN,
        blind_input_fingerprint_sha256=blind_input.fingerprint_sha256,
        primary_unit_sha256=blind_input.primary_unit_sha256,
        policy_fingerprint_sha256=policy.fingerprint_sha256,
        estimator_id=LOOP_PHASE_ESTIMATOR_ID,
        observed_attempt_status=status,
        prediction_class=prediction_class,
        reason_codes=reasons,
        signed_total_cycles=total,
        max_abs_edge_increment_radians=maximum,
        nearest_integer_residual_cycles=residual,
        comparison_tolerance_cycles=(policy.integer_residual_tolerance_cycles),
    )


@dataclass(frozen=True, slots=True, init=False)
class LoopOracleTruth:
    """Factory-only expected sampled outcome, unavailable to the estimator."""

    blind_input_fingerprint_sha256: str
    primary_unit_sha256: str
    policy_fingerprint_sha256: str
    truth_id: str
    expected_disposition: LoopDisposition
    expected_sampled_cycles: int | None
    expected_prerequisite_reasons: tuple[str, ...]
    obligation_mode: ObligationMode
    evaluation_unit: EvaluationUnit
    estimator_input_allowed: bool

    receipt_version: ClassVar[str] = LOOP_ORACLE_TRUTH_VERSION

    def __init__(
        self,
        *,
        _factory_token: object = None,
        blind_input_fingerprint_sha256: str,
        primary_unit_sha256: str,
        policy_fingerprint_sha256: str,
        truth_id: str,
        expected_disposition: LoopDisposition,
        expected_sampled_cycles: int | None,
        expected_prerequisite_reasons: tuple[str, ...],
        obligation_mode: ObligationMode,
    ) -> None:
        if _factory_token is not _LOOP_ORACLE_TRUTH_FACTORY_TOKEN:
            raise QualificationContractError(
                "LoopOracleTruth must be produced by build_loop_oracle_truth"
            )
        for label, value in (
            (
                "blind_input_fingerprint_sha256",
                blind_input_fingerprint_sha256,
            ),
            ("primary_unit_sha256", primary_unit_sha256),
            ("policy_fingerprint_sha256", policy_fingerprint_sha256),
        ):
            object.__setattr__(
                self,
                label,
                require_sha256(value, label=label),
            )
        object.__setattr__(
            self,
            "truth_id",
            require_slug(truth_id, label="truth_id"),
        )
        disposition = require_enum(
            LoopDisposition,
            expected_disposition,
            label="expected_disposition",
        )
        expected = (
            None
            if expected_sampled_cycles is None
            else require_plain_int(
                expected_sampled_cycles,
                label="expected_sampled_cycles",
            )
        )
        reasons = _canonical_reasons(
            expected_prerequisite_reasons,
            label="expected_prerequisite_reasons",
        )
        if disposition is LoopDisposition.NONZERO:
            if expected in {None, 0} or reasons:
                raise QualificationContractError(
                    "positive loop truth requires one nonzero expected outcome"
                )
        elif disposition is LoopDisposition.NULL:
            if expected != 0 or reasons:
                raise QualificationContractError(
                    "negative loop truth is the fixed-null outcome zero"
                )
        elif expected is not None or not reasons:
            raise QualificationContractError(
                "prerequisite loop truth requires reasons and no outcome"
            )
        object.__setattr__(self, "expected_disposition", disposition)
        object.__setattr__(self, "expected_sampled_cycles", expected)
        object.__setattr__(
            self,
            "expected_prerequisite_reasons",
            reasons,
        )
        object.__setattr__(
            self,
            "obligation_mode",
            require_enum(
                ObligationMode,
                obligation_mode,
                label="obligation_mode",
            ),
        )
        object.__setattr__(
            self,
            "evaluation_unit",
            EvaluationUnit.BOUNDARY_LOOP,
        )
        object.__setattr__(self, "estimator_input_allowed", False)

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            **level0_boundary(),
            "blind_input_fingerprint_sha256": (self.blind_input_fingerprint_sha256),
            "primary_unit_sha256": self.primary_unit_sha256,
            "policy_fingerprint_sha256": self.policy_fingerprint_sha256,
            "truth_id": self.truth_id,
            "expected_disposition": self.expected_disposition.value,
            "expected_sampled_cycles": self.expected_sampled_cycles,
            "expected_prerequisite_reasons": list(self.expected_prerequisite_reasons),
            "obligation_mode": self.obligation_mode.value,
            "evaluation_unit": self.evaluation_unit.value,
            "estimator_input_allowed": self.estimator_input_allowed,
            "oracle_integer_is_synthetic_expected_sampled_outcome": True,
            "observed_integer_output_present": False,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return fingerprint_mapping(self.to_dict())


def build_loop_oracle_truth(
    *,
    blind_input: BlindLoopInput,
    policy: LoopPhasePolicy,
    expected_disposition: LoopDisposition,
    expected_sampled_cycles: int | None,
    expected_prerequisite_reasons: tuple[str, ...],
    obligation_mode: ObligationMode = ObligationMode.INDIVIDUALLY_REQUIRED,
) -> LoopOracleTruth:
    """Bind evaluator-only expected data to exact input and policy digests."""

    if not isinstance(blind_input, BlindLoopInput):
        raise TypeError("blind_input must be a BlindLoopInput")
    if not isinstance(policy, LoopPhasePolicy):
        raise TypeError("policy must be a LoopPhasePolicy")
    disposition = require_enum(
        LoopDisposition,
        expected_disposition,
        label="expected_disposition",
    )
    expected = (
        None
        if expected_sampled_cycles is None
        else require_plain_int(
            expected_sampled_cycles,
            label="expected_sampled_cycles",
        )
    )
    reasons = tuple(expected_prerequisite_reasons)
    truth_content: dict[str, object] = {
        "blind_input_fingerprint_sha256": blind_input.fingerprint_sha256,
        "primary_unit_sha256": blind_input.primary_unit_sha256,
        "policy_fingerprint_sha256": policy.fingerprint_sha256,
        "expected_disposition": disposition.value,
        "expected_sampled_cycles": expected,
        "expected_prerequisite_reasons": list(reasons),
        "obligation_mode": require_enum(
            ObligationMode,
            obligation_mode,
            label="obligation_mode",
        ).value,
    }
    truth_id = f"qlt_{fingerprint_mapping(truth_content)[:32]}"
    return LoopOracleTruth(
        _factory_token=_LOOP_ORACLE_TRUTH_FACTORY_TOKEN,
        blind_input_fingerprint_sha256=blind_input.fingerprint_sha256,
        primary_unit_sha256=blind_input.primary_unit_sha256,
        policy_fingerprint_sha256=policy.fingerprint_sha256,
        truth_id=truth_id,
        expected_disposition=disposition,
        expected_sampled_cycles=expected,
        expected_prerequisite_reasons=reasons,
        obligation_mode=obligation_mode,
    )


@dataclass(frozen=True, slots=True, init=False)
class LoopCaseEvaluation:
    """Digest-joined loop score with attempt status separate from verdict."""

    prediction_fingerprint_sha256: str
    truth_fingerprint_sha256: str
    blind_input_fingerprint_sha256: str
    policy_fingerprint_sha256: str
    observed_attempt_status: AttemptStatus
    expected_disposition: LoopDisposition
    gate_verdict: QualificationState
    reason_codes: tuple[str, ...]
    sampled_total_match: bool | None
    signed_error_cycles: float | None
    obligation_mode: ObligationMode
    evaluation_unit: EvaluationUnit

    receipt_version: ClassVar[str] = LOOP_CASE_EVALUATION_VERSION

    def __init__(
        self,
        *,
        _factory_token: object = None,
        prediction_fingerprint_sha256: str,
        truth_fingerprint_sha256: str,
        blind_input_fingerprint_sha256: str,
        policy_fingerprint_sha256: str,
        observed_attempt_status: AttemptStatus,
        expected_disposition: LoopDisposition,
        gate_verdict: QualificationState,
        reason_codes: tuple[str, ...],
        sampled_total_match: bool | None,
        signed_error_cycles: float | None,
        obligation_mode: ObligationMode,
    ) -> None:
        if _factory_token is not _LOOP_CASE_EVALUATION_FACTORY_TOKEN:
            raise QualificationContractError(
                "LoopCaseEvaluation must be produced by score_loop_prediction"
            )
        for label, value in (
            ("prediction_fingerprint_sha256", prediction_fingerprint_sha256),
            ("truth_fingerprint_sha256", truth_fingerprint_sha256),
            (
                "blind_input_fingerprint_sha256",
                blind_input_fingerprint_sha256,
            ),
            ("policy_fingerprint_sha256", policy_fingerprint_sha256),
        ):
            object.__setattr__(
                self,
                label,
                require_sha256(value, label=label),
            )
        object.__setattr__(
            self,
            "observed_attempt_status",
            require_enum(
                AttemptStatus,
                observed_attempt_status,
                label="observed_attempt_status",
            ),
        )
        object.__setattr__(
            self,
            "expected_disposition",
            require_enum(
                LoopDisposition,
                expected_disposition,
                label="expected_disposition",
            ),
        )
        object.__setattr__(
            self,
            "gate_verdict",
            require_enum(
                QualificationState,
                gate_verdict,
                label="gate_verdict",
            ),
        )
        object.__setattr__(
            self,
            "reason_codes",
            _canonical_reasons(reason_codes, label="reason_codes"),
        )
        if sampled_total_match is not None and not isinstance(
            sampled_total_match,
            (bool, np.bool_),
        ):
            raise QualificationContractError(
                "sampled_total_match must be boolean or None"
            )
        object.__setattr__(
            self,
            "sampled_total_match",
            None if sampled_total_match is None else bool(sampled_total_match),
        )
        object.__setattr__(
            self,
            "signed_error_cycles",
            (
                None
                if signed_error_cycles is None
                else require_finite_real(
                    signed_error_cycles,
                    label="signed_error_cycles",
                    minimum=0.0,
                )
            ),
        )
        object.__setattr__(
            self,
            "obligation_mode",
            require_enum(
                ObligationMode,
                obligation_mode,
                label="obligation_mode",
            ),
        )
        object.__setattr__(
            self,
            "evaluation_unit",
            EvaluationUnit.BOUNDARY_LOOP,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            **level0_boundary(),
            "prediction_fingerprint_sha256": (self.prediction_fingerprint_sha256),
            "truth_fingerprint_sha256": self.truth_fingerprint_sha256,
            "blind_input_fingerprint_sha256": (self.blind_input_fingerprint_sha256),
            "policy_fingerprint_sha256": self.policy_fingerprint_sha256,
            "observed_attempt_status": self.observed_attempt_status.value,
            "expected_disposition": self.expected_disposition.value,
            "gate_verdict": self.gate_verdict.value,
            "reason_codes": list(self.reason_codes),
            "sampled_total_match": self.sampled_total_match,
            "signed_error_cycles": self.signed_error_cycles,
            "obligation_mode": self.obligation_mode.value,
            "evaluation_unit": self.evaluation_unit.value,
            "sampled_continuous_observable_only": True,
            "integer_output_present": False,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return fingerprint_mapping(self.to_dict())


def score_loop_prediction(
    prediction: SealedLoopPrediction,
    truth: LoopOracleTruth,
) -> LoopCaseEvaluation:
    """Score a sealed prediction only after all exact digest joins pass."""

    if not isinstance(prediction, SealedLoopPrediction):
        raise TypeError("prediction must be a SealedLoopPrediction")
    if not isinstance(truth, LoopOracleTruth):
        raise TypeError("truth must be a LoopOracleTruth")
    for label, predicted, expected in (
        (
            "blind input",
            prediction.blind_input_fingerprint_sha256,
            truth.blind_input_fingerprint_sha256,
        ),
        (
            "primary unit",
            prediction.primary_unit_sha256,
            truth.primary_unit_sha256,
        ),
        (
            "policy",
            prediction.policy_fingerprint_sha256,
            truth.policy_fingerprint_sha256,
        ),
    ):
        if predicted != expected:
            raise QualificationContractError(f"{label} digest join mismatch")

    status = prediction.observed_attempt_status
    disposition = truth.expected_disposition
    reasons: set[str] = set()
    matched: bool | None = None
    error: float | None = None
    if status is AttemptStatus.NOT_RUN:
        verdict = QualificationState.NOT_RUN
    elif disposition is LoopDisposition.PREREQUISITE_FAILURE:
        if (
            status is AttemptStatus.INSUFFICIENT
            and prediction.reason_codes == truth.expected_prerequisite_reasons
        ):
            verdict = QualificationState.PASS
        else:
            verdict = QualificationState.FAIL
            reasons.add(
                "prerequisite_reason_mismatch"
                if status is AttemptStatus.INSUFFICIENT
                else "forced_output_on_prerequisite_failure"
            )
    elif status is AttemptStatus.INSUFFICIENT:
        verdict = QualificationState.INSUFFICIENT
        reasons.update(prediction.reason_codes)
    else:
        assert prediction.signed_total_cycles is not None
        assert truth.expected_sampled_cycles is not None
        error = abs(prediction.signed_total_cycles - truth.expected_sampled_cycles)
        matched = error <= prediction.comparison_tolerance_cycles
        if disposition is LoopDisposition.NONZERO:
            matched = (
                prediction.prediction_class is LoopPredictionClass.NONZERO and matched
            )
            if matched:
                verdict = QualificationState.PASS
            else:
                verdict = QualificationState.FAIL
                reasons.add("expected_signed_sampled_total_not_recovered")
        else:
            matched = (
                prediction.prediction_class is LoopPredictionClass.NULL and matched
            )
            if matched:
                verdict = QualificationState.PASS
            else:
                verdict = QualificationState.FAIL
                reasons.add("false_nonzero_sampled_phase")

    return LoopCaseEvaluation(
        _factory_token=_LOOP_CASE_EVALUATION_FACTORY_TOKEN,
        prediction_fingerprint_sha256=prediction.fingerprint_sha256,
        truth_fingerprint_sha256=truth.fingerprint_sha256,
        blind_input_fingerprint_sha256=(prediction.blind_input_fingerprint_sha256),
        policy_fingerprint_sha256=prediction.policy_fingerprint_sha256,
        observed_attempt_status=status,
        expected_disposition=disposition,
        gate_verdict=verdict,
        reason_codes=tuple(sorted(reasons)),
        sampled_total_match=matched,
        signed_error_cycles=error,
        obligation_mode=truth.obligation_mode,
    )
