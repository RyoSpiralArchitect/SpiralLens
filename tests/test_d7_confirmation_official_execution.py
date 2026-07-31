from __future__ import annotations

import inspect
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_d7_confirmation_execution_design import _build_design

from spirallens.core.canonical import canonical_json_sha256
from spirallens.qualification.common import QualificationContractError
from spirallens.qualification import confirmation_attempt_records as ar
from spirallens.qualification import confirmation_fused_start as fused_start
from spirallens.qualification.confirmation_attempt_authority import (
    D7AuthorityArtifactBinding,
    D7OfficialSeed,
    D7OfficialSeedInventoryRecord,
)
from spirallens.qualification.confirmation_c1 import (
    D7C1SeedFreeSourceSet,
    D7_C1_BUNDLE_REPOSITORY_PATH,
)
from spirallens.qualification.confirmation_execution_design import (
    D7_CONFIRMATION_PRIMARY_UNIT_COUNT,
    D7_CONFIRMATION_SEED_SLOT_IDS,
    _build_recorded_c1_d7_confirmation_execution_design,
)
from spirallens.qualification.confirmation_official_execution import (
    D7_OFFICIAL_FUSED_DESCRIPTOR_REPOSITORY_PATH,
    D7_OFFICIAL_PARENT_PROTOCOL_REPOSITORY_PATH,
    D7_OFFICIAL_PARENT_PROTOCOL_SHA256,
    D7_OFFICIAL_PRODUCER_MODULE,
    D7_OFFICIAL_PRODUCER_QUALNAME,
    D7_RECORDED_C1_AGGREGATION_APPLICATION_SHA256,
    D7_RECORDED_C1_CANONICAL_SHA256,
    D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_SHA256,
    D7_RECORDED_C1_LOCKED_AGGREGATION_SHA256,
)
from spirallens.qualification import confirmation_official_execution as official
from spirallens.qualification.persistence import load_qualification_protocol


_ROOT = Path(__file__).resolve().parents[1]


def test_official_producer_is_one_exact_zero_argument_function() -> None:
    producer = official.produce_d7_official_result

    assert type(producer).__name__ == "function"
    assert producer.__module__ == D7_OFFICIAL_PRODUCER_MODULE
    assert producer.__qualname__ == D7_OFFICIAL_PRODUCER_QUALNAME
    assert producer.__closure__ is None
    assert tuple(inspect.signature(producer).parameters) == ()
    assert official._require_official_producer_identity(producer) is producer


def test_spoofed_module_and_qualname_cannot_substitute_for_producer() -> None:
    def substitute() -> None:
        return None

    substitute.__module__ = D7_OFFICIAL_PRODUCER_MODULE
    substitute.__qualname__ = D7_OFFICIAL_PRODUCER_QUALNAME

    with pytest.raises(QualificationContractError, match="identity differs"):
        official._require_official_producer_identity(substitute)


def test_official_fused_path_rejects_spoofed_and_ordinary_callbacks() -> None:
    official_path = _ROOT / D7_OFFICIAL_FUSED_DESCRIPTOR_REPOSITORY_PATH
    snapshot = SimpleNamespace(
        repository_root=_ROOT,
        descriptor_path=official_path,
    )

    def same_name_spoof() -> None:
        return None

    same_name_spoof.__module__ = D7_OFFICIAL_PRODUCER_MODULE
    same_name_spoof.__qualname__ = D7_OFFICIAL_PRODUCER_QUALNAME

    def ordinary_callback() -> None:
        return None

    fused_start._require_descriptor_bound_official_producer(
        snapshot,
        official.produce_d7_official_result,
    )
    for substitute in (same_name_spoof, ordinary_callback):
        with pytest.raises(QualificationContractError, match="identity differs"):
            fused_start._require_descriptor_bound_official_producer(
                snapshot,
                substitute,
            )


def test_nonofficial_fused_path_retains_generic_callback_compatibility() -> None:
    snapshot = SimpleNamespace(
        repository_root=_ROOT,
        descriptor_path=_ROOT / "experiments/qualification/test/launch.json",
    )

    def ordinary_callback() -> None:
        return None

    fused_start._require_descriptor_bound_official_producer(
        snapshot,
        ordinary_callback,
    )


def test_absent_fixed_descriptor_fails_before_c1_or_generator_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def forbidden(*args: object, **kwargs: object) -> None:
        calls.append("forbidden")
        raise AssertionError("post-descriptor work was reached")

    monkeypatch.setattr(official, "_repository_root", lambda: tmp_path)
    monkeypatch.setattr(official, "_recorded_c1_design", forbidden)
    monkeypatch.setattr(
        official.fused_authority,
        "load_d7_fused_authority_snapshot",
        forbidden,
    )
    monkeypatch.setattr(official, "SpectralMomentConfirmationGenerator", forbidden)

    with pytest.raises(
        QualificationContractError,
        match="official D7 fused descriptor is absent",
    ):
        official.produce_d7_official_result()

    assert calls == []
    assert official._official_descriptor_path(tmp_path) == (
        tmp_path / D7_OFFICIAL_FUSED_DESCRIPTOR_REPOSITORY_PATH
    )


def test_committed_c1_reconstructs_the_exact_typed_design_and_pinned_bodies() -> None:
    source = (_ROOT / D7_C1_BUNDLE_REPOSITORY_PATH).read_bytes()
    c1 = D7C1SeedFreeSourceSet.from_canonical_bytes(
        source,
        expected_sha256=D7_RECORDED_C1_CANONICAL_SHA256,
    )
    document = c1.to_dict()
    components = document["components"]
    implementation = components["implementation_registry"]
    aggregation = components["aggregation_application"]
    recorded = components["seed_free_execution_design"]["body"][
        "seed_free_execution_design"
    ]
    parent = load_qualification_protocol(
        _ROOT / D7_OFFICIAL_PARENT_PROTOCOL_REPOSITORY_PATH,
        expected_source_sha256=D7_OFFICIAL_PARENT_PROTOCOL_SHA256,
        expected_canonical_sha256=D7_OFFICIAL_PARENT_PROTOCOL_SHA256,
    )

    rebuilt = _build_recorded_c1_d7_confirmation_execution_design(
        parent_protocol=parent,
        recorded_document=recorded,
    )

    assert rebuilt.to_dict() == recorded
    assert canonical_json_sha256(implementation["body"]) == (
        D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_SHA256
    )
    assert implementation["canonical_sha256"] == (
        D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_SHA256
    )
    assert canonical_json_sha256(aggregation["body"]) == (
        D7_RECORDED_C1_AGGREGATION_APPLICATION_SHA256
    )
    assert aggregation["canonical_sha256"] == (
        D7_RECORDED_C1_AGGREGATION_APPLICATION_SHA256
    )
    assert canonical_json_sha256(aggregation["body"]["locked_aggregation"]) == (
        D7_RECORDED_C1_LOCKED_AGGREGATION_SHA256
    )


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("artifact_contract_id", "spirallens.substituted-registry.v0.1"),
        ("canonical_sha256", "c" * 64),
        ("byte_count", 5303),
    ),
)
def test_c1_implementation_registry_binding_substitution_is_rejected(
    field: str,
    replacement: object,
) -> None:
    binding = D7AuthorityArtifactBinding(
        artifact_role="implementation-registry",
        artifact_contract_id=(
            official.D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_SCHEMA_VERSION
        ),
        canonical_sha256=D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_SHA256,
        byte_count=(official.D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_BYTE_COUNT),
    )
    official._require_exact_artifact_binding(
        binding,
        role="implementation-registry",
        contract_id=(official.D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_SCHEMA_VERSION),
        canonical_sha256=D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_SHA256,
        byte_count=(official.D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_BYTE_COUNT),
    )

    substituted = replace(binding, **{field: replacement})
    with pytest.raises(QualificationContractError, match="binding differs"):
        official._require_exact_artifact_binding(
            substituted,
            role="implementation-registry",
            contract_id=(
                official.D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_SCHEMA_VERSION
            ),
            canonical_sha256=D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_SHA256,
            byte_count=(official.D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_BYTE_COUNT),
        )


def test_global_prediction_barrier_seals_all_64_without_oracle_materialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = _build_design()
    calls: list[tuple[str, int]] = []

    class FakeHandoff:
        def __init__(self, unit: object) -> None:
            self.unit = unit

    class ForbiddenGenerator:
        def __init__(self) -> None:
            raise AssertionError("oracle generator crossed the sealing barrier")

    def fake_execute(
        received_design: object,
        *,
        unit: object,
        supplied_seed: int,
    ) -> FakeHandoff:
        assert received_design is design
        calls.append((unit.primary_unit_id, supplied_seed))
        return FakeHandoff(unit)

    monkeypatch.setattr(
        official,
        "_D7SeedSlotPrimaryRuntimeHandoff",
        FakeHandoff,
    )
    monkeypatch.setattr(
        official,
        "_execute_d7_seed_slot_primary_runtime",
        fake_execute,
    )
    monkeypatch.setattr(
        official,
        "SpectralMomentConfirmationGenerator",
        ForbiddenGenerator,
    )
    seeds = {
        D7_CONFIRMATION_SEED_SLOT_IDS[0]: 700001,
        D7_CONFIRMATION_SEED_SLOT_IDS[1]: 700002,
    }

    handoffs = official._seal_all_primary_handoffs(
        design,
        seed_by_slot=seeds,
    )

    assert len(handoffs) == D7_CONFIRMATION_PRIMARY_UNIT_COUNT
    assert len(calls) == D7_CONFIRMATION_PRIMARY_UNIT_COUNT
    assert tuple(item[0] for item in calls) == tuple(
        item.primary_unit_id for item in design.inventory.primary_units
    )
    assert {item[1] for item in calls} == set(seeds.values())


def test_paired_case_identity_is_seed_slot_independent_and_exactly_two_way() -> None:
    design = _build_design()
    pairs: dict[str, list[object]] = {}
    for unit in design.inventory.primary_units:
        pairs.setdefault(official._paired_case_id(unit), []).append(unit)

    assert len(pairs) == 32
    assert {len(units) for units in pairs.values()} == {2}
    assert {
        tuple(sorted(unit.seed_slot_id for unit in units)) for units in pairs.values()
    } == {D7_CONFIRMATION_SEED_SLOT_IDS}
    for units in pairs.values():
        left, right = units
        assert left.parent_control_id == right.parent_control_id
        assert left.case_id == right.case_id
        assert left.case_semantics == right.case_semantics
        assert left.stress_assignments == right.stress_assignments


def test_gate_manifest_definitions_use_canonical_component_order() -> None:
    gate_ids = tuple(item["gate_id"] for item in official._gate_definitions())

    assert gate_ids == tuple(sorted(gate_ids))
    assert gate_ids == (
        "all-primary-units-pass",
        "full-coverage",
        "worst-case-required-strata-pass",
        "zero-abstention",
    )


def _test_only_inventory() -> D7OfficialSeedInventoryRecord:
    return D7OfficialSeedInventoryRecord(
        inventory_id="d7-test-only-unpublished-seed-inventory-v0-1",
        development_exclusion_registry_binding=D7AuthorityArtifactBinding(
            artifact_role="development-exclusion-registry",
            artifact_contract_id="spirallens.test-development-exclusion.v0.1",
            canonical_sha256="a" * 64,
            byte_count=1,
        ),
        parent_selection_exclusion_registry_binding=D7AuthorityArtifactBinding(
            artifact_role="parent-selection-exclusion-registry",
            artifact_contract_id="spirallens.test-parent-exclusion.v0.1",
            canonical_sha256="b" * 64,
            byte_count=1,
        ),
        seeds=(
            D7OfficialSeed(
                seed_slot_id=D7_CONFIRMATION_SEED_SLOT_IDS[0],
                seed=700001,
            ),
            D7OfficialSeed(
                seed_slot_id=D7_CONFIRMATION_SEED_SLOT_IDS[1],
                seed=700002,
            ),
        ),
    )


def test_test_only_full_execution_is_deterministic_and_writes_no_artifact() -> None:
    descriptor_path = _ROOT / D7_OFFICIAL_FUSED_DESCRIPTOR_REPOSITORY_PATH
    assert not descriptor_path.exists()
    experiment_root = descriptor_path.parent
    before = {
        item.relative_to(experiment_root): item.read_bytes()
        for item in experiment_root.rglob("*")
        if item.is_file()
    }
    design = _build_design()
    inventory = _test_only_inventory()
    full_inventory = official.build_d7_official_full_inventory_document(
        design=design,
        official_seed_inventory=inventory,
    )
    aggregation = official.build_d7_official_aggregation_document(
        implementation_registry_sha256=(D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_SHA256)
    )
    context = official._D7OfficialProducerContext(
        design=design,
        official_seed_inventory=inventory,
        replay_target_sha256="0" * 64,
        full_inventory_sha256=canonical_json_sha256(full_inventory),
        aggregation_sha256=canonical_json_sha256(aggregation),
        gate_manifest_sha256=canonical_json_sha256(aggregation["gate_manifest"]),
        _factory_token=official._CONTEXT_FACTORY_TOKEN,
    )

    first = official._execute_official_context(context)
    second = official._execute_official_context(context)

    assert first.result_payload.state is ar.D7ScientificResultState.PASS
    assert first.result_payload.reason_codes == ()
    assert tuple(len(item.records) for item in first.ordered_values[:-1]) == (
        1344,
        192,
        1152,
        64,
        6,
        4,
    )
    assert tuple(item.canonical_sha256 for item in first.ordered_values) == tuple(
        item.canonical_sha256 for item in second.ordered_values
    )
    assert aggregation["gate_manifest"]["gate_order"] == [
        item.gate_id for item in first.aggregate_gates.records
    ]
    after = {
        item.relative_to(experiment_root): item.read_bytes()
        for item in experiment_root.rglob("*")
        if item.is_file()
    }
    assert after == before
    assert not descriptor_path.exists()
