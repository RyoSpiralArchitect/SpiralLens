"""Fail closed when pytest resolves SpiralLens outside this worktree."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from types import ModuleType

import pytest

_REPOSITORY_ROOT = Path(__file__).resolve().parent
_EXPECTED_SOURCE_ROOT = (_REPOSITORY_ROOT / "src").resolve(strict=True)
_EXPECTED_PACKAGE_ROOT = (_REPOSITORY_ROOT / "src" / "spirallens").resolve(strict=True)
_EXPECTED_PACKAGE_INIT = (_EXPECTED_PACKAGE_ROOT / "__init__.py").resolve(strict=True)
_MISSING = object()


def _resolved_origin(value: object) -> Path | None:
    if type(value) is not str or value in {"built-in", "frozen"}:
        return None
    try:
        return Path(value).resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return None


def _same_location(left: Path | None, right: Path | None) -> bool:
    if left is None or right is None:
        return False
    try:
        return left.samefile(right)
    except (OSError, ValueError):
        return False


def _is_within_expected_package(origin: Path | None) -> bool:
    if origin is None:
        return False
    return any(
        _same_location(candidate, _EXPECTED_PACKAGE_ROOT)
        for candidate in (origin, *origin.parents)
    )


def _is_exact_single_search_path(
    paths: tuple[Path, ...], expected: Path | None
) -> bool:
    return len(paths) == 1 and _same_location(paths[0], expected)


def _module_origin_violations(name: str, module: ModuleType) -> list[str]:
    violations: list[str] = []
    file_origin = _resolved_origin(getattr(module, "__file__", None))
    spec = getattr(module, "__spec__", None)
    spec_origin = _resolved_origin(getattr(spec, "origin", None))

    if name == "spirallens":
        if not _same_location(file_origin, _EXPECTED_PACKAGE_INIT):
            violations.append(f"spirallens.__file__={file_origin!s}")
        if not _same_location(spec_origin, _EXPECTED_PACKAGE_INIT):
            violations.append(f"spirallens.__spec__.origin={spec_origin!s}")
    else:
        for label, origin in (
            ("__file__", file_origin),
            ("__spec__.origin", spec_origin),
        ):
            if not _is_within_expected_package(origin):
                violations.append(f"{name}.{label}={origin!s}")

    package_path = getattr(module, "__path__", _MISSING)
    spec_search_locations = getattr(spec, "submodule_search_locations", None)
    if package_path is not _MISSING or spec_search_locations is not None:
        expected_search_root = (
            _EXPECTED_PACKAGE_ROOT
            if name == "spirallens"
            else file_origin.parent
            if file_origin is not None
            else None
        )
        try:
            resolved_search_paths = tuple(
                Path(item).resolve(strict=True) for item in package_path
            )
        except (OSError, RuntimeError, TypeError, ValueError):
            resolved_search_paths = ()
        try:
            resolved_spec_search_locations = tuple(
                Path(item).resolve(strict=True) for item in spec_search_locations
            )
        except (OSError, RuntimeError, TypeError, ValueError):
            resolved_spec_search_locations = ()
        if not _is_exact_single_search_path(
            resolved_search_paths, expected_search_root
        ):
            violations.append(f"{name}.__path__={resolved_search_paths!r}")
        if not _is_exact_single_search_path(
            resolved_spec_search_locations, expected_search_root
        ):
            violations.append(
                f"{name}.__spec__.submodule_search_locations="
                f"{resolved_spec_search_locations!r}"
            )
    return violations


def _assert_worktree_import_origin() -> None:
    package = sys.modules.get("spirallens", _MISSING)
    if package is _MISSING:
        try:
            package = importlib.import_module("spirallens")
        except Exception as exc:
            raise pytest.UsageError(
                "SpiralLens pytest import-origin guard could not import spirallens "
                f"from {_EXPECTED_PACKAGE_ROOT}: {type(exc).__name__}: {exc}"
            ) from exc
    if type(package) is not ModuleType:
        raise pytest.UsageError(
            "SpiralLens pytest import-origin guard failed: "
            f"sys.modules['spirallens']={package!r} is not a module"
        )

    violations: list[str] = []
    for name, module in sorted(sys.modules.items()):
        if name != "spirallens" and not name.startswith("spirallens."):
            continue
        if type(module) is not ModuleType:
            violations.append(f"{name}=non-module")
            continue
        violations.extend(_module_origin_violations(name, module))

    if violations:
        details = "; ".join(violations)
        raise pytest.UsageError(
            "SpiralLens pytest import-origin guard failed: expected every "
            f"spirallens module under {_EXPECTED_PACKAGE_ROOT}; observed {details}. "
            "Use this worktree's .venv and do not reuse an editable install from "
            "another checkout."
        )


def _pin_inherited_pythonpath() -> None:
    os.environ["PYTHONPATH"] = str(_EXPECTED_SOURCE_ROOT)


def _restore_pythonpath(original: object) -> None:
    if original is _MISSING:
        os.environ.pop("PYTHONPATH", None)
    else:
        os.environ["PYTHONPATH"] = str(original)


def pytest_configure(config: pytest.Config) -> None:
    original = os.environ.get("PYTHONPATH", _MISSING)
    _pin_inherited_pythonpath()
    config.add_cleanup(lambda: _restore_pythonpath(original))


def pytest_sessionstart(session: pytest.Session) -> None:
    del session
    _pin_inherited_pythonpath()
    _assert_worktree_import_origin()


def pytest_collection_finish(session: pytest.Session) -> None:
    del session
    _pin_inherited_pythonpath()
    _assert_worktree_import_origin()
