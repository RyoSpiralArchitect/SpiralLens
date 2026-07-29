from __future__ import annotations

import json
import subprocess
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest

import spirallens.qualification.preparation as qualification_preparation
import spirallens.qualification.runner as qualification_runner
from spirallens.instrument_contracts import load_hypothesis_registry
from spirallens.qualification import (
    CLOSED_D0_D5_KNOWN_SEED_EXCLUSION_REGISTRY,
    CLOSED_D0_D5_KNOWN_SEED_EXCLUSION_SCHEMA_VERSION,
    CLOSED_D0_D5_PRIMARY_UNIT_COUNT,
    CLOSED_D0_D5_PROTOCOL_FACTORY_ID,
    CLOSED_D0_D5_PROTOCOL_ID,
    CLOSED_D0_D5_SELECTION_SEED_COUNT,
    ClosedD0D5KnownSeedExclusionRegistry,
    QualificationContractError,
    build_current_qualification_engine_binding,
    prepare_closed_d0_d5_selection_protocol,
    validate_closed_d0_d5_selection_protocol,
    verify_closed_d0_d5_preseed_source_readiness,
)
from spirallens.qualification.persistence import LoadedQualificationProtocol
from spirallens.qualification.preparation import (
    CLOSED_D0_D5_OFFICIAL_EXECUTABLE_PATHS,
    build_closed_d0_d5_selection_protocol,
    load_closed_d0_d5_preseed_readiness_artifact,
)
from spirallens.qualification.protocol import (
    EngineBinding,
    ModuleDigest,
    NumericStressLevel,
    QualificationProtocol,
    RegistryBinding,
)
from spirallens.qualification.runner import (
    REQUIRED_ENGINE_MODULES,
    module_source_sha256,
)
from spirallens.qualification.source_binding import QualificationSourceBindingError
from spirallens.referents import canonical_f0_f4_referent_contracts
from spirallens.synthetic.cartesian_fourier_domain_phantom import (
    CartesianFourierDomainGenerator,
)

REPOSITORY = Path(__file__).resolve().parents[1]
TRACKED_REGISTRY = (
    REPOSITORY / "protocols" / "order_parameter_hypothesis_registry_v0_1.yaml"
)


def _engine() -> EngineBinding:
    return EngineBinding(
        repository="RyoSpiralArchitect/SpiralLens",
        commit="1" * 40,
        modules=(ModuleDigest("spirallens.qualification.runner", "2" * 64),),
    )


def _registry() -> RegistryBinding:
    return RegistryBinding(
        registry_source_sha256="3" * 64,
        registry_canonical_sha256="4" * 64,
        referent_canonical_sha256="5" * 64,
    )


def _protocol() -> QualificationProtocol:
    return build_closed_d0_d5_selection_protocol(
        engine=_engine(),
        registry=_registry(),
        selection_seeds=(400001, 400002),
    )


def _git(repository: Path, *arguments: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
    ).stdout


def _readiness_repository(tmp_path: Path) -> tuple[Path, str, Path]:
    repository = tmp_path / "repository"
    module_path = repository / "src" / "spirallens" / "qualification" / "demo.py"
    registry_path = repository / "protocols" / "registry.yaml"
    referent_path = repository / "protocols" / "referents.json"
    module_path.parent.mkdir(parents=True)
    registry_path.parent.mkdir(parents=True)
    module_path.write_bytes(b'"""Seed-free readiness test module."""\n\nVALUE = 7\n')
    registry_path.write_bytes(TRACKED_REGISTRY.read_bytes())
    loaded_registry = load_hypothesis_registry(registry_path)
    referents = canonical_f0_f4_referent_contracts(loaded_registry.canonical_sha256)
    referent_path.write_bytes(referents.canonical_bytes)
    for repository_path in CLOSED_D0_D5_OFFICIAL_EXECUTABLE_PATHS:
        script_path = repository / repository_path
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_bytes(
            f'#!/usr/bin/env python3\n"""Test {repository_path}."""\n'.encode()
        )
    _git(repository, "init", "-q")
    _git(repository, "config", "user.name", "SpiralLens Test")
    _git(repository, "config", "user.email", "test@example.invalid")
    _git(repository, "add", ".")
    _git(repository, "commit", "-qm", "seed-free preparation sources")
    commit = _git(repository, "rev-parse", "HEAD").decode("ascii").strip()
    return repository, commit, module_path


def _preseed_path(repository: Path) -> Path:
    parent = repository / "artifacts"
    parent.mkdir(exist_ok=True)
    return parent / "preseed-readiness.json"


def test_closed_protocol_factory_has_exact_reviewed_cartesian_product() -> None:
    protocol = _protocol()

    assert CLOSED_D0_D5_PROTOCOL_FACTORY_ID.endswith(".v0.1")
    assert CLOSED_D0_D5_SELECTION_SEED_COUNT == 2
    assert protocol.protocol_id == CLOSED_D0_D5_PROTOCOL_ID
    assert len(protocol.expected_core_cells) == 192
    assert len(protocol.expected_cells) == 1152
    assert len(protocol.expected_strata) == 6

    primary_ids = {cell.primary_unit_id for cell in protocol.expected_core_cells}
    assert len(primary_ids) == CLOSED_D0_D5_PRIMARY_UNIT_COUNT == 64
    assert Counter(
        cell.primary_unit_id for cell in protocol.expected_core_cells
    ) == Counter({primary_id: 3 for primary_id in primary_ids})
    assert Counter(cell.primary_unit_id for cell in protocol.expected_cells) == Counter(
        {primary_id: 18 for primary_id in primary_ids}
    )
    assert all(
        len(stratum.primary_unit_ids) == 32 for stratum in protocol.expected_strata
    )
    assert {stratum.stratum_id for stratum in protocol.expected_strata} == {
        "stress.boundary.central",
        "stress.boundary.wide",
        "stress.state-geometry-warp.nominal",
        "stress.state-geometry-warp.stressed",
        "stress.structured-observation-perturbation.nominal",
        "stress.structured-observation-perturbation.stressed",
    }

    assert len({cell.core_cell_id for cell in protocol.expected_core_cells}) == 192
    assert len({cell.cell_id for cell in protocol.expected_cells}) == 1152
    assert {graph.graph_id for graph in protocol.graphs.field_estimation} == {
        "a-mutual",
        "a-radius",
        "a-shared",
    }
    assert {graph.graph_id for graph in protocol.graphs.cycle_construction} == {
        "b-mutual",
        "b-radius",
        "b-shared",
    }
    assert protocol.evaluation_design.to_dict() == {
        "declared_seed_block_count": 2,
        "matched_control_count": 4,
        "paired_stress_variant_count_per_seed_control": 8,
        "execution_variant_count": 64,
        "d2_unique_scientific_input_unit_count": 32,
        "loop_execution_variant_count": 64,
        "paired_repeated_measure_block_unit": "selection-seed-block",
        "controls_are_matched": True,
        "stress_variants_are_paired_repeated_measures": True,
        "boundary_variants_are_d2_repeated_measures": True,
        "execution_variants_are_independent_replicates": False,
        "seed_block_independence_proved": False,
        "inferential_sample_size_claimed": False,
    }
    assert protocol.gate_claim_scopes == {
        "d0": "engine-and-protocol-contracts",
        "d1": "cartesian-surrogate-and-representation-development",
        "d2": "cartesian-surrogate-only",
        "d3": "cartesian-surrogate-and-representation-development",
        "d4": "cartesian-surrogate-only",
        "d5": "cartesian-surrogate-only",
    }


def test_closed_protocol_factory_fixes_numeric_stresses_and_boundaries() -> None:
    cartesian = _protocol().cartesian

    assert [
        (item.level, item.value) for item in cartesian.state_geometry_warp_levels
    ] == [
        ("nominal", 0.0),
        ("stressed", 0.1),
    ]
    assert [
        (item.level, item.value)
        for item in cartesian.structured_observation_perturbation_levels
    ] == [
        ("nominal", 0.0),
        ("stressed", 0.01),
    ]
    assert [
        (item.level, item.x_min, item.y_min, item.x_max, item.y_max)
        for item in cartesian.primary_boundaries
    ] == [
        ("central", 2, 2, 4, 4),
        ("wide", 1, 1, 5, 5),
    ]
    assert (
        cartesian.offcore_boundary.level,
        cartesian.offcore_boundary.x_min,
        cartesian.offcore_boundary.y_min,
        cartesian.offcore_boundary.x_max,
        cartesian.offcore_boundary.y_max,
    ) == ("offcore", 0, 0, 1, 1)


def test_closed_protocol_factory_keeps_all_scientific_promotions_false() -> None:
    protocol = _protocol()

    assert protocol.authority.to_dict() == {
        "pythia_access_authorized": False,
        "subject_data_access_authorized": False,
        "subject_execution_authorized": False,
        "semantic_labels_authorized": False,
        "integer_output_authorized": False,
        "p0_competitor_selection_authorized": False,
        "representation_d2_d5_transfer_authorized": False,
        "localized_core_loop_join_authorized": False,
        "synthetic_qualification_authorized": False,
    }


def test_known_seed_exclusion_registry_is_canonical_and_explicitly_nonproof() -> None:
    registry = CLOSED_D0_D5_KNOWN_SEED_EXCLUSION_REGISTRY

    assert registry.schema_version == CLOSED_D0_D5_KNOWN_SEED_EXCLUSION_SCHEMA_VERSION
    assert registry.seeds == (
        3,
        4,
        101,
        202,
        314159,
        314160,
        424242,
        424243,
    )
    assert json.loads(registry.canonical_bytes) == registry.to_dict()
    assert registry.canonical_sha256 == (
        "889029d616faad25d0ca5bdb12ba63daa44b2c3c0c624cea1f3740d9ca83aa6b"
    )
    assert registry.unseen_status == "external-attestation-required"
    assert registry.cryptographic_unseen_proof is False
    assert registry.scientific_claim_eligible is False


def test_known_seed_exclusion_registry_rejects_alternate_entries() -> None:
    with pytest.raises(ValueError, match="canonical development/exploratory seed set"):
        ClosedD0D5KnownSeedExclusionRegistry(
            registry_id="closed-d0-d5-known-development-seeds-v0-1",
            entries=((999, "alternate entry"),),
        )


@pytest.mark.parametrize(
    "known_seed",
    CLOSED_D0_D5_KNOWN_SEED_EXCLUSION_REGISTRY.seeds,
)
def test_closed_protocol_factory_rejects_every_known_seed(
    known_seed: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="known-seed exclusion.*external unopened-seed attestation",
    ):
        build_closed_d0_d5_selection_protocol(
            engine=_engine(),
            registry=_registry(),
            selection_seeds=(known_seed, 900001),
        )


@pytest.mark.parametrize(
    "seeds",
    [
        (),
        (1,),
        (1, 2, 3),
        (2, 1),
        (1, 1),
        (-1, 2),
        (1, 2**63),
    ],
)
def test_closed_protocol_factory_rejects_noncanonical_seed_family(
    seeds: tuple[int, ...],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        build_closed_d0_d5_selection_protocol(
            engine=_engine(),
            registry=_registry(),
            selection_seeds=seeds,
        )


def test_closed_protocol_factory_is_canonical_round_trip() -> None:
    protocol = _protocol()

    reconstructed = QualificationProtocol.from_dict(
        json.loads(protocol.canonical_bytes)
    )
    assert reconstructed == protocol
    assert reconstructed.canonical_bytes == protocol.canonical_bytes
    assert reconstructed.canonical_sha256 == protocol.canonical_sha256


def test_closed_protocol_validator_accepts_exact_factory_output() -> None:
    protocol = _protocol()

    assert validate_closed_d0_d5_selection_protocol(protocol) is protocol


def _mutated_closed_protocol(
    protocol: QualificationProtocol,
    mutation: str,
) -> QualificationProtocol:
    if mutation == "threshold":
        return replace(
            protocol,
            thresholds=replace(protocol.thresholds, branch_margin_rad=0.051),
        )
    if mutation == "field-graph":
        field_graphs = list(protocol.graphs.field_estimation)
        field_graphs[1] = replace(
            field_graphs[1],
            parameters=(("radius", 0.49),),
        )
        return replace(
            protocol,
            graphs=replace(
                protocol.graphs,
                field_estimation=tuple(field_graphs),
            ),
        )
    if mutation == "stress":
        return replace(
            protocol,
            cartesian=replace(
                protocol.cartesian,
                structured_observation_perturbation_levels=(
                    NumericStressLevel("nominal", 0.0),
                    NumericStressLevel("stressed", 0.02),
                ),
            ),
        )
    raise AssertionError(f"unknown mutation {mutation!r}")


@pytest.mark.parametrize(
    "mutation",
    ("threshold", "field-graph", "stress"),
)
def test_closed_protocol_validator_rejects_self_consistent_exact_mutations(
    mutation: str,
) -> None:
    mutated = _mutated_closed_protocol(_protocol(), mutation)
    round_tripped = QualificationProtocol.from_dict(json.loads(mutated.canonical_bytes))

    assert round_tripped == mutated
    assert round_tripped.protocol_id == CLOSED_D0_D5_PROTOCOL_ID
    with pytest.raises(ValueError, match="exact closed D0-D5 factory profile"):
        validate_closed_d0_d5_selection_protocol(round_tripped)


def test_generic_protocol_contract_already_rejects_coverage_weakening() -> None:
    protocol = _protocol()

    with pytest.raises(ValueError, match="minimum_recall must equal 1.0"):
        replace(protocol.coverage_policy, minimum_recall=0.99)


def test_closed_protocol_factory_does_not_generate_phantom_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_generate(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("preparation must not generate selection values")

    monkeypatch.setattr(
        CartesianFourierDomainGenerator,
        "generate",
        forbidden_generate,
    )
    protocol = _protocol()
    assert len(protocol.selection.seeds) == 2


def test_current_engine_binding_covers_exact_runner_source_closure() -> None:
    binding = build_current_qualification_engine_binding(engine_commit="a" * 40)

    assert tuple(item.module for item in binding.modules) == tuple(
        sorted(REQUIRED_ENGINE_MODULES)
    )
    assert {item.module: item.sha256 for item in binding.modules} == {
        module: module_source_sha256(module)
        for module in sorted(REQUIRED_ENGINE_MODULES)
    }
    assert "spirallens.qualification.preparation" in {
        item.module for item in binding.modules
    }


def test_seed_free_readiness_precedes_supplier_and_returns_bindable_receipt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository, commit, _module_path = _readiness_repository(tmp_path)
    monkeypatch.setattr(
        qualification_runner,
        "REQUIRED_ENGINE_MODULES",
        ("spirallens.qualification.demo",),
    )
    supplier_calls: list[str] = []
    chronology: list[str] = []
    preseed_path = _preseed_path(repository)
    original_load = (
        qualification_preparation.load_closed_d0_d5_preseed_readiness_artifact
    )

    def observed_load(*args: object, **kwargs: object):
        loaded = original_load(*args, **kwargs)
        chronology.append("canonical-roundtrip-loaded")
        return loaded

    monkeypatch.setattr(
        qualification_preparation,
        "load_closed_d0_d5_preseed_readiness_artifact",
        observed_load,
    )

    def supply() -> tuple[int, ...]:
        assert preseed_path.is_file()
        assert chronology == ["canonical-roundtrip-loaded"]
        supplier_calls.append("called")
        return (400001, 400002)

    protocol, receipt = prepare_closed_d0_d5_selection_protocol(
        engine_commit=commit,
        repository_root=repository,
        registry_path="protocols/registry.yaml",
        referent_path="protocols/referents.json",
        preseed_readiness_path=preseed_path,
        selection_seed_supplier=supply,
    )

    assert supplier_calls == ["called"]
    assert receipt.engine == protocol.engine
    assert receipt.registry == protocol.registry
    assert receipt.head_commit == commit
    assert len(receipt.canonical_sha256) == 64
    assert receipt.referent_contracts.source_sha256 == (
        receipt.registry.referent_canonical_sha256
    )
    assert protocol.preseed_readiness is not None
    loaded_preseed = load_closed_d0_d5_preseed_readiness_artifact(
        preseed_path,
        expected_source_sha256=protocol.preseed_readiness.artifact_source_sha256,
        expected_canonical_sha256=(
            protocol.preseed_readiness.artifact_canonical_sha256
        ),
    )
    assert loaded_preseed.binding == protocol.preseed_readiness
    assert (
        validate_closed_d0_d5_selection_protocol(
            protocol,
            require_persisted_preseed_readiness=True,
        )
        is protocol
    )


def test_preseed_roundtrip_failure_leaves_supplier_unopened(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository, commit, _module_path = _readiness_repository(tmp_path)
    monkeypatch.setattr(
        qualification_runner,
        "REQUIRED_ENGINE_MODULES",
        ("spirallens.qualification.demo",),
    )
    preseed_path = _preseed_path(repository)
    supplier_calls: list[str] = []

    def fail_roundtrip(*_args: object, **_kwargs: object) -> object:
        raise QualificationContractError("injected preseed roundtrip failure")

    def supply() -> tuple[int, ...]:
        supplier_calls.append("called")
        return (400001, 400002)

    monkeypatch.setattr(
        qualification_preparation,
        "load_closed_d0_d5_preseed_readiness_artifact",
        fail_roundtrip,
    )
    with pytest.raises(
        QualificationContractError,
        match="preseed roundtrip failure",
    ):
        prepare_closed_d0_d5_selection_protocol(
            engine_commit=commit,
            repository_root=repository,
            registry_path="protocols/registry.yaml",
            referent_path="protocols/referents.json",
            preseed_readiness_path=preseed_path,
            selection_seed_supplier=supply,
        )

    assert preseed_path.is_file()
    assert supplier_calls == []


def test_direct_seed_first_builder_cannot_enter_official_profile() -> None:
    protocol = _protocol()

    assert protocol.preseed_readiness is None
    with pytest.raises(
        QualificationContractError,
        match="official .* executable closure|durable preseed",
    ):
        validate_closed_d0_d5_selection_protocol(
            protocol,
            require_persisted_preseed_readiness=True,
        )


def test_preseed_path_digest_and_tamper_mismatches_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository, commit, _module_path = _readiness_repository(tmp_path)
    monkeypatch.setattr(
        qualification_runner,
        "REQUIRED_ENGINE_MODULES",
        ("spirallens.qualification.demo",),
    )
    preseed_path = _preseed_path(repository)
    protocol, _receipt = prepare_closed_d0_d5_selection_protocol(
        engine_commit=commit,
        repository_root=repository,
        registry_path="protocols/registry.yaml",
        referent_path="protocols/referents.json",
        preseed_readiness_path=preseed_path,
        selection_seed_supplier=lambda: (400001, 400002),
    )
    binding = protocol.preseed_readiness
    assert binding is not None

    with pytest.raises(
        QualificationContractError,
        match="source SHA-256 differs",
    ):
        load_closed_d0_d5_preseed_readiness_artifact(
            preseed_path,
            expected_source_sha256="0" * 64,
            expected_canonical_sha256=binding.artifact_canonical_sha256,
        )

    wrong_path_binding = replace(
        binding,
        artifact_path=str(repository / "artifacts" / "wrong-readiness.json"),
    )
    wrong_path_protocol = replace(
        protocol,
        preseed_readiness=wrong_path_binding,
    )
    with pytest.raises(QualificationContractError, match="cannot read preseed"):
        validate_closed_d0_d5_selection_protocol(
            wrong_path_protocol,
            require_persisted_preseed_readiness=True,
        )

    preseed_path.write_bytes(preseed_path.read_bytes() + b" ")
    with pytest.raises(
        QualificationContractError,
        match="source SHA-256 differs",
    ):
        validate_closed_d0_d5_selection_protocol(
            protocol,
            require_persisted_preseed_readiness=True,
        )


def test_invalid_engine_commit_fails_before_seed_supplier(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository, _commit, _module_path = _readiness_repository(tmp_path)
    monkeypatch.setattr(
        qualification_runner,
        "REQUIRED_ENGINE_MODULES",
        ("spirallens.qualification.demo",),
    )

    def forbidden_supplier() -> tuple[int, ...]:
        raise AssertionError("seed supplier must remain unopened")

    with pytest.raises(QualificationSourceBindingError):
        prepare_closed_d0_d5_selection_protocol(
            engine_commit="f" * 40,
            repository_root=repository,
            registry_path="protocols/registry.yaml",
            referent_path="protocols/referents.json",
            preseed_readiness_path=_preseed_path(repository),
            selection_seed_supplier=forbidden_supplier,
        )


def test_dirty_engine_source_fails_before_seed_supplier(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository, commit, module_path = _readiness_repository(tmp_path)
    monkeypatch.setattr(
        qualification_runner,
        "REQUIRED_ENGINE_MODULES",
        ("spirallens.qualification.demo",),
    )
    module_path.write_bytes(module_path.read_bytes() + b"\nDIRTY = True\n")

    def forbidden_supplier() -> tuple[int, ...]:
        raise AssertionError("seed supplier must remain unopened")

    with pytest.raises(QualificationSourceBindingError):
        prepare_closed_d0_d5_selection_protocol(
            engine_commit=commit,
            repository_root=repository,
            registry_path="protocols/registry.yaml",
            referent_path="protocols/referents.json",
            preseed_readiness_path=_preseed_path(repository),
            selection_seed_supplier=forbidden_supplier,
        )


def test_noncanonical_referent_fails_before_seed_supplier(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository, _commit, _module_path = _readiness_repository(tmp_path)
    monkeypatch.setattr(
        qualification_runner,
        "REQUIRED_ENGINE_MODULES",
        ("spirallens.qualification.demo",),
    )
    referent_path = repository / "protocols" / "referents.json"
    wrong_referents = canonical_f0_f4_referent_contracts("0" * 64)
    referent_path.write_bytes(wrong_referents.canonical_bytes)
    _git(repository, "add", "protocols/referents.json")
    _git(repository, "commit", "-qm", "wrong canonical referent")
    commit = _git(repository, "rev-parse", "HEAD").decode("ascii").strip()

    def forbidden_supplier() -> tuple[int, ...]:
        raise AssertionError("seed supplier must remain unopened")

    with pytest.raises(
        QualificationSourceBindingError,
        match="canonical registry/referent readiness",
    ):
        prepare_closed_d0_d5_selection_protocol(
            engine_commit=commit,
            repository_root=repository,
            registry_path="protocols/registry.yaml",
            referent_path="protocols/referents.json",
            preseed_readiness_path=_preseed_path(repository),
            selection_seed_supplier=forbidden_supplier,
        )


def test_seed_free_readiness_api_has_no_seed_input(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository, commit, _module_path = _readiness_repository(tmp_path)
    monkeypatch.setattr(
        qualification_runner,
        "REQUIRED_ENGINE_MODULES",
        ("spirallens.qualification.demo",),
    )

    receipt = verify_closed_d0_d5_preseed_source_readiness(
        engine_commit=commit,
        repository_root=repository,
        registry_path="protocols/registry.yaml",
        referent_path="protocols/referents.json",
    )

    assert receipt.head_commit == commit
    assert receipt.scientific_claim_eligible is False


def test_official_runner_rejects_closed_profile_mutation_before_execution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    mutated = _mutated_closed_protocol(_protocol(), "threshold")
    loaded = LoadedQualificationProtocol(
        protocol=mutated,
        source_path=(tmp_path / "mutated-protocol.json").resolve(),
        source_bytes=mutated.canonical_bytes,
        source_sha256=mutated.canonical_sha256,
        canonical_sha256=mutated.canonical_sha256,
    )

    def forbidden_run(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("selection execution must not start")

    monkeypatch.setattr(
        qualification_runner,
        "run_calibration_selection",
        forbidden_run,
    )
    with pytest.raises(ValueError, match="exact closed D0-D5 factory profile"):
        qualification_runner.run_and_publish_calibration_selection(
            loaded,
            source_binding_receipt=None,  # type: ignore[arg-type]
            selection_freeze_artifact=None,  # type: ignore[arg-type]
            attempt_claim=None,  # type: ignore[arg-type]
            attempt_store_directory=tmp_path,
        )
    assert list(tmp_path.iterdir()) == []


def test_low_level_runner_cannot_bypass_exact_closed_profile_gate(
    tmp_path: Path,
) -> None:
    mutated = _mutated_closed_protocol(_protocol(), "field-graph")
    loaded = LoadedQualificationProtocol(
        protocol=mutated,
        source_path=(tmp_path / "mutated-low-level.json").resolve(),
        source_bytes=mutated.canonical_bytes,
        source_sha256=mutated.canonical_sha256,
        canonical_sha256=mutated.canonical_sha256,
    )

    with pytest.raises(ValueError, match="exact closed D0-D5 factory profile"):
        qualification_runner.run_calibration_selection(
            loaded,
            source_binding_receipt=None,  # type: ignore[arg-type]
            selection_freeze_artifact=None,  # type: ignore[arg-type]
            attempt_claim=None,  # type: ignore[arg-type]
            attempt_store_directory=tmp_path,
        )
    assert list(tmp_path.iterdir()) == []


def test_low_level_runner_retains_generic_custom_protocol_id_path(
    tmp_path: Path,
) -> None:
    custom = replace(
        _mutated_closed_protocol(_protocol(), "threshold"),
        protocol_id="custom-development-protocol",
    )
    loaded = LoadedQualificationProtocol(
        protocol=custom,
        source_path=(tmp_path / "custom-low-level.json").resolve(),
        source_bytes=custom.canonical_bytes,
        source_sha256=custom.canonical_sha256,
        canonical_sha256=custom.canonical_sha256,
    )

    with pytest.raises(TypeError, match="selection_freeze_artifact"):
        qualification_runner.run_calibration_selection(
            loaded,
            source_binding_receipt=None,  # type: ignore[arg-type]
            selection_freeze_artifact=None,  # type: ignore[arg-type]
            attempt_claim=None,  # type: ignore[arg-type]
            attempt_store_directory=tmp_path,
        )
