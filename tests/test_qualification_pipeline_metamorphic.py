from __future__ import annotations

from dataclasses import replace

import pytest

from spirallens.qualification.common import (
    QualificationContractError,
    QualificationState,
)
from spirallens.qualification.pipeline_metamorphic import (
    PIPELINE_METAMORPHIC_DEVELOPMENT_SEED,
    CartesianPipelineMetamorphicReceipt,
    PipelineMetamorphCheck,
    PipelineMetamorphLaw,
    PipelineSnapshot,
    run_cartesian_pipeline_metamorphic_checks,
)


@pytest.fixture(scope="module")
def receipt() -> CartesianPipelineMetamorphicReceipt:
    return run_cartesian_pipeline_metamorphic_checks()


def test_actual_pipeline_metamorphic_suite_passes(
    receipt: CartesianPipelineMetamorphicReceipt,
) -> None:
    assert receipt.state is QualificationState.PASS
    assert receipt.development_seed == PIPELINE_METAMORPHIC_DEVELOPMENT_SEED
    assert receipt.pipeline_rerun_verified is True
    assert tuple(check.law for check in receipt.checks) == (
        PipelineMetamorphLaw.AMBIENT_SIGNED_PERMUTATION,
        PipelineMetamorphLaw.REFERENCE_ROTATION,
        PipelineMetamorphLaw.REFERENCE_REFLECTION,
        PipelineMetamorphLaw.LOOP_REVERSAL,
    )
    for check in receipt.checks:
        assert check.state is QualificationState.PASS
        assert check.nonidentity_verified is True
        assert check.inverse_verified is True
        assert check.composition_verified is True
        assert check.all_graph_adjacencies_verified is True
        assert check.all_graph_edge_distances_bit_identical is True
        assert check.claim_relevant_field_law_verified is True
        assert check.continuous_loop_law_verified is True
        assert check.pipeline_rerun_verified is True
        assert check.maximum_distance_error <= check.tolerance
        assert check.maximum_field_law_error <= check.tolerance
        assert check.maximum_loop_law_error <= check.tolerance
        assert isinstance(check.base, PipelineSnapshot)
        assert isinstance(check.transformed, PipelineSnapshot)
    assert receipt.checks[0].maximum_distance_error == 0.0


def test_fingerprints_expose_which_pipeline_stage_transformed(
    receipt: CartesianPipelineMetamorphicReceipt,
) -> None:
    ambient, rotation, reflection, reversal = receipt.checks

    assert (
        ambient.base.estimator_input_fingerprint_sha256
        != ambient.transformed.estimator_input_fingerprint_sha256
    )
    assert (
        ambient.base.graph_input_fingerprint_sha256
        != ambient.transformed.graph_input_fingerprint_sha256
    )
    assert (
        ambient.base.field_graph_fingerprint_sha256
        != ambient.transformed.field_graph_fingerprint_sha256
    )

    for reference in (rotation, reflection):
        assert (
            reference.base.estimator_input_fingerprint_sha256
            != reference.transformed.estimator_input_fingerprint_sha256
        )
        assert (
            reference.base.graph_input_fingerprint_sha256
            == reference.transformed.graph_input_fingerprint_sha256
        )
        assert (
            reference.base.field_graph_fingerprint_sha256
            == reference.transformed.field_graph_fingerprint_sha256
        )
        assert (
            reference.base.field_estimate_fingerprint_sha256
            != reference.transformed.field_estimate_fingerprint_sha256
        )
        assert (
            reference.base.blind_loop_input_fingerprint_sha256
            != reference.transformed.blind_loop_input_fingerprint_sha256
        )

    assert (
        reversal.base.estimator_input_fingerprint_sha256
        == reversal.transformed.estimator_input_fingerprint_sha256
    )
    assert (
        reversal.base.field_estimate_fingerprint_sha256
        == reversal.transformed.field_estimate_fingerprint_sha256
    )
    assert (
        reversal.base.blind_loop_input_fingerprint_sha256
        != reversal.transformed.blind_loop_input_fingerprint_sha256
    )
    assert (
        reversal.base.sealed_loop_prediction_fingerprint_sha256
        != reversal.transformed.sealed_loop_prediction_fingerprint_sha256
    )


def test_reference_and_reversal_sign_laws_are_continuous_only(
    receipt: CartesianPipelineMetamorphicReceipt,
) -> None:
    signs = {
        check.law: check.expected_loop_orientation_sign for check in receipt.checks
    }
    assert signs == {
        PipelineMetamorphLaw.AMBIENT_SIGNED_PERMUTATION: 1,
        PipelineMetamorphLaw.REFERENCE_ROTATION: 1,
        PipelineMetamorphLaw.REFERENCE_REFLECTION: -1,
        PipelineMetamorphLaw.LOOP_REVERSAL: -1,
    }

    payload = receipt.to_dict()
    assert payload["sampled_continuous_observable_only"] is True
    assert payload["integer_output_present"] is False
    assert payload["topology_claimed"] is False
    assert payload["d3_gate_advanced"] is False
    assert payload["synthetic_qualification_advanced"] is False
    for check in payload["checks"]:
        assert check["sampled_continuous_observable_only"] is True
        assert check["integer_output_present"] is False
        assert check["topology_claimed"] is False
        assert check["d3_gate_advanced"] is False
        assert check["all_graph_edge_distances_bit_identical"] is True


def test_receipt_is_outcome_free_and_discloses_factory_dependency(
    receipt: CartesianPipelineMetamorphicReceipt,
) -> None:
    payload = receipt.to_dict()
    assert payload["oracle_object_read"] is False
    assert payload["case_id_read"] is False
    assert payload["anchor_read"] is False
    assert payload["charge_read"] is False
    assert payload["subject_value_read"] is False
    assert payload["selection_seed_accessed"] is False
    assert payload["private_content_pseudonym_helper_imported"] is False
    assert payload["content_pseudonym_receipt_algorithm_reimplemented"] is True
    assert (
        payload["content_pseudonym_dependency"]
        == "cartesian-fourier-label-free-content-v0.1"
    )
    assert payload["qualification_contract_module_imported"] is False
    for check in payload["checks"]:
        assert check["oracle_object_read"] is False
        assert check["case_id_read"] is False
        assert check["anchor_read"] is False
        assert check["charge_read"] is False
        assert check["subject_value_read"] is False


def test_pipeline_factories_are_actually_rerun(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from spirallens.qualification import pipeline_metamorphic as module

    counts = {"graph": 0, "field": 0, "loop": 0}
    original_graph = module.build_crossed_graph_execution
    original_field = module.estimate_cartesian_fourier_field
    original_loop = module.estimate_and_seal_loop

    def counted_graph(*args: object, **kwargs: object):
        counts["graph"] += 1
        return original_graph(*args, **kwargs)

    def counted_field(*args: object, **kwargs: object):
        counts["field"] += 1
        return original_field(*args, **kwargs)

    def counted_loop(*args: object, **kwargs: object):
        counts["loop"] += 1
        return original_loop(*args, **kwargs)

    monkeypatch.setattr(module, "build_crossed_graph_execution", counted_graph)
    monkeypatch.setattr(module, "estimate_cartesian_fourier_field", counted_field)
    monkeypatch.setattr(module, "estimate_and_seal_loop", counted_loop)

    observed = module.run_cartesian_pipeline_metamorphic_checks()
    assert observed.state is QualificationState.PASS
    assert counts["graph"] >= 17
    assert counts["field"] == counts["graph"]
    assert counts["loop"] >= counts["graph"] + 2


def test_replay_is_deterministic_and_selection_seeds_are_rejected(
    receipt: CartesianPipelineMetamorphicReceipt,
) -> None:
    replay = run_cartesian_pipeline_metamorphic_checks()
    assert replay.to_dict() == receipt.to_dict()
    assert replay.fingerprint_sha256 == receipt.fingerprint_sha256

    with pytest.raises(
        QualificationContractError,
        match="development seed 314159",
    ):
        run_cartesian_pipeline_metamorphic_checks(development_seed=314160)
    with pytest.raises(QualificationContractError, match="tolerance"):
        run_cartesian_pipeline_metamorphic_checks(tolerance=0.0)
    with pytest.raises(QualificationContractError, match="frozen"):
        run_cartesian_pipeline_metamorphic_checks(tolerance=1.0)


def test_typed_receipts_reject_laundered_pass_states(
    receipt: CartesianPipelineMetamorphicReceipt,
) -> None:
    check = receipt.checks[0]
    with pytest.raises(
        QualificationContractError,
        match="mechanically derived pipeline result",
    ):
        replace(
            check,
            nonidentity_verified=False,
            state=QualificationState.PASS,
        )
    with pytest.raises(
        QualificationContractError,
        match="reason_codes",
    ):
        replace(
            check,
            reason_codes=("pipeline_transformation_law_failed",),
        )
    with pytest.raises(
        QualificationContractError,
        match="pass or fail",
    ):
        replace(check, state=QualificationState.INSUFFICIENT)


def test_public_receipt_types_reject_malformed_digests(
    receipt: CartesianPipelineMetamorphicReceipt,
) -> None:
    check: PipelineMetamorphCheck = receipt.checks[0]
    with pytest.raises(
        QualificationContractError,
        match="estimator_input_fingerprint_sha256",
    ):
        replace(
            check.base,
            estimator_input_fingerprint_sha256="not-a-digest",
        )
