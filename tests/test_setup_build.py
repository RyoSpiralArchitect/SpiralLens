from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tarfile
from types import ModuleType
import zipfile

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


@pytest.mark.parametrize(
    ("mutation", "exception", "match"),
    [
        ("missing", SetupError, "cannot load installed import policy"),
        ("symlink", SetupError, "cannot load installed import policy"),
        ("oversize", SetupError, "cannot load installed import policy"),
        ("import_failure", ValueError, "policy import failed"),
    ],
)
def test_setup_policy_load_fails_closed(
    tmp_path: Path,
    mutation: str,
    exception: type[BaseException],
    match: str,
) -> None:
    repository = Path(__file__).resolve().parents[1]
    setup_path = tmp_path / "setup.py"
    setup_path.write_bytes((repository / "setup.py").read_bytes())
    distribution = tmp_path / "distribution"
    distribution.mkdir()
    policy = distribution / "_installed_import_policy.py"
    if mutation == "symlink":
        target = tmp_path / "policy-target.py"
        target.write_text("SCHEMA = 'untrusted'\n", encoding="utf-8")
        policy.symlink_to(target)
    elif mutation == "oversize":
        policy.write_bytes(b"#" * (1024 * 1024 + 1))
    elif mutation == "import_failure":
        policy.write_text(
            "raise ValueError('policy import failed')\n",
            encoding="utf-8",
        )
    elif mutation != "missing":  # pragma: no cover - parameter table is exhaustive
        raise AssertionError(mutation)

    with pytest.raises(exception, match=match):
        runpy.run_path(str(setup_path))


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


def _write_installed_import_contract_fixture(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    document: object | None = None,
    pyproject_source: str | None = None,
) -> tuple[Path, Path]:
    repository = Path(__file__).resolve().parents[1]
    manifest = tmp_path / "distribution/installed-imports.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    if document is None:
        manifest.write_bytes(setup_module._IMPORT_CLASSIFICATION_PATH.read_bytes())
    else:
        manifest.write_text(json.dumps(document), encoding="utf-8")
    pyproject = tmp_path / "pyproject.toml"
    if pyproject_source is None:
        pyproject.write_bytes((repository / "pyproject.toml").read_bytes())
    else:
        pyproject.write_text(pyproject_source, encoding="utf-8")
    monkeypatch.setattr(setup_module, "_PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(setup_module, "_IMPORT_CLASSIFICATION_PATH", manifest)
    return manifest, pyproject


def _minimal_pyproject(dependencies: list[str]) -> str:
    return '[project]\nname = "spirallens"\ndependencies = ' + json.dumps(dependencies)


def test_setup_installed_import_manifest_closes_exact_159_and_23_plus_1_projection(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _write_installed_import_contract_fixture(setup_module, monkeypatch, tmp_path)

    outcomes = setup_module._load_installed_import_classification()

    success = outcomes["base_import_success"]
    missing_torch = outcomes["models_extra_missing_torch"]
    assert len(success) == 154
    assert missing_torch == setup_module._POLICY["MISSING_TORCH"]
    assert len(set(success) | set(missing_torch)) == 159
    initializer_modules = {
        setup_module._module_for_python_member(member)
        for member in setup_module._PYTHON_MEMBER_CLASSIFICATION["package_initializer"]
    }
    assert len(initializer_modules & set(success)) == 23
    assert initializer_modules & set(missing_torch) == {"spirallens.adapters"}


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown_top_level",
        "wrong_schema",
        "wrong_scope",
        "wrong_claim",
        "wrong_base_dependency",
        "wrong_blocked_prefixes",
        "extra_outcome",
        "unsorted_success",
        "duplicate_success",
        "invalid_module",
        "overlap",
        "missing_module",
        "wrong_negative",
    ],
)
def test_setup_installed_import_manifest_rejects_schema_and_topology_drift(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mutation: str,
) -> None:
    original = json.loads(
        setup_module._IMPORT_CLASSIFICATION_PATH.read_text(encoding="utf-8")
    )
    if mutation == "unknown_top_level":
        original["unknown"] = True
    elif mutation == "wrong_schema":
        original["schema_version"] = "wrong"
    elif mutation == "wrong_scope":
        original["classification_scope"] = "broader"
    elif mutation == "wrong_claim":
        original["claim_boundary"] = "broader"
    elif mutation == "wrong_base_dependency":
        original["base_dependencies"][0]["requirement"] = "numpy>=1.25"
    elif mutation == "wrong_blocked_prefixes":
        original["blocked_optional_prefixes"].pop()
    elif mutation == "extra_outcome":
        original["outcomes"]["unknown"] = ["spirallens.unknown"]
    elif mutation == "unsorted_success":
        original["outcomes"]["base_import_success"][0:2] = reversed(
            original["outcomes"]["base_import_success"][0:2]
        )
    elif mutation == "duplicate_success":
        original["outcomes"]["base_import_success"].append(
            original["outcomes"]["base_import_success"][-1]
        )
    elif mutation == "invalid_module":
        original["outcomes"]["base_import_success"][-1] = "spirallens.bad-name"
        original["outcomes"]["base_import_success"].sort()
    elif mutation == "overlap":
        original["outcomes"]["base_import_success"].append(
            original["outcomes"]["models_extra_missing_torch"][0]
        )
        original["outcomes"]["base_import_success"].sort()
    elif mutation == "missing_module":
        original["outcomes"]["base_import_success"].pop()
    elif mutation == "wrong_negative":
        original["outcomes"]["models_extra_missing_torch"][-1] = (
            "spirallens.synthetic.generators"
        )
        original["outcomes"]["models_extra_missing_torch"].sort()
    else:  # pragma: no cover - parameter table is exhaustive
        raise AssertionError(mutation)
    _write_installed_import_contract_fixture(
        setup_module,
        monkeypatch,
        tmp_path,
        document=original,
    )

    with pytest.raises(SetupError):
        setup_module._load_installed_import_classification()


@pytest.mark.parametrize(
    ("malformed", "match"),
    [
        ("duplicate_json_key", "duplicate key"),
        ("invalid_utf8", "strict UTF-8 JSON"),
        ("oversized", "size bound"),
        ("symlink", "ordinary file"),
    ],
)
def test_setup_installed_import_manifest_rejects_non_strict_files(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    malformed: str,
    match: str,
) -> None:
    manifest, _pyproject = _write_installed_import_contract_fixture(
        setup_module,
        monkeypatch,
        tmp_path,
    )
    if malformed == "duplicate_json_key":
        source = manifest.read_text(encoding="utf-8")
        marker = '  "schema_version": '
        line = next(line for line in source.splitlines() if line.startswith(marker))
        manifest.write_text(
            source.replace(line, f"{line}\n{line}", 1), encoding="utf-8"
        )
    elif malformed == "invalid_utf8":
        manifest.write_bytes(b"\xff")
    elif malformed == "oversized":
        manifest.write_bytes(b" " * (1024 * 1024 + 1))
    elif malformed == "symlink":
        target = tmp_path / "installed-imports-target.json"
        target.write_bytes(manifest.read_bytes())
        manifest.unlink()
        manifest.symlink_to(target)
    else:  # pragma: no cover - parameter table is exhaustive
        raise AssertionError(malformed)

    with pytest.raises(SetupError, match=match):
        setup_module._load_installed_import_classification()


def test_setup_pyproject_dependency_gate_accepts_reordering(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _write_installed_import_contract_fixture(
        setup_module,
        monkeypatch,
        tmp_path,
        pyproject_source=_minimal_pyproject(
            ["PyYAML>=6.0", "numpy>=1.26", "scipy>=1.11"]
        ),
    )

    outcomes = setup_module._load_installed_import_classification()

    assert len(outcomes["base_import_success"]) == 154


@pytest.mark.parametrize(
    "dependencies",
    [
        ["numpy>=1.26", "scipy>=1.11", "PyYAML>=6.0", "rogue>=1"],
        ["numpy>=1.26", "scipy>=1.11"],
        ["numpy>=1.27", "scipy>=1.11", "PyYAML>=6.0"],
        ["numpy>=1.26", "numpy>=1.26", "scipy>=1.11", "PyYAML>=6.0"],
    ],
)
def test_setup_pyproject_dependency_gate_rejects_exact_set_drift(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    dependencies: list[str],
) -> None:
    _write_installed_import_contract_fixture(
        setup_module,
        monkeypatch,
        tmp_path,
        pyproject_source=_minimal_pyproject(dependencies),
    )

    with pytest.raises(SetupError, match="exact installed import base requirements"):
        setup_module._load_installed_import_classification()


@pytest.mark.parametrize("malformed", ["symlink", "invalid_toml"])
def test_setup_pyproject_dependency_gate_rejects_non_strict_file(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    malformed: str,
) -> None:
    _manifest, pyproject = _write_installed_import_contract_fixture(
        setup_module,
        monkeypatch,
        tmp_path,
    )
    if malformed == "symlink":
        target = tmp_path / "pyproject-target.toml"
        target.write_bytes(pyproject.read_bytes())
        pyproject.unlink()
        pyproject.symlink_to(target)
    else:
        pyproject.write_text("[project\n", encoding="utf-8")

    with pytest.raises(SetupError):
        setup_module._load_installed_import_classification()


def test_setup_artifacts_omit_tests_and_place_policy_only_in_sdist(
    tmp_path: Path,
) -> None:
    repository = Path(__file__).resolve().parents[1]
    source = tmp_path / "source"
    source.mkdir()
    for relative in (
        "LICENSE",
        "MANIFEST.in",
        "README.md",
        "pyproject.toml",
        "setup.py",
    ):
        shutil.copy2(repository / relative, source / relative)
    shutil.copytree(repository / "distribution", source / "distribution")
    shutil.copytree(repository / "src", source / "src")
    tracked_tests = subprocess.run(
        ["git", "ls-files", "-z", "--", "tests"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split("\0")
    tracked_tests = [relative for relative in tracked_tests if relative]
    assert tracked_tests
    for relative in tracked_tests:
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(repository / relative, target)
    assert not (source / ".git").exists()
    artifact_dir = tmp_path / "dist"
    environment = dict(os.environ)
    environment.update(
        {
            "PIP_NO_INDEX": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
        }
    )

    subprocess.run(
        [sys.executable, "setup.py", "sdist", "--dist-dir", str(artifact_dir)],
        cwd=source,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            sys.executable,
            "setup.py",
            "bdist_wheel",
            "--dist-dir",
            str(artifact_dir),
        ],
        cwd=source,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    archives = list(artifact_dir.glob("*.tar.gz"))
    assert len(archives) == 1
    expected_sdist_members = (
        "distribution/spirallens_installed_imports_v0_1.json",
        "distribution/_installed_import_policy.py",
    )
    with tarfile.open(archives[0], mode="r:gz") as archive:
        relative_members = {
            "/".join(Path(member.name).parts[1:]) for member in archive.getmembers()
        }
        assert "tests" not in relative_members
        assert not any(relative.startswith("tests/") for relative in relative_members)
        for relative in expected_sdist_members:
            matches = [
                member
                for member in archive.getmembers()
                if "/".join(Path(member.name).parts[1:]) == relative
            ]
            assert len(matches) == 1
            assert matches[0].isfile()
            handle = archive.extractfile(matches[0])
            assert handle is not None
            assert handle.read() == (repository / relative).read_bytes()

    wheels = list(artifact_dir.glob("*.whl"))
    assert len(wheels) == 1
    with zipfile.ZipFile(wheels[0]) as archive:
        assert all(
            not member.endswith("distribution/_installed_import_policy.py")
            for member in archive.namelist()
        )


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
