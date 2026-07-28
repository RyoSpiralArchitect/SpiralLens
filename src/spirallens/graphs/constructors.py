"""Deterministic exhaustive rounded-float64 graph constructors."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .common import (
    MAX_GRAPH_ESTIMATED_PEAK_BYTES,
    GraphContractError,
    GraphFamily,
    graph_construction_estimated_peak_bytes,
    module_sha256,
)
from .contracts import (
    _GRAPH_RECEIPT_FACTORY_TOKEN,
    GraphConstructionReceipt,
    GraphFamilyIdentity,
    GraphInput,
    MutualKnnSpec,
    RadiusGraphSpec,
    SharedNeighborSpec,
)

_FAMILY_METADATA: dict[GraphFamily, tuple[str, str]] = {
    GraphFamily.MUTUAL_KNN: (
        "reciprocal-directed-k-nearest-neighbor",
        "numpy-exhaustive-rounded-mutual-knn",
    ),
    GraphFamily.FIXED_RADIUS: (
        "inclusive-fixed-euclidean-radius",
        "numpy-exhaustive-rounded-fixed-radius",
    ),
    GraphFamily.SHARED_NEIGHBOR: (
        "directed-knn-neighborhood-intersection-threshold",
        "numpy-exhaustive-rounded-shared-neighbor",
    ),
}


def _family_identity(family: GraphFamily) -> GraphFamilyIdentity:
    mechanism_id, implementation_id = _FAMILY_METADATA[family]
    return GraphFamilyIdentity(
        family=family,
        mechanism_id=mechanism_id,
        implementation_id=implementation_id,
        implementation_version="v0.1",
        source_sha256=module_sha256(str(Path(__file__))),
    )


def _pairwise_distances(graph_input: GraphInput) -> np.ndarray:
    states = graph_input.states
    row_count = states.shape[0]
    distances = np.empty((row_count, row_count), dtype="<f8")
    for row in range(row_count):
        differences = states - states[row]
        rounded_distances = np.hypot.reduce(
            np.abs(differences),
            axis=1,
        )
        if not np.all(np.isfinite(rounded_distances)):
            raise GraphContractError(
                "pairwise distance overflowed the arithmetic bound"
            )
        collapsed = np.any(differences != 0.0, axis=1) & (rounded_distances == 0.0)
        if np.any(collapsed):
            raise GraphContractError(
                "nonzero state separation underflowed to zero distance"
            )
        distances[row] = rounded_distances
    distances[distances == 0.0] = 0.0
    np.fill_diagonal(distances, np.inf)
    return distances


def _directed_neighbors(
    graph_input: GraphInput,
    distances: np.ndarray,
    *,
    neighbor_count: int,
) -> np.ndarray:
    row_count = graph_input.states.shape[0]
    if neighbor_count >= row_count:
        raise GraphContractError("neighbor_count must be smaller than row_count")
    row_indices = np.arange(row_count, dtype="<i8")
    directed = np.empty((row_count, neighbor_count), dtype="<i8")
    for row in range(row_count):
        order = np.lexsort(
            (
                row_indices,
                graph_input.vertex_ids,
                distances[row],
            )
        )
        directed[row] = order[:neighbor_count]
    return directed


def _component_labels(
    row_count: int,
    adjacency: list[list[int]],
) -> np.ndarray:
    labels = np.full(row_count, -1, dtype="<i8")
    next_label = 0
    for start in range(row_count):
        if labels[start] >= 0:
            continue
        labels[start] = next_label
        stack = [start]
        while stack:
            vertex = stack.pop()
            for neighbor in adjacency[vertex]:
                if labels[neighbor] < 0:
                    labels[neighbor] = next_label
                    stack.append(neighbor)
        next_label += 1
    return labels


def _two_core(
    row_count: int,
    adjacency: list[list[int]],
) -> np.ndarray:
    active = np.ones(row_count, dtype="|b1")
    degree = np.array([len(items) for items in adjacency], dtype="<i8")
    queue = [int(index) for index in np.flatnonzero(degree < 2)]
    cursor = 0
    while cursor < len(queue):
        vertex = queue[cursor]
        cursor += 1
        if not active[vertex]:
            continue
        active[vertex] = False
        for neighbor in adjacency[vertex]:
            if active[neighbor]:
                degree[neighbor] -= 1
                if degree[neighbor] == 1:
                    queue.append(neighbor)
    return active


def _receipt(
    graph_input: GraphInput,
    specification: MutualKnnSpec | RadiusGraphSpec | SharedNeighborSpec,
    distances: np.ndarray,
    edges: list[tuple[int, int]],
) -> GraphConstructionReceipt:
    row_count = graph_input.states.shape[0]
    edge_array = (
        np.asarray(edges, dtype="<i8").reshape(-1, 2)
        if edges
        else np.empty((0, 2), dtype="<i8")
    )
    weights = np.array(
        [float(distances[left, right]) for left, right in edges],
        dtype="<f8",
    )
    adjacency: list[list[int]] = [[] for _ in range(row_count)]
    for left, right in edges:
        adjacency[left].append(right)
        adjacency[right].append(left)
    for neighbors in adjacency:
        neighbors.sort()
    degree = np.array([len(neighbors) for neighbors in adjacency], dtype="<i8")
    return GraphConstructionReceipt(
        _factory_token=_GRAPH_RECEIPT_FACTORY_TOKEN,
        graph_input=graph_input,
        specification=specification,
        family_identity=_family_identity(specification.family),
        canonical_edges=edge_array,
        edge_distances=weights,
        component_labels=_component_labels(row_count, adjacency),
        degree=degree,
        two_core_mask=_two_core(row_count, adjacency),
    )


def _preflight(
    graph_input: GraphInput,
    *,
    family: GraphFamily,
    neighbor_count: int | None,
) -> None:
    row_count, feature_count = graph_input.states.shape
    if neighbor_count is not None and neighbor_count >= row_count:
        raise GraphContractError("neighbor_count must be smaller than row_count")
    estimated_peak = graph_construction_estimated_peak_bytes(
        row_count=row_count,
        feature_count=feature_count,
        family=family,
        neighbor_count=neighbor_count,
    )
    if estimated_peak > MAX_GRAPH_ESTIMATED_PEAK_BYTES:
        raise GraphContractError(
            "graph construction estimated working set exceeds the fixed 256 MiB cap"
        )


def construct_mutual_knn(
    graph_input: GraphInput,
    specification: MutualKnnSpec,
) -> GraphConstructionReceipt:
    """Construct reciprocal k-nearest-neighbor adjacency."""

    if not isinstance(graph_input, GraphInput):
        raise TypeError("graph_input must be a GraphInput")
    if not isinstance(specification, MutualKnnSpec):
        raise TypeError("specification must be a MutualKnnSpec")
    _preflight(
        graph_input,
        family=specification.family,
        neighbor_count=specification.neighbor_count,
    )
    distances = _pairwise_distances(graph_input)
    directed = _directed_neighbors(
        graph_input,
        distances,
        neighbor_count=specification.neighbor_count,
    )
    memberships = [
        {int(item) for item in directed[row]} for row in range(directed.shape[0])
    ]
    edges = [
        (left, right)
        for left in range(directed.shape[0])
        for right in range(left + 1, directed.shape[0])
        if right in memberships[left] and left in memberships[right]
    ]
    return _receipt(graph_input, specification, distances, edges)


def construct_radius_graph(
    graph_input: GraphInput,
    specification: RadiusGraphSpec,
) -> GraphConstructionReceipt:
    """Construct inclusive fixed-radius adjacency."""

    if not isinstance(graph_input, GraphInput):
        raise TypeError("graph_input must be a GraphInput")
    if not isinstance(specification, RadiusGraphSpec):
        raise TypeError("specification must be a RadiusGraphSpec")
    _preflight(
        graph_input,
        family=specification.family,
        neighbor_count=None,
    )
    distances = _pairwise_distances(graph_input)
    row_count = graph_input.states.shape[0]
    edges = [
        (left, right)
        for left in range(row_count)
        for right in range(left + 1, row_count)
        if distances[left, right] <= specification.radius
    ]
    return _receipt(graph_input, specification, distances, edges)


def construct_shared_neighbor_graph(
    graph_input: GraphInput,
    specification: SharedNeighborSpec,
) -> GraphConstructionReceipt:
    """Connect all unordered pairs whose directed-kNN sets overlap enough."""

    if not isinstance(graph_input, GraphInput):
        raise TypeError("graph_input must be a GraphInput")
    if not isinstance(specification, SharedNeighborSpec):
        raise TypeError("specification must be a SharedNeighborSpec")
    _preflight(
        graph_input,
        family=specification.family,
        neighbor_count=specification.neighbor_count,
    )
    distances = _pairwise_distances(graph_input)
    directed = _directed_neighbors(
        graph_input,
        distances,
        neighbor_count=specification.neighbor_count,
    )
    memberships = [
        {int(item) for item in directed[row]} for row in range(directed.shape[0])
    ]
    edges = [
        (left, right)
        for left in range(directed.shape[0])
        for right in range(left + 1, directed.shape[0])
        if len(memberships[left].intersection(memberships[right]))
        >= specification.minimum_shared_neighbors
    ]
    return _receipt(graph_input, specification, distances, edges)
