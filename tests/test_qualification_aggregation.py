from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from spirallens.qualification.aggregation import (
    REASON_CORE_CANDIDATE_GRAPH_DRIFT,
    REASON_EXPECTED_CELL_NOT_RUN,
    REASON_EXPECTED_CORE_CELL_NOT_RUN,
    REASON_LOOP_TOTAL_GRAPH_DRIFT,
    build_d2_gate,
    build_d4_gate,
    build_d5_gate,
    collapse_core_primary_units,
    collapse_primary_units,
    materialize_expected_cells,
    materialize_expected_core_cells,
    summarize_stratum,
)
from spirallens.qualification.common import (
    AttemptStatus,
    CoreDisposition,
    CorePredictionClass,
    EvaluationUnit,
    LoopDisposition,
    LoopPredictionClass,
    QualificationContractError,
    QualificationState,
)
from spirallens.qualification.contracts import (
    CoreCellSummary,
    CorePrimaryUnitSummary,
    CrossedCellSummary,
    CrossedNonvacuitySummary,
    PrimaryUnitSummary,
    QualificationGateId,
    StratumSummary,
)
from spirallens.qualification.crossed import (
    FieldComponentEffectReceipt,
    FieldGraphPairEffectReceipt,
)
from spirallens.qualification.protocol import (
    CoveragePolicy,
    ExpectedCell,
    ExpectedCoreCell,
    ExpectedStratum,
    LoopRole,
    StressAssignment,
)


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _field_pair_effects(
    *,
    distance: float,
    threshold: float = 1e-6,
) -> tuple[FieldGraphPairEffectReceipt, ...]:
    graph_ids = ("a-one", "a-three", "a-two")
    pairs: list[FieldGraphPairEffectReceipt] = []
    for left_index, left_id in enumerate(graph_ids):
        for right_id in graph_ids[left_index + 1 :]:
            effects = tuple(
                FieldComponentEffectReceipt(
                    component_name=name,
                    rms_distance=distance if name == "section_values" else 0.0,
                    changed_scalar_count=2 if name == "section_values" else 0,
                    effect_eligible=name != "edge_coherence",
                    minimum_effect_distance=threshold,
                    minimum_changed_scalar_count=2,
                    qualifies=name == "section_values" and distance >= threshold,
                )
                for name in (
                    "amplitude",
                    "identifiability_score",
                    "section_values",
                    "edge_coherence",
                )
            )
            qualifying = tuple(
                item.component_name for item in effects if item.qualifies
            )
            pairs.append(
                FieldGraphPairEffectReceipt(
                    left_field_graph_id=left_id,
                    right_field_graph_id=right_id,
                    left_field_graph_fingerprint_sha256=_digest(left_id),
                    right_field_graph_fingerprint_sha256=_digest(right_id),
                    component_effects=effects,
                    qualifying_substantive_components=qualifying,
                    substantive_response_pass=bool(qualifying),
                )
            )
    return tuple(pairs)


def _expected_core(
    cell_id: str,
    *,
    primary_id: str = "unit-a",
    graph_id: str = "a-one",
    disposition: CoreDisposition = CoreDisposition.LOCALIZED_CORE,
    control_id: str = "control-a",
) -> ExpectedCoreCell:
    return ExpectedCoreCell(
        core_cell_id=cell_id,
        primary_unit_id=primary_id,
        selection_seed=101,
        control_id=control_id,
        stress_assignments=(),
        field_graph_id=graph_id,
        expected_core_disposition=disposition,
    )


def _core_cell(
    expected: ExpectedCoreCell,
    *,
    difference_rows: tuple[int, ...] = (),
    prediction: CorePredictionClass | None = None,
    status: AttemptStatus = AttemptStatus.EVALUABLE,
    state: QualificationState | None = None,
    anchor_fingerprint: str | None = None,
) -> CoreCellSummary:
    if status is AttemptStatus.NOT_RUN:
        return CoreCellSummary(
            core_cell_id=expected.core_cell_id,
            primary_unit_id=expected.primary_unit_id,
            field_graph_id=expected.field_graph_id,
            expected_disposition=expected.expected_core_disposition,
            field_graph_fingerprint_sha256=None,
            field_estimate_fingerprint_sha256=None,
            blind_input_fingerprint_sha256=None,
            prediction_fingerprint_sha256=None,
            oracle_fingerprint_sha256=None,
            candidate_fingerprint_sha256=None,
            oracle_anchor_fingerprint_sha256=None,
            candidate_anchor_symmetric_difference_rows=(),
            attempt_status=AttemptStatus.NOT_RUN,
            prediction_class=CorePredictionClass.NONE,
            state=QualificationState.NOT_RUN,
            reason_codes=("not-run",),
        )
    if prediction is None:
        prediction = {
            CoreDisposition.LOCALIZED_CORE: CorePredictionClass.LOCALIZED_CORE,
            CoreDisposition.NO_CORE: CorePredictionClass.NO_CORE,
            CoreDisposition.PREREQUISITE_FAILURE: CorePredictionClass.ABSTAIN,
        }[expected.expected_core_disposition]
    if state is None:
        if status is AttemptStatus.INSUFFICIENT:
            state = (
                QualificationState.PASS
                if expected.expected_core_disposition
                is CoreDisposition.PREREQUISITE_FAILURE
                else QualificationState.INSUFFICIENT
            )
        else:
            expected_prediction = {
                CoreDisposition.LOCALIZED_CORE: (CorePredictionClass.LOCALIZED_CORE),
                CoreDisposition.NO_CORE: CorePredictionClass.NO_CORE,
                CoreDisposition.PREREQUISITE_FAILURE: None,
            }[expected.expected_core_disposition]
            state = (
                QualificationState.PASS
                if prediction is expected_prediction and not difference_rows
                else QualificationState.FAIL
            )
    return CoreCellSummary(
        core_cell_id=expected.core_cell_id,
        primary_unit_id=expected.primary_unit_id,
        field_graph_id=expected.field_graph_id,
        expected_disposition=expected.expected_core_disposition,
        field_graph_fingerprint_sha256=_digest(f"{expected.core_cell_id}-graph"),
        field_estimate_fingerprint_sha256=_digest(f"{expected.core_cell_id}-field"),
        blind_input_fingerprint_sha256=_digest(f"{expected.core_cell_id}-input"),
        prediction_fingerprint_sha256=_digest(f"{expected.core_cell_id}-prediction"),
        oracle_fingerprint_sha256=_digest(f"{expected.core_cell_id}-oracle"),
        candidate_fingerprint_sha256=_digest(f"{expected.core_cell_id}-candidate"),
        oracle_anchor_fingerprint_sha256=(
            anchor_fingerprint or _digest(f"{expected.primary_unit_id}-anchor")
        ),
        candidate_anchor_symmetric_difference_rows=difference_rows,
        attempt_status=status,
        prediction_class=prediction,
        state=state,
        reason_codes=() if state is QualificationState.PASS else ("core-nonpass",),
    )


def _core_template(
    expected: tuple[ExpectedCoreCell, ...],
    *,
    disposition: CoreDisposition | None = None,
) -> CorePrimaryUnitSummary:
    first = expected[0]
    return CorePrimaryUnitSummary(
        primary_unit_id=first.primary_unit_id,
        selection_seed=first.selection_seed,
        control_id=first.control_id,
        expected_disposition=(
            first.expected_core_disposition if disposition is None else disposition
        ),
        stress_assignments=first.stress_assignments,
        d2_scientific_input_fingerprint_sha256=_digest(
            f"{first.primary_unit_id}-scientific-input"
        ),
        domain_instance_fingerprint_sha256=_digest(f"{first.primary_unit_id}-domain"),
        support_instance_fingerprint_sha256=_digest(f"{first.primary_unit_id}-support"),
        attempt_status=AttemptStatus.EVALUABLE,
        prediction_class=CorePredictionClass.LOCALIZED_CORE,
        state=QualificationState.PASS,
        max_candidate_symmetric_difference_rows=0,
        reason_codes=(),
        core_cell_ids=tuple(cell.core_cell_id for cell in expected),
    )


def _expected_loop(
    cell_id: str,
    *,
    primary_id: str = "unit-a",
    field_graph_id: str = "a-one",
    cycle_graph_id: str = "b-one",
    role: LoopRole = LoopRole.PRIMARY_BOUNDARY,
    disposition: LoopDisposition = LoopDisposition.NONZERO,
    control_id: str = "control-a",
) -> ExpectedCell:
    return ExpectedCell(
        cell_id=cell_id,
        primary_unit_id=primary_id,
        selection_seed=101,
        control_id=control_id,
        stress_assignments=(),
        field_graph_id=field_graph_id,
        cycle_graph_id=cycle_graph_id,
        loop_role=role,
        expected_loop_disposition=disposition,
        stratum_ids=("all",),
    )


def _loop_cell(
    expected: ExpectedCell,
    *,
    total: float = 1.0,
    prediction: LoopPredictionClass | None = None,
    status: AttemptStatus = AttemptStatus.EVALUABLE,
    state: QualificationState | None = None,
    error: float = 0.0,
    reason_codes: tuple[str, ...] | None = None,
) -> CrossedCellSummary:
    if status is AttemptStatus.NOT_RUN:
        return CrossedCellSummary(
            cell_id=expected.cell_id,
            primary_unit_id=expected.primary_unit_id,
            field_graph_id=expected.field_graph_id,
            cycle_graph_id=expected.cycle_graph_id,
            loop_role=expected.loop_role,
            expected_disposition=expected.expected_loop_disposition,
            field_graph_fingerprint_sha256=None,
            cycle_graph_fingerprint_sha256=None,
            field_estimate_fingerprint_sha256=None,
            cycle_binding_fingerprint_sha256=None,
            representative_content_sha256=None,
            blind_input_fingerprint_sha256=None,
            prediction_fingerprint_sha256=None,
            oracle_fingerprint_sha256=None,
            attempt_status=AttemptStatus.NOT_RUN,
            prediction_class=LoopPredictionClass.NONE,
            state=QualificationState.NOT_RUN,
            continuous_signed_total_cycles=None,
            oracle_absolute_error_cycles=None,
            reason_codes=("not-run",),
        )
    if status is AttemptStatus.INSUFFICIENT:
        prediction = LoopPredictionClass.ABSTAIN
        total_value = None
        error_value = None
        if state is None:
            state = (
                QualificationState.PASS
                if expected.expected_loop_disposition
                is LoopDisposition.PREREQUISITE_FAILURE
                else QualificationState.INSUFFICIENT
            )
    else:
        if prediction is None:
            prediction = {
                LoopDisposition.NONZERO: LoopPredictionClass.NONZERO,
                LoopDisposition.NULL: LoopPredictionClass.NULL,
                LoopDisposition.PREREQUISITE_FAILURE: LoopPredictionClass.NONZERO,
            }[expected.expected_loop_disposition]
        total_value = total
        error_value = error
        if state is None:
            expected_prediction = {
                LoopDisposition.NONZERO: LoopPredictionClass.NONZERO,
                LoopDisposition.NULL: LoopPredictionClass.NULL,
                LoopDisposition.PREREQUISITE_FAILURE: None,
            }[expected.expected_loop_disposition]
            state = (
                QualificationState.PASS
                if prediction is expected_prediction and error == 0.0
                else QualificationState.FAIL
            )
    return CrossedCellSummary(
        cell_id=expected.cell_id,
        primary_unit_id=expected.primary_unit_id,
        field_graph_id=expected.field_graph_id,
        cycle_graph_id=expected.cycle_graph_id,
        loop_role=expected.loop_role,
        expected_disposition=expected.expected_loop_disposition,
        field_graph_fingerprint_sha256=_digest(f"{expected.cell_id}-a"),
        cycle_graph_fingerprint_sha256=_digest(f"{expected.cell_id}-b"),
        field_estimate_fingerprint_sha256=_digest(f"{expected.cell_id}-field"),
        cycle_binding_fingerprint_sha256=_digest(f"{expected.cell_id}-cycle"),
        representative_content_sha256=_digest(f"{expected.cell_id}-content"),
        blind_input_fingerprint_sha256=_digest(f"{expected.cell_id}-input"),
        prediction_fingerprint_sha256=_digest(f"{expected.cell_id}-prediction"),
        oracle_fingerprint_sha256=_digest(f"{expected.cell_id}-oracle"),
        attempt_status=status,
        prediction_class=prediction,
        state=state,
        continuous_signed_total_cycles=total_value,
        oracle_absolute_error_cycles=error_value,
        reason_codes=(
            reason_codes
            if reason_codes is not None
            else (() if state is QualificationState.PASS else ("loop-nonpass",))
        ),
    )


def _loop_template(
    expected: tuple[ExpectedCell, ...],
) -> PrimaryUnitSummary:
    first = expected[0]
    disposition = next(
        cell.expected_loop_disposition
        for cell in expected
        if cell.loop_role is LoopRole.PRIMARY_BOUNDARY
    )
    return PrimaryUnitSummary(
        primary_unit_id=first.primary_unit_id,
        selection_seed=first.selection_seed,
        control_id=first.control_id,
        expected_disposition=disposition,
        stress_assignments=first.stress_assignments,
        domain_instance_fingerprint_sha256=_digest(f"{first.primary_unit_id}-domain"),
        support_instance_fingerprint_sha256=_digest(f"{first.primary_unit_id}-support"),
        attempt_status=AttemptStatus.EVALUABLE,
        prediction_class=(
            LoopPredictionClass.NONZERO
            if disposition is LoopDisposition.NONZERO
            else LoopPredictionClass.NULL
        ),
        state=QualificationState.PASS,
        continuous_total_span_cycles=0.0,
        reason_codes=(),
        crossed_cell_ids=tuple(cell.cell_id for cell in expected),
    )


def _policy() -> CoveragePolicy:
    return CoveragePolicy(
        evaluation_unit=EvaluationUnit.PHANTOM_INSTANCE,
        minimum_coverage=1.0,
        maximum_abstention_fraction=0.0,
        minimum_recall=1.0,
        minimum_specificity=1.0,
    )


def _nonvacuity(
    primary_id: str,
    *,
    control_id: str = "control-a",
    sentinel: bool = False,
    status: AttemptStatus = AttemptStatus.EVALUABLE,
) -> CrossedNonvacuitySummary:
    if status is AttemptStatus.NOT_RUN:
        return CrossedNonvacuitySummary(
            primary_unit_id=primary_id,
            control_id=control_id,
            attempt_status=status,
            receipt_fingerprint_sha256=None,
            state=QualificationState.NOT_RUN,
            substantive_output_variation_required=sentinel,
            field_adjacency_variant_count=0,
            cycle_adjacency_variant_count=0,
            field_consumption_variant_count=0,
            field_output_variant_count=0,
            maximum_pairwise_substantive_output_distance=None,
            minimum_substantive_output_distance=1e-6,
            field_graph_pair_effects=(),
            substantive_response_field_graph_ids=(),
            substantive_response_field_graph_count=0,
            required_substantive_response_field_graph_count=3,
            matched_cycle_count=0,
            representative_content_variant_count=0,
            minimum_representative_content_variants=2,
            reason_codes=("crossed-nonvacuity-not-run",),
        )
    pair_effects = _field_pair_effects(distance=0.02 if sentinel else 0.0)
    response_ids = ("a-one", "a-three", "a-two") if sentinel else ()
    return CrossedNonvacuitySummary(
        primary_unit_id=primary_id,
        control_id=control_id,
        attempt_status=status,
        receipt_fingerprint_sha256=_digest(f"{primary_id}-nonvacuity"),
        state=QualificationState.PASS,
        substantive_output_variation_required=sentinel,
        field_adjacency_variant_count=3,
        cycle_adjacency_variant_count=3,
        field_consumption_variant_count=3,
        field_output_variant_count=3 if sentinel else 1,
        maximum_pairwise_substantive_output_distance=0.02 if sentinel else 0.0,
        minimum_substantive_output_distance=1e-6,
        field_graph_pair_effects=pair_effects,
        substantive_response_field_graph_ids=response_ids,
        substantive_response_field_graph_count=len(response_ids),
        required_substantive_response_field_graph_count=3,
        matched_cycle_count=3,
        representative_content_variant_count=3,
        minimum_representative_content_variants=2,
        reason_codes=(),
    )


def _complete_loop_manifest(
    *,
    primary_id: str,
    disposition: LoopDisposition,
    control_id: str,
    field_graph_ids: tuple[str, ...] = ("a-one",),
) -> tuple[ExpectedCell, ...]:
    return tuple(
        sorted(
            (
                _expected_loop(
                    f"{primary_id}-{field_graph_id}-{role.value}",
                    primary_id=primary_id,
                    field_graph_id=field_graph_id,
                    role=role,
                    disposition=(
                        disposition
                        if (
                            role is LoopRole.PRIMARY_BOUNDARY
                            or disposition is LoopDisposition.PREREQUISITE_FAILURE
                        )
                        else LoopDisposition.NULL
                    ),
                    control_id=control_id,
                )
                for field_graph_id in field_graph_ids
                for role in LoopRole
            ),
            key=lambda cell: cell.cell_id,
        )
    )


def _passing_loop_primary(
    *,
    primary_id: str,
    disposition: LoopDisposition,
    control_id: str,
) -> PrimaryUnitSummary:
    expected = _complete_loop_manifest(
        primary_id=primary_id,
        disposition=disposition,
        control_id=control_id,
    )
    cells = tuple(
        _loop_cell(
            cell,
            total=(
                1.0
                if cell.expected_loop_disposition is LoopDisposition.NONZERO
                else 0.0
            ),
            prediction=(
                LoopPredictionClass.NONZERO
                if cell.expected_loop_disposition is LoopDisposition.NONZERO
                else LoopPredictionClass.NULL
            ),
            status=(
                AttemptStatus.INSUFFICIENT
                if disposition is LoopDisposition.PREREQUISITE_FAILURE
                else AttemptStatus.EVALUABLE
            ),
        )
        for cell in expected
    )
    return collapse_primary_units(
        expected,
        cells,
        (_loop_template(expected),),
        graph_total_tolerance_cycles=0.1,
    )[0]


def _all_stratum(
    primary_units: tuple[PrimaryUnitSummary, ...],
    *,
    stratum_id: str = "all",
) -> ExpectedStratum:
    return ExpectedStratum(
        stratum_id=stratum_id,
        evaluation_unit=EvaluationUnit.PHANTOM_INSTANCE,
        required=True,
        primary_unit_ids=tuple(sorted(unit.primary_unit_id for unit in primary_units)),
    )


def test_exact_manifests_materialize_missing_core_and_loop_cells() -> None:
    core = _expected_core("core-a")
    loop = _expected_loop("loop-a")

    materialized_core = materialize_expected_core_cells((core,), ())
    materialized_loop = materialize_expected_cells((loop,), ())

    assert materialized_core[0].reason_codes == (REASON_EXPECTED_CORE_CELL_NOT_RUN,)
    assert materialized_core[0].prediction_class is CorePredictionClass.NONE
    assert materialized_loop[0].reason_codes == (REASON_EXPECTED_CELL_NOT_RUN,)
    assert materialized_loop[0].prediction_class is LoopPredictionClass.NONE


def test_loop_manifest_identity_includes_role_and_disposition() -> None:
    expected = _expected_loop("loop-a")
    wrong_role = replace(
        _loop_cell(expected),
        loop_role=LoopRole.OFFCORE_CONTROL,
    )
    with pytest.raises(QualificationContractError, match="identity"):
        materialize_expected_cells((expected,), (wrong_role,))


def test_core_candidate_set_difference_is_graph_dependence() -> None:
    expected = (
        _expected_core("core-a", graph_id="a-one"),
        _expected_core("core-b", graph_id="a-two"),
    )
    cells = (
        _core_cell(expected[0], difference_rows=(7,)),
        _core_cell(expected[1], difference_rows=(8,)),
    )
    # Both cells have the same binary class; only the candidate sets move.
    assert {cell.prediction_class for cell in cells} == {
        CorePredictionClass.LOCALIZED_CORE
    }
    primary = collapse_core_primary_units(
        expected,
        cells,
        (_core_template(expected),),
        candidate_difference_tolerance_rows=1,
    )[0]

    assert primary.state is QualificationState.FAIL_GRAPH_DEPENDENCE
    assert primary.max_candidate_symmetric_difference_rows == 2
    assert REASON_CORE_CANDIDATE_GRAPH_DRIFT in primary.reason_codes
    assert build_d2_gate((primary,)).state is QualificationState.FAIL_GRAPH_DEPENDENCE


def _d2_boundary_repeat_fixture() -> tuple[
    tuple[CorePrimaryUnitSummary, CorePrimaryUnitSummary],
    tuple[CoreCellSummary, CoreCellSummary],
]:
    central_expected = replace(
        _expected_core("core-central", primary_id="unit-central"),
        stress_assignments=(
            StressAssignment("boundary", "central"),
            StressAssignment("state-geometry-warp", "nominal"),
        ),
    )
    wide_expected = replace(
        _expected_core("core-wide", primary_id="unit-wide"),
        stress_assignments=(
            StressAssignment("boundary", "wide"),
            StressAssignment("state-geometry-warp", "nominal"),
        ),
    )
    candidate_fingerprint = _digest("same-candidate-rows")
    anchor_fingerprint = _digest("same-anchor-rows")
    central_cell = replace(
        _core_cell(central_expected),
        candidate_fingerprint_sha256=candidate_fingerprint,
        oracle_anchor_fingerprint_sha256=anchor_fingerprint,
    )
    wide_cell = replace(
        _core_cell(wide_expected),
        candidate_fingerprint_sha256=candidate_fingerprint,
        oracle_anchor_fingerprint_sha256=anchor_fingerprint,
    )
    shared_input_fingerprint = _digest("same-d2-scientific-input")
    central_unit = replace(
        _core_template((central_expected,)),
        d2_scientific_input_fingerprint_sha256=shared_input_fingerprint,
    )
    wide_unit = replace(
        _core_template((wide_expected,)),
        d2_scientific_input_fingerprint_sha256=shared_input_fingerprint,
    )
    return (
        (central_unit, wide_unit),
        (central_cell, wide_cell),
    )


def test_d2_collapses_boundary_repeats_to_one_scientific_input_unit() -> None:
    units, cells = _d2_boundary_repeat_fixture()

    gate = build_d2_gate(
        units,
        boundary_axis_id="boundary",
        boundary_levels=("central", "wide"),
        core_cells=cells,
    )

    assert gate.attempted_count == 1
    assert gate.evaluable_count == 1
    assert gate.pass_count == 1


def test_d2_boundary_repeat_observation_disagreement_fails_closed() -> None:
    units, cells = _d2_boundary_repeat_fixture()
    disagreeing = replace(
        cells[1],
        candidate_fingerprint_sha256=_digest("different-candidate-rows"),
    )

    with pytest.raises(
        QualificationContractError,
        match="identity-free core-cell observations",
    ):
        build_d2_gate(
            units,
            boundary_axis_id="boundary",
            boundary_levels=("central", "wide"),
            core_cells=(cells[0], disagreeing),
        )


def test_d2_boundary_repeat_scientific_input_disagreement_fails_closed() -> None:
    units, cells = _d2_boundary_repeat_fixture()
    disagreeing = replace(
        units[1],
        d2_scientific_input_fingerprint_sha256=_digest("different-d2-scientific-input"),
    )

    with pytest.raises(
        QualificationContractError,
        match="scientific-input or primary-verdict",
    ):
        build_d2_gate(
            (units[0], disagreeing),
            boundary_axis_id="boundary",
            boundary_levels=("central", "wide"),
            core_cells=cells,
        )


def test_d2_boundary_repeat_manifest_gap_fails_closed() -> None:
    units, cells = _d2_boundary_repeat_fixture()

    with pytest.raises(QualificationContractError, match="exact declared boundary"):
        build_d2_gate(
            (units[0],),
            boundary_axis_id="boundary",
            boundary_levels=("central", "wide"),
            core_cells=(cells[0],),
        )


def test_core_candidate_set_difference_at_tolerance_is_allowed() -> None:
    expected = (
        _expected_core("core-a", graph_id="a-one"),
        _expected_core("core-b", graph_id="a-two"),
    )
    primary = collapse_core_primary_units(
        expected,
        (
            _core_cell(expected[0], difference_rows=(7,)),
            _core_cell(expected[1], difference_rows=(7, 8)),
        ),
        (_core_template(expected),),
        candidate_difference_tolerance_rows=1,
    )[0]

    assert primary.max_candidate_symmetric_difference_rows == 1
    # The individual cells fail exact anchor recovery, so this is an ordinary
    # localization failure, not graph dependence.
    assert primary.state is QualificationState.FAIL


def test_core_anchor_identity_must_be_fixed_across_graph_repeats() -> None:
    expected = (
        _expected_core("core-a", graph_id="a-one"),
        _expected_core("core-b", graph_id="a-two"),
    )
    with pytest.raises(QualificationContractError, match="anchor sets"):
        collapse_core_primary_units(
            expected,
            (
                _core_cell(
                    expected[0],
                    anchor_fingerprint=_digest("anchor-one"),
                ),
                _core_cell(
                    expected[1],
                    anchor_fingerprint=_digest("anchor-two"),
                ),
            ),
            (_core_template(expected),),
            candidate_difference_tolerance_rows=0,
        )


def test_fixed_null_with_core_remains_two_independent_typed_results() -> None:
    expected_core = (
        _expected_core(
            "core-fixed-null",
            disposition=CoreDisposition.LOCALIZED_CORE,
            control_id="fixed-null-with-core",
        ),
    )
    expected_loop = (
        _expected_loop(
            "loop-fixed-null-boundary",
            disposition=LoopDisposition.NULL,
            control_id="fixed-null-with-core",
        ),
        _expected_loop(
            "loop-fixed-null-offcore",
            role=LoopRole.OFFCORE_CONTROL,
            disposition=LoopDisposition.NULL,
            control_id="fixed-null-with-core",
        ),
    )
    core_primary = collapse_core_primary_units(
        expected_core,
        tuple(_core_cell(cell) for cell in expected_core),
        (_core_template(expected_core),),
        candidate_difference_tolerance_rows=0,
    )[0]
    loop_primary = collapse_primary_units(
        expected_loop,
        tuple(
            _loop_cell(
                cell,
                total=0.0,
                prediction=LoopPredictionClass.NULL,
            )
            for cell in expected_loop
        ),
        (_loop_template(expected_loop),),
        graph_total_tolerance_cycles=0.1,
    )[0]

    assert core_primary.prediction_class is CorePredictionClass.LOCALIZED_CORE
    assert loop_primary.prediction_class is LoopPredictionClass.NULL
    assert core_primary.state is loop_primary.state is QualificationState.PASS


def test_continuous_total_drift_rejects_unique_binary_loop_class() -> None:
    expected = (
        _expected_loop("loop-a", field_graph_id="a-one"),
        _expected_loop("loop-b", field_graph_id="a-two"),
        _expected_loop(
            "off-a",
            field_graph_id="a-one",
            role=LoopRole.OFFCORE_CONTROL,
            disposition=LoopDisposition.NULL,
        ),
        _expected_loop(
            "off-b",
            field_graph_id="a-two",
            role=LoopRole.OFFCORE_CONTROL,
            disposition=LoopDisposition.NULL,
        ),
    )
    cells = (
        _loop_cell(expected[0], total=0.9),
        _loop_cell(expected[1], total=1.2),
        _loop_cell(
            expected[2],
            total=0.0,
            prediction=LoopPredictionClass.NULL,
        ),
        _loop_cell(
            expected[3],
            total=0.0,
            prediction=LoopPredictionClass.NULL,
        ),
    )
    assert {
        cell.prediction_class
        for cell in cells
        if cell.loop_role is LoopRole.PRIMARY_BOUNDARY
    } == {LoopPredictionClass.NONZERO}

    primary = collapse_primary_units(
        expected,
        cells,
        (_loop_template(expected),),
        graph_total_tolerance_cycles=0.1,
    )[0]

    assert primary.state is QualificationState.FAIL_GRAPH_DEPENDENCE
    assert primary.continuous_total_span_cycles == pytest.approx(0.3)
    assert REASON_LOOP_TOTAL_GRAPH_DRIFT in primary.reason_codes


def test_primary_and_offcore_binary_classes_are_not_compared_to_each_other() -> None:
    expected = (
        _expected_loop("boundary"),
        _expected_loop(
            "offcore",
            role=LoopRole.OFFCORE_CONTROL,
            disposition=LoopDisposition.NULL,
        ),
    )
    primary = collapse_primary_units(
        expected,
        (
            _loop_cell(expected[0], prediction=LoopPredictionClass.NONZERO),
            _loop_cell(
                expected[1],
                total=0.0,
                prediction=LoopPredictionClass.NULL,
            ),
        ),
        (_loop_template(expected),),
        graph_total_tolerance_cycles=0.1,
    )[0]
    assert primary.state is QualificationState.PASS


def test_offcore_failure_propagates_to_d4_primary() -> None:
    expected = (
        _expected_loop("boundary"),
        _expected_loop(
            "offcore",
            role=LoopRole.OFFCORE_CONTROL,
            disposition=LoopDisposition.NULL,
        ),
    )
    primary = collapse_primary_units(
        expected,
        (
            _loop_cell(expected[0]),
            _loop_cell(
                expected[1],
                total=1.0,
                prediction=LoopPredictionClass.NONZERO,
                state=QualificationState.FAIL,
                error=1.0,
            ),
        ),
        (_loop_template(expected),),
        graph_total_tolerance_cycles=2.0,
    )[0]
    assert primary.prediction_class is LoopPredictionClass.NONZERO
    assert primary.state is QualificationState.FAIL
    assert (
        build_d4_gate(
            (primary,),
            (_nonvacuity(primary.primary_unit_id),),
        ).state
        is QualificationState.FAIL
    )


def test_d4_enforces_output_variation_only_for_frozen_sentinel() -> None:
    expected = (
        _expected_loop("boundary"),
        _expected_loop(
            "offcore",
            role=LoopRole.OFFCORE_CONTROL,
            disposition=LoopDisposition.NULL,
        ),
    )
    primary = collapse_primary_units(
        expected,
        (
            _loop_cell(expected[0]),
            _loop_cell(
                expected[1],
                total=0.0,
                prediction=LoopPredictionClass.NULL,
            ),
        ),
        (_loop_template(expected),),
        graph_total_tolerance_cycles=0.1,
    )[0]
    ordinary = CrossedNonvacuitySummary(
        primary_unit_id=primary.primary_unit_id,
        control_id=primary.control_id,
        attempt_status=AttemptStatus.EVALUABLE,
        receipt_fingerprint_sha256=_digest("ordinary-nonvacuity"),
        state=QualificationState.PASS,
        substantive_output_variation_required=False,
        field_adjacency_variant_count=3,
        cycle_adjacency_variant_count=3,
        field_consumption_variant_count=2,
        field_output_variant_count=1,
        maximum_pairwise_substantive_output_distance=0.0,
        minimum_substantive_output_distance=1e-6,
        field_graph_pair_effects=_field_pair_effects(distance=0.0),
        substantive_response_field_graph_ids=(),
        substantive_response_field_graph_count=0,
        required_substantive_response_field_graph_count=3,
        matched_cycle_count=3,
        representative_content_variant_count=2,
        minimum_representative_content_variants=2,
        reason_codes=(),
    )
    sentinel = CrossedNonvacuitySummary(
        primary_unit_id=primary.primary_unit_id,
        control_id=primary.control_id,
        attempt_status=AttemptStatus.INSUFFICIENT,
        receipt_fingerprint_sha256=_digest("sentinel-nonvacuity"),
        state=QualificationState.INSUFFICIENT,
        substantive_output_variation_required=True,
        field_adjacency_variant_count=3,
        cycle_adjacency_variant_count=3,
        field_consumption_variant_count=2,
        field_output_variant_count=1,
        maximum_pairwise_substantive_output_distance=0.0,
        minimum_substantive_output_distance=1e-6,
        field_graph_pair_effects=_field_pair_effects(distance=0.0),
        substantive_response_field_graph_ids=(),
        substantive_response_field_graph_count=0,
        required_substantive_response_field_graph_count=3,
        matched_cycle_count=3,
        representative_content_variant_count=2,
        minimum_representative_content_variants=2,
        reason_codes=(
            "field-output-axis-vacuous",
            "field-output-effect-below-minimum",
            "field-output-graph-coverage-incomplete",
        ),
    )

    assert build_d4_gate((primary,), (ordinary,)).state is QualificationState.PASS
    assert build_d4_gate((primary,), (sentinel,)).state is (
        QualificationState.INSUFFICIENT
    )


def test_d5_rates_use_only_primary_boundary_nonzero_and_null_classes() -> None:
    positive_expected = (
        _expected_loop("positive-boundary", primary_id="unit-positive"),
        _expected_loop(
            "positive-offcore",
            primary_id="unit-positive",
            role=LoopRole.OFFCORE_CONTROL,
            disposition=LoopDisposition.NULL,
        ),
    )
    null_expected = (
        _expected_loop(
            "null-boundary",
            primary_id="unit-null",
            disposition=LoopDisposition.NULL,
            control_id="control-null",
        ),
        _expected_loop(
            "null-offcore",
            primary_id="unit-null",
            role=LoopRole.OFFCORE_CONTROL,
            disposition=LoopDisposition.NULL,
            control_id="control-null",
        ),
    )
    prerequisite_expected = (
        _expected_loop(
            "prereq-boundary",
            primary_id="unit-prerequisite",
            disposition=LoopDisposition.PREREQUISITE_FAILURE,
            control_id="control-prerequisite",
        ),
        _expected_loop(
            "prereq-offcore",
            primary_id="unit-prerequisite",
            role=LoopRole.OFFCORE_CONTROL,
            disposition=LoopDisposition.PREREQUISITE_FAILURE,
            control_id="control-prerequisite",
        ),
    )
    primaries: list[PrimaryUnitSummary] = []
    for expected in (positive_expected, null_expected):
        cells = tuple(
            _loop_cell(
                cell,
                total=(
                    1.0
                    if cell.expected_loop_disposition is LoopDisposition.NONZERO
                    else 0.0
                ),
                prediction=(
                    LoopPredictionClass.NONZERO
                    if cell.expected_loop_disposition is LoopDisposition.NONZERO
                    else LoopPredictionClass.NULL
                ),
            )
            for cell in expected
        )
        primaries.extend(
            collapse_primary_units(
                expected,
                cells,
                (_loop_template(expected),),
                graph_total_tolerance_cycles=0.1,
            )
        )
    prereq_cells = tuple(
        _loop_cell(cell, status=AttemptStatus.INSUFFICIENT)
        for cell in prerequisite_expected
    )
    primaries.extend(
        collapse_primary_units(
            prerequisite_expected,
            prereq_cells,
            (_loop_template(prerequisite_expected),),
            graph_total_tolerance_cycles=0.1,
        )
    )
    primary_tuple = tuple(sorted(primaries, key=lambda unit: unit.primary_unit_id))
    expected_stratum = ExpectedStratum(
        stratum_id="all",
        evaluation_unit=EvaluationUnit.PHANTOM_INSTANCE,
        required=True,
        primary_unit_ids=tuple(unit.primary_unit_id for unit in primary_tuple),
    )
    summary = summarize_stratum(expected_stratum, primary_tuple, _policy())

    assert summary.recall == 1.0
    assert summary.specificity == 1.0
    assert summary.score_denominator == "expected_nonprerequisite_primary_units"
    assert summary.attempted_count == 3
    assert summary.evaluable_count == 2
    assert summary.rate_eligible_count == 2
    assert summary.rate_evaluable_count == 2
    assert summary.prerequisite_expected_count == 1
    assert summary.prerequisite_pass_count == 1
    assert summary.prerequisite_rate_handling == "excluded_but_mandatory"
    assert summary.all_expected_primary_units_must_pass is True
    assert build_d5_gate(
        primary_tuple,
        (summary,),
        _policy(),
        expected_strata=(expected_stratum,),
    ).state is (QualificationState.PASS)


@pytest.mark.parametrize(
    ("mode", "expected_state"),
    (
        ("forced-output", QualificationState.FAIL),
        ("wrong-reason", QualificationState.FAIL),
        ("not-run", QualificationState.NOT_RUN),
    ),
)
def test_prerequisite_control_is_rate_excluded_but_still_mandatory(
    mode: str,
    expected_state: QualificationState,
) -> None:
    positive = _passing_loop_primary(
        primary_id="unit-positive",
        disposition=LoopDisposition.NONZERO,
        control_id="control-positive",
    )
    negative = _passing_loop_primary(
        primary_id="unit-negative",
        disposition=LoopDisposition.NULL,
        control_id="control-negative",
    )
    expected = _complete_loop_manifest(
        primary_id="unit-prerequisite",
        disposition=LoopDisposition.PREREQUISITE_FAILURE,
        control_id="control-prerequisite",
    )
    if mode == "forced-output":
        cells = tuple(
            _loop_cell(
                cell,
                prediction=LoopPredictionClass.NONZERO,
                state=QualificationState.FAIL,
            )
            for cell in expected
        )
    elif mode == "wrong-reason":
        cells = tuple(
            _loop_cell(
                cell,
                status=AttemptStatus.INSUFFICIENT,
                state=QualificationState.FAIL,
                reason_codes=("prerequisite_reason_mismatch",),
            )
            for cell in expected
        )
    else:
        cells = tuple(
            _loop_cell(cell, status=AttemptStatus.NOT_RUN) for cell in expected
        )
    prerequisite = collapse_primary_units(
        expected,
        cells,
        (_loop_template(expected),),
        graph_total_tolerance_cycles=0.1,
    )[0]
    primaries = tuple(
        sorted(
            (positive, negative, prerequisite),
            key=lambda unit: unit.primary_unit_id,
        )
    )
    expected_stratum = _all_stratum(primaries)
    summary = summarize_stratum(expected_stratum, primaries, _policy())

    # The designed prerequisite control never changes the class-rate
    # denominator.  Its failure still changes the all-primary verdict.
    assert summary.rate_eligible_count == 2
    assert summary.rate_evaluable_count == 2
    assert summary.coverage == 1.0
    assert summary.abstention_fraction == 0.0
    assert summary.recall == 1.0
    assert summary.specificity == 1.0
    assert summary.prerequisite_expected_count == 1
    assert summary.prerequisite_pass_count == 0
    assert summary.state is expected_state
    assert (
        build_d5_gate(
            primaries,
            (summary,),
            _policy(),
            expected_strata=(expected_stratum,),
        ).state
        is expected_state
    )


@pytest.mark.parametrize(
    "abstaining_disposition",
    (LoopDisposition.NONZERO, LoopDisposition.NULL),
)
def test_ordinary_class_abstention_lowers_coverage_and_class_rate(
    abstaining_disposition: LoopDisposition,
) -> None:
    primaries: list[PrimaryUnitSummary] = []
    for disposition, primary_id in (
        (LoopDisposition.NONZERO, "unit-positive"),
        (LoopDisposition.NULL, "unit-negative"),
    ):
        expected = _complete_loop_manifest(
            primary_id=primary_id,
            disposition=disposition,
            control_id=f"control-{disposition.value}",
        )
        cells = tuple(
            _loop_cell(
                cell,
                status=(
                    AttemptStatus.INSUFFICIENT
                    if disposition is abstaining_disposition
                    else AttemptStatus.EVALUABLE
                ),
                total=(
                    1.0
                    if cell.expected_loop_disposition is LoopDisposition.NONZERO
                    else 0.0
                ),
                prediction=(
                    LoopPredictionClass.NONZERO
                    if cell.expected_loop_disposition is LoopDisposition.NONZERO
                    else LoopPredictionClass.NULL
                ),
            )
            for cell in expected
        )
        primaries.extend(
            collapse_primary_units(
                expected,
                cells,
                (_loop_template(expected),),
                graph_total_tolerance_cycles=0.1,
            )
        )
    primary_tuple = tuple(sorted(primaries, key=lambda unit: unit.primary_unit_id))
    expected_stratum = _all_stratum(primary_tuple)
    summary = summarize_stratum(expected_stratum, primary_tuple, _policy())

    assert summary.rate_eligible_count == 2
    assert summary.rate_evaluable_count == 1
    assert summary.rate_insufficient_count == 1
    assert summary.coverage == 0.5
    assert summary.abstention_fraction == 0.5
    if abstaining_disposition is LoopDisposition.NONZERO:
        assert summary.recall == 0.0
        assert summary.specificity == 1.0
    else:
        assert summary.recall == 1.0
        assert summary.specificity == 0.0
    assert summary.state is QualificationState.FAIL
    assert (
        build_d5_gate(
            primary_tuple,
            (summary,),
            _policy(),
            expected_strata=(expected_stratum,),
        ).state
        is QualificationState.FAIL
    )


@pytest.mark.parametrize("missing_obligation", ("offcore", "graph-repeat"))
def test_missing_loop_obligation_makes_primary_insufficient(
    missing_obligation: str,
) -> None:
    field_graph_ids = (
        ("a-one",) if missing_obligation == "offcore" else ("a-one", "a-two")
    )
    expected = _complete_loop_manifest(
        primary_id="unit-positive",
        disposition=LoopDisposition.NONZERO,
        control_id="control-positive",
        field_graph_ids=field_graph_ids,
    )
    missing = next(
        cell
        for cell in expected
        if (
            cell.loop_role is LoopRole.OFFCORE_CONTROL
            if missing_obligation == "offcore"
            else (
                cell.field_graph_id == "a-two"
                and cell.loop_role is LoopRole.PRIMARY_BOUNDARY
            )
        )
    )
    observed = tuple(
        _loop_cell(
            cell,
            total=(1.0 if cell.loop_role is LoopRole.PRIMARY_BOUNDARY else 0.0),
            prediction=(
                LoopPredictionClass.NONZERO
                if cell.loop_role is LoopRole.PRIMARY_BOUNDARY
                else LoopPredictionClass.NULL
            ),
        )
        for cell in expected
        if cell.cell_id != missing.cell_id
    )
    materialized = materialize_expected_cells(expected, observed)
    primary = collapse_primary_units(
        expected,
        materialized,
        (_loop_template(expected),),
        graph_total_tolerance_cycles=0.1,
    )[0]

    assert primary.attempt_status is AttemptStatus.INSUFFICIENT
    assert primary.prediction_class is LoopPredictionClass.ABSTAIN
    assert primary.state is QualificationState.INSUFFICIENT
    assert (
        build_d4_gate(
            (primary,),
            (
                _nonvacuity(
                    primary.primary_unit_id,
                    control_id=primary.control_id,
                ),
            ),
        ).state
        is QualificationState.INSUFFICIENT
    )


def test_failed_required_stratum_cannot_be_pooled_away() -> None:
    positive_pass = _passing_loop_primary(
        primary_id="positive-pass",
        disposition=LoopDisposition.NONZERO,
        control_id="control-positive-pass",
    )
    negative_pass = _passing_loop_primary(
        primary_id="negative-pass",
        disposition=LoopDisposition.NULL,
        control_id="control-negative-pass",
    )
    expected_fail = _complete_loop_manifest(
        primary_id="positive-fail",
        disposition=LoopDisposition.NONZERO,
        control_id="control-positive-fail",
    )
    positive_fail = collapse_primary_units(
        expected_fail,
        tuple(
            _loop_cell(cell, status=AttemptStatus.INSUFFICIENT)
            for cell in expected_fail
        ),
        (_loop_template(expected_fail),),
        graph_total_tolerance_cycles=0.1,
    )[0]
    negative_for_fail = _passing_loop_primary(
        primary_id="negative-for-fail",
        disposition=LoopDisposition.NULL,
        control_id="control-negative-for-fail",
    )
    primaries = tuple(
        sorted(
            (
                positive_pass,
                negative_pass,
                positive_fail,
                negative_for_fail,
            ),
            key=lambda unit: unit.primary_unit_id,
        )
    )
    pass_stratum = _all_stratum(
        (negative_pass, positive_pass),
        stratum_id="passing",
    )
    fail_stratum = _all_stratum(
        (negative_for_fail, positive_fail),
        stratum_id="failing",
    )
    summaries = (
        summarize_stratum(
            fail_stratum,
            (negative_for_fail, positive_fail),
            _policy(),
        ),
        summarize_stratum(
            pass_stratum,
            (negative_pass, positive_pass),
            _policy(),
        ),
    )

    assert summaries[0].state is QualificationState.FAIL
    assert summaries[1].state is QualificationState.PASS
    assert (
        build_d5_gate(
            primaries,
            summaries,
            _policy(),
            expected_strata=(fail_stratum, pass_stratum),
        ).state
        is QualificationState.FAIL
    )


@pytest.mark.parametrize(
    ("field_name", "tampered_value", "message"),
    (
        ("rate_evaluable_count", 1, "partition"),
        ("coverage", 0.5, "score universe"),
        ("recall", 0.5, "class counts"),
        ("score_denominator", "all_primary_units", "score_denominator"),
    ),
)
def test_stratum_summary_rejects_count_rate_and_denominator_tampering(
    field_name: str,
    tampered_value: object,
    message: str,
) -> None:
    primaries = (
        _passing_loop_primary(
            primary_id="unit-negative",
            disposition=LoopDisposition.NULL,
            control_id="control-negative",
        ),
        _passing_loop_primary(
            primary_id="unit-positive",
            disposition=LoopDisposition.NONZERO,
            control_id="control-positive",
        ),
    )
    expected_stratum = _all_stratum(primaries)
    summary = summarize_stratum(expected_stratum, primaries, _policy())

    with pytest.raises(QualificationContractError, match=message):
        replace(summary, **{field_name: tampered_value})

    document = summary.to_dict()
    document[field_name] = tampered_value
    with pytest.raises(QualificationContractError, match=message):
        StratumSummary.from_dict(document)


def test_d5_rejects_missing_extra_or_membership_mutated_strata() -> None:
    primaries = (
        _passing_loop_primary(
            primary_id="unit-negative",
            disposition=LoopDisposition.NULL,
            control_id="control-negative",
        ),
        _passing_loop_primary(
            primary_id="unit-positive",
            disposition=LoopDisposition.NONZERO,
            control_id="control-positive",
        ),
    )
    expected_stratum = _all_stratum(primaries)
    summary = summarize_stratum(expected_stratum, primaries, _policy())
    extra = replace(summary, stratum_id="extra")
    mutated_membership = replace(
        summary,
        primary_unit_ids=("unit-negative", "unit-z"),
    )

    for supplied in (
        (),
        (summary, extra),
        (mutated_membership,),
    ):
        with pytest.raises(
            QualificationContractError,
            match="exact frozen expected-stratum|frozen manifest",
        ):
            build_d5_gate(
                primaries,
                supplied,
                _policy(),
                expected_strata=(expected_stratum,),
            )


def test_all_not_run_primary_units_cannot_produce_passing_d2_or_d4() -> None:
    expected_core = (_expected_core("core-a"),)
    core_cells = materialize_expected_core_cells(expected_core, ())
    core_template = replace(
        _core_template(expected_core),
        d2_scientific_input_fingerprint_sha256=None,
        domain_instance_fingerprint_sha256=None,
        support_instance_fingerprint_sha256=None,
        attempt_status=AttemptStatus.NOT_RUN,
        prediction_class=CorePredictionClass.NONE,
        state=QualificationState.NOT_RUN,
        max_candidate_symmetric_difference_rows=None,
        reason_codes=("not-run",),
    )
    core_primary = collapse_core_primary_units(
        expected_core,
        core_cells,
        (core_template,),
        candidate_difference_tolerance_rows=0,
    )

    expected_loop = (
        _expected_loop("boundary"),
        _expected_loop(
            "offcore",
            role=LoopRole.OFFCORE_CONTROL,
            disposition=LoopDisposition.NULL,
        ),
    )
    loop_cells = materialize_expected_cells(expected_loop, ())
    loop_template = replace(
        _loop_template(expected_loop),
        domain_instance_fingerprint_sha256=None,
        support_instance_fingerprint_sha256=None,
        attempt_status=AttemptStatus.NOT_RUN,
        prediction_class=LoopPredictionClass.NONE,
        state=QualificationState.NOT_RUN,
        continuous_total_span_cycles=None,
        reason_codes=("not-run",),
    )
    loop_primary = collapse_primary_units(
        expected_loop,
        loop_cells,
        (loop_template,),
        graph_total_tolerance_cycles=0.1,
    )

    d2 = build_d2_gate(core_primary)
    d4 = build_d4_gate(
        loop_primary,
        (
            _nonvacuity(
                loop_primary[0].primary_unit_id,
                status=AttemptStatus.NOT_RUN,
            ),
        ),
    )
    assert d2.gate_id is QualificationGateId.D2
    assert d4.gate_id is QualificationGateId.D4
    assert d2.state is d4.state is QualificationState.NOT_RUN
    assert d2.pass_count == d4.pass_count == 0
