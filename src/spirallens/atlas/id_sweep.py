"""Fixed-context, batched token-ID sweeps for Pythia."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np
import torch

from spirallens.adapters import PythiaAdapter
from spirallens.contexts import (
    OBSERVATION_KEY_SCHEMA_VERSION,
    ContextContractError,
    ContextRole,
    ContextSpec,
    LoadedContextBank,
    SweepDomain,
)

from .engineering_protocol import validate_engineering_request_binding
from .store import ATLAS_SCHEMA_VERSION, AtlasStore, token_ids_sha256


ATLAS_CONTEXT_BINDING_SCHEMA_VERSION = "spirallens.atlas-context-binding.v1"


@dataclass(frozen=True)
class ContextBankBinding:
    """Bind one validated bank entry to an atlas request without path identity."""

    loaded: LoadedContextBank
    context_id: str
    role: ContextRole

    def __post_init__(self) -> None:
        if not isinstance(self.loaded, LoadedContextBank):
            raise TypeError("loaded must be a LoadedContextBank")
        if not isinstance(self.context_id, str) or not self.context_id:
            raise TypeError("context_id must be a non-empty string")
        if not isinstance(self.role, ContextRole):
            raise TypeError("role must be a ContextRole")
        if self.loaded.canonical_sha256 != self.loaded.bank.sha256:
            raise ContextContractError(
                "loaded canonical SHA-256 does not match the context bank"
            )
        if (
            not isinstance(self.loaded.source_sha256, str)
            or len(self.loaded.source_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in self.loaded.source_sha256
            )
        ):
            raise ContextContractError(
                "loaded source SHA-256 must be a lowercase digest"
            )
        self.loaded.bank.require(self.context_id, role=self.role)

    @property
    def context(self) -> ContextSpec:
        return self.loaded.bank.require(self.context_id, role=self.role)

    @property
    def materialized_context_ids(self) -> tuple[int, ...]:
        """Return tensor-ready IDs with a deterministic overwritten slot fill."""

        return self.context.materialize(
            0,
            model_vocab_size=self.loaded.bank.model.vocab_size,
        )

    def to_dict(self) -> dict[str, object]:
        """Return the complete path-independent capture binding."""

        bank = self.loaded.bank
        context = self.context
        return {
            "schema_version": ATLAS_CONTEXT_BINDING_SCHEMA_VERSION,
            "bank": {
                "source_sha256": self.loaded.source_sha256,
                "canonical_sha256": self.loaded.canonical_sha256,
                "content": bank.to_dict(),
            },
            "selected_context": {
                "context_id": context.context_id,
                "role": context.role.value,
                "entry_order_index": next(
                    index
                    for index, item in enumerate(bank.contexts)
                    if item.context_id == context.context_id
                ),
                "context_spec_sha256": context.sha256,
                "context_input_sha256": context.input_sha256,
                "sweep_position": context.sweep_position,
                "observation_position": context.observation_position,
            },
            "tokenizer_provenance_sha256": bank.tokenizer.sha256,
            "observation_key_schema_version": OBSERVATION_KEY_SCHEMA_VERSION,
            "interpretation_contract": {
                "language_space_atlas": False,
                "semantic_unit": False,
                "decoded_strings_used_for_selection": False,
                "semantic_annotation_used": False,
                "sae_annotation_used": False,
                "projection_used": False,
            },
        }

    @property
    def sha256(self) -> str:
        return _sha256_json(self.to_dict())


@dataclass(frozen=True)
class SweepConfig:
    """Configuration for a deterministic token-ID activation sweep.

    ``position`` remains the observation position for backward compatibility.
    ``sweep_position`` selects the context slot replaced by each token ID and
    defaults to ``position`` when omitted.
    """

    output_dir: str | Path
    context_ids: tuple[int, ...] | list[int]
    position: int
    batch_size: int = 16
    subset: tuple[int, ...] | list[int] | None = None
    max_tokens: int | None = None
    attention_mask: tuple[int, ...] | list[int] | None = None
    resume: bool = False
    sweep_position: int | None = None
    context_bank_binding: ContextBankBinding | None = None
    public_example_plumbing_protocol_binding: (
        Mapping[str, object] | None
    ) = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_dir", Path(self.output_dir))
        object.__setattr__(
            self, "context_ids", _integer_tuple(self.context_ids, label="context_ids")
        )
        if self.context_bank_binding is not None:
            if not isinstance(self.context_bank_binding, ContextBankBinding):
                raise TypeError(
                    "context_bank_binding must be a ContextBankBinding"
                )
            binding = self.context_bank_binding
            if self.context_ids != binding.materialized_context_ids:
                raise ValueError(
                    "context_ids do not match the bound ContextSpec"
                )
            if self.attention_mask is None:
                object.__setattr__(
                    self,
                    "attention_mask",
                    binding.context.attention_mask,
                )
            if self.sweep_position is None:
                object.__setattr__(
                    self,
                    "sweep_position",
                    binding.context.sweep_position,
                )
        if self.public_example_plumbing_protocol_binding is not None:
            if self.context_bank_binding is None:
                raise ValueError(
                    "public-example plumbing requires a ContextBank binding"
                )
            protocol_binding = self.public_example_plumbing_protocol_binding
            if (
                not isinstance(protocol_binding, Mapping)
                or any(
                    not isinstance(key, str)
                    for key in protocol_binding
                )
            ):
                raise TypeError(
                    "public_example_plumbing_protocol_binding must be "
                    "a string-keyed mapping"
                )
            try:
                encoded_binding = json.dumps(
                    protocol_binding,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                    allow_nan=False,
                )
            except (TypeError, ValueError) as error:
                raise TypeError(
                    "public-example plumbing binding must be canonical-JSON "
                    "compatible"
                ) from error
            object.__setattr__(
                self,
                "public_example_plumbing_protocol_binding",
                json.loads(encoded_binding),
            )
        if self.subset is not None:
            object.__setattr__(
                self, "subset", _integer_tuple(self.subset, label="subset")
            )
        if self.attention_mask is not None:
            mask = _integer_tuple(self.attention_mask, label="attention_mask")
            if len(mask) != len(self.context_ids):
                raise ValueError("attention_mask length must match context_ids")
            if any(value not in (0, 1) for value in mask):
                raise ValueError("attention_mask values must be 0 or 1")
            object.__setattr__(self, "attention_mask", mask)
        if not self.context_ids:
            raise ValueError("context_ids must not be empty")
        if not isinstance(self.position, int) or isinstance(self.position, bool):
            raise TypeError("position must be an integer")
        if not 0 <= self.position < len(self.context_ids):
            raise ValueError(
                f"position must be in [0, {len(self.context_ids) - 1}]"
            )
        if (
            self.context_bank_binding is not None
            and self.position
            != self.context_bank_binding.context.observation_position
        ):
            raise ValueError(
                "position does not match the bound observation position"
            )
        if self.sweep_position is not None:
            if not isinstance(self.sweep_position, int) or isinstance(
                self.sweep_position, bool
            ):
                raise TypeError("sweep_position must be an integer")
            if not 0 <= self.sweep_position < len(self.context_ids):
                raise ValueError(
                    f"sweep_position must be in [0, {len(self.context_ids) - 1}]"
                )
        if (
            self.context_bank_binding is not None
            and self.effective_sweep_position
            != self.context_bank_binding.context.sweep_position
        ):
            raise ValueError(
                "sweep_position does not match the bound ContextSpec slot"
            )
        if (
            self.context_bank_binding is not None
            and self.attention_mask
            != self.context_bank_binding.context.attention_mask
        ):
            raise ValueError(
                "attention_mask does not match the bound ContextSpec"
            )
        if self.attention_mask is not None:
            if self.attention_mask[self.position] != 1:
                raise ValueError("the observation position must be attended")
            if self.attention_mask[self.effective_sweep_position] != 1:
                raise ValueError("the sweep position must be attended")
        if not isinstance(self.batch_size, int) or isinstance(self.batch_size, bool):
            raise TypeError("batch_size must be an integer")
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if self.max_tokens is not None:
            if not isinstance(self.max_tokens, int) or isinstance(
                self.max_tokens, bool
            ):
                raise TypeError("max_tokens must be an integer")
            if self.max_tokens <= 0:
                raise ValueError("max_tokens must be positive")

    @property
    def effective_sweep_position(self) -> int:
        """Return the context position replaced during the token-ID sweep."""

        return self.position if self.sweep_position is None else self.sweep_position


def _integer_tuple(values: Iterable[int], *, label: str) -> tuple[int, ...]:
    result: list[int] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
            raise TypeError(f"{label} values must be integers, got {value!r}")
        result.append(int(value))
    return tuple(result)


def select_token_ids(
    vocab_size: int,
    *,
    subset: Iterable[int] | None = None,
    max_tokens: int | None = None,
) -> np.ndarray:
    """Build an ordered, unique token-ID selection.

    ``subset=None`` selects the full vocabulary.  ``max_tokens`` is applied
    last, making a small plumbing smoke an explicit prefix of the eventual run.
    """

    if not isinstance(vocab_size, int) or isinstance(vocab_size, bool):
        raise TypeError("vocab_size must be an integer")
    if vocab_size <= 0:
        raise ValueError("vocab_size must be positive")
    if subset is None:
        values = tuple(range(vocab_size))
    else:
        values = _integer_tuple(subset, label="subset")
    if not values:
        raise ValueError("token selection must not be empty")
    if len(set(values)) != len(values):
        raise ValueError("token selection contains duplicate IDs")
    invalid = [value for value in values if not 0 <= value < vocab_size]
    if invalid:
        raise ValueError(
            f"token selection contains out-of-range IDs: {invalid[:5]}"
        )
    if max_tokens is not None:
        if not isinstance(max_tokens, int) or isinstance(max_tokens, bool):
            raise TypeError("max_tokens must be an integer")
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        values = values[:max_tokens]
    return np.asarray(values, dtype=np.int64)


def _sha256_json(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def run_id_sweep(adapter: PythiaAdapter, config: SweepConfig) -> dict[str, object]:
    """Stream a fixed-context token-ID sweep to a resumable atlas directory."""

    context_binding = config.context_bank_binding
    selection_vocab_size = adapter.vocab_size
    if context_binding is not None:
        bound_bank = context_binding.loaded.bank
        if adapter.model_id != bound_bank.model.model_id:
            raise ValueError(
                "adapter model ID does not match the bound context bank"
            )
        if adapter.vocab_size != bound_bank.model.vocab_size:
            raise ValueError(
                "adapter vocabulary size does not match the bound context bank"
            )
        if bound_bank.sweep_domain is SweepDomain.TOKENIZER_ADDRESSABLE:
            selection_vocab_size = bound_bank.tokenizer.addressable_size

    token_ids = select_token_ids(
        selection_vocab_size,
        subset=config.subset,
        max_tokens=config.max_tokens,
    )
    for value in config.context_ids:
        if not 0 <= value < adapter.vocab_size:
            raise ValueError(
                f"context token ID {value} is outside vocabulary "
                f"[0, {adapter.vocab_size - 1}]"
            )

    model_metadata = adapter.config_metadata()
    if model_metadata["resolved_revision"] is None:
        raise ValueError(
            "model revision could not be resolved; construct PythiaAdapter with "
            "an explicit immutable revision for an auditable sweep"
        )
    if (
        context_binding is not None
        and model_metadata["resolved_revision"]
        != context_binding.loaded.bank.model.resolved_revision
    ):
        raise ValueError(
            "adapter resolved revision does not match the bound context bank"
        )
    capture_metadata = {
        "atlas_schema_version": ATLAS_SCHEMA_VERSION,
        **adapter.capture_metadata(),
    }
    capture_fingerprint = _sha256_json(capture_metadata)
    config_fingerprint = _sha256_json(model_metadata["config"])
    sweep_domain = (
        context_binding.loaded.bank.sweep_domain
        if context_binding is not None
        else SweepDomain.MODEL_EMBEDDING_ROWS
    )
    if config.subset is None:
        if len(token_ids) == selection_vocab_size:
            selection_kind = (
                "full_vocabulary"
                if sweep_domain is SweepDomain.MODEL_EMBEDDING_ROWS
                else "full_tokenizer_addressable"
            )
        else:
            selection_kind = (
                "vocabulary_prefix"
                if sweep_domain is SweepDomain.MODEL_EMBEDDING_ROWS
                else "tokenizer_addressable_prefix"
            )
    else:
        selection_kind = "subset"
    binding_payload = (
        None if context_binding is None else context_binding.to_dict()
    )
    engineering_binding = (
        None
        if config.public_example_plumbing_protocol_binding is None
        else deepcopy(
            dict(config.public_example_plumbing_protocol_binding)
        )
    )
    request: dict[str, object] = {
        "model_id": adapter.model_id,
        "requested_model_revision": adapter.revision,
        "resolved_model_revision": model_metadata["resolved_revision"],
        "context_ids": list(config.context_ids),
        "attention_mask": (
            list(config.attention_mask)
            if config.attention_mask is not None
            else [1] * len(config.context_ids)
        ),
        "position": config.position,
        "selection": {
            "kind": selection_kind,
            "subset_size_before_limit": (
                selection_vocab_size
                if config.subset is None
                else len(config.subset)
            ),
            "max_tokens": config.max_tokens,
        },
        "num_tokens": int(len(token_ids)),
        "token_ids_sha256": token_ids_sha256(token_ids),
        "batch_size_initial": config.batch_size,
        "batch_size_latest": config.batch_size,
        "capture_dtype": "float32",
        "capture_fingerprint": capture_fingerprint,
        "config_sha256": config_fingerprint,
    }
    uses_position_split = (
        config.sweep_position is not None or context_binding is not None
    )
    if uses_position_split:
        request.update(
            {
                "observation_position": config.position,
                "sweep_position": config.effective_sweep_position,
            }
        )
    if context_binding is not None:
        request.update(
            {
                "context_bank_binding": binding_payload,
                "context_bank_binding_sha256": context_binding.sha256,
                "token_domain": {
                    "kind": sweep_domain.value,
                    "size": selection_vocab_size,
                    "model_vocab_size": adapter.vocab_size,
                    "tokenizer_addressable_size": (
                        context_binding.loaded.bank.tokenizer.addressable_size
                    ),
                },
                "language_space_atlas": False,
                "semantic_unit": False,
            }
        )
        if engineering_binding is not None:
            model_files = engineering_binding.get("model_files_verified")
            model_file_mapping = (
                model_files if isinstance(model_files, Mapping) else {}
            )
            request.update(
                {
                    "output_id": config.output_dir.name,
                    "config_blob_sha256": model_file_mapping.get(
                        "config.json"
                    ),
                    "model_blob_sha256": model_file_mapping.get(
                        "model.safetensors"
                    ),
                    "public_example_plumbing_protocol_binding": (
                        engineering_binding
                    ),
                    "public_example_plumbing_protocol_binding_sha256": (
                        _sha256_json(engineering_binding)
                    ),
                }
            )
            validate_engineering_request_binding(
                request,
                manifest_model=model_metadata,
            )
        request_identity = dict(request)
        request_identity.pop("batch_size_initial")
        request_identity.pop("batch_size_latest")
        request["request_identity_sha256"] = _sha256_json(request_identity)
    fingerprint_payload = {
        "schema_version": ATLAS_SCHEMA_VERSION,
        "model_id": adapter.model_id,
        "requested_model_revision": adapter.revision,
        "resolved_model_revision": model_metadata["resolved_revision"],
        "config_sha256": config_fingerprint,
        "context_ids": request["context_ids"],
        "attention_mask": request["attention_mask"],
        "position": config.position,
        "token_ids_sha256": request["token_ids_sha256"],
        "capture_dtype": request["capture_dtype"],
        "capture": capture_metadata,
    }
    if uses_position_split:
        fingerprint_payload.update(
            {
                "observation_position": config.position,
                "sweep_position": config.effective_sweep_position,
            }
        )
    if context_binding is not None:
        fingerprint_payload.update(
            {
                "context_bank_binding": binding_payload,
                "context_bank_binding_sha256": request[
                    "context_bank_binding_sha256"
                ],
                "token_domain": request["token_domain"],
                "language_space_atlas": False,
                "semantic_unit": False,
                "request_identity_sha256": request[
                    "request_identity_sha256"
                ],
            }
        )
        if engineering_binding is not None:
            fingerprint_payload.update(
                {
                    "public_example_plumbing_protocol_binding": (
                        engineering_binding
                    ),
                    "public_example_plumbing_protocol_binding_sha256": (
                        request[
                            "public_example_plumbing_protocol_binding_sha256"
                        ]
                    ),
                }
            )

    store = AtlasStore.initialize(
        output_dir=Path(config.output_dir),
        token_ids=token_ids,
        model_metadata=model_metadata,
        request=request,
        fingerprint_payload=fingerprint_payload,
        capture_metadata=capture_metadata,
        resume=config.resume,
        batch_size=config.batch_size,
    )
    try:
        if store.is_complete:
            return dict(store.manifest)

        context = torch.tensor(config.context_ids, dtype=torch.long)
        base_mask = torch.tensor(
            request["attention_mask"], dtype=torch.long
        )
        for start in range(
            store.completed_rows, len(token_ids), config.batch_size
        ):
            end = min(start + config.batch_size, len(token_ids))
            batch_token_ids = torch.from_numpy(token_ids[start:end].copy())
            input_ids = context.unsqueeze(0).repeat(end - start, 1)
            input_ids[:, config.effective_sweep_position] = batch_token_ids
            attention_mask = base_mask.unsqueeze(0).repeat(end - start, 1)
            observation = adapter.observe_batch(
                input_ids,
                position=config.position,
                attention_mask=attention_mask,
            )
            store.write_batch(start, observation)
        return store.finalize()
    except BaseException as exc:
        store.mark_failed(exc)
        raise
    finally:
        store.close()
