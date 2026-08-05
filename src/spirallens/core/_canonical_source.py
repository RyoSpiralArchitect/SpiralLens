"""Internal, authority-free binding of canonical JSON source bytes."""

from __future__ import annotations

from spirallens.core.canonical import (
    CanonicalJsonError,
    JsonValue,
    parse_canonical_json,
    sha256_bytes,
)


class SourceDigestMismatchError(ValueError):
    """Raised before parsing when source bytes differ from a trusted digest."""


def bind_canonical_json_source(
    source: bytes,
    *,
    label: str,
    maximum_bytes: int,
    expected_source_sha256: str | None,
) -> tuple[JsonValue, str]:
    """Return canonical JSON and its pre-parse-verified source digest.

    The caller owns file access, digest syntax, object/schema reconstruction,
    claim meaning, authority, chronology, publication, and repository state.
    """

    if type(source) is not bytes:
        raise TypeError("source must be exact built-in bytes")
    if type(maximum_bytes) is not int or maximum_bytes <= 0:
        raise TypeError("maximum_bytes must be a positive integer")
    if len(source) > maximum_bytes:
        raise CanonicalJsonError(f"{label} exceeds {maximum_bytes} bytes")
    source_sha256 = sha256_bytes(source)
    if (
        expected_source_sha256 is not None
        and source_sha256 != expected_source_sha256
    ):
        raise SourceDigestMismatchError(f"{label} source SHA-256 differs")
    return parse_canonical_json(source, label=label), source_sha256
