from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, replace
import hashlib
import io
import json
import os
from pathlib import Path

import numpy as np
import pytest

import spirallens.instrument_contracts.bundle_loader as bundle_loader_module
from spirallens.cli import main
from spirallens.contexts import ContextRole, load_context_bank
from spirallens.instrument_contracts.artifacts import (
    CalibrationSelectionDecision,
    CandidateGraph,
    CoreCandidate,
    CoreScore,
    DefectCoordinateBinding,
    DefectLocalizationBinding,
    DefectLoopEstimate,
    EdgeConnection,
    GraphFreeBinding,
    GraphConstructionSpec,
    HypothesisDecision,
    HypothesisFixedChoice,
    HypothesisResolvedChoice,
    HypothesisRuleChoice,
    OrderParameterField,
    OrderParameterSpec,
    SubstrateBinding,
    SupportDiagnostic,
)
from spirallens.instrument_contracts.bundle import (
    BundleArtifactEntry,
    BundleContextBankEntry,
    BundlePayloadEntry,
    InstrumentBundleManifest,
)
from spirallens.instrument_contracts.bundle_loader import (
    InstrumentBundleConsistencyError,
    InstrumentBundleError,
    InstrumentBundleIntegrityError,
    InstrumentBundleResolutionError,
    InstrumentBundleSchemaError,
    _detect_cycle,
    _reachable_from_roots,
    load_instrument_bundle,
)
from spirallens.instrument_contracts.canonical import canonical_json_bytes
from spirallens.instrument_contracts.common import (
    ARTIFACT_SCHEMA_VERSION_BY_TYPE,
    ArtifactRef,
    ArtifactType,
    ClaimLevel,
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
from spirallens.instrument_contracts.registry_loader import (
    load_hypothesis_registry,
)


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


SUBSTRATE_ROWS = _digest("bundle-substrate-rows")
GRAPH_VERTICES = _digest("bundle-graph-vertices")
GRAPH_EDGES = _digest("bundle-graph-edges")
GRAPH_CYCLES = _digest("bundle-graph-cycles")
LOOP_ROWS = _digest("bundle-loop-rows")
REGISTRY_CHOICE_FIELDS = (
    "input_tensor",
    "observation_axis",
    "centering_rule",
    "residual_rule",
    "architecture_accounting_rule",
    "estimator",
    "fit_role",
    "interpolation_rule",
    "lift_rule",
    "trivialization_rule",
    "reference_rule",
)


def _artifact_ref(artifact: object) -> ArtifactRef:
    return ArtifactRef(
        artifact_type=artifact.artifact_type,
        schema_version=artifact.schema_version,
        artifact_id=artifact.artifact_id,
        canonical_sha256=artifact.canonical_sha256,
    )


def _external_ref(
    artifact_type: ArtifactType,
    *,
    artifact_id: str,
    canonical_sha256: str,
) -> ArtifactRef:
    return ArtifactRef(
        artifact_type=artifact_type,
        schema_version=ARTIFACT_SCHEMA_VERSION_BY_TYPE[artifact_type],
        artifact_id=artifact_id,
        canonical_sha256=canonical_sha256,
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


@dataclass(frozen=True, slots=True)
class BundleFixture:
    root: Path
    manifest_path: Path
    manifest: InstrumentBundleManifest
    artifacts: dict[str, object]
    artifact_entries: dict[str, BundleArtifactEntry]
    payload_entries: tuple[BundlePayloadEntry, ...]


def _member_relative_path(
    fixture: BundleFixture,
    member_kind: str,
) -> str:
    if member_kind == "manifest":
        return fixture.manifest_path.name
    if member_kind == "instrument":
        return fixture.manifest.instrument_artifacts[0].path
    if member_kind == "registry":
        return fixture.manifest.hypothesis_registries[0].path
    if member_kind == "context_bank":
        return fixture.manifest.context_banks[0].path
    if member_kind == "payload":
        return fixture.manifest.payloads[0].path
    raise AssertionError(f"unknown member kind {member_kind!r}")


def _root_sort_key(reference: ArtifactRef) -> tuple[str, ...]:
    return (
        reference.artifact_type.value,
        reference.artifact_id,
        reference.schema_version,
        reference.canonical_sha256,
    )


def _write_manifest(
    path: Path,
    manifest: InstrumentBundleManifest,
) -> None:
    path.write_bytes(manifest.canonical_bytes)


def _write_manifest_document(
    fixture: BundleFixture,
    document: dict[str, object],
) -> None:
    fixture.manifest_path.write_bytes(canonical_json_bytes(document))


def _build_bundle(
    tmp_path: Path,
    *,
    substrate_role: FitRole = FitRole.CALIBRATION_SELECTION,
    substrate_axis: EvolutionAxis = EvolutionAxis.LAYER_INDEX,
    graph_allowed_role: FitRole | None = None,
    support_row_identity: str = SUBSTRATE_ROWS,
    split_graph_spec_substrate: bool = False,
    defect_edge_claim: ClaimLevel | None = None,
    include_instrument_dev_selection: bool = False,
    selection_fit_role: FitRole = FitRole.INSTRUMENT_DEV,
    select_retained_f3_artifact: bool = False,
    include_level_2t: bool = False,
    level_2t_selection_role: FitRole | None = None,
    level_2t_selection_axis: EvolutionAxis | None = None,
    level_2t_selected_precursor: bool = True,
) -> BundleFixture:
    root = tmp_path / "bundle"
    artifact_directory = root / "artifacts"
    external_directory = root / "external"
    payload_directory = root / "payloads"
    for directory in (
        artifact_directory,
        external_directory,
        payload_directory,
    ):
        directory.mkdir(parents=True)

    repository_root = Path(__file__).resolve().parents[1]
    registry_source = (
        repository_root / "protocols" / "order_parameter_hypothesis_registry_v0_1.yaml"
    )
    context_source = repository_root / "protocols" / "context_bank_example_v0_1.yaml"
    registry_path = external_directory / "hypothesis-registry.yaml"
    context_path = external_directory / "context-bank.yaml"
    registry_path.write_bytes(registry_source.read_bytes())
    context_path.write_bytes(context_source.read_bytes())

    loaded_registry = load_hypothesis_registry(registry_path)
    loaded_context = load_context_bank(
        context_path,
        allowed_roles={ContextRole.EXAMPLE},
    )
    registry_ref = _external_ref(
        ArtifactType.HYPOTHESIS_REGISTRY,
        artifact_id=loaded_registry.registry.registry_id,
        canonical_sha256=loaded_registry.canonical_sha256,
    )
    context_ref = _external_ref(
        ArtifactType.CONTEXT_BANK,
        artifact_id=loaded_context.bank.bank_id,
        canonical_sha256=loaded_context.canonical_sha256,
    )

    payload_entries: list[BundlePayloadEntry] = []
    payload_counter = 0
    boolean_payload_counter = 0

    def write_array(
        label: str,
        *,
        row_identity: str,
        shape: tuple[int, ...] = (4,),
        dtype: str = "<f4",
    ) -> PayloadRef:
        nonlocal boolean_payload_counter, payload_counter
        payload_counter += 1
        array_dtype = np.dtype(dtype)
        if array_dtype.kind == "b":
            boolean_payload_counter += 1
            bit_positions = np.arange(np.prod(shape), dtype=np.uint64)
            array = (
                ((np.uint64(boolean_payload_counter) >> bit_positions) & 1)
                .astype(array_dtype)
                .reshape(shape)
            )
        else:
            array = np.arange(
                np.prod(shape),
                dtype=array_dtype,
            ).reshape(shape)
            array = array + payload_counter
        stream = io.BytesIO()
        np.save(stream, array, allow_pickle=False)
        payload_bytes = stream.getvalue()
        relative_path = f"payloads/{label}.npy"
        (root / relative_path).write_bytes(payload_bytes)
        reference = PayloadRef(
            kind=PayloadKind.ARRAY,
            sha256=hashlib.sha256(payload_bytes).hexdigest(),
            byte_length=len(payload_bytes),
            media_type="application/x-npy",
            dtype=dtype,
            shape=shape,
            row_identity_sha256=row_identity,
        )
        payload_entries.append(
            BundlePayloadEntry(path=relative_path, reference=reference)
        )
        return reference

    def write_records(
        label: str,
        *,
        row_identity: str,
    ) -> PayloadRef:
        payload_bytes = f'{{"cell":"{label}"}}\n'.encode("utf-8")
        relative_path = f"payloads/{label}.jsonl"
        (root / relative_path).write_bytes(payload_bytes)
        reference = PayloadRef(
            kind=PayloadKind.JSON_RECORDS,
            sha256=hashlib.sha256(payload_bytes).hexdigest(),
            byte_length=len(payload_bytes),
            media_type="application/x-ndjson",
            record_count=1,
            row_identity_sha256=row_identity,
        )
        payload_entries.append(
            BundlePayloadEntry(path=relative_path, reference=reference)
        )
        return reference

    def write_opaque(label: str) -> PayloadRef:
        payload_bytes = f"opaque:{label}".encode("utf-8")
        relative_path = f"payloads/{label}.bin"
        (root / relative_path).write_bytes(payload_bytes)
        reference = PayloadRef(
            kind=PayloadKind.OPAQUE,
            sha256=hashlib.sha256(payload_bytes).hexdigest(),
            byte_length=len(payload_bytes),
            media_type="application/octet-stream",
        )
        payload_entries.append(
            BundlePayloadEntry(path=relative_path, reference=reference)
        )
        return reference

    substrate_payloads = {
        "vertex_identities": write_array(
            "substrate-vertex-identities",
            row_identity=SUBSTRATE_ROWS,
            dtype="<i8",
        ),
        "observation_identities": write_array(
            "substrate-observation-identities",
            row_identity=SUBSTRATE_ROWS,
            dtype="<i8",
        ),
        "states": write_array(
            "substrate-states",
            row_identity=SUBSTRATE_ROWS,
            shape=(4, 8),
        ),
        "accounted_response": write_array(
            "substrate-accounted-response",
            row_identity=SUBSTRATE_ROWS,
        ),
        "mask": write_array(
            "substrate-mask",
            row_identity=SUBSTRATE_ROWS,
            dtype="|b1",
        ),
        "preprocessing_fit": write_opaque("substrate-preprocessing-fit"),
    }
    substrate = SubstrateBinding(
        artifact_id="bundle-substrate",
        role=substrate_role,
        evolution_axis=substrate_axis,
        row_identity_sha256=SUBSTRATE_ROWS,
        context_bank=context_ref,
        **substrate_payloads,
    )
    substrate_ref = _artifact_ref(substrate)

    secondary_substrate = replace(
        substrate,
        artifact_id="bundle-secondary-substrate",
    )
    graph_spec_substrate_ref = (
        _artifact_ref(secondary_substrate)
        if split_graph_spec_substrate
        else substrate_ref
    )
    graph_spec = GraphConstructionSpec(
        artifact_id="bundle-graph-spec",
        substrate=graph_spec_substrate_ref,
        purpose="field_estimation",
        family=_fixed("graph_family", "mutual-knn"),
        metric=_fixed("graph_metric", "cosine"),
        scale=_fixed("graph_scale", "local"),
        constructor_id="deterministic-graph-v1",
        deterministic_tie_policy="lexicographic-vertex-id",
        allowed_role=(
            substrate_role if graph_allowed_role is None else graph_allowed_role
        ),
    )
    graph_spec_ref = _artifact_ref(graph_spec)

    candidate_graph = CandidateGraph(
        artifact_id="bundle-candidate-graph",
        substrate=substrate_ref,
        specification=graph_spec_ref,
        vertex_order_sha256=GRAPH_VERTICES,
        edge_order_sha256=GRAPH_EDGES,
        cycle_order_sha256=GRAPH_CYCLES,
        vertices=write_array(
            "graph-vertices",
            row_identity=GRAPH_VERTICES,
            dtype="<i8",
        ),
        canonical_edges=write_array(
            "graph-edges",
            row_identity=GRAPH_EDGES,
            shape=(4, 2),
            dtype="<i8",
        ),
        weights=write_array(
            "graph-weights",
            row_identity=GRAPH_EDGES,
        ),
        connected_components=write_array(
            "graph-components",
            row_identity=GRAPH_VERTICES,
            dtype="<i8",
        ),
        degree_distribution=write_array(
            "graph-degrees",
            row_identity=GRAPH_VERTICES,
            dtype="<i8",
        ),
        two_core=write_array(
            "graph-two-core",
            row_identity=GRAPH_VERTICES,
            dtype="|b1",
        ),
        cycle_support=write_array(
            "graph-cycle-support",
            row_identity=GRAPH_CYCLES,
            shape=(4, 3),
            dtype="<i8",
        ),
    )
    candidate_graph_ref = _artifact_ref(candidate_graph)

    support = SupportDiagnostic(
        artifact_id="bundle-support",
        substrate=substrate_ref,
        row_identity_sha256=support_row_identity,
        scalar_definition_id="local-support-v1",
        neighborhood_specification=candidate_graph_ref,
        fit_role=substrate_role,
        values=write_array(
            "support-values",
            row_identity=support_row_identity,
        ),
        uncertainty=write_array(
            "support-uncertainty",
            row_identity=support_row_identity,
        ),
        support=write_array(
            "support-mask",
            row_identity=support_row_identity,
            dtype="|b1",
        ),
        pointwise_reason_codes=write_array(
            "support-reasons",
            row_identity=support_row_identity,
            dtype="<i4",
        ),
        claim_ceiling=ClaimLevel.LEVEL_1G,
    )

    artifacts: dict[str, object] = {
        "substrate": substrate,
        "graph_spec": graph_spec,
        "candidate_graph": candidate_graph,
        "support": support,
    }
    extra_roots: list[ArtifactRef] = []

    if defect_edge_claim is not None:
        hypothesis = loaded_registry.registry.require(
            HypothesisId.F3_GLOBAL_PLANE_SECTION
        )
        order_spec = OrderParameterSpec(
            artifact_id="bundle-order-spec",
            hypothesis_registry=registry_ref,
            substrate=substrate_ref,
            estimation_graph=candidate_graph_ref,
            hypothesis_id=HypothesisId.F3_GLOBAL_PLANE_SECTION,
            input_binding=write_opaque("order-input-binding"),
            fit_receipt=write_opaque("order-fit-receipt"),
            target_manifold_id=hypothesis.target_manifold,
            gauge_law_id=hypothesis.gauge_law,
            charge_group=_fixed(
                "charge_group",
                hypothesis.charge_group,
            ),
            amplitude_rule=_fixed("amplitude_rule", "spectral-gap"),
            identifiability_rule=_fixed(
                "identifiability_rule",
                "support-threshold",
            ),
            interpolation_rule=hypothesis.interpolation_rule,
            lift_rule=hypothesis.lift_rule,
            trivialization_rule=hypothesis.trivialization_rule,
            reference_rule=hypothesis.reference_rule,
            forbidden_labels=hypothesis.forbidden_labels,
            claim_ceiling=ClaimLevel.LEVEL_1D,
        )
        order_spec_ref = _artifact_ref(order_spec)
        order_field = OrderParameterField(
            artifact_id="bundle-order-field",
            specification=order_spec_ref,
            hypothesis_id=HypothesisId.F3_GLOBAL_PLANE_SECTION,
            substrate=substrate_ref,
            estimation_graph=candidate_graph_ref,
            row_identity_sha256=SUBSTRATE_ROWS,
            values=write_array(
                "order-values",
                row_identity=SUBSTRATE_ROWS,
                shape=(4, 2),
            ),
            amplitude=write_array(
                "order-amplitude",
                row_identity=SUBSTRATE_ROWS,
            ),
            frame_or_tensor=write_array(
                "order-frame",
                row_identity=SUBSTRATE_ROWS,
                shape=(4, 2, 2),
            ),
            eigenspectrum=write_array(
                "order-eigenspectrum",
                row_identity=SUBSTRATE_ROWS,
                shape=(4, 2),
            ),
            support=write_array(
                "order-support",
                row_identity=SUBSTRATE_ROWS,
                dtype="|b1",
            ),
            pointwise_reason_codes=write_array(
                "order-reasons",
                row_identity=SUBSTRATE_ROWS,
                dtype="<i4",
            ),
            claim_ceiling=ClaimLevel.LEVEL_1D,
        )
        order_field_ref = _artifact_ref(order_field)
        edge_connection = EdgeConnection(
            artifact_id="bundle-defect-edge-connection",
            substrate=substrate_ref,
            field=order_field_ref,
            field_branch=ScientificBranch.DEFECT,
            graph=candidate_graph_ref,
            edge_order_sha256=GRAPH_EDGES,
            endpoint_identities=write_array(
                "defect-edge-endpoints",
                row_identity=GRAPH_EDGES,
                shape=(4, 2),
                dtype="<i8",
            ),
            principal_angles=write_array(
                "defect-edge-principal-angles",
                row_identity=GRAPH_EDGES,
            ),
            procrustes_singular_values=write_array(
                "defect-edge-singular-values",
                row_identity=GRAPH_EDGES,
                shape=(4, 2),
            ),
            coherence=write_array(
                "defect-edge-coherence",
                row_identity=GRAPH_EDGES,
            ),
            orientation_state="so2",
            transport_convention_id="defect-transport-v1",
            claim_ceiling=defect_edge_claim,
        )
        artifacts.update(
            {
                "order_spec": order_spec,
                "order_field": order_field,
                "edge_connection": edge_connection,
            }
        )
        extra_roots.append(_artifact_ref(edge_connection))

    if include_level_2t:
        selected_role = (
            substrate_role
            if level_2t_selection_role is None
            else level_2t_selection_role
        )
        selected_axis = (
            substrate_axis
            if level_2t_selection_axis is None
            else level_2t_selection_axis
        )
        decisions_2t: list[HypothesisDecision] = []
        fixed_choices_2t: list[HypothesisFixedChoice] = []
        resolved_choices_2t: list[HypothesisResolvedChoice] = []
        unresolved_choices_2t: list[HypothesisRuleChoice] = []
        f2_selected: dict[str, str] = {}
        for hypothesis in loaded_registry.registry.hypotheses:
            advanced = (
                hypothesis.hypothesis_id is HypothesisId.F2_LOCAL_COVARIANT_SECTION
            )
            decisions_2t.append(
                HypothesisDecision(
                    hypothesis_id=hypothesis.hypothesis_id,
                    disposition=(
                        HypothesisDisposition.ADVANCE
                        if advanced
                        else HypothesisDisposition.RETAIN_DIAGNOSTIC
                    ),
                    reason_codes=(
                        ("level-2t-authorization",) if advanced else ("not-selected",)
                    ),
                )
            )
            for field_name in REGISTRY_CHOICE_FIELDS:
                choice = getattr(hypothesis, field_name)
                if choice.resolution is ResolutionState.FIXED_BY_HYPOTHESIS:
                    fixed_choices_2t.append(
                        HypothesisFixedChoice(
                            hypothesis_id=hypothesis.hypothesis_id,
                            choice=choice,
                        )
                    )
                elif choice.resolution is ResolutionState.CALIBRATION_SELECTION:
                    if advanced:
                        selected_id = (
                            selected_role.value
                            if field_name == "fit_role"
                            else (
                                selected_axis.value
                                if field_name == "observation_axis"
                                else sorted(choice.candidate_ids)[0]
                            )
                        )
                        f2_selected[field_name] = selected_id
                        resolved_choices_2t.append(
                            HypothesisResolvedChoice(
                                hypothesis_id=hypothesis.hypothesis_id,
                                choice=_resolved(
                                    field_name,
                                    selected_id,
                                ),
                            )
                        )
                    else:
                        unresolved_choices_2t.append(
                            HypothesisRuleChoice(
                                hypothesis_id=hypothesis.hypothesis_id,
                                choice=choice,
                            )
                        )

        cycle_graph_spec = GraphConstructionSpec(
            artifact_id="bundle-cycle-graph-spec",
            substrate=substrate_ref,
            purpose="cycle_construction",
            family=_fixed("graph_family", "mutual-knn"),
            metric=_fixed("graph_metric", "cosine"),
            scale=_fixed("graph_scale", "local"),
            constructor_id="deterministic-cycle-graph-v1",
            deterministic_tie_policy="lexicographic-vertex-id",
            allowed_role=substrate_role,
        )
        cycle_graph_spec_ref = _artifact_ref(cycle_graph_spec)
        cycle_graph = CandidateGraph(
            artifact_id="bundle-cycle-graph",
            substrate=substrate_ref,
            specification=cycle_graph_spec_ref,
            vertex_order_sha256=GRAPH_VERTICES,
            edge_order_sha256=GRAPH_EDGES,
            cycle_order_sha256=GRAPH_CYCLES,
            vertices=candidate_graph.vertices,
            canonical_edges=candidate_graph.canonical_edges,
            weights=candidate_graph.weights,
            connected_components=candidate_graph.connected_components,
            degree_distribution=candidate_graph.degree_distribution,
            two_core=candidate_graph.two_core,
            cycle_support=candidate_graph.cycle_support,
        )
        cycle_graph_ref = _artifact_ref(cycle_graph)

        f2_hypothesis = loaded_registry.registry.require(
            HypothesisId.F2_LOCAL_COVARIANT_SECTION
        )
        order_spec_2t = OrderParameterSpec(
            artifact_id="bundle-order-spec-2t",
            hypothesis_registry=registry_ref,
            substrate=substrate_ref,
            estimation_graph=candidate_graph_ref,
            hypothesis_id=HypothesisId.F2_LOCAL_COVARIANT_SECTION,
            input_binding=write_opaque("order-input-binding-2t"),
            fit_receipt=write_opaque("order-fit-receipt-2t"),
            target_manifold_id=f2_hypothesis.target_manifold,
            gauge_law_id=f2_hypothesis.gauge_law,
            charge_group=_fixed(
                "charge_group",
                f2_hypothesis.charge_group,
            ),
            amplitude_rule=_fixed("amplitude_rule", "spectral-gap"),
            identifiability_rule=_fixed(
                "identifiability_rule",
                "support-threshold",
            ),
            interpolation_rule=_resolved(
                "interpolation_rule",
                f2_selected["interpolation_rule"],
            ),
            lift_rule=_resolved(
                "lift_rule",
                f2_selected["lift_rule"],
            ),
            trivialization_rule=_resolved(
                "trivialization_rule",
                f2_selected["trivialization_rule"],
            ),
            reference_rule=_resolved(
                "reference_rule",
                f2_selected["reference_rule"],
            ),
            forbidden_labels=f2_hypothesis.forbidden_labels,
            claim_ceiling=ClaimLevel.LEVEL_2T,
        )
        order_spec_2t_ref = _artifact_ref(order_spec_2t)
        order_field_2t = OrderParameterField(
            artifact_id="bundle-order-field-2t",
            specification=order_spec_2t_ref,
            hypothesis_id=HypothesisId.F2_LOCAL_COVARIANT_SECTION,
            substrate=substrate_ref,
            estimation_graph=candidate_graph_ref,
            row_identity_sha256=SUBSTRATE_ROWS,
            values=write_array(
                "order-values-2t",
                row_identity=SUBSTRATE_ROWS,
                shape=(4, 2),
            ),
            amplitude=write_array(
                "order-amplitude-2t",
                row_identity=SUBSTRATE_ROWS,
            ),
            frame_or_tensor=write_array(
                "order-frame-2t",
                row_identity=SUBSTRATE_ROWS,
                shape=(4, 2, 2),
            ),
            eigenspectrum=write_array(
                "order-eigenspectrum-2t",
                row_identity=SUBSTRATE_ROWS,
                shape=(4, 2),
            ),
            support=write_array(
                "order-support-2t",
                row_identity=SUBSTRATE_ROWS,
                dtype="|b1",
            ),
            pointwise_reason_codes=write_array(
                "order-reasons-2t",
                row_identity=SUBSTRATE_ROWS,
                dtype="<i4",
            ),
            claim_ceiling=ClaimLevel.LEVEL_2T,
        )
        order_field_2t_ref = _artifact_ref(order_field_2t)
        graph_free = GraphFreeBinding()
        core_score = CoreScore(
            artifact_id="bundle-core-score-2t",
            substrate=substrate_ref,
            order_parameter_spec=order_spec_2t_ref,
            order_parameter_field=order_field_2t_ref,
            field_estimation_graph=candidate_graph_ref,
            row_identity_sha256=SUBSTRATE_ROWS,
            scalar_definition_id="charge-blind-core-score-v1",
            fit_role=substrate_role,
            singularity_rule_id="low-amplitude-v1",
            graph_binding=graph_free,
            values=write_array(
                "core-score-values-2t",
                row_identity=SUBSTRATE_ROWS,
            ),
            uncertainty=write_array(
                "core-score-uncertainty-2t",
                row_identity=SUBSTRATE_ROWS,
            ),
            support=write_array(
                "core-score-support-2t",
                row_identity=SUBSTRATE_ROWS,
                dtype="|b1",
            ),
            pointwise_reason_codes=write_array(
                "core-score-reasons-2t",
                row_identity=SUBSTRATE_ROWS,
                dtype="<i4",
            ),
            charge_blind=True,
            claim_ceiling=ClaimLevel.LEVEL_1D,
        )
        core_score_ref = _artifact_ref(core_score)
        core_candidate = CoreCandidate(
            artifact_id="bundle-core-candidate-2t",
            substrate=substrate_ref,
            core_score=core_score_ref,
            order_parameter_field=order_field_2t_ref,
            field_estimation_graph=candidate_graph_ref,
            row_identity_sha256=SUBSTRATE_ROWS,
            localization_algorithm_id="component-minimum-v1",
            singularity_rule_id="low-amplitude-v1",
            graph_binding=graph_free,
            localized_support=write_array(
                "core-localized-support-2t",
                row_identity=SUBSTRATE_ROWS,
                dtype="|b1",
            ),
            uncertainty=write_array(
                "core-localization-uncertainty-2t",
                row_identity=SUBSTRATE_ROWS,
            ),
            charge_blind=True,
            sealed_without_loop_observable_input=True,
            claim_ceiling=ClaimLevel.LEVEL_1D,
        )
        core_candidate_ref = _artifact_ref(core_candidate)

        selection_2t = CalibrationSelectionDecision(
            artifact_id="bundle-selection-decision-2t",
            hypothesis_registry=registry_ref,
            hypothesis_decisions=tuple(decisions_2t),
            crossed_cell_order_sha256=_digest("level-2t-crossed-cells"),
            crossed_cell_manifest=write_records(
                "level-2t-crossed-cells",
                row_identity=_digest("level-2t-crossed-cells"),
            ),
            selected_artifacts=(
                (order_field_2t_ref,) if level_2t_selected_precursor else ()
            ),
            locked_policy_bundle=write_opaque("level-2t-locked-policy"),
            selection_inputs=(registry_ref,),
            selection_outputs=(
                (order_field_2t_ref,) if level_2t_selected_precursor else ()
            ),
            source_commit_sha1="b" * 40,
            source_tree_sha256=_digest("level-2t-selection-source-tree"),
            fixed_choices=tuple(
                sorted(
                    fixed_choices_2t,
                    key=lambda item: (
                        item.hypothesis_id.value,
                        item.choice.family_id,
                    ),
                )
            ),
            resolved_choices=tuple(
                sorted(
                    resolved_choices_2t,
                    key=lambda item: (
                        item.hypothesis_id.value,
                        item.choice.family_id,
                    ),
                )
            ),
            unresolved_choices=tuple(
                sorted(
                    unresolved_choices_2t,
                    key=lambda item: (
                        item.hypothesis_id.value,
                        item.choice.family_id,
                    ),
                )
            ),
            integer_output_authorizations=(HypothesisId.F2_LOCAL_COVARIANT_SECTION,),
            confirmation_access_commitment=write_opaque(
                "level-2t-confirmation-commitment"
            ),
            sealed_before_confirmation_access=True,
            claim_ceiling=ClaimLevel.LEVEL_2T,
        )
        selection_2t_ref = _artifact_ref(selection_2t)
        defect_loop = DefectLoopEstimate(
            artifact_id="bundle-defect-loop-2t",
            substrate=substrate_ref,
            order_parameter_field=order_field_2t_ref,
            hypothesis_id=HypothesisId.F2_LOCAL_COVARIANT_SECTION,
            cycle_graph=cycle_graph_ref,
            loop_order_sha256=LOOP_ROWS,
            ordered_support=write_array(
                "defect-loop-support-2t",
                row_identity=LOOP_ROWS,
                shape=(4, 3),
                dtype="<i8",
            ),
            matched_class=write_array(
                "defect-loop-class-2t",
                row_identity=LOOP_ROWS,
                dtype="<i4",
            ),
            interpolation_evidence=write_array(
                "defect-interpolation-evidence-2t",
                row_identity=LOOP_ROWS,
            ),
            lift_or_reference_evidence=write_array(
                "defect-lift-evidence-2t",
                row_identity=LOOP_ROWS,
            ),
            boundary_identifiability_evidence=write_array(
                "defect-boundary-evidence-2t",
                row_identity=LOOP_ROWS,
            ),
            branch_and_sampling_evidence=write_array(
                "defect-sampling-evidence-2t",
                row_identity=LOOP_ROWS,
            ),
            coordinate_binding=DefectCoordinateBinding(
                mode="global_frame",
            ),
            localization_binding=DefectLocalizationBinding(
                mode="inferred_core",
                core_candidate=core_candidate_ref,
            ),
            sampled_winding=write_array(
                "defect-sampled-winding-2t",
                row_identity=LOOP_ROWS,
                dtype="<i4",
            ),
            integer_output_authorization=selection_2t_ref,
            gate_state=GateState.PASS,
            reason_codes=(),
            claim_ceiling=ClaimLevel.LEVEL_2T,
        )
        artifacts.update(
            {
                "cycle_graph_spec": cycle_graph_spec,
                "cycle_graph": cycle_graph,
                "order_spec_2t": order_spec_2t,
                "order_field_2t": order_field_2t,
                "core_score": core_score,
                "core_candidate": core_candidate,
                "selection_2t": selection_2t,
                "defect_loop": defect_loop,
            }
        )
        extra_roots.append(_artifact_ref(defect_loop))

    if include_instrument_dev_selection:
        decisions: list[HypothesisDecision] = []
        fixed_choices: list[HypothesisFixedChoice] = []
        resolved_choices: list[HypothesisResolvedChoice] = []
        unresolved_choices: list[HypothesisRuleChoice] = []
        for hypothesis in loaded_registry.registry.hypotheses:
            advanced = hypothesis.hypothesis_id is HypothesisId.F0_SUPPORT
            decisions.append(
                HypothesisDecision(
                    hypothesis_id=hypothesis.hypothesis_id,
                    disposition=(
                        HypothesisDisposition.ADVANCE
                        if advanced
                        else HypothesisDisposition.RETAIN_DIAGNOSTIC
                    ),
                    reason_codes=(
                        ("instrument-dev-selection",) if advanced else ("not-selected",)
                    ),
                )
            )
            for field_name in REGISTRY_CHOICE_FIELDS:
                choice = getattr(hypothesis, field_name)
                if choice.resolution is ResolutionState.FIXED_BY_HYPOTHESIS:
                    fixed_choices.append(
                        HypothesisFixedChoice(
                            hypothesis_id=hypothesis.hypothesis_id,
                            choice=choice,
                        )
                    )
                elif choice.resolution is ResolutionState.CALIBRATION_SELECTION:
                    if advanced:
                        selected_id = (
                            selection_fit_role.value
                            if field_name == "fit_role"
                            else sorted(choice.candidate_ids)[0]
                        )
                        resolved_choices.append(
                            HypothesisResolvedChoice(
                                hypothesis_id=hypothesis.hypothesis_id,
                                choice=RuleChoice(
                                    family_id=field_name,
                                    resolution=(ResolutionState.CALIBRATION_RESOLVED),
                                    selected_id=selected_id,
                                ),
                            )
                        )
                    else:
                        unresolved_choices.append(
                            HypothesisRuleChoice(
                                hypothesis_id=hypothesis.hypothesis_id,
                                choice=choice,
                            )
                        )
        support_ref = _artifact_ref(support)
        selected_references = [support_ref]
        if select_retained_f3_artifact:
            selected_references.append(_artifact_ref(artifacts["order_field"]))
        selected_references_tuple = tuple(
            sorted(selected_references, key=_root_sort_key)
        )
        selection = CalibrationSelectionDecision(
            artifact_id="bundle-selection-decision",
            hypothesis_registry=registry_ref,
            hypothesis_decisions=tuple(decisions),
            crossed_cell_order_sha256=_digest("instrument-dev-crossed-cells"),
            crossed_cell_manifest=write_records(
                "instrument-dev-crossed-cells",
                row_identity=_digest("instrument-dev-crossed-cells"),
            ),
            selected_artifacts=selected_references_tuple,
            locked_policy_bundle=write_opaque("instrument-dev-locked-policy"),
            selection_inputs=(registry_ref,),
            selection_outputs=selected_references_tuple,
            source_commit_sha1="a" * 40,
            source_tree_sha256=_digest("instrument-dev-selection-source-tree"),
            fixed_choices=tuple(
                sorted(
                    fixed_choices,
                    key=lambda item: (
                        item.hypothesis_id.value,
                        item.choice.family_id,
                    ),
                )
            ),
            resolved_choices=tuple(
                sorted(
                    resolved_choices,
                    key=lambda item: (
                        item.hypothesis_id.value,
                        item.choice.family_id,
                    ),
                )
            ),
            unresolved_choices=tuple(
                sorted(
                    unresolved_choices,
                    key=lambda item: (
                        item.hypothesis_id.value,
                        item.choice.family_id,
                    ),
                )
            ),
            integer_output_authorizations=(),
            confirmation_access_commitment=write_opaque(
                "instrument-dev-confirmation-commitment"
            ),
            sealed_before_confirmation_access=True,
            claim_ceiling=ClaimLevel.LEVEL_1G,
        )
        artifacts["selection"] = selection
        extra_roots.append(_artifact_ref(selection))

    if split_graph_spec_substrate:
        artifacts["secondary_substrate"] = secondary_substrate

    artifact_entries: dict[str, BundleArtifactEntry] = {}
    for name, artifact in artifacts.items():
        relative_path = f"artifacts/{name}.json"
        artifact_bytes = artifact.canonical_bytes
        (root / relative_path).write_bytes(artifact_bytes)
        artifact_entries[name] = BundleArtifactEntry(
            path=relative_path,
            source_sha256=hashlib.sha256(artifact_bytes).hexdigest(),
            reference=_artifact_ref(artifact),
        )

    registry_entry = BundleArtifactEntry(
        path=registry_path.relative_to(root).as_posix(),
        source_sha256=loaded_registry.source_sha256,
        reference=registry_ref,
    )
    context_entry = BundleContextBankEntry(
        path=context_path.relative_to(root).as_posix(),
        source_sha256=loaded_context.source_sha256,
        reference=context_ref,
        allowed_role=ContextRole.EXAMPLE,
    )
    roots = tuple(
        sorted(
            (
                _artifact_ref(support),
                registry_ref,
                *extra_roots,
            ),
            key=_root_sort_key,
        )
    )
    manifest = InstrumentBundleManifest(
        bundle_id="minimal-rooted-instrument-bundle",
        roots=roots,
        instrument_artifacts=tuple(
            sorted(
                artifact_entries.values(),
                key=lambda entry: entry.sort_key,
            )
        ),
        hypothesis_registries=(registry_entry,),
        context_banks=(context_entry,),
        payloads=tuple(sorted(payload_entries, key=lambda entry: entry.sort_key)),
    )
    manifest_path = root / "bundle.json"
    _write_manifest(manifest_path, manifest)
    return BundleFixture(
        root=root,
        manifest_path=manifest_path,
        manifest=manifest,
        artifacts=artifacts,
        artifact_entries=artifact_entries,
        payload_entries=manifest.payloads,
    )


def test_bundle_manifest_round_trips_canonically(tmp_path: Path) -> None:
    fixture = _build_bundle(tmp_path)

    reconstructed = InstrumentBundleManifest.from_dict(fixture.manifest.to_dict())

    assert reconstructed == fixture.manifest
    assert reconstructed.canonical_bytes == fixture.manifest.canonical_bytes
    assert (
        reconstructed.canonical_sha256
        == hashlib.sha256(reconstructed.canonical_bytes).hexdigest()
    )
    assert not reconstructed.canonical_bytes.endswith(b"\n")


def test_loader_resolves_closed_bundle_and_reports_cli_ready_facts(
    tmp_path: Path,
) -> None:
    fixture = _build_bundle(tmp_path)

    loaded = load_instrument_bundle(
        fixture.manifest_path,
        expected_source_sha256=fixture.manifest.canonical_sha256,
        expected_canonical_sha256=fixture.manifest.canonical_sha256,
    )

    assert loaded.manifest == fixture.manifest
    assert loaded.source_path == fixture.manifest_path.resolve()
    assert loaded.source_sha256 == fixture.manifest.canonical_sha256
    assert loaded.canonical_sha256 == fixture.manifest.canonical_sha256
    assert len(loaded.artifacts) == 6
    assert len(loaded.payloads) == 17
    assert all(not hasattr(payload, "source_path") for payload in loaded.payloads)
    assert loaded.artifact_reference_count == 6
    assert loaded.payload_reference_count == 17
    assert loaded.cross_manifest_join_count > 0
    assert loaded.manifest.subject_data_access_authorized is False
    assert loaded.resolve(fixture.manifest.roots[-1]) == fixture.artifacts["support"]
    assert GRAPH_VERTICES != SUBSTRATE_ROWS


def test_instrument_bundle_cli_reports_closed_integrity_scope(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fixture = _build_bundle(tmp_path)

    exit_code = main(
        [
            "instrument-bundle",
            "validate",
            "--path",
            str(fixture.manifest_path),
            "--expected-source-sha256",
            fixture.manifest.canonical_sha256,
            "--expected-canonical-sha256",
            fixture.manifest.canonical_sha256,
        ]
    )
    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert exit_code == 0
    assert captured.err == ""
    assert report["status"] == "valid"
    assert report["validation_scope"] == "closed_integrity_bundle"
    assert report["bundle_integrity_validated"] is True
    assert report["artifact_references_resolved"] is True
    assert report["payload_references_resolved"] is True
    assert report["dependency_graph_acyclic"] is True
    assert report["payload_content_decoded"] is False
    assert report["row_identity_content_recomputed"] is False
    assert report["subject_roles_allowed"] is False
    assert report["subject_data_accessed"] is False
    assert report["subject_execution_performed"] is False
    assert report["root_artifacts"] == 2
    assert report["artifact_entries"] == 6
    assert report["payload_entries"] == 17
    assert report["artifact_reference_count"] == 6
    assert report["payload_reference_count"] == 17
    assert report["cross_manifest_join_count"] > 0


def test_loader_rejects_wrong_expected_bundle_digests(tmp_path: Path) -> None:
    fixture = _build_bundle(tmp_path)

    with pytest.raises(
        InstrumentBundleIntegrityError,
        match="bundle_source_digest_mismatch",
    ):
        load_instrument_bundle(
            fixture.manifest_path,
            expected_source_sha256="0" * 64,
        )
    with pytest.raises(
        InstrumentBundleIntegrityError,
        match="bundle_canonical_digest_mismatch",
    ):
        load_instrument_bundle(
            fixture.manifest_path,
            expected_canonical_sha256="0" * 64,
        )


@pytest.mark.parametrize(
    ("member_kind", "expected_code"),
    [
        ("instrument", "instrument_member_integrity_mismatch"),
        ("registry", "registry_member_integrity_mismatch"),
        ("context_bank", "context_bank_member_integrity_mismatch"),
    ],
)
def test_loader_preserves_member_integrity_error_classification(
    tmp_path: Path,
    member_kind: str,
    expected_code: str,
) -> None:
    fixture = _build_bundle(tmp_path)
    if member_kind == "instrument":
        relative_path = fixture.artifact_entries["graph_spec"].path
    elif member_kind == "registry":
        relative_path = fixture.manifest.hypothesis_registries[0].path
    else:
        relative_path = fixture.manifest.context_banks[0].path
    member_path = fixture.root / relative_path
    member_path.write_bytes(member_path.read_bytes() + b" ")

    with pytest.raises(InstrumentBundleIntegrityError) as caught:
        load_instrument_bundle(fixture.manifest_path)

    assert caught.value.code == expected_code


def test_loader_classifies_context_contract_violation_as_member_schema(
    tmp_path: Path,
) -> None:
    fixture = _build_bundle(tmp_path)
    entry = fixture.manifest.context_banks[0]
    member_path = fixture.root / entry.path
    invalid_source = member_path.read_bytes().replace(
        b"template_ids: [null]",
        b"template_ids: [null, null]",
        1,
    )
    member_path.write_bytes(invalid_source)
    invalid_entry = replace(
        entry,
        source_sha256=hashlib.sha256(invalid_source).hexdigest(),
    )
    _write_manifest(
        fixture.manifest_path,
        replace(fixture.manifest, context_banks=(invalid_entry,)),
    )

    with pytest.raises(InstrumentBundleSchemaError) as caught:
        load_instrument_bundle(fixture.manifest_path)

    assert caught.value.code == "context_bank_member_invalid"


def test_loader_classifies_post_validation_member_read_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_bundle(tmp_path)
    original_read = bundle_loader_module._read_descriptor_bytes
    read_count = 0

    def fail_second_read(
        descriptor: int,
        *,
        maximum_bytes: int,
    ) -> bytes:
        nonlocal read_count
        read_count += 1
        if read_count == 2:
            raise PermissionError("simulated descriptor read failure")
        return original_read(
            descriptor,
            maximum_bytes=maximum_bytes,
        )

    monkeypatch.setattr(
        bundle_loader_module,
        "_read_descriptor_bytes",
        fail_second_read,
    )

    with pytest.raises(InstrumentBundleResolutionError) as caught:
        load_instrument_bundle(fixture.manifest_path)

    assert caught.value.code == "bundle_member_unreadable"


def test_loader_does_not_launder_unexpected_member_loader_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_bundle(tmp_path)

    def fail_internally(*args: object, **kwargs: object) -> object:
        raise RuntimeError("simulated internal loader defect")

    monkeypatch.setattr(
        bundle_loader_module,
        "_load_instrument_artifact_from_bytes",
        fail_internally,
    )

    with pytest.raises(RuntimeError, match="simulated internal loader defect"):
        load_instrument_bundle(fixture.manifest_path)


@pytest.mark.parametrize(
    "parser_name",
    [
        "_load_instrument_artifact_from_bytes",
        "_load_hypothesis_registry_from_bytes",
        "_load_context_bank_from_bytes",
    ],
)
def test_loader_does_not_launder_unexpected_member_parser_oserror(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    parser_name: str,
) -> None:
    fixture = _build_bundle(tmp_path)

    def fail_internally(*args: object, **kwargs: object) -> object:
        raise OSError("simulated internal parser defect")

    monkeypatch.setattr(
        bundle_loader_module,
        parser_name,
        fail_internally,
    )

    with pytest.raises(OSError, match="simulated internal parser defect"):
        load_instrument_bundle(fixture.manifest_path)


def test_loader_rejects_missing_artifact_member(tmp_path: Path) -> None:
    fixture = _build_bundle(tmp_path)
    graph_path = fixture.root / fixture.artifact_entries["graph_spec"].path
    graph_path.unlink()

    with pytest.raises(
        InstrumentBundleResolutionError,
        match="bundle_member_missing",
    ):
        load_instrument_bundle(fixture.manifest_path)


def test_loader_classifies_member_open_permission_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_bundle(tmp_path)
    target_name = Path(fixture.manifest.instrument_artifacts[0].path).name
    original_open = os.open

    def fail_target_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if path == target_name and dir_fd is not None:
            raise PermissionError("simulated member open denial")
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", fail_target_open)

    with pytest.raises(InstrumentBundleResolutionError) as caught:
        load_instrument_bundle(fixture.manifest_path)

    assert caught.value.code == "bundle_member_unreadable"


def test_loader_classifies_member_path_inspection_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_bundle(tmp_path)
    target_name = Path(fixture.manifest.instrument_artifacts[0].path).name
    original_stat = os.stat

    def fail_target_stat(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *args: object,
        **kwargs: object,
    ) -> os.stat_result:
        if path == target_name and kwargs.get("dir_fd") is not None:
            raise PermissionError("simulated member path inspection denial")
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(os, "stat", fail_target_stat)

    with pytest.raises(InstrumentBundleResolutionError) as caught:
        load_instrument_bundle(fixture.manifest_path)

    assert caught.value.code == "bundle_member_unreadable"


@pytest.mark.parametrize(
    "manifest_path",
    [
        Path(),
        Path(Path.cwd().anchor),
    ],
)
def test_loader_classifies_empty_name_manifest_paths(
    manifest_path: Path,
) -> None:
    with pytest.raises(InstrumentBundleSchemaError) as caught:
        load_instrument_bundle(manifest_path)

    assert caught.value.code == "bundle_manifest_unreadable"


@pytest.mark.parametrize(
    ("member_kind", "expected_code"),
    [
        ("manifest", "bundle_manifest_symlink"),
        ("instrument", "symlink_member_forbidden"),
        ("registry", "symlink_member_forbidden"),
        ("context_bank", "symlink_member_forbidden"),
        ("payload", "symlink_member_forbidden"),
    ],
)
def test_loader_rejects_symlink_inserted_immediately_before_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    member_kind: str,
    expected_code: str,
) -> None:
    fixture = _build_bundle(tmp_path)
    relative_path = _member_relative_path(fixture, member_kind)
    target_path = fixture.root / relative_path
    target_name = target_path.name
    replacement_path = tmp_path / f"outside-{member_kind}-member"
    replacement_path.write_bytes(target_path.read_bytes())
    original_open = os.open
    replaced = False

    def replace_before_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal replaced
        if path == target_name and dir_fd is not None and not replaced:
            target_path.unlink()
            target_path.symlink_to(replacement_path)
            replaced = True
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", replace_before_open)

    with pytest.raises(InstrumentBundleError) as caught:
        load_instrument_bundle(fixture.manifest_path)

    assert replaced is True
    assert caught.value.code == expected_code


@pytest.mark.parametrize(
    "member_kind",
    ["manifest", "instrument", "registry", "context_bank", "payload"],
)
def test_loader_consumes_opened_descriptor_after_path_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    member_kind: str,
) -> None:
    fixture = _build_bundle(tmp_path)
    relative_path = _member_relative_path(fixture, member_kind)
    target_path = fixture.root / relative_path
    original_open_member = bundle_loader_module._open_bundle_member
    replaced = False

    @contextmanager
    def replace_after_descriptor_open(**kwargs: object):
        nonlocal replaced
        with original_open_member(**kwargs) as opened:
            if kwargs["relative_path"] == relative_path and not replaced:
                corrupted = bytearray(target_path.read_bytes())
                corrupted[-1] ^= 1
                replacement = target_path.with_name(f"{target_path.name}.replacement")
                replacement.write_bytes(corrupted)
                os.replace(replacement, target_path)
                replaced = True
            yield opened

    monkeypatch.setattr(
        bundle_loader_module,
        "_open_bundle_member",
        replace_after_descriptor_open,
    )

    load_instrument_bundle(fixture.manifest_path)

    assert replaced is True


def test_loader_rejects_intermediate_directory_symlink(tmp_path: Path) -> None:
    fixture = _build_bundle(tmp_path)
    artifact_directory = fixture.root / "artifacts"
    real_directory = fixture.root / "artifacts-real"
    artifact_directory.rename(real_directory)
    artifact_directory.symlink_to(real_directory, target_is_directory=True)

    with pytest.raises(InstrumentBundleResolutionError) as caught:
        load_instrument_bundle(fixture.manifest_path)

    assert caught.value.code == "symlink_member_forbidden"


def test_loader_classifies_raced_intermediate_symlink_as_unreadable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_bundle(tmp_path)
    artifact_directory = fixture.root / "artifacts"
    real_directory = fixture.root / "artifacts-real"
    original_open = os.open
    replaced = False

    def replace_directory_before_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal replaced
        if path == "artifacts" and dir_fd is not None and not replaced:
            artifact_directory.rename(real_directory)
            artifact_directory.symlink_to(real_directory, target_is_directory=True)
            replaced = True
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", replace_directory_before_open)

    with pytest.raises(InstrumentBundleResolutionError) as caught:
        load_instrument_bundle(fixture.manifest_path)

    assert replaced is True
    assert caught.value.code == "bundle_member_unreadable"


def test_loader_rejects_bundle_root_replacement_after_manifest_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_bundle(tmp_path)
    original_read_manifest = bundle_loader_module._read_bundle_manifest
    replaced_root = tmp_path / "bundle-original"

    def replace_root_after_read(*args: object, **kwargs: object):
        result = original_read_manifest(*args, **kwargs)
        fixture.root.rename(replaced_root)
        fixture.root.mkdir()
        return result

    monkeypatch.setattr(
        bundle_loader_module,
        "_read_bundle_manifest",
        replace_root_after_read,
    )

    with pytest.raises(InstrumentBundleResolutionError) as caught:
        load_instrument_bundle(fixture.manifest_path)

    assert caught.value.code == "bundle_member_unreadable"


def test_loader_classifies_manifest_descriptor_inspection_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_bundle(tmp_path)
    original_fstat = os.fstat
    fstat_count = 0

    def fail_manifest_fstat(
        descriptor: int,
    ) -> os.stat_result:
        nonlocal fstat_count
        fstat_count += 1
        if fstat_count == 2:
            raise PermissionError("simulated manifest descriptor denial")
        return original_fstat(descriptor)

    monkeypatch.setattr(os, "fstat", fail_manifest_fstat)

    with pytest.raises(InstrumentBundleSchemaError) as caught:
        load_instrument_bundle(fixture.manifest_path)

    assert caught.value.code == "bundle_manifest_unreadable"


def test_loader_reports_unavailable_secure_member_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_bundle(tmp_path)
    monkeypatch.setattr(
        bundle_loader_module,
        "_SUPPORTS_SECURE_DIR_FD",
        False,
    )

    with pytest.raises(InstrumentBundleResolutionError) as caught:
        load_instrument_bundle(fixture.manifest_path)

    assert caught.value.code == "secure_member_open_unavailable"


def test_loader_rejects_missing_artifact_reference_entry(
    tmp_path: Path,
) -> None:
    fixture = _build_bundle(tmp_path)
    document = fixture.manifest.to_dict()
    document["instrument_artifacts"] = [
        entry
        for entry in document["instrument_artifacts"]
        if entry["reference"]["artifact_id"] != "bundle-graph-spec"
    ]
    _write_manifest_document(fixture, document)

    with pytest.raises(
        InstrumentBundleResolutionError,
        match="artifact_reference_missing",
    ):
        load_instrument_bundle(fixture.manifest_path)


def test_loader_rejects_unreferenced_artifact_entry(tmp_path: Path) -> None:
    fixture = _build_bundle(tmp_path)
    orphan = replace(
        fixture.artifacts["support"],
        artifact_id="orphan-support",
    )
    orphan_bytes = orphan.canonical_bytes
    orphan_path = fixture.root / "artifacts" / "orphan.json"
    orphan_path.write_bytes(orphan_bytes)
    orphan_entry = BundleArtifactEntry(
        path="artifacts/orphan.json",
        source_sha256=hashlib.sha256(orphan_bytes).hexdigest(),
        reference=_artifact_ref(orphan),
    )
    manifest = replace(
        fixture.manifest,
        instrument_artifacts=tuple(
            sorted(
                (*fixture.manifest.instrument_artifacts, orphan_entry),
                key=lambda entry: entry.sort_key,
            )
        ),
    )
    _write_manifest(fixture.manifest_path, manifest)

    with pytest.raises(
        InstrumentBundleResolutionError,
        match="unreferenced_artifact_entry",
    ):
        load_instrument_bundle(fixture.manifest_path)


def test_bundle_schema_rejects_duplicate_artifact_entry(tmp_path: Path) -> None:
    fixture = _build_bundle(tmp_path)
    document = fixture.manifest.to_dict()
    duplicate = deepcopy(document["instrument_artifacts"][0])
    document["instrument_artifacts"].append(duplicate)
    _write_manifest_document(fixture, document)

    with pytest.raises(
        InstrumentBundleSchemaError,
        match="bundle_manifest_invalid",
    ):
        load_instrument_bundle(fixture.manifest_path)


def test_bundle_schema_rejects_registry_only_bundle(tmp_path: Path) -> None:
    fixture = _build_bundle(tmp_path)
    document = fixture.manifest.to_dict()
    document["roots"] = [document["hypothesis_registries"][0]["reference"]]
    document["instrument_artifacts"] = []
    document["context_banks"] = []
    document["payloads"] = []
    _write_manifest_document(fixture, document)

    with pytest.raises(
        InstrumentBundleSchemaError,
        match="instrument bundle must contain an instrument artifact",
    ):
        load_instrument_bundle(fixture.manifest_path)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("artifact_id", "wrong-artifact-id"),
        ("canonical_sha256", "0" * 64),
    ],
)
def test_loader_rejects_indexed_artifact_identity_mismatch(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    fixture = _build_bundle(tmp_path)
    entry = fixture.artifact_entries["candidate_graph"]
    wrong_reference = replace(entry.reference, **{field: value})
    wrong_entry = replace(entry, reference=wrong_reference)
    manifest = replace(
        fixture.manifest,
        instrument_artifacts=tuple(
            sorted(
                (
                    *(
                        item
                        for item in fixture.manifest.instrument_artifacts
                        if item is not entry
                    ),
                    wrong_entry,
                ),
                key=lambda item: item.sort_key,
            )
        ),
    )
    _write_manifest(fixture.manifest_path, manifest)

    with pytest.raises(
        InstrumentBundleIntegrityError,
        match="instrument_member_identity_mismatch",
    ):
        load_instrument_bundle(fixture.manifest_path)


def test_bundle_schema_rejects_reference_schema_type_mismatch(
    tmp_path: Path,
) -> None:
    fixture = _build_bundle(tmp_path)
    document = fixture.manifest.to_dict()
    graph_entry = next(
        entry
        for entry in document["instrument_artifacts"]
        if entry["reference"]["artifact_id"] == "bundle-candidate-graph"
    )
    graph_entry["reference"]["schema_version"] = ARTIFACT_SCHEMA_VERSION_BY_TYPE[
        ArtifactType.SUPPORT_DIAGNOSTIC
    ]
    _write_manifest_document(fixture, document)

    with pytest.raises(
        InstrumentBundleSchemaError,
        match="bundle_manifest_invalid",
    ):
        load_instrument_bundle(fixture.manifest_path)


def test_bundle_schema_rejects_parent_path_escape(tmp_path: Path) -> None:
    fixture = _build_bundle(tmp_path)
    document = fixture.manifest.to_dict()
    document["instrument_artifacts"][0]["path"] = "../escape.json"
    _write_manifest_document(fixture, document)

    with pytest.raises(
        InstrumentBundleSchemaError,
        match="bundle_manifest_invalid",
    ):
        load_instrument_bundle(fixture.manifest_path)


def test_loader_rejects_symlinked_payload_member(tmp_path: Path) -> None:
    fixture = _build_bundle(tmp_path)
    entry = fixture.payload_entries[0]
    original = fixture.root / entry.path
    symlink_path = original.with_name(f"{original.name}.link")
    os.symlink(original.name, symlink_path)
    replacement = replace(
        entry,
        path=symlink_path.relative_to(fixture.root).as_posix(),
    )
    manifest = replace(
        fixture.manifest,
        payloads=tuple(
            sorted(
                (
                    *(item for item in fixture.manifest.payloads if item is not entry),
                    replacement,
                ),
                key=lambda item: item.sort_key,
            )
        ),
    )
    _write_manifest(fixture.manifest_path, manifest)

    with pytest.raises(
        InstrumentBundleResolutionError,
        match="symlink_member_forbidden",
    ):
        load_instrument_bundle(fixture.manifest_path)


def test_loader_rejects_payload_with_external_hardlink(tmp_path: Path) -> None:
    fixture = _build_bundle(tmp_path)
    entry = fixture.payload_entries[0]
    indexed_path = fixture.root / entry.path
    outside_path = tmp_path / "outside-payload.bin"
    indexed_path.rename(outside_path)
    os.link(outside_path, indexed_path)

    with pytest.raises(InstrumentBundleResolutionError) as caught:
        load_instrument_bundle(fixture.manifest_path)

    assert caught.value.code == "bundle_member_alias"


def test_loader_rejects_missing_payload_reference_entry(
    tmp_path: Path,
) -> None:
    fixture = _build_bundle(tmp_path)
    manifest = replace(
        fixture.manifest,
        payloads=fixture.manifest.payloads[1:],
    )
    _write_manifest(fixture.manifest_path, manifest)

    with pytest.raises(
        InstrumentBundleResolutionError,
        match="payload_reference_missing",
    ):
        load_instrument_bundle(fixture.manifest_path)


def test_loader_rejects_unreferenced_payload_entry(tmp_path: Path) -> None:
    fixture = _build_bundle(tmp_path)
    payload_bytes = b"unreferenced payload"
    payload_path = fixture.root / "payloads" / "orphan.bin"
    payload_path.write_bytes(payload_bytes)
    reference = PayloadRef(
        kind=PayloadKind.OPAQUE,
        sha256=hashlib.sha256(payload_bytes).hexdigest(),
        byte_length=len(payload_bytes),
        media_type="application/octet-stream",
    )
    orphan = BundlePayloadEntry(
        path="payloads/orphan.bin",
        reference=reference,
    )
    manifest = replace(
        fixture.manifest,
        payloads=tuple(
            sorted(
                (*fixture.manifest.payloads, orphan),
                key=lambda item: item.sort_key,
            )
        ),
    )
    _write_manifest(fixture.manifest_path, manifest)

    with pytest.raises(
        InstrumentBundleResolutionError,
        match="unreferenced_payload_entry",
    ):
        load_instrument_bundle(fixture.manifest_path)


def test_bundle_schema_rejects_duplicate_payload_entry(tmp_path: Path) -> None:
    fixture = _build_bundle(tmp_path)
    document = fixture.manifest.to_dict()
    document["payloads"].append(deepcopy(document["payloads"][0]))
    _write_manifest_document(fixture, document)

    with pytest.raises(
        InstrumentBundleSchemaError,
        match="bundle_manifest_invalid",
    ):
        load_instrument_bundle(fixture.manifest_path)


def test_loader_rejects_missing_payload_file(tmp_path: Path) -> None:
    fixture = _build_bundle(tmp_path)
    entry = fixture.payload_entries[0]
    (fixture.root / entry.path).unlink()

    with pytest.raises(
        InstrumentBundleResolutionError,
        match="bundle_member_missing",
    ):
        load_instrument_bundle(fixture.manifest_path)


def test_loader_classifies_post_validation_payload_read_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_bundle(tmp_path)

    def fail_read(*args: object, **kwargs: object) -> tuple[int, str]:
        raise PermissionError("simulated post-validation payload read failure")

    monkeypatch.setattr(
        bundle_loader_module,
        "_stream_payload_identity",
        fail_read,
    )

    with pytest.raises(InstrumentBundleResolutionError) as caught:
        load_instrument_bundle(fixture.manifest_path)

    assert caught.value.code == "bundle_member_unreadable"


def test_loader_preserves_missing_classification_at_payload_read_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_bundle(tmp_path)

    def disappear(*args: object, **kwargs: object) -> tuple[int, str]:
        raise FileNotFoundError("simulated payload disappearance")

    monkeypatch.setattr(
        bundle_loader_module,
        "_stream_payload_identity",
        disappear,
    )

    with pytest.raises(InstrumentBundleResolutionError) as caught:
        load_instrument_bundle(fixture.manifest_path)

    assert caught.value.code == "bundle_member_missing"


def test_loader_does_not_launder_unexpected_payload_reader_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_bundle(tmp_path)

    def fail_internally(*args: object, **kwargs: object) -> tuple[int, str]:
        raise RuntimeError("simulated internal payload reader defect")

    monkeypatch.setattr(
        bundle_loader_module,
        "_stream_payload_identity",
        fail_internally,
    )

    with pytest.raises(RuntimeError, match="internal payload reader defect"):
        load_instrument_bundle(fixture.manifest_path)


def test_loader_rejects_payload_digest_mismatch(tmp_path: Path) -> None:
    fixture = _build_bundle(tmp_path)
    entry = fixture.payload_entries[0]
    path = fixture.root / entry.path
    payload = bytearray(path.read_bytes())
    payload[-1] ^= 1
    path.write_bytes(payload)

    with pytest.raises(
        InstrumentBundleIntegrityError,
        match="payload_digest_mismatch",
    ):
        load_instrument_bundle(fixture.manifest_path)


def test_loader_rejects_payload_byte_length_mismatch(tmp_path: Path) -> None:
    fixture = _build_bundle(tmp_path)
    entry = fixture.payload_entries[0]
    path = fixture.root / entry.path
    path.write_bytes(path.read_bytes() + b"x")

    with pytest.raises(
        InstrumentBundleIntegrityError,
        match="payload_byte_length_mismatch",
    ):
        load_instrument_bundle(fixture.manifest_path)


def test_graph_spec_and_candidate_must_bind_same_substrate(
    tmp_path: Path,
) -> None:
    fixture = _build_bundle(
        tmp_path,
        split_graph_spec_substrate=True,
    )

    with pytest.raises(
        InstrumentBundleConsistencyError,
        match="graph_spec_substrate_mismatch",
    ):
        load_instrument_bundle(fixture.manifest_path)


def test_graph_allowed_role_must_match_substrate_role(
    tmp_path: Path,
) -> None:
    fixture = _build_bundle(
        tmp_path,
        graph_allowed_role=FitRole.INSTRUMENT_DEV,
    )

    with pytest.raises(
        InstrumentBundleConsistencyError,
        match="graph_role_mismatch",
    ):
        load_instrument_bundle(fixture.manifest_path)


def test_support_row_identity_must_match_substrate_rows(
    tmp_path: Path,
) -> None:
    fixture = _build_bundle(
        tmp_path,
        support_row_identity=_digest("wrong-support-row-order"),
    )

    with pytest.raises(
        InstrumentBundleConsistencyError,
        match="row_identity_join_mismatch",
    ):
        load_instrument_bundle(fixture.manifest_path)


def test_dependency_walk_handles_more_than_1500_acyclic_members() -> None:
    keys = tuple(
        (
            ArtifactType.SUPPORT_DIAGNOSTIC,
            f"deep-member-{index:04d}",
        )
        for index in range(1_601)
    )
    adjacency = {
        key: (() if index == len(keys) - 1 else (keys[index + 1],))
        for index, key in enumerate(keys)
    }
    root = ArtifactRef(
        artifact_type=keys[0][0],
        schema_version=ARTIFACT_SCHEMA_VERSION_BY_TYPE[keys[0][0]],
        artifact_id=keys[0][1],
        canonical_sha256=_digest("deep-root"),
    )

    _detect_cycle(adjacency)
    reachable = _reachable_from_roots(
        roots=(root,),
        adjacency=adjacency,
    )

    assert reachable == set(keys)


def test_dependency_walk_reports_deep_cycle_without_recursion_error() -> None:
    keys = tuple(
        (
            ArtifactType.SUPPORT_DIAGNOSTIC,
            f"deep-cycle-member-{index:04d}",
        )
        for index in range(1_601)
    )
    adjacency = {
        key: (keys[(index + 1) % len(keys)],) for index, key in enumerate(keys)
    }

    with pytest.raises(
        InstrumentBundleResolutionError,
        match="artifact_dependency_cycle",
    ) as error:
        _detect_cycle(adjacency)

    assert error.value.code == "artifact_dependency_cycle"


def test_defect_field_can_support_level_1g_edge_observation(
    tmp_path: Path,
) -> None:
    fixture = _build_bundle(
        tmp_path,
        defect_edge_claim=ClaimLevel.LEVEL_1G,
    )

    loaded = load_instrument_bundle(fixture.manifest_path)

    edge = fixture.artifacts["edge_connection"]
    assert loaded.resolve(_artifact_ref(edge)) == edge
    assert edge.field_branch is ScientificBranch.DEFECT
    assert edge.claim_ceiling is ClaimLevel.LEVEL_1G
    assert fixture.artifacts["order_field"].claim_ceiling is (ClaimLevel.LEVEL_1D)


def test_defect_field_rejects_level_2g_edge_over_ceiling(
    tmp_path: Path,
) -> None:
    fixture = _build_bundle(
        tmp_path,
        defect_edge_claim=ClaimLevel.LEVEL_2G,
    )

    with pytest.raises(
        InstrumentBundleConsistencyError,
        match="claim_ceiling_join_mismatch",
    ):
        load_instrument_bundle(fixture.manifest_path)


def test_selection_accepts_instrument_dev_evidence_when_role_is_resolved(
    tmp_path: Path,
) -> None:
    fixture = _build_bundle(
        tmp_path,
        substrate_role=FitRole.INSTRUMENT_DEV,
        include_instrument_dev_selection=True,
    )

    loaded = load_instrument_bundle(fixture.manifest_path)

    selection = fixture.artifacts["selection"]
    selected_roles = {
        item.choice.selected_id
        for item in selection.resolved_choices
        if item.choice.family_id == "fit_role"
    }
    assert selected_roles == {FitRole.INSTRUMENT_DEV.value}
    assert loaded.resolve(_artifact_ref(selection)) == selection
    assert fixture.artifacts["support"].fit_role is FitRole.INSTRUMENT_DEV


def test_selection_rejects_traced_artifact_for_retained_hypothesis(
    tmp_path: Path,
) -> None:
    fixture = _build_bundle(
        tmp_path,
        substrate_role=FitRole.INSTRUMENT_DEV,
        defect_edge_claim=ClaimLevel.LEVEL_1G,
        include_instrument_dev_selection=True,
        select_retained_f3_artifact=True,
    )

    with pytest.raises(
        InstrumentBundleConsistencyError,
        match="selected_artifact_hypothesis_not_advanced",
    ) as error:
        load_instrument_bundle(fixture.manifest_path)

    assert error.value.code == "selected_artifact_hypothesis_not_advanced"


def test_level_2t_authorization_accepts_matching_substrate_role_and_axis(
    tmp_path: Path,
) -> None:
    fixture = _build_bundle(
        tmp_path,
        substrate_role=FitRole.INSTRUMENT_DEV,
        include_level_2t=True,
    )

    loaded = load_instrument_bundle(fixture.manifest_path)

    defect_loop = fixture.artifacts["defect_loop"]
    field_graph = fixture.artifacts["candidate_graph"]
    cycle_graph = fixture.artifacts["cycle_graph"]
    assert loaded.resolve(_artifact_ref(defect_loop)) == defect_loop
    assert defect_loop.claim_ceiling is ClaimLevel.LEVEL_2T
    assert defect_loop.cycle_graph != _artifact_ref(field_graph)
    assert defect_loop.loop_order_sha256 != cycle_graph.cycle_order_sha256


def test_level_2t_authorization_requires_selected_precursor(
    tmp_path: Path,
) -> None:
    fixture = _build_bundle(
        tmp_path,
        include_level_2t=True,
        level_2t_selected_precursor=False,
    )

    with pytest.raises(
        InstrumentBundleConsistencyError,
        match="integer_authorization_selected_path_missing",
    ) as error:
        load_instrument_bundle(fixture.manifest_path)

    assert error.value.code == "integer_authorization_selected_path_missing"


def test_level_2t_authorization_rejects_substrate_role_mismatch(
    tmp_path: Path,
) -> None:
    fixture = _build_bundle(
        tmp_path,
        substrate_role=FitRole.INSTRUMENT_DEV,
        include_level_2t=True,
        level_2t_selection_role=FitRole.CALIBRATION_SELECTION,
    )

    with pytest.raises(
        InstrumentBundleConsistencyError,
        match="selected_artifact_fit_role_mismatch",
    ) as error:
        load_instrument_bundle(fixture.manifest_path)

    assert error.value.code == "selected_artifact_fit_role_mismatch"


def test_level_2t_authorization_rejects_observation_axis_mismatch(
    tmp_path: Path,
) -> None:
    fixture = _build_bundle(
        tmp_path,
        include_level_2t=True,
        level_2t_selection_axis=EvolutionAxis.TOKEN_POSITION,
    )

    with pytest.raises(
        InstrumentBundleConsistencyError,
        match="selected_artifact_observation_axis_mismatch",
    ) as error:
        load_instrument_bundle(fixture.manifest_path)

    assert error.value.code == "selected_artifact_observation_axis_mismatch"
