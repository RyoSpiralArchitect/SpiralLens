from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import spirallens
from spirallens import access, core, graphs, instrument_contracts, synthetic
from spirallens.core import canonical as core_canonical
from spirallens.instrument_contracts import canonical as legacy_canonical

EXPECTED_CORE_EXPORTS = [
    "CanonicalJsonError",
    "JsonScalar",
    "JsonValue",
    "canonical_json_bytes",
    "canonical_json_sha256",
    "parse_canonical_json",
    "sha256_bytes",
]

EXPECTED_ACCESS_EXPORTS = [
    "ATLAS_PREPARATION_DESCRIPTOR_SCHEMA_VERSION",
    "ATLAS_PREPARATION_VIEW_SCHEMA_VERSION",
    "ATTEMPT_TERMINAL_RECORD_SCHEMA_VERSION",
    "MAX_ATLAS_PREPARATION_DESCRIPTOR_BYTES",
    "VALUE_ACCESS_LINEAGE_SCHEMA_VERSION",
    "AtlasAccessContractError",
    "AtlasAccessPolicy",
    "AtlasConsumer",
    "AtlasConsumerDenied",
    "AtlasPreparationDescriptor",
    "AtlasPreparationView",
    "AttemptAccessFacts",
    "AttemptLifecycle",
    "AttemptLifecycleError",
    "AttemptPhase",
    "AttemptPolicy",
    "AttemptTerminalRecord",
    "AttemptTerminalState",
    "CaptureDeclaration",
    "ContextIdentity",
    "InterpretationContract",
    "LoadedAtlasPreparationDescriptor",
    "ModelIdentity",
    "ProtocolIdentity",
    "ProvenanceEscalationError",
    "ProvenanceTaint",
    "QuarantineDisposition",
    "RowDomainIdentity",
    "ValueAccessLineage",
    "ValueAccessTransition",
    "bind_value_access_lineage",
    "load_atlas_preparation_descriptor",
    "prepare_descriptor_only_view",
    "require_atlas_consumer",
    "restrict_atlas_access",
    "reverify_value_access_lineage",
    "write_atlas_preparation_descriptor",
]

EXPECTED_INSTRUMENT_CONTRACT_EXPORTS = [
    "ARTIFACT_REFERENCE_POLICY",
    "ARTIFACT_SCHEMA_VERSIONS_BY_TYPE",
    "ARTIFACT_SCHEMA_VERSION_BY_TYPE",
    "INSTRUMENT_BUNDLE_SCHEMA_VERSION",
    "MAX_INSTRUMENT_BUNDLE_BYTES",
    "MAX_NPY_HEADER_BYTES",
    "MAX_NUMERIC_PAYLOAD_BYTES",
    "PAYLOAD_REFERENCE_POLICY",
    "SUPPORTED_NPY_VERSIONS",
    "SYNTHETIC_LATTICE_SUBSTRATE_BINDING_SCHEMA_VERSION",
    "ArtifactRef",
    "ArtifactReferenceUse",
    "ArtifactType",
    "BundleArtifactEntry",
    "BundleContextBankEntry",
    "BundlePayloadEntry",
    "CalibrationConfirmationResult",
    "CalibrationSelectionDecision",
    "CandidateGraph",
    "CanonicalJsonError",
    "ClaimLevel",
    "ContractValidationError",
    "CoreCandidate",
    "CoreScore",
    "DecodedNumericArray",
    "DefectCoordinateBinding",
    "DefectLocalizationBinding",
    "DefectLoopEstimate",
    "EdgeConnection",
    "EvolutionAxis",
    "ExplicitCoreGraphBinding",
    "FitRole",
    "GateState",
    "GeometricFieldEstimate",
    "GeometryLoopEstimate",
    "GraphConstructionSpec",
    "GraphFreeBinding",
    "GroundTruthAnchor",
    "HistoricalSelectionBoundary",
    "HypothesisDecision",
    "HypothesisDisposition",
    "HypothesisFixedChoice",
    "HypothesisId",
    "HypothesisRegistry",
    "HypothesisRegistryError",
    "HypothesisRegistryIntegrityError",
    "HypothesisRegistryPolicyError",
    "HypothesisRegistrySchemaError",
    "HypothesisResolvedChoice",
    "HypothesisRuleChoice",
    "HypothesisSpec",
    "InheritedFieldGraphBinding",
    "InstrumentArtifactIntegrityError",
    "InstrumentArtifactSchemaError",
    "InstrumentBundleConsistencyError",
    "InstrumentBundleError",
    "InstrumentBundleIntegrityError",
    "InstrumentBundleManifest",
    "InstrumentBundleResolutionError",
    "InstrumentBundleSchemaError",
    "L2AmplitudeRelation",
    "L2AmplitudeValidation",
    "LoadedBundleArtifact",
    "LoadedBundlePayload",
    "LoadedHypothesisRegistry",
    "LoadedInstrumentArtifact",
    "LoadedInstrumentBundle",
    "NeighborhoodMode",
    "NumericArrayContract",
    "NumericPayloadError",
    "NumericPayloadSession",
    "NumericValueRule",
    "OrderParameterField",
    "OrderParameterSpec",
    "PayloadKind",
    "PayloadRef",
    "PayloadReferenceUse",
    "ResolutionState",
    "RowIdentityContract",
    "RuleChoice",
    "ScientificBranch",
    "SubstrateBinding",
    "SubstrateBindingValue",
    "SupportDiagnostic",
    "SyntheticLatticeContextBinding",
    "SyntheticLatticeSubstrateBinding",
    "VerifiedRowIdentity",
    "canonical_json_bytes",
    "canonical_json_sha256",
    "hypothesis_registry_from_dict",
    "instrument_artifact_from_dict",
    "iter_artifact_reference_uses",
    "iter_payload_reference_uses",
    "load_hypothesis_registry",
    "load_instrument_artifact",
    "load_instrument_bundle",
    "open_numeric_payload_session",
    "parse_canonical_json",
    "validate_p0_registry",
]

EXPECTED_SYNTHETIC_EXPORTS = [
    "ANGULAR_SECTION_POSITIVE",
    "FIXED_DIRECTION_NULL",
    "GENERATOR_FAMILY_IDENTITY_SCHEMA_VERSION",
    "REPRESENTATION_PHANTOM_PROTOCOL_SCHEMA_VERSION",
    "SPECTRAL_MOMENT_FIXED_NULL",
    "SPECTRAL_MOMENT_PHANTOM_RECEIPT_VERSION",
    "SPECTRAL_MOMENT_POSITIVE",
    "SPECTRAL_MOMENT_PREREQUISITE_FAILURE",
    "EmittedRepresentationPhantomBundle",
    "ExpectedControlDisposition",
    "GeneratorFamilyContractError",
    "GeneratorFamilyIdentity",
    "GeneratorProtocol",
    "LoadedRepresentationPhantomProtocol",
    "PhantomCase",
    "RepresentationPhantom",
    "RepresentationPhantomBundleError",
    "RepresentationPhantomProtocol",
    "RepresentationPhantomProtocolError",
    "RepresentationPhantomProtocolIntegrityError",
    "RepresentationPhantomProtocolSchemaError",
    "RepresentationPhantomSpec",
    "SpectralMomentCase",
    "SpectralMomentEstimatorInputs",
    "SpectralMomentGenerator",
    "SpectralMomentOracleTruth",
    "SpectralMomentPhantom",
    "SpectralMomentPhantomSpec",
    "emit_representation_phantom_bundle",
    "load_representation_phantom_protocol",
    "representation_phantom_family_identity",
    "require_distinct_construction_families",
]

EXPECTED_GRAPH_EXPORTS = [
    "BOUNDARY_CYCLE_CLASS_SPEC_RECEIPT_VERSION",
    "BOUNDARY_REFINEMENT_RULE_RECEIPT_VERSION",
    "CYCLE_CLASS_BINDING_RECEIPT_VERSION",
    "CYCLE_CLASS_MATCH_ATTEMPT_RECEIPT_VERSION",
    "DISCRETE_DOMAIN_RECEIPT_VERSION",
    "GRAPH_CLAIM_CEILING",
    "GRAPH_CLAIM_SCOPE",
    "GRAPH_CONSTRUCTION_RECEIPT_VERSION",
    "GRAPH_DIVERSITY_RECEIPT_VERSION",
    "GRAPH_FAMILY_IDENTITY_RECEIPT_VERSION",
    "GRAPH_INPUT_RECEIPT_VERSION",
    "GRAPH_PAIR_DIVERSITY_RECEIPT_VERSION",
    "GRAPH_PERSISTENCE_ROUND_TRIP_SUPPORTED",
    "GRAPH_RECORD_SCOPE",
    "GRAPH_SPEC_RECEIPT_VERSION",
    "MAX_DOMAIN_ESTIMATED_PEAK_BYTES",
    "MAX_GRAPH_ESTIMATED_PEAK_BYTES",
    "BoundaryCycleClassSpec",
    "BoundaryRefinementRule",
    "CycleClassBinding",
    "CycleClassMatchAttempt",
    "DiscreteDomainComplex",
    "GraphConstructionReceipt",
    "GraphContractError",
    "GraphDiversityReceipt",
    "GraphFamily",
    "GraphFamilyIdentity",
    "GraphInput",
    "GraphPairDiversity",
    "GraphPurpose",
    "GraphSpecValue",
    "MutualKnnSpec",
    "RadiusGraphSpec",
    "SharedNeighborSpec",
    "bind_cycle_class",
    "build_discrete_domain_complex",
    "construct_mutual_knn",
    "construct_radius_graph",
    "construct_shared_neighbor_graph",
    "define_boundary_cycle_class",
    "measure_graph_diversity",
]


def test_curated_public_export_snapshots_are_exact() -> None:
    assert spirallens.__all__ == ["__version__"]
    assert core.__all__ == EXPECTED_CORE_EXPORTS
    assert access.__all__ == EXPECTED_ACCESS_EXPORTS
    assert graphs.__all__ == EXPECTED_GRAPH_EXPORTS
    assert instrument_contracts.__all__ == EXPECTED_INSTRUMENT_CONTRACT_EXPORTS
    assert synthetic.__all__ == EXPECTED_SYNTHETIC_EXPORTS


def test_legacy_canonical_module_is_an_identity_preserving_reexport() -> None:
    for name in EXPECTED_CORE_EXPORTS:
        assert getattr(legacy_canonical, name) is getattr(core_canonical, name)


def test_access_import_is_framework_neutral_in_fresh_process() -> None:
    source_root = Path(__file__).resolve().parents[1] / "src"
    probe = f"""
import json
import sys
sys.path.insert(0, {str(source_root)!r})
import spirallens.access
forbidden = ["faiss", "huggingface_hub", "safetensors", "torch", "transformers"]
print(json.dumps(sorted(name for name in forbidden if name in sys.modules)))
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-c", probe],
        cwd=source_root.parent,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == []


def test_graphs_import_is_framework_neutral_in_fresh_process() -> None:
    source_root = Path(__file__).resolve().parents[1] / "src"
    probe = f"""
import json
import sys
sys.path.insert(0, {str(source_root)!r})
import spirallens.graphs
forbidden = ["faiss", "huggingface_hub", "safetensors", "torch", "transformers"]
print(json.dumps(sorted(name for name in forbidden if name in sys.modules)))
"""
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=source_root.parent,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == []


def test_pr5_frozen_engineering_artifact_bytes_are_unchanged() -> None:
    repository = Path(__file__).resolve().parents[1]
    expected = {
        (
            repository / "protocols" / "pythia70_public_example_plumbing_v0_1.yaml"
        ): "ef93891c7450ef13cc2c5da54bf1a80d4a0b679df2df04964f2cc505e00aaf4c",
        (
            repository
            / "experiments"
            / "pythia"
            / "receipts"
            / "pythia70_public_example_plumbing_v0_1.json"
        ): "4ab51c1e01992dc63f9bea18a7f53e00293a0ec11617f4970abf2a400723ce82",
    }

    assert {
        path: hashlib.sha256(path.read_bytes()).hexdigest() for path in expected
    } == expected
