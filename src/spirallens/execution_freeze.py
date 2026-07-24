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
import subprocess
import sys
from typing import Any

import numpy as np
import yaml

from spirallens import __version__ as SPIRALLENS_VERSION
from spirallens.neighbors.contracts import NeighborBackendDescriptor


EXECUTION_FREEZE_SCHEMA_VERSION = (
    "spirallens.subject-audit-freeze.v0.1"
)
SELF_SHA256_PLACEHOLDER = "<SELF_SHA256>"
_CAPABILITY_TOKEN = object()


class ValidatedExecutionFreeze:
    """Capability issued only after a complete execution-freeze preflight."""

    __slots__ = (
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
    """Describe the exact code and native runtime imported by a Faiss worker."""

    import faiss
    import faiss._swigfaiss as faiss_native

    package_root = Path(__file__).resolve().parent
    numpy_import = Path(np.__file__).resolve()
    faiss_import = Path(faiss.__file__).resolve()
    faiss_native_import = Path(faiss_native.__file__).resolve()
    process_image = process_image_path()
    contract = {
        "faiss_compile_options": str(faiss.get_compile_options()),
        "faiss_distribution_sha256": distribution_content_sha256(
            "faiss-cpu"
        ),
        "faiss_hnsw_source_sha256": _sha256_file(
            package_root / "neighbors" / "faiss_hnsw.py"
        ),
        "faiss_import_file": str(faiss_import),
        "faiss_import_sha256": _sha256_file(faiss_import),
        "faiss_native_file": str(faiss_native_import),
        "faiss_native_sha256": _sha256_file(faiss_native_import),
        "faiss_version": str(faiss.__version__),
        "faiss_worker_source_sha256": _sha256_file(
            package_root / "neighbors" / "_faiss_worker.py"
        ),
        "machine": platform.machine(),
        "numpy_distribution_sha256": distribution_content_sha256(
            "numpy"
        ),
        "numpy_import_file": str(numpy_import),
        "numpy_import_sha256": _sha256_file(numpy_import),
        "numpy_version": np.__version__,
        "process_image": str(process_image),
        "process_image_sha256": _sha256_file(process_image),
        "python_version": platform.python_version(),
        "system": platform.system(),
    }
    if execution_freeze_sha256 is not None:
        contract["execution_freeze_sha256"] = _require_sha256(
            execution_freeze_sha256,
            label="execution_freeze_sha256",
        )
    return contract


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


def _require_mapping(
    value: object,
    *,
    label: str,
    fields: set[str],
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{label} fields differ from the freeze contract")
    return value


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
) -> None:
    expected = copy.deepcopy(dict(parent))
    expected["protocol_id"] = (
        "pythia70-slot-only-001-layer0-neighbor-v0.2"
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
    if expected != dict(frozen):
        raise ValueError(
            "frozen neighbor protocol exceeds its allowlisted lineage"
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
) -> tuple[str, dict[str, str]]:
    import faiss
    import faiss._swigfaiss as faiss_native
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
    if (
        set(document) != expected_top_level
        or document.get("schema_version")
        != EXECUTION_FREEZE_SCHEMA_VERSION
        or not isinstance(document.get("freeze_id"), str)
        or not document["freeze_id"]
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
        fields={
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
        },
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
    expected_freeze_relative = (
        "protocols/"
        "pythia70_slot_only_001_layer0_subject_audit_freeze_v0_1.yaml"
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
    faiss_import = Path(faiss.__file__).resolve()
    faiss_native_import = Path(faiss_native.__file__).resolve()
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
        or runtime["faiss_version"] != faiss.__version__
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
        != faiss.get_compile_options()
        or _require_sha256(
            runtime["faiss_hnsw_source_sha256"],
            label="runtime.faiss_hnsw_source_sha256",
        )
        != _sha256_file(faiss_hnsw_source)
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
    neighbor_parent_path = (
        repo_root / "protocols" / "pythia_neighbor_v0_2.yaml"
    )
    candidate_parent_sha256 = (
        "ce3e6b6ba7c6cac026ba74671faf5c800e3d21bfc6abbf2641b9d03a37ceb2d8"
    )
    neighbor_parent_sha256 = (
        "45f6699badb314f68c43d5fee2bf2070405af13b518437e24590b0de9f117350"
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

    single_shot = _require_mapping(
        document.get("single_shot_contract"),
        label="single_shot_contract",
        fields={
            "prepare_only_before_outcome_allowed",
            "subject_audit_runs_allowed",
            "overwrite_allowed",
            "pass_is_terminal",
            "fail_is_terminal",
            "insufficient_is_terminal",
            "retry_after_observing_outcome_allowed",
            "tuning_from_this_outcome_allowed",
            "output_path",
            "prior_unbound_attempt",
        },
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
        or not isinstance(prior_attempt, Mapping)
        or dict(prior_attempt)
        != {
            "status": "aborted_before_outcome",
            "exit_code": 130,
            "stdout_outcome_observed": False,
            "artifact_written": False,
            "bound_by_this_freeze": False,
        }
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
    expected_worker_runtime = {
        key: str(runtime[key])
        for key in worker_runtime
        if key != "execution_freeze_sha256"
    }
    if any(
        worker_runtime[key] != expected
        for key, expected in expected_worker_runtime.items()
    ):
        raise ValueError(
            "execution freeze worker runtime contract differs"
        )
    return actual_digest, worker_runtime


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
    digest, worker_runtime = _validate_freeze_core(**arguments)

    def revalidate() -> None:
        _validate_freeze_core(**arguments)

    return ValidatedExecutionFreeze(
        token=_CAPABILITY_TOKEN,
        sha256=digest,
        revalidate=revalidate,
        worker_runtime=worker_runtime,
    )
