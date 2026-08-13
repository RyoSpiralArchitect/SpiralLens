#!/usr/bin/env python3
"""Build and inspect a SpiralLens wheel in a fresh virtual environment.

The validator intentionally runs from a neutral temporary directory.  It
builds an sdist and wheel from a private source copy, installs the wheel without
dependencies, and then proves that the inspected package came from that
environment rather than an editable checkout.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile
from collections.abc import Sequence
from pathlib import Path, PurePosixPath

REPORT_SCHEMA_VERSION = "spirallens.distribution-validation.v0.6"
PYTHON_MEMBER_CLASSIFICATION_PATH = "distribution/spirallens_python_members_v0_1.json"
PYTHON_MEMBER_CLASSIFICATION_SCHEMA_VERSION = (
    "spirallens.python-distribution-members.v0.1"
)
PYTHON_MEMBER_CLASSIFICATION_SCOPE = (
    "physical Python member placement across repository source, sdist, and wheels"
)
PYTHON_MEMBER_CLASSIFICATION_CLAIM_BOUNDARY = (
    "classification grants no public API, stability, compatibility, authority, "
    "scientific claim, or library maturity"
)
PYTHON_MEMBER_ROLE_NAMES = (
    "package_initializer",
    "console_entrypoint_runtime",
    "shipped_runtime",
    "repository_only",
)
DEFAULT_IMPORTS = (
    "spirallens",
    "spirallens._held_file",
    "spirallens.core",
    "spirallens.core.canonical",
    "spirallens.access",
)
DEFAULT_SCIENTIFIC_IMPORTS = (
    "spirallens.qualification",
    "spirallens.qualification.confirmation_attempt_authority",
    "spirallens.qualification.confirmation_attempt_evidence",
    "spirallens.qualification.confirmation_attempt_evidence_validation",
    "spirallens.qualification.confirmation_attempt_persistence",
    "spirallens.qualification.confirmation_attempt_records",
    "spirallens.qualification.confirmation_attempt_terminal_persistence",
    "spirallens.qualification.confirmation_attempt_validation",
    "spirallens.qualification.confirmation_c1",
    "spirallens.qualification.confirmation_crossed_development",
    "spirallens.qualification.confirmation_execution_design",
    "spirallens.qualification.confirmation_execution_kernel",
    "spirallens.qualification.confirmation_protocol",
    "spirallens.qualification.confirmation_rebinding",
    "spirallens.qualification.confirmation_replay_contracts",
    "spirallens.qualification.confirmation_result_component_validation",
    "spirallens.qualification.confirmation_result_components",
    "spirallens.qualification.confirmation_external_witness",
    "spirallens.qualification.confirmation_runner",
    "spirallens.qualification.confirmation_source_closure",
    "spirallens.qualification.confirmation_terminal_operations",
    "spirallens.synthetic.spectral_moment_confirmation",
)
ATLAS_READER_IMPORTS = (
    "spirallens.atlas",
    "spirallens.atlas.store",
    "spirallens.atlas.engineering_receipt",
)
ATLAS_READER_FORBIDDEN_IMPORTS = (
    "torch",
    "transformers",
    "huggingface_hub",
    "safetensors",
    "spirallens.adapters",
    "spirallens.atlas.id_sweep",
    "spirallens.atlas.engineering_run",
    "spirallens.atlas._capture_store",
)
ATLAS_PUBLIC_EXPORTS = (
    "ATLAS_SCHEMA_VERSION",
    "ATLAS_CONTEXT_BINDING_SCHEMA_VERSION",
    "AtlasIntegrityError",
    "AtlasStateError",
    "ContextBankBinding",
    "EngineeringConsumerAuthorizationError",
    "LoadedPublicExamplePlumbingProtocol",
    "PublicExamplePlumbingProtocolError",
    "PublicExamplePlumbingReceiptError",
    "PublicExamplePlumbingRunError",
    "SweepConfig",
    "load_manifest",
    "load_manifest_metadata",
    "load_public_example_plumbing_protocol",
    "load_public_example_plumbing_receipt",
    "require_engineering_consumer_authorized",
    "run_id_sweep",
    "run_public_example_plumbing",
    "select_token_ids",
    "validate_engineering_request_binding",
)
ATLAS_READER_SYMBOL_MODULES = {
    "AtlasIntegrityError": "spirallens.atlas.store",
    "AtlasStateError": "spirallens.atlas.store",
    "PublicExamplePlumbingReceiptError": ("spirallens.atlas.engineering_receipt"),
    "load_manifest": "spirallens.atlas.store",
    "load_manifest_metadata": "spirallens.atlas.store",
    "load_public_example_plumbing_receipt": ("spirallens.atlas.engineering_receipt"),
}
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
REPOSITORY_EXPERIMENT_WHEEL_MEMBER_PREFIXES = (
    "spirallens/access/_pythia160_",
    "spirallens/qualification/confirmation_v1_",
)
REPOSITORY_EXPERIMENT_SOURCE_PATHS = (
    "src/spirallens/access/_pythia160_identity_acquisition.py",
    "src/spirallens/access/_pythia160_preobservation.py",
    "src/spirallens/qualification/confirmation_v1_descriptive_common.py",
    "src/spirallens/qualification/confirmation_v1_descriptive_d1.py",
    "src/spirallens/qualification/confirmation_v1_descriptive_d2.py",
    "src/spirallens/qualification/confirmation_v1_descriptive_d3.py",
    "src/spirallens/qualification/confirmation_v1_descriptive_d4.py",
    "src/spirallens/qualification/confirmation_v1_descriptive_d5_inputs.py",
    "src/spirallens/qualification/confirmation_v1_descriptive_d5_outputs.py",
    "src/spirallens/qualification/confirmation_v1_descriptive_independence.py",
    "src/spirallens/qualification/confirmation_v1_design_referent_documents.py",
    "src/spirallens/qualification/confirmation_v1_deterministic_inputs.py",
    "src/spirallens/qualification/confirmation_v1_full_design_referents.py",
    "src/spirallens/qualification/confirmation_v1_materialization.py",
    "src/spirallens/qualification/confirmation_v1_official_execution.py",
    "src/spirallens/qualification/confirmation_v1_post_d6_descriptive.py",
    "src/spirallens/qualification/confirmation_v1_pre_item23_orchestrator.py",
    "src/spirallens/qualification/confirmation_v1_private_publication.py",
    "src/spirallens/qualification/confirmation_v1_records.py",
    "src/spirallens/qualification/confirmation_v1_result_publication.py",
    "src/spirallens/qualification/confirmation_v1_source_closure.py",
    "src/spirallens/qualification/confirmation_v1_source_selected_supplier.py",
)
REPOSITORY_EXPERIMENT_MODULES = tuple(
    path.removeprefix("src/").removesuffix(".py").replace("/", ".")
    for path in REPOSITORY_EXPERIMENT_SOURCE_PATHS
)
_REPOSITORY_EXPERIMENT_SOURCE_PREFIXES = (
    ("src/spirallens/access", "_pythia160_"),
    ("src/spirallens/qualification", "confirmation_v1_"),
)
_PUBLIC_PACKAGE_INIT_PATHS = {
    "spirallens.access": "src/spirallens/access/__init__.py",
    "spirallens.qualification": "src/spirallens/qualification/__init__.py",
}
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


def _ordered_path_manifest_sha256(paths: Sequence[str]) -> str:
    return hashlib.sha256(
        "".join(f"{path}\n" for path in paths).encode("utf-8")
    ).hexdigest()


def _reject_duplicate_json_object(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key {key!r}")
        value[key] = item
    return value


def _require_portable_python_member(value: object, *, role: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise DistributionValidationError(
            f"Python member role {role!r} contains a non-portable path: {value!r}"
        )
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or len(path.parts) < 2
        or path.parts[0] != "spirallens"
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.suffix != ".py"
        or "__pycache__" in path.parts
    ):
        raise DistributionValidationError(
            f"Python member role {role!r} contains an invalid path: {value!r}"
        )
    identifiers = (*path.parts[:-1], path.stem)
    if not all(item.isascii() and item.isidentifier() for item in identifiers):
        raise DistributionValidationError(
            f"Python member role {role!r} contains a non-module path: {value!r}"
        )
    return value


def _load_python_member_classification(source_root: Path) -> dict[str, object]:
    """Load and validate the literal distribution-member authority document."""

    manifest_path = source_root / PYTHON_MEMBER_CLASSIFICATION_PATH
    for required_directory in (source_root / "distribution",):
        try:
            mode = required_directory.lstat().st_mode
        except OSError as error:
            raise DistributionValidationError(
                "Python member classification has a missing distribution directory"
            ) from error
        if not stat.S_ISDIR(mode):
            raise DistributionValidationError(
                "Python member classification distribution directory must be ordinary"
            )
    try:
        manifest_mode = manifest_path.lstat().st_mode
        manifest_bytes = manifest_path.read_bytes()
    except OSError as error:
        raise DistributionValidationError(
            "cannot read the Python member classification manifest"
        ) from error
    if not stat.S_ISREG(manifest_mode):
        raise DistributionValidationError(
            "Python member classification manifest must be an ordinary file"
        )
    if len(manifest_bytes) > 1024 * 1024:
        raise DistributionValidationError(
            "Python member classification manifest exceeds its size bound"
        )
    try:
        value = json.loads(
            manifest_bytes.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_json_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise DistributionValidationError(
            "Python member classification manifest is not duplicate-free JSON"
        ) from error
    if not isinstance(value, dict) or set(value) != {
        "schema_version",
        "classification_scope",
        "claim_boundary",
        "roles",
    }:
        raise DistributionValidationError(
            "Python member classification manifest has unexpected top-level keys"
        )
    if value.get("schema_version") != PYTHON_MEMBER_CLASSIFICATION_SCHEMA_VERSION:
        raise DistributionValidationError(
            "Python member classification manifest has the wrong schema version"
        )
    if value.get("classification_scope") != PYTHON_MEMBER_CLASSIFICATION_SCOPE:
        raise DistributionValidationError(
            "Python member classification manifest has the wrong physical scope"
        )
    if value.get("claim_boundary") != PYTHON_MEMBER_CLASSIFICATION_CLAIM_BOUNDARY:
        raise DistributionValidationError(
            "Python member classification manifest has the wrong claim boundary"
        )
    raw_roles = value.get("roles")
    if not isinstance(raw_roles, dict) or set(raw_roles) != set(
        PYTHON_MEMBER_ROLE_NAMES
    ):
        raise DistributionValidationError(
            "Python member classification manifest has unexpected role keys"
        )
    roles: dict[str, tuple[str, ...]] = {}
    already_classified: set[str] = set()
    for role in PYTHON_MEMBER_ROLE_NAMES:
        raw_members = raw_roles.get(role)
        if not isinstance(raw_members, list) or not raw_members:
            raise DistributionValidationError(
                f"Python member role {role!r} must be a non-empty list"
            )
        members = tuple(
            _require_portable_python_member(member, role=role) for member in raw_members
        )
        if members != tuple(sorted(set(members))):
            raise DistributionValidationError(
                f"Python member role {role!r} must be sorted and unique"
            )
        overlap = sorted(already_classified.intersection(members))
        if overlap:
            raise DistributionValidationError(
                f"Python member roles overlap at: {overlap}"
            )
        already_classified.update(members)
        roles[role] = members
    if any(
        not member.endswith("/__init__.py") for member in roles["package_initializer"]
    ):
        raise DistributionValidationError(
            "package_initializer role contains a non-initializer member"
        )
    if any(
        member.endswith("/__init__.py")
        for role in PYTHON_MEMBER_ROLE_NAMES
        if role != "package_initializer"
        for member in roles[role]
    ):
        raise DistributionValidationError(
            "a non-initializer role contains a package initializer"
        )
    if roles["console_entrypoint_runtime"] != (
        "spirallens/__main__.py",
        "spirallens/cli.py",
    ):
        raise DistributionValidationError(
            "console_entrypoint_runtime differs from the reviewed paths"
        )
    shipped_members = tuple(
        sorted(
            member
            for role in PYTHON_MEMBER_ROLE_NAMES
            if role != "repository_only"
            for member in roles[role]
        )
    )
    repository_only_members = roles["repository_only"]
    expected_repository_only = tuple(
        path.removeprefix("src/") for path in REPOSITORY_EXPERIMENT_SOURCE_PATHS
    )
    if repository_only_members != expected_repository_only:
        raise DistributionValidationError(
            "repository_only role differs from the reviewed experiment set"
        )
    source_members = tuple(sorted((*shipped_members, *repository_only_members)))
    expected_initializers = {
        (parent / "__init__.py").as_posix()
        for member in shipped_members
        for parent in PurePosixPath(member).parents
        if parent.as_posix() not in {"."}
    }
    if set(roles["package_initializer"]) != expected_initializers:
        raise DistributionValidationError(
            "package_initializer role does not close every shipped package ancestor"
        )
    return {
        "classification_scope": value["classification_scope"],
        "claim_boundary": value["claim_boundary"],
        "manifest_path": PYTHON_MEMBER_CLASSIFICATION_PATH,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "repository_only_members": repository_only_members,
        "roles": roles,
        "schema_version": PYTHON_MEMBER_CLASSIFICATION_SCHEMA_VERSION,
        "shipped_members": shipped_members,
        "source_members": source_members,
    }


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


def _seed_stale_repository_experiment_build_outputs(source_root: Path) -> int:
    """Seed the exact forbidden set under build/lib for a stale-build adversary."""

    build_lib = source_root / "build" / "lib"
    source = source_root / "src/spirallens/qualification/confirmation_v1_records.py"
    destination = (
        build_lib
        / "spirallens/qualification/__pycache__/"
        / f"confirmation_v1_records.cpython-{sys.version_info.major}{sys.version_info.minor}.pyc"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    import py_compile

    py_compile.compile(str(source), cfile=str(destination), doraise=True)
    return 1


def _setuptools_build_python() -> str:
    candidates = tuple(
        dict.fromkeys(
            str(candidate)
            for candidate in (sys.executable, getattr(sys, "_base_executable", None))
            if candidate
        )
    )
    for candidate in candidates:
        completed = subprocess.run(
            [candidate, "-P", "-c", "import setuptools; import wheel"],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode == 0:
            return candidate
    raise DistributionValidationError(
        "stale-build adversary requires an interpreter with setuptools and wheel"
    )


def _require_stale_build_rejected(
    staged_source: Path,
    artifact_dir: Path,
) -> dict[str, object]:
    """Prove a stale build/lib experiment set fails closed before publication."""

    seeded_count = _seed_stale_repository_experiment_build_outputs(staged_source)
    completed = subprocess.run(
        [
            _setuptools_build_python(),
            "setup.py",
            "bdist_wheel",
            "--skip-build",
            "--dist-dir",
            str(artifact_dir),
        ],
        cwd=staged_source,
        env=_clean_subprocess_environment(
            exclude_user_site=False,
            no_package_index=False,
        ),
        check=False,
        capture_output=True,
        text=True,
    )
    detail = completed.stderr + completed.stdout
    if completed.returncode == 0:
        raise DistributionValidationError(
            "direct wheel build unexpectedly accepted stale repository-experiment "
            "build outputs"
        )
    if (
        "install input package tree must contain the exact classified shipped "
        "Python tree"
        not in detail
        or "confirmation_v1_records" not in detail
    ):
        raise DistributionValidationError(
            "stale repository-experiment build failed for an unrelated reason"
        )
    artifacts = sorted(artifact_dir.glob("*.whl"))
    if artifacts:
        raise DistributionValidationError(
            "stale repository-experiment build failure still published a wheel"
        )
    build_dir = staged_source / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    return {
        "observation": "rejected-before-wheel-publication",
        "seeded_target_count": seeded_count,
        "skip_build": True,
        "wheel_artifact_count": 0,
    }


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
            _require_safe_archive_member_path(member.name, artifact_kind="sdist")
            if member.isfile() and member.name.endswith("/"):
                raise DistributionValidationError(
                    f"sdist contains an unsafe path: {member.name!r}"
                )
            relative = PurePosixPath(member.name)
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


def _require_safe_archive_member_path(member: str, *, artifact_kind: str) -> None:
    if not member or "\\" in member:
        raise DistributionValidationError(
            f"{artifact_kind} contains an unsafe path: {member!r}"
        )
    path = PurePosixPath(member)
    canonical = path.as_posix()
    expected_spelling = f"{canonical}/" if member.endswith("/") else canonical
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
        or member != expected_spelling
    ):
        raise DistributionValidationError(
            f"{artifact_kind} contains an unsafe path: {member!r}"
        )


def _require_exact_python_members(
    observed_members: Sequence[str],
    *,
    expected_members: Sequence[str],
    artifact_kind: str,
) -> dict[str, object]:
    observed = tuple(sorted(observed_members))
    expected = tuple(expected_members)
    if expected != tuple(sorted(set(expected))):
        raise DistributionValidationError(
            "expected Python member classification is not sorted and unique"
        )
    missing = sorted(set(expected) - set(observed))
    unclassified = sorted(set(observed) - set(expected))
    if missing or unclassified or len(observed) != len(set(observed)):
        raise DistributionValidationError(
            f"{artifact_kind} Python member classification differs from the exact "
            f"manifest: missing={missing}, unclassified={unclassified}, "
            f"duplicates={len(observed) - len(set(observed))}"
        )
    return {
        "observation": "exact-closed-set",
        "count": len(observed),
        "manifest_sha256": _ordered_path_manifest_sha256(observed),
        "missing_count": 0,
        "unclassified_count": 0,
        "members": list(observed),
    }


def _classify_wheel_python_members(
    wheel: Path,
    *,
    expected_members: Sequence[str],
) -> dict[str, object]:
    """Require one wheel's package subtree to be the exact Python-only set."""

    with zipfile.ZipFile(wheel) as archive:
        infos = archive.infolist()
    names = [info.filename for info in infos]
    if len(names) != len(set(names)):
        raise DistributionValidationError("wheel contains duplicate archive members")
    for name in names:
        _require_safe_archive_member_path(name, artifact_kind="wheel")
    nonregular_archive_members: list[str] = []
    for info in infos:
        mode = (info.external_attr >> 16) & 0xFFFF
        file_type = stat.S_IFMT(mode)
        if info.is_dir():
            if file_type not in {0, stat.S_IFDIR}:
                nonregular_archive_members.append(info.filename)
        elif file_type not in {0, stat.S_IFREG}:
            nonregular_archive_members.append(info.filename)
    if nonregular_archive_members:
        raise DistributionValidationError(
            "wheel contains non-regular archive members: "
            f"{sorted(nonregular_archive_members)}"
        )
    package_infos = [
        info
        for info in infos
        if not (
            PurePosixPath(info.filename).parts
            and PurePosixPath(info.filename).parts[0].endswith(".dist-info")
        )
    ]
    file_infos = [info for info in package_infos if not info.is_dir()]
    non_python_regular = sorted(
        info.filename for info in file_infos if not info.filename.endswith(".py")
    )
    if non_python_regular:
        raise DistributionValidationError(
            "wheel contains non-Python regular members outside generated metadata: "
            f"{non_python_regular}"
        )
    package_members = tuple(sorted(info.filename for info in file_infos))
    non_python = sorted(
        member for member in package_members if not member.endswith(".py")
    )
    if non_python:
        raise DistributionValidationError(
            f"wheel package subtree contains non-Python members: {non_python}"
        )
    return _require_exact_python_members(
        package_members,
        expected_members=expected_members,
        artifact_kind="wheel",
    )


def _classify_sdist_python_members(
    sdist: Path,
    *,
    expected_members: Sequence[str],
) -> dict[str, object]:
    """Require an sdist's ``src/spirallens`` subtree to be the exact set."""

    with tarfile.open(sdist, mode="r:gz") as archive:
        infos = archive.getmembers()
    names = [info.name for info in infos]
    if len(names) != len(set(names)):
        raise DistributionValidationError("sdist contains duplicate archive members")
    for info in infos:
        _require_safe_archive_member_path(info.name, artifact_kind="sdist")
        if info.isfile() and info.name.endswith("/"):
            raise DistributionValidationError(
                f"sdist contains an unsafe path: {info.name!r}"
            )
    top_levels = {PurePosixPath(name).parts[0] for name in names}
    if len(top_levels) != 1:
        raise DistributionValidationError(
            "sdist must contain exactly one top-level directory"
        )
    package_infos: list[tuple[tarfile.TarInfo, str]] = []
    for info in infos:
        parts = PurePosixPath(info.name).parts
        if len(parts) >= 3 and parts[1] == "src":
            if len(parts) >= 3 and parts[2].endswith(".egg-info"):
                continue
            package_infos.append((info, "/".join(parts[2:])))
    nonregular = sorted(
        normalized
        for info, normalized in package_infos
        if not info.isdir() and not info.isfile()
    )
    if nonregular:
        raise DistributionValidationError(
            f"sdist package subtree contains non-regular members: {nonregular}"
        )
    package_members = tuple(
        sorted(normalized for info, normalized in package_infos if info.isfile())
    )
    non_python = sorted(
        member for member in package_members if not member.endswith(".py")
    )
    if non_python:
        raise DistributionValidationError(
            f"sdist package subtree contains non-Python members: {non_python}"
        )
    return _require_exact_python_members(
        package_members,
        expected_members=expected_members,
        artifact_kind="sdist",
    )


def _require_sdist_classification_manifest(
    sdist: Path,
    *,
    expected_sha256: str,
) -> dict[str, object]:
    with tarfile.open(sdist, mode="r:gz") as archive:
        matches = [
            info
            for info in archive.getmembers()
            if "/".join(PurePosixPath(info.name).parts[1:])
            == PYTHON_MEMBER_CLASSIFICATION_PATH
        ]
        if len(matches) != 1 or not matches[0].isfile():
            raise DistributionValidationError(
                "sdist must contain one regular Python member classification manifest"
            )
        handle = archive.extractfile(matches[0])
        if handle is None:
            raise DistributionValidationError(
                "cannot read the sdist Python member classification manifest"
            )
        with handle:
            payload = handle.read(1024 * 1024 + 1)
    digest = hashlib.sha256(payload).hexdigest()
    if len(payload) > 1024 * 1024 or digest != expected_sha256:
        raise DistributionValidationError(
            "sdist Python member classification manifest differs from source"
        )
    return {
        "path": PYTHON_MEMBER_CLASSIFICATION_PATH,
        "sha256": digest,
        "size_bytes": len(payload),
    }


def _classify_repository_experiment_members(wheel: Path) -> tuple[str, ...]:
    """Return repository-experiment members currently shipped in ``wheel``."""

    with zipfile.ZipFile(wheel) as archive:
        members = archive.namelist()
    return tuple(sorted(member for member in members if _is_experiment_member(member)))


def _is_experiment_member(member: str) -> bool:
    for prefix in REPOSITORY_EXPERIMENT_WHEEL_MEMBER_PREFIXES:
        package, filename_prefix = prefix.rsplit("/", 1)
        if not member.startswith(f"{package}/"):
            continue
        if PurePosixPath(member).name.split(".", 1)[0].startswith(filename_prefix):
            return True
    return False


def _classify_repository_experiment_sdist_members(sdist: Path) -> tuple[str, ...]:
    """Return matching members from an sdist's single top-level directory."""

    with tarfile.open(sdist, mode="r:gz") as archive:
        members = archive.getnames()
    matching: list[str] = []
    for member in members:
        parts = PurePosixPath(member).parts
        if not parts:
            continue
        relative = "/".join(parts[1:])
        if _is_experiment_member(relative.removeprefix("src/")):
            matching.append(member)
    return tuple(sorted(matching))


def _repository_experiment_source_report(source_root: Path) -> dict[str, object]:
    """Require the reviewed experiment set to be exact and regular in source."""

    source_directories = (
        "src",
        "src/spirallens",
        "src/spirallens/access",
        "src/spirallens/qualification",
    )
    nonregular_directories: list[str] = []
    for relative in source_directories:
        try:
            mode = (source_root / relative).lstat().st_mode
        except OSError:
            nonregular_directories.append(relative)
            continue
        if not stat.S_ISDIR(mode):
            nonregular_directories.append(relative)
    if nonregular_directories:
        raise DistributionValidationError(
            "repository-experiment source inventory contains missing, "
            "non-directory, or symlinked ancestors: "
            f"{nonregular_directories}"
        )

    observed: list[str] = []
    nonregular: list[str] = []
    for parent_name, filename_prefix in _REPOSITORY_EXPERIMENT_SOURCE_PREFIXES:
        parent = source_root / parent_name
        if not parent.is_dir():
            continue
        for candidate in parent.iterdir():
            if not candidate.name.startswith(filename_prefix):
                continue
            relative = candidate.relative_to(source_root).as_posix()
            observed.append(relative)
            try:
                mode = candidate.lstat().st_mode
            except OSError:
                nonregular.append(relative)
                continue
            if not stat.S_ISREG(mode):
                nonregular.append(relative)
    observed_paths = tuple(sorted(observed))
    if observed_paths != REPOSITORY_EXPERIMENT_SOURCE_PATHS:
        missing = sorted(set(REPOSITORY_EXPERIMENT_SOURCE_PATHS) - set(observed_paths))
        unexpected = sorted(
            set(observed_paths) - set(REPOSITORY_EXPERIMENT_SOURCE_PATHS)
        )
        raise DistributionValidationError(
            "repository-experiment source inventory differs from the reviewed "
            f"22 paths: missing={missing}, unexpected={unexpected}"
        )
    if nonregular:
        raise DistributionValidationError(
            "repository-experiment source inventory contains non-regular paths: "
            f"{sorted(nonregular)}"
        )
    total_lines = 0
    try:
        for relative in observed_paths:
            with (source_root / relative).open("rb") as handle:
                total_lines += sum(1 for _line in handle)
    except OSError as error:
        raise DistributionValidationError(
            "cannot read the reviewed repository-experiment source inventory"
        ) from error
    return {
        "observation": "reviewed-exact-set-present",
        "count": len(observed_paths),
        "all_regular_files": True,
        "total_lines": total_lines,
        "paths": list(observed_paths),
    }


def _classify_source_python_members(
    source_root: Path,
    *,
    classification: dict[str, object],
) -> dict[str, object]:
    """Require every source ``.py`` member to have exactly one manifest role."""

    package_root = source_root / "src"
    try:
        if not stat.S_ISDIR((source_root / "src").lstat().st_mode):
            raise OSError("src is not an ordinary directory")
        if not stat.S_ISDIR((package_root / "spirallens").lstat().st_mode):
            raise OSError("src/spirallens is not an ordinary directory")
    except OSError as error:
        raise DistributionValidationError(
            "Python member source inventory has a missing or non-ordinary root"
        ) from error

    observed: list[str] = []
    nonregular: list[str] = []

    def raise_walk_error(error: OSError) -> None:
        raise DistributionValidationError(
            "cannot enumerate the Python member source inventory"
        ) from error

    try:
        for directory, directory_names, filenames in os.walk(
            package_root,
            followlinks=False,
            onerror=raise_walk_error,
        ):
            parent = Path(directory)
            retained_directories: list[str] = []
            for name in directory_names:
                child = parent / name
                relative = child.relative_to(source_root).as_posix()
                if stat.S_ISDIR(child.lstat().st_mode):
                    retained_directories.append(name)
                else:
                    nonregular.append(relative)
            directory_names[:] = retained_directories
            for name in filenames:
                child = parent / name
                if not name.endswith(".py"):
                    continue
                relative = child.relative_to(source_root).as_posix()
                observed.append(relative.removeprefix("src/"))
                if not stat.S_ISREG(child.lstat().st_mode):
                    nonregular.append(relative)
    except OSError as error:
        raise DistributionValidationError(
            "cannot inspect the Python member source inventory"
        ) from error
    if nonregular:
        raise DistributionValidationError(
            "Python member source inventory contains non-ordinary paths: "
            f"{sorted(nonregular)}"
        )
    expected_source_members = classification["source_members"]
    assert isinstance(expected_source_members, tuple)
    exact = _require_exact_python_members(
        observed,
        expected_members=expected_source_members,
        artifact_kind="source tree",
    )
    shipped_members = classification["shipped_members"]
    repository_only_members = classification["repository_only_members"]
    assert isinstance(shipped_members, tuple)
    assert isinstance(repository_only_members, tuple)
    exact.update(
        {
            "all_regular_files": True,
            "shipped_count": len(shipped_members),
            "shipped_manifest_sha256": _ordered_path_manifest_sha256(shipped_members),
            "repository_only_count": len(repository_only_members),
            "repository_only_manifest_sha256": _ordered_path_manifest_sha256(
                repository_only_members
            ),
        }
    )
    return exact


def _require_zero_repository_experiment_members(
    members: Sequence[str],
    *,
    artifact_kind: str,
) -> dict[str, object]:
    checked = tuple(members)
    if checked:
        raise DistributionValidationError(
            f"{artifact_kind} contains repository-experiment members: {list(checked)}"
        )
    return {
        "observation": "absent",
        "count": 0,
        "members": [],
    }


def _load_literal_all(path: Path) -> tuple[str, ...]:
    """Read one package's literal ordered ``__all__`` without importing it."""

    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as error:
        raise DistributionValidationError(
            f"cannot parse public package exports from {path}"
        ) from error
    assignments = [
        node
        for node in tree.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        and (
            (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name) and target.id == "__all__"
                    for target in node.targets
                )
            )
            or (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == "__all__"
            )
        )
    ]
    if len(assignments) != 1:
        raise DistributionValidationError(
            f"expected one literal __all__ assignment in {path}"
        )
    value_node = assignments[0].value
    try:
        value = ast.literal_eval(value_node)
    except (TypeError, ValueError) as error:
        raise DistributionValidationError(
            f"public package __all__ is not literal in {path}"
        ) from error
    if (
        not isinstance(value, (list, tuple))
        or not value
        or any(not isinstance(name, str) or not name for name in value)
        or len(set(value)) != len(value)
    ):
        raise DistributionValidationError(
            f"public package __all__ is not a non-empty ordered unique string set: {path}"
        )
    return tuple(value)


def _load_public_package_exports(source_root: Path) -> dict[str, tuple[str, ...]]:
    return {
        module: _load_literal_all(source_root / relative)
        for module, relative in _PUBLIC_PACKAGE_INIT_PATHS.items()
    }


def _library_separation_report(
    *,
    source_tree: dict[str, object],
    sdist: dict[str, object],
    direct_source_wheel: dict[str, object],
    sdist_derived_wheel: dict[str, object],
    python_module_inventory: dict[str, object],
) -> dict[str, object]:
    return {
        "repository_experiment_separation": {
            "source_tree": source_tree,
            "sdist": sdist,
            "direct_source_wheel": direct_source_wheel,
            "sdist_derived_wheel": sdist_derived_wheel,
            "source_prefixes": [
                f"{parent}/{prefix}"
                for parent, prefix in _REPOSITORY_EXPERIMENT_SOURCE_PREFIXES
            ],
            "wheel_prefixes": list(REPOSITORY_EXPERIMENT_WHEEL_MEMBER_PREFIXES),
        },
        "python_module_inventory": python_module_inventory,
        "closed_wheel_python_module_inventory_established": True,
        "closed_library_allowlist_established": False,
        "grants": {
            "authority": False,
            "lib_l0": False,
            "library": False,
            "portability": False,
            "public_api": False,
            "scientific": False,
        },
    }


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


_ATLAS_READER_PROBE = r"""
import importlib
import importlib.abc
import importlib.metadata
import json
from pathlib import Path
import sys

required_imports = json.loads(sys.argv[1])
forbidden_imports = tuple(json.loads(sys.argv[2]))
expected_public_exports = json.loads(sys.argv[3])


def matches(name, prefix):
    return name == prefix or name.startswith(prefix + ".")


preloaded_forbidden = sorted(
    prefix
    for prefix in forbidden_imports
    if any(matches(name, prefix) for name in sys.modules)
)
if preloaded_forbidden:
    raise RuntimeError(
        f"Atlas reader probe began with forbidden imports: {preloaded_forbidden}"
    )


class Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(matches(fullname, prefix) for prefix in forbidden_imports):
            raise ModuleNotFoundError(
                f"blocked Atlas capture dependency: {fullname}"
            )
        return None


blocker = Blocker()
sys.meta_path.insert(0, blocker)
module_origins = {}
for name in required_imports:
    module = importlib.import_module(name)
    origin = getattr(module, "__file__", None)
    if not isinstance(origin, str):
        raise RuntimeError(f"{name} has no concrete module origin")
    module_origins[name] = str(Path(origin).resolve())

atlas = importlib.import_module("spirallens.atlas")
store = importlib.import_module("spirallens.atlas.store")
receipt = importlib.import_module("spirallens.atlas.engineering_receipt")
reader_symbol_identities = (
    atlas.load_manifest is store.load_manifest
    and atlas.load_manifest_metadata is store.load_manifest_metadata
    and atlas.AtlasIntegrityError is store.AtlasIntegrityError
    and atlas.AtlasStateError is store.AtlasStateError
    and atlas.load_public_example_plumbing_receipt
    is receipt.load_public_example_plumbing_receipt
    and atlas.PublicExamplePlumbingReceiptError
    is receipt.PublicExamplePlumbingReceiptError
)
reader_symbol_modules = {
    "AtlasIntegrityError": atlas.AtlasIntegrityError.__module__,
    "AtlasStateError": atlas.AtlasStateError.__module__,
    "PublicExamplePlumbingReceiptError": (
        atlas.PublicExamplePlumbingReceiptError.__module__
    ),
    "load_manifest": atlas.load_manifest.__module__,
    "load_manifest_metadata": atlas.load_manifest_metadata.__module__,
    "load_public_example_plumbing_receipt": (
        atlas.load_public_example_plumbing_receipt.__module__
    ),
}
loaded_forbidden = sorted(
    prefix
    for prefix in forbidden_imports
    if any(matches(name, prefix) for name in sys.modules)
)

distribution = importlib.metadata.distribution("spirallens")
direct_url_text = distribution.read_text("direct_url.json")
direct_url = None if direct_url_text is None else json.loads(direct_url_text)
print(
    json.dumps(
        {
            "dependencies_loaded": sorted(
                name for name in ("numpy", "yaml") if name in sys.modules
            ),
            "dir_includes_public_exports": set(expected_public_exports).issubset(
                dir(atlas)
            ),
            "distribution_root": str(
                Path(distribution.locate_file("")).resolve()
            ),
            "direct_url": direct_url,
            "forbidden_imports_loaded": loaded_forbidden,
            "module_origins": module_origins,
            "package_version": distribution.version,
            "public_exports": list(atlas.__all__),
            "reader_symbol_identities": reader_symbol_identities,
            "reader_symbol_modules": reader_symbol_modules,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
)
"""


_REPOSITORY_EXPERIMENT_ABSENCE_PROBE = r"""
import importlib
import importlib.metadata
import json
from pathlib import Path
import sys

experiment_modules = json.loads(sys.argv[1])
expected_public_exports = json.loads(sys.argv[2])

module_origins = {}
observed_public_exports = {}
for name, expected in expected_public_exports.items():
    module = importlib.import_module(name)
    origin = getattr(module, "__file__", None)
    if not isinstance(origin, str):
        raise RuntimeError(f"{name} has no concrete module origin")
    module_origins[name] = str(Path(origin).resolve())
    observed = list(module.__all__)
    if observed != expected:
        raise RuntimeError(f"{name} ordered __all__ changed in installed wheel")
    observed_public_exports[name] = observed

absence_receipts = []
for name in experiment_modules:
    try:
        importlib.import_module(name)
    except ModuleNotFoundError as error:
        if error.name != name:
            raise RuntimeError(
                f"{name} failed through a transitive missing module: {error.name}"
            ) from error
        absence_receipts.append(
            {
                "exception_type": type(error).__name__,
                "module": name,
                "name": error.name,
            }
        )
    else:
        raise RuntimeError(f"repository-experiment module remained importable: {name}")

distribution = importlib.metadata.distribution("spirallens")
direct_url_text = distribution.read_text("direct_url.json")
direct_url = None if direct_url_text is None else json.loads(direct_url_text)
print(
    json.dumps(
        {
            "absence_receipts": absence_receipts,
            "distribution_root": str(
                Path(distribution.locate_file("")).resolve()
            ),
            "direct_url": direct_url,
            "module_origins": module_origins,
            "package_version": distribution.version,
            "public_exports": observed_public_exports,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
)
"""


_INSTALLED_PYTHON_MEMBER_PROBE = r"""
import importlib.metadata
import json
from pathlib import PurePosixPath

distribution = importlib.metadata.distribution("spirallens")
files = distribution.files
if files is None:
    raise RuntimeError("installed distribution omitted its file inventory")
members = []
for item in files:
    value = str(item)
    path = PurePosixPath(value)
    if path.parts[:1] != ("spirallens",) and (
        path.suffix != ".py"
        or any(part.endswith(".dist-info") for part in path.parts)
    ):
        continue
    members.append(value)
print(json.dumps({"package_members": sorted(members)}, separators=(",", ":")))
"""


_REPOSITORY_EXPERIMENT_SOURCE_IMPORT_PROBE = r"""
import importlib
import importlib.abc
import json
from pathlib import Path
import sys

source_root = Path(sys.argv[1]).resolve()
experiment_modules = json.loads(sys.argv[2])
forbidden_imports = tuple(json.loads(sys.argv[3]))


def matches(name, prefix):
    return name == prefix or name.startswith(prefix + ".")


class Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(matches(fullname, prefix) for prefix in forbidden_imports):
            raise ModuleNotFoundError(
                f"blocked model dependency in source import probe: {fullname}",
                name=fullname,
            )
        return None


sys.meta_path.insert(0, Blocker())
sys.path.insert(0, str(source_root / "src"))
module_origins = {}
for name in experiment_modules:
    module = importlib.import_module(name)
    origin = getattr(module, "__file__", None)
    if not isinstance(origin, str):
        raise RuntimeError(f"{name} has no concrete source origin")
    module_origins[name] = str(Path(origin).resolve())

loaded_forbidden = sorted(
    prefix
    for prefix in forbidden_imports
    if any(matches(name, prefix) for name in sys.modules)
)
print(
    json.dumps(
        {
            "forbidden_imports_loaded": loaded_forbidden,
            "module_origins": module_origins,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
)
"""


def _parse_repository_experiment_source_import_probe_output(
    output: str,
    *,
    source_root: Path,
) -> dict[str, object]:
    try:
        value = json.loads(output)
    except json.JSONDecodeError as error:
        raise DistributionValidationError(
            "repository-experiment source import probe did not emit valid JSON"
        ) from error
    if not isinstance(value, dict):
        raise DistributionValidationError(
            "repository-experiment source import probe must emit a JSON object"
        )
    if value.get("forbidden_imports_loaded") != []:
        raise DistributionValidationError(
            "repository-experiment source imports loaded model dependencies"
        )
    origins = value.get("module_origins")
    if not isinstance(origins, dict) or sorted(origins) != sorted(
        REPOSITORY_EXPERIMENT_MODULES
    ):
        raise DistributionValidationError(
            "repository-experiment source import probe returned incomplete origins"
        )
    source_root = source_root.resolve()
    checked_origins: dict[str, str] = {}
    for name, relative in zip(
        REPOSITORY_EXPERIMENT_MODULES,
        REPOSITORY_EXPERIMENT_SOURCE_PATHS,
        strict=True,
    ):
        origin_value = origins.get(name)
        if not isinstance(origin_value, str):
            raise DistributionValidationError(
                f"repository-experiment source import omitted origin for {name}"
            )
        origin = Path(origin_value).resolve()
        expected = (source_root / relative).resolve()
        if origin != expected:
            raise DistributionValidationError(
                f"{name} imported from {origin}, expected exact source path {expected}"
            )
        checked_origins[name] = relative
    return {
        "forbidden_model_imports_loaded": [],
        "imported_module_count": len(checked_origins),
        "module_origins": checked_origins,
    }


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


def _parse_repository_experiment_absence_probe_output(
    output: str,
    *,
    environment_root: Path,
    expected_modules: Sequence[str],
    expected_public_exports: dict[str, tuple[str, ...]],
) -> dict[str, object]:
    """Validate exact import absence and surviving package surfaces."""

    try:
        value = json.loads(output)
    except json.JSONDecodeError as error:
        raise DistributionValidationError(
            "repository-experiment absence probe did not emit valid JSON"
        ) from error
    if not isinstance(value, dict):
        raise DistributionValidationError(
            "repository-experiment absence probe output must be a JSON object"
        )

    environment_root = environment_root.resolve()
    origins = value.get("module_origins")
    expected_packages = list(expected_public_exports)
    if (
        not isinstance(origins, dict)
        or list(origins) != expected_packages
        or any(not isinstance(origin, str) for origin in origins.values())
    ):
        raise DistributionValidationError(
            "repository-experiment absence probe returned invalid package origins"
        )
    checked_origins: dict[str, str] = {}
    for name in expected_packages:
        origin = Path(origins[name]).resolve()
        if not origin.is_relative_to(environment_root):
            raise DistributionValidationError(
                f"{name} imported outside the fresh separated-wheel environment: "
                f"{origin}"
            )
        checked_origins[name] = origin.relative_to(environment_root).as_posix()

    distribution_root_value = value.get("distribution_root")
    if not isinstance(distribution_root_value, str):
        raise DistributionValidationError(
            "repository-experiment absence probe omitted distribution_root"
        )
    distribution_root = Path(distribution_root_value).resolve()
    if not distribution_root.is_relative_to(environment_root):
        raise DistributionValidationError(
            "SpiralLens distribution metadata resolved outside the fresh "
            f"separated-wheel environment: {distribution_root}"
        )

    direct_url = value.get("direct_url")
    if direct_url is not None and not isinstance(direct_url, dict):
        raise DistributionValidationError(
            "separated-wheel direct_url metadata is malformed"
        )
    if (
        isinstance(direct_url, dict)
        and isinstance(direct_url.get("dir_info"), dict)
        and direct_url["dir_info"].get("editable") is True
    ):
        raise DistributionValidationError(
            "fresh separated-wheel environment contains an editable install"
        )

    expected_receipts = [
        {
            "exception_type": "ModuleNotFoundError",
            "module": name,
            "name": name,
        }
        for name in expected_modules
    ]
    if value.get("absence_receipts") != expected_receipts:
        raise DistributionValidationError(
            "repository-experiment imports did not fail with exact requested "
            "ModuleNotFoundError.name receipts"
        )

    expected_exports_json = {
        name: list(exports) for name, exports in expected_public_exports.items()
    }
    if value.get("public_exports") != expected_exports_json:
        raise DistributionValidationError(
            "installed access/qualification ordered __all__ differs from source"
        )
    package_version = value.get("package_version")
    if not isinstance(package_version, str) or not package_version:
        raise DistributionValidationError(
            "repository-experiment absence probe omitted package version"
        )

    export_receipts = {
        name: {
            "count": len(exports),
            "ordered_sha256": hashlib.sha256(
                json.dumps(
                    list(exports),
                    ensure_ascii=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest(),
        }
        for name, exports in expected_public_exports.items()
    }
    return {
        "direct_url_editable": False,
        "distribution_root": distribution_root.relative_to(environment_root).as_posix(),
        "exact_module_not_found_receipt_count": len(expected_receipts),
        "module_origins": checked_origins,
        "package_version": package_version,
        "public_package_exports": export_receipts,
    }


def _parse_atlas_reader_probe_output(
    output: str,
    *,
    environment_root: Path,
    required_imports: Sequence[str],
) -> dict[str, object]:
    """Validate the installed-wheel Atlas reader import receipt."""

    try:
        value = json.loads(output)
    except json.JSONDecodeError as error:
        raise DistributionValidationError(
            "Atlas reader probe did not emit valid JSON"
        ) from error
    if not isinstance(value, dict):
        raise DistributionValidationError(
            "Atlas reader probe output must be a JSON object"
        )

    origins = value.get("module_origins")
    expected_imports = list(required_imports)
    if (
        not isinstance(origins, dict)
        or sorted(origins) != sorted(expected_imports)
        or any(not isinstance(item, str) for item in origins.values())
    ):
        raise DistributionValidationError(
            "Atlas reader probe returned incomplete module origins"
        )

    environment_root = environment_root.resolve()
    checked_origins: dict[str, str] = {}
    for name in expected_imports:
        origin = Path(origins[name]).resolve()
        if not origin.is_relative_to(environment_root):
            raise DistributionValidationError(
                f"{name} imported outside the fresh Atlas reader environment: {origin}"
            )
        checked_origins[name] = origin.relative_to(environment_root).as_posix()

    distribution_root_value = value.get("distribution_root")
    if not isinstance(distribution_root_value, str):
        raise DistributionValidationError(
            "Atlas reader probe omitted distribution_root"
        )
    distribution_root = Path(distribution_root_value).resolve()
    if not distribution_root.is_relative_to(environment_root):
        raise DistributionValidationError(
            "SpiralLens distribution metadata resolved outside the fresh "
            f"Atlas reader environment: {distribution_root}"
        )

    direct_url = value.get("direct_url")
    if direct_url is not None and not isinstance(direct_url, dict):
        raise DistributionValidationError(
            "installed-wheel Atlas reader direct_url metadata is malformed"
        )
    if (
        isinstance(direct_url, dict)
        and isinstance(direct_url.get("dir_info"), dict)
        and direct_url["dir_info"].get("editable") is True
    ):
        raise DistributionValidationError(
            "fresh Atlas reader environment contains an editable SpiralLens install"
        )

    forbidden = value.get("forbidden_imports_loaded")
    if forbidden != []:
        raise DistributionValidationError(
            f"Atlas reader imports loaded forbidden capture modules: {forbidden!r}"
        )
    if value.get("dependencies_loaded") != ["numpy", "yaml"]:
        raise DistributionValidationError(
            "Atlas reader probe did not load its declared NumPy/PyYAML dependencies"
        )
    if value.get("public_exports") != list(ATLAS_PUBLIC_EXPORTS):
        raise DistributionValidationError(
            "installed Atlas public export order differs from the frozen surface"
        )
    if value.get("dir_includes_public_exports") is not True:
        raise DistributionValidationError(
            "installed Atlas dir() omits frozen public exports"
        )
    if value.get("reader_symbol_identities") is not True:
        raise DistributionValidationError(
            "installed Atlas reader symbols do not preserve object identity"
        )
    if value.get("reader_symbol_modules") != ATLAS_READER_SYMBOL_MODULES:
        raise DistributionValidationError(
            "installed Atlas reader symbols changed defining modules"
        )

    package_version = value.get("package_version")
    if not isinstance(package_version, str) or not package_version:
        raise DistributionValidationError(
            "Atlas reader probe omitted the package version"
        )
    return {
        "dependencies_loaded": ["numpy", "yaml"],
        "direct_url_editable": False,
        "dir_includes_public_exports": True,
        "distribution_root": distribution_root.relative_to(environment_root).as_posix(),
        "forbidden_imports_loaded": [],
        "module_origins": checked_origins,
        "package_version": package_version,
        "public_exports": list(ATLAS_PUBLIC_EXPORTS),
        "reader_symbol_identities": True,
        "reader_symbol_modules": dict(ATLAS_READER_SYMBOL_MODULES),
    }


def _parse_installed_python_member_probe_output(
    output: str,
    *,
    expected_members: Sequence[str],
    artifact_kind: str,
) -> dict[str, object]:
    try:
        value = json.loads(output)
    except json.JSONDecodeError as error:
        raise DistributionValidationError(
            "installed Python member probe did not emit valid JSON"
        ) from error
    if not isinstance(value, dict) or set(value) != {"package_members"}:
        raise DistributionValidationError(
            "installed Python member probe has unexpected fields"
        )
    members = value["package_members"]
    if not isinstance(members, list) or any(
        not isinstance(member, str) for member in members
    ):
        raise DistributionValidationError(
            "installed Python member probe has invalid members"
        )
    if members != sorted(members) or len(members) != len(set(members)):
        raise DistributionValidationError(
            "installed Python member probe members must be sorted and unique"
        )
    for member in members:
        _require_safe_archive_member_path(member, artifact_kind=artifact_kind)
    non_python = sorted(member for member in members if not member.endswith(".py"))
    if non_python:
        raise DistributionValidationError(
            f"{artifact_kind} package subtree contains non-Python members: {non_python}"
        )
    return _require_exact_python_members(
        members,
        expected_members=expected_members,
        artifact_kind=artifact_kind,
    )


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
    atlas_reader_imports = tuple(ATLAS_READER_IMPORTS)
    python_member_classification = _load_python_member_classification(source_root)
    python_source_inventory = _classify_source_python_members(
        source_root,
        classification=python_member_classification,
    )
    shipped_python_members = python_member_classification["shipped_members"]
    assert isinstance(shipped_python_members, tuple)
    source_inventory = _repository_experiment_source_report(source_root)
    public_package_exports = _load_public_package_exports(source_root)
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
        direct_wheel_artifact_dir = temporary / "direct-wheel-artifacts"
        stale_wheel_artifact_dir = temporary / "stale-wheel-artifacts"
        wheel_artifact_dir = temporary / "wheel-artifacts"
        environment_root = temporary / "venv"
        direct_scientific_environment_root = temporary / "direct-scientific-venv"
        scientific_environment_root = temporary / "scientific-venv"
        neutral_cwd = temporary / "neutral"
        artifact_dir.mkdir()
        direct_wheel_artifact_dir.mkdir()
        stale_wheel_artifact_dir.mkdir()
        wheel_artifact_dir.mkdir()
        neutral_cwd.mkdir()
        _copy_source(source_root, staged_source)
        source_import_probe = _run(
            (
                sys.executable,
                "-P",
                "-c",
                _REPOSITORY_EXPERIMENT_SOURCE_IMPORT_PROBE,
                str(staged_source),
                json.dumps(REPOSITORY_EXPERIMENT_MODULES),
                json.dumps(("torch", "transformers", "huggingface_hub", "safetensors")),
            ),
            cwd=neutral_cwd,
            env=_clean_subprocess_environment(
                exclude_user_site=False,
                no_package_index=True,
            ),
        )
        source_import_inspection = (
            _parse_repository_experiment_source_import_probe_output(
                source_import_probe.stdout,
                source_root=staged_source,
            )
        )
        stale_build_rejection = _require_stale_build_rejected(
            staged_source,
            stale_wheel_artifact_dir,
        )

        _run(
            (
                sys.executable,
                "-m",
                "build",
                "--wheel",
                "--outdir",
                str(direct_wheel_artifact_dir),
            ),
            cwd=staged_source,
            env=_clean_subprocess_environment(
                exclude_user_site=False,
                no_package_index=False,
            ),
        )
        direct_wheel = _single_artifact(
            direct_wheel_artifact_dir,
            "*.whl",
            label="direct-source wheel",
        )
        direct_python_inventory = _classify_wheel_python_members(
            direct_wheel,
            expected_members=shipped_python_members,
        )
        direct_wheel_separation = _require_zero_repository_experiment_members(
            _classify_repository_experiment_members(direct_wheel),
            artifact_kind="direct-source wheel",
        )

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
        sdist_python_inventory = _classify_sdist_python_members(
            sdist,
            expected_members=shipped_python_members,
        )
        sdist_classification_manifest = _require_sdist_classification_manifest(
            sdist,
            expected_sha256=str(python_member_classification["manifest_sha256"]),
        )
        sdist_separation = _require_zero_repository_experiment_members(
            _classify_repository_experiment_sdist_members(sdist),
            artifact_kind="sdist",
        )
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
        sdist_wheel_python_inventory = _classify_wheel_python_members(
            wheel,
            expected_members=shipped_python_members,
        )
        if (
            direct_python_inventory["members"]
            != sdist_wheel_python_inventory["members"]
        ):
            raise DistributionValidationError(
                "direct-source and sdist-derived wheels differ in observed Python members"
            )
        sdist_wheel_separation = _require_zero_repository_experiment_members(
            _classify_repository_experiment_members(wheel),
            artifact_kind="sdist-derived wheel",
        )
        library_separation = _library_separation_report(
            source_tree=source_inventory,
            sdist=sdist_separation,
            direct_source_wheel=direct_wheel_separation,
            sdist_derived_wheel=sdist_wheel_separation,
            python_module_inventory={
                "classification": {
                    "claim_boundary": python_member_classification["claim_boundary"],
                    "classification_scope": python_member_classification[
                        "classification_scope"
                    ],
                    "manifest_path": python_member_classification["manifest_path"],
                    "manifest_sha256": python_member_classification["manifest_sha256"],
                    "sdist_manifest": sdist_classification_manifest,
                    "role_counts": {
                        role: len(members)
                        for role, members in python_member_classification[
                            "roles"
                        ].items()
                    },
                    "schema_version": python_member_classification["schema_version"],
                },
                "source_tree": python_source_inventory,
                "sdist": sdist_python_inventory,
                "direct_source_wheel": direct_python_inventory,
                "sdist_derived_wheel": sdist_wheel_python_inventory,
                "equality": {
                    "source_shipped_to_sdist": True,
                    "source_shipped_to_direct_source_wheel": True,
                    "source_shipped_to_sdist_derived_wheel": True,
                    "direct_source_to_sdist_derived_wheel": True,
                },
            },
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
                "--no-compile",
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
        installed_python_probe = _run(
            (
                str(venv_python),
                "-P",
                "-c",
                _INSTALLED_PYTHON_MEMBER_PROBE,
            ),
            cwd=neutral_cwd,
            env=environment,
        )
        installed_python_inventory = _parse_installed_python_member_probe_output(
            installed_python_probe.stdout,
            expected_members=shipped_python_members,
            artifact_kind="sdist-derived fresh install",
        )

        # Qualification is a scientific surface and intentionally imports its
        # declared numerical dependencies.  Two distinct fresh environments
        # use the host's already-installed system/user dependencies while
        # requiring SpiralLens itself to originate from each exact
        # non-editable wheel installation.
        venv.EnvBuilder(
            with_pip=True,
            system_site_packages=True,
            clear=False,
            symlinks=True,
        ).create(direct_scientific_environment_root)
        direct_scientific_environment = _clean_subprocess_environment(
            exclude_user_site=False
        )
        direct_scientific_python = _venv_executable(
            direct_scientific_environment_root,
            "python",
        )
        _run(
            (
                str(direct_scientific_python),
                "-m",
                "pip",
                "install",
                "--no-deps",
                "--no-compile",
                "--force-reinstall",
                str(direct_wheel),
            ),
            cwd=neutral_cwd,
            env=direct_scientific_environment,
        )
        direct_absence_probe = _run(
            (
                str(direct_scientific_python),
                "-P",
                "-c",
                _REPOSITORY_EXPERIMENT_ABSENCE_PROBE,
                json.dumps(REPOSITORY_EXPERIMENT_MODULES),
                json.dumps(public_package_exports),
            ),
            cwd=neutral_cwd,
            env=direct_scientific_environment,
        )
        direct_absence_inspection = _parse_repository_experiment_absence_probe_output(
            direct_absence_probe.stdout,
            environment_root=direct_scientific_environment_root,
            expected_modules=REPOSITORY_EXPERIMENT_MODULES,
            expected_public_exports=public_package_exports,
        )
        direct_installed_python_probe = _run(
            (
                str(direct_scientific_python),
                "-P",
                "-c",
                _INSTALLED_PYTHON_MEMBER_PROBE,
            ),
            cwd=neutral_cwd,
            env=direct_scientific_environment,
        )
        direct_installed_python_inventory = _parse_installed_python_member_probe_output(
            direct_installed_python_probe.stdout,
            expected_members=shipped_python_members,
            artifact_kind="direct-source fresh install",
        )

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
                "--no-compile",
                "--force-reinstall",
                str(wheel),
            ),
            cwd=neutral_cwd,
            env=scientific_environment,
        )
        sdist_absence_probe = _run(
            (
                str(scientific_python),
                "-P",
                "-c",
                _REPOSITORY_EXPERIMENT_ABSENCE_PROBE,
                json.dumps(REPOSITORY_EXPERIMENT_MODULES),
                json.dumps(public_package_exports),
            ),
            cwd=neutral_cwd,
            env=scientific_environment,
        )
        sdist_absence_inspection = _parse_repository_experiment_absence_probe_output(
            sdist_absence_probe.stdout,
            environment_root=scientific_environment_root,
            expected_modules=REPOSITORY_EXPERIMENT_MODULES,
            expected_public_exports=public_package_exports,
        )
        if (
            installed_python_inventory["members"]
            != (sdist_wheel_python_inventory["members"])
        ):
            raise DistributionValidationError(
                "sdist-derived wheel and fresh install differ in Python members"
            )
        if (
            direct_installed_python_inventory["members"]
            != (direct_python_inventory["members"])
        ):
            raise DistributionValidationError(
                "direct-source wheel and fresh install differ in Python members"
            )
        python_inventory_report = library_separation["python_module_inventory"]
        assert isinstance(python_inventory_report, dict)
        python_inventory_report["direct_source_install"] = (
            direct_installed_python_inventory
        )
        python_inventory_report["sdist_derived_install"] = installed_python_inventory
        equality_report = python_inventory_report["equality"]
        assert isinstance(equality_report, dict)
        equality_report.update(
            {
                "direct_source_wheel_to_install": True,
                "sdist_derived_wheel_to_install": True,
            }
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
        atlas_reader_probe = _run(
            (
                str(scientific_python),
                "-P",
                "-c",
                _ATLAS_READER_PROBE,
                json.dumps(atlas_reader_imports),
                json.dumps(ATLAS_READER_FORBIDDEN_IMPORTS),
                json.dumps(ATLAS_PUBLIC_EXPORTS),
            ),
            cwd=neutral_cwd,
            env=scientific_environment,
        )
        atlas_reader_inspection = _parse_atlas_reader_probe_output(
            atlas_reader_probe.stdout,
            environment_root=scientific_environment_root,
            required_imports=atlas_reader_imports,
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
                    "filename": direct_wheel.name,
                    "kind": "direct-source-wheel",
                    "sha256": _sha256_file(direct_wheel),
                    "size_bytes": direct_wheel.stat().st_size,
                },
                {
                    "filename": wheel.name,
                    "kind": "sdist-derived-wheel",
                    "sha256": _sha256_file(wheel),
                    "size_bytes": wheel.stat().st_size,
                },
            ],
            "build": {
                "frontend": "python-build",
                "isolation": True,
                "source_copy": True,
                "direct_source_wheel_built": True,
                "stale_build_outputs_fail_closed": True,
                "wheel_built_from_sdist": True,
            },
            "installation": {
                "atlas_reader_system_site_packages": True,
                "atlas_reader_user_site_packages": True,
                "no_dependencies": True,
                "system_site_packages": False,
                "direct_source_wheel_filename": direct_wheel.name,
                "repository_experiment_fresh_environment_count": 2,
                "scientific_surface_system_site_packages": True,
                "scientific_surface_user_site_packages": True,
                "wheel_filename": wheel.name,
            },
            "atlas_reader_inspection": atlas_reader_inspection,
            "atlas_reader_forbidden_imports": list(ATLAS_READER_FORBIDDEN_IMPORTS),
            "inspection": inspection,
            "library_separation": library_separation,
            "repository_experiment_source_import_inspection": (
                source_import_inspection
            ),
            "repository_experiment_stale_build_rejection": stale_build_rejection,
            "repository_experiment_install_inspections": {
                "direct_source_wheel": direct_absence_inspection,
                "sdist_derived_wheel": sdist_absence_inspection,
            },
            "scientific_surface_inspection": scientific_inspection,
            "required_wheel_members": list(shipped_python_members),
            "forbidden_imports": list(FORBIDDEN_IMPORTS),
            "required_imports": list(imports),
            "required_atlas_reader_imports": list(atlas_reader_imports),
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
