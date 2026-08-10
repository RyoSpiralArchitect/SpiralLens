"""Private D4 descriptive work package for the D7 v1 successor."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence

from spirallens.core.canonical import canonical_json_bytes, sha256_bytes

from .common import QualificationContractError
from . import confirmation_v1_records as records
from .confirmation_v1_descriptive_common import (
    _boolean,
    _integer,
    _mapping,
    _number,
    _output,
    _sequence,
    _string,
)

__all__: tuple[str, ...] = ()


def _crossed_summary(
    members: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    totals = [
        _number(item["continuous_signed_total_cycles"], label="signed total")
        for item in members
        if item.get("continuous_signed_total_cycles") is not None
    ]
    errors = [
        _number(item["oracle_absolute_error_cycles"], label="oracle error")
        for item in members
        if item.get("oracle_absolute_error_cycles") is not None
    ]
    return {
        "cell_count": len(members),
        "cell_ids": sorted(
            _string(item.get("cell_id"), label="crossed cell_id") for item in members
        ),
        "unique_execution_count": len(
            {
                _string(item.get("primary_unit_id"), label="primary_unit_id")
                for item in members
            }
        ),
        "evaluable_cell_count": sum(
            item["attempt_status"] == "evaluable" for item in members
        ),
        "prerequisite_cell_count": sum(
            item["attempt_status"] == "insufficient" for item in members
        ),
        "minimum_continuous_signed_total_cycles": min(totals) if totals else None,
        "maximum_continuous_signed_total_cycles": max(totals) if totals else None,
        "maximum_oracle_absolute_error_cycles": max(errors) if errors else None,
    }


def _d4_optional_number(value: object, *, label: str) -> float | None:
    return None if value is None else _number(value, label=label)


def _d4_string_fields(
    source: Mapping[str, object], fields: Sequence[str]
) -> dict[str, str]:
    return {field: _string(source.get(field), label=f"D4 {field}") for field in fields}


def _d4_string_list(value: object, *, label: str) -> list[str]:
    return [_string(item, label=label) for item in _sequence(value, label=f"{label}s")]


def _d4_index(value: object, *, key: str, label: str) -> dict[str, dict[str, object]]:
    result = {}
    for item in _sequence(value, label=label):
        row = _mapping(item, label=label.removesuffix("s"))
        identity = _string(row.get(key), label=f"{label} {key}")
        if identity in result:
            raise QualificationContractError(f"{label} contains duplicate {key}")
        result[identity] = row
    return result


def _d4_stress_assignments(unit: Mapping[str, object]) -> list[dict[str, str]]:
    rows = []
    for item in _sequence(unit.get("stress_assignments"), label="stress assignments"):
        assignment = _mapping(item, label="stress assignment")
        rows.append(
            {
                "axis_id": _string(assignment.get("axis_id"), label="stress axis_id"),
                "level": _string(assignment.get("level"), label="stress level"),
            }
        )
    if len(rows) != 3 or len({row["axis_id"] for row in rows}) != 3:
        raise QualificationContractError(
            "each D4 execution must retain three distinct stress assignments"
        )
    return rows


def _d4_unit_fields(unit: Mapping[str, object]) -> dict[str, object]:
    return {
        **_d4_string_fields(unit, ("primary_unit_id", "control_id")),
        "selection_seed": _integer(unit.get("selection_seed"), label="selection_seed"),
        "stress_assignments": _d4_stress_assignments(unit),
    }


def _d4_descriptor(value: object, *, label: str) -> dict[str, object]:
    descriptor = _mapping(value, label=label)
    if set(descriptor) != {"dtype", "shape", "sha256"}:
        raise QualificationContractError(f"{label} descriptor fields differ")
    shape = [
        _integer(item, label=f"{label} shape")
        for item in _sequence(descriptor.get("shape"), label=f"{label} shape")
    ]
    if not shape or any(dimension <= 0 for dimension in shape):
        raise QualificationContractError(f"{label} shape must be positive")
    return {
        "dtype": _string(descriptor.get("dtype"), label=f"{label} dtype"),
        "shape": shape,
        "sha256": _string(descriptor.get("sha256"), label=f"{label} sha256"),
    }


def _d4_pair_class(field_graph_id: str, cycle_graph_id: str) -> str:
    return (
        "diagonal"
        if field_graph_id.removeprefix("a-") == cycle_graph_id.removeprefix("b-")
        else "offdiagonal"
    )


def _d4_cell_row(cell: Mapping[str, object]) -> dict[str, object]:
    field_graph_id = _string(cell.get("field_graph_id"), label="field_graph_id")
    cycle_graph_id = _string(cell.get("cycle_graph_id"), label="cycle_graph_id")
    return {
        **_d4_string_fields(
            cell,
            (
                "cell_id",
                "field_graph_id",
                "cycle_graph_id",
                "attempt_status",
                "expected_disposition",
                "prediction_class",
                "state",
            ),
        ),
        "pair_class": _d4_pair_class(field_graph_id, cycle_graph_id),
        "continuous_signed_total_cycles": _d4_optional_number(
            cell.get("continuous_signed_total_cycles"), label="crossed signed total"
        ),
        "oracle_absolute_error_cycles": _d4_optional_number(
            cell.get("oracle_absolute_error_cycles"), label="crossed oracle error"
        ),
    }


def _d4_index_inputs(
    result: Mapping[str, object],
) -> tuple[
    dict[str, dict[str, object]],
    dict[str, list[dict[str, object]]],
    dict[str, dict[str, object]],
    dict[str, dict[str, object]],
]:
    field_graph_ids = ("a-mutual", "a-radius", "a-shared")
    cycle_graph_ids = ("b-mutual", "b-radius", "b-shared")
    loop_roles = ("offcore_control", "primary_boundary")
    expected_coordinates = {
        (field_graph_id, cycle_graph_id, loop_role)
        for field_graph_id in field_graph_ids
        for cycle_graph_id in cycle_graph_ids
        for loop_role in loop_roles
    }

    units = _d4_index(
        result.get("primary_units"), key="primary_unit_id", label="primary units"
    )
    for unit in units.values():
        _d4_stress_assignments(unit)
    if len(units) != 64:
        raise QualificationContractError("D4 must retain exactly 64 executions")
    if Counter(str(unit.get("attempt_status")) for unit in units.values()) != {
        "evaluable": 48,
        "insufficient": 16,
    } or any(unit.get("state") != "pass" for unit in units.values()):
        raise QualificationContractError(
            "D4 execution disposition counts differ from the frozen grain"
        )

    cells_by_id = _d4_index(
        result.get("crossed_cells"), key="cell_id", label="crossed cells"
    )
    cells_by_unit: dict[str, list[dict[str, object]]] = defaultdict(list)
    for cell in cells_by_id.values():
        primary_unit_id = _string(
            cell.get("primary_unit_id"), label="crossed primary_unit_id"
        )
        if primary_unit_id not in units:
            raise QualificationContractError("D4 crossed-cell identity is not closed")
        cells_by_unit[primary_unit_id].append(cell)
    if len(cells_by_id) != 1_152 or set(cells_by_unit) != set(units):
        raise QualificationContractError("D4 must retain exactly 1,152 crossed cells")
    for primary_unit_id, members in cells_by_unit.items():
        coordinates = {
            (
                _string(cell.get("field_graph_id"), label="field_graph_id"),
                _string(cell.get("cycle_graph_id"), label="cycle_graph_id"),
                _string(cell.get("loop_role"), label="loop_role"),
            )
            for cell in members
        }
        declared_ids = {
            _string(cell_id, label="declared crossed cell_id")
            for cell_id in _sequence(
                units[primary_unit_id].get("crossed_cell_ids"),
                label="declared crossed cell ids",
            )
        }
        if (
            len(members) != 18
            or coordinates != expected_coordinates
            or declared_ids != {str(cell["cell_id"]) for cell in members}
        ):
            raise QualificationContractError(
                "each D4 execution must retain the exact 3x3x2 crossed leaf set"
            )

    bundle = _mapping(result.get("evidence_bundle"), label="evidence bundle")
    loop_evidence = _d4_index(
        bundle.get("loop_cell_receipts"),
        key="cell_id",
        label="loop cell receipts",
    )
    if set(loop_evidence) != set(cells_by_id):
        raise QualificationContractError("D4 loop evidence does not cover every leaf")
    for cell_id, evidence in loop_evidence.items():
        cell = cells_by_id[cell_id]
        normalized_sha256 = _string(
            evidence.get("normalized_summary_sha256"),
            label="loop normalized summary sha256",
        )
        if sha256_bytes(canonical_json_bytes(cell)) != normalized_sha256:
            raise QualificationContractError(
                "D4 loop normalized summary digest differs"
            )
        for receipt_key, fingerprint_key in (
            ("blind_input_receipt", "blind_input_fingerprint_sha256"),
            ("sealed_prediction_receipt", "prediction_fingerprint_sha256"),
            ("oracle_truth_receipt", "oracle_fingerprint_sha256"),
        ):
            receipt = _mapping(evidence.get(receipt_key), label=receipt_key)
            if sha256_bytes(canonical_json_bytes(receipt)) != cell.get(fingerprint_key):
                raise QualificationContractError(
                    f"D4 {receipt_key} fingerprint join differs"
                )
    nonvacuity = _d4_index(
        result.get("crossed_nonvacuity"),
        key="primary_unit_id",
        label="crossed nonvacuity rows",
    )
    nonvacuity_evidence = _d4_index(
        bundle.get("nonvacuity_receipts"),
        key="primary_unit_id",
        label="nonvacuity receipts",
    )
    if set(nonvacuity) != set(units) or set(nonvacuity_evidence) != set(units):
        raise QualificationContractError(
            "D4 nonvacuity receipts must cover all 64 executions"
        )
    for primary_unit_id, evidence in nonvacuity_evidence.items():
        summary = nonvacuity[primary_unit_id]
        receipt = _mapping(
            evidence.get("crossed_nonvacuity_receipt"),
            label="crossed nonvacuity receipt",
        )
        if (
            sha256_bytes(canonical_json_bytes(summary))
            != evidence.get("normalized_summary_sha256")
            or sha256_bytes(canonical_json_bytes(receipt))
            != summary.get("receipt_fingerprint_sha256")
            or receipt.get("field_graph_pair_effects")
            != summary.get("field_graph_pair_effects")
        ):
            raise QualificationContractError("D4 nonvacuity receipt join differs")
    return units, cells_by_unit, loop_evidence, nonvacuity_evidence


def _d4_outputs(result: Mapping[str, object]) -> list[records.D7V1DescriptiveOutput]:
    (
        units,
        cells_by_unit,
        loop_evidence,
        nonvacuity_evidence,
    ) = _d4_index_inputs(result)
    all_cells = [cell for members in cells_by_unit.values() for cell in members]
    field_graph_ids = ("a-mutual", "a-radius", "a-shared")
    cycle_graph_ids = ("b-mutual", "b-radius", "b-shared")
    loop_roles = ("offcore_control", "primary_boundary")

    matrix_rows = []
    role_rows = []
    for primary_unit_id, unit in sorted(units.items()):
        unit_fields = _d4_unit_fields(unit)
        members = cells_by_unit[primary_unit_id]
        for loop_role in loop_roles:
            role_members = sorted(
                (cell for cell in members if cell.get("loop_role") == loop_role),
                key=lambda cell: (
                    str(cell["field_graph_id"]),
                    str(cell["cycle_graph_id"]),
                ),
            )
            matrix_rows.append(
                {
                    **unit_fields,
                    "loop_role": loop_role,
                    "field_graph_ids": list(field_graph_ids),
                    "cycle_graph_ids": list(cycle_graph_ids),
                    "cells": [_d4_cell_row(cell) for cell in role_members],
                }
            )
            summary = _crossed_summary(role_members)
            maximum_error = summary["maximum_oracle_absolute_error_cycles"]
            role_rows.append(
                {
                    **unit_fields,
                    "loop_role": loop_role,
                    "cell_count": summary["cell_count"],
                    "cell_ids": summary["cell_ids"],
                    "evaluable_cell_count": summary["evaluable_cell_count"],
                    "prerequisite_cell_count": summary["prerequisite_cell_count"],
                    "continuous_total_min_cycles": (
                        summary["minimum_continuous_signed_total_cycles"]
                    ),
                    "continuous_total_max_cycles": (
                        summary["maximum_continuous_signed_total_cycles"]
                    ),
                    "continuous_total_span_cycles": (
                        None
                        if summary["minimum_continuous_signed_total_cycles"] is None
                        else float(summary["maximum_continuous_signed_total_cycles"])
                        - float(summary["minimum_continuous_signed_total_cycles"])
                    ),
                    "maximum_oracle_absolute_error_cycles": maximum_error,
                    "worst_oracle_cell_ids": sorted(
                        str(cell["cell_id"])
                        for cell in role_members
                        if maximum_error is not None
                        and cell.get("oracle_absolute_error_cycles") == maximum_error
                    ),
                    "abstention_reason_codes": sorted(
                        {
                            _string(reason, label="sealed prediction reason code")
                            for cell in role_members
                            for reason in _sequence(
                                _mapping(
                                    loop_evidence[str(cell["cell_id"])].get(
                                        "sealed_prediction_receipt"
                                    ),
                                    label="sealed loop prediction receipt",
                                ).get("reason_codes"),
                                label="sealed prediction reason codes",
                            )
                        }
                    ),
                }
            )

    diagonal_groups: dict[tuple[str, str], list[Mapping[str, object]]] = defaultdict(
        list
    )
    for cell in all_cells:
        field_graph_id = _string(cell.get("field_graph_id"), label="field_graph_id")
        cycle_graph_id = _string(cell.get("cycle_graph_id"), label="cycle_graph_id")
        diagonal_groups[
            (
                _string(cell.get("loop_role"), label="loop_role"),
                _d4_pair_class(field_graph_id, cycle_graph_id),
            )
        ].append(cell)
    diagonal_rows = []
    for (loop_role, pair_class), members in sorted(diagonal_groups.items()):
        summary = _crossed_summary(members)
        diagonal_rows.append(
            {
                "loop_role": loop_role,
                "pair_class": pair_class,
                "cell_count": summary["cell_count"],
                "unique_execution_count": summary["unique_execution_count"],
                "evaluable_cell_count": summary["evaluable_cell_count"],
                "prerequisite_cell_count": summary["prerequisite_cell_count"],
                "graph_cells_are_repeated_measures": True,
            }
        )

    adjacency_rows = []
    component_row_count = 0
    loop_contrast_row_count = 0
    component_rms_values: list[float] = []
    loop_contrast_values: list[float] = []
    expected_pair_ids = {
        "a-mutual--a-radius",
        "a-mutual--a-shared",
        "a-radius--a-shared",
    }
    for primary_unit_id, unit in sorted(units.items()):
        evidence = nonvacuity_evidence[primary_unit_id]
        receipt = _mapping(
            evidence.get("crossed_nonvacuity_receipt"),
            label="crossed nonvacuity receipt",
        )
        effects = [
            _mapping(item, label="field graph pair effect")
            for item in _sequence(
                receipt.get("field_graph_pair_effects"),
                label="field graph pair effects",
            )
        ]
        if {str(effect.get("pair_id")) for effect in effects} != expected_pair_ids:
            raise QualificationContractError(
                "each D4 nonvacuity receipt must retain three field-graph pairs"
            )
        cell_index = {
            (
                str(cell["field_graph_id"]),
                str(cell["cycle_graph_id"]),
                str(cell["loop_role"]),
            ): cell
            for cell in cells_by_unit[primary_unit_id]
        }
        for effect in sorted(effects, key=lambda item: str(item["pair_id"])):
            left_field_graph_id = _string(
                effect.get("left_field_graph_id"), label="left field graph id"
            )
            right_field_graph_id = _string(
                effect.get("right_field_graph_id"), label="right field graph id"
            )
            component_effects = [
                dict(_mapping(item, label="field component effect"))
                for item in _sequence(
                    effect.get("component_effects"), label="component effects"
                )
            ]
            if {
                str(component.get("component_name")) for component in component_effects
            } != {
                "amplitude",
                "identifiability_score",
                "section_values",
                "edge_coherence",
            } or len(component_effects) != 4:
                raise QualificationContractError(
                    "each D4 field-pair effect must retain four exact components"
                )
            component_row_count += len(component_effects)
            component_rms_values.extend(
                _number(component.get("rms_distance"), label="component RMS distance")
                for component in component_effects
            )
            loop_contrasts = []
            for loop_role in loop_roles:
                for cycle_graph_id in cycle_graph_ids:
                    left = cell_index[(left_field_graph_id, cycle_graph_id, loop_role)]
                    right = cell_index[
                        (right_field_graph_id, cycle_graph_id, loop_role)
                    ]
                    left_total = _d4_optional_number(
                        left.get("continuous_signed_total_cycles"),
                        label="left loop total",
                    )
                    right_total = _d4_optional_number(
                        right.get("continuous_signed_total_cycles"),
                        label="right loop total",
                    )
                    signed_difference = (
                        None
                        if left_total is None or right_total is None
                        else right_total - left_total
                    )
                    absolute_difference = (
                        None if signed_difference is None else abs(signed_difference)
                    )
                    if absolute_difference is not None:
                        loop_contrast_values.append(absolute_difference)
                    loop_contrasts.append(
                        {
                            "cycle_graph_id": cycle_graph_id,
                            "loop_role": loop_role,
                            "left_cell_id": _string(
                                left.get("cell_id"), label="left cell_id"
                            ),
                            "right_cell_id": _string(
                                right.get("cell_id"), label="right cell_id"
                            ),
                            "left_total_cycles": left_total,
                            "right_total_cycles": right_total,
                            "signed_difference_cycles": signed_difference,
                            "absolute_difference_cycles": absolute_difference,
                        }
                    )
            loop_contrast_row_count += len(loop_contrasts)
            adjacency_rows.append(
                {
                    **_d4_unit_fields(unit),
                    **_d4_string_fields(
                        effect,
                        (
                            "pair_id",
                            "left_field_graph_id",
                            "right_field_graph_id",
                            "left_field_graph_fingerprint_sha256",
                            "right_field_graph_fingerprint_sha256",
                        ),
                    ),
                    "field_adjacency_identity_differs": (
                        effect.get("left_field_graph_fingerprint_sha256")
                        != effect.get("right_field_graph_fingerprint_sha256")
                    ),
                    "numeric_adjacency_difference_available": False,
                    "component_effects": component_effects,
                    "qualifying_substantive_components": _d4_string_list(
                        effect.get("qualifying_substantive_components"),
                        label="qualifying substantive component",
                    ),
                    "substantive_response_pass": _boolean(
                        effect.get("substantive_response_pass"),
                        label="substantive response pass",
                    ),
                    "loop_contrasts": loop_contrasts,
                }
            )
    if (
        len(adjacency_rows) != 192
        or component_row_count != 768
        or loop_contrast_row_count != 1_152
    ):
        raise QualificationContractError(
            "D4 effects must retain 192 field pairs, 768 components, "
            "and 1,152 contrasts"
        )

    support_rows = []
    for primary_unit_id, unit in sorted(units.items()):
        unit_fields = _d4_unit_fields(unit)
        stratum_ids = [
            f"stress.{item['axis_id']}.{item['level']}"
            for item in unit_fields["stress_assignments"]
        ]
        for cell in sorted(
            cells_by_unit[primary_unit_id],
            key=lambda item: str(item["cell_id"]),
        ):
            cell_id = _string(cell.get("cell_id"), label="crossed cell_id")
            evidence = loop_evidence[cell_id]
            blind = _mapping(
                evidence.get("blind_input_receipt"), label="blind loop input receipt"
            )
            prediction = _mapping(
                evidence.get("sealed_prediction_receipt"),
                label="sealed loop prediction receipt",
            )
            oracle = _mapping(
                evidence.get("oracle_truth_receipt"), label="loop oracle truth receipt"
            )
            if (
                prediction.get("observed_attempt_status") != cell.get("attempt_status")
                or prediction.get("prediction_class") != cell.get("prediction_class")
                or oracle.get("expected_disposition")
                != cell.get("expected_disposition")
                or blind.get("field_graph_fingerprint_sha256")
                != cell.get("field_graph_fingerprint_sha256")
                or blind.get("cycle_graph_fingerprint_sha256")
                != cell.get("cycle_graph_fingerprint_sha256")
            ):
                raise QualificationContractError("D4 support-aware leaf join differs")
            field_graph_id = _string(cell.get("field_graph_id"), label="field_graph_id")
            cycle_graph_id = _string(cell.get("cycle_graph_id"), label="cycle_graph_id")
            row: dict[str, object] = {
                **unit_fields,
                **_d4_string_fields(
                    cell,
                    (
                        "cell_id",
                        "field_graph_id",
                        "cycle_graph_id",
                        "loop_role",
                        "attempt_status",
                        "expected_disposition",
                        "prediction_class",
                        "state",
                        "field_graph_fingerprint_sha256",
                        "cycle_graph_fingerprint_sha256",
                        "field_estimate_fingerprint_sha256",
                        "representative_content_sha256",
                        "prediction_fingerprint_sha256",
                        "oracle_fingerprint_sha256",
                    ),
                ),
                "stratum_ids": stratum_ids,
                "pair_class": _d4_pair_class(field_graph_id, cycle_graph_id),
                "continuous_signed_total_cycles": _d4_optional_number(
                    cell.get("continuous_signed_total_cycles"),
                    label="continuous signed total",
                ),
                "oracle_absolute_error_cycles": _d4_optional_number(
                    cell.get("oracle_absolute_error_cycles"),
                    label="oracle absolute error",
                ),
                "sealed_prediction_reason_codes": _d4_string_list(
                    prediction.get("reason_codes"),
                    label="sealed prediction reason",
                ),
                "oracle_expected_prerequisite_reasons": _d4_string_list(
                    oracle.get("expected_prerequisite_reasons"),
                    label="oracle prerequisite reason",
                ),
                "numeric_support_available": False,
            }
            for output_key, receipt_key in (
                ("boundary_amplitude_descriptor", "boundary_amplitude"),
                ("boundary_coherence_descriptor", "boundary_coherence"),
                (
                    "boundary_identifiability_descriptor",
                    "boundary_identifiability_score",
                ),
            ):
                row[output_key] = _d4_descriptor(
                    blind.get(receipt_key), label=receipt_key.replace("_", " ")
                )
            support_rows.append(row)
    if len(support_rows) != 1_152:
        raise QualificationContractError(
            "D4 support table must retain all 1,152 leaf members"
        )

    return [
        _output(
            "three-by-three-field-cycle-graph-matrix",
            {
                "rows": matrix_rows,
                "evaluation_unit": "d4-d5-loop-execution-unit",
                "scientific_execution_count": len(units),
                "execution_role_row_count": len(matrix_rows),
                "matrix_shape": [3, 3],
                "cells_per_role_per_execution": 9,
                "graph_cells_are_repeated_measures": True,
                "graph_cells_are_independent_samples": False,
            },
        ),
        _output(
            "loop-role-separated-primary-boundary-and-offcore-control-table",
            {
                "rows": role_rows,
                "evaluation_unit": "d4-d5-loop-execution-unit",
                "scientific_execution_count": len(units),
                "cells_per_role_per_execution": 9,
                "role_counts": dict(Counter(row["loop_role"] for row in role_rows)),
                "loop_roles_collapsed": False,
                "graph_cells_are_repeated_measures": True,
                "loop_roles_are_independent_samples": False,
            },
        ),
        _output(
            "diagonal-offdiagonal-separation",
            {
                "rows": diagonal_rows,
                "classification_basis": "exact-declared-graph-family-equality",
                "classified_cell_count": sum(
                    int(row["cell_count"]) for row in diagonal_rows
                ),
                "diagonal_selected_as_winner": False,
                "descriptive_only": True,
                "graph_cells_are_independent_samples": False,
            },
        ),
        _output(
            "adjacency-output-loop-total-effects",
            {
                "rows": adjacency_rows,
                "scientific_execution_count": len(units),
                "field_pair_row_count": len(adjacency_rows),
                "component_row_count": component_row_count,
                "loop_contrast_row_count": loop_contrast_row_count,
                "nonvacuity_receipt_count": len(nonvacuity_evidence),
                "maximum_component_rms_distance": max(component_rms_values),
                "maximum_loop_contrast_absolute_difference_cycles": max(
                    loop_contrast_values
                ),
                "numeric_adjacency_difference_available": False,
                "field_output_and_loop_total_kept_distinct": True,
                "field_pairs_and_loop_contrasts_are_repeated_measures": True,
                "derived_rows_are_independent_samples": False,
            },
        ),
        _output(
            "support-aware-cell-table",
            {
                "rows": support_rows,
                "scientific_execution_count": len(units),
                "leaf_member_count": len(support_rows),
                "evaluable_cell_count": sum(
                    row["attempt_status"] == "evaluable" for row in support_rows
                ),
                "prerequisite_cell_count": sum(
                    row["attempt_status"] == "insufficient" for row in support_rows
                ),
                "numeric_support_available": False,
                "insufficient_is_not_fail": True,
                "support_bookkeeping_is_not_substantive_output": True,
                "leaf_members_are_repeated_measures": True,
                "leaf_members_are_independent_samples": False,
            },
        ),
    ]
