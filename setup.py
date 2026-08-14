from __future__ import annotations

import ast
import json
import runpy
import stat
import tomllib
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.install_lib import install_lib
from setuptools.errors import SetupError


_PROJECT_ROOT = Path(__file__).absolute().parent
_SOURCE_ROOT = _PROJECT_ROOT / "src"
_PACKAGE_NAME = "spirallens"
_CLASSIFICATION_PATH = (
    _PROJECT_ROOT / "distribution/spirallens_python_members_v0_1.json"
)
_EXPORT_CLASSIFICATION_PATH = (
    _PROJECT_ROOT / "distribution/spirallens_ordered_exports_v0_1.json"
)
_IMPORT_CLASSIFICATION_PATH = (
    _PROJECT_ROOT / "distribution/spirallens_installed_imports_v0_1.json"
)
_POLICY_PATH = _PROJECT_ROOT / "distribution/_installed_import_policy.py"
_CLASSIFICATION_SCHEMA_VERSION = "spirallens.python-distribution-members.v0.1"
_CLASSIFICATION_SCOPE = (
    "physical Python member placement across repository source, sdist, and wheels"
)
_CLASSIFICATION_CLAIM_BOUNDARY = (
    "classification grants no public API, stability, compatibility, authority, "
    "scientific claim, or library maturity"
)
_EXPORT_CLASSIFICATION_SCHEMA_VERSION = "spirallens.ordered-package-exports.v0.1"
_EXPORT_CLASSIFICATION_SCOPE = (
    "literal ordered __all__ values for every classified package initializer"
)
_EXPORT_CLASSIFICATION_CLAIM_BOUNDARY = _CLASSIFICATION_CLAIM_BOUNDARY
try:
    _POLICY_STAT = _POLICY_PATH.lstat()
    if not stat.S_ISREG(_POLICY_STAT.st_mode) or _POLICY_STAT.st_size > 1024 * 1024:
        raise OSError
    _POLICY = runpy.run_path(str(_POLICY_PATH))
except (OSError, SyntaxError) as error:
    raise SetupError("cannot load installed import policy") from error

_MODELS_EXTRA_MISSING_TORCH_MODULES = _POLICY["MISSING_TORCH"]
_CLASSIFICATION_ROLES = (
    "package_initializer",
    "console_entrypoint_runtime",
    "shipped_runtime",
    "repository_only",
)
_SHIPPED_ROLES = _CLASSIFICATION_ROLES[:3]
_CONSOLE_ENTRYPOINT_PATHS = (
    "spirallens/__main__.py",
    "spirallens/cli.py",
)


def _is_ordinary_file(path: Path) -> bool:
    try:
        return stat.S_ISREG(path.lstat().st_mode)
    except OSError:
        return False


def _is_ordinary_directory(path: Path) -> bool:
    try:
        return stat.S_ISDIR(path.lstat().st_mode)
    except OSError:
        return False


def _is_absent(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return False


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SetupError(f"distribution classification has duplicate key {key!r}")
        result[key] = value
    return result


def _reject_export_duplicate_json_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SetupError(f"ordered export classification has duplicate key {key!r}")
        result[key] = value
    return result


def _reject_import_duplicate_json_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SetupError(
                f"installed import classification has duplicate key {key!r}"
            )
        result[key] = value
    return result


def _is_portable_python_member(value: str) -> bool:
    path = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or path.is_absolute()
        or path.as_posix() != value
        or len(path.parts) < 2
        or path.parts[0] != _PACKAGE_NAME
        or path.suffix != ".py"
        or any(part in {"", ".", ".."} for part in path.parts)
        or "__pycache__" in path.parts
    ):
        return False
    identifiers = (*path.parts[:-1], path.stem)
    return all(
        identifier.isascii() and identifier.isidentifier() for identifier in identifiers
    )


def _load_distribution_classification() -> dict[str, tuple[str, ...]]:
    if not _is_ordinary_directory(_CLASSIFICATION_PATH.parent):
        raise SetupError(
            "distribution classification parent must be an ordinary directory"
        )
    if not _is_ordinary_file(_CLASSIFICATION_PATH):
        raise SetupError("distribution classification must be an ordinary file")
    try:
        source = _CLASSIFICATION_PATH.read_bytes()
    except OSError as error:
        raise SetupError("cannot read distribution classification") from error
    if len(source) > 1024 * 1024:
        raise SetupError("distribution classification exceeds its size bound")
    try:
        document = json.loads(
            source.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except SetupError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SetupError(
            "distribution classification is not strict UTF-8 JSON"
        ) from error
    expected_top_level = {
        "schema_version",
        "classification_scope",
        "claim_boundary",
        "roles",
    }
    if not isinstance(document, dict) or set(document) != expected_top_level:
        raise SetupError(
            "distribution classification must have the exact top-level fields"
        )
    if document["schema_version"] != _CLASSIFICATION_SCHEMA_VERSION:
        raise SetupError("distribution classification has the wrong schema version")
    if document["classification_scope"] != _CLASSIFICATION_SCOPE:
        raise SetupError("distribution classification has the wrong physical scope")
    if document["claim_boundary"] != _CLASSIFICATION_CLAIM_BOUNDARY:
        raise SetupError("distribution classification has the wrong claim boundary")
    roles = document["roles"]
    if not isinstance(roles, dict) or set(roles) != set(_CLASSIFICATION_ROLES):
        raise SetupError("distribution classification must have the exact roles")

    parsed: dict[str, tuple[str, ...]] = {}
    owner: dict[str, str] = {}
    for role in _CLASSIFICATION_ROLES:
        members = roles[role]
        if (
            not isinstance(members, list)
            or not members
            or any(not isinstance(member, str) for member in members)
            or members != sorted(members)
            or len(set(members)) != len(members)
            or any(not _is_portable_python_member(member) for member in members)
        ):
            raise SetupError(
                f"distribution classification role {role!r} must be a non-empty, "
                "sorted, unique list of portable spirallens Python members"
            )
        for member in members:
            previous = owner.get(member)
            if previous is not None:
                raise SetupError(
                    f"distribution classification member {member!r} appears in "
                    f"both {previous!r} and {role!r}"
                )
            owner[member] = role
        parsed[role] = tuple(members)

    initializers = parsed["package_initializer"]
    if any(PurePosixPath(member).name != "__init__.py" for member in initializers):
        raise SetupError("package_initializer contains a non-initializer member")
    if tuple(parsed["console_entrypoint_runtime"]) != _CONSOLE_ENTRYPOINT_PATHS:
        raise SetupError("console_entrypoint_runtime differs from the reviewed paths")
    non_initializers = tuple(
        member for role in _CLASSIFICATION_ROLES[1:] for member in parsed[role]
    )
    if any(PurePosixPath(member).name == "__init__.py" for member in non_initializers):
        raise SetupError("an initializer is classified outside package_initializer")
    shipped_members = tuple(
        member for role in _SHIPPED_ROLES for member in parsed[role]
    )
    required_initializers = {
        (parent / "__init__.py").as_posix()
        for member in shipped_members
        for parent in PurePosixPath(member).parents
        if parent.as_posix() != "."
    }
    if set(initializers) != required_initializers:
        raise SetupError(
            "package_initializer must exactly close every shipped package ancestor"
        )
    return parsed


_PYTHON_MEMBER_CLASSIFICATION = _load_distribution_classification()


def _load_ordered_export_classification() -> dict[str, tuple[str, ...]]:
    if not _is_ordinary_directory(_EXPORT_CLASSIFICATION_PATH.parent):
        raise SetupError(
            "ordered export classification parent must be an ordinary directory"
        )
    if not _is_ordinary_file(_EXPORT_CLASSIFICATION_PATH):
        raise SetupError("ordered export classification must be an ordinary file")
    try:
        source = _EXPORT_CLASSIFICATION_PATH.read_bytes()
    except OSError as error:
        raise SetupError("cannot read ordered export classification") from error
    if len(source) > 1024 * 1024:
        raise SetupError("ordered export classification exceeds its size bound")
    try:
        document = json.loads(
            source.decode("utf-8"),
            object_pairs_hook=_reject_export_duplicate_json_keys,
        )
    except SetupError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SetupError(
            "ordered export classification is not strict UTF-8 JSON"
        ) from error
    expected_top_level = {
        "schema_version",
        "classification_scope",
        "claim_boundary",
        "packages",
    }
    if not isinstance(document, dict) or set(document) != expected_top_level:
        raise SetupError(
            "ordered export classification must have the exact top-level fields"
        )
    if document["schema_version"] != _EXPORT_CLASSIFICATION_SCHEMA_VERSION:
        raise SetupError("ordered export classification has the wrong schema version")
    if document["classification_scope"] != _EXPORT_CLASSIFICATION_SCOPE:
        raise SetupError("ordered export classification has the wrong literal scope")
    if document["claim_boundary"] != _EXPORT_CLASSIFICATION_CLAIM_BOUNDARY:
        raise SetupError("ordered export classification has the wrong claim boundary")

    packages = document["packages"]
    if not isinstance(packages, list) or not packages:
        raise SetupError(
            "ordered export classification packages must be a non-empty list"
        )
    parsed: dict[str, tuple[str, ...]] = {}
    initializers: set[str] = set()
    observed_order: list[str] = []
    for package in packages:
        if not isinstance(package, dict) or set(package) != {
            "module",
            "initializer",
            "exports",
        }:
            raise SetupError(
                "ordered export package must have the exact package fields"
            )
        module = package["module"]
        initializer = package["initializer"]
        exports = package["exports"]
        if (
            not isinstance(module, str)
            or not module
            or any(
                not part.isascii() or not part.isidentifier()
                for part in module.split(".")
            )
            or module.split(".")[0] != _PACKAGE_NAME
        ):
            raise SetupError(
                "ordered export package module must be a dotted spirallens identifier"
            )
        expected_initializer = f"{module.replace('.', '/')}/__init__.py"
        if (
            not isinstance(initializer, str)
            or initializer != expected_initializer
            or not _is_portable_python_member(initializer)
        ):
            raise SetupError(
                f"ordered export initializer does not match module {module!r}"
            )
        if (
            not isinstance(exports, list)
            or not exports
            or any(
                not isinstance(name, str)
                or not name
                or not name.isascii()
                or not name.isidentifier()
                for name in exports
            )
            or len(set(exports)) != len(exports)
        ):
            raise SetupError(
                f"ordered exports for {module!r} must be a non-empty, ordered, "
                "unique list of ASCII identifiers"
            )
        if module in parsed or initializer in initializers:
            raise SetupError(
                f"ordered export classification repeats package {module!r}"
            )
        parsed[module] = tuple(exports)
        initializers.add(initializer)
        observed_order.append(module)

    if observed_order != sorted(observed_order):
        raise SetupError("ordered export packages must be sorted by module")
    expected_initializers = set(_PYTHON_MEMBER_CLASSIFICATION["package_initializer"])
    if initializers != expected_initializers:
        raise SetupError(
            "ordered export packages must exactly close the classified package "
            "initializer set"
        )
    return parsed


_ORDERED_EXPORT_CLASSIFICATION = _load_ordered_export_classification()
_SHIPPED_PYTHON_PATHS = frozenset(
    member for role in _SHIPPED_ROLES for member in _PYTHON_MEMBER_CLASSIFICATION[role]
)
_REPOSITORY_ONLY_PYTHON_PATHS = frozenset(
    _PYTHON_MEMBER_CLASSIFICATION["repository_only"]
)
_ALL_PYTHON_PATHS = _SHIPPED_PYTHON_PATHS | _REPOSITORY_ONLY_PYTHON_PATHS
_REPOSITORY_ONLY_MODULES = frozenset(
    member.removesuffix(".py").replace("/", ".")
    for member in _REPOSITORY_ONLY_PYTHON_PATHS
)
_EXPECTED_PACKAGE_DIRECTORIES = frozenset(
    parent.as_posix()
    for member in _SHIPPED_PYTHON_PATHS
    for parent in PurePosixPath(member).parents
    if parent.as_posix() != "."
)


def _module_for_python_member(member: str) -> str:
    path = PurePosixPath(member)
    parts = path.with_suffix("").parts
    if path.name == "__init__.py":
        parts = parts[:-1]
    return ".".join(parts)


def _is_portable_spirallens_module(value: str) -> bool:
    parts = value.split(".")
    return (
        value != ""
        and parts[0] == _PACKAGE_NAME
        and all(
            part != "__init__" and part.isascii() and part.isidentifier()
            for part in parts
        )
    )


def _load_installed_import_classification() -> dict[str, tuple[str, ...]]:
    if not _is_ordinary_directory(_IMPORT_CLASSIFICATION_PATH.parent):
        raise SetupError(
            "installed import classification parent must be an ordinary directory"
        )
    if not _is_ordinary_file(_IMPORT_CLASSIFICATION_PATH):
        raise SetupError("installed import classification must be an ordinary file")
    try:
        source = _IMPORT_CLASSIFICATION_PATH.read_bytes()
    except OSError as error:
        raise SetupError("cannot read installed import classification") from error
    if len(source) > 1024 * 1024:
        raise SetupError("installed import classification exceeds its size bound")
    try:
        document = json.loads(
            source.decode("utf-8"),
            object_pairs_hook=_reject_import_duplicate_json_keys,
        )
    except SetupError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SetupError(
            "installed import classification is not strict UTF-8 JSON"
        ) from error

    expected_top_level = {
        "schema_version",
        "classification_scope",
        "claim_boundary",
        "base_dependencies",
        "blocked_optional_prefixes",
        "outcomes",
    }
    if not isinstance(document, dict) or set(document) != expected_top_level:
        raise SetupError(
            "installed import classification must have the exact top-level fields"
        )
    if document["schema_version"] != _POLICY["SCHEMA"]:
        raise SetupError("installed import classification has the wrong schema version")
    if document["classification_scope"] != _POLICY["SCOPE"]:
        raise SetupError("installed import classification has the wrong scope")
    if document["claim_boundary"] != _POLICY["CLAIM"]:
        raise SetupError("installed import classification has the wrong claim boundary")
    if document["base_dependencies"] != _POLICY["dependency_records"]():
        raise SetupError(
            "installed import classification has the wrong base dependencies"
        )
    pyproject_path = _PROJECT_ROOT / "pyproject.toml"
    if not _is_ordinary_file(pyproject_path):
        raise SetupError("pyproject.toml must be an ordinary file")
    try:
        pyproject_source = pyproject_path.read_bytes()
    except OSError as error:
        raise SetupError("cannot read pyproject.toml") from error
    if len(pyproject_source) > 1024 * 1024:
        raise SetupError("pyproject.toml exceeds its size bound")
    try:
        pyproject = tomllib.loads(pyproject_source.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise SetupError("pyproject.toml is not strict UTF-8 TOML") from error
    project = pyproject.get("project")
    declared_dependencies = (
        project.get("dependencies") if isinstance(project, dict) else None
    )
    if (
        not isinstance(declared_dependencies, list)
        or any(
            not isinstance(requirement, str) or not requirement
            for requirement in declared_dependencies
        )
        or len(declared_dependencies) != len(set(declared_dependencies))
        or tuple(sorted(declared_dependencies, key=str.casefold))
        != _POLICY["PROJECT_DEPENDENCIES"]
    ):
        raise SetupError(
            "pyproject.toml project dependencies differ from the exact installed "
            "import base requirements"
        )
    if document["blocked_optional_prefixes"] != list(_POLICY["BLOCKED"]):
        raise SetupError(
            "installed import classification has the wrong blocked optional prefixes"
        )

    raw_outcomes = document["outcomes"]
    if not isinstance(raw_outcomes, dict) or set(raw_outcomes) != set(
        _POLICY["OUTCOMES"]
    ):
        raise SetupError("installed import classification must have the exact outcomes")
    parsed: dict[str, tuple[str, ...]] = {}
    owner: dict[str, str] = {}
    for outcome in _POLICY["OUTCOMES"]:
        raw_modules = raw_outcomes[outcome]
        if (
            not isinstance(raw_modules, list)
            or not raw_modules
            or any(not isinstance(module, str) for module in raw_modules)
            or raw_modules != sorted(raw_modules)
            or len(set(raw_modules)) != len(raw_modules)
            or any(not _is_portable_spirallens_module(module) for module in raw_modules)
        ):
            raise SetupError(
                f"installed import outcome {outcome!r} must be a non-empty, sorted, "
                "unique list of dotted spirallens modules"
            )
        for module in raw_modules:
            previous = owner.get(module)
            if previous is not None:
                raise SetupError(
                    f"installed import module {module!r} appears in both "
                    f"{previous!r} and {outcome!r}"
                )
            owner[module] = outcome
        parsed[outcome] = tuple(raw_modules)

    expected_modules = {
        _module_for_python_member(member) for member in _SHIPPED_PYTHON_PATHS
    }
    if len(expected_modules) != len(_SHIPPED_PYTHON_PATHS):
        raise SetupError(
            "classified shipped Python paths do not map one-to-one to modules"
        )
    observed_modules = set(owner)
    if observed_modules != expected_modules:
        raise SetupError(
            "installed import outcomes must exactly partition every shipped module"
        )
    if parsed["models_extra_missing_torch"] != _POLICY["MISSING_TORCH"]:
        raise SetupError(
            "models_extra_missing_torch differs from the reviewed exact modules"
        )
    expected_success = tuple(sorted(expected_modules - set(_POLICY["MISSING_TORCH"])))
    if parsed["base_import_success"] != expected_success:
        raise SetupError(
            "base_import_success differs from the reviewed exact module complement"
        )
    if len(parsed["base_import_success"]) != 129:
        raise SetupError(
            "base_import_success differs from the exact 129-module inventory"
        )

    initializer_modules = {
        _module_for_python_member(member)
        for member in _PYTHON_MEMBER_CLASSIFICATION["package_initializer"]
    }
    successful_initializers = initializer_modules & set(parsed["base_import_success"])
    missing_torch_initializers = initializer_modules & set(
        parsed["models_extra_missing_torch"]
    )
    if (
        len(initializer_modules) != 24
        or len(successful_initializers) != 23
        or missing_torch_initializers != {"spirallens.adapters"}
    ):
        raise SetupError(
            "installed import outcomes differ from the exact 23-success/one-"
            "missing-torch package-initializer projection"
        )
    return parsed


_INSTALLED_IMPORT_CLASSIFICATION = _load_installed_import_classification()


def _require_ordinary_source_ancestors(expected_members: Sequence[str]) -> None:
    expected_directories = {
        "src",
        *(
            (PurePosixPath("src") / parent).as_posix()
            for member in expected_members
            for parent in PurePosixPath(member).parents
            if parent.as_posix() != "."
        ),
    }
    nonordinary = sorted(
        relative
        for relative in expected_directories
        if not _is_ordinary_directory(_PROJECT_ROOT / relative)
    )
    if nonordinary:
        raise SetupError(
            "classified Python source has missing, non-directory, or symlinked "
            f"ancestors: {nonordinary!r}"
        )


def _observed_source_python_paths() -> tuple[frozenset[str], tuple[str, ...]]:
    observed: set[str] = set()
    nonordinary_directories: list[str] = []

    def visit(directory: Path) -> None:
        try:
            entries = tuple(directory.iterdir())
        except OSError as error:
            raise SetupError(
                f"cannot enumerate classified Python source directory: {directory}"
            ) from error
        for entry in entries:
            try:
                mode = entry.lstat().st_mode
            except OSError as error:
                raise SetupError(
                    f"cannot inspect classified Python source entry: {entry}"
                ) from error
            if stat.S_ISDIR(mode):
                visit(entry)
                continue
            if entry.name.endswith(".py"):
                relative = entry.relative_to(_SOURCE_ROOT).as_posix()
                observed.add(relative)
                if not stat.S_ISREG(mode):
                    nonordinary_directories.append(relative)
            elif stat.S_ISLNK(mode):
                nonordinary_directories.append(
                    entry.relative_to(_SOURCE_ROOT).as_posix()
                )

    if not _is_ordinary_directory(_SOURCE_ROOT):
        return frozenset(), ("src/",)
    visit(_SOURCE_ROOT)
    return frozenset(observed), tuple(sorted(nonordinary_directories))


def _require_classified_source_state() -> None:
    observed, nonordinary = _observed_source_python_paths()
    sdist_marked = _is_ordinary_file(_PROJECT_ROOT / "PKG-INFO") and _is_absent(
        _PROJECT_ROOT / ".git"
    )
    full_source = observed == _ALL_PYTHON_PATHS
    sdist_source = observed == _SHIPPED_PYTHON_PATHS and sdist_marked
    expected = (
        _SHIPPED_PYTHON_PATHS
        if sdist_marked and not observed & _REPOSITORY_ONLY_PYTHON_PATHS
        else _ALL_PYTHON_PATHS
    )
    _require_ordinary_source_ancestors(tuple(expected))
    nonregular = sorted(
        member
        for member in observed & expected
        if not _is_ordinary_file(_SOURCE_ROOT / member)
    )
    if (full_source or sdist_source) and not nonordinary and not nonregular:
        return
    missing = sorted(expected - observed)
    unexpected = sorted(observed - expected)
    raise SetupError(
        "Python source must match the exact classified full repository set or "
        "the exact PKG-INFO-marked no-Git sdist set; "
        f"missing={missing!r}; unexpected={unexpected!r}; "
        f"nonregular={nonregular!r}; nonordinary_entries={list(nonordinary)!r}; "
        f"pkg_info_regular={_is_ordinary_file(_PROJECT_ROOT / 'PKG-INFO')!r}; "
        f"git_marker_absent={_is_absent(_PROJECT_ROOT / '.git')!r}"
    )


def _load_literal_ordered_exports(path: Path, *, label: str) -> tuple[str, ...]:
    if not _is_ordinary_file(path):
        raise SetupError(f"{label} initializer must be an ordinary file")
    try:
        source = path.read_bytes()
    except OSError as error:
        raise SetupError(f"cannot read {label} initializer") from error
    if len(source) > 1024 * 1024:
        raise SetupError(f"{label} initializer exceeds its size bound")
    try:
        text = source.decode("utf-8")
        tree = ast.parse(text, filename=str(path))
    except (UnicodeDecodeError, SyntaxError) as error:
        raise SetupError(
            f"cannot parse {label} initializer as strict UTF-8 Python"
        ) from error

    assignments: list[ast.Assign | ast.AnnAssign] = []
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "__all__"
        ) or (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "__all__"
        ):
            assignments.append(node)
    if len(assignments) != 1:
        raise SetupError(
            f"{label} initializer must have one literal __all__ assignment"
        )
    declaration = assignments[0]
    declaration_target = (
        declaration.targets[0]
        if isinstance(declaration, ast.Assign)
        else declaration.target
    )
    stores_or_deletes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
        and node.id == "__all__"
        and isinstance(node.ctx, (ast.Store, ast.Del))
    ]
    if stores_or_deletes != [declaration_target]:
        raise SetupError(
            f"{label} initializer must not contain another direct __all__ "
            "name store or delete"
        )

    def rooted_in_all(node: ast.expr) -> bool:
        while isinstance(node, (ast.Attribute, ast.Subscript)):
            node = node.value
        return isinstance(node, ast.Name) and node.id == "__all__"

    if any(
        (
            isinstance(node, (ast.Attribute, ast.Subscript))
            and isinstance(node.ctx, (ast.Store, ast.Del))
            and rooted_in_all(node)
        )
        or (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and rooted_in_all(node.func.value)
        )
        for node in ast.walk(tree)
    ):
        raise SetupError(
            f"{label} initializer must not contain a direct __all__ "
            "attribute/subscript write or method call"
        )
    try:
        value = ast.literal_eval(assignments[0].value)
    except (TypeError, ValueError) as error:
        raise SetupError(f"{label} initializer __all__ must be literal") from error
    if (
        not isinstance(value, (list, tuple))
        or not value
        or any(
            not isinstance(name, str)
            or not name
            or not name.isascii()
            or not name.isidentifier()
            for name in value
        )
        or len(set(value)) != len(value)
    ):
        raise SetupError(
            f"{label} initializer __all__ must be a non-empty, ordered, unique "
            "literal of ASCII identifiers"
        )
    return tuple(value)


def _require_source_ordered_export_state() -> None:
    expected_initializers = {
        f"{module.replace('.', '/')}/__init__.py"
        for module in _ORDERED_EXPORT_CLASSIFICATION
    }
    observed_python, _ = _observed_source_python_paths()
    observed_initializers = {
        member
        for member in observed_python
        if PurePosixPath(member).name == "__init__.py"
    }
    if observed_initializers != expected_initializers:
        raise SetupError(
            "source package initializers differ from the exact ordered export "
            "classification"
        )
    for module, expected_exports in _ORDERED_EXPORT_CLASSIFICATION.items():
        initializer = f"{module.replace('.', '/')}/__init__.py"
        observed_exports = _load_literal_ordered_exports(
            _SOURCE_ROOT / initializer,
            label=f"source package {module}",
        )
        if observed_exports != expected_exports:
            raise SetupError(
                f"source package {module!r} ordered __all__ differs from the "
                "classification"
            )


def _scan_built_package_tree(root: Path) -> tuple[frozenset[str], frozenset[str]]:
    if _is_absent(root):
        return frozenset(), frozenset()
    if not _is_ordinary_directory(root):
        raise SetupError(
            f"classified build package tree root must be an ordinary directory: {root}"
        )
    files: set[str] = set()
    directories: set[str] = set()

    def visit(directory: Path) -> None:
        try:
            entries = tuple(directory.iterdir())
        except OSError as error:
            raise SetupError(
                f"cannot enumerate classified build package tree: {directory}"
            ) from error
        for entry in entries:
            relative = entry.relative_to(root).as_posix()
            try:
                mode = entry.lstat().st_mode
            except OSError as error:
                raise SetupError(
                    f"cannot inspect classified build package entry: {entry}"
                ) from error
            if stat.S_ISDIR(mode):
                directories.add(relative)
                visit(entry)
            elif stat.S_ISREG(mode):
                files.add(relative)
            else:
                raise SetupError(
                    "classified build package tree contains a symlink or "
                    f"non-regular entry: {relative!r}"
                )

    visit(root)
    return frozenset(files), frozenset(directories)


def _require_built_package_state(
    root: Path,
    *,
    allow_absent_or_empty: bool,
    label: str,
) -> None:
    observed_files, observed_directories = _scan_built_package_tree(root)
    if (
        allow_absent_or_empty
        and not observed_files
        and observed_directories
        in {
            frozenset(),
            frozenset({_PACKAGE_NAME}),
        }
    ):
        return
    missing = sorted(_SHIPPED_PYTHON_PATHS - observed_files)
    unexpected = sorted(observed_files - _SHIPPED_PYTHON_PATHS)
    unexpected_directories = sorted(
        observed_directories - _EXPECTED_PACKAGE_DIRECTORIES
    )
    if not missing and not unexpected and not unexpected_directories:
        return
    raise SetupError(
        f"{label} must contain the exact classified shipped Python tree; "
        f"missing={missing!r}; unexpected={unexpected!r}; "
        f"unexpected_directories={unexpected_directories!r}"
    )


def _require_built_ordered_export_state(
    root: Path,
    *,
    allow_absent_or_empty: bool,
    label: str,
) -> None:
    observed_files, observed_directories = _scan_built_package_tree(root)
    if (
        allow_absent_or_empty
        and not observed_files
        and observed_directories
        in {
            frozenset(),
            frozenset({_PACKAGE_NAME}),
        }
    ):
        return
    expected_initializers = {
        f"{module.replace('.', '/')}/__init__.py"
        for module in _ORDERED_EXPORT_CLASSIFICATION
    }
    observed_initializers = {
        member
        for member in observed_files
        if PurePosixPath(member).name == "__init__.py"
    }
    if observed_initializers != expected_initializers:
        raise SetupError(
            f"{label} initializers differ from the exact ordered export classification"
        )
    for module, expected_exports in _ORDERED_EXPORT_CLASSIFICATION.items():
        initializer = f"{module.replace('.', '/')}/__init__.py"
        observed_exports = _load_literal_ordered_exports(
            root / initializer,
            label=f"{label} package {module}",
        )
        if observed_exports != expected_exports:
            raise SetupError(
                f"{label} package {module!r} ordered __all__ differs from the "
                "classification"
            )


def _absolute_command_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else _PROJECT_ROOT / path


class LibraryBuildPy(build_py):
    def find_package_modules(
        self, package: str, package_dir: str
    ) -> list[tuple[str, str, str]]:
        _require_classified_source_state()
        _require_source_ordered_export_state()
        modules = super().find_package_modules(package, package_dir)
        return [
            item
            for item in modules
            if f"{item[0]}.{item[1]}" not in _REPOSITORY_ONLY_MODULES
        ]

    def run(self) -> None:
        _require_classified_source_state()
        _require_source_ordered_export_state()
        build_root = _absolute_command_path(self.build_lib)
        _require_built_package_state(
            build_root,
            allow_absent_or_empty=True,
            label="pre-build package tree",
        )
        _require_built_ordered_export_state(
            build_root,
            allow_absent_or_empty=True,
            label="pre-build package tree",
        )
        super().run()
        _require_built_package_state(
            build_root,
            allow_absent_or_empty=False,
            label="post-build package tree",
        )
        _require_built_ordered_export_state(
            build_root,
            allow_absent_or_empty=False,
            label="post-build package tree",
        )


class LibraryInstallLib(install_lib):
    def install(self) -> list[str] | None:
        _require_classified_source_state()
        _require_source_ordered_export_state()
        build_root = _absolute_command_path(self.build_dir)
        install_root = _absolute_command_path(self.install_dir)
        _require_built_package_state(
            build_root,
            allow_absent_or_empty=False,
            label="install input package tree",
        )
        _require_built_ordered_export_state(
            build_root,
            allow_absent_or_empty=False,
            label="install input package tree",
        )
        _require_built_package_state(
            install_root,
            allow_absent_or_empty=True,
            label="pre-install package tree",
        )
        _require_built_ordered_export_state(
            install_root,
            allow_absent_or_empty=True,
            label="pre-install package tree",
        )
        outputs = super().install()
        _require_built_package_state(
            install_root,
            allow_absent_or_empty=False,
            label="post-install package tree",
        )
        _require_built_ordered_export_state(
            install_root,
            allow_absent_or_empty=False,
            label="post-install package tree",
        )
        return outputs


_COMMAND_CLASSES = {
    "build_py": LibraryBuildPy,
    "install_lib": LibraryInstallLib,
}


setup(cmdclass=_COMMAND_CLASSES)
