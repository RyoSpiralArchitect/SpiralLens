from __future__ import annotations

import os
import shlex
import subprocess
import sys
import textwrap
import tomllib
from pathlib import Path

import pytest
import spirallens

REPOSITORY = Path(__file__).resolve().parents[1]
_PROBE = textwrap.dedent(
    r"""
    import importlib.machinery
    import importlib.util
    import os
    import pathlib
    import sys
    import types

    scenario = sys.argv[1]
    argument = pathlib.Path(sys.argv[2]) if len(sys.argv) == 3 else None
    sys.path.insert(0, str(pathlib.Path.cwd() / "src"))

    def preload_package(package):
        spec = importlib.util.spec_from_file_location(
            "spirallens",
            package / "__init__.py",
            submodule_search_locations=[str(package)],
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules["spirallens"] = module
        spec.loader.exec_module(module)

    if scenario in {"case-alias", "foreign-package"}:
        preload_package(argument)
    elif scenario == "foreign-submodule":
        import spirallens
        module = types.ModuleType("spirallens.foreign")
        module.__file__ = str(argument)
        module.__spec__ = importlib.machinery.ModuleSpec(
            "spirallens.foreign", loader=None, origin=str(argument)
        )
        sys.modules["spirallens.foreign"] = module
    elif scenario == "root-none":
        sys.modules["spirallens"] = None
    elif scenario == "malformed-origin":
        import spirallens
        module = types.ModuleType("spirallens.malformed")
        module.__file__ = "malformed\0origin.py"
        module.__spec__ = importlib.machinery.ModuleSpec(
            "spirallens.malformed", loader=None, origin="malformed\0origin.py"
        )
        sys.modules["spirallens.malformed"] = module
    elif scenario == "subpackage-overlay":
        import spirallens.core
        spirallens.core.__path__ = [str(argument)]
        spirallens.core.__spec__.submodule_search_locations = [str(argument)]
    elif scenario == "restore-environment":
        os.environ["PYTHONPATH"] = "sentinel-before-pytest"
    else:
        raise AssertionError(f"unknown scenario: {scenario}")

    import pytest
    target = (
        "tests/test_pytest_import_origin.py::"
        "test_current_session_uses_the_exact_worktree_package"
        if scenario == "case-alias"
        else "tests/test_public_api_surface.py"
    )
    arguments = ["-q", target]
    if scenario != "case-alias":
        arguments.insert(0, "--collect-only")
    exit_code = pytest.main(arguments)
    if scenario == "restore-environment":
        print(f"PYTHONPATH_AFTER={os.environ.get('PYTHONPATH')}")
    raise SystemExit(exit_code)
    """
)


def _clean_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for name in ("PYTHONPATH", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"):
        environment.pop(name, None)
    return environment


def _run_probe(
    scenario: str, argument: Path | None = None
) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, "-c", _PROBE, scenario]
    if argument is not None:
        command.append(str(argument))
    return subprocess.run(
        command,
        cwd=REPOSITORY,
        env=_clean_environment(),
        check=False,
        capture_output=True,
        text=True,
    )


def _assert_guard_rejects(
    completed: subprocess.CompletedProcess[str], *needles: str
) -> None:
    assert completed.returncode == pytest.ExitCode.USAGE_ERROR
    output = completed.stdout + completed.stderr
    assert "SpiralLens pytest import-origin guard failed" in output
    assert "INTERNALERROR" not in output
    for needle in needles:
        assert needle in output


def _different_case_alias(path: Path) -> Path | None:
    source = str(path)
    for index, character in enumerate(source):
        if not character.isalpha():
            continue
        alias = Path(source[:index] + character.swapcase() + source[index + 1 :])
        try:
            if alias != path and alias.samefile(path):
                return alias
        except OSError:
            continue
    return None


def test_pytest_configuration_pins_this_worktree_source_root() -> None:
    with (REPOSITORY / "pyproject.toml").open("rb") as source:
        options = tomllib.load(source)["tool"]["pytest"]["ini_options"]

    assert options["pythonpath"] == ["src"]
    assert {"-ra", "--import-mode=prepend"} <= set(shlex.split(options["addopts"]))


def test_current_session_uses_the_exact_worktree_package() -> None:
    expected = (REPOSITORY / "src" / "spirallens").resolve(strict=True)
    paths = tuple(Path(item) for item in spirallens.__path__)

    assert Path(spirallens.__file__).samefile(expected / "__init__.py")
    assert len(paths) == 1 and paths[0].samefile(expected)


def test_repo_root_inheriting_python_subprocess_uses_the_worktree_package() -> None:
    expected_source = (REPOSITORY / "src").resolve(strict=True)
    assert Path(os.environ["PYTHONPATH"]).samefile(expected_source)

    completed = subprocess.run(
        [sys.executable, "-c", "import spirallens; print(spirallens.__file__)"],
        cwd=REPOSITORY,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert Path(completed.stdout.strip()).samefile(
        expected_source / "spirallens" / "__init__.py"
    )


def test_embedded_pytest_restores_the_original_pythonpath_after_session() -> None:
    completed = _run_probe("restore-environment")

    assert completed.returncode == pytest.ExitCode.OK, (
        completed.stdout + completed.stderr
    )
    assert "PYTHONPATH_AFTER=sentinel-before-pytest" in completed.stdout


def test_guard_accepts_a_same_file_package_through_a_case_alias() -> None:
    package = (REPOSITORY / "src" / "spirallens").resolve(strict=True)
    alias = _different_case_alias(package)
    if alias is None:
        pytest.skip("filesystem exposes no different-case alias for this package")

    completed = _run_probe("case-alias", alias)

    assert completed.returncode == pytest.ExitCode.OK, (
        completed.stdout + completed.stderr
    )


def test_configured_source_root_shadows_an_unloaded_foreign_pythonpath(
    tmp_path: Path,
) -> None:
    foreign = tmp_path / "foreign-checkout" / "src" / "spirallens"
    foreign.mkdir(parents=True)
    (foreign / "__init__.py").write_text('__version__ = "foreign"\n', encoding="utf-8")
    environment = _clean_environment()
    environment["PYTHONPATH"] = str(foreign.parent)
    uncontrolled = subprocess.run(
        [sys.executable, "-c", "import spirallens; print(spirallens.__file__)"],
        cwd=REPOSITORY,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert uncontrolled.returncode == 0 and str(foreign) in uncontrolled.stdout

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "tests/test_public_api_surface.py",
        ],
        cwd=REPOSITORY,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == pytest.ExitCode.OK, (
        completed.stdout + completed.stderr
    )


def test_guard_rejects_a_preloaded_package_from_another_checkout(
    tmp_path: Path,
) -> None:
    foreign = tmp_path / "foreign-checkout" / "src" / "spirallens"
    foreign.mkdir(parents=True)
    (foreign / "__init__.py").write_text('__version__ = "foreign"\n', encoding="utf-8")

    _assert_guard_rejects(_run_probe("foreign-package", foreign), str(foreign))


def test_guard_rejects_a_preloaded_foreign_submodule(tmp_path: Path) -> None:
    foreign = tmp_path / "foreign-checkout" / "spirallens" / "foreign.py"
    foreign.parent.mkdir(parents=True)
    foreign.write_text("FOREIGN = True\n", encoding="utf-8")

    _assert_guard_rejects(
        _run_probe("foreign-submodule", foreign), "spirallens.foreign", str(foreign)
    )


def test_guard_reports_a_none_root_cache_as_usage_error() -> None:
    _assert_guard_rejects(_run_probe("root-none"), "is not a module")


def test_guard_reports_a_malformed_cached_origin_as_usage_error() -> None:
    _assert_guard_rejects(_run_probe("malformed-origin"), "spirallens.malformed")


def test_guard_rejects_a_foreign_cached_subpackage_search_path(
    tmp_path: Path,
) -> None:
    foreign = tmp_path / "foreign-checkout" / "src" / "spirallens" / "core"
    foreign.mkdir(parents=True)

    _assert_guard_rejects(
        _run_probe("subpackage-overlay", foreign),
        "spirallens.core.__path__",
        str(foreign),
    )
