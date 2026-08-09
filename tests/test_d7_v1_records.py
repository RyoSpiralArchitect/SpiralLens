from __future__ import annotations

import ast
from pathlib import Path

import pytest

from spirallens.core.canonical import canonical_json_bytes, sha256_bytes
from spirallens.qualification import confirmation_v1_records as records
from spirallens.qualification.common import QualificationContractError


MODULE_PATH = Path("src/spirallens/qualification/confirmation_v1_records.py")
ZERO_SHA = "0" * 64
ONE_SHA = "1" * 64
COMMIT_A = "a" * 40


def _external(
    role: str,
    digit: str | None = None,
) -> records.D7V1ArtifactBinding:
    return records.D7V1ArtifactBinding(
        artifact_role=role,
        artifact_contract_id=f"spirallens.test-{role}.v0.1",
        canonical_sha256=(
            sha256_bytes(role.encode("utf-8")) if digit is None else digit * 64
        ),
        byte_count=17,
    )


def _bound(record: object) -> records.D7V1ArtifactBinding:
    assert isinstance(record, records._D7V1CanonicalRecord)
    return records.D7V1ArtifactBinding.from_record(record)


def _chain() -> dict[str, object]:
    c1 = records.D7V1C1SourceSetRecord.create(
        record_id="d7-v1-c1",
        repository_path=(
            "experiments/qualification/d7_spectral_moment_confirmation_v1/"
            "c1-seed-free-source-set.json"
        ),
        route_binding=_external("navigation-route", "1"),
        source_members=(
            records.D7V1SourceMember("pyproject.toml", "100644", "2" * 64, 17),
            records.D7V1SourceMember(
                "src/spirallens/qualification/confirmation_v1_records.py",
                "100644",
                "3" * 64,
                101,
            ),
        ),
    )
    c2 = records.D7V1C2SourceClosureReceipt.create(
        record_id="d7-v1-c2",
        repository_path=(
            "experiments/qualification/d7_spectral_moment_confirmation_v1/"
            "c2-source-closure-receipt.json"
        ),
        c1=c1,
        source_commit=COMMIT_A,
    )
    supplier_identity = _external("supplier-identity", "5")
    claim = records.D7V1ExclusiveSeedSupplyClaim.create(
        record_id="d7-v1-seed-claim",
        repository_path=(
            "experiments/qualification/d7_spectral_moment_confirmation_v1/"
            "seed-supply/exclusive-seed-supply-claim.json"
        ),
        c2=c2,
        supplier_identity_binding=supplier_identity,
        supplier_id="honest-local-csprng",
        external_claim_path=(
            "/Users/test/SpiralReality/spirallens-d7-v1-store/"
            "d7-v1-prefix-evidence-only/exclusive-seed-supply-claim.json"
        ),
    )
    inventory = records.D7V1OfficialSeedInventory.create(
        record_id="d7-v1-seed-inventory",
        repository_path=(
            "experiments/qualification/d7_spectral_moment_confirmation_v1/"
            "seed-supply/published-target/official-seed-inventory.json"
        ),
        claim=claim,
        supplier_identity_binding=supplier_identity,
        supplier_id="honest-local-csprng",
        seeds=(8_100_001, 8_100_002),
        predecessor_inventory_binding=_external(
            "historical-predecessor-seed-inventory", "6"
        ),
        predecessor_seed_values=(8_001_001, 8_001_002),
    )
    full_design = records.D7V1EmbeddedFullDesign.create(
        design_id="d7-v1-spectral-moment-official-full-design",
        family_binding=_external("confirmation-family", "7"),
        admission_binding=_external("family-admission", "8"),
        protocol_binding=_external("confirmation-protocol", "9"),
        source_graph_binding=_external("source-graph", "a"),
        inventory_binding=_bound(inventory),
        graph_case_stress_aggregation_binding=_external(
            "graph-case-stress-aggregation", "b"
        ),
        lifecycle_binding=_external("lifecycle", "a"),
    )
    transitive = {
        key: (
            _bound(c1)
            if role == records.D7V1C1SourceSetRecord.artifact_role
            else _bound(c2)
            if role == records.D7V1C2SourceClosureReceipt.artifact_role
            else _bound(claim)
            if role == records.D7V1ExclusiveSeedSupplyClaim.artifact_role
            else _bound(inventory)
            if role == records.D7V1OfficialSeedInventory.artifact_role
            else _external(role, "d")
        )
        for key, role in records._REPLAY_TRANSITIVE_ROLES.items()
        if key != "embedded_full_design_binding"
    }
    replay = records.D7V1ReplayTarget.create(
        record_id="d7-v1-replay-target",
        repository_path=(
            "experiments/qualification/d7_spectral_moment_confirmation_v1/"
            "seed-supply/published-target/replay-target.json"
        ),
        official_seed_inventory_binding=_bound(inventory),
        full_design=full_design,
        transitive_bindings=transitive,
    )
    replay_document = replay.to_dict()
    design_pointer = records.D7V1JsonPointerBinding.from_dict(
        replay_document["full_design_binding"]
    )
    freeze = records.D7V1FullDesignFreeze.create(
        record_id="d7-v1-full-design-freeze",
        repository_path=(
            "experiments/qualification/d7_spectral_moment_confirmation_v1/"
            "seed-supply/full-design-freeze.json"
        ),
        replay_target_binding=_bound(replay),
        full_design_binding=design_pointer,
        reviewed_source_commit=COMMIT_A,
    )
    launch = records.D7V1LaunchIntent.create(
        record_id="d7-v1-launch-intent",
        repository_path=(
            "experiments/qualification/d7_spectral_moment_confirmation_v1/"
            "launch-members/launch-intent.json"
        ),
        replay_target_binding=_bound(replay),
        full_design_freeze_binding=_bound(freeze),
        external_store_path="/Users/test/SpiralReality/spirallens-d7-v1-store",
        external_staging_path=(
            "/Users/test/SpiralReality/.spirallens-d7-v1-store.staging"
        ),
        runner_script="scripts/run_d7_v1.py",
        official_callable=(
            "spirallens.qualification.confirmation_v1_official_execution:"
            "produce_d7_v1_official_result"
        ),
    )
    attempt = records.D7V1OfficialExecutionAttemptReservation.create(
        record_id="d7-v1-attempt-reservation",
        repository_path=(
            "experiments/qualification/d7_spectral_moment_confirmation_v1/"
            "pre-item23/official-execution-attempt-envelope.json"
        ),
        launch_intent=launch,
        replay_target=replay,
        seed_claim=claim,
        external_attempt_path=(
            "/Users/test/SpiralReality/spirallens-d7-v1-store/"
            "d7-v1-attempt-evidence/official-execution-attempt-reservation.json"
        ),
        external_store_path="/Users/test/SpiralReality/spirallens-d7-v1-store",
        reviewed_source_commit=COMMIT_A,
    )
    root = "experiments/qualification/d7_spectral_moment_confirmation_v1"
    inventory_paths = {
        records.D7V1C1SourceSetRecord.artifact_role: (
            f"{root}/c1-seed-free-source-set.json"
        ),
        records.D7V1C2SourceClosureReceipt.artifact_role: (
            f"{root}/c2-source-closure-receipt.json"
        ),
        records.D7V1ExclusiveSeedSupplyClaim.artifact_role: (
            f"{root}/seed-supply/exclusive-seed-supply-claim.json"
        ),
        records.D7V1OfficialSeedInventory.artifact_role: (
            f"{root}/seed-supply/published-target/official-seed-inventory.json"
        ),
        records.D7V1ReplayTarget.artifact_role: (
            f"{root}/seed-supply/published-target/replay-target.json"
        ),
        records.D7V1FullDesignFreeze.artifact_role: (
            f"{root}/seed-supply/full-design-freeze.json"
        ),
        records.D7V1LaunchIntent.artifact_role: (
            f"{root}/launch-members/launch-intent.json"
        ),
        records.D7V1OfficialExecutionAttemptReservation.artifact_role: (
            f"{root}/pre-item23/official-execution-attempt-envelope.json"
        ),
        records.D7V1PreItem23ChronologyReceipt.artifact_role: (
            f"{root}/pre-item23-chronology-receipt.json"
        ),
    }
    absence = records.D7V1NamespaceAbsenceObservation(
        repository_path=f"{root}/post-d6-descriptive-analysis-result.json",
        observed_at_reviewed_source_commit=COMMIT_A,
    )
    receipt = records.D7V1PreItem23ChronologyReceipt.create(
        record_id="d7-v1-pre-item23-receipt",
        repository_path=inventory_paths[
            records.D7V1PreItem23ChronologyReceipt.artifact_role
        ],
        predecessor_bindings={
            records.D7V1C1SourceSetRecord.artifact_role: _bound(c1),
            records.D7V1C2SourceClosureReceipt.artifact_role: _bound(c2),
            records.D7V1ExclusiveSeedSupplyClaim.artifact_role: _bound(claim),
            records.D7V1OfficialSeedInventory.artifact_role: _bound(inventory),
            records.D7V1ReplayTarget.artifact_role: _bound(replay),
            records.D7V1FullDesignFreeze.artifact_role: _bound(freeze),
            records.D7V1LaunchIntent.artifact_role: _bound(launch),
            records.D7V1OfficialExecutionAttemptReservation.artifact_role: (
                _bound(attempt)
            ),
        },
        pre_item23_file_inventory=inventory_paths,
        descriptive_result_namespace_absence=absence,
    )
    result = records.D7V1PostselectionDescriptiveResult.create(
        record_id="d7-v1-postselection-result",
        repository_path=f"{root}/post-d6-descriptive-analysis-result.json",
        parent_binding=_bound(attempt),
        chronology_receipt_binding=_bound(receipt),
        read_trace=tuple(
            records.D7V1ReadTraceEntry(index, _external(role))
            for index, role in enumerate(records._DESCRIPTIVE_READ_TRACE_ROLES, start=1)
        ),
        status="complete",
        outputs=tuple(
            records.D7V1DescriptiveOutput.create(
                output_id=output_id,
                status=(
                    "blocked"
                    if output_id == "amplitude-identifiability-support-separation"
                    else "available"
                ),
                data={"sequence": index, "rows": []},
            )
            for index, output_id in enumerate(records._POST_D6_OUTPUT_IDS, start=1)
        ),
    )
    return {
        "c1": c1,
        "c2": c2,
        "claim": claim,
        "inventory": inventory,
        "full_design": full_design,
        "replay": replay,
        "freeze": freeze,
        "launch": launch,
        "attempt": attempt,
        "receipt": receipt,
        "result": result,
    }


def test_exact_eleven_roles_round_trip_with_no_authority() -> None:
    chain = _chain()
    assert len(chain) == 11
    expected_types = {
        records.D7V1C1SourceSetRecord,
        records.D7V1C2SourceClosureReceipt,
        records.D7V1ExclusiveSeedSupplyClaim,
        records.D7V1OfficialSeedInventory,
        records.D7V1EmbeddedFullDesign,
        records.D7V1ReplayTarget,
        records.D7V1FullDesignFreeze,
        records.D7V1LaunchIntent,
        records.D7V1OfficialExecutionAttemptReservation,
        records.D7V1PreItem23ChronologyReceipt,
        records.D7V1PostselectionDescriptiveResult,
    }
    assert {type(record) for record in chain.values()} == expected_types
    for record in chain.values():
        assert isinstance(
            record,
            (records._D7V1CanonicalRecord, records.D7V1EmbeddedFullDesign),
        )
        loaded = type(record).from_canonical_bytes(
            record.canonical_bytes,
            expected_sha256=record.canonical_sha256,
        )
        assert loaded.canonical_bytes == record.canonical_bytes
        assert loaded.to_dict() == record.to_dict()
        assert loaded.to_dict()["claim_boundary"] == records._CLAIM_BOUNDARY


def test_records_are_factory_only_immutable_and_return_detached_documents() -> None:
    c1 = _chain()["c1"]
    assert isinstance(c1, records.D7V1C1SourceSetRecord)
    with pytest.raises(TypeError, match="validated factory"):
        records.D7V1C1SourceSetRecord(b"{}", _factory_token=object())
    with pytest.raises(AttributeError, match="immutable"):
        c1.extra = True  # type: ignore[attr-defined]
    detached = c1.to_dict()
    detached["artifact_role"] = "mutated"
    assert c1.to_dict()["artifact_role"] == "c1-seed-free-source-set"


def test_loader_checks_digest_before_attempting_parse() -> None:
    with pytest.raises(QualificationContractError, match="digest differs before parse"):
        records.D7V1C1SourceSetRecord.from_canonical_bytes(
            b"{",
            expected_sha256=ZERO_SHA,
        )
    invalid = b"{"
    with pytest.raises(QualificationContractError, match="invalid JSON"):
        records.D7V1C1SourceSetRecord.from_canonical_bytes(
            invalid,
            expected_sha256=sha256_bytes(invalid),
        )


def test_unknown_root_and_nested_keys_fail_closed() -> None:
    c1 = _chain()["c1"]
    assert isinstance(c1, records.D7V1C1SourceSetRecord)
    root = c1.to_dict()
    root["surprise"] = False
    with pytest.raises(QualificationContractError, match="fields differ"):
        records.D7V1C1SourceSetRecord.from_dict(root)
    nested = c1.to_dict()
    nested["payload"]["surprise"] = False  # type: ignore[index]
    with pytest.raises(QualificationContractError, match="fields differ"):
        records.D7V1C1SourceSetRecord.from_dict(nested)
    boundary = c1.to_dict()
    boundary["claim_boundary"]["d7_execution_authorized"] = True  # type: ignore[index]
    with pytest.raises(QualificationContractError, match="no-authority"):
        records.D7V1C1SourceSetRecord.from_dict(boundary)


def test_seed_claim_precedes_supplier_and_inventory_is_honest_but_not_proven() -> None:
    chain = _chain()
    claim = chain["claim"].to_dict()  # type: ignore[union-attr]
    assert claim["typestate"] == {
        "claim_persisted": True,
        "supplier_entered": False,
        "seed_values_present": False,
    }
    assert claim["payload"]["supplier_identity_binding"]["artifact_role"] == (  # type: ignore[index]
        "supplier-identity"
    )
    inventory = chain["inventory"].to_dict()  # type: ignore[union-attr]
    assert inventory["payload"]["observations"] == {  # type: ignore[index]
        "supplier_invocation_observed": True,
        "supplier_invocation_count_claimed": 1,
        "independent_single_invocation_proof": False,
    }
    payload = inventory["payload"]
    payload["seeds"] = [8_001_001]  # type: ignore[index]
    with pytest.raises(QualificationContractError, match="overlap"):
        records.D7V1OfficialSeedInventory.from_dict(inventory)
    empty_predecessor = chain["inventory"].to_dict()  # type: ignore[union-attr]
    empty_predecessor["payload"]["predecessor_seed_values"] = []  # type: ignore[index]
    with pytest.raises(QualificationContractError, match="non-empty"):
        records.D7V1OfficialSeedInventory.from_dict(empty_predecessor)


def test_c1_embeds_a_recomputable_sorted_source_inventory_and_allows_empty_files() -> (
    None
):
    empty = records.D7V1SourceMember(
        repository_path="src/spirallens/empty.py",
        git_mode="100644",
        sha256=ZERO_SHA,
        byte_count=0,
    )
    assert empty.byte_count == 0
    with pytest.raises(QualificationContractError, match="at least 0"):
        records.D7V1SourceMember(
            repository_path="src/spirallens/invalid.py",
            git_mode="100644",
            sha256=ZERO_SHA,
            byte_count=-1,
        )
    c1 = _chain()["c1"]
    assert isinstance(c1, records.D7V1C1SourceSetRecord)
    payload = c1.to_dict()["payload"]
    paths = [member["repository_path"] for member in payload["source_members"]]  # type: ignore[index]
    assert paths == sorted(paths)
    tampered = c1.to_dict()
    tampered["payload"]["source_members"][0]["byte_count"] += 1  # type: ignore[index,operator]
    with pytest.raises(QualificationContractError, match="does not bind"):
        records.D7V1C1SourceSetRecord.from_dict(tampered)
    c2 = _chain()["c2"]
    c2_document = c2.to_dict()  # type: ignore[union-attr]
    assert c2_document["typestate"]["source_tree_authenticated"] is False  # type: ignore[index]
    c2_document["payload"]["source_tree_derivation"][  # type: ignore[index]
        "merged_source_commit"
    ] = "b" * 40
    with pytest.raises(QualificationContractError, match="derivation differs"):
        records.D7V1C2SourceClosureReceipt.from_dict(c2_document)


def test_internal_role_bindings_reject_schema_substitution_and_role_override() -> None:
    c2 = _chain()["c2"]
    assert isinstance(c2, records.D7V1C2SourceClosureReceipt)
    document = c2.to_dict()
    document["payload"]["c1_binding"]["artifact_contract_id"] = (  # type: ignore[index]
        "spirallens.fake-c1.v0.1"
    )
    with pytest.raises(QualificationContractError, match="C1 binding schema"):
        records.D7V1C2SourceClosureReceipt.from_dict(document)
    c1 = _chain()["c1"]
    with pytest.raises(TypeError, match="unexpected keyword"):
        records.D7V1ArtifactBinding.from_record(  # type: ignore[call-arg]
            c1, artifact_role="replay-target"
        )


def test_replay_target_binds_real_full_design_and_inventory_pointers() -> None:
    replay = _chain()["replay"]
    assert isinstance(replay, records.D7V1ReplayTarget)
    document = replay.to_dict()
    assert "full_design" in document
    assert "inventory" in document["full_design"]  # type: ignore[operator]
    design_binding = document["full_design_binding"]
    inventory_binding = document["full_design_inventory_binding"]
    assert design_binding["json_pointer"] == "/full_design"  # type: ignore[index]
    assert inventory_binding["json_pointer"] == "/full_design/inventory"  # type: ignore[index]
    assert len(document["transitive_bindings"]) == 13  # type: ignore[arg-type]
    tampered = replay.to_dict()
    tampered["full_design_binding"]["byte_count"] += 1  # type: ignore[index,operator]
    with pytest.raises(QualificationContractError, match="exact subdocument"):
        records.D7V1ReplayTarget.from_dict(tampered)
    transitive_tamper = replay.to_dict()
    transitive_tamper["transitive_bindings"]["embedded_full_design_binding"][  # type: ignore[index]
        "canonical_sha256"
    ] = ZERO_SHA
    with pytest.raises(QualificationContractError, match="transitive design differs"):
        records.D7V1ReplayTarget.from_dict(transitive_tamper)


def test_attempt_is_exclusive_reservation_not_a_started_or_retryable_claim() -> None:
    attempt = _chain()["attempt"].to_dict()  # type: ignore[union-attr]
    assert attempt["typestate"] == {
        "attempt_state": "reserved_not_started",
        "execution_started": False,
        "retry": False,
        "exclusive_no_replace": True,
    }
    attempt["typestate"]["retry"] = True  # type: ignore[index]
    with pytest.raises(QualificationContractError, match="typestate differs"):
        records.D7V1OfficialExecutionAttemptReservation.from_dict(attempt)
    derived = _chain()["attempt"].to_dict()  # type: ignore[union-attr]
    derived["payload"]["attempt_key_derivation"]["domain"] = "bad"  # type: ignore[index]
    with pytest.raises(QualificationContractError, match="domain differs"):
        records.D7V1OfficialExecutionAttemptReservation.from_dict(derived)


def test_receipt_has_eight_predecessor_digests_nine_paths_and_no_self_hash() -> None:
    receipt = _chain()["receipt"]
    assert isinstance(receipt, records.D7V1PreItem23ChronologyReceipt)
    payload = receipt.to_dict()["payload"]
    predecessor_files = payload["predecessor_files"]  # type: ignore[index]
    assert len(predecessor_files) == 8
    assert records.D7V1PreItem23ChronologyReceipt.artifact_role not in predecessor_files
    inventory = payload["pre_item23_file_inventory"]  # type: ignore[index]
    assert set(inventory) == set(records._PRE_ITEM23_FILE_ROLES)
    assert len(inventory) == 9
    for role, joined in predecessor_files.items():
        assert joined["repository_path"] == inventory[role]
        assert joined["artifact_binding"]["artifact_role"] == role
    assert receipt.to_dict()["typestate"]["artifact_commit_authenticated"] is False  # type: ignore[index]
    tampered = receipt.to_dict()
    role = records.D7V1C1SourceSetRecord.artifact_role
    tampered["payload"]["predecessor_files"][role]["repository_path"] = (  # type: ignore[index]
        "different/c1.json"
    )
    with pytest.raises(QualificationContractError, match="path differs"):
        records.D7V1PreItem23ChronologyReceipt.from_dict(tampered)
    assert (
        payload["descriptive_result_namespace_absence"]["path_absent"] is True  # type: ignore[index]
    )


def test_result_embeds_and_binds_closed_outputs() -> None:
    result = _chain()["result"]
    assert isinstance(result, records.D7V1PostselectionDescriptiveResult)
    payload = result.to_dict()["payload"]
    assert set(payload) == {  # type: ignore[arg-type]
        "repository_path",
        "parent_binding",
        "chronology_receipt_binding",
        "read_trace",
        "status",
        "outputs",
        "output_bindings",
        "observations",
    }
    invalid = result.to_dict()
    invalid["payload"]["status"] = "positive"  # type: ignore[index]
    with pytest.raises(QualificationContractError, match="status is not closed"):
        records.D7V1PostselectionDescriptiveResult.from_dict(invalid)
    assert len(payload["read_trace"]) == 6  # type: ignore[arg-type,index]
    assert len(payload["outputs"]) == 27  # type: ignore[arg-type,index]
    assert len(payload["output_bindings"]) == 27  # type: ignore[arg-type,index]
    first_output = records._POST_D6_OUTPUT_IDS[0]
    assert payload["output_bindings"][first_output]["json_pointer"] == (  # type: ignore[index]
        f"/payload/outputs/{first_output}"
    )
    assert payload["observations"] == {  # type: ignore[index]
        "read_trace_recorded": True,
        "any_input_read": True,
        "status_recorded": True,
    }
    embedded = records.D7V1DescriptiveOutput.from_dict(
        payload["outputs"][first_output]  # type: ignore[index]
    )
    assert embedded.to_dict()["claim_boundary"] == records._CLAIM_BOUNDARY
    assert embedded.output_id == first_output
    forbidden = result.to_dict()
    forbidden["payload"]["read_trace"][0]["artifact_binding"][  # type: ignore[index]
        "artifact_role"
    ] = "replay-target"
    with pytest.raises(QualificationContractError, match="ordered prefix"):
        records.D7V1PostselectionDescriptiveResult.from_dict(forbidden)


@pytest.mark.parametrize(
    ("section", "field", "replacement"),
    (
        ("outputs", "data", {"sequence": 999, "rows": []}),
        ("output_bindings", "json_pointer", "/outputs/1"),
        (
            "output_bindings",
            "target_schema_version",
            "spirallens.fake-output.v0.1",
        ),
        ("output_bindings", "canonical_sha256", ZERO_SHA),
    ),
)
def test_result_rejects_tampered_embedded_output_binding(
    section: str,
    field: str,
    replacement: object,
) -> None:
    document = _chain()["result"].to_dict()  # type: ignore[union-attr]
    output_id = records._POST_D6_OUTPUT_IDS[0]
    document["payload"][section][output_id][field] = replacement  # type: ignore[index]
    with pytest.raises(QualificationContractError, match="output_bindings"):
        records.D7V1PostselectionDescriptiveResult.from_dict(document)


def test_failed_result_can_record_an_empty_trace_and_output_set() -> None:
    chain = _chain()
    result = records.D7V1PostselectionDescriptiveResult.create(
        record_id="d7-v1-failed-result",
        repository_path=(
            "experiments/qualification/d7_spectral_moment_confirmation_v1/"
            "post-d6-descriptive-analysis-result.json"
        ),
        parent_binding=_bound(chain["attempt"]),
        chronology_receipt_binding=_bound(chain["receipt"]),
        read_trace=(),
        status="failed",
        outputs=(),
    )
    payload = result.to_dict()["payload"]
    assert payload["observations"] == {  # type: ignore[index]
        "read_trace_recorded": True,
        "any_input_read": False,
        "status_recorded": True,
    }


def test_module_has_no_legacy_confirmation_import_or_operational_surface() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)
    assert not any("confirmation_" in name for name in imported_modules)
    assert not imported_modules & {
        "os",
        "secrets",
        "subprocess",
        "torch",
        "transformers",
    }
    assert records.__all__ == ()


def test_noncanonical_bytes_and_byte_cap_are_rejected() -> None:
    c1 = _chain()["c1"]
    assert isinstance(c1, records.D7V1C1SourceSetRecord)
    noncanonical = canonical_json_bytes(c1.to_dict()) + b"\n"
    with pytest.raises(QualificationContractError, match="not canonical JSON"):
        records.D7V1C1SourceSetRecord.from_canonical_bytes(
            noncanonical,
            expected_sha256=sha256_bytes(noncanonical),
        )
    too_large = b"x" * (records.D7_V1_MAX_RECORD_BYTES + 1)
    with pytest.raises(QualificationContractError, match="byte contract"):
        records.D7V1C1SourceSetRecord.from_canonical_bytes(
            too_large,
            expected_sha256=sha256_bytes(too_large),
        )


def test_postselection_result_has_a_frozen_sixteen_mib_cap() -> None:
    chain = _chain()
    data_chunk = "x" * 1_500_000
    outputs = tuple(
        records.D7V1DescriptiveOutput.create(
            output_id=output_id,
            status="available",
            data={"payload": data_chunk},
        )
        for output_id in records._POST_D6_OUTPUT_IDS[:3]
    )
    result = records.D7V1PostselectionDescriptiveResult.create(
        record_id="d7-v1-large-failed-result",
        repository_path=(
            "experiments/qualification/d7_spectral_moment_confirmation_v1/"
            "post-d6-descriptive-analysis-result.json"
        ),
        parent_binding=_bound(chain["attempt"]),
        chronology_receipt_binding=_bound(chain["receipt"]),
        read_trace=(),
        status="failed",
        outputs=outputs,
    )
    assert len(result.canonical_bytes) > records.D7_V1_DEFAULT_MAX_RECORD_BYTES
    assert (
        len(result.canonical_bytes)
        < records.D7_V1_POSTSELECTION_RESULT_MAX_RECORD_BYTES
    )
    loaded = records.D7V1PostselectionDescriptiveResult.from_canonical_bytes(
        result.canonical_bytes,
        expected_sha256=result.canonical_sha256,
    )
    assert loaded.canonical_bytes == result.canonical_bytes
    assert (
        records.D7V1PostselectionDescriptiveResult.max_record_bytes
        == records.D7_V1_POSTSELECTION_RESULT_MAX_RECORD_BYTES
    )
    assert (
        records.D7V1C1SourceSetRecord.max_record_bytes
        == records.D7_V1_DEFAULT_MAX_RECORD_BYTES
    )

    too_large = b"x" * (records.D7_V1_POSTSELECTION_RESULT_MAX_RECORD_BYTES + 1)
    with pytest.raises(QualificationContractError, match="byte contract"):
        records.D7V1PostselectionDescriptiveResult.from_canonical_bytes(
            too_large,
            expected_sha256=sha256_bytes(too_large),
        )
