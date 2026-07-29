"""Execute the frozen field-graph A × cycle-graph B foundation in memory.

This module joins the standalone PR8 graph/domain primitives to the PR9
qualification protocol.  It checks *actual* adjacency, field-consumption, and
cycle-representative content; graph IDs alone can never satisfy nonvacuity.
No field value, core, phase, oracle outcome, or subject value is used while
constructing either graph axis or the discrete boundary class.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from itertools import combinations
from typing import Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray

from spirallens.core.canonical import canonical_json_sha256
from spirallens.graphs import (
    BOUNDARY_CYCLE_CLASS_SPEC_RECEIPT_VERSION,
    DISCRETE_DOMAIN_RECEIPT_VERSION,
    BoundaryCycleClassSpec,
    BoundaryRefinementRule,
    CycleClassMatchAttempt,
    DiscreteDomainComplex,
    GraphConstructionReceipt,
    GraphDiversityReceipt,
    GraphFamily,
    GraphInput,
    MutualKnnSpec,
    RadiusGraphSpec,
    SharedNeighborSpec,
    bind_cycle_class,
    build_discrete_domain_complex,
    construct_mutual_knn,
    construct_radius_graph,
    construct_shared_neighbor_graph,
    define_boundary_cycle_class,
    measure_graph_diversity,
)
from spirallens.graphs.common import array_fingerprint

from .blind import BlindCoreInput, build_blind_core_input
from .common import (
    QualificationContractError,
    QualificationState,
    fingerprint_mapping,
    level0_boundary,
    require_finite_real,
    require_plain_int,
    require_sha256,
    require_slug,
)
from .protocol import GraphAxes, GraphDeclaration
from .winding import BlindLoopInput, build_blind_loop_input

Int64Array = NDArray[np.int64]

DOMAIN_CONSTRUCTION_ID = "cartesian-oriented-grid-triangle-domain-v0.1"
SUPPORT_CONSTRUCTION_ID = "rectangular-grid-face-support-v0.1"
_SUBSTANTIVE_EFFECT_COMPONENTS = (
    "amplitude",
    "identifiability_score",
    "section_values",
)
_DIAGNOSTIC_EFFECT_COMPONENTS = ("edge_coherence",)
_ALL_EFFECT_COMPONENTS = (
    *_SUBSTANTIVE_EFFECT_COMPONENTS,
    *_DIAGNOSTIC_EFFECT_COMPONENTS,
)
_MINIMUM_CHANGED_SUBSTANTIVE_SCALARS = 2


def domain_construction_sha256() -> str:
    """Return the protocol identity of the graph-independent domain recipe."""

    return canonical_json_sha256(
        {
            "construction_id": DOMAIN_CONSTRUCTION_ID,
            "domain_receipt_version": DISCRETE_DOMAIN_RECEIPT_VERSION,
            "row_order": "cartesian-row-major-y-then-x",
            "cell_triangulation": (
                "lower-left-lower-right-upper-right-then-"
                "lower-left-upper-right-upper-left"
            ),
            "orientation": "counterclockwise",
            "observable_inputs_accepted": False,
        }
    )


def support_construction_sha256() -> str:
    """Return the protocol identity of the rectangular support recipe."""

    return canonical_json_sha256(
        {
            "construction_id": SUPPORT_CONSTRUCTION_ID,
            "boundary_receipt_version": (BOUNDARY_CYCLE_CLASS_SPEC_RECEIPT_VERSION),
            "support": "all-two-triangles-of-each-selected-grid-cell",
            "boundary": "single-induced-counterclockwise-boundary",
            "rectangle_coordinates": "half-open-cell-box",
            "observable_inputs_accepted": False,
        }
    )


@runtime_checkable
class FieldEstimateLike(Protocol):
    """Observable surface required for exact A-axis binding."""

    field_graph: GraphConstructionReceipt
    estimator_input_fingerprint_sha256: str
    field_graph_fingerprint_sha256: str
    field_consumption_sha256: str
    substantive_output_sha256: str
    output_sha256: str
    fingerprint_sha256: str
    section_values: NDArray[np.float64]
    amplitude: NDArray[np.float64]
    identifiability_score: NDArray[np.float64]
    edge_coherence: NDArray[np.float64]
    support_count: NDArray[np.int64]


def construct_declared_graph(
    graph_input: GraphInput,
    declaration: GraphDeclaration,
) -> GraphConstructionReceipt:
    """Construct exactly one protocol-declared graph."""

    if not isinstance(graph_input, GraphInput):
        raise TypeError("graph_input must be a GraphInput")
    if not isinstance(declaration, GraphDeclaration):
        raise TypeError("declaration must be a GraphDeclaration")
    parameters = dict(declaration.parameters)
    if declaration.family is GraphFamily.MUTUAL_KNN:
        return construct_mutual_knn(
            graph_input,
            MutualKnnSpec(
                spec_id=declaration.graph_id,
                purpose=declaration.purpose,
                neighbor_count=int(parameters["neighbor_count"]),
            ),
        )
    if declaration.family is GraphFamily.FIXED_RADIUS:
        return construct_radius_graph(
            graph_input,
            RadiusGraphSpec(
                spec_id=declaration.graph_id,
                purpose=declaration.purpose,
                radius=float(parameters["radius"]),
            ),
        )
    if declaration.family is GraphFamily.SHARED_NEIGHBOR:
        return construct_shared_neighbor_graph(
            graph_input,
            SharedNeighborSpec(
                spec_id=declaration.graph_id,
                purpose=declaration.purpose,
                neighbor_count=int(parameters["neighbor_count"]),
                minimum_shared_neighbors=int(parameters["minimum_shared_neighbors"]),
            ),
        )
    raise AssertionError("GraphFamily is closed")


def rectangular_grid_support_faces(
    *,
    grid_side: object,
    x_min: object,
    y_min: object,
    x_max: object,
    y_max: object,
) -> Int64Array:
    """Return canonical triangle rows for one rectangular cell support."""

    side = require_plain_int(grid_side, label="grid_side", minimum=2)
    x0 = require_plain_int(x_min, label="x_min", minimum=0)
    y0 = require_plain_int(y_min, label="y_min", minimum=0)
    x1 = require_plain_int(x_max, label="x_max", minimum=1)
    y1 = require_plain_int(y_max, label="y_max", minimum=1)
    if not (x0 < x1 < side and y0 < y1 < side):
        raise QualificationContractError(
            "rectangle must contain cells strictly inside the declared grid"
        )
    faces = [
        2 * (y * (side - 1) + x) + triangle
        for y in range(y0, y1)
        for x in range(x0, x1)
        for triangle in (0, 1)
    ]
    result = np.asarray(faces, dtype="<i8")
    backing = result.tobytes(order="C")
    return np.frombuffer(backing, dtype="<i8")


def representative_content_sha256(
    attempt: CycleClassMatchAttempt,
) -> str | None:
    """Fingerprint actual representative rows, not a graph or ID alias."""

    if not isinstance(attempt, CycleClassMatchAttempt):
        raise TypeError("attempt must be a CycleClassMatchAttempt")
    if attempt.binding is None:
        return None
    binding = attempt.binding
    return canonical_json_sha256(
        {
            "domain_version": ("spirallens.cycle-representative-content.v0.1"),
            "graph_cycle_vertex_rows": array_fingerprint(
                binding.graph_cycle_vertex_rows
            ),
            "lifted_boundary_offsets": array_fingerprint(
                binding.lifted_boundary_offsets
            ),
            "lifted_boundary_arcs": array_fingerprint(binding.lifted_boundary_arcs),
        }
    )


@dataclass(frozen=True, slots=True)
class CrossedGraphExecution:
    """One in-memory A/B graph and matched-boundary execution."""

    graph_input: GraphInput
    field_graphs: tuple[
        GraphConstructionReceipt,
        GraphConstructionReceipt,
        GraphConstructionReceipt,
    ]
    cycle_graphs: tuple[
        GraphConstructionReceipt,
        GraphConstructionReceipt,
        GraphConstructionReceipt,
    ]
    field_diversity: GraphDiversityReceipt
    cycle_diversity: GraphDiversityReceipt
    domain: DiscreteDomainComplex
    cycle_class: BoundaryCycleClassSpec
    refinement_rule: BoundaryRefinementRule
    cycle_attempts: tuple[
        CycleClassMatchAttempt,
        CycleClassMatchAttempt,
        CycleClassMatchAttempt,
    ]

    def __post_init__(self) -> None:
        if not isinstance(self.graph_input, GraphInput):
            raise TypeError("graph_input must be a GraphInput")
        if len(self.field_graphs) != 3 or len(self.cycle_graphs) != 3:
            raise QualificationContractError(
                "crossed execution requires exactly three A and three B graphs"
            )
        expected_input = self.graph_input.fingerprint_sha256
        for graph in (*self.field_graphs, *self.cycle_graphs):
            if graph.graph_input.fingerprint_sha256 != expected_input:
                raise QualificationContractError(
                    "every graph must bind the same GraphInput"
                )
        if (
            self.domain.graph_input.fingerprint_sha256 != expected_input
            or self.cycle_class.domain.fingerprint_sha256
            != self.domain.fingerprint_sha256
        ):
            raise QualificationContractError(
                "domain and boundary class must bind the crossed GraphInput"
            )
        expected_cycle_fingerprints = tuple(
            graph.fingerprint_sha256 for graph in self.cycle_graphs
        )
        observed_cycle_fingerprints = tuple(
            attempt.graph_receipt.fingerprint_sha256 for attempt in self.cycle_attempts
        )
        if observed_cycle_fingerprints != expected_cycle_fingerprints:
            raise QualificationContractError(
                "cycle attempts must align with the canonical B axis"
            )

    @property
    def representative_content_digests(self) -> tuple[str, ...]:
        return tuple(
            digest
            for attempt in self.cycle_attempts
            if (digest := representative_content_sha256(attempt)) is not None
        )

    @property
    def fingerprint_sha256(self) -> str:
        return fingerprint_mapping(
            {
                "schema_version": "spirallens.crossed-graph-execution.v0.1",
                **level0_boundary(),
                "graph_input_fingerprint_sha256": (self.graph_input.fingerprint_sha256),
                "field_graph_fingerprints": [
                    graph.fingerprint_sha256 for graph in self.field_graphs
                ],
                "cycle_graph_fingerprints": [
                    graph.fingerprint_sha256 for graph in self.cycle_graphs
                ],
                "field_diversity_fingerprint_sha256": (
                    self.field_diversity.fingerprint_sha256
                ),
                "cycle_diversity_fingerprint_sha256": (
                    self.cycle_diversity.fingerprint_sha256
                ),
                "domain_fingerprint_sha256": self.domain.fingerprint_sha256,
                "cycle_class_fingerprint_sha256": (self.cycle_class.fingerprint_sha256),
                "refinement_rule_fingerprint_sha256": (
                    self.refinement_rule.fingerprint_sha256
                ),
                "cycle_attempt_fingerprints": [
                    attempt.fingerprint_sha256 for attempt in self.cycle_attempts
                ],
                "representative_content_digests": list(
                    self.representative_content_digests
                ),
                "field_read_during_graph_construction": False,
                "core_read_during_graph_construction": False,
                "oracle_read_during_graph_construction": False,
            }
        )


def build_crossed_graph_execution(
    *,
    graph_input: GraphInput,
    graph_axes: GraphAxes,
    oriented_faces: object,
    support_face_indices: object,
    domain_id: str,
    cycle_class_spec_id: str,
    matched_set_id: str,
    refinement_rule: BoundaryRefinementRule,
) -> CrossedGraphExecution:
    """Build all graph/domain objects before any field or oracle is read."""

    if not isinstance(graph_input, GraphInput):
        raise TypeError("graph_input must be a GraphInput")
    if not isinstance(graph_axes, GraphAxes):
        raise TypeError("graph_axes must be GraphAxes")
    if not isinstance(refinement_rule, BoundaryRefinementRule):
        raise TypeError("refinement_rule must be a BoundaryRefinementRule")
    require_slug(domain_id, label="domain_id")
    require_slug(cycle_class_spec_id, label="cycle_class_spec_id")
    require_slug(matched_set_id, label="matched_set_id")

    field_graphs = tuple(
        construct_declared_graph(graph_input, declaration)
        for declaration in graph_axes.field_estimation
    )
    cycle_graphs = tuple(
        construct_declared_graph(graph_input, declaration)
        for declaration in graph_axes.cycle_construction
    )
    domain = build_discrete_domain_complex(
        graph_input,
        oriented_faces,
        domain_id=domain_id,
        primary_unit_id=graph_input.primary_unit_id,
    )
    cycle_class = define_boundary_cycle_class(
        domain,
        support_face_indices,
        cycle_class_spec_id=cycle_class_spec_id,
        primary_unit_id=graph_input.primary_unit_id,
        matched_set_id=matched_set_id,
    )
    attempts = tuple(
        bind_cycle_class(graph, cycle_class, refinement_rule) for graph in cycle_graphs
    )
    return CrossedGraphExecution(
        graph_input=graph_input,
        field_graphs=field_graphs,  # type: ignore[arg-type]
        cycle_graphs=cycle_graphs,  # type: ignore[arg-type]
        field_diversity=measure_graph_diversity(field_graphs),
        cycle_diversity=measure_graph_diversity(cycle_graphs),
        domain=domain,
        cycle_class=cycle_class,
        refinement_rule=refinement_rule,
        cycle_attempts=attempts,  # type: ignore[arg-type]
    )


def build_crossed_blind_loop_input(
    execution: CrossedGraphExecution,
    field_estimate: FieldEstimateLike,
    *,
    cycle_graph_id: str,
    primary_unit_sha256: str,
) -> BlindLoopInput:
    """Slice one exact A field on one exact matched B representative."""

    if not isinstance(execution, CrossedGraphExecution):
        raise TypeError("execution must be a CrossedGraphExecution")
    if not isinstance(field_estimate, FieldEstimateLike):
        raise TypeError("field_estimate must expose the bound field surface")
    require_slug(cycle_graph_id, label="cycle_graph_id")
    matching_field = tuple(
        graph
        for graph in execution.field_graphs
        if graph.fingerprint_sha256 == field_estimate.field_graph_fingerprint_sha256
    )
    if len(matching_field) != 1:
        raise QualificationContractError(
            "field estimate does not bind exactly one A graph in the execution"
        )
    field_graph = matching_field[0]
    if (
        field_estimate.field_graph.fingerprint_sha256 != field_graph.fingerprint_sha256
        or field_graph.graph_input.fingerprint_sha256
        != execution.graph_input.fingerprint_sha256
    ):
        raise QualificationContractError(
            "field estimate A graph differs from the crossed execution"
        )
    matches = tuple(
        (graph, attempt)
        for graph, attempt in zip(
            execution.cycle_graphs,
            execution.cycle_attempts,
            strict=True,
        )
        if graph.specification.spec_id == cycle_graph_id
    )
    if len(matches) != 1:
        raise QualificationContractError(
            "cycle_graph_id must select exactly one B graph"
        )
    cycle_graph, attempt = matches[0]
    if attempt.binding is None:
        raise QualificationContractError(
            "the selected B graph has no matched boundary representative"
        )
    binding = attempt.binding
    positions = np.asarray(binding.graph_cycle_vertex_rows, dtype=np.int64)
    rows = execution.graph_input.vertex_ids[positions]
    section = np.asarray(field_estimate.section_values)[positions]
    amplitude = np.asarray(field_estimate.amplitude)[positions]
    identifiability = np.asarray(field_estimate.identifiability_score)[positions]
    coherence = np.asarray(field_estimate.edge_coherence)[positions]
    representative_digest = representative_content_sha256(attempt)
    if representative_digest is None:  # pragma: no cover - binding checked above
        raise AssertionError("matched binding must have representative content")
    return build_blind_loop_input(
        primary_unit_sha256=primary_unit_sha256,
        estimator_input_fingerprint_sha256=(
            field_estimate.estimator_input_fingerprint_sha256
        ),
        field_graph_fingerprint_sha256=field_graph.fingerprint_sha256,
        field_estimate_fingerprint_sha256=(field_estimate.fingerprint_sha256),
        cycle_graph_fingerprint_sha256=cycle_graph.fingerprint_sha256,
        cycle_binding_fingerprint_sha256=binding.fingerprint_sha256,
        representative_content_sha256=representative_digest,
        ordered_loop_rows=rows,
        section_values=section,
        boundary_amplitude=amplitude,
        boundary_identifiability_score=identifiability,
        boundary_coherence=coherence,
    )


def build_crossed_blind_core_input(
    execution: CrossedGraphExecution,
    field_estimate: FieldEstimateLike,
    *,
    primary_unit_sha256: str,
) -> BlindCoreInput:
    """Build one exact A-bound charge- and direction-blind core input."""

    if not isinstance(execution, CrossedGraphExecution):
        raise TypeError("execution must be a CrossedGraphExecution")
    if not isinstance(field_estimate, FieldEstimateLike):
        raise TypeError("field_estimate must expose the bound field surface")
    matching = tuple(
        graph
        for graph in execution.field_graphs
        if graph.fingerprint_sha256 == field_estimate.field_graph_fingerprint_sha256
    )
    if len(matching) != 1:
        raise QualificationContractError(
            "field estimate does not bind exactly one A graph in the execution"
        )
    field_graph = matching[0]
    if (
        field_estimate.field_graph.fingerprint_sha256 != field_graph.fingerprint_sha256
        or field_graph.graph_input.fingerprint_sha256
        != execution.graph_input.fingerprint_sha256
    ):
        raise QualificationContractError(
            "field estimate A graph differs from the crossed execution"
        )
    row_ids = execution.graph_input.vertex_ids
    edge_positions = field_graph.canonical_edges
    graph_edges = np.column_stack(
        (
            row_ids[edge_positions[:, 0]],
            row_ids[edge_positions[:, 1]],
        )
    )
    graph_edges = np.sort(graph_edges, axis=1)
    graph_edges = graph_edges[np.lexsort((graph_edges[:, 1], graph_edges[:, 0]))]
    return build_blind_core_input(
        primary_unit_sha256=primary_unit_sha256,
        estimator_input_fingerprint_sha256=(
            field_estimate.estimator_input_fingerprint_sha256
        ),
        field_graph_fingerprint_sha256=field_graph.fingerprint_sha256,
        field_estimate_fingerprint_sha256=(field_estimate.fingerprint_sha256),
        row_ids=row_ids,
        section_values=field_estimate.section_values,
        identifiability_score=field_estimate.identifiability_score,
        edge_coherence=field_estimate.edge_coherence,
        support_counts=field_estimate.support_count,
        orientation_resolved=True,
        orientation_preserving=True,
        graph_edges=graph_edges,
    )


@dataclass(frozen=True, slots=True)
class FieldComponentEffectReceipt:
    """Exact numeric effect for one field component in one A-graph pair."""

    component_name: str
    rms_distance: float
    changed_scalar_count: int
    effect_eligible: bool
    minimum_effect_distance: float
    minimum_changed_scalar_count: int
    qualifies: bool

    def __post_init__(self) -> None:
        if self.component_name not in _ALL_EFFECT_COMPONENTS:
            raise QualificationContractError(
                "component_name is outside the closed field-effect vocabulary"
            )
        require_finite_real(
            self.rms_distance,
            label=f"{self.component_name} rms_distance",
            minimum=0.0,
        )
        require_plain_int(
            self.changed_scalar_count,
            label=f"{self.component_name} changed_scalar_count",
            minimum=0,
        )
        if type(self.effect_eligible) is not bool:
            raise TypeError("effect_eligible must be a bool")
        minimum = require_finite_real(
            self.minimum_effect_distance,
            label=f"{self.component_name} minimum_effect_distance",
            minimum=0.0,
            maximum=1.0,
            minimum_inclusive=False,
        )
        minimum_changed = require_plain_int(
            self.minimum_changed_scalar_count,
            label=f"{self.component_name} minimum_changed_scalar_count",
            minimum=2,
        )
        if minimum_changed != _MINIMUM_CHANGED_SUBSTANTIVE_SCALARS:
            raise QualificationContractError(
                "minimum_changed_scalar_count differs from the closed "
                "multi-scalar field-response contract"
            )
        expected_eligible = self.component_name in _SUBSTANTIVE_EFFECT_COMPONENTS
        if self.effect_eligible is not expected_eligible:
            raise QualificationContractError(
                "effect_eligible differs from the closed substantive "
                "component vocabulary"
            )
        expected_qualifies = (
            expected_eligible
            and self.rms_distance >= minimum
            and self.changed_scalar_count >= minimum_changed
        )
        if type(self.qualifies) is not bool or self.qualifies is not expected_qualifies:
            raise QualificationContractError(
                "component qualifies flag differs from its exact measurements"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "spirallens.field-component-effect.v0.1",
            "component_name": self.component_name,
            "rms_distance": self.rms_distance,
            "changed_scalar_count": self.changed_scalar_count,
            "effect_eligible": self.effect_eligible,
            "minimum_effect_distance": self.minimum_effect_distance,
            "minimum_changed_scalar_count": self.minimum_changed_scalar_count,
            "qualifies": self.qualifies,
        }

    @classmethod
    def from_dict(cls, value: object) -> FieldComponentEffectReceipt:
        if not isinstance(value, Mapping) or any(
            not isinstance(key, str) for key in value
        ):
            raise QualificationContractError(
                "field component effect must be a string-keyed mapping"
            )
        document = dict(value)
        expected = {
            "schema_version",
            "component_name",
            "rms_distance",
            "changed_scalar_count",
            "effect_eligible",
            "minimum_effect_distance",
            "minimum_changed_scalar_count",
            "qualifies",
        }
        if set(document) != expected:
            raise QualificationContractError(
                "field component effect fields differ from the exact schema"
            )
        if document["schema_version"] != "spirallens.field-component-effect.v0.1":
            raise QualificationContractError(
                "field component effect schema_version is not supported"
            )
        for name in ("effect_eligible", "qualifies"):
            if type(document[name]) is not bool:
                raise QualificationContractError(
                    f"field component effect {name} must be bool"
                )
        component_name = document["component_name"]
        if not isinstance(component_name, str):
            raise QualificationContractError(
                "field component effect component_name must be a string"
            )
        return cls(
            component_name=component_name,
            rms_distance=require_finite_real(
                document["rms_distance"],
                label="field component rms_distance",
                minimum=0.0,
            ),
            changed_scalar_count=require_plain_int(
                document["changed_scalar_count"],
                label="field component changed_scalar_count",
                minimum=0,
            ),
            effect_eligible=document["effect_eligible"],
            minimum_effect_distance=require_finite_real(
                document["minimum_effect_distance"],
                label="field component minimum_effect_distance",
                minimum=0.0,
                maximum=1.0,
                minimum_inclusive=False,
            ),
            minimum_changed_scalar_count=require_plain_int(
                document["minimum_changed_scalar_count"],
                label="field component minimum_changed_scalar_count",
                minimum=2,
            ),
            qualifies=document["qualifies"],
        )


@dataclass(frozen=True, slots=True)
class FieldGraphPairEffectReceipt:
    """All component effects for one canonical pair of A graphs."""

    left_field_graph_id: str
    right_field_graph_id: str
    left_field_graph_fingerprint_sha256: str
    right_field_graph_fingerprint_sha256: str
    component_effects: tuple[FieldComponentEffectReceipt, ...]
    qualifying_substantive_components: tuple[str, ...]
    substantive_response_pass: bool

    def __post_init__(self) -> None:
        left_id = require_slug(
            self.left_field_graph_id,
            label="left_field_graph_id",
        )
        right_id = require_slug(
            self.right_field_graph_id,
            label="right_field_graph_id",
        )
        if left_id >= right_id:
            raise QualificationContractError(
                "field-graph pair IDs must be distinct and canonical"
            )
        require_sha256(
            self.left_field_graph_fingerprint_sha256,
            label="left_field_graph_fingerprint_sha256",
        )
        require_sha256(
            self.right_field_graph_fingerprint_sha256,
            label="right_field_graph_fingerprint_sha256",
        )
        if (
            type(self.component_effects) is not tuple
            or any(
                not isinstance(item, FieldComponentEffectReceipt)
                for item in self.component_effects
            )
            or tuple(item.component_name for item in self.component_effects)
            != _ALL_EFFECT_COMPONENTS
        ):
            raise QualificationContractError(
                "component_effects must cover the exact canonical component vocabulary"
            )
        expected_components = tuple(
            item.component_name for item in self.component_effects if item.qualifies
        )
        if (
            self.qualifying_substantive_components != expected_components
            or self.qualifying_substantive_components
            != tuple(sorted(set(self.qualifying_substantive_components)))
        ):
            raise QualificationContractError(
                "qualifying_substantive_components differ from exact effects"
            )
        expected_pass = bool(expected_components)
        if (
            type(self.substantive_response_pass) is not bool
            or self.substantive_response_pass is not expected_pass
        ):
            raise QualificationContractError(
                "substantive_response_pass differs from exact component effects"
            )

    @property
    def pair_id(self) -> str:
        return f"{self.left_field_graph_id}--{self.right_field_graph_id}"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "spirallens.field-graph-pair-effect.v0.1",
            "pair_id": self.pair_id,
            "left_field_graph_id": self.left_field_graph_id,
            "right_field_graph_id": self.right_field_graph_id,
            "left_field_graph_fingerprint_sha256": (
                self.left_field_graph_fingerprint_sha256
            ),
            "right_field_graph_fingerprint_sha256": (
                self.right_field_graph_fingerprint_sha256
            ),
            "component_effects": [item.to_dict() for item in self.component_effects],
            "qualifying_substantive_components": list(
                self.qualifying_substantive_components
            ),
            "substantive_response_pass": self.substantive_response_pass,
        }

    @classmethod
    def from_dict(cls, value: object) -> FieldGraphPairEffectReceipt:
        if not isinstance(value, Mapping) or any(
            not isinstance(key, str) for key in value
        ):
            raise QualificationContractError(
                "field graph pair effect must be a string-keyed mapping"
            )
        document = dict(value)
        expected = {
            "schema_version",
            "pair_id",
            "left_field_graph_id",
            "right_field_graph_id",
            "left_field_graph_fingerprint_sha256",
            "right_field_graph_fingerprint_sha256",
            "component_effects",
            "qualifying_substantive_components",
            "substantive_response_pass",
        }
        if set(document) != expected:
            raise QualificationContractError(
                "field graph pair effect fields differ from the exact schema"
            )
        if document["schema_version"] != "spirallens.field-graph-pair-effect.v0.1":
            raise QualificationContractError(
                "field graph pair effect schema_version is not supported"
            )
        component_values = document["component_effects"]
        qualifying_values = document["qualifying_substantive_components"]
        if not isinstance(component_values, list) or not isinstance(
            qualifying_values,
            list,
        ):
            raise QualificationContractError(
                "field graph pair effect arrays must be JSON arrays"
            )
        if type(document["substantive_response_pass"]) is not bool:
            raise QualificationContractError("substantive_response_pass must be bool")
        result = cls(
            left_field_graph_id=require_slug(
                document["left_field_graph_id"],
                label="left_field_graph_id",
            ),
            right_field_graph_id=require_slug(
                document["right_field_graph_id"],
                label="right_field_graph_id",
            ),
            left_field_graph_fingerprint_sha256=require_sha256(
                document["left_field_graph_fingerprint_sha256"],
                label="left_field_graph_fingerprint_sha256",
            ),
            right_field_graph_fingerprint_sha256=require_sha256(
                document["right_field_graph_fingerprint_sha256"],
                label="right_field_graph_fingerprint_sha256",
            ),
            component_effects=tuple(
                FieldComponentEffectReceipt.from_dict(item) for item in component_values
            ),
            qualifying_substantive_components=tuple(
                require_slug(item, label="qualifying substantive component")
                for item in qualifying_values
            ),
            substantive_response_pass=document["substantive_response_pass"],
        )
        if document["pair_id"] != result.pair_id:
            raise QualificationContractError(
                "field graph pair effect pair_id differs from its endpoints"
            )
        return result


def _effect_receipt(
    *,
    component_name: str,
    left: NDArray[np.generic],
    right: NDArray[np.generic],
    minimum_effect_distance: float,
) -> FieldComponentEffectReceipt:
    left_values = np.asarray(left, dtype=np.float64).reshape(-1)
    right_values = np.asarray(right, dtype=np.float64).reshape(-1)
    if left_values.shape != right_values.shape:
        raise QualificationContractError(
            f"{component_name} A-graph outputs have unequal shapes"
        )
    difference = left_values - right_values
    rms_distance = float(np.linalg.norm(difference) / np.sqrt(difference.shape[0]))
    changed_scalar_count = int(np.count_nonzero(left_values != right_values))
    eligible = component_name in _SUBSTANTIVE_EFFECT_COMPONENTS
    return FieldComponentEffectReceipt(
        component_name=component_name,
        rms_distance=rms_distance,
        changed_scalar_count=changed_scalar_count,
        effect_eligible=eligible,
        minimum_effect_distance=minimum_effect_distance,
        minimum_changed_scalar_count=_MINIMUM_CHANGED_SUBSTANTIVE_SCALARS,
        qualifies=(
            eligible
            and rms_distance >= minimum_effect_distance
            and changed_scalar_count >= _MINIMUM_CHANGED_SUBSTANTIVE_SCALARS
        ),
    )


def _pair_effect_receipt(
    *,
    left_graph: GraphConstructionReceipt,
    right_graph: GraphConstructionReceipt,
    left_estimate: FieldEstimateLike,
    right_estimate: FieldEstimateLike,
    minimum_effect_distance: float,
) -> FieldGraphPairEffectReceipt:
    left_id = left_graph.specification.spec_id
    right_id = right_graph.specification.spec_id
    if left_id >= right_id:
        raise QualificationContractError(
            "A-graph effect pairs must be supplied in canonical ID order"
        )
    effects = tuple(
        _effect_receipt(
            component_name=name,
            left=np.asarray(getattr(left_estimate, name)),
            right=np.asarray(getattr(right_estimate, name)),
            minimum_effect_distance=minimum_effect_distance,
        )
        for name in _ALL_EFFECT_COMPONENTS
    )
    qualifying = tuple(item.component_name for item in effects if item.qualifies)
    return FieldGraphPairEffectReceipt(
        left_field_graph_id=left_id,
        right_field_graph_id=right_id,
        left_field_graph_fingerprint_sha256=left_graph.fingerprint_sha256,
        right_field_graph_fingerprint_sha256=right_graph.fingerprint_sha256,
        component_effects=effects,
        qualifying_substantive_components=qualifying,
        substantive_response_pass=bool(qualifying),
    )


@dataclass(frozen=True, slots=True)
class CrossedNonvacuityReceipt:
    """Evidence that both crossed axes changed actual consumed content."""

    state: QualificationState
    substantive_output_variation_required: bool
    field_adjacency_variant_count: int
    cycle_adjacency_variant_count: int
    field_consumption_variant_count: int
    field_output_variant_count: int
    maximum_pairwise_substantive_output_distance: float
    minimum_substantive_output_distance: float
    field_graph_pair_effects: tuple[FieldGraphPairEffectReceipt, ...]
    substantive_response_field_graph_ids: tuple[str, ...]
    substantive_response_field_graph_count: int
    required_substantive_response_field_graph_count: int
    matched_cycle_count: int
    representative_content_variant_count: int
    minimum_representative_content_variants: int
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.state, QualificationState):
            raise TypeError("state must be a QualificationState")
        if type(self.substantive_output_variation_required) is not bool:
            raise TypeError("substantive_output_variation_required must be a bool")
        for name in (
            "field_adjacency_variant_count",
            "cycle_adjacency_variant_count",
            "field_consumption_variant_count",
            "field_output_variant_count",
            "substantive_response_field_graph_count",
            "required_substantive_response_field_graph_count",
            "matched_cycle_count",
            "representative_content_variant_count",
            "minimum_representative_content_variants",
        ):
            require_plain_int(getattr(self, name), label=name, minimum=0)
        require_finite_real(
            self.maximum_pairwise_substantive_output_distance,
            label="maximum_pairwise_substantive_output_distance",
            minimum=0.0,
        )
        require_finite_real(
            self.minimum_substantive_output_distance,
            label="minimum_substantive_output_distance",
            minimum=0.0,
            maximum=1.0,
            minimum_inclusive=False,
        )
        if (
            type(self.field_graph_pair_effects) is not tuple
            or len(self.field_graph_pair_effects) != 3
            or any(
                not isinstance(item, FieldGraphPairEffectReceipt)
                for item in self.field_graph_pair_effects
            )
        ):
            raise QualificationContractError(
                "field_graph_pair_effects must contain the exact three A-graph pairs"
            )
        pair_ids = tuple(item.pair_id for item in self.field_graph_pair_effects)
        if pair_ids != tuple(sorted(set(pair_ids))):
            raise QualificationContractError(
                "field_graph_pair_effects must be unique and canonical"
            )
        graph_ids = tuple(
            sorted(
                {
                    graph_id
                    for item in self.field_graph_pair_effects
                    for graph_id in (
                        item.left_field_graph_id,
                        item.right_field_graph_id,
                    )
                }
            )
        )
        expected_pairs = tuple(
            f"{left}--{right}" for left, right in combinations(graph_ids, 2)
        )
        if len(graph_ids) != 3 or pair_ids != expected_pairs:
            raise QualificationContractError(
                "field_graph_pair_effects do not form the complete three-graph A-axis"
            )
        thresholds = {
            effect.minimum_effect_distance
            for pair in self.field_graph_pair_effects
            for effect in pair.component_effects
        }
        if thresholds != {self.minimum_substantive_output_distance}:
            raise QualificationContractError(
                "pair component thresholds differ from the nonvacuity threshold"
            )
        eligible_distances = tuple(
            effect.rms_distance
            for pair in self.field_graph_pair_effects
            for effect in pair.component_effects
            if effect.effect_eligible
        )
        if self.maximum_pairwise_substantive_output_distance != max(
            eligible_distances, default=0.0
        ):
            raise QualificationContractError(
                "maximum substantive-output distance differs from exact "
                "component effects"
            )
        expected_response_ids = tuple(
            sorted(
                {
                    graph_id
                    for pair in self.field_graph_pair_effects
                    if pair.substantive_response_pass
                    for graph_id in (
                        pair.left_field_graph_id,
                        pair.right_field_graph_id,
                    )
                }
            )
        )
        if self.substantive_response_field_graph_ids != expected_response_ids:
            raise QualificationContractError(
                "substantive response graph IDs differ from exact pair effects"
            )
        if self.substantive_response_field_graph_count != len(expected_response_ids):
            raise QualificationContractError(
                "substantive response graph count differs from exact pair effects"
            )
        if self.required_substantive_response_field_graph_count != 3:
            raise QualificationContractError(
                "the closed A axis requires substantive response coverage for "
                "all three graphs"
            )
        expected_reasons: set[str] = set()
        if self.field_adjacency_variant_count != 3:
            expected_reasons.add("field-adjacency-axis-vacuous")
        if self.cycle_adjacency_variant_count != 3:
            expected_reasons.add("cycle-adjacency-axis-vacuous")
        if self.field_consumption_variant_count < 2:
            expected_reasons.add("field-consumption-axis-vacuous")
        if self.substantive_output_variation_required:
            if self.field_output_variant_count < 2:
                expected_reasons.add("field-output-axis-vacuous")
            if (
                self.maximum_pairwise_substantive_output_distance
                < self.minimum_substantive_output_distance
            ):
                expected_reasons.add("field-output-effect-below-minimum")
            magnitude_only = any(
                effect.effect_eligible
                and effect.rms_distance >= self.minimum_substantive_output_distance
                and not effect.qualifies
                for pair in self.field_graph_pair_effects
                for effect in pair.component_effects
            )
            if (
                magnitude_only
                and self.substantive_response_field_graph_count
                != self.required_substantive_response_field_graph_count
            ):
                expected_reasons.add("field-output-single-scalar-only")
            if (
                self.substantive_response_field_graph_count
                != self.required_substantive_response_field_graph_count
            ):
                expected_reasons.add("field-output-graph-coverage-incomplete")
        if self.matched_cycle_count != 3:
            expected_reasons.add("cycle-boundary-unmatched")
        if (
            self.representative_content_variant_count
            < self.minimum_representative_content_variants
        ):
            expected_reasons.add("representative-content-axis-vacuous")
        expected_reason_codes = tuple(sorted(expected_reasons))
        if self.reason_codes != expected_reason_codes:
            raise QualificationContractError(
                "reason_codes differ from the exact nonvacuity measurements"
            )
        expected_state = (
            QualificationState.PASS
            if not expected_reason_codes
            else QualificationState.INSUFFICIENT
        )
        if self.state is not expected_state:
            raise QualificationContractError(
                "state differs from the exact nonvacuity measurements"
            )
        if self.reason_codes != tuple(sorted(set(self.reason_codes))):
            raise QualificationContractError(
                "reason_codes must be unique and canonical"
            )
        if self.state is QualificationState.PASS and self.reason_codes:
            raise QualificationContractError(
                "passing nonvacuity receipts cannot carry reasons"
            )
        if self.state is not QualificationState.PASS and not self.reason_codes:
            raise QualificationContractError(
                "non-passing nonvacuity receipts require reasons"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "spirallens.crossed-nonvacuity.v0.4",
            **level0_boundary(),
            "state": self.state.value,
            "substantive_output_variation_required": (
                self.substantive_output_variation_required
            ),
            "field_adjacency_variant_count": (self.field_adjacency_variant_count),
            "cycle_adjacency_variant_count": (self.cycle_adjacency_variant_count),
            "field_consumption_variant_count": (self.field_consumption_variant_count),
            "field_output_variant_count": self.field_output_variant_count,
            "substantive_output_distance_metric": (
                "per-component-rms-over-section-amplitude-identifiability-v0.2"
            ),
            "maximum_pairwise_substantive_output_distance": (
                self.maximum_pairwise_substantive_output_distance
            ),
            "minimum_substantive_output_distance": (
                self.minimum_substantive_output_distance
            ),
            "field_graph_pair_effects": [
                item.to_dict() for item in self.field_graph_pair_effects
            ],
            "substantive_response_field_graph_ids": list(
                self.substantive_response_field_graph_ids
            ),
            "substantive_response_field_graph_count": (
                self.substantive_response_field_graph_count
            ),
            "required_substantive_response_field_graph_count": (
                self.required_substantive_response_field_graph_count
            ),
            "matched_cycle_count": self.matched_cycle_count,
            "representative_content_variant_count": (
                self.representative_content_variant_count
            ),
            "minimum_representative_content_variants": (
                self.minimum_representative_content_variants
            ),
            "reason_codes": list(self.reason_codes),
            "id_only_nonvacuity_forbidden": True,
            "field_estimate_to_graph_binding_verified": True,
            "substantive_output_excludes_support_bookkeeping": True,
            "edge_coherence_is_diagnostic_not_effect_eligible": True,
            "single_scalar_effect_is_insufficient": True,
            "every_a_graph_requires_substantive_response": True,
            "graph_cells_are_repeated_measures": True,
        }

    @classmethod
    def from_dict(cls, value: object) -> CrossedNonvacuityReceipt:
        if not isinstance(value, Mapping) or any(
            not isinstance(key, str) for key in value
        ):
            raise QualificationContractError(
                "crossed nonvacuity receipt must be a string-keyed mapping"
            )
        document = dict(value)
        expected = {
            "schema_version",
            *level0_boundary(),
            "state",
            "substantive_output_variation_required",
            "field_adjacency_variant_count",
            "cycle_adjacency_variant_count",
            "field_consumption_variant_count",
            "field_output_variant_count",
            "substantive_output_distance_metric",
            "maximum_pairwise_substantive_output_distance",
            "minimum_substantive_output_distance",
            "field_graph_pair_effects",
            "substantive_response_field_graph_ids",
            "substantive_response_field_graph_count",
            "required_substantive_response_field_graph_count",
            "matched_cycle_count",
            "representative_content_variant_count",
            "minimum_representative_content_variants",
            "reason_codes",
            "id_only_nonvacuity_forbidden",
            "field_estimate_to_graph_binding_verified",
            "substantive_output_excludes_support_bookkeeping",
            "edge_coherence_is_diagnostic_not_effect_eligible",
            "single_scalar_effect_is_insufficient",
            "every_a_graph_requires_substantive_response",
            "graph_cells_are_repeated_measures",
        }
        if set(document) != expected:
            raise QualificationContractError(
                "crossed nonvacuity receipt fields differ from the exact schema"
            )
        if document["schema_version"] != "spirallens.crossed-nonvacuity.v0.4":
            raise QualificationContractError(
                "crossed nonvacuity schema_version is not supported"
            )
        for name, expected_value in level0_boundary().items():
            if document[name] != expected_value:
                raise QualificationContractError(
                    f"crossed nonvacuity {name} differs from the Level-0 boundary"
                )
        if document["substantive_output_distance_metric"] != (
            "per-component-rms-over-section-amplitude-identifiability-v0.2"
        ):
            raise QualificationContractError(
                "crossed nonvacuity effect metric is not supported"
            )
        bool_names = (
            "substantive_output_variation_required",
            "id_only_nonvacuity_forbidden",
            "field_estimate_to_graph_binding_verified",
            "substantive_output_excludes_support_bookkeeping",
            "edge_coherence_is_diagnostic_not_effect_eligible",
            "single_scalar_effect_is_insufficient",
            "every_a_graph_requires_substantive_response",
            "graph_cells_are_repeated_measures",
        )
        for name in bool_names:
            if type(document[name]) is not bool:
                raise QualificationContractError(
                    f"crossed nonvacuity {name} must be bool"
                )
        for name in bool_names[1:]:
            if document[name] is not True:
                raise QualificationContractError(
                    f"crossed nonvacuity {name} must be true"
                )
        pair_values = document["field_graph_pair_effects"]
        response_ids = document["substantive_response_field_graph_ids"]
        reasons = document["reason_codes"]
        if (
            not isinstance(pair_values, list)
            or not isinstance(
                response_ids,
                list,
            )
            or not isinstance(reasons, list)
        ):
            raise QualificationContractError(
                "crossed nonvacuity receipt sequence fields must be JSON arrays"
            )
        try:
            state = QualificationState(document["state"])
        except (TypeError, ValueError) as error:
            raise QualificationContractError(
                "crossed nonvacuity state is invalid"
            ) from error
        return cls(
            state=state,
            substantive_output_variation_required=document[
                "substantive_output_variation_required"
            ],
            field_adjacency_variant_count=require_plain_int(
                document["field_adjacency_variant_count"],
                label="field_adjacency_variant_count",
                minimum=0,
            ),
            cycle_adjacency_variant_count=require_plain_int(
                document["cycle_adjacency_variant_count"],
                label="cycle_adjacency_variant_count",
                minimum=0,
            ),
            field_consumption_variant_count=require_plain_int(
                document["field_consumption_variant_count"],
                label="field_consumption_variant_count",
                minimum=0,
            ),
            field_output_variant_count=require_plain_int(
                document["field_output_variant_count"],
                label="field_output_variant_count",
                minimum=0,
            ),
            maximum_pairwise_substantive_output_distance=require_finite_real(
                document["maximum_pairwise_substantive_output_distance"],
                label="maximum_pairwise_substantive_output_distance",
                minimum=0.0,
            ),
            minimum_substantive_output_distance=require_finite_real(
                document["minimum_substantive_output_distance"],
                label="minimum_substantive_output_distance",
                minimum=0.0,
                maximum=1.0,
                minimum_inclusive=False,
            ),
            field_graph_pair_effects=tuple(
                FieldGraphPairEffectReceipt.from_dict(item) for item in pair_values
            ),
            substantive_response_field_graph_ids=tuple(
                require_slug(item, label="substantive response field graph ID")
                for item in response_ids
            ),
            substantive_response_field_graph_count=require_plain_int(
                document["substantive_response_field_graph_count"],
                label="substantive_response_field_graph_count",
                minimum=0,
            ),
            required_substantive_response_field_graph_count=require_plain_int(
                document["required_substantive_response_field_graph_count"],
                label="required_substantive_response_field_graph_count",
                minimum=0,
            ),
            matched_cycle_count=require_plain_int(
                document["matched_cycle_count"],
                label="matched_cycle_count",
                minimum=0,
            ),
            representative_content_variant_count=require_plain_int(
                document["representative_content_variant_count"],
                label="representative_content_variant_count",
                minimum=0,
            ),
            minimum_representative_content_variants=require_plain_int(
                document["minimum_representative_content_variants"],
                label="minimum_representative_content_variants",
                minimum=2,
            ),
            reason_codes=tuple(
                require_slug(item, label="crossed nonvacuity reason")
                for item in reasons
            ),
        )

    @property
    def fingerprint_sha256(self) -> str:
        return fingerprint_mapping(self.to_dict())


def assess_crossed_nonvacuity(
    execution: CrossedGraphExecution,
    field_estimates: tuple[FieldEstimateLike, ...],
    *,
    minimum_representative_content_variants: object,
    require_substantive_output_variation: object,
    minimum_substantive_output_distance: object = 1e-6,
) -> CrossedNonvacuityReceipt:
    """Assess actual A/B content variation after every A field is estimated."""

    if not isinstance(execution, CrossedGraphExecution):
        raise TypeError("execution must be a CrossedGraphExecution")
    if (
        not isinstance(field_estimates, tuple)
        or len(field_estimates) != len(execution.field_graphs)
        or any(not isinstance(item, FieldEstimateLike) for item in field_estimates)
    ):
        raise QualificationContractError(
            "field_estimates must align with all three A graphs"
        )
    substantive_outputs: set[str] = set()
    consumptions: set[str] = set()
    expected_input = execution.graph_input.fingerprint_sha256
    for index, (graph, estimate) in enumerate(
        zip(execution.field_graphs, field_estimates, strict=True)
    ):
        if (
            estimate.field_graph.fingerprint_sha256 != graph.fingerprint_sha256
            or estimate.field_graph_fingerprint_sha256 != graph.fingerprint_sha256
            or estimate.field_graph.graph_input.fingerprint_sha256 != expected_input
        ):
            raise QualificationContractError(
                f"field estimate {index} is not bound to its exact A graph"
            )
        rows = execution.graph_input.vertex_ids.shape[0]
        arrays = {
            "section_values": (estimate.section_values, (rows, 2)),
            "amplitude": (estimate.amplitude, (rows,)),
            "identifiability_score": (
                estimate.identifiability_score,
                (rows,),
            ),
            "edge_coherence": (estimate.edge_coherence, (rows,)),
            "support_count": (estimate.support_count, (rows,)),
        }
        for name, (value, shape) in arrays.items():
            observed = np.asarray(value)
            if observed.shape != shape or not np.all(np.isfinite(observed)):
                raise QualificationContractError(
                    f"field estimate {index} {name} has invalid content"
                )
        recomputed_consumption = canonical_json_sha256(
            {
                "domain_version": (
                    "spirallens.cartesian-fourier-field-consumption.v0.1"
                ),
                "field_graph_fingerprint_sha256": graph.fingerprint_sha256,
                "canonical_edges": array_fingerprint(graph.canonical_edges),
                "support_count": array_fingerprint(np.asarray(estimate.support_count)),
            }
        )
        if len(estimate.field_consumption_sha256) != 64 or any(
            character not in "0123456789abcdef"
            for character in estimate.field_consumption_sha256
        ):
            raise QualificationContractError(
                f"field estimate {index} has an invalid consumption digest"
            )
        if estimate.field_consumption_sha256 != recomputed_consumption:
            raise QualificationContractError(
                f"field estimate {index} consumption digest is not "
                "reconstructable from the consumed A graph"
            )
        recomputed_substantive = canonical_json_sha256(
            {
                name: array_fingerprint(np.asarray(value))
                for name, value in (
                    ("section_values", estimate.section_values),
                    ("amplitude", estimate.amplitude),
                    (
                        "identifiability_score",
                        estimate.identifiability_score,
                    ),
                    ("edge_coherence", estimate.edge_coherence),
                )
            }
        )
        if estimate.substantive_output_sha256 != recomputed_substantive:
            raise QualificationContractError(
                f"field estimate {index} substantive digest is not "
                "reconstructable from its claim-relevant arrays"
            )
        consumptions.add(recomputed_consumption)
        substantive_outputs.add(recomputed_substantive)
    minimum = require_plain_int(
        minimum_representative_content_variants,
        label="minimum_representative_content_variants",
        minimum=2,
    )
    if type(require_substantive_output_variation) is not bool:
        raise TypeError("require_substantive_output_variation must be a bool")
    minimum_distance = require_finite_real(
        minimum_substantive_output_distance,
        label="minimum_substantive_output_distance",
        minimum=0.0,
        maximum=1.0,
        minimum_inclusive=False,
    )
    graph_estimate_pairs = tuple(
        sorted(
            zip(execution.field_graphs, field_estimates, strict=True),
            key=lambda item: item[0].specification.spec_id,
        )
    )
    pair_effects = tuple(
        _pair_effect_receipt(
            left_graph=left_graph,
            right_graph=right_graph,
            left_estimate=left_estimate,
            right_estimate=right_estimate,
            minimum_effect_distance=minimum_distance,
        )
        for (
            (left_graph, left_estimate),
            (right_graph, right_estimate),
        ) in combinations(graph_estimate_pairs, 2)
    )
    eligible_distances = tuple(
        effect.rms_distance
        for pair in pair_effects
        for effect in pair.component_effects
        if effect.effect_eligible
    )
    maximum_distance = max(eligible_distances, default=0.0)
    response_graph_ids = tuple(
        sorted(
            {
                graph_id
                for pair in pair_effects
                if pair.substantive_response_pass
                for graph_id in (
                    pair.left_field_graph_id,
                    pair.right_field_graph_id,
                )
            }
        )
    )
    field_adjacency = {graph.edge_order_sha256 for graph in execution.field_graphs}
    cycle_adjacency = {graph.edge_order_sha256 for graph in execution.cycle_graphs}
    representative_digests = set(execution.representative_content_digests)
    matched_count = sum(
        attempt.binding is not None for attempt in execution.cycle_attempts
    )
    reasons: set[str] = set()
    if len(field_adjacency) != 3:
        reasons.add("field-adjacency-axis-vacuous")
    if len(cycle_adjacency) != 3:
        reasons.add("cycle-adjacency-axis-vacuous")
    if len(consumptions) < 2:
        reasons.add("field-consumption-axis-vacuous")
    if require_substantive_output_variation and len(substantive_outputs) < 2:
        reasons.add("field-output-axis-vacuous")
    if require_substantive_output_variation and maximum_distance < minimum_distance:
        reasons.add("field-output-effect-below-minimum")
    if require_substantive_output_variation:
        magnitude_only = any(
            effect.effect_eligible
            and effect.rms_distance >= minimum_distance
            and not effect.qualifies
            for pair in pair_effects
            for effect in pair.component_effects
        )
        if magnitude_only and len(response_graph_ids) != 3:
            reasons.add("field-output-single-scalar-only")
        if len(response_graph_ids) != 3:
            reasons.add("field-output-graph-coverage-incomplete")
    if matched_count != 3:
        reasons.add("cycle-boundary-unmatched")
    if len(representative_digests) < minimum:
        reasons.add("representative-content-axis-vacuous")
    state = QualificationState.PASS if not reasons else QualificationState.INSUFFICIENT
    return CrossedNonvacuityReceipt(
        state=state,
        substantive_output_variation_required=(require_substantive_output_variation),
        field_adjacency_variant_count=len(field_adjacency),
        cycle_adjacency_variant_count=len(cycle_adjacency),
        field_consumption_variant_count=len(consumptions),
        field_output_variant_count=len(substantive_outputs),
        maximum_pairwise_substantive_output_distance=maximum_distance,
        minimum_substantive_output_distance=minimum_distance,
        field_graph_pair_effects=pair_effects,
        substantive_response_field_graph_ids=response_graph_ids,
        substantive_response_field_graph_count=len(response_graph_ids),
        required_substantive_response_field_graph_count=3,
        matched_cycle_count=matched_count,
        representative_content_variant_count=len(representative_digests),
        minimum_representative_content_variants=minimum,
        reason_codes=tuple(sorted(reasons)),
    )
