"""Private D2 descriptive work package for the D7 v1 successor."""

from __future__ import annotations

from collections import Counter
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


_CORE_DECLARED_OUTCOME_FIELDS = (
    "attempt_status",
    "expected_disposition",
    "prediction_class",
    "reason_codes",
    "state",
)
_CORE_BLIND_DESCRIPTOR_FIELDS = (
    "amplitude",
    "identifiability_score",
    "support_counts",
)
_CORE_BOUNDARY_IDENTITY_FIELDS = (
    "blind_input_fingerprint_sha256",
    "field_estimate_fingerprint_sha256",
    "field_graph_fingerprint_sha256",
    "oracle_fingerprint_sha256",
    "prediction_fingerprint_sha256",
)


def _collapse_core_boundary_repeats(
    primary_units: Sequence[Mapping[str, object]],
    core_cells: Sequence[Mapping[str, object]],
    core_receipts: Sequence[Mapping[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    cells_by_id = {
        _string(item.get("core_cell_id"), label="core_cell_id"): item
        for item in core_cells
    }
    receipts_by_id = {
        _string(item.get("core_cell_id"), label="core receipt cell_id"): item
        for item in core_receipts
    }
    if (
        len(cells_by_id) != 192
        or len(receipts_by_id) != 192
        or set(cells_by_id) != set(receipts_by_id)
    ):
        raise QualificationContractError("D2 core cell evidence universe is not closed")

    repeat_groups: dict[tuple[int, str, str, str], dict[str, Mapping[str, object]]] = {}
    for unit in primary_units:
        assignments = {
            _string(item.get("axis_id"), label="stress axis id"): _string(
                item.get("level"), label="stress level"
            )
            for item in (
                _mapping(value, label="stress assignment")
                for value in _sequence(
                    unit.get("stress_assignments"), label="stress assignments"
                )
            )
        }
        if set(assignments) != {
            "boundary",
            "state-geometry-warp",
            "structured-observation-perturbation",
        }:
            raise QualificationContractError("D2 stress assignments are not closed")
        key = (
            _integer(unit.get("selection_seed"), label="selection_seed"),
            _string(unit.get("control_id"), label="control_id"),
            assignments["state-geometry-warp"],
            assignments["structured-observation-perturbation"],
        )
        boundary_level = assignments["boundary"]
        group = repeat_groups.setdefault(key, {})
        if boundary_level in group:
            raise QualificationContractError("D2 boundary repeat is duplicated")
        group[boundary_level] = unit

    collapsed_units = []
    repeat_rows = []
    for key, boundaries in repeat_groups.items():
        if set(boundaries) != {"central", "wide"}:
            raise QualificationContractError(
                "D2 scientific input requires central and wide boundary repeats"
            )
        central = boundaries["central"]
        wide = boundaries["wide"]
        unit_equalities = {
            field: central.get(field) == wide.get(field)
            for field in (
                "d2_scientific_input_fingerprint_sha256",
                *_CORE_DECLARED_OUTCOME_FIELDS,
            )
        }
        central_ids = _sequence(
            central.get("core_cell_ids"), label="central core_cell_ids"
        )
        wide_ids = _sequence(wide.get("core_cell_ids"), label="wide core_cell_ids")
        if (
            not all(unit_equalities.values())
            or len(central_ids) != 3
            or len(wide_ids) != 3
        ):
            raise QualificationContractError(
                "D2 boundary repeats disagree at the scientific-input grain"
            )

        graph_rows = []
        for central_raw_id, wide_raw_id in zip(central_ids, wide_ids, strict=True):
            central_id = _string(central_raw_id, label="central core_cell_id")
            wide_id = _string(wide_raw_id, label="wide core_cell_id")
            central_cell = cells_by_id[central_id]
            wide_cell = cells_by_id[wide_id]
            field_graph_id = _string(
                central_cell.get("field_graph_id"), label="field_graph_id"
            )
            if wide_cell.get("field_graph_id") != field_graph_id:
                raise QualificationContractError("D2 boundary graph order differs")
            central_receipt = receipts_by_id[central_id]
            wide_receipt = receipts_by_id[wide_id]
            for cell, receipt in (
                (central_cell, central_receipt),
                (wide_cell, wide_receipt),
            ):
                if sha256_bytes(canonical_json_bytes(cell)) != receipt.get(
                    "normalized_summary_sha256"
                ):
                    raise QualificationContractError(
                        "D2 core summary evidence fingerprint differs"
                    )
            central_blind = _mapping(
                central_receipt.get("blind_input_receipt"),
                label="central blind core input",
            )
            wide_blind = _mapping(
                wide_receipt.get("blind_input_receipt"),
                label="wide blind core input",
            )
            descriptor_equalities = {
                f"{field}_descriptor_equal": (
                    central_blind.get(field) == wide_blind.get(field)
                )
                for field in _CORE_BLIND_DESCRIPTOR_FIELDS
            }
            identity_equalities = {
                f"{field}_equal": central_cell.get(field) == wide_cell.get(field)
                for field in _CORE_BOUNDARY_IDENTITY_FIELDS
            }
            cell_equalities = {
                field: central_cell.get(field) == wide_cell.get(field)
                for field in _CORE_DECLARED_OUTCOME_FIELDS
            }
            candidate_rows_equal = central_receipt.get(
                "candidate_rows"
            ) == wide_receipt.get("candidate_rows")
            candidate_fingerprint_equal = central_cell.get(
                "candidate_fingerprint_sha256"
            ) == wide_cell.get("candidate_fingerprint_sha256")
            declared_outcomes_equal = all(cell_equalities.values())
            if (
                not declared_outcomes_equal
                or not candidate_rows_equal
                or not candidate_fingerprint_equal
                or not all(descriptor_equalities.values())
                or any(identity_equalities.values())
            ):
                raise QualificationContractError(
                    "D2 boundary graph evidence differs outside the frozen scope"
                )
            graph_rows.append(
                {
                    "field_graph_id": field_graph_id,
                    "central_core_cell_id": central_id,
                    "wide_core_cell_id": wide_id,
                    "central_candidate_fingerprint_sha256": central_cell[
                        "candidate_fingerprint_sha256"
                    ],
                    "wide_candidate_fingerprint_sha256": wide_cell[
                        "candidate_fingerprint_sha256"
                    ],
                    "declared_outcomes_equal": declared_outcomes_equal,
                    "blind_array_descriptor_equalities": descriptor_equalities,
                    "boundary_specific_identity_equalities": identity_equalities,
                }
            )
            repeat_rows.append(
                {
                    "selection_seed": key[0],
                    "control_id": key[1],
                    "state_geometry_warp_level": key[2],
                    "structured_observation_perturbation_level": key[3],
                    "field_graph_id": field_graph_id,
                    "central_core_cell_id": central_id,
                    "wide_core_cell_id": wide_id,
                    "scientific_input_fingerprint_equal": unit_equalities[
                        "d2_scientific_input_fingerprint_sha256"
                    ],
                    "attempt_status_equal": cell_equalities["attempt_status"],
                    "expected_disposition_equal": cell_equalities[
                        "expected_disposition"
                    ],
                    "prediction_class_equal": cell_equalities["prediction_class"],
                    "candidate_rows_equal": candidate_rows_equal,
                    "candidate_fingerprint_equal": candidate_fingerprint_equal,
                    "reason_codes_equal": cell_equalities["reason_codes"],
                    "state_equal": cell_equalities["state"],
                    "declared_outcomes_equal": declared_outcomes_equal,
                    "blind_array_descriptor_equalities": descriptor_equalities,
                    "boundary_specific_identity_equalities": identity_equalities,
                }
            )
        collapsed_units.append(
            {
                "selection_seed": key[0],
                "control_id": key[1],
                "state_geometry_warp_level": key[2],
                "structured_observation_perturbation_level": key[3],
                "d2_scientific_input_fingerprint_sha256": central[
                    "d2_scientific_input_fingerprint_sha256"
                ],
                "expected_disposition": central["expected_disposition"],
                "attempt_status": central["attempt_status"],
                "prediction_class": central["prediction_class"],
                "state": central["state"],
                "reason_codes": list(
                    _sequence(central.get("reason_codes"), label="reason_codes")
                ),
                "boundary_primary_unit_ids": {
                    "central": _string(
                        central.get("primary_unit_id"), label="central primary_unit_id"
                    ),
                    "wide": _string(
                        wide.get("primary_unit_id"), label="wide primary_unit_id"
                    ),
                },
                "graph_rows": graph_rows,
            }
        )
    if len(collapsed_units) != 32 or len(repeat_rows) != 96:
        raise QualificationContractError("D2 exact boundary grain is not 32 by 3")
    return collapsed_units, repeat_rows


def _d2_confounder_observation_rows(
    bundle: Mapping[str, object],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    matrix = _mapping(
        bundle.get("d2_confounder_matrix_receipt"),
        label="D2 confounder matrix receipt",
    )
    rows = []
    for item in _sequence(matrix.get("cells"), label="D2 confounder cells"):
        cell = _mapping(item, label="D2 confounder cell")
        observation = _mapping(
            cell.get("construction_observation"),
            label="D2 confounder construction observation",
        )
        sealed = _mapping(
            cell.get("sealed_prediction_receipt"),
            label="D2 confounder sealed prediction",
        )
        rows.append(
            {
                "cell_id": _string(cell.get("cell_id"), label="confounder cell_id"),
                "confounder_id": _string(
                    cell.get("confounder_id"), label="confounder_id"
                ),
                "construction_id": _string(
                    cell.get("construction_id"), label="confounder construction_id"
                ),
                "field_graph_id": _string(
                    cell.get("field_graph_id"), label="confounder field_graph_id"
                ),
                "probe_row": _integer(
                    observation.get("probe_row"), label="confounder probe_row"
                ),
                "probe_row_role": _string(
                    observation.get("probe_row_role"),
                    label="confounder probe_row_role",
                ),
                "probe_amplitude": _number(
                    observation.get("probe_amplitude"),
                    label="confounder probe_amplitude",
                ),
                "core_amplitude_ceiling": _number(
                    observation.get("core_amplitude_ceiling"),
                    label="confounder core_amplitude_ceiling",
                ),
                "core_amplitude_threshold_satisfied": _boolean(
                    observation.get("core_amplitude_threshold_satisfied"),
                    label="confounder core amplitude threshold",
                ),
                "probe_identifiability_score": _number(
                    observation.get("probe_identifiability_score"),
                    label="confounder probe_identifiability_score",
                ),
                "identifiability_floor": _number(
                    observation.get("identifiability_floor"),
                    label="confounder identifiability_floor",
                ),
                "direction_loss_threshold_satisfied": _boolean(
                    observation.get("direction_loss_threshold_satisfied"),
                    label="confounder direction loss threshold",
                ),
                "probe_measurement_support": _integer(
                    observation.get("probe_measurement_support"),
                    label="confounder probe_measurement_support",
                ),
                "minimum_support_count": _integer(
                    observation.get("minimum_support_count"),
                    label="confounder minimum_support_count",
                ),
                "measurement_support_threshold_satisfied": _boolean(
                    observation.get("measurement_support_threshold_satisfied"),
                    label="confounder measurement support threshold",
                ),
                "oracle_input_present": _boolean(
                    observation.get("oracle_input_present"),
                    label="confounder oracle_input_present",
                ),
                "selection_seed_present": _boolean(
                    observation.get("selection_seed_present"),
                    label="confounder selection_seed_present",
                ),
                "expected_attempt_status": _string(
                    cell.get("expected_attempt_status"),
                    label="confounder expected_attempt_status",
                ),
                "expected_prediction_class": _string(
                    cell.get("expected_prediction_class"),
                    label="confounder expected_prediction_class",
                ),
                "expected_reason_codes": [
                    _string(reason, label="confounder expected reason")
                    for reason in _sequence(
                        cell.get("expected_reason_codes"),
                        label="confounder expected reason codes",
                    )
                ],
                "observed_attempt_status": _string(
                    sealed.get("observed_attempt_status"),
                    label="confounder observed_attempt_status",
                ),
                "observed_prediction_class": _string(
                    sealed.get("prediction_class"),
                    label="confounder observed prediction_class",
                ),
                "observed_reason_codes": [
                    _string(reason, label="confounder observed reason")
                    for reason in _sequence(
                        sealed.get("reason_codes"),
                        label="confounder observed reason codes",
                    )
                ],
                "blind_input_fingerprint_sha256": _string(
                    sealed.get("blind_input_fingerprint_sha256"),
                    label="confounder blind input fingerprint",
                ),
                "primary_unit_sha256": _string(
                    sealed.get("primary_unit_sha256"),
                    label="confounder primary unit fingerprint",
                ),
                "policy_fingerprint_sha256": _string(
                    sealed.get("policy_fingerprint_sha256"),
                    label="confounder policy fingerprint",
                ),
                "sealed_before_oracle_score": _boolean(
                    sealed.get("sealed_before_oracle_score"),
                    label="confounder sealed_before_oracle_score",
                ),
                "oracle_read": _boolean(
                    sealed.get("oracle_read"),
                    label="confounder oracle_read",
                ),
                "state": _string(cell.get("state"), label="confounder state"),
            }
        )
    rows.sort(key=lambda row: str(row["cell_id"]))
    if len(rows) != 6 or len({str(row["cell_id"]) for row in rows}) != 6:
        raise QualificationContractError("D2 confounder observation set is not closed")
    metadata = {
        "schema_version": _string(
            matrix.get("schema_version"), label="D2 confounder matrix schema"
        ),
        "state": _string(matrix.get("state"), label="D2 confounder matrix state"),
        "failed_cell_ids": [
            _string(cell_id, label="D2 failed confounder cell id")
            for cell_id in _sequence(
                matrix.get("failed_cell_ids"), label="D2 failed confounder cell ids"
            )
        ],
        "field_graph_ids": [
            _string(graph_id, label="D2 confounder field graph id")
            for graph_id in _sequence(
                matrix.get("field_graph_ids"), label="D2 confounder field graph ids"
            )
        ],
        "policy_fingerprint_sha256": _string(
            matrix.get("policy_fingerprint_sha256"),
            label="D2 confounder matrix policy fingerprint",
        ),
        "selection_seed_consumed": _boolean(
            matrix.get("selection_seed_consumed"),
            label="D2 confounder selection_seed_consumed",
        ),
        "oracle_scoring_used": _boolean(
            matrix.get("oracle_scoring_used"),
            label="D2 confounder oracle_scoring_used",
        ),
        "joint_loop_registry_consumed": _boolean(
            matrix.get("joint_loop_registry_consumed"),
            label="D2 confounder joint_loop_registry_consumed",
        ),
    }
    return rows, metadata


def _core_outputs(result: Mapping[str, object]) -> list[records.D7V1DescriptiveOutput]:
    primary_units = [
        _mapping(item, label="core primary unit")
        for item in _sequence(
            result.get("core_primary_units"), label="core primary units"
        )
    ]
    bundle = _mapping(result.get("evidence_bundle"), label="evidence bundle")
    core_receipts = [
        _mapping(item, label="core cell receipt")
        for item in _sequence(
            bundle.get("core_cell_receipts"), label="core cell receipts"
        )
    ]
    core_cells = [
        _mapping(item, label="core cell")
        for item in _sequence(result.get("core_cells"), label="core cells")
    ]
    matrix, repeat_rows = _collapse_core_boundary_repeats(
        primary_units, core_cells, core_receipts
    )
    scalar_fields = ("amplitude", "identifiability_score", "support_counts")
    descriptor_only_count = 0
    for receipt in core_receipts:
        blind = _mapping(receipt.get("blind_input_receipt"), label="blind core input")
        if all(
            set(_mapping(blind.get(field), label=field)) == {"dtype", "shape", "sha256"}
            for field in scalar_fields
        ):
            descriptor_only_count += 1
    blocked = descriptor_only_count == len(core_receipts) and bool(core_receipts)
    if not blocked:
        raise QualificationContractError(
            "main D2 scalar persistence boundary unexpectedly changed"
        )
    confounder_rows, confounder_metadata = _d2_confounder_observation_rows(bundle)

    return [
        _output(
            "core-no-core-abstain-matrix",
            {
                "rows": matrix,
                "nested_graph_row_count": sum(len(row["graph_rows"]) for row in matrix),
                "expected_disposition_counts": dict(
                    sorted(
                        Counter(row["expected_disposition"] for row in matrix).items()
                    )
                ),
                "prediction_class_counts": dict(
                    sorted(Counter(row["prediction_class"] for row in matrix).items())
                ),
                "attempt_status_counts": dict(
                    sorted(Counter(row["attempt_status"] for row in matrix).items())
                ),
            },
        ),
        _output(
            "boundary-repeat-exact-agreement",
            {
                "rows": repeat_rows,
                "comparison_scope": (
                    "declared-outcomes-and-blind-array-descriptors-not-byte-or-"
                    "graph-identity"
                ),
                "all_declared_outcomes_equal": all(
                    row["declared_outcomes_equal"] is True for row in repeat_rows
                ),
                "all_blind_array_descriptors_equal": all(
                    all(row["blind_array_descriptor_equalities"].values())
                    for row in repeat_rows
                ),
                "blind_array_descriptor_fields": list(_CORE_BLIND_DESCRIPTOR_FIELDS),
                "boundary_specific_identity_fields_expected_to_differ": list(
                    _CORE_BOUNDARY_IDENTITY_FIELDS
                ),
            },
        ),
        _output(
            "amplitude-identifiability-support-separation",
            {
                "blocked_reason": (
                    "historical-main-d2-amplitude-identifiability-support-values-"
                    "not-persisted"
                ),
                "required_scalar_fields": list(scalar_fields),
                "main_core_cell_receipt_count": len(core_receipts),
                "descriptor_only_receipt_count": descriptor_only_count,
                "persisted_representation": "dtype-shape-sha256-only",
                "confounder_observation_rows": confounder_rows,
                "confounder_observation_row_count": len(confounder_rows),
                "confounder_matrix_metadata": confounder_metadata,
                "confounder_rows_are_not_main_d2_scientific_units": True,
                "confounder_rows_do_not_cure_main_d2_absence": True,
                "rerun_authorized": False,
                "partial_or_confounder_values_may_not_cure_main_d2_absence": True,
            },
            status="blocked",
        ),
    ]
