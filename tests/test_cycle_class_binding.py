from __future__ import annotations

import numpy as np
import pytest

from spirallens.graphs.common import GraphContractError, GraphFamily, GraphPurpose
from spirallens.graphs.constructors import (
    construct_mutual_knn,
    construct_radius_graph,
    construct_shared_neighbor_graph,
)
from spirallens.graphs.contracts import (
    GraphInput,
    MutualKnnSpec,
    RadiusGraphSpec,
    SharedNeighborSpec,
)
from spirallens.graphs.diversity import measure_graph_diversity
from spirallens.graphs.domain import (
    BoundaryRefinementRule,
    bind_cycle_class,
    build_discrete_domain_complex,
    define_boundary_cycle_class,
)


def _grid_faces(side: int) -> np.ndarray:
    faces: list[tuple[int, int, int]] = []
    for y in range(side - 1):
        for x in range(side - 1):
            lower_left = y * side + x
            lower_right = lower_left + 1
            upper_left = lower_left + side
            upper_right = upper_left + 1
            faces.extend(
                [
                    (lower_left, lower_right, upper_right),
                    (lower_left, upper_right, upper_left),
                ]
            )
    return np.asarray(faces, dtype="<i8")


def _ordinary_grid_input() -> GraphInput:
    return GraphInput(
        primary_unit_id="grid-unit",
        vertex_ids=np.arange(100, 109, dtype="<i8"),
        states=np.array(
            [(float(x), float(y)) for y in range(3) for x in range(3)],
            dtype="<f8",
        ),
    )


def _domain_and_boundary(graph_input: GraphInput):
    domain = build_discrete_domain_complex(
        graph_input,
        _grid_faces(3),
        domain_id="grid-domain",
        primary_unit_id="grid-unit",
    )
    cycle_class = define_boundary_cycle_class(
        domain,
        range(domain.canonical_faces.shape[0]),
        cycle_class_spec_id="outer-boundary",
        primary_unit_id="grid-unit",
        matched_set_id="graph-family-comparison",
    )
    return domain, cycle_class


def test_cycle_class_is_exact_connected_face_support_not_homology() -> None:
    domain, cycle_class = _domain_and_boundary(_ordinary_grid_input())

    assert np.array_equal(
        cycle_class.support_face_indices,
        np.arange(8, dtype="<i8"),
    )
    assert cycle_class.boundary_vertex_rows.tolist() == [0, 1, 2, 5, 8, 7, 6, 3]
    assert cycle_class.induced_boundary_edges.tolist() == [
        [0, 1],
        [1, 2],
        [2, 5],
        [5, 8],
        [8, 7],
        [7, 6],
        [6, 3],
        [3, 0],
    ]
    assert cycle_class.support_face_indices.flags.writeable is False
    assert cycle_class.to_dict()["equivalence_relation_id"] == (
        "same-induced-support-boundary"
    )
    assert cycle_class.to_dict()["same_support_is_generic_homology"] is False
    assert cycle_class.to_dict()["support_called_core"] is False
    assert cycle_class.to_dict()["preobservation_support_seal_verified"] is False
    assert (
        cycle_class.to_dict()["outcome_independent_support_selection_established"]
        is False
    )
    assert cycle_class.domain is domain
    assert not hasattr(type(cycle_class), "from_dict")
    assert not hasattr(cycle_class, "write")


def test_reflection_reverses_the_declared_boundary_orientation() -> None:
    graph_input = _ordinary_grid_input()
    reflected_domain = build_discrete_domain_complex(
        graph_input,
        _grid_faces(3)[:, ::-1],
        domain_id="reflected-grid-domain",
        primary_unit_id="grid-unit",
    )
    reflected_class = define_boundary_cycle_class(
        reflected_domain,
        range(reflected_domain.canonical_faces.shape[0]),
        cycle_class_spec_id="reflected-outer-boundary",
        primary_unit_id="grid-unit",
        matched_set_id="graph-family-comparison",
    )

    assert reflected_class.boundary_vertex_rows.tolist() == [
        0,
        3,
        6,
        7,
        8,
        5,
        2,
        1,
    ]


def test_binding_prefers_maximum_graph_edge_count_then_is_deterministic() -> None:
    graph_input = _ordinary_grid_input()
    _, cycle_class = _domain_and_boundary(graph_input)
    graph = construct_radius_graph(
        graph_input,
        RadiusGraphSpec(
            spec_id="unit-grid-radius",
            purpose=GraphPurpose.CYCLE_CONSTRUCTION,
            radius=1.01,
        ),
    )
    rule = BoundaryRefinementRule(
        rule_id="up-to-two-domain-edges",
        max_domain_edges_per_graph_edge=2,
    )

    first = bind_cycle_class(graph, cycle_class, rule)
    second = bind_cycle_class(graph, cycle_class, rule)

    assert first.matched is True
    assert first.reason == "ok"
    assert first.binding is not None
    assert first.binding.graph_cycle_vertex_rows.tolist() == [
        0,
        1,
        2,
        5,
        8,
        7,
        6,
        3,
    ]
    assert first.binding.lifted_boundary_offsets.tolist() == list(range(9))
    assert first.binding.lifted_boundary_arcs.tolist() == [
        [index, index + 1] for index in range(8)
    ]
    assert first.binding.fingerprint_sha256 == second.binding.fingerprint_sha256
    assert first.primary_unit_id == "grid-unit"
    assert first.matched_set_id == "graph-family-comparison"
    assert first.graph_cell_id == f"graph-cell-{graph.fingerprint_sha256}"
    assert first.graph_spec_id == "unit-grid-radius"
    assert first.binding.primary_unit_id == first.primary_unit_id
    assert first.binding.matched_set_id == first.matched_set_id
    assert first.binding.graph_cell_id == first.graph_cell_id
    assert first.binding.graph_spec_id == first.graph_spec_id
    for array in (
        first.binding.graph_cycle_vertex_rows,
        first.binding.lifted_boundary_offsets,
        first.binding.lifted_boundary_arcs,
    ):
        assert array.flags.writeable is False
        with pytest.raises(ValueError):
            array.setflags(write=True)
    receipt = first.binding.to_dict()
    assert receipt["orientation_relation"] == "same"
    assert receipt["boundary_traversal_multiplicity"] == 1
    assert receipt["graph_family_is_statistical_replicate"] is False
    assert receipt["combinatorial_multiplicity_is_statistical_replication"] is False
    assert receipt["graph_cells_are_repeated_measures"] is True
    assert receipt["mapped_boundary_chain_equals_declared"] is True
    assert receipt["common_boundary_availability_only"] is True
    assert receipt["graph_family_cycle_invariance_evaluated"] is False
    assert receipt["homology_claimed"] is False
    assert receipt["winding_read"] is False
    assert receipt["d0_d8_advanced"] is False


def _coarse_boundary_input() -> GraphInput:
    states = np.array(
        [
            (0.0, 0.0),
            (10.0, 10.0),
            (1.0, 0.0),
            (10.0, 20.0),
            (30.0, 30.0),
            (20.0, 10.0),
            (0.0, 1.0),
            (20.0, 20.0),
            (1.0, 1.0),
        ],
        dtype="<f8",
    )
    return GraphInput(
        primary_unit_id="grid-unit",
        vertex_ids=np.arange(100, 109, dtype="<i8"),
        states=states,
    )


def test_boundary_refinement_can_match_coarse_graph_and_types_nonmatch() -> None:
    graph_input = _coarse_boundary_input()
    _, cycle_class = _domain_and_boundary(graph_input)
    graph = construct_radius_graph(
        graph_input,
        RadiusGraphSpec(
            spec_id="coarse-boundary-radius",
            purpose=GraphPurpose.CYCLE_CONSTRUCTION,
            radius=1.01,
        ),
    )

    unmatched = bind_cycle_class(
        graph,
        cycle_class,
        BoundaryRefinementRule(
            rule_id="direct-boundary-only",
            max_domain_edges_per_graph_edge=1,
        ),
    )
    matched = bind_cycle_class(
        graph,
        cycle_class,
        BoundaryRefinementRule(
            rule_id="two-edge-refinement",
            max_domain_edges_per_graph_edge=2,
        ),
    )

    assert unmatched.matched is False
    assert unmatched.reason == "cycle-boundary-not-coverable"
    assert unmatched.binding is None
    assert unmatched.to_dict()["unmatched_is_measurement_not_gate"] is True
    assert unmatched.to_dict()["qualification_gate_evaluated"] is False
    assert matched.matched is True
    assert matched.binding is not None
    assert matched.binding.graph_cycle_vertex_rows.tolist() == [0, 2, 8, 6]
    assert matched.binding.lifted_boundary_offsets.tolist() == [0, 2, 4, 6, 8]


def test_circular_refinement_searches_across_the_canonical_boundary_cut() -> None:
    states = np.array(
        [
            (10.0, 0.0),
            (0.0, 0.0),
            (20.0, 0.0),
            (0.0, 1.0),
            (100.0, 100.0),
            (1.0, 0.0),
            (30.0, 0.0),
            (1.0, 1.0),
            (40.0, 0.0),
        ],
        dtype="<f8",
    )
    graph_input = GraphInput(
        primary_unit_id="grid-unit",
        vertex_ids=np.arange(100, 109, dtype="<i8"),
        states=states,
    )
    _, cycle_class = _domain_and_boundary(graph_input)
    graph = construct_radius_graph(
        graph_input,
        RadiusGraphSpec(
            spec_id="cross-cut-radius",
            purpose=GraphPurpose.CYCLE_CONSTRUCTION,
            radius=1.01,
        ),
    )

    attempt = bind_cycle_class(
        graph,
        cycle_class,
        BoundaryRefinementRule(
            rule_id="cross-cut-two-edge-refinement",
            max_domain_edges_per_graph_edge=2,
        ),
    )

    assert attempt.matched is True
    assert attempt.binding is not None
    assert attempt.binding.boundary_start_offset == 1
    assert attempt.binding.graph_cycle_vertex_rows.tolist() == [1, 5, 7, 3]
    assert attempt.binding.lifted_boundary_offsets.tolist() == [0, 2, 4, 6, 8]
    assert (
        attempt.binding.to_dict()[
            "mapped_boundary_cycle_is_cyclic_rotation_of_declared"
        ]
        is True
    )


def test_three_families_bind_one_common_boundary_as_repeated_measures() -> None:
    side = 4
    graph_input = GraphInput(
        primary_unit_id="three-family-grid-unit",
        vertex_ids=np.arange(100, 100 + side * side, dtype="<i8"),
        states=np.array(
            [(float(x), float(y)) for y in range(side) for x in range(side)],
            dtype="<f8",
        ),
    )
    domain = build_discrete_domain_complex(
        graph_input,
        _grid_faces(side),
        domain_id="three-family-grid-domain",
        primary_unit_id="three-family-grid-unit",
    )
    cycle_class = define_boundary_cycle_class(
        domain,
        range(domain.canonical_faces.shape[0]),
        cycle_class_spec_id="three-family-outer-boundary",
        primary_unit_id="three-family-grid-unit",
        matched_set_id="three-family-common-boundary",
    )
    graphs = (
        construct_mutual_knn(
            graph_input,
            MutualKnnSpec(
                spec_id="three-family-mutual",
                purpose=GraphPurpose.CYCLE_CONSTRUCTION,
                neighbor_count=4,
            ),
        ),
        construct_radius_graph(
            graph_input,
            RadiusGraphSpec(
                spec_id="three-family-radius",
                purpose=GraphPurpose.CYCLE_CONSTRUCTION,
                radius=1.01,
            ),
        ),
        construct_shared_neighbor_graph(
            graph_input,
            SharedNeighborSpec(
                spec_id="three-family-shared",
                purpose=GraphPurpose.CYCLE_CONSTRUCTION,
                neighbor_count=5,
                minimum_shared_neighbors=1,
            ),
        ),
    )
    diversity = measure_graph_diversity(graphs)
    rule = BoundaryRefinementRule(
        rule_id="three-family-direct-boundary",
        max_domain_edges_per_graph_edge=1,
    )
    attempts = tuple(bind_cycle_class(graph, cycle_class, rule) for graph in graphs)

    assert diversity.adjacency_fingerprints_pairwise_distinct
    assert all(attempt.matched for attempt in attempts)
    bindings = tuple(attempt.binding for attempt in attempts)
    assert all(binding is not None for binding in bindings)
    concrete = tuple(binding for binding in bindings if binding is not None)
    assert {binding.graph_receipt.specification.family for binding in concrete} == {
        GraphFamily.MUTUAL_KNN,
        GraphFamily.FIXED_RADIUS,
        GraphFamily.SHARED_NEIGHBOR,
    }
    assert len({binding.graph_cell_id for binding in concrete}) == 3
    assert len({binding.representative_id for binding in concrete}) == 3
    assert len({binding.content_equivalence_group_id for binding in concrete}) == 1
    assert {binding.primary_unit_id for binding in concrete} == {
        "three-family-grid-unit"
    }
    assert {binding.matched_set_id for binding in concrete} == {
        "three-family-common-boundary"
    }
    assert all(
        binding.to_dict()["graph_cells_are_repeated_measures"] is True
        for binding in concrete
    )
    assert all(
        binding.to_dict()["graph_family_cycle_invariance_evaluated"] is False
        for binding in concrete
    )


def test_content_equivalence_ignores_declaration_and_domain_labels() -> None:
    graph_input = _ordinary_grid_input()
    first_domain = build_discrete_domain_complex(
        graph_input,
        _grid_faces(3),
        domain_id="content-copy-domain-a",
        primary_unit_id="grid-unit",
    )
    second_domain = build_discrete_domain_complex(
        graph_input,
        _grid_faces(3),
        domain_id="content-copy-domain-b",
        primary_unit_id="grid-unit",
    )
    first_class = define_boundary_cycle_class(
        first_domain,
        range(first_domain.canonical_faces.shape[0]),
        cycle_class_spec_id="content-copy-a",
        primary_unit_id="grid-unit",
        matched_set_id="content-copy-set-a",
    )
    second_class = define_boundary_cycle_class(
        second_domain,
        range(second_domain.canonical_faces.shape[0]),
        cycle_class_spec_id="content-copy-b",
        primary_unit_id="grid-unit",
        matched_set_id="content-copy-set-b",
    )
    graph = construct_radius_graph(
        graph_input,
        RadiusGraphSpec(
            spec_id="content-copy-radius",
            purpose=GraphPurpose.CYCLE_CONSTRUCTION,
            radius=1.01,
        ),
    )
    rule = BoundaryRefinementRule(
        rule_id="content-copy-direct",
        max_domain_edges_per_graph_edge=1,
    )
    first = bind_cycle_class(graph, first_class, rule)
    second = bind_cycle_class(graph, second_class, rule)

    assert first.binding is not None
    assert second.binding is not None
    assert first_domain.fingerprint_sha256 != second_domain.fingerprint_sha256
    assert first_class.fingerprint_sha256 != second_class.fingerprint_sha256
    assert first.binding.representative_id != second.binding.representative_id
    assert (
        first.binding.content_equivalence_sha256
        == second.binding.content_equivalence_sha256
    )
    assert (
        first.binding.content_equivalence_group_id
        == second.binding.content_equivalence_group_id
    )


def test_cycle_class_rejects_disconnected_support_and_multiple_boundaries() -> None:
    graph_input = GraphInput(
        primary_unit_id="large-grid-unit",
        vertex_ids=np.arange(16, dtype="<i8"),
        states=np.array(
            [(float(x), float(y)) for y in range(4) for x in range(4)],
            dtype="<f8",
        ),
    )
    domain = build_discrete_domain_complex(
        graph_input,
        _grid_faces(4),
        domain_id="large-grid-domain",
        primary_unit_id="large-grid-unit",
    )
    with pytest.raises(GraphContractError, match="edge-connected"):
        define_boundary_cycle_class(
            domain,
            [0, 17],
            cycle_class_spec_id="disconnected-support",
            primary_unit_id="large-grid-unit",
            matched_set_id="invalid-comparison",
        )

    center_faces = {
        index
        for index, face in enumerate(domain.canonical_faces)
        if {int(item) for item in face} == {5, 6, 10}
        or {int(item) for item in face} == {5, 9, 10}
    }
    annulus_support = [
        index
        for index in range(domain.canonical_faces.shape[0])
        if index not in center_faces
    ]
    assert len(center_faces) == 2
    with pytest.raises(GraphContractError, match="multiple|simple"):
        define_boundary_cycle_class(
            domain,
            annulus_support,
            cycle_class_spec_id="annulus-support",
            primary_unit_id="large-grid-unit",
            matched_set_id="invalid-comparison",
        )


def test_binding_rejects_different_graph_input_fingerprint() -> None:
    graph_input = _ordinary_grid_input()
    _, cycle_class = _domain_and_boundary(graph_input)
    different_input = GraphInput(
        primary_unit_id="grid-unit",
        vertex_ids=graph_input.vertex_ids,
        states=graph_input.states + np.array([0.0, 0.25], dtype="<f8"),
    )
    graph = construct_radius_graph(
        different_input,
        RadiusGraphSpec(
            spec_id="different-input-radius",
            purpose=GraphPurpose.CYCLE_CONSTRUCTION,
            radius=1.01,
        ),
    )

    with pytest.raises(GraphContractError, match="different GraphInput"):
        bind_cycle_class(
            graph,
            cycle_class,
            BoundaryRefinementRule(
                rule_id="direct-boundary-only",
                max_domain_edges_per_graph_edge=1,
            ),
        )


def test_binding_rejects_graph_not_predeclared_for_cycle_construction() -> None:
    graph_input = _ordinary_grid_input()
    _, cycle_class = _domain_and_boundary(graph_input)
    field_graph = construct_radius_graph(
        graph_input,
        RadiusGraphSpec(
            spec_id="field-only-radius",
            purpose=GraphPurpose.FIELD_ESTIMATION,
            radius=1.01,
        ),
    )

    with pytest.raises(GraphContractError, match="cycle-construction"):
        bind_cycle_class(
            field_graph,
            cycle_class,
            BoundaryRefinementRule(
                rule_id="direct-boundary-only",
                max_domain_edges_per_graph_edge=1,
            ),
        )


def test_cycle_class_validates_identifiers_support_and_rule() -> None:
    domain, _ = _domain_and_boundary(_ordinary_grid_input())
    with pytest.raises(GraphContractError, match="primary_unit_id"):
        define_boundary_cycle_class(
            domain,
            [0],
            cycle_class_spec_id="wrong-unit",
            primary_unit_id="another-unit",
            matched_set_id="invalid-comparison",
        )
    with pytest.raises(GraphContractError, match="unique"):
        define_boundary_cycle_class(
            domain,
            [0, 0],
            cycle_class_spec_id="duplicate-support",
            primary_unit_id="grid-unit",
            matched_set_id="invalid-comparison",
        )
    for invalid_support in ([0.9], [True], ["1"]):
        with pytest.raises(GraphContractError, match="must be an integer"):
            define_boundary_cycle_class(
                domain,
                invalid_support,
                cycle_class_spec_id="lossy-support",
                primary_unit_id="grid-unit",
                matched_set_id="invalid-comparison",
            )
    with pytest.raises(GraphContractError, match="at least 1"):
        BoundaryRefinementRule(
            rule_id="invalid-rule",
            max_domain_edges_per_graph_edge=0,
        )
