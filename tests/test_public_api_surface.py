from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import spirallens
from spirallens import (
    access,
    core,
    graphs,
    instrument_contracts,
    qualification,
    synthetic,
)
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
    "CARTESIAN_FOURIER_FIELD_ESTIMATOR_ID",
    "CARTESIAN_FOURIER_FIELD_RECEIPT_VERSION",
    "CARTESIAN_FOURIER_FIXED_NULL",
    "CARTESIAN_FOURIER_NO_CORE_NULL",
    "CARTESIAN_FOURIER_POSITIVE",
    "CARTESIAN_FOURIER_PREREQUISITE_FAILURE",
    "CARTESIAN_FOURIER_RESOURCE_ESTIMATOR_ID",
    "CARTESIAN_FOURIER_STATE_MIXING_ID",
    "FIXED_DIRECTION_NULL",
    "GENERATOR_FAMILY_IDENTITY_SCHEMA_VERSION",
    "REPRESENTATION_ESTIMATOR_INPUT_RECEIPT_VERSION",
    "REPRESENTATION_FIELD_ESTIMATE_RECEIPT_VERSION",
    "REPRESENTATION_FIELD_ESTIMATOR_ID",
    "REPRESENTATION_PHANTOM_PROTOCOL_SCHEMA_VERSION",
    "SPECTRAL_MOMENT_FIXED_NULL",
    "SPECTRAL_MOMENT_PHANTOM_RECEIPT_VERSION",
    "SPECTRAL_MOMENT_POSITIVE",
    "SPECTRAL_MOMENT_PREREQUISITE_FAILURE",
    "CartesianExpectedDisposition",
    "CartesianFourierCase",
    "CartesianFourierDomainGenerator",
    "CartesianFourierDomainPhantom",
    "CartesianFourierDomainSpec",
    "CartesianFourierEstimatorError",
    "CartesianFourierEstimatorInputs",
    "CartesianFourierFieldEstimate",
    "CartesianFourierOracleTruth",
    "EmittedRepresentationPhantomBundle",
    "ExpectedControlDisposition",
    "GeneratorFamilyContractError",
    "GeneratorFamilyIdentity",
    "GeneratorProtocol",
    "LoadedRepresentationPhantomProtocol",
    "PhantomCase",
    "RepresentationEstimatorError",
    "RepresentationEstimatorInputs",
    "RepresentationFieldEstimate",
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
    "build_representation_estimator_inputs",
    "emit_representation_phantom_bundle",
    "estimate_cartesian_fourier_field",
    "estimate_representation_field",
    "load_representation_phantom_protocol",
    "representation_phantom_family_identity",
    "require_distinct_construction_families",
]

EXPECTED_QUALIFICATION_EXPORTS = [
    "ADVANCEMENT_SOURCE_BINDING_SCHEMA_VERSION",
    "CARTESIAN_SELECTION_CONSTRUCTION_FAMILY_ID",
    "CLOSED_D0_D5_KNOWN_SEED_EXCLUSION_REGISTRY",
    "CLOSED_D0_D5_KNOWN_SEED_EXCLUSION_SCHEMA_VERSION",
    "CLOSED_D0_D5_PRESEED_READINESS_ARTIFACT_ID",
    "CLOSED_D0_D5_PRESEED_READINESS_SCHEMA_VERSION",
    "CLOSED_D0_D5_PRIMARY_UNIT_COUNT",
    "CLOSED_D0_D5_PROTOCOL_FACTORY_ID",
    "CLOSED_D0_D5_PROTOCOL_ID",
    "CLOSED_D0_D5_SELECTION_SEED_COUNT",
    "D6_SELECTION_TERMINAL_BINDING_SCHEMA_VERSION",
    "D7_NOT_RUN_REASON_CODES",
    "D8_NOT_RUN_REASON_CODES",
    "EXCLUSIVE_TERMINAL_PUBLICATION_CAPABILITY_SCHEMA_VERSION",
    "INDEPENDENT_CONFIRMATION_ADMISSION_SCHEMA_VERSION",
    "MAX_ADVANCEMENT_ARTIFACT_BYTES",
    "MAX_PREPARED_SELECTION_LAUNCH_DESCRIPTOR_BYTES",
    "ORCHESTRATED_TERMINAL_PUBLICATION_RECEIPT_ATTRIBUTE",
    "ORCHESTRATED_TERMINAL_PUBLICATION_RECEIPT_SCHEMA_VERSION",
    "PREPARED_SELECTION_LAUNCH_DESCRIPTOR_SCHEMA_VERSION",
    "PREPARED_SELECTION_LAUNCH_INTENT_SCHEMA_VERSION",
    "QUALIFICATION_PROTOCOL_SCHEMA_VERSION",
    "QUALIFICATION_RESULT_SCHEMA_VERSION",
    "SELECTION_ATTEMPT_CLAIM_SCHEMA_VERSION",
    "SELECTION_ATTEMPT_KEY_SCHEME",
    "SELECTION_CONSUMPTION_SCHEMA_VERSION",
    "SELECTION_EXECUTION_START_SCHEMA_VERSION",
    "SELECTION_FAILED_ATTEMPT_SCHEMA_VERSION",
    "SELECTION_FREEZE_SCHEMA_VERSION",
    "SELECTION_LAUNCH_AUTHORIZATION_SCHEMA_VERSION",
    "SELECTION_TERMINAL_MANIFEST_SCHEMA_VERSION",
    "SURROGATE_ADVANCEMENT_DECISION_SCHEMA_VERSION",
    "SURROGATE_ADVANCEMENT_SCOPE",
    "SURROGATE_PROFILE_ID",
    "AttemptStatus",
    "ClosedD0D5KnownSeedExclusionRegistry",
    "ClosedD0D5PreseedReadinessArtifact",
    "ExclusiveTerminalPublicationCapability",
    "GateResult",
    "IndependentConfirmationAdmissionSpec",
    "LoadedClosedD0D5PreseedReadinessArtifact",
    "LoadedCommittedSelectionTerminal",
    "LoadedPreparedSelectionLaunchDescriptor",
    "LoadedPreparedSelectionLaunchIntent",
    "LoadedQualificationProtocol",
    "LoadedScopeLimitedD6Decision",
    "OrchestratedTerminalPublicationReceipt",
    "PersistedQualificationIdentity",
    "PersistedSelectionIdentity",
    "PersistedSelectionTerminalIdentity",
    "PreparedSelectionLaunch",
    "PreparedSelectionLaunchDescriptor",
    "PreparedSelectionLaunchIntentArtifact",
    "PreseedReadinessBinding",
    "PublishedScopeLimitedD6Decision",
    "QualificationContractError",
    "QualificationGateId",
    "QualificationProtocol",
    "QualificationResult",
    "QualificationSourceBindingError",
    "QualificationSourceBindingReceipt",
    "QualificationSourceBindingSummary",
    "QualificationState",
    "SelectionAccessState",
    "SelectionAttemptClaimArtifact",
    "SelectionConsumptionArtifact",
    "SelectionExecutionStartArtifact",
    "SelectionFailedAttemptArtifact",
    "SelectionFreezeArtifact",
    "SelectionLaunchAuthorization",
    "SelectionLaunchIntentBinding",
    "SelectionTerminalBinding",
    "SelectionTerminalManifestArtifact",
    "SurrogateAdvancementDecision",
    "TerminalAttemptArtifactKind",
    "advancement_source_binding_sha256",
    "begin_selection_execution",
    "build_current_advancement_source_binding",
    "build_current_qualification_engine_binding",
    "build_selection_terminal_binding",
    "claim_selection_attempt",
    "load_closed_d0_d5_preseed_readiness_artifact",
    "load_committed_selection_terminal",
    "load_prepared_selection_launch",
    "load_prepared_selection_launch_descriptor",
    "load_prepared_selection_launch_intent",
    "load_protocol_preseed_readiness_artifact",
    "load_qualification_protocol",
    "load_scope_limited_d6_decision",
    "load_selection_attempt_claim",
    "load_selection_execution_start",
    "load_selection_freeze",
    "load_terminal_selection_consumption",
    "prepare_closed_d0_d5_selection_protocol",
    "prepare_selection_launch",
    "probe_exclusive_terminal_publication_capability",
    "publish_closed_d0_d5_preseed_readiness_artifact",
    "publish_scope_limited_d6_decision",
    "publish_terminal_selection_consumption",
    "run_and_publish_calibration_selection",
    "selection_attempt_claim_path",
    "selection_attempt_key_sha256",
    "selection_execution_start_path",
    "selection_freeze_store_path",
    "terminal_selection_transaction_path",
    "validate_advancement_decision_source",
    "validate_closed_d0_d5_selection_protocol",
    "validate_persisted_selection_attempt_claim",
    "validate_persisted_selection_execution_start",
    "verify_closed_d0_d5_preseed_source_readiness",
    "verify_protocol_source_binding",
    "verify_protocol_source_binding_successor",
    "write_prepared_selection_launch_descriptor",
    "write_qualification_protocol",
    "write_selection_freeze",
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
    assert qualification.__all__ == EXPECTED_QUALIFICATION_EXPORTS
    assert not hasattr(qualification, "run_calibration_selection")
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
