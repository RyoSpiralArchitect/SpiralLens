from __future__ import annotations

import ast
from pathlib import Path

import pytest

from spirallens import execution_freeze as execution_freeze_module
from spirallens.metrics import neighbor_audit as neighbor_audit_module
from spirallens.metrics import neighbor_receipt as neighbor_receipt_module
from spirallens.neighbors import contracts as neighbor_contracts_module


_VALIDATOR = neighbor_contracts_module._require_sha256
_CONSUMERS = (
    execution_freeze_module,
    neighbor_audit_module,
    neighbor_receipt_module,
)


def test_neighbor_digest_consumers_bind_the_contract_validator() -> None:
    assert all(module._require_sha256 is _VALIDATOR for module in _CONSUMERS)


def test_neighbor_contract_validator_has_no_spirallens_import_edge() -> None:
    source_path = Path(neighbor_contracts_module.__file__)
    tree = ast.parse(source_path.read_text())
    imported = {
        name.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for name in node.names
    }
    imported.update(
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    assert not any(
        isinstance(node, ast.ImportFrom) and node.level > 0 for node in ast.walk(tree)
    )
    assert not any(name == "spirallens" or name.startswith("spirallens.") for name in imported)


class _Digest(str):
    pass


@pytest.mark.parametrize("value", ("a" * 64, _Digest("0123456789abcdef" * 4)))
def test_neighbor_digest_validator_returns_the_original_string(value: str) -> None:
    assert _VALIDATOR(value, label="digest") is value


@pytest.mark.parametrize(
    "value",
    (None, b"a" * 64, "a" * 63, "a" * 65, "A" * 64, "g" * 64, "é" * 64),
)
def test_neighbor_digest_validator_preserves_exact_failure(value: object) -> None:
    with pytest.raises(
        ValueError,
        match=r"^field\[0\] must be a lowercase SHA-256 digest$",
    ) as captured:
        _VALIDATOR(value, label="field[0]")
    assert type(captured.value) is ValueError
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None


def test_neighbor_digest_validator_rejects_non_strings_before_protocols() -> None:
    class Adversary:
        def __len__(self) -> int:
            raise AssertionError("non-string length must not be observed")

        def __iter__(self) -> object:
            raise AssertionError("non-string iteration must not be observed")

    with pytest.raises(ValueError, match="lowercase SHA-256 digest"):
        _VALIDATOR(Adversary(), label="digest")
