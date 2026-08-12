"""Private, value-blind Pythia-160M pre-observation declarations.

This module validates caller declarations and performs integer-only static
resource arithmetic.  It does not resolve or verify a model identity, inspect
files or host resources, load a model or tokenizer, execute a forward pass,
observe activations, create an atlas, or grant preparation or execution
authority.  No declaration or assessment instance is shipped by the package.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import re
from types import MappingProxyType

from spirallens.core.canonical import canonical_json_bytes, canonical_json_sha256


__all__ = ()

_DECLARATION_SCHEMA_VERSION = "spirallens.pythia160-preobservation-declaration.v0.1"
_ASSESSMENT_SCHEMA_VERSION = "spirallens.pythia160-preobservation-assessment.v0.1"
_MODEL_ID = "EleutherAI/pythia-160m"
_DECLARED_UNVERIFIED = "declared_unverified"
_BLOCKED_STATUS = "blocked_external_prerequisites"
_CAPTURE_IMPLEMENTATION_VERSION = "spirallens.pythia.residual_hooks.v1"
_OBSERVATION_CONTRACT = "all_residual_pre_post_layers"
_RESOURCE_ESTIMATOR_ID = "pythia-preobservation-static-estimate-v0.1"
_DTYPE_BYTES = 4
_MAX_DECLARED_INTEGER = (1 << 63) - 1
_MAX_ESTIMATED_BYTES = (1 << 127) - 1
_MAX_DECLARED_FILES = 1024

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_DECLARATION_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_FILE_ROLES = frozenset({"auxiliary", "config", "weights"})

_BLOCKING_PREREQUISITES = (
    "adapter_hook_parity_qualification",
    "external_witness",
    "frozen_discovery_context_bank",
    "frozen_heldout_context_bank",
    "instrument_qualification",
    "pythia70_outcome_independence_review",
    "reviewed_model_file_manifest",
    "reviewed_model_identity",
    "reviewed_model_profile",
    "terminal_sci_s1_transition",
    "zero_intervention_qualification",
)

_ACCESS_FACTS = MappingProxyType(
    {
        "activation_values_accessed": False,
        "atlas_created": False,
        "atlas_manifest_read": False,
        "attempt_issued": False,
        "descriptor_read": False,
        "execution_started": False,
        "forward_executed": False,
        "hugging_face_accessed": False,
        "model_files_accessed": False,
        "model_loaded": False,
        "network_accessed": False,
        "output_created": False,
        "payload_files_read": False,
        "receipt_published": False,
        "result_produced": False,
        "subject_values_accessed": False,
        "tokenizer_loaded": False,
    }
)

_VERIFICATION_FACTS = MappingProxyType(
    {
        "adapter_hook_parity_verified": False,
        "architecture_verified": False,
        "discovery_context_bank_verified": False,
        "external_witness_verified": False,
        "heldout_context_bank_verified": False,
        "instrument_qualified": False,
        "model_dimensions_verified": False,
        "model_file_manifest_verified": False,
        "model_file_sizes_verified": False,
        "model_identity_verified": False,
        "model_profile_verified": False,
        "model_revision_verified": False,
        "parameter_layout_verified": False,
        "pythia70_outcome_independence_verified": False,
        "sci_s1_terminal_transition_verified": False,
        "zero_intervention_verified": False,
    }
)

_AUTHORITY_FACTS = MappingProxyType(
    {
        "attempt_authorized": False,
        "candidate_authority": False,
        "capture_authorized": False,
        "causal_authority": False,
        "core_authority": False,
        "d0_d8_credit": False,
        "execution_authorized": False,
        "field_authority": False,
        "graph_authority": False,
        "holonomy_authority": False,
        "instrument_authority": False,
        "integer_authority": False,
        "loop_authority": False,
        "model_access_authorized": False,
        "neighbor_authority": False,
        "pythia_access_authorized": False,
        "sae_authority": False,
        "sci_s1_completion_credit": False,
        "sci_s2_authorized": False,
        "scientific_claim_eligible": False,
        "semantic_authority": False,
        "subject_execution_authorized": False,
        "subject_manifest_authorized": False,
        "subject_preparation_authorized": False,
        "topology_authority": False,
        "voy_v3_credit": False,
        "voy_v7_credit": False,
        "winding_authority": False,
    }
)

_CLAIM_BOUNDARY = MappingProxyType(
    {
        "claim_ceiling": "level_0",
        "claim_delta": "none",
        "declaration_inputs_verified": False,
        "execution_readiness_established": False,
        "persistence_supported": False,
        "public_schema_supported": False,
        "record_scope": "in_memory_fingerprint_only",
        "resource_sufficiency_established": False,
        "sci_s1_satisfied": False,
        "sci_s2_unblocked": False,
        "scientific_result_produced": False,
    }
)


class _Pythia160PreobservationContractError(ValueError):
    """Raised when a private declaration or assessment is not exact."""


def _mapping(value: object, *, label: str) -> Mapping[str, object]:
    if type(value) is not dict:
        raise _Pythia160PreobservationContractError(
            f"{label} must be a plain string-keyed dictionary"
        )
    return value


def _exact_keys(
    value: Mapping[str, object], expected: frozenset[str], *, label: str
) -> None:
    if len(value) != len(expected):
        raise _Pythia160PreobservationContractError(
            f"{label} field count differs from the private contract"
        )
    keys = tuple(value.keys())
    if any(type(key) is not str for key in keys):
        raise _Pythia160PreobservationContractError(
            f"{label} must contain only string keys"
        )
    actual = set(keys)
    if actual != expected:
        raise _Pythia160PreobservationContractError(
            f"{label} fields differ from the private contract: "
            f"missing={sorted(expected - actual)}, "
            f"unknown={sorted(actual - expected)}"
        )


def _constant(value: object, expected: str, *, label: str) -> str:
    if type(value) is not str or value != expected:
        raise _Pythia160PreobservationContractError(f"{label} must equal {expected!r}")
    return expected


def _trimmed_string(value: object, *, label: str, maximum: int = 1024) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value) > maximum
    ):
        raise _Pythia160PreobservationContractError(
            f"{label} must be a non-empty trimmed string of at most {maximum} characters"
        )
    return value


def _positive_integer(value: object, *, label: str) -> int:
    if type(value) is not int or value < 1 or value > _MAX_DECLARED_INTEGER:
        raise _Pythia160PreobservationContractError(
            f"{label} must be a positive exact integer no greater than "
            f"{_MAX_DECLARED_INTEGER}"
        )
    return value


def _sha256(value: object, *, label: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise _Pythia160PreobservationContractError(
            f"{label} must be a lowercase SHA-256 digest"
        )
    return value


def _commit(value: object, *, label: str) -> str:
    if type(value) is not str or _COMMIT.fullmatch(value) is None:
        raise _Pythia160PreobservationContractError(
            f"{label} must be a full lowercase 40-hex revision declaration"
        )
    return value


def _bounded_estimate(value: int, *, label: str) -> int:
    if value < 1 or value > _MAX_ESTIMATED_BYTES:
        raise _Pythia160PreobservationContractError(
            f"{label} exceeds the private static-estimator bound"
        )
    return value


def _snapshot_exact_closed_mapping(
    actual: Mapping[str, object],
    expected: Mapping[str, object],
    *,
    label: str,
) -> Mapping[str, object]:
    if type(actual) is not dict:
        raise _Pythia160PreobservationContractError(
            f"assessment {label} must be a plain dictionary"
        )
    if len(actual) != len(expected):
        raise _Pythia160PreobservationContractError(
            f"assessment {label} field count differs from the closed boundary"
        )
    keys = tuple(actual.keys())
    if any(type(key) is not str for key in keys):
        raise _Pythia160PreobservationContractError(
            f"assessment {label} must be string-keyed"
        )
    snapshot = dict(actual)
    if set(snapshot) != set(expected):
        raise _Pythia160PreobservationContractError(
            f"assessment {label} fields differ from the closed boundary"
        )
    for key, expected_value in expected.items():
        actual_value = snapshot[key]
        if (
            type(actual_value) is not type(expected_value)
            or actual_value != expected_value
        ):
            raise _Pythia160PreobservationContractError(
                f"assessment {label} differs from the closed boundary"
            )
    return MappingProxyType(snapshot)


@dataclass(frozen=True, slots=True)
class _Pythia160DeclaredFile:
    role: str
    name: str
    sha256: str
    byte_count: int

    def __post_init__(self) -> None:
        if type(self.role) is not str or self.role not in _FILE_ROLES:
            raise _Pythia160PreobservationContractError(
                "model.files[].role is unsupported"
            )
        _trimmed_string(self.name, label="model.files[].name")
        _sha256(self.sha256, label="model.files[].sha256")
        _positive_integer(self.byte_count, label="model.files[].byte_count")

    def to_dict(self) -> dict[str, object]:
        return {
            "role": self.role,
            "name": self.name,
            "sha256": self.sha256,
            "byte_count": self.byte_count,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> _Pythia160DeclaredFile:
        item = _mapping(value, label="model.files[]")
        _exact_keys(
            item,
            frozenset({"role", "name", "sha256", "byte_count"}),
            label="model.files[]",
        )
        return cls(
            role=item["role"],  # type: ignore[arg-type]
            name=_trimmed_string(item["name"], label="model.files[].name"),
            sha256=_sha256(item["sha256"], label="model.files[].sha256"),
            byte_count=_positive_integer(
                item["byte_count"], label="model.files[].byte_count"
            ),
        )


@dataclass(frozen=True, slots=True)
class _Pythia160DeclaredProfile:
    num_layers: int
    hidden_size: int
    vocab_size: int
    num_attention_heads: int
    intermediate_size: int
    max_position_embeddings: int
    parameter_count: int
    parameter_tensor_count: int
    status: str = _DECLARED_UNVERIFIED

    def __post_init__(self) -> None:
        for name in (
            "num_layers",
            "hidden_size",
            "vocab_size",
            "num_attention_heads",
            "intermediate_size",
            "max_position_embeddings",
            "parameter_count",
            "parameter_tensor_count",
        ):
            _positive_integer(getattr(self, name), label=f"model.profile.{name}")
        _constant(
            self.status,
            _DECLARED_UNVERIFIED,
            label="model.profile.status",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "num_layers": self.num_layers,
            "hidden_size": self.hidden_size,
            "vocab_size": self.vocab_size,
            "num_attention_heads": self.num_attention_heads,
            "intermediate_size": self.intermediate_size,
            "max_position_embeddings": self.max_position_embeddings,
            "parameter_count": self.parameter_count,
            "parameter_tensor_count": self.parameter_tensor_count,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> _Pythia160DeclaredProfile:
        item = _mapping(value, label="model.profile")
        fields = frozenset(
            {
                "num_layers",
                "hidden_size",
                "vocab_size",
                "num_attention_heads",
                "intermediate_size",
                "max_position_embeddings",
                "parameter_count",
                "parameter_tensor_count",
                "status",
            }
        )
        _exact_keys(item, fields, label="model.profile")
        return cls(
            num_layers=_positive_integer(
                item["num_layers"], label="model.profile.num_layers"
            ),
            hidden_size=_positive_integer(
                item["hidden_size"], label="model.profile.hidden_size"
            ),
            vocab_size=_positive_integer(
                item["vocab_size"], label="model.profile.vocab_size"
            ),
            num_attention_heads=_positive_integer(
                item["num_attention_heads"],
                label="model.profile.num_attention_heads",
            ),
            intermediate_size=_positive_integer(
                item["intermediate_size"],
                label="model.profile.intermediate_size",
            ),
            max_position_embeddings=_positive_integer(
                item["max_position_embeddings"],
                label="model.profile.max_position_embeddings",
            ),
            parameter_count=_positive_integer(
                item["parameter_count"], label="model.profile.parameter_count"
            ),
            parameter_tensor_count=_positive_integer(
                item["parameter_tensor_count"],
                label="model.profile.parameter_tensor_count",
            ),
            status=_constant(
                item["status"],
                _DECLARED_UNVERIFIED,
                label="model.profile.status",
            ),
        )


@dataclass(frozen=True, slots=True)
class _Pythia160DeclaredModel:
    model_id: str
    revision: str
    architecture: str
    files: tuple[_Pythia160DeclaredFile, ...]
    profile: _Pythia160DeclaredProfile
    identity_status: str = _DECLARED_UNVERIFIED
    architecture_status: str = _DECLARED_UNVERIFIED
    files_status: str = _DECLARED_UNVERIFIED

    def __post_init__(self) -> None:
        _constant(self.model_id, _MODEL_ID, label="model.model_id")
        _commit(self.revision, label="model.revision")
        _trimmed_string(self.architecture, label="model.architecture")
        for label, status in (
            ("model.identity_status", self.identity_status),
            ("model.architecture_status", self.architecture_status),
            ("model.files_status", self.files_status),
        ):
            _constant(status, _DECLARED_UNVERIFIED, label=label)
        if (
            type(self.files) is not tuple
            or not self.files
            or len(self.files) > _MAX_DECLARED_FILES
        ):
            raise _Pythia160PreobservationContractError(
                "model.files must be a bounded non-empty immutable tuple"
            )
        if any(type(item) is not _Pythia160DeclaredFile for item in self.files):
            raise _Pythia160PreobservationContractError(
                "model.files entries must be exact private declared-file records"
            )
        identities = tuple((item.role, item.name) for item in self.files)
        if identities != tuple(sorted(identities)) or len(set(identities)) != len(
            identities
        ):
            raise _Pythia160PreobservationContractError(
                "model.files must be strictly sorted and unique by role and name"
            )
        names = tuple(item.name for item in self.files)
        if len(set(names)) != len(names):
            raise _Pythia160PreobservationContractError(
                "model.files names must be unique"
            )
        if sum(item.role == "config" for item in self.files) != 1:
            raise _Pythia160PreobservationContractError(
                "model.files must declare exactly one config role"
            )
        if not any(item.role == "weights" for item in self.files):
            raise _Pythia160PreobservationContractError(
                "model.files must declare at least one weights role"
            )
        if type(self.profile) is not _Pythia160DeclaredProfile:
            raise _Pythia160PreobservationContractError(
                "model.profile must be an exact private declared-profile record"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "model_id": self.model_id,
            "revision": self.revision,
            "identity_status": self.identity_status,
            "architecture": self.architecture,
            "architecture_status": self.architecture_status,
            "files": [item.to_dict() for item in self.files],
            "files_status": self.files_status,
            "profile": self.profile.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> _Pythia160DeclaredModel:
        item = _mapping(value, label="model")
        fields = frozenset(
            {
                "model_id",
                "revision",
                "identity_status",
                "architecture",
                "architecture_status",
                "files",
                "files_status",
                "profile",
            }
        )
        _exact_keys(item, fields, label="model")
        files = item["files"]
        if type(files) is not list or not files or len(files) > _MAX_DECLARED_FILES:
            raise _Pythia160PreobservationContractError(
                "model.files must be a bounded non-empty JSON array"
            )
        return cls(
            model_id=_constant(item["model_id"], _MODEL_ID, label="model.model_id"),
            revision=_commit(item["revision"], label="model.revision"),
            identity_status=_constant(
                item["identity_status"],
                _DECLARED_UNVERIFIED,
                label="model.identity_status",
            ),
            architecture=_trimmed_string(
                item["architecture"], label="model.architecture"
            ),
            architecture_status=_constant(
                item["architecture_status"],
                _DECLARED_UNVERIFIED,
                label="model.architecture_status",
            ),
            files=tuple(
                _Pythia160DeclaredFile.from_dict(
                    _mapping(file_item, label="model.files[]")
                )
                for file_item in files
            ),
            files_status=_constant(
                item["files_status"],
                _DECLARED_UNVERIFIED,
                label="model.files_status",
            ),
            profile=_Pythia160DeclaredProfile.from_dict(
                _mapping(item["profile"], label="model.profile")
            ),
        )


@dataclass(frozen=True, slots=True)
class _Pythia160DeclaredCapture:
    batch_size: int
    context_tokens: int
    row_count: int
    implementation_version: str = _CAPTURE_IMPLEMENTATION_VERSION
    device: str = "cpu"
    dtype: str = "float32"
    observation_contract: str = _OBSERVATION_CONTRACT
    hook_parity_status: str = "not_run"
    zero_intervention_status: str = "not_run"

    def __post_init__(self) -> None:
        _positive_integer(self.batch_size, label="capture.batch_size")
        _positive_integer(self.context_tokens, label="capture.context_tokens")
        _positive_integer(self.row_count, label="capture.row_count")
        for label, value, expected in (
            (
                "capture.implementation_version",
                self.implementation_version,
                _CAPTURE_IMPLEMENTATION_VERSION,
            ),
            ("capture.device", self.device, "cpu"),
            ("capture.dtype", self.dtype, "float32"),
            (
                "capture.observation_contract",
                self.observation_contract,
                _OBSERVATION_CONTRACT,
            ),
            ("capture.hook_parity_status", self.hook_parity_status, "not_run"),
            (
                "capture.zero_intervention_status",
                self.zero_intervention_status,
                "not_run",
            ),
        ):
            _constant(value, expected, label=label)

    def to_dict(self) -> dict[str, object]:
        return {
            "implementation_version": self.implementation_version,
            "device": self.device,
            "dtype": self.dtype,
            "observation_contract": self.observation_contract,
            "batch_size": self.batch_size,
            "context_tokens": self.context_tokens,
            "row_count": self.row_count,
            "hook_parity_status": self.hook_parity_status,
            "zero_intervention_status": self.zero_intervention_status,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> _Pythia160DeclaredCapture:
        item = _mapping(value, label="capture")
        fields = frozenset(
            {
                "implementation_version",
                "device",
                "dtype",
                "observation_contract",
                "batch_size",
                "context_tokens",
                "row_count",
                "hook_parity_status",
                "zero_intervention_status",
            }
        )
        _exact_keys(item, fields, label="capture")
        return cls(
            implementation_version=_constant(
                item["implementation_version"],
                _CAPTURE_IMPLEMENTATION_VERSION,
                label="capture.implementation_version",
            ),
            device=_constant(item["device"], "cpu", label="capture.device"),
            dtype=_constant(item["dtype"], "float32", label="capture.dtype"),
            observation_contract=_constant(
                item["observation_contract"],
                _OBSERVATION_CONTRACT,
                label="capture.observation_contract",
            ),
            batch_size=_positive_integer(
                item["batch_size"], label="capture.batch_size"
            ),
            context_tokens=_positive_integer(
                item["context_tokens"], label="capture.context_tokens"
            ),
            row_count=_positive_integer(item["row_count"], label="capture.row_count"),
            hook_parity_status=_constant(
                item["hook_parity_status"],
                "not_run",
                label="capture.hook_parity_status",
            ),
            zero_intervention_status=_constant(
                item["zero_intervention_status"],
                "not_run",
                label="capture.zero_intervention_status",
            ),
        )


@dataclass(frozen=True, slots=True)
class _Pythia160DeclaredResourcePlan:
    safety_factor: int
    max_estimated_output_bytes: int
    max_estimated_peak_bytes: int
    estimator_id: str = _RESOURCE_ESTIMATOR_ID

    def __post_init__(self) -> None:
        _constant(
            self.estimator_id,
            _RESOURCE_ESTIMATOR_ID,
            label="resource_plan.estimator_id",
        )
        _positive_integer(self.safety_factor, label="resource_plan.safety_factor")
        _positive_integer(
            self.max_estimated_output_bytes,
            label="resource_plan.max_estimated_output_bytes",
        )
        _positive_integer(
            self.max_estimated_peak_bytes,
            label="resource_plan.max_estimated_peak_bytes",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "estimator_id": self.estimator_id,
            "safety_factor": self.safety_factor,
            "max_estimated_output_bytes": self.max_estimated_output_bytes,
            "max_estimated_peak_bytes": self.max_estimated_peak_bytes,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> _Pythia160DeclaredResourcePlan:
        item = _mapping(value, label="resource_plan")
        fields = frozenset(
            {
                "estimator_id",
                "safety_factor",
                "max_estimated_output_bytes",
                "max_estimated_peak_bytes",
            }
        )
        _exact_keys(item, fields, label="resource_plan")
        return cls(
            estimator_id=_constant(
                item["estimator_id"],
                _RESOURCE_ESTIMATOR_ID,
                label="resource_plan.estimator_id",
            ),
            safety_factor=_positive_integer(
                item["safety_factor"], label="resource_plan.safety_factor"
            ),
            max_estimated_output_bytes=_positive_integer(
                item["max_estimated_output_bytes"],
                label="resource_plan.max_estimated_output_bytes",
            ),
            max_estimated_peak_bytes=_positive_integer(
                item["max_estimated_peak_bytes"],
                label="resource_plan.max_estimated_peak_bytes",
            ),
        )


@dataclass(frozen=True, slots=True)
class _Pythia160PreobservationDeclaration:
    declaration_id: str
    model: _Pythia160DeclaredModel
    capture: _Pythia160DeclaredCapture
    resource_plan: _Pythia160DeclaredResourcePlan
    schema_version: str = _DECLARATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _constant(
            self.schema_version,
            _DECLARATION_SCHEMA_VERSION,
            label="schema_version",
        )
        if (
            type(self.declaration_id) is not str
            or _DECLARATION_ID.fullmatch(self.declaration_id) is None
        ):
            raise _Pythia160PreobservationContractError(
                "declaration_id must be a lowercase canonical identifier"
            )
        if type(self.model) is not _Pythia160DeclaredModel:
            raise _Pythia160PreobservationContractError(
                "model must be an exact private declared-model record"
            )
        if type(self.capture) is not _Pythia160DeclaredCapture:
            raise _Pythia160PreobservationContractError(
                "capture must be an exact private declared-capture record"
            )
        if type(self.resource_plan) is not _Pythia160DeclaredResourcePlan:
            raise _Pythia160PreobservationContractError(
                "resource_plan must be an exact private resource-plan record"
            )
        if self.capture.context_tokens > self.model.profile.max_position_embeddings:
            raise _Pythia160PreobservationContractError(
                "capture.context_tokens exceeds the declared maximum position count"
            )
        estimate = _derive_static_estimate(self)
        if (
            estimate["estimated_output_bytes"]
            > self.resource_plan.max_estimated_output_bytes
        ):
            raise _Pythia160PreobservationContractError(
                "declared output budget is below the static estimate"
            )
        if (
            estimate["estimated_peak_bytes"]
            > self.resource_plan.max_estimated_peak_bytes
        ):
            raise _Pythia160PreobservationContractError(
                "declared peak budget is below the static estimate"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "declaration_id": self.declaration_id,
            "model": self.model.to_dict(),
            "capture": self.capture.to_dict(),
            "resource_plan": self.resource_plan.to_dict(),
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(
        cls, value: Mapping[str, object]
    ) -> _Pythia160PreobservationDeclaration:
        item = _mapping(value, label="Pythia-160M pre-observation declaration")
        fields = frozenset(
            {"schema_version", "declaration_id", "model", "capture", "resource_plan"}
        )
        _exact_keys(item, fields, label="Pythia-160M pre-observation declaration")
        declaration_id = item["declaration_id"]
        if (
            type(declaration_id) is not str
            or _DECLARATION_ID.fullmatch(declaration_id) is None
        ):
            raise _Pythia160PreobservationContractError(
                "declaration_id must be a lowercase canonical identifier"
            )
        return cls(
            schema_version=_constant(
                item["schema_version"],
                _DECLARATION_SCHEMA_VERSION,
                label="schema_version",
            ),
            declaration_id=declaration_id,
            model=_Pythia160DeclaredModel.from_dict(
                _mapping(item["model"], label="model")
            ),
            capture=_Pythia160DeclaredCapture.from_dict(
                _mapping(item["capture"], label="capture")
            ),
            resource_plan=_Pythia160DeclaredResourcePlan.from_dict(
                _mapping(item["resource_plan"], label="resource_plan")
            ),
        )


def _derive_static_estimate(
    declaration: _Pythia160PreobservationDeclaration,
) -> dict[str, object]:
    profile = declaration.model.profile
    capture = declaration.capture
    plan = declaration.resource_plan
    declared_model_file_bytes = _bounded_estimate(
        sum(item.byte_count for item in declaration.model.files),
        label="declared_model_file_bytes",
    )
    declared_parameter_bytes = _bounded_estimate(
        profile.parameter_count * _DTYPE_BYTES,
        label="declared_parameter_bytes",
    )
    declared_row_bytes = _bounded_estimate(
        8
        + 2 * profile.num_layers * profile.hidden_size * _DTYPE_BYTES
        + profile.num_layers * 2 * _DTYPE_BYTES
        + 6 * _DTYPE_BYTES
        + 8,
        label="declared_row_bytes",
    )
    estimated_output_bytes = _bounded_estimate(
        capture.row_count * declared_row_bytes * plan.safety_factor,
        label="estimated_output_bytes",
    )
    estimated_working_bytes = _bounded_estimate(
        capture.batch_size
        * (
            capture.context_tokens * profile.vocab_size * _DTYPE_BYTES
            + 2 * profile.num_layers * profile.hidden_size * _DTYPE_BYTES
        ),
        label="estimated_working_bytes",
    )
    estimated_peak_bytes = _bounded_estimate(
        declared_model_file_bytes
        + declared_parameter_bytes
        + estimated_working_bytes
        + estimated_output_bytes,
        label="estimated_peak_bytes",
    )
    return {
        "estimator_id": _RESOURCE_ESTIMATOR_ID,
        "dtype_bytes": _DTYPE_BYTES,
        "declared_model_file_bytes": declared_model_file_bytes,
        "declared_parameter_bytes": declared_parameter_bytes,
        "declared_row_bytes": declared_row_bytes,
        "estimated_output_bytes": estimated_output_bytes,
        "estimated_working_bytes": estimated_working_bytes,
        "estimated_peak_bytes": estimated_peak_bytes,
        "max_estimated_output_bytes": plan.max_estimated_output_bytes,
        "max_estimated_peak_bytes": plan.max_estimated_peak_bytes,
        "physical_memory_observed": False,
        "free_disk_observed": False,
        "oom_safety_proved": False,
    }


@dataclass(frozen=True, slots=True)
class _Pythia160PreobservationAssessment:
    declaration: _Pythia160PreobservationDeclaration
    declaration_canonical_sha256: str
    static_estimate: Mapping[str, object]
    blocking_prerequisites: tuple[str, ...]
    access: Mapping[str, bool]
    verification: Mapping[str, bool]
    authority: Mapping[str, bool]
    claim_boundary: Mapping[str, object]
    status: str = _BLOCKED_STATUS
    schema_version: str = _ASSESSMENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _constant(
            self.schema_version,
            _ASSESSMENT_SCHEMA_VERSION,
            label="assessment.schema_version",
        )
        _constant(self.status, _BLOCKED_STATUS, label="assessment.status")
        if type(self.declaration) is not _Pythia160PreobservationDeclaration:
            raise _Pythia160PreobservationContractError(
                "assessment.declaration must be an exact private declaration"
            )
        if self.declaration_canonical_sha256 != self.declaration.canonical_sha256:
            raise _Pythia160PreobservationContractError(
                "assessment declaration digest differs from its declaration"
            )
        _sha256(
            self.declaration_canonical_sha256,
            label="assessment.declaration_canonical_sha256",
        )
        object.__setattr__(
            self,
            "static_estimate",
            _snapshot_exact_closed_mapping(
                self.static_estimate,
                _derive_static_estimate(self.declaration),
                label="static_estimate",
            ),
        )
        if (
            type(self.blocking_prerequisites) is not tuple
            or any(type(item) is not str for item in self.blocking_prerequisites)
            or self.blocking_prerequisites != _BLOCKING_PREREQUISITES
        ):
            raise _Pythia160PreobservationContractError(
                "assessment blocking prerequisites differ from the closed set"
            )
        for label, actual, expected in (
            ("access", self.access, _ACCESS_FACTS),
            ("verification", self.verification, _VERIFICATION_FACTS),
            ("authority", self.authority, _AUTHORITY_FACTS),
            ("claim_boundary", self.claim_boundary, _CLAIM_BOUNDARY),
        ):
            object.__setattr__(
                self,
                label,
                _snapshot_exact_closed_mapping(actual, expected, label=label),
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "declaration": self.declaration.to_dict(),
            "declaration_canonical_sha256": self.declaration_canonical_sha256,
            "static_estimate": dict(self.static_estimate),
            "blocking_prerequisites": list(self.blocking_prerequisites),
            "access": dict(self.access),
            "verification": dict(self.verification),
            "authority": dict(self.authority),
            "claim_boundary": dict(self.claim_boundary),
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(
        cls, value: Mapping[str, object]
    ) -> _Pythia160PreobservationAssessment:
        item = _mapping(value, label="Pythia-160M pre-observation assessment")
        fields = frozenset(
            {
                "schema_version",
                "status",
                "declaration",
                "declaration_canonical_sha256",
                "static_estimate",
                "blocking_prerequisites",
                "access",
                "verification",
                "authority",
                "claim_boundary",
            }
        )
        _exact_keys(item, fields, label="Pythia-160M pre-observation assessment")
        declaration = _Pythia160PreobservationDeclaration.from_dict(
            _mapping(item["declaration"], label="assessment.declaration")
        )
        expected = _assess_pythia160_preobservation_declaration(declaration)
        _constant(
            item["schema_version"],
            _ASSESSMENT_SCHEMA_VERSION,
            label="assessment.schema_version",
        )
        _constant(item["status"], _BLOCKED_STATUS, label="assessment.status")
        _sha256(
            item["declaration_canonical_sha256"],
            label="assessment.declaration_canonical_sha256",
        )
        prerequisites = item["blocking_prerequisites"]
        if (
            type(prerequisites) is not list
            or len(prerequisites) != len(_BLOCKING_PREREQUISITES)
            or tuple(prerequisites) != _BLOCKING_PREREQUISITES
        ):
            raise _Pythia160PreobservationContractError(
                "assessment blocking prerequisites differ from the closed set"
            )
        for label, closed in (
            ("static_estimate", expected.static_estimate),
            ("access", _ACCESS_FACTS),
            ("verification", _VERIFICATION_FACTS),
            ("authority", _AUTHORITY_FACTS),
            ("claim_boundary", _CLAIM_BOUNDARY),
        ):
            _snapshot_exact_closed_mapping(
                _mapping(item[label], label=f"assessment.{label}"),
                closed,
                label=label,
            )
        try:
            supplied_bytes = canonical_json_bytes(dict(item))
        except (TypeError, ValueError) as error:
            raise _Pythia160PreobservationContractError(
                "assessment document is not canonical-JSON-compatible"
            ) from error
        if supplied_bytes != expected.canonical_bytes:
            raise _Pythia160PreobservationContractError(
                "assessment document differs from the derived closed assessment"
            )
        return expected


def _assess_pythia160_preobservation_declaration(
    declaration: _Pythia160PreobservationDeclaration,
) -> _Pythia160PreobservationAssessment:
    """Derive the only closed assessment: externally blocked, no authority."""

    if type(declaration) is not _Pythia160PreobservationDeclaration:
        raise TypeError(
            "declaration must be an exact _Pythia160PreobservationDeclaration"
        )
    return _Pythia160PreobservationAssessment(
        declaration=declaration,
        declaration_canonical_sha256=declaration.canonical_sha256,
        static_estimate=_derive_static_estimate(declaration),
        blocking_prerequisites=_BLOCKING_PREREQUISITES,
        access=dict(_ACCESS_FACTS),
        verification=dict(_VERIFICATION_FACTS),
        authority=dict(_AUTHORITY_FACTS),
        claim_boundary=dict(_CLAIM_BOUNDARY),
    )
