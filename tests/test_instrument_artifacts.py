from __future__ import annotations

from dataclasses import replace
import hashlib

import pytest

from spirallens.instrument_contracts.artifact_loader import (
    MAX_INSTRUMENT_ARTIFACT_BYTES,
    InstrumentArtifactIntegrityError,
    InstrumentArtifactSchemaError,
    load_instrument_artifact,
)
from spirallens.instrument_contracts.artifacts import (
    _P0_CALIBRATION_SELECTIONS_BY_HYPOTHESIS,
    _P0_FIXED_SELECTIONS_BY_HYPOTHESIS,
    CalibrationConfirmationResult,
    CalibrationSelectionDecision,
    CandidateGraph,
    CoreCandidate,
    CoreScore,
    DefectCoordinateBinding,
    DefectLocalizationBinding,
    DefectLoopEstimate,
    EdgeConnection,
    GeometricFieldEstimate,
    GeometryLoopEstimate,
    GraphConstructionSpec,
    GroundTruthAnchor,
    HypothesisDecision,
    HypothesisFixedChoice,
    HypothesisResolvedChoice,
    HypothesisRuleChoice,
    InheritedFieldGraphBinding,
    OrderParameterField,
    OrderParameterSpec,
    SubstrateBinding,
    SyntheticLatticeContextBinding,
    SyntheticLatticeSubstrateBinding,
    SupportDiagnostic,
    core_graph_binding_from_dict,
    instrument_artifact_from_dict,
)
from spirallens.instrument_contracts.common import (
    ARTIFACT_SCHEMA_VERSION_BY_TYPE,
    ArtifactRef,
    ArtifactType,
    ClaimLevel,
    ContractValidationError,
    EvolutionAxis,
    FitRole,
    GateState,
    HypothesisDisposition,
    HypothesisId,
    PayloadKind,
    PayloadRef,
    ResolutionState,
    RuleChoice,
    ScientificBranch,
)


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


ROW = _digest("substrate-row-order")
VERTEX_ORDER = _digest("vertex-order")
EDGE_ORDER = _digest("edge-order")
CYCLE_ORDER = _digest("cycle-order")
LOOP_ORDER = _digest("loop-order")
CALIBRATION_ORDER = _digest("calibration-order")


def _ref(artifact_type: ArtifactType, artifact_id: str) -> ArtifactRef:
    return ArtifactRef(
        artifact_type=artifact_type,
        schema_version=ARTIFACT_SCHEMA_VERSION_BY_TYPE[artifact_type],
        artifact_id=artifact_id,
        canonical_sha256=_digest(f"artifact:{artifact_id}"),
    )


def _array(
    label: str,
    *,
    row_identity: str = ROW,
    shape: tuple[int, ...] = (4,),
    dtype: str = "<f4",
) -> PayloadRef:
    return PayloadRef(
        kind=PayloadKind.ARRAY,
        sha256=_digest(f"payload:{label}"),
        byte_length=4096,
        media_type="application/x-npy",
        dtype=dtype,
        shape=shape,
        row_identity_sha256=row_identity,
    )


def _records(
    label: str,
    *,
    row_identity: str = CALIBRATION_ORDER,
    count: int = 4,
) -> PayloadRef:
    return PayloadRef(
        kind=PayloadKind.JSON_RECORDS,
        sha256=_digest(f"payload:{label}"),
        byte_length=32,
        media_type="application/x-ndjson",
        record_count=count,
        row_identity_sha256=row_identity if count else None,
    )


def _opaque(label: str) -> PayloadRef:
    return PayloadRef(
        kind=PayloadKind.OPAQUE,
        sha256=_digest(f"payload:{label}"),
        byte_length=8,
        media_type="application/octet-stream",
    )


def _synthetic_context(
    *,
    row_identity: str = ROW,
    lattice_shape: tuple[int, int] = (2, 2),
) -> SyntheticLatticeContextBinding:
    return SyntheticLatticeContextBinding(
        context_id="representation-phantom-lattice",
        source_id="p1-representation-phantom-v0.1",
        generator_revision="a" * 40,
        generator_module_sha256=_digest("synthetic-generator-module"),
        generator_spec_sha256=_digest("synthetic-generator-spec"),
        protocol_source_sha256=_digest("synthetic-protocol-source"),
        protocol_canonical_sha256=_digest(
            "synthetic-protocol-canonical"
        ),
        row_identity_sha256=row_identity,
        lattice_shape=lattice_shape,
        boundary_rule="open",
    )


def _fixed(family_id: str, selected_id: str) -> RuleChoice:
    return RuleChoice(
        family_id=family_id,
        resolution=ResolutionState.FIXED_BY_HYPOTHESIS,
        selected_id=selected_id,
    )


def _resolved(family_id: str, selected_id: str) -> RuleChoice:
    return RuleChoice(
        family_id=family_id,
        resolution=ResolutionState.CALIBRATION_RESOLVED,
        selected_id=selected_id,
    )


def _resolved_choices(
    hypothesis_id: HypothesisId,
    selections: dict[str, str],
) -> tuple[HypothesisResolvedChoice, ...]:
    return tuple(
        HypothesisResolvedChoice(
            hypothesis_id=hypothesis_id,
            choice=_resolved(family_id, selected_id),
        )
        for family_id, selected_id in sorted(selections.items())
    )


def _first_p0_resolved_choices(
    hypothesis_id: HypothesisId,
) -> tuple[HypothesisResolvedChoice, ...]:
    return _resolved_choices(
        hypothesis_id,
        {
            family_id: sorted(candidate_ids)[0]
            for family_id, candidate_ids in (
                _P0_CALIBRATION_SELECTIONS_BY_HYPOTHESIS[
                    hypothesis_id
                ].items()
            )
        },
    )


def _p0_unresolved_choices(
    *resolved_hypotheses: HypothesisId,
) -> tuple[HypothesisRuleChoice, ...]:
    resolved = set(resolved_hypotheses)
    return tuple(
        HypothesisRuleChoice(
            hypothesis_id=hypothesis_id,
            choice=RuleChoice(
                family_id=family_id,
                resolution=ResolutionState.CALIBRATION_SELECTION,
                candidate_ids=tuple(sorted(candidate_ids)),
            ),
        )
        for hypothesis_id in sorted(
            HypothesisId,
            key=lambda item: item.value,
        )
        if hypothesis_id not in resolved
        for family_id, candidate_ids in sorted(
            _P0_CALIBRATION_SELECTIONS_BY_HYPOTHESIS[
                hypothesis_id
            ].items()
        )
    )


def _p0_fixed_choices() -> tuple[HypothesisFixedChoice, ...]:
    values: list[HypothesisFixedChoice] = []
    for hypothesis_id in sorted(HypothesisId, key=lambda item: item.value):
        for family_id, selected_ids in sorted(
            _P0_FIXED_SELECTIONS_BY_HYPOTHESIS[hypothesis_id].items()
        ):
            assert len(selected_ids) == 1
            values.append(
                HypothesisFixedChoice(
                    hypothesis_id=hypothesis_id,
                    choice=_fixed(
                        family_id,
                        next(iter(selected_ids)),
                    ),
                )
            )
    return tuple(values)


def _f2_resolved_choices() -> tuple[HypothesisResolvedChoice, ...]:
    return _resolved_choices(
        HypothesisId.F2_LOCAL_COVARIANT_SECTION,
        {
            "architecture_accounting_rule": (
                "explicit_component_accounting"
            ),
            "centering_rule": "global_centering",
            "estimator": "cross_fitted_local_frame",
            "fit_role": "calibration_selection",
            "input_tensor": "accounted_response",
            "interpolation_rule": (
                "connection_transport_interpolation"
            ),
            "lift_rule": "connection_corrected_lift",
            "observation_axis": "layer_index",
            "reference_rule": "connection_defined_reference",
            "residual_rule": "architecture_accounted_response",
            "trivialization_rule": "local_frame_with_connection",
        },
    )


def _f4_resolved_choices() -> tuple[HypothesisResolvedChoice, ...]:
    return _resolved_choices(
        HypothesisId.F4_SPIN_TWO_ANISOTROPY,
        {
            "architecture_accounting_rule": (
                "explicit_component_accounting"
            ),
            "centering_rule": "global_centering",
            "estimator": "local_traceless_tensor",
            "fit_role": "calibration_selection",
            "input_tensor": "accounted_response",
            "interpolation_rule": "doubled_angle_geodesic",
            "observation_axis": "layer_index",
            "reference_rule": "doubled_angle_reference",
            "residual_rule": "architecture_accounted_response",
            "trivialization_rule": "director_bundle_trivialization",
        },
    )


def _artifact_set() -> dict[str, object]:
    registry_ref = _ref(
        ArtifactType.HYPOTHESIS_REGISTRY,
        "registry-p0",
    )
    context_ref = _ref(ArtifactType.CONTEXT_BANK, "context-bank-p0")
    substrate_ref = _ref(ArtifactType.SUBSTRATE_BINDING, "substrate-p0")
    graph_spec_ref = _ref(
        ArtifactType.GRAPH_CONSTRUCTION_SPEC,
        "field-graph-spec",
    )
    graph_ref = _ref(ArtifactType.CANDIDATE_GRAPH, "field-graph")
    geometry_field_ref = _ref(
        ArtifactType.GEOMETRIC_FIELD_ESTIMATE,
        "geometry-field",
    )
    order_spec_ref = _ref(
        ArtifactType.ORDER_PARAMETER_SPEC,
        "order-spec",
    )
    order_field_ref = _ref(
        ArtifactType.ORDER_PARAMETER_FIELD,
        "order-field",
    )
    core_score_ref = _ref(ArtifactType.CORE_SCORE, "core-score")
    core_candidate_ref = _ref(
        ArtifactType.CORE_CANDIDATE,
        "core-candidate",
    )
    edge_ref = _ref(ArtifactType.EDGE_CONNECTION, "edge-connection")
    selection_ref = _ref(
        ArtifactType.CALIBRATION_SELECTION_DECISION,
        "selection-decision",
    )

    substrate = SubstrateBinding(
        artifact_id="substrate-p0",
        role=FitRole.CALIBRATION_SELECTION,
        evolution_axis=EvolutionAxis.LAYER_INDEX,
        row_identity_sha256=ROW,
        context_bank=context_ref,
        vertex_identities=_array(
            "vertex-identities",
            dtype="<i8",
        ),
        observation_identities=_array(
            "observation-identities",
            dtype="<i8",
        ),
        states=_array("states", shape=(4, 8)),
        accounted_response=_array("accounted-response"),
        mask=_array("mask", dtype="|b1"),
        preprocessing_fit=_opaque("preprocessing-fit"),
    )
    graph_spec = GraphConstructionSpec(
        artifact_id="field-graph-spec",
        substrate=substrate_ref,
        purpose="field_estimation",
        family=_fixed("graph_family", "mutual-knn"),
        metric=_fixed("graph_metric", "cosine"),
        scale=_fixed("graph_scale", "local"),
        constructor_id="deterministic-graph-v1",
        deterministic_tie_policy="lexicographic-vertex-id",
        allowed_role=FitRole.CALIBRATION_SELECTION,
    )
    candidate_graph = CandidateGraph(
        artifact_id="field-graph",
        substrate=substrate_ref,
        specification=graph_spec_ref,
        vertex_order_sha256=VERTEX_ORDER,
        edge_order_sha256=EDGE_ORDER,
        cycle_order_sha256=CYCLE_ORDER,
        vertices=_array(
            "graph-vertices",
            row_identity=VERTEX_ORDER,
            dtype="<i8",
        ),
        canonical_edges=_array(
            "graph-edges",
            row_identity=EDGE_ORDER,
            shape=(4, 2),
            dtype="<i8",
        ),
        weights=_array("graph-weights", row_identity=EDGE_ORDER),
        connected_components=_array(
            "connected-components",
            row_identity=VERTEX_ORDER,
            dtype="<i8",
        ),
        degree_distribution=_array(
            "degree-distribution",
            row_identity=VERTEX_ORDER,
            dtype="<i8",
        ),
        two_core=_array(
            "two-core",
            row_identity=VERTEX_ORDER,
            dtype="|b1",
        ),
        cycle_support=_array(
            "cycle-support",
            row_identity=CYCLE_ORDER,
            shape=(4, 3),
            dtype="<i8",
        ),
    )
    support = SupportDiagnostic(
        artifact_id="support-diagnostic",
        substrate=substrate_ref,
        row_identity_sha256=ROW,
        scalar_definition_id="local-support-v1",
        neighborhood_specification=graph_ref,
        fit_role=FitRole.CALIBRATION_SELECTION,
        values=_array("support-values"),
        uncertainty=_array("support-uncertainty"),
        support=_array("support-mask", dtype="|b1"),
        pointwise_reason_codes=_array(
            "support-reasons",
            dtype="<i4",
        ),
        claim_ceiling=ClaimLevel.LEVEL_1G,
    )
    geometric_field = GeometricFieldEstimate(
        artifact_id="geometry-field",
        hypothesis_registry=registry_ref,
        substrate=substrate_ref,
        estimation_graph=graph_ref,
        hypothesis_id=HypothesisId.F1_PROJECTOR_CONNECTION,
        fit_receipt=_opaque("geometry-fit-receipt"),
        row_identity_sha256=ROW,
        projector_or_frame=_array(
            "projector",
            shape=(4, 2, 2),
        ),
        eigenspectrum=_array("geometry-eigenspectrum", shape=(4, 2)),
        support=_array("geometry-support", dtype="|b1"),
        gauge_law_id="projector-gauge-v1",
        claim_ceiling=ClaimLevel.LEVEL_1G,
    )
    order_spec = OrderParameterSpec(
        artifact_id="order-spec",
        hypothesis_registry=registry_ref,
        substrate=substrate_ref,
        estimation_graph=graph_ref,
        hypothesis_id=HypothesisId.F2_LOCAL_COVARIANT_SECTION,
        input_binding=_opaque("order-input-binding"),
        fit_receipt=_opaque("order-fit-receipt"),
        target_manifold_id="rp1",
        gauge_law_id="local-sign-gauge-v1",
        charge_group=_fixed("charge_group", "z2"),
        amplitude_rule=_fixed("amplitude_rule", "spectral-gap"),
        identifiability_rule=_fixed(
            "identifiability_rule",
            "support-threshold",
        ),
        interpolation_rule=_fixed(
            "interpolation_rule",
            "geodesic-shortest",
        ),
        lift_rule=_fixed("lift_rule", "local-continuous-lift"),
        trivialization_rule=_fixed(
            "trivialization_rule",
            "edge-frame-v1",
        ),
        reference_rule=_fixed("reference_rule", "canonical-first"),
        forbidden_labels=("concept", "oam", "phase", "vortex"),
        claim_ceiling=ClaimLevel.LEVEL_1D,
    )
    order_field = OrderParameterField(
        artifact_id="order-field",
        specification=order_spec_ref,
        hypothesis_id=HypothesisId.F2_LOCAL_COVARIANT_SECTION,
        substrate=substrate_ref,
        estimation_graph=graph_ref,
        row_identity_sha256=ROW,
        values=_array("order-values", shape=(4, 2)),
        amplitude=_array("order-amplitude"),
        frame_or_tensor=_array("order-frame", shape=(4, 2, 2)),
        eigenspectrum=_array("order-eigenspectrum", shape=(4, 2)),
        support=_array("order-support", dtype="|b1"),
        pointwise_reason_codes=_array("order-reasons", dtype="<i4"),
        claim_ceiling=ClaimLevel.LEVEL_1D,
    )
    inherited_graph = InheritedFieldGraphBinding(
        candidate_graph=graph_ref,
    )
    core_score = CoreScore(
        artifact_id="core-score",
        substrate=substrate_ref,
        order_parameter_spec=order_spec_ref,
        order_parameter_field=order_field_ref,
        field_estimation_graph=graph_ref,
        row_identity_sha256=ROW,
        scalar_definition_id="charge-blind-core-score-v1",
        fit_role=FitRole.CALIBRATION_SELECTION,
        singularity_rule_id="low-amplitude-v1",
        graph_binding=inherited_graph,
        values=_array("core-score-values"),
        uncertainty=_array("core-score-uncertainty"),
        support=_array("core-score-support", dtype="|b1"),
        pointwise_reason_codes=_array("core-score-reasons", dtype="<i4"),
        charge_blind=True,
        claim_ceiling=ClaimLevel.LEVEL_1D,
    )
    core_candidate = CoreCandidate(
        artifact_id="core-candidate",
        substrate=substrate_ref,
        core_score=core_score_ref,
        order_parameter_field=order_field_ref,
        field_estimation_graph=graph_ref,
        row_identity_sha256=ROW,
        localization_algorithm_id="component-minimum-v1",
        singularity_rule_id="low-amplitude-v1",
        graph_binding=inherited_graph,
        localized_support=_array("localized-support", dtype="|b1"),
        uncertainty=_array("localization-uncertainty"),
        charge_blind=True,
        sealed_without_loop_observable_input=True,
        claim_ceiling=ClaimLevel.LEVEL_1D,
    )
    ground_truth_anchor = GroundTruthAnchor(
        artifact_id="ground-truth-anchor",
        substrate=substrate_ref,
        generator_id="synthetic-defect-v1",
        generator_sha256=_digest("synthetic-defect-v1"),
        role=FitRole.CALIBRATION_CONFIRMATION,
        anchor_kind="synthetic-core-support",
        row_identity_sha256=ROW,
        supplied_support=_array("supplied-anchor-support", dtype="|b1"),
        estimator_input_allowed=False,
        localization_gate_eligible=False,
        claim_ceiling=ClaimLevel.LEVEL_0,
    )
    edge_connection = EdgeConnection(
        artifact_id="edge-connection",
        substrate=substrate_ref,
        field=geometry_field_ref,
        field_branch=ScientificBranch.GEOMETRY,
        graph=graph_ref,
        edge_order_sha256=EDGE_ORDER,
        endpoint_identities=_array(
            "edge-endpoints",
            row_identity=EDGE_ORDER,
            shape=(4, 2),
            dtype="<i8",
        ),
        principal_angles=_array(
            "principal-angles",
            row_identity=EDGE_ORDER,
        ),
        procrustes_singular_values=_array(
            "procrustes-singular-values",
            row_identity=EDGE_ORDER,
            shape=(4, 2),
        ),
        coherence=_array("edge-coherence", row_identity=EDGE_ORDER),
        orientation_state="so2",
        transport_convention_id="polar-procrustes-v1",
        claim_ceiling=ClaimLevel.LEVEL_1G,
    )
    geometry_loop = GeometryLoopEstimate(
        artifact_id="geometry-loop",
        substrate=substrate_ref,
        geometric_field=geometry_field_ref,
        edge_connection=edge_ref,
        cycle_graph=graph_ref,
        loop_order_sha256=LOOP_ORDER,
        ordered_support=_array(
            "geometry-loop-support",
            row_identity=LOOP_ORDER,
            shape=(4, 3),
            dtype="<i8",
        ),
        matched_class_or_anchor=_array(
            "geometry-loop-class",
            row_identity=LOOP_ORDER,
            dtype="<i4",
        ),
        sampling_specification=_opaque("geometry-sampling-spec"),
        support_evidence=_array(
            "geometry-loop-evidence",
            row_identity=LOOP_ORDER,
        ),
        continuous_holonomy=_array(
            "continuous-holonomy",
            row_identity=LOOP_ORDER,
        ),
        gate_state=GateState.PASS,
        reason_codes=(),
        claim_ceiling=ClaimLevel.LEVEL_2G,
    )
    defect_loop = DefectLoopEstimate(
        artifact_id="defect-loop",
        substrate=substrate_ref,
        order_parameter_field=order_field_ref,
        hypothesis_id=HypothesisId.F2_LOCAL_COVARIANT_SECTION,
        cycle_graph=graph_ref,
        loop_order_sha256=LOOP_ORDER,
        ordered_support=_array(
            "defect-loop-support",
            row_identity=LOOP_ORDER,
            shape=(4, 3),
            dtype="<i8",
        ),
        matched_class=_array(
            "defect-loop-class",
            row_identity=LOOP_ORDER,
            dtype="<i4",
        ),
        interpolation_evidence=_array(
            "interpolation-evidence",
            row_identity=LOOP_ORDER,
        ),
        lift_or_reference_evidence=_array(
            "lift-evidence",
            row_identity=LOOP_ORDER,
        ),
        boundary_identifiability_evidence=_array(
            "boundary-identifiability",
            row_identity=LOOP_ORDER,
        ),
        branch_and_sampling_evidence=_array(
            "branch-sampling-evidence",
            row_identity=LOOP_ORDER,
        ),
        coordinate_binding=DefectCoordinateBinding(mode="global_frame"),
        localization_binding=DefectLocalizationBinding(
            mode="inferred_core",
            core_candidate=core_candidate_ref,
        ),
        sampled_winding=_array(
            "sampled-winding",
            row_identity=LOOP_ORDER,
            dtype="<i4",
        ),
        integer_output_authorization=selection_ref,
        gate_state=GateState.PASS,
        reason_codes=(),
        claim_ceiling=ClaimLevel.LEVEL_2T,
    )
    decisions = tuple(
        HypothesisDecision(
            hypothesis_id=hypothesis_id,
            disposition=(
                HypothesisDisposition.ADVANCE
                if hypothesis_id
                is HypothesisId.F2_LOCAL_COVARIANT_SECTION
                else HypothesisDisposition.RETAIN_DIAGNOSTIC
            ),
            reason_codes=(
                ("synthetic-selection",)
                if hypothesis_id
                is HypothesisId.F2_LOCAL_COVARIANT_SECTION
                else ("p0-only",)
            ),
        )
        for hypothesis_id in sorted(HypothesisId, key=lambda item: item.value)
    )
    support_ref = _ref(
        ArtifactType.SUPPORT_DIAGNOSTIC,
        "support-diagnostic",
    )
    selection = CalibrationSelectionDecision(
        artifact_id="selection-decision",
        hypothesis_registry=registry_ref,
        hypothesis_decisions=decisions,
        crossed_cell_order_sha256=CALIBRATION_ORDER,
        crossed_cell_manifest=_records("crossed-cell-manifest"),
        selected_artifacts=(support_ref,),
        locked_policy_bundle=_opaque("locked-policy-bundle"),
        selection_inputs=(registry_ref,),
        selection_outputs=(support_ref,),
        source_commit_sha1="a" * 40,
        source_tree_sha256=_digest("source-tree-selection"),
        fixed_choices=_p0_fixed_choices(),
        resolved_choices=_f2_resolved_choices(),
        unresolved_choices=_p0_unresolved_choices(
            HypothesisId.F2_LOCAL_COVARIANT_SECTION
        ),
        integer_output_authorizations=(
            HypothesisId.F2_LOCAL_COVARIANT_SECTION,
        ),
        confirmation_access_commitment=_opaque(
            "confirmation-access-commitment"
        ),
        sealed_before_confirmation_access=True,
        claim_ceiling=ClaimLevel.LEVEL_2T,
    )
    confirmation = CalibrationConfirmationResult(
        artifact_id="confirmation-result",
        selection_decision=selection_ref,
        confirmation_cell_order_sha256=CALIBRATION_ORDER,
        confirmation_cells=_records("confirmation-cells"),
        evidence_artifacts=(support_ref,),
        locked_result=GateState.INSUFFICIENT,
        unresolved_hypotheses=(
            HypothesisId.F2_LOCAL_COVARIANT_SECTION,
        ),
        source_commit_sha1="b" * 40,
        source_tree_sha256=_digest("source-tree-confirmation"),
        claim_ceiling=ClaimLevel.LEVEL_0,
    )
    return {
        "substrate": substrate,
        "graph_spec": graph_spec,
        "candidate_graph": candidate_graph,
        "support": support,
        "geometric_field": geometric_field,
        "order_spec": order_spec,
        "order_field": order_field,
        "core_score": core_score,
        "core_candidate": core_candidate,
        "ground_truth_anchor": ground_truth_anchor,
        "edge_connection": edge_connection,
        "geometry_loop": geometry_loop,
        "defect_loop": defect_loop,
        "selection": selection,
        "confirmation": confirmation,
    }


def test_all_fifteen_artifacts_round_trip_canonically() -> None:
    artifacts = _artifact_set()

    assert len(artifacts) == 15
    for artifact in artifacts.values():
        reconstructed = instrument_artifact_from_dict(artifact.to_dict())
        assert reconstructed == artifact
        assert reconstructed.canonical_bytes == artifact.canonical_bytes
        assert reconstructed.canonical_sha256 == hashlib.sha256(
            artifact.canonical_bytes
        ).hexdigest()
        assert reconstructed.artifact_type is artifact.artifact_type
        assert reconstructed.schema_version == artifact.schema_version
        assert reconstructed.artifact_id == artifact.artifact_id


def test_synthetic_lattice_uses_a_separate_model_free_schema_variant() -> None:
    substrate = _artifact_set()["substrate"]
    assert isinstance(substrate, SubstrateBinding)

    synthetic = SyntheticLatticeSubstrateBinding(
        artifact_id="synthetic-substrate",
        role=FitRole.INSTRUMENT_DEV,
        evolution_axis=EvolutionAxis.SYNTHETIC_LATTICE,
        row_identity_sha256=substrate.row_identity_sha256,
        synthetic_context=_synthetic_context(),
        vertex_identities=substrate.vertex_identities,
        observation_identities=substrate.observation_identities,
        states=substrate.states,
        accounted_response=substrate.accounted_response,
        mask=substrate.mask,
        preprocessing_fit=substrate.preprocessing_fit,
    )
    reconstructed = instrument_artifact_from_dict(synthetic.to_dict())

    assert reconstructed == synthetic
    assert isinstance(reconstructed, SyntheticLatticeSubstrateBinding)
    assert reconstructed.artifact_type is ArtifactType.SUBSTRATE_BINDING
    assert reconstructed.schema_version != substrate.schema_version
    context_document = synthetic.to_dict()["synthetic_context"]
    assert isinstance(context_document, dict)
    assert "model" not in context_document
    assert "tokenizer" not in context_document
    assert "sweep_domain" not in context_document

    with pytest.raises(
        ContractValidationError,
        match="requires SyntheticLatticeSubstrateBinding",
    ):
        replace(
            substrate,
            role=FitRole.INSTRUMENT_DEV,
            evolution_axis=EvolutionAxis.SYNTHETIC_LATTICE,
        )


def test_synthetic_lattice_binding_rejects_contract_drift() -> None:
    substrate = _artifact_set()["substrate"]
    assert isinstance(substrate, SubstrateBinding)
    context = _synthetic_context()
    common = {
        "artifact_id": "synthetic-substrate",
        "role": FitRole.INSTRUMENT_DEV,
        "evolution_axis": EvolutionAxis.SYNTHETIC_LATTICE,
        "row_identity_sha256": substrate.row_identity_sha256,
        "synthetic_context": context,
        "vertex_identities": substrate.vertex_identities,
        "observation_identities": substrate.observation_identities,
        "states": substrate.states,
        "accounted_response": substrate.accounted_response,
        "mask": substrate.mask,
        "preprocessing_fit": substrate.preprocessing_fit,
    }

    with pytest.raises(
        ContractValidationError,
        match="role=instrument_dev",
    ):
        SyntheticLatticeSubstrateBinding(
            **{**common, "role": FitRole.CALIBRATION_SELECTION}
        )
    with pytest.raises(
        ContractValidationError,
        match="evolution_axis=synthetic_lattice",
    ):
        SyntheticLatticeSubstrateBinding(
            **{**common, "evolution_axis": EvolutionAxis.LAYER_INDEX}
        )
    with pytest.raises(
        ContractValidationError,
        match="bind the substrate row identity",
    ):
        SyntheticLatticeSubstrateBinding(
            **{
                **common,
                "synthetic_context": _synthetic_context(
                    row_identity=_digest("different-rows")
                ),
            }
        )
    with pytest.raises(
        ContractValidationError,
        match="site count",
    ):
        SyntheticLatticeSubstrateBinding(
            **{
                **common,
                "synthetic_context": _synthetic_context(
                    lattice_shape=(2, 3)
                ),
            }
        )
    with pytest.raises(
        ContractValidationError,
        match="cannot be claim eligible",
    ):
        replace(context, claim_eligible=True)

    context_document = context.to_dict()
    context_document["model"] = {"id": "forbidden"}
    with pytest.raises(ContractValidationError, match="unknown"):
        SyntheticLatticeContextBinding.from_dict(context_document)


def test_instrument_dev_graph_execution_is_explicit_and_all_or_none() -> None:
    graph = _artifact_set()["graph_spec"]
    assert isinstance(graph, GraphConstructionSpec)

    executed = replace(
        graph,
        allowed_role=FitRole.INSTRUMENT_DEV,
        family=RuleChoice(
            family_id="graph_family",
            resolution=ResolutionState.INSTRUMENT_DEV_EXECUTED,
            selected_id="mutual-knn",
        ),
        metric=RuleChoice(
            family_id="graph_metric",
            resolution=ResolutionState.INSTRUMENT_DEV_EXECUTED,
            selected_id="euclidean",
        ),
        scale=RuleChoice(
            family_id="graph_scale",
            resolution=ResolutionState.INSTRUMENT_DEV_EXECUTED,
            selected_id="k-4",
        ),
    )
    assert GraphConstructionSpec.from_dict(executed.to_dict()) == executed

    for relabelled in (
        ResolutionState.FIXED_BY_HYPOTHESIS,
        ResolutionState.CALIBRATION_RESOLVED,
    ):
        with pytest.raises(
            ContractValidationError,
            match="instrument_dev graphs must record",
        ):
            replace(
                executed,
                family=RuleChoice(
                    family_id="graph_family",
                    resolution=relabelled,
                    selected_id="mutual-knn",
                ),
                metric=RuleChoice(
                    family_id="graph_metric",
                    resolution=relabelled,
                    selected_id="euclidean",
                ),
                scale=RuleChoice(
                    family_id="graph_scale",
                    resolution=relabelled,
                    selected_id="k-4",
                ),
            )

    with pytest.raises(
        ContractValidationError,
        match="must cover family, metric, and scale",
    ):
        replace(
            graph,
            family=executed.family,
        )

    with pytest.raises(
        ContractValidationError,
        match="instrument_dev graph",
    ):
        replace(
            executed,
            allowed_role=FitRole.CALIBRATION_SELECTION,
        )

    order_spec = _artifact_set()["order_spec"]
    assert isinstance(order_spec, OrderParameterSpec)
    with pytest.raises(
        ContractValidationError,
        match="reserved for GraphConstructionSpec",
    ):
        replace(
            order_spec,
            charge_group=RuleChoice(
                family_id="charge_group",
                resolution=ResolutionState.INSTRUMENT_DEV_EXECUTED,
                selected_id="u1",
            ),
        )


def test_loader_checks_both_hashes_without_dereferencing_payloads(
    tmp_path,
) -> None:
    artifact = _artifact_set()["order_field"]
    path = tmp_path / "order-field.json"
    path.write_bytes(artifact.canonical_bytes)
    source_sha256 = hashlib.sha256(artifact.canonical_bytes).hexdigest()

    loaded = load_instrument_artifact(
        path,
        expected_source_sha256=source_sha256,
        expected_canonical_sha256=artifact.canonical_sha256,
    )

    assert loaded.artifact == artifact
    assert loaded.source_path == path.resolve()
    assert loaded.source_sha256 == source_sha256
    assert loaded.canonical_sha256 == artifact.canonical_sha256


def test_loader_rejects_noncanonical_duplicate_and_oversized_sources(
    tmp_path,
) -> None:
    artifact = _artifact_set()["support"]
    noncanonical = tmp_path / "trailing-newline.json"
    noncanonical.write_bytes(artifact.canonical_bytes + b"\n")
    with pytest.raises(InstrumentArtifactSchemaError):
        load_instrument_artifact(noncanonical)

    duplicate = tmp_path / "duplicate.json"
    duplicate.write_bytes(b'{"artifact_type":"x","artifact_type":"x"}')
    with pytest.raises(InstrumentArtifactSchemaError):
        load_instrument_artifact(duplicate)

    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b"x" * (MAX_INSTRUMENT_ARTIFACT_BYTES + 1))
    with pytest.raises(InstrumentArtifactSchemaError):
        load_instrument_artifact(oversized)


def test_loader_rejects_source_and_canonical_hash_mismatches(tmp_path) -> None:
    artifact = _artifact_set()["support"]
    path = tmp_path / "support.json"
    path.write_bytes(artifact.canonical_bytes)

    with pytest.raises(InstrumentArtifactIntegrityError):
        load_instrument_artifact(
            path,
            expected_source_sha256="0" * 64,
        )
    with pytest.raises(InstrumentArtifactIntegrityError):
        load_instrument_artifact(
            path,
            expected_canonical_sha256="0" * 64,
        )


def test_exact_schema_and_support_core_separation() -> None:
    artifacts = _artifact_set()
    support = artifacts["support"].to_dict()
    support["order_parameter_field"] = _ref(
        ArtifactType.ORDER_PARAMETER_FIELD,
        "order-field",
    ).to_dict()
    with pytest.raises(ContractValidationError):
        SupportDiagnostic.from_dict(support)

    wrong_neighborhood = artifacts["support"].to_dict()
    wrong_neighborhood["neighborhood_specification"] = _ref(
        ArtifactType.CORE_SCORE,
        "core-score",
    ).to_dict()
    with pytest.raises(ContractValidationError):
        SupportDiagnostic.from_dict(wrong_neighborhood)

    with pytest.raises(ContractValidationError):
        replace(artifacts["core_score"], charge_blind=False)


def test_graph_mode_union_and_inherited_graph_identity_are_exact() -> None:
    artifacts = _artifact_set()
    with pytest.raises(ContractValidationError):
        core_graph_binding_from_dict(
            {
                "mode": "graph_free",
                "candidate_graph": _ref(
                    ArtifactType.CANDIDATE_GRAPH,
                    "field-graph",
                ).to_dict(),
            }
        )

    with pytest.raises(ContractValidationError):
        replace(
            artifacts["core_score"],
            graph_binding=InheritedFieldGraphBinding(
                _ref(ArtifactType.CANDIDATE_GRAPH, "different-graph")
            ),
        )


def test_ground_truth_anchor_and_core_candidate_cannot_be_swapped() -> None:
    artifacts = _artifact_set()
    with pytest.raises(ContractValidationError):
        replace(
            artifacts["ground_truth_anchor"],
            role=FitRole.SUBJECT_DISCOVERY,
        )

    candidate = artifacts["core_candidate"].to_dict()
    candidate["core_score"] = _ref(
        ArtifactType.GROUND_TRUTH_ANCHOR,
        "ground-truth-anchor",
    ).to_dict()
    with pytest.raises(ContractValidationError):
        CoreCandidate.from_dict(candidate)


def test_geometry_and_defect_branches_cannot_cross() -> None:
    artifacts = _artifact_set()
    geometry = artifacts["geometry_loop"].to_dict()
    geometry["order_parameter_field"] = _ref(
        ArtifactType.ORDER_PARAMETER_FIELD,
        "order-field",
    ).to_dict()
    with pytest.raises(ContractValidationError):
        GeometryLoopEstimate.from_dict(geometry)

    defect = artifacts["defect_loop"].to_dict()
    defect["coordinate_binding"] = {"mode": "local_frames"}
    with pytest.raises(ContractValidationError):
        DefectLoopEstimate.from_dict(defect)

    with pytest.raises(ContractValidationError):
        replace(
            artifacts["defect_loop"],
            localization_binding=DefectLocalizationBinding(
                mode="supplied_anchor",
                ground_truth_anchor=_ref(
                    ArtifactType.GROUND_TRUTH_ANCHOR,
                    "ground-truth-anchor",
                ),
            ),
        )


def test_f3_ceiling_cannot_be_laundered_through_defect_artifacts() -> None:
    artifacts = _artifact_set()

    with pytest.raises(ContractValidationError, match="exceeds"):
        replace(
            artifacts["order_spec"],
            hypothesis_id=HypothesisId.F3_GLOBAL_PLANE_SECTION,
            claim_ceiling=ClaimLevel.LEVEL_2T,
        )
    with pytest.raises(ContractValidationError, match="exceeds"):
        replace(
            artifacts["order_field"],
            hypothesis_id=HypothesisId.F3_GLOBAL_PLANE_SECTION,
            claim_ceiling=ClaimLevel.LEVEL_2T,
        )
    with pytest.raises(ContractValidationError, match="exceeds"):
        replace(
            artifacts["defect_loop"],
            hypothesis_id=HypothesisId.F3_GLOBAL_PLANE_SECTION,
            claim_ceiling=ClaimLevel.LEVEL_2T,
        )


def test_level_2t_requires_typed_selection_authorization() -> None:
    artifacts = _artifact_set()
    defect_loop = artifacts["defect_loop"]

    with pytest.raises(ContractValidationError, match="authorization"):
        replace(
            defect_loop,
            integer_output_authorization=None,
        )
    with pytest.raises(ContractValidationError):
        replace(
            defect_loop,
            integer_output_authorization=_ref(
                ArtifactType.SUPPORT_DIAGNOSTIC,
                "not-an-authorization",
            ),
        )

    all_retained = tuple(
        replace(
            decision,
            disposition=HypothesisDisposition.RETAIN_DIAGNOSTIC,
        )
        for decision in artifacts["selection"].hypothesis_decisions
    )
    with pytest.raises(ContractValidationError, match="advanced"):
        replace(
            artifacts["selection"],
            hypothesis_decisions=all_retained,
        )
    with pytest.raises(ContractValidationError, match="declared together"):
        replace(
            artifacts["selection"],
            integer_output_authorizations=(),
        )
    with pytest.raises(ContractValidationError, match="missing choice receipts"):
        replace(
            artifacts["selection"],
            resolved_choices=artifacts["selection"].resolved_choices[:-1],
        )
    with pytest.raises(ContractValidationError, match="candidate set"):
        replace(
            artifacts["selection"],
            resolved_choices=tuple(
                replace(
                    choice,
                    choice=_resolved(
                        "interpolation_rule",
                        "outcome-invented-rule",
                    ),
                )
                if choice.choice.family_id == "interpolation_rule"
                else choice
                for choice in artifacts["selection"].resolved_choices
            ),
        )
    with pytest.raises(ContractValidationError, match="unexpected resolved"):
        replace(
            artifacts["selection"],
            resolved_choices=tuple(
                sorted(
                    (
                        *artifacts["selection"].resolved_choices,
                        HypothesisResolvedChoice(
                            hypothesis_id=(
                                HypothesisId.F2_LOCAL_COVARIANT_SECTION
                            ),
                            choice=_resolved(
                                "outcome_invented_family",
                                "outcome-invented-rule",
                            ),
                        ),
                    ),
                    key=lambda value: (
                        value.hypothesis_id.value,
                        value.choice.family_id,
                    ),
                )
            ),
        )


def test_f4_authorization_preserves_fixed_lift_provenance_and_all_choices() -> None:
    selection = _artifact_set()["selection"]
    decisions = tuple(
        replace(
            decision,
            disposition=(
                HypothesisDisposition.ADVANCE
                if decision.hypothesis_id
                is HypothesisId.F4_SPIN_TWO_ANISOTROPY
                else HypothesisDisposition.RETAIN_DIAGNOSTIC
            ),
        )
        for decision in selection.hypothesis_decisions
    )
    fixed_lift = next(
        value
        for value in selection.fixed_choices
        if value.hypothesis_id
        is HypothesisId.F4_SPIN_TWO_ANISOTROPY
    )
    valid = replace(
        selection,
        hypothesis_decisions=decisions,
        resolved_choices=_f4_resolved_choices(),
        unresolved_choices=_p0_unresolved_choices(
            HypothesisId.F4_SPIN_TWO_ANISOTROPY
        ),
        integer_output_authorizations=(
            HypothesisId.F4_SPIN_TWO_ANISOTROPY,
        ),
    )
    assert fixed_lift in valid.fixed_choices

    with pytest.raises(
        ContractValidationError,
        match="hypothesis-fixed",
    ):
        replace(
            valid,
            fixed_choices=tuple(
                value
                for value in valid.fixed_choices
                if value is not fixed_lift
            ),
        )
    with pytest.raises(
        ContractValidationError,
        match="unexpected hypothesis-fixed",
    ):
        replace(
            valid,
            fixed_choices=tuple(
                sorted(
                    (
                        *valid.fixed_choices,
                        HypothesisFixedChoice(
                            hypothesis_id=(
                                HypothesisId.F4_SPIN_TWO_ANISOTROPY
                            ),
                            choice=_fixed(
                                "outcome_invented_family",
                                "outcome-invented-rule",
                            ),
                        ),
                    ),
                    key=lambda value: (
                        value.hypothesis_id.value,
                        value.choice.family_id,
                    ),
                )
            ),
        )
    with pytest.raises(ContractValidationError, match="missing choice receipts"):
        replace(
            valid,
            resolved_choices=tuple(
                value
                for value in valid.resolved_choices
                if value.choice.family_id != "input_tensor"
            ),
        )


def test_confirmation_schema_has_no_policy_override_field() -> None:
    confirmation = _artifact_set()["confirmation"].to_dict()
    confirmation["policy_override_applied"] = False

    with pytest.raises(ContractValidationError):
        CalibrationConfirmationResult.from_dict(confirmation)

    confirmation = _artifact_set()["confirmation"].to_dict()
    confirmation["unresolved_hypotheses"] = ["banana"]
    with pytest.raises(ContractValidationError, match="must be one of"):
        CalibrationConfirmationResult.from_dict(confirmation)

    with pytest.raises(ContractValidationError):
        replace(
            _artifact_set()["confirmation"],
            evidence_artifacts=(
                _ref(
                    ArtifactType.CALIBRATION_SELECTION_DECISION,
                    "conflicting-selection",
                ),
            ),
        )


def test_named_rule_fields_reject_family_reclassification() -> None:
    artifacts = _artifact_set()

    with pytest.raises(ContractValidationError, match="family_id"):
        replace(
            artifacts["order_spec"],
            reference_rule=_fixed(
                "interpolation_rule",
                "misclassified-reference",
            ),
        )
    with pytest.raises(ContractValidationError, match="family_id"):
        replace(
            artifacts["graph_spec"],
            family=_fixed("wrong_family", "mutual-knn"),
        )


def test_unresolved_choices_are_hypothesis_scoped_and_not_fixed() -> None:
    selection = _artifact_set()["selection"]

    with pytest.raises(ContractValidationError, match="calibration_resolved"):
        HypothesisResolvedChoice(
            hypothesis_id=HypothesisId.F2_LOCAL_COVARIANT_SECTION,
            choice=_fixed("interpolation_rule", "fixed-too-early"),
        )
    with pytest.raises(
        ContractValidationError,
        match="must remain calibration_selection",
    ):
        replace(
            selection,
            unresolved_choices=(
                HypothesisRuleChoice(
                    hypothesis_id=(
                        HypothesisId.F2_LOCAL_COVARIANT_SECTION
                    ),
                    choice=_fixed(
                        "interpolation_rule",
                        "outcome_selected_rule",
                    ),
                ),
            ),
        )

    keys = {
        (value.hypothesis_id, value.choice.family_id)
        for value in selection.unresolved_choices
    }
    assert (
        HypothesisId.F3_GLOBAL_PLANE_SECTION,
        "estimator",
    ) in keys
    assert (
        HypothesisId.F4_SPIN_TWO_ANISOTROPY,
        "estimator",
    ) in keys

    with pytest.raises(ContractValidationError, match="candidate set"):
        replace(
            selection,
            unresolved_choices=tuple(
                replace(
                    value,
                    choice=RuleChoice(
                        family_id="estimator",
                        resolution=ResolutionState.CALIBRATION_SELECTION,
                        candidate_ids=("invented-a", "invented-b"),
                    ),
                )
                if (
                    value.hypothesis_id
                    is HypothesisId.F3_GLOBAL_PLANE_SECTION
                    and value.choice.family_id == "estimator"
                )
                else value
                for value in selection.unresolved_choices
            ),
        )

    with pytest.raises(
        ContractValidationError,
        match="more than once",
    ):
        duplicate = HypothesisRuleChoice(
            hypothesis_id=HypothesisId.F2_LOCAL_COVARIANT_SECTION,
            choice=RuleChoice(
                family_id="interpolation_rule",
                resolution=ResolutionState.CALIBRATION_SELECTION,
                candidate_ids=tuple(
                    sorted(
                        _P0_CALIBRATION_SELECTIONS_BY_HYPOTHESIS[
                            HypothesisId.F2_LOCAL_COVARIANT_SECTION
                        ]["interpolation_rule"]
                    )
                ),
            ),
        )
        replace(
            selection,
            unresolved_choices=tuple(
                sorted(
                    (*selection.unresolved_choices, duplicate),
                    key=lambda value: (
                        value.hypothesis_id.value,
                        value.choice.family_id,
                    ),
                )
            ),
        )


def test_selection_choice_receipts_close_every_p0_hypothesis() -> None:
    selection = _artifact_set()["selection"]

    with pytest.raises(
        ContractValidationError,
        match="f0_support is missing choice receipts",
    ):
        replace(
            selection,
            unresolved_choices=tuple(
                value
                for value in selection.unresolved_choices
                if not (
                    value.hypothesis_id is HypothesisId.F0_SUPPORT
                    and value.choice.family_id == "input_tensor"
                )
            ),
        )

    invented = HypothesisResolvedChoice(
        hypothesis_id=HypothesisId.F1_PROJECTOR_CONNECTION,
        choice=_resolved("invented_family", "invented-choice"),
    )
    with pytest.raises(
        ContractValidationError,
        match="f1_projector_connection has unexpected resolved",
    ):
        replace(
            selection,
            resolved_choices=tuple(
                sorted(
                    (*selection.resolved_choices, invented),
                    key=lambda value: (
                        value.hypothesis_id.value,
                        value.choice.family_id,
                    ),
                )
            ),
        )

    f3_lift = next(
        value
        for value in selection.fixed_choices
        if value.hypothesis_id
        is HypothesisId.F3_GLOBAL_PLANE_SECTION
        and value.choice.family_id == "lift_rule"
    )
    with pytest.raises(
        ContractValidationError,
        match="f3_global_plane_section is missing hypothesis-fixed",
    ):
        replace(
            selection,
            fixed_choices=tuple(
                value
                for value in selection.fixed_choices
                if value is not f3_lift
            ),
        )


def test_advanced_hypothesis_cannot_retain_unresolved_choices() -> None:
    selection = _artifact_set()["selection"]
    f1_advanced = tuple(
        replace(
            decision,
            disposition=(
                HypothesisDisposition.ADVANCE
                if decision.hypothesis_id
                is HypothesisId.F1_PROJECTOR_CONNECTION
                else HypothesisDisposition.RETAIN_DIAGNOSTIC
            ),
        )
        for decision in selection.hypothesis_decisions
    )

    with pytest.raises(
        ContractValidationError,
        match="f1_projector_connection cannot advance with unresolved",
    ):
        replace(
            selection,
            hypothesis_decisions=f1_advanced,
            resolved_choices=(),
            unresolved_choices=_p0_unresolved_choices(),
            integer_output_authorizations=(),
            claim_ceiling=ClaimLevel.LEVEL_2G,
        )


def test_selection_claim_ceiling_requires_a_supporting_advanced_path() -> None:
    selection = _artifact_set()["selection"]
    f0_advanced = tuple(
        replace(
            decision,
            disposition=(
                HypothesisDisposition.ADVANCE
                if decision.hypothesis_id is HypothesisId.F0_SUPPORT
                else HypothesisDisposition.RETAIN_DIAGNOSTIC
            ),
        )
        for decision in selection.hypothesis_decisions
    )
    valid = replace(
        selection,
        hypothesis_decisions=f0_advanced,
        resolved_choices=_first_p0_resolved_choices(
            HypothesisId.F0_SUPPORT
        ),
        unresolved_choices=_p0_unresolved_choices(
            HypothesisId.F0_SUPPORT
        ),
        integer_output_authorizations=(),
        claim_ceiling=ClaimLevel.LEVEL_1G,
    )
    assert valid.claim_ceiling is ClaimLevel.LEVEL_1G

    with pytest.raises(
        ContractValidationError,
        match="do not support selection claim ceiling",
    ):
        replace(valid, claim_ceiling=ClaimLevel.LEVEL_2G)


@pytest.mark.parametrize(
    ("artifact_name", "field_name"),
    [
        ("candidate_graph", "vertices"),
        ("candidate_graph", "canonical_edges"),
        ("candidate_graph", "cycle_support"),
        ("edge_connection", "coherence"),
        ("geometry_loop", "continuous_holonomy"),
        ("defect_loop", "sampled_winding"),
    ],
)
def test_order_digest_mismatches_are_rejected(
    artifact_name: str,
    field_name: str,
) -> None:
    artifact = _artifact_set()[artifact_name]
    document = artifact.to_dict()
    document[field_name]["row_identity_sha256"] = _digest("wrong-order")

    with pytest.raises(ContractValidationError):
        type(artifact).from_dict(document)


def test_substrate_requires_distinct_identity_payload_fields() -> None:
    substrate = _artifact_set()["substrate"].to_dict()
    del substrate["observation_identities"]

    with pytest.raises(ContractValidationError):
        SubstrateBinding.from_dict(substrate)

    substrate = _artifact_set()["substrate"].to_dict()
    substrate["observation_identities"]["row_identity_sha256"] = _digest(
        "wrong-observation-order"
    )
    with pytest.raises(ContractValidationError):
        SubstrateBinding.from_dict(substrate)


def test_structured_payload_roles_reject_opaque_and_row_count_drift() -> None:
    artifacts = _artifact_set()

    with pytest.raises(ContractValidationError, match="payload kind"):
        replace(
            artifacts["ground_truth_anchor"],
            supplied_support=_opaque("opaque-anchor"),
        )
    with pytest.raises(ContractValidationError, match="payload kind"):
        replace(
            artifacts["selection"],
            crossed_cell_manifest=_opaque("opaque-selection-cells"),
        )
    with pytest.raises(ContractValidationError, match="payload kind"):
        replace(
            artifacts["confirmation"],
            confirmation_cells=_opaque("opaque-confirmation-cells"),
        )
    with pytest.raises(ContractValidationError, match="shared row count"):
        replace(
            artifacts["order_field"],
            amplitude=_array("wrong-count-amplitude", shape=(7,)),
        )


def test_typed_references_and_content_bound_metadata_are_enforced() -> None:
    artifacts = _artifact_set()
    substrate = artifacts["substrate"].to_dict()
    substrate["context_bank"] = _ref(
        ArtifactType.CANDIDATE_GRAPH,
        "field-graph",
    ).to_dict()
    with pytest.raises(ContractValidationError):
        SubstrateBinding.from_dict(substrate)

    geometry = artifacts["geometric_field"].to_dict()
    geometry["fit_receipt"] = _ref(
        ArtifactType.CANDIDATE_GRAPH,
        "field-graph",
    ).to_dict()
    with pytest.raises(ContractValidationError):
        GeometricFieldEstimate.from_dict(geometry)

    selection = artifacts["selection"].to_dict()
    selection["hypothesis_registry"] = _ref(
        ArtifactType.CONTEXT_BANK,
        "context-bank-p0",
    ).to_dict()
    with pytest.raises(ContractValidationError):
        CalibrationSelectionDecision.from_dict(selection)
