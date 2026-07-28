from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest

import spirallens.graphs.constructors as graph_constructors
import spirallens.graphs.contracts as graph_contracts
from spirallens.graphs.common import (
    GRAPH_RECORD_SCOPE,
    GraphContractError,
    GraphFamily,
    GraphPurpose,
)
from spirallens.graphs.constructors import (
    construct_mutual_knn,
    construct_radius_graph,
    construct_shared_neighbor_graph,
)
from spirallens.graphs.contracts import (
    GraphConstructionReceipt,
    GraphInput,
    MutualKnnSpec,
    RadiusGraphSpec,
    SharedNeighborSpec,
)
from spirallens.synthetic.representation_phantom import RepresentationPhantom


def _input(states: list[list[float]], vertex_ids: list[int]) -> GraphInput:
    return GraphInput(
        primary_unit_id="constructor-test-unit",
        vertex_ids=np.asarray(vertex_ids, dtype="<i8"),
        states=np.asarray(states, dtype="<f8"),
    )


def test_mutual_knn_uses_frozen_identity_tie_break_and_reciprocity() -> None:
    graph_input = _input(
        [[0.0], [1.0], [-1.0], [3.0]],
        [0, 20, 10, 30],
    )
    receipt = construct_mutual_knn(
        graph_input,
        MutualKnnSpec(
            spec_id="tie-test",
            purpose=GraphPurpose.FIELD_ESTIMATION,
            neighbor_count=1,
        ),
    )

    assert receipt.family_identity.family is GraphFamily.MUTUAL_KNN
    assert receipt.canonical_edges.tolist() == [[0, 2]]
    assert receipt.edge_distances.tolist() == [1.0]
    assert receipt.degree.tolist() == [1, 0, 1, 0]
    assert receipt.component_labels.tolist() == [0, 1, 0, 2]
    assert not np.any(receipt.two_core_mask)


def test_radius_graph_is_inclusive_at_the_declared_radius() -> None:
    receipt = construct_radius_graph(
        _input([[0.0], [1.0], [2.1]], [10, 11, 12]),
        RadiusGraphSpec(
            spec_id="inclusive-radius",
            purpose=GraphPurpose.CYCLE_CONSTRUCTION,
            radius=1.0,
        ),
    )

    assert receipt.canonical_edges.tolist() == [[0, 1]]
    assert receipt.edge_distances.tolist() == [1.0]


def test_shared_neighbor_ranges_over_all_pairs_without_mutual_prerequisite() -> None:
    receipt = construct_shared_neighbor_graph(
        _input([[0.0], [1.0], [2.0]], [0, 1, 2]),
        SharedNeighborSpec(
            spec_id="all-pair-shared-neighbor",
            purpose=GraphPurpose.CYCLE_CONSTRUCTION,
            neighbor_count=1,
            minimum_shared_neighbors=1,
        ),
    )

    # Rows 0 and 2 are not in each other's directed 1-NN sets. They are
    # connected because both directed neighborhoods equal {1}.
    assert receipt.canonical_edges.tolist() == [[0, 2]]
    assert receipt.edge_distances.tolist() == [2.0]


def test_receipt_arrays_are_bytes_backed_and_cannot_be_reenabled() -> None:
    receipt = construct_radius_graph(
        _input([[0.0], [1.0], [2.0]], [0, 1, 2]),
        RadiusGraphSpec(
            spec_id="immutable",
            purpose=GraphPurpose.FIELD_ESTIMATION,
            radius=1.0,
        ),
    )

    for value in (
        receipt.graph_input.vertex_ids,
        receipt.graph_input.states,
        receipt.canonical_edges,
        receipt.edge_distances,
        receipt.component_labels,
        receipt.degree,
        receipt.two_core_mask,
    ):
        assert not value.flags.writeable
        with pytest.raises(ValueError):
            value.setflags(write=True)


def test_receipt_is_factory_only_and_fingerprint_only() -> None:
    graph_input = _input([[0.0], [1.0]], [0, 1])
    specification = RadiusGraphSpec(
        spec_id="factory-only",
        purpose=GraphPurpose.FIELD_ESTIMATION,
        radius=1.0,
    )
    receipt = construct_radius_graph(graph_input, specification)

    assert receipt.to_dict()["record_scope"] == GRAPH_RECORD_SCOPE
    assert receipt.to_dict()["persistence_round_trip_supported"] is False
    assert receipt.to_dict()["qualification_gate_evaluated"] is False
    assert receipt.to_dict()["d0_d8_advanced"] is False
    assert receipt.to_dict()["field_read"] is False
    assert receipt.to_dict()["core_read"] is False
    assert receipt.to_dict()["winding_read"] is False
    assert not hasattr(GraphConstructionReceipt, "from_dict")
    with pytest.raises(GraphContractError, match="must be produced"):
        GraphConstructionReceipt(
            graph_input=graph_input,
            specification=specification,
            family_identity=receipt.family_identity,
            canonical_edges=receipt.canonical_edges,
            edge_distances=receipt.edge_distances,
            component_labels=receipt.component_labels,
            degree=receipt.degree,
            two_core_mask=receipt.two_core_mask,
        )


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        (
            "edge_distances",
            np.array([2.0, 1.0], dtype="<f8"),
            "edge_distances differ",
        ),
        (
            "component_labels",
            np.array([0, 1, 0], dtype="<i8"),
            "component_labels differ",
        ),
        (
            "two_core_mask",
            np.array([True, True, True], dtype="|b1"),
            "two_core_mask differs",
        ),
    ],
)
def test_receipt_recomputes_derived_structure(
    field: str,
    replacement: np.ndarray,
    message: str,
) -> None:
    receipt = construct_radius_graph(
        _input([[0.0], [1.0], [2.0]], [0, 1, 2]),
        RadiusGraphSpec(
            spec_id="derived-audit",
            purpose=GraphPurpose.FIELD_ESTIMATION,
            radius=1.0,
        ),
    )
    values = {
        "graph_input": receipt.graph_input,
        "specification": receipt.specification,
        "family_identity": receipt.family_identity,
        "canonical_edges": receipt.canonical_edges,
        "edge_distances": receipt.edge_distances,
        "component_labels": receipt.component_labels,
        "degree": receipt.degree,
        "two_core_mask": receipt.two_core_mask,
    }
    values[field] = replacement

    with pytest.raises(GraphContractError, match=message):
        GraphConstructionReceipt(
            _factory_token=graph_contracts._GRAPH_RECEIPT_FACTORY_TOKEN,
            **values,  # type: ignore[arg-type]
        )


def test_neighbor_count_fails_before_pairwise_allocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph_input = _input([[0.0], [1.0]], [0, 1])
    pairwise_called = False

    def forbidden_pairwise(_: GraphInput) -> np.ndarray:
        nonlocal pairwise_called
        pairwise_called = True
        raise AssertionError("pairwise allocation must not run")

    monkeypatch.setattr(
        graph_constructors,
        "_pairwise_distances",
        forbidden_pairwise,
    )
    for construct, specification in (
        (
            construct_mutual_knn,
            MutualKnnSpec(
                spec_id="too-many-mutual-neighbors",
                purpose=GraphPurpose.FIELD_ESTIMATION,
                neighbor_count=2,
            ),
        ),
        (
            construct_shared_neighbor_graph,
            SharedNeighborSpec(
                spec_id="too-many-shared-neighbors",
                purpose=GraphPurpose.FIELD_ESTIMATION,
                neighbor_count=2,
                minimum_shared_neighbors=1,
            ),
        ),
    ):
        with pytest.raises(GraphContractError, match="smaller than row_count"):
            construct(graph_input, specification)  # type: ignore[arg-type]
    assert not pairwise_called


def test_radius_comparison_does_not_alias_through_squared_underflow() -> None:
    radius = 1.6e-162
    outside = float(np.nextafter(radius, np.inf))
    receipt = construct_radius_graph(
        _input([[0.0], [outside]], [0, 1]),
        RadiusGraphSpec(
            spec_id="subnormal-square-boundary",
            purpose=GraphPurpose.FIELD_ESTIMATION,
            radius=radius,
        ),
    )

    assert receipt.canonical_edges.shape == (0, 2)


def test_graph_input_resource_preflight_runs_before_pairwise_allocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(graph_contracts, "MAX_GRAPH_ESTIMATED_PEAK_BYTES", 1)

    with pytest.raises(GraphContractError, match="256 MiB cap"):
        _input([[0.0], [1.0]], [0, 1])


def test_high_k_python_working_set_fails_before_pairwise_allocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row_count = 1970
    graph_input = GraphInput(
        primary_unit_id="high-k-resource-unit",
        vertex_ids=np.arange(row_count, dtype="<i8"),
        states=np.zeros((row_count, 1), dtype="<f8"),
    )
    pairwise_called = False

    def forbidden_pairwise(_: GraphInput) -> np.ndarray:
        nonlocal pairwise_called
        pairwise_called = True
        raise AssertionError("pairwise allocation must not run")

    monkeypatch.setattr(
        graph_constructors,
        "_pairwise_distances",
        forbidden_pairwise,
    )
    with pytest.raises(GraphContractError, match="working set exceeds"):
        construct_mutual_knn(
            graph_input,
            MutualKnnSpec(
                spec_id="high-k-resource",
                purpose=GraphPurpose.FIELD_ESTIMATION,
                neighbor_count=row_count - 1,
            ),
        )
    assert not pairwise_called


def test_new_mutual_knn_adjacency_matches_frozen_p1_payload() -> None:
    case = RepresentationPhantom.generate().angular_section_positive
    receipt = construct_mutual_knn(
        GraphInput(
            primary_unit_id="frozen-p1-development-unit",
            vertex_ids=case.vertex_identities,
            states=case.states,
        ),
        MutualKnnSpec(
            spec_id="frozen-p1-equivalence",
            purpose=GraphPurpose.FIELD_ESTIMATION,
            neighbor_count=case.spec.neighbor_count,
        ),
    )

    assert np.array_equal(receipt.canonical_edges, case.edges)
    assert np.allclose(receipt.edge_distances, case.graph_weights, rtol=2e-15, atol=0.0)
    assert np.array_equal(receipt.component_labels, case.components)
    assert np.array_equal(receipt.degree, case.degree)
    assert np.array_equal(receipt.two_core_mask, case.two_core_mask)


def test_frozen_p1_producer_and_protocol_bytes_are_untouched() -> None:
    repository = Path(__file__).resolve().parents[1]
    expected = {
        repository / "src" / "spirallens" / "synthetic" / "representation_phantom.py": (
            "08325f28b87b0a895538a36a8d72a4fa2ef9ad7411d43995451cb36559b28ac3"
        ),
        repository / "protocols" / "p1_representation_phantom_v0_1.yaml": (
            "5d5b754ab7659401f2abf30ef9a0ed32506573c917a33be48725999cd17c3d26"
        ),
    }

    assert {
        path: hashlib.sha256(path.read_bytes()).hexdigest() for path in expected
    } == expected
