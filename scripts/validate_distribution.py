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
import base64
import concurrent.futures
import hashlib
import json
import os
import runpy
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import venv
import zipfile
from collections.abc import Sequence
from pathlib import Path, PurePosixPath

# `packaging` is provided to this parent validator by the declared dev/build
# toolchain (`build>=1.2.2` requires packaging); it is never imported by the
# isolated `-I -S` installed-module workers or treated as a runtime dependency.
from packaging.markers import Marker
from packaging.requirements import InvalidRequirement, Requirement

REPORT_SCHEMA_VERSION = "spirallens.distribution-validation.v0.10"
QUALIFICATION_STATE_CONFORMANCE_SCHEMA_VERSION = (
    "spirallens.qualification-state-conformance.v0.1"
)
QUALIFICATION_STATE_ORDER = ("pass", "fail", "insufficient", "not_run")
QUALIFICATION_STATE_CANONICAL_SHA256 = {
    "pass": "5c231df1519e2d5021f14f548142d49152a6a8f8fd47e00394b52bd110363760",
    "fail": "47b5b365a17dbab28f9f29dba249b423e42a89f209a594dcb37cde1cb00e6608",
    "insufficient": (
        "6467ca69869fbcf999e627beb0928cda1a9103307deab41ce8891d45b6544d34"
    ),
    "not_run": ("59916db9d25b90aa1fc15743abb2c104ce1e45bc559a901e37585ccc04f68600"),
}
QUALIFICATION_STATE_MODULE_ORIGINS = {
    "spirallens": "spirallens/__init__.py",
    "spirallens.core": "spirallens/core/__init__.py",
    "spirallens.core.canonical": "spirallens/core/canonical.py",
    "spirallens.qualification": "spirallens/qualification/__init__.py",
    "spirallens.qualification.common": "spirallens/qualification/common.py",
    "spirallens.qualification.contracts": ("spirallens/qualification/contracts.py"),
}
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
ORDERED_EXPORT_CLASSIFICATION_PATH = "distribution/spirallens_ordered_exports_v0_1.json"
ORDERED_EXPORT_CLASSIFICATION_SCHEMA_VERSION = "spirallens.ordered-package-exports.v0.1"
ORDERED_EXPORT_CLASSIFICATION_SCOPE = (
    "literal ordered __all__ values for every classified package initializer"
)
ORDERED_EXPORT_CLASSIFICATION_CLAIM_BOUNDARY = (
    "classification grants no public API, stability, compatibility, authority, "
    "scientific claim, or library maturity"
)
INSTALLED_IMPORT_CLASSIFICATION_PATH = (
    "distribution/spirallens_installed_imports_v0_1.json"
)
_POLICY_PATH = (
    Path(__file__).resolve().parents[1] / "distribution/_installed_import_policy.py"
)
try:
    _POLICY_STAT = _POLICY_PATH.lstat()
    if not stat.S_ISREG(_POLICY_STAT.st_mode) or _POLICY_STAT.st_size > 1024 * 1024:
        raise OSError
    _POLICY_BYTES = _POLICY_PATH.read_bytes()
    _POLICY = runpy.run_path(str(_POLICY_PATH))
except (OSError, SyntaxError) as error:
    raise RuntimeError("cannot load installed import policy") from error

INSTALLED_IMPORT_BASE_DEPENDENCIES = tuple(_POLICY["dependency_records"]())
INSTALLED_IMPORT_CLASSIFICATION_SCHEMA_VERSION = _POLICY["SCHEMA"]
_INSTALLED_IMPORT_WORKER_POLICY = json.dumps(
    _POLICY["worker_policy_projection"](), sort_keys=True, separators=(",", ":")
)
INSTALLED_IMPORT_PROJECT_OPTIONAL_DEPENDENCIES = (
    ("ann", ("faiss-cpu==1.14.3",)),
    ("dev", ("build>=1.2.2", "cryptography>=42", "pytest>=8", "ruff>=0.9")),
    (
        "models",
        (
            "huggingface-hub>=0.34",
            "torch>=2.2",
            "transformers>=4.40",
            "safetensors>=0.4",
        ),
    ),
    ("witness", ("cryptography>=42",)),
)
INSTALLED_IMPORT_BLOCKED_OPTIONAL_PREFIXES = _POLICY["BLOCKED"]
INSTALLED_IMPORT_SUCCESS_COUNT = 131
INSTALLED_IMPORT_MISSING_TORCH_COUNT = 2
INSTALLED_IMPORT_SUCCESSFUL_INITIALIZER_COUNT = 23
INSTALLED_IMPORT_SUCCESSFUL_RUNTIME_EXPORT_COUNT = 554
INSTALLED_IMPORT_UNAVAILABLE_RUNTIME_EXPORT_COUNT = 5
INSTALLED_IMPORT_PROBE_TIMEOUT_SECONDS = 30
INSTALLED_IMPORT_PROBE_CONCURRENCY = 8
INSTALLED_IMPORT_DENIED_AUDIT_EVENTS = _POLICY["DENIED_AUDIT_EVENTS"]
_MAX_CLASSIFICATION_BYTES = 1024 * 1024
_MAX_INITIALIZER_BYTES = 1024 * 1024
ORDERED_EXPORT_PACKAGE_COUNT = 24
ORDERED_EXPORT_NAME_COUNT = 559
DEFAULT_IMPORTS = (
    "spirallens",
    "spirallens._held_file",
    "spirallens.core",
    "spirallens.core.canonical",
    "spirallens.access",
)
DEFAULT_SCIENTIFIC_IMPORTS = (
    "spirallens.qualification",
    "spirallens.qualification.advancement",
    "spirallens.qualification.aggregation",
    "spirallens.qualification.blind",
    "spirallens.qualification.common",
    "spirallens.qualification.contracts",
    "spirallens.qualification.crossed",
    "spirallens.qualification.evidence_bundle",
    "spirallens.qualification.freeze",
    "spirallens.qualification.launch",
    "spirallens.qualification.metamorphic",
    "spirallens.qualification.persistence",
    "spirallens.qualification.pipeline_metamorphic",
    "spirallens.qualification.preparation",
    "spirallens.qualification.prerequisites",
    "spirallens.qualification.protocol",
    "spirallens.qualification.runner",
    "spirallens.qualification.source_binding",
    "spirallens.qualification.winding",
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
    "spirallens/qualification/confirmation_",
)
REPOSITORY_EXPERIMENT_SOURCE_PATHS = (
    "src/spirallens/access/_pythia160_identity_acquisition.py",
    "src/spirallens/access/_pythia160_preobservation.py",
    "src/spirallens/qualification/confirmation_attempt_authority.py",
    "src/spirallens/qualification/confirmation_attempt_evidence.py",
    "src/spirallens/qualification/confirmation_attempt_evidence_validation.py",
    "src/spirallens/qualification/confirmation_attempt_persistence.py",
    "src/spirallens/qualification/confirmation_attempt_records.py",
    "src/spirallens/qualification/confirmation_attempt_terminal_persistence.py",
    "src/spirallens/qualification/confirmation_attempt_validation.py",
    "src/spirallens/qualification/confirmation_authoritative_start_persistence.py",
    "src/spirallens/qualification/confirmation_c1.py",
    "src/spirallens/qualification/confirmation_crossed_development.py",
    "src/spirallens/qualification/confirmation_execution_design.py",
    "src/spirallens/qualification/confirmation_execution_kernel.py",
    "src/spirallens/qualification/confirmation_external_witness.py",
    "src/spirallens/qualification/confirmation_fused_authority.py",
    "src/spirallens/qualification/confirmation_fused_start.py",
    "src/spirallens/qualification/confirmation_official_execution.py",
    "src/spirallens/qualification/confirmation_preseed_authority.py",
    "src/spirallens/qualification/confirmation_protocol.py",
    "src/spirallens/qualification/confirmation_rebinding.py",
    "src/spirallens/qualification/confirmation_replay_contracts.py",
    "src/spirallens/qualification/confirmation_result_component_validation.py",
    "src/spirallens/qualification/confirmation_result_components.py",
    "src/spirallens/qualification/confirmation_runner.py",
    "src/spirallens/qualification/confirmation_runtime_observation.py",
    "src/spirallens/qualification/confirmation_seed_supply_contracts.py",
    "src/spirallens/qualification/confirmation_source_closure.py",
    "src/spirallens/qualification/confirmation_terminal_operations.py",
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
    ("src/spirallens/qualification", "confirmation_"),
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


def _python_member_module(member: str) -> str:
    """Map one already-validated package member to its dotted module name."""

    path = PurePosixPath(member)
    if path.name == "__init__.py":
        parts = path.parts[:-1]
    else:
        parts = (*path.parts[:-1], path.stem)
    return ".".join(parts)


def _normalize_project_requires_dist(
    project: dict[str, object],
) -> tuple[dict[str, str | None], ...]:
    """Convert strict PEP 621 base/extra declarations to an exact contract."""

    dependencies = project.get("dependencies")
    optional_dependencies = project.get("optional-dependencies")
    expected_optional_dependencies = dict(
        INSTALLED_IMPORT_PROJECT_OPTIONAL_DEPENDENCIES
    )
    if (
        not isinstance(dependencies, list)
        or any(not isinstance(item, str) for item in dependencies)
        or len(dependencies) != len(set(dependencies))
        or set(dependencies) != set(_POLICY["PROJECT_DEPENDENCIES"])
        or not isinstance(optional_dependencies, dict)
        or set(optional_dependencies) != set(expected_optional_dependencies)
    ):
        raise DistributionValidationError(
            "project dependencies differ from the exact reviewed structure"
        )

    records: list[dict[str, str | None]] = []

    def add(requirement_text: str, *, extra: str | None) -> None:
        try:
            requirement = Requirement(requirement_text)
        except InvalidRequirement as error:
            raise DistributionValidationError(
                "project contains an invalid dependency requirement"
            ) from error
        if (
            requirement.marker is not None
            or requirement.url is not None
            or requirement.extras
            or not str(requirement.specifier)
        ):
            raise DistributionValidationError(
                "project dependency entries must be marker-free named requirements "
                "with exact version specifiers"
            )
        records.append(
            {
                "extra": extra,
                "name": requirement.name,
                "specifier": str(requirement.specifier),
            }
        )

    for requirement_text in dependencies:
        add(requirement_text, extra=None)
    for extra, requirements in optional_dependencies.items():
        if (
            not isinstance(extra, str)
            or not extra
            or extra.casefold() != extra
            or any(
                not (character.isascii() and (character.isalnum() or character == "-"))
                for character in extra
            )
            or not isinstance(requirements, list)
            or not requirements
            or any(not isinstance(item, str) for item in requirements)
            or len(requirements) != len(set(requirements))
            or set(requirements) != set(expected_optional_dependencies[extra])
        ):
            raise DistributionValidationError(
                "project optional dependencies have an invalid extra declaration"
            )
        for requirement_text in requirements:
            add(requirement_text, extra=extra)
    ordered = tuple(
        sorted(
            records,
            key=lambda record: (
                record["extra"] or "",
                record["name"] or "",
                record["specifier"] or "",
            ),
        )
    )
    if len(ordered) != len({json.dumps(record, sort_keys=True) for record in ordered}):
        raise DistributionValidationError(
            "project contains a duplicate dependency within one marker association"
        )
    return ordered


def _normalize_installed_requires_dist(
    raw_requirements: object,
    *,
    expected: tuple[dict[str, str | None], ...],
    label: str,
) -> tuple[dict[str, str | None], ...]:
    """Parse every installed Requires-Dist and require the exact PEP 621 contract."""

    if (
        not isinstance(raw_requirements, list)
        or len(raw_requirements) > 1024
        or any(
            not isinstance(item, str) or not item or len(item) > 4096
            for item in raw_requirements
        )
    ):
        raise DistributionValidationError(f"{label} has invalid Requires-Dist data")
    allowed_extras = {
        record["extra"] for record in expected if record["extra"] is not None
    }
    marker_to_extra = {
        str(Marker(f'extra == "{extra}"')): extra for extra in allowed_extras
    }
    records: list[dict[str, str | None]] = []
    for raw_requirement in raw_requirements:
        try:
            requirement = Requirement(raw_requirement)
        except InvalidRequirement as error:
            raise DistributionValidationError(
                f"{label} contains an invalid Requires-Dist requirement"
            ) from error
        if requirement.url is not None or requirement.extras:
            raise DistributionValidationError(
                f"{label} Requires-Dist contains an unsupported URL or requirement extra"
            )
        marker = None if requirement.marker is None else str(requirement.marker)
        if marker is None:
            extra = None
        else:
            extra = marker_to_extra.get(marker)
            if extra is None:
                raise DistributionValidationError(
                    f"{label} Requires-Dist contains a non-exact extra marker"
                )
        records.append(
            {
                "extra": extra,
                "name": requirement.name,
                "specifier": str(requirement.specifier),
            }
        )
    ordered = tuple(
        sorted(
            records,
            key=lambda record: (
                record["extra"] or "",
                record["name"] or "",
                record["specifier"] or "",
            ),
        )
    )
    if len(ordered) != len({json.dumps(record, sort_keys=True) for record in ordered}):
        raise DistributionValidationError(
            f"{label} has duplicate Requires-Dist entries"
        )
    if ordered != expected:
        raise DistributionValidationError(
            f"{label} full Requires-Dist set differs from pyproject dependencies"
        )
    return ordered


def _normalize_installed_import_explicit_roots(
    roots: Sequence[str],
    *,
    environment_root: Path,
) -> list[str]:
    """Normalize only the fresh-environment root; retain exact host roots."""

    resolved_environment = environment_root.resolve()
    normalized = []
    for root_value in roots:
        root = Path(root_value).resolve()
        if root.is_relative_to(resolved_environment):
            normalized.append(
                f"fresh-environment/{root.relative_to(resolved_environment).as_posix()}"
            )
        else:
            normalized.append(str(root))
    return normalized


def _load_installed_import_classification(
    source_root: Path,
    *,
    python_member_classification: dict[str, object],
    ordered_export_classification: dict[str, object],
) -> dict[str, object]:
    """Load the independent literal installed-import outcome inventory."""

    manifest_path = source_root / INSTALLED_IMPORT_CLASSIFICATION_PATH
    try:
        distribution_mode = (source_root / "distribution").lstat().st_mode
        manifest_mode = manifest_path.lstat().st_mode
        manifest_bytes = manifest_path.read_bytes()
    except OSError as error:
        raise DistributionValidationError(
            "cannot read the installed import classification manifest"
        ) from error
    if not stat.S_ISDIR(distribution_mode) or not stat.S_ISREG(manifest_mode):
        raise DistributionValidationError(
            "installed import classification path must be an ordinary file"
        )
    if len(manifest_bytes) > _MAX_CLASSIFICATION_BYTES:
        raise DistributionValidationError(
            "installed import classification manifest exceeds its size bound"
        )
    try:
        value = json.loads(
            manifest_bytes.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_json_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise DistributionValidationError(
            "installed import classification manifest is not duplicate-free JSON"
        ) from error
    if not isinstance(value, dict) or set(value) != {
        "schema_version",
        "classification_scope",
        "claim_boundary",
        "base_dependencies",
        "blocked_optional_prefixes",
        "outcomes",
    }:
        raise DistributionValidationError(
            "installed import classification manifest has unexpected top-level keys"
        )
    if value.get("schema_version") != _POLICY["SCHEMA"]:
        raise DistributionValidationError(
            "installed import classification manifest has the wrong schema version"
        )
    if value.get("classification_scope") != _POLICY["SCOPE"]:
        raise DistributionValidationError(
            "installed import classification manifest has the wrong scope"
        )
    if value.get("claim_boundary") != _POLICY["CLAIM"]:
        raise DistributionValidationError(
            "installed import classification manifest has the wrong claim boundary"
        )
    if value.get("base_dependencies") != list(INSTALLED_IMPORT_BASE_DEPENDENCIES):
        raise DistributionValidationError(
            "installed import classification base dependencies differ"
        )
    pyproject_path = source_root / "pyproject.toml"
    try:
        pyproject_mode = pyproject_path.lstat().st_mode
        pyproject_bytes = pyproject_path.read_bytes()
    except OSError as error:
        raise DistributionValidationError(
            "cannot read project dependencies for installed import classification"
        ) from error
    if (
        not stat.S_ISREG(pyproject_mode)
        or len(pyproject_bytes) > _MAX_CLASSIFICATION_BYTES
    ):
        raise DistributionValidationError(
            "project metadata must be an ordinary file within its size bound"
        )
    try:
        pyproject = tomllib.loads(pyproject_bytes.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise DistributionValidationError(
            "cannot parse project dependencies for installed import classification"
        ) from error
    project = pyproject.get("project") if isinstance(pyproject, dict) else None
    if not isinstance(project, dict):
        raise DistributionValidationError("project metadata has no project table")
    requires_dist_contract = _normalize_project_requires_dist(project)
    manifest_requirements = {
        dependency["requirement"] for dependency in INSTALLED_IMPORT_BASE_DEPENDENCIES
    }
    if manifest_requirements != set(_POLICY["PROJECT_DEPENDENCIES"]):
        raise DistributionValidationError(
            "installed import manifest dependencies do not map to project dependencies"
        )
    if value.get("blocked_optional_prefixes") != list(
        INSTALLED_IMPORT_BLOCKED_OPTIONAL_PREFIXES
    ):
        raise DistributionValidationError(
            "installed import classification optional prefixes differ"
        )
    outcomes = value.get("outcomes")
    if not isinstance(outcomes, dict) or set(outcomes) != {
        "base_import_success",
        "models_extra_missing_torch",
    }:
        raise DistributionValidationError(
            "installed import classification has unexpected outcome roles"
        )
    parsed_outcomes: dict[str, tuple[str, ...]] = {}
    for role in ("base_import_success", "models_extra_missing_torch"):
        raw_modules = outcomes.get(role)
        if not isinstance(raw_modules, list) or any(
            not isinstance(module, str)
            or not module
            or any(
                not part.isascii() or not part.isidentifier()
                for part in module.split(".")
            )
            for module in raw_modules
        ):
            raise DistributionValidationError(
                f"installed import outcome {role!r} contains an invalid module"
            )
        modules = tuple(raw_modules)
        if modules != tuple(sorted(set(modules))):
            raise DistributionValidationError(
                f"installed import outcome {role!r} must be sorted and unique"
            )
        parsed_outcomes[role] = modules
    success = parsed_outcomes["base_import_success"]
    missing_torch = parsed_outcomes["models_extra_missing_torch"]
    if set(success).intersection(missing_torch):
        raise DistributionValidationError(
            "installed import classification outcome roles overlap"
        )
    shipped_members = python_member_classification.get("shipped_members")
    if not isinstance(shipped_members, tuple):
        raise DistributionValidationError(
            "Python member classification shipped members are unavailable"
        )
    expected_modules = tuple(
        sorted(_python_member_module(member) for member in shipped_members)
    )
    if tuple(sorted((*success, *missing_torch))) != expected_modules:
        raise DistributionValidationError(
            "installed import outcomes do not close the exact shipped module set"
        )
    if (
        len(success) != INSTALLED_IMPORT_SUCCESS_COUNT
        or missing_torch != _POLICY["MISSING_TORCH"]
        or len(missing_torch) != INSTALLED_IMPORT_MISSING_TORCH_COUNT
    ):
        raise DistributionValidationError(
            "installed import outcomes differ from the exact 131/2 inventory"
        )
    packages = ordered_export_classification.get("packages")
    if not isinstance(packages, tuple):
        raise DistributionValidationError(
            "ordered package export classification is unavailable"
        )
    package_modules = tuple(str(package["module"]) for package in packages)
    successful_packages = tuple(
        module for module in package_modules if module in set(success)
    )
    unavailable_packages = tuple(
        module for module in package_modules if module in set(missing_torch)
    )
    successful_runtime_exports = sum(
        len(package["exports"])
        for package in packages
        if package["module"] in set(successful_packages)
    )
    unavailable_runtime_exports = sum(
        len(package["exports"])
        for package in packages
        if package["module"] in set(unavailable_packages)
    )
    if (
        len(successful_packages) != INSTALLED_IMPORT_SUCCESSFUL_INITIALIZER_COUNT
        or successful_runtime_exports
        != INSTALLED_IMPORT_SUCCESSFUL_RUNTIME_EXPORT_COUNT
        or unavailable_packages != ("spirallens.adapters",)
        or unavailable_runtime_exports
        != INSTALLED_IMPORT_UNAVAILABLE_RUNTIME_EXPORT_COUNT
    ):
        raise DistributionValidationError(
            "installed import outcomes differ from the exact initializer/export "
            "projection"
        )
    return {
        "base_dependencies": tuple(INSTALLED_IMPORT_BASE_DEPENDENCIES),
        "blocked_optional_prefixes": INSTALLED_IMPORT_BLOCKED_OPTIONAL_PREFIXES,
        "claim_boundary": value["claim_boundary"],
        "classification_scope": value["classification_scope"],
        "manifest_bytes": manifest_bytes,
        "manifest_path": INSTALLED_IMPORT_CLASSIFICATION_PATH,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "outcomes": parsed_outcomes,
        "python_members": python_member_classification,
        "requires_dist_contract": requires_dist_contract,
        "schema_version": _POLICY["SCHEMA"],
        "successful_package_modules": successful_packages,
        "successful_runtime_export_count": successful_runtime_exports,
        "unavailable_package_modules": unavailable_packages,
        "unavailable_runtime_export_count": unavailable_runtime_exports,
    }


def _module_for_initializer(initializer: str) -> str:
    path = PurePosixPath(initializer)
    if (
        path.is_absolute()
        or path.as_posix() != initializer
        or len(path.parts) < 2
        or path.parts[0] != "spirallens"
        or path.name != "__init__.py"
        or any(
            not part.isascii() or not part.isidentifier() for part in path.parts[:-1]
        )
    ):
        raise DistributionValidationError(
            f"ordered export classification contains an invalid initializer: "
            f"{initializer!r}"
        )
    return ".".join(path.parts[:-1])


def _load_ordered_export_classification(
    source_root: Path,
    *,
    python_member_classification: dict[str, object],
) -> dict[str, object]:
    """Load the independent literal ordered-package-export classification."""

    manifest_path = source_root / ORDERED_EXPORT_CLASSIFICATION_PATH
    try:
        distribution_mode = (source_root / "distribution").lstat().st_mode
        manifest_mode = manifest_path.lstat().st_mode
        manifest_bytes = manifest_path.read_bytes()
    except OSError as error:
        raise DistributionValidationError(
            "cannot read the ordered export classification manifest"
        ) from error
    if not stat.S_ISDIR(distribution_mode) or not stat.S_ISREG(manifest_mode):
        raise DistributionValidationError(
            "ordered export classification path must be an ordinary file"
        )
    if len(manifest_bytes) > _MAX_CLASSIFICATION_BYTES:
        raise DistributionValidationError(
            "ordered export classification manifest exceeds its size bound"
        )
    try:
        value = json.loads(
            manifest_bytes.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_json_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise DistributionValidationError(
            "ordered export classification manifest is not duplicate-free JSON"
        ) from error
    if not isinstance(value, dict) or set(value) != {
        "schema_version",
        "classification_scope",
        "claim_boundary",
        "packages",
    }:
        raise DistributionValidationError(
            "ordered export classification manifest has unexpected top-level keys"
        )
    if value.get("schema_version") != ORDERED_EXPORT_CLASSIFICATION_SCHEMA_VERSION:
        raise DistributionValidationError(
            "ordered export classification manifest has the wrong schema version"
        )
    if value.get("classification_scope") != ORDERED_EXPORT_CLASSIFICATION_SCOPE:
        raise DistributionValidationError(
            "ordered export classification manifest has the wrong scope"
        )
    if value.get("claim_boundary") != ORDERED_EXPORT_CLASSIFICATION_CLAIM_BOUNDARY:
        raise DistributionValidationError(
            "ordered export classification manifest has the wrong claim boundary"
        )
    raw_packages = value.get("packages")
    if not isinstance(raw_packages, list) or not raw_packages:
        raise DistributionValidationError(
            "ordered export classification packages must be a non-empty list"
        )
    packages: list[dict[str, object]] = []
    for raw_package in raw_packages:
        if not isinstance(raw_package, dict) or set(raw_package) != {
            "module",
            "initializer",
            "exports",
        }:
            raise DistributionValidationError(
                "ordered export classification package has unexpected fields"
            )
        module = raw_package.get("module")
        initializer = raw_package.get("initializer")
        raw_exports = raw_package.get("exports")
        if not isinstance(module, str) or not isinstance(initializer, str):
            raise DistributionValidationError(
                "ordered export classification package coordinates must be strings"
            )
        if _module_for_initializer(initializer) != module:
            raise DistributionValidationError(
                "ordered export classification module/initializer topology differs"
            )
        if (
            not isinstance(raw_exports, list)
            or not raw_exports
            or any(
                not isinstance(name, str)
                or not name
                or not name.isascii()
                or not name.isidentifier()
                for name in raw_exports
            )
            or len(raw_exports) != len(set(raw_exports))
        ):
            raise DistributionValidationError(
                "ordered export classification exports must be non-empty ordered "
                "unique ASCII identifiers"
            )
        packages.append(
            {
                "module": module,
                "initializer": initializer,
                "exports": tuple(raw_exports),
            }
        )
    modules = tuple(str(package["module"]) for package in packages)
    initializers = tuple(str(package["initializer"]) for package in packages)
    if modules != tuple(sorted(set(modules))):
        raise DistributionValidationError(
            "ordered export classification packages must be sorted and unique"
        )
    if len(initializers) != len(set(initializers)):
        raise DistributionValidationError(
            "ordered export classification initializer paths must be unique"
        )
    roles = python_member_classification.get("roles")
    if not isinstance(roles, dict):
        raise DistributionValidationError(
            "Python member classification roles are unavailable"
        )
    package_initializers = roles.get("package_initializer")
    if not isinstance(package_initializers, tuple):
        raise DistributionValidationError(
            "Python member initializer classification is unavailable"
        )
    if set(initializers) != set(package_initializers):
        raise DistributionValidationError(
            "ordered export classification does not close the exact package "
            "initializer topology"
        )
    export_count = sum(len(package["exports"]) for package in packages)
    if (
        len(packages) != ORDERED_EXPORT_PACKAGE_COUNT
        or export_count != ORDERED_EXPORT_NAME_COUNT
    ):
        raise DistributionValidationError(
            "ordered export classification differs from the exact 24-package/559-name "
            "inventory"
        )
    return {
        "classification_scope": value["classification_scope"],
        "claim_boundary": value["claim_boundary"],
        "export_count": export_count,
        "initializers": initializers,
        "manifest_bytes": manifest_bytes,
        "manifest_path": ORDERED_EXPORT_CLASSIFICATION_PATH,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "package_count": len(packages),
        "packages": tuple(packages),
        "schema_version": ORDERED_EXPORT_CLASSIFICATION_SCHEMA_VERSION,
    }


def _load_literal_ordered_exports(source: bytes, *, label: str) -> tuple[str, ...]:
    """Statically read one and only one literal top-level ``__all__``."""

    if len(source) > _MAX_INITIALIZER_BYTES:
        raise DistributionValidationError(f"{label} exceeds its initializer size bound")
    try:
        text = source.decode("utf-8", errors="strict")
        tree = ast.parse(text, filename=label)
    except (UnicodeDecodeError, SyntaxError) as error:
        raise DistributionValidationError(
            f"cannot parse ordered package exports from {label}"
        ) from error
    stored_names = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
        and node.id == "__all__"
        and isinstance(node.ctx, (ast.Store, ast.Del))
    ]

    def rooted_in_all(node: ast.expr) -> bool:
        while isinstance(node, (ast.Attribute, ast.Subscript)):
            node = node.value
        return isinstance(node, ast.Name) and node.id == "__all__"

    mutations = [
        node
        for node in ast.walk(tree)
        if (
            isinstance(node, (ast.Attribute, ast.Subscript))
            and isinstance(node.ctx, (ast.Store, ast.Del))
            and rooted_in_all(node)
        )
        or (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and rooted_in_all(node.func.value)
        )
    ]
    assignments = [
        node
        for node in tree.body
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "__all__"
        )
        or (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "__all__"
            and node.value is not None
        )
    ]
    if len(assignments) != 1 or len(stored_names) != 1 or mutations:
        raise DistributionValidationError(
            f"expected one literal top-level __all__ assignment in {label}"
        )
    assignment = assignments[0]
    value_node = assignment.value
    assert value_node is not None
    try:
        value = ast.literal_eval(value_node)
    except (TypeError, ValueError) as error:
        raise DistributionValidationError(
            f"package __all__ is not literal in {label}"
        ) from error
    if (
        not isinstance(value, (list, tuple))
        or not value
        or any(
            not isinstance(name, str)
            or not name
            or not name.isascii()
            or not name.isidentifier()
            for name in value
        )
        or len(value) != len(set(value))
    ):
        raise DistributionValidationError(
            f"package __all__ is not a non-empty ordered unique ASCII identifier "
            f"sequence in {label}"
        )
    return tuple(value)


def _initializer_bytes_manifest_sha256(
    ordered_sources: Sequence[tuple[str, bytes]],
) -> str:
    digest = hashlib.sha256()
    for initializer, source in ordered_sources:
        encoded_path = initializer.encode("utf-8")
        digest.update(len(encoded_path).to_bytes(8, "big"))
        digest.update(encoded_path)
        digest.update(len(source).to_bytes(8, "big"))
        digest.update(source)
    return digest.hexdigest()


def _ordered_export_manifest_sha256(packages: Sequence[dict[str, object]]) -> str:
    payload = [
        {
            "module": package["module"],
            "initializer": package["initializer"],
            "exports": list(package["exports"]),
        }
        for package in packages
    ]
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _require_ordered_export_state(
    initializer_sources: dict[str, bytes],
    *,
    classification: dict[str, object],
    artifact_kind: str,
) -> dict[str, object]:
    packages = classification.get("packages")
    initializers = classification.get("initializers")
    if not isinstance(packages, tuple) or not isinstance(initializers, tuple):
        raise DistributionValidationError("ordered export classification is incomplete")
    observed = tuple(sorted(initializer_sources))
    expected = tuple(sorted(initializers))
    missing = sorted(set(expected) - set(observed))
    extra = sorted(set(observed) - set(expected))
    if observed != expected:
        raise DistributionValidationError(
            f"{artifact_kind} package initializer topology differs: "
            f"missing={missing}, extra={extra}"
        )
    package_receipts: list[dict[str, object]] = []
    ordered_sources: list[tuple[str, bytes]] = []
    for package in packages:
        module = str(package["module"])
        initializer = str(package["initializer"])
        expected_exports = package["exports"]
        assert isinstance(expected_exports, tuple)
        source = initializer_sources[initializer]
        observed_exports = _load_literal_ordered_exports(
            source,
            label=f"{artifact_kind}:{initializer}",
        )
        if observed_exports != expected_exports:
            raise DistributionValidationError(
                f"{artifact_kind} ordered exports differ for {module}: "
                f"expected={list(expected_exports)!r}, "
                f"observed={list(observed_exports)!r}"
            )
        ordered_sources.append((initializer, source))
        package_receipts.append(
            {
                "module": module,
                "initializer": initializer,
                "export_count": len(observed_exports),
                "ordered_exports_sha256": hashlib.sha256(
                    json.dumps(
                        list(observed_exports),
                        ensure_ascii=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ).hexdigest(),
                "source_sha256": hashlib.sha256(source).hexdigest(),
            }
        )
    export_count = sum(int(receipt["export_count"]) for receipt in package_receipts)
    if (
        len(package_receipts) != ORDERED_EXPORT_PACKAGE_COUNT
        or export_count != ORDERED_EXPORT_NAME_COUNT
    ):
        raise DistributionValidationError(
            f"{artifact_kind} ordered exports differ from the exact "
            "24-package/559-name inventory"
        )
    return {
        "observation": "exact-literal-ordered-set",
        "package_count": len(package_receipts),
        "export_count": export_count,
        "initializer_bytes_sha256": _initializer_bytes_manifest_sha256(ordered_sources),
        "ordered_exports_sha256": _ordered_export_manifest_sha256(packages),
        "packages": package_receipts,
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
    source = (
        source_root / "src/spirallens/qualification/confirmation_attempt_records.py"
    )
    destination = (
        build_lib
        / "spirallens/qualification/__pycache__/"
        / f"confirmation_attempt_records.cpython-{sys.version_info.major}{sys.version_info.minor}.pyc"
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
        or "confirmation_attempt_records" not in detail
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


def _require_absent_sdist_test_surface(
    extracted_source: Path,
) -> dict[str, object]:
    """Require the extracted sdist to omit its top-level ``tests`` path."""

    tests_path = extracted_source / "tests"
    try:
        tests_path.lstat()
    except FileNotFoundError:
        return {"observation": "absent", "count": 0, "members": []}
    except OSError as error:
        raise DistributionValidationError(
            "cannot inspect extracted sdist top-level tests path"
        ) from error
    raise DistributionValidationError("extracted sdist contains top-level tests path")


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


def _read_bounded_initializer(path: Path, *, label: str) -> bytes:
    try:
        mode = path.lstat().st_mode
        if not stat.S_ISREG(mode):
            raise DistributionValidationError(
                f"{label} must be an ordinary initializer file"
            )
        with path.open("rb") as handle:
            source = handle.read(_MAX_INITIALIZER_BYTES + 1)
    except OSError as error:
        raise DistributionValidationError(f"cannot read {label}") from error
    if len(source) > _MAX_INITIALIZER_BYTES:
        raise DistributionValidationError(f"{label} exceeds its initializer size bound")
    return source


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
    ordered_export_classification: dict[str, object] | None = None,
) -> dict[str, object]:
    """Require one wheel's package subtree to be the exact Python-only set."""

    initializer_sources: dict[str, bytes] = {}
    with zipfile.ZipFile(wheel) as archive:
        infos = archive.infolist()
        for info in infos:
            path = PurePosixPath(info.filename)
            if (
                not info.is_dir()
                and path.name == "__init__.py"
                and not any(part.endswith(".dist-info") for part in path.parts)
            ):
                with archive.open(info) as handle:
                    source = handle.read(_MAX_INITIALIZER_BYTES + 1)
                if len(source) > _MAX_INITIALIZER_BYTES:
                    raise DistributionValidationError(
                        f"wheel initializer {info.filename!r} exceeds its size bound"
                    )
                initializer_sources[info.filename] = source
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
    receipt = _require_exact_python_members(
        package_members,
        expected_members=expected_members,
        artifact_kind="wheel",
    )
    if ordered_export_classification is not None:
        receipt["ordered_export_inventory"] = _require_ordered_export_state(
            initializer_sources,
            classification=ordered_export_classification,
            artifact_kind="wheel",
        )
    return receipt


def _classify_sdist_python_members(
    sdist: Path,
    *,
    expected_members: Sequence[str],
    ordered_export_classification: dict[str, object] | None = None,
) -> dict[str, object]:
    """Require an sdist's ``src/spirallens`` subtree to be the exact set."""

    initializer_sources: dict[str, bytes] = {}
    with tarfile.open(sdist, mode="r:gz") as archive:
        infos = archive.getmembers()
        if ordered_export_classification is not None:
            for info in infos:
                parts = PurePosixPath(info.name).parts
                if (
                    info.isfile()
                    and len(parts) >= 4
                    and parts[1] == "src"
                    and parts[-1] == "__init__.py"
                    and not parts[2].endswith(".egg-info")
                ):
                    handle = archive.extractfile(info)
                    if handle is None:
                        raise DistributionValidationError(
                            f"cannot read sdist initializer {info.name!r}"
                        )
                    with handle:
                        source = handle.read(_MAX_INITIALIZER_BYTES + 1)
                    if len(source) > _MAX_INITIALIZER_BYTES:
                        raise DistributionValidationError(
                            f"sdist initializer {info.name!r} exceeds its size bound"
                        )
                    initializer_sources["/".join(parts[2:])] = source
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
    receipt = _require_exact_python_members(
        package_members,
        expected_members=expected_members,
        artifact_kind="sdist",
    )
    if ordered_export_classification is not None:
        receipt["ordered_export_inventory"] = _require_ordered_export_state(
            initializer_sources,
            classification=ordered_export_classification,
            artifact_kind="sdist",
        )
    return receipt


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


def _require_sdist_exact_file(
    sdist: Path,
    *,
    relative: str,
    expected_bytes: bytes,
    label: str,
) -> dict[str, object]:
    """Require one regular sdist member to equal its reviewed source bytes."""

    with tarfile.open(sdist, mode="r:gz") as archive:
        matches = [
            info
            for info in archive.getmembers()
            if "/".join(PurePosixPath(info.name).parts[1:]) == relative
        ]
        if len(matches) != 1 or not matches[0].isfile():
            raise DistributionValidationError(f"sdist must contain one regular {label}")
        handle = archive.extractfile(matches[0])
        if handle is None:
            raise DistributionValidationError(f"cannot read the sdist {label}")
        with handle:
            payload = handle.read(_MAX_CLASSIFICATION_BYTES + 1)
    if len(payload) > _MAX_CLASSIFICATION_BYTES or payload != expected_bytes:
        raise DistributionValidationError(f"sdist {label} differs from source")
    return {
        "path": relative,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
        "byte_identical_to_source": True,
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
            f"49 paths: missing={missing}, unexpected={unexpected}"
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
    ordered_export_classification: dict[str, object] | None = None,
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
    initializer_sources: dict[str, bytes] = {}

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
                elif name == "__init__.py":
                    initializer_sources[relative.removeprefix("src/")] = (
                        _read_bounded_initializer(
                            child,
                            label=f"source initializer {relative!r}",
                        )
                    )
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
    if ordered_export_classification is not None:
        exact["ordered_export_inventory"] = _require_ordered_export_state(
            initializer_sources,
            classification=ordered_export_classification,
            artifact_kind="source tree",
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
    ordered_package_export_inventory: dict[str, object],
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
        "ordered_package_export_inventory": ordered_package_export_inventory,
        "closed_wheel_python_module_inventory_established": True,
        "closed_ordered_package_export_inventory_established": True,
        "closed_installed_module_import_outcome_inventory_established": True,
        "closed_public_api_contract_established": False,
        "runtime_successful_package_export_values_established": True,
        "runtime_export_values_established": False,
        "all_package_runtime_export_values_established": False,
        "export_symbol_importability_established": False,
        "side_effect_free_imports_established": False,
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


_INSTALLED_IMPORT_ROOT_DISCOVERY_PROBE = r"""
import importlib.metadata
import json
import os
from pathlib import Path
import site
import sys
import sysconfig

dependencies = json.loads(sys.argv[1])
environment_root = Path(sys.argv[2]).resolve()
if sys.flags.isolated != 1 or sys.flags.no_site != 1:
    raise RuntimeError("root discovery requires isolated no-site startup")

candidate_roots = []


def add_candidate(value):
    if not isinstance(value, str):
        return
    path = Path(value).resolve()
    if path.is_dir() and path not in candidate_roots:
        candidate_roots.append(path)


if os.name == "nt":
    add_candidate(str(environment_root / "Lib/site-packages"))
else:
    add_candidate(
        str(
            environment_root
            / f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"
        )
    )
add_candidate(sysconfig.get_path("purelib"))
add_candidate(sysconfig.get_path("platlib"))
base_variables = {"base": sys.base_prefix, "platbase": sys.base_prefix}
add_candidate(sysconfig.get_path("purelib", vars=base_variables))
add_candidate(sysconfig.get_path("platlib", vars=base_variables))
for value in site.getsitepackages([sys.base_prefix]):
    add_candidate(value)
user_sites = site.getusersitepackages()
if isinstance(user_sites, str):
    add_candidate(user_sites)
else:
    for value in user_sites:
        add_candidate(value)
sys.path.extend(str(path) for path in candidate_roots)


def distribution_import_root(distribution, import_name):
    files = distribution.files
    if files is None:
        raise RuntimeError(f"{distribution.metadata['Name']!r} has no file inventory")
    expected = f"{import_name}/__init__.py"
    matching = [
        Path(distribution.locate_file(item)).resolve()
        for item in files
        if Path(str(item)).as_posix() == expected
    ]
    if len(matching) != 1 or not matching[0].is_file():
        raise RuntimeError(
            f"{distribution.metadata['Name']!r} has no unique {expected!r}"
        )
    return matching[0].parent.parent, matching[0]


spirallens = importlib.metadata.distribution("spirallens")
spirallens_root, spirallens_origin = distribution_import_root(
    spirallens, "spirallens"
)
if not spirallens_origin.is_relative_to(environment_root):
    raise RuntimeError("SpiralLens discovery resolved outside its fresh environment")

observations = []
explicit_roots = [spirallens_root]
for expected in dependencies:
    distribution = importlib.metadata.distribution(expected["distribution"])
    import_root, import_origin = distribution_import_root(
        distribution, expected["import_name"]
    )
    if import_origin.is_relative_to(environment_root):
        raise RuntimeError(
            f"declared dependency {expected['import_name']!r} is not host-projected"
        )
    if import_root not in explicit_roots:
        explicit_roots.append(import_root)
    observations.append(
        {
            "distribution": distribution.metadata["Name"],
            "import_name": expected["import_name"],
            "origin": str(import_origin),
            "requirement": expected["requirement"],
            "version": distribution.version,
        }
    )

print(
    json.dumps(
        {
            "base_dependencies": observations,
            "explicit_import_roots": [str(path) for path in explicit_roots],
            "isolated_mode_enabled": True,
            "pth_startup_executed": False,
            "site_initialization_enabled": False,
            "spirallens_requires_dist": list(spirallens.requires or ()),
            "spirallens_origin": str(spirallens_origin),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
)
"""


_INSTALLED_IMPORT_MODULE_PROBE = r"""
import hashlib
import importlib
import importlib.abc
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import sys
import sysconfig
import traceback
import typing

module_name = sys.argv[1]
expected_outcome = sys.argv[2]
expected_initializer_exports = json.loads(sys.argv[3])
worker_policy = json.loads(sys.argv[4])
explicit_import_roots = tuple(json.loads(sys.argv[5]))
expected_member = sys.argv[6]

if not isinstance(worker_policy, dict) or set(worker_policy) != {
    "base_dependencies",
    "blocked_optional_prefixes",
    "denied_audit_events",
    "models_extra_missing_torch",
    "schema_version",
}:
    raise RuntimeError("installed import probe received invalid policy fields")
base_dependencies = worker_policy["base_dependencies"]
raw_blocked_prefixes = worker_policy["blocked_optional_prefixes"]
raw_denied_audit_events = worker_policy["denied_audit_events"]
raw_missing_torch_modules = worker_policy["models_extra_missing_torch"]
blocked_optional_prefixes = tuple(raw_blocked_prefixes)
denied_audit_events = tuple(raw_denied_audit_events)
missing_torch_modules = tuple(raw_missing_torch_modules)
if (
    not isinstance(worker_policy["schema_version"], str)
    or not worker_policy["schema_version"]
    or not isinstance(base_dependencies, list)
    or not base_dependencies
    or not isinstance(raw_blocked_prefixes, list)
    or not raw_blocked_prefixes
    or not isinstance(raw_denied_audit_events, list)
    or not raw_denied_audit_events
    or not isinstance(raw_missing_torch_modules, list)
    or not raw_missing_torch_modules
    or any(
        not isinstance(item, dict)
        or set(item) != {"distribution", "import_name", "requirement"}
        or any(not isinstance(value, str) or not value for value in item.values())
        for item in base_dependencies
    )
    or any(not isinstance(prefix, str) or not prefix for prefix in blocked_optional_prefixes)
    or any(not isinstance(event, str) or not event for event in denied_audit_events)
    or any(not isinstance(name, str) or not name for name in missing_torch_modules)
    or (expected_outcome == "models_extra_missing_torch")
    != (module_name in missing_torch_modules)
):
    raise RuntimeError("installed import probe received invalid policy values")
declared_distribution_names = {
    item["distribution"].casefold().replace("_", "-"): item["distribution"]
    for item in base_dependencies
}

if sys.flags.isolated != 1 or sys.flags.no_site != 1:
    raise RuntimeError("installed import probe requires isolated no-site startup")
if not explicit_import_roots or any(
    not isinstance(root, str) or not Path(root).is_absolute()
    for root in explicit_import_roots
):
    raise RuntimeError("installed import probe received invalid explicit roots")
if any("site-packages" in Path(root).parts for root in sys.path):
    raise RuntimeError("installed import probe started with an implicit site path")
sys.path.extend(explicit_import_roots)


def matches_prefix(name, prefix):
    return name == prefix or name.startswith(prefix + ".")


tracked_import_prefixes = blocked_optional_prefixes
if module_name in ("spirallens.atlas.id_sweep", "spirallens.atlas.engineering_run"):
    tracked_import_prefixes += ("spirallens.adapters",)
preloaded_optional = sorted(
    prefix
    for prefix in tracked_import_prefixes
    if any(matches_prefix(name, prefix) for name in sys.modules)
)
if preloaded_optional:
    raise RuntimeError(
        f"installed import probe began with optional modules: {preloaded_optional}"
    )

blocked_optional_import_attempts = []


class OptionalImportBlocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        for prefix in tracked_import_prefixes:
            if matches_prefix(fullname, prefix):
                blocked_optional_import_attempts.append(fullname)
                raise ModuleNotFoundError(
                    f"blocked optional dependency: {fullname}",
                    name=fullname,
                )
        return None


sys.meta_path.insert(0, OptionalImportBlocker())
packages_to_distributions = importlib.metadata.packages_distributions()
blocked_undeclared_import_attempts = []


class UndeclaredImportBlocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        top_level = fullname.split(".", 1)[0]
        if top_level in sys.stdlib_module_names or top_level == "spirallens":
            return None
        distributions = packages_to_distributions.get(top_level)
        if distributions is None:
            return None
        canonical = {
            name.casefold().replace("_", "-") for name in distributions
        }
        if not canonical or not canonical.issubset(declared_distribution_names):
            blocked_undeclared_import_attempts.append(fullname)
            raise ModuleNotFoundError(
                f"blocked undeclared dependency: {fullname}",
                name=fullname,
            )
        return None


sys.meta_path.insert(1, UndeclaredImportBlocker())
denied_events = []
write_flags = (
    os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
)
audited_events = set(denied_audit_events) - {"builtins/open-write"}


def deny_import_side_effect(event, arguments):
    denied = False
    if event == "open":
        mode = arguments[1] if len(arguments) > 1 else None
        flags = arguments[2] if len(arguments) > 2 else None
        denied = (
            isinstance(mode, str)
            and any(character in mode for character in "wax+")
        ) or (isinstance(flags, int) and bool(flags & write_flags))
        policy_event = "builtins/open-write"
    else:
        denied = event in audited_events
        policy_event = event
    if denied:
        denied_events.append(policy_event)
        raise RuntimeError(f"blocked installed import audit event: {policy_event}")


sys.addaudithook(deny_import_side_effect)
stdlib_bootstrap_modules = frozenset(sys.modules)
if any(
    name
    and name.split(".", 1)[0] not in sys.stdlib_module_names
    and name.split(".", 1)[0] != "__main__"
    and packages_to_distributions.get(name.split(".", 1)[0]) is not None
    for name in stdlib_bootstrap_modules
):
    raise RuntimeError("installed import probe bootstrapped a third-party module")

allowed_dependencies = {
    item["distribution"].casefold().replace("_", "-"): (
        item["import_name"],
        item["requirement"],
    )
    for item in base_dependencies
}
allowed_distribution_versions = {}
allowed_distribution_files = {}
for distribution_name in (item["distribution"] for item in base_dependencies):
    distribution = importlib.metadata.distribution(distribution_name)
    canonical_name = distribution_name.casefold().replace("_", "-")
    allowed_distribution_versions[canonical_name] = distribution.version
    files = distribution.files
    if files is None:
        raise RuntimeError(
            f"declared dependency {distribution_name!r} has no file inventory"
        )
    allowed_distribution_files[canonical_name] = {
        Path(distribution.locate_file(item)).resolve() for item in files
    }

spirallens_distribution = importlib.metadata.distribution("spirallens")
spirallens_files = spirallens_distribution.files
if spirallens_files is None:
    raise RuntimeError("installed SpiralLens distribution has no file inventory")
spirallens_distribution_files = {
    Path(spirallens_distribution.locate_file(item)).resolve()
    for item in spirallens_files
}
spirallens_initializers = [
    path
    for path in spirallens_distribution_files
    if path.as_posix().endswith("/spirallens/__init__.py")
]
if len(spirallens_initializers) != 1:
    raise RuntimeError("installed SpiralLens distribution has no unique initializer")
spirallens_distribution_root = spirallens_initializers[0].parent.parent
spirallens_requires_dist = list(spirallens_distribution.requires or ())


def concrete_origin(loaded_module):
    origin = getattr(loaded_module, "__file__", None)
    if not isinstance(origin, str):
        specification = getattr(loaded_module, "__spec__", None)
        origin = getattr(specification, "origin", None)
    if not isinstance(origin, str) or origin in {"built-in", "frozen"}:
        return None
    return Path(origin).resolve()


stdlib_roots = {
    Path(path).resolve()
    for path in (sysconfig.get_path("stdlib"), sysconfig.get_path("platstdlib"))
    if isinstance(path, str)
}
stdlib_internal_modules = {sysconfig._get_sysconfigdata_name()}
baseline_modules = frozenset(sys.modules)
status = "unexpected_failure"
missing_name = None
module = None
failure_type = None
failure_message = None
failure_frames = []
try:
    module = importlib.import_module(module_name)
except ModuleNotFoundError as error:
    status = "models_extra_missing_torch"
    missing_name = error.name
    failure_type = type(error).__name__
    failure_message = str(error)
    failure_frames = [frame.filename for frame in traceback.extract_tb(error.__traceback__)]
except BaseException as error:
    failure_type = type(error).__name__
    failure_message = str(error)
else:
    status = "base_import_success"

if status != expected_outcome:
    raise RuntimeError(
        f"{module_name} produced {status!r}, expected {expected_outcome!r}: "
        f"{failure_type}: {failure_message}"
    )
if status == "models_extra_missing_torch":
    if (
        missing_name != "torch"
        or failure_type != "ModuleNotFoundError"
        or failure_message != "blocked optional dependency: torch"
    ):
        raise RuntimeError(
            f"{module_name} did not fail solely at the exact blocked torch boundary"
        )
    expected_suffix = "/" + expected_member
    candidate_origins = sorted(
        {
            str(Path(filename).resolve())
            for filename in failure_frames
            if filename.endswith(expected_suffix)
        }
    )
    if len(candidate_origins) != 1:
        raise RuntimeError(
            f"{module_name} failure is not bound to exact member {expected_member!r}"
        )
    module_origin = candidate_origins[0]
    if Path(module_origin).resolve() not in spirallens_distribution_files:
        raise RuntimeError(
            f"{module_name} failure origin is not an exact SpiralLens wheel file"
        )
    runtime_exports = None
else:
    module_origin = getattr(module, "__file__", None)
    if not isinstance(module_origin, str):
        raise RuntimeError(f"{module_name} has no concrete module origin")
    if Path(module_origin).resolve() not in spirallens_distribution_files:
        raise RuntimeError(
            f"{module_name} origin is not an exact SpiralLens wheel file"
        )
    runtime_value = getattr(module, "__all__", None)
    if expected_initializer_exports is None or module_name == (
        "spirallens.atlas.engineering_run"
    ):
        runtime_exports = None
    else:
        if (
            type(runtime_value) is not list
            or any(type(item) is not str for item in runtime_value)
            or runtime_value != expected_initializer_exports
        ):
            raise RuntimeError(
                f"{module_name} runtime __all__ differs from its literal inventory"
            )
        runtime_exports = runtime_value


def require_exact_blocked_torch(function, label):
    try:
        function()
    except ModuleNotFoundError as error:
        if (
            error.name != "torch"
            or str(error) != "blocked optional dependency: torch"
            or error.__cause__ is not None
            or error.__context__ is not None
            or blocked_optional_import_attempts != ["torch"]
        ):
            raise RuntimeError(f"{label} call did not fail at exact torch") from error
    else:
        raise RuntimeError(f"{label} call crossed the blocked torch boundary")


def has_exact_signature(function, names, annotations, kind):
    signature = inspect.signature(function)
    parameters = tuple(signature.parameters.values())
    return (
        tuple(parameter.name for parameter in parameters) == names
        and all(
            parameter.kind is kind
            and parameter.default is inspect.Parameter.empty
            for parameter in parameters
        )
        and signature.return_annotation == annotations["return"]
        and function.__annotations__ == annotations
    )


if module_name == "spirallens.atlas.id_sweep":
    neutral_names = (
        "ATLAS_CONTEXT_BINDING_SCHEMA_VERSION",
        "ContextBankBinding",
        "SweepConfig",
        "run_id_sweep",
        "select_token_ids",
    )
    atlas = importlib.import_module("spirallens.atlas")
    if (
        tuple(name for name in atlas.__all__ if name in neutral_names)
        != neutral_names
        or any(getattr(atlas, name) is not getattr(module, name) for name in neutral_names)
        or any(
            getattr(getattr(module, name), "__module__", None) != module_name
            for name in neutral_names[1:]
        )
    ):
        raise RuntimeError("id_sweep neutral root/module identities differ")
    expected_annotations = {
        "adapter": "PythiaAdapter",
        "config": "SweepConfig",
        "return": "dict[str, object]",
    }
    if not has_exact_signature(
        module.run_id_sweep,
        ("adapter", "config"),
        expected_annotations,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    ):
        raise RuntimeError("id_sweep run signature or raw annotations differ")
    for neutral in (
        module.ContextBankBinding,
        module.SweepConfig,
        module.select_token_ids,
    ):
        resolved = typing.get_type_hints(neutral)
        if set(resolved) != set(neutral.__annotations__) or any(
            isinstance(value, str) for value in resolved.values()
        ):
            raise RuntimeError("id_sweep neutral type hints did not resolve")
    selected = module.select_token_ids(6, subset=(4, 1, 3), max_tokens=2)
    if selected.tolist() != [4, 1] or str(selected.dtype) != "int64":
        raise RuntimeError("id_sweep bounded token selection differs")
    if any(
        name in sys.modules
        for name in (
            "spirallens.adapters",
            "spirallens.adapters.pythia",
            "spirallens.atlas.engineering_run",
        )
    ):
        raise RuntimeError("id_sweep neutral surface loaded a model module")

    class Bomb:
        def __getattribute__(self, name):
            raise RuntimeError(f"id_sweep bomb attribute accessed: {name}")

    require_exact_blocked_torch(
        lambda: module.run_id_sweep(Bomb(), Bomb()), "id_sweep"
    )

if module_name == "spirallens.atlas.engineering_run":
    atlas = importlib.import_module("spirallens.atlas")
    error_type = module.PublicExamplePlumbingRunError
    run = module.run_public_example_plumbing
    star = {}
    exec("from spirallens.atlas import *", star)
    if (
        type(expected_initializer_exports) is not list
        or len(expected_initializer_exports) != 20
        or atlas.__all__ != expected_initializer_exports
        or set(star) != {"__builtins__", *expected_initializer_exports}
        or any(star[name] is not getattr(atlas, name) for name in atlas.__all__)
        or atlas.PublicExamplePlumbingRunError is not error_type
        or atlas.run_public_example_plumbing is not run
        or error_type.__module__ != module_name
        or run.__module__ != module_name
    ):
        raise RuntimeError("engineering_run Atlas star/root identities differ")
    expected_names = tuple(
        "protocol_path output_dir receipt_path expected_protocol_source_sha256 "
        "expected_protocol_canonical_sha256 repository_root".split()
    )
    path_arguments = {*expected_names[:3], expected_names[-1]}
    expected_annotations = {
        name: "str | Path" if name in path_arguments else "str"
        for name in expected_names
    }
    expected_annotations["return"] = "dict[str, object]"
    resolved_hints = typing.get_type_hints(run)
    expected_hints = dict.fromkeys(expected_names, str)
    expected_hints.update(dict.fromkeys(path_arguments, str | Path))
    expected_hints["return"] = dict[str, object]
    if (
        not has_exact_signature(
            run,
            expected_names,
            expected_annotations,
            inspect.Parameter.KEYWORD_ONLY,
        )
        or resolved_hints != expected_hints
    ):
        raise RuntimeError("engineering_run public signature or hints differ")
    if blocked_optional_import_attempts or any(
        matches_prefix(name, "spirallens.adapters") for name in sys.modules
    ):
        raise RuntimeError("engineering_run neutral surface loaded a model module")

    class Bomb:
        def __getattribute__(self, name):
            raise RuntimeError(f"engineering_run bomb attribute accessed: {name}")

    bomb = Bomb()
    bomb_kwargs = {name: bomb for name in expected_names}
    require_exact_blocked_torch(
        lambda: run(**bomb_kwargs), "engineering_run"
    )
    if any(matches_prefix(name, "spirallens.adapters") for name in sys.modules):
        raise RuntimeError("engineering_run call retained a model module")

loaded_optional = sorted(
    prefix
    for prefix in blocked_optional_prefixes
    if any(matches_prefix(name, prefix) for name in sys.modules)
)
if loaded_optional:
    raise RuntimeError(
        f"{module_name} loaded blocked optional modules: {loaded_optional}"
    )

stdlib_names = set(sys.stdlib_module_names)
loaded_allowed_distributions = set()
dependency_runtime_modules_without_file_origin = []
dependency_runtime_module_aliases = []
reviewed_dependency_module_aliases = {
    "_cyutility": ("scipy._cyutility", "scipy"),
}
for name in sorted(set(sys.modules) - baseline_modules):
    loaded_module = sys.modules[name]
    if not name:
        continue
    top_level = name.split(".", 1)[0]
    if top_level in stdlib_names:
        continue
    resolved_origin = concrete_origin(loaded_module)
    if resolved_origin is None:
        dependency_runtime_modules_without_file_origin.append(name)
        continue
    if any(resolved_origin.is_relative_to(root) for root in stdlib_roots) and not any(
        part in {"site-packages", "dist-packages"}
        for part in resolved_origin.parts
    ):
        if top_level not in stdlib_internal_modules:
            raise RuntimeError(
                f"{module_name} loaded unclassified stdlib-path module {name!r}"
            )
        continue
    owners = []
    if resolved_origin in spirallens_distribution_files:
        owners.append("spirallens")
    owners.extend(
        distribution_name
        for distribution_name, files in allowed_distribution_files.items()
        if resolved_origin in files
    )
    if len(owners) != 1:
        raise RuntimeError(
            f"{module_name} target import module {name!r} is not owned by "
            f"exactly one allowed distribution: {resolved_origin}"
        )
    mapped_distributions = packages_to_distributions.get(top_level)
    if owners == ["spirallens"]:
        if top_level != "spirallens":
            raise RuntimeError(
                f"{module_name} loaded a non-SpiralLens name from a SpiralLens file"
            )
    else:
        if mapped_distributions is None:
            specification = getattr(loaded_module, "__spec__", None)
            specification_name = getattr(specification, "name", None)
            expected_alias = reviewed_dependency_module_aliases.get(top_level)
            if (
                expected_alias != (specification_name, owners[0])
                or sys.modules.get(specification_name) is not loaded_module
            ):
                raise RuntimeError(
                    f"{module_name} target import {top_level!r} has no exact "
                    f"metadata owner matching file owner {owners[0]!r}"
                )
            dependency_runtime_module_aliases.append(
                {
                    "alias": top_level,
                    "canonical_module": specification_name,
                    "distribution": owners[0],
                }
            )
            mapped_distributions = packages_to_distributions.get(
                specification_name.split(".", 1)[0]
            )
        if (
            not isinstance(mapped_distributions, list)
            or len(mapped_distributions) != 1
            or mapped_distributions[0].casefold().replace("_", "-") != owners[0]
        ):
            raise RuntimeError(
                f"{module_name} target import {top_level!r} metadata ownership "
                f"does not match exact file owner {owners[0]!r}"
            )
    if owners[0] != "spirallens":
        loaded_allowed_distributions.add(owners[0])
    if top_level == "spirallens" and owners != ["spirallens"]:
        raise RuntimeError(
            f"{module_name} loaded a SpiralLens module outside its exact wheel files"
        )

if any(
    name != "cython_runtime"
    and not (
        name.startswith("_cython_")
        and name.removeprefix("_cython_")
        and all(
            part.isascii() and part.isdigit()
            for part in name.removeprefix("_cython_").split("_")
        )
    )
    for name in dependency_runtime_modules_without_file_origin
):
    raise RuntimeError("target import created an unexpected originless module")
if dependency_runtime_modules_without_file_origin and not loaded_allowed_distributions:
    raise RuntimeError(
        "target import created originless runtime modules without a declared dependency"
    )

third_party_distributions = {}
for canonical_distribution in sorted(loaded_allowed_distributions):
    import_name, requirement = allowed_dependencies[canonical_distribution]
    imported = sys.modules.get(import_name)
    import_origin = concrete_origin(imported)
    if import_origin not in allowed_distribution_files[canonical_distribution]:
        raise RuntimeError(
            f"declared dependency {import_name!r} is not an exact distribution file"
        )
    distribution_name = declared_distribution_names[canonical_distribution]
    third_party_distributions[import_name] = {
        "distribution": distribution_name,
        "origin": str(import_origin),
        "requirement": requirement,
        "version": allowed_distribution_versions[canonical_distribution],
    }

print(
    json.dumps(
        {
            "audit_denied_event_count": len(denied_events),
            "audit_denied_events": denied_events,
            "blocked_optional_prefixes_loaded": loaded_optional,
            "blocked_undeclared_import_attempts": sorted(
                set(blocked_undeclared_import_attempts)
            ),
            "dependency_runtime_modules_without_file_origin": (
                dependency_runtime_modules_without_file_origin
            ),
            "dependency_runtime_module_aliases": dependency_runtime_module_aliases,
            "explicit_import_roots": list(explicit_import_roots),
            "failure_message": failure_message,
            "failure_type": failure_type,
            "missing_name": missing_name,
            "module": module_name,
            "module_origin": module_origin,
            "runtime_exports": runtime_exports,
            "runtime_exports_sha256": (
                None
                if runtime_exports is None
                else hashlib.sha256(
                    json.dumps(
                        runtime_exports,
                        ensure_ascii=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ).hexdigest()
            ),
            "spirallens_requires_dist": spirallens_requires_dist,
            "spirallens_distribution_root": str(spirallens_distribution_root),
            "site_initialization_enabled": False,
            "status": status,
            "third_party_distributions": third_party_distributions,
            "pth_startup_executed": False,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
)
"""


def _discover_installed_import_roots(
    *,
    python: Path,
    environment_root: Path,
    neutral_cwd: Path,
    environment: dict[str, str],
    artifact_kind: str,
    expected_requires_dist: tuple[dict[str, str | None], ...],
) -> dict[str, object]:
    """Discover only canonical venv/base/user roots without executing site files."""

    completed = subprocess.run(
        (
            str(python),
            "-I",
            "-S",
            "-B",
            "-c",
            _INSTALLED_IMPORT_ROOT_DISCOVERY_PROBE,
            json.dumps(INSTALLED_IMPORT_BASE_DEPENDENCIES),
            str(environment_root),
        ),
        cwd=neutral_cwd,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=INSTALLED_IMPORT_PROBE_TIMEOUT_SECONDS,
    )
    if completed.returncode != 0 or completed.stderr != "":
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise DistributionValidationError(
            f"{artifact_kind} explicit import-root discovery failed"
            + (f": {detail[-2000:]}" if detail else "")
        )
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise DistributionValidationError(
            f"{artifact_kind} explicit import-root discovery returned invalid JSON"
        ) from error
    expected_keys = {
        "base_dependencies",
        "explicit_import_roots",
        "isolated_mode_enabled",
        "pth_startup_executed",
        "site_initialization_enabled",
        "spirallens_requires_dist",
        "spirallens_origin",
    }
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise DistributionValidationError(
            f"{artifact_kind} explicit import-root discovery returned unexpected fields"
        )
    if (
        value.get("isolated_mode_enabled") is not True
        or value.get("site_initialization_enabled") is not False
        or value.get("pth_startup_executed") is not False
    ):
        raise DistributionValidationError(
            f"{artifact_kind} import-root discovery did not disable site startup"
        )
    normalized_requires_dist = _normalize_installed_requires_dist(
        value.get("spirallens_requires_dist"),
        expected=expected_requires_dist,
        label=f"{artifact_kind} installed wheel",
    )
    value["spirallens_requires_dist"] = list(normalized_requires_dist)
    environment_root = environment_root.resolve()
    spirallens_origin_value = value.get("spirallens_origin")
    if not isinstance(spirallens_origin_value, str):
        raise DistributionValidationError(
            f"{artifact_kind} root discovery omitted SpiralLens origin"
        )
    spirallens_origin = Path(spirallens_origin_value).resolve()
    if (
        not spirallens_origin.is_file()
        or not spirallens_origin.is_relative_to(environment_root)
        or not spirallens_origin.as_posix().endswith("/spirallens/__init__.py")
    ):
        raise DistributionValidationError(
            f"{artifact_kind} root discovery found invalid SpiralLens origin"
        )
    dependencies = value.get("base_dependencies")
    if not isinstance(dependencies, list) or len(dependencies) != len(
        INSTALLED_IMPORT_BASE_DEPENDENCIES
    ):
        raise DistributionValidationError(
            f"{artifact_kind} root discovery returned wrong dependency count"
        )
    expected_roots = [spirallens_origin.parent.parent]
    normalized_dependencies = []
    minimum_by_import = {"numpy": (1, 26), "scipy": (1, 11), "yaml": (6, 0)}
    for expected, observation in zip(
        INSTALLED_IMPORT_BASE_DEPENDENCIES, dependencies, strict=True
    ):
        if not isinstance(observation, dict) or set(observation) != {
            "distribution",
            "import_name",
            "origin",
            "requirement",
            "version",
        }:
            raise DistributionValidationError(
                f"{artifact_kind} root discovery returned malformed dependency data"
            )
        distribution = observation.get("distribution")
        import_name = observation.get("import_name")
        requirement = observation.get("requirement")
        version = observation.get("version")
        origin_value = observation.get("origin")
        if (
            not isinstance(distribution, str)
            or distribution.casefold().replace("_", "-")
            != expected["distribution"].casefold().replace("_", "-")
            or import_name != expected["import_name"]
            or requirement != expected["requirement"]
            or not isinstance(version, str)
            or not isinstance(origin_value, str)
        ):
            raise DistributionValidationError(
                f"{artifact_kind} root discovery dependency differs"
            )
        origin = Path(origin_value).resolve()
        if (
            not origin.is_file()
            or origin.is_relative_to(environment_root)
            or not origin.as_posix().endswith(f"/{import_name}/__init__.py")
        ):
            raise DistributionValidationError(
                f"{artifact_kind} dependency {import_name} is not host-projected"
            )
        _require_minimum_release_version(
            version,
            minimum=minimum_by_import[import_name],
            label=f"{artifact_kind} dependency {import_name}",
        )
        if origin.parent.parent not in expected_roots:
            expected_roots.append(origin.parent.parent)
        normalized_dependencies.append(observation)
    explicit_roots = value.get("explicit_import_roots")
    if (
        not isinstance(explicit_roots, list)
        or any(not isinstance(root, str) for root in explicit_roots)
        or [Path(root).resolve() for root in explicit_roots] != expected_roots
    ):
        raise DistributionValidationError(
            f"{artifact_kind} explicit import roots differ from exact package roots"
        )
    value["explicit_import_roots"] = [str(root) for root in expected_roots]
    value["spirallens_origin"] = spirallens_origin.relative_to(
        environment_root
    ).as_posix()
    value["base_dependencies"] = normalized_dependencies
    return value


def _parse_installed_import_probe_output(
    output: str,
    *,
    module: str,
    expected_member: str,
    expected_outcome: str,
    expected_initializer_exports: tuple[str, ...] | None,
    environment_root: Path,
    explicit_import_roots: tuple[str, ...],
    expected_dependencies: tuple[dict[str, object], ...],
    expected_requires_dist: tuple[dict[str, str | None], ...],
) -> dict[str, object]:
    """Parse one isolated installed-module probe and enforce exact boundaries."""

    try:
        value = json.loads(output)
    except json.JSONDecodeError as error:
        raise DistributionValidationError(
            f"installed import probe for {module} did not emit valid JSON"
        ) from error
    expected_keys = {
        "audit_denied_event_count",
        "audit_denied_events",
        "blocked_optional_prefixes_loaded",
        "blocked_undeclared_import_attempts",
        "dependency_runtime_modules_without_file_origin",
        "dependency_runtime_module_aliases",
        "explicit_import_roots",
        "failure_message",
        "failure_type",
        "missing_name",
        "module",
        "module_origin",
        "runtime_exports",
        "runtime_exports_sha256",
        "spirallens_requires_dist",
        "spirallens_distribution_root",
        "site_initialization_enabled",
        "status",
        "third_party_distributions",
        "pth_startup_executed",
    }
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise DistributionValidationError(
            f"installed import probe for {module} returned unexpected fields"
        )
    if value.get("module") != module or value.get("status") != expected_outcome:
        raise DistributionValidationError(
            f"installed import probe for {module} returned the wrong outcome"
        )
    if (
        value.get("audit_denied_event_count") != 0
        or value.get("audit_denied_events") != []
    ):
        raise DistributionValidationError(
            f"installed import probe for {module} attempted a denied audit event"
        )
    if value.get("blocked_optional_prefixes_loaded") != []:
        raise DistributionValidationError(
            f"installed import probe for {module} loaded a blocked optional prefix"
        )
    blocked_undeclared = value.get("blocked_undeclared_import_attempts")
    if (
        not isinstance(blocked_undeclared, list)
        or blocked_undeclared != sorted(set(blocked_undeclared))
        or any(not isinstance(name, str) or not name for name in blocked_undeclared)
    ):
        raise DistributionValidationError(
            f"installed import probe for {module} returned invalid undeclared attempts"
        )
    if (
        value.get("site_initialization_enabled") is not False
        or value.get("pth_startup_executed") is not False
        or value.get("explicit_import_roots") != list(explicit_import_roots)
    ):
        raise DistributionValidationError(
            f"installed import probe for {module} did not preserve no-site roots"
        )
    environment_root = environment_root.resolve()
    value["explicit_import_roots"] = _normalize_installed_import_explicit_roots(
        explicit_import_roots,
        environment_root=environment_root,
    )
    generated_modules = value.get("dependency_runtime_modules_without_file_origin")
    if (
        not isinstance(generated_modules, list)
        or generated_modules != sorted(set(generated_modules))
        or any(
            not isinstance(name, str)
            or (
                name != "cython_runtime"
                and not (
                    name.startswith("_cython_")
                    and name.removeprefix("_cython_")
                    and all(
                        part.isascii() and part.isdigit()
                        for part in name.removeprefix("_cython_").split("_")
                    )
                )
            )
            for name in generated_modules
        )
    ):
        raise DistributionValidationError(
            f"installed import probe for {module} returned invalid generated modules"
        )
    runtime_aliases = value.get("dependency_runtime_module_aliases")
    if not isinstance(runtime_aliases, list) or any(
        alias
        != {
            "alias": "_cyutility",
            "canonical_module": "scipy._cyutility",
            "distribution": "scipy",
        }
        for alias in runtime_aliases
    ):
        raise DistributionValidationError(
            f"installed import probe for {module} returned invalid dependency aliases"
        )
    distribution_root_value = value.get("spirallens_distribution_root")
    if not isinstance(distribution_root_value, str):
        raise DistributionValidationError(
            f"installed import probe for {module} omitted SpiralLens metadata root"
        )
    spirallens_distribution_root = Path(distribution_root_value).resolve()
    if not spirallens_distribution_root.is_relative_to(environment_root):
        raise DistributionValidationError(
            f"installed import probe for {module} resolved SpiralLens metadata "
            "outside its fresh environment"
        )
    value["spirallens_distribution_root"] = spirallens_distribution_root.relative_to(
        environment_root
    ).as_posix()
    normalized_requires_dist = _normalize_installed_requires_dist(
        value.get("spirallens_requires_dist"),
        expected=expected_requires_dist,
        label=f"installed import probe for {module}",
    )
    value["spirallens_requires_dist"] = list(normalized_requires_dist)
    negative_outcome = expected_outcome == "models_extra_missing_torch"
    if negative_outcome:
        if (
            value.get("failure_type") != "ModuleNotFoundError"
            or value.get("failure_message") != "blocked optional dependency: torch"
            or value.get("missing_name") != "torch"
            or value.get("runtime_exports") is not None
            or value.get("runtime_exports_sha256") is not None
        ):
            raise DistributionValidationError(
                f"installed import probe for {module} did not stop at exact torch"
            )
    else:
        if any(
            value.get(key) is not None
            for key in ("failure_type", "failure_message", "missing_name")
        ):
            raise DistributionValidationError(
                f"successful installed import probe for {module} returned a failure"
            )
    origin_value = value.get("module_origin")
    if not isinstance(origin_value, str):
        raise DistributionValidationError(
            f"installed import probe for {module} omitted its origin"
        )
    origin = Path(origin_value).resolve()
    if not origin.is_relative_to(environment_root):
        raise DistributionValidationError(
            f"{module} observed outside the fresh import environment: {origin}"
        )
    relative_origin = origin.relative_to(environment_root).as_posix()
    if not relative_origin.endswith(f"/{expected_member}"):
        raise DistributionValidationError(
            f"{module} origin does not match classified member {expected_member!r}"
        )
    value["module_origin"] = relative_origin
    if not negative_outcome:
        runtime_exports = value.get("runtime_exports")
        runtime_exports_sha256 = value.get("runtime_exports_sha256")
        if expected_initializer_exports is None:
            if runtime_exports is not None or runtime_exports_sha256 is not None:
                raise DistributionValidationError(
                    f"non-initializer {module} returned runtime package exports"
                )
        else:
            if runtime_exports != list(expected_initializer_exports):
                raise DistributionValidationError(
                    f"initializer {module} runtime exports differ"
                )
            expected_sha256 = hashlib.sha256(
                json.dumps(
                    list(expected_initializer_exports),
                    ensure_ascii=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            if runtime_exports_sha256 != expected_sha256:
                raise DistributionValidationError(
                    f"initializer {module} runtime export digest differs"
                )
    third_party = value.get("third_party_distributions")
    if not isinstance(third_party, dict):
        raise DistributionValidationError(
            f"installed import probe for {module} omitted dependency observations"
        )
    allowed_imports = {"numpy", "scipy", "yaml"}
    allowed_distributions = {"numpy", "scipy", "pyyaml"}
    for import_name, observation in third_party.items():
        if import_name not in allowed_imports or not isinstance(observation, dict):
            raise DistributionValidationError(
                f"installed import probe for {module} loaded an undeclared dependency"
            )
        if set(observation) != {
            "distribution",
            "version",
            "origin",
            "requirement",
        }:
            raise DistributionValidationError(
                f"installed import probe for {module} returned malformed dependency data"
            )
        distribution_name = observation.get("distribution")
        version = observation.get("version")
        origin_value = observation.get("origin")
        requirement = observation.get("requirement")
        expected_dependency = next(
            (
                dependency
                for dependency in INSTALLED_IMPORT_BASE_DEPENDENCIES
                if dependency["import_name"] == import_name
            ),
            None,
        )
        if (
            not isinstance(distribution_name, str)
            or distribution_name.casefold().replace("_", "-")
            not in allowed_distributions
            or not isinstance(version, str)
            or not version
            or not isinstance(origin_value, str)
            or expected_dependency is None
            or requirement != expected_dependency["requirement"]
        ):
            raise DistributionValidationError(
                f"installed import probe for {module} returned invalid dependency data"
            )
        origin = Path(origin_value).resolve()
        if not origin.exists():
            raise DistributionValidationError(
                f"{module} dependency {import_name} has a missing origin: {origin}"
            )
        if origin.is_relative_to(environment_root):
            raise DistributionValidationError(
                f"{module} dependency {import_name} was not host-projected: {origin}"
            )
        observation["origin"] = str(origin)
        minimum_by_import = {
            "numpy": (1, 26),
            "scipy": (1, 11),
            "yaml": (6, 0),
        }
        _require_minimum_release_version(
            version,
            minimum=minimum_by_import[import_name],
            label=f"{module} dependency {import_name}",
        )
    expected_dependency_by_import = {}
    for dependency in expected_dependencies:
        import_name = dependency["import_name"]
        if import_name not in third_party:
            continue
        expected_dependency_by_import[import_name] = {
            key: dependency[key]
            for key in ("distribution", "origin", "requirement", "version")
        }
    if third_party != expected_dependency_by_import:
        raise DistributionValidationError(
            f"installed import probe for {module} dependency receipt differs"
        )
    return value


def _installed_import_outcome_manifest_sha256(
    modules: Sequence[dict[str, object]],
) -> str:
    return hashlib.sha256(
        "".join(
            f"{module['module']}\t{module['status']}\t"
            f"{module['module_origin'] or ''}\t"
            f"{module['runtime_exports_sha256'] or ''}\n"
            for module in modules
        ).encode("utf-8")
    ).hexdigest()


def _require_minimum_release_version(
    version: str,
    *,
    minimum: tuple[int, ...],
    label: str,
) -> None:
    """Require a numeric final release at or above one frozen lower bound."""

    if not isinstance(version, str) or not version:
        raise DistributionValidationError(f"{label} version must be non-empty")
    components = version.split(".")
    if any(
        not component.isascii() or not component.isdigit() for component in components
    ):
        raise DistributionValidationError(
            f"{label} version must be a numeric final release"
        )
    observed = tuple(int(component) for component in components)
    width = max(len(observed), len(minimum))
    padded_observed = observed + (0,) * (width - len(observed))
    padded_minimum = minimum + (0,) * (width - len(minimum))
    if padded_observed < padded_minimum:
        raise DistributionValidationError(
            f"{label} version does not satisfy its declared minimum"
        )


def _probe_installed_import_outcomes(
    *,
    python: Path,
    environment_root: Path,
    neutral_cwd: Path,
    environment: dict[str, str],
    classification: dict[str, object],
    ordered_export_classification: dict[str, object],
    artifact_kind: str,
) -> dict[str, object]:
    """Import every classified module in a distinct fail-closed subprocess."""

    outcomes = classification.get("outcomes")
    if not isinstance(outcomes, dict):
        raise DistributionValidationError(
            "installed import classification outcomes are unavailable"
        )
    expected_by_module = {
        module: role for role, modules in outcomes.items() for module in modules
    }
    python_member_classification = classification.get("python_members")
    if not isinstance(python_member_classification, dict):
        raise DistributionValidationError(
            "installed import classification lacks its Python member join"
        )
    expected_member_by_module = {
        _python_member_module(member): member
        for member in python_member_classification["shipped_members"]
    }
    if set(expected_member_by_module) != set(expected_by_module):
        raise DistributionValidationError(
            "installed import classification differs from its Python member join"
        )
    ordered_packages = ordered_export_classification.get("packages")
    if not isinstance(ordered_packages, tuple):
        raise DistributionValidationError(
            "ordered package export classification is unavailable"
        )
    initializer_exports = {
        str(package["module"]): package["exports"] for package in ordered_packages
    }
    blocked_prefixes = classification.get("blocked_optional_prefixes")
    if not isinstance(blocked_prefixes, tuple):
        raise DistributionValidationError(
            "installed import optional-prefix classification is unavailable"
        )
    expected_requires_dist = classification.get("requires_dist_contract")
    if not isinstance(expected_requires_dist, tuple):
        raise DistributionValidationError(
            "installed import full Requires-Dist contract is unavailable"
        )
    root_discovery = _discover_installed_import_roots(
        python=python,
        environment_root=environment_root,
        neutral_cwd=neutral_cwd,
        environment=environment,
        artifact_kind=artifact_kind,
        expected_requires_dist=expected_requires_dist,
    )
    explicit_import_roots = tuple(root_discovery["explicit_import_roots"])
    expected_dependencies = tuple(root_discovery["base_dependencies"])

    def run_module(module: str) -> dict[str, object]:
        expected_outcome = expected_by_module[module]
        expected_exports = initializer_exports.get(module)
        probe_exports = expected_exports
        if module == "spirallens.atlas.engineering_run":
            probe_exports = initializer_exports["spirallens.atlas"]
        try:
            completed = subprocess.run(
                (
                    str(python),
                    "-I",
                    "-S",
                    "-B",
                    "-c",
                    _INSTALLED_IMPORT_MODULE_PROBE,
                    module,
                    expected_outcome,
                    json.dumps(probe_exports),
                    _INSTALLED_IMPORT_WORKER_POLICY,
                    json.dumps(explicit_import_roots),
                    expected_member_by_module[module],
                ),
                cwd=neutral_cwd,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
                timeout=INSTALLED_IMPORT_PROBE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as error:
            raise DistributionValidationError(
                f"{artifact_kind} isolated import probe timed out for {module}"
            ) from error
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            if len(detail) > 2000:
                detail = detail[-2000:]
            raise DistributionValidationError(
                f"{artifact_kind} isolated import probe failed for {module}"
                + (f": {detail}" if detail else "")
            )
        if completed.stderr != "":
            raise DistributionValidationError(
                f"{artifact_kind} isolated import probe wrote stderr for {module}"
            )
        return _parse_installed_import_probe_output(
            completed.stdout,
            module=module,
            expected_member=expected_member_by_module[module],
            expected_outcome=expected_outcome,
            expected_initializer_exports=expected_exports,
            environment_root=environment_root,
            explicit_import_roots=explicit_import_roots,
            expected_dependencies=expected_dependencies,
            expected_requires_dist=expected_requires_dist,
        )

    modules = tuple(sorted(expected_by_module))
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=INSTALLED_IMPORT_PROBE_CONCURRENCY
    ) as executor:
        observations = tuple(executor.map(run_module, modules))
    successes = tuple(
        observation
        for observation in observations
        if observation["status"] == "base_import_success"
    )
    missing_torch = tuple(
        observation
        for observation in observations
        if observation["status"] == "models_extra_missing_torch"
    )
    runtime_packages = tuple(
        observation
        for observation in successes
        if observation["module"] in initializer_exports
    )
    runtime_export_count = sum(
        len(observation["runtime_exports"]) for observation in runtime_packages
    )
    if (
        len(observations) != 133
        or len(successes) != INSTALLED_IMPORT_SUCCESS_COUNT
        or len(missing_torch) != INSTALLED_IMPORT_MISSING_TORCH_COUNT
        or len(runtime_packages) != INSTALLED_IMPORT_SUCCESSFUL_INITIALIZER_COUNT
        or runtime_export_count != INSTALLED_IMPORT_SUCCESSFUL_RUNTIME_EXPORT_COUNT
        or any(
            observation["audit_denied_event_count"] != 0 for observation in observations
        )
    ):
        raise DistributionValidationError(
            f"{artifact_kind} installed import outcome aggregate differs"
        )
    dependency_observations: dict[str, dict[str, object]] = {}
    for observation in observations:
        for import_name, dependency in observation["third_party_distributions"].items():
            current = dependency_observations.setdefault(import_name, dependency)
            if current != dependency:
                raise DistributionValidationError(
                    f"{artifact_kind} dependency observation differs across imports"
                )
    if set(dependency_observations) != {"numpy", "scipy", "yaml"}:
        raise DistributionValidationError(
            f"{artifact_kind} imports did not exercise all declared base dependencies"
        )
    originless_runtime_modules = sorted(
        {
            name
            for observation in observations
            for name in observation["dependency_runtime_modules_without_file_origin"]
        }
    )
    dependency_runtime_module_aliases = sorted(
        {
            json.dumps(alias, sort_keys=True, separators=(",", ":"))
            for observation in observations
            for alias in observation["dependency_runtime_module_aliases"]
        }
    )
    blocked_undeclared_import_attempts = sorted(
        {
            name
            for observation in observations
            for name in observation["blocked_undeclared_import_attempts"]
        }
    )
    return {
        "observation": "exact-host-installed-module-import-outcomes",
        "module_process_isolation": "one-fresh-process-per-module",
        "module_count": len(observations),
        "base_import_success_count": len(successes),
        "models_extra_missing_torch_count": len(missing_torch),
        "successful_runtime_initializer_count": len(runtime_packages),
        "successful_runtime_export_count": runtime_export_count,
        "unavailable_runtime_initializer_count": 1,
        "unavailable_runtime_export_count": (
            INSTALLED_IMPORT_UNAVAILABLE_RUNTIME_EXPORT_COUNT
        ),
        "optional_prefixes_loaded": [],
        "audit_denied_event_count": 0,
        "blocked_undeclared_import_attempts": blocked_undeclared_import_attempts,
        "denied_audit_event_policy": list(INSTALLED_IMPORT_DENIED_AUDIT_EVENTS),
        "dependency_runtime_modules_without_file_origin": (originless_runtime_modules),
        "dependency_runtime_module_aliases": [
            json.loads(alias) for alias in dependency_runtime_module_aliases
        ],
        "startup": {
            **root_discovery,
            "explicit_import_roots": _normalize_installed_import_explicit_roots(
                explicit_import_roots,
                environment_root=environment_root,
            ),
        },
        "per_module_timeout_seconds": INSTALLED_IMPORT_PROBE_TIMEOUT_SECONDS,
        "outcome_manifest_sha256": _installed_import_outcome_manifest_sha256(
            observations
        ),
        "third_party_dependencies": dependency_observations,
        "modules": list(observations),
    }


def _require_installed_import_outcome_equality(
    direct_source: dict[str, object],
    sdist_derived: dict[str, object],
) -> dict[str, bool]:
    """Require exact normalized installed-import and startup receipts."""

    for field in (
        "outcome_manifest_sha256",
        "modules",
        "third_party_dependencies",
        "startup",
    ):
        if direct_source.get(field) != sdist_derived.get(field):
            raise DistributionValidationError(
                "direct-source and sdist-derived installed import outcomes differ"
            )
    return {
        "direct_source_to_sdist_derived_install": True,
        "direct_source_to_sdist_derived_startup": True,
    }


_QUALIFICATION_STATE_CONFORMANCE_PROBE = r"""
import importlib
import importlib.metadata
import json
from pathlib import Path
import sys

mode = sys.argv[1]
if mode == "source":
    import_root = Path(sys.argv[2]).resolve(strict=True)
    sys.path.insert(0, str(import_root))
elif mode == "installed":
    if sys.argv[2] != "-":
        raise RuntimeError("installed qualification probe received an import root")
    distribution = importlib.metadata.distribution("spirallens")
    import_root = Path(distribution.locate_file("")).resolve(strict=True)
else:
    raise RuntimeError("qualification probe received an unknown mode")

from spirallens.core import canonical_json_bytes, parse_canonical_json, sha256_bytes
from spirallens.qualification import GateResult, QualificationGateId, QualificationState
from spirallens.qualification.common import EvaluationUnit

origin_modules = {
    name: importlib.import_module(name)
    for name in (
        "spirallens",
        "spirallens.core",
        "spirallens.core.canonical",
        "spirallens.qualification",
        "spirallens.qualification.common",
        "spirallens.qualification.contracts",
    )
}

fixtures = (
    ("pass", 1, 0, 0, 1, 0, 0, 0, ()),
    ("fail", 1, 0, 0, 0, 1, 0, 0, ("synthetic-failure",)),
    (
        "insufficient",
        0,
        1,
        0,
        0,
        0,
        1,
        0,
        ("synthetic-insufficient",),
    ),
    ("not_run", 0, 0, 1, 0, 0, 0, 1, ("synthetic-not-run",)),
)

states = []
for (
    state_name,
    evaluable_count,
    attempt_insufficient_count,
    attempt_not_run_count,
    pass_count,
    fail_count,
    insufficient_count,
    not_run_count,
    reason_codes,
) in fixtures:
    gate = GateResult(
        gate_id=QualificationGateId.D0,
        state=QualificationState(state_name),
        evaluation_unit=EvaluationUnit.PHANTOM_INSTANCE,
        attempted_count=1,
        evaluable_count=evaluable_count,
        attempt_insufficient_count=attempt_insufficient_count,
        attempt_not_run_count=attempt_not_run_count,
        pass_count=pass_count,
        fail_count=fail_count,
        fail_graph_dependence_count=0,
        insufficient_count=insufficient_count,
        not_run_count=not_run_count,
        reason_codes=reason_codes,
    )
    canonical_bytes = canonical_json_bytes(gate.to_dict())
    reparsed = parse_canonical_json(canonical_bytes)
    reloaded = GateResult.from_dict(reparsed)
    rerendered = canonical_json_bytes(reloaded.to_dict())
    if (
        type(reloaded) is not GateResult
        or reloaded != gate
        or rerendered != canonical_bytes
        or reloaded.state.value != state_name
        or reloaded.claim_scope.value != "engine-and-protocol-contracts"
        or (state_name != "pass" and reloaded.state is QualificationState.PASS)
    ):
        raise RuntimeError("qualification state changed during canonical round trip")
    states.append(
        {
            "canonical_json": canonical_bytes.decode("utf-8"),
            "canonical_sha256": sha256_bytes(canonical_bytes),
            "claim_scope": reloaded.claim_scope.value,
            "state": reloaded.state.value,
        }
    )

module_origins = {}
for name, module in sorted(sys.modules.items()):
    if name != "spirallens" and not name.startswith("spirallens."):
        continue
    origin_value = getattr(module, "__file__", None)
    if not isinstance(origin_value, str):
        raise RuntimeError(f"loaded SpiralLens module has no origin: {name}")
    origin = Path(origin_value).resolve(strict=True)
    if not origin.is_relative_to(import_root):
        raise RuntimeError(f"loaded SpiralLens module escaped the intended root: {name}")
for name, module in origin_modules.items():
    module_origins[name] = (
        Path(module.__file__).resolve(strict=True).relative_to(import_root).as_posix()
    )

print(
    json.dumps(
        {
            "import_root": str(import_root),
            "module_origins": module_origins,
            "schema_version": "spirallens.qualification-state-conformance.v0.1",
            "states": states,
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


_INSTALLED_ORDERED_EXPORT_PROBE = r"""
import base64
import importlib.metadata
import json
from pathlib import Path, PurePosixPath
import stat
import sys

distribution = importlib.metadata.distribution("spirallens")
files = distribution.files
if files is None:
    raise RuntimeError("installed distribution omitted its file inventory")
distribution_root = Path(distribution.locate_file("")).resolve(strict=True)
initializer_sources = {}
for item in files:
    value = str(item)
    path = PurePosixPath(value)
    if path.name != "__init__.py" or any(
        part.endswith(".dist-info") for part in path.parts
    ):
        continue
    located = Path(distribution.locate_file(item))
    try:
        mode = located.lstat().st_mode
    except OSError as error:
        raise RuntimeError(f"cannot inspect installed initializer {value!r}") from error
    if not stat.S_ISREG(mode):
        raise RuntimeError(f"installed initializer is not ordinary: {value!r}")
    resolved = located.resolve(strict=True)
    try:
        resolved.relative_to(distribution_root)
    except ValueError as error:
        raise RuntimeError(f"installed initializer escapes distribution root: {value!r}") from error
    source = located.read_bytes()
    if len(source) > 1024 * 1024:
        raise RuntimeError(f"installed initializer exceeds its size bound: {value!r}")
    initializer_sources[value] = base64.b64encode(source).decode("ascii")

print(
    json.dumps(
        {
            "distribution_root": str(distribution_root),
            "initializer_sources_base64": initializer_sources,
            "spirallens_modules_loaded": sorted(
                name
                for name in sys.modules
                if name == "spirallens" or name.startswith("spirallens.")
            ),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
)
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


def _parse_qualification_state_conformance_probe_output(
    output: str,
    *,
    import_root: Path,
) -> dict[str, object]:
    try:
        value = json.loads(
            output,
            object_pairs_hook=_reject_duplicate_json_object,
        )
    except (json.JSONDecodeError, ValueError) as error:
        raise DistributionValidationError(
            "qualification state conformance probe did not emit canonical JSON"
        ) from error
    if not isinstance(value, dict) or set(value) != {
        "import_root",
        "module_origins",
        "schema_version",
        "states",
    }:
        raise DistributionValidationError(
            "qualification state conformance probe returned invalid fields"
        )
    if value["schema_version"] != QUALIFICATION_STATE_CONFORMANCE_SCHEMA_VERSION:
        raise DistributionValidationError(
            "qualification state conformance probe returned the wrong schema"
        )
    observed_root_value = value["import_root"]
    if not isinstance(observed_root_value, str):
        raise DistributionValidationError(
            "qualification state conformance probe omitted its import root"
        )
    observed_root = Path(observed_root_value).resolve()
    import_root = import_root.resolve()
    if observed_root != import_root and not observed_root.is_relative_to(import_root):
        raise DistributionValidationError(
            "qualification state conformance import root escaped its intended root"
        )
    origins = value["module_origins"]
    if not isinstance(origins, dict) or any(
        not isinstance(name, str) or not isinstance(origin, str)
        for name, origin in origins.items()
    ):
        raise DistributionValidationError(
            "qualification state conformance probe returned invalid origins"
        )
    if set(origins) != set(QUALIFICATION_STATE_MODULE_ORIGINS):
        raise DistributionValidationError(
            "qualification state conformance probe returned an unexpected origin set"
        )
    for module, relative in QUALIFICATION_STATE_MODULE_ORIGINS.items():
        if origins.get(module) != relative:
            raise DistributionValidationError(
                f"qualification state conformance origin mismatch: {module}"
            )
    if any(
        not (observed_root / relative).resolve().is_relative_to(observed_root)
        or not (observed_root / relative).is_file()
        for relative in origins.values()
    ):
        raise DistributionValidationError(
            "qualification state conformance origin escaped its intended root"
        )
    states = value["states"]
    if not isinstance(states, list) or len(states) != len(QUALIFICATION_STATE_ORDER):
        raise DistributionValidationError(
            "qualification state conformance probe returned the wrong state count"
        )
    normalized_states: list[dict[str, str]] = []
    for expected_state, state in zip(QUALIFICATION_STATE_ORDER, states, strict=True):
        if not isinstance(state, dict) or set(state) != {
            "canonical_json",
            "canonical_sha256",
            "claim_scope",
            "state",
        }:
            raise DistributionValidationError(
                "qualification state conformance probe returned invalid state fields"
            )
        canonical_json = state["canonical_json"]
        canonical_sha256 = state["canonical_sha256"]
        if (
            state["state"] != expected_state
            or state["claim_scope"] != "engine-and-protocol-contracts"
            or not isinstance(canonical_json, str)
            or not isinstance(canonical_sha256, str)
            or hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
            != canonical_sha256
            or canonical_sha256 != QUALIFICATION_STATE_CANONICAL_SHA256[expected_state]
        ):
            raise DistributionValidationError(
                "qualification state conformance probe changed state or canonical bytes"
            )
        try:
            parsed = json.loads(
                canonical_json,
                object_pairs_hook=_reject_duplicate_json_object,
            )
        except (json.JSONDecodeError, ValueError) as error:
            raise DistributionValidationError(
                "qualification state conformance probe returned invalid state JSON"
            ) from error
        if (
            not isinstance(parsed, dict)
            or parsed.get("state") != expected_state
            or parsed.get("claim_scope") != "engine-and-protocol-contracts"
            or json.dumps(
                parsed,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )
            != canonical_json
        ):
            raise DistributionValidationError(
                "qualification state conformance probe returned noncanonical state JSON"
            )
        normalized_states.append(state)
    return {
        "module_origins": {
            module: origins[module] for module in QUALIFICATION_STATE_MODULE_ORIGINS
        },
        "schema_version": QUALIFICATION_STATE_CONFORMANCE_SCHEMA_VERSION,
        "states": normalized_states,
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


def _parse_installed_ordered_export_probe_output(
    output: str,
    *,
    environment_root: Path,
    classification: dict[str, object],
    artifact_kind: str,
) -> dict[str, object]:
    """Verify static initializer bytes returned by one fresh installation."""

    try:
        value = json.loads(output, object_pairs_hook=_reject_duplicate_json_object)
    except (json.JSONDecodeError, ValueError) as error:
        raise DistributionValidationError(
            "installed ordered export probe did not emit duplicate-free JSON"
        ) from error
    if not isinstance(value, dict) or set(value) != {
        "distribution_root",
        "initializer_sources_base64",
        "spirallens_modules_loaded",
    }:
        raise DistributionValidationError(
            "installed ordered export probe has unexpected fields"
        )
    if value.get("spirallens_modules_loaded") != []:
        raise DistributionValidationError(
            "installed ordered export probe imported SpiralLens modules"
        )
    raw_root = value.get("distribution_root")
    if not isinstance(raw_root, str):
        raise DistributionValidationError(
            "installed ordered export probe omitted its distribution root"
        )
    distribution_root = Path(raw_root).resolve()
    environment_root = environment_root.resolve()
    try:
        relative_root = distribution_root.relative_to(environment_root)
    except ValueError as error:
        raise DistributionValidationError(
            f"{artifact_kind} ordered export probe resolved outside its fresh "
            "environment"
        ) from error
    raw_sources = value.get("initializer_sources_base64")
    if not isinstance(raw_sources, dict) or any(
        not isinstance(initializer, str) or not isinstance(source, str)
        for initializer, source in raw_sources.items()
    ):
        raise DistributionValidationError(
            "installed ordered export probe returned invalid initializer sources"
        )
    sources: dict[str, bytes] = {}
    for initializer, encoded in raw_sources.items():
        _require_safe_archive_member_path(initializer, artifact_kind=artifact_kind)
        try:
            source = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError) as error:
            raise DistributionValidationError(
                f"installed ordered export probe returned invalid base64 for "
                f"{initializer!r}"
            ) from error
        if len(source) > _MAX_INITIALIZER_BYTES:
            raise DistributionValidationError(
                f"installed initializer {initializer!r} exceeds its size bound"
            )
        sources[initializer] = source
    receipt = _require_ordered_export_state(
        sources,
        classification=classification,
        artifact_kind=artifact_kind,
    )
    receipt.update(
        {
            "distribution_root": relative_root.as_posix(),
            "spirallens_modules_imported": False,
        }
    )
    return receipt


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
    ordered_export_classification = _load_ordered_export_classification(
        source_root,
        python_member_classification=python_member_classification,
    )
    installed_import_classification = _load_installed_import_classification(
        source_root,
        python_member_classification=python_member_classification,
        ordered_export_classification=ordered_export_classification,
    )
    python_source_inventory = _classify_source_python_members(
        source_root,
        classification=python_member_classification,
        ordered_export_classification=ordered_export_classification,
    )
    source_ordered_export_inventory = python_source_inventory.pop(
        "ordered_export_inventory"
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
        source_qualification_probe = _run(
            (
                sys.executable,
                "-P",
                "-B",
                "-c",
                _QUALIFICATION_STATE_CONFORMANCE_PROBE,
                "source",
                str(staged_source / "src"),
            ),
            cwd=neutral_cwd,
            env=_clean_subprocess_environment(exclude_user_site=False),
        )
        source_qualification_conformance = (
            _parse_qualification_state_conformance_probe_output(
                source_qualification_probe.stdout,
                import_root=staged_source / "src",
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
            ordered_export_classification=ordered_export_classification,
        )
        direct_ordered_export_inventory = direct_python_inventory.pop(
            "ordered_export_inventory"
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
            ordered_export_classification=ordered_export_classification,
        )
        sdist_ordered_export_inventory = sdist_python_inventory.pop(
            "ordered_export_inventory"
        )
        sdist_classification_manifest = _require_sdist_classification_manifest(
            sdist,
            expected_sha256=str(python_member_classification["manifest_sha256"]),
        )
        ordered_export_manifest_bytes = ordered_export_classification["manifest_bytes"]
        assert isinstance(ordered_export_manifest_bytes, bytes)
        sdist_ordered_export_manifest = _require_sdist_exact_file(
            sdist,
            relative=ORDERED_EXPORT_CLASSIFICATION_PATH,
            expected_bytes=ordered_export_manifest_bytes,
            label="ordered export classification manifest",
        )
        installed_import_manifest_bytes = installed_import_classification[
            "manifest_bytes"
        ]
        assert isinstance(installed_import_manifest_bytes, bytes)
        sdist_installed_import_manifest = _require_sdist_exact_file(
            sdist,
            relative=INSTALLED_IMPORT_CLASSIFICATION_PATH,
            expected_bytes=installed_import_manifest_bytes,
            label="installed import classification manifest",
        )
        _require_sdist_exact_file(
            sdist,
            relative="distribution/_installed_import_policy.py",
            expected_bytes=_POLICY_BYTES,
            label="installed import policy",
        )
        sdist_separation = _require_zero_repository_experiment_members(
            _classify_repository_experiment_sdist_members(sdist),
            artifact_kind="sdist",
        )
        extracted_source = _extract_sdist(sdist, extracted_dir)
        sdist_test_surface = _require_absent_sdist_test_surface(extracted_source)
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
            ordered_export_classification=ordered_export_classification,
        )
        sdist_wheel_ordered_export_inventory = sdist_wheel_python_inventory.pop(
            "ordered_export_inventory"
        )
        if (
            direct_python_inventory["members"]
            != sdist_wheel_python_inventory["members"]
        ):
            raise DistributionValidationError(
                "direct-source and sdist-derived wheels differ in observed Python members"
            )
        source_initializer_bytes_sha256 = source_ordered_export_inventory[
            "initializer_bytes_sha256"
        ]
        for artifact_kind, inventory in (
            ("sdist", sdist_ordered_export_inventory),
            ("direct-source wheel", direct_ordered_export_inventory),
            ("sdist-derived wheel", sdist_wheel_ordered_export_inventory),
        ):
            if inventory["initializer_bytes_sha256"] != source_initializer_bytes_sha256:
                raise DistributionValidationError(
                    f"{artifact_kind} package initializer bytes differ from source"
                )
        sdist_wheel_separation = _require_zero_repository_experiment_members(
            _classify_repository_experiment_members(wheel),
            artifact_kind="sdist-derived wheel",
        )
        installed_import_classification_report = {
            "base_dependencies": list(
                installed_import_classification["base_dependencies"]
            ),
            "blocked_optional_prefixes": list(
                installed_import_classification["blocked_optional_prefixes"]
            ),
            "claim_boundary": installed_import_classification["claim_boundary"],
            "classification_scope": installed_import_classification[
                "classification_scope"
            ],
            "manifest_path": installed_import_classification["manifest_path"],
            "manifest_sha256": installed_import_classification["manifest_sha256"],
            "outcome_counts": {
                role: len(modules)
                for role, modules in installed_import_classification["outcomes"].items()
            },
            "schema_version": installed_import_classification["schema_version"],
            "sdist_manifest": sdist_installed_import_manifest,
        }
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
            ordered_package_export_inventory={
                "classification": {
                    "claim_boundary": ordered_export_classification["claim_boundary"],
                    "classification_scope": ordered_export_classification[
                        "classification_scope"
                    ],
                    "export_count": ordered_export_classification["export_count"],
                    "manifest_path": ordered_export_classification["manifest_path"],
                    "manifest_sha256": ordered_export_classification["manifest_sha256"],
                    "package_count": ordered_export_classification["package_count"],
                    "schema_version": ordered_export_classification["schema_version"],
                    "sdist_manifest": sdist_ordered_export_manifest,
                },
                "source_tree": source_ordered_export_inventory,
                "sdist": sdist_ordered_export_inventory,
                "direct_source_wheel": direct_ordered_export_inventory,
                "sdist_derived_wheel": sdist_wheel_ordered_export_inventory,
                "equality": {
                    "source_to_sdist": True,
                    "source_to_direct_source_wheel": True,
                    "source_to_sdist_derived_wheel": True,
                    "direct_source_to_sdist_derived_wheel": True,
                },
            },
        )
        installed_import_conformance = {
            "classification": installed_import_classification_report,
        }

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
        installed_ordered_export_probe = _run(
            (
                str(venv_python),
                "-P",
                "-c",
                _INSTALLED_ORDERED_EXPORT_PROBE,
            ),
            cwd=neutral_cwd,
            env=environment,
        )
        installed_ordered_export_inventory = (
            _parse_installed_ordered_export_probe_output(
                installed_ordered_export_probe.stdout,
                environment_root=environment_root,
                classification=ordered_export_classification,
                artifact_kind="sdist-derived fresh install",
            )
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
        direct_installed_ordered_export_probe = _run(
            (
                str(direct_scientific_python),
                "-P",
                "-c",
                _INSTALLED_ORDERED_EXPORT_PROBE,
            ),
            cwd=neutral_cwd,
            env=direct_scientific_environment,
        )
        direct_installed_ordered_export_inventory = (
            _parse_installed_ordered_export_probe_output(
                direct_installed_ordered_export_probe.stdout,
                environment_root=direct_scientific_environment_root,
                classification=ordered_export_classification,
                artifact_kind="direct-source fresh install",
            )
        )
        direct_installed_import_outcomes = _probe_installed_import_outcomes(
            python=direct_scientific_python,
            environment_root=direct_scientific_environment_root,
            neutral_cwd=neutral_cwd,
            environment=direct_scientific_environment,
            classification=installed_import_classification,
            ordered_export_classification=ordered_export_classification,
            artifact_kind="direct-source fresh install",
        )
        direct_qualification_probe = _run(
            (
                str(direct_scientific_python),
                "-P",
                "-B",
                "-c",
                _QUALIFICATION_STATE_CONFORMANCE_PROBE,
                "installed",
                "-",
            ),
            cwd=neutral_cwd,
            env=direct_scientific_environment,
        )
        direct_qualification_conformance = (
            _parse_qualification_state_conformance_probe_output(
                direct_qualification_probe.stdout,
                import_root=direct_scientific_environment_root,
            )
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
        sdist_installed_import_outcomes = _probe_installed_import_outcomes(
            python=scientific_python,
            environment_root=scientific_environment_root,
            neutral_cwd=neutral_cwd,
            environment=scientific_environment,
            classification=installed_import_classification,
            ordered_export_classification=ordered_export_classification,
            artifact_kind="sdist-derived fresh install",
        )
        sdist_qualification_probe = _run(
            (
                str(scientific_python),
                "-P",
                "-B",
                "-c",
                _QUALIFICATION_STATE_CONFORMANCE_PROBE,
                "installed",
                "-",
            ),
            cwd=neutral_cwd,
            env=scientific_environment,
        )
        sdist_qualification_conformance = (
            _parse_qualification_state_conformance_probe_output(
                sdist_qualification_probe.stdout,
                import_root=scientific_environment_root,
            )
        )
        if not (
            source_qualification_conformance
            == direct_qualification_conformance
            == sdist_qualification_conformance
        ):
            raise DistributionValidationError(
                "qualification state conformance differs across source and wheel routes"
            )
        qualification_state_conformance = {
            "claim_boundary": (
                "synthetic model-free state preservation only; no scientific, "
                "authority, compatibility, portability, public API, or LIB-L0 grant"
            ),
            "direct_source_install": direct_qualification_conformance,
            "equality": {
                "direct_source_to_sdist_derived_install": True,
                "source_to_direct_source_install": True,
                "source_to_sdist_derived_install": True,
            },
            "observation": "exact-four-state-canonical-round-trip",
            "schema_version": QUALIFICATION_STATE_CONFORMANCE_SCHEMA_VERSION,
            "sdist_derived_install": sdist_qualification_conformance,
            "source_tree": source_qualification_conformance,
        }
        installed_import_equality = _require_installed_import_outcome_equality(
            direct_installed_import_outcomes,
            sdist_installed_import_outcomes,
        )
        installed_import_conformance.update(
            {
                "direct_source_install": direct_installed_import_outcomes,
                "sdist_derived_install": sdist_installed_import_outcomes,
                "equality": installed_import_equality,
            }
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
        ordered_export_inventory_report = library_separation[
            "ordered_package_export_inventory"
        ]
        assert isinstance(ordered_export_inventory_report, dict)
        for artifact_kind, inventory in (
            ("direct-source fresh install", direct_installed_ordered_export_inventory),
            ("sdist-derived fresh install", installed_ordered_export_inventory),
        ):
            if inventory["initializer_bytes_sha256"] != source_initializer_bytes_sha256:
                raise DistributionValidationError(
                    f"{artifact_kind} package initializer bytes differ from source"
                )
        ordered_export_inventory_report["direct_source_install"] = (
            direct_installed_ordered_export_inventory
        )
        ordered_export_inventory_report["sdist_derived_install"] = (
            installed_ordered_export_inventory
        )
        ordered_export_equality = ordered_export_inventory_report["equality"]
        assert isinstance(ordered_export_equality, dict)
        ordered_export_equality.update(
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
                "base_dependencies_freshly_installed": False,
                "host_projected_base_dependencies": True,
                "isolated_base_dependency_environment_established": False,
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
            "installed_import_conformance": installed_import_conformance,
            "library_separation": library_separation,
            "qualification_state_conformance": qualification_state_conformance,
            "repository_experiment_source_import_inspection": (
                source_import_inspection
            ),
            "repository_experiment_stale_build_rejection": stale_build_rejection,
            "repository_experiment_install_inspections": {
                "direct_source_wheel": direct_absence_inspection,
                "sdist_derived_wheel": sdist_absence_inspection,
            },
            "scientific_surface_inspection": scientific_inspection,
            "sdist_test_surface": sdist_test_surface,
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
