from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from spirallens import referents
from spirallens.instrument_contracts import load_hypothesis_registry
from spirallens.instrument_contracts.common import ClaimLevel, HypothesisId
from spirallens.referents import (
    ChargeConvention,
    DirectionRule,
    FitEvaluationRule,
    ReferentContractError,
    ReferentContractSet,
    ReferentKind,
    canonical_f0_f4_referent_contracts,
)


def _contract_set() -> ReferentContractSet:
    return canonical_f0_f4_referent_contracts("1" * 64)


def test_canonical_contracts_define_exact_f0_f4_referents() -> None:
    contract_set = _contract_set()

    assert tuple(
        definition.hypothesis_id for definition in contract_set.definitions
    ) == tuple(HypothesisId)
    assert contract_set.scientific_claim_eligible is False
    assert contract_set.subject_access_authorized is False

    f0 = contract_set.require(HypothesisId.F0_SUPPORT)
    assert f0.referent_kind is ReferentKind.SUPPORT_DIAGNOSTIC
    assert f0.order_parameter_defined is False
    assert f0.direction_rule is DirectionRule.NOT_DEFINED
    assert f0.claim_ceiling is ClaimLevel.LEVEL_1G

    f1 = contract_set.require(HypothesisId.F1_PROJECTOR_CONNECTION)
    assert f1.referent_kind is ReferentKind.RANK_TWO_PROJECTOR
    assert f1.order_parameter_defined is False
    assert "integer-charge-from-matrix-holonomy" in f1.forbidden_labels

    f2 = contract_set.require(HypothesisId.F2_LOCAL_COVARIANT_SECTION)
    assert f2.pointwise_formula_id == "z-equals-u-transpose-s"
    assert f2.amplitude_formula_id == "l2-norm-of-z"
    assert f2.gauge_transformation_formula_id == "z-prime-equals-g-transpose-z"
    assert f2.fit_evaluation_rule is FitEvaluationRule.CROSS_FIT_REQUIRED
    assert f2.same_object_amplitude_direction_required is True
    assert f2.pointwise_formula_defined is True
    assert f2.substrate_field_bound is False
    assert f2.interpolation_bound is False
    assert f2.order_parameter_defined is False
    assert f2.charge_convention is ChargeConvention.CONDITIONAL_VECTOR_INTEGER
    assert {
        "amplitude-nonzero-on-loop",
        "connection-or-trivialization-bound",
        "orientability-resolved",
        "reference-resolved",
        "reflection-behavior-validated",
        "sampling-and-refinement-gates-passed",
    }.issubset(f2.required_claim_qualifiers)

    f3 = contract_set.require(HypothesisId.F3_GLOBAL_PLANE_SECTION)
    assert f3.claim_ceiling is ClaimLevel.LEVEL_1D
    assert f3.charge_convention is ChargeConvention.PROJECTION_DEPENDENT_CANDIDATE

    f4 = contract_set.require(HypothesisId.F4_SPIN_TWO_ANISOTROPY)
    assert f4.direction_rule is DirectionRule.NORMALIZE_SPIN_TWO_VECTOR
    assert f4.charge_convention is ChargeConvention.DOUBLED_ANGLE_INTEGER
    assert f4.pointwise_formula_defined is True
    assert f4.order_parameter_defined is False
    assert f4.gauge_transformation_formula_id == "t-prime-equals-g-transpose-t-g"
    assert "ordinary-vector-charge" in f4.forbidden_labels
    assert {
        "amplitude-nonzero-on-loop",
        "director-reference-resolved",
        "reflection-behavior-validated",
        "sampling-and-refinement-gates-passed",
        "spin-two-connection-or-trivialization-bound",
    }.issubset(f4.required_claim_qualifiers)

    for definition in contract_set.definitions:
        assert "does-not-establish-model-side-existence" in (
            definition.construct_validity_nonclaims
        )
        assert "does-not-establish-semantic-meaning" in (
            definition.construct_validity_nonclaims
        )
        assert "does-not-authorize-promotion" in (
            definition.construct_validity_nonclaims
        )


def test_contract_set_round_trips_canonically_and_rejects_drift() -> None:
    contract_set = _contract_set()
    reconstructed = ReferentContractSet.from_dict(contract_set.to_dict())

    assert reconstructed == contract_set
    assert reconstructed.canonical_bytes == contract_set.canonical_bytes
    assert (
        reconstructed.canonical_sha256
        == hashlib.sha256(contract_set.canonical_bytes).hexdigest()
    )

    document = contract_set.to_dict()
    document["definitions"][2]["amplitude_formula_id"] = "independent-amplitude"
    with pytest.raises(
        ReferentContractError,
        match="definitions differ from the canonical",
    ):
        ReferentContractSet.from_dict(document)

    with pytest.raises(
        ReferentContractError,
        match="definitions differ from the canonical",
    ):
        replace(
            contract_set,
            definitions=tuple(reversed(contract_set.definitions)),
        )


def test_non_order_parameter_definition_cannot_acquire_direction() -> None:
    definition = _contract_set().require(HypothesisId.F0_SUPPORT)

    with pytest.raises(
        ReferentContractError,
        match="without a pointwise formula cannot define",
    ):
        replace(
            definition,
            direction_rule=DirectionRule.NORMALIZE_SAME_VECTOR,
        )

    pointwise = _contract_set().require(HypothesisId.F2_LOCAL_COVARIANT_SECTION)
    for field_name in (
        "substrate_field_bound",
        "interpolation_bound",
        "order_parameter_defined",
    ):
        with pytest.raises(
            ReferentContractError,
            match=rf"{field_name} must be false",
        ):
            replace(pointwise, **{field_name: True})


def test_referents_export_surface_is_exact() -> None:
    assert referents.__all__ == [
        "CANONICAL_REFERENT_CONTRACT_SET_ID",
        "MAX_REFERENT_CONTRACT_SET_BYTES",
        "REFERENT_CONTRACT_SET_SCHEMA_VERSION",
        "SYNTHETIC_CONSTRUCT_VALIDITY_SCOPE",
        "ChargeConvention",
        "DirectionRule",
        "FitEvaluationRule",
        "GaugeGroup",
        "LoadedReferentContractSet",
        "ObservationPartition",
        "ReferentContractError",
        "ReferentContractSet",
        "ReferentDefinition",
        "ReferentKind",
        "SectionObservation",
        "SpinTwoObservation",
        "TransformationLaw",
        "canonical_f0_f4_referent_contracts",
        "derive_f2_section",
        "derive_f3_section",
        "derive_f4_spin_two",
        "load_referent_contract_set",
        "validate_observation_partition",
    ]


def test_tracked_registry_produces_the_frozen_referent_identity() -> None:
    repository = Path(__file__).resolve().parents[1]
    referent_path = (
        repository / "protocols" / "order_parameter_referent_contracts_v0_1.json"
    )
    registry = load_hypothesis_registry(
        repository / "protocols" / "order_parameter_hypothesis_registry_v0_1.yaml"
    )

    contract_set = canonical_f0_f4_referent_contracts(registry.canonical_sha256)
    loaded = referents.load_referent_contract_set(
        referent_path,
        expected_source_sha256=contract_set.canonical_sha256,
        expected_canonical_sha256=contract_set.canonical_sha256,
    )

    assert contract_set.canonical_sha256 == (
        "4108ccda4f2a76920091bf2bf422b97297fe4d91ee54f14e2b03362e53e358f2"
    )
    assert loaded.contract_set == contract_set
    assert referent_path.read_bytes() == contract_set.canonical_bytes
