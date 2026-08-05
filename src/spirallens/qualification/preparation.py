"""Outcome-blind construction of the closed 64-primary D0--D5 protocol.

This module constructs declarations only.  It does not instantiate a
phantom, execute an estimator, read a selection outcome, or acquire an
attempt claim.  Selection seeds are caller-supplied so the engine commit can
be fixed before the candidate family is chosen.  This module excludes known
development seeds but does not prove that any remaining seed is unseen.
"""

from __future__ import annotations

import hashlib
import os
import stat
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import ClassVar

from spirallens._repository_context import RepositoryContext
from spirallens.core.canonical import (
    CanonicalJsonError,
    canonical_json_bytes,
    canonical_json_sha256,
    parse_canonical_json,
    sha256_bytes,
)
from spirallens.graphs import GraphFamily, GraphPurpose
from spirallens.instrument_contracts import load_hypothesis_registry
from spirallens.referents import (
    canonical_f0_f4_referent_contracts,
    load_referent_contract_set,
)

from .common import (
    CoreDisposition,
    EvaluationUnit,
    LoopDisposition,
    QualificationContractError,
)
from .crossed import (
    domain_construction_sha256,
    support_construction_sha256,
)
from .protocol import (
    BOUNDARY_AXIS_ID,
    CLOSED_CARTESIAN_ESTIMATOR_ID,
    CLOSED_CARTESIAN_GENERATOR_FAMILY_ID,
    CLOSED_CARTESIAN_TRIVIALIZATION_ID,
    CLOSED_CORE_LOCALIZER_ID,
    CLOSED_REPRESENTATION_ESTIMATOR_ID,
    CLOSED_REPRESENTATION_TRIVIALIZATION_ID,
    F2_LOCAL_COVARIANT_SECTION_REFERENT_ID,
    STATE_GEOMETRY_WARP_AXIS_ID,
    STRUCTURED_OBSERVATION_PERTURBATION_AXIS_ID,
    AuthorityBoundary,
    BoundaryTemplate,
    CartesianSelectionSubstrate,
    ClosedImplementationRegistry,
    ControlDeclaration,
    CoveragePolicy,
    DomainDeclaration,
    EngineBinding,
    ExpectedCell,
    ExpectedCoreCell,
    ExpectedStratum,
    GeneratorCaseBinding,
    GraphAxes,
    GraphDeclaration,
    InstrumentSelection,
    LoopRole,
    ModuleDigest,
    NumericStressLevel,
    PreseedReadinessBinding,
    QualificationProtocol,
    RegistryBinding,
    RepositoryFileDigest,
    SelectionDesign,
    StressAssignment,
    StressAxis,
    Thresholds,
    required_stress_stratum_id,
)
from .source_binding import (
    QualificationSourceBindingError,
    QualificationSourceBindingReceipt,
    QualificationSourceBindingSummary,
    module_repository_path,
    verify_source_binding,
)

CLOSED_D0_D5_PROTOCOL_ID = "d0-d5-f2-cartesian-selection-v0-1"
CLOSED_D0_D5_PROTOCOL_FACTORY_ID = "spirallens.closed-d0-d5-protocol-factory.v0.1"
CLOSED_D0_D5_SELECTION_SEED_COUNT = 2
CLOSED_D0_D5_PRIMARY_UNIT_COUNT = 64
CLOSED_D0_D5_PRESEED_READINESS_SCHEMA_VERSION = (
    "spirallens.closed-d0-d5-preseed-readiness.v0.1"
)
CLOSED_D0_D5_PRESEED_READINESS_ARTIFACT_ID = "d0-d5-f2-cartesian-preseed-readiness-v0-1"
MAX_CLOSED_D0_D5_PRESEED_READINESS_BYTES = 64 * 1024
CLOSED_D0_D5_OFFICIAL_EXECUTABLE_PATHS = (
    "scripts/prepare_d0_d5_launch.py",
    "scripts/prepare_d0_d5_selection.py",
    "scripts/run_d0_d5_selection.py",
)
CLOSED_D0_D5_KNOWN_SEED_EXCLUSION_SCHEMA_VERSION = (
    "spirallens.closed-d0-d5-known-seed-exclusion-registry.v0.1"
)
_CLOSED_D0_D5_KNOWN_SEED_EXCLUSION_ENTRIES = (
    (3, "cartesian generator development test"),
    (4, "cartesian generator counterfactual test"),
    (101, "qualification development and stress tests"),
    (202, "qualification preparation declaration test"),
    (314159, "permanent qualification metamorphic development seed"),
    (314160, "qualification metamorphic rejected-seed test"),
    (424242, "full-envelope development stress audit"),
    (424243, "full-envelope development stress audit"),
)


@dataclass(frozen=True, slots=True)
class ClosedD0D5KnownSeedExclusionRegistry:
    """Canonical list of seeds that cannot be represented as unopened.

    Absence from this finite list is only a local known-seed check.  It is not
    cryptographic evidence that a seed or its outcomes have never been seen;
    that remains an external process attestation.
    """

    registry_id: str
    entries: tuple[tuple[int, str], ...]
    schema_version: str = CLOSED_D0_D5_KNOWN_SEED_EXCLUSION_SCHEMA_VERSION
    unseen_status: str = "external-attestation-required"
    cryptographic_unseen_proof: bool = False
    scientific_claim_eligible: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != CLOSED_D0_D5_KNOWN_SEED_EXCLUSION_SCHEMA_VERSION:
            raise QualificationContractError(
                "known-seed registry schema_version differs from the contract"
            )
        if self.registry_id != "closed-d0-d5-known-development-seeds-v0-1":
            raise QualificationContractError(
                "known-seed registry_id differs from the canonical registry"
            )
        if type(self.entries) is not tuple or not self.entries:
            raise QualificationContractError(
                "known-seed registry entries must be a non-empty immutable tuple"
            )
        previous = -1
        for seed, reason in self.entries:
            if (
                type(seed) is not int
                or seed < 0
                or seed <= previous
                or not isinstance(reason, str)
                or not reason
            ):
                raise QualificationContractError(
                    "known-seed entries must be strictly ordered nonnegative "
                    "integers with non-empty reasons"
                )
            previous = seed
        if self.entries != _CLOSED_D0_D5_KNOWN_SEED_EXCLUSION_ENTRIES:
            raise QualificationContractError(
                "known-seed registry entries differ from the canonical "
                "development/exploratory seed set"
            )
        if self.unseen_status != "external-attestation-required":
            raise QualificationContractError(
                "known-seed registry unseen_status differs from the boundary"
            )
        if self.cryptographic_unseen_proof is not False:
            raise QualificationContractError(
                "known-seed registry cannot claim cryptographic unseen proof"
            )
        if self.scientific_claim_eligible is not False:
            raise QualificationContractError(
                "known-seed registry cannot grant scientific claim eligibility"
            )

    @property
    def seeds(self) -> tuple[int, ...]:
        return tuple(seed for seed, _reason in self.entries)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "registry_id": self.registry_id,
            "entries": [
                {"seed": seed, "reason": reason} for seed, reason in self.entries
            ],
            "unseen_status": self.unseen_status,
            "cryptographic_unseen_proof": self.cryptographic_unseen_proof,
            "scientific_claim_eligible": self.scientific_claim_eligible,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


CLOSED_D0_D5_KNOWN_SEED_EXCLUSION_REGISTRY = ClosedD0D5KnownSeedExclusionRegistry(
    registry_id="closed-d0-d5-known-development-seeds-v0-1",
    entries=_CLOSED_D0_D5_KNOWN_SEED_EXCLUSION_ENTRIES,
)


def _normalized_absolute_path(path: str | Path, *, label: str) -> Path:
    result = Path(os.path.abspath(Path(path)))
    if not result.is_absolute():
        raise QualificationSourceBindingError(f"{label} must be absolute")
    return result


@dataclass(frozen=True, slots=True)
class ClosedD0D5PreseedReadinessArtifact:
    """Durable official-process evidence published before seed supply.

    The artifact attests the order enforced by the official preparation
    function only.  It does not cryptographically prove that a human or
    another process had not already selected, recorded, or observed a seed.
    """

    artifact_path: str
    repository_root: str
    registry_path: str
    referent_path: str
    source_readiness: QualificationSourceBindingSummary
    referent_source_sha256: str
    schema_version: str = CLOSED_D0_D5_PRESEED_READINESS_SCHEMA_VERSION
    artifact_id: str = CLOSED_D0_D5_PRESEED_READINESS_ARTIFACT_ID
    role: str = "closed_d0_d5_preseed_readiness"
    claim_ceiling: str = "level_0"
    chronology_claim: str = "official-process-attested"
    official_seed_supplier_invoked: bool = False
    selection_seed_present: bool = False
    selection_value_observed: bool = False
    cryptographic_preseed_proof: bool = False
    human_or_external_process_unseen_proof: bool = False
    scientific_claim_eligible: bool = False

    _ROOT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "artifact_id",
            "role",
            "claim_ceiling",
            "artifact_path",
            "repository_root",
            "registry_path",
            "referent_path",
            "source_readiness",
            "referent_source_sha256",
            "chronology_claim",
            "official_seed_supplier_invoked",
            "selection_seed_present",
            "selection_value_observed",
            "cryptographic_preseed_proof",
            "human_or_external_process_unseen_proof",
            "scientific_claim_eligible",
        }
    )

    def __post_init__(self) -> None:
        expected_constants = {
            "schema_version": CLOSED_D0_D5_PRESEED_READINESS_SCHEMA_VERSION,
            "artifact_id": CLOSED_D0_D5_PRESEED_READINESS_ARTIFACT_ID,
            "role": "closed_d0_d5_preseed_readiness",
            "claim_ceiling": "level_0",
            "chronology_claim": "official-process-attested",
        }
        for name, expected in expected_constants.items():
            if (
                type(getattr(self, name)) is not type(expected)
                or getattr(self, name) != expected
            ):
                raise QualificationContractError(
                    f"preseed readiness {name} must equal {expected!r}"
                )
        for name in (
            "artifact_path",
            "repository_root",
            "registry_path",
            "referent_path",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or not value
                or str(_normalized_absolute_path(value, label=name)) != value
            ):
                raise QualificationContractError(
                    f"preseed readiness {name} must be a normalized absolute path"
                )
        try:
            Path(self.artifact_path).relative_to(Path(self.repository_root))
        except ValueError as error:
            raise QualificationContractError(
                "preseed readiness artifact_path must be inside repository_root"
            ) from error
        if not isinstance(
            self.source_readiness,
            QualificationSourceBindingSummary,
        ):
            raise TypeError(
                "source_readiness must be a QualificationSourceBindingSummary"
            )
        if (
            not isinstance(self.referent_source_sha256, str)
            or len(self.referent_source_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in self.referent_source_sha256
            )
        ):
            raise QualificationContractError(
                "preseed readiness referent_source_sha256 must be a SHA-256"
            )
        if (
            self.referent_source_sha256
            != self.source_readiness.referent_canonical_sha256
        ):
            raise QualificationContractError(
                "preseed readiness canonical referent source differs from "
                "its canonical identity"
            )
        for name in (
            "official_seed_supplier_invoked",
            "selection_seed_present",
            "selection_value_observed",
            "cryptographic_preseed_proof",
            "human_or_external_process_unseen_proof",
            "scientific_claim_eligible",
        ):
            if getattr(self, name) is not False:
                raise QualificationContractError(
                    f"preseed readiness {name} must remain false"
                )
        if len(self.canonical_bytes) > MAX_CLOSED_D0_D5_PRESEED_READINESS_BYTES:
            raise QualificationContractError(
                "preseed readiness artifact exceeds the fixed byte cap"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "artifact_id": self.artifact_id,
            "role": self.role,
            "claim_ceiling": self.claim_ceiling,
            "artifact_path": self.artifact_path,
            "repository_root": self.repository_root,
            "registry_path": self.registry_path,
            "referent_path": self.referent_path,
            "source_readiness": self.source_readiness.to_dict(),
            "referent_source_sha256": self.referent_source_sha256,
            "chronology_claim": self.chronology_claim,
            "official_seed_supplier_invoked": self.official_seed_supplier_invoked,
            "selection_seed_present": self.selection_seed_present,
            "selection_value_observed": self.selection_value_observed,
            "cryptographic_preseed_proof": self.cryptographic_preseed_proof,
            "human_or_external_process_unseen_proof": (
                self.human_or_external_process_unseen_proof
            ),
            "scientific_claim_eligible": self.scientific_claim_eligible,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    def binding(
        self,
        *,
        source_sha256: str,
        byte_count: int,
    ) -> PreseedReadinessBinding:
        return PreseedReadinessBinding(
            artifact_path=self.artifact_path,
            artifact_source_sha256=source_sha256,
            artifact_canonical_sha256=self.canonical_sha256,
            artifact_byte_count=byte_count,
            source_binding_receipt_sha256=(
                self.source_readiness.source_binding_receipt_sha256
            ),
            engine_commit=self.source_readiness.engine_commit,
            registry_source_sha256=self.source_readiness.registry_source_sha256,
            registry_canonical_sha256=(self.source_readiness.registry_canonical_sha256),
            referent_source_sha256=self.referent_source_sha256,
            referent_canonical_sha256=(self.source_readiness.referent_canonical_sha256),
        )

    @classmethod
    def from_dict(cls, value: object) -> ClosedD0D5PreseedReadinessArtifact:
        if not isinstance(value, dict) or any(
            not isinstance(key, str) for key in value
        ):
            raise QualificationContractError(
                "preseed readiness artifact must be a string-keyed mapping"
            )
        if set(value) != set(cls._ROOT_KEYS):
            raise QualificationContractError(
                "preseed readiness artifact fields differ from the contract"
            )
        return cls(
            schema_version=value["schema_version"],  # type: ignore[arg-type]
            artifact_id=value["artifact_id"],  # type: ignore[arg-type]
            role=value["role"],  # type: ignore[arg-type]
            claim_ceiling=value["claim_ceiling"],  # type: ignore[arg-type]
            artifact_path=value["artifact_path"],  # type: ignore[arg-type]
            repository_root=value["repository_root"],  # type: ignore[arg-type]
            registry_path=value["registry_path"],  # type: ignore[arg-type]
            referent_path=value["referent_path"],  # type: ignore[arg-type]
            source_readiness=QualificationSourceBindingSummary.from_dict(
                value["source_readiness"]
            ),
            referent_source_sha256=value["referent_source_sha256"],  # type: ignore[arg-type]
            chronology_claim=value["chronology_claim"],  # type: ignore[arg-type]
            official_seed_supplier_invoked=value[  # type: ignore[arg-type]
                "official_seed_supplier_invoked"
            ],
            selection_seed_present=value["selection_seed_present"],  # type: ignore[arg-type]
            selection_value_observed=value["selection_value_observed"],  # type: ignore[arg-type]
            cryptographic_preseed_proof=value[  # type: ignore[arg-type]
                "cryptographic_preseed_proof"
            ],
            human_or_external_process_unseen_proof=value[  # type: ignore[arg-type]
                "human_or_external_process_unseen_proof"
            ],
            scientific_claim_eligible=value["scientific_claim_eligible"],  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class LoadedClosedD0D5PreseedReadinessArtifact:
    """One exact canonical pre-seed readiness artifact loaded from disk."""

    artifact: ClosedD0D5PreseedReadinessArtifact
    source_path: Path
    source_bytes: bytes
    source_sha256: str
    canonical_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.artifact, ClosedD0D5PreseedReadinessArtifact):
            raise TypeError("artifact must be a ClosedD0D5PreseedReadinessArtifact")
        if not isinstance(self.source_path, Path) or not self.source_path.is_absolute():
            raise TypeError("source_path must be an absolute Path")
        if not isinstance(self.source_bytes, bytes) or not self.source_bytes:
            raise TypeError("source_bytes must be non-empty bytes")
        if hashlib.sha256(self.source_bytes).hexdigest() != self.source_sha256:
            raise QualificationContractError(
                "preseed readiness source bytes differ from source_sha256"
            )
        if (
            self.source_bytes != self.artifact.canonical_bytes
            or self.canonical_sha256 != self.artifact.canonical_sha256
            or self.source_sha256 != self.canonical_sha256
            or self.artifact.artifact_path != str(self.source_path)
        ):
            raise QualificationContractError(
                "preseed readiness artifact differs from its canonical "
                "path/content identity"
            )

    @property
    def binding(self) -> PreseedReadinessBinding:
        return self.artifact.binding(
            source_sha256=self.source_sha256,
            byte_count=len(self.source_bytes),
        )


def load_closed_d0_d5_preseed_readiness_artifact(
    path: str | Path,
    *,
    expected_source_sha256: str,
    expected_canonical_sha256: str,
) -> LoadedClosedD0D5PreseedReadinessArtifact:
    """Load one exact regular canonical readiness artifact, fail closed."""

    source_path = _normalized_absolute_path(path, label="preseed readiness path")
    if source_path.is_symlink():
        raise QualificationContractError(
            "preseed readiness artifact must not be a symbolic link"
        )
    try:
        before = source_path.stat()
        source = source_path.read_bytes()
        after = source_path.stat()
    except OSError as error:
        raise QualificationContractError(
            f"cannot read preseed readiness artifact: {error}"
        ) from error
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or before.st_ctime_ns != after.st_ctime_ns
        or before.st_nlink != 1
        or after.st_nlink != 1
        or len(source) != after.st_size
        or not source
        or len(source) > MAX_CLOSED_D0_D5_PRESEED_READINESS_BYTES
    ):
        raise QualificationContractError(
            "preseed readiness artifact is not one stable bounded regular file"
        )
    source_sha256 = hashlib.sha256(source).hexdigest()
    if source_sha256 != expected_source_sha256:
        raise QualificationContractError(
            "preseed readiness artifact source SHA-256 differs"
        )
    try:
        document = parse_canonical_json(
            source,
            label="preseed readiness artifact",
        )
    except CanonicalJsonError as error:
        raise QualificationContractError(str(error)) from error
    artifact = ClosedD0D5PreseedReadinessArtifact.from_dict(document)
    if artifact.canonical_sha256 != expected_canonical_sha256:
        raise QualificationContractError(
            "preseed readiness artifact canonical identity differs"
        )
    return LoadedClosedD0D5PreseedReadinessArtifact(
        artifact=artifact,
        source_path=source_path,
        source_bytes=source,
        source_sha256=source_sha256,
        canonical_sha256=artifact.canonical_sha256,
    )


def publish_closed_d0_d5_preseed_readiness_artifact(
    path: str | Path,
    *,
    repository_root: str | Path,
    registry_path: str | Path,
    referent_path: str | Path,
    source_readiness_receipt: QualificationSourceBindingReceipt,
) -> LoadedClosedD0D5PreseedReadinessArtifact:
    """Publish without overwrite and round-trip before returning."""

    if not isinstance(
        source_readiness_receipt,
        QualificationSourceBindingReceipt,
    ):
        raise TypeError(
            "source_readiness_receipt must be a QualificationSourceBindingReceipt"
        )
    destination = _normalized_absolute_path(path, label="preseed readiness path")
    repository = _normalized_absolute_path(
        repository_root,
        label="repository_root",
    )
    try:
        repository = repository.resolve(strict=True)
    except OSError as error:
        raise QualificationContractError(
            "repository_root must be an existing real directory"
        ) from error
    try:
        destination.relative_to(repository)
    except ValueError as error:
        raise QualificationContractError(
            "preseed readiness artifact must be published inside repository_root"
        ) from error
    registry = _repository_input_path(repository, registry_path)
    referent = _repository_input_path(repository, referent_path)
    try:
        parent = destination.parent.resolve(strict=True)
    except OSError as error:
        raise QualificationContractError(
            "preseed readiness parent must be an existing real directory"
        ) from error
    if parent != destination.parent or not parent.is_dir() or parent.is_symlink():
        raise QualificationContractError(
            "preseed readiness parent must be an existing real directory"
        )
    if destination.exists() or destination.is_symlink():
        raise QualificationContractError(
            f"refusing to overwrite preseed readiness artifact: {destination}"
        )
    artifact = ClosedD0D5PreseedReadinessArtifact(
        artifact_path=str(destination),
        repository_root=str(repository),
        registry_path=str(registry),
        referent_path=str(referent),
        source_readiness=QualificationSourceBindingSummary.from_receipt(
            source_readiness_receipt
        ),
        referent_source_sha256=(
            source_readiness_receipt.referent_contracts.source_sha256
        ),
    )
    payload = artifact.canonical_bytes
    descriptor, temporary_name = tempfile.mkstemp(
        dir=parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError as error:
            raise QualificationContractError(
                f"refusing to overwrite preseed readiness artifact: {destination}"
            ) from error
        except OSError as error:
            raise QualificationContractError(
                f"cannot atomically publish preseed readiness artifact: {error}"
            ) from error
        directory_flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            directory_flags |= os.O_DIRECTORY
        directory_descriptor = os.open(parent, directory_flags)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    loaded = load_closed_d0_d5_preseed_readiness_artifact(
        destination,
        expected_source_sha256=artifact.canonical_sha256,
        expected_canonical_sha256=artifact.canonical_sha256,
    )
    if loaded.artifact != artifact:
        raise QualificationContractError(
            "preseed readiness artifact differs after canonical round-trip"
        )
    return loaded


def build_current_qualification_engine_binding(
    *,
    engine_commit: str,
    repository_root: str | Path,
) -> EngineBinding:
    """Bind the current complete runner closure to one declared commit.

    This hashes local source only.  The later source verifier proves that the
    supplied commit resolves exactly and that every working/HEAD/bound blob
    equals these declarations.
    """

    from . import runner as runner_module

    context = RepositoryContext(
        root=Path(os.path.abspath(Path(repository_root))),
    )
    root = context.root
    imported_sources = (
        (
            __file__,
            "src/spirallens/qualification/preparation.py",
            "qualification preparation",
        ),
        (
            runner_module.__file__,
            "src/spirallens/qualification/runner.py",
            "qualification runner closure",
        ),
    )
    for imported_file, repository_path, label in imported_sources:
        if not context.matches_imported_file(
            imported_file=imported_file,
            repository_path=repository_path,
        ):
            raise QualificationContractError(
                f"{label} import origin differs from repository_root"
            )

    return EngineBinding(
        repository="RyoSpiralArchitect/SpiralLens",
        commit=engine_commit,
        modules=tuple(
            ModuleDigest(
                module,
                sha256_bytes(
                    (
                        root / module_repository_path(module, repository_root=root)
                    ).read_bytes()
                ),
            )
            for module in sorted(runner_module.REQUIRED_ENGINE_MODULES)
        ),
        official_executables=tuple(
            RepositoryFileDigest(
                repository_path=repository_path,
                sha256=sha256_bytes((root / repository_path).read_bytes()),
            )
            for repository_path in CLOSED_D0_D5_OFFICIAL_EXECUTABLE_PATHS
        ),
    )


def _instrument() -> InstrumentSelection:
    return InstrumentSelection(
        referent_id=F2_LOCAL_COVARIANT_SECTION_REFERENT_ID,
        estimator_id=CLOSED_REPRESENTATION_ESTIMATOR_ID,
        trivialization_id=CLOSED_REPRESENTATION_TRIVIALIZATION_ID,
        core_localizer_id=CLOSED_CORE_LOCALIZER_ID,
    )


def _implementation_registry() -> ClosedImplementationRegistry:
    instrument = _instrument()
    return ClosedImplementationRegistry(
        generator_family_id=CLOSED_CARTESIAN_GENERATOR_FAMILY_ID,
        generator_cases=(
            GeneratorCaseBinding(
                "cartesian-fourier-fixed-null",
                CoreDisposition.LOCALIZED_CORE,
                LoopDisposition.NULL,
            ),
            GeneratorCaseBinding(
                "cartesian-fourier-no-core-null",
                CoreDisposition.NO_CORE,
                LoopDisposition.NULL,
            ),
            GeneratorCaseBinding(
                "cartesian-fourier-positive",
                CoreDisposition.LOCALIZED_CORE,
                LoopDisposition.NONZERO,
            ),
            GeneratorCaseBinding(
                "cartesian-fourier-prerequisite-failure",
                CoreDisposition.PREREQUISITE_FAILURE,
                LoopDisposition.PREREQUISITE_FAILURE,
            ),
        ),
        surrogate_estimator_id=CLOSED_CARTESIAN_ESTIMATOR_ID,
        surrogate_trivialization_id=CLOSED_CARTESIAN_TRIVIALIZATION_ID,
        instrument=instrument,
    )


def _controls() -> tuple[ControlDeclaration, ...]:
    return (
        ControlDeclaration(
            control_id="fixed-null-core",
            generator_case_id="cartesian-fourier-fixed-null",
            core_disposition=CoreDisposition.LOCALIZED_CORE,
            loop_disposition=LoopDisposition.NULL,
        ),
        ControlDeclaration(
            control_id="nonzero-core",
            generator_case_id="cartesian-fourier-positive",
            core_disposition=CoreDisposition.LOCALIZED_CORE,
            loop_disposition=LoopDisposition.NONZERO,
            field_sensitivity_sentinel=True,
        ),
        ControlDeclaration(
            control_id="null-no-core",
            generator_case_id="cartesian-fourier-no-core-null",
            core_disposition=CoreDisposition.NO_CORE,
            loop_disposition=LoopDisposition.NULL,
        ),
        ControlDeclaration(
            control_id="prerequisite",
            generator_case_id="cartesian-fourier-prerequisite-failure",
            core_disposition=CoreDisposition.PREREQUISITE_FAILURE,
            loop_disposition=LoopDisposition.PREREQUISITE_FAILURE,
        ),
    )


def _graph(
    graph_id: str,
    family: GraphFamily,
    purpose: GraphPurpose,
) -> GraphDeclaration:
    if family is GraphFamily.MUTUAL_KNN:
        parameters: tuple[tuple[str, int | float], ...] = (("neighbor_count", 4),)
    elif family is GraphFamily.FIXED_RADIUS:
        parameters = (("radius", 0.48),)
    else:
        parameters = (
            (
                "minimum_shared_neighbors",
                2 if purpose is GraphPurpose.FIELD_ESTIMATION else 1,
            ),
            ("neighbor_count", 4),
        )
    return GraphDeclaration(
        graph_id=graph_id,
        family=family,
        purpose=purpose,
        parameters=parameters,
    )


def closed_d0_d5_graph_axes() -> GraphAxes:
    """Return the reviewed graph-family axes shared by later confirmations."""

    return GraphAxes(
        field_estimation=(
            _graph(
                "a-mutual",
                GraphFamily.MUTUAL_KNN,
                GraphPurpose.FIELD_ESTIMATION,
            ),
            _graph(
                "a-radius",
                GraphFamily.FIXED_RADIUS,
                GraphPurpose.FIELD_ESTIMATION,
            ),
            _graph(
                "a-shared",
                GraphFamily.SHARED_NEIGHBOR,
                GraphPurpose.FIELD_ESTIMATION,
            ),
        ),
        cycle_construction=(
            _graph(
                "b-mutual",
                GraphFamily.MUTUAL_KNN,
                GraphPurpose.CYCLE_CONSTRUCTION,
            ),
            _graph(
                "b-radius",
                GraphFamily.FIXED_RADIUS,
                GraphPurpose.CYCLE_CONSTRUCTION,
            ),
            _graph(
                "b-shared",
                GraphFamily.SHARED_NEIGHBOR,
                GraphPurpose.CYCLE_CONSTRUCTION,
            ),
        ),
    )


def closed_d0_d5_stress_axes() -> tuple[StressAxis, ...]:
    """Return the reviewed three-factor stress template without any seeds."""

    return (
        StressAxis(BOUNDARY_AXIS_ID, ("central", "wide")),
        StressAxis(STATE_GEOMETRY_WARP_AXIS_ID, ("nominal", "stressed")),
        StressAxis(
            STRUCTURED_OBSERVATION_PERTURBATION_AXIS_ID,
            ("nominal", "stressed"),
        ),
    )


def closed_d0_d5_cartesian_substrate() -> CartesianSelectionSubstrate:
    """Return the reviewed numeric stress and boundary translation profile."""

    return CartesianSelectionSubstrate(
        generator_family_id=CLOSED_CARTESIAN_GENERATOR_FAMILY_ID,
        grid_side=7,
        ambient_dimension=12,
        samples_per_split=8,
        baseline=1.25,
        second_harmonic_scale=0.35,
        structured_observation_perturbation_axis_id=(
            STRUCTURED_OBSERVATION_PERTURBATION_AXIS_ID
        ),
        structured_observation_perturbation_levels=(
            NumericStressLevel("nominal", 0.0),
            NumericStressLevel("stressed", 0.01),
        ),
        state_geometry_warp_axis_id=STATE_GEOMETRY_WARP_AXIS_ID,
        state_geometry_warp_levels=(
            NumericStressLevel("nominal", 0.0),
            NumericStressLevel("stressed", 0.1),
        ),
        boundary_axis_id=BOUNDARY_AXIS_ID,
        primary_boundaries=(
            BoundaryTemplate("central", 2, 2, 4, 4),
            BoundaryTemplate("wide", 1, 1, 5, 5),
        ),
        offcore_boundary=BoundaryTemplate("offcore", 0, 0, 1, 1),
    )


def closed_d0_d5_thresholds() -> Thresholds:
    """Return the reviewed numeric policy inherited by D7 confirmation."""

    return Thresholds(
        d1_numeric_tolerance=1e-10,
        d1_cartesian_direction_cosine_floor=0.99,
        d1_representation_phase_coherence_floor=0.99,
        core_amplitude_ceiling=0.05,
        identifiability_floor=0.2,
        coherence_floor=0.3,
        minimum_support_count=2,
        max_localized_core_fraction=0.05,
        minimum_core_contrast_ratio=2.0,
        branch_margin_rad=0.05,
        loop_nonzero_floor_cycles=0.5,
        loop_oracle_tolerance_cycles=1e-8,
        graph_total_tolerance_cycles=1e-8,
        core_candidate_difference_tolerance_rows=0,
        minimum_representative_content_variants=2,
        minimum_field_output_effect_size=1e-6,
    )


def closed_d0_d5_coverage_policy() -> CoveragePolicy:
    """Return the reviewed worst-case repeated-measures aggregation policy."""

    return CoveragePolicy(
        evaluation_unit=EvaluationUnit.PHANTOM_INSTANCE,
        minimum_coverage=1.0,
        maximum_abstention_fraction=0.0,
        minimum_recall=1.0,
        minimum_specificity=1.0,
    )


def _primary_unit_id(
    *,
    seed: int,
    control_id: str,
    boundary: str,
    state_geometry_warp: str,
    structured_observation_perturbation: str,
) -> str:
    return (
        f"unit-s{seed}-{control_id}-b-{boundary}-"
        f"sgw-{state_geometry_warp}-sop-{structured_observation_perturbation}"
    )


def build_closed_d0_d5_selection_protocol(
    *,
    engine: EngineBinding,
    registry: RegistryBinding,
    selection_seeds: tuple[int, ...],
    preseed_readiness: PreseedReadinessBinding | None = None,
) -> QualificationProtocol:
    """Build the reviewed profile for explicit development or official use.

    Supplying seeds directly is a development constructor.  A protocol enters
    the official workflow only when ``preseed_readiness`` came from a strict
    load of the earlier no-overwrite artifact and official validation is
    requested.
    """

    if not isinstance(engine, EngineBinding):
        raise TypeError("engine must be an EngineBinding")
    if not isinstance(registry, RegistryBinding):
        raise TypeError("registry must be a RegistryBinding")
    if preseed_readiness is not None and not isinstance(
        preseed_readiness,
        PreseedReadinessBinding,
    ):
        raise TypeError("preseed_readiness must be a PreseedReadinessBinding or None")
    if type(selection_seeds) is not tuple:
        raise TypeError("selection_seeds must be an immutable tuple")
    if len(selection_seeds) != CLOSED_D0_D5_SELECTION_SEED_COUNT:
        raise QualificationContractError(
            "closed D0-D5 selection requires exactly two caller-attested unopened seeds"
        )
    excluded = tuple(
        seed
        for seed in selection_seeds
        if seed in CLOSED_D0_D5_KNOWN_SEED_EXCLUSION_REGISTRY.seeds
    )
    if excluded:
        raise QualificationContractError(
            "selection seeds intersect the canonical known-seed exclusion "
            f"registry: {excluded}; absence from this registry still requires "
            "external unopened-seed attestation"
        )

    controls = _controls()
    graphs = closed_d0_d5_graph_axes()
    stress_axes = closed_d0_d5_stress_axes()
    selection = SelectionDesign(
        seeds=selection_seeds,
        controls=controls,
        stress_axes=stress_axes,
    )
    core_cells: list[ExpectedCoreCell] = []
    loop_cells: list[ExpectedCell] = []
    memberships: dict[str, set[str]] = {
        required_stress_stratum_id(axis.axis_id, level): set()
        for axis in stress_axes
        for level in axis.levels
    }

    for seed, control, boundary, state_geometry_warp, perturbation in product(
        selection.seeds,
        controls,
        stress_axes[0].levels,
        stress_axes[1].levels,
        stress_axes[2].levels,
    ):
        primary_id = _primary_unit_id(
            seed=seed,
            control_id=control.control_id,
            boundary=boundary,
            state_geometry_warp=state_geometry_warp,
            structured_observation_perturbation=perturbation,
        )
        assignments = (
            StressAssignment(BOUNDARY_AXIS_ID, boundary),
            StressAssignment(STATE_GEOMETRY_WARP_AXIS_ID, state_geometry_warp),
            StressAssignment(
                STRUCTURED_OBSERVATION_PERTURBATION_AXIS_ID,
                perturbation,
            ),
        )
        stratum_ids = tuple(
            required_stress_stratum_id(item.axis_id, item.level) for item in assignments
        )
        for stratum_id in stratum_ids:
            memberships[stratum_id].add(primary_id)
        for a_graph in graphs.field_estimation:
            core_cells.append(
                ExpectedCoreCell(
                    core_cell_id=f"core-{primary_id}-{a_graph.graph_id}",
                    primary_unit_id=primary_id,
                    selection_seed=seed,
                    control_id=control.control_id,
                    stress_assignments=assignments,
                    field_graph_id=a_graph.graph_id,
                    expected_core_disposition=control.core_disposition,
                )
            )
            for b_graph in graphs.cycle_construction:
                for role in LoopRole:
                    expected_loop = (
                        control.loop_disposition
                        if role is LoopRole.PRIMARY_BOUNDARY
                        else (
                            LoopDisposition.PREREQUISITE_FAILURE
                            if control.loop_disposition
                            is LoopDisposition.PREREQUISITE_FAILURE
                            else LoopDisposition.NULL
                        )
                    )
                    loop_cells.append(
                        ExpectedCell(
                            cell_id=(
                                f"loop-{primary_id}-{a_graph.graph_id}-"
                                f"{b_graph.graph_id}-{role.value}"
                            ),
                            primary_unit_id=primary_id,
                            selection_seed=seed,
                            control_id=control.control_id,
                            stress_assignments=assignments,
                            field_graph_id=a_graph.graph_id,
                            cycle_graph_id=b_graph.graph_id,
                            loop_role=role,
                            expected_loop_disposition=expected_loop,
                            stratum_ids=stratum_ids,
                        )
                    )

    expected_strata = tuple(
        ExpectedStratum(
            stratum_id=stratum_id,
            evaluation_unit=EvaluationUnit.PHANTOM_INSTANCE,
            required=True,
            primary_unit_ids=tuple(sorted(primary_ids)),
        )
        for stratum_id, primary_ids in sorted(memberships.items())
    )
    protocol = QualificationProtocol(
        protocol_id=CLOSED_D0_D5_PROTOCOL_ID,
        engine=engine,
        registry=registry,
        instrument=_instrument(),
        implementation_registry=_implementation_registry(),
        graphs=graphs,
        domain=DomainDeclaration(
            domain_id="cartesian-grid-v0-1",
            domain_construction_sha256=domain_construction_sha256(),
            support_id="rectangular-face-support-v0-1",
            support_construction_sha256=support_construction_sha256(),
            boundary_class_id="same-induced-boundary-v0-1",
            refinement_rule_id="forward-span-four-v0-1",
            max_domain_edges_per_graph_edge=4,
        ),
        cartesian=closed_d0_d5_cartesian_substrate(),
        selection=selection,
        preseed_readiness=preseed_readiness,
        thresholds=closed_d0_d5_thresholds(),
        coverage_policy=closed_d0_d5_coverage_policy(),
        expected_core_cells=tuple(
            sorted(core_cells, key=lambda item: item.core_cell_id)
        ),
        expected_cells=tuple(sorted(loop_cells, key=lambda item: item.cell_id)),
        expected_strata=expected_strata,
        authority=AuthorityBoundary(),
    )
    primary_ids = {cell.primary_unit_id for cell in protocol.expected_core_cells}
    if (
        len(primary_ids) != CLOSED_D0_D5_PRIMARY_UNIT_COUNT
        or len(protocol.expected_core_cells) != 192
        or len(protocol.expected_cells) != 1152
    ):
        raise QualificationContractError(
            "closed D0-D5 factory did not produce its exact 64-primary "
            "3A-by-3B-by-2-role manifest"
        )
    return protocol


def validate_closed_d0_d5_selection_protocol(
    protocol: QualificationProtocol,
    *,
    require_persisted_preseed_readiness: bool = False,
) -> QualificationProtocol:
    """Require exact equality with the canonical factory reconstruction.

    The engine binding, registry binding, and caller-attested seed tuple are
    the only variable inputs.  Every other protocol byte is reconstructed by
    this module and compared exactly, so a self-consistent generic protocol
    mutation cannot enter the official D0--D5 runner.
    """

    if not isinstance(protocol, QualificationProtocol):
        raise TypeError("protocol must be a QualificationProtocol")
    expected = build_closed_d0_d5_selection_protocol(
        engine=protocol.engine,
        registry=protocol.registry,
        selection_seeds=protocol.selection.seeds,
        preseed_readiness=protocol.preseed_readiness,
    )
    if protocol.canonical_bytes != expected.canonical_bytes:
        raise QualificationContractError(
            "qualification protocol differs from the exact closed D0-D5 "
            f"factory profile {CLOSED_D0_D5_PROTOCOL_FACTORY_ID}"
        )
    if require_persisted_preseed_readiness:
        if (
            tuple(item.repository_path for item in protocol.engine.official_executables)
            != CLOSED_D0_D5_OFFICIAL_EXECUTABLE_PATHS
        ):
            raise QualificationContractError(
                "official closed D0-D5 protocol must bind the exact official "
                "prepare/launch/run executable closure"
            )
        load_protocol_preseed_readiness_artifact(protocol)
    return protocol


def load_protocol_preseed_readiness_artifact(
    protocol: QualificationProtocol,
) -> LoadedClosedD0D5PreseedReadinessArtifact:
    """Load and join the durable earlier artifact required by official paths."""

    if not isinstance(protocol, QualificationProtocol):
        raise TypeError("protocol must be a QualificationProtocol")
    binding = protocol.preseed_readiness
    if binding is None:
        raise QualificationContractError(
            "official closed D0-D5 protocol lacks a durable preseed readiness binding"
        )
    loaded = load_closed_d0_d5_preseed_readiness_artifact(
        binding.artifact_path,
        expected_source_sha256=binding.artifact_source_sha256,
        expected_canonical_sha256=binding.artifact_canonical_sha256,
    )
    if loaded.binding != binding:
        raise QualificationContractError(
            "loaded preseed readiness artifact differs from the protocol binding"
        )
    if (
        loaded.artifact.source_readiness.engine_commit != protocol.engine.commit
        or loaded.artifact.source_readiness.registry_source_sha256
        != protocol.registry.registry_source_sha256
        or loaded.artifact.source_readiness.registry_canonical_sha256
        != protocol.registry.registry_canonical_sha256
        or loaded.artifact.source_readiness.referent_canonical_sha256
        != protocol.registry.referent_canonical_sha256
    ):
        raise QualificationContractError(
            "loaded preseed readiness source identities differ from the protocol"
        )
    return loaded


def _repository_input_path(
    repository_root: str | Path,
    path: str | Path,
) -> Path:
    try:
        root = Path(repository_root).resolve(strict=True)
    except OSError as error:
        raise QualificationSourceBindingError(
            "repository_root must resolve before seed-free readiness"
        ) from error
    value = Path(path)
    candidate = value if value.is_absolute() else root / value
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as error:
        raise QualificationSourceBindingError(
            "readiness source paths must resolve inside repository_root"
        ) from error
    return resolved


def verify_closed_d0_d5_preseed_source_readiness(
    *,
    engine_commit: str,
    repository_root: str | Path,
    registry_path: str | Path,
    referent_path: str | Path,
) -> QualificationSourceBindingReceipt:
    """Prove the seed-free source prerequisites for canonical preparation.

    The strict P0 registry is loaded first and the canonical F0--F4 referent is
    reconstructed in memory.  The checked-in referent must equal that exact
    reconstruction.  The complete current engine closure is then bound and
    the existing Git verifier proves the declared commit, clean HEAD bytes,
    registry, and referent join.  No seed supplier is accepted by this API.
    """

    registry_input = _repository_input_path(repository_root, registry_path)
    referent_input = _repository_input_path(repository_root, referent_path)
    try:
        loaded_registry = load_hypothesis_registry(registry_input)
        expected_referents = canonical_f0_f4_referent_contracts(
            loaded_registry.canonical_sha256
        )
        loaded_referents = load_referent_contract_set(
            referent_input,
            expected_source_sha256=expected_referents.canonical_sha256,
            expected_canonical_sha256=expected_referents.canonical_sha256,
        )
    except Exception as error:
        raise QualificationSourceBindingError(
            "seed-free canonical registry/referent readiness verification failed"
        ) from error
    if loaded_referents.contract_set != expected_referents:
        raise QualificationSourceBindingError(
            "checked-in referent differs from the in-memory canonical "
            "registry-derived referent"
        )

    registry = RegistryBinding(
        registry_source_sha256=loaded_registry.source_sha256,
        registry_canonical_sha256=loaded_registry.canonical_sha256,
        referent_canonical_sha256=expected_referents.canonical_sha256,
    )
    try:
        engine = build_current_qualification_engine_binding(
            engine_commit=engine_commit,
            repository_root=repository_root,
        )
    except Exception as error:
        raise QualificationSourceBindingError(
            "seed-free current engine-closure binding failed"
        ) from error
    return verify_source_binding(
        engine=engine,
        registry=registry,
        repository_root=repository_root,
        registry_path=registry_path,
        referent_path=referent_path,
    )


def prepare_closed_d0_d5_selection_protocol(
    *,
    engine_commit: str,
    repository_root: str | Path,
    registry_path: str | Path,
    referent_path: str | Path,
    preseed_readiness_path: str | Path,
    selection_seed_supplier: Callable[[], tuple[int, ...]],
) -> tuple[QualificationProtocol, QualificationSourceBindingReceipt]:
    """Open a seed supplier only after the seed-free readiness receipt exists.

    The returned source receipt has a canonical digest suitable for a later
    persisted preparation join.  It proves source readiness, not seed novelty:
    seeds absent from the finite exclusion registry still require external
    process attestation that they and their outcomes were unopened.
    """

    if not callable(selection_seed_supplier):
        raise TypeError("selection_seed_supplier must be callable")
    receipt = verify_closed_d0_d5_preseed_source_readiness(
        engine_commit=engine_commit,
        repository_root=repository_root,
        registry_path=registry_path,
        referent_path=referent_path,
    )
    loaded_preseed = publish_closed_d0_d5_preseed_readiness_artifact(
        preseed_readiness_path,
        repository_root=repository_root,
        registry_path=registry_path,
        referent_path=referent_path,
        source_readiness_receipt=receipt,
    )
    selection_seeds = selection_seed_supplier()
    protocol = build_closed_d0_d5_selection_protocol(
        engine=receipt.engine,
        registry=receipt.registry,
        selection_seeds=selection_seeds,
        preseed_readiness=loaded_preseed.binding,
    )
    validate_closed_d0_d5_selection_protocol(
        protocol,
        require_persisted_preseed_readiness=True,
    )
    return protocol, receipt
