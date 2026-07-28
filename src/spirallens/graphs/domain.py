"""Graph-independent discrete domains and exact boundary refinements.

The records in this module are in-memory fingerprint receipts.  They deliberately
stop at exact finite combinatorics: a triangle complex is not a recovered latent
manifold, and equality of one declared support boundary is not a homology claim.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import ClassVar

import numpy as np
from numpy.typing import NDArray

from spirallens.core.canonical import canonical_json_bytes, canonical_json_sha256

from .common import (
    GRAPH_CLAIM_CEILING,
    GRAPH_CLAIM_SCOPE,
    GRAPH_PERSISTENCE_ROUND_TRIP_SUPPORTED,
    GRAPH_RECORD_SCOPE,
    GraphContractError,
    GraphPurpose,
    Int64Array,
    array_fingerprint,
    int64_matrix,
    int64_vector,
    require_plain_int,
    require_slug,
)
from .contracts import GraphConstructionReceipt, GraphInput

DISCRETE_DOMAIN_RECEIPT_VERSION = "spirallens.discrete-domain-receipt.v0.1"
BOUNDARY_REFINEMENT_RULE_RECEIPT_VERSION = (
    "spirallens.boundary-refinement-rule-receipt.v0.1"
)
BOUNDARY_CYCLE_CLASS_SPEC_RECEIPT_VERSION = (
    "spirallens.boundary-cycle-class-spec-receipt.v0.1"
)
CYCLE_CLASS_BINDING_RECEIPT_VERSION = "spirallens.cycle-class-binding-receipt.v0.1"
CYCLE_CLASS_MATCH_ATTEMPT_RECEIPT_VERSION = (
    "spirallens.cycle-class-match-attempt-receipt.v0.1"
)

DOMAIN_RESOURCE_ESTIMATOR_ID = "dense-integer-boundary-matrices-v0.1"
DOMAIN_RESOURCE_SAFETY_FACTOR = 2
MAX_DOMAIN_ESTIMATED_PEAK_BYTES = 256 * 1024 * 1024
_DOMAIN_RESOURCE_BASE_OVERHEAD_BYTES = 1024 * 1024

DOMAIN_FACE_CANONICALIZATION_ID = (
    "minimum-row-first-cyclic-rotation-preserving-handedness"
)
DOMAIN_EDGE_ORIENTATION_ID = "minimum-row-to-maximum-row"
DOMAIN_COEFFICIENT_RING = "integer"
DOMAIN_BOUNDARY_PROVENANCE_ID = "supplied-oriented-triangle-complex-exterior-boundary"
BOUNDARY_SUPPORT_EQUIVALENCE_ID = "same-induced-support-boundary"
BOUNDARY_SUPPORT_PROVENANCE_ID = "caller-supplied-face-support-induced-boundary"
BOUNDARY_COMPONENT_POLICY_ID = "require-one-simple-oriented-boundary-component"
BOUNDARY_ARC_MAPPING_ID = "forward-contiguous-domain-boundary-arc"
BOUNDARY_REFINEMENT_SELECTION_ID = "maximum-graph-edge-count-then-lexicographic"

_DOMAIN_FACTORY_TOKEN = object()
_CYCLE_SPEC_FACTORY_TOKEN = object()
_BINDING_FACTORY_TOKEN = object()
_ATTEMPT_FACTORY_TOKEN = object()


def _canonical_oriented_face(face: tuple[int, int, int]) -> tuple[int, int, int]:
    """Rotate a triangle without reflecting its declared handedness."""

    start = face.index(min(face))
    return face[start:] + face[:start]


def _directed_face_edges(
    face: tuple[int, int, int],
) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    return ((face[0], face[1]), (face[1], face[2]), (face[2], face[0]))


def _undirected_edge(left: int, right: int) -> tuple[int, int]:
    return (left, right) if left < right else (right, left)


def _domain_estimated_peak_bytes(
    *,
    vertex_count: int,
    edge_count: int,
    face_count: int,
) -> int:
    array_bytes = 8 * (
        3 * face_count
        + 2 * edge_count
        + vertex_count * edge_count
        + edge_count * face_count
        + vertex_count * face_count
    )
    return (
        _DOMAIN_RESOURCE_BASE_OVERHEAD_BYTES
        + DOMAIN_RESOURCE_SAFETY_FACTOR * array_bytes
    )


def _preflight_face_input(
    value: object,
    *,
    vertex_count: int,
) -> NDArray[np.generic]:
    source = np.asarray(value)
    if source.ndim != 2 or source.shape[1] != 3 or source.dtype.kind not in {"i", "u"}:
        raise GraphContractError(
            "oriented_triangles must be an integer matrix with width 3"
        )
    if source.shape[0] == 0:
        raise GraphContractError("oriented_triangles must be nonempty")
    face_count = int(source.shape[0])
    minimum_valid_edge_count = (3 * face_count + 1) // 2
    input_estimate = _domain_estimated_peak_bytes(
        vertex_count=vertex_count,
        edge_count=minimum_valid_edge_count,
        face_count=face_count,
    )
    if input_estimate > MAX_DOMAIN_ESTIMATED_PEAK_BYTES:
        raise GraphContractError(
            "domain triangle input exceeds the fixed 256 MiB resource cap"
        )
    return source


def _canonical_faces(
    source: NDArray[np.generic],
    *,
    vertex_count: int,
) -> tuple[tuple[int, int, int], ...]:
    faces: list[tuple[int, int, int]] = []
    undirected_faces: set[tuple[int, int, int]] = set()
    for raw_face in source:
        try:
            face = tuple(int(item) for item in raw_face)
        except (OverflowError, TypeError, ValueError) as error:
            raise GraphContractError(
                "oriented_triangles cannot be represented as row indices"
            ) from error
        if len(set(face)) != 3:
            raise GraphContractError(
                "each oriented triangle must contain three distinct row indices"
            )
        if any(vertex < 0 or vertex >= vertex_count for vertex in face):
            raise GraphContractError(
                "oriented triangle row indices fall outside the graph input"
            )
        undirected = tuple(sorted(face))
        if undirected in undirected_faces:
            raise GraphContractError(
                "an undirected triangle may occur only once in the domain"
            )
        undirected_faces.add(undirected)
        faces.append(_canonical_oriented_face(face))
    return tuple(sorted(faces))


def _edge_incidence(
    faces: tuple[tuple[int, int, int], ...],
) -> dict[tuple[int, int], list[tuple[int, int]]]:
    incidence: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    for face_index, face in enumerate(faces):
        for left, right in _directed_face_edges(face):
            edge = _undirected_edge(left, right)
            coefficient = 1 if (left, right) == edge else -1
            incidence[edge].append((face_index, coefficient))
    for edge, uses in incidence.items():
        if len(uses) > 2:
            raise GraphContractError(
                f"domain edge {edge} has more than two incident triangles"
            )
        if len(uses) == 2 and uses[0][1] == uses[1][1]:
            raise GraphContractError(
                "triangles sharing an edge must induce opposite orientations"
            )
    return dict(incidence)


def _require_face_connected(
    *,
    face_count: int,
    incidence: dict[tuple[int, int], list[tuple[int, int]]],
) -> None:
    adjacency: list[list[int]] = [[] for _ in range(face_count)]
    for uses in incidence.values():
        if len(uses) == 2:
            left = uses[0][0]
            right = uses[1][0]
            adjacency[left].append(right)
            adjacency[right].append(left)
    reached = {0}
    stack = [0]
    while stack:
        face = stack.pop()
        for neighbor in adjacency[face]:
            if neighbor not in reached:
                reached.add(neighbor)
                stack.append(neighbor)
    if len(reached) != face_count:
        raise GraphContractError(
            "oriented triangles must form one edge-connected face complex"
        )


@dataclass(frozen=True, slots=True, init=False)
class DiscreteDomainComplex:
    """Exact oriented triangular complex over ``GraphInput`` row indices."""

    graph_input: GraphInput
    domain_id: str
    primary_unit_id: str
    canonical_faces: Int64Array
    canonical_edges: Int64Array
    boundary_1: Int64Array
    boundary_2: Int64Array
    domain_boundary_directed_edges: Int64Array
    estimated_peak_bytes: int

    receipt_version: ClassVar[str] = DISCRETE_DOMAIN_RECEIPT_VERSION

    def __init__(
        self,
        *,
        _factory_token: object = None,
        graph_input: GraphInput,
        domain_id: str,
        primary_unit_id: str,
        canonical_faces: NDArray[np.generic],
        canonical_edges: NDArray[np.generic],
        boundary_1: NDArray[np.generic],
        boundary_2: NDArray[np.generic],
        domain_boundary_directed_edges: NDArray[np.generic],
        estimated_peak_bytes: int,
    ) -> None:
        if _factory_token is not _DOMAIN_FACTORY_TOKEN:
            raise GraphContractError(
                "discrete domain complexes must be produced by the domain builder"
            )
        if not isinstance(graph_input, GraphInput):
            raise TypeError("graph_input must be a GraphInput")
        require_slug(domain_id, label="domain_id")
        require_slug(primary_unit_id, label="primary_unit_id")
        if primary_unit_id != graph_input.primary_unit_id:
            raise GraphContractError(
                "domain primary_unit_id must equal the GraphInput primary_unit_id"
            )
        faces = int64_matrix(
            canonical_faces,
            label="canonical_faces",
            width=3,
            nonempty=True,
        )
        edges = int64_matrix(
            canonical_edges,
            label="canonical_edges",
            width=2,
            nonempty=True,
        )
        d1 = int64_matrix(
            boundary_1,
            label="boundary_1",
            width=edges.shape[0],
            nonempty=True,
        )
        d2 = int64_matrix(
            boundary_2,
            label="boundary_2",
            width=faces.shape[0],
            nonempty=True,
        )
        boundary_edges = int64_matrix(
            domain_boundary_directed_edges,
            label="domain_boundary_directed_edges",
            width=2,
        )
        if d1.shape != (graph_input.states.shape[0], edges.shape[0]):
            raise GraphContractError("boundary_1 has the wrong shape")
        if d2.shape != (edges.shape[0], faces.shape[0]):
            raise GraphContractError("boundary_2 has the wrong shape")
        if np.any(d1 @ d2):
            raise GraphContractError(
                "boundary matrices violate boundary_1*boundary_2=0"
            )
        peak = require_plain_int(
            estimated_peak_bytes,
            label="estimated_peak_bytes",
            minimum=0,
        )
        if peak > MAX_DOMAIN_ESTIMATED_PEAK_BYTES:
            raise GraphContractError(
                "domain estimated working set exceeds the fixed 256 MiB cap"
            )
        object.__setattr__(self, "graph_input", graph_input)
        object.__setattr__(self, "domain_id", domain_id)
        object.__setattr__(self, "primary_unit_id", primary_unit_id)
        object.__setattr__(self, "canonical_faces", faces)
        object.__setattr__(self, "canonical_edges", edges)
        object.__setattr__(self, "boundary_1", d1)
        object.__setattr__(self, "boundary_2", d2)
        object.__setattr__(
            self,
            "domain_boundary_directed_edges",
            boundary_edges,
        )
        object.__setattr__(self, "estimated_peak_bytes", peak)

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            "record_scope": GRAPH_RECORD_SCOPE,
            "persistence_round_trip_supported": (
                GRAPH_PERSISTENCE_ROUND_TRIP_SUPPORTED
            ),
            "claim_scope": GRAPH_CLAIM_SCOPE,
            "claim_ceiling": GRAPH_CLAIM_CEILING,
            "domain_id": self.domain_id,
            "primary_unit_id": self.primary_unit_id,
            "graph_input_fingerprint_sha256": self.graph_input.fingerprint_sha256,
            "vertex_order_sha256": self.graph_input.vertex_order_sha256,
            "state_sha256": self.graph_input.state_sha256,
            "row_reference": "graph-input-row-index",
            "face_canonicalization_id": DOMAIN_FACE_CANONICALIZATION_ID,
            "edge_orientation_id": DOMAIN_EDGE_ORIENTATION_ID,
            "coefficient_ring": DOMAIN_COEFFICIENT_RING,
            "domain_boundary_provenance_id": DOMAIN_BOUNDARY_PROVENANCE_ID,
            "arrays": {
                "canonical_faces": array_fingerprint(self.canonical_faces),
                "canonical_edges": array_fingerprint(self.canonical_edges),
                "boundary_1": array_fingerprint(self.boundary_1),
                "boundary_2": array_fingerprint(self.boundary_2),
                "domain_boundary_directed_edges": array_fingerprint(
                    self.domain_boundary_directed_edges
                ),
            },
            "face_count": int(self.canonical_faces.shape[0]),
            "edge_count": int(self.canonical_edges.shape[0]),
            "domain_boundary_edge_count": int(
                self.domain_boundary_directed_edges.shape[0]
            ),
            "chain_identity": "boundary_1-times-boundary_2-equals-zero-exactly",
            "resource_estimator_id": DOMAIN_RESOURCE_ESTIMATOR_ID,
            "resource_safety_factor": DOMAIN_RESOURCE_SAFETY_FACTOR,
            "estimated_peak_bytes": self.estimated_peak_bytes,
            "max_estimated_peak_bytes": MAX_DOMAIN_ESTIMATED_PEAK_BYTES,
            "latent_manifold_triangulation_claimed": False,
            "continuous_topology_claimed": False,
            "homology_claimed": False,
            "construction_observable_inputs_present": False,
            "caller_selection_history_verified": False,
            "core_read": False,
            "field_read": False,
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


def build_discrete_domain_complex(
    graph_input: GraphInput,
    oriented_triangles: object,
    *,
    domain_id: str,
    primary_unit_id: str,
) -> DiscreteDomainComplex:
    """Build and exactly validate one graph-independent triangle complex."""

    if not isinstance(graph_input, GraphInput):
        raise TypeError("graph_input must be a GraphInput")
    require_slug(domain_id, label="domain_id")
    require_slug(primary_unit_id, label="primary_unit_id")
    if primary_unit_id != graph_input.primary_unit_id:
        raise GraphContractError(
            "domain primary_unit_id must equal the GraphInput primary_unit_id"
        )
    source = _preflight_face_input(
        oriented_triangles,
        vertex_count=graph_input.states.shape[0],
    )
    faces = _canonical_faces(
        source,
        vertex_count=graph_input.states.shape[0],
    )
    incidence = _edge_incidence(faces)
    _require_face_connected(face_count=len(faces), incidence=incidence)
    edges = tuple(sorted(incidence))
    peak = _domain_estimated_peak_bytes(
        vertex_count=graph_input.states.shape[0],
        edge_count=len(edges),
        face_count=len(faces),
    )
    if peak > MAX_DOMAIN_ESTIMATED_PEAK_BYTES:
        raise GraphContractError(
            "domain boundary matrices exceed the fixed 256 MiB resource cap"
        )

    edge_index = {edge: index for index, edge in enumerate(edges)}
    d1 = np.zeros((graph_input.states.shape[0], len(edges)), dtype="<i8")
    for index, (left, right) in enumerate(edges):
        d1[left, index] = -1
        d1[right, index] = 1
    d2 = np.zeros((len(edges), len(faces)), dtype="<i8")
    for face_index, face in enumerate(faces):
        for left, right in _directed_face_edges(face):
            edge = _undirected_edge(left, right)
            d2[edge_index[edge], face_index] = 1 if (left, right) == edge else -1
    if np.any(d1 @ d2):
        raise GraphContractError("derived boundary matrices violate the chain identity")

    boundary_edges = []
    for edge in edges:
        uses = incidence[edge]
        if len(uses) == 1:
            coefficient = uses[0][1]
            boundary_edges.append(edge if coefficient == 1 else edge[::-1])

    return DiscreteDomainComplex(
        _factory_token=_DOMAIN_FACTORY_TOKEN,
        graph_input=graph_input,
        domain_id=domain_id,
        primary_unit_id=primary_unit_id,
        canonical_faces=np.asarray(faces, dtype="<i8"),
        canonical_edges=np.asarray(edges, dtype="<i8"),
        boundary_1=d1,
        boundary_2=d2,
        domain_boundary_directed_edges=np.asarray(
            boundary_edges,
            dtype="<i8",
        ).reshape(-1, 2),
        estimated_peak_bytes=peak,
    )


@dataclass(frozen=True, slots=True)
class BoundaryRefinementRule:
    """Caller-declared limit for replacing one graph edge by a boundary arc."""

    rule_id: str
    max_domain_edges_per_graph_edge: int

    receipt_version: ClassVar[str] = BOUNDARY_REFINEMENT_RULE_RECEIPT_VERSION

    def __post_init__(self) -> None:
        require_slug(self.rule_id, label="rule_id")
        object.__setattr__(
            self,
            "max_domain_edges_per_graph_edge",
            require_plain_int(
                self.max_domain_edges_per_graph_edge,
                label="max_domain_edges_per_graph_edge",
                minimum=1,
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            "record_scope": GRAPH_RECORD_SCOPE,
            "persistence_round_trip_supported": (
                GRAPH_PERSISTENCE_ROUND_TRIP_SUPPORTED
            ),
            "rule_id": self.rule_id,
            "mapping_id": BOUNDARY_ARC_MAPPING_ID,
            "selection_id": BOUNDARY_REFINEMENT_SELECTION_ID,
            "max_domain_edges_per_graph_edge": (self.max_domain_edges_per_graph_edge),
            "orientation_policy": "preserve-induced-support-boundary-orientation",
            "observable_inputs_accepted_by_api": False,
            "caller_selection_history_verified": False,
            "preobservation_rule_seal_verified": False,
            "outcome_independent_rule_selection_established": False,
            "qualification_gate_evaluated": False,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


def _selected_face_adjacency(
    domain: DiscreteDomainComplex,
    support: tuple[int, ...],
) -> list[list[int]]:
    local_index = {face: index for index, face in enumerate(support)}
    adjacency: list[list[int]] = [[] for _ in support]
    edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    for face_index in support:
        face = tuple(int(item) for item in domain.canonical_faces[face_index])
        for left, right in _directed_face_edges(face):
            edge_faces[_undirected_edge(left, right)].append(face_index)
    for uses in edge_faces.values():
        if len(uses) == 2:
            left = local_index[uses[0]]
            right = local_index[uses[1]]
            adjacency[left].append(right)
            adjacency[right].append(left)
    return adjacency


def _require_support_connected(
    domain: DiscreteDomainComplex,
    support: tuple[int, ...],
) -> None:
    adjacency = _selected_face_adjacency(domain, support)
    reached = {0}
    stack = [0]
    while stack:
        local_face = stack.pop()
        for neighbor in adjacency[local_face]:
            if neighbor not in reached:
                reached.add(neighbor)
                stack.append(neighbor)
    if len(reached) != len(support):
        raise GraphContractError(
            "support_face_indices must select one edge-connected face support"
        )


def _induced_simple_boundary(
    domain: DiscreteDomainComplex,
    support: tuple[int, ...],
) -> tuple[tuple[int, ...], tuple[tuple[int, int], ...]]:
    directed_by_edge: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    for face_index in support:
        face = tuple(int(item) for item in domain.canonical_faces[face_index])
        for directed in _directed_face_edges(face):
            directed_by_edge[_undirected_edge(*directed)].append(directed)
    remaining: list[tuple[int, int]] = []
    for uses in directed_by_edge.values():
        if len(uses) == 1:
            remaining.append(uses[0])
        elif len(uses) == 2 and uses[0] == uses[1][::-1]:
            continue
        else:
            raise GraphContractError(
                "selected support has inconsistent oriented edge incidence"
            )
    if len(remaining) < 3:
        raise GraphContractError(
            "selected support must induce a boundary with at least three edges"
        )

    outgoing: dict[int, int] = {}
    incoming: dict[int, int] = {}
    for left, right in remaining:
        if left in outgoing or right in incoming:
            raise GraphContractError(
                "selected support does not induce one simple oriented boundary"
            )
        outgoing[left] = right
        incoming[right] = left
    vertices = set(outgoing) | set(incoming)
    if set(outgoing) != vertices or set(incoming) != vertices:
        raise GraphContractError(
            "selected support boundary is not a closed oriented cycle"
        )

    start = min(vertices)
    ordered_vertices = [start]
    current = start
    for _ in range(len(remaining) - 1):
        current = outgoing[current]
        if current == start or current in ordered_vertices:
            raise GraphContractError(
                "selected support induces multiple or non-simple boundary cycles"
            )
        ordered_vertices.append(current)
    if outgoing[current] != start or len(ordered_vertices) != len(vertices):
        raise GraphContractError(
            "selected support induces multiple or non-simple boundary cycles"
        )
    ordered_edges = tuple(
        (
            ordered_vertices[index],
            ordered_vertices[(index + 1) % len(ordered_vertices)],
        )
        for index in range(len(ordered_vertices))
    )
    if set(ordered_edges) != set(remaining):
        raise GraphContractError(
            "selected support induces multiple oriented boundary components"
        )
    return tuple(ordered_vertices), ordered_edges


@dataclass(frozen=True, slots=True, init=False)
class BoundaryCycleClassSpec:
    """One exact face support and its single induced oriented boundary."""

    domain: DiscreteDomainComplex
    cycle_class_spec_id: str
    primary_unit_id: str
    matched_set_id: str
    support_face_indices: Int64Array
    boundary_vertex_rows: Int64Array
    induced_boundary_edges: Int64Array

    receipt_version: ClassVar[str] = BOUNDARY_CYCLE_CLASS_SPEC_RECEIPT_VERSION

    def __init__(
        self,
        *,
        _factory_token: object = None,
        domain: DiscreteDomainComplex,
        cycle_class_spec_id: str,
        primary_unit_id: str,
        matched_set_id: str,
        support_face_indices: NDArray[np.generic],
        boundary_vertex_rows: NDArray[np.generic],
        induced_boundary_edges: NDArray[np.generic],
    ) -> None:
        if _factory_token is not _CYCLE_SPEC_FACTORY_TOKEN:
            raise GraphContractError(
                "boundary cycle-class specifications must be factory-produced"
            )
        if not isinstance(domain, DiscreteDomainComplex):
            raise TypeError("domain must be a DiscreteDomainComplex")
        require_slug(cycle_class_spec_id, label="cycle_class_spec_id")
        require_slug(primary_unit_id, label="primary_unit_id")
        require_slug(matched_set_id, label="matched_set_id")
        if primary_unit_id != domain.primary_unit_id:
            raise GraphContractError(
                "cycle-class primary_unit_id must equal the domain primary_unit_id"
            )
        support = int64_vector(
            support_face_indices,
            label="support_face_indices",
        )
        vertices = int64_vector(
            boundary_vertex_rows,
            label="boundary_vertex_rows",
        )
        edges = int64_matrix(
            induced_boundary_edges,
            label="induced_boundary_edges",
            width=2,
            nonempty=True,
        )
        if support.shape[0] == 0 or vertices.shape[0] < 3:
            raise GraphContractError("cycle-class support or boundary is empty")
        if edges.shape[0] != vertices.shape[0]:
            raise GraphContractError(
                "induced_boundary_edges must align with boundary_vertex_rows"
            )
        object.__setattr__(self, "domain", domain)
        object.__setattr__(self, "cycle_class_spec_id", cycle_class_spec_id)
        object.__setattr__(self, "primary_unit_id", primary_unit_id)
        object.__setattr__(self, "matched_set_id", matched_set_id)
        object.__setattr__(self, "support_face_indices", support)
        object.__setattr__(self, "boundary_vertex_rows", vertices)
        object.__setattr__(self, "induced_boundary_edges", edges)

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            "record_scope": GRAPH_RECORD_SCOPE,
            "persistence_round_trip_supported": (
                GRAPH_PERSISTENCE_ROUND_TRIP_SUPPORTED
            ),
            "claim_scope": GRAPH_CLAIM_SCOPE,
            "claim_ceiling": GRAPH_CLAIM_CEILING,
            "cycle_class_spec_id": self.cycle_class_spec_id,
            "primary_unit_id": self.primary_unit_id,
            "matched_set_id": self.matched_set_id,
            "domain_fingerprint_sha256": self.domain.fingerprint_sha256,
            "graph_input_fingerprint_sha256": (
                self.domain.graph_input.fingerprint_sha256
            ),
            "equivalence_relation_id": BOUNDARY_SUPPORT_EQUIVALENCE_ID,
            "support_provenance_id": BOUNDARY_SUPPORT_PROVENANCE_ID,
            "boundary_component_policy_id": BOUNDARY_COMPONENT_POLICY_ID,
            "arrays": {
                "support_face_indices": array_fingerprint(self.support_face_indices),
                "boundary_vertex_rows": array_fingerprint(self.boundary_vertex_rows),
                "induced_boundary_edges": array_fingerprint(
                    self.induced_boundary_edges
                ),
            },
            "support_face_count": int(self.support_face_indices.shape[0]),
            "boundary_edge_count": int(self.induced_boundary_edges.shape[0]),
            "same_support_is_generic_homology": False,
            "homology_claimed": False,
            "homotopy_claimed": False,
            "topology_claimed": False,
            "support_called_core": False,
            "observable_inputs_accepted_by_api": False,
            "caller_selection_history_verified": False,
            "preobservation_support_seal_verified": False,
            "outcome_independent_support_selection_established": False,
            "core_read": False,
            "field_read": False,
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


def define_boundary_cycle_class(
    domain: DiscreteDomainComplex,
    support_face_indices: Iterable[int] | NDArray[np.generic],
    *,
    cycle_class_spec_id: str,
    primary_unit_id: str,
    matched_set_id: str,
) -> BoundaryCycleClassSpec:
    """Derive one exact boundary from a caller-declared face support."""

    if not isinstance(domain, DiscreteDomainComplex):
        raise TypeError("domain must be a DiscreteDomainComplex")
    require_slug(cycle_class_spec_id, label="cycle_class_spec_id")
    require_slug(primary_unit_id, label="primary_unit_id")
    require_slug(matched_set_id, label="matched_set_id")
    if primary_unit_id != domain.primary_unit_id:
        raise GraphContractError(
            "cycle-class primary_unit_id must equal the domain primary_unit_id"
        )
    try:
        raw_support = tuple(
            require_plain_int(
                item,
                label=f"support_face_indices[{index}]",
                minimum=0,
            )
            for index, item in enumerate(support_face_indices)
        )
    except TypeError as error:
        raise GraphContractError(
            "support_face_indices must be an integer iterable"
        ) from error
    if not raw_support:
        raise GraphContractError("support_face_indices must be nonempty")
    if len(set(raw_support)) != len(raw_support):
        raise GraphContractError("support_face_indices must be unique")
    support = tuple(sorted(raw_support))
    if support[0] < 0 or support[-1] >= domain.canonical_faces.shape[0]:
        raise GraphContractError(
            "support_face_indices fall outside the canonical domain faces"
        )
    _require_support_connected(domain, support)
    boundary_vertices, boundary_edges = _induced_simple_boundary(
        domain,
        support,
    )
    return BoundaryCycleClassSpec(
        _factory_token=_CYCLE_SPEC_FACTORY_TOKEN,
        domain=domain,
        cycle_class_spec_id=cycle_class_spec_id,
        primary_unit_id=primary_unit_id,
        matched_set_id=matched_set_id,
        support_face_indices=np.asarray(support, dtype="<i8"),
        boundary_vertex_rows=np.asarray(boundary_vertices, dtype="<i8"),
        induced_boundary_edges=np.asarray(boundary_edges, dtype="<i8"),
    )


def _canonical_graph_edge(left: int, right: int) -> tuple[int, int]:
    return _undirected_edge(left, right)


@dataclass(frozen=True, slots=True, init=False)
class CycleClassBinding:
    """Exact graph-cycle refinement of one caller-declared support boundary."""

    graph_receipt: GraphConstructionReceipt
    cycle_class_spec: BoundaryCycleClassSpec
    refinement_rule: BoundaryRefinementRule
    boundary_start_offset: int
    graph_cycle_vertex_rows: Int64Array
    lifted_boundary_offsets: Int64Array
    lifted_boundary_arcs: Int64Array

    receipt_version: ClassVar[str] = CYCLE_CLASS_BINDING_RECEIPT_VERSION

    def __init__(
        self,
        *,
        _factory_token: object = None,
        graph_receipt: GraphConstructionReceipt,
        cycle_class_spec: BoundaryCycleClassSpec,
        refinement_rule: BoundaryRefinementRule,
        boundary_start_offset: int,
        graph_cycle_vertex_rows: NDArray[np.generic],
        lifted_boundary_offsets: NDArray[np.generic],
        lifted_boundary_arcs: NDArray[np.generic],
    ) -> None:
        if _factory_token is not _BINDING_FACTORY_TOKEN:
            raise GraphContractError(
                "cycle-class bindings must be produced by bind_cycle_class"
            )
        if not isinstance(graph_receipt, GraphConstructionReceipt):
            raise TypeError("graph_receipt must be a GraphConstructionReceipt")
        if not isinstance(cycle_class_spec, BoundaryCycleClassSpec):
            raise TypeError("cycle_class_spec must be a BoundaryCycleClassSpec")
        if not isinstance(refinement_rule, BoundaryRefinementRule):
            raise TypeError("refinement_rule must be a BoundaryRefinementRule")
        vertices = int64_vector(
            graph_cycle_vertex_rows,
            label="graph_cycle_vertex_rows",
        )
        offsets = int64_vector(
            lifted_boundary_offsets,
            label="lifted_boundary_offsets",
        )
        arcs = int64_matrix(
            lifted_boundary_arcs,
            label="lifted_boundary_arcs",
            width=2,
            nonempty=True,
        )
        boundary_length = cycle_class_spec.boundary_vertex_rows.shape[0]
        start_offset = require_plain_int(
            boundary_start_offset,
            label="boundary_start_offset",
            minimum=0,
        )
        if start_offset >= boundary_length:
            raise GraphContractError(
                "boundary_start_offset falls outside the declared boundary"
            )
        if vertices.shape[0] < 3 or len(set(vertices.tolist())) != vertices.shape[0]:
            raise GraphContractError(
                "graph cycle must contain at least three unique row indices"
            )
        if offsets.shape != (vertices.shape[0] + 1,):
            raise GraphContractError(
                "lifted_boundary_offsets must delimit every graph edge"
            )
        if arcs.shape != (vertices.shape[0], 2):
            raise GraphContractError(
                "lifted_boundary_arcs must align with graph cycle edges"
            )
        if offsets[0] != 0 or offsets[-1] != boundary_length:
            raise GraphContractError(
                "lifted boundary offsets must cover the complete boundary once"
            )
        spans = np.diff(offsets)
        if np.any(spans <= 0) or np.any(
            spans > refinement_rule.max_domain_edges_per_graph_edge
        ):
            raise GraphContractError(
                "lifted boundary arcs violate the refinement bound"
            )
        expected_arcs = np.column_stack((offsets[:-1], offsets[1:]))
        if not np.array_equal(arcs, expected_arcs):
            raise GraphContractError(
                "lifted_boundary_arcs differ from lifted_boundary_offsets"
            )
        expected_vertex_offsets = (start_offset + offsets[:-1]) % boundary_length
        expected_vertices = cycle_class_spec.boundary_vertex_rows[
            expected_vertex_offsets
        ]
        if not np.array_equal(vertices, expected_vertices):
            raise GraphContractError(
                "graph cycle vertices do not start their declared boundary arcs"
            )
        graph_edges = {
            tuple(int(item) for item in edge) for edge in graph_receipt.canonical_edges
        }
        for index, left in enumerate(vertices):
            right = vertices[(index + 1) % vertices.shape[0]]
            if _canonical_graph_edge(int(left), int(right)) not in graph_edges:
                raise GraphContractError(
                    "graph cycle contains an edge absent from the graph receipt"
                )
        rotated_boundary_edges = np.concatenate(
            (
                cycle_class_spec.induced_boundary_edges[start_offset:],
                cycle_class_spec.induced_boundary_edges[:start_offset],
            ),
            axis=0,
        )
        mapped_edges = np.concatenate(
            [rotated_boundary_edges[int(start) : int(end)] for start, end in arcs],
            axis=0,
        )
        if not np.array_equal(
            mapped_edges,
            rotated_boundary_edges,
        ):
            raise GraphContractError(
                "lifted graph edges do not partition the induced boundary"
            )
        object.__setattr__(self, "graph_receipt", graph_receipt)
        object.__setattr__(self, "cycle_class_spec", cycle_class_spec)
        object.__setattr__(self, "refinement_rule", refinement_rule)
        object.__setattr__(self, "boundary_start_offset", start_offset)
        object.__setattr__(self, "graph_cycle_vertex_rows", vertices)
        object.__setattr__(self, "lifted_boundary_offsets", offsets)
        object.__setattr__(self, "lifted_boundary_arcs", arcs)

    @property
    def primary_unit_id(self) -> str:
        return self.cycle_class_spec.primary_unit_id

    @property
    def matched_set_id(self) -> str:
        return self.cycle_class_spec.matched_set_id

    @property
    def graph_cell_id(self) -> str:
        return f"graph-cell-{self.graph_receipt.fingerprint_sha256}"

    @property
    def graph_spec_id(self) -> str:
        return self.graph_receipt.specification.spec_id

    @property
    def representative_id(self) -> str:
        digest = canonical_json_sha256(
            {
                "graph": self.graph_receipt.fingerprint_sha256,
                "cycle_class": self.cycle_class_spec.fingerprint_sha256,
                "rule": self.refinement_rule.fingerprint_sha256,
                "boundary_start_offset": self.boundary_start_offset,
                "vertices": array_fingerprint(self.graph_cycle_vertex_rows),
                "offsets": array_fingerprint(self.lifted_boundary_offsets),
            }
        )
        return f"cycle-representative-{digest}"

    @property
    def content_equivalence_sha256(self) -> str:
        domain = self.cycle_class_spec.domain
        return canonical_json_sha256(
            {
                "equivalence_relation_id": BOUNDARY_SUPPORT_EQUIVALENCE_ID,
                "graph_input_fingerprint_sha256": (
                    domain.graph_input.fingerprint_sha256
                ),
                "domain_structural_content": {
                    "canonical_faces": array_fingerprint(domain.canonical_faces),
                    "canonical_edges": array_fingerprint(domain.canonical_edges),
                    "boundary_1": array_fingerprint(domain.boundary_1),
                    "boundary_2": array_fingerprint(domain.boundary_2),
                },
                "support_face_indices": array_fingerprint(
                    self.cycle_class_spec.support_face_indices
                ),
                "boundary_vertex_rows": array_fingerprint(
                    self.cycle_class_spec.boundary_vertex_rows
                ),
                "induced_boundary_edges": array_fingerprint(
                    self.cycle_class_spec.induced_boundary_edges
                ),
            }
        )

    @property
    def content_equivalence_group_id(self) -> str:
        return f"same-induced-boundary-{self.content_equivalence_sha256}"

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            "record_scope": GRAPH_RECORD_SCOPE,
            "persistence_round_trip_supported": (
                GRAPH_PERSISTENCE_ROUND_TRIP_SUPPORTED
            ),
            "claim_scope": GRAPH_CLAIM_SCOPE,
            "claim_ceiling": GRAPH_CLAIM_CEILING,
            "graph_receipt_fingerprint_sha256": (self.graph_receipt.fingerprint_sha256),
            "cycle_class_spec_fingerprint_sha256": (
                self.cycle_class_spec.fingerprint_sha256
            ),
            "refinement_rule": self.refinement_rule.to_dict(),
            "primary_unit_id": self.primary_unit_id,
            "matched_set_id": self.matched_set_id,
            "graph_cell_id": self.graph_cell_id,
            "graph_spec_id": self.graph_spec_id,
            "graph_family": self.graph_receipt.family_identity.family.value,
            "representative_id": self.representative_id,
            "content_equivalence_sha256": self.content_equivalence_sha256,
            "content_equivalence_group_id": self.content_equivalence_group_id,
            "equivalence_relation_id": BOUNDARY_SUPPORT_EQUIVALENCE_ID,
            "mapping_id": BOUNDARY_ARC_MAPPING_ID,
            "selection_id": BOUNDARY_REFINEMENT_SELECTION_ID,
            "orientation_relation": "same",
            "boundary_traversal_multiplicity": 1,
            "boundary_start_offset": self.boundary_start_offset,
            "arrays": {
                "graph_cycle_vertex_rows": array_fingerprint(
                    self.graph_cycle_vertex_rows
                ),
                "lifted_boundary_offsets": array_fingerprint(
                    self.lifted_boundary_offsets
                ),
                "lifted_boundary_arcs": array_fingerprint(self.lifted_boundary_arcs),
            },
            "graph_cycle_edge_count": int(self.graph_cycle_vertex_rows.shape[0]),
            "domain_boundary_edge_count": int(
                self.cycle_class_spec.induced_boundary_edges.shape[0]
            ),
            "mapped_boundary_chain": array_fingerprint(
                self.cycle_class_spec.induced_boundary_edges
            ),
            "mapped_boundary_chain_equals_declared": True,
            "mapped_boundary_cycle_is_cyclic_rotation_of_declared": True,
            "graph_family_is_statistical_replicate": False,
            "combinatorial_multiplicity_is_statistical_replication": False,
            "graph_cells_are_repeated_measures": True,
            "repeated_measure_primary_unit_id": self.primary_unit_id,
            "repeated_measure_matched_set_id": self.matched_set_id,
            "homology_claimed": False,
            "homotopy_claimed": False,
            "topology_claimed": False,
            "boundary_arc_mapping_establishes_geometric_realization": False,
            "boundary_arc_mapping_establishes_homotopy": False,
            "graph_family_cycle_invariance_evaluated": False,
            "common_boundary_availability_only": True,
            "caller_selection_history_verified": False,
            "core_read": False,
            "field_read": False,
            "holonomy_read": False,
            "winding_read": False,
            "charge_read": False,
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


@dataclass(frozen=True, slots=True, init=False)
class CycleClassMatchAttempt:
    """Typed matched/unmatched result for one exact graph refinement attempt."""

    graph_receipt: GraphConstructionReceipt
    cycle_class_spec: BoundaryCycleClassSpec
    refinement_rule: BoundaryRefinementRule
    matched: bool
    reason: str
    binding: CycleClassBinding | None

    receipt_version: ClassVar[str] = CYCLE_CLASS_MATCH_ATTEMPT_RECEIPT_VERSION

    def __init__(
        self,
        *,
        _factory_token: object = None,
        graph_receipt: GraphConstructionReceipt,
        cycle_class_spec: BoundaryCycleClassSpec,
        refinement_rule: BoundaryRefinementRule,
        matched: bool,
        reason: str,
        binding: CycleClassBinding | None,
    ) -> None:
        if _factory_token is not _ATTEMPT_FACTORY_TOKEN:
            raise GraphContractError(
                "cycle-class match attempts must be factory-produced"
            )
        if not isinstance(graph_receipt, GraphConstructionReceipt):
            raise TypeError("graph_receipt must be a GraphConstructionReceipt")
        if not isinstance(cycle_class_spec, BoundaryCycleClassSpec):
            raise TypeError("cycle_class_spec must be a BoundaryCycleClassSpec")
        if not isinstance(refinement_rule, BoundaryRefinementRule):
            raise TypeError("refinement_rule must be a BoundaryRefinementRule")
        if reason not in {"ok", "cycle-boundary-not-coverable"}:
            raise GraphContractError("cycle-class match reason is not supported")
        if matched != (binding is not None) or matched != (reason == "ok"):
            raise GraphContractError(
                "cycle-class match state, reason, and binding disagree"
            )
        if binding is not None and (
            binding.graph_receipt.fingerprint_sha256 != graph_receipt.fingerprint_sha256
            or binding.cycle_class_spec.fingerprint_sha256
            != cycle_class_spec.fingerprint_sha256
            or binding.refinement_rule.fingerprint_sha256
            != refinement_rule.fingerprint_sha256
        ):
            raise GraphContractError(
                "cycle-class match binding differs from the attempted contracts"
            )
        object.__setattr__(self, "graph_receipt", graph_receipt)
        object.__setattr__(self, "cycle_class_spec", cycle_class_spec)
        object.__setattr__(self, "refinement_rule", refinement_rule)
        object.__setattr__(self, "matched", matched)
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "binding", binding)

    @property
    def primary_unit_id(self) -> str:
        return self.cycle_class_spec.primary_unit_id

    @property
    def matched_set_id(self) -> str:
        return self.cycle_class_spec.matched_set_id

    @property
    def graph_cell_id(self) -> str:
        return f"graph-cell-{self.graph_receipt.fingerprint_sha256}"

    @property
    def graph_spec_id(self) -> str:
        return self.graph_receipt.specification.spec_id

    def to_dict(self) -> dict[str, object]:
        return {
            "receipt_version": self.receipt_version,
            "record_scope": GRAPH_RECORD_SCOPE,
            "persistence_round_trip_supported": (
                GRAPH_PERSISTENCE_ROUND_TRIP_SUPPORTED
            ),
            "claim_scope": GRAPH_CLAIM_SCOPE,
            "claim_ceiling": GRAPH_CLAIM_CEILING,
            "primary_unit_id": self.primary_unit_id,
            "matched_set_id": self.matched_set_id,
            "graph_cell_id": self.graph_cell_id,
            "graph_spec_id": self.graph_spec_id,
            "graph_cells_are_repeated_measures": True,
            "graph_receipt_fingerprint_sha256": (self.graph_receipt.fingerprint_sha256),
            "cycle_class_spec_fingerprint_sha256": (
                self.cycle_class_spec.fingerprint_sha256
            ),
            "refinement_rule_fingerprint_sha256": (
                self.refinement_rule.fingerprint_sha256
            ),
            "matched": self.matched,
            "reason": self.reason,
            "binding_fingerprint_sha256": (
                self.binding.fingerprint_sha256 if self.binding is not None else None
            ),
            "unmatched_is_measurement_not_gate": True,
            "common_boundary_availability_only": True,
            "graph_family_cycle_invariance_evaluated": False,
            "caller_selection_history_verified": False,
            "qualification_gate_evaluated": False,
            "homology_claimed": False,
            "topology_claimed": False,
            "core_read": False,
            "field_read": False,
            "holonomy_read": False,
            "winding_read": False,
            "charge_read": False,
            "d0_d8_advanced": False,
            "subject_access_authorized": False,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


def _validate_binding_join(
    graph_receipt: GraphConstructionReceipt,
    cycle_class_spec: BoundaryCycleClassSpec,
    refinement_rule: BoundaryRefinementRule,
) -> None:
    if not isinstance(graph_receipt, GraphConstructionReceipt):
        raise TypeError("graph_receipt must be a GraphConstructionReceipt")
    if not isinstance(cycle_class_spec, BoundaryCycleClassSpec):
        raise TypeError("cycle_class_spec must be a BoundaryCycleClassSpec")
    if not isinstance(refinement_rule, BoundaryRefinementRule):
        raise TypeError("refinement_rule must be a BoundaryRefinementRule")
    if (
        graph_receipt.graph_input.fingerprint_sha256
        != cycle_class_spec.domain.graph_input.fingerprint_sha256
    ):
        raise GraphContractError(
            "graph receipt and discrete domain use different GraphInput fingerprints"
        )
    if graph_receipt.specification.purpose is not GraphPurpose.CYCLE_CONSTRUCTION:
        raise GraphContractError(
            "cycle-class binding requires a cycle-construction graph purpose"
        )


def _best_linear_boundary_partition(
    *,
    boundary_vertices: tuple[int, ...],
    graph_edges: set[tuple[int, int]],
    max_span: int,
) -> tuple[int, ...] | None:
    boundary_length = len(boundary_vertices)
    best: list[tuple[int, ...] | None] = [None] * (boundary_length + 1)
    best[0] = (0,)
    for end in range(1, boundary_length + 1):
        chosen: tuple[int, ...] | None = None
        for start in range(max(0, end - max_span), end):
            prefix = best[start]
            if prefix is None:
                continue
            left = boundary_vertices[start % boundary_length]
            right = boundary_vertices[end % boundary_length]
            if _canonical_graph_edge(left, right) not in graph_edges:
                continue
            candidate = prefix + (end,)
            candidate_cycle = tuple(
                boundary_vertices[offset] for offset in candidate[:-1]
            )
            chosen_cycle = (
                tuple(boundary_vertices[offset] for offset in chosen[:-1])
                if chosen is not None
                else ()
            )
            if (
                chosen is None
                or len(candidate) > len(chosen)
                or (len(candidate) == len(chosen) and candidate_cycle < chosen_cycle)
            ):
                chosen = candidate
        best[end] = chosen
    result = best[boundary_length]
    if result is None or len(result) - 1 < 3:
        return None
    return result


def _best_boundary_partition(
    *,
    boundary_vertices: tuple[int, ...],
    graph_edges: set[tuple[int, int]],
    max_span: int,
) -> tuple[int, tuple[int, ...]] | None:
    """Search every orientation-preserving cyclic cut of the boundary."""

    boundary_length = len(boundary_vertices)
    chosen: tuple[int, tuple[int, ...], tuple[int, ...]] | None = None
    for start_offset in range(boundary_length):
        rotated = boundary_vertices[start_offset:] + boundary_vertices[:start_offset]
        offsets = _best_linear_boundary_partition(
            boundary_vertices=rotated,
            graph_edges=graph_edges,
            max_span=max_span,
        )
        if offsets is None:
            continue
        cycle_vertices = tuple(rotated[offset] for offset in offsets[:-1])
        candidate = (start_offset, offsets, cycle_vertices)
        if (
            chosen is None
            or len(offsets) > len(chosen[1])
            or (len(offsets) == len(chosen[1]) and cycle_vertices < chosen[2])
            or (
                len(offsets) == len(chosen[1])
                and cycle_vertices == chosen[2]
                and start_offset < chosen[0]
            )
        ):
            chosen = candidate
    if chosen is None:
        return None
    return chosen[0], chosen[1]


def bind_cycle_class(
    graph_receipt: GraphConstructionReceipt,
    cycle_class_spec: BoundaryCycleClassSpec,
    refinement_rule: BoundaryRefinementRule,
) -> CycleClassMatchAttempt:
    """Match a graph cycle by an exact forward partition of the common boundary."""

    _validate_binding_join(
        graph_receipt,
        cycle_class_spec,
        refinement_rule,
    )
    graph_edges = {
        tuple(int(item) for item in edge) for edge in graph_receipt.canonical_edges
    }
    boundary_vertices = tuple(
        int(item) for item in cycle_class_spec.boundary_vertex_rows
    )
    partition = _best_boundary_partition(
        boundary_vertices=boundary_vertices,
        graph_edges=graph_edges,
        max_span=refinement_rule.max_domain_edges_per_graph_edge,
    )
    if partition is None:
        return CycleClassMatchAttempt(
            _factory_token=_ATTEMPT_FACTORY_TOKEN,
            graph_receipt=graph_receipt,
            cycle_class_spec=cycle_class_spec,
            refinement_rule=refinement_rule,
            matched=False,
            reason="cycle-boundary-not-coverable",
            binding=None,
        )
    start_offset, offsets = partition
    offset_array = np.asarray(offsets, dtype="<i8")
    boundary_length = cycle_class_spec.boundary_vertex_rows.shape[0]
    vertex_offsets = (start_offset + offset_array[:-1]) % boundary_length
    vertex_array = cycle_class_spec.boundary_vertex_rows[vertex_offsets]
    arc_array = np.column_stack((offset_array[:-1], offset_array[1:]))
    binding = CycleClassBinding(
        _factory_token=_BINDING_FACTORY_TOKEN,
        graph_receipt=graph_receipt,
        cycle_class_spec=cycle_class_spec,
        refinement_rule=refinement_rule,
        boundary_start_offset=start_offset,
        graph_cycle_vertex_rows=vertex_array,
        lifted_boundary_offsets=offset_array,
        lifted_boundary_arcs=arc_array,
    )
    return CycleClassMatchAttempt(
        _factory_token=_ATTEMPT_FACTORY_TOKEN,
        graph_receipt=graph_receipt,
        cycle_class_spec=cycle_class_spec,
        refinement_rule=refinement_rule,
        matched=True,
        reason="ok",
        binding=binding,
    )
