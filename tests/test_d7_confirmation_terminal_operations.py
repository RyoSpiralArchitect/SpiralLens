from __future__ import annotations

import inspect
from dataclasses import replace
from pathlib import Path

import pytest

import spirallens
import test_d7_confirmation_attempt_evidence as evidence_fixtures
import test_d7_confirmation_attempt_persistence as prefix_fixtures
import test_d7_confirmation_result_components as component_fixtures
from spirallens import qualification
from spirallens.qualification import confirmation_attempt_records as r
from spirallens.qualification import confirmation_attempt_terminal_persistence as tp
from spirallens.qualification import confirmation_runner as runner
from spirallens.qualification import confirmation_terminal_operations as operations
from spirallens.qualification.common import QualificationContractError


@pytest.fixture(scope="module")
def component_bundle() -> component_fixtures._Bundle:
    return component_fixtures.bundle.__wrapped__()


def _ownership(prefix: object) -> runner._D7PostStartOwnership:
    return runner._D7PostStartOwnership(
        prefix.declaration,  # type: ignore[attr-defined]
        prefix.authorization,  # type: ignore[attr-defined]
        prefix.claim,  # type: ignore[attr-defined]
        prefix.start,  # type: ignore[attr-defined]
        full_inventory_sha256=component_fixtures._INVENTORY,
        aggregation_sha256=component_fixtures._AGGREGATION,
        result_schema_sha256=(r.D7_SCIENTIFIC_RESULT_IMPLEMENTATION_SCHEMA_SHA256),
        _factory_token=runner._POST_START_OWNERSHIP_FACTORY_TOKEN,
    )


def _producer_output(
    bundle: component_fixtures._Bundle,
) -> runner.D7ScientificProducerOutput:
    return runner.D7ScientificProducerOutput(
        event_ledger=bundle.event,
        core_cells=bundle.core,
        loop_cells=bundle.loop,
        primary_units=bundle.primary,
        required_strata=bundle.strata,
        aggregate_gates=bundle.gates,
        result_payload=bundle.result,
    )


def test_runner_scientific_handoff_publishes_one_typed_terminal(
    tmp_path: Path,
    component_bundle: component_fixtures._Bundle,
) -> None:
    prefix = prefix_fixtures._prefix(tmp_path)
    loaded_prefix = prefix_fixtures._persist(prefix)
    ownership = _ownership(prefix)
    prepared = runner.prepare_d7_post_start_terminal(
        ownership,
        lambda: _producer_output(component_bundle),
    )

    identity = operations.persist_d7_prepared_terminal_no_replace(
        loaded_prefix,
        prepared,
    )
    loaded = tp.load_d7_structural_terminal_transaction(
        loaded_prefix,
        expected_manifest_sha256=identity.terminal_manifest_sha256,
        expected_consumption_sha256=identity.terminal_consumption_sha256,
    )

    assert loaded.terminal_artifact == prepared.scientific_result
    assert loaded.manifest.terminal_artifact_kind is (
        r.D7TerminalArtifactKind.SCIENTIFIC_RESULT
    )
    assert loaded.authority_granted is False
    with pytest.raises(QualificationContractError, match="replace existing"):
        operations.persist_d7_prepared_terminal_no_replace(
            loaded_prefix,
            prepared,
        )


def test_runner_failure_handoff_cannot_be_rebound_to_another_prefix(
    tmp_path: Path,
) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    first = prefix_fixtures._prefix(first_dir)
    second = prefix_fixtures._prefix(second_dir)
    first_loaded = prefix_fixtures._persist(first)
    second_loaded = prefix_fixtures._persist(second)
    ownership = _ownership(first)
    original = RuntimeError("runner failure")

    with pytest.raises(RuntimeError) as caught:
        runner.prepare_d7_post_start_terminal(
            ownership,
            lambda: (_ for _ in ()).throw(original),
        )
    prepared = getattr(
        caught.value,
        runner.D7_PREPARED_FAILED_TERMINAL_ATTRIBUTE,
    )
    with pytest.raises(QualificationContractError, match="differs"):
        operations.persist_d7_prepared_terminal_no_replace(
            second_loaded,
            prepared,
        )
    assert not (second_dir / "primary-terminal").exists()

    identity = operations.persist_d7_prepared_terminal_no_replace(
        first_loaded,
        prepared,
    )
    assert identity.terminal_artifact_kind is r.D7TerminalArtifactKind.FAILED_ATTEMPT


def test_signed_external_abort_is_verified_derived_and_persisted_as_one_path(
    tmp_path: Path,
) -> None:
    prefix = prefix_fixtures._prefix(tmp_path)
    loaded_prefix = prefix_fixtures._persist(prefix)
    ownership = _ownership(prefix)
    signed = evidence_fixtures._signed_external_witness(prefix)

    authenticated = operations.finalize_d7_external_abort_relative_to_pins_no_replace(
        loaded_prefix,
        ownership,
        envelope_source=signed.envelope.canonical_bytes,
        expected_envelope_sha256=signed.envelope.canonical_sha256,
        trust_root=signed.trust_root,
        payload=signed.failure.payload,
        structural_receipt=signed.failure.receipt,
    )

    assert authenticated.witness_signatures_verified is True
    assert authenticated.signature_authentication_scope == (
        "explicit-runtime-pins-only"
    )
    assert authenticated.trust_root_provenance_verified is False
    assert authenticated.authoritative_start_proved is False
    assert authenticated.authority_granted is False
    assert authenticated.execution_observed is False
    assert authenticated.scientific_claim_eligible is False
    assert authenticated.created_by_call is True
    assert (
        authenticated.signed_witness_envelope_sha256 == signed.envelope.canonical_sha256
    )
    with pytest.raises(TypeError, match="requires its verifier"):
        replace(authenticated, _factory_token=object())

    reloaded = operations.load_d7_external_abort_relative_to_pins(
        loaded_prefix,
        expected_manifest_sha256=authenticated.terminal_manifest_sha256,
        expected_consumption_sha256=authenticated.terminal_consumption_sha256,
        trust_root=signed.trust_root,
    )
    assert reloaded.created_by_call is False
    assert reloaded.failed_attempt_sha256 == authenticated.failed_attempt_sha256
    assert reloaded.runtime_trust_root_sha256 == (
        authenticated.runtime_trust_root_sha256
    )


def test_wrong_runtime_pins_never_publish_and_cannot_authenticate(
    tmp_path: Path,
) -> None:
    first_dir = tmp_path / "unpublished"
    second_dir = tmp_path / "published"
    first_dir.mkdir()
    second_dir.mkdir()
    first = prefix_fixtures._prefix(first_dir)
    first_loaded = prefix_fixtures._persist(first)
    signed = evidence_fixtures._signed_external_witness(first)
    wrong_key = (
        bytes([signed.trust_root.verifier_public_key[0] ^ 1])
        + (signed.trust_root.verifier_public_key[1:])
    )
    wrong_root = replace(
        signed.trust_root,
        verifier_public_key=wrong_key,
    )
    with pytest.raises(QualificationContractError, match="runtime trust root"):
        operations.finalize_d7_external_abort_relative_to_pins_no_replace(
            first_loaded,
            _ownership(first),
            envelope_source=signed.envelope.canonical_bytes,
            expected_envelope_sha256=signed.envelope.canonical_sha256,
            trust_root=wrong_root,
            payload=signed.failure.payload,
            structural_receipt=signed.failure.receipt,
        )
    assert not (first_dir / "primary-terminal").exists()

    second = prefix_fixtures._prefix(second_dir)
    second_loaded = prefix_fixtures._persist(second)
    second_signed = evidence_fixtures._signed_external_witness(second)
    receipt = operations.finalize_d7_external_abort_relative_to_pins_no_replace(
        second_loaded,
        _ownership(second),
        envelope_source=second_signed.envelope.canonical_bytes,
        expected_envelope_sha256=second_signed.envelope.canonical_sha256,
        trust_root=second_signed.trust_root,
        payload=second_signed.failure.payload,
        structural_receipt=second_signed.failure.receipt,
    )
    second_wrong_key = (
        bytes([second_signed.trust_root.verifier_public_key[0] ^ 1])
        + second_signed.trust_root.verifier_public_key[1:]
    )
    second_wrong_root = replace(
        second_signed.trust_root,
        verifier_public_key=second_wrong_key,
    )
    with pytest.raises(QualificationContractError, match="runtime trust root"):
        operations.load_d7_external_abort_relative_to_pins(
            second_loaded,
            expected_manifest_sha256=receipt.terminal_manifest_sha256,
            expected_consumption_sha256=receipt.terminal_consumption_sha256,
            trust_root=second_wrong_root,
        )


def test_operations_surface_has_no_supplier_start_or_preverified_witness_input() -> (
    None
):
    assert operations.__all__ == ()
    assert not hasattr(spirallens, "D7ExternalAbortAuthenticationRelativeToPins")
    assert not hasattr(
        qualification,
        "D7ExternalAbortAuthenticationRelativeToPins",
    )
    signature = inspect.signature(
        operations.finalize_d7_external_abort_relative_to_pins_no_replace
    )
    assert "verified_witness" not in signature.parameters
    assert "supplier" not in signature.parameters
    assert "seed" not in signature.parameters
    assert "execution_start" not in signature.parameters
    assert not hasattr(operations, "issue_d7_post_start_ownership")
