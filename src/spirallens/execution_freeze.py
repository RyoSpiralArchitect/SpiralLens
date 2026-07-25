"""Fail-closed execution-freeze validation for subject neighbor audits."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import copy
import ctypes
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys
import tempfile
from typing import Any

import numpy as np
import yaml

from spirallens import __version__ as SPIRALLENS_VERSION
from spirallens.neighbors.contracts import (
    NeighborBackendDescriptor,
    canonical_json_sha256,
)


EXECUTION_FREEZE_SCHEMA_VERSION_V0_1 = (
    "spirallens.subject-audit-freeze.v0.1"
)
EXECUTION_FREEZE_SCHEMA_VERSION_V0_2 = (
    "spirallens.subject-audit-freeze.v0.2"
)
EXECUTION_FREEZE_SCHEMA_VERSION_V0_3 = (
    "spirallens.subject-audit-freeze.v0.3"
)
# Kept as the historical default for callers that imported this name before
# schema dispatch existed.
EXECUTION_FREEZE_SCHEMA_VERSION = EXECUTION_FREEZE_SCHEMA_VERSION_V0_1
SUPPORTED_EXECUTION_FREEZE_SCHEMA_VERSIONS = frozenset(
    {
        EXECUTION_FREEZE_SCHEMA_VERSION_V0_1,
        EXECUTION_FREEZE_SCHEMA_VERSION_V0_2,
        EXECUTION_FREEZE_SCHEMA_VERSION_V0_3,
    }
)
_QUALIFICATION_SCHEMA_VERSION_V0_1 = (
    "spirallens.faiss-hnsw-range-qualification.v0.1"
)
_QUALIFICATION_SCHEMA_VERSION_V0_2 = (
    "spirallens.faiss-hnsw-range-qualification.v0.2"
)
_QUALIFICATION_OBSERVATION_SCHEMA_VERSION = (
    "spirallens.faiss-hnsw-qualification-predecessor-observation.v0.1"
)
_QUALIFICATION_PREDECESSOR_SCHEMA_VERSION = (
    "spirallens.subject-audit-qualification-predecessor.v0.1"
)
_V0_2_PREDECESSOR_PROTOCOL_SHA256 = (
    "296609585f4f165e44a235d6a8af9416b840477313a63013414abb1ed9a55661"
)
_V0_2_PREDECESSOR_FREEZE_SHA256 = (
    "ffef5e0ddc749c942962afb22509e1ec5726847f41ed99bd294adb409b6ba111"
)
_V0_2_PREDECESSOR_MARKER_SHA256 = (
    "7255ca9e9c905a128348f7fc41ebf458c7e7feb233d3adcd5daebbaedf8be5cb"
)
_V0_3_OBSERVED_QUALIFICATION_SHA256 = (
    "572bed090750a314d4415eeaaef3c2f96662a08442437616c9dc85823c2b33cb"
)
_V0_3_OBSERVED_FIXTURE_SHA256 = (
    "5d365820e09ce33683bcf9d003a64f842bad89055a62088b64c3b6f8d28df58e"
)
_V0_3_OBSERVED_SEARCH_SHA256 = (
    "b78b2f47d875be459dc451568876416339ad2f609c19087ca8a92e702d9b70ce"
)
_V0_3_OBSERVED_SOURCE_COMMIT = (
    "dca11d116c2d5218d586bb5d089460d28e59e7d8"
)
_V0_3_OBSERVED_SOURCE_TREE = (
    "d7003c09037cb34b9147a2992a4ae74c88f2e907"
)
_V0_3_OBSERVATION_RELATIVE_PATH = (
    "protocols/"
    "pythia70_slot_only_001_layer0_faiss_range_qualification_"
    "v0_1_observation.yaml"
)
_V0_3_ACTIVE_QUALIFICATION_RELATIVE_PATH = (
    "protocols/"
    "pythia70_slot_only_001_layer0_faiss_range_qualification_v0_2.json"
)
_V0_3_LOST_QUALIFICATION_RELATIVE_PATH = (
    "protocols/"
    "pythia70_slot_only_001_layer0_faiss_range_qualification_v0_1.json"
)
SELF_SHA256_PLACEHOLDER = "<SELF_SHA256>"
_CAPABILITY_TOKEN = object()


class ValidatedExecutionFreeze:
    """Capability issued only after a complete execution-freeze preflight."""

    __slots__ = (
        "_backend_contract",
        "_sha256",
        "_revalidate",
        "_sealed",
        "_token",
        "_worker_runtime",
    )

    def __init__(
        self,
        *,
        token: object,
        sha256: str,
        revalidate: Callable[[], None],
        worker_runtime: Mapping[str, str],
        backend_contract: Mapping[str, object] | None = None,
    ) -> None:
        if token is not _CAPABILITY_TOKEN:
            raise TypeError(
                "ValidatedExecutionFreeze cannot be constructed directly"
            )
        object.__setattr__(self, "_token", token)
        object.__setattr__(
            self,
            "_sha256",
            _require_sha256(
                sha256,
                label="execution freeze SHA-256",
            ),
        )
        object.__setattr__(self, "_revalidate", revalidate)
        object.__setattr__(
            self,
            "_worker_runtime",
            dict(worker_runtime),
        )
        object.__setattr__(
            self,
            "_backend_contract",
            (
                None
                if backend_contract is None
                else copy.deepcopy(dict(backend_contract))
            ),
        )
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError(
                "ValidatedExecutionFreeze is immutable"
            )
        object.__setattr__(self, name, value)

    @property
    def sha256(self) -> str:
        return self._sha256

    def revalidate(self) -> None:
        if self._token is not _CAPABILITY_TOKEN:
            raise TypeError("execution-freeze capability is invalid")
        self._revalidate()

    def validate_subject_backend(
        self,
        descriptor: NeighborBackendDescriptor,
    ) -> None:
        if (
            self._token is not _CAPABILITY_TOKEN
            or not isinstance(descriptor, NeighborBackendDescriptor)
        ):
            raise TypeError("subject backend descriptor is invalid")
        runtime = dict(descriptor.runtime)
        if runtime != self._worker_runtime:
            raise ValueError(
                "subject worker runtime differs from the execution freeze"
            )
        expected = self._backend_contract
        if expected is not None:
            parameters = dict(descriptor.parameters)
            expected_parameters = expected.get("parameters")
            if (
                descriptor.backend_id != expected.get("backend_id")
                or descriptor.backend_version
                != expected.get("backend_version")
                or not isinstance(expected_parameters, Mapping)
                or any(
                    parameters.get(key) != value
                    for key, value in expected_parameters.items()
                )
            ):
                raise ValueError(
                    "subject backend differs from the qualified execution "
                    "freeze"
                )

    def worker_runtime_contract(self) -> dict[str, str]:
        if self._token is not _CAPABILITY_TOKEN:
            raise TypeError("execution-freeze capability is invalid")
        return dict(self._worker_runtime)


def validated_execution_freeze_sha256(
    capability: object,
) -> str:
    """Extract a digest only from a module-issued freeze capability."""

    if (
        not isinstance(capability, ValidatedExecutionFreeze)
        or capability._token is not _CAPABILITY_TOKEN
    ):
        raise TypeError(
            "manifest audit requires a validated execution-freeze capability"
        )
    return capability.sha256


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _read_repo_regular_file(
    path: Path,
    *,
    repo_root: Path,
    label: str,
) -> tuple[bytes, str]:
    """Read one repo file without accepting symlink indirection."""

    if not path.is_absolute():
        raise ValueError(f"{label} path must be absolute")
    root = repo_root.resolve()
    lexical_path = path.absolute()
    try:
        relative = lexical_path.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{label} must be inside the repository") from error
    if not relative.parts:
        raise ValueError(f"{label} must name a regular file")
    current = root
    for part in relative.parts:
        current = current / part
        try:
            metadata = current.lstat()
        except FileNotFoundError as error:
            raise ValueError(f"{label} is missing") from error
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"{label} path must not contain symlinks")
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"{label} must be a regular file")
    payload = lexical_path.read_bytes()
    return payload, relative.as_posix()


def _require_sha256(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _require_git_object(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be a full lowercase Git object ID")
    return value


def _distribution_files(distribution_name: str) -> tuple[Path, ...]:
    distribution = metadata.distribution(distribution_name)
    files = distribution.files
    if files is None:
        raise ValueError(
            f"{distribution_name} does not expose installed file records"
        )
    paths = tuple(
        Path(distribution.locate_file(relative))
        for relative in sorted(files, key=lambda value: str(value))
    )
    missing = [path for path in paths if not path.is_file()]
    if missing:
        raise ValueError(
            f"{distribution_name} installed file is missing: {missing[0]}"
        )
    return paths


def distribution_content_sha256(distribution_name: str) -> str:
    """Hash the installed files declared by one distribution RECORD."""

    distribution = metadata.distribution(distribution_name)
    files = distribution.files
    if files is None:
        raise ValueError(
            f"{distribution_name} does not expose installed file records"
        )
    digest = hashlib.sha256()
    digest.update(
        b"spirallens.installed-distribution-content.v0.1\0"
    )
    for relative in sorted(files, key=lambda value: str(value)):
        path = Path(distribution.locate_file(relative))
        if not path.is_file():
            raise ValueError(
                f"{distribution_name} installed file is missing: "
                f"{relative}"
            )
        relative_bytes = str(relative).encode("utf-8")
        digest.update(len(relative_bytes).to_bytes(8, "big"))
        digest.update(relative_bytes)
        digest.update(path.stat().st_size.to_bytes(8, "big"))
        with path.open("rb") as handle:
            while chunk := handle.read(8 * 1024 * 1024):
                digest.update(chunk)
    return digest.hexdigest()


def process_image_path() -> Path:
    """Return the current process image rather than the launcher symlink."""

    if sys.platform == "darwin":
        library = ctypes.CDLL("/usr/lib/libproc.dylib")
        buffer = ctypes.create_string_buffer(4096)
        result = library.proc_pidpath(
            os.getpid(),
            buffer,
            ctypes.sizeof(buffer),
        )
        if result <= 0:
            raise RuntimeError("proc_pidpath failed for the Python process")
        return Path(os.fsdecode(buffer.value))
    proc_path = Path("/proc/self/exe")
    if proc_path.exists():
        return proc_path.resolve()
    return Path(sys.orig_argv[0]).resolve()


def current_worker_runtime_contract(
    execution_freeze_sha256: str | None,
) -> dict[str, str]:
    """Probe the exact Faiss runtime in one fresh reporter subprocess."""

    freeze_digest = (
        None
        if execution_freeze_sha256 is None
        else _require_sha256(
            execution_freeze_sha256,
            label="execution_freeze_sha256",
        )
    )
    allowed_environment = {
        "PYTHONPATH",
        "PYTHONDONTWRITEBYTECODE",
        "PYTHONPYCACHEPREFIX",
        "PATH",
        "LANG",
        "LC_ALL",
        "TMPDIR",
    }
    environment = {
        key: value
        for key, value in os.environ.items()
        if key in allowed_environment
    }
    environment.setdefault("PATH", "/usr/bin:/bin:/usr/sbin:/sbin")
    environment.setdefault("LANG", "C")
    environment.setdefault("LC_ALL", "C")
    environment.setdefault("TMPDIR", tempfile.gettempdir())
    command = [
        sys.executable,
        "-m",
        "spirallens.neighbors._faiss_runtime_worker",
    ]
    if freeze_digest is not None:
        command.extend(
            ["--execution-freeze-sha256", freeze_digest]
        )
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        env=environment,
        timeout=120,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        stdout = completed.stdout.decode("utf-8", errors="replace").strip()
        detail = stderr or stdout
        raise RuntimeError(
            "Faiss runtime reporter failed"
            + (f": {detail}" if detail else "")
        )

    duplicate_key = False

    def reject_duplicate_keys(
        pairs: list[tuple[str, object]],
    ) -> dict[str, object]:
        nonlocal duplicate_key
        payload: dict[str, object] = {}
        for key, value in pairs:
            if key in payload:
                duplicate_key = True
            payload[key] = value
        return payload

    try:
        raw = json.loads(
            completed.stdout,
            object_pairs_hook=reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(
            "Faiss runtime reporter returned invalid JSON"
        ) from error
    expected_fields = {
        "faiss_compile_options",
        "faiss_distribution_sha256",
        "faiss_hnsw_source_sha256",
        "faiss_import_file",
        "faiss_import_sha256",
        "faiss_native_file",
        "faiss_native_sha256",
        "faiss_runtime_worker_source_sha256",
        "faiss_version",
        "faiss_worker_source_sha256",
        "machine",
        "numpy_distribution_sha256",
        "numpy_import_file",
        "numpy_import_sha256",
        "numpy_version",
        "process_image",
        "process_image_sha256",
        "python_version",
        "system",
    }
    if freeze_digest is not None:
        expected_fields.add("execution_freeze_sha256")
    if (
        duplicate_key
        or not isinstance(raw, dict)
        or set(raw) != expected_fields
        or any(
            not isinstance(key, str)
            or not key
            or not isinstance(value, str)
            or not value
            for key, value in raw.items()
        )
    ):
        raise ValueError("Faiss runtime reporter contract is invalid")
    canonical = json.dumps(
        raw,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if canonical != completed.stdout:
        raise ValueError(
            "Faiss runtime reporter did not return canonical JSON"
        )
    if (
        freeze_digest is not None
        and raw["execution_freeze_sha256"] != freeze_digest
    ):
        raise ValueError(
            "Faiss runtime reporter freeze digest differs"
        )
    return {str(key): str(value) for key, value in raw.items()}


def _git_environment() -> dict[str, str]:
    return {
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
    }


def _git_command(
    git_executable: Path,
    root: Path,
    *arguments: str,
) -> list[str]:
    return [
        str(git_executable),
        "--no-replace-objects",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.untrackedCache=false",
        "-C",
        str(root),
        *arguments,
    ]


def _git_output(
    git_executable: Path,
    root: Path,
    *arguments: str,
) -> str:
    result = subprocess.run(
        _git_command(git_executable, root, *arguments),
        check=True,
        capture_output=True,
        text=True,
        env=_git_environment(),
    )
    return result.stdout.strip()


def _git_bytes(
    git_executable: Path,
    root: Path,
    *arguments: str,
) -> bytes:
    result = subprocess.run(
        _git_command(git_executable, root, *arguments),
        check=True,
        capture_output=True,
        env=_git_environment(),
    )
    return result.stdout


def _validate_git_index_records(records: list[bytes]) -> None:
    if any(
        not record.startswith(b"H ")
        for record in records
    ):
        raise ValueError(
            "execution freeze rejects assume-unchanged or skip-worktree "
            "index flags"
        )


def _require_mapping(
    value: object,
    *,
    label: str,
    fields: set[str],
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{label} fields differ from the freeze contract")
    return value


def _qualified_freeze_profile(
    schema_version: object,
) -> dict[str, str] | None:
    """Return one exact qualified-freeze profile without rewriting history."""

    if schema_version == EXECUTION_FREEZE_SCHEMA_VERSION_V0_2:
        return {
            "freeze_id": (
                "pythia70-slot-only-001-layer0-subject-audit-v0.2"
            ),
            "freeze_filename_version": "v0_2",
            "neighbor_parent_filename": "pythia_neighbor_v0_3.yaml",
            "neighbor_frozen_filename": (
                "pythia70_slot_only_001_layer0_neighbor_v0_3.yaml"
            ),
            "neighbor_schema_version": (
                "spirallens.neighbor-audit-protocol.v0.3"
            ),
            "qualification_schema_version": (
                _QUALIFICATION_SCHEMA_VERSION_V0_1
            ),
            # v0.2 historically accepted the in-repository path bound by the
            # frozen protocol. Keep that behavior intact.
            "qualification_relative_path": "",
            "output_filename": "layer-0-neighbor-audit-v0-3.json",
        }
    if schema_version == EXECUTION_FREEZE_SCHEMA_VERSION_V0_3:
        return {
            "freeze_id": (
                "pythia70-slot-only-001-layer0-subject-audit-v0.3"
            ),
            "freeze_filename_version": "v0_3",
            "neighbor_parent_filename": "pythia_neighbor_v0_4.yaml",
            "neighbor_frozen_filename": (
                "pythia70_slot_only_001_layer0_neighbor_v0_4.yaml"
            ),
            "neighbor_schema_version": (
                "spirallens.neighbor-audit-protocol.v0.4"
            ),
            "qualification_schema_version": (
                _QUALIFICATION_SCHEMA_VERSION_V0_2
            ),
            "qualification_relative_path": (
                _V0_3_ACTIVE_QUALIFICATION_RELATIVE_PATH
            ),
            "output_filename": "layer-0-neighbor-audit-v0-4.json",
        }
    return None


def _execution_runtime_fields(schema_version: object) -> set[str]:
    """Keep historical freeze field sets exact while extending v0.3."""

    fields = {
        "executable",
        "executable_resolved",
        "executable_sha256",
        "process_image",
        "process_image_sha256",
        "python_implementation",
        "python_version",
        "platform",
        "machine",
        "system",
        "spirallens_version",
        "spirallens_import_file",
        "numpy_version",
        "numpy_distribution_sha256",
        "numpy_import_file",
        "numpy_import_sha256",
        "faiss_distribution",
        "faiss_version",
        "faiss_distribution_sha256",
        "faiss_import_file",
        "faiss_import_sha256",
        "faiss_native_file",
        "faiss_native_sha256",
        "faiss_compile_options",
        "faiss_hnsw_source_sha256",
        "faiss_worker_source_sha256",
        "git_executable",
        "git_executable_sha256",
        "git_version",
    }
    if schema_version == EXECUTION_FREEZE_SCHEMA_VERSION_V0_3:
        fields.add("faiss_runtime_worker_source_sha256")
    return fields


def _load_protocol_document(
    path: Path,
    *,
    label: str,
) -> dict[str, Any]:
    document = yaml.safe_load(path.read_bytes())
    if not isinstance(document, dict):
        raise ValueError(f"{label} must contain one YAML mapping")
    return document


def _validate_candidate_protocol_lineage(
    *,
    parent: Mapping[str, Any],
    frozen: Mapping[str, Any],
    layer_index: int,
) -> None:
    expected = copy.deepcopy(dict(parent))
    expected["protocol_id"] = (
        "pythia70-slot-only-001-layer0-candidate-v0.2"
    )
    expected["status"] = "frozen"
    candidate_search = expected.get("candidate_search")
    if not isinstance(candidate_search, dict):
        raise ValueError("candidate parent protocol is invalid")
    candidate_search["layer_indices"] = [layer_index]
    if expected != dict(frozen):
        raise ValueError(
            "frozen candidate protocol exceeds its allowlisted lineage"
        )


def _validate_neighbor_protocol_lineage(
    *,
    parent: Mapping[str, Any],
    frozen: Mapping[str, Any],
    repo_root: Path,
    candidate_protocol_path: Path,
    candidate_protocol_sha256: str,
    comparison_group: str,
    global_row_key_sha256: str,
    qualification_path: Path | None = None,
    qualification_sha256: str | None = None,
    qualification_fixture_sha256: str | None = None,
) -> None:
    expected = copy.deepcopy(dict(parent))
    protocol_schema = expected.get("schema_version")
    protocol_versions = {
        "spirallens.neighbor-audit-protocol.v0.2": "v0.2",
        "spirallens.neighbor-audit-protocol.v0.3": "v0.3",
        "spirallens.neighbor-audit-protocol.v0.4": "v0.4",
    }
    qualification_schemas = {
        "spirallens.neighbor-audit-protocol.v0.3": (
            _QUALIFICATION_SCHEMA_VERSION_V0_1
        ),
        "spirallens.neighbor-audit-protocol.v0.4": (
            _QUALIFICATION_SCHEMA_VERSION_V0_2
        ),
    }
    protocol_version = protocol_versions.get(protocol_schema)
    if protocol_version is None:
        raise ValueError("neighbor parent protocol schema is invalid")
    qualification_schema = qualification_schemas.get(protocol_schema)
    qualified_protocol = qualification_schema is not None
    expected["protocol_id"] = (
        "pythia70-slot-only-001-layer0-neighbor-"
        f"{protocol_version}"
    )
    expected["status"] = "frozen"
    expected["audit_scope"] = {
        "comparison_group": comparison_group,
    }
    expected["candidate_protocol"] = {
        "path": str(candidate_protocol_path.relative_to(repo_root)),
        "sha256": candidate_protocol_sha256,
        "declared_id": (
            "pythia70-slot-only-001-layer0-candidate-v0.2"
        ),
    }
    if qualified_protocol:
        if (
            qualification_path is None
            or qualification_sha256 is None
            or qualification_fixture_sha256 is None
        ):
            raise ValueError(
                "qualified neighbor lineage lacks its receipt binding"
            )
        expected["backend_qualification"] = {
            "schema_version": qualification_schema,
            "path": str(qualification_path.relative_to(repo_root)),
            "sha256": qualification_sha256,
            "fixture_sha256": qualification_fixture_sha256,
        }
    query_sampling = expected.get("query_sampling")
    audit = expected.get("audit")
    readiness = expected.get("promotion_readiness")
    if (
        not isinstance(query_sampling, dict)
        or not isinstance(audit, dict)
        or not isinstance(readiness, dict)
    ):
        raise ValueError("neighbor parent protocol is invalid")
    query_sampling["global_row_key_sha256"] = (
        global_row_key_sha256
    )
    query_sampling.pop("binding_rule", None)
    audit["issue_persistence_receipt_on_verified_pass"] = True
    readiness["atlas_execution_bindings_frozen"] = True
    readiness["tracked_protocol_can_issue_persistence_receipt"] = True
    if qualified_protocol:
        readiness["production_shape_subprocess_qualified"] = True
    if expected != dict(frozen):
        raise ValueError(
            "frozen neighbor protocol exceeds its allowlisted lineage"
        )


def _validate_predecessor_tombstone(
    value: object,
    *,
    repo_root: Path,
    new_output_path: Path,
) -> None:
    tombstone = _require_mapping(
        value,
        label="predecessor_tombstone",
        fields={
            "schema_version",
            "protocol_path",
            "protocol_sha256",
            "execution_freeze_path",
            "execution_freeze_sha256",
            "output_path",
            "reservation_marker_sha256",
            "terminal_status",
            "exit_code",
            "stdout_outcome_observed",
            "audit_artifact_written",
            "promotion_receipt_issued",
            "recovery_sidecar_written",
            "predecessor_rerun_allowed",
            "this_is_new_remediation_protocol",
        },
    )
    protocol_path = (
        repo_root
        / "protocols"
        / "pythia70_slot_only_001_layer0_neighbor_v0_2.yaml"
    )
    freeze_path = (
        repo_root
        / "protocols"
        / "pythia70_slot_only_001_layer0_subject_audit_freeze_v0_1.yaml"
    )
    output_path = Path(
        "/Users/ryohiga/SpiralReality/spirallens/runs/"
        "pythia70-full-slot-only-001/layer-0-neighbor-audit.json"
    )
    expected = {
        "schema_version": (
            "spirallens.subject-audit-predecessor-tombstone.v0.1"
        ),
        "protocol_path": str(protocol_path),
        "protocol_sha256": _V0_2_PREDECESSOR_PROTOCOL_SHA256,
        "execution_freeze_path": str(freeze_path),
        "execution_freeze_sha256": _V0_2_PREDECESSOR_FREEZE_SHA256,
        "output_path": str(output_path),
        "reservation_marker_sha256": _V0_2_PREDECESSOR_MARKER_SHA256,
        "terminal_status": "infrastructure_abort_before_outcome",
        "exit_code": 1,
        "stdout_outcome_observed": False,
        "audit_artifact_written": False,
        "promotion_receipt_issued": False,
        "recovery_sidecar_written": False,
        "predecessor_rerun_allowed": False,
        "this_is_new_remediation_protocol": True,
    }
    if dict(tombstone) != expected or new_output_path == output_path:
        raise ValueError("execution freeze predecessor tombstone is invalid")
    protocol_bytes, _ = _read_repo_regular_file(
        protocol_path,
        repo_root=repo_root,
        label="predecessor protocol",
    )
    freeze_bytes, _ = _read_repo_regular_file(
        freeze_path,
        repo_root=repo_root,
        label="predecessor execution freeze",
    )
    if (
        hashlib.sha256(protocol_bytes).hexdigest()
        != _V0_2_PREDECESSOR_PROTOCOL_SHA256
        or hashlib.sha256(freeze_bytes).hexdigest()
        != _V0_2_PREDECESSOR_FREEZE_SHA256
        or output_path.is_symlink()
        or not output_path.is_file()
    ):
        raise ValueError("execution freeze predecessor evidence differs")
    marker_bytes = output_path.read_bytes()
    marker_lines = marker_bytes.decode("utf-8").splitlines()
    if (
        hashlib.sha256(marker_bytes).hexdigest()
        != _V0_2_PREDECESSOR_MARKER_SHA256
        or len(marker_lines) != 2
        or marker_lines[0]
        != "spirallens-neighbor-audit-reservation-v0.3"
        or not marker_lines[1].startswith("recovery=.")
    ):
        raise ValueError("execution freeze predecessor marker differs")
    recovery_path = output_path.parent / marker_lines[1].removeprefix(
        "recovery="
    )
    if recovery_path.exists() or recovery_path.is_symlink():
        raise ValueError(
            "execution freeze predecessor recovery sidecar must be absent"
        )


def _validate_qualification_predecessor(
    value: object,
    *,
    repo_root: Path,
    git_executable: Path,
    repository: str,
    branch: str,
    active_preflight_commit: str,
    active_preflight_tree: str,
    implementation_commit: str,
    active_receipt_path: Path,
    active_receipt_sha256: str,
) -> None:
    """Bind logged v0.1 evidence without claiming the lost file survived."""

    binding = _require_mapping(
        value,
        label="qualification_predecessor",
        fields={
            "schema_version",
            "observation_path",
            "observation_sha256",
            "artifact_available",
            "raw_receipt_bytes_preserved",
            "record_is_original_receipt",
            "observed_receipt_schema_version",
            "observed_receipt_sha256",
            "observed_source_implementation_commit",
            "observed_source_package_tree",
            "producer_status",
            "consumer_binding_status",
            "failure_stage",
            "subject_audit_runs_observed",
            "subject_outcome_observed",
            "audit_artifact_written",
            "promotion_receipt_issued",
            "active_binding_allowed",
            "successor_schema_version",
            "successor_path",
            "successor_sha256",
        },
    )
    observation_path = repo_root / _V0_3_OBSERVATION_RELATIVE_PATH
    observation_sha256 = _require_sha256(
        binding.get("observation_sha256"),
        label="qualification_predecessor.observation_sha256",
    )
    observation_bytes, observation_relative = _read_repo_regular_file(
        Path(str(binding.get("observation_path"))),
        repo_root=repo_root,
        label="qualification predecessor observation",
    )
    active_receipt_expected = (
        repo_root / _V0_3_ACTIVE_QUALIFICATION_RELATIVE_PATH
    )
    expected_binding = {
        "schema_version": _QUALIFICATION_PREDECESSOR_SCHEMA_VERSION,
        "observation_path": str(observation_path),
        "observation_sha256": observation_sha256,
        "artifact_available": False,
        "raw_receipt_bytes_preserved": False,
        "record_is_original_receipt": False,
        "observed_receipt_schema_version": (
            _QUALIFICATION_SCHEMA_VERSION_V0_1
        ),
        "observed_receipt_sha256": (
            _V0_3_OBSERVED_QUALIFICATION_SHA256
        ),
        "observed_source_implementation_commit": (
            _V0_3_OBSERVED_SOURCE_COMMIT
        ),
        "observed_source_package_tree": _V0_3_OBSERVED_SOURCE_TREE,
        "producer_status": "pass",
        "consumer_binding_status": "unbound_before_subject_audit",
        "failure_stage": "prepare_only_consumer_validation",
        "subject_audit_runs_observed": 0,
        "subject_outcome_observed": False,
        "audit_artifact_written": False,
        "promotion_receipt_issued": False,
        "active_binding_allowed": False,
        "successor_schema_version": _QUALIFICATION_SCHEMA_VERSION_V0_2,
        "successor_path": str(active_receipt_expected),
        "successor_sha256": active_receipt_sha256,
    }
    lost_receipt_path = repo_root / _V0_3_LOST_QUALIFICATION_RELATIVE_PATH
    if (
        dict(binding) != expected_binding
        or Path(str(binding.get("observation_path"))) != observation_path
        or observation_relative != _V0_3_OBSERVATION_RELATIVE_PATH
        or hashlib.sha256(observation_bytes).hexdigest()
        != observation_sha256
        or active_receipt_path != active_receipt_expected
        or lost_receipt_path.exists()
        or lost_receipt_path.is_symlink()
    ):
        raise ValueError(
            "qualification predecessor binding or artifact boundary differs"
        )

    observation = _load_protocol_document(
        observation_path,
        label="qualification predecessor observation",
    )
    expected_observation_fields = {
        "schema_version",
        "status",
        "qualification_schema_version",
        "observed_receipt_sha256",
        "observed_fixture_sha256",
        "observed_search_sha256",
        "observed_cold_process_runs",
        "observed_raw_hit_count_per_run",
        "observed_payload",
        "source",
        "consumer_preflight",
        "artifact_recovery",
        "authorization",
    }
    payload = observation.get("observed_payload")
    observed_source = observation.get("source")
    consumer_preflight = observation.get("consumer_preflight")
    artifact_recovery = observation.get("artifact_recovery")
    authorization = observation.get("authorization")
    if (
        set(observation) != expected_observation_fields
        or not isinstance(payload, Mapping)
        or not isinstance(observed_source, Mapping)
        or not isinstance(consumer_preflight, Mapping)
        or not isinstance(artifact_recovery, Mapping)
        or not isinstance(authorization, Mapping)
    ):
        raise ValueError(
            "qualification predecessor observation fields differ"
        )
    expected_source = {
        "repository": repository,
        "branch": branch,
        "implementation_commit": _V0_3_OBSERVED_SOURCE_COMMIT,
        "spirallens_package_tree": _V0_3_OBSERVED_SOURCE_TREE,
    }
    expected_consumer_preflight = {
        "torch_loaded_parent_process": True,
        "phase": "frozen_protocol_prepare_only",
        "status": "infrastructure_abort_before_protocol_freeze",
        "boundary": "in_process_fixture_normalization",
        "unsafe_duplicate_openmp_override_used": False,
    }
    expected_artifact_recovery = {
        "original_receipt_available": False,
        "raw_receipt_bytes_preserved": False,
        "reason": "volatile_untracked_worktree_removed_during_host_restart",
        "provenance": "terminal_tool_log_complete_payload_and_sha256",
        "reconstructed_receipt_claimed": False,
    }
    expected_authorization = {
        "producer_qualification_pass_observed": True,
        "consumer_binding_established": False,
        "promotion_authorized": False,
        "subject_data_observed": False,
        "subject_audit_outcome_observed": False,
        "subject_one_shot_consumed": False,
        "superseded_by_qualification_schema_version": (
            _QUALIFICATION_SCHEMA_VERSION_V0_2
        ),
    }
    payload_fields = {
        "schema_version",
        "status",
        "backend",
        "source",
        "fixture",
        "fixture_sha256",
        "search",
        "runtime",
        "cold_runs",
    }
    payload_fixture = payload.get("fixture")
    payload_search = payload.get("search")
    payload_runtime = payload.get("runtime")
    payload_cold_runs = payload.get("cold_runs")
    if (
        observation.get("schema_version")
        != _QUALIFICATION_OBSERVATION_SCHEMA_VERSION
        or observation.get("status")
        != "producer_pass_consumer_binding_unestablished"
        or observation.get("qualification_schema_version")
        != _QUALIFICATION_SCHEMA_VERSION_V0_1
        or observation.get("observed_receipt_sha256")
        != _V0_3_OBSERVED_QUALIFICATION_SHA256
        or observation.get("observed_fixture_sha256")
        != _V0_3_OBSERVED_FIXTURE_SHA256
        or observation.get("observed_search_sha256")
        != _V0_3_OBSERVED_SEARCH_SHA256
        or observation.get("observed_cold_process_runs") != 2
        or observation.get("observed_raw_hit_count_per_run") != 16_384
        or dict(observed_source) != expected_source
        or dict(consumer_preflight) != expected_consumer_preflight
        or dict(artifact_recovery) != expected_artifact_recovery
        or dict(authorization) != expected_authorization
        or set(payload) != payload_fields
        or payload.get("schema_version")
        != _QUALIFICATION_SCHEMA_VERSION_V0_1
        or payload.get("status") != "pass"
        or payload.get("backend")
        != {
            "backend_id": "spirallens.faiss-hnsw-range",
            "backend_version": "0.2",
        }
        or payload.get("source") != expected_source
        or not isinstance(payload_fixture, Mapping)
        or not isinstance(payload_search, Mapping)
        or not isinstance(payload_runtime, Mapping)
        or not payload_runtime
        or not isinstance(payload_cold_runs, list)
        or len(payload_cold_runs) != 2
        or payload_cold_runs[0] != payload_cold_runs[1]
        or any(
            not isinstance(run, Mapping)
            or run.get("raw_hit_count") != 16_384
            for run in payload_cold_runs
        )
        or payload.get("fixture_sha256")
        != _V0_3_OBSERVED_FIXTURE_SHA256
        or canonical_json_sha256(dict(payload_fixture))
        != _V0_3_OBSERVED_FIXTURE_SHA256
        or canonical_json_sha256(dict(payload_search))
        != _V0_3_OBSERVED_SEARCH_SHA256
        or canonical_json_sha256(dict(payload))
        != _V0_3_OBSERVED_QUALIFICATION_SHA256
    ):
        raise ValueError(
            "qualification predecessor observation evidence differs"
        )

    raw_active_preflight = _git_bytes(
        git_executable,
        repo_root,
        "cat-file",
        "commit",
        active_preflight_commit,
    )
    raw_parent_lines = [
        line
        for line in raw_active_preflight.split(b"\n\n", 1)[0].splitlines()
        if line.startswith(b"parent ")
    ]
    observed_tree_from_git = _git_output(
        git_executable,
        repo_root,
        "rev-parse",
        f"{_V0_3_OBSERVED_SOURCE_COMMIT}:src/spirallens",
    )
    if (
        raw_parent_lines
        != [f"parent {_V0_3_OBSERVED_SOURCE_COMMIT}".encode("ascii")]
        or observed_tree_from_git != _V0_3_OBSERVED_SOURCE_TREE
        or active_preflight_tree == _V0_3_OBSERVED_SOURCE_TREE
        or _git_bytes(
            git_executable,
            repo_root,
            "show",
            f"{active_preflight_commit}:{observation_relative}",
        )
        != observation_bytes
        or _git_bytes(
            git_executable,
            repo_root,
            "show",
            f"{implementation_commit}:{observation_relative}",
        )
        != observation_bytes
        or _git_output(
            git_executable,
            repo_root,
            "ls-tree",
            "--name-only",
            active_preflight_commit,
            "--",
            _V0_3_LOST_QUALIFICATION_RELATIVE_PATH,
        )
        or _git_output(
            git_executable,
            repo_root,
            "ls-tree",
            "--name-only",
            implementation_commit,
            "--",
            _V0_3_LOST_QUALIFICATION_RELATIVE_PATH,
        )
    ):
        raise ValueError(
            "qualification predecessor Git lineage or availability differs"
        )


def _validate_v0_3_implementation_delta(
    *,
    repo_root: Path,
    git_executable: Path,
    preflight_commit: str,
    implementation_commit: str,
    qualification_path: Path,
    frozen_protocol_path: Path,
) -> None:
    expected = sorted(
        {
            qualification_path.relative_to(repo_root).as_posix(),
            frozen_protocol_path.relative_to(repo_root).as_posix(),
        }
    )
    actual = _git_output(
        git_executable,
        repo_root,
        "diff",
        "--name-only",
        f"{preflight_commit}..{implementation_commit}",
    ).splitlines()
    if actual != expected:
        raise ValueError(
            "v0.3 implementation commit exceeds its receipt/protocol "
            "allowlist"
        )


def _validate_backend_qualification(
    value: object,
    *,
    repo_root: Path,
    implementation_commit: str,
    implementation_package_tree: str,
    repository: str,
    branch: str,
    git_executable: Path,
    frozen_neighbor: Mapping[str, Any],
    frozen_candidate: Mapping[str, Any],
    runtime: Mapping[str, Any],
    atlas_row_count: object,
    expected_schema_version: str = _QUALIFICATION_SCHEMA_VERSION_V0_1,
    expected_relative_path: str | None = None,
) -> tuple[Path, str, str, dict[str, object], str, str]:
    from spirallens.neighbors.faiss_qualification import (
        load_faiss_hnsw_qualification_receipt,
    )

    binding = _require_mapping(
        value,
        label="backend_qualification",
        fields={
            "schema_version",
            "path",
            "sha256",
            "fixture_sha256",
            "subject_config_sha256",
            "search_sha256",
            "faiss_native_sha256",
            "range_call_batch_size",
            "cold_process_runs",
            "preflight_commit",
            "preflight_package_tree",
        },
    )
    if binding.get("schema_version") != expected_schema_version:
        raise ValueError(
            "execution freeze backend qualification schema is invalid"
        )
    receipt_path = Path(str(binding.get("path")))
    receipt_bytes, receipt_relative = _read_repo_regular_file(
        receipt_path,
        repo_root=repo_root,
        label="backend qualification receipt",
    )
    if (
        expected_relative_path is not None
        and receipt_relative != expected_relative_path
    ):
        raise ValueError(
            "execution freeze backend qualification path is invalid"
        )
    receipt_sha256 = _require_sha256(
        binding.get("sha256"),
        label="backend_qualification.sha256",
    )
    fixture_sha256 = _require_sha256(
        binding.get("fixture_sha256"),
        label="backend_qualification.fixture_sha256",
    )
    subject_config_sha256 = _require_sha256(
        binding.get("subject_config_sha256"),
        label="backend_qualification.subject_config_sha256",
    )
    search_sha256 = _require_sha256(
        binding.get("search_sha256"),
        label="backend_qualification.search_sha256",
    )
    native_sha256 = _require_sha256(
        binding.get("faiss_native_sha256"),
        label="backend_qualification.faiss_native_sha256",
    )
    preflight_commit = _require_git_object(
        binding.get("preflight_commit"),
        label="backend_qualification.preflight_commit",
    )
    preflight_package_tree = _require_git_object(
        binding.get("preflight_package_tree"),
        label="backend_qualification.preflight_package_tree",
    )
    if (
        hashlib.sha256(receipt_bytes).hexdigest() != receipt_sha256
        or _git_bytes(
            git_executable,
            repo_root,
            "show",
            f"{implementation_commit}:{receipt_relative}",
        )
        != receipt_bytes
    ):
        raise ValueError(
            "backend qualification receipt bytes or Git blob differ"
        )
    receipt = load_faiss_hnsw_qualification_receipt(
        receipt_path,
        expected_sha256=receipt_sha256,
    )
    search = receipt.search
    qualification_runtime = receipt.runtime
    qualification_source = receipt.source
    if (
        not isinstance(search, Mapping)
        or not isinstance(qualification_runtime, Mapping)
        or not isinstance(qualification_source, Mapping)
    ):
        raise ValueError("backend qualification receipt is malformed")
    raw_implementation_commit = _git_bytes(
        git_executable,
        repo_root,
        "cat-file",
        "commit",
        implementation_commit,
    )
    raw_parent_lines = [
        line
        for line in raw_implementation_commit.split(b"\n\n", 1)[
            0
        ].splitlines()
        if line.startswith(b"parent ")
    ]
    preflight_tree_from_git = _git_output(
        git_executable,
        repo_root,
        "rev-parse",
        f"{preflight_commit}:src/spirallens",
    )

    subject = frozen_neighbor.get("subject_backend")
    subject_config = (
        subject.get("config")
        if isinstance(subject, Mapping)
        else None
    )
    candidate_search = frozen_candidate.get("candidate_search")
    protocol_qualification = frozen_neighbor.get(
        "backend_qualification"
    )
    if (
        not isinstance(subject, Mapping)
        or subject.get("backend_id")
        != "spirallens.faiss-hnsw-range"
        or str(subject.get("backend_version")) != "0.2"
        or not isinstance(subject_config, Mapping)
        or not isinstance(candidate_search, Mapping)
        or not isinstance(protocol_qualification, Mapping)
    ):
        raise ValueError(
            "qualified neighbor protocol backend declaration is invalid"
        )
    expected_protocol_qualification = {
        "schema_version": expected_schema_version,
        "path": receipt_relative,
        "sha256": receipt_sha256,
        "fixture_sha256": fixture_sha256,
    }
    config_sha256 = canonical_json_sha256(dict(subject_config))
    cosine_min = candidate_search.get("cosine_min")
    score_margin = subject_config.get("score_margin")
    if (
        isinstance(cosine_min, bool)
        or not isinstance(cosine_min, (int, float))
        or isinstance(score_margin, bool)
        or not isinstance(score_margin, (int, float))
    ):
        raise ValueError(
            "qualified search threshold declaration is invalid"
        )
    expected_radius = float(
        np.nextafter(
            np.float32(max(-1.0, cosine_min - score_margin)),
            np.float32(-np.inf),
        )
    )
    config_search_fields = (
        "m",
        "ef_construction",
        "ef_search",
        "seed",
        "thread_count",
        "query_batch_size",
        "range_call_batch_size",
        "score_margin",
        "max_raw_hits",
    )
    expected_runtime = {
        key: str(runtime[key])
        for key in qualification_runtime
        if key in runtime
    }
    if (
        dict(protocol_qualification)
        != expected_protocol_qualification
        or receipt.sha256 != receipt_sha256
        or receipt.fixture_sha256 != fixture_sha256
        or receipt.search_sha256 != search_sha256
        or receipt.status != "pass"
        or receipt.backend_id != "spirallens.faiss-hnsw-range"
        or receipt.backend_version != "0.2"
        or len(receipt.cold_process_runs) != 2
        or config_sha256 != subject_config_sha256
        or binding.get("range_call_batch_size") != 1
        or subject_config.get("range_call_batch_size") != 1
        or search.get("range_call_batch_size") != 1
        or binding.get("cold_process_runs") != 2
        or receipt.implementation_commit != preflight_commit
        or receipt.spirallens_package_tree
        != preflight_package_tree
        or qualification_source.get("repository") != repository
        or qualification_source.get("branch") != branch
        or raw_parent_lines
        != [f"parent {preflight_commit}".encode("ascii")]
        or preflight_tree_from_git != preflight_package_tree
        or preflight_package_tree != implementation_package_tree
        or native_sha256 != runtime.get("faiss_native_sha256")
        or qualification_runtime.get("faiss_native_sha256")
        != native_sha256
        or dict(qualification_runtime) != expected_runtime
        or any(
            search.get(key) != subject_config.get(key)
            for key in config_search_fields
        )
        or search.get("cosine_min") != float(cosine_min)
        or search.get("radius") != expected_radius
        or search.get("max_native_call_hits") != atlas_row_count
    ):
        raise ValueError(
            "backend qualification receipt, protocol, runtime, or freeze "
            "binding differs"
        )
    expected_parameters = {
        key: value for key, value in subject_config.items()
    }
    expected_parameters.update(
        {
            "qualification_receipt_sha256": receipt_sha256,
            "qualification_fixture_sha256": fixture_sha256,
            "max_native_call_hits": receipt.max_native_call_hits,
        }
    )
    backend_contract = {
        "backend_id": "spirallens.faiss-hnsw-range",
        "backend_version": "0.2",
        "parameters": expected_parameters,
    }
    return (
        receipt_path,
        receipt_sha256,
        fixture_sha256,
        backend_contract,
        preflight_commit,
        preflight_package_tree,
    )


def _validate_freeze_core(
    *,
    document: Mapping[str, Any],
    source_bytes: bytes,
    source_path: Path,
    expected_sha256: str,
    manifest_path: Path,
    manifest_sha256: str,
    protocol_path: Path,
    protocol_sha256: str,
    candidate_protocol_path: Path,
    candidate_protocol_sha256: str,
    recall_gate_path: Path,
    recall_gate_sha256: str,
    output_path: Path,
    layer_index: int,
    comparison_group: str,
    global_row_key_sha256: str,
    query_selection_sha256: str,
    audit_config_sha256: str,
    query_count: int,
    query_seed: int,
) -> tuple[
    str,
    dict[str, str],
    dict[str, object] | None,
]:
    import spirallens

    expected_digest = _require_sha256(
        expected_sha256,
        label="expected execution-freeze SHA-256",
    )
    actual_digest = hashlib.sha256(source_bytes).hexdigest()
    if actual_digest != expected_digest:
        raise ValueError(
            "execution freeze does not match its out-of-band SHA-256"
        )
    isolated_worker_runtime = current_worker_runtime_contract(None)
    schema_version = document.get("schema_version")
    qualified_profile = _qualified_freeze_profile(schema_version)
    qualified_freeze = qualified_profile is not None
    v0_3_freeze = (
        schema_version == EXECUTION_FREEZE_SCHEMA_VERSION_V0_3
    )
    expected_top_level = {
        "schema_version",
        "freeze_id",
        "status",
        "source",
        "atlas",
        "frozen_protocols",
        "prepared_bindings",
        "runtime",
        "execution",
        "single_shot_contract",
        "claim_boundary",
    }
    if qualified_freeze:
        expected_top_level.update(
            {"backend_qualification", "predecessor_tombstone"}
        )
    if v0_3_freeze:
        expected_top_level.add("qualification_predecessor")
    if (
        set(document) != expected_top_level
        or schema_version
        not in SUPPORTED_EXECUTION_FREEZE_SCHEMA_VERSIONS
        or not isinstance(document.get("freeze_id"), str)
        or not document["freeze_id"]
        or (
            qualified_profile is not None
            and document.get("freeze_id")
            != qualified_profile["freeze_id"]
        )
        or document.get("status") != "frozen_before_outcome"
    ):
        raise ValueError("execution freeze identity is invalid")

    source = _require_mapping(
        document.get("source"),
        label="source",
        fields={
            "repository",
            "branch",
            "implementation_commit",
            "implementation_package_tree",
            "required_worktree_state",
            "allowed_head_diff",
            "git_common_dir",
            "git_dir",
            "git_admin_pointer_sha256",
        },
    )
    execution = _require_mapping(
        document.get("execution"),
        label="execution",
        fields={
            "cwd",
            "pythonpath",
            "pythonpycacheprefix",
            "pythondontwritebytecode",
            "manifest_path",
            "protocol_path",
            "freeze_record_path",
            "output_path",
            "layer_index",
            "argv_template",
        },
    )
    runtime = _require_mapping(
        document.get("runtime"),
        label="runtime",
        fields=_execution_runtime_fields(schema_version),
    )

    freeze_path = source_path.resolve()
    repo_root = Path(str(execution["cwd"]))
    import_root = Path(str(execution["pythonpath"]))
    current_import_file = Path(__file__).resolve()
    expected_values = {
        "cwd": Path.cwd(),
        "pythonpath": Path(os.environ.get("PYTHONPATH", "")),
        "manifest_path": manifest_path,
        "protocol_path": protocol_path,
        "freeze_record_path": freeze_path,
        "output_path": output_path,
    }
    for field_name, actual_path in expected_values.items():
        declared_path = Path(str(execution[field_name]))
        if (
            not declared_path.is_absolute()
            or actual_path.absolute() != declared_path
        ):
            raise ValueError(
                f"execution freeze {field_name} differs from runtime"
            )
    pycache_prefix = Path(str(execution["pythonpycacheprefix"]))
    inherited_control_environment = sorted(
        key
        for key in os.environ
        if key.startswith(("GIT_", "DYLD_", "LD_"))
    )
    if (
        repo_root.resolve() != current_import_file.parents[2]
        or import_root.resolve() != current_import_file.parents[1]
        or import_root != repo_root / "src"
        or execution["pythonpycacheprefix"]
        != os.environ.get("PYTHONPYCACHEPREFIX")
        or not pycache_prefix.is_absolute()
        or pycache_prefix.exists()
        or execution["pythondontwritebytecode"] != "1"
        or os.environ.get("PYTHONDONTWRITEBYTECODE") != "1"
        or execution["layer_index"] != layer_index
        or inherited_control_environment
    ):
        raise ValueError(
            "execution freeze import root, environment, or layer differs"
        )

    implementation_commit = _require_git_object(
        source.get("implementation_commit"),
        label="source.implementation_commit",
    )
    implementation_tree = _require_git_object(
        source.get("implementation_package_tree"),
        label="source.implementation_package_tree",
    )
    branch = source.get("branch")
    repository = source.get("repository")
    allowed_head_diff = source.get("allowed_head_diff")
    git_executable = Path(str(runtime["git_executable"]))
    freeze_filename_version = (
        "v0_1"
        if qualified_profile is None
        else qualified_profile["freeze_filename_version"]
    )
    expected_freeze_relative = (
        "protocols/"
        "pythia70_slot_only_001_layer0_subject_audit_freeze_"
        f"{freeze_filename_version}.yaml"
    )
    if qualified_freeze:
        assert qualified_profile is not None
        expected_protocol_path = (
            repo_root
            / "protocols"
            / qualified_profile["neighbor_frozen_filename"]
        )
        expected_output_path = Path(
            "/Users/ryohiga/SpiralReality/spirallens/runs/"
            "pythia70-full-slot-only-001/"
            f"{qualified_profile['output_filename']}"
        )
        if (
            protocol_path != expected_protocol_path
            or output_path != expected_output_path
        ):
            raise ValueError(
                "qualified execution freeze protocol or output path is invalid"
            )
        _validate_predecessor_tombstone(
            document.get("predecessor_tombstone"),
            repo_root=repo_root,
            new_output_path=output_path,
        )
    if (
        git_executable != Path("/usr/bin/git")
        or not git_executable.is_file()
        or _require_sha256(
            runtime["git_executable_sha256"],
            label="runtime.git_executable_sha256",
        )
        != _sha256_file(git_executable)
        or runtime["git_version"]
        != _git_output(git_executable, repo_root, "--version")
    ):
        raise ValueError("execution freeze Git runtime differs")
    git_pointer_path = repo_root / ".git"
    if not git_pointer_path.is_file():
        raise ValueError(
            "execution freeze requires an explicit Git worktree pointer"
        )
    git_pointer_bytes = git_pointer_path.read_bytes()
    try:
        git_pointer_line = git_pointer_bytes.decode("utf-8").strip()
    except UnicodeDecodeError as error:
        raise ValueError("Git worktree pointer is invalid") from error
    if not git_pointer_line.startswith("gitdir: "):
        raise ValueError("Git worktree pointer is invalid")
    git_dir = Path(git_pointer_line.removeprefix("gitdir: "))
    if not git_dir.is_absolute():
        git_dir = repo_root / git_dir
    git_dir = git_dir.resolve()
    common_dir_pointer = git_dir / "commondir"
    if common_dir_pointer.is_file():
        common_dir_value = common_dir_pointer.read_text(
            encoding="utf-8"
        ).strip()
        git_common_dir_from_pointer = Path(common_dir_value)
        if not git_common_dir_from_pointer.is_absolute():
            git_common_dir_from_pointer = (
                git_dir / git_common_dir_from_pointer
            )
        git_common_dir_from_pointer = (
            git_common_dir_from_pointer.resolve()
        )
    else:
        git_common_dir_from_pointer = git_dir
    if (
        not git_dir.is_dir()
        or not git_common_dir_from_pointer.is_dir()
        or source.get("git_dir") != str(git_dir)
        or source.get("git_common_dir")
        != str(git_common_dir_from_pointer)
        or _require_sha256(
            source.get("git_admin_pointer_sha256"),
            label="source.git_admin_pointer_sha256",
        )
        != hashlib.sha256(git_pointer_bytes).hexdigest()
    ):
        raise ValueError(
            "execution freeze Git worktree pointer differs"
        )
    local_config_names = {
        value.lower()
        for value in _git_output(
            git_executable,
            repo_root,
            "config",
            "--local",
            "--name-only",
            "--list",
        ).splitlines()
    }
    index_records = [
        record
        for record in _git_bytes(
            git_executable,
            repo_root,
            "ls-files",
            "-v",
            "-z",
            "--",
            ".",
        ).split(b"\0")
        if record
    ]
    _validate_git_index_records(index_records)
    git_common_dir_value = _git_output(
        git_executable,
        repo_root,
        "rev-parse",
        "--git-common-dir",
    )
    git_common_dir = Path(git_common_dir_value)
    if not git_common_dir.is_absolute():
        git_common_dir = (repo_root / git_common_dir).resolve()
    if (
        any(
            name.startswith(
                (
                    "credential.",
                    "http.",
                    "https.",
                    "include.",
                    "includeif.",
                    "url.",
                )
            )
            for name in local_config_names
        )
        or any(
            name
            in {
                "core.alternaterefscommand",
                "core.fsmonitor",
                "core.gitproxy",
                "core.sshcommand",
                "core.worktree",
                "remote.origin.proxy",
                "remote.origin.uploadpack",
            }
            for name in local_config_names
        )
        or "extensions.worktreeconfig" in local_config_names
        or (git_dir / "config.worktree").exists()
        or git_common_dir != git_common_dir_from_pointer
        or (git_common_dir / "objects" / "info" / "alternates").exists()
        or (git_common_dir / "info" / "grafts").exists()
        or (git_common_dir / "shallow").exists()
        or (git_dir / "shallow").exists()
        or _git_output(
            git_executable,
            repo_root,
            "for-each-ref",
            "--format=%(refname)",
            "refs/replace",
        )
    ):
        raise ValueError(
            "execution freeze Git repository uses mutable indirection"
        )
    if (
        source.get("required_worktree_state") != "clean"
        or not isinstance(branch, str)
        or not branch
        or not isinstance(repository, str)
        or not repository
        or allowed_head_diff != [expected_freeze_relative]
        or freeze_path != repo_root / expected_freeze_relative
        or _git_output(
            git_executable,
            repo_root,
            "branch",
            "--show-current",
        )
        != branch
        or _git_output(
            git_executable,
            repo_root,
            "remote",
            "get-url",
            "origin",
        )
        != repository
        or _git_output(
            git_executable,
            repo_root,
            "status",
            "--porcelain",
            "--untracked-files=all",
        )
        or _git_output(
            git_executable,
            repo_root,
            "status",
            "--porcelain",
            "--ignored",
            "--untracked-files=all",
            "--",
            "src/spirallens",
        )
        or _git_output(
            git_executable,
            repo_root,
            "diff",
            "--name-only",
            f"{implementation_commit}..HEAD",
        ).splitlines()
        != allowed_head_diff
        or _git_output(
            git_executable,
            repo_root,
            "rev-list",
            "--count",
            f"{implementation_commit}..HEAD",
        )
        != "1"
        or _git_output(
            git_executable,
            repo_root,
            "rev-parse",
            "HEAD^",
        )
        != implementation_commit
        or _git_output(
            git_executable,
            repo_root,
            "rev-parse",
            f"{implementation_commit}:src/spirallens",
        )
        != implementation_tree
        or _git_output(
            git_executable,
            repo_root,
            "rev-parse",
            "HEAD:src/spirallens",
        )
        != implementation_tree
        or _git_bytes(
            git_executable,
            repo_root,
            "show",
            f"HEAD:{expected_freeze_relative}",
        )
        != source_bytes
    ):
        raise ValueError(
            "execution freeze repository, source tree, or tracked blob differs"
        )
    raw_head_commit = _git_bytes(
        git_executable,
        repo_root,
        "cat-file",
        "commit",
        "HEAD",
    )
    raw_parent_lines = [
        line
        for line in raw_head_commit.split(b"\n\n", 1)[0].splitlines()
        if line.startswith(b"parent ")
    ]
    if raw_parent_lines != [
        f"parent {implementation_commit}".encode("ascii")
    ]:
        raise ValueError(
            "execution freeze HEAD raw parent differs"
        )
    head = _git_output(
        git_executable,
        repo_root,
        "rev-parse",
        "HEAD",
    )
    upstream = _git_output(
        git_executable,
        repo_root,
        "rev-parse",
        f"refs/remotes/origin/{branch}",
    )
    remote_lines = _git_output(
        git_executable,
        repo_root,
        "ls-remote",
        "--heads",
        str(repository),
        f"refs/heads/{branch}",
    ).splitlines()
    if (
        head != upstream
        or remote_lines != [f"{head}\trefs/heads/{branch}"]
    ):
        raise ValueError(
            "execution freeze requires the exact live pushed branch HEAD"
        )

    executable = Path(sys.executable)
    executable_resolved = executable.resolve()
    process_image = process_image_path()
    numpy_import = Path(np.__file__).resolve()
    faiss_import = Path(
        isolated_worker_runtime["faiss_import_file"]
    ).resolve()
    faiss_native_import = Path(
        isolated_worker_runtime["faiss_native_file"]
    ).resolve()
    numpy_owned = {
        path.resolve() for path in _distribution_files("numpy")
    }
    faiss_owned = {
        path.resolve() for path in _distribution_files("faiss-cpu")
    }
    spirallens_import = Path(spirallens.__file__).resolve()
    faiss_hnsw_source = (
        current_import_file.parent / "neighbors" / "faiss_hnsw.py"
    )
    faiss_worker_source = (
        current_import_file.parent / "neighbors" / "_faiss_worker.py"
    )
    faiss_runtime_worker_source = (
        current_import_file.parent
        / "neighbors"
        / "_faiss_runtime_worker.py"
    )
    if (
        numpy_import not in numpy_owned
        or faiss_import not in faiss_owned
        or faiss_native_import not in faiss_owned
        or runtime["executable"] != sys.executable
        or Path(str(runtime["executable_resolved"]))
        != executable_resolved
        or _require_sha256(
            runtime["executable_sha256"],
            label="runtime.executable_sha256",
        )
        != _sha256_file(executable_resolved)
        or Path(str(runtime["process_image"])) != process_image
        or _require_sha256(
            runtime["process_image_sha256"],
            label="runtime.process_image_sha256",
        )
        != _sha256_file(process_image)
        or runtime["python_implementation"]
        != platform.python_implementation()
        or runtime["python_version"] != platform.python_version()
        or runtime["platform"] != platform.platform()
        or runtime["machine"] != platform.machine()
        or runtime["system"] != platform.system()
        or runtime["spirallens_version"] != SPIRALLENS_VERSION
        or Path(str(runtime["spirallens_import_file"])).resolve()
        != spirallens_import
        or spirallens_import
        != current_import_file.parent / "__init__.py"
        or runtime["numpy_version"] != np.__version__
        or _require_sha256(
            runtime["numpy_distribution_sha256"],
            label="runtime.numpy_distribution_sha256",
        )
        != distribution_content_sha256("numpy")
        or Path(str(runtime["numpy_import_file"])) != numpy_import
        or _require_sha256(
            runtime["numpy_import_sha256"],
            label="runtime.numpy_import_sha256",
        )
        != _sha256_file(numpy_import)
        or runtime["faiss_distribution"] != "faiss-cpu"
        or runtime["faiss_version"]
        != isolated_worker_runtime["faiss_version"]
        or _require_sha256(
            runtime["faiss_distribution_sha256"],
            label="runtime.faiss_distribution_sha256",
        )
        != distribution_content_sha256("faiss-cpu")
        or Path(str(runtime["faiss_import_file"])) != faiss_import
        or _require_sha256(
            runtime["faiss_import_sha256"],
            label="runtime.faiss_import_sha256",
        )
        != _sha256_file(faiss_import)
        or Path(str(runtime["faiss_native_file"]))
        != faiss_native_import
        or _require_sha256(
            runtime["faiss_native_sha256"],
            label="runtime.faiss_native_sha256",
        )
        != _sha256_file(faiss_native_import)
        or runtime["faiss_compile_options"]
        != isolated_worker_runtime["faiss_compile_options"]
        or _require_sha256(
            runtime["faiss_hnsw_source_sha256"],
            label="runtime.faiss_hnsw_source_sha256",
        )
        != _sha256_file(faiss_hnsw_source)
        or (
            v0_3_freeze
            and _require_sha256(
                runtime["faiss_runtime_worker_source_sha256"],
                label="runtime.faiss_runtime_worker_source_sha256",
            )
            != _sha256_file(faiss_runtime_worker_source)
        )
        or _require_sha256(
            runtime["faiss_worker_source_sha256"],
            label="runtime.faiss_worker_source_sha256",
        )
        != _sha256_file(faiss_worker_source)
    ):
        raise ValueError(
            "execution freeze runtime imports or content differ"
        )

    persisted_manifest_bytes = manifest_path.read_bytes()
    if hashlib.sha256(persisted_manifest_bytes).hexdigest() != (
        manifest_sha256
    ):
        raise ValueError("execution freeze atlas bytes differ")
    try:
        persisted_manifest = json.loads(persisted_manifest_bytes)
    except json.JSONDecodeError as error:
        raise ValueError("execution freeze atlas JSON is invalid") from error
    if not isinstance(persisted_manifest, Mapping):
        raise ValueError("execution freeze atlas JSON is invalid")
    manifest_request = persisted_manifest.get("request")
    manifest_progress = persisted_manifest.get("progress")
    context_binding = (
        manifest_request.get("context_bank_binding")
        if isinstance(manifest_request, Mapping)
        else None
    )
    selected_context = (
        context_binding.get("selected_context")
        if isinstance(context_binding, Mapping)
        else None
    )
    context_bank = (
        context_binding.get("bank")
        if isinstance(context_binding, Mapping)
        else None
    )
    context_bank_content = (
        context_bank.get("content")
        if isinstance(context_bank, Mapping)
        else None
    )
    manifest_selection = (
        manifest_request.get("selection")
        if isinstance(manifest_request, Mapping)
        else None
    )
    if (
        not isinstance(manifest_request, Mapping)
        or not isinstance(manifest_progress, Mapping)
        or not isinstance(selected_context, Mapping)
        or not isinstance(context_bank_content, Mapping)
        or not isinstance(manifest_selection, Mapping)
    ):
        raise ValueError("execution freeze atlas provenance is incomplete")
    atlas = _require_mapping(
        document.get("atlas"),
        label="atlas",
        fields={
            "manifest_path",
            "manifest_sha256",
            "run_id",
            "row_count",
            "selection",
            "context_bank_binding_sha256",
            "context_id",
            "context_role",
            "context_bank_claim_eligible",
            "layer_index",
        },
    )
    expected_atlas = {
        "manifest_path": str(manifest_path),
        "manifest_sha256": _require_sha256(
            manifest_sha256,
            label="manifest_sha256",
        ),
        "run_id": persisted_manifest.get("run_id"),
        "row_count": manifest_progress.get("total_rows"),
        "selection": manifest_selection.get("kind"),
        "context_bank_binding_sha256": manifest_request.get(
            "context_bank_binding_sha256"
        ),
        "context_id": selected_context.get("context_id"),
        "context_role": selected_context.get("role"),
        "context_bank_claim_eligible": context_bank_content.get(
            "claim_eligible"
        ),
        "layer_index": layer_index,
    }
    if dict(atlas) != expected_atlas:
        raise ValueError("execution freeze atlas declaration differs")

    frozen_protocols = _require_mapping(
        document.get("frozen_protocols"),
        label="frozen_protocols",
        fields={"candidate", "neighbor", "recall_gate"},
    )
    candidate_sha256 = _require_sha256(
        candidate_protocol_sha256,
        label="candidate_protocol_sha256",
    )
    neighbor_sha256 = _require_sha256(
        protocol_sha256,
        label="protocol_sha256",
    )
    gate_sha256 = _require_sha256(
        recall_gate_sha256,
        label="recall_gate_sha256",
    )
    candidate_parent_path = (
        repo_root / "protocols" / "pythia_candidate_v0_2.yaml"
    )
    neighbor_parent_filename = (
        "pythia_neighbor_v0_2.yaml"
        if qualified_profile is None
        else qualified_profile["neighbor_parent_filename"]
    )
    neighbor_parent_path = (
        repo_root
        / "protocols"
        / neighbor_parent_filename
    )
    candidate_parent_sha256 = (
        "ce3e6b6ba7c6cac026ba74671faf5c800e3d21bfc6abbf2641b9d03a37ceb2d8"
    )
    neighbor_parent_sha256 = (
        _sha256_file(neighbor_parent_path)
        if qualified_freeze
        else (
            "45f6699badb314f68c43d5fee2bf2070405af13b518437e24590b0de9f117350"
        )
    )
    candidate_changes = [
        "protocol_id",
        "status_preregistered_draft_to_frozen",
        "candidate_search.layer_indices_null_to_layer_0",
    ]
    neighbor_changes = [
        "protocol_id",
        "status_preregistered_draft_to_frozen",
        "audit_scope_binding",
        "frozen_candidate_protocol_binding",
        "query_row_universe_binding",
        "receipt_issue_flag_false_to_true",
        "promotion_readiness_execution_flags_false_to_true",
    ]
    if qualified_freeze:
        neighbor_changes.extend(
            [
                "backend_qualification_binding",
                "production_shape_subprocess_qualified_false_to_true",
            ]
        )
    candidate_binding = _require_mapping(
        frozen_protocols.get("candidate"),
        label="frozen_protocols.candidate",
        fields={
            "path",
            "sha256",
            "parent_draft_path",
            "parent_draft_sha256",
            "allowed_freeze_changes",
        },
    )
    neighbor_binding = _require_mapping(
        frozen_protocols.get("neighbor"),
        label="frozen_protocols.neighbor",
        fields={
            "path",
            "sha256",
            "parent_draft_path",
            "parent_draft_sha256",
            "allowed_freeze_changes",
        },
    )
    gate_binding = _require_mapping(
        frozen_protocols.get("recall_gate"),
        label="frozen_protocols.recall_gate",
        fields={"path", "sha256"},
    )
    if (
        not candidate_protocol_path.is_absolute()
        or candidate_binding.get("path")
        != str(candidate_protocol_path)
        or candidate_binding.get("sha256") != candidate_sha256
        or candidate_binding.get("parent_draft_path")
        != str(candidate_parent_path)
        or candidate_binding.get("parent_draft_sha256")
        != candidate_parent_sha256
        or candidate_binding.get("allowed_freeze_changes")
        != candidate_changes
        or _sha256_file(candidate_protocol_path) != candidate_sha256
        or _sha256_file(candidate_parent_path)
        != candidate_parent_sha256
        or not protocol_path.is_absolute()
        or neighbor_binding.get("path") != str(protocol_path)
        or neighbor_binding.get("sha256") != neighbor_sha256
        or neighbor_binding.get("parent_draft_path")
        != str(neighbor_parent_path)
        or neighbor_binding.get("parent_draft_sha256")
        != neighbor_parent_sha256
        or neighbor_binding.get("allowed_freeze_changes")
        != neighbor_changes
        or _sha256_file(protocol_path) != neighbor_sha256
        or _sha256_file(neighbor_parent_path)
        != neighbor_parent_sha256
        or not recall_gate_path.is_absolute()
        or gate_binding.get("path") != str(recall_gate_path)
        or gate_binding.get("sha256") != gate_sha256
        or _sha256_file(recall_gate_path) != gate_sha256
    ):
        raise ValueError(
            "execution freeze protocol declaration or lineage differs"
        )
    candidate_parent = _load_protocol_document(
        candidate_parent_path,
        label="candidate parent protocol",
    )
    frozen_candidate = _load_protocol_document(
        candidate_protocol_path,
        label="frozen candidate protocol",
    )
    neighbor_parent = _load_protocol_document(
        neighbor_parent_path,
        label="neighbor parent protocol",
    )
    frozen_neighbor = _load_protocol_document(
        protocol_path,
        label="frozen neighbor protocol",
    )
    backend_contract: dict[str, object] | None = None
    qualification_path: Path | None = None
    qualification_sha256: str | None = None
    qualification_fixture_sha256: str | None = None
    qualification_preflight_commit: str | None = None
    qualification_preflight_tree: str | None = None
    if qualified_freeze:
        assert qualified_profile is not None
        for tracked_path, tracked_bytes, label in (
            (
                neighbor_parent_path,
                neighbor_parent_path.read_bytes(),
                "qualified neighbor parent",
            ),
            (
                protocol_path,
                protocol_path.read_bytes(),
                "qualified frozen neighbor protocol",
            ),
        ):
            tracked_relative = tracked_path.relative_to(repo_root).as_posix()
            if (
                _git_bytes(
                    git_executable,
                    repo_root,
                    "show",
                    f"{implementation_commit}:{tracked_relative}",
                )
                != tracked_bytes
            ):
                raise ValueError(f"{label} differs from its Git blob")
        (
            qualification_path,
            qualification_sha256,
            qualification_fixture_sha256,
            backend_contract,
            qualification_preflight_commit,
            qualification_preflight_tree,
        ) = _validate_backend_qualification(
            document.get("backend_qualification"),
            repo_root=repo_root,
            implementation_commit=implementation_commit,
            implementation_package_tree=implementation_tree,
            repository=str(repository),
            branch=str(branch),
            git_executable=git_executable,
            frozen_neighbor=frozen_neighbor,
            frozen_candidate=frozen_candidate,
            runtime=runtime,
            atlas_row_count=expected_atlas["row_count"],
            expected_schema_version=(
                qualified_profile["qualification_schema_version"]
            ),
            expected_relative_path=(
                qualified_profile["qualification_relative_path"] or None
            ),
        )
    if v0_3_freeze:
        if (
            qualification_path is None
            or qualification_sha256 is None
            or qualification_preflight_commit is None
            or qualification_preflight_tree is None
        ):
            raise ValueError(
                "v0.3 execution freeze lacks active qualification lineage"
            )
        _validate_qualification_predecessor(
            document.get("qualification_predecessor"),
            repo_root=repo_root,
            git_executable=git_executable,
            repository=str(repository),
            branch=str(branch),
            active_preflight_commit=qualification_preflight_commit,
            active_preflight_tree=qualification_preflight_tree,
            implementation_commit=implementation_commit,
            active_receipt_path=qualification_path,
            active_receipt_sha256=qualification_sha256,
        )
        _validate_v0_3_implementation_delta(
            repo_root=repo_root,
            git_executable=git_executable,
            preflight_commit=qualification_preflight_commit,
            implementation_commit=implementation_commit,
            qualification_path=qualification_path,
            frozen_protocol_path=protocol_path,
        )
    _validate_candidate_protocol_lineage(
        parent=candidate_parent,
        frozen=frozen_candidate,
        layer_index=layer_index,
    )
    _validate_neighbor_protocol_lineage(
        parent=neighbor_parent,
        frozen=frozen_neighbor,
        repo_root=repo_root,
        candidate_protocol_path=candidate_protocol_path,
        candidate_protocol_sha256=candidate_sha256,
        comparison_group=comparison_group,
        global_row_key_sha256=global_row_key_sha256,
        qualification_path=qualification_path,
        qualification_sha256=qualification_sha256,
        qualification_fixture_sha256=(
            qualification_fixture_sha256
        ),
    )

    prepared_bindings = _require_mapping(
        document.get("prepared_bindings"),
        label="prepared_bindings",
        fields={
            "comparison_group",
            "global_row_key_schema_version",
            "global_row_key_sha256",
            "query_selection_sha256",
            "audit_config_sha256",
            "query_count",
            "query_seed",
        },
    )
    expected_prepared_bindings = {
        "comparison_group": comparison_group,
        "global_row_key_schema_version": (
            "spirallens.global-row-key.v0.2"
        ),
        "global_row_key_sha256": _require_sha256(
            global_row_key_sha256,
            label="global_row_key_sha256",
        ),
        "query_selection_sha256": _require_sha256(
            query_selection_sha256,
            label="query_selection_sha256",
        ),
        "audit_config_sha256": _require_sha256(
            audit_config_sha256,
            label="audit_config_sha256",
        ),
        "query_count": query_count,
        "query_seed": query_seed,
    }
    if dict(prepared_bindings) != expected_prepared_bindings:
        raise ValueError(
            "execution freeze prepared bindings differ"
        )

    claim_boundary = _require_mapping(
        document.get("claim_boundary"),
        label="claim_boundary",
        fields={
            "qualification_kind",
            "semantic_evidence",
            "scientific_target_evidence",
            "passing_audit_proves_retrieval_coverage_only",
            "candidate_is_not_verified_vortex",
        },
    )
    if dict(claim_boundary) != {
        "qualification_kind": "retrieval_plumbing",
        "semantic_evidence": False,
        "scientific_target_evidence": False,
        "passing_audit_proves_retrieval_coverage_only": True,
        "candidate_is_not_verified_vortex": True,
    }:
        raise ValueError("execution freeze claim boundary differs")

    single_shot_fields = {
        "prepare_only_before_outcome_allowed",
        "subject_audit_runs_allowed",
        "overwrite_allowed",
        "pass_is_terminal",
        "fail_is_terminal",
        "insufficient_is_terminal",
        "retry_after_observing_outcome_allowed",
        "tuning_from_this_outcome_allowed",
        "output_path",
    }
    single_shot_fields.add(
        "infrastructure_error_is_terminal"
        if qualified_freeze
        else "prior_unbound_attempt"
    )
    single_shot = _require_mapping(
        document.get("single_shot_contract"),
        label="single_shot_contract",
        fields=single_shot_fields,
    )
    prior_attempt = single_shot.get("prior_unbound_attempt")
    if (
        single_shot.get("prepare_only_before_outcome_allowed") is not True
        or single_shot.get("subject_audit_runs_allowed") != 1
        or single_shot.get("overwrite_allowed") is not False
        or single_shot.get("pass_is_terminal") is not True
        or single_shot.get("fail_is_terminal") is not True
        or single_shot.get("insufficient_is_terminal") is not True
        or single_shot.get("retry_after_observing_outcome_allowed")
        is not False
        or single_shot.get("tuning_from_this_outcome_allowed") is not False
        or single_shot.get("output_path") != str(output_path)
        or (
            qualified_freeze
            and single_shot.get("infrastructure_error_is_terminal")
            is not True
        )
        or (
            not qualified_freeze
            and (
                not isinstance(prior_attempt, Mapping)
                or dict(prior_attempt)
                != {
                    "status": "aborted_before_outcome",
                    "exit_code": 130,
                    "stdout_outcome_observed": False,
                    "artifact_written": False,
                    "bound_by_this_freeze": False,
                }
            )
        )
    ):
        raise ValueError("execution freeze single-shot contract is invalid")

    argv_template = execution.get("argv_template")
    required_argv_template = [
        str(process_image),
        "-m",
        "spirallens",
        "neighbor-audit",
        "--manifest",
        str(manifest_path),
        "--layer",
        str(layer_index),
        "--protocol",
        str(protocol_path),
        "--expected-protocol-sha256",
        protocol_sha256,
        "--execution-freeze",
        str(freeze_path),
        "--expected-execution-freeze-sha256",
        SELF_SHA256_PLACEHOLDER,
        "--output",
        str(output_path),
    ]
    if (
        argv_template != required_argv_template
    ):
        raise ValueError("execution freeze argv_template is invalid")
    expected_argv = [
        expected_digest if value == SELF_SHA256_PLACEHOLDER else value
        for value in argv_template
    ]
    if list(sys.orig_argv) != expected_argv:
        raise ValueError(
            "execution freeze argv differs from the exact invocation"
        )

    worker_runtime = current_worker_runtime_contract(actual_digest)
    comparable_worker_runtime = {
        key: value
        for key, value in worker_runtime.items()
        if key != "execution_freeze_sha256"
    }
    if not v0_3_freeze:
        comparable_worker_runtime.pop(
            "faiss_runtime_worker_source_sha256",
            None,
        )
    expected_worker_runtime = {
        key: str(runtime[key])
        for key in comparable_worker_runtime
    }
    if comparable_worker_runtime != expected_worker_runtime:
        raise ValueError(
            "execution freeze worker runtime contract differs"
        )
    return actual_digest, worker_runtime, backend_contract


def validate_subject_audit_execution_freeze(
    *,
    document: Mapping[str, Any],
    source_bytes: bytes,
    source_path: Path,
    expected_sha256: str,
    manifest_path: Path,
    manifest_sha256: str,
    protocol_path: Path,
    protocol_sha256: str,
    candidate_protocol_path: Path,
    candidate_protocol_sha256: str,
    recall_gate_path: Path,
    recall_gate_sha256: str,
    output_path: Path,
    layer_index: int,
    comparison_group: str,
    global_row_key_sha256: str,
    query_selection_sha256: str,
    audit_config_sha256: str,
    query_count: int,
    query_seed: int,
) -> ValidatedExecutionFreeze:
    """Validate and issue a capability that can be rechecked after audit."""

    arguments = {
        "document": document,
        "source_bytes": source_bytes,
        "source_path": source_path,
        "expected_sha256": expected_sha256,
        "manifest_path": manifest_path,
        "manifest_sha256": manifest_sha256,
        "protocol_path": protocol_path,
        "protocol_sha256": protocol_sha256,
        "candidate_protocol_path": candidate_protocol_path,
        "candidate_protocol_sha256": candidate_protocol_sha256,
        "recall_gate_path": recall_gate_path,
        "recall_gate_sha256": recall_gate_sha256,
        "output_path": output_path,
        "layer_index": layer_index,
        "comparison_group": comparison_group,
        "global_row_key_sha256": global_row_key_sha256,
        "query_selection_sha256": query_selection_sha256,
        "audit_config_sha256": audit_config_sha256,
        "query_count": query_count,
        "query_seed": query_seed,
    }
    digest, worker_runtime, backend_contract = _validate_freeze_core(
        **arguments
    )

    def revalidate() -> None:
        _validate_freeze_core(**arguments)

    return ValidatedExecutionFreeze(
        token=_CAPABILITY_TOKEN,
        sha256=digest,
        revalidate=revalidate,
        worker_runtime=worker_runtime,
        backend_contract=backend_contract,
    )
