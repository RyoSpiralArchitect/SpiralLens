from __future__ import annotations

import math
from dataclasses import fields

import numpy as np
import pytest

from spirallens.qualification.common import (
    AttemptStatus,
    CoreDisposition,
    LoopDisposition,
    LoopPredictionClass,
    QualificationContractError,
    QualificationState,
)
from spirallens.qualification.winding import (
    REASON_BOUNDARY_AMPLITUDE_FLOOR,
    REASON_BRANCH_AMBIGUITY,
    BlindLoopInput,
    LoopPhasePolicy,
    build_blind_loop_input,
    build_loop_oracle_truth,
    estimate_and_seal_loop,
    score_loop_prediction,
)

PRIMARY_DIGEST = "d" * 64


def _policy() -> LoopPhasePolicy:
    return LoopPhasePolicy(
        policy_id="level0-loop-phase",
        amplitude_floor=0.05,
        identifiability_floor=0.2,
        coherence_floor=0.3,
        branch_margin_radians=0.05,
        integer_residual_tolerance_cycles=1e-8,
    )


def _values(q: int, samples: int = 16) -> np.ndarray:
    phase = np.linspace(0.0, 2.0 * math.pi, samples, endpoint=False)
    return np.column_stack((np.cos(q * phase), np.sin(q * phase))).astype("<f8")


def _blind(
    values: np.ndarray,
    *,
    rows: np.ndarray | None = None,
    gap: float = 0.8,
    coherence: float = 0.9,
) -> BlindLoopInput:
    if rows is None:
        rows = np.arange(values.shape[0], dtype="<i8")
    return build_blind_loop_input(
        primary_unit_sha256=PRIMARY_DIGEST,
        estimator_input_fingerprint_sha256="b" * 64,
        field_graph_fingerprint_sha256="c" * 64,
        field_estimate_fingerprint_sha256="d" * 64,
        cycle_graph_fingerprint_sha256="e" * 64,
        cycle_binding_fingerprint_sha256="f" * 64,
        representative_content_sha256="1" * 64,
        ordered_loop_rows=rows,
        section_values=values,
        boundary_amplitude=np.linalg.norm(values, axis=1),
        boundary_identifiability_score=np.full(
            values.shape[0],
            gap,
            dtype="<f8",
        ),
        boundary_coherence=np.full(
            values.shape[0],
            coherence,
            dtype="<f8",
        ),
    )


@pytest.mark.parametrize("q", [2, -2])
def test_signed_q_is_scored_by_exact_sign_and_magnitude(q: int) -> None:
    blind_input = _blind(_values(q))
    policy = _policy()

    prediction = estimate_and_seal_loop(blind_input, policy)
    assert prediction.comparison_tolerance_cycles == (
        policy.integer_residual_tolerance_cycles
    )
    truth = build_loop_oracle_truth(
        blind_input=blind_input,
        policy=policy,
        expected_disposition=LoopDisposition.NONZERO,
        expected_sampled_cycles=q,
        expected_prerequisite_reasons=(),
    )
    evaluation = score_loop_prediction(prediction, truth)

    assert prediction.observed_attempt_status is AttemptStatus.EVALUABLE
    assert prediction.prediction_class is LoopPredictionClass.NONZERO
    assert prediction.signed_total_cycles == pytest.approx(float(q))
    assert isinstance(prediction.signed_total_cycles, float)
    assert evaluation.gate_verdict is QualificationState.PASS
    assert evaluation.sampled_total_match is True


def test_fixed_null_is_the_negative_prediction_class() -> None:
    values = np.tile(np.asarray(((1.0, 0.0),), dtype="<f8"), (8, 1))
    blind_input = _blind(values)
    policy = _policy()

    prediction = estimate_and_seal_loop(blind_input, policy)
    truth = build_loop_oracle_truth(
        blind_input=blind_input,
        policy=policy,
        expected_disposition=LoopDisposition.NULL,
        expected_sampled_cycles=0,
        expected_prerequisite_reasons=(),
    )
    evaluation = score_loop_prediction(prediction, truth)

    assert prediction.prediction_class is LoopPredictionClass.NULL
    assert prediction.signed_total_cycles == 0.0
    assert evaluation.gate_verdict is QualificationState.PASS


def test_wrong_sign_is_a_failure_not_an_insufficient_result() -> None:
    blind_input = _blind(_values(-1))
    policy = _policy()
    prediction = estimate_and_seal_loop(blind_input, policy)
    wrong_truth = build_loop_oracle_truth(
        blind_input=blind_input,
        policy=policy,
        expected_disposition=LoopDisposition.NONZERO,
        expected_sampled_cycles=1,
        expected_prerequisite_reasons=(),
    )

    evaluation = score_loop_prediction(prediction, wrong_truth)

    assert evaluation.observed_attempt_status is AttemptStatus.EVALUABLE
    assert evaluation.gate_verdict is QualificationState.FAIL
    assert evaluation.reason_codes == ("expected_signed_sampled_total_not_recovered",)


def test_loop_reversal_flips_only_the_continuous_signed_total() -> None:
    values = _values(1, samples=12)
    rows = np.arange(values.shape[0], dtype="<i8")
    policy = _policy()
    forward = estimate_and_seal_loop(_blind(values, rows=rows), policy)
    reverse = estimate_and_seal_loop(
        _blind(values[::-1].copy(), rows=rows[::-1].copy()),
        policy,
    )

    assert forward.signed_total_cycles == pytest.approx(1.0)
    assert reverse.signed_total_cycles == pytest.approx(-1.0)
    assert reverse.signed_total_cycles == pytest.approx(-forward.signed_total_cycles)


def test_zero_boundary_is_a_correct_prerequisite_abstention() -> None:
    values = _values(1)
    values[3] = 0.0
    blind_input = _blind(values)
    policy = _policy()

    prediction = estimate_and_seal_loop(blind_input, policy)
    truth = build_loop_oracle_truth(
        blind_input=blind_input,
        policy=policy,
        expected_disposition=LoopDisposition.PREREQUISITE_FAILURE,
        expected_sampled_cycles=None,
        expected_prerequisite_reasons=(REASON_BOUNDARY_AMPLITUDE_FLOOR,),
    )
    evaluation = score_loop_prediction(prediction, truth)

    assert prediction.observed_attempt_status is AttemptStatus.INSUFFICIENT
    assert prediction.prediction_class is LoopPredictionClass.ABSTAIN
    assert prediction.reason_codes == (REASON_BOUNDARY_AMPLITUDE_FLOOR,)
    assert prediction.signed_total_cycles is None
    assert evaluation.gate_verdict is QualificationState.PASS


def test_edge_inside_pi_branch_margin_abstains() -> None:
    phase = np.asarray((0.0, math.pi, math.pi / 2.0), dtype="<f8")
    values = np.column_stack((np.cos(phase), np.sin(phase))).astype("<f8")
    blind_input = _blind(values)
    policy = _policy()

    prediction = estimate_and_seal_loop(blind_input, policy)
    truth = build_loop_oracle_truth(
        blind_input=blind_input,
        policy=policy,
        expected_disposition=LoopDisposition.PREREQUISITE_FAILURE,
        expected_sampled_cycles=None,
        expected_prerequisite_reasons=(REASON_BRANCH_AMBIGUITY,),
    )

    assert prediction.observed_attempt_status is AttemptStatus.INSUFFICIENT
    assert prediction.reason_codes == (REASON_BRANCH_AMBIGUITY,)
    assert prediction.max_abs_edge_increment_radians == pytest.approx(math.pi)
    assert (
        score_loop_prediction(
            prediction,
            truth,
        ).gate_verdict
        is QualificationState.PASS
    )


def test_normal_case_abstention_is_adverse_not_a_pass() -> None:
    values = _values(1)
    values[4] = 0.0
    blind_input = _blind(values)
    policy = _policy()
    prediction = estimate_and_seal_loop(blind_input, policy)
    positive_truth = build_loop_oracle_truth(
        blind_input=blind_input,
        policy=policy,
        expected_disposition=LoopDisposition.NONZERO,
        expected_sampled_cycles=1,
        expected_prerequisite_reasons=(),
    )

    evaluation = score_loop_prediction(prediction, positive_truth)

    assert evaluation.gate_verdict is QualificationState.INSUFFICIENT
    assert evaluation.reason_codes == (REASON_BOUNDARY_AMPLITUDE_FLOOR,)


def test_loop_oracle_uses_caller_supplied_prerequisite_reasons() -> None:
    values = _values(1)
    values[4] = 0.0
    blind_input = _blind(values)
    policy = _policy()
    prediction = estimate_and_seal_loop(blind_input, policy)
    truth = build_loop_oracle_truth(
        blind_input=blind_input,
        policy=policy,
        expected_disposition=LoopDisposition.PREREQUISITE_FAILURE,
        expected_sampled_cycles=None,
        expected_prerequisite_reasons=(REASON_BRANCH_AMBIGUITY,),
    )

    assert truth.expected_prerequisite_reasons == (REASON_BRANCH_AMBIGUITY,)
    evaluation = score_loop_prediction(prediction, truth)
    assert evaluation.gate_verdict is QualificationState.FAIL
    assert evaluation.reason_codes == ("prerequisite_reason_mismatch",)


def test_loop_and_core_truth_types_are_not_interchangeable() -> None:
    blind_input = _blind(_values(1))
    with pytest.raises(TypeError, match="LoopDisposition"):
        build_loop_oracle_truth(
            blind_input=blind_input,
            policy=_policy(),
            expected_disposition=CoreDisposition.LOCALIZED_CORE,  # type: ignore[arg-type]
            expected_sampled_cycles=1,
            expected_prerequisite_reasons=(),
        )


def test_exact_digest_join_rejects_cross_case_tampering() -> None:
    policy = _policy()
    positive = _blind(_values(1))
    null = _blind(np.tile(np.asarray(((1.0, 0.0),), dtype="<f8"), (16, 1)))
    prediction = estimate_and_seal_loop(positive, policy)
    unrelated_truth = build_loop_oracle_truth(
        blind_input=null,
        policy=policy,
        expected_disposition=LoopDisposition.NULL,
        expected_sampled_cycles=0,
        expected_prerequisite_reasons=(),
    )

    with pytest.raises(
        QualificationContractError,
        match="blind input digest join mismatch",
    ):
        score_loop_prediction(prediction, unrelated_truth)


def test_input_and_prediction_expose_no_oracle_or_integer_claim() -> None:
    blind_input = _blind(_values(1))
    prediction = estimate_and_seal_loop(blind_input, _policy())
    forbidden_input_fields = {
        "truth",
        "charge",
        "core",
        "anchor",
        "control",
        "expected",
    }

    assert not forbidden_input_fields.intersection(
        {field.name for field in fields(BlindLoopInput)}
    )
    assert prediction.to_dict()["integer_output_present"] is False
    assert prediction.to_dict()["topology_claimed"] is False
    assert "nearest_integer" not in prediction.to_dict()


def test_same_object_amplitude_mismatch_is_malformed() -> None:
    values = _values(1)
    with pytest.raises(
        QualificationContractError,
        match="same section_values",
    ):
        build_blind_loop_input(
            primary_unit_sha256=PRIMARY_DIGEST,
            estimator_input_fingerprint_sha256="b" * 64,
            field_graph_fingerprint_sha256="c" * 64,
            field_estimate_fingerprint_sha256="d" * 64,
            cycle_graph_fingerprint_sha256="e" * 64,
            cycle_binding_fingerprint_sha256="f" * 64,
            representative_content_sha256="1" * 64,
            ordered_loop_rows=np.arange(values.shape[0], dtype="<i8"),
            section_values=values,
            boundary_amplitude=np.ones(values.shape[0], dtype="<f8") * 2.0,
            boundary_identifiability_score=np.ones(
                values.shape[0],
                dtype="<f8",
            ),
            boundary_coherence=np.ones(values.shape[0], dtype="<f8"),
        )
