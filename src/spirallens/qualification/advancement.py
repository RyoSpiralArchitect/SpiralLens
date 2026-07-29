"""Scope-limited D6 admission and fail-closed D7/D8 contracts.

The official D0--D5 result qualifies one Cartesian surrogate profile.  It
does not select the representation instrument.  This module seals that exact
scope and the requirements for a future construction-diverse confirmation.
It deliberately contains no confirmation runner and cannot promote D7, D8,
global synthetic qualification, a subject, an integer, or topology.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from spirallens.core.canonical import (
    CanonicalJsonError,
    canonical_json_bytes,
    canonical_json_sha256,
    parse_canonical_json,
)

from .common import (
    QualificationContractError,
    QualificationState,
    require_bool,
    require_sha256,
    require_slug,
)
from .contracts import QualificationResult
from .freeze import (
    PersistedSelectionTerminalIdentity,
    SelectionConsumptionArtifact,
    TerminalAttemptArtifactKind,
)
from .protocol import QualificationProtocol

D6_SELECTION_TERMINAL_BINDING_SCHEMA_VERSION = (
    "spirallens.d6-selection-terminal-binding.v0.1"
)
INDEPENDENT_CONFIRMATION_ADMISSION_SCHEMA_VERSION = (
    "spirallens.independent-confirmation-admission.v0.1"
)
SURROGATE_ADVANCEMENT_DECISION_SCHEMA_VERSION = (
    "spirallens.surrogate-advancement-decision.v0.1"
)

MAX_ADVANCEMENT_ARTIFACT_BYTES = 1024 * 1024
ADVANCEMENT_SOURCE_BINDING_SCHEMA_VERSION = (
    "spirallens.advancement-source-binding.v0.1"
)

SURROGATE_PROFILE_ID = "f2-cartesian-surrogate-d2-d5-v0-1"
SURROGATE_ADVANCEMENT_SCOPE = "surrogate-profile-confirmation-only"
CARTESIAN_SELECTION_CONSTRUCTION_FAMILY_ID = (
    "cartesian-fourier-quadrature-lattice"
)

D7_NOT_RUN_REASON_CODES = (
    "full-d2-d5-confirmation-path-not-implemented",
    "independent-construction-family-not-admitted",
)
D8_NOT_RUN_REASON_CODES = (
    "d7-not-pass",
    "replay-not-run",
)

_GATES = ("d0", "d1", "d2", "d3", "d4", "d5")
_EXPECTED_GATE_SCOPES = (
    ("d0", "engine-and-protocol-contracts"),
    ("d1", "cartesian-surrogate-and-representation-development"),
    ("d2", "cartesian-surrogate-only"),
    ("d3", "cartesian-surrogate-and-representation-development"),
    ("d4", "cartesian-surrogate-only"),
    ("d5", "cartesian-surrogate-only"),
)
_REQUIRED_CASE_SEMANTICS = (
    "localized-core|nonzero",
    "localized-core|null",
    "no-core|null",
    "prerequisite-failure|prerequisite-failure",
)
_ADVANCEMENT_SEALER_PATH = "scripts/seal_d6_surrogate_advancement.py"
_ADVANCEMENT_PACKAGE_ROOT = "src/spirallens"


def _mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(
        not isinstance(key, str) for key in value
    ):
        raise QualificationContractError(f"{label} must be a string-keyed mapping")
    return value


def _sequence(value: object, *, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise QualificationContractError(f"{label} must be a sequence")
    return value


def _exact_keys(
    value: Mapping[str, object],
    expected: frozenset[str],
    *,
    label: str,
) -> None:
    if set(value) != expected:
        raise QualificationContractError(
            f"{label} fields differ from the exact schema"
        )


def _constant(value: object, expected: object, *, label: str) -> object:
    if type(value) is not type(expected) or value != expected:
        raise QualificationContractError(f"{label} must be {expected!r}")
    return value


def _text(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise QualificationContractError(f"{label} must be a nonempty string")
    return value


def _git_commit(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise QualificationContractError(
            f"{label} must be a lowercase 40-character Git commit"
        )
    return value


def _resolve_repository(path: str | Path | None) -> Path:
    repository = (
        Path(__file__).resolve().parents[3]
        if path is None
        else Path(os.path.abspath(Path(path)))
    )
    if repository.is_symlink() or not repository.is_dir():
        raise QualificationContractError(
            "advancement repository_root must be a real directory"
        )
    return repository


def _advancement_source_paths_at_commit(
    repository: Path,
    *,
    commit: str,
) -> tuple[str, ...]:
    """Resolve the complete tracked Python surface used by the D6 sealer."""

    completed = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "ls-tree",
            "-r",
            "--name-only",
            "-z",
            commit,
            "--",
            _ADVANCEMENT_PACKAGE_ROOT,
            _ADVANCEMENT_SEALER_PATH,
        ],
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise QualificationContractError(
            "cannot enumerate the advancement source surface"
        )
    try:
        entries = tuple(
            entry.decode("utf-8")
            for entry in completed.stdout.split(b"\0")
            if entry
        )
    except UnicodeDecodeError as error:
        raise QualificationContractError(
            "advancement source paths must be UTF-8"
        ) from error
    paths = tuple(
        sorted(
            path
            for path in entries
            if path == _ADVANCEMENT_SEALER_PATH
            or (
                path.startswith(f"{_ADVANCEMENT_PACKAGE_ROOT}/")
                and path.endswith(".py")
            )
        )
    )
    if (
        not paths
        or len(paths) != len(set(paths))
        or _ADVANCEMENT_SEALER_PATH not in paths
    ):
        raise QualificationContractError(
            "advancement source surface is incomplete or non-canonical"
        )
    return paths


def advancement_source_binding_sha256(
    *,
    repository_root: str | Path | None,
    commit: str,
    require_clean_current_sources: bool = False,
) -> str:
    """Hash the declared D6 source surface at one Git commit.

    The receipt is deliberately source-only: it does not attest the imported
    runtime, host process, or a complete transitive dependency closure.
    """

    repository = _resolve_repository(repository_root)
    source_commit = _git_commit(commit, label="advancement source commit")
    resolved = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "rev-parse",
            "--verify",
            f"{source_commit}^{{commit}}",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if resolved.returncode != 0 or resolved.stdout.strip() != source_commit:
        raise QualificationContractError(
            "advancement source commit does not resolve exactly"
        )
    source_paths = _advancement_source_paths_at_commit(
        repository,
        commit=source_commit,
    )
    if require_clean_current_sources:
        filesystem_entries = tuple(
            (repository / _ADVANCEMENT_PACKAGE_ROOT).rglob("*.py")
        )
        if any(
            path.is_symlink() or not path.is_file()
            for path in filesystem_entries
        ):
            raise QualificationContractError(
                "current advancement Python surface contains a non-regular path"
            )
        filesystem_paths = tuple(
            sorted(
                path.relative_to(repository).as_posix()
                for path in filesystem_entries
            )
        )
        expected_package_paths = tuple(
            path
            for path in source_paths
            if path.startswith(f"{_ADVANCEMENT_PACKAGE_ROOT}/")
        )
        if filesystem_paths != expected_package_paths:
            raise QualificationContractError(
                "current advancement Python surface differs from tracked HEAD"
            )
    files: list[dict[str, str]] = []
    for repository_path in source_paths:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "show",
                f"{source_commit}:{repository_path}",
            ],
            check=False,
            capture_output=True,
        )
        if completed.returncode != 0:
            raise QualificationContractError(
                f"advancement source {repository_path!r} is absent at commit"
            )
        digest = hashlib.sha256(completed.stdout).hexdigest()
        if require_clean_current_sources:
            working_path = repository / repository_path
            if (
                working_path.is_symlink()
                or not working_path.is_file()
                or working_path.read_bytes() != completed.stdout
            ):
                raise QualificationContractError(
                    f"advancement source {repository_path!r} is not the clean "
                    "current commit blob"
                )
        files.append(
            {
                "repository_path": repository_path,
                "sha256": digest,
            }
        )
    return canonical_json_sha256(
        {
            "schema_version": ADVANCEMENT_SOURCE_BINDING_SCHEMA_VERSION,
            "commit": source_commit,
            "files": files,
            "source_only": True,
            "runtime_attested": False,
            "hostile_process_attested": False,
        }
    )


def build_current_advancement_source_binding(
    *,
    repository_root: str | Path | None = None,
) -> tuple[str, str]:
    """Return current HEAD and its clean exact D6 source-binding digest."""

    repository = _resolve_repository(repository_root)
    completed = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise QualificationContractError(
            "cannot resolve current advancement source commit"
        )
    commit = _git_commit(
        completed.stdout.strip(),
        label="current advancement source commit",
    )
    digest = advancement_source_binding_sha256(
        repository_root=repository,
        commit=commit,
        require_clean_current_sources=True,
    )
    return commit, digest


def validate_advancement_decision_source(
    decision: SurrogateAdvancementDecision,
    *,
    repository_root: str | Path | None = None,
) -> None:
    """Reconstruct and verify the exact historical D6 implementation binding."""

    if not isinstance(decision, SurrogateAdvancementDecision):
        raise TypeError("decision must be a SurrogateAdvancementDecision")
    repository = _resolve_repository(repository_root)
    expected = advancement_source_binding_sha256(
        repository_root=repository,
        commit=decision.decision_source_commit,
        require_clean_current_sources=False,
    )
    if expected != decision.decision_source_binding_sha256:
        raise QualificationContractError(
            "D6 decision source binding differs from its historical Git blobs"
        )
    head_before = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "--verify", "HEAD^{commit}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if head_before.returncode != 0:
        raise QualificationContractError(
            "cannot resolve current advancement validation HEAD"
        )
    current_head = _git_commit(
        head_before.stdout.strip(),
        label="current advancement validation HEAD",
    )
    ancestry = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "merge-base",
            "--is-ancestor",
            decision.decision_source_commit,
            current_head,
        ],
        check=False,
        capture_output=True,
    )
    if ancestry.returncode != 0:
        raise QualificationContractError(
            "D6 decision source commit is not an ancestor of current HEAD"
        )
    head_after = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "--verify", "HEAD^{commit}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if (
        head_after.returncode != 0
        or head_after.stdout.strip() != current_head
    ):
        raise QualificationContractError(
            "advancement validation HEAD changed during source verification"
        )


def _canonical_pairs(
    value: tuple[tuple[str, str], ...],
    *,
    label: str,
) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, tuple):
        raise TypeError(f"{label} must be a tuple")
    pairs: list[tuple[str, str]] = []
    for index, pair in enumerate(value):
        if not isinstance(pair, tuple) or len(pair) != 2:
            raise TypeError(f"{label}[{index}] must be a two-item tuple")
        left = _text(pair[0], label=f"{label}[{index}][0]")
        right = _text(pair[1], label=f"{label}[{index}][1]")
        pairs.append((left, right))
    result = tuple(pairs)
    if result != tuple(sorted(set(result))):
        raise QualificationContractError(
            f"{label} must be unique and in canonical order"
        )
    return result


def _parse_pairs(value: object, *, label: str) -> tuple[tuple[str, str], ...]:
    pairs: list[tuple[str, str]] = []
    for index, item in enumerate(_sequence(value, label=label)):
        pair = _sequence(item, label=f"{label}[{index}]")
        if len(pair) != 2:
            raise QualificationContractError(
                f"{label}[{index}] must contain exactly two items"
            )
        pairs.append(
            (
                _text(pair[0], label=f"{label}[{index}][0]"),
                _text(pair[1], label=f"{label}[{index}][1]"),
            )
        )
    return _canonical_pairs(tuple(pairs), label=label)


def _canonical_strings(
    value: tuple[str, ...],
    *,
    label: str,
) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise TypeError(f"{label} must be a tuple")
    result = tuple(_text(item, label=f"{label} item") for item in value)
    if result != tuple(sorted(set(result))):
        raise QualificationContractError(
            f"{label} must be unique and in canonical order"
        )
    return result


def _false_authority(document: Mapping[str, object], *, label: str) -> None:
    for name in (
        "d6_d8_advanced",
        "synthetic_qualified",
        "p0_winner_selected",
        "representation_instrument_advanced",
        "representation_d2_d5_qualified",
        "localized_core_loop_join_established",
        "integer_output_authorized",
        "topology_claim_authorized",
        "subject_access_authorized",
        "subject_execution_authorized",
        "semantic_authority",
        "pythia_access_authorized",
    ):
        _constant(document[name], False, label=f"{label}.{name}")


_AUTHORITY_KEYS = frozenset(
    {
        "d6_d8_advanced",
        "synthetic_qualified",
        "p0_winner_selected",
        "representation_instrument_advanced",
        "representation_d2_d5_qualified",
        "localized_core_loop_join_established",
        "integer_output_authorized",
        "topology_claim_authorized",
        "subject_access_authorized",
        "subject_execution_authorized",
        "semantic_authority",
        "pythia_access_authorized",
    }
)


def _authority_dict() -> dict[str, object]:
    return {name: False for name in sorted(_AUTHORITY_KEYS)}


@dataclass(frozen=True, slots=True)
class SelectionTerminalBinding:
    """Exact historical terminal identity admitted as D6 input."""

    protocol_id: str
    protocol_source_sha256: str
    protocol_canonical_sha256: str
    selection_freeze_sha256: str
    selection_attempt_claim_sha256: str
    launch_authorization_sha256: str
    result_id: str
    result_sha256: str
    result_evidence_root_sha256: str
    terminal_manifest_sha256: str
    consumption_sha256: str
    selection_generator_family_id: str
    selection_construction_family_id: str
    surrogate_estimator_id: str
    surrogate_trivialization_id: str
    selection_implementation_registry_sha256: str
    graph_axes_sha256: str
    required_cells_manifest_sha256: str
    required_stress_strata_sha256: str
    locked_thresholds_sha256: str
    locked_aggregation_sha256: str
    gate_states: tuple[tuple[str, str], ...]
    gate_claim_scopes: tuple[tuple[str, str], ...]

    schema_version: ClassVar[str] = D6_SELECTION_TERMINAL_BINDING_SCHEMA_VERSION
    claim_ceiling: ClassVar[str] = "level_0"
    selection_profile_id: ClassVar[str] = SURROGATE_PROFILE_ID
    historical_terminal_companion_validation_required: ClassVar[bool] = True
    historical_terminal_companion_validation_embedded: ClassVar[bool] = False
    current_engine_reexecution_verified: ClassVar[bool] = False
    external_prior_observation_excluded: ClassVar[bool] = False

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "claim_ceiling",
            "selection_profile_id",
            "protocol_id",
            "protocol_source_sha256",
            "protocol_canonical_sha256",
            "selection_freeze_sha256",
            "selection_attempt_claim_sha256",
            "launch_authorization_sha256",
            "result_id",
            "result_sha256",
            "result_evidence_root_sha256",
            "terminal_manifest_sha256",
            "consumption_sha256",
            "selection_generator_family_id",
            "selection_construction_family_id",
            "surrogate_estimator_id",
            "surrogate_trivialization_id",
            "selection_implementation_registry_sha256",
            "graph_axes_sha256",
            "required_cells_manifest_sha256",
            "required_stress_strata_sha256",
            "locked_thresholds_sha256",
            "locked_aggregation_sha256",
            "gate_states",
            "gate_claim_scopes",
            "historical_terminal_companion_validation_required",
            "historical_terminal_companion_validation_embedded",
            "current_engine_reexecution_verified",
            "external_prior_observation_excluded",
            "authority",
        }
    )

    def __post_init__(self) -> None:
        for name in (
            "protocol_id",
            "result_id",
            "selection_generator_family_id",
            "selection_construction_family_id",
            "surrogate_estimator_id",
            "surrogate_trivialization_id",
        ):
            require_slug(getattr(self, name), label=f"selection terminal {name}")
        for name in (
            "protocol_source_sha256",
            "protocol_canonical_sha256",
            "selection_freeze_sha256",
            "selection_attempt_claim_sha256",
            "launch_authorization_sha256",
            "result_sha256",
            "result_evidence_root_sha256",
            "terminal_manifest_sha256",
            "consumption_sha256",
            "selection_implementation_registry_sha256",
            "graph_axes_sha256",
            "required_cells_manifest_sha256",
            "required_stress_strata_sha256",
            "locked_thresholds_sha256",
            "locked_aggregation_sha256",
        ):
            require_sha256(
                getattr(self, name),
                label=f"selection terminal {name}",
            )
        if (
            self.selection_construction_family_id
            != CARTESIAN_SELECTION_CONSTRUCTION_FAMILY_ID
        ):
            raise QualificationContractError(
                "selection construction family must equal the closed Cartesian "
                "quadrature-lattice construction"
            )
        states = _canonical_pairs(self.gate_states, label="gate_states")
        if states != tuple((gate, QualificationState.PASS.value) for gate in _GATES):
            raise QualificationContractError(
                "selection terminal must contain exact D0-D5 pass states"
            )
        scopes = _canonical_pairs(
            self.gate_claim_scopes,
            label="gate_claim_scopes",
        )
        if scopes != _EXPECTED_GATE_SCOPES:
            raise QualificationContractError(
                "selection terminal gate scopes differ from the closed result"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "claim_ceiling": self.claim_ceiling,
            "selection_profile_id": self.selection_profile_id,
            "protocol_id": self.protocol_id,
            "protocol_source_sha256": self.protocol_source_sha256,
            "protocol_canonical_sha256": self.protocol_canonical_sha256,
            "selection_freeze_sha256": self.selection_freeze_sha256,
            "selection_attempt_claim_sha256": (
                self.selection_attempt_claim_sha256
            ),
            "launch_authorization_sha256": self.launch_authorization_sha256,
            "result_id": self.result_id,
            "result_sha256": self.result_sha256,
            "result_evidence_root_sha256": self.result_evidence_root_sha256,
            "terminal_manifest_sha256": self.terminal_manifest_sha256,
            "consumption_sha256": self.consumption_sha256,
            "selection_generator_family_id": (
                self.selection_generator_family_id
            ),
            "selection_construction_family_id": (
                self.selection_construction_family_id
            ),
            "surrogate_estimator_id": self.surrogate_estimator_id,
            "surrogate_trivialization_id": self.surrogate_trivialization_id,
            "selection_implementation_registry_sha256": (
                self.selection_implementation_registry_sha256
            ),
            "graph_axes_sha256": self.graph_axes_sha256,
            "required_cells_manifest_sha256": (
                self.required_cells_manifest_sha256
            ),
            "required_stress_strata_sha256": (
                self.required_stress_strata_sha256
            ),
            "locked_thresholds_sha256": self.locked_thresholds_sha256,
            "locked_aggregation_sha256": self.locked_aggregation_sha256,
            "gate_states": [list(item) for item in self.gate_states],
            "gate_claim_scopes": [
                list(item) for item in self.gate_claim_scopes
            ],
            "historical_terminal_companion_validation_required": (
                self.historical_terminal_companion_validation_required
            ),
            "historical_terminal_companion_validation_embedded": (
                self.historical_terminal_companion_validation_embedded
            ),
            "current_engine_reexecution_verified": (
                self.current_engine_reexecution_verified
            ),
            "external_prior_observation_excluded": (
                self.external_prior_observation_excluded
            ),
            "authority": _authority_dict(),
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> SelectionTerminalBinding:
        item = _mapping(value, label="selection terminal binding")
        _exact_keys(item, cls._ROOT_KEYS, label="selection terminal binding")
        _constant(
            item["schema_version"],
            cls.schema_version,
            label="selection terminal schema_version",
        )
        _constant(item["claim_ceiling"], "level_0", label="claim_ceiling")
        _constant(
            item["selection_profile_id"],
            SURROGATE_PROFILE_ID,
            label="selection_profile_id",
        )
        _constant(
            item["historical_terminal_companion_validation_required"],
            True,
            label="historical_terminal_companion_validation_required",
        )
        _constant(
            item["historical_terminal_companion_validation_embedded"],
            False,
            label="historical_terminal_companion_validation_embedded",
        )
        _constant(
            item["current_engine_reexecution_verified"],
            False,
            label="current_engine_reexecution_verified",
        )
        _constant(
            item["external_prior_observation_excluded"],
            False,
            label="external_prior_observation_excluded",
        )
        authority = _mapping(item["authority"], label="selection authority")
        _exact_keys(authority, _AUTHORITY_KEYS, label="selection authority")
        _false_authority(authority, label="selection authority")
        return cls(
            protocol_id=require_slug(item["protocol_id"], label="protocol_id"),
            protocol_source_sha256=require_sha256(
                item["protocol_source_sha256"],
                label="protocol_source_sha256",
            ),
            protocol_canonical_sha256=require_sha256(
                item["protocol_canonical_sha256"],
                label="protocol_canonical_sha256",
            ),
            selection_freeze_sha256=require_sha256(
                item["selection_freeze_sha256"],
                label="selection_freeze_sha256",
            ),
            selection_attempt_claim_sha256=require_sha256(
                item["selection_attempt_claim_sha256"],
                label="selection_attempt_claim_sha256",
            ),
            launch_authorization_sha256=require_sha256(
                item["launch_authorization_sha256"],
                label="launch_authorization_sha256",
            ),
            result_id=require_slug(item["result_id"], label="result_id"),
            result_sha256=require_sha256(
                item["result_sha256"],
                label="result_sha256",
            ),
            result_evidence_root_sha256=require_sha256(
                item["result_evidence_root_sha256"],
                label="result_evidence_root_sha256",
            ),
            terminal_manifest_sha256=require_sha256(
                item["terminal_manifest_sha256"],
                label="terminal_manifest_sha256",
            ),
            consumption_sha256=require_sha256(
                item["consumption_sha256"],
                label="consumption_sha256",
            ),
            selection_generator_family_id=require_slug(
                item["selection_generator_family_id"],
                label="selection_generator_family_id",
            ),
            selection_construction_family_id=require_slug(
                item["selection_construction_family_id"],
                label="selection_construction_family_id",
            ),
            surrogate_estimator_id=require_slug(
                item["surrogate_estimator_id"],
                label="surrogate_estimator_id",
            ),
            surrogate_trivialization_id=require_slug(
                item["surrogate_trivialization_id"],
                label="surrogate_trivialization_id",
            ),
            selection_implementation_registry_sha256=require_sha256(
                item["selection_implementation_registry_sha256"],
                label="selection_implementation_registry_sha256",
            ),
            graph_axes_sha256=require_sha256(
                item["graph_axes_sha256"],
                label="graph_axes_sha256",
            ),
            required_cells_manifest_sha256=require_sha256(
                item["required_cells_manifest_sha256"],
                label="required_cells_manifest_sha256",
            ),
            required_stress_strata_sha256=require_sha256(
                item["required_stress_strata_sha256"],
                label="required_stress_strata_sha256",
            ),
            locked_thresholds_sha256=require_sha256(
                item["locked_thresholds_sha256"],
                label="locked_thresholds_sha256",
            ),
            locked_aggregation_sha256=require_sha256(
                item["locked_aggregation_sha256"],
                label="locked_aggregation_sha256",
            ),
            gate_states=_parse_pairs(item["gate_states"], label="gate_states"),
            gate_claim_scopes=_parse_pairs(
                item["gate_claim_scopes"],
                label="gate_claim_scopes",
            ),
        )


def build_selection_terminal_binding(
    *,
    result: QualificationResult,
    protocol: QualificationProtocol,
    terminal_identity: PersistedSelectionTerminalIdentity,
    consumption: SelectionConsumptionArtifact,
) -> SelectionTerminalBinding:
    """Bind an already strictly loaded result without reopening its attempt."""

    if not isinstance(result, QualificationResult):
        raise TypeError("result must be a QualificationResult")
    if not isinstance(protocol, QualificationProtocol):
        raise TypeError("protocol must be a QualificationProtocol")
    if not isinstance(
        terminal_identity,
        PersistedSelectionTerminalIdentity,
    ):
        raise TypeError(
            "terminal_identity must be a PersistedSelectionTerminalIdentity"
        )
    if not isinstance(consumption, SelectionConsumptionArtifact):
        raise TypeError("consumption must be a SelectionConsumptionArtifact")
    if consumption.terminal_artifact_kind is not TerminalAttemptArtifactKind.RESULT:
        raise QualificationContractError(
            "D6 requires a successful qualification-result terminal"
        )
    if (
        result.canonical_sha256 != terminal_identity.terminal_artifact_sha256
        or consumption.canonical_sha256 != terminal_identity.consumption_sha256
        or consumption.terminal_artifact_sha256 != result.canonical_sha256
        or result.protocol_id != protocol.protocol_id
        or result.protocol_source_sha256 != protocol.canonical_sha256
        or result.protocol_canonical_sha256 != protocol.canonical_sha256
        or result.selection_freeze_artifact_sha256
        != consumption.freeze_artifact_sha256
        or result.selection_attempt_claim_sha256
        != consumption.attempt_claim_sha256
        or result.selection_launch_authorization_sha256 is None
    ):
        raise QualificationContractError(
            "selection result, protocol, terminal, and consumption do not join"
        )
    if any(gate.state is not QualificationState.PASS for gate in result.gate_results):
        raise QualificationContractError("D6 requires exact D0-D5 pass states")
    for name in (
        "d6_d8_advanced",
        "synthetic_qualified",
        "p0_winner_selected",
        "representation_d2_d5_qualified",
        "localized_core_loop_join_established",
        "integer_claimed",
        "pythia_accessed",
        "subject_accessed",
        "semantic_labels_accessed",
    ):
        if getattr(result, name) is not False:
            raise QualificationContractError(
                f"D6 input result must keep {name}=false"
            )
    implementation = protocol.implementation_registry
    graph_axes_sha256 = canonical_json_sha256(protocol.graphs.to_dict())
    required_cells_sha256 = canonical_json_sha256(
        {
            "schema_version": "spirallens.required-confirmation-cells.v0.1",
            "expected_core_cells": [
                item.to_dict() for item in protocol.expected_core_cells
            ],
            "expected_loop_cells": [
                item.to_dict() for item in protocol.expected_cells
            ],
        }
    )
    stress_sha256 = canonical_json_sha256(
        {
            "schema_version": "spirallens.required-confirmation-stress.v0.1",
            "stress_axes": [
                item.to_dict() for item in protocol.selection.stress_axes
            ],
            "expected_strata": [
                item.to_dict() for item in protocol.expected_strata
            ],
        }
    )
    threshold_sha256 = canonical_json_sha256(protocol.thresholds.to_dict())
    aggregation_sha256 = canonical_json_sha256(
        {
            "schema_version": "spirallens.locked-confirmation-aggregation.v0.1",
            "coverage_policy": protocol.coverage_policy.to_dict(),
            "evaluation_design": protocol.evaluation_design.to_dict(),
        }
    )
    return SelectionTerminalBinding(
        protocol_id=result.protocol_id,
        protocol_source_sha256=result.protocol_source_sha256,
        protocol_canonical_sha256=result.protocol_canonical_sha256,
        selection_freeze_sha256=result.selection_freeze_artifact_sha256,
        selection_attempt_claim_sha256=(
            result.selection_attempt_claim_sha256
        ),
        launch_authorization_sha256=(
            result.selection_launch_authorization_sha256
        ),
        result_id=result.result_id,
        result_sha256=result.canonical_sha256,
        result_evidence_root_sha256=result.result_evidence_root_sha256,
        terminal_manifest_sha256=terminal_identity.manifest_sha256,
        consumption_sha256=consumption.canonical_sha256,
        selection_generator_family_id=implementation.generator_family_id,
        selection_construction_family_id=(
            CARTESIAN_SELECTION_CONSTRUCTION_FAMILY_ID
        ),
        surrogate_estimator_id=implementation.surrogate_estimator_id,
        surrogate_trivialization_id=(
            implementation.surrogate_trivialization_id
        ),
        selection_implementation_registry_sha256=canonical_json_sha256(
            implementation.to_dict()
        ),
        graph_axes_sha256=graph_axes_sha256,
        required_cells_manifest_sha256=required_cells_sha256,
        required_stress_strata_sha256=stress_sha256,
        locked_thresholds_sha256=threshold_sha256,
        locked_aggregation_sha256=aggregation_sha256,
        gate_states=tuple(
            (gate.gate_id.value, gate.state.value)
            for gate in result.gate_results
        ),
        gate_claim_scopes=tuple(
            (gate.gate_id.value, gate.claim_scope.value)
            for gate in result.gate_results
        ),
    )


@dataclass(frozen=True, slots=True)
class IndependentConfirmationAdmissionSpec:
    """D6-frozen admission requirements, not a D7 family or result."""

    admission_spec_id: str
    selection_terminal_binding_sha256: str
    selection_generator_family_id: str
    selection_construction_family_id: str
    required_surrogate_estimator_id: str
    required_surrogate_trivialization_id: str
    selection_implementation_registry_sha256: str
    required_case_semantics: tuple[str, ...]
    required_graph_axes_sha256: str
    required_stress_strata_sha256: str
    required_cells_manifest_sha256: str
    locked_thresholds_sha256: str
    locked_aggregation_sha256: str

    schema_version: ClassVar[str] = (
        INDEPENDENT_CONFIRMATION_ADMISSION_SCHEMA_VERSION
    )
    selection_profile_id: ClassVar[str] = SURROGATE_PROFILE_ID
    claim_ceiling: ClassVar[str] = "level_0"
    required_distinct_generator_family: ClassVar[bool] = True
    required_distinct_construction_family: ClassVar[bool] = True
    source_or_implementation_change_alone_sufficient: ClassVar[bool] = False
    seed_change_alone_sufficient: ClassVar[bool] = False
    required_core_and_loop_separation: ClassVar[bool] = True
    selection_evidence_disjointness_required: ClassVar[bool] = True
    policy_override_allowed: ClassVar[bool] = False
    post_selection_exclusion_allowed: ClassVar[bool] = False
    sealed_before_confirmation_access: ClassVar[bool] = True
    confirmation_values_accessed: ClassVar[bool] = False
    confirmation_access_facts_are_external_attestations: ClassVar[bool] = True
    cryptographic_confirmation_access_proof: ClassVar[bool] = False

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "admission_spec_id",
            "selection_profile_id",
            "claim_ceiling",
            "selection_terminal_binding_sha256",
            "selection_generator_family_id",
            "selection_construction_family_id",
            "required_surrogate_estimator_id",
            "required_surrogate_trivialization_id",
            "selection_implementation_registry_sha256",
            "required_distinct_generator_family",
            "required_distinct_construction_family",
            "source_or_implementation_change_alone_sufficient",
            "seed_change_alone_sufficient",
            "required_case_semantics",
            "required_graph_axes_sha256",
            "required_core_and_loop_separation",
            "required_stress_strata_sha256",
            "required_cells_manifest_sha256",
            "locked_thresholds_sha256",
            "locked_aggregation_sha256",
            "selection_evidence_disjointness_required",
            "policy_override_allowed",
            "post_selection_exclusion_allowed",
            "sealed_before_confirmation_access",
            "confirmation_values_accessed",
            "confirmation_access_facts_are_external_attestations",
            "cryptographic_confirmation_access_proof",
            "authority",
        }
    )

    def __post_init__(self) -> None:
        for name in (
            "admission_spec_id",
            "selection_generator_family_id",
            "selection_construction_family_id",
            "required_surrogate_estimator_id",
            "required_surrogate_trivialization_id",
        ):
            require_slug(getattr(self, name), label=f"admission {name}")
        for name in (
            "selection_terminal_binding_sha256",
            "selection_implementation_registry_sha256",
            "required_graph_axes_sha256",
            "required_stress_strata_sha256",
            "required_cells_manifest_sha256",
            "locked_thresholds_sha256",
            "locked_aggregation_sha256",
        ):
            require_sha256(getattr(self, name), label=f"admission {name}")
        semantics = _canonical_strings(
            self.required_case_semantics,
            label="required_case_semantics",
        )
        if semantics != _REQUIRED_CASE_SEMANTICS:
            raise QualificationContractError(
                "required case semantics differ from the selected profile"
            )
        if (
            self.selection_construction_family_id
            != CARTESIAN_SELECTION_CONSTRUCTION_FAMILY_ID
        ):
            raise QualificationContractError(
                "admission selection construction differs from the D6 profile"
            )

    @classmethod
    def from_selection(
        cls,
        binding: SelectionTerminalBinding,
        *,
        admission_spec_id: str,
    ) -> IndependentConfirmationAdmissionSpec:
        if not isinstance(binding, SelectionTerminalBinding):
            raise TypeError("binding must be a SelectionTerminalBinding")
        return cls(
            admission_spec_id=admission_spec_id,
            selection_terminal_binding_sha256=binding.canonical_sha256,
            selection_generator_family_id=(
                binding.selection_generator_family_id
            ),
            selection_construction_family_id=(
                binding.selection_construction_family_id
            ),
            required_surrogate_estimator_id=binding.surrogate_estimator_id,
            required_surrogate_trivialization_id=(
                binding.surrogate_trivialization_id
            ),
            selection_implementation_registry_sha256=(
                binding.selection_implementation_registry_sha256
            ),
            required_case_semantics=_REQUIRED_CASE_SEMANTICS,
            required_graph_axes_sha256=binding.graph_axes_sha256,
            required_stress_strata_sha256=(
                binding.required_stress_strata_sha256
            ),
            required_cells_manifest_sha256=(
                binding.required_cells_manifest_sha256
            ),
            locked_thresholds_sha256=binding.locked_thresholds_sha256,
            locked_aggregation_sha256=binding.locked_aggregation_sha256,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "admission_spec_id": self.admission_spec_id,
            "selection_profile_id": self.selection_profile_id,
            "claim_ceiling": self.claim_ceiling,
            "selection_terminal_binding_sha256": (
                self.selection_terminal_binding_sha256
            ),
            "selection_generator_family_id": (
                self.selection_generator_family_id
            ),
            "selection_construction_family_id": (
                self.selection_construction_family_id
            ),
            "required_surrogate_estimator_id": (
                self.required_surrogate_estimator_id
            ),
            "required_surrogate_trivialization_id": (
                self.required_surrogate_trivialization_id
            ),
            "selection_implementation_registry_sha256": (
                self.selection_implementation_registry_sha256
            ),
            "required_distinct_generator_family": (
                self.required_distinct_generator_family
            ),
            "required_distinct_construction_family": (
                self.required_distinct_construction_family
            ),
            "source_or_implementation_change_alone_sufficient": (
                self.source_or_implementation_change_alone_sufficient
            ),
            "seed_change_alone_sufficient": self.seed_change_alone_sufficient,
            "required_case_semantics": list(self.required_case_semantics),
            "required_graph_axes_sha256": self.required_graph_axes_sha256,
            "required_core_and_loop_separation": (
                self.required_core_and_loop_separation
            ),
            "required_stress_strata_sha256": (
                self.required_stress_strata_sha256
            ),
            "required_cells_manifest_sha256": (
                self.required_cells_manifest_sha256
            ),
            "locked_thresholds_sha256": self.locked_thresholds_sha256,
            "locked_aggregation_sha256": self.locked_aggregation_sha256,
            "selection_evidence_disjointness_required": (
                self.selection_evidence_disjointness_required
            ),
            "policy_override_allowed": self.policy_override_allowed,
            "post_selection_exclusion_allowed": (
                self.post_selection_exclusion_allowed
            ),
            "sealed_before_confirmation_access": (
                self.sealed_before_confirmation_access
            ),
            "confirmation_values_accessed": self.confirmation_values_accessed,
            "confirmation_access_facts_are_external_attestations": (
                self.confirmation_access_facts_are_external_attestations
            ),
            "cryptographic_confirmation_access_proof": (
                self.cryptographic_confirmation_access_proof
            ),
            "authority": _authority_dict(),
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> IndependentConfirmationAdmissionSpec:
        item = _mapping(value, label="confirmation admission spec")
        _exact_keys(item, cls._ROOT_KEYS, label="confirmation admission spec")
        constants = {
            "schema_version": cls.schema_version,
            "selection_profile_id": SURROGATE_PROFILE_ID,
            "claim_ceiling": "level_0",
            "required_distinct_generator_family": True,
            "required_distinct_construction_family": True,
            "source_or_implementation_change_alone_sufficient": False,
            "seed_change_alone_sufficient": False,
            "required_core_and_loop_separation": True,
            "selection_evidence_disjointness_required": True,
            "policy_override_allowed": False,
            "post_selection_exclusion_allowed": False,
            "sealed_before_confirmation_access": True,
            "confirmation_values_accessed": False,
            "confirmation_access_facts_are_external_attestations": True,
            "cryptographic_confirmation_access_proof": False,
        }
        for name, expected in constants.items():
            _constant(item[name], expected, label=f"admission {name}")
        authority = _mapping(item["authority"], label="admission authority")
        _exact_keys(authority, _AUTHORITY_KEYS, label="admission authority")
        _false_authority(authority, label="admission authority")
        semantics = tuple(
            _text(entry, label="required_case_semantics item")
            for entry in _sequence(
                item["required_case_semantics"],
                label="required_case_semantics",
            )
        )
        return cls(
            admission_spec_id=require_slug(
                item["admission_spec_id"],
                label="admission_spec_id",
            ),
            selection_terminal_binding_sha256=require_sha256(
                item["selection_terminal_binding_sha256"],
                label="selection_terminal_binding_sha256",
            ),
            selection_generator_family_id=require_slug(
                item["selection_generator_family_id"],
                label="selection_generator_family_id",
            ),
            selection_construction_family_id=require_slug(
                item["selection_construction_family_id"],
                label="selection_construction_family_id",
            ),
            required_surrogate_estimator_id=require_slug(
                item["required_surrogate_estimator_id"],
                label="required_surrogate_estimator_id",
            ),
            required_surrogate_trivialization_id=require_slug(
                item["required_surrogate_trivialization_id"],
                label="required_surrogate_trivialization_id",
            ),
            selection_implementation_registry_sha256=require_sha256(
                item["selection_implementation_registry_sha256"],
                label="selection_implementation_registry_sha256",
            ),
            required_case_semantics=semantics,
            required_graph_axes_sha256=require_sha256(
                item["required_graph_axes_sha256"],
                label="required_graph_axes_sha256",
            ),
            required_stress_strata_sha256=require_sha256(
                item["required_stress_strata_sha256"],
                label="required_stress_strata_sha256",
            ),
            required_cells_manifest_sha256=require_sha256(
                item["required_cells_manifest_sha256"],
                label="required_cells_manifest_sha256",
            ),
            locked_thresholds_sha256=require_sha256(
                item["locked_thresholds_sha256"],
                label="locked_thresholds_sha256",
            ),
            locked_aggregation_sha256=require_sha256(
                item["locked_aggregation_sha256"],
                label="locked_aggregation_sha256",
            ),
        )


@dataclass(frozen=True, slots=True)
class SurrogateAdvancementDecision:
    """D6 pass for one surrogate profile; D7/D8 remain not-run."""

    decision_id: str
    decision_source_commit: str
    decision_source_binding_sha256: str
    selection_terminal: SelectionTerminalBinding
    confirmation_admission_spec: IndependentConfirmationAdmissionSpec

    schema_version: ClassVar[str] = (
        SURROGATE_ADVANCEMENT_DECISION_SCHEMA_VERSION
    )
    selection_profile_id: ClassVar[str] = SURROGATE_PROFILE_ID
    advancement_scope: ClassVar[str] = SURROGATE_ADVANCEMENT_SCOPE
    decision_status: ClassVar[str] = "sealed"
    authoritative_commit_validation_required: ClassVar[bool] = True
    authoritative_commit_validation_embedded: ClassVar[bool] = False
    claim_ceiling: ClassVar[str] = "level_0"
    d6_state: ClassVar[str] = "pass"
    d6_scope: ClassVar[str] = SURROGATE_ADVANCEMENT_SCOPE
    confirmation_family_admitted: ClassVar[bool] = False
    sealed_before_confirmation_access: ClassVar[bool] = True
    confirmation_values_accessed: ClassVar[bool] = False
    confirmation_access_facts_are_external_attestations: ClassVar[bool] = True
    cryptographic_confirmation_access_proof: ClassVar[bool] = False
    d7_state: ClassVar[str] = "not_run"
    d7_reason_codes: ClassVar[tuple[str, ...]] = D7_NOT_RUN_REASON_CODES
    d8_state: ClassVar[str] = "not_run"
    d8_reason_codes: ClassVar[tuple[str, ...]] = D8_NOT_RUN_REASON_CODES

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "decision_id",
            "decision_source_commit",
            "decision_source_binding_sha256",
            "selection_profile_id",
            "advancement_scope",
            "decision_status",
            "authoritative_commit_validation_required",
            "authoritative_commit_validation_embedded",
            "claim_ceiling",
            "selection_terminal",
            "confirmation_admission_spec",
            "d6",
            "confirmation_family_admitted",
            "sealed_before_confirmation_access",
            "confirmation_values_accessed",
            "confirmation_access_facts_are_external_attestations",
            "cryptographic_confirmation_access_proof",
            "d7",
            "d8",
            "authority",
        }
    )

    def __post_init__(self) -> None:
        require_slug(self.decision_id, label="decision_id")
        _git_commit(
            self.decision_source_commit,
            label="decision_source_commit",
        )
        require_sha256(
            self.decision_source_binding_sha256,
            label="decision_source_binding_sha256",
        )
        if not isinstance(self.selection_terminal, SelectionTerminalBinding):
            raise TypeError(
                "selection_terminal must be a SelectionTerminalBinding"
            )
        if not isinstance(
            self.confirmation_admission_spec,
            IndependentConfirmationAdmissionSpec,
        ):
            raise TypeError(
                "confirmation_admission_spec must be an "
                "IndependentConfirmationAdmissionSpec"
            )
        admission_spec = self.confirmation_admission_spec
        if (
            admission_spec.selection_terminal_binding_sha256
            != self.selection_terminal.canonical_sha256
            or admission_spec.selection_generator_family_id
            != self.selection_terminal.selection_generator_family_id
            or admission_spec.selection_construction_family_id
            != self.selection_terminal.selection_construction_family_id
            or admission_spec.required_surrogate_estimator_id
            != self.selection_terminal.surrogate_estimator_id
            or admission_spec.required_surrogate_trivialization_id
            != self.selection_terminal.surrogate_trivialization_id
            or admission_spec.selection_implementation_registry_sha256
            != self.selection_terminal.selection_implementation_registry_sha256
            or admission_spec.required_graph_axes_sha256
            != self.selection_terminal.graph_axes_sha256
            or admission_spec.required_stress_strata_sha256
            != self.selection_terminal.required_stress_strata_sha256
            or admission_spec.required_cells_manifest_sha256
            != self.selection_terminal.required_cells_manifest_sha256
            or admission_spec.locked_thresholds_sha256
            != self.selection_terminal.locked_thresholds_sha256
            or admission_spec.locked_aggregation_sha256
            != self.selection_terminal.locked_aggregation_sha256
        ):
            raise QualificationContractError(
                "confirmation admission spec differs from the selected terminal"
            )

    @classmethod
    def seal(
        cls,
        *,
        decision_id: str,
        decision_source_commit: str,
        decision_source_binding_sha256: str,
        selection_terminal: SelectionTerminalBinding,
        admission_spec: IndependentConfirmationAdmissionSpec,
    ) -> SurrogateAdvancementDecision:
        if not isinstance(
            selection_terminal,
            SelectionTerminalBinding,
        ):
            raise TypeError(
                "selection_terminal must be a SelectionTerminalBinding"
            )
        if not isinstance(
            admission_spec,
            IndependentConfirmationAdmissionSpec,
        ):
            raise TypeError(
                "admission_spec must be an IndependentConfirmationAdmissionSpec"
            )
        return cls(
            decision_id=decision_id,
            decision_source_commit=decision_source_commit,
            decision_source_binding_sha256=decision_source_binding_sha256,
            selection_terminal=selection_terminal,
            confirmation_admission_spec=admission_spec,
        )

    def validate_admission_spec(
        self,
        spec: IndependentConfirmationAdmissionSpec,
    ) -> None:
        if spec != self.confirmation_admission_spec:
            raise QualificationContractError(
                "decision differs from its exact confirmation admission spec"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "decision_id": self.decision_id,
            "decision_source_commit": self.decision_source_commit,
            "decision_source_binding_sha256": (
                self.decision_source_binding_sha256
            ),
            "selection_profile_id": self.selection_profile_id,
            "advancement_scope": self.advancement_scope,
            "decision_status": self.decision_status,
            "authoritative_commit_validation_required": (
                self.authoritative_commit_validation_required
            ),
            "authoritative_commit_validation_embedded": (
                self.authoritative_commit_validation_embedded
            ),
            "claim_ceiling": self.claim_ceiling,
            "selection_terminal": self.selection_terminal.to_dict(),
            "confirmation_admission_spec": (
                self.confirmation_admission_spec.to_dict()
            ),
            "d6": {
                "state": self.d6_state,
                "scope": self.d6_scope,
            },
            "confirmation_family_admitted": self.confirmation_family_admitted,
            "sealed_before_confirmation_access": (
                self.sealed_before_confirmation_access
            ),
            "confirmation_values_accessed": self.confirmation_values_accessed,
            "confirmation_access_facts_are_external_attestations": (
                self.confirmation_access_facts_are_external_attestations
            ),
            "cryptographic_confirmation_access_proof": (
                self.cryptographic_confirmation_access_proof
            ),
            "d7": {
                "state": self.d7_state,
                "reason_codes": list(self.d7_reason_codes),
            },
            "d8": {
                "state": self.d8_state,
                "reason_codes": list(self.d8_reason_codes),
            },
            "authority": _authority_dict(),
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> SurrogateAdvancementDecision:
        item = _mapping(value, label="surrogate advancement decision")
        _exact_keys(item, cls._ROOT_KEYS, label="surrogate advancement decision")
        constants = {
            "schema_version": cls.schema_version,
            "selection_profile_id": SURROGATE_PROFILE_ID,
            "advancement_scope": SURROGATE_ADVANCEMENT_SCOPE,
            "decision_status": "sealed",
            "authoritative_commit_validation_required": True,
            "authoritative_commit_validation_embedded": False,
            "claim_ceiling": "level_0",
            "confirmation_family_admitted": False,
            "sealed_before_confirmation_access": True,
            "confirmation_values_accessed": False,
            "confirmation_access_facts_are_external_attestations": True,
            "cryptographic_confirmation_access_proof": False,
        }
        for name, expected in constants.items():
            _constant(item[name], expected, label=f"decision {name}")
        d6 = _mapping(item["d6"], label="decision d6")
        _exact_keys(d6, frozenset({"state", "scope"}), label="decision d6")
        _constant(d6["state"], "pass", label="decision d6.state")
        _constant(
            d6["scope"],
            SURROGATE_ADVANCEMENT_SCOPE,
            label="decision d6.scope",
        )
        for gate_name, expected_reasons in (
            ("d7", D7_NOT_RUN_REASON_CODES),
            ("d8", D8_NOT_RUN_REASON_CODES),
        ):
            gate = _mapping(item[gate_name], label=f"decision {gate_name}")
            _exact_keys(
                gate,
                frozenset({"state", "reason_codes"}),
                label=f"decision {gate_name}",
            )
            _constant(
                gate["state"],
                "not_run",
                label=f"decision {gate_name}.state",
            )
            reasons = tuple(
                _text(entry, label=f"decision {gate_name} reason")
                for entry in _sequence(
                    gate["reason_codes"],
                    label=f"decision {gate_name}.reason_codes",
                )
            )
            if reasons != expected_reasons:
                raise QualificationContractError(
                    f"decision {gate_name} reasons differ from the contract"
                )
        authority = _mapping(item["authority"], label="decision authority")
        _exact_keys(authority, _AUTHORITY_KEYS, label="decision authority")
        _false_authority(authority, label="decision authority")
        return cls(
            decision_id=require_slug(item["decision_id"], label="decision_id"),
            decision_source_commit=_git_commit(
                item["decision_source_commit"],
                label="decision_source_commit",
            ),
            decision_source_binding_sha256=require_sha256(
                item["decision_source_binding_sha256"],
                label="decision_source_binding_sha256",
            ),
            selection_terminal=SelectionTerminalBinding.from_dict(
                item["selection_terminal"]
            ),
            confirmation_admission_spec=(
                IndependentConfirmationAdmissionSpec.from_dict(
                    item["confirmation_admission_spec"]
                )
            ),
        )


AdvancementArtifact = SurrogateAdvancementDecision


@dataclass(frozen=True, slots=True)
class PersistedAdvancementIdentity:
    """Exact identity of one no-overwrite D6 artifact."""

    path: Path
    source_sha256: str
    canonical_sha256: str
    byte_count: int
    parent_directory_fsync_verified: bool

    def __post_init__(self) -> None:
        if not isinstance(self.path, Path) or not self.path.is_absolute():
            raise TypeError("path must be an absolute Path")
        require_sha256(self.source_sha256, label="source_sha256")
        require_sha256(self.canonical_sha256, label="canonical_sha256")
        if type(self.byte_count) is not int or self.byte_count <= 0:
            raise QualificationContractError(
                "byte_count must be a positive integer"
            )
        require_bool(
            self.parent_directory_fsync_verified,
            label="parent_directory_fsync_verified",
        )


@dataclass(frozen=True, slots=True)
class LoadedAdvancementArtifact:
    """A strict canonical D6 artifact and its exact file identity."""

    artifact: AdvancementArtifact
    identity: PersistedAdvancementIdentity
    source_bytes: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.artifact, SurrogateAdvancementDecision):
            raise TypeError(
                "artifact must be a SurrogateAdvancementDecision"
            )
        if not isinstance(self.identity, PersistedAdvancementIdentity):
            raise TypeError("identity must be a PersistedAdvancementIdentity")
        if not isinstance(self.source_bytes, bytes) or not self.source_bytes:
            raise TypeError("source_bytes must be nonempty bytes")
        if (
            self.source_bytes != self.artifact.canonical_bytes
            or hashlib.sha256(self.source_bytes).hexdigest()
            != self.identity.source_sha256
            or self.artifact.canonical_sha256
            != self.identity.canonical_sha256
            or len(self.source_bytes) != self.identity.byte_count
        ):
            raise QualificationContractError(
                "loaded advancement artifact differs from its identity"
            )


def _absolute(path: str | Path) -> Path:
    return Path(os.path.abspath(Path(path)))


def _read_artifact(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise QualificationContractError(
            "advancement artifact must be a regular non-symlink file"
        )
    try:
        with path.open("rb") as handle:
            source = handle.read(MAX_ADVANCEMENT_ARTIFACT_BYTES + 1)
    except OSError as error:
        raise QualificationContractError(
            f"cannot read advancement artifact: {error}"
        ) from error
    if not source:
        raise QualificationContractError("advancement artifact must not be empty")
    if len(source) > MAX_ADVANCEMENT_ARTIFACT_BYTES:
        raise QualificationContractError(
            "advancement artifact exceeds the fixed byte cap"
        )
    return source


def _load_advancement_artifact(
    path: str | Path,
    *,
    expected_source_sha256: str,
    expected_canonical_sha256: str,
    _parent_directory_fsync_verified: bool = False,
) -> LoadedAdvancementArtifact:
    """Load one bounded canonical D6 artifact with mandatory digests."""

    expected_source = require_sha256(
        expected_source_sha256,
        label="expected_source_sha256",
    )
    expected_canonical = require_sha256(
        expected_canonical_sha256,
        label="expected_canonical_sha256",
    )
    source_path = _absolute(path)
    source = _read_artifact(source_path)
    source_sha256 = hashlib.sha256(source).hexdigest()
    if source_sha256 != expected_source:
        raise QualificationContractError(
            "advancement artifact source digest differs"
        )
    try:
        document = parse_canonical_json(source, label="advancement artifact")
    except CanonicalJsonError as error:
        raise QualificationContractError(str(error)) from error
    item = _mapping(document, label="advancement artifact")
    schema = item.get("schema_version")
    if schema != SURROGATE_ADVANCEMENT_DECISION_SCHEMA_VERSION:
        raise QualificationContractError(
            "unsupported advancement artifact schema"
        )
    artifact = SurrogateAdvancementDecision.from_dict(item)
    if (
        artifact.canonical_bytes != source
        or artifact.canonical_sha256 != expected_canonical
    ):
        raise QualificationContractError(
            "advancement artifact canonical identity differs"
        )
    identity = PersistedAdvancementIdentity(
        path=source_path,
        source_sha256=source_sha256,
        canonical_sha256=artifact.canonical_sha256,
        byte_count=len(source),
        parent_directory_fsync_verified=require_bool(
            _parent_directory_fsync_verified,
            label="_parent_directory_fsync_verified",
        ),
    )
    return LoadedAdvancementArtifact(
        artifact=artifact,
        identity=identity,
        source_bytes=source,
    )


def _write_advancement_artifact(
    path: str | Path,
    artifact: AdvancementArtifact,
) -> LoadedAdvancementArtifact:
    """Atomically publish one D6 artifact without overwrite and reload it."""

    if not isinstance(artifact, SurrogateAdvancementDecision):
        raise TypeError(
            "artifact must be a SurrogateAdvancementDecision"
        )
    destination = _absolute(path)
    parent = destination.parent
    if parent.is_symlink() or not parent.is_dir():
        raise QualificationContractError(
            "advancement artifact parent must be a real directory"
        )
    if destination.exists() or destination.is_symlink():
        raise QualificationContractError(
            "refusing to overwrite an advancement artifact"
        )
    payload = artifact.canonical_bytes
    if len(payload) > MAX_ADVANCEMENT_ARTIFACT_BYTES:
        raise QualificationContractError(
            "advancement artifact exceeds the fixed byte cap"
        )
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError as error:
            raise QualificationContractError(
                "refusing to overwrite an advancement artifact"
            ) from error
        except OSError as error:
            raise QualificationContractError(
                f"cannot publish advancement artifact: {error}"
            ) from error
        parent_directory_fsync_verified = False
        try:
            directory_descriptor = os.open(parent, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
                parent_directory_fsync_verified = True
            finally:
                os.close(directory_descriptor)
        except OSError:
            parent_directory_fsync_verified = False
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return _load_advancement_artifact(
        destination,
        expected_source_sha256=artifact.canonical_sha256,
        expected_canonical_sha256=artifact.canonical_sha256,
        _parent_directory_fsync_verified=(
            parent_directory_fsync_verified
        ),
    )


@dataclass(frozen=True, slots=True)
class PublishedScopeLimitedD6Decision:
    """Validated candidate publication that still requires a Git commit."""

    loaded_artifact: LoadedAdvancementArtifact
    historical_terminal_companions_verified: bool = True
    decision_source_surface_verified: bool = True
    embedded_admission_spec_verified: bool = True
    committed_artifact_verified: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.loaded_artifact, LoadedAdvancementArtifact):
            raise TypeError(
                "loaded_artifact must be a LoadedAdvancementArtifact"
            )
        for name in (
            "historical_terminal_companions_verified",
            "decision_source_surface_verified",
            "embedded_admission_spec_verified",
        ):
            _constant(
                getattr(self, name),
                True,
                label=f"published D6 decision {name}",
            )
        _constant(
            self.committed_artifact_verified,
            False,
            label="published D6 decision committed_artifact_verified",
        )

    @property
    def decision(self) -> SurrogateAdvancementDecision:
        return self.loaded_artifact.artifact

    @property
    def identity(self) -> PersistedAdvancementIdentity:
        return self.loaded_artifact.identity

    @property
    def parent_directory_fsync_verified(self) -> bool:
        return self.identity.parent_directory_fsync_verified


@dataclass(frozen=True, slots=True, init=False)
class LoadedScopeLimitedD6Decision:
    """Authoritatively rejoined D6 decision and its canonical file identity."""

    loaded_artifact: LoadedAdvancementArtifact
    historical_terminal_companions_verified: bool = True
    decision_source_surface_verified: bool = True
    embedded_admission_spec_verified: bool = True
    committed_artifact_verified: bool = True
    current_source_compatibility_verified: bool = False
    historical_engine_reexecution_verified: bool = False
    historical_d1_recomputation_performed: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.loaded_artifact, LoadedAdvancementArtifact):
            raise TypeError(
                "loaded_artifact must be a LoadedAdvancementArtifact"
            )
        for name in (
            "historical_terminal_companions_verified",
            "decision_source_surface_verified",
            "embedded_admission_spec_verified",
            "committed_artifact_verified",
        ):
            _constant(
                getattr(self, name),
                True,
                label=f"loaded D6 decision {name}",
            )
        for name in (
            "current_source_compatibility_verified",
            "historical_engine_reexecution_verified",
            "historical_d1_recomputation_performed",
        ):
            _constant(
                getattr(self, name),
                False,
                label=f"loaded D6 decision {name}",
            )

    @property
    def decision(self) -> SurrogateAdvancementDecision:
        return self.loaded_artifact.artifact

    @property
    def identity(self) -> PersistedAdvancementIdentity:
        return self.loaded_artifact.identity

    @property
    def source_bytes(self) -> bytes:
        return self.loaded_artifact.source_bytes


def _build_authoritative_loaded_d6_decision(
    loaded_artifact: LoadedAdvancementArtifact,
) -> LoadedScopeLimitedD6Decision:
    """Construct the public receipt only after the loader finishes all gates."""

    receipt = object.__new__(LoadedScopeLimitedD6Decision)
    values: tuple[tuple[str, object], ...] = (
        ("loaded_artifact", loaded_artifact),
        ("historical_terminal_companions_verified", True),
        ("decision_source_surface_verified", True),
        ("embedded_admission_spec_verified", True),
        ("committed_artifact_verified", True),
        ("current_source_compatibility_verified", False),
        ("historical_engine_reexecution_verified", False),
        ("historical_d1_recomputation_performed", False),
    )
    for name, value in values:
        object.__setattr__(receipt, name, value)
    receipt.__post_init__()
    return receipt


def _rebuild_selection_terminal_binding(
    *,
    launch_descriptor: str | Path,
    launch_descriptor_source_sha256: str,
    launch_descriptor_canonical_sha256: str,
    terminal_manifest_sha256: str,
    terminal_result_sha256: str,
    terminal_consumption_sha256: str,
) -> tuple[SelectionTerminalBinding, Path]:
    """Reload the committed H terminal and return only its seed-free binding."""

    from .contracts import QualificationResult
    from .launch import (
        load_committed_selection_terminal,
        load_prepared_selection_launch_descriptor,
    )
    from .persistence import load_qualification_protocol

    descriptor_path = _absolute(launch_descriptor)
    loaded_descriptor = load_prepared_selection_launch_descriptor(
        descriptor_path,
        expected_source_sha256=launch_descriptor_source_sha256,
        expected_canonical_sha256=launch_descriptor_canonical_sha256,
    )
    loaded_terminal = load_committed_selection_terminal(
        descriptor_path,
        expected_descriptor_source_sha256=(
            launch_descriptor_source_sha256
        ),
        expected_descriptor_canonical_sha256=(
            launch_descriptor_canonical_sha256
        ),
        expected_terminal_manifest_sha256=terminal_manifest_sha256,
        expected_terminal_artifact_sha256=terminal_result_sha256,
        expected_consumption_sha256=terminal_consumption_sha256,
    )
    if not isinstance(loaded_terminal.terminal_artifact, QualificationResult):
        raise QualificationContractError(
            "D6 requires a successful committed qualification-result terminal"
        )
    if (
        loaded_terminal.archival_contract_parser_used is not True
        or loaded_terminal.historical_d1_recomputation_performed is not False
        or loaded_terminal.current_source_compatibility_verified is not False
        or loaded_terminal.historical_engine_reexecution_verified is not False
    ):
        raise QualificationContractError(
            "committed terminal archival verification flags differ"
        )
    descriptor = loaded_descriptor.descriptor
    loaded_protocol = load_qualification_protocol(
        descriptor.protocol_path,
        expected_source_sha256=descriptor.protocol_source_sha256,
        expected_canonical_sha256=descriptor.protocol_canonical_sha256,
    )
    binding = build_selection_terminal_binding(
        result=loaded_terminal.terminal_artifact,
        protocol=loaded_protocol.protocol,
        terminal_identity=loaded_terminal.terminal_identity,
        consumption=loaded_terminal.consumption,
    )
    return binding, _resolve_repository(descriptor.repository_root)


def _require_committed_decision_artifact(
    repository: Path,
    loaded: LoadedAdvancementArtifact,
) -> None:
    """Require the D6 bundle to be one clean tracked current-HEAD blob."""

    try:
        repository_path = loaded.identity.path.relative_to(repository).as_posix()
    except ValueError as error:
        raise QualificationContractError(
            "D6 decision artifact must be inside repository_root"
        ) from error
    head_before = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "--verify", "HEAD^{commit}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if head_before.returncode != 0:
        raise QualificationContractError(
            "cannot resolve committed D6 artifact HEAD"
        )
    current_head = _git_commit(
        head_before.stdout.strip(),
        label="committed D6 artifact HEAD",
    )
    tracked = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "ls-files",
            "--error-unmatch",
            "--",
            repository_path,
        ],
        check=False,
        capture_output=True,
    )
    status = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--",
            repository_path,
        ],
        check=False,
        capture_output=True,
    )
    blob = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "show",
            f"{current_head}:{repository_path}",
        ],
        check=False,
        capture_output=True,
    )
    if (
        tracked.returncode != 0
        or status.returncode != 0
        or status.stdout
        or blob.returncode != 0
        or blob.stdout != loaded.source_bytes
    ):
        raise QualificationContractError(
            "D6 decision artifact is not one clean tracked current-HEAD blob"
        )
    existed_at_source = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "cat-file",
            "-e",
            (
                f"{loaded.artifact.decision_source_commit}:"
                f"{repository_path}"
            ),
        ],
        check=False,
        capture_output=True,
    )
    if existed_at_source.returncode == 0:
        raise QualificationContractError(
            "D6 decision artifact already existed at its source commit"
        )
    head_after = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "--verify", "HEAD^{commit}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if (
        head_after.returncode != 0
        or head_after.stdout.strip() != current_head
    ):
        raise QualificationContractError(
            "D6 artifact HEAD changed during committed verification"
        )


def load_scope_limited_d6_decision(
    path: str | Path,
    *,
    expected_source_sha256: str,
    expected_canonical_sha256: str,
    expected_decision_id: str,
    expected_admission_spec_id: str,
    launch_descriptor: str | Path,
    launch_descriptor_source_sha256: str,
    launch_descriptor_canonical_sha256: str,
    terminal_manifest_sha256: str,
    terminal_result_sha256: str,
    terminal_consumption_sha256: str,
) -> LoadedScopeLimitedD6Decision:
    """Load D6 only after source, H terminal, and embedded spec all rejoin."""

    decision_id = require_slug(
        expected_decision_id,
        label="expected_decision_id",
    )
    admission_spec_id = require_slug(
        expected_admission_spec_id,
        label="expected_admission_spec_id",
    )
    loaded = _load_advancement_artifact(
        path,
        expected_source_sha256=expected_source_sha256,
        expected_canonical_sha256=expected_canonical_sha256,
    )
    decision = loaded.artifact
    if (
        decision.decision_id != decision_id
        or decision.confirmation_admission_spec.admission_spec_id
        != admission_spec_id
    ):
        raise QualificationContractError(
            "D6 decision or admission-spec identity differs"
        )
    selection_terminal, repository = _rebuild_selection_terminal_binding(
        launch_descriptor=launch_descriptor,
        launch_descriptor_source_sha256=(
            launch_descriptor_source_sha256
        ),
        launch_descriptor_canonical_sha256=(
            launch_descriptor_canonical_sha256
        ),
        terminal_manifest_sha256=terminal_manifest_sha256,
        terminal_result_sha256=terminal_result_sha256,
        terminal_consumption_sha256=terminal_consumption_sha256,
    )
    validate_advancement_decision_source(
        decision,
        repository_root=repository,
    )
    expected_admission = IndependentConfirmationAdmissionSpec.from_selection(
        selection_terminal,
        admission_spec_id=admission_spec_id,
    )
    expected_decision = SurrogateAdvancementDecision.seal(
        decision_id=decision_id,
        decision_source_commit=decision.decision_source_commit,
        decision_source_binding_sha256=(
            decision.decision_source_binding_sha256
        ),
        selection_terminal=selection_terminal,
        admission_spec=expected_admission,
    )
    if decision != expected_decision:
        raise QualificationContractError(
            "D6 decision differs from its committed terminal or admission spec"
        )
    _require_committed_decision_artifact(repository, loaded)
    return _build_authoritative_loaded_d6_decision(loaded)


def publish_scope_limited_d6_decision(
    path: str | Path,
    *,
    decision_id: str,
    admission_spec_id: str,
    launch_descriptor: str | Path,
    launch_descriptor_source_sha256: str,
    launch_descriptor_canonical_sha256: str,
    terminal_manifest_sha256: str,
    terminal_result_sha256: str,
    terminal_consumption_sha256: str,
) -> PublishedScopeLimitedD6Decision:
    """Publish a validated D6 candidate; a later Git commit is still required."""

    selection_terminal, repository = _rebuild_selection_terminal_binding(
        launch_descriptor=launch_descriptor,
        launch_descriptor_source_sha256=(
            launch_descriptor_source_sha256
        ),
        launch_descriptor_canonical_sha256=(
            launch_descriptor_canonical_sha256
        ),
        terminal_manifest_sha256=terminal_manifest_sha256,
        terminal_result_sha256=terminal_result_sha256,
        terminal_consumption_sha256=terminal_consumption_sha256,
    )
    admission_spec = IndependentConfirmationAdmissionSpec.from_selection(
        selection_terminal,
        admission_spec_id=admission_spec_id,
    )
    source_commit, source_binding_sha256 = (
        build_current_advancement_source_binding(
            repository_root=repository,
        )
    )
    decision = SurrogateAdvancementDecision.seal(
        decision_id=decision_id,
        decision_source_commit=source_commit,
        decision_source_binding_sha256=source_binding_sha256,
        selection_terminal=selection_terminal,
        admission_spec=admission_spec,
    )
    destination = _absolute(path)
    try:
        destination.relative_to(repository)
    except ValueError as error:
        raise QualificationContractError(
            "published D6 decision must remain inside repository_root"
        ) from error
    written = _write_advancement_artifact(destination, decision)
    if written.artifact != decision:
        raise QualificationContractError(
            "published D6 decision differs after canonical reload"
        )
    validate_advancement_decision_source(
        decision,
        repository_root=repository,
    )
    return PublishedScopeLimitedD6Decision(loaded_artifact=written)


__all__ = [
    "ADVANCEMENT_SOURCE_BINDING_SCHEMA_VERSION",
    "CARTESIAN_SELECTION_CONSTRUCTION_FAMILY_ID",
    "D6_SELECTION_TERMINAL_BINDING_SCHEMA_VERSION",
    "D7_NOT_RUN_REASON_CODES",
    "D8_NOT_RUN_REASON_CODES",
    "INDEPENDENT_CONFIRMATION_ADMISSION_SCHEMA_VERSION",
    "MAX_ADVANCEMENT_ARTIFACT_BYTES",
    "SURROGATE_ADVANCEMENT_DECISION_SCHEMA_VERSION",
    "SURROGATE_ADVANCEMENT_SCOPE",
    "SURROGATE_PROFILE_ID",
    "IndependentConfirmationAdmissionSpec",
    "LoadedScopeLimitedD6Decision",
    "PublishedScopeLimitedD6Decision",
    "SelectionTerminalBinding",
    "SurrogateAdvancementDecision",
    "advancement_source_binding_sha256",
    "build_current_advancement_source_binding",
    "build_selection_terminal_binding",
    "load_scope_limited_d6_decision",
    "publish_scope_limited_d6_decision",
    "validate_advancement_decision_source",
]
