"""Metrics used by the structural candidate-discovery pipeline."""

from spirallens.metrics.candidate_pairs import (
    CandidateSearchConfig,
    LedgerSummary,
    extract_candidates_from_manifest,
    iter_candidate_pairs,
    iter_exact_reranked_candidates,
    load_candidate_config_from_protocol,
    write_candidate_ledger,
)
from spirallens.metrics.neighbor_audit import (
    NEIGHBOR_AUDIT_SCHEMA_VERSION,
    NeighborAuditConfig,
    NeighborAuditProtocolBinding,
    NeighborAuditResult,
    audit_neighbor_backend,
    load_neighbor_audit,
    write_neighbor_audit,
)
from spirallens.metrics.norm_decomposition import (
    NormAngularDecomposition,
    cosine_similarity,
    decompose_difference,
)
from spirallens.metrics.whitening import WhiteningTransform, fit_whitening

__all__ = [
    "CandidateSearchConfig",
    "LedgerSummary",
    "NEIGHBOR_AUDIT_SCHEMA_VERSION",
    "NeighborAuditConfig",
    "NeighborAuditProtocolBinding",
    "NeighborAuditResult",
    "NormAngularDecomposition",
    "WhiteningTransform",
    "audit_neighbor_backend",
    "cosine_similarity",
    "decompose_difference",
    "extract_candidates_from_manifest",
    "fit_whitening",
    "iter_candidate_pairs",
    "iter_exact_reranked_candidates",
    "load_neighbor_audit",
    "load_candidate_config_from_protocol",
    "write_neighbor_audit",
    "write_candidate_ledger",
]
