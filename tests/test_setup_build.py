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
    repository = Path(__file__).resolve().parents[1]
    for member in paths:
        path = root / "src" / member
        path.parent.mkdir(parents=True, exist_ok=True)
        source = repository / "src" / member
        if member.endswith("/__init__.py"):
            path.write_bytes(source.read_bytes())
        else:
            path.write_text("# classified Python member\n", encoding="utf-8")


def _write_build_paths(root: Path, paths: set[str] | frozenset[str]) -> None:
    repository = Path(__file__).resolve().parents[1]
    for member in paths:
        path = root / member
        path.parent.mkdir(parents=True, exist_ok=True)
        source = repository / "src" / member
        if member.endswith("/__init__.py"):
            path.write_bytes(source.read_bytes())
        else:
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


def _write_export_manifest_fixture(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    document: object,
) -> None:
    path = tmp_path / "distribution/ordered-exports.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(setup_module, "_EXPORT_CLASSIFICATION_PATH", path)


def test_setup_export_manifest_rejects_missing_extra_and_invalid_packages(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    original = json.loads(
        setup_module._EXPORT_CLASSIFICATION_PATH.read_text(encoding="utf-8")
    )
    variants: list[tuple[dict[str, object], str]] = []
    missing = json.loads(json.dumps(original))
    missing["packages"].pop()
    variants.append((missing, "exactly close"))
    reordered = json.loads(json.dumps(original))
    reordered["packages"][0], reordered["packages"][1] = (
        reordered["packages"][1],
        reordered["packages"][0],
    )
    variants.append((reordered, "sorted by module"))
    extra = json.loads(json.dumps(original))
    extra["packages"].append(
        {
            "module": "spirallens.rogue",
            "initializer": "spirallens/rogue/__init__.py",
            "exports": ["Rogue"],
        }
    )
    extra["packages"].sort(key=lambda package: package["module"])
    variants.append((extra, "exactly close"))
    duplicate = json.loads(json.dumps(original))
    duplicate["packages"][0]["exports"].append(duplicate["packages"][0]["exports"][0])
    variants.append((duplicate, "ordered"))
    nonstring = json.loads(json.dumps(original))
    nonstring["packages"][0]["exports"][0] = 1
    variants.append((nonstring, "ordered"))
    empty = json.loads(json.dumps(original))
    empty["packages"][0]["exports"] = []
    variants.append((empty, "ordered"))

    for index, (document, match) in enumerate(variants):
        directory = tmp_path / str(index)
        _write_export_manifest_fixture(
            setup_module,
            monkeypatch,
            directory,
            document,
        )
        with pytest.raises(SetupError, match=match):
            setup_module._load_ordered_export_classification()


def test_setup_export_manifest_rejects_missing_file(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "distribution/missing.json"
    path.parent.mkdir(parents=True)
    monkeypatch.setattr(setup_module, "_EXPORT_CLASSIFICATION_PATH", path)

    with pytest.raises(SetupError, match="ordinary file"):
        setup_module._load_ordered_export_classification()


@pytest.mark.parametrize(
    "source",
    [
        "__all__ = ['alpha', 'beta']\n",
        "__all__ = ['alpha', 'beta', 'Gamma']\n",
        "__all__ = ['alpha']\n",
        "__all__ = ['alpha', 'alpha']\n",
        "__all__ = ['alpha', 1]\n",
        "__all__ = []\n",
        "__all__ = tuple(['alpha'])\n",
        "__all__ = ['alpha']\n__all__ = ['beta']\n",
        "__all__ = ['alpha']\n__all__ += ['beta']\n",
        "__all__ = ['alpha']\ndel __all__\n",
        "__all__ = ['alpha']\ndef mutate():\n    __all__ = ['beta']\n",
        "__all__ = ['alpha']\n__all__.append('beta')\n",
        "__all__ = ['alpha']\n__all__.extend(['beta'])\n",
        "__all__ = ['alpha']\n__all__[0] = 'beta'\n",
        "__all__ = ['alpha']\ndel __all__[0]\n",
    ],
)
def test_setup_source_ordered_exports_rejects_literal_drift_and_direct_mutation(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    source: str,
) -> None:
    _set_project_root(setup_module, monkeypatch, tmp_path)
    _write_paths(tmp_path, setup_module._ALL_PYTHON_PATHS)
    package = next(iter(setup_module._ORDERED_EXPORT_CLASSIFICATION))
    initializer = tmp_path / "src" / f"{package.replace('.', '/')}/__init__.py"
    expected = setup_module._ORDERED_EXPORT_CLASSIFICATION[package]
    if source == "__all__ = ['alpha', 'beta']\n" and expected == (
        "alpha",
        "beta",
    ):
        source = "__all__ = ['beta', 'alpha']\n"
    initializer.write_text(source, encoding="utf-8")

    with pytest.raises(SetupError):
        setup_module._require_source_ordered_export_state()


def test_setup_source_ordered_exports_rejects_actual_reorder_add_and_remove(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_project_root(setup_module, monkeypatch, tmp_path)
    _write_paths(tmp_path, setup_module._ALL_PYTHON_PATHS)
    package, expected = next(
        (package, exports)
        for package, exports in setup_module._ORDERED_EXPORT_CLASSIFICATION.items()
        if len(exports) > 1
    )
    initializer = tmp_path / "src" / f"{package.replace('.', '/')}/__init__.py"

    for changed in (
        (expected[1], expected[0], *expected[2:]),
        (*expected, "RogueExport"),
        expected[:-1],
    ):
        initializer.write_text(f"__all__ = {changed!r}\n", encoding="utf-8")
        with pytest.raises(SetupError, match="ordered __all__ differs"):
            setup_module._require_source_ordered_export_state()


def test_setup_built_ordered_exports_reject_missing_and_extra_initializer(
    setup_module: ModuleType,
    tmp_path: Path,
) -> None:
    root = tmp_path / "build/lib"
    _write_build_paths(root, setup_module._SHIPPED_PYTHON_PATHS)
    selected = next(
        member
        for member in setup_module._SHIPPED_PYTHON_PATHS
        if member.endswith("/__init__.py")
    )
    (root / selected).unlink()
    with pytest.raises(SetupError, match="initializers differ"):
        setup_module._require_built_ordered_export_state(
            root,
            allow_absent_or_empty=False,
            label="fixture",
        )

    _write_build_paths(root, setup_module._SHIPPED_PYTHON_PATHS)
    extra = root / "spirallens/rogue/__init__.py"
    extra.parent.mkdir(parents=True)
    extra.write_text("__all__ = ['Rogue']\n", encoding="utf-8")
    with pytest.raises(SetupError, match="initializers differ"):
        setup_module._require_built_ordered_export_state(
            root,
            allow_absent_or_empty=False,
            label="fixture",
        )


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
