"""Strict, semantics-free identity contracts for fixed-context observations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
from typing import Any, Mapping


CONTEXT_BANK_SCHEMA_VERSION = "spirallens.context-bank.v1"
CONTEXT_SPEC_SCHEMA_VERSION = "spirallens.context-spec.v1"
OBSERVATION_KEY_SCHEMA_VERSION = "spirallens.observation-key.v1"

_SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REVISION = re.compile(r"^[0-9a-f]{40}$")


class ContextContractError(ValueError):
    """Raised when a context or observation violates its persisted contract."""


class ContextRole(str, Enum):
    """A bank's non-interchangeable experimental role."""

    EXAMPLE = "example"
    DISCOVERY = "discovery"
    HELD_OUT = "held_out"


class BankStatus(str, Enum):
    """Lifecycle state attached to a context-bank artifact."""

    EXAMPLE = "example"
    DRAFT = "draft"
    FROZEN = "frozen"


class SweepDomain(str, Enum):
    """The declared universe from which swept IDs may be selected."""

    MODEL_EMBEDDING_ROWS = "model_embedding_rows"
    TOKENIZER_ADDRESSABLE = "tokenizer_addressable"


class CaptureStage(str, Enum):
    """Residual-stream location represented by an observation."""

    RESID_PRE = "resid_pre"
    RESID_POST = "resid_post"


def _canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256_json(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _require_plain_int(value: object, *, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer")
    if value < minimum:
        raise ContextContractError(f"{label} must be >= {minimum}")
    return value


def _require_nonempty_string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"{label} must be a non-empty string")
    if value != value.strip():
        raise ContextContractError(f"{label} must not have surrounding whitespace")
    return value


def _require_slug(value: object, *, label: str) -> str:
    text = _require_nonempty_string(value, label=label)
    if _SLUG.fullmatch(text) is None:
        raise ContextContractError(
            f"{label} must match {_SLUG.pattern!r}, got {text!r}"
        )
    return text


def _require_sha256(value: object, *, label: str) -> str:
    text = _require_nonempty_string(value, label=label)
    if _SHA256.fullmatch(text) is None:
        raise ContextContractError(f"{label} must be a lowercase SHA-256 digest")
    return text


def _require_revision(value: object, *, label: str) -> str:
    text = _require_nonempty_string(value, label=label)
    if _REVISION.fullmatch(text) is None:
        raise ContextContractError(
            f"{label} must be a lowercase 40-character commit hash"
        )
    return text


@dataclass(frozen=True, slots=True)
class ModelBinding:
    """Immutable model identity and embedding-row domain."""

    model_id: str
    requested_revision: str
    resolved_revision: str
    vocab_size: int

    def __post_init__(self) -> None:
        _require_nonempty_string(self.model_id, label="model_id")
        _require_nonempty_string(
            self.requested_revision, label="requested_model_revision"
        )
        _require_revision(
            self.resolved_revision, label="resolved_model_revision"
        )
        _require_plain_int(self.vocab_size, label="model_vocab_size", minimum=1)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.model_id,
            "requested_revision": self.requested_revision,
            "resolved_revision": self.resolved_revision,
            "vocab_size": self.vocab_size,
        }


@dataclass(frozen=True, slots=True)
class TokenizerBinding:
    """Tokenizer provenance without treating decoded strings as identity."""

    tokenizer_id: str
    requested_revision: str
    resolved_revision: str
    addressable_size: int
    tokenizer_class: str
    implementation: str
    transformers_version: str
    tokenizers_version: str
    add_special_tokens: bool
    file_sha256: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        _require_nonempty_string(self.tokenizer_id, label="tokenizer_id")
        _require_nonempty_string(
            self.requested_revision, label="requested_tokenizer_revision"
        )
        _require_revision(
            self.resolved_revision, label="resolved_tokenizer_revision"
        )
        _require_plain_int(
            self.addressable_size,
            label="tokenizer_addressable_size",
            minimum=1,
        )
        _require_nonempty_string(
            self.tokenizer_class, label="tokenizer_class"
        )
        if self.implementation not in {"fast", "slow"}:
            raise ContextContractError(
                "tokenizer implementation must be 'fast' or 'slow'"
            )
        _require_nonempty_string(
            self.transformers_version, label="transformers_version"
        )
        _require_nonempty_string(
            self.tokenizers_version, label="tokenizers_version"
        )
        if type(self.add_special_tokens) is not bool:
            raise TypeError("add_special_tokens must be a boolean")
        if self.add_special_tokens:
            raise ContextContractError(
                "context-bank v1 requires add_special_tokens=false"
            )
        if not self.file_sha256:
            raise ContextContractError(
                "tokenizer file hashes must contain at least one file"
            )
        names = [name for name, _ in self.file_sha256]
        if len(names) != len(set(names)):
            raise ContextContractError("tokenizer filenames must be unique")
        if names != sorted(names):
            raise ContextContractError(
                "tokenizer file hashes must be sorted by filename"
            )
        for name, digest in self.file_sha256:
            _require_nonempty_string(name, label="tokenizer filename")
            if name.startswith("/") or ".." in name.split("/"):
                raise ContextContractError(
                    "tokenizer filenames must be safe relative paths"
                )
            _require_sha256(digest, label=f"tokenizer.files[{name!r}]")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.tokenizer_id,
            "requested_revision": self.requested_revision,
            "resolved_revision": self.resolved_revision,
            "addressable_size": self.addressable_size,
            "tokenizer_class": self.tokenizer_class,
            "implementation": self.implementation,
            "transformers_version": self.transformers_version,
            "tokenizers_version": self.tokenizers_version,
            "add_special_tokens": self.add_special_tokens,
            "files": dict(self.file_sha256),
        }

    @property
    def sha256(self) -> str:
        """Canonical tokenizer-provenance digest."""

        return _sha256_json(self.to_dict())


@dataclass(frozen=True, slots=True)
class SourceBinding:
    """Non-semantic origin and licensing handle for a bank."""

    kind: str
    source_id: str

    def __post_init__(self) -> None:
        _require_slug(self.kind, label="source.kind")
        _require_slug(self.source_id, label="source.source_id")

    def to_dict(self) -> dict[str, object]:
        return {"kind": self.kind, "source_id": self.source_id}


@dataclass(frozen=True, slots=True)
class ContextSpec:
    """One exactly-one-slot token template and observation location."""

    context_id: str
    role: ContextRole
    family_id: str
    source_id: str
    template_id: str
    template_ids: tuple[int | None, ...]
    attention_mask: tuple[int, ...]
    observation_position: int

    def __post_init__(self) -> None:
        _require_slug(self.context_id, label="context_id")
        if not isinstance(self.role, ContextRole):
            raise TypeError("role must be a ContextRole")
        _require_slug(self.family_id, label=f"{self.context_id}.family_id")
        _require_slug(self.source_id, label=f"{self.context_id}.source_id")
        _require_slug(self.template_id, label=f"{self.context_id}.template_id")
        if not isinstance(self.template_ids, tuple):
            raise TypeError("template_ids must be a tuple")
        if not self.template_ids:
            raise ContextContractError("template_ids must not be empty")
        slot_count = sum(value is None for value in self.template_ids)
        if slot_count != 1:
            raise ContextContractError(
                f"template_ids must contain exactly one null slot, got {slot_count}"
            )
        for value in self.template_ids:
            if value is None:
                continue
            _require_plain_int(value, label="template token ID")
        if not isinstance(self.attention_mask, tuple):
            raise TypeError("attention_mask must be a tuple")
        if len(self.attention_mask) != len(self.template_ids):
            raise ContextContractError(
                "attention_mask length must match template_ids"
            )
        for value in self.attention_mask:
            _require_plain_int(value, label="attention mask value")
            if value not in (0, 1):
                raise ContextContractError(
                    "attention_mask values must be 0 or 1"
                )
        _require_plain_int(
            self.observation_position, label="observation_position"
        )
        if self.observation_position >= len(self.template_ids):
            raise ContextContractError(
                "observation_position is outside template_ids"
            )
        if self.attention_mask[self.sweep_position] != 1:
            raise ContextContractError("the sweep slot must be attended")
        if self.attention_mask[self.observation_position] != 1:
            raise ContextContractError("the observation position must be attended")

    @property
    def sweep_position(self) -> int:
        """Position of the structured slot replaced during a sweep."""

        return self.template_ids.index(None)

    def input_dict(self) -> dict[str, object]:
        """Return numeric input identity, excluding role and human identifiers."""

        return {
            "schema_version": CONTEXT_SPEC_SCHEMA_VERSION,
            "template_ids": list(self.template_ids),
            "attention_mask": list(self.attention_mask),
            "sweep_position": self.sweep_position,
            "observation_position": self.observation_position,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "context_id": self.context_id,
            "role": self.role.value,
            "family_id": self.family_id,
            "source_id": self.source_id,
            "template_id": self.template_id,
            "template_ids": list(self.template_ids),
            "attention_mask": list(self.attention_mask),
            "observation_position": self.observation_position,
        }

    @property
    def input_sha256(self) -> str:
        """Digest used to reject duplicate numeric inputs."""

        return _sha256_json(self.input_dict())

    @property
    def sha256(self) -> str:
        """Digest of both numeric input and split/audit identity."""

        return _sha256_json(
            {
                "schema_version": CONTEXT_SPEC_SCHEMA_VERSION,
                **self.to_dict(),
                "sweep_position": self.sweep_position,
            }
        )

    def materialize(
        self,
        swept_token_id: int,
        *,
        model_vocab_size: int,
    ) -> tuple[int, ...]:
        """Replace only the structured slot with one model embedding-row ID."""

        _require_plain_int(
            model_vocab_size, label="model_vocab_size", minimum=1
        )
        token_id = _require_plain_int(
            swept_token_id, label="swept_token_id"
        )
        if token_id >= model_vocab_size:
            raise ContextContractError(
                f"swept_token_id must be < model_vocab_size ({model_vocab_size})"
            )
        return tuple(
            token_id if value is None else value for value in self.template_ids
        )


@dataclass(frozen=True, slots=True)
class ContextBank:
    """Ordered, single-role context bank bound to model and tokenizer bytes."""

    bank_id: str
    status: BankStatus
    license: str
    claim_eligible: bool
    source: SourceBinding
    model: ModelBinding
    tokenizer: TokenizerBinding
    sweep_domain: SweepDomain
    contexts: tuple[ContextSpec, ...]

    def __post_init__(self) -> None:
        _require_slug(self.bank_id, label="bank_id")
        if not isinstance(self.status, BankStatus):
            raise TypeError("status must be a BankStatus")
        _require_nonempty_string(self.license, label="license")
        if type(self.claim_eligible) is not bool:
            raise TypeError("claim_eligible must be a boolean")
        if not isinstance(self.source, SourceBinding):
            raise TypeError("source must be a SourceBinding")
        if not isinstance(self.model, ModelBinding):
            raise TypeError("model must be a ModelBinding")
        if not isinstance(self.tokenizer, TokenizerBinding):
            raise TypeError("tokenizer must be a TokenizerBinding")
        if not isinstance(self.sweep_domain, SweepDomain):
            raise TypeError("sweep_domain must be a SweepDomain")
        if self.tokenizer.addressable_size > self.model.vocab_size:
            raise ContextContractError(
                "tokenizer addressable size cannot exceed model vocabulary size"
            )
        if not isinstance(self.contexts, tuple) or not self.contexts:
            raise ContextContractError("contexts must be a non-empty tuple")
        if any(not isinstance(context, ContextSpec) for context in self.contexts):
            raise TypeError("contexts must contain only ContextSpec values")

        roles = {context.role for context in self.contexts}
        if len(roles) != 1:
            raise ContextContractError(
                "a context bank must contain exactly one role; use separate "
                "artifacts for discovery and held_out contexts"
            )
        role = next(iter(roles))
        if role is ContextRole.EXAMPLE:
            if self.status is not BankStatus.EXAMPLE or self.claim_eligible:
                raise ContextContractError(
                    "example banks require status=example and "
                    "claim_eligible=false"
                )
        elif self.status is BankStatus.EXAMPLE:
            raise ContextContractError(
                "status=example is reserved for role=example banks"
            )
        if role is ContextRole.HELD_OUT and self.status is not BankStatus.FROZEN:
            raise ContextContractError("held_out banks must be frozen")
        if self.claim_eligible and self.status is not BankStatus.FROZEN:
            raise ContextContractError(
                "claim-eligible banks must have status=frozen"
            )

        context_ids = [context.context_id for context in self.contexts]
        if len(context_ids) != len(set(context_ids)):
            raise ContextContractError("context IDs must be unique")
        input_digests = [context.input_sha256 for context in self.contexts]
        if len(input_digests) != len(set(input_digests)):
            raise ContextContractError(
                "duplicate numeric context inputs are not allowed"
            )
        for context in self.contexts:
            for token_id in context.template_ids:
                if (
                    token_id is not None
                    and token_id >= self.tokenizer.addressable_size
                ):
                    raise ContextContractError(
                        f"context {context.context_id!r} contains token ID "
                        f"{token_id} outside the tokenizer-addressable domain "
                        f"[0, {self.tokenizer.addressable_size - 1}]"
                    )

    @property
    def role(self) -> ContextRole:
        return self.contexts[0].role

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": CONTEXT_BANK_SCHEMA_VERSION,
            "bank_id": self.bank_id,
            "status": self.status.value,
            "license": self.license,
            "claim_eligible": self.claim_eligible,
            "source": self.source.to_dict(),
            "model": self.model.to_dict(),
            "tokenizer": self.tokenizer.to_dict(),
            "sweep_domain": self.sweep_domain.value,
            "contexts": [context.to_dict() for context in self.contexts],
        }

    @property
    def sha256(self) -> str:
        """Canonical content digest; ordered context entries are significant."""

        return _sha256_json(self.to_dict())

    def require(
        self,
        context_id: str,
        *,
        role: ContextRole,
    ) -> ContextSpec:
        """Resolve an entry while explicitly checking its experimental role."""

        if not isinstance(role, ContextRole):
            raise TypeError("role must be a ContextRole")
        for context in self.contexts:
            if context.context_id == context_id:
                if context.role is not role:
                    raise ContextContractError(
                        f"context {context_id!r} has role "
                        f"{context.role.value!r}, not {role.value!r}"
                    )
                return context
        raise ContextContractError(f"unknown context_id {context_id!r}")

    def validate_swept_token_id(self, token_id: int) -> bool:
        """Validate a swept ID and return tokenizer-range addressability."""

        value = _require_plain_int(token_id, label="swept_token_id")
        upper = (
            self.model.vocab_size
            if self.sweep_domain is SweepDomain.MODEL_EMBEDDING_ROWS
            else self.tokenizer.addressable_size
        )
        if value >= upper:
            raise ContextContractError(
                f"swept_token_id must be in [0, {upper - 1}] for "
                f"{self.sweep_domain.value}"
            )
        return value < self.tokenizer.addressable_size

    def observation_key(
        self,
        *,
        context_id: str,
        role: ContextRole,
        swept_token_id: int,
        layer_index: int,
        capture_stage: CaptureStage,
    ) -> "ObservationKey":
        """Build an observation identity from this bank's canonical binding."""

        context = self.require(context_id, role=role)
        tokenizer_addressable = self.validate_swept_token_id(swept_token_id)
        return ObservationKey(
            model_id=self.model.model_id,
            resolved_model_revision=self.model.resolved_revision,
            context_bank_sha256=self.sha256,
            context_id=context.context_id,
            context_role=context.role,
            context_spec_sha256=context.sha256,
            swept_token_id=swept_token_id,
            model_vocab_size=self.model.vocab_size,
            tokenizer_addressable_size=self.tokenizer.addressable_size,
            sweep_domain=self.sweep_domain,
            tokenizer_addressable=tokenizer_addressable,
            sweep_position=context.sweep_position,
            observation_position=context.observation_position,
            layer_index=layer_index,
            capture_stage=capture_stage,
        )

    def validate_observation_key(
        self,
        key: "ObservationKey",
    ) -> "ObservationKey":
        """Reject a structurally valid key that is not bound to this bank."""

        if not isinstance(key, ObservationKey):
            raise TypeError("key must be an ObservationKey")
        context = self.require(key.context_id, role=key.context_role)
        expected_tokenizer_addressable = self.validate_swept_token_id(
            key.swept_token_id
        )
        expected: dict[str, object] = {
            "model_id": self.model.model_id,
            "resolved_model_revision": self.model.resolved_revision,
            "context_bank_sha256": self.sha256,
            "context_spec_sha256": context.sha256,
            "model_vocab_size": self.model.vocab_size,
            "tokenizer_addressable_size": self.tokenizer.addressable_size,
            "sweep_domain": self.sweep_domain,
            "tokenizer_addressable": expected_tokenizer_addressable,
            "sweep_position": context.sweep_position,
            "observation_position": context.observation_position,
        }
        mismatches = [
            field
            for field, expected_value in expected.items()
            if getattr(key, field) != expected_value
        ]
        if mismatches:
            raise ContextContractError(
                "observation key does not match context bank fields: "
                + ", ".join(mismatches)
            )
        return key


@dataclass(frozen=True, slots=True)
class ObservationKey:
    """Stable identity for one layer/context/token residual observation."""

    model_id: str
    resolved_model_revision: str
    context_bank_sha256: str
    context_id: str
    context_role: ContextRole
    context_spec_sha256: str
    swept_token_id: int
    model_vocab_size: int
    tokenizer_addressable_size: int
    sweep_domain: SweepDomain
    tokenizer_addressable: bool
    sweep_position: int
    observation_position: int
    layer_index: int
    capture_stage: CaptureStage

    def __post_init__(self) -> None:
        _require_nonempty_string(self.model_id, label="model_id")
        _require_revision(
            self.resolved_model_revision, label="resolved_model_revision"
        )
        _require_sha256(
            self.context_bank_sha256, label="context_bank_sha256"
        )
        _require_slug(self.context_id, label="context_id")
        if not isinstance(self.context_role, ContextRole):
            raise TypeError("context_role must be a ContextRole")
        _require_sha256(
            self.context_spec_sha256, label="context_spec_sha256"
        )
        _require_plain_int(self.swept_token_id, label="swept_token_id")
        _require_plain_int(
            self.model_vocab_size, label="model_vocab_size", minimum=1
        )
        _require_plain_int(
            self.tokenizer_addressable_size,
            label="tokenizer_addressable_size",
            minimum=1,
        )
        if self.tokenizer_addressable_size > self.model_vocab_size:
            raise ContextContractError(
                "tokenizer_addressable_size cannot exceed model_vocab_size"
            )
        if not isinstance(self.sweep_domain, SweepDomain):
            raise TypeError("sweep_domain must be a SweepDomain")
        if type(self.tokenizer_addressable) is not bool:
            raise TypeError("tokenizer_addressable must be a boolean")
        domain_upper = (
            self.model_vocab_size
            if self.sweep_domain is SweepDomain.MODEL_EMBEDDING_ROWS
            else self.tokenizer_addressable_size
        )
        if self.swept_token_id >= domain_upper:
            raise ContextContractError(
                "swept_token_id is outside the declared sweep domain"
            )
        expected_tokenizer_addressable = (
            self.swept_token_id < self.tokenizer_addressable_size
        )
        if self.tokenizer_addressable is not expected_tokenizer_addressable:
            raise ContextContractError(
                "tokenizer_addressable does not match the tokenizer domain"
            )
        _require_plain_int(self.sweep_position, label="sweep_position")
        _require_plain_int(
            self.observation_position, label="observation_position"
        )
        _require_plain_int(self.layer_index, label="layer_index")
        if not isinstance(self.capture_stage, CaptureStage):
            raise TypeError("capture_stage must be a CaptureStage")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": OBSERVATION_KEY_SCHEMA_VERSION,
            "model_id": self.model_id,
            "resolved_model_revision": self.resolved_model_revision,
            "context_bank_sha256": self.context_bank_sha256,
            "context_id": self.context_id,
            "context_role": self.context_role.value,
            "context_spec_sha256": self.context_spec_sha256,
            "swept_token_id": self.swept_token_id,
            "model_vocab_size": self.model_vocab_size,
            "tokenizer_addressable_size": self.tokenizer_addressable_size,
            "sweep_domain": self.sweep_domain.value,
            "tokenizer_addressable": self.tokenizer_addressable,
            "sweep_position": self.sweep_position,
            "observation_position": self.observation_position,
            "layer_index": self.layer_index,
            "capture_stage": self.capture_stage.value,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "ObservationKey":
        """Strictly restore a key without accepting schema drift or extras."""

        expected = {
            "schema_version",
            "model_id",
            "resolved_model_revision",
            "context_bank_sha256",
            "context_id",
            "context_role",
            "context_spec_sha256",
            "swept_token_id",
            "model_vocab_size",
            "tokenizer_addressable_size",
            "sweep_domain",
            "tokenizer_addressable",
            "sweep_position",
            "observation_position",
            "layer_index",
            "capture_stage",
        }
        if not isinstance(value, Mapping):
            raise TypeError("observation key must be a mapping")
        if any(not isinstance(key, str) for key in value):
            raise ContextContractError(
                "observation key fields must have string names"
            )
        keys = set(value)
        if keys != expected:
            raise ContextContractError(
                "observation key fields differ from v1 contract: "
                f"missing={sorted(expected - keys)}, "
                f"unknown={sorted(keys - expected)}"
            )
        if value["schema_version"] != OBSERVATION_KEY_SCHEMA_VERSION:
            raise ContextContractError(
                f"unsupported observation key schema "
                f"{value['schema_version']!r}"
            )
        try:
            domain = SweepDomain(value["sweep_domain"])
            context_role = ContextRole(value["context_role"])
            stage = CaptureStage(value["capture_stage"])
        except (TypeError, ValueError) as exc:
            raise ContextContractError(
                "observation key contains an unknown enum value"
            ) from exc
        return cls(
            model_id=value["model_id"],  # type: ignore[arg-type]
            resolved_model_revision=value["resolved_model_revision"],  # type: ignore[arg-type]
            context_bank_sha256=value["context_bank_sha256"],  # type: ignore[arg-type]
            context_id=value["context_id"],  # type: ignore[arg-type]
            context_role=context_role,
            context_spec_sha256=value["context_spec_sha256"],  # type: ignore[arg-type]
            swept_token_id=value["swept_token_id"],  # type: ignore[arg-type]
            model_vocab_size=value["model_vocab_size"],  # type: ignore[arg-type]
            tokenizer_addressable_size=value["tokenizer_addressable_size"],  # type: ignore[arg-type]
            sweep_domain=domain,
            tokenizer_addressable=value["tokenizer_addressable"],  # type: ignore[arg-type]
            sweep_position=value["sweep_position"],  # type: ignore[arg-type]
            observation_position=value["observation_position"],  # type: ignore[arg-type]
            layer_index=value["layer_index"],  # type: ignore[arg-type]
            capture_stage=stage,
        )

    @property
    def observation_id(self) -> str:
        """Canonical SHA-256 identity for joins and candidate graphs."""

        return _sha256_json(self.to_dict())
