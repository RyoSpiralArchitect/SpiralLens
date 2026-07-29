"""Deterministic, model-free D0--D5 calibration-selection execution.

This module is the sole adapter from a frozen :class:`QualificationProtocol`
to a :class:`QualificationResult`.  It executes the exact Cartesian numeric
substrate and manifests declared by the protocol; no selection constant is
duplicated here.

The two inferential axes remain separate:

* D2 emits a Level-0 localized low-amplitude/core candidate on the three
  inherited field-estimation graphs (A).
* D4 evaluates continuous sampled-phase totals on A x B x loop-role cells.

Every prediction is sealed before the corresponding oracle object is read.
After scoring, those source-enforced content dependencies are reconstructed
as a complete digest-chained logical manifest.  That manifest is not a
real-time or independently observed event log.
Observed loop totals are never rounded or persisted as integer claims.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import math
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from .launch import SelectionLaunchAuthorization

from spirallens.core.canonical import canonical_json_bytes, canonical_json_sha256
from spirallens.graphs import BoundaryRefinementRule, GraphInput
from spirallens.qualification.pipeline_metamorphic import (
    run_cartesian_pipeline_metamorphic_checks,
)
from spirallens.synthetic.cartesian_fourier_domain_phantom import (
    CARTESIAN_FOURIER_FIXED_NULL,
    CARTESIAN_FOURIER_NO_CORE_NULL,
    CARTESIAN_FOURIER_POSITIVE,
    CARTESIAN_FOURIER_PREREQUISITE_FAILURE,
    CartesianExpectedDisposition,
    CartesianFourierCase,
    CartesianFourierDomainGenerator,
    CartesianFourierDomainSpec,
    evaluate_oracle_sampled_response,
)
from spirallens.synthetic.cartesian_fourier_estimator import (
    CARTESIAN_FOURIER_FIELD_ESTIMATOR_ID,
    CartesianFourierFieldEstimate,
    estimate_cartesian_fourier_field,
)
from spirallens.synthetic.representation_estimator import (
    REPRESENTATION_FIELD_ESTIMATOR_ID,
    RepresentationEstimatorInputs,
    RepresentationFieldEstimate,
    build_representation_estimator_inputs,
    estimate_representation_field,
)
from spirallens.synthetic.representation_phantom import (
    RepresentationPhantom,
    RepresentationPhantomSpec,
)

from .aggregation import (
    aggregate_d4_d5,
    build_d2_gate,
    collapse_core_primary_units,
    materialize_expected_core_cells,
)
from .blind import BlindCoreInput, SealedCorePrediction, build_blind_core_input
from .common import (
    AttemptStatus,
    CoreDisposition,
    CorePredictionClass,
    EvaluationUnit,
    LoopDisposition,
    LoopPredictionClass,
    ObligationMode,
    QualificationContractError,
    QualificationState,
    array_fingerprint,
    fingerprint_mapping,
    require_sha256,
)
from .contracts import (
    CoreCellSummary,
    CorePrimaryUnitSummary,
    CrossedCellSummary,
    CrossedNonvacuitySummary,
    GateEvidenceSummary,
    PrimaryUnitSummary,
    QualificationGateId,
    QualificationResult,
    StaticEvidenceReceipt,
    build_qualification_lane_event_payloads,
    derive_static_gate,
    qualification_result_evidence_root_sha256,
)
from .crossed import (
    CrossedGraphExecution,
    assess_crossed_nonvacuity,
    build_crossed_blind_core_input,
    build_crossed_blind_loop_input,
    build_crossed_graph_execution,
    construct_declared_graph,
    domain_construction_sha256,
    rectangular_grid_support_faces,
    support_construction_sha256,
)
from .evidence_bundle import (
    CoreCellEvaluationReceipt,
    D1FamilyExecutionReceipt,
    D2CoreConfounderCellReceipt,
    D2CoreConfounderMatrixReceipt,
    D3PipelineExecutionReceipt,
    LoopCellEvaluationReceipt,
    NonvacuityEvaluationReceipt,
    QualificationEvidenceBundle,
)
from .freeze import (
    PersistedSelectionTerminalIdentity,
    SelectionAttemptClaimArtifact,
    SelectionConsumptionArtifact,
    SelectionFailedAttemptArtifact,
    SelectionFreezeArtifact,
    SelectionTerminalManifestArtifact,
    TerminalAttemptArtifactKind,
    begin_selection_execution,
    load_terminal_selection_consumption,
    publish_terminal_selection_consumption,
    selection_execution_start_path,
    terminal_selection_transaction_path,
    validate_persisted_selection_attempt_claim,
    validate_persisted_selection_execution_start,
)
from .metamorphic import (
    ambient_signed_permutation_check,
    local_frame_gauge_check,
    loop_reversal_check,
    nonorientable_control_check,
    reference_orientation_check,
    spin_two_double_angle_check,
)
from .persistence import LoadedQualificationProtocol
from .prerequisites import (
    CORE_ESTIMATOR_ID,
    REASON_CORE_AMPLITUDE_NOT_LOCALIZED,
    REASON_EMPTY_GRAPH,
    CorePrerequisitePolicy,
    build_core_oracle_truth,
    estimate_and_seal_core,
    score_core_prediction,
)
from .protocol import (
    CLOSED_CARTESIAN_ESTIMATOR_ID,
    CLOSED_CARTESIAN_GENERATOR_FAMILY_ID,
    CLOSED_CARTESIAN_TRIVIALIZATION_ID,
    CLOSED_CORE_LOCALIZER_ID,
    CLOSED_REPRESENTATION_ESTIMATOR_ID,
    CLOSED_REPRESENTATION_TRIVIALIZATION_ID,
    D2_IDENTIFIABILITY_LOSS_DECOY_CONSTRUCTION_ID,
    D2_MISSING_CANDIDATE_SUPPORT_CONSTRUCTION_ID,
    F2_LOCAL_COVARIANT_SECTION_REFERENT_ID,
    BoundaryTemplate,
    ControlDeclaration,
    ExpectedCell,
    ExpectedCoreCell,
    LoopRole,
    ModuleDigest,
    QualificationProtocol,
    StressAssignment,
)
from .source_binding import (
    QualificationEventLedger,
    QualificationSourceBindingError,
    QualificationSourceBindingReceipt,
    QualificationSourceBindingSummary,
    module_repository_path,
    qualification_event_lane_ids,
    verify_protocol_source_binding,
)
from .winding import (
    REASON_BOUNDARY_AMPLITUDE_FLOOR,
    REASON_BOUNDARY_COHERENCE_FLOOR,
    REASON_BOUNDARY_IDENTIFIABILITY_FLOOR,
    REASON_LOOP_ROWS_REPEATED,
    REASON_LOOP_SUPPORT,
    BlindLoopInput,
    LoopPhasePolicy,
    SealedLoopPrediction,
    build_blind_loop_input,
    build_loop_oracle_truth,
    estimate_and_seal_loop,
    score_loop_prediction,
)

FloatArray = NDArray[np.float64]
Int64Array = NDArray[np.int64]

RUNNER_SCHEMA_VERSION = "spirallens.qualification-runner.v0.4"
ORCHESTRATED_FAILURE_EVIDENCE_SCHEMA_VERSION = (
    "spirallens.orchestrated-selection-failure-evidence.v0.1"
)
ORCHESTRATED_FAILURE_STAGE = "closed-selection-execution-or-publication"
ORCHESTRATED_TERMINAL_PUBLICATION_RECEIPT_SCHEMA_VERSION = (
    "spirallens.orchestrated-terminal-publication-receipt.v0.1"
)
ORCHESTRATED_TERMINAL_PUBLICATION_RECEIPT_ATTRIBUTE = (
    "spirallens_terminal_publication_receipt"
)
REPRESENTATION_METAMORPHIC_DEVELOPMENT_SEED = 314159
REPRESENTATION_METAMORPHIC_TOLERANCE = 2e-10

_ENGINE_ENTRY_MODULES = ("spirallens.qualification.runner",)
_SPIRALLENS_SOURCE_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class OrchestratedTerminalPublicationReceipt:
    """Machine-readable proof that one visible terminal strictly round-tripped."""

    terminal_transaction_path: str
    manifest_sha256: str
    terminal_artifact_kind: TerminalAttemptArtifactKind
    terminal_artifact_sha256: str
    consumption_sha256: str
    schema_version: str = ORCHESTRATED_TERMINAL_PUBLICATION_RECEIPT_SCHEMA_VERSION
    strict_roundtrip_verified: bool = True
    original_exception_preserved: bool = True
    publication_call_returned: bool = True
    parent_directory_durability_fsync_proved: bool = True
    retry_authorized: bool = False

    def __post_init__(self) -> None:
        path = Path(self.terminal_transaction_path)
        if (
            not isinstance(self.terminal_transaction_path, str)
            or not path.is_absolute()
        ):
            raise QualificationContractError(
                "terminal publication receipt path must be absolute"
            )
        for name in (
            "manifest_sha256",
            "terminal_artifact_sha256",
            "consumption_sha256",
        ):
            require_sha256(
                getattr(self, name),
                label=f"terminal publication receipt {name}",
            )
        if (
            self.schema_version
            != ORCHESTRATED_TERMINAL_PUBLICATION_RECEIPT_SCHEMA_VERSION
            or not isinstance(
                self.terminal_artifact_kind,
                TerminalAttemptArtifactKind,
            )
            or self.strict_roundtrip_verified is not True
            or self.original_exception_preserved is not True
            or type(self.publication_call_returned) is not bool
            or type(self.parent_directory_durability_fsync_proved) is not bool
            or self.retry_authorized is not False
        ):
            raise QualificationContractError(
                "terminal publication receipt constants differ from the contract"
            )
        if (
            self.publication_call_returned
            is not self.parent_directory_durability_fsync_proved
        ):
            raise QualificationContractError(
                "terminal receipt publication-return and parent-fsync facts "
                "must be the same conservative state"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "terminal_transaction_path": self.terminal_transaction_path,
            "manifest_sha256": self.manifest_sha256,
            "terminal_artifact_kind": self.terminal_artifact_kind.value,
            "terminal_artifact_sha256": self.terminal_artifact_sha256,
            "consumption_sha256": self.consumption_sha256,
            "strict_roundtrip_verified": self.strict_roundtrip_verified,
            "original_exception_preserved": self.original_exception_preserved,
            "publication_call_returned": self.publication_call_returned,
            "parent_directory_durability_fsync_proved": (
                self.parent_directory_durability_fsync_proved
            ),
            "retry_authorized": self.retry_authorized,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())


def _local_module_source_path(module: str) -> Path | None:
    """Resolve one in-repository module without importing it."""

    if module != "spirallens" and not module.startswith("spirallens."):
        return None
    stem = _SPIRALLENS_SOURCE_ROOT.joinpath(*module.split("."))
    candidates = (stem.with_suffix(".py"), stem / "__init__.py")
    existing = tuple(path for path in candidates if path.is_file())
    if len(existing) > 1:
        raise QualificationContractError(
            f"engine module {module!r} has ambiguous module and package sources"
        )
    return existing[0] if existing else None


def _local_import_targets(module: str, source_path: Path) -> tuple[str, ...]:
    """Return statically declared local imports from one exact source file."""

    try:
        tree = ast.parse(source_path.read_bytes(), filename=str(source_path))
    except (OSError, SyntaxError) as error:
        raise QualificationContractError(
            f"cannot inspect engine imports for {module!r}"
        ) from error
    package = module if source_path.name == "__init__.py" else module.rpartition(".")[0]
    targets: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                callable_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                callable_name = node.func.attr
            else:
                callable_name = ""
            if callable_name in {
                "__import__",
                "import_module",
                "module_from_spec",
                "spec_from_file_location",
            }:
                raise QualificationContractError(
                    f"engine module {module!r} uses forbidden dynamic "
                    f"execution/import primitive {callable_name!r}"
                )
        if isinstance(node, ast.Import):
            candidates = (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                try:
                    base = importlib.util.resolve_name(
                        "." * node.level + (node.module or ""),
                        package,
                    )
                except (ImportError, ValueError) as error:
                    raise QualificationContractError(
                        f"cannot resolve relative engine import in {module!r}"
                    ) from error
            else:
                base = node.module or ""
            expanded = [base]
            expanded.extend(f"{base}.{alias.name}" for alias in node.names)
            candidates = iter(expanded)
        else:
            continue
        for candidate in candidates:
            if _local_module_source_path(candidate) is not None:
                targets.add(candidate)
    return tuple(sorted(targets))


def _runtime_engine_module_closure(
    entry_modules: tuple[str, ...],
) -> frozenset[str]:
    """Close engine entries over local imports and every package initializer."""

    pending = list(entry_modules)
    closed: set[str] = set()
    while pending:
        module = pending.pop()
        if module in closed:
            continue
        source_path = _local_module_source_path(module)
        if source_path is None:
            raise QualificationContractError(
                f"engine entry or dependency {module!r} has no local Python source"
            )
        closed.add(module)
        parts = module.split(".")
        for count in range(1, len(parts)):
            package = ".".join(parts[:count])
            if package not in closed and _local_module_source_path(package) is not None:
                pending.append(package)
        pending.extend(_local_import_targets(module, source_path))
    return frozenset(closed)


# Exact positive side of InstrumentSelection.  The closure starts at the
# executable runner, follows every in-repository import transitively, and
# includes every parent package ``__init__.py`` that Python executes on the
# way.  A newly imported dependency therefore becomes required without a
# hand-maintained allowlist update.
REQUIRED_ENGINE_MODULES = _runtime_engine_module_closure(_ENGINE_ENTRY_MODULES)

_BOUND_RUNTIME_CALLABLES = {
    "construct_declared_graph": construct_declared_graph,
    "estimate_and_seal_core": estimate_and_seal_core,
    "estimate_and_seal_loop": estimate_and_seal_loop,
    "estimate_cartesian_fourier_field": estimate_cartesian_fourier_field,
    "estimate_representation_field": estimate_representation_field,
}


def _validate_in_process_callable_bindings() -> None:
    """Reject accidental runtime replacement of the critical runner aliases.

    This is a narrow integrity tripwire, not hostile-process attestation.  A
    caller able to rewrite arbitrary module state can also rewrite this map,
    which is why the source receipt explicitly keeps hostile-local-mutation
    resistance false.
    """

    for name, expected in _BOUND_RUNTIME_CALLABLES.items():
        if globals().get(name) is not expected:
            raise QualificationSourceBindingError(
                f"critical in-process runner callable {name!r} was replaced"
            )


_CONTROL_CASE_REGISTRY = {
    (CoreDisposition.LOCALIZED_CORE, LoopDisposition.NONZERO): (
        CARTESIAN_FOURIER_POSITIVE
    ),
    (CoreDisposition.LOCALIZED_CORE, LoopDisposition.NULL): (
        CARTESIAN_FOURIER_FIXED_NULL
    ),
    (CoreDisposition.NO_CORE, LoopDisposition.NULL): (CARTESIAN_FOURIER_NO_CORE_NULL),
    (
        CoreDisposition.PREREQUISITE_FAILURE,
        LoopDisposition.PREREQUISITE_FAILURE,
    ): CARTESIAN_FOURIER_PREREQUISITE_FAILURE,
}


@dataclass(frozen=True, slots=True)
class _RepresentationEvidence:
    runtime_receipt: D1FamilyExecutionReceipt
    positive_inputs: RepresentationEstimatorInputs
    positive_estimates: tuple[RepresentationFieldEstimate, ...]


@dataclass(frozen=True, slots=True)
class _RepresentationMetamorphicEvidence:
    runtime_receipt: D3PipelineExecutionReceipt


@dataclass(frozen=True, slots=True)
class _PrimaryRun:
    core_cells: tuple[CoreCellSummary, ...]
    core_evidence: tuple[CoreCellEvaluationReceipt, ...]
    core_template: CorePrimaryUnitSummary
    loop_cells: tuple[CrossedCellSummary, ...]
    loop_evidence: tuple[LoopCellEvaluationReceipt, ...]
    loop_template: PrimaryUnitSummary
    nonvacuity: CrossedNonvacuitySummary
    nonvacuity_evidence: NonvacuityEvaluationReceipt


def module_source_sha256(module: str) -> str:
    """Hash the exact Python module source or package ``__init__.py``."""

    if not isinstance(module, str) or not module:
        raise QualificationContractError("module must be a nonempty string")
    specification = importlib.util.find_spec(module)
    if specification is None or specification.origin is None:
        raise QualificationContractError(f"engine module {module!r} cannot be resolved")
    path = Path(specification.origin)
    if path.suffix != ".py" or not path.is_file():
        raise QualificationContractError(
            f"engine module {module!r} is not backed by Python source"
        )
    expected_path = (
        Path(__file__).resolve().parents[3] / module_repository_path(module)
    ).resolve()
    if path.resolve() != expected_path:
        raise QualificationContractError(
            f"engine module {module!r} did not resolve inside this repository"
        )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_source_and_protocol(
    protocol: QualificationProtocol,
    *,
    protocol_source_sha256: str,
    source_binding_receipt: QualificationSourceBindingReceipt,
) -> QualificationSourceBindingSummary:
    if not isinstance(protocol, QualificationProtocol):
        raise TypeError("protocol must be a QualificationProtocol")
    require_sha256(protocol_source_sha256, label="protocol_source_sha256")
    if not isinstance(source_binding_receipt, QualificationSourceBindingReceipt):
        raise TypeError(
            "source_binding_receipt must be a QualificationSourceBindingReceipt"
        )
    if (
        source_binding_receipt.engine != protocol.engine
        or source_binding_receipt.registry != protocol.registry
    ):
        raise QualificationContractError(
            "source-binding receipt differs from the protocol declarations"
        )

    declared = {item.module: item.sha256 for item in protocol.engine.modules}
    missing = sorted(REQUIRED_ENGINE_MODULES - set(declared))
    if missing:
        raise QualificationContractError(
            f"engine binding omits required runner modules: {missing}"
        )
    for module, expected in sorted(declared.items()):
        if module_source_sha256(module) != expected:
            raise QualificationContractError(
                f"runtime module digest differs for {module!r}"
            )

    if protocol.domain.domain_construction_sha256 != domain_construction_sha256():
        raise QualificationContractError(
            "protocol domain construction differs from the runner"
        )
    if protocol.domain.support_construction_sha256 != support_construction_sha256():
        raise QualificationContractError(
            "protocol support construction differs from the runner"
        )

    instrument = protocol.instrument
    expected_instrument = (
        F2_LOCAL_COVARIANT_SECTION_REFERENT_ID,
        CLOSED_REPRESENTATION_ESTIMATOR_ID,
        CLOSED_REPRESENTATION_TRIVIALIZATION_ID,
        CLOSED_CORE_LOCALIZER_ID,
    )
    observed_instrument = (
        instrument.referent_id,
        instrument.estimator_id,
        instrument.trivialization_id,
        instrument.core_localizer_id,
    )
    if observed_instrument != expected_instrument:
        raise QualificationContractError(
            "protocol instrument does not equal the closed executed instrument"
        )

    generator = CartesianFourierDomainGenerator()
    if (
        generator.family_identity.family_id != CLOSED_CARTESIAN_GENERATOR_FAMILY_ID
        or protocol.cartesian.generator_family_id
        != CLOSED_CARTESIAN_GENERATOR_FAMILY_ID
        or protocol.implementation_registry.generator_family_id
        != CLOSED_CARTESIAN_GENERATOR_FAMILY_ID
        or CARTESIAN_FOURIER_FIELD_ESTIMATOR_ID != CLOSED_CARTESIAN_ESTIMATOR_ID
        or REPRESENTATION_FIELD_ESTIMATOR_ID != CLOSED_REPRESENTATION_ESTIMATOR_ID
        or CORE_ESTIMATOR_ID != CLOSED_CORE_LOCALIZER_ID
        or protocol.implementation_registry.surrogate_estimator_id
        != CLOSED_CARTESIAN_ESTIMATOR_ID
        or protocol.implementation_registry.surrogate_trivialization_id
        != CLOSED_CARTESIAN_TRIVIALIZATION_ID
        or protocol.implementation_registry.instrument != instrument
    ):
        raise QualificationContractError(
            "closed implementation registry differs from the executable "
            "generator, surrogate, or instrument"
        )
    observed_cases: dict[
        tuple[CoreDisposition, LoopDisposition],
        ControlDeclaration,
    ] = {}
    for control in protocol.selection.controls:
        key = (control.core_disposition, control.loop_disposition)
        if key not in _CONTROL_CASE_REGISTRY or key in observed_cases:
            raise QualificationContractError(
                "controls do not equal the closed joint case registry"
            )
        if control.generator_case_id != _CONTROL_CASE_REGISTRY[key]:
            raise QualificationContractError(
                f"control {control.control_id!r} does not bind its exact generator case"
            )
        observed_cases[key] = control
    if set(observed_cases) != set(_CONTROL_CASE_REGISTRY):
        raise QualificationContractError(
            "controls do not cover the exact closed joint case registry"
        )
    registered_cases = {
        binding.generator_case_id: (
            binding.core_disposition,
            binding.loop_disposition,
        )
        for binding in protocol.implementation_registry.generator_cases
    }
    runtime_cases = {
        case_id: dispositions
        for dispositions, case_id in _CONTROL_CASE_REGISTRY.items()
    }
    if registered_cases != runtime_cases:
        raise QualificationContractError(
            "closed implementation case registry differs from the runtime case registry"
        )
    return QualificationSourceBindingSummary.from_receipt(source_binding_receipt)


def _assignment_map(
    assignments: tuple[StressAssignment, ...],
) -> dict[str, str]:
    return {item.axis_id: item.level for item in assignments}


def _numeric_level(
    values: object,
    *,
    level: str,
    label: str,
) -> float:
    matches = tuple(item.value for item in values if item.level == level)  # type: ignore[attr-defined]
    if len(matches) != 1:
        raise QualificationContractError(
            f"{label} must resolve exactly one numeric stress value"
        )
    return float(matches[0])


def _boundary_template(
    protocol: QualificationProtocol,
    assignments: tuple[StressAssignment, ...],
) -> BoundaryTemplate:
    values = _assignment_map(assignments)
    level = values.get(protocol.cartesian.boundary_axis_id)
    matches = tuple(
        item for item in protocol.cartesian.primary_boundaries if item.level == level
    )
    if len(matches) != 1:
        raise QualificationContractError(
            "primary boundary stress must resolve exactly one template"
        )
    return matches[0]


def _cartesian_spec(
    protocol: QualificationProtocol,
    expected: ExpectedCoreCell,
) -> CartesianFourierDomainSpec:
    assignments = _assignment_map(expected.stress_assignments)
    required_axes = {
        protocol.cartesian.boundary_axis_id,
        protocol.cartesian.state_geometry_warp_axis_id,
        protocol.cartesian.structured_observation_perturbation_axis_id,
    }
    if set(assignments) != required_axes:
        raise QualificationContractError(
            "primary unit does not carry the exact Cartesian stress axes"
        )
    return CartesianFourierDomainSpec(
        seed=expected.selection_seed,
        grid_side=protocol.cartesian.grid_side,
        ambient_dimension=protocol.cartesian.ambient_dimension,
        samples_per_split=protocol.cartesian.samples_per_split,
        baseline=protocol.cartesian.baseline,
        second_harmonic_scale=protocol.cartesian.second_harmonic_scale,
        noise_scale=_numeric_level(
            protocol.cartesian.structured_observation_perturbation_levels,
            level=assignments[
                protocol.cartesian.structured_observation_perturbation_axis_id
            ],
            label="structured observation perturbation stress",
        ),
        density_warp_strength=_numeric_level(
            protocol.cartesian.state_geometry_warp_levels,
            level=assignments[protocol.cartesian.state_geometry_warp_axis_id],
            label="state geometry warp stress",
        ),
    )


def _support_faces(
    side: int,
    template: BoundaryTemplate,
) -> Int64Array:
    return rectangular_grid_support_faces(
        grid_side=side,
        x_min=template.x_min,
        y_min=template.y_min,
        x_max=template.x_max,
        y_max=template.y_max,
    )


def _loop_rows(side: int, template: BoundaryTemplate) -> Int64Array:
    rows: list[int] = []
    rows.extend(
        template.y_min * side + x for x in range(template.x_min, template.x_max)
    )
    rows.extend(
        y * side + template.x_max for y in range(template.y_min, template.y_max)
    )
    rows.extend(
        template.y_max * side + x for x in range(template.x_max, template.x_min, -1)
    )
    rows.extend(
        y * side + template.x_min for y in range(template.y_max, template.y_min, -1)
    )
    return np.asarray(rows, dtype="<i8")


def _build_execution(
    protocol: QualificationProtocol,
    *,
    graph_input: GraphInput,
    oriented_faces: Int64Array,
    template: BoundaryTemplate,
) -> CrossedGraphExecution:
    return build_crossed_graph_execution(
        graph_input=graph_input,
        graph_axes=protocol.graphs,
        oriented_faces=oriented_faces,
        support_face_indices=_support_faces(
            protocol.cartesian.grid_side,
            template,
        ),
        domain_id=protocol.domain.domain_id,
        cycle_class_spec_id=protocol.domain.boundary_class_id,
        matched_set_id=protocol.domain.support_id,
        refinement_rule=BoundaryRefinementRule(
            rule_id=protocol.domain.refinement_rule_id,
            max_domain_edges_per_graph_edge=(
                protocol.domain.max_domain_edges_per_graph_edge
            ),
        ),
    )


def _blind_primary_content_sha256(
    *,
    estimator_input_fingerprint_sha256: str,
) -> str:
    """Return an estimator-visible handle derived only from visible content."""

    return fingerprint_mapping(
        {
            "schema_version": ("spirallens.runner-blind-primary-content-handle.v0.1"),
            "estimator_input_fingerprint_sha256": (estimator_input_fingerprint_sha256),
        }
    )


def _policies(
    protocol: QualificationProtocol,
) -> tuple[CorePrerequisitePolicy, LoopPhasePolicy]:
    thresholds = protocol.thresholds
    return (
        CorePrerequisitePolicy(
            policy_id="qualification-core-prerequisites-v0.5",
            core_amplitude_ceiling=thresholds.core_amplitude_ceiling,
            identifiability_floor=thresholds.identifiability_floor,
            edge_coherence_floor=thresholds.coherence_floor,
            minimum_support_count=thresholds.minimum_support_count,
            max_localized_core_fraction=(thresholds.max_localized_core_fraction),
            minimum_core_contrast_ratio=(thresholds.minimum_core_contrast_ratio),
        ),
        LoopPhasePolicy(
            policy_id="qualification-loop-phase-v0.3",
            amplitude_floor=thresholds.core_amplitude_ceiling,
            identifiability_floor=thresholds.identifiability_floor,
            coherence_floor=thresholds.coherence_floor,
            branch_margin_radians=thresholds.branch_margin_rad,
            integer_residual_tolerance_cycles=(thresholds.loop_oracle_tolerance_cycles),
            nonzero_floor_cycles=thresholds.loop_nonzero_floor_cycles,
        ),
    )


def _d2_confounder_graph_input(protocol: QualificationProtocol) -> GraphInput:
    """Build a deterministic seed-free substrate used only by D2 confounders."""

    side = protocol.cartesian.grid_side
    row_count = side * side
    rows = np.arange(row_count, dtype="<i8")
    y, x = np.divmod(rows, side)
    states = np.zeros(
        (row_count, protocol.cartesian.ambient_dimension),
        dtype="<f8",
    )
    coordinate_scale = float(side * 4)
    states[:, 0] = x / coordinate_scale
    states[:, 1] = y / coordinate_scale
    for column in range(2, states.shape[1]):
        states[:, column] = ((column + 1) * x + (column + 3) * y + x * y) / float(
            side * (column + 4) * coordinate_scale
        )
    return GraphInput(
        primary_unit_id="d2-seed-free-core-confounder-substrate",
        vertex_ids=rows,
        states=states,
    )


def _support_counts_from_edges(
    row_count: int,
    edges: NDArray[np.int64],
) -> Int64Array:
    counts = np.zeros(row_count, dtype="<i8")
    for left, right in edges:
        counts[int(left)] += 1
        counts[int(right)] += 1
    return counts


def _run_d2_confounder_matrix(
    protocol: QualificationProtocol,
    policy: CorePrerequisitePolicy,
) -> D2CoreConfounderMatrixReceipt:
    """Execute the frozen D2-only confounders without a selection seed."""

    graph_input = _d2_confounder_graph_input(protocol)
    row_count = graph_input.vertex_ids.shape[0]
    center_row = row_count // 2
    offcenter_row = 0
    graph_ids = tuple(item.graph_id for item in protocol.graphs.field_estimation)
    cells: list[D2CoreConfounderCellReceipt] = []
    for declaration in protocol.d2_core_confounders:
        for graph_declaration in protocol.graphs.field_estimation:
            base_graph = construct_declared_graph(graph_input, graph_declaration)
            base_edges = np.asarray(base_graph.canonical_edges, dtype="<i8")
            if (
                declaration.construction_id
                == D2_IDENTIFIABILITY_LOSS_DECOY_CONSTRUCTION_ID
            ):
                candidate_row = offcenter_row
                edges = base_edges
                noncandidate_amplitude = max(
                    1.0,
                    policy.core_amplitude_ceiling
                    * policy.minimum_core_contrast_ratio
                    * 2.0,
                )
                candidate_amplitude = noncandidate_amplitude
            elif (
                declaration.construction_id
                == D2_MISSING_CANDIDATE_SUPPORT_CONSTRUCTION_ID
            ):
                candidate_row = center_row
                edges = base_edges[np.all(base_edges != candidate_row, axis=1)]
                candidate_amplitude = 0.0
                noncandidate_amplitude = max(
                    1.0,
                    policy.core_amplitude_ceiling
                    * policy.minimum_core_contrast_ratio
                    * 2.0,
                )
            else:
                raise QualificationContractError(
                    "D2 confounder construction is outside the closed runtime registry"
                )
            support_counts = _support_counts_from_edges(row_count, edges)
            amplitudes = np.full(
                row_count,
                noncandidate_amplitude,
                dtype="<f8",
            )
            amplitudes[candidate_row] = candidate_amplitude
            section_values = np.column_stack(
                (amplitudes, np.zeros(row_count, dtype="<f8"))
            ).astype("<f8")
            identifiability = np.full(
                row_count,
                max(1.0, policy.identifiability_floor * 2.0),
                dtype="<f8",
            )
            if declaration.construction_id in {
                D2_IDENTIFIABILITY_LOSS_DECOY_CONSTRUCTION_ID,
                D2_MISSING_CANDIDATE_SUPPORT_CONSTRUCTION_ID,
            }:
                identifiability[candidate_row] = 0.0
            coherence = np.ones(row_count, dtype="<f8")
            construction_receipt = {
                "construction_id": declaration.construction_id,
                "field_graph_id": graph_declaration.graph_id,
                "base_field_graph_sha256": base_graph.fingerprint_sha256,
                "probe_row": candidate_row,
                "masked_probe_measurement_support": (
                    declaration.construction_id
                    == D2_MISSING_CANDIDATE_SUPPORT_CONSTRUCTION_ID
                ),
                "graph_edges": array_fingerprint(edges),
                "section_values": array_fingerprint(section_values),
                "identifiability_score": array_fingerprint(identifiability),
                "edge_coherence": array_fingerprint(coherence),
                "support_counts": array_fingerprint(support_counts),
                "selection_seed_present": False,
                "oracle_input_present": False,
            }
            estimator_input_sha256 = canonical_json_sha256(
                {
                    "substrate_primary_unit_id": graph_input.primary_unit_id,
                    "row_ids": array_fingerprint(graph_input.vertex_ids),
                    "states": array_fingerprint(graph_input.states),
                    "selection_seed_present": False,
                }
            )
            field_graph_sha256 = canonical_json_sha256(
                {
                    "base_field_graph_sha256": base_graph.fingerprint_sha256,
                    "consumed_edges": array_fingerprint(edges),
                    "measurement_mask_confounder": (
                        declaration.construction_id
                        == D2_MISSING_CANDIDATE_SUPPORT_CONSTRUCTION_ID
                    ),
                }
            )
            field_estimate_sha256 = canonical_json_sha256(construction_receipt)
            primary_sha256 = canonical_json_sha256(
                {
                    "scope": "d2-seed-free-core-confounder",
                    "construction_id": declaration.construction_id,
                    "field_graph_id": graph_declaration.graph_id,
                    "estimator_input_sha256": estimator_input_sha256,
                }
            )
            blind = build_blind_core_input(
                primary_unit_sha256=primary_sha256,
                estimator_input_fingerprint_sha256=(estimator_input_sha256),
                field_graph_fingerprint_sha256=field_graph_sha256,
                field_estimate_fingerprint_sha256=field_estimate_sha256,
                row_ids=graph_input.vertex_ids,
                section_values=section_values,
                identifiability_score=identifiability,
                edge_coherence=coherence,
                support_counts=support_counts,
                orientation_resolved=True,
                orientation_preserving=True,
                graph_edges=edges,
            )
            prediction = estimate_and_seal_core(blind, policy)
            cells.append(
                D2CoreConfounderCellReceipt.from_runtime(
                    cell_id=(
                        f"d2cf.{declaration.confounder_id}.{graph_declaration.graph_id}"
                    ),
                    declaration=declaration,
                    field_graph_id=graph_declaration.graph_id,
                    policy=policy,
                    probe_row=candidate_row,
                    probe_row_role=(
                        "offcenter"
                        if declaration.construction_id
                        == D2_IDENTIFIABILITY_LOSS_DECOY_CONSTRUCTION_ID
                        else "center"
                    ),
                    blind_input=blind,
                    sealed_prediction=prediction,
                )
            )
    failed = tuple(
        cell.cell_id for cell in cells if cell.state is not QualificationState.PASS
    )
    result = D2CoreConfounderMatrixReceipt(
        policy_fingerprint_sha256=policy.fingerprint_sha256,
        confounder_declarations=tuple(
            item.to_dict() for item in protocol.d2_core_confounders
        ),
        field_graph_ids=graph_ids,
        cells=tuple(cells),
        state=(QualificationState.PASS if not failed else QualificationState.FAIL),
        failed_cell_ids=failed,
    )
    result.validate_protocol(protocol)
    return result


def _rows_fingerprint(rows: object) -> str:
    return canonical_json_sha256(array_fingerprint(np.asarray(rows, dtype="<i8")))


def _independent_core_prerequisite_reasons(
    *,
    case: CartesianFourierCase,
    estimate: CartesianFourierFieldEstimate,
    policy: CorePrerequisitePolicy,
) -> tuple[str, ...]:
    truth = case.oracle_truth
    if (
        truth.disposition.value != "prerequisite_failure"
        or np.any(truth.f2_support)
        or np.any(truth.f2_amplitude)
    ):
        raise QualificationContractError(
            "prerequisite oracle source is not the zero-support control"
        )
    # The zero-support control has no non-core support on which
    # identifiability, coherence, or degree eligibility could be evaluated.
    # Its exact D2 failure is therefore the diffuse low-amplitude field,
    # augmented only by an actually empty consumed graph.
    reasons = {REASON_CORE_AMPLITUDE_NOT_LOCALIZED}
    edges = estimate.field_graph.canonical_edges
    counts = np.zeros(truth.row_ids.shape[0], dtype="<i8")
    for left, right in edges:
        counts[int(left)] += 1
        counts[int(right)] += 1
    if edges.shape[0] == 0:
        reasons.add(REASON_EMPTY_GRAPH)
    return tuple(sorted(reasons))


def _independent_loop_prerequisite_reasons(
    *,
    case: CartesianFourierCase,
    blind_input: BlindLoopInput,
) -> tuple[str, ...]:
    truth = case.oracle_truth
    if (
        truth.disposition.value != "prerequisite_failure"
        or np.any(truth.f2_support)
        or np.any(truth.f2_amplitude)
    ):
        raise QualificationContractError(
            "prerequisite oracle source is not the zero-support control"
        )
    reasons = {
        REASON_BOUNDARY_AMPLITUDE_FLOOR,
        REASON_BOUNDARY_IDENTIFIABILITY_FLOOR,
        REASON_BOUNDARY_COHERENCE_FLOOR,
    }
    rows = tuple(int(item) for item in blind_input.ordered_loop_rows)
    if len(set(rows)) < 3:
        reasons.add(REASON_LOOP_SUPPORT)
    if len(set(rows)) != len(rows):
        reasons.add(REASON_LOOP_ROWS_REPEATED)
    return tuple(sorted(reasons))


def _expected_sampled_cycles(
    case: CartesianFourierCase,
    template: BoundaryTemplate,
) -> int | None:
    truth = case.oracle_truth
    side = round(math.sqrt(truth.row_ids.shape[0]))
    if side * side != truth.row_ids.shape[0]:
        raise QualificationContractError("Cartesian oracle row domain is not square")
    template_rows = _loop_rows(side, template)
    candidates = (
        (
            truth.outer_loop_vertex_rows,
            truth.expected_outer_sampled_winding,
        ),
        (
            truth.central_loop_vertex_rows,
            truth.expected_central_sampled_winding,
        ),
        (
            truth.offcore_loop_vertex_rows,
            truth.expected_offcore_sampled_winding,
        ),
    )
    matches = tuple(
        expected
        for oracle_rows, expected in candidates
        if np.array_equal(template_rows, oracle_rows)
    )
    if len(matches) > 1:
        raise QualificationContractError(
            f"boundary template {template.level!r} joins multiple oracle loops"
        )
    if matches:
        return matches[0]
    if truth.disposition is CartesianExpectedDisposition.PREREQUISITE_FAILURE:
        return None
    if not np.all(truth.f2_support[template_rows]):
        raise QualificationContractError(
            f"boundary template {template.level!r} crosses undefined oracle direction"
        )
    # The boundary is frozen in the protocol before execution.  Deriving its
    # evaluator target here occurs only after all primary predictions have
    # been sealed; it does not expose oracle values to either estimator.
    return evaluate_oracle_sampled_response(
        truth.f2_coordinates,
        template_rows,
    )


def _core_template(
    expected: tuple[ExpectedCoreCell, ...],
    *,
    d2_scientific_input_sha256: str,
    domain_sha256: str,
    support_sha256: str,
) -> CorePrimaryUnitSummary:
    first = expected[0]
    status = (
        AttemptStatus.INSUFFICIENT
        if first.expected_core_disposition is CoreDisposition.PREREQUISITE_FAILURE
        else AttemptStatus.EVALUABLE
    )
    prediction = {
        CoreDisposition.LOCALIZED_CORE: CorePredictionClass.LOCALIZED_CORE,
        CoreDisposition.NO_CORE: CorePredictionClass.NO_CORE,
        CoreDisposition.PREREQUISITE_FAILURE: CorePredictionClass.ABSTAIN,
    }[first.expected_core_disposition]
    return CorePrimaryUnitSummary(
        primary_unit_id=first.primary_unit_id,
        selection_seed=first.selection_seed,
        control_id=first.control_id,
        expected_disposition=first.expected_core_disposition,
        stress_assignments=first.stress_assignments,
        d2_scientific_input_fingerprint_sha256=(d2_scientific_input_sha256),
        domain_instance_fingerprint_sha256=domain_sha256,
        support_instance_fingerprint_sha256=support_sha256,
        attempt_status=status,
        prediction_class=prediction,
        state=QualificationState.PASS,
        max_candidate_symmetric_difference_rows=0,
        reason_codes=(),
        core_cell_ids=tuple(item.core_cell_id for item in expected),
    )


def _loop_template(
    expected: tuple[ExpectedCell, ...],
    *,
    domain_sha256: str,
    support_sha256: str,
) -> PrimaryUnitSummary:
    first = expected[0]
    disposition = next(
        item.expected_loop_disposition
        for item in expected
        if item.loop_role is LoopRole.PRIMARY_BOUNDARY
    )
    status = (
        AttemptStatus.INSUFFICIENT
        if disposition is LoopDisposition.PREREQUISITE_FAILURE
        else AttemptStatus.EVALUABLE
    )
    prediction = {
        LoopDisposition.NONZERO: LoopPredictionClass.NONZERO,
        LoopDisposition.NULL: LoopPredictionClass.NULL,
        LoopDisposition.PREREQUISITE_FAILURE: LoopPredictionClass.ABSTAIN,
    }[disposition]
    return PrimaryUnitSummary(
        primary_unit_id=first.primary_unit_id,
        selection_seed=first.selection_seed,
        control_id=first.control_id,
        expected_disposition=disposition,
        stress_assignments=first.stress_assignments,
        domain_instance_fingerprint_sha256=domain_sha256,
        support_instance_fingerprint_sha256=support_sha256,
        attempt_status=status,
        prediction_class=prediction,
        state=QualificationState.PASS,
        continuous_total_span_cycles=0.0,
        reason_codes=(),
        crossed_cell_ids=tuple(item.cell_id for item in expected),
    )


def _run_primary(
    protocol: QualificationProtocol,
    *,
    core_expected: tuple[ExpectedCoreCell, ...],
    loop_expected: tuple[ExpectedCell, ...],
    control: ControlDeclaration,
    core_policy: CorePrerequisitePolicy,
    loop_policy: LoopPhasePolicy,
) -> _PrimaryRun:
    first = core_expected[0]
    if (
        first.primary_unit_id != loop_expected[0].primary_unit_id
        or first.control_id != control.control_id
    ):
        raise QualificationContractError(
            "core, loop, and control primary identities do not join"
        )
    phantom = CartesianFourierDomainGenerator().generate(
        _cartesian_spec(protocol, first)
    )
    cases = {item.case_id: item for item in phantom.cases}
    if tuple(cases) != tuple(_CONTROL_CASE_REGISTRY.values()):
        raise QualificationContractError(
            "runtime Cartesian case registry is not canonical"
        )
    case = cases[control.generator_case_id]
    inputs = case.estimator_inputs
    graph_input = GraphInput(
        primary_unit_id=first.primary_unit_id,
        vertex_ids=inputs.row_ids,
        states=inputs.states,
    )
    primary_template = _boundary_template(protocol, first.stress_assignments)
    primary_execution = _build_execution(
        protocol,
        graph_input=graph_input,
        oriented_faces=inputs.oriented_faces,
        template=primary_template,
    )
    offcore_execution = _build_execution(
        protocol,
        graph_input=graph_input,
        oriented_faces=inputs.oriented_faces,
        template=protocol.cartesian.offcore_boundary,
    )
    estimates = tuple(
        estimate_cartesian_fourier_field(inputs, graph)
        for graph in primary_execution.field_graphs
    )
    if len(estimates) != 3:
        raise AssertionError("protocol requires exactly three field estimates")
    primary_sha256 = _blind_primary_content_sha256(
        estimator_input_fingerprint_sha256=inputs.fingerprint_sha256,
    )

    core_blind: dict[str, BlindCoreInput] = {}
    core_predictions: dict[str, SealedCorePrediction] = {}
    for expected, estimate in zip(core_expected, estimates, strict=True):
        if expected.field_graph_id != estimate.field_graph.specification.spec_id:
            raise QualificationContractError(
                "core manifest is not aligned with the field graph axis"
            )
        blind = build_crossed_blind_core_input(
            primary_execution,
            estimate,
            primary_unit_sha256=primary_sha256,
        )
        prediction = estimate_and_seal_core(blind, core_policy)
        core_blind[expected.core_cell_id] = blind
        core_predictions[expected.core_cell_id] = prediction

    execution_by_role = {
        LoopRole.PRIMARY_BOUNDARY: primary_execution,
        LoopRole.OFFCORE_CONTROL: offcore_execution,
    }
    estimate_by_graph_id = {
        declaration.graph_id: estimate
        for declaration, estimate in zip(
            protocol.graphs.field_estimation,
            estimates,
            strict=True,
        )
    }
    loop_blind: dict[str, BlindLoopInput] = {}
    loop_predictions: dict[str, SealedLoopPrediction] = {}
    for expected in loop_expected:
        execution = execution_by_role[expected.loop_role]
        estimate = estimate_by_graph_id[expected.field_graph_id]
        blind = build_crossed_blind_loop_input(
            execution,
            estimate,
            cycle_graph_id=expected.cycle_graph_id,
            primary_unit_sha256=primary_sha256,
        )
        prediction = estimate_and_seal_loop(blind, loop_policy)
        loop_blind[expected.cell_id] = blind
        loop_predictions[expected.cell_id] = prediction

    # Oracle access begins only after every prediction for this primary unit is
    # immutable.  The final typed ledger records this exact API-local order.
    oracle = case.oracle_truth
    anchor_rows = oracle.row_ids[oracle.core_anchor_mask]
    core_cells: list[CoreCellSummary] = []
    core_evidence: list[CoreCellEvaluationReceipt] = []
    for expected, estimate in zip(core_expected, estimates, strict=True):
        blind = core_blind[expected.core_cell_id]
        prediction = core_predictions[expected.core_cell_id]
        reasons = (
            _independent_core_prerequisite_reasons(
                case=case,
                estimate=estimate,
                policy=core_policy,
            )
            if expected.expected_core_disposition
            is CoreDisposition.PREREQUISITE_FAILURE
            else ()
        )
        truth = build_core_oracle_truth(
            blind_input=blind,
            policy=core_policy,
            expected_disposition=expected.expected_core_disposition,
            anchor_rows=anchor_rows,
            expected_prerequisite_reasons=reasons,
            obligation_mode=ObligationMode.INDIVIDUALLY_REQUIRED,
            evaluation_unit=EvaluationUnit.CORE,
        )
        evaluation = score_core_prediction(
            prediction,
            truth,
        )
        candidate_rows = prediction.candidate_rows
        difference = tuple(
            sorted(
                {int(item) for item in candidate_rows}
                ^ {int(item) for item in anchor_rows}
            )
        )
        summary = CoreCellSummary(
            core_cell_id=expected.core_cell_id,
            primary_unit_id=expected.primary_unit_id,
            field_graph_id=expected.field_graph_id,
            expected_disposition=expected.expected_core_disposition,
            field_graph_fingerprint_sha256=(estimate.field_graph.fingerprint_sha256),
            field_estimate_fingerprint_sha256=estimate.fingerprint_sha256,
            blind_input_fingerprint_sha256=blind.fingerprint_sha256,
            prediction_fingerprint_sha256=prediction.fingerprint_sha256,
            oracle_fingerprint_sha256=truth.fingerprint_sha256,
            candidate_fingerprint_sha256=_rows_fingerprint(candidate_rows),
            oracle_anchor_fingerprint_sha256=_rows_fingerprint(anchor_rows),
            candidate_anchor_symmetric_difference_rows=difference,
            attempt_status=evaluation.observed_attempt_status,
            prediction_class=prediction.prediction_class,
            state=evaluation.gate_verdict,
            reason_codes=evaluation.reason_codes,
        )
        core_cells.append(summary)
        core_evidence.append(
            CoreCellEvaluationReceipt.from_runtime(
                core_cell_id=expected.core_cell_id,
                blind_input=blind,
                sealed_prediction=prediction,
                oracle_truth=truth,
                case_evaluation=evaluation,
                summary=summary,
            )
        )

    loop_cells: list[CrossedCellSummary] = []
    loop_evidence: list[LoopCellEvaluationReceipt] = []
    for expected in loop_expected:
        blind = loop_blind[expected.cell_id]
        prediction = loop_predictions[expected.cell_id]
        template = (
            primary_template
            if expected.loop_role is LoopRole.PRIMARY_BOUNDARY
            else protocol.cartesian.offcore_boundary
        )
        expected_cycles = _expected_sampled_cycles(case, template)
        reasons = (
            _independent_loop_prerequisite_reasons(
                case=case,
                blind_input=blind,
            )
            if expected.expected_loop_disposition
            is LoopDisposition.PREREQUISITE_FAILURE
            else ()
        )
        truth = build_loop_oracle_truth(
            blind_input=blind,
            policy=loop_policy,
            expected_disposition=expected.expected_loop_disposition,
            expected_sampled_cycles=expected_cycles,
            expected_prerequisite_reasons=reasons,
            obligation_mode=ObligationMode.INDIVIDUALLY_REQUIRED,
        )
        evaluation = score_loop_prediction(prediction, truth)
        summary = CrossedCellSummary(
            cell_id=expected.cell_id,
            primary_unit_id=expected.primary_unit_id,
            field_graph_id=expected.field_graph_id,
            cycle_graph_id=expected.cycle_graph_id,
            loop_role=expected.loop_role,
            expected_disposition=expected.expected_loop_disposition,
            field_graph_fingerprint_sha256=(blind.field_graph_fingerprint_sha256),
            cycle_graph_fingerprint_sha256=(blind.cycle_graph_fingerprint_sha256),
            field_estimate_fingerprint_sha256=(blind.field_estimate_fingerprint_sha256),
            cycle_binding_fingerprint_sha256=(blind.cycle_binding_fingerprint_sha256),
            representative_content_sha256=blind.representative_content_sha256,
            blind_input_fingerprint_sha256=blind.fingerprint_sha256,
            prediction_fingerprint_sha256=prediction.fingerprint_sha256,
            oracle_fingerprint_sha256=truth.fingerprint_sha256,
            attempt_status=evaluation.observed_attempt_status,
            prediction_class=prediction.prediction_class,
            state=evaluation.gate_verdict,
            continuous_signed_total_cycles=prediction.signed_total_cycles,
            oracle_absolute_error_cycles=evaluation.signed_error_cycles,
            reason_codes=evaluation.reason_codes,
        )
        loop_cells.append(summary)
        loop_evidence.append(
            LoopCellEvaluationReceipt.from_runtime(
                cell_id=expected.cell_id,
                blind_input=blind,
                sealed_prediction=prediction,
                oracle_truth=truth,
                case_evaluation=evaluation,
                summary=summary,
            )
        )

    nonvacuity_receipt = assess_crossed_nonvacuity(
        primary_execution,
        estimates,
        minimum_representative_content_variants=(
            protocol.thresholds.minimum_representative_content_variants
        ),
        require_substantive_output_variation=(control.field_sensitivity_sentinel),
        minimum_substantive_output_distance=(
            protocol.thresholds.minimum_field_output_effect_size
        ),
    )
    nonvacuity = CrossedNonvacuitySummary.from_receipt(
        primary_unit_id=first.primary_unit_id,
        control_id=control.control_id,
        receipt=nonvacuity_receipt,
    )
    return _PrimaryRun(
        core_cells=tuple(sorted(core_cells, key=lambda item: item.core_cell_id)),
        core_evidence=tuple(sorted(core_evidence, key=lambda item: item.core_cell_id)),
        core_template=_core_template(
            core_expected,
            d2_scientific_input_sha256=primary_sha256,
            domain_sha256=primary_execution.domain.fingerprint_sha256,
            support_sha256=primary_execution.cycle_class.fingerprint_sha256,
        ),
        loop_cells=tuple(sorted(loop_cells, key=lambda item: item.cell_id)),
        loop_evidence=tuple(sorted(loop_evidence, key=lambda item: item.cell_id)),
        loop_template=_loop_template(
            loop_expected,
            domain_sha256=primary_execution.domain.fingerprint_sha256,
            support_sha256=primary_execution.cycle_class.fingerprint_sha256,
        ),
        nonvacuity=nonvacuity,
        nonvacuity_evidence=NonvacuityEvaluationReceipt.from_runtime(
            primary_unit_id=first.primary_unit_id,
            receipt=nonvacuity_receipt,
            summary=nonvacuity,
        ),
    )


def _run_representation_family(
    protocol: QualificationProtocol,
) -> _RepresentationEvidence:
    mutual = protocol.graphs.field_estimation[0]
    neighbor_count = int(dict(mutual.parameters)["neighbor_count"])
    spec = RepresentationPhantomSpec(
        seed=REPRESENTATION_METAMORPHIC_DEVELOPMENT_SEED,
        grid_side=protocol.cartesian.grid_side,
        ambient_dimension=protocol.cartesian.ambient_dimension,
        probe_count=protocol.cartesian.samples_per_split,
        neighbor_count=neighbor_count,
    )
    phantom = RepresentationPhantom.generate(spec)
    phantom.validate()
    executions: dict[
        str,
        tuple[
            RepresentationEstimatorInputs,
            tuple[RepresentationFieldEstimate, ...],
        ],
    ] = {}
    positive_inputs: RepresentationEstimatorInputs | None = None
    positive_estimates: tuple[RepresentationFieldEstimate, ...] | None = None
    for case in phantom.cases:
        inputs = build_representation_estimator_inputs(
            spec=spec,
            vertex_ids=case.vertex_identities,
            grid_coordinates=phantom.grid_coordinates,
            states=case.states,
            accounted_response=case.accounted_response,
            valid_mask=case.valid_mask,
        )
        graph_input = GraphInput(
            primary_unit_id=inputs.primary_unit_id,
            vertex_ids=inputs.vertex_ids,
            states=inputs.states,
        )
        graphs = tuple(
            construct_declared_graph(graph_input, declaration)
            for declaration in protocol.graphs.field_estimation
        )
        estimates = tuple(
            estimate_representation_field(inputs, graph) for graph in graphs
        )
        executions[case.case_id] = (inputs, estimates)
        if case is phantom.angular_section_positive:
            positive_inputs = inputs
            positive_estimates = estimates
    if positive_inputs is None or positive_estimates is None:
        raise AssertionError("representation positive construction is missing")
    return _RepresentationEvidence(
        runtime_receipt=D1FamilyExecutionReceipt.from_representation(
            phantom=phantom,
            executions=executions,
            numeric_tolerance=protocol.thresholds.d1_numeric_tolerance,
            phase_coherence_floor=(
                protocol.thresholds.d1_representation_phase_coherence_floor
            ),
        ),
        positive_inputs=positive_inputs,
        positive_estimates=positive_estimates,
    )


def _run_cartesian_d1_family(
    protocol: QualificationProtocol,
) -> D1FamilyExecutionReceipt:
    """Execute the full Cartesian family on a fixed development seed only."""

    phantom = CartesianFourierDomainGenerator().generate(
        CartesianFourierDomainSpec(
            seed=REPRESENTATION_METAMORPHIC_DEVELOPMENT_SEED,
            grid_side=protocol.cartesian.grid_side,
            ambient_dimension=protocol.cartesian.ambient_dimension,
            samples_per_split=protocol.cartesian.samples_per_split,
            baseline=protocol.cartesian.baseline,
            second_harmonic_scale=protocol.cartesian.second_harmonic_scale,
            noise_scale=0.0,
            density_warp_strength=0.0,
        )
    )
    estimates_by_case: dict[
        str,
        tuple[CartesianFourierFieldEstimate, ...],
    ] = {}
    for case in phantom.cases:
        inputs = case.estimator_inputs
        graph_input = GraphInput(
            primary_unit_id=f"d1-development-{case.case_id}",
            vertex_ids=inputs.row_ids,
            states=inputs.states,
        )
        graphs = tuple(
            construct_declared_graph(graph_input, declaration)
            for declaration in protocol.graphs.field_estimation
        )
        estimates_by_case[case.case_id] = tuple(
            estimate_cartesian_fourier_field(inputs, graph) for graph in graphs
        )
    return D1FamilyExecutionReceipt.from_cartesian(
        phantom=phantom,
        estimates_by_case=estimates_by_case,
        numeric_tolerance=protocol.thresholds.d1_numeric_tolerance,
        direction_cosine_floor=(
            protocol.thresholds.d1_cartesian_direction_cosine_floor
        ),
    )


def recompute_fixed_development_d1(
    protocol: QualificationProtocol,
) -> tuple[D1FamilyExecutionReceipt, D1FamilyExecutionReceipt]:
    """Re-execute both D1 families without consulting selection seeds.

    This helper is only the deterministic numeric rerun.  Its caller must
    first establish the live source binding for the current engine.
    """

    if not isinstance(protocol, QualificationProtocol):
        raise TypeError("protocol must be a QualificationProtocol")
    cartesian = _run_cartesian_d1_family(protocol)
    representation = _run_representation_family(protocol)
    return cartesian, representation.runtime_receipt


def _signed_permutation(dimension: int) -> FloatArray:
    matrix = np.zeros((dimension, dimension), dtype="<f8")
    for destination in range(dimension):
        source = (destination + 3) % dimension
        matrix[destination, source] = -1.0 if destination % 2 else 1.0
    return matrix


def _rectangular_boundary_rows(
    template: BoundaryTemplate,
    *,
    grid_side: int,
) -> Int64Array:
    rows: list[int] = []
    rows.extend(
        template.y_min * grid_side + x
        for x in range(template.x_min, template.x_max + 1)
    )
    rows.extend(
        y * grid_side + template.x_max
        for y in range(template.y_min + 1, template.y_max + 1)
    )
    rows.extend(
        template.y_max * grid_side + x
        for x in range(template.x_max - 1, template.x_min - 1, -1)
    )
    rows.extend(
        y * grid_side + template.x_min
        for y in range(template.y_max - 1, template.y_min, -1)
    )
    return np.asarray(rows, dtype="<i8")


def _rectangular_grid_oriented_faces(grid_side: int) -> Int64Array:
    faces: list[tuple[int, int, int]] = []
    for y in range(grid_side - 1):
        for x in range(grid_side - 1):
            lower_left = y * grid_side + x
            lower_right = lower_left + 1
            upper_left = lower_left + grid_side
            upper_right = upper_left + 1
            faces.extend(
                (
                    (lower_left, lower_right, upper_right),
                    (lower_left, upper_right, upper_left),
                )
            )
    return np.asarray(faces, dtype="<i8")


def _representation_loop_variant(
    base: BlindLoopInput,
    *,
    variant_id: str,
    ordered_loop_rows: object,
    section_values: object,
    boundary_identifiability_score: object,
    boundary_coherence: object,
) -> BlindLoopInput:
    section = np.asarray(section_values, dtype="<f8")
    return build_blind_loop_input(
        primary_unit_sha256=base.primary_unit_sha256,
        estimator_input_fingerprint_sha256=(base.estimator_input_fingerprint_sha256),
        field_graph_fingerprint_sha256=(base.field_graph_fingerprint_sha256),
        field_estimate_fingerprint_sha256=fingerprint_mapping(
            {
                "schema_version": ("spirallens.representation-loop-field-view.v0.1"),
                "base_field_estimate_fingerprint_sha256": (
                    base.field_estimate_fingerprint_sha256
                ),
                "variant_id": variant_id,
                "section_values": array_fingerprint(section),
            }
        ),
        cycle_graph_fingerprint_sha256=(base.cycle_graph_fingerprint_sha256),
        cycle_binding_fingerprint_sha256=(base.cycle_binding_fingerprint_sha256),
        representative_content_sha256=fingerprint_mapping(
            {
                "schema_version": (
                    "spirallens.representation-loop-representative-view.v0.1"
                ),
                "base_representative_content_sha256": (
                    base.representative_content_sha256
                ),
                "variant_id": variant_id,
                "ordered_loop_rows": array_fingerprint(
                    np.asarray(ordered_loop_rows, dtype="<i8")
                ),
            }
        ),
        ordered_loop_rows=ordered_loop_rows,
        section_values=section,
        boundary_amplitude=np.linalg.norm(section, axis=1),
        boundary_identifiability_score=boundary_identifiability_score,
        boundary_coherence=boundary_coherence,
    )


def _representation_prediction_document(
    prediction: SealedLoopPrediction,
) -> dict[str, object]:
    if (
        prediction.observed_attempt_status is not AttemptStatus.EVALUABLE
        or prediction.reason_codes
        or prediction.signed_total_cycles is None
    ):
        raise QualificationContractError(
            "representation D3 requires an evaluable sealed loop prediction"
        )
    return {
        "prediction_sha256": prediction.fingerprint_sha256,
        "receipt": prediction.to_dict(),
    }


def _representation_loop_law_receipt(
    *,
    receipt_version: str,
    law: str,
    field_graph_id: str,
    cycle_graph_id: str,
    base_blind: BlindLoopInput,
    transformed_blind: BlindLoopInput,
    base_prediction: SealedLoopPrediction,
    transformed_prediction: SealedLoopPrediction,
    transformation_sha256: str,
    orientation_determinant: float,
    tolerance: float,
) -> dict[str, object]:
    base_total = base_prediction.signed_total_cycles
    transformed_total = transformed_prediction.signed_total_cycles
    if base_total is None or transformed_total is None:
        raise QualificationContractError(
            "representation D3 loop law requires two evaluable totals"
        )
    expected_total = orientation_determinant * base_total
    error = abs(transformed_total - expected_total)
    verified = (
        base_prediction.observed_attempt_status is AttemptStatus.EVALUABLE
        and transformed_prediction.observed_attempt_status is AttemptStatus.EVALUABLE
        and not base_prediction.reason_codes
        and not transformed_prediction.reason_codes
        and abs(abs(orientation_determinant) - 1.0) <= tolerance
        and error <= tolerance
    )
    return {
        "receipt_version": receipt_version,
        "field_graph_id": field_graph_id,
        "cycle_graph_id": cycle_graph_id,
        "law": law,
        "transformation_sha256": transformation_sha256,
        "orientation_determinant": orientation_determinant,
        "base_blind_input_sha256": base_blind.fingerprint_sha256,
        "transformed_blind_input_sha256": (transformed_blind.fingerprint_sha256),
        "base_blind_input": base_blind.to_dict(),
        "transformed_blind_input": transformed_blind.to_dict(),
        "base_prediction": _representation_prediction_document(base_prediction),
        "transformed_prediction": _representation_prediction_document(
            transformed_prediction
        ),
        "base_signed_total_cycles": base_total,
        "expected_transformed_signed_total_cycles": expected_total,
        "transformed_signed_total_cycles": transformed_total,
        "signed_total_error_cycles": error,
        "tolerance": tolerance,
        "verified": verified,
        "selection_seed_accessed": False,
        "oracle_read": False,
        "sampled_continuous_observable_only": True,
        "integer_output_present": False,
        "topology_claimed": False,
    }


def _run_representation_metamorphic(
    protocol: QualificationProtocol,
    evidence: _RepresentationEvidence,
) -> _RepresentationMetamorphicEvidence:
    base_inputs = evidence.positive_inputs
    transform = _signed_permutation(base_inputs.spec.ambient_dimension)
    transformed_inputs = build_representation_estimator_inputs(
        spec=base_inputs.spec,
        vertex_ids=base_inputs.vertex_ids,
        grid_coordinates=base_inputs.grid_coordinates,
        states=base_inputs.states @ transform.T,
        accounted_response=base_inputs.accounted_response @ transform.T,
        valid_mask=base_inputs.valid_mask,
    )
    oriented_faces = _rectangular_grid_oriented_faces(protocol.cartesian.grid_side)
    boundary = protocol.cartesian.primary_boundaries[0]

    def execute_pipeline(
        inputs: RepresentationEstimatorInputs,
    ) -> tuple[
        CrossedGraphExecution,
        tuple[RepresentationFieldEstimate, ...],
    ]:
        graph_input = GraphInput(
            primary_unit_id=inputs.primary_unit_id,
            vertex_ids=inputs.vertex_ids,
            states=inputs.states,
        )
        execution = _build_execution(
            protocol,
            graph_input=graph_input,
            oriented_faces=oriented_faces,
            template=boundary,
        )
        estimates = tuple(
            estimate_representation_field(inputs, graph)
            for graph in execution.field_graphs
        )
        return execution, estimates

    base_execution, base_estimates = execute_pipeline(base_inputs)
    transformed_execution, transformed_estimates = execute_pipeline(transformed_inputs)
    if tuple(item.fingerprint_sha256 for item in base_estimates) != tuple(
        item.fingerprint_sha256 for item in evidence.positive_estimates
    ):
        raise QualificationContractError(
            "representation D3 base rerun differs from its D1 source execution"
        )
    _core_policy, loop_policy = _policies(protocol)
    base_primary_sha256 = _blind_primary_content_sha256(
        estimator_input_fingerprint_sha256=(base_inputs.fingerprint_sha256)
    )
    transformed_primary_sha256 = _blind_primary_content_sha256(
        estimator_input_fingerprint_sha256=(transformed_inputs.fingerprint_sha256)
    )

    pipeline_checks: list[dict[str, object]] = []
    loop_variant_checks: list[dict[str, object]] = []
    verified = True
    for base, transformed in zip(
        base_estimates,
        transformed_estimates,
        strict=True,
    ):
        cross = transformed.section_values.T @ base.section_values
        left, _singular, right = np.linalg.svd(cross)
        alignment = left @ right
        alignment_determinant = float(np.linalg.det(alignment))
        errors = {
            "ambient_equivariance": float(
                np.max(
                    np.abs(
                        transformed.ambient_section - base.ambient_section @ transform.T
                    )
                )
            ),
            "section_gauge_alignment": float(
                np.max(
                    np.abs(transformed.section_values @ alignment - base.section_values)
                )
            ),
            "amplitude": float(np.max(np.abs(transformed.amplitude - base.amplitude))),
            "identifiability": float(
                np.max(
                    np.abs(
                        transformed.identifiability_score - base.identifiability_score
                    )
                )
            ),
            "coherence": float(
                np.max(np.abs(transformed.edge_coherence - base.edge_coherence))
            ),
            "alignment_orthogonality": float(
                np.max(np.abs(alignment.T @ alignment - np.eye(2)))
            ),
            "alignment_determinant_unit": abs(abs(alignment_determinant) - 1.0),
        }
        adjacency_equal = np.array_equal(
            base.field_graph.canonical_edges,
            transformed.field_graph.canonical_edges,
        )
        edge_distances_bit_identical = np.array_equal(
            base.field_graph.edge_distances,
            transformed.field_graph.edge_distances,
        )
        support_equal = np.array_equal(
            base.support_count,
            transformed.support_count,
        )
        field_graph_id = base.field_graph.specification.spec_id
        if field_graph_id != transformed.field_graph.specification.spec_id:
            raise QualificationContractError(
                "representation D3 field graph identities differ"
            )
        crossed_loop_checks: list[dict[str, object]] = []
        for (
            base_cycle_graph,
            transformed_cycle_graph,
        ) in zip(
            base_execution.cycle_graphs,
            transformed_execution.cycle_graphs,
            strict=True,
        ):
            cycle_graph_id = base_cycle_graph.specification.spec_id
            if cycle_graph_id != transformed_cycle_graph.specification.spec_id:
                raise QualificationContractError(
                    "representation D3 cycle graph identities differ"
                )
            base_blind = build_crossed_blind_loop_input(
                base_execution,
                base,
                cycle_graph_id=cycle_graph_id,
                primary_unit_sha256=base_primary_sha256,
            )
            transformed_blind = build_crossed_blind_loop_input(
                transformed_execution,
                transformed,
                cycle_graph_id=cycle_graph_id,
                primary_unit_sha256=transformed_primary_sha256,
            )
            base_prediction = estimate_and_seal_loop(
                base_blind,
                loop_policy,
            )
            transformed_prediction = estimate_and_seal_loop(
                transformed_blind,
                loop_policy,
            )
            crossed_receipt = _representation_loop_law_receipt(
                receipt_version=("spirallens.representation-crossed-loop-law.v0.1"),
                law="ambient_o2_alignment",
                field_graph_id=field_graph_id,
                cycle_graph_id=cycle_graph_id,
                base_blind=base_blind,
                transformed_blind=transformed_blind,
                base_prediction=base_prediction,
                transformed_prediction=transformed_prediction,
                transformation_sha256=canonical_json_sha256(
                    {
                        "ambient_signed_permutation_sha256": (
                            canonical_json_sha256(
                                {"matrix": array_fingerprint(transform)}
                            )
                        ),
                        "alignment": array_fingerprint(alignment),
                    }
                ),
                orientation_determinant=alignment_determinant,
                tolerance=REPRESENTATION_METAMORPHIC_TOLERANCE,
            )
            crossed_loop_checks.append(crossed_receipt)

            reference_angle = 0.31
            reference_rotation = np.asarray(
                (
                    (
                        math.cos(reference_angle),
                        -math.sin(reference_angle),
                    ),
                    (
                        math.sin(reference_angle),
                        math.cos(reference_angle),
                    ),
                ),
                dtype="<f8",
            )
            reference_reflection = np.asarray(
                ((1.0, 0.0), (0.0, -1.0)),
                dtype="<f8",
            )
            for law, reference_transform in (
                ("reference_rotation", reference_rotation),
                ("reference_reflection", reference_reflection),
            ):
                variant = _representation_loop_variant(
                    base_blind,
                    variant_id=(f"{field_graph_id}-{cycle_graph_id}-{law}"),
                    ordered_loop_rows=base_blind.ordered_loop_rows,
                    section_values=(base_blind.section_values @ reference_transform),
                    boundary_identifiability_score=(
                        base_blind.boundary_identifiability_score
                    ),
                    boundary_coherence=base_blind.boundary_coherence,
                )
                variant_prediction = estimate_and_seal_loop(
                    variant,
                    loop_policy,
                )
                loop_variant_checks.append(
                    _representation_loop_law_receipt(
                        receipt_version=(
                            "spirallens.representation-loop-variant-law.v0.1"
                        ),
                        law=law,
                        field_graph_id=field_graph_id,
                        cycle_graph_id=cycle_graph_id,
                        base_blind=base_blind,
                        transformed_blind=variant,
                        base_prediction=base_prediction,
                        transformed_prediction=variant_prediction,
                        transformation_sha256=canonical_json_sha256(
                            {
                                "law": law,
                                "matrix": array_fingerprint(reference_transform),
                            }
                        ),
                        orientation_determinant=float(
                            np.linalg.det(reference_transform)
                        ),
                        tolerance=REPRESENTATION_METAMORPHIC_TOLERANCE,
                    )
                )
            reversed_blind = _representation_loop_variant(
                base_blind,
                variant_id=(f"{field_graph_id}-{cycle_graph_id}-loop-reversal"),
                ordered_loop_rows=base_blind.ordered_loop_rows[::-1],
                section_values=base_blind.section_values[::-1],
                boundary_identifiability_score=(
                    base_blind.boundary_identifiability_score[::-1]
                ),
                boundary_coherence=base_blind.boundary_coherence[::-1],
            )
            reversed_prediction = estimate_and_seal_loop(
                reversed_blind,
                loop_policy,
            )
            loop_variant_checks.append(
                _representation_loop_law_receipt(
                    receipt_version=("spirallens.representation-loop-variant-law.v0.1"),
                    law="loop_reversal",
                    field_graph_id=field_graph_id,
                    cycle_graph_id=cycle_graph_id,
                    base_blind=base_blind,
                    transformed_blind=reversed_blind,
                    base_prediction=base_prediction,
                    transformed_prediction=reversed_prediction,
                    transformation_sha256=canonical_json_sha256(
                        {
                            "law": "loop_reversal",
                            "base_rows": array_fingerprint(
                                base_blind.ordered_loop_rows
                            ),
                            "reversed_rows": array_fingerprint(
                                reversed_blind.ordered_loop_rows
                            ),
                        }
                    ),
                    orientation_determinant=-1.0,
                    tolerance=REPRESENTATION_METAMORPHIC_TOLERANCE,
                )
            )
        loop_laws_verified = all(
            item["verified"] is True for item in crossed_loop_checks
        )
        item_verified = (
            adjacency_equal
            and edge_distances_bit_identical
            and support_equal
            and max(errors.values()) <= REPRESENTATION_METAMORPHIC_TOLERANCE
            and loop_laws_verified
        )
        verified = verified and item_verified
        pipeline_checks.append(
            {
                "field_graph_id": field_graph_id,
                "base_estimator_fingerprint_sha256": base.fingerprint_sha256,
                "transformed_estimator_fingerprint_sha256": (
                    transformed.fingerprint_sha256
                ),
                "adjacency_equal": adjacency_equal,
                "edge_distances_bit_identical": (edge_distances_bit_identical),
                "support_equal": support_equal,
                "alignment_matrix": alignment.tolist(),
                "alignment_sha256": canonical_json_sha256(
                    {"alignment_matrix": alignment.tolist()}
                ),
                "alignment_determinant": alignment_determinant,
                "errors": errors,
                "crossed_loop_checks": crossed_loop_checks,
                "verified": item_verified,
            }
        )
    base_estimate = base_estimates[0]
    row_angles = 0.17 + 0.013 * np.arange(
        base_estimate.local_frames.shape[0], dtype="<f8"
    )
    gauges = np.empty(
        (base_estimate.local_frames.shape[0], 2, 2),
        dtype="<f8",
    )
    gauges[:, 0, 0] = np.cos(row_angles)
    gauges[:, 0, 1] = -np.sin(row_angles)
    gauges[:, 1, 0] = np.sin(row_angles)
    gauges[:, 1, 1] = np.cos(row_angles)
    gauges[::5, :, 1] *= -1.0
    loop_rows = _rectangular_boundary_rows(
        boundary,
        grid_side=protocol.cartesian.grid_side,
    )
    reference_angle = 0.31
    reference_rotation = np.asarray(
        (
            (math.cos(reference_angle), -math.sin(reference_angle)),
            (math.sin(reference_angle), math.cos(reference_angle)),
        ),
        dtype="<f8",
    )
    reference_reflection = np.asarray(((1.0, 0.0), (0.0, -1.0)), dtype="<f8")
    algebraic_checks = (
        ambient_signed_permutation_check(
            states=base_inputs.states,
            local_frames=base_estimate.local_frames,
            signed_permutation=transform.T,
            tolerance=REPRESENTATION_METAMORPHIC_TOLERANCE,
        ),
        local_frame_gauge_check(
            local_frames=base_estimate.local_frames,
            local_coordinates=base_estimate.local_coordinates,
            gauges=gauges,
            tolerance=REPRESENTATION_METAMORPHIC_TOLERANCE,
        ),
        reference_orientation_check(
            section_values=base_estimate.section_values,
            loop_rows=loop_rows,
            reference_transform=reference_rotation,
            tolerance=REPRESENTATION_METAMORPHIC_TOLERANCE,
        ),
        reference_orientation_check(
            section_values=base_estimate.section_values,
            loop_rows=loop_rows,
            reference_transform=reference_reflection,
            tolerance=REPRESENTATION_METAMORPHIC_TOLERANCE,
        ),
        loop_reversal_check(
            section_values=base_estimate.section_values,
            loop_rows=loop_rows,
            tolerance=REPRESENTATION_METAMORPHIC_TOLERANCE,
        ),
        spin_two_double_angle_check(
            spin_two_values=base_estimate.section_values,
            physical_angle=reference_angle,
            tolerance=REPRESENTATION_METAMORPHIC_TOLERANCE,
        ),
        nonorientable_control_check(
            edge_determinants=np.asarray((-1.0, 1.0, 1.0), dtype="<f8"),
            cycle_edge_rows=np.asarray((0, 1, 2), dtype="<i8"),
        ),
    )
    verified = verified and all(
        check.state is QualificationState.PASS for check in algebraic_checks[:-1]
    )
    nonorientable = algebraic_checks[-1]
    verified = verified and (
        nonorientable.state is QualificationState.INSUFFICIENT
        and nonorientable.reason_codes == ("orientation-reversing-cycle",)
    )
    verified = (
        verified
        and len(loop_variant_checks) == 27
        and all(item["verified"] is True for item in loop_variant_checks)
    )
    if not verified:
        raise QualificationContractError(
            "representation D3 pipeline or algebraic check failed"
        )
    transformation_sha256 = canonical_json_sha256(
        {"matrix": array_fingerprint(transform)}
    )
    runtime_receipt = D3PipelineExecutionReceipt.from_representation(
        obligation_checks={
            "ambient-signed-permutation": algebraic_checks[0],
            "local-frame-gauge": algebraic_checks[1],
            "reference-orientation": algebraic_checks[2],
            "loop-reversal": algebraic_checks[4],
            "spin-two-double-angle": algebraic_checks[5],
            "nonorientable-control": algebraic_checks[6],
        },
        pipeline_checks=tuple(pipeline_checks),
        loop_variant_checks=tuple(loop_variant_checks),
        all_algebraic_checks=algebraic_checks,
        development_seed=REPRESENTATION_METAMORPHIC_DEVELOPMENT_SEED,
        transformation_sha256=transformation_sha256,
        tolerance=REPRESENTATION_METAMORPHIC_TOLERANCE,
    )
    return _RepresentationMetamorphicEvidence(
        runtime_receipt=runtime_receipt,
    )


def _static_evidence(
    *,
    protocol: QualificationProtocol,
    source_binding: QualificationSourceBindingSummary,
    d1_cartesian: D1FamilyExecutionReceipt,
    d1_representation: D1FamilyExecutionReceipt,
    d3_cartesian: D3PipelineExecutionReceipt,
    d3_representation: D3PipelineExecutionReceipt,
) -> tuple[
    tuple[GateEvidenceSummary, ...],
    tuple[StaticEvidenceReceipt, ...],
]:
    module_map = {item.module: item for item in protocol.engine.modules}

    def producers(*names: str) -> tuple[ModuleDigest, ...]:
        try:
            return tuple(module_map[name] for name in sorted(names))
        except KeyError as error:
            raise QualificationContractError(
                f"static evidence producer module {error.args[0]!r} is not "
                "source-bound by the protocol"
            ) from error

    runtime_receipts = (
        (
            d1_cartesian,
            producers(
                "spirallens.synthetic.cartesian_fourier_domain_phantom",
                "spirallens.synthetic.cartesian_fourier_estimator",
            ),
        ),
        (
            d1_representation,
            producers(
                "spirallens.synthetic.representation_estimator",
                "spirallens.synthetic.representation_phantom",
            ),
        ),
        (
            d3_cartesian,
            producers(
                "spirallens.qualification.crossed",
                "spirallens.qualification.pipeline_metamorphic",
                "spirallens.qualification.winding",
                "spirallens.synthetic.cartesian_fourier_domain_phantom",
                "spirallens.synthetic.cartesian_fourier_estimator",
            ),
        ),
        (
            d3_representation,
            producers(
                "spirallens.qualification.metamorphic",
                "spirallens.qualification.runner",
                "spirallens.synthetic.representation_estimator",
                "spirallens.synthetic.representation_phantom",
            ),
        ),
    )
    receipts = tuple(
        StaticEvidenceReceipt(
            gate_id=(
                QualificationGateId.D1
                if isinstance(runtime, D1FamilyExecutionReceipt)
                else QualificationGateId.D3
            ),
            evidence_id=runtime.evidence_id,
            attempt_status=AttemptStatus.EVALUABLE,
            underlying_receipt_sha256=runtime.canonical_sha256,
            producer_modules=producer_modules,
            checked_obligation_ids=runtime.obligation_ids,
            failed_obligation_ids=runtime.failed_obligation_ids,
            observation_fingerprints_sha256=(runtime.observation_fingerprints_sha256),
            pipeline_rerun_count=(
                0
                if isinstance(runtime, D1FamilyExecutionReceipt)
                else runtime.pipeline_rerun_count
            ),
            base_estimator_fingerprint_sha256=(
                None
                if isinstance(runtime, D1FamilyExecutionReceipt)
                else runtime.base_estimator_fingerprint_sha256
            ),
            transformed_estimator_fingerprint_sha256=(
                None
                if isinstance(runtime, D1FamilyExecutionReceipt)
                else runtime.transformed_estimator_fingerprint_sha256
            ),
        )
        for runtime, producer_modules in runtime_receipts
    )
    evidence = (
        GateEvidenceSummary(
            gate_id=QualificationGateId.D0,
            evidence_id="engine-module-digests-verified",
            attempt_status=AttemptStatus.EVALUABLE,
            verified=True,
            evidence_fingerprint_sha256=(source_binding.source_binding_receipt_sha256),
            pipeline_rerun_verified=None,
            base_estimator_fingerprint_sha256=None,
            transformed_estimator_fingerprint_sha256=None,
            reason_codes=(),
        ),
        GateEvidenceSummary(
            gate_id=QualificationGateId.D0,
            evidence_id="protocol-manifest-verified",
            attempt_status=AttemptStatus.EVALUABLE,
            verified=True,
            evidence_fingerprint_sha256=protocol.canonical_sha256,
            pipeline_rerun_verified=None,
            base_estimator_fingerprint_sha256=None,
            transformed_estimator_fingerprint_sha256=None,
            reason_codes=(),
        ),
        *(receipt.to_summary() for receipt in receipts),
    )
    return evidence, receipts


def run_calibration_selection(
    loaded_protocol: LoadedQualificationProtocol,
    *,
    source_binding_receipt: QualificationSourceBindingReceipt,
    selection_freeze_artifact: SelectionFreezeArtifact,
    attempt_claim: SelectionAttemptClaimArtifact,
    attempt_store_directory: str | Path,
    launch_authorization: SelectionLaunchAuthorization | None = None,
    _execution_started_callback: Callable[[], None] | None = None,
) -> QualificationResult:
    """Development primitive: execute D0--D5 and return an in-memory receipt.

    ``loaded_protocol`` is the sole protocol boundary: its source bytes are
    canonical and its source digest is derived internally.  A caller-provided
    ``source_binding_receipt`` is only a claimed companion; this entry point
    re-runs the complete local Git/source/loader verification and requires the
    fresh receipt to be byte-identical before executing any generator.  It
    then atomically persists the freeze-keyed execution-start transition, so
    an exception or process failure permanently consumes the sole right to
    enter this frozen selection.  The function performs no terminal publish
    and is intentionally absent from the package's official public surface.
    Production selection callers must use
    :func:`run_and_publish_calibration_selection`, which owns both execution
    and terminal closure.  This primitive has no Pythia, subject,
    semantic-label, or network access.
    """

    if not isinstance(loaded_protocol, LoadedQualificationProtocol):
        raise TypeError("loaded_protocol must be a LoadedQualificationProtocol")
    protocol = loaded_protocol.protocol
    from .preparation import (
        CLOSED_D0_D5_PROTOCOL_ID,
        validate_closed_d0_d5_selection_protocol,
    )

    if protocol.protocol_id == CLOSED_D0_D5_PROTOCOL_ID:
        validate_closed_d0_d5_selection_protocol(
            protocol,
            require_persisted_preseed_readiness=True,
        )
    if not isinstance(selection_freeze_artifact, SelectionFreezeArtifact):
        raise TypeError("selection_freeze_artifact must be a SelectionFreezeArtifact")
    selection_freeze_artifact.validate_loaded_protocol(
        loaded_protocol=loaded_protocol,
    )
    validate_persisted_selection_attempt_claim(
        attempt_store_directory,
        freeze=selection_freeze_artifact,
        attempt_claim=attempt_claim,
    )
    from .launch import SelectionLaunchAuthorization

    if protocol.protocol_id == CLOSED_D0_D5_PROTOCOL_ID:
        if not isinstance(launch_authorization, SelectionLaunchAuthorization):
            raise QualificationContractError(
                "official low-level selection execution requires typed "
                "committed-G launch authorization"
            )
        launch_authorization.validate_companions(
            loaded_protocol=loaded_protocol,
            freeze=selection_freeze_artifact,
            attempt_claim=attempt_claim,
            attempt_store=attempt_store_directory,
        )
        launch_authorization_sha256 = launch_authorization.canonical_sha256
    elif launch_authorization is None:
        launch_authorization_sha256 = None
    else:
        raise QualificationContractError(
            "custom/development selection execution does not accept launch "
            "authorization"
        )
    protocol_source_sha256 = loaded_protocol.source_sha256
    live_source_binding_receipt = verify_protocol_source_binding(
        protocol,
        repository_root=Path(__file__).resolve().parents[3],
        registry_path=(source_binding_receipt.hypothesis_registry.repository_path),
        referent_path=source_binding_receipt.referent_contracts.repository_path,
    )
    if live_source_binding_receipt != source_binding_receipt:
        raise QualificationSourceBindingError(
            "caller-provided source-binding receipt differs from live verification"
        )
    source_binding = _validate_source_and_protocol(
        protocol,
        protocol_source_sha256=protocol_source_sha256,
        source_binding_receipt=live_source_binding_receipt,
    )
    _validate_in_process_callable_bindings()
    begin_selection_execution(
        attempt_store_directory,
        freeze=selection_freeze_artifact,
        attempt_claim=attempt_claim,
        loaded_protocol=loaded_protocol,
        launch_authorization=launch_authorization,
    )
    if _execution_started_callback is not None:
        _execution_started_callback()
    d1_cartesian = _run_cartesian_d1_family(protocol)
    representation = _run_representation_family(protocol)
    representation_metamorphic = _run_representation_metamorphic(
        protocol,
        representation,
    )
    cartesian_metamorphic = run_cartesian_pipeline_metamorphic_checks()
    d3_cartesian = D3PipelineExecutionReceipt.from_cartesian(cartesian_metamorphic)

    core_by_primary: dict[str, list[ExpectedCoreCell]] = {}
    for item in protocol.expected_core_cells:
        core_by_primary.setdefault(item.primary_unit_id, []).append(item)
    loop_by_primary: dict[str, list[ExpectedCell]] = {}
    for item in protocol.expected_cells:
        loop_by_primary.setdefault(item.primary_unit_id, []).append(item)
    if set(core_by_primary) != set(loop_by_primary):
        raise QualificationContractError(
            "core and loop expected primary manifests differ"
        )
    controls = {item.control_id: item for item in protocol.selection.controls}
    core_policy, loop_policy = _policies(protocol)
    d2_confounder_matrix = _run_d2_confounder_matrix(
        protocol,
        core_policy,
    )
    runs: list[_PrimaryRun] = []
    for primary_unit_id in sorted(core_by_primary):
        core_expected = tuple(
            sorted(
                core_by_primary[primary_unit_id],
                key=lambda item: item.core_cell_id,
            )
        )
        loop_expected = tuple(
            sorted(
                loop_by_primary[primary_unit_id],
                key=lambda item: item.cell_id,
            )
        )
        run = _run_primary(
            protocol,
            core_expected=core_expected,
            loop_expected=loop_expected,
            control=controls[core_expected[0].control_id],
            core_policy=core_policy,
            loop_policy=loop_policy,
        )
        runs.append(run)

    core_cells = materialize_expected_core_cells(
        protocol.expected_core_cells,
        (cell for run in runs for cell in run.core_cells),
    )
    core_primaries = collapse_core_primary_units(
        protocol.expected_core_cells,
        core_cells,
        (run.core_template for run in runs),
        candidate_difference_tolerance_rows=(
            protocol.thresholds.core_candidate_difference_tolerance_rows
        ),
    )
    loop_aggregation = aggregate_d4_d5(
        expected_cells=protocol.expected_cells,
        expected_strata=protocol.expected_strata,
        coverage_policy=protocol.coverage_policy,
        observed_cells=(cell for run in runs for cell in run.loop_cells),
        primary_unit_templates=(run.loop_template for run in runs),
        crossed_nonvacuity=(run.nonvacuity for run in runs),
        graph_total_tolerance_cycles=(protocol.thresholds.graph_total_tolerance_cycles),
    )
    evidence, static_receipts = _static_evidence(
        protocol=protocol,
        source_binding=source_binding,
        d1_cartesian=d1_cartesian,
        d1_representation=representation.runtime_receipt,
        d3_cartesian=d3_cartesian,
        d3_representation=representation_metamorphic.runtime_receipt,
    )
    gates = (
        derive_static_gate(QualificationGateId.D0, evidence),
        derive_static_gate(QualificationGateId.D1, evidence),
        build_d2_gate(
            core_primaries,
            confounder_state=d2_confounder_matrix.state,
            confounder_reason_codes=d2_confounder_matrix.reason_codes,
            boundary_axis_id=protocol.cartesian.boundary_axis_id,
            boundary_levels=tuple(
                item.level for item in protocol.cartesian.primary_boundaries
            ),
            core_cells=core_cells,
        ),
        derive_static_gate(QualificationGateId.D3, evidence),
        loop_aggregation.d4_gate,
        loop_aggregation.d5_gate,
    )
    evidence_bundle = QualificationEvidenceBundle(
        protocol_canonical_sha256=protocol.canonical_sha256,
        source_binding_receipt_sha256=(source_binding.source_binding_receipt_sha256),
        selection_freeze_artifact_sha256=(selection_freeze_artifact.canonical_sha256),
        selection_attempt_claim_sha256=attempt_claim.canonical_sha256,
        d2_confounder_matrix_receipt=d2_confounder_matrix,
        static_runtime_receipts=(
            d1_cartesian,
            representation.runtime_receipt,
            d3_cartesian,
            representation_metamorphic.runtime_receipt,
        ),
        core_cell_receipts=tuple(
            sorted(
                (receipt for run in runs for receipt in run.core_evidence),
                key=lambda item: item.core_cell_id,
            )
        ),
        loop_cell_receipts=tuple(
            sorted(
                (receipt for run in runs for receipt in run.loop_evidence),
                key=lambda item: item.cell_id,
            )
        ),
        nonvacuity_receipts=tuple(
            sorted(
                (run.nonvacuity_evidence for run in runs),
                key=lambda item: item.primary_unit_id,
            )
        ),
    )
    evidence_bundle.validate_summaries(
        protocol_canonical_sha256=protocol.canonical_sha256,
        source_binding_receipt_sha256=(source_binding.source_binding_receipt_sha256),
        selection_freeze_artifact_sha256=(selection_freeze_artifact.canonical_sha256),
        selection_attempt_claim_sha256=attempt_claim.canonical_sha256,
        core_cells=core_cells,
        loop_cells=loop_aggregation.crossed_cells,
        nonvacuity=loop_aggregation.crossed_nonvacuity,
    )
    evidence_bundle.validate_static_receipts(static_receipts)
    result_content = {
        "schema_version": RUNNER_SCHEMA_VERSION,
        "protocol_id": protocol.protocol_id,
        "protocol_source_sha256": protocol_source_sha256,
        "protocol_canonical_sha256": protocol.canonical_sha256,
        "selection_freeze_artifact_sha256": (
            selection_freeze_artifact.canonical_sha256
        ),
        "selection_attempt_claim_sha256": attempt_claim.canonical_sha256,
        "selection_launch_authorization_sha256": launch_authorization_sha256,
        "source_binding_receipt_sha256": (source_binding.source_binding_receipt_sha256),
        "evidence_bundle_sha256": evidence_bundle.canonical_sha256,
        "gate_results": [item.to_dict() for item in gates],
        "gate_evidence": [item.to_dict() for item in evidence],
        "static_evidence_receipts": [item.to_dict() for item in static_receipts],
        "core_primary_units": [item.to_dict() for item in core_primaries],
        "core_cells": [item.to_dict() for item in core_cells],
        "primary_units": [item.to_dict() for item in loop_aggregation.primary_units],
        "crossed_cells": [item.to_dict() for item in loop_aggregation.crossed_cells],
        "crossed_nonvacuity": [
            item.to_dict() for item in loop_aggregation.crossed_nonvacuity
        ],
        "strata": [item.to_dict() for item in loop_aggregation.strata],
    }
    result_id = f"qualification-result-{canonical_json_sha256(result_content)[:24]}"
    result_evidence_root = qualification_result_evidence_root_sha256(
        result_id=result_id,
        protocol_id=protocol.protocol_id,
        protocol_source_sha256=protocol_source_sha256,
        protocol_canonical_sha256=protocol.canonical_sha256,
        selection_freeze_artifact_sha256=(selection_freeze_artifact.canonical_sha256),
        selection_attempt_claim_sha256=attempt_claim.canonical_sha256,
        selection_launch_authorization_sha256=launch_authorization_sha256,
        source_binding=source_binding,
        evidence_bundle=evidence_bundle,
        gate_results=gates,
        gate_evidence=evidence,
        static_evidence_receipts=static_receipts,
        core_primary_units=core_primaries,
        core_cells=core_cells,
        primary_units=loop_aggregation.primary_units,
        crossed_cells=loop_aggregation.crossed_cells,
        crossed_nonvacuity=loop_aggregation.crossed_nonvacuity,
        strata=loop_aggregation.strata,
    )
    core_primaries_by_id = {item.primary_unit_id: item for item in core_primaries}
    loop_primaries_by_id = {
        item.primary_unit_id: item for item in loop_aggregation.primary_units
    }
    nonvacuity_by_id = {
        item.primary_unit_id: item for item in loop_aggregation.crossed_nonvacuity
    }
    core_cells_by_lane = {f"core.{item.core_cell_id}": item for item in core_cells}
    loop_cells_by_lane = {
        f"loop.{item.cell_id}": item for item in loop_aggregation.crossed_cells
    }
    ledger = QualificationEventLedger.create(qualification_event_lane_ids(protocol))
    for lane_id in ledger.expected_lane_ids:
        if lane_id.startswith("core."):
            cell = core_cells_by_lane[lane_id]
            payloads = build_qualification_lane_event_payloads(
                protocol=protocol,
                protocol_source_sha256=protocol_source_sha256,
                source_binding=source_binding,
                selection_freeze_artifact_sha256=(
                    selection_freeze_artifact.canonical_sha256
                ),
                result_id=result_id,
                result_evidence_root_sha256=result_evidence_root,
                selection_attempt_claim_sha256=(attempt_claim.canonical_sha256),
                cell=cell,
                primary=core_primaries_by_id[cell.primary_unit_id],
                nonvacuity=None,
                strata=loop_aggregation.strata,
            )
        else:
            cell = loop_cells_by_lane[lane_id]
            payloads = build_qualification_lane_event_payloads(
                protocol=protocol,
                protocol_source_sha256=protocol_source_sha256,
                source_binding=source_binding,
                selection_freeze_artifact_sha256=(
                    selection_freeze_artifact.canonical_sha256
                ),
                result_id=result_id,
                result_evidence_root_sha256=result_evidence_root,
                selection_attempt_claim_sha256=(attempt_claim.canonical_sha256),
                cell=cell,
                primary=loop_primaries_by_id[cell.primary_unit_id],
                nonvacuity=nonvacuity_by_id[cell.primary_unit_id],
                strata=loop_aggregation.strata,
            )
        for payload in payloads:
            ledger = ledger.append(
                lane_id=lane_id,
                event_kind=payload.event_kind,
                payload=payload,
            )
    event_receipt = ledger.receipt()
    result = QualificationResult(
        result_id=result_id,
        protocol_id=protocol.protocol_id,
        protocol_source_sha256=protocol_source_sha256,
        protocol_canonical_sha256=protocol.canonical_sha256,
        selection_freeze_artifact_sha256=(selection_freeze_artifact.canonical_sha256),
        selection_attempt_claim_sha256=attempt_claim.canonical_sha256,
        source_binding=source_binding,
        evidence_bundle=evidence_bundle,
        result_evidence_root_sha256=result_evidence_root,
        event_ledger_receipt=event_receipt,
        gate_results=gates,
        gate_evidence=evidence,
        static_evidence_receipts=static_receipts,
        core_primary_units=core_primaries,
        core_cells=core_cells,
        primary_units=loop_aggregation.primary_units,
        crossed_cells=loop_aggregation.crossed_cells,
        crossed_nonvacuity=loop_aggregation.crossed_nonvacuity,
        strata=loop_aggregation.strata,
        selection_launch_authorization_sha256=launch_authorization_sha256,
    )
    exit_source_binding_receipt = verify_protocol_source_binding(
        protocol,
        repository_root=Path(__file__).resolve().parents[3],
        registry_path=(live_source_binding_receipt.hypothesis_registry.repository_path),
        referent_path=(live_source_binding_receipt.referent_contracts.repository_path),
    )
    if exit_source_binding_receipt != live_source_binding_receipt:
        raise QualificationSourceBindingError(
            "qualification source binding changed during selection execution"
        )
    _validate_in_process_callable_bindings()
    result.validate_against_protocol(
        protocol,
        protocol_source_sha256=protocol_source_sha256,
        source_binding_receipt=exit_source_binding_receipt,
        selection_freeze_artifact=selection_freeze_artifact,
        selection_attempt_claim=attempt_claim,
        selection_launch_authorization_sha256=launch_authorization_sha256,
    )
    return result


def _orchestrated_failure_evidence_sha256(error: BaseException) -> str:
    """Hash the canonical class/message identity of one after-start exception."""

    error_class = type(error)
    return canonical_json_sha256(
        {
            "schema_version": ORCHESTRATED_FAILURE_EVIDENCE_SCHEMA_VERSION,
            "failure_stage": ORCHESTRATED_FAILURE_STAGE,
            "exception_class": (f"{error_class.__module__}.{error_class.__qualname__}"),
            "exception_message": str(error),
        }
    )


def _expected_terminal_publication(
    *,
    attempt_store_directory: str | Path,
    consumption_id: str,
    freeze: SelectionFreezeArtifact,
    attempt_claim: SelectionAttemptClaimArtifact,
    terminal_artifact: QualificationResult | SelectionFailedAttemptArtifact,
    terminal_artifact_kind: TerminalAttemptArtifactKind,
) -> tuple[
    SelectionConsumptionArtifact,
    PersistedSelectionTerminalIdentity,
]:
    """Derive exact terminal identities without mutating the store."""

    consumption = SelectionConsumptionArtifact.consume(
        consumption_id=consumption_id,
        freeze=freeze,
        attempt_claim=attempt_claim,
        terminal_artifact=terminal_artifact,
    )
    manifest = SelectionTerminalManifestArtifact(
        freeze_artifact_sha256=freeze.canonical_sha256,
        attempt_claim_sha256=attempt_claim.canonical_sha256,
        terminal_artifact_kind=terminal_artifact_kind,
        terminal_artifact_sha256=terminal_artifact.canonical_sha256,
        terminal_artifact_byte_count=len(terminal_artifact.canonical_bytes),
        consumption_sha256=consumption.canonical_sha256,
        consumption_byte_count=len(consumption.canonical_bytes),
    )
    return consumption, PersistedSelectionTerminalIdentity(
        path=terminal_selection_transaction_path(
            attempt_store_directory,
            freeze,
        ),
        manifest_sha256=manifest.canonical_sha256,
        terminal_artifact_sha256=terminal_artifact.canonical_sha256,
        consumption_sha256=consumption.canonical_sha256,
    )


def _strict_reload_terminal(
    *,
    identity: PersistedSelectionTerminalIdentity,
    expected_consumption: SelectionConsumptionArtifact,
    expected_terminal_artifact: QualificationResult | SelectionFailedAttemptArtifact,
    freeze: SelectionFreezeArtifact,
    attempt_claim: SelectionAttemptClaimArtifact,
    loaded_protocol: LoadedQualificationProtocol | None = None,
    launch_authorization: SelectionLaunchAuthorization | None = None,
    repository_root: str | Path | None = None,
    registry_path: str | Path | None = None,
    referent_path: str | Path | None = None,
) -> None:
    loaded_consumption, loaded_terminal_artifact = load_terminal_selection_consumption(
        identity.path,
        expected_manifest_sha256=identity.manifest_sha256,
        expected_terminal_artifact_sha256=identity.terminal_artifact_sha256,
        expected_consumption_sha256=identity.consumption_sha256,
        freeze=freeze,
        attempt_claim=attempt_claim,
        loaded_protocol=loaded_protocol,
        launch_authorization=launch_authorization,
        repository_root=repository_root,
        registry_path=registry_path,
        referent_path=referent_path,
    )
    if (
        loaded_consumption != expected_consumption
        or loaded_terminal_artifact != expected_terminal_artifact
    ):
        raise QualificationContractError(
            "terminal artifact differs after strict canonical reload"
        )


def _attach_terminal_publication_receipt(
    error: BaseException,
    *,
    identity: PersistedSelectionTerminalIdentity,
    terminal_artifact_kind: TerminalAttemptArtifactKind,
    publication_call_returned: bool,
    parent_directory_durability_fsync_proved: bool,
) -> OrchestratedTerminalPublicationReceipt:
    receipt = OrchestratedTerminalPublicationReceipt(
        terminal_transaction_path=str(identity.path),
        manifest_sha256=identity.manifest_sha256,
        terminal_artifact_kind=terminal_artifact_kind,
        terminal_artifact_sha256=identity.terminal_artifact_sha256,
        consumption_sha256=identity.consumption_sha256,
        publication_call_returned=publication_call_returned,
        parent_directory_durability_fsync_proved=(
            parent_directory_durability_fsync_proved
        ),
    )
    setattr(
        error,
        ORCHESTRATED_TERMINAL_PUBLICATION_RECEIPT_ATTRIBUTE,
        receipt,
    )
    error.add_note(
        "spirallens_terminal_publication_receipt="
        + receipt.canonical_bytes.decode("utf-8")
    )
    return receipt


def run_and_publish_calibration_selection(
    loaded_protocol: LoadedQualificationProtocol,
    *,
    source_binding_receipt: QualificationSourceBindingReceipt,
    selection_freeze_artifact: SelectionFreezeArtifact,
    attempt_claim: SelectionAttemptClaimArtifact,
    attempt_store_directory: str | Path,
    launch_authorization: SelectionLaunchAuthorization | None = None,
) -> tuple[
    QualificationResult,
    SelectionConsumptionArtifact,
    PersistedSelectionTerminalIdentity,
]:
    """Own one frozen selection from execution start through terminal publish.

    Validation failures before the exclusive execution-start transition remain
    correctable and do not create a terminal record.  After this call owns that
    transition, every ordinary Python outcome is terminal: a valid result is
    published atomically, while any execution or result-publication exception
    first publishes a conservative typed failed-attempt artifact and then
    re-raises the original exception.

    A process kill cannot execute the exception handler.  Its retained
    start-only state is terminal-aborted and requires explicit forensic
    inspection plus manual typed failure publication; it never authorizes a
    retry.
    """

    if not isinstance(loaded_protocol, LoadedQualificationProtocol):
        raise TypeError("loaded_protocol must be a LoadedQualificationProtocol")
    from .launch import SelectionLaunchAuthorization
    from .preparation import (
        CLOSED_D0_D5_PROTOCOL_ID,
        validate_closed_d0_d5_selection_protocol,
    )

    if loaded_protocol.protocol.protocol_id == CLOSED_D0_D5_PROTOCOL_ID:
        validate_closed_d0_d5_selection_protocol(
            loaded_protocol.protocol,
            require_persisted_preseed_readiness=True,
        )
        if not isinstance(launch_authorization, SelectionLaunchAuthorization):
            raise QualificationContractError(
                "official closed D0-D5 execution requires descriptor-derived "
                "committed-G launch authorization"
            )
        launch_authorization.validate_companions(
            loaded_protocol=loaded_protocol,
            freeze=selection_freeze_artifact,
            attempt_claim=attempt_claim,
            attempt_store=attempt_store_directory,
        )
        launch_authorization_sha256 = launch_authorization.canonical_sha256
        chronology_loaded_protocol: LoadedQualificationProtocol | None = loaded_protocol
    elif launch_authorization is None:
        launch_authorization_sha256 = None
        chronology_loaded_protocol = None
    else:
        raise QualificationContractError(
            "custom/development orchestration does not accept launch authorization"
        )

    start_path = selection_execution_start_path(
        attempt_store_directory,
        selection_freeze_artifact,
    )
    terminal_path = terminal_selection_transaction_path(
        attempt_store_directory,
        selection_freeze_artifact,
    )
    start_existed_before_call = start_path.exists() or start_path.is_symlink()
    execution_start_owned = False
    result: QualificationResult | None = None
    expected_result_consumption: SelectionConsumptionArtifact | None = None
    expected_result_terminal_identity: PersistedSelectionTerminalIdentity | None = None
    repository_root = Path(__file__).resolve().parents[3]
    registry_path = source_binding_receipt.hypothesis_registry.repository_path
    referent_path = source_binding_receipt.referent_contracts.repository_path

    def mark_execution_start_owned() -> None:
        nonlocal execution_start_owned
        execution_start_owned = True

    try:
        observed_result = run_calibration_selection(
            loaded_protocol,
            source_binding_receipt=source_binding_receipt,
            selection_freeze_artifact=selection_freeze_artifact,
            attempt_claim=attempt_claim,
            attempt_store_directory=attempt_store_directory,
            launch_authorization=launch_authorization,
            _execution_started_callback=mark_execution_start_owned,
        )
        if not isinstance(observed_result, QualificationResult):
            raise TypeError(
                "run_calibration_selection must return a QualificationResult"
            )
        result = observed_result
        result_consumption_id = f"selection-result-{result.canonical_sha256[:24]}"
        (
            expected_result_consumption,
            expected_result_terminal_identity,
        ) = _expected_terminal_publication(
            attempt_store_directory=attempt_store_directory,
            consumption_id=result_consumption_id,
            freeze=selection_freeze_artifact,
            attempt_claim=attempt_claim,
            terminal_artifact=result,
            terminal_artifact_kind=TerminalAttemptArtifactKind.RESULT,
        )
        consumption, terminal_identity = publish_terminal_selection_consumption(
            attempt_store_directory,
            consumption_id=result_consumption_id,
            freeze=selection_freeze_artifact,
            attempt_claim=attempt_claim,
            terminal_artifact=result,
            loaded_protocol=loaded_protocol,
            launch_authorization=launch_authorization,
            repository_root=repository_root,
            registry_path=registry_path,
            referent_path=referent_path,
        )
        if (
            consumption != expected_result_consumption
            or terminal_identity != expected_result_terminal_identity
        ):
            raise QualificationContractError(
                "result terminal publication returned unexpected canonical identities"
            )
        return result, consumption, terminal_identity
    except BaseException as original_error:
        if (
            not execution_start_owned
            or start_existed_before_call
            or not (start_path.exists() or start_path.is_symlink())
        ):
            raise
        if terminal_path.exists() or terminal_path.is_symlink():
            # Publication may have completed before its final durability call
            # raised.  Strictly recover only the exact expected result terminal;
            # never attempt to replace or overlay that transaction.
            if (
                result is not None
                and expected_result_consumption is not None
                and expected_result_terminal_identity is not None
            ):
                try:
                    _strict_reload_terminal(
                        identity=expected_result_terminal_identity,
                        expected_consumption=expected_result_consumption,
                        expected_terminal_artifact=result,
                        freeze=selection_freeze_artifact,
                        attempt_claim=attempt_claim,
                        loaded_protocol=loaded_protocol,
                        launch_authorization=launch_authorization,
                        repository_root=repository_root,
                        registry_path=registry_path,
                        referent_path=referent_path,
                    )
                    _attach_terminal_publication_receipt(
                        original_error,
                        identity=expected_result_terminal_identity,
                        terminal_artifact_kind=(TerminalAttemptArtifactKind.RESULT),
                        publication_call_returned=False,
                        parent_directory_durability_fsync_proved=False,
                    )
                    original_error.add_note(
                        "typed result terminal publication raised after its "
                        "canonical terminal directory became visible; strict "
                        "roundtrip succeeded, retry is forbidden, and "
                        "parent-directory durability fsync is not proved"
                    )
                except Exception as recovery_error:  # noqa: BLE001
                    original_error.add_note(
                        "visible result terminal did not match the exact "
                        "expected canonical publication: "
                        f"{type(recovery_error).__module__}."
                        f"{type(recovery_error).__qualname__}: "
                        f"{recovery_error}"
                    )
            raise

        try:
            validate_persisted_selection_execution_start(
                attempt_store_directory,
                freeze=selection_freeze_artifact,
                attempt_claim=attempt_claim,
                loaded_protocol=chronology_loaded_protocol,
                launch_authorization=launch_authorization,
            )
            failure_evidence_sha256 = _orchestrated_failure_evidence_sha256(
                original_error
            )
            failed_attempt = SelectionFailedAttemptArtifact.from_freeze(
                failed_attempt_id=(f"selection-failed-{failure_evidence_sha256[:24]}"),
                freeze=selection_freeze_artifact,
                failure_stage=ORCHESTRATED_FAILURE_STAGE,
                failure_evidence_sha256=failure_evidence_sha256,
                attested_selection_values_observed=True,
                selection_launch_authorization_sha256=(launch_authorization_sha256),
            )
            failure_consumption_id = f"selection-failure-{failure_evidence_sha256[:24]}"
            (
                expected_failure_consumption,
                expected_failure_terminal_identity,
            ) = _expected_terminal_publication(
                attempt_store_directory=attempt_store_directory,
                consumption_id=failure_consumption_id,
                freeze=selection_freeze_artifact,
                attempt_claim=attempt_claim,
                terminal_artifact=failed_attempt,
                terminal_artifact_kind=(TerminalAttemptArtifactKind.FAILED_ATTEMPT),
            )
            failure_publication_returned = False
            try:
                (
                    failure_consumption,
                    failure_terminal_identity,
                ) = publish_terminal_selection_consumption(
                    attempt_store_directory,
                    consumption_id=failure_consumption_id,
                    freeze=selection_freeze_artifact,
                    attempt_claim=attempt_claim,
                    terminal_artifact=failed_attempt,
                    loaded_protocol=chronology_loaded_protocol,
                    launch_authorization=launch_authorization,
                )
                failure_publication_returned = True
                if (
                    failure_consumption != expected_failure_consumption
                    or failure_terminal_identity != expected_failure_terminal_identity
                ):
                    raise QualificationContractError(
                        "failed terminal publication returned unexpected "
                        "canonical identities"
                    )
                _strict_reload_terminal(
                    identity=expected_failure_terminal_identity,
                    expected_consumption=expected_failure_consumption,
                    expected_terminal_artifact=failed_attempt,
                    freeze=selection_freeze_artifact,
                    attempt_claim=attempt_claim,
                    loaded_protocol=chronology_loaded_protocol,
                    launch_authorization=launch_authorization,
                )
                _attach_terminal_publication_receipt(
                    original_error,
                    identity=expected_failure_terminal_identity,
                    terminal_artifact_kind=(TerminalAttemptArtifactKind.FAILED_ATTEMPT),
                    publication_call_returned=True,
                    parent_directory_durability_fsync_proved=True,
                )
            except Exception as publication_error:  # noqa: BLE001
                if (
                    expected_failure_terminal_identity.path.exists()
                    or expected_failure_terminal_identity.path.is_symlink()
                ):
                    try:
                        _strict_reload_terminal(
                            identity=expected_failure_terminal_identity,
                            expected_consumption=expected_failure_consumption,
                            expected_terminal_artifact=failed_attempt,
                            freeze=selection_freeze_artifact,
                            attempt_claim=attempt_claim,
                            loaded_protocol=chronology_loaded_protocol,
                            launch_authorization=launch_authorization,
                        )
                        _attach_terminal_publication_receipt(
                            original_error,
                            identity=expected_failure_terminal_identity,
                            terminal_artifact_kind=(
                                TerminalAttemptArtifactKind.FAILED_ATTEMPT
                            ),
                            publication_call_returned=(failure_publication_returned),
                            parent_directory_durability_fsync_proved=(
                                failure_publication_returned
                            ),
                        )
                        if not failure_publication_returned:
                            original_error.add_note(
                                "typed terminal failure publication raised "
                                "after its canonical terminal directory became "
                                "visible; strict roundtrip succeeded, retry is "
                                "forbidden, and parent-directory durability "
                                "fsync is not proved: "
                                f"{type(publication_error).__module__}."
                                f"{type(publication_error).__qualname__}: "
                                f"{publication_error}"
                            )
                    except Exception as recovery_error:  # noqa: BLE001
                        original_error.add_note(
                            "typed terminal failure publication left a visible "
                            "terminal directory, but strict recovery failed: "
                            f"{type(publication_error).__module__}."
                            f"{type(publication_error).__qualname__}: "
                            f"{publication_error}; recovery="
                            f"{type(recovery_error).__module__}."
                            f"{type(recovery_error).__qualname__}: "
                            f"{recovery_error}"
                        )
                else:
                    original_error.add_note(
                        "typed terminal failure publication did not complete: "
                        f"{type(publication_error).__module__}."
                        f"{type(publication_error).__qualname__}: "
                        f"{publication_error}"
                    )
        except Exception as publication_error:  # noqa: BLE001
            original_error.add_note(
                "typed terminal failure publication did not complete: "
                f"{type(publication_error).__module__}."
                f"{type(publication_error).__qualname__}: "
                f"{publication_error}"
            )
        raise
