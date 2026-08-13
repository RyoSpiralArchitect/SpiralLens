from __future__ import annotations

import json
import stat
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
_CLASSIFICATION_SCHEMA_VERSION = "spirallens.python-distribution-members.v0.1"
_CLASSIFICATION_SCOPE = (
    "physical Python member placement across repository source, sdist, and wheels"
)
_CLASSIFICATION_CLAIM_BOUNDARY = (
    "classification grants no public API, stability, compatibility, authority, "
    "scientific claim, or library maturity"
)
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


def _absolute_command_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else _PROJECT_ROOT / path


class LibraryBuildPy(build_py):
    def find_package_modules(
        self, package: str, package_dir: str
    ) -> list[tuple[str, str, str]]:
        _require_classified_source_state()
        modules = super().find_package_modules(package, package_dir)
        return [
            item
            for item in modules
            if f"{item[0]}.{item[1]}" not in _REPOSITORY_ONLY_MODULES
        ]

    def run(self) -> None:
        _require_classified_source_state()
        build_root = _absolute_command_path(self.build_lib)
        _require_built_package_state(
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


class LibraryInstallLib(install_lib):
    def install(self) -> list[str] | None:
        _require_classified_source_state()
        build_root = _absolute_command_path(self.build_dir)
        install_root = _absolute_command_path(self.install_dir)
        _require_built_package_state(
            build_root,
            allow_absent_or_empty=False,
            label="install input package tree",
        )
        _require_built_package_state(
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
        return outputs


_COMMAND_CLASSES = {
    "build_py": LibraryBuildPy,
    "install_lib": LibraryInstallLib,
}


setup(cmdclass=_COMMAND_CLASSES)
