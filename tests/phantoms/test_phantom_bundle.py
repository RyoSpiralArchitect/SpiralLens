from __future__ import annotations

from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import subprocess

import numpy as np
import pytest
import yaml

from spirallens.contexts import ContextBank, ContextRole
from spirallens.cli import main
from spirallens.instrument_contracts import (
    ArtifactType,
    ClaimLevel,
    EvolutionAxis,
    FitRole,
    GeometricFieldEstimate,
    GraphConstructionSpec,
    GroundTruthAnchor,
    HypothesisId,
    InstrumentBundleIntegrityError,
    OrderParameterField,
    OrderParameterSpec,
    ResolutionState,
    SubstrateBinding,
    SupportDiagnostic,
    load_hypothesis_registry,
    load_instrument_bundle,
    parse_canonical_json,
)
from spirallens.synthetic import representation_phantom as phantom_module
from spirallens.synthetic import phantom_bundle as bundle_module
from spirallens.synthetic.phantom_bundle import (
    ADDRESS_INDEXER_ID,
    CONTEXT_TO_FIT_ROLE,
    PSEUDO_MODEL_ID,
    EmittedRepresentationPhantomBundle,
    RepresentationPhantomBundleError,
    _ordered_content_sha256,
    _publish_staging_no_replace,
    _verify_generator_revision,
    emit_representation_phantom_bundle,
)
from spirallens.synthetic.protocol import (
    load_representation_phantom_protocol,
)
from spirallens.synthetic.representation_phantom import (
    RepresentationPhantom,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SOURCE = (
    REPOSITORY_ROOT
    / "protocols"
    / "order_parameter_hypothesis_registry_v0_1.yaml"
)
GENERATOR_REVISION = "a" * 40


@pytest.fixture(autouse=True)
def _accept_fixture_generator_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        bundle_module,
        "_verify_generator_revision",
        lambda **_kwargs: None,
    )


def _generator_module_sha256() -> str:
    source_path = Path(phantom_module.__file__)
    return hashlib.sha256(source_path.read_bytes()).hexdigest()


def _write_protocol(
    root: Path,
    *,
    seed: int = 1729,
    protocol_id: str = "representation-phantom-instrument-dev-v0.1",
    generator_module_sha256: str | None = None,
) -> Path:
    root.mkdir()
    registry_path = root / "registry.yaml"
    registry_path.write_bytes(REGISTRY_SOURCE.read_bytes())
    loaded_registry = load_hypothesis_registry(registry_path)
    document = {
        "schema_version": (
            "spirallens.representation-phantom-protocol.v0.1"
        ),
        "protocol_id": protocol_id,
        "status": "instrument_dev",
        "claim_ceiling": "level_0",
        "qualification_status": "not_evaluated",
        "source": {
            "repository": "RyoSpiralArchitect/SpiralLens",
            "generator_revision": GENERATOR_REVISION,
            "generator_module_sha256": (
                _generator_module_sha256()
                if generator_module_sha256 is None
                else generator_module_sha256
            ),
        },
        "generator": {
            "seed": seed,
            "grid_side": 7,
            "ambient_dimension": 12,
            "probe_count": 8,
            "neighbor_count": 4,
            "radial_scale": 1.0,
            "probe_scale": 1.0,
            "nuisance_scale": 0.02,
        },
        "cases": [
            {
                "case_id": "angular-section-positive",
                "field_kind": "angular-unit-vector",
            },
            {
                "case_id": "fixed-direction-null",
                "field_kind": "fixed-unit-vector",
            },
        ],
        "registry": {
            "path": "registry.yaml",
            "source_sha256": loaded_registry.source_sha256,
            "canonical_sha256": loaded_registry.canonical_sha256,
        },
        "execution": {
            "fit_role": "instrument_dev",
            "context_role": "example",
            "context_claim_eligible": False,
            "model_access_authorized": False,
            "subject_data_access_authorized": False,
            "subject_execution_authorized": False,
            "subject_protocol_preparation_authorized": False,
            "calibration_selection_authorized": False,
            "integer_output_authorized": False,
        },
    }
    protocol_path = root / "protocol.yaml"
    protocol_path.write_text(
        yaml.safe_dump(document, sort_keys=False),
        encoding="utf-8",
    )
    return protocol_path


def _emit(
    tmp_path: Path,
    *,
    seed: int = 1729,
    protocol_id: str = "representation-phantom-instrument-dev-v0.1",
    name: str = "bundle",
) -> tuple[Path, EmittedRepresentationPhantomBundle]:
    protocol_path = _write_protocol(
        tmp_path / f"{name}-protocol",
        seed=seed,
        protocol_id=protocol_id,
    )
    receipt = emit_representation_phantom_bundle(
        protocol_path,
        tmp_path / name,
    )
    return protocol_path, receipt


def _tree_snapshot(root: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        (
            path.relative_to(root).as_posix(),
            path.read_bytes(),
        )
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    )


def _payload_array(
    bundle_root: Path,
    loaded: object,
    reference: object,
) -> np.ndarray:
    entry = next(
        item
        for item in loaded.manifest.payloads
        if item.reference == reference
    )
    source = (bundle_root / entry.path).read_bytes()
    return np.load(io.BytesIO(source), allow_pickle=False)


def _payload_json(
    bundle_root: Path,
    loaded: object,
    reference: object,
) -> dict[str, object]:
    entry = next(
        item
        for item in loaded.manifest.payloads
        if item.reference == reference
    )
    source = (bundle_root / entry.path).read_bytes()
    return parse_canonical_json(source, label=entry.path)


def _artifact_values(loaded: object, expected_type: type) -> list[object]:
    return [
        member.value
        for member in loaded.artifacts
        if isinstance(member.value, expected_type)
    ]


def test_cli_generates_bundle_and_reports_bounded_receipt(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    protocol_path = _write_protocol(tmp_path / "cli-protocol")
    output_dir = tmp_path / "cli-bundle"

    exit_code = main(
        [
            "synthetic-bundle",
            "generate",
            "--protocol",
            str(protocol_path),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["status"] == "valid"
    assert receipt["manifest_path"] == str(output_dir / "bundle.json")
    assert receipt["validation_scope"] == "closed_integrity_bundle"
    assert receipt["qualification_status"] == "not_evaluated"
    assert receipt["synthetic_qualified"] is False
    assert receipt["claim_ceiling"] == "level_0"
    assert receipt["model_access_authorized"] is False
    assert receipt["subject_execution_authorized"] is False
    assert receipt["calibration_selection_authorized"] is False
    assert receipt["integer_output_authorized"] is False
    assert receipt["d0_d8"] == {
        f"d{index}": "not_run" for index in range(9)
    }
    assert (output_dir / "bundle.json").is_file()


def test_emitter_publishes_closed_level_zero_bundle(
    tmp_path: Path,
) -> None:
    protocol_path, receipt = _emit(tmp_path)
    loaded = load_instrument_bundle(
        receipt.manifest_path,
        expected_source_sha256=receipt.source_sha256,
        expected_canonical_sha256=receipt.canonical_sha256,
    )
    report = receipt.to_dict()

    assert receipt.manifest_path == tmp_path / "bundle" / "bundle.json"
    assert loaded.canonical_sha256 == receipt.canonical_sha256
    assert receipt.canonical_sha256 == receipt.source_sha256
    assert receipt.artifact_count == 16
    assert receipt.payload_count < 2 * 28
    assert receipt.cross_manifest_join_count > 0
    assert len(receipt.substrate_preprocessing_receipt_sha256) == 64
    assert report["validation_scope"] == "closed_integrity_bundle"
    assert report["qualification_status"] == "not_evaluated"
    assert report["synthetic_qualified"] is False
    assert report["subject_protocol_preparation_authorized"] is False
    assert report["model_access_authorized"] is False
    assert report["subject_data_access_authorized"] is False
    assert report["subject_protocol_execution_authorized"] is False
    assert report["d0_d8"] == {
        f"d{index}": "not_run" for index in range(9)
    }
    assert load_representation_phantom_protocol(protocol_path)


def test_bundle_contains_exact_per_case_artifact_surface(
    tmp_path: Path,
) -> None:
    _, receipt = _emit(tmp_path)
    loaded = load_instrument_bundle(receipt.manifest_path)
    type_counts = Counter(
        member.reference.artifact_type for member in loaded.artifacts
    )
    expected_instrument_types = {
        ArtifactType.SUBSTRATE_BINDING,
        ArtifactType.GRAPH_CONSTRUCTION_SPEC,
        ArtifactType.CANDIDATE_GRAPH,
        ArtifactType.SUPPORT_DIAGNOSTIC,
        ArtifactType.GEOMETRIC_FIELD_ESTIMATE,
        ArtifactType.ORDER_PARAMETER_SPEC,
        ArtifactType.ORDER_PARAMETER_FIELD,
        ArtifactType.GROUND_TRUTH_ANCHOR,
    }

    assert {
        artifact_type
        for artifact_type in type_counts
        if artifact_type
        not in {
            ArtifactType.HYPOTHESIS_REGISTRY,
            ArtifactType.CONTEXT_BANK,
        }
    } == expected_instrument_types
    assert all(type_counts[item] == 2 for item in expected_instrument_types)
    assert type_counts[ArtifactType.HYPOTHESIS_REGISTRY] == 1
    assert type_counts[ArtifactType.CONTEXT_BANK] == 1
    forbidden = {
        ArtifactType.CORE_SCORE,
        ArtifactType.CORE_CANDIDATE,
        ArtifactType.EDGE_CONNECTION,
        ArtifactType.GEOMETRY_LOOP_ESTIMATE,
        ArtifactType.DEFECT_LOOP_ESTIMATE,
        ArtifactType.CALIBRATION_SELECTION_DECISION,
        ArtifactType.CALIBRATION_CONFIRMATION_RESULT,
    }
    assert not forbidden.intersection(type_counts)

    for value in _artifact_values(loaded, SubstrateBinding):
        assert value.role is FitRole.INSTRUMENT_DEV
    for value in _artifact_values(loaded, GraphConstructionSpec):
        assert value.allowed_role is FitRole.INSTRUMENT_DEV
        assert value.family.resolution is ResolutionState.CALIBRATION_SELECTION
        assert value.metric.resolution is ResolutionState.CALIBRATION_SELECTION
        assert value.scale.resolution is ResolutionState.CALIBRATION_SELECTION
        assert value.constructor_id == (
            "instrument-dev-mutual-knn-euclidean-k-4-v0.1"
        )
    for value in _artifact_values(loaded, SupportDiagnostic):
        assert value.fit_role is FitRole.INSTRUMENT_DEV
        assert value.claim_ceiling is ClaimLevel.LEVEL_0
    for artifact_type in (
        GeometricFieldEstimate,
        OrderParameterSpec,
        OrderParameterField,
        GroundTruthAnchor,
    ):
        for value in _artifact_values(loaded, artifact_type):
            assert value.claim_ceiling is ClaimLevel.LEVEL_0


def test_f1_f2_fields_preserve_registry_values_without_resolution(
    tmp_path: Path,
) -> None:
    _, receipt = _emit(tmp_path)
    loaded = load_instrument_bundle(receipt.manifest_path)
    registry = next(
        member.value
        for member in loaded.artifacts
        if member.reference.artifact_type
        is ArtifactType.HYPOTHESIS_REGISTRY
    )
    f1 = registry.require(HypothesisId.F1_PROJECTOR_CONNECTION)
    f2 = registry.require(HypothesisId.F2_LOCAL_COVARIANT_SECTION)

    for field in _artifact_values(loaded, GeometricFieldEstimate):
        assert field.hypothesis_id is HypothesisId.F1_PROJECTOR_CONNECTION
        assert field.gauge_law_id == f1.gauge_law
    for specification in _artifact_values(loaded, OrderParameterSpec):
        assert (
            specification.hypothesis_id
            is HypothesisId.F2_LOCAL_COVARIANT_SECTION
        )
        assert specification.target_manifold_id == f2.target_manifold
        assert specification.gauge_law_id == f2.gauge_law
        assert specification.charge_group.selected_id == f2.charge_group
        assert (
            specification.amplitude_rule.resolution
            is ResolutionState.FIXED_BY_HYPOTHESIS
        )
        assert (
            specification.amplitude_rule.selected_id
            == f2.amplitude_quantity
        )
        assert (
            specification.identifiability_rule.resolution
            is ResolutionState.CALIBRATION_SELECTION
        )
        assert specification.identifiability_rule.candidate_ids == tuple(
            sorted(f2.identifiability_quantities)
        )
        assert specification.interpolation_rule == f2.interpolation_rule
        assert specification.lift_rule == f2.lift_rule
        assert specification.trivialization_rule == f2.trivialization_rule
        assert specification.reference_rule == f2.reference_rule
        assert (
            specification.interpolation_rule.resolution
            is ResolutionState.CALIBRATION_SELECTION
        )


def test_two_cold_emissions_are_byte_identical(tmp_path: Path) -> None:
    first_protocol = _write_protocol(tmp_path / "first-protocol")
    second_protocol = _write_protocol(tmp_path / "second-protocol")
    first = emit_representation_phantom_bundle(
        first_protocol,
        tmp_path / "first",
    )
    second = emit_representation_phantom_bundle(
        second_protocol,
        tmp_path / "second",
    )

    assert first.canonical_sha256 == second.canonical_sha256
    assert _tree_snapshot(tmp_path / "first") == _tree_snapshot(
        tmp_path / "second"
    )


def test_seed_and_protocol_changes_change_bundle_identity(
    tmp_path: Path,
) -> None:
    _, baseline = _emit(tmp_path, name="baseline")
    _, changed_seed = _emit(
        tmp_path,
        seed=1730,
        name="changed-seed",
    )
    _, changed_protocol = _emit(
        tmp_path,
        protocol_id="representation-phantom-instrument-dev-v0.1b",
        name="changed-protocol",
    )

    assert len(
        {
            baseline.canonical_sha256,
            changed_seed.canonical_sha256,
            changed_protocol.canonical_sha256,
        }
    ) == 3
    assert len(
        {
            baseline.bundle_id,
            changed_seed.bundle_id,
            changed_protocol.bundle_id,
        }
    ) == 3


def test_payloads_round_trip_semantic_joins_and_order_digests(
    tmp_path: Path,
) -> None:
    protocol_path, receipt = _emit(tmp_path)
    loaded_protocol = load_representation_phantom_protocol(protocol_path)
    phantom = RepresentationPhantom.generate(
        loaded_protocol.protocol.generator.to_spec()
    )
    loaded = load_instrument_bundle(receipt.manifest_path)
    bundle_root = receipt.manifest_path.parent
    values = {
        (
            member.reference.artifact_type,
            member.reference.artifact_id,
        ): member.value
        for member in loaded.artifacts
    }

    for case in phantom.cases:
        substrate = values[
            (
                ArtifactType.SUBSTRATE_BINDING,
                f"{case.case_id}-substrate",
            )
        ]
        graph = values[
            (
                ArtifactType.CANDIDATE_GRAPH,
                f"{case.case_id}-field-estimation-graph",
            )
        ]
        diagnostic = values[
            (
                ArtifactType.SUPPORT_DIAGNOSTIC,
                f"{case.case_id}-f0-support",
            )
        ]
        geometric = values[
            (
                ArtifactType.GEOMETRIC_FIELD_ESTIMATE,
                f"{case.case_id}-f1-geometric-field",
            )
        ]
        order_field = values[
            (
                ArtifactType.ORDER_PARAMETER_FIELD,
                f"{case.case_id}-f2-order-parameter-field",
            )
        ]
        anchor = values[
            (
                ArtifactType.GROUND_TRUTH_ANCHOR,
                f"{case.case_id}-ground-truth-anchor",
            )
        ]

        assert substrate.row_identity_sha256 == _ordered_content_sha256(
            "vertex-row-order",
            case.vertex_identities,
        )
        assert graph.vertex_order_sha256 == _ordered_content_sha256(
            "vertex-row-order",
            case.vertex_identities,
        )
        assert graph.edge_order_sha256 == _ordered_content_sha256(
            "candidate-graph-edge-order",
            case.edges,
        )
        assert graph.cycle_order_sha256 == _ordered_content_sha256(
            "candidate-graph-cycle-order",
            case.cycle_support,
        )
        expected_arrays = (
            (substrate.states, case.states),
            (substrate.accounted_response, case.accounted_response),
            (graph.canonical_edges, case.edges),
            (graph.weights, case.graph_weights),
            (graph.cycle_support, case.cycle_support),
            (diagnostic.values, case.f0_values),
            (geometric.projector_or_frame, case.f1_frames),
            (geometric.eigenspectrum, case.f1_eigenvalues),
            (order_field.values, case.f2_coordinates),
            (order_field.amplitude, case.f2_amplitude),
            (order_field.support, case.f2_support),
            (anchor.supplied_support, case.center_support_mask),
        )
        for reference, expected in expected_arrays:
            actual = _payload_array(bundle_root, loaded, reference)
            assert actual.dtype.str == expected.dtype.str
            assert actual.shape == expected.shape
            assert np.array_equal(actual, expected)
            assert np.all(np.isfinite(actual))

        assert order_field.frame_or_tensor == geometric.projector_or_frame
        assert order_field.eigenspectrum == geometric.eigenspectrum

    opaque_entries = [
        entry
        for entry in loaded.manifest.payloads
        if entry.reference.kind.value == "opaque"
    ]
    assert opaque_entries
    for entry in opaque_entries:
        source = (bundle_root / entry.path).read_bytes()
        parsed = parse_canonical_json(source, label=entry.path)
        bounded = (
            parsed["execution_boundary"]
            if parsed["schema_version"]
            == (
                "spirallens.synthetic-substrate-"
                "preprocessing-receipt.v0.1"
            )
            else parsed
        )
        assert bounded["fit_role"] == "instrument_dev"
        assert bounded["claim_ceiling"] == "level_0"
        assert bounded["calibration_selection_authorized"] is False


def test_bundle_alone_preserves_nonqualification_boundary(
    tmp_path: Path,
) -> None:
    _, receipt = _emit(tmp_path)
    loaded = load_instrument_bundle(receipt.manifest_path)
    bundle_root = receipt.manifest_path.parent
    substrates = _artifact_values(loaded, SubstrateBinding)
    boundary_references = {
        substrate.preprocessing_fit for substrate in substrates
    }

    assert len(boundary_references) == 1
    boundary_reference = next(iter(boundary_references))
    assert (
        boundary_reference.sha256
        == receipt.substrate_preprocessing_receipt_sha256
    )
    preprocessing_receipt = _payload_json(
        bundle_root,
        loaded,
        boundary_reference,
    )
    assert preprocessing_receipt["schema_version"] == (
        "spirallens.synthetic-substrate-preprocessing-receipt.v0.1"
    )
    assert preprocessing_receipt["receipt_kind"] == "preprocessing"
    assert (
        preprocessing_receipt["implementation_id"]
        == "identity-no-preprocessing"
    )
    assert preprocessing_receipt["fit_performed"] is False
    assert preprocessing_receipt["learned_state_present"] is False
    boundary = preprocessing_receipt["execution_boundary"]
    assert boundary["schema_version"] == (
        "spirallens.synthetic-execution-boundary.v0.1"
    )
    assert boundary["protocol"]["status"] == "instrument_dev"
    assert boundary["protocol"]["qualification_status"] == "not_evaluated"
    assert boundary["validation_scope"] == "closed_integrity_bundle"
    assert boundary["qualification_status"] == "not_evaluated"
    assert boundary["synthetic_qualified"] is False
    assert boundary["generator_revision_verified"] is True
    assert boundary["generator_execution_bound_to_source_bytes"] is True
    assert boundary["model_access_authorized"] is False
    assert boundary["subject_data_access_authorized"] is False
    assert boundary["subject_execution_authorized"] is False
    assert boundary["calibration_selection_authorized"] is False
    assert boundary["integer_output_authorized"] is False
    assert boundary["d0_d8"] == {
        f"d{index}": "not_run" for index in range(9)
    }


def test_generated_context_is_example_pseudo_model_only(
    tmp_path: Path,
) -> None:
    _, receipt = _emit(tmp_path)
    loaded = load_instrument_bundle(receipt.manifest_path)
    context = next(
        member.value
        for member in loaded.artifacts
        if isinstance(member.value, ContextBank)
    )
    substrates = _artifact_values(loaded, SubstrateBinding)

    assert context.role is ContextRole.EXAMPLE
    assert context.claim_eligible is False
    assert context.model.model_id == PSEUDO_MODEL_ID
    assert context.tokenizer.tokenizer_id == ADDRESS_INDEXER_ID
    assert context.model.resolved_revision == GENERATOR_REVISION
    assert context.model.vocab_size == 49
    assert context.tokenizer.addressable_size == 49
    assert "pythia" not in context.model.model_id.lower()
    assert "pythia" not in context.tokenizer.tokenizer_id.lower()
    assert CONTEXT_TO_FIT_ROLE[context.role] is FitRole.INSTRUMENT_DEV
    assert all(item.role is FitRole.INSTRUMENT_DEV for item in substrates)
    assert all(
        item.evolution_axis is EvolutionAxis.SYNTHETIC_LATTICE
        for item in substrates
    )
    assert loaded.manifest.context_banks[0].allowed_role is ContextRole.EXAMPLE
    assert receipt.to_dict()["context_role_mapping"] == {
        "example": "instrument_dev"
    }


def test_bundle_payload_tamper_is_rejected(tmp_path: Path) -> None:
    _, receipt = _emit(tmp_path)
    loaded = load_instrument_bundle(receipt.manifest_path)
    entry = loaded.manifest.payloads[0]
    payload_path = receipt.manifest_path.parent / entry.path
    payload_path.write_bytes(payload_path.read_bytes() + b"tamper")

    with pytest.raises(InstrumentBundleIntegrityError):
        load_instrument_bundle(receipt.manifest_path)


def test_existing_and_symlink_destinations_are_rejected(
    tmp_path: Path,
) -> None:
    protocol_path = _write_protocol(tmp_path / "protocol")
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(
        RepresentationPhantomBundleError,
        match="must not already exist",
    ):
        emit_representation_phantom_bundle(protocol_path, existing)

    target = tmp_path / "target"
    target.mkdir()
    destination_link = tmp_path / "destination-link"
    destination_link.symlink_to(target, target_is_directory=True)
    with pytest.raises(
        RepresentationPhantomBundleError,
        match="must not already exist",
    ):
        emit_representation_phantom_bundle(
            protocol_path,
            destination_link,
        )

    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    parent_link = tmp_path / "parent-link"
    parent_link.symlink_to(real_parent, target_is_directory=True)
    with pytest.raises(
        RepresentationPhantomBundleError,
        match="parent chain must not contain symlinks",
    ):
        emit_representation_phantom_bundle(
            protocol_path,
            parent_link / "bundle",
        )


def test_generator_digest_mismatch_refuses_output(tmp_path: Path) -> None:
    protocol_path = _write_protocol(
        tmp_path / "protocol",
        generator_module_sha256="0" * 64,
    )
    destination = tmp_path / "bundle"

    with pytest.raises(
        RepresentationPhantomBundleError,
        match="generator module SHA-256 differs",
    ):
        emit_representation_phantom_bundle(protocol_path, destination)
    assert not destination.exists()


def test_generator_revision_must_resolve_to_a_commit() -> None:
    with pytest.raises(
        RepresentationPhantomBundleError,
        match="generator revision is not resolvable",
    ):
        _verify_generator_revision(
            repository_root=REPOSITORY_ROOT,
            revision="0" * 40,
            generator_module_sha256=_generator_module_sha256(),
        )


def test_generator_revision_accepts_matching_commit_and_rejects_wrong_blob(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    generator_path = (
        repository
        / "src"
        / "spirallens"
        / "synthetic"
        / "representation_phantom.py"
    )
    generator_path.parent.mkdir(parents=True)
    source_bytes = b"BOUND_GENERATOR_FIXTURE = True\n"
    generator_path.write_bytes(source_bytes)
    subprocess.run(
        ("git", "init", "-q"),
        cwd=repository,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ("git", "add", "."),
        cwd=repository,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        (
            "git",
            "-c",
            "user.name=SpiralLens Test",
            "-c",
            "user.email=spirallens-test@example.invalid",
            "commit",
            "-q",
            "-m",
            "fixture",
        ),
        cwd=repository,
        check=True,
        capture_output=True,
    )
    revision = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()

    _verify_generator_revision(
        repository_root=repository,
        revision=revision,
        generator_module_sha256=source_sha256,
    )
    with pytest.raises(
        RepresentationPhantomBundleError,
        match="does not contain the bound module",
    ):
        _verify_generator_revision(
            repository_root=repository,
            revision=revision,
            generator_module_sha256="0" * 64,
        )


def test_emitter_executes_bound_source_not_cached_generator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol_path = _write_protocol(tmp_path / "protocol")
    destination = tmp_path / "bundle"

    def forbidden_cached_generate(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("cached generator must not execute")

    monkeypatch.setattr(
        phantom_module.RepresentationPhantom,
        "generate",
        classmethod(forbidden_cached_generate),
    )

    receipt = emit_representation_phantom_bundle(
        protocol_path,
        destination,
    )
    assert receipt.manifest_path.is_file()


def test_publication_moves_manifest_entrypoint_last(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    for name in ("artifacts", "external", "payloads"):
        child = staging / name
        child.mkdir()
        (child / "member").write_bytes(name.encode("ascii"))
    (staging / "bundle.json").write_bytes(b"manifest")
    destination = tmp_path / "bundle"
    original_rename = bundle_module.os.rename
    moves: list[tuple[str, str]] = []

    def recording_rename(
        source: str | bytes | Path,
        target: str | bytes | Path,
    ) -> None:
        moves.append((Path(source).name, Path(target).name))
        original_rename(source, target)

    monkeypatch.setattr(bundle_module.os, "rename", recording_rename)

    identity = _publish_staging_no_replace(staging, destination)

    published = bundle_module.os.lstat(destination)
    assert identity == (published.st_dev, published.st_ino)
    assert [source for source, _target in moves] == [
        "artifacts",
        "external",
        "payloads",
        "bundle.json",
    ]
    assert (destination / "bundle.json").read_bytes() == b"manifest"


def test_mid_transfer_rename_failure_rolls_back_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol_path = _write_protocol(tmp_path / "protocol")
    destination = tmp_path / "bundle"
    original_rename = bundle_module.os.rename

    def failing_rename(
        source: str | bytes | Path,
        target: str | bytes | Path,
    ) -> None:
        if Path(source).name == "external":
            raise OSError("injected mid-transfer failure")
        original_rename(source, target)

    monkeypatch.setattr(bundle_module.os, "rename", failing_rename)

    with pytest.raises(OSError, match="injected mid-transfer failure"):
        emit_representation_phantom_bundle(protocol_path, destination)

    assert not destination.exists()
    assert not tuple(tmp_path.glob(".bundle.staging-*"))


def test_publication_race_does_not_replace_competing_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol_path = _write_protocol(tmp_path / "protocol")
    destination = tmp_path / "bundle"
    original_mkdir = bundle_module.os.mkdir

    def racing_mkdir(
        path: str | bytes | Path,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        if Path(path) == destination:
            original_mkdir(path, mode, dir_fd=dir_fd)
            raise FileExistsError
        original_mkdir(path, mode, dir_fd=dir_fd)

    monkeypatch.setattr(bundle_module.os, "mkdir", racing_mkdir)

    with pytest.raises(
        RepresentationPhantomBundleError,
        match="appeared before publication",
    ):
        emit_representation_phantom_bundle(protocol_path, destination)

    assert destination.is_dir()
    assert list(destination.iterdir()) == []


def test_failed_published_revalidation_removes_owned_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol_path = _write_protocol(tmp_path / "protocol")
    destination = tmp_path / "bundle"
    real_loader = bundle_module.load_instrument_bundle
    call_count = 0

    def fail_second_load(*args: object, **kwargs: object) -> object:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise InstrumentBundleIntegrityError(
                "injected_published_failure",
                "published validation failure injection",
            )
        return real_loader(*args, **kwargs)

    monkeypatch.setattr(
        bundle_module,
        "load_instrument_bundle",
        fail_second_load,
    )

    with pytest.raises(
        InstrumentBundleIntegrityError,
        match="injected_published_failure",
    ):
        emit_representation_phantom_bundle(protocol_path, destination)

    assert call_count == 2
    assert not destination.exists()
