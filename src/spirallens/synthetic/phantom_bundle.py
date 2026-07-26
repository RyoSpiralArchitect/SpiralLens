"""Canonical closed-bundle emission for representation-shaped phantoms.

The emitter is deliberately limited to instrument-development observations.
It emits F0/F1/F2 artifacts at Level 0, but it does not select a graph family,
qualify an instrument, localize a core, construct a loop, estimate winding,
or authorize model or subject access.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import io
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
from types import ModuleType
from typing import TYPE_CHECKING, Iterator
import uuid

import numpy as np
from numpy.typing import NDArray

from spirallens.contexts import (
    BankStatus,
    ContextBank,
    ContextRole,
    ContextSpec,
    ModelBinding,
    SourceBinding,
    SweepDomain,
    TokenizerBinding,
    load_context_bank,
)
from spirallens.instrument_contracts import (
    ARTIFACT_SCHEMA_VERSION_BY_TYPE,
    ArtifactRef,
    ArtifactType,
    BundleArtifactEntry,
    BundleContextBankEntry,
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
    SubstrateBinding,
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


PSEUDO_MODEL_ID = (
    "spirallens.synthetic.representation-phantom-pseudo-model"
)
ADDRESS_INDEXER_ID = (
    "spirallens.synthetic.representation-phantom-address-indexer"
)
CONTEXT_TO_FIT_ROLE = {
    ContextRole.EXAMPLE: FitRole.INSTRUMENT_DEV,
}
_D0_D8 = tuple((f"d{index}", "not_run") for index in range(9))
_GENERATOR_REPOSITORY_PATH = (
    "src/spirallens/synthetic/representation_phantom.py"
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
            "validation_scope": self.validation_scope,
            "qualification_status": self.qualification_status,
            "synthetic_qualified": self.synthetic_qualified,
            "claim_ceiling": ClaimLevel.LEVEL_0.value,
            "fit_role": FitRole.INSTRUMENT_DEV.value,
            "context_role": ContextRole.EXAMPLE.value,
            "context_role_mapping": {
                ContextRole.EXAMPLE.value: FitRole.INSTRUMENT_DEV.value,
            },
            "numeric_payloads_self_audited": True,
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


def _generated_context_bank(
    loaded: LoadedRepresentationPhantomProtocol,
    *,
    row_count: int,
    generator_module_sha256: str,
) -> ContextBank:
    protocol = loaded.protocol
    revision = protocol.source.generator_revision
    bank_id = (
        "representation-phantom-example-"
        f"{loaded.canonical_sha256[:20]}"
    )
    bank = ContextBank(
        bank_id=bank_id,
        status=BankStatus.EXAMPLE,
        license="Apache-2.0",
        claim_eligible=False,
        source=SourceBinding(
            kind="project_authored_synthetic",
            source_id=protocol.protocol_id,
        ),
        model=ModelBinding(
            model_id=PSEUDO_MODEL_ID,
            requested_revision=revision,
            resolved_revision=revision,
            vocab_size=row_count,
        ),
        tokenizer=TokenizerBinding(
            tokenizer_id=ADDRESS_INDEXER_ID,
            requested_revision=revision,
            resolved_revision=revision,
            addressable_size=row_count,
            tokenizer_class="DeterministicAddressIndexer",
            implementation="slow",
            transformers_version="not-applicable",
            tokenizers_version="not-applicable",
            add_special_tokens=False,
            file_sha256=(
                (
                    "representation_phantom.py",
                    generator_module_sha256,
                ),
            ),
        ),
        sweep_domain=SweepDomain.TOKENIZER_ADDRESSABLE,
        contexts=(
            ContextSpec(
                context_id="representation-phantom-address-only",
                role=ContextRole.EXAMPLE,
                family_id="synthetic-address-index",
                source_id=protocol.protocol_id,
                template_id="address-only",
                template_ids=(None,),
                attention_mask=(1,),
                observation_position=0,
            ),
        ),
    )
    expected_fit_role = CONTEXT_TO_FIT_ROLE.get(bank.role)
    if (
        bank.role is not ContextRole.EXAMPLE
        or bank.claim_eligible
        or expected_fit_role is not FitRole.INSTRUMENT_DEV
        or protocol.execution.context_role != bank.role.value
        or protocol.execution.fit_role != expected_fit_role.value
    ):
        raise RepresentationPhantomBundleError(
            "example context to instrument_dev mapping is not authorized"
        )
    return bank


def _substrate_preprocessing_receipt_document(
    loaded: LoadedRepresentationPhantomProtocol,
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
            "context_role": ContextRole.EXAMPLE.value,
            "context_claim_eligible": False,
            "numeric_payloads_self_audited": True,
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
    context_ref: ArtifactRef,
    substrate_preprocessing_receipt: PayloadRef,
    generator_module_sha256: str,
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
    substrate = SubstrateBinding(
        artifact_id=f"{case_id}-substrate",
        role=FitRole.INSTRUMENT_DEV,
        evolution_axis=EvolutionAxis.SYNTHETIC_LATTICE,
        row_identity_sha256=row_identity,
        context_bank=context_ref,
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
        family=_selection(
            "graph_family",
            "mutual-knn",
            "symmetric-knn",
        ),
        metric=_selection(
            "graph_metric",
            "cosine",
            "euclidean",
        ),
        scale=_selection(
            "graph_scale",
            f"k-{case.spec.neighbor_count}",
            "radius-local",
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


def _safe_destination(value: Path) -> Path:
    destination = value.absolute()
    if destination.exists() or destination.is_symlink():
        raise RepresentationPhantomBundleError(
            "output destination must not already exist"
        )
    parent = destination.parent
    if not parent.exists() or not parent.is_dir():
        raise RepresentationPhantomBundleError(
            "output destination parent must be an existing directory"
        )
    cursor = parent
    while True:
        if cursor.is_symlink():
            raise RepresentationPhantomBundleError(
                "output destination parent chain must not contain symlinks"
            )
        if cursor == cursor.parent:
            break
        cursor = cursor.parent
    return destination


def _remove_reserved_destination(
    destination: Path,
    *,
    identity: tuple[int, int],
) -> None:
    """Remove only the exact directory inode reserved by this emitter."""

    try:
        current = os.lstat(destination)
    except FileNotFoundError:
        return
    if (
        not stat.S_ISDIR(current.st_mode)
        or (current.st_dev, current.st_ino) != identity
    ):
        return
    shutil.rmtree(destination)


def _publish_staging_no_replace(
    staging_path: Path,
    destination: Path,
) -> tuple[int, int]:
    """Reserve without replacement and publish the manifest entrypoint last."""

    try:
        os.mkdir(destination, mode=0o700)
    except FileExistsError as error:
        raise RepresentationPhantomBundleError(
            "output destination appeared before publication"
        ) from error
    except OSError as error:
        raise RepresentationPhantomBundleError(
            "output destination reservation failed"
        ) from error

    reserved = os.lstat(destination)
    identity = (reserved.st_dev, reserved.st_ino)
    try:
        for name in ("artifacts", "external", "payloads"):
            os.rename(staging_path / name, destination / name)
        os.rename(
            staging_path / "bundle.json",
            destination / "bundle.json",
        )
        os.rmdir(staging_path)
    except Exception:
        _remove_reserved_destination(destination, identity=identity)
        raise
    return identity


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

    destination = _safe_destination(Path(output_dir))
    staging_path = Path(
        tempfile.mkdtemp(
            prefix=f".{destination.name}.staging-",
            dir=destination.parent,
        )
    )
    published = False
    reserved_destination_identity: tuple[int, int] | None = None
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

        context_bank = _generated_context_bank(
            loaded_protocol,
            row_count=phantom.spec.row_count,
            generator_module_sha256=generator_module_sha256,
        )
        context_bytes = canonical_json_bytes(context_bank.to_dict())
        context_bundle_path = (
            staging_path / "external" / "context-bank.json"
        )
        context_bundle_path.write_bytes(context_bytes)
        context_source_sha256 = _sha256(context_bytes)
        loaded_context = load_context_bank(
            context_bundle_path,
            allowed_roles={ContextRole.EXAMPLE},
            expected_source_sha256=context_source_sha256,
            expected_canonical_sha256=context_bank.sha256,
        )
        context_ref = _external_ref(
            ArtifactType.CONTEXT_BANK,
            artifact_id=context_bank.bank_id,
            canonical_sha256=context_bank.sha256,
        )
        context_entry = BundleContextBankEntry(
            path="external/context-bank.json",
            source_sha256=loaded_context.source_sha256,
            reference=context_ref,
            allowed_role=ContextRole.EXAMPLE,
        )

        payload_writer = _PayloadWriter(staging_path)
        substrate_preprocessing_receipt = payload_writer.opaque_json(
            _substrate_preprocessing_receipt_document(loaded_protocol)
        )
        artifact_entries: list[BundleArtifactEntry] = []
        roots: list[ArtifactRef] = []
        for case in phantom.cases:
            case_artifacts, case_roots = _case_artifacts(
                case,
                payloads=payload_writer,
                registry_ref=registry_ref,
                registry=loaded_registry.registry,
                context_ref=context_ref,
                substrate_preprocessing_receipt=(
                    substrate_preprocessing_receipt
                ),
                generator_module_sha256=generator_module_sha256,
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
            context_banks=(context_entry,),
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
        reserved_destination_identity = _publish_staging_no_replace(
            staging_path,
            destination,
        )

        published_manifest_path = destination / "bundle.json"
        published_loaded = load_instrument_bundle(
            published_manifest_path,
            expected_source_sha256=manifest.canonical_sha256,
            expected_canonical_sha256=manifest.canonical_sha256,
        )
        if (
            published_loaded.canonical_sha256
            != staged_loaded.canonical_sha256
        ):
            raise RepresentationPhantomBundleError(
                "published bundle identity differs from staging"
            )
        published = True
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
        )
    finally:
        if not published and staging_path.exists():
            shutil.rmtree(staging_path)
        if (
            not published
            and reserved_destination_identity is not None
        ):
            _remove_reserved_destination(
                destination,
                identity=reserved_destination_identity,
            )
