"""Measurement-only structural diversity across three declared graph families."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import ClassVar

import numpy as np

from spirallens.core.canonical import canonical_json_sha256

from .common import (
    GRAPH_CLAIM_CEILING,
    GRAPH_CLAIM_SCOPE,
    GRAPH_PERSISTENCE_ROUND_TRIP_SUPPORTED,
    GRAPH_RECORD_SCOPE,
    GraphContractError,
    GraphFamily,
    GraphPurpose,
)
from .contracts import GRAPH_METRIC_ID, GraphConstructionReceipt

GRAPH_PAIR_DIVERSITY_RECEIPT_VERSION = "spirallens.graph-pair-diversity-receipt.v0.1"
GRAPH_DIVERSITY_RECEIPT_VERSION = "spirallens.graph-diversity-receipt.v0.1"

_CANONICAL_GRAPH_FAMILY_ORDER = (
    GraphFamily.MUTUAL_KNN,
    GraphFamily.FIXED_RADIUS,
    GraphFamily.SHARED_NEIGHBOR,
)
_PAIR_DIVERSITY_FACTORY_TOKEN = object()
_DIVERSITY_RECEIPT_FACTORY_TOKEN = object()


@dataclass(frozen=True, slots=True, init=False)
class GraphPairDiversity:
    """Factory-produced structural comparisons for one graph-family pair."""

    left_family: GraphFamily
    right_family: GraphFamily
    left_graph_fingerprint_sha256: str
    right_graph_fingerprint_sha256: str
    left_edge_count: int
    right_edge_count: int
    edge_intersection_count: int
    edge_union_count: int
    edge_sets_equal: bool
    edge_jaccard_similarity: float | None
    edge_jaccard_defined: bool
    edge_jaccard_reason: str
    degree_pearson_correlation: float | None
    degree_pearson_defined: bool
    degree_pearson_reason: str
    component_vertex_pair_count: int
    component_pair_agreement_count: int
    component_pair_agreement: float | None
    component_pair_agreement_defined: bool
    component_pair_agreement_reason: str
    left_two_core_vertex_count: int
    right_two_core_vertex_count: int
    two_core_intersection_count: int
    two_core_union_count: int
    two_core_jaccard_similarity: float | None
    two_core_jaccard_defined: bool
    two_core_jaccard_reason: str

    receipt_version: ClassVar[str] = GRAPH_PAIR_DIVERSITY_RECEIPT_VERSION

    def __init__(
        self,
        *,
        _factory_token: object = None,
        left_family: GraphFamily,
        right_family: GraphFamily,
        left_graph_fingerprint_sha256: str,
        right_graph_fingerprint_sha256: str,
        left_edge_count: int,
        right_edge_count: int,
        edge_intersection_count: int,
        edge_union_count: int,
        edge_sets_equal: bool,
        edge_jaccard_similarity: float | None,
        edge_jaccard_defined: bool,
        edge_jaccard_reason: str,
        degree_pearson_correlation: float | None,
        degree_pearson_defined: bool,
        degree_pearson_reason: str,
        component_vertex_pair_count: int,
        component_pair_agreement_count: int,
        component_pair_agreement: float | None,
        component_pair_agreement_defined: bool,
        component_pair_agreement_reason: str,
        left_two_core_vertex_count: int,
        right_two_core_vertex_count: int,
        two_core_intersection_count: int,
        two_core_union_count: int,
        two_core_jaccard_similarity: float | None,
        two_core_jaccard_defined: bool,
        two_core_jaccard_reason: str,
    ) -> None:
        if _factory_token is not _PAIR_DIVERSITY_FACTORY_TOKEN:
            raise GraphContractError(
                "graph-pair diversity records must be produced by "
                "measure_graph_diversity"
            )
        values = locals()
        for name in self.__dataclass_fields__:
            if name == "receipt_version":
                continue
            object.__setattr__(self, name, values[name])

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            "record_scope": GRAPH_RECORD_SCOPE,
            "persistence_round_trip_supported": (
                GRAPH_PERSISTENCE_ROUND_TRIP_SUPPORTED
            ),
            "left_family": self.left_family.value,
            "right_family": self.right_family.value,
            "left_graph_fingerprint_sha256": (self.left_graph_fingerprint_sha256),
            "right_graph_fingerprint_sha256": (self.right_graph_fingerprint_sha256),
            "edge_comparison": {
                "left_count": self.left_edge_count,
                "right_count": self.right_edge_count,
                "intersection_count": self.edge_intersection_count,
                "union_count": self.edge_union_count,
                "sets_equal": self.edge_sets_equal,
                "jaccard_similarity": self.edge_jaccard_similarity,
                "jaccard_defined": self.edge_jaccard_defined,
                "jaccard_reason": self.edge_jaccard_reason,
            },
            "degree_comparison": {
                "pearson_correlation": self.degree_pearson_correlation,
                "pearson_defined": self.degree_pearson_defined,
                "pearson_reason": self.degree_pearson_reason,
            },
            "component_partition_comparison": {
                "vertex_pair_count": self.component_vertex_pair_count,
                "agreement_count": self.component_pair_agreement_count,
                "agreement": self.component_pair_agreement,
                "agreement_defined": self.component_pair_agreement_defined,
                "agreement_reason": self.component_pair_agreement_reason,
            },
            "two_core_comparison": {
                "left_vertex_count": self.left_two_core_vertex_count,
                "right_vertex_count": self.right_two_core_vertex_count,
                "intersection_count": self.two_core_intersection_count,
                "union_count": self.two_core_union_count,
                "jaccard_similarity": self.two_core_jaccard_similarity,
                "jaccard_defined": self.two_core_jaccard_defined,
                "jaccard_reason": self.two_core_jaccard_reason,
            },
        }

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


@dataclass(frozen=True, slots=True, init=False)
class GraphDiversityReceipt:
    """Canonical three-family structural measurements without a decision."""

    graphs: tuple[
        GraphConstructionReceipt,
        GraphConstructionReceipt,
        GraphConstructionReceipt,
    ]
    pairwise: tuple[
        GraphPairDiversity,
        GraphPairDiversity,
        GraphPairDiversity,
    ]
    graph_input_fingerprint_sha256: str
    primary_unit_id: str
    vertex_order_sha256: str
    state_sha256: str
    purpose: GraphPurpose
    adjacency_fingerprints_pairwise_distinct: bool

    receipt_version: ClassVar[str] = GRAPH_DIVERSITY_RECEIPT_VERSION

    def __init__(
        self,
        *,
        _factory_token: object = None,
        graphs: tuple[
            GraphConstructionReceipt,
            GraphConstructionReceipt,
            GraphConstructionReceipt,
        ],
        pairwise: tuple[
            GraphPairDiversity,
            GraphPairDiversity,
            GraphPairDiversity,
        ],
        graph_input_fingerprint_sha256: str,
        primary_unit_id: str,
        vertex_order_sha256: str,
        state_sha256: str,
        purpose: GraphPurpose,
        adjacency_fingerprints_pairwise_distinct: bool,
    ) -> None:
        if _factory_token is not _DIVERSITY_RECEIPT_FACTORY_TOKEN:
            raise GraphContractError(
                "graph diversity receipts must be produced by measure_graph_diversity"
            )
        object.__setattr__(self, "graphs", graphs)
        object.__setattr__(self, "pairwise", pairwise)
        object.__setattr__(
            self,
            "graph_input_fingerprint_sha256",
            graph_input_fingerprint_sha256,
        )
        object.__setattr__(self, "primary_unit_id", primary_unit_id)
        object.__setattr__(self, "vertex_order_sha256", vertex_order_sha256)
        object.__setattr__(self, "state_sha256", state_sha256)
        object.__setattr__(self, "purpose", purpose)
        object.__setattr__(
            self,
            "adjacency_fingerprints_pairwise_distinct",
            adjacency_fingerprints_pairwise_distinct,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            "record_scope": GRAPH_RECORD_SCOPE,
            "persistence_round_trip_supported": (
                GRAPH_PERSISTENCE_ROUND_TRIP_SUPPORTED
            ),
            "claim_scope": GRAPH_CLAIM_SCOPE,
            "claim_ceiling": GRAPH_CLAIM_CEILING,
            "measurement_scope": ("three-family-adjacency-structural-diversity-only"),
            "graph_input_fingerprint_sha256": (self.graph_input_fingerprint_sha256),
            "primary_unit_id": self.primary_unit_id,
            "vertex_order_sha256": self.vertex_order_sha256,
            "state_sha256": self.state_sha256,
            "metric_id": GRAPH_METRIC_ID,
            "purpose": self.purpose.value,
            "canonical_family_order": [
                family.value for family in _CANONICAL_GRAPH_FAMILY_ORDER
            ],
            "graphs": [
                {
                    "family": graph.specification.family.value,
                    "graph_fingerprint_sha256": graph.fingerprint_sha256,
                    "adjacency_fingerprint_sha256": graph.edge_order_sha256,
                    "specification_fingerprint_sha256": (
                        graph.specification.fingerprint_sha256
                    ),
                    "family_identity": graph.family_identity.to_dict(),
                }
                for graph in self.graphs
            ],
            "pairwise": [comparison.to_dict() for comparison in self.pairwise],
            "adjacency_fingerprints_pairwise_distinct": (
                self.adjacency_fingerprints_pairwise_distinct
            ),
            "nonclaims": [
                (
                    "declared-family-identity-does-not-establish-software-"
                    "or-scientific-independence"
                ),
                ("structural-difference-does-not-establish-statistical-independence"),
                "no-field-core-holonomy-winding-or-charge-is-read",
                "no-qualification-or-d0-d8-decision-is-made",
            ],
        }

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


def _edge_set(graph: GraphConstructionReceipt) -> set[tuple[int, int]]:
    return {(int(left), int(right)) for left, right in graph.canonical_edges.tolist()}


def _jaccard(
    left: set[object],
    right: set[object],
    *,
    empty_reason: str,
) -> tuple[int, int, float | None, bool, str]:
    intersection_count = len(left.intersection(right))
    union_count = len(left.union(right))
    if union_count == 0:
        return intersection_count, union_count, None, False, empty_reason
    return (
        intersection_count,
        union_count,
        intersection_count / union_count,
        True,
        "ok",
    )


def _degree_pearson(
    left: GraphConstructionReceipt,
    right: GraphConstructionReceipt,
) -> tuple[float | None, bool, str]:
    left_values = left.degree.astype("<f8", copy=False)
    right_values = right.degree.astype("<f8", copy=False)
    left_centered = left_values - float(np.mean(left_values))
    right_centered = right_values - float(np.mean(right_values))
    left_squared_norm = float(np.dot(left_centered, left_centered))
    right_squared_norm = float(np.dot(right_centered, right_centered))
    if left_squared_norm == 0.0 or right_squared_norm == 0.0:
        return None, False, "constant-degree-vector"
    denominator = math.sqrt(left_squared_norm * right_squared_norm)
    correlation = float(np.dot(left_centered, right_centered)) / denominator
    if not math.isfinite(correlation):
        raise GraphContractError("degree correlation arithmetic is nonfinite")
    return max(-1.0, min(1.0, correlation)), True, "ok"


def _component_pair_agreement(
    left: GraphConstructionReceipt,
    right: GraphConstructionReceipt,
) -> tuple[int, int, float | None, bool, str]:
    row_count = left.component_labels.shape[0]
    pair_count = row_count * (row_count - 1) // 2
    if pair_count == 0:
        return 0, 0, None, False, "fewer-than-two-vertices"
    left_counts = Counter(int(label) for label in left.component_labels)
    right_counts = Counter(int(label) for label in right.component_labels)
    joint_counts = Counter(
        (int(left_label), int(right_label))
        for left_label, right_label in zip(
            left.component_labels,
            right.component_labels,
            strict=True,
        )
    )
    left_same = sum(count * (count - 1) // 2 for count in left_counts.values())
    right_same = sum(count * (count - 1) // 2 for count in right_counts.values())
    same_in_both = sum(count * (count - 1) // 2 for count in joint_counts.values())
    agreement_count = pair_count - left_same - right_same + (2 * same_in_both)
    return (
        pair_count,
        agreement_count,
        agreement_count / pair_count,
        True,
        "ok",
    )


def _measure_pair(
    left: GraphConstructionReceipt,
    right: GraphConstructionReceipt,
) -> GraphPairDiversity:
    left_edges = _edge_set(left)
    right_edges = _edge_set(right)
    (
        edge_intersection,
        edge_union,
        edge_jaccard,
        edge_defined,
        edge_reason,
    ) = _jaccard(
        left_edges,
        right_edges,
        empty_reason="no-edges-in-pair",
    )
    degree_correlation, degree_defined, degree_reason = _degree_pearson(
        left,
        right,
    )
    (
        component_pair_count,
        component_agreement_count,
        component_agreement,
        component_defined,
        component_reason,
    ) = _component_pair_agreement(left, right)
    left_two_core = {int(row) for row in np.flatnonzero(left.two_core_mask)}
    right_two_core = {int(row) for row in np.flatnonzero(right.two_core_mask)}
    (
        two_core_intersection,
        two_core_union,
        two_core_jaccard,
        two_core_defined,
        two_core_reason,
    ) = _jaccard(
        left_two_core,
        right_two_core,
        empty_reason="no-two-core-support",
    )
    return GraphPairDiversity(
        _factory_token=_PAIR_DIVERSITY_FACTORY_TOKEN,
        left_family=left.specification.family,
        right_family=right.specification.family,
        left_graph_fingerprint_sha256=left.fingerprint_sha256,
        right_graph_fingerprint_sha256=right.fingerprint_sha256,
        left_edge_count=len(left_edges),
        right_edge_count=len(right_edges),
        edge_intersection_count=edge_intersection,
        edge_union_count=edge_union,
        edge_sets_equal=left_edges == right_edges,
        edge_jaccard_similarity=edge_jaccard,
        edge_jaccard_defined=edge_defined,
        edge_jaccard_reason=edge_reason,
        degree_pearson_correlation=degree_correlation,
        degree_pearson_defined=degree_defined,
        degree_pearson_reason=degree_reason,
        component_vertex_pair_count=component_pair_count,
        component_pair_agreement_count=component_agreement_count,
        component_pair_agreement=component_agreement,
        component_pair_agreement_defined=component_defined,
        component_pair_agreement_reason=component_reason,
        left_two_core_vertex_count=len(left_two_core),
        right_two_core_vertex_count=len(right_two_core),
        two_core_intersection_count=two_core_intersection,
        two_core_union_count=two_core_union,
        two_core_jaccard_similarity=two_core_jaccard,
        two_core_jaccard_defined=two_core_defined,
        two_core_jaccard_reason=two_core_reason,
    )


def measure_graph_diversity(
    graphs: tuple[GraphConstructionReceipt, ...],
) -> GraphDiversityReceipt:
    """Measure three-family structural differences without qualifying them."""

    if not isinstance(graphs, tuple):
        raise TypeError("graphs must be a tuple")
    if len(graphs) != len(_CANONICAL_GRAPH_FAMILY_ORDER):
        raise GraphContractError(
            "graph diversity requires exactly three graph receipts"
        )
    if any(not isinstance(graph, GraphConstructionReceipt) for graph in graphs):
        raise TypeError("graphs must contain GraphConstructionReceipt values")
    by_family = {graph.specification.family: graph for graph in graphs}
    if set(by_family) != set(_CANONICAL_GRAPH_FAMILY_ORDER):
        raise GraphContractError(
            "graph diversity requires exactly one receipt from each canonical "
            "graph family"
        )
    ordered = tuple(by_family[family] for family in _CANONICAL_GRAPH_FAMILY_ORDER)
    first = ordered[0]
    input_fingerprints = {graph.graph_input.fingerprint_sha256 for graph in ordered}
    vertex_order_digests = {graph.graph_input.vertex_order_sha256 for graph in ordered}
    state_digests = {graph.graph_input.state_sha256 for graph in ordered}
    if (
        len(input_fingerprints) != 1
        or len(vertex_order_digests) != 1
        or len(state_digests) != 1
    ):
        raise GraphContractError(
            "all graph families must bind the same GraphInput identity"
        )
    purposes = {graph.specification.purpose for graph in ordered}
    if len(purposes) != 1:
        raise GraphContractError(
            "all graph families must have the same predeclared purpose"
        )
    mechanism_ids = {graph.family_identity.mechanism_id for graph in ordered}
    implementation_ids = {graph.family_identity.implementation_id for graph in ordered}
    if len(mechanism_ids) != len(ordered) or len(implementation_ids) != len(ordered):
        raise GraphContractError(
            "canonical graph families must have distinct declared mechanism "
            "and implementation identifiers"
        )
    pairwise = (
        _measure_pair(ordered[0], ordered[1]),
        _measure_pair(ordered[0], ordered[2]),
        _measure_pair(ordered[1], ordered[2]),
    )
    adjacency_fingerprints = {graph.edge_order_sha256 for graph in ordered}
    return GraphDiversityReceipt(
        _factory_token=_DIVERSITY_RECEIPT_FACTORY_TOKEN,
        graphs=ordered,
        pairwise=pairwise,
        graph_input_fingerprint_sha256=first.graph_input.fingerprint_sha256,
        primary_unit_id=first.graph_input.primary_unit_id,
        vertex_order_sha256=first.graph_input.vertex_order_sha256,
        state_sha256=first.graph_input.state_sha256,
        purpose=first.specification.purpose,
        adjacency_fingerprints_pairwise_distinct=(
            len(adjacency_fingerprints) == len(ordered)
        ),
    )
