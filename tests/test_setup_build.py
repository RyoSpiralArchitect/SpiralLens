from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest
import setuptools
from setuptools.command.build_py import build_py
from setuptools.command.install_lib import install_lib
from setuptools.errors import SetupError


@pytest.fixture
def setup_module(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    setup_path = Path(__file__).resolve().parents[1] / "setup.py"
    spec = importlib.util.spec_from_file_location(
        "_spirallens_setup_build_contract",
        setup_path,
    )
    assert spec is not None
    assert spec.loader is not None
    monkeypatch.setattr(setuptools, "setup", lambda **_kwargs: None)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _set_project_root(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
) -> None:
    monkeypatch.setattr(module, "_PROJECT_ROOT", root)
    monkeypatch.setattr(module, "_SOURCE_ROOT", root / "src")


def _write_paths(root: Path, paths: set[str] | frozenset[str]) -> None:
    for member in paths:
        path = root / "src" / member
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# classified Python member\n", encoding="utf-8")


def _write_build_paths(root: Path, paths: set[str] | frozenset[str]) -> None:
    for member in paths:
        path = root / member
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# classified built member\n", encoding="utf-8")


def test_setup_accepts_exact_full_181_source_partition(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_project_root(setup_module, monkeypatch, tmp_path)
    _write_paths(tmp_path, setup_module._ALL_PYTHON_PATHS)

    setup_module._require_classified_source_state()
    assert len(setup_module._SHIPPED_PYTHON_PATHS) == 159
    assert len(setup_module._REPOSITORY_ONLY_PYTHON_PATHS) == 22
    assert len(setup_module._ALL_PYTHON_PATHS) == 181


def test_setup_accepts_exact_159_pkg_info_no_git_sdist_source(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_project_root(setup_module, monkeypatch, tmp_path)
    _write_paths(tmp_path, setup_module._SHIPPED_PYTHON_PATHS)
    (tmp_path / "PKG-INFO").write_text("Metadata-Version: 2.4\n", encoding="utf-8")

    setup_module._require_classified_source_state()


def test_setup_rejects_empty_or_partial_source_tree(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_project_root(setup_module, monkeypatch, tmp_path)
    selected = set(setup_module._ALL_PYTHON_PATHS)
    selected.remove("spirallens/core/canonical.py")
    _write_paths(tmp_path, selected)

    with pytest.raises(SetupError, match="missing=.*canonical.py"):
        setup_module._require_classified_source_state()


@pytest.mark.parametrize(
    "rogue",
    [
        "spirallens/future.py",
        "roguepkg/__init__.py",
        "spirallens/core/__pycache__/rogue.py",
    ],
)
def test_setup_rejects_every_unclassified_source_python_member(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    rogue: str,
) -> None:
    _set_project_root(setup_module, monkeypatch, tmp_path)
    _write_paths(tmp_path, setup_module._ALL_PYTHON_PATHS)
    path = tmp_path / "src" / rogue
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# unclassified\n", encoding="utf-8")

    with pytest.raises(SetupError, match="unexpected=.*rogue|unexpected=.*future"):
        setup_module._require_classified_source_state()


def test_setup_rejects_symlinked_pycache_directory(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_project_root(setup_module, monkeypatch, tmp_path)
    _write_paths(tmp_path, setup_module._ALL_PYTHON_PATHS)
    outside = tmp_path / "outside-cache"
    outside.mkdir()
    (tmp_path / "src/spirallens/core/__pycache__").symlink_to(outside)

    with pytest.raises(SetupError, match="nonordinary_entries=.*__pycache__"):
        setup_module._require_classified_source_state()


def test_manifest_rejects_partial_package_topology(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = json.loads(setup_module._CLASSIFICATION_PATH.read_text(encoding="utf-8"))
    manifest["roles"]["shipped_runtime"].append("spirallens/newpkg/module.py")
    manifest["roles"]["shipped_runtime"].sort()
    path = tmp_path / "distribution/classification.json"
    path.parent.mkdir()
    path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(setup_module, "_CLASSIFICATION_PATH", path)

    with pytest.raises(SetupError, match="package_initializer.*close"):
        setup_module._load_distribution_classification()


def test_manifest_rejects_missing_or_extra_initializer(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = json.loads(setup_module._CLASSIFICATION_PATH.read_text(encoding="utf-8"))
    manifest["roles"]["package_initializer"].remove("spirallens/core/__init__.py")
    path = tmp_path / "distribution/classification.json"
    path.parent.mkdir()
    path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(setup_module, "_CLASSIFICATION_PATH", path)

    with pytest.raises(SetupError, match="package_initializer.*close"):
        setup_module._load_distribution_classification()


def test_library_build_py_filters_repository_only_and_retains_exact_shipped(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_project_root(setup_module, monkeypatch, tmp_path)
    _write_paths(tmp_path, setup_module._ALL_PYTHON_PATHS)
    candidates = []
    for member in sorted(setup_module._ALL_PYTHON_PATHS):
        path = Path(member)
        module_name = path.stem
        package = ".".join(path.parts[:-1])
        candidates.append((package, module_name, f"/{member}"))
    monkeypatch.setattr(
        build_py,
        "find_package_modules",
        lambda _self, _package, _package_dir: list(candidates),
    )
    command = object.__new__(setup_module.LibraryBuildPy)

    observed = command.find_package_modules("spirallens", "src/spirallens")
    assert len(observed) == 159
    assert {f"{package}.{name}" for package, name, _path in observed}.isdisjoint(
        setup_module._REPOSITORY_ONLY_MODULES
    )


@pytest.mark.parametrize(
    "rogue",
    [
        "spirallens/qualification/confirmation_v1_records.py",
        "spirallens/core/__pycache__/canonical.cpython-313.pyc",
        "roguepkg/__init__.py",
    ],
)
def test_prebuild_rejects_stale_missing_or_unclassified_tree(
    setup_module: ModuleType,
    tmp_path: Path,
    rogue: str,
) -> None:
    root = tmp_path / "build/lib"
    path = root / rogue
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("stale", encoding="utf-8")

    with pytest.raises(SetupError, match="exact classified shipped Python tree"):
        setup_module._require_built_package_state(
            root,
            allow_absent_or_empty=True,
            label="pre-build package tree",
        )


def test_install_lib_rejects_bad_tree_before_super_install(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_project_root(setup_module, monkeypatch, tmp_path)
    _write_paths(tmp_path, setup_module._ALL_PYTHON_PATHS)
    build_root = tmp_path / "build/lib"
    _write_build_paths(build_root, setup_module._SHIPPED_PYTHON_PATHS)
    (build_root / "roguepkg/__init__.py").parent.mkdir()
    (build_root / "roguepkg/__init__.py").write_text("rogue", encoding="utf-8")
    called = False

    def fake_install(_command: install_lib) -> list[str]:
        nonlocal called
        called = True
        return []

    monkeypatch.setattr(install_lib, "install", fake_install)
    command = object.__new__(setup_module.LibraryInstallLib)
    command.build_dir = str(build_root)
    command.install_dir = str(tmp_path / "wheel-root")

    with pytest.raises(SetupError, match="unexpected=.*roguepkg"):
        command.install()
    assert called is False
    assert setup_module._COMMAND_CLASSES == {
        "build_py": setup_module.LibraryBuildPy,
        "install_lib": setup_module.LibraryInstallLib,
    }
