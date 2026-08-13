from __future__ import annotations

import ast
import hashlib
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_SOURCES = {
    "init": (
        _ROOT / "src/spirallens/core/__init__.py",
        656,
        "3a1af1d86ac24e9796d5f0961180352c669e5dd37ed46e8fa2c0cea9dc31df1d",
    ),
    "canonical": (
        _ROOT / "src/spirallens/core/canonical.py",
        4_989,
        "0a39f0b896e0ae1c2af8d1910dd37afae31ad563c20df785973a91ff4cadac5e",
    ),
}
_IMPORTS = {
    "init": """from __future__ import annotations
from .canonical import CanonicalJsonError, JsonScalar, JsonValue, canonical_json_bytes, canonical_json_sha256, parse_canonical_json, sha256_bytes""".splitlines(),
    "canonical": """from __future__ import annotations
from collections.abc import Mapping
import hashlib
import json
import math
from typing import TypeAlias""".splitlines(),
}
_EXPORTS = """
CanonicalJsonError JsonScalar JsonValue canonical_json_bytes
canonical_json_sha256 parse_canonical_json sha256_bytes
""".split()
_OPERATIONS = "canonical_json_bytes canonical_json_sha256 parse_canonical_json sha256_bytes".split()
_CALLS = """
CanonicalJsonError TypeError _validate_json_value ancestors.add ancestors.remove
canonical_json_bytes enumerate hashlib.sha256 hashlib.sha256(value).hexdigest id
isinstance json.dumps json.loads label.strip math.copysign math.isfinite set
sha256_bytes source.decode text.encode type value.items
""".split()
_FORBIDDEN = """
Path PurePath __builtins__ __file__ __import__ aiohttp chdir checkout compile cwd
delattr environ eval exec fork getcwd getenv getattr git git_root globals http httpx
import_module importlib io locals open os pathlib popen project_root repo repo_root
repository repository_context repository_root requests resolve root run setattr
shutil socket source_root spawn ssl subprocess system tempfile urllib urlopen vars
read_bytes read_text write_bytes write_text
""".split()


def test_core_operation_repository_context_source_policy_is_exact() -> None:
    trees: dict[str, ast.Module] = {}
    for role, (path, size, digest) in _SOURCES.items():
        source = path.read_bytes()
        assert (len(source), hashlib.sha256(source).hexdigest()) == (size, digest)
        trees[role] = ast.parse(source, filename=str(path))

    imports = {}
    for role, tree in trees.items():
        imports[role] = [
            ast.unparse(node)
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
    assert imports == _IMPORTS  # ast.walk also catches nested/conditional imports.

    init, canonical = trees["init"], trees["canonical"]
    definitions = {
        node.name: node
        for node in canonical.body
        if isinstance(node, (ast.FunctionDef, ast.ClassDef))
    }
    binding = {
        alias.asname or alias.name: alias.name
        for node in init.body
        if isinstance(node, ast.ImportFrom)
        and node.level == 1
        and node.module == "canonical"
        for alias in node.names
    }
    all_values = [
        node.value
        for node in init.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        )
    ]
    assert len(all_values) == 1 and isinstance(all_values[0], ast.List)
    exports = [element.value for element in all_values[0].elts]
    assert exports == _EXPORTS
    coordinates = tuple(
        (f"spirallens.core:{name}", f"spirallens.core.canonical:{binding[name]}")
        for name in exports
        if isinstance(definitions.get(binding[name]), ast.FunctionDef)
    )
    assert coordinates == tuple(
        (f"spirallens.core:{name}", f"spirallens.core.canonical:{name}")
        for name in _OPERATIONS
    )

    declarations = [
        node
        for tree in trees.values()
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    for node in declarations:
        assert not node.decorator_list
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for default in (*node.args.defaults, *node.args.kw_defaults):
                assert default is None or not any(
                    isinstance(child, ast.Call) for child in ast.walk(default)
                )
    assert not any(
        isinstance(child, ast.Call)
        for tree in trees.values()
        for statement in tree.body
        if not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
        for child in ast.walk(statement)
    )

    functions = {
        name: node
        for name, node in definitions.items()
        if isinstance(node, ast.FunctionDef)
    }
    closure = set(_OPERATIONS)
    while expansion := {
        node.id
        for name in closure
        for node in ast.walk(functions[name])
        if isinstance(node, ast.Name)
        and isinstance(node.ctx, ast.Load)
        and node.id in functions
        and node.id not in closure
    }:
        closure |= expansion
    assert closure == set(_OPERATIONS) | set(
        "_reject_duplicate_keys _reject_nonstandard_constant _validate_json_value".split()
    )
    # Receiver calls are syntax observations, not purity or callback-free claims.
    assert {
        ast.unparse(node.func)
        for name in closure
        for node in ast.walk(functions[name])
        if isinstance(node, ast.Call)
    } == set(_CALLS)

    identifiers: set[str] = set()
    for tree in trees.values():
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                identifiers.add(node.id)
            elif isinstance(node, ast.arg):
                identifiers.add(node.arg)
            elif isinstance(node, ast.Attribute):
                identifiers.add(node.attr)
            elif isinstance(node, ast.alias):
                identifiers.update(value for value in (node.name, node.asname) if value)
    assert identifiers.isdisjoint(_FORBIDDEN)
    assert not any("repository" in name.lower() for name in identifiers)
