from __future__ import annotations

import hashlib
import json
from pathlib import Path

from spirallens.instrument_contracts.common import HypothesisId
from spirallens.referents import canonical_f0_f4_referent_contracts


ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = (
    ROOT
    / "experiments"
    / "qualification"
    / "p4_phase_capture_measurement_chain_v0_1"
    / "design.json"
)
DOC_PATH = ROOT / "docs" / "P4_PHASE_CAPTURE_MEASUREMENT_CHAIN.md"


def _load_design() -> dict[str, object]:
    return json.loads(DESIGN_PATH.read_bytes())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_design_identity_is_planning_only_and_closed_world() -> None:
    design = _load_design()

    assert set(design) == {
        "schema_version",
        "design_id",
        "decision_date",
        "status",
        "predecessor_binding",
        "target_observables",
        "claim_boundary",
        "graph_reception",
        "domain_cycle_contract",
        "field_hypotheses",
        "phase_like_regime_contract",
        "pattern_registry_contract",
        "core_contract",
        "measurement_chain",
        "control_contract",
        "detection_limit_contract",
        "transition_contract",
        "chronology",
        "stop_rules",
        "future_freeze_requirements",
        "authority",
        "nonclaims",
    }
    assert design["schema_version"] == (
        "spirallens.p4-phase-capture-measurement-chain-design.v0.1"
    )
    assert design["design_id"] == "p4-phase-capture-measurement-chain-v0.1"
    assert design["decision_date"] == "2026-08-27"
    assert design["status"] == "planned_not_frozen_not_run"

    claim_boundary = design["claim_boundary"]
    assert claim_boundary["claim_ceiling"] == "level_0"
    assert claim_boundary["design_only"] is True
    assert claim_boundary["unqualified_phase_field_forbidden"] is True
    assert claim_boundary["claim_delta"] == "none"
    assert claim_boundary["milestone_credit"] == "none"
    for key in (
        "thermodynamic_phase_claimed",
        "semantic_or_causal_claimed",
        "order_parameter_field_constructed",
        "core_score_or_candidate_constructed",
        "holonomy_observed",
        "sampled_winding_observed",
        "phase_like_regime_observed",
        "transition_observed",
        "integer_output_authority",
        "scientific_authority",
        "topology_authority",
        "semantic_authority",
    ):
        assert claim_boundary[key] is False

    authority = design["authority"]
    assert authority["design_record_write_authorized"] is True
    for key, value in authority.items():
        if key != "design_record_write_authorized":
            assert value is False


def test_design_binds_the_consumed_v02_terminal_without_authority_transfer() -> None:
    design = _load_design()
    predecessor = design["predecessor_binding"]

    assert predecessor["experiment_id"] == ("p4-graph-evaluability-calibration-v0.2")
    assert predecessor["source_commit"] == ("e25e6da1fea3ce3f09cd4745f6b08bb47f528d70")
    assert predecessor["interpretation_merge_commit"] == (
        "9cf7e79b6f723dfd5832697d5e45e9e4e24ca8d4"
    )
    assert predecessor["authority_transfer"] is False
    assert predecessor["outcome_reconstruction_authorized"] is False

    expected = {
        "launch": (
            "experiments/qualification/"
            "p4_graph_evaluability_calibration_v0_2/launch.json",
            "c6bfb9edf4f8ff22aaf2df8badcb137fb780158edf229543fc337e8e9400aeac",
        ),
        "attempt": (
            "experiments/qualification/"
            "p4_graph_evaluability_calibration_v0_2/attempt.json",
            "cce96c962ae3fd62b9eff75bc1205edde08f5943ee3a1ce63dc858fa7638e576",
        ),
        "terminal": (
            "experiments/qualification/"
            "p4_graph_evaluability_calibration_v0_2/terminal-result.json",
            "606893f6cfeb31fac476fd0658a6f1c9dab7ade4d40c7ba3c40f71c754fdfed0",
        ),
    }
    for artifact, (relative_path, expected_sha256) in expected.items():
        binding = predecessor[artifact]
        assert binding["path"] == relative_path
        assert binding["sha256"] == expected_sha256
        assert _sha256(ROOT / relative_path) == expected_sha256

    attempt = json.loads((ROOT / expected["attempt"][0]).read_bytes())
    terminal = json.loads((ROOT / expected["terminal"][0]).read_bytes())
    assert attempt["identity_consumed"] is True
    assert attempt["retry_resume_rescue_authorized"] is False
    assert predecessor["attempt"]["identity_consumed"] is True
    assert terminal["execution_terminal"] == "complete"
    assert terminal["result"]["terminal_state"] == "insufficient"
    assert terminal["result"]["reason"] == ("held-out-confirmation-structural-gate")
    assert predecessor["terminal"]["execution_terminal"] == "complete"
    assert predecessor["terminal"]["terminal_state"] == "insufficient"
    assert predecessor["terminal"]["reason"] == (
        "held-out-confirmation-structural-gate"
    )


def test_graph_reception_combines_transport_and_multi_nuisance_selection() -> None:
    graph = _load_design()["graph_reception"]

    assert graph["strategy"] == (
        "dimensionless-field-blind-scale-transport-plus-"
        "multi-nuisance-worst-case-calibration"
    )
    transport = graph["transport_rule_family"]
    assert transport == {
        "vertex_count_symbol": "n",
        "mutual_knn_neighbor_count": "ceil-kappa-times-n-minus-one",
        "local_scale": "median-declared-k-scale-neighbor-distance",
        "fixed_radius": "rho-times-local-scale",
        "shared_neighbor_count": "same-transported-neighbor-count",
        "minimum_shared_neighbors": "ceil-tau-times-neighbor-count",
        "exact_tie_clipping_and_float_rules_required_at_future_freeze": True,
        "concrete_hyperparameters_selected": False,
    }
    assert graph["calibration_nuisance_axes"] == [
        "seed",
        "density-warp",
        "noise",
        "sampling-density",
    ]
    assert graph["required_graph_families"] == [
        "mutual-knn",
        "fixed-radius",
        "shared-neighbor",
    ]
    assert graph["held_out_confirmation_rule"] == (
        "apply-sealed-transport-law-to-fresh-nuisance-without-reselection"
    )
    assert graph["post_confirmation_threshold_widening_authorized"] is False
    assert graph["selector_rerun_on_confirmation_authorized"] is False
    assert {
        "f2-values",
        "f4-values",
        "amplitude",
        "core",
        "holonomy",
        "winding",
        "phase-like-aggregate",
        "subject-outcome",
    }.issubset(graph["forbidden_reads"])


def test_domain_classes_precede_graph_support_and_cycle_indices_cannot_alias() -> None:
    contract = _load_design()["domain_cycle_contract"]

    assert contract["primary_domain"] == (
        "predeclared-two-dimensional-intervention-coordinate-domain"
    )
    assert contract["domain_fixed_before_graph_construction"] is True
    assert contract["cycle_identity"] == "oriented-domain-boundary-class"
    assert contract["graphs_validate_support_for_same_class"] is True
    assert contract["graph_specific_cycle_index_may_define_cross_family_identity"] is (
        False
    )
    assert contract["required_loop_relations"] == [
        "nested-core-centered",
        "reverse-orientation",
        "off-core",
        "multi-core-when-present",
        "deformation-companion",
        "sampling-refinement-companion",
    ]


def test_f2_and_f4_are_co_primary_and_match_the_referent_registry() -> None:
    fields = _load_design()["field_hypotheses"]
    referents = canonical_f0_f4_referent_contracts("1" * 64)
    f2 = referents.require(HypothesisId.F2_LOCAL_COVARIANT_SECTION)
    f4 = referents.require(HypothesisId.F4_SPIN_TWO_ANISOTROPY)

    assert fields["co_primary"] == [
        HypothesisId.F2_LOCAL_COVARIANT_SECTION.value,
        HypothesisId.F4_SPIN_TWO_ANISOTROPY.value,
    ]
    assert fields["winner_selected"] is False
    assert fields["outcome_selected_winner_authorized"] is False
    assert fields["branch_outcomes"] == [
        "both-qualified",
        "f2-only",
        "f4-only",
        "neither-qualified",
        "insufficient-support",
    ]
    assert fields["same_object_amplitude_and_direction_required"] is True
    assert fields["cross_fit_required"] is True
    assert fields["separate_order_parameter_spec_per_branch_required"] is True
    assert fields["selection_by_core_holonomy_winding_or_transition_forbidden"] is (
        True
    )

    assert fields["f2"]["pointwise_formula"] == f2.pointwise_formula_id
    assert fields["f2"]["amplitude_formula"] == f2.amplitude_formula_id
    assert fields["f2"]["gauge_law"] == f2.gauge_transformation_formula_id
    assert fields["f2"]["gauge_group"] == f2.gauge_group.value
    assert fields["f2"]["fit_evaluation_rule"] == f2.fit_evaluation_rule.value
    assert fields["f2"]["charge_convention"] == f2.charge_convention.value
    assert fields["f4"]["pointwise_formula"] == f4.pointwise_formula_id
    assert fields["f4"]["amplitude_formula"] == f4.amplitude_formula_id
    assert fields["f4"]["gauge_law"] == f4.gauge_transformation_formula_id
    assert fields["f4"]["gauge_group"] == f4.gauge_group.value
    assert fields["f4"]["fit_evaluation_rule"] == f4.fit_evaluation_rule.value
    assert fields["f4"]["charge_convention"] == f4.charge_convention.value
    assert fields["f4"]["ordinary_vector_charge_forbidden"] is True


def test_core_is_same_field_charge_blind_and_sealed_before_loops() -> None:
    core = _load_design()["core_contract"]

    assert core["charge_blind"] is True
    assert core["bound_to_same_order_parameter_field"] is True
    assert core["inputs"] == [
        "same-field-amplitude",
        "same-field-direction-identifiability-or-frame-conditioning",
        "independent-measurement-support-at-candidate",
    ]
    assert core["exact_scalar_and_threshold_deferred_to_future_calibration"] is True
    assert core["nested_radius_profile_required"] is True
    assert core["multiplicity_states"] == ["zero", "one", "many", "unresolved"]
    assert core["sealed_before_loop_readout"] is True
    assert core["ground_truth_anchor_is_separate"] is True
    assert core["select_candidate_by_observed_winding_authorized"] is False
    assert core["no_core_allows_geometry_branch"] is True
    assert core["no_core_allows_core_centered_defect_claim"] is False


def test_phase_like_regime_is_per_branch_three_way_and_sensitivity_bounded() -> None:
    contract = _load_design()["phase_like_regime_contract"]

    assert contract["unit_of_evaluation"] == (
        "per-field-branch-per-checkpoint-per-required-context-stratum"
    )
    assert contract["prerequisites"] == [
        "eligible-m3-order-parameter-field",
        "completed-m8-required-controls",
        "qualified-m9-detection-region",
        "separate-subject-protocol-freeze-and-authority",
    ]
    assert contract["same_field_observables"] == [
        "eligible-amplitude",
        "eligible-angular-coordinate",
        "declared-domain-coordinate",
        "support-mask",
    ]
    assert contract["branch_coordinate_bindings"] == {
        "f2": "vector-angle-arg-z",
        "f4": "doubled-angle-arg-w-with-director-angle-separate",
    }
    assert contract["required_statistic_families"] == [
        "amplitude-conditioned-circular-concentration-under-sealed-trivialization",
        "transport-corrected-domain-coordinate-angular-correlation",
        "coherent-support-coverage",
    ]
    assert contract["gauge_comparison_rule"] == (
        "declared-trivialization-or-relative-transport-with-pure-gauge-control"
    )
    assert contract["summary_statistics_and_numeric_thresholds_selected"] is False
    assert contract["outcomes"] == [
        "operational-phase-like-regime-candidate",
        "qualified-no-phase-like-regime-detected",
        "insufficient",
    ]
    assert contract["candidate_requires"] == [
        "held-out-departure-from-matched-nulls",
        "adequate-detection-sensitivity",
        "required-graph-gauge-architecture-and-context-robustness",
        "no-support-or-coverage-artifact",
    ]
    assert contract["qualified_non_detection_limited_to_detection_and_coverage_region"]
    assert contract["f2_f4_pooling_authorized"] is False
    assert contract["selection_by_core_holonomy_winding_or_transition_authorized"] is (
        False
    )
    assert contract["single_global_phase_scalar_authorized"] is False
    assert contract["thermodynamic_semantic_or_causal_interpretation_authorized"] is (
        False
    )


def test_partial_pattern_registry_retains_absence_and_unresolved_slots() -> None:
    registry = _load_design()["pattern_registry_contract"]

    assert registry["record_unit"] == (
        "per-checkpoint-with-declared-inter-checkpoint-transition-boundary-window"
    )
    assert registry["pattern_axes"] == [
        "f2-section-eligibility",
        "f4-section-eligibility",
        "f2-order-parameter-field",
        "f4-order-parameter-field",
        "f2-core-multiplicity",
        "f4-core-multiplicity",
        "geometry-relative-holonomy",
        "f2-operational-phase-like-regime",
        "f4-operational-phase-like-regime",
        "f2-sampled-winding",
        "f4-sampled-winding",
        "training-checkpoint-transition",
    ]
    assert registry["required_per_axis_fields"] == [
        "measurement-gate-state",
        "finding-state",
        "typed-value-or-value-reference",
        "support-and-coverage",
        "uncertainty",
        "graph-gauge-architecture-and-context-strata",
        "reason",
    ]
    assert registry["measurement_gate_states"] == [
        "pass",
        "fail",
        "insufficient",
        "not_run",
    ]
    assert registry["finding_states"] == [
        "candidate-present",
        "qualified-not-detected",
        "unresolved",
        "not-applicable",
    ]
    assert registry["every_axis_slot_required_in_record"] is True
    assert registry["all_axes_required_to_be_evaluable"] is False
    assert registry["qualified_non_detection_requires_pass_and_m9_region"] is True
    assert registry["fail_means_measurement_contract_failure_not_absence"] is True
    assert registry["insufficient_or_not_run_may_be_relabelled_absent"] is False
    assert registry["partial_patterns_retained"] is True
    assert registry[
        "pattern_may_select_graph_field_core_loop_threshold_or_checkpoint"
    ] is (False)
    assert registry["available_in_current_design"] is False


def test_measurement_chain_is_ordered_and_preserves_branch_boundaries() -> None:
    stages = _load_design()["measurement_chain"]
    assert [stage["stage_id"] for stage in stages] == [
        f"M{index}" for index in range(12)
    ]
    seen: set[str] = set()
    for stage in stages:
        for requirement in stage["requires"]:
            if requirement.startswith("M"):
                assert requirement in seen
        seen.add(stage["stage_id"])

    by_id = {stage["stage_id"]: stage for stage in stages}
    assert by_id["M1"]["blocks_all_downstream_on_required-insufficient-or-fail"] is (
        True
    )
    assert by_id["M2"]["winner_selection_permitted"] is False
    assert by_id["M4"]["loop_readout_before_seal_forbidden"] is True
    assert by_id["M5"]["recenter_or_replace_after_readout_forbidden"] is True
    assert by_id["M6"]["integer_output"] is False
    assert by_id["M7"]["nearest_integer_label_authorized"] is False
    assert by_id["M8"]["requires"] == ["M3", "M5"]
    assert by_id["M8"]["conditional_branch_inputs"] == {
        "geometry": "M6-if-geometry-eligible",
        "defect": "M7-if-defect-eligible",
    }
    assert by_id["M8"]["outputs"] == [
        "per-field-phase-like-regime-control-gates",
        "geometry-branch-gate",
        "defect-branch-gate",
        "coverage-and-abstention-receipts",
    ]
    assert by_id["M8"]["independent_branch_gating"] is True
    assert by_id["M8"]["required_insufficient_cells_may_be_dropped"] is False
    assert by_id["M9"]["instrument_detection_boundary_is_model_transition"] is (False)
    assert by_id["M10"]["outputs"] == [
        "per-branch-operational-phase-like-regime-outcome",
        "per-checkpoint-partial-cooccurrence-pattern-record",
        "operational-model-regime-transition-candidate-or-bounded-null",
    ]
    assert by_id["M10"]["available_in_current_design"] is False
    assert by_id["M11"]["available_in_current_design"] is False


def test_detection_surface_and_model_transition_are_distinct() -> None:
    design = _load_design()
    detection = design["detection_limit_contract"]
    transition = design["transition_contract"]

    assert detection["full_pipeline_required"] is True
    assert detection["detection_boundary_is_scientific_transition"] is False
    assert detection["complete_before_claim_bearing_model_run"] is True
    assert "qualified-null-region" in detection["outputs"]
    assert detection["per_target_and_branch_surfaces_required"] is True
    assert detection["joint_partial_pattern_surface_required"] is True
    assert detection["unavailable_branch_may_be_imputed"] is False

    assert transition["primary_future_axis"] == "ordered-training-checkpoint"
    assert transition["exact_checkpoint_identities_selected"] is False
    assert transition["intervention_strength_role"] == "later-causal-probe-axis"
    assert transition["layer_role"] == "architectural-depth-profile-not-time"
    assert transition["observable_panel"] == [
        "f2-and-f4-field-eligibility-and-support",
        "same-object-angular-order-parameter-distributions",
        "same-object-amplitude-distributions",
        "per-branch-operational-phase-like-regime-outcomes",
        "charge-blind-core-profiles",
        "relative-holonomy-distributions",
        "unrounded-winding-and-stability-distributions",
        "graph-family-agreement-coverage-abstention-and-controls",
    ]
    assert transition["checkpoint_identity_and_alignment_requirements"] == [
        "exact-checkpoint-hash-and-training-step",
        "common-model-family-architecture-tokenizer-context-and-address-domain",
        "common-intervention-domain-coordinates",
        "declared-gauge-invariant-comparison-or-fit-only-alignment",
        "no-outcome-selected-basis-or-alignment",
        "optimizer-data-mixture-and-schedule-discontinuities-declared-as-covariates",
    ]
    assert transition["discovery_may_fit_bounded_change_point"] is True
    assert transition["held_out_confirmation_may_move_change_point_window"] is (False)
    assert transition["candidate_requires"] == [
        "held-out-change-in-at-least-one-field-or-core-observable",
        "held-out-change-in-at-least-one-independent-geometry-or-defect-observable",
        "overlapping-change-point-uncertainty",
        "required-graph-family-robustness",
        "adequate-detection-sensitivity",
        "replication-across-required-context-strata",
        "no-omitted-required-stratum",
    ]
    assert transition["single_spike_or_coverage_loss_is_transition"] is False
    assert (
        transition[
            "outcome_selected_hypothesis_graph_layer_alignment_or_checkpoint_range_authorized"
        ]
        is False
    )


def test_chronology_future_freeze_and_nonclaims_fail_closed() -> None:
    design = _load_design()
    chronology = design["chronology"]
    assert chronology["required_seal_order"] == [
        "identities-roles-budgets-and-input-definitions",
        "graph-transport-rule-and-hyperparameters",
        "f2-f4-specifications-and-fit-evaluation-partitions",
        "amplitude-identifiability-and-core-rules",
        "core-candidates",
        "loop-and-class-ensemble",
        "control-matrix-and-numeric-thresholds",
        "checkpoint-identity-common-coordinates-alignment-covariates-transition-axis-observable-panel-and-change-point-rule",
        "calibration-selection-decision",
        "hidden-confirmation-access",
    ]
    assert chronology["operator_prior_p4_v02_outcome_exposure"] is True
    assert chronology["independent"] is False
    assert chronology["preregistered"] is False
    assert chronology["cryptographic_unseen"] is False
    assert chronology["dynamic_timestamp_present"] is False

    future = design["future_freeze_requirements"]
    assert all(value is True for value in future.values())
    assert design["stop_rules"] == [
        "stop-insufficient-before-field-readout-if-graph-reception-is-not-jointly-evaluable",
        "stop-or-branch-explicitly-on-field-amplitude-orientation-core-loop-sensitivity-or-coverage-insufficiency",
        "stop-fail-on-evaluable-known-positive-required-null-covariance-graph-invariance-or-held-out-transition-error",
        "never-convert-fail-to-insufficient-by-post-outcome-floor-change",
        "never-drop-required-family-hypothesis-context-or-checkpoint-after-observation",
    ]
    assert design["nonclaims"] == [
        "no-p4-v03-protocol-or-run-exists",
        "no-graph-transport-rule-has-been-calibrated",
        "no-f2-or-f4-model-field-has-been-observed",
        "no-order-parameter-or-core-has-been-constructed",
        "no-holonomy-or-winding-has-been-observed",
        "no-phase-like-regime-or-transition-has-been-observed",
        "no-qualified-null-has-been-established",
        "no-scientific-topology-semantic-or-publication-authority-is-granted",
    ]


def test_human_readable_design_retains_the_same_boundaries() -> None:
    document = DOC_PATH.read_text(encoding="utf-8")

    for required in (
        "**Status:** `planned_not_frozen_not_run`",
        "dimensionless parameter-transport law",
        "F2 and F4 remain co-primary",
        "operational-phase-like-regime-candidate",
        "qualified-no-phase-like-regime-detected",
        "Partial-pattern registry",
        "may never be recoded as absence",
        "Core localization precedes every loop value",
        "The graph families do not invent the loop",
        "detection boundary, not evidence of",
        "primary future model-transition axis is ordered training checkpoint",
        "gauge-invariant observables or an alignment fitted only on the fit partition",
        "replication across the required context strata",
        "does not authorize P4 v0.3 execution",
    ):
        assert required in document
