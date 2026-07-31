from __future__ import annotations

from dataclasses import fields, replace

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
from spirallens.qualification.confirmation_execution_design import (
    D7ConfirmationStressTranslation,
)
from spirallens.qualification.confirmation_execution_kernel import (
    D7_SEED_SLOT_PREDICTION_KERNEL_ID,
    D7SeedSlotCorePrediction,
    D7SeedSlotLoopPrediction,
    D7SeedSlotPrimaryPrediction,
    _CORE_FACTORY_TOKEN,
    _D7SeedSlotPrimaryRuntimeHandoff,
    _PRIMARY_FACTORY_TOKEN,
    _RUNTIME_HANDOFF_FACTORY_TOKEN,
    _execute_d7_seed_slot_primary_runtime,
    execute_d7_seed_slot_primary,
)
from spirallens.qualification.protocol import LoopRole
from spirallens.synthetic import spectral_moment_confirmation
from spirallens.synthetic.cartesian_fourier_domain_phantom import (
    CartesianFourierEstimatorInputs,
)
from spirallens.synthetic.spectral_moment_confirmation import (
    SpectralMomentConfirmationGenerator,
    SpectralMomentConfirmationSpec,
    SpectralMomentPreparedCase,
    SpectralMomentPreparedBundle,
)

_HISTORICAL_OBSERVABLE_SHA256 = (
    "c05d69597ed9309c087a14d23d6ea5982fb470cb04d3e8d992a30d85ae35b3b0"
)


def _rebuild_handoff(
    runtime: _D7SeedSlotPrimaryRuntimeHandoff,
    **changes: object,
) -> _D7SeedSlotPrimaryRuntimeHandoff:
    values = {field.name: getattr(runtime, field.name) for field in fields(runtime)}
    values.update(changes)
    return _D7SeedSlotPrimaryRuntimeHandoff(
        _factory_token=_RUNTIME_HANDOFF_FACTORY_TOKEN,
        **values,  # type: ignore[arg-type]
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
                        "max": (item.prediction.max_abs_edge_increment_radians),
                        "residual": (item.prediction.nearest_integer_residual_cycles),
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


def test_private_runtime_handoff_preserves_public_prediction_semantics() -> None:
    design = _build_design()
    unit = design.inventory.primary_units[0]
    runtime = _execute_d7_seed_slot_primary_runtime(
        design,
        unit=unit,
        supplied_seed=12345,
    )
    public = execute_d7_seed_slot_primary(
        design,
        unit=unit,
        supplied_seed=12345,
    )

    assert isinstance(runtime, _D7SeedSlotPrimaryRuntimeHandoff)
    assert runtime.prediction.to_dict() == public.to_dict()
    assert runtime.prediction.fingerprint_sha256 == public.fingerprint_sha256
    with pytest.raises(QualificationContractError, match="must be produced"):
        replace(runtime, spec=runtime.spec)


def test_private_runtime_handoff_accepts_the_exact_retained_objects() -> None:
    design = _build_design()
    runtime = _execute_d7_seed_slot_primary_runtime(
        design,
        unit=design.inventory.primary_units[0],
        supplied_seed=12345,
    )

    rebuilt = _rebuild_handoff(runtime)

    assert all(
        getattr(rebuilt, field.name) is getattr(runtime, field.name)
        for field in fields(runtime)
    )
    assert rebuilt.stress_translation is design.stress_translation
    assert type(rebuilt.stress_translation) is D7ConfirmationStressTranslation


def test_private_runtime_handoff_materializes_and_carries_no_oracle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_oracle(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("private runtime handoff must not construct an oracle")

    monkeypatch.setattr(
        spectral_moment_confirmation,
        "_oracle_truth",
        forbidden_oracle,
    )
    design = _build_design()
    runtime = _execute_d7_seed_slot_primary_runtime(
        design,
        unit=design.inventory.primary_units[0],
        supplied_seed=12345,
    )

    assert {field.name for field in fields(runtime)} == {
        "prediction",
        "unit",
        "stress_translation",
        "spec",
        "prepared_case",
        "estimator_inputs",
        "graph_input",
        "primary_execution",
        "offcore_execution",
        "field_estimates",
        "blind_core_inputs",
        "blind_loop_inputs",
        "core_policy",
        "loop_policy",
    }
    retained_objects = (
        runtime.prediction,
        runtime.unit,
        runtime.stress_translation,
        runtime.spec,
        runtime.prepared_case,
        runtime.estimator_inputs,
        runtime.graph_input,
        runtime.primary_execution,
        runtime.offcore_execution,
        runtime.core_policy,
        runtime.loop_policy,
        *(item for _, item in runtime.field_estimates),
        *(item for _, item in runtime.blind_core_inputs),
        *(item for _, item in runtime.blind_loop_inputs),
    )
    assert all(not hasattr(item, "oracle_truth") for item in retained_objects)
    assert runtime.prediction.to_dict()["oracle_truth_record_materialized"] is False


def test_private_runtime_handoff_rejects_subclassed_prepared_case() -> None:
    class OracleCarryingPreparedCase(SpectralMomentPreparedCase):
        __slots__ = ("oracle_truth",)

    design = _build_design()
    runtime = _execute_d7_seed_slot_primary_runtime(
        design,
        unit=design.inventory.primary_units[0],
        supplied_seed=12345,
    )
    original_case = runtime.prepared_case
    subclass_case = OracleCarryingPreparedCase(
        case_id=original_case.case_id,
        spec_receipt_sha256=original_case.spec_receipt_sha256,
        estimator_inputs=original_case.estimator_inputs,
    )
    object.__setattr__(subclass_case, "oracle_truth", object())

    with pytest.raises(TypeError, match="prepared_case must be"):
        _rebuild_handoff(runtime, prepared_case=subclass_case)


def test_private_runtime_handoff_rejects_a_mixed_prepared_case() -> None:
    design = _build_design()
    runtime = _execute_d7_seed_slot_primary_runtime(
        design,
        unit=design.inventory.primary_units[0],
        supplied_seed=12345,
    )
    other_case_id = next(
        unit.case_id
        for unit in design.inventory.primary_units
        if unit.case_id != runtime.unit.case_id
    )
    mixed_case = (
        SpectralMomentConfirmationGenerator().prepare(runtime.spec).case(other_case_id)
    )

    with pytest.raises(QualificationContractError, match="exact spec and unit case"):
        _rebuild_handoff(runtime, prepared_case=mixed_case)


def test_private_runtime_handoff_rejects_an_oracle_carrying_subclass() -> None:
    class OracleCarryingEstimatorInputs(CartesianFourierEstimatorInputs):
        __slots__ = ("oracle_truth",)

    design = _build_design()
    runtime = _execute_d7_seed_slot_primary_runtime(
        design,
        unit=design.inventory.primary_units[0],
        supplied_seed=12345,
    )
    base_inputs = runtime.estimator_inputs
    subclass_inputs = OracleCarryingEstimatorInputs(
        **{
            field.name: getattr(base_inputs, field.name)
            for field in fields(base_inputs)
        }
    )
    object.__setattr__(subclass_inputs, "oracle_truth", object())

    with pytest.raises(TypeError, match="estimator_inputs must be"):
        _rebuild_handoff(runtime, estimator_inputs=subclass_inputs)


def test_private_runtime_handoff_rejects_subclassed_prediction_children() -> None:
    class OracleCarryingCorePrediction(D7SeedSlotCorePrediction):
        __slots__ = ("oracle_truth",)

    design = _build_design()
    runtime = _execute_d7_seed_slot_primary_runtime(
        design,
        unit=design.inventory.primary_units[0],
        supplied_seed=12345,
    )
    original_core = runtime.prediction.core_predictions[0]
    subclass_core = OracleCarryingCorePrediction(
        _factory_token=_CORE_FACTORY_TOKEN,
        core_cell_id=original_core.core_cell_id,
        field_graph_id=original_core.field_graph_id,
        field_estimate_fingerprint_sha256=(
            original_core.field_estimate_fingerprint_sha256
        ),
        prediction=original_core.prediction,
    )
    object.__setattr__(subclass_core, "oracle_truth", object())
    forged_prediction = D7SeedSlotPrimaryPrediction(
        _factory_token=_PRIMARY_FACTORY_TOKEN,
        primary_unit_id=runtime.prediction.primary_unit_id,
        seed_slot_id=runtime.prediction.seed_slot_id,
        supplied_seed=runtime.prediction.supplied_seed,
        spec_receipt_sha256=runtime.prediction.spec_receipt_sha256,
        estimator_input_fingerprint_sha256=(
            runtime.prediction.estimator_input_fingerprint_sha256
        ),
        graph_input_fingerprint_sha256=(
            runtime.prediction.graph_input_fingerprint_sha256
        ),
        primary_execution_fingerprint_sha256=(
            runtime.prediction.primary_execution_fingerprint_sha256
        ),
        offcore_execution_fingerprint_sha256=(
            runtime.prediction.offcore_execution_fingerprint_sha256
        ),
        core_predictions=(
            subclass_core,
            *runtime.prediction.core_predictions[1:],
        ),
        loop_predictions=runtime.prediction.loop_predictions,
    )

    with pytest.raises(TypeError, match="children and sealed predictions"):
        _rebuild_handoff(runtime, prediction=forged_prediction)


def test_private_runtime_handoff_rejects_mixed_seed_spec_and_runtime() -> None:
    design = _build_design()
    runtime = _execute_d7_seed_slot_primary_runtime(
        design,
        unit=design.inventory.primary_units[0],
        supplied_seed=12345,
    )
    mixed_spec = replace(runtime.spec, seed=12346)
    forged_prediction = D7SeedSlotPrimaryPrediction(
        _factory_token=_PRIMARY_FACTORY_TOKEN,
        primary_unit_id=runtime.prediction.primary_unit_id,
        seed_slot_id=runtime.prediction.seed_slot_id,
        supplied_seed=mixed_spec.seed,
        spec_receipt_sha256=mixed_spec.receipt_sha256,
        estimator_input_fingerprint_sha256=(
            runtime.prediction.estimator_input_fingerprint_sha256
        ),
        graph_input_fingerprint_sha256=(
            runtime.prediction.graph_input_fingerprint_sha256
        ),
        primary_execution_fingerprint_sha256=(
            runtime.prediction.primary_execution_fingerprint_sha256
        ),
        offcore_execution_fingerprint_sha256=(
            runtime.prediction.offcore_execution_fingerprint_sha256
        ),
        core_predictions=runtime.prediction.core_predictions,
        loop_predictions=runtime.prediction.loop_predictions,
    )

    with pytest.raises(QualificationContractError, match="exact spec and unit case"):
        _rebuild_handoff(
            runtime,
            prediction=forged_prediction,
            spec=mixed_spec,
        )


@pytest.mark.parametrize(
    ("axis_id", "replacement_level"),
    [
        ("boundary", "wide"),
        ("state-geometry-warp", "stressed"),
        ("structured-observation-perturbation", "stressed"),
    ],
)
def test_private_runtime_handoff_rejects_mixed_unit_stress_assignments(
    axis_id: str,
    replacement_level: str,
) -> None:
    design = _build_design()
    unit = design.inventory.primary_units[0]
    runtime = _execute_d7_seed_slot_primary_runtime(
        design,
        unit=unit,
        supplied_seed=12345,
    )
    mixed_unit = replace(
        unit,
        stress_assignments=tuple(
            replace(assignment, level=replacement_level)
            if assignment.axis_id == axis_id
            else assignment
            for assignment in unit.stress_assignments
        ),
    )

    with pytest.raises(
        QualificationContractError,
        match="runtime objects differ from the unit stress assignments",
    ):
        _rebuild_handoff(runtime, unit=mixed_unit)


def test_private_runtime_handoff_has_complete_prediction_input_joins() -> None:
    design = _build_design()
    runtime = _execute_d7_seed_slot_primary_runtime(
        design,
        unit=design.inventory.primary_units[0],
        supplied_seed=12345,
    )
    estimates = dict(runtime.field_estimates)
    core_inputs = dict(runtime.blind_core_inputs)
    loop_inputs = dict(runtime.blind_loop_inputs)
    core_predictions = {
        item.core_cell_id: item for item in runtime.prediction.core_predictions
    }
    loop_predictions = {
        item.loop_cell_id: item for item in runtime.prediction.loop_predictions
    }

    assert tuple(estimates) == tuple(
        sorted({item.field_graph_id for item in runtime.prediction.core_predictions})
    )
    assert tuple(core_inputs) == tuple(sorted(core_predictions))
    assert tuple(loop_inputs) == tuple(sorted(loop_predictions))
    assert len(estimates) == 3
    assert len(core_inputs) == 3
    assert len(loop_inputs) == 18
    assert runtime.primary_execution.graph_input is runtime.graph_input
    assert runtime.offcore_execution.graph_input is runtime.graph_input

    for cell_id, blind_input in core_inputs.items():
        sealed = core_predictions[cell_id]
        estimate = estimates[sealed.field_graph_id]
        assert estimate.estimator_inputs is runtime.estimator_inputs
        assert (
            blind_input.field_estimate_fingerprint_sha256 == estimate.fingerprint_sha256
        )
        assert (
            blind_input.fingerprint_sha256
            == sealed.prediction.blind_input_fingerprint_sha256
        )
        assert (
            sealed.prediction.policy_fingerprint_sha256
            == runtime.core_policy.fingerprint_sha256
        )

    execution_by_role = {
        LoopRole.PRIMARY_BOUNDARY: runtime.primary_execution,
        LoopRole.OFFCORE_CONTROL: runtime.offcore_execution,
    }
    for cell_id, blind_input in loop_inputs.items():
        sealed = loop_predictions[cell_id]
        estimate = estimates[sealed.field_graph_id]
        execution = execution_by_role[sealed.loop_role]
        cycle_graph = next(
            graph
            for graph in execution.cycle_graphs
            if graph.specification.spec_id == sealed.cycle_graph_id
        )
        assert estimate.estimator_inputs is runtime.estimator_inputs
        assert (
            blind_input.field_estimate_fingerprint_sha256 == estimate.fingerprint_sha256
        )
        assert (
            blind_input.cycle_graph_fingerprint_sha256 == cycle_graph.fingerprint_sha256
        )
        assert (
            blind_input.fingerprint_sha256
            == sealed.prediction.blind_input_fingerprint_sha256
        )
        assert (
            sealed.prediction.policy_fingerprint_sha256
            == runtime.loop_policy.fingerprint_sha256
        )


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
            observed.prediction.prediction_class is expected.prediction.prediction_class
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
            observed.prediction.prediction_class is expected.prediction.prediction_class
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
            field_estimate_fingerprint_sha256=(core.field_estimate_fingerprint_sha256),
            prediction=core.prediction,
        )
    with pytest.raises(QualificationContractError, match="must be produced"):
        D7SeedSlotLoopPrediction(
            loop_cell_id=loop.loop_cell_id,
            field_graph_id=loop.field_graph_id,
            cycle_graph_id=loop.cycle_graph_id,
            loop_role=loop.loop_role,
            field_estimate_fingerprint_sha256=(loop.field_estimate_fingerprint_sha256),
            prediction=loop.prediction,
        )
    with pytest.raises(QualificationContractError, match="must be produced"):
        replace(core, field_estimate_fingerprint_sha256="1" * 64)
    with pytest.raises(QualificationContractError, match="must be produced"):
        replace(loop, field_estimate_fingerprint_sha256="1" * 64)
    with pytest.raises(QualificationContractError, match="must be produced"):
        replace(prediction, supplied_seed=1)
