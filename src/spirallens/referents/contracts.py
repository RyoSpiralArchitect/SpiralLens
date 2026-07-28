"""Canonical F0--F4 pointwise-referent contracts.

These records say what object an estimator would have to observe.  They do
not establish that such an object exists in a model, qualify an estimator, or
authorize subject access.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar

from spirallens.core.canonical import (
    canonical_json_bytes,
    canonical_json_sha256,
)
from spirallens.instrument_contracts.common import ClaimLevel, HypothesisId

from .common import (
    ChargeConvention,
    DirectionRule,
    FitEvaluationRule,
    GaugeGroup,
    ReferentContractError,
    ReferentKind,
    TransformationLaw,
    parse_enum,
    parse_slug_list,
    require_bool,
    require_exact_keys,
    require_false,
    require_mapping,
    require_sha256,
    require_slug,
    validate_slug_tuple,
)

REFERENT_CONTRACT_SET_SCHEMA_VERSION = "spirallens.referent-contract-set.v0.1"
CANONICAL_REFERENT_CONTRACT_SET_ID = "f0-f4-operational-referents-v0.1"
SYNTHETIC_CONSTRUCT_VALIDITY_SCOPE = (
    "injected-referent-estimator-and-transformation-behavior-only"
)


@dataclass(frozen=True, slots=True)
class ReferentDefinition:
    """One exact operational meaning for an F0--F4 hypothesis."""

    hypothesis_id: HypothesisId
    referent_kind: ReferentKind
    source_object_formula_id: str
    pointwise_formula_id: str
    amplitude_formula_id: str
    direction_rule: DirectionRule
    fit_evaluation_rule: FitEvaluationRule
    gauge_group: GaugeGroup
    transformation_law: TransformationLaw
    ambient_transformation_formula_id: str
    gauge_transformation_formula_id: str
    reflection_law_id: str
    charge_convention: ChargeConvention
    pointwise_formula_defined: bool
    substrate_field_bound: bool
    interpolation_bound: bool
    order_parameter_defined: bool
    same_object_amplitude_direction_required: bool
    claim_ceiling: ClaimLevel
    required_claim_qualifiers: tuple[str, ...]
    forbidden_labels: tuple[str, ...]
    construct_validity_nonclaims: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.hypothesis_id, HypothesisId):
            raise TypeError("hypothesis_id must be a HypothesisId")
        for name, enum_type in (
            ("referent_kind", ReferentKind),
            ("direction_rule", DirectionRule),
            ("fit_evaluation_rule", FitEvaluationRule),
            ("gauge_group", GaugeGroup),
            ("transformation_law", TransformationLaw),
            ("charge_convention", ChargeConvention),
        ):
            if not isinstance(getattr(self, name), enum_type):
                raise TypeError(f"{name} must be a {enum_type.__name__}")
        if not isinstance(self.claim_ceiling, ClaimLevel):
            raise TypeError("claim_ceiling must be a ClaimLevel")
        for name in (
            "source_object_formula_id",
            "pointwise_formula_id",
            "amplitude_formula_id",
            "ambient_transformation_formula_id",
            "gauge_transformation_formula_id",
            "reflection_law_id",
        ):
            require_slug(getattr(self, name), label=name)
        for name in (
            "pointwise_formula_defined",
            "substrate_field_bound",
            "interpolation_bound",
            "order_parameter_defined",
            "same_object_amplitude_direction_required",
        ):
            require_bool(getattr(self, name), label=name)
        for name in (
            "required_claim_qualifiers",
            "forbidden_labels",
            "construct_validity_nonclaims",
        ):
            validate_slug_tuple(getattr(self, name), label=name)

        for name in (
            "substrate_field_bound",
            "interpolation_bound",
            "order_parameter_defined",
        ):
            require_false(
                getattr(self, name),
                label=name,
            )
        if not self.pointwise_formula_defined:
            if (
                self.pointwise_formula_id != "not-applicable"
                or self.amplitude_formula_id != "not-applicable"
                or self.direction_rule is not DirectionRule.NOT_DEFINED
                or self.same_object_amplitude_direction_required
                or self.charge_convention is not ChargeConvention.NONE
            ):
                raise ReferentContractError(
                    "referents without a pointwise formula cannot define "
                    "amplitude, direction, or charge"
                )
        elif (
            self.direction_rule is DirectionRule.NOT_DEFINED
            or not self.same_object_amplitude_direction_required
        ):
            raise ReferentContractError(
                "pointwise section formulas require same-object direction"
            )
        if self.interpolation_bound and not self.substrate_field_bound:
            raise ReferentContractError(
                "interpolation cannot be bound without a substrate field"
            )
        if self.order_parameter_defined and not (
            self.pointwise_formula_defined
            and self.substrate_field_bound
            and self.interpolation_bound
        ):
            raise ReferentContractError(
                "an order parameter requires pointwise, substrate-field, "
                "and interpolation bindings"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "hypothesis_id": self.hypothesis_id.value,
            "referent_kind": self.referent_kind.value,
            "source_object_formula_id": self.source_object_formula_id,
            "pointwise_formula_id": self.pointwise_formula_id,
            "amplitude_formula_id": self.amplitude_formula_id,
            "direction_rule": self.direction_rule.value,
            "fit_evaluation_rule": self.fit_evaluation_rule.value,
            "gauge_group": self.gauge_group.value,
            "transformation_law": self.transformation_law.value,
            "ambient_transformation_formula_id": (
                self.ambient_transformation_formula_id
            ),
            "gauge_transformation_formula_id": (self.gauge_transformation_formula_id),
            "reflection_law_id": self.reflection_law_id,
            "charge_convention": self.charge_convention.value,
            "pointwise_formula_defined": self.pointwise_formula_defined,
            "substrate_field_bound": self.substrate_field_bound,
            "interpolation_bound": self.interpolation_bound,
            "order_parameter_defined": self.order_parameter_defined,
            "same_object_amplitude_direction_required": (
                self.same_object_amplitude_direction_required
            ),
            "claim_ceiling": self.claim_ceiling.value,
            "required_claim_qualifiers": list(self.required_claim_qualifiers),
            "forbidden_labels": list(self.forbidden_labels),
            "construct_validity_nonclaims": list(self.construct_validity_nonclaims),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> ReferentDefinition:
        document = require_mapping(value, label="referent definition")
        require_exact_keys(
            document,
            expected=frozenset(
                {
                    "hypothesis_id",
                    "referent_kind",
                    "source_object_formula_id",
                    "pointwise_formula_id",
                    "amplitude_formula_id",
                    "direction_rule",
                    "fit_evaluation_rule",
                    "gauge_group",
                    "transformation_law",
                    "ambient_transformation_formula_id",
                    "gauge_transformation_formula_id",
                    "reflection_law_id",
                    "charge_convention",
                    "pointwise_formula_defined",
                    "substrate_field_bound",
                    "interpolation_bound",
                    "order_parameter_defined",
                    "same_object_amplitude_direction_required",
                    "claim_ceiling",
                    "required_claim_qualifiers",
                    "forbidden_labels",
                    "construct_validity_nonclaims",
                }
            ),
            label="referent definition",
        )
        return cls(
            hypothesis_id=parse_enum(
                HypothesisId,
                document["hypothesis_id"],
                label="hypothesis_id",
            ),
            referent_kind=parse_enum(
                ReferentKind,
                document["referent_kind"],
                label="referent_kind",
            ),
            source_object_formula_id=require_slug(
                document["source_object_formula_id"],
                label="source_object_formula_id",
            ),
            pointwise_formula_id=require_slug(
                document["pointwise_formula_id"],
                label="pointwise_formula_id",
            ),
            amplitude_formula_id=require_slug(
                document["amplitude_formula_id"],
                label="amplitude_formula_id",
            ),
            direction_rule=parse_enum(
                DirectionRule,
                document["direction_rule"],
                label="direction_rule",
            ),
            fit_evaluation_rule=parse_enum(
                FitEvaluationRule,
                document["fit_evaluation_rule"],
                label="fit_evaluation_rule",
            ),
            gauge_group=parse_enum(
                GaugeGroup,
                document["gauge_group"],
                label="gauge_group",
            ),
            transformation_law=parse_enum(
                TransformationLaw,
                document["transformation_law"],
                label="transformation_law",
            ),
            ambient_transformation_formula_id=require_slug(
                document["ambient_transformation_formula_id"],
                label="ambient_transformation_formula_id",
            ),
            gauge_transformation_formula_id=require_slug(
                document["gauge_transformation_formula_id"],
                label="gauge_transformation_formula_id",
            ),
            reflection_law_id=require_slug(
                document["reflection_law_id"],
                label="reflection_law_id",
            ),
            charge_convention=parse_enum(
                ChargeConvention,
                document["charge_convention"],
                label="charge_convention",
            ),
            pointwise_formula_defined=require_bool(
                document["pointwise_formula_defined"],
                label="pointwise_formula_defined",
            ),
            substrate_field_bound=require_false(
                document["substrate_field_bound"],
                label="substrate_field_bound",
            ),
            interpolation_bound=require_false(
                document["interpolation_bound"],
                label="interpolation_bound",
            ),
            order_parameter_defined=require_false(
                document["order_parameter_defined"],
                label="order_parameter_defined",
            ),
            same_object_amplitude_direction_required=require_bool(
                document["same_object_amplitude_direction_required"],
                label="same_object_amplitude_direction_required",
            ),
            claim_ceiling=parse_enum(
                ClaimLevel,
                document["claim_ceiling"],
                label="claim_ceiling",
            ),
            required_claim_qualifiers=parse_slug_list(
                document["required_claim_qualifiers"],
                label="required_claim_qualifiers",
            ),
            forbidden_labels=parse_slug_list(
                document["forbidden_labels"],
                label="forbidden_labels",
            ),
            construct_validity_nonclaims=parse_slug_list(
                document["construct_validity_nonclaims"],
                label="construct_validity_nonclaims",
            ),
        )


_COMMON_NONCLAIMS = tuple(
    sorted(
        {
            "does-not-authorize-promotion",
            "does-not-establish-model-side-existence",
            "does-not-establish-physical-phase",
            "does-not-establish-semantic-meaning",
            "does-not-establish-uniqueness-or-naturalness",
        }
    )
)


def _canonical_definitions() -> tuple[ReferentDefinition, ...]:
    return (
        ReferentDefinition(
            hypothesis_id=HypothesisId.F0_SUPPORT,
            referent_kind=ReferentKind.SUPPORT_DIAGNOSTIC,
            source_object_formula_id="declared-local-covariance-spectrum",
            pointwise_formula_id="not-applicable",
            amplitude_formula_id="not-applicable",
            direction_rule=DirectionRule.NOT_DEFINED,
            fit_evaluation_rule=FitEvaluationRule.FIT_ONLY_GEOMETRY,
            gauge_group=GaugeGroup.NONE,
            transformation_law=TransformationLaw.SCALAR_INVARIANT,
            ambient_transformation_formula_id=("ambient-basis-invariant-scalar"),
            gauge_transformation_formula_id="not-applicable",
            reflection_law_id="scalar-invariant",
            charge_convention=ChargeConvention.NONE,
            pointwise_formula_defined=False,
            substrate_field_bound=False,
            interpolation_bound=False,
            order_parameter_defined=False,
            same_object_amplitude_direction_required=False,
            claim_ceiling=ClaimLevel.LEVEL_1G,
            required_claim_qualifiers=(
                "field-unbound",
                "support-diagnostic",
            ),
            forbidden_labels=("defect", "phase", "winding"),
            construct_validity_nonclaims=_COMMON_NONCLAIMS,
        ),
        ReferentDefinition(
            hypothesis_id=HypothesisId.F1_PROJECTOR_CONNECTION,
            referent_kind=ReferentKind.RANK_TWO_PROJECTOR,
            source_object_formula_id="fitted-rank-two-frame",
            pointwise_formula_id="not-applicable",
            amplitude_formula_id="not-applicable",
            direction_rule=DirectionRule.NOT_DEFINED,
            fit_evaluation_rule=FitEvaluationRule.FIT_ONLY_GEOMETRY,
            gauge_group=GaugeGroup.LOCAL_O2,
            transformation_law=TransformationLaw.PROJECTOR_CONJUGATION,
            ambient_transformation_formula_id=("p-prime-equals-q-p-q-transpose"),
            gauge_transformation_formula_id=(
                "projector-invariant-under-u-prime-equals-u-g"
            ),
            reflection_law_id="projector-frame-gauge-invariant",
            charge_convention=ChargeConvention.NONE,
            pointwise_formula_defined=False,
            substrate_field_bound=False,
            interpolation_bound=False,
            order_parameter_defined=False,
            same_object_amplitude_direction_required=False,
            claim_ceiling=ClaimLevel.LEVEL_2G,
            required_claim_qualifiers=(
                "continuous-geometry",
                "rank-two-projector",
                "spec-relative",
            ),
            forbidden_labels=(
                "defect",
                "integer-charge-from-matrix-holonomy",
                "phase",
            ),
            construct_validity_nonclaims=_COMMON_NONCLAIMS,
        ),
        ReferentDefinition(
            hypothesis_id=HypothesisId.F2_LOCAL_COVARIANT_SECTION,
            referent_kind=ReferentKind.LOCAL_VECTOR_SECTION,
            source_object_formula_id=("cross-fitted-frame-and-evaluation-response"),
            pointwise_formula_id="z-equals-u-transpose-s",
            amplitude_formula_id="l2-norm-of-z",
            direction_rule=DirectionRule.NORMALIZE_SAME_VECTOR,
            fit_evaluation_rule=FitEvaluationRule.CROSS_FIT_REQUIRED,
            gauge_group=GaugeGroup.LOCAL_O2,
            transformation_law=TransformationLaw.O2_COVARIANT_VECTOR,
            ambient_transformation_formula_id=(
                "joint-ambient-action-leaves-z-invariant"
            ),
            gauge_transformation_formula_id=("z-prime-equals-g-transpose-z"),
            reflection_law_id="full-o2-vector-covariance",
            charge_convention=ChargeConvention.CONDITIONAL_VECTOR_INTEGER,
            pointwise_formula_defined=True,
            substrate_field_bound=False,
            interpolation_bound=False,
            order_parameter_defined=False,
            same_object_amplitude_direction_required=True,
            claim_ceiling=ClaimLevel.LEVEL_2T,
            required_claim_qualifiers=(
                "amplitude-nonzero-on-loop",
                "branch-gate-passed",
                "connection-or-trivialization-bound",
                "declared-domain",
                "local-covariant-section",
                "matched-cycle-contract",
                "orientability-resolved",
                "reference-resolved",
                "reflection-behavior-validated",
                "sampling-and-refinement-gates-passed",
                "spec-relative",
            ),
            forbidden_labels=(
                "intrinsic-representation-vortex",
                "model-phase",
                "topological-charge-without-domain-certificate",
            ),
            construct_validity_nonclaims=_COMMON_NONCLAIMS,
        ),
        ReferentDefinition(
            hypothesis_id=HypothesisId.F3_GLOBAL_PLANE_SECTION,
            referent_kind=ReferentKind.GLOBAL_VECTOR_SECTION,
            source_object_formula_id=("global-plane-and-evaluation-response"),
            pointwise_formula_id="z-equals-b-transpose-s",
            amplitude_formula_id="l2-norm-of-z",
            direction_rule=DirectionRule.NORMALIZE_SAME_VECTOR,
            fit_evaluation_rule=FitEvaluationRule.CROSS_FIT_IF_LEARNED,
            gauge_group=GaugeGroup.GLOBAL_O2,
            transformation_law=TransformationLaw.O2_COVARIANT_VECTOR,
            ambient_transformation_formula_id=(
                "joint-ambient-action-leaves-z-invariant"
            ),
            gauge_transformation_formula_id=("z-prime-equals-g-transpose-z"),
            reflection_law_id="global-plane-o2-covariance",
            charge_convention=(ChargeConvention.PROJECTION_DEPENDENT_CANDIDATE),
            pointwise_formula_defined=True,
            substrate_field_bound=False,
            interpolation_bound=False,
            order_parameter_defined=False,
            same_object_amplitude_direction_required=True,
            claim_ceiling=ClaimLevel.LEVEL_1D,
            required_claim_qualifiers=(
                "global-plane-baseline",
                "projection-dependent",
                "spec-relative",
            ),
            forbidden_labels=(
                "basis-invariant-charge",
                "intrinsic-representation-vortex",
                "level-2t",
            ),
            construct_validity_nonclaims=_COMMON_NONCLAIMS,
        ),
        ReferentDefinition(
            hypothesis_id=HypothesisId.F4_SPIN_TWO_ANISOTROPY,
            referent_kind=ReferentKind.SPIN_TWO_TRACELESS_TENSOR,
            source_object_formula_id=(
                "cross-fitted-plane-and-evaluation-symmetric-tensor"
            ),
            pointwise_formula_id=("w-equals-half-diagonal-difference-and-offdiagonal"),
            amplitude_formula_id="l2-norm-of-w-equals-frobenius-over-root-two",
            direction_rule=DirectionRule.NORMALIZE_SPIN_TWO_VECTOR,
            fit_evaluation_rule=FitEvaluationRule.CROSS_FIT_REQUIRED,
            gauge_group=GaugeGroup.LOCAL_O2,
            transformation_law=(TransformationLaw.SPIN_TWO_TRACELESS_SYMMETRIC),
            ambient_transformation_formula_id=(
                "joint-ambient-action-leaves-in-plane-tensor-invariant"
            ),
            gauge_transformation_formula_id=("t-prime-equals-g-transpose-t-g"),
            reflection_law_id="full-o2-spin-two-representation",
            charge_convention=ChargeConvention.DOUBLED_ANGLE_INTEGER,
            pointwise_formula_defined=True,
            substrate_field_bound=False,
            interpolation_bound=False,
            order_parameter_defined=False,
            same_object_amplitude_direction_required=True,
            claim_ceiling=ClaimLevel.LEVEL_2T,
            required_claim_qualifiers=(
                "amplitude-nonzero-on-loop",
                "declared-domain",
                "director-reference-resolved",
                "doubled-angle-convention",
                "matched-cycle-contract",
                "orientability-resolved",
                "reflection-behavior-validated",
                "sampling-and-refinement-gates-passed",
                "spec-relative",
                "spin-two-connection-or-trivialization-bound",
                "spin-two-director",
            ),
            forbidden_labels=(
                "intrinsic-representation-vortex",
                "ordinary-vector-charge",
                "undoubled-angle-direction",
            ),
            construct_validity_nonclaims=_COMMON_NONCLAIMS,
        ),
    )


@dataclass(frozen=True, slots=True)
class ReferentContractSet:
    """The exact canonical pointwise referents for F0--F4."""

    hypothesis_registry_canonical_sha256: str
    definitions: tuple[ReferentDefinition, ...]
    contract_set_id: str = CANONICAL_REFERENT_CONTRACT_SET_ID
    scientific_claim_eligible: bool = False
    subject_access_authorized: bool = False
    synthetic_construct_validity_scope: str = SYNTHETIC_CONSTRUCT_VALIDITY_SCOPE

    schema_version: ClassVar[str] = REFERENT_CONTRACT_SET_SCHEMA_VERSION

    def __post_init__(self) -> None:
        require_sha256(
            self.hypothesis_registry_canonical_sha256,
            label="hypothesis_registry_canonical_sha256",
        )
        if self.contract_set_id != CANONICAL_REFERENT_CONTRACT_SET_ID:
            raise ReferentContractError(
                "contract_set_id differs from the canonical F0-F4 contract"
            )
        require_false(
            self.scientific_claim_eligible,
            label="scientific_claim_eligible",
        )
        require_false(
            self.subject_access_authorized,
            label="subject_access_authorized",
        )
        if (
            self.synthetic_construct_validity_scope
            != SYNTHETIC_CONSTRUCT_VALIDITY_SCOPE
        ):
            raise ReferentContractError(
                "synthetic_construct_validity_scope differs from the canonical boundary"
            )
        if self.definitions != _canonical_definitions():
            raise ReferentContractError(
                "definitions differ from the canonical F0-F4 referents"
            )

    def require(self, hypothesis_id: HypothesisId) -> ReferentDefinition:
        if not isinstance(hypothesis_id, HypothesisId):
            raise TypeError("hypothesis_id must be a HypothesisId")
        for definition in self.definitions:
            if definition.hypothesis_id is hypothesis_id:
                return definition
        raise KeyError(hypothesis_id.value)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "contract_set_id": self.contract_set_id,
            "hypothesis_registry_canonical_sha256": (
                self.hypothesis_registry_canonical_sha256
            ),
            "definitions": [definition.to_dict() for definition in self.definitions],
            "scientific_claim_eligible": self.scientific_claim_eligible,
            "subject_access_authorized": self.subject_access_authorized,
            "synthetic_construct_validity_scope": (
                self.synthetic_construct_validity_scope
            ),
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, object],
    ) -> ReferentContractSet:
        document = require_mapping(value, label="referent contract set")
        require_exact_keys(
            document,
            expected=frozenset(
                {
                    "schema_version",
                    "contract_set_id",
                    "hypothesis_registry_canonical_sha256",
                    "definitions",
                    "scientific_claim_eligible",
                    "subject_access_authorized",
                    "synthetic_construct_validity_scope",
                }
            ),
            label="referent contract set",
        )
        if document["schema_version"] != cls.schema_version:
            raise ReferentContractError(
                f"schema_version must be exactly {cls.schema_version!r}"
            )
        definitions_value = document["definitions"]
        if not isinstance(definitions_value, list):
            raise ReferentContractError("definitions must be a list")
        return cls(
            contract_set_id=require_slug(
                document["contract_set_id"],
                label="contract_set_id",
            ),
            hypothesis_registry_canonical_sha256=require_sha256(
                document["hypothesis_registry_canonical_sha256"],
                label="hypothesis_registry_canonical_sha256",
            ),
            definitions=tuple(
                ReferentDefinition.from_dict(
                    require_mapping(
                        definition,
                        label=f"definitions[{index}]",
                    )
                )
                for index, definition in enumerate(definitions_value)
            ),
            scientific_claim_eligible=require_false(
                document["scientific_claim_eligible"],
                label="scientific_claim_eligible",
            ),
            subject_access_authorized=require_false(
                document["subject_access_authorized"],
                label="subject_access_authorized",
            ),
            synthetic_construct_validity_scope=require_slug(
                document["synthetic_construct_validity_scope"],
                label="synthetic_construct_validity_scope",
            ),
        )


def canonical_f0_f4_referent_contracts(
    hypothesis_registry_canonical_sha256: str,
) -> ReferentContractSet:
    """Bind the exact F0--F4 referents to one hypothesis-registry identity."""

    return ReferentContractSet(
        hypothesis_registry_canonical_sha256=(hypothesis_registry_canonical_sha256),
        definitions=_canonical_definitions(),
    )
