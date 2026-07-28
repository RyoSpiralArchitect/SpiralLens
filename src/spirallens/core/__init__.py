"""Framework-neutral primitives intended to mature into SpiralLens core APIs.

The symbols in this namespace are stable candidates, not stable 1.0
commitments. Scientific artifacts and experiment orchestration remain
provisional elsewhere in the package.
"""

from __future__ import annotations

from .canonical import (
    CanonicalJsonError,
    JsonScalar,
    JsonValue,
    canonical_json_bytes,
    canonical_json_sha256,
    parse_canonical_json,
    sha256_bytes,
)

__all__ = [
    "CanonicalJsonError",
    "JsonScalar",
    "JsonValue",
    "canonical_json_bytes",
    "canonical_json_sha256",
    "parse_canonical_json",
    "sha256_bytes",
]
