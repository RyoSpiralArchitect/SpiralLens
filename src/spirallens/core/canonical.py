"""Strict, framework-neutral canonical JSON primitives.

The canonical representation is UTF-8 JSON with object keys sorted, compact
separators, non-ASCII characters encoded directly, and no trailing newline.
Only genuine JSON values are accepted. Non-finite floats and negative zero are
rejected rather than normalized into a different value.
"""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
import math
from typing import TypeAlias


JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


class CanonicalJsonError(ValueError):
    """Raised when a value or byte string is not canonical JSON."""


def _validate_json_value(
    value: object,
    *,
    path: str,
    ancestors: set[int],
) -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CanonicalJsonError(f"{path} must be finite")
        if value == 0.0 and math.copysign(1.0, value) < 0.0:
            raise CanonicalJsonError(f"{path} must not be negative zero")
        return

    if isinstance(value, Mapping):
        identity = id(value)
        if identity in ancestors:
            raise CanonicalJsonError(f"{path} must not contain a cycle")
        ancestors.add(identity)
        try:
            for key, item in value.items():
                if not isinstance(key, str):
                    raise CanonicalJsonError(f"{path} object keys must be strings")
                _validate_json_value(
                    item,
                    path=f"{path}.{key}",
                    ancestors=ancestors,
                )
        finally:
            ancestors.remove(identity)
        return

    if isinstance(value, list):
        identity = id(value)
        if identity in ancestors:
            raise CanonicalJsonError(f"{path} must not contain a cycle")
        ancestors.add(identity)
        try:
            for index, item in enumerate(value):
                _validate_json_value(
                    item,
                    path=f"{path}[{index}]",
                    ancestors=ancestors,
                )
        finally:
            ancestors.remove(identity)
        return

    raise CanonicalJsonError(
        f"{path} contains unsupported JSON value {type(value).__name__}"
    )


def canonical_json_bytes(value: object) -> bytes:
    """Encode one value as SpiralLens canonical JSON bytes."""

    _validate_json_value(value, path="$", ancestors=set())
    try:
        text = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        return text.encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise CanonicalJsonError(
            "value cannot be encoded as canonical UTF-8 JSON"
        ) from error


def sha256_bytes(value: bytes) -> str:
    """Return a lowercase SHA-256 digest for immutable bytes."""

    if not isinstance(value, bytes):
        raise TypeError("value must be bytes")
    return hashlib.sha256(value).hexdigest()


def canonical_json_sha256(value: object) -> str:
    """Return the SHA-256 digest of ``canonical_json_bytes(value)``."""

    return sha256_bytes(canonical_json_bytes(value))


def _reject_duplicate_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise CanonicalJsonError(f"duplicate JSON key {key!r}")
        value[key] = item
    return value


def _reject_nonstandard_constant(value: str) -> None:
    raise CanonicalJsonError(
        f"non-standard JSON numeric constant {value!r} is forbidden"
    )


def parse_canonical_json(
    source: bytes,
    *,
    label: str = "canonical JSON",
) -> JsonValue:
    """Parse bytes only when they already equal their canonical encoding."""

    if not isinstance(source, bytes):
        raise TypeError("source must be bytes")
    if not isinstance(label, str) or not label.strip():
        raise TypeError("label must be a non-empty string")
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError as error:
        raise CanonicalJsonError(f"{label} must be UTF-8") from error
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonstandard_constant,
        )
    except CanonicalJsonError:
        raise
    except json.JSONDecodeError as error:
        raise CanonicalJsonError(f"{label} is invalid JSON") from error

    _validate_json_value(value, path="$", ancestors=set())
    if canonical_json_bytes(value) != source:
        raise CanonicalJsonError(f"{label} is not canonical JSON")
    return value
