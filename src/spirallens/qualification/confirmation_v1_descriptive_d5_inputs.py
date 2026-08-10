"""Private D5 input reconstruction for the D7 v1 descriptive successor."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence

from .common import QualificationContractError
from .confirmation_v1_descriptive_common import (
    _REPRESENTATION_D3_CYCLE_GRAPH_IDS,
    _REPRESENTATION_D3_FIELD_GRAPH_IDS,
    _integer,
    _mapping,
    _number,
    _sequence,
    _string,
)

__all__: tuple[str, ...] = ()


def _stress_stratum_ids(unit: Mapping[str, object]) -> list[str]:
    result = []
    seen_axes: set[str] = set()
    for item in _sequence(unit.get("stress_assignments"), label="stress assignments"):
        assignment = _mapping(item, label="stress assignment")
        axis_id = _string(assignment.get("axis_id"), label="axis_id")
        level = _string(assignment.get("level"), label="level")
        if axis_id in seen_axes:
            raise QualificationContractError("stress assignment axis is duplicated")
        seen_axes.add(axis_id)
        result.append(f"stress.{axis_id}.{level}")
    if len(result) != 3:
        raise QualificationContractError(
            "each D4/D5 execution must retain three stress assignments"
        )
    return result


def _d5_crossed_inputs(
    protocol: Mapping[str, object],
    result: Mapping[str, object],
) -> tuple[
    list[dict[str, object]],
    dict[str, dict[str, object]],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
]:
    graphs = _mapping(protocol.get("graphs"), label="graphs")
    field_graph_ids = tuple(
        _string(
            _mapping(item, label="field graph").get("graph_id"),
            label="field graph_id",
        )
        for item in _sequence(graphs.get("field_estimation"), label="field graphs")
    )
    cycle_graph_ids = tuple(
        _string(
            _mapping(item, label="cycle graph").get("graph_id"),
            label="cycle graph_id",
        )
        for item in _sequence(graphs.get("cycle_construction"), label="cycle graphs")
    )
    if (
        field_graph_ids != _REPRESENTATION_D3_FIELD_GRAPH_IDS
        or cycle_graph_ids != _REPRESENTATION_D3_CYCLE_GRAPH_IDS
    ):
        raise QualificationContractError("D5 graph order differs from the protocol")

    expected_strata = [
        _mapping(item, label="expected stratum")
        for item in _sequence(protocol.get("expected_strata"), label="expected strata")
    ]
    stratum_ids = tuple(
        _string(item.get("stratum_id"), label="expected stratum_id")
        for item in expected_strata
    )
    if len(stratum_ids) != 6 or len(set(stratum_ids)) != 6:
        raise QualificationContractError("D5 stress-stratum universe is not closed")

    expected_cells = [
        _mapping(item, label="expected crossed cell")
        for item in _sequence(protocol.get("expected_cells"), label="expected cells")
    ]
    expected_by_id = {
        _string(item.get("cell_id"), label="expected cell_id"): item
        for item in expected_cells
    }
    cells = [
        _mapping(item, label="crossed cell")
        for item in _sequence(result.get("crossed_cells"), label="crossed cells")
    ]
    observed_by_id = {
        _string(item.get("cell_id"), label="crossed cell_id"): item for item in cells
    }
    if (
        len(expected_by_id) != 1_152
        or len(observed_by_id) != 1_152
        or set(expected_by_id) != set(observed_by_id)
    ):
        raise QualificationContractError(
            "D5 crossed cells differ from the exact protocol universe"
        )
    primary_units = {
        _string(
            _mapping(item, label="primary unit").get("primary_unit_id"),
            label="primary_unit_id",
        ): _mapping(item, label="primary unit")
        for item in _sequence(result.get("primary_units"), label="primary units")
    }
    if len(primary_units) != 64:
        raise QualificationContractError("D5 primary-unit universe is not closed")
    for cell_id, expected in expected_by_id.items():
        observed = observed_by_id[cell_id]
        direct_fields = (
            "primary_unit_id",
            "field_graph_id",
            "cycle_graph_id",
            "loop_role",
        )
        if any(observed.get(field) != expected.get(field) for field in direct_fields):
            raise QualificationContractError(
                "D5 crossed cell differs from its protocol identity"
            )
        if observed.get("expected_disposition") != expected.get(
            "expected_loop_disposition"
        ):
            raise QualificationContractError(
                "D5 crossed cell disposition differs from the protocol"
            )
        primary_unit_id = _string(
            observed.get("primary_unit_id"), label="crossed primary_unit_id"
        )
        unit = primary_units.get(primary_unit_id)
        if unit is None:
            raise QualificationContractError(
                "D5 crossed cell has no parent primary unit"
            )
        expected_ids = [
            _string(value, label="expected stratum membership")
            for value in _sequence(
                expected.get("stratum_ids"), label="expected stratum memberships"
            )
        ]
        if expected_ids != _stress_stratum_ids(unit) or not set(expected_ids) <= set(
            stratum_ids
        ):
            raise QualificationContractError(
                "D5 crossed-cell stress membership differs"
            )
    return (
        cells,
        expected_by_id,
        stratum_ids,
        field_graph_ids,
        cycle_graph_ids,
    )


def _stress_graph_rows(
    cells: Sequence[Mapping[str, object]],
    expected_by_id: Mapping[str, Mapping[str, object]],
    stratum_ids: Sequence[str],
    field_graph_ids: Sequence[str],
    cycle_graph_ids: Sequence[str],
) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str, str], list[Mapping[str, object]]] = defaultdict(
        list
    )
    for cell in cells:
        cell_id = _string(cell.get("cell_id"), label="crossed cell_id")
        expected = expected_by_id[cell_id]
        for stratum_id in _sequence(
            expected.get("stratum_ids"), label="expected stratum memberships"
        ):
            grouped[
                (
                    _string(stratum_id, label="stratum_id"),
                    _string(cell.get("loop_role"), label="loop_role"),
                    _string(cell.get("field_graph_id"), label="field_graph_id"),
                    _string(cell.get("cycle_graph_id"), label="cycle_graph_id"),
                )
            ].append(cell)

    rows = []
    for stratum_id in stratum_ids:
        for loop_role in ("offcore_control", "primary_boundary"):
            for field_graph_id in field_graph_ids:
                for cycle_graph_id in cycle_graph_ids:
                    key = (stratum_id, loop_role, field_graph_id, cycle_graph_id)
                    members = grouped.get(key, [])
                    if len(members) != 32:
                        raise QualificationContractError(
                            "each D5 role-graph stress row must retain 32 cells"
                        )
                    errors = [
                        _number(
                            member.get("oracle_absolute_error_cycles"),
                            label="oracle absolute error",
                        )
                        for member in members
                        if member.get("oracle_absolute_error_cycles") is not None
                    ]
                    if len(errors) != 24:
                        raise QualificationContractError(
                            "each D5 role-graph stress row must retain 24 errors"
                        )
                    maximum_error = max(errors)
                    rows.append(
                        {
                            "stratum_id": stratum_id,
                            "field_graph_id": field_graph_id,
                            "cycle_graph_id": cycle_graph_id,
                            "loop_role": loop_role,
                            "attempted_execution_count": len(members),
                            "evaluable_execution_count": sum(
                                member.get("attempt_status") == "evaluable"
                                for member in members
                            ),
                            "prerequisite_execution_count": sum(
                                member.get("expected_disposition")
                                == "prerequisite_failure"
                                for member in members
                            ),
                            "maximum_oracle_absolute_error_cycles": maximum_error,
                            "worst_cell_ids": sorted(
                                _string(member.get("cell_id"), label="cell_id")
                                for member in members
                                if member.get("oracle_absolute_error_cycles")
                                == maximum_error
                            ),
                            "state_counts": dict(
                                sorted(
                                    Counter(
                                        _string(member.get("state"), label="state")
                                        for member in members
                                    ).items()
                                )
                            ),
                        }
                    )
    if len(rows) != 108 or set(grouped) != {
        (
            stratum_id,
            loop_role,
            field_graph_id,
            cycle_graph_id,
        )
        for stratum_id in stratum_ids
        for loop_role in ("offcore_control", "primary_boundary")
        for field_graph_id in field_graph_ids
        for cycle_graph_id in cycle_graph_ids
    }:
        raise QualificationContractError("D5 role-graph stress table is not closed")
    return rows


def _role_primary_units(
    result: Mapping[str, object],
    expected_by_id: Mapping[str, Mapping[str, object]],
) -> list[dict[str, object]]:
    primary_values = [
        _mapping(item, label="primary unit")
        for item in _sequence(result.get("primary_units"), label="primary units")
    ]
    primary = {
        _string(item.get("primary_unit_id"), label="primary_unit_id"): item
        for item in primary_values
    }
    if len(primary) != 64:
        raise QualificationContractError("D5 primary-unit universe is not closed")
    groups: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for item in _sequence(result.get("crossed_cells"), label="crossed cells"):
        cell = _mapping(item, label="crossed cell")
        cell_id = _string(cell.get("cell_id"), label="crossed cell_id")
        if cell_id not in expected_by_id:
            raise QualificationContractError(
                "D5 role reduction contains an unexpected crossed cell"
            )
        groups[
            (
                _string(cell.get("primary_unit_id"), label="primary_unit_id"),
                _string(cell.get("loop_role"), label="loop_role"),
            )
        ].append(cell)
    rows = []
    for (primary_unit_id, loop_role), cells in sorted(groups.items()):
        if len(cells) != 9:
            raise QualificationContractError(
                "each primary-unit loop role must retain nine graph cells"
            )
        observed_pairs = {
            (
                _string(cell.get("field_graph_id"), label="field_graph_id"),
                _string(cell.get("cycle_graph_id"), label="cycle_graph_id"),
            )
            for cell in cells
        }
        if observed_pairs != {
            (field_graph_id, cycle_graph_id)
            for field_graph_id in _REPRESENTATION_D3_FIELD_GRAPH_IDS
            for cycle_graph_id in _REPRESENTATION_D3_CYCLE_GRAPH_IDS
        }:
            raise QualificationContractError(
                "D5 role reduction differs from the nine graph pairs"
            )
        expected = {str(cell["expected_disposition"]) for cell in cells}
        predictions = {str(cell["prediction_class"]) for cell in cells}
        attempts = {str(cell["attempt_status"]) for cell in cells}
        if len(expected) != 1 or len(predictions) != 1 or len(attempts) != 1:
            raise QualificationContractError("graph-cell role projection disagrees")
        unit = primary[primary_unit_id]
        totals = [
            _number(cell.get("continuous_signed_total_cycles"), label="signed total")
            for cell in cells
            if cell.get("continuous_signed_total_cycles") is not None
        ]
        errors = [
            _number(cell.get("oracle_absolute_error_cycles"), label="oracle error")
            for cell in cells
            if cell.get("oracle_absolute_error_cycles") is not None
        ]
        if (not totals) != (next(iter(attempts)) == "insufficient") or len(
            totals
        ) != len(errors):
            raise QualificationContractError(
                "D5 role reduction evaluability differs across graph cells"
            )
        maximum_error = max(errors) if errors else None
        minimum_total = min(totals) if totals else None
        maximum_total = max(totals) if totals else None
        rows.append(
            {
                "primary_unit_id": primary_unit_id,
                "loop_role": loop_role,
                "expected_disposition": next(iter(expected)),
                "prediction_class": next(iter(predictions)),
                "attempt_status": next(iter(attempts)),
                "state": "pass"
                if all(cell["state"] == "pass" for cell in cells)
                else "fail",
                "control_id": unit["control_id"],
                "stratum_ids": _stress_stratum_ids(unit),
                "graph_cell_count": len(cells),
                "continuous_span_cycles": (
                    maximum_total - minimum_total
                    if minimum_total is not None and maximum_total is not None
                    else None
                ),
                "span_endpoint_cell_ids": sorted(
                    _string(cell.get("cell_id"), label="cell_id")
                    for cell in cells
                    if cell.get("continuous_signed_total_cycles")
                    in {minimum_total, maximum_total}
                )
                if totals
                else [],
                "maximum_oracle_absolute_error_cycles": maximum_error,
                "worst_error_cell_ids": sorted(
                    _string(cell.get("cell_id"), label="cell_id")
                    for cell in cells
                    if maximum_error is not None
                    and cell.get("oracle_absolute_error_cycles") == maximum_error
                ),
            }
        )
    if len(rows) != 128 or {
        (str(row["primary_unit_id"]), str(row["loop_role"])) for row in rows
    } != {
        (primary_unit_id, loop_role)
        for primary_unit_id in primary
        for loop_role in ("offcore_control", "primary_boundary")
    }:
        raise QualificationContractError(
            "D5 within-execution role reduction is not closed"
        )
    return rows


_PERSISTED_STRATUM_KEYS = frozenset(
    {
        "abstention_fraction",
        "all_expected_primary_units_must_pass",
        "attempt_insufficient_count",
        "attempt_not_run_count",
        "attempted_count",
        "coverage",
        "evaluable_count",
        "evaluation_unit",
        "fail_count",
        "fail_graph_dependence_count",
        "graph_cells_are_repeated_measures",
        "insufficient_count",
        "negative_expected_count",
        "negative_pass_count",
        "not_run_count",
        "pass_count",
        "positive_expected_count",
        "positive_pass_count",
        "prerequisite_expected_count",
        "prerequisite_pass_count",
        "prerequisite_rate_handling",
        "primary_unit_ids",
        "rate_eligible_count",
        "rate_evaluable_count",
        "rate_insufficient_count",
        "rate_not_run_count",
        "reason_codes",
        "recall",
        "required",
        "score_denominator",
        "specificity",
        "state",
        "stratum_id",
    }
)


def _persisted_stratum_rows(
    protocol: Mapping[str, object],
    result: Mapping[str, object],
) -> list[dict[str, object]]:
    expected = [
        _mapping(item, label="expected stratum")
        for item in _sequence(protocol.get("expected_strata"), label="expected strata")
    ]
    observed = [
        _mapping(item, label="stress stratum")
        for item in _sequence(result.get("strata"), label="strata")
    ]
    if len(expected) != 6 or len(observed) != 6:
        raise QualificationContractError("D5 persisted strata are not closed")
    rows = []
    for expected_item, item in zip(expected, observed, strict=True):
        if set(item) != _PERSISTED_STRATUM_KEYS:
            raise QualificationContractError(
                "D5 persisted stratum fields differ from the 33-field record"
            )
        primary_unit_ids = [
            _string(value, label="stratum primary_unit_id")
            for value in _sequence(
                item.get("primary_unit_ids"), label="stratum primary_unit_ids"
            )
        ]
        if (
            item.get("stratum_id") != expected_item.get("stratum_id")
            or primary_unit_ids != expected_item.get("primary_unit_ids")
            or len(primary_unit_ids) != 32
            or len(set(primary_unit_ids)) != 32
            or item.get("evaluation_unit") != expected_item.get("evaluation_unit")
            or item.get("required") != expected_item.get("required")
        ):
            raise QualificationContractError(
                "D5 persisted stratum identity differs from the protocol"
            )
        exact_values = {
            "attempted_count": 32,
            "evaluable_count": 24,
            "attempt_insufficient_count": 8,
            "attempt_not_run_count": 0,
            "pass_count": 32,
            "fail_count": 0,
            "rate_eligible_count": 24,
            "rate_evaluable_count": 24,
            "rate_insufficient_count": 0,
            "rate_not_run_count": 0,
            "prerequisite_expected_count": 8,
            "prerequisite_pass_count": 8,
            "coverage": 1.0,
            "abstention_fraction": 0.0,
            "recall": 1.0,
            "specificity": 1.0,
            "graph_cells_are_repeated_measures": True,
            "score_denominator": "expected_nonprerequisite_primary_units",
            "prerequisite_rate_handling": "excluded_but_mandatory",
            "state": "pass",
        }
        if any(item.get(key) != value for key, value in exact_values.items()):
            raise QualificationContractError(
                "D5 persisted stratum metric differs from the parent record"
            )
        rows.append(dict(item))
    return rows


def _prerequisite_member_rows(
    result: Mapping[str, object],
    bundle: Mapping[str, object],
    core_primary_units: Sequence[Mapping[str, object]],
    loop_primary_units: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    core_by_primary = {
        _string(item.get("primary_unit_id"), label="core primary_unit_id"): item
        for item in core_primary_units
        if item.get("expected_disposition") == "prerequisite_failure"
    }
    loop_by_primary = {
        _string(item.get("primary_unit_id"), label="loop primary_unit_id"): item
        for item in loop_primary_units
        if item.get("expected_disposition") == "prerequisite_failure"
    }
    core_cells = {
        _string(item.get("core_cell_id"), label="core_cell_id"): item
        for item in (
            _mapping(value, label="core cell")
            for value in _sequence(result.get("core_cells"), label="core cells")
        )
    }
    loop_cells = {
        _string(item.get("cell_id"), label="loop cell_id"): item
        for item in (
            _mapping(value, label="loop cell")
            for value in _sequence(result.get("crossed_cells"), label="crossed cells")
        )
    }
    core_evidence = {
        _string(item.get("core_cell_id"), label="core_cell_id"): item
        for item in (
            _mapping(value, label="core evidence")
            for value in _sequence(
                bundle.get("core_cell_receipts"), label="core cell receipts"
            )
        )
    }
    loop_evidence = {
        _string(item.get("cell_id"), label="loop cell_id"): item
        for item in (
            _mapping(value, label="loop evidence")
            for value in _sequence(
                bundle.get("loop_cell_receipts"), label="loop cell receipts"
            )
        )
    }
    if (
        len(core_by_primary) != 16
        or len(loop_by_primary) != 16
        or set(core_by_primary) != set(loop_by_primary)
    ):
        raise QualificationContractError(
            "mandatory prerequisite member universe differs"
        )
    rows = []
    for primary_unit_id in sorted(core_by_primary):
        core = core_by_primary[primary_unit_id]
        loop = loop_by_primary[primary_unit_id]
        if any(
            core.get(field) != loop.get(field)
            for field in (
                "control_id",
                "selection_seed",
                "stress_assignments",
                "expected_disposition",
            )
        ):
            raise QualificationContractError(
                "core and loop prerequisite primary identities differ"
            )
        selected_core = [
            core_cells[_string(value, label="core_cell_id")]
            for value in _sequence(core.get("core_cell_ids"), label="core_cell_ids")
        ]
        selected_loop = [
            loop_cells[_string(value, label="loop cell_id")]
            for value in _sequence(
                loop.get("crossed_cell_ids"), label="crossed_cell_ids"
            )
        ]
        required_pass = all(
            item.get("attempt_status") == "insufficient"
            and item.get("prediction_class") == "abstain"
            and item.get("state") == "pass"
            for item in (core, loop, *selected_core, *selected_loop)
        )
        rows.append(
            {
                "primary_unit_id": primary_unit_id,
                "control_id": _string(core.get("control_id"), label="control_id"),
                "selection_seed": _integer(
                    core.get("selection_seed"), label="selection_seed"
                ),
                "stress_assignments": [
                    dict(_mapping(value, label="stress assignment"))
                    for value in _sequence(
                        core.get("stress_assignments"), label="stress assignments"
                    )
                ],
                "stratum_ids": _stress_stratum_ids(core),
                "core_primary_attempt_status": _string(
                    core.get("attempt_status"), label="core attempt_status"
                ),
                "core_primary_prediction_class": _string(
                    core.get("prediction_class"), label="core prediction_class"
                ),
                "loop_primary_attempt_status": _string(
                    loop.get("attempt_status"), label="loop attempt_status"
                ),
                "loop_primary_prediction_class": _string(
                    loop.get("prediction_class"), label="loop prediction_class"
                ),
                "expected_prerequisite_failure_is_required_pass_route": (required_pass),
                "core_cells": [
                    {
                        "core_cell_id": _string(
                            item.get("core_cell_id"), label="core_cell_id"
                        ),
                        "field_graph_id": _string(
                            item.get("field_graph_id"), label="field_graph_id"
                        ),
                        "reason_codes": [
                            _string(reason, label="core reason code")
                            for reason in _sequence(
                                _mapping(
                                    core_evidence[str(item["core_cell_id"])].get(
                                        "sealed_prediction_receipt"
                                    ),
                                    label="core sealed prediction",
                                ).get("reason_codes"),
                                label="core reason codes",
                            )
                        ],
                    }
                    for item in sorted(
                        selected_core, key=lambda value: str(value["core_cell_id"])
                    )
                ],
                "loop_cells": [
                    {
                        "cell_id": _string(item.get("cell_id"), label="cell_id"),
                        "field_graph_id": _string(
                            item.get("field_graph_id"), label="field_graph_id"
                        ),
                        "cycle_graph_id": _string(
                            item.get("cycle_graph_id"), label="cycle_graph_id"
                        ),
                        "loop_role": _string(item.get("loop_role"), label="loop_role"),
                        "reason_codes": [
                            _string(reason, label="loop reason code")
                            for reason in _sequence(
                                _mapping(
                                    loop_evidence[str(item["cell_id"])].get(
                                        "sealed_prediction_receipt"
                                    ),
                                    label="loop sealed prediction",
                                ).get("reason_codes"),
                                label="loop reason codes",
                            )
                        ],
                    }
                    for item in sorted(
                        selected_loop, key=lambda value: str(value["cell_id"])
                    )
                ],
            }
        )
    if (
        any(
            row["expected_prerequisite_failure_is_required_pass_route"] is not True
            for row in rows
        )
        or sum(len(row["core_cells"]) for row in rows) != 48
        or sum(len(row["loop_cells"]) for row in rows) != 288
    ):
        raise QualificationContractError(
            "mandatory prerequisite leaf coverage differs from 48/288"
        )
    return rows
