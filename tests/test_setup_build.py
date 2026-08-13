from __future__ import annotations

import importlib.util
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


def _module_path(root: Path, module_name: str) -> Path:
    return root / Path("src", *module_name.split(".")).with_suffix(".py")


def _write_modules(root: Path, module_names: set[str] | frozenset[str]) -> None:
    for module_name in module_names:
        path = _module_path(root, module_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# reviewed repository experiment\n", encoding="utf-8")


def _write_source_directories(root: Path) -> None:
    (root / "src/spirallens/access").mkdir(parents=True)
    (root / "src/spirallens/qualification").mkdir(parents=True)


def test_setup_accepts_exact_reviewed_22_regular_source_files(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_project_root(setup_module, monkeypatch, tmp_path)
    _write_modules(tmp_path, setup_module._REPOSITORY_EXPERIMENT_MODULES)

    setup_module._require_repository_experiment_source_state()


def test_setup_accepts_empty_pkg_info_marked_no_git_source_tree(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_project_root(setup_module, monkeypatch, tmp_path)
    _write_source_directories(tmp_path)
    (tmp_path / "PKG-INFO").write_text("Metadata-Version: 2.4\n", encoding="utf-8")

    setup_module._require_repository_experiment_source_state()


def test_setup_rejects_empty_tree_with_pkg_info_when_git_marker_exists(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_project_root(setup_module, monkeypatch, tmp_path)
    _write_source_directories(tmp_path)
    (tmp_path / "PKG-INFO").write_text("Metadata-Version: 2.4\n", encoding="utf-8")
    (tmp_path / ".git").mkdir()

    with pytest.raises(SetupError, match="git_marker_absent=False"):
        setup_module._require_repository_experiment_source_state()


def test_setup_rejects_empty_tree_without_extracted_sdist_marker(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_project_root(setup_module, monkeypatch, tmp_path)

    with pytest.raises(SetupError, match="empty PKG-INFO-marked no-Git source set"):
        setup_module._require_repository_experiment_source_state()


@pytest.mark.parametrize("subset", ["qualification_only", "access_only"])
def test_setup_rejects_partial_20_plus_0_and_0_plus_2_source_sets(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    subset: str,
) -> None:
    _set_project_root(setup_module, monkeypatch, tmp_path)
    if subset == "qualification_only":
        selected = {
            name
            for name in setup_module._REPOSITORY_EXPERIMENT_MODULES
            if name.startswith("spirallens.qualification.")
        }
        assert len(selected) == 20
    else:
        selected = {
            name
            for name in setup_module._REPOSITORY_EXPERIMENT_MODULES
            if name.startswith("spirallens.access.")
        }
        assert len(selected) == 2
    _write_modules(tmp_path, selected)

    with pytest.raises(SetupError, match="exact reviewed set"):
        setup_module._require_repository_experiment_source_state()


def test_setup_rejects_future_matching_prefix_even_with_exact_22(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_project_root(setup_module, monkeypatch, tmp_path)
    _write_modules(tmp_path, setup_module._REPOSITORY_EXPERIMENT_MODULES)
    future = tmp_path / "src/spirallens/qualification/confirmation_v1_future_module.py"
    future.write_text("# not reviewed\n", encoding="utf-8")
    (tmp_path / "MANIFEST.in").write_text(
        "exclude src/spirallens/qualification/confirmation_v1_*.py\n",
        encoding="utf-8",
    )

    with pytest.raises(SetupError, match="unexpected=.*future"):
        setup_module._require_repository_experiment_source_state()


def test_setup_rejects_nonregular_reviewed_target(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_project_root(setup_module, monkeypatch, tmp_path)
    modules = sorted(setup_module._REPOSITORY_EXPERIMENT_MODULES)
    _write_modules(tmp_path, set(modules[1:]))
    _module_path(tmp_path, modules[0]).mkdir(parents=True)

    with pytest.raises(SetupError, match="non_regular=.*pythia160"):
        setup_module._require_repository_experiment_source_state()


def test_setup_rejects_symlinked_source_package_ancestor(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_project_root(setup_module, monkeypatch, tmp_path)
    outside = tmp_path / "outside-access"
    modules = {
        name
        for name in setup_module._REPOSITORY_EXPERIMENT_MODULES
        if name.startswith("spirallens.access.")
    }
    for module_name in modules:
        path = outside / f"{module_name.rsplit('.', 1)[1]}.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# outside source\n", encoding="utf-8")
    (tmp_path / "src/spirallens").mkdir(parents=True)
    (tmp_path / "src/spirallens/access").symlink_to(outside)
    qualification = {
        name
        for name in setup_module._REPOSITORY_EXPERIMENT_MODULES
        if name.startswith("spirallens.qualification.")
    }
    _write_modules(tmp_path, qualification)

    with pytest.raises(SetupError, match="non_regular_directories=.*access"):
        setup_module._require_repository_experiment_source_state()


def test_library_build_py_filters_exact_closed_set_only(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_project_root(setup_module, monkeypatch, tmp_path)
    _write_modules(tmp_path, setup_module._REPOSITORY_EXPERIMENT_MODULES)
    candidates = [
        (*module_name.rsplit(".", 1), f"/{module_name}.py")
        for module_name in sorted(setup_module._REPOSITORY_EXPERIMENT_MODULES)
    ]
    candidates.extend(
        [
            ("spirallens.access", "contracts", "/spirallens/access/contracts.py"),
            (
                "spirallens.qualification",
                "confirmation_attempt_records",
                "/spirallens/qualification/confirmation_attempt_records.py",
            ),
        ]
    )
    monkeypatch.setattr(
        build_py,
        "find_package_modules",
        lambda _self, _package, _package_dir: list(candidates),
    )
    command = object.__new__(setup_module.LibraryBuildPy)

    assert command.find_package_modules("spirallens", "src/spirallens") == [
        ("spirallens.access", "contracts", "/spirallens/access/contracts.py"),
        (
            "spirallens.qualification",
            "confirmation_attempt_records",
            "/spirallens/qualification/confirmation_attempt_records.py",
        ),
    ]


def test_setup_rejects_stale_repository_experiment_build_outputs(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_project_root(setup_module, monkeypatch, tmp_path)
    _write_modules(tmp_path, setup_module._REPOSITORY_EXPERIMENT_MODULES)
    stale = tmp_path / "build/lib/spirallens/qualification/confirmation_v1_records.py"
    stale.parent.mkdir(parents=True)
    stale.write_text("# stale build target\n", encoding="utf-8")

    with pytest.raises(
        SetupError,
        match="repository-experiment build outputs must be absent",
    ):
        setup_module._require_repository_experiment_build_outputs_absent(
            tmp_path / "build/lib"
        )


def test_setup_rejects_nonregular_stale_build_output(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_project_root(setup_module, monkeypatch, tmp_path)
    _write_modules(tmp_path, setup_module._REPOSITORY_EXPERIMENT_MODULES)
    target = tmp_path / "ordinary-target.py"
    target.write_text("# target\n", encoding="utf-8")
    stale = tmp_path / "build/lib/spirallens/access/_pythia160_preobservation.py"
    stale.parent.mkdir(parents=True)
    stale.symlink_to(target)

    with pytest.raises(
        SetupError,
        match="non_regular=.*_pythia160_preobservation.py",
    ):
        setup_module._require_repository_experiment_build_outputs_absent(
            tmp_path / "build/lib"
        )


def test_setup_rejects_pep3147_stale_build_output(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_project_root(setup_module, monkeypatch, tmp_path)
    stale = (
        tmp_path
        / "build/lib/spirallens/qualification/__pycache__/"
        / "confirmation_v1_records.cpython-313.pyc"
    )
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"stale bytecode")

    with pytest.raises(
        SetupError,
        match="repository-experiment build outputs must be absent",
    ):
        setup_module._require_repository_experiment_build_outputs_absent(
            tmp_path / "build/lib"
        )


def test_install_lib_rejects_stale_build_output_even_when_build_is_skipped(
    setup_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_project_root(setup_module, monkeypatch, tmp_path)
    _write_modules(tmp_path, setup_module._REPOSITORY_EXPERIMENT_MODULES)
    stale = tmp_path / "build/lib/spirallens/qualification/confirmation_v1_records.py"
    stale.parent.mkdir(parents=True)
    stale.write_text("# stale skip-build target\n", encoding="utf-8")
    install_called = False

    def fake_install(_command: install_lib) -> list[str]:
        nonlocal install_called
        install_called = True
        return []

    monkeypatch.setattr(install_lib, "install", fake_install)
    command = object.__new__(setup_module.LibraryInstallLib)
    command.build_dir = str(tmp_path / "build/lib")
    command.install_dir = str(tmp_path / "wheel-root")

    with pytest.raises(
        SetupError,
        match="repository-experiment build outputs must be absent",
    ):
        command.install()
    assert install_called is False
    assert setup_module._COMMAND_CLASSES == {
        "build_py": setup_module.LibraryBuildPy,
        "install_lib": setup_module.LibraryInstallLib,
    }
