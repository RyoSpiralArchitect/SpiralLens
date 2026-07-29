from __future__ import annotations

import numpy as np
import pytest

from spirallens.graphs import (
    GraphInput,
    GraphPurpose,
    MutualKnnSpec,
    RadiusGraphSpec,
    construct_mutual_knn,
    construct_radius_graph,
)
from spirallens.synthetic.cartesian_fourier_domain_phantom import (
    CartesianFourierDomainGenerator,
    CartesianFourierDomainSpec,
)
from spirallens.synthetic.cartesian_fourier_estimator import (
    CartesianFourierEstimatorError,
    CartesianFourierFieldEstimate,
    estimate_cartesian_fourier_field,
)


def _inputs():
    phantom = CartesianFourierDomainGenerator().generate(
        CartesianFourierDomainSpec(grid_side=7)
    )
    return phantom.positive.estimator_inputs


def _graph(inputs, *, radius: bool = False):
    graph_input = GraphInput(
        primary_unit_id="cartesian-fourier-unit",
        vertex_ids=inputs.row_ids,
        states=inputs.states,
    )
    if radius:
        return construct_radius_graph(
            graph_input,
            RadiusGraphSpec(
                spec_id="field-radius",
                purpose=GraphPurpose.FIELD_ESTIMATION,
                radius=0.42,
            ),
        )
    return construct_mutual_knn(
        graph_input,
        MutualKnnSpec(
            spec_id="field-mutual",
            purpose=GraphPurpose.FIELD_ESTIMATION,
            neighbor_count=4,
        ),
    )


def test_estimator_recovers_label_free_positive_section() -> None:
    inputs = _inputs()
    estimate = estimate_cartesian_fourier_field(inputs, _graph(inputs))
    assert estimate.section_values.shape == (49, 2)
    assert estimate.amplitude[24] == pytest.approx(0.0, abs=1e-14)
    assert np.max(estimate.split_disagreement) < 1e-12
    assert estimate.edge_coherence[24] == 0.0
    assert np.min(np.delete(estimate.edge_coherence, 24)) > 0.9
    assert estimate.to_dict()["truth_read"] is False
    assert estimate.to_dict()["integer_output_authorized"] is False


def test_field_graph_changes_claim_relevant_coherence_not_only_metadata() -> None:
    inputs = _inputs()
    mutual = estimate_cartesian_fourier_field(inputs, _graph(inputs))
    radius = estimate_cartesian_fourier_field(
        inputs,
        _graph(inputs, radius=True),
    )
    assert not np.array_equal(mutual.section_values, radius.section_values)
    assert np.array_equal(mutual.amplitude, radius.amplitude)
    assert mutual.field_consumption_sha256 != radius.field_consumption_sha256
    assert not np.array_equal(mutual.support_count, radius.support_count)
    assert not np.array_equal(mutual.edge_coherence, radius.edge_coherence)
    assert mutual.substantive_output_sha256 != radius.substantive_output_sha256
    assert mutual.output_sha256 != radius.output_sha256


def test_estimate_is_factory_only_and_input_bound() -> None:
    inputs = _inputs()
    graph = _graph(inputs)
    with pytest.raises(
        CartesianFourierEstimatorError,
        match="factory-produced",
    ):
        CartesianFourierFieldEstimate(
            estimator_inputs=inputs,
            field_graph=graph,
            fit_section_values=np.zeros((49, 2), dtype=np.float64),
            section_values=np.zeros((49, 2), dtype=np.float64),
            second_harmonic_values=np.zeros((49, 2), dtype=np.float64),
            amplitude=np.zeros(49, dtype=np.float64),
            first_harmonic_dominance_ratio=np.zeros(
                49,
                dtype=np.float64,
            ),
            edge_coherence=np.ones(49, dtype=np.float64),
            split_disagreement=np.zeros(49, dtype=np.float64),
            support_count=np.zeros(49, dtype=np.int64),
            support=np.zeros(49, dtype=np.bool_),
        )

    foreign = GraphInput(
        primary_unit_id="foreign-fourier-unit",
        vertex_ids=inputs.row_ids,
        states=np.asarray(inputs.states + 0.01, dtype=np.float64),
    )
    foreign_graph = construct_mutual_knn(
        foreign,
        MutualKnnSpec(
            spec_id="foreign-field",
            purpose=GraphPurpose.FIELD_ESTIMATION,
            neighbor_count=4,
        ),
    )
    with pytest.raises(CartesianFourierEstimatorError, match="does not bind"):
        estimate_cartesian_fourier_field(inputs, foreign_graph)


def test_wrong_graph_purpose_is_rejected() -> None:
    inputs = _inputs()
    graph_input = GraphInput(
        primary_unit_id="cartesian-fourier-unit",
        vertex_ids=inputs.row_ids,
        states=inputs.states,
    )
    graph = construct_mutual_knn(
        graph_input,
        MutualKnnSpec(
            spec_id="cycle-mutual",
            purpose=GraphPurpose.CYCLE_CONSTRUCTION,
            neighbor_count=4,
        ),
    )
    with pytest.raises(CartesianFourierEstimatorError, match="does not bind"):
        estimate_cartesian_fourier_field(inputs, graph)
