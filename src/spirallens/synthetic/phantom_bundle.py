"""Canonical closed-bundle emission for representation-shaped phantoms.

The emitter is deliberately limited to instrument-development observations.
It emits F0/F1/F2 artifacts at Level 0 and records the executed development
graph constructor, but it does not calibration-select or qualify that graph,
qualify an instrument, localize a core, construct a loop, estimate winding, or
authorize model or subject access.
"""

from __future__ import annotations

from contextlib import contextmanager
import ctypes
import ctypes.util
from dataclasses import dataclass
import errno
import hashlib
import io
import os
from pathlib import Path
import stat
import subprocess
import sys
from types import ModuleType
from typing import TYPE_CHECKING, Iterator
import uuid

import numpy as np
from numpy.typing import NDArray

from spirallens.instrument_contracts import (
    ARTIFACT_SCHEMA_VERSION_BY_TYPE,
    ArtifactRef,
    ArtifactType,
    BundleArtifactEntry,
    BundlePayloadEntry,
    CandidateGraph,
    ClaimLevel,
    EvolutionAxis,
    FitRole,
    GeometricFieldEstimate,
    GraphConstructionSpec,
    GroundTruthAnchor,
    HypothesisId,
    InstrumentBundleManifest,
    OrderParameterField,
    OrderParameterSpec,
    PayloadKind,
    PayloadRef,
    ResolutionState,
    RuleChoice,
    SyntheticLatticeContextBinding,
    SyntheticLatticeSubstrateBinding,
    SupportDiagnostic,
    canonical_json_bytes,
    load_hypothesis_registry,
    load_instrument_bundle,
    parse_canonical_json,
)

from .protocol import (
    LoadedRepresentationPhantomProtocol,
    load_representation_phantom_protocol,
)

if TYPE_CHECKING:
    from .representation_phantom import PhantomCase


_D0_D8 = tuple((f"d{index}", "not_run") for index in range(9))
_GENERATOR_REPOSITORY_PATH = (
    "src/spirallens/synthetic/representation_phantom.py"
)
_RENAME_EXCL = 0x00000004
_RENAME_NOFOLLOW_ANY = 0x00000010
_RENAME_RESOLVE_BENEATH = 0x00000020
_RENAME_PUBLICATION_FLAGS = (
    _RENAME_EXCL | _RENAME_NOFOLLOW_ANY | _RENAME_RESOLVE_BENEATH
)


class RepresentationPhantomBundleError(ValueError):
    """Raised when a phantom bundle cannot be emitted fail-closed."""


@dataclass(frozen=True, slots=True)
class EmittedRepresentationPhantomBundle:
    """JSON-safe receipt for one published, revalidated integrity bundle."""

    manifest_path: Path
    canonical_sha256: str
    source_sha256: str
    bundle_id: str
    protocol_source_sha256: str
    protocol_canonical_sha256: str
    substrate_preprocessing_receipt_sha256: str
    generator_module_sha256: str
    registry_source_sha256: str
    registry_canonical_sha256: str
    case_ids: tuple[str, ...]
    artifact_count: int
    payload_count: int
    cross_manifest_join_count: int
    resource_budget_estimator_id: str
    resource_budget_safety_factor: int
    estimated_peak_bytes: int
    estimated_output_bytes: int
    max_estimated_peak_bytes: int
    max_estimated_output_bytes: int
    resource_budget_claim_boundary: str
    validation_scope: str = "closed_integrity_bundle"
    qualification_status: str = "not_evaluated"
    synthetic_qualified: bool = False
    subject_protocol_preparation_authorized: bool = False
    model_access_authorized: bool = False
    subject_data_access_authorized: bool = False
    subject_execution_authorized: bool = False
    subject_protocol_execution_authorized: bool = False
    calibration_selection_authorized: bool = False
    integer_output_authorized: bool = False
    d0_d8: tuple[tuple[str, str], ...] = _D0_D8

    def to_dict(self) -> dict[str, object]:
        """Return the bounded CLI-facing summary without scientific claims."""

        return {
            "status": "valid",
            "manifest_path": str(self.manifest_path),
            "canonical_sha256": self.canonical_sha256,
            "source_sha256": self.source_sha256,
            "bundle_id": self.bundle_id,
            "protocol_source_sha256": self.protocol_source_sha256,
            "protocol_canonical_sha256": self.protocol_canonical_sha256,
            "substrate_preprocessing_receipt_sha256": (
                self.substrate_preprocessing_receipt_sha256
            ),
            "generator_module_sha256": self.generator_module_sha256,
            "registry_source_sha256": self.registry_source_sha256,
            "registry_canonical_sha256": self.registry_canonical_sha256,
            "case_ids": list(self.case_ids),
            "artifact_count": self.artifact_count,
            "payload_count": self.payload_count,
            "cross_manifest_join_count": self.cross_manifest_join_count,
            "resource_budget": {
                "claim_boundary": self.resource_budget_claim_boundary,
                "estimator_id": self.resource_budget_estimator_id,
                "estimated_output_bytes": self.estimated_output_bytes,
                "estimated_peak_bytes": self.estimated_peak_bytes,
                "max_estimated_output_bytes": (
                    self.max_estimated_output_bytes
                ),
                "max_estimated_peak_bytes": self.max_estimated_peak_bytes,
                "preflight_status": "pass",
                "safety_factor": self.resource_budget_safety_factor,
            },
            "validation_scope": self.validation_scope,
            "qualification_status": self.qualification_status,
            "synthetic_qualified": self.synthetic_qualified,
            "claim_ceiling": ClaimLevel.LEVEL_0.value,
            "fit_role": FitRole.INSTRUMENT_DEV.value,
            "context_kind": "synthetic_lattice",
            "synthetic_context_claim_eligible": False,
            "numeric_payloads_self_audited": True,
            "cycle_construction_status": "not_run",
            "loop_artifacts_emitted": False,
            "subject_protocol_preparation_authorized": (
                self.subject_protocol_preparation_authorized
            ),
            "model_access_authorized": self.model_access_authorized,
            "subject_data_access_authorized": (
                self.subject_data_access_authorized
            ),
            "subject_execution_authorized": (
                self.subject_execution_authorized
            ),
            "subject_protocol_execution_authorized": (
                self.subject_protocol_execution_authorized
            ),
            "calibration_selection_authorized": (
                self.calibration_selection_authorized
            ),
            "integer_output_authorized": self.integer_output_authorized,
            "d0_d8": dict(self.d0_d8),
        }


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_generator_source(
    module_path: Path,
    *,
    expected_sha256: str,
) -> bytes:
    if module_path.is_symlink():
        raise RepresentationPhantomBundleError(
            "representation phantom generator module must not be a symlink"
        )
    source_bytes = module_path.read_bytes()
    if _sha256(source_bytes) != expected_sha256:
        raise RepresentationPhantomBundleError(
            "representation phantom generator module SHA-256 differs from "
            "the protocol binding"
        )
    return source_bytes


def _git_output(
    repository_root: Path,
    *arguments: str,
) -> bytes:
    try:
        completed = subprocess.run(
            ("git", "-C", str(repository_root), *arguments),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RepresentationPhantomBundleError(
            "generator revision verification could not execute git"
        ) from error
    if completed.returncode != 0:
        raise RepresentationPhantomBundleError(
            "generator revision is not resolvable in the repository"
        )
    return completed.stdout


def _verify_generator_revision(
    *,
    repository_root: Path,
    revision: str,
    generator_module_sha256: str,
) -> None:
    """Bind the declared commit to the exact generator source bytes."""

    object_type = _git_output(
        repository_root,
        "cat-file",
        "-t",
        revision,
    ).strip()
    if object_type != b"commit":
        raise RepresentationPhantomBundleError(
            "generator revision must identify a git commit"
        )
    committed_source = _git_output(
        repository_root,
        "show",
        f"{revision}:{_GENERATOR_REPOSITORY_PATH}",
    )
    if _sha256(committed_source) != generator_module_sha256:
        raise RepresentationPhantomBundleError(
            "declared generator revision does not contain the bound module"
        )


@contextmanager
def _bound_generator_module(
    *,
    module_path: Path,
    source_bytes: bytes,
) -> Iterator[ModuleType]:
    """Execute the exact source bytes whose digest the protocol binds."""

    module_name = (
        "spirallens.synthetic._bound_representation_phantom_"
        f"{uuid.uuid4().hex}"
    )
    module = ModuleType(module_name)
    module.__file__ = str(module_path)
    module.__package__ = "spirallens.synthetic"
    sys.modules[module_name] = module
    try:
        code = compile(source_bytes, str(module_path), "exec")
        exec(code, module.__dict__)
        yield module
    except RepresentationPhantomBundleError:
        raise
    except Exception as error:
        raise RepresentationPhantomBundleError(
            "bound representation phantom generator execution failed"
        ) from error
    finally:
        if sys.modules.get(module_name) is module:
            del sys.modules[module_name]


def _artifact_ref(value: object) -> ArtifactRef:
    return ArtifactRef(
        artifact_type=value.artifact_type,
        schema_version=value.schema_version,
        artifact_id=value.artifact_id,
        canonical_sha256=value.canonical_sha256,
    )


def _external_ref(
    artifact_type: ArtifactType,
    *,
    artifact_id: str,
    canonical_sha256: str,
) -> ArtifactRef:
    return ArtifactRef(
        artifact_type=artifact_type,
        schema_version=ARTIFACT_SCHEMA_VERSION_BY_TYPE[artifact_type],
        artifact_id=artifact_id,
        canonical_sha256=canonical_sha256,
    )


def _ordered_content_sha256(
    domain: str,
    value: NDArray[np.generic],
) -> str:
    """Hash explicit ordered identity content, including dtype and shape."""

    array = np.asarray(value)
    if array.dtype.hasobject or not array.flags.c_contiguous:
        raise RepresentationPhantomBundleError(
            f"{domain} must be a C-contiguous non-object array"
        )
    descriptor = canonical_json_bytes(
        {
            "schema_version": "spirallens.ordered-content-identity.v0.1",
            "domain": domain,
            "dtype": array.dtype.str,
            "shape": list(array.shape),
        }
    )
    return _sha256(descriptor + b"\x00" + array.tobytes(order="C"))


def _selection(
    family_id: str,
    *candidate_ids: str,
) -> RuleChoice:
    return RuleChoice(
        family_id=family_id,
        resolution=ResolutionState.CALIBRATION_SELECTION,
        candidate_ids=tuple(sorted(candidate_ids)),
    )


def _fixed(family_id: str, selected_id: str) -> RuleChoice:
    return RuleChoice(
        family_id=family_id,
        resolution=ResolutionState.FIXED_BY_HYPOTHESIS,
        selected_id=selected_id,
    )


def _instrument_dev_executed(
    family_id: str,
    selected_id: str,
) -> RuleChoice:
    return RuleChoice(
        family_id=family_id,
        resolution=ResolutionState.INSTRUMENT_DEV_EXECUTED,
        selected_id=selected_id,
    )


class _PayloadWriter:
    """Content-addressed payload writer with semantic reclassification checks."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._entries_by_sha: dict[str, BundlePayloadEntry] = {}

    @property
    def entries(self) -> tuple[BundlePayloadEntry, ...]:
        return tuple(
            sorted(
                self._entries_by_sha.values(),
                key=lambda entry: entry.sort_key,
            )
        )

    def _register(
        self,
        *,
        suffix: str,
        payload_bytes: bytes,
        reference: PayloadRef,
    ) -> PayloadRef:
        existing = self._entries_by_sha.get(reference.sha256)
        if existing is not None:
            if existing.reference != reference:
                raise RepresentationPhantomBundleError(
                    "one payload digest would be assigned conflicting "
                    "structured metadata"
                )
            if (self.root / existing.path).read_bytes() != payload_bytes:
                raise RepresentationPhantomBundleError(
                    "payload digest collision has non-identical bytes"
                )
            return existing.reference
        relative_path = f"payloads/{reference.sha256}.{suffix}"
        destination = self.root / relative_path
        destination.write_bytes(payload_bytes)
        entry = BundlePayloadEntry(
            path=relative_path,
            reference=reference,
        )
        self._entries_by_sha[reference.sha256] = entry
        return reference

    def array(
        self,
        value: NDArray[np.generic],
        *,
        row_identity_sha256: str,
    ) -> PayloadRef:
        array = np.asarray(value)
        if (
            array.dtype.hasobject
            or not array.dtype.str
            or array.dtype.str[0] not in {"<", ">", "|"}
        ):
            raise RepresentationPhantomBundleError(
                "array payload dtype must be explicit-endian and non-object"
            )
        if not array.flags.c_contiguous:
            raise RepresentationPhantomBundleError(
                "array payload must be C-contiguous"
            )
        if not np.all(np.isfinite(array)):
            raise RepresentationPhantomBundleError(
                "array payload must contain only finite values"
            )
        stream = io.BytesIO()
        np.save(stream, array, allow_pickle=False)
        payload_bytes = stream.getvalue()
        decoded_stream = io.BytesIO(payload_bytes)
        decoded = np.load(decoded_stream, allow_pickle=False)
        if (
            decoded_stream.tell() != len(payload_bytes)
            or decoded.dtype.str != array.dtype.str
            or decoded.shape != array.shape
            or not decoded.flags.c_contiguous
            or not np.array_equal(decoded, array)
            or not np.all(np.isfinite(decoded))
        ):
            raise RepresentationPhantomBundleError(
                "NPY round-trip self-audit failed"
            )
        reference = PayloadRef(
            kind=PayloadKind.ARRAY,
            sha256=_sha256(payload_bytes),
            byte_length=len(payload_bytes),
            media_type="application/x-npy",
            dtype=array.dtype.str,
            shape=tuple(int(item) for item in array.shape),
            row_identity_sha256=row_identity_sha256,
        )
        return self._register(
            suffix="npy",
            payload_bytes=payload_bytes,
            reference=reference,
        )

    def opaque_json(self, value: dict[str, object]) -> PayloadRef:
        payload_bytes = canonical_json_bytes(value)
        if parse_canonical_json(payload_bytes, label="opaque receipt") != value:
            raise RepresentationPhantomBundleError(
                "opaque receipt canonical round-trip failed"
            )
        reference = PayloadRef(
            kind=PayloadKind.OPAQUE,
            sha256=_sha256(payload_bytes),
            byte_length=len(payload_bytes),
            media_type="application/json",
        )
        return self._register(
            suffix="json",
            payload_bytes=payload_bytes,
            reference=reference,
        )


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_registry_path(
    loaded: LoadedRepresentationPhantomProtocol,
) -> Path:
    relative = Path(loaded.protocol.registry.path)
    candidates = (
        loaded.source_path.parent / relative,
        _repository_root() / relative,
    )
    existing: dict[Path, Path] = {}
    for candidate in candidates:
        if candidate.exists():
            if candidate.is_symlink():
                raise RepresentationPhantomBundleError(
                    "registry source must not be a symlink"
                )
            resolved = candidate.resolve()
            existing[resolved] = candidate
    if len(existing) != 1:
        raise RepresentationPhantomBundleError(
            "registry path must resolve uniquely from the protocol directory "
            "or repository root"
        )
    return next(iter(existing))


def _substrate_preprocessing_receipt_document(
    loaded: LoadedRepresentationPhantomProtocol,
    *,
    resource_budget: dict[str, object],
) -> dict[str, object]:
    """Bind no-preprocessing provenance and the durable execution boundary."""

    protocol = loaded.protocol
    return {
        "schema_version": (
            "spirallens.synthetic-substrate-preprocessing-receipt.v0.1"
        ),
        "receipt_kind": "preprocessing",
        "implementation_id": "identity-no-preprocessing",
        "fit_performed": False,
        "learned_state_present": False,
        "execution_boundary": {
            "schema_version": (
                "spirallens.synthetic-execution-boundary.v0.1"
            ),
            "protocol": protocol.to_dict(),
            "protocol_source_sha256": loaded.source_sha256,
            "protocol_canonical_sha256": loaded.canonical_sha256,
            "validation_scope": "closed_integrity_bundle",
            "qualification_status": "not_evaluated",
            "synthetic_qualified": False,
            "claim_ceiling": ClaimLevel.LEVEL_0.value,
            "fit_role": FitRole.INSTRUMENT_DEV.value,
            "context_kind": "synthetic_lattice",
            "synthetic_context_claim_eligible": False,
            "numeric_payloads_self_audited": True,
            "resource_budget": resource_budget,
            "cycle_construction_status": "not_run",
            "graph_choice_resolution": (
                ResolutionState.INSTRUMENT_DEV_EXECUTED.value
            ),
            "loop_artifacts_emitted": False,
            "generator_revision_verified": True,
            "generator_execution_bound_to_source_bytes": True,
            "subject_protocol_preparation_authorized": False,
            "model_access_authorized": False,
            "subject_data_access_authorized": False,
            "subject_execution_authorized": False,
            "calibration_selection_authorized": False,
            "integer_output_authorized": False,
            "d0_d8": dict(_D0_D8),
            "non_emitted_artifact_types": [
                ArtifactType.CALIBRATION_CONFIRMATION_RESULT.value,
                ArtifactType.CALIBRATION_SELECTION_DECISION.value,
                ArtifactType.CORE_CANDIDATE.value,
                ArtifactType.CORE_SCORE.value,
                ArtifactType.DEFECT_LOOP_ESTIMATE.value,
                ArtifactType.EDGE_CONNECTION.value,
                ArtifactType.GEOMETRY_LOOP_ESTIMATE.value,
            ],
        },
    }


def _artifact_entry(
    root: Path,
    *,
    case_id: str,
    name: str,
    artifact: object,
) -> BundleArtifactEntry:
    relative_path = f"artifacts/{case_id}/{name}.json"
    artifact_bytes = artifact.canonical_bytes
    destination = root / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(artifact_bytes)
    return BundleArtifactEntry(
        path=relative_path,
        source_sha256=_sha256(artifact_bytes),
        reference=_artifact_ref(artifact),
    )


def _case_artifacts(
    case: PhantomCase,
    *,
    payloads: _PayloadWriter,
    registry_ref: ArtifactRef,
    registry: object,
    substrate_preprocessing_receipt: PayloadRef,
    generator_module_sha256: str,
    generator_revision: str,
    protocol_id: str,
    protocol_source_sha256: str,
    protocol_canonical_sha256: str,
) -> tuple[tuple[tuple[str, object], ...], tuple[ArtifactRef, ...]]:
    case.validate()
    case_id = case.case_id
    row_identity = _ordered_content_sha256(
        "vertex-row-order",
        case.vertex_identities,
    )
    vertex_order = _ordered_content_sha256(
        "vertex-row-order",
        case.vertex_identities,
    )
    edge_order = _ordered_content_sha256(
        "candidate-graph-edge-order",
        case.edges,
    )
    cycle_order = _ordered_content_sha256(
        "candidate-graph-cycle-order",
        case.cycle_support,
    )

    receipt_common: dict[str, object] = {
        "schema_version": "spirallens.synthetic-fit-receipt.v0.1",
        "case_id": case_id,
        "spec_sha256": case.spec.canonical_sha256,
        "protocol_source_sha256": protocol_source_sha256,
        "protocol_canonical_sha256": protocol_canonical_sha256,
        "fit_role": FitRole.INSTRUMENT_DEV.value,
        "claim_ceiling": ClaimLevel.LEVEL_0.value,
        "calibration_selection_authorized": False,
        "model_access_authorized": False,
        "subject_data_access_authorized": False,
    }
    synthetic_context = SyntheticLatticeContextBinding(
        context_id=(
            "representation-phantom-lattice-"
            f"{protocol_canonical_sha256[:20]}"
        ),
        source_id=protocol_id,
        generator_revision=generator_revision,
        generator_module_sha256=generator_module_sha256,
        generator_spec_sha256=case.spec.canonical_sha256,
        protocol_source_sha256=protocol_source_sha256,
        protocol_canonical_sha256=protocol_canonical_sha256,
        row_identity_sha256=row_identity,
        lattice_shape=(case.spec.grid_side, case.spec.grid_side),
        boundary_rule="open",
        claim_eligible=False,
    )
    substrate = SyntheticLatticeSubstrateBinding(
        artifact_id=f"{case_id}-substrate",
        role=FitRole.INSTRUMENT_DEV,
        evolution_axis=EvolutionAxis.SYNTHETIC_LATTICE,
        row_identity_sha256=row_identity,
        synthetic_context=synthetic_context,
        vertex_identities=payloads.array(
            case.vertex_identities,
            row_identity_sha256=row_identity,
        ),
        observation_identities=payloads.array(
            case.observation_identities,
            row_identity_sha256=row_identity,
        ),
        states=payloads.array(
            case.states,
            row_identity_sha256=row_identity,
        ),
        accounted_response=payloads.array(
            case.accounted_response,
            row_identity_sha256=row_identity,
        ),
        mask=payloads.array(
            case.valid_mask,
            row_identity_sha256=row_identity,
        ),
        preprocessing_fit=substrate_preprocessing_receipt,
    )
    substrate_ref = _artifact_ref(substrate)

    graph_specification = GraphConstructionSpec(
        artifact_id=f"{case_id}-field-estimation-graph-spec",
        substrate=substrate_ref,
        purpose="field_estimation",
        family=_instrument_dev_executed(
            "graph_family",
            "mutual-knn",
        ),
        metric=_instrument_dev_executed(
            "graph_metric",
            "euclidean",
        ),
        scale=_instrument_dev_executed(
            "graph_scale",
            f"k-{case.spec.neighbor_count}",
        ),
        constructor_id=(
            "instrument-dev-mutual-knn-euclidean-"
            f"k-{case.spec.neighbor_count}-v0.1"
        ),
        deterministic_tie_policy="distance-then-vertex-id",
        allowed_role=FitRole.INSTRUMENT_DEV,
    )
    graph_specification_ref = _artifact_ref(graph_specification)
    graph = CandidateGraph(
        artifact_id=f"{case_id}-field-estimation-graph",
        substrate=substrate_ref,
        specification=graph_specification_ref,
        vertex_order_sha256=vertex_order,
        edge_order_sha256=edge_order,
        cycle_order_sha256=cycle_order,
        vertices=payloads.array(
            case.vertex_identities,
            row_identity_sha256=vertex_order,
        ),
        canonical_edges=payloads.array(
            case.edges,
            row_identity_sha256=edge_order,
        ),
        weights=payloads.array(
            case.graph_weights,
            row_identity_sha256=edge_order,
        ),
        connected_components=payloads.array(
            case.components,
            row_identity_sha256=vertex_order,
        ),
        degree_distribution=payloads.array(
            case.degree,
            row_identity_sha256=vertex_order,
        ),
        two_core=payloads.array(
            case.two_core_mask,
            row_identity_sha256=vertex_order,
        ),
        cycle_support=payloads.array(
            case.cycle_support,
            row_identity_sha256=cycle_order,
        ),
    )
    graph_ref = _artifact_ref(graph)

    support = SupportDiagnostic(
        artifact_id=f"{case_id}-f0-support",
        substrate=substrate_ref,
        row_identity_sha256=row_identity,
        scalar_definition_id="f0-local-covariance-spectrum-v0.1",
        neighborhood_specification=graph_ref,
        fit_role=FitRole.INSTRUMENT_DEV,
        values=payloads.array(
            case.f0_values,
            row_identity_sha256=row_identity,
        ),
        uncertainty=payloads.array(
            case.f0_uncertainty,
            row_identity_sha256=row_identity,
        ),
        support=payloads.array(
            case.f0_support,
            row_identity_sha256=row_identity,
        ),
        pointwise_reason_codes=payloads.array(
            case.f0_reason_codes,
            row_identity_sha256=row_identity,
        ),
        claim_ceiling=ClaimLevel.LEVEL_0,
    )

    f1_hypothesis = registry.require(
        HypothesisId.F1_PROJECTOR_CONNECTION
    )
    geometric_fit_receipt = payloads.opaque_json(
        {
            **receipt_common,
            "receipt_kind": "f1-estimator",
            "implementation_id": (
                "instrument-dev-local-rank-two-projector-even-probes"
            ),
            "registry_candidate_id": "local_rank_two_projector",
            "registry_choice_resolution": (
                f1_hypothesis.estimator.resolution.value
            ),
            "even_probe_indices": list(case.spec.even_probe_indices),
        }
    )
    geometric = GeometricFieldEstimate(
        artifact_id=f"{case_id}-f1-geometric-field",
        hypothesis_registry=registry_ref,
        substrate=substrate_ref,
        estimation_graph=graph_ref,
        hypothesis_id=HypothesisId.F1_PROJECTOR_CONNECTION,
        fit_receipt=geometric_fit_receipt,
        row_identity_sha256=row_identity,
        projector_or_frame=payloads.array(
            case.f1_frames,
            row_identity_sha256=row_identity,
        ),
        eigenspectrum=payloads.array(
            case.f1_eigenvalues,
            row_identity_sha256=row_identity,
        ),
        support=payloads.array(
            case.f1_support,
            row_identity_sha256=row_identity,
        ),
        gauge_law_id=f1_hypothesis.gauge_law,
        claim_ceiling=ClaimLevel.LEVEL_0,
    )

    f2_hypothesis = registry.require(
        HypothesisId.F2_LOCAL_COVARIANT_SECTION
    )
    input_binding = payloads.opaque_json(
        {
            **receipt_common,
            "receipt_kind": "f2-input-binding",
            "implementation_id": "odd-probe-section-observation-mean",
            "odd_probe_indices": list(case.spec.odd_probe_indices),
            "f1_field_artifact_id": geometric.artifact_id,
        }
    )
    order_fit_receipt = payloads.opaque_json(
        {
            **receipt_common,
            "receipt_kind": "f2-estimator",
            "implementation_id": (
                "instrument-dev-cross-fitted-local-frame-section"
            ),
            "registry_candidate_id": "cross_fitted_local_frame",
            "registry_choice_resolution": (
                f2_hypothesis.estimator.resolution.value
            ),
        }
    )
    order_specification = OrderParameterSpec(
        artifact_id=f"{case_id}-f2-order-parameter-spec",
        hypothesis_registry=registry_ref,
        substrate=substrate_ref,
        estimation_graph=graph_ref,
        hypothesis_id=HypothesisId.F2_LOCAL_COVARIANT_SECTION,
        input_binding=input_binding,
        fit_receipt=order_fit_receipt,
        target_manifold_id=f2_hypothesis.target_manifold,
        gauge_law_id=f2_hypothesis.gauge_law,
        charge_group=_fixed(
            "charge_group",
            f2_hypothesis.charge_group,
        ),
        amplitude_rule=_fixed(
            "amplitude_rule",
            f2_hypothesis.amplitude_quantity,
        ),
        identifiability_rule=_selection(
            "identifiability_rule",
            *f2_hypothesis.identifiability_quantities,
        ),
        interpolation_rule=f2_hypothesis.interpolation_rule,
        lift_rule=f2_hypothesis.lift_rule,
        trivialization_rule=f2_hypothesis.trivialization_rule,
        reference_rule=f2_hypothesis.reference_rule,
        forbidden_labels=f2_hypothesis.forbidden_labels,
        claim_ceiling=ClaimLevel.LEVEL_0,
    )
    order_specification_ref = _artifact_ref(order_specification)
    order_field = OrderParameterField(
        artifact_id=f"{case_id}-f2-order-parameter-field",
        specification=order_specification_ref,
        hypothesis_id=HypothesisId.F2_LOCAL_COVARIANT_SECTION,
        substrate=substrate_ref,
        estimation_graph=graph_ref,
        row_identity_sha256=row_identity,
        values=payloads.array(
            case.f2_coordinates,
            row_identity_sha256=row_identity,
        ),
        amplitude=payloads.array(
            case.f2_amplitude,
            row_identity_sha256=row_identity,
        ),
        frame_or_tensor=payloads.array(
            case.f1_frames,
            row_identity_sha256=row_identity,
        ),
        eigenspectrum=payloads.array(
            case.f1_eigenvalues,
            row_identity_sha256=row_identity,
        ),
        support=payloads.array(
            case.f2_support,
            row_identity_sha256=row_identity,
        ),
        pointwise_reason_codes=payloads.array(
            case.f2_reason_codes,
            row_identity_sha256=row_identity,
        ),
        claim_ceiling=ClaimLevel.LEVEL_0,
    )

    anchor = GroundTruthAnchor(
        artifact_id=f"{case_id}-ground-truth-anchor",
        substrate=substrate_ref,
        generator_id="representation-phantom-v0.1",
        generator_sha256=generator_module_sha256,
        role=FitRole.INSTRUMENT_DEV,
        anchor_kind="declared-zero-amplitude-center",
        row_identity_sha256=row_identity,
        supplied_support=payloads.array(
            case.center_support_mask,
            row_identity_sha256=row_identity,
        ),
        estimator_input_allowed=False,
        localization_gate_eligible=False,
        claim_ceiling=ClaimLevel.LEVEL_0,
    )

    artifacts: tuple[tuple[str, object], ...] = (
        ("candidate-graph", graph),
        ("f0-support", support),
        ("f1-geometric-field", geometric),
        ("f2-order-parameter-field", order_field),
        ("f2-order-parameter-spec", order_specification),
        ("graph-construction-spec", graph_specification),
        ("ground-truth-anchor", anchor),
        ("substrate-binding", substrate),
    )
    roots = (
        _artifact_ref(anchor),
        _artifact_ref(support),
        _artifact_ref(geometric),
        _artifact_ref(order_field),
    )
    return artifacts, roots


@dataclass(frozen=True, slots=True)
class _PublicationWorkspace:
    """Descriptor-anchored private staging state for one publication."""

    destination: Path
    parent_descriptor: int
    parent_identity: tuple[int, int]
    staging_leaf: str
    staging_path: Path
    staging_identity: tuple[int, int]


def _safe_destination(value: Path) -> Path:
    destination = Path(os.path.abspath(os.fspath(value)))
    if destination.name in {"", ".", ".."}:
        raise RepresentationPhantomBundleError(
            "output destination must name one directory"
        )
    return destination


def _secure_parent_open_flags() -> int:
    no_follow_any = getattr(os, "O_NOFOLLOW_ANY", None)
    directory_only = getattr(os, "O_DIRECTORY", None)
    if sys.platform != "darwin" or no_follow_any is None:
        raise RepresentationPhantomBundleError(
            "exclusive bundle publication requires Darwin O_NOFOLLOW_ANY"
        )
    if directory_only is None:
        raise RepresentationPhantomBundleError(
            "exclusive bundle publication requires directory-only opens"
        )
    return (
        os.O_RDONLY
        | directory_only
        | no_follow_any
        | getattr(os, "O_CLOEXEC", 0)
    )


def _identity(value: os.stat_result) -> tuple[int, int]:
    return value.st_dev, value.st_ino


def _verify_parent_display_identity(
    parent: Path,
    *,
    expected: tuple[int, int],
) -> None:
    descriptor: int | None = None
    try:
        descriptor = os.open(parent, _secure_parent_open_flags())
        observed = _identity(os.fstat(descriptor))
    except OSError as error:
        raise RepresentationPhantomBundleError(
            "output destination parent changed or became inaccessible"
        ) from error
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if observed != expected:
        raise RepresentationPhantomBundleError(
            "output destination parent identity changed"
        )


def _relative_stat(
    parent_descriptor: int,
    leaf: str,
) -> os.stat_result | None:
    try:
        return os.stat(
            leaf,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return None


def _open_publication_workspace(value: Path) -> _PublicationWorkspace:
    destination = _safe_destination(value)
    try:
        parent_descriptor = os.open(
            destination.parent,
            _secure_parent_open_flags(),
        )
    except OSError as error:
        raise RepresentationPhantomBundleError(
            "output destination parent chain must not contain symlinks and "
            "must name an existing real directory"
        ) from error

    try:
        parent_stat = os.fstat(parent_descriptor)
        if not stat.S_ISDIR(parent_stat.st_mode):
            raise RepresentationPhantomBundleError(
                "output destination parent must be a directory"
            )
        parent_identity = _identity(parent_stat)
        _verify_parent_display_identity(
            destination.parent,
            expected=parent_identity,
        )
        if (
            _relative_stat(parent_descriptor, destination.name)
            is not None
        ):
            raise RepresentationPhantomBundleError(
                "output destination must not already exist"
            )

        for _attempt in range(128):
            staging_leaf = (
                f".{destination.name}.staging-{uuid.uuid4().hex}"
            )
            try:
                os.mkdir(
                    staging_leaf,
                    mode=0o700,
                    dir_fd=parent_descriptor,
                )
            except FileExistsError:
                continue
            break
        else:
            raise RepresentationPhantomBundleError(
                "could not allocate a private staging directory"
            )

        staging_stat = _relative_stat(parent_descriptor, staging_leaf)
        if (
            staging_stat is None
            or not stat.S_ISDIR(staging_stat.st_mode)
        ):
            raise RepresentationPhantomBundleError(
                "private staging directory identity is unavailable"
            )
        return _PublicationWorkspace(
            destination=destination,
            parent_descriptor=parent_descriptor,
            parent_identity=parent_identity,
            staging_leaf=staging_leaf,
            staging_path=destination.parent / staging_leaf,
            staging_identity=_identity(staging_stat),
        )
    except Exception:
        os.close(parent_descriptor)
        raise


def _load_renameatx_np() -> object:
    if sys.platform != "darwin":
        raise RepresentationPhantomBundleError(
            "exclusive directory publication requires Darwin renameatx_np"
        )
    library = ctypes.util.find_library("System")
    if library is None:
        raise RepresentationPhantomBundleError(
            "Darwin libSystem is unavailable"
        )
    libc = ctypes.CDLL(library, use_errno=True)
    function = getattr(libc, "renameatx_np", None)
    if function is None:
        raise RepresentationPhantomBundleError(
            "Darwin renameatx_np is unavailable"
        )
    function.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    function.restype = ctypes.c_int
    return function


def _renameatx_np_no_replace(
    *,
    parent_descriptor: int,
    source_leaf: str,
    destination_leaf: str,
) -> None:
    renameatx_np = _load_renameatx_np()
    ctypes.set_errno(0)
    result = renameatx_np(
        parent_descriptor,
        os.fsencode(source_leaf),
        parent_descriptor,
        os.fsencode(destination_leaf),
        _RENAME_PUBLICATION_FLAGS,
    )
    if result == 0:
        return
    error_number = ctypes.get_errno()
    if error_number == errno.EEXIST:
        raise RepresentationPhantomBundleError(
            "output destination appeared before publication"
        )
    if error_number in {
        errno.EINVAL,
        getattr(errno, "ENOTSUP", errno.EINVAL),
        getattr(errno, "ENOSYS", errno.EINVAL),
    }:
        raise RepresentationPhantomBundleError(
            "filesystem does not support required exclusive publication"
        )
    raise RepresentationPhantomBundleError(
        "exclusive directory publication failed"
    ) from OSError(error_number, os.strerror(error_number))


def _publish_staging_no_replace(
    workspace: _PublicationWorkspace,
) -> tuple[int, int]:
    """Atomically publish a complete staging directory without replacement."""

    _verify_parent_display_identity(
        workspace.destination.parent,
        expected=workspace.parent_identity,
    )
    staged = _relative_stat(
        workspace.parent_descriptor,
        workspace.staging_leaf,
    )
    if (
        staged is None
        or not stat.S_ISDIR(staged.st_mode)
        or _identity(staged) != workspace.staging_identity
    ):
        raise RepresentationPhantomBundleError(
            "private staging directory identity changed before publication"
        )
    _renameatx_np_no_replace(
        parent_descriptor=workspace.parent_descriptor,
        source_leaf=workspace.staging_leaf,
        destination_leaf=workspace.destination.name,
    )
    if (
        _relative_stat(
            workspace.parent_descriptor,
            workspace.staging_leaf,
        )
        is not None
    ):
        raise RepresentationPhantomBundleError(
            "staging directory remained visible after publication"
        )
    published = _relative_stat(
        workspace.parent_descriptor,
        workspace.destination.name,
    )
    if (
        published is None
        or not stat.S_ISDIR(published.st_mode)
        or _identity(published) != workspace.staging_identity
    ):
        raise RepresentationPhantomBundleError(
            "published directory identity differs from staging"
        )
    _verify_parent_display_identity(
        workspace.destination.parent,
        expected=workspace.parent_identity,
    )
    return workspace.staging_identity


def _open_published_directory(
    workspace: _PublicationWorkspace,
) -> int:
    """Retain the exact published inode through post-publication validation."""

    try:
        descriptor = os.open(
            workspace.destination.name,
            _secure_parent_open_flags(),
            dir_fd=workspace.parent_descriptor,
        )
    except OSError as error:
        raise RepresentationPhantomBundleError(
            "published directory cannot be opened through the parent anchor"
        ) from error
    opened = os.fstat(descriptor)
    if (
        not stat.S_ISDIR(opened.st_mode)
        or _identity(opened) != workspace.staging_identity
    ):
        os.close(descriptor)
        raise RepresentationPhantomBundleError(
            "published directory descriptor differs from staging"
        )
    return descriptor


def emit_representation_phantom_bundle(
    protocol_path: Path,
    output_dir: Path,
) -> EmittedRepresentationPhantomBundle:
    """Generate, close, publish, and revalidate a Level-0 phantom bundle."""

    loaded_protocol = load_representation_phantom_protocol(protocol_path)
    protocol = loaded_protocol.protocol
    module_path = Path(__file__).with_name("representation_phantom.py")
    generator_module_sha256 = protocol.source.generator_module_sha256
    generator_source_bytes = _read_generator_source(
        module_path,
        expected_sha256=generator_module_sha256,
    )
    _verify_generator_revision(
        repository_root=_repository_root(),
        revision=protocol.source.generator_revision,
        generator_module_sha256=generator_module_sha256,
    )

    registry_source_path = _resolve_registry_path(loaded_protocol)
    loaded_registry = load_hypothesis_registry(
        registry_source_path,
        expected_source_sha256=protocol.registry.source_sha256,
        expected_canonical_sha256=protocol.registry.canonical_sha256,
    )
    registry_source_bytes = registry_source_path.read_bytes()
    if _sha256(registry_source_bytes) != loaded_registry.source_sha256:
        raise RepresentationPhantomBundleError(
            "registry changed after strict loading"
        )

    with _bound_generator_module(
        module_path=module_path,
        source_bytes=generator_source_bytes,
    ) as generator_module:
        bound_spec = generator_module.RepresentationPhantomSpec(
            **protocol.generator.to_dict()
        )
        phantom = generator_module.RepresentationPhantom.generate(bound_spec)
        phantom.validate()
    protocol_case_ids = tuple(case.case_id for case in protocol.cases)
    generated_case_ids = tuple(case.case_id for case in phantom.cases)
    if generated_case_ids != protocol_case_ids:
        raise RepresentationPhantomBundleError(
            "generated case order differs from the protocol"
        )

    workspace = _open_publication_workspace(Path(output_dir))
    destination = workspace.destination
    staging_path = workspace.staging_path
    try:
        for name in ("artifacts", "external", "payloads"):
            (staging_path / name).mkdir()

        registry_bundle_path = (
            staging_path / "external" / "hypothesis-registry.yaml"
        )
        registry_bundle_path.write_bytes(registry_source_bytes)
        registry_ref = _external_ref(
            ArtifactType.HYPOTHESIS_REGISTRY,
            artifact_id=loaded_registry.registry.registry_id,
            canonical_sha256=loaded_registry.canonical_sha256,
        )
        registry_entry = BundleArtifactEntry(
            path="external/hypothesis-registry.yaml",
            source_sha256=loaded_registry.source_sha256,
            reference=registry_ref,
        )

        payload_writer = _PayloadWriter(staging_path)
        resource_budget = bound_spec.to_dict()["resource_budget"]
        if not isinstance(resource_budget, dict):
            raise RepresentationPhantomBundleError(
                "bound generator resource budget must be a mapping"
            )
        substrate_preprocessing_receipt = payload_writer.opaque_json(
            _substrate_preprocessing_receipt_document(
                loaded_protocol,
                resource_budget=resource_budget,
            )
        )
        artifact_entries: list[BundleArtifactEntry] = []
        roots: list[ArtifactRef] = []
        for case in phantom.cases:
            case_artifacts, case_roots = _case_artifacts(
                case,
                payloads=payload_writer,
                registry_ref=registry_ref,
                registry=loaded_registry.registry,
                substrate_preprocessing_receipt=(
                    substrate_preprocessing_receipt
                ),
                generator_module_sha256=generator_module_sha256,
                generator_revision=protocol.source.generator_revision,
                protocol_id=protocol.protocol_id,
                protocol_source_sha256=loaded_protocol.source_sha256,
                protocol_canonical_sha256=loaded_protocol.canonical_sha256,
            )
            for name, artifact in case_artifacts:
                artifact_entries.append(
                    _artifact_entry(
                        staging_path,
                        case_id=case.case_id,
                        name=name,
                        artifact=artifact,
                    )
                )
            roots.extend(case_roots)

        bundle_id = (
            "representation-phantom-"
            f"{loaded_protocol.canonical_sha256[:16]}-"
            f"{phantom.canonical_sha256[:16]}"
        )
        root_tuple = tuple(
            sorted(
                roots,
                key=lambda reference: (
                    reference.artifact_type.value,
                    reference.artifact_id,
                    reference.schema_version,
                    reference.canonical_sha256,
                ),
            )
        )
        manifest = InstrumentBundleManifest(
            bundle_id=bundle_id,
            roots=root_tuple,
            instrument_artifacts=tuple(
                sorted(
                    artifact_entries,
                    key=lambda entry: entry.sort_key,
                )
            ),
            hypothesis_registries=(registry_entry,),
            context_banks=(),
            payloads=payload_writer.entries,
            subject_data_access_authorized=False,
        )
        manifest_path = staging_path / "bundle.json"
        manifest_path.write_bytes(manifest.canonical_bytes)

        staged_loaded = load_instrument_bundle(
            manifest_path,
            expected_source_sha256=manifest.canonical_sha256,
            expected_canonical_sha256=manifest.canonical_sha256,
        )
        _publish_staging_no_replace(workspace)
        # Publication is a single exclusive namespace transition. From this
        # point onward the owned tree is preserved for forensic inspection if
        # the second validation fails; it is never recursively rolled back.

        published_manifest_path = destination / "bundle.json"
        published_descriptor = _open_published_directory(workspace)
        try:
            published_loaded = load_instrument_bundle(
                published_manifest_path,
                expected_source_sha256=manifest.canonical_sha256,
                expected_canonical_sha256=manifest.canonical_sha256,
                expected_root_identity=workspace.staging_identity,
            )
            if (
                _identity(os.fstat(published_descriptor))
                != workspace.staging_identity
            ):
                raise RepresentationPhantomBundleError(
                    "published directory identity changed during validation"
                )
            _verify_parent_display_identity(
                destination.parent,
                expected=workspace.parent_identity,
            )
        finally:
            os.close(published_descriptor)
        if (
            published_loaded.canonical_sha256
            != staged_loaded.canonical_sha256
        ):
            raise RepresentationPhantomBundleError(
                "published bundle identity differs from staging"
            )
        return EmittedRepresentationPhantomBundle(
            manifest_path=published_manifest_path,
            canonical_sha256=published_loaded.canonical_sha256,
            source_sha256=published_loaded.source_sha256,
            bundle_id=manifest.bundle_id,
            protocol_source_sha256=loaded_protocol.source_sha256,
            protocol_canonical_sha256=loaded_protocol.canonical_sha256,
            substrate_preprocessing_receipt_sha256=(
                substrate_preprocessing_receipt.sha256
            ),
            generator_module_sha256=generator_module_sha256,
            registry_source_sha256=loaded_registry.source_sha256,
            registry_canonical_sha256=loaded_registry.canonical_sha256,
            case_ids=generated_case_ids,
            artifact_count=len(manifest.instrument_artifacts),
            payload_count=len(manifest.payloads),
            cross_manifest_join_count=(
                published_loaded.cross_manifest_join_count
            ),
            resource_budget_estimator_id=str(
                resource_budget["estimator_id"]
            ),
            resource_budget_safety_factor=int(
                resource_budget["safety_factor"]
            ),
            estimated_peak_bytes=int(
                resource_budget["estimated_peak_bytes"]
            ),
            estimated_output_bytes=int(
                resource_budget["estimated_output_bytes"]
            ),
            max_estimated_peak_bytes=int(
                resource_budget["max_estimated_peak_bytes"]
            ),
            max_estimated_output_bytes=int(
                resource_budget["max_estimated_output_bytes"]
            ),
            resource_budget_claim_boundary=str(
                resource_budget["claim_boundary"]
            ),
        )
    finally:
        # Unpublished staging is intentionally retained on failure. A
        # stat-then-rmtree cleanup cannot be made inode-bound against a
        # concurrent staging-leaf replacement, so fail closed without delete.
        os.close(workspace.parent_descriptor)
