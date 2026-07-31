from __future__ import annotations

import inspect
import pickle
from dataclasses import replace
from types import SimpleNamespace

import pytest

from spirallens import qualification
from spirallens.qualification import confirmation_attempt_evidence as e
from spirallens.qualification import confirmation_attempt_evidence_validation as ev
from spirallens.qualification import confirmation_attempt_records as r
from spirallens.qualification import confirmation_runner as runner
from spirallens.qualification.common import QualificationContractError
from test_d7_confirmation_attempt_records import _h, _prefix, _scientific
import test_d7_confirmation_result_components as component_fixtures


@pytest.fixture(scope="module")
def valid_bundle() -> component_fixtures._Bundle:
    return component_fixtures.bundle.__wrapped__()


def _ownership(
    prefix: SimpleNamespace | None = None,
    *,
    full_inventory_sha256: str = component_fixtures._INVENTORY,
    aggregation_sha256: str = component_fixtures._AGGREGATION,
    result_schema_sha256: str = (r.D7_SCIENTIFIC_RESULT_IMPLEMENTATION_SCHEMA_SHA256),
) -> runner._D7PostStartOwnership:
    prefix = prefix or _prefix()
    return runner._D7PostStartOwnership(
        prefix.declaration,
        prefix.authorization,
        prefix.claim,
        prefix.start,
        full_inventory_sha256=full_inventory_sha256,
        aggregation_sha256=aggregation_sha256,
        result_schema_sha256=result_schema_sha256,
        _factory_token=runner._POST_START_OWNERSHIP_FACTORY_TOKEN,
    )


def _producer_output(
    bundle: component_fixtures._Bundle,
    *,
    result_payload: r.D7ScientificResultPayload | None = None,
) -> runner.D7ScientificProducerOutput:
    return runner.D7ScientificProducerOutput(
        event_ledger=bundle.event,
        core_cells=bundle.core,
        loop_cells=bundle.loop,
        primary_units=bundle.primary,
        required_strata=bundle.strata,
        aggregate_gates=bundle.gates,
        result_payload=result_payload or bundle.result,
    )


def _attached_failure(error: BaseException) -> runner.D7PreparedFailedTerminal:
    value = getattr(error, runner.D7_PREPARED_FAILED_TERMINAL_ATTRIBUTE)
    assert type(value) is runner.D7PreparedFailedTerminal
    return value


def test_zero_argument_producer_prepares_validated_scientific_terminal(
    valid_bundle: component_fixtures._Bundle,
) -> None:
    ownership = _ownership()
    output = _producer_output(valid_bundle)
    calls = 0

    def scientific_producer() -> runner.D7ScientificProducerOutput:
        nonlocal calls
        calls += 1
        return output

    prepared = runner.prepare_d7_post_start_terminal(
        ownership,
        scientific_producer,
    )

    assert calls == 1
    assert type(prepared) is runner.D7PreparedScientificTerminal
    assert prepared.ownership is ownership
    assert prepared.producer_output is output
    assert prepared.scientific_result.replay_target_sha256 == (
        ownership.start.replay_target_sha256
    )
    assert (
        prepared.scientific_result.attempt_key_sha256
        == ownership.start.attempt_key_sha256
    )
    assert (
        prepared.scientific_result.execution_start_sha256
        == ownership.start.canonical_sha256
    )
    assert (
        prepared.scientific_result.execution_identity_receipt_sha256
        == ownership.start.execution_identity_receipt_sha256
    )
    assert (
        prepared.scientific_result.result_payload_sha256
        == output.result_payload.canonical_sha256
    )
    assert prepared.scientific_result.result_payload_byte_count == len(
        output.result_payload.canonical_bytes
    )
    assert not hasattr(prepared, "terminal_manifest")
    assert not hasattr(prepared, "terminal_consumption")
    assert not hasattr(prepared, "publication")
    with pytest.raises(TypeError, match="in-process handoff"):
        pickle.dumps(prepared)


def test_producer_exception_is_re_raised_with_conservative_failure_bundle(
    valid_bundle: component_fixtures._Bundle,
) -> None:
    del valid_bundle
    ownership = _ownership()
    cause = ValueError("private-cause-text")
    original = RuntimeError("private-producer-message")
    original.__cause__ = cause

    def scientific_producer() -> runner.D7ScientificProducerOutput:
        raise original

    with pytest.raises(RuntimeError) as caught:
        runner.prepare_d7_post_start_terminal(
            ownership,
            scientific_producer,
        )

    assert caught.value is original
    assert caught.value.__cause__ is cause
    assert caught.value.__traceback__ is not None
    prepared = _attached_failure(caught.value)
    assert prepared.ownership is ownership
    assert prepared.failure_payload.failure_stage is r.D7FailureStage.EXECUTION_KERNEL
    assert prepared.failure_payload.origin is r.D7FailureEvidenceOrigin.IN_PROCESS
    assert prepared.failure_payload.reason_code == "scientific-producer-exception"
    assert (
        prepared.failure_payload.confirmation_value_access_state
        is r.D7ConfirmationValueAccessState.UNKNOWN
    )
    assert type(prepared.failure_payload.detail) is e.D7InProcessFailureDetail
    assert prepared.failure_payload.detail.exception_class == "builtins.RuntimeError"
    assert prepared.failure_evidence.external_verification_receipt_sha256 is None
    assert prepared.failure_evidence.external_verification_receipt_byte_count is None
    assert prepared.failed_attempt.started_unresolved_finalization_sha256 is None
    assert (
        prepared.failed_attempt.confirmation_value_access_state
        is r.D7ConfirmationValueAccessState.UNKNOWN
    )
    assert b"private-producer-message" not in prepared.failure_payload.canonical_bytes
    assert b"private-cause-text" not in prepared.failure_payload.canonical_bytes
    assert all(
        "private-producer-message" not in note and "private-cause-text" not in note
        for note in caught.value.__notes__
    )
    ev.validate_d7_failure_evidence_payload_chain(
        start=ownership.start,
        payload=prepared.failure_payload,
        evidence=prepared.failure_evidence,
        failed_attempt=prepared.failed_attempt,
    )
    with pytest.raises(TypeError, match="in-process handoff"):
        pickle.dumps(prepared)


def test_complete_bundle_validator_failure_becomes_result_validation_failure(
    valid_bundle: component_fixtures._Bundle,
) -> None:
    ownership = _ownership()
    mismatched_result = replace(
        valid_bundle.result,
        aggregation_sha256=_h("mismatched-aggregation"),
    )
    output = _producer_output(
        valid_bundle,
        result_payload=mismatched_result,
    )

    with pytest.raises(QualificationContractError) as caught:
        runner.prepare_d7_post_start_terminal(ownership, lambda: output)

    prepared = _attached_failure(caught.value)
    assert prepared.failure_payload.failure_stage is r.D7FailureStage.RESULT_VALIDATION
    assert (
        prepared.failure_payload.reason_code == "scientific-result-validation-exception"
    )
    assert prepared.failure_payload.detail.exception_class == (
        "spirallens.qualification.common.QualificationContractError"
    )


def test_replay_target_must_join_private_post_start_ownership(
    valid_bundle: component_fixtures._Bundle,
) -> None:
    ownership = _ownership(_prefix(target=_h("different-target")))
    output = _producer_output(valid_bundle)

    with pytest.raises(
        QualificationContractError,
        match="replay target differs",
    ) as caught:
        runner.prepare_d7_post_start_terminal(ownership, lambda: output)

    assert (
        _attached_failure(caught.value).failure_payload.failure_stage
        is r.D7FailureStage.RESULT_VALIDATION
    )


@pytest.mark.parametrize(
    ("field", "message"),
    (
        ("full_inventory_sha256", "full inventory differs"),
        ("aggregation_sha256", "aggregation differs"),
    ),
)
def test_target_projection_must_join_private_post_start_ownership(
    valid_bundle: component_fixtures._Bundle,
    field: str,
    message: str,
) -> None:
    ownership = _ownership(**{field: _h(f"different-{field}")})
    output = _producer_output(valid_bundle)

    with pytest.raises(QualificationContractError, match=message) as caught:
        runner.prepare_d7_post_start_terminal(ownership, lambda: output)

    assert (
        _attached_failure(caught.value).failure_payload.failure_stage
        is r.D7FailureStage.RESULT_VALIDATION
    )


def test_post_start_ownership_requires_current_result_schema() -> None:
    with pytest.raises(
        QualificationContractError,
        match="current result implementation schema",
    ):
        _ownership(result_schema_sha256=_h("old-result-schema"))


def test_producer_result_schema_must_join_post_start_ownership(
    monkeypatch: pytest.MonkeyPatch,
    valid_bundle: component_fixtures._Bundle,
) -> None:
    ownership = _ownership()
    output = _producer_output(valid_bundle)
    monkeypatch.setattr(
        r.D7ScientificResultPayload,
        "result_schema_sha256",
        _h("producer-old-result-schema"),
    )

    with pytest.raises(
        QualificationContractError,
        match="result schema differs",
    ) as caught:
        runner.prepare_d7_post_start_terminal(ownership, lambda: output)

    assert (
        _attached_failure(caught.value).failure_payload.failure_stage
        is r.D7FailureStage.RESULT_VALIDATION
    )


def test_terminal_preparation_exception_has_exact_stage(
    monkeypatch: pytest.MonkeyPatch,
    valid_bundle: component_fixtures._Bundle,
) -> None:
    ownership = _ownership()
    output = _producer_output(valid_bundle)
    original = RuntimeError("terminal-preparation-detail")

    def fail_terminal_preparation(**values: object) -> None:
        assert values == {
            "ownership": ownership,
            "producer_output": output,
        }
        raise original

    monkeypatch.setattr(
        runner,
        "_prepare_scientific_terminal",
        fail_terminal_preparation,
    )

    with pytest.raises(RuntimeError) as caught:
        runner.prepare_d7_post_start_terminal(ownership, lambda: output)

    assert caught.value is original
    prepared = _attached_failure(caught.value)
    assert (
        prepared.failure_payload.failure_stage is r.D7FailureStage.TERMINAL_PREPARATION
    )
    assert (
        prepared.failure_payload.reason_code
        == "scientific-terminal-preparation-exception"
    )


def test_private_ownership_is_prefix_validated_and_nonserializable() -> None:
    prefix = _prefix()
    with pytest.raises(TypeError, match="private issuer"):
        runner._D7PostStartOwnership(
            prefix.declaration,
            prefix.authorization,
            prefix.claim,
            prefix.start,
            full_inventory_sha256=component_fixtures._INVENTORY,
            aggregation_sha256=component_fixtures._AGGREGATION,
            result_schema_sha256=(r.D7_SCIENTIFIC_RESULT_IMPLEMENTATION_SCHEMA_SHA256),
            _factory_token=object(),
        )

    mismatched_start = replace(
        prefix.start,
        authorization_commit="b" * 40,
    )
    with pytest.raises(QualificationContractError):
        runner._D7PostStartOwnership(
            prefix.declaration,
            prefix.authorization,
            prefix.claim,
            mismatched_start,
            full_inventory_sha256=component_fixtures._INVENTORY,
            aggregation_sha256=component_fixtures._AGGREGATION,
            result_schema_sha256=(r.D7_SCIENTIFIC_RESULT_IMPLEMENTATION_SCHEMA_SHA256),
            _factory_token=runner._POST_START_OWNERSHIP_FACTORY_TOKEN,
        )

    ownership = _ownership(prefix)
    assert not hasattr(ownership, "__dict__")
    assert not hasattr(ownership, "to_dict")
    assert not hasattr(ownership, "canonical_bytes")
    with pytest.raises(AttributeError, match="immutable"):
        ownership._full_inventory_sha256 = _h("mutated-inventory")
    with pytest.raises(AttributeError, match="immutable"):
        del ownership._sealed
    with pytest.raises(TypeError, match="in-process handoff"):
        pickle.dumps(ownership)


def test_prepared_handoffs_are_immutable(
    valid_bundle: component_fixtures._Bundle,
) -> None:
    scientific = runner.prepare_d7_post_start_terminal(
        _ownership(),
        lambda: _producer_output(valid_bundle),
    )
    with pytest.raises(AttributeError, match="immutable"):
        scientific._producer_output = _producer_output(valid_bundle)
    with pytest.raises(AttributeError, match="immutable"):
        scientific._scientific_result = scientific.scientific_result
    with pytest.raises(AttributeError, match="immutable"):
        del scientific._sealed

    error = RuntimeError("immutable-failure-handoff")
    with pytest.raises(RuntimeError) as caught:
        runner.prepare_d7_post_start_terminal(
            _ownership(),
            lambda: (_ for _ in ()).throw(error),
        )
    failed = _attached_failure(caught.value)
    with pytest.raises(AttributeError, match="immutable"):
        failed._failure_payload = failed.failure_payload
    with pytest.raises(AttributeError, match="immutable"):
        del failed._sealed


def test_private_ownership_rejects_isolated_replay_role() -> None:
    primary = _scientific()
    role = r.D7IsolatedReplayRoleEvidence(
        primary.prefix.declaration.replay_target_sha256,
        primary.prefix.declaration.attempt_key_sha256,
        primary.prefix.declaration.canonical_sha256,
        primary.prefix.authorization.canonical_sha256,
        primary.prefix.claim.canonical_sha256,
        primary.prefix.start.canonical_sha256,
        primary.payload.canonical_sha256,
        primary.result.canonical_sha256,
        primary.manifest.canonical_sha256,
        primary.consumption.canonical_sha256,
    )
    isolated = _prefix(
        "isolated",
        target=primary.prefix.declaration.replay_target_sha256,
        role=role,
    )

    with pytest.raises(
        QualificationContractError,
        match="primary confirmation attempt",
    ):
        _ownership(isolated)


def test_mutation_resistant_exception_is_re_raised_unmodified() -> None:
    ownership = _ownership()

    class MutationResistantError(Exception):
        __slots__ = ()

        def __setattr__(self, name: str, value: object) -> None:
            del name, value
            raise RuntimeError("setattr rejected")

        def add_note(self, note: str) -> None:
            del note
            raise RuntimeError("add_note rejected")

    original = MutationResistantError("original must survive")

    def scientific_producer() -> runner.D7ScientificProducerOutput:
        raise original

    with pytest.raises(MutationResistantError) as caught:
        runner.prepare_d7_post_start_terminal(ownership, scientific_producer)

    assert caught.value is original
    assert not hasattr(caught.value, runner.D7_PREPARED_FAILED_TERMINAL_ATTRIBUTE)
    assert not hasattr(caught.value, "__notes__")


def test_add_note_rejection_keeps_original_and_valid_attachment() -> None:
    ownership = _ownership()

    class NoteResistantError(Exception):
        def add_note(self, note: str) -> None:
            del note
            raise RuntimeError("add_note rejected")

    original = NoteResistantError("original must survive")

    with pytest.raises(NoteResistantError) as caught:
        runner.prepare_d7_post_start_terminal(
            ownership,
            lambda: (_ for _ in ()).throw(original),
        )

    assert caught.value is original
    prepared = _attached_failure(caught.value)
    assert prepared.failure_payload.failure_stage is r.D7FailureStage.EXECUTION_KERNEL
    assert not hasattr(caught.value, "__notes__")


def test_hard_crash_like_base_exception_is_not_inferred_as_failure() -> None:
    ownership = _ownership()

    class SimulatedHardCrash(BaseException):
        pass

    original = SimulatedHardCrash("no in-process recovery")

    def scientific_producer() -> runner.D7ScientificProducerOutput:
        raise original

    with pytest.raises(SimulatedHardCrash) as caught:
        runner.prepare_d7_post_start_terminal(ownership, scientific_producer)

    assert caught.value is original
    assert not hasattr(
        caught.value,
        runner.D7_PREPARED_FAILED_TERMINAL_ATTRIBUTE,
    )
    assert not hasattr(caught.value, "__notes__")


def test_runner_surface_has_only_private_post_start_inputs_and_no_public_export() -> (
    None
):
    signature = inspect.signature(runner.prepare_d7_post_start_terminal)
    assert tuple(signature.parameters) == ("ownership", "scientific_producer")
    assert all(
        forbidden not in signature.parameters
        for forbidden in ("supplier", "seed", "start")
    )
    assert runner.__all__ == ()
    assert "prepare_d7_post_start_terminal" not in qualification.__all__
    assert not hasattr(qualification, "prepare_d7_post_start_terminal")
    assert not hasattr(qualification, "D7ScientificProducerOutput")
    assert not hasattr(qualification, "D7PreparedScientificTerminal")
