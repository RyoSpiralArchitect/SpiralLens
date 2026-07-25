"""Blockwise discovery of cosine-near, drift-divergent structural candidates.

Discovery consumes only atlas activations and preregistered numeric gates.
Token strings, SAE labels, minimal-pair classes, and other semantic annotations
are deliberately absent from this module.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
from numbers import Integral, Real
from typing import TYPE_CHECKING, Any
import uuid

import numpy as np
from numpy.typing import ArrayLike, NDArray
import yaml

from spirallens.neighbors import (
    ExactBlockwiseBackend,
    NeighborBackend,
    NeighborBackendDescriptor,
    NeighborIndexBuildReceipt,
    NeighborPair,
    NeighborQuery,
    canonical_json_sha256,
    exact_state_pair_metrics,
    finite_row_norms,
    state_matrix_sha256,
    state_pair_passes_query,
    validate_prepared_backend,
    validate_neighbor_pairs,
)

if TYPE_CHECKING:
    from spirallens.execution_freeze import ValidatedExecutionFreeze

    from .neighbor_audit import (
        NeighborAuditConfig,
        NeighborAuditProtocolBinding,
        NeighborAuditResult,
    )


CANDIDATE_SCHEMA_VERSION = "spirallens.candidate.v0.3"
LEDGER_SCHEMA_VERSION = "spirallens.candidate-ledger.v0.3"
EXACT_RERANK_CONTRACT_VERSION = "spirallens.candidate-exact-rerank.v0.1"
NEIGHBOR_RETRIEVAL_BINDING_SCHEMA_VERSION = (
    "spirallens.neighbor-retrieval-binding.v0.1"
)


@dataclass(frozen=True)
class CandidateSearchConfig:
    """Preregistered structural gates for pair discovery."""

    cosine_min: float = 0.995
    relative_norm_gap_max: float = 0.05
    drift_relative_divergence_min: float = 0.5
    drift_absolute_divergence_min: float = 0.0
    min_state_norm: float = 1e-8
    min_drift_norm: float = 1e-8
    block_size: int = 1024
    max_pairwise_rows: int = 10_000
    epsilon: float = 1e-12
    layer_indices: tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        numeric_fields = (
            "cosine_min",
            "relative_norm_gap_max",
            "drift_relative_divergence_min",
            "drift_absolute_divergence_min",
            "min_state_norm",
            "min_drift_norm",
            "epsilon",
        )
        for field_name in numeric_fields:
            value = getattr(self, field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, Real)
                or not np.isfinite(value)
            ):
                raise TypeError(f"{field_name} must be a finite real number")
        if not -1.0 <= self.cosine_min <= 1.0:
            raise ValueError("cosine_min must lie in [-1, 1]")
        if self.relative_norm_gap_max < 0.0:
            raise ValueError("relative_norm_gap_max must be non-negative")
        if self.drift_relative_divergence_min < 0.0:
            raise ValueError("drift_relative_divergence_min must be non-negative")
        if self.drift_absolute_divergence_min < 0.0:
            raise ValueError("drift_absolute_divergence_min must be non-negative")
        if self.min_state_norm < 0.0:
            raise ValueError("min_state_norm must be non-negative")
        if self.min_drift_norm <= 0.0:
            raise ValueError(
                "min_drift_norm must be positive so drift direction is defined"
            )
        for field_name in ("block_size", "max_pairwise_rows"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, Integral):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
        if self.epsilon <= 0.0:
            raise ValueError("epsilon must be positive")
        if self.layer_indices is not None:
            if any(
                isinstance(index, bool) or not isinstance(index, Integral)
                for index in self.layer_indices
            ):
                raise TypeError("layer_indices must contain integers")
            canonical = tuple(int(index) for index in self.layer_indices)
            if any(index < 0 for index in canonical):
                raise ValueError("layer_indices must be non-negative")
            if len(set(canonical)) != len(canonical):
                raise ValueError("layer_indices must not contain duplicates")
            object.__setattr__(self, "layer_indices", canonical)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        if self.layer_indices is not None:
            result["layer_indices"] = list(self.layer_indices)
        return result


@dataclass(frozen=True)
class LedgerSummary:
    """Summary returned after an atomically completed ledger write."""

    output_path: Path
    candidate_count: int
    header_count: int = 1
    footer_count: int = 1


def atlas_global_row_key_sha256(
    *,
    token_ids: ArrayLike,
    request: Mapping[str, Any],
) -> str:
    """Bind the immutable ordered row universe used by every layer index."""

    token_values = np.asanyarray(token_ids)
    if token_values.ndim != 1:
        raise ValueError("token_ids must have shape (observations,)")
    if not isinstance(request, Mapping):
        raise ValueError("atlas row identity provenance is invalid")
    return canonical_json_sha256(
        {
            "schema_version": "spirallens.global-row-key.v0.2",
            "token_ids_sha256": state_matrix_sha256(
                token_values.reshape(-1, 1)
            ),
            "row_count": int(token_values.shape[0]),
            "model_id": request.get("model_id"),
            "resolved_model_revision": request.get(
                "resolved_model_revision"
            ),
            "context_bank_binding_sha256": request.get(
                "context_bank_binding_sha256"
            ),
            "context_ids": request.get("context_ids"),
            "attention_mask": request.get("attention_mask"),
            "sweep_position": request.get("sweep_position"),
            "observation_position": request.get(
                "observation_position",
                request.get("position"),
            ),
            "token_domain": request.get("token_domain"),
            "selection": request.get("selection"),
        }
    )


def _validate_neighbor_audit_atlas_scope(
    *,
    manifest: Mapping[str, Any],
    token_ids: ArrayLike,
    layer_index: int,
) -> None:
    """Require one ContextBank-bound, exact model-vocabulary audit scope."""

    request = manifest.get("request")
    model = manifest.get("model")
    if not isinstance(request, Mapping) or not isinstance(model, Mapping):
        raise ValueError("neighbor audit atlas provenance is incomplete")
    token_values = np.asanyarray(token_ids)
    if token_values.ndim != 1:
        raise ValueError(
            "neighbor audit requires one-dimensional atlas token_ids"
        )
    row_count = int(token_values.shape[0])
    if row_count <= 0:
        raise ValueError("neighbor audit requires a non-empty atlas")
    if token_values.dtype != np.dtype(np.int64):
        raise ValueError("neighbor audit requires int64 atlas token_ids")

    progress = manifest.get("progress")
    arrays = manifest.get("arrays")
    token_descriptor = (
        arrays.get("token_ids")
        if isinstance(arrays, Mapping)
        else None
    )
    resid_pre_descriptor = (
        arrays.get("resid_pre")
        if isinstance(arrays, Mapping)
        else None
    )
    resid_post_descriptor = (
        arrays.get("resid_post")
        if isinstance(arrays, Mapping)
        else None
    )
    resid_pre_shape = (
        resid_pre_descriptor.get("shape")
        if isinstance(resid_pre_descriptor, Mapping)
        else None
    )
    resid_post_shape = (
        resid_post_descriptor.get("shape")
        if isinstance(resid_post_descriptor, Mapping)
        else None
    )
    num_layers = model.get("num_layers")
    hidden_size = model.get("hidden_size")
    if (
        manifest.get("status") != "complete"
        or not isinstance(progress, Mapping)
        or progress.get("completed_rows") != row_count
        or progress.get("total_rows") != row_count
        or not isinstance(token_descriptor, Mapping)
        or token_descriptor.get("shape") != [row_count]
        or isinstance(num_layers, bool)
        or not isinstance(num_layers, Integral)
        or int(num_layers) <= 0
        or isinstance(hidden_size, bool)
        or not isinstance(hidden_size, Integral)
        or int(hidden_size) <= 0
        or resid_pre_shape
        != [row_count, int(num_layers), int(hidden_size)]
        or resid_post_shape != resid_pre_shape
        or isinstance(layer_index, bool)
        or not isinstance(layer_index, Integral)
        or not 0 <= int(layer_index) < int(num_layers)
    ):
        raise ValueError(
            "neighbor audit requires one complete, layer-compatible atlas"
        )

    context_binding = request.get("context_bank_binding")
    context_binding_sha256 = request.get(
        "context_bank_binding_sha256"
    )
    if (
        not isinstance(context_binding, Mapping)
        or not _is_lower_sha256(context_binding_sha256)
    ):
        raise ValueError(
            "neighbor audit requires a ContextBank-bound atlas"
        )

    bank = context_binding.get("bank")
    bank_content = (
        bank.get("content")
        if isinstance(bank, Mapping)
        else None
    )
    if (
        not isinstance(bank_content, Mapping)
        or bank_content.get("sweep_domain")
        != "model_embedding_rows"
    ):
        raise ValueError(
            "neighbor audit requires a model_embedding_rows ContextBank"
        )

    selection = request.get("selection")
    expected_selection = {
        "kind": "full_vocabulary",
        "subset_size_before_limit": row_count,
        "max_tokens": None,
    }
    if selection != expected_selection:
        raise ValueError(
            "neighbor audit requires an exact full-vocabulary selection"
        )

    token_domain = request.get("token_domain")
    model_vocab_size = model.get("vocab_size")
    if (
        isinstance(model_vocab_size, bool)
        or not isinstance(model_vocab_size, Integral)
        or int(model_vocab_size) != row_count
        or isinstance(request.get("num_tokens"), bool)
        or not isinstance(request.get("num_tokens"), Integral)
        or int(request["num_tokens"]) != row_count
        or not isinstance(token_domain, Mapping)
        or token_domain.get("kind") != "model_embedding_rows"
        or isinstance(token_domain.get("size"), bool)
        or not isinstance(token_domain.get("size"), Integral)
        or int(token_domain["size"]) != row_count
        or isinstance(token_domain.get("model_vocab_size"), bool)
        or not isinstance(
            token_domain.get("model_vocab_size"),
            Integral,
        )
        or int(token_domain["model_vocab_size"]) != row_count
    ):
        raise ValueError(
            "neighbor audit atlas vocabulary dimensions are inconsistent"
        )

    if (
        request.get("language_space_atlas") is not False
        or request.get("semantic_unit") is not False
    ):
        raise ValueError(
            "neighbor audit requires semantics-free atlas scope flags"
        )

    expected_token_ids = np.arange(row_count, dtype=np.int64)
    if (
        not np.issubdtype(token_values.dtype, np.integer)
        or not np.array_equal(token_values, expected_token_ids)
    ):
        raise ValueError(
            "neighbor audit requires ordered token_ids 0..vocab_size-1"
        )


def load_candidate_config_from_protocol(
    protocol_path: str | Path,
    *,
    block_size_override: int | None = None,
) -> CandidateSearchConfig:
    """Load only the candidate-search section from a YAML protocol."""

    path = Path(protocol_path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("protocol must contain a YAML mapping")
    search = payload.get("candidate_search")
    if not isinstance(search, Mapping):
        raise ValueError("protocol is missing a candidate_search mapping")

    allowed = {field.name for field in CandidateSearchConfig.__dataclass_fields__.values()}
    unknown = set(search) - allowed
    if unknown:
        raise ValueError(f"unknown candidate_search fields: {sorted(unknown)}")
    values = dict(search)
    if "layer_indices" in values and values["layer_indices"] is not None:
        values["layer_indices"] = tuple(values["layer_indices"])
    config = CandidateSearchConfig(**values)
    if block_size_override is not None:
        config = replace(config, block_size=block_size_override)
    return config


def _finite_block(
    array: NDArray[np.generic],
    start: int,
    stop: int,
    *,
    label: str,
) -> NDArray[np.float64]:
    block = np.asarray(array[start:stop], dtype=np.float64)
    if block.ndim != 2:
        raise ValueError(f"{label} must be a two-dimensional row matrix")
    if not np.all(np.isfinite(block)):
        raise ValueError(f"{label}[{start}:{stop}] contains non-finite values")
    return block


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        value = float(value)
    if isinstance(value, float):
        if not np.isfinite(value):
            raise ValueError("persisted candidate values must be finite")
        return value
    if isinstance(value, Path):
        return str(value)
    return value


def _is_lower_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _reference_for_row(
    references: Sequence[Mapping[str, Any]] | None,
    index: int,
) -> dict[str, Any]:
    if references is None:
        return {"row_index": index}
    reference = dict(references[index])
    supplied_index = reference.get("row_index", index)
    if (
        isinstance(supplied_index, bool)
        or not isinstance(supplied_index, Integral)
        or int(supplied_index) != index
    ):
        raise ValueError(
            f"references[{index}].row_index must equal its matrix row"
        )
    reference["row_index"] = index
    return _json_safe(reference)


def _candidate_id(
    *,
    source_run_id: str,
    group_key: str,
    left_reference: Mapping[str, Any],
    right_reference: Mapping[str, Any],
) -> str:
    identity = {
        "source_run_id": source_run_id,
        "group_key": group_key,
        "left": left_reference,
        "right": right_reference,
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "cand_" + hashlib.sha256(encoded).hexdigest()[:24]


def _finite_metric_mapping(
    payload: object,
    *,
    required_fields: set[str],
    label: str,
) -> Mapping[str, Real]:
    if not isinstance(payload, Mapping) or set(payload) != required_fields:
        raise ValueError(f"candidate {label} fields are invalid")
    for field_name, value in payload.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not np.isfinite(value)
        ):
            raise ValueError(
                f"candidate {label}.{field_name} must be finite"
            )
    return payload


def _validate_candidate_payload_shape(
    candidate: Mapping[str, Any],
    *,
    config: CandidateSearchConfig,
    expected_source_run_id: str | None = None,
    expected_row_count: int | None = None,
) -> None:
    required_fields = {
        "schema_version",
        "record_type",
        "candidate_id",
        "candidate_kind",
        "claim_level",
        "source_run_id",
        "comparison_group",
        "left",
        "right",
        "state_metrics",
        "drift_metrics",
        "retrieval",
        "discovery",
        "gates",
    }
    claim_level = candidate.get("claim_level")
    if (
        set(candidate) != required_fields
        or candidate.get("schema_version") != CANDIDATE_SCHEMA_VERSION
        or candidate.get("record_type") != "candidate"
        or candidate.get("candidate_kind")
        != "cosine_near_drift_divergent"
        or isinstance(claim_level, bool)
        or not isinstance(claim_level, Integral)
        or int(claim_level) != 1
    ):
        raise ValueError("candidate record shape is invalid")
    source_run_id = candidate.get("source_run_id")
    group_key = candidate.get("comparison_group")
    left = candidate.get("left")
    right = candidate.get("right")
    if (
        not isinstance(source_run_id, str)
        or not source_run_id
        or not isinstance(group_key, str)
        or not group_key
        or not isinstance(left, Mapping)
        or not isinstance(right, Mapping)
    ):
        raise ValueError("candidate identity fields are invalid")
    if (
        expected_source_run_id is not None
        and source_run_id != expected_source_run_id
    ):
        raise ValueError(
            "candidate source_run_id differs from the ledger source"
        )
    left_index = left.get("row_index")
    right_index = right.get("row_index")
    if (
        isinstance(left_index, bool)
        or not isinstance(left_index, Integral)
        or isinstance(right_index, bool)
        or not isinstance(right_index, Integral)
        or int(left_index) < 0
        or int(left_index) >= int(right_index)
        or (
            expected_row_count is not None
            and int(right_index) >= expected_row_count
        )
    ):
        raise ValueError("candidate row identity is invalid")
    if group_key.startswith("layer_index="):
        try:
            expected_layer_index = int(
                group_key.removeprefix("layer_index=")
            )
        except ValueError as error:
            raise ValueError(
                "candidate layer group is invalid"
            ) from error
        for reference in (left, right):
            layer_index = reference.get("layer_index")
            if (
                isinstance(layer_index, bool)
                or not isinstance(layer_index, Integral)
                or int(layer_index) != expected_layer_index
            ):
                raise ValueError(
                    "candidate reference layer differs from its group"
                )
    if candidate.get("candidate_id") != _candidate_id(
        source_run_id=source_run_id,
        group_key=group_key,
        left_reference=left,
        right_reference=right,
    ):
        raise ValueError("candidate stable identity is invalid")
    state_metrics = _finite_metric_mapping(
        candidate.get("state_metrics"),
        required_fields={
            "cosine_similarity",
            "norm_a",
            "norm_b",
            "euclidean_distance",
            "radial_distance",
            "angular_distance",
            "relative_norm_gap",
            "angular_fraction_sq",
            "unit_chord_distance",
        },
        label="state_metrics",
    )
    drift_metrics = _finite_metric_mapping(
        candidate.get("drift_metrics"),
        required_fields={
            "norm_a",
            "norm_b",
            "cosine_similarity",
            "divergence",
            "relative_divergence",
            "radial_divergence",
            "angular_divergence",
            "angular_fraction_sq",
        },
        label="drift_metrics",
    )
    if (
        state_metrics["cosine_similarity"] < config.cosine_min
        or state_metrics["relative_norm_gap"]
        > config.relative_norm_gap_max
        or state_metrics["norm_a"] < config.min_state_norm
        or state_metrics["norm_b"] < config.min_state_norm
        or drift_metrics["norm_a"] < config.min_drift_norm
        or drift_metrics["norm_b"] < config.min_drift_norm
        or drift_metrics["divergence"]
        < config.drift_absolute_divergence_min
        or drift_metrics["relative_divergence"]
        < config.drift_relative_divergence_min
    ):
        raise ValueError("candidate does not satisfy its declared gates")
    norm_a = float(state_metrics["norm_a"])
    norm_b = float(state_metrics["norm_b"])
    cosine = float(state_metrics["cosine_similarity"])
    drift_norm_a = float(drift_metrics["norm_a"])
    drift_norm_b = float(drift_metrics["norm_b"])
    drift_cosine = float(drift_metrics["cosine_similarity"])
    drift_divergence = float(drift_metrics["divergence"])
    if (
        norm_a < 0.0
        or norm_b < 0.0
        or not -1.0 <= cosine <= 1.0
        or drift_norm_a < 0.0
        or drift_norm_b < 0.0
        or not -1.0 <= drift_cosine <= 1.0
        or drift_divergence < 0.0
    ):
        raise ValueError("candidate metric domain is invalid")
    radial = abs(norm_a - norm_b)
    angular_sq = max(
        0.0,
        2.0 * norm_a * norm_b * (1.0 - cosine),
    )
    euclidean_sq = radial**2 + angular_sq
    drift_radial = abs(drift_norm_a - drift_norm_b)
    drift_angular_sq = max(
        0.0,
        2.0
        * drift_norm_a
        * drift_norm_b
        * (1.0 - drift_cosine),
    )
    expected_state_metrics = {
        "euclidean_distance": np.sqrt(euclidean_sq),
        "radial_distance": radial,
        "angular_distance": np.sqrt(angular_sq),
        "relative_norm_gap": radial
        / max(0.5 * (norm_a + norm_b), config.epsilon),
        "angular_fraction_sq": angular_sq
        / max(euclidean_sq, config.epsilon),
        "unit_chord_distance": np.sqrt(
            max(0.0, 2.0 * (1.0 - cosine))
        ),
    }
    expected_drift_metrics = {
        "relative_divergence": drift_divergence
        / max(
            0.5 * (drift_norm_a + drift_norm_b),
            config.epsilon,
        ),
        "radial_divergence": drift_radial,
        "angular_divergence": np.sqrt(drift_angular_sq),
        "angular_fraction_sq": drift_angular_sq
        / max(drift_divergence**2, config.epsilon),
    }
    absolute_tolerance = max(1e-12, 32.0 * config.epsilon)
    if (
        any(
            not np.isclose(
                state_metrics[field_name],
                expected,
                rtol=1e-9,
                atol=absolute_tolerance,
            )
            for field_name, expected in expected_state_metrics.items()
        )
        or any(
            not np.isclose(
                drift_metrics[field_name],
                expected,
                rtol=1e-9,
                atol=absolute_tolerance,
            )
            for field_name, expected in expected_drift_metrics.items()
        )
        or not np.isclose(
            drift_divergence**2,
            drift_radial**2 + drift_angular_sq,
            rtol=1e-8,
            atol=absolute_tolerance,
        )
    ):
        raise ValueError("candidate metric identities are inconsistent")
    if candidate.get("discovery") != {
        "semantic_annotation_used": False,
        "sae_annotation_used": False,
        "projection_used": False,
    }:
        raise ValueError("candidate discovery contract is invalid")
    if candidate.get("gates") != {
        "cosine_min": config.cosine_min,
        "relative_norm_gap_max": config.relative_norm_gap_max,
        "drift_relative_divergence_min": (
            config.drift_relative_divergence_min
        ),
        "drift_absolute_divergence_min": (
            config.drift_absolute_divergence_min
        ),
    }:
        raise ValueError("candidate gates differ from the ledger header")


def _iter_candidate_pairs_v0_1_oracle(
    states: ArrayLike,
    drifts: ArrayLike,
    *,
    references: Sequence[Mapping[str, Any]] | None = None,
    config: CandidateSearchConfig | None = None,
    source_run_id: str = "array-input",
    group_key: str = "ungrouped",
) -> Iterator[dict[str, Any]]:
    """Frozen pre-backend oracle retained for parity regression tests.

    Args:
        states: Row matrix ``(observations, hidden)`` at the input of a
            transformation.
        drifts: Matching row matrix of ``output - input`` updates.
        references: Optional JSON-ready identity metadata for every row.
        config: Numeric gates and the pairwise block size.
        source_run_id: Provenance identifier used in stable candidate IDs.
        group_key: Declares the controlled comparison slice, typically a layer.
    """

    settings = config or CandidateSearchConfig()
    state_rows = states if hasattr(states, "shape") else np.asanyarray(states)
    drift_rows = drifts if hasattr(drifts, "shape") else np.asanyarray(drifts)
    if state_rows.ndim != 2 or drift_rows.ndim != 2:
        raise ValueError("states and drifts must both have shape (observations, hidden)")
    if state_rows.shape != drift_rows.shape:
        raise ValueError(f"state/drift shape mismatch: {state_rows.shape} != {drift_rows.shape}")
    if references is not None and len(references) != state_rows.shape[0]:
        raise ValueError("references length must equal the number of observations")
    if state_rows.shape[0] > settings.max_pairwise_rows:
        raise ValueError(
            "exact pairwise candidate search is bounded to "
            f"max_pairwise_rows={settings.max_pairwise_rows}, but received "
            f"{state_rows.shape[0]} rows; use a preregistered subset until the "
            "audited ANN retrieval stage lands"
        )

    n_rows = state_rows.shape[0]
    state_norms = finite_row_norms(
        state_rows,
        block_size=settings.block_size,
        label="states",
    )
    drift_norms = finite_row_norms(
        drift_rows,
        block_size=settings.block_size,
        label="drifts",
    )

    for left_start in range(0, n_rows, settings.block_size):
        left_stop = min(left_start + settings.block_size, n_rows)
        left_states = _finite_block(state_rows, left_start, left_stop, label="states")
        left_state_norms = state_norms[left_start:left_stop]
        left_unit = left_states / np.maximum(left_state_norms[:, None], settings.epsilon)

        for right_start in range(left_start, n_rows, settings.block_size):
            right_stop = min(right_start + settings.block_size, n_rows)
            right_states = _finite_block(state_rows, right_start, right_stop, label="states")
            right_state_norms = state_norms[right_start:right_stop]
            right_unit = right_states / np.maximum(right_state_norms[:, None], settings.epsilon)

            cosine_block = np.clip(left_unit @ right_unit.T, -1.0, 1.0)
            mean_norm = 0.5 * (
                left_state_norms[:, None] + right_state_norms[None, :]
            )
            relative_norm_gap = np.abs(
                left_state_norms[:, None] - right_state_norms[None, :]
            ) / np.maximum(mean_norm, settings.epsilon)
            eligible = (
                (left_state_norms[:, None] >= settings.min_state_norm)
                & (right_state_norms[None, :] >= settings.min_state_norm)
                & (cosine_block >= settings.cosine_min)
                & (relative_norm_gap <= settings.relative_norm_gap_max)
            )
            if left_start == right_start:
                eligible &= np.triu(np.ones_like(eligible, dtype=bool), k=1)
            if not np.any(eligible):
                continue

            local_left, local_right = np.nonzero(eligible)
            global_left = local_left + left_start
            global_right = local_right + right_start

            left_drifts = _finite_block(drift_rows, left_start, left_stop, label="drifts")
            right_drifts = _finite_block(drift_rows, right_start, right_stop, label="drifts")
            selected_left_drift = left_drifts[local_left]
            selected_right_drift = right_drifts[local_right]
            drift_difference = selected_left_drift - selected_right_drift
            drift_divergence = np.linalg.norm(drift_difference, axis=1)
            selected_left_drift_norm = drift_norms[global_left]
            selected_right_drift_norm = drift_norms[global_right]
            mean_drift_norm = 0.5 * (
                selected_left_drift_norm + selected_right_drift_norm
            )
            relative_drift_divergence = drift_divergence / np.maximum(
                mean_drift_norm,
                settings.epsilon,
            )
            drift_eligible = (
                (selected_left_drift_norm >= settings.min_drift_norm)
                & (selected_right_drift_norm >= settings.min_drift_norm)
                & (drift_divergence >= settings.drift_absolute_divergence_min)
                & (
                    relative_drift_divergence
                    >= settings.drift_relative_divergence_min
                )
            )

            for offset in np.flatnonzero(drift_eligible):
                left_index = int(global_left[offset])
                right_index = int(global_right[offset])
                cosine = float(cosine_block[local_left[offset], local_right[offset]])
                norm_a = float(state_norms[left_index])
                norm_b = float(state_norms[right_index])
                radial_distance = abs(norm_a - norm_b)
                angular_sq = max(0.0, 2.0 * norm_a * norm_b * (1.0 - cosine))
                state_distance_sq = radial_distance**2 + angular_sq

                drift_norm_a = float(selected_left_drift_norm[offset])
                drift_norm_b = float(selected_right_drift_norm[offset])
                drift_cosine = float(
                    np.clip(
                        np.dot(
                            selected_left_drift[offset],
                            selected_right_drift[offset],
                        )
                        / (drift_norm_a * drift_norm_b),
                        -1.0,
                        1.0,
                    )
                )
                drift_radial = abs(drift_norm_a - drift_norm_b)
                drift_angular_sq = max(
                    0.0,
                    2.0 * drift_norm_a * drift_norm_b * (1.0 - drift_cosine),
                )

                left_reference = _reference_for_row(references, left_index)
                right_reference = _reference_for_row(references, right_index)
                yield {
                    "schema_version": CANDIDATE_SCHEMA_VERSION,
                    "record_type": "candidate",
                    "candidate_id": _candidate_id(
                        source_run_id=source_run_id,
                        group_key=group_key,
                        left_reference=left_reference,
                        right_reference=right_reference,
                    ),
                    "candidate_kind": "cosine_near_drift_divergent",
                    "claim_level": 1,
                    "source_run_id": source_run_id,
                    "comparison_group": group_key,
                    "left": left_reference,
                    "right": right_reference,
                    "state_metrics": {
                        "cosine_similarity": cosine,
                        "norm_a": norm_a,
                        "norm_b": norm_b,
                        "euclidean_distance": float(np.sqrt(state_distance_sq)),
                        "radial_distance": radial_distance,
                        "angular_distance": float(np.sqrt(angular_sq)),
                        "relative_norm_gap": radial_distance
                        / max(0.5 * (norm_a + norm_b), settings.epsilon),
                        "angular_fraction_sq": angular_sq
                        / max(state_distance_sq, settings.epsilon),
                        "unit_chord_distance": float(
                            np.sqrt(max(0.0, 2.0 * (1.0 - cosine)))
                        ),
                    },
                    "drift_metrics": {
                        "norm_a": drift_norm_a,
                        "norm_b": drift_norm_b,
                        "cosine_similarity": drift_cosine,
                        "divergence": float(drift_divergence[offset]),
                        "relative_divergence": float(relative_drift_divergence[offset]),
                        "radial_divergence": drift_radial,
                        "angular_divergence": float(np.sqrt(drift_angular_sq)),
                        "angular_fraction_sq": drift_angular_sq
                        / max(
                            float(drift_divergence[offset]) ** 2,
                            settings.epsilon,
                        ),
                    },
                    "discovery": {
                        "semantic_annotation_used": False,
                        "sae_annotation_used": False,
                        "projection_used": False,
                    },
                    "gates": {
                        "cosine_min": settings.cosine_min,
                        "relative_norm_gap_max": settings.relative_norm_gap_max,
                        "drift_relative_divergence_min": (
                            settings.drift_relative_divergence_min
                        ),
                        "drift_absolute_divergence_min": (
                            settings.drift_absolute_divergence_min
                        ),
                    },
                }


def _neighbor_query_from_config(
    settings: CandidateSearchConfig,
    *,
    query_indices: tuple[int, ...] | None = None,
) -> NeighborQuery:
    return NeighborQuery(
        cosine_min=settings.cosine_min,
        relative_norm_gap_max=settings.relative_norm_gap_max,
        min_state_norm=settings.min_state_norm,
        epsilon=settings.epsilon,
        query_indices=query_indices,
    )


def _default_exact_backend(
    settings: CandidateSearchConfig,
) -> ExactBlockwiseBackend:
    return ExactBlockwiseBackend(
        block_size=settings.block_size,
        max_rows=settings.max_pairwise_rows,
        max_comparisons=max(
            1,
            settings.max_pairwise_rows
            * (settings.max_pairwise_rows - 1)
            // 2,
        ),
    )


def _validate_search_inputs(
    states: ArrayLike,
    drifts: ArrayLike,
    *,
    references: Sequence[Mapping[str, Any]] | None,
) -> tuple[NDArray[np.generic], NDArray[np.generic]]:
    state_rows = states if hasattr(states, "shape") else np.asanyarray(states)
    drift_rows = drifts if hasattr(drifts, "shape") else np.asanyarray(drifts)
    if state_rows.ndim != 2 or drift_rows.ndim != 2:
        raise ValueError(
            "states and drifts must both have shape (observations, hidden)"
        )
    if state_rows.shape != drift_rows.shape:
        raise ValueError(
            f"state/drift shape mismatch: {state_rows.shape} != "
            f"{drift_rows.shape}"
        )
    if references is not None and len(references) != state_rows.shape[0]:
        raise ValueError(
            "references length must equal the number of observations"
        )
    if references is not None:
        for index, reference in enumerate(references):
            if not isinstance(reference, Mapping):
                raise TypeError(f"references[{index}] must be a mapping")
            _reference_for_row(references, index)
    return state_rows, drift_rows


def iter_exact_reranked_candidates(
    states: ArrayLike,
    drifts: ArrayLike,
    pairs: Iterable[NeighborPair],
    *,
    backend_descriptor: NeighborBackendDescriptor,
    query: NeighborQuery,
    references: Sequence[Mapping[str, Any]] | None = None,
    config: CandidateSearchConfig | None = None,
    source_run_id: str = "array-input",
    group_key: str = "ungrouped",
    audit_receipt_sha256: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Apply canonical float64 state and drift gates to proposed pairs.

    Backend scores are deliberately ignored. This is the only path from
    neighbor proposals to persisted structural candidates.
    """

    settings = config or CandidateSearchConfig()
    if not isinstance(backend_descriptor, NeighborBackendDescriptor):
        raise TypeError(
            "backend_descriptor must be a NeighborBackendDescriptor"
        )
    if not isinstance(query, NeighborQuery):
        raise TypeError("query must be a NeighborQuery")
    expected_query = _neighbor_query_from_config(
        settings,
        query_indices=query.query_indices,
    )
    if query != expected_query:
        raise ValueError(
            "neighbor query boundaries must match CandidateSearchConfig"
        )
    state_rows, drift_rows = _validate_search_inputs(
        states,
        drifts,
        references=references,
    )
    row_count = int(state_rows.shape[0])
    state_norms = finite_row_norms(
        state_rows,
        block_size=settings.block_size,
        label="states",
    )
    drift_norms = finite_row_norms(
        drift_rows,
        block_size=settings.block_size,
        label="drifts",
    )
    query_scope = (
        None
        if query.query_indices is None
        else set(query.query_indices)
    )
    retrieval = {
        "backend_id": backend_descriptor.backend_id,
        "backend_kind": backend_descriptor.kind,
        "backend_sha256": backend_descriptor.sha256,
        "query_sha256": query.sha256,
        "exact_rerank_contract": EXACT_RERANK_CONTRACT_VERSION,
        "exact_reranked": True,
        "backend_score_used_for_gates": False,
        "audit_receipt_sha256": audit_receipt_sha256,
    }

    for pair in validate_neighbor_pairs(iter(pairs), row_count=row_count):
        left_index = pair.left_index
        right_index = pair.right_index
        if (
            query_scope is not None
            and left_index not in query_scope
            and right_index not in query_scope
        ):
            raise ValueError(
                f"neighbor pair {pair.key} does not touch query_indices"
            )

        norm_a = float(state_norms[left_index])
        norm_b = float(state_norms[right_index])
        left_state = np.asarray(state_rows[left_index], dtype=np.float64)
        right_state = np.asarray(state_rows[right_index], dtype=np.float64)
        state_pair = exact_state_pair_metrics(
            left_state,
            right_state,
            norm_a=norm_a,
            norm_b=norm_b,
            epsilon=settings.epsilon,
        )
        cosine = state_pair.cosine_similarity
        radial_distance = abs(norm_a - norm_b)
        relative_norm_gap = state_pair.relative_norm_gap
        if not state_pair_passes_query(
            state_pair,
            norm_a=norm_a,
            norm_b=norm_b,
            query=query,
        ):
            continue

        left_drift = np.asarray(drift_rows[left_index], dtype=np.float64)
        right_drift = np.asarray(drift_rows[right_index], dtype=np.float64)
        drift_norm_a = float(drift_norms[left_index])
        drift_norm_b = float(drift_norms[right_index])
        drift_difference = left_drift - right_drift
        drift_divergence = float(np.linalg.norm(drift_difference))
        mean_drift_norm = 0.5 * (drift_norm_a + drift_norm_b)
        relative_drift_divergence = drift_divergence / max(
            mean_drift_norm,
            settings.epsilon,
        )
        if (
            drift_norm_a < settings.min_drift_norm
            or drift_norm_b < settings.min_drift_norm
            or drift_divergence
            < settings.drift_absolute_divergence_min
            or relative_drift_divergence
            < settings.drift_relative_divergence_min
        ):
            continue

        angular_sq = max(
            0.0,
            2.0 * norm_a * norm_b * (1.0 - cosine),
        )
        state_distance_sq = radial_distance**2 + angular_sq
        drift_cosine = float(
            np.clip(
                np.dot(left_drift, right_drift)
                / (drift_norm_a * drift_norm_b),
                -1.0,
                1.0,
            )
        )
        drift_radial = abs(drift_norm_a - drift_norm_b)
        drift_angular_sq = max(
            0.0,
            2.0
            * drift_norm_a
            * drift_norm_b
            * (1.0 - drift_cosine),
        )

        left_reference = _reference_for_row(references, left_index)
        right_reference = _reference_for_row(references, right_index)
        yield {
            "schema_version": CANDIDATE_SCHEMA_VERSION,
            "record_type": "candidate",
            "candidate_id": _candidate_id(
                source_run_id=source_run_id,
                group_key=group_key,
                left_reference=left_reference,
                right_reference=right_reference,
            ),
            "candidate_kind": "cosine_near_drift_divergent",
            "claim_level": 1,
            "source_run_id": source_run_id,
            "comparison_group": group_key,
            "left": left_reference,
            "right": right_reference,
            "state_metrics": {
                "cosine_similarity": cosine,
                "norm_a": norm_a,
                "norm_b": norm_b,
                "euclidean_distance": float(np.sqrt(state_distance_sq)),
                "radial_distance": radial_distance,
                "angular_distance": float(np.sqrt(angular_sq)),
                "relative_norm_gap": relative_norm_gap,
                "angular_fraction_sq": angular_sq
                / max(state_distance_sq, settings.epsilon),
                "unit_chord_distance": float(
                    np.sqrt(max(0.0, 2.0 * (1.0 - cosine)))
                ),
            },
            "drift_metrics": {
                "norm_a": drift_norm_a,
                "norm_b": drift_norm_b,
                "cosine_similarity": drift_cosine,
                "divergence": drift_divergence,
                "relative_divergence": relative_drift_divergence,
                "radial_divergence": drift_radial,
                "angular_divergence": float(np.sqrt(drift_angular_sq)),
                "angular_fraction_sq": drift_angular_sq
                / max(drift_divergence**2, settings.epsilon),
            },
            "retrieval": retrieval,
            "discovery": {
                "semantic_annotation_used": False,
                "sae_annotation_used": False,
                "projection_used": False,
            },
            "gates": {
                "cosine_min": settings.cosine_min,
                "relative_norm_gap_max": settings.relative_norm_gap_max,
                "drift_relative_divergence_min": (
                    settings.drift_relative_divergence_min
                ),
                "drift_absolute_divergence_min": (
                    settings.drift_absolute_divergence_min
                ),
            },
        }


def iter_candidate_pairs(
    states: ArrayLike,
    drifts: ArrayLike,
    *,
    references: Sequence[Mapping[str, Any]] | None = None,
    config: CandidateSearchConfig | None = None,
    source_run_id: str = "array-input",
    group_key: str = "ungrouped",
    neighbor_backend: NeighborBackend | None = None,
    query_indices: tuple[int, ...] | None = None,
    expected_backend_descriptor: NeighborBackendDescriptor | None = None,
    audit_receipt_sha256: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Retrieve state neighbors, then exact-rerank structural candidates."""

    settings = config or CandidateSearchConfig()
    state_rows, _ = _validate_search_inputs(
        states,
        drifts,
        references=references,
    )
    backend = neighbor_backend or _default_exact_backend(settings)
    descriptor = backend.descriptor
    if not isinstance(descriptor, NeighborBackendDescriptor):
        raise TypeError(
            "neighbor_backend.descriptor must be a "
            "NeighborBackendDescriptor"
        )
    if (
        expected_backend_descriptor is not None
        and descriptor != expected_backend_descriptor
    ):
        raise ValueError(
            "neighbor backend descriptor changed before retrieval"
        )
    query = _neighbor_query_from_config(
        settings,
        query_indices=query_indices,
    )
    yield from iter_exact_reranked_candidates(
        states,
        drifts,
        backend.iter_pairs(state_rows, query=query),
        backend_descriptor=descriptor,
        query=query,
        references=references,
        config=settings,
        source_run_id=source_run_id,
        group_key=group_key,
        audit_receipt_sha256=audit_receipt_sha256,
    )
    if backend.descriptor != descriptor:
        raise ValueError(
            "neighbor backend descriptor changed during retrieval"
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _neighbor_descriptor_from_mapping(
    payload: Mapping[str, Any],
) -> NeighborBackendDescriptor:
    parameters = payload.get("parameters")
    runtime = payload.get("runtime")
    if not isinstance(parameters, Mapping) or not isinstance(
        runtime,
        Mapping,
    ):
        raise ValueError("neighbor backend descriptor is malformed")
    descriptor = NeighborBackendDescriptor(
        backend_id=payload.get("backend_id"),
        backend_version=payload.get("backend_version"),
        kind=payload.get("kind"),
        deterministic=payload.get("deterministic"),
        parameters=tuple(parameters.items()),
        runtime=tuple(runtime.items()),
    )
    if descriptor.to_dict() != dict(payload):
        raise ValueError(
            "neighbor backend descriptor fields are not canonical"
        )
    return descriptor


def _neighbor_query_from_mapping(
    payload: Mapping[str, Any],
) -> NeighborQuery:
    raw_indices = payload.get("query_indices")
    query_indices = (
        None
        if raw_indices is None
        else tuple(raw_indices)
        if isinstance(raw_indices, list)
        else raw_indices
    )
    query = NeighborQuery(
        cosine_min=payload.get("cosine_min"),
        relative_norm_gap_max=payload.get(
            "relative_norm_gap_max"
        ),
        min_state_norm=payload.get("min_state_norm"),
        epsilon=payload.get("epsilon"),
        query_indices=query_indices,
    )
    if query.to_dict() != dict(payload):
        raise ValueError(
            "neighbor query fields are not canonical"
        )
    return query


def _validated_neighbor_retrieval_bindings(
    source: Mapping[str, Any],
) -> Mapping[str, Mapping[str, Any]] | None:
    envelope = source.get("neighbor_retrieval")
    if envelope is None:
        return None
    if not isinstance(envelope, Mapping):
        raise TypeError("source.neighbor_retrieval must be a mapping")
    groups = envelope.get("groups")
    if (
        set(envelope) != {"schema_version", "groups"}
        or envelope.get("schema_version")
        != NEIGHBOR_RETRIEVAL_BINDING_SCHEMA_VERSION
        or not isinstance(groups, Mapping)
        or not groups
        or tuple(groups) != tuple(sorted(groups))
    ):
        raise ValueError(
            "source.neighbor_retrieval violates its provenance contract"
        )
    validated: dict[str, Mapping[str, Any]] = {}
    required_fields = {
        "comparison_group",
        "backend",
        "backend_sha256",
        "query",
        "query_sha256",
        "exact_rerank_contract",
        "exact_rerank_required",
        "backend_score_used_for_gates",
        "audit_receipt",
        "audit_receipt_sha256",
    }
    for group_key, value in groups.items():
        if (
            not isinstance(group_key, str)
            or not group_key
            or not isinstance(value, Mapping)
            or set(value) != required_fields
        ):
            raise ValueError(
                "neighbor retrieval group binding is malformed"
            )
        backend = value.get("backend")
        query = value.get("query")
        backend_sha256 = value.get("backend_sha256")
        query_sha256 = value.get("query_sha256")
        if (
            value.get("comparison_group") != group_key
            or not isinstance(backend, Mapping)
            or not isinstance(query, Mapping)
            or not isinstance(backend_sha256, str)
            or len(backend_sha256) != 64
            or not isinstance(query_sha256, str)
            or len(query_sha256) != 64
            or canonical_json_sha256(backend) != backend_sha256
            or canonical_json_sha256(query) != query_sha256
            or value.get("exact_rerank_contract")
            != EXACT_RERANK_CONTRACT_VERSION
            or value.get("exact_rerank_required") is not True
            or value.get("backend_score_used_for_gates") is not False
        ):
            raise ValueError(
                "neighbor retrieval group violates provenance"
            )
        backend_descriptor = _neighbor_descriptor_from_mapping(backend)
        query_contract = _neighbor_query_from_mapping(query)
        if (
            backend_descriptor.sha256 != backend_sha256
            or query_contract.sha256 != query_sha256
            or query_contract.query_indices is not None
        ):
            raise ValueError(
                "neighbor retrieval typed identity is invalid"
            )
        receipt = value.get("audit_receipt")
        receipt_sha256 = value.get("audit_receipt_sha256")
        if backend_descriptor.kind == "approximate":
            from .neighbor_receipt import NeighborAuditReceipt

            if (
                not isinstance(receipt, Mapping)
                or not isinstance(receipt_sha256, str)
                or len(receipt_sha256) != 64
                or canonical_json_sha256(receipt) != receipt_sha256
                or receipt.get("comparison_group") != group_key
                or receipt.get("subject_backend_sha256")
                != backend_sha256
                or receipt.get("authorized_target_query_sha256")
                != query_sha256
            ):
                raise ValueError(
                    "approximate neighbor retrieval lacks a matching "
                    "audit receipt"
                )
            typed_receipt = NeighborAuditReceipt.from_dict(receipt)
            if (
                typed_receipt.sha256 != receipt_sha256
                or typed_receipt.atlas_manifest_sha256
                != source.get("atlas_manifest_sha256")
                or typed_receipt.atlas_run_id
                != source.get("atlas_run_id")
                or typed_receipt.source_run_id
                != source.get("atlas_run_id")
                or typed_receipt.global_row_key_sha256
                != source.get("global_row_key_sha256")
            ):
                raise ValueError(
                    "approximate neighbor receipt identity is invalid"
                )
        elif receipt is not None or receipt_sha256 is not None:
            raise ValueError(
                "exact neighbor retrieval must not claim an audit receipt"
            )
        validated[group_key] = value
    return validated


def _validate_ledger_source_scope(
    source: Mapping[str, Any],
    *,
    config: CandidateSearchConfig,
    neighbor_bindings: Mapping[str, Mapping[str, Any]] | None,
) -> tuple[str | None, int | None]:
    atlas_run_id = source.get("atlas_run_id")
    if atlas_run_id is None:
        if config.layer_indices is not None:
            raise ValueError(
                "layer-scoped candidate config requires atlas source scope"
            )
        return None, None
    if not isinstance(atlas_run_id, str) or not atlas_run_id:
        raise ValueError("source.atlas_run_id must be a non-empty string")
    for field_name in (
        "atlas_manifest_sha256",
        "global_row_key_sha256",
    ):
        if not _is_lower_sha256(source.get(field_name)):
            raise ValueError(
                f"source.{field_name} must be a lowercase SHA-256"
            )
    request = source.get("request")
    layers = source.get("layers_analyzed")
    if not isinstance(request, Mapping) or not isinstance(layers, list):
        raise ValueError("atlas candidate source scope is incomplete")
    row_count = request.get("num_tokens")
    if (
        isinstance(row_count, bool)
        or not isinstance(row_count, Integral)
        or row_count <= 0
    ):
        raise ValueError("source.request.num_tokens must be positive")
    if (
        any(
            isinstance(layer, bool)
            or not isinstance(layer, Integral)
            or layer < 0
            for layer in layers
        )
        or len(set(layers)) != len(layers)
    ):
        raise ValueError("source.layers_analyzed is invalid")
    canonical_layers = tuple(int(layer) for layer in layers)
    if (
        config.layer_indices is not None
        and config.layer_indices != canonical_layers
    ):
        raise ValueError(
            "candidate config layer scope differs from its source"
        )
    if neighbor_bindings is not None:
        expected_groups = {
            f"layer_index={layer}" for layer in canonical_layers
        }
        if expected_groups != set(neighbor_bindings):
            raise ValueError(
                "ledger layers do not match neighbor groups"
            )
    return atlas_run_id, int(row_count)


def _write_candidate_ledger(
    candidates: Iterable[Mapping[str, Any]],
    output_path: str | Path,
    *,
    source: Mapping[str, Any],
    config: CandidateSearchConfig,
    protocol_id: str,
    overwrite: bool = False,
    protocol_claim_ceiling: int = 1,
    protocol_binding: Mapping[str, Any] | None = None,
    neighbor_audit_receipts: Mapping[str, object] | None = None,
    _allow_receipt_authorized_approximate: bool,
    _allow_atlas_source: bool,
) -> LedgerSummary:
    """Atomically write a header, candidate records, and completion footer.

    Existing destinations are protected by default.  The no-overwrite publish
    uses a hard link so a file created after the initial check is not replaced.
    """

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(overwrite, np.bool_) or not isinstance(overwrite, bool):
        raise TypeError("overwrite must be a boolean")
    if (
        isinstance(protocol_claim_ceiling, bool)
        or not isinstance(protocol_claim_ceiling, Integral)
        or not 1 <= protocol_claim_ceiling <= 3
    ):
        raise ValueError("protocol_claim_ceiling must be an integer in [1, 3]")
    if destination.exists() and not overwrite:
        raise FileExistsError(
            f"refusing to overwrite existing candidate ledger: {destination}"
        )
    safe_source = _json_safe(source)
    if not isinstance(safe_source, Mapping):
        raise TypeError("source must be a mapping")
    neighbor_bindings = _validated_neighbor_retrieval_bindings(safe_source)
    (
        expected_source_run_id,
        expected_row_count,
    ) = _validate_ledger_source_scope(
        safe_source,
        config=config,
        neighbor_bindings=neighbor_bindings,
    )
    if expected_source_run_id is not None and not _allow_atlas_source:
        raise ValueError(
            "atlas-backed candidate publication is available only through "
            "extract_candidates_from_manifest"
        )
    approximate_groups = (
        ()
        if neighbor_bindings is None
        else tuple(
            group_key
            for group_key, binding in neighbor_bindings.items()
            if binding["backend"].get("kind") == "approximate"
        )
    )
    if (
        approximate_groups
        and not _allow_receipt_authorized_approximate
    ):
        raise ValueError(
            "receipt-authorized approximate publication is available only "
            "through extract_candidates_from_manifest"
        )
    if approximate_groups and overwrite:
        raise ValueError(
            "receipt-authorized approximate ledgers cannot overwrite "
            "an existing path"
        )
    if approximate_groups:
        from .neighbor_receipt import NeighborAuditReceipt

        if (
            neighbor_audit_receipts is None
            or set(neighbor_audit_receipts) != set(approximate_groups)
        ):
            raise ValueError(
                "every approximate retrieval group requires its validated "
                "NeighborAuditReceipt object"
            )
        for group_key in approximate_groups:
            receipt = neighbor_audit_receipts[group_key]
            binding = neighbor_bindings[group_key]
            if (
                not isinstance(receipt, NeighborAuditReceipt)
                or not receipt.verified
                or receipt.to_dict() != binding["audit_receipt"]
                or receipt.sha256
                != binding["audit_receipt_sha256"]
            ):
                raise ValueError(
                    "neighbor audit receipt object differs from ledger "
                    f"binding for {group_key}"
                )
    elif neighbor_audit_receipts:
        raise ValueError(
            "neighbor_audit_receipts were supplied without approximate groups"
        )
    protocol_record: dict[str, Any] = {
        "declared_id": protocol_id,
        "claim_ceiling": int(protocol_claim_ceiling),
    }
    if protocol_binding is not None:
        if not isinstance(protocol_binding, Mapping):
            raise TypeError("protocol_binding must be a mapping")
        bound = _json_safe(protocol_binding)
        declared_id = bound.get("declared_id")
        if declared_id != protocol_id:
            raise ValueError(
                "protocol_binding.declared_id must match protocol_id: "
                f"{declared_id!r} != {protocol_id!r}"
            )
        bound_ceiling = bound.get("claim_ceiling", protocol_claim_ceiling)
        if (
            isinstance(bound_ceiling, bool)
            or not isinstance(bound_ceiling, Integral)
            or int(bound_ceiling) != int(protocol_claim_ceiling)
        ):
            raise ValueError(
                "protocol_binding.claim_ceiling must match protocol_claim_ceiling"
            )
        protocol_record.update(bound)
    temporary = destination.with_name(
        f".{destination.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}"
    )
    candidate_count = 0
    candidate_counts_by_group = {
        group_key: 0
        for group_key in (
            () if neighbor_bindings is None else neighbor_bindings
        )
    }
    started_at = _utc_now()
    header = {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "record_type": "ledger_header",
        "status": "in_progress",
        "protocol_id": protocol_id,
        "current_claim_level": 1,
        "protocol_claim_ceiling": int(protocol_claim_ceiling),
        "protocol": protocol_record,
        "started_at": started_at,
        "source": safe_source,
        "candidate_search": config.to_dict(),
        "discovery_contract": {
            "structural_metrics_only": True,
            "semantic_annotation_used": False,
            "candidate_is_not_verified_vortex": True,
            "neighbor_backend_proposes_pairs_only": True,
            "exact_rerank_required": True,
            "exact_rerank_contract": EXACT_RERANK_CONTRACT_VERSION,
            "backend_score_used_for_gates": False,
            "neighbor_retrieval_bound": neighbor_bindings is not None,
            "approximate_groups_receipt_authorized": list(
                approximate_groups
            ),
        },
    }

    try:
        with temporary.open("x", encoding="utf-8") as handle:
            content_digest = hashlib.sha256()
            header_line = (
                json.dumps(
                    header,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )
            handle.write(header_line)
            content_digest.update(header_line.encode("utf-8"))
            for candidate in candidates:
                safe_candidate = _json_safe(candidate)
                if not isinstance(safe_candidate, Mapping):
                    raise ValueError(
                        "candidate iterator emitted a non-object record"
                    )
                _validate_candidate_payload_shape(
                    safe_candidate,
                    config=config,
                    expected_source_run_id=expected_source_run_id,
                    expected_row_count=expected_row_count,
                )
                if safe_candidate.get("record_type") != "candidate":
                    raise ValueError("candidate iterator emitted a non-candidate record")
                retrieval = safe_candidate.get("retrieval")
                if (
                    safe_candidate.get("schema_version")
                    != CANDIDATE_SCHEMA_VERSION
                    or not isinstance(retrieval, Mapping)
                    or set(retrieval)
                    != {
                        "backend_id",
                        "backend_kind",
                        "backend_sha256",
                        "query_sha256",
                        "exact_rerank_contract",
                        "exact_reranked",
                        "backend_score_used_for_gates",
                        "audit_receipt_sha256",
                    }
                    or retrieval.get("exact_reranked") is not True
                    or retrieval.get("backend_score_used_for_gates")
                    is not False
                    or retrieval.get("exact_rerank_contract")
                    != EXACT_RERANK_CONTRACT_VERSION
                ):
                    raise ValueError(
                        "candidate is not bound to the exact-rerank contract"
                    )
                group_key = safe_candidate.get("comparison_group")
                group_binding = (
                    None
                    if neighbor_bindings is None
                    or not isinstance(group_key, str)
                    else neighbor_bindings.get(group_key)
                )
                if (
                    group_binding is None
                    or retrieval.get("backend_sha256")
                    != group_binding.get("backend_sha256")
                    or retrieval.get("query_sha256")
                    != group_binding.get("query_sha256")
                    or retrieval.get("backend_id")
                    != group_binding["backend"].get("backend_id")
                    or retrieval.get("backend_kind")
                    != group_binding["backend"].get("kind")
                    or retrieval.get("audit_receipt_sha256")
                    != group_binding.get("audit_receipt_sha256")
                ):
                    raise ValueError(
                        "candidate retrieval provenance does not match "
                        "the ledger header"
                    )
                candidate_line = (
                    json.dumps(
                        safe_candidate,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n"
                )
                handle.write(candidate_line)
                content_digest.update(candidate_line.encode("utf-8"))
                candidate_count += 1
                candidate_counts_by_group[group_key] += 1
            footer_without_digest = {
                "schema_version": LEDGER_SCHEMA_VERSION,
                "record_type": "ledger_footer",
                "status": "complete",
                "protocol_id": protocol_id,
                "started_at": started_at,
                "completed_at": _utc_now(),
                "candidate_count": candidate_count,
                "candidate_count_by_group": candidate_counts_by_group,
            }
            footer_identity_line = (
                json.dumps(
                    footer_without_digest,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )
            footer_digest = content_digest.copy()
            footer_digest.update(footer_identity_line.encode("utf-8"))
            footer = {
                **footer_without_digest,
                "content_sha256": footer_digest.hexdigest(),
            }
            handle.write(
                json.dumps(
                    footer,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )
            handle.flush()
            os.fsync(handle.fileno())
        if overwrite:
            os.replace(temporary, destination)
        else:
            try:
                os.link(temporary, destination)
            except FileExistsError as error:
                raise FileExistsError(
                    f"refusing to overwrite existing candidate ledger: {destination}"
                ) from error
            temporary.unlink()
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise

    return LedgerSummary(output_path=destination, candidate_count=candidate_count)


def write_candidate_ledger(
    candidates: Iterable[Mapping[str, Any]],
    output_path: str | Path,
    *,
    source: Mapping[str, Any],
    config: CandidateSearchConfig,
    protocol_id: str,
    overwrite: bool = False,
    protocol_claim_ceiling: int = 1,
    protocol_binding: Mapping[str, Any] | None = None,
    neighbor_audit_receipts: Mapping[str, object] | None = None,
) -> LedgerSummary:
    """Publish an exact-backend candidate ledger.

    Receipt-authorized approximate publication is intentionally owned by
    :func:`extract_candidates_from_manifest`, which also owns the shared
    float64 reranker and post-retrieval input checks.
    """

    return _write_candidate_ledger(
        candidates,
        output_path,
        source=source,
        config=config,
        protocol_id=protocol_id,
        overwrite=overwrite,
        protocol_claim_ceiling=protocol_claim_ceiling,
        protocol_binding=protocol_binding,
        neighbor_audit_receipts=neighbor_audit_receipts,
        _allow_receipt_authorized_approximate=False,
        _allow_atlas_source=False,
    )


def read_candidate_records(
    ledger_path: str | Path,
    *,
    expected_ledger_sha256: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield candidates only after strict whole-ledger verification."""

    path = Path(ledger_path)
    ledger_bytes = path.read_bytes()
    if expected_ledger_sha256 is not None:
        if (
            len(expected_ledger_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in expected_ledger_sha256
            )
        ):
            raise ValueError(
                "expected_ledger_sha256 must be a lowercase SHA-256"
            )
        if (
            hashlib.sha256(ledger_bytes).hexdigest()
            != expected_ledger_sha256
        ):
            raise ValueError(
                "candidate ledger does not match expected digest"
            )
    content_digest = hashlib.sha256()
    header: Mapping[str, Any] | None = None
    neighbor_bindings: Mapping[
        str,
        Mapping[str, Any],
    ] | None = None
    parsed_config: CandidateSearchConfig | None = None
    expected_source_run_id: str | None = None
    expected_row_count: int | None = None
    candidates: list[dict[str, Any]] = []
    candidate_counts_by_group: dict[str, int] = {}
    candidate_ids: set[str] = set()
    footer: Mapping[str, Any] | None = None
    try:
        ledger_text = ledger_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"candidate ledger is not UTF-8: {path}") from error
    with StringIO(ledger_text) as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                raise ValueError(
                    f"blank line is not allowed at {path}:{line_number}"
                )
            if footer is not None:
                raise ValueError(
                    f"record follows ledger footer at {path}:{line_number}"
                )
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"invalid JSON at {path}:{line_number}"
                ) from error
            if not isinstance(record, dict):
                raise ValueError(
                    f"ledger record is not an object at {path}:{line_number}"
                )
            record_type = record.get("record_type")
            if line_number == 1:
                current_claim_level = record.get("current_claim_level")
                protocol_claim_ceiling = record.get(
                    "protocol_claim_ceiling"
                )
                protocol_id = record.get("protocol_id")
                started_at = record.get("started_at")
                if (
                    record_type != "ledger_header"
                    or record.get("schema_version")
                    != LEDGER_SCHEMA_VERSION
                    or record.get("status") != "in_progress"
                    or set(record)
                    != {
                        "schema_version",
                        "record_type",
                        "status",
                        "protocol_id",
                        "current_claim_level",
                        "protocol_claim_ceiling",
                        "protocol",
                        "started_at",
                        "source",
                        "candidate_search",
                        "discovery_contract",
                    }
                    or not isinstance(protocol_id, str)
                    or not protocol_id
                    or not isinstance(started_at, str)
                    or not started_at
                    or isinstance(current_claim_level, bool)
                    or not isinstance(current_claim_level, Integral)
                    or int(current_claim_level) != 1
                    or isinstance(protocol_claim_ceiling, bool)
                    or not isinstance(protocol_claim_ceiling, Integral)
                    or not 1 <= int(protocol_claim_ceiling) <= 3
                ):
                    raise ValueError("candidate ledger header is invalid")
                source = record.get("source")
                search = record.get("candidate_search")
                protocol = record.get("protocol")
                if not isinstance(source, Mapping) or not isinstance(
                    search,
                    Mapping,
                ) or not isinstance(
                    protocol,
                    Mapping,
                ):
                    raise ValueError(
                        "candidate ledger header provenance is invalid"
                    )
                if (
                    protocol.get("declared_id")
                    != protocol_id
                    or not isinstance(
                        protocol.get("declared_id"),
                        str,
                    )
                    or isinstance(
                        protocol.get("claim_ceiling"),
                        bool,
                    )
                    or not isinstance(
                        protocol.get("claim_ceiling"),
                        Integral,
                    )
                    or protocol.get("claim_ceiling")
                    != protocol_claim_ceiling
                ):
                    raise ValueError(
                        "candidate ledger protocol identity is invalid"
                    )
                neighbor_bindings = (
                    _validated_neighbor_retrieval_bindings(source)
                )
                config_values = dict(search)
                if config_values.get("layer_indices") is not None:
                    config_values["layer_indices"] = tuple(
                        config_values["layer_indices"]
                    )
                parsed_config = CandidateSearchConfig(**config_values)
                if (
                    parsed_config.to_dict()
                    != dict(search)
                ):
                    raise ValueError(
                        "candidate search config is not canonical"
                    )
                (
                    expected_source_run_id,
                    expected_row_count,
                ) = _validate_ledger_source_scope(
                    source,
                    config=parsed_config,
                    neighbor_bindings=neighbor_bindings,
                )
                approximate_groups = (
                    []
                    if neighbor_bindings is None
                    else [
                        group_key
                        for group_key, binding in (
                            neighbor_bindings.items()
                        )
                        if binding["backend"].get("kind")
                        == "approximate"
                    ]
                )
                if record.get("discovery_contract") != {
                    "structural_metrics_only": True,
                    "semantic_annotation_used": False,
                    "candidate_is_not_verified_vortex": True,
                    "neighbor_backend_proposes_pairs_only": True,
                    "exact_rerank_required": True,
                    "exact_rerank_contract": (
                        EXACT_RERANK_CONTRACT_VERSION
                    ),
                    "backend_score_used_for_gates": False,
                    "neighbor_retrieval_bound": (
                        neighbor_bindings is not None
                    ),
                    "approximate_groups_receipt_authorized": (
                        approximate_groups
                    ),
                }:
                    raise ValueError(
                        "candidate ledger discovery contract is invalid"
                    )
                if neighbor_bindings is not None:
                    from .neighbor_receipt import NeighborAuditReceipt

                    candidate_config_sha256 = canonical_json_sha256(
                        parsed_config.to_dict()
                    )
                    for binding in neighbor_bindings.values():
                        if binding["backend"].get("kind") != "approximate":
                            continue
                        typed_receipt = NeighborAuditReceipt.from_dict(
                            binding["audit_receipt"]
                        )
                        if (
                            typed_receipt.candidate_config_sha256
                            != candidate_config_sha256
                            or typed_receipt.candidate_protocol_id
                            != protocol.get("declared_id")
                            or typed_receipt.candidate_protocol_sha256
                            != protocol.get("sha256")
                        ):
                            raise ValueError(
                                "candidate ledger header differs from its "
                                "neighbor audit receipt"
                            )
                header = record
                content_digest.update(line.encode("utf-8"))
            elif record_type == "candidate":
                if (
                    header is None
                    or parsed_config is None
                    or record.get("schema_version")
                    != CANDIDATE_SCHEMA_VERSION
                ):
                    raise ValueError("candidate ledger row is invalid")
                _validate_candidate_payload_shape(
                    record,
                    config=parsed_config,
                    expected_source_run_id=expected_source_run_id,
                    expected_row_count=expected_row_count,
                )
                group_key = record.get("comparison_group")
                if not isinstance(group_key, str) or not group_key:
                    raise ValueError(
                        "candidate comparison_group is invalid"
                    )
                retrieval = record.get("retrieval")
                group_binding = (
                    None
                    if neighbor_bindings is None
                    else neighbor_bindings.get(group_key)
                )
                candidate_id = record.get("candidate_id")
                if (
                    group_binding is None
                    or not isinstance(retrieval, Mapping)
                    or set(retrieval)
                    != {
                        "backend_id",
                        "backend_kind",
                        "backend_sha256",
                        "query_sha256",
                        "exact_rerank_contract",
                        "exact_reranked",
                        "backend_score_used_for_gates",
                        "audit_receipt_sha256",
                    }
                    or retrieval.get("backend_sha256")
                    != group_binding.get("backend_sha256")
                    or retrieval.get("query_sha256")
                    != group_binding.get("query_sha256")
                    or retrieval.get("backend_id")
                    != group_binding["backend"].get("backend_id")
                    or retrieval.get("backend_kind")
                    != group_binding["backend"].get("kind")
                    or retrieval.get("audit_receipt_sha256")
                    != group_binding.get("audit_receipt_sha256")
                    or retrieval.get("exact_rerank_contract")
                    != EXACT_RERANK_CONTRACT_VERSION
                    or retrieval.get("exact_reranked") is not True
                    or retrieval.get("backend_score_used_for_gates")
                    is not False
                    or not isinstance(candidate_id, str)
                    or not candidate_id
                    or candidate_id in candidate_ids
                ):
                    raise ValueError(
                        "candidate retrieval provenance does not match "
                        "the ledger header"
                    )
                candidate_ids.add(candidate_id)
                candidates.append(record)
                candidate_counts_by_group[group_key] = (
                    candidate_counts_by_group.get(group_key, 0) + 1
                )
                content_digest.update(line.encode("utf-8"))
            elif record_type == "ledger_footer":
                footer = record
                persisted_digest = record.get("content_sha256")
                footer_candidate_count = record.get("candidate_count")
                footer_group_counts = record.get(
                    "candidate_count_by_group"
                )
                footer_completed_at = record.get("completed_at")
                if (
                    record.get("schema_version") != LEDGER_SCHEMA_VERSION
                    or record.get("status") != "complete"
                    or set(record)
                    != {
                        "schema_version",
                        "record_type",
                        "status",
                        "protocol_id",
                        "started_at",
                        "completed_at",
                        "candidate_count",
                        "candidate_count_by_group",
                        "content_sha256",
                    }
                    or not _is_lower_sha256(persisted_digest)
                    or not isinstance(footer_completed_at, str)
                    or not footer_completed_at
                    or isinstance(footer_candidate_count, bool)
                    or not isinstance(
                        footer_candidate_count,
                        Integral,
                    )
                    or footer_candidate_count < 0
                    or not isinstance(footer_group_counts, Mapping)
                    or tuple(footer_group_counts)
                    != tuple(sorted(footer_group_counts))
                    or any(
                        not isinstance(group_key, str)
                        or not group_key
                        or isinstance(count, bool)
                        or not isinstance(count, Integral)
                        or count < 0
                        for group_key, count in (
                            footer_group_counts.items()
                        )
                    )
                ):
                    raise ValueError("candidate ledger footer is invalid")
                footer_without_digest = dict(record)
                footer_without_digest.pop("content_sha256")
                footer_identity_line = (
                    json.dumps(
                        footer_without_digest,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n"
                )
                expected_digest = content_digest.copy()
                expected_digest.update(
                    footer_identity_line.encode("utf-8")
                )
                if expected_digest.hexdigest() != persisted_digest:
                    raise ValueError(
                        "candidate ledger content digest mismatch"
                    )
            else:
                raise ValueError(
                    f"unexpected ledger record at {path}:{line_number}"
                )
    if header is None or footer is None:
        raise ValueError(f"candidate ledger is not complete: {path}")
    declared_counts = footer.get("candidate_count_by_group")
    expected_groups = (
        {}
        if neighbor_bindings is None
        else {
            str(group_key): 0
            for group_key in neighbor_bindings
        }
    )
    for group_key, count in candidate_counts_by_group.items():
        if group_key not in expected_groups:
            raise ValueError(
                "candidate group is not declared by the ledger header"
            )
        expected_groups[group_key] = count
    if (
        footer.get("candidate_count") != len(candidates)
        or declared_counts != expected_groups
        or footer.get("protocol_id") != header.get("protocol_id")
        or footer.get("started_at") != header.get("started_at")
    ):
        raise ValueError("candidate ledger footer counts are invalid")
    yield from candidates


def _sha256_file(path: Path, *, chunk_bytes: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_bytes):
            digest.update(chunk)
    return digest.hexdigest()


def _load_manifest_array(
    root: Path,
    manifest: Mapping[str, Any],
    name: str,
    *,
    verify_checksums: bool,
) -> NDArray[np.generic]:
    arrays = manifest.get("arrays")
    if not isinstance(arrays, Mapping) or not isinstance(arrays.get(name), Mapping):
        raise ValueError(f"atlas manifest is missing arrays.{name}")
    descriptor = arrays[name]
    relative_path = descriptor.get("path")
    if not isinstance(relative_path, str) or not relative_path:
        raise ValueError(f"arrays.{name}.path must be a non-empty string")
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"arrays.{name}.path escapes the atlas directory") from error
    if not path.is_file():
        raise FileNotFoundError(path)
    expected_sha = descriptor.get("sha256")
    if (
        verify_checksums
        and expected_sha is not None
        and (
            not isinstance(expected_sha, str)
            or len(expected_sha) != 64
        )
    ):
        raise ValueError(f"arrays.{name}.sha256 is malformed")
    with path.open("rb") as handle:
        if verify_checksums and expected_sha is not None:
            digest = hashlib.sha256()
            while chunk := handle.read(8 * 1024 * 1024):
                digest.update(chunk)
            actual_sha = digest.hexdigest()
            if actual_sha != expected_sha:
                raise ValueError(
                    f"checksum mismatch for arrays.{name}: "
                    f"{actual_sha} != {expected_sha}"
                )
            handle.seek(0)
        version = np.lib.format.read_magic(handle)
        if version == (1, 0):
            shape, fortran_order, dtype = (
                np.lib.format.read_array_header_1_0(handle)
            )
        elif version == (2, 0):
            shape, fortran_order, dtype = (
                np.lib.format.read_array_header_2_0(handle)
            )
        else:
            shape, fortran_order, dtype = (
                np.lib.format._read_array_header(  # noqa: SLF001
                    handle,
                    version,
                )
            )
        if dtype.hasobject:
            raise ValueError(
                f"arrays.{name} cannot use an object dtype"
            )
        array = np.memmap(
            handle,
            dtype=dtype,
            mode="r",
            offset=handle.tell(),
            shape=shape,
            order="F" if fortran_order else "C",
        )
    expected_shape = descriptor.get("shape")
    if expected_shape is not None and tuple(expected_shape) != array.shape:
        raise ValueError(
            f"arrays.{name} shape {array.shape} does not match manifest {expected_shape}"
        )
    expected_dtype = descriptor.get("dtype")
    if expected_dtype is not None and np.dtype(expected_dtype) != array.dtype:
        raise ValueError(
            f"arrays.{name} dtype {array.dtype} does not match manifest {expected_dtype}"
        )
    return array


class _DifferenceRows:
    """Lazy row-wise difference of two arrays with matching shapes."""

    def __init__(self, outputs: NDArray[np.generic], inputs: NDArray[np.generic]) -> None:
        if outputs.shape != inputs.shape:
            raise ValueError("lazy difference arrays must have matching shapes")
        self._outputs = outputs
        self._inputs = inputs
        self.shape = outputs.shape
        self.ndim = outputs.ndim
        self.dtype = np.result_type(outputs.dtype, inputs.dtype)

    def __getitem__(self, key: Any) -> NDArray[np.generic]:
        return np.asarray(self._outputs[key]) - np.asarray(self._inputs[key])


def extract_candidates_from_manifest(
    manifest_path: str | Path,
    output_path: str | Path,
    *,
    config: CandidateSearchConfig | None = None,
    protocol_id: str = "ad-hoc-v0.1",
    verify_checksums: bool = True,
    overwrite: bool = False,
    protocol_claim_ceiling: int = 1,
    protocol_binding: Mapping[str, Any] | None = None,
    neighbor_backend: NeighborBackend | None = None,
    neighbor_backend_factory: Callable[
        [NDArray[np.generic], str, str],
        NeighborBackend,
    ]
    | None = None,
    neighbor_audit_receipts: Mapping[str, object] | None = None,
) -> LedgerSummary:
    """Read a complete Pythia atlas and write a structural candidate ledger."""

    settings = config or CandidateSearchConfig()
    requested_path = Path(manifest_path).resolve()
    path = (
        requested_path / "manifest.json"
        if requested_path.is_dir()
        else requested_path
    )
    manifest_bytes_before = path.read_bytes()
    # Import lazily so the lightweight metric primitives do not require model
    # dependencies merely to be imported.
    from spirallens.atlas import load_manifest

    manifest = load_manifest(path.parent, verify_checksums=verify_checksums)
    manifest_bytes = path.read_bytes()
    if manifest_bytes != manifest_bytes_before:
        raise ValueError("atlas manifest changed during candidate validation")
    try:
        persisted_manifest = json.loads(manifest_bytes)
    except json.JSONDecodeError as error:
        raise ValueError("atlas manifest became invalid during validation") from error
    if persisted_manifest != manifest:
        raise ValueError(
            "validated atlas manifest differs from its persisted snapshot"
        )
    if not isinstance(manifest, Mapping):
        raise ValueError("atlas manifest must contain a JSON object")
    if manifest.get("status") != "complete":
        raise ValueError("candidate extraction requires an atlas with status='complete'")

    progress = manifest.get("progress")
    if not isinstance(progress, Mapping):
        raise ValueError("atlas manifest is missing progress")
    completed_rows = int(progress.get("completed_rows", -1))
    total_rows = int(progress.get("total_rows", -2))
    if completed_rows < 0 or completed_rows != total_rows:
        raise ValueError("atlas progress is incomplete or inconsistent")

    root = path.parent
    token_ids = _load_manifest_array(
        root,
        manifest,
        "token_ids",
        verify_checksums=verify_checksums,
    )
    resid_pre = _load_manifest_array(
        root,
        manifest,
        "resid_pre",
        verify_checksums=verify_checksums,
    )
    resid_post = _load_manifest_array(
        root,
        manifest,
        "resid_post",
        verify_checksums=verify_checksums,
    )
    if token_ids.ndim != 1:
        raise ValueError("token_ids must have shape (observations,)")
    if resid_pre.ndim != 3 or resid_post.shape != resid_pre.shape:
        raise ValueError("resid_pre/resid_post must have matching shape (N, layers, hidden)")
    if resid_pre.shape[0] != token_ids.shape[0] or token_ids.shape[0] != total_rows:
        raise ValueError("atlas arrays and progress disagree on the row count")

    request = manifest.get("request")
    if not isinstance(request, Mapping):
        raise ValueError("atlas manifest is missing request provenance")
    model = manifest.get("model")
    if not isinstance(model, Mapping):
        raise ValueError("atlas manifest is missing model provenance")
    run_id = str(manifest.get("run_id", ""))
    if not run_id:
        raise ValueError("atlas manifest is missing run_id")

    num_layers = resid_pre.shape[1]
    if int(model.get("num_layers", -1)) != num_layers:
        raise ValueError("atlas model.num_layers disagrees with residual arrays")
    if int(model.get("hidden_size", -1)) != resid_pre.shape[2]:
        raise ValueError("atlas model.hidden_size disagrees with residual arrays")
    if int(request.get("num_tokens", -1)) != token_ids.shape[0]:
        raise ValueError("atlas request.num_tokens disagrees with token_ids")
    layers = settings.layer_indices or tuple(range(num_layers))
    if any(layer >= num_layers for layer in layers):
        raise ValueError(f"requested layer_indices exceed atlas layer count {num_layers}")
    if (
        neighbor_backend is not None
        and neighbor_backend_factory is not None
    ):
        raise ValueError(
            "neighbor_backend and neighbor_backend_factory are mutually "
            "exclusive"
        )
    if neighbor_backend_factory is not None and len(layers) != 1:
        raise ValueError(
            "prepared approximate extraction currently requires exactly "
            "one layer per ledger"
        )
    neighbor_query = _neighbor_query_from_config(settings)
    atlas_manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()

    token_values = np.array(
        token_ids,
        dtype=np.int64,
        order="C",
        copy=True,
    )
    token_values.setflags(write=False)
    token_source_sha256 = state_matrix_sha256(
        np.asanyarray(token_ids).reshape(-1, 1)
    )
    global_row_key_sha256 = atlas_global_row_key_sha256(
        token_ids=token_values,
        request=request,
    )
    position = request.get(
        "observation_position",
        request.get("position"),
    )
    context_ids = request.get("context_ids")
    context_binding = request.get("context_bank_binding")
    bound_reference: dict[str, Any] | None = None
    tokenizer_addressable_size: int | None = None
    if isinstance(context_binding, Mapping):
        bank_binding = context_binding.get("bank")
        selected_context = context_binding.get("selected_context")
        bank_content = (
            bank_binding.get("content")
            if isinstance(bank_binding, Mapping)
            else None
        )
        tokenizer = (
            bank_content.get("tokenizer")
            if isinstance(bank_content, Mapping)
            else None
        )
        contexts = (
            bank_content.get("contexts")
            if isinstance(bank_content, Mapping)
            else None
        )
        entry_index = selected_context.get("entry_order_index")
        selected_content = (
            contexts[entry_index]
            if (
                isinstance(contexts, list)
                and isinstance(entry_index, int)
                and not isinstance(entry_index, bool)
                and 0 <= entry_index < len(contexts)
            )
            else None
        )
        token_domain = request.get("token_domain")
        if (
            not isinstance(bank_binding, Mapping)
            or not isinstance(selected_context, Mapping)
            or not isinstance(bank_content, Mapping)
            or not isinstance(tokenizer, Mapping)
            or not isinstance(selected_content, Mapping)
            or not isinstance(token_domain, Mapping)
        ):
            raise ValueError("atlas context-bank binding is incomplete")
        addressable_value = tokenizer.get("addressable_size")
        if (
            isinstance(addressable_value, bool)
            or not isinstance(addressable_value, int)
        ):
            raise ValueError(
                "atlas tokenizer addressable size is invalid"
            )
        tokenizer_addressable_size = addressable_value
        bound_reference = {
            "context_bank_sha256": bank_binding.get("canonical_sha256"),
            "context_bank_source_sha256": bank_binding.get("source_sha256"),
            "context_bank_binding_sha256": request.get(
                "context_bank_binding_sha256"
            ),
            "context_id": selected_context.get("context_id"),
            "context_role": selected_context.get("role"),
            "context_spec_sha256": selected_context.get(
                "context_spec_sha256"
            ),
            "context_input_sha256": selected_context.get(
                "context_input_sha256"
            ),
            "context_entry_order_index": entry_index,
            "context_template_ids": selected_content.get("template_ids"),
            "observation_position": selected_context.get(
                "observation_position"
            ),
            "sweep_position": selected_context.get("sweep_position"),
            "sweep_domain": token_domain.get("kind"),
            "observation_key_schema_version": context_binding.get(
                "observation_key_schema_version"
            ),
        }

    group_backends: dict[str, NeighborBackend] = {}
    group_descriptors: dict[str, NeighborBackendDescriptor] = {}
    group_receipt_sha256: dict[str, str | None] = {}
    group_bindings: dict[str, dict[str, Any]] = {}
    group_input_digests: dict[str, tuple[str, str]] = {}
    group_build_receipts: dict[str, NeighborIndexBuildReceipt] = {}
    supplied_receipts = dict(neighbor_audit_receipts or {})
    shared_backend = (
        neighbor_backend
        if neighbor_backend is not None
        else (
            None
            if neighbor_backend_factory is not None
            else _default_exact_backend(settings)
        )
    )
    for layer_index in layers:
        group_key = f"layer_index={layer_index}"
        states = resid_pre[:, layer_index, :]
        drifts = _DifferenceRows(
            resid_post[:, layer_index, :],
            resid_pre[:, layer_index, :],
        )
        states_sha256 = state_matrix_sha256(states)
        drifts_sha256 = state_matrix_sha256(drifts)
        group_input_digests[group_key] = (
            states_sha256,
            drifts_sha256,
        )
        if neighbor_backend_factory is not None:
            snapshot_storage = np.array(
                states,
                copy=True,
                order="C",
                subok=False,
            )
            snapshot_storage.setflags(write=False)
            snapshot = snapshot_storage.view()
            snapshot.setflags(write=False)
            snapshot_sha256 = state_matrix_sha256(snapshot)
            backend = neighbor_backend_factory(
                snapshot,
                global_row_key_sha256,
                group_key,
            )
            if state_matrix_sha256(snapshot) != snapshot_sha256:
                raise ValueError(
                    "neighbor backend factory changed its state snapshot"
                )
        else:
            assert shared_backend is not None
            backend = shared_backend
        descriptor = backend.descriptor
        if not isinstance(descriptor, NeighborBackendDescriptor):
            raise TypeError(
                "neighbor_backend.descriptor must be a "
                "NeighborBackendDescriptor"
            )
        receipt_sha256: str | None = None
        receipt_payload: Mapping[str, Any] | None = None
        if descriptor.kind == "approximate":
            from spirallens.neighbors import FaissHNSWBackend

            if not verify_checksums:
                raise ValueError(
                    "receipt-authorized approximate persistence "
                    "requires atlas checksum verification"
                )
            if type(backend) is not FaissHNSWBackend:
                raise ValueError(
                    "candidate persistence currently authorizes only "
                    "the built-in Faiss HNSW backend"
                )
            if len(layers) != 1:
                raise ValueError(
                    "approximate extraction requires one layer per ledger"
                )
            build_receipt = validate_prepared_backend(
                backend,
                states=states,
                row_identity_sha256=global_row_key_sha256,
                comparison_group=group_key,
            )
            receipt = supplied_receipts.get(group_key)
            from .neighbor_receipt import (
                NeighborAuditReceipt,
                NeighborPersistenceTarget,
            )

            if not isinstance(receipt, NeighborAuditReceipt):
                raise ValueError(
                    f"{group_key} requires a validated audit receipt"
                )
            if not isinstance(protocol_binding, Mapping):
                raise ValueError(
                    "approximate extraction requires the exact "
                    "candidate protocol binding"
                )
            candidate_protocol_id = protocol_binding.get(
                "declared_id"
            )
            candidate_protocol_sha256 = protocol_binding.get("sha256")
            target = NeighborPersistenceTarget(
                backend=descriptor,
                build_receipt=build_receipt,
                candidate_config=settings,
                candidate_protocol_id=candidate_protocol_id,
                candidate_protocol_sha256=(
                    candidate_protocol_sha256
                ),
                query=neighbor_query,
                atlas_manifest_sha256=atlas_manifest_sha256,
                atlas_run_id=run_id,
                global_row_key_sha256=global_row_key_sha256,
                source_run_id=run_id,
                comparison_group=group_key,
                states_sha256=states_sha256,
                drifts_sha256=drifts_sha256,
                row_count=int(states.shape[0]),
                hidden_size=int(states.shape[1]),
                states_dtype=str(states.dtype),
                drifts_dtype=str(drifts.dtype),
            )
            receipt.validate_target(target)
            receipt_sha256 = receipt.sha256
            receipt_payload = receipt.to_dict()
            group_build_receipts[group_key] = build_receipt
        elif group_key in supplied_receipts:
            raise ValueError(
                "exact retrieval group must not receive an audit receipt"
            )
        group_backends[group_key] = backend
        group_descriptors[group_key] = descriptor
        group_receipt_sha256[group_key] = receipt_sha256
        group_bindings[group_key] = {
            "comparison_group": group_key,
            "backend": descriptor.to_dict(),
            "backend_sha256": descriptor.sha256,
            "query": neighbor_query.to_dict(),
            "query_sha256": neighbor_query.sha256,
            "exact_rerank_contract": EXACT_RERANK_CONTRACT_VERSION,
            "exact_rerank_required": True,
            "backend_score_used_for_gates": False,
            "audit_receipt": receipt_payload,
            "audit_receipt_sha256": receipt_sha256,
        }
    if set(supplied_receipts) != {
        group_key
        for group_key, descriptor in group_descriptors.items()
        if descriptor.kind == "approximate"
    }:
        raise ValueError(
            "audit receipt groups must exactly match approximate layers"
        )

    def all_candidates() -> Iterator[dict[str, Any]]:
        for layer_index in layers:
            group_key = f"layer_index={layer_index}"
            references = []
            for row_index in range(token_values.size):
                reference = {
                    "row_index": row_index,
                    "token_id": int(token_values[row_index]),
                    "layer_index": layer_index,
                    "token_position": position,
                    "context_ids": context_ids,
                }
                if bound_reference is not None:
                    assert tokenizer_addressable_size is not None
                    reference.update(bound_reference)
                    reference["tokenizer_addressable"] = (
                        int(token_values[row_index])
                        < tokenizer_addressable_size
                    )
                references.append(reference)
            states = resid_pre[:, layer_index, :]
            drifts = _DifferenceRows(
                resid_post[:, layer_index, :],
                resid_pre[:, layer_index, :],
            )
            yield from iter_candidate_pairs(
                states,
                drifts,
                references=references,
                config=settings,
                source_run_id=run_id,
                group_key=group_key,
                neighbor_backend=group_backends[group_key],
                expected_backend_descriptor=group_descriptors[group_key],
                audit_receipt_sha256=group_receipt_sha256[group_key],
            )
            expected_states, expected_drifts = group_input_digests[
                group_key
            ]
            if (
                state_matrix_sha256(states) != expected_states
                or state_matrix_sha256(drifts) != expected_drifts
                or group_backends[group_key].descriptor
                != group_descriptors[group_key]
            ):
                raise ValueError(
                    "retrieval input/backend changed during "
                    f"{group_key}"
                )
            if group_key in group_build_receipts:
                post_receipt = validate_prepared_backend(
                    group_backends[group_key],
                    states=states,
                    row_identity_sha256=global_row_key_sha256,
                    comparison_group=group_key,
                )
                if post_receipt != group_build_receipts[group_key]:
                    raise ValueError(
                        "prepared backend build receipt changed during "
                        f"{group_key}"
                    )
        if path.read_bytes() != manifest_bytes:
            raise ValueError(
                "atlas manifest changed during candidate extraction"
            )
        if verify_checksums:
            for array_name in (
                "token_ids",
                "resid_pre",
                "resid_post",
            ):
                _load_manifest_array(
                    root,
                    manifest,
                    array_name,
                    verify_checksums=True,
                )
        if (
            state_matrix_sha256(
                np.asanyarray(token_ids).reshape(-1, 1)
            )
            != token_source_sha256
            or atlas_global_row_key_sha256(
                token_ids=token_values,
                request=request,
            )
            != global_row_key_sha256
        ):
            raise ValueError(
                "atlas token rows changed during candidate extraction"
            )

    source = {
        "atlas_manifest_path": str(path),
        "atlas_manifest_sha256": atlas_manifest_sha256,
        "atlas_schema_version": manifest.get("schema_version"),
        "atlas_run_id": run_id,
        "model": _json_safe(model),
        "request": _json_safe(request),
        "layers_analyzed": list(layers),
        "global_row_key_sha256": global_row_key_sha256,
        "neighbor_retrieval": {
            "schema_version": NEIGHBOR_RETRIEVAL_BINDING_SCHEMA_VERSION,
            "groups": {
                group_key: group_bindings[group_key]
                for group_key in sorted(group_bindings)
            },
        },
    }
    return _write_candidate_ledger(
        all_candidates(),
        output_path,
        source=source,
        config=settings,
        protocol_id=protocol_id,
        overwrite=overwrite,
        protocol_claim_ceiling=protocol_claim_ceiling,
        protocol_binding=protocol_binding,
        neighbor_audit_receipts=supplied_receipts or None,
        _allow_receipt_authorized_approximate=True,
        _allow_atlas_source=True,
    )


def _audit_neighbor_backend_from_manifest(
    manifest_path: str | Path,
    *,
    layer_index: int,
    subject_backend_factory: Callable[
        [NDArray[np.generic]],
        NeighborBackend,
    ],
    protocol_binding: "NeighborAuditProtocolBinding",
    candidate_config: CandidateSearchConfig,
    audit_config: "NeighborAuditConfig",
    execution_freeze: "ValidatedExecutionFreeze",
    verify_checksums: bool = True,
) -> "NeighborAuditResult":
    """Audit one prepared full-input index on preregistered query rows."""

    from spirallens.atlas import load_manifest
    from spirallens.execution_freeze import (
        validated_execution_freeze_sha256,
    )

    from .neighbor_audit import (
        NeighborAuditProtocolBinding,
        audit_neighbor_backend,
    )

    if (
        isinstance(layer_index, bool)
        or not isinstance(layer_index, Integral)
        or layer_index < 0
    ):
        raise ValueError("layer_index must be a non-negative integer")
    if not isinstance(
        protocol_binding,
        NeighborAuditProtocolBinding,
    ):
        raise TypeError(
            "protocol_binding must be NeighborAuditProtocolBinding"
        )
    if protocol_binding.status != "frozen":
        raise ValueError(
            "manifest-backed subject neighbor audits require a frozen "
            "protocol binding"
        )
    if (
        protocol_binding.status == "frozen"
        and not verify_checksums
    ):
        raise ValueError(
            "frozen neighbor audits require atlas checksum verification"
        )
    if candidate_config.layer_indices != (int(layer_index),):
        raise ValueError(
            "candidate_config must bind exactly the audited layer"
        )
    execution_freeze_sha256 = (
        validated_execution_freeze_sha256(execution_freeze)
    )
    execution_freeze.revalidate()
    selection = protocol_binding.query_selection
    if selection is None:
        raise ValueError(
            "manifest audit requires preregistered query selection"
        )
    requested_path = Path(manifest_path).resolve()
    path = (
        requested_path / "manifest.json"
        if requested_path.is_dir()
        else requested_path
    )
    manifest_bytes_before = path.read_bytes()
    manifest = load_manifest(
        path.parent,
        verify_checksums=verify_checksums,
    )
    manifest_bytes = path.read_bytes()
    if manifest_bytes != manifest_bytes_before:
        raise ValueError("atlas manifest changed during audit validation")
    try:
        persisted_manifest = json.loads(manifest_bytes)
    except json.JSONDecodeError as error:
        raise ValueError(
            "atlas manifest became invalid during audit validation"
        ) from error
    if persisted_manifest != manifest:
        raise ValueError(
            "validated atlas manifest differs from its persisted "
            "snapshot"
        )
    if (
        not isinstance(manifest, Mapping)
        or manifest.get("status") != "complete"
    ):
        raise ValueError(
            "neighbor audit requires a complete atlas manifest"
        )
    root = path.parent
    token_ids = _load_manifest_array(
        root,
        manifest,
        "token_ids",
        verify_checksums=verify_checksums,
    )
    resid_pre = _load_manifest_array(
        root,
        manifest,
        "resid_pre",
        verify_checksums=verify_checksums,
    )
    resid_post = _load_manifest_array(
        root,
        manifest,
        "resid_post",
        verify_checksums=verify_checksums,
    )
    if (
        token_ids.ndim != 1
        or resid_pre.ndim != 3
        or resid_post.shape != resid_pre.shape
        or resid_pre.shape[0] != token_ids.shape[0]
        or layer_index >= resid_pre.shape[1]
    ):
        raise ValueError("atlas arrays are incompatible with neighbor audit")
    request = manifest.get("request")
    model = manifest.get("model")
    run_id = manifest.get("run_id")
    if (
        not isinstance(request, Mapping)
        or not isinstance(model, Mapping)
        or not isinstance(run_id, str)
        or not run_id
    ):
        raise ValueError("atlas audit provenance is incomplete")
    _validate_neighbor_audit_atlas_scope(
        manifest=manifest,
        token_ids=token_ids,
        layer_index=int(layer_index),
    )
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    token_values = np.array(
        token_ids,
        dtype=np.int64,
        order="C",
        copy=True,
    )
    token_values.setflags(write=False)
    token_source_sha256 = state_matrix_sha256(
        np.asanyarray(token_ids).reshape(-1, 1)
    )
    global_row_key_sha256 = atlas_global_row_key_sha256(
        token_ids=token_values,
        request=request,
    )
    if (
        selection.global_row_key_sha256
        != global_row_key_sha256
    ):
        raise ValueError(
            "query selection row identity differs from atlas"
        )
    group_key = f"layer_index={int(layer_index)}"
    observation_scope_sha256 = canonical_json_sha256(
        {
            "schema_version": "spirallens.observation-scope.v0.1",
            "atlas_manifest_sha256": manifest_sha256,
            "atlas_run_id": run_id,
            "comparison_group": group_key,
            "model": _json_safe(model),
            "request": _json_safe(request),
        }
    )
    states = resid_pre[:, layer_index, :]
    drift_source = _DifferenceRows(
        resid_post[:, layer_index, :],
        resid_pre[:, layer_index, :],
    )
    drifts = np.asarray(resid_post[:, layer_index, :]) - np.asarray(
        resid_pre[:, layer_index, :]
    )
    states_sha256 = state_matrix_sha256(states)
    drifts_sha256 = state_matrix_sha256(drift_source)
    result = audit_neighbor_backend(
        states,
        drifts,
        subject_backend_factory=subject_backend_factory,
        protocol_binding=protocol_binding,
        source_identity={
            "kind": "atlas_subset",
            "atlas_manifest_sha256": manifest_sha256,
            "atlas_run_id": run_id,
            "observation_scope_sha256": observation_scope_sha256,
            "global_row_key_sha256": global_row_key_sha256,
            "execution_freeze_sha256": execution_freeze_sha256,
        },
        candidate_config=candidate_config,
        audit_config=audit_config,
        query_indices=selection.select(int(states.shape[0])),
        source_run_id=run_id,
        group_key=group_key,
    )
    if path.read_bytes() != manifest_bytes:
        raise ValueError("atlas manifest changed during neighbor audit")
    if verify_checksums:
        for array_name in ("token_ids", "resid_pre", "resid_post"):
            _load_manifest_array(
                root,
                manifest,
                array_name,
                verify_checksums=True,
            )
    if (
        state_matrix_sha256(states) != states_sha256
        or state_matrix_sha256(drift_source) != drifts_sha256
        or state_matrix_sha256(
            np.asanyarray(token_ids).reshape(-1, 1)
        )
        != token_source_sha256
        or atlas_global_row_key_sha256(
            token_ids=token_values,
            request=request,
        )
        != global_row_key_sha256
    ):
        raise ValueError(
            "atlas arrays changed during neighbor audit"
        )
    execution_freeze.revalidate()
    execution_freeze.validate_subject_backend(result.subject_backend)
    return result
