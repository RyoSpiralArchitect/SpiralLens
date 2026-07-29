from __future__ import annotations

import hashlib
import inspect
import math
from dataclasses import fields, replace
from pathlib import Path

import numpy as np
import pytest

import spirallens.synthetic.spectral_moment_confirmation as confirmation_module
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
    CartesianFourierEstimatorInputs,
)
from spirallens.synthetic.cartesian_fourier_estimator import (
    CartesianFourierFieldEstimate,
    estimate_cartesian_fourier_field,
)
from spirallens.synthetic.generators import (
    GeneratorProtocol,
    require_distinct_construction_families,
)
from spirallens.synthetic.spectral_moment_confirmation import (
    SPECTRAL_MOMENT_CONSTRUCTION_FAMILY_ID,
    SPECTRAL_MOMENT_GENERATOR_FAMILY_ID,
    SPECTRAL_MOMENT_IMPLEMENTATION_ID,
    SPECTRAL_MOMENT_IMPLEMENTATION_VERSION,
    SPECTRAL_MOMENT_REQUIRED_CASE_SEMANTICS,
    SPECTRAL_MOMENT_STATE_NORMALIZATION_SCALE,
    SpectralMomentConfirmationGenerator,
    SpectralMomentConfirmationSpec,
)

# This is deliberately a local development value, not a library default or a
# frozen D7 confirmation seed.
_DEVELOPMENT_SEED = 9001


def _spec(
    seed: int = _DEVELOPMENT_SEED,
    *,
    warp: float = 0.0,
    perturbation: float = 0.0,
) -> SpectralMomentConfirmationSpec:
    return SpectralMomentConfirmationSpec(
        seed=seed,
        state_geometry_warp_strength=warp,
        structured_observation_perturbation_scale=perturbation,
    )


def _bundle(
    seed: int = _DEVELOPMENT_SEED,
    *,
    warp: float = 0.0,
    perturbation: float = 0.0,
):
    return SpectralMomentConfirmationGenerator().generate(
        _spec(
            seed,
            warp=warp,
            perturbation=perturbation,
        )
    )


def test_generator_is_deterministic_and_source_bound() -> None:
    first = _bundle()
    second = _bundle()
    source_path = Path(inspect.getfile(SpectralMomentConfirmationGenerator))

    assert first.receipt_bytes == second.receipt_bytes
    assert first.receipt_sha256 == second.receipt_sha256
    assert (
        first.family_identity.source_sha256
        == hashlib.sha256(source_path.read_bytes()).hexdigest()
    )
    assert isinstance(SpectralMomentConfirmationGenerator(), GeneratorProtocol)


def test_declared_family_ids_differ_and_seed_is_not_family_identity() -> None:
    generator = SpectralMomentConfirmationGenerator()
    cartesian = CartesianFourierDomainGenerator().family_identity
    first = generator.generate(_spec(11))
    second = generator.generate(_spec(12))

    require_distinct_construction_families((cartesian, generator.family_identity))
    assert first.family_identity == second.family_identity
    assert first.family_identity.family_id == SPECTRAL_MOMENT_GENERATOR_FAMILY_ID
    assert (
        first.family_identity.construction_family_id
        == SPECTRAL_MOMENT_CONSTRUCTION_FAMILY_ID
    )
    assert first.family_identity.implementation_id == SPECTRAL_MOMENT_IMPLEMENTATION_ID
    assert (
        first.family_identity.implementation_version
        == SPECTRAL_MOMENT_IMPLEMENTATION_VERSION
    )
    assert first.family_identity.construction_family_id != (
        cartesian.construction_family_id
    )
    assert not np.array_equal(
        first.positive.estimator_inputs.evaluation_values,
        second.positive.estimator_inputs.evaluation_values,
    )
    source = Path(inspect.getfile(SpectralMomentConfirmationGenerator)).read_text(
        encoding="utf-8"
    )
    assert "CartesianFourierDomainGenerator" not in source
    assert "CartesianFourierDomainSpec" not in source


def test_spec_requires_an_explicit_non_confirmation_seed() -> None:
    parameters = inspect.signature(SpectralMomentConfirmationSpec).parameters
    for name in (
        "seed",
        "state_geometry_warp_strength",
        "structured_observation_perturbation_scale",
    ):
        assert parameters[name].default is inspect.Parameter.empty

    with pytest.raises(TypeError, match="seed must be an integer"):
        _spec(seed=True)
    with pytest.raises(ValueError, match="non-negative"):
        _spec(seed=-1)
    with pytest.raises(ValueError, match="state_geometry_warp_strength"):
        _spec(warp=-0.1)
    with pytest.raises(ValueError, match="structured_observation"):
        _spec(perturbation=0.11)

    receipt = _spec().to_dict()
    assert receipt["confirmation_seed_frozen_by_this_source"] is False
    assert receipt["stress_values_are_caller_supplied"] is True
    assert receipt["stress_values_frozen_by_this_source"] is False


@pytest.mark.parametrize(
    ("warp", "perturbation"),
    (
        (0.0, 0.0),
        (0.1, 0.0),
        (0.0, 0.01),
        (0.1, 0.01),
    ),
)
def test_exact_stress_combinations_are_deterministic(
    warp: float,
    perturbation: float,
) -> None:
    first = _bundle(warp=warp, perturbation=perturbation)
    second = _bundle(warp=warp, perturbation=perturbation)

    assert first.receipt_bytes == second.receipt_bytes
    assert first.receipt_sha256 == second.receipt_sha256
    for first_case, second_case in zip(first.cases, second.cases, strict=True):
        assert np.array_equal(
            first_case.estimator_inputs.states,
            second_case.estimator_inputs.states,
        )
        assert np.array_equal(
            first_case.estimator_inputs.fit_values,
            second_case.estimator_inputs.fit_values,
        )
        assert np.array_equal(
            first_case.estimator_inputs.evaluation_values,
            second_case.estimator_inputs.evaluation_values,
        )


def test_state_geometry_warp_changes_states_only() -> None:
    nominal = _bundle(warp=0.0, perturbation=0.0)
    stressed = _bundle(warp=0.1, perturbation=0.0)

    assert not np.array_equal(nominal.domain.states, stressed.domain.states)
    assert np.array_equal(
        nominal.domain.site_coordinates,
        stressed.domain.site_coordinates,
    )
    assert np.array_equal(
        nominal.domain.oriented_faces,
        stressed.domain.oriented_faces,
    )
    for nominal_case, stressed_case in zip(
        nominal.cases,
        stressed.cases,
        strict=True,
    ):
        nominal_inputs = nominal_case.estimator_inputs
        stressed_inputs = stressed_case.estimator_inputs
        assert not np.array_equal(nominal_inputs.states, stressed_inputs.states)
        assert np.array_equal(
            nominal_inputs.site_coordinates,
            stressed_inputs.site_coordinates,
        )
        assert np.array_equal(
            nominal_inputs.oriented_faces,
            stressed_inputs.oriented_faces,
        )
        assert np.array_equal(
            nominal_inputs.fit_values,
            stressed_inputs.fit_values,
        )
        assert np.array_equal(
            nominal_inputs.evaluation_values,
            stressed_inputs.evaluation_values,
        )
        assert np.array_equal(
            nominal_case.oracle_truth.first_moment_field,
            stressed_case.oracle_truth.first_moment_field,
        )
        assert np.array_equal(
            nominal_case.oracle_truth.second_moment_field,
            stressed_case.oracle_truth.second_moment_field,
        )


def test_structured_perturbation_changes_observed_values_only() -> None:
    nominal = _bundle(warp=0.0, perturbation=0.0)
    stressed = _bundle(warp=0.0, perturbation=0.01)
    rows = np.arange(49, dtype=np.int64)
    row_phase = 2.0 * np.pi * ((37 * rows + (_DEVELOPMENT_SEED % 1009)) % 1009) / 1009.0

    assert np.array_equal(nominal.domain.states, stressed.domain.states)
    assert np.array_equal(
        nominal.domain.site_coordinates,
        stressed.domain.site_coordinates,
    )
    for nominal_case, stressed_case in zip(
        nominal.cases,
        stressed.cases,
        strict=True,
    ):
        nominal_inputs = nominal_case.estimator_inputs
        stressed_inputs = stressed_case.estimator_inputs
        assert np.array_equal(nominal_inputs.states, stressed_inputs.states)
        assert np.array_equal(
            nominal_inputs.site_coordinates,
            stressed_inputs.site_coordinates,
        )
        assert np.array_equal(
            nominal_case.oracle_truth.first_moment_field,
            stressed_case.oracle_truth.first_moment_field,
        )
        assert np.array_equal(
            nominal_case.oracle_truth.second_moment_field,
            stressed_case.oracle_truth.second_moment_field,
        )
        for split in ("fit", "evaluation"):
            angles = getattr(nominal_inputs, f"{split}_angles_rad")
            nominal_values = getattr(nominal_inputs, f"{split}_values")
            stressed_values = getattr(stressed_inputs, f"{split}_values")
            if stressed_case is stressed.prerequisite_failure:
                assert np.array_equal(nominal_values, stressed_values)
                continue
            expected_delta = 0.01 * np.cos(
                math.sqrt(2.0) * angles[None, :] + row_phase[:, None]
            )
            np.testing.assert_allclose(
                stressed_values - nominal_values,
                expected_delta,
                rtol=0.0,
                atol=5e-16,
            )


def test_prerequisite_perturbation_suppression_is_receipted() -> None:
    nominal = _bundle(perturbation=0.0).prerequisite_failure
    stressed_bundle = _bundle(perturbation=0.01)
    stressed = stressed_bundle.prerequisite_failure
    receipt = stressed.to_dict()

    assert receipt["requested_structured_observation_perturbation_scale"] == 0.01
    assert receipt["effective_structured_observation_perturbation_scale"] == 0.0
    assert receipt["prerequisite_perturbation_suppression_applied"] is True
    assert np.array_equal(
        nominal.estimator_inputs.fit_values,
        stressed.estimator_inputs.fit_values,
    )
    assert np.array_equal(
        nominal.estimator_inputs.evaluation_values,
        stressed.estimator_inputs.evaluation_values,
    )
    for case in stressed_bundle.cases[:-1]:
        case_receipt = case.to_dict()
        assert (
            case_receipt["effective_structured_observation_perturbation_scale"] == 0.01
        )
        assert case_receipt["prerequisite_perturbation_suppression_applied"] is False


@pytest.mark.parametrize("warp", (0.0, 0.1))
def test_root_dimension_normalization_conforms_to_parent_radius(
    warp: float,
) -> None:
    radius = 0.48
    domain = SpectralMomentConfirmationGenerator().prepare(_spec(warp=warp)).domain
    graph = construct_radius_graph(
        GraphInput(
            primary_unit_id=f"spectral-radius-conformance-{warp}",
            vertex_ids=domain.row_ids,
            states=domain.states,
        ),
        RadiusGraphSpec(
            spec_id=f"spectral-radius-conformance-{warp}",
            purpose=GraphPurpose.FIELD_ESTIMATION,
            radius=radius,
        ),
    )
    expected_edges = np.asarray(
        [
            (left, right)
            for left in range(49)
            for right in range(left + 1, 49)
            if max(
                abs(left % 7 - right % 7),
                abs(left // 7 - right // 7),
            )
            == 1
        ],
        dtype=np.int64,
    )
    distances = np.linalg.norm(
        domain.states[:, None, :] - domain.states[None, :, :],
        axis=2,
    )
    expected_edge_set = {(int(left), int(right)) for left, right in expected_edges}
    excluded_distances = [
        distances[left, right]
        for left in range(49)
        for right in range(left + 1, 49)
        if (left, right) not in expected_edge_set
    ]

    assert SPECTRAL_MOMENT_STATE_NORMALIZATION_SCALE == (1.0 / math.sqrt(12.0))
    assert expected_edges.shape == (156, 2)
    assert np.array_equal(graph.canonical_edges, expected_edges)
    assert float(np.max(graph.edge_distances)) < radius
    assert float(np.min(excluded_distances)) > radius
    assert len(set(graph.component_labels.tolist())) == 1
    assert np.all(graph.two_core_mask)


def test_prepare_does_not_construct_oracle_objects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oracle_constructions: list[object] = []

    def forbidden_oracle_construction(*args: object, **kwargs: object) -> object:
        oracle_constructions.append((args, kwargs))
        raise AssertionError("prepare() attempted to construct an oracle")

    monkeypatch.setattr(
        confirmation_module,
        "SpectralMomentConfirmationOracleTruth",
        forbidden_oracle_construction,
    )
    prepared = SpectralMomentConfirmationGenerator().prepare(
        _spec(warp=0.1, perturbation=0.01)
    )

    assert oracle_constructions == []
    assert len(prepared.cases) == 4
    assert prepared.to_dict()["oracle_truth_record_materialized"] is False
    for case in prepared.cases:
        assert not hasattr(case, "oracle_truth")
        assert case.to_dict()["oracle_truth_record_materialized"] is False


def test_exact_four_semantics_share_one_7_by_7_discrete_domain() -> None:
    bundle = _bundle()
    domain = bundle.domain

    assert (
        tuple(case.oracle_truth.case_semantics for case in bundle.cases)
        == SPECTRAL_MOMENT_REQUIRED_CASE_SEMANTICS
    )
    assert domain.row_ids.shape == (49,)
    assert domain.support_mask.shape == (49,)
    assert np.all(domain.support_mask)
    assert domain.states.shape == (49, 12)
    assert domain.site_coordinates.shape == (49, 2)
    assert domain.oriented_faces.shape == (72, 3)

    for case in bundle.cases:
        inputs = case.estimator_inputs
        assert isinstance(inputs, CartesianFourierEstimatorInputs)
        assert np.array_equal(inputs.row_ids, domain.row_ids)
        assert np.array_equal(inputs.states, domain.states)
        assert np.array_equal(inputs.site_coordinates, domain.site_coordinates)
        assert np.array_equal(inputs.oriented_faces, domain.oriented_faces)

    assert [
        int(case.oracle_truth.field_support_mask.sum()) for case in bundle.cases
    ] == [
        48,
        48,
        49,
        0,
    ]
    assert [int(case.oracle_truth.core_anchor_mask.sum()) for case in bundle.cases] == [
        1,
        1,
        0,
        0,
    ]


def test_estimator_inputs_are_label_free_and_oracle_arrays_are_immutable() -> None:
    bundle = _bundle()
    forbidden = {
        "case_id",
        "case_semantics",
        "oracle_truth",
        "first_moment_field",
        "core_anchor_mask",
        "probe_loop_vertex_rows",
    }

    for case in bundle.cases:
        inputs = case.estimator_inputs
        assert forbidden.isdisjoint(item.name for item in fields(inputs))
        receipt = inputs.to_dict()
        assert receipt["truth_present"] is False
        assert receipt["case_id_present"] is False
        assert receipt["semantic_labels_present"] is False
        assert case.case_id not in inputs.input_id
        assert case.oracle_truth.case_semantics not in inputs.input_id
        for value in (
            inputs.row_ids,
            inputs.states,
            inputs.site_coordinates,
            inputs.oriented_faces,
            inputs.fit_values,
            inputs.evaluation_values,
            case.oracle_truth.first_moment_field,
            case.oracle_truth.second_moment_field,
            case.oracle_truth.field_support_mask,
            case.oracle_truth.core_anchor_mask,
        ):
            assert value.flags.c_contiguous
            assert value.flags.writeable is False
            with pytest.raises(ValueError):
                value.setflags(write=True)


def test_content_identifier_is_locked_estimator_compatible() -> None:
    inputs = _bundle().positive.estimator_inputs
    rebuilt = CartesianFourierEstimatorInputs.from_observable_arrays(
        row_ids=inputs.row_ids,
        states=inputs.states,
        site_coordinates=inputs.site_coordinates,
        oriented_faces=inputs.oriented_faces,
        fit_sample_ids=inputs.fit_sample_ids,
        fit_angles_rad=inputs.fit_angles_rad,
        fit_values=inputs.fit_values,
        evaluation_sample_ids=inputs.evaluation_sample_ids,
        evaluation_angles_rad=inputs.evaluation_angles_rad,
        evaluation_values=inputs.evaluation_values,
    )
    assert rebuilt.input_id == inputs.input_id


def test_oracle_semantics_cannot_be_relabelled_or_moved_into_inputs() -> None:
    case = _bundle().positive
    with pytest.raises(ValueError, match="null loop semantics"):
        replace(case.oracle_truth, case_semantics="localized-core|null")
    with pytest.raises(ValueError, match="localized-core field"):
        replace(
            case.oracle_truth,
            first_moment_field=np.ones((49, 2), dtype=np.float64),
            second_moment_field=np.ones((49, 2), dtype=np.float64),
            field_support_mask=np.ones(49, dtype=np.bool_),
        )


def test_development_seed_runs_through_graph_and_locked_field_estimator() -> None:
    inputs = _bundle().positive.estimator_inputs
    graph = construct_mutual_knn(
        GraphInput(
            primary_unit_id="spectral-moment-development-unit",
            vertex_ids=inputs.row_ids,
            states=inputs.states,
        ),
        MutualKnnSpec(
            spec_id="spectral-moment-development-field",
            purpose=GraphPurpose.FIELD_ESTIMATION,
            neighbor_count=6,
        ),
    )
    estimate = estimate_cartesian_fourier_field(inputs, graph)

    assert isinstance(estimate, CartesianFourierFieldEstimate)
    assert estimate.estimator_inputs is inputs
    assert estimate.section_values.shape == (49, 2)
    assert estimate.amplitude[24] == pytest.approx(0.0, abs=1e-12)
    assert np.max(estimate.split_disagreement) < 1e-12
    assert estimate.to_dict()["truth_read"] is False
    assert estimate.to_dict()["integer_output_authorized"] is False


def test_bundle_keeps_development_and_claim_boundaries_explicit() -> None:
    receipt = _bundle().to_dict()

    assert receipt["development_only"] is True
    assert receipt["d7_runner_present"] is False
    assert receipt["d7_confirmation_executed"] is False
    assert receipt["confirmation_seed_frozen"] is False
    assert receipt["model_values_present"] is False
    assert receipt["semantic_labels_present"] is False
    assert receipt["model_claim_authorized"] is False
    assert receipt["semantic_claim_authorized"] is False
    assert receipt["integer_output_authorized"] is False
    assert receipt["topology_claim_authorized"] is False
    for case in _bundle().cases:
        oracle_receipt = case.oracle_truth.to_dict()
        assert oracle_receipt["integer_loop_value_present"] is False
        assert oracle_receipt["topology_claimed"] is False
