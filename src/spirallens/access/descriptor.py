"""Strict persistence and descriptor-only preparation views.

Preparation reads one pre-observation descriptor.  It deliberately has no
atlas-directory or manifest argument, so outcome-bearing manifests and payload
files cannot enter this code path by redaction after the fact.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat

from spirallens._held_file import (
    _open_directory_chain as _open_held_directory_chain,
    _read_bounded_regular_file as _read_held_file,
)
from spirallens.core.canonical import (
    CanonicalJsonError,
    canonical_json_bytes,
    canonical_json_sha256,
    parse_canonical_json,
)

from .contracts import (
    AtlasAccessContractError,
    AtlasConsumer,
    AtlasConsumerDenied,
    AtlasPreparationDescriptor,
    require_atlas_consumer,
)


ATLAS_PREPARATION_VIEW_SCHEMA_VERSION = "spirallens.atlas-preparation-view.v0.1"
MAX_ATLAS_PREPARATION_DESCRIPTOR_BYTES = 1_048_576


@dataclass(frozen=True, slots=True)
class LoadedAtlasPreparationDescriptor:
    """A descriptor plus exact source identity and its one-file read trace."""

    descriptor: AtlasPreparationDescriptor
    source_path: Path
    source_sha256: str
    canonical_sha256: str
    read_trace: tuple[Path, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.descriptor, AtlasPreparationDescriptor):
            raise TypeError("descriptor must be an AtlasPreparationDescriptor")
        if not isinstance(self.source_path, Path) or not self.source_path.is_absolute():
            raise TypeError("source_path must be an absolute Path")
        for name in ("source_sha256", "canonical_sha256"):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                raise TypeError(f"{name} must be a lowercase SHA-256 digest")
        if self.read_trace != (self.source_path,):
            raise AtlasAccessContractError(
                "descriptor load trace must contain exactly its source file"
            )


@dataclass(frozen=True, slots=True)
class AtlasPreparationView:
    """Canonical record emitted by the descriptor-only preparation path."""

    descriptor_id: str
    descriptor_source_sha256: str
    descriptor_canonical_sha256: str
    access_policy_sha256: str
    requested_consumer: AtlasConsumer
    protocol_id: str
    protocol_canonical_sha256: str
    model_id: str
    model_revision: str
    context_id: str
    row_count: int
    output_id: str

    def __post_init__(self) -> None:
        if self.requested_consumer is not AtlasConsumer.SUBJECT_PROTOCOL_PREPARATION:
            raise AtlasAccessContractError(
                "preparation view consumer must be subject_protocol_preparation"
            )
        if type(self.row_count) is not int or self.row_count <= 0:
            raise AtlasAccessContractError("row_count must be a positive integer")
        for name in (
            "descriptor_id",
            "protocol_id",
            "model_id",
            "model_revision",
            "context_id",
            "output_id",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise AtlasAccessContractError(f"{name} must be a non-empty string")
        for name in (
            "descriptor_source_sha256",
            "descriptor_canonical_sha256",
            "access_policy_sha256",
            "protocol_canonical_sha256",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                raise AtlasAccessContractError(
                    f"{name} must be a lowercase SHA-256 digest"
                )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": ATLAS_PREPARATION_VIEW_SCHEMA_VERSION,
            "status": "prepared_metadata_only",
            "descriptor_id": self.descriptor_id,
            "descriptor_source_sha256": self.descriptor_source_sha256,
            "descriptor_canonical_sha256": (self.descriptor_canonical_sha256),
            "access_policy_sha256": self.access_policy_sha256,
            "requested_consumer": self.requested_consumer.value,
            "protocol_id": self.protocol_id,
            "protocol_canonical_sha256": (self.protocol_canonical_sha256),
            "model_id": self.model_id,
            "model_revision": self.model_revision,
            "context_id": self.context_id,
            "row_count": self.row_count,
            "output_id": self.output_id,
            "authorization_scope": "preobservation_metadata_only",
            "subject_values_observed": False,
            "manifest_read": False,
            "payload_files_read": False,
            "subject_execution_authorized": False,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, object],
    ) -> "AtlasPreparationView":
        if not isinstance(value, Mapping) or any(
            not isinstance(key, str) for key in value
        ):
            raise AtlasAccessContractError(
                "atlas preparation view must be a string-keyed mapping"
            )
        fields = {
            "schema_version",
            "status",
            "descriptor_id",
            "descriptor_source_sha256",
            "descriptor_canonical_sha256",
            "access_policy_sha256",
            "requested_consumer",
            "protocol_id",
            "protocol_canonical_sha256",
            "model_id",
            "model_revision",
            "context_id",
            "row_count",
            "output_id",
            "authorization_scope",
            "subject_values_observed",
            "manifest_read",
            "payload_files_read",
            "subject_execution_authorized",
        }
        actual = set(value)
        if actual != fields:
            raise AtlasAccessContractError(
                "atlas preparation view fields differ from the contract: "
                f"missing={sorted(fields - actual)}, "
                f"unknown={sorted(actual - fields)}"
            )
        constants = {
            "schema_version": ATLAS_PREPARATION_VIEW_SCHEMA_VERSION,
            "status": "prepared_metadata_only",
            "requested_consumer": (AtlasConsumer.SUBJECT_PROTOCOL_PREPARATION.value),
            "authorization_scope": "preobservation_metadata_only",
            "subject_values_observed": False,
            "manifest_read": False,
            "payload_files_read": False,
            "subject_execution_authorized": False,
        }
        for name, expected in constants.items():
            if type(value[name]) is not type(expected) or value[name] != expected:
                raise AtlasAccessContractError(
                    f"atlas preparation view {name} must equal {expected!r}"
                )
        row_count = value["row_count"]
        if type(row_count) is not int or row_count <= 0:
            raise AtlasAccessContractError(
                "atlas preparation view row_count must be a positive integer"
            )
        string_fields = (
            "descriptor_id",
            "protocol_id",
            "model_id",
            "model_revision",
            "context_id",
            "output_id",
        )
        for name in string_fields:
            if not isinstance(value[name], str) or not value[name]:
                raise AtlasAccessContractError(
                    f"atlas preparation view {name} must be a non-empty string"
                )
        return cls(
            descriptor_id=value["descriptor_id"],
            descriptor_source_sha256=_lowercase_sha256(
                value["descriptor_source_sha256"],
                label="descriptor_source_sha256",
            ),
            descriptor_canonical_sha256=_lowercase_sha256(
                value["descriptor_canonical_sha256"],
                label="descriptor_canonical_sha256",
            ),
            access_policy_sha256=_lowercase_sha256(
                value["access_policy_sha256"],
                label="access_policy_sha256",
            ),
            requested_consumer=(AtlasConsumer.SUBJECT_PROTOCOL_PREPARATION),
            protocol_id=value["protocol_id"],
            protocol_canonical_sha256=_lowercase_sha256(
                value["protocol_canonical_sha256"],
                label="protocol_canonical_sha256",
            ),
            model_id=value["model_id"],
            model_revision=value["model_revision"],
            context_id=value["context_id"],
            row_count=row_count,
            output_id=value["output_id"],
        )


def _lowercase_sha256(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise AtlasAccessContractError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _absolute_path(path: str | Path, *, label: str) -> Path:
    value = Path(path)
    absolute = Path(os.path.abspath(value))
    if not absolute.name:
        raise AtlasAccessContractError(f"{label} must name one file")
    return absolute


def _open_directory_chain(directory: Path) -> int:
    if not directory.is_absolute():
        raise AtlasAccessContractError("descriptor parent directory must be absolute")
    return _open_held_directory_chain(directory)


def _read_bounded_regular_file(path: Path) -> bytes:
    messages = (
        f"cannot safely open descriptor parent: {path.parent}",
        f"cannot safely read atlas preparation descriptor: {path}",
        "atlas preparation descriptor must be a regular file",
        "atlas preparation descriptor must have exactly one link",
        "atlas preparation descriptor exceeds the size limit",
        "atlas preparation descriptor changed during read",
    )
    return _read_held_file(
        path,
        maximum_bytes=MAX_ATLAS_PREPARATION_DESCRIPTOR_BYTES,
        error_type=AtlasAccessContractError,
        messages=messages,
    )


def load_atlas_preparation_descriptor(
    path: str | Path,
    *,
    expected_source_sha256: str,
    expected_canonical_sha256: str,
) -> LoadedAtlasPreparationDescriptor:
    """Load one canonical descriptor without reading an atlas or manifest."""

    source_path = _absolute_path(path, label="descriptor path")
    expected_source = _lowercase_sha256(
        expected_source_sha256,
        label="expected_source_sha256",
    )
    expected_canonical = _lowercase_sha256(
        expected_canonical_sha256,
        label="expected_canonical_sha256",
    )
    source = _read_bounded_regular_file(source_path)
    source_sha256 = hashlib.sha256(source).hexdigest()
    if source_sha256 != expected_source:
        raise AtlasAccessContractError(
            "atlas preparation descriptor source SHA-256 mismatch"
        )
    try:
        parsed = parse_canonical_json(
            source,
            label="atlas preparation descriptor",
        )
    except CanonicalJsonError as error:
        raise AtlasAccessContractError(str(error)) from error
    if not isinstance(parsed, dict):
        raise AtlasAccessContractError(
            "atlas preparation descriptor must contain one object"
        )
    descriptor = AtlasPreparationDescriptor.from_dict(parsed)
    canonical_sha256 = descriptor.canonical_sha256
    if canonical_sha256 != expected_canonical:
        raise AtlasAccessContractError(
            "atlas preparation descriptor canonical SHA-256 mismatch"
        )
    if descriptor.canonical_bytes != source:
        raise AtlasAccessContractError(
            "atlas preparation descriptor typed round-trip differs"
        )
    return LoadedAtlasPreparationDescriptor(
        descriptor=descriptor,
        source_path=source_path,
        source_sha256=source_sha256,
        canonical_sha256=canonical_sha256,
        read_trace=(source_path,),
    )


def prepare_descriptor_only_view(
    loaded: LoadedAtlasPreparationDescriptor,
    *,
    consumer: AtlasConsumer,
) -> AtlasPreparationView:
    """Authorize and bind a preparation view without further file access."""

    if not isinstance(loaded, LoadedAtlasPreparationDescriptor):
        raise TypeError("loaded must be a LoadedAtlasPreparationDescriptor")
    if not isinstance(consumer, AtlasConsumer):
        raise TypeError("consumer must be an AtlasConsumer")
    if consumer is not AtlasConsumer.SUBJECT_PROTOCOL_PREPARATION:
        raise AtlasConsumerDenied(
            "descriptor-only preparation cannot authorize "
            f"{consumer.value!r}; only "
            f"{AtlasConsumer.SUBJECT_PROTOCOL_PREPARATION.value!r} is "
            "valid for this view"
        )
    require_atlas_consumer(loaded.descriptor.access_policy, consumer)
    descriptor = loaded.descriptor
    return AtlasPreparationView(
        descriptor_id=descriptor.descriptor_id,
        descriptor_source_sha256=loaded.source_sha256,
        descriptor_canonical_sha256=loaded.canonical_sha256,
        access_policy_sha256=descriptor.access_policy.sha256,
        requested_consumer=consumer,
        protocol_id=descriptor.protocol.protocol_id,
        protocol_canonical_sha256=(descriptor.protocol.canonical_sha256),
        model_id=descriptor.model.model_id,
        model_revision=descriptor.model.revision,
        context_id=descriptor.context.context_id,
        row_count=descriptor.row_domain.row_count,
        output_id=descriptor.capture.output_id,
    )


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise OSError("descriptor write made no forward progress")
        offset += written


def write_atlas_preparation_descriptor(
    path: str | Path,
    descriptor: AtlasPreparationDescriptor,
) -> LoadedAtlasPreparationDescriptor:
    """Publish one canonical descriptor exclusively and validate its readback."""

    if not isinstance(descriptor, AtlasPreparationDescriptor):
        raise TypeError("descriptor must be an AtlasPreparationDescriptor")
    payload = descriptor.canonical_bytes
    if len(payload) > MAX_ATLAS_PREPARATION_DESCRIPTOR_BYTES:
        raise AtlasAccessContractError(
            "atlas preparation descriptor exceeds the size limit"
        )
    output = _absolute_path(path, label="descriptor output path")
    parent_descriptor = _open_directory_chain(output.parent)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    file_descriptor = -1
    try:
        file_descriptor = os.open(
            output.name,
            flags,
            0o600,
            dir_fd=parent_descriptor,
        )
        _write_all(file_descriptor, payload)
        os.fsync(file_descriptor)
        metadata = os.fstat(file_descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise AtlasAccessContractError("published descriptor identity is invalid")
        os.fsync(parent_descriptor)
    except FileExistsError as error:
        raise AtlasAccessContractError(
            "atlas preparation descriptor already exists; overwrite is forbidden"
        ) from error
    finally:
        if file_descriptor >= 0:
            os.close(file_descriptor)
        os.close(parent_descriptor)
    return load_atlas_preparation_descriptor(
        output,
        expected_source_sha256=hashlib.sha256(payload).hexdigest(),
        expected_canonical_sha256=descriptor.canonical_sha256,
    )
