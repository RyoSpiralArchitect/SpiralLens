"""Deterministic bounded exact reference retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral

import numpy as np
from numpy.typing import ArrayLike

from .contracts import (
    NeighborBackendDescriptor,
    NeighborPair,
    NeighborQuery,
)
from .scoring import (
    conservative_dot_tolerance,
    exact_state_pair_metrics,
    finite_row_norms,
    state_pair_passes_query,
)


EXACT_BACKEND_ID = "spirallens.exact-blockwise-reference"
EXACT_BACKEND_VERSION = "0.1"


def _comparison_count(row_count: int, query_count: int) -> int:
    non_query_count = row_count - query_count
    return (
        query_count * non_query_count
        + query_count * (query_count - 1) // 2
    )


@dataclass(frozen=True)
class ExactBlockwiseBackend:
    """NumPy reference backend with a bounded exact-comparison budget."""

    block_size: int = 1024
    max_rows: int = 10_000
    max_comparisons: int = 50_000_000

    def __post_init__(self) -> None:
        for field_name in ("block_size", "max_rows", "max_comparisons"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, Integral):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
            object.__setattr__(self, field_name, int(value))

    @property
    def descriptor(self) -> NeighborBackendDescriptor:
        return NeighborBackendDescriptor(
            backend_id=EXACT_BACKEND_ID,
            backend_version=EXACT_BACKEND_VERSION,
            kind="exact",
            deterministic=True,
            parameters=(
                ("block_size", self.block_size),
                ("max_comparisons", self.max_comparisons),
                ("max_rows", self.max_rows),
                ("pair_order", "left_then_right_ascending"),
            ),
            runtime=(("numpy_version", np.__version__),),
        )

    def iter_pairs(
        self,
        states: ArrayLike,
        *,
        query: NeighborQuery,
    ):
        rows = states if hasattr(states, "shape") else np.asanyarray(states)
        if rows.ndim != 2:
            raise ValueError("states must have shape (observations, hidden)")
        row_count = int(rows.shape[0])
        if query.query_indices is None:
            query_indices = tuple(range(row_count))
            if row_count > self.max_rows:
                raise ValueError(
                    "exact pairwise candidate search is bounded to "
                    f"max_pairwise_rows={self.max_rows}, but received "
                    f"{row_count} rows; use an audited ANN neighbor backend"
                )
        else:
            query_indices = query.query_indices
            if query_indices and query_indices[-1] >= row_count:
                raise ValueError(
                    "query_indices contain a row outside the state matrix"
                )
        comparisons = _comparison_count(row_count, len(query_indices))
        if comparisons > self.max_comparisons:
            raise ValueError(
                "exact neighbor reference exceeds "
                f"max_comparisons={self.max_comparisons}: {comparisons}"
            )

        state_norms = finite_row_norms(
            rows,
            block_size=self.block_size,
            label="states",
        )
        query_set = set(query_indices)
        query_array = np.asarray(query_indices, dtype=np.int64)
        tolerance = conservative_dot_tolerance(int(rows.shape[1]))

        for left_index in range(max(0, row_count - 1)):
            if left_index in query_set:
                right_indices = np.arange(
                    left_index + 1,
                    row_count,
                    dtype=np.int64,
                )
            else:
                right_indices = query_array[query_array > left_index]
            if right_indices.size == 0:
                continue

            left_state = np.asarray(rows[left_index], dtype=np.float64)
            norm_a = float(state_norms[left_index])
            for right_start in range(0, right_indices.size, self.block_size):
                selected_indices = right_indices[
                    right_start : right_start + self.block_size
                ]
                right_states = np.asarray(
                    rows[selected_indices],
                    dtype=np.float64,
                )
                right_norms = state_norms[selected_indices]
                rough_cosine = np.clip(
                    (right_states @ left_state)
                    / (
                        np.maximum(right_norms, query.epsilon)
                        * max(norm_a, query.epsilon)
                    ),
                    -1.0,
                    1.0,
                )
                mean_norm = 0.5 * (norm_a + right_norms)
                norm_gap = np.abs(norm_a - right_norms) / np.maximum(
                    mean_norm,
                    query.epsilon,
                )
                prefiltered = (
                    (norm_a >= query.min_state_norm)
                    & (right_norms >= query.min_state_norm)
                    & (rough_cosine >= query.cosine_min - tolerance)
                    & (
                        norm_gap
                        <= query.relative_norm_gap_max + tolerance
                    )
                )
                for offset in np.flatnonzero(prefiltered):
                    right_index = int(selected_indices[offset])
                    metrics = exact_state_pair_metrics(
                        left_state,
                        rows[right_index],
                        norm_a=norm_a,
                        norm_b=float(right_norms[offset]),
                        epsilon=query.epsilon,
                    )
                    if not state_pair_passes_query(
                        metrics,
                        norm_a=norm_a,
                        norm_b=float(right_norms[offset]),
                        query=query,
                    ):
                        continue
                    yield NeighborPair(
                        left_index=left_index,
                        right_index=right_index,
                        backend_score=metrics.cosine_similarity,
                    )
