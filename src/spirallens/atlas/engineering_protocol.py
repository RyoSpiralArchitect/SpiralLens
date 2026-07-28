"""Strict protocol boundary for the public-example Pythia atlas smoke.

The protocol authorizes only capture of a small, explicitly enumerated
activation atlas.  It is not a subject protocol and it cannot authorize any
downstream scientific consumer.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
from pathlib import Path, PurePosixPath
import re
import struct
import subprocess
from typing import Any

import yaml
from yaml.events import AliasEvent
from yaml.nodes import MappingNode

from spirallens.access import (
    AtlasAccessPolicy,
    AtlasConsumer,
    AtlasConsumerDenied,
    ProvenanceTaint,
    require_atlas_consumer,
)
from spirallens.core.canonical import (
    canonical_json_bytes,
    canonical_json_sha256,
)


PUBLIC_EXAMPLE_PLUMBING_PROTOCOL_SCHEMA_VERSION = (
    "spirallens.public-example-plumbing-protocol.v0.1"
)
PUBLIC_EXAMPLE_PLUMBING_PROTOCOL_BINDING_SCHEMA_VERSION = (
    "spirallens.public-example-plumbing-protocol-binding.v0.1"
)
MAX_PUBLIC_EXAMPLE_PLUMBING_PROTOCOL_BYTES = 1_048_576

_REPOSITORY = "RyoSpiralArchitect/SpiralLens"
_IMPLEMENTATION_REPOSITORY_PATH = "src/spirallens/adapters/pythia.py"
_MODEL_ID = "EleutherAI/pythia-70m"
_MODEL_ARCHITECTURE = "GPTNeoXForCausalLM"
_MODEL_DIMENSIONS = {
    "num_layers": 6,
    "hidden_size": 512,
    "vocab_size": 50304,
    "num_attention_heads": 8,
    "intermediate_size": 2048,
    "max_position_embeddings": 2048,
}
_MODEL_FILE_NAMES = frozenset({"config.json", "model.safetensors"})
_RESOURCE_ESTIMATOR = "pythia-atlas-conservative-static-estimate-v0.1"
_RESOURCE_CLAIM_BOUNDARY = (
    "static-array-and-working-set-estimate-not-os-oom-guarantee"
)
_ALLOWED_CONSUMER = "atlas_integrity_validation"
_LEGACY_CONSUMER_ALIASES = {
    "candidate_extraction": AtlasConsumer.CANDIDATE_SEARCH,
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")

_ROOT_KEYS = frozenset(
    {
        "schema_version",
        "protocol_id",
        "status",
        "purpose",
        "claim_ceiling",
        "execution_class",
        "scientific_claim_eligible",
        "p1_instrument_consumed",
        "tokenizer_runtime_verified",
        "source",
        "model",
        "context_bank",
        "token_selection",
        "capture",
        "resource_budget",
        "authorizations",
        "stage_status",
        "allowed_consumers",
    }
)
_SOURCE_KEYS = frozenset(
    {
        "repository",
        "implementation_commit",
        "implementation_repository_path",
        "implementation_module_sha256",
    }
)
_MODEL_KEYS = frozenset(
    {
        "id",
        "revision",
        "architecture",
        *_MODEL_DIMENSIONS,
        "files",
    }
)
_CONTEXT_BANK_KEYS = frozenset(
    {
        "path",
        "source_sha256",
        "canonical_sha256",
        "context_id",
        "role",
        "claim_eligible",
    }
)
_TOKEN_SELECTION_KEYS = frozenset(
    {"kind", "token_ids", "token_ids_sha256"}
)
_CAPTURE_KEYS = frozenset(
    {
        "device",
        "dtype",
        "batch_size",
        "output_id",
        "observation_contract",
    }
)
_RESOURCE_KEYS = frozenset(
    {
        "estimator_id",
        "safety_factor",
        "estimated_output_bytes",
        "max_estimated_output_bytes",
        "estimated_peak_bytes",
        "max_estimated_peak_bytes",
        "claim_boundary",
    }
)
_AUTHORIZATION_CONSTANTS = {
    "example_model_access": True,
    "activation_atlas_capture": True,
    "network_access": False,
    "subject_protocol_preparation": False,
    "subject_execution": False,
    "instrument_bundle_conversion": False,
    "candidate_search": False,
    "neighbor_audit": False,
    "graph_construction": False,
    "field_estimation": False,
    "core_detection": False,
    "loop_construction": False,
    "holonomy_analysis": False,
    "winding_analysis": False,
    "semantic_analysis": False,
    "sae_analysis": False,
    "causal_analysis": False,
    "integer_output": False,
}
_STAGE_NAMES = (
    "D0",
    "D1",
    "D2",
    "D3",
    "D4",
    "D5",
    "D6",
    "D7",
    "D8",
    "subject_protocol_preparation",
    "subject_execution",
    "instrument_bundle_conversion",
    "candidate_search",
    "neighbor_audit",
    "graph_construction",
    "field_estimation",
    "core_detection",
    "loop_construction",
    "holonomy_analysis",
    "winding_analysis",
    "semantic_analysis",
    "sae_analysis",
    "causal_analysis",
    "integer_output",
)
_BINDING_KEYS = frozenset(
    {
        "schema_version",
        "source_sha256",
        "canonical_sha256",
        "content",
        "resource_preflight",
        "execution_preflight",
        "model_files_verified",
        "interpretation_contract",
    }
)
_EXECUTION_PREFLIGHT_KEYS = frozenset(
    {
        "status",
        "estimator_id",
        "model_file_bytes",
        "minimum_peak_bytes",
        "free_disk_bytes",
        "physical_memory_bytes",
        "disk_reserve_bytes",
    }
)
_INTERPRETATION_CONTRACT = {
    "scientific_claim_eligible": False,
    "p1_instrument_consumed": False,
    "tokenizer_runtime_verified": False,
    "language_space_atlas": False,
    "semantic_unit": False,
}


class PublicExamplePlumbingProtocolError(ValueError):
    """Base class for public-example protocol failures."""


class PublicExamplePlumbingProtocolSchemaError(
    PublicExamplePlumbingProtocolError
):
    """Raised for YAML or semantic content outside the closed schema."""


class PublicExamplePlumbingProtocolIntegrityError(
    PublicExamplePlumbingProtocolError
):
    """Raised when a source, canonical, or implementation digest differs."""


class EngineeringConsumerAuthorizationError(PermissionError):
    """Raised when a bound engineering atlas reaches a forbidden consumer."""


class _StrictSafeLoader(yaml.SafeLoader):
    def compose_node(self, parent: Any, index: Any) -> Any:
        if self.check_event(AliasEvent):
            raise PublicExamplePlumbingProtocolSchemaError(
                "YAML aliases are not allowed"
            )
        return super().compose_node(parent, index)


def _construct_mapping(
    loader: _StrictSafeLoader,
    node: MappingNode,
    deep: bool = False,
) -> dict[str, Any]:
    if not isinstance(node, MappingNode):
        raise PublicExamplePlumbingProtocolSchemaError(
            "expected a YAML mapping"
        )
    result: dict[str, Any] = {}
    for key_node, value_node in node.value:
        if key_node.tag == "tag:yaml.org,2002:merge":
            raise PublicExamplePlumbingProtocolSchemaError(
                "YAML merge keys are not allowed"
            )
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise PublicExamplePlumbingProtocolSchemaError(
                "all YAML mapping keys must be strings"
            )
        if key in result:
            raise PublicExamplePlumbingProtocolSchemaError(
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
        raise PublicExamplePlumbingProtocolSchemaError(
            f"{label} must be a mapping"
        )
    if any(not isinstance(key, str) for key in value):
        raise PublicExamplePlumbingProtocolSchemaError(
            f"{label} keys must be strings"
        )
    return value


def _exact_keys(
    value: Mapping[str, object],
    expected: frozenset[str] | set[str],
    *,
    label: str,
) -> None:
    actual = set(value)
    if actual != set(expected):
        raise PublicExamplePlumbingProtocolSchemaError(
            f"{label} fields differ from the contract: "
            f"missing={sorted(set(expected) - actual)}, "
            f"unknown={sorted(actual - set(expected))}"
        )


def _string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise PublicExamplePlumbingProtocolSchemaError(
            f"{label} must be a non-empty trimmed string"
        )
    return value


def _constant(value: object, expected: str, *, label: str) -> str:
    text = _string(value, label=label)
    if text != expected:
        raise PublicExamplePlumbingProtocolSchemaError(
            f"{label} must be exactly {expected!r}"
        )
    return text


def _boolean_constant(value: object, expected: bool, *, label: str) -> bool:
    if type(value) is not bool or value is not expected:
        raise PublicExamplePlumbingProtocolSchemaError(
            f"{label} must be {str(expected).lower()}"
        )
    return expected


def _integer(value: object, *, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PublicExamplePlumbingProtocolSchemaError(
            f"{label} must be an integer"
        )
    if value < minimum:
        raise PublicExamplePlumbingProtocolSchemaError(
            f"{label} must be >= {minimum}"
        )
    return value


def _integer_constant(value: object, expected: int, *, label: str) -> int:
    parsed = _integer(value, label=label)
    if parsed != expected:
        raise PublicExamplePlumbingProtocolSchemaError(
            f"{label} must be exactly {expected}"
        )
    return parsed


def _exact_scalar_equal(value: object, expected: object) -> bool:
    return type(value) is type(expected) and value == expected


def _sha256(value: object, *, label: str) -> str:
    text = _string(value, label=label)
    if _SHA256.fullmatch(text) is None:
        raise PublicExamplePlumbingProtocolSchemaError(
            f"{label} must be a lowercase SHA-256 digest"
        )
    return text


def _commit(value: object, *, label: str) -> str:
    text = _string(value, label=label)
    if _COMMIT.fullmatch(text) is None:
        raise PublicExamplePlumbingProtocolSchemaError(
            f"{label} must be a lowercase 40-hex commit"
        )
    return text


def _slug(value: object, *, label: str) -> str:
    text = _string(value, label=label)
    if _SLUG.fullmatch(text) is None:
        raise PublicExamplePlumbingProtocolSchemaError(
            f"{label} must be a lowercase slug"
        )
    return text


def _repository_relative_path(value: object, *, label: str) -> str:
    text = _string(value, label=label)
    candidate = PurePosixPath(text)
    if (
        "\x00" in text
        or "\\" in text
        or candidate.is_absolute()
        or candidate.as_posix() != text
        or text in {".", ".."}
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise PublicExamplePlumbingProtocolSchemaError(
            f"{label} must be a normalized repository-relative POSIX path"
        )
    return text


def token_ids_little_endian_i8_sha256(token_ids: tuple[int, ...]) -> str:
    """Digest explicit IDs as contiguous signed little-endian int64 values."""

    payload = b"".join(struct.pack("<q", token_id) for token_id in token_ids)
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class EngineeringSource:
    repository: str
    implementation_commit: str
    implementation_repository_path: str
    implementation_module_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "repository": self.repository,
            "implementation_commit": self.implementation_commit,
            "implementation_repository_path": (
                self.implementation_repository_path
            ),
            "implementation_module_sha256": self.implementation_module_sha256,
        }


@dataclass(frozen=True, slots=True)
class EngineeringModel:
    model_id: str
    revision: str
    architecture: str
    num_layers: int
    hidden_size: int
    vocab_size: int
    num_attention_heads: int
    intermediate_size: int
    max_position_embeddings: int
    files: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.model_id,
            "revision": self.revision,
            "architecture": self.architecture,
            "num_layers": self.num_layers,
            "hidden_size": self.hidden_size,
            "vocab_size": self.vocab_size,
            "num_attention_heads": self.num_attention_heads,
            "intermediate_size": self.intermediate_size,
            "max_position_embeddings": self.max_position_embeddings,
            "files": dict(self.files),
        }


@dataclass(frozen=True, slots=True)
class EngineeringContextBank:
    path: str
    source_sha256: str
    canonical_sha256: str
    context_id: str
    role: str
    claim_eligible: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "source_sha256": self.source_sha256,
            "canonical_sha256": self.canonical_sha256,
            "context_id": self.context_id,
            "role": self.role,
            "claim_eligible": self.claim_eligible,
        }


@dataclass(frozen=True, slots=True)
class EngineeringTokenSelection:
    kind: str
    token_ids: tuple[int, ...]
    token_ids_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "token_ids": list(self.token_ids),
            "token_ids_sha256": self.token_ids_sha256,
        }


@dataclass(frozen=True, slots=True)
class EngineeringCapture:
    device: str
    dtype: str
    batch_size: int
    output_id: str
    observation_contract: str

    def to_dict(self) -> dict[str, object]:
        return {
            "device": self.device,
            "dtype": self.dtype,
            "batch_size": self.batch_size,
            "output_id": self.output_id,
            "observation_contract": self.observation_contract,
        }


@dataclass(frozen=True, slots=True)
class EngineeringResourceBudget:
    estimator_id: str
    safety_factor: int
    estimated_output_bytes: int
    max_estimated_output_bytes: int
    estimated_peak_bytes: int
    max_estimated_peak_bytes: int
    claim_boundary: str

    def to_dict(self) -> dict[str, object]:
        return {
            "estimator_id": self.estimator_id,
            "safety_factor": self.safety_factor,
            "estimated_output_bytes": self.estimated_output_bytes,
            "max_estimated_output_bytes": self.max_estimated_output_bytes,
            "estimated_peak_bytes": self.estimated_peak_bytes,
            "max_estimated_peak_bytes": self.max_estimated_peak_bytes,
            "claim_boundary": self.claim_boundary,
        }

    def preflight_dict(self) -> dict[str, object]:
        return {"status": "pass", **self.to_dict()}


@dataclass(frozen=True, slots=True)
class PublicExamplePlumbingProtocol:
    schema_version: str
    protocol_id: str
    status: str
    purpose: str
    claim_ceiling: str
    execution_class: str
    scientific_claim_eligible: bool
    p1_instrument_consumed: bool
    tokenizer_runtime_verified: bool
    source: EngineeringSource
    model: EngineeringModel
    context_bank: EngineeringContextBank
    token_selection: EngineeringTokenSelection
    capture: EngineeringCapture
    resource_budget: EngineeringResourceBudget
    authorizations: tuple[tuple[str, bool], ...]
    stage_status: tuple[tuple[str, str], ...]
    allowed_consumers: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "protocol_id": self.protocol_id,
            "status": self.status,
            "purpose": self.purpose,
            "claim_ceiling": self.claim_ceiling,
            "execution_class": self.execution_class,
            "scientific_claim_eligible": self.scientific_claim_eligible,
            "p1_instrument_consumed": self.p1_instrument_consumed,
            "tokenizer_runtime_verified": self.tokenizer_runtime_verified,
            "source": self.source.to_dict(),
            "model": self.model.to_dict(),
            "context_bank": self.context_bank.to_dict(),
            "token_selection": self.token_selection.to_dict(),
            "capture": self.capture.to_dict(),
            "resource_budget": self.resource_budget.to_dict(),
            "authorizations": dict(self.authorizations),
            "stage_status": dict(self.stage_status),
            "allowed_consumers": list(self.allowed_consumers),
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()


@dataclass(frozen=True, slots=True)
class LoadedPublicExamplePlumbingProtocol:
    protocol: PublicExamplePlumbingProtocol
    source_bytes: bytes
    source_path: Path
    source_sha256: str
    canonical_sha256: str

    def to_dict(self) -> dict[str, object]:
        return self.protocol.to_dict()

    @property
    def canonical_bytes(self) -> bytes:
        return self.protocol.canonical_bytes


def _parse_source(value: object) -> EngineeringSource:
    item = _mapping(value, label="source")
    _exact_keys(item, _SOURCE_KEYS, label="source")
    return EngineeringSource(
        repository=_constant(
            item["repository"], _REPOSITORY, label="source.repository"
        ),
        implementation_commit=_commit(
            item["implementation_commit"],
            label="source.implementation_commit",
        ),
        implementation_repository_path=_constant(
            item["implementation_repository_path"],
            _IMPLEMENTATION_REPOSITORY_PATH,
            label="source.implementation_repository_path",
        ),
        implementation_module_sha256=_sha256(
            item["implementation_module_sha256"],
            label="source.implementation_module_sha256",
        ),
    )


def _parse_model(value: object) -> EngineeringModel:
    item = _mapping(value, label="model")
    _exact_keys(item, _MODEL_KEYS, label="model")
    files = _mapping(item["files"], label="model.files")
    _exact_keys(files, _MODEL_FILE_NAMES, label="model.files")
    return EngineeringModel(
        model_id=_constant(item["id"], _MODEL_ID, label="model.id"),
        revision=_commit(item["revision"], label="model.revision"),
        architecture=_constant(
            item["architecture"],
            _MODEL_ARCHITECTURE,
            label="model.architecture",
        ),
        **{
            name: _integer_constant(
                item[name], expected, label=f"model.{name}"
            )
            for name, expected in _MODEL_DIMENSIONS.items()
        },
        files=tuple(
            (name, _sha256(files[name], label=f"model.files[{name!r}]"))
            for name in sorted(files)
        ),
    )


def _parse_context_bank(value: object) -> EngineeringContextBank:
    item = _mapping(value, label="context_bank")
    _exact_keys(item, _CONTEXT_BANK_KEYS, label="context_bank")
    return EngineeringContextBank(
        path=_repository_relative_path(
            item["path"], label="context_bank.path"
        ),
        source_sha256=_sha256(
            item["source_sha256"], label="context_bank.source_sha256"
        ),
        canonical_sha256=_sha256(
            item["canonical_sha256"], label="context_bank.canonical_sha256"
        ),
        context_id=_slug(
            item["context_id"], label="context_bank.context_id"
        ),
        role=_constant(item["role"], "example", label="context_bank.role"),
        claim_eligible=_boolean_constant(
            item["claim_eligible"],
            False,
            label="context_bank.claim_eligible",
        ),
    )


def _parse_token_selection(
    value: object, *, vocab_size: int
) -> EngineeringTokenSelection:
    item = _mapping(value, label="token_selection")
    _exact_keys(item, _TOKEN_SELECTION_KEYS, label="token_selection")
    raw_ids = item["token_ids"]
    if not isinstance(raw_ids, list) or not raw_ids:
        raise PublicExamplePlumbingProtocolSchemaError(
            "token_selection.token_ids must be a non-empty list"
        )
    token_ids = tuple(
        _integer(
            token_id,
            label=f"token_selection.token_ids[{index}]",
        )
        for index, token_id in enumerate(raw_ids)
    )
    if token_ids != tuple(sorted(set(token_ids))):
        raise PublicExamplePlumbingProtocolSchemaError(
            "token_selection.token_ids must be strictly sorted and unique"
        )
    if token_ids[-1] >= vocab_size:
        raise PublicExamplePlumbingProtocolSchemaError(
            "token_selection.token_ids contains an out-of-range model row"
        )
    declared_digest = _sha256(
        item["token_ids_sha256"],
        label="token_selection.token_ids_sha256",
    )
    actual_digest = token_ids_little_endian_i8_sha256(token_ids)
    if declared_digest != actual_digest:
        raise PublicExamplePlumbingProtocolIntegrityError(
            "token selection little-endian int64 SHA-256 mismatch"
        )
    return EngineeringTokenSelection(
        kind=_constant(
            item["kind"], "explicit_sorted_ids", label="token_selection.kind"
        ),
        token_ids=token_ids,
        token_ids_sha256=declared_digest,
    )


def _parse_capture(value: object) -> EngineeringCapture:
    item = _mapping(value, label="capture")
    _exact_keys(item, _CAPTURE_KEYS, label="capture")
    return EngineeringCapture(
        device=_constant(item["device"], "cpu", label="capture.device"),
        dtype=_constant(item["dtype"], "float32", label="capture.dtype"),
        batch_size=_integer(
            item["batch_size"], label="capture.batch_size", minimum=1
        ),
        output_id=_slug(item["output_id"], label="capture.output_id"),
        observation_contract=_constant(
            item["observation_contract"],
            "all_residual_pre_post_layers",
            label="capture.observation_contract",
        ),
    )


def _minimum_output_bytes(
    *, num_tokens: int, num_layers: int, hidden_size: int, safety_factor: int
) -> int:
    per_token = (
        8
        + (2 * num_layers * hidden_size * 4)
        + (num_layers * 2 * 4)
        + (6 * 4)
        + 8
    )
    return num_tokens * per_token * safety_factor


def _parse_resource_budget(
    value: object,
    *,
    selection: EngineeringTokenSelection,
    model: EngineeringModel,
) -> EngineeringResourceBudget:
    item = _mapping(value, label="resource_budget")
    _exact_keys(item, _RESOURCE_KEYS, label="resource_budget")
    safety_factor = _integer_constant(
        item["safety_factor"], 4, label="resource_budget.safety_factor"
    )
    estimated_output = _integer(
        item["estimated_output_bytes"],
        label="resource_budget.estimated_output_bytes",
        minimum=1,
    )
    maximum_output = _integer(
        item["max_estimated_output_bytes"],
        label="resource_budget.max_estimated_output_bytes",
        minimum=1,
    )
    estimated_peak = _integer(
        item["estimated_peak_bytes"],
        label="resource_budget.estimated_peak_bytes",
        minimum=1,
    )
    maximum_peak = _integer(
        item["max_estimated_peak_bytes"],
        label="resource_budget.max_estimated_peak_bytes",
        minimum=1,
    )
    minimum_output = _minimum_output_bytes(
        num_tokens=len(selection.token_ids),
        num_layers=model.num_layers,
        hidden_size=model.hidden_size,
        safety_factor=safety_factor,
    )
    if (
        estimated_output < minimum_output
        or estimated_output > maximum_output
        or estimated_peak < estimated_output
        or estimated_peak > maximum_peak
    ):
        raise PublicExamplePlumbingProtocolSchemaError(
            "resource_budget is not a conservative passing receipt"
        )
    return EngineeringResourceBudget(
        estimator_id=_constant(
            item["estimator_id"],
            _RESOURCE_ESTIMATOR,
            label="resource_budget.estimator_id",
        ),
        safety_factor=safety_factor,
        estimated_output_bytes=estimated_output,
        max_estimated_output_bytes=maximum_output,
        estimated_peak_bytes=estimated_peak,
        max_estimated_peak_bytes=maximum_peak,
        claim_boundary=_constant(
            item["claim_boundary"],
            _RESOURCE_CLAIM_BOUNDARY,
            label="resource_budget.claim_boundary",
        ),
    )


def public_example_plumbing_protocol_from_dict(
    value: Mapping[str, object],
) -> PublicExamplePlumbingProtocol:
    """Parse an exact JSON-like public-example engineering protocol."""

    document = _mapping(value, label="public-example plumbing protocol")
    _exact_keys(document, _ROOT_KEYS, label="public-example plumbing protocol")
    model = _parse_model(document["model"])
    selection = _parse_token_selection(
        document["token_selection"], vocab_size=model.vocab_size
    )
    authorizations = _mapping(
        document["authorizations"], label="authorizations"
    )
    _exact_keys(
        authorizations, set(_AUTHORIZATION_CONSTANTS), label="authorizations"
    )
    parsed_authorizations = tuple(
        (
            name,
            _boolean_constant(
                authorizations[name],
                expected,
                label=f"authorizations.{name}",
            ),
        )
        for name, expected in _AUTHORIZATION_CONSTANTS.items()
    )
    stages = _mapping(document["stage_status"], label="stage_status")
    _exact_keys(stages, set(_STAGE_NAMES), label="stage_status")
    parsed_stages = tuple(
        (
            name,
            _constant(
                stages[name], "not_run", label=f"stage_status.{name}"
            ),
        )
        for name in _STAGE_NAMES
    )
    raw_consumers = document["allowed_consumers"]
    if raw_consumers != [_ALLOWED_CONSUMER]:
        raise PublicExamplePlumbingProtocolSchemaError(
            "allowed_consumers must contain only "
            f"{_ALLOWED_CONSUMER!r}"
        )
    return PublicExamplePlumbingProtocol(
        schema_version=_constant(
            document["schema_version"],
            PUBLIC_EXAMPLE_PLUMBING_PROTOCOL_SCHEMA_VERSION,
            label="schema_version",
        ),
        protocol_id=_slug(document["protocol_id"], label="protocol_id"),
        status=_constant(
            document["status"], "frozen_engineering", label="status"
        ),
        purpose=_constant(
            document["purpose"],
            "public_example_capture_plumbing",
            label="purpose",
        ),
        claim_ceiling=_constant(
            document["claim_ceiling"], "level_0", label="claim_ceiling"
        ),
        execution_class=_constant(
            document["execution_class"],
            "public_example_engineering",
            label="execution_class",
        ),
        scientific_claim_eligible=_boolean_constant(
            document["scientific_claim_eligible"],
            False,
            label="scientific_claim_eligible",
        ),
        p1_instrument_consumed=_boolean_constant(
            document["p1_instrument_consumed"],
            False,
            label="p1_instrument_consumed",
        ),
        tokenizer_runtime_verified=_boolean_constant(
            document["tokenizer_runtime_verified"],
            False,
            label="tokenizer_runtime_verified",
        ),
        source=_parse_source(document["source"]),
        model=model,
        context_bank=_parse_context_bank(document["context_bank"]),
        token_selection=selection,
        capture=_parse_capture(document["capture"]),
        resource_budget=_parse_resource_budget(
            document["resource_budget"], selection=selection, model=model
        ),
        authorizations=parsed_authorizations,
        stage_status=parsed_stages,
        allowed_consumers=(_ALLOWED_CONSUMER,),
    )


def load_public_example_plumbing_protocol(
    path: str | Path,
    *,
    expected_source_sha256: str | None = None,
    expected_canonical_sha256: str | None = None,
) -> LoadedPublicExamplePlumbingProtocol:
    """Load strict UTF-8 YAML and bind both source and canonical identities."""

    source_path = Path(path).resolve()
    with source_path.open("rb") as handle:
        source_bytes = handle.read(
            MAX_PUBLIC_EXAMPLE_PLUMBING_PROTOCOL_BYTES + 1
        )
    if len(source_bytes) > MAX_PUBLIC_EXAMPLE_PLUMBING_PROTOCOL_BYTES:
        raise PublicExamplePlumbingProtocolSchemaError(
            "public-example plumbing protocol exceeds the size limit"
        )
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    if (
        expected_source_sha256 is not None
        and source_sha256 != expected_source_sha256
    ):
        raise PublicExamplePlumbingProtocolIntegrityError(
            "public-example protocol source SHA-256 mismatch"
        )
    try:
        text = source_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise PublicExamplePlumbingProtocolSchemaError(
            "public-example plumbing protocol must be UTF-8 YAML"
        ) from error
    try:
        document = yaml.load(text, Loader=_StrictSafeLoader)
    except PublicExamplePlumbingProtocolSchemaError:
        raise
    except yaml.YAMLError as error:
        raise PublicExamplePlumbingProtocolSchemaError(
            f"invalid public-example plumbing YAML: {error}"
        ) from error
    if not isinstance(document, Mapping):
        raise PublicExamplePlumbingProtocolSchemaError(
            "public-example plumbing protocol must be a mapping"
        )
    protocol = public_example_plumbing_protocol_from_dict(document)
    canonical_sha256 = protocol.canonical_sha256
    if (
        expected_canonical_sha256 is not None
        and canonical_sha256 != expected_canonical_sha256
    ):
        raise PublicExamplePlumbingProtocolIntegrityError(
            "public-example protocol canonical SHA-256 mismatch"
        )
    return LoadedPublicExamplePlumbingProtocol(
        protocol=protocol,
        source_bytes=source_bytes,
        source_path=source_path,
        source_sha256=source_sha256,
        canonical_sha256=canonical_sha256,
    )


def _build_public_example_plumbing_protocol_binding(
    loaded: LoadedPublicExamplePlumbingProtocol,
    *,
    verified_model_files: Mapping[str, str],
    execution_preflight: Mapping[str, object],
) -> dict[str, object]:
    """Build a binding only after the caller observed the exact model blobs."""

    if not isinstance(loaded, LoadedPublicExamplePlumbingProtocol):
        raise TypeError("loaded must be a LoadedPublicExamplePlumbingProtocol")
    protocol = loaded.protocol
    observed = _mapping(
        verified_model_files,
        label="verified_model_files",
    )
    _exact_keys(
        observed,
        _MODEL_FILE_NAMES,
        label="verified_model_files",
    )
    parsed_observed = {
        name: _sha256(
            observed[name],
            label=f"verified_model_files[{name!r}]",
        )
        for name in sorted(observed)
    }
    if parsed_observed != dict(protocol.model.files):
        raise PublicExamplePlumbingProtocolIntegrityError(
            "observed model file hashes differ from the frozen protocol"
        )
    parsed_preflight = _validate_execution_preflight(
        execution_preflight,
        protocol=protocol,
    )
    return {
        "schema_version": (
            PUBLIC_EXAMPLE_PLUMBING_PROTOCOL_BINDING_SCHEMA_VERSION
        ),
        "source_sha256": loaded.source_sha256,
        "canonical_sha256": loaded.canonical_sha256,
        "content": protocol.to_dict(),
        "resource_preflight": protocol.resource_budget.preflight_dict(),
        "execution_preflight": parsed_preflight,
        "model_files_verified": parsed_observed,
        "interpretation_contract": dict(_INTERPRETATION_CONTRACT),
    }


def public_example_plumbing_protocol_binding_sha256(
    binding: Mapping[str, object],
) -> str:
    return canonical_json_sha256(binding)


def _validate_execution_preflight(
    value: object,
    *,
    protocol: PublicExamplePlumbingProtocol,
) -> dict[str, object]:
    item = _mapping(value, label="execution_preflight")
    _exact_keys(
        item,
        _EXECUTION_PREFLIGHT_KEYS,
        label="execution_preflight",
    )
    parsed: dict[str, object] = {
        "status": _constant(
            item["status"],
            "pass",
            label="execution_preflight.status",
        ),
        "estimator_id": _constant(
            item["estimator_id"],
            _RESOURCE_ESTIMATOR,
            label="execution_preflight.estimator_id",
        ),
    }
    for name in (
        "model_file_bytes",
        "minimum_peak_bytes",
        "free_disk_bytes",
        "physical_memory_bytes",
        "disk_reserve_bytes",
    ):
        parsed[name] = _integer(
            item[name],
            label=f"execution_preflight.{name}",
            minimum=1,
        )
    budget = protocol.resource_budget
    if (
        parsed["minimum_peak_bytes"] > budget.estimated_peak_bytes
        or parsed["free_disk_bytes"]
        < budget.max_estimated_output_bytes
        + parsed["disk_reserve_bytes"]
        or parsed["physical_memory_bytes"]
        < budget.max_estimated_peak_bytes
        or parsed["model_file_bytes"] > parsed["minimum_peak_bytes"]
    ):
        raise PublicExamplePlumbingProtocolIntegrityError(
            "execution resource preflight does not satisfy the frozen budget"
        )
    return parsed


def _validated_binding(
    request: Mapping[str, object],
) -> PublicExamplePlumbingProtocol | None:
    binding = request.get("public_example_plumbing_protocol_binding")
    digest = request.get("public_example_plumbing_protocol_binding_sha256")
    if binding is None and digest is None:
        return None
    if not isinstance(binding, Mapping):
        raise PublicExamplePlumbingProtocolIntegrityError(
            "public-example protocol binding must be a mapping"
        )
    _exact_keys(binding, _BINDING_KEYS, label="protocol binding")
    expected_digest = _sha256(
        digest, label="public_example_plumbing_protocol_binding_sha256"
    )
    if canonical_json_sha256(binding) != expected_digest:
        raise PublicExamplePlumbingProtocolIntegrityError(
            "public-example protocol binding SHA-256 mismatch"
        )
    _constant(
        binding["schema_version"],
        PUBLIC_EXAMPLE_PLUMBING_PROTOCOL_BINDING_SCHEMA_VERSION,
        label="protocol binding schema_version",
    )
    content = _mapping(binding["content"], label="protocol binding content")
    protocol = public_example_plumbing_protocol_from_dict(content)
    execution_preflight = _validate_execution_preflight(
        binding["execution_preflight"],
        protocol=protocol,
    )
    interpretation = _mapping(
        binding["interpretation_contract"],
        label="protocol binding interpretation_contract",
    )
    _exact_keys(
        interpretation,
        set(_INTERPRETATION_CONTRACT),
        label="protocol binding interpretation_contract",
    )
    parsed_interpretation = {
        name: _boolean_constant(
            interpretation[name],
            expected,
            label=f"protocol binding interpretation_contract.{name}",
        )
        for name, expected in _INTERPRETATION_CONTRACT.items()
    }
    if (
        _sha256(
            binding["canonical_sha256"],
            label="protocol binding canonical_sha256",
        )
        != protocol.canonical_sha256
        or binding["resource_preflight"]
        != protocol.resource_budget.preflight_dict()
        or binding["execution_preflight"] != execution_preflight
        or binding["model_files_verified"] != dict(protocol.model.files)
        or parsed_interpretation != _INTERPRETATION_CONTRACT
    ):
        raise PublicExamplePlumbingProtocolIntegrityError(
            "public-example protocol binding content is internally inconsistent"
        )
    _sha256(binding["source_sha256"], label="protocol binding source_sha256")
    return protocol


def validate_engineering_request_binding(
    request: Mapping[str, object],
    manifest_model: Mapping[str, object] | None = None,
) -> PublicExamplePlumbingProtocol | None:
    """Purely validate a request's protocol binding and cross-field identity.

    Legacy requests without either binding field remain valid and return
    ``None``.  A partially present or malformed binding fails closed.
    """

    if not isinstance(request, Mapping):
        raise TypeError("request must be a mapping")
    protocol = _validated_binding(request)
    if protocol is None:
        return None
    model = protocol.model
    selection = protocol.token_selection
    capture = protocol.capture
    expected_request_fields = {
        "model_id": model.model_id,
        "requested_model_revision": model.revision,
        "resolved_model_revision": model.revision,
        "config_blob_sha256": dict(model.files)["config.json"],
        "model_blob_sha256": dict(model.files)["model.safetensors"],
        "num_tokens": len(selection.token_ids),
        "token_ids_sha256": selection.token_ids_sha256,
        "batch_size_initial": capture.batch_size,
        "capture_dtype": capture.dtype,
        "output_id": capture.output_id,
        "language_space_atlas": False,
        "semantic_unit": False,
    }
    mismatched = [
        name
        for name, expected in expected_request_fields.items()
        if not _exact_scalar_equal(request.get(name), expected)
    ]
    latest = request.get("batch_size_latest")
    if (
        isinstance(latest, bool)
        or not isinstance(latest, int)
        or not 1 <= latest <= capture.batch_size
    ):
        mismatched.append("batch_size_latest")
    selection_request = request.get("selection")
    if not isinstance(selection_request, Mapping) or (
        not _exact_scalar_equal(
            selection_request.get("kind"),
            "subset",
        )
        or not _exact_scalar_equal(
            selection_request.get("subset_size_before_limit"),
            len(selection.token_ids),
        )
        or selection_request.get("max_tokens") is not None
    ):
        mismatched.append("selection")
    context_binding = request.get("context_bank_binding")
    if not isinstance(context_binding, Mapping):
        mismatched.append("context_bank_binding")
    else:
        bank = context_binding.get("bank")
        selected = context_binding.get("selected_context")
        bank_content = bank.get("content") if isinstance(bank, Mapping) else None
        if (
            not isinstance(bank, Mapping)
            or bank.get("source_sha256")
            != protocol.context_bank.source_sha256
            or bank.get("canonical_sha256")
            != protocol.context_bank.canonical_sha256
            or not isinstance(bank_content, Mapping)
            or bank_content.get("claim_eligible") is not False
            or not isinstance(selected, Mapping)
            or selected.get("context_id") != protocol.context_bank.context_id
            or selected.get("role") != "example"
        ):
            mismatched.append("context_bank_binding")
    if manifest_model is not None:
        if not isinstance(manifest_model, Mapping):
            raise TypeError("manifest_model must be a mapping")
        model_expected = {
            "model_id": model.model_id,
            "requested_revision": model.revision,
            "resolved_revision": model.revision,
            "architecture": model.architecture,
            "num_layers": model.num_layers,
            "hidden_size": model.hidden_size,
            "vocab_size": model.vocab_size,
        }
        if any(
            not _exact_scalar_equal(
                manifest_model.get(name),
                expected,
            )
            for name, expected in model_expected.items()
        ):
            mismatched.append("manifest_model")
        if manifest_model.get("parameter_devices") != ["cpu"]:
            mismatched.append("manifest_model.parameter_devices")
        if manifest_model.get("parameter_dtypes") != ["float32"]:
            mismatched.append("manifest_model.parameter_dtypes")
    if mismatched:
        raise PublicExamplePlumbingProtocolIntegrityError(
            "atlas request differs from its public-example protocol: "
            + ", ".join(sorted(set(mismatched)))
        )
    return protocol


def require_engineering_consumer_authorized(
    request: Mapping[str, object],
    consumer: AtlasConsumer | str,
) -> None:
    """Apply the generic monotone policy to a bound engineering atlas.

    String consumers remain accepted for the historical CLI call sites. New
    library consumers should pass :class:`~spirallens.access.AtlasConsumer`.
    Unbound historical atlases retain their pre-v0.1 compatibility behavior.
    """

    if isinstance(consumer, AtlasConsumer):
        consumer_name = consumer.value
    else:
        consumer_name = _string(consumer, label="consumer")
    protocol = _validated_binding(request)
    if protocol is None:
        return
    try:
        typed_consumer = (
            _LEGACY_CONSUMER_ALIASES[consumer_name]
            if consumer_name in _LEGACY_CONSUMER_ALIASES
            else AtlasConsumer(consumer_name)
        )
    except ValueError as error:
        raise EngineeringConsumerAuthorizationError(
            f"bound public-example atlas does not authorize "
            f"{consumer_name!r}; "
            f"only {_ALLOWED_CONSUMER!r} is allowed"
        ) from error
    policy = AtlasAccessPolicy(
        origin_execution_class=protocol.execution_class,
        claim_ceiling=protocol.claim_ceiling,
        scientific_claim_eligible=protocol.scientific_claim_eligible,
        allowed_consumers=frozenset(
            AtlasConsumer(item) for item in protocol.allowed_consumers
        ),
        provenance_taints=frozenset(
            {
                ProvenanceTaint.PUBLIC_EXAMPLE_ENGINEERING,
                ProvenanceTaint.CLAIM_INELIGIBLE_CONTEXT,
                ProvenanceTaint.INSTRUMENT_UNQUALIFIED,
            }
        ),
    )
    try:
        require_atlas_consumer(policy, typed_consumer)
    except AtlasConsumerDenied as error:
        raise EngineeringConsumerAuthorizationError(
            f"bound public-example atlas does not authorize "
            f"{consumer_name!r}; "
            f"only {_ALLOWED_CONSUMER!r} is allowed"
        ) from error


def resolve_repository_relative_path(
    repository_root: str | Path, relative_path: str
) -> Path:
    """Resolve a validated protocol path without permitting root escape."""

    normalized = _repository_relative_path(
        relative_path, label="repository-relative path"
    )
    root = Path(repository_root).resolve(strict=True)
    resolved = (root / normalized).resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise PublicExamplePlumbingProtocolIntegrityError(
            "repository-relative path escapes the repository root"
        )
    return resolved


def verify_implementation_source(
    loaded: LoadedPublicExamplePlumbingProtocol,
    repository_root: str | Path,
) -> None:
    """Verify the bound adapter blob directly from the committed git object."""

    if not isinstance(loaded, LoadedPublicExamplePlumbingProtocol):
        raise TypeError("loaded must be a LoadedPublicExamplePlumbingProtocol")
    root = Path(repository_root).resolve(strict=True)
    source = loaded.protocol.source
    try:
        top_level = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if Path(top_level).resolve(strict=True) != root:
            raise PublicExamplePlumbingProtocolIntegrityError(
                "repository_root is not the git worktree root"
            )
        subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "cat-file",
                "-e",
                f"{source.implementation_commit}^{{commit}}",
            ],
            check=True,
            capture_output=True,
        )
        module_bytes = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "show",
                (
                    f"{source.implementation_commit}:"
                    f"{source.implementation_repository_path}"
                ),
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
                source.implementation_commit,
                "--",
                "src/spirallens",
            ],
            check=True,
            capture_output=True,
        )
        source_status = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "status",
                "--porcelain",
                "--untracked-files=all",
                "--",
                "src/spirallens",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise PublicExamplePlumbingProtocolIntegrityError(
            "cannot resolve the bound implementation commit/blob"
        ) from error
    if hashlib.sha256(module_bytes).hexdigest() != (
        source.implementation_module_sha256
    ):
        raise PublicExamplePlumbingProtocolIntegrityError(
            "bound implementation module SHA-256 mismatch"
        )
    if source_status:
        raise PublicExamplePlumbingProtocolIntegrityError(
            "current SpiralLens source tree differs from the bound "
            "implementation commit"
        )
    current_module = resolve_repository_relative_path(
        root,
        source.implementation_repository_path,
    )
    if hashlib.sha256(current_module.read_bytes()).hexdigest() != (
        source.implementation_module_sha256
    ):
        raise PublicExamplePlumbingProtocolIntegrityError(
            "current implementation module differs from the bound blob"
        )
