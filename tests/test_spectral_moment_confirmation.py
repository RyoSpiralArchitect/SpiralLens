from __future__ import annotations

import hashlib
import inspect
from dataclasses import fields, replace
from pathlib import Path

import numpy as np
import pytest

from spirallens.graphs import (
    GraphInput,
    GraphPurpose,
    MutualKnnSpec,
    construct_mutual_knn,
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
    SpectralMomentConfirmationGenerator,
    SpectralMomentConfirmationSpec,
)

# This is deliberately a local development value, not a library default or a
# frozen D7 confirmation seed.
_DEVELOPMENT_SEED = 9001


def _bundle(seed: int = _DEVELOPMENT_SEED):
    return SpectralMomentConfirmationGenerator().generate(
        SpectralMomentConfirmationSpec(seed=seed)
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
    first = generator.generate(SpectralMomentConfirmationSpec(seed=11))
    second = generator.generate(SpectralMomentConfirmationSpec(seed=12))

    require_distinct_construction_families((cartesian, generator.family_identity))
    assert first.family_identity == second.family_identity
    assert first.family_identity.family_id == SPECTRAL_MOMENT_GENERATOR_FAMILY_ID
    assert (
        first.family_identity.construction_family_id
        == SPECTRAL_MOMENT_CONSTRUCTION_FAMILY_ID
    )
    assert (
        first.family_identity.implementation_id
        == SPECTRAL_MOMENT_IMPLEMENTATION_ID
    )
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
    assert (
        inspect.signature(SpectralMomentConfirmationSpec).parameters["seed"].default
        is inspect.Parameter.empty
    )
    with pytest.raises(TypeError, match="seed must be an integer"):
        SpectralMomentConfirmationSpec(seed=True)
    with pytest.raises(ValueError, match="non-negative"):
        SpectralMomentConfirmationSpec(seed=-1)

    receipt = SpectralMomentConfirmationSpec(seed=_DEVELOPMENT_SEED).to_dict()
    assert receipt["confirmation_seed_frozen_by_this_source"] is False


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
