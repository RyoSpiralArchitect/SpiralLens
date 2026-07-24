"""State-only neighbor retrieval contracts and exact references."""

from .contracts import (
    NEIGHBOR_BACKEND_SCHEMA_VERSION,
    NEIGHBOR_INDEX_BUILD_SCHEMA_VERSION,
    NEIGHBOR_QUERY_SCHEMA_VERSION,
    NeighborBackend,
    NeighborBackendDescriptor,
    NeighborIndexBuildReceipt,
    NeighborPair,
    NeighborQuery,
    PreparedNeighborBackend,
    canonical_json_sha256,
    state_matrix_sha256,
    validate_prepared_backend,
    validate_neighbor_pairs,
)
from .exact import (
    EXACT_BACKEND_ID,
    EXACT_BACKEND_VERSION,
    ExactBlockwiseBackend,
)
from .faiss_hnsw import (
    FAISS_HNSW_BACKEND_ID,
    FAISS_HNSW_BACKEND_VERSION,
    FaissHNSWBackend,
    FaissHNSWConfig,
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
    "FAISS_HNSW_BACKEND_ID",
    "FAISS_HNSW_BACKEND_VERSION",
    "NEIGHBOR_BACKEND_SCHEMA_VERSION",
    "NEIGHBOR_INDEX_BUILD_SCHEMA_VERSION",
    "NEIGHBOR_QUERY_SCHEMA_VERSION",
    "ExactBlockwiseBackend",
    "ExactStatePairMetrics",
    "FaissHNSWBackend",
    "FaissHNSWConfig",
    "NeighborBackend",
    "NeighborBackendDescriptor",
    "NeighborIndexBuildReceipt",
    "NeighborPair",
    "NeighborQuery",
    "PreparedNeighborBackend",
    "canonical_json_sha256",
    "conservative_dot_tolerance",
    "exact_state_pair_metrics",
    "finite_row_norms",
    "state_matrix_sha256",
    "state_pair_passes_query",
    "validate_prepared_backend",
    "validate_neighbor_pairs",
]
