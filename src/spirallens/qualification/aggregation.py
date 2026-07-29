"""Exact-manifest aggregation for the independent core and loop axes.

Graph constructions are repeated nuisance measurements, never additional
inferential samples.  The full core A matrix and loop A × B × role matrix are
materialized first, then collapsed to one boundary-execution summary.  D2
subsequently collapses exact-agreement boundary repeats to one scientific
input unit; D4/D5 retain the loop executions.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol, TypeVar

from .common import (
    AttemptStatus,
    CorePredictionClass,
    EvaluationUnit,
    LoopDisposition,
    LoopPredictionClass,
    QualificationContractError,
    QualificationState,
)
from .contracts import (
    CoreCellSummary,
    CorePrimaryUnitSummary,
    CrossedCellSummary,
    CrossedNonvacuitySummary,
    GateResult,
    PrimaryUnitSummary,
    QualificationGateId,
    StratumSummary,
)
from .protocol import (
    CoveragePolicy,
    ExpectedCell,
    ExpectedCoreCell,
    ExpectedStratum,
    LoopRole,
)

REASON_EXPECTED_CORE_CELL_NOT_RUN = "expected_core_cell_not_run"
REASON_EXPECTED_CELL_NOT_RUN = "expected_cell_not_run"
REASON_GRAPH_CELL_PREDICTION_DISAGREEMENT = "graph_cell_prediction_disagreement"
REASON_CORE_CANDIDATE_GRAPH_DRIFT = "core_candidate_graph_drift"
REASON_LOOP_TOTAL_GRAPH_DRIFT = "loop_continuous_total_graph_drift"
REASON_POSITIVE_CLASS_DENOMINATOR_ZERO = "positive_class_denominator_zero"
REASON_NEGATIVE_CLASS_DENOMINATOR_ZERO = "negative_class_denominator_zero"
REASON_COVERAGE_BELOW_MINIMUM = "coverage_below_minimum"
REASON_ABSTENTION_ABOVE_MAXIMUM = "abstention_above_maximum"
REASON_RECALL_BELOW_MINIMUM = "recall_below_minimum"
REASON_SPECIFICITY_BELOW_MINIMUM = "specificity_below_minimum"
REASON_D2_CORE_PRIMARY_NONPASS = "d2_core_primary_nonpass"
REASON_D2_GRAPH_DEPENDENCE = "d2_graph_dependence"
REASON_D2_NO_PRIMARY_UNITS = "d2_no_primary_units"
REASON_D2_CONFOUNDER_MATRIX_NONPASS = "d2_false_core_confounder_matrix_nonpass"
REASON_D2_CONFOUNDER_MATRIX_NOT_RUN = "d2_false_core_confounder_matrix_not_run"
REASON_D4_PRIMARY_UNIT_NONPASS = "d4_primary_unit_nonpass"
REASON_D4_GRAPH_DEPENDENCE = "d4_graph_dependence"
REASON_D4_NO_PRIMARY_UNITS = "d4_no_primary_units"
REASON_D5_REQUIRED_STRATUM_NONPASS = "d5_required_stratum_nonpass"
REASON_D5_NO_PRIMARY_UNITS = "d5_no_primary_units"
REASON_D5_NO_REQUIRED_STRATA = "d5_no_required_strata"

_STATE_PRECEDENCE = {
    QualificationState.PASS: 0,
    QualificationState.NOT_RUN: 1,
    QualificationState.INSUFFICIENT: 2,
    QualificationState.FAIL: 3,
    QualificationState.FAIL_GRAPH_DEPENDENCE: 4,
}

_Item = TypeVar("_Item")


class _PrimarySummary(Protocol):
    attempt_status: AttemptStatus
    state: QualificationState
    reason_codes: tuple[str, ...]


def _canonical_reasons(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(set(values)))


def _worst_state(states: Iterable[QualificationState]) -> QualificationState:
    values = tuple(states)
    if not values:
        return QualificationState.NOT_RUN
    return max(values, key=_STATE_PRECEDENCE.__getitem__)


def _collapsed_state(states: tuple[QualificationState, ...]) -> QualificationState:
    """Collapse partial matrices without treating one missing cell as all-not-run."""

    if not states or all(state is QualificationState.NOT_RUN for state in states):
        return QualificationState.NOT_RUN
    if QualificationState.FAIL_GRAPH_DEPENDENCE in states:
        return QualificationState.FAIL_GRAPH_DEPENDENCE
    if QualificationState.FAIL in states:
        return QualificationState.FAIL
    if all(state is QualificationState.PASS for state in states):
        return QualificationState.PASS
    return QualificationState.INSUFFICIENT


def _index_unique(
    values: Iterable[_Item],
    *,
    item_type: type[_Item],
    id_attribute: str,
    label: str,
) -> dict[str, _Item]:
    result: dict[str, _Item] = {}
    for value in values:
        if not isinstance(value, item_type):
            raise TypeError(f"{label} must contain {item_type.__name__} values")
        identifier = getattr(value, id_attribute, None)
        if not isinstance(identifier, str):
            raise QualificationContractError(f"{label} lacks a string {id_attribute}")
        if identifier in result:
            raise QualificationContractError(
                f"{label} contains duplicate ID {identifier!r}"
            )
        result[identifier] = value
    return result


def materialize_expected_core_cells(
    expected_cells: Iterable[ExpectedCoreCell],
    observed_cells: Iterable[CoreCellSummary],
) -> tuple[CoreCellSummary, ...]:
    """Materialize the exact core A matrix with explicit not-run rows."""

    expected_by_id = _index_unique(
        expected_cells,
        item_type=ExpectedCoreCell,
        id_attribute="core_cell_id",
        label="expected core-cell manifest",
    )
    if not expected_by_id:
        raise QualificationContractError(
            "expected core-cell manifest must not be empty"
        )
    observed_by_id = _index_unique(
        observed_cells,
        item_type=CoreCellSummary,
        id_attribute="core_cell_id",
        label="observed core cells",
    )
    extras = sorted(set(observed_by_id) - set(expected_by_id))
    if extras:
        raise QualificationContractError(
            f"observed core cells contain undeclared IDs: {extras}"
        )
    normalized: list[CoreCellSummary] = []
    for core_cell_id in sorted(expected_by_id):
        expected = expected_by_id[core_cell_id]
        observed = observed_by_id.get(core_cell_id)
        if observed is None:
            normalized.append(
                CoreCellSummary(
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
                    reason_codes=(REASON_EXPECTED_CORE_CELL_NOT_RUN,),
                )
            )
            continue
        identity = (
            observed.primary_unit_id,
            observed.field_graph_id,
            observed.expected_disposition,
        )
        expected_identity = (
            expected.primary_unit_id,
            expected.field_graph_id,
            expected.expected_core_disposition,
        )
        if identity != expected_identity:
            raise QualificationContractError(
                f"core cell {core_cell_id!r} identity differs from the "
                "expected manifest"
            )
        normalized.append(observed)
    return tuple(normalized)


def materialize_expected_cells(
    expected_cells: Iterable[ExpectedCell],
    observed_cells: Iterable[CrossedCellSummary],
) -> tuple[CrossedCellSummary, ...]:
    """Materialize the exact loop A × B × role matrix with not-run rows."""

    expected_by_id = _index_unique(
        expected_cells,
        item_type=ExpectedCell,
        id_attribute="cell_id",
        label="expected loop-cell manifest",
    )
    if not expected_by_id:
        raise QualificationContractError(
            "expected loop-cell manifest must not be empty"
        )
    observed_by_id = _index_unique(
        observed_cells,
        item_type=CrossedCellSummary,
        id_attribute="cell_id",
        label="observed loop cells",
    )
    extras = sorted(set(observed_by_id) - set(expected_by_id))
    if extras:
        raise QualificationContractError(
            f"observed loop cells contain undeclared IDs: {extras}"
        )
    normalized: list[CrossedCellSummary] = []
    for cell_id in sorted(expected_by_id):
        expected = expected_by_id[cell_id]
        observed = observed_by_id.get(cell_id)
        if observed is None:
            normalized.append(
                CrossedCellSummary(
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
                    reason_codes=(REASON_EXPECTED_CELL_NOT_RUN,),
                )
            )
            continue
        identity = (
            observed.primary_unit_id,
            observed.field_graph_id,
            observed.cycle_graph_id,
            observed.loop_role,
            observed.expected_disposition,
        )
        expected_identity = (
            expected.primary_unit_id,
            expected.field_graph_id,
            expected.cycle_graph_id,
            expected.loop_role,
            expected.expected_loop_disposition,
        )
        if identity != expected_identity:
            raise QualificationContractError(
                f"loop cell {cell_id!r} identity differs from the expected manifest"
            )
        normalized.append(observed)
    return tuple(normalized)


def _group_expected_core(
    expected_cells: Iterable[ExpectedCoreCell],
) -> dict[str, tuple[ExpectedCoreCell, ...]]:
    grouped: dict[str, list[ExpectedCoreCell]] = {}
    seen: set[str] = set()
    for cell in expected_cells:
        if not isinstance(cell, ExpectedCoreCell):
            raise TypeError(
                "expected core-cell manifest must contain ExpectedCoreCell values"
            )
        if cell.core_cell_id in seen:
            raise QualificationContractError(
                f"expected core-cell manifest contains duplicate ID "
                f"{cell.core_cell_id!r}"
            )
        seen.add(cell.core_cell_id)
        grouped.setdefault(cell.primary_unit_id, []).append(cell)
    if not grouped:
        raise QualificationContractError(
            "expected core-cell manifest must not be empty"
        )
    return {
        primary_id: tuple(sorted(cells, key=lambda item: item.core_cell_id))
        for primary_id, cells in grouped.items()
    }


def _group_expected_loop(
    expected_cells: Iterable[ExpectedCell],
) -> dict[str, tuple[ExpectedCell, ...]]:
    grouped: dict[str, list[ExpectedCell]] = {}
    seen: set[str] = set()
    for cell in expected_cells:
        if not isinstance(cell, ExpectedCell):
            raise TypeError(
                "expected loop-cell manifest must contain ExpectedCell values"
            )
        if cell.cell_id in seen:
            raise QualificationContractError(
                f"expected loop-cell manifest contains duplicate ID {cell.cell_id!r}"
            )
        seen.add(cell.cell_id)
        grouped.setdefault(cell.primary_unit_id, []).append(cell)
    if not grouped:
        raise QualificationContractError(
            "expected loop-cell manifest must not be empty"
        )
    return {
        primary_id: tuple(sorted(cells, key=lambda item: item.cell_id))
        for primary_id, cells in grouped.items()
    }


def _validate_core_template(
    template: CorePrimaryUnitSummary,
    expected: tuple[ExpectedCoreCell, ...],
) -> None:
    first = expected[0]
    if (
        template.primary_unit_id != first.primary_unit_id
        or template.selection_seed != first.selection_seed
        or template.control_id != first.control_id
        or template.expected_disposition is not first.expected_core_disposition
        or template.stress_assignments != first.stress_assignments
        or template.core_cell_ids != tuple(cell.core_cell_id for cell in expected)
    ):
        raise QualificationContractError(
            f"core primary template {template.primary_unit_id!r} differs "
            "from the expected manifest"
        )


def _validate_loop_template(
    template: PrimaryUnitSummary,
    expected: tuple[ExpectedCell, ...],
) -> None:
    first = expected[0]
    primary_expected = next(
        cell.expected_loop_disposition
        for cell in expected
        if cell.loop_role is LoopRole.PRIMARY_BOUNDARY
    )
    if (
        template.primary_unit_id != first.primary_unit_id
        or template.selection_seed != first.selection_seed
        or template.control_id != first.control_id
        or template.expected_disposition is not primary_expected
        or template.stress_assignments != first.stress_assignments
        or template.crossed_cell_ids != tuple(cell.cell_id for cell in expected)
    ):
        raise QualificationContractError(
            f"loop primary template {template.primary_unit_id!r} differs "
            "from the expected manifest"
        )


def _max_set_symmetric_difference(
    values: tuple[set[int], ...],
) -> int:
    if len(values) < 2:
        return 0
    return max(len(left ^ right) for left, right in itertools.combinations(values, 2))


def _collapse_core_one(
    template: CorePrimaryUnitSummary,
    cells: tuple[CoreCellSummary, ...],
    *,
    candidate_difference_tolerance_rows: int,
) -> CorePrimaryUnitSummary:
    attempted = tuple(
        cell for cell in cells if cell.attempt_status is not AttemptStatus.NOT_RUN
    )
    if attempted:
        anchor_fingerprints = {
            cell.oracle_anchor_fingerprint_sha256 for cell in attempted
        }
        if len(anchor_fingerprints) != 1:
            raise QualificationContractError(
                f"core primary {template.primary_unit_id!r} carries different "
                "oracle anchor sets across graph-A repeats"
            )
    evaluable = tuple(
        cell for cell in cells if cell.attempt_status is AttemptStatus.EVALUABLE
    )
    candidate_sets = tuple(
        set(cell.candidate_anchor_symmetric_difference_rows) for cell in evaluable
    )
    candidate_span = _max_set_symmetric_difference(candidate_sets)
    predictions = tuple(cell.prediction_class for cell in evaluable)
    prediction_disagreement = len(set(predictions)) > 1
    graph_dependent = (
        prediction_disagreement or candidate_span > candidate_difference_tolerance_rows
    )

    if all(cell.attempt_status is AttemptStatus.NOT_RUN for cell in cells):
        attempt_status = AttemptStatus.NOT_RUN
        prediction = CorePredictionClass.NONE
        span: int | None = None
    elif all(cell.attempt_status is AttemptStatus.EVALUABLE for cell in cells):
        attempt_status = AttemptStatus.EVALUABLE
        if not predictions:
            raise QualificationContractError(
                "evaluable core primary has no evaluable cell prediction"
            )
        prediction = predictions[0]
        span = candidate_span
    else:
        attempt_status = AttemptStatus.INSUFFICIENT
        prediction = CorePredictionClass.ABSTAIN
        span = candidate_span

    state = _collapsed_state(tuple(cell.state for cell in cells))
    if graph_dependent:
        state = QualificationState.FAIL_GRAPH_DEPENDENCE
    reasons = [
        reason
        for cell in cells
        if cell.state is not QualificationState.PASS
        for reason in cell.reason_codes
    ]
    if prediction_disagreement:
        reasons.append(REASON_GRAPH_CELL_PREDICTION_DISAGREEMENT)
    if candidate_span > candidate_difference_tolerance_rows:
        reasons.append(REASON_CORE_CANDIDATE_GRAPH_DRIFT)
    reason_codes = (
        () if state is QualificationState.PASS else _canonical_reasons(reasons)
    )

    scientific_input_fp = template.d2_scientific_input_fingerprint_sha256
    domain_fp = template.domain_instance_fingerprint_sha256
    support_fp = template.support_instance_fingerprint_sha256
    if attempt_status is AttemptStatus.NOT_RUN:
        scientific_input_fp = None
        domain_fp = None
        support_fp = None
    elif scientific_input_fp is None or domain_fp is None or support_fp is None:
        raise QualificationContractError(
            f"attempted core primary {template.primary_unit_id!r} requires "
            "scientific-input, domain, and support fingerprints"
        )
    return CorePrimaryUnitSummary(
        primary_unit_id=template.primary_unit_id,
        selection_seed=template.selection_seed,
        control_id=template.control_id,
        expected_disposition=template.expected_disposition,
        stress_assignments=template.stress_assignments,
        d2_scientific_input_fingerprint_sha256=scientific_input_fp,
        domain_instance_fingerprint_sha256=domain_fp,
        support_instance_fingerprint_sha256=support_fp,
        attempt_status=attempt_status,
        prediction_class=prediction,
        state=state,
        max_candidate_symmetric_difference_rows=span,
        reason_codes=reason_codes,
        core_cell_ids=template.core_cell_ids,
    )


def collapse_core_primary_units(
    expected_cells: Iterable[ExpectedCoreCell],
    core_cells: Iterable[CoreCellSummary],
    primary_unit_templates: Iterable[CorePrimaryUnitSummary],
    *,
    candidate_difference_tolerance_rows: int,
) -> tuple[CorePrimaryUnitSummary, ...]:
    """Collapse graph-A repeats and enforce candidate-set stability."""

    if type(candidate_difference_tolerance_rows) is not int:
        raise TypeError("candidate_difference_tolerance_rows must be int")
    if candidate_difference_tolerance_rows < 0:
        raise QualificationContractError(
            "candidate_difference_tolerance_rows must be non-negative"
        )
    expected_groups = _group_expected_core(expected_cells)
    cells_by_id = _index_unique(
        core_cells,
        item_type=CoreCellSummary,
        id_attribute="core_cell_id",
        label="materialized core cells",
    )
    templates_by_id = _index_unique(
        primary_unit_templates,
        item_type=CorePrimaryUnitSummary,
        id_attribute="primary_unit_id",
        label="core primary templates",
    )
    expected_ids = {
        cell.core_cell_id for group in expected_groups.values() for cell in group
    }
    if set(cells_by_id) != expected_ids:
        raise QualificationContractError(
            "core cells must equal the exact materialized core manifest"
        )
    if set(templates_by_id) != set(expected_groups):
        raise QualificationContractError(
            "core primary templates must equal the expected primary manifest"
        )
    collapsed: list[CorePrimaryUnitSummary] = []
    for primary_id in sorted(expected_groups):
        expected = expected_groups[primary_id]
        template = templates_by_id[primary_id]
        _validate_core_template(template, expected)
        cells = tuple(cells_by_id[cell.core_cell_id] for cell in expected)
        for expected_cell, observed in zip(expected, cells, strict=True):
            if (
                observed.primary_unit_id != expected_cell.primary_unit_id
                or observed.field_graph_id != expected_cell.field_graph_id
                or observed.expected_disposition
                is not expected_cell.expected_core_disposition
            ):
                raise QualificationContractError(
                    f"core cell {expected_cell.core_cell_id!r} differs "
                    "from the expected manifest"
                )
        collapsed.append(
            _collapse_core_one(
                template,
                cells,
                candidate_difference_tolerance_rows=(
                    candidate_difference_tolerance_rows
                ),
            )
        )
    return tuple(collapsed)


def _role_total_span(cells: tuple[CrossedCellSummary, ...]) -> float:
    totals = tuple(
        cell.continuous_signed_total_cycles
        for cell in cells
        if cell.attempt_status is AttemptStatus.EVALUABLE
    )
    if len(totals) < 2:
        return 0.0
    if any(total is None for total in totals):
        raise QualificationContractError(
            "evaluable loop cells must carry continuous totals"
        )
    numeric = tuple(float(total) for total in totals if total is not None)
    return max(numeric) - min(numeric)


def _collapse_loop_one(
    template: PrimaryUnitSummary,
    cells: tuple[CrossedCellSummary, ...],
    *,
    graph_total_tolerance_cycles: float,
) -> PrimaryUnitSummary:
    by_role = {
        role: tuple(cell for cell in cells if cell.loop_role is role)
        for role in LoopRole
    }
    if any(not role_cells for role_cells in by_role.values()):
        raise QualificationContractError(
            f"loop primary {template.primary_unit_id!r} lacks one loop role"
        )
    boundary = by_role[LoopRole.PRIMARY_BOUNDARY]
    role_prediction_disagreement = any(
        len(
            {
                cell.prediction_class
                for cell in role_cells
                if cell.attempt_status is AttemptStatus.EVALUABLE
            }
        )
        > 1
        for role_cells in by_role.values()
    )
    role_spans = tuple(_role_total_span(by_role[role]) for role in LoopRole)
    total_span = max(role_spans, default=0.0)
    total_drift = total_span > graph_total_tolerance_cycles
    graph_dependent = role_prediction_disagreement or total_drift

    if all(cell.attempt_status is AttemptStatus.NOT_RUN for cell in cells):
        attempt_status = AttemptStatus.NOT_RUN
        prediction = LoopPredictionClass.NONE
        span: float | None = None
    elif all(cell.attempt_status is AttemptStatus.EVALUABLE for cell in cells):
        predictions = tuple(cell.prediction_class for cell in boundary)
        if not predictions:
            raise QualificationContractError(
                "evaluable loop primary has no boundary prediction"
            )
        attempt_status = AttemptStatus.EVALUABLE
        prediction = predictions[0]
        span = total_span
    else:
        attempt_status = AttemptStatus.INSUFFICIENT
        prediction = LoopPredictionClass.ABSTAIN
        span = total_span

    state = _collapsed_state(tuple(cell.state for cell in cells))
    if graph_dependent:
        state = QualificationState.FAIL_GRAPH_DEPENDENCE
    reasons = [
        reason
        for cell in cells
        if cell.state is not QualificationState.PASS
        for reason in cell.reason_codes
    ]
    if role_prediction_disagreement:
        reasons.append(REASON_GRAPH_CELL_PREDICTION_DISAGREEMENT)
    if total_drift:
        reasons.append(REASON_LOOP_TOTAL_GRAPH_DRIFT)
    reason_codes = (
        () if state is QualificationState.PASS else _canonical_reasons(reasons)
    )

    domain_fp = template.domain_instance_fingerprint_sha256
    support_fp = template.support_instance_fingerprint_sha256
    if attempt_status is AttemptStatus.NOT_RUN:
        domain_fp = None
        support_fp = None
    elif domain_fp is None or support_fp is None:
        raise QualificationContractError(
            f"attempted loop primary {template.primary_unit_id!r} requires "
            "domain and support fingerprints"
        )
    return PrimaryUnitSummary(
        primary_unit_id=template.primary_unit_id,
        selection_seed=template.selection_seed,
        control_id=template.control_id,
        expected_disposition=template.expected_disposition,
        stress_assignments=template.stress_assignments,
        domain_instance_fingerprint_sha256=domain_fp,
        support_instance_fingerprint_sha256=support_fp,
        attempt_status=attempt_status,
        prediction_class=prediction,
        state=state,
        continuous_total_span_cycles=span,
        reason_codes=reason_codes,
        crossed_cell_ids=template.crossed_cell_ids,
    )


def collapse_primary_units(
    expected_cells: Iterable[ExpectedCell],
    crossed_cells: Iterable[CrossedCellSummary],
    primary_unit_templates: Iterable[PrimaryUnitSummary],
    *,
    graph_total_tolerance_cycles: float,
) -> tuple[PrimaryUnitSummary, ...]:
    """Collapse A × B × role repeats and enforce continuous-total stability."""

    if isinstance(graph_total_tolerance_cycles, bool) or not isinstance(
        graph_total_tolerance_cycles, (int, float)
    ):
        raise TypeError("graph_total_tolerance_cycles must be real")
    tolerance = float(graph_total_tolerance_cycles)
    if not math.isfinite(tolerance) or tolerance < 0.0:
        raise QualificationContractError(
            "graph_total_tolerance_cycles must be finite and non-negative"
        )
    expected_groups = _group_expected_loop(expected_cells)
    cells_by_id = _index_unique(
        crossed_cells,
        item_type=CrossedCellSummary,
        id_attribute="cell_id",
        label="materialized loop cells",
    )
    templates_by_id = _index_unique(
        primary_unit_templates,
        item_type=PrimaryUnitSummary,
        id_attribute="primary_unit_id",
        label="loop primary templates",
    )
    expected_ids = {
        cell.cell_id for group in expected_groups.values() for cell in group
    }
    if set(cells_by_id) != expected_ids:
        raise QualificationContractError(
            "loop cells must equal the exact materialized loop manifest"
        )
    if set(templates_by_id) != set(expected_groups):
        raise QualificationContractError(
            "loop primary templates must equal the expected primary manifest"
        )
    collapsed: list[PrimaryUnitSummary] = []
    for primary_id in sorted(expected_groups):
        expected = expected_groups[primary_id]
        template = templates_by_id[primary_id]
        _validate_loop_template(template, expected)
        cells = tuple(cells_by_id[cell.cell_id] for cell in expected)
        for expected_cell, observed in zip(expected, cells, strict=True):
            if (
                observed.primary_unit_id != expected_cell.primary_unit_id
                or observed.field_graph_id != expected_cell.field_graph_id
                or observed.cycle_graph_id != expected_cell.cycle_graph_id
                or observed.loop_role is not expected_cell.loop_role
                or observed.expected_disposition
                is not expected_cell.expected_loop_disposition
            ):
                raise QualificationContractError(
                    f"loop cell {expected_cell.cell_id!r} differs "
                    "from the expected manifest"
                )
        collapsed.append(
            _collapse_loop_one(
                template,
                cells,
                graph_total_tolerance_cycles=tolerance,
            )
        )
    return tuple(collapsed)


def _primary_counts(primary_units: tuple[_PrimarySummary, ...]) -> dict[str, int]:
    return {
        "attempted_count": len(primary_units),
        "evaluable_count": sum(
            unit.attempt_status is AttemptStatus.EVALUABLE for unit in primary_units
        ),
        "attempt_insufficient_count": sum(
            unit.attempt_status is AttemptStatus.INSUFFICIENT for unit in primary_units
        ),
        "attempt_not_run_count": sum(
            unit.attempt_status is AttemptStatus.NOT_RUN for unit in primary_units
        ),
        "pass_count": sum(
            unit.state is QualificationState.PASS for unit in primary_units
        ),
        "fail_count": sum(
            unit.state is QualificationState.FAIL for unit in primary_units
        ),
        "fail_graph_dependence_count": sum(
            unit.state is QualificationState.FAIL_GRAPH_DEPENDENCE
            for unit in primary_units
        ),
        "insufficient_count": sum(
            unit.state is QualificationState.INSUFFICIENT for unit in primary_units
        ),
        "not_run_count": sum(
            unit.state is QualificationState.NOT_RUN for unit in primary_units
        ),
    }


def _raw_primary_state(
    primary_units: tuple[_PrimarySummary, ...],
) -> QualificationState:
    return _worst_state(unit.state for unit in primary_units)


def summarize_stratum(
    expected_stratum: ExpectedStratum,
    primary_units: Iterable[PrimaryUnitSummary],
    coverage_policy: CoveragePolicy,
) -> StratumSummary:
    """Aggregate one frozen stratum over expected loop primary units."""

    primary_by_id = _index_unique(
        primary_units,
        item_type=PrimaryUnitSummary,
        id_attribute="primary_unit_id",
        label=f"primary units for stratum {expected_stratum.stratum_id!r}",
    )
    if set(primary_by_id) != set(expected_stratum.primary_unit_ids):
        raise QualificationContractError(
            f"stratum {expected_stratum.stratum_id!r} primary units differ "
            "from its frozen expected manifest"
        )
    if expected_stratum.evaluation_unit is not coverage_policy.evaluation_unit:
        raise QualificationContractError(
            f"stratum {expected_stratum.stratum_id!r} evaluation unit differs "
            "from the coverage policy"
        )
    units = tuple(
        primary_by_id[primary_id] for primary_id in expected_stratum.primary_unit_ids
    )
    counts = _primary_counts(units)
    expected_count = counts["attempted_count"]
    rate_units = tuple(
        unit
        for unit in units
        if unit.expected_disposition in {LoopDisposition.NONZERO, LoopDisposition.NULL}
    )
    if not rate_units:
        raise QualificationContractError(
            f"stratum {expected_stratum.stratum_id!r} has no expected "
            "evaluable nonzero/null primaries"
        )
    rate_eligible_count = len(rate_units)
    rate_evaluable_count = sum(
        unit.attempt_status is AttemptStatus.EVALUABLE for unit in rate_units
    )
    rate_insufficient_count = sum(
        unit.attempt_status is AttemptStatus.INSUFFICIENT for unit in rate_units
    )
    rate_not_run_count = sum(
        unit.attempt_status is AttemptStatus.NOT_RUN for unit in rate_units
    )
    coverage = rate_evaluable_count / rate_eligible_count
    abstention = (rate_insufficient_count + rate_not_run_count) / rate_eligible_count
    positive_units = tuple(
        unit for unit in units if unit.expected_disposition is LoopDisposition.NONZERO
    )
    negative_units = tuple(
        unit for unit in units if unit.expected_disposition is LoopDisposition.NULL
    )
    prerequisite_units = tuple(
        unit
        for unit in units
        if unit.expected_disposition is LoopDisposition.PREREQUISITE_FAILURE
    )
    positive_pass_count = sum(
        unit.attempt_status is AttemptStatus.EVALUABLE
        and unit.prediction_class is LoopPredictionClass.NONZERO
        and unit.state is QualificationState.PASS
        for unit in positive_units
    )
    negative_pass_count = sum(
        unit.attempt_status is AttemptStatus.EVALUABLE
        and unit.prediction_class is LoopPredictionClass.NULL
        and unit.state is QualificationState.PASS
        for unit in negative_units
    )
    prerequisite_pass_count = sum(
        unit.state is QualificationState.PASS for unit in prerequisite_units
    )
    recall = None if not positive_units else positive_pass_count / len(positive_units)
    specificity = (
        None if not negative_units else negative_pass_count / len(negative_units)
    )

    raw_state = _raw_primary_state(units)
    all_units_not_run = counts["not_run_count"] == expected_count
    policy_reasons: list[str] = []
    accuracy_failed = False
    support_failed = False
    if expected_stratum.required and not all_units_not_run:
        if recall is None:
            support_failed = True
            policy_reasons.append(REASON_POSITIVE_CLASS_DENOMINATOR_ZERO)
        if specificity is None:
            support_failed = True
            policy_reasons.append(REASON_NEGATIVE_CLASS_DENOMINATOR_ZERO)
        if coverage < coverage_policy.minimum_coverage:
            support_failed = True
            policy_reasons.append(REASON_COVERAGE_BELOW_MINIMUM)
        if abstention > coverage_policy.maximum_abstention_fraction:
            support_failed = True
            policy_reasons.append(REASON_ABSTENTION_ABOVE_MAXIMUM)
        if recall is not None and recall < coverage_policy.minimum_recall:
            accuracy_failed = True
            policy_reasons.append(REASON_RECALL_BELOW_MINIMUM)
        if (
            specificity is not None
            and specificity < coverage_policy.minimum_specificity
        ):
            accuracy_failed = True
            policy_reasons.append(REASON_SPECIFICITY_BELOW_MINIMUM)

    if all_units_not_run:
        state = QualificationState.NOT_RUN
    elif raw_state is QualificationState.FAIL_GRAPH_DEPENDENCE:
        state = QualificationState.FAIL_GRAPH_DEPENDENCE
    elif raw_state is QualificationState.FAIL or accuracy_failed:
        state = QualificationState.FAIL
    elif support_failed:
        state = QualificationState.INSUFFICIENT
    else:
        state = raw_state
    reasons = [
        reason
        for unit in units
        if unit.state is not QualificationState.PASS
        for reason in unit.reason_codes
    ]
    reasons.extend(policy_reasons)
    reason_codes = (
        () if state is QualificationState.PASS else _canonical_reasons(reasons)
    )
    return StratumSummary(
        stratum_id=expected_stratum.stratum_id,
        evaluation_unit=expected_stratum.evaluation_unit,
        required=expected_stratum.required,
        primary_unit_ids=expected_stratum.primary_unit_ids,
        state=state,
        rate_eligible_count=rate_eligible_count,
        rate_evaluable_count=rate_evaluable_count,
        rate_insufficient_count=rate_insufficient_count,
        rate_not_run_count=rate_not_run_count,
        positive_expected_count=len(positive_units),
        positive_pass_count=positive_pass_count,
        negative_expected_count=len(negative_units),
        negative_pass_count=negative_pass_count,
        prerequisite_expected_count=len(prerequisite_units),
        prerequisite_pass_count=prerequisite_pass_count,
        coverage=coverage,
        abstention_fraction=abstention,
        recall=recall,
        specificity=specificity,
        reason_codes=reason_codes,
        **counts,
    )


def summarize_strata(
    expected_strata: Iterable[ExpectedStratum],
    primary_units: Iterable[PrimaryUnitSummary],
    coverage_policy: CoveragePolicy,
) -> tuple[StratumSummary, ...]:
    """Return canonical summaries for the exact frozen strata."""

    expected_by_id = _index_unique(
        expected_strata,
        item_type=ExpectedStratum,
        id_attribute="stratum_id",
        label="expected strata",
    )
    if not expected_by_id:
        raise QualificationContractError("expected strata must not be empty")
    primary_by_id = _index_unique(
        primary_units,
        item_type=PrimaryUnitSummary,
        id_attribute="primary_unit_id",
        label="primary units across strata",
    )
    required_members: set[str] = set()
    for stratum in expected_by_id.values():
        unknown = set(stratum.primary_unit_ids) - set(primary_by_id)
        if unknown:
            raise QualificationContractError(
                f"stratum {stratum.stratum_id!r} references unknown primaries: "
                f"{sorted(unknown)}"
            )
        if stratum.required:
            required_members.update(stratum.primary_unit_ids)
    if required_members != set(primary_by_id):
        raise QualificationContractError(
            "required strata must cover the exact expected-primary universe"
        )
    return tuple(
        summarize_stratum(
            expected_by_id[stratum_id],
            (
                primary_by_id[primary_id]
                for primary_id in expected_by_id[stratum_id].primary_unit_ids
            ),
            coverage_policy,
        )
        for stratum_id in sorted(expected_by_id)
    )


def _gate_reasons(
    *,
    state: QualificationState,
    source_reasons: Iterable[str],
    marker: str,
    empty_marker: str,
    attempted_count: int,
) -> tuple[str, ...]:
    if state is QualificationState.PASS:
        return ()
    reasons = list(source_reasons)
    reasons.append(empty_marker if attempted_count == 0 else marker)
    return _canonical_reasons(reasons)


def _d2_primary_repeat_projection(
    unit: CorePrimaryUnitSummary,
) -> tuple[object, ...]:
    """Return the identity-free fields that can affect the D2 verdict."""

    return (
        unit.expected_disposition,
        unit.d2_scientific_input_fingerprint_sha256,
        unit.attempt_status,
        unit.prediction_class,
        unit.state,
        unit.max_candidate_symmetric_difference_rows,
        unit.reason_codes,
    )


def _d2_cell_repeat_projection(
    cell: CoreCellSummary,
) -> tuple[object, ...]:
    """Return D2 observations whose digests do not include the execution ID."""

    return (
        cell.field_graph_id,
        cell.expected_disposition,
        cell.candidate_fingerprint_sha256,
        cell.oracle_anchor_fingerprint_sha256,
        cell.candidate_anchor_symmetric_difference_rows,
        cell.attempt_status,
        cell.prediction_class,
        cell.state,
        cell.reason_codes,
    )


def _collapse_d2_boundary_repeats(
    primary_units: tuple[CorePrimaryUnitSummary, ...],
    *,
    boundary_axis_id: str,
    boundary_levels: tuple[str, ...],
    core_cells: Iterable[CoreCellSummary],
) -> tuple[CorePrimaryUnitSummary, ...]:
    """Collapse loop-boundary repeats after exact D2-observation agreement.

    Several stored fingerprints intentionally include ``primary_unit_id`` and
    the loop support, so they must differ between boundary executions.  The
    equality contract therefore compares the complete identity-free D2 verdict
    projection, including candidate/anchor row-set fingerprints, for every A
    graph.  D0 source binding separately fixes the runner path in which the
    boundary assignment is absent from Cartesian generation and field fitting.
    """

    if not boundary_axis_id:
        raise QualificationContractError(
            "D2 boundary collapse requires a non-empty boundary axis ID"
        )
    if not boundary_levels or len(set(boundary_levels)) != len(boundary_levels):
        raise QualificationContractError(
            "D2 boundary collapse requires unique declared boundary levels"
        )
    if boundary_levels != tuple(sorted(boundary_levels)):
        raise QualificationContractError(
            "D2 boundary levels must be in canonical order"
        )

    cells_by_id = _index_unique(
        core_cells,
        item_type=CoreCellSummary,
        id_attribute="core_cell_id",
        label="D2 boundary-repeat core cells",
    )
    referenced_cell_ids = {
        cell_id for unit in primary_units for cell_id in unit.core_cell_ids
    }
    if set(cells_by_id) != referenced_cell_ids:
        raise QualificationContractError(
            "D2 boundary-repeat core cells must exactly cover the supplied "
            "core primary units"
        )

    grouped: dict[
        tuple[int, str, tuple[tuple[str, str], ...]],
        dict[str, CorePrimaryUnitSummary],
    ] = {}
    for unit in primary_units:
        assignments = tuple(
            (assignment.axis_id, assignment.level)
            for assignment in unit.stress_assignments
        )
        boundary = tuple(
            level for axis_id, level in assignments if axis_id == boundary_axis_id
        )
        if len(boundary) != 1:
            raise QualificationContractError(
                "every D2 primary must carry exactly one boundary assignment"
            )
        nonboundary = tuple(
            assignment
            for assignment in assignments
            if assignment[0] != boundary_axis_id
        )
        key = (unit.selection_seed, unit.control_id, nonboundary)
        by_level = grouped.setdefault(key, {})
        if boundary[0] in by_level:
            raise QualificationContractError(
                "D2 boundary-repeat group contains a duplicate boundary level"
            )
        by_level[boundary[0]] = unit

    collapsed: list[CorePrimaryUnitSummary] = []
    expected_levels = set(boundary_levels)
    for key in sorted(grouped):
        by_level = grouped[key]
        if set(by_level) != expected_levels:
            raise QualificationContractError(
                "D2 boundary-repeat group does not cover the exact declared "
                "boundary levels"
            )
        ordered_units = tuple(by_level[level] for level in boundary_levels)
        reference = ordered_units[0]
        reference_projection = _d2_primary_repeat_projection(reference)
        reference_cells = {
            cells_by_id[cell_id].field_graph_id: cells_by_id[cell_id]
            for cell_id in reference.core_cell_ids
        }
        if len(reference_cells) != len(reference.core_cell_ids):
            raise QualificationContractError(
                "D2 boundary repeat contains duplicate A-graph core cells"
            )
        reference_cell_projection = {
            graph_id: _d2_cell_repeat_projection(cell)
            for graph_id, cell in reference_cells.items()
        }
        for repeated in ordered_units[1:]:
            if _d2_primary_repeat_projection(repeated) != reference_projection:
                raise QualificationContractError(
                    "D2 boundary repeats disagree on their scientific-input "
                    "or primary-verdict projection"
                )
            repeated_cells = {
                cells_by_id[cell_id].field_graph_id: cells_by_id[cell_id]
                for cell_id in repeated.core_cell_ids
            }
            if len(repeated_cells) != len(repeated.core_cell_ids):
                raise QualificationContractError(
                    "D2 boundary repeat contains duplicate A-graph core cells"
                )
            repeated_projection = {
                graph_id: _d2_cell_repeat_projection(cell)
                for graph_id, cell in repeated_cells.items()
            }
            if repeated_projection != reference_cell_projection:
                raise QualificationContractError(
                    "D2 boundary repeats disagree on their identity-free "
                    "core-cell observations"
                )
        collapsed.append(reference)
    return tuple(collapsed)


def build_d2_gate(
    primary_units: Iterable[CorePrimaryUnitSummary],
    *,
    confounder_state: QualificationState = QualificationState.PASS,
    confounder_reason_codes: tuple[str, ...] = (),
    boundary_axis_id: str | None = None,
    boundary_levels: tuple[str, ...] = (),
    core_cells: Iterable[CoreCellSummary] | None = None,
) -> GateResult:
    """Build D2 from unique core inputs plus the frozen false-core matrix."""

    if not isinstance(confounder_state, QualificationState):
        raise TypeError("confounder_state must be a QualificationState")
    if confounder_state not in {
        QualificationState.PASS,
        QualificationState.FAIL,
        QualificationState.NOT_RUN,
    }:
        raise QualificationContractError(
            "D2 confounder matrix state must be pass, fail, or not_run"
        )
    canonical_confounder_reasons = _canonical_reasons(confounder_reason_codes)
    if (
        (confounder_state is QualificationState.PASS and canonical_confounder_reasons)
        or (
            confounder_state is QualificationState.FAIL
            and canonical_confounder_reasons != (REASON_D2_CONFOUNDER_MATRIX_NONPASS,)
        )
        or (
            confounder_state is QualificationState.NOT_RUN
            and canonical_confounder_reasons != (REASON_D2_CONFOUNDER_MATRIX_NOT_RUN,)
        )
    ):
        raise QualificationContractError(
            "D2 confounder reasons differ from its exact matrix state"
        )

    primary_by_id = _index_unique(
        primary_units,
        item_type=CorePrimaryUnitSummary,
        id_attribute="primary_unit_id",
        label="D2 core primary units",
    )
    units = tuple(primary_by_id[key] for key in sorted(primary_by_id))
    if boundary_axis_id is None:
        if boundary_levels or core_cells is not None:
            raise QualificationContractError(
                "D2 boundary collapse arguments must be supplied together"
            )
    else:
        if core_cells is None:
            raise QualificationContractError(
                "D2 boundary collapse requires core-cell observations"
            )
        units = _collapse_d2_boundary_repeats(
            units,
            boundary_axis_id=boundary_axis_id,
            boundary_levels=boundary_levels,
            core_cells=core_cells,
        )
    counts = _primary_counts(units)
    primary_state = _raw_primary_state(units)
    state = _worst_state((primary_state, confounder_state))
    reasons = [
        reason
        for unit in units
        if unit.state is not QualificationState.PASS
        for reason in unit.reason_codes
    ]
    if primary_state is QualificationState.FAIL_GRAPH_DEPENDENCE:
        reasons.append(REASON_D2_GRAPH_DEPENDENCE)
    if primary_state is not QualificationState.PASS:
        reasons.append(
            REASON_D2_NO_PRIMARY_UNITS
            if counts["attempted_count"] == 0
            else REASON_D2_CORE_PRIMARY_NONPASS
        )
    reasons.extend(canonical_confounder_reasons)
    return GateResult(
        gate_id=QualificationGateId.D2,
        state=state,
        evaluation_unit=EvaluationUnit.PHANTOM_INSTANCE,
        reason_codes=_canonical_reasons(reasons),
        **counts,
    )


def build_d4_gate(
    primary_units: Iterable[PrimaryUnitSummary],
    nonvacuity_summaries: Iterable[CrossedNonvacuitySummary],
    *,
    evaluation_unit: EvaluationUnit = EvaluationUnit.PHANTOM_INSTANCE,
) -> GateResult:
    """Build D4 from loop primaries and per-primary crossed nonvacuity."""

    primary_by_id = _index_unique(
        primary_units,
        item_type=PrimaryUnitSummary,
        id_attribute="primary_unit_id",
        label="D4 loop primary units",
    )
    units = tuple(primary_by_id[key] for key in sorted(primary_by_id))
    nonvacuity_by_id = _index_unique(
        nonvacuity_summaries,
        item_type=CrossedNonvacuitySummary,
        id_attribute="primary_unit_id",
        label="D4 crossed nonvacuity summaries",
    )
    if set(nonvacuity_by_id) != set(primary_by_id):
        raise QualificationContractError(
            "D4 crossed nonvacuity evidence must cover every loop primary"
        )
    effective_statuses: list[AttemptStatus] = []
    effective_states: list[QualificationState] = []
    for unit in units:
        evidence = nonvacuity_by_id[unit.primary_unit_id]
        if evidence.control_id != unit.control_id:
            raise QualificationContractError(
                "D4 crossed nonvacuity control differs from its primary"
            )
        if (
            unit.attempt_status is AttemptStatus.NOT_RUN
            and evidence.attempt_status is AttemptStatus.NOT_RUN
        ):
            effective_statuses.append(AttemptStatus.NOT_RUN)
        elif (
            unit.attempt_status is AttemptStatus.EVALUABLE
            and evidence.attempt_status is AttemptStatus.EVALUABLE
        ):
            effective_statuses.append(AttemptStatus.EVALUABLE)
        else:
            effective_statuses.append(AttemptStatus.INSUFFICIENT)
        effective_states.append(_worst_state((unit.state, evidence.state)))
    statuses = tuple(effective_statuses)
    states = tuple(effective_states)
    counts = {
        "attempted_count": len(units),
        "evaluable_count": statuses.count(AttemptStatus.EVALUABLE),
        "attempt_insufficient_count": statuses.count(AttemptStatus.INSUFFICIENT),
        "attempt_not_run_count": statuses.count(AttemptStatus.NOT_RUN),
        "pass_count": states.count(QualificationState.PASS),
        "fail_count": states.count(QualificationState.FAIL),
        "fail_graph_dependence_count": states.count(
            QualificationState.FAIL_GRAPH_DEPENDENCE
        ),
        "insufficient_count": states.count(QualificationState.INSUFFICIENT),
        "not_run_count": states.count(QualificationState.NOT_RUN),
    }
    state = _worst_state(states)
    reasons = [
        reason
        for unit in units
        if unit.state is not QualificationState.PASS
        for reason in unit.reason_codes
    ]
    reasons.extend(
        reason
        for evidence in nonvacuity_by_id.values()
        if evidence.state is not QualificationState.PASS
        for reason in evidence.reason_codes
    )
    if state is QualificationState.FAIL_GRAPH_DEPENDENCE:
        reasons.append(REASON_D4_GRAPH_DEPENDENCE)
    return GateResult(
        gate_id=QualificationGateId.D4,
        state=state,
        evaluation_unit=evaluation_unit,
        reason_codes=_gate_reasons(
            state=state,
            source_reasons=reasons,
            marker=REASON_D4_PRIMARY_UNIT_NONPASS,
            empty_marker=REASON_D4_NO_PRIMARY_UNITS,
            attempted_count=counts["attempted_count"],
        ),
        **counts,
    )


def build_d5_gate(
    primary_units: Iterable[PrimaryUnitSummary],
    strata: Iterable[StratumSummary],
    coverage_policy: CoveragePolicy,
    *,
    expected_strata: Iterable[ExpectedStratum],
) -> GateResult:
    """Build D5 from the exact frozen stratum manifest.

    Supplying summaries that merely cover all primaries is insufficient: the
    IDs, required flags, evaluation units, memberships, counts, rates, and
    states must all be the deterministic summaries of the declared manifest.
    """

    primary_by_id = _index_unique(
        primary_units,
        item_type=PrimaryUnitSummary,
        id_attribute="primary_unit_id",
        label="D5 loop primary units",
    )
    units = tuple(primary_by_id[key] for key in sorted(primary_by_id))
    expected_stratum_tuple = tuple(expected_strata)
    derived_strata = summarize_strata(
        expected_stratum_tuple,
        units,
        coverage_policy,
    )
    strata_by_id = _index_unique(
        strata,
        item_type=StratumSummary,
        id_attribute="stratum_id",
        label="D5 strata",
    )
    derived_by_id = {stratum.stratum_id: stratum for stratum in derived_strata}
    if set(strata_by_id) != set(derived_by_id):
        raise QualificationContractError(
            "D5 strata must have the exact frozen expected-stratum IDs"
        )
    for stratum_id, derived in derived_by_id.items():
        if strata_by_id[stratum_id].to_dict() != derived.to_dict():
            raise QualificationContractError(
                f"D5 stratum {stratum_id!r} differs from its frozen manifest "
                "or mechanically derived summary"
            )
    required = tuple(
        strata_by_id[key] for key in sorted(strata_by_id) if strata_by_id[key].required
    )
    counts = _primary_counts(units)
    raw_state = _raw_primary_state(units)
    if not required:
        if counts["attempted_count"]:
            raise QualificationContractError(
                "D5 requires at least one required frozen stratum"
            )
        state = QualificationState.NOT_RUN
        reasons = [REASON_D5_NO_REQUIRED_STRATA]
    else:
        required_members = {
            primary_id
            for stratum in required
            for primary_id in stratum.primary_unit_ids
        }
        if required_members != set(primary_by_id):
            raise QualificationContractError(
                "D5 required strata must cover the expected-primary denominator"
            )
        if any(
            stratum.evaluation_unit is not coverage_policy.evaluation_unit
            for stratum in required
        ):
            raise QualificationContractError(
                "D5 stratum units must match the coverage policy"
            )
        state = _worst_state((raw_state, *(stratum.state for stratum in required)))
        reasons = [
            reason
            for stratum in required
            if stratum.state is not QualificationState.PASS
            for reason in stratum.reason_codes
        ]
    return GateResult(
        gate_id=QualificationGateId.D5,
        state=state,
        evaluation_unit=coverage_policy.evaluation_unit,
        reason_codes=_gate_reasons(
            state=state,
            source_reasons=reasons,
            marker=REASON_D5_REQUIRED_STRATUM_NONPASS,
            empty_marker=REASON_D5_NO_PRIMARY_UNITS,
            attempted_count=counts["attempted_count"],
        ),
        **counts,
    )


@dataclass(frozen=True, slots=True)
class D4D5Aggregation:
    """Normalized loop evidence and its D4/D5 summaries."""

    crossed_cells: tuple[CrossedCellSummary, ...]
    primary_units: tuple[PrimaryUnitSummary, ...]
    crossed_nonvacuity: tuple[CrossedNonvacuitySummary, ...]
    strata: tuple[StratumSummary, ...]
    d4_gate: GateResult
    d5_gate: GateResult


def aggregate_d4_d5(
    *,
    expected_cells: Iterable[ExpectedCell],
    expected_strata: Iterable[ExpectedStratum],
    coverage_policy: CoveragePolicy,
    observed_cells: Iterable[CrossedCellSummary],
    primary_unit_templates: Iterable[PrimaryUnitSummary],
    crossed_nonvacuity: Iterable[CrossedNonvacuitySummary],
    graph_total_tolerance_cycles: float,
) -> D4D5Aggregation:
    """Run exact loop normalization through D4 and D5."""

    expected_cell_tuple = tuple(expected_cells)
    expected_stratum_tuple = tuple(expected_strata)
    crossed = materialize_expected_cells(expected_cell_tuple, observed_cells)
    primary = collapse_primary_units(
        expected_cell_tuple,
        crossed,
        primary_unit_templates,
        graph_total_tolerance_cycles=graph_total_tolerance_cycles,
    )
    nonvacuity_tuple = tuple(crossed_nonvacuity)
    strata = summarize_strata(
        expected_stratum_tuple,
        primary,
        coverage_policy,
    )
    return D4D5Aggregation(
        crossed_cells=crossed,
        primary_units=primary,
        crossed_nonvacuity=nonvacuity_tuple,
        strata=strata,
        d4_gate=build_d4_gate(
            primary,
            nonvacuity_tuple,
            evaluation_unit=coverage_policy.evaluation_unit,
        ),
        d5_gate=build_d5_gate(
            primary,
            strata,
            coverage_policy,
            expected_strata=expected_stratum_tuple,
        ),
    )
