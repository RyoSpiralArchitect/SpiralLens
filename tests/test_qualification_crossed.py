from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np
import pytest

from spirallens.core.canonical import canonical_json_sha256
from spirallens.graphs import (
    BoundaryRefinementRule,
    GraphFamily,
    GraphInput,
    GraphPurpose,
)
from spirallens.graphs.common import array_fingerprint
from spirallens.qualification.common import (
    QualificationContractError,
    QualificationState,
)
from spirallens.qualification.crossed import (
    CrossedNonvacuityReceipt,
    assess_crossed_nonvacuity,
    build_crossed_blind_core_input,
    build_crossed_blind_loop_input,
    build_crossed_graph_execution,
    domain_construction_sha256,
    rectangular_grid_support_faces,
    support_construction_sha256,
)
from spirallens.qualification.protocol import (
    GraphAxes,
    GraphDeclaration,
)
from spirallens.synthetic.cartesian_fourier_domain_phantom import (
    CartesianFourierDomainGenerator,
    CartesianFourierDomainSpec,
)
from spirallens.synthetic.cartesian_fourier_estimator import (
    estimate_cartesian_fourier_field,
)


def _declaration(
    graph_id: str,
    family: GraphFamily,
    purpose: GraphPurpose,
    **parameters: float,
) -> GraphDeclaration:
    return GraphDeclaration(
        graph_id=graph_id,
        family=family,
        purpose=purpose,
        parameters=tuple(sorted(parameters.items())),
    )


def _axes() -> GraphAxes:
    return GraphAxes(
        field_estimation=(
            _declaration(
                "a-mutual",
                GraphFamily.MUTUAL_KNN,
                GraphPurpose.FIELD_ESTIMATION,
                neighbor_count=4,
            ),
            _declaration(
                "a-radius",
                GraphFamily.FIXED_RADIUS,
                GraphPurpose.FIELD_ESTIMATION,
                radius=0.42,
            ),
            _declaration(
                "a-shared",
                GraphFamily.SHARED_NEIGHBOR,
                GraphPurpose.FIELD_ESTIMATION,
                minimum_shared_neighbors=2,
                neighbor_count=4,
            ),
        ),
        cycle_construction=(
            _declaration(
                "b-mutual",
                GraphFamily.MUTUAL_KNN,
                GraphPurpose.CYCLE_CONSTRUCTION,
                neighbor_count=4,
            ),
            _declaration(
                "b-radius",
                GraphFamily.FIXED_RADIUS,
                GraphPurpose.CYCLE_CONSTRUCTION,
                radius=0.42,
            ),
            _declaration(
                "b-shared",
                GraphFamily.SHARED_NEIGHBOR,
                GraphPurpose.CYCLE_CONSTRUCTION,
                minimum_shared_neighbors=1,
                neighbor_count=3,
            ),
        ),
    )


def _execution(
    *,
    warp: float = 0.0,
    support: str = "outer",
    case_name: str = "positive",
):
    phantom = CartesianFourierDomainGenerator().generate(
        CartesianFourierDomainSpec(
            grid_side=7,
            density_warp_strength=warp,
        )
    )
    case = getattr(phantom, case_name)
    inputs = case.estimator_inputs
    graph_input = GraphInput(
        primary_unit_id=f"fourier-warp-{int(warp * 100):02d}-{support}",
        vertex_ids=inputs.row_ids,
        states=inputs.states,
    )
    rectangles = {
        "outer": (0, 0, 6, 6),
        "central": (2, 2, 4, 4),
        "offcore": (0, 0, 1, 1),
    }
    x0, y0, x1, y1 = rectangles[support]
    execution = build_crossed_graph_execution(
        graph_input=graph_input,
        graph_axes=_axes(),
        oriented_faces=inputs.oriented_faces,
        support_face_indices=rectangular_grid_support_faces(
            grid_side=7,
            x_min=x0,
            y_min=y0,
            x_max=x1,
            y_max=y1,
        ),
        domain_id=f"grid-domain-{support}",
        cycle_class_spec_id=f"boundary-{support}",
        matched_set_id=f"matched-{support}",
        refinement_rule=BoundaryRefinementRule(
            rule_id="forward-span-four",
            max_domain_edges_per_graph_edge=4,
        ),
    )
    estimates = tuple(
        estimate_cartesian_fourier_field(inputs, graph)
        for graph in execution.field_graphs
    )
    return execution, estimates


def _estimate_proxy(base, **overrides):
    values = {
        "field_graph": base.field_graph,
        "estimator_input_fingerprint_sha256": (base.estimator_input_fingerprint_sha256),
        "field_graph_fingerprint_sha256": (base.field_graph_fingerprint_sha256),
        "field_consumption_sha256": base.field_consumption_sha256,
        "substantive_output_sha256": base.substantive_output_sha256,
        "output_sha256": base.output_sha256,
        "fingerprint_sha256": base.fingerprint_sha256,
        "section_values": base.section_values,
        "amplitude": base.amplitude,
        "identifiability_score": base.identifiability_score,
        "edge_coherence": base.edge_coherence,
        "support_count": base.support_count,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _substantive_sha256(estimate) -> str:
    return canonical_json_sha256(
        {
            "section_values": array_fingerprint(estimate.section_values),
            "amplitude": array_fingerprint(estimate.amplitude),
            "identifiability_score": array_fingerprint(estimate.identifiability_score),
            "edge_coherence": array_fingerprint(estimate.edge_coherence),
        }
    )


def test_construction_identities_are_stable_and_value_free() -> None:
    assert (
        domain_construction_sha256()
        == "378fc615e5beeb016fa512fb56275ad26ee9ef6d06ddc4c287cbcf7c318f0d3a"
    )
    assert (
        support_construction_sha256()
        == "2f31fec788dcba68889e1683048e6b5a057722526d6ce3a66ed5a3998c8f3533"
    )


@pytest.mark.parametrize("support", ["outer", "central", "offcore"])
def test_actual_crossed_content_is_nonvacuous(support: str) -> None:
    execution, estimates = _execution(support=support)
    receipt = assess_crossed_nonvacuity(
        execution,
        estimates,
        minimum_representative_content_variants=2,
        require_substantive_output_variation=True,
    )
    assert receipt.state is QualificationState.PASS
    assert receipt.field_adjacency_variant_count == 3
    assert receipt.cycle_adjacency_variant_count == 3
    assert receipt.field_consumption_variant_count >= 2
    assert receipt.field_output_variant_count >= 2
    assert receipt.matched_cycle_count == 3
    assert receipt.representative_content_variant_count >= 2
    assert len(execution.field_graphs) * len(execution.cycle_graphs) == 9


def test_mild_density_stress_preserves_matched_cross() -> None:
    execution, estimates = _execution(warp=0.1, support="central")
    receipt = assess_crossed_nonvacuity(
        execution,
        estimates,
        minimum_representative_content_variants=2,
        require_substantive_output_variation=True,
    )
    assert receipt.state is QualificationState.PASS
    assert all(attempt.binding is not None for attempt in execution.cycle_attempts)


def test_only_frozen_sentinel_requires_substantive_a_output_variation() -> None:
    execution, estimates = _execution(case_name="no_core_null")
    required = assess_crossed_nonvacuity(
        execution,
        estimates,
        minimum_representative_content_variants=2,
        require_substantive_output_variation=True,
    )
    ordinary_control = assess_crossed_nonvacuity(
        execution,
        estimates,
        minimum_representative_content_variants=2,
        require_substantive_output_variation=False,
    )
    assert required.state is QualificationState.INSUFFICIENT
    assert required.reason_codes == (
        "field-output-axis-vacuous",
        "field-output-effect-below-minimum",
        "field-output-graph-coverage-incomplete",
    )
    assert ordinary_control.state is QualificationState.PASS
    assert ordinary_control.field_output_variant_count == 1


@dataclass(frozen=True)
class _SpoofedEstimate:
    field_consumption_sha256: str
    output_sha256: str
    fingerprint_sha256: str


def test_identifier_only_field_axis_is_insufficient() -> None:
    execution, _estimates = _execution()
    same = "0" * 64
    spoofed = tuple(
        _SpoofedEstimate(
            field_consumption_sha256=same,
            output_sha256=same,
            fingerprint_sha256=f"{index + 1:064x}",
        )
        for index in range(3)
    )
    with pytest.raises(
        QualificationContractError,
        match="align with all three A graphs",
    ):
        assess_crossed_nonvacuity(
            execution,
            spoofed,
            minimum_representative_content_variants=2,
            require_substantive_output_variation=True,
        )


def test_actual_estimates_cannot_be_reordered_across_a_graphs() -> None:
    execution, estimates = _execution()
    with pytest.raises(
        QualificationContractError,
        match="exact A graph",
    ):
        assess_crossed_nonvacuity(
            execution,
            (estimates[1], estimates[0], estimates[2]),
            minimum_representative_content_variants=2,
            require_substantive_output_variation=True,
        )


def test_declared_field_consumption_must_equal_reconstructed_content() -> None:
    execution, estimates = _execution()
    tampered = _estimate_proxy(
        estimates[0],
        field_consumption_sha256="0" * 64,
    )
    with pytest.raises(
        QualificationContractError,
        match="consumption digest is not reconstructable",
    ):
        assess_crossed_nonvacuity(
            execution,
            (tampered, estimates[1], estimates[2]),
            minimum_representative_content_variants=2,
            require_substantive_output_variation=True,
        )


def test_digest_only_one_bit_output_variation_is_insufficient() -> None:
    execution, estimates = _execution()
    proxies = []
    reference = estimates[0]
    for index, estimate in enumerate(estimates):
        section = np.array(reference.section_values, copy=True)
        section[0, 0] += index * 1e-12
        proxy = _estimate_proxy(
            estimate,
            section_values=section,
            amplitude=reference.amplitude,
            identifiability_score=reference.identifiability_score,
            edge_coherence=reference.edge_coherence,
        )
        proxy.substantive_output_sha256 = _substantive_sha256(proxy)
        proxies.append(proxy)
    receipt = assess_crossed_nonvacuity(
        execution,
        tuple(proxies),
        minimum_representative_content_variants=2,
        require_substantive_output_variation=True,
        minimum_substantive_output_distance=1e-6,
    )
    assert receipt.state is QualificationState.INSUFFICIENT
    assert receipt.field_output_variant_count == 3
    assert receipt.reason_codes == (
        "field-output-effect-below-minimum",
        "field-output-graph-coverage-incomplete",
    )


def test_sentinel_records_all_pairs_and_covers_every_a_graph() -> None:
    execution, estimates = _execution()
    receipt = assess_crossed_nonvacuity(
        execution,
        estimates,
        minimum_representative_content_variants=2,
        require_substantive_output_variation=True,
        minimum_substantive_output_distance=1e-6,
    )

    assert len(receipt.field_graph_pair_effects) == 3
    assert receipt.substantive_response_field_graph_count == 3
    assert receipt.substantive_response_field_graph_ids == tuple(
        sorted(graph.specification.spec_id for graph in execution.field_graphs)
    )
    assert all(
        "section_values" in pair.qualifying_substantive_components
        for pair in receipt.field_graph_pair_effects
    )
    assert all(
        "edge_coherence" not in pair.qualifying_substantive_components
        for pair in receipt.field_graph_pair_effects
    )


def test_edge_coherence_only_change_cannot_satisfy_sentinel() -> None:
    execution, estimates = _execution()
    reference = estimates[0]
    proxies = []
    for index, estimate in enumerate(estimates):
        proxy = _estimate_proxy(
            estimate,
            section_values=reference.section_values,
            amplitude=reference.amplitude,
            identifiability_score=reference.identifiability_score,
            edge_coherence=reference.edge_coherence + index * 0.25,
        )
        proxy.substantive_output_sha256 = _substantive_sha256(proxy)
        proxies.append(proxy)

    receipt = assess_crossed_nonvacuity(
        execution,
        tuple(proxies),
        minimum_representative_content_variants=2,
        require_substantive_output_variation=True,
        minimum_substantive_output_distance=1e-6,
    )

    assert receipt.state is QualificationState.INSUFFICIENT
    assert receipt.field_output_variant_count == 3
    assert receipt.maximum_pairwise_substantive_output_distance == 0.0
    assert receipt.substantive_response_field_graph_ids == ()
    assert "field-output-effect-below-minimum" in receipt.reason_codes
    assert "field-output-graph-coverage-incomplete" in receipt.reason_codes


def test_one_large_pair_effect_cannot_hide_an_unresponsive_a_graph() -> None:
    execution, estimates = _execution()
    reference = estimates[0]
    offsets = (0.0, 0.7e-6, -0.7e-6)
    proxies = []
    for offset, estimate in zip(offsets, estimates, strict=True):
        proxy = _estimate_proxy(
            estimate,
            section_values=reference.section_values + offset,
            amplitude=reference.amplitude,
            identifiability_score=reference.identifiability_score,
            edge_coherence=reference.edge_coherence,
        )
        proxy.substantive_output_sha256 = _substantive_sha256(proxy)
        proxies.append(proxy)

    receipt = assess_crossed_nonvacuity(
        execution,
        tuple(proxies),
        minimum_representative_content_variants=2,
        require_substantive_output_variation=True,
        minimum_substantive_output_distance=1e-6,
    )

    assert receipt.maximum_pairwise_substantive_output_distance > 1e-6
    assert (
        sum(pair.substantive_response_pass for pair in receipt.field_graph_pair_effects)
        == 1
    )
    assert receipt.substantive_response_field_graph_count == 2
    assert receipt.state is QualificationState.INSUFFICIENT
    assert receipt.reason_codes == ("field-output-graph-coverage-incomplete",)


def test_single_scalar_spike_cannot_satisfy_field_response() -> None:
    execution, estimates = _execution()
    reference = estimates[0]
    offsets = (0.0, 1.0, -1.0)
    proxies = []
    for offset, estimate in zip(offsets, estimates, strict=True):
        section = np.array(reference.section_values, copy=True)
        section[0, 0] += offset
        proxy = _estimate_proxy(
            estimate,
            section_values=section,
            amplitude=reference.amplitude,
            identifiability_score=reference.identifiability_score,
            edge_coherence=reference.edge_coherence,
        )
        proxy.substantive_output_sha256 = _substantive_sha256(proxy)
        proxies.append(proxy)

    receipt = assess_crossed_nonvacuity(
        execution,
        tuple(proxies),
        minimum_representative_content_variants=2,
        require_substantive_output_variation=True,
        minimum_substantive_output_distance=1e-6,
    )

    assert receipt.maximum_pairwise_substantive_output_distance > 1e-6
    assert receipt.substantive_response_field_graph_count == 0
    assert all(
        not pair.substantive_response_pass for pair in receipt.field_graph_pair_effects
    )
    assert "field-output-single-scalar-only" in receipt.reason_codes
    assert "field-output-graph-coverage-incomplete" in receipt.reason_codes


def test_exact_pair_receipts_are_revalidated_on_load() -> None:
    execution, estimates = _execution()
    receipt = assess_crossed_nonvacuity(
        execution,
        estimates,
        minimum_representative_content_variants=2,
        require_substantive_output_variation=True,
        minimum_substantive_output_distance=1e-6,
    )
    payload = receipt.to_dict()
    assert CrossedNonvacuityReceipt.from_dict(payload).to_dict() == payload

    missing_pair = deepcopy(payload)
    missing_pair["field_graph_pair_effects"].pop()  # type: ignore[union-attr]
    with pytest.raises(
        QualificationContractError,
        match="exact three A-graph pairs",
    ):
        CrossedNonvacuityReceipt.from_dict(missing_pair)

    forged_single_scalar = deepcopy(payload)
    pair = forged_single_scalar["field_graph_pair_effects"][0]  # type: ignore[index]
    component = next(  # type: ignore[union-attr]
        item
        for item in pair["component_effects"]
        if item["component_name"] == "section_values"
    )
    component["changed_scalar_count"] = 1
    with pytest.raises(
        QualificationContractError,
        match="qualifies flag differs",
    ):
        CrossedNonvacuityReceipt.from_dict(forged_single_scalar)

    forged_edge = deepcopy(payload)
    pair = forged_edge["field_graph_pair_effects"][0]  # type: ignore[index]
    edge = next(  # type: ignore[union-attr]
        item
        for item in pair["component_effects"]
        if item["component_name"] == "edge_coherence"
    )
    edge["effect_eligible"] = True
    with pytest.raises(
        QualificationContractError,
        match="effect_eligible differs",
    ):
        CrossedNonvacuityReceipt.from_dict(forged_edge)


def test_crossed_factories_bind_exact_a_field_and_b_representative() -> None:
    execution, estimates = _execution(support="central")
    primary_digest = "a" * 64
    core_input = build_crossed_blind_core_input(
        execution,
        estimates[0],
        primary_unit_sha256=primary_digest,
    )
    loop_input = build_crossed_blind_loop_input(
        execution,
        estimates[0],
        cycle_graph_id="b-mutual",
        primary_unit_sha256=primary_digest,
    )

    assert (
        core_input.field_graph_fingerprint_sha256
        == execution.field_graphs[0].fingerprint_sha256
    )
    assert (
        loop_input.field_graph_fingerprint_sha256
        == execution.field_graphs[0].fingerprint_sha256
    )
    assert (
        loop_input.cycle_graph_fingerprint_sha256
        == execution.cycle_graphs[0].fingerprint_sha256
    )
    assert loop_input.section_values.shape[0] >= 3


def test_rectangular_support_rejects_degenerate_or_outside_regions() -> None:
    with pytest.raises(QualificationContractError, match="strictly inside"):
        rectangular_grid_support_faces(
            grid_side=7,
            x_min=2,
            y_min=2,
            x_max=2,
            y_max=4,
        )
    with pytest.raises(QualificationContractError, match="strictly inside"):
        rectangular_grid_support_faces(
            grid_side=7,
            x_min=0,
            y_min=0,
            x_max=7,
            y_max=6,
        )
