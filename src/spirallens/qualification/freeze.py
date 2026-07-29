"""One-way freeze and terminal-consumption artifacts for D0--D5 selection.

These records describe access chronology only.  They contain no field, core,
loop, graph, oracle, verdict, subject, or semantic value.  A frozen selection
starts in the explicit ``unopened`` state.  Any result publication or failed
attempt consumes that frozen family terminally; reopening and retry authority
remain false.
"""

from __future__ import annotations

import ctypes
import errno
import hashlib
import os
import re
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import ClassVar

from spirallens.core.canonical import (
    CanonicalJsonError,
    canonical_json_bytes,
    canonical_json_sha256,
    parse_canonical_json,
)

from .common import QualificationContractError
from .protocol import PreseedReadinessBinding

SELECTION_FREEZE_SCHEMA_VERSION = "spirallens.selection-freeze.v0.3"
SELECTION_CONSUMPTION_SCHEMA_VERSION = "spirallens.selection-consumption.v0.2"
SELECTION_FAILED_ATTEMPT_SCHEMA_VERSION = "spirallens.selection-failed-attempt.v0.2"
SELECTION_ATTEMPT_CLAIM_SCHEMA_VERSION = "spirallens.selection-attempt-claim.v0.3"
SELECTION_EXECUTION_START_SCHEMA_VERSION = "spirallens.selection-execution-start.v0.2"
SELECTION_TERMINAL_MANIFEST_SCHEMA_VERSION = (
    "spirallens.selection-terminal-manifest.v0.1"
)
SEED_FAMILY_COMMITMENT_SCHEME = "spirallens.seed-family-commitment.v0.1"
SELECTION_ATTEMPT_KEY_SCHEME = "spirallens.selection-attempt-key.v0.1"
MAX_SELECTION_CHRONOLOGY_ARTIFACT_BYTES = 64 * 1024
MAX_SELECTION_TERMINAL_ARTIFACT_BYTES = 32 * 1024 * 1024
SELECTION_FREEZE_STORE_SUFFIX = ".selection-freeze.json"
SELECTION_ATTEMPT_CLAIM_SUFFIX = ".selection-attempt-claim.json"
SELECTION_EXECUTION_START_SUFFIX = ".selection-execution-start.json"
SELECTION_TERMINAL_TRANSACTION_SUFFIX = ".selection-terminal"
SELECTION_TERMINAL_ARTIFACT_FILENAME = "terminal-artifact.json"
SELECTION_TERMINAL_CONSUMPTION_FILENAME = "selection-consumption.json"
SELECTION_TERMINAL_MANIFEST_FILENAME = "terminal-manifest.json"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_HISTORICAL_SOURCE_RELOAD_CAPABILITY = object()


class SelectionAccessState(str, Enum):
    """Closed pre/post access states; there is no reusable opened state."""

    UNOPENED = "unopened"
    TERMINALLY_CONSUMED = "terminally_consumed"


class TerminalAttemptArtifactKind(str, Enum):
    """What immutable artifact closes the one allowed selection attempt."""

    RESULT = "result"
    FAILED_ATTEMPT = "failed_attempt"


def _mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise QualificationContractError(f"{label} must be a string-keyed mapping")
    return value


def _exact_keys(
    value: Mapping[str, object],
    expected: frozenset[str],
    *,
    label: str,
) -> None:
    actual = set(value)
    if actual != set(expected):
        raise QualificationContractError(
            f"{label} fields differ from the contract: "
            f"missing={sorted(set(expected) - actual)}, "
            f"unknown={sorted(actual - set(expected))}"
        )


def _string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise QualificationContractError(f"{label} must be a non-empty trimmed string")
    return value


def _slug(value: object, *, label: str) -> str:
    result = _string(value, label=label)
    if _SLUG.fullmatch(result) is None:
        raise QualificationContractError(f"{label} must be a lowercase portable slug")
    return result


def _sha256(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise QualificationContractError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _launch_authorization_sha256(
    value: object,
    *,
    protocol_id: str,
    label: str,
) -> str | None:
    """Validate optional lineage, requiring it for the official protocol."""

    authorization_sha256 = None if value is None else _sha256(value, label=label)
    from .preparation import CLOSED_D0_D5_PROTOCOL_ID

    if protocol_id == CLOSED_D0_D5_PROTOCOL_ID and authorization_sha256 is None:
        raise QualificationContractError(
            f"{label} is required for the official closed D0-D5 protocol"
        )
    if protocol_id != CLOSED_D0_D5_PROTOCOL_ID and authorization_sha256 is not None:
        raise QualificationContractError(
            f"{label} must be None for custom/development protocols"
        )
    return authorization_sha256


def _authorized_head_commit(
    value: object,
    *,
    protocol_id: str,
    label: str,
) -> str | None:
    from .preparation import CLOSED_D0_D5_PROTOCOL_ID

    if protocol_id == CLOSED_D0_D5_PROTOCOL_ID:
        if value is None:
            raise QualificationContractError(
                f"{label} is required for the official closed D0-D5 protocol"
            )
        return _commit(value, label=label)
    if value is not None:
        raise QualificationContractError(
            f"{label} must be None for custom/development protocols"
        )
    return None


def _commit(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _COMMIT.fullmatch(value) is None:
        raise QualificationContractError(
            f"{label} must be a lowercase 40-character Git commit"
        )
    return value


def _plain_int(value: object, *, label: str, minimum: int) -> int:
    if type(value) is not int or value < minimum:
        raise QualificationContractError(
            f"{label} must be an integer of at least {minimum}"
        )
    return value


def _plain_bool(value: object, *, label: str) -> bool:
    if type(value) is not bool:
        raise QualificationContractError(f"{label} must be a boolean")
    return value


def _constant(value: object, expected: object, *, label: str) -> object:
    if type(value) is not type(expected) or value != expected:
        raise QualificationContractError(f"{label} must equal {expected!r}")
    return value


def _enum(
    enum_type: type[Enum],
    value: object,
    *,
    label: str,
) -> Enum:
    if not isinstance(value, str):
        raise QualificationContractError(f"{label} must be a string")
    try:
        return enum_type(value)
    except ValueError as error:
        raise QualificationContractError(f"{label} is not supported") from error


def seed_family_commitment_sha256(
    *,
    seed_family_id: str,
    seeds: tuple[int, ...],
) -> str:
    """Commit to one canonical, finite seed family without running it."""

    family_id = _slug(seed_family_id, label="seed_family_id")
    if not seeds:
        raise QualificationContractError("seed family must not be empty")
    for index, seed in enumerate(seeds):
        _plain_int(seed, label=f"seed family seed[{index}]", minimum=0)
    if len(set(seeds)) != len(seeds) or seeds != tuple(sorted(seeds)):
        raise QualificationContractError(
            "seed family seeds must be unique and in canonical order"
        )
    return canonical_json_sha256(
        {
            "scheme": SEED_FAMILY_COMMITMENT_SCHEME,
            "seed_family_id": family_id,
            "seeds": list(seeds),
        }
    )


def selection_attempt_key_sha256(freeze: SelectionFreezeArtifact) -> str:
    """Derive the label-independent identity of one store-local attempt.

    ``freeze_id``, ``seed_family_id``, and caller-chosen claim labels are
    intentionally absent.  Exact canonical protocol bytes already bind the
    seed values and every selection choice, while the explicit selection
    manifest and engine commit make the intended uniqueness boundary easy to
    audit.
    """

    if not isinstance(freeze, SelectionFreezeArtifact):
        raise TypeError("freeze must be a SelectionFreezeArtifact")
    return canonical_json_sha256(
        {
            "scheme": SELECTION_ATTEMPT_KEY_SCHEME,
            "protocol_source_sha256": freeze.protocol_source_sha256,
            "protocol_canonical_sha256": freeze.protocol_canonical_sha256,
            "engine_commit": freeze.engine_commit,
            "selection_manifest_sha256": freeze.selection_manifest_sha256,
            "seed_family_size": freeze.seed_family_size,
        }
    )


@dataclass(frozen=True, slots=True)
class PersistedSelectionIdentity:
    """Exact identity of one no-overwrite chronology publication."""

    path: Path
    source_sha256: str
    canonical_sha256: str
    byte_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.path, Path) or not self.path.is_absolute():
            raise TypeError("path must be an absolute Path")
        _sha256(self.source_sha256, label="source_sha256")
        _sha256(self.canonical_sha256, label="canonical_sha256")
        _plain_int(self.byte_count, label="byte_count", minimum=1)


@dataclass(frozen=True, slots=True)
class PersistedSelectionTerminalIdentity:
    """Identity of one atomically visible terminal transaction directory."""

    path: Path
    manifest_sha256: str
    terminal_artifact_sha256: str
    consumption_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.path, Path) or not self.path.is_absolute():
            raise TypeError("path must be an absolute Path")
        for name in (
            "manifest_sha256",
            "terminal_artifact_sha256",
            "consumption_sha256",
        ):
            _sha256(getattr(self, name), label=name)


@dataclass(frozen=True, slots=True)
class SelectionLaunchIntentBinding:
    """Exact persisted launch-intent identity required by an official claim."""

    path: str
    source_sha256: str
    canonical_sha256: str
    byte_count: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.path, str)
            or not self.path
            or not Path(self.path).is_absolute()
            or str(_absolute_path(self.path)) != self.path
        ):
            raise QualificationContractError(
                "launch intent binding path must be normalized and absolute"
            )
        _sha256(self.source_sha256, label="launch intent binding source_sha256")
        _sha256(
            self.canonical_sha256,
            label="launch intent binding canonical_sha256",
        )
        _plain_int(
            self.byte_count,
            label="launch intent binding byte_count",
            minimum=1,
        )
        if self.source_sha256 != self.canonical_sha256:
            raise QualificationContractError(
                "launch intent binding must identify exact canonical source bytes"
            )
        if self.byte_count > MAX_SELECTION_CHRONOLOGY_ARTIFACT_BYTES:
            raise QualificationContractError(
                "launch intent binding byte_count exceeds the chronology cap"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "source_sha256": self.source_sha256,
            "canonical_sha256": self.canonical_sha256,
            "byte_count": self.byte_count,
        }

    @property
    def identity_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> SelectionLaunchIntentBinding:
        item = _mapping(value, label="selection launch intent binding")
        _exact_keys(
            item,
            frozenset({"path", "source_sha256", "canonical_sha256", "byte_count"}),
            label="selection launch intent binding",
        )
        return cls(
            path=_string(item["path"], label="launch intent binding path"),
            source_sha256=_sha256(
                item["source_sha256"],
                label="launch intent binding source_sha256",
            ),
            canonical_sha256=_sha256(
                item["canonical_sha256"],
                label="launch intent binding canonical_sha256",
            ),
            byte_count=_plain_int(
                item["byte_count"],
                label="launch intent binding byte_count",
                minimum=1,
            ),
        )


def _absolute_path(path: str | Path) -> Path:
    return Path(os.path.abspath(Path(path)))


def _atomic_write_no_overwrite(
    path: str | Path,
    payload: bytes,
    *,
    label: str,
) -> PersistedSelectionIdentity:
    destination = _absolute_path(path)
    if (
        not isinstance(payload, bytes)
        or not payload
        or len(payload) > MAX_SELECTION_CHRONOLOGY_ARTIFACT_BYTES
    ):
        raise QualificationContractError(
            f"{label} must contain 1.."
            f"{MAX_SELECTION_CHRONOLOGY_ARTIFACT_BYTES} canonical bytes"
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
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError as error:
            raise QualificationContractError(
                f"refusing to overwrite existing {label}: {destination}"
            ) from error
        except OSError as error:
            raise QualificationContractError(
                f"cannot atomically publish {label}: {error}"
            ) from error
        directory_flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            directory_flags |= os.O_DIRECTORY
        directory_descriptor = os.open(parent, directory_flags)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    digest = hashlib.sha256(payload).hexdigest()
    return PersistedSelectionIdentity(
        path=destination,
        source_sha256=digest,
        canonical_sha256=digest,
        byte_count=len(payload),
    )


def _load_canonical_mapping(
    path: str | Path,
    *,
    label: str,
) -> tuple[Path, bytes, Mapping[str, object]]:
    return _load_bounded_canonical_mapping(
        path,
        label=label,
        maximum_bytes=MAX_SELECTION_CHRONOLOGY_ARTIFACT_BYTES,
    )


def _load_bounded_canonical_mapping(
    path: str | Path,
    *,
    label: str,
    maximum_bytes: int,
) -> tuple[Path, bytes, Mapping[str, object]]:
    source_path = _absolute_path(path)
    _plain_int(maximum_bytes, label="maximum_bytes", minimum=1)
    if source_path.is_symlink():
        raise QualificationContractError(f"{label} must not be a symbolic link")
    try:
        with source_path.open("rb") as handle:
            source = handle.read(maximum_bytes + 1)
    except OSError as error:
        raise QualificationContractError(f"cannot read {label}: {error}") from error
    if not source or len(source) > maximum_bytes:
        raise QualificationContractError(
            f"{label} must contain 1..{maximum_bytes} bytes"
        )
    try:
        document = parse_canonical_json(source, label=label)
    except CanonicalJsonError as error:
        raise QualificationContractError(str(error)) from error
    mapping = _mapping(document, label=label)
    return source_path, source, mapping


def _fsync_directory(path: Path) -> None:
    directory_flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        directory_flags |= os.O_DIRECTORY
    descriptor = os.open(path, directory_flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_exclusive_file(
    path: Path,
    payload: bytes,
    *,
    label: str,
    maximum_bytes: int,
) -> None:
    if not isinstance(payload, bytes) or not payload or len(payload) > maximum_bytes:
        raise QualificationContractError(
            f"{label} must contain 1..{maximum_bytes} canonical bytes"
        )
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as error:
        raise QualificationContractError(
            f"refusing to overwrite existing {label}: {path}"
        ) from error
    except OSError as error:
        raise QualificationContractError(f"cannot write {label}: {error}") from error


def _rename_directory_no_replace(source: Path, destination: Path) -> None:
    """Atomically publish a directory while refusing destination replacement.

    Python's portable ``os.rename`` permits replacing an empty destination
    directory after a time-of-check/time-of-use race.  The qualification
    terminal transaction therefore uses the platform's exclusive rename
    primitive and fails closed where no such primitive is available.
    """

    if source.parent != destination.parent:
        raise QualificationContractError(
            "terminal transaction staging and destination must share a parent"
        )
    libc = ctypes.CDLL(None, use_errno=True)
    at_fdcwd = -2
    source_bytes = os.fsencode(source)
    destination_bytes = os.fsencode(destination)
    if sys.platform == "darwin":
        try:
            rename_exclusive = libc.renameatx_np
        except AttributeError as error:
            raise QualificationContractError(
                "exclusive terminal-directory rename is unavailable"
            ) from error
        rename_exclusive.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        rename_exclusive.restype = ctypes.c_int
        result = rename_exclusive(
            at_fdcwd,
            source_bytes,
            at_fdcwd,
            destination_bytes,
            0x00000004,  # RENAME_EXCL from Darwin <sys/stdio.h>.
        )
    elif sys.platform.startswith("linux"):
        try:
            rename_exclusive = libc.renameat2
        except AttributeError as error:
            raise QualificationContractError(
                "exclusive terminal-directory rename is unavailable"
            ) from error
        rename_exclusive.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        rename_exclusive.restype = ctypes.c_int
        result = rename_exclusive(
            at_fdcwd,
            source_bytes,
            at_fdcwd,
            destination_bytes,
            0x00000001,  # RENAME_NOREPLACE from Linux <linux/fs.h>.
        )
    else:
        raise QualificationContractError(
            "exclusive terminal-directory rename is unsupported on this platform"
        )
    if result == 0:
        return
    error_number = ctypes.get_errno()
    if error_number in {errno.EEXIST, errno.ENOTEMPTY}:
        raise QualificationContractError(
            "refusing to overwrite existing selection terminal transaction: "
            f"{destination}"
        )
    raise QualificationContractError(
        "cannot atomically publish selection terminal transaction: "
        f"{os.strerror(error_number)}"
    )


@dataclass(frozen=True, slots=True)
class SelectionFreezeArtifact:
    """Pre-execution commitment with procedural external-access attestations.

    The access facts are not cryptographic proof of a negative.  Their force
    comes from publishing this exact canonical artifact, without overwrite,
    before the separately controlled selection process begins.
    """

    freeze_id: str
    protocol_id: str
    protocol_source_sha256: str
    protocol_canonical_sha256: str
    engine_commit: str
    preseed_readiness: PreseedReadinessBinding | None
    selection_manifest_sha256: str
    seed_family_id: str
    seed_family_size: int
    seed_family_commitment_sha256: str
    schema_version: str = SELECTION_FREEZE_SCHEMA_VERSION
    role: str = "calibration_selection_freeze"
    claim_ceiling: str = "level_0"
    access_state: SelectionAccessState = SelectionAccessState.UNOPENED
    attested_selection_values_observed: bool = False
    attested_prior_selection_family_accessed: bool = False
    attested_confirmation_accessed: bool = False
    access_facts_are_external_attestations: bool = True
    cryptographic_access_proof: bool = False
    selection_execution_started: bool = False
    terminally_consumed: bool = False
    reopen_authorized: bool = False
    retry_authorized: bool = False

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "freeze_id",
            "role",
            "claim_ceiling",
            "protocol_id",
            "protocol_source_sha256",
            "protocol_canonical_sha256",
            "engine_commit",
            "preseed_readiness",
            "selection_manifest_sha256",
            "seed_family_id",
            "seed_family_size",
            "seed_family_commitment_sha256",
            "access_state",
            "attested_selection_values_observed",
            "attested_prior_selection_family_accessed",
            "attested_confirmation_accessed",
            "access_facts_are_external_attestations",
            "cryptographic_access_proof",
            "selection_execution_started",
            "terminally_consumed",
            "reopen_authorized",
            "retry_authorized",
        }
    )

    def __post_init__(self) -> None:
        _constant(
            self.schema_version,
            SELECTION_FREEZE_SCHEMA_VERSION,
            label="schema_version",
        )
        _slug(self.freeze_id, label="freeze_id")
        _constant(self.role, "calibration_selection_freeze", label="role")
        _constant(self.claim_ceiling, "level_0", label="claim_ceiling")
        _slug(self.protocol_id, label="protocol_id")
        for name in (
            "protocol_source_sha256",
            "protocol_canonical_sha256",
            "selection_manifest_sha256",
            "seed_family_commitment_sha256",
        ):
            _sha256(getattr(self, name), label=name)
        _commit(self.engine_commit, label="engine_commit")
        if self.preseed_readiness is not None:
            if not isinstance(self.preseed_readiness, PreseedReadinessBinding):
                raise TypeError(
                    "preseed_readiness must be a PreseedReadinessBinding or None"
                )
            if self.preseed_readiness.engine_commit != self.engine_commit:
                raise QualificationContractError(
                    "freeze preseed readiness differs from engine_commit"
                )
        _slug(self.seed_family_id, label="seed_family_id")
        _plain_int(self.seed_family_size, label="seed_family_size", minimum=1)
        if self.access_state is not SelectionAccessState.UNOPENED:
            raise QualificationContractError(
                "a freeze artifact access_state must be unopened"
            )
        for name in (
            "attested_selection_values_observed",
            "attested_prior_selection_family_accessed",
            "attested_confirmation_accessed",
            "selection_execution_started",
            "terminally_consumed",
            "reopen_authorized",
            "retry_authorized",
        ):
            _constant(getattr(self, name), False, label=name)
        _constant(
            self.access_facts_are_external_attestations,
            True,
            label="access_facts_are_external_attestations",
        )
        _constant(
            self.cryptographic_access_proof,
            False,
            label="cryptographic_access_proof",
        )
        if self.protocol_source_sha256 != self.protocol_canonical_sha256:
            raise QualificationContractError(
                "a freeze must bind exact canonical protocol source bytes"
            )
        if len(self.canonical_bytes) > MAX_SELECTION_CHRONOLOGY_ARTIFACT_BYTES:
            raise QualificationContractError(
                "selection freeze artifact exceeds the fixed byte cap"
            )

    @classmethod
    def from_loaded_protocol(
        cls,
        *,
        freeze_id: str,
        loaded_protocol: object,
        seed_family_id: str,
    ) -> SelectionFreezeArtifact:
        # Local import avoids coupling persistence back to chronology records.
        from .persistence import LoadedQualificationProtocol

        if not isinstance(loaded_protocol, LoadedQualificationProtocol):
            raise TypeError("loaded_protocol must be a LoadedQualificationProtocol")
        protocol = loaded_protocol.protocol
        if loaded_protocol.source_bytes != protocol.canonical_bytes:
            raise QualificationContractError(
                "loaded protocol source bytes are not the canonical protocol"
            )
        return cls(
            freeze_id=freeze_id,
            protocol_id=protocol.protocol_id,
            protocol_source_sha256=loaded_protocol.source_sha256,
            protocol_canonical_sha256=protocol.canonical_sha256,
            engine_commit=protocol.engine.commit,
            preseed_readiness=protocol.preseed_readiness,
            selection_manifest_sha256=canonical_json_sha256(
                protocol.selection.to_dict()
            ),
            seed_family_id=seed_family_id,
            seed_family_size=len(protocol.selection.seeds),
            seed_family_commitment_sha256=seed_family_commitment_sha256(
                seed_family_id=seed_family_id,
                seeds=protocol.selection.seeds,
            ),
        )

    def validate_loaded_protocol(
        self,
        *,
        loaded_protocol: object,
    ) -> None:
        expected = SelectionFreezeArtifact.from_loaded_protocol(
            freeze_id=self.freeze_id,
            loaded_protocol=loaded_protocol,
            seed_family_id=self.seed_family_id,
        )
        if self != expected:
            raise QualificationContractError(
                "selection freeze artifact does not match the exact protocol"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "freeze_id": self.freeze_id,
            "role": self.role,
            "claim_ceiling": self.claim_ceiling,
            "protocol_id": self.protocol_id,
            "protocol_source_sha256": self.protocol_source_sha256,
            "protocol_canonical_sha256": self.protocol_canonical_sha256,
            "engine_commit": self.engine_commit,
            "preseed_readiness": (
                None
                if self.preseed_readiness is None
                else self.preseed_readiness.to_dict()
            ),
            "selection_manifest_sha256": self.selection_manifest_sha256,
            "seed_family_id": self.seed_family_id,
            "seed_family_size": self.seed_family_size,
            "seed_family_commitment_sha256": (self.seed_family_commitment_sha256),
            "access_state": self.access_state.value,
            "attested_selection_values_observed": (
                self.attested_selection_values_observed
            ),
            "attested_prior_selection_family_accessed": (
                self.attested_prior_selection_family_accessed
            ),
            "attested_confirmation_accessed": (self.attested_confirmation_accessed),
            "access_facts_are_external_attestations": (
                self.access_facts_are_external_attestations
            ),
            "cryptographic_access_proof": self.cryptographic_access_proof,
            "selection_execution_started": self.selection_execution_started,
            "terminally_consumed": self.terminally_consumed,
            "reopen_authorized": self.reopen_authorized,
            "retry_authorized": self.retry_authorized,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> SelectionFreezeArtifact:
        item = _mapping(value, label="selection freeze artifact")
        _exact_keys(item, cls._ROOT_KEYS, label="selection freeze artifact")
        return cls(
            schema_version=_constant(
                item["schema_version"],
                SELECTION_FREEZE_SCHEMA_VERSION,
                label="schema_version",
            ),  # type: ignore[arg-type]
            freeze_id=_slug(item["freeze_id"], label="freeze_id"),
            role=_constant(
                item["role"],
                "calibration_selection_freeze",
                label="role",
            ),  # type: ignore[arg-type]
            claim_ceiling=_constant(
                item["claim_ceiling"],
                "level_0",
                label="claim_ceiling",
            ),  # type: ignore[arg-type]
            protocol_id=_slug(item["protocol_id"], label="protocol_id"),
            protocol_source_sha256=_sha256(
                item["protocol_source_sha256"],
                label="protocol_source_sha256",
            ),
            protocol_canonical_sha256=_sha256(
                item["protocol_canonical_sha256"],
                label="protocol_canonical_sha256",
            ),
            engine_commit=_commit(item["engine_commit"], label="engine_commit"),
            preseed_readiness=(
                None
                if item["preseed_readiness"] is None
                else PreseedReadinessBinding.from_dict(item["preseed_readiness"])
            ),
            selection_manifest_sha256=_sha256(
                item["selection_manifest_sha256"],
                label="selection_manifest_sha256",
            ),
            seed_family_id=_slug(
                item["seed_family_id"],
                label="seed_family_id",
            ),
            seed_family_size=_plain_int(
                item["seed_family_size"],
                label="seed_family_size",
                minimum=1,
            ),
            seed_family_commitment_sha256=_sha256(
                item["seed_family_commitment_sha256"],
                label="seed_family_commitment_sha256",
            ),
            access_state=_enum(
                SelectionAccessState,
                item["access_state"],
                label="access_state",
            ),  # type: ignore[arg-type]
            attested_selection_values_observed=_plain_bool(
                item["attested_selection_values_observed"],
                label="attested_selection_values_observed",
            ),
            attested_prior_selection_family_accessed=_plain_bool(
                item["attested_prior_selection_family_accessed"],
                label="attested_prior_selection_family_accessed",
            ),
            attested_confirmation_accessed=_plain_bool(
                item["attested_confirmation_accessed"],
                label="attested_confirmation_accessed",
            ),
            access_facts_are_external_attestations=_plain_bool(
                item["access_facts_are_external_attestations"],
                label="access_facts_are_external_attestations",
            ),
            cryptographic_access_proof=_plain_bool(
                item["cryptographic_access_proof"],
                label="cryptographic_access_proof",
            ),
            selection_execution_started=_plain_bool(
                item["selection_execution_started"],
                label="selection_execution_started",
            ),
            terminally_consumed=_plain_bool(
                item["terminally_consumed"],
                label="terminally_consumed",
            ),
            reopen_authorized=_plain_bool(
                item["reopen_authorized"],
                label="reopen_authorized",
            ),
            retry_authorized=_plain_bool(
                item["retry_authorized"],
                label="retry_authorized",
            ),
        )


@dataclass(frozen=True, slots=True)
class SelectionAttemptClaimArtifact:
    """Exclusive store-local claim acquired before any selection generation."""

    claim_id: str
    freeze_artifact_sha256: str
    protocol_id: str
    protocol_source_sha256: str
    protocol_canonical_sha256: str
    engine_commit: str
    preseed_readiness: PreseedReadinessBinding | None
    launch_intent: SelectionLaunchIntentBinding | None = None
    schema_version: str = SELECTION_ATTEMPT_CLAIM_SCHEMA_VERSION
    role: str = "calibration_selection_attempt_claim"
    claim_ceiling: str = "level_0"
    attempt_number: int = 1
    selection_execution_claimed: bool = True
    terminally_consumed: bool = False
    reopen_authorized: bool = False
    retry_authorized: bool = False

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "claim_id",
            "role",
            "claim_ceiling",
            "freeze_artifact_sha256",
            "protocol_id",
            "protocol_source_sha256",
            "protocol_canonical_sha256",
            "engine_commit",
            "preseed_readiness",
            "launch_intent",
            "attempt_number",
            "selection_execution_claimed",
            "terminally_consumed",
            "reopen_authorized",
            "retry_authorized",
        }
    )

    def __post_init__(self) -> None:
        _constant(
            self.schema_version,
            SELECTION_ATTEMPT_CLAIM_SCHEMA_VERSION,
            label="schema_version",
        )
        _slug(self.claim_id, label="claim_id")
        _constant(
            self.role,
            "calibration_selection_attempt_claim",
            label="role",
        )
        _constant(self.claim_ceiling, "level_0", label="claim_ceiling")
        _sha256(self.freeze_artifact_sha256, label="freeze_artifact_sha256")
        _slug(self.protocol_id, label="protocol_id")
        _sha256(self.protocol_source_sha256, label="protocol_source_sha256")
        _sha256(
            self.protocol_canonical_sha256,
            label="protocol_canonical_sha256",
        )
        _commit(self.engine_commit, label="engine_commit")
        if self.preseed_readiness is not None:
            if not isinstance(self.preseed_readiness, PreseedReadinessBinding):
                raise TypeError(
                    "preseed_readiness must be a PreseedReadinessBinding or None"
                )
            if self.preseed_readiness.engine_commit != self.engine_commit:
                raise QualificationContractError(
                    "attempt claim preseed readiness differs from engine_commit"
                )
        if self.launch_intent is not None and not isinstance(
            self.launch_intent,
            SelectionLaunchIntentBinding,
        ):
            raise TypeError(
                "launch_intent must be a SelectionLaunchIntentBinding or None"
            )
        _constant(self.attempt_number, 1, label="attempt_number")
        _constant(
            self.selection_execution_claimed,
            True,
            label="selection_execution_claimed",
        )
        for name in (
            "terminally_consumed",
            "reopen_authorized",
            "retry_authorized",
        ):
            _constant(getattr(self, name), False, label=name)
        if self.protocol_source_sha256 != self.protocol_canonical_sha256:
            raise QualificationContractError(
                "an attempt claim must bind exact canonical protocol source bytes"
            )
        if len(self.canonical_bytes) > MAX_SELECTION_CHRONOLOGY_ARTIFACT_BYTES:
            raise QualificationContractError(
                "selection attempt claim exceeds the fixed byte cap"
            )

    @classmethod
    def from_freeze(
        cls,
        *,
        claim_id: str,
        freeze: SelectionFreezeArtifact,
        launch_intent: SelectionLaunchIntentBinding | None = None,
    ) -> SelectionAttemptClaimArtifact:
        if not isinstance(freeze, SelectionFreezeArtifact):
            raise TypeError("freeze must be a SelectionFreezeArtifact")
        return cls(
            claim_id=claim_id,
            freeze_artifact_sha256=freeze.canonical_sha256,
            protocol_id=freeze.protocol_id,
            protocol_source_sha256=freeze.protocol_source_sha256,
            protocol_canonical_sha256=freeze.protocol_canonical_sha256,
            engine_commit=freeze.engine_commit,
            preseed_readiness=freeze.preseed_readiness,
            launch_intent=launch_intent,
        )

    def validate_freeze(self, freeze: SelectionFreezeArtifact) -> None:
        if not isinstance(freeze, SelectionFreezeArtifact):
            raise TypeError("freeze must be a SelectionFreezeArtifact")
        expected = SelectionAttemptClaimArtifact.from_freeze(
            claim_id=self.claim_id,
            freeze=freeze,
            launch_intent=self.launch_intent,
        )
        if self != expected:
            raise QualificationContractError(
                "selection attempt claim does not match its freeze"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "claim_id": self.claim_id,
            "role": self.role,
            "claim_ceiling": self.claim_ceiling,
            "freeze_artifact_sha256": self.freeze_artifact_sha256,
            "protocol_id": self.protocol_id,
            "protocol_source_sha256": self.protocol_source_sha256,
            "protocol_canonical_sha256": self.protocol_canonical_sha256,
            "engine_commit": self.engine_commit,
            "preseed_readiness": (
                None
                if self.preseed_readiness is None
                else self.preseed_readiness.to_dict()
            ),
            "launch_intent": (
                None if self.launch_intent is None else self.launch_intent.to_dict()
            ),
            "attempt_number": self.attempt_number,
            "selection_execution_claimed": self.selection_execution_claimed,
            "terminally_consumed": self.terminally_consumed,
            "reopen_authorized": self.reopen_authorized,
            "retry_authorized": self.retry_authorized,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> SelectionAttemptClaimArtifact:
        item = _mapping(value, label="selection attempt claim")
        _exact_keys(item, cls._ROOT_KEYS, label="selection attempt claim")
        return cls(
            schema_version=_constant(
                item["schema_version"],
                SELECTION_ATTEMPT_CLAIM_SCHEMA_VERSION,
                label="schema_version",
            ),  # type: ignore[arg-type]
            claim_id=_slug(item["claim_id"], label="claim_id"),
            role=_constant(
                item["role"],
                "calibration_selection_attempt_claim",
                label="role",
            ),  # type: ignore[arg-type]
            claim_ceiling=_constant(
                item["claim_ceiling"],
                "level_0",
                label="claim_ceiling",
            ),  # type: ignore[arg-type]
            freeze_artifact_sha256=_sha256(
                item["freeze_artifact_sha256"],
                label="freeze_artifact_sha256",
            ),
            protocol_id=_slug(item["protocol_id"], label="protocol_id"),
            protocol_source_sha256=_sha256(
                item["protocol_source_sha256"],
                label="protocol_source_sha256",
            ),
            protocol_canonical_sha256=_sha256(
                item["protocol_canonical_sha256"],
                label="protocol_canonical_sha256",
            ),
            engine_commit=_commit(item["engine_commit"], label="engine_commit"),
            preseed_readiness=(
                None
                if item["preseed_readiness"] is None
                else PreseedReadinessBinding.from_dict(item["preseed_readiness"])
            ),
            launch_intent=(
                None
                if item["launch_intent"] is None
                else SelectionLaunchIntentBinding.from_dict(item["launch_intent"])
            ),
            attempt_number=_plain_int(
                item["attempt_number"],
                label="attempt_number",
                minimum=1,
            ),
            selection_execution_claimed=_plain_bool(
                item["selection_execution_claimed"],
                label="selection_execution_claimed",
            ),
            terminally_consumed=_plain_bool(
                item["terminally_consumed"],
                label="terminally_consumed",
            ),
            reopen_authorized=_plain_bool(
                item["reopen_authorized"],
                label="reopen_authorized",
            ),
            retry_authorized=_plain_bool(
                item["retry_authorized"],
                label="retry_authorized",
            ),
        )


@dataclass(frozen=True, slots=True)
class SelectionExecutionStartArtifact:
    """Immutable transition proving that one claimed execution has started.

    The freeze-keyed file containing this record is created with ``O_EXCL``
    immediately before any generator is entered.  It is never removed after a
    crash, so the same attempt claim cannot be used to execute the selection
    twice.
    """

    freeze_artifact_sha256: str
    attempt_claim_sha256: str
    protocol_id: str
    protocol_source_sha256: str
    protocol_canonical_sha256: str
    engine_commit: str
    selection_launch_authorization_sha256: str | None = None
    authorized_head_commit: str | None = None
    schema_version: str = SELECTION_EXECUTION_START_SCHEMA_VERSION
    role: str = "calibration_selection_execution_start"
    claim_ceiling: str = "level_0"
    attempt_number: int = 1
    selection_execution_started: bool = True
    terminally_consumed: bool = False
    reopen_authorized: bool = False
    retry_authorized: bool = False

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "role",
            "claim_ceiling",
            "freeze_artifact_sha256",
            "attempt_claim_sha256",
            "protocol_id",
            "protocol_source_sha256",
            "protocol_canonical_sha256",
            "engine_commit",
            "selection_launch_authorization_sha256",
            "authorized_head_commit",
            "attempt_number",
            "selection_execution_started",
            "terminally_consumed",
            "reopen_authorized",
            "retry_authorized",
        }
    )

    def __post_init__(self) -> None:
        _constant(
            self.schema_version,
            SELECTION_EXECUTION_START_SCHEMA_VERSION,
            label="schema_version",
        )
        _constant(
            self.role,
            "calibration_selection_execution_start",
            label="role",
        )
        _constant(self.claim_ceiling, "level_0", label="claim_ceiling")
        for name in (
            "freeze_artifact_sha256",
            "attempt_claim_sha256",
            "protocol_source_sha256",
            "protocol_canonical_sha256",
        ):
            _sha256(getattr(self, name), label=name)
        _slug(self.protocol_id, label="protocol_id")
        _commit(self.engine_commit, label="engine_commit")
        _launch_authorization_sha256(
            self.selection_launch_authorization_sha256,
            protocol_id=self.protocol_id,
            label="execution start selection_launch_authorization_sha256",
        )
        _authorized_head_commit(
            self.authorized_head_commit,
            protocol_id=self.protocol_id,
            label="execution start authorized_head_commit",
        )
        _constant(self.attempt_number, 1, label="attempt_number")
        _constant(
            self.selection_execution_started,
            True,
            label="selection_execution_started",
        )
        for name in (
            "terminally_consumed",
            "reopen_authorized",
            "retry_authorized",
        ):
            _constant(getattr(self, name), False, label=name)
        if self.protocol_source_sha256 != self.protocol_canonical_sha256:
            raise QualificationContractError(
                "an execution start must bind exact canonical protocol source bytes"
            )
        if len(self.canonical_bytes) > MAX_SELECTION_CHRONOLOGY_ARTIFACT_BYTES:
            raise QualificationContractError(
                "selection execution-start artifact exceeds the fixed byte cap"
            )

    @classmethod
    def from_companions(
        cls,
        *,
        freeze: SelectionFreezeArtifact,
        attempt_claim: SelectionAttemptClaimArtifact,
        selection_launch_authorization_sha256: str | None = None,
        authorized_head_commit: str | None = None,
    ) -> SelectionExecutionStartArtifact:
        if not isinstance(freeze, SelectionFreezeArtifact):
            raise TypeError("freeze must be a SelectionFreezeArtifact")
        if not isinstance(attempt_claim, SelectionAttemptClaimArtifact):
            raise TypeError("attempt_claim must be a SelectionAttemptClaimArtifact")
        attempt_claim.validate_freeze(freeze)
        from .preparation import CLOSED_D0_D5_PROTOCOL_ID

        if (
            freeze.protocol_id == CLOSED_D0_D5_PROTOCOL_ID
            and attempt_claim.launch_intent is None
        ):
            raise QualificationContractError(
                "official execution start requires an intent-bound attempt claim"
            )
        return cls(
            freeze_artifact_sha256=freeze.canonical_sha256,
            attempt_claim_sha256=attempt_claim.canonical_sha256,
            protocol_id=freeze.protocol_id,
            protocol_source_sha256=freeze.protocol_source_sha256,
            protocol_canonical_sha256=freeze.protocol_canonical_sha256,
            engine_commit=freeze.engine_commit,
            selection_launch_authorization_sha256=(
                selection_launch_authorization_sha256
            ),
            authorized_head_commit=authorized_head_commit,
        )

    def validate_companions(
        self,
        *,
        freeze: SelectionFreezeArtifact,
        attempt_claim: SelectionAttemptClaimArtifact,
        selection_launch_authorization_sha256: str | None = None,
        authorized_head_commit: str | None = None,
    ) -> None:
        expected = SelectionExecutionStartArtifact.from_companions(
            freeze=freeze,
            attempt_claim=attempt_claim,
            selection_launch_authorization_sha256=(
                selection_launch_authorization_sha256
            ),
            authorized_head_commit=authorized_head_commit,
        )
        if self != expected:
            raise QualificationContractError(
                "selection execution-start artifact does not match its companions"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "role": self.role,
            "claim_ceiling": self.claim_ceiling,
            "freeze_artifact_sha256": self.freeze_artifact_sha256,
            "attempt_claim_sha256": self.attempt_claim_sha256,
            "protocol_id": self.protocol_id,
            "protocol_source_sha256": self.protocol_source_sha256,
            "protocol_canonical_sha256": self.protocol_canonical_sha256,
            "engine_commit": self.engine_commit,
            "selection_launch_authorization_sha256": (
                self.selection_launch_authorization_sha256
            ),
            "authorized_head_commit": self.authorized_head_commit,
            "attempt_number": self.attempt_number,
            "selection_execution_started": self.selection_execution_started,
            "terminally_consumed": self.terminally_consumed,
            "reopen_authorized": self.reopen_authorized,
            "retry_authorized": self.retry_authorized,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> SelectionExecutionStartArtifact:
        item = _mapping(value, label="selection execution-start artifact")
        _exact_keys(
            item,
            cls._ROOT_KEYS,
            label="selection execution-start artifact",
        )
        return cls(
            schema_version=_constant(
                item["schema_version"],
                SELECTION_EXECUTION_START_SCHEMA_VERSION,
                label="schema_version",
            ),  # type: ignore[arg-type]
            role=_constant(
                item["role"],
                "calibration_selection_execution_start",
                label="role",
            ),  # type: ignore[arg-type]
            claim_ceiling=_constant(
                item["claim_ceiling"],
                "level_0",
                label="claim_ceiling",
            ),  # type: ignore[arg-type]
            freeze_artifact_sha256=_sha256(
                item["freeze_artifact_sha256"],
                label="freeze_artifact_sha256",
            ),
            attempt_claim_sha256=_sha256(
                item["attempt_claim_sha256"],
                label="attempt_claim_sha256",
            ),
            protocol_id=_slug(item["protocol_id"], label="protocol_id"),
            protocol_source_sha256=_sha256(
                item["protocol_source_sha256"],
                label="protocol_source_sha256",
            ),
            protocol_canonical_sha256=_sha256(
                item["protocol_canonical_sha256"],
                label="protocol_canonical_sha256",
            ),
            engine_commit=_commit(item["engine_commit"], label="engine_commit"),
            selection_launch_authorization_sha256=_launch_authorization_sha256(
                item["selection_launch_authorization_sha256"],
                protocol_id=_slug(item["protocol_id"], label="protocol_id"),
                label="execution start selection_launch_authorization_sha256",
            ),
            authorized_head_commit=_authorized_head_commit(
                item["authorized_head_commit"],
                protocol_id=_slug(item["protocol_id"], label="protocol_id"),
                label="execution start authorized_head_commit",
            ),
            attempt_number=_plain_int(
                item["attempt_number"],
                label="attempt_number",
                minimum=1,
            ),
            selection_execution_started=_plain_bool(
                item["selection_execution_started"],
                label="selection_execution_started",
            ),
            terminally_consumed=_plain_bool(
                item["terminally_consumed"],
                label="terminally_consumed",
            ),
            reopen_authorized=_plain_bool(
                item["reopen_authorized"],
                label="reopen_authorized",
            ),
            retry_authorized=_plain_bool(
                item["retry_authorized"],
                label="retry_authorized",
            ),
        )


@dataclass(frozen=True, slots=True)
class SelectionTerminalManifestArtifact:
    """Content manifest for one atomically published terminal transaction."""

    freeze_artifact_sha256: str
    attempt_claim_sha256: str
    terminal_artifact_kind: TerminalAttemptArtifactKind
    terminal_artifact_sha256: str
    terminal_artifact_byte_count: int
    consumption_sha256: str
    consumption_byte_count: int
    schema_version: str = SELECTION_TERMINAL_MANIFEST_SCHEMA_VERSION
    role: str = "calibration_selection_terminal_transaction"
    terminal_artifact_filename: str = SELECTION_TERMINAL_ARTIFACT_FILENAME
    consumption_filename: str = SELECTION_TERMINAL_CONSUMPTION_FILENAME

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "role",
            "freeze_artifact_sha256",
            "attempt_claim_sha256",
            "terminal_artifact_kind",
            "terminal_artifact_filename",
            "terminal_artifact_sha256",
            "terminal_artifact_byte_count",
            "consumption_filename",
            "consumption_sha256",
            "consumption_byte_count",
        }
    )

    def __post_init__(self) -> None:
        _constant(
            self.schema_version,
            SELECTION_TERMINAL_MANIFEST_SCHEMA_VERSION,
            label="schema_version",
        )
        _constant(
            self.role,
            "calibration_selection_terminal_transaction",
            label="role",
        )
        _sha256(self.freeze_artifact_sha256, label="freeze_artifact_sha256")
        _sha256(self.attempt_claim_sha256, label="attempt_claim_sha256")
        if not isinstance(
            self.terminal_artifact_kind,
            TerminalAttemptArtifactKind,
        ):
            raise TypeError(
                "terminal_artifact_kind must be a TerminalAttemptArtifactKind"
            )
        _constant(
            self.terminal_artifact_filename,
            SELECTION_TERMINAL_ARTIFACT_FILENAME,
            label="terminal_artifact_filename",
        )
        _sha256(
            self.terminal_artifact_sha256,
            label="terminal_artifact_sha256",
        )
        _plain_int(
            self.terminal_artifact_byte_count,
            label="terminal_artifact_byte_count",
            minimum=1,
        )
        if self.terminal_artifact_byte_count > MAX_SELECTION_TERMINAL_ARTIFACT_BYTES:
            raise QualificationContractError(
                "terminal_artifact_byte_count exceeds the fixed byte cap"
            )
        _constant(
            self.consumption_filename,
            SELECTION_TERMINAL_CONSUMPTION_FILENAME,
            label="consumption_filename",
        )
        _sha256(self.consumption_sha256, label="consumption_sha256")
        _plain_int(
            self.consumption_byte_count,
            label="consumption_byte_count",
            minimum=1,
        )
        if self.consumption_byte_count > MAX_SELECTION_CHRONOLOGY_ARTIFACT_BYTES:
            raise QualificationContractError(
                "consumption_byte_count exceeds the fixed byte cap"
            )
        if len(self.canonical_bytes) > MAX_SELECTION_CHRONOLOGY_ARTIFACT_BYTES:
            raise QualificationContractError(
                "selection terminal manifest exceeds the fixed byte cap"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "role": self.role,
            "freeze_artifact_sha256": self.freeze_artifact_sha256,
            "attempt_claim_sha256": self.attempt_claim_sha256,
            "terminal_artifact_kind": self.terminal_artifact_kind.value,
            "terminal_artifact_filename": self.terminal_artifact_filename,
            "terminal_artifact_sha256": self.terminal_artifact_sha256,
            "terminal_artifact_byte_count": self.terminal_artifact_byte_count,
            "consumption_filename": self.consumption_filename,
            "consumption_sha256": self.consumption_sha256,
            "consumption_byte_count": self.consumption_byte_count,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> SelectionTerminalManifestArtifact:
        item = _mapping(value, label="selection terminal manifest")
        _exact_keys(item, cls._ROOT_KEYS, label="selection terminal manifest")
        return cls(
            schema_version=_constant(
                item["schema_version"],
                SELECTION_TERMINAL_MANIFEST_SCHEMA_VERSION,
                label="schema_version",
            ),  # type: ignore[arg-type]
            role=_constant(
                item["role"],
                "calibration_selection_terminal_transaction",
                label="role",
            ),  # type: ignore[arg-type]
            freeze_artifact_sha256=_sha256(
                item["freeze_artifact_sha256"],
                label="freeze_artifact_sha256",
            ),
            attempt_claim_sha256=_sha256(
                item["attempt_claim_sha256"],
                label="attempt_claim_sha256",
            ),
            terminal_artifact_kind=_enum(
                TerminalAttemptArtifactKind,
                item["terminal_artifact_kind"],
                label="terminal_artifact_kind",
            ),  # type: ignore[arg-type]
            terminal_artifact_filename=_constant(
                item["terminal_artifact_filename"],
                SELECTION_TERMINAL_ARTIFACT_FILENAME,
                label="terminal_artifact_filename",
            ),  # type: ignore[arg-type]
            terminal_artifact_sha256=_sha256(
                item["terminal_artifact_sha256"],
                label="terminal_artifact_sha256",
            ),
            terminal_artifact_byte_count=_plain_int(
                item["terminal_artifact_byte_count"],
                label="terminal_artifact_byte_count",
                minimum=1,
            ),
            consumption_filename=_constant(
                item["consumption_filename"],
                SELECTION_TERMINAL_CONSUMPTION_FILENAME,
                label="consumption_filename",
            ),  # type: ignore[arg-type]
            consumption_sha256=_sha256(
                item["consumption_sha256"],
                label="consumption_sha256",
            ),
            consumption_byte_count=_plain_int(
                item["consumption_byte_count"],
                label="consumption_byte_count",
                minimum=1,
            ),
        )


@dataclass(frozen=True, slots=True)
class SelectionFailedAttemptArtifact:
    """Typed terminal evidence for an attempt that produced no result."""

    failed_attempt_id: str
    freeze_artifact_sha256: str
    protocol_id: str
    protocol_source_sha256: str
    protocol_canonical_sha256: str
    engine_commit: str
    failure_stage: str
    failure_evidence_sha256: str
    attested_selection_values_observed: bool
    selection_launch_authorization_sha256: str | None = None
    schema_version: str = SELECTION_FAILED_ATTEMPT_SCHEMA_VERSION
    role: str = "calibration_selection_failed_attempt"
    claim_ceiling: str = "level_0"
    attempt_number: int = 1
    selection_execution_started: bool = True
    terminally_consumed: bool = True
    reopen_authorized: bool = False
    retry_authorized: bool = False
    access_facts_are_external_attestations: bool = True
    cryptographic_access_proof: bool = False

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "failed_attempt_id",
            "role",
            "claim_ceiling",
            "freeze_artifact_sha256",
            "protocol_id",
            "protocol_source_sha256",
            "protocol_canonical_sha256",
            "engine_commit",
            "failure_stage",
            "failure_evidence_sha256",
            "attested_selection_values_observed",
            "selection_launch_authorization_sha256",
            "attempt_number",
            "selection_execution_started",
            "terminally_consumed",
            "reopen_authorized",
            "retry_authorized",
            "access_facts_are_external_attestations",
            "cryptographic_access_proof",
        }
    )

    def __post_init__(self) -> None:
        _constant(
            self.schema_version,
            SELECTION_FAILED_ATTEMPT_SCHEMA_VERSION,
            label="schema_version",
        )
        _slug(self.failed_attempt_id, label="failed_attempt_id")
        _constant(
            self.role,
            "calibration_selection_failed_attempt",
            label="role",
        )
        _constant(self.claim_ceiling, "level_0", label="claim_ceiling")
        for name in (
            "freeze_artifact_sha256",
            "protocol_source_sha256",
            "protocol_canonical_sha256",
            "failure_evidence_sha256",
        ):
            _sha256(getattr(self, name), label=name)
        _slug(self.protocol_id, label="protocol_id")
        _commit(self.engine_commit, label="engine_commit")
        _launch_authorization_sha256(
            self.selection_launch_authorization_sha256,
            protocol_id=self.protocol_id,
            label="failed attempt selection_launch_authorization_sha256",
        )
        _slug(self.failure_stage, label="failure_stage")
        _plain_bool(
            self.attested_selection_values_observed,
            label="attested_selection_values_observed",
        )
        _constant(self.attempt_number, 1, label="attempt_number")
        for name in ("selection_execution_started", "terminally_consumed"):
            _constant(getattr(self, name), True, label=name)
        for name in (
            "reopen_authorized",
            "retry_authorized",
            "cryptographic_access_proof",
        ):
            _constant(getattr(self, name), False, label=name)
        _constant(
            self.access_facts_are_external_attestations,
            True,
            label="access_facts_are_external_attestations",
        )
        if self.protocol_source_sha256 != self.protocol_canonical_sha256:
            raise QualificationContractError(
                "a failed attempt must bind exact canonical protocol source bytes"
            )
        if len(self.canonical_bytes) > MAX_SELECTION_CHRONOLOGY_ARTIFACT_BYTES:
            raise QualificationContractError(
                "selection failed-attempt artifact exceeds the fixed byte cap"
            )

    @classmethod
    def from_freeze(
        cls,
        *,
        failed_attempt_id: str,
        freeze: SelectionFreezeArtifact,
        failure_stage: str,
        failure_evidence_sha256: str,
        attested_selection_values_observed: bool,
        selection_launch_authorization_sha256: str | None = None,
    ) -> SelectionFailedAttemptArtifact:
        if not isinstance(freeze, SelectionFreezeArtifact):
            raise TypeError("freeze must be a SelectionFreezeArtifact")
        return cls(
            failed_attempt_id=failed_attempt_id,
            freeze_artifact_sha256=freeze.canonical_sha256,
            protocol_id=freeze.protocol_id,
            protocol_source_sha256=freeze.protocol_source_sha256,
            protocol_canonical_sha256=freeze.protocol_canonical_sha256,
            engine_commit=freeze.engine_commit,
            failure_stage=failure_stage,
            failure_evidence_sha256=_sha256(
                failure_evidence_sha256,
                label="failure_evidence_sha256",
            ),
            attested_selection_values_observed=_plain_bool(
                attested_selection_values_observed,
                label="attested_selection_values_observed",
            ),
            selection_launch_authorization_sha256=(
                selection_launch_authorization_sha256
            ),
        )

    def validate_freeze(self, freeze: SelectionFreezeArtifact) -> None:
        if not isinstance(freeze, SelectionFreezeArtifact):
            raise TypeError("freeze must be a SelectionFreezeArtifact")
        if (
            self.freeze_artifact_sha256 != freeze.canonical_sha256
            or self.protocol_id != freeze.protocol_id
            or self.protocol_source_sha256 != freeze.protocol_source_sha256
            or self.protocol_canonical_sha256 != freeze.protocol_canonical_sha256
            or self.engine_commit != freeze.engine_commit
        ):
            raise QualificationContractError(
                "failed-attempt artifact does not match its freeze"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "failed_attempt_id": self.failed_attempt_id,
            "role": self.role,
            "claim_ceiling": self.claim_ceiling,
            "freeze_artifact_sha256": self.freeze_artifact_sha256,
            "protocol_id": self.protocol_id,
            "protocol_source_sha256": self.protocol_source_sha256,
            "protocol_canonical_sha256": self.protocol_canonical_sha256,
            "engine_commit": self.engine_commit,
            "failure_stage": self.failure_stage,
            "failure_evidence_sha256": self.failure_evidence_sha256,
            "attested_selection_values_observed": (
                self.attested_selection_values_observed
            ),
            "selection_launch_authorization_sha256": (
                self.selection_launch_authorization_sha256
            ),
            "attempt_number": self.attempt_number,
            "selection_execution_started": self.selection_execution_started,
            "terminally_consumed": self.terminally_consumed,
            "reopen_authorized": self.reopen_authorized,
            "retry_authorized": self.retry_authorized,
            "access_facts_are_external_attestations": (
                self.access_facts_are_external_attestations
            ),
            "cryptographic_access_proof": self.cryptographic_access_proof,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> SelectionFailedAttemptArtifact:
        item = _mapping(value, label="selection failed-attempt artifact")
        _exact_keys(
            item,
            cls._ROOT_KEYS,
            label="selection failed-attempt artifact",
        )
        return cls(
            schema_version=_constant(
                item["schema_version"],
                SELECTION_FAILED_ATTEMPT_SCHEMA_VERSION,
                label="schema_version",
            ),  # type: ignore[arg-type]
            failed_attempt_id=_slug(
                item["failed_attempt_id"],
                label="failed_attempt_id",
            ),
            role=_constant(
                item["role"],
                "calibration_selection_failed_attempt",
                label="role",
            ),  # type: ignore[arg-type]
            claim_ceiling=_constant(
                item["claim_ceiling"],
                "level_0",
                label="claim_ceiling",
            ),  # type: ignore[arg-type]
            freeze_artifact_sha256=_sha256(
                item["freeze_artifact_sha256"],
                label="freeze_artifact_sha256",
            ),
            protocol_id=_slug(item["protocol_id"], label="protocol_id"),
            protocol_source_sha256=_sha256(
                item["protocol_source_sha256"],
                label="protocol_source_sha256",
            ),
            protocol_canonical_sha256=_sha256(
                item["protocol_canonical_sha256"],
                label="protocol_canonical_sha256",
            ),
            engine_commit=_commit(item["engine_commit"], label="engine_commit"),
            failure_stage=_slug(item["failure_stage"], label="failure_stage"),
            failure_evidence_sha256=_sha256(
                item["failure_evidence_sha256"],
                label="failure_evidence_sha256",
            ),
            attested_selection_values_observed=_plain_bool(
                item["attested_selection_values_observed"],
                label="attested_selection_values_observed",
            ),
            selection_launch_authorization_sha256=_launch_authorization_sha256(
                item["selection_launch_authorization_sha256"],
                protocol_id=_slug(item["protocol_id"], label="protocol_id"),
                label="failed attempt selection_launch_authorization_sha256",
            ),
            attempt_number=_plain_int(
                item["attempt_number"],
                label="attempt_number",
                minimum=1,
            ),
            selection_execution_started=_plain_bool(
                item["selection_execution_started"],
                label="selection_execution_started",
            ),
            terminally_consumed=_plain_bool(
                item["terminally_consumed"],
                label="terminally_consumed",
            ),
            reopen_authorized=_plain_bool(
                item["reopen_authorized"],
                label="reopen_authorized",
            ),
            retry_authorized=_plain_bool(
                item["retry_authorized"],
                label="retry_authorized",
            ),
            access_facts_are_external_attestations=_plain_bool(
                item["access_facts_are_external_attestations"],
                label="access_facts_are_external_attestations",
            ),
            cryptographic_access_proof=_plain_bool(
                item["cryptographic_access_proof"],
                label="cryptographic_access_proof",
            ),
        )


@dataclass(frozen=True, slots=True)
class SelectionConsumptionArtifact:
    """Post-attempt receipt joined to one typed terminal artifact."""

    consumption_id: str
    freeze_artifact_sha256: str
    attempt_claim_sha256: str
    protocol_id: str
    protocol_source_sha256: str
    protocol_canonical_sha256: str
    engine_commit: str
    seed_family_id: str
    seed_family_commitment_sha256: str
    terminal_artifact_kind: TerminalAttemptArtifactKind
    terminal_artifact_sha256: str
    attested_selection_values_observed: bool
    schema_version: str = SELECTION_CONSUMPTION_SCHEMA_VERSION
    role: str = "calibration_selection_terminal_consumption"
    claim_ceiling: str = "level_0"
    attempt_number: int = 1
    access_state: SelectionAccessState = SelectionAccessState.TERMINALLY_CONSUMED
    attested_prior_selection_family_accessed: bool = False
    attested_confirmation_accessed: bool = False
    access_facts_are_external_attestations: bool = True
    cryptographic_access_proof: bool = False
    selection_execution_started: bool = True
    terminally_consumed: bool = True
    reopen_authorized: bool = False
    retry_authorized: bool = False

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "consumption_id",
            "role",
            "claim_ceiling",
            "freeze_artifact_sha256",
            "attempt_claim_sha256",
            "protocol_id",
            "protocol_source_sha256",
            "protocol_canonical_sha256",
            "engine_commit",
            "seed_family_id",
            "seed_family_commitment_sha256",
            "terminal_artifact_kind",
            "terminal_artifact_sha256",
            "attempt_number",
            "access_state",
            "attested_selection_values_observed",
            "attested_prior_selection_family_accessed",
            "attested_confirmation_accessed",
            "access_facts_are_external_attestations",
            "cryptographic_access_proof",
            "selection_execution_started",
            "terminally_consumed",
            "reopen_authorized",
            "retry_authorized",
        }
    )

    def __post_init__(self) -> None:
        _constant(
            self.schema_version,
            SELECTION_CONSUMPTION_SCHEMA_VERSION,
            label="schema_version",
        )
        _slug(self.consumption_id, label="consumption_id")
        _constant(
            self.role,
            "calibration_selection_terminal_consumption",
            label="role",
        )
        _constant(self.claim_ceiling, "level_0", label="claim_ceiling")
        for name in (
            "freeze_artifact_sha256",
            "attempt_claim_sha256",
            "protocol_source_sha256",
            "protocol_canonical_sha256",
            "seed_family_commitment_sha256",
            "terminal_artifact_sha256",
        ):
            _sha256(getattr(self, name), label=name)
        _slug(self.protocol_id, label="protocol_id")
        _commit(self.engine_commit, label="engine_commit")
        _slug(self.seed_family_id, label="seed_family_id")
        if not isinstance(self.terminal_artifact_kind, TerminalAttemptArtifactKind):
            raise TypeError(
                "terminal_artifact_kind must be a TerminalAttemptArtifactKind"
            )
        _constant(self.attempt_number, 1, label="attempt_number")
        if self.access_state is not SelectionAccessState.TERMINALLY_CONSUMED:
            raise QualificationContractError(
                "a consumption artifact access_state must be terminally_consumed"
            )
        _plain_bool(
            self.attested_selection_values_observed,
            label="attested_selection_values_observed",
        )
        if (
            self.terminal_artifact_kind is TerminalAttemptArtifactKind.RESULT
            and not self.attested_selection_values_observed
        ):
            raise QualificationContractError(
                "a result terminal artifact requires observed selection values"
            )
        for name in (
            "attested_prior_selection_family_accessed",
            "attested_confirmation_accessed",
            "reopen_authorized",
            "retry_authorized",
            "cryptographic_access_proof",
        ):
            _constant(getattr(self, name), False, label=name)
        _constant(
            self.access_facts_are_external_attestations,
            True,
            label="access_facts_are_external_attestations",
        )
        for name in ("selection_execution_started", "terminally_consumed"):
            _constant(getattr(self, name), True, label=name)
        if self.protocol_source_sha256 != self.protocol_canonical_sha256:
            raise QualificationContractError(
                "a consumption must bind exact canonical protocol source bytes"
            )
        if len(self.canonical_bytes) > MAX_SELECTION_CHRONOLOGY_ARTIFACT_BYTES:
            raise QualificationContractError(
                "selection consumption artifact exceeds the fixed byte cap"
            )

    @classmethod
    def consume(
        cls,
        *,
        consumption_id: str,
        freeze: SelectionFreezeArtifact,
        attempt_claim: SelectionAttemptClaimArtifact,
        terminal_artifact: object,
    ) -> SelectionConsumptionArtifact:
        if not isinstance(freeze, SelectionFreezeArtifact):
            raise TypeError("freeze must be a SelectionFreezeArtifact")
        if not isinstance(attempt_claim, SelectionAttemptClaimArtifact):
            raise TypeError("attempt_claim must be a SelectionAttemptClaimArtifact")
        attempt_claim.validate_freeze(freeze)
        from .contracts import QualificationResult

        if isinstance(terminal_artifact, QualificationResult):
            if (
                terminal_artifact.protocol_id != freeze.protocol_id
                or terminal_artifact.protocol_source_sha256
                != freeze.protocol_source_sha256
                or terminal_artifact.protocol_canonical_sha256
                != freeze.protocol_canonical_sha256
                or terminal_artifact.source_binding.engine_commit
                != freeze.engine_commit
                or terminal_artifact.selection_freeze_artifact_sha256
                != freeze.canonical_sha256
                or terminal_artifact.selection_attempt_claim_sha256
                != attempt_claim.canonical_sha256
            ):
                raise QualificationContractError(
                    "qualification result does not match the frozen protocol "
                    "and exact execution companions"
                )
            terminal_kind = TerminalAttemptArtifactKind.RESULT
            terminal_sha256 = terminal_artifact.canonical_sha256
            observed = True
        elif isinstance(terminal_artifact, SelectionFailedAttemptArtifact):
            terminal_artifact.validate_freeze(freeze)
            terminal_kind = TerminalAttemptArtifactKind.FAILED_ATTEMPT
            terminal_sha256 = terminal_artifact.canonical_sha256
            observed = terminal_artifact.attested_selection_values_observed
        else:
            raise TypeError(
                "terminal_artifact must be a QualificationResult or "
                "SelectionFailedAttemptArtifact"
            )
        return cls(
            consumption_id=consumption_id,
            freeze_artifact_sha256=freeze.canonical_sha256,
            attempt_claim_sha256=attempt_claim.canonical_sha256,
            protocol_id=freeze.protocol_id,
            protocol_source_sha256=freeze.protocol_source_sha256,
            protocol_canonical_sha256=freeze.protocol_canonical_sha256,
            engine_commit=freeze.engine_commit,
            seed_family_id=freeze.seed_family_id,
            seed_family_commitment_sha256=(freeze.seed_family_commitment_sha256),
            terminal_artifact_kind=terminal_kind,
            terminal_artifact_sha256=terminal_sha256,
            attested_selection_values_observed=observed,
        )

    def validate_freeze(self, freeze: SelectionFreezeArtifact) -> None:
        if not isinstance(freeze, SelectionFreezeArtifact):
            raise TypeError("freeze must be a SelectionFreezeArtifact")
        expected_bindings = (
            self.freeze_artifact_sha256 == freeze.canonical_sha256
            and self.protocol_id == freeze.protocol_id
            and self.protocol_source_sha256 == freeze.protocol_source_sha256
            and self.protocol_canonical_sha256 == freeze.protocol_canonical_sha256
            and self.engine_commit == freeze.engine_commit
            and self.seed_family_id == freeze.seed_family_id
            and self.seed_family_commitment_sha256
            == freeze.seed_family_commitment_sha256
        )
        if not expected_bindings:
            raise QualificationContractError(
                "selection consumption artifact does not match its freeze"
            )

    def validate_attempt_claim(
        self,
        *,
        freeze: SelectionFreezeArtifact,
        attempt_claim: SelectionAttemptClaimArtifact,
    ) -> None:
        self.validate_freeze(freeze)
        if not isinstance(attempt_claim, SelectionAttemptClaimArtifact):
            raise TypeError("attempt_claim must be a SelectionAttemptClaimArtifact")
        attempt_claim.validate_freeze(freeze)
        if self.attempt_claim_sha256 != attempt_claim.canonical_sha256:
            raise QualificationContractError(
                "selection consumption artifact does not match its attempt claim"
            )

    def validate_terminal_artifact(
        self,
        *,
        freeze: SelectionFreezeArtifact,
        attempt_claim: SelectionAttemptClaimArtifact,
        terminal_artifact: object,
    ) -> None:
        self.validate_attempt_claim(
            freeze=freeze,
            attempt_claim=attempt_claim,
        )
        expected = SelectionConsumptionArtifact.consume(
            consumption_id=self.consumption_id,
            freeze=freeze,
            attempt_claim=attempt_claim,
            terminal_artifact=terminal_artifact,
        )
        if self != expected:
            raise QualificationContractError(
                "selection consumption artifact does not match its typed "
                "terminal artifact"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "consumption_id": self.consumption_id,
            "role": self.role,
            "claim_ceiling": self.claim_ceiling,
            "freeze_artifact_sha256": self.freeze_artifact_sha256,
            "attempt_claim_sha256": self.attempt_claim_sha256,
            "protocol_id": self.protocol_id,
            "protocol_source_sha256": self.protocol_source_sha256,
            "protocol_canonical_sha256": self.protocol_canonical_sha256,
            "engine_commit": self.engine_commit,
            "seed_family_id": self.seed_family_id,
            "seed_family_commitment_sha256": (self.seed_family_commitment_sha256),
            "terminal_artifact_kind": self.terminal_artifact_kind.value,
            "terminal_artifact_sha256": self.terminal_artifact_sha256,
            "attempt_number": self.attempt_number,
            "access_state": self.access_state.value,
            "attested_selection_values_observed": (
                self.attested_selection_values_observed
            ),
            "attested_prior_selection_family_accessed": (
                self.attested_prior_selection_family_accessed
            ),
            "attested_confirmation_accessed": (self.attested_confirmation_accessed),
            "access_facts_are_external_attestations": (
                self.access_facts_are_external_attestations
            ),
            "cryptographic_access_proof": self.cryptographic_access_proof,
            "selection_execution_started": self.selection_execution_started,
            "terminally_consumed": self.terminally_consumed,
            "reopen_authorized": self.reopen_authorized,
            "retry_authorized": self.retry_authorized,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> SelectionConsumptionArtifact:
        item = _mapping(value, label="selection consumption artifact")
        _exact_keys(
            item,
            cls._ROOT_KEYS,
            label="selection consumption artifact",
        )
        return cls(
            schema_version=_constant(
                item["schema_version"],
                SELECTION_CONSUMPTION_SCHEMA_VERSION,
                label="schema_version",
            ),  # type: ignore[arg-type]
            consumption_id=_slug(
                item["consumption_id"],
                label="consumption_id",
            ),
            role=_constant(
                item["role"],
                "calibration_selection_terminal_consumption",
                label="role",
            ),  # type: ignore[arg-type]
            claim_ceiling=_constant(
                item["claim_ceiling"],
                "level_0",
                label="claim_ceiling",
            ),  # type: ignore[arg-type]
            freeze_artifact_sha256=_sha256(
                item["freeze_artifact_sha256"],
                label="freeze_artifact_sha256",
            ),
            attempt_claim_sha256=_sha256(
                item["attempt_claim_sha256"],
                label="attempt_claim_sha256",
            ),
            protocol_id=_slug(item["protocol_id"], label="protocol_id"),
            protocol_source_sha256=_sha256(
                item["protocol_source_sha256"],
                label="protocol_source_sha256",
            ),
            protocol_canonical_sha256=_sha256(
                item["protocol_canonical_sha256"],
                label="protocol_canonical_sha256",
            ),
            engine_commit=_commit(item["engine_commit"], label="engine_commit"),
            seed_family_id=_slug(
                item["seed_family_id"],
                label="seed_family_id",
            ),
            seed_family_commitment_sha256=_sha256(
                item["seed_family_commitment_sha256"],
                label="seed_family_commitment_sha256",
            ),
            terminal_artifact_kind=_enum(
                TerminalAttemptArtifactKind,
                item["terminal_artifact_kind"],
                label="terminal_artifact_kind",
            ),  # type: ignore[arg-type]
            terminal_artifact_sha256=_sha256(
                item["terminal_artifact_sha256"],
                label="terminal_artifact_sha256",
            ),
            attempt_number=_plain_int(
                item["attempt_number"],
                label="attempt_number",
                minimum=1,
            ),
            access_state=_enum(
                SelectionAccessState,
                item["access_state"],
                label="access_state",
            ),  # type: ignore[arg-type]
            attested_selection_values_observed=_plain_bool(
                item["attested_selection_values_observed"],
                label="attested_selection_values_observed",
            ),
            attested_prior_selection_family_accessed=_plain_bool(
                item["attested_prior_selection_family_accessed"],
                label="attested_prior_selection_family_accessed",
            ),
            attested_confirmation_accessed=_plain_bool(
                item["attested_confirmation_accessed"],
                label="attested_confirmation_accessed",
            ),
            access_facts_are_external_attestations=_plain_bool(
                item["access_facts_are_external_attestations"],
                label="access_facts_are_external_attestations",
            ),
            cryptographic_access_proof=_plain_bool(
                item["cryptographic_access_proof"],
                label="cryptographic_access_proof",
            ),
            selection_execution_started=_plain_bool(
                item["selection_execution_started"],
                label="selection_execution_started",
            ),
            terminally_consumed=_plain_bool(
                item["terminally_consumed"],
                label="terminally_consumed",
            ),
            reopen_authorized=_plain_bool(
                item["reopen_authorized"],
                label="reopen_authorized",
            ),
            retry_authorized=_plain_bool(
                item["retry_authorized"],
                label="retry_authorized",
            ),
        )


def write_selection_freeze(
    path: str | Path,
    freeze: SelectionFreezeArtifact,
) -> PersistedSelectionIdentity:
    """Publish one exact freeze artifact without overwriting any prior file."""

    if not isinstance(freeze, SelectionFreezeArtifact):
        raise TypeError("freeze must be a SelectionFreezeArtifact")
    return _atomic_write_no_overwrite(
        path,
        freeze.canonical_bytes,
        label="selection freeze artifact",
    )


def load_selection_freeze(
    path: str | Path,
    *,
    expected_source_sha256: str,
    expected_canonical_sha256: str,
    loaded_protocol: object,
) -> SelectionFreezeArtifact:
    """Load a bounded canonical freeze and rejoin its exact protocol file."""

    expected_source = _sha256(
        expected_source_sha256,
        label="expected_source_sha256",
    )
    expected_canonical = _sha256(
        expected_canonical_sha256,
        label="expected_canonical_sha256",
    )
    _source_path, source, document = _load_canonical_mapping(
        path,
        label="selection freeze artifact",
    )
    freeze = SelectionFreezeArtifact.from_dict(document)
    source_sha256 = hashlib.sha256(source).hexdigest()
    if (
        source_sha256 != expected_source
        or freeze.canonical_sha256 != expected_canonical
        or source != freeze.canonical_bytes
    ):
        raise QualificationContractError(
            "selection freeze source or canonical identity differs"
        )
    freeze.validate_loaded_protocol(loaded_protocol=loaded_protocol)
    return freeze


def selection_freeze_store_path(
    store_directory: str | Path,
    freeze: SelectionFreezeArtifact,
) -> Path:
    """Return the canonical store-local freeze path for one attempt identity."""

    if not isinstance(freeze, SelectionFreezeArtifact):
        raise TypeError("freeze must be a SelectionFreezeArtifact")
    directory = _absolute_path(store_directory)
    if not directory.is_dir() or directory.is_symlink():
        raise QualificationContractError(
            f"selection chronology store must be a real directory: {directory}"
        )
    return directory / (
        f"{selection_attempt_key_sha256(freeze)}{SELECTION_FREEZE_STORE_SUFFIX}"
    )


def _load_persisted_store_freeze(
    store_directory: str | Path,
    *,
    freeze: SelectionFreezeArtifact,
) -> SelectionFreezeArtifact:
    path = selection_freeze_store_path(store_directory, freeze)
    source_path, source, document = _load_canonical_mapping(
        path,
        label="persisted selection freeze",
    )
    if source_path != path:
        raise QualificationContractError(
            "persisted selection freeze path is not canonical for its attempt"
        )
    loaded = SelectionFreezeArtifact.from_dict(document)
    if source != loaded.canonical_bytes or loaded != freeze:
        raise QualificationContractError(
            "persisted selection freeze differs from the supplied freeze"
        )
    return loaded


def _ensure_persisted_store_freeze(
    store_directory: str | Path,
    *,
    freeze: SelectionFreezeArtifact,
) -> SelectionFreezeArtifact:
    """Publish or exactly revalidate the attempt-keyed freeze before claiming."""

    path = selection_freeze_store_path(store_directory, freeze)
    try:
        _write_exclusive_file(
            path,
            freeze.canonical_bytes,
            label="persisted selection freeze",
            maximum_bytes=MAX_SELECTION_CHRONOLOGY_ARTIFACT_BYTES,
        )
        _fsync_directory(path.parent)
    except QualificationContractError:
        if not path.exists() and not path.is_symlink():
            raise
    return _load_persisted_store_freeze(
        store_directory,
        freeze=freeze,
    )


def selection_attempt_claim_path(
    store_directory: str | Path,
    freeze: SelectionFreezeArtifact,
) -> Path:
    """Return the sole store-local pre-run claim path for one attempt."""

    if not isinstance(freeze, SelectionFreezeArtifact):
        raise TypeError("freeze must be a SelectionFreezeArtifact")
    directory = _absolute_path(store_directory)
    if not directory.is_dir() or directory.is_symlink():
        raise QualificationContractError(
            f"selection chronology store must be a real directory: {directory}"
        )
    return directory / (
        f"{selection_attempt_key_sha256(freeze)}{SELECTION_ATTEMPT_CLAIM_SUFFIX}"
    )


def claim_selection_attempt(
    store_directory: str | Path,
    *,
    claim_id: str,
    freeze: SelectionFreezeArtifact,
    launch_intent: SelectionLaunchIntentBinding | None = None,
) -> tuple[SelectionAttemptClaimArtifact, PersistedSelectionIdentity]:
    """Acquire the one O_EXCL selection-attempt claim before generation.

    A partial claim left by a process or machine failure is intentionally not
    removed: its existence remains a fail-closed barrier against a second run.
    """

    _ensure_persisted_store_freeze(
        store_directory,
        freeze=freeze,
    )
    claim = SelectionAttemptClaimArtifact.from_freeze(
        claim_id=claim_id,
        freeze=freeze,
        launch_intent=launch_intent,
    )
    destination = selection_attempt_claim_path(store_directory, freeze)
    _write_exclusive_file(
        destination,
        claim.canonical_bytes,
        label="selection attempt claim",
        maximum_bytes=MAX_SELECTION_CHRONOLOGY_ARTIFACT_BYTES,
    )
    _fsync_directory(destination.parent)
    digest = claim.canonical_sha256
    return claim, PersistedSelectionIdentity(
        path=destination,
        source_sha256=digest,
        canonical_sha256=digest,
        byte_count=len(claim.canonical_bytes),
    )


def load_selection_attempt_claim(
    path: str | Path,
    *,
    expected_source_sha256: str,
    expected_canonical_sha256: str,
    freeze: SelectionFreezeArtifact,
) -> SelectionAttemptClaimArtifact:
    """Load and validate the exact canonical pre-run claim for a freeze."""

    expected_source = _sha256(
        expected_source_sha256,
        label="expected_source_sha256",
    )
    expected_canonical = _sha256(
        expected_canonical_sha256,
        label="expected_canonical_sha256",
    )
    source_path, source, document = _load_canonical_mapping(
        path,
        label="selection attempt claim",
    )
    if source_path != selection_attempt_claim_path(source_path.parent, freeze):
        raise QualificationContractError(
            "selection attempt claim path is not canonical for its freeze"
        )
    claim = SelectionAttemptClaimArtifact.from_dict(document)
    source_sha256 = hashlib.sha256(source).hexdigest()
    if (
        source_sha256 != expected_source
        or claim.canonical_sha256 != expected_canonical
        or source != claim.canonical_bytes
    ):
        raise QualificationContractError(
            "selection attempt claim source or canonical identity differs"
        )
    claim.validate_freeze(freeze)
    return claim


def validate_persisted_selection_attempt_claim(
    store_directory: str | Path,
    *,
    freeze: SelectionFreezeArtifact,
    attempt_claim: SelectionAttemptClaimArtifact,
) -> SelectionAttemptClaimArtifact:
    """Require the supplied claim to exist canonically in its freeze-keyed store."""

    if not isinstance(attempt_claim, SelectionAttemptClaimArtifact):
        raise TypeError("attempt_claim must be a SelectionAttemptClaimArtifact")
    _load_persisted_store_freeze(
        store_directory,
        freeze=freeze,
    )
    loaded = load_selection_attempt_claim(
        selection_attempt_claim_path(store_directory, freeze),
        expected_source_sha256=attempt_claim.canonical_sha256,
        expected_canonical_sha256=attempt_claim.canonical_sha256,
        freeze=freeze,
    )
    if loaded != attempt_claim:
        raise QualificationContractError(
            "persisted selection attempt claim differs from its companion"
        )
    return loaded


def selection_execution_start_path(
    store_directory: str | Path,
    freeze: SelectionFreezeArtifact,
) -> Path:
    """Return the sole freeze-keyed execution-start transition path."""

    if not isinstance(freeze, SelectionFreezeArtifact):
        raise TypeError("freeze must be a SelectionFreezeArtifact")
    directory = _absolute_path(store_directory)
    if not directory.is_dir() or directory.is_symlink():
        raise QualificationContractError(
            f"selection chronology store must be a real directory: {directory}"
        )
    return directory / (
        f"{selection_attempt_key_sha256(freeze)}{SELECTION_EXECUTION_START_SUFFIX}"
    )


def begin_selection_execution(
    store_directory: str | Path,
    *,
    freeze: SelectionFreezeArtifact,
    attempt_claim: SelectionAttemptClaimArtifact,
    loaded_protocol: object | None = None,
    launch_authorization: object | None = None,
) -> tuple[SelectionExecutionStartArtifact, PersistedSelectionIdentity]:
    """Atomically consume the sole right to enter one selection execution.

    The marker is retained after exceptions or process failure.  Its
    freeze-keyed ``O_EXCL`` publication therefore rejects a second runner call
    before any generator can be entered.
    """

    validate_persisted_selection_attempt_claim(
        store_directory,
        freeze=freeze,
        attempt_claim=attempt_claim,
    )
    from .launch import SelectionLaunchAuthorization
    from .persistence import LoadedQualificationProtocol
    from .preparation import CLOSED_D0_D5_PROTOCOL_ID

    if freeze.protocol_id == CLOSED_D0_D5_PROTOCOL_ID:
        if not isinstance(loaded_protocol, LoadedQualificationProtocol):
            raise QualificationContractError(
                "official execution start requires the full loaded protocol"
            )
        if not isinstance(launch_authorization, SelectionLaunchAuthorization):
            raise QualificationContractError(
                "official execution start requires typed committed-G launch "
                "authorization"
            )
        launch_authorization.validate_companions(
            loaded_protocol=loaded_protocol,
            freeze=freeze,
            attempt_claim=attempt_claim,
            attempt_store=store_directory,
        )
        selection_launch_authorization_sha256 = launch_authorization.canonical_sha256
        authorized_head_commit = launch_authorization.authorized_head_commit
    elif launch_authorization is None:
        selection_launch_authorization_sha256 = None
        authorized_head_commit = None
    else:
        raise QualificationContractError(
            "custom/development execution start does not accept launch authorization"
        )
    terminal_path = terminal_selection_transaction_path(
        store_directory,
        freeze,
    )
    if terminal_path.exists() or terminal_path.is_symlink():
        raise QualificationContractError(
            "selection attempt is already terminally consumed"
        )
    start = SelectionExecutionStartArtifact.from_companions(
        freeze=freeze,
        attempt_claim=attempt_claim,
        selection_launch_authorization_sha256=(selection_launch_authorization_sha256),
        authorized_head_commit=authorized_head_commit,
    )
    destination = selection_execution_start_path(store_directory, freeze)
    _write_exclusive_file(
        destination,
        start.canonical_bytes,
        label="selection execution-start artifact",
        maximum_bytes=MAX_SELECTION_CHRONOLOGY_ARTIFACT_BYTES,
    )
    _fsync_directory(destination.parent)
    digest = start.canonical_sha256
    return start, PersistedSelectionIdentity(
        path=destination,
        source_sha256=digest,
        canonical_sha256=digest,
        byte_count=len(start.canonical_bytes),
    )


def load_selection_execution_start(
    path: str | Path,
    *,
    expected_source_sha256: str,
    expected_canonical_sha256: str,
    freeze: SelectionFreezeArtifact,
    attempt_claim: SelectionAttemptClaimArtifact,
    loaded_protocol: object | None = None,
    launch_authorization: object | None = None,
) -> SelectionExecutionStartArtifact:
    """Load and validate the exact execution-start transition."""

    expected_source = _sha256(
        expected_source_sha256,
        label="expected_source_sha256",
    )
    expected_canonical = _sha256(
        expected_canonical_sha256,
        label="expected_canonical_sha256",
    )
    source_path, source, document = _load_canonical_mapping(
        path,
        label="selection execution-start artifact",
    )
    if source_path != selection_execution_start_path(source_path.parent, freeze):
        raise QualificationContractError(
            "selection execution-start path is not canonical for its freeze"
        )
    (
        selection_launch_authorization_sha256,
        authorized_head_commit,
    ) = _terminal_start_authorization_lineage(
        source_path.parent,
        freeze=freeze,
        attempt_claim=attempt_claim,
        loaded_protocol=loaded_protocol,
        launch_authorization=launch_authorization,
    )
    start = SelectionExecutionStartArtifact.from_dict(document)
    source_sha256 = hashlib.sha256(source).hexdigest()
    if (
        source_sha256 != expected_source
        or start.canonical_sha256 != expected_canonical
        or source != start.canonical_bytes
    ):
        raise QualificationContractError(
            "selection execution-start source or canonical identity differs"
        )
    start.validate_companions(
        freeze=freeze,
        attempt_claim=attempt_claim,
        selection_launch_authorization_sha256=(selection_launch_authorization_sha256),
        authorized_head_commit=authorized_head_commit,
    )
    return start


def _terminal_start_authorization_lineage(
    store_directory: str | Path,
    *,
    freeze: SelectionFreezeArtifact,
    attempt_claim: SelectionAttemptClaimArtifact,
    loaded_protocol: object | None,
    launch_authorization: object | None,
) -> tuple[str | None, str | None]:
    """Derive terminal start lineage only from a live typed authorization."""

    from .launch import SelectionLaunchAuthorization
    from .persistence import LoadedQualificationProtocol
    from .preparation import CLOSED_D0_D5_PROTOCOL_ID

    if freeze.protocol_id == CLOSED_D0_D5_PROTOCOL_ID:
        if not isinstance(loaded_protocol, LoadedQualificationProtocol):
            raise QualificationContractError(
                "official terminal chronology validation requires the full "
                "loaded protocol"
            )
        if not isinstance(launch_authorization, SelectionLaunchAuthorization):
            raise QualificationContractError(
                "official terminal chronology validation requires typed "
                "committed-G launch authorization"
            )
        launch_authorization.validate_terminal_companions(
            loaded_protocol=loaded_protocol,
            freeze=freeze,
            attempt_claim=attempt_claim,
            attempt_store=store_directory,
        )
        return (
            launch_authorization.canonical_sha256,
            launch_authorization.authorized_head_commit,
        )
    if loaded_protocol is not None or launch_authorization is not None:
        raise QualificationContractError(
            "custom/development terminal chronology validation requires "
            "loaded_protocol=None and launch_authorization=None"
        )
    return None, None


def validate_persisted_selection_execution_start(
    store_directory: str | Path,
    *,
    freeze: SelectionFreezeArtifact,
    attempt_claim: SelectionAttemptClaimArtifact,
    loaded_protocol: object | None = None,
    launch_authorization: object | None = None,
) -> SelectionExecutionStartArtifact:
    """Require the immutable start transition for an exact freeze and claim."""

    (
        selection_launch_authorization_sha256,
        authorized_head_commit,
    ) = _terminal_start_authorization_lineage(
        store_directory,
        freeze=freeze,
        attempt_claim=attempt_claim,
        loaded_protocol=loaded_protocol,
        launch_authorization=launch_authorization,
    )
    start_path = selection_execution_start_path(store_directory, freeze)
    _candidate_path, candidate_source, candidate_document = _load_canonical_mapping(
        start_path,
        label="selection execution-start artifact",
    )
    candidate = SelectionExecutionStartArtifact.from_dict(candidate_document)
    if candidate_source != candidate.canonical_bytes:
        raise QualificationContractError(
            "persisted selection execution-start is not exact canonical bytes"
        )
    expected = SelectionExecutionStartArtifact.from_companions(
        freeze=freeze,
        attempt_claim=attempt_claim,
        selection_launch_authorization_sha256=(selection_launch_authorization_sha256),
        authorized_head_commit=authorized_head_commit,
    )
    loaded = load_selection_execution_start(
        start_path,
        expected_source_sha256=expected.canonical_sha256,
        expected_canonical_sha256=expected.canonical_sha256,
        freeze=freeze,
        attempt_claim=attempt_claim,
        loaded_protocol=loaded_protocol,
        launch_authorization=launch_authorization,
    )
    if loaded != expected:
        raise QualificationContractError(
            "persisted selection execution-start differs from its companions"
        )
    return loaded


def terminal_selection_transaction_path(
    store_directory: str | Path,
    freeze: SelectionFreezeArtifact,
) -> Path:
    """Return the canonical atomic terminal-transaction path for one freeze."""

    if not isinstance(freeze, SelectionFreezeArtifact):
        raise TypeError("freeze must be a SelectionFreezeArtifact")
    directory = _absolute_path(store_directory)
    if not directory.is_dir() or directory.is_symlink():
        raise QualificationContractError(
            f"selection chronology store must be a real directory: {directory}"
        )
    return directory / (
        f"{selection_attempt_key_sha256(freeze)}{SELECTION_TERMINAL_TRANSACTION_SUFFIX}"
    )


def _validate_terminal_result_against_live_sources(
    terminal_artifact: object,
    *,
    loaded_protocol: object | None,
    freeze: SelectionFreezeArtifact,
    attempt_claim: SelectionAttemptClaimArtifact,
    selection_launch_authorization_sha256: str | None,
    repository_root: str | Path | None,
    registry_path: str | Path | None,
    referent_path: str | Path | None,
    historical_source_binding_receipt: object | None = None,
    historical_reload_capability: object | None = None,
) -> None:
    """Run the full result contract with exact successor-aware provenance.

    The default remains full live-source verification.  A committed historical
    reload may instead supply the exact execution-time receipt already
    cryptographically bound by the result's source-binding summary.
    """

    if historical_source_binding_receipt is not None:
        if historical_reload_capability is not _HISTORICAL_SOURCE_RELOAD_CAPABILITY:
            raise QualificationContractError(
                "historical source receipt requires the private archived-reload "
                "capability"
            )
    elif historical_reload_capability is not None:
        raise QualificationContractError(
            "historical reload capability requires a historical source receipt"
        )

    from .contracts import QualificationResult

    if not isinstance(terminal_artifact, QualificationResult):
        return
    from .persistence import LoadedQualificationProtocol
    from .source_binding import (
        QualificationSourceBindingReceipt,
        verify_protocol_source_binding_successor,
    )

    if not isinstance(loaded_protocol, LoadedQualificationProtocol):
        raise QualificationContractError(
            "result terminal publication requires the full loaded protocol"
        )
    if historical_source_binding_receipt is not None:
        if not isinstance(
            historical_source_binding_receipt,
            QualificationSourceBindingReceipt,
        ):
            raise TypeError(
                "historical_source_binding_receipt must be a "
                "QualificationSourceBindingReceipt or None"
            )
        if any(
            value is not None
            for value in (repository_root, registry_path, referent_path)
        ):
            raise QualificationContractError(
                "historical source verification does not accept live source paths"
            )
        freeze.validate_loaded_protocol(loaded_protocol=loaded_protocol)
        terminal_artifact.validate_against_protocol(
            loaded_protocol.protocol,
            protocol_source_sha256=loaded_protocol.source_sha256,
            source_binding_receipt=historical_source_binding_receipt,
            selection_freeze_artifact=freeze,
            selection_attempt_claim=attempt_claim,
            selection_launch_authorization_sha256=(
                selection_launch_authorization_sha256
            ),
            _historical_reload_capability=(
                _HISTORICAL_SOURCE_RELOAD_CAPABILITY
            ),
        )
        return
    if repository_root is None or registry_path is None or referent_path is None:
        raise QualificationContractError(
            "result terminal publication requires live source-verification paths"
        )
    freeze.validate_loaded_protocol(loaded_protocol=loaded_protocol)
    execution_receipt = verify_protocol_source_binding_successor(
        loaded_protocol.protocol,
        source_binding_summary=terminal_artifact.source_binding,
        repository_root=repository_root,
        registry_path=registry_path,
        referent_path=referent_path,
    )
    terminal_artifact.validate_against_protocol(
        loaded_protocol.protocol,
        protocol_source_sha256=loaded_protocol.source_sha256,
        source_binding_receipt=execution_receipt,
        selection_freeze_artifact=freeze,
        selection_attempt_claim=attempt_claim,
        selection_launch_authorization_sha256=(selection_launch_authorization_sha256),
    )


def _terminal_launch_authorization_sha256(
    terminal_artifact: object,
) -> str | None:
    """Return the typed terminal artifact's exact launch lineage."""

    from .contracts import QualificationResult

    if isinstance(
        terminal_artifact,
        (QualificationResult, SelectionFailedAttemptArtifact),
    ):
        return terminal_artifact.selection_launch_authorization_sha256
    raise TypeError(
        "terminal_artifact must be a QualificationResult or "
        "SelectionFailedAttemptArtifact"
    )


def publish_terminal_selection_consumption(
    store_directory: str | Path,
    *,
    consumption_id: str,
    freeze: SelectionFreezeArtifact,
    attempt_claim: SelectionAttemptClaimArtifact,
    terminal_artifact: object,
    loaded_protocol: object | None = None,
    launch_authorization: object | None = None,
    repository_root: str | Path | None = None,
    registry_path: str | Path | None = None,
    referent_path: str | Path | None = None,
) -> tuple[
    SelectionConsumptionArtifact,
    PersistedSelectionTerminalIdentity,
]:
    """Atomically publish terminal bytes, consumption, and their manifest.

    The transaction cannot be published without the canonical persisted claim.
    Its freeze-derived destination is an immutable non-empty directory, so a
    second result or failed-attempt publication cannot replace it.
    """

    validate_persisted_selection_attempt_claim(
        store_directory,
        freeze=freeze,
        attempt_claim=attempt_claim,
    )
    terminal_authorization_sha256 = _terminal_launch_authorization_sha256(
        terminal_artifact
    )
    from .preparation import CLOSED_D0_D5_PROTOCOL_ID

    chronology_loaded_protocol = (
        loaded_protocol if freeze.protocol_id == CLOSED_D0_D5_PROTOCOL_ID else None
    )
    start = validate_persisted_selection_execution_start(
        store_directory,
        freeze=freeze,
        attempt_claim=attempt_claim,
        loaded_protocol=chronology_loaded_protocol,
        launch_authorization=launch_authorization,
    )
    if terminal_authorization_sha256 != start.selection_launch_authorization_sha256:
        raise QualificationContractError(
            "terminal artifact launch authorization differs from the typed "
            "execution-start lineage"
        )
    _validate_terminal_result_against_live_sources(
        terminal_artifact,
        loaded_protocol=loaded_protocol,
        freeze=freeze,
        attempt_claim=attempt_claim,
        selection_launch_authorization_sha256=(
            start.selection_launch_authorization_sha256
        ),
        repository_root=repository_root,
        registry_path=registry_path,
        referent_path=referent_path,
    )
    consumption = SelectionConsumptionArtifact.consume(
        consumption_id=consumption_id,
        freeze=freeze,
        attempt_claim=attempt_claim,
        terminal_artifact=terminal_artifact,
    )
    consumption.validate_terminal_artifact(
        freeze=freeze,
        attempt_claim=attempt_claim,
        terminal_artifact=terminal_artifact,
    )

    from .contracts import QualificationResult

    if isinstance(terminal_artifact, QualificationResult):
        terminal_kind = TerminalAttemptArtifactKind.RESULT
    elif isinstance(terminal_artifact, SelectionFailedAttemptArtifact):
        terminal_kind = TerminalAttemptArtifactKind.FAILED_ATTEMPT
    else:  # Defensive: consume() already rejects this branch.
        raise TypeError(
            "terminal_artifact must be a QualificationResult or "
            "SelectionFailedAttemptArtifact"
        )
    terminal_bytes = terminal_artifact.canonical_bytes
    if (
        not terminal_bytes
        or len(terminal_bytes) > MAX_SELECTION_TERMINAL_ARTIFACT_BYTES
    ):
        raise QualificationContractError(
            "terminal artifact exceeds the fixed transaction byte cap"
        )
    consumption_bytes = consumption.canonical_bytes
    manifest = SelectionTerminalManifestArtifact(
        freeze_artifact_sha256=freeze.canonical_sha256,
        attempt_claim_sha256=attempt_claim.canonical_sha256,
        terminal_artifact_kind=terminal_kind,
        terminal_artifact_sha256=terminal_artifact.canonical_sha256,
        terminal_artifact_byte_count=len(terminal_bytes),
        consumption_sha256=consumption.canonical_sha256,
        consumption_byte_count=len(consumption_bytes),
    )

    destination = terminal_selection_transaction_path(
        store_directory,
        freeze,
    )
    if destination.exists() or destination.is_symlink():
        raise QualificationContractError(
            "refusing to overwrite existing selection terminal transaction: "
            f"{destination}"
        )
    stage = Path(
        tempfile.mkdtemp(
            dir=destination.parent,
            prefix=(f".{selection_attempt_key_sha256(freeze)}.selection-terminal."),
            suffix=".tmp",
        )
    )
    published = False
    try:
        _write_exclusive_file(
            stage / SELECTION_TERMINAL_ARTIFACT_FILENAME,
            terminal_bytes,
            label="selection terminal artifact",
            maximum_bytes=MAX_SELECTION_TERMINAL_ARTIFACT_BYTES,
        )
        _write_exclusive_file(
            stage / SELECTION_TERMINAL_CONSUMPTION_FILENAME,
            consumption_bytes,
            label="selection terminal consumption",
            maximum_bytes=MAX_SELECTION_CHRONOLOGY_ARTIFACT_BYTES,
        )
        _write_exclusive_file(
            stage / SELECTION_TERMINAL_MANIFEST_FILENAME,
            manifest.canonical_bytes,
            label="selection terminal manifest",
            maximum_bytes=MAX_SELECTION_CHRONOLOGY_ARTIFACT_BYTES,
        )
        _fsync_directory(stage)
        _rename_directory_no_replace(stage, destination)
        published = True
        _fsync_directory(destination.parent)
    finally:
        if not published and stage.exists():
            for filename in (
                SELECTION_TERMINAL_ARTIFACT_FILENAME,
                SELECTION_TERMINAL_CONSUMPTION_FILENAME,
                SELECTION_TERMINAL_MANIFEST_FILENAME,
            ):
                try:
                    (stage / filename).unlink()
                except FileNotFoundError:
                    pass
            try:
                stage.rmdir()
            except OSError:
                # Unknown content is never deleted by cleanup.
                pass

    return consumption, PersistedSelectionTerminalIdentity(
        path=destination,
        manifest_sha256=manifest.canonical_sha256,
        terminal_artifact_sha256=terminal_artifact.canonical_sha256,
        consumption_sha256=consumption.canonical_sha256,
    )


def load_terminal_selection_consumption(
    path: str | Path,
    *,
    expected_manifest_sha256: str,
    expected_terminal_artifact_sha256: str,
    expected_consumption_sha256: str,
    freeze: SelectionFreezeArtifact,
    attempt_claim: SelectionAttemptClaimArtifact,
    loaded_protocol: object | None = None,
    launch_authorization: object | None = None,
    repository_root: str | Path | None = None,
    registry_path: str | Path | None = None,
    referent_path: str | Path | None = None,
    _historical_source_binding_receipt: object | None = None,
    _historical_reload_capability: object | None = None,
) -> tuple[SelectionConsumptionArtifact, object]:
    """Load and validate every member of an atomic terminal transaction."""

    expected_manifest = _sha256(
        expected_manifest_sha256,
        label="expected_manifest_sha256",
    )
    expected_terminal = _sha256(
        expected_terminal_artifact_sha256,
        label="expected_terminal_artifact_sha256",
    )
    expected_consumption = _sha256(
        expected_consumption_sha256,
        label="expected_consumption_sha256",
    )
    transaction_path = _absolute_path(path)
    if transaction_path.is_symlink() or not transaction_path.is_dir():
        raise QualificationContractError(
            "selection terminal transaction must be a real directory"
        )
    if transaction_path != terminal_selection_transaction_path(
        transaction_path.parent,
        freeze,
    ):
        raise QualificationContractError(
            "selection terminal transaction path is not canonical for its freeze"
        )
    validate_persisted_selection_attempt_claim(
        transaction_path.parent,
        freeze=freeze,
        attempt_claim=attempt_claim,
    )
    from .preparation import CLOSED_D0_D5_PROTOCOL_ID

    chronology_loaded_protocol = (
        loaded_protocol if freeze.protocol_id == CLOSED_D0_D5_PROTOCOL_ID else None
    )
    start = validate_persisted_selection_execution_start(
        transaction_path.parent,
        freeze=freeze,
        attempt_claim=attempt_claim,
        loaded_protocol=chronology_loaded_protocol,
        launch_authorization=launch_authorization,
    )
    try:
        filenames = {item.name for item in transaction_path.iterdir()}
    except OSError as error:
        raise QualificationContractError(
            f"cannot inspect selection terminal transaction: {error}"
        ) from error
    expected_filenames = {
        SELECTION_TERMINAL_ARTIFACT_FILENAME,
        SELECTION_TERMINAL_CONSUMPTION_FILENAME,
        SELECTION_TERMINAL_MANIFEST_FILENAME,
    }
    if filenames != expected_filenames:
        raise QualificationContractError(
            "selection terminal transaction members differ from the contract"
        )

    _manifest_path, manifest_source, manifest_document = _load_canonical_mapping(
        transaction_path / SELECTION_TERMINAL_MANIFEST_FILENAME,
        label="selection terminal manifest",
    )
    manifest = SelectionTerminalManifestArtifact.from_dict(manifest_document)
    if (
        manifest_source != manifest.canonical_bytes
        or manifest.canonical_sha256 != expected_manifest
        or manifest.freeze_artifact_sha256 != freeze.canonical_sha256
        or manifest.attempt_claim_sha256 != attempt_claim.canonical_sha256
    ):
        raise QualificationContractError(
            "selection terminal manifest identity or companion join differs"
        )

    _terminal_path, terminal_source, terminal_document = (
        _load_bounded_canonical_mapping(
            transaction_path / SELECTION_TERMINAL_ARTIFACT_FILENAME,
            label="selection terminal artifact",
            maximum_bytes=MAX_SELECTION_TERMINAL_ARTIFACT_BYTES,
        )
    )
    if manifest.terminal_artifact_kind is TerminalAttemptArtifactKind.RESULT:
        from .contracts import QualificationResult

        terminal_artifact: object = QualificationResult.from_dict(terminal_document)
    else:
        terminal_artifact = SelectionFailedAttemptArtifact.from_dict(terminal_document)
    terminal_canonical_bytes = terminal_artifact.canonical_bytes  # type: ignore[attr-defined]
    terminal_canonical_sha256 = terminal_artifact.canonical_sha256  # type: ignore[attr-defined]
    if (
        terminal_source != terminal_canonical_bytes
        or terminal_canonical_sha256 != expected_terminal
        or terminal_canonical_sha256 != manifest.terminal_artifact_sha256
        or len(terminal_source) != manifest.terminal_artifact_byte_count
    ):
        raise QualificationContractError(
            "terminal artifact identity differs from its manifest"
        )
    if (
        _terminal_launch_authorization_sha256(terminal_artifact)
        != start.selection_launch_authorization_sha256
    ):
        raise QualificationContractError(
            "terminal artifact launch authorization differs from the typed "
            "execution-start lineage"
        )
    _validate_terminal_result_against_live_sources(
        terminal_artifact,
        loaded_protocol=loaded_protocol,
        freeze=freeze,
        attempt_claim=attempt_claim,
        selection_launch_authorization_sha256=(
            start.selection_launch_authorization_sha256
        ),
        repository_root=repository_root,
        registry_path=registry_path,
        referent_path=referent_path,
        historical_source_binding_receipt=_historical_source_binding_receipt,
        historical_reload_capability=_historical_reload_capability,
    )

    _consumption_path, consumption_source, consumption_document = (
        _load_canonical_mapping(
            transaction_path / SELECTION_TERMINAL_CONSUMPTION_FILENAME,
            label="selection terminal consumption",
        )
    )
    consumption = SelectionConsumptionArtifact.from_dict(consumption_document)
    if (
        consumption_source != consumption.canonical_bytes
        or consumption.canonical_sha256 != expected_consumption
        or consumption.canonical_sha256 != manifest.consumption_sha256
        or len(consumption_source) != manifest.consumption_byte_count
    ):
        raise QualificationContractError(
            "selection consumption identity differs from its manifest"
        )
    consumption.validate_terminal_artifact(
        freeze=freeze,
        attempt_claim=attempt_claim,
        terminal_artifact=terminal_artifact,
    )
    return consumption, terminal_artifact
