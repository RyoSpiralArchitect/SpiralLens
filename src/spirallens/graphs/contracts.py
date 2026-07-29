"""Typed inputs, specifications, and receipts for canonical graph construction."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import ClassVar, TypeAlias

import numpy as np
from numpy.typing import NDArray

from spirallens.core.canonical import canonical_json_bytes, canonical_json_sha256

from .common import (
    GRAPH_CLAIM_CEILING,
    GRAPH_CLAIM_SCOPE,
    GRAPH_PERSISTENCE_ROUND_TRIP_SUPPORTED,
    GRAPH_RECORD_SCOPE,
    GRAPH_RESOURCE_ESTIMATOR_ID,
    GRAPH_RESOURCE_SAFETY_FACTOR,
    MAX_GRAPH_ESTIMATED_PEAK_BYTES,
    BoolArray,
    FloatArray,
    GraphContractError,
    GraphFamily,
    GraphPurpose,
    Int64Array,
    array_fingerprint,
    array_sha256,
    bool_vector,
    coordinate_order_invariant_euclidean_norm,
    float_matrix,
    float_vector,
    graph_construction_estimated_peak_bytes,
    graph_estimated_peak_bytes,
    int64_matrix,
    int64_vector,
    require_plain_int,
    require_positive_float,
    require_sha256,
    require_slug,
)

GRAPH_INPUT_RECEIPT_VERSION = "spirallens.graph-input-receipt.v0.1"
GRAPH_FAMILY_IDENTITY_RECEIPT_VERSION = "spirallens.graph-family-identity-receipt.v0.1"
GRAPH_SPEC_RECEIPT_VERSION = "spirallens.graph-construction-spec-receipt.v0.1"
GRAPH_CONSTRUCTION_RECEIPT_VERSION = "spirallens.graph-construction-receipt.v0.1"

GRAPH_METRIC_ID = "exhaustive-canonical-coordinate-order-euclidean-float64"
GRAPH_PREPROCESSING_ID = "identity-no-preprocessing"
GRAPH_EDGE_ORDER_ID = "row-index-left-right-lexicographic"
GRAPH_EDGE_WEIGHT_ID = "canonical-coordinate-order-euclidean-float64-distance"
GRAPH_KNN_TIE_POLICY_ID = (
    "canonical-coordinate-order-distance-then-vertex-id-then-row-index"
)

_GRAPH_RECEIPT_FACTORY_TOKEN = object()


@dataclass(frozen=True, slots=True)
class GraphInput:
    """Bounded, label-free numerical input shared by graph families."""

    primary_unit_id: str
    vertex_ids: Int64Array
    states: FloatArray

    receipt_version: ClassVar[str] = GRAPH_INPUT_RECEIPT_VERSION

    def __post_init__(self) -> None:
        require_slug(self.primary_unit_id, label="primary_unit_id")
        vertex_ids = int64_vector(self.vertex_ids, label="vertex_ids")
        states = float_matrix(self.states, label="states")
        if states.shape[0] != vertex_ids.shape[0]:
            raise GraphContractError(
                "states and vertex_ids must have the same row count"
            )
        if len(set(vertex_ids.tolist())) != vertex_ids.shape[0]:
            raise GraphContractError("vertex_ids must be unique")
        estimated_peak = graph_estimated_peak_bytes(
            row_count=states.shape[0],
            feature_count=states.shape[1],
        )
        if estimated_peak > MAX_GRAPH_ESTIMATED_PEAK_BYTES:
            raise GraphContractError(
                "graph input estimated pairwise working set exceeds the "
                "fixed 256 MiB cap"
            )
        maximum = float(np.max(np.abs(states)))
        safe_coordinate = math.sqrt(np.finfo(np.float64).max) / (
            16.0 * math.sqrt(float(states.shape[1]))
        )
        if maximum > safe_coordinate:
            raise GraphContractError(
                "state magnitude exceeds the derived-distance arithmetic bound"
            )
        object.__setattr__(self, "vertex_ids", vertex_ids)
        object.__setattr__(self, "states", states)

    @property
    def vertex_order_sha256(self) -> str:
        return array_sha256(self.vertex_ids)

    @property
    def state_sha256(self) -> str:
        return array_sha256(self.states)

    @property
    def estimated_peak_bytes(self) -> int:
        return graph_estimated_peak_bytes(
            row_count=self.states.shape[0],
            feature_count=self.states.shape[1],
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            "record_scope": GRAPH_RECORD_SCOPE,
            "persistence_round_trip_supported": (
                GRAPH_PERSISTENCE_ROUND_TRIP_SUPPORTED
            ),
            "primary_unit_id": self.primary_unit_id,
            "input_scope": "label-free-numerical-states-only",
            "vertex_ids": array_fingerprint(self.vertex_ids),
            "states": array_fingerprint(self.states),
            "resource_estimator_id": GRAPH_RESOURCE_ESTIMATOR_ID,
            "resource_safety_factor": GRAPH_RESOURCE_SAFETY_FACTOR,
            "estimated_peak_bytes": self.estimated_peak_bytes,
            "max_estimated_peak_bytes": MAX_GRAPH_ESTIMATED_PEAK_BYTES,
            "resource_claim_boundary": (
                "parameter-induced-runaway-allocation-guard-not-os-oom-guarantee"
            ),
            "field_read": False,
            "core_read": False,
            "winding_read": False,
            "semantic_labels_present": False,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


@dataclass(frozen=True, slots=True)
class GraphFamilyIdentity:
    """Source-bound identity of one declared adjacency mechanism."""

    family: GraphFamily
    mechanism_id: str
    implementation_id: str
    implementation_version: str
    source_sha256: str

    receipt_version: ClassVar[str] = GRAPH_FAMILY_IDENTITY_RECEIPT_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.family, GraphFamily):
            raise TypeError("family must be a GraphFamily")
        for name in (
            "mechanism_id",
            "implementation_id",
            "implementation_version",
        ):
            require_slug(getattr(self, name), label=name)
        require_sha256(self.source_sha256, label="source_sha256")

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            "record_scope": GRAPH_RECORD_SCOPE,
            "persistence_round_trip_supported": (
                GRAPH_PERSISTENCE_ROUND_TRIP_SUPPORTED
            ),
            "family": self.family.value,
            "mechanism_id": self.mechanism_id,
            "implementation_id": self.implementation_id,
            "implementation_version": self.implementation_version,
            "source_sha256": self.source_sha256,
            "identity_claim_boundary": (
                "declared-mechanism-identity-not-scientific-or-software-independence"
            ),
        }

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


@dataclass(frozen=True, slots=True)
class MutualKnnSpec:
    spec_id: str
    purpose: GraphPurpose
    neighbor_count: int

    family: ClassVar[GraphFamily] = GraphFamily.MUTUAL_KNN
    receipt_version: ClassVar[str] = GRAPH_SPEC_RECEIPT_VERSION

    def __post_init__(self) -> None:
        require_slug(self.spec_id, label="spec_id")
        if not isinstance(self.purpose, GraphPurpose):
            raise TypeError("purpose must be a GraphPurpose")
        object.__setattr__(
            self,
            "neighbor_count",
            require_plain_int(
                self.neighbor_count,
                label="neighbor_count",
                minimum=1,
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return _spec_dict(
            spec_id=self.spec_id,
            purpose=self.purpose,
            family=self.family,
            parameters={"neighbor_count": self.neighbor_count},
            tie_policy=GRAPH_KNN_TIE_POLICY_ID,
        )

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


@dataclass(frozen=True, slots=True)
class RadiusGraphSpec:
    spec_id: str
    purpose: GraphPurpose
    radius: float

    family: ClassVar[GraphFamily] = GraphFamily.FIXED_RADIUS
    receipt_version: ClassVar[str] = GRAPH_SPEC_RECEIPT_VERSION

    def __post_init__(self) -> None:
        require_slug(self.spec_id, label="spec_id")
        if not isinstance(self.purpose, GraphPurpose):
            raise TypeError("purpose must be a GraphPurpose")
        object.__setattr__(
            self,
            "radius",
            require_positive_float(self.radius, label="radius"),
        )

    def to_dict(self) -> dict[str, object]:
        return _spec_dict(
            spec_id=self.spec_id,
            purpose=self.purpose,
            family=self.family,
            parameters={
                "radius": self.radius,
                "threshold_comparison": "distance-less-than-or-equal",
            },
            tie_policy="not-applicable",
        )

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


@dataclass(frozen=True, slots=True)
class SharedNeighborSpec:
    spec_id: str
    purpose: GraphPurpose
    neighbor_count: int
    minimum_shared_neighbors: int

    family: ClassVar[GraphFamily] = GraphFamily.SHARED_NEIGHBOR
    receipt_version: ClassVar[str] = GRAPH_SPEC_RECEIPT_VERSION

    def __post_init__(self) -> None:
        require_slug(self.spec_id, label="spec_id")
        if not isinstance(self.purpose, GraphPurpose):
            raise TypeError("purpose must be a GraphPurpose")
        neighbor_count = require_plain_int(
            self.neighbor_count,
            label="neighbor_count",
            minimum=1,
        )
        minimum_shared = require_plain_int(
            self.minimum_shared_neighbors,
            label="minimum_shared_neighbors",
            minimum=1,
        )
        if minimum_shared > neighbor_count:
            raise GraphContractError(
                "minimum_shared_neighbors must not exceed neighbor_count"
            )
        object.__setattr__(self, "neighbor_count", neighbor_count)
        object.__setattr__(
            self,
            "minimum_shared_neighbors",
            minimum_shared,
        )

    def to_dict(self) -> dict[str, object]:
        return _spec_dict(
            spec_id=self.spec_id,
            purpose=self.purpose,
            family=self.family,
            parameters={
                "neighbor_count": self.neighbor_count,
                "minimum_shared_neighbors": self.minimum_shared_neighbors,
                "pair_scope": "all-unordered-vertex-pairs",
            },
            tie_policy=GRAPH_KNN_TIE_POLICY_ID,
        )

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


GraphSpecValue: TypeAlias = MutualKnnSpec | RadiusGraphSpec | SharedNeighborSpec


def _spec_dict(
    *,
    spec_id: str,
    purpose: GraphPurpose,
    family: GraphFamily,
    parameters: dict[str, object],
    tie_policy: str,
) -> dict[str, object]:
    return {
        "receipt_version": GRAPH_SPEC_RECEIPT_VERSION,
        "record_scope": GRAPH_RECORD_SCOPE,
        "persistence_round_trip_supported": (GRAPH_PERSISTENCE_ROUND_TRIP_SUPPORTED),
        "spec_id": spec_id,
        "purpose": purpose.value,
        "family": family.value,
        "metric_id": GRAPH_METRIC_ID,
        "preprocessing_id": GRAPH_PREPROCESSING_ID,
        "tie_policy_id": tie_policy,
        "canonical_edge_order_id": GRAPH_EDGE_ORDER_ID,
        "edge_weight_id": GRAPH_EDGE_WEIGHT_ID,
        "parameters": parameters,
        "scale_selection_performed": False,
        "qualification_gate_evaluated": False,
        "claim_ceiling": GRAPH_CLAIM_CEILING,
        "subject_access_authorized": False,
    }


@dataclass(frozen=True, slots=True, init=False)
class GraphConstructionReceipt:
    """Factory-produced graph and exact structural diagnostics."""

    graph_input: GraphInput
    specification: GraphSpecValue
    family_identity: GraphFamilyIdentity
    canonical_edges: Int64Array
    edge_distances: FloatArray
    component_labels: Int64Array
    degree: Int64Array
    two_core_mask: BoolArray

    receipt_version: ClassVar[str] = GRAPH_CONSTRUCTION_RECEIPT_VERSION

    def __init__(
        self,
        *,
        _factory_token: object = None,
        graph_input: GraphInput,
        specification: GraphSpecValue,
        family_identity: GraphFamilyIdentity,
        canonical_edges: NDArray[np.generic],
        edge_distances: NDArray[np.generic],
        component_labels: NDArray[np.generic],
        degree: NDArray[np.generic],
        two_core_mask: NDArray[np.generic],
    ) -> None:
        if _factory_token is not _GRAPH_RECEIPT_FACTORY_TOKEN:
            raise GraphContractError(
                "graph construction receipts must be produced by a constructor"
            )
        if not isinstance(graph_input, GraphInput):
            raise TypeError("graph_input must be a GraphInput")
        if not isinstance(
            specification,
            (MutualKnnSpec, RadiusGraphSpec, SharedNeighborSpec),
        ):
            raise TypeError("specification must be a graph specification")
        if not isinstance(family_identity, GraphFamilyIdentity):
            raise TypeError("family_identity must be a GraphFamilyIdentity")
        if family_identity.family is not specification.family:
            raise GraphContractError("family identity and graph specification disagree")
        edges = int64_matrix(
            canonical_edges,
            label="canonical_edges",
            width=2,
        )
        distances = float_vector(edge_distances, label="edge_distances")
        components = int64_vector(
            component_labels,
            label="component_labels",
        )
        degrees = int64_vector(degree, label="degree")
        two_core = bool_vector(two_core_mask, label="two_core_mask")
        row_count = graph_input.states.shape[0]
        if components.shape != (row_count,):
            raise GraphContractError("component_labels has the wrong shape")
        if degrees.shape != (row_count,):
            raise GraphContractError("degree has the wrong shape")
        if two_core.shape != (row_count,):
            raise GraphContractError("two_core_mask has the wrong shape")
        if distances.shape != (edges.shape[0],):
            raise GraphContractError("edge_distances must align with canonical_edges")
        edge_rows = tuple(tuple(int(item) for item in row) for row in edges)
        if any(
            left < 0 or right >= row_count or left >= right for left, right in edge_rows
        ):
            raise GraphContractError(
                "canonical edges must satisfy 0 <= left < right < row_count"
            )
        if edge_rows != tuple(sorted(set(edge_rows))):
            raise GraphContractError(
                "canonical edges must be unique and lexicographically sorted"
            )
        if np.any(distances < 0.0):
            raise GraphContractError("edge distances must be nonnegative")
        expected_degree = np.zeros(row_count, dtype="<i8")
        adjacency: list[list[int]] = [[] for _ in range(row_count)]
        expected_distances = np.empty(edges.shape[0], dtype="<f8")
        for edge_index, (left, right) in enumerate(edge_rows):
            expected_degree[left] += 1
            expected_degree[right] += 1
            adjacency[left].append(right)
            adjacency[right].append(left)
            difference = graph_input.states[left] - graph_input.states[right]
            expected_distance = float(
                coordinate_order_invariant_euclidean_norm(difference)
            )
            if not math.isfinite(expected_distance):
                raise GraphContractError(
                    "canonical edge distance overflowed the arithmetic bound"
                )
            expected_distances[edge_index] = expected_distance
        if not np.array_equal(degrees, expected_degree):
            raise GraphContractError("degree differs from canonical edges")
        if not np.array_equal(distances, expected_distances):
            raise GraphContractError(
                "edge_distances differ from graph_input states and canonical_edges"
            )
        if np.any(components < 0):
            raise GraphContractError("component labels must be nonnegative")
        labels = tuple(int(item) for item in np.unique(components))
        if labels != tuple(range(len(labels))):
            raise GraphContractError(
                "component labels must be canonical contiguous integers"
            )
        expected_components = np.full(row_count, -1, dtype="<i8")
        next_component = 0
        for start in range(row_count):
            if expected_components[start] >= 0:
                continue
            expected_components[start] = next_component
            stack = [start]
            while stack:
                vertex = stack.pop()
                for neighbor in adjacency[vertex]:
                    if expected_components[neighbor] < 0:
                        expected_components[neighbor] = next_component
                        stack.append(neighbor)
            next_component += 1
        if not np.array_equal(components, expected_components):
            raise GraphContractError("component_labels differ from canonical_edges")
        active = np.ones(row_count, dtype="|b1")
        residual_degree = expected_degree.copy()
        queue = [int(index) for index in np.flatnonzero(residual_degree < 2)]
        cursor = 0
        while cursor < len(queue):
            vertex = queue[cursor]
            cursor += 1
            if not active[vertex]:
                continue
            active[vertex] = False
            for neighbor in adjacency[vertex]:
                if active[neighbor]:
                    residual_degree[neighbor] -= 1
                    if residual_degree[neighbor] == 1:
                        queue.append(neighbor)
        if not np.array_equal(two_core, active):
            raise GraphContractError("two_core_mask differs from canonical_edges")
        object.__setattr__(self, "graph_input", graph_input)
        object.__setattr__(self, "specification", specification)
        object.__setattr__(self, "family_identity", family_identity)
        object.__setattr__(self, "canonical_edges", edges)
        object.__setattr__(self, "edge_distances", distances)
        object.__setattr__(self, "component_labels", components)
        object.__setattr__(self, "degree", degrees)
        object.__setattr__(self, "two_core_mask", two_core)

    @property
    def edge_order_sha256(self) -> str:
        return array_sha256(self.canonical_edges)

    @property
    def construction_estimated_peak_bytes(self) -> int:
        neighbor_count = (
            self.specification.neighbor_count
            if isinstance(self.specification, (MutualKnnSpec, SharedNeighborSpec))
            else None
        )
        return graph_construction_estimated_peak_bytes(
            row_count=self.graph_input.states.shape[0],
            feature_count=self.graph_input.states.shape[1],
            family=self.specification.family,
            neighbor_count=neighbor_count,
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
            "primary_unit_id": self.graph_input.primary_unit_id,
            "graph_input_fingerprint_sha256": (self.graph_input.fingerprint_sha256),
            "vertex_order_sha256": self.graph_input.vertex_order_sha256,
            "state_sha256": self.graph_input.state_sha256,
            "specification": self.specification.to_dict(),
            "family_identity": self.family_identity.to_dict(),
            "arrays": {
                "canonical_edges": array_fingerprint(self.canonical_edges),
                "edge_distances": array_fingerprint(self.edge_distances),
                "component_labels": array_fingerprint(self.component_labels),
                "degree": array_fingerprint(self.degree),
                "two_core_mask": array_fingerprint(self.two_core_mask),
            },
            "edge_count": int(self.canonical_edges.shape[0]),
            "component_count": int(np.unique(self.component_labels).shape[0]),
            "two_core_vertex_count": int(np.count_nonzero(self.two_core_mask)),
            "resource_estimator_id": GRAPH_RESOURCE_ESTIMATOR_ID,
            "resource_safety_factor": GRAPH_RESOURCE_SAFETY_FACTOR,
            "construction_estimated_peak_bytes": (
                self.construction_estimated_peak_bytes
            ),
            "max_estimated_peak_bytes": MAX_GRAPH_ESTIMATED_PEAK_BYTES,
            "resource_claim_boundary": (
                "conservative-python-working-set-model-not-os-oom-guarantee"
            ),
            "cycle_constructed": False,
            "field_read": False,
            "core_read": False,
            "winding_read": False,
            "qualification_gate_evaluated": False,
            "d0_d8_advanced": False,
            "subject_access_authorized": False,
        }

    @property
    def fingerprint_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def fingerprint_sha256(self) -> str:
        return hashlib.sha256(self.fingerprint_bytes).hexdigest()
