from __future__ import annotations

import stat
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.install_lib import install_lib
from setuptools.errors import SetupError


_PROJECT_ROOT = Path(__file__).absolute().parent
_SOURCE_ROOT = _PROJECT_ROOT / "src"
_REPOSITORY_EXPERIMENT_MODULES = frozenset(
    {
        "spirallens.access._pythia160_identity_acquisition",
        "spirallens.access._pythia160_preobservation",
        "spirallens.qualification.confirmation_v1_descriptive_common",
        "spirallens.qualification.confirmation_v1_descriptive_d1",
        "spirallens.qualification.confirmation_v1_descriptive_d2",
        "spirallens.qualification.confirmation_v1_descriptive_d3",
        "spirallens.qualification.confirmation_v1_descriptive_d4",
        "spirallens.qualification.confirmation_v1_descriptive_d5_inputs",
        "spirallens.qualification.confirmation_v1_descriptive_d5_outputs",
        "spirallens.qualification.confirmation_v1_descriptive_independence",
        "spirallens.qualification.confirmation_v1_design_referent_documents",
        "spirallens.qualification.confirmation_v1_deterministic_inputs",
        "spirallens.qualification.confirmation_v1_full_design_referents",
        "spirallens.qualification.confirmation_v1_materialization",
        "spirallens.qualification.confirmation_v1_official_execution",
        "spirallens.qualification.confirmation_v1_post_d6_descriptive",
        "spirallens.qualification.confirmation_v1_pre_item23_orchestrator",
        "spirallens.qualification.confirmation_v1_private_publication",
        "spirallens.qualification.confirmation_v1_records",
        "spirallens.qualification.confirmation_v1_result_publication",
        "spirallens.qualification.confirmation_v1_source_closure",
        "spirallens.qualification.confirmation_v1_source_selected_supplier",
    }
)
_REPOSITORY_EXPERIMENT_PREFIXES = (
    ("spirallens.access", "_pythia160_"),
    ("spirallens.qualification", "confirmation_v1_"),
)
_EXPECTED_REPOSITORY_EXPERIMENT_PATHS = frozenset(
    Path("src", *module_name.split(".")).with_suffix(".py").as_posix()
    for module_name in _REPOSITORY_EXPERIMENT_MODULES
)
_EXPECTED_REPOSITORY_EXPERIMENT_BUILD_PATHS = frozenset(
    Path(*module_name.split(".")).with_suffix(".py").as_posix()
    for module_name in _REPOSITORY_EXPERIMENT_MODULES
)
_REPOSITORY_EXPERIMENT_SOURCE_DIRECTORIES = (
    "src",
    "src/spirallens",
    "src/spirallens/access",
    "src/spirallens/qualification",
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


def _nonordinary_repository_experiment_source_directories() -> list[str]:
    return [
        relative_path
        for relative_path in _REPOSITORY_EXPERIMENT_SOURCE_DIRECTORIES
        if not _is_ordinary_directory(_PROJECT_ROOT / relative_path)
    ]


def _is_absent(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return False


def _observed_repository_experiment_paths() -> frozenset[str]:
    observed: set[str] = set()
    for package_name, prefix in _REPOSITORY_EXPERIMENT_PREFIXES:
        package_path = Path(*package_name.split("."))
        directory = _SOURCE_ROOT / package_path
        try:
            entries = tuple(directory.iterdir())
        except FileNotFoundError:
            continue
        for entry in entries:
            if entry.name.startswith(prefix):
                observed.add((Path("src") / package_path / entry.name).as_posix())
    return frozenset(observed)


def _observed_repository_experiment_build_paths(
    build_root: Path,
) -> frozenset[str]:
    observed: set[str] = set()
    for package_name, prefix in _REPOSITORY_EXPERIMENT_PREFIXES:
        package_path = Path(*package_name.split("."))
        directory = build_root / package_path
        try:
            entries = tuple(directory.rglob("*"))
        except OSError:
            continue
        for entry in entries:
            if entry.name.split(".", 1)[0].startswith(prefix):
                observed.add((package_path / entry.relative_to(directory)).as_posix())
    return frozenset(observed)


def _require_repository_experiment_source_state() -> None:
    non_regular_directories = _nonordinary_repository_experiment_source_directories()
    observed = (
        frozenset()
        if non_regular_directories
        else _observed_repository_experiment_paths()
    )
    non_regular = sorted(
        relative_path
        for relative_path in observed & _EXPECTED_REPOSITORY_EXPERIMENT_PATHS
        if not _is_ordinary_file(_PROJECT_ROOT / relative_path)
    )
    if (
        not non_regular_directories
        and observed == _EXPECTED_REPOSITORY_EXPERIMENT_PATHS
        and not non_regular
    ):
        return
    if (
        not non_regular_directories
        and not observed
        and _is_ordinary_file(_PROJECT_ROOT / "PKG-INFO")
        and _is_absent(_PROJECT_ROOT / ".git")
    ):
        return
    missing = sorted(_EXPECTED_REPOSITORY_EXPERIMENT_PATHS - observed)
    unexpected = sorted(observed - _EXPECTED_REPOSITORY_EXPERIMENT_PATHS)
    raise SetupError(
        "repository-experiment source set must be the exact reviewed set or "
        "the empty PKG-INFO-marked no-Git source set; "
        f"missing={missing!r}; unexpected={unexpected!r}; "
        f"non_regular={non_regular!r}; "
        f"non_regular_directories={non_regular_directories!r}; "
        f"pkg_info_regular={_is_ordinary_file(_PROJECT_ROOT / 'PKG-INFO')!r}; "
        f"git_marker_absent={_is_absent(_PROJECT_ROOT / '.git')!r}"
    )


def _require_repository_experiment_build_outputs_absent(build_root: Path) -> None:
    observed = _observed_repository_experiment_build_paths(build_root)
    non_regular = sorted(
        relative_path
        for relative_path in observed
        if not _is_ordinary_file(build_root / relative_path)
    )
    if observed:
        raise SetupError(
            "repository-experiment build outputs must be absent before build; "
            f"observed={sorted(observed)!r}; non_regular={non_regular!r}"
        )


class LibraryBuildPy(build_py):
    def find_package_modules(
        self, package: str, package_dir: str
    ) -> list[tuple[str, str, str]]:
        _require_repository_experiment_source_state()
        return [
            item
            for item in super().find_package_modules(package, package_dir)
            if f"{item[0]}.{item[1]}" not in _REPOSITORY_EXPERIMENT_MODULES
        ]

    def run(self) -> None:
        _require_repository_experiment_source_state()
        build_root = Path(self.build_lib)
        if not build_root.is_absolute():
            build_root = _PROJECT_ROOT / build_root
        _require_repository_experiment_build_outputs_absent(build_root)
        super().run()
        _require_repository_experiment_build_outputs_absent(build_root)


class LibraryInstallLib(install_lib):
    def install(self) -> list[str] | None:
        _require_repository_experiment_source_state()
        build_root = Path(self.build_dir)
        install_root = Path(self.install_dir)
        if not build_root.is_absolute():
            build_root = _PROJECT_ROOT / build_root
        if not install_root.is_absolute():
            install_root = _PROJECT_ROOT / install_root
        _require_repository_experiment_build_outputs_absent(build_root)
        _require_repository_experiment_build_outputs_absent(install_root)
        outputs = super().install()
        _require_repository_experiment_build_outputs_absent(install_root)
        return outputs


_COMMAND_CLASSES = {
    "build_py": LibraryBuildPy,
    "install_lib": LibraryInstallLib,
}


setup(cmdclass=_COMMAND_CLASSES)
