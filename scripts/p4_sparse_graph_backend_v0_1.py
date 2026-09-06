#!/usr/bin/env python3
"""Bounded, model-free sparse geometry for the P4 Furnace warmup.

This is a separate development backend, not a change to the sealed exhaustive
constructors. A KD tree proposes exact-query candidates; canonical float64 norms
and row-id tie breaking decide every edge. No field or outcome enters this API.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json

import numpy as np
from scipy import sparse
from scipy.spatial import cKDTree

from spirallens.core.canonical import canonical_json_sha256
from spirallens.graphs.common import (
    array_sha256,
    coordinate_order_invariant_euclidean_norm,
)

SCHEMA_VERSION = "spirallens.p4-sparse-graph-backend.v0.1"
FAMILIES = ("mutual-knn", "fixed-radius", "shared-neighbor")
MAX_VERTICES = 300_000
MAX_K = 32
MAX_GRAPH_NNZ = 64_000_000
MAX_TOTAL_QUERY_CANDIDATES = 64_000_000
MAX_BATCH_QUERY_CANDIDATES = 2_000_000
MAX_SHARED_PRODUCTS = 500_000_000
MAX_BATCH_SHARED_PRODUCTS = 2_000_000
QUERY_BATCH = 1024
RECTANGLES = {
    "outer": (-1.0, 1.0, -1.0, 1.0),
    "inner": (-0.5, 0.5, -0.5, 0.5),
    "local_positive": (-0.75, -0.25, -0.25, 0.25),
    "local_negative": (0.25, 0.75, -0.25, 0.25),
    "offcore": (-0.25, 0.25, 0.5, 1.0),
}


class SparseBudgetError(ValueError):
    """A predeclared allocation/operation bound prevented construction."""


@dataclass(frozen=True)
class SparseGraph:
    family: str
    canonical_edges: np.ndarray
    degree: np.ndarray
    adjacency: sparse.csr_matrix
    receipt: dict

    @property
    def edge_order_sha256(self) -> str:
        return self.receipt["edge_order_sha256"]

    @property
    def fingerprint_sha256(self) -> str:
        return self.receipt["receipt_sha256"]


def _csr_receipt(matrix: sparse.csr_matrix) -> dict:
    matrix.sort_indices()
    return {
        "shape": list(matrix.shape),
        "nnz": int(matrix.nnz),
        "data_sha256": array_sha256(matrix.data),
        "indices_sha256": array_sha256(matrix.indices),
        "indptr_sha256": array_sha256(matrix.indptr),
        "storage_bytes": int(
            matrix.data.nbytes + matrix.indices.nbytes + matrix.indptr.nbytes
        ),
    }


def _rectangle_loop(axis: np.ndarray, bounds: tuple[float, ...]) -> np.ndarray:
    xmin, xmax, ymin, ymax = bounds
    side = len(axis)
    left, right = np.searchsorted(axis, [xmin, xmax], side="left")
    if right == side or axis[right] > xmax:
        right -= 1
    bottom, top = np.searchsorted(axis, [ymin, ymax], side="left")
    if top == side or axis[top] > ymax:
        top -= 1
    if left >= right or bottom >= top:
        raise ValueError("declared rectangle has no two-dimensional face support")
    # CCW induced boundary, minimum row id first, without a repeated endpoint.
    return np.asarray(
        [bottom * side + x for x in range(left, right)]
        + [y * side + right for y in range(bottom, top)]
        + [top * side + x for x in range(right, left, -1)]
        + [y * side + left for y in range(top, bottom, -1)],
        dtype="<i8",
    )


def make_domain(side: int) -> dict:
    """Make the prior square triangulation with exact sparse boundary maps."""
    if type(side) is not int or not 9 <= side <= 513 or side % 4 != 1:
        raise ValueError("side must be 4k+1 in [9,513]")
    count = side * side
    axis = np.linspace(-1.0, 1.0, side)
    x, y = np.meshgrid(axis, axis, indexing="xy")
    coords = np.column_stack((x.ravel(), y.ravel())).astype("<f8")
    base = (
        np.arange(side - 1, dtype="<i8")[:, None] * side
        + np.arange(side - 1, dtype="<i8")[None, :]
    ).ravel()
    faces = np.empty((2 * len(base), 3), dtype="<i8")
    faces[0::2] = np.column_stack((base, base + 1, base + side + 1))
    faces[1::2] = np.column_stack((base, base + side + 1, base + side))
    directed = faces[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2)
    signs = np.where(directed[:, 0] < directed[:, 1], 1, -1).astype(np.int32)
    ordered = np.sort(directed, axis=1)
    codes, inverse = np.unique(
        ordered[:, 0] * count + ordered[:, 1], return_inverse=True
    )
    edges = np.column_stack((codes // count, codes % count)).astype("<i8")
    edge_ids = np.arange(len(edges), dtype="<i8")
    d1 = sparse.csr_matrix(
        (
            np.tile(np.array([-1, 1], dtype=np.int32), len(edges)),
            (edges.ravel(), np.repeat(edge_ids, 2)),
        ),
        shape=(count, len(edges)),
        dtype=np.int32,
    )
    d2 = sparse.csr_matrix(
        (signs, (inverse, np.repeat(np.arange(len(faces)), 3))),
        shape=(len(edges), len(faces)),
        dtype=np.int32,
    )
    boundary_squared = d1 @ d2
    boundary_squared.eliminate_zeros()
    if boundary_squared.nnz:
        raise ValueError("exact sparse boundary identity d1 @ d2 != 0")
    loops = {name: _rectangle_loop(axis, bounds) for name, bounds in RECTANGLES.items()}
    loop_receipts = {}
    face_coords = coords[faces]
    for name, bounds in RECTANGLES.items():
        xmin, xmax, ymin, ymax = bounds
        selected = (
            (face_coords[:, :, 0] >= xmin)
            & (face_coords[:, :, 0] <= xmax)
            & (face_coords[:, :, 1] >= ymin)
            & (face_coords[:, :, 1] <= ymax)
        ).all(axis=1)
        induced = np.asarray(d2 @ selected.astype(np.int32)).ravel()
        loop = loops[name]
        loop_pairs = np.column_stack((loop, np.roll(loop, -1)))
        loop_codes = np.min(loop_pairs, axis=1) * count + np.max(loop_pairs, axis=1)
        loop_edge_ids = np.searchsorted(codes, loop_codes)
        expected = np.zeros(len(edges), dtype=np.int32)
        expected[loop_edge_ids] = np.where(loop_pairs[:, 0] < loop_pairs[:, 1], 1, -1)
        if not np.array_equal(induced, expected):
            raise ValueError("rectangle boundary differs from selected face boundary")
        loop_receipts[name] = {
            "bounds": list(bounds),
            "vertex_count": len(loop),
            "boundary_sha256": array_sha256(loop),
            "support_face_count": int(selected.sum()),
            "support_faces_sha256": array_sha256(
                np.flatnonzero(selected).astype("<i8")
            ),
            "induced_boundary_verified": True,
        }
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "side": side,
        "vertex_count": count,
        "face_count": len(faces),
        "edge_count": len(edges),
        "coords_sha256": array_sha256(coords),
        "faces_sha256": array_sha256(faces),
        "edge_order_sha256": array_sha256(edges),
        "d1": _csr_receipt(d1),
        "d2": _csr_receipt(d2),
        "boundary_squared_nnz": int(boundary_squared.nnz),
        "exact_boundary_identity_verified": True,
        "loops": loop_receipts,
        "hypothetical_dense_float64_bytes": {
            "pairwise_distances": 8 * count * count,
            "d1": 8 * count * len(edges),
            "d2": 8 * len(edges) * len(faces),
        },
        "sparse_domain_bytes": _csr_receipt(d1)["storage_bytes"]
        + _csr_receipt(d2)["storage_bytes"],
        "native_domain_receipt": False,
        "scientific_authority": False,
    }
    receipt["domain_sha256"] = canonical_json_sha256(receipt)
    return {
        "coords": coords,
        "faces": faces,
        "loops": loops,
        "canonical_edges": edges,
        "d1": d1,
        "d2": d2,
        "receipt": receipt,
    }


def _query_radius(radius: np.ndarray | float) -> np.ndarray:
    # Conservative rounding enclosure for the 4D KD-tree arithmetic. It only
    # broadens candidate retrieval; exact canonical distances decide inclusion.
    value = np.asarray(radius, dtype=np.float64)
    arithmetic = np.finfo(np.float64)
    # The absolute term also encloses underflow in a tree's squared distances;
    # tiny substrates can therefore hit the candidate cap rather than silently
    # lose canonically tied/nearby points.
    enclosure = value * (1 + 64 * arithmetic.eps) + 8 * np.sqrt(arithmetic.tiny)
    return np.nextafter(enclosure, np.inf)


def _query_candidates(tree: cKDTree, states: np.ndarray, radii: np.ndarray):
    counts = tree.query_ball_point(states, radii, eps=0.0, return_length=True)
    total = int(np.sum(counts, dtype=np.int64))
    if total > MAX_TOTAL_QUERY_CANDIDATES:
        raise SparseBudgetError("KD-tree candidate count exceeds fixed total budget")
    for start in range(0, len(states), QUERY_BATCH):
        end = min(start + QUERY_BATCH, len(states))
        if int(np.sum(counts[start:end])) > MAX_BATCH_QUERY_CANDIDATES:
            raise SparseBudgetError("KD-tree candidate batch exceeds fixed budget")
        candidates = tree.query_ball_point(
            states[start:end], radii[start:end], eps=0.0, return_sorted=False
        )
        yield start, candidates, total


def _directed_neighbors(states: np.ndarray, tree: cKDTree, k: int):
    count = len(states)
    query_k = max(k, 4)
    # Query only supplies a radius enclosing k other vertices, even with ties.
    distances, _ = tree.query(states, k=query_k + 1, eps=0.0, workers=1)
    radii = _query_radius(distances[:, -1])
    neighbors = np.empty((count, k), dtype="<i8")
    fourth = np.empty(count, dtype="<f8")
    candidate_count = 0
    for start, candidates, candidate_count in _query_candidates(tree, states, radii):
        for offset, proposed in enumerate(candidates):
            row = start + offset
            ids = np.asarray(proposed, dtype="<i8")
            ids = ids[ids != row]
            norms = coordinate_order_invariant_euclidean_norm(states[ids] - states[row])
            if not np.all(np.isfinite(norms)):
                raise ValueError("canonical graph distance is not finite")
            order = np.lexsort((ids, norms))
            if len(order) < query_k:
                raise ValueError(
                    "KD-tree candidates do not cover the requested neighbors"
                )
            neighbors[row] = ids[order[:k]]
            fourth[row] = norms[order[3]]
    return neighbors, float(np.median(fourth)), candidate_count


def _edge_arrays(blocks: list[np.ndarray], count: int) -> np.ndarray:
    if not blocks:
        return np.empty((0, 2), dtype="<i8")
    edges = np.concatenate(blocks).astype("<i8", copy=False)
    if len(edges) * 2 > MAX_GRAPH_NNZ:
        raise SparseBudgetError("graph adjacency nnz exceeds fixed budget")
    codes = edges[:, 0] * count + edges[:, 1]
    return edges[np.argsort(codes, kind="stable")]


def _graph(family: str, edges: np.ndarray, count: int, common: dict) -> SparseGraph:
    if len(edges) * 2 > MAX_GRAPH_NNZ:
        raise SparseBudgetError("graph adjacency nnz exceeds fixed budget")
    adjacency = sparse.csr_matrix(
        (
            np.ones(2 * len(edges), dtype=np.int32),
            (
                np.concatenate((edges[:, 0], edges[:, 1])),
                np.concatenate((edges[:, 1], edges[:, 0])),
            ),
        ),
        shape=(count, count),
    )
    degree = np.diff(adjacency.indptr).astype("<i8")
    receipt = {
        **common,
        "family": family,
        "edge_count": len(edges),
        "edge_order_sha256": array_sha256(edges),
        "degree_sha256": array_sha256(degree),
        "degree_min": int(degree.min()),
        "degree_max": int(degree.max()),
        "adjacency": _csr_receipt(adjacency),
    }
    receipt["receipt_sha256"] = canonical_json_sha256(receipt)
    return SparseGraph(family, edges, degree, adjacency, receipt)


def build_graphs(
    states: np.ndarray,
    *,
    k: int = 8,
    radius_multiplier: float = 1.15,
    min_shared: int = 3,
) -> dict[str, SparseGraph]:
    """Build three field-blind families without dense pairwise allocations.

    Vertex IDs are exactly row IDs. This backend deliberately accepts only
    finite 4D float64 substrates within the declared arithmetic/resource bounds.
    """
    states = np.asarray(states)
    if (
        states.ndim != 2
        or states.shape[1] != 4
        or states.dtype.kind != "f"
        or not 9 <= len(states) <= MAX_VERTICES
        or not np.all(np.isfinite(states))
        or np.max(np.abs(states)) > 1e100
    ):
        raise ValueError("states must be finite floating N x 4, 9 <= N <= 300000")
    if type(k) is not int or not 1 <= k <= min(MAX_K, len(states) - 1):
        raise ValueError("k must be an integer in [1,min(32,N-1)]")
    if type(min_shared) is not int or not 1 <= min_shared <= k:
        raise ValueError("min_shared must be an integer in [1,k]")
    if (
        isinstance(radius_multiplier, (bool, np.bool_))
        or not np.isfinite(radius_multiplier)
        or not 0 < radius_multiplier <= 4
    ):
        raise ValueError("radius_multiplier must be finite in (0,4]")
    states = np.ascontiguousarray(states, dtype="<f8")
    tree = cKDTree(states, compact_nodes=True, balanced_tree=True)
    neighbors, scale, candidate_count = _directed_neighbors(states, tree, k)
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError("nonpositive-support-state-scale")
    radius = float(radius_multiplier * scale)
    count = len(states)
    directed = sparse.csr_matrix(
        (
            np.ones(count * k, dtype=np.int32),
            neighbors.ravel(),
            np.arange(count + 1) * k,
        ),
        shape=(count, count),
    )
    directed.sort_indices()
    indegree = np.bincount(neighbors.ravel(), minlength=count).astype(np.int64)
    shared_products = sum(int(value) ** 2 for value in indegree)
    if shared_products > MAX_SHARED_PRODUCTS:
        raise SparseBudgetError("shared-neighbor product count exceeds fixed budget")
    common = {
        "schema_version": SCHEMA_VERSION,
        "input_sha256": array_sha256(states),
        "vertex_count": count,
        "neighbor_count": k,
        "neighbors_sha256": array_sha256(neighbors),
        "scale_neighbor_count": 4,
        "scale": scale,
        "radius_multiplier": float(radius_multiplier),
        "radius": radius,
        "minimum_shared_neighbors": min_shared,
        "directed_candidate_count": candidate_count,
        "shared_product_count": shared_products,
        "candidate_search": "ckdtree-exact-eps0-with-rounding-enclosure",
        "edge_decision": "canonical-magnitude-ordered-hypot-float64",
        "tie_breaking": "distance-then-row-id;vertex-id-equals-row-id",
        "native_graph_receipt": False,
        "approximate_neighbors": False,
        "scientific_authority": False,
        "hypothetical_dense_pairwise_bytes": 8 * count * count,
        "resource_caps": {
            "vertices": MAX_VERTICES,
            "graph_nnz": MAX_GRAPH_NNZ,
            "query_candidates": MAX_TOTAL_QUERY_CANDIDATES,
            "query_batch_candidates": MAX_BATCH_QUERY_CANDIDATES,
            "shared_products": MAX_SHARED_PRODUCTS,
            "shared_batch_products": MAX_BATCH_SHARED_PRODUCTS,
        },
    }
    mutual = sparse.triu(directed.multiply(directed.T), k=1, format="coo")
    mutual_edges = _edge_arrays([np.column_stack((mutual.row, mutual.col))], count)
    graphs = {"mutual-knn": _graph("mutual-knn", mutual_edges, count, common)}
    radius_blocks = []
    radius_edge_count = 0
    radius_radii = np.full(count, float(_query_radius(radius)))
    radius_candidates = 0
    for start, candidates, radius_candidates in _query_candidates(
        tree, states, radius_radii
    ):
        batch_edges = []
        for offset, proposed in enumerate(candidates):
            row = start + offset
            ids = np.asarray(proposed, dtype="<i8")
            ids = ids[ids > row]
            norms = coordinate_order_invariant_euclidean_norm(states[ids] - states[row])
            ids = ids[norms <= radius]
            if len(ids):
                batch_edges.append(np.column_stack((np.full(len(ids), row), ids)))
                radius_edge_count += len(ids)
        if radius_edge_count * 2 > MAX_GRAPH_NNZ:
            raise SparseBudgetError("radius graph adjacency nnz exceeds fixed budget")
        if batch_edges:
            radius_blocks.append(np.concatenate(batch_edges))
    graphs["fixed-radius"] = _graph(
        "fixed-radius",
        _edge_arrays(radius_blocks, count),
        count,
        {**common, "radius_candidate_count": radius_candidates},
    )
    shared_blocks = []
    shared_edge_count = 0
    transpose = directed.T.tocsr()
    for start in range(0, count, QUERY_BATCH):
        end = min(start + QUERY_BATCH, count)
        product_bound = int(indegree[neighbors[start:end]].sum())
        if product_bound > MAX_BATCH_SHARED_PRODUCTS:
            raise SparseBudgetError(
                "shared-neighbor product batch exceeds fixed budget"
            )
        overlap = (directed[start:end] @ transpose).tocoo()
        left = overlap.row.astype(np.int64) + start
        keep = (overlap.data >= min_shared) & (left < overlap.col)
        edges = np.column_stack((left[keep], overlap.col[keep])).astype("<i8")
        shared_edge_count += len(edges)
        if shared_edge_count * 2 > MAX_GRAPH_NNZ:
            raise SparseBudgetError("shared graph adjacency nnz exceeds fixed budget")
        if len(edges):
            shared_blocks.append(edges)
    graphs["shared-neighbor"] = _graph(
        "shared-neighbor", _edge_arrays(shared_blocks, count), count, common
    )
    return graphs


def self_test() -> dict:
    """Small exact parity against the unchanged exhaustive development kernel."""
    import prototype_p4_graph_cross_v0_1 as native
    from spirallens.graphs.common import GraphPurpose

    checks = []
    for side, warp in ((9, 0.0), (17, 0.0), (17, 0.75)):
        bundle = native.make_graph_cross_probes(
            native.GraphCrossSpec(side=side, warp=warp)
        )
        domain = make_domain(side)
        expected, _ = native.build_graphs(
            bundle.graph_input, GraphPurpose.CYCLE_CONSTRUCTION
        )
        actual = build_graphs(bundle.graph_input.states)
        loops, _ = native.bind_loops(
            bundle.graph_input,
            bundle.observations.coords,
            bundle.observations.faces,
            expected,
        )
        assert np.array_equal(domain["coords"], bundle.observations.coords)
        assert np.array_equal(domain["faces"], bundle.observations.faces)
        for family in FAMILIES:
            assert np.array_equal(
                actual[family].canonical_edges, expected[family].canonical_edges
            )
            assert (
                actual[family].edge_order_sha256 == expected[family].edge_order_sha256
            )
        for name, rows in loops.items():
            assert np.array_equal(domain["loops"][name], rows)
        checks.append({"side": side, "warp": warp, "exact_edges_and_loops": True})
    return {"schema_version": SCHEMA_VERSION, "passed": len(checks), "checks": checks}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.self_test:
        parser.error("choose --self-test")
    print(json.dumps(self_test(), sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
