#!/usr/bin/env python3
"""Model-free P4 M1 graph-scale transport development prototype.

This is a deterministic Level-0 development instrument.  It constructs only
canonical graphs from synthetic, label-free numerical states and declared
domain-boundary vertex identities.  It does not read a field, model, subject,
core, phase, holonomy, winding, charge, or official P4 input; it does not
prepare a launch or persist an official result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter, deque
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from itertools import product
from pathlib import Path
from typing import Final

import numpy as np

from spirallens.core.canonical import canonical_json_bytes, canonical_json_sha256
from spirallens.graphs import (
    GraphConstructionReceipt,
    GraphContractError,
    GraphFamily,
    GraphInput,
    GraphPurpose,
    MutualKnnSpec,
    RadiusGraphSpec,
    SharedNeighborSpec,
    construct_mutual_knn,
    construct_radius_graph,
    construct_shared_neighbor_graph,
)
from spirallens.graphs.common import coordinate_order_invariant_euclidean_norm


PROTOTYPE_SCHEMA_VERSION: Final = (
    "spirallens.p4-graph-scale-transport-development-report.v0.1"
)
SELECTION_SCHEMA_VERSION: Final = (
    "spirallens.p4-graph-scale-transport-selection-decision.v0.1"
)
EVALUATION_SCHEMA_VERSION: Final = (
    "spirallens.p4-graph-scale-transport-case-evaluation.v0.1"
)
CONFIRMATION_SCHEMA_VERSION: Final = (
    "spirallens.p4-graph-scale-transport-held-out-confirmation.v0.1"
)
PROTOTYPE_ID: Final = "p4-graph-scale-transport-prototype-v0.1"
CLAIM_CEILING: Final = "level_0"
FAMILY_ORDER: Final = (
    GraphFamily.MUTUAL_KNN,
    GraphFamily.FIXED_RADIUS,
    GraphFamily.SHARED_NEIGHBOR,
)
NUISANCE_AXES: Final = (
    "seed",
    "density-warp",
    "noise",
    "sampling-density",
)
_SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_MAX_RATIONAL_COMPONENT = 1_000_000
_SELECTION_FACTORY_TOKEN = object()


class PrototypeContractError(ValueError):
    """Raised when the development-only transport contract is invalid."""


class CaseRole(str, Enum):
    """Pre-observation role of one synthetic nuisance definition."""

    CALIBRATION = "calibration"
    HELD_OUT_CONFIRMATION = "held-out-confirmation"


def _require_plain_int(value: object, *, label: str, minimum: int) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise PrototypeContractError(f"{label} must be an integer")
    result = int(value)
    if result < minimum:
        raise PrototypeContractError(f"{label} must be at least {minimum}")
    return result


def _require_slug(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _SLUG.fullmatch(value) is None:
        raise PrototypeContractError(f"{label} must be a lowercase portable slug")
    return value


@dataclass(frozen=True, slots=True, order=True)
class PositiveRational:
    """Canonical positive rational used for every selector decision."""

    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        numerator = _require_plain_int(
            self.numerator,
            label="rational numerator",
            minimum=1,
        )
        denominator = _require_plain_int(
            self.denominator,
            label="rational denominator",
            minimum=1,
        )
        if numerator > _MAX_RATIONAL_COMPONENT or denominator > _MAX_RATIONAL_COMPONENT:
            raise PrototypeContractError(
                "rational components exceed the fixed development bound"
            )
        if math.gcd(numerator, denominator) != 1:
            raise PrototypeContractError("rational values must be reduced")
        object.__setattr__(self, "numerator", numerator)
        object.__setattr__(self, "denominator", denominator)

    @property
    def fraction(self) -> Fraction:
        return Fraction(self.numerator, self.denominator)

    def ceil_times(self, value: int) -> int:
        integer = _require_plain_int(value, label="ceil input", minimum=0)
        return (self.numerator * integer + self.denominator - 1) // self.denominator

    def to_dict(self) -> dict[str, int]:
        return {
            "numerator": self.numerator,
            "denominator": self.denominator,
        }


@dataclass(frozen=True, slots=True)
class TransportLaw:
    """One all-dimensionless graph parameter-transport law."""

    law_id: str
    neighbor_fraction: PositiveRational
    scale_neighbor_fraction: PositiveRational
    radius_scale_multiplier: PositiveRational
    shared_overlap_fraction: PositiveRational

    def __post_init__(self) -> None:
        _require_slug(self.law_id, label="law_id")
        for name in (
            "neighbor_fraction",
            "scale_neighbor_fraction",
            "radius_scale_multiplier",
            "shared_overlap_fraction",
        ):
            if not isinstance(getattr(self, name), PositiveRational):
                raise TypeError(f"{name} must be a PositiveRational")
        if self.neighbor_fraction.fraction > 1:
            raise PrototypeContractError("neighbor_fraction must not exceed one")
        if self.scale_neighbor_fraction.fraction > 1:
            raise PrototypeContractError("scale_neighbor_fraction must not exceed one")
        if self.shared_overlap_fraction.fraction > 1:
            raise PrototypeContractError("shared_overlap_fraction must not exceed one")

    @property
    def parameter_key(self) -> tuple[int, ...]:
        values = (
            self.neighbor_fraction,
            self.scale_neighbor_fraction,
            self.radius_scale_multiplier,
            self.shared_overlap_fraction,
        )
        return tuple(
            component
            for value in values
            for component in (value.numerator, value.denominator)
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "law_id": self.law_id,
            "neighbor_fraction": self.neighbor_fraction.to_dict(),
            "scale_neighbor_fraction": self.scale_neighbor_fraction.to_dict(),
            "radius_scale_multiplier": self.radius_scale_multiplier.to_dict(),
            "shared_overlap_fraction": self.shared_overlap_fraction.to_dict(),
            "all_parameters_dimensionless": True,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


@dataclass(frozen=True, slots=True)
class TransportedParameters:
    """Concrete graph parameters derived from one law and one GraphInput."""

    row_count: int
    neighbor_count: int
    scale_neighbor_count: int
    local_scale: float
    radius: float
    minimum_shared_neighbors: int

    def to_dict(self) -> dict[str, object]:
        return {
            "row_count": self.row_count,
            "neighbor_count": self.neighbor_count,
            "scale_neighbor_count": self.scale_neighbor_count,
            "local_scale": self.local_scale,
            "local_scale_hex": self.local_scale.hex(),
            "radius": self.radius,
            "radius_hex": self.radius.hex(),
            "minimum_shared_neighbors": self.minimum_shared_neighbors,
            "clipping_rule": "neighbor-min-two-scale-min-one-max-n-minus-one",
            "median_rule": "sorted-float64-middle-or-fsum-middle-pair-over-two",
            "radius_rule": "float64-local-scale-times-rational-float64-ratio",
        }


@dataclass(frozen=True, slots=True)
class NuisanceCase:
    """Label-free numerical input and one predeclared domain boundary."""

    case_id: str
    role: CaseRole
    graph_input: GraphInput
    boundary_vertex_ids: tuple[int, ...]
    nuisance_axes: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        _require_slug(self.case_id, label="case_id")
        if not isinstance(self.role, CaseRole):
            raise TypeError("role must be a CaseRole")
        if not isinstance(self.graph_input, GraphInput):
            raise TypeError("graph_input must be a GraphInput")
        if not isinstance(self.boundary_vertex_ids, tuple):
            raise TypeError("boundary_vertex_ids must be a tuple")
        boundary = tuple(
            _require_plain_int(item, label="boundary vertex id", minimum=0)
            for item in self.boundary_vertex_ids
        )
        if len(boundary) < 4 or len(set(boundary)) != len(boundary):
            raise PrototypeContractError(
                "boundary must contain at least four distinct vertex ids"
            )
        input_ids = {int(item) for item in self.graph_input.vertex_ids.tolist()}
        if not set(boundary).issubset(input_ids):
            raise PrototypeContractError("boundary vertex ids must exist in GraphInput")
        if not isinstance(self.nuisance_axes, tuple) or any(
            not isinstance(item, tuple)
            or len(item) != 2
            or not isinstance(item[0], str)
            or not isinstance(item[1], str)
            for item in self.nuisance_axes
        ):
            raise PrototypeContractError(
                "nuisance_axes must be a tuple of string pairs"
            )
        names = tuple(name for name, _value in self.nuisance_axes)
        if names != NUISANCE_AXES:
            raise PrototypeContractError(
                "nuisance axes must use the exact canonical order"
            )
        object.__setattr__(self, "boundary_vertex_ids", boundary)

    def to_descriptor(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "role": self.role.value,
            "graph_input_fingerprint_sha256": self.graph_input.fingerprint_sha256,
            "vertex_order_sha256": self.graph_input.vertex_order_sha256,
            "state_sha256": self.graph_input.state_sha256,
            "row_count": int(self.graph_input.states.shape[0]),
            "feature_count": int(self.graph_input.states.shape[1]),
            "boundary_vertex_ids": list(self.boundary_vertex_ids),
            "nuisance_axes": dict(self.nuisance_axes),
            "field_read": False,
            "core_read": False,
            "holonomy_read": False,
            "phase_read": False,
            "winding_read": False,
            "subject_outcome_read": False,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return canonical_json_sha256(self.to_descriptor())


@dataclass(frozen=True, slots=True)
class StructuralGates:
    """Development-only dimensionless graph reception gates."""

    minimum_mean_degree: PositiveRational
    maximum_mean_degree: PositiveRational
    minimum_largest_component_fraction: PositiveRational
    minimum_two_core_fraction: PositiveRational
    minimum_cycle_rank: int
    maximum_boundary_hops_per_domain_edge: int
    maximum_edge_count_ratio: PositiveRational
    maximum_largest_component_fraction_spread: PositiveRational
    maximum_two_core_fraction_spread: PositiveRational
    minimum_common_two_core_fraction: PositiveRational
    maximum_pairwise_edge_jaccard: PositiveRational
    target_mean_degree: PositiveRational

    def __post_init__(self) -> None:
        rational_names = (
            "minimum_mean_degree",
            "maximum_mean_degree",
            "minimum_largest_component_fraction",
            "minimum_two_core_fraction",
            "maximum_edge_count_ratio",
            "maximum_largest_component_fraction_spread",
            "maximum_two_core_fraction_spread",
            "minimum_common_two_core_fraction",
            "maximum_pairwise_edge_jaccard",
            "target_mean_degree",
        )
        for name in rational_names:
            if not isinstance(getattr(self, name), PositiveRational):
                raise TypeError(f"{name} must be a PositiveRational")
        if self.minimum_mean_degree.fraction > self.maximum_mean_degree.fraction:
            raise PrototypeContractError("mean-degree gate interval is reversed")
        if self.maximum_edge_count_ratio.fraction < 1:
            raise PrototypeContractError(
                "maximum_edge_count_ratio must be at least one"
            )
        for name in (
            "minimum_largest_component_fraction",
            "minimum_two_core_fraction",
            "maximum_largest_component_fraction_spread",
            "maximum_two_core_fraction_spread",
            "minimum_common_two_core_fraction",
            "maximum_pairwise_edge_jaccard",
        ):
            if getattr(self, name).fraction > 1:
                raise PrototypeContractError(f"{name} must not exceed one")
        object.__setattr__(
            self,
            "minimum_cycle_rank",
            _require_plain_int(
                self.minimum_cycle_rank,
                label="minimum_cycle_rank",
                minimum=1,
            ),
        )
        object.__setattr__(
            self,
            "maximum_boundary_hops_per_domain_edge",
            _require_plain_int(
                self.maximum_boundary_hops_per_domain_edge,
                label="maximum_boundary_hops_per_domain_edge",
                minimum=1,
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "minimum_mean_degree": self.minimum_mean_degree.to_dict(),
            "maximum_mean_degree": self.maximum_mean_degree.to_dict(),
            "minimum_largest_component_fraction": (
                self.minimum_largest_component_fraction.to_dict()
            ),
            "minimum_two_core_fraction": self.minimum_two_core_fraction.to_dict(),
            "minimum_cycle_rank": self.minimum_cycle_rank,
            "maximum_boundary_hops_per_domain_edge": (
                self.maximum_boundary_hops_per_domain_edge
            ),
            "maximum_edge_count_ratio": self.maximum_edge_count_ratio.to_dict(),
            "maximum_largest_component_fraction_spread": (
                self.maximum_largest_component_fraction_spread.to_dict()
            ),
            "maximum_two_core_fraction_spread": (
                self.maximum_two_core_fraction_spread.to_dict()
            ),
            "minimum_common_two_core_fraction": (
                self.minimum_common_two_core_fraction.to_dict()
            ),
            "maximum_pairwise_edge_jaccard": (
                self.maximum_pairwise_edge_jaccard.to_dict()
            ),
            "target_mean_degree": self.target_mean_degree.to_dict(),
            "status": "development-only-not-frozen",
        }


class _TransportInsufficient(RuntimeError):
    pass


def _pairwise_distances(graph_input: GraphInput) -> np.ndarray:
    row_count = graph_input.states.shape[0]
    distances = np.empty((row_count, row_count), dtype="<f8")
    for row in range(row_count):
        values = coordinate_order_invariant_euclidean_norm(
            graph_input.states - graph_input.states[row],
            axis=1,
        )
        if not np.all(np.isfinite(values)):
            raise PrototypeContractError("pairwise distance is nonfinite")
        distances[row] = values
    distances[distances == 0.0] = 0.0
    np.fill_diagonal(distances, np.inf)
    return distances


def derive_transported_parameters(
    law: TransportLaw,
    graph_input: GraphInput,
) -> TransportedParameters:
    """Derive concrete parameters without reading any downstream field."""

    if not isinstance(law, TransportLaw):
        raise TypeError("law must be a TransportLaw")
    if not isinstance(graph_input, GraphInput):
        raise TypeError("graph_input must be a GraphInput")
    row_count = int(graph_input.states.shape[0])
    if row_count < 3:
        raise _TransportInsufficient("fewer-than-three-vertices")
    available = row_count - 1
    neighbor_count = min(
        available,
        max(2, law.neighbor_fraction.ceil_times(available)),
    )
    scale_neighbor_count = min(
        available,
        max(1, law.scale_neighbor_fraction.ceil_times(available)),
    )
    distances = _pairwise_distances(graph_input)
    row_indices = np.arange(row_count, dtype="<i8")
    local_scales = np.empty(row_count, dtype="<f8")
    for row in range(row_count):
        order = np.lexsort(
            (
                row_indices,
                graph_input.vertex_ids,
                distances[row],
            )
        )
        local_scales[row] = distances[row, order[scale_neighbor_count - 1]]
    ordered_scales = np.sort(local_scales, kind="stable")
    middle = row_count // 2
    if row_count % 2:
        local_scale = float(ordered_scales[middle])
    else:
        local_scale = (
            math.fsum(
                (float(ordered_scales[middle - 1]), float(ordered_scales[middle]))
            )
            / 2.0
        )
    if not math.isfinite(local_scale) or local_scale <= 0.0:
        raise _TransportInsufficient("nonpositive-or-nonfinite-local-scale")
    multiplier = (
        law.radius_scale_multiplier.numerator / law.radius_scale_multiplier.denominator
    )
    radius = float(local_scale * multiplier)
    if not math.isfinite(radius) or radius <= 0.0:
        raise _TransportInsufficient("nonpositive-or-nonfinite-radius")
    minimum_shared_neighbors = min(
        neighbor_count,
        max(1, law.shared_overlap_fraction.ceil_times(neighbor_count)),
    )
    return TransportedParameters(
        row_count=row_count,
        neighbor_count=neighbor_count,
        scale_neighbor_count=scale_neighbor_count,
        local_scale=local_scale,
        radius=radius,
        minimum_shared_neighbors=minimum_shared_neighbors,
    )


def _construct_graphs(
    law: TransportLaw,
    graph_input: GraphInput,
    parameters: TransportedParameters,
) -> tuple[
    GraphConstructionReceipt,
    GraphConstructionReceipt,
    GraphConstructionReceipt,
]:
    suffix = law.fingerprint_sha256[:12]
    purpose = GraphPurpose.CYCLE_CONSTRUCTION
    try:
        mutual = construct_mutual_knn(
            graph_input,
            MutualKnnSpec(
                spec_id=f"m1-mutual-{suffix}",
                purpose=purpose,
                neighbor_count=parameters.neighbor_count,
            ),
        )
        radius = construct_radius_graph(
            graph_input,
            RadiusGraphSpec(
                spec_id=f"m1-radius-{suffix}",
                purpose=purpose,
                radius=parameters.radius,
            ),
        )
        shared = construct_shared_neighbor_graph(
            graph_input,
            SharedNeighborSpec(
                spec_id=f"m1-shared-{suffix}",
                purpose=purpose,
                neighbor_count=parameters.neighbor_count,
                minimum_shared_neighbors=parameters.minimum_shared_neighbors,
            ),
        )
    except GraphContractError as error:
        raise PrototypeContractError("canonical graph construction failed") from error
    return mutual, radius, shared


def _canonical_vertex_edges(
    receipt: GraphConstructionReceipt,
) -> frozenset[tuple[int, int]]:
    vertex_ids = receipt.graph_input.vertex_ids
    return frozenset(
        (
            min(int(vertex_ids[left]), int(vertex_ids[right])),
            max(int(vertex_ids[left]), int(vertex_ids[right])),
        )
        for left, right in receipt.canonical_edges.tolist()
    )


def _bounded_shortest_path_length(
    adjacency: dict[int, set[int]],
    start: int,
    end: int,
    *,
    maximum_hops: int,
) -> int | None:
    if start == end:
        return 0
    queue: deque[tuple[int, int]] = deque([(start, 0)])
    visited = {start}
    while queue:
        vertex, distance = queue.popleft()
        if distance >= maximum_hops:
            continue
        for neighbor in sorted(adjacency[vertex]):
            if neighbor == end:
                return distance + 1
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, distance + 1))
    return None


def _boundary_support(
    receipt: GraphConstructionReceipt,
    boundary_vertex_ids: tuple[int, ...],
    *,
    maximum_hops: int,
) -> tuple[bool, tuple[int | None, ...]]:
    adjacency = {
        int(vertex_id): set() for vertex_id in receipt.graph_input.vertex_ids.tolist()
    }
    for left, right in _canonical_vertex_edges(receipt):
        adjacency[left].add(right)
        adjacency[right].add(left)
    lengths = tuple(
        _bounded_shortest_path_length(
            adjacency,
            left,
            right,
            maximum_hops=maximum_hops,
        )
        for left, right in zip(
            boundary_vertex_ids,
            boundary_vertex_ids[1:] + boundary_vertex_ids[:1],
            strict=True,
        )
    )
    return all(length is not None for length in lengths), lengths


@dataclass(frozen=True, slots=True)
class _GraphMetrics:
    family: GraphFamily
    graph_fingerprint_sha256: str
    edge_fingerprint_sha256: str
    vertex_edges: frozenset[tuple[int, int]]
    edge_count: int
    component_count: int
    largest_component_vertex_count: int
    two_core_vertex_ids: frozenset[int]
    cycle_rank: int
    boundary_supported: bool
    boundary_hop_lengths: tuple[int | None, ...]

    @property
    def two_core_vertex_count(self) -> int:
        return len(self.two_core_vertex_ids)

    def to_dict(self, *, row_count: int) -> dict[str, object]:
        return {
            "family": self.family.value,
            "graph_fingerprint_sha256": self.graph_fingerprint_sha256,
            "edge_fingerprint_sha256": self.edge_fingerprint_sha256,
            "edge_count": self.edge_count,
            "mean_degree": _fraction_dict(Fraction(2 * self.edge_count, row_count)),
            "component_count": self.component_count,
            "largest_component_vertex_count": self.largest_component_vertex_count,
            "largest_component_fraction": _fraction_dict(
                Fraction(self.largest_component_vertex_count, row_count)
            ),
            "two_core_vertex_count": self.two_core_vertex_count,
            "two_core_fraction": _fraction_dict(
                Fraction(self.two_core_vertex_count, row_count)
            ),
            "cycle_rank": self.cycle_rank,
            "boundary_supported": self.boundary_supported,
            "boundary_hop_lengths": list(self.boundary_hop_lengths),
        }


def _graph_metrics(
    receipt: GraphConstructionReceipt,
    boundary_vertex_ids: tuple[int, ...],
    *,
    maximum_boundary_hops: int,
) -> _GraphMetrics:
    labels, counts = np.unique(receipt.component_labels, return_counts=True)
    row_count = int(receipt.graph_input.states.shape[0])
    vertex_ids = receipt.graph_input.vertex_ids
    boundary_supported, hop_lengths = _boundary_support(
        receipt,
        boundary_vertex_ids,
        maximum_hops=maximum_boundary_hops,
    )
    edge_count = int(receipt.canonical_edges.shape[0])
    component_count = int(labels.shape[0])
    return _GraphMetrics(
        family=receipt.specification.family,
        graph_fingerprint_sha256=receipt.fingerprint_sha256,
        edge_fingerprint_sha256=receipt.edge_order_sha256,
        vertex_edges=_canonical_vertex_edges(receipt),
        edge_count=edge_count,
        component_count=component_count,
        largest_component_vertex_count=int(np.max(counts)),
        two_core_vertex_ids=frozenset(
            int(vertex_ids[row]) for row in np.flatnonzero(receipt.two_core_mask)
        ),
        cycle_rank=edge_count - row_count + component_count,
        boundary_supported=boundary_supported,
        boundary_hop_lengths=hop_lengths,
    )


def _fraction_dict(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _below(value: Fraction, minimum: PositiveRational) -> bool:
    return value < minimum.fraction


def _above(value: Fraction, maximum: PositiveRational) -> bool:
    return value > maximum.fraction


def _per_graph_reasons(
    metric: _GraphMetrics,
    *,
    row_count: int,
    gates: StructuralGates,
) -> tuple[str, ...]:
    prefix = metric.family.value
    reasons: list[str] = []
    mean_degree = Fraction(2 * metric.edge_count, row_count)
    if _below(mean_degree, gates.minimum_mean_degree):
        reasons.append(f"{prefix}:mean-degree-below-minimum")
    if _above(mean_degree, gates.maximum_mean_degree):
        reasons.append(f"{prefix}:mean-degree-above-maximum")
    if _below(
        Fraction(metric.largest_component_vertex_count, row_count),
        gates.minimum_largest_component_fraction,
    ):
        reasons.append(f"{prefix}:largest-component-below-minimum")
    if _below(
        Fraction(metric.two_core_vertex_count, row_count),
        gates.minimum_two_core_fraction,
    ):
        reasons.append(f"{prefix}:two-core-below-minimum")
    if metric.cycle_rank < gates.minimum_cycle_rank:
        reasons.append(f"{prefix}:cycle-rank-below-minimum")
    if not metric.boundary_supported:
        reasons.append(f"{prefix}:declared-boundary-unsupported")
    return tuple(reasons)


def _pairwise_measurements(
    metrics: tuple[_GraphMetrics, _GraphMetrics, _GraphMetrics],
) -> tuple[tuple[dict[str, object], ...], tuple[str, ...]]:
    records: list[dict[str, object]] = []
    reasons: list[str] = []
    for left_index, right_index in ((0, 1), (0, 2), (1, 2)):
        left = metrics[left_index]
        right = metrics[right_index]
        intersection = len(left.vertex_edges & right.vertex_edges)
        union = len(left.vertex_edges | right.vertex_edges)
        jaccard = Fraction(intersection, union) if union else None
        distinct = left.vertex_edges != right.vertex_edges
        pair_id = f"{left.family.value}-vs-{right.family.value}"
        if not distinct:
            reasons.append(f"{pair_id}:edge-sets-not-distinct")
        records.append(
            {
                "pair_id": pair_id,
                "intersection_count": intersection,
                "union_count": union,
                "edge_sets_distinct": distinct,
                "jaccard": _fraction_dict(jaccard) if jaccard is not None else None,
            }
        )
    return tuple(records), tuple(reasons)


@dataclass(frozen=True, slots=True)
class _CaseEvaluation:
    report: dict[str, object]
    objective: tuple[Fraction, Fraction, Fraction, Fraction]

    @property
    def passed(self) -> bool:
        return self.report["state"] == "pass"


def evaluate_transport_law(
    law: TransportLaw,
    case: NuisanceCase,
    gates: StructuralGates,
) -> _CaseEvaluation:
    """Evaluate one law on one case without downstream scientific reads."""

    if not isinstance(case, NuisanceCase):
        raise TypeError("case must be a NuisanceCase")
    if not isinstance(gates, StructuralGates):
        raise TypeError("gates must be StructuralGates")
    try:
        parameters = derive_transported_parameters(law, case.graph_input)
    except _TransportInsufficient as error:
        report = {
            "schema_version": EVALUATION_SCHEMA_VERSION,
            "state": "insufficient",
            "reason": str(error),
            "rejection_reasons": [str(error)],
            "case": case.to_descriptor(),
            "law": law.to_dict(),
            "law_fingerprint_sha256": law.fingerprint_sha256,
            "transported_parameters": None,
            "graphs": None,
            "triplet": None,
            "field_read": False,
            "core_read": False,
            "holonomy_read": False,
            "phase_read": False,
            "winding_read": False,
            "subject_outcome_read": False,
        }
        worst = Fraction(10**12, 1)
        return _CaseEvaluation(report=report, objective=(worst,) * 4)
    receipts = _construct_graphs(law, case.graph_input, parameters)
    row_count = int(case.graph_input.states.shape[0])
    metrics = tuple(
        _graph_metrics(
            receipt,
            case.boundary_vertex_ids,
            maximum_boundary_hops=(gates.maximum_boundary_hops_per_domain_edge),
        )
        for receipt in receipts
    )
    typed_metrics = (metrics[0], metrics[1], metrics[2])
    reasons = [
        reason
        for metric in typed_metrics
        for reason in _per_graph_reasons(metric, row_count=row_count, gates=gates)
    ]
    pairwise, pair_reasons = _pairwise_measurements(typed_metrics)
    reasons.extend(pair_reasons)
    edge_counts = [metric.edge_count for metric in typed_metrics]
    lcc_counts = [metric.largest_component_vertex_count for metric in typed_metrics]
    core_counts = [metric.two_core_vertex_count for metric in typed_metrics]
    minimum_edges = min(edge_counts)
    edge_ratio = (
        Fraction(max(edge_counts), minimum_edges)
        if minimum_edges
        else Fraction(10**12, 1)
    )
    if minimum_edges == 0 or _above(edge_ratio, gates.maximum_edge_count_ratio):
        reasons.append("triplet:edge-count-ratio-above-maximum")
    lcc_spread = Fraction(max(lcc_counts) - min(lcc_counts), row_count)
    if _above(lcc_spread, gates.maximum_largest_component_fraction_spread):
        reasons.append("triplet:largest-component-spread-above-maximum")
    core_spread = Fraction(max(core_counts) - min(core_counts), row_count)
    if _above(core_spread, gates.maximum_two_core_fraction_spread):
        reasons.append("triplet:two-core-spread-above-maximum")
    common_core = len(
        set.intersection(*(set(metric.two_core_vertex_ids) for metric in typed_metrics))
    )
    common_core_fraction = Fraction(common_core, row_count)
    if _below(common_core_fraction, gates.minimum_common_two_core_fraction):
        reasons.append("triplet:common-two-core-below-minimum")
    for record in pairwise:
        jaccard_document = record["jaccard"]
        if jaccard_document is None:
            reasons.append(f"{record['pair_id']}:jaccard-undefined")
            continue
        assert isinstance(jaccard_document, dict)
        jaccard = Fraction(
            int(jaccard_document["numerator"]),
            int(jaccard_document["denominator"]),
        )
        if _above(jaccard, gates.maximum_pairwise_edge_jaccard):
            reasons.append(f"{record['pair_id']}:jaccard-above-maximum")
    target = gates.target_mean_degree.fraction
    mean_degree_deviation = sum(
        (
            abs(Fraction(2 * metric.edge_count, row_count) - target)
            for metric in typed_metrics
        ),
        start=Fraction(0, 1),
    )
    common_core_deficit = Fraction(row_count - common_core, row_count)
    component_count_sum = Fraction(
        sum(metric.component_count for metric in typed_metrics),
        1,
    )
    objective = (
        edge_ratio,
        mean_degree_deviation,
        common_core_deficit,
        component_count_sum,
    )
    unique_reasons = tuple(sorted(set(reasons)))
    report = {
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "state": "pass" if not unique_reasons else "insufficient",
        "reason": "ok" if not unique_reasons else "structural-gate",
        "rejection_reasons": list(unique_reasons),
        "case": case.to_descriptor(),
        "law": law.to_dict(),
        "law_fingerprint_sha256": law.fingerprint_sha256,
        "transported_parameters": parameters.to_dict(),
        "graphs": [metric.to_dict(row_count=row_count) for metric in typed_metrics],
        "triplet": {
            "edge_count_ratio": _fraction_dict(edge_ratio),
            "largest_component_fraction_spread": _fraction_dict(lcc_spread),
            "two_core_fraction_spread": _fraction_dict(core_spread),
            "common_two_core_vertex_count": common_core,
            "common_two_core_fraction": _fraction_dict(common_core_fraction),
            "pairwise": list(pairwise),
            "lexicographic_case_objective": [
                _fraction_dict(value) for value in objective
            ],
            "jaccard_is_gate_not_objective": True,
        },
        "field_read": False,
        "core_read": False,
        "holonomy_read": False,
        "phase_read": False,
        "winding_read": False,
        "subject_outcome_read": False,
    }
    return _CaseEvaluation(report=report, objective=objective)


@dataclass(frozen=True, slots=True, init=False)
class SelectionDecision:
    """In-memory selector decision; no persistence or execution authority."""

    state: str
    selected_law: TransportLaw | None
    gates: StructuralGates
    report: dict[str, object]
    report_sha256: str

    def __init__(
        self,
        *,
        _factory_token: object = None,
        state: str,
        selected_law: TransportLaw | None,
        gates: StructuralGates,
        report: dict[str, object],
    ) -> None:
        if _factory_token is not _SELECTION_FACTORY_TOKEN:
            raise PrototypeContractError(
                "selection decisions must be produced by select_transport_law"
            )
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "selected_law", selected_law)
        object.__setattr__(self, "gates", gates)
        object.__setattr__(self, "report", report)
        object.__setattr__(self, "report_sha256", canonical_json_sha256(report))

    @property
    def fingerprint_sha256(self) -> str:
        return self.report_sha256


def _worst_case_objective(
    evaluations: tuple[_CaseEvaluation, ...],
) -> tuple[Fraction, Fraction, Fraction, Fraction]:
    return tuple(
        max(evaluation.objective[index] for evaluation in evaluations)
        for index in range(4)
    )  # type: ignore[return-value]


def select_transport_law(
    laws: tuple[TransportLaw, ...],
    calibration_cases: tuple[NuisanceCase, ...],
    gates: StructuralGates,
) -> SelectionDecision:
    """Select exactly one law by a deterministic worst-case objective."""

    if not isinstance(laws, tuple) or not laws:
        raise PrototypeContractError("laws must be a nonempty tuple")
    if any(not isinstance(law, TransportLaw) for law in laws):
        raise TypeError("every law must be a TransportLaw")
    if len({law.law_id for law in laws}) != len(laws):
        raise PrototypeContractError("law ids must be unique")
    if len({law.parameter_key for law in laws}) != len(laws):
        raise PrototypeContractError("law parameterizations must be unique")
    if not isinstance(calibration_cases, tuple) or not calibration_cases:
        raise PrototypeContractError("calibration_cases must be a nonempty tuple")
    if any(not isinstance(case, NuisanceCase) for case in calibration_cases):
        raise TypeError("every calibration case must be a NuisanceCase")
    if any(case.role is not CaseRole.CALIBRATION for case in calibration_cases):
        raise PrototypeContractError("selector may read calibration cases only")
    if len({case.case_id for case in calibration_cases}) != len(calibration_cases):
        raise PrototypeContractError("calibration case ids must be unique")
    if not isinstance(gates, StructuralGates):
        raise TypeError("gates must be StructuralGates")

    ordered_laws = tuple(sorted(laws, key=lambda item: item.parameter_key))
    ordered_cases = tuple(sorted(calibration_cases, key=lambda item: item.case_id))
    decision_records: list[dict[str, object]] = []
    eligible: list[
        tuple[
            tuple[Fraction, Fraction, Fraction, Fraction, tuple[int, ...]],
            TransportLaw,
            tuple[_CaseEvaluation, ...],
        ]
    ] = []
    rejection_counts: Counter[str] = Counter()
    for law in ordered_laws:
        evaluations = tuple(
            evaluate_transport_law(law, case, gates) for case in ordered_cases
        )
        passed = all(evaluation.passed for evaluation in evaluations)
        worst = _worst_case_objective(evaluations)
        for evaluation in evaluations:
            reasons = evaluation.report.get("rejection_reasons", [])
            assert isinstance(reasons, list)
            rejection_counts.update(str(reason) for reason in reasons)
        decision_records.append(
            {
                "law_fingerprint_sha256": law.fingerprint_sha256,
                "eligible_across_all_calibration_nuisances": passed,
                "worst_case_objective": [_fraction_dict(value) for value in worst],
                "case_decisions": [
                    {
                        "case_id": evaluation.report["case"]["case_id"],  # type: ignore[index]
                        "state": evaluation.report["state"],
                        "evaluation_sha256": canonical_json_sha256(evaluation.report),
                    }
                    for evaluation in evaluations
                ],
            }
        )
        if passed:
            eligible.append(((*worst, law.parameter_key), law, evaluations))

    selected_law: TransportLaw | None = None
    selected_evaluations: tuple[_CaseEvaluation, ...] = ()
    selected_worst: tuple[Fraction, Fraction, Fraction, Fraction] | None = None
    if eligible:
        eligible.sort(key=lambda item: item[0])
        _key, selected_law, selected_evaluations = eligible[0]
        selected_worst = _worst_case_objective(selected_evaluations)
    report: dict[str, object] = {
        "schema_version": SELECTION_SCHEMA_VERSION,
        "prototype_id": PROTOTYPE_ID,
        "state": "pass" if selected_law is not None else "insufficient",
        "reason": (
            "ok"
            if selected_law is not None
            else "no-law-passed-every-calibration-nuisance"
        ),
        "selection_rule": (
            "all-calibration-cases-must-pass-then-minimize-coordinatewise-"
            "worst-case-lexicographic-objective"
        ),
        "objective_order": [
            "maximum-edge-count-ratio",
            "maximum-summed-mean-degree-target-deviation",
            "maximum-common-two-core-deficit",
            "maximum-component-count-sum",
            "canonical-law-parameter-key",
        ],
        "candidate_law_count": len(ordered_laws),
        "calibration_case_count": len(ordered_cases),
        "calibration_case_ids": [case.case_id for case in ordered_cases],
        "eligible_law_count": len(eligible),
        "all_candidate_decisions_sha256": canonical_json_sha256(decision_records),
        "rejection_reason_counts": dict(sorted(rejection_counts.items())),
        "selected_law": selected_law.to_dict() if selected_law else None,
        "selected_law_fingerprint_sha256": (
            selected_law.fingerprint_sha256 if selected_law else None
        ),
        "selected_worst_case_objective": (
            [_fraction_dict(value) for value in selected_worst]
            if selected_worst is not None
            else None
        ),
        "selected_calibration_evaluations": [
            evaluation.report for evaluation in selected_evaluations
        ],
        "gates": gates.to_dict(),
        "gates_fingerprint_sha256": canonical_json_sha256(gates.to_dict()),
        "candidate_order_affects_decision": False,
        "calibration_case_order_affects_decision": False,
        "average_case_objective_used": False,
        "held_out_case_read": False,
        "field_read": False,
        "core_read": False,
        "holonomy_read": False,
        "phase_read": False,
        "winding_read": False,
        "subject_outcome_read": False,
        "claim_ceiling": CLAIM_CEILING,
        "scientific_authority": False,
    }
    return SelectionDecision(
        _factory_token=_SELECTION_FACTORY_TOKEN,
        state=str(report["state"]),
        selected_law=selected_law,
        gates=gates,
        report=report,
    )


def confirm_selected_transport_law(
    selection: SelectionDecision,
    held_out_case: NuisanceCase,
    gates: StructuralGates,
) -> dict[str, object]:
    """Apply a selected law once; no candidate set or reselection is accepted."""

    if not isinstance(selection, SelectionDecision):
        raise TypeError("selection must be a SelectionDecision")
    if selection.state != "pass" or selection.selected_law is None:
        raise PrototypeContractError("a passing selection is required")
    if not isinstance(held_out_case, NuisanceCase):
        raise TypeError("held_out_case must be a NuisanceCase")
    if held_out_case.role is not CaseRole.HELD_OUT_CONFIRMATION:
        raise PrototypeContractError("confirmation requires a held-out case")
    if canonical_json_sha256(selection.report) != selection.report_sha256:
        raise PrototypeContractError("selection report changed after construction")
    if selection.report.get("state") != selection.state:
        raise PrototypeContractError("selection state binding is invalid")
    if selection.report.get("selected_law_fingerprint_sha256") != (
        selection.selected_law.fingerprint_sha256
    ):
        raise PrototypeContractError("selected law binding is invalid")
    if selection.gates != gates:
        raise PrototypeContractError(
            "confirmation gates differ from the calibration selection"
        )
    expected_gates_sha256 = canonical_json_sha256(gates.to_dict())
    if selection.report.get("gates_fingerprint_sha256") != expected_gates_sha256:
        raise PrototypeContractError("selection gate binding is invalid")
    evaluation = evaluate_transport_law(selection.selected_law, held_out_case, gates)
    return {
        "schema_version": CONFIRMATION_SCHEMA_VERSION,
        "prototype_id": PROTOTYPE_ID,
        "state": "pass" if evaluation.passed else "insufficient",
        "reason": "ok" if evaluation.passed else "held-out-structural-gate",
        "selection_fingerprint_sha256": selection.fingerprint_sha256,
        "selected_law_fingerprint_sha256": (selection.selected_law.fingerprint_sha256),
        "gates_fingerprint_sha256": expected_gates_sha256,
        "held_out_evaluation": evaluation.report,
        "candidate_set_read": False,
        "selector_rerun": False,
        "threshold_widening": False,
        "field_read": False,
        "core_read": False,
        "holonomy_read": False,
        "phase_read": False,
        "winding_read": False,
        "subject_outcome_read": False,
        "claim_ceiling": CLAIM_CEILING,
        "scientific_authority": False,
    }


def _nonnegative_ratio(numerator: int, denominator: int, *, label: str) -> float:
    value = _require_plain_int(numerator, label=f"{label} numerator", minimum=0)
    divisor = _require_plain_int(
        denominator,
        label=f"{label} denominator",
        minimum=1,
    )
    return value / divisor


def make_grid_nuisance_case(
    *,
    case_id: str,
    role: CaseRole,
    side: int,
    seed: int,
    warp_numerator: int,
    warp_denominator: int,
    noise_numerator: int,
    noise_denominator: int,
) -> NuisanceCase:
    """Create one deterministic synthetic 2-D intervention-domain nuisance."""

    side = _require_plain_int(side, label="side", minimum=3)
    seed = _require_plain_int(seed, label="seed", minimum=0)
    warp = _nonnegative_ratio(
        warp_numerator,
        warp_denominator,
        label="warp",
    )
    noise = _nonnegative_ratio(
        noise_numerator,
        noise_denominator,
        label="noise",
    )
    axis = np.linspace(-1.0, 1.0, side, dtype="<f8")
    domain = np.array([(x, y) for y in axis for x in axis], dtype="<f8")
    warped = domain + warp * np.power(domain, 3)
    row_indices = np.arange(side * side, dtype="<i8")[:, None]
    coordinate_indices = np.arange(2, dtype="<i8")[None, :]
    integer_noise = (
        seed * 104_729 + row_indices * 15_485_863 + coordinate_indices * 32_452_843
    ) % 2_000_003
    signed_noise = (integer_noise.astype("<f8") - 1_000_001.0) / 1_000_001.0
    perturbation = np.asarray(noise * signed_noise, dtype="<f8")
    states = np.asarray(warped + perturbation, dtype="<f8")
    vertex_ids = np.arange(side * side, dtype="<i8") + side * 10_000
    top = [column for column in range(side)]
    right = [row * side + side - 1 for row in range(1, side)]
    bottom = [(side - 1) * side + column for column in range(side - 2, -1, -1)]
    left = [row * side for row in range(side - 2, 0, -1)]
    boundary_rows = tuple(top + right + bottom + left)
    boundary_ids = tuple(int(vertex_ids[row]) for row in boundary_rows)
    return NuisanceCase(
        case_id=case_id,
        role=role,
        graph_input=GraphInput(
            primary_unit_id=case_id,
            vertex_ids=vertex_ids,
            states=states,
        ),
        boundary_vertex_ids=boundary_ids,
        nuisance_axes=(
            ("seed", str(seed)),
            ("density-warp", f"{warp_numerator}/{warp_denominator}"),
            ("noise", f"{noise_numerator}/{noise_denominator}"),
            ("sampling-density", f"{side}x{side}"),
        ),
    )


def development_candidate_laws() -> tuple[TransportLaw, ...]:
    """Return a finite development grid; these values are not a protocol freeze."""

    neighbor_fractions = (
        PositiveRational(1, 8),
        PositiveRational(1, 6),
        PositiveRational(1, 4),
    )
    scale_fractions = (
        PositiveRational(1, 8),
        PositiveRational(1, 6),
    )
    radius_multipliers = (
        PositiveRational(1, 1),
        PositiveRational(3, 2),
        PositiveRational(2, 1),
    )
    overlap_fractions = (
        PositiveRational(1, 4),
        PositiveRational(1, 2),
        PositiveRational(3, 4),
    )
    laws: list[TransportLaw] = []
    for index, values in enumerate(
        product(
            neighbor_fractions,
            scale_fractions,
            radius_multipliers,
            overlap_fractions,
        )
    ):
        neighbor, scale, radius, overlap = values
        laws.append(
            TransportLaw(
                law_id=f"m1-development-law-{index:03d}",
                neighbor_fraction=neighbor,
                scale_neighbor_fraction=scale,
                radius_scale_multiplier=radius,
                shared_overlap_fraction=overlap,
            )
        )
    return tuple(laws)


def development_gates() -> StructuralGates:
    """Return broad plumbing gates; no value is frozen for P4 v0.3."""

    return StructuralGates(
        minimum_mean_degree=PositiveRational(1, 1),
        maximum_mean_degree=PositiveRational(16, 1),
        minimum_largest_component_fraction=PositiveRational(4, 5),
        minimum_two_core_fraction=PositiveRational(1, 2),
        minimum_cycle_rank=1,
        maximum_boundary_hops_per_domain_edge=3,
        maximum_edge_count_ratio=PositiveRational(3, 1),
        maximum_largest_component_fraction_spread=PositiveRational(1, 4),
        maximum_two_core_fraction_spread=PositiveRational(2, 5),
        minimum_common_two_core_fraction=PositiveRational(2, 5),
        maximum_pairwise_edge_jaccard=PositiveRational(49, 50),
        target_mean_degree=PositiveRational(6, 1),
    )


def development_calibration_cases() -> tuple[NuisanceCase, ...]:
    """Vary all four nuisance axes without creating an official input."""

    definitions = (
        ("m1-calibration-a", 5, 11, 0, 1, 0, 1),
        ("m1-calibration-b", 6, 23, 1, 5, 1, 200),
        ("m1-calibration-c", 7, 37, 2, 5, 1, 100),
        ("m1-calibration-d", 6, 41, 1, 2, 3, 200),
    )
    return tuple(
        make_grid_nuisance_case(
            case_id=case_id,
            role=CaseRole.CALIBRATION,
            side=side,
            seed=seed,
            warp_numerator=warp_numerator,
            warp_denominator=warp_denominator,
            noise_numerator=noise_numerator,
            noise_denominator=noise_denominator,
        )
        for (
            case_id,
            side,
            seed,
            warp_numerator,
            warp_denominator,
            noise_numerator,
            noise_denominator,
        ) in definitions
    )


def development_held_out_case() -> NuisanceCase:
    """Return the one synthetic demo holdout, inaccessible to the selector."""

    return make_grid_nuisance_case(
        case_id="m1-held-out-e",
        role=CaseRole.HELD_OUT_CONFIRMATION,
        side=8,
        seed=59,
        warp_numerator=3,
        warp_denominator=5,
        noise_numerator=1,
        noise_denominator=50,
    )


def run_development_demo() -> dict[str, object]:
    """Run the bounded synthetic demonstration in memory and return a report."""

    gates = development_gates()
    selection = select_transport_law(
        development_candidate_laws(),
        development_calibration_cases(),
        gates,
    )
    confirmation = (
        confirm_selected_transport_law(
            selection,
            development_held_out_case(),
            gates,
        )
        if selection.state == "pass"
        else None
    )
    final_state = (
        "pass"
        if confirmation is not None and confirmation["state"] == "pass"
        else "insufficient"
    )
    source_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return {
        "schema_version": PROTOTYPE_SCHEMA_VERSION,
        "prototype_id": PROTOTYPE_ID,
        "state": final_state,
        "reason": (
            "synthetic-plumbing-pass"
            if final_state == "pass"
            else "synthetic-plumbing-insufficient"
        ),
        "implementation": {
            "path": "scripts/prototype_p4_graph_scale_transport_v0_1.py",
            "sha256": source_sha256,
            "single_file_prototype": True,
        },
        "selection": selection.report,
        "held_out_confirmation": confirmation,
        "scope": {
            "model_free": True,
            "synthetic_only": True,
            "in_memory_only": True,
            "official_input": False,
            "protocol_freeze": False,
            "launch_prepared": False,
            "execution_authorized": False,
            "model_accessed": False,
            "network_accessed": False,
            "subject_accessed": False,
            "pythia70_accessed": False,
            "pythia160_accessed": False,
            "field_read": False,
            "core_read": False,
            "holonomy_read": False,
            "phase_read": False,
            "winding_read": False,
        },
        "claim_boundary": {
            "claim_ceiling": CLAIM_CEILING,
            "development_plumbing_only": True,
            "graph_transport_calibrated_for_p4_v03": False,
            "scientific_authority": False,
            "topology_authority": False,
            "semantic_authority": False,
            "publication_authority": False,
            "claim_delta": "none",
            "milestone_credit": "none",
        },
        "nonclaims": [
            "synthetic-plumbing-pass-is-not-p4-v03-qualification",
            "development-grid-values-are-not-frozen-thresholds",
            "no-model-or-subject-result-exists",
            "no-f2-f4-order-parameter-core-holonomy-winding-phase-or-transition-is-evaluated",
            "no-qualified-null-or-scientific-claim-is-created",
        ],
        "dynamic_timestamp_present": False,
        "persistent_artifact_written": False,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the model-free P4 M1 synthetic development prototype."
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="pretty-print the deterministic in-memory development report",
    )
    return parser.parse_args()


def main() -> int:
    arguments = _parse_args()
    report = run_development_demo()
    if arguments.pretty:
        print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    else:
        print(canonical_json_bytes(report).decode("utf-8"))
    return 0 if report["state"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
