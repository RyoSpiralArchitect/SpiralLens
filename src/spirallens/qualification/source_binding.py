"""Read-only D0 source binding and logical-dependency provenance.

This module closes two Level-0 bookkeeping gaps without granting scientific
authority:

* a qualification engine binding is checked against both the current
  worktree bytes and the blobs at its declared ancestor commit; and
* the source-reviewed blind-input/prediction/oracle dependencies are
  reconstructed after scoring as an immutable, digest-chained, per-lane
  logical manifest.

The manifest is deliberately not a real-time, durable, or independently
observed event log.  It proves internal content joins and canonical dependency
order only; source review and process isolation remain separate obligations.

No network access, subject data, semantic labels, or integer/topology claims
are involved.
"""

from __future__ import annotations

import hashlib
import re
import stat
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import ClassVar

from spirallens.core.canonical import (
    canonical_json_bytes,
    canonical_json_sha256,
    sha256_bytes,
)
from spirallens.instrument_contracts import load_hypothesis_registry
from spirallens.referents import load_referent_contract_set

from .common import (
    AttemptStatus,
    CorePredictionClass,
    LoopPredictionClass,
    QualificationContractError,
    QualificationState,
    require_plain_int,
    require_sha256,
)
from .protocol import (
    EngineBinding,
    ModuleDigest,
    QualificationProtocol,
    RegistryBinding,
    RepositoryFileDigest,
)

SOURCE_BINDING_RECEIPT_SCHEMA_VERSION = (
    "spirallens.qualification-source-binding-receipt.v0.3"
)
EVENT_ENTRY_SCHEMA_VERSION = "spirallens.qualification-event-entry.v0.3"
EVENT_LEDGER_SCHEMA_VERSION = "spirallens.qualification-event-ledger.v0.3"
EVENT_LEDGER_RECEIPT_SCHEMA_VERSION = (
    "spirallens.qualification-event-ledger-receipt.v0.4"
)
PROTOCOL_VERIFIED_PAYLOAD_SCHEMA_VERSION = (
    "spirallens.qualification-protocol-verified-payload.v0.2"
)
BLIND_INPUT_PAYLOAD_SCHEMA_VERSION = "spirallens.qualification-blind-input-payload.v0.1"
PREDICTION_SEALED_PAYLOAD_SCHEMA_VERSION = (
    "spirallens.qualification-prediction-sealed-payload.v0.1"
)
ORACLE_MATERIALIZED_PAYLOAD_SCHEMA_VERSION = (
    "spirallens.qualification-oracle-materialized-payload.v0.1"
)
SCORED_PAYLOAD_SCHEMA_VERSION = "spirallens.qualification-scored-payload.v0.1"
RESULT_ASSEMBLED_PAYLOAD_SCHEMA_VERSION = (
    "spirallens.qualification-result-assembled-payload.v0.2"
)
MAX_EVENT_PAYLOAD_BYTES = 16 * 1024 * 1024
MAX_EVENT_LEDGER_ENTRIES = 262_144
GENESIS_ENTRY_SHA256 = hashlib.sha256(
    b"spirallens.qualification-event-ledger.genesis.v0.1"
).hexdigest()

_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_MODULE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*$")
_LANE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,255}$")


class QualificationSourceBindingError(QualificationContractError):
    """Raised when a declared D0 source binding cannot be proved locally."""


def _require_commit(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _COMMIT.fullmatch(value) is None:
        raise QualificationSourceBindingError(
            f"{label} must be a lowercase 40-character Git commit"
        )
    return value


def _require_constant(value: object, expected: object, *, label: str) -> None:
    if type(value) is not type(expected) or value != expected:
        raise QualificationContractError(f"{label} must equal {expected!r}")


def _require_relative_path(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise QualificationContractError(
            f"{label} must be a non-empty repository-relative path"
        )
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise QualificationContractError(
            f"{label} must be a normalized repository-relative POSIX path"
        )
    return value


def _require_lane_id(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _LANE_ID.fullmatch(value) is None:
        raise QualificationContractError(
            f"{label} must be a lowercase portable lane identifier"
        )
    return value


def _require_exact_keys(
    value: Mapping[str, object],
    expected: set[str] | frozenset[str],
    *,
    label: str,
) -> None:
    actual = set(value)
    if actual != set(expected):
        raise QualificationContractError(
            f"{label} fields differ from the contract: "
            f"missing={sorted(set(expected) - actual)}, "
            f"unknown={sorted(actual - set(expected))}"
        )


def _require_mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise QualificationContractError(f"{label} must be a string-keyed mapping")
    return value


def _require_list(value: object, *, label: str) -> list[object]:
    if not isinstance(value, list):
        raise QualificationContractError(f"{label} must be a JSON array")
    return value


def _git(
    root: Path,
    arguments: list[str],
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=check,
            capture_output=True,
        )
    except OSError as error:
        raise QualificationSourceBindingError(
            "cannot execute the local Git source-binding checks"
        ) from error
    except subprocess.CalledProcessError as error:
        command = " ".join(arguments[:2])
        raise QualificationSourceBindingError(
            f"local Git source-binding check failed: {command}"
        ) from error


def _git_text(root: Path, arguments: list[str]) -> str:
    raw = _git(root, arguments).stdout
    try:
        return raw.decode("ascii").strip()
    except UnicodeDecodeError as error:
        raise QualificationSourceBindingError(
            "local Git identity output must be ASCII"
        ) from error


def _repository_root(repository_root: str | Path) -> Path:
    try:
        root = Path(repository_root).resolve(strict=True)
    except OSError as error:
        raise QualificationSourceBindingError(
            "repository_root must resolve to an existing directory"
        ) from error
    if not root.is_dir():
        raise QualificationSourceBindingError("repository_root must be a directory")
    top_level = _git_text(root, ["rev-parse", "--show-toplevel"])
    try:
        resolved_top_level = Path(top_level).resolve(strict=True)
    except OSError as error:
        raise QualificationSourceBindingError(
            "Git reported an invalid worktree root"
        ) from error
    if resolved_top_level != root:
        raise QualificationSourceBindingError(
            "repository_root must be the exact Git worktree root"
        )
    return root


def _resolve_explicit_repo_file(
    root: Path,
    path: str | Path,
    *,
    label: str,
) -> tuple[Path, str]:
    unresolved = Path(path)
    candidate = unresolved if unresolved.is_absolute() else root / unresolved
    if candidate.is_symlink():
        raise QualificationSourceBindingError(f"{label} must not be a symlink")
    try:
        resolved = candidate.resolve(strict=True)
        relative = resolved.relative_to(root)
    except (OSError, ValueError) as error:
        raise QualificationSourceBindingError(
            f"{label} must be an existing file inside repository_root"
        ) from error
    relative_posix = relative.as_posix()
    _require_relative_path(relative_posix, label=f"{label} relative path")
    return resolved, relative_posix


def _read_stable_regular_file(path: Path, *, label: str) -> bytes:
    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode):
            raise QualificationSourceBindingError(f"{label} must be a regular file")
        if stat.S_ISLNK(before.st_mode):
            raise QualificationSourceBindingError(f"{label} must not be a symlink")
        source = path.read_bytes()
        after = path.lstat()
    except QualificationSourceBindingError:
        raise
    except OSError as error:
        raise QualificationSourceBindingError(f"cannot safely read {label}") from error
    identity_before = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    identity_after = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )
    if identity_before != identity_after or len(source) != after.st_size:
        raise QualificationSourceBindingError(f"{label} changed while it was read")
    return source


def _verify_clean_head_file(
    root: Path,
    path: str | Path,
    *,
    label: str,
) -> tuple[Path, str, bytes]:
    resolved, relative = _resolve_explicit_repo_file(root, path, label=label)
    _git(root, ["ls-files", "--error-unmatch", "--", relative])
    status_before = _git(
        root,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all", "--", relative],
    ).stdout
    if status_before:
        raise QualificationSourceBindingError(
            f"{label} has a tracked or untracked worktree difference"
        )
    source = _read_stable_regular_file(resolved, label=label)
    head_blob = _git(root, ["show", f"HEAD:{relative}"]).stdout
    if source != head_blob:
        raise QualificationSourceBindingError(
            f"{label} bytes differ from the current HEAD blob"
        )
    status_after = _git(
        root,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all", "--", relative],
    ).stdout
    if status_after:
        raise QualificationSourceBindingError(
            f"{label} changed during source-binding verification"
        )
    if _read_stable_regular_file(resolved, label=label) != source:
        raise QualificationSourceBindingError(
            f"{label} bytes changed during source-binding verification"
        )
    return resolved, relative, source


def _module_repository_path_candidates(module: str) -> tuple[str, str]:
    source_stem = PurePosixPath("src", *module.split("."))
    return (
        f"{source_stem.as_posix()}.py",
        f"{source_stem.as_posix()}/__init__.py",
    )


def module_repository_path(
    module: str,
    *,
    repository_root: str | Path | None = None,
) -> str:
    """Map a dotted module or package to its exact repository source path.

    A package executes its ``__init__.py`` before any child module.  Treating
    the package name as ``src/<package>.py`` would therefore leave executable
    source outside the engine binding.  When a repository root is available,
    this resolver requires exactly one of the module and package candidates to
    exist.  The no-root form resolves against this checkout and retains the
    historical ``.py`` fallback solely for detached receipt construction.
    """

    if not isinstance(module, str) or _MODULE.fullmatch(module) is None:
        raise QualificationSourceBindingError(
            "module must be a dotted Python module name"
        )
    module_path, package_path = _module_repository_path_candidates(module)
    if repository_root is None:
        root = Path(__file__).resolve().parents[3]
        strict = False
    else:
        root = Path(repository_root)
        strict = True
    existing = tuple(
        candidate
        for candidate in (module_path, package_path)
        if (root / candidate).is_file()
    )
    if len(existing) == 1:
        return existing[0]
    if len(existing) > 1:
        raise QualificationSourceBindingError(
            f"module {module!r} has ambiguous module and package sources"
        )
    if strict:
        raise QualificationSourceBindingError(
            f"module {module!r} has no Python source inside repository_root"
        )
    return module_path


@dataclass(frozen=True, slots=True)
class ModuleSourceReceipt:
    """One module proved equal in declaration, worktree, HEAD, and bound blob."""

    module: str
    repository_path: str
    declared_sha256: str
    working_sha256: str
    head_blob_sha256: str
    bound_blob_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.module, str) or _MODULE.fullmatch(self.module) is None:
            raise QualificationContractError(
                "module source receipt module must be a dotted module name"
            )
        allowed_paths = _module_repository_path_candidates(self.module)
        if self.repository_path not in allowed_paths:
            raise QualificationContractError(
                "module source receipt path differs from its dotted module or package"
            )
        digests = (
            self.declared_sha256,
            self.working_sha256,
            self.head_blob_sha256,
            self.bound_blob_sha256,
        )
        for index, digest in enumerate(digests):
            require_sha256(digest, label=f"module source digest[{index}]")
        if len(set(digests)) != 1:
            raise QualificationContractError(
                "module declaration, worktree, HEAD, and bound blob must agree"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "module": self.module,
            "repository_path": self.repository_path,
            "declared_sha256": self.declared_sha256,
            "working_sha256": self.working_sha256,
            "head_blob_sha256": self.head_blob_sha256,
            "bound_blob_sha256": self.bound_blob_sha256,
        }


@dataclass(frozen=True, slots=True)
class RegistrySourceReceipt:
    """Loader-verified hypothesis-registry source and canonical identity."""

    repository_path: str
    source_sha256: str
    canonical_sha256: str

    def __post_init__(self) -> None:
        _require_relative_path(
            self.repository_path, label="registry receipt repository_path"
        )
        require_sha256(self.source_sha256, label="registry receipt source_sha256")
        require_sha256(self.canonical_sha256, label="registry receipt canonical_sha256")

    def to_dict(self) -> dict[str, object]:
        return {
            "repository_path": self.repository_path,
            "source_sha256": self.source_sha256,
            "canonical_sha256": self.canonical_sha256,
        }


@dataclass(frozen=True, slots=True)
class ReferentSourceReceipt:
    """Loader-verified canonical referent source and registry join."""

    repository_path: str
    source_sha256: str
    canonical_sha256: str
    hypothesis_registry_canonical_sha256: str

    def __post_init__(self) -> None:
        _require_relative_path(
            self.repository_path, label="referent receipt repository_path"
        )
        require_sha256(self.source_sha256, label="referent receipt source_sha256")
        require_sha256(self.canonical_sha256, label="referent receipt canonical_sha256")
        require_sha256(
            self.hypothesis_registry_canonical_sha256,
            label="referent receipt hypothesis_registry_canonical_sha256",
        )
        if self.source_sha256 != self.canonical_sha256:
            raise QualificationContractError(
                "canonical referent source and canonical digests must agree"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "repository_path": self.repository_path,
            "source_sha256": self.source_sha256,
            "canonical_sha256": self.canonical_sha256,
            "hypothesis_registry_canonical_sha256": (
                self.hypothesis_registry_canonical_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class QualificationSourceBindingReceipt:
    """Self-checking Level-0 receipt for the protocol's source declarations."""

    engine: EngineBinding
    registry: RegistryBinding
    head_commit: str
    modules: tuple[ModuleSourceReceipt, ...]
    hypothesis_registry: RegistrySourceReceipt
    referent_contracts: ReferentSourceReceipt
    schema_version: str = SOURCE_BINDING_RECEIPT_SCHEMA_VERSION
    claim_ceiling: str = "level_0"
    git_ancestry_verified: bool = True
    module_worktree_clean: bool = True
    registry_loader_verified: bool = True
    referent_loader_verified: bool = True
    scientific_claim_eligible: bool = False
    subject_access_authorized: bool = False
    semantic_authority: bool = False
    integer_or_topology_authority: bool = False
    in_process_callable_identity_verified: bool = False
    python_or_native_runtime_attested: bool = False
    hostile_local_mutation_resistant: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.engine, EngineBinding):
            raise TypeError("engine must be an EngineBinding")
        if not isinstance(self.registry, RegistryBinding):
            raise TypeError("registry must be a RegistryBinding")
        _require_commit(self.head_commit, label="head_commit")
        if type(self.modules) is not tuple:
            raise TypeError("modules must be an immutable tuple")
        if any(not isinstance(item, ModuleSourceReceipt) for item in self.modules):
            raise TypeError("modules must contain only ModuleSourceReceipt")
        _require_constant(
            self.schema_version,
            SOURCE_BINDING_RECEIPT_SCHEMA_VERSION,
            label="source binding receipt schema_version",
        )
        _require_constant(
            self.claim_ceiling,
            "level_0",
            label="source binding receipt claim_ceiling",
        )
        for name in (
            "git_ancestry_verified",
            "module_worktree_clean",
            "registry_loader_verified",
            "referent_loader_verified",
        ):
            _require_constant(
                getattr(self, name), True, label=f"source binding receipt {name}"
            )
        for name in (
            "scientific_claim_eligible",
            "subject_access_authorized",
            "semantic_authority",
            "integer_or_topology_authority",
            "in_process_callable_identity_verified",
            "python_or_native_runtime_attested",
            "hostile_local_mutation_resistant",
        ):
            _require_constant(
                getattr(self, name), False, label=f"source binding receipt {name}"
            )
        expected_modules = tuple(
            (item.module, item.sha256) for item in self.engine.modules
        )
        observed_modules = tuple(
            (item.module, item.declared_sha256) for item in self.modules
        )
        if observed_modules != expected_modules:
            raise QualificationContractError(
                "module receipts differ from the declared engine module map"
            )
        if (
            self.hypothesis_registry.source_sha256
            != self.registry.registry_source_sha256
            or self.hypothesis_registry.canonical_sha256
            != self.registry.registry_canonical_sha256
        ):
            raise QualificationContractError(
                "hypothesis-registry receipt differs from the declared binding"
            )
        if (
            self.referent_contracts.canonical_sha256
            != self.registry.referent_canonical_sha256
            or self.referent_contracts.hypothesis_registry_canonical_sha256
            != self.registry.registry_canonical_sha256
        ):
            raise QualificationContractError(
                "referent receipt differs from the declared registry join"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "claim_ceiling": self.claim_ceiling,
            "engine": self.engine.to_dict(),
            "registry": self.registry.to_dict(),
            "head_commit": self.head_commit,
            "modules": [item.to_dict() for item in self.modules],
            "hypothesis_registry": self.hypothesis_registry.to_dict(),
            "referent_contracts": self.referent_contracts.to_dict(),
            "git_ancestry_verified": self.git_ancestry_verified,
            "module_worktree_clean": self.module_worktree_clean,
            "registry_loader_verified": self.registry_loader_verified,
            "referent_loader_verified": self.referent_loader_verified,
            "scientific_claim_eligible": self.scientific_claim_eligible,
            "subject_access_authorized": self.subject_access_authorized,
            "semantic_authority": self.semantic_authority,
            "integer_or_topology_authority": self.integer_or_topology_authority,
            "in_process_callable_identity_verified": (
                self.in_process_callable_identity_verified
            ),
            "python_or_native_runtime_attested": (
                self.python_or_native_runtime_attested
            ),
            "hostile_local_mutation_resistant": (self.hostile_local_mutation_resistant),
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


@dataclass(frozen=True, slots=True)
class QualificationSourceBindingSummary:
    """Compact Result join derived only from a live source-binding receipt.

    The summary is not a substitute for the full receipt during validation.
    A persisted result must either carry that receipt or require it as a
    companion and call :meth:`verify_receipt`.
    """

    source_binding_receipt_sha256: str
    engine_commit: str
    head_commit: str
    module_count: int
    registry_source_sha256: str
    registry_canonical_sha256: str
    referent_canonical_sha256: str
    source_binding_verified: bool = True
    claim_ceiling: str = "level_0"
    scientific_claim_eligible: bool = False
    subject_access_authorized: bool = False
    semantic_authority: bool = False
    integer_or_topology_authority: bool = False
    in_process_callable_identity_verified: bool = False
    python_or_native_runtime_attested: bool = False
    hostile_local_mutation_resistant: bool = False

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "source_binding_receipt_sha256",
            "engine_commit",
            "head_commit",
            "module_count",
            "registry_source_sha256",
            "registry_canonical_sha256",
            "referent_canonical_sha256",
            "source_binding_verified",
            "claim_ceiling",
            "scientific_claim_eligible",
            "subject_access_authorized",
            "semantic_authority",
            "integer_or_topology_authority",
            "in_process_callable_identity_verified",
            "python_or_native_runtime_attested",
            "hostile_local_mutation_resistant",
        }
    )

    def __post_init__(self) -> None:
        require_sha256(
            self.source_binding_receipt_sha256,
            label="source binding summary receipt_sha256",
        )
        _require_commit(
            self.engine_commit, label="source binding summary engine_commit"
        )
        _require_commit(self.head_commit, label="source binding summary head_commit")
        require_plain_int(
            self.module_count, label="source binding summary module_count", minimum=1
        )
        for name in (
            "registry_source_sha256",
            "registry_canonical_sha256",
            "referent_canonical_sha256",
        ):
            require_sha256(getattr(self, name), label=f"source binding summary {name}")
        _require_constant(
            self.source_binding_verified,
            True,
            label="source binding summary source_binding_verified",
        )
        _require_constant(
            self.claim_ceiling,
            "level_0",
            label="source binding summary claim_ceiling",
        )
        for name in (
            "scientific_claim_eligible",
            "subject_access_authorized",
            "semantic_authority",
            "integer_or_topology_authority",
            "in_process_callable_identity_verified",
            "python_or_native_runtime_attested",
            "hostile_local_mutation_resistant",
        ):
            _require_constant(
                getattr(self, name), False, label=f"source binding summary {name}"
            )

    @classmethod
    def from_receipt(
        cls,
        receipt: QualificationSourceBindingReceipt,
    ) -> QualificationSourceBindingSummary:
        """Derive the only accepted compact source-binding summary."""

        if not isinstance(receipt, QualificationSourceBindingReceipt):
            raise TypeError("receipt must be a QualificationSourceBindingReceipt")
        return cls(
            source_binding_receipt_sha256=receipt.canonical_sha256,
            engine_commit=receipt.engine.commit,
            head_commit=receipt.head_commit,
            module_count=len(receipt.modules),
            registry_source_sha256=receipt.hypothesis_registry.source_sha256,
            registry_canonical_sha256=receipt.hypothesis_registry.canonical_sha256,
            referent_canonical_sha256=receipt.referent_contracts.canonical_sha256,
        )

    def verify_receipt(self, receipt: QualificationSourceBindingReceipt) -> None:
        """Require exact equality with a freshly validated full receipt."""

        if self != type(self).from_receipt(receipt):
            raise QualificationContractError(
                "source binding summary differs from its full receipt"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "source_binding_receipt_sha256": self.source_binding_receipt_sha256,
            "engine_commit": self.engine_commit,
            "head_commit": self.head_commit,
            "module_count": self.module_count,
            "registry_source_sha256": self.registry_source_sha256,
            "registry_canonical_sha256": self.registry_canonical_sha256,
            "referent_canonical_sha256": self.referent_canonical_sha256,
            "source_binding_verified": self.source_binding_verified,
            "claim_ceiling": self.claim_ceiling,
            "scientific_claim_eligible": self.scientific_claim_eligible,
            "subject_access_authorized": self.subject_access_authorized,
            "semantic_authority": self.semantic_authority,
            "integer_or_topology_authority": self.integer_or_topology_authority,
            "in_process_callable_identity_verified": (
                self.in_process_callable_identity_verified
            ),
            "python_or_native_runtime_attested": (
                self.python_or_native_runtime_attested
            ),
            "hostile_local_mutation_resistant": (self.hostile_local_mutation_resistant),
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> QualificationSourceBindingSummary:
        """Parse a compact join without treating it as live source evidence."""

        document = _require_mapping(value, label="qualification source binding summary")
        _require_exact_keys(
            document,
            cls._ROOT_KEYS,
            label="qualification source binding summary",
        )
        for name, expected in (
            ("source_binding_verified", True),
            ("claim_ceiling", "level_0"),
            ("scientific_claim_eligible", False),
            ("subject_access_authorized", False),
            ("semantic_authority", False),
            ("integer_or_topology_authority", False),
            ("in_process_callable_identity_verified", False),
            ("python_or_native_runtime_attested", False),
            ("hostile_local_mutation_resistant", False),
        ):
            _require_constant(
                document[name],
                expected,
                label=f"source binding summary {name}",
            )
        return cls(
            source_binding_receipt_sha256=require_sha256(
                document["source_binding_receipt_sha256"],
                label="source binding summary receipt_sha256",
            ),
            engine_commit=_require_commit(
                document["engine_commit"],
                label="source binding summary engine_commit",
            ),
            head_commit=_require_commit(
                document["head_commit"],
                label="source binding summary head_commit",
            ),
            module_count=require_plain_int(
                document["module_count"],
                label="source binding summary module_count",
                minimum=1,
            ),
            registry_source_sha256=require_sha256(
                document["registry_source_sha256"],
                label="source binding summary registry_source_sha256",
            ),
            registry_canonical_sha256=require_sha256(
                document["registry_canonical_sha256"],
                label="source binding summary registry_canonical_sha256",
            ),
            referent_canonical_sha256=require_sha256(
                document["referent_canonical_sha256"],
                label="source binding summary referent_canonical_sha256",
            ),
        )


def _verify_module(
    root: Path,
    bound_commit: str,
    declaration: ModuleDigest,
) -> ModuleSourceReceipt:
    repository_path = module_repository_path(
        declaration.module,
        repository_root=root,
    )
    _, relative, working_bytes = _verify_clean_head_file(
        root,
        repository_path,
        label=f"engine module {declaration.module}",
    )
    if relative != repository_path:
        raise QualificationSourceBindingError(
            "dotted engine module did not resolve to its exact repository path"
        )
    bound_blob = _git(root, ["show", f"{bound_commit}:{repository_path}"]).stdout
    declared = declaration.sha256
    working_sha256 = sha256_bytes(working_bytes)
    head_blob_sha256 = sha256_bytes(
        _git(root, ["show", f"HEAD:{repository_path}"]).stdout
    )
    bound_blob_sha256 = sha256_bytes(bound_blob)
    if (
        working_sha256 != declared
        or head_blob_sha256 != declared
        or bound_blob_sha256 != declared
    ):
        raise QualificationSourceBindingError(
            f"engine module {declaration.module} does not match its declared "
            "worktree, HEAD, and bound-commit digest"
        )
    return ModuleSourceReceipt(
        module=declaration.module,
        repository_path=repository_path,
        declared_sha256=declared,
        working_sha256=working_sha256,
        head_blob_sha256=head_blob_sha256,
        bound_blob_sha256=bound_blob_sha256,
    )


def _verify_official_executable(
    root: Path,
    bound_commit: str,
    declaration: RepositoryFileDigest,
) -> None:
    """Require one official script to match worktree, HEAD, and engine commit."""

    if not isinstance(declaration, RepositoryFileDigest):
        raise TypeError("declaration must be a RepositoryFileDigest")
    _, relative, working_bytes = _verify_clean_head_file(
        root,
        declaration.repository_path,
        label=f"official executable {declaration.repository_path}",
    )
    if relative != declaration.repository_path:
        raise QualificationSourceBindingError(
            "official executable did not resolve to its exact repository path"
        )
    bound_blob = _git(
        root,
        ["show", f"{bound_commit}:{declaration.repository_path}"],
    ).stdout
    head_blob = _git(
        root,
        ["show", f"HEAD:{declaration.repository_path}"],
    ).stdout
    if any(
        sha256_bytes(source) != declaration.sha256
        for source in (working_bytes, head_blob, bound_blob)
    ):
        raise QualificationSourceBindingError(
            f"official executable {declaration.repository_path} does not match "
            "its declared worktree, HEAD, and bound-commit digest"
        )


def verify_source_binding(
    *,
    engine: EngineBinding,
    registry: RegistryBinding,
    repository_root: str | Path,
    registry_path: str | Path,
    referent_path: str | Path,
) -> QualificationSourceBindingReceipt:
    """Verify exact engine, registry, and referent sources without a network."""

    if not isinstance(engine, EngineBinding):
        raise TypeError("engine must be an EngineBinding")
    if not isinstance(registry, RegistryBinding):
        raise TypeError("registry must be a RegistryBinding")
    root = _repository_root(repository_root)
    head_commit = _git_text(root, ["rev-parse", "HEAD"])
    _require_commit(head_commit, label="current HEAD")
    resolved_bound_commit = _git_text(
        root, ["rev-parse", f"{engine.commit}^{{commit}}"]
    )
    if resolved_bound_commit != engine.commit:
        raise QualificationSourceBindingError(
            "engine.commit did not resolve to the exact declared commit"
        )
    ancestry = _git(
        root,
        ["merge-base", "--is-ancestor", engine.commit, head_commit],
        check=False,
    )
    if ancestry.returncode != 0:
        raise QualificationSourceBindingError(
            "engine.commit is not an ancestor of the current HEAD"
        )

    modules = tuple(
        _verify_module(root, engine.commit, declaration)
        for declaration in engine.modules
    )
    for declaration in engine.official_executables:
        _verify_official_executable(root, engine.commit, declaration)

    registry_resolved, registry_relative, registry_bytes = _verify_clean_head_file(
        root,
        registry_path,
        label="hypothesis registry",
    )
    try:
        loaded_registry = load_hypothesis_registry(
            registry_resolved,
            expected_source_sha256=registry.registry_source_sha256,
            expected_canonical_sha256=registry.registry_canonical_sha256,
        )
    except Exception as error:
        raise QualificationSourceBindingError(
            "hypothesis registry failed its existing strict loader"
        ) from error
    if sha256_bytes(registry_bytes) != loaded_registry.source_sha256:
        raise QualificationSourceBindingError(
            "hypothesis-registry bytes changed across source verification"
        )

    referent_resolved, referent_relative, referent_bytes = _verify_clean_head_file(
        root,
        referent_path,
        label="referent contract set",
    )
    try:
        loaded_referents = load_referent_contract_set(
            referent_resolved,
            expected_source_sha256=registry.referent_canonical_sha256,
            expected_canonical_sha256=registry.referent_canonical_sha256,
        )
    except Exception as error:
        raise QualificationSourceBindingError(
            "referent contract set failed its existing strict loader"
        ) from error
    if sha256_bytes(referent_bytes) != loaded_referents.source_sha256:
        raise QualificationSourceBindingError(
            "referent bytes changed across source verification"
        )
    if (
        loaded_referents.contract_set.hypothesis_registry_canonical_sha256
        != loaded_registry.canonical_sha256
    ):
        raise QualificationSourceBindingError(
            "referent contract set is not joined to the loaded hypothesis registry"
        )

    return QualificationSourceBindingReceipt(
        engine=engine,
        registry=registry,
        head_commit=head_commit,
        modules=modules,
        hypothesis_registry=RegistrySourceReceipt(
            repository_path=registry_relative,
            source_sha256=loaded_registry.source_sha256,
            canonical_sha256=loaded_registry.canonical_sha256,
        ),
        referent_contracts=ReferentSourceReceipt(
            repository_path=referent_relative,
            source_sha256=loaded_referents.source_sha256,
            canonical_sha256=loaded_referents.canonical_sha256,
            hypothesis_registry_canonical_sha256=(
                loaded_referents.contract_set.hypothesis_registry_canonical_sha256
            ),
        ),
    )


def verify_protocol_source_binding(
    protocol: QualificationProtocol,
    *,
    repository_root: str | Path,
    registry_path: str | Path,
    referent_path: str | Path,
) -> QualificationSourceBindingReceipt:
    """Verify the source bindings carried by one typed qualification protocol."""

    if not isinstance(protocol, QualificationProtocol):
        raise TypeError("protocol must be a QualificationProtocol")
    return verify_source_binding(
        engine=protocol.engine,
        registry=protocol.registry,
        repository_root=repository_root,
        registry_path=registry_path,
        referent_path=referent_path,
    )


def _require_exact_resolved_commit(
    root: Path,
    commit: str,
    *,
    label: str,
) -> str:
    declared = _require_commit(commit, label=label)
    resolved = _git_text(root, ["rev-parse", f"{declared}^{{commit}}"])
    if resolved != declared:
        raise QualificationSourceBindingError(
            f"{label} did not resolve to the exact declared commit"
        )
    return resolved


def _require_commit_ancestry(
    root: Path,
    ancestor: str,
    descendant: str,
    *,
    label: str,
) -> None:
    ancestry = _git(
        root,
        ["merge-base", "--is-ancestor", ancestor, descendant],
        check=False,
    )
    if ancestry.returncode != 0:
        raise QualificationSourceBindingError(label)


def _historical_blob_sha256(
    root: Path,
    commit: str,
    repository_path: str,
    *,
    label: str,
) -> str:
    _require_relative_path(repository_path, label=f"{label} repository path")
    try:
        source = _git(root, ["show", f"{commit}:{repository_path}"]).stdout
    except QualificationSourceBindingError as error:
        raise QualificationSourceBindingError(
            f"{label} is absent from the execution HEAD"
        ) from error
    return sha256_bytes(source)


def verify_protocol_source_binding_successor(
    protocol: QualificationProtocol,
    *,
    source_binding_summary: QualificationSourceBindingSummary,
    repository_root: str | Path,
    registry_path: str | Path,
    referent_path: str | Path,
) -> QualificationSourceBindingReceipt:
    """Revalidate one exact execution receipt from a clean successor HEAD.

    A qualification result binds the source receipt produced at execution
    time, including that receipt's exact ``head_commit`` and canonical digest.
    A later artifact-only commit must not silently replace those identities
    with a receipt for the new HEAD.  This verifier instead:

    * performs the ordinary complete live-source verification at current HEAD;
    * proves ``engine.commit -> execution HEAD -> current HEAD`` ancestry;
    * checks every declared module, registry, and referent blob at the stored
      execution HEAD against the frozen protocol identities; and
    * reconstructs the historical receipt and requires the existing compact
      summary to verify it by exact canonical digest equality.

    The returned receipt is the reconstructed execution-time receipt, not the
    current-HEAD receipt.  This remains source-only Level-0 evidence: it does
    not attest in-process callable identity, Python/native runtime state, or
    resistance to hostile local mutation.
    """

    if not isinstance(protocol, QualificationProtocol):
        raise TypeError("protocol must be a QualificationProtocol")
    if not isinstance(source_binding_summary, QualificationSourceBindingSummary):
        raise TypeError(
            "source_binding_summary must be a QualificationSourceBindingSummary"
        )
    root = _repository_root(repository_root)
    current_receipt = verify_protocol_source_binding(
        protocol,
        repository_root=root,
        registry_path=registry_path,
        referent_path=referent_path,
    )
    engine_commit = _require_exact_resolved_commit(
        root,
        protocol.engine.commit,
        label="protocol engine commit",
    )
    execution_head = _require_exact_resolved_commit(
        root,
        source_binding_summary.head_commit,
        label="stored execution HEAD",
    )
    current_head = _require_exact_resolved_commit(
        root,
        current_receipt.head_commit,
        label="current live HEAD",
    )
    _require_commit_ancestry(
        root,
        engine_commit,
        execution_head,
        label="engine.commit is not an ancestor of the stored execution HEAD",
    )
    _require_commit_ancestry(
        root,
        execution_head,
        current_head,
        label="stored execution HEAD is not an ancestor of the current HEAD",
    )

    current_modules = {item.module: item for item in current_receipt.modules}
    for declaration in protocol.engine.modules:
        module_receipt = current_modules.get(declaration.module)
        if module_receipt is None:
            raise QualificationSourceBindingError(
                "current live receipt omits a protocol engine module"
            )
        historical_sha256 = _historical_blob_sha256(
            root,
            execution_head,
            module_receipt.repository_path,
            label=f"engine module {declaration.module}",
        )
        if historical_sha256 != declaration.sha256:
            raise QualificationSourceBindingError(
                f"engine module {declaration.module} at the stored execution "
                "HEAD differs from the frozen protocol digest"
            )

    for declaration in protocol.engine.official_executables:
        historical_sha256 = _historical_blob_sha256(
            root,
            execution_head,
            declaration.repository_path,
            label=f"official executable {declaration.repository_path}",
        )
        if historical_sha256 != declaration.sha256:
            raise QualificationSourceBindingError(
                f"official executable {declaration.repository_path} at the "
                "stored execution HEAD differs from the frozen protocol digest"
            )

    registry_sha256 = _historical_blob_sha256(
        root,
        execution_head,
        current_receipt.hypothesis_registry.repository_path,
        label="hypothesis registry",
    )
    if registry_sha256 != protocol.registry.registry_source_sha256:
        raise QualificationSourceBindingError(
            "hypothesis-registry blob at the stored execution HEAD differs "
            "from the frozen protocol digest"
        )
    referent_sha256 = _historical_blob_sha256(
        root,
        execution_head,
        current_receipt.referent_contracts.repository_path,
        label="referent contract set",
    )
    if referent_sha256 != protocol.registry.referent_canonical_sha256:
        raise QualificationSourceBindingError(
            "referent blob at the stored execution HEAD differs from the "
            "frozen protocol digest"
        )

    historical_receipt = replace(
        current_receipt,
        head_commit=execution_head,
    )
    try:
        source_binding_summary.verify_receipt(historical_receipt)
    except QualificationContractError as error:
        raise QualificationSourceBindingError(
            "stored source-binding summary differs from the reconstructed "
            "execution-time receipt"
        ) from error
    return historical_receipt


def qualification_event_lane_ids(
    protocol: QualificationProtocol,
) -> tuple[str, ...]:
    """Derive the exact canonical core/cell lane manifest from a protocol."""

    if not isinstance(protocol, QualificationProtocol):
        raise TypeError("protocol must be a QualificationProtocol")
    lane_ids = tuple(
        sorted(
            (
                *(f"core.{cell.core_cell_id}" for cell in protocol.expected_core_cells),
                *(f"loop.{cell.cell_id}" for cell in protocol.expected_cells),
            )
        )
    )
    return _canonical_lane_ids(
        lane_ids, label="protocol-derived qualification event lane IDs"
    )


class QualificationEventKind(str, Enum):
    """The sole permitted truth-blind-to-scored event chronology."""

    PROTOCOL_VERIFIED = "protocol_verified"
    BLIND_INPUT_GENERATED = "blind_input_generated"
    PREDICTION_SEALED = "prediction_sealed"
    ORACLE_MATERIALIZED = "oracle_materialized"
    SCORED = "scored"
    RESULT_ASSEMBLED = "result_assembled"


_EVENT_ORDER = tuple(QualificationEventKind)


def _optional_payload_sha256(value: object, *, label: str) -> str | None:
    if value is None:
        return None
    return require_sha256(value, label=label)


def _payload_reason_codes(value: object, *, label: str) -> tuple[str, ...]:
    values = _require_list(value, label=label)
    result = tuple(
        _require_lane_id(item, label=f"{label}[{index}]")
        for index, item in enumerate(values)
    )
    if result != tuple(sorted(set(result))):
        raise QualificationContractError(
            f"{label} must be unique and in canonical order"
        )
    return result


def _payload_attempt_status(value: object, *, label: str) -> AttemptStatus:
    try:
        return AttemptStatus(value)
    except (TypeError, ValueError) as error:
        raise QualificationContractError(f"{label} is not supported") from error


def _payload_state(value: object, *, label: str) -> QualificationState:
    try:
        return QualificationState(value)
    except (TypeError, ValueError) as error:
        raise QualificationContractError(f"{label} is not supported") from error


def _payload_prediction_class(
    value: object,
    *,
    lane_id: str,
    label: str,
) -> str:
    enum_type: type[CorePredictionClass | LoopPredictionClass]
    enum_type = (
        CorePredictionClass if lane_id.startswith("core.") else LoopPredictionClass
    )
    try:
        return enum_type(value).value
    except (TypeError, ValueError) as error:
        raise QualificationContractError(f"{label} is not supported") from error


@dataclass(frozen=True, slots=True)
class ProtocolVerifiedEventPayload:
    """Exact protocol/source/cell identity known before a blind lane starts."""

    lane_id: str
    protocol_id: str
    protocol_source_sha256: str
    protocol_canonical_sha256: str
    selection_freeze_artifact_sha256: str
    selection_attempt_claim_sha256: str
    source_binding_receipt_sha256: str
    lane_contract_sha256: str
    schema_version: str = PROTOCOL_VERIFIED_PAYLOAD_SCHEMA_VERSION

    event_kind: ClassVar[QualificationEventKind] = (
        QualificationEventKind.PROTOCOL_VERIFIED
    )
    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "event_kind",
            "lane_id",
            "protocol_id",
            "protocol_source_sha256",
            "protocol_canonical_sha256",
            "selection_freeze_artifact_sha256",
            "selection_attempt_claim_sha256",
            "source_binding_receipt_sha256",
            "lane_contract_sha256",
        }
    )

    def __post_init__(self) -> None:
        _require_constant(
            self.schema_version,
            PROTOCOL_VERIFIED_PAYLOAD_SCHEMA_VERSION,
            label="protocol-verified payload schema_version",
        )
        _require_lane_id(self.lane_id, label="protocol-verified payload lane_id")
        _require_lane_id(
            self.protocol_id, label="protocol-verified payload protocol_id"
        )
        for name in (
            "protocol_source_sha256",
            "protocol_canonical_sha256",
            "selection_freeze_artifact_sha256",
            "selection_attempt_claim_sha256",
            "source_binding_receipt_sha256",
            "lane_contract_sha256",
        ):
            require_sha256(
                getattr(self, name),
                label=f"protocol-verified payload {name}",
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "event_kind": self.event_kind.value,
            "lane_id": self.lane_id,
            "protocol_id": self.protocol_id,
            "protocol_source_sha256": self.protocol_source_sha256,
            "protocol_canonical_sha256": self.protocol_canonical_sha256,
            "selection_freeze_artifact_sha256": (self.selection_freeze_artifact_sha256),
            "selection_attempt_claim_sha256": (self.selection_attempt_claim_sha256),
            "source_binding_receipt_sha256": self.source_binding_receipt_sha256,
            "lane_contract_sha256": self.lane_contract_sha256,
        }

    @classmethod
    def from_dict(cls, value: object) -> ProtocolVerifiedEventPayload:
        document = _require_mapping(value, label="protocol-verified event payload")
        _require_exact_keys(
            document,
            cls._ROOT_KEYS,
            label="protocol-verified event payload",
        )
        _require_constant(
            document["event_kind"],
            cls.event_kind.value,
            label="protocol-verified payload event_kind",
        )
        return cls(
            schema_version=document["schema_version"],  # type: ignore[arg-type]
            lane_id=_require_lane_id(
                document["lane_id"], label="protocol-verified payload lane_id"
            ),
            protocol_id=_require_lane_id(
                document["protocol_id"], label="protocol-verified payload protocol_id"
            ),
            protocol_source_sha256=require_sha256(
                document["protocol_source_sha256"],
                label="protocol-verified payload protocol_source_sha256",
            ),
            protocol_canonical_sha256=require_sha256(
                document["protocol_canonical_sha256"],
                label="protocol-verified payload protocol_canonical_sha256",
            ),
            selection_freeze_artifact_sha256=require_sha256(
                document["selection_freeze_artifact_sha256"],
                label=("protocol-verified payload selection_freeze_artifact_sha256"),
            ),
            selection_attempt_claim_sha256=require_sha256(
                document["selection_attempt_claim_sha256"],
                label=("protocol-verified payload selection_attempt_claim_sha256"),
            ),
            source_binding_receipt_sha256=require_sha256(
                document["source_binding_receipt_sha256"],
                label="protocol-verified payload source_binding_receipt_sha256",
            ),
            lane_contract_sha256=require_sha256(
                document["lane_contract_sha256"],
                label="protocol-verified payload lane_contract_sha256",
            ),
        )


@dataclass(frozen=True, slots=True)
class BlindInputGeneratedEventPayload:
    """Typed blind-input identity joined to the preceding protocol event."""

    lane_id: str
    protocol_payload_sha256: str
    attempt_status: AttemptStatus
    input_evidence_sha256: str
    blind_input_fingerprint_sha256: str | None
    schema_version: str = BLIND_INPUT_PAYLOAD_SCHEMA_VERSION

    event_kind: ClassVar[QualificationEventKind] = (
        QualificationEventKind.BLIND_INPUT_GENERATED
    )
    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "event_kind",
            "lane_id",
            "protocol_payload_sha256",
            "attempt_status",
            "input_evidence_sha256",
            "blind_input_fingerprint_sha256",
        }
    )

    def __post_init__(self) -> None:
        _require_constant(
            self.schema_version,
            BLIND_INPUT_PAYLOAD_SCHEMA_VERSION,
            label="blind-input payload schema_version",
        )
        _require_lane_id(self.lane_id, label="blind-input payload lane_id")
        require_sha256(
            self.protocol_payload_sha256,
            label="blind-input payload protocol_payload_sha256",
        )
        if not isinstance(self.attempt_status, AttemptStatus):
            raise TypeError("blind-input attempt_status must be an AttemptStatus")
        require_sha256(
            self.input_evidence_sha256,
            label="blind-input payload input_evidence_sha256",
        )
        blind = _optional_payload_sha256(
            self.blind_input_fingerprint_sha256,
            label="blind-input payload blind_input_fingerprint_sha256",
        )
        if (self.attempt_status is AttemptStatus.NOT_RUN) != (blind is None):
            raise QualificationContractError(
                "blind-input fingerprint must be null exactly for not_run lanes"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "event_kind": self.event_kind.value,
            "lane_id": self.lane_id,
            "protocol_payload_sha256": self.protocol_payload_sha256,
            "attempt_status": self.attempt_status.value,
            "input_evidence_sha256": self.input_evidence_sha256,
            "blind_input_fingerprint_sha256": self.blind_input_fingerprint_sha256,
        }

    @classmethod
    def from_dict(cls, value: object) -> BlindInputGeneratedEventPayload:
        document = _require_mapping(value, label="blind-input event payload")
        _require_exact_keys(document, cls._ROOT_KEYS, label="blind-input event payload")
        _require_constant(
            document["event_kind"],
            cls.event_kind.value,
            label="blind-input payload event_kind",
        )
        return cls(
            schema_version=document["schema_version"],  # type: ignore[arg-type]
            lane_id=_require_lane_id(
                document["lane_id"], label="blind-input payload lane_id"
            ),
            protocol_payload_sha256=require_sha256(
                document["protocol_payload_sha256"],
                label="blind-input payload protocol_payload_sha256",
            ),
            attempt_status=_payload_attempt_status(
                document["attempt_status"],
                label="blind-input payload attempt_status",
            ),
            input_evidence_sha256=require_sha256(
                document["input_evidence_sha256"],
                label="blind-input payload input_evidence_sha256",
            ),
            blind_input_fingerprint_sha256=_optional_payload_sha256(
                document["blind_input_fingerprint_sha256"],
                label="blind-input payload blind_input_fingerprint_sha256",
            ),
        )


@dataclass(frozen=True, slots=True)
class PredictionSealedEventPayload:
    """Typed sealed-prediction identity with an explicit blind-input join."""

    lane_id: str
    blind_input_payload_sha256: str
    attempt_status: AttemptStatus
    prediction_evidence_sha256: str
    prediction_fingerprint_sha256: str | None
    prediction_class: str
    schema_version: str = PREDICTION_SEALED_PAYLOAD_SCHEMA_VERSION

    event_kind: ClassVar[QualificationEventKind] = (
        QualificationEventKind.PREDICTION_SEALED
    )
    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "event_kind",
            "lane_id",
            "blind_input_payload_sha256",
            "attempt_status",
            "prediction_evidence_sha256",
            "prediction_fingerprint_sha256",
            "prediction_class",
        }
    )

    def __post_init__(self) -> None:
        _require_constant(
            self.schema_version,
            PREDICTION_SEALED_PAYLOAD_SCHEMA_VERSION,
            label="prediction-sealed payload schema_version",
        )
        _require_lane_id(self.lane_id, label="prediction-sealed payload lane_id")
        require_sha256(
            self.blind_input_payload_sha256,
            label="prediction-sealed payload blind_input_payload_sha256",
        )
        if not isinstance(self.attempt_status, AttemptStatus):
            raise TypeError("prediction-sealed attempt_status must be AttemptStatus")
        require_sha256(
            self.prediction_evidence_sha256,
            label="prediction-sealed payload prediction_evidence_sha256",
        )
        prediction = _optional_payload_sha256(
            self.prediction_fingerprint_sha256,
            label="prediction-sealed payload prediction_fingerprint_sha256",
        )
        normalized = _payload_prediction_class(
            self.prediction_class,
            lane_id=self.lane_id,
            label="prediction-sealed payload prediction_class",
        )
        if normalized != self.prediction_class:
            raise QualificationContractError(
                "prediction-sealed prediction_class is not canonical"
            )
        none_value = (
            CorePredictionClass.NONE.value
            if self.lane_id.startswith("core.")
            else LoopPredictionClass.NONE.value
        )
        if self.attempt_status is AttemptStatus.NOT_RUN:
            if prediction is not None or self.prediction_class != none_value:
                raise QualificationContractError(
                    "not_run prediction payloads require null fingerprint and "
                    "the lane-specific none class"
                )
        elif prediction is None or self.prediction_class == none_value:
            raise QualificationContractError(
                "attempted prediction payloads require a sealed fingerprint "
                "and a non-none class"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "event_kind": self.event_kind.value,
            "lane_id": self.lane_id,
            "blind_input_payload_sha256": self.blind_input_payload_sha256,
            "attempt_status": self.attempt_status.value,
            "prediction_evidence_sha256": self.prediction_evidence_sha256,
            "prediction_fingerprint_sha256": self.prediction_fingerprint_sha256,
            "prediction_class": self.prediction_class,
        }

    @classmethod
    def from_dict(cls, value: object) -> PredictionSealedEventPayload:
        document = _require_mapping(value, label="prediction-sealed event payload")
        _require_exact_keys(
            document,
            cls._ROOT_KEYS,
            label="prediction-sealed event payload",
        )
        _require_constant(
            document["event_kind"],
            cls.event_kind.value,
            label="prediction-sealed payload event_kind",
        )
        lane_id = _require_lane_id(
            document["lane_id"], label="prediction-sealed payload lane_id"
        )
        return cls(
            schema_version=document["schema_version"],  # type: ignore[arg-type]
            lane_id=lane_id,
            blind_input_payload_sha256=require_sha256(
                document["blind_input_payload_sha256"],
                label="prediction-sealed payload blind_input_payload_sha256",
            ),
            attempt_status=_payload_attempt_status(
                document["attempt_status"],
                label="prediction-sealed payload attempt_status",
            ),
            prediction_evidence_sha256=require_sha256(
                document["prediction_evidence_sha256"],
                label="prediction-sealed payload prediction_evidence_sha256",
            ),
            prediction_fingerprint_sha256=_optional_payload_sha256(
                document["prediction_fingerprint_sha256"],
                label="prediction-sealed payload prediction_fingerprint_sha256",
            ),
            prediction_class=_payload_prediction_class(
                document["prediction_class"],
                lane_id=lane_id,
                label="prediction-sealed payload prediction_class",
            ),
        )


@dataclass(frozen=True, slots=True)
class OracleMaterializedEventPayload:
    """Typed oracle identity materialized only after prediction sealing."""

    lane_id: str
    prediction_payload_sha256: str
    attempt_status: AttemptStatus
    oracle_evidence_sha256: str
    oracle_fingerprint_sha256: str | None
    schema_version: str = ORACLE_MATERIALIZED_PAYLOAD_SCHEMA_VERSION

    event_kind: ClassVar[QualificationEventKind] = (
        QualificationEventKind.ORACLE_MATERIALIZED
    )
    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "event_kind",
            "lane_id",
            "prediction_payload_sha256",
            "attempt_status",
            "oracle_evidence_sha256",
            "oracle_fingerprint_sha256",
        }
    )

    def __post_init__(self) -> None:
        _require_constant(
            self.schema_version,
            ORACLE_MATERIALIZED_PAYLOAD_SCHEMA_VERSION,
            label="oracle-materialized payload schema_version",
        )
        _require_lane_id(self.lane_id, label="oracle-materialized payload lane_id")
        require_sha256(
            self.prediction_payload_sha256,
            label="oracle-materialized payload prediction_payload_sha256",
        )
        if not isinstance(self.attempt_status, AttemptStatus):
            raise TypeError("oracle-materialized attempt_status must be AttemptStatus")
        require_sha256(
            self.oracle_evidence_sha256,
            label="oracle-materialized payload oracle_evidence_sha256",
        )
        oracle = _optional_payload_sha256(
            self.oracle_fingerprint_sha256,
            label="oracle-materialized payload oracle_fingerprint_sha256",
        )
        if (self.attempt_status is AttemptStatus.NOT_RUN) != (oracle is None):
            raise QualificationContractError(
                "oracle fingerprint must be null exactly for not_run lanes"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "event_kind": self.event_kind.value,
            "lane_id": self.lane_id,
            "prediction_payload_sha256": self.prediction_payload_sha256,
            "attempt_status": self.attempt_status.value,
            "oracle_evidence_sha256": self.oracle_evidence_sha256,
            "oracle_fingerprint_sha256": self.oracle_fingerprint_sha256,
        }

    @classmethod
    def from_dict(cls, value: object) -> OracleMaterializedEventPayload:
        document = _require_mapping(value, label="oracle-materialized event payload")
        _require_exact_keys(
            document,
            cls._ROOT_KEYS,
            label="oracle-materialized event payload",
        )
        _require_constant(
            document["event_kind"],
            cls.event_kind.value,
            label="oracle-materialized payload event_kind",
        )
        return cls(
            schema_version=document["schema_version"],  # type: ignore[arg-type]
            lane_id=_require_lane_id(
                document["lane_id"], label="oracle-materialized payload lane_id"
            ),
            prediction_payload_sha256=require_sha256(
                document["prediction_payload_sha256"],
                label="oracle-materialized payload prediction_payload_sha256",
            ),
            attempt_status=_payload_attempt_status(
                document["attempt_status"],
                label="oracle-materialized payload attempt_status",
            ),
            oracle_evidence_sha256=require_sha256(
                document["oracle_evidence_sha256"],
                label="oracle-materialized payload oracle_evidence_sha256",
            ),
            oracle_fingerprint_sha256=_optional_payload_sha256(
                document["oracle_fingerprint_sha256"],
                label="oracle-materialized payload oracle_fingerprint_sha256",
            ),
        )


@dataclass(frozen=True, slots=True)
class ScoredEventPayload:
    """Exact normalized cell identity and mechanically recorded verdict."""

    lane_id: str
    oracle_payload_sha256: str
    attempt_status: AttemptStatus
    prediction_class: str
    state: QualificationState
    reason_codes: tuple[str, ...]
    normalized_cell_summary_sha256: str
    schema_version: str = SCORED_PAYLOAD_SCHEMA_VERSION

    event_kind: ClassVar[QualificationEventKind] = QualificationEventKind.SCORED
    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "event_kind",
            "lane_id",
            "oracle_payload_sha256",
            "attempt_status",
            "prediction_class",
            "state",
            "reason_codes",
            "normalized_cell_summary_sha256",
        }
    )

    def __post_init__(self) -> None:
        _require_constant(
            self.schema_version,
            SCORED_PAYLOAD_SCHEMA_VERSION,
            label="scored payload schema_version",
        )
        _require_lane_id(self.lane_id, label="scored payload lane_id")
        require_sha256(
            self.oracle_payload_sha256,
            label="scored payload oracle_payload_sha256",
        )
        if not isinstance(self.attempt_status, AttemptStatus):
            raise TypeError("scored attempt_status must be AttemptStatus")
        normalized = _payload_prediction_class(
            self.prediction_class,
            lane_id=self.lane_id,
            label="scored payload prediction_class",
        )
        if normalized != self.prediction_class:
            raise QualificationContractError("scored prediction_class is not canonical")
        if not isinstance(self.state, QualificationState):
            raise TypeError("scored state must be QualificationState")
        _payload_reason_codes(
            list(self.reason_codes),
            label="scored payload reason_codes",
        )
        require_sha256(
            self.normalized_cell_summary_sha256,
            label="scored payload normalized_cell_summary_sha256",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "event_kind": self.event_kind.value,
            "lane_id": self.lane_id,
            "oracle_payload_sha256": self.oracle_payload_sha256,
            "attempt_status": self.attempt_status.value,
            "prediction_class": self.prediction_class,
            "state": self.state.value,
            "reason_codes": list(self.reason_codes),
            "normalized_cell_summary_sha256": (self.normalized_cell_summary_sha256),
        }

    @classmethod
    def from_dict(cls, value: object) -> ScoredEventPayload:
        document = _require_mapping(value, label="scored event payload")
        _require_exact_keys(document, cls._ROOT_KEYS, label="scored event payload")
        _require_constant(
            document["event_kind"],
            cls.event_kind.value,
            label="scored payload event_kind",
        )
        lane_id = _require_lane_id(document["lane_id"], label="scored payload lane_id")
        return cls(
            schema_version=document["schema_version"],  # type: ignore[arg-type]
            lane_id=lane_id,
            oracle_payload_sha256=require_sha256(
                document["oracle_payload_sha256"],
                label="scored payload oracle_payload_sha256",
            ),
            attempt_status=_payload_attempt_status(
                document["attempt_status"],
                label="scored payload attempt_status",
            ),
            prediction_class=_payload_prediction_class(
                document["prediction_class"],
                lane_id=lane_id,
                label="scored payload prediction_class",
            ),
            state=_payload_state(document["state"], label="scored payload state"),
            reason_codes=_payload_reason_codes(
                document["reason_codes"],
                label="scored payload reason_codes",
            ),
            normalized_cell_summary_sha256=require_sha256(
                document["normalized_cell_summary_sha256"],
                label="scored payload normalized_cell_summary_sha256",
            ),
        )


@dataclass(frozen=True, slots=True)
class ResultAssembledEventPayload:
    """Exact normalized primary/nonvacuity/stratum projection identity."""

    lane_id: str
    scored_payload_sha256: str
    result_id: str
    result_evidence_root_sha256: str
    selection_freeze_artifact_sha256: str
    selection_attempt_claim_sha256: str
    normalized_primary_summary_sha256: str
    normalized_nonvacuity_summary_sha256: str | None
    normalized_strata_projection_sha256: str
    schema_version: str = RESULT_ASSEMBLED_PAYLOAD_SCHEMA_VERSION

    event_kind: ClassVar[QualificationEventKind] = (
        QualificationEventKind.RESULT_ASSEMBLED
    )
    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "event_kind",
            "lane_id",
            "scored_payload_sha256",
            "result_id",
            "result_evidence_root_sha256",
            "selection_freeze_artifact_sha256",
            "selection_attempt_claim_sha256",
            "normalized_primary_summary_sha256",
            "normalized_nonvacuity_summary_sha256",
            "normalized_strata_projection_sha256",
        }
    )

    def __post_init__(self) -> None:
        _require_constant(
            self.schema_version,
            RESULT_ASSEMBLED_PAYLOAD_SCHEMA_VERSION,
            label="result-assembled payload schema_version",
        )
        _require_lane_id(self.lane_id, label="result-assembled payload lane_id")
        _require_lane_id(self.result_id, label="result-assembled payload result_id")
        for name in (
            "scored_payload_sha256",
            "result_evidence_root_sha256",
            "selection_freeze_artifact_sha256",
            "selection_attempt_claim_sha256",
            "normalized_primary_summary_sha256",
            "normalized_strata_projection_sha256",
        ):
            require_sha256(
                getattr(self, name),
                label=f"result-assembled payload {name}",
            )
        nonvacuity = _optional_payload_sha256(
            self.normalized_nonvacuity_summary_sha256,
            label=("result-assembled payload normalized_nonvacuity_summary_sha256"),
        )
        if self.lane_id.startswith("core.") and nonvacuity is not None:
            raise QualificationContractError(
                "core result-assembly payloads cannot carry loop nonvacuity"
            )
        if self.lane_id.startswith("loop.") and nonvacuity is None:
            raise QualificationContractError(
                "loop result-assembly payloads require nonvacuity identity"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "event_kind": self.event_kind.value,
            "lane_id": self.lane_id,
            "scored_payload_sha256": self.scored_payload_sha256,
            "result_id": self.result_id,
            "result_evidence_root_sha256": self.result_evidence_root_sha256,
            "selection_freeze_artifact_sha256": (self.selection_freeze_artifact_sha256),
            "selection_attempt_claim_sha256": (self.selection_attempt_claim_sha256),
            "normalized_primary_summary_sha256": (
                self.normalized_primary_summary_sha256
            ),
            "normalized_nonvacuity_summary_sha256": (
                self.normalized_nonvacuity_summary_sha256
            ),
            "normalized_strata_projection_sha256": (
                self.normalized_strata_projection_sha256
            ),
        }

    @classmethod
    def from_dict(cls, value: object) -> ResultAssembledEventPayload:
        document = _require_mapping(value, label="result-assembled event payload")
        _require_exact_keys(
            document,
            cls._ROOT_KEYS,
            label="result-assembled event payload",
        )
        _require_constant(
            document["event_kind"],
            cls.event_kind.value,
            label="result-assembled payload event_kind",
        )
        return cls(
            schema_version=document["schema_version"],  # type: ignore[arg-type]
            lane_id=_require_lane_id(
                document["lane_id"], label="result-assembled payload lane_id"
            ),
            scored_payload_sha256=require_sha256(
                document["scored_payload_sha256"],
                label="result-assembled payload scored_payload_sha256",
            ),
            result_id=_require_lane_id(
                document["result_id"], label="result-assembled payload result_id"
            ),
            result_evidence_root_sha256=require_sha256(
                document["result_evidence_root_sha256"],
                label="result-assembled payload result_evidence_root_sha256",
            ),
            selection_freeze_artifact_sha256=require_sha256(
                document["selection_freeze_artifact_sha256"],
                label=("result-assembled payload selection_freeze_artifact_sha256"),
            ),
            selection_attempt_claim_sha256=require_sha256(
                document["selection_attempt_claim_sha256"],
                label=("result-assembled payload selection_attempt_claim_sha256"),
            ),
            normalized_primary_summary_sha256=require_sha256(
                document["normalized_primary_summary_sha256"],
                label=("result-assembled payload normalized_primary_summary_sha256"),
            ),
            normalized_nonvacuity_summary_sha256=_optional_payload_sha256(
                document["normalized_nonvacuity_summary_sha256"],
                label=("result-assembled payload normalized_nonvacuity_summary_sha256"),
            ),
            normalized_strata_projection_sha256=require_sha256(
                document["normalized_strata_projection_sha256"],
                label=("result-assembled payload normalized_strata_projection_sha256"),
            ),
        )


QualificationEventPayload = (
    ProtocolVerifiedEventPayload
    | BlindInputGeneratedEventPayload
    | PredictionSealedEventPayload
    | OracleMaterializedEventPayload
    | ScoredEventPayload
    | ResultAssembledEventPayload
)

_PAYLOAD_TYPES: dict[QualificationEventKind, type[QualificationEventPayload]] = {
    QualificationEventKind.PROTOCOL_VERIFIED: ProtocolVerifiedEventPayload,
    QualificationEventKind.BLIND_INPUT_GENERATED: BlindInputGeneratedEventPayload,
    QualificationEventKind.PREDICTION_SEALED: PredictionSealedEventPayload,
    QualificationEventKind.ORACLE_MATERIALIZED: OracleMaterializedEventPayload,
    QualificationEventKind.SCORED: ScoredEventPayload,
    QualificationEventKind.RESULT_ASSEMBLED: ResultAssembledEventPayload,
}


def parse_qualification_event_payload(
    value: object,
) -> QualificationEventPayload:
    """Parse one exact event-kind-specific payload and reject all other JSON."""

    document = _require_mapping(value, label="qualification event payload")
    try:
        event_kind = QualificationEventKind(document.get("event_kind"))
    except (TypeError, ValueError) as error:
        raise QualificationContractError(
            "qualification event payload kind is not supported"
        ) from error
    return _PAYLOAD_TYPES[event_kind].from_dict(document)


def qualification_event_payload_sha256(payload: QualificationEventPayload) -> str:
    """Return the canonical digest of one validated typed event payload."""

    if not isinstance(payload, tuple(_PAYLOAD_TYPES.values())):
        raise TypeError("payload must be a typed qualification event payload")
    return canonical_json_sha256(payload.to_dict())


@dataclass(frozen=True, slots=True)
class QualificationEvent:
    """One globally chained entry in one primary/cell execution lane."""

    sequence_number: int
    lane_id: str
    event_kind: QualificationEventKind
    payload: QualificationEventPayload
    payload_sha256: str
    previous_entry_sha256: str
    entry_sha256: str
    schema_version: str = EVENT_ENTRY_SCHEMA_VERSION

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "sequence_number",
            "lane_id",
            "event_kind",
            "payload",
            "payload_sha256",
            "previous_entry_sha256",
            "entry_sha256",
        }
    )

    def __post_init__(self) -> None:
        _require_constant(
            self.schema_version,
            EVENT_ENTRY_SCHEMA_VERSION,
            label="event schema_version",
        )
        require_plain_int(
            self.sequence_number, label="event sequence_number", minimum=0
        )
        _require_lane_id(self.lane_id, label="event lane_id")
        if not isinstance(self.event_kind, QualificationEventKind):
            raise TypeError("event_kind must be a QualificationEventKind")
        if not isinstance(self.payload, _PAYLOAD_TYPES[self.event_kind]):
            raise QualificationContractError(
                "event payload type differs from event_kind"
            )
        if self.payload.lane_id != self.lane_id:
            raise QualificationContractError(
                "event payload lane differs from its enclosing event"
            )
        require_sha256(self.payload_sha256, label="event payload_sha256")
        if self.payload_sha256 != qualification_event_payload_sha256(self.payload):
            raise QualificationContractError(
                "event payload digest differs from its typed payload"
            )
        require_sha256(self.previous_entry_sha256, label="event previous_entry_sha256")
        require_sha256(self.entry_sha256, label="event entry_sha256")

    def unsigned_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "sequence_number": self.sequence_number,
            "lane_id": self.lane_id,
            "event_kind": self.event_kind.value,
            "payload_sha256": self.payload_sha256,
            "previous_entry_sha256": self.previous_entry_sha256,
        }

    @property
    def expected_entry_sha256(self) -> str:
        return canonical_json_sha256(self.unsigned_dict())

    def to_dict(self) -> dict[str, object]:
        return {
            **self.unsigned_dict(),
            "payload": self.payload.to_dict(),
            "entry_sha256": self.entry_sha256,
        }

    @classmethod
    def create(
        cls,
        *,
        sequence_number: int,
        lane_id: str,
        event_kind: QualificationEventKind,
        payload: QualificationEventPayload,
        previous_entry_sha256: str,
    ) -> QualificationEvent:
        payload_sha256 = qualification_event_payload_sha256(payload)
        unsigned = {
            "schema_version": EVENT_ENTRY_SCHEMA_VERSION,
            "sequence_number": sequence_number,
            "lane_id": lane_id,
            "event_kind": event_kind.value,
            "payload_sha256": payload_sha256,
            "previous_entry_sha256": previous_entry_sha256,
        }
        return cls(
            sequence_number=sequence_number,
            lane_id=lane_id,
            event_kind=event_kind,
            payload=payload,
            payload_sha256=payload_sha256,
            previous_entry_sha256=previous_entry_sha256,
            entry_sha256=canonical_json_sha256(unsigned),
        )

    @classmethod
    def from_dict(cls, value: object) -> QualificationEvent:
        document = _require_mapping(value, label="qualification event")
        _require_exact_keys(document, cls._ROOT_KEYS, label="qualification event")
        try:
            kind = QualificationEventKind(document["event_kind"])
        except (TypeError, ValueError) as error:
            raise QualificationContractError(
                "qualification event kind is not supported"
            ) from error
        return cls(
            schema_version=document["schema_version"],  # type: ignore[arg-type]
            sequence_number=require_plain_int(
                document["sequence_number"],
                label="event sequence_number",
                minimum=0,
            ),
            lane_id=_require_lane_id(document["lane_id"], label="event lane_id"),
            event_kind=kind,
            payload=parse_qualification_event_payload(document["payload"]),
            payload_sha256=require_sha256(
                document["payload_sha256"], label="event payload_sha256"
            ),
            previous_entry_sha256=require_sha256(
                document["previous_entry_sha256"],
                label="event previous_entry_sha256",
            ),
            entry_sha256=require_sha256(
                document["entry_sha256"], label="event entry_sha256"
            ),
        )


def _canonical_lane_ids(values: tuple[str, ...], *, label: str) -> tuple[str, ...]:
    if type(values) is not tuple:
        raise TypeError(f"{label} must be an immutable tuple")
    if not values:
        raise QualificationContractError(f"{label} must not be empty")
    for index, value in enumerate(values):
        _require_lane_id(value, label=f"{label}[{index}]")
    if values != tuple(sorted(set(values))):
        raise QualificationContractError(
            f"{label} must be unique and in canonical order"
        )
    return values


@dataclass(frozen=True, slots=True)
class QualificationEventLedger:
    """Immutable global digest chain with fixed per-lane event order."""

    expected_lane_ids: tuple[str, ...]
    entries: tuple[QualificationEvent, ...] = ()
    schema_version: str = EVENT_LEDGER_SCHEMA_VERSION
    claim_ceiling: str = "level_0"
    scientific_claim_eligible: bool = False
    subject_access_authorized: bool = False
    semantic_authority: bool = False
    integer_or_topology_authority: bool = False

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "claim_ceiling",
            "expected_lane_ids",
            "entries",
            "scientific_claim_eligible",
            "subject_access_authorized",
            "semantic_authority",
            "integer_or_topology_authority",
        }
    )

    def __post_init__(self) -> None:
        _require_constant(
            self.schema_version,
            EVENT_LEDGER_SCHEMA_VERSION,
            label="event ledger schema_version",
        )
        _require_constant(
            self.claim_ceiling, "level_0", label="event ledger claim_ceiling"
        )
        _canonical_lane_ids(
            self.expected_lane_ids, label="event ledger expected_lane_ids"
        )
        if type(self.entries) is not tuple:
            raise TypeError("event ledger entries must be an immutable tuple")
        for name in (
            "scientific_claim_eligible",
            "subject_access_authorized",
            "semantic_authority",
            "integer_or_topology_authority",
        ):
            _require_constant(getattr(self, name), False, label=f"event ledger {name}")
        if len(self.entries) > MAX_EVENT_LEDGER_ENTRIES:
            raise QualificationContractError("event ledger exceeds its entry limit")
        expected_lanes = set(self.expected_lane_ids)
        lane_positions = dict.fromkeys(self.expected_lane_ids, 0)
        previous = GENESIS_ENTRY_SHA256
        for sequence_number, entry in enumerate(self.entries):
            if not isinstance(entry, QualificationEvent):
                raise TypeError("event ledger entries must be QualificationEvent")
            if entry.sequence_number != sequence_number:
                raise QualificationContractError(
                    "event ledger sequence numbers must be contiguous from zero"
                )
            if entry.previous_entry_sha256 != previous:
                raise QualificationContractError(
                    "event ledger previous-entry digest chain is broken"
                )
            if entry.entry_sha256 != entry.expected_entry_sha256:
                raise QualificationContractError(
                    "event ledger entry digest does not match its contents"
                )
            if entry.lane_id not in expected_lanes:
                raise QualificationContractError(
                    "event ledger contains an undeclared lane"
                )
            position = lane_positions[entry.lane_id]
            if position >= len(_EVENT_ORDER):
                raise QualificationContractError(
                    "event ledger contains a duplicate completed-lane event"
                )
            if entry.event_kind is not _EVENT_ORDER[position]:
                raise QualificationContractError(
                    f"event ledger lane {entry.lane_id!r} violates the fixed "
                    "truth-blind chronology"
                )
            lane_positions[entry.lane_id] = position + 1
            previous = entry.entry_sha256

    @classmethod
    def create(cls, expected_lane_ids: tuple[str, ...]) -> QualificationEventLedger:
        """Create an empty immutable ledger for an exact lane manifest."""

        return cls(expected_lane_ids=expected_lane_ids)

    def _lane_position(self, lane_id: str) -> int:
        return sum(entry.lane_id == lane_id for entry in self.entries)

    def append(
        self,
        *,
        lane_id: str,
        event_kind: QualificationEventKind,
        payload: QualificationEventPayload,
    ) -> QualificationEventLedger:
        """Return a new ledger after validating one typed local payload."""

        _require_lane_id(lane_id, label="event lane_id")
        if lane_id not in self.expected_lane_ids:
            raise QualificationContractError(
                "cannot append an event for an undeclared lane"
            )
        if not isinstance(event_kind, QualificationEventKind):
            raise TypeError("event_kind must be a QualificationEventKind")
        if not isinstance(payload, _PAYLOAD_TYPES[event_kind]):
            raise QualificationContractError(
                "event payload type differs from event_kind"
            )
        if payload.lane_id != lane_id:
            raise QualificationContractError(
                "event payload lane differs from append lane"
            )
        payload_bytes = canonical_json_bytes(payload.to_dict())
        if len(payload_bytes) > MAX_EVENT_PAYLOAD_BYTES:
            raise QualificationContractError("event payload exceeds its byte limit")
        position = self._lane_position(lane_id)
        if position >= len(_EVENT_ORDER):
            raise QualificationContractError(
                "cannot append an event to a completed lane"
            )
        if event_kind is not _EVENT_ORDER[position]:
            raise QualificationContractError(
                f"event {event_kind.value!r} cannot precede "
                f"{_EVENT_ORDER[position].value!r} in lane {lane_id!r}"
            )
        previous = (
            self.entries[-1].entry_sha256 if self.entries else GENESIS_ENTRY_SHA256
        )
        entry = QualificationEvent.create(
            sequence_number=len(self.entries),
            lane_id=lane_id,
            event_kind=event_kind,
            payload=payload,
            previous_entry_sha256=previous,
        )
        return QualificationEventLedger(
            expected_lane_ids=self.expected_lane_ids,
            entries=(*self.entries, entry),
        )

    @property
    def completed_lane_ids(self) -> tuple[str, ...]:
        return tuple(
            lane_id
            for lane_id in self.expected_lane_ids
            if self._lane_position(lane_id) == len(_EVENT_ORDER)
        )

    @property
    def is_complete(self) -> bool:
        return self.completed_lane_ids == self.expected_lane_ids

    @property
    def chain_head_sha256(self) -> str:
        return self.entries[-1].entry_sha256 if self.entries else GENESIS_ENTRY_SHA256

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "claim_ceiling": self.claim_ceiling,
            "expected_lane_ids": list(self.expected_lane_ids),
            "entries": [entry.to_dict() for entry in self.entries],
            "scientific_claim_eligible": self.scientific_claim_eligible,
            "subject_access_authorized": self.subject_access_authorized,
            "semantic_authority": self.semantic_authority,
            "integer_or_topology_authority": self.integer_or_topology_authority,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    def receipt(self) -> QualificationEventLedgerReceipt:
        """Finalize a self-validating receipt only after every lane completes."""

        if not self.is_complete:
            raise QualificationContractError(
                "event ledger receipt requires every declared lane to complete"
            )
        return QualificationEventLedgerReceipt(
            expected_lane_ids=self.expected_lane_ids,
            entries=self.entries,
            ledger_canonical_sha256=self.canonical_sha256,
            chain_head_sha256=self.chain_head_sha256,
            event_count=len(self.entries),
        )

    @classmethod
    def from_dict(cls, value: object) -> QualificationEventLedger:
        document = _require_mapping(value, label="qualification event ledger")
        _require_exact_keys(
            document, cls._ROOT_KEYS, label="qualification event ledger"
        )
        for name, expected in (
            ("schema_version", EVENT_LEDGER_SCHEMA_VERSION),
            ("claim_ceiling", "level_0"),
            ("scientific_claim_eligible", False),
            ("subject_access_authorized", False),
            ("semantic_authority", False),
            ("integer_or_topology_authority", False),
        ):
            _require_constant(document[name], expected, label=f"event ledger {name}")
        lane_values = _require_list(
            document["expected_lane_ids"], label="event ledger expected_lane_ids"
        )
        entries = _require_list(document["entries"], label="event ledger entries")
        return cls(
            expected_lane_ids=tuple(
                _require_lane_id(item, label=f"expected_lane_ids[{index}]")
                for index, item in enumerate(lane_values)
            ),
            entries=tuple(QualificationEvent.from_dict(item) for item in entries),
        )


@dataclass(frozen=True, slots=True)
class QualificationEventLedgerReceipt:
    """Self-contained post-hoc logical dependency manifest for every lane."""

    expected_lane_ids: tuple[str, ...]
    entries: tuple[QualificationEvent, ...]
    ledger_canonical_sha256: str
    chain_head_sha256: str
    event_count: int
    schema_version: str = EVENT_LEDGER_RECEIPT_SCHEMA_VERSION
    claim_ceiling: str = "level_0"
    posthoc_logical_dependency_manifest_validated: bool = True
    scientific_claim_eligible: bool = False
    subject_access_authorized: bool = False
    semantic_authority: bool = False
    integer_or_topology_authority: bool = False

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "claim_ceiling",
            "expected_lane_ids",
            "entries",
            "ledger_canonical_sha256",
            "chain_head_sha256",
            "event_count",
            "posthoc_logical_dependency_manifest_validated",
            "scientific_claim_eligible",
            "subject_access_authorized",
            "semantic_authority",
            "integer_or_topology_authority",
        }
    )

    def __post_init__(self) -> None:
        _require_constant(
            self.schema_version,
            EVENT_LEDGER_RECEIPT_SCHEMA_VERSION,
            label="event ledger receipt schema_version",
        )
        _require_constant(
            self.claim_ceiling,
            "level_0",
            label="event ledger receipt claim_ceiling",
        )
        _require_constant(
            self.posthoc_logical_dependency_manifest_validated,
            True,
            label=(
                "event ledger receipt posthoc_logical_dependency_manifest_validated"
            ),
        )
        for name in (
            "scientific_claim_eligible",
            "subject_access_authorized",
            "semantic_authority",
            "integer_or_topology_authority",
        ):
            _require_constant(
                getattr(self, name), False, label=f"event ledger receipt {name}"
            )
        require_sha256(
            self.ledger_canonical_sha256,
            label="event ledger receipt ledger_canonical_sha256",
        )
        require_sha256(
            self.chain_head_sha256,
            label="event ledger receipt chain_head_sha256",
        )
        require_plain_int(
            self.event_count, label="event ledger receipt event_count", minimum=1
        )
        if type(self.expected_lane_ids) is not tuple:
            raise TypeError(
                "event ledger receipt expected_lane_ids must be an immutable tuple"
            )
        if type(self.entries) is not tuple:
            raise TypeError("event ledger receipt entries must be an immutable tuple")
        ledger = QualificationEventLedger(
            expected_lane_ids=self.expected_lane_ids,
            entries=self.entries,
        )
        if not ledger.is_complete:
            raise QualificationContractError(
                "event ledger receipt contains an incomplete lane"
            )
        if self.event_count != len(self.entries):
            raise QualificationContractError(
                "event ledger receipt event_count differs from its entries"
            )
        if self.event_count != len(self.expected_lane_ids) * len(_EVENT_ORDER):
            raise QualificationContractError(
                "event ledger receipt does not contain exactly one event "
                "chronology per lane"
            )
        if self.ledger_canonical_sha256 != ledger.canonical_sha256:
            raise QualificationContractError(
                "event ledger receipt canonical digest differs from its ledger"
            )
        if self.chain_head_sha256 != ledger.chain_head_sha256:
            raise QualificationContractError(
                "event ledger receipt chain head differs from its ledger"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "claim_ceiling": self.claim_ceiling,
            "expected_lane_ids": list(self.expected_lane_ids),
            "entries": [entry.to_dict() for entry in self.entries],
            "ledger_canonical_sha256": self.ledger_canonical_sha256,
            "chain_head_sha256": self.chain_head_sha256,
            "event_count": self.event_count,
            "posthoc_logical_dependency_manifest_validated": (
                self.posthoc_logical_dependency_manifest_validated
            ),
            "scientific_claim_eligible": self.scientific_claim_eligible,
            "subject_access_authorized": self.subject_access_authorized,
            "semantic_authority": self.semantic_authority,
            "integer_or_topology_authority": self.integer_or_topology_authority,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> QualificationEventLedgerReceipt:
        document = _require_mapping(value, label="qualification event ledger receipt")
        _require_exact_keys(
            document,
            cls._ROOT_KEYS,
            label="qualification event ledger receipt",
        )
        for name, expected in (
            ("schema_version", EVENT_LEDGER_RECEIPT_SCHEMA_VERSION),
            ("claim_ceiling", "level_0"),
            ("posthoc_logical_dependency_manifest_validated", True),
            ("scientific_claim_eligible", False),
            ("subject_access_authorized", False),
            ("semantic_authority", False),
            ("integer_or_topology_authority", False),
        ):
            _require_constant(
                document[name],
                expected,
                label=f"event ledger receipt {name}",
            )
        lanes = _require_list(
            document["expected_lane_ids"],
            label="event ledger receipt expected_lane_ids",
        )
        entries = _require_list(
            document["entries"], label="event ledger receipt entries"
        )
        return cls(
            expected_lane_ids=tuple(
                _require_lane_id(item, label=f"expected_lane_ids[{index}]")
                for index, item in enumerate(lanes)
            ),
            entries=tuple(QualificationEvent.from_dict(item) for item in entries),
            ledger_canonical_sha256=require_sha256(
                document["ledger_canonical_sha256"],
                label="event ledger receipt ledger_canonical_sha256",
            ),
            chain_head_sha256=require_sha256(
                document["chain_head_sha256"],
                label="event ledger receipt chain_head_sha256",
            ),
            event_count=require_plain_int(
                document["event_count"],
                label="event ledger receipt event_count",
                minimum=1,
            ),
        )


@dataclass(frozen=True, slots=True)
class QualificationEventLedgerSummary:
    """Compact Result join for a separately validated complete ledger receipt.

    A result loader must call :meth:`verify_receipt` with the full companion
    receipt. Merely parsing this summary does not establish event order.
    """

    event_ledger_receipt_sha256: str
    event_ledger_canonical_sha256: str
    event_ledger_chain_head_sha256: str
    event_ledger_lane_count: int
    event_ledger_event_count: int
    posthoc_logical_dependency_manifest_validated: bool = True
    claim_ceiling: str = "level_0"
    scientific_claim_eligible: bool = False
    subject_access_authorized: bool = False
    semantic_authority: bool = False
    integer_or_topology_authority: bool = False

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "event_ledger_receipt_sha256",
            "event_ledger_canonical_sha256",
            "event_ledger_chain_head_sha256",
            "event_ledger_lane_count",
            "event_ledger_event_count",
            "posthoc_logical_dependency_manifest_validated",
            "claim_ceiling",
            "scientific_claim_eligible",
            "subject_access_authorized",
            "semantic_authority",
            "integer_or_topology_authority",
        }
    )

    def __post_init__(self) -> None:
        for name in (
            "event_ledger_receipt_sha256",
            "event_ledger_canonical_sha256",
            "event_ledger_chain_head_sha256",
        ):
            require_sha256(getattr(self, name), label=f"event ledger summary {name}")
        require_plain_int(
            self.event_ledger_lane_count,
            label="event ledger summary lane_count",
            minimum=1,
        )
        require_plain_int(
            self.event_ledger_event_count,
            label="event ledger summary event_count",
            minimum=1,
        )
        if self.event_ledger_event_count != (
            self.event_ledger_lane_count * len(_EVENT_ORDER)
        ):
            raise QualificationContractError(
                "event ledger summary count does not describe one complete "
                "chronology per lane"
            )
        _require_constant(
            self.posthoc_logical_dependency_manifest_validated,
            True,
            label=(
                "event ledger summary posthoc_logical_dependency_manifest_validated"
            ),
        )
        _require_constant(
            self.claim_ceiling,
            "level_0",
            label="event ledger summary claim_ceiling",
        )
        for name in (
            "scientific_claim_eligible",
            "subject_access_authorized",
            "semantic_authority",
            "integer_or_topology_authority",
        ):
            _require_constant(
                getattr(self, name), False, label=f"event ledger summary {name}"
            )

    @classmethod
    def from_receipt(
        cls,
        receipt: QualificationEventLedgerReceipt,
    ) -> QualificationEventLedgerSummary:
        """Derive the compact join only after full receipt validation."""

        if not isinstance(receipt, QualificationEventLedgerReceipt):
            raise TypeError("receipt must be a QualificationEventLedgerReceipt")
        return cls(
            event_ledger_receipt_sha256=receipt.canonical_sha256,
            event_ledger_canonical_sha256=receipt.ledger_canonical_sha256,
            event_ledger_chain_head_sha256=receipt.chain_head_sha256,
            event_ledger_lane_count=len(receipt.expected_lane_ids),
            event_ledger_event_count=receipt.event_count,
        )

    def verify_receipt(self, receipt: QualificationEventLedgerReceipt) -> None:
        """Require this summary to equal one fully revalidated receipt."""

        if self != type(self).from_receipt(receipt):
            raise QualificationContractError(
                "event ledger summary differs from its full receipt"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "event_ledger_receipt_sha256": self.event_ledger_receipt_sha256,
            "event_ledger_canonical_sha256": self.event_ledger_canonical_sha256,
            "event_ledger_chain_head_sha256": (self.event_ledger_chain_head_sha256),
            "event_ledger_lane_count": self.event_ledger_lane_count,
            "event_ledger_event_count": self.event_ledger_event_count,
            "posthoc_logical_dependency_manifest_validated": (
                self.posthoc_logical_dependency_manifest_validated
            ),
            "claim_ceiling": self.claim_ceiling,
            "scientific_claim_eligible": self.scientific_claim_eligible,
            "subject_access_authorized": self.subject_access_authorized,
            "semantic_authority": self.semantic_authority,
            "integer_or_topology_authority": self.integer_or_topology_authority,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> QualificationEventLedgerSummary:
        """Parse a compact join that still requires its full receipt."""

        document = _require_mapping(value, label="qualification event ledger summary")
        _require_exact_keys(
            document,
            cls._ROOT_KEYS,
            label="qualification event ledger summary",
        )
        for name, expected in (
            ("posthoc_logical_dependency_manifest_validated", True),
            ("claim_ceiling", "level_0"),
            ("scientific_claim_eligible", False),
            ("subject_access_authorized", False),
            ("semantic_authority", False),
            ("integer_or_topology_authority", False),
        ):
            _require_constant(
                document[name],
                expected,
                label=f"event ledger summary {name}",
            )
        return cls(
            event_ledger_receipt_sha256=require_sha256(
                document["event_ledger_receipt_sha256"],
                label="event ledger summary receipt_sha256",
            ),
            event_ledger_canonical_sha256=require_sha256(
                document["event_ledger_canonical_sha256"],
                label="event ledger summary ledger_canonical_sha256",
            ),
            event_ledger_chain_head_sha256=require_sha256(
                document["event_ledger_chain_head_sha256"],
                label="event ledger summary chain_head_sha256",
            ),
            event_ledger_lane_count=require_plain_int(
                document["event_ledger_lane_count"],
                label="event ledger summary lane_count",
                minimum=1,
            ),
            event_ledger_event_count=require_plain_int(
                document["event_ledger_event_count"],
                label="event ledger summary event_count",
                minimum=1,
            ),
        )
