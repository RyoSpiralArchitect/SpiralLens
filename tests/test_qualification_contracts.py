from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from spirallens.graphs import GraphFamily, GraphPurpose
from spirallens.qualification.aggregation import (
    build_d2_gate,
    build_d4_gate,
    build_d5_gate,
    collapse_core_primary_units,
    collapse_primary_units,
    materialize_expected_cells,
    materialize_expected_core_cells,
    summarize_strata,
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
    STATIC_REQUIRED_EVIDENCE_IDS,
    CoreCellSummary,
    CorePrimaryUnitSummary,
    CrossedCellSummary,
    CrossedNonvacuitySummary,
    GateEvidenceSummary,
    GateResult,
    PrimaryUnitSummary,
    QualificationGateId,
    QualificationResult,
    StaticEvidenceReceipt,
    build_qualification_lane_event_payloads,
    derive_static_gate,
    qualification_result_evidence_root_sha256,
)
from spirallens.qualification.crossed import (
    CrossedNonvacuityReceipt,
    FieldComponentEffectReceipt,
    FieldGraphPairEffectReceipt,
)
from spirallens.qualification.evidence_bundle import (
    D2CoreConfounderMatrixReceipt,
    QualificationEvidenceBundle,
)
from spirallens.qualification.freeze import (
    SelectionAttemptClaimArtifact,
    SelectionFreezeArtifact,
    SelectionLaunchIntentBinding,
)
from spirallens.qualification.persistence import (
    LoadedQualificationProtocol,
    load_qualification_protocol,
    load_qualification_result,
    write_qualification_protocol,
    write_qualification_result,
)
from spirallens.qualification.preparation import CLOSED_D0_D5_PROTOCOL_ID
from spirallens.qualification.prerequisites import CorePrerequisitePolicy
from spirallens.qualification.protocol import (
    CLOSED_CARTESIAN_ESTIMATOR_ID,
    CLOSED_CARTESIAN_GENERATOR_FAMILY_ID,
    CLOSED_CARTESIAN_TRIVIALIZATION_ID,
    CLOSED_CORE_LOCALIZER_ID,
    CLOSED_REPRESENTATION_ESTIMATOR_ID,
    CLOSED_REPRESENTATION_TRIVIALIZATION_ID,
    F2_LOCAL_COVARIANT_SECTION_REFERENT_ID,
    AuthorityBoundary,
    BoundaryTemplate,
    CartesianSelectionSubstrate,
    ClosedImplementationRegistry,
    ControlDeclaration,
    CoveragePolicy,
    DomainDeclaration,
    EngineBinding,
    ExpectedCell,
    ExpectedCoreCell,
    ExpectedStratum,
    GeneratorCaseBinding,
    GraphAxes,
    GraphDeclaration,
    InstrumentSelection,
    LoopRole,
    ModuleDigest,
    NumericStressLevel,
    QualificationProtocol,
    RegistryBinding,
    SelectionDesign,
    StressAssignment,
    StressAxis,
    Thresholds,
    required_stress_stratum_id,
)
from spirallens.qualification.source_binding import (
    QualificationEventLedger,
    QualificationSourceBindingSummary,
    qualification_event_lane_ids,
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


def _graph(
    graph_id: str,
    family: GraphFamily,
    purpose: GraphPurpose,
) -> GraphDeclaration:
    if family is GraphFamily.MUTUAL_KNN:
        parameters: tuple[tuple[str, int | float], ...] = (("neighbor_count", 4),)
    elif family is GraphFamily.FIXED_RADIUS:
        parameters = (("radius", 0.42),)
    else:
        parameters = (
            ("minimum_shared_neighbors", 1),
            ("neighbor_count", 4),
        )
    return GraphDeclaration(
        graph_id=graph_id,
        family=family,
        purpose=purpose,
        parameters=parameters,
    )


def _instrument() -> InstrumentSelection:
    return InstrumentSelection(
        referent_id=F2_LOCAL_COVARIANT_SECTION_REFERENT_ID,
        estimator_id=CLOSED_REPRESENTATION_ESTIMATOR_ID,
        trivialization_id=CLOSED_REPRESENTATION_TRIVIALIZATION_ID,
        core_localizer_id=CLOSED_CORE_LOCALIZER_ID,
    )


def _implementation_registry() -> ClosedImplementationRegistry:
    return ClosedImplementationRegistry(
        generator_family_id=CLOSED_CARTESIAN_GENERATOR_FAMILY_ID,
        generator_cases=(
            GeneratorCaseBinding(
                "cartesian-fourier-fixed-null",
                CoreDisposition.LOCALIZED_CORE,
                LoopDisposition.NULL,
            ),
            GeneratorCaseBinding(
                "cartesian-fourier-no-core-null",
                CoreDisposition.NO_CORE,
                LoopDisposition.NULL,
            ),
            GeneratorCaseBinding(
                "cartesian-fourier-positive",
                CoreDisposition.LOCALIZED_CORE,
                LoopDisposition.NONZERO,
            ),
            GeneratorCaseBinding(
                "cartesian-fourier-prerequisite-failure",
                CoreDisposition.PREREQUISITE_FAILURE,
                LoopDisposition.PREREQUISITE_FAILURE,
            ),
        ),
        surrogate_estimator_id=CLOSED_CARTESIAN_ESTIMATOR_ID,
        surrogate_trivialization_id=CLOSED_CARTESIAN_TRIVIALIZATION_ID,
        instrument=_instrument(),
    )


def _protocol() -> QualificationProtocol:
    a_graphs = (
        _graph("a-mutual", GraphFamily.MUTUAL_KNN, GraphPurpose.FIELD_ESTIMATION),
        _graph("a-radius", GraphFamily.FIXED_RADIUS, GraphPurpose.FIELD_ESTIMATION),
        _graph("a-shared", GraphFamily.SHARED_NEIGHBOR, GraphPurpose.FIELD_ESTIMATION),
    )
    b_graphs = (
        _graph("b-mutual", GraphFamily.MUTUAL_KNN, GraphPurpose.CYCLE_CONSTRUCTION),
        _graph("b-radius", GraphFamily.FIXED_RADIUS, GraphPurpose.CYCLE_CONSTRUCTION),
        _graph(
            "b-shared", GraphFamily.SHARED_NEIGHBOR, GraphPurpose.CYCLE_CONSTRUCTION
        ),
    )
    controls = (
        ControlDeclaration(
            control_id="fixed-null-core",
            generator_case_id="cartesian-fourier-fixed-null",
            core_disposition=CoreDisposition.LOCALIZED_CORE,
            loop_disposition=LoopDisposition.NULL,
        ),
        ControlDeclaration(
            control_id="nonzero-core",
            generator_case_id="cartesian-fourier-positive",
            core_disposition=CoreDisposition.LOCALIZED_CORE,
            loop_disposition=LoopDisposition.NONZERO,
            field_sensitivity_sentinel=True,
        ),
        ControlDeclaration(
            control_id="null-no-core",
            generator_case_id="cartesian-fourier-no-core-null",
            core_disposition=CoreDisposition.NO_CORE,
            loop_disposition=LoopDisposition.NULL,
        ),
        ControlDeclaration(
            control_id="prerequisite",
            generator_case_id="cartesian-fourier-prerequisite-failure",
            core_disposition=CoreDisposition.PREREQUISITE_FAILURE,
            loop_disposition=LoopDisposition.PREREQUISITE_FAILURE,
        ),
    )
    assignments = (
        StressAssignment("boundary", "central"),
        StressAssignment("state-geometry-warp", "nominal"),
        StressAssignment("structured-observation-perturbation", "nominal"),
    )
    stress_strata = tuple(
        sorted(
            required_stress_stratum_id(item.axis_id, item.level) for item in assignments
        )
    )
    core_cells: list[ExpectedCoreCell] = []
    loop_cells: list[ExpectedCell] = []
    primary_ids: list[str] = []
    for control in controls:
        primary_id = f"unit-{control.control_id}"
        primary_ids.append(primary_id)
        for a_graph in a_graphs:
            core_cells.append(
                ExpectedCoreCell(
                    core_cell_id=(f"core-{control.control_id}-{a_graph.graph_id}"),
                    primary_unit_id=primary_id,
                    selection_seed=101,
                    control_id=control.control_id,
                    stress_assignments=assignments,
                    field_graph_id=a_graph.graph_id,
                    expected_core_disposition=control.core_disposition,
                )
            )
            for b_graph in b_graphs:
                for role in LoopRole:
                    disposition = (
                        control.loop_disposition
                        if role is LoopRole.PRIMARY_BOUNDARY
                        else (
                            LoopDisposition.PREREQUISITE_FAILURE
                            if control.loop_disposition
                            is LoopDisposition.PREREQUISITE_FAILURE
                            else LoopDisposition.NULL
                        )
                    )
                    loop_cells.append(
                        ExpectedCell(
                            cell_id=(
                                f"loop-{control.control_id}-{a_graph.graph_id}-"
                                f"{b_graph.graph_id}-{role.value}"
                            ),
                            primary_unit_id=primary_id,
                            selection_seed=101,
                            control_id=control.control_id,
                            stress_assignments=assignments,
                            field_graph_id=a_graph.graph_id,
                            cycle_graph_id=b_graph.graph_id,
                            loop_role=role,
                            expected_loop_disposition=disposition,
                            stratum_ids=stress_strata,
                        )
                    )
    return QualificationProtocol(
        protocol_id="d0-d5-selection-v0-2",
        engine=EngineBinding(
            repository="RyoSpiralArchitect/SpiralLens",
            commit="1" * 40,
            modules=(
                ModuleDigest(
                    "spirallens.qualification.aggregation",
                    _digest("aggregation"),
                ),
                ModuleDigest(
                    "spirallens.qualification.contracts",
                    _digest("contracts"),
                ),
            ),
        ),
        registry=RegistryBinding(
            registry_source_sha256=_digest("registry-source"),
            registry_canonical_sha256=_digest("registry-canonical"),
            referent_canonical_sha256=_digest("referent-canonical"),
        ),
        instrument=_instrument(),
        implementation_registry=_implementation_registry(),
        graphs=GraphAxes(
            field_estimation=a_graphs,
            cycle_construction=b_graphs,
        ),
        domain=DomainDeclaration(
            domain_id="cartesian-grid-v0-1",
            domain_construction_sha256=_digest("domain-construction"),
            support_id="rectangular-face-support-v0-1",
            support_construction_sha256=_digest("support-construction"),
            boundary_class_id="same-induced-boundary-v0-1",
            refinement_rule_id="forward-span-four-v0-1",
            max_domain_edges_per_graph_edge=4,
        ),
        cartesian=CartesianSelectionSubstrate(
            generator_family_id=CLOSED_CARTESIAN_GENERATOR_FAMILY_ID,
            grid_side=7,
            ambient_dimension=12,
            samples_per_split=8,
            baseline=1.0,
            second_harmonic_scale=0.2,
            structured_observation_perturbation_axis_id=(
                "structured-observation-perturbation"
            ),
            structured_observation_perturbation_levels=(
                NumericStressLevel("nominal", 0.0),
            ),
            state_geometry_warp_axis_id="state-geometry-warp",
            state_geometry_warp_levels=(NumericStressLevel("nominal", 0.0),),
            boundary_axis_id="boundary",
            primary_boundaries=(BoundaryTemplate("central", 2, 2, 4, 4),),
            offcore_boundary=BoundaryTemplate("offcore", 0, 0, 1, 1),
        ),
        selection=SelectionDesign(
            seeds=(101,),
            controls=controls,
            stress_axes=(
                StressAxis("boundary", ("central",)),
                StressAxis("state-geometry-warp", ("nominal",)),
                StressAxis(
                    "structured-observation-perturbation",
                    ("nominal",),
                ),
            ),
        ),
        thresholds=Thresholds(
            d1_numeric_tolerance=1e-10,
            d1_cartesian_direction_cosine_floor=0.99,
            d1_representation_phase_coherence_floor=0.99,
            core_amplitude_ceiling=1e-8,
            identifiability_floor=1e-8,
            coherence_floor=0.8,
            minimum_support_count=2,
            max_localized_core_fraction=0.05,
            minimum_core_contrast_ratio=2.0,
            branch_margin_rad=1e-6,
            loop_nonzero_floor_cycles=0.5,
            loop_oracle_tolerance_cycles=1e-6,
            graph_total_tolerance_cycles=1e-6,
            core_candidate_difference_tolerance_rows=0,
            minimum_representative_content_variants=2,
            minimum_field_output_effect_size=1e-6,
        ),
        coverage_policy=CoveragePolicy(
            evaluation_unit=EvaluationUnit.PHANTOM_INSTANCE,
            minimum_coverage=1.0,
            maximum_abstention_fraction=0.0,
            minimum_recall=1.0,
            minimum_specificity=1.0,
        ),
        expected_core_cells=tuple(
            sorted(core_cells, key=lambda item: item.core_cell_id)
        ),
        expected_cells=tuple(sorted(loop_cells, key=lambda item: item.cell_id)),
        expected_strata=tuple(
            ExpectedStratum(
                stratum_id=stratum_id,
                evaluation_unit=EvaluationUnit.PHANTOM_INSTANCE,
                required=True,
                primary_unit_ids=tuple(sorted(primary_ids)),
            )
            for stratum_id in stress_strata
        ),
        authority=AuthorityBoundary(),
    )


def _static_evidence(
    *,
    status: AttemptStatus,
) -> tuple[GateEvidenceSummary, ...]:
    values: list[GateEvidenceSummary] = []
    for gate_id in (
        QualificationGateId.D0,
        QualificationGateId.D1,
        QualificationGateId.D3,
    ):
        for evidence_id in STATIC_REQUIRED_EVIDENCE_IDS[gate_id]:
            if status is AttemptStatus.NOT_RUN:
                values.append(
                    GateEvidenceSummary(
                        gate_id=gate_id,
                        evidence_id=evidence_id,
                        attempt_status=status,
                        verified=None,
                        evidence_fingerprint_sha256=None,
                        pipeline_rerun_verified=None,
                        base_estimator_fingerprint_sha256=None,
                        transformed_estimator_fingerprint_sha256=None,
                        reason_codes=("evidence-not-run",),
                    )
                )
            else:
                values.append(
                    GateEvidenceSummary(
                        gate_id=gate_id,
                        evidence_id=evidence_id,
                        attempt_status=AttemptStatus.EVALUABLE,
                        verified=True,
                        evidence_fingerprint_sha256=_digest(evidence_id),
                        pipeline_rerun_verified=(
                            True if gate_id is QualificationGateId.D3 else None
                        ),
                        base_estimator_fingerprint_sha256=(
                            _digest(f"{evidence_id}-base")
                            if gate_id is QualificationGateId.D3
                            else None
                        ),
                        transformed_estimator_fingerprint_sha256=(
                            _digest(f"{evidence_id}-transformed")
                            if gate_id is QualificationGateId.D3
                            else None
                        ),
                        reason_codes=(),
                    )
                )
    return tuple(values)


def _core_templates(
    protocol: QualificationProtocol,
    *,
    not_run: bool,
) -> tuple[CorePrimaryUnitSummary, ...]:
    result: list[CorePrimaryUnitSummary] = []
    for primary_id in sorted(
        {cell.primary_unit_id for cell in protocol.expected_core_cells}
    ):
        expected = tuple(
            cell
            for cell in protocol.expected_core_cells
            if cell.primary_unit_id == primary_id
        )
        first = expected[0]
        result.append(
            CorePrimaryUnitSummary(
                primary_unit_id=primary_id,
                selection_seed=first.selection_seed,
                control_id=first.control_id,
                expected_disposition=first.expected_core_disposition,
                stress_assignments=first.stress_assignments,
                d2_scientific_input_fingerprint_sha256=(
                    None if not_run else _digest(f"{primary_id}-scientific-input")
                ),
                domain_instance_fingerprint_sha256=(
                    None if not_run else _digest(f"{primary_id}-domain")
                ),
                support_instance_fingerprint_sha256=(
                    None if not_run else _digest(f"{primary_id}-support")
                ),
                attempt_status=(
                    AttemptStatus.NOT_RUN if not_run else AttemptStatus.EVALUABLE
                ),
                prediction_class=(
                    CorePredictionClass.NONE
                    if not_run
                    else CorePredictionClass.LOCALIZED_CORE
                ),
                state=(
                    QualificationState.NOT_RUN if not_run else QualificationState.PASS
                ),
                max_candidate_symmetric_difference_rows=(None if not_run else 0),
                reason_codes=("not-run",) if not_run else (),
                core_cell_ids=tuple(cell.core_cell_id for cell in expected),
            )
        )
    return tuple(result)


def _loop_templates(
    protocol: QualificationProtocol,
    *,
    not_run: bool,
) -> tuple[PrimaryUnitSummary, ...]:
    result: list[PrimaryUnitSummary] = []
    for primary_id in sorted(
        {cell.primary_unit_id for cell in protocol.expected_cells}
    ):
        expected = tuple(
            cell
            for cell in protocol.expected_cells
            if cell.primary_unit_id == primary_id
        )
        first = expected[0]
        disposition = next(
            cell.expected_loop_disposition
            for cell in expected
            if cell.loop_role is LoopRole.PRIMARY_BOUNDARY
        )
        result.append(
            PrimaryUnitSummary(
                primary_unit_id=primary_id,
                selection_seed=first.selection_seed,
                control_id=first.control_id,
                expected_disposition=disposition,
                stress_assignments=first.stress_assignments,
                domain_instance_fingerprint_sha256=(
                    None if not_run else _digest(f"{primary_id}-domain")
                ),
                support_instance_fingerprint_sha256=(
                    None if not_run else _digest(f"{primary_id}-support")
                ),
                attempt_status=(
                    AttemptStatus.NOT_RUN if not_run else AttemptStatus.EVALUABLE
                ),
                prediction_class=(
                    LoopPredictionClass.NONE if not_run else LoopPredictionClass.NONZERO
                ),
                state=(
                    QualificationState.NOT_RUN if not_run else QualificationState.PASS
                ),
                continuous_total_span_cycles=None if not_run else 0.0,
                reason_codes=("not-run",) if not_run else (),
                crossed_cell_ids=tuple(cell.cell_id for cell in expected),
            )
        )
    return tuple(result)


def _not_run_nonvacuity(
    protocol: QualificationProtocol,
) -> tuple[CrossedNonvacuitySummary, ...]:
    sentinel = {
        control.control_id: control.field_sensitivity_sentinel
        for control in protocol.selection.controls
    }
    controls = {
        cell.primary_unit_id: cell.control_id for cell in protocol.expected_cells
    }
    return tuple(
        CrossedNonvacuitySummary(
            primary_unit_id=primary_id,
            control_id=controls[primary_id],
            attempt_status=AttemptStatus.NOT_RUN,
            receipt_fingerprint_sha256=None,
            state=QualificationState.NOT_RUN,
            substantive_output_variation_required=sentinel[controls[primary_id]],
            field_adjacency_variant_count=0,
            cycle_adjacency_variant_count=0,
            field_consumption_variant_count=0,
            field_output_variant_count=0,
            maximum_pairwise_substantive_output_distance=None,
            minimum_substantive_output_distance=(
                protocol.thresholds.minimum_field_output_effect_size
            ),
            field_graph_pair_effects=(),
            substantive_response_field_graph_ids=(),
            substantive_response_field_graph_count=0,
            required_substantive_response_field_graph_count=3,
            matched_cycle_count=0,
            representative_content_variant_count=0,
            minimum_representative_content_variants=(
                protocol.thresholds.minimum_representative_content_variants
            ),
            reason_codes=("crossed-nonvacuity-not-run",),
        )
        for primary_id in sorted(controls)
    )


def _source_binding_summary(
    protocol: QualificationProtocol,
) -> QualificationSourceBindingSummary:
    return QualificationSourceBindingSummary(
        source_binding_receipt_sha256=_digest("source-binding-receipt"),
        engine_commit=protocol.engine.commit,
        head_commit="2" * 40,
        module_count=len(protocol.engine.modules),
        registry_source_sha256=protocol.registry.registry_source_sha256,
        registry_canonical_sha256=protocol.registry.registry_canonical_sha256,
        referent_canonical_sha256=protocol.registry.referent_canonical_sha256,
    )


def _selection_companions(
    protocol: QualificationProtocol,
) -> tuple[SelectionFreezeArtifact, SelectionAttemptClaimArtifact]:
    loaded = LoadedQualificationProtocol(
        protocol=protocol,
        source_path=Path("/tmp/spirallens-contract-test-protocol.json"),
        source_bytes=protocol.canonical_bytes,
        source_sha256=protocol.canonical_sha256,
        canonical_sha256=protocol.canonical_sha256,
    )
    freeze = SelectionFreezeArtifact.from_loaded_protocol(
        freeze_id="contract-test-freeze",
        loaded_protocol=loaded,
        seed_family_id="contract-test-seeds",
    )
    launch_intent = (
        SelectionLaunchIntentBinding(
            path="/tmp/spirallens-contract-test-launch-intent.json",
            source_sha256=_digest("contract-test-launch-intent"),
            canonical_sha256=_digest("contract-test-launch-intent"),
            byte_count=1,
        )
        if protocol.protocol_id == CLOSED_D0_D5_PROTOCOL_ID
        else None
    )
    claim = SelectionAttemptClaimArtifact.from_freeze(
        claim_id="contract-test-attempt",
        freeze=freeze,
        launch_intent=launch_intent,
    )
    return freeze, claim


def _static_not_run_receipts() -> tuple[StaticEvidenceReceipt, ...]:
    return tuple(
        StaticEvidenceReceipt(
            gate_id=gate_id,
            evidence_id=evidence_id,
            attempt_status=AttemptStatus.NOT_RUN,
            underlying_receipt_sha256=None,
            producer_modules=(),
            checked_obligation_ids=(),
            failed_obligation_ids=(),
            observation_fingerprints_sha256=(),
            pipeline_rerun_count=0,
            base_estimator_fingerprint_sha256=None,
            transformed_estimator_fingerprint_sha256=None,
        )
        for gate_id in (QualificationGateId.D1, QualificationGateId.D3)
        for evidence_id in STATIC_REQUIRED_EVIDENCE_IDS[gate_id]
    )


def _not_run_d2_confounder_receipt(
    protocol: QualificationProtocol,
) -> D2CoreConfounderMatrixReceipt:
    thresholds = protocol.thresholds
    policy = CorePrerequisitePolicy(
        policy_id="qualification-core-prerequisites-v0.5",
        core_amplitude_ceiling=thresholds.core_amplitude_ceiling,
        identifiability_floor=thresholds.identifiability_floor,
        edge_coherence_floor=thresholds.coherence_floor,
        minimum_support_count=thresholds.minimum_support_count,
        max_localized_core_fraction=thresholds.max_localized_core_fraction,
        minimum_core_contrast_ratio=thresholds.minimum_core_contrast_ratio,
    )
    return D2CoreConfounderMatrixReceipt(
        policy_fingerprint_sha256=policy.fingerprint_sha256,
        confounder_declarations=tuple(
            item.to_dict() for item in protocol.d2_core_confounders
        ),
        field_graph_ids=tuple(
            item.graph_id for item in protocol.graphs.field_estimation
        ),
        cells=(),
        state=QualificationState.NOT_RUN,
        failed_cell_ids=(),
    )


def _not_run_result(
    protocol: QualificationProtocol,
    *,
    selection_launch_authorization_sha256: str | None = None,
) -> QualificationResult:
    core_cells = materialize_expected_core_cells(protocol.expected_core_cells, ())
    loop_cells = materialize_expected_cells(protocol.expected_cells, ())
    core_primaries = collapse_core_primary_units(
        protocol.expected_core_cells,
        core_cells,
        _core_templates(protocol, not_run=True),
        candidate_difference_tolerance_rows=(
            protocol.thresholds.core_candidate_difference_tolerance_rows
        ),
    )
    loop_primaries = collapse_primary_units(
        protocol.expected_cells,
        loop_cells,
        _loop_templates(protocol, not_run=True),
        graph_total_tolerance_cycles=(protocol.thresholds.graph_total_tolerance_cycles),
    )
    nonvacuity = _not_run_nonvacuity(protocol)
    strata = summarize_strata(
        protocol.expected_strata,
        loop_primaries,
        protocol.coverage_policy,
    )
    source_binding = _source_binding_summary(protocol)
    freeze, claim = _selection_companions(protocol)
    static_receipts = _static_not_run_receipts()
    evidence = (
        *(
            item
            for item in _static_evidence(status=AttemptStatus.NOT_RUN)
            if item.gate_id is QualificationGateId.D0
        ),
        *(item.to_summary() for item in static_receipts),
    )
    d2_confounder = _not_run_d2_confounder_receipt(protocol)
    gates = (
        derive_static_gate(QualificationGateId.D0, evidence),
        derive_static_gate(QualificationGateId.D1, evidence),
        build_d2_gate(
            core_primaries,
            confounder_state=d2_confounder.state,
            confounder_reason_codes=d2_confounder.reason_codes,
        ),
        derive_static_gate(QualificationGateId.D3, evidence),
        build_d4_gate(
            loop_primaries,
            nonvacuity,
            evaluation_unit=protocol.coverage_policy.evaluation_unit,
        ),
        build_d5_gate(
            loop_primaries,
            strata,
            protocol.coverage_policy,
            expected_strata=protocol.expected_strata,
        ),
    )
    evidence_bundle = QualificationEvidenceBundle(
        protocol_canonical_sha256=protocol.canonical_sha256,
        source_binding_receipt_sha256=(source_binding.source_binding_receipt_sha256),
        selection_freeze_artifact_sha256=freeze.canonical_sha256,
        selection_attempt_claim_sha256=claim.canonical_sha256,
        d2_confounder_matrix_receipt=d2_confounder,
        static_runtime_receipts=(),
        core_cell_receipts=(),
        loop_cell_receipts=(),
        nonvacuity_receipts=(),
    )
    result_id = "d0-d5-selection-result-v0-2"
    evidence_root = qualification_result_evidence_root_sha256(
        result_id=result_id,
        protocol_id=protocol.protocol_id,
        protocol_source_sha256=protocol.canonical_sha256,
        protocol_canonical_sha256=protocol.canonical_sha256,
        selection_freeze_artifact_sha256=freeze.canonical_sha256,
        selection_attempt_claim_sha256=claim.canonical_sha256,
        selection_launch_authorization_sha256=(selection_launch_authorization_sha256),
        source_binding=source_binding,
        evidence_bundle=evidence_bundle,
        gate_results=gates,
        gate_evidence=evidence,
        static_evidence_receipts=static_receipts,
        core_primary_units=core_primaries,
        core_cells=core_cells,
        primary_units=loop_primaries,
        crossed_cells=loop_cells,
        crossed_nonvacuity=nonvacuity,
        strata=strata,
    )
    core_primaries_by_id = {item.primary_unit_id: item for item in core_primaries}
    loop_primaries_by_id = {item.primary_unit_id: item for item in loop_primaries}
    nonvacuity_by_id = {item.primary_unit_id: item for item in nonvacuity}
    core_cells_by_lane = {f"core.{item.core_cell_id}": item for item in core_cells}
    loop_cells_by_lane = {f"loop.{item.cell_id}": item for item in loop_cells}
    ledger = QualificationEventLedger.create(qualification_event_lane_ids(protocol))
    for lane_id in ledger.expected_lane_ids:
        if lane_id.startswith("core."):
            cell = core_cells_by_lane[lane_id]
            payloads = build_qualification_lane_event_payloads(
                protocol=protocol,
                protocol_source_sha256=protocol.canonical_sha256,
                source_binding=source_binding,
                selection_freeze_artifact_sha256=freeze.canonical_sha256,
                selection_attempt_claim_sha256=claim.canonical_sha256,
                result_id=result_id,
                result_evidence_root_sha256=evidence_root,
                cell=cell,
                primary=core_primaries_by_id[cell.primary_unit_id],
                nonvacuity=None,
                strata=strata,
            )
        else:
            cell = loop_cells_by_lane[lane_id]
            payloads = build_qualification_lane_event_payloads(
                protocol=protocol,
                protocol_source_sha256=protocol.canonical_sha256,
                source_binding=source_binding,
                selection_freeze_artifact_sha256=freeze.canonical_sha256,
                selection_attempt_claim_sha256=claim.canonical_sha256,
                result_id=result_id,
                result_evidence_root_sha256=evidence_root,
                cell=cell,
                primary=loop_primaries_by_id[cell.primary_unit_id],
                nonvacuity=nonvacuity_by_id[cell.primary_unit_id],
                strata=strata,
            )
        for payload in payloads:
            ledger = ledger.append(
                lane_id=lane_id,
                event_kind=payload.event_kind,
                payload=payload,
            )
    return QualificationResult(
        result_id=result_id,
        protocol_id=protocol.protocol_id,
        protocol_source_sha256=protocol.canonical_sha256,
        protocol_canonical_sha256=protocol.canonical_sha256,
        selection_freeze_artifact_sha256=freeze.canonical_sha256,
        selection_attempt_claim_sha256=claim.canonical_sha256,
        source_binding=source_binding,
        evidence_bundle=evidence_bundle,
        result_evidence_root_sha256=evidence_root,
        event_ledger_receipt=ledger.receipt(),
        gate_results=gates,
        gate_evidence=evidence,
        static_evidence_receipts=static_receipts,
        core_primary_units=core_primaries,
        core_cells=core_cells,
        primary_units=loop_primaries,
        crossed_cells=loop_cells,
        crossed_nonvacuity=nonvacuity,
        strata=strata,
        selection_launch_authorization_sha256=(selection_launch_authorization_sha256),
    )


def _fake_passing_gate(
    gate_id: QualificationGateId,
    count: int,
) -> GateResult:
    return GateResult(
        gate_id=gate_id,
        state=QualificationState.PASS,
        evaluation_unit=EvaluationUnit.PHANTOM_INSTANCE,
        attempted_count=count,
        evaluable_count=count,
        attempt_insufficient_count=0,
        attempt_not_run_count=0,
        pass_count=count,
        fail_count=0,
        fail_graph_dependence_count=0,
        insufficient_count=0,
        not_run_count=0,
        reason_codes=(),
    )


def test_gate_result_serializes_and_enforces_positive_claim_scope() -> None:
    gate = _fake_passing_gate(QualificationGateId.D2, 1)
    payload = gate.to_dict()

    assert payload["claim_scope"] == "cartesian-surrogate-only"
    assert GateResult.from_dict(payload) == gate

    payload["claim_scope"] = "engine-and-protocol-contracts"
    with pytest.raises(QualificationContractError, match="mandatory positive scope"):
        GateResult.from_dict(payload)


def _validate_result(
    result: QualificationResult,
    protocol: QualificationProtocol,
) -> None:
    freeze, claim = _selection_companions(protocol)
    result.validate_against_protocol(
        protocol,
        protocol_source_sha256=protocol.canonical_sha256,
        selection_freeze_artifact=freeze,
        selection_attempt_claim=claim,
    )


def test_protocol_and_not_run_result_round_trip_and_validate() -> None:
    protocol = _protocol()
    result = _not_run_result(protocol)

    assert QualificationProtocol.from_dict(protocol.to_dict()) == protocol
    assert QualificationResult.from_dict(result.to_dict()) == result
    _validate_result(result, protocol)
    assert all(gate.state is QualificationState.NOT_RUN for gate in result.gate_results)


def test_result_authorization_lineage_is_explicit_for_official_and_custom(
    tmp_path: Path,
) -> None:
    protocol = _protocol()
    result = _not_run_result(protocol)

    assert result.selection_launch_authorization_sha256 is None
    with pytest.raises(
        QualificationContractError,
        match="must be None for custom/development",
    ):
        replace(
            result,
            selection_launch_authorization_sha256="a" * 64,
        )
    with pytest.raises(
        QualificationContractError,
        match="required for the official",
    ):
        replace(
            result,
            protocol_id=CLOSED_D0_D5_PROTOCOL_ID,
            selection_launch_authorization_sha256=None,
        )
    freeze, claim = _selection_companions(protocol)
    with pytest.raises(
        QualificationContractError,
        match="must be None for custom/development",
    ):
        result.validate_against_protocol(
            protocol,
            protocol_source_sha256=protocol.canonical_sha256,
            selection_freeze_artifact=freeze,
            selection_attempt_claim=claim,
            selection_launch_authorization_sha256="b" * 64,
        )

    official_protocol = replace(
        protocol,
        protocol_id=CLOSED_D0_D5_PROTOCOL_ID,
    )
    official_authorization_sha256 = "c" * 64
    official_result = _not_run_result(
        official_protocol,
        selection_launch_authorization_sha256=(official_authorization_sha256),
    )
    official_freeze, official_claim = _selection_companions(official_protocol)
    with pytest.raises(
        QualificationContractError,
        match="launch authorization differs",
    ):
        official_result.validate_against_protocol(
            official_protocol,
            protocol_source_sha256=official_protocol.canonical_sha256,
            selection_freeze_artifact=official_freeze,
            selection_attempt_claim=official_claim,
            selection_launch_authorization_sha256="d" * 64,
        )
    official_result.validate_against_protocol(
        official_protocol,
        protocol_source_sha256=official_protocol.canonical_sha256,
        selection_freeze_artifact=official_freeze,
        selection_attempt_claim=official_claim,
        selection_launch_authorization_sha256=(official_authorization_sha256),
    )
    loaded_official_protocol = LoadedQualificationProtocol(
        protocol=official_protocol,
        source_path=tmp_path / "official-protocol.json",
        source_bytes=official_protocol.canonical_bytes,
        source_sha256=official_protocol.canonical_sha256,
        canonical_sha256=official_protocol.canonical_sha256,
    )
    standalone_path = tmp_path / "forbidden-official-result.json"
    with pytest.raises(
        QualificationContractError,
        match="terminal transaction publisher/loader",
    ):
        write_qualification_result(
            standalone_path,
            official_result,
            protocol=loaded_official_protocol,
            selection_freeze_artifact=official_freeze,
            selection_attempt_claim=official_claim,
            selection_launch_authorization_sha256=(official_authorization_sha256),
        )
    standalone_path.write_bytes(official_result.canonical_bytes)
    with pytest.raises(
        QualificationContractError,
        match="terminal transaction publisher/loader",
    ):
        load_qualification_result(
            standalone_path,
            protocol=loaded_official_protocol,
            expected_source_sha256=official_result.canonical_sha256,
            expected_canonical_sha256=official_result.canonical_sha256,
            selection_freeze_artifact=official_freeze,
            selection_attempt_claim=official_claim,
            selection_launch_authorization_sha256=(official_authorization_sha256),
        )


def test_persistence_round_trip_keeps_exact_protocol_join(tmp_path: Path) -> None:
    protocol = _protocol()
    protocol_path = tmp_path / "protocol.json"
    protocol_identity = write_qualification_protocol(protocol_path, protocol)
    loaded_protocol = load_qualification_protocol(
        protocol_path,
        expected_source_sha256=protocol_identity.source_sha256,
        expected_canonical_sha256=protocol_identity.canonical_sha256,
    )
    result = replace(
        _not_run_result(protocol),
        protocol_source_sha256=loaded_protocol.source_sha256,
    )
    freeze, claim = _selection_companions(protocol)
    result_path = tmp_path / "result.json"
    result_identity = write_qualification_result(
        result_path,
        result,
        protocol=loaded_protocol,
        selection_freeze_artifact=freeze,
        selection_attempt_claim=claim,
    )
    loaded_result = load_qualification_result(
        result_path,
        protocol=loaded_protocol,
        expected_source_sha256=result_identity.source_sha256,
        expected_canonical_sha256=result_identity.canonical_sha256,
        selection_freeze_artifact=freeze,
        selection_attempt_claim=claim,
    )

    assert loaded_result.result == result
    assert loaded_result.source_bytes == result.canonical_bytes
    assert loaded_result.selection_freeze_artifact == freeze
    assert loaded_result.selection_attempt_claim == claim

    wrong_freeze = SelectionFreezeArtifact.from_loaded_protocol(
        freeze_id="contract-test-other-freeze",
        loaded_protocol=loaded_protocol,
        seed_family_id=freeze.seed_family_id,
    )
    wrong_freeze_claim = SelectionAttemptClaimArtifact.from_freeze(
        claim_id=claim.claim_id,
        freeze=wrong_freeze,
    )
    with pytest.raises(
        QualificationContractError,
        match="selection-freeze digest differs",
    ):
        load_qualification_result(
            result_path,
            protocol=loaded_protocol,
            expected_source_sha256=result_identity.source_sha256,
            expected_canonical_sha256=result_identity.canonical_sha256,
            selection_freeze_artifact=wrong_freeze,
            selection_attempt_claim=wrong_freeze_claim,
        )

    wrong_claim = SelectionAttemptClaimArtifact.from_freeze(
        claim_id="contract-test-other-attempt",
        freeze=freeze,
    )
    with pytest.raises(
        QualificationContractError,
        match="selection-attempt-claim digest differs",
    ):
        load_qualification_result(
            result_path,
            protocol=loaded_protocol,
            expected_source_sha256=result_identity.source_sha256,
            expected_canonical_sha256=result_identity.canonical_sha256,
            selection_freeze_artifact=freeze,
            selection_attempt_claim=wrong_claim,
        )


def test_d3_evidence_requires_pipeline_rerun_and_both_fingerprints() -> None:
    evidence_id = STATIC_REQUIRED_EVIDENCE_IDS[QualificationGateId.D3][0]
    with pytest.raises(QualificationContractError, match="pipeline rerun"):
        GateEvidenceSummary(
            gate_id=QualificationGateId.D3,
            evidence_id=evidence_id,
            attempt_status=AttemptStatus.EVALUABLE,
            verified=True,
            evidence_fingerprint_sha256=_digest("evidence"),
            pipeline_rerun_verified=None,
            base_estimator_fingerprint_sha256=None,
            transformed_estimator_fingerprint_sha256=None,
            reason_codes=(),
        )


def test_static_evidence_manifest_is_exact_and_cannot_be_relabelled() -> None:
    evidence = _static_evidence(status=AttemptStatus.EVALUABLE)
    d1 = tuple(item for item in evidence if item.gate_id is QualificationGateId.D1)
    with pytest.raises(QualificationContractError, match="exact static manifest"):
        derive_static_gate(
            QualificationGateId.D1,
            (replace(d1[0], evidence_id="invented-family"), d1[1]),
        )


def test_all_not_run_evidence_cannot_be_replaced_by_passing_d2_or_d4() -> None:
    protocol = _protocol()
    result = _not_run_result(protocol)
    gates = list(result.gate_results)
    count = len(result.primary_units)

    gates[2] = _fake_passing_gate(QualificationGateId.D2, count)
    with pytest.raises(QualificationContractError, match="evidence root differs"):
        replace(result, gate_results=tuple(gates))

    gates = list(result.gate_results)
    gates[4] = _fake_passing_gate(QualificationGateId.D4, count)
    with pytest.raises(QualificationContractError, match="evidence root differs"):
        replace(result, gate_results=tuple(gates))


def test_all_not_run_d3_cannot_be_replaced_by_a_passing_gate() -> None:
    result = _not_run_result(_protocol())
    gates = list(result.gate_results)
    gates[3] = _fake_passing_gate(
        QualificationGateId.D3,
        len(STATIC_REQUIRED_EVIDENCE_IDS[QualificationGateId.D3]),
    )
    gates[3] = replace(gates[3], evaluation_unit=EvaluationUnit.MATCHED_CLASS)
    with pytest.raises(QualificationContractError, match="evidence root differs"):
        replace(result, gate_results=tuple(gates))


def test_crossed_nonvacuity_requires_output_variation_only_for_sentinel() -> None:
    ordinary = CrossedNonvacuitySummary(
        primary_unit_id="ordinary",
        control_id="ordinary-control",
        attempt_status=AttemptStatus.EVALUABLE,
        receipt_fingerprint_sha256=_digest("ordinary"),
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
    assert ordinary.state is QualificationState.PASS

    with pytest.raises(
        QualificationContractError,
        match="reason_codes differ|attempt status differs",
    ):
        replace(
            ordinary,
            primary_unit_id="sentinel",
            control_id="sentinel-control",
            substantive_output_variation_required=True,
        )


def test_crossed_nonvacuity_summary_binds_exact_receipt_fingerprint() -> None:
    pair_effects = _field_pair_effects(distance=1e-3)
    receipt = CrossedNonvacuityReceipt(
        state=QualificationState.PASS,
        substantive_output_variation_required=True,
        field_adjacency_variant_count=3,
        cycle_adjacency_variant_count=3,
        field_consumption_variant_count=2,
        field_output_variant_count=2,
        maximum_pairwise_substantive_output_distance=1e-3,
        minimum_substantive_output_distance=1e-6,
        field_graph_pair_effects=pair_effects,
        substantive_response_field_graph_ids=("a-one", "a-three", "a-two"),
        substantive_response_field_graph_count=3,
        required_substantive_response_field_graph_count=3,
        matched_cycle_count=3,
        representative_content_variant_count=2,
        minimum_representative_content_variants=2,
        reason_codes=(),
    )
    summary = CrossedNonvacuitySummary.from_receipt(
        primary_unit_id="unit-sentinel",
        control_id="sentinel-control",
        receipt=receipt,
    )
    assert summary.receipt_fingerprint_sha256 == receipt.fingerprint_sha256
    assert summary.state is receipt.state
    assert summary.substantive_output_variation_required is True


def test_protocol_validator_rejects_wrong_sentinel_assignment() -> None:
    protocol = _protocol()
    result = _not_run_result(protocol)
    sentinel = next(
        item
        for item in result.crossed_nonvacuity
        if item.substantive_output_variation_required
    )
    tampered = tuple(
        replace(
            item,
            substantive_output_variation_required=False,
        )
        if item.primary_unit_id == sentinel.primary_unit_id
        else item
        for item in result.crossed_nonvacuity
    )
    # The complete evidence root binds this assignment before protocol
    # validation can even be reached.
    with pytest.raises(QualificationContractError, match="evidence root differs"):
        replace(result, crossed_nonvacuity=tampered)


def test_loop_cell_pass_cannot_hide_oracle_error_above_frozen_tolerance() -> None:
    protocol = _protocol()
    result = _not_run_result(protocol)
    expected = next(
        cell
        for cell in protocol.expected_cells
        if cell.loop_role is LoopRole.PRIMARY_BOUNDARY
        and cell.expected_loop_disposition is LoopDisposition.NONZERO
    )
    observed = CrossedCellSummary(
        cell_id=expected.cell_id,
        primary_unit_id=expected.primary_unit_id,
        field_graph_id=expected.field_graph_id,
        cycle_graph_id=expected.cycle_graph_id,
        loop_role=expected.loop_role,
        expected_disposition=expected.expected_loop_disposition,
        field_graph_fingerprint_sha256=_digest("a"),
        cycle_graph_fingerprint_sha256=_digest("b"),
        field_estimate_fingerprint_sha256=_digest("field"),
        cycle_binding_fingerprint_sha256=_digest("binding"),
        representative_content_sha256=_digest("content"),
        blind_input_fingerprint_sha256=_digest("input"),
        prediction_fingerprint_sha256=_digest("prediction"),
        oracle_fingerprint_sha256=_digest("oracle"),
        attempt_status=AttemptStatus.EVALUABLE,
        prediction_class=LoopPredictionClass.NONZERO,
        state=QualificationState.PASS,
        continuous_signed_total_cycles=1.0,
        oracle_absolute_error_cycles=0.2,
        reason_codes=(),
    )
    cells = tuple(
        observed if cell.cell_id == observed.cell_id else cell
        for cell in result.crossed_cells
    )
    # Keeping the stale evidence root models a forged result receipt.
    with pytest.raises(QualificationContractError, match="evidence root differs"):
        replace(result, crossed_cells=cells)


def test_loop_class_must_follow_continuous_total_and_frozen_floor() -> None:
    protocol = _protocol()
    result = _not_run_result(protocol)
    expected = next(
        cell
        for cell in protocol.expected_cells
        if cell.loop_role is LoopRole.PRIMARY_BOUNDARY
        and cell.expected_loop_disposition is LoopDisposition.NONZERO
    )
    observed = CrossedCellSummary(
        cell_id=expected.cell_id,
        primary_unit_id=expected.primary_unit_id,
        field_graph_id=expected.field_graph_id,
        cycle_graph_id=expected.cycle_graph_id,
        loop_role=expected.loop_role,
        expected_disposition=expected.expected_loop_disposition,
        field_graph_fingerprint_sha256=_digest("floor-a"),
        cycle_graph_fingerprint_sha256=_digest("floor-b"),
        field_estimate_fingerprint_sha256=_digest("floor-field"),
        cycle_binding_fingerprint_sha256=_digest("floor-binding"),
        representative_content_sha256=_digest("floor-content"),
        blind_input_fingerprint_sha256=_digest("floor-input"),
        prediction_fingerprint_sha256=_digest("floor-prediction"),
        oracle_fingerprint_sha256=_digest("floor-oracle"),
        attempt_status=AttemptStatus.EVALUABLE,
        prediction_class=LoopPredictionClass.NONZERO,
        state=QualificationState.PASS,
        continuous_signed_total_cycles=0.1,
        oracle_absolute_error_cycles=0.0,
        reason_codes=(),
    )
    with pytest.raises(QualificationContractError, match="evidence root differs"):
        replace(
            result,
            crossed_cells=tuple(
                observed if cell.cell_id == observed.cell_id else cell
                for cell in result.crossed_cells
            ),
        )


def test_unique_loop_class_cannot_hide_continuous_graph_drift() -> None:
    protocol = _protocol()
    result = _not_run_result(protocol)
    expected = tuple(
        cell
        for cell in protocol.expected_cells
        if cell.control_id == "nonzero-core"
        and cell.loop_role is LoopRole.PRIMARY_BOUNDARY
    )[:2]
    totals = (0.9, 1.2)
    replacements: dict[str, CrossedCellSummary] = {}
    for cell, total in zip(expected, totals, strict=True):
        replacements[cell.cell_id] = CrossedCellSummary(
            cell_id=cell.cell_id,
            primary_unit_id=cell.primary_unit_id,
            field_graph_id=cell.field_graph_id,
            cycle_graph_id=cell.cycle_graph_id,
            loop_role=cell.loop_role,
            expected_disposition=cell.expected_loop_disposition,
            field_graph_fingerprint_sha256=_digest(f"{cell.cell_id}-a"),
            cycle_graph_fingerprint_sha256=_digest(f"{cell.cell_id}-b"),
            field_estimate_fingerprint_sha256=_digest(f"{cell.cell_id}-field"),
            cycle_binding_fingerprint_sha256=_digest(f"{cell.cell_id}-binding"),
            representative_content_sha256=_digest(f"{cell.cell_id}-content"),
            blind_input_fingerprint_sha256=_digest(f"{cell.cell_id}-input"),
            prediction_fingerprint_sha256=_digest(f"{cell.cell_id}-prediction"),
            oracle_fingerprint_sha256=_digest(f"{cell.cell_id}-oracle"),
            attempt_status=AttemptStatus.EVALUABLE,
            prediction_class=LoopPredictionClass.NONZERO,
            state=QualificationState.PASS,
            continuous_signed_total_cycles=total,
            oracle_absolute_error_cycles=0.0,
            reason_codes=(),
        )
    tampered_cells = tuple(
        replacements.get(cell.cell_id, cell) for cell in result.crossed_cells
    )
    with pytest.raises(
        QualificationContractError,
        match="evidence root differs",
    ):
        replace(result, crossed_cells=tampered_cells)


def test_core_cell_and_loop_cell_use_disjoint_enums() -> None:
    protocol = _protocol()
    core_expected = protocol.expected_core_cells[0]
    with pytest.raises(TypeError, match="CorePredictionClass"):
        CoreCellSummary(
            core_cell_id=core_expected.core_cell_id,
            primary_unit_id=core_expected.primary_unit_id,
            field_graph_id=core_expected.field_graph_id,
            expected_disposition=core_expected.expected_core_disposition,
            field_graph_fingerprint_sha256=None,
            field_estimate_fingerprint_sha256=None,
            blind_input_fingerprint_sha256=None,
            prediction_fingerprint_sha256=None,
            oracle_fingerprint_sha256=None,
            candidate_fingerprint_sha256=None,
            oracle_anchor_fingerprint_sha256=None,
            candidate_anchor_symmetric_difference_rows=(),
            attempt_status=AttemptStatus.NOT_RUN,
            prediction_class=LoopPredictionClass.NONE,  # type: ignore[arg-type]
            state=QualificationState.NOT_RUN,
            reason_codes=("not-run",),
        )


def test_missing_core_or_nonvacuity_primary_is_rejected_at_construction() -> None:
    result = _not_run_result(_protocol())
    with pytest.raises(
        QualificationContractError,
        match="evidence root differs",
    ):
        replace(result, core_cells=result.core_cells[:-1])
    with pytest.raises(QualificationContractError, match="evidence root differs"):
        replace(result, crossed_nonvacuity=result.crossed_nonvacuity[:-1])
