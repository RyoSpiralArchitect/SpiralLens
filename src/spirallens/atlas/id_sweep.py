"""Fixed-context, batched token-ID sweeps for Pythia."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import torch

from spirallens.adapters import PythiaAdapter

from .store import ATLAS_SCHEMA_VERSION, AtlasStore, token_ids_sha256


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

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_dir", Path(self.output_dir))
        object.__setattr__(
            self, "context_ids", _integer_tuple(self.context_ids, label="context_ids")
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
        if self.sweep_position is not None:
            if not isinstance(self.sweep_position, int) or isinstance(
                self.sweep_position, bool
            ):
                raise TypeError("sweep_position must be an integer")
            if not 0 <= self.sweep_position < len(self.context_ids):
                raise ValueError(
                    f"sweep_position must be in [0, {len(self.context_ids) - 1}]"
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

    token_ids = select_token_ids(
        adapter.vocab_size,
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
    capture_metadata = {
        "atlas_schema_version": ATLAS_SCHEMA_VERSION,
        **adapter.capture_metadata(),
    }
    capture_fingerprint = _sha256_json(capture_metadata)
    config_fingerprint = _sha256_json(model_metadata["config"])
    if config.subset is None:
        selection_kind = (
            "full_vocabulary"
            if len(token_ids) == adapter.vocab_size
            else "vocabulary_prefix"
        )
    else:
        selection_kind = "subset"
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
        "observation_position": config.position,
        "sweep_position": config.effective_sweep_position,
        "selection": {
            "kind": selection_kind,
            "subset_size_before_limit": (
                adapter.vocab_size
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
    fingerprint_payload = {
        "schema_version": ATLAS_SCHEMA_VERSION,
        "model_id": adapter.model_id,
        "requested_model_revision": adapter.revision,
        "resolved_model_revision": model_metadata["resolved_revision"],
        "config_sha256": config_fingerprint,
        "context_ids": request["context_ids"],
        "attention_mask": request["attention_mask"],
        "position": config.position,
        "observation_position": config.position,
        "sweep_position": config.effective_sweep_position,
        "token_ids_sha256": request["token_ids_sha256"],
        "capture_dtype": request["capture_dtype"],
        "capture": capture_metadata,
    }

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
