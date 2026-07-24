"""Canonical float64 scoring shared by retrieval and candidate reranking."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .contracts import NeighborQuery


@dataclass(frozen=True)
class ExactStatePairMetrics:
    """Canonical state-only metrics for one unordered row pair."""

    cosine_similarity: float
    relative_norm_gap: float


def finite_row_norms(
    rows: NDArray[np.generic],
    *,
    block_size: int,
    label: str,
) -> NDArray[np.float64]:
    """Compute deterministic float64 row norms while validating finiteness."""

    if rows.ndim != 2:
        raise ValueError(f"{label} must be a two-dimensional row matrix")
    norms = np.empty(rows.shape[0], dtype=np.float64)
    for start in range(0, rows.shape[0], block_size):
        stop = min(start + block_size, rows.shape[0])
        block = np.asarray(rows[start:stop], dtype=np.float64)
        if block.ndim != 2:
            raise ValueError(f"{label} must be a two-dimensional row matrix")
        if not np.all(np.isfinite(block)):
            raise ValueError(
                f"{label}[{start}:{stop}] contains non-finite values"
            )
        squared = np.sum(block * block, axis=1, dtype=np.float64)
        norms[start:stop] = np.sqrt(squared)
    return norms


def exact_state_pair_metrics(
    left_state: NDArray[np.generic],
    right_state: NDArray[np.generic],
    *,
    norm_a: float,
    norm_b: float,
    epsilon: float,
) -> ExactStatePairMetrics:
    """Score one pair with the sole canonical scalar-dot implementation."""

    # Always materialize both rows with the same layout. NumPy's dot-product
    # dispatch can otherwise differ by a final bit for a strided source view
    # versus a fancy-indexed copy, which is enough to split an inclusive
    # threshold between retrieval and reranking.
    left = np.array(left_state, dtype=np.float64, order="C", copy=True)
    right = np.array(right_state, dtype=np.float64, order="C", copy=True)
    if left.ndim != 1 or right.ndim != 1 or left.shape != right.shape:
        raise ValueError("state pair rows must be matching one-dimensional vectors")
    cosine = float(
        np.clip(
            np.dot(left, right)
            / (max(norm_a, epsilon) * max(norm_b, epsilon)),
            -1.0,
            1.0,
        )
    )
    relative_norm_gap = abs(norm_a - norm_b) / max(
        0.5 * (norm_a + norm_b),
        epsilon,
    )
    return ExactStatePairMetrics(
        cosine_similarity=cosine,
        relative_norm_gap=relative_norm_gap,
    )


def state_pair_passes_query(
    metrics: ExactStatePairMetrics,
    *,
    norm_a: float,
    norm_b: float,
    query: NeighborQuery,
) -> bool:
    """Apply the inclusive state-only retrieval boundary."""

    return (
        norm_a >= query.min_state_norm
        and norm_b >= query.min_state_norm
        and metrics.cosine_similarity >= query.cosine_min
        and metrics.relative_norm_gap <= query.relative_norm_gap_max
    )


def conservative_dot_tolerance(hidden_size: int) -> float:
    """Return a safe prefilter margin before canonical scalar rescoring.

    The widened vectorized prefilter is never itself a scientific gate. Every
    row that survives it is scored again by :func:`exact_state_pair_metrics`.
    """

    return float(
        64.0 * np.finfo(np.float64).eps * max(1, int(hidden_size))
    )
