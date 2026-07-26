"""Fail-closed YAML loading for :mod:`spirallens.contexts`."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any, Collection, Mapping

import yaml
from yaml.events import AliasEvent
from yaml.nodes import MappingNode

from .contracts import (
    CONTEXT_BANK_SCHEMA_VERSION,
    BankStatus,
    ContextBank,
    ContextContractError,
    ContextRole,
    ContextSpec,
    ModelBinding,
    SourceBinding,
    SweepDomain,
    TokenizerBinding,
)


MAX_CONTEXT_BANK_BYTES = 1_048_576


class ContextBankSchemaError(ContextContractError):
    """Raised when source YAML is ambiguous or outside the v1 schema."""


class ContextBankIntegrityError(ContextContractError):
    """Raised when source or canonical content fails its expected digest."""


class _StrictSafeLoader(yaml.SafeLoader):
    """SafeLoader variant that rejects aliases before construction."""

    def compose_node(self, parent: Any, index: Any) -> Any:
        if self.check_event(AliasEvent):
            raise ContextBankSchemaError("YAML aliases are not allowed")
        return super().compose_node(parent, index)


def _construct_mapping(
    loader: _StrictSafeLoader,
    node: MappingNode,
    deep: bool = False,
) -> dict[str, Any]:
    if not isinstance(node, MappingNode):
        raise ContextBankSchemaError("expected a YAML mapping")
    mapping: dict[str, Any] = {}
    for key_node, value_node in node.value:
        if key_node.tag == "tag:yaml.org,2002:merge":
            raise ContextBankSchemaError("YAML merge keys are not allowed")
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise ContextBankSchemaError("all mapping keys must be strings")
        if key in mapping:
            raise ContextBankSchemaError(f"duplicate YAML key {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_StrictSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


@dataclass(frozen=True, slots=True)
class LoadedContextBank:
    """A validated bank plus both byte-level and canonical identities."""

    bank: ContextBank
    source_path: Path
    source_sha256: str
    canonical_sha256: str


def _mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ContextBankSchemaError(f"{label} must be a mapping")
    if any(not isinstance(key, str) for key in value):
        raise ContextBankSchemaError(f"{label} keys must be strings")
    return value


def _exact_keys(
    value: Mapping[str, object],
    expected: set[str],
    *,
    label: str,
) -> None:
    actual = set(value)
    if actual != expected:
        raise ContextBankSchemaError(
            f"{label} fields differ from v1 contract: "
            f"missing={sorted(expected - actual)}, "
            f"unknown={sorted(actual - expected)}"
        )


def _string(value: object, *, label: str) -> str:
    if not isinstance(value, str):
        raise ContextBankSchemaError(f"{label} must be a string")
    return value


def _integer(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContextBankSchemaError(f"{label} must be an integer")
    return value


def _boolean(value: object, *, label: str) -> bool:
    if type(value) is not bool:
        raise ContextBankSchemaError(f"{label} must be a boolean")
    return value


def _enum(enum_type: type[Any], value: object, *, label: str) -> Any:
    if not isinstance(value, str):
        raise ContextBankSchemaError(f"{label} must be a string")
    try:
        return enum_type(value)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in enum_type)
        raise ContextBankSchemaError(f"{label} must be one of: {allowed}") from exc


def _parse_model(value: object) -> ModelBinding:
    model = _mapping(value, label="model")
    _exact_keys(
        model,
        {"id", "requested_revision", "resolved_revision", "vocab_size"},
        label="model",
    )
    return ModelBinding(
        model_id=_string(model["id"], label="model.id"),
        requested_revision=_string(
            model["requested_revision"], label="model.requested_revision"
        ),
        resolved_revision=_string(
            model["resolved_revision"], label="model.resolved_revision"
        ),
        vocab_size=_integer(model["vocab_size"], label="model.vocab_size"),
    )


def _parse_tokenizer(value: object) -> TokenizerBinding:
    tokenizer = _mapping(value, label="tokenizer")
    _exact_keys(
        tokenizer,
        {
            "id",
            "requested_revision",
            "resolved_revision",
            "addressable_size",
            "tokenizer_class",
            "implementation",
            "transformers_version",
            "tokenizers_version",
            "add_special_tokens",
            "files",
        },
        label="tokenizer",
    )
    files = _mapping(tokenizer["files"], label="tokenizer.files")
    if not files:
        raise ContextBankSchemaError("tokenizer.files must be a non-empty mapping")
    file_sha256 = tuple(
        (name, _string(files[name], label=f"tokenizer.files[{name!r}]"))
        for name in sorted(files)
    )
    return TokenizerBinding(
        tokenizer_id=_string(tokenizer["id"], label="tokenizer.id"),
        requested_revision=_string(
            tokenizer["requested_revision"],
            label="tokenizer.requested_revision",
        ),
        resolved_revision=_string(
            tokenizer["resolved_revision"],
            label="tokenizer.resolved_revision",
        ),
        addressable_size=_integer(
            tokenizer["addressable_size"],
            label="tokenizer.addressable_size",
        ),
        tokenizer_class=_string(
            tokenizer["tokenizer_class"],
            label="tokenizer.tokenizer_class",
        ),
        implementation=_string(
            tokenizer["implementation"],
            label="tokenizer.implementation",
        ),
        transformers_version=_string(
            tokenizer["transformers_version"],
            label="tokenizer.transformers_version",
        ),
        tokenizers_version=_string(
            tokenizer["tokenizers_version"],
            label="tokenizer.tokenizers_version",
        ),
        add_special_tokens=_boolean(
            tokenizer["add_special_tokens"],
            label="tokenizer.add_special_tokens",
        ),
        file_sha256=file_sha256,
    )


def _parse_source(value: object) -> SourceBinding:
    source = _mapping(value, label="source")
    _exact_keys(source, {"kind", "source_id"}, label="source")
    return SourceBinding(
        kind=_string(source["kind"], label="source.kind"),
        source_id=_string(source["source_id"], label="source.source_id"),
    )


def _parse_context(value: object, *, index: int) -> ContextSpec:
    label = f"contexts[{index}]"
    context = _mapping(value, label=label)
    _exact_keys(
        context,
        {
            "context_id",
            "role",
            "family_id",
            "source_id",
            "template_id",
            "template_ids",
            "attention_mask",
            "observation_position",
        },
        label=label,
    )
    raw_template = context["template_ids"]
    if not isinstance(raw_template, list):
        raise ContextBankSchemaError(f"{label}.template_ids must be a list")
    template_ids: list[int | None] = []
    for token_index, token_id in enumerate(raw_template):
        if token_id is None:
            template_ids.append(None)
        else:
            template_ids.append(
                _integer(
                    token_id,
                    label=f"{label}.template_ids[{token_index}]",
                )
            )
    raw_mask = context["attention_mask"]
    if not isinstance(raw_mask, list):
        raise ContextBankSchemaError(f"{label}.attention_mask must be a list")
    attention_mask = tuple(
        _integer(value, label=f"{label}.attention_mask[{mask_index}]")
        for mask_index, value in enumerate(raw_mask)
    )
    return ContextSpec(
        context_id=_string(context["context_id"], label=f"{label}.context_id"),
        role=_enum(
            ContextRole,
            context["role"],
            label=f"{label}.role",
        ),
        family_id=_string(context["family_id"], label=f"{label}.family_id"),
        source_id=_string(context["source_id"], label=f"{label}.source_id"),
        template_id=_string(context["template_id"], label=f"{label}.template_id"),
        template_ids=tuple(template_ids),
        attention_mask=attention_mask,
        observation_position=_integer(
            context["observation_position"],
            label=f"{label}.observation_position",
        ),
    )


def _parse_bank(document: object) -> ContextBank:
    root = _mapping(document, label="context bank")
    _exact_keys(
        root,
        {
            "schema_version",
            "bank_id",
            "status",
            "license",
            "claim_eligible",
            "source",
            "model",
            "tokenizer",
            "sweep_domain",
            "contexts",
        },
        label="context bank",
    )
    if root["schema_version"] != CONTEXT_BANK_SCHEMA_VERSION:
        raise ContextBankSchemaError(
            f"unsupported context-bank schema {root['schema_version']!r}"
        )
    raw_contexts = root["contexts"]
    if not isinstance(raw_contexts, list) or not raw_contexts:
        raise ContextBankSchemaError("contexts must be a non-empty list")
    contexts = tuple(
        _parse_context(value, index=index) for index, value in enumerate(raw_contexts)
    )
    return ContextBank(
        bank_id=_string(root["bank_id"], label="bank_id"),
        status=_enum(BankStatus, root["status"], label="status"),
        license=_string(root["license"], label="license"),
        claim_eligible=_boolean(root["claim_eligible"], label="claim_eligible"),
        source=_parse_source(root["source"]),
        model=_parse_model(root["model"]),
        tokenizer=_parse_tokenizer(root["tokenizer"]),
        sweep_domain=_enum(SweepDomain, root["sweep_domain"], label="sweep_domain"),
        contexts=contexts,
    )


def context_bank_from_dict(document: Mapping[str, object]) -> ContextBank:
    """Validate canonical JSON-like bank content without reading YAML."""

    return _parse_bank(document)


def _coerce_allowed_roles(
    values: Collection[ContextRole | str],
) -> frozenset[ContextRole]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Collection):
        raise TypeError("allowed_roles must be a non-empty collection of roles")
    roles: set[ContextRole] = set()
    for value in values:
        if isinstance(value, ContextRole):
            roles.add(value)
            continue
        if isinstance(value, str):
            try:
                roles.add(ContextRole(value))
            except ValueError as exc:
                raise ContextBankSchemaError(f"unknown allowed role {value!r}") from exc
            continue
        raise TypeError("allowed_roles values must be ContextRole or str")
    if not roles:
        raise ContextBankSchemaError("allowed_roles must not be empty")
    if len(roles) != 1:
        raise ContextBankSchemaError(
            "allowed_roles must select exactly one experimental role"
        )
    return frozenset(roles)


def load_context_bank(
    path: str | Path,
    *,
    allowed_roles: Collection[ContextRole | str],
    expected_source_sha256: str | None = None,
    expected_canonical_sha256: str | None = None,
) -> LoadedContextBank:
    """Load one strict, single-role bank without implicit role filtering."""

    source_path = Path(path).resolve()
    with source_path.open("rb") as handle:
        raw = handle.read(MAX_CONTEXT_BANK_BYTES + 1)
    return _load_context_bank_from_bytes(
        raw,
        source_path=source_path,
        allowed_roles=allowed_roles,
        expected_source_sha256=expected_source_sha256,
        expected_canonical_sha256=expected_canonical_sha256,
    )


def _load_context_bank_from_bytes(
    raw: bytes,
    *,
    source_path: Path,
    allowed_roles: Collection[ContextRole | str],
    expected_source_sha256: str | None = None,
    expected_canonical_sha256: str | None = None,
) -> LoadedContextBank:
    """Validate already-opened ContextBank bytes without reopening their path."""

    if len(raw) > MAX_CONTEXT_BANK_BYTES:
        raise ContextBankSchemaError(
            f"context bank exceeds {MAX_CONTEXT_BANK_BYTES} bytes"
        )
    source_sha256 = hashlib.sha256(raw).hexdigest()
    if expected_source_sha256 is not None and source_sha256 != expected_source_sha256:
        raise ContextBankIntegrityError(
            "context-bank source SHA-256 does not match the expected digest"
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContextBankSchemaError("context bank must be UTF-8 YAML") from exc
    try:
        document = yaml.load(text, Loader=_StrictSafeLoader)
    except ContextBankSchemaError:
        raise
    except yaml.YAMLError as exc:
        raise ContextBankSchemaError(f"invalid context-bank YAML: {exc}") from exc
    bank = context_bank_from_dict(document)
    canonical_sha256 = bank.sha256
    if (
        expected_canonical_sha256 is not None
        and canonical_sha256 != expected_canonical_sha256
    ):
        raise ContextBankIntegrityError(
            "context-bank canonical SHA-256 does not match the expected digest"
        )
    allowed = _coerce_allowed_roles(allowed_roles)
    if bank.role not in allowed:
        raise ContextBankSchemaError(
            f"bank role {bank.role.value!r} is not in explicitly allowed roles "
            f"{sorted(role.value for role in allowed)!r}"
        )
    return LoadedContextBank(
        bank=bank,
        source_path=source_path,
        source_sha256=source_sha256,
        canonical_sha256=canonical_sha256,
    )
