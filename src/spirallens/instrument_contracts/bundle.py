"""Canonical closed-world index for instrument contract bundles.

The index names artifact manifests and opaque payload files by content
identity.  It does not itself qualify an instrument, decode payload values,
load a model, run an estimator, construct a graph, or authorize subject data
access.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import ClassVar, TypeVar

from spirallens.contexts import ContextRole

from .canonical import canonical_json_bytes, canonical_json_sha256
from .common import (
    ArtifactRef,
    ArtifactType,
    ContractValidationError,
    PayloadRef,
    enum_from_value,
    exact_keys,
    require_bool,
    require_mapping,
    require_sha256,
    require_slug,
    require_string,
)


INSTRUMENT_BUNDLE_SCHEMA_VERSION = "spirallens.instrument-bundle.v0.1"
ARTIFACT_REFERENCE_POLICY = "closed_world"
PAYLOAD_REFERENCE_POLICY = "closed_world"

_EXTERNAL_ARTIFACT_TYPES = {
    ArtifactType.HYPOTHESIS_REGISTRY,
    ArtifactType.CONTEXT_BANK,
}
_INSTRUMENT_ARTIFACT_TYPES = set(ArtifactType) - _EXTERNAL_ARTIFACT_TYPES


def _relative_path(value: object, *, label: str) -> str:
    text = require_string(value, label=label)
    if "\x00" in text:
        raise ContractValidationError(f"{label} must not contain NUL")
    if "\\" in text:
        raise ContractValidationError(f"{label} must use canonical POSIX separators")
    path = PurePosixPath(text)
    if (
        path.is_absolute()
        or text != path.as_posix()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ContractValidationError(
            f"{label} must be a normalized bundle-relative path"
        )
    return text


@dataclass(frozen=True, slots=True)
class BundleArtifactEntry:
    """One instrument artifact or hypothesis-registry file."""

    path: str
    source_sha256: str
    reference: ArtifactRef

    def __post_init__(self) -> None:
        _relative_path(self.path, label="artifact entry path")
        require_sha256(
            self.source_sha256,
            label="artifact entry source_sha256",
        )
        if not isinstance(self.reference, ArtifactRef):
            raise TypeError("artifact entry reference must be an ArtifactRef")
        if self.reference.artifact_type is ArtifactType.CONTEXT_BANK:
            raise ContractValidationError(
                "context-bank entries require an explicit allowed role"
            )

    @property
    def sort_key(self) -> tuple[str, ...]:
        ref = self.reference
        return (
            ref.artifact_type.value,
            ref.artifact_id,
            ref.schema_version,
            ref.canonical_sha256,
            self.path,
            self.source_sha256,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "source_sha256": self.source_sha256,
            "reference": self.reference.to_dict(),
        }

    @classmethod
    def from_dict(
        cls,
        value: object,
        *,
        label: str,
    ) -> "BundleArtifactEntry":
        document = require_mapping(value, label=label)
        exact_keys(
            document,
            {"path", "source_sha256", "reference"},
            label=label,
        )
        return cls(
            path=_relative_path(document["path"], label=f"{label}.path"),
            source_sha256=require_sha256(
                document["source_sha256"],
                label=f"{label}.source_sha256",
            ),
            reference=ArtifactRef.from_dict(
                require_mapping(
                    document["reference"],
                    label=f"{label}.reference",
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class BundleContextBankEntry:
    """One context bank plus the exact role permitted for this bundle."""

    path: str
    source_sha256: str
    reference: ArtifactRef
    allowed_role: ContextRole

    def __post_init__(self) -> None:
        _relative_path(self.path, label="context-bank entry path")
        require_sha256(
            self.source_sha256,
            label="context-bank entry source_sha256",
        )
        if not isinstance(self.reference, ArtifactRef):
            raise TypeError("context-bank entry reference must be an ArtifactRef")
        if self.reference.artifact_type is not ArtifactType.CONTEXT_BANK:
            raise ContractValidationError(
                "context-bank entry must reference a context bank"
            )
        if not isinstance(self.allowed_role, ContextRole):
            raise TypeError("allowed_role must be a ContextRole")

    @property
    def sort_key(self) -> tuple[str, ...]:
        ref = self.reference
        return (
            ref.artifact_type.value,
            ref.artifact_id,
            ref.schema_version,
            ref.canonical_sha256,
            self.allowed_role.value,
            self.path,
            self.source_sha256,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "source_sha256": self.source_sha256,
            "reference": self.reference.to_dict(),
            "allowed_role": self.allowed_role.value,
        }

    @classmethod
    def from_dict(
        cls,
        value: object,
        *,
        label: str,
    ) -> "BundleContextBankEntry":
        document = require_mapping(value, label=label)
        exact_keys(
            document,
            {"path", "source_sha256", "reference", "allowed_role"},
            label=label,
        )
        return cls(
            path=_relative_path(document["path"], label=f"{label}.path"),
            source_sha256=require_sha256(
                document["source_sha256"],
                label=f"{label}.source_sha256",
            ),
            reference=ArtifactRef.from_dict(
                require_mapping(
                    document["reference"],
                    label=f"{label}.reference",
                )
            ),
            allowed_role=enum_from_value(
                ContextRole,
                document["allowed_role"],
                label=f"{label}.allowed_role",
            ),
        )


@dataclass(frozen=True, slots=True)
class BundlePayloadEntry:
    """One opaque payload file bound by its complete PayloadRef."""

    path: str
    reference: PayloadRef

    def __post_init__(self) -> None:
        _relative_path(self.path, label="payload entry path")
        if not isinstance(self.reference, PayloadRef):
            raise TypeError("payload entry reference must be a PayloadRef")

    @property
    def sort_key(self) -> tuple[str, ...]:
        return (
            self.reference.sha256,
            self.reference.identity_sha256,
            self.path,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "reference": self.reference.to_dict(),
        }

    @classmethod
    def from_dict(
        cls,
        value: object,
        *,
        label: str,
    ) -> "BundlePayloadEntry":
        document = require_mapping(value, label=label)
        exact_keys(document, {"path", "reference"}, label=label)
        return cls(
            path=_relative_path(document["path"], label=f"{label}.path"),
            reference=PayloadRef.from_dict(
                require_mapping(
                    document["reference"],
                    label=f"{label}.reference",
                )
            ),
        )


EntryValue = TypeVar(
    "EntryValue",
    BundleArtifactEntry,
    BundleContextBankEntry,
    BundlePayloadEntry,
)


def _canonical_entries(
    values: tuple[EntryValue, ...],
    *,
    label: str,
) -> tuple[EntryValue, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{label} must be a tuple")
    if any(
        not isinstance(
            value,
            (
                BundleArtifactEntry,
                BundleContextBankEntry,
                BundlePayloadEntry,
            ),
        )
        for value in values
    ):
        raise TypeError(f"{label} contains an invalid entry")
    keys = [value.sort_key for value in values]
    if keys != sorted(set(keys)):
        raise ContractValidationError(f"{label} must be unique and canonically sorted")
    return values


def _canonical_roots(
    values: tuple[ArtifactRef, ...],
) -> tuple[ArtifactRef, ...]:
    if not isinstance(values, tuple):
        raise TypeError("roots must be a tuple")
    if not values:
        raise ContractValidationError("roots must not be empty")
    if any(not isinstance(value, ArtifactRef) for value in values):
        raise TypeError("roots must contain ArtifactRef values")
    keys = [
        (
            value.artifact_type.value,
            value.artifact_id,
            value.schema_version,
            value.canonical_sha256,
        )
        for value in values
    ]
    if keys != sorted(set(keys)):
        raise ContractValidationError("roots must be unique and canonically sorted")
    return values


@dataclass(frozen=True, slots=True)
class InstrumentBundleManifest:
    """Canonical, closed-world artifact and payload index."""

    bundle_id: str
    roots: tuple[ArtifactRef, ...]
    instrument_artifacts: tuple[BundleArtifactEntry, ...]
    hypothesis_registries: tuple[BundleArtifactEntry, ...]
    context_banks: tuple[BundleContextBankEntry, ...]
    payloads: tuple[BundlePayloadEntry, ...]
    subject_data_access_authorized: bool = False

    schema_version: ClassVar[str] = INSTRUMENT_BUNDLE_SCHEMA_VERSION
    artifact_reference_policy: ClassVar[str] = ARTIFACT_REFERENCE_POLICY
    payload_reference_policy: ClassVar[str] = PAYLOAD_REFERENCE_POLICY

    def __post_init__(self) -> None:
        require_slug(self.bundle_id, label="bundle_id")
        _canonical_roots(self.roots)
        if any(
            not isinstance(value, BundleArtifactEntry)
            for value in self.instrument_artifacts
        ):
            raise TypeError(
                "instrument_artifacts must contain BundleArtifactEntry values"
            )
        if any(
            not isinstance(value, BundleArtifactEntry)
            for value in self.hypothesis_registries
        ):
            raise TypeError(
                "hypothesis_registries must contain BundleArtifactEntry values"
            )
        if any(
            not isinstance(value, BundleContextBankEntry)
            for value in self.context_banks
        ):
            raise TypeError("context_banks must contain BundleContextBankEntry values")
        if any(not isinstance(value, BundlePayloadEntry) for value in self.payloads):
            raise TypeError("payloads must contain BundlePayloadEntry values")
        _canonical_entries(
            self.instrument_artifacts,
            label="instrument_artifacts",
        )
        _canonical_entries(
            self.hypothesis_registries,
            label="hypothesis_registries",
        )
        _canonical_entries(self.context_banks, label="context_banks")
        _canonical_entries(self.payloads, label="payloads")
        if self.subject_data_access_authorized is not False:
            raise ContractValidationError(
                "instrument bundle cannot authorize subject data access"
            )
        if not self.instrument_artifacts:
            raise ContractValidationError(
                "instrument bundle must contain an instrument artifact"
            )
        if not any(
            root.artifact_type in _INSTRUMENT_ARTIFACT_TYPES for root in self.roots
        ):
            raise ContractValidationError(
                "instrument bundle must declare an instrument artifact root"
            )

        for entry in self.instrument_artifacts:
            if entry.reference.artifact_type not in _INSTRUMENT_ARTIFACT_TYPES:
                raise ContractValidationError(
                    "instrument_artifacts contains an external artifact type"
                )
        for entry in self.hypothesis_registries:
            if entry.reference.artifact_type is not ArtifactType.HYPOTHESIS_REGISTRY:
                raise ContractValidationError(
                    "hypothesis_registries must contain registry references"
                )

        artifact_entries = (
            *self.instrument_artifacts,
            *self.hypothesis_registries,
            *self.context_banks,
        )
        paths = [entry.path for entry in (*artifact_entries, *self.payloads)]
        if len(paths) != len(set(paths)):
            raise ContractValidationError("bundle entry paths must be globally unique")

        logical_keys = [
            (
                entry.reference.artifact_type,
                entry.reference.artifact_id,
            )
            for entry in artifact_entries
        ]
        if len(logical_keys) != len(set(logical_keys)):
            raise ContractValidationError(
                "artifact type/id identities must be globally unique"
            )
        entry_refs = {entry.reference for entry in artifact_entries}
        for root in self.roots:
            if root not in entry_refs:
                raise ContractValidationError(
                    "every root must exactly match one bundle artifact entry"
                )

        payload_paths = [entry.path for entry in self.payloads]
        if len(payload_paths) != len(set(payload_paths)):
            raise ContractValidationError("payload paths must be unique")
        payload_refs = [entry.reference for entry in self.payloads]
        if len(payload_refs) != len(set(payload_refs)):
            raise ContractValidationError("payload references must be unique")
        payload_hashes = [entry.reference.sha256 for entry in self.payloads]
        if len(payload_hashes) != len(set(payload_hashes)):
            raise ContractValidationError(
                "one payload digest cannot be reclassified by multiple entries"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "bundle_id": self.bundle_id,
            "artifact_reference_policy": self.artifact_reference_policy,
            "payload_reference_policy": self.payload_reference_policy,
            "roots": [value.to_dict() for value in self.roots],
            "instrument_artifacts": [
                value.to_dict() for value in self.instrument_artifacts
            ],
            "hypothesis_registries": [
                value.to_dict() for value in self.hypothesis_registries
            ],
            "context_banks": [value.to_dict() for value in self.context_banks],
            "payloads": [value.to_dict() for value in self.payloads],
            "subject_data_access_authorized": (self.subject_data_access_authorized),
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
        value: object,
    ) -> "InstrumentBundleManifest":
        document = require_mapping(value, label="instrument bundle")
        exact_keys(
            document,
            {
                "schema_version",
                "bundle_id",
                "artifact_reference_policy",
                "payload_reference_policy",
                "roots",
                "instrument_artifacts",
                "hypothesis_registries",
                "context_banks",
                "payloads",
                "subject_data_access_authorized",
            },
            label="instrument bundle",
        )
        if document["schema_version"] != cls.schema_version:
            raise ContractValidationError(
                "instrument bundle schema_version is unsupported"
            )
        if document["artifact_reference_policy"] != cls.artifact_reference_policy:
            raise ContractValidationError(
                "artifact_reference_policy must be closed_world"
            )
        if document["payload_reference_policy"] != cls.payload_reference_policy:
            raise ContractValidationError(
                "payload_reference_policy must be closed_world"
            )
        roots_value = document["roots"]
        instrument_value = document["instrument_artifacts"]
        registry_value = document["hypothesis_registries"]
        context_value = document["context_banks"]
        payload_value = document["payloads"]
        for label, item in (
            ("roots", roots_value),
            ("instrument_artifacts", instrument_value),
            ("hypothesis_registries", registry_value),
            ("context_banks", context_value),
            ("payloads", payload_value),
        ):
            if not isinstance(item, list):
                raise ContractValidationError(f"{label} must be a list")
        return cls(
            bundle_id=require_slug(document["bundle_id"], label="bundle_id"),
            roots=tuple(
                ArtifactRef.from_dict(require_mapping(item, label=f"roots[{index}]"))
                for index, item in enumerate(roots_value)
            ),
            instrument_artifacts=tuple(
                BundleArtifactEntry.from_dict(
                    item,
                    label=f"instrument_artifacts[{index}]",
                )
                for index, item in enumerate(instrument_value)
            ),
            hypothesis_registries=tuple(
                BundleArtifactEntry.from_dict(
                    item,
                    label=f"hypothesis_registries[{index}]",
                )
                for index, item in enumerate(registry_value)
            ),
            context_banks=tuple(
                BundleContextBankEntry.from_dict(
                    item,
                    label=f"context_banks[{index}]",
                )
                for index, item in enumerate(context_value)
            ),
            payloads=tuple(
                BundlePayloadEntry.from_dict(
                    item,
                    label=f"payloads[{index}]",
                )
                for index, item in enumerate(payload_value)
            ),
            subject_data_access_authorized=require_bool(
                document["subject_data_access_authorized"],
                label="subject_data_access_authorized",
            ),
        )
