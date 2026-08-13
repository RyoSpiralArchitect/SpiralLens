from __future__ import annotations

import ast
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

from spirallens.access import AtlasAccessContractError, AttemptPhase
from spirallens.access import contracts as contracts_module
from spirallens.access import lifecycle as lifecycle_module
from spirallens.access import lineage as lineage_module


def _assert_plain_failure(call: Callable[[], object], pattern: str) -> None:
    with pytest.raises(AtlasAccessContractError, match=pattern) as captured:
        call()
    assert type(captured.value) is AtlasAccessContractError
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None


def test_access_schema_consumers_bind_the_contract_validators() -> None:
    expected = contracts_module._mapping, contracts_module._exact_keys
    assert (lifecycle_module._mapping, lifecycle_module._exact_keys) == expected
    assert lifecycle_module._enum_value is contracts_module._enum_value
    assert lifecycle_module._sha256 is contracts_module._sha256
    assert lineage_module._sha256 is contracts_module._sha256


def test_access_contract_validator_owner_does_not_import_its_consumers() -> None:
    tree = ast.parse(Path(contracts_module.__file__).read_text())
    forbidden = {"spirallens.access.lifecycle", "spirallens.access.lineage"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert forbidden.isdisjoint(name.name for name in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported = {
                f"{node.module}.{name.name}" if node.module else name.name
                for name in node.names
            }
            coordinates = {node.module or "", *imported}
            assert not any(
                coordinate == blocked or coordinate.startswith(f"{blocked}.")
                for coordinate in coordinates
                for blocked in forbidden
            )
            if node.level > 0:
                assert not any(
                    coordinate == blocked or coordinate.startswith(f"{blocked}.")
                    for coordinate in coordinates
                    for blocked in ("lifecycle", "lineage")
                )


def test_lifecycle_exact_key_calls_receive_only_local_builtin_sets() -> None:
    tree = ast.parse(Path(lifecycle_module.__file__).read_text())
    all_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_exact_keys"
    ]
    assert len(all_calls) == 2
    for class_name in ("AttemptAccessFacts", "AttemptTerminalRecord"):
        class_node = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == class_name
        )
        method = next(
            node
            for node in class_node.body
            if isinstance(node, ast.FunctionDef) and node.name == "from_dict"
        )
        calls = [node for node in ast.walk(method) if node in all_calls]
        fields = [
            node
            for node in method.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "fields"
                for target in node.targets
            )
        ]
        assert len(calls) == len(fields) == 1
        assert isinstance(fields[0].value, ast.Set)
        assert ast.unparse(calls[0].args[1]) == "fields"


class _Digest(str):
    pass


@pytest.mark.parametrize("value", ("a" * 64, _Digest("0123456789abcdef" * 4)))
def test_access_digest_validator_returns_the_original_string(value: str) -> None:
    assert contracts_module._sha256(value, label="digest") is value


@pytest.mark.parametrize(
    "value", (None, b"a" * 64, "a" * 63, "a" * 65, "A" * 64, "g" * 64, "é" * 64)
)
def test_access_digest_validator_preserves_plain_failure(value: object) -> None:
    _assert_plain_failure(
        lambda: contracts_module._sha256(value, label="field[0]"),
        r"^field\[0\] must be a lowercase SHA-256 digest$",
    )


def test_access_mapping_and_exact_keys_preserve_the_narrow_boundary() -> None:
    value = {"a": 1, "z": 2}
    assert contracts_module._mapping(value, label="record") is value
    _assert_plain_failure(
        lambda: contracts_module._exact_keys(value, {"a", "b"}, label="record"),
        r"^record fields differ from the contract: missing=\['b'\], unknown=\['z'\]$",
    )

    class OnePassMapping(dict[str, object]):
        def __init__(self) -> None:
            super().__init__(field=1)
            self.iterations = 0

        def __iter__(self):
            self.iterations += 1
            if self.iterations > 1:
                raise AssertionError("mapping must not be iterated twice")
            return super().__iter__()

    observed: Mapping[str, object] = OnePassMapping()
    contracts_module._exact_keys(observed, {"field"}, label="record")
    assert isinstance(observed, OnePassMapping) and observed.iterations == 1
    _assert_plain_failure(
        lambda: contracts_module._mapping({1: "value"}, label="record"),
        r"^record must be a string-keyed mapping$",
    )


def test_access_enum_validator_preserves_success_and_failure_chains() -> None:
    assert (
        contracts_module._enum_value("preflight", AttemptPhase, label="phase")
        is AttemptPhase.PREFLIGHT
    )
    with pytest.raises(
        AtlasAccessContractError, match=r"^phase is not a supported AttemptPhase$"
    ) as captured:
        contracts_module._enum_value("unknown", AttemptPhase, label="phase")
    assert type(captured.value) is AtlasAccessContractError
    assert type(captured.value.__cause__) is ValueError
    assert captured.value.__context__ is captured.value.__cause__
    assert captured.value.__suppress_context__ is True
    _assert_plain_failure(
        lambda: contracts_module._enum_value(None, AttemptPhase, label="phase"),
        r"^phase must be a string$",
    )
