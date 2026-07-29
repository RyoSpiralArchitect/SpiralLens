from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

import spirallens.qualification.freeze as qualification_freeze
from spirallens.graphs import GraphFamily, GraphPurpose
from spirallens.qualification.common import (
    CoreDisposition,
    EvaluationUnit,
    LoopDisposition,
    QualificationContractError,
)
from spirallens.qualification.contracts import MAX_QUALIFICATION_RESULT_BYTES
from spirallens.qualification.freeze import (
    SelectionAccessState,
    SelectionAttemptClaimArtifact,
    SelectionConsumptionArtifact,
    SelectionExecutionStartArtifact,
    SelectionFailedAttemptArtifact,
    SelectionFreezeArtifact,
    TerminalAttemptArtifactKind,
    begin_selection_execution,
    claim_selection_attempt,
    load_selection_attempt_claim,
    load_selection_execution_start,
    load_selection_freeze,
    load_terminal_selection_consumption,
    publish_terminal_selection_consumption,
    seed_family_commitment_sha256,
    selection_attempt_key_sha256,
    selection_freeze_store_path,
    validate_persisted_selection_attempt_claim,
    write_selection_freeze,
)
from spirallens.qualification.persistence import (
    LoadedQualificationProtocol,
    load_qualification_protocol,
    write_qualification_protocol,
)
from spirallens.qualification.protocol import (
    CLOSED_CARTESIAN_ESTIMATOR_ID,
    CLOSED_CARTESIAN_GENERATOR_FAMILY_ID,
    CLOSED_CARTESIAN_TRIVIALIZATION_ID,
    CLOSED_CORE_LOCALIZER_ID,
    CLOSED_REPRESENTATION_ESTIMATOR_ID,
    CLOSED_REPRESENTATION_TRIVIALIZATION_ID,
    F2_LOCAL_COVARIANT_SECTION_REFERENT_ID,
    MAX_GRAPH_TOTAL_TOLERANCE_CYCLES,
    MAX_LOOP_ORACLE_TOLERANCE_CYCLES,
    MAX_QUALIFICATION_CORE_CELLS,
    MAX_QUALIFICATION_EVENT_ENTRIES,
    MAX_QUALIFICATION_EVENT_LANES,
    MAX_QUALIFICATION_LOOP_CELLS,
    MAX_QUALIFICATION_PRIMARY_UNITS,
    MAX_QUALIFICATION_RESULT_BYTES_BOUND,
    MIN_BRANCH_MARGIN_RAD,
    MIN_COHERENCE_FLOOR,
    MIN_FIELD_OUTPUT_EFFECT_SIZE,
    MIN_IDENTIFIABILITY_FLOOR,
    QUALIFICATION_EVENTS_PER_LANE,
    AuthorityBoundary,
    BoundaryTemplate,
    CartesianSelectionSubstrate,
    ClosedImplementationRegistry,
    ControlDeclaration,
    CoreGraphMode,
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


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _loaded_protocol(tmp_path: Path) -> LoadedQualificationProtocol:
    protocol = _protocol()
    path = tmp_path / "protocol.json"
    identity = write_qualification_protocol(path, protocol)
    return load_qualification_protocol(
        path,
        expected_source_sha256=identity.source_sha256,
        expected_canonical_sha256=identity.canonical_sha256,
    )


def _instrument() -> InstrumentSelection:
    return InstrumentSelection(
        referent_id=F2_LOCAL_COVARIANT_SECTION_REFERENT_ID,
        estimator_id=CLOSED_REPRESENTATION_ESTIMATOR_ID,
        trivialization_id=CLOSED_REPRESENTATION_TRIVIALIZATION_ID,
        core_localizer_id=CLOSED_CORE_LOCALIZER_ID,
    )


def _case_bindings() -> tuple[GeneratorCaseBinding, ...]:
    return (
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
    )


def _implementation_registry() -> ClosedImplementationRegistry:
    return ClosedImplementationRegistry(
        generator_family_id=CLOSED_CARTESIAN_GENERATOR_FAMILY_ID,
        generator_cases=_case_bindings(),
        surrogate_estimator_id=CLOSED_CARTESIAN_ESTIMATOR_ID,
        surrogate_trivialization_id=CLOSED_CARTESIAN_TRIVIALIZATION_ID,
        instrument=_instrument(),
    )


def _controls() -> tuple[ControlDeclaration, ...]:
    return (
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


def _graph(
    graph_id: str,
    family: GraphFamily,
    purpose: GraphPurpose,
) -> GraphDeclaration:
    parameters: tuple[tuple[str, int | float], ...]
    if family is GraphFamily.MUTUAL_KNN:
        parameters = (("neighbor_count", 4),)
    elif family is GraphFamily.FIXED_RADIUS:
        parameters = (("radius", 0.48),)
    else:
        parameters = (
            (
                "minimum_shared_neighbors",
                2 if purpose is GraphPurpose.FIELD_ESTIMATION else 1,
            ),
            ("neighbor_count", 4),
        )
    return GraphDeclaration(
        graph_id=graph_id,
        family=family,
        purpose=purpose,
        parameters=parameters,
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
    assignments = (
        StressAssignment("boundary", "central"),
        StressAssignment("state-geometry-warp", "nominal"),
        StressAssignment("structured-observation-perturbation", "nominal"),
    )
    stratum_ids = tuple(
        required_stress_stratum_id(item.axis_id, item.level) for item in assignments
    )
    controls = _controls()
    core_cells: list[ExpectedCoreCell] = []
    loop_cells: list[ExpectedCell] = []
    primary_ids: list[str] = []
    for control in controls:
        primary_id = f"unit-{control.control_id}"
        primary_ids.append(primary_id)
        for a_graph in a_graphs:
            core_cells.append(
                ExpectedCoreCell(
                    core_cell_id=f"core-{control.control_id}-{a_graph.graph_id}",
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
                    expected_loop = (
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
                            expected_loop_disposition=expected_loop,
                            stratum_ids=stratum_ids,
                        )
                    )
    primary_members = tuple(sorted(primary_ids))
    return QualificationProtocol(
        protocol_id="qualification-hardening-test-v0-3",
        engine=EngineBinding(
            repository="RyoSpiralArchitect/SpiralLens",
            commit="1" * 40,
            modules=(
                ModuleDigest(
                    "spirallens.qualification.protocol",
                    _digest("protocol"),
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
            baseline=1.25,
            second_harmonic_scale=0.35,
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
            offcore_boundary=BoundaryTemplate("offcore", 0, 0, 2, 2),
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
            core_amplitude_ceiling=0.05,
            identifiability_floor=0.2,
            coherence_floor=0.3,
            minimum_support_count=2,
            max_localized_core_fraction=0.05,
            minimum_core_contrast_ratio=2.0,
            branch_margin_rad=0.05,
            loop_nonzero_floor_cycles=0.5,
            loop_oracle_tolerance_cycles=1e-8,
            graph_total_tolerance_cycles=1e-8,
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
                primary_unit_ids=primary_members,
            )
            for stratum_id in stratum_ids
        ),
        authority=AuthorityBoundary(),
    )


def test_hardened_protocol_round_trips_with_exact_registry_and_strata() -> None:
    protocol = _protocol()

    assert QualificationProtocol.from_dict(protocol.to_dict()) == protocol
    assert protocol.implementation_registry.instrument == protocol.instrument
    assert (
        protocol.instrument.core_graph_mode
        is CoreGraphMode.INHERIT_FIELD_ESTIMATION_GRAPH
    )
    assert (
        protocol.to_dict()["instrument"]["core_graph_mode"]
        == "inherit_field_estimation_graph"
    )
    assert protocol.authority.p0_competitor_selection_authorized is False
    assert protocol.authority.representation_d2_d5_transfer_authorized is False
    assert protocol.authority.localized_core_loop_join_authorized is False
    assert protocol.authority.synthetic_qualification_authorized is False
    assert tuple(item.stratum_id for item in protocol.expected_strata) == (
        "stress.boundary.central",
        "stress.state-geometry-warp.nominal",
        "stress.structured-observation-perturbation.nominal",
    )
    assert protocol.gate_claim_scopes == {
        "d0": "engine-and-protocol-contracts",
        "d1": "cartesian-surrogate-and-representation-development",
        "d2": "cartesian-surrogate-only",
        "d3": "cartesian-surrogate-and-representation-development",
        "d4": "cartesian-surrogate-only",
        "d5": "cartesian-surrogate-only",
    }
    assert protocol.evaluation_design.to_dict() == {
        "declared_seed_block_count": 1,
        "matched_control_count": 4,
        "paired_stress_variant_count_per_seed_control": 1,
        "execution_variant_count": 4,
        "d2_unique_scientific_input_unit_count": 4,
        "loop_execution_variant_count": 4,
        "paired_repeated_measure_block_unit": "selection-seed-block",
        "controls_are_matched": True,
        "stress_variants_are_paired_repeated_measures": True,
        "boundary_variants_are_d2_repeated_measures": True,
        "execution_variants_are_independent_replicates": False,
        "seed_block_independence_proved": False,
        "inferential_sample_size_claimed": False,
    }


def test_protocol_rejects_derived_scope_or_evaluation_design_tampering() -> None:
    payload = _protocol().to_dict()
    scopes = dict(payload["gate_claim_scopes"])
    scopes["d2"] = "engine-and-protocol-contracts"
    payload["gate_claim_scopes"] = scopes
    with pytest.raises(QualificationContractError, match="gate_claim_scopes.d2"):
        QualificationProtocol.from_dict(payload)

    payload = _protocol().to_dict()
    design = dict(payload["evaluation_design"])
    design["execution_variants_are_independent_replicates"] = True
    payload["evaluation_design"] = design
    with pytest.raises(
        QualificationContractError,
        match="execution_variants_are_independent_replicates",
    ):
        QualificationProtocol.from_dict(payload)


def test_graph_free_core_mode_is_not_admitted_by_qualification_protocol() -> None:
    payload = _instrument().to_dict()
    payload["core_graph_mode"] = "graph_free"

    with pytest.raises(QualificationContractError, match="not supported"):
        InstrumentSelection.from_dict(payload)


def test_closed_registry_rejects_family_alias_and_referent_alias() -> None:
    registry = _implementation_registry()
    with pytest.raises(QualificationContractError, match="generator family"):
        replace(registry, generator_family_id="cartesian-fourier-domain-v0-1")

    aliased_instrument = replace(
        _instrument(),
        referent_id="f2-local-covariant-section",
    )
    with pytest.raises(QualificationContractError, match="F2 representation"):
        replace(registry, instrument=aliased_instrument)


def test_protocol_rejects_control_to_case_swap_despite_closed_case_set() -> None:
    protocol = _protocol()
    first, second, *rest = protocol.selection.controls
    swapped = (
        replace(first, generator_case_id=second.generator_case_id),
        replace(second, generator_case_id=first.generator_case_id),
        *rest,
    )

    with pytest.raises(QualificationContractError, match="exactly join"):
        replace(
            protocol,
            selection=replace(protocol.selection, controls=swapped),
        )


def test_protocol_rejects_missing_or_relabelled_d2_confounder() -> None:
    protocol = _protocol()
    with pytest.raises(
        QualificationContractError,
        match="exact seed-free D2-only",
    ):
        replace(
            protocol,
            d2_core_confounders=protocol.d2_core_confounders[:-1],
        )
    with pytest.raises(
        QualificationContractError,
        match="exact seed-free D2-only",
    ):
        replace(
            protocol,
            d2_core_confounders=(
                replace(
                    protocol.d2_core_confounders[0],
                    construction_id="isolated-low-amplitude-alias-v0.1",
                ),
                *protocol.d2_core_confounders[1:],
            ),
        )


def test_single_all_stratum_cannot_replace_required_stress_strata() -> None:
    protocol = _protocol()
    all_primary = protocol.expected_strata[0].primary_unit_ids
    with pytest.raises(
        QualificationContractError,
        match="exact boundary, state-geometry-warp",
    ):
        replace(
            protocol,
            expected_strata=(
                ExpectedStratum(
                    stratum_id="all-cases",
                    evaluation_unit=EvaluationUnit.PHANTOM_INSTANCE,
                    required=True,
                    primary_unit_ids=all_primary,
                ),
            ),
        )


def test_cell_stress_membership_is_derived_not_self_declared() -> None:
    protocol = _protocol()
    first = protocol.expected_cells[0]
    tampered = replace(
        first,
        stratum_ids=first.stratum_ids[:-1],
    )
    cells = tuple(
        sorted(
            (tampered, *protocol.expected_cells[1:]),
            key=lambda item: item.cell_id,
        )
    )
    with pytest.raises(QualificationContractError, match="stress assignments"):
        replace(protocol, expected_cells=cells)


def test_oracle_and_graph_tolerances_have_strict_upper_bounds() -> None:
    thresholds = _protocol().thresholds
    with pytest.raises(
        QualificationContractError,
        match="loop_oracle_tolerance_cycles",
    ):
        replace(
            thresholds,
            loop_oracle_tolerance_cycles=(MAX_LOOP_ORACLE_TOLERANCE_CYCLES * 10.0),
        )
    with pytest.raises(
        QualificationContractError,
        match="graph_total_tolerance_cycles",
    ):
        replace(
            thresholds,
            graph_total_tolerance_cycles=(MAX_GRAPH_TOTAL_TOLERANCE_CYCLES * 10.0),
        )


def test_identifiability_and_field_effect_size_are_explicit_thresholds() -> None:
    thresholds = _protocol().thresholds
    payload = thresholds.to_dict()

    assert "rank_gap_floor" not in payload
    assert payload["identifiability_floor"] == 0.2
    assert payload["minimum_field_output_effect_size"] == 1e-6
    with pytest.raises(QualificationContractError, match="effect_size"):
        replace(thresholds, minimum_field_output_effect_size=0.0)


def test_positive_thresholds_have_meaningful_global_floors() -> None:
    thresholds = _protocol().thresholds
    for field, value in (
        ("identifiability_floor", MIN_IDENTIFIABILITY_FLOOR / 10.0),
        ("coherence_floor", MIN_COHERENCE_FLOOR / 10.0),
        ("branch_margin_rad", MIN_BRANCH_MARGIN_RAD / 10.0),
        (
            "minimum_field_output_effect_size",
            MIN_FIELD_OUTPUT_EFFECT_SIZE / 10.0,
        ),
    ):
        with pytest.raises(QualificationContractError, match=field):
            replace(thresholds, **{field: value})


def test_protocol_rejects_generator_invalid_numeric_commitments() -> None:
    protocol = _protocol()
    with pytest.raises(QualificationContractError, match="signed int64"):
        replace(protocol.selection, seeds=(1 << 63,))

    state_geometry_warp = replace(
        protocol.cartesian.state_geometry_warp_levels[0],
        value=0.9,
    )
    with pytest.raises(
        QualificationContractError,
        match="not executable by the closed generator",
    ):
        replace(
            protocol,
            cartesian=replace(
                protocol.cartesian,
                state_geometry_warp_levels=(state_geometry_warp,),
            ),
        )

    with pytest.raises(
        QualificationContractError,
        match="not executable by the closed generator",
    ):
        replace(
            protocol,
            cartesian=replace(
                protocol.cartesian,
                ambient_dimension=10_000_000,
            ),
        )


def test_protocol_rejects_vacuous_numeric_and_boundary_stress_aliases() -> None:
    cartesian = _protocol().cartesian
    with pytest.raises(QualificationContractError, match="distinct numeric"):
        replace(
            cartesian,
            structured_observation_perturbation_levels=(
                NumericStressLevel("nominal", 0.0),
                NumericStressLevel("stressed", 0.0),
            ),
        )
    central = cartesian.primary_boundaries[0]
    with pytest.raises(QualificationContractError, match="distinct geometries"):
        replace(
            cartesian,
            primary_boundaries=(
                central,
                replace(central, level="outer"),
            ),
        )
    with pytest.raises(QualificationContractError, match="offcore boundary geometry"):
        replace(
            cartesian,
            offcore_boundary=replace(
                central,
                level="offcore",
            ),
        )


def test_protocol_rejects_graph_k_larger_than_runtime_row_domain() -> None:
    protocol = _protocol()
    first, *rest = protocol.graphs.field_estimation
    oversized = replace(
        first,
        parameters=(("neighbor_count", protocol.cartesian.grid_side**2),),
    )
    with pytest.raises(
        QualificationContractError,
        match="smaller than the Cartesian row count",
    ):
        replace(
            protocol,
            graphs=replace(
                protocol.graphs,
                field_estimation=(oversized, *rest),
            ),
        )


def test_coverage_policy_is_fixed_all_cells_required() -> None:
    policy = _protocol().coverage_policy

    assert policy.all_expected_primary_units_must_pass is True
    assert policy.to_dict()["all_expected_primary_units_must_pass"] is True
    with pytest.raises(QualificationContractError, match="minimum_coverage"):
        replace(policy, minimum_coverage=0.99)
    with pytest.raises(
        QualificationContractError,
        match="maximum_abstention_fraction",
    ):
        replace(policy, maximum_abstention_fraction=0.01)


def test_protocol_volume_caps_are_aligned_with_result_and_event_contract() -> None:
    assert MAX_QUALIFICATION_RESULT_BYTES_BOUND == MAX_QUALIFICATION_RESULT_BYTES
    assert MAX_QUALIFICATION_PRIMARY_UNITS == 64
    assert MAX_QUALIFICATION_CORE_CELLS == 192
    assert MAX_QUALIFICATION_LOOP_CELLS == 1152
    assert MAX_QUALIFICATION_EVENT_LANES == 1344
    assert QUALIFICATION_EVENTS_PER_LANE == 6
    assert MAX_QUALIFICATION_EVENT_ENTRIES == 8064


def test_freeze_requires_loaded_canonical_protocol_and_no_overwrite(
    tmp_path: Path,
) -> None:
    loaded = _loaded_protocol(tmp_path)
    freeze = SelectionFreezeArtifact.from_loaded_protocol(
        freeze_id="selection-freeze-v0-1",
        loaded_protocol=loaded,
        seed_family_id="selection-family-a",
    )

    assert freeze.access_state is SelectionAccessState.UNOPENED
    assert freeze.attested_selection_values_observed is False
    assert freeze.attested_prior_selection_family_accessed is False
    assert freeze.attested_confirmation_accessed is False
    assert freeze.access_facts_are_external_attestations is True
    assert freeze.cryptographic_access_proof is False
    assert freeze.terminally_consumed is False
    assert freeze.reopen_authorized is False
    assert freeze.retry_authorized is False
    assert freeze.protocol_source_sha256 == loaded.source_sha256
    assert freeze.protocol_source_sha256 == freeze.protocol_canonical_sha256
    assert SelectionFreezeArtifact.from_dict(freeze.to_dict()) == freeze
    freeze.validate_loaded_protocol(loaded_protocol=loaded)

    path = tmp_path / "freeze.json"
    identity = write_selection_freeze(path, freeze)
    assert (
        load_selection_freeze(
            path,
            expected_source_sha256=identity.source_sha256,
            expected_canonical_sha256=identity.canonical_sha256,
            loaded_protocol=loaded,
        )
        == freeze
    )
    with pytest.raises(QualificationContractError, match="overwrite"):
        write_selection_freeze(path, freeze)
    with pytest.raises(
        QualificationContractError,
        match="canonical protocol source",
    ):
        replace(freeze, protocol_source_sha256=_digest("not-protocol-source"))


def test_failed_attempt_terminal_publication_is_typed_unique_and_reloadable(
    tmp_path: Path,
) -> None:
    loaded = _loaded_protocol(tmp_path)
    freeze = SelectionFreezeArtifact.from_loaded_protocol(
        freeze_id="selection-freeze-v0-1",
        loaded_protocol=loaded,
        seed_family_id="selection-family-a",
    )
    claim, claim_identity = claim_selection_attempt(
        tmp_path,
        claim_id="selection-attempt-claim-v0-1",
        freeze=freeze,
    )
    assert SelectionAttemptClaimArtifact.from_dict(claim.to_dict()) == claim
    claim.validate_freeze(freeze)
    assert (
        load_selection_attempt_claim(
            claim_identity.path,
            expected_source_sha256=claim_identity.source_sha256,
            expected_canonical_sha256=claim_identity.canonical_sha256,
            freeze=freeze,
        )
        == claim
    )
    assert (
        validate_persisted_selection_attempt_claim(
            tmp_path,
            freeze=freeze,
            attempt_claim=claim,
        )
        == claim
    )
    with pytest.raises(QualificationContractError, match="overwrite"):
        claim_selection_attempt(
            tmp_path,
            claim_id="second-selection-attempt-claim",
            freeze=freeze,
        )
    start, start_identity = begin_selection_execution(
        tmp_path,
        freeze=freeze,
        attempt_claim=claim,
    )
    assert start.selection_launch_authorization_sha256 is None
    assert start.authorized_head_commit is None
    assert SelectionExecutionStartArtifact.from_dict(start.to_dict()) == start
    assert (
        load_selection_execution_start(
            start_identity.path,
            expected_source_sha256=start_identity.source_sha256,
            expected_canonical_sha256=start_identity.canonical_sha256,
            freeze=freeze,
            attempt_claim=claim,
        )
        == start
    )
    with pytest.raises(QualificationContractError, match="overwrite"):
        begin_selection_execution(
            tmp_path,
            freeze=freeze,
            attempt_claim=claim,
        )

    failed = SelectionFailedAttemptArtifact.from_freeze(
        failed_attempt_id="failed-selection-attempt-v0-1",
        freeze=freeze,
        failure_stage="blind-input-generation",
        failure_evidence_sha256=_digest("failed-attempt-receipt"),
        attested_selection_values_observed=False,
    )
    assert failed.selection_launch_authorization_sha256 is None
    assert SelectionFailedAttemptArtifact.from_dict(failed.to_dict()) == failed
    failed.validate_freeze(freeze)

    consumption, identity = publish_terminal_selection_consumption(
        tmp_path,
        consumption_id="selection-consumption-v0-1",
        freeze=freeze,
        attempt_claim=claim,
        terminal_artifact=failed,
    )
    assert consumption.access_state is SelectionAccessState.TERMINALLY_CONSUMED
    assert consumption.attempt_number == 1
    assert consumption.terminally_consumed is True
    assert consumption.reopen_authorized is False
    assert consumption.retry_authorized is False
    assert consumption.attested_selection_values_observed is False
    assert consumption.protocol_source_sha256 == loaded.source_sha256
    assert consumption.protocol_canonical_sha256 == loaded.canonical_sha256
    assert SelectionConsumptionArtifact.from_dict(consumption.to_dict()) == consumption
    consumption.validate_freeze(freeze)
    consumption.validate_terminal_artifact(
        freeze=freeze,
        attempt_claim=claim,
        terminal_artifact=failed,
    )
    loaded_consumption, loaded_terminal = load_terminal_selection_consumption(
        identity.path,
        expected_manifest_sha256=identity.manifest_sha256,
        expected_terminal_artifact_sha256=(identity.terminal_artifact_sha256),
        expected_consumption_sha256=identity.consumption_sha256,
        freeze=freeze,
        attempt_claim=claim,
    )
    assert loaded_consumption == consumption
    assert loaded_terminal == failed
    assert {item.name for item in identity.path.iterdir()} == {
        "terminal-artifact.json",
        "selection-consumption.json",
        "terminal-manifest.json",
    }
    assert (
        identity.path.joinpath("terminal-artifact.json").read_bytes()
        == failed.canonical_bytes
    )
    assert (
        identity.path.joinpath("selection-consumption.json").read_bytes()
        == consumption.canonical_bytes
    )
    with pytest.raises(QualificationContractError, match="overwrite"):
        publish_terminal_selection_consumption(
            tmp_path,
            consumption_id="second-terminal-attempt",
            freeze=freeze,
            attempt_claim=claim,
            terminal_artifact=failed,
        )


def test_store_attempt_identity_ignores_freeze_and_seed_family_labels(
    tmp_path: Path,
) -> None:
    loaded = _loaded_protocol(tmp_path)
    first = SelectionFreezeArtifact.from_loaded_protocol(
        freeze_id="selection-freeze-label-a",
        loaded_protocol=loaded,
        seed_family_id="selection-family-label-a",
    )
    relabeled = SelectionFreezeArtifact.from_loaded_protocol(
        freeze_id="selection-freeze-label-b",
        loaded_protocol=loaded,
        seed_family_id="selection-family-label-b",
    )

    assert first.canonical_sha256 != relabeled.canonical_sha256
    assert selection_attempt_key_sha256(first) == selection_attempt_key_sha256(
        relabeled
    )
    claim_selection_attempt(
        tmp_path,
        claim_id="selection-attempt-label-a",
        freeze=first,
    )
    persisted = selection_freeze_store_path(tmp_path, first)
    assert persisted.read_bytes() == first.canonical_bytes
    assert selection_freeze_store_path(tmp_path, relabeled) == persisted

    with pytest.raises(
        QualificationContractError,
        match="persisted selection freeze differs",
    ):
        claim_selection_attempt(
            tmp_path,
            claim_id="selection-attempt-label-b",
            freeze=relabeled,
        )


def test_terminal_publish_exclusive_rename_rejects_empty_directory_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded = _loaded_protocol(tmp_path)
    freeze = SelectionFreezeArtifact.from_loaded_protocol(
        freeze_id="exclusive-rename-freeze",
        loaded_protocol=loaded,
        seed_family_id="exclusive-rename-family",
    )
    claim, _claim_identity = claim_selection_attempt(
        tmp_path,
        claim_id="exclusive-rename-claim",
        freeze=freeze,
    )
    begin_selection_execution(
        tmp_path,
        freeze=freeze,
        attempt_claim=claim,
    )
    failed = SelectionFailedAttemptArtifact.from_freeze(
        failed_attempt_id="exclusive-rename-failure",
        freeze=freeze,
        failure_stage="exclusive-rename-race",
        failure_evidence_sha256=_digest("exclusive-rename-race"),
        attested_selection_values_observed=False,
    )
    destination = qualification_freeze.terminal_selection_transaction_path(
        tmp_path,
        freeze,
    )
    real_rename = qualification_freeze._rename_directory_no_replace

    def create_empty_destination_then_rename(
        source: Path,
        target: Path,
    ) -> None:
        assert target == destination
        target.mkdir()
        real_rename(source, target)

    monkeypatch.setattr(
        qualification_freeze,
        "_rename_directory_no_replace",
        create_empty_destination_then_rename,
    )
    with pytest.raises(QualificationContractError, match="refusing to overwrite"):
        publish_terminal_selection_consumption(
            tmp_path,
            consumption_id="exclusive-rename-consumption",
            freeze=freeze,
            attempt_claim=claim,
            terminal_artifact=failed,
        )
    assert destination.is_dir()
    assert tuple(destination.iterdir()) == ()


def test_terminal_consumption_rejects_untyped_digest_and_false_result_access(
    tmp_path: Path,
) -> None:
    freeze = SelectionFreezeArtifact.from_loaded_protocol(
        freeze_id="selection-freeze-v0-1",
        loaded_protocol=_loaded_protocol(tmp_path),
        seed_family_id="selection-family-a",
    )
    claim = SelectionAttemptClaimArtifact.from_freeze(
        claim_id="selection-attempt-claim-v0-1",
        freeze=freeze,
    )
    with pytest.raises(TypeError, match="terminal_artifact"):
        SelectionConsumptionArtifact.consume(
            consumption_id="arbitrary-digest",
            freeze=freeze,
            attempt_claim=claim,
            terminal_artifact=_digest("not-a-terminal-artifact"),
        )
    failed = SelectionFailedAttemptArtifact.from_freeze(
        failed_attempt_id="failed-selection-attempt-v0-1",
        freeze=freeze,
        failure_stage="protocol-verification",
        failure_evidence_sha256=_digest("failed-attempt-receipt"),
        attested_selection_values_observed=False,
    )
    consumption = SelectionConsumptionArtifact.consume(
        consumption_id="failed-selection-attempt-v0-1",
        freeze=freeze,
        attempt_claim=claim,
        terminal_artifact=failed,
    )
    with pytest.raises(
        QualificationContractError,
        match="requires observed selection values",
    ):
        replace(
            consumption,
            terminal_artifact_kind=TerminalAttemptArtifactKind.RESULT,
        )
    with pytest.raises(QualificationContractError, match="attempt_number"):
        replace(consumption, attempt_number=2)


def test_terminal_publication_requires_the_persisted_pre_run_claim(
    tmp_path: Path,
) -> None:
    freeze = SelectionFreezeArtifact.from_loaded_protocol(
        freeze_id="selection-freeze-v0-1",
        loaded_protocol=_loaded_protocol(tmp_path),
        seed_family_id="selection-family-a",
    )
    unpersisted_claim = SelectionAttemptClaimArtifact.from_freeze(
        claim_id="unpersisted-selection-attempt-claim",
        freeze=freeze,
    )
    failed = SelectionFailedAttemptArtifact.from_freeze(
        failed_attempt_id="failed-selection-attempt-v0-1",
        freeze=freeze,
        failure_stage="protocol-verification",
        failure_evidence_sha256=_digest("failed-attempt-receipt"),
        attested_selection_values_observed=False,
    )

    with pytest.raises(
        QualificationContractError,
        match="cannot read persisted selection freeze",
    ):
        publish_terminal_selection_consumption(
            tmp_path,
            consumption_id="selection-consumption-v0-1",
            freeze=freeze,
            attempt_claim=unpersisted_claim,
            terminal_artifact=failed,
        )


def test_terminal_publication_requires_atomic_execution_start(
    tmp_path: Path,
) -> None:
    freeze = SelectionFreezeArtifact.from_loaded_protocol(
        freeze_id="selection-freeze-v0-1",
        loaded_protocol=_loaded_protocol(tmp_path),
        seed_family_id="selection-family-a",
    )
    claim, _identity = claim_selection_attempt(
        tmp_path,
        claim_id="selection-attempt-claim-v0-1",
        freeze=freeze,
    )
    failed = SelectionFailedAttemptArtifact.from_freeze(
        failed_attempt_id="failed-selection-attempt-v0-1",
        freeze=freeze,
        failure_stage="protocol-verification",
        failure_evidence_sha256=_digest("failed-attempt-receipt"),
        attested_selection_values_observed=False,
    )

    with pytest.raises(
        QualificationContractError,
        match="cannot read selection execution-start artifact",
    ):
        publish_terminal_selection_consumption(
            tmp_path,
            consumption_id="selection-consumption-v0-1",
            freeze=freeze,
            attempt_claim=claim,
            terminal_artifact=failed,
        )


def test_freeze_external_access_attestations_are_constant_false(
    tmp_path: Path,
) -> None:
    freeze = SelectionFreezeArtifact.from_loaded_protocol(
        freeze_id="selection-freeze-v0-1",
        loaded_protocol=_loaded_protocol(tmp_path),
        seed_family_id="selection-family-a",
    )
    payload = freeze.to_dict()
    payload["attested_prior_selection_family_accessed"] = True

    with pytest.raises(
        QualificationContractError,
        match="attested_prior_selection_family_accessed",
    ):
        SelectionFreezeArtifact.from_dict(payload)


def test_seed_family_commitment_is_order_sensitive_and_requires_canonical_order() -> (
    None
):
    first = seed_family_commitment_sha256(
        seed_family_id="selection-family-a",
        seeds=(101, 202),
    )
    assert first == seed_family_commitment_sha256(
        seed_family_id="selection-family-a",
        seeds=(101, 202),
    )
    with pytest.raises(QualificationContractError, match="canonical order"):
        seed_family_commitment_sha256(
            seed_family_id="selection-family-a",
            seeds=(202, 101),
        )
