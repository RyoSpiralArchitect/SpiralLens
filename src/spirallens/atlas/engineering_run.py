"""One-shot runner for the bounded public-example Pythia engineering lane."""

from __future__ import annotations

import hashlib
import inspect
import os
from pathlib import Path
import shutil
import stat
import subprocess
from typing import Any

from spirallens._repository_context import RepositoryContext
from spirallens.adapters import CAPTURE_IMPLEMENTATION_VERSION, PythiaAdapter
from spirallens.contexts import ContextRole, load_context_bank

from .engineering_protocol import (
    PublicExamplePlumbingProtocolIntegrityError,
    _build_public_example_plumbing_protocol_binding,
    load_public_example_plumbing_protocol,
    resolve_repository_relative_path,
    verify_implementation_source,
)
from .engineering_receipt import (
    _build_public_example_plumbing_receipt,
    write_public_example_plumbing_receipt,
)
from .id_sweep import ContextBankBinding, SweepConfig, run_id_sweep


class PublicExamplePlumbingRunError(RuntimeError):
    """Raised when the frozen engineering cell cannot execute as declared."""


_PYTHIA70_PARAMETER_COUNT = 70_426_624
_DISK_RESERVE_BYTES = 64 * 1024 * 1024
_RUNNER_REPOSITORY_PATH = "src/spirallens/atlas/engineering_run.py"


def _require_imported_source_origin(
    *,
    context: RepositoryContext,
    imported_file: str | Path | None,
    repository_path: str,
    label: str,
) -> None:
    """Fail closed when executing code is not from the declared checkout."""

    if not context.matches_imported_file(
        imported_file=imported_file,
        repository_path=repository_path,
    ):
        raise PublicExamplePlumbingRunError(
            f"{label} import origin differs from repository_root"
        )


def _require_offline_environment() -> None:
    required = ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")
    missing = [name for name in required if os.environ.get(name) != "1"]
    if missing:
        raise PublicExamplePlumbingRunError(
            "public-example capture requires offline environment flags: "
            + ", ".join(missing)
        )
    credential_names = (
        "HF_TOKEN",
        "HUGGING_FACE_HUB_TOKEN",
    )
    present = [name for name in credential_names if os.environ.get(name)]
    if present:
        raise PublicExamplePlumbingRunError(
            "public-example capture refuses inherited Hub credentials: "
            + ", ".join(present)
        )


def _stable_regular_file_sha256(path: str | Path) -> str:
    """Hash one resolved regular file while checking stable inode identity."""

    resolved = Path(path).resolve(strict=True)
    before = resolved.stat()
    if not stat.S_ISREG(before.st_mode):
        raise PublicExamplePlumbingRunError(
            f"model artifact is not a regular file: {resolved}"
        )
    digest = hashlib.sha256()
    with resolved.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise PublicExamplePlumbingRunError(
                f"model artifact identity changed before read: {resolved}"
            )
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
        after_read = os.fstat(handle.fileno())
    after = resolved.stat()
    identities = {
        (before.st_dev, before.st_ino, before.st_size),
        (opened.st_dev, opened.st_ino, opened.st_size),
        (after_read.st_dev, after_read.st_ino, after_read.st_size),
        (after.st_dev, after.st_ino, after.st_size),
    }
    if len(identities) != 1:
        raise PublicExamplePlumbingRunError(
            f"model artifact identity changed during read: {resolved}"
        )
    return digest.hexdigest()


def _require_real_directory(path: Path, *, label: str) -> None:
    """Require an existing directory with no symlink in its resolved chain."""

    resolved = path.resolve(strict=True)
    if not resolved.is_dir():
        raise PublicExamplePlumbingRunError(
            f"{label} must be an existing directory"
        )
    for item in (resolved, *resolved.parents):
        details = item.lstat()
        if stat.S_ISLNK(details.st_mode) or not stat.S_ISDIR(details.st_mode):
            raise PublicExamplePlumbingRunError(
                f"{label} parent chain must contain only real directories"
            )


def _resolve_verified_model_files(
    *,
    model_id: str,
    revision: str,
    expected: dict[str, str],
) -> tuple[dict[str, Path], dict[str, str]]:
    """Resolve exact cached Hub files and verify their stable content hashes."""

    try:
        from huggingface_hub import hf_hub_download
    except ImportError as error:  # pragma: no cover - optional dependency
        raise PublicExamplePlumbingRunError(
            "huggingface-hub is required for the public-example model lane"
        ) from error

    paths: dict[str, Path] = {}
    observed: dict[str, str] = {}
    for name in sorted(expected):
        try:
            downloaded = hf_hub_download(
                repo_id=model_id,
                filename=name,
                revision=revision,
                local_files_only=True,
            )
        except Exception as error:
            raise PublicExamplePlumbingRunError(
                f"exact cached model file is unavailable: {name}"
            ) from error
        path = Path(downloaded).resolve(strict=True)
        digest = _stable_regular_file_sha256(path)
        if digest != expected[name]:
            raise PublicExamplePlumbingProtocolIntegrityError(
                f"cached model file SHA-256 mismatch: {name}"
            )
        paths[name] = path
        observed[name] = digest
    return paths, observed


def _physical_memory_bytes() -> int:
    try:
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        pages = int(os.sysconf("SC_PHYS_PAGES"))
    except (AttributeError, OSError, TypeError, ValueError) as error:
        raise PublicExamplePlumbingRunError(
            "cannot determine physical memory for resource preflight"
        ) from error
    total = page_size * pages
    if total <= 0:
        raise PublicExamplePlumbingRunError(
            "physical memory preflight returned a non-positive value"
        )
    return total


def _resource_preflight(
    *,
    protocol: Any,
    model_paths: dict[str, Path],
    output_parent: Path,
    context_length: int,
) -> dict[str, object]:
    model_file_bytes = sum(path.stat().st_size for path in model_paths.values())
    parameter_bytes = _PYTHIA70_PARAMETER_COUNT * 4
    batch_working_bytes = protocol.capture.batch_size * (
        context_length * protocol.model.vocab_size * 4
        + 2 * protocol.model.num_layers * protocol.model.hidden_size * 4
    )
    minimum_peak_bytes = (
        model_file_bytes
        + parameter_bytes
        + batch_working_bytes
        + protocol.resource_budget.estimated_output_bytes
    )
    free_disk_bytes = shutil.disk_usage(output_parent).free
    physical_memory_bytes = _physical_memory_bytes()
    if (
        minimum_peak_bytes
        > protocol.resource_budget.estimated_peak_bytes
        or free_disk_bytes
        < protocol.resource_budget.max_estimated_output_bytes
        + _DISK_RESERVE_BYTES
        or physical_memory_bytes
        < protocol.resource_budget.max_estimated_peak_bytes
    ):
        raise PublicExamplePlumbingRunError(
            "live resources do not satisfy the frozen engineering budget"
        )
    return {
        "status": "pass",
        "estimator_id": protocol.resource_budget.estimator_id,
        "model_file_bytes": model_file_bytes,
        "minimum_peak_bytes": minimum_peak_bytes,
        "free_disk_bytes": free_disk_bytes,
        "physical_memory_bytes": physical_memory_bytes,
        "disk_reserve_bytes": _DISK_RESERVE_BYTES,
    }


def _verify_protocol_git_anchor(
    *,
    root: Path,
    protocol_path: Path,
    implementation_commit: str,
) -> str:
    try:
        relative = protocol_path.resolve(strict=True).relative_to(root)
    except ValueError as error:
        raise PublicExamplePlumbingRunError(
            "engineering protocol must be tracked inside the repository"
        ) from error
    relative_posix = relative.as_posix()
    try:
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "merge-base",
                "--is-ancestor",
                implementation_commit,
                head,
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "--error-unmatch",
                "--",
                relative_posix,
            ],
            check=True,
            capture_output=True,
        )
        tracked = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "show",
                f"HEAD:{relative_posix}",
            ],
            check=True,
            capture_output=True,
        ).stdout
        subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "diff",
                "--quiet",
                "HEAD",
                "--",
                relative_posix,
            ],
            check=True,
            capture_output=True,
        )
        staged = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "diff",
                "--cached",
                "--quiet",
                "HEAD",
                "--",
                relative_posix,
            ],
            check=True,
            capture_output=True,
        )
        del staged
    except (OSError, subprocess.CalledProcessError) as error:
        raise PublicExamplePlumbingRunError(
            "engineering protocol is not a clean tracked Git blob"
        ) from error
    if tracked != protocol_path.read_bytes():
        raise PublicExamplePlumbingRunError(
            "engineering protocol bytes differ from the tracked Git blob"
        )
    return head


def _verify_model_metadata(adapter: PythiaAdapter, protocol: Any) -> None:
    metadata = adapter.config_metadata()
    expected = {
        "model_id": protocol.model.model_id,
        "requested_revision": protocol.model.revision,
        "resolved_revision": protocol.model.revision,
        "architecture": protocol.model.architecture,
        "num_layers": protocol.model.num_layers,
        "hidden_size": protocol.model.hidden_size,
        "vocab_size": protocol.model.vocab_size,
        "parameter_count": _PYTHIA70_PARAMETER_COUNT,
        "parameter_devices": ["cpu"],
        "parameter_dtypes": ["float32"],
    }
    mismatched = [
        key for key, value in expected.items() if metadata.get(key) != value
    ]
    config = metadata.get("config")
    config_expected = {
        "num_attention_heads": protocol.model.num_attention_heads,
        "intermediate_size": protocol.model.intermediate_size,
        "max_position_embeddings": protocol.model.max_position_embeddings,
    }
    if not isinstance(config, dict) or any(
        config.get(key) != value for key, value in config_expected.items()
    ):
        mismatched.append("config_dimensions")
    if mismatched:
        raise PublicExamplePlumbingProtocolIntegrityError(
            "loaded model differs from the frozen engineering protocol: "
            + ", ".join(sorted(mismatched))
        )
    capture = adapter.capture_metadata()
    if (
        capture.get("capture_implementation")
        != {
            "name": "PythiaAdapter.observe_batch.residual_hooks",
            "version": CAPTURE_IMPLEMENTATION_VERSION,
            "accelerator_to_cpu_copy": "synchronous",
            "activation_dtype": "float32",
        }
        or capture.get("effective_parameter_layout")
        != [
            {
                "device": "cpu",
                "dtype": "float32",
                "parameter_tensors": 76,
                "parameter_values": _PYTHIA70_PARAMETER_COUNT,
            }
        ]
    ):
        raise PublicExamplePlumbingProtocolIntegrityError(
            "loaded model does not satisfy the exact production capture layout"
        )


def run_public_example_plumbing(
    *,
    protocol_path: str | Path,
    output_dir: str | Path,
    receipt_path: str | Path,
    expected_protocol_source_sha256: str,
    expected_protocol_canonical_sha256: str,
    repository_root: str | Path,
) -> dict[str, object]:
    """Execute and receipt one frozen, atlas-integrity-only Pythia capture."""

    context = RepositoryContext(
        root=Path(repository_root).resolve(strict=True),
    )
    _require_imported_source_origin(
        context=context,
        imported_file=__file__,
        repository_path=_RUNNER_REPOSITORY_PATH,
        label="public-example runner",
    )

    import torch

    root = context.root
    _require_offline_environment()
    loaded = load_public_example_plumbing_protocol(
        protocol_path,
        expected_source_sha256=expected_protocol_source_sha256,
        expected_canonical_sha256=expected_protocol_canonical_sha256,
    )
    protocol = loaded.protocol
    _require_imported_source_origin(
        context=context,
        imported_file=inspect.getsourcefile(PythiaAdapter),
        repository_path=protocol.source.implementation_repository_path,
        label="Pythia adapter",
    )
    verify_implementation_source(loaded, root)
    execution_commit = _verify_protocol_git_anchor(
        root=root,
        protocol_path=loaded.source_path,
        implementation_commit=protocol.source.implementation_commit,
    )

    output = Path(output_dir).resolve()
    receipt_output = Path(receipt_path).resolve()
    if output.name != protocol.capture.output_id:
        raise PublicExamplePlumbingRunError(
            "atlas output basename differs from the frozen output_id"
        )
    if output.exists():
        raise PublicExamplePlumbingRunError(
            f"atlas output already exists; fresh output is required: {output}"
        )
    if receipt_output.exists():
        raise PublicExamplePlumbingRunError(
            "receipt output already exists; overwrite is forbidden"
        )
    _require_real_directory(output.parent, label="atlas output parent")
    _require_real_directory(receipt_output.parent, label="receipt output parent")
    if receipt_output.is_relative_to(output):
        raise PublicExamplePlumbingRunError(
            "receipt must be published outside the activation atlas directory"
        )

    context_path = resolve_repository_relative_path(
        root,
        protocol.context_bank.path,
    )
    context_source_bytes = context_path.read_bytes()
    loaded_bank = load_context_bank(
        context_path,
        allowed_roles={ContextRole.EXAMPLE},
        expected_source_sha256=protocol.context_bank.source_sha256,
        expected_canonical_sha256=protocol.context_bank.canonical_sha256,
    )
    bank = loaded_bank.bank
    if (
        bank.claim_eligible is not False
        or bank.model.model_id != protocol.model.model_id
        or bank.model.resolved_revision != protocol.model.revision
        or bank.model.vocab_size != protocol.model.vocab_size
    ):
        raise PublicExamplePlumbingProtocolIntegrityError(
            "ContextBank differs from the frozen engineering protocol"
        )
    context_binding = ContextBankBinding(
        loaded=loaded_bank,
        context_id=protocol.context_bank.context_id,
        role=ContextRole.EXAMPLE,
    )

    expected_model_files = dict(protocol.model.files)
    model_paths, observed_model_files = _resolve_verified_model_files(
        model_id=protocol.model.model_id,
        revision=protocol.model.revision,
        expected=expected_model_files,
    )
    execution_preflight = _resource_preflight(
        protocol=protocol,
        model_paths=model_paths,
        output_parent=output.parent,
        context_length=len(context_binding.materialized_context_ids),
    )
    binding = _build_public_example_plumbing_protocol_binding(
        loaded,
        verified_model_files=observed_model_files,
        execution_preflight=execution_preflight,
    )

    adapter = PythiaAdapter.from_pretrained(
        protocol.model.model_id,
        revision=protocol.model.revision,
        device="cpu",
        local_files_only=True,
        torch_dtype=torch.float32,
    )
    _verify_model_metadata(adapter, protocol)
    for name, path in model_paths.items():
        if _stable_regular_file_sha256(path) != expected_model_files[name]:
            raise PublicExamplePlumbingProtocolIntegrityError(
                f"model file changed during load: {name}"
            )

    manifest = run_id_sweep(
        adapter,
        SweepConfig(
            output_dir=output,
            context_ids=context_binding.materialized_context_ids,
            position=context_binding.context.observation_position,
            batch_size=protocol.capture.batch_size,
            subset=protocol.token_selection.token_ids,
            max_tokens=None,
            context_bank_binding=context_binding,
            public_example_plumbing_protocol_binding=binding,
        ),
    )
    if manifest.get("status") != "complete":
        raise PublicExamplePlumbingRunError(
            "public-example activation atlas did not complete"
        )

    if loaded.source_path.read_bytes() != loaded.source_bytes:
        raise PublicExamplePlumbingProtocolIntegrityError(
            "engineering protocol changed during execution"
        )
    if (
        context_path.read_bytes() != context_source_bytes
        or loaded_bank.source_sha256
        != protocol.context_bank.source_sha256
    ):
        raise PublicExamplePlumbingProtocolIntegrityError(
            "ContextBank changed during execution"
        )
    verify_implementation_source(loaded, root)
    for name, path in model_paths.items():
        if _stable_regular_file_sha256(path) != expected_model_files[name]:
            raise PublicExamplePlumbingProtocolIntegrityError(
                f"model file changed during capture: {name}"
            )

    receipt = _build_public_example_plumbing_receipt(
        output,
        loaded_protocol=loaded,
    )
    write_public_example_plumbing_receipt(receipt_output, receipt)
    payload = receipt.to_dict()
    return {
        "command": "public-example-plumbing run",
        "status": "complete",
        "execution_class": protocol.execution_class,
        "protocol_id": protocol.protocol_id,
        "protocol_source_sha256": loaded.source_sha256,
        "protocol_canonical_sha256": loaded.canonical_sha256,
        "implementation_commit": protocol.source.implementation_commit,
        "execution_commit": execution_commit,
        "resource_preflight": execution_preflight,
        "model": {
            "id": protocol.model.model_id,
            "revision": protocol.model.revision,
            "device": protocol.capture.device,
            "dtype": protocol.capture.dtype,
            "model_files_sha256": expected_model_files,
        },
        "rows": payload["row_count"],
        "manifest": str((output / "manifest.json").resolve()),
        "manifest_sha256": payload["manifest"]["sha256"],
        "receipt": str(receipt_output),
        "receipt_sha256": receipt.sha256,
        "allowed_consumers": list(protocol.allowed_consumers),
        "execution_facts": payload["execution_facts"],
        "claim_boundary": payload["claim_boundary"],
        "d0_d8": payload["d0_d8"],
        "analysis_status": payload["analysis_status"],
    }
