"""Strict, read-only loading for canonical instrument artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from .artifacts import (
    InstrumentArtifactValue,
    instrument_artifact_from_dict,
)
from .canonical import CanonicalJsonError, parse_canonical_json
from .common import (
    ContractValidationError,
    require_mapping,
    require_sha256,
)


MAX_INSTRUMENT_ARTIFACT_BYTES = 4 * 1024 * 1024


class InstrumentArtifactSchemaError(ContractValidationError):
    """Raised when canonical bytes do not encode a supported exact schema."""


class InstrumentArtifactIntegrityError(ContractValidationError):
    """Raised when source or reconstructed canonical identity differs."""


@dataclass(frozen=True, slots=True)
class LoadedInstrumentArtifact:
    """A validated artifact and its byte-level/canonical identities."""

    artifact: InstrumentArtifactValue
    source_path: Path
    source_sha256: str
    canonical_sha256: str


def load_instrument_artifact(
    path: str | Path,
    *,
    expected_source_sha256: str | None = None,
    expected_canonical_sha256: str | None = None,
) -> LoadedInstrumentArtifact:
    """Load one canonical JSON manifest without dereferencing its payloads."""

    if expected_source_sha256 is not None:
        require_sha256(
            expected_source_sha256,
            label="expected_source_sha256",
        )
    if expected_canonical_sha256 is not None:
        require_sha256(
            expected_canonical_sha256,
            label="expected_canonical_sha256",
        )
    source_path = Path(path).resolve()
    with source_path.open("rb") as handle:
        source = handle.read(MAX_INSTRUMENT_ARTIFACT_BYTES + 1)
    if len(source) > MAX_INSTRUMENT_ARTIFACT_BYTES:
        raise InstrumentArtifactSchemaError(
            "instrument artifact exceeds "
            f"{MAX_INSTRUMENT_ARTIFACT_BYTES} bytes"
        )
    source_sha256 = hashlib.sha256(source).hexdigest()
    if (
        expected_source_sha256 is not None
        and source_sha256 != expected_source_sha256
    ):
        raise InstrumentArtifactIntegrityError(
            "instrument artifact source SHA-256 differs"
        )
    try:
        parsed = parse_canonical_json(
            source,
            label="instrument artifact",
        )
    except CanonicalJsonError as error:
        raise InstrumentArtifactSchemaError(str(error)) from error
    try:
        document = require_mapping(parsed, label="instrument artifact")
        artifact = instrument_artifact_from_dict(document)
    except (ContractValidationError, KeyError, TypeError) as error:
        raise InstrumentArtifactSchemaError(str(error)) from error
    if artifact.canonical_bytes != source:
        raise InstrumentArtifactIntegrityError(
            "instrument artifact typed reconstruction differs"
        )
    canonical_sha256 = artifact.canonical_sha256
    if (
        expected_canonical_sha256 is not None
        and canonical_sha256 != expected_canonical_sha256
    ):
        raise InstrumentArtifactIntegrityError(
            "instrument artifact canonical SHA-256 differs"
        )
    return LoadedInstrumentArtifact(
        artifact=artifact,
        source_path=source_path,
        source_sha256=source_sha256,
        canonical_sha256=canonical_sha256,
    )
