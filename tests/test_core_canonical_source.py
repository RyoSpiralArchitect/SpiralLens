from __future__ import annotations

import hashlib

import pytest

from spirallens.core import _canonical_source
from spirallens.core._canonical_source import (
    SourceDigestMismatchError,
    bind_canonical_json_source,
)
from spirallens.core.canonical import CanonicalJsonError, canonical_json_bytes


def _sha256(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def test_binding_returns_canonical_value_and_exact_source_digest() -> None:
    source = canonical_json_bytes({"kind": "fixture", "value": 1})

    document, source_sha256 = bind_canonical_json_source(
        source,
        label="fixture",
        maximum_bytes=len(source),
        expected_source_sha256=_sha256(source),
    )

    assert document == {"kind": "fixture", "value": 1}
    assert source_sha256 == _sha256(source)


def test_source_digest_mismatch_precedes_parser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_parser(*args: object, **kwargs: object) -> object:
        raise AssertionError("parser must not run before source identity matches")

    monkeypatch.setattr(_canonical_source, "parse_canonical_json", forbidden_parser)

    with pytest.raises(SourceDigestMismatchError, match="source SHA-256 differs"):
        bind_canonical_json_source(
            b"not-json",
            label="fixture",
            maximum_bytes=100,
            expected_source_sha256="0" * 64,
        )


@pytest.mark.parametrize(
    ("source", "maximum_bytes", "message"),
    (
        (b"{}", 1, "exceeds"),
        (b"", 10, "invalid JSON"),
        (b'{"x":1,"x":2}', 100, "duplicate JSON key"),
        (b'{"x": 1}', 100, "not canonical JSON"),
    ),
)
def test_binding_rejects_unqualified_sources(
    source: bytes,
    maximum_bytes: int,
    message: str,
) -> None:
    with pytest.raises(CanonicalJsonError, match=message):
        bind_canonical_json_source(
            source,
            label="fixture",
            maximum_bytes=maximum_bytes,
            expected_source_sha256=None,
        )


def test_binding_leaves_object_schema_to_consumer() -> None:
    document, _ = bind_canonical_json_source(
        b"[]",
        label="fixture",
        maximum_bytes=10,
        expected_source_sha256=None,
    )

    assert document == []
