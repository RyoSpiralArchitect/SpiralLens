"""Truth-blind D2 prerequisite kernel and its separate oracle scorer."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import ClassVar

import numpy as np
from numpy.typing import NDArray

from .blind import BlindCoreInput, SealedCorePrediction, _seal_core_prediction
from .common import (
    AttemptStatus,
    CoreDisposition,
    CorePredictionClass,
    EvaluationUnit,
    Int64Array,
    ObligationMode,
    QualificationContractError,
    QualificationState,
    array_fingerprint,
    fingerprint_mapping,
    int64_vector,
    level0_boundary,
    require_enum,
    require_finite_real,
    require_plain_int,
    require_sha256,
    require_slug,
)

CORE_PREREQUISITE_POLICY_VERSION = "spirallens.core-prerequisite-policy.v0.5"
CORE_ORACLE_TRUTH_VERSION = "spirallens.core-oracle-truth.v0.1"
CORE_CASE_EVALUATION_VERSION = "spirallens.core-case-evaluation.v0.1"
CORE_ESTIMATOR_ID = "truth-blind-localized-amplitude-core-v0.3"

REASON_CORE_AMPLITUDE_NOT_LOCALIZED = "amplitude_at_or_below_core_ceiling_not_localized"
REASON_CORE_CONTRAST = "core_to_noncore_amplitude_contrast_below_minimum"
REASON_COHERENCE_FLOOR = "edge_coherence_below_floor"
REASON_EMPTY_GRAPH = "graph_consumption_empty"
REASON_NON_ORIENTABLE = "non_orientable_bundle"
REASON_ORIENTATION_UNRESOLVED = "orientation_unresolved"
REASON_IDENTIFIABILITY_FLOOR = "identifiability_at_or_below_floor"
REASON_SUPPORT_MINIMUM = "support_below_minimum"
REASON_CANDIDATE_MEASUREMENT_SUPPORT = "candidate_measurement_support_below_minimum"

_ORACLE_TRUTH_FACTORY_TOKEN = object()
_CASE_EVALUATION_FACTORY_TOKEN = object()


@dataclass(frozen=True, slots=True)
class CorePrerequisitePolicy:
    """Frozen exact-threshold policy for the in-memory Level-0 kernel."""

    policy_id: str
    core_amplitude_ceiling: float
    identifiability_floor: float
    edge_coherence_floor: float
    minimum_support_count: int
    max_localized_core_fraction: float
    minimum_core_contrast_ratio: float

    receipt_version: ClassVar[str] = CORE_PREREQUISITE_POLICY_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "policy_id",
            require_slug(self.policy_id, label="policy_id"),
        )
        object.__setattr__(
            self,
            "core_amplitude_ceiling",
            require_finite_real(
                self.core_amplitude_ceiling,
                label="core_amplitude_ceiling",
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
            "edge_coherence_floor",
            require_finite_real(
                self.edge_coherence_floor,
                label="edge_coherence_floor",
                minimum=0.0,
                maximum=1.0,
            ),
        )
        object.__setattr__(
            self,
            "minimum_support_count",
            require_plain_int(
                self.minimum_support_count,
                label="minimum_support_count",
                minimum=0,
            ),
        )
        object.__setattr__(
            self,
            "max_localized_core_fraction",
            require_finite_real(
                self.max_localized_core_fraction,
                label="max_localized_core_fraction",
                minimum=0.0,
                maximum=1.0,
                minimum_inclusive=False,
                maximum_inclusive=False,
            ),
        )
        object.__setattr__(
            self,
            "minimum_core_contrast_ratio",
            require_finite_real(
                self.minimum_core_contrast_ratio,
                label="minimum_core_contrast_ratio",
                minimum=1.0,
                minimum_inclusive=False,
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            **level0_boundary(),
            "policy_id": self.policy_id,
            "core_amplitude_ceiling": self.core_amplitude_ceiling,
            "identifiability_floor": self.identifiability_floor,
            "edge_coherence_floor": self.edge_coherence_floor,
            "minimum_support_count": self.minimum_support_count,
            "max_localized_core_fraction": (self.max_localized_core_fraction),
            "minimum_core_contrast_ratio": (self.minimum_core_contrast_ratio),
            "minimum_identifiable_non_core_fraction": (
                1.0 - self.max_localized_core_fraction
            ),
            "threshold_comparison": (
                "localized-same-section-amplitude-at-or-below-ceiling-is-a-"
                "core-candidate;identifiability-coherence-and-support-are-"
                "strict-noncore-measurement-eligibility-floors"
            ),
            "localized_fraction_comparison": ("at_or_below_maximum_is_positive"),
            "localized_core_candidates_excluded_from_non_core_support": True,
            "candidate_measurement_support_checked_independently": True,
            "candidate_direction_identifiability_loss_required": False,
            "exact_zero_direction_undefined_by_normalization": True,
            "identifiability_is_not_a_core_candidate_predicate": True,
            "contrast_rule": (
                "minimum-noncore-amplitude-divided-by-maximum-core-"
                "amplitude-must-meet-ratio;exact-zero-has-infinite-contrast"
            ),
            "argmin_localization_used": False,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return fingerprint_mapping(self.to_dict())


def _core_partition(
    blind_input: BlindCoreInput,
    policy: CorePrerequisitePolicy,
) -> tuple[NDArray[np.bool_], NDArray[np.bool_], bool]:
    below_ceiling = np.asarray(
        blind_input.amplitude <= policy.core_amplitude_ceiling,
        dtype=np.bool_,
    )
    candidate_fraction = below_ceiling.sum() / blind_input.row_ids.shape[0]
    if 0.0 < candidate_fraction <= policy.max_localized_core_fraction:
        core_maximum = float(np.max(blind_input.amplitude[below_ceiling]))
        noncore_minimum = float(np.min(blind_input.amplitude[~below_ceiling]))
        contrast = math.inf if core_maximum == 0.0 else noncore_minimum / core_maximum
        contrast_satisfied = contrast >= policy.minimum_core_contrast_ratio
        if contrast_satisfied:
            candidate_mask = below_ceiling
        else:
            candidate_mask = np.zeros(
                blind_input.row_ids.shape[0],
                dtype=np.bool_,
            )
        support_domain = ~below_ceiling
    else:
        # With no low-amplitude site there is no candidate.  A diffuse
        # low-amplitude set is not localized and is therefore withheld.
        # In both cases, measurement eligibility is assessed only on the
        # complement of the low-amplitude set.
        contrast_satisfied = True
        candidate_mask = np.zeros(
            blind_input.row_ids.shape[0],
            dtype=np.bool_,
        )
        support_domain = ~below_ceiling
    return candidate_mask, support_domain, contrast_satisfied


def _prerequisite_reasons(
    blind_input: BlindCoreInput,
    policy: CorePrerequisitePolicy,
    *,
    candidate_mask: NDArray[np.bool_] | None = None,
    support_domain: NDArray[np.bool_] | None = None,
    contrast_satisfied: bool | None = None,
) -> tuple[str, ...]:
    if support_domain is None:
        candidate_mask, support_domain, contrast_satisfied = _core_partition(
            blind_input,
            policy,
        )
    elif candidate_mask is None:
        candidate_mask = ~support_domain
    if candidate_mask is None:
        raise AssertionError("candidate mask resolution failed")
    if contrast_satisfied is None:
        raise QualificationContractError(
            "contrast_satisfied must accompany an explicit support_domain"
        )
    reasons: set[str] = set()
    if not contrast_satisfied:
        reasons.add(REASON_CORE_CONTRAST)
    low_amplitude_fraction = (
        np.count_nonzero(blind_input.amplitude <= policy.core_amplitude_ceiling)
        / blind_input.row_ids.shape[0]
    )
    if low_amplitude_fraction > policy.max_localized_core_fraction:
        reasons.add(REASON_CORE_AMPLITUDE_NOT_LOCALIZED)
    amplitude_supported = blind_input.amplitude > policy.core_amplitude_ceiling
    identifiability_supported = (
        blind_input.identifiability_score > policy.identifiability_floor
    )
    coherence_supported = blind_input.edge_coherence > policy.edge_coherence_floor
    degree_supported = blind_input.support_counts >= policy.minimum_support_count
    if np.any(candidate_mask & ~degree_supported):
        # A phase-like direction may legitimately lose identifiability at a
        # true zero, but the zero itself still needs independent measurement
        # support.  Otherwise an isolated/missing observation is merely a
        # sparse false-core confounder.
        reasons.add(REASON_CANDIDATE_MEASUREMENT_SUPPORT)
    jointly_identifiable = (
        support_domain
        & amplitude_supported
        & identifiability_supported
        & coherence_supported
        & degree_supported
    )
    identifiable_fraction = (
        np.count_nonzero(jointly_identifiable) / blind_input.row_ids.shape[0]
    )
    required_fraction = 1.0 - policy.max_localized_core_fraction
    if identifiable_fraction < required_fraction:
        if np.any(support_domain & ~identifiability_supported):
            reasons.add(REASON_IDENTIFIABILITY_FLOOR)
        if np.any(support_domain & ~coherence_supported):
            reasons.add(REASON_COHERENCE_FLOOR)
        if np.any(support_domain & ~degree_supported):
            reasons.add(REASON_SUPPORT_MINIMUM)
    if not blind_input.orientation_resolved:
        reasons.add(REASON_ORIENTATION_UNRESOLVED)
    elif blind_input.orientation_preserving is not True:
        reasons.add(REASON_NON_ORIENTABLE)
    if blind_input.graph_edges.shape[0] == 0:
        reasons.add(REASON_EMPTY_GRAPH)
    return tuple(sorted(reasons))


def estimate_and_seal_core(
    blind_input: BlindCoreInput,
    policy: CorePrerequisitePolicy,
) -> SealedCorePrediction:
    """Estimate from amplitudes only, then seal before any oracle access."""

    if not isinstance(blind_input, BlindCoreInput):
        raise TypeError("blind_input must be a BlindCoreInput")
    if not isinstance(policy, CorePrerequisitePolicy):
        raise TypeError("policy must be a CorePrerequisitePolicy")
    candidate_mask, support_domain, contrast_satisfied = _core_partition(
        blind_input,
        policy,
    )
    reasons = _prerequisite_reasons(
        blind_input,
        policy,
        candidate_mask=candidate_mask,
        support_domain=support_domain,
        contrast_satisfied=contrast_satisfied,
    )
    if reasons:
        status = AttemptStatus.INSUFFICIENT
        prediction = CorePredictionClass.ABSTAIN
        candidate_rows = np.asarray([], dtype="<i8")
    else:
        status = AttemptStatus.EVALUABLE
        if np.any(candidate_mask):
            prediction = CorePredictionClass.LOCALIZED_CORE
            candidate_rows = blind_input.row_ids[candidate_mask]
        else:
            prediction = CorePredictionClass.NO_CORE
            candidate_rows = np.asarray([], dtype="<i8")
    return _seal_core_prediction(
        blind_input=blind_input,
        policy_fingerprint_sha256=policy.fingerprint_sha256,
        estimator_id=CORE_ESTIMATOR_ID,
        observed_attempt_status=status,
        prediction_class=prediction,
        reason_codes=reasons,
        candidate_rows=candidate_rows,
    )


@dataclass(frozen=True, slots=True, init=False)
class CoreOracleTruth:
    """Factory-only oracle data that cannot enter the estimator signature."""

    blind_input_fingerprint_sha256: str
    primary_unit_sha256: str
    policy_fingerprint_sha256: str
    truth_id: str
    expected_disposition: CoreDisposition
    anchor_rows: Int64Array
    expected_prerequisite_reasons: tuple[str, ...]
    obligation_mode: ObligationMode
    evaluation_unit: EvaluationUnit
    estimator_input_allowed: bool
    localization_gate_eligible: bool

    receipt_version: ClassVar[str] = CORE_ORACLE_TRUTH_VERSION

    def __init__(
        self,
        *,
        _factory_token: object = None,
        blind_input_fingerprint_sha256: str,
        primary_unit_sha256: str,
        policy_fingerprint_sha256: str,
        truth_id: str,
        expected_disposition: CoreDisposition,
        anchor_rows: NDArray[np.generic],
        expected_prerequisite_reasons: tuple[str, ...],
        obligation_mode: ObligationMode,
        evaluation_unit: EvaluationUnit,
    ) -> None:
        if _factory_token is not _ORACLE_TRUTH_FACTORY_TOKEN:
            raise QualificationContractError(
                "CoreOracleTruth must be produced by build_core_oracle_truth"
            )
        for name, value in (
            (
                "blind_input_fingerprint_sha256",
                blind_input_fingerprint_sha256,
            ),
            ("primary_unit_sha256", primary_unit_sha256),
            ("policy_fingerprint_sha256", policy_fingerprint_sha256),
        ):
            object.__setattr__(
                self,
                name,
                require_sha256(value, label=name),
            )
        object.__setattr__(
            self,
            "truth_id",
            require_slug(truth_id, label="truth_id"),
        )
        disposition = require_enum(
            CoreDisposition,
            expected_disposition,
            label="expected_disposition",
        )
        anchors = int64_vector(
            anchor_rows,
            label="anchor_rows",
            nonempty=False,
        )
        reasons = tuple(expected_prerequisite_reasons)
        if reasons != tuple(sorted(set(reasons))):
            raise QualificationContractError(
                "expected_prerequisite_reasons must be unique and canonical"
            )
        for index, reason in enumerate(reasons):
            require_slug(
                reason,
                label=f"expected_prerequisite_reasons[{index}]",
            )
        if disposition is CoreDisposition.LOCALIZED_CORE:
            if anchors.shape[0] == 0 or reasons:
                raise QualificationContractError(
                    "localized-core truth requires nonempty anchors"
                )
        elif disposition is CoreDisposition.NO_CORE:
            if anchors.shape[0] != 0 or reasons:
                raise QualificationContractError(
                    "no-core truth cannot carry anchors or reasons"
                )
        elif anchors.shape[0] != 0 or not reasons:
            raise QualificationContractError("prerequisite truth requires reasons only")
        object.__setattr__(self, "expected_disposition", disposition)
        object.__setattr__(self, "anchor_rows", anchors)
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
            require_enum(
                EvaluationUnit,
                evaluation_unit,
                label="evaluation_unit",
            ),
        )
        object.__setattr__(self, "estimator_input_allowed", False)
        object.__setattr__(self, "localization_gate_eligible", False)

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            **level0_boundary(),
            "blind_input_fingerprint_sha256": (self.blind_input_fingerprint_sha256),
            "primary_unit_sha256": self.primary_unit_sha256,
            "policy_fingerprint_sha256": self.policy_fingerprint_sha256,
            "truth_id": self.truth_id,
            "expected_disposition": self.expected_disposition.value,
            "anchor_rows": array_fingerprint(self.anchor_rows),
            "expected_prerequisite_reasons": list(self.expected_prerequisite_reasons),
            "obligation_mode": self.obligation_mode.value,
            "evaluation_unit": self.evaluation_unit.value,
            "estimator_input_allowed": self.estimator_input_allowed,
            "localization_gate_eligible": (self.localization_gate_eligible),
        }

    @property
    def fingerprint_sha256(self) -> str:
        return fingerprint_mapping(self.to_dict())


def build_core_oracle_truth(
    *,
    blind_input: BlindCoreInput,
    policy: CorePrerequisitePolicy,
    expected_disposition: CoreDisposition,
    anchor_rows: object,
    expected_prerequisite_reasons: tuple[str, ...],
    obligation_mode: ObligationMode,
    evaluation_unit: EvaluationUnit,
) -> CoreOracleTruth:
    """Build oracle truth separately and bind it to exact input digests."""

    if not isinstance(blind_input, BlindCoreInput):
        raise TypeError("blind_input must be a BlindCoreInput")
    if not isinstance(policy, CorePrerequisitePolicy):
        raise TypeError("policy must be a CorePrerequisitePolicy")
    disposition = require_enum(
        CoreDisposition,
        expected_disposition,
        label="expected_disposition",
    )
    requested = int64_vector(
        anchor_rows,
        label="anchor_rows",
        nonempty=False,
    )
    if len({int(item) for item in requested}) != requested.shape[0]:
        raise QualificationContractError("anchor_rows must be unique")
    requested_set = {int(item) for item in requested}
    row_set = {int(item) for item in blind_input.row_ids}
    if not requested_set.issubset(row_set):
        raise QualificationContractError(
            "anchor_rows must belong to the blind row domain"
        )
    ordered_anchors = blind_input.row_ids[
        np.asarray(
            [int(item) in requested_set for item in blind_input.row_ids],
            dtype=np.bool_,
        )
    ]
    reasons = tuple(expected_prerequisite_reasons)
    truth_content: dict[str, object] = {
        "blind_input_fingerprint_sha256": blind_input.fingerprint_sha256,
        "policy_fingerprint_sha256": policy.fingerprint_sha256,
        "expected_disposition": disposition.value,
        "anchor_rows": array_fingerprint(ordered_anchors),
        "expected_prerequisite_reasons": list(reasons),
        "obligation_mode": require_enum(
            ObligationMode,
            obligation_mode,
            label="obligation_mode",
        ).value,
        "evaluation_unit": require_enum(
            EvaluationUnit,
            evaluation_unit,
            label="evaluation_unit",
        ).value,
    }
    truth_id = f"qct_{fingerprint_mapping(truth_content)[:32]}"
    return CoreOracleTruth(
        _factory_token=_ORACLE_TRUTH_FACTORY_TOKEN,
        blind_input_fingerprint_sha256=blind_input.fingerprint_sha256,
        primary_unit_sha256=blind_input.primary_unit_sha256,
        policy_fingerprint_sha256=policy.fingerprint_sha256,
        truth_id=truth_id,
        expected_disposition=disposition,
        anchor_rows=ordered_anchors,
        expected_prerequisite_reasons=reasons,
        obligation_mode=obligation_mode,
        evaluation_unit=evaluation_unit,
    )


@dataclass(frozen=True, slots=True, init=False)
class CoreCaseEvaluation:
    """Digest-joined result with observed status distinct from gate verdict."""

    prediction_fingerprint_sha256: str
    truth_fingerprint_sha256: str
    blind_input_fingerprint_sha256: str
    policy_fingerprint_sha256: str
    observed_attempt_status: AttemptStatus
    expected_disposition: CoreDisposition
    gate_verdict: QualificationState
    reason_codes: tuple[str, ...]
    exact_anchor_match: bool | None
    obligation_mode: ObligationMode
    evaluation_unit: EvaluationUnit

    receipt_version: ClassVar[str] = CORE_CASE_EVALUATION_VERSION

    def __init__(
        self,
        *,
        _factory_token: object = None,
        prediction_fingerprint_sha256: str,
        truth_fingerprint_sha256: str,
        blind_input_fingerprint_sha256: str,
        policy_fingerprint_sha256: str,
        observed_attempt_status: AttemptStatus,
        expected_disposition: CoreDisposition,
        gate_verdict: QualificationState,
        reason_codes: tuple[str, ...],
        exact_anchor_match: bool | None,
        obligation_mode: ObligationMode,
        evaluation_unit: EvaluationUnit,
    ) -> None:
        if _factory_token is not _CASE_EVALUATION_FACTORY_TOKEN:
            raise QualificationContractError(
                "CoreCaseEvaluation must be produced by score_core_prediction"
            )
        for name, value in (
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
                name,
                require_sha256(value, label=name),
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
                CoreDisposition,
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
        if tuple(reason_codes) != tuple(sorted(set(reason_codes))):
            raise QualificationContractError(
                "reason_codes must be unique and canonical"
            )
        if exact_anchor_match is not None and not isinstance(
            exact_anchor_match,
            (bool, np.bool_),
        ):
            raise QualificationContractError(
                "exact_anchor_match must be boolean or None"
            )
        object.__setattr__(self, "reason_codes", tuple(reason_codes))
        object.__setattr__(
            self,
            "exact_anchor_match",
            None if exact_anchor_match is None else bool(exact_anchor_match),
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
            require_enum(
                EvaluationUnit,
                evaluation_unit,
                label="evaluation_unit",
            ),
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
            "exact_anchor_match": self.exact_anchor_match,
            "obligation_mode": self.obligation_mode.value,
            "evaluation_unit": self.evaluation_unit.value,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return fingerprint_mapping(self.to_dict())


def score_core_prediction(
    prediction: SealedCorePrediction,
    truth: CoreOracleTruth,
) -> CoreCaseEvaluation:
    """Score only after exact digest joins; malformed joins never abstain."""

    if not isinstance(prediction, SealedCorePrediction):
        raise TypeError("prediction must be a SealedCorePrediction")
    if not isinstance(truth, CoreOracleTruth):
        raise TypeError("truth must be a CoreOracleTruth")
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
    exact_match: bool | None = None
    reasons: set[str] = set()
    if status is AttemptStatus.NOT_RUN:
        verdict = QualificationState.NOT_RUN
    elif disposition is CoreDisposition.PREREQUISITE_FAILURE:
        if status is AttemptStatus.INSUFFICIENT:
            if prediction.reason_codes == truth.expected_prerequisite_reasons:
                verdict = QualificationState.PASS
            else:
                verdict = QualificationState.FAIL
                reasons.add("prerequisite_reason_mismatch")
        else:
            verdict = QualificationState.FAIL
            reasons.add("forced_output_on_prerequisite_failure")
    elif status is AttemptStatus.INSUFFICIENT:
        verdict = QualificationState.INSUFFICIENT
        reasons.update(prediction.reason_codes)
    elif disposition is CoreDisposition.LOCALIZED_CORE:
        exact_match = np.array_equal(
            prediction.candidate_rows,
            truth.anchor_rows,
        )
        if (
            prediction.prediction_class is CorePredictionClass.LOCALIZED_CORE
            and exact_match
        ):
            verdict = QualificationState.PASS
        else:
            verdict = QualificationState.FAIL
            reasons.add("positive_anchor_not_recovered")
    else:
        exact_match = prediction.candidate_rows.shape[0] == 0
        if prediction.prediction_class is CorePredictionClass.NO_CORE:
            verdict = QualificationState.PASS
        else:
            verdict = QualificationState.FAIL
            reasons.add("false_core_localization")

    return CoreCaseEvaluation(
        _factory_token=_CASE_EVALUATION_FACTORY_TOKEN,
        prediction_fingerprint_sha256=prediction.fingerprint_sha256,
        truth_fingerprint_sha256=truth.fingerprint_sha256,
        blind_input_fingerprint_sha256=(prediction.blind_input_fingerprint_sha256),
        policy_fingerprint_sha256=prediction.policy_fingerprint_sha256,
        observed_attempt_status=status,
        expected_disposition=disposition,
        gate_verdict=verdict,
        reason_codes=tuple(sorted(reasons)),
        exact_anchor_match=exact_match,
        obligation_mode=truth.obligation_mode,
        evaluation_unit=truth.evaluation_unit,
    )
