"""Private D1 descriptive work package for the D7 v1 successor."""

from __future__ import annotations

from collections.abc import Mapping

from .common import QualificationContractError
from . import confirmation_v1_records as records
from .confirmation_v1_descriptive_common import (
    _boolean,
    _mapping,
    _number,
    _output,
    _sequence,
    _string,
)

__all__: tuple[str, ...] = ()


def _numeric_metric_rows(result: Mapping[str, object]) -> list[dict[str, object]]:
    expected = {
        "cartesian-fourier-family-verified": (
            (
                "cartesian-fourier-fixed-null",
                "cartesian-fourier-no-core-null",
                "cartesian-fourier-positive",
                "cartesian-fourier-prerequisite-failure",
            ),
            (
                "amplitude-max-absolute-error",
                "direction-minimum-cosine",
                "second-harmonic-max-absolute-error",
                "split-max-disagreement",
                "support-mismatch-count",
            ),
        ),
        "representation-family-verified": (
            ("angular-section-positive", "fixed-direction-null"),
            (
                "amplitude-max-absolute-error",
                "phase-law-coherence",
                "support-mismatch-count",
            ),
        ),
    }
    graph_families = ("mutual-knn", "fixed-radius", "shared-neighbor")
    bundle = _mapping(result.get("evidence_bundle"), label="evidence bundle")
    rows: list[dict[str, object]] = []
    observed_family_ids = []
    for family_item in _sequence(
        bundle.get("static_runtime_receipts"), label="static runtime receipts"
    ):
        family = _mapping(family_item, label="static runtime receipt")
        if "cases" not in family:
            continue
        family_evidence_id = _string(
            family.get("evidence_id"), label="D1 family evidence_id"
        )
        if family_evidence_id not in expected:
            raise QualificationContractError("D1 numeric family is not closed")
        observed_family_ids.append(family_evidence_id)
        case_ids, metric_ids = expected[family_evidence_id]
        observed_coordinates = []
        for case_item in _sequence(family.get("cases"), label="D1 cases"):
            case = _mapping(case_item, label="D1 case")
            case_id = _string(case.get("case_id"), label="D1 case_id")
            for metric_item in _sequence(
                case.get("numeric_metric_receipts"), label="D1 numeric metrics"
            ):
                metric = _mapping(metric_item, label="D1 numeric metric")
                graph_family = _string(
                    metric.get("graph_family"), label="D1 graph_family"
                )
                metric_id = _string(metric.get("metric_id"), label="D1 metric_id")
                observed_coordinates.append((case_id, graph_family, metric_id))
                comparator = _string(metric.get("comparator"), label="D1 comparator")
                observed = _number(
                    metric.get("observed_value"), label="D1 observed_value"
                )
                threshold = _number(metric.get("threshold"), label="D1 threshold")
                if comparator == "at-most":
                    margin = threshold - observed
                elif comparator == "at-least":
                    margin = observed - threshold
                elif comparator == "exact-zero":
                    difference = abs(observed - threshold)
                    margin = 0.0 if difference == 0.0 else -difference
                else:
                    raise QualificationContractError("D1 comparator is not closed")
                passed = _boolean(metric.get("passed"), label="D1 metric passed")
                if passed is not (margin >= 0.0):
                    raise QualificationContractError(
                        "D1 persisted pass flag differs from its signed margin"
                    )
                rows.append(
                    {
                        "family_evidence_id": family_evidence_id,
                        "case_id": case_id,
                        "graph_family": graph_family,
                        "metric_id": metric_id,
                        "comparator": comparator,
                        "observed_value": observed,
                        "threshold": threshold,
                        "signed_margin": margin,
                        "passed": passed,
                        "field_graph_fingerprint_sha256": _string(
                            metric.get("field_graph_fingerprint_sha256"),
                            label="D1 field graph fingerprint",
                        ),
                        "estimator_output_sha256": _string(
                            metric.get("estimator_output_sha256"),
                            label="D1 estimator output fingerprint",
                        ),
                        "oracle_fingerprint_sha256": _string(
                            metric.get("oracle_fingerprint_sha256"),
                            label="D1 oracle fingerprint",
                        ),
                    }
                )
        expected_coordinates = tuple(
            (case_id, graph_family, metric_id)
            for case_id in case_ids
            for graph_family in graph_families
            for metric_id in metric_ids
        )
        if tuple(observed_coordinates) != expected_coordinates:
            raise QualificationContractError(
                "D1 persisted analytic-check order or universe differs"
            )
    if tuple(observed_family_ids) != tuple(expected) or len(rows) != 78:
        raise QualificationContractError(
            "D1 numeric family coverage differs from 60 plus 18 checks"
        )
    return rows


def _d1_outputs(result: Mapping[str, object]) -> list[records.D7V1DescriptiveOutput]:
    rows = _numeric_metric_rows(result)
    family_ids = (
        "cartesian-fourier-family-verified",
        "representation-family-verified",
    )
    grouped = {
        family_evidence_id: [
            row for row in rows if row["family_evidence_id"] == family_evidence_id
        ]
        for family_evidence_id in family_ids
    }
    family_row_counts = {
        family_evidence_id: len(grouped[family_evidence_id])
        for family_evidence_id in family_ids
    }
    if family_row_counts != {
        "cartesian-fourier-family-verified": 60,
        "representation-family-verified": 18,
    }:
        raise QualificationContractError("D1 family analytic-check counts differ")

    fragility_rows = []
    for family_evidence_id in family_ids:
        members = grouped[family_evidence_id]
        margins = [float(member["signed_margin"]) for member in members]
        positive = [
            member for member in members if float(member["signed_margin"]) > 0.0
        ]
        if not positive:
            raise QualificationContractError(
                "D1 family has no strictly positive signed margin"
            )
        minimum_positive = min(float(member["signed_margin"]) for member in positive)
        fragility_rows.append(
            {
                "family_evidence_id": family_evidence_id,
                "analytic_check_count": len(members),
                "zero_margin_count": sum(value == 0.0 for value in margins),
                "negative_margin_count": sum(value < 0.0 for value in margins),
                "minimum_signed_margin": min(margins),
                "minimum_strictly_positive_margin": minimum_positive,
                "closest_positive_check_keys": [
                    {
                        "case_id": member["case_id"],
                        "graph_family": member["graph_family"],
                        "metric_id": member["metric_id"],
                    }
                    for member in positive
                    if member["signed_margin"] == minimum_positive
                ],
                "all_persisted_checks_passed": all(
                    member["passed"] is True for member in members
                ),
                "threshold_change_authorized": False,
            }
        )
    if [row["zero_margin_count"] for row in fragility_rows] != [12, 6] or [
        row["negative_margin_count"] for row in fragility_rows
    ] != [0, 0]:
        raise QualificationContractError(
            "D1 exact-zero or negative-margin counts differ"
        )
    global_minimum = min(float(row["signed_margin"]) for row in rows)
    global_minimum_positive = min(
        float(row["minimum_strictly_positive_margin"]) for row in fragility_rows
    )
    if global_minimum != 0.0 or global_minimum_positive != 9.999877875467292e-11:
        raise QualificationContractError("D1 global fragility extrema differ")

    return [
        _output(
            "signed-margin-by-analytic-check",
            {
                "rows": rows,
                "family_row_counts": family_row_counts,
                "row_count": len(rows),
                "thresholds_modified": False,
                "descriptive_only": True,
            },
        ),
        _output(
            "fragility-without-threshold-change",
            {
                "rows": fragility_rows,
                "evaluation_unit": "d1-matched-class-unit",
                "matched_class_unit_count": len(fragility_rows),
                "thresholds_modified": False,
                "gate_reclassified": False,
                "minimum_observed_signed_margin": global_minimum,
                "minimum_strictly_positive_margin": global_minimum_positive,
                "exact_zero_margins_kept_distinct_from_positive_fragility": True,
            },
        ),
    ]
