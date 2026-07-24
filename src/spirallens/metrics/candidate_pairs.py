"""Blockwise discovery of cosine-near, drift-divergent structural candidates.

Discovery consumes only atlas activations and preregistered numeric gates.
Token strings, SAE labels, minimal-pair classes, and other semantic annotations
are deliberately absent from this module.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from numbers import Integral, Real
from typing import Any
import uuid

import numpy as np
from numpy.typing import ArrayLike, NDArray
import yaml

from spirallens.neighbors import (
    ExactBlockwiseBackend,
    NeighborBackend,
    NeighborBackendDescriptor,
    NeighborPair,
    NeighborQuery,
    canonical_json_sha256,
    exact_state_pair_metrics,
    finite_row_norms,
    state_pair_passes_query,
    validate_neighbor_pairs,
)


CANDIDATE_SCHEMA_VERSION = "spirallens.candidate.v0.2"
LEDGER_SCHEMA_VERSION = "spirallens.candidate-ledger.v0.2"
EXACT_RERANK_CONTRACT_VERSION = "spirallens.candidate-exact-rerank.v0.1"


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
    )
    if backend.descriptor != descriptor:
        raise ValueError(
            "neighbor backend descriptor changed during retrieval"
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validated_neighbor_retrieval_binding(
    source: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    binding = source.get("neighbor_retrieval")
    if binding is None:
        return None
    if not isinstance(binding, Mapping):
        raise TypeError("source.neighbor_retrieval must be a mapping")
    backend = binding.get("backend")
    query = binding.get("query")
    backend_sha256 = binding.get("backend_sha256")
    query_sha256 = binding.get("query_sha256")
    if (
        not isinstance(backend, Mapping)
        or not isinstance(query, Mapping)
        or not isinstance(backend_sha256, str)
        or len(backend_sha256) != 64
        or not isinstance(query_sha256, str)
        or len(query_sha256) != 64
        or canonical_json_sha256(backend) != backend_sha256
        or canonical_json_sha256(query) != query_sha256
        or binding.get("exact_rerank_contract")
        != EXACT_RERANK_CONTRACT_VERSION
        or binding.get("exact_rerank_required") is not True
        or binding.get("backend_score_used_for_gates") is not False
    ):
        raise ValueError(
            "source.neighbor_retrieval violates its provenance contract"
        )
    if backend.get("kind") == "approximate":
        raise ValueError(
            "approximate candidate persistence is disabled until an "
            "audit-receipt binding is implemented"
        )
    return binding


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
    neighbor_binding = _validated_neighbor_retrieval_binding(safe_source)
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
            "neighbor_retrieval_bound": neighbor_binding is not None,
        },
    }

    try:
        with temporary.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(header, sort_keys=True, separators=(",", ":")) + "\n")
            for candidate in candidates:
                safe_candidate = _json_safe(candidate)
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
                if (
                    neighbor_binding is None
                    or retrieval.get("backend_sha256")
                    != neighbor_binding.get("backend_sha256")
                    or retrieval.get("query_sha256")
                    != neighbor_binding.get("query_sha256")
                    or retrieval.get("backend_id")
                    != neighbor_binding["backend"].get("backend_id")
                    or retrieval.get("backend_kind")
                    != neighbor_binding["backend"].get("kind")
                ):
                    raise ValueError(
                        "candidate retrieval provenance does not match "
                        "the ledger header"
                    )
                handle.write(
                    json.dumps(safe_candidate, sort_keys=True, separators=(",", ":"))
                    + "\n"
                )
                candidate_count += 1
            footer = {
                "schema_version": LEDGER_SCHEMA_VERSION,
                "record_type": "ledger_footer",
                "status": "complete",
                "protocol_id": protocol_id,
                "started_at": started_at,
                "completed_at": _utc_now(),
                "candidate_count": candidate_count,
            }
            handle.write(json.dumps(footer, sort_keys=True, separators=(",", ":")) + "\n")
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


def read_candidate_records(ledger_path: str | Path) -> Iterator[dict[str, Any]]:
    """Yield only candidate rows from a completed ledger."""

    path = Path(ledger_path)
    saw_complete_footer = False
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid JSON at {path}:{line_number}") from error
            record_type = record.get("record_type")
            if record_type == "candidate":
                yield record
            elif record_type == "ledger_footer":
                saw_complete_footer = record.get("status") == "complete"
    if not saw_complete_footer:
        raise ValueError(f"candidate ledger is not complete: {path}")


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
    if verify_checksums and expected_sha is not None:
        if not isinstance(expected_sha, str) or len(expected_sha) != 64:
            raise ValueError(f"arrays.{name}.sha256 is malformed")
        actual_sha = _sha256_file(path)
        if actual_sha != expected_sha:
            raise ValueError(
                f"checksum mismatch for arrays.{name}: {actual_sha} != {expected_sha}"
            )

    array = np.load(path, mmap_mode="r", allow_pickle=False)
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
    backend = neighbor_backend or _default_exact_backend(settings)
    backend_descriptor = backend.descriptor
    if not isinstance(backend_descriptor, NeighborBackendDescriptor):
        raise TypeError(
            "neighbor_backend.descriptor must be a "
            "NeighborBackendDescriptor"
        )
    neighbor_query = _neighbor_query_from_config(settings)

    token_values = np.asarray(token_ids, dtype=np.int64)
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

    def all_candidates() -> Iterator[dict[str, Any]]:
        for layer_index in layers:
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
                group_key=f"layer_index={layer_index}",
                neighbor_backend=backend,
                expected_backend_descriptor=backend_descriptor,
            )

    source = {
        "atlas_manifest_path": str(path),
        "atlas_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "atlas_schema_version": manifest.get("schema_version"),
        "atlas_run_id": run_id,
        "model": _json_safe(model),
        "request": _json_safe(request),
        "layers_analyzed": list(layers),
        "neighbor_retrieval": {
            "backend": backend_descriptor.to_dict(),
            "backend_sha256": backend_descriptor.sha256,
            "query": neighbor_query.to_dict(),
            "query_sha256": neighbor_query.sha256,
            "exact_rerank_contract": EXACT_RERANK_CONTRACT_VERSION,
            "exact_rerank_required": True,
            "backend_score_used_for_gates": False,
        },
    }
    return write_candidate_ledger(
        all_candidates(),
        output_path,
        source=source,
        config=settings,
        protocol_id=protocol_id,
        overwrite=overwrite,
        protocol_claim_ceiling=protocol_claim_ceiling,
        protocol_binding=protocol_binding,
    )
