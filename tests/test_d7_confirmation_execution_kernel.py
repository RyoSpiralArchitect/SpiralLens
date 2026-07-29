from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest
from test_d7_confirmation_execution_design import _build_design

from spirallens.core.canonical import canonical_json_sha256
from spirallens.qualification.common import QualificationContractError
from spirallens.qualification.confirmation_crossed_development import (
    D7DevelopmentPredictionInventory,
    execute_d7_confirmation_development_inventory,
    execute_d7_confirmation_development_primary,
)
from spirallens.qualification.confirmation_execution_kernel import (
    D7_SEED_SLOT_PREDICTION_KERNEL_ID,
    D7SeedSlotCorePrediction,
    D7SeedSlotLoopPrediction,
    execute_d7_seed_slot_primary,
)
from spirallens.synthetic import spectral_moment_confirmation
from spirallens.synthetic.spectral_moment_confirmation import (
    SpectralMomentConfirmationGenerator,
    SpectralMomentConfirmationSpec,
    SpectralMomentPreparedBundle,
)

_HISTORICAL_OBSERVABLE_SHA256 = (
    "c05d69597ed9309c087a14d23d6ea5982fb470cb04d3e8d992a30d85ae35b3b0"
)


def _historical_observable_projection(
    inventory: D7DevelopmentPredictionInventory,
) -> dict[str, object]:
    return {
        "projection": "d7-pre-extraction-observable-v0-1",
        "primaries": [
            {
                "id": primary.primary_unit_id,
                "slot": primary.seed_slot_id,
                "seed": primary.development_seed,
                "spec": primary.spec_receipt_sha256,
                "input": primary.estimator_input_fingerprint_sha256,
                "graph": primary.graph_input_fingerprint_sha256,
                "primary": primary.primary_execution_fingerprint_sha256,
                "offcore": primary.offcore_execution_fingerprint_sha256,
                "cores": [
                    {
                        "id": item.core_cell_id,
                        "g": item.field_graph_id,
                        "f": item.field_estimate_fingerprint_sha256,
                        "status": item.prediction.observed_attempt_status.value,
                        "class": item.prediction.prediction_class.value,
                        "reasons": list(item.prediction.reason_codes),
                        "rows": item.prediction.candidate_rows.tolist(),
                        "estimator": item.prediction.estimator_id,
                    }
                    for item in primary.core_predictions
                ],
                "loops": [
                    {
                        "id": item.loop_cell_id,
                        "a": item.field_graph_id,
                        "b": item.cycle_graph_id,
                        "role": item.loop_role.value,
                        "f": item.field_estimate_fingerprint_sha256,
                        "status": item.prediction.observed_attempt_status.value,
                        "class": item.prediction.prediction_class.value,
                        "reasons": list(item.prediction.reason_codes),
                        "total": item.prediction.signed_total_cycles,
                        "max": (
                            item.prediction.max_abs_edge_increment_radians
                        ),
                        "residual": (
                            item.prediction.nearest_integer_residual_cycles
                        ),
                        "tol": item.prediction.comparison_tolerance_cycles,
                        "estimator": item.prediction.estimator_id,
                    }
                    for item in primary.loop_predictions
                ],
            }
            for primary in inventory.primary_predictions
        ],
    }


def test_seed_slot_kernel_accepts_an_unattested_non_development_seed() -> None:
    design = _build_design()
    prediction = execute_d7_seed_slot_primary(
        design,
        unit=design.inventory.primary_units[0],
        supplied_seed=12345,
    )

    document = prediction.to_dict()
    assert document["kernel_id"] == D7_SEED_SLOT_PREDICTION_KERNEL_ID
    assert document["supplied_seed"] == 12345
    assert document["seed_freeze_or_authorization_attested"] is False
    assert document["chronology_attested"] is False
    assert document["claim_ceiling"] == "level_0"
    assert document["oracle_truth_record_materialized"] is False
    assert document["gate_scored"] is False
    assert document["result_produced"] is False
    assert document["scientific_claim_eligible"] is False
    assert len(prediction.core_predictions) == 3
    assert len(prediction.loop_predictions) == 18


def test_seed_slot_kernel_directly_uses_the_oracle_free_prepared_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = _build_design()
    prepare_calls: list[int] = []
    original_prepare = SpectralMomentConfirmationGenerator.prepare

    def counted_prepare(
        self: SpectralMomentConfirmationGenerator,
        spec: SpectralMomentConfirmationSpec,
    ) -> SpectralMomentPreparedBundle:
        prepare_calls.append(spec.seed)
        return original_prepare(self, spec)

    def forbidden_oracle(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("seed-slot kernel must not construct an oracle")

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

    prediction = execute_d7_seed_slot_primary(
        design,
        unit=design.inventory.primary_units[0],
        supplied_seed=12345,
    )

    assert prepare_calls == [12345]
    assert prediction.to_dict()["oracle_truth_record_materialized"] is False


def test_development_adapter_preserves_the_observable_prediction_semantics() -> None:
    design = _build_design()
    unit = design.inventory.primary_units[0]
    kernel = execute_d7_seed_slot_primary(
        design,
        unit=unit,
        supplied_seed=9001,
    )
    development = execute_d7_confirmation_development_primary(
        design,
        unit=unit,
        development_seed=9001,
    )

    assert development.primary_unit_id == kernel.primary_unit_id
    assert development.seed_slot_id == kernel.seed_slot_id
    assert development.development_seed == kernel.supplied_seed
    assert development.spec_receipt_sha256 == kernel.spec_receipt_sha256
    assert (
        development.estimator_input_fingerprint_sha256
        == kernel.estimator_input_fingerprint_sha256
    )
    assert (
        development.graph_input_fingerprint_sha256
        == kernel.graph_input_fingerprint_sha256
    )
    assert (
        development.primary_execution_fingerprint_sha256
        == kernel.primary_execution_fingerprint_sha256
    )
    assert (
        development.offcore_execution_fingerprint_sha256
        == kernel.offcore_execution_fingerprint_sha256
    )

    development_cores = {
        item.core_cell_id: item for item in development.core_predictions
    }
    kernel_cores = {item.core_cell_id: item for item in kernel.core_predictions}
    assert development_cores.keys() == kernel_cores.keys()
    for cell_id, expected in kernel_cores.items():
        observed = development_cores[cell_id]
        assert observed.field_graph_id == expected.field_graph_id
        assert (
            observed.field_estimate_fingerprint_sha256
            == expected.field_estimate_fingerprint_sha256
        )
        assert (
            observed.prediction.observed_attempt_status
            is expected.prediction.observed_attempt_status
        )
        assert (
            observed.prediction.prediction_class
            is expected.prediction.prediction_class
        )
        assert observed.prediction.reason_codes == expected.prediction.reason_codes
        assert observed.prediction.candidate_rows.tolist() == (
            expected.prediction.candidate_rows.tolist()
        )

    development_loops = {
        item.loop_cell_id: item for item in development.loop_predictions
    }
    kernel_loops = {item.loop_cell_id: item for item in kernel.loop_predictions}
    assert development_loops.keys() == kernel_loops.keys()
    for cell_id, expected in kernel_loops.items():
        observed = development_loops[cell_id]
        assert observed.field_graph_id == expected.field_graph_id
        assert observed.cycle_graph_id == expected.cycle_graph_id
        assert observed.loop_role is expected.loop_role
        assert (
            observed.field_estimate_fingerprint_sha256
            == expected.field_estimate_fingerprint_sha256
        )
        assert (
            observed.prediction.observed_attempt_status
            is expected.prediction.observed_attempt_status
        )
        assert (
            observed.prediction.prediction_class
            is expected.prediction.prediction_class
        )
        assert observed.prediction.reason_codes == expected.prediction.reason_codes
        assert (
            observed.prediction.signed_total_cycles
            == expected.prediction.signed_total_cycles
        )
        assert (
            observed.prediction.max_abs_edge_increment_radians
            == expected.prediction.max_abs_edge_increment_radians
        )
        assert (
            observed.prediction.nearest_integer_residual_cycles
            == expected.prediction.nearest_integer_residual_cycles
        )


def test_full_development_observables_match_the_pre_extraction_golden() -> None:
    inventory = execute_d7_confirmation_development_inventory(
        _build_design(),
        development_seeds=(9001, 9002),
    )

    assert (
        canonical_json_sha256(_historical_observable_projection(inventory))
        == _HISTORICAL_OBSERVABLE_SHA256
    )


def test_development_adapter_retains_its_stricter_seed_policy() -> None:
    design = _build_design()
    unit = design.inventory.primary_units[0]

    prediction = execute_d7_seed_slot_primary(
        design,
        unit=unit,
        supplied_seed=12345,
    )
    assert prediction.supplied_seed == 12345
    assert prediction.to_dict()["seed_freeze_or_authorization_attested"] is False

    with pytest.raises(
        QualificationContractError,
        match="only permanently excluded seeds",
    ):
        execute_d7_confirmation_development_primary(
            design,
            unit=unit,
            development_seed=12345,
        )


@pytest.mark.parametrize(
    ("seed", "error"),
    [
        (True, TypeError),
        (np.bool_(False), TypeError),
        (1.5, TypeError),
        ("1", TypeError),
        (-1, ValueError),
        (2**63, ValueError),
    ],
)
def test_seed_slot_kernel_rejects_non_signed_int64_seeds(
    seed: object,
    error: type[Exception],
) -> None:
    design = _build_design()
    with pytest.raises(error):
        execute_d7_seed_slot_primary(
            design,
            unit=design.inventory.primary_units[0],
            supplied_seed=seed,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("seed", [0, np.int64(7), 2**63 - 1])
def test_seed_slot_kernel_accepts_the_full_signed_int64_domain(seed: int) -> None:
    design = _build_design()
    prediction = execute_d7_seed_slot_primary(
        design,
        unit=design.inventory.primary_units[0],
        supplied_seed=seed,
    )
    assert prediction.supplied_seed == int(seed)


def test_seed_slot_kernel_rejects_wrong_or_foreign_design_members() -> None:
    design = _build_design()
    unit = design.inventory.primary_units[0]

    with pytest.raises(TypeError, match="design must be"):
        execute_d7_seed_slot_primary(  # type: ignore[arg-type]
            object(),
            unit=unit,
            supplied_seed=0,
        )
    with pytest.raises(TypeError, match="unit must be"):
        execute_d7_seed_slot_primary(
            design,
            unit=object(),  # type: ignore[arg-type]
            supplied_seed=0,
        )
    with pytest.raises(QualificationContractError, match="not a member"):
        execute_d7_seed_slot_primary(
            design,
            unit=replace(unit, primary_unit_id="foreign-primary-unit"),
            supplied_seed=0,
        )


def test_seed_slot_prediction_records_are_kernel_factory_only() -> None:
    design = _build_design()
    prediction = execute_d7_seed_slot_primary(
        design,
        unit=design.inventory.primary_units[0],
        supplied_seed=0,
    )
    core = prediction.core_predictions[0]
    loop = prediction.loop_predictions[0]

    with pytest.raises(QualificationContractError, match="must be produced"):
        D7SeedSlotCorePrediction(
            core_cell_id=core.core_cell_id,
            field_graph_id=core.field_graph_id,
            field_estimate_fingerprint_sha256=(
                core.field_estimate_fingerprint_sha256
            ),
            prediction=core.prediction,
        )
    with pytest.raises(QualificationContractError, match="must be produced"):
        D7SeedSlotLoopPrediction(
            loop_cell_id=loop.loop_cell_id,
            field_graph_id=loop.field_graph_id,
            cycle_graph_id=loop.cycle_graph_id,
            loop_role=loop.loop_role,
            field_estimate_fingerprint_sha256=(
                loop.field_estimate_fingerprint_sha256
            ),
            prediction=loop.prediction,
        )
    with pytest.raises(QualificationContractError, match="must be produced"):
        replace(core, field_estimate_fingerprint_sha256="1" * 64)
    with pytest.raises(QualificationContractError, match="must be produced"):
        replace(loop, field_estimate_fingerprint_sha256="1" * 64)
    with pytest.raises(QualificationContractError, match="must be produced"):
        replace(prediction, supplied_seed=1)
