"""Provisional canonical-order graph and exact discrete-domain foundations.

The namespace provides immutable in-memory fingerprints over model-free
numerical inputs. It does not persist records, read a field/core/winding, or
qualify a graph family, topology claim, subject, or D0--D8 gate.
"""

from .common import (
    GRAPH_CLAIM_CEILING,
    GRAPH_CLAIM_SCOPE,
    GRAPH_PERSISTENCE_ROUND_TRIP_SUPPORTED,
    GRAPH_RECORD_SCOPE,
    MAX_GRAPH_ESTIMATED_PEAK_BYTES,
    GraphContractError,
    GraphFamily,
    GraphPurpose,
)
from .constructors import (
    construct_mutual_knn,
    construct_radius_graph,
    construct_shared_neighbor_graph,
)
from .contracts import (
    GRAPH_CONSTRUCTION_RECEIPT_VERSION,
    GRAPH_FAMILY_IDENTITY_RECEIPT_VERSION,
    GRAPH_INPUT_RECEIPT_VERSION,
    GRAPH_SPEC_RECEIPT_VERSION,
    GraphConstructionReceipt,
    GraphFamilyIdentity,
    GraphInput,
    GraphSpecValue,
    MutualKnnSpec,
    RadiusGraphSpec,
    SharedNeighborSpec,
)
from .diversity import (
    GRAPH_DIVERSITY_RECEIPT_VERSION,
    GRAPH_PAIR_DIVERSITY_RECEIPT_VERSION,
    GraphDiversityReceipt,
    GraphPairDiversity,
    measure_graph_diversity,
)
from .domain import (
    BOUNDARY_CYCLE_CLASS_SPEC_RECEIPT_VERSION,
    BOUNDARY_REFINEMENT_RULE_RECEIPT_VERSION,
    CYCLE_CLASS_BINDING_RECEIPT_VERSION,
    CYCLE_CLASS_MATCH_ATTEMPT_RECEIPT_VERSION,
    DISCRETE_DOMAIN_RECEIPT_VERSION,
    MAX_DOMAIN_ESTIMATED_PEAK_BYTES,
    BoundaryCycleClassSpec,
    BoundaryRefinementRule,
    CycleClassBinding,
    CycleClassMatchAttempt,
    DiscreteDomainComplex,
    bind_cycle_class,
    build_discrete_domain_complex,
    define_boundary_cycle_class,
)

__all__ = [
    "BOUNDARY_CYCLE_CLASS_SPEC_RECEIPT_VERSION",
    "BOUNDARY_REFINEMENT_RULE_RECEIPT_VERSION",
    "CYCLE_CLASS_BINDING_RECEIPT_VERSION",
    "CYCLE_CLASS_MATCH_ATTEMPT_RECEIPT_VERSION",
    "DISCRETE_DOMAIN_RECEIPT_VERSION",
    "GRAPH_CLAIM_CEILING",
    "GRAPH_CLAIM_SCOPE",
    "GRAPH_CONSTRUCTION_RECEIPT_VERSION",
    "GRAPH_DIVERSITY_RECEIPT_VERSION",
    "GRAPH_FAMILY_IDENTITY_RECEIPT_VERSION",
    "GRAPH_INPUT_RECEIPT_VERSION",
    "GRAPH_PAIR_DIVERSITY_RECEIPT_VERSION",
    "GRAPH_PERSISTENCE_ROUND_TRIP_SUPPORTED",
    "GRAPH_RECORD_SCOPE",
    "GRAPH_SPEC_RECEIPT_VERSION",
    "MAX_DOMAIN_ESTIMATED_PEAK_BYTES",
    "MAX_GRAPH_ESTIMATED_PEAK_BYTES",
    "BoundaryCycleClassSpec",
    "BoundaryRefinementRule",
    "CycleClassBinding",
    "CycleClassMatchAttempt",
    "DiscreteDomainComplex",
    "GraphConstructionReceipt",
    "GraphContractError",
    "GraphDiversityReceipt",
    "GraphFamily",
    "GraphFamilyIdentity",
    "GraphInput",
    "GraphPairDiversity",
    "GraphPurpose",
    "GraphSpecValue",
    "MutualKnnSpec",
    "RadiusGraphSpec",
    "SharedNeighborSpec",
    "bind_cycle_class",
    "build_discrete_domain_complex",
    "construct_mutual_knn",
    "construct_radius_graph",
    "construct_shared_neighbor_graph",
    "define_boundary_cycle_class",
    "measure_graph_diversity",
]
