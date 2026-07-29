from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from spirallens.graphs import (
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
from spirallens.synthetic.representation_estimator import (
    RepresentationEstimatorError,
    RepresentationEstimatorInputs,
    build_representation_estimator_inputs,
    estimate_representation_field,
)
from spirallens.synthetic.representation_phantom import (
    RepresentationPhantom,
    RepresentationPhantomSpec,
)


def _phantom() -> RepresentationPhantom:
    return RepresentationPhantom.generate(
        RepresentationPhantomSpec(
            grid_side=7,
            ambient_dimension=12,
            probe_count=8,
            neighbor_count=4,
            nuisance_scale=0.02,
        )
    )


def _inputs(
    phantom: RepresentationPhantom,
    *,
    case_index: int,
) -> RepresentationEstimatorInputs:
    case = phantom.cases[case_index]
    return build_representation_estimator_inputs(
        spec=phantom.spec,
        vertex_ids=case.vertex_identities,
        grid_coordinates=phantom.grid_coordinates,
        states=case.states,
        accounted_response=case.accounted_response,
        valid_mask=case.valid_mask,
    )


def _graph_input(inputs: RepresentationEstimatorInputs) -> GraphInput:
    return GraphInput(
        primary_unit_id=inputs.primary_unit_id,
        vertex_ids=inputs.vertex_ids,
        states=inputs.states,
    )


def _field_graphs(inputs: RepresentationEstimatorInputs):
    graph_input = _graph_input(inputs)
    return (
        construct_mutual_knn(
            graph_input,
            MutualKnnSpec(
                spec_id="field-mutual",
                purpose=GraphPurpose.FIELD_ESTIMATION,
                neighbor_count=4,
            ),
        ),
        construct_radius_graph(
            graph_input,
            RadiusGraphSpec(
                spec_id="field-radius",
                purpose=GraphPurpose.FIELD_ESTIMATION,
                radius=0.34,
            ),
        ),
        construct_shared_neighbor_graph(
            graph_input,
            SharedNeighborSpec(
                spec_id="field-shared",
                purpose=GraphPurpose.FIELD_ESTIMATION,
                neighbor_count=4,
                minimum_shared_neighbors=2,
            ),
        ),
    )


def test_estimator_input_is_label_free_and_content_bound() -> None:
    phantom = _phantom()
    positive = _inputs(phantom, case_index=0)
    fixed_null = _inputs(phantom, case_index=1)

    assert positive.input_id != fixed_null.input_id
    assert positive.primary_unit_id.startswith("representation-unit-")
    assert not hasattr(positive, "case_id")
    assert not hasattr(positive, "case_index")
    assert not hasattr(positive, "center_support_mask")
    assert not hasattr(positive, "charge")
    assert not hasattr(positive, "cycle")
    assert not hasattr(positive, "winding")
    receipt = positive.to_dict()
    assert receipt["truth_present"] is False
    assert receipt["case_label_present"] is False
    assert receipt["center_anchor_present"] is False
    assert receipt["charge_present"] is False
    assert receipt["loop_observable_present"] is False
    assert receipt["persistence_round_trip_supported"] is False
    for array_name in (
        "vertex_ids",
        "grid_coordinates",
        "states",
        "accounted_response",
        "valid_mask",
    ):
        value = getattr(positive, array_name)
        assert value.flags.writeable is False
        with pytest.raises(ValueError):
            value.setflags(write=True)

    with pytest.raises(RepresentationEstimatorError, match="differs"):
        replace(positive, input_id="rpi_" + "0" * 32)


def test_three_field_graphs_are_consumed_and_preserve_the_core_envelope() -> None:
    phantom = _phantom()
    inputs = _inputs(phantom, case_index=0)
    estimates = tuple(
        estimate_representation_field(inputs, graph) for graph in _field_graphs(inputs)
    )

    assert {estimate.field_graph.family_identity.family for estimate in estimates} == {
        GraphFamily.MUTUAL_KNN,
        GraphFamily.FIXED_RADIUS,
        GraphFamily.SHARED_NEIGHBOR,
    }
    assert len({estimate.field_consumption_sha256 for estimate in estimates}) == 3
    assert len({estimate.output_sha256 for estimate in estimates}) >= 2
    for estimate in estimates:
        serialized_before_generic_binding = estimate.to_dict()
        fingerprint_before_generic_binding = estimate.fingerprint_sha256
        assert estimate.estimator_input_fingerprint_sha256 == inputs.fingerprint_sha256
        assert (
            estimate.field_graph_fingerprint_sha256
            == estimate.field_graph.fingerprint_sha256
        )
        assert estimate.to_dict() == serialized_before_generic_binding
        assert estimate.fingerprint_sha256 == fingerprint_before_generic_binding
        assert np.all(estimate.support)
        assert float(np.min(estimate.relative_rank_gap)) > 0.49
        assert float(np.min(estimate.edge_coherence)) > 0.999999999999
        assert int(np.argmin(estimate.amplitude)) == 24
        assert estimate.amplitude[24] < 1e-14
        assert np.min(np.delete(estimate.amplitude, 24)) > 0.3
        assert estimate.to_dict()["integer_output_authorized"] is False
        assert estimate.to_dict()["topology_claimed"] is False
        assert estimate.to_dict()["d0_d8_advanced"] is False


def test_noncontiguous_vertex_ids_are_not_used_as_array_positions() -> None:
    phantom = _phantom()
    case = phantom.cases[0]
    vertex_ids = 10_000 + 101 * np.arange(phantom.spec.row_count, dtype="<i8")
    inputs = build_representation_estimator_inputs(
        spec=phantom.spec,
        vertex_ids=vertex_ids,
        grid_coordinates=phantom.grid_coordinates,
        states=case.states,
        accounted_response=case.accounted_response,
        valid_mask=case.valid_mask,
    )
    graph = _field_graphs(inputs)[0]
    estimate = estimate_representation_field(inputs, graph)

    assert int(np.max(graph.canonical_edges)) < phantom.spec.row_count
    assert not np.isin(graph.canonical_edges, vertex_ids).any()
    assert np.array_equal(estimate.support_count, graph.degree)
    assert (
        estimate.to_dict()["canonical_edge_endpoint_namespace"]
        == "graph-input-row-position"
    )


def test_support_validation_uses_the_same_scale_tolerance_as_estimation() -> None:
    phantom = _phantom()
    case = phantom.cases[0]
    response = np.zeros_like(case.accounted_response)
    probe_angles = (
        2.0
        * np.pi
        * np.arange(phantom.spec.probe_count, dtype="<f8")
        / float(phantom.spec.probe_count)
    )
    response[:, :, 0] = np.cos(probe_angles)[None, :]
    response[:, :, 1] = 1e-7 * np.sin(probe_angles)[None, :]
    inputs = build_representation_estimator_inputs(
        spec=phantom.spec,
        vertex_ids=case.vertex_identities,
        grid_coordinates=phantom.grid_coordinates,
        states=case.states,
        accounted_response=response,
        valid_mask=case.valid_mask,
    )

    estimate = estimate_representation_field(inputs, _field_graphs(inputs)[0])

    assert np.all(estimate.top_three_eigenvalues[:, 1] > 0.0)
    assert not np.any(estimate.support)
    assert np.all(estimate.reason_codes == 3)
    assert (
        estimate.to_dict()["support_rule_id"]
        == "valid-degree-two-lambda2-scale-tolerance-v0.1"
    )


def test_local_frame_gauges_cancel_in_the_projector_lift() -> None:
    phantom = _phantom()
    inputs = _inputs(phantom, case_index=0)
    estimate = estimate_representation_field(
        inputs,
        _field_graphs(inputs)[0],
    )
    angles = np.linspace(0.1, 1.7, phantom.spec.row_count)
    gauges = np.empty((phantom.spec.row_count, 2, 2), dtype="<f8")
    gauges[:, 0, 0] = np.cos(angles)
    gauges[:, 0, 1] = -np.sin(angles)
    gauges[:, 1, 0] = np.sin(angles)
    gauges[:, 1, 1] = np.cos(angles)
    gauges[::5, :, 1] *= -1.0

    transformed_frames = np.einsum(
        "ndi,nij->ndj",
        estimate.local_frames,
        gauges,
        optimize=False,
    )
    transformed_coordinates = np.einsum(
        "nji,nj->ni",
        gauges,
        estimate.local_coordinates,
        optimize=False,
    )
    reconstructed = np.einsum(
        "ndi,ni->nd",
        transformed_frames,
        transformed_coordinates,
        optimize=False,
    )

    assert np.allclose(
        reconstructed,
        estimate.ambient_section,
        rtol=1e-13,
        atol=1e-13,
    )
    assert np.allclose(
        reconstructed @ estimate.reference_frame,
        estimate.section_values,
        rtol=1e-13,
        atol=1e-13,
    )


def test_estimator_rejects_wrong_graph_role_or_input() -> None:
    phantom = _phantom()
    inputs = _inputs(phantom, case_index=0)
    graph_input = _graph_input(inputs)
    cycle_graph = construct_mutual_knn(
        graph_input,
        MutualKnnSpec(
            spec_id="cycle-mutual",
            purpose=GraphPurpose.CYCLE_CONSTRUCTION,
            neighbor_count=4,
        ),
    )
    with pytest.raises(RepresentationEstimatorError, match="field estimation"):
        estimate_representation_field(inputs, cycle_graph)

    changed_graph_input = GraphInput(
        primary_unit_id=inputs.primary_unit_id,
        vertex_ids=inputs.vertex_ids,
        states=inputs.states + np.linspace(0.0, 1e-3, inputs.states.shape[0])[:, None],
    )
    changed_graph = construct_mutual_knn(
        changed_graph_input,
        MutualKnnSpec(
            spec_id="changed-field",
            purpose=GraphPurpose.FIELD_ESTIMATION,
            neighbor_count=4,
        ),
    )
    with pytest.raises(RepresentationEstimatorError, match="does not bind"):
        estimate_representation_field(inputs, changed_graph)


def test_existing_phantom_bytes_are_unchanged_by_the_additive_estimator() -> None:
    phantom = _phantom()

    assert phantom.spec.canonical_sha256 == (
        "17ddd42b828d2111711177ed2f14b90d593aa10074877f09fd2b4099838edc0c"
    )
    assert phantom.canonical_sha256 == (
        "31cf1384d7a677c612039308fb3bc1483ff51aaa7e9fea9483645d409950a9a1"
    )
