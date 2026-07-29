from __future__ import annotations

from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from spirallens.qualification.blind import (
    BlindCoreInput,
    _seal_core_prediction,
    build_blind_core_input,
)
from spirallens.qualification.common import (
    AttemptStatus,
    CoreDisposition,
    CorePredictionClass,
    EvaluationUnit,
    LoopDisposition,
    ObligationMode,
    QualificationContractError,
    QualificationState,
)
from spirallens.qualification.prerequisites import (
    REASON_CANDIDATE_MEASUREMENT_SUPPORT,
    REASON_COHERENCE_FLOOR,
    REASON_CORE_AMPLITUDE_NOT_LOCALIZED,
    REASON_CORE_CONTRAST,
    REASON_EMPTY_GRAPH,
    REASON_IDENTIFIABILITY_FLOOR,
    REASON_NON_ORIENTABLE,
    REASON_ORIENTATION_UNRESOLVED,
    REASON_SUPPORT_MINIMUM,
    CorePrerequisitePolicy,
    build_core_oracle_truth,
    estimate_and_seal_core,
    score_core_prediction,
)

PRIMARY_DIGEST = "a" * 64
ROWS = np.asarray([10, 11, 12, 13], dtype="<i8")
DENSE_EDGES = np.asarray(
    [(10, 11), (10, 13), (11, 12), (12, 13)],
    dtype="<i8",
)


def _policy(
    *,
    core_amplitude_ceiling: float = 0.1,
    identifiability_floor: float = 0.2,
    edge_coherence_floor: float = 0.3,
    minimum_support_count: int = 2,
    max_localized_core_fraction: float = 0.3,
    minimum_core_contrast_ratio: float = 2.0,
) -> CorePrerequisitePolicy:
    return CorePrerequisitePolicy(
        policy_id="level0-core-policy",
        core_amplitude_ceiling=core_amplitude_ceiling,
        identifiability_floor=identifiability_floor,
        edge_coherence_floor=edge_coherence_floor,
        minimum_support_count=minimum_support_count,
        max_localized_core_fraction=max_localized_core_fraction,
        minimum_core_contrast_ratio=minimum_core_contrast_ratio,
    )


def _blind(
    sections: np.ndarray | None = None,
    *,
    gaps: np.ndarray | None = None,
    coherence: np.ndarray | None = None,
    edges: np.ndarray = DENSE_EDGES,
    support: np.ndarray | None = None,
    orientation_resolved: bool = True,
    orientation_preserving: bool | None = True,
    primary_digest: str = PRIMARY_DIGEST,
) -> BlindCoreInput:
    if sections is None:
        sections = np.asarray(
            [(1.0, 0.0), (0.05, 0.0), (1.2, 0.0), (1.3, 0.0)],
            dtype="<f8",
        )
    if gaps is None:
        gaps = np.asarray([0.8, 0.0, 0.8, 0.8], dtype="<f8")
    if coherence is None:
        coherence = np.full(4, 0.9, dtype="<f8")
    if support is None:
        support_map = {int(row): 0 for row in ROWS}
        for left, right in edges:
            support_map[int(left)] += 1
            support_map[int(right)] += 1
        support = np.asarray(
            [support_map[int(row)] for row in ROWS],
            dtype="<i8",
        )
    return build_blind_core_input(
        primary_unit_sha256=primary_digest,
        estimator_input_fingerprint_sha256="b" * 64,
        field_graph_fingerprint_sha256="c" * 64,
        field_estimate_fingerprint_sha256="d" * 64,
        row_ids=ROWS,
        section_values=sections,
        identifiability_score=gaps,
        edge_coherence=coherence,
        support_counts=support,
        orientation_resolved=orientation_resolved,
        orientation_preserving=orientation_preserving,
        graph_edges=edges,
    )


def _truth(
    blind_input: BlindCoreInput,
    policy: CorePrerequisitePolicy,
    disposition: CoreDisposition,
    *,
    anchors: np.ndarray | None = None,
    expected_prerequisite_reasons: tuple[str, ...] = (),
):
    return build_core_oracle_truth(
        blind_input=blind_input,
        policy=policy,
        expected_disposition=disposition,
        anchor_rows=(np.asarray([], dtype="<i8") if anchors is None else anchors),
        expected_prerequisite_reasons=expected_prerequisite_reasons,
        obligation_mode=ObligationMode.INDIVIDUALLY_REQUIRED,
        evaluation_unit=EvaluationUnit.CORE,
    )


def test_charge_blind_estimator_localizes_and_scores_exact_anchor() -> None:
    policy = _policy()
    blind_input = _blind()

    prediction = estimate_and_seal_core(blind_input, policy)
    truth = _truth(
        blind_input,
        policy,
        CoreDisposition.LOCALIZED_CORE,
        anchors=np.asarray([11], dtype="<i8"),
    )
    evaluation = score_core_prediction(prediction, truth)

    assert prediction.observed_attempt_status is AttemptStatus.EVALUABLE
    assert prediction.prediction_class is CorePredictionClass.LOCALIZED_CORE
    assert prediction.candidate_rows.tolist() == [11]
    assert prediction.oracle_read is False
    assert evaluation.observed_attempt_status is AttemptStatus.EVALUABLE
    assert evaluation.gate_verdict is QualificationState.PASS
    assert evaluation.exact_anchor_match is True


def test_off_core_anchor_fails_without_turning_into_insufficient() -> None:
    policy = _policy()
    blind_input = _blind()
    prediction = estimate_and_seal_core(blind_input, policy)
    truth = _truth(
        blind_input,
        policy,
        CoreDisposition.LOCALIZED_CORE,
        anchors=np.asarray([12], dtype="<i8"),
    )

    evaluation = score_core_prediction(prediction, truth)

    assert evaluation.observed_attempt_status is AttemptStatus.EVALUABLE
    assert evaluation.gate_verdict is QualificationState.FAIL
    assert evaluation.reason_codes == ("positive_anchor_not_recovered",)


@pytest.mark.parametrize(
    ("edges", "minimum_support"),
    [
        (DENSE_EDGES, 2),
        (
            np.asarray([(10, 11), (11, 12), (12, 13)], dtype="<i8"),
            0,
        ),
    ],
)
def test_dense_and_sparse_false_cores_fail(
    edges: np.ndarray,
    minimum_support: int,
) -> None:
    policy = _policy(minimum_support_count=minimum_support)
    blind_input = _blind(edges=edges)
    prediction = estimate_and_seal_core(blind_input, policy)
    truth = _truth(
        blind_input,
        policy,
        CoreDisposition.NO_CORE,
    )

    evaluation = score_core_prediction(prediction, truth)

    assert prediction.prediction_class is CorePredictionClass.LOCALIZED_CORE
    assert evaluation.gate_verdict is QualificationState.FAIL
    assert evaluation.reason_codes == ("false_core_localization",)


def test_uniform_high_nonzero_field_is_no_core() -> None:
    policy = _policy()
    sections = np.tile(
        np.asarray(((1.0, 0.0),), dtype="<f8"),
        (4, 1),
    )
    prediction = estimate_and_seal_core(_blind(sections), policy)

    assert prediction.observed_attempt_status is AttemptStatus.EVALUABLE
    assert prediction.prediction_class is CorePredictionClass.NO_CORE
    assert prediction.candidate_rows.shape == (0,)


def test_localized_low_amplitude_is_core_even_if_auxiliary_score_is_high() -> None:
    sections = np.asarray(
        [(1.0, 0.0), (0.0, 0.0), (1.2, 0.0), (1.3, 0.0)],
        dtype="<f8",
    )
    identifiable = np.full(4, 0.8, dtype="<f8")

    prediction = estimate_and_seal_core(
        _blind(sections, gaps=identifiable),
        _policy(),
    )

    assert prediction.observed_attempt_status is AttemptStatus.EVALUABLE
    assert prediction.prediction_class is CorePredictionClass.LOCALIZED_CORE
    assert prediction.reason_codes == ()
    assert prediction.candidate_rows.tolist() == [11]


def test_high_amplitude_local_identifiability_loss_is_not_a_core() -> None:
    sections = np.asarray(
        [(1.0, 0.0), (1.1, 0.0), (1.2, 0.0), (1.3, 0.0)],
        dtype="<f8",
    )
    one_local_loss = np.asarray([0.8, 0.0, 0.8, 0.8], dtype="<f8")

    prediction = estimate_and_seal_core(
        _blind(sections, gaps=one_local_loss),
        _policy(max_localized_core_fraction=0.3),
    )

    assert prediction.observed_attempt_status is AttemptStatus.EVALUABLE
    assert prediction.prediction_class is CorePredictionClass.NO_CORE
    assert prediction.reason_codes == ()
    assert prediction.candidate_rows.shape == (0,)


@pytest.mark.parametrize(
    "amplitudes",
    [
        np.asarray([1.0, 2.0, 3.0, 4.0], dtype="<f8"),
        np.asarray([100.0, 101.0, 102.0, 103.0], dtype="<f8"),
    ],
)
def test_localized_high_argmin_is_not_a_core(
    amplitudes: np.ndarray,
) -> None:
    sections = np.column_stack(
        (amplitudes, np.zeros(amplitudes.shape[0], dtype="<f8"))
    ).astype("<f8")

    prediction = estimate_and_seal_core(_blind(sections), _policy())

    assert prediction.observed_attempt_status is AttemptStatus.EVALUABLE
    assert prediction.prediction_class is CorePredictionClass.NO_CORE
    assert prediction.candidate_rows.shape == (0,)


def test_fixed_null_with_zero_core_is_core_localized() -> None:
    policy = _policy()
    sections = np.asarray(
        [(1.0, 0.0), (0.0, 0.0), (1.2, 0.0), (1.3, 0.0)],
        dtype="<f8",
    )
    gaps = np.asarray([0.8, 0.0, 0.8, 0.8], dtype="<f8")
    coherence = np.asarray([0.9, 0.0, 0.9, 0.9], dtype="<f8")
    blind_input = _blind(
        sections,
        gaps=gaps,
        coherence=coherence,
    )
    prediction = estimate_and_seal_core(blind_input, policy)
    truth = _truth(
        blind_input,
        policy,
        CoreDisposition.LOCALIZED_CORE,
        anchors=np.asarray([11], dtype="<i8"),
    )

    evaluation = score_core_prediction(prediction, truth)

    assert prediction.observed_attempt_status is AttemptStatus.EVALUABLE
    assert prediction.prediction_class is CorePredictionClass.LOCALIZED_CORE
    assert prediction.candidate_rows.tolist() == [11]
    assert evaluation.gate_verdict is QualificationState.PASS


@pytest.mark.parametrize(
    ("sections", "expected_reasons"),
    [
        (
            np.zeros((4, 2), dtype="<f8"),
            (REASON_CORE_AMPLITUDE_NOT_LOCALIZED,),
        ),
        (
            np.asarray(
                [(0.09, 0.0), (0.1, 0.0), (0.1, 0.0), (0.1, 0.0)],
                dtype="<f8",
            ),
            (REASON_CORE_AMPLITUDE_NOT_LOCALIZED,),
        ),
    ],
)
def test_all_zero_and_diffuse_low_fields_abstain(
    sections: np.ndarray,
    expected_reasons: tuple[str, ...],
) -> None:
    prediction = estimate_and_seal_core(_blind(sections), _policy())

    assert prediction.observed_attempt_status is AttemptStatus.INSUFFICIENT
    assert prediction.prediction_class is CorePredictionClass.ABSTAIN
    assert prediction.reason_codes == expected_reasons
    assert prediction.candidate_rows.shape == (0,)


def test_localized_amplitude_at_floor_is_not_prerequisite_failure() -> None:
    floor = 0.1
    policy = _policy(core_amplitude_ceiling=floor)
    exact = np.asarray(
        [(1.0, 0.0), (floor, 0.0), (1.2, 0.0), (1.3, 0.0)],
        dtype="<f8",
    )
    above = exact.copy()
    above[1, 0] = np.nextafter(floor, np.inf)

    exact_prediction = estimate_and_seal_core(_blind(exact), policy)
    above_prediction = estimate_and_seal_core(_blind(above), policy)

    assert exact_prediction.observed_attempt_status is AttemptStatus.EVALUABLE
    assert exact_prediction.prediction_class is (CorePredictionClass.LOCALIZED_CORE)
    assert exact_prediction.candidate_rows.tolist() == [11]
    assert above_prediction.observed_attempt_status is AttemptStatus.EVALUABLE
    assert above_prediction.prediction_class is CorePredictionClass.NO_CORE
    assert above_prediction.candidate_rows.shape == (0,)


def test_localized_but_shallow_low_amplitude_abstains_on_contrast() -> None:
    sections = np.asarray(
        [(0.11, 0.0), (0.1, 0.0), (0.12, 0.0), (0.13, 0.0)],
        dtype="<f8",
    )
    prediction = estimate_and_seal_core(
        _blind(sections),
        _policy(minimum_core_contrast_ratio=2.0),
    )

    assert prediction.observed_attempt_status is AttemptStatus.INSUFFICIENT
    assert prediction.prediction_class is CorePredictionClass.ABSTAIN
    assert REASON_CORE_CONTRAST in prediction.reason_codes


@pytest.mark.parametrize(
    ("field", "expected_reasons"),
    [
        (
            "identifiability_score",
            (REASON_IDENTIFIABILITY_FLOOR,),
        ),
        ("edge_coherence", (REASON_COHERENCE_FLOOR,)),
    ],
)
def test_gap_and_coherence_floors_use_exact_closed_boundary(
    field: str,
    expected_reasons: tuple[str, ...],
) -> None:
    floor = 0.3
    policy = _policy(
        identifiability_floor=floor,
        edge_coherence_floor=floor,
    )
    values = np.asarray([floor, 0.8, floor, floor], dtype="<f8")
    above = values.copy()
    above[[0, 2, 3]] = np.nextafter(floor, np.inf)
    exact_kwargs = {field: values}
    above_kwargs = {field: above}
    if field == "identifiability_score":
        exact_input = _blind(gaps=exact_kwargs[field])
        above_input = _blind(gaps=above_kwargs[field])
    else:
        exact_input = _blind(coherence=exact_kwargs[field])
        above_input = _blind(coherence=above_kwargs[field])

    exact_prediction = estimate_and_seal_core(exact_input, policy)
    above_prediction = estimate_and_seal_core(above_input, policy)

    assert exact_prediction.reason_codes == expected_reasons
    assert above_prediction.observed_attempt_status is AttemptStatus.EVALUABLE


def test_support_minimum_and_localized_fraction_boundaries_are_inclusive() -> None:
    blind_input = _blind()
    at_support = estimate_and_seal_core(
        blind_input,
        _policy(
            minimum_support_count=2,
            max_localized_core_fraction=0.25,
        ),
    )
    below_support = estimate_and_seal_core(
        blind_input,
        _policy(minimum_support_count=3),
    )

    assert at_support.prediction_class is CorePredictionClass.LOCALIZED_CORE
    assert below_support.reason_codes == tuple(
        sorted(
            (
                REASON_CANDIDATE_MEASUREMENT_SUPPORT,
                REASON_SUPPORT_MINIMUM,
            )
        )
    )


def test_low_amplitude_candidate_without_own_measurement_support_abstains() -> None:
    policy = _policy(minimum_support_count=2)
    candidate_isolated_edges = np.asarray(
        [(10, 12), (10, 13), (12, 13)],
        dtype="<i8",
    )
    blind_input = _blind(edges=candidate_isolated_edges)

    prediction = estimate_and_seal_core(blind_input, policy)
    no_core_truth = _truth(
        blind_input,
        policy,
        CoreDisposition.NO_CORE,
    )
    evaluation = score_core_prediction(prediction, no_core_truth)

    assert blind_input.support_counts.tolist() == [2, 0, 2, 2]
    assert prediction.observed_attempt_status is AttemptStatus.INSUFFICIENT
    assert prediction.prediction_class is CorePredictionClass.ABSTAIN
    assert prediction.candidate_rows.shape == (0,)
    assert prediction.reason_codes == (REASON_CANDIDATE_MEASUREMENT_SUPPORT,)
    assert evaluation.gate_verdict is QualificationState.INSUFFICIENT
    assert evaluation.reason_codes == (REASON_CANDIDATE_MEASUREMENT_SUPPORT,)


def test_all_prerequisite_failures_are_reported_canonically() -> None:
    policy = _policy(minimum_support_count=1)
    empty_edges = np.empty((0, 2), dtype="<i8")
    blind_input = _blind(
        np.asarray(
            [(0.1, 0.0), (0.1, 0.0), (0.1, 0.0), (0.1, 0.0)],
            dtype="<f8",
        ),
        gaps=np.full(4, 0.2, dtype="<f8"),
        coherence=np.full(4, 0.3, dtype="<f8"),
        edges=empty_edges,
        support=np.zeros(4, dtype="<i8"),
        orientation_resolved=False,
        orientation_preserving=None,
    )

    prediction = estimate_and_seal_core(blind_input, policy)

    assert prediction.observed_attempt_status is AttemptStatus.INSUFFICIENT
    assert prediction.prediction_class is CorePredictionClass.ABSTAIN
    assert prediction.candidate_rows.shape == (0,)
    assert prediction.reason_codes == tuple(
        sorted(
            (
                REASON_CORE_AMPLITUDE_NOT_LOCALIZED,
                REASON_EMPTY_GRAPH,
                REASON_ORIENTATION_UNRESOLVED,
            )
        )
    )
    assert not np.any(np.isnan(blind_input.amplitude))


def test_non_orientable_reason_is_distinct_from_unresolved() -> None:
    prediction = estimate_and_seal_core(
        _blind(orientation_preserving=False),
        _policy(),
    )

    assert prediction.reason_codes == (REASON_NON_ORIENTABLE,)


def test_expected_prerequisite_passes_but_normal_case_remains_insufficient() -> None:
    policy = _policy()
    sections = np.zeros((4, 2), dtype="<f8")
    blind_input = _blind(sections)
    prediction = estimate_and_seal_core(blind_input, policy)
    prerequisite_truth = _truth(
        blind_input,
        policy,
        CoreDisposition.PREREQUISITE_FAILURE,
        expected_prerequisite_reasons=(REASON_CORE_AMPLITUDE_NOT_LOCALIZED,),
    )
    normal_truth = _truth(
        blind_input,
        policy,
        CoreDisposition.LOCALIZED_CORE,
        anchors=np.asarray([11], dtype="<i8"),
    )

    prerequisite_evaluation = score_core_prediction(
        prediction,
        prerequisite_truth,
    )
    normal_evaluation = score_core_prediction(prediction, normal_truth)

    assert prerequisite_evaluation.observed_attempt_status is (
        AttemptStatus.INSUFFICIENT
    )
    assert prerequisite_evaluation.gate_verdict is QualificationState.PASS
    assert normal_evaluation.observed_attempt_status is AttemptStatus.INSUFFICIENT
    assert normal_evaluation.gate_verdict is QualificationState.INSUFFICIENT


def test_core_oracle_uses_caller_supplied_prerequisite_reasons() -> None:
    policy = _policy()
    blind_input = _blind(np.zeros((4, 2), dtype="<f8"))
    prediction = estimate_and_seal_core(blind_input, policy)
    truth = _truth(
        blind_input,
        policy,
        CoreDisposition.PREREQUISITE_FAILURE,
        expected_prerequisite_reasons=(REASON_EMPTY_GRAPH,),
    )

    assert truth.expected_prerequisite_reasons == (REASON_EMPTY_GRAPH,)
    evaluation = score_core_prediction(prediction, truth)
    assert evaluation.gate_verdict is QualificationState.FAIL
    assert evaluation.reason_codes == ("prerequisite_reason_mismatch",)


def test_core_and_loop_truth_types_are_not_interchangeable() -> None:
    with pytest.raises(TypeError, match="CoreDisposition"):
        _truth(
            _blind(),
            _policy(),
            LoopDisposition.NONZERO,  # type: ignore[arg-type]
            anchors=np.asarray([11], dtype="<i8"),
        )


def test_forced_output_on_expected_prerequisite_is_a_gate_failure() -> None:
    policy = _policy()
    sections = np.zeros((4, 2), dtype="<f8")
    blind_input = _blind(sections)
    forced = _seal_core_prediction(
        blind_input=blind_input,
        policy_fingerprint_sha256=policy.fingerprint_sha256,
        estimator_id="adversarial-forced-output-v0.1",
        observed_attempt_status=AttemptStatus.EVALUABLE,
        prediction_class=CorePredictionClass.LOCALIZED_CORE,
        reason_codes=(),
        candidate_rows=np.asarray([11], dtype="<i8"),
    )
    truth = _truth(
        blind_input,
        policy,
        CoreDisposition.PREREQUISITE_FAILURE,
        expected_prerequisite_reasons=(REASON_CORE_AMPLITUDE_NOT_LOCALIZED,),
    )

    evaluation = score_core_prediction(forced, truth)

    assert evaluation.observed_attempt_status is AttemptStatus.EVALUABLE
    assert evaluation.gate_verdict is QualificationState.FAIL
    assert evaluation.reason_codes == ("forced_output_on_prerequisite_failure",)


def test_charge_sign_and_direction_do_not_change_core_candidate() -> None:
    policy = _policy()
    positive_direction = np.asarray(
        [(1.0, 0.0), (0.03, 0.04), (1.2, 0.0), (1.3, 0.0)],
        dtype="<f8",
    )
    negative_direction = -positive_direction
    positive = estimate_and_seal_core(_blind(positive_direction), policy)
    negative = estimate_and_seal_core(_blind(negative_direction), policy)

    assert positive.candidate_rows.tolist() == negative.candidate_rows.tolist()
    assert positive.prediction_class is negative.prediction_class


def test_malformed_numeric_row_and_graph_inputs_raise_not_insufficient() -> None:
    with pytest.raises(QualificationContractError, match="finite"):
        _blind(
            np.asarray(
                [(1.0, 0.0), (np.nan, 0.0), (1.2, 0.0), (1.3, 0.0)],
                dtype="<f8",
            )
        )
    with pytest.raises(QualificationContractError, match="unique"):
        build_blind_core_input(
            primary_unit_sha256=PRIMARY_DIGEST,
            estimator_input_fingerprint_sha256="b" * 64,
            field_graph_fingerprint_sha256="c" * 64,
            field_estimate_fingerprint_sha256="d" * 64,
            row_ids=np.asarray([10, 10, 12, 13], dtype="<i8"),
            section_values=np.ones((4, 2), dtype="<f8"),
            identifiability_score=np.ones(4, dtype="<f8"),
            edge_coherence=np.ones(4, dtype="<f8"),
            support_counts=np.zeros(4, dtype="<i8"),
            orientation_resolved=True,
            orientation_preserving=True,
            graph_edges=np.empty((0, 2), dtype="<i8"),
        )
    with pytest.raises(QualificationContractError, match="degree"):
        _blind(support=np.ones(4, dtype="<i8"))


def test_digest_join_mismatch_raises_contract_error() -> None:
    policy = _policy()
    first_input = _blind()
    second_input = _blind(primary_digest="b" * 64)
    prediction = estimate_and_seal_core(first_input, policy)
    truth = _truth(
        second_input,
        policy,
        CoreDisposition.LOCALIZED_CORE,
        anchors=np.asarray([11], dtype="<i8"),
    )

    with pytest.raises(QualificationContractError, match="digest join"):
        score_core_prediction(prediction, truth)


@pytest.mark.parametrize("injected_name", ["charge", "anchor", "loop", "oracle"])
def test_blind_factory_rejects_oracle_channel_injection(
    injected_name: str,
) -> None:
    kwargs = {
        "primary_unit_sha256": PRIMARY_DIGEST,
        "estimator_input_fingerprint_sha256": "b" * 64,
        "field_graph_fingerprint_sha256": "c" * 64,
        "field_estimate_fingerprint_sha256": "d" * 64,
        "row_ids": ROWS,
        "section_values": np.ones((4, 2), dtype="<f8"),
        "identifiability_score": np.ones(4, dtype="<f8"),
        "edge_coherence": np.ones(4, dtype="<f8"),
        "support_counts": np.full(4, 2, dtype="<i8"),
        "orientation_resolved": True,
        "orientation_preserving": True,
        "graph_edges": DENSE_EDGES,
        injected_name: 1,
    }
    with pytest.raises(TypeError, match="unexpected keyword"):
        build_blind_core_input(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize("injected_name", ["charge", "anchor", "loop", "oracle"])
def test_estimator_signature_rejects_oracle_channel_injection(
    injected_name: str,
) -> None:
    kwargs = {
        "blind_input": _blind(),
        "policy": _policy(),
        injected_name: 1,
    }
    with pytest.raises(TypeError, match="unexpected keyword"):
        estimate_and_seal_core(**kwargs)  # type: ignore[arg-type]


def test_blind_records_are_immutable_and_direction_free() -> None:
    blind_input = _blind()

    assert not hasattr(blind_input, "section_values")
    assert not hasattr(blind_input, "direction")
    assert blind_input.amplitude.flags.writeable is False
    with pytest.raises(ValueError, match="read-only"):
        blind_input.amplitude[0] = 0.0
    with pytest.raises(FrozenInstanceError):
        blind_input.input_id = "tampered"  # type: ignore[misc]


def test_records_expose_fingerprints_and_level_zero_nonclaims() -> None:
    policy = _policy()
    blind_input = _blind()
    prediction = estimate_and_seal_core(blind_input, policy)
    truth = _truth(
        blind_input,
        policy,
        CoreDisposition.LOCALIZED_CORE,
        anchors=np.asarray([11], dtype="<i8"),
    )
    evaluation = score_core_prediction(prediction, truth)

    assert not hasattr(truth, "supplied_charge")
    assert "supplied_charge" not in truth.to_dict()
    for record in (policy, blind_input, prediction, truth, evaluation):
        payload = record.to_dict()
        assert len(record.fingerprint_sha256) == 64
        assert payload["record_scope"] == "in-memory-fingerprint-only"
        assert payload["persistence_round_trip_supported"] is False
        assert payload["claim_ceiling"] == "level_0"
        assert payload["integer_output_authorized"] is False
        assert payload["topology_claimed"] is False
        assert payload["subject_access_authorized"] is False
        assert payload["semantic_labels_present"] is False
