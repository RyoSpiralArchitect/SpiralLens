from __future__ import annotations

import inspect
import shutil
from dataclasses import replace
from pathlib import Path

import pytest
from test_d7_confirmation_execution_design import (
    _authoritative_d6,
    _parent_protocol,
)

import spirallens
from spirallens import qualification
from spirallens.core.canonical import (
    canonical_json_bytes,
    canonical_json_sha256,
    sha256_bytes,
)
from spirallens.qualification import confirmation_c1 as confirmation_c1_module
from spirallens.qualification.advancement import LoadedScopeLimitedD6Decision
from spirallens.qualification.common import QualificationContractError
from spirallens.qualification.confirmation_c1 import (
    D7_C1_BUNDLE_REPOSITORY_PATH,
    D7C1SeedFreeSourceSet,
    build_d7_c1_seed_free_source_set,
    load_d7_c1_seed_free_source_set,
    write_d7_c1_seed_free_source_set,
)
from spirallens.qualification.confirmation_execution_kernel import (
    D7_CONFIRMATION_CORE_POLICY_ID,
    D7_CONFIRMATION_LOOP_POLICY_ID,
    D7_SEED_SLOT_PREDICTION_KERNEL_ID,
)
from spirallens.qualification.persistence import LoadedQualificationProtocol
from spirallens.qualification.protocol import ModuleDigest

REPOSITORY = Path(__file__).resolve().parents[1]


def _c1_inputs() -> tuple[
    LoadedScopeLimitedD6Decision,
    LoadedQualificationProtocol,
]:
    original = _parent_protocol()
    protocol = replace(
        original.protocol,
        engine=replace(
            original.protocol.engine,
            modules=(
                *original.protocol.engine.modules,
                ModuleDigest(
                    "spirallens.synthetic.cartesian_fourier_domain_phantom",
                    "6" * 64,
                ),
            ),
        ),
    )
    parent = LoadedQualificationProtocol(
        protocol=protocol,
        source_path=original.source_path,
        source_bytes=protocol.canonical_bytes,
        source_sha256=protocol.canonical_sha256,
        canonical_sha256=protocol.canonical_sha256,
    )
    return _authoritative_d6(parent), parent


def _patch_c1_parent_pins(
    monkeypatch: pytest.MonkeyPatch,
    loaded_d6: LoadedScopeLimitedD6Decision,
    parent: LoadedQualificationProtocol,
) -> None:
    decision = loaded_d6.decision
    identity = loaded_d6.identity
    admission = decision.confirmation_admission_spec
    monkeypatch.setattr(
        confirmation_c1_module,
        "_CANONICAL_D6_DECISION_ID",
        decision.decision_id,
    )
    monkeypatch.setattr(
        confirmation_c1_module,
        "_CANONICAL_D6_DECISION_SHA256",
        identity.canonical_sha256,
    )
    monkeypatch.setattr(
        confirmation_c1_module,
        "_CANONICAL_D6_ADMISSION_SPEC_ID",
        admission.admission_spec_id,
    )
    monkeypatch.setattr(
        confirmation_c1_module,
        "_CANONICAL_D6_ADMISSION_SPEC_SHA256",
        admission.canonical_sha256,
    )
    monkeypatch.setattr(
        confirmation_c1_module,
        "_CANONICAL_PARENT_PROTOCOL_ID",
        parent.protocol.protocol_id,
    )
    monkeypatch.setattr(
        confirmation_c1_module,
        "_CANONICAL_PARENT_PROTOCOL_SHA256",
        parent.canonical_sha256,
    )
    design = (
        confirmation_c1_module.build_seed_free_d7_confirmation_execution_design(
            loaded_d6=loaded_d6,  # type: ignore[arg-type]
            parent_protocol=parent,
        )
    )
    proposal = confirmation_c1_module.build_d6_d7_structural_rebinding_amendment(
        loaded_d6=loaded_d6,  # type: ignore[arg-type]
        parent_protocol=parent,
        seed_free_design=design,
    )
    monkeypatch.setattr(
        confirmation_c1_module,
        "_CANONICAL_SOURCE_DRAFT_SHA256",
        design.canonical_sha256,
    )
    monkeypatch.setattr(
        confirmation_c1_module,
        "_CANONICAL_HISTORICAL_REBINDING_PROPOSAL_SHA256",
        proposal.canonical_sha256,
    )
    monkeypatch.setattr(
        confirmation_c1_module,
        "_CANONICAL_SELECTION_SOURCE_SHA256",
        "6" * 64,
    )
    monkeypatch.setattr(
        confirmation_c1_module,
        "_CANONICAL_PARENT_ENGINE_COMMIT",
        parent.protocol.engine.commit,
    )


@pytest.fixture(autouse=True)
def _pin_c1_test_lineage(monkeypatch: pytest.MonkeyPatch) -> None:
    loaded_d6, parent = _c1_inputs()
    _patch_c1_parent_pins(monkeypatch, loaded_d6, parent)


def _bundle() -> D7C1SeedFreeSourceSet:
    loaded_d6, parent = _c1_inputs()
    return build_d7_c1_seed_free_source_set(
        loaded_d6=loaded_d6,  # type: ignore[arg-type]
        parent_protocol=parent,
        repository_root=REPOSITORY,
    )


def test_c1_bundle_closes_registry_aggregation_and_review_contract_only() -> None:
    bundle = _bundle()
    document = bundle.to_dict()
    components = document["components"]
    stable = components["seed_free_execution_design"]["body"]
    review = components["construction_diversity_review"]["body"]
    registry = components["implementation_registry"]["body"]
    aggregation = components["aggregation_application"]["body"]
    rebinding = components["successor_rebinding_review_contract"]["body"]

    assert document["status"] == "seed-free-source-set-candidate"
    assert document["repository_path"] == D7_C1_BUNDLE_REPOSITORY_PATH
    assert document["chronology"] == {
        "artifact_knowledge": {
            "candidate_atomically_publishable": True,
            "c1_commit_identity_embedded": False,
            "repository_review_attestation_embedded": False,
            "c2_receipt_embedded": False,
            "source_closure_attestation_embedded": False,
            "official_seed_inventory_embedded": False,
            "confirmation_values_embedded": False,
        },
        "ordering_requirements": {
            "repository_review_required_before_c1_merge": True,
            "c2_must_bind_post_merge_c1": True,
            "official_seed_supplier_must_follow_c2": True,
            "launch_must_follow_seed_free_design_freeze": True,
        },
    }
    assert stable["counts"] == {
        "seed_slots": 2,
        "primary_units": 64,
        "core_cells": 192,
        "loop_cells": 1152,
        "event_lanes": 1344,
    }
    assert stable["committed_c1_verified"] is False
    assert review["declared_construction_diversity_review_passed"] is True
    assert review["static_dependency_review_only"] is True
    assert review["dynamic_or_transitive_independence_proved"] is False
    assert review["epistemic_independence_proved"] is False
    assert review["family_admitted"] is False
    assert review["selection_construction"]["source_sha256"] == "6" * 64
    assert (
        review["source_dependency_review"][
            "dynamic_or_transitive_dependency_absence_proved"
        ]
        is False
    )
    assert registry["parent_bindings"][
        "selection_implementation_registry_reused"
    ] is False
    assert registry["operations"] == {
        "seed_slot_prediction_kernel_id": D7_SEED_SLOT_PREDICTION_KERNEL_ID,
        "crossed_graph_execution_id": (
            "three-a-by-three-b-primary-and-offcore-crossed-execution-v0-1"
        ),
        "core_policy_id": D7_CONFIRMATION_CORE_POLICY_ID,
        "loop_policy_id": D7_CONFIRMATION_LOOP_POLICY_ID,
        "core_and_loop_separate": True,
        "core_and_loop_share_graph_input": True,
        "core_and_loop_share_a_bound_field_estimate": True,
        "oracle_truth_record_is_not_kernel_input": True,
    }
    assert b"d7-development-core" not in canonical_json_bytes(registry)
    assert b"d7-development-loop" not in canonical_json_bytes(registry)
    assert aggregation["bindings"]["parent_locked_aggregation_sha256"] == (
        "300c3b63f3897fe808b418369d2dbeac7"
        "6df41160b456f6e5feec6d3995dcef3"
    )
    assert aggregation["bindings"]["successor_locked_aggregation_sha256"] == (
        "0f3abb2fdea20f21a3460454bad77e6a8"
        "6aba47db47ec34389729a468f9ecc8e"
    )
    assert aggregation["evaluation_design"][
        "paired_repeated_measure_block_unit"
    ] == "confirmation-seed-slot-block"
    assert aggregation["numeric_seed_values_present"] is False
    assert aggregation["counts"] == {
        "seed_slot_blocks": 2,
        "primary_units": 64,
        "core_cells": 192,
        "loop_cells": 1152,
        "required_strata": 6,
        "d2_boundary_collapsed_units": 32,
        "rate_eligible_primary_units": 48,
        "mandatory_prerequisite_primary_units": 16,
        "field_graph_repeats_per_primary": 3,
        "loop_repeats_per_primary": 18,
    }
    assert rebinding["review_contract_encoded"] is True
    assert rebinding["repository_review_attestation_embedded"] is False
    assert rebinding["historical_proposal"][
        "historical_proposal_mutated"
    ] is False
    assert rebinding["effective_for_admission"] is False
    assert rebinding["source_closure_verified"] is False
    assert all(value is False for value in document["authority"].values())


def test_c1_source_manifest_is_complete_for_current_package_tree() -> None:
    bundle = _bundle()
    manifest = bundle.to_dict()["components"]["source_set_manifest"]["body"]
    observed = [item["repository_path"] for item in manifest["entries"]]
    expected = sorted(
        [
            *(
                path.relative_to(REPOSITORY).as_posix()
                for path in (REPOSITORY / "src" / "spirallens").rglob("*.py")
            ),
            "pyproject.toml",
        ]
    )

    assert observed == expected
    assert "src/spirallens/qualification/confirmation_c1.py" in observed
    assert "src/spirallens/qualification/confirmation_execution_kernel.py" in (
        observed
    )
    assert (
        "src/spirallens/qualification/confirmation_source_closure.py" in observed
    )
    assert manifest["bundle_self_included"] is False
    assert manifest["bundle_self_digest_deferred_to_c2"] is True
    assert manifest["source_closure_verified"] is False


def _rehash_component(document: dict[str, object], name: str) -> None:
    components = document["components"]
    assert isinstance(components, dict)
    component = components[name]
    assert isinstance(component, dict)
    body = component["body"]
    assert isinstance(body, dict)
    digest = canonical_json_sha256(body)
    component["canonical_sha256"] = digest
    component_hashes = document["component_hashes"]
    assert isinstance(component_hashes, dict)
    component_hashes[name] = digest
    document["component_set_sha256"] = canonical_json_sha256(component_hashes)


def test_c1_envelope_rejects_nested_mutation_even_after_rehash() -> None:
    bundle = _bundle()
    document = bundle.to_dict()
    document["authority"]["scientific_claim_eligible"] = True
    mutated = canonical_json_bytes(document)

    with pytest.raises(QualificationContractError, match="authority"):
        D7C1SeedFreeSourceSet.from_canonical_bytes(
            mutated,
            expected_sha256=sha256_bytes(mutated),
        )

    document = bundle.to_dict()
    component = document["components"]["implementation_registry"]
    registry = component["body"]
    registry["family_admitted"] = True
    registry["execution_authorized"] = True
    registry["source_closure_verified"] = True
    registry["authority"]["scientific_claim_eligible"] = True
    component_digest = canonical_json_sha256(registry)
    component["canonical_sha256"] = component_digest
    document["component_hashes"]["implementation_registry"] = component_digest
    document["component_set_sha256"] = canonical_json_sha256(
        document["component_hashes"]
    )
    nested_mutation = canonical_json_bytes(document)
    with pytest.raises(
        QualificationContractError,
        match="registry authority",
    ):
        D7C1SeedFreeSourceSet.from_canonical_bytes(
            nested_mutation,
            expected_sha256=sha256_bytes(nested_mutation),
        )

    mutations = (
        (
            "review rule",
            "successor_rebinding_review_contract",
            lambda body: body["declared_fulfillment_rule"].__setitem__(
                "graph_axes_byte_exact",
                False,
            ),
        ),
        (
            "aggregation override",
            "aggregation_application",
            lambda body: body["application_policy"].__setitem__(
                "policy_override_allowed",
                True,
            ),
        ),
        (
            "registry operation",
            "implementation_registry",
            lambda body: body["operations"].__setitem__(
                "oracle_truth_record_is_not_kernel_input",
                False,
            ),
        ),
        (
            "stable identity",
            "seed_free_execution_design",
            lambda body: body.__setitem__("design_id", "rewritten-design"),
        ),
        (
            "source closure",
            "source_set_manifest",
            lambda body: body.__setitem__("git_commit_bound", True),
        ),
    )
    for _label, component_name, mutate in mutations:
        document = bundle.to_dict()
        components = document["components"]
        assert isinstance(components, dict)
        component = components[component_name]
        assert isinstance(component, dict)
        body = component["body"]
        assert isinstance(body, dict)
        mutate(body)
        _rehash_component(document, component_name)
        source = canonical_json_bytes(document)
        with pytest.raises(QualificationContractError):
            D7C1SeedFreeSourceSet.from_canonical_bytes(
                source,
                expected_sha256=sha256_bytes(source),
            )


def test_c1_envelope_pins_parent_derived_historical_bodies() -> None:
    bundle = _bundle()

    document = bundle.to_dict()
    stable = document["components"]["seed_free_execution_design"]["body"]
    draft = stable["seed_free_execution_design"]
    draft["parent_d6"]["required_graph_axes_sha256"] = "f" * 64
    draft["parent"]["graph_axes_sha256"] = "f" * 64
    rewritten_draft_sha256 = canonical_json_sha256(draft)
    stable["source_draft_canonical_sha256"] = rewritten_draft_sha256
    document["parent_bindings"]["source_draft_sha256"] = rewritten_draft_sha256
    _rehash_component(document, "seed_free_execution_design")
    source = canonical_json_bytes(document)
    with pytest.raises(QualificationContractError, match="pinned lineage"):
        D7C1SeedFreeSourceSet.from_canonical_bytes(
            source,
            expected_sha256=sha256_bytes(source),
        )

    document = bundle.to_dict()
    review = document["components"]["successor_rebinding_review_contract"]["body"]
    proposal = review["historical_proposal"]
    proposal["body"]["seed_free_design"]["byte_count"] = 1
    rewritten_proposal_sha256 = canonical_json_sha256(proposal["body"])
    proposal["canonical_sha256"] = rewritten_proposal_sha256
    document["parent_bindings"][
        "historical_rebinding_proposal_sha256"
    ] = rewritten_proposal_sha256
    _rehash_component(document, "successor_rebinding_review_contract")
    source = canonical_json_bytes(document)
    with pytest.raises(QualificationContractError, match="pinned lineage"):
        D7C1SeedFreeSourceSet.from_canonical_bytes(
            source,
            expected_sha256=sha256_bytes(source),
        )


@pytest.mark.parametrize("field", ("source_sha256", "source_commit"))
def test_c1_envelope_pins_selection_source_identity(field: str) -> None:
    document = _bundle().to_dict()
    review = document["components"]["construction_diversity_review"]["body"]
    review["selection_construction"][field] = (
        "f" * 64 if field == "source_sha256" else "f" * 40
    )
    _rehash_component(document, "construction_diversity_review")
    source = canonical_json_bytes(document)
    with pytest.raises(
        QualificationContractError,
        match="construction-family identities differ",
    ):
        D7C1SeedFreeSourceSet.from_canonical_bytes(
            source,
            expected_sha256=sha256_bytes(source),
        )


def test_c1_envelope_rejects_boolean_integer_laundering() -> None:
    bundle = _bundle()

    root_mutations = (
        (("authority", "scientific_claim_eligible"), 0),
        (
            (
                "chronology",
                "artifact_knowledge",
                "c1_commit_identity_embedded",
            ),
            0,
        ),
        (
            (
                "chronology",
                "ordering_requirements",
                "c2_must_bind_post_merge_c1",
            ),
            1,
        ),
        (("deferred", "choice_free_c2_receipt"), 1),
    )
    for path, replacement in root_mutations:
        document = bundle.to_dict()
        cursor = document
        for key in path[:-1]:
            nested = cursor[key]
            assert isinstance(nested, dict)
            cursor = nested
        cursor[path[-1]] = replacement
        source = canonical_json_bytes(document)
        with pytest.raises(QualificationContractError, match="differ"):
            D7C1SeedFreeSourceSet.from_canonical_bytes(
                source,
                expected_sha256=sha256_bytes(source),
            )

    component_mutations = (
        (
            "seed_free_execution_design",
            ("seed_free_execution_design", "authority", "semantic_authority"),
            0,
        ),
        (
            "construction_diversity_review",
            ("mechanism_comparison", "implementation_distinct"),
            1,
        ),
        (
            "source_set_manifest",
            ("role_counts", "packaging_contract"),
            True,
        ),
    )
    for component_name, path, replacement in component_mutations:
        document = bundle.to_dict()
        body = document["components"][component_name]["body"]
        cursor = body
        for key in path[:-1]:
            nested = cursor[key]
            assert isinstance(nested, dict)
            cursor = nested
        cursor[path[-1]] = replacement
        _rehash_component(document, component_name)
        source = canonical_json_bytes(document)
        with pytest.raises(QualificationContractError, match="differ"):
            D7C1SeedFreeSourceSet.from_canonical_bytes(
                source,
                expected_sha256=sha256_bytes(source),
            )


@pytest.mark.parametrize(
    "malicious_path",
    (
        "src/spirallens/../evil.py",
        "src/spirallens/./evil.py",
        "src/spirallens//evil.py",
        "/src/spirallens/evil.py",
        "src\\spirallens\\evil.py",
        "src/spirallens/evil.py\nignored",
    ),
)
def test_c1_source_manifest_rejects_noncanonical_paths(
    malicious_path: str,
) -> None:
    document = _bundle().to_dict()
    manifest = document["components"]["source_set_manifest"]["body"]
    entry = next(
        item
        for item in manifest["entries"]
        if item["repository_path"].startswith("src/spirallens/")
    )
    entry["repository_path"] = malicious_path
    manifest["entries"] = sorted(
        manifest["entries"],
        key=lambda item: item["repository_path"],
    )
    _rehash_component(document, "source_set_manifest")
    source = canonical_json_bytes(document)
    with pytest.raises(
        QualificationContractError,
        match="canonical relative POSIX path",
    ):
        D7C1SeedFreeSourceSet.from_canonical_bytes(
            source,
            expected_sha256=sha256_bytes(source),
        )


def test_c1_builder_rejects_alternate_valid_parent_choices() -> None:
    loaded_d6, parent = _c1_inputs()
    alternate_d6 = _authoritative_d6(
        parent,
        decision_id="alternate-valid-d6-decision-v0-1",
    )
    with pytest.raises(
        QualificationContractError,
        match="one pinned D6",
    ):
        build_d7_c1_seed_free_source_set(
            loaded_d6=alternate_d6,
            parent_protocol=parent,
            repository_root=REPOSITORY,
        )

    alternate_parent = _parent_protocol(
        selection_seeds=(500001, 500002),
    )
    with pytest.raises(
        QualificationContractError,
        match="one pinned parent protocol",
    ):
        build_d7_c1_seed_free_source_set(
            loaded_d6=loaded_d6,  # type: ignore[arg-type]
            parent_protocol=alternate_parent,
            repository_root=REPOSITORY,
        )


def test_c1_source_enumeration_is_bounded_before_bundle_construction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    member = tmp_path / "member.py"
    member.write_bytes(b"12345")
    monkeypatch.setattr(
        confirmation_c1_module,
        "MAX_D7_C1_SOURCE_MEMBER_BYTES",
        4,
    )
    with pytest.raises(QualificationContractError, match="nonempty and bounded"):
        confirmation_c1_module._regular_source(tmp_path, "member.py")

    monkeypatch.setattr(
        confirmation_c1_module,
        "MAX_D7_C1_SOURCE_MEMBER_BYTES",
        8 * 1024 * 1024,
    )
    monkeypatch.setattr(
        confirmation_c1_module,
        "MAX_D7_C1_SOURCE_FILE_COUNT",
        1,
    )
    with pytest.raises(QualificationContractError, match="file-count cap"):
        confirmation_c1_module._source_set_document(REPOSITORY)

    monkeypatch.setattr(
        confirmation_c1_module,
        "MAX_D7_C1_SOURCE_FILE_COUNT",
        8192,
    )
    monkeypatch.setattr(
        confirmation_c1_module,
        "MAX_D7_C1_SOURCE_SET_TOTAL_BYTES",
        1,
    )
    with pytest.raises(QualificationContractError, match="total-byte cap"):
        confirmation_c1_module._source_set_document(REPOSITORY)


def test_c1_rejects_a_repository_copy_loaded_by_another_source_identity(
    tmp_path: Path,
) -> None:
    copied = tmp_path / "copy"
    shutil.copytree(REPOSITORY, copied)
    loaded_d6, parent = _c1_inputs()

    with pytest.raises(QualificationContractError, match="source checkout"):
        build_d7_c1_seed_free_source_set(
            loaded_d6=loaded_d6,  # type: ignore[arg-type]
            parent_protocol=parent,
            repository_root=copied,
        )


@pytest.mark.parametrize(
    "forbidden_import",
    (
        (
            b"import spirallens.synthetic.cartesian_fourier_domain_phantom as "
            b"selection_generator_module\n"
        ),
        b"from . import cartesian_fourier_domain_phantom\n",
        b"from spirallens.synthetic import cartesian_fourier_domain_phantom\n",
        (
            b"from spirallens.synthetic.cartesian_fourier_domain_phantom import "
            b"CartesianFourierEstimatorInputs\n"
        ),
        (
            b"from ..synthetic.cartesian_fourier_domain_phantom import "
            b"CartesianFourierEstimatorInputs\n"
        ),
        (
            b"from .other.cartesian_fourier_domain_phantom import "
            b"CartesianFourierEstimatorInputs\n"
        ),
    ),
)
def test_construction_review_rejects_nonexact_cartesian_module_imports(
    monkeypatch: pytest.MonkeyPatch,
    forbidden_import: bytes,
) -> None:
    malicious = forbidden_import + (
        b"from .cartesian_fourier_domain_phantom import "
        b"CartesianFourierEstimatorInputs\n"
    )

    monkeypatch.setattr(
        confirmation_c1_module,
        "_regular_source",
        lambda _root, _relative: (malicious, "100644"),
    )
    with pytest.raises(QualificationContractError, match="dependency review"):
        confirmation_c1_module._spectral_import_review(REPOSITORY)


def test_c1_writer_and_authoritative_loader_round_trip_without_overwrite(
    tmp_path: Path,
) -> None:
    loaded_d6, parent = _c1_inputs()
    bundle = build_d7_c1_seed_free_source_set(
        loaded_d6=loaded_d6,  # type: ignore[arg-type]
        parent_protocol=parent,
        repository_root=REPOSITORY,
    )
    destination = tmp_path / "c1.json"
    published = write_d7_c1_seed_free_source_set(destination, bundle)
    loaded = load_d7_c1_seed_free_source_set(
        destination,
        expected_source_sha256=published.identity.source_sha256,
        expected_canonical_sha256=published.identity.canonical_sha256,
        loaded_d6=loaded_d6,  # type: ignore[arg-type]
        parent_protocol=parent,
        repository_root=REPOSITORY,
    )

    assert loaded == bundle
    assert published.committed_c1_verified is False
    assert published.source_closure_verified is False
    with pytest.raises(QualificationContractError, match="overwrite"):
        write_d7_c1_seed_free_source_set(destination, bundle)


def test_c1_builders_accept_no_seed_result_or_admission_choices() -> None:
    parameters = set(inspect.signature(build_d7_c1_seed_free_source_set).parameters)
    assert parameters == {
        "loaded_d6",
        "parent_protocol",
        "repository_root",
    }
    assert "confirmation_c1" not in spirallens.__all__
    assert "confirmation_c1" not in qualification.__all__
    assert "confirmation_source_closure" not in spirallens.__all__
    assert "confirmation_source_closure" not in qualification.__all__
