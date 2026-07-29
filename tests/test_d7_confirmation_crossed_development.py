from __future__ import annotations

from collections import Counter
from dataclasses import replace

import pytest
from test_d7_confirmation_execution_design import _build_design

from spirallens.qualification.common import (
    CoreDisposition,
    CorePredictionClass,
    LoopDisposition,
    LoopPredictionClass,
    QualificationContractError,
)
from spirallens.qualification.confirmation_crossed_development import (
    execute_d7_confirmation_development_inventory,
    execute_d7_confirmation_development_primary,
)
from spirallens.synthetic import spectral_moment_confirmation
from spirallens.synthetic.spectral_moment_confirmation import (
    SpectralMomentConfirmationGenerator,
    SpectralMomentConfirmationSpec,
    SpectralMomentPreparedBundle,
)


def test_one_primary_uses_the_oracle_free_prepared_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = _build_design()
    unit = design.inventory.primary_units[0]
    prepare_calls: list[int] = []
    original_prepare = SpectralMomentConfirmationGenerator.prepare

    def counted_prepare(
        self: SpectralMomentConfirmationGenerator,
        spec: SpectralMomentConfirmationSpec,
    ) -> SpectralMomentPreparedBundle:
        prepare_calls.append(spec.seed)
        return original_prepare(self, spec)

    def forbidden_oracle(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("development execution must not construct an oracle")

    monkeypatch.setattr(
        SpectralMomentConfirmationGenerator,
        "prepare",
        counted_prepare,
    )
    monkeypatch.setattr(
        spectral_moment_confirmation,
        "_oracle_truth",
        forbidden_oracle,
    )

    prediction = execute_d7_confirmation_development_primary(
        design,
        unit=unit,
        development_seed=9001,
    )

    expected_core_ids = {
        item.core_cell_id
        for item in design.inventory.core_cells
        if item.primary_unit_id == unit.primary_unit_id
    }
    expected_loop_ids = {
        item.loop_cell_id
        for item in design.inventory.loop_cells
        if item.primary_unit_id == unit.primary_unit_id
    }
    assert prepare_calls == [9001]
    assert prediction.primary_unit_id == unit.primary_unit_id
    assert {item.core_cell_id for item in prediction.core_predictions} == (
        expected_core_ids
    )
    assert {item.loop_cell_id for item in prediction.loop_predictions} == (
        expected_loop_ids
    )
    assert len(expected_core_ids) == 3
    assert len(expected_loop_ids) == 18
    assert all(
        item.prediction.oracle_read is False for item in prediction.core_predictions
    )
    assert all(
        item.prediction.oracle_read is False for item in prediction.loop_predictions
    )
    document = prediction.to_dict()
    assert document["oracle_truth_record_materialized"] is False
    assert document["d7_gate_scored"] is False
    assert document["core_and_loop_share_graph_input"] is True
    assert document["core_and_loop_share_a_bound_field_estimates"] is True


def test_full_development_inventory_covers_every_crossed_cell_exactly() -> None:
    design = _build_design()

    result = execute_d7_confirmation_development_inventory(
        design,
        development_seeds=(9001, 9002),
    )

    primary_ids = {item.primary_unit_id for item in design.inventory.primary_units}
    core_ids = {item.core_cell_id for item in design.inventory.core_cells}
    loop_ids = {item.loop_cell_id for item in design.inventory.loop_cells}
    observed_core_ids = {
        item.core_cell_id
        for primary in result.primary_predictions
        for item in primary.core_predictions
    }
    observed_loop_ids = {
        item.loop_cell_id
        for primary in result.primary_predictions
        for item in primary.loop_predictions
    }
    unmatched_loop_ids = loop_ids.symmetric_difference(observed_loop_ids)
    core_classes = Counter(
        item.prediction.prediction_class
        for primary in result.primary_predictions
        for item in primary.core_predictions
    )
    loop_classes = Counter(
        item.prediction.prediction_class
        for primary in result.primary_predictions
        for item in primary.loop_predictions
    )
    expected_core_class = {
        CoreDisposition.LOCALIZED_CORE: (CorePredictionClass.LOCALIZED_CORE),
        CoreDisposition.NO_CORE: CorePredictionClass.NO_CORE,
        CoreDisposition.PREREQUISITE_FAILURE: (CorePredictionClass.ABSTAIN),
    }
    expected_loop_class = {
        LoopDisposition.NONZERO: LoopPredictionClass.NONZERO,
        LoopDisposition.NULL: LoopPredictionClass.NULL,
        LoopDisposition.PREREQUISITE_FAILURE: (LoopPredictionClass.ABSTAIN),
    }
    predicted_primary = {
        item.primary_unit_id: item for item in result.primary_predictions
    }

    assert result.development_seeds == (9001, 9002)
    assert result.design_sha256 == design.canonical_sha256
    assert {item.primary_unit_id for item in result.primary_predictions} == primary_ids
    assert observed_core_ids == core_ids
    assert observed_loop_ids == loop_ids
    assert unmatched_loop_ids == set()
    assert len(result.primary_predictions) == 64
    assert len(observed_core_ids) == 192
    assert len(observed_loop_ids) == 1_152
    assert all(
        len(primary.core_predictions) == 3 and len(primary.loop_predictions) == 18
        for primary in result.primary_predictions
    )
    for cell in design.inventory.core_cells:
        primary = predicted_primary[cell.primary_unit_id]
        prediction = next(
            item
            for item in primary.core_predictions
            if item.core_cell_id == cell.core_cell_id
        )
        assert (
            prediction.prediction.prediction_class
            is (expected_core_class[cell.expected_core_disposition])
        )
    for cell in design.inventory.loop_cells:
        primary = predicted_primary[cell.primary_unit_id]
        prediction = next(
            item
            for item in primary.loop_predictions
            if item.loop_cell_id == cell.loop_cell_id
        )
        assert (
            prediction.prediction.prediction_class
            is (expected_loop_class[cell.expected_loop_disposition])
        )
    assert core_classes == Counter(
        {
            CorePredictionClass.LOCALIZED_CORE: 96,
            CorePredictionClass.NO_CORE: 48,
            CorePredictionClass.ABSTAIN: 48,
        }
    )
    assert loop_classes == Counter(
        {
            LoopPredictionClass.NULL: 720,
            LoopPredictionClass.ABSTAIN: 288,
            LoopPredictionClass.NONZERO: 144,
        }
    )
    document = result.to_dict()
    assert document["counts"] == {
        "primary_units": 64,
        "core_predictions": 192,
        "loop_predictions": 1_152,
    }
    assert document["oracle_truth_record_materialized"] is False
    assert document["oracle_supplier_called"] is False
    assert document["d7_state"] == "not_run"
    assert document["scientific_claim_eligible"] is False


def test_development_inventory_rejects_an_unlisted_seed() -> None:
    with pytest.raises(
        QualificationContractError,
        match="only permanently excluded seeds",
    ):
        execute_d7_confirmation_development_inventory(
            _build_design(),
            development_seeds=(9001, 9100),
        )


def test_development_receipts_are_executor_factory_only() -> None:
    result = execute_d7_confirmation_development_inventory(
        _build_design(),
        development_seeds=(9001, 9002),
    )
    first = result.primary_predictions[0]

    with pytest.raises(
        QualificationContractError,
        match="must be produced by",
    ):
        replace(first, development_seed=9002)
    with pytest.raises(
        QualificationContractError,
        match="must be produced by",
    ):
        replace(result, design_sha256="1" * 64)
