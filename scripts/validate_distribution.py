#!/usr/bin/env python3
"""Build and inspect a SpiralLens wheel in a fresh virtual environment.

The validator intentionally runs from a neutral temporary directory.  It
builds an sdist and wheel from a private source copy, installs the wheel without
dependencies, and then proves that the inspected package came from that
environment rather than an editable checkout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile
from collections.abc import Sequence
from pathlib import Path, PurePosixPath

REPORT_SCHEMA_VERSION = "spirallens.distribution-validation.v0.2"
DEFAULT_IMPORTS = (
    "spirallens",
    "spirallens.core",
    "spirallens.core.canonical",
    "spirallens.access",
)
DEFAULT_SCIENTIFIC_IMPORTS = (
    "spirallens.qualification",
    "spirallens.qualification.confirmation_c1",
    "spirallens.qualification.confirmation_crossed_development",
    "spirallens.qualification.confirmation_execution_design",
    "spirallens.qualification.confirmation_execution_kernel",
    "spirallens.qualification.confirmation_protocol",
    "spirallens.qualification.confirmation_rebinding",
    "spirallens.qualification.confirmation_replay_contracts",
    "spirallens.qualification.confirmation_source_closure",
    "spirallens.synthetic.spectral_moment_confirmation",
)
FORBIDDEN_IMPORTS = (
    "faiss",
    "huggingface_hub",
    "numpy",
    "safetensors",
    "scipy",
    "torch",
    "transformers",
    "yaml",
)
REQUIRED_WHEEL_MEMBERS = (
    "spirallens/graphs/__init__.py",
    "spirallens/graphs/common.py",
    "spirallens/graphs/constructors.py",
    "spirallens/graphs/contracts.py",
    "spirallens/graphs/diversity.py",
    "spirallens/graphs/domain.py",
    "spirallens/qualification/__init__.py",
    "spirallens/qualification/advancement.py",
    "spirallens/qualification/aggregation.py",
    "spirallens/qualification/blind.py",
    "spirallens/qualification/common.py",
    "spirallens/qualification/confirmation_c1.py",
    "spirallens/qualification/confirmation_crossed_development.py",
    "spirallens/qualification/confirmation_execution_design.py",
    "spirallens/qualification/confirmation_execution_kernel.py",
    "spirallens/qualification/confirmation_protocol.py",
    "spirallens/qualification/confirmation_rebinding.py",
    "spirallens/qualification/confirmation_replay_contracts.py",
    "spirallens/qualification/confirmation_source_closure.py",
    "spirallens/qualification/contracts.py",
    "spirallens/qualification/crossed.py",
    "spirallens/qualification/evidence_bundle.py",
    "spirallens/qualification/freeze.py",
    "spirallens/qualification/launch.py",
    "spirallens/qualification/metamorphic.py",
    "spirallens/qualification/persistence.py",
    "spirallens/qualification/pipeline_metamorphic.py",
    "spirallens/qualification/preparation.py",
    "spirallens/qualification/prerequisites.py",
    "spirallens/qualification/protocol.py",
    "spirallens/qualification/runner.py",
    "spirallens/qualification/source_binding.py",
    "spirallens/qualification/winding.py",
    "spirallens/synthetic/cartesian_fourier_domain_phantom.py",
    "spirallens/synthetic/cartesian_fourier_estimator.py",
    "spirallens/synthetic/representation_estimator.py",
    "spirallens/synthetic/spectral_moment_confirmation.py",
)
_COPY_IGNORE = (
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "*.egg-info",
    "*.pyc",
    "build",
    "dist",
    "runs",
)


class DistributionValidationError(RuntimeError):
    """Raised when a built distribution violates the validation contract."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _run(
    command: Sequence[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [str(value) for value in command],
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        if len(detail) > 4000:
            detail = detail[-4000:]
        raise DistributionValidationError(
            f"command failed with exit code {completed.returncode}: "
            f"{' '.join(str(value) for value in command)}"
            + (f"\n{detail}" if detail else "")
        )
    return completed


def _copy_source(source_root: Path, destination: Path) -> None:
    if not (source_root / "pyproject.toml").is_file():
        raise DistributionValidationError(
            f"source root has no pyproject.toml: {source_root}"
        )
    shutil.copytree(
        source_root,
        destination,
        ignore=shutil.ignore_patterns(*_COPY_IGNORE),
    )


def _single_artifact(directory: Path, pattern: str, *, label: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if len(matches) != 1 or not matches[0].is_file():
        raise DistributionValidationError(
            f"expected exactly one {label} artifact, found "
            f"{[path.name for path in matches]}"
        )
    return matches[0]


def _extract_sdist(source: Path, destination: Path) -> Path:
    """Extract one regular-file-only sdist under one top-level directory."""

    destination.mkdir()
    with tarfile.open(source, mode="r:gz") as archive:
        members = archive.getmembers()
        if not members:
            raise DistributionValidationError("sdist archive is empty")
        top_levels: set[str] = set()
        checked: list[tuple[tarfile.TarInfo, PurePosixPath]] = []
        for member in members:
            relative = PurePosixPath(member.name)
            if (
                relative.is_absolute()
                or not relative.parts
                or any(part in {"", ".", ".."} for part in relative.parts)
            ):
                raise DistributionValidationError(
                    f"sdist contains an unsafe path: {member.name!r}"
                )
            if not (member.isdir() or member.isfile()):
                raise DistributionValidationError(
                    "sdist may contain only directories and regular files: "
                    f"{member.name!r}"
                )
            top_levels.add(relative.parts[0])
            checked.append((member, relative))
        if len(top_levels) != 1:
            raise DistributionValidationError(
                "sdist must contain exactly one top-level directory"
            )
        for member, relative in checked:
            output = destination.joinpath(*relative.parts)
            if member.isdir():
                output.mkdir(parents=True, exist_ok=True)
                continue
            output.parent.mkdir(parents=True, exist_ok=True)
            source_handle = archive.extractfile(member)
            if source_handle is None:
                raise DistributionValidationError(
                    f"cannot extract regular sdist member: {member.name!r}"
                )
            with source_handle, output.open("xb") as destination_handle:
                shutil.copyfileobj(source_handle, destination_handle)
    extracted = destination / next(iter(top_levels))
    if not (extracted / "pyproject.toml").is_file():
        raise DistributionValidationError(
            "extracted sdist has no top-level pyproject.toml"
        )
    return extracted


def _require_wheel_members(
    wheel: Path,
    *,
    required_members: Sequence[str],
) -> tuple[str, ...]:
    with zipfile.ZipFile(wheel) as archive:
        members = set(archive.namelist())
    missing = sorted(set(required_members) - members)
    if missing:
        raise DistributionValidationError(
            f"wheel is missing required package members: {missing}"
        )
    return tuple(sorted(required_members))


def _venv_executable(environment: Path, name: str) -> Path:
    if os.name == "nt":
        suffix = ".exe" if name in {"python", "spirallens"} else ""
        return environment / "Scripts" / f"{name}{suffix}"
    return environment / "bin" / name


def _clean_subprocess_environment(
    *,
    exclude_user_site: bool = True,
    no_package_index: bool = True,
) -> dict[str, str]:
    environment = dict(os.environ)
    for name in (
        "PYTHONHOME",
        "PYTHONPATH",
        "PYTHONSTARTUP",
        "VIRTUAL_ENV",
    ):
        environment.pop(name, None)
    environment.update(
        {
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONSAFEPATH": "1",
        }
    )
    if no_package_index:
        environment["PIP_NO_INDEX"] = "1"
    else:
        environment.pop("PIP_NO_INDEX", None)
    if exclude_user_site:
        environment["PYTHONNOUSERSITE"] = "1"
    else:
        environment.pop("PYTHONNOUSERSITE", None)
    return environment


_PROBE = r"""
import contextlib
import importlib
import importlib.metadata
import io
import json
from pathlib import Path
import sys

required_imports = json.loads(sys.argv[1])
forbidden_imports = set(json.loads(sys.argv[2]))

module_origins = {}
for name in required_imports:
    module = importlib.import_module(name)
    origin = getattr(module, "__file__", None)
    if not isinstance(origin, str):
        raise RuntimeError(f"{name} has no concrete module origin")
    module_origins[name] = str(Path(origin).resolve())

from spirallens.cli import main

help_stdout = io.StringIO()
help_stderr = io.StringIO()
help_exit_code = None
with contextlib.redirect_stdout(help_stdout), contextlib.redirect_stderr(
    help_stderr
):
    try:
        help_exit_code = int(main(["--help"]))
    except SystemExit as error:
        help_exit_code = int(error.code)

distribution = importlib.metadata.distribution("spirallens")
direct_url_text = distribution.read_text("direct_url.json")
direct_url = (
    None if direct_url_text is None else json.loads(direct_url_text)
)
loaded_top_levels = sorted(
    {
        name.split(".", 1)[0]
        for name in sys.modules
        if name.split(".", 1)[0] in forbidden_imports
    }
)
print(
    json.dumps(
        {
            "distribution_root": str(
                Path(distribution.locate_file("")).resolve()
            ),
            "direct_url": direct_url,
            "forbidden_imports_loaded": loaded_top_levels,
            "help_exit_code": help_exit_code,
            "help_stderr": help_stderr.getvalue(),
            "help_stdout": help_stdout.getvalue(),
            "module_origins": module_origins,
            "package_version": distribution.version,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
)
"""


def _parse_probe_output(
    output: str,
    *,
    environment_root: Path,
    required_imports: Sequence[str],
) -> dict[str, object]:
    try:
        value = json.loads(output)
    except json.JSONDecodeError as error:
        raise DistributionValidationError(
            "installed-wheel probe did not emit valid JSON"
        ) from error
    if not isinstance(value, dict):
        raise DistributionValidationError(
            "installed-wheel probe output must be a JSON object"
        )

    origins = value.get("module_origins")
    expected_imports = list(required_imports)
    if (
        not isinstance(origins, dict)
        or sorted(origins) != sorted(expected_imports)
        or any(not isinstance(item, str) for item in origins.values())
    ):
        raise DistributionValidationError(
            "installed-wheel probe returned incomplete module origins"
        )

    environment_root = environment_root.resolve()
    checked_origins: dict[str, str] = {}
    for name in expected_imports:
        origin = Path(origins[name]).resolve()
        if not origin.is_relative_to(environment_root):
            raise DistributionValidationError(
                f"{name} imported outside the fresh wheel environment: {origin}"
            )
        checked_origins[name] = origin.relative_to(environment_root).as_posix()

    distribution_root_value = value.get("distribution_root")
    if not isinstance(distribution_root_value, str):
        raise DistributionValidationError(
            "installed-wheel probe omitted distribution_root"
        )
    distribution_root = Path(distribution_root_value).resolve()
    if not distribution_root.is_relative_to(environment_root):
        raise DistributionValidationError(
            "spirallens distribution metadata resolved outside the fresh "
            f"wheel environment: {distribution_root}"
        )

    direct_url = value.get("direct_url")
    if direct_url is not None and not isinstance(direct_url, dict):
        raise DistributionValidationError(
            "installed-wheel direct_url metadata is malformed"
        )
    if (
        isinstance(direct_url, dict)
        and isinstance(direct_url.get("dir_info"), dict)
        and direct_url["dir_info"].get("editable") is True
    ):
        raise DistributionValidationError(
            "fresh environment contains an editable SpiralLens install"
        )

    forbidden = value.get("forbidden_imports_loaded")
    if forbidden != []:
        raise DistributionValidationError(
            f"core/access/CLI imports loaded forbidden modules: {forbidden!r}"
        )
    if value.get("help_exit_code") != 0:
        raise DistributionValidationError(
            "installed SpiralLens CLI --help did not exit successfully"
        )
    help_stdout = value.get("help_stdout")
    if not isinstance(help_stdout, str) or "usage: spirallens" not in help_stdout:
        raise DistributionValidationError(
            "installed SpiralLens CLI --help output is missing its usage line"
        )
    if value.get("help_stderr") != "":
        raise DistributionValidationError(
            "installed SpiralLens CLI --help wrote unexpected stderr"
        )

    package_version = value.get("package_version")
    if not isinstance(package_version, str) or not package_version:
        raise DistributionValidationError(
            "installed-wheel probe omitted the package version"
        )
    return {
        "cli_help_sha256": hashlib.sha256(help_stdout.encode("utf-8")).hexdigest(),
        "direct_url_editable": False,
        "distribution_root": distribution_root.relative_to(environment_root).as_posix(),
        "forbidden_imports_loaded": [],
        "module_origins": checked_origins,
        "package_version": package_version,
    }


def validate_distribution(
    source_root: Path,
    *,
    required_imports: Sequence[str] = DEFAULT_IMPORTS,
    required_scientific_imports: Sequence[str] = DEFAULT_SCIENTIFIC_IMPORTS,
) -> dict[str, object]:
    """Build, install, and inspect the current SpiralLens distribution."""

    source_root = source_root.resolve(strict=True)
    imports = tuple(required_imports)
    scientific_imports = tuple(required_scientific_imports)
    if not imports or any(not isinstance(name, str) or not name for name in imports):
        raise DistributionValidationError(
            "required_imports must contain non-empty module names"
        )
    if len(set(imports)) != len(imports):
        raise DistributionValidationError(
            "required_imports must not contain duplicates"
        )
    if not scientific_imports or any(
        not isinstance(name, str) or not name for name in scientific_imports
    ):
        raise DistributionValidationError(
            "required_scientific_imports must contain non-empty module names"
        )
    if len(set(scientific_imports)) != len(scientific_imports):
        raise DistributionValidationError(
            "required_scientific_imports must not contain duplicates"
        )

    with tempfile.TemporaryDirectory(
        prefix="spirallens-distribution-validation-"
    ) as temporary_name:
        temporary = Path(temporary_name)
        staged_source = temporary / "source"
        artifact_dir = temporary / "artifacts"
        extracted_dir = temporary / "extracted"
        wheel_artifact_dir = temporary / "wheel-artifacts"
        environment_root = temporary / "venv"
        scientific_environment_root = temporary / "scientific-venv"
        neutral_cwd = temporary / "neutral"
        artifact_dir.mkdir()
        wheel_artifact_dir.mkdir()
        neutral_cwd.mkdir()
        _copy_source(source_root, staged_source)

        _run(
            (
                sys.executable,
                "-m",
                "build",
                "--sdist",
                "--outdir",
                str(artifact_dir),
            ),
            cwd=staged_source,
            env=_clean_subprocess_environment(
                exclude_user_site=False,
                no_package_index=False,
            ),
        )
        sdist = _single_artifact(artifact_dir, "*.tar.gz", label="sdist")
        extracted_source = _extract_sdist(sdist, extracted_dir)
        _run(
            (
                sys.executable,
                "-m",
                "build",
                "--wheel",
                "--outdir",
                str(wheel_artifact_dir),
            ),
            cwd=extracted_source,
            env=_clean_subprocess_environment(
                exclude_user_site=False,
                no_package_index=False,
            ),
        )
        wheel = _single_artifact(
            wheel_artifact_dir,
            "*.whl",
            label="wheel",
        )
        verified_wheel_members = _require_wheel_members(
            wheel,
            required_members=REQUIRED_WHEEL_MEMBERS,
        )

        venv.EnvBuilder(
            with_pip=True,
            system_site_packages=False,
            clear=False,
            symlinks=True,
        ).create(environment_root)
        environment = _clean_subprocess_environment(exclude_user_site=True)
        venv_python = _venv_executable(environment_root, "python")
        _run(
            (
                str(venv_python),
                "-m",
                "pip",
                "install",
                "--no-deps",
                "--force-reinstall",
                str(wheel),
            ),
            cwd=neutral_cwd,
            env=environment,
        )

        probe = _run(
            (
                str(venv_python),
                "-P",
                "-c",
                _PROBE,
                json.dumps(imports),
                json.dumps(FORBIDDEN_IMPORTS),
            ),
            cwd=neutral_cwd,
            env=environment,
        )
        inspection = _parse_probe_output(
            probe.stdout,
            environment_root=environment_root,
            required_imports=imports,
        )

        # Qualification is a scientific surface and intentionally imports its
        # declared numerical dependencies.  A second fresh environment uses
        # the host's already-installed system/user dependencies while still
        # requiring the SpiralLens module itself to originate from this exact
        # non-editable wheel installation.
        venv.EnvBuilder(
            with_pip=True,
            system_site_packages=True,
            clear=False,
            symlinks=True,
        ).create(scientific_environment_root)
        scientific_environment = _clean_subprocess_environment(exclude_user_site=False)
        scientific_python = _venv_executable(
            scientific_environment_root,
            "python",
        )
        _run(
            (
                str(scientific_python),
                "-m",
                "pip",
                "install",
                "--no-deps",
                "--force-reinstall",
                str(wheel),
            ),
            cwd=neutral_cwd,
            env=scientific_environment,
        )
        scientific_probe = _run(
            (
                str(scientific_python),
                "-P",
                "-c",
                _PROBE,
                json.dumps(scientific_imports),
                json.dumps(()),
            ),
            cwd=neutral_cwd,
            env=scientific_environment,
        )
        scientific_inspection = _parse_probe_output(
            scientific_probe.stdout,
            environment_root=scientific_environment_root,
            required_imports=scientific_imports,
        )

        cli = _venv_executable(environment_root, "spirallens")
        if not cli.is_file():
            raise DistributionValidationError(
                "wheel install did not create the spirallens console script"
            )
        entrypoint = _run(
            (str(cli), "--help"),
            cwd=neutral_cwd,
            env=environment,
        )
        if "usage: spirallens" not in entrypoint.stdout:
            raise DistributionValidationError(
                "installed console script --help output is invalid"
            )
        entrypoint_help_sha256 = hashlib.sha256(
            entrypoint.stdout.encode("utf-8")
        ).hexdigest()
        if entrypoint_help_sha256 != inspection["cli_help_sha256"]:
            raise DistributionValidationError(
                "console script and imported CLI produced different --help output"
            )

        return {
            "schema_version": REPORT_SCHEMA_VERSION,
            "status": "pass",
            "artifacts": [
                {
                    "filename": sdist.name,
                    "kind": "sdist",
                    "sha256": _sha256_file(sdist),
                    "size_bytes": sdist.stat().st_size,
                },
                {
                    "filename": wheel.name,
                    "kind": "wheel",
                    "sha256": _sha256_file(wheel),
                    "size_bytes": wheel.stat().st_size,
                },
            ],
            "build": {
                "frontend": "python-build",
                "isolation": True,
                "source_copy": True,
                "wheel_built_from_sdist": True,
            },
            "installation": {
                "no_dependencies": True,
                "system_site_packages": False,
                "scientific_surface_system_site_packages": True,
                "scientific_surface_user_site_packages": True,
                "wheel_filename": wheel.name,
            },
            "inspection": inspection,
            "scientific_surface_inspection": scientific_inspection,
            "required_wheel_members": list(verified_wheel_members),
            "forbidden_imports": list(FORBIDDEN_IMPORTS),
            "required_imports": list(imports),
            "required_scientific_imports": list(scientific_imports),
        }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "build SpiralLens and validate a non-editable wheel install in a "
            "fresh virtual environment"
        )
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument(
        "--import-module",
        action="append",
        dest="required_imports",
        help=(
            "module that must import from the installed wheel; repeat to "
            "replace the default core/access import set"
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _build_parser().parse_args(argv)
    required_imports = (
        DEFAULT_IMPORTS
        if arguments.required_imports is None
        else tuple(arguments.required_imports)
    )
    try:
        report = validate_distribution(
            arguments.source_root,
            required_imports=required_imports,
        )
    except Exception as error:  # noqa: BLE001 - CLI must emit a failure receipt.
        report = {
            "schema_version": REPORT_SCHEMA_VERSION,
            "status": "fail",
            "error": {
                "message": str(error),
                "type": type(error).__name__,
            },
        }
        print(
            json.dumps(
                report,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print(
        json.dumps(
            report,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
