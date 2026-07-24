"""State-only neighbor retrieval contracts and exact references."""

from .contracts import (
    NEIGHBOR_BACKEND_SCHEMA_VERSION,
    NEIGHBOR_QUERY_SCHEMA_VERSION,
    NeighborBackend,
    NeighborBackendDescriptor,
    NeighborPair,
    NeighborQuery,
    canonical_json_sha256,
    validate_neighbor_pairs,
)
from .exact import (
    EXACT_BACKEND_ID,
    EXACT_BACKEND_VERSION,
    ExactBlockwiseBackend,
)
from .scoring import (
    ExactStatePairMetrics,
    conservative_dot_tolerance,
    exact_state_pair_metrics,
    finite_row_norms,
    state_pair_passes_query,
)

__all__ = [
    "EXACT_BACKEND_ID",
    "EXACT_BACKEND_VERSION",
    "NEIGHBOR_BACKEND_SCHEMA_VERSION",
    "NEIGHBOR_QUERY_SCHEMA_VERSION",
    "ExactBlockwiseBackend",
    "ExactStatePairMetrics",
    "NeighborBackend",
    "NeighborBackendDescriptor",
    "NeighborPair",
    "NeighborQuery",
    "canonical_json_sha256",
    "conservative_dot_tolerance",
    "exact_state_pair_metrics",
    "finite_row_norms",
    "state_pair_passes_query",
    "validate_neighbor_pairs",
]
