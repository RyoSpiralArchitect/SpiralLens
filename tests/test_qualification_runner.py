from __future__ import annotations

import runpy
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

import spirallens.qualification.runner as qualification_runner
import spirallens.qualification.source_binding as qualification_source_binding
from spirallens.core.canonical import canonical_json_sha256
from spirallens.qualification.common import (
    AttemptStatus,
    CorePredictionClass,
    LoopPredictionClass,
    QualificationContractError,
    QualificationState,
)
from spirallens.qualification.contracts import (
    MAX_QUALIFICATION_RESULT_BYTES,
    QualificationGateId,
    QualificationResult,
    build_qualification_lane_event_payloads,
    derive_static_gate,
    qualification_result_evidence_root_sha256,
)
from spirallens.qualification.crossed import (
    domain_construction_sha256,
    support_construction_sha256,
)
from spirallens.qualification.freeze import (
    MAX_SELECTION_TERMINAL_ARTIFACT_BYTES,
    SelectionAttemptClaimArtifact,
    SelectionConsumptionArtifact,
    SelectionFreezeArtifact,
    claim_selection_attempt,
    load_terminal_selection_consumption,
    publish_terminal_selection_consumption,
    selection_execution_start_path,
)
from spirallens.qualification.persistence import LoadedQualificationProtocol
from spirallens.qualification.protocol import (
    MAX_QUALIFICATION_PRIMARY_UNITS,
    BoundaryTemplate,
    EngineBinding,
    ModuleDigest,
    QualificationProtocol,
)
from spirallens.qualification.runner import (
    REQUIRED_ENGINE_MODULES,
    _expected_sampled_cycles,
    module_source_sha256,
    run_calibration_selection,
)
from spirallens.qualification.source_binding import (
    ModuleSourceReceipt,
    QualificationEventKind,
    QualificationEventLedger,
    QualificationSourceBindingError,
    QualificationSourceBindingReceipt,
    ReferentSourceReceipt,
    RegistrySourceReceipt,
    module_repository_path,
    qualification_event_lane_ids,
)
from spirallens.synthetic.cartesian_fourier_domain_phantom import (
    CartesianFourierDomainGenerator,
    CartesianFourierDomainSpec,
)


def _development_protocol() -> QualificationProtocol:
    """Reuse the exact hardened manifest and bind it to live runner sources."""

    namespace = runpy.run_path(
        Path(__file__).with_name("test_qualification_protocol_hardening.py")
    )
    protocol = namespace["_protocol"]()
    assert isinstance(protocol, QualificationProtocol)
    modules = tuple(
        ModuleDigest(module, module_source_sha256(module))
        for module in sorted(REQUIRED_ENGINE_MODULES)
    )
    return replace(
        protocol,
        engine=EngineBinding(
            repository=protocol.engine.repository,
            commit=protocol.engine.commit,
            modules=modules,
        ),
        domain=replace(
            protocol.domain,
            domain_construction_sha256=domain_construction_sha256(),
            support_construction_sha256=support_construction_sha256(),
        ),
        cartesian=replace(
            protocol.cartesian,
            offcore_boundary=BoundaryTemplate("offcore", 0, 0, 1, 1),
        ),
    )


def _loaded_protocol(
    protocol: QualificationProtocol,
) -> LoadedQualificationProtocol:
    return LoadedQualificationProtocol(
        protocol=protocol,
        source_path=Path("/tmp/spirallens-development-protocol.json"),
        source_bytes=protocol.canonical_bytes,
        source_sha256=protocol.canonical_sha256,
        canonical_sha256=protocol.canonical_sha256,
    )


def _source_binding(
    protocol: QualificationProtocol,
) -> QualificationSourceBindingReceipt:
    modules = tuple(
        ModuleSourceReceipt(
            module=item.module,
            repository_path=module_repository_path(item.module),
            declared_sha256=item.sha256,
            working_sha256=item.sha256,
            head_blob_sha256=item.sha256,
            bound_blob_sha256=item.sha256,
        )
        for item in protocol.engine.modules
    )
    return QualificationSourceBindingReceipt(
        engine=protocol.engine,
        registry=protocol.registry,
        head_commit=protocol.engine.commit,
        modules=modules,
        hypothesis_registry=RegistrySourceReceipt(
            repository_path="protocols/development-registry.yaml",
            source_sha256=protocol.registry.registry_source_sha256,
            canonical_sha256=protocol.registry.registry_canonical_sha256,
        ),
        referent_contracts=ReferentSourceReceipt(
            repository_path="protocols/development-referents.json",
            source_sha256=protocol.registry.referent_canonical_sha256,
            canonical_sha256=protocol.registry.referent_canonical_sha256,
            hypothesis_registry_canonical_sha256=(
                protocol.registry.registry_canonical_sha256
            ),
        ),
    )


def _freeze(
    loaded: LoadedQualificationProtocol,
) -> SelectionFreezeArtifact:
    return SelectionFreezeArtifact.from_loaded_protocol(
        freeze_id="qualification-development-freeze",
        loaded_protocol=loaded,
        seed_family_id="qualification-development-seeds",
    )


def _reroot_result_with_d1_runtime(
    result: QualificationResult,
    protocol: QualificationProtocol,
    replacement_runtime: object,
) -> QualificationResult:
    runtime_receipts = tuple(
        replacement_runtime
        if item.evidence_id == replacement_runtime.evidence_id  # type: ignore[attr-defined]
        else item
        for item in result.evidence_bundle.static_runtime_receipts
    )
    evidence_bundle = replace(
        result.evidence_bundle,
        static_runtime_receipts=runtime_receipts,
    )
    by_id = {item.evidence_id: item for item in runtime_receipts}
    gate_evidence, static_receipts = qualification_runner._static_evidence(
        protocol=protocol,
        source_binding=result.source_binding,
        d1_cartesian=by_id["cartesian-fourier-family-verified"],
        d1_representation=by_id["representation-family-verified"],
        d3_cartesian=by_id["cartesian-gauge-pipeline-rerun-verified"],
        d3_representation=by_id["representation-gauge-pipeline-rerun-verified"],
    )
    gates = (
        derive_static_gate(QualificationGateId.D0, gate_evidence),
        derive_static_gate(QualificationGateId.D1, gate_evidence),
        result.gate_results[2],
        derive_static_gate(QualificationGateId.D3, gate_evidence),
        result.gate_results[4],
        result.gate_results[5],
    )
    evidence_root = qualification_result_evidence_root_sha256(
        result_id=result.result_id,
        protocol_id=result.protocol_id,
        protocol_source_sha256=result.protocol_source_sha256,
        protocol_canonical_sha256=result.protocol_canonical_sha256,
        selection_freeze_artifact_sha256=(result.selection_freeze_artifact_sha256),
        selection_attempt_claim_sha256=(result.selection_attempt_claim_sha256),
        source_binding=result.source_binding,
        evidence_bundle=evidence_bundle,
        gate_results=gates,
        gate_evidence=gate_evidence,
        static_evidence_receipts=static_receipts,
        core_primary_units=result.core_primary_units,
        core_cells=result.core_cells,
        primary_units=result.primary_units,
        crossed_cells=result.crossed_cells,
        crossed_nonvacuity=result.crossed_nonvacuity,
        strata=result.strata,
    )
    core_primaries = {item.primary_unit_id: item for item in result.core_primary_units}
    loop_primaries = {item.primary_unit_id: item for item in result.primary_units}
    nonvacuity = {item.primary_unit_id: item for item in result.crossed_nonvacuity}
    core_cells = {f"core.{item.core_cell_id}": item for item in result.core_cells}
    loop_cells = {f"loop.{item.cell_id}": item for item in result.crossed_cells}
    ledger = QualificationEventLedger.create(qualification_event_lane_ids(protocol))
    for lane_id in ledger.expected_lane_ids:
        if lane_id.startswith("core."):
            cell = core_cells[lane_id]
            primary = core_primaries[cell.primary_unit_id]
            cell_nonvacuity = None
        else:
            cell = loop_cells[lane_id]
            primary = loop_primaries[cell.primary_unit_id]
            cell_nonvacuity = nonvacuity[cell.primary_unit_id]
        for payload in build_qualification_lane_event_payloads(
            protocol=protocol,
            protocol_source_sha256=result.protocol_source_sha256,
            source_binding=result.source_binding,
            selection_freeze_artifact_sha256=(result.selection_freeze_artifact_sha256),
            selection_attempt_claim_sha256=(result.selection_attempt_claim_sha256),
            result_id=result.result_id,
            result_evidence_root_sha256=evidence_root,
            cell=cell,
            primary=primary,
            nonvacuity=cell_nonvacuity,
            strata=result.strata,
        ):
            ledger = ledger.append(
                lane_id=lane_id,
                event_kind=payload.event_kind,
                payload=payload,
            )
    return replace(
        result,
        evidence_bundle=evidence_bundle,
        result_evidence_root_sha256=evidence_root,
        event_ledger_receipt=ledger.receipt(),
        gate_results=gates,
        gate_evidence=gate_evidence,
        static_evidence_receipts=static_receipts,
    )


def _tamper_cartesian_d1_runtime(
    result: QualificationResult,
    tamper_kind: str,
) -> object:
    family = next(
        item
        for item in result.evidence_bundle.static_runtime_receipts
        if item.evidence_id == "cartesian-fourier-family-verified"
    )
    cases = list(family.cases)
    case = cases[0]
    metrics = list(case.numeric_metric_receipts)
    metric = metrics[0]
    if tamper_kind == "threshold":
        metrics[0] = replace(metric, threshold=metric.threshold * 2.0)
        cases[0] = replace(case, numeric_metric_receipts=tuple(metrics))
        return replace(family, cases=tuple(cases))
    if tamper_kind == "comparator":
        metrics[0] = replace(
            metric,
            comparator="at-least",
            passed=metric.observed_value >= metric.threshold,
        )
        cases[0] = replace(case, numeric_metric_receipts=tuple(metrics))
        return replace(family, cases=tuple(cases))
    if tamper_kind == "observed":
        metrics[0] = replace(
            metric,
            observed_value=metric.threshold / 2.0,
            passed=True,
        )
        cases[0] = replace(case, numeric_metric_receipts=tuple(metrics))
        return replace(family, cases=tuple(cases))
    if tamper_kind == "output-fingerprint":
        outputs = list(case.estimator_output_receipts)
        output = dict(outputs[0])
        output["output_sha256"] = "f" * 64
        outputs[0] = output
        output_fingerprint = canonical_json_sha256(output)
        graph_fingerprint = output["field_graph_fingerprint_sha256"]
        metrics = [
            replace(
                item,
                estimator_output_sha256=output_fingerprint,
            )
            if item.field_graph_fingerprint_sha256 == graph_fingerprint
            else item
            for item in metrics
        ]
        cases[0] = replace(
            case,
            estimator_output_receipts=tuple(outputs),
            numeric_metric_receipts=tuple(metrics),
        )
        return replace(family, cases=tuple(cases))
    if tamper_kind == "oracle-fingerprint":
        forged_oracle = "e" * 64
        generator_case = dict(case.generator_case_receipt)
        generator_case["oracle_truth_fingerprint_sha256"] = forged_oracle
        metrics = [
            replace(item, oracle_fingerprint_sha256=forged_oracle) for item in metrics
        ]
        cases[0] = replace(
            case,
            generator_case_receipt=generator_case,
            numeric_metric_receipts=tuple(metrics),
        )
        generator_family = deepcopy(family.generator_family_receipt)
        generator_cases = generator_family["cases"]
        assert isinstance(generator_cases, list)
        for item in generator_cases:
            if isinstance(item, dict) and item["case_id"] == case.case_id:
                item["oracle_truth_fingerprint_sha256"] = forged_oracle
        return replace(
            family,
            generator_family_receipt=generator_family,
            cases=tuple(cases),
        )
    raise AssertionError(f"unknown D1 tamper kind: {tamper_kind}")


def test_runner_executes_exact_development_manifest_and_full_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    protocol = _development_protocol()
    loaded = _loaded_protocol(protocol)
    source_binding = _source_binding(protocol)
    monkeypatch.setattr(
        qualification_runner,
        "verify_protocol_source_binding",
        lambda *_args, **_kwargs: source_binding,
    )
    freeze = _freeze(loaded)
    attempt_claim, _identity = claim_selection_attempt(
        tmp_path,
        claim_id="qualification-development-attempt",
        freeze=freeze,
    )
    observed_seeds: list[int] = []
    original_generate = CartesianFourierDomainGenerator.generate

    def record_generate(
        self: CartesianFourierDomainGenerator,
        spec: object,
    ):
        observed_seeds.append(spec.seed)  # type: ignore[attr-defined]
        return original_generate(self, spec)  # type: ignore[arg-type]

    monkeypatch.setattr(
        CartesianFourierDomainGenerator,
        "generate",
        record_generate,
    )
    result = run_calibration_selection(
        loaded,
        source_binding_receipt=source_binding,
        selection_freeze_artifact=freeze,
        attempt_claim=attempt_claim,
        attempt_store_directory=tmp_path,
    )

    assert set(observed_seeds) == {101, 314159}
    assert len(result.core_cells) == len(protocol.expected_core_cells) == 12
    assert len(result.crossed_cells) == len(protocol.expected_cells) == 72
    assert result.event_ledger_receipt.event_count == 84 * len(QualificationEventKind)
    assert (
        result.event_ledger_receipt.posthoc_logical_dependency_manifest_validated
        is True
    )
    assert result.selection_attempt_claim_sha256 == attempt_claim.canonical_sha256
    assert (
        result.evidence_bundle.selection_attempt_claim_sha256
        == attempt_claim.canonical_sha256
    )
    assert len(result.evidence_bundle.core_cell_receipts) == 12
    assert len(result.evidence_bundle.loop_cell_receipts) == 72
    assert len(result.evidence_bundle.nonvacuity_receipts) == 4
    assert len(result.evidence_bundle.static_runtime_receipts) == 4
    assert result.p0_winner_selected is False
    assert result.representation_d2_d5_qualified is False
    assert result.localized_core_loop_join_established is False
    d2_confounders = result.evidence_bundle.d2_confounder_matrix_receipt
    assert d2_confounders.state is QualificationState.PASS
    assert len(d2_confounders.cells) == 6
    assert d2_confounders.failed_cell_ids == ()
    assert d2_confounders.selection_seed_consumed is False
    assert d2_confounders.oracle_scoring_used is False
    assert d2_confounders.joint_loop_registry_consumed is False
    identifiability_decoys = tuple(
        cell
        for cell in d2_confounders.cells
        if cell.confounder_id == "high-amplitude-local-identifiability-loss-decoy"
    )
    sparse = tuple(
        cell
        for cell in d2_confounders.cells
        if cell.confounder_id == "low-amplitude-missing-candidate-support-abstain"
    )
    assert len(identifiability_decoys) == len(sparse) == 3
    assert all(
        cell.sealed_prediction_receipt["observed_attempt_status"]
        == AttemptStatus.EVALUABLE.value
        and cell.sealed_prediction_receipt["prediction_class"]
        == CorePredictionClass.NO_CORE.value
        and cell.sealed_prediction_receipt["reason_codes"] == []
        and cell.construction_observation["core_amplitude_threshold_satisfied"] is False
        and cell.construction_observation["direction_loss_threshold_satisfied"] is True
        and cell.construction_observation["measurement_support_threshold_satisfied"]
        is True
        for cell in identifiability_decoys
    )
    assert all(
        cell.sealed_prediction_receipt["observed_attempt_status"]
        == AttemptStatus.INSUFFICIENT.value
        and cell.sealed_prediction_receipt["prediction_class"]
        == CorePredictionClass.ABSTAIN.value
        and cell.sealed_prediction_receipt["reason_codes"]
        == ["candidate_measurement_support_below_minimum"]
        and cell.construction_observation["direction_loss_threshold_satisfied"] is True
        and cell.construction_observation["measurement_support_threshold_satisfied"]
        is False
        for cell in sparse
    )
    with pytest.raises(
        QualificationContractError,
        match="exact confounder x A matrix",
    ):
        replace(d2_confounders, cells=d2_confounders.cells[:-1])
    with pytest.raises(
        QualificationContractError,
        match="exact truth-blind behavior",
    ):
        replace(
            identifiability_decoys[0],
            expected_prediction_class=CorePredictionClass.LOCALIZED_CORE,
        )
    representation_d3 = next(
        receipt
        for receipt in result.evidence_bundle.static_runtime_receipts
        if receipt.evidence_id == "representation-gauge-pipeline-rerun-verified"
    )
    assert len(representation_d3.aggregate_runtime_receipt["pipeline_checks"]) == 3
    assert len(representation_d3.aggregate_runtime_receipt["all_algebraic_checks"]) == 7

    core_by_control = {item.control_id: item for item in result.core_primary_units}
    loop_by_control = {item.control_id: item for item in result.primary_units}
    assert (
        core_by_control["fixed-null-core"].prediction_class
        is CorePredictionClass.LOCALIZED_CORE
    )
    assert (
        loop_by_control["fixed-null-core"].prediction_class is LoopPredictionClass.NULL
    )
    assert (
        core_by_control["null-no-core"].prediction_class is CorePredictionClass.NO_CORE
    )
    assert core_by_control["prerequisite"].attempt_status is AttemptStatus.INSUFFICIENT
    assert (
        core_by_control["prerequisite"].prediction_class is CorePredictionClass.ABSTAIN
    )
    assert loop_by_control["prerequisite"].attempt_status is AttemptStatus.INSUFFICIENT
    assert (
        loop_by_control["prerequisite"].prediction_class is LoopPredictionClass.ABSTAIN
    )
    assert core_by_control["prerequisite"].state is QualificationState.PASS
    assert loop_by_control["prerequisite"].state is QualificationState.PASS

    sentinel = next(
        item for item in result.crossed_nonvacuity if item.control_id == "nonzero-core"
    )
    assert sentinel.state is QualificationState.PASS
    assert (
        sentinel.maximum_pairwise_substantive_output_distance
        >= protocol.thresholds.minimum_field_output_effect_size
    )
    assert sentinel.field_output_variant_count >= 2
    assert len(result.canonical_bytes) <= MAX_QUALIFICATION_RESULT_BYTES
    # The four-primary development result is deliberately a conservative
    # linear envelope: multiplying its complete bytes by the maximum primary
    # count over the observed primary count overestimates the audited
    # 64-primary result (19,964,272 bytes).  Keep both persistence caps above
    # that closed-protocol envelope as result schemas evolve.
    primary_scale = MAX_QUALIFICATION_PRIMARY_UNITS // len(result.primary_units)
    projected_maximum_bytes = len(result.canonical_bytes) * primary_scale
    assert projected_maximum_bytes < MAX_QUALIFICATION_RESULT_BYTES
    assert MAX_SELECTION_TERMINAL_ARTIFACT_BYTES == MAX_QUALIFICATION_RESULT_BYTES
    assert QualificationResult.from_dict(result.to_dict()) == result
    tampered = deepcopy(result.to_dict())
    bundle_document = tampered["evidence_bundle"]
    assert isinstance(bundle_document, dict)
    runtime_receipts = bundle_document["static_runtime_receipts"]
    assert isinstance(runtime_receipts, list)
    cartesian_d3_document = next(
        item
        for item in runtime_receipts
        if isinstance(item, dict)
        and item.get("evidence_id") == "cartesian-gauge-pipeline-rerun-verified"
    )
    aggregate_document = cartesian_d3_document["aggregate_runtime_receipt"]
    assert isinstance(aggregate_document, dict)
    aggregate_checks = aggregate_document["checks"]
    assert isinstance(aggregate_checks, list)
    aggregate_checks.append(deepcopy(aggregate_checks[0]))
    with pytest.raises(
        QualificationContractError,
        match="exact closed pipeline-check sequence",
    ):
        QualificationResult.from_dict(tampered)
    result.validate_against_protocol(
        protocol,
        protocol_source_sha256=loaded.source_sha256,
        source_binding_receipt=source_binding,
        selection_freeze_artifact=freeze,
        selection_attempt_claim=attempt_claim,
    )
    assert (
        tuple(gate.state for gate in result.gate_results)
        == (QualificationState.PASS,) * 6
    )
    wrong_claim = SelectionAttemptClaimArtifact.from_freeze(
        claim_id="qualification-wrong-attempt",
        freeze=freeze,
    )
    with pytest.raises(
        QualificationContractError,
        match="exact execution companions",
    ):
        SelectionConsumptionArtifact.consume(
            consumption_id="qualification-wrong-consumption",
            freeze=freeze,
            attempt_claim=wrong_claim,
            terminal_artifact=result,
        )
    with pytest.raises(
        QualificationContractError,
        match="full loaded protocol",
    ):
        publish_terminal_selection_consumption(
            tmp_path,
            consumption_id="qualification-missing-terminal-companions",
            freeze=freeze,
            attempt_claim=attempt_claim,
            terminal_artifact=result,
        )
    monkeypatch.setattr(
        qualification_source_binding,
        "verify_protocol_source_binding_successor",
        lambda *_args, **_kwargs: source_binding,
    )
    consumption, terminal_identity = publish_terminal_selection_consumption(
        tmp_path,
        consumption_id="qualification-terminal-consumption",
        freeze=freeze,
        attempt_claim=attempt_claim,
        terminal_artifact=result,
        loaded_protocol=loaded,
        repository_root=Path.cwd(),
        registry_path=source_binding.hypothesis_registry.repository_path,
        referent_path=source_binding.referent_contracts.repository_path,
    )
    loaded_consumption, loaded_result = load_terminal_selection_consumption(
        terminal_identity.path,
        expected_manifest_sha256=terminal_identity.manifest_sha256,
        expected_terminal_artifact_sha256=(terminal_identity.terminal_artifact_sha256),
        expected_consumption_sha256=terminal_identity.consumption_sha256,
        freeze=freeze,
        attempt_claim=attempt_claim,
        loaded_protocol=loaded,
        repository_root=Path.cwd(),
        registry_path=source_binding.hypothesis_registry.repository_path,
        referent_path=source_binding.referent_contracts.repository_path,
    )
    assert loaded_consumption == consumption
    assert loaded_result == result


def test_d1_validation_rejects_fully_rerooted_numeric_tampering(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    protocol = _development_protocol()
    loaded = _loaded_protocol(protocol)
    source_binding = _source_binding(protocol)
    monkeypatch.setattr(
        qualification_runner,
        "verify_protocol_source_binding",
        lambda *_args, **_kwargs: source_binding,
    )
    freeze = _freeze(loaded)
    attempt_claim, _identity = claim_selection_attempt(
        tmp_path,
        claim_id="qualification-d1-adversarial-attempt",
        freeze=freeze,
    )
    result = run_calibration_selection(
        loaded,
        source_binding_receipt=source_binding,
        selection_freeze_artifact=freeze,
        attempt_claim=attempt_claim,
        attempt_store_directory=tmp_path,
    )

    expected_errors = {
        "threshold": "comparator or threshold differs",
        "comparator": "comparator or threshold differs",
        "observed": "current-engine recomputation",
        "output-fingerprint": "current-engine recomputation",
        "oracle-fingerprint": "current-engine recomputation",
    }
    for tamper_kind, expected_error in expected_errors.items():
        forged = _reroot_result_with_d1_runtime(
            result,
            protocol,
            _tamper_cartesian_d1_runtime(result, tamper_kind),
        )
        assert forged.result_evidence_root_sha256 != result.result_evidence_root_sha256
        assert (
            forged.event_ledger_receipt.chain_head_sha256
            != result.event_ledger_receipt.chain_head_sha256
        )
        with pytest.raises(
            QualificationContractError,
            match=expected_error,
        ):
            forged.validate_against_protocol(
                protocol,
                protocol_source_sha256=loaded.source_sha256,
                source_binding_receipt=source_binding,
                selection_freeze_artifact=freeze,
                selection_attempt_claim=attempt_claim,
            )


def test_fixed_development_d1_rerun_does_not_consume_selection_seeds() -> None:
    protocol = _development_protocol()
    cartesian, representation = qualification_runner.recompute_fixed_development_d1(
        protocol
    )
    development_seed = qualification_runner.REPRESENTATION_METAMORPHIC_DEVELOPMENT_SEED

    assert cartesian.generator_family_receipt["spec"]["seed"] == development_seed
    assert representation.generator_family_receipt["spec"]["seed"] == development_seed
    assert development_seed not in protocol.selection.seeds


def test_representation_d3_runs_and_revalidates_all_signed_loop_laws() -> None:
    protocol = _development_protocol()
    d1_evidence = qualification_runner._run_representation_family(protocol)
    receipt = qualification_runner._run_representation_metamorphic(
        protocol,
        d1_evidence,
    ).runtime_receipt
    aggregate = receipt.aggregate_runtime_receipt
    pipeline_checks = aggregate["pipeline_checks"]
    variants = aggregate["loop_variant_checks"]
    assert isinstance(pipeline_checks, list)
    assert isinstance(variants, list)
    assert len(pipeline_checks) == 3
    assert len(variants) == 27
    assert receipt.pipeline_rerun_count == 18
    assert aggregate["field_pipeline_execution_count"] == 2
    assert aggregate["crossed_loop_cell_count"] == 9
    assert aggregate["loop_variant_rerun_count"] == 27
    assert aggregate["sealed_loop_prediction_count"] == 45

    crossed = [
        loop for pipeline in pipeline_checks for loop in pipeline["crossed_loop_checks"]
    ]
    assert len(crossed) == 9
    assert all(pipeline["alignment_determinant"] < 0.0 for pipeline in pipeline_checks)
    assert all(loop["base_signed_total_cycles"] == 1.0 for loop in crossed)
    assert all(loop["transformed_signed_total_cycles"] == -1.0 for loop in crossed)
    assert all(loop["signed_total_error_cycles"] == 0.0 for loop in crossed)

    totals_by_law = {
        law: {
            item["transformed_signed_total_cycles"]
            for item in variants
            if item["law"] == law
        }
        for law in (
            "reference_rotation",
            "reference_reflection",
            "loop_reversal",
        )
    }
    assert totals_by_law == {
        "reference_rotation": {1.0},
        "reference_reflection": {-1.0},
        "loop_reversal": {-1.0},
    }
    assert type(receipt).from_dict(receipt.to_dict()) == receipt

    determinant_tamper = deepcopy(receipt.to_dict())
    determinant_aggregate = determinant_tamper["aggregate_runtime_receipt"]
    assert isinstance(determinant_aggregate, dict)
    determinant_pipelines = determinant_aggregate["pipeline_checks"]
    assert isinstance(determinant_pipelines, list)
    determinant_pipelines[0]["alignment_determinant"] = 1.0
    with pytest.raises(
        QualificationContractError,
        match="declared O\\(2\\) transform",
    ):
        type(receipt).from_dict(determinant_tamper)

    signed_total_tamper = deepcopy(receipt.to_dict())
    total_aggregate = signed_total_tamper["aggregate_runtime_receipt"]
    assert isinstance(total_aggregate, dict)
    total_variants = total_aggregate["loop_variant_checks"]
    assert isinstance(total_variants, list)
    total_variants[1]["transformed_signed_total_cycles"] = 1.0
    with pytest.raises(
        QualificationContractError,
        match="transformed_signed_total_cycles",
    ):
        type(receipt).from_dict(signed_total_tamper)


def test_representation_d3_rejects_a_procrustes_hidden_loop_sign_fault(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol = _development_protocol()
    d1_evidence = qualification_runner._run_representation_family(protocol)
    original_estimate = qualification_runner.estimate_and_seal_loop

    def unsigned_total(*args: object, **kwargs: object):
        prediction = original_estimate(*args, **kwargs)
        if prediction.signed_total_cycles is not None:
            object.__setattr__(
                prediction,
                "signed_total_cycles",
                abs(prediction.signed_total_cycles),
            )
        return prediction

    monkeypatch.setattr(
        qualification_runner,
        "estimate_and_seal_loop",
        unsigned_total,
    )
    with pytest.raises(
        QualificationContractError,
        match="pipeline or algebraic check failed",
    ):
        qualification_runner._run_representation_metamorphic(
            protocol,
            d1_evidence,
        )


def test_d1_numeric_oracle_law_detects_a_systematic_direction_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol = _development_protocol()
    original_estimate = qualification_runner.estimate_cartesian_fourier_field

    def reversed_direction(*args: object, **kwargs: object):
        estimate = original_estimate(*args, **kwargs)
        reversed_section = np.ascontiguousarray(
            -estimate.section_values,
            dtype="<f8",
        )
        reversed_section.flags.writeable = False
        object.__setattr__(
            estimate,
            "section_values",
            reversed_section,
        )
        return estimate

    monkeypatch.setattr(
        qualification_runner,
        "estimate_cartesian_fourier_field",
        reversed_direction,
    )
    receipt = qualification_runner._run_cartesian_d1_family(protocol)

    assert receipt.failed_obligation_ids == ("cartesian-oracle-numeric-law",)
    assert any(
        metric.metric_id == "direction-minimum-cosine" and metric.passed is False
        for case in receipt.cases
        for metric in case.numeric_metric_receipts
    )


def test_blind_primary_handle_is_exactly_estimator_visible_content_only() -> None:
    visible_content = "a" * 64
    expected = qualification_runner.fingerprint_mapping(
        {
            "schema_version": ("spirallens.runner-blind-primary-content-handle.v0.1"),
            "estimator_input_fingerprint_sha256": visible_content,
        }
    )

    assert (
        qualification_runner._blind_primary_content_sha256(
            estimator_input_fingerprint_sha256=visible_content,
        )
        == expected
    )
    assert qualification_runner._blind_primary_content_sha256(
        estimator_input_fingerprint_sha256=visible_content,
    ) != qualification_runner._blind_primary_content_sha256(
        estimator_input_fingerprint_sha256="b" * 64,
    )


def test_engine_closure_binds_package_initializers_and_transitive_dependencies() -> (
    None
):
    formerly_omitted = {
        "spirallens",
        "spirallens.graphs",
        "spirallens.graphs.diversity",
        "spirallens.graphs.domain",
        "spirallens.instrument_contracts",
        "spirallens.instrument_contracts.registry_loader",
        "spirallens.qualification",
        "spirallens.referents",
        "spirallens.referents.loader",
        "spirallens.synthetic",
        "spirallens.synthetic.generators",
    }

    assert formerly_omitted <= REQUIRED_ENGINE_MODULES
    assert module_repository_path("spirallens.qualification") == (
        "src/spirallens/qualification/__init__.py"
    )
    assert module_source_sha256("spirallens.qualification")


@pytest.mark.parametrize(
    "source",
    (
        "import importlib\nimportlib.import_module('spirallens.graphs')\n",
        "__import__('spirallens.graphs')\n",
        (
            "import importlib.util\n"
            "importlib.util.spec_from_file_location('x', '/tmp/x.py')\n"
        ),
    ),
)
def test_engine_closure_rejects_dynamic_local_execution_primitives(
    tmp_path: Path,
    source: str,
) -> None:
    path = tmp_path / "dynamic_engine.py"
    path.write_text(source, encoding="utf-8")

    with pytest.raises(
        QualificationContractError,
        match="forbidden dynamic execution/import primitive",
    ):
        qualification_runner._local_import_targets(
            "spirallens.dynamic_engine",
            path,
        )


def test_runner_rejects_omitted_transitive_dependency_before_generator(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    protocol = _development_protocol()
    omitted = "spirallens.graphs.domain"
    protocol = replace(
        protocol,
        engine=replace(
            protocol.engine,
            modules=tuple(
                item for item in protocol.engine.modules if item.module != omitted
            ),
        ),
    )
    loaded = _loaded_protocol(protocol)
    source_binding = _source_binding(protocol)
    freeze = _freeze(loaded)
    attempt_claim, _identity = claim_selection_attempt(
        tmp_path,
        claim_id="qualification-omitted-dependency-attempt",
        freeze=freeze,
    )
    generation_started = False

    monkeypatch.setattr(
        qualification_runner,
        "verify_protocol_source_binding",
        lambda *_args, **_kwargs: source_binding,
    )

    def forbidden_generate(
        _self: CartesianFourierDomainGenerator,
        _spec: object,
    ) -> None:
        nonlocal generation_started
        generation_started = True
        raise AssertionError("generator must not run with an omitted dependency")

    monkeypatch.setattr(
        CartesianFourierDomainGenerator,
        "generate",
        forbidden_generate,
    )
    with pytest.raises(
        QualificationContractError,
        match="engine binding omits required runner modules",
    ):
        run_calibration_selection(
            loaded,
            source_binding_receipt=source_binding,
            selection_freeze_artifact=freeze,
            attempt_claim=attempt_claim,
            attempt_store_directory=tmp_path,
        )
    assert generation_started is False


def test_runner_rejects_forged_public_source_receipt_before_generator(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    protocol = _development_protocol()
    loaded = _loaded_protocol(protocol)
    live_receipt = _source_binding(protocol)
    forged_receipt = replace(live_receipt, head_commit="f" * 40)
    freeze = _freeze(loaded)
    attempt_claim, _identity = claim_selection_attempt(
        tmp_path,
        claim_id="qualification-forged-receipt-attempt",
        freeze=freeze,
    )
    generation_started = False

    monkeypatch.setattr(
        qualification_runner,
        "verify_protocol_source_binding",
        lambda *_args, **_kwargs: live_receipt,
    )

    def forbidden_generate(
        _self: CartesianFourierDomainGenerator,
        _spec: object,
    ) -> None:
        nonlocal generation_started
        generation_started = True
        raise AssertionError("generator must not run for a forged source receipt")

    monkeypatch.setattr(
        CartesianFourierDomainGenerator,
        "generate",
        forbidden_generate,
    )
    with pytest.raises(
        QualificationSourceBindingError,
        match="differs from live verification",
    ):
        run_calibration_selection(
            loaded,
            source_binding_receipt=forged_receipt,
            selection_freeze_artifact=freeze,
            attempt_claim=attempt_claim,
            attempt_store_directory=tmp_path,
        )
    assert generation_started is False


def test_runner_rejects_replaced_critical_callable_before_execution_start(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    protocol = _development_protocol()
    loaded = _loaded_protocol(protocol)
    source_binding = _source_binding(protocol)
    freeze = _freeze(loaded)
    attempt_claim, _identity = claim_selection_attempt(
        tmp_path,
        claim_id="qualification-replaced-callable-attempt",
        freeze=freeze,
    )
    monkeypatch.setattr(
        qualification_runner,
        "verify_protocol_source_binding",
        lambda *_args, **_kwargs: source_binding,
    )
    monkeypatch.setattr(
        qualification_runner,
        "estimate_cartesian_fourier_field",
        lambda *_args, **_kwargs: None,
    )

    with pytest.raises(
        QualificationSourceBindingError,
        match="critical in-process runner callable",
    ):
        run_calibration_selection(
            loaded,
            source_binding_receipt=source_binding,
            selection_freeze_artifact=freeze,
            attempt_claim=attempt_claim,
            attempt_store_directory=tmp_path,
        )
    assert not selection_execution_start_path(
        tmp_path,
        freeze,
    ).exists()


def test_runner_rechecks_live_source_binding_after_execution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    protocol = _development_protocol()
    loaded = _loaded_protocol(protocol)
    source_binding = _source_binding(protocol)
    changed = replace(source_binding, head_commit="f" * 40)
    freeze = _freeze(loaded)
    attempt_claim, _identity = claim_selection_attempt(
        tmp_path,
        claim_id="qualification-source-exit-recheck-attempt",
        freeze=freeze,
    )
    receipts = iter((source_binding, changed))
    monkeypatch.setattr(
        qualification_runner,
        "verify_protocol_source_binding",
        lambda *_args, **_kwargs: next(receipts),
    )

    with pytest.raises(
        QualificationSourceBindingError,
        match="changed during selection execution",
    ):
        run_calibration_selection(
            loaded,
            source_binding_receipt=source_binding,
            selection_freeze_artifact=freeze,
            attempt_claim=attempt_claim,
            attempt_store_directory=tmp_path,
        )
    assert selection_execution_start_path(tmp_path, freeze).is_file()


def test_runner_rejects_nonexistent_engine_commit_before_generator(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    protocol = _development_protocol()
    protocol = replace(
        protocol,
        engine=replace(protocol.engine, commit="f" * 40),
    )
    loaded = _loaded_protocol(protocol)
    claimed_receipt = _source_binding(protocol)
    freeze = _freeze(loaded)
    attempt_claim, _identity = claim_selection_attempt(
        tmp_path,
        claim_id="qualification-nonexistent-commit-attempt",
        freeze=freeze,
    )
    generation_started = False

    def forbidden_generate(
        _self: CartesianFourierDomainGenerator,
        _spec: object,
    ) -> None:
        nonlocal generation_started
        generation_started = True
        raise AssertionError("generator must not run for a nonexistent commit")

    monkeypatch.setattr(
        CartesianFourierDomainGenerator,
        "generate",
        forbidden_generate,
    )
    with pytest.raises(QualificationSourceBindingError):
        run_calibration_selection(
            loaded,
            source_binding_receipt=claimed_receipt,
            selection_freeze_artifact=freeze,
            attempt_claim=attempt_claim,
            attempt_store_directory=tmp_path,
        )
    assert generation_started is False


def test_runner_execution_start_survives_failure_and_blocks_retry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    protocol = _development_protocol()
    loaded = _loaded_protocol(protocol)
    source_binding = _source_binding(protocol)
    freeze = _freeze(loaded)
    attempt_claim, _identity = claim_selection_attempt(
        tmp_path,
        claim_id="qualification-single-entry-attempt",
        freeze=freeze,
    )
    generator_entry_count = 0

    monkeypatch.setattr(
        qualification_runner,
        "verify_protocol_source_binding",
        lambda *_args, **_kwargs: source_binding,
    )

    def fail_after_entry(
        _self: CartesianFourierDomainGenerator,
        _spec: object,
    ) -> None:
        nonlocal generator_entry_count
        generator_entry_count += 1
        raise RuntimeError("simulated generator crash")

    monkeypatch.setattr(
        CartesianFourierDomainGenerator,
        "generate",
        fail_after_entry,
    )
    with pytest.raises(RuntimeError, match="simulated generator crash"):
        run_calibration_selection(
            loaded,
            source_binding_receipt=source_binding,
            selection_freeze_artifact=freeze,
            attempt_claim=attempt_claim,
            attempt_store_directory=tmp_path,
        )
    with pytest.raises(
        QualificationContractError,
        match="existing selection execution-start artifact",
    ):
        run_calibration_selection(
            loaded,
            source_binding_receipt=source_binding,
            selection_freeze_artifact=freeze,
            attempt_claim=attempt_claim,
            attempt_store_directory=tmp_path,
        )
    assert generator_entry_count == 1


def test_runner_rejects_wrong_freeze_before_any_generator(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    protocol = _development_protocol()
    loaded = _loaded_protocol(protocol)
    source_binding = _source_binding(protocol)
    original_freeze = _freeze(loaded)
    attempt_claim, _identity = claim_selection_attempt(
        tmp_path,
        claim_id="qualification-development-attempt",
        freeze=original_freeze,
    )
    freeze = replace(original_freeze, engine_commit="2" * 40)
    generation_started = False

    def forbidden_generate(
        _self: CartesianFourierDomainGenerator,
        _spec: object,
    ) -> None:
        nonlocal generation_started
        generation_started = True
        raise AssertionError("generator must not run before freeze validation")

    monkeypatch.setattr(
        CartesianFourierDomainGenerator,
        "generate",
        forbidden_generate,
    )
    with pytest.raises(
        QualificationContractError,
        match="does not match the exact protocol",
    ):
        run_calibration_selection(
            loaded,
            source_binding_receipt=source_binding,
            selection_freeze_artifact=freeze,
            attempt_claim=attempt_claim,
            attempt_store_directory=tmp_path,
        )
    assert generation_started is False


def test_frozen_wide_boundary_gets_an_oracle_target_without_becoming_output() -> None:
    phantom = CartesianFourierDomainGenerator().generate(
        CartesianFourierDomainSpec(
            seed=101,
            grid_side=7,
            ambient_dimension=12,
            samples_per_split=8,
            baseline=1.25,
            second_harmonic_scale=0.35,
        )
    )
    wide = BoundaryTemplate("wide", 1, 1, 5, 5)

    assert _expected_sampled_cycles(phantom.positive, wide) == 1
    assert _expected_sampled_cycles(phantom.fixed_null, wide) == 0
    assert _expected_sampled_cycles(phantom.no_core_null, wide) == 0
    assert _expected_sampled_cycles(phantom.prerequisite_failure, wide) is None

    # A declared boundary that crosses the zero-amplitude core has no oracle
    # direction and fails instead of manufacturing an integer target.
    with pytest.raises(
        QualificationContractError,
        match="crosses undefined oracle direction",
    ):
        _expected_sampled_cycles(
            phantom.positive,
            BoundaryTemplate("crosses-core", 3, 2, 5, 4),
        )


def test_runner_rejects_unpersisted_attempt_claim_before_any_generator(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    protocol = _development_protocol()
    loaded = _loaded_protocol(protocol)
    source_binding = _source_binding(protocol)
    freeze = _freeze(loaded)
    attempt_claim = SelectionAttemptClaimArtifact.from_freeze(
        claim_id="qualification-development-attempt",
        freeze=freeze,
    )
    generation_started = False

    def forbidden_generate(
        _self: CartesianFourierDomainGenerator,
        _spec: object,
    ) -> None:
        nonlocal generation_started
        generation_started = True
        raise AssertionError("generator must not run before persisted claim validation")

    monkeypatch.setattr(
        CartesianFourierDomainGenerator,
        "generate",
        forbidden_generate,
    )
    with pytest.raises(
        QualificationContractError,
        match="cannot read persisted selection freeze",
    ):
        run_calibration_selection(
            loaded,
            source_binding_receipt=source_binding,
            selection_freeze_artifact=freeze,
            attempt_claim=attempt_claim,
            attempt_store_directory=tmp_path,
        )
    assert generation_started is False
