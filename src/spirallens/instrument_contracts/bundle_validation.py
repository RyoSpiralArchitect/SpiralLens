"""Cross-manifest joins for a resolved instrument integrity bundle."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypeVar

from spirallens.contexts import ContextBank

from .artifacts import (
    CalibrationConfirmationResult,
    CalibrationSelectionDecision,
    CandidateGraph,
    CoreCandidate,
    CoreScore,
    DefectLoopEstimate,
    EdgeConnection,
    ExplicitCoreGraphBinding,
    GeometricFieldEstimate,
    GeometryLoopEstimate,
    GraphConstructionSpec,
    GraphFreeBinding,
    GroundTruthAnchor,
    InheritedFieldGraphBinding,
    OrderParameterField,
    OrderParameterSpec,
    SubstrateBinding,
    SupportDiagnostic,
)
from .common import (
    ArtifactRef,
    ArtifactType,
    ClaimLevel,
    FitRole,
    HypothesisDisposition,
    HypothesisId,
    ResolutionState,
    RuleChoice,
    ScientificBranch,
)
from .registry import HypothesisRegistry, HypothesisSpec


_CLAIMS_AT_OR_BELOW: Mapping[ClaimLevel, frozenset[ClaimLevel]] = {
    ClaimLevel.LEVEL_0: frozenset({ClaimLevel.LEVEL_0}),
    ClaimLevel.LEVEL_1G: frozenset({ClaimLevel.LEVEL_0, ClaimLevel.LEVEL_1G}),
    ClaimLevel.LEVEL_1D: frozenset({ClaimLevel.LEVEL_0, ClaimLevel.LEVEL_1D}),
    ClaimLevel.LEVEL_2G: frozenset(
        {
            ClaimLevel.LEVEL_0,
            ClaimLevel.LEVEL_1G,
            ClaimLevel.LEVEL_2G,
        }
    ),
    ClaimLevel.LEVEL_2T: frozenset(
        {
            ClaimLevel.LEVEL_0,
            ClaimLevel.LEVEL_1D,
            ClaimLevel.LEVEL_2T,
        }
    ),
    ClaimLevel.LEVEL_3: frozenset(set(ClaimLevel)),
}
_DEFECT_FIELD_TO_EDGE_CLAIMS: Mapping[
    ClaimLevel,
    frozenset[ClaimLevel],
] = {
    ClaimLevel.LEVEL_0: frozenset({ClaimLevel.LEVEL_0}),
    ClaimLevel.LEVEL_1D: frozenset({ClaimLevel.LEVEL_0, ClaimLevel.LEVEL_1G}),
    ClaimLevel.LEVEL_2T: frozenset(
        {
            ClaimLevel.LEVEL_0,
            ClaimLevel.LEVEL_1G,
            ClaimLevel.LEVEL_2G,
        }
    ),
}
_SUBJECT_ROLES = {
    FitRole.SUBJECT_DISCOVERY,
    FitRole.SUBJECT_CONFIRMATION,
}
_STAGE_SAFE_SELECTION_ROLES = {
    FitRole.INSTRUMENT_DEV,
    FitRole.CALIBRATION_SELECTION,
}
_REGISTRY_CHOICE_FIELDS = (
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
_SPEC_REGISTRY_CHOICE_FIELDS = (
    "interpolation_rule",
    "lift_rule",
    "trivialization_rule",
    "reference_rule",
)

ResolvedType = TypeVar("ResolvedType")


@dataclass(frozen=True, slots=True)
class _HypothesisArtifactTrace:
    hypothesis_id: HypothesisId
    hypothesis_registry: ArtifactRef
    substrate: ArtifactRef
    order_parameter_spec_reference: ArtifactRef | None = None
    order_parameter_spec: OrderParameterSpec | None = None


@dataclass(slots=True)
class _JoinValidator:
    index: Mapping[tuple[ArtifactType, str], object]
    checks: int = 0

    def require(self, condition: bool, code: str, message: str) -> None:
        from .bundle_loader import InstrumentBundleConsistencyError

        if not condition:
            raise InstrumentBundleConsistencyError(code, message)
        self.checks += 1

    def resolve(
        self,
        reference: ArtifactRef,
        expected_type: type[ResolvedType],
        *,
        label: str,
    ) -> ResolvedType:
        from .bundle_loader import InstrumentBundleConsistencyError

        member = self.index.get((reference.artifact_type, reference.artifact_id))
        if member is None:
            raise InstrumentBundleConsistencyError(
                "resolved_member_missing",
                f"{label} is absent after reference resolution",
            )
        self.require(
            member.reference == reference,
            "resolved_member_identity_mismatch",
            f"{label} differs from the indexed reference",
        )
        self.require(
            isinstance(member.value, expected_type),
            "resolved_member_type_mismatch",
            f"{label} resolves to the wrong runtime artifact type",
        )
        return member.value

    def ref_equal(
        self,
        actual: ArtifactRef,
        expected: ArtifactRef,
        *,
        code: str,
        label: str,
    ) -> None:
        self.require(actual == expected, code, f"{label} references differ")

    def claim_at_or_below(
        self,
        actual: ClaimLevel,
        ceiling: ClaimLevel,
        *,
        label: str,
    ) -> None:
        self.require(
            actual in _CLAIMS_AT_OR_BELOW[ceiling],
            "claim_ceiling_join_mismatch",
            f"{label} exceeds its resolved upstream claim ceiling",
        )

    def edge_claim_at_or_below_field(
        self,
        *,
        edge_claim: ClaimLevel,
        field_claim: ClaimLevel,
        branch: ScientificBranch,
        label: str,
    ) -> None:
        if branch is ScientificBranch.GEOMETRY:
            self.claim_at_or_below(
                edge_claim,
                field_claim,
                label=label,
            )
            return
        self.require(
            edge_claim in _DEFECT_FIELD_TO_EDGE_CLAIMS[field_claim],
            "edge_claim_ceiling_join_mismatch",
            f"{label} exceeds the defect-to-geometry prerequisite mapping",
        )

    def substrate(
        self,
        reference: ArtifactRef,
        *,
        label: str,
    ) -> SubstrateBinding:
        return self.resolve(reference, SubstrateBinding, label=label)

    def graph(
        self,
        reference: ArtifactRef,
        *,
        label: str,
        purpose: str | None = None,
    ) -> CandidateGraph:
        graph = self.resolve(reference, CandidateGraph, label=label)
        specification = self.resolve(
            graph.specification,
            GraphConstructionSpec,
            label=f"{label}.specification",
        )
        self.ref_equal(
            graph.substrate,
            specification.substrate,
            code="graph_spec_substrate_mismatch",
            label=label,
        )
        substrate = self.substrate(
            graph.substrate,
            label=f"{label}.substrate",
        )
        self.require(
            specification.allowed_role is substrate.role,
            "graph_role_mismatch",
            f"{label} allowed_role differs from its substrate role",
        )
        if purpose is not None:
            self.require(
                specification.purpose == purpose,
                "graph_purpose_mismatch",
                f"{label} must have purpose={purpose!r}",
            )
        return graph

    def registry(
        self,
        reference: ArtifactRef,
        *,
        label: str,
    ) -> HypothesisRegistry:
        return self.resolve(reference, HypothesisRegistry, label=label)

    def role_for_reference(
        self,
        reference: ArtifactRef,
        *,
        label: str,
    ) -> FitRole | None:
        member = self.index[(reference.artifact_type, reference.artifact_id)]
        value = member.value
        if isinstance(value, SubstrateBinding):
            return value.role
        if isinstance(value, GraphConstructionSpec):
            return value.allowed_role
        if isinstance(value, SupportDiagnostic):
            return value.fit_role
        if isinstance(value, CoreScore):
            return value.fit_role
        if isinstance(value, GroundTruthAnchor):
            return value.role
        if isinstance(value, CalibrationSelectionDecision):
            return FitRole.CALIBRATION_SELECTION
        if isinstance(value, CalibrationConfirmationResult):
            return FitRole.CALIBRATION_CONFIRMATION
        substrate_ref = getattr(value, "substrate", None)
        if isinstance(substrate_ref, ArtifactRef):
            return self.substrate(
                substrate_ref,
                label=f"{label}.substrate",
            ).role
        return None


def _choice_refines_registry(
    validator: _JoinValidator,
    *,
    actual: RuleChoice,
    registered: RuleChoice,
    label: str,
) -> None:
    validator.require(
        actual.family_id == registered.family_id,
        "registry_choice_family_mismatch",
        f"{label} family differs from the registry",
    )
    if registered.resolution is ResolutionState.CALIBRATION_SELECTION:
        if actual.resolution is ResolutionState.CALIBRATION_SELECTION:
            validator.require(
                actual.candidate_ids == registered.candidate_ids,
                "registry_choice_candidates_mismatch",
                f"{label} candidate set differs from the registry",
            )
            return
        validator.require(
            actual.resolution is ResolutionState.CALIBRATION_RESOLVED,
            "registry_choice_resolution_mismatch",
            f"{label} must remain selectable or become calibration_resolved",
        )
        validator.require(
            actual.selected_id in registered.candidate_ids,
            "registry_choice_selection_mismatch",
            f"{label} selected ID is outside the registry candidates",
        )
        return
    validator.require(
        actual == registered,
        "registry_fixed_choice_mismatch",
        f"{label} differs from the registry-fixed rule",
    )


def _validate_registry_hypothesis(
    validator: _JoinValidator,
    *,
    registry: HypothesisRegistry,
    hypothesis_id: HypothesisId,
    expected_branch: ScientificBranch,
    claim_ceiling: ClaimLevel,
    label: str,
) -> HypothesisSpec:
    try:
        hypothesis = registry.require(hypothesis_id)
    except KeyError as error:
        from .bundle_loader import InstrumentBundleConsistencyError

        raise InstrumentBundleConsistencyError(
            "registry_hypothesis_missing",
            f"{label} hypothesis is absent from the resolved registry",
        ) from error
    validator.require(
        hypothesis.branch is expected_branch,
        "registry_branch_mismatch",
        f"{label} branch differs from the resolved registry",
    )
    validator.claim_at_or_below(
        claim_ceiling,
        hypothesis.claim_ceiling,
        label=label,
    )
    return hypothesis


def _validate_order_parameter_spec(
    validator: _JoinValidator,
    spec: OrderParameterSpec,
    *,
    label: str,
) -> HypothesisSpec:
    registry = validator.registry(
        spec.hypothesis_registry,
        label=f"{label}.hypothesis_registry",
    )
    hypothesis = _validate_registry_hypothesis(
        validator,
        registry=registry,
        hypothesis_id=spec.hypothesis_id,
        expected_branch=ScientificBranch.DEFECT,
        claim_ceiling=spec.claim_ceiling,
        label=label,
    )
    validator.require(
        spec.target_manifold_id == hypothesis.target_manifold,
        "registry_target_manifold_mismatch",
        f"{label} target manifold differs from the registry",
    )
    validator.require(
        spec.gauge_law_id == hypothesis.gauge_law,
        "registry_gauge_law_mismatch",
        f"{label} gauge law differs from the registry",
    )
    validator.require(
        spec.charge_group.resolution is ResolutionState.FIXED_BY_HYPOTHESIS
        and spec.charge_group.selected_id == hypothesis.charge_group,
        "registry_charge_group_mismatch",
        f"{label} charge group does not preserve the registry value",
    )
    validator.require(
        set(hypothesis.forbidden_labels).issubset(spec.forbidden_labels),
        "registry_forbidden_labels_missing",
        f"{label} omits registry-forbidden labels",
    )
    for field_name in _SPEC_REGISTRY_CHOICE_FIELDS:
        _choice_refines_registry(
            validator,
            actual=getattr(spec, field_name),
            registered=getattr(hypothesis, field_name),
            label=f"{label}.{field_name}",
        )
    validator.graph(
        spec.estimation_graph,
        label=f"{label}.estimation_graph",
        purpose="field_estimation",
    )
    graph = validator.resolve(
        spec.estimation_graph,
        CandidateGraph,
        label=f"{label}.estimation_graph",
    )
    validator.ref_equal(
        spec.substrate,
        graph.substrate,
        code="spec_graph_substrate_mismatch",
        label=label,
    )
    return hypothesis


def _validate_core_graph_binding(
    validator: _JoinValidator,
    *,
    binding: object,
    field_graph: ArtifactRef,
    substrate: ArtifactRef,
    label: str,
) -> None:
    if isinstance(binding, GraphFreeBinding):
        validator.require(True, "graph_free_binding_valid", label)
        return
    if isinstance(binding, InheritedFieldGraphBinding):
        validator.ref_equal(
            binding.candidate_graph,
            field_graph,
            code="inherited_core_graph_mismatch",
            label=label,
        )
        validator.graph(
            binding.candidate_graph,
            label=f"{label}.candidate_graph",
            purpose="field_estimation",
        )
        return
    validator.require(
        isinstance(binding, ExplicitCoreGraphBinding),
        "core_graph_binding_type_mismatch",
        f"{label} has an unsupported graph binding",
    )
    assert isinstance(binding, ExplicitCoreGraphBinding)
    graph = validator.graph(
        binding.candidate_graph,
        label=f"{label}.candidate_graph",
        purpose="core_localization",
    )
    validator.ref_equal(
        graph.specification,
        binding.graph_specification,
        code="explicit_core_graph_spec_mismatch",
        label=label,
    )
    validator.ref_equal(
        graph.substrate,
        substrate,
        code="explicit_core_graph_substrate_mismatch",
        label=label,
    )
    validator.require(
        binding.candidate_graph != field_graph,
        "explicit_core_graph_axis_collapsed",
        f"{label} must remain distinct from the field-estimation graph",
    )


def _validate_decision_against_registry(
    validator: _JoinValidator,
    decision: CalibrationSelectionDecision,
    registry: HypothesisRegistry,
    *,
    label: str,
) -> None:
    fixed = {
        (value.hypothesis_id, value.choice.family_id): value.choice
        for value in decision.fixed_choices
    }
    resolved = {
        (value.hypothesis_id, value.choice.family_id): value.choice
        for value in decision.resolved_choices
    }
    unresolved = {
        (value.hypothesis_id, value.choice.family_id): value.choice
        for value in decision.unresolved_choices
    }
    for hypothesis in registry.hypotheses:
        for field_name in _REGISTRY_CHOICE_FIELDS:
            registered = getattr(hypothesis, field_name)
            key = (hypothesis.hypothesis_id, field_name)
            present = sum(key in values for values in (fixed, resolved, unresolved))
            if registered.resolution is ResolutionState.CALIBRATION_SELECTION:
                validator.require(
                    present == 1 and key not in fixed,
                    "selection_registry_partition_mismatch",
                    f"{label} does not close registry choice {key!r}",
                )
                if key in resolved:
                    validator.require(
                        resolved[key].selected_id in registered.candidate_ids,
                        "selection_registry_resolved_id_mismatch",
                        f"{label} resolves {key!r} outside registry candidates",
                    )
                else:
                    validator.require(
                        unresolved[key].candidate_ids == registered.candidate_ids,
                        "selection_registry_candidates_mismatch",
                        f"{label} changes registry candidates for {key!r}",
                    )
            elif registered.resolution is ResolutionState.FIXED_BY_HYPOTHESIS:
                validator.require(
                    present == 1 and key in fixed and fixed[key] == registered,
                    "selection_registry_fixed_mismatch",
                    f"{label} changes registry-fixed choice {key!r}",
                )
            else:
                validator.require(
                    present == 0,
                    "selection_registry_nonchoice_receipt",
                    f"{label} gives a receipt to non-selectable {key!r}",
                )


def _validate_spec_matches_decision(
    validator: _JoinValidator,
    *,
    spec: OrderParameterSpec,
    decision: CalibrationSelectionDecision,
    label: str,
) -> None:
    resolved = {
        (value.hypothesis_id, value.choice.family_id): value.choice
        for value in decision.resolved_choices
    }
    fixed = {
        (value.hypothesis_id, value.choice.family_id): value.choice
        for value in decision.fixed_choices
    }
    for field_name in _SPEC_REGISTRY_CHOICE_FIELDS:
        key = (spec.hypothesis_id, field_name)
        expected = resolved.get(key, fixed.get(key))
        validator.require(
            expected is not None,
            "selected_spec_choice_unresolved",
            f"{label}.{field_name} has no locked selection receipt",
        )
        assert expected is not None
        validator.require(
            getattr(spec, field_name) == expected,
            "selected_spec_choice_mismatch",
            f"{label}.{field_name} differs from the selection receipt",
        )


def _trace_hypothesis_artifact(
    validator: _JoinValidator,
    reference: ArtifactRef,
    *,
    label: str,
) -> _HypothesisArtifactTrace | None:
    artifact_type = reference.artifact_type
    if artifact_type is ArtifactType.GEOMETRIC_FIELD_ESTIMATE:
        field = validator.resolve(
            reference,
            GeometricFieldEstimate,
            label=label,
        )
        return _HypothesisArtifactTrace(
            hypothesis_id=field.hypothesis_id,
            hypothesis_registry=field.hypothesis_registry,
            substrate=field.substrate,
        )
    if artifact_type is ArtifactType.GEOMETRY_LOOP_ESTIMATE:
        loop = validator.resolve(
            reference,
            GeometryLoopEstimate,
            label=label,
        )
        trace = _trace_hypothesis_artifact(
            validator,
            loop.geometric_field,
            label=f"{label}.geometric_field",
        )
        assert trace is not None
        return _HypothesisArtifactTrace(
            hypothesis_id=trace.hypothesis_id,
            hypothesis_registry=trace.hypothesis_registry,
            substrate=loop.substrate,
        )
    if artifact_type is ArtifactType.ORDER_PARAMETER_SPEC:
        spec = validator.resolve(
            reference,
            OrderParameterSpec,
            label=label,
        )
        return _HypothesisArtifactTrace(
            hypothesis_id=spec.hypothesis_id,
            hypothesis_registry=spec.hypothesis_registry,
            substrate=spec.substrate,
            order_parameter_spec_reference=reference,
            order_parameter_spec=spec,
        )
    if artifact_type is ArtifactType.ORDER_PARAMETER_FIELD:
        field = validator.resolve(
            reference,
            OrderParameterField,
            label=label,
        )
        trace = _trace_hypothesis_artifact(
            validator,
            field.specification,
            label=f"{label}.specification",
        )
        assert trace is not None
        return _HypothesisArtifactTrace(
            hypothesis_id=trace.hypothesis_id,
            hypothesis_registry=trace.hypothesis_registry,
            substrate=field.substrate,
            order_parameter_spec_reference=field.specification,
            order_parameter_spec=trace.order_parameter_spec,
        )
    if artifact_type is ArtifactType.CORE_SCORE:
        score = validator.resolve(reference, CoreScore, label=label)
        trace = _trace_hypothesis_artifact(
            validator,
            score.order_parameter_spec,
            label=f"{label}.order_parameter_spec",
        )
        assert trace is not None
        return _HypothesisArtifactTrace(
            hypothesis_id=trace.hypothesis_id,
            hypothesis_registry=trace.hypothesis_registry,
            substrate=score.substrate,
            order_parameter_spec_reference=score.order_parameter_spec,
            order_parameter_spec=trace.order_parameter_spec,
        )
    if artifact_type is ArtifactType.CORE_CANDIDATE:
        candidate = validator.resolve(
            reference,
            CoreCandidate,
            label=label,
        )
        trace = _trace_hypothesis_artifact(
            validator,
            candidate.order_parameter_field,
            label=f"{label}.order_parameter_field",
        )
        assert trace is not None
        return _HypothesisArtifactTrace(
            hypothesis_id=trace.hypothesis_id,
            hypothesis_registry=trace.hypothesis_registry,
            substrate=candidate.substrate,
            order_parameter_spec_reference=(trace.order_parameter_spec_reference),
            order_parameter_spec=trace.order_parameter_spec,
        )
    if artifact_type is ArtifactType.DEFECT_LOOP_ESTIMATE:
        loop = validator.resolve(
            reference,
            DefectLoopEstimate,
            label=label,
        )
        trace = _trace_hypothesis_artifact(
            validator,
            loop.order_parameter_field,
            label=f"{label}.order_parameter_field",
        )
        assert trace is not None
        return _HypothesisArtifactTrace(
            hypothesis_id=trace.hypothesis_id,
            hypothesis_registry=trace.hypothesis_registry,
            substrate=loop.substrate,
            order_parameter_spec_reference=(trace.order_parameter_spec_reference),
            order_parameter_spec=trace.order_parameter_spec,
        )
    if artifact_type is ArtifactType.EDGE_CONNECTION:
        edge = validator.resolve(
            reference,
            EdgeConnection,
            label=label,
        )
        trace = _trace_hypothesis_artifact(
            validator,
            edge.field,
            label=f"{label}.field",
        )
        assert trace is not None
        return _HypothesisArtifactTrace(
            hypothesis_id=trace.hypothesis_id,
            hypothesis_registry=trace.hypothesis_registry,
            substrate=edge.substrate,
            order_parameter_spec_reference=(trace.order_parameter_spec_reference),
            order_parameter_spec=trace.order_parameter_spec,
        )
    return None


def _locked_decision_choice(
    validator: _JoinValidator,
    *,
    decision: CalibrationSelectionDecision,
    hypothesis_id: HypothesisId,
    family_id: str,
    label: str,
    code_prefix: str,
) -> RuleChoice:
    matches = [
        item.choice
        for item in (*decision.fixed_choices, *decision.resolved_choices)
        if item.hypothesis_id is hypothesis_id and item.choice.family_id == family_id
    ]
    validator.require(
        len(matches) == 1,
        f"{code_prefix}_choice_unresolved",
        f"{label} has no unique locked {family_id} receipt",
    )
    choice = matches[0]
    validator.require(
        choice.selected_id is not None,
        f"{code_prefix}_choice_unresolved",
        f"{label} has no selected {family_id} value",
    )
    return choice


def _validate_trace_against_decision(
    validator: _JoinValidator,
    *,
    trace: _HypothesisArtifactTrace,
    decision: CalibrationSelectionDecision,
    label: str,
    code_prefix: str,
) -> None:
    dispositions = {
        item.hypothesis_id: item.disposition for item in decision.hypothesis_decisions
    }
    validator.require(
        dispositions.get(trace.hypothesis_id) is HypothesisDisposition.ADVANCE,
        f"{code_prefix}_hypothesis_not_advanced",
        f"{label} is bound to a hypothesis that was not advanced",
    )
    validator.ref_equal(
        trace.hypothesis_registry,
        decision.hypothesis_registry,
        code=f"{code_prefix}_registry_mismatch",
        label=label,
    )
    substrate = validator.substrate(
        trace.substrate,
        label=f"{label}.substrate",
    )
    fit_role = _locked_decision_choice(
        validator,
        decision=decision,
        hypothesis_id=trace.hypothesis_id,
        family_id="fit_role",
        label=label,
        code_prefix=code_prefix,
    )
    observation_axis = _locked_decision_choice(
        validator,
        decision=decision,
        hypothesis_id=trace.hypothesis_id,
        family_id="observation_axis",
        label=label,
        code_prefix=code_prefix,
    )
    validator.require(
        fit_role.selected_id == substrate.role.value,
        f"{code_prefix}_fit_role_mismatch",
        f"{label} substrate role differs from the locked fit_role",
    )
    validator.require(
        observation_axis.selected_id == substrate.evolution_axis.value,
        f"{code_prefix}_observation_axis_mismatch",
        f"{label} substrate axis differs from the locked observation_axis",
    )
    if trace.order_parameter_spec is not None:
        _validate_spec_matches_decision(
            validator,
            spec=trace.order_parameter_spec,
            decision=decision,
            label=label,
        )


def _validate_one(
    validator: _JoinValidator,
    value: object,
) -> None:
    label = value.__class__.__name__

    if isinstance(value, SubstrateBinding):
        validator.require(
            value.role not in _SUBJECT_ROLES,
            "subject_role_bundle_forbidden",
            "v0.1 integrity bundles cannot read subject-role payloads",
        )
        validator.resolve(
            value.context_bank,
            ContextBank,
            label=f"{label}.context_bank",
        )
        return

    if isinstance(value, GraphConstructionSpec):
        substrate = validator.substrate(
            value.substrate,
            label=f"{label}.substrate",
        )
        validator.require(
            value.allowed_role is substrate.role,
            "graph_role_mismatch",
            f"{label} allowed_role differs from its substrate",
        )
        return

    if isinstance(value, CandidateGraph):
        validator.graph(
            ArtifactRef(
                artifact_type=value.artifact_type,
                schema_version=value.schema_version,
                artifact_id=value.artifact_id,
                canonical_sha256=value.canonical_sha256,
            ),
            label=label,
        )
        return

    if isinstance(value, SupportDiagnostic):
        substrate = validator.substrate(
            value.substrate,
            label=f"{label}.substrate",
        )
        validator.require(
            value.row_identity_sha256 == substrate.row_identity_sha256,
            "row_identity_join_mismatch",
            f"{label} row identity differs from its substrate",
        )
        validator.require(
            value.fit_role is substrate.role,
            "fit_role_join_mismatch",
            f"{label} fit_role differs from its substrate",
        )
        neighborhood = validator.resolve(
            value.neighborhood_specification,
            (
                GraphConstructionSpec,
                CandidateGraph,
            ),
            label=f"{label}.neighborhood_specification",
        )
        neighborhood_substrate = (
            neighborhood.substrate
            if isinstance(neighborhood, GraphConstructionSpec)
            else neighborhood.substrate
        )
        validator.ref_equal(
            value.substrate,
            neighborhood_substrate,
            code="support_neighborhood_substrate_mismatch",
            label=label,
        )
        if isinstance(neighborhood, CandidateGraph):
            validator.graph(
                value.neighborhood_specification,
                label=f"{label}.neighborhood_specification",
            )
        return

    if isinstance(value, GeometricFieldEstimate):
        substrate = validator.substrate(
            value.substrate,
            label=f"{label}.substrate",
        )
        graph = validator.graph(
            value.estimation_graph,
            label=f"{label}.estimation_graph",
            purpose="field_estimation",
        )
        validator.ref_equal(
            value.substrate,
            graph.substrate,
            code="field_graph_substrate_mismatch",
            label=label,
        )
        validator.require(
            value.row_identity_sha256 == substrate.row_identity_sha256,
            "row_identity_join_mismatch",
            f"{label} row identity differs from its substrate",
        )
        registry = validator.registry(
            value.hypothesis_registry,
            label=f"{label}.hypothesis_registry",
        )
        hypothesis = _validate_registry_hypothesis(
            validator,
            registry=registry,
            hypothesis_id=value.hypothesis_id,
            expected_branch=ScientificBranch.GEOMETRY,
            claim_ceiling=value.claim_ceiling,
            label=label,
        )
        validator.require(
            value.gauge_law_id == hypothesis.gauge_law,
            "registry_gauge_law_mismatch",
            f"{label} gauge law differs from the registry",
        )
        return

    if isinstance(value, OrderParameterSpec):
        _validate_order_parameter_spec(validator, value, label=label)
        return

    if isinstance(value, OrderParameterField):
        spec = validator.resolve(
            value.specification,
            OrderParameterSpec,
            label=f"{label}.specification",
        )
        _validate_order_parameter_spec(
            validator,
            spec,
            label=f"{label}.specification",
        )
        substrate = validator.substrate(
            value.substrate,
            label=f"{label}.substrate",
        )
        validator.ref_equal(
            value.substrate,
            spec.substrate,
            code="field_spec_substrate_mismatch",
            label=label,
        )
        validator.ref_equal(
            value.estimation_graph,
            spec.estimation_graph,
            code="field_spec_graph_mismatch",
            label=label,
        )
        validator.require(
            value.hypothesis_id is spec.hypothesis_id,
            "field_spec_hypothesis_mismatch",
            f"{label} hypothesis differs from its specification",
        )
        validator.require(
            value.row_identity_sha256 == substrate.row_identity_sha256,
            "row_identity_join_mismatch",
            f"{label} row identity differs from its substrate",
        )
        validator.claim_at_or_below(
            value.claim_ceiling,
            spec.claim_ceiling,
            label=label,
        )
        return

    if isinstance(value, CoreScore):
        spec = validator.resolve(
            value.order_parameter_spec,
            OrderParameterSpec,
            label=f"{label}.order_parameter_spec",
        )
        field = validator.resolve(
            value.order_parameter_field,
            OrderParameterField,
            label=f"{label}.order_parameter_field",
        )
        substrate = validator.substrate(
            value.substrate,
            label=f"{label}.substrate",
        )
        validator.ref_equal(
            field.specification,
            value.order_parameter_spec,
            code="core_score_spec_field_mismatch",
            label=label,
        )
        for actual, expected, code in (
            (
                value.substrate,
                spec.substrate,
                "core_score_spec_substrate_mismatch",
            ),
            (
                value.substrate,
                field.substrate,
                "core_score_field_substrate_mismatch",
            ),
            (
                value.field_estimation_graph,
                spec.estimation_graph,
                "core_score_spec_graph_mismatch",
            ),
            (
                value.field_estimation_graph,
                field.estimation_graph,
                "core_score_field_graph_mismatch",
            ),
        ):
            validator.ref_equal(
                actual,
                expected,
                code=code,
                label=label,
            )
        validator.require(
            value.row_identity_sha256
            == field.row_identity_sha256
            == substrate.row_identity_sha256,
            "row_identity_join_mismatch",
            f"{label} row identities differ",
        )
        validator.require(
            value.fit_role is substrate.role,
            "fit_role_join_mismatch",
            f"{label} fit_role differs from its substrate",
        )
        _validate_core_graph_binding(
            validator,
            binding=value.graph_binding,
            field_graph=value.field_estimation_graph,
            substrate=value.substrate,
            label=f"{label}.graph_binding",
        )
        validator.claim_at_or_below(
            value.claim_ceiling,
            field.claim_ceiling,
            label=label,
        )
        return

    if isinstance(value, CoreCandidate):
        core_score = validator.resolve(
            value.core_score,
            CoreScore,
            label=f"{label}.core_score",
        )
        field = validator.resolve(
            value.order_parameter_field,
            OrderParameterField,
            label=f"{label}.order_parameter_field",
        )
        substrate = validator.substrate(
            value.substrate,
            label=f"{label}.substrate",
        )
        for actual, expected, code in (
            (
                value.substrate,
                core_score.substrate,
                "core_candidate_substrate_mismatch",
            ),
            (
                value.order_parameter_field,
                core_score.order_parameter_field,
                "core_candidate_field_mismatch",
            ),
            (
                value.field_estimation_graph,
                core_score.field_estimation_graph,
                "core_candidate_graph_mismatch",
            ),
        ):
            validator.ref_equal(
                actual,
                expected,
                code=code,
                label=label,
            )
        validator.require(
            value.row_identity_sha256
            == core_score.row_identity_sha256
            == field.row_identity_sha256
            == substrate.row_identity_sha256,
            "row_identity_join_mismatch",
            f"{label} row identities differ",
        )
        validator.require(
            value.singularity_rule_id == core_score.singularity_rule_id,
            "core_candidate_singularity_rule_mismatch",
            f"{label} singularity rule differs from CoreScore",
        )
        validator.require(
            value.graph_binding == core_score.graph_binding,
            "core_candidate_graph_binding_mismatch",
            f"{label} graph binding differs from CoreScore",
        )
        validator.require(
            value.charge_blind is core_score.charge_blind,
            "core_candidate_charge_boundary_mismatch",
            f"{label} charge-blind boundary differs from CoreScore",
        )
        validator.claim_at_or_below(
            value.claim_ceiling,
            core_score.claim_ceiling,
            label=label,
        )
        return

    if isinstance(value, GroundTruthAnchor):
        substrate = validator.substrate(
            value.substrate,
            label=f"{label}.substrate",
        )
        validator.require(
            value.role is substrate.role,
            "fit_role_join_mismatch",
            f"{label} role differs from its substrate",
        )
        validator.require(
            value.row_identity_sha256 == substrate.row_identity_sha256,
            "row_identity_join_mismatch",
            f"{label} row identity differs from its substrate",
        )
        return

    if isinstance(value, EdgeConnection):
        field_type = (
            GeometricFieldEstimate
            if value.field_branch is ScientificBranch.GEOMETRY
            else OrderParameterField
        )
        field = validator.resolve(
            value.field,
            field_type,
            label=f"{label}.field",
        )
        graph = validator.graph(
            value.graph,
            label=f"{label}.graph",
        )
        validator.ref_equal(
            value.substrate,
            field.substrate,
            code="edge_field_substrate_mismatch",
            label=label,
        )
        validator.ref_equal(
            value.substrate,
            graph.substrate,
            code="edge_graph_substrate_mismatch",
            label=label,
        )
        validator.require(
            value.edge_order_sha256 == graph.edge_order_sha256,
            "edge_order_join_mismatch",
            f"{label} edge order differs from its graph",
        )
        validator.edge_claim_at_or_below_field(
            edge_claim=value.claim_ceiling,
            field_claim=field.claim_ceiling,
            branch=value.field_branch,
            label=label,
        )
        return

    if isinstance(value, GeometryLoopEstimate):
        field = validator.resolve(
            value.geometric_field,
            GeometricFieldEstimate,
            label=f"{label}.geometric_field",
        )
        edge = validator.resolve(
            value.edge_connection,
            EdgeConnection,
            label=f"{label}.edge_connection",
        )
        graph = validator.graph(
            value.cycle_graph,
            label=f"{label}.cycle_graph",
            purpose="cycle_construction",
        )
        for actual, expected, code in (
            (
                value.substrate,
                field.substrate,
                "geometry_loop_field_substrate_mismatch",
            ),
            (
                value.substrate,
                edge.substrate,
                "geometry_loop_edge_substrate_mismatch",
            ),
            (
                value.substrate,
                graph.substrate,
                "geometry_loop_graph_substrate_mismatch",
            ),
            (
                edge.field,
                value.geometric_field,
                "geometry_loop_edge_field_mismatch",
            ),
            (
                edge.graph,
                value.cycle_graph,
                "geometry_loop_edge_graph_mismatch",
            ),
        ):
            validator.ref_equal(
                actual,
                expected,
                code=code,
                label=label,
            )
        validator.claim_at_or_below(
            value.claim_ceiling,
            field.claim_ceiling,
            label=label,
        )
        validator.claim_at_or_below(
            value.claim_ceiling,
            edge.claim_ceiling,
            label=label,
        )
        return

    if isinstance(value, DefectLoopEstimate):
        field = validator.resolve(
            value.order_parameter_field,
            OrderParameterField,
            label=f"{label}.order_parameter_field",
        )
        spec = validator.resolve(
            field.specification,
            OrderParameterSpec,
            label=f"{label}.order_parameter_spec",
        )
        graph = validator.graph(
            value.cycle_graph,
            label=f"{label}.cycle_graph",
            purpose="cycle_construction",
        )
        for actual, expected, code in (
            (
                value.substrate,
                field.substrate,
                "defect_loop_field_substrate_mismatch",
            ),
            (
                value.substrate,
                graph.substrate,
                "defect_loop_graph_substrate_mismatch",
            ),
        ):
            validator.ref_equal(
                actual,
                expected,
                code=code,
                label=label,
            )
        validator.require(
            value.hypothesis_id is field.hypothesis_id is spec.hypothesis_id,
            "defect_loop_hypothesis_mismatch",
            f"{label} hypothesis IDs differ",
        )
        if value.coordinate_binding.edge_connection is not None:
            edge = validator.resolve(
                value.coordinate_binding.edge_connection,
                EdgeConnection,
                label=f"{label}.coordinate_binding.edge_connection",
            )
            validator.require(
                edge.field_branch is ScientificBranch.DEFECT,
                "defect_loop_edge_branch_mismatch",
                f"{label} local-frame edge is not a defect edge",
            )
            for actual, expected, code in (
                (
                    edge.field,
                    value.order_parameter_field,
                    "defect_loop_edge_field_mismatch",
                ),
                (
                    edge.graph,
                    value.cycle_graph,
                    "defect_loop_edge_graph_mismatch",
                ),
                (
                    edge.substrate,
                    value.substrate,
                    "defect_loop_edge_substrate_mismatch",
                ),
            ):
                validator.ref_equal(
                    actual,
                    expected,
                    code=code,
                    label=label,
                )
        if value.localization_binding.core_candidate is not None:
            candidate = validator.resolve(
                value.localization_binding.core_candidate,
                CoreCandidate,
                label=f"{label}.localization_binding.core_candidate",
            )
            validator.ref_equal(
                candidate.order_parameter_field,
                value.order_parameter_field,
                code="defect_loop_core_field_mismatch",
                label=label,
            )
            validator.ref_equal(
                candidate.substrate,
                value.substrate,
                code="defect_loop_core_substrate_mismatch",
                label=label,
            )
        if value.localization_binding.ground_truth_anchor is not None:
            anchor = validator.resolve(
                value.localization_binding.ground_truth_anchor,
                GroundTruthAnchor,
                label=f"{label}.localization_binding.ground_truth_anchor",
            )
            validator.ref_equal(
                anchor.substrate,
                value.substrate,
                code="defect_loop_anchor_substrate_mismatch",
                label=label,
            )
        validator.claim_at_or_below(
            value.claim_ceiling,
            field.claim_ceiling,
            label=label,
        )
        if value.claim_ceiling is ClaimLevel.LEVEL_2T:
            assert value.integer_output_authorization is not None
            decision = validator.resolve(
                value.integer_output_authorization,
                CalibrationSelectionDecision,
                label=f"{label}.integer_output_authorization",
            )
            validator.ref_equal(
                decision.hypothesis_registry,
                spec.hypothesis_registry,
                code="integer_authorization_registry_mismatch",
                label=label,
            )
            validator.require(
                value.hypothesis_id in decision.integer_output_authorizations,
                "integer_authorization_hypothesis_mismatch",
                f"{label} hypothesis is not integer-authorized",
            )
            disposition = {
                item.hypothesis_id: item.disposition
                for item in decision.hypothesis_decisions
            }
            validator.require(
                disposition[value.hypothesis_id] is HypothesisDisposition.ADVANCE,
                "integer_authorization_not_advanced",
                f"{label} hypothesis was not advanced",
            )
            selected_traces = tuple(
                trace
                for reference in decision.selected_artifacts
                if (
                    trace := _trace_hypothesis_artifact(
                        validator,
                        reference,
                        label=(
                            f"{label}.integer_output_authorization."
                            f"selected_artifacts.{reference.artifact_id}"
                        ),
                    )
                )
                is not None
            )
            matching_selected_traces = tuple(
                trace
                for trace in selected_traces
                if trace.hypothesis_id is value.hypothesis_id
                and trace.hypothesis_registry == spec.hypothesis_registry
                and trace.order_parameter_spec_reference == field.specification
            )
            validator.require(
                bool(matching_selected_traces),
                "integer_authorization_selected_path_missing",
                f"{label} has no selected precursor bound to its exact "
                "order-parameter specification",
            )
            _validate_trace_against_decision(
                validator,
                trace=_HypothesisArtifactTrace(
                    hypothesis_id=spec.hypothesis_id,
                    hypothesis_registry=spec.hypothesis_registry,
                    substrate=value.substrate,
                    order_parameter_spec_reference=field.specification,
                    order_parameter_spec=spec,
                ),
                decision=decision,
                label=label,
                code_prefix="integer_authorization",
            )
        return

    if isinstance(value, CalibrationSelectionDecision):
        registry = validator.registry(
            value.hypothesis_registry,
            label=f"{label}.hypothesis_registry",
        )
        _validate_decision_against_registry(
            validator,
            value,
            registry,
            label=label,
        )
        validator.require(
            value.hypothesis_registry in value.selection_inputs,
            "selection_registry_input_missing",
            f"{label} registry must be an exact selection input",
        )
        validator.require(
            set(value.selected_artifacts).issubset(value.selection_outputs),
            "selected_artifacts_not_outputs",
            f"{label} selected artifacts must be selection outputs",
        )
        validator.require(
            set(value.selection_inputs).isdisjoint(value.selection_outputs),
            "selection_input_output_overlap",
            f"{label} inputs and outputs must be content-distinct",
        )
        for collection_name, references in (
            ("selection_inputs", value.selection_inputs),
            ("selection_outputs", value.selection_outputs),
            ("selected_artifacts", value.selected_artifacts),
        ):
            for reference in references:
                role = validator.role_for_reference(
                    reference,
                    label=f"{label}.{collection_name}",
                )
                if role is not None:
                    validator.require(
                        role in _STAGE_SAFE_SELECTION_ROLES,
                        "selection_evidence_role_mismatch",
                        f"{label}.{collection_name} contains evidence outside "
                        "the calibration-safe stages",
                    )
        for reference in value.selected_artifacts:
            trace = _trace_hypothesis_artifact(
                validator,
                reference,
                label=(f"{label}.selected_artifacts.{reference.artifact_id}"),
            )
            if trace is not None:
                _validate_trace_against_decision(
                    validator,
                    trace=trace,
                    decision=value,
                    label=(f"{label}.selected_artifacts.{reference.artifact_id}"),
                    code_prefix="selected_artifact",
                )
        return

    if isinstance(value, CalibrationConfirmationResult):
        decision = validator.resolve(
            value.selection_decision,
            CalibrationSelectionDecision,
            label=f"{label}.selection_decision",
        )
        selection_refs = {
            *decision.selection_inputs,
            *decision.selection_outputs,
            *decision.selected_artifacts,
        }
        validator.require(
            set(value.evidence_artifacts).isdisjoint(selection_refs),
            "confirmation_reuses_selection_evidence",
            f"{label} reuses selection artifacts",
        )
        for reference in value.evidence_artifacts:
            role = validator.role_for_reference(
                reference,
                label=f"{label}.evidence_artifacts",
            )
            validator.require(
                role is FitRole.CALIBRATION_CONFIRMATION,
                "confirmation_evidence_role_mismatch",
                f"{label} evidence is not calibration_confirmation",
            )
        validator.claim_at_or_below(
            value.claim_ceiling,
            decision.claim_ceiling,
            label=label,
        )


def validate_bundle_cross_manifest(
    *,
    members: tuple[object, ...],
    index: Mapping[tuple[ArtifactType, str], object],
) -> int:
    """Validate only explicit, metadata-level joins and return check count."""

    validator = _JoinValidator(index=index)
    for member in members:
        if isinstance(member.value, (HypothesisRegistry, ContextBank)):
            continue
        _validate_one(validator, member.value)
    return validator.checks
