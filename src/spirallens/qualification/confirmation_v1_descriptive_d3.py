"""Private D3 descriptive work package for the D7 v1 successor."""

from __future__ import annotations

from collections.abc import Mapping

from .common import QualificationContractError
from . import confirmation_v1_records as records
from .confirmation_v1_descriptive_common import (
    _CARTESIAN_D3_LAWS,
    _REPRESENTATION_D3_CYCLE_GRAPH_IDS,
    _REPRESENTATION_D3_FIELD_GRAPH_IDS,
    _REPRESENTATION_D3_LOOP_LAWS,
    _boolean,
    _integer,
    _mapping,
    _number,
    _output,
    _sequence,
    _string,
)

__all__: tuple[str, ...] = ()


def _metamorphic_rows(result: Mapping[str, object]) -> list[dict[str, object]]:
    bundle = _mapping(result.get("evidence_bundle"), label="evidence bundle")
    rows: list[dict[str, object]] = []
    for item in _sequence(
        bundle.get("static_runtime_receipts"), label="static runtime receipts"
    ):
        family = _mapping(item, label="static runtime receipt")
        if "obligation_receipts" not in family:
            continue
        evidence_id = _string(family.get("evidence_id"), label="evidence_id")
        for obligation_item in _sequence(
            family.get("obligation_receipts"), label="obligation receipts"
        ):
            obligation = _mapping(obligation_item, label="obligation receipt")
            receipt = _mapping(obligation.get("receipt"), label="metamorphic receipt")
            component_errors = {
                field: (
                    _number(receipt[field], label=field)
                    if receipt.get(field) is not None
                    else None
                )
                for field in (
                    "maximum_distance_error",
                    "maximum_field_law_error",
                    "maximum_loop_law_error",
                )
            }
            if receipt.get("observed_error") is not None:
                observed_error = _number(
                    receipt["observed_error"], label="metamorphic observed_error"
                )
            else:
                present_errors = [
                    value for value in component_errors.values() if value is not None
                ]
                if not present_errors:
                    raise QualificationContractError(
                        "metamorphic receipt has no numeric error"
                    )
                observed_error = max(present_errors)
            rows.append(
                {
                    "evidence_id": evidence_id,
                    "obligation_id": obligation["obligation_id"],
                    "law": receipt["law"],
                    "state": receipt["state"],
                    "observed_error": observed_error,
                    **component_errors,
                    "tolerance": _number(
                        receipt["tolerance"], label="metamorphic tolerance"
                    ),
                    "composition_verified": receipt["composition_verified"],
                    "inverse_verified": receipt["inverse_verified"],
                    "nonidentity_verified": receipt["nonidentity_verified"],
                    "integer_output_present": receipt["integer_output_present"],
                    "topology_claimed": receipt["topology_claimed"],
                }
            )
    rows.sort(key=lambda row: (str(row["evidence_id"]), str(row["obligation_id"])))
    if not rows:
        raise QualificationContractError("D3 metamorphic receipts are absent")
    return rows


def _d3_family_aggregates(
    result: Mapping[str, object],
) -> tuple[
    list[dict[str, object]],
    dict[str, object],
    list[dict[str, object]],
    list[dict[str, object]],
    dict[str, object],
]:
    bundle = _mapping(result.get("evidence_bundle"), label="evidence bundle")
    wanted = {
        "cartesian-gauge-pipeline-rerun-verified",
        "representation-gauge-pipeline-rerun-verified",
    }
    families: dict[str, dict[str, object]] = {}
    for item in _sequence(
        bundle.get("static_runtime_receipts"), label="static runtime receipts"
    ):
        family = _mapping(item, label="static runtime receipt")
        evidence_id = _string(family.get("evidence_id"), label="evidence_id")
        if evidence_id not in wanted:
            continue
        if evidence_id in families:
            raise QualificationContractError("D3 family receipt is duplicated")
        families[evidence_id] = family
    if set(families) != wanted:
        raise QualificationContractError("D3 aggregate family receipts are incomplete")

    cartesian = _mapping(
        families["cartesian-gauge-pipeline-rerun-verified"].get(
            "aggregate_runtime_receipt"
        ),
        label="Cartesian D3 aggregate",
    )
    cartesian_checks = [
        _mapping(item, label="Cartesian D3 pipeline check")
        for item in _sequence(cartesian.get("checks"), label="Cartesian D3 checks")
    ]
    if (
        tuple(
            _string(item.get("law"), label="Cartesian D3 law")
            for item in cartesian_checks
        )
        != _CARTESIAN_D3_LAWS
    ):
        raise QualificationContractError(
            "Cartesian D3 checks differ from the exact four-law sequence"
        )
    for item, expected_sign in zip(cartesian_checks, (1, 1, -1, -1), strict=True):
        tolerance = _number(item.get("tolerance"), label="Cartesian D3 tolerance")
        errors = (
            _number(item.get(field), label=f"Cartesian D3 {field}")
            for field in (
                "maximum_distance_error",
                "maximum_field_law_error",
                "maximum_loop_law_error",
            )
        )
        if (
            item.get("state") != "pass"
            or item.get("pipeline_rerun_verified") is not True
            or item.get("claim_relevant_field_law_verified") is not True
            or item.get("continuous_loop_law_verified") is not True
            or item.get("sampled_continuous_observable_only") is not True
            or item.get("integer_output_present") is not False
            or item.get("topology_claimed") is not False
            or item.get("expected_loop_orientation_sign") != expected_sign
            or tolerance <= 0.0
            or any(error < 0.0 or error > tolerance for error in errors)
        ):
            raise QualificationContractError(
                "Cartesian D3 pipeline check boundary differs"
            )

    representation = _mapping(
        families["representation-gauge-pipeline-rerun-verified"].get(
            "aggregate_runtime_receipt"
        ),
        label="representation D3 aggregate",
    )
    if (
        representation.get("schema_version")
        != "spirallens.representation-pipeline-metamorphic-receipt.v0.3"
        or representation.get("verified") is not True
        or representation.get("pipeline_rerun_verified") is not True
        or representation.get("signed_loop_law_verified") is not True
        or representation.get("selection_seed_accessed") is not False
        or representation.get("integer_output_present") is not False
        or representation.get("topology_claimed") is not False
    ):
        raise QualificationContractError("representation D3 aggregate boundary differs")
    tolerance = _number(
        representation.get("tolerance"), label="representation D3 tolerance"
    )
    if tolerance <= 0.0:
        raise QualificationContractError("representation D3 tolerance is not positive")

    algebraic_checks = [
        _mapping(item, label="representation D3 algebraic check")
        for item in _sequence(
            representation.get("all_algebraic_checks"),
            label="representation D3 algebraic checks",
        )
    ]
    ambient_algebraic = [
        item
        for item in algebraic_checks
        if item.get("law") == "ambient_signed_permutation"
    ]
    if len(algebraic_checks) != 7 or len(ambient_algebraic) != 1:
        raise QualificationContractError(
            "representation D3 algebraic surface differs from the closed set"
        )
    if (
        ambient_algebraic[0].get("state") != "pass"
        or ambient_algebraic[0].get("composition_verified") is not True
        or ambient_algebraic[0].get("inverse_verified") is not True
        or ambient_algebraic[0].get("nonidentity_verified") is not True
    ):
        raise QualificationContractError(
            "representation ambient algebraic check is not verified"
        )

    pipeline_checks = [
        _mapping(item, label="representation D3 pipeline check")
        for item in _sequence(
            representation.get("pipeline_checks"),
            label="representation D3 pipeline checks",
        )
    ]
    if (
        tuple(
            _string(item.get("field_graph_id"), label="D3 field_graph_id")
            for item in pipeline_checks
        )
        != _REPRESENTATION_D3_FIELD_GRAPH_IDS
    ):
        raise QualificationContractError(
            "representation D3 pipeline checks differ from the three A graphs"
        )
    for item in pipeline_checks:
        field_graph_id = _string(item.get("field_graph_id"), label="D3 field_graph_id")
        errors = _mapping(item.get("errors"), label="D3 pipeline errors")
        if set(errors) != {
            "alignment_determinant_unit",
            "alignment_orthogonality",
            "ambient_equivariance",
            "amplitude",
            "coherence",
            "identifiability",
            "section_gauge_alignment",
        }:
            raise QualificationContractError(
                "representation D3 pipeline error fields differ"
            )
        for field, value in errors.items():
            error = _number(value, label=f"D3 pipeline error {field}")
            if error < 0.0 or error > tolerance:
                raise QualificationContractError(
                    "representation D3 pipeline error exceeds its tolerance"
                )
        crossed = [
            _mapping(value, label="representation D3 crossed loop")
            for value in _sequence(
                item.get("crossed_loop_checks"), label="D3 crossed loop checks"
            )
        ]
        if tuple(
            _string(value.get("cycle_graph_id"), label="D3 cycle_graph_id")
            for value in crossed
        ) != _REPRESENTATION_D3_CYCLE_GRAPH_IDS or any(
            value.get("field_graph_id") != field_graph_id
            or value.get("law") != "ambient_o2_alignment"
            or value.get("verified") is not True
            for value in crossed
        ):
            raise QualificationContractError(
                "representation D3 crossed-loop surface differs"
            )
        if (
            item.get("verified") is not True
            or item.get("alignment_determinant") != -1.0
            or item.get("adjacency_equal") is not True
            or item.get("edge_distances_bit_identical") is not True
            or item.get("support_equal") is not True
            or any(
                _number(
                    value.get("signed_total_error_cycles"),
                    label="D3 crossed-loop signed-total error",
                )
                > tolerance
                for value in crossed
            )
        ):
            raise QualificationContractError(
                "representation D3 pipeline verification differs"
            )

    loop_variants = [
        _mapping(item, label="representation D3 loop variant")
        for item in _sequence(
            representation.get("loop_variant_checks"),
            label="representation D3 loop variants",
        )
    ]
    expected_variants = tuple(
        (field_graph_id, cycle_graph_id, law)
        for field_graph_id in _REPRESENTATION_D3_FIELD_GRAPH_IDS
        for cycle_graph_id in _REPRESENTATION_D3_CYCLE_GRAPH_IDS
        for law in _REPRESENTATION_D3_LOOP_LAWS
    )
    observed_variants = tuple(
        (
            _string(item.get("field_graph_id"), label="D3 variant field graph"),
            _string(item.get("cycle_graph_id"), label="D3 variant cycle graph"),
            _string(item.get("law"), label="D3 variant law"),
        )
        for item in loop_variants
    )
    expected_signs = {
        "reference_rotation": 1.0,
        "reference_reflection": -1.0,
        "loop_reversal": -1.0,
    }
    if observed_variants != expected_variants or any(
        item.get("verified") is not True
        or item.get("oracle_read") is not False
        or item.get("selection_seed_accessed") is not False
        or item.get("sampled_continuous_observable_only") is not True
        or item.get("integer_output_present") is not False
        or item.get("topology_claimed") is not False
        or item.get("orientation_determinant") != expected_signs[item["law"]]
        or not (
            0.0
            <= _number(
                item.get("signed_total_error_cycles"),
                label="D3 variant signed-total error",
            )
            <= tolerance
        )
        for item in loop_variants
    ):
        raise QualificationContractError(
            "representation D3 loop variants differ from the closed A by B laws"
        )
    return (
        cartesian_checks,
        ambient_algebraic[0],
        pipeline_checks,
        loop_variants,
        representation,
    )


def _cartesian_d3_row(check: Mapping[str, object]) -> dict[str, object]:
    law = _string(check.get("law"), label="Cartesian D3 law")
    return {
        "row_id": law.replace("_", "-"),
        "family_evidence_id": "cartesian-gauge-pipeline-rerun-verified",
        "law": law,
        "source_check_count": 1,
        "structural_checks": {
            "all_graph_adjacencies_verified": _boolean(
                check.get("all_graph_adjacencies_verified"),
                label="Cartesian D3 adjacency verification",
            ),
            "all_graph_edge_distances_bit_identical": _boolean(
                check.get("all_graph_edge_distances_bit_identical"),
                label="Cartesian D3 edge-distance verification",
            ),
            "maximum_distance_error": _number(
                check.get("maximum_distance_error"),
                label="Cartesian D3 distance error",
            ),
        },
        "alignment_errors": {},
        "observable_law_errors": {
            "maximum_field_law_error": _number(
                check.get("maximum_field_law_error"),
                label="Cartesian D3 field-law error",
            ),
            "maximum_loop_law_error": _number(
                check.get("maximum_loop_law_error"),
                label="Cartesian D3 loop-law error",
            ),
        },
        "determinant_or_sign": _integer(
            check.get("expected_loop_orientation_sign"),
            label="Cartesian D3 orientation sign",
        ),
        "tolerance": _number(check.get("tolerance"), label="Cartesian D3 tolerance"),
        "state": check["state"],
        "verified": True,
    }


def _representation_d3_row(
    check: Mapping[str, object],
    *,
    tolerance: float,
) -> dict[str, object]:
    errors = _mapping(check.get("errors"), label="D3 pipeline errors")
    crossed = [
        _mapping(item, label="D3 crossed-loop check")
        for item in _sequence(
            check.get("crossed_loop_checks"), label="D3 crossed-loop checks"
        )
    ]
    return {
        "row_id": check["field_graph_id"],
        "family_evidence_id": "representation-gauge-pipeline-rerun-verified",
        "law": "ambient_o2_alignment",
        "source_check_count": len(crossed),
        "cycle_graph_ids": [item["cycle_graph_id"] for item in crossed],
        "structural_checks": {
            "adjacency_equal": check["adjacency_equal"],
            "edge_distances_bit_identical": check["edge_distances_bit_identical"],
            "support_equal": check["support_equal"],
        },
        "alignment_errors": {
            "alignment_determinant_unit": _number(
                errors.get("alignment_determinant_unit"),
                label="D3 alignment determinant error",
            ),
            "alignment_orthogonality": _number(
                errors.get("alignment_orthogonality"),
                label="D3 alignment orthogonality error",
            ),
        },
        "observable_law_errors": {
            "ambient_equivariance": _number(
                errors.get("ambient_equivariance"),
                label="D3 ambient equivariance error",
            ),
            "amplitude": _number(errors.get("amplitude"), label="D3 amplitude error"),
            "coherence": _number(errors.get("coherence"), label="D3 coherence error"),
            "identifiability": _number(
                errors.get("identifiability"), label="D3 identifiability error"
            ),
            "section_gauge_alignment": _number(
                errors.get("section_gauge_alignment"),
                label="D3 section-gauge error",
            ),
            "maximum_crossed_loop_signed_total_error_cycles": max(
                _number(
                    item.get("signed_total_error_cycles"),
                    label="D3 crossed-loop signed-total error",
                )
                for item in crossed
            ),
        },
        "determinant_or_sign": _number(
            check.get("alignment_determinant"),
            label="D3 alignment determinant",
        ),
        "tolerance": tolerance,
        "state": "pass",
        "verified": True,
    }


def _d3_outputs(
    result: Mapping[str, object],
) -> list[records.D7V1DescriptiveOutput]:
    (
        cartesian_checks,
        representation_ambient,
        representation_pipelines,
        representation_variants,
        representation_aggregate,
    ) = _d3_family_aggregates(result)
    cartesian_by_law = {str(item["law"]): item for item in cartesian_checks}
    representation_tolerance = _number(
        representation_aggregate.get("tolerance"),
        label="representation D3 tolerance",
    )

    cartesian_ambient = cartesian_by_law["ambient_signed_permutation"]
    pipeline_ambient_maximum = max(
        _number(
            _mapping(item.get("errors"), label="D3 pipeline errors").get(
                "ambient_equivariance"
            ),
            label="D3 ambient equivariance error",
        )
        for item in representation_pipelines
    )
    ambient_rows = [
        {
            "family_evidence_id": "cartesian-gauge-pipeline-rerun-verified",
            "law": "ambient_signed_permutation",
            "source_check_count": 1,
            "maximum_distance_error": _number(
                cartesian_ambient.get("maximum_distance_error"),
                label="Cartesian ambient distance error",
            ),
            "maximum_field_law_error": _number(
                cartesian_ambient.get("maximum_field_law_error"),
                label="Cartesian ambient field error",
            ),
            "maximum_loop_law_error": _number(
                cartesian_ambient.get("maximum_loop_law_error"),
                label="Cartesian ambient loop error",
            ),
            "observed_error": None,
            "pipeline_ambient_equivariance_max": None,
            "tolerance": _number(
                cartesian_ambient.get("tolerance"),
                label="Cartesian ambient tolerance",
            ),
            "state": "pass",
            "verified": True,
        },
        {
            "family_evidence_id": "representation-gauge-pipeline-rerun-verified",
            "law": "ambient_signed_permutation",
            "source_check_count": 1 + len(representation_pipelines),
            "maximum_distance_error": None,
            "maximum_field_law_error": None,
            "maximum_loop_law_error": None,
            "observed_error": _number(
                representation_ambient.get("observed_error"),
                label="representation ambient algebraic error",
            ),
            "pipeline_ambient_equivariance_max": pipeline_ambient_maximum,
            "tolerance": representation_tolerance,
            "state": "pass",
            "verified": True,
        },
    ]

    reference_rows: list[dict[str, object]] = []
    for law, sign in (("reference_rotation", 1), ("reference_reflection", -1)):
        cartesian = cartesian_by_law[law]
        reference_rows.append(
            {
                "family_evidence_id": "cartesian-gauge-pipeline-rerun-verified",
                "law": law,
                "source_check_count": 1,
                "expected_orientation_sign": sign,
                "maximum_field_law_error": _number(
                    cartesian.get("maximum_field_law_error"),
                    label="Cartesian reference field error",
                ),
                "maximum_loop_or_signed_total_error": _number(
                    cartesian.get("maximum_loop_law_error"),
                    label="Cartesian reference loop error",
                ),
                "tolerance": _number(
                    cartesian.get("tolerance"),
                    label="Cartesian reference tolerance",
                ),
                "all_verified": True,
            }
        )
    for law, sign in (("reference_rotation", 1), ("reference_reflection", -1)):
        variants = [item for item in representation_variants if item["law"] == law]
        reference_rows.append(
            {
                "family_evidence_id": "representation-gauge-pipeline-rerun-verified",
                "law": law,
                "source_check_count": len(variants),
                "field_cycle_pairs": [
                    [item["field_graph_id"], item["cycle_graph_id"]]
                    for item in variants
                ],
                "expected_orientation_sign": sign,
                "maximum_field_law_error": None,
                "maximum_loop_or_signed_total_error": max(
                    _number(
                        item.get("signed_total_error_cycles"),
                        label="representation reference signed-total error",
                    )
                    for item in variants
                ),
                "tolerance": representation_tolerance,
                "all_verified": True,
            }
        )

    cartesian_reversal = cartesian_by_law["loop_reversal"]
    representation_reversal = [
        item for item in representation_variants if item["law"] == "loop_reversal"
    ]
    reversal_rows = [
        {
            "family_evidence_id": "cartesian-gauge-pipeline-rerun-verified",
            "law": "loop_reversal",
            "source_check_count": 1,
            "expected_orientation_sign": -1,
            "maximum_field_law_error": _number(
                cartesian_reversal.get("maximum_field_law_error"),
                label="Cartesian reversal field error",
            ),
            "maximum_loop_or_signed_total_error": _number(
                cartesian_reversal.get("maximum_loop_law_error"),
                label="Cartesian reversal loop error",
            ),
            "tolerance": _number(
                cartesian_reversal.get("tolerance"),
                label="Cartesian reversal tolerance",
            ),
            "all_verified": True,
        },
        {
            "family_evidence_id": "representation-gauge-pipeline-rerun-verified",
            "law": "loop_reversal",
            "source_check_count": len(representation_reversal),
            "field_cycle_pairs": [
                [item["field_graph_id"], item["cycle_graph_id"]]
                for item in representation_reversal
            ],
            "expected_orientation_sign": -1,
            "maximum_field_law_error": None,
            "maximum_loop_or_signed_total_error": max(
                _number(
                    item.get("signed_total_error_cycles"),
                    label="representation reversal signed-total error",
                )
                for item in representation_reversal
            ),
            "tolerance": representation_tolerance,
            "all_verified": True,
        },
    ]

    separated_rows = [_cartesian_d3_row(item) for item in cartesian_checks] + [
        _representation_d3_row(item, tolerance=representation_tolerance)
        for item in representation_pipelines
    ]
    cartesian_separated = [
        row
        for row in separated_rows
        if row["family_evidence_id"] == "cartesian-gauge-pipeline-rerun-verified"
    ]
    representation_separated = [
        row
        for row in separated_rows
        if row["family_evidence_id"] == "representation-gauge-pipeline-rerun-verified"
    ]
    cartesian_array_or_field_maximum = max(
        max(
            float(row["structural_checks"]["maximum_distance_error"]),
            float(row["observable_law_errors"]["maximum_field_law_error"]),
        )
        for row in cartesian_separated
    )
    representation_array_or_field_maximum = max(
        max(
            [float(value) for value in row["alignment_errors"].values()]
            + [
                float(value)
                for key, value in row["observable_law_errors"].items()
                if key != "maximum_crossed_loop_signed_total_error_cycles"
            ]
        )
        for row in representation_separated
    )
    return [
        _output(
            "ambient-basis-error",
            {
                "rows": ambient_rows,
                "evaluation_unit": "d3-matched-class-unit",
                "matched_class_unit_count": 2,
                "family_row_count": len(ambient_rows),
                "maximum_pipeline_ambient_equivariance_error": (
                    pipeline_ambient_maximum
                ),
                "algebraic_and_pipeline_errors_kept_distinct": True,
                "diagnostic_rows_are_independent_scientific_observations": False,
                "integer_output_present": False,
                "topology_claimed": False,
            },
        ),
        _output(
            "reference-o2-error",
            {
                "rows": reference_rows,
                "evaluation_unit": "d3-matched-class-unit",
                "matched_class_unit_count": 2,
                "law_groups": ["reference_rotation", "reference_reflection"],
                "maximum_observed_field_error": max(
                    float(row["maximum_field_law_error"])
                    for row in reference_rows
                    if row["maximum_field_law_error"] is not None
                ),
                "maximum_observed_loop_or_signed_total_error": max(
                    float(row["maximum_loop_or_signed_total_error"])
                    for row in reference_rows
                ),
                "orientation_preserving_and_reversing_laws_kept_distinct": True,
                "diagnostic_rows_are_independent_scientific_observations": False,
                "integer_output_present": False,
                "topology_claimed": False,
            },
        ),
        _output(
            "loop-reversal-signed-total-error",
            {
                "rows": reversal_rows,
                "evaluation_unit": "d3-matched-class-unit",
                "matched_class_unit_count": 2,
                "maximum_observed_error_cycles": max(
                    float(row["maximum_loop_or_signed_total_error"])
                    for row in reversal_rows
                ),
                "integer_output_used": False,
                "continuous_sampled_total_only": True,
                "diagnostic_rows_are_independent_scientific_observations": False,
                "integer_output_present": False,
                "topology_claimed": False,
            },
        ),
        _output(
            "array-versus-observable-law-separation",
            {
                "rows": separated_rows,
                "evaluation_unit": "d3-matched-class-unit",
                "matched_class_unit_count": 2,
                "cartesian_pipeline_row_count": len(cartesian_checks),
                "representation_pipeline_row_count": len(representation_pipelines),
                "representation_crossed_loop_cell_count": sum(
                    int(row["source_check_count"])
                    for row in separated_rows
                    if row["family_evidence_id"]
                    == "representation-gauge-pipeline-rerun-verified"
                ),
                "family_maximum_errors": {
                    "cartesian_array_or_field": cartesian_array_or_field_maximum,
                    "cartesian_sampled_loop": max(
                        float(row["observable_law_errors"]["maximum_loop_law_error"])
                        for row in cartesian_separated
                    ),
                    "representation_array_or_field": (
                        representation_array_or_field_maximum
                    ),
                    "representation_sampled_loop": max(
                        float(
                            row["observable_law_errors"][
                                "maximum_crossed_loop_signed_total_error_cycles"
                            ]
                        )
                        for row in representation_separated
                    ),
                },
                "array_field_and_sampled_loop_surfaces_collapsed": False,
                "diagnostic_rows_are_independent_scientific_observations": False,
                "integer_output_present": False,
                "topology_claimed": False,
            },
        ),
    ]
