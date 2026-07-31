from __future__ import annotations

import hashlib
import inspect
from dataclasses import replace
from types import SimpleNamespace

import pytest

import spirallens
from spirallens import qualification
from spirallens.core.canonical import canonical_json_sha256
from spirallens.qualification import confirmation_attempt_records as r
from spirallens.qualification import confirmation_attempt_validation as v
from spirallens.qualification.common import QualificationContractError


def _h(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _prefix(
    label: str = "primary",
    *,
    target: str | None = None,
    role: r.D7AttemptRoleEvidence | None = None,
    store: str | None = None,
    launch_intent: str | None = None,
    execution_identity: str | None = None,
    output_namespace: str | None = None,
    terminal_path: str | None = None,
    authorization_namespace_absence: str | None = None,
) -> SimpleNamespace:
    target = target or _h("target")
    declaration = r.D7AttemptDeclarationRecord(
        target,
        launch_intent or _h(f"{label}-intent"),
        role or r.D7PrimaryRoleEvidence(),
        store or _h(f"{label}-store"),
        output_namespace or _h(f"{label}-namespace"),
        terminal_path or _h(f"{label}-terminal"),
        "a" * 40,
        execution_identity or _h(f"{label}-identity"),
    )
    authorization = r.D7LaunchAuthorizationRecord(
        declaration.canonical_sha256,
        target,
        declaration.attempt_key_sha256,
        declaration.authorization_commit,
        declaration.execution_identity_receipt_sha256,
        _h(f"{label}-source-runtime"),
        _h(f"{label}-runtime-spec"),
        _h(f"{label}-admission"),
        _h(f"{label}-freeze"),
        declaration.store_identity_sha256,
        declaration.output_namespace_identity_sha256,
        declaration.terminal_path_identity_sha256,
        authorization_namespace_absence
        or _h(f"{label}-authorization-namespace-absence"),
        _h(f"{label}-authorization-terminal-absence"),
    )
    claim = r.D7AttemptClaimRecord(
        declaration.canonical_sha256,
        authorization.canonical_sha256,
        target,
        declaration.attempt_key_sha256,
        declaration.execution_identity_receipt_sha256,
        declaration.store_identity_sha256,
    )
    start = r.D7ExecutionStartRecord(
        declaration.canonical_sha256,
        authorization.canonical_sha256,
        claim.canonical_sha256,
        target,
        declaration.attempt_key_sha256,
        declaration.authorization_commit,
        declaration.execution_identity_receipt_sha256,
        declaration.execution_identity_receipt_sha256,
        authorization.execution_source_runtime_receipt_sha256,
        authorization.runtime_specification_sha256,
        declaration.output_namespace_identity_sha256,
        declaration.terminal_path_identity_sha256,
        _h(f"{label}-pre-start-namespace-absence"),
        _h(f"{label}-pre-start-terminal-absence"),
    )
    return SimpleNamespace(
        declaration=declaration, authorization=authorization, claim=claim, start=start
    )


def _bindings(gates: int, gate_digest: str) -> tuple[r.D7ResultComponentBinding, ...]:
    result = []
    for index, component_id in enumerate(r.D7_RESULT_COMPONENT_ORDER):
        count = r.D7_RESULT_COMPONENT_FIXED_RECORD_COUNTS.get(component_id, gates)
        result.append(
            r.D7ResultComponentBinding(
                component_id,
                r.D7_RESULT_COMPONENT_CONTRACT_IDS[component_id],
                gate_digest if index == 5 else _h(f"component-{component_id.value}"),
                100 + index,
                count,
            )
        )
    return tuple(result)


def _payload(
    target: str,
    state: r.D7ScientificResultState = r.D7ScientificResultState.PASS,
    *,
    gate_states: tuple[r.D7GateState, ...] | None = None,
) -> r.D7ScientificResultPayload:
    states = (
        gate_states
        or {
            r.D7ScientificResultState.PASS: (r.D7GateState.PASS,) * 3,
            r.D7ScientificResultState.FAIL: (r.D7GateState.PASS, r.D7GateState.FAIL),
            r.D7ScientificResultState.INSUFFICIENT: (
                r.D7GateState.PASS,
                r.D7GateState.INSUFFICIENT,
            ),
        }[state]
    )
    gate_digest = _h("aggregate-gates")
    summary = r.D7GateOutcomeSummary.from_gate_states(
        gate_manifest_sha256=_h("gate-manifest"),
        gate_states=states,
        gate_results_component_sha256=gate_digest,
    )
    reasons = (
        () if state is r.D7ScientificResultState.PASS else (f"gate-{state.value}",)
    )
    return r.D7ScientificResultPayload(
        target,
        _h("inventory"),
        _h("aggregation"),
        state,
        reasons,
        summary,
        _bindings(len(states), gate_digest),
    )


def _scientific(
    prefix: SimpleNamespace | None = None,
    state: r.D7ScientificResultState = r.D7ScientificResultState.PASS,
    *,
    payload: r.D7ScientificResultPayload | None = None,
) -> SimpleNamespace:
    prefix = prefix or _prefix()
    payload = payload or _payload(prefix.start.replay_target_sha256, state)
    result = r.D7ScientificResultRecord(
        prefix.start.replay_target_sha256,
        prefix.start.attempt_key_sha256,
        prefix.start.canonical_sha256,
        prefix.start.execution_identity_receipt_sha256,
        payload.canonical_sha256,
        len(payload.canonical_bytes),
    )
    manifest = r.D7TerminalManifestRecord(
        prefix.start.replay_target_sha256,
        prefix.start.attempt_key_sha256,
        prefix.claim.canonical_sha256,
        prefix.start.canonical_sha256,
        prefix.start.execution_identity_receipt_sha256,
        r.D7TerminalArtifactKind.SCIENTIFIC_RESULT,
        result.canonical_sha256,
        v._scientific_members(payload, result),
    )
    consumption = r.D7TerminalConsumptionRecord(
        prefix.start.replay_target_sha256,
        prefix.start.attempt_key_sha256,
        prefix.claim.canonical_sha256,
        prefix.start.canonical_sha256,
        prefix.start.execution_identity_receipt_sha256,
        manifest.canonical_sha256,
        r.D7TerminalArtifactKind.SCIENTIFIC_RESULT,
        result.canonical_sha256,
        r.D7ConfirmationValueAccessState.OBSERVED,
    )
    return SimpleNamespace(
        prefix=prefix,
        payload=payload,
        result=result,
        manifest=manifest,
        consumption=consumption,
    )


def _failed(
    prefix: SimpleNamespace | None = None,
    *,
    external: bool = False,
    access: r.D7ConfirmationValueAccessState = r.D7ConfirmationValueAccessState.UNKNOWN,
) -> SimpleNamespace:
    prefix = prefix or _prefix()
    stage = (
        r.D7FailureStage.EVIDENCED_ABORT
        if external
        else r.D7FailureStage.EXECUTION_KERNEL
    )
    evidence = r.D7FailureEvidenceRecord(
        prefix.start.replay_target_sha256,
        prefix.start.attempt_key_sha256,
        prefix.start.canonical_sha256,
        prefix.start.execution_identity_receipt_sha256,
        stage,
        r.D7FailureEvidenceOrigin.EXTERNAL
        if external
        else r.D7FailureEvidenceOrigin.IN_PROCESS,
        "external-abort" if external else "kernel-error",
        _h("failure-payload"),
        211,
        _h("external-verification") if external else None,
        97 if external else None,
    )
    finalization = (
        r.D7StartedUnresolvedFinalizationRecord(
            prefix.start.replay_target_sha256,
            prefix.start.attempt_key_sha256,
            prefix.start.canonical_sha256,
            prefix.start.execution_identity_receipt_sha256,
            evidence.canonical_sha256,
            evidence.external_verification_receipt_sha256 or "",
            evidence.external_verification_receipt_byte_count or 0,
            _h("signed-external-witness-envelope"),
            193,
        )
        if external
        else None
    )
    failed = r.D7FailedAttemptRecord(
        prefix.start.replay_target_sha256,
        prefix.start.attempt_key_sha256,
        prefix.start.canonical_sha256,
        prefix.start.execution_identity_receipt_sha256,
        stage,
        evidence.canonical_sha256,
        finalization.canonical_sha256 if finalization else None,
        access,
    )
    manifest = r.D7TerminalManifestRecord(
        prefix.start.replay_target_sha256,
        prefix.start.attempt_key_sha256,
        prefix.claim.canonical_sha256,
        prefix.start.canonical_sha256,
        prefix.start.execution_identity_receipt_sha256,
        r.D7TerminalArtifactKind.FAILED_ATTEMPT,
        failed.canonical_sha256,
        v._failure_members(evidence, failed, finalization),
    )
    consumption = r.D7TerminalConsumptionRecord(
        prefix.start.replay_target_sha256,
        prefix.start.attempt_key_sha256,
        prefix.claim.canonical_sha256,
        prefix.start.canonical_sha256,
        prefix.start.execution_identity_receipt_sha256,
        manifest.canonical_sha256,
        r.D7TerminalArtifactKind.FAILED_ATTEMPT,
        failed.canonical_sha256,
        access,
    )
    return SimpleNamespace(
        prefix=prefix,
        evidence=evidence,
        finalization=finalization,
        failed=failed,
        manifest=manifest,
        consumption=consumption,
    )


def _examples() -> tuple[object, ...]:
    scientific, failed = _scientific(), _failed(external=True)
    assert failed.finalization
    isolated = v.derive_d7_isolated_replay_role_evidence(
        primary_declaration=scientific.prefix.declaration,
        primary_authorization=scientific.prefix.authorization,
        primary_claim=scientific.prefix.claim,
        primary_start=scientific.prefix.start,
        primary_payload=scientific.payload,
        primary_result=scientific.result,
        primary_manifest=scientific.manifest,
        primary_consumption=scientific.consumption,
    )
    return (
        scientific.prefix.declaration.role_evidence,
        isolated,
        scientific.prefix.declaration,
        scientific.prefix.authorization,
        scientific.prefix.claim,
        scientific.prefix.start,
        scientific.payload.gate_summary,
        scientific.payload.component_bindings[0],
        scientific.payload,
        scientific.result,
        failed.evidence,
        failed.finalization,
        failed.failed,
        scientific.manifest.immutable_members[0],
        scientific.manifest,
        scientific.consumption,
    )


def test_every_record_has_strict_canonical_roundtrip_and_golden_vector() -> None:
    examples = _examples()
    expected = (
        "d79427636fc6cad4bb95579dd8cc0347dd0d0f4270cf1f65ec1c930d5557acdc",
        "f39ade299e2b2f3b13d2c0fadfc13fcdccb2d19068c59613051aa1944d7116dd",
        "f115b05febc47fd12be7faaca7ce2461b4808a59ae0c20e4b51717541e0e4323",
        "a921802d1555dc2db1974efd89f3e8d1e308829f8dc9ceaa9ce91f4003179998",
        "8d403a67a565fccb4f9283070a59201054dc50ac2b5488bbdc5347334a7939d6",
        "c0daef13071a9645017813b5f3e02c8a386bb6edb035a15cde57164680bb4618",
        "2f8a704e045e11cb2db30b48404c4766a3874da2498fb20a35be9b27132d485b",
        "93bbfd2c871277f66ee02c69437319b8ebd178ed74b7c4ce970b65de0c966495",
        "b2feadd23b2036a00feed9509b639240201120df8c6d81c085c8dca43df6b721",
        "2f67c6fb535bd62350f171493e8a898c19959691d67fa59dde6486fd02ab9e9c",
        "7bf30285c87b38c0a6081dc551389776c0c26e8d5d9716a929c6cfcd17bce798",
        "59ba52b4d743e20ef697fc4bf7d540d7352762ed63a726dd832b22185e9312d5",
        "06efe4ed6d7b2492552fc05f3aa83e41a68e92be3be13f93b7c025a198437faa",
        "c214d63a15da4075809f4aa74f80e3adc46a6b548c8e8877ace14b010b626cfd",
        "0098c21867e82149c418a903f05d04797b9710143ccb9716bac47e6b8f74f84e",
        "7ebb576e0d5fab363947b21a4eabac83984a7315f869d9be8169821bc16ddbf9",
    )
    assert tuple(item.canonical_sha256 for item in examples) == expected
    for item in examples:
        cls = type(item)
        assert cls.from_dict(item.to_dict()) == item
        assert (
            cls.from_canonical_bytes(
                item.canonical_bytes, expected_sha256=item.canonical_sha256
            )
            == item
        )
        extra = item.to_dict() | {"future_extension": True}
        with pytest.raises(QualificationContractError, match="fields differ"):
            cls.from_dict(extra)
        noncanonical = b" " + item.canonical_bytes
        with pytest.raises(QualificationContractError):
            cls.from_canonical_bytes(
                noncanonical, expected_sha256=hashlib.sha256(noncanonical).hexdigest()
            )


def test_nested_json_constants_are_type_strict() -> None:
    scientific = _scientific()
    manifest = scientific.manifest.to_dict()
    required_consumption = manifest["required_consumption"]
    assert type(required_consumption) is dict
    required_consumption["manifest_sha256_must_be_bound"] = 1
    with pytest.raises(QualificationContractError, match="required_consumption"):
        r.D7TerminalManifestRecord.from_dict(manifest)

    failed = _failed(external=True)
    assert failed.finalization
    finalization = failed.finalization.to_dict()
    assertions = finalization["verification_receipt_required_assertions"]
    assert type(assertions) is dict
    assertions["aggregate_outcome_observed"] = 0
    with pytest.raises(QualificationContractError, match="assertions"):
        r.D7StartedUnresolvedFinalizationRecord.from_dict(finalization)


def test_prefix_requires_exact_types_and_every_frozen_join() -> None:
    prefix = _prefix()

    class LyingString(str):
        def __eq__(self, other: object) -> bool:
            return True

        def __ne__(self, other: object) -> bool:
            return False

        __hash__ = str.__hash__

    with pytest.raises(QualificationContractError, match="lowercase SHA-256"):
        replace(
            prefix.declaration,
            replay_target_sha256=LyingString("f" * 64),
        )
    values = {
        "declaration": prefix.declaration,
        "authorization": prefix.authorization,
        "claim": prefix.claim,
        "start": prefix.start,
    }
    substitutions = {
        "authorization": "attempt_declaration_sha256 replay_target_sha256 attempt_key_sha256 authorization_commit execution_identity_receipt_sha256 execution_source_runtime_receipt_sha256 runtime_specification_sha256 store_identity_sha256 output_namespace_identity_sha256 terminal_path_identity_sha256",
        "claim": "attempt_declaration_sha256 launch_authorization_sha256 replay_target_sha256 attempt_key_sha256 execution_identity_receipt_sha256 store_identity_sha256",
        "start": "attempt_declaration_sha256 launch_authorization_sha256 attempt_claim_sha256 replay_target_sha256 attempt_key_sha256 authorization_commit execution_identity_receipt_sha256 observed_execution_identity_receipt_sha256 observed_execution_source_runtime_receipt_sha256 observed_runtime_specification_sha256 output_namespace_identity_sha256 terminal_path_identity_sha256",
    }
    for owner, fields in substitutions.items():
        for field in fields.split():
            changed = "b" * 40 if field == "authorization_commit" else _h(field)
            with pytest.raises(QualificationContractError):
                replacement = replace(values[owner], **{field: changed})
                v.validate_d7_attempt_prefix(**(values | {owner: replacement}))
    receipts = (
        prefix.authorization.authorization_output_namespace_absence_receipt_sha256,
        prefix.authorization.authorization_terminal_path_absence_receipt_sha256,
        prefix.start.pre_start_output_namespace_absence_receipt_sha256,
        prefix.start.pre_start_terminal_path_absence_receipt_sha256,
    )
    semantic = (
        prefix.declaration.execution_identity_receipt_sha256,
        prefix.authorization.execution_source_runtime_receipt_sha256,
        prefix.authorization.runtime_specification_sha256,
    )
    assert len(set(receipts)) == 4 and len(set(semantic)) == 3
    assert semantic[1] == prefix.start.observed_execution_source_runtime_receipt_sha256
    for field, collision in (
        ("execution_source_runtime_receipt_sha256", semantic[0]),
        ("runtime_specification_sha256", semantic[1]),
    ):
        with pytest.raises(QualificationContractError, match="must differ"):
            replace(prefix.authorization, **{field: collision})
    with pytest.raises(QualificationContractError, match="must differ"):
        replace(
            prefix.start,
            observed_runtime_specification_sha256=(
                prefix.start.observed_execution_source_runtime_receipt_sha256
            ),
        )
    with pytest.raises(QualificationContractError, match="absence receipts"):
        v.validate_d7_attempt_prefix(
            **(
                values
                | {
                    "start": replace(
                        prefix.start,
                        pre_start_output_namespace_absence_receipt_sha256=receipts[0],
                    )
                }
            )
        )

    class ClaimSubclass(r.D7AttemptClaimRecord):
        pass

    subclass = ClaimSubclass(
        *(
            getattr(prefix.claim, field)
            for field in (
                "attempt_declaration_sha256",
                "launch_authorization_sha256",
                "replay_target_sha256",
                "attempt_key_sha256",
                "execution_identity_receipt_sha256",
                "store_identity_sha256",
            )
        )
    )
    with pytest.raises(TypeError, match="wrong D7 record type"):
        v.validate_d7_attempt_prefix(**(values | {"claim": subclass}))


def test_nested_canonical_records_require_exact_types() -> None:
    chain = _scientific()

    class RoleSubclass(r.D7PrimaryRoleEvidence):
        pass

    with pytest.raises(TypeError, match="role_evidence"):
        replace(chain.prefix.declaration, role_evidence=RoleSubclass())

    class GateSubclass(r.D7GateOutcomeSummary):
        pass

    gate = chain.payload.gate_summary
    with pytest.raises(TypeError, match="gate_summary"):
        replace(
            chain.payload,
            gate_summary=GateSubclass(
                *(
                    getattr(gate, field)
                    for field in (
                        "gate_manifest_sha256",
                        "required_gate_count",
                        "pass_count",
                        "fail_count",
                        "insufficient_count",
                        "not_run_count",
                        "aggregate_state",
                        "gate_results_component_sha256",
                    )
                )
            ),
        )

    class BindingSubclass(r.D7ResultComponentBinding):
        pass

    binding = chain.payload.component_bindings[0]
    subclass_binding = BindingSubclass(
        binding.component_id,
        binding.component_contract_id,
        binding.component_canonical_sha256,
        binding.byte_count,
        binding.record_count,
    )
    with pytest.raises(TypeError, match="component_bindings"):
        replace(
            chain.payload,
            component_bindings=(
                subclass_binding,
                *chain.payload.component_bindings[1:],
            ),
        )

    class MemberSubclass(r.D7TerminalMemberBinding):
        pass

    member = chain.manifest.immutable_members[0]
    subclass_member = MemberSubclass(
        member.filename,
        member.member_kind,
        member.member_contract_id,
        member.member_canonical_sha256,
        member.byte_count,
    )
    with pytest.raises(TypeError, match="immutable_members"):
        replace(
            chain.manifest,
            immutable_members=(subclass_member, *chain.manifest.immutable_members[1:]),
        )


@pytest.mark.parametrize(
    ("gate", "overall"),
    [
        (r.D7GateState.PASS, r.D7ScientificResultState.PASS),
        (r.D7GateState.FAIL, r.D7ScientificResultState.FAIL),
        (r.D7GateState.INSUFFICIENT, r.D7ScientificResultState.INSUFFICIENT),
        (r.D7GateState.NOT_RUN, r.D7ScientificResultState.INSUFFICIENT),
    ],
)
def test_four_gate_states_persist_with_three_terminal_states(
    gate: r.D7GateState, overall: r.D7ScientificResultState
) -> None:
    summary = r.D7GateOutcomeSummary.from_gate_states(
        gate_manifest_sha256=_h("four-state-manifest"),
        gate_states=(gate,),
        gate_results_component_sha256=_h("four-state-component"),
    )
    payload = _payload(_h("four-state-target"), overall, gate_states=(gate,))
    assert summary.aggregate_state is overall
    assert payload.gate_summary.to_dict()[f"{gate.value}_count"] == 1
    assert set(r.D7GateState) > set(r.D7ScientificResultState)
    assert "not_run" not in {state.value for state in r.D7ScientificResultState}


def test_six_component_contracts_have_fixed_order_names_counts_and_boundary() -> None:
    payload = _payload(_h("component-target"))
    assert tuple(item.component_id for item in payload.component_bindings) == (
        r.D7_RESULT_COMPONENT_ORDER
    )
    for item in payload.component_bindings:
        document = item.to_dict()
        assert document["filename"] == f"result-{item.component_id.value}.json"
        assert document["component_contract_id"].endswith("payload-contract.v0.1")
        assert "component_schema_version" not in document
        fixed = r.D7_RESULT_COMPONENT_FIXED_RECORD_COUNTS.get(item.component_id)
        assert item.record_count == (fixed or payload.gate_summary.required_gate_count)
    with pytest.raises(QualificationContractError, match="fixed component contract"):
        replace(payload.component_bindings[0], component_contract_id=_h("not-contract"))
    with pytest.raises(QualificationContractError, match="record_count"):
        replace(payload.component_bindings[0], record_count=999)
    with pytest.raises(QualificationContractError, match="fixed ordered inventory"):
        replace(payload, component_bindings=tuple(reversed(payload.component_bindings)))
    component_id = r.D7_RESULT_COMPONENT_ORDER[0]
    with pytest.raises(TypeError):
        r.D7_RESULT_COMPONENT_CONTRACT_IDS[component_id] = "mutated"
    with pytest.raises(TypeError):
        r.D7_RESULT_COMPONENT_FIXED_RECORD_COUNTS[component_id] = 1
    assert payload.result_schema_sha256 == (
        r.D7_SCIENTIFIC_RESULT_IMPLEMENTATION_SCHEMA_SHA256
    )
    assert payload.result_schema_sha256 == canonical_json_sha256(
        r._result_schema_descriptor()
    )


@pytest.mark.parametrize("state", list(r.D7ScientificResultState))
def test_complete_scientific_terminals_cover_all_outcomes(
    state: r.D7ScientificResultState,
) -> None:
    chain = _scientific(state=state)
    v.validate_d7_scientific_terminal_chain(
        claim=chain.prefix.claim,
        start=chain.prefix.start,
        payload=chain.payload,
        result=chain.result,
        manifest=chain.manifest,
        consumption=chain.consumption,
    )
    assert chain.payload.state is state
    assert tuple(item.filename for item in chain.manifest.immutable_members) == tuple(
        sorted(
            (
                r.D7_SCIENTIFIC_RESULT_FILENAME,
                r.D7_SCIENTIFIC_RESULT_PAYLOAD_FILENAME,
                *(item.filename for item in chain.payload.component_bindings),
            )
        )
    )


@pytest.mark.parametrize("access", list(r.D7ConfirmationValueAccessState))
def test_failed_terminal_never_observes_aggregate_and_preserves_access_tristate(
    access: r.D7ConfirmationValueAccessState,
) -> None:
    chain = _failed(access=access)
    v.validate_d7_failed_terminal_chain(
        claim=chain.prefix.claim,
        start=chain.prefix.start,
        evidence=chain.evidence,
        failed_attempt=chain.failed,
        manifest=chain.manifest,
        consumption=chain.consumption,
    )
    assert chain.failed.confirmation_value_access_state is access
    assert chain.failed.to_dict()["aggregate_outcome_observed"] is False
    assert chain.consumption.to_dict()["aggregate_outcome_observed"] is False
    assert chain.consumption.confirmation_value_access_state is access


def test_external_abort_has_evidence_verification_and_exact_inventory() -> None:
    chain = _failed(external=True)
    assert chain.finalization
    v.validate_d7_failed_terminal_chain(
        claim=chain.prefix.claim,
        start=chain.prefix.start,
        evidence=chain.evidence,
        failed_attempt=chain.failed,
        manifest=chain.manifest,
        consumption=chain.consumption,
        finalization=chain.finalization,
    )
    v.validate_d7_started_unresolved_finalization(
        start=chain.prefix.start,
        evidence=chain.evidence,
        finalization=chain.finalization,
    )
    evidence_document = chain.evidence.to_dict()
    assert evidence_document["evidence_payload"]["contract_id"] == (
        r.D7_FAILURE_EVIDENCE_PAYLOAD_CONTRACT_ID
    )
    assert evidence_document["external_verification_receipt"]["contract_id"] == (
        r.D7_EXTERNAL_ABORT_VERIFICATION_RECEIPT_CONTRACT_ID
    )
    assert tuple(item.filename for item in chain.manifest.immutable_members) == tuple(
        sorted(
            (
                r.D7_EXTERNAL_ABORT_VERIFICATION_RECEIPT_FILENAME,
                r.D7_FAILED_ATTEMPT_FILENAME,
                r.D7_FAILURE_EVIDENCE_FILENAME,
                r.D7_FAILURE_EVIDENCE_PAYLOAD_FILENAME,
                r.D7_SIGNED_EXTERNAL_ABORT_WITNESS_ENVELOPE_FILENAME,
                r.D7_STARTED_UNRESOLVED_FINALIZATION_FILENAME,
            )
        )
    )
    with pytest.raises(QualificationContractError, match="requires external"):
        replace(chain.evidence, origin=r.D7FailureEvidenceOrigin.IN_PROCESS)
    with pytest.raises(QualificationContractError, match="external_abort_evidence"):
        v.validate_d7_started_unresolved_finalization(
            start=chain.prefix.start,
            evidence=chain.evidence,
            finalization=replace(
                chain.finalization, external_abort_evidence_sha256=_h("fabricated")
            ),
        )
    envelope_member = next(
        member
        for member in chain.manifest.immutable_members
        if member.member_kind
        is r.D7TerminalMemberKind.SIGNED_EXTERNAL_ABORT_WITNESS_ENVELOPE
    )
    assert envelope_member.member_contract_id == (
        r.D7_SIGNED_EXTERNAL_ABORT_WITNESS_ENVELOPE_CONTRACT_ID
    )
    assert envelope_member.member_canonical_sha256 == (
        chain.finalization.signed_external_abort_witness_envelope_sha256
    )
    missing_envelope = replace(
        chain.manifest,
        immutable_members=tuple(
            member
            for member in chain.manifest.immutable_members
            if member.member_kind
            is not r.D7TerminalMemberKind.SIGNED_EXTERNAL_ABORT_WITNESS_ENVELOPE
        ),
    )
    with pytest.raises(QualificationContractError, match="manifest members"):
        v.validate_d7_failed_terminal_chain(
            claim=chain.prefix.claim,
            start=chain.prefix.start,
            evidence=chain.evidence,
            failed_attempt=chain.failed,
            manifest=missing_envelope,
            consumption=replace(
                chain.consumption,
                terminal_manifest_sha256=missing_envelope.canonical_sha256,
            ),
            finalization=chain.finalization,
        )


def _isolated_arguments(chain: SimpleNamespace) -> dict[str, object]:
    return {
        "primary_declaration": chain.prefix.declaration,
        "primary_authorization": chain.prefix.authorization,
        "primary_claim": chain.prefix.claim,
        "primary_start": chain.prefix.start,
        "primary_payload": chain.payload,
        "primary_result": chain.result,
        "primary_manifest": chain.manifest,
        "primary_consumption": chain.consumption,
    }


def _attempt_arguments(chain: SimpleNamespace) -> dict[str, object]:
    return {
        "declaration": chain.prefix.declaration,
        "authorization": chain.prefix.authorization,
        "claim": chain.prefix.claim,
        "start": chain.prefix.start,
        "payload": chain.payload,
        "result": chain.result,
        "manifest": chain.manifest,
        "consumption": chain.consumption,
    }


def test_isolated_replay_rejects_fabricated_or_nonpass_primary() -> None:
    primary = _scientific()
    arguments = _isolated_arguments(primary)
    evidence = v.derive_d7_isolated_replay_role_evidence(**arguments)
    v.validate_d7_isolated_replay_role_evidence(evidence=evidence, **arguments)
    isolated = _scientific(
        prefix=_prefix(
            "isolated",
            target=primary.prefix.declaration.replay_target_sha256,
            role=evidence,
            store=primary.prefix.declaration.store_identity_sha256,
        )
    )
    isolated_arguments = _attempt_arguments(isolated)
    v.validate_d7_isolated_replay_attempt_chain(
        **isolated_arguments,
        **arguments,
    )
    with pytest.raises(QualificationContractError, match="combined"):
        v.validate_d7_scientific_attempt_chain(**isolated_arguments)
    for field, value, message in (
        (
            "execution_identity",
            primary.prefix.declaration.execution_identity_receipt_sha256,
            "execution identity",
        ),
        (
            "output_namespace",
            primary.prefix.declaration.output_namespace_identity_sha256,
            "output namespace",
        ),
        (
            "terminal_path",
            primary.prefix.declaration.terminal_path_identity_sha256,
            "terminal path",
        ),
        (
            "launch_intent",
            primary.prefix.declaration.launch_intent_sha256,
            "launch intent",
        ),
        (
            "authorization_namespace_absence",
            primary.prefix.authorization.authorization_output_namespace_absence_receipt_sha256,
            "absence receipts",
        ),
    ):
        reused = _scientific(
            prefix=_prefix(
                f"isolated-reused-{field}",
                target=primary.prefix.declaration.replay_target_sha256,
                role=evidence,
                store=primary.prefix.declaration.store_identity_sha256,
                **{field: value},
            )
        )
        with pytest.raises(QualificationContractError, match=message):
            v.validate_d7_isolated_replay_attempt_chain(
                **_attempt_arguments(reused),
                **arguments,
            )
    for label, overrides in (
        (
            "cross-kind-identity",
            {"execution_identity": (primary.prefix.declaration.launch_intent_sha256)},
        ),
        (
            "cross-kind-absence",
            {
                "authorization_namespace_absence": (
                    primary.prefix.declaration.output_namespace_identity_sha256
                )
            },
        ),
    ):
        reused = _scientific(
            prefix=_prefix(
                f"isolated-reused-{label}",
                target=primary.prefix.declaration.replay_target_sha256,
                role=evidence,
                store=primary.prefix.declaration.store_identity_sha256,
                **overrides,
            )
        )
        with pytest.raises(QualificationContractError, match="identifier sets"):
            v.validate_d7_isolated_replay_attempt_chain(
                **_attempt_arguments(reused),
                **arguments,
            )
    alternate_store = _scientific(
        prefix=_prefix(
            "isolated-alternate-store",
            target=primary.prefix.declaration.replay_target_sha256,
            role=evidence,
        )
    )
    with pytest.raises(QualificationContractError, match="store identity"):
        v.validate_d7_isolated_replay_attempt_chain(
            **_attempt_arguments(alternate_store),
            **arguments,
        )
    fabricated_evidence = replace(
        evidence,
        primary_attempt_claim_sha256=_h("disconnected-primary-claim"),
    )
    fabricated = _scientific(
        prefix=_prefix(
            "fabricated-isolated",
            target=primary.prefix.declaration.replay_target_sha256,
            role=fabricated_evidence,
            store=primary.prefix.declaration.store_identity_sha256,
        )
    )
    with pytest.raises(QualificationContractError, match="primary_attempt_claim"):
        v.validate_d7_isolated_replay_attempt_chain(
            declaration=fabricated.prefix.declaration,
            authorization=fabricated.prefix.authorization,
            claim=fabricated.prefix.claim,
            start=fabricated.prefix.start,
            payload=fabricated.payload,
            result=fabricated.result,
            manifest=fabricated.manifest,
            consumption=fabricated.consumption,
            **arguments,
        )
    fake_claim = replace(
        primary.prefix.claim, launch_authorization_sha256=_h("fabricated-authorization")
    )
    fabricated = replace(
        evidence, primary_attempt_claim_sha256=fake_claim.canonical_sha256
    )
    with pytest.raises(QualificationContractError, match="launch_authorization_sha256"):
        v.validate_d7_isolated_replay_role_evidence(
            evidence=fabricated, **(arguments | {"primary_claim": fake_claim})
        )
    failed_primary = _scientific(state=r.D7ScientificResultState.FAIL)
    with pytest.raises(QualificationContractError, match="passed primary"):
        v.derive_d7_isolated_replay_role_evidence(**_isolated_arguments(failed_primary))


def test_failed_isolated_replay_requires_the_same_primary_and_separation() -> None:
    primary = _scientific()
    primary_arguments = _isolated_arguments(primary)
    role = v.derive_d7_isolated_replay_role_evidence(**primary_arguments)
    failed = _failed(
        prefix=_prefix(
            "failed-isolated",
            target=primary.prefix.declaration.replay_target_sha256,
            role=role,
            store=primary.prefix.declaration.store_identity_sha256,
        )
    )
    v.validate_d7_isolated_replay_failed_attempt_chain(
        declaration=failed.prefix.declaration,
        authorization=failed.prefix.authorization,
        claim=failed.prefix.claim,
        start=failed.prefix.start,
        evidence=failed.evidence,
        failed_attempt=failed.failed,
        manifest=failed.manifest,
        consumption=failed.consumption,
        **primary_arguments,
    )
    fabricated_role = replace(
        role,
        primary_terminal_consumption_sha256=_h("fabricated-consumption"),
    )
    fabricated = _failed(
        prefix=_prefix(
            "failed-isolated-fabricated",
            target=primary.prefix.declaration.replay_target_sha256,
            role=fabricated_role,
            store=primary.prefix.declaration.store_identity_sha256,
        )
    )
    with pytest.raises(
        QualificationContractError,
        match="primary_terminal_consumption_sha256",
    ):
        v.validate_d7_isolated_replay_failed_attempt_chain(
            declaration=fabricated.prefix.declaration,
            authorization=fabricated.prefix.authorization,
            claim=fabricated.prefix.claim,
            start=fabricated.prefix.start,
            evidence=fabricated.evidence,
            failed_attempt=fabricated.failed,
            manifest=fabricated.manifest,
            consumption=fabricated.consumption,
            **primary_arguments,
        )


def test_manifest_reserved_mapping_inventory_and_acyclicity() -> None:
    chain = _scientific()
    members = chain.manifest.immutable_members
    manifest_document = chain.manifest.to_dict()
    assert manifest_document["consumption_sha256_present"] is False
    assert "terminal_manifest_sha256" not in manifest_document
    with pytest.raises(QualificationContractError, match="kind, filename"):
        replace(
            members[0],
            member_kind=r.D7TerminalMemberKind.FAILURE_EVIDENCE,
        )
    missing = tuple(
        item
        for item in members
        if item
        is not next(
            member
            for member in members
            if member.member_kind is r.D7TerminalMemberKind.RESULT_COMPONENT
        )
    )
    for altered in (
        missing,
        tuple(
            sorted(
                (
                    *members,
                    r.D7TerminalMemberBinding(
                        r.D7_FAILURE_EVIDENCE_FILENAME,
                        r.D7TerminalMemberKind.FAILURE_EVIDENCE,
                        r.D7_FAILURE_EVIDENCE_SCHEMA_VERSION,
                        _h("extra"),
                        1,
                    ),
                ),
                key=lambda item: item.filename,
            )
        ),
    ):
        manifest = replace(chain.manifest, immutable_members=altered)
        consumption = replace(
            chain.consumption, terminal_manifest_sha256=manifest.canonical_sha256
        )
        with pytest.raises(QualificationContractError, match="manifest members"):
            v.validate_d7_scientific_terminal_chain(
                claim=chain.prefix.claim,
                start=chain.prefix.start,
                payload=chain.payload,
                result=chain.result,
                manifest=manifest,
                consumption=consumption,
            )
    with pytest.raises(QualificationContractError, match="unique, and sorted"):
        replace(chain.manifest, immutable_members=tuple(reversed(members)))
    with pytest.raises(QualificationContractError, match="manifest or consumption"):
        r.D7TerminalMemberBinding(
            r.D7_TERMINAL_CONSUMPTION_FILENAME,
            r.D7TerminalMemberKind.SCIENTIFIC_RESULT,
            r.D7_SCIENTIFIC_RESULT_SCHEMA_VERSION,
            _h("cycle"),
            1,
        )


def test_no_operational_api_or_root_reexports() -> None:
    assert r.__all__ == ()
    assert v.__all__ == ()
    allowed_functions = {
        "d7_attempt_key_sha256",
        "derive_d7_isolated_replay_role_evidence",
        *(name for name in vars(v) if name.startswith("validate_d7_")),
    }
    public_functions = {
        name
        for module in (r, v)
        for name, value in vars(module).items()
        if not name.startswith("_")
        and inspect.isfunction(value)
        and value.__module__ == module.__name__
    }
    assert public_functions <= allowed_functions
    forbidden = "write load authorize claim start finalize run publish".split()
    assert not {
        name
        for name in public_functions
        if any(name == word or name.startswith(f"{word}_") for word in forbidden)
    }
    contract_names = {
        name
        for name, value in vars(r).items()
        if not name.startswith("_")
        and (inspect.isclass(value) or inspect.isfunction(value))
        and getattr(value, "__module__", None) == r.__name__
    }
    for name in contract_names:
        assert name not in spirallens.__all__
        assert name not in qualification.__all__
        assert not hasattr(spirallens, name)
        assert not hasattr(qualification, name)
