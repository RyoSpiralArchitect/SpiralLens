"""Authenticated external-witness verification for future D7 finalization.

The signed envelope remains evidence, not a serialized capability.  Verification
is relative to an explicitly supplied runtime trust-root pin set and returns a
module-issued, one-shot runtime value.  This module does not issue an
authoritative execution start, write a terminal, authorize D7/D8, supply seeds,
or run an attempt.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass

from spirallens.core.canonical import sha256_bytes

from . import confirmation_attempt_evidence as e
from . import confirmation_attempt_evidence_validation as ev
from . import confirmation_attempt_records as r
from .common import QualificationContractError

__all__: tuple[str, ...] = ()

_VERIFIED_WITNESS_TOKEN = object()


def _exact(value: object, expected: type[object], label: str) -> None:
    if type(value) is not expected:
        raise TypeError(f"{label} must be an exact {expected.__name__}")


def _public_key_bytes(value: object, label: str) -> bytes:
    if type(value) is not bytes or len(value) != 32:
        raise QualificationContractError(
            f"{label} must be exactly 32 raw Ed25519 public-key bytes"
        )
    return value


@dataclass(frozen=True, slots=True)
class D7PinnedExternalWitnessTrustRoot:
    """Explicit runtime pins; construction alone grants no SpiralLens authority."""

    execution_principal_id: str
    execution_identity_receipt_sha256: str
    observer_principal_id: str
    observer_identity_receipt_sha256: str
    observer_public_key: bytes
    verifier_principal_id: str
    verifier_source_runtime_receipt_sha256: str
    verifier_public_key: bytes

    def __post_init__(self) -> None:
        observer_key = _public_key_bytes(
            self.observer_public_key,
            "observer_public_key",
        )
        verifier_key = _public_key_bytes(
            self.verifier_public_key,
            "verifier_public_key",
        )
        if observer_key == verifier_key:
            raise QualificationContractError(
                "observer and verifier public keys must differ"
            )
        # This validates all principal IDs and receipt digests and requires
        # authenticated-principal separation.
        e.d7_external_witness_runtime_trust_root_sha256(
            execution_principal_id=self.execution_principal_id,
            execution_identity_receipt_sha256=(self.execution_identity_receipt_sha256),
            observer_principal_id=self.observer_principal_id,
            observer_identity_receipt_sha256=(self.observer_identity_receipt_sha256),
            observer_public_key_sha256=self.observer_public_key_sha256,
            verifier_principal_id=self.verifier_principal_id,
            verifier_source_runtime_receipt_sha256=(
                self.verifier_source_runtime_receipt_sha256
            ),
            verifier_public_key_sha256=self.verifier_public_key_sha256,
        )

    @property
    def observer_public_key_sha256(self) -> str:
        return sha256_bytes(self.observer_public_key)

    @property
    def verifier_public_key_sha256(self) -> str:
        return sha256_bytes(self.verifier_public_key)

    @property
    def canonical_sha256(self) -> str:
        return e.d7_external_witness_runtime_trust_root_sha256(
            execution_principal_id=self.execution_principal_id,
            execution_identity_receipt_sha256=(self.execution_identity_receipt_sha256),
            observer_principal_id=self.observer_principal_id,
            observer_identity_receipt_sha256=(self.observer_identity_receipt_sha256),
            observer_public_key_sha256=self.observer_public_key_sha256,
            verifier_principal_id=self.verifier_principal_id,
            verifier_source_runtime_receipt_sha256=(
                self.verifier_source_runtime_receipt_sha256
            ),
            verifier_public_key_sha256=self.verifier_public_key_sha256,
        )


class VerifiedD7ExternalAbortWitness:
    """One-shot authenticated witness result with no serialized representation."""

    __slots__ = (
        "_consumption_lock",
        "_consumption_state",
        "_envelope",
        "_envelope_canonical_bytes",
        "_envelope_sha256",
        "_sealed",
        "_token",
        "_trust_root",
    )

    def __init__(
        self,
        *,
        token: object,
        envelope: e.D7SignedExternalAbortWitnessEnvelope,
        trust_root: D7PinnedExternalWitnessTrustRoot,
    ) -> None:
        if token is not _VERIFIED_WITNESS_TOKEN:
            raise TypeError(
                "VerifiedD7ExternalAbortWitness cannot be constructed directly"
            )
        _exact(
            envelope,
            e.D7SignedExternalAbortWitnessEnvelope,
            "envelope",
        )
        _exact(
            trust_root,
            D7PinnedExternalWitnessTrustRoot,
            "trust_root",
        )
        object.__setattr__(self, "_token", token)
        object.__setattr__(self, "_envelope", envelope)
        object.__setattr__(
            self,
            "_envelope_canonical_bytes",
            bytes(envelope.canonical_bytes),
        )
        object.__setattr__(
            self,
            "_envelope_sha256",
            envelope.canonical_sha256,
        )
        object.__setattr__(self, "_trust_root", trust_root)
        object.__setattr__(self, "_consumption_lock", threading.Lock())
        object.__setattr__(self, "_consumption_state", "available")
        object.__setattr__(self, "_sealed", True)

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("VerifiedD7ExternalAbortWitness cannot be subclassed")

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("VerifiedD7ExternalAbortWitness is immutable")
        object.__setattr__(self, name, value)

    def __copy__(self) -> None:
        raise TypeError("verified D7 witness results cannot be copied")

    def __deepcopy__(self, memo: object) -> None:
        raise TypeError("verified D7 witness results cannot be copied")

    def __reduce_ex__(self, protocol: int) -> None:
        raise TypeError("verified D7 witness results cannot be serialized")

    def _require_valid(self) -> None:
        if self._token is not _VERIFIED_WITNESS_TOKEN:
            raise TypeError("verified D7 witness result is invalid")

    @property
    def envelope_canonical_bytes(self) -> bytes:
        self._require_valid()
        return self._envelope_canonical_bytes

    @property
    def envelope_sha256(self) -> str:
        self._require_valid()
        return self._envelope_sha256

    @property
    def observer_public_key_sha256(self) -> str:
        self._require_valid()
        return self._trust_root.observer_public_key_sha256

    @property
    def verifier_public_key_sha256(self) -> str:
        self._require_valid()
        return self._trust_root.verifier_public_key_sha256

    @property
    def runtime_trust_root_sha256(self) -> str:
        self._require_valid()
        return self._trust_root.canonical_sha256

    @property
    def replay_target_sha256(self) -> str:
        self._require_valid()
        return self._envelope.statement.replay_target_sha256

    @property
    def attempt_key_sha256(self) -> str:
        self._require_valid()
        return self._envelope.statement.attempt_key_sha256

    @property
    def execution_start_sha256(self) -> str:
        self._require_valid()
        return self._envelope.statement.execution_start_sha256

    @property
    def execution_identity_receipt_sha256(self) -> str:
        self._require_valid()
        return self._envelope.statement.execution_identity_receipt_sha256

    @property
    def failure_evidence_payload_sha256(self) -> str:
        self._require_valid()
        return self._envelope.statement.failure_evidence_payload_sha256

    @property
    def structural_verification_receipt_sha256(self) -> str:
        self._require_valid()
        return self._envelope.statement.structural_verification_receipt_sha256

    @property
    def store_identity_sha256(self) -> str:
        self._require_valid()
        return self._envelope.statement.store_identity_sha256

    @property
    def terminal_path_identity_sha256(self) -> str:
        self._require_valid()
        return self._envelope.statement.terminal_path_identity_sha256

    @property
    def store_root_realpath(self) -> str:
        self._require_valid()
        return self._envelope.statement.store_root_realpath

    @property
    def terminal_parent_realpath(self) -> str:
        self._require_valid()
        return self._envelope.statement.terminal_parent_realpath

    @property
    def terminal_basename(self) -> str:
        self._require_valid()
        return self._envelope.statement.terminal_basename

    @property
    def terminal_parent_device(self) -> int:
        self._require_valid()
        return self._envelope.statement.terminal_parent_device

    @property
    def terminal_parent_inode(self) -> int:
        self._require_valid()
        return self._envelope.statement.terminal_parent_inode

    @property
    def is_consumed(self) -> bool:
        self._require_valid()
        with self._consumption_lock:
            return self._consumption_state != "available"

    def consume(
        self,
        *,
        revalidate: Callable[["VerifiedD7ExternalAbortWitness"], None],
    ) -> None:
        """Run consumer-owned live checks once, then permanently consume the result."""

        self._require_valid()
        if not callable(revalidate):
            raise TypeError("revalidate must be callable")
        with self._consumption_lock:
            if self._consumption_state != "available":
                raise QualificationContractError(
                    "verified D7 witness result is already consumed"
                )
            object.__setattr__(self, "_consumption_state", "revalidating")
        try:
            result = revalidate(self)
            if result is not None:
                raise TypeError(
                    "witness revalidation must raise on failure and return None"
                )
        finally:
            with self._consumption_lock:
                object.__setattr__(self, "_consumption_state", "consumed")


def _verify_ed25519_signature(
    *,
    public_key: bytes,
    signature: str,
    signed_bytes: bytes,
    label: str,
) -> None:
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey,
        )
    except ImportError as error:
        raise QualificationContractError(
            "Ed25519 verification requires the optional cryptography package"
        ) from error

    try:
        key = Ed25519PublicKey.from_public_bytes(public_key)
        key.verify(bytes.fromhex(signature), signed_bytes)
    except (InvalidSignature, ValueError) as error:
        raise QualificationContractError(f"{label} is invalid") from error


def verify_d7_signed_external_abort_witness(
    *,
    envelope_source: bytes,
    expected_envelope_sha256: str,
    trust_root: D7PinnedExternalWitnessTrustRoot,
    declaration: r.D7AttemptDeclarationRecord,
    start: r.D7ExecutionStartRecord,
    terminal_path_receipt: e.D7PreStartPathAbsenceReceipt,
    payload: e.D7FailureEvidencePayload,
    structural_receipt: e.D7ExternalAbortVerificationReceipt,
) -> VerifiedD7ExternalAbortWitness:
    """Authenticate exact signed bytes relative to explicit runtime pins.

    The returned value authenticates the witness only.  It is not an
    authoritative start, terminal-finalization permission, or D7/D8 authority.
    """

    # The byte digest and canonical encoding are checked before any semantic
    # join, trust-root comparison, public-key construction, or signature work.
    envelope = e.D7SignedExternalAbortWitnessEnvelope.from_canonical_bytes(
        envelope_source,
        expected_sha256=expected_envelope_sha256,
    )
    _exact(
        trust_root,
        D7PinnedExternalWitnessTrustRoot,
        "trust_root",
    )
    ev.validate_d7_signed_external_abort_witness_envelope(
        declaration=declaration,
        start=start,
        terminal_path_receipt=terminal_path_receipt,
        payload=payload,
        structural_receipt=structural_receipt,
        envelope=envelope,
    )
    statement = envelope.statement
    for expected, observed, label in (
        (
            trust_root.canonical_sha256,
            statement.runtime_trust_root_sha256,
            "runtime trust root",
        ),
        (
            trust_root.execution_principal_id,
            statement.execution_principal_id,
            "execution principal",
        ),
        (
            trust_root.execution_identity_receipt_sha256,
            statement.execution_identity_receipt_sha256,
            "execution identity receipt",
        ),
        (
            trust_root.observer_principal_id,
            statement.observer_principal_id,
            "observer principal",
        ),
        (
            trust_root.observer_identity_receipt_sha256,
            statement.observer_identity_receipt_sha256,
            "observer identity receipt",
        ),
        (
            trust_root.observer_public_key_sha256,
            statement.observer_public_key_sha256,
            "observer public key",
        ),
        (
            trust_root.verifier_principal_id,
            statement.verifier_principal_id,
            "verifier principal",
        ),
        (
            trust_root.verifier_source_runtime_receipt_sha256,
            statement.verifier_source_runtime_receipt_sha256,
            "verifier source/runtime receipt",
        ),
        (
            trust_root.verifier_public_key_sha256,
            statement.verifier_public_key_sha256,
            "verifier public key",
        ),
    ):
        if type(expected) is not type(observed) or expected != observed:
            raise QualificationContractError(f"signed witness {label} differs")
    _verify_ed25519_signature(
        public_key=trust_root.observer_public_key,
        signature=envelope.observer_signature,
        signed_bytes=envelope.observer_signed_bytes,
        label="external observer signature",
    )
    _verify_ed25519_signature(
        public_key=trust_root.verifier_public_key,
        signature=envelope.verifier_signature,
        signed_bytes=envelope.verifier_signed_bytes,
        label="independent verifier signature",
    )
    return VerifiedD7ExternalAbortWitness(
        token=_VERIFIED_WITNESS_TOKEN,
        envelope=envelope,
        trust_root=trust_root,
    )
