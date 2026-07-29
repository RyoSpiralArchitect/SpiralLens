from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from spirallens.qualification import advancement
from spirallens.qualification.advancement import (
    CARTESIAN_SELECTION_CONSTRUCTION_FAMILY_ID,
    IndependentConfirmationAdmissionSpec,
    LoadedAdvancementArtifact,
    PersistedAdvancementIdentity,
    SelectionTerminalBinding,
    SurrogateAdvancementDecision,
    load_scope_limited_d6_decision,
)
from spirallens.qualification.common import (
    QualificationContractError,
    QualificationState,
)
from spirallens.qualification.confirmation_execution_design import (
    build_seed_free_d7_confirmation_execution_design,
)
from spirallens.qualification.confirmation_protocol import (
    D6_DECISION_REPOSITORY_PATH,
    MAX_D7_CONFIRMATION_FOUNDATION_BYTES,
    SPECTRAL_MOMENT_CASE_REGISTRY_SHA256,
    SPECTRAL_MOMENT_MECHANISM_SHA256,
    D7ConfirmationFoundation,
    D7ParentD6Binding,
    build_spectral_moment_d7_confirmation_foundation,
)
from spirallens.qualification.persistence import load_qualification_protocol
from spirallens.synthetic.spectral_moment_confirmation import (
    SPECTRAL_MOMENT_CASE_REGISTRY,
)


def _selection_binding() -> SelectionTerminalBinding:
    return SelectionTerminalBinding(
        protocol_id="d0-d5-f2-cartesian-selection-v0-1",
        protocol_source_sha256="1" * 64,
        protocol_canonical_sha256="1" * 64,
        selection_freeze_sha256="2" * 64,
        selection_attempt_claim_sha256="3" * 64,
        launch_authorization_sha256="4" * 64,
        result_id="d0-d5-f2-cartesian-selection-result-v0-1",
        result_sha256="5" * 64,
        result_evidence_root_sha256="6" * 64,
        terminal_manifest_sha256="7" * 64,
        consumption_sha256="8" * 64,
        selection_generator_family_id="cartesian-fourier-domain-v0.1",
        selection_construction_family_id=(
            CARTESIAN_SELECTION_CONSTRUCTION_FAMILY_ID
        ),
        surrogate_estimator_id=(
            "interleaved-first-harmonic-graph-local-direction-v0.4"
        ),
        surrogate_trivialization_id=(
            "fixed-cartesian-fourier-quadrature-basis-v0.1"
        ),
        selection_implementation_registry_sha256="9" * 64,
        graph_axes_sha256="a" * 64,
        required_cells_manifest_sha256="b" * 64,
        required_stress_strata_sha256="c" * 64,
        locked_thresholds_sha256="d" * 64,
        locked_aggregation_sha256="e" * 64,
        gate_states=tuple(
            (f"d{index}", QualificationState.PASS.value)
            for index in range(6)
        ),
        gate_claim_scopes=(
            ("d0", "engine-and-protocol-contracts"),
            ("d1", "cartesian-surrogate-and-representation-development"),
            ("d2", "cartesian-surrogate-only"),
            ("d3", "cartesian-surrogate-and-representation-development"),
            ("d4", "cartesian-surrogate-only"),
            ("d5", "cartesian-surrogate-only"),
        ),
    )


def _authoritative_loaded_d6() -> advancement.LoadedScopeLimitedD6Decision:
    terminal = _selection_binding()
    admission = IndependentConfirmationAdmissionSpec.from_selection(
        terminal,
        admission_spec_id=(
            "cartesian-surrogate-independent-family-admission-v0-1"
        ),
    )
    decision = SurrogateAdvancementDecision.seal(
        decision_id="cartesian-surrogate-d6-decision-v0-1",
        decision_source_commit="f" * 40,
        decision_source_binding_sha256="0" * 64,
        selection_terminal=terminal,
        admission_spec=admission,
    )
    path = Path("/tmp/test-repository") / D6_DECISION_REPOSITORY_PATH
    loaded_artifact = LoadedAdvancementArtifact(
        artifact=decision,
        identity=PersistedAdvancementIdentity(
            path=path,
            source_sha256=decision.canonical_sha256,
            canonical_sha256=decision.canonical_sha256,
            byte_count=len(decision.canonical_bytes),
            parent_directory_fsync_verified=True,
        ),
        source_bytes=decision.canonical_bytes,
    )
    return advancement._build_authoritative_loaded_d6_decision(
        loaded_artifact,
        current_loader_source_commit="1" * 40,
        current_loader_source_binding_sha256="2" * 64,
    )


def test_foundation_requires_authoritative_loaded_d6_receipt() -> None:
    loaded = _authoritative_loaded_d6()
    bare_spec = loaded.decision.confirmation_admission_spec

    with pytest.raises(TypeError, match="LoadedScopeLimitedD6Decision"):
        build_spectral_moment_d7_confirmation_foundation(  # type: ignore[arg-type]
            bare_spec
        )
    with pytest.raises(TypeError):
        D7ParentD6Binding(d6_decision_id="fabricated")  # type: ignore[call-arg]


def test_foundation_binds_parent_and_serializes_every_open_obligation() -> None:
    loaded = _authoritative_loaded_d6()
    foundation = build_spectral_moment_d7_confirmation_foundation(loaded)
    document = foundation.to_dict()
    parent = document["parent_d6"]
    obligations = document["obligations"]

    assert document["status"] == "implementation-foundation-not-frozen"
    assert document["claim_ceiling"] == "level_0"
    assert document["d7_state"] == "not_run"
    assert document["d8_state"] == "not_run"
    assert set(document["authority"].values()) == {False}
    assert parent["d6_decision_id"] == loaded.decision.decision_id
    assert parent["d6_decision_source_sha256"] == (
        loaded.identity.source_sha256
    )
    assert parent["admission_spec_sha256"] == (
        loaded.decision.confirmation_admission_spec.canonical_sha256
    )
    assert parent["current_loader_source_commit"] == (
        loaded.current_loader_source_commit
    )
    assert all(value is False for key, value in obligations.items() if key != "schema_version")


def test_foundation_uses_the_generator_case_registry_without_duplicate_literals() -> None:
    foundation = build_spectral_moment_d7_confirmation_foundation(
        _authoritative_loaded_d6()
    )

    assert tuple(
        (
            item.case_id,
            item.required_semantic,
            item.construction_recipe_id,
            item.core_disposition,
            item.loop_disposition,
        )
        for item in foundation.cases
    ) == SPECTRAL_MOMENT_CASE_REGISTRY
    assert foundation.family.to_dict()["case_registry_sha256"] == (
        SPECTRAL_MOMENT_CASE_REGISTRY_SHA256
    )
    assert SPECTRAL_MOMENT_CASE_REGISTRY_SHA256 == (
        "8a6030405512778c75efdfe27d3ef693"
        "ca13013bcec1ed4e7071cd7d67caf8bc"
    )
    assert SPECTRAL_MOMENT_MECHANISM_SHA256 == (
        "3dedf73dab90463025b527a5e7a1265"
        "c6c860cf95d59bdd165ede0fbcfb107fb"
    )
    mutable_document = foundation.to_dict()
    mutable_document["family"]["mechanism_descriptor"]["construction"] = (  # type: ignore[index]
        "caller-mutation"
    )
    assert foundation.to_dict()["family"]["mechanism_descriptor"][  # type: ignore[index]
        "construction"
    ] == "separable-sine-spectral-moment-grid"


def test_strict_canonical_reload_requires_digest_and_authoritative_reconstruction() -> None:
    loaded = _authoritative_loaded_d6()
    foundation = build_spectral_moment_d7_confirmation_foundation(loaded)

    restored = D7ConfirmationFoundation.from_canonical_bytes(
        foundation.canonical_bytes,
        expected_sha256=foundation.canonical_sha256,
        loaded_d6=loaded,
    )
    assert restored == foundation

    with pytest.raises(QualificationContractError, match="SHA-256"):
        D7ConfirmationFoundation.from_canonical_bytes(
            foundation.canonical_bytes,
            expected_sha256="0" * 64,
            loaded_d6=loaded,
        )
    noncanonical = foundation.canonical_bytes.replace(b"{", b"{ ", 1)
    with pytest.raises(QualificationContractError, match="not canonical"):
        D7ConfirmationFoundation.from_canonical_bytes(
            noncanonical,
            expected_sha256=hashlib.sha256(noncanonical).hexdigest(),
            loaded_d6=loaded,
        )
    duplicate_key = b'{"schema_version":"one","schema_version":"two"}'
    with pytest.raises(QualificationContractError, match="duplicate JSON key"):
        D7ConfirmationFoundation.from_canonical_bytes(
            duplicate_key,
            expected_sha256=hashlib.sha256(duplicate_key).hexdigest(),
            loaded_d6=loaded,
        )
    oversized = b" " * (MAX_D7_CONFIRMATION_FOUNDATION_BYTES + 1)
    with pytest.raises(QualificationContractError, match="fixed cap"):
        D7ConfirmationFoundation.from_canonical_bytes(
            oversized,
            expected_sha256=hashlib.sha256(oversized).hexdigest(),
            loaded_d6=loaded,
        )


def test_foundation_rejects_parent_or_interface_substitution() -> None:
    foundation = build_spectral_moment_d7_confirmation_foundation(
        _authoritative_loaded_d6()
    )

    with pytest.raises(QualificationContractError, match="locked interface"):
        replace(
            foundation,
            locked_interface=replace(
                foundation.locked_interface,
                locked_thresholds_sha256="3" * 64,
            ),
        )
    with pytest.raises(QualificationContractError, match="family proposal"):
        replace(
            foundation,
            family=replace(
                foundation.family,
                selection_generator_family_id="different-selection-family",
            ),
        )


def test_recorded_d6_receipt_builds_the_foundation_when_local_lineage_is_available() -> (
    None
):
    repository = Path(__file__).resolve().parents[1]
    descriptor = (
        repository
        / "experiments"
        / "qualification"
        / "d0_d5_f2_cartesian_selection_v0_1"
        / "launch.json"
    )
    bound_repository = Path(
        json.loads(descriptor.read_bytes())["repository_root"]
    )
    if not bound_repository.is_dir():
        pytest.skip(
            "recorded D6 reload is absolute-path local archival evidence"
        )
    bound_descriptor = (
        bound_repository
        / "experiments"
        / "qualification"
        / "d0_d5_f2_cartesian_selection_v0_1"
        / "launch.json"
    )
    loaded = load_scope_limited_d6_decision(
        (
            bound_repository
            / "experiments"
            / "qualification"
            / "d0_d5_f2_cartesian_selection_v0_1"
            / "d6-surrogate-advancement-decision.json"
        ),
        expected_source_sha256=(
            "c1c3fbbb9a06e8df120755dcf159e015"
            "636d96993bd6ec3a6792312618587a07"
        ),
        expected_canonical_sha256=(
            "c1c3fbbb9a06e8df120755dcf159e015"
            "636d96993bd6ec3a6792312618587a07"
        ),
        expected_decision_id="cartesian-surrogate-d6-decision-v0-1",
        expected_admission_spec_id=(
            "cartesian-surrogate-independent-family-admission-v0-1"
        ),
        launch_descriptor=bound_descriptor,
        launch_descriptor_source_sha256=(
            "a6a8f8a2c3c47cc76053646440cec94c"
            "6bf7da6a6794a2bdda2e4a2cfa28f300"
        ),
        launch_descriptor_canonical_sha256=(
            "a6a8f8a2c3c47cc76053646440cec94c"
            "6bf7da6a6794a2bdda2e4a2cfa28f300"
        ),
        terminal_manifest_sha256=(
            "518b66d715cf9bd05e12de62cb5681ec"
            "63ec7f978fd4d2538ba3c2594deed4b1"
        ),
        terminal_result_sha256=(
            "44749d8d237b8b35874099c605f8de3d"
            "76130691ce8beb92e1ccf80fa368c13a"
        ),
        terminal_consumption_sha256=(
            "a42ae9cffb6a2c87de6ed645e0982e85"
            "b09046a4ed5ad3f815a8a8ce38c0cadb"
        ),
    )
    foundation = build_spectral_moment_d7_confirmation_foundation(loaded)
    descriptor_document = json.loads(bound_descriptor.read_bytes())
    parent_protocol = load_qualification_protocol(
        descriptor_document["protocol_path"],
        expected_source_sha256=(
            descriptor_document["protocol_source_sha256"]
        ),
        expected_canonical_sha256=(
            descriptor_document["protocol_canonical_sha256"]
        ),
    )
    execution_design = build_seed_free_d7_confirmation_execution_design(
        loaded_d6=loaded,
        parent_protocol=parent_protocol,
    )

    assert foundation.parent_d6.d6_decision_canonical_sha256 == (
        "c1c3fbbb9a06e8df120755dcf159e015"
        "636d96993bd6ec3a6792312618587a07"
    )
    assert foundation.parent_d6.admission_spec_sha256 == (
        "2e4aa2a272a38ed68b61f612d8a3a261"
        "cc6376f3d9a8097f5dce701a2c3f5aa4"
    )
    assert execution_design.parent_d6.d6_decision_id == (
        "cartesian-surrogate-d6-decision-v0-1"
    )
    assert execution_design.parent_d6.d6_decision_canonical_sha256 == (
        "c1c3fbbb9a06e8df120755dcf159e015"
        "636d96993bd6ec3a6792312618587a07"
    )
    assert execution_design.parent.protocol_canonical_sha256 == (
        "9908bb83bb5ff5642416aa09d9e468e0"
        "a9499185cec9305e69a54143f2578bd1"
    )
    assert execution_design.parent.graph_axes_sha256 == (
        "71e7e1a128d4bfb4473b1b809fc16dde"
        "58971d38ab0d5b3b1ec8794150e05247"
    )
    assert execution_design.parent.required_cells_manifest_sha256 == (
        "4d243f9ba2c0029480bd98e002914f5a"
        "100aa93ac981aae5517142eee0dae7ff"
    )
    assert execution_design.parent.required_stress_strata_sha256 == (
        "cabe0827e0dc74f4d118fa3453f6e887"
        "eec553a7005fcba3c30e6fea976b982f"
    )
    assert execution_design.parent.locked_thresholds_sha256 == (
        "17b4fc193c4d02ab5526dc2f45028327"
        "01480ef01deaf3acd01a6e06458cf271"
    )
    assert execution_design.parent.locked_aggregation_sha256 == (
        "300c3b63f3897fe808b418369d2dbeac7"
        "6df41160b456f6e5feec6d3995dcef3"
    )
