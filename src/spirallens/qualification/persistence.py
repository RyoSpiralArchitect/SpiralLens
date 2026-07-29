"""Bounded canonical persistence for standalone qualification records."""

from __future__ import annotations

import hashlib
import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from spirallens.core.canonical import CanonicalJsonError, parse_canonical_json

from .common import QualificationContractError
from .contracts import (
    MAX_QUALIFICATION_RESULT_BYTES,
    QualificationResult,
)
from .freeze import (
    SelectionAttemptClaimArtifact,
    SelectionFreezeArtifact,
)
from .protocol import (
    MAX_QUALIFICATION_PROTOCOL_BYTES,
    QualificationProtocol,
    _sha256,
)
from .source_binding import QualificationSourceBindingReceipt


@dataclass(frozen=True, slots=True)
class PersistedQualificationIdentity:
    """Exact identity returned after an atomic publication."""

    path: Path
    source_sha256: str
    canonical_sha256: str
    byte_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.path, Path) or not self.path.is_absolute():
            raise TypeError("path must be an absolute Path")
        _sha256(self.source_sha256, label="source_sha256")
        _sha256(self.canonical_sha256, label="canonical_sha256")
        if type(self.byte_count) is not int or self.byte_count <= 0:
            raise QualificationContractError("byte_count must be a positive integer")


@dataclass(frozen=True, slots=True)
class LoadedQualificationProtocol:
    """A protocol and the exact canonical file from which it was loaded."""

    protocol: QualificationProtocol
    source_path: Path
    source_bytes: bytes
    source_sha256: str
    canonical_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.protocol, QualificationProtocol):
            raise TypeError("protocol must be a QualificationProtocol")
        if not isinstance(self.source_path, Path) or not self.source_path.is_absolute():
            raise TypeError("source_path must be an absolute Path")
        if not isinstance(self.source_bytes, bytes) or not self.source_bytes:
            raise TypeError("source_bytes must be non-empty bytes")
        _sha256(self.source_sha256, label="source_sha256")
        _sha256(self.canonical_sha256, label="canonical_sha256")
        if hashlib.sha256(self.source_bytes).hexdigest() != self.source_sha256:
            raise QualificationContractError(
                "loaded protocol source bytes do not match source_sha256"
            )
        if (
            self.protocol.canonical_bytes != self.source_bytes
            or self.protocol.canonical_sha256 != self.canonical_sha256
        ):
            raise QualificationContractError(
                "loaded protocol differs from its canonical identity"
            )


@dataclass(frozen=True, slots=True)
class LoadedQualificationResult:
    """A result, exact source identity, and all verified pre-run companions."""

    result: QualificationResult
    protocol: LoadedQualificationProtocol
    source_binding_receipt: QualificationSourceBindingReceipt | None
    selection_freeze_artifact: SelectionFreezeArtifact
    selection_attempt_claim: SelectionAttemptClaimArtifact
    selection_launch_authorization_sha256: str | None
    source_path: Path
    source_bytes: bytes
    source_sha256: str
    canonical_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.result, QualificationResult):
            raise TypeError("result must be a QualificationResult")
        if not isinstance(self.protocol, LoadedQualificationProtocol):
            raise TypeError("protocol must be a LoadedQualificationProtocol")
        if self.source_binding_receipt is not None and not isinstance(
            self.source_binding_receipt,
            QualificationSourceBindingReceipt,
        ):
            raise TypeError(
                "source_binding_receipt must be a "
                "QualificationSourceBindingReceipt or None"
            )
        if not isinstance(
            self.selection_freeze_artifact,
            SelectionFreezeArtifact,
        ):
            raise TypeError(
                "selection_freeze_artifact must be a SelectionFreezeArtifact"
            )
        if not isinstance(
            self.selection_attempt_claim,
            SelectionAttemptClaimArtifact,
        ):
            raise TypeError(
                "selection_attempt_claim must be a SelectionAttemptClaimArtifact"
            )
        if not isinstance(self.source_path, Path) or not self.source_path.is_absolute():
            raise TypeError("source_path must be an absolute Path")
        if not isinstance(self.source_bytes, bytes) or not self.source_bytes:
            raise TypeError("source_bytes must be non-empty bytes")
        _sha256(self.source_sha256, label="source_sha256")
        _sha256(self.canonical_sha256, label="canonical_sha256")
        if hashlib.sha256(self.source_bytes).hexdigest() != self.source_sha256:
            raise QualificationContractError(
                "loaded result source bytes do not match source_sha256"
            )
        if (
            self.result.canonical_bytes != self.source_bytes
            or self.result.canonical_sha256 != self.canonical_sha256
        ):
            raise QualificationContractError(
                "loaded result differs from its canonical identity"
            )
        self.result.validate_against_protocol(
            self.protocol.protocol,
            protocol_source_sha256=self.protocol.source_sha256,
            source_binding_receipt=self.source_binding_receipt,
            selection_freeze_artifact=self.selection_freeze_artifact,
            selection_attempt_claim=self.selection_attempt_claim,
            selection_launch_authorization_sha256=(
                self.selection_launch_authorization_sha256
            ),
        )


def _absolute_path(path: str | Path) -> Path:
    value = Path(path)
    return Path(os.path.abspath(value))


def _reject_official_standalone_result_persistence(
    protocol: LoadedQualificationProtocol,
) -> None:
    from .preparation import CLOSED_D0_D5_PROTOCOL_ID

    if protocol.protocol.protocol_id == CLOSED_D0_D5_PROTOCOL_ID:
        raise QualificationContractError(
            "official closed D0-D5 results must use the authorization-lineage "
            "terminal transaction publisher/loader, not standalone result "
            "persistence"
        )


def _read_bounded(path: Path, *, maximum_bytes: int, label: str) -> bytes:
    try:
        with path.open("rb") as handle:
            source = handle.read(maximum_bytes + 1)
    except OSError as error:
        raise QualificationContractError(f"cannot read {label}: {error}") from error
    if len(source) > maximum_bytes:
        raise QualificationContractError(
            f"{label} exceeds the {maximum_bytes}-byte limit"
        )
    if not source:
        raise QualificationContractError(f"{label} must not be empty")
    return source


def _verify_expected_digests(
    source: bytes,
    canonical_sha256: str,
    *,
    expected_source_sha256: str,
    expected_canonical_sha256: str,
    label: str,
) -> str:
    _sha256(expected_source_sha256, label="expected_source_sha256")
    _sha256(expected_canonical_sha256, label="expected_canonical_sha256")
    source_sha256 = hashlib.sha256(source).hexdigest()
    if source_sha256 != expected_source_sha256:
        raise QualificationContractError(
            f"{label} source SHA-256 does not match the expected digest"
        )
    if canonical_sha256 != expected_canonical_sha256:
        raise QualificationContractError(
            f"{label} canonical SHA-256 does not match the expected digest"
        )
    return source_sha256


def _canonical_document(source: bytes, *, label: str) -> Mapping[str, object]:
    try:
        document = parse_canonical_json(source, label=label)
    except CanonicalJsonError as error:
        raise QualificationContractError(str(error)) from error
    if not isinstance(document, Mapping) or any(
        not isinstance(key, str) for key in document
    ):
        raise QualificationContractError(f"{label} must be a canonical JSON object")
    return document


def load_qualification_protocol(
    path: str | Path,
    *,
    expected_source_sha256: str,
    expected_canonical_sha256: str,
) -> LoadedQualificationProtocol:
    """Load one bounded canonical protocol with two mandatory identities."""

    source_path = _absolute_path(path)
    source = _read_bounded(
        source_path,
        maximum_bytes=MAX_QUALIFICATION_PROTOCOL_BYTES,
        label="qualification protocol",
    )
    document = _canonical_document(source, label="qualification protocol")
    protocol = QualificationProtocol.from_dict(document)
    source_sha256 = _verify_expected_digests(
        source,
        protocol.canonical_sha256,
        expected_source_sha256=expected_source_sha256,
        expected_canonical_sha256=expected_canonical_sha256,
        label="qualification protocol",
    )
    return LoadedQualificationProtocol(
        protocol=protocol,
        source_path=source_path,
        source_bytes=source,
        source_sha256=source_sha256,
        canonical_sha256=protocol.canonical_sha256,
    )


def load_qualification_result(
    path: str | Path,
    *,
    protocol: LoadedQualificationProtocol,
    expected_source_sha256: str,
    expected_canonical_sha256: str,
    selection_freeze_artifact: SelectionFreezeArtifact,
    selection_attempt_claim: SelectionAttemptClaimArtifact,
    source_binding_receipt: QualificationSourceBindingReceipt | None = None,
    selection_launch_authorization_sha256: str | None = None,
) -> LoadedQualificationResult:
    """Load a result and verify its exact protocol and pre-run companions."""

    if not isinstance(protocol, LoadedQualificationProtocol):
        raise TypeError("protocol must be a LoadedQualificationProtocol")
    _reject_official_standalone_result_persistence(protocol)
    if not isinstance(selection_freeze_artifact, SelectionFreezeArtifact):
        raise TypeError("selection_freeze_artifact must be a SelectionFreezeArtifact")
    if not isinstance(selection_attempt_claim, SelectionAttemptClaimArtifact):
        raise TypeError(
            "selection_attempt_claim must be a SelectionAttemptClaimArtifact"
        )
    source_path = _absolute_path(path)
    source = _read_bounded(
        source_path,
        maximum_bytes=MAX_QUALIFICATION_RESULT_BYTES,
        label="qualification result",
    )
    document = _canonical_document(source, label="qualification result")
    result = QualificationResult.from_dict(document)
    result.validate_against_protocol(
        protocol.protocol,
        protocol_source_sha256=protocol.source_sha256,
        source_binding_receipt=source_binding_receipt,
        selection_freeze_artifact=selection_freeze_artifact,
        selection_attempt_claim=selection_attempt_claim,
        selection_launch_authorization_sha256=(selection_launch_authorization_sha256),
    )
    source_sha256 = _verify_expected_digests(
        source,
        result.canonical_sha256,
        expected_source_sha256=expected_source_sha256,
        expected_canonical_sha256=expected_canonical_sha256,
        label="qualification result",
    )
    return LoadedQualificationResult(
        result=result,
        protocol=protocol,
        source_binding_receipt=source_binding_receipt,
        selection_freeze_artifact=selection_freeze_artifact,
        selection_attempt_claim=selection_attempt_claim,
        selection_launch_authorization_sha256=(selection_launch_authorization_sha256),
        source_path=source_path,
        source_bytes=source,
        source_sha256=source_sha256,
        canonical_sha256=result.canonical_sha256,
    )


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_write_no_overwrite(
    destination: Path,
    payload: bytes,
    *,
    maximum_bytes: int,
    label: str,
) -> PersistedQualificationIdentity:
    if not payload or len(payload) > maximum_bytes:
        raise QualificationContractError(
            f"{label} must contain 1..{maximum_bytes} canonical bytes"
        )
    parent = destination.parent
    if not parent.is_dir():
        raise QualificationContractError(
            f"{label} parent directory does not exist: {parent}"
        )
    if destination.exists() or destination.is_symlink():
        raise QualificationContractError(
            f"refusing to overwrite existing {label}: {destination}"
        )

    descriptor, temporary_name = tempfile.mkstemp(
        dir=parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    published = False
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, destination)
            published = True
        except FileExistsError as error:
            raise QualificationContractError(
                f"refusing to overwrite existing {label}: {destination}"
            ) from error
        except OSError as error:
            raise QualificationContractError(
                f"cannot atomically publish {label}: {error}"
            ) from error
        _fsync_directory(parent)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        if not published and destination.exists():
            # A successful hard-link is the only operation that can create the
            # destination.  If publication was interrupted after link(2), retain
            # the complete immutable file rather than delete user-visible data.
            published = True

    digest = hashlib.sha256(payload).hexdigest()
    return PersistedQualificationIdentity(
        path=destination,
        source_sha256=digest,
        canonical_sha256=digest,
        byte_count=len(payload),
    )


def write_qualification_protocol(
    path: str | Path,
    protocol: QualificationProtocol,
) -> PersistedQualificationIdentity:
    """Atomically publish one canonical protocol without overwriting."""

    if not isinstance(protocol, QualificationProtocol):
        raise TypeError("protocol must be a QualificationProtocol")
    destination = _absolute_path(path)
    return _atomic_write_no_overwrite(
        destination,
        protocol.canonical_bytes,
        maximum_bytes=MAX_QUALIFICATION_PROTOCOL_BYTES,
        label="qualification protocol",
    )


def write_qualification_result(
    path: str | Path,
    result: QualificationResult,
    *,
    protocol: LoadedQualificationProtocol,
    selection_freeze_artifact: SelectionFreezeArtifact,
    selection_attempt_claim: SelectionAttemptClaimArtifact,
    source_binding_receipt: QualificationSourceBindingReceipt | None = None,
    selection_launch_authorization_sha256: str | None = None,
) -> PersistedQualificationIdentity:
    """Verify all protocol companions, then atomically publish one result."""

    if not isinstance(result, QualificationResult):
        raise TypeError("result must be a QualificationResult")
    if not isinstance(protocol, LoadedQualificationProtocol):
        raise TypeError("protocol must be a LoadedQualificationProtocol")
    _reject_official_standalone_result_persistence(protocol)
    if not isinstance(selection_freeze_artifact, SelectionFreezeArtifact):
        raise TypeError("selection_freeze_artifact must be a SelectionFreezeArtifact")
    if not isinstance(selection_attempt_claim, SelectionAttemptClaimArtifact):
        raise TypeError(
            "selection_attempt_claim must be a SelectionAttemptClaimArtifact"
        )
    result.validate_against_protocol(
        protocol.protocol,
        protocol_source_sha256=protocol.source_sha256,
        source_binding_receipt=source_binding_receipt,
        selection_freeze_artifact=selection_freeze_artifact,
        selection_attempt_claim=selection_attempt_claim,
        selection_launch_authorization_sha256=(selection_launch_authorization_sha256),
    )
    destination = _absolute_path(path)
    return _atomic_write_no_overwrite(
        destination,
        result.canonical_bytes,
        maximum_bytes=MAX_QUALIFICATION_RESULT_BYTES,
        label="qualification result",
    )
