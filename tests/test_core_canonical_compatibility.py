from __future__ import annotations

import hashlib
import inspect
import json
from types import MappingProxyType

import pytest

import spirallens.core as core
from spirallens.core import canonical
import spirallens.instrument_contracts as instrument_contracts
from spirallens.instrument_contracts import canonical as legacy_canonical


EXPORTS = [
    "CanonicalJsonError",
    "JsonScalar",
    "JsonValue",
    "canonical_json_bytes",
    "canonical_json_sha256",
    "parse_canonical_json",
    "sha256_bytes",
]
# fmt: off
EMPTY = inspect.Parameter.empty
POSITIONAL = inspect.Parameter.POSITIONAL_OR_KEYWORD
KEYWORD_ONLY = inspect.Parameter.KEYWORD_ONLY
CALLABLE_CONTRACTS = {
    "canonical_json_bytes": ((("value", POSITIONAL, EMPTY, "object"),), "bytes", {"value": "object", "return": "bytes"}),
    "canonical_json_sha256": ((("value", POSITIONAL, EMPTY, "object"),), "str", {"value": "object", "return": "str"}),
    "parse_canonical_json": ((("source", POSITIONAL, EMPTY, "bytes"), ("label", KEYWORD_ONLY, "canonical JSON", "str")), "JsonValue", {"source": "bytes", "label": "str", "return": "JsonValue"}),
    "sha256_bytes": ((("value", POSITIONAL, EMPTY, "bytes"),), "str", {"value": "bytes", "return": "str"}),
}
# fmt: on


def test_core_canonical_surface_and_compatibility_aliases_are_exact() -> None:
    assert core.__all__ == EXPORTS
    assert legacy_canonical.__all__ == EXPORTS
    for name in EXPORTS:
        defining_value = getattr(canonical, name)
        assert getattr(core, name) is defining_value
        assert getattr(legacy_canonical, name) is defining_value
    for name in EXPORTS[:1] + EXPORTS[3:6]:
        assert getattr(instrument_contracts, name) is getattr(canonical, name)

    assert canonical.CanonicalJsonError.__bases__ == (ValueError,)
    assert canonical.CanonicalJsonError.__module__ == canonical.__name__
    assert canonical.__annotations__ == {
        "JsonScalar": "TypeAlias",
        "JsonValue": "TypeAlias",
    }
    assert canonical.JsonScalar == str | int | float | bool | None
    json_value_name = "JsonValue"
    assert canonical.JsonValue == (
        canonical.JsonScalar | list[json_value_name] | dict[str, json_value_name]
    )


def test_core_canonical_callable_contracts_are_exact() -> None:
    for name, (
        parameters,
        return_annotation,
        expected_annotations,
    ) in CALLABLE_CONTRACTS.items():
        operation = getattr(canonical, name)
        assert (operation.__module__, operation.__qualname__) == (
            canonical.__name__,
            name,
        )
        signature = inspect.signature(operation)
        assert (
            tuple(
                (item.name, item.kind, item.default, item.annotation)
                for item in signature.parameters.values()
            )
            == parameters
        )
        assert signature.return_annotation == return_annotation
        assert operation.__annotations__ == expected_annotations


def test_core_canonical_success_values_are_exact() -> None:
    value = {"z": ["渦", 3, 1.25], "a": {"truth": True, "nothing": None}}
    source = (
        b'{"a":{"nothing":null,"truth":true},"z":["' + "渦".encode() + b'",3,1.25]}'
    )
    assert core.canonical_json_bytes(value) == source
    assert core.parse_canonical_json(source) == value
    assert core.sha256_bytes(source) == hashlib.sha256(source).hexdigest()
    assert core.canonical_json_sha256(value) == hashlib.sha256(source).hexdigest()
    for encoded, parsed in (
        (b"null", None),
        (b"true", True),
        (b"0", 0),
        (b"0.0", 0.0),
        (b'"text"', "text"),
        (b"[]", []),
        (b"{}", {}),
    ):
        observed = core.parse_canonical_json(encoded)
        assert type(observed) is type(parsed)
        assert observed == parsed


def _cyclic_list() -> list[object]:
    value: list[object] = []
    value.append(value)
    return value


def test_core_canonical_direct_failures_are_exact() -> None:
    # fmt: off
    cases = (
        (core.sha256_bytes, (bytearray(b"x"),), TypeError, "value must be bytes"),
        (core.parse_canonical_json, ("{}",), TypeError, "source must be bytes"),
        (core.canonical_json_bytes, ((1, 2),), canonical.CanonicalJsonError, "$ contains unsupported JSON value tuple"),
        (core.canonical_json_bytes, ({1: "x"},), canonical.CanonicalJsonError, "$ object keys must be strings"),
        (core.canonical_json_bytes, (_cyclic_list(),), canonical.CanonicalJsonError, "$[0] must not contain a cycle"),
        (core.canonical_json_bytes, (float("inf"),), canonical.CanonicalJsonError, "$ must be finite"),
        (core.canonical_json_bytes, (-0.0,), canonical.CanonicalJsonError, "$ must not be negative zero"),
        (core.parse_canonical_json, (b'{"x":1,"x":2}',), canonical.CanonicalJsonError, "duplicate JSON key 'x'"),
        (core.parse_canonical_json, (b"NaN",), canonical.CanonicalJsonError, "non-standard JSON numeric constant 'NaN' is forbidden"),
        (core.parse_canonical_json, (b'{"b":1,"a":2}',), canonical.CanonicalJsonError, "canonical JSON is not canonical JSON"),
    )
    # fmt: on
    for operation, args, exception_type, message in cases:
        with pytest.raises(exception_type) as caught:
            operation(*args)
        assert (
            str(caught.value),
            caught.value.__cause__,
            caught.value.__context__,
        ) == (message, None, None)
        assert caught.value.__suppress_context__ is False

    with pytest.raises(TypeError) as caught:
        core.parse_canonical_json(b"{}", label=" ")
    assert str(caught.value) == "label must be a non-empty string"
    assert caught.value.__cause__ is caught.value.__context__ is None
    assert caught.value.__suppress_context__ is False


def test_core_canonical_wrapped_failures_preserve_direct_causes() -> None:
    # fmt: off
    cases = (
        (core.parse_canonical_json, (b"\xff",), {"label": "fixture"}, "fixture must be UTF-8", UnicodeDecodeError),
        (core.parse_canonical_json, (b"{",), {"label": "fixture"}, "fixture is invalid JSON", json.JSONDecodeError),
        (core.canonical_json_bytes, ("\ud800",), {}, "value cannot be encoded as canonical UTF-8 JSON", UnicodeEncodeError),
        (core.canonical_json_bytes, (MappingProxyType({"a": 1}),), {}, "value cannot be encoded as canonical UTF-8 JSON", TypeError),
    )
    # fmt: on
    for operation, args, kwargs, message, cause_type in cases:
        with pytest.raises(canonical.CanonicalJsonError) as caught:
            operation(*args, **kwargs)
        assert str(caught.value) == message
        assert type(caught.value.__cause__) is cause_type
        assert caught.value.__context__ is caught.value.__cause__
        assert caught.value.__suppress_context__ is True


def test_core_canonical_validation_order_is_exact() -> None:
    with pytest.raises(TypeError, match="^source must be bytes$"):
        core.parse_canonical_json("not bytes", label=1)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="^label must be a non-empty string$"):
        core.parse_canonical_json(b"\xff", label="")
    with pytest.raises(canonical.CanonicalJsonError, match=r"^\$\.z contains"):
        core.canonical_json_bytes({"z": (1,), "a": float("inf")})
    with pytest.raises(canonical.CanonicalJsonError, match=r"^\$\.b must be finite$"):
        core.parse_canonical_json(b'{"b":1e999,"a":0}')
