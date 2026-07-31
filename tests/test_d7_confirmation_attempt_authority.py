from __future__ import annotations

import builtins
import copy
import inspect
from dataclasses import replace

import pytest

from spirallens.core.canonical import canonical_json_bytes, sha256_bytes
from spirallens.qualification import confirmation_attempt_authority as authority
from spirallens.qualification import confirmation_replay_contracts


def _opaque(
    role: str,
    marker: int,
    *,
    contract_id: str = "spirallens.test-artifact.v0.1",
) -> authority.D7AuthorityArtifactBinding:
    source = f"opaque-{marker:04d}-{role}".encode()
    return authority.D7AuthorityArtifactBinding(
        artifact_role=role,
        artifact_contract_id=contract_id,
        canonical_sha256=sha256_bytes(source),
        byte_count=len(source),
    )


def _bind(
    role: str,
    record: object,
) -> authority.D7AuthorityArtifactBinding:
    return authority.D7AuthorityArtifactBinding.from_record(
        artifact_role=role,
        artifact_contract_id=record.schema_version,  # type: ignore[attr-defined]
        record=record,  # type: ignore[arg-type]
    )


def _recorded_parent_bindings() -> tuple[
    authority.D7AuthorityArtifactBinding,
    authority.D7AuthorityArtifactBinding,
    authority.D7AuthorityArtifactBinding,
]:
    return (
        authority.D7AuthorityArtifactBinding(
            artifact_role="recorded-c1",
            artifact_contract_id=authority.D7_RECORDED_C1_SCHEMA_VERSION,
            canonical_sha256=authority.D7_RECORDED_C1_CANONICAL_SHA256,
            byte_count=authority.D7_RECORDED_C1_BYTE_COUNT,
        ),
        authority.D7AuthorityArtifactBinding(
            artifact_role="recorded-c2",
            artifact_contract_id=authority.D7_RECORDED_C2_SCHEMA_VERSION,
            canonical_sha256=authority.D7_RECORDED_C2_CANONICAL_SHA256,
            byte_count=authority.D7_RECORDED_C2_BYTE_COUNT,
        ),
        authority.D7ParentSelectionSeedExclusionRegistryRecord.exact().parent_protocol_binding,
    )


def _bundle() -> authority.D7LaunchAuthorityInputBundle:
    final_code = authority.D7ChronologyInputRecord(
        transition=authority.D7SeedSupplyTransition.FINAL_CODE_REVIEWED,
        ordinal=0,
        record_id="chronology-final-code-review-v0-1",
        predecessor_binding=None,
        subject_bindings=tuple(
            _opaque(role, index)
            for index, role in enumerate(
                (
                    "lifecycle-code",
                    "result-code",
                    "terminal-code",
                    "witness-code",
                    "runner-code",
                ),
                start=1,
            )
        ),
    )
    runtime = authority.D7RuntimeSpecificationInputRecord(
        runtime_specification_id="runtime-specification-v0-1",
        python_implementation="cpython",
        python_version="3.11.9",
        platform="darwin",
        machine="arm64",
        dependency_lock_sha256="1" * 64,
        native_runtime_sha256="2" * 64,
    )
    source_runtime_receipt = _opaque(
        "execution-source-runtime-receipt",
        8,
    )
    closure = authority.D7SourceRuntimeClosureInputRecord(
        closure_id="execution-source-runtime-closure-v0-1",
        receipt_binding=source_runtime_receipt,
        final_code_review_binding=final_code.artifact_binding,
        runtime_specification_binding=_bind("runtime-specification", runtime),
        source_commit="a" * 40,
        source_tree_sha256="3" * 64,
        transitive_dependency_set_sha256="4" * 64,
    )
    closure_transition = authority.D7ChronologyInputRecord(
        transition=(authority.D7SeedSupplyTransition.EXACT_SOURCE_RUNTIME_CLOSURE),
        ordinal=1,
        record_id="chronology-source-runtime-closure-v0-1",
        predecessor_binding=final_code.artifact_binding,
        subject_bindings=(source_runtime_receipt,),
    )
    readiness_subject = _opaque("seed-free-readiness", 10)
    readiness = authority.D7ChronologyInputRecord(
        transition=authority.D7SeedSupplyTransition.SEED_FREE_READINESS,
        ordinal=2,
        record_id="chronology-seed-free-readiness-v0-1",
        predecessor_binding=closure_transition.artifact_binding,
        subject_bindings=(readiness_subject,),
    )
    admission_receipt = _opaque("family-admission-receipt", 11)
    admission_spec = _opaque("admission-spec", 12)
    admission = authority.D7FamilyAdmissionInputRecord(
        admission_id="reviewed-family-admission-v0-1",
        generator_family_id=authority.D7_CONFIRMATION_GENERATOR_FAMILY_ID,
        admission_receipt_binding=admission_receipt,
        source_runtime_closure_binding=_bind(
            "execution-source-runtime-closure",
            closure,
        ),
        seed_free_readiness_binding=readiness_subject,
        construction_review_binding=_opaque("construction-review", 13),
        admission_spec_binding=admission_spec,
    )
    admission_transition = authority.D7ChronologyInputRecord(
        transition=authority.D7SeedSupplyTransition.REVIEWED_FAMILY_ADMISSION,
        ordinal=3,
        record_id="chronology-reviewed-family-admission-v0-1",
        predecessor_binding=readiness.artifact_binding,
        subject_bindings=(admission_receipt,),
    )
    development_registry = authority.D7DevelopmentSeedExclusionRegistryRecord.exact()
    parent_registry = authority.D7ParentSelectionSeedExclusionRegistryRecord.exact()
    development_registry_binding = _bind(
        "development-seed-exclusion-registry",
        development_registry,
    )
    parent_registry_binding = _bind(
        "parent-selection-seed-exclusion-registry",
        parent_registry,
    )
    inventory = authority.D7OfficialSeedInventoryRecord(
        inventory_id="official-seed-inventory-v0-1",
        development_exclusion_registry_binding=development_registry_binding,
        parent_selection_exclusion_registry_binding=parent_registry_binding,
        seeds=(
            authority.D7OfficialSeed(
                seed_slot_id=authority.D7_CONFIRMATION_SEED_SLOT_IDS[0],
                seed=10_000_001,
            ),
            authority.D7OfficialSeed(
                seed_slot_id=authority.D7_CONFIRMATION_SEED_SLOT_IDS[1],
                seed=10_000_002,
            ),
        ),
    )
    official_inventory_binding = _bind(
        "official-seed-inventory",
        inventory,
    )
    supplier_identity = _opaque("seed-supplier-identity", 14)
    exclusive_claim = authority.D7ExclusiveSeedSupplyClaimInputRecord(
        claim_id="exclusive-seed-supply-claim-v0-1",
        supplier_identity_binding=supplier_identity,
        development_exclusion_registry_binding=development_registry_binding,
        parent_selection_exclusion_registry_binding=parent_registry_binding,
        seed_free_readiness_binding=readiness_subject,
        admission_receipt_binding=admission_receipt,
        source_runtime_receipt_binding=source_runtime_receipt,
    )
    claim = authority.D7ChronologyInputRecord(
        transition=(authority.D7SeedSupplyTransition.EXCLUSIVE_SEED_SUPPLY_CLAIM),
        ordinal=4,
        record_id="chronology-exclusive-seed-supply-claim-v0-1",
        predecessor_binding=admission_transition.artifact_binding,
        subject_bindings=(exclusive_claim.artifact_binding,),
    )
    single_invocation = authority.D7SingleSupplierInvocationInputRecord(
        invocation_id="single-supplier-invocation-v0-1",
        claim_binding=exclusive_claim.artifact_binding,
        supplier_identity_binding=supplier_identity,
        official_seed_inventory_binding=official_inventory_binding,
    )
    invocation = authority.D7ChronologyInputRecord(
        transition=authority.D7SeedSupplyTransition.SINGLE_SUPPLIER_INVOCATION,
        ordinal=5,
        record_id="chronology-single-supplier-invocation-v0-1",
        predecessor_binding=claim.artifact_binding,
        subject_bindings=(single_invocation.artifact_binding,),
    )
    implementation_registry = _opaque("implementation-registry", 16)
    aggregation = _opaque("aggregation", 17)
    result_payload_schema = _opaque("result-payload-schema", 18)
    full_inventory = _opaque("full-inventory", 19)
    full_design_artifact = _opaque("full-design", 20)
    target_admission = authority.D7TargetAdmissionBindingCandidate(
        receipt_binding=admission_receipt,
        generator_family_id=admission.generator_family_id,
        construction_review_binding=admission.construction_review_binding,
        admission_spec_binding=admission_spec,
        source_runtime_receipt_sha256=(source_runtime_receipt.canonical_sha256),
    )
    target_source_runtime = authority.D7TargetSourceRuntimeBindingCandidate(
        receipt_binding=source_runtime_receipt,
        runtime_specification_sha256=runtime.canonical_sha256,
    )
    target_full_design = authority.D7TargetFullDesignBindingCandidate(
        design_binding=full_design_artifact,
        inventory_binding=full_inventory,
        inventory_sha256=full_inventory.canonical_sha256,
        official_seed_inventory_sha256=inventory.canonical_sha256,
        implementation_registry_sha256=(implementation_registry.canonical_sha256),
        aggregation_sha256=aggregation.canonical_sha256,
        result_payload_schema_sha256=(result_payload_schema.canonical_sha256),
    )
    target = authority.D7ReplayTargetInputRecord(
        replay_target_id="spectral-moment-replay-target-v0-1",
        parent_bindings=_recorded_parent_bindings(),
        admission_receipt_binding=target_admission,
        official_seed_inventory_binding=official_inventory_binding,
        full_design_binding=target_full_design,
        implementation_registry_binding=implementation_registry,
        aggregation_binding=aggregation,
        result_payload_schema_binding=result_payload_schema,
        execution_source_runtime_closure_binding=target_source_runtime,
    )
    publication = authority.D7ChronologyInputRecord(
        transition=(authority.D7SeedSupplyTransition.ATOMIC_DESIGN_TARGET_PUBLICATION),
        ordinal=6,
        record_id="chronology-atomic-design-target-publication-v0-1",
        predecessor_binding=invocation.artifact_binding,
        subject_bindings=(
            official_inventory_binding,
            full_design_artifact,
            _bind("replay-target", target),
        ),
    )
    freeze = authority.D7FullDesignFreezeInputRecord(
        freeze_id="full-design-freeze-v0-1",
        full_design_binding=full_design_artifact,
        replay_target_binding=_bind("replay-target", target),
        atomic_publication_binding=publication.artifact_binding,
        freeze_commit="b" * 40,
        authorization_commit="c" * 40,
    )
    freeze_transition = authority.D7ChronologyInputRecord(
        transition=(authority.D7SeedSupplyTransition.COMMITTED_FULL_DESIGN_FREEZE),
        ordinal=7,
        record_id="chronology-committed-full-design-freeze-v0-1",
        predecessor_binding=publication.artifact_binding,
        subject_bindings=(_bind("full-design-freeze", freeze),),
    )
    execution_identity = authority.D7ExecutionIdentityInputRecord(
        execution_identity_id="execution-identity-v0-1",
        source_runtime_closure_binding=_bind(
            "execution-source-runtime-closure",
            closure,
        ),
        runtime_specification_binding=_bind("runtime-specification", runtime),
        executable_sha256="5" * 64,
        callable_identity_sha256="6" * 64,
        process_identity_sha256="7" * 64,
    )
    physical = authority.D7PhysicalStoreLaneIdentityRecord(
        physical_identity_id="physical-store-lane-identity-v0-1",
        attempt_key_sha256="8" * 64,
        store_path="/var/tmp/spirallens-d7",
        store_device=101,
        store_inode=202,
        lane_path=("/var/tmp/spirallens-d7/d7-prefix-evidence-only-v0"),
        lane_device=101,
        lane_inode=303,
        lane_parent_device=101,
        lane_parent_inode=202,
        output_namespace_path="/var/tmp/spirallens-d7/output",
        output_parent_device=101,
        output_parent_inode=202,
        terminal_path="/var/tmp/spirallens-d7/terminal",
        terminal_parent_device=101,
        terminal_parent_inode=202,
    )
    intent = authority.D7LaunchIntentInputRecord(
        launch_intent_id="launch-intent-v0-1",
        replay_target_binding=_bind("replay-target", target),
        full_design_freeze_binding=_bind("full-design-freeze", freeze),
        execution_identity_binding=_bind(
            "execution-identity",
            execution_identity,
        ),
        physical_identity_binding=_bind(
            "physical-store-lane-identity",
            physical,
        ),
        freeze_commit="b" * 40,
        authorization_commit="c" * 40,
    )
    intent_transition = authority.D7ChronologyInputRecord(
        transition=authority.D7SeedSupplyTransition.LAUNCH_INTENT,
        ordinal=8,
        record_id="chronology-launch-intent-v0-1",
        predecessor_binding=freeze_transition.artifact_binding,
        subject_bindings=(_bind("launch-intent", intent),),
    )
    return authority.D7LaunchAuthorityInputBundle(
        bundle_id="launch-authority-input-bundle-v0-1",
        development_seed_exclusion_registry=development_registry,
        parent_selection_seed_exclusion_registry=parent_registry,
        official_seed_inventory=inventory,
        runtime_specification=runtime,
        source_runtime_closure=closure,
        family_admission=admission,
        exclusive_seed_supply_claim=exclusive_claim,
        single_supplier_invocation=single_invocation,
        execution_identity=execution_identity,
        physical_store_lane_identity=physical,
        replay_target=target,
        full_design_freeze=freeze,
        launch_intent=intent,
        chronology=(
            final_code,
            closure_transition,
            readiness,
            admission_transition,
            claim,
            invocation,
            publication,
            freeze_transition,
            intent_transition,
        ),
    )


def _load_document(
    document: dict[str, object],
) -> authority.LoadedD7LaunchAuthorityStructuralCandidate:
    source = canonical_json_bytes(document)
    return authority.load_d7_launch_authority_structural_candidate(
        source,
        expected_sha256=sha256_bytes(source),
    )


def test_canonical_round_trip_is_structural_only() -> None:
    bundle = _bundle()
    loaded = authority.load_d7_launch_authority_structural_candidate(
        bundle.canonical_bytes,
        expected_sha256=bundle.canonical_sha256,
    )
    assert loaded.bundle == bundle
    assert loaded.source_sha256 == bundle.canonical_sha256
    assert loaded.byte_count == bundle.byte_count
    assert loaded.bundle.canonical_bytes == bundle.canonical_bytes
    assert authority.D7LaunchAuthorityInputBundle.from_dict(bundle.to_dict()) == bundle


def test_digest_is_checked_before_malformed_bytes_are_parsed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _unexpected_parse(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("wrong-digest source reached canonical parser")

    monkeypatch.setattr(authority, "parse_canonical_json", _unexpected_parse)
    with pytest.raises(
        authority.D7AuthorityInputError,
        match="digest differs before parse",
    ):
        authority.load_d7_launch_authority_structural_candidate(
            b"{",
            expected_sha256="0" * 64,
        )


def test_matching_digest_malformed_canonical_json_is_translated() -> None:
    source = b"{"
    with pytest.raises(
        authority.D7AuthorityInputError,
        match="canonical|parse",
    ):
        authority.load_d7_launch_authority_structural_candidate(
            source,
            expected_sha256=sha256_bytes(source),
        )


@pytest.mark.parametrize(
    "source",
    (
        b"[" * 1000 + b"0" + b"]" * 1000,
        b"1" * 5000,
    ),
)
def test_matching_digest_hostile_json_is_translated(source: bytes) -> None:
    with pytest.raises(
        authority.D7AuthorityInputError,
        match="canonical JSON",
    ):
        authority.load_d7_launch_authority_structural_candidate(
            source,
            expected_sha256=sha256_bytes(source),
        )


def test_loader_rejects_oversize_input() -> None:
    source = b"x" * (authority.MAX_D7_LAUNCH_AUTHORITY_INPUT_BYTES + 1)
    with pytest.raises(
        authority.D7AuthorityInputError,
        match="byte count is out of bounds",
    ):
        authority.load_d7_launch_authority_structural_candidate(
            source,
            expected_sha256=sha256_bytes(source),
        )


def test_target_fields_exactly_match_the_frozen_contract_surface() -> None:
    contract_source = canonical_json_bytes(
        confirmation_replay_contracts._target_document()
    )
    contract = (
        confirmation_replay_contracts.D7ReplayTargetContractSpec.from_canonical_bytes(
            contract_source,
            expected_sha256=sha256_bytes(contract_source),
        )
    )
    expected = contract.to_dict()["future_replay_target"]["required_fields"]
    assert list(_bundle().replay_target.to_dict()) == expected


def test_unrelated_generator_family_cannot_be_laundered_into_target() -> None:
    document = copy.deepcopy(_bundle().to_dict())
    document["family_admission"]["generator_family_id"] = (  # type: ignore[index]
        "unrelated-generator-family-v9"
    )
    document["replay_target"]["admission_receipt_binding"][  # type: ignore[index]
        "generator_family_id"
    ] = "unrelated-generator-family-v9"

    with pytest.raises(authority.D7AuthorityInputError, match="family"):
        _load_document(document)


@pytest.mark.parametrize(
    "binding_name",
    ("construction_review_binding", "admission_spec_binding"),
)
def test_admission_semantic_roles_cannot_be_laundered(
    binding_name: str,
) -> None:
    document = copy.deepcopy(_bundle().to_dict())
    document["family_admission"][binding_name]["artifact_role"] = (  # type: ignore[index]
        "seed-supplier-identity"
    )
    document["replay_target"]["admission_receipt_binding"][binding_name][  # type: ignore[index]
        "artifact_role"
    ] = "seed-supplier-identity"

    with pytest.raises(authority.D7AuthorityInputError, match="admission.*role"):
        _load_document(document)


@pytest.mark.parametrize(
    "binding_name",
    ("construction_review_binding", "admission_spec_binding"),
)
@pytest.mark.parametrize(
    "leaf",
    ("artifact_contract_id", "canonical_sha256", "byte_count"),
)
def test_target_admission_preserves_full_semantic_binding_identity(
    binding_name: str,
    leaf: str,
) -> None:
    document = copy.deepcopy(_bundle().to_dict())
    binding = document["family_admission"][binding_name]  # type: ignore[index]
    if leaf == "artifact_contract_id":
        binding[leaf] = "spirallens.substituted-artifact.v0.1"  # type: ignore[index]
    elif leaf == "canonical_sha256":
        binding[leaf] = "e" * 64  # type: ignore[index]
    else:
        binding[leaf] += 1  # type: ignore[index,operator]

    with pytest.raises(authority.D7AuthorityInputError, match="admission"):
        _load_document(document)


def test_target_requires_all_three_exact_recorded_parent_bindings() -> None:
    omitted = copy.deepcopy(_bundle().to_dict())
    omitted["replay_target"]["parent_bindings"].pop()  # type: ignore[index,union-attr]
    with pytest.raises(authority.D7AuthorityInputError, match="parent"):
        _load_document(omitted)

    for index in range(3):
        substituted = copy.deepcopy(_bundle().to_dict())
        substituted["replay_target"]["parent_bindings"][index][  # type: ignore[index]
            "canonical_sha256"
        ] = "e" * 64
        with pytest.raises(authority.D7AuthorityInputError, match="parent"):
            _load_document(substituted)


@pytest.mark.parametrize(
    ("path", "match"),
    (
        (
            (
                "replay_target",
                "admission_receipt_binding",
                "construction_review_sha256",
            ),
            "admission semantic digest",
        ),
        (
            (
                "replay_target",
                "admission_receipt_binding",
                "admission_spec_sha256",
            ),
            "admission semantic digest",
        ),
        (
            (
                "replay_target",
                "full_design_binding",
                "inventory_sha256",
            ),
            "inventory",
        ),
        (
            (
                "replay_target",
                "full_design_binding",
                "official_seed_inventory_sha256",
            ),
            "full-design|inventory",
        ),
        (
            (
                "replay_target",
                "execution_source_runtime_closure_binding",
                "receipt_sha256",
            ),
            "receipt",
        ),
        (
            (
                "replay_target",
                "execution_source_runtime_closure_binding",
                "runtime_specification_sha256",
            ),
            "source/runtime|runtime",
        ),
    ),
)
def test_target_semantic_leaf_substitutions_fail_closed(
    path: tuple[str, ...],
    match: str,
) -> None:
    document = copy.deepcopy(_bundle().to_dict())
    cursor: object = document
    for part in path[:-1]:
        cursor = cursor[part]  # type: ignore[index]
    cursor[path[-1]] = "e" * 64  # type: ignore[index]

    with pytest.raises(authority.D7AuthorityInputError, match=match):
        _load_document(document)


def test_development_and_parent_exclusion_registries_are_exact() -> None:
    bundle = _bundle()
    development = bundle.development_seed_exclusion_registry
    parent = bundle.parent_selection_seed_exclusion_registry

    assert development.canonical_sha256 == (
        authority.D7_DEVELOPMENT_SEED_EXCLUSION_SHA256
    )
    assert [entry.seed for entry in development.entries] == [
        11,
        12,
        9001,
        9002,
    ]
    assert parent.parent_protocol_binding == _recorded_parent_bindings()[2]
    assert parent.selection_manifest_sha256 == (
        authority.D7_PARENT_SELECTION_MANIFEST_SHA256
    )
    assert parent.seed_family_commitment_sha256 == (
        authority.D7_PARENT_SEED_FAMILY_COMMITMENT_SHA256
    )
    assert parent.seed_family_id == authority.D7_PARENT_SEED_FAMILY_ID
    assert tuple(entry.seed for entry in parent.entries) == (
        authority.D7_PARENT_SELECTION_SEEDS
    )


@pytest.mark.parametrize(
    ("path", "replacement", "match"),
    (
        (
            ("development_seed_exclusion_registry", "entries"),
            lambda entries: entries[:-1],
            "exact frozen body",
        ),
        (
            (
                "development_seed_exclusion_registry",
                "entries",
                0,
                "seed",
            ),
            lambda _seed: 13,
            "exact frozen body",
        ),
        (
            ("parent_selection_seed_exclusion_registry", "entries"),
            lambda entries: entries[:-1],
            "both exact parent seeds",
        ),
        (
            ("parent_selection_seed_exclusion_registry", "entries", 0, "seed"),
            lambda _seed: 99,
            "both exact parent seeds",
        ),
        (
            (
                "parent_selection_seed_exclusion_registry",
                "selection_manifest_sha256",
            ),
            lambda _digest: "e" * 64,
            "frozen selection",
        ),
        (
            ("official_seed_inventory", "seeds", 0, "seed"),
            lambda _seed: 11,
            "overlap development or parent",
        ),
        (
            (
                "replay_target",
                "official_seed_inventory_binding",
                "canonical_sha256",
            ),
            lambda _digest: "f" * 64,
            "exact record",
        ),
    ),
)
def test_seed_completeness_and_target_joins_fail_closed(
    path: tuple[object, ...],
    replacement: object,
    match: str,
) -> None:
    document = copy.deepcopy(_bundle().to_dict())
    cursor: object = document
    for part in path[:-1]:
        cursor = cursor[part]  # type: ignore[index]
    leaf = path[-1]
    cursor[leaf] = replacement(cursor[leaf])  # type: ignore[index,operator]
    with pytest.raises(authority.D7AuthorityInputError, match=match):
        _load_document(document)


@pytest.mark.parametrize(
    "path",
    (
        (
            "official_seed_inventory",
            "development_exclusion_registry_binding",
        ),
        (
            "official_seed_inventory",
            "parent_selection_exclusion_registry_binding",
        ),
        ("source_runtime_closure", "receipt_binding"),
        ("source_runtime_closure", "runtime_specification_binding"),
        ("family_admission", "admission_receipt_binding"),
        ("family_admission", "source_runtime_closure_binding"),
        ("execution_identity", "source_runtime_closure_binding"),
        ("execution_identity", "runtime_specification_binding"),
        (
            "replay_target",
            "admission_receipt_binding",
            "receipt_binding",
        ),
        ("replay_target", "official_seed_inventory_binding"),
        (
            "replay_target",
            "execution_source_runtime_closure_binding",
            "receipt_binding",
        ),
        ("full_design_freeze", "replay_target_binding"),
        ("launch_intent", "replay_target_binding"),
        ("launch_intent", "full_design_freeze_binding"),
        ("launch_intent", "execution_identity_binding"),
        ("launch_intent", "physical_identity_binding"),
        (
            "exclusive_seed_supply_claim",
            "development_exclusion_registry_binding",
        ),
        (
            "exclusive_seed_supply_claim",
            "parent_selection_exclusion_registry_binding",
        ),
        (
            "exclusive_seed_supply_claim",
            "seed_free_readiness_binding",
        ),
        (
            "exclusive_seed_supply_claim",
            "admission_receipt_binding",
        ),
        (
            "exclusive_seed_supply_claim",
            "source_runtime_receipt_binding",
        ),
        ("single_supplier_invocation", "claim_binding"),
        ("single_supplier_invocation", "supplier_identity_binding"),
        (
            "single_supplier_invocation",
            "official_seed_inventory_binding",
        ),
    ),
)
def test_nested_record_joins_reject_digest_and_byte_count_substitution(
    path: tuple[str, ...],
) -> None:
    for leaf in ("canonical_sha256", "byte_count"):
        document = copy.deepcopy(_bundle().to_dict())
        cursor: object = document
        for part in path:
            cursor = cursor[part]  # type: ignore[index]
        if leaf == "canonical_sha256":
            cursor[leaf] = "e" * 64  # type: ignore[index]
        else:
            cursor[leaf] += 1  # type: ignore[index,operator]
        with pytest.raises(authority.D7AuthorityInputError):
            _load_document(document)


def test_official_seed_inventory_is_ordered_int64_and_disjoint() -> None:
    seeds = _bundle().official_seed_inventory.seeds
    values = tuple(item.seed for item in seeds)

    assert len(seeds) == 2
    assert tuple(item.seed_slot_id for item in seeds) == (
        authority.D7_CONFIRMATION_SEED_SLOT_IDS
    )
    assert all(type(value) is int and 0 <= value < (1 << 63) for value in values)
    assert values == tuple(sorted(set(values)))
    assert set(values).isdisjoint({11, 12, 9001, 9002})
    assert set(values).isdisjoint(authority.D7_PARENT_SELECTION_SEEDS)


def test_seed_inventory_rejects_wrong_count_order_and_int64() -> None:
    document = copy.deepcopy(_bundle().to_dict())
    document["official_seed_inventory"]["seeds"].pop()  # type: ignore[index,union-attr]
    with pytest.raises(authority.D7AuthorityInputError, match="exactly two"):
        _load_document(document)

    document = copy.deepcopy(_bundle().to_dict())
    seeds = document["official_seed_inventory"]["seeds"]  # type: ignore[index]
    seeds[0]["seed"], seeds[1]["seed"] = seeds[1]["seed"], seeds[0]["seed"]  # type: ignore[index]
    with pytest.raises(authority.D7AuthorityInputError, match="sorted"):
        _load_document(document)

    document = copy.deepcopy(_bundle().to_dict())
    document["official_seed_inventory"]["seeds"][1]["seed"] = 1 << 63  # type: ignore[index]
    with pytest.raises(authority.D7AuthorityInputError, match="plain integer"):
        _load_document(document)

    document = copy.deepcopy(_bundle().to_dict())
    document["official_seed_inventory"]["seeds"][0]["seed"] = True  # type: ignore[index]
    with pytest.raises(authority.D7AuthorityInputError, match="plain integer"):
        _load_document(document)

    document = copy.deepcopy(_bundle().to_dict())
    document["official_seed_inventory"]["seeds"][1]["seed"] = (  # type: ignore[index]
        authority.D7_PARENT_SELECTION_SEEDS[0]
    )
    with pytest.raises(
        authority.D7AuthorityInputError,
        match="overlap development or parent",
    ):
        _load_document(document)


def test_seed_inventory_persists_external_unseen_and_unfrozen_nonclaims() -> None:
    inventory = _bundle().official_seed_inventory.to_dict()

    assert inventory["unseen_status"] == "external-attestation-required"
    assert inventory["seed_inventory_frozen"] is False
    assert inventory["supplier_chronology_verified"] is False
    assert inventory["cryptographic_unseen_proof"] is False


def test_chronology_requires_all_transitions_and_exact_predecessors() -> None:
    bundle = _bundle()
    assert tuple(record.transition for record in bundle.chronology) == (
        authority.D7_SEED_SUPPLY_TRANSITION_ORDER
    )

    document = copy.deepcopy(bundle.to_dict())
    document["chronology"].pop(5)  # type: ignore[union-attr]
    with pytest.raises(authority.D7AuthorityInputError):
        _load_document(document)

    document = copy.deepcopy(bundle.to_dict())
    document["chronology"][4]["predecessor_binding"]["canonical_sha256"] = (  # type: ignore[index]
        "e" * 64
    )
    with pytest.raises(authority.D7AuthorityInputError, match="predecessor"):
        _load_document(document)

    document = copy.deepcopy(bundle.to_dict())
    document["chronology"][6]["subject_bindings"][2]["canonical_sha256"] = (  # type: ignore[index]
        "e" * 64
    )
    with pytest.raises(
        authority.D7AuthorityInputError,
        match="predecessor|replay target",
    ):
        _load_document(document)


def test_every_chronology_subject_rejects_omission_and_substitution() -> None:
    for index in range(len(authority.D7_SEED_SUPPLY_TRANSITION_ORDER)):
        omitted = copy.deepcopy(_bundle().to_dict())
        omitted["chronology"][index]["subject_bindings"].pop()  # type: ignore[index,union-attr]
        with pytest.raises(authority.D7AuthorityInputError):
            _load_document(omitted)

        substituted = copy.deepcopy(_bundle().to_dict())
        substituted["chronology"][index]["subject_bindings"][0][  # type: ignore[index]
            "canonical_sha256"
        ] = "e" * 64
        with pytest.raises(authority.D7AuthorityInputError):
            _load_document(substituted)


def test_every_chronology_predecessor_rejects_omission_and_substitution() -> None:
    first_substituted = copy.deepcopy(_bundle().to_dict())
    first_substituted["chronology"][0]["predecessor_binding"] = (  # type: ignore[index]
        first_substituted["chronology"][0]["subject_bindings"][0]  # type: ignore[index]
    )
    with pytest.raises(authority.D7AuthorityInputError, match="predecessor"):
        _load_document(first_substituted)

    for index in range(1, len(authority.D7_SEED_SUPPLY_TRANSITION_ORDER)):
        omitted = copy.deepcopy(_bundle().to_dict())
        omitted["chronology"][index]["predecessor_binding"] = None  # type: ignore[index]
        with pytest.raises(authority.D7AuthorityInputError, match="predecessor"):
            _load_document(omitted)

        substituted = copy.deepcopy(_bundle().to_dict())
        substituted["chronology"][index]["predecessor_binding"][  # type: ignore[index]
            "canonical_sha256"
        ] = "e" * 64
        with pytest.raises(authority.D7AuthorityInputError, match="predecessor"):
            _load_document(substituted)


@pytest.mark.parametrize(
    ("path", "match"),
    (
        (
            (
                "single_supplier_invocation",
                "supplier_identity_binding",
                "canonical_sha256",
            ),
            "supplier|identity",
        ),
        (
            (
                "single_supplier_invocation",
                "official_seed_inventory_binding",
                "canonical_sha256",
            ),
            "inventory",
        ),
        (
            (
                "chronology",
                6,
                "subject_bindings",
                0,
                "canonical_sha256",
            ),
            "inventory|predecessor|publication",
        ),
    ),
)
def test_supplier_and_publication_inventory_substitutions_fail_closed(
    path: tuple[object, ...],
    match: str,
) -> None:
    document = copy.deepcopy(_bundle().to_dict())
    cursor: object = document
    for part in path[:-1]:
        cursor = cursor[part]  # type: ignore[index]
    cursor[path[-1]] = "e" * 64  # type: ignore[index]

    with pytest.raises(authority.D7AuthorityInputError, match=match):
        _load_document(document)


def test_freeze_and_launch_commit_and_design_joins_fail_closed() -> None:
    document = copy.deepcopy(_bundle().to_dict())
    document["full_design_freeze"]["authorization_commit"] = "b" * 40  # type: ignore[index]
    with pytest.raises(authority.D7AuthorityInputError, match="must differ"):
        _load_document(document)

    document = copy.deepcopy(_bundle().to_dict())
    document["launch_intent"]["freeze_commit"] = "d" * 40  # type: ignore[index]
    with pytest.raises(authority.D7AuthorityInputError, match="commit"):
        _load_document(document)

    document = copy.deepcopy(_bundle().to_dict())
    document["full_design_freeze"]["full_design_binding"]["canonical_sha256"] = (  # type: ignore[index]
        "e" * 64
    )
    with pytest.raises(authority.D7AuthorityInputError, match="full-design"):
        _load_document(document)


def test_physical_contract_allows_nested_lane_and_shared_parent() -> None:
    physical = _bundle().physical_store_lane_identity
    serialized = physical.to_dict()
    assert physical.lane_path.startswith(f"{physical.store_path}/")
    assert serialized["lane_device"] == physical.lane_device
    assert serialized["lane_inode"] == physical.lane_inode
    assert serialized["lane_identity_sha256"] == physical.lane_identity_sha256
    assert authority.D7PhysicalStoreLaneIdentityRecord.from_dict(serialized) == physical
    assert physical.output_parent_inode == physical.terminal_parent_inode
    assert (
        physical.output_subject_identity_sha256
        != physical.terminal_subject_identity_sha256
    )


@pytest.mark.parametrize(
    ("field", "value", "match"),
    (
        (
            "lane_path",
            "/var/tmp/spirallens-d7/wrong-lane",
            "exact evidence-only child",
        ),
        (
            "terminal_path",
            "/var/tmp/spirallens-d7/output/terminal",
            "paths overlap",
        ),
        (
            "terminal_path",
            "/var/tmp/spirallens-d7/output",
            "paths overlap",
        ),
        (
            "output_namespace_path",
            "/var/tmp/spirallens-d7/terminal/output",
            "paths overlap",
        ),
        (
            "output_namespace_path",
            "/outside/output",
            "inside the store",
        ),
    ),
)
def test_physical_path_shape_rejects_wrong_containment(
    field: str,
    value: str,
    match: str,
) -> None:
    document = copy.deepcopy(_bundle().physical_store_lane_identity.to_dict())
    document[field] = value
    with pytest.raises(authority.D7AuthorityInputError, match=match):
        authority.D7PhysicalStoreLaneIdentityRecord.from_dict(document)


def test_physical_alias_collision_rejects_same_leaf_key() -> None:
    document = copy.deepcopy(_bundle().physical_store_lane_identity.to_dict())
    document["output_namespace_path"] = "/var/tmp/spirallens-d7/output-parent/collision"
    document["terminal_path"] = "/var/tmp/spirallens-d7/terminal-parent/collision"
    document["output_parent_device"] = 901
    document["output_parent_inode"] = 902
    document["terminal_parent_device"] = 901
    document["terminal_parent_inode"] = 902
    for key in (
        "output_subject_identity_sha256",
        "terminal_subject_identity_sha256",
    ):
        document[key] = "0" * 64
    with pytest.raises(
        authority.D7AuthorityInputError,
        match="same physical subject key",
    ):
        authority.D7PhysicalStoreLaneIdentityRecord.from_dict(document)


def test_lane_parent_coordinates_must_equal_the_store() -> None:
    document = copy.deepcopy(_bundle().physical_store_lane_identity.to_dict())
    document["lane_parent_inode"] = 999
    with pytest.raises(
        authority.D7AuthorityInputError,
        match="coordinates must equal the store",
    ):
        authority.D7PhysicalStoreLaneIdentityRecord.from_dict(document)


def test_lane_identity_digest_rejects_coordinate_substitution() -> None:
    document = copy.deepcopy(_bundle().physical_store_lane_identity.to_dict())
    document["lane_device"] += 1
    with pytest.raises(
        authority.D7AuthorityInputError,
        match="lane_identity_sha256",
    ):
        authority.D7PhysicalStoreLaneIdentityRecord.from_dict(document)


def test_output_cannot_be_nested_under_the_reserved_evidence_lane() -> None:
    physical = _bundle().physical_store_lane_identity
    with pytest.raises(
        authority.D7AuthorityInputError,
        match="reserved|evidence lane",
    ):
        replace(
            physical,
            output_namespace_path=f"{physical.lane_path}/output",
        )


@pytest.mark.parametrize(
    "subject",
    (
        "/var/tmp/spirallens-d7/d7-prefix-evidence-only-v0/output",
        "/var/tmp/spirallens-d7/d7-attempt-evidence/output",
        ("/var/tmp/spirallens-d7/" + "8" * 64 + ".attempt-declaration.envelope.json"),
        ("/var/tmp/spirallens-d7/" + "9" * 64 + ".attempt-claim.json"),
    ),
)
def test_output_cannot_overlap_any_persistence_reserved_path(
    subject: str,
) -> None:
    with pytest.raises(authority.D7AuthorityInputError, match="reserved"):
        replace(
            _bundle().physical_store_lane_identity,
            output_namespace_path=subject,
        )


@pytest.mark.parametrize(
    "store_path",
    (
        "//var/tmp/spirallens-d7",
        "/var/tmp/bad\x00store",
        "/" + "a" * (authority.MAX_D7_DECLARED_PATH_BYTES + 1),
    ),
)
def test_physical_identity_rejects_unopenable_or_aliased_paths(
    store_path: str,
) -> None:
    with pytest.raises(
        authority.D7AuthorityInputError,
        match="alias|NUL|overlong",
    ):
        replace(
            _bundle().physical_store_lane_identity,
            store_path=store_path,
        )


@pytest.mark.parametrize(
    "changes",
    (
        {"store_inode": 0, "lane_parent_inode": 0},
        {"lane_inode": 0},
        {"lane_parent_inode": 0},
        {"output_parent_inode": 0},
        {"terminal_parent_inode": 0},
    ),
)
def test_physical_identity_rejects_zero_inodes(
    changes: dict[str, int],
) -> None:
    with pytest.raises(authority.D7AuthorityInputError, match="positive|inode"):
        replace(_bundle().physical_store_lane_identity, **changes)


def test_loaded_candidate_persists_every_authority_nonclaim() -> None:
    bundle = _bundle()
    loaded = authority.load_d7_launch_authority_structural_candidate(
        bundle.canonical_bytes,
        expected_sha256=bundle.canonical_sha256,
    )
    false_claims = (
        "authority_authenticated",
        "target_authoritative",
        "source_runtime_verified",
        "family_admission_verified",
        "seed_free_readiness_verified",
        "official_seed_chronology_verified",
        "seed_supply_claim_verified",
        "supplier_invocation_verified",
        "inventory_output_verified",
        "atomic_publication_verified",
        "full_design_freeze_verified",
        "launch_intent_verified",
        "physical_identity_reobserved",
        "path_absence_observed",
        "alternate_store_exclusivity_proved",
        "hostile_mutation_resistant",
        "exclusive_start_authorized",
        "launch_authorization_derived",
        "authoritative_lifecycle_eligible",
        "in_place_promotion_allowed",
        "terminal_publication_authorized",
        "finalization_authorized",
        "unresolved_finalization_authorized",
        "isolated_replay_authorized",
        "d7_execution_authorized",
        "d8_execution_authorized",
        "d7_result_produced",
        "execution_observed",
        "scientific_claim_eligible",
    )
    assert all(getattr(loaded, name) is False for name in false_claims)
    assert {value for value in vars(type(loaded)).values() if type(value) is bool} == {
        False
    }


def test_loader_performs_no_filesystem_access_or_callback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signature = inspect.signature(
        authority.load_d7_launch_authority_structural_candidate
    )
    assert tuple(signature.parameters) == ("source", "expected_sha256")
    assert signature.parameters["source"].kind is (
        inspect.Parameter.POSITIONAL_OR_KEYWORD
    )
    assert signature.parameters["expected_sha256"].kind is (
        inspect.Parameter.KEYWORD_ONLY
    )
    assert all(
        "callback" not in name and "writer" not in name and "runner" not in name
        for name in signature.parameters
    )

    def _forbidden_open(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("loader attempted filesystem access")

    monkeypatch.setattr(builtins, "open", _forbidden_open)
    bundle = _bundle()
    authority.load_d7_launch_authority_structural_candidate(
        bundle.canonical_bytes,
        expected_sha256=bundle.canonical_sha256,
    )


def test_module_is_deep_internal_and_mints_no_operational_surface() -> None:
    assert authority.__all__ == ()
    assert not hasattr(authority.D7AuthorityArtifactBinding, "from_bytes")
    forbidden_fragments = ("capability", "writer", "runner", "finalizer")
    local_classes = {
        name: value
        for name, value in vars(authority).items()
        if not name.startswith("_")
        and inspect.isclass(value)
        and value.__module__ == authority.__name__
    }
    public_names = {
        name
        for name, value in vars(authority).items()
        if not name.startswith("_")
        and (
            value in local_classes.values()
            or (inspect.isfunction(value) and value.__module__ == authority.__name__)
        )
    }
    operational_names = {name.lower() for name in public_names}
    operational_names.update(
        member_name.lower()
        for value in local_classes.values()
        for member_name in vars(value)
        if not member_name.startswith("_")
    )
    assert all(
        fragment not in name
        for name in operational_names
        for fragment in forbidden_fragments
    )
    import spirallens
    import spirallens.qualification as qualification

    for name in public_names:
        assert not hasattr(spirallens, name)
        assert not hasattr(qualification, name)
