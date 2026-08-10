"""Private independence outputs for the D7 v1 descriptive successor."""

from __future__ import annotations

from collections.abc import Mapping

from spirallens.core.canonical import canonical_json_bytes, sha256_bytes

from .common import QualificationContractError
from . import confirmation_v1_records as records
from .confirmation_v1_descriptive_common import (
    _mapping,
    _output,
    _sequence,
    _string,
)

__all__: tuple[str, ...] = ()


def _independence_outputs(
    plan: Mapping[str, object],
    protocol: Mapping[str, object],
    result: Mapping[str, object],
    manifest: Mapping[str, object],
    consumption: Mapping[str, object],
    d6_decision: Mapping[str, object],
) -> list[records.D7V1DescriptiveOutput]:
    selection = _mapping(protocol.get("selection"), label="selection")
    cartesian = _mapping(protocol.get("cartesian"), label="cartesian")
    graphs = _mapping(protocol.get("graphs"), label="graphs")
    implementation = _mapping(
        protocol.get("implementation_registry"), label="implementation registry"
    )
    thresholds = _mapping(protocol.get("thresholds"), label="locked thresholds")
    engine = _mapping(protocol.get("engine"), label="protocol engine")
    admission = _mapping(
        d6_decision.get("confirmation_admission_spec"),
        label="confirmation admission spec",
    )
    bundle = _mapping(result.get("evidence_bundle"), label="evidence bundle")
    field_graphs = [
        _mapping(item, label="field graph")
        for item in _sequence(graphs.get("field_estimation"), label="field graphs")
    ]
    cycle_graphs = [
        _mapping(item, label="cycle graph")
        for item in _sequence(graphs.get("cycle_construction"), label="cycle graphs")
    ]
    seeds = _sequence(selection.get("seeds"), label="selection seeds")
    implementation_sha256 = sha256_bytes(canonical_json_bytes(implementation))
    thresholds_sha256 = sha256_bytes(canonical_json_bytes(thresholds))
    if (
        implementation_sha256
        != admission.get("selection_implementation_registry_sha256")
        or thresholds_sha256 != admission.get("locked_thresholds_sha256")
        or cartesian.get("generator_family_id")
        != admission.get("selection_generator_family_id")
        or implementation.get("surrogate_estimator_id")
        != admission.get("required_surrogate_estimator_id")
        or engine.get("commit") != consumption.get("engine_commit")
    ):
        raise QualificationContractError(
            "independence-map protocol, admission, and execution joins differ"
        )

    def unique_estimator_id(receipt_key: str) -> str:
        estimator_ids = {
            _string(
                _mapping(
                    _mapping(item, label=receipt_key[:-1]).get(
                        "sealed_prediction_receipt"
                    ),
                    label=f"{receipt_key} sealed prediction",
                ).get("estimator_id"),
                label=f"{receipt_key} estimator_id",
            )
            for item in _sequence(bundle.get(receipt_key), label=receipt_key)
        }
        if len(estimator_ids) != 1:
            raise QualificationContractError(
                f"{receipt_key} does not retain one exact estimator identity"
            )
        return next(iter(estimator_ids))

    core_estimator_id = unique_estimator_id("core_cell_receipts")
    loop_estimator_id = unique_estimator_id("loop_cell_receipts")
    estimator_ids = [
        implementation["surrogate_estimator_id"],
        core_estimator_id,
        loop_estimator_id,
    ]
    if len(set(estimator_ids)) != 3:
        raise QualificationContractError("role-specific estimator identities collapse")

    field_families = sorted(str(item["family"]) for item in field_graphs)
    cycle_families = sorted(str(item["family"]) for item in cycle_graphs)
    if field_families != cycle_families or len(set(field_families)) != 3:
        raise QualificationContractError("field and cycle graph families differ")

    core_oracle_ids = {
        _string(item.get("oracle_fingerprint_sha256"), label="core oracle identity")
        for raw in _sequence(result.get("core_cells"), label="core cells")
        for item in (_mapping(raw, label="core cell"),)
    }
    loop_oracle_ids = {
        _string(item.get("oracle_fingerprint_sha256"), label="loop oracle identity")
        for raw in _sequence(result.get("crossed_cells"), label="crossed cells")
        for item in (_mapping(raw, label="crossed cell"),)
    }
    if (
        len(core_oracle_ids) != 192
        or len(loop_oracle_ids) != 1_152
        or core_oracle_ids & loop_oracle_ids
    ):
        raise QualificationContractError("oracle payload identity surface differs")

    for receipt_key in ("core_cell_receipts", "loop_cell_receipts"):
        for raw in _sequence(bundle.get(receipt_key), label=receipt_key):
            receipt = _mapping(raw, label=receipt_key[:-1])
            prediction = _mapping(
                receipt.get("sealed_prediction_receipt"),
                label=f"{receipt_key} sealed prediction",
            )
            truth = _mapping(
                receipt.get("oracle_truth_receipt"),
                label=f"{receipt_key} oracle truth",
            )
            if (
                prediction.get("oracle_read") is not False
                or prediction.get("sealed_before_oracle_score") is not True
                or truth.get("estimator_input_allowed") is not False
            ):
                raise QualificationContractError(
                    "oracle separation boundary differs in the evidence bundle"
                )
            if (
                receipt_key == "loop_cell_receipts"
                and truth.get("oracle_integer_is_synthetic_expected_sampled_outcome")
                is not True
            ):
                raise QualificationContractError(
                    "loop oracle synthetic-outcome boundary differs"
                )

    map_rows = [
        {
            "dimension_id": "generator-construction",
            "identities": [cartesian["generator_family_id"]],
            "identity_count": 1,
            "sharing_relation": "all selection observations share one family",
            "independence_supported": False,
            "detail": {
                "construction_family_id": admission["selection_construction_family_id"],
                "generator_case_count": len(
                    _sequence(
                        implementation.get("generator_cases"),
                        label="generator cases",
                    )
                ),
            },
        },
        {
            "dimension_id": "seed-block",
            "identities": list(seeds),
            "identity_count": len(seeds),
            "sharing_relation": "same-family repeated seed blocks",
            "independence_supported": False,
            "detail": {"seed_block_independence_proved": False},
        },
        {
            "dimension_id": "boundary-repeat",
            "identities": sorted(
                str(_mapping(item, label="boundary")["level"])
                for item in cartesian["primary_boundaries"]
            ),
            "identity_count": len(cartesian["primary_boundaries"]),
            "sharing_relation": "paired nuisance repeats",
            "independence_supported": False,
            "detail": {
                "d2_repeated_measure": True,
                "d4_d5_execution_retained": True,
            },
        },
        {
            "dimension_id": "graph-family",
            "identities": field_families,
            "identity_count": len(field_families),
            "sharing_relation": "within-execution repeated measures",
            "independence_supported": False,
            "detail": {
                "field_graph_ids": sorted(
                    str(item["graph_id"]) for item in field_graphs
                ),
                "cycle_graph_ids": sorted(
                    str(item["graph_id"]) for item in cycle_graphs
                ),
                "graph_role_record_count": len(field_graphs) + len(cycle_graphs),
                "crossed_cells_per_execution": (
                    len(field_graphs) * len(cycle_graphs) * 2
                ),
            },
        },
        {
            "dimension_id": "implementation",
            "identities": [implementation_sha256],
            "identity_count": 1,
            "sharing_relation": "one frozen implementation registry",
            "independence_supported": False,
            "detail": {"engine_commit": engine["commit"]},
        },
        {
            "dimension_id": "estimator",
            "identities": estimator_ids,
            "identity_count": len(estimator_ids),
            "sharing_relation": "shared role-specific mechanisms",
            "independence_supported": False,
            "detail": {"role_count": 3},
        },
        {
            "dimension_id": "threshold",
            "identities": [thresholds_sha256],
            "identity_count": 1,
            "sharing_relation": "one locked threshold set",
            "independence_supported": False,
            "detail": {"postselection_threshold_change_authorized": False},
        },
        {
            "dimension_id": "oracle",
            "identities": {
                "core_payload_count": len(core_oracle_ids),
                "loop_payload_count": len(loop_oracle_ids),
                "synthetic_oracle_mechanism_shared": True,
            },
            "identity_count": len(core_oracle_ids | loop_oracle_ids),
            "sharing_relation": (
                "different payload hashes do not prove independent observers"
            ),
            "independence_supported": False,
            "detail": {"oracle_read_before_prediction": False},
        },
        {
            "dimension_id": "evidence-bundle",
            "identities": [result["result_evidence_root_sha256"]],
            "identity_count": 1,
            "sharing_relation": "one terminal evidence lineage",
            "independence_supported": False,
            "detail": {
                "consumption_id": consumption["consumption_id"],
                "terminal_artifact_sha256": manifest["terminal_artifact_sha256"],
            },
        },
    ]

    scientific_units = [
        _mapping(item, label="scientific unit")
        for item in _sequence(plan.get("scientific_units"), label="scientific units")
    ]
    construction_unit = next(
        item
        for item in scientific_units
        if item.get("unit_id") == "construction-family-unit"
    )
    diversity_rows = [
        {
            "category": "deterministic-replay",
            "evidence_state": "observed_scoped",
            "detail": {
                "graph_records_reconstructed": result[
                    "pr8_graph_records_reconstructed"
                ],
                "d8_isolated_replay_state": _mapping(
                    d6_decision.get("d8"), label="D8 decision"
                )["state"],
            },
            "independent_confirmation_credit": False,
        },
        {
            "category": "same-family-replication",
            "evidence_state": "observed",
            "detail": {
                "seed_block_count": len(seeds),
                "seed_block_independence_proved": False,
            },
            "independent_confirmation_credit": False,
        },
        {
            "category": "construction-diversity",
            "evidence_state": "absent",
            "detail": {
                "observed_construction_family_count": construction_unit[
                    "declared_count"
                ],
                "confirmation_family_admitted": d6_decision[
                    "confirmation_family_admitted"
                ],
                "graph_protocol_difference_is_construction_diversity": False,
            },
            "independent_confirmation_credit": False,
        },
        {
            "category": "implementation-diversity",
            "evidence_state": "absent",
            "detail": {"implementation_registry_count": 1},
            "independent_confirmation_credit": False,
        },
        {
            "category": "epistemic-independence",
            "evidence_state": "not_established",
            "detail": {"independent_confirmation_count": 0},
            "independent_confirmation_credit": False,
        },
    ]

    nonclaim_fields = {
        "external_prior_observation_excluded": result[
            "external_prior_observation_excluded"
        ],
        "hidden_confirmation_accessed": result["hidden_confirmation_accessed"],
        "representation_d2_d5_qualified": result["representation_d2_d5_qualified"],
        "synthetic_qualified": result["synthetic_qualified"],
        "confirmation_family_admitted": d6_decision["confirmation_family_admitted"],
        "confirmation_values_accessed": d6_decision["confirmation_values_accessed"],
    }
    epistemic_nonclaim_rows = [
        {
            "claim_ceiling": "level_0",
            "claim_delta": "none",
            "observed_construction_family_count": construction_unit["declared_count"],
            "confirmation_family_admitted": d6_decision["confirmation_family_admitted"],
            "independent_confirmation_count": 0,
            "seed_block_independence_proved": False,
            "seed_change_alone_sufficient": admission["seed_change_alone_sufficient"],
            "source_or_implementation_change_alone_sufficient": admission[
                "source_or_implementation_change_alone_sufficient"
            ],
            "boundary_variants_are_repeated_measures": True,
            "graph_cells_are_repeated_measures": True,
            "graph_protocol_difference_is_construction_diversity": False,
            "construction_family_generalization_claimed": False,
            "epistemic_independence_claimed": False,
            "inferential_sample_size_claimed": False,
        }
    ]
    return [
        _output(
            "shared-generator-seed-graph-boundary-implementation-oracle-map",
            {
                "rows": map_rows,
                "dimension_count": len(map_rows),
                "hash_inequality_implies_independence": False,
                "shared_dimensions_are_not_independent_evidence": True,
                "graph_pairs_are_not_iid_replicates": True,
            },
        ),
        _output(
            "replication-versus-construction-diversity-table",
            {
                "rows": diversity_rows,
                "category_count": len(diversity_rows),
                "graph_protocol_difference_is_construction_diversity": False,
                "observed_construction_family_count": construction_unit[
                    "declared_count"
                ],
                "seed_block_independence_proved": False,
                "independent_confirmation_observed": False,
            },
        ),
        _output(
            "epistemic-independence-nonclaim",
            {
                "rows": epistemic_nonclaim_rows,
                "claim_ceiling": "level_0",
                "claim_delta": "none",
                "observed_parent_facts": nonclaim_fields,
                "one_immutable_evidence_lineage_is_not_a_scientific_replicate": True,
                "replication_is_not_construction_diversity": True,
                "independent_confirmation_observed": False,
                "d0_d6_claim_strengthened": False,
                "d7_design_selected_from_these_descriptive_values": False,
                "scientific_claim_eligible": False,
            },
        ),
    ]
