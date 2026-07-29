"""Closed Level-0 protocol for synthetic D0--D5 qualification.

The protocol is deliberately standalone from the P0 instrument bundle.  It
declares exact graph, control, stress, threshold, cell, and stratum manifests,
but contains no graph receipt, numerical field, core, loop, or subject value.
"""

from __future__ import annotations

import math
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import ClassVar

from spirallens.core.canonical import canonical_json_bytes, canonical_json_sha256
from spirallens.graphs import GraphFamily, GraphPurpose

from .common import (
    AttemptStatus,
    CoreDisposition,
    CorePredictionClass,
    EvaluationUnit,
    LoopDisposition,
    QualificationContractError,
)

QUALIFICATION_PROTOCOL_SCHEMA_VERSION = "spirallens.qualification-protocol.v0.8"
MAX_QUALIFICATION_PROTOCOL_BYTES = 4 * 1024 * 1024
MAX_QUALIFICATION_RESULT_BYTES_BOUND = 32 * 1024 * 1024
MAX_QUALIFICATION_PRIMARY_UNITS = 64
MAX_QUALIFICATION_CORE_CELLS = 192
MAX_QUALIFICATION_LOOP_CELLS = 1152
QUALIFICATION_EVENTS_PER_LANE = 6
MAX_QUALIFICATION_EVENT_LANES = (
    MAX_QUALIFICATION_CORE_CELLS + MAX_QUALIFICATION_LOOP_CELLS
)
MAX_QUALIFICATION_EVENT_ENTRIES = (
    MAX_QUALIFICATION_EVENT_LANES * QUALIFICATION_EVENTS_PER_LANE
)
MAX_LOOP_ORACLE_TOLERANCE_CYCLES = 1e-6
MAX_GRAPH_TOTAL_TOLERANCE_CYCLES = 1e-6
MIN_IDENTIFIABILITY_FLOOR = 1e-9
MIN_COHERENCE_FLOOR = 1e-9
MIN_BRANCH_MARGIN_RAD = 1e-9
MIN_FIELD_OUTPUT_EFFECT_SIZE = 1e-9
MAX_D1_NUMERIC_TOLERANCE = 1e-6
MIN_D1_COSINE_FLOOR = 0.9
MAX_SIGNED_INT64 = (1 << 63) - 1
F2_LOCAL_COVARIANT_SECTION_REFERENT_ID = "f2_local_covariant_section"
CLOSED_CARTESIAN_GENERATOR_FAMILY_ID = "cartesian-fourier-domain-v0.1"
CLOSED_CARTESIAN_ESTIMATOR_ID = "interleaved-first-harmonic-graph-local-direction-v0.4"
CLOSED_CARTESIAN_TRIVIALIZATION_ID = "fixed-cartesian-fourier-quadrature-basis-v0.1"
CLOSED_REPRESENTATION_ESTIMATOR_ID = (
    "local-rank-two-projector-global-reference-lift-v0.2"
)
CLOSED_REPRESENTATION_TRIVIALIZATION_ID = (
    "fit-split-global-reference-after-local-projector-v0.1"
)
CLOSED_CORE_LOCALIZER_ID = "truth-blind-localized-amplitude-core-v0.3"
D2_IDENTIFIABILITY_LOSS_DECOY_CONFOUNDER_ID = (
    "high-amplitude-local-identifiability-loss-decoy"
)
D2_MISSING_CANDIDATE_SUPPORT_CONFOUNDER_ID = (
    "low-amplitude-missing-candidate-support-abstain"
)
D2_IDENTIFIABILITY_LOSS_DECOY_CONSTRUCTION_ID = (
    "high-amplitude-offcenter-identifiability-loss-decoy-v0.2"
)
D2_MISSING_CANDIDATE_SUPPORT_CONSTRUCTION_ID = (
    "isolated-low-amplitude-measurement-hole-v0.2"
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_MODULE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*$")
_GRAPH_FAMILY_ORDER = (
    GraphFamily.MUTUAL_KNN,
    GraphFamily.FIXED_RADIUS,
    GraphFamily.SHARED_NEIGHBOR,
)
_GATE_ORDER = ("d0", "d1", "d2", "d3", "d4", "d5")
BOUNDARY_AXIS_ID = "boundary"
STATE_GEOMETRY_WARP_AXIS_ID = "state-geometry-warp"
STRUCTURED_OBSERVATION_PERTURBATION_AXIS_ID = "structured-observation-perturbation"


class GateClaimScope(str, Enum):
    """Positive scientific scope carried by every serialized gate verdict."""

    ENGINE_AND_PROTOCOL_CONTRACTS = "engine-and-protocol-contracts"
    CARTESIAN_SURROGATE_AND_REPRESENTATION_DEVELOPMENT = (
        "cartesian-surrogate-and-representation-development"
    )
    CARTESIAN_SURROGATE_ONLY = "cartesian-surrogate-only"


_GATE_CLAIM_SCOPES: dict[str, GateClaimScope] = {
    "d0": GateClaimScope.ENGINE_AND_PROTOCOL_CONTRACTS,
    "d1": GateClaimScope.CARTESIAN_SURROGATE_AND_REPRESENTATION_DEVELOPMENT,
    "d2": GateClaimScope.CARTESIAN_SURROGATE_ONLY,
    "d3": GateClaimScope.CARTESIAN_SURROGATE_AND_REPRESENTATION_DEVELOPMENT,
    "d4": GateClaimScope.CARTESIAN_SURROGATE_ONLY,
    "d5": GateClaimScope.CARTESIAN_SURROGATE_ONLY,
}


def gate_claim_scope_for_gate(gate_id: str) -> GateClaimScope:
    """Return the immutable positive claim scope for a closed gate ID."""

    try:
        return _GATE_CLAIM_SCOPES[gate_id]
    except KeyError as error:
        raise QualificationContractError(
            f"unknown qualification gate claim scope {gate_id!r}"
        ) from error


class CoreGraphMode(str, Enum):
    """Exact core/field graph binding available to this protocol."""

    INHERIT_FIELD_ESTIMATION_GRAPH = "inherit_field_estimation_graph"


class LoopRole(str, Enum):
    """Semantically distinct loop obligations inside every A x B cell."""

    PRIMARY_BOUNDARY = "primary_boundary"
    OFFCORE_CONTROL = "offcore_control"


def _mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise QualificationContractError(f"{label} must be a string-keyed mapping")
    return value


def _exact_keys(
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


def _sequence(value: object, *, label: str) -> list[object]:
    if not isinstance(value, list):
        raise QualificationContractError(f"{label} must be a JSON array")
    return value


def _constant(value: object, expected: object, *, label: str) -> object:
    if type(value) is not type(expected) or value != expected:
        raise QualificationContractError(f"{label} must equal {expected!r}")
    return value


def _string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise QualificationContractError(f"{label} must be a non-empty trimmed string")
    return value


def _slug(value: object, *, label: str) -> str:
    result = _string(value, label=label)
    if _SLUG.fullmatch(result) is None:
        raise QualificationContractError(f"{label} must be a lowercase portable slug")
    return result


def _sha256(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise QualificationContractError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _commit(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _COMMIT.fullmatch(value) is None:
        raise QualificationContractError(
            f"{label} must be a lowercase 40-character Git commit"
        )
    return value


def _plain_int(value: object, *, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise QualificationContractError(
            f"{label} must be an integer of at least {minimum}"
        )
    return value


def _plain_bool(value: object, *, label: str) -> bool:
    if type(value) is not bool:
        raise QualificationContractError(f"{label} must be a boolean")
    return value


def _finite_float(
    value: object,
    *,
    label: str,
    minimum: float | None = None,
    maximum: float | None = None,
    minimum_inclusive: bool = True,
    maximum_inclusive: bool = True,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise QualificationContractError(f"{label} must be a real number")
    result = float(value)
    if not math.isfinite(result):
        raise QualificationContractError(f"{label} must be finite")
    if result == 0.0 and math.copysign(1.0, result) < 0.0:
        raise QualificationContractError(f"{label} must not be negative zero")
    if minimum is not None and (
        result < minimum or (result == minimum and not minimum_inclusive)
    ):
        comparator = "at least" if minimum_inclusive else "greater than"
        raise QualificationContractError(f"{label} must be {comparator} {minimum}")
    if maximum is not None and (
        result > maximum or (result == maximum and not maximum_inclusive)
    ):
        comparator = "at most" if maximum_inclusive else "less than"
        raise QualificationContractError(f"{label} must be {comparator} {maximum}")
    return result


def _enum(enum_type: type[Enum], value: object, *, label: str) -> Enum:
    if not isinstance(value, str):
        raise QualificationContractError(f"{label} must be a string")
    try:
        return enum_type(value)
    except ValueError as error:
        raise QualificationContractError(f"{label} is not supported") from error


def _canonical_unique_slugs(
    values: tuple[str, ...],
    *,
    label: str,
    nonempty: bool = True,
) -> tuple[str, ...]:
    if nonempty and not values:
        raise QualificationContractError(f"{label} must not be empty")
    for index, value in enumerate(values):
        _slug(value, label=f"{label}[{index}]")
    if len(set(values)) != len(values):
        raise QualificationContractError(f"{label} must be unique")
    if values != tuple(sorted(values)):
        raise QualificationContractError(f"{label} must be in canonical order")
    return values


@dataclass(frozen=True, slots=True)
class ModuleDigest:
    """Exact source digest for one engine module."""

    module: str
    sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.module, str) or _MODULE.fullmatch(self.module) is None:
            raise QualificationContractError(
                "engine module must be a dotted Python module name"
            )
        _sha256(self.sha256, label=f"module_sha256[{self.module}]")

    def to_dict(self) -> dict[str, object]:
        return {"module": self.module, "sha256": self.sha256}

    @classmethod
    def from_dict(cls, value: object) -> ModuleDigest:
        item = _mapping(value, label="module digest")
        _exact_keys(item, {"module", "sha256"}, label="module digest")
        return cls(
            module=_string(item["module"], label="module"),
            sha256=_sha256(item["sha256"], label="sha256"),
        )


@dataclass(frozen=True, slots=True)
class RepositoryFileDigest:
    """Exact digest of one load-bearing non-module repository file."""

    repository_path: str
    sha256: str

    def __post_init__(self) -> None:
        path = Path(_string(self.repository_path, label="repository file path"))
        if (
            path.is_absolute()
            or ".." in path.parts
            or path.as_posix() != self.repository_path
        ):
            raise QualificationContractError(
                "repository file path must be a normalized relative path"
            )
        _sha256(self.sha256, label=f"repository file sha256[{self.repository_path}]")

    def to_dict(self) -> dict[str, object]:
        return {
            "repository_path": self.repository_path,
            "sha256": self.sha256,
        }

    @classmethod
    def from_dict(cls, value: object) -> RepositoryFileDigest:
        item = _mapping(value, label="repository file digest")
        _exact_keys(
            item,
            {"repository_path", "sha256"},
            label="repository file digest",
        )
        return cls(
            repository_path=_string(
                item["repository_path"],
                label="repository file path",
            ),
            sha256=_sha256(
                item["sha256"],
                label="repository file sha256",
            ),
        )


@dataclass(frozen=True, slots=True)
class EngineBinding:
    """Repository commit and exact module map used by the runner."""

    repository: str
    commit: str
    modules: tuple[ModuleDigest, ...]
    official_executables: tuple[RepositoryFileDigest, ...] = ()

    def __post_init__(self) -> None:
        _constant(
            self.repository,
            "RyoSpiralArchitect/SpiralLens",
            label="engine.repository",
        )
        _commit(self.commit, label="engine.commit")
        if not self.modules:
            raise QualificationContractError("engine.modules must not be empty")
        names = tuple(item.module for item in self.modules)
        if len(set(names)) != len(names):
            raise QualificationContractError("engine.modules must be unique")
        if names != tuple(sorted(names)):
            raise QualificationContractError(
                "engine.modules must be in canonical module order"
            )
        if type(self.official_executables) is not tuple:
            raise TypeError("engine.official_executables must be an immutable tuple")
        if any(
            not isinstance(item, RepositoryFileDigest)
            for item in self.official_executables
        ):
            raise TypeError(
                "engine.official_executables must contain RepositoryFileDigest"
            )
        paths = tuple(item.repository_path for item in self.official_executables)
        if len(set(paths)) != len(paths) or paths != tuple(sorted(paths)):
            raise QualificationContractError(
                "engine.official_executables must be unique and canonically ordered"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "repository": self.repository,
            "commit": self.commit,
            "modules": [item.to_dict() for item in self.modules],
            "official_executables": [
                item.to_dict() for item in self.official_executables
            ],
        }

    @classmethod
    def from_dict(cls, value: object) -> EngineBinding:
        item = _mapping(value, label="engine")
        _exact_keys(
            item,
            {"repository", "commit", "modules", "official_executables"},
            label="engine",
        )
        return cls(
            repository=_string(item["repository"], label="engine.repository"),
            commit=_commit(item["commit"], label="engine.commit"),
            modules=tuple(
                ModuleDigest.from_dict(entry)
                for entry in _sequence(item["modules"], label="engine.modules")
            ),
            official_executables=tuple(
                RepositoryFileDigest.from_dict(entry)
                for entry in _sequence(
                    item["official_executables"],
                    label="engine.official_executables",
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class RegistryBinding:
    """Content identities of the frozen hypothesis and referent registries."""

    registry_source_sha256: str
    registry_canonical_sha256: str
    referent_canonical_sha256: str

    def __post_init__(self) -> None:
        for name in (
            "registry_source_sha256",
            "registry_canonical_sha256",
            "referent_canonical_sha256",
        ):
            _sha256(getattr(self, name), label=f"registry.{name}")

    def to_dict(self) -> dict[str, object]:
        return {
            "registry_source_sha256": self.registry_source_sha256,
            "registry_canonical_sha256": self.registry_canonical_sha256,
            "referent_canonical_sha256": self.referent_canonical_sha256,
        }

    @classmethod
    def from_dict(cls, value: object) -> RegistryBinding:
        item = _mapping(value, label="registry")
        expected = {
            "registry_source_sha256",
            "registry_canonical_sha256",
            "referent_canonical_sha256",
        }
        _exact_keys(item, expected, label="registry")
        return cls(
            registry_source_sha256=_sha256(
                item["registry_source_sha256"],
                label="registry.registry_source_sha256",
            ),
            registry_canonical_sha256=_sha256(
                item["registry_canonical_sha256"],
                label="registry.registry_canonical_sha256",
            ),
            referent_canonical_sha256=_sha256(
                item["referent_canonical_sha256"],
                label="registry.referent_canonical_sha256",
            ),
        )


@dataclass(frozen=True, slots=True)
class PreseedReadinessBinding:
    """Exact durable artifact that precedes official selection-seed supply.

    This is evidence for the chronology implemented by the official local
    preparation process.  It is deliberately not cryptographic proof that a
    human or another process did not choose, record, or inspect a seed first.
    """

    artifact_path: str
    artifact_source_sha256: str
    artifact_canonical_sha256: str
    artifact_byte_count: int
    source_binding_receipt_sha256: str
    engine_commit: str
    registry_source_sha256: str
    registry_canonical_sha256: str
    referent_source_sha256: str
    referent_canonical_sha256: str
    chronology_claim: str = "official-process-attested"
    artifact_published_before_official_seed_supplier: bool = True
    artifact_roundtrip_verified_before_official_seed_supplier: bool = True
    cryptographic_preseed_proof: bool = False
    human_or_external_process_unseen_proof: bool = False

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "artifact_path",
            "artifact_source_sha256",
            "artifact_canonical_sha256",
            "artifact_byte_count",
            "source_binding_receipt_sha256",
            "engine_commit",
            "registry_source_sha256",
            "registry_canonical_sha256",
            "referent_source_sha256",
            "referent_canonical_sha256",
            "chronology_claim",
            "artifact_published_before_official_seed_supplier",
            "artifact_roundtrip_verified_before_official_seed_supplier",
            "cryptographic_preseed_proof",
            "human_or_external_process_unseen_proof",
        }
    )

    def __post_init__(self) -> None:
        path = Path(_string(self.artifact_path, label="preseed artifact_path"))
        if (
            not path.is_absolute()
            or str(Path(os.path.abspath(path))) != self.artifact_path
        ):
            raise QualificationContractError(
                "preseed artifact_path must be a normalized absolute path"
            )
        for name in (
            "artifact_source_sha256",
            "artifact_canonical_sha256",
            "source_binding_receipt_sha256",
            "registry_source_sha256",
            "registry_canonical_sha256",
            "referent_source_sha256",
            "referent_canonical_sha256",
        ):
            _sha256(getattr(self, name), label=f"preseed {name}")
        _commit(self.engine_commit, label="preseed engine_commit")
        if type(self.artifact_byte_count) is not int or self.artifact_byte_count < 1:
            raise QualificationContractError(
                "preseed artifact_byte_count must be a positive integer"
            )
        if self.artifact_source_sha256 != self.artifact_canonical_sha256:
            raise QualificationContractError(
                "preseed artifact source must be exact canonical bytes"
            )
        if self.referent_source_sha256 != self.referent_canonical_sha256:
            raise QualificationContractError(
                "preseed canonical referent source and identity must agree"
            )
        _constant(
            self.chronology_claim,
            "official-process-attested",
            label="preseed chronology_claim",
        )
        for name in (
            "artifact_published_before_official_seed_supplier",
            "artifact_roundtrip_verified_before_official_seed_supplier",
        ):
            _constant(getattr(self, name), True, label=f"preseed {name}")
        for name in (
            "cryptographic_preseed_proof",
            "human_or_external_process_unseen_proof",
        ):
            _constant(getattr(self, name), False, label=f"preseed {name}")

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_path": self.artifact_path,
            "artifact_source_sha256": self.artifact_source_sha256,
            "artifact_canonical_sha256": self.artifact_canonical_sha256,
            "artifact_byte_count": self.artifact_byte_count,
            "source_binding_receipt_sha256": self.source_binding_receipt_sha256,
            "engine_commit": self.engine_commit,
            "registry_source_sha256": self.registry_source_sha256,
            "registry_canonical_sha256": self.registry_canonical_sha256,
            "referent_source_sha256": self.referent_source_sha256,
            "referent_canonical_sha256": self.referent_canonical_sha256,
            "chronology_claim": self.chronology_claim,
            "artifact_published_before_official_seed_supplier": (
                self.artifact_published_before_official_seed_supplier
            ),
            "artifact_roundtrip_verified_before_official_seed_supplier": (
                self.artifact_roundtrip_verified_before_official_seed_supplier
            ),
            "cryptographic_preseed_proof": self.cryptographic_preseed_proof,
            "human_or_external_process_unseen_proof": (
                self.human_or_external_process_unseen_proof
            ),
        }

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> PreseedReadinessBinding:
        item = _mapping(value, label="preseed readiness binding")
        _exact_keys(item, cls._ROOT_KEYS, label="preseed readiness binding")
        return cls(
            artifact_path=_string(
                item["artifact_path"],
                label="preseed artifact_path",
            ),
            artifact_source_sha256=_sha256(
                item["artifact_source_sha256"],
                label="preseed artifact_source_sha256",
            ),
            artifact_canonical_sha256=_sha256(
                item["artifact_canonical_sha256"],
                label="preseed artifact_canonical_sha256",
            ),
            artifact_byte_count=_plain_int(
                item["artifact_byte_count"],
                label="preseed artifact_byte_count",
                minimum=1,
            ),
            source_binding_receipt_sha256=_sha256(
                item["source_binding_receipt_sha256"],
                label="preseed source_binding_receipt_sha256",
            ),
            engine_commit=_commit(
                item["engine_commit"],
                label="preseed engine_commit",
            ),
            registry_source_sha256=_sha256(
                item["registry_source_sha256"],
                label="preseed registry_source_sha256",
            ),
            registry_canonical_sha256=_sha256(
                item["registry_canonical_sha256"],
                label="preseed registry_canonical_sha256",
            ),
            referent_source_sha256=_sha256(
                item["referent_source_sha256"],
                label="preseed referent_source_sha256",
            ),
            referent_canonical_sha256=_sha256(
                item["referent_canonical_sha256"],
                label="preseed referent_canonical_sha256",
            ),
            chronology_claim=_constant(
                item["chronology_claim"],
                "official-process-attested",
                label="preseed chronology_claim",
            ),  # type: ignore[arg-type]
            artifact_published_before_official_seed_supplier=_constant(
                item["artifact_published_before_official_seed_supplier"],
                True,
                label="preseed artifact publication chronology",
            ),  # type: ignore[arg-type]
            artifact_roundtrip_verified_before_official_seed_supplier=_constant(
                item["artifact_roundtrip_verified_before_official_seed_supplier"],
                True,
                label="preseed artifact roundtrip chronology",
            ),  # type: ignore[arg-type]
            cryptographic_preseed_proof=_constant(
                item["cryptographic_preseed_proof"],
                False,
                label="preseed cryptographic_preseed_proof",
            ),  # type: ignore[arg-type]
            human_or_external_process_unseen_proof=_constant(
                item["human_or_external_process_unseen_proof"],
                False,
                label="preseed human_or_external_process_unseen_proof",
            ),  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class InstrumentSelection:
    """The sole F2 estimator/trivialization/core selection in v0.1."""

    referent_id: str
    estimator_id: str
    trivialization_id: str
    core_localizer_id: str
    core_graph_mode: CoreGraphMode = CoreGraphMode.INHERIT_FIELD_ESTIMATION_GRAPH

    def __post_init__(self) -> None:
        for name in (
            "referent_id",
            "estimator_id",
            "trivialization_id",
            "core_localizer_id",
        ):
            _slug(getattr(self, name), label=f"instrument.{name}")
        if self.core_graph_mode is not CoreGraphMode.INHERIT_FIELD_ESTIMATION_GRAPH:
            raise QualificationContractError(
                "qualification requires exact inheritance of the "
                "field-estimation graph for core localization"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "referent_id": self.referent_id,
            "estimator_id": self.estimator_id,
            "trivialization_id": self.trivialization_id,
            "core_localizer_id": self.core_localizer_id,
            "core_graph_mode": self.core_graph_mode.value,
        }

    @classmethod
    def from_dict(cls, value: object) -> InstrumentSelection:
        item = _mapping(value, label="instrument")
        expected = {
            "referent_id",
            "estimator_id",
            "trivialization_id",
            "core_localizer_id",
            "core_graph_mode",
        }
        _exact_keys(item, expected, label="instrument")
        return cls(
            referent_id=_slug(item["referent_id"], label="instrument.referent_id"),
            estimator_id=_slug(item["estimator_id"], label="instrument.estimator_id"),
            trivialization_id=_slug(
                item["trivialization_id"],
                label="instrument.trivialization_id",
            ),
            core_localizer_id=_slug(
                item["core_localizer_id"],
                label="instrument.core_localizer_id",
            ),
            core_graph_mode=_enum(
                CoreGraphMode,
                item["core_graph_mode"],
                label="instrument.core_graph_mode",
            ),  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class GeneratorCaseBinding:
    """One source-bound generator case admitted by the closed registry."""

    generator_case_id: str
    core_disposition: CoreDisposition
    loop_disposition: LoopDisposition

    def __post_init__(self) -> None:
        _slug(self.generator_case_id, label="generator case binding ID")
        if not isinstance(self.core_disposition, CoreDisposition):
            raise TypeError("core_disposition must be a CoreDisposition")
        if not isinstance(self.loop_disposition, LoopDisposition):
            raise TypeError("loop_disposition must be a LoopDisposition")
        if (self.core_disposition is CoreDisposition.PREREQUISITE_FAILURE) is not (
            self.loop_disposition is LoopDisposition.PREREQUISITE_FAILURE
        ):
            raise QualificationContractError(
                "a generator case prerequisite failure must apply to both axes"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "generator_case_id": self.generator_case_id,
            "core_disposition": self.core_disposition.value,
            "loop_disposition": self.loop_disposition.value,
        }

    @classmethod
    def from_dict(cls, value: object) -> GeneratorCaseBinding:
        item = _mapping(value, label="generator case binding")
        _exact_keys(
            item,
            {
                "generator_case_id",
                "core_disposition",
                "loop_disposition",
            },
            label="generator case binding",
        )
        return cls(
            generator_case_id=_slug(
                item["generator_case_id"],
                label="generator case binding ID",
            ),
            core_disposition=_enum(
                CoreDisposition,
                item["core_disposition"],
                label="generator case binding core_disposition",
            ),  # type: ignore[arg-type]
            loop_disposition=_enum(
                LoopDisposition,
                item["loop_disposition"],
                label="generator case binding loop_disposition",
            ),  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class ClosedImplementationRegistry:
    """Closed generator/case/instrument universe for one selection protocol."""

    generator_family_id: str
    generator_cases: tuple[GeneratorCaseBinding, ...]
    surrogate_estimator_id: str
    surrogate_trivialization_id: str
    instrument: InstrumentSelection

    def __post_init__(self) -> None:
        family_id = _slug(
            self.generator_family_id,
            label="implementation registry generator_family_id",
        )
        if family_id != CLOSED_CARTESIAN_GENERATOR_FAMILY_ID:
            raise QualificationContractError(
                "implementation registry generator family is not the closed "
                "Cartesian Fourier family"
            )
        if not self.generator_cases:
            raise QualificationContractError(
                "implementation registry generator_cases must not be empty"
            )
        case_ids = tuple(binding.generator_case_id for binding in self.generator_cases)
        _canonical_unique_slugs(
            case_ids,
            label="implementation registry generator case IDs",
        )
        expected_cases = {
            "cartesian-fourier-fixed-null": (
                CoreDisposition.LOCALIZED_CORE,
                LoopDisposition.NULL,
            ),
            "cartesian-fourier-no-core-null": (
                CoreDisposition.NO_CORE,
                LoopDisposition.NULL,
            ),
            "cartesian-fourier-positive": (
                CoreDisposition.LOCALIZED_CORE,
                LoopDisposition.NONZERO,
            ),
            "cartesian-fourier-prerequisite-failure": (
                CoreDisposition.PREREQUISITE_FAILURE,
                LoopDisposition.PREREQUISITE_FAILURE,
            ),
        }
        observed_cases = {
            binding.generator_case_id: (
                binding.core_disposition,
                binding.loop_disposition,
            )
            for binding in self.generator_cases
        }
        if observed_cases != expected_cases:
            raise QualificationContractError(
                "implementation registry generator cases must equal the closed "
                "Cartesian Fourier case universe"
            )
        _constant(
            self.surrogate_estimator_id,
            CLOSED_CARTESIAN_ESTIMATOR_ID,
            label="implementation registry surrogate_estimator_id",
        )
        _constant(
            self.surrogate_trivialization_id,
            CLOSED_CARTESIAN_TRIVIALIZATION_ID,
            label="implementation registry surrogate_trivialization_id",
        )
        if not isinstance(self.instrument, InstrumentSelection):
            raise TypeError("instrument must be an InstrumentSelection")
        expected_instrument = InstrumentSelection(
            referent_id=F2_LOCAL_COVARIANT_SECTION_REFERENT_ID,
            estimator_id=CLOSED_REPRESENTATION_ESTIMATOR_ID,
            trivialization_id=CLOSED_REPRESENTATION_TRIVIALIZATION_ID,
            core_localizer_id=CLOSED_CORE_LOCALIZER_ID,
        )
        if self.instrument != expected_instrument:
            raise QualificationContractError(
                "implementation registry instrument must equal the closed "
                "F2 representation instrument"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "generator_family_id": self.generator_family_id,
            "generator_cases": [binding.to_dict() for binding in self.generator_cases],
            "surrogate_estimator_id": self.surrogate_estimator_id,
            "surrogate_trivialization_id": self.surrogate_trivialization_id,
            "instrument": self.instrument.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: object) -> ClosedImplementationRegistry:
        item = _mapping(value, label="implementation registry")
        _exact_keys(
            item,
            {
                "generator_family_id",
                "generator_cases",
                "surrogate_estimator_id",
                "surrogate_trivialization_id",
                "instrument",
            },
            label="implementation registry",
        )
        return cls(
            generator_family_id=_slug(
                item["generator_family_id"],
                label="implementation registry generator_family_id",
            ),
            generator_cases=tuple(
                GeneratorCaseBinding.from_dict(binding)
                for binding in _sequence(
                    item["generator_cases"],
                    label="implementation registry generator_cases",
                )
            ),
            surrogate_estimator_id=_slug(
                item["surrogate_estimator_id"],
                label="implementation registry surrogate_estimator_id",
            ),
            surrogate_trivialization_id=_slug(
                item["surrogate_trivialization_id"],
                label="implementation registry surrogate_trivialization_id",
            ),
            instrument=InstrumentSelection.from_dict(item["instrument"]),
        )


GraphParameterValue = int | float


@dataclass(frozen=True, slots=True)
class GraphDeclaration:
    """One typed A or B graph declaration."""

    graph_id: str
    family: GraphFamily
    purpose: GraphPurpose
    parameters: tuple[tuple[str, GraphParameterValue], ...]

    def __post_init__(self) -> None:
        _slug(self.graph_id, label="graph_id")
        if not isinstance(self.family, GraphFamily):
            raise TypeError("family must be a GraphFamily")
        if not isinstance(self.purpose, GraphPurpose):
            raise TypeError("purpose must be a GraphPurpose")
        names = tuple(name for name, _value in self.parameters)
        if names != tuple(sorted(names)) or len(set(names)) != len(names):
            raise QualificationContractError(
                "graph parameters must have unique canonical keys"
            )
        expected: dict[GraphFamily, tuple[str, ...]] = {
            GraphFamily.MUTUAL_KNN: ("neighbor_count",),
            GraphFamily.FIXED_RADIUS: ("radius",),
            GraphFamily.SHARED_NEIGHBOR: (
                "minimum_shared_neighbors",
                "neighbor_count",
            ),
        }
        if names != expected[self.family]:
            raise QualificationContractError(
                "graph parameter fields do not match the graph family"
            )
        parameters = dict(self.parameters)
        if self.family is GraphFamily.FIXED_RADIUS:
            _finite_float(
                parameters["radius"],
                label="graph.parameters.radius",
                minimum=0.0,
                minimum_inclusive=False,
            )
            return
        neighbor_count = _plain_int(
            parameters["neighbor_count"],
            label="graph.parameters.neighbor_count",
            minimum=1,
        )
        if self.family is GraphFamily.SHARED_NEIGHBOR:
            minimum_shared = _plain_int(
                parameters["minimum_shared_neighbors"],
                label="graph.parameters.minimum_shared_neighbors",
                minimum=1,
            )
            if minimum_shared > neighbor_count:
                raise QualificationContractError(
                    "minimum_shared_neighbors must not exceed neighbor_count"
                )

    def to_dict(self) -> dict[str, object]:
        return {
            "graph_id": self.graph_id,
            "family": self.family.value,
            "purpose": self.purpose.value,
            "parameters": dict(self.parameters),
        }

    @classmethod
    def from_dict(cls, value: object) -> GraphDeclaration:
        item = _mapping(value, label="graph declaration")
        _exact_keys(
            item,
            {"graph_id", "family", "purpose", "parameters"},
            label="graph declaration",
        )
        family = _enum(GraphFamily, item["family"], label="graph declaration.family")
        purpose = _enum(
            GraphPurpose, item["purpose"], label="graph declaration.purpose"
        )
        parameters = _mapping(item["parameters"], label="graph declaration.parameters")
        parsed_parameters: list[tuple[str, GraphParameterValue]] = []
        for name in sorted(parameters):
            raw = parameters[name]
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                raise QualificationContractError(
                    f"graph parameter {name!r} must be numeric"
                )
            parsed_parameters.append((name, raw))
        return cls(
            graph_id=_slug(item["graph_id"], label="graph declaration.graph_id"),
            family=family,  # type: ignore[arg-type]
            purpose=purpose,  # type: ignore[arg-type]
            parameters=tuple(parsed_parameters),
        )


@dataclass(frozen=True, slots=True)
class GraphAxes:
    """The exact three-family A and B axes."""

    field_estimation: tuple[GraphDeclaration, ...]
    cycle_construction: tuple[GraphDeclaration, ...]

    def __post_init__(self) -> None:
        for label, graphs, purpose in (
            (
                "field_estimation",
                self.field_estimation,
                GraphPurpose.FIELD_ESTIMATION,
            ),
            (
                "cycle_construction",
                self.cycle_construction,
                GraphPurpose.CYCLE_CONSTRUCTION,
            ),
        ):
            if len(graphs) != 3:
                raise QualificationContractError(
                    f"graphs.{label} must contain exactly three families"
                )
            if tuple(graph.family for graph in graphs) != _GRAPH_FAMILY_ORDER:
                raise QualificationContractError(
                    f"graphs.{label} must be in canonical family order"
                )
            if any(graph.purpose is not purpose for graph in graphs):
                raise QualificationContractError(
                    f"graphs.{label} contains the wrong graph purpose"
                )
        identifiers = tuple(
            graph.graph_id
            for graph in (*self.field_estimation, *self.cycle_construction)
        )
        if len(set(identifiers)) != len(identifiers):
            raise QualificationContractError(
                "A and B graph identifiers must be globally unique"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "field_estimation": [graph.to_dict() for graph in self.field_estimation],
            "cycle_construction": [
                graph.to_dict() for graph in self.cycle_construction
            ],
        }

    @classmethod
    def from_dict(cls, value: object) -> GraphAxes:
        item = _mapping(value, label="graphs")
        _exact_keys(item, {"field_estimation", "cycle_construction"}, label="graphs")
        return cls(
            field_estimation=tuple(
                GraphDeclaration.from_dict(entry)
                for entry in _sequence(
                    item["field_estimation"], label="graphs.field_estimation"
                )
            ),
            cycle_construction=tuple(
                GraphDeclaration.from_dict(entry)
                for entry in _sequence(
                    item["cycle_construction"],
                    label="graphs.cycle_construction",
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class DomainDeclaration:
    """Outcome-blind domain-construction and matched-support identities.

    The two digests bind canonical constructor/template declarations shared by
    every selected phantom.  They are deliberately not fingerprints of one
    generated runtime domain, because a protocol may span many seeds and stress
    cells.  Runtime instance fingerprints belong to the result's primary-unit
    summaries.
    """

    domain_id: str
    domain_construction_sha256: str
    support_id: str
    support_construction_sha256: str
    boundary_class_id: str
    refinement_rule_id: str
    max_domain_edges_per_graph_edge: int

    def __post_init__(self) -> None:
        for name in (
            "domain_id",
            "support_id",
            "boundary_class_id",
            "refinement_rule_id",
        ):
            _slug(getattr(self, name), label=f"domain.{name}")
        for name in (
            "domain_construction_sha256",
            "support_construction_sha256",
        ):
            _sha256(getattr(self, name), label=f"domain.{name}")
        _plain_int(
            self.max_domain_edges_per_graph_edge,
            label="domain.max_domain_edges_per_graph_edge",
            minimum=1,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "domain_id": self.domain_id,
            "domain_construction_sha256": self.domain_construction_sha256,
            "support_id": self.support_id,
            "support_construction_sha256": self.support_construction_sha256,
            "boundary_class_id": self.boundary_class_id,
            "refinement_rule_id": self.refinement_rule_id,
            "max_domain_edges_per_graph_edge": (self.max_domain_edges_per_graph_edge),
        }

    @classmethod
    def from_dict(cls, value: object) -> DomainDeclaration:
        item = _mapping(value, label="domain")
        expected = {
            "domain_id",
            "domain_construction_sha256",
            "support_id",
            "support_construction_sha256",
            "boundary_class_id",
            "refinement_rule_id",
            "max_domain_edges_per_graph_edge",
        }
        _exact_keys(item, expected, label="domain")
        return cls(
            domain_id=_slug(item["domain_id"], label="domain.domain_id"),
            domain_construction_sha256=_sha256(
                item["domain_construction_sha256"],
                label="domain.domain_construction_sha256",
            ),
            support_id=_slug(item["support_id"], label="domain.support_id"),
            support_construction_sha256=_sha256(
                item["support_construction_sha256"],
                label="domain.support_construction_sha256",
            ),
            boundary_class_id=_slug(
                item["boundary_class_id"], label="domain.boundary_class_id"
            ),
            refinement_rule_id=_slug(
                item["refinement_rule_id"],
                label="domain.refinement_rule_id",
            ),
            max_domain_edges_per_graph_edge=_plain_int(
                item["max_domain_edges_per_graph_edge"],
                label="domain.max_domain_edges_per_graph_edge",
                minimum=1,
            ),
        )


@dataclass(frozen=True, slots=True)
class ControlDeclaration:
    """One joint core/loop control without collapsing the two questions."""

    control_id: str
    generator_case_id: str
    core_disposition: CoreDisposition
    loop_disposition: LoopDisposition
    field_sensitivity_sentinel: bool = False

    def __post_init__(self) -> None:
        _slug(self.control_id, label="control_id")
        _slug(self.generator_case_id, label="generator_case_id")
        if not isinstance(self.core_disposition, CoreDisposition):
            raise TypeError("core_disposition must be a CoreDisposition")
        if not isinstance(self.loop_disposition, LoopDisposition):
            raise TypeError("loop_disposition must be a LoopDisposition")
        if type(self.field_sensitivity_sentinel) is not bool:
            raise TypeError("field_sensitivity_sentinel must be a bool")
        if (self.core_disposition is CoreDisposition.PREREQUISITE_FAILURE) is not (
            self.loop_disposition is LoopDisposition.PREREQUISITE_FAILURE
        ):
            raise QualificationContractError(
                "prerequisite failure must be declared on both independent axes"
            )
        if self.field_sensitivity_sentinel and (
            self.core_disposition is not CoreDisposition.LOCALIZED_CORE
            or self.loop_disposition is not LoopDisposition.NONZERO
        ):
            raise QualificationContractError(
                "the field-sensitivity sentinel must be the "
                "localized-core/nonzero positive control"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "control_id": self.control_id,
            "generator_case_id": self.generator_case_id,
            "core_disposition": self.core_disposition.value,
            "loop_disposition": self.loop_disposition.value,
            "field_sensitivity_sentinel": self.field_sensitivity_sentinel,
        }

    @classmethod
    def from_dict(cls, value: object) -> ControlDeclaration:
        item = _mapping(value, label="control declaration")
        _exact_keys(
            item,
            {
                "control_id",
                "generator_case_id",
                "core_disposition",
                "loop_disposition",
                "field_sensitivity_sentinel",
            },
            label="control declaration",
        )
        return cls(
            control_id=_slug(item["control_id"], label="control_id"),
            generator_case_id=_slug(
                item["generator_case_id"],
                label="generator_case_id",
            ),
            core_disposition=_enum(
                CoreDisposition,
                item["core_disposition"],
                label="core_disposition",
            ),  # type: ignore[arg-type]
            loop_disposition=_enum(
                LoopDisposition,
                item["loop_disposition"],
                label="loop_disposition",
            ),  # type: ignore[arg-type]
            field_sensitivity_sentinel=_plain_bool(
                item["field_sensitivity_sentinel"],
                label="field_sensitivity_sentinel",
            ),
        )


@dataclass(frozen=True, slots=True)
class D2CoreConfounderDeclaration:
    """One exact seed-free D2-only false-core confounder."""

    confounder_id: str
    construction_id: str
    expected_attempt_status: AttemptStatus
    expected_prediction_class: CorePredictionClass
    expected_reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        _slug(self.confounder_id, label="D2 confounder_id")
        _slug(self.construction_id, label="D2 confounder construction_id")
        if not isinstance(self.expected_attempt_status, AttemptStatus):
            raise TypeError("expected_attempt_status must be an AttemptStatus")
        if not isinstance(self.expected_prediction_class, CorePredictionClass):
            raise TypeError("expected_prediction_class must be a CorePredictionClass")
        _canonical_unique_slugs(
            self.expected_reason_codes,
            label=f"D2 confounder {self.confounder_id} expected reasons",
            nonempty=False,
        )
        expected_behavior = (
            self.expected_attempt_status,
            self.expected_prediction_class,
            bool(self.expected_reason_codes),
        )
        if expected_behavior not in {
            (
                AttemptStatus.EVALUABLE,
                CorePredictionClass.NO_CORE,
                False,
            ),
            (
                AttemptStatus.INSUFFICIENT,
                CorePredictionClass.ABSTAIN,
                True,
            ),
        }:
            raise QualificationContractError(
                "D2 false-core confounders must contract either evaluable "
                "NO_CORE or an explicit truth-blind abstention reason"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "confounder_id": self.confounder_id,
            "construction_id": self.construction_id,
            "expected_attempt_status": self.expected_attempt_status.value,
            "expected_prediction_class": self.expected_prediction_class.value,
            "expected_reason_codes": list(self.expected_reason_codes),
        }

    @classmethod
    def from_dict(cls, value: object) -> D2CoreConfounderDeclaration:
        item = _mapping(value, label="D2 core confounder declaration")
        _exact_keys(
            item,
            {
                "confounder_id",
                "construction_id",
                "expected_attempt_status",
                "expected_prediction_class",
                "expected_reason_codes",
            },
            label="D2 core confounder declaration",
        )
        return cls(
            confounder_id=_slug(item["confounder_id"], label="D2 confounder_id"),
            construction_id=_slug(
                item["construction_id"],
                label="D2 confounder construction_id",
            ),
            expected_attempt_status=_enum(
                AttemptStatus,
                item["expected_attempt_status"],
                label="D2 confounder expected_attempt_status",
            ),  # type: ignore[arg-type]
            expected_prediction_class=_enum(
                CorePredictionClass,
                item["expected_prediction_class"],
                label="D2 confounder expected_prediction_class",
            ),  # type: ignore[arg-type]
            expected_reason_codes=tuple(
                _slug(reason, label="D2 confounder expected reason")
                for reason in _sequence(
                    item["expected_reason_codes"],
                    label="D2 confounder expected_reason_codes",
                )
            ),
        )


D2_CORE_CONFOUNDER_REGISTRY = (
    D2CoreConfounderDeclaration(
        confounder_id=D2_IDENTIFIABILITY_LOSS_DECOY_CONFOUNDER_ID,
        construction_id=D2_IDENTIFIABILITY_LOSS_DECOY_CONSTRUCTION_ID,
        expected_attempt_status=AttemptStatus.EVALUABLE,
        expected_prediction_class=CorePredictionClass.NO_CORE,
        expected_reason_codes=(),
    ),
    D2CoreConfounderDeclaration(
        confounder_id=D2_MISSING_CANDIDATE_SUPPORT_CONFOUNDER_ID,
        construction_id=D2_MISSING_CANDIDATE_SUPPORT_CONSTRUCTION_ID,
        expected_attempt_status=AttemptStatus.INSUFFICIENT,
        expected_prediction_class=CorePredictionClass.ABSTAIN,
        expected_reason_codes=("candidate_measurement_support_below_minimum",),
    ),
)


@dataclass(frozen=True, slots=True)
class StressAxis:
    axis_id: str
    levels: tuple[str, ...]

    def __post_init__(self) -> None:
        _slug(self.axis_id, label="stress axis_id")
        _canonical_unique_slugs(self.levels, label=f"stress axis {self.axis_id} levels")

    def to_dict(self) -> dict[str, object]:
        return {"axis_id": self.axis_id, "levels": list(self.levels)}

    @classmethod
    def from_dict(cls, value: object) -> StressAxis:
        item = _mapping(value, label="stress axis")
        _exact_keys(item, {"axis_id", "levels"}, label="stress axis")
        return cls(
            axis_id=_slug(item["axis_id"], label="stress axis_id"),
            levels=tuple(
                _slug(level, label="stress level")
                for level in _sequence(item["levels"], label="stress levels")
            ),
        )


@dataclass(frozen=True, slots=True)
class NumericStressLevel:
    """One exact numeric value attached to a declared stress level."""

    level: str
    value: float

    def __post_init__(self) -> None:
        _slug(self.level, label="numeric stress level")
        object.__setattr__(
            self,
            "value",
            _finite_float(
                self.value,
                label=f"numeric stress value {self.level}",
                minimum=0.0,
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {"level": self.level, "value": self.value}

    @classmethod
    def from_dict(cls, value: object) -> NumericStressLevel:
        item = _mapping(value, label="numeric stress level")
        _exact_keys(item, {"level", "value"}, label="numeric stress level")
        return cls(
            level=_slug(item["level"], label="numeric stress level"),
            value=_finite_float(
                item["value"],
                label="numeric stress value",
                minimum=0.0,
            ),
        )


@dataclass(frozen=True, slots=True)
class BoundaryTemplate:
    """One exact rectangular face support on the fixed Cartesian grid."""

    level: str
    x_min: int
    y_min: int
    x_max: int
    y_max: int

    def __post_init__(self) -> None:
        _slug(self.level, label="boundary template level")
        for name in ("x_min", "y_min"):
            _plain_int(
                getattr(self, name),
                label=f"boundary template {name}",
                minimum=0,
            )
        for name in ("x_max", "y_max"):
            _plain_int(
                getattr(self, name),
                label=f"boundary template {name}",
                minimum=1,
            )
        if not (self.x_min < self.x_max and self.y_min < self.y_max):
            raise QualificationContractError(
                "boundary template must contain at least one grid cell"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "level": self.level,
            "x_min": self.x_min,
            "y_min": self.y_min,
            "x_max": self.x_max,
            "y_max": self.y_max,
        }

    @classmethod
    def from_dict(cls, value: object) -> BoundaryTemplate:
        item = _mapping(value, label="boundary template")
        expected = {"level", "x_min", "y_min", "x_max", "y_max"}
        _exact_keys(item, expected, label="boundary template")
        return cls(
            level=_slug(item["level"], label="boundary template level"),
            x_min=_plain_int(
                item["x_min"],
                label="boundary template x_min",
            ),
            y_min=_plain_int(
                item["y_min"],
                label="boundary template y_min",
            ),
            x_max=_plain_int(
                item["x_max"],
                label="boundary template x_max",
                minimum=1,
            ),
            y_max=_plain_int(
                item["y_max"],
                label="boundary template y_max",
                minimum=1,
            ),
        )


@dataclass(frozen=True, slots=True)
class CartesianSelectionSubstrate:
    """Exact numeric construction interpreted by the calibration runner."""

    generator_family_id: str
    grid_side: int
    ambient_dimension: int
    samples_per_split: int
    baseline: float
    second_harmonic_scale: float
    structured_observation_perturbation_axis_id: str
    structured_observation_perturbation_levels: tuple[NumericStressLevel, ...]
    state_geometry_warp_axis_id: str
    state_geometry_warp_levels: tuple[NumericStressLevel, ...]
    boundary_axis_id: str
    primary_boundaries: tuple[BoundaryTemplate, ...]
    offcore_boundary: BoundaryTemplate

    def __post_init__(self) -> None:
        _slug(self.generator_family_id, label="cartesian generator_family_id")
        side = _plain_int(
            self.grid_side,
            label="cartesian grid_side",
            minimum=5,
        )
        if side % 2 == 0:
            raise QualificationContractError("cartesian grid_side must be odd")
        _plain_int(
            self.ambient_dimension,
            label="cartesian ambient_dimension",
            minimum=8,
        )
        samples = _plain_int(
            self.samples_per_split,
            label="cartesian samples_per_split",
            minimum=8,
        )
        if samples % 4:
            raise QualificationContractError(
                "cartesian samples_per_split must be divisible by four"
            )
        for name in ("baseline", "second_harmonic_scale"):
            object.__setattr__(
                self,
                name,
                _finite_float(
                    getattr(self, name),
                    label=f"cartesian {name}",
                    minimum=0.0,
                    minimum_inclusive=False,
                ),
            )
        for name in (
            "structured_observation_perturbation_axis_id",
            "state_geometry_warp_axis_id",
            "boundary_axis_id",
        ):
            _slug(getattr(self, name), label=f"cartesian {name}")
        if (
            self.boundary_axis_id,
            self.state_geometry_warp_axis_id,
            self.structured_observation_perturbation_axis_id,
        ) != (
            BOUNDARY_AXIS_ID,
            STATE_GEOMETRY_WARP_AXIS_ID,
            STRUCTURED_OBSERVATION_PERTURBATION_AXIS_ID,
        ):
            raise QualificationContractError(
                "cartesian stress axis IDs must be exactly boundary, "
                "state-geometry-warp, and structured-observation-perturbation"
            )
        for label, values in (
            (
                "structured_observation_perturbation_levels",
                self.structured_observation_perturbation_levels,
            ),
            ("state_geometry_warp_levels", self.state_geometry_warp_levels),
        ):
            levels = tuple(item.level for item in values)
            _canonical_unique_slugs(levels, label=f"cartesian {label}")
            numeric_values = tuple(item.value for item in values)
            if len(set(numeric_values)) != len(numeric_values):
                raise QualificationContractError(
                    f"cartesian {label} must have distinct numeric values"
                )
        boundary_levels = tuple(item.level for item in self.primary_boundaries)
        _canonical_unique_slugs(
            boundary_levels,
            label="cartesian primary boundary levels",
        )
        if self.offcore_boundary.level in set(boundary_levels):
            raise QualificationContractError(
                "offcore boundary level must be distinct from primary levels"
            )
        primary_geometries = tuple(
            (item.x_min, item.y_min, item.x_max, item.y_max)
            for item in self.primary_boundaries
        )
        if len(set(primary_geometries)) != len(primary_geometries):
            raise QualificationContractError(
                "cartesian primary boundaries must have distinct geometries"
            )
        offcore_geometry = (
            self.offcore_boundary.x_min,
            self.offcore_boundary.y_min,
            self.offcore_boundary.x_max,
            self.offcore_boundary.y_max,
        )
        if offcore_geometry in set(primary_geometries):
            raise QualificationContractError(
                "offcore boundary geometry must differ from every primary boundary"
            )
        for template in (*self.primary_boundaries, self.offcore_boundary):
            if template.x_max >= side or template.y_max >= side:
                raise QualificationContractError(
                    "boundary template lies outside the fixed grid"
                )

    def to_dict(self) -> dict[str, object]:
        return {
            "generator_family_id": self.generator_family_id,
            "grid_side": self.grid_side,
            "ambient_dimension": self.ambient_dimension,
            "samples_per_split": self.samples_per_split,
            "baseline": self.baseline,
            "second_harmonic_scale": self.second_harmonic_scale,
            "structured_observation_perturbation_axis_id": (
                self.structured_observation_perturbation_axis_id
            ),
            "structured_observation_perturbation_levels": [
                item.to_dict()
                for item in self.structured_observation_perturbation_levels
            ],
            "state_geometry_warp_axis_id": self.state_geometry_warp_axis_id,
            "state_geometry_warp_levels": [
                item.to_dict() for item in self.state_geometry_warp_levels
            ],
            "boundary_axis_id": self.boundary_axis_id,
            "primary_boundaries": [item.to_dict() for item in self.primary_boundaries],
            "offcore_boundary": self.offcore_boundary.to_dict(),
            "seed_source": "selection.seeds",
        }

    @classmethod
    def from_dict(cls, value: object) -> CartesianSelectionSubstrate:
        item = _mapping(value, label="cartesian substrate")
        expected = {
            "generator_family_id",
            "grid_side",
            "ambient_dimension",
            "samples_per_split",
            "baseline",
            "second_harmonic_scale",
            "structured_observation_perturbation_axis_id",
            "structured_observation_perturbation_levels",
            "state_geometry_warp_axis_id",
            "state_geometry_warp_levels",
            "boundary_axis_id",
            "primary_boundaries",
            "offcore_boundary",
            "seed_source",
        }
        _exact_keys(item, expected, label="cartesian substrate")
        _constant(
            item["seed_source"],
            "selection.seeds",
            label="cartesian seed_source",
        )
        return cls(
            generator_family_id=_slug(
                item["generator_family_id"],
                label="cartesian generator_family_id",
            ),
            grid_side=_plain_int(
                item["grid_side"],
                label="cartesian grid_side",
                minimum=5,
            ),
            ambient_dimension=_plain_int(
                item["ambient_dimension"],
                label="cartesian ambient_dimension",
                minimum=8,
            ),
            samples_per_split=_plain_int(
                item["samples_per_split"],
                label="cartesian samples_per_split",
                minimum=8,
            ),
            baseline=_finite_float(
                item["baseline"],
                label="cartesian baseline",
                minimum=0.0,
                minimum_inclusive=False,
            ),
            second_harmonic_scale=_finite_float(
                item["second_harmonic_scale"],
                label="cartesian second_harmonic_scale",
                minimum=0.0,
                minimum_inclusive=False,
            ),
            structured_observation_perturbation_axis_id=_slug(
                item["structured_observation_perturbation_axis_id"],
                label=("cartesian structured_observation_perturbation_axis_id"),
            ),
            structured_observation_perturbation_levels=tuple(
                NumericStressLevel.from_dict(entry)
                for entry in _sequence(
                    item["structured_observation_perturbation_levels"],
                    label=("cartesian structured_observation_perturbation_levels"),
                )
            ),
            state_geometry_warp_axis_id=_slug(
                item["state_geometry_warp_axis_id"],
                label="cartesian state_geometry_warp_axis_id",
            ),
            state_geometry_warp_levels=tuple(
                NumericStressLevel.from_dict(entry)
                for entry in _sequence(
                    item["state_geometry_warp_levels"],
                    label="cartesian state_geometry_warp_levels",
                )
            ),
            boundary_axis_id=_slug(
                item["boundary_axis_id"],
                label="cartesian boundary_axis_id",
            ),
            primary_boundaries=tuple(
                BoundaryTemplate.from_dict(entry)
                for entry in _sequence(
                    item["primary_boundaries"],
                    label="cartesian primary_boundaries",
                )
            ),
            offcore_boundary=BoundaryTemplate.from_dict(item["offcore_boundary"]),
        )


@dataclass(frozen=True, slots=True)
class SelectionDesign:
    """Exact calibration-selection seeds, controls, and stress axes."""

    seeds: tuple[int, ...]
    controls: tuple[ControlDeclaration, ...]
    stress_axes: tuple[StressAxis, ...]

    def __post_init__(self) -> None:
        if not self.seeds:
            raise QualificationContractError("selection.seeds must not be empty")
        for index, seed in enumerate(self.seeds):
            _plain_int(seed, label=f"selection.seeds[{index}]", minimum=0)
            if seed > MAX_SIGNED_INT64:
                raise QualificationContractError(
                    f"selection.seeds[{index}] must fit in signed int64"
                )
        if len(set(self.seeds)) != len(self.seeds):
            raise QualificationContractError("selection.seeds must be unique")
        if self.seeds != tuple(sorted(self.seeds)):
            raise QualificationContractError(
                "selection.seeds must be in canonical order"
            )
        control_ids = tuple(control.control_id for control in self.controls)
        _canonical_unique_slugs(control_ids, label="selection control IDs")
        generator_case_ids = tuple(
            control.generator_case_id for control in self.controls
        )
        if len(set(generator_case_ids)) != len(generator_case_ids):
            raise QualificationContractError(
                "selection controls must bind unique generator cases"
            )
        joint_controls = {
            (control.core_disposition, control.loop_disposition)
            for control in self.controls
        }
        required_joint_controls = {
            (CoreDisposition.LOCALIZED_CORE, LoopDisposition.NONZERO),
            (CoreDisposition.LOCALIZED_CORE, LoopDisposition.NULL),
            (CoreDisposition.NO_CORE, LoopDisposition.NULL),
            (
                CoreDisposition.PREREQUISITE_FAILURE,
                LoopDisposition.PREREQUISITE_FAILURE,
            ),
        }
        if not required_joint_controls <= joint_controls:
            raise QualificationContractError(
                "selection.controls must include nonzero-with-core, "
                "null-with-core, null-without-core, and prerequisite-failure "
                "matched controls"
            )
        sentinels = tuple(
            control for control in self.controls if control.field_sensitivity_sentinel
        )
        if len(sentinels) != 1:
            raise QualificationContractError(
                "selection.controls must designate exactly one "
                "field-sensitivity sentinel"
            )
        axis_ids = tuple(axis.axis_id for axis in self.stress_axes)
        _canonical_unique_slugs(axis_ids, label="selection stress axis IDs")
        primary_unit_count = len(self.seeds)
        for factor in (
            len(self.controls),
            *(len(axis.levels) for axis in self.stress_axes),
        ):
            if (
                factor <= 0
                or primary_unit_count > MAX_QUALIFICATION_PRIMARY_UNITS // factor
            ):
                raise QualificationContractError(
                    "selection Cartesian product exceeds the fixed primary-unit cap"
                )
            primary_unit_count *= factor

    def to_dict(self) -> dict[str, object]:
        return {
            "seeds": list(self.seeds),
            "controls": [control.to_dict() for control in self.controls],
            "stress_axes": [axis.to_dict() for axis in self.stress_axes],
        }

    @classmethod
    def from_dict(cls, value: object) -> SelectionDesign:
        item = _mapping(value, label="selection")
        _exact_keys(item, {"seeds", "controls", "stress_axes"}, label="selection")
        return cls(
            seeds=tuple(
                _plain_int(seed, label="selection seed", minimum=0)
                for seed in _sequence(item["seeds"], label="selection.seeds")
            ),
            controls=tuple(
                ControlDeclaration.from_dict(control)
                for control in _sequence(item["controls"], label="selection.controls")
            ),
            stress_axes=tuple(
                StressAxis.from_dict(axis)
                for axis in _sequence(
                    item["stress_axes"], label="selection.stress_axes"
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class EvaluationDesign:
    """Serialized repeated-measures semantics for the closed selection grid."""

    declared_seed_block_count: int
    matched_control_count: int
    paired_stress_variant_count_per_seed_control: int
    execution_variant_count: int
    d2_unique_scientific_input_unit_count: int
    loop_execution_variant_count: int
    paired_repeated_measure_block_unit: str = "selection-seed-block"
    controls_are_matched: bool = True
    stress_variants_are_paired_repeated_measures: bool = True
    boundary_variants_are_d2_repeated_measures: bool = True
    execution_variants_are_independent_replicates: bool = False
    seed_block_independence_proved: bool = False
    inferential_sample_size_claimed: bool = False

    def __post_init__(self) -> None:
        for name in (
            "declared_seed_block_count",
            "matched_control_count",
            "paired_stress_variant_count_per_seed_control",
            "execution_variant_count",
            "d2_unique_scientific_input_unit_count",
            "loop_execution_variant_count",
        ):
            _plain_int(
                getattr(self, name),
                label=f"evaluation_design.{name}",
                minimum=1,
            )
        _constant(
            self.paired_repeated_measure_block_unit,
            "selection-seed-block",
            label="evaluation_design.paired_repeated_measure_block_unit",
        )
        for name in (
            "controls_are_matched",
            "stress_variants_are_paired_repeated_measures",
            "boundary_variants_are_d2_repeated_measures",
        ):
            _constant(
                getattr(self, name),
                True,
                label=f"evaluation_design.{name}",
            )
        for name in (
            "execution_variants_are_independent_replicates",
            "seed_block_independence_proved",
            "inferential_sample_size_claimed",
        ):
            _constant(
                getattr(self, name),
                False,
                label=f"evaluation_design.{name}",
            )
        expected_execution_count = (
            self.declared_seed_block_count
            * self.matched_control_count
            * self.paired_stress_variant_count_per_seed_control
        )
        if self.execution_variant_count != expected_execution_count:
            raise QualificationContractError(
                "evaluation_design execution count differs from seed blocks × "
                "matched controls × paired stress variants"
            )
        if self.loop_execution_variant_count != self.execution_variant_count:
            raise QualificationContractError(
                "evaluation_design loop count must retain every execution variant"
            )
        if (
            self.d2_unique_scientific_input_unit_count > self.execution_variant_count
            or self.execution_variant_count % self.d2_unique_scientific_input_unit_count
        ):
            raise QualificationContractError(
                "evaluation_design D2 scientific units must exactly divide the "
                "execution variants"
            )

    @classmethod
    def derive(
        cls,
        *,
        selection: SelectionDesign,
        boundary_axis_id: str,
    ) -> EvaluationDesign:
        stress_variant_count = math.prod(
            len(axis.levels) for axis in selection.stress_axes
        )
        boundary_axes = tuple(
            axis for axis in selection.stress_axes if axis.axis_id == boundary_axis_id
        )
        if len(boundary_axes) != 1:
            raise QualificationContractError(
                "evaluation_design requires exactly one declared boundary axis"
            )
        boundary_level_count = len(boundary_axes[0].levels)
        execution_count = (
            len(selection.seeds) * len(selection.controls) * stress_variant_count
        )
        return cls(
            declared_seed_block_count=len(selection.seeds),
            matched_control_count=len(selection.controls),
            paired_stress_variant_count_per_seed_control=stress_variant_count,
            execution_variant_count=execution_count,
            d2_unique_scientific_input_unit_count=(
                execution_count // boundary_level_count
            ),
            loop_execution_variant_count=execution_count,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "declared_seed_block_count": self.declared_seed_block_count,
            "matched_control_count": self.matched_control_count,
            "paired_stress_variant_count_per_seed_control": (
                self.paired_stress_variant_count_per_seed_control
            ),
            "execution_variant_count": self.execution_variant_count,
            "d2_unique_scientific_input_unit_count": (
                self.d2_unique_scientific_input_unit_count
            ),
            "loop_execution_variant_count": self.loop_execution_variant_count,
            "paired_repeated_measure_block_unit": (
                self.paired_repeated_measure_block_unit
            ),
            "controls_are_matched": self.controls_are_matched,
            "stress_variants_are_paired_repeated_measures": (
                self.stress_variants_are_paired_repeated_measures
            ),
            "boundary_variants_are_d2_repeated_measures": (
                self.boundary_variants_are_d2_repeated_measures
            ),
            "execution_variants_are_independent_replicates": (
                self.execution_variants_are_independent_replicates
            ),
            "seed_block_independence_proved": (self.seed_block_independence_proved),
            "inferential_sample_size_claimed": self.inferential_sample_size_claimed,
        }

    @classmethod
    def from_dict(cls, value: object) -> EvaluationDesign:
        item = _mapping(value, label="evaluation_design")
        expected = {
            "declared_seed_block_count",
            "matched_control_count",
            "paired_stress_variant_count_per_seed_control",
            "execution_variant_count",
            "d2_unique_scientific_input_unit_count",
            "loop_execution_variant_count",
            "paired_repeated_measure_block_unit",
            "controls_are_matched",
            "stress_variants_are_paired_repeated_measures",
            "boundary_variants_are_d2_repeated_measures",
            "execution_variants_are_independent_replicates",
            "seed_block_independence_proved",
            "inferential_sample_size_claimed",
        }
        _exact_keys(item, expected, label="evaluation_design")
        return cls(
            declared_seed_block_count=_plain_int(
                item["declared_seed_block_count"],
                label="evaluation_design.declared_seed_block_count",
                minimum=1,
            ),
            matched_control_count=_plain_int(
                item["matched_control_count"],
                label="evaluation_design.matched_control_count",
                minimum=1,
            ),
            paired_stress_variant_count_per_seed_control=_plain_int(
                item["paired_stress_variant_count_per_seed_control"],
                label=(
                    "evaluation_design.paired_stress_variant_count_per_seed_control"
                ),
                minimum=1,
            ),
            execution_variant_count=_plain_int(
                item["execution_variant_count"],
                label="evaluation_design.execution_variant_count",
                minimum=1,
            ),
            d2_unique_scientific_input_unit_count=_plain_int(
                item["d2_unique_scientific_input_unit_count"],
                label="evaluation_design.d2_unique_scientific_input_unit_count",
                minimum=1,
            ),
            loop_execution_variant_count=_plain_int(
                item["loop_execution_variant_count"],
                label="evaluation_design.loop_execution_variant_count",
                minimum=1,
            ),
            paired_repeated_measure_block_unit=_constant(
                item["paired_repeated_measure_block_unit"],
                "selection-seed-block",
                label="evaluation_design.paired_repeated_measure_block_unit",
            ),  # type: ignore[arg-type]
            controls_are_matched=_constant(
                item["controls_are_matched"],
                True,
                label="evaluation_design.controls_are_matched",
            ),  # type: ignore[arg-type]
            stress_variants_are_paired_repeated_measures=_constant(
                item["stress_variants_are_paired_repeated_measures"],
                True,
                label=(
                    "evaluation_design.stress_variants_are_paired_repeated_measures"
                ),
            ),  # type: ignore[arg-type]
            boundary_variants_are_d2_repeated_measures=_constant(
                item["boundary_variants_are_d2_repeated_measures"],
                True,
                label=("evaluation_design.boundary_variants_are_d2_repeated_measures"),
            ),  # type: ignore[arg-type]
            execution_variants_are_independent_replicates=_constant(
                item["execution_variants_are_independent_replicates"],
                False,
                label=(
                    "evaluation_design.execution_variants_are_independent_replicates"
                ),
            ),  # type: ignore[arg-type]
            seed_block_independence_proved=_constant(
                item["seed_block_independence_proved"],
                False,
                label="evaluation_design.seed_block_independence_proved",
            ),  # type: ignore[arg-type]
            inferential_sample_size_claimed=_constant(
                item["inferential_sample_size_claimed"],
                False,
                label="evaluation_design.inferential_sample_size_claimed",
            ),  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class Thresholds:
    """Frozen numerical floors and tolerances used by D1--D5."""

    d1_numeric_tolerance: float
    d1_cartesian_direction_cosine_floor: float
    d1_representation_phase_coherence_floor: float
    core_amplitude_ceiling: float
    identifiability_floor: float
    coherence_floor: float
    minimum_support_count: int
    max_localized_core_fraction: float
    minimum_core_contrast_ratio: float
    branch_margin_rad: float
    loop_nonzero_floor_cycles: float
    loop_oracle_tolerance_cycles: float
    graph_total_tolerance_cycles: float
    core_candidate_difference_tolerance_rows: int
    minimum_representative_content_variants: int
    minimum_field_output_effect_size: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "d1_numeric_tolerance",
            _finite_float(
                self.d1_numeric_tolerance,
                label="thresholds.d1_numeric_tolerance",
                minimum=0.0,
                maximum=MAX_D1_NUMERIC_TOLERANCE,
                minimum_inclusive=False,
            ),
        )
        for name in (
            "d1_cartesian_direction_cosine_floor",
            "d1_representation_phase_coherence_floor",
        ):
            object.__setattr__(
                self,
                name,
                _finite_float(
                    getattr(self, name),
                    label=f"thresholds.{name}",
                    minimum=MIN_D1_COSINE_FLOOR,
                    maximum=1.0,
                ),
            )
        object.__setattr__(
            self,
            "core_amplitude_ceiling",
            _finite_float(
                self.core_amplitude_ceiling,
                label="thresholds.core_amplitude_ceiling",
                minimum=0.0,
                minimum_inclusive=False,
            ),
        )
        for name, minimum in (("identifiability_floor", MIN_IDENTIFIABILITY_FLOOR),):
            object.__setattr__(
                self,
                name,
                _finite_float(
                    getattr(self, name),
                    label=f"thresholds.{name}",
                    minimum=minimum,
                ),
            )
        object.__setattr__(
            self,
            "coherence_floor",
            _finite_float(
                self.coherence_floor,
                label="thresholds.coherence_floor",
                minimum=MIN_COHERENCE_FLOOR,
                maximum=1.0,
                maximum_inclusive=False,
            ),
        )
        _plain_int(
            self.minimum_support_count,
            label="thresholds.minimum_support_count",
            minimum=1,
        )
        object.__setattr__(
            self,
            "max_localized_core_fraction",
            _finite_float(
                self.max_localized_core_fraction,
                label="thresholds.max_localized_core_fraction",
                minimum=0.0,
                maximum=1.0,
                minimum_inclusive=False,
                maximum_inclusive=False,
            ),
        )
        object.__setattr__(
            self,
            "minimum_core_contrast_ratio",
            _finite_float(
                self.minimum_core_contrast_ratio,
                label="thresholds.minimum_core_contrast_ratio",
                minimum=1.0,
                minimum_inclusive=False,
            ),
        )
        object.__setattr__(
            self,
            "branch_margin_rad",
            _finite_float(
                self.branch_margin_rad,
                label="thresholds.branch_margin_rad",
                minimum=MIN_BRANCH_MARGIN_RAD,
                maximum=math.pi,
                maximum_inclusive=False,
            ),
        )
        object.__setattr__(
            self,
            "loop_nonzero_floor_cycles",
            _finite_float(
                self.loop_nonzero_floor_cycles,
                label="thresholds.loop_nonzero_floor_cycles",
                minimum=0.0,
                maximum=1.0,
                minimum_inclusive=False,
                maximum_inclusive=False,
            ),
        )
        for name in (
            "loop_oracle_tolerance_cycles",
            "graph_total_tolerance_cycles",
        ):
            maximum = (
                MAX_LOOP_ORACLE_TOLERANCE_CYCLES
                if name == "loop_oracle_tolerance_cycles"
                else MAX_GRAPH_TOTAL_TOLERANCE_CYCLES
            )
            object.__setattr__(
                self,
                name,
                _finite_float(
                    getattr(self, name),
                    label=f"thresholds.{name}",
                    minimum=0.0,
                    maximum=maximum,
                ),
            )
        if self.loop_nonzero_floor_cycles <= self.loop_oracle_tolerance_cycles:
            raise QualificationContractError(
                "loop_nonzero_floor_cycles must exceed loop_oracle_tolerance_cycles"
            )
        _plain_int(
            self.core_candidate_difference_tolerance_rows,
            label="thresholds.core_candidate_difference_tolerance_rows",
            minimum=0,
        )
        _plain_int(
            self.minimum_representative_content_variants,
            label="thresholds.minimum_representative_content_variants",
            minimum=2,
        )
        object.__setattr__(
            self,
            "minimum_field_output_effect_size",
            _finite_float(
                self.minimum_field_output_effect_size,
                label="thresholds.minimum_field_output_effect_size",
                minimum=MIN_FIELD_OUTPUT_EFFECT_SIZE,
                maximum=1.0,
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "d1_numeric_tolerance": self.d1_numeric_tolerance,
            "d1_cartesian_direction_cosine_floor": (
                self.d1_cartesian_direction_cosine_floor
            ),
            "d1_representation_phase_coherence_floor": (
                self.d1_representation_phase_coherence_floor
            ),
            "core_amplitude_ceiling": self.core_amplitude_ceiling,
            "identifiability_floor": self.identifiability_floor,
            "coherence_floor": self.coherence_floor,
            "minimum_support_count": self.minimum_support_count,
            "max_localized_core_fraction": (self.max_localized_core_fraction),
            "minimum_core_contrast_ratio": (self.minimum_core_contrast_ratio),
            "branch_margin_rad": self.branch_margin_rad,
            "loop_nonzero_floor_cycles": self.loop_nonzero_floor_cycles,
            "loop_oracle_tolerance_cycles": self.loop_oracle_tolerance_cycles,
            "graph_total_tolerance_cycles": (self.graph_total_tolerance_cycles),
            "core_candidate_difference_tolerance_rows": (
                self.core_candidate_difference_tolerance_rows
            ),
            "minimum_representative_content_variants": (
                self.minimum_representative_content_variants
            ),
            "minimum_field_output_effect_size": (self.minimum_field_output_effect_size),
        }

    @classmethod
    def from_dict(cls, value: object) -> Thresholds:
        item = _mapping(value, label="thresholds")
        expected = {
            "d1_numeric_tolerance",
            "d1_cartesian_direction_cosine_floor",
            "d1_representation_phase_coherence_floor",
            "core_amplitude_ceiling",
            "identifiability_floor",
            "coherence_floor",
            "minimum_support_count",
            "max_localized_core_fraction",
            "minimum_core_contrast_ratio",
            "branch_margin_rad",
            "loop_nonzero_floor_cycles",
            "loop_oracle_tolerance_cycles",
            "graph_total_tolerance_cycles",
            "core_candidate_difference_tolerance_rows",
            "minimum_representative_content_variants",
            "minimum_field_output_effect_size",
        }
        _exact_keys(item, expected, label="thresholds")
        return cls(
            d1_numeric_tolerance=_finite_float(
                item["d1_numeric_tolerance"],
                label="thresholds.d1_numeric_tolerance",
                minimum=0.0,
                maximum=MAX_D1_NUMERIC_TOLERANCE,
                minimum_inclusive=False,
            ),
            d1_cartesian_direction_cosine_floor=_finite_float(
                item["d1_cartesian_direction_cosine_floor"],
                label="thresholds.d1_cartesian_direction_cosine_floor",
                minimum=MIN_D1_COSINE_FLOOR,
                maximum=1.0,
            ),
            d1_representation_phase_coherence_floor=_finite_float(
                item["d1_representation_phase_coherence_floor"],
                label="thresholds.d1_representation_phase_coherence_floor",
                minimum=MIN_D1_COSINE_FLOOR,
                maximum=1.0,
            ),
            core_amplitude_ceiling=_finite_float(
                item["core_amplitude_ceiling"],
                label="thresholds.core_amplitude_ceiling",
                minimum=0.0,
                minimum_inclusive=False,
            ),
            identifiability_floor=_finite_float(
                item["identifiability_floor"],
                label="thresholds.identifiability_floor",
                minimum=MIN_IDENTIFIABILITY_FLOOR,
            ),
            coherence_floor=_finite_float(
                item["coherence_floor"],
                label="thresholds.coherence_floor",
                minimum=MIN_COHERENCE_FLOOR,
                maximum=1.0,
                maximum_inclusive=False,
            ),
            minimum_support_count=_plain_int(
                item["minimum_support_count"],
                label="thresholds.minimum_support_count",
                minimum=1,
            ),
            max_localized_core_fraction=_finite_float(
                item["max_localized_core_fraction"],
                label="thresholds.max_localized_core_fraction",
                minimum=0.0,
                maximum=1.0,
                minimum_inclusive=False,
                maximum_inclusive=False,
            ),
            minimum_core_contrast_ratio=_finite_float(
                item["minimum_core_contrast_ratio"],
                label="thresholds.minimum_core_contrast_ratio",
                minimum=1.0,
                minimum_inclusive=False,
            ),
            branch_margin_rad=_finite_float(
                item["branch_margin_rad"],
                label="thresholds.branch_margin_rad",
                minimum=MIN_BRANCH_MARGIN_RAD,
                maximum=math.pi,
                maximum_inclusive=False,
            ),
            loop_nonzero_floor_cycles=_finite_float(
                item["loop_nonzero_floor_cycles"],
                label="thresholds.loop_nonzero_floor_cycles",
                minimum=0.0,
                maximum=1.0,
                minimum_inclusive=False,
                maximum_inclusive=False,
            ),
            loop_oracle_tolerance_cycles=_finite_float(
                item["loop_oracle_tolerance_cycles"],
                label="thresholds.loop_oracle_tolerance_cycles",
                minimum=0.0,
                maximum=MAX_LOOP_ORACLE_TOLERANCE_CYCLES,
            ),
            graph_total_tolerance_cycles=_finite_float(
                item["graph_total_tolerance_cycles"],
                label="thresholds.graph_total_tolerance_cycles",
                minimum=0.0,
                maximum=MAX_GRAPH_TOTAL_TOLERANCE_CYCLES,
            ),
            core_candidate_difference_tolerance_rows=_plain_int(
                item["core_candidate_difference_tolerance_rows"],
                label="thresholds.core_candidate_difference_tolerance_rows",
                minimum=0,
            ),
            minimum_representative_content_variants=_plain_int(
                item["minimum_representative_content_variants"],
                label="thresholds.minimum_representative_content_variants",
                minimum=2,
            ),
            minimum_field_output_effect_size=_finite_float(
                item["minimum_field_output_effect_size"],
                label="thresholds.minimum_field_output_effect_size",
                minimum=MIN_FIELD_OUTPUT_EFFECT_SIZE,
                maximum=1.0,
            ),
        )


@dataclass(frozen=True, slots=True)
class CoveragePolicy:
    """Frozen-universe all-cells-required aggregation contract."""

    evaluation_unit: EvaluationUnit
    minimum_coverage: float
    maximum_abstention_fraction: float
    minimum_recall: float
    minimum_specificity: float
    aggregation: str = "worst_case_required_strata"
    score_denominator: str = "expected_nonprerequisite_primary_units"
    graph_cells_are_repeated_measures: bool = True
    insufficient_counts_as_success: bool = False
    all_expected_primary_units_must_pass: bool = True

    def __post_init__(self) -> None:
        if self.evaluation_unit is not EvaluationUnit.PHANTOM_INSTANCE:
            raise QualificationContractError(
                "coverage evaluation_unit must be phantom_instance"
            )
        for name in (
            "minimum_coverage",
            "maximum_abstention_fraction",
            "minimum_recall",
            "minimum_specificity",
        ):
            object.__setattr__(
                self,
                name,
                _finite_float(
                    getattr(self, name),
                    label=f"coverage_policy.{name}",
                    minimum=0.0,
                    maximum=1.0,
                ),
            )
        for name, expected in (
            ("minimum_coverage", 1.0),
            ("maximum_abstention_fraction", 0.0),
            ("minimum_recall", 1.0),
            ("minimum_specificity", 1.0),
        ):
            _constant(
                getattr(self, name),
                expected,
                label=f"coverage_policy.{name}",
            )
        _constant(
            self.aggregation,
            "worst_case_required_strata",
            label="coverage_policy.aggregation",
        )
        _constant(
            self.score_denominator,
            "expected_nonprerequisite_primary_units",
            label="coverage_policy.score_denominator",
        )
        _constant(
            self.graph_cells_are_repeated_measures,
            True,
            label="coverage_policy.graph_cells_are_repeated_measures",
        )
        _constant(
            self.insufficient_counts_as_success,
            False,
            label="coverage_policy.insufficient_counts_as_success",
        )
        _constant(
            self.all_expected_primary_units_must_pass,
            True,
            label="coverage_policy.all_expected_primary_units_must_pass",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "evaluation_unit": self.evaluation_unit.value,
            "minimum_coverage": self.minimum_coverage,
            "maximum_abstention_fraction": self.maximum_abstention_fraction,
            "minimum_recall": self.minimum_recall,
            "minimum_specificity": self.minimum_specificity,
            "aggregation": self.aggregation,
            "score_denominator": self.score_denominator,
            "graph_cells_are_repeated_measures": (
                self.graph_cells_are_repeated_measures
            ),
            "insufficient_counts_as_success": (self.insufficient_counts_as_success),
            "all_expected_primary_units_must_pass": (
                self.all_expected_primary_units_must_pass
            ),
        }

    @classmethod
    def from_dict(cls, value: object) -> CoveragePolicy:
        item = _mapping(value, label="coverage_policy")
        expected = {
            "evaluation_unit",
            "minimum_coverage",
            "maximum_abstention_fraction",
            "minimum_recall",
            "minimum_specificity",
            "aggregation",
            "score_denominator",
            "graph_cells_are_repeated_measures",
            "insufficient_counts_as_success",
            "all_expected_primary_units_must_pass",
        }
        _exact_keys(item, expected, label="coverage_policy")
        return cls(
            evaluation_unit=_enum(
                EvaluationUnit,
                item["evaluation_unit"],
                label="coverage_policy.evaluation_unit",
            ),  # type: ignore[arg-type]
            minimum_coverage=_finite_float(
                item["minimum_coverage"],
                label="coverage_policy.minimum_coverage",
                minimum=0.0,
                maximum=1.0,
            ),
            maximum_abstention_fraction=_finite_float(
                item["maximum_abstention_fraction"],
                label="coverage_policy.maximum_abstention_fraction",
                minimum=0.0,
                maximum=1.0,
            ),
            minimum_recall=_finite_float(
                item["minimum_recall"],
                label="coverage_policy.minimum_recall",
                minimum=0.0,
                maximum=1.0,
            ),
            minimum_specificity=_finite_float(
                item["minimum_specificity"],
                label="coverage_policy.minimum_specificity",
                minimum=0.0,
                maximum=1.0,
            ),
            aggregation=_constant(
                item["aggregation"],
                "worst_case_required_strata",
                label="coverage_policy.aggregation",
            ),  # type: ignore[arg-type]
            score_denominator=_constant(
                item["score_denominator"],
                "expected_nonprerequisite_primary_units",
                label="coverage_policy.score_denominator",
            ),  # type: ignore[arg-type]
            graph_cells_are_repeated_measures=_constant(
                item["graph_cells_are_repeated_measures"],
                True,
                label="coverage_policy.graph_cells_are_repeated_measures",
            ),  # type: ignore[arg-type]
            insufficient_counts_as_success=_constant(
                item["insufficient_counts_as_success"],
                False,
                label="coverage_policy.insufficient_counts_as_success",
            ),  # type: ignore[arg-type]
            all_expected_primary_units_must_pass=_constant(
                item["all_expected_primary_units_must_pass"],
                True,
                label="coverage_policy.all_expected_primary_units_must_pass",
            ),  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class StressAssignment:
    axis_id: str
    level: str

    def __post_init__(self) -> None:
        _slug(self.axis_id, label="stress assignment axis_id")
        _slug(self.level, label="stress assignment level")

    def to_dict(self) -> dict[str, object]:
        return {"axis_id": self.axis_id, "level": self.level}

    @classmethod
    def from_dict(cls, value: object) -> StressAssignment:
        item = _mapping(value, label="stress assignment")
        _exact_keys(item, {"axis_id", "level"}, label="stress assignment")
        return cls(
            axis_id=_slug(item["axis_id"], label="stress assignment axis_id"),
            level=_slug(item["level"], label="stress assignment level"),
        )


def required_stress_stratum_id(axis_id: str, level: str) -> str:
    """Return the sole canonical worst-case stratum ID for one stress level."""

    axis = _slug(axis_id, label="required stress stratum axis_id")
    declared_level = _slug(level, label="required stress stratum level")
    return _slug(
        f"stress.{axis}.{declared_level}",
        label="required stress stratum ID",
    )


@dataclass(frozen=True, slots=True)
class ExpectedCoreCell:
    """One exact primary-unit variant x field-graph core obligation."""

    core_cell_id: str
    primary_unit_id: str
    selection_seed: int
    control_id: str
    stress_assignments: tuple[StressAssignment, ...]
    field_graph_id: str
    expected_core_disposition: CoreDisposition

    def __post_init__(self) -> None:
        for name in (
            "core_cell_id",
            "primary_unit_id",
            "control_id",
            "field_graph_id",
        ):
            _slug(getattr(self, name), label=f"expected core cell {name}")
        _plain_int(self.selection_seed, label="expected core cell selection_seed")
        assignment_axes = tuple(
            assignment.axis_id for assignment in self.stress_assignments
        )
        _canonical_unique_slugs(
            assignment_axes,
            label="expected core cell stress assignment axes",
            nonempty=False,
        )
        if not isinstance(self.expected_core_disposition, CoreDisposition):
            raise TypeError("expected_core_disposition must be a CoreDisposition")

    def to_dict(self) -> dict[str, object]:
        return {
            "core_cell_id": self.core_cell_id,
            "primary_unit_id": self.primary_unit_id,
            "selection_seed": self.selection_seed,
            "control_id": self.control_id,
            "stress_assignments": [
                assignment.to_dict() for assignment in self.stress_assignments
            ],
            "field_graph_id": self.field_graph_id,
            "expected_core_disposition": (self.expected_core_disposition.value),
        }

    @classmethod
    def from_dict(cls, value: object) -> ExpectedCoreCell:
        item = _mapping(value, label="expected core cell")
        expected = {
            "core_cell_id",
            "primary_unit_id",
            "selection_seed",
            "control_id",
            "stress_assignments",
            "field_graph_id",
            "expected_core_disposition",
        }
        _exact_keys(item, expected, label="expected core cell")
        return cls(
            core_cell_id=_slug(
                item["core_cell_id"],
                label="expected core cell core_cell_id",
            ),
            primary_unit_id=_slug(
                item["primary_unit_id"],
                label="expected core cell primary_unit_id",
            ),
            selection_seed=_plain_int(
                item["selection_seed"],
                label="expected core cell selection_seed",
            ),
            control_id=_slug(
                item["control_id"],
                label="expected core cell control_id",
            ),
            stress_assignments=tuple(
                StressAssignment.from_dict(assignment)
                for assignment in _sequence(
                    item["stress_assignments"],
                    label="expected core cell stress_assignments",
                )
            ),
            field_graph_id=_slug(
                item["field_graph_id"],
                label="expected core cell field_graph_id",
            ),
            expected_core_disposition=_enum(
                CoreDisposition,
                item["expected_core_disposition"],
                label="expected core disposition",
            ),  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class ExpectedCell:
    """One exact primary-unit variant x A x B x loop-role obligation."""

    cell_id: str
    primary_unit_id: str
    selection_seed: int
    control_id: str
    stress_assignments: tuple[StressAssignment, ...]
    field_graph_id: str
    cycle_graph_id: str
    loop_role: LoopRole
    expected_loop_disposition: LoopDisposition
    stratum_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "cell_id",
            "primary_unit_id",
            "control_id",
            "field_graph_id",
            "cycle_graph_id",
        ):
            _slug(getattr(self, name), label=f"expected cell {name}")
        _plain_int(self.selection_seed, label="expected cell selection_seed")
        if not isinstance(self.loop_role, LoopRole):
            raise TypeError("loop_role must be a LoopRole")
        if not isinstance(
            self.expected_loop_disposition,
            LoopDisposition,
        ):
            raise TypeError("expected_loop_disposition must be a LoopDisposition")
        assignment_axes = tuple(
            assignment.axis_id for assignment in self.stress_assignments
        )
        _canonical_unique_slugs(
            assignment_axes,
            label="expected cell stress assignment axes",
            nonempty=False,
        )
        _canonical_unique_slugs(self.stratum_ids, label="expected cell stratum_ids")

    def to_dict(self) -> dict[str, object]:
        return {
            "cell_id": self.cell_id,
            "primary_unit_id": self.primary_unit_id,
            "selection_seed": self.selection_seed,
            "control_id": self.control_id,
            "stress_assignments": [
                assignment.to_dict() for assignment in self.stress_assignments
            ],
            "field_graph_id": self.field_graph_id,
            "cycle_graph_id": self.cycle_graph_id,
            "loop_role": self.loop_role.value,
            "expected_loop_disposition": (self.expected_loop_disposition.value),
            "stratum_ids": list(self.stratum_ids),
        }

    @classmethod
    def from_dict(cls, value: object) -> ExpectedCell:
        item = _mapping(value, label="expected cell")
        expected = {
            "cell_id",
            "primary_unit_id",
            "selection_seed",
            "control_id",
            "stress_assignments",
            "field_graph_id",
            "cycle_graph_id",
            "loop_role",
            "expected_loop_disposition",
            "stratum_ids",
        }
        _exact_keys(item, expected, label="expected cell")
        return cls(
            cell_id=_slug(item["cell_id"], label="expected cell cell_id"),
            primary_unit_id=_slug(
                item["primary_unit_id"],
                label="expected cell primary_unit_id",
            ),
            selection_seed=_plain_int(
                item["selection_seed"],
                label="expected cell selection_seed",
            ),
            control_id=_slug(item["control_id"], label="expected cell control_id"),
            stress_assignments=tuple(
                StressAssignment.from_dict(assignment)
                for assignment in _sequence(
                    item["stress_assignments"],
                    label="expected cell stress_assignments",
                )
            ),
            field_graph_id=_slug(
                item["field_graph_id"],
                label="expected cell field_graph_id",
            ),
            cycle_graph_id=_slug(
                item["cycle_graph_id"],
                label="expected cell cycle_graph_id",
            ),
            loop_role=_enum(
                LoopRole,
                item["loop_role"],
                label="expected cell loop_role",
            ),  # type: ignore[arg-type]
            expected_loop_disposition=_enum(
                LoopDisposition,
                item["expected_loop_disposition"],
                label="expected cell expected_loop_disposition",
            ),  # type: ignore[arg-type]
            stratum_ids=tuple(
                _slug(stratum_id, label="expected cell stratum_id")
                for stratum_id in _sequence(
                    item["stratum_ids"],
                    label="expected cell stratum_ids",
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class ExpectedStratum:
    """One exact aggregation stratum over unique primary units."""

    stratum_id: str
    evaluation_unit: EvaluationUnit
    required: bool
    primary_unit_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _slug(self.stratum_id, label="expected stratum stratum_id")
        if not isinstance(self.evaluation_unit, EvaluationUnit):
            raise TypeError("evaluation_unit must be an EvaluationUnit")
        if type(self.required) is not bool:
            raise TypeError("required must be bool")
        _canonical_unique_slugs(
            self.primary_unit_ids,
            label=f"expected stratum {self.stratum_id} primary_unit_ids",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "stratum_id": self.stratum_id,
            "evaluation_unit": self.evaluation_unit.value,
            "required": self.required,
            "primary_unit_ids": list(self.primary_unit_ids),
        }

    @classmethod
    def from_dict(cls, value: object) -> ExpectedStratum:
        item = _mapping(value, label="expected stratum")
        _exact_keys(
            item,
            {"stratum_id", "evaluation_unit", "required", "primary_unit_ids"},
            label="expected stratum",
        )
        if type(item["required"]) is not bool:
            raise QualificationContractError("expected stratum required must be bool")
        return cls(
            stratum_id=_slug(item["stratum_id"], label="expected stratum stratum_id"),
            evaluation_unit=_enum(
                EvaluationUnit,
                item["evaluation_unit"],
                label="expected stratum evaluation_unit",
            ),  # type: ignore[arg-type]
            required=item["required"],
            primary_unit_ids=tuple(
                _slug(primary_unit_id, label="expected stratum primary_unit_id")
                for primary_unit_id in _sequence(
                    item["primary_unit_ids"],
                    label="expected stratum primary_unit_ids",
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class AuthorityBoundary:
    """Closed negative authority of the synthetic selection lane."""

    pythia_access_authorized: bool = False
    subject_data_access_authorized: bool = False
    subject_execution_authorized: bool = False
    semantic_labels_authorized: bool = False
    integer_output_authorized: bool = False
    p0_competitor_selection_authorized: bool = False
    representation_d2_d5_transfer_authorized: bool = False
    localized_core_loop_join_authorized: bool = False
    synthetic_qualification_authorized: bool = False

    def __post_init__(self) -> None:
        for name in (
            "pythia_access_authorized",
            "subject_data_access_authorized",
            "subject_execution_authorized",
            "semantic_labels_authorized",
            "integer_output_authorized",
            "p0_competitor_selection_authorized",
            "representation_d2_d5_transfer_authorized",
            "localized_core_loop_join_authorized",
            "synthetic_qualification_authorized",
        ):
            _constant(getattr(self, name), False, label=f"authority.{name}")

    def to_dict(self) -> dict[str, object]:
        return {
            "pythia_access_authorized": self.pythia_access_authorized,
            "subject_data_access_authorized": self.subject_data_access_authorized,
            "subject_execution_authorized": self.subject_execution_authorized,
            "semantic_labels_authorized": self.semantic_labels_authorized,
            "integer_output_authorized": self.integer_output_authorized,
            "p0_competitor_selection_authorized": (
                self.p0_competitor_selection_authorized
            ),
            "representation_d2_d5_transfer_authorized": (
                self.representation_d2_d5_transfer_authorized
            ),
            "localized_core_loop_join_authorized": (
                self.localized_core_loop_join_authorized
            ),
            "synthetic_qualification_authorized": (
                self.synthetic_qualification_authorized
            ),
        }

    @classmethod
    def from_dict(cls, value: object) -> AuthorityBoundary:
        item = _mapping(value, label="authority")
        expected = {
            "pythia_access_authorized",
            "subject_data_access_authorized",
            "subject_execution_authorized",
            "semantic_labels_authorized",
            "integer_output_authorized",
            "p0_competitor_selection_authorized",
            "representation_d2_d5_transfer_authorized",
            "localized_core_loop_join_authorized",
            "synthetic_qualification_authorized",
        }
        _exact_keys(item, expected, label="authority")
        for name in expected:
            _constant(item[name], False, label=f"authority.{name}")
        return cls()


@dataclass(frozen=True, slots=True)
class QualificationProtocol:
    """Complete immutable D0--D5 calibration-selection declaration."""

    protocol_id: str
    engine: EngineBinding
    registry: RegistryBinding
    instrument: InstrumentSelection
    implementation_registry: ClosedImplementationRegistry
    graphs: GraphAxes
    domain: DomainDeclaration
    cartesian: CartesianSelectionSubstrate
    selection: SelectionDesign
    thresholds: Thresholds
    coverage_policy: CoveragePolicy
    expected_core_cells: tuple[ExpectedCoreCell, ...]
    expected_cells: tuple[ExpectedCell, ...]
    expected_strata: tuple[ExpectedStratum, ...]
    preseed_readiness: PreseedReadinessBinding | None = None
    d2_core_confounders: tuple[D2CoreConfounderDeclaration, ...] = (
        D2_CORE_CONFOUNDER_REGISTRY
    )
    authority: AuthorityBoundary = AuthorityBoundary()
    schema_version: str = QUALIFICATION_PROTOCOL_SCHEMA_VERSION
    role: str = "calibration_selection"
    claim_ceiling: str = "level_0"
    gates: tuple[str, ...] = _GATE_ORDER

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "protocol_id",
            "role",
            "claim_ceiling",
            "gate_claim_scopes",
            "evaluation_design",
            "engine",
            "registry",
            "preseed_readiness",
            "instrument",
            "implementation_registry",
            "graphs",
            "domain",
            "cartesian",
            "selection",
            "thresholds",
            "coverage_policy",
            "expected_core_cells",
            "expected_cells",
            "expected_strata",
            "d2_core_confounders",
            "gates",
            "authority",
        }
    )

    def __post_init__(self) -> None:
        _constant(
            self.schema_version,
            QUALIFICATION_PROTOCOL_SCHEMA_VERSION,
            label="schema_version",
        )
        _slug(self.protocol_id, label="protocol_id")
        _constant(self.role, "calibration_selection", label="role")
        _constant(self.claim_ceiling, "level_0", label="claim_ceiling")
        if self.gates != _GATE_ORDER:
            raise QualificationContractError(
                "protocol gates must be exactly d0 through d5 in order"
            )
        if not self.expected_core_cells:
            raise QualificationContractError("expected_core_cells must not be empty")
        if not self.expected_cells:
            raise QualificationContractError("expected_cells must not be empty")
        if not self.expected_strata:
            raise QualificationContractError("expected_strata must not be empty")
        if self.d2_core_confounders != D2_CORE_CONFOUNDER_REGISTRY:
            raise QualificationContractError(
                "d2_core_confounders must equal the exact seed-free "
                "D2-only false-core registry"
            )
        if self.preseed_readiness is not None:
            if not isinstance(self.preseed_readiness, PreseedReadinessBinding):
                raise TypeError(
                    "preseed_readiness must be a PreseedReadinessBinding or None"
                )
            if self.preseed_readiness.engine_commit != self.engine.commit:
                raise QualificationContractError(
                    "preseed readiness engine commit differs from the protocol"
                )
            if (
                self.preseed_readiness.registry_source_sha256
                != self.registry.registry_source_sha256
                or self.preseed_readiness.registry_canonical_sha256
                != self.registry.registry_canonical_sha256
                or self.preseed_readiness.referent_canonical_sha256
                != self.registry.referent_canonical_sha256
            ):
                raise QualificationContractError(
                    "preseed readiness registry/referent identities differ "
                    "from the protocol"
                )
        self._validate_manifests()
        if len(self.canonical_bytes) > MAX_QUALIFICATION_PROTOCOL_BYTES:
            raise QualificationContractError(
                "canonical qualification protocol exceeds the fixed byte cap"
            )

    def _validate_manifests(self) -> None:
        core_cell_ids = tuple(cell.core_cell_id for cell in self.expected_core_cells)
        _canonical_unique_slugs(
            core_cell_ids,
            label="expected core cell IDs",
        )
        cell_ids = tuple(cell.cell_id for cell in self.expected_cells)
        _canonical_unique_slugs(cell_ids, label="expected cell IDs")
        stratum_ids = tuple(stratum.stratum_id for stratum in self.expected_strata)
        _canonical_unique_slugs(stratum_ids, label="expected stratum IDs")

        seed_set = set(self.selection.seeds)
        controls = {control.control_id: control for control in self.selection.controls}
        if (
            self.implementation_registry.generator_family_id
            != self.cartesian.generator_family_id
        ):
            raise QualificationContractError(
                "implementation registry generator family does not exactly "
                "join the Cartesian substrate"
            )
        if self.implementation_registry.instrument != self.instrument:
            raise QualificationContractError(
                "implementation registry instrument does not exactly join "
                "the selected instrument"
            )
        registered_cases = {
            binding.generator_case_id: (
                binding.core_disposition,
                binding.loop_disposition,
            )
            for binding in self.implementation_registry.generator_cases
        }
        selected_cases = {
            control.generator_case_id: (
                control.core_disposition,
                control.loop_disposition,
            )
            for control in self.selection.controls
        }
        if registered_cases != selected_cases:
            raise QualificationContractError(
                "implementation registry generator cases do not exactly join "
                "the selected controls"
            )
        axes = {axis.axis_id: set(axis.levels) for axis in self.selection.stress_axes}
        expected_cartesian_axes = {
            self.cartesian.structured_observation_perturbation_axis_id: {
                item.level
                for item in self.cartesian.structured_observation_perturbation_levels
            },
            self.cartesian.state_geometry_warp_axis_id: {
                item.level for item in self.cartesian.state_geometry_warp_levels
            },
            self.cartesian.boundary_axis_id: {
                item.level for item in self.cartesian.primary_boundaries
            },
        }
        if axes != expected_cartesian_axes:
            raise QualificationContractError(
                "selection stress axes differ from the exact Cartesian "
                "numeric substrate"
            )
        # A protocol that passes schema validation must also be executable by
        # the exact closed generator.  This constructor performs no numerical
        # generation or allocation; it applies the generator's signed-int64,
        # monotonic-density, finite-scale, and fixed peak-allocation guards.
        from spirallens.synthetic.cartesian_fourier_domain_phantom import (
            CartesianFourierDomainSpec,
        )

        for seed in self.selection.seeds:
            for (
                perturbation
            ) in self.cartesian.structured_observation_perturbation_levels:
                for state_geometry_warp in self.cartesian.state_geometry_warp_levels:
                    try:
                        CartesianFourierDomainSpec(
                            seed=seed,
                            grid_side=self.cartesian.grid_side,
                            ambient_dimension=self.cartesian.ambient_dimension,
                            samples_per_split=self.cartesian.samples_per_split,
                            baseline=self.cartesian.baseline,
                            second_harmonic_scale=(
                                self.cartesian.second_harmonic_scale
                            ),
                            noise_scale=perturbation.value,
                            density_warp_strength=state_geometry_warp.value,
                        )
                    except (TypeError, ValueError) as error:
                        raise QualificationContractError(
                            "Cartesian selection substrate is not executable by "
                            "the closed generator"
                        ) from error
        a_ids = {graph.graph_id for graph in self.graphs.field_estimation}
        b_ids = {graph.graph_id for graph in self.graphs.cycle_construction}
        row_count = self.cartesian.grid_side * self.cartesian.grid_side
        if self.thresholds.max_localized_core_fraction < 1.0 / row_count:
            raise QualificationContractError(
                "max_localized_core_fraction cannot admit one exact core row"
            )
        if self.thresholds.minimum_support_count > row_count - 2:
            raise QualificationContractError(
                "minimum_support_count exceeds the D2 missing-candidate-support "
                "noncandidate support capacity"
            )
        for graph in (
            *self.graphs.field_estimation,
            *self.graphs.cycle_construction,
        ):
            parameters = dict(graph.parameters)
            neighbor_count = parameters.get("neighbor_count")
            if neighbor_count is not None and neighbor_count >= row_count:
                raise QualificationContractError(
                    "graph neighbor_count must be smaller than the Cartesian row count"
                )
        declared_strata = set(stratum_ids)
        required_stratum_ids = {
            required_stress_stratum_id(axis.axis_id, level)
            for axis in self.selection.stress_axes
            for level in axis.levels
        }
        if declared_strata != required_stratum_ids:
            raise QualificationContractError(
                "expected_strata must be the exact boundary, "
                "state-geometry-warp, and structured-observation-perturbation "
                "stress-level worst-case manifest"
            )
        if any(
            not stratum.required
            or stratum.evaluation_unit is not EvaluationUnit.PHANTOM_INSTANCE
            for stratum in self.expected_strata
        ):
            raise QualificationContractError(
                "every stress-level stratum must be a required phantom-instance "
                "worst-case gate"
            )

        core_base_cells: dict[
            tuple[int, str, tuple[tuple[str, str], ...]],
            list[ExpectedCoreCell],
        ] = {}
        base_cells: dict[
            tuple[int, str, tuple[tuple[str, str], ...]],
            list[ExpectedCell],
        ] = {}
        primary_base: dict[
            str,
            tuple[int, str, tuple[tuple[str, str], ...]],
        ] = {}
        primary_strata: dict[str, tuple[str, ...]] = {}
        for core_cell in self.expected_core_cells:
            if core_cell.selection_seed not in seed_set:
                raise QualificationContractError(
                    "expected core cell references an undeclared selection seed"
                )
            control = controls.get(core_cell.control_id)
            if control is None:
                raise QualificationContractError(
                    "expected core cell references an undeclared control"
                )
            assignments = tuple(
                (assignment.axis_id, assignment.level)
                for assignment in core_cell.stress_assignments
            )
            if tuple(axis_id for axis_id, _level in assignments) != tuple(axes):
                raise QualificationContractError(
                    "expected core cell stress axes must exactly match the "
                    "canonical selection axes"
                )
            if any(level not in axes[axis_id] for axis_id, level in assignments):
                raise QualificationContractError(
                    "expected core cell references an undeclared stress level"
                )
            if core_cell.field_graph_id not in a_ids:
                raise QualificationContractError(
                    "expected core cell references an undeclared A graph"
                )
            if core_cell.expected_core_disposition is not control.core_disposition:
                raise QualificationContractError(
                    "expected core disposition differs from its control"
                )
            base = (
                core_cell.selection_seed,
                core_cell.control_id,
                assignments,
            )
            existing_base = primary_base.setdefault(
                core_cell.primary_unit_id,
                base,
            )
            if existing_base != base:
                raise QualificationContractError(
                    "one primary_unit_id maps to multiple selection variants"
                )
            core_base_cells.setdefault(base, []).append(core_cell)

        for cell in self.expected_cells:
            if cell.selection_seed not in seed_set:
                raise QualificationContractError(
                    "expected cell references an undeclared selection seed"
                )
            if cell.control_id not in controls:
                raise QualificationContractError(
                    "expected cell references an undeclared control"
                )
            assignments = tuple(
                (assignment.axis_id, assignment.level)
                for assignment in cell.stress_assignments
            )
            if tuple(axis_id for axis_id, _level in assignments) != tuple(axes):
                raise QualificationContractError(
                    "expected cell stress axes must exactly match the "
                    "canonical selection axes"
                )
            if any(level not in axes[axis_id] for axis_id, level in assignments):
                raise QualificationContractError(
                    "expected cell references an undeclared stress level"
                )
            expected_cell_strata = tuple(
                sorted(
                    required_stress_stratum_id(axis_id, level)
                    for axis_id, level in assignments
                )
            )
            if cell.stratum_ids != expected_cell_strata:
                raise QualificationContractError(
                    "expected cell strata must exactly follow its stress assignments"
                )
            if cell.field_graph_id not in a_ids or cell.cycle_graph_id not in b_ids:
                raise QualificationContractError(
                    "expected cell references an undeclared A or B graph"
                )
            if not set(cell.stratum_ids) <= declared_strata:
                raise QualificationContractError(
                    "expected cell references an undeclared stratum"
                )
            control = controls[cell.control_id]
            expected_loop = (
                control.loop_disposition
                if cell.loop_role is LoopRole.PRIMARY_BOUNDARY
                else (
                    LoopDisposition.PREREQUISITE_FAILURE
                    if control.loop_disposition is LoopDisposition.PREREQUISITE_FAILURE
                    else LoopDisposition.NULL
                )
            )
            if cell.expected_loop_disposition is not expected_loop:
                raise QualificationContractError(
                    "expected loop disposition differs from its control and loop role"
                )
            base = (cell.selection_seed, cell.control_id, assignments)
            existing_base = primary_base.setdefault(cell.primary_unit_id, base)
            if existing_base != base:
                raise QualificationContractError(
                    "one primary_unit_id maps to multiple selection variants"
                )
            existing_strata = primary_strata.setdefault(
                cell.primary_unit_id, cell.stratum_ids
            )
            if existing_strata != cell.stratum_ids:
                raise QualificationContractError(
                    "graph cells of one primary unit must have identical strata"
                )
            base_cells.setdefault(base, []).append(cell)

        expected_bases: set[tuple[int, str, tuple[tuple[str, str], ...]]] = set()

        def extend_assignments(
            index: int,
            current: tuple[tuple[str, str], ...],
        ) -> None:
            if index == len(self.selection.stress_axes):
                for seed in self.selection.seeds:
                    for control in self.selection.controls:
                        expected_bases.add((seed, control.control_id, current))
                return
            axis = self.selection.stress_axes[index]
            for level in axis.levels:
                extend_assignments(index + 1, (*current, (axis.axis_id, level)))

        extend_assignments(0, ())
        if set(base_cells) != expected_bases:
            raise QualificationContractError(
                "expected_cells must cover the exact seed × control × stress manifest"
            )
        if set(core_base_cells) != expected_bases:
            raise QualificationContractError(
                "expected_core_cells must cover the exact seed × control × "
                "stress manifest"
            )
        for base in sorted(expected_bases):
            core_primary_ids = {cell.primary_unit_id for cell in core_base_cells[base]}
            loop_primary_ids = {cell.primary_unit_id for cell in base_cells[base]}
            if len(core_primary_ids) != 1 or loop_primary_ids != core_primary_ids:
                raise QualificationContractError(
                    "core and loop manifests must use one identical primary "
                    "unit ID for every selection variant"
                )
        required_core_cross = set(a_ids)
        for cells in core_base_cells.values():
            observed = {cell.field_graph_id for cell in cells}
            if observed != required_core_cross or len(cells) != len(
                required_core_cross
            ):
                raise QualificationContractError(
                    "every primary-unit variant must contain the exact full "
                    "A core matrix"
                )
        required_cross = {
            (a_id, b_id, loop_role)
            for a_id in a_ids
            for b_id in b_ids
            for loop_role in LoopRole
        }
        for cells in base_cells.values():
            observed_cross = {
                (
                    cell.field_graph_id,
                    cell.cycle_graph_id,
                    cell.loop_role,
                )
                for cell in cells
            }
            if observed_cross != required_cross or len(cells) != len(required_cross):
                raise QualificationContractError(
                    "every primary-unit variant must contain the exact full "
                    "A x B x loop-role matrix"
                )

        primary_unit_count = len(expected_bases)
        if primary_unit_count > MAX_QUALIFICATION_PRIMARY_UNITS:
            raise QualificationContractError(
                "selection Cartesian product exceeds the fixed primary-unit cap"
            )
        if len(self.expected_core_cells) > MAX_QUALIFICATION_CORE_CELLS:
            raise QualificationContractError(
                "expected core manifest exceeds the fixed cell cap"
            )
        if len(self.expected_cells) > MAX_QUALIFICATION_LOOP_CELLS:
            raise QualificationContractError(
                "expected loop manifest exceeds the fixed cell cap"
            )
        event_lane_count = len(self.expected_core_cells) + len(self.expected_cells)
        if event_lane_count > MAX_QUALIFICATION_EVENT_LANES:
            raise QualificationContractError(
                "expected manifests exceed the fixed event-lane cap"
            )
        if (
            event_lane_count * QUALIFICATION_EVENTS_PER_LANE
            > MAX_QUALIFICATION_EVENT_ENTRIES
        ):
            raise QualificationContractError(
                "expected manifests exceed the fixed event-entry cap"
            )

        all_primary_units = set(primary_base)
        for stratum in self.expected_strata:
            if not set(stratum.primary_unit_ids) <= all_primary_units:
                raise QualificationContractError(
                    "expected stratum references an undeclared primary unit"
                )
            observed_members = {
                primary_unit_id
                for primary_unit_id, memberships in primary_strata.items()
                if stratum.stratum_id in memberships
            }
            if observed_members != set(stratum.primary_unit_ids):
                raise QualificationContractError(
                    "expected stratum primary-unit membership differs from cells"
                )
        required_memberships = {
            primary_unit_id
            for stratum in self.expected_strata
            if stratum.required
            for primary_unit_id in stratum.primary_unit_ids
        }
        if required_memberships != all_primary_units:
            raise QualificationContractError(
                "every primary unit must belong to at least one required stratum"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "protocol_id": self.protocol_id,
            "role": self.role,
            "claim_ceiling": self.claim_ceiling,
            "gate_claim_scopes": self.gate_claim_scopes,
            "evaluation_design": self.evaluation_design.to_dict(),
            "engine": self.engine.to_dict(),
            "registry": self.registry.to_dict(),
            "preseed_readiness": (
                None
                if self.preseed_readiness is None
                else self.preseed_readiness.to_dict()
            ),
            "instrument": self.instrument.to_dict(),
            "implementation_registry": self.implementation_registry.to_dict(),
            "graphs": self.graphs.to_dict(),
            "domain": self.domain.to_dict(),
            "cartesian": self.cartesian.to_dict(),
            "selection": self.selection.to_dict(),
            "thresholds": self.thresholds.to_dict(),
            "coverage_policy": self.coverage_policy.to_dict(),
            "expected_core_cells": [
                cell.to_dict() for cell in self.expected_core_cells
            ],
            "expected_cells": [cell.to_dict() for cell in self.expected_cells],
            "expected_strata": [stratum.to_dict() for stratum in self.expected_strata],
            "d2_core_confounders": [
                item.to_dict() for item in self.d2_core_confounders
            ],
            "gates": list(self.gates),
            "authority": self.authority.to_dict(),
        }

    @property
    def gate_claim_scopes(self) -> dict[str, str]:
        """Return the mandatory positive scope declaration in gate order."""

        return {
            gate_id: gate_claim_scope_for_gate(gate_id).value for gate_id in self.gates
        }

    @property
    def evaluation_design(self) -> EvaluationDesign:
        """Derive the serialized repeated-measures design from closed axes."""

        return EvaluationDesign.derive(
            selection=self.selection,
            boundary_axis_id=self.cartesian.boundary_axis_id,
        )

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> QualificationProtocol:
        document = _mapping(value, label="qualification protocol")
        _exact_keys(document, cls._ROOT_KEYS, label="qualification protocol")
        gates = tuple(
            _slug(gate, label="qualification gate")
            for gate in _sequence(document["gates"], label="gates")
        )
        result = cls(
            schema_version=_constant(
                document["schema_version"],
                QUALIFICATION_PROTOCOL_SCHEMA_VERSION,
                label="schema_version",
            ),  # type: ignore[arg-type]
            protocol_id=_slug(document["protocol_id"], label="protocol_id"),
            role=_constant(document["role"], "calibration_selection", label="role"),  # type: ignore[arg-type]
            claim_ceiling=_constant(
                document["claim_ceiling"], "level_0", label="claim_ceiling"
            ),  # type: ignore[arg-type]
            engine=EngineBinding.from_dict(document["engine"]),
            registry=RegistryBinding.from_dict(document["registry"]),
            preseed_readiness=(
                None
                if document["preseed_readiness"] is None
                else PreseedReadinessBinding.from_dict(document["preseed_readiness"])
            ),
            instrument=InstrumentSelection.from_dict(document["instrument"]),
            implementation_registry=ClosedImplementationRegistry.from_dict(
                document["implementation_registry"]
            ),
            graphs=GraphAxes.from_dict(document["graphs"]),
            domain=DomainDeclaration.from_dict(document["domain"]),
            cartesian=CartesianSelectionSubstrate.from_dict(document["cartesian"]),
            selection=SelectionDesign.from_dict(document["selection"]),
            thresholds=Thresholds.from_dict(document["thresholds"]),
            coverage_policy=CoveragePolicy.from_dict(document["coverage_policy"]),
            expected_core_cells=tuple(
                ExpectedCoreCell.from_dict(cell)
                for cell in _sequence(
                    document["expected_core_cells"],
                    label="expected_core_cells",
                )
            ),
            expected_cells=tuple(
                ExpectedCell.from_dict(cell)
                for cell in _sequence(
                    document["expected_cells"], label="expected_cells"
                )
            ),
            expected_strata=tuple(
                ExpectedStratum.from_dict(stratum)
                for stratum in _sequence(
                    document["expected_strata"], label="expected_strata"
                )
            ),
            d2_core_confounders=tuple(
                D2CoreConfounderDeclaration.from_dict(item)
                for item in _sequence(
                    document["d2_core_confounders"],
                    label="d2_core_confounders",
                )
            ),
            gates=gates,
            authority=AuthorityBoundary.from_dict(document["authority"]),
        )
        serialized_scopes = _mapping(
            document["gate_claim_scopes"],
            label="gate_claim_scopes",
        )
        _exact_keys(
            serialized_scopes,
            set(_GATE_ORDER),
            label="gate_claim_scopes",
        )
        for gate_id, expected_scope in result.gate_claim_scopes.items():
            _constant(
                serialized_scopes[gate_id],
                expected_scope,
                label=f"gate_claim_scopes.{gate_id}",
            )
        serialized_design = EvaluationDesign.from_dict(document["evaluation_design"])
        if serialized_design != result.evaluation_design:
            raise QualificationContractError(
                "evaluation_design differs from the closed selection axes"
            )
        return result
