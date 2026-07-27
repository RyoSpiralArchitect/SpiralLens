"""Strict tracked protocol contract for representation-shaped phantoms.

This module deliberately stops at protocol parsing and identity.  It does not
run a generator, resolve the bound registry, or authorize subject/model access.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path, PurePosixPath
import re
from typing import Any

import yaml
from yaml.events import AliasEvent
from yaml.nodes import MappingNode

from spirallens.instrument_contracts.canonical import canonical_json_bytes


REPRESENTATION_PHANTOM_PROTOCOL_SCHEMA_VERSION = (
    "spirallens.representation-phantom-protocol.v0.1"
)
MAX_REPRESENTATION_PHANTOM_PROTOCOL_BYTES = 1_048_576

_REPOSITORY = "RyoSpiralArchitect/SpiralLens"
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")

_ROOT_KEYS = frozenset(
    {
        "schema_version",
        "protocol_id",
        "status",
        "claim_ceiling",
        "qualification_status",
        "source",
        "generator",
        "cases",
        "registry",
        "execution",
    }
)
_SOURCE_KEYS = frozenset(
    {
        "repository",
        "generator_revision",
        "generator_module_sha256",
    }
)
_GENERATOR_KEYS = frozenset(
    {
        "seed",
        "grid_side",
        "ambient_dimension",
        "probe_count",
        "neighbor_count",
        "radial_scale",
        "probe_scale",
        "nuisance_scale",
    }
)
_CASE_KEYS = frozenset({"case_id", "field_kind"})
_REGISTRY_KEYS = frozenset({"path", "source_sha256", "canonical_sha256"})
_EXECUTION_KEYS = frozenset(
    {
        "fit_role",
        "context_kind",
        "synthetic_context_claim_eligible",
        "model_access_authorized",
        "subject_data_access_authorized",
        "subject_execution_authorized",
        "subject_protocol_preparation_authorized",
        "calibration_selection_authorized",
        "integer_output_authorized",
    }
)
_EXPECTED_CASES = (
    ("angular-section-positive", "angular-unit-vector"),
    ("fixed-direction-null", "fixed-unit-vector"),
)


class RepresentationPhantomProtocolError(ValueError):
    """Base class for representation-phantom protocol failures."""


class RepresentationPhantomProtocolSchemaError(RepresentationPhantomProtocolError):
    """Raised when YAML or parsed content is outside the closed schema."""


class RepresentationPhantomProtocolIntegrityError(
    RepresentationPhantomProtocolError
):
    """Raised when source or canonical content fails an expected digest."""


class _StrictSafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects aliases before construction."""

    def compose_node(self, parent: Any, index: Any) -> Any:
        if self.check_event(AliasEvent):
            raise RepresentationPhantomProtocolSchemaError(
                "YAML aliases are not allowed"
            )
        return super().compose_node(parent, index)


def _construct_mapping(
    loader: _StrictSafeLoader,
    node: MappingNode,
    deep: bool = False,
) -> dict[str, Any]:
    if not isinstance(node, MappingNode):
        raise RepresentationPhantomProtocolSchemaError(
            "expected a YAML mapping"
        )
    result: dict[str, Any] = {}
    for key_node, value_node in node.value:
        if key_node.tag == "tag:yaml.org,2002:merge":
            raise RepresentationPhantomProtocolSchemaError(
                "YAML merge keys are not allowed"
            )
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise RepresentationPhantomProtocolSchemaError(
                "all YAML mapping keys must be strings"
            )
        if key in result:
            raise RepresentationPhantomProtocolSchemaError(
                f"duplicate YAML key {key!r}"
            )
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_StrictSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


def _mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RepresentationPhantomProtocolSchemaError(
            f"{label} must be a mapping"
        )
    if any(not isinstance(key, str) for key in value):
        raise RepresentationPhantomProtocolSchemaError(
            f"{label} keys must be strings"
        )
    return value


def _exact_keys(
    value: Mapping[str, object],
    expected: frozenset[str],
    *,
    label: str,
) -> None:
    actual = set(value)
    if actual != set(expected):
        raise RepresentationPhantomProtocolSchemaError(
            f"{label} fields differ from the contract: "
            f"missing={sorted(set(expected) - actual)}, "
            f"unknown={sorted(actual - set(expected))}"
        )


def _string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise RepresentationPhantomProtocolSchemaError(
            f"{label} must be a non-empty string"
        )
    if value != value.strip():
        raise RepresentationPhantomProtocolSchemaError(
            f"{label} must not have surrounding whitespace"
        )
    return value


def _constant(value: object, expected: str, *, label: str) -> str:
    text = _string(value, label=label)
    if text != expected:
        raise RepresentationPhantomProtocolSchemaError(
            f"{label} must be exactly {expected!r}"
        )
    return text


def _slug(value: object, *, label: str) -> str:
    text = _string(value, label=label)
    if _SLUG.fullmatch(text) is None:
        raise RepresentationPhantomProtocolSchemaError(
            f"{label} must be a lowercase slug"
        )
    return text


def _sha256(value: object, *, label: str) -> str:
    text = _string(value, label=label)
    if _SHA256.fullmatch(text) is None:
        raise RepresentationPhantomProtocolSchemaError(
            f"{label} must be a lowercase SHA-256 digest"
        )
    return text


def _commit(value: object, *, label: str) -> str:
    text = _string(value, label=label)
    if _COMMIT.fullmatch(text) is None:
        raise RepresentationPhantomProtocolSchemaError(
            f"{label} must be a lowercase 40-hex revision"
        )
    return text


def _integer(value: object, *, label: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RepresentationPhantomProtocolSchemaError(
            f"{label} must be an integer"
        )
    if value < minimum:
        raise RepresentationPhantomProtocolSchemaError(
            f"{label} must be >= {minimum}"
        )
    return value


def _float(value: object, *, label: str, minimum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, float):
        raise RepresentationPhantomProtocolSchemaError(
            f"{label} must be a floating-point number"
        )
    if not math.isfinite(value) or value < minimum:
        raise RepresentationPhantomProtocolSchemaError(
            f"{label} must be finite and >= {minimum}"
        )
    if value == 0.0 and math.copysign(1.0, value) < 0.0:
        raise RepresentationPhantomProtocolSchemaError(
            f"{label} must not be negative zero"
        )
    return value


def _false(value: object, *, label: str) -> bool:
    if type(value) is not bool:
        raise RepresentationPhantomProtocolSchemaError(
            f"{label} must be a boolean"
        )
    if value:
        raise RepresentationPhantomProtocolSchemaError(
            f"{label} must be false"
        )
    return value


def _normalized_relative_path(value: object, *, label: str) -> str:
    text = _string(value, label=label)
    if "\x00" in text:
        raise RepresentationPhantomProtocolSchemaError(
            f"{label} must not contain NUL"
        )
    if "\\" in text:
        raise RepresentationPhantomProtocolSchemaError(
            f"{label} must use normalized POSIX separators"
        )
    candidate = PurePosixPath(text)
    if (
        candidate.is_absolute()
        or candidate.as_posix() != text
        or text in {".", ".."}
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise RepresentationPhantomProtocolSchemaError(
            f"{label} must be a normalized repository-relative path"
        )
    return text


@dataclass(frozen=True, slots=True)
class RepresentationPhantomSource:
    """Immutable source-code identity for one phantom generator."""

    repository: str
    generator_revision: str
    generator_module_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "repository": self.repository,
            "generator_revision": self.generator_revision,
            "generator_module_sha256": self.generator_module_sha256,
        }


@dataclass(frozen=True, slots=True)
class RepresentationPhantomGenerator:
    """Closed numeric generator configuration."""

    seed: int
    grid_side: int
    ambient_dimension: int
    probe_count: int
    neighbor_count: int
    radial_scale: float
    probe_scale: float
    nuisance_scale: float

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "grid_side": self.grid_side,
            "ambient_dimension": self.ambient_dimension,
            "probe_count": self.probe_count,
            "neighbor_count": self.neighbor_count,
            "radial_scale": self.radial_scale,
            "probe_scale": self.probe_scale,
            "nuisance_scale": self.nuisance_scale,
        }

    def to_spec(self) -> object:
        """Construct the executable spec without importing it at module load."""

        from .representation_phantom import RepresentationPhantomSpec

        return RepresentationPhantomSpec(**self.to_dict())


@dataclass(frozen=True, slots=True)
class RepresentationPhantomCase:
    """One fixed positive or null phantom case."""

    case_id: str
    field_kind: str

    def to_dict(self) -> dict[str, object]:
        return {"case_id": self.case_id, "field_kind": self.field_kind}


@dataclass(frozen=True, slots=True)
class RepresentationPhantomRegistryBinding:
    """Byte and canonical binding to the tracked P0 registry."""

    path: str
    source_sha256: str
    canonical_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "source_sha256": self.source_sha256,
            "canonical_sha256": self.canonical_sha256,
        }


@dataclass(frozen=True, slots=True)
class RepresentationPhantomExecutionBoundary:
    """Explicitly non-subject execution authority."""

    fit_role: str
    context_kind: str
    synthetic_context_claim_eligible: bool
    model_access_authorized: bool
    subject_data_access_authorized: bool
    subject_execution_authorized: bool
    subject_protocol_preparation_authorized: bool
    calibration_selection_authorized: bool
    integer_output_authorized: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "fit_role": self.fit_role,
            "context_kind": self.context_kind,
            "synthetic_context_claim_eligible": (
                self.synthetic_context_claim_eligible
            ),
            "model_access_authorized": self.model_access_authorized,
            "subject_data_access_authorized": (
                self.subject_data_access_authorized
            ),
            "subject_execution_authorized": (
                self.subject_execution_authorized
            ),
            "subject_protocol_preparation_authorized": (
                self.subject_protocol_preparation_authorized
            ),
            "calibration_selection_authorized": (
                self.calibration_selection_authorized
            ),
            "integer_output_authorized": self.integer_output_authorized,
        }


@dataclass(frozen=True, slots=True)
class RepresentationPhantomProtocol:
    """Validated semantic content of a tracked representation phantom."""

    schema_version: str
    protocol_id: str
    status: str
    claim_ceiling: str
    qualification_status: str
    source: RepresentationPhantomSource
    generator: RepresentationPhantomGenerator
    cases: tuple[RepresentationPhantomCase, ...]
    registry: RepresentationPhantomRegistryBinding
    execution: RepresentationPhantomExecutionBoundary

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "protocol_id": self.protocol_id,
            "status": self.status,
            "claim_ceiling": self.claim_ceiling,
            "qualification_status": self.qualification_status,
            "source": self.source.to_dict(),
            "generator": self.generator.to_dict(),
            "cases": [case.to_dict() for case in self.cases],
            "registry": self.registry.to_dict(),
            "execution": self.execution.to_dict(),
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()


@dataclass(frozen=True, slots=True)
class LoadedRepresentationPhantomProtocol:
    """A validated protocol plus its immutable source-byte identity."""

    protocol: RepresentationPhantomProtocol
    source_bytes: bytes
    source_path: Path
    source_sha256: str
    canonical_sha256: str

    def to_dict(self) -> dict[str, object]:
        return self.protocol.to_dict()

    @property
    def canonical_bytes(self) -> bytes:
        return self.protocol.canonical_bytes


def _parse_source(value: object) -> RepresentationPhantomSource:
    item = _mapping(value, label="source")
    _exact_keys(item, _SOURCE_KEYS, label="source")
    return RepresentationPhantomSource(
        repository=_constant(
            item["repository"],
            _REPOSITORY,
            label="source.repository",
        ),
        generator_revision=_commit(
            item["generator_revision"],
            label="source.generator_revision",
        ),
        generator_module_sha256=_sha256(
            item["generator_module_sha256"],
            label="source.generator_module_sha256",
        ),
    )


def _parse_generator(value: object) -> RepresentationPhantomGenerator:
    item = _mapping(value, label="generator")
    _exact_keys(item, _GENERATOR_KEYS, label="generator")
    generator = RepresentationPhantomGenerator(
        seed=_integer(item["seed"], label="generator.seed", minimum=0),
        grid_side=_integer(
            item["grid_side"], label="generator.grid_side", minimum=1
        ),
        ambient_dimension=_integer(
            item["ambient_dimension"],
            label="generator.ambient_dimension",
            minimum=2,
        ),
        probe_count=_integer(
            item["probe_count"], label="generator.probe_count", minimum=1
        ),
        neighbor_count=_integer(
            item["neighbor_count"],
            label="generator.neighbor_count",
            minimum=1,
        ),
        radial_scale=_float(
            item["radial_scale"], label="generator.radial_scale", minimum=0.0
        ),
        probe_scale=_float(
            item["probe_scale"], label="generator.probe_scale", minimum=0.0
        ),
        nuisance_scale=_float(
            item["nuisance_scale"],
            label="generator.nuisance_scale",
            minimum=0.0,
        ),
    )
    try:
        generator.to_spec()
    except (TypeError, ValueError) as error:
        raise RepresentationPhantomProtocolSchemaError(
            f"generator is not executable under the bound spec: {error}"
        ) from error
    return generator


def _parse_cases(value: object) -> tuple[RepresentationPhantomCase, ...]:
    if not isinstance(value, list):
        raise RepresentationPhantomProtocolSchemaError("cases must be a list")
    parsed: list[RepresentationPhantomCase] = []
    for index, raw_case in enumerate(value):
        label = f"cases[{index}]"
        item = _mapping(raw_case, label=label)
        _exact_keys(item, _CASE_KEYS, label=label)
        parsed.append(
            RepresentationPhantomCase(
                case_id=_slug(item["case_id"], label=f"{label}.case_id"),
                field_kind=_slug(
                    item["field_kind"], label=f"{label}.field_kind"
                ),
            )
        )
    identities = tuple((case.case_id, case.field_kind) for case in parsed)
    if identities != _EXPECTED_CASES:
        raise RepresentationPhantomProtocolSchemaError(
            "cases must be the exact sorted positive/null case pair"
        )
    return tuple(parsed)


def _parse_registry(value: object) -> RepresentationPhantomRegistryBinding:
    item = _mapping(value, label="registry")
    _exact_keys(item, _REGISTRY_KEYS, label="registry")
    return RepresentationPhantomRegistryBinding(
        path=_normalized_relative_path(item["path"], label="registry.path"),
        source_sha256=_sha256(
            item["source_sha256"], label="registry.source_sha256"
        ),
        canonical_sha256=_sha256(
            item["canonical_sha256"], label="registry.canonical_sha256"
        ),
    )


def _parse_execution(
    value: object,
) -> RepresentationPhantomExecutionBoundary:
    item = _mapping(value, label="execution")
    _exact_keys(item, _EXECUTION_KEYS, label="execution")
    return RepresentationPhantomExecutionBoundary(
        fit_role=_constant(
            item["fit_role"], "instrument_dev", label="execution.fit_role"
        ),
        context_kind=_constant(
            item["context_kind"],
            "synthetic_lattice",
            label="execution.context_kind",
        ),
        synthetic_context_claim_eligible=_false(
            item["synthetic_context_claim_eligible"],
            label="execution.synthetic_context_claim_eligible",
        ),
        model_access_authorized=_false(
            item["model_access_authorized"],
            label="execution.model_access_authorized",
        ),
        subject_data_access_authorized=_false(
            item["subject_data_access_authorized"],
            label="execution.subject_data_access_authorized",
        ),
        subject_execution_authorized=_false(
            item["subject_execution_authorized"],
            label="execution.subject_execution_authorized",
        ),
        subject_protocol_preparation_authorized=_false(
            item["subject_protocol_preparation_authorized"],
            label="execution.subject_protocol_preparation_authorized",
        ),
        calibration_selection_authorized=_false(
            item["calibration_selection_authorized"],
            label="execution.calibration_selection_authorized",
        ),
        integer_output_authorized=_false(
            item["integer_output_authorized"],
            label="execution.integer_output_authorized",
        ),
    )


def representation_phantom_protocol_from_dict(
    value: Mapping[str, object],
) -> RepresentationPhantomProtocol:
    """Parse one exact JSON-like protocol mapping."""

    document = _mapping(value, label="representation phantom protocol")
    _exact_keys(
        document,
        _ROOT_KEYS,
        label="representation phantom protocol",
    )
    return RepresentationPhantomProtocol(
        schema_version=_constant(
            document["schema_version"],
            REPRESENTATION_PHANTOM_PROTOCOL_SCHEMA_VERSION,
            label="schema_version",
        ),
        protocol_id=_slug(document["protocol_id"], label="protocol_id"),
        status=_constant(
            document["status"], "instrument_dev", label="status"
        ),
        claim_ceiling=_constant(
            document["claim_ceiling"], "level_0", label="claim_ceiling"
        ),
        qualification_status=_constant(
            document["qualification_status"],
            "not_evaluated",
            label="qualification_status",
        ),
        source=_parse_source(document["source"]),
        generator=_parse_generator(document["generator"]),
        cases=_parse_cases(document["cases"]),
        registry=_parse_registry(document["registry"]),
        execution=_parse_execution(document["execution"]),
    )


def load_representation_phantom_protocol(
    path: str | Path,
    *,
    expected_source_sha256: str | None = None,
    expected_canonical_sha256: str | None = None,
) -> LoadedRepresentationPhantomProtocol:
    """Load a strict, single-document tracked phantom protocol."""

    source_path = Path(path).resolve()
    with source_path.open("rb") as handle:
        source_bytes = handle.read(
            MAX_REPRESENTATION_PHANTOM_PROTOCOL_BYTES + 1
        )
    if len(source_bytes) > MAX_REPRESENTATION_PHANTOM_PROTOCOL_BYTES:
        raise RepresentationPhantomProtocolSchemaError(
            "representation phantom protocol exceeds "
            f"{MAX_REPRESENTATION_PHANTOM_PROTOCOL_BYTES} bytes"
        )
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    if (
        expected_source_sha256 is not None
        and source_sha256 != expected_source_sha256
    ):
        raise RepresentationPhantomProtocolIntegrityError(
            "representation phantom protocol source SHA-256 does not match "
            "the expected digest"
        )
    try:
        text = source_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RepresentationPhantomProtocolSchemaError(
            "representation phantom protocol must be UTF-8 YAML"
        ) from error
    try:
        document = yaml.load(text, Loader=_StrictSafeLoader)
    except RepresentationPhantomProtocolSchemaError:
        raise
    except yaml.YAMLError as error:
        raise RepresentationPhantomProtocolSchemaError(
            f"invalid representation phantom protocol YAML: {error}"
        ) from error
    if not isinstance(document, Mapping):
        raise RepresentationPhantomProtocolSchemaError(
            "representation phantom protocol must be a mapping"
        )
    protocol = representation_phantom_protocol_from_dict(document)
    canonical_sha256 = protocol.canonical_sha256
    if (
        expected_canonical_sha256 is not None
        and canonical_sha256 != expected_canonical_sha256
    ):
        raise RepresentationPhantomProtocolIntegrityError(
            "representation phantom protocol canonical SHA-256 does not "
            "match the expected digest"
        )
    return LoadedRepresentationPhantomProtocol(
        protocol=protocol,
        source_bytes=source_bytes,
        source_path=source_path,
        source_sha256=source_sha256,
        canonical_sha256=canonical_sha256,
    )
