"""Source-selected, uninvoked seed supplier candidate for D7 v1.

This module fixes one fresh v1 module-global OS-CSPRNG supplier, its canonical
identity, and the complete predecessor/parent/development exclusion registry.
It never invokes the supplier, generates seed values, creates a claim or
inventory, writes files, enters an official callable, or grants authority.

The pure derivation core accepts only source objects already rejoined by the
materialization verifier.  It repeats the source join without requiring
``HEAD == S`` so it is safe during commit-A/commit-B verification.  The
clean-source convenience builder separately rebuilds the PR50/PR51 candidates
and retains their exact-clean-HEAD boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import inspect
import secrets
from types import FunctionType
from typing import TYPE_CHECKING, ClassVar

from spirallens import _repository_context as repository_context_module
from spirallens._repository_context import RepositoryContext
from spirallens.core.canonical import canonical_json_bytes, sha256_bytes

from .common import QualificationContractError, require_sha256, require_slug
from . import confirmation_execution_design as execution_design
from . import confirmation_v1_materialization as materialization
from . import confirmation_v1_records as records

if TYPE_CHECKING:
    from .confirmation_v1_deterministic_inputs import (
        D7V1DeterministicInputContractCandidate,
    )

__all__: tuple[str, ...] = ()


_MODULE_PATH = (
    "src/spirallens/qualification/confirmation_v1_source_selected_supplier.py"
)
_REPOSITORY_CONTEXT_MODULE_PATH = "src/spirallens/_repository_context.py"
_EXECUTION_DESIGN_MODULE_PATH = (
    "src/spirallens/qualification/confirmation_execution_design.py"
)
_APPROVED_DESIGN_SYMBOL = "build_seed_free_d7_confirmation_execution_design"
_SUPPLIER_FUNCTION_NAME = "_supply_d7_v1_official_seed_values"
_SUPPLIER_IDENTITY_SCHEMA = (
    "spirallens.d7-v1-source-selected-seed-supplier-identity.v0.1"
)
_SUPPLIER_IDENTITY_CONTRACT_ID = "d7-v1-source-selected-seed-supplier-identity-v0-1"
_EXCLUSION_REGISTRY_SCHEMA = "spirallens.d7-v1-combined-seed-exclusion-registry.v0.1"
_EXCLUSION_REGISTRY_CONTRACT_ID = "d7-v1-combined-seed-exclusion-registry-v0-1"
_EXCLUSION_REGISTRY_ROLE = "seed-exclusion-registry"
_SUPPLIER_ID_PREFIX = "d7-v1-source-selected-os-csprng"
_MAX_SUPPLIER_DRAWS = 256
_MAX_SIGNED_INT64 = 2**63 - 1
_EXPECTED_SEED_SLOT_IDS = (
    "confirmation-seed-slot-00",
    "confirmation-seed-slot-01",
)
_EXPECTED_PREDECESSOR_SEED_VALUES = (
    6721142749694866469,
    6838919520062855071,
)
_EXPECTED_PARENT_SELECTION_SEED_VALUES = (
    1111097936516803550,
    6819071872908675098,
)
_EXPECTED_DEVELOPMENT_EXCLUSION_ENTRIES = (
    (11, "spectral generator family-identity development test"),
    (12, "spectral generator family-identity development test"),
    (9001, "spectral confirmation crossed-path development test"),
    (9002, "spectral confirmation full-inventory development test"),
)
_EXPECTED_DESIGN_DEVELOPMENT_REGISTRY_SHA256 = (
    "20803b40c5fc6903e1d1a64ae41c0eb3dcbb3c4a859d7a482971088346fcb54a"
)
_EXPECTED_EXCLUDED_SEED_VALUES = tuple(
    sorted(
        (
            *_EXPECTED_PREDECESSOR_SEED_VALUES,
            *_EXPECTED_PARENT_SELECTION_SEED_VALUES,
            *(seed for seed, _reason in _EXPECTED_DEVELOPMENT_EXCLUSION_ENTRIES),
        )
    )
)
_CANDIDATE_FACTORY_TOKEN = object()


def _supply_d7_v1_official_seed_values() -> tuple[int, int]:
    """Return two exclusion-clean values when a later chronology invokes it."""

    values: set[int] = set()
    for _attempt in range(_MAX_SUPPLIER_DRAWS):
        value = secrets.randbits(63)
        if (
            type(value) is int
            and 0 <= value <= _MAX_SIGNED_INT64
            and value not in _EXPECTED_EXCLUDED_SEED_VALUES
        ):
            values.add(value)
        if len(values) == 2:
            first, second = sorted(values)
            return first, second
    raise QualificationContractError(
        "fixed D7 v1 OS-CSPRNG supplier did not produce two valid values"
    )


_FIXED_SUPPLIER = _supply_d7_v1_official_seed_values


@dataclass(frozen=True, slots=True)
class D7V1SourceSelectedSeedSupplierCandidate:
    """Exact in-memory supplier binding with no invocation or seed values."""

    source_commit: str
    c1_binding: records.D7V1ArtifactBinding
    c2_binding: records.D7V1ArtifactBinding
    seed_slot_ids: tuple[str, str]
    supplier_id: str
    supplier_identity_source: bytes
    supplier_identity_binding: records.D7V1ArtifactBinding
    exclusion_registry_source: bytes
    exclusion_registry_binding: records.D7V1ArtifactBinding
    excluded_seed_values: tuple[int, ...]
    _factory_token: object = field(default=None, repr=False, compare=False)

    structural_only: ClassVar[bool] = True
    source_join_reverified: ClassVar[bool] = True
    executing_source_members_reauthenticated: ClassVar[bool] = True
    deterministic_input_declarations_rederived: ClassVar[bool] = True
    supplier_source_selected: ClassVar[bool] = True
    supplier_function_fixed: ClassVar[bool] = True
    supplier_identity_derived: ClassVar[bool] = True
    supplier_identity_bytes_present: ClassVar[bool] = True
    exclusion_registry_derived: ClassVar[bool] = True
    seed_cardinality_policy_fixed: ClassVar[bool] = True
    seed_slot_policy_fixed: ClassVar[bool] = True
    full_exclusion_policy_closed: ClassVar[bool] = True

    source_reviewed: ClassVar[bool] = False
    source_selected: ClassVar[bool] = False
    source_closure_established: ClassVar[bool] = False
    source_tree_authenticated: ClassVar[bool] = False
    runtime_environment_authenticated: ClassVar[bool] = False
    runtime_dependency_closure_verified: ClassVar[bool] = False
    supplier_identity_authenticated: ClassVar[bool] = False
    supplier_invoked: ClassVar[bool] = False
    supplier_invocation_authorized: ClassVar[bool] = False
    cryptographic_unseen_proof: ClassVar[bool] = False
    seed_values_generated: ClassVar[bool] = False
    seed_values_present: ClassVar[bool] = False
    seed_cardinality_authorized: ClassVar[bool] = False
    seed_slot_assignment_authorized: ClassVar[bool] = False
    seed_claim_created: ClassVar[bool] = False
    seed_claim_persisted: ClassVar[bool] = False
    supplier_identity_persisted: ClassVar[bool] = False
    exclusion_registry_persisted: ClassVar[bool] = False
    official_seed_inventory_created: ClassVar[bool] = False
    official_seed_inventory_persisted: ClassVar[bool] = False
    six_full_design_bindings_resolved: ClassVar[bool] = False
    external_bindings_authenticated: ClassVar[bool] = False
    full_design_created: ClassVar[bool] = False
    full_design_frozen: ClassVar[bool] = False
    chronology_orchestrated: ClassVar[bool] = False
    chronology_receipt_created: ClassVar[bool] = False
    chronology_receipt_persisted: ClassVar[bool] = False
    external_store_observed: ClassVar[bool] = False
    external_namespace_reserved: ClassVar[bool] = False
    materialization_authorized: ClassVar[bool] = False
    materialized: ClassVar[bool] = False
    publication_authorized: ClassVar[bool] = False
    artifacts_published: ClassVar[bool] = False
    artifact_commit_a_created: ClassVar[bool] = False
    artifact_commit_a_verified: ClassVar[bool] = False
    result_commit_b_created: ClassVar[bool] = False
    result_commit_b_verified: ClassVar[bool] = False
    authority_granted: ClassVar[bool] = False
    official_callable_invoked: ClassVar[bool] = False
    execution_authorized: ClassVar[bool] = False
    execution_started: ClassVar[bool] = False
    result_produced: ClassVar[bool] = False
    scientific_claim_eligible: ClassVar[bool] = False

    def __post_init__(self) -> None:
        if self._factory_token is not _CANDIDATE_FACTORY_TOKEN:
            raise QualificationContractError(
                "source-selected supplier candidate must be factory-produced"
            )
        materialization._full_commit(self.source_commit, label="source_commit")
        for value, role, label in (
            (
                self.c1_binding,
                records.D7V1C1SourceSetRecord.artifact_role,
                "C1 binding",
            ),
            (
                self.c2_binding,
                records.D7V1C2SourceClosureReceipt.artifact_role,
                "C2 binding",
            ),
            (
                self.supplier_identity_binding,
                "supplier-identity",
                "supplier identity binding",
            ),
            (
                self.exclusion_registry_binding,
                _EXCLUSION_REGISTRY_ROLE,
                "exclusion registry binding",
            ),
        ):
            if not isinstance(value, records.D7V1ArtifactBinding):
                raise TypeError(f"{label} must be D7V1ArtifactBinding")
            if value.artifact_role != role:
                raise QualificationContractError(f"{label} role differs")
        if self.seed_slot_ids != _EXPECTED_SEED_SLOT_IDS:
            raise QualificationContractError("seed slot identifiers differ")
        if self.excluded_seed_values != _EXPECTED_EXCLUDED_SEED_VALUES:
            raise QualificationContractError("combined excluded seed values differ")
        if (
            type(self.supplier_identity_source) is not bytes
            or type(self.exclusion_registry_source) is not bytes
        ):
            raise TypeError("candidate canonical sources must be bytes")
        for source, binding, schema, label in (
            (
                self.supplier_identity_source,
                self.supplier_identity_binding,
                _SUPPLIER_IDENTITY_SCHEMA,
                "supplier identity",
            ),
            (
                self.exclusion_registry_source,
                self.exclusion_registry_binding,
                _EXCLUSION_REGISTRY_SCHEMA,
                "exclusion registry",
            ),
        ):
            if (
                not source
                or binding.artifact_contract_id != schema
                or binding.byte_count != len(source)
                or binding.canonical_sha256 != sha256_bytes(source)
            ):
                raise QualificationContractError(f"{label} binding differs")

    @property
    def required_seed_count(self) -> int:
        return len(self.seed_slot_ids)


def _require_import_origins(repository: RepositoryContext) -> None:
    for imported_file, repository_path, label in (
        (__file__, _MODULE_PATH, "source-selected supplier module"),
        (
            repository_context_module.__file__,
            _REPOSITORY_CONTEXT_MODULE_PATH,
            "repository-context module",
        ),
        (
            execution_design.__file__,
            _EXECUTION_DESIGN_MODULE_PATH,
            "execution-design module",
        ),
    ):
        try:
            matches = (repository.root / repository_path).samefile(imported_file)
        except (OSError, TypeError, ValueError):
            matches = False
        if not matches:
            raise QualificationContractError(
                f"{label} import origin differs from repository"
            )


def _require_exact_source_member(
    repository: RepositoryContext,
    *,
    source_commit: str,
    c1: records.D7V1C1SourceSetRecord,
    repository_path: str,
) -> records.D7V1SourceMember:
    matches = tuple(
        member
        for member in materialization._source_members_from_c1(c1)
        if member.repository_path == repository_path
    )
    if len(matches) != 1:
        raise QualificationContractError(
            f"C1 must bind exactly one executing source member: {repository_path}"
        )
    member = matches[0]
    mode, committed = materialization._git_blob(
        repository,
        source_commit,
        repository_path,
        maximum_bytes=materialization._MAX_SOURCE_MEMBER_BYTES,
    )
    live = materialization._safe_read_file(
        repository.root / repository_path,
        materialization._MAX_SOURCE_MEMBER_BYTES,
        require_single_link=False,
    )
    if (
        member.git_mode != mode
        or member.byte_count != len(committed)
        or member.sha256 != sha256_bytes(committed)
        or live != committed
    ):
        raise QualificationContractError(
            f"executing source differs from Git S or C1: {repository_path}"
        )
    return member


def _require_approved_design_source(
    repository: RepositoryContext,
    *,
    protocol: materialization.D7V1MaterializationProtocol,
    source_commit: str,
    c1: records.D7V1C1SourceSetRecord,
) -> records.D7V1SourceMember:
    source_contract = materialization._mapping(
        protocol.document.get("source_contract"),
        label="source_contract",
    )
    entries = materialization._sequence(
        source_contract.get("approved_exact_function_runtime_reuse"),
        label="approved_exact_function_runtime_reuse",
    )
    approved = tuple(
        materialization._mapping(item, label="approved execution-design reuse")
        for item in entries
        if type(item) is dict and item.get("allowed_symbol") == _APPROVED_DESIGN_SYMBOL
    )
    if len(approved) != 1:
        raise QualificationContractError(
            "approved execution-design runtime source is not exact"
        )
    entry = approved[0]
    if set(entry) != {
        "allowed_symbol",
        "authority_transfer_allowed",
        "future_c1_must_bind_transitive_dependency_closure",
        "persistence_transfer_allowed",
        "repository_path",
        "reuse_scope",
        "runtime_purpose",
        "schema_transfer_allowed",
        "source_commit",
        "source_sha256",
    }:
        raise QualificationContractError(
            "approved execution-design source contract keys differ"
        )
    if (
        entry.get("repository_path") != _EXECUTION_DESIGN_MODULE_PATH
        or entry.get("reuse_scope") != "runtime_function_only"
        or entry.get("runtime_purpose")
        != "fresh_five_parent_seed_free_scientific_projection_only"
        or entry.get("future_c1_must_bind_transitive_dependency_closure") is not True
        or entry.get("authority_transfer_allowed") is not False
        or entry.get("persistence_transfer_allowed") is not False
        or entry.get("schema_transfer_allowed") is not False
    ):
        raise QualificationContractError(
            "approved execution-design source contract differs"
        )
    approved_commit = materialization._resolve_commit(
        repository,
        materialization._string(
            entry.get("source_commit"),
            label="approved execution-design source_commit",
        ),
        label="approved execution-design source_commit",
    )
    if not materialization._is_ancestor(
        repository,
        approved_commit,
        source_commit,
    ):
        raise QualificationContractError(
            "approved execution-design source is not an ancestor of source S"
        )
    expected_sha256 = require_sha256(
        entry.get("source_sha256"),
        label="approved execution-design source_sha256",
    )
    _mode, approved_source = materialization._git_blob(
        repository,
        approved_commit,
        _EXECUTION_DESIGN_MODULE_PATH,
        maximum_bytes=materialization._MAX_SOURCE_MEMBER_BYTES,
    )
    current_member = _require_exact_source_member(
        repository,
        source_commit=source_commit,
        c1=c1,
        repository_path=_EXECUTION_DESIGN_MODULE_PATH,
    )
    if (
        sha256_bytes(approved_source) != expected_sha256
        or current_member.sha256 != expected_sha256
    ):
        raise QualificationContractError(
            "execution-design source differs from its approved exact digest"
        )
    approved_function = getattr(execution_design, _APPROVED_DESIGN_SYMBOL, None)
    if (
        type(approved_function) is not FunctionType
        or approved_function.__module__ != execution_design.__name__
        or approved_function.__qualname__ != _APPROVED_DESIGN_SYMBOL
    ):
        raise QualificationContractError(
            "approved execution-design function identity differs"
        )
    return current_member


def _fixed_callable_contract() -> dict[str, object]:
    candidate = globals().get(_SUPPLIER_FUNCTION_NAME)
    if type(candidate) is not FunctionType or candidate is not _FIXED_SUPPLIER:
        raise QualificationContractError("fixed D7 v1 supplier identity differs")
    code = candidate.__code__
    if (
        candidate.__module__ != __name__
        or candidate.__qualname__ != _SUPPLIER_FUNCTION_NAME
        or code.co_argcount != 0
        or code.co_posonlyargcount != 0
        or code.co_kwonlyargcount != 0
        or code.co_flags & (inspect.CO_VARARGS | inspect.CO_VARKEYWORDS)
        or candidate.__defaults__ is not None
        or candidate.__kwdefaults__ is not None
        or candidate.__closure__ is not None
    ):
        raise QualificationContractError("fixed D7 v1 supplier contract differs")
    return {
        "function_type": "types.FunctionType",
        "module": __name__,
        "qualname": _SUPPLIER_FUNCTION_NAME,
        "module_global_fixed": True,
        "positional_parameter_count": 0,
        "positional_only_parameter_count": 0,
        "keyword_only_parameter_count": 0,
        "varargs_present": False,
        "varkw_present": False,
        "defaults_present": False,
        "keyword_defaults_present": False,
        "closure_present": False,
    }


def _seed_slots_and_supplier_role(
    protocol: materialization.D7V1MaterializationProtocol,
) -> tuple[tuple[str, str], str]:
    future = materialization._mapping(
        protocol.document.get("future_authoritative_verification_contract"),
        label="future_authoritative_verification_contract",
    )
    joins = materialization._mapping(
        future.get("cross_record_join_requirements"),
        label="cross_record_join_requirements",
    )
    claim = materialization._mapping(
        joins.get("exclusive_seed_claim"),
        label="exclusive_seed_claim",
    )
    supplier_role = materialization._string(
        claim.get("supplier_identity_role"),
        label="supplier_identity_role",
    )
    if supplier_role != "supplier-identity":
        raise QualificationContractError("frozen supplier identity role differs")
    return _EXPECTED_SEED_SLOT_IDS, supplier_role


def _development_exclusion_entries() -> tuple[tuple[int, str], ...]:
    source_document = {
        "schema_version": "spirallens.d7-development-seed-exclusion.v0.1",
        "entries": [
            {"seed": seed, "reason": reason}
            for seed, reason in _EXPECTED_DEVELOPMENT_EXCLUSION_ENTRIES
        ],
    }
    observed_sha256 = sha256_bytes(canonical_json_bytes(source_document))
    if observed_sha256 != _EXPECTED_DESIGN_DEVELOPMENT_REGISTRY_SHA256:
        raise QualificationContractError(
            "reviewed development exclusion registry digest differs"
        )
    return _EXPECTED_DEVELOPMENT_EXCLUSION_ENTRIES


def _parent_selection_seed_values(
    historical_sources: dict[str, bytes],
) -> tuple[int, int]:
    parent = materialization._parse_canonical_mapping(
        historical_sources["parent-protocol"],
        label="parent protocol seed policy",
    )
    selection = materialization._mapping(
        parent.get("selection"),
        label="parent protocol selection",
    )
    if set(selection) != {"controls", "seeds", "stress_axes"}:
        raise QualificationContractError("parent selection fields differ")
    observed = tuple(
        materialization._plain_int(item, label="parent selection seed", minimum=0)
        for item in materialization._sequence(
            selection.get("seeds"),
            label="parent selection seeds",
        )
    )
    if (
        observed != _EXPECTED_PARENT_SELECTION_SEED_VALUES
        or observed != tuple(sorted(observed))
        or len(set(observed)) != 2
        or any(value > _MAX_SIGNED_INT64 for value in observed)
    ):
        raise QualificationContractError("parent selection seed values differ")
    return observed


def _binding_for_source(
    *,
    artifact_role: str,
    artifact_contract_id: str,
    source: bytes,
) -> records.D7V1ArtifactBinding:
    return records.D7V1ArtifactBinding(
        artifact_role=artifact_role,
        artifact_contract_id=artifact_contract_id,
        canonical_sha256=sha256_bytes(source),
        byte_count=len(source),
    )


def _derive_d7_v1_source_selected_seed_supplier_candidate(
    repository: RepositoryContext,
    *,
    protocol: materialization.D7V1MaterializationProtocol,
    source_commit: str,
    c1: records.D7V1C1SourceSetRecord,
    c2: records.D7V1C2SourceClosureReceipt,
) -> D7V1SourceSelectedSeedSupplierCandidate:
    """Derive from an exact S/C1/C2 join without requiring ``HEAD == S``."""

    if not isinstance(repository, RepositoryContext):
        raise TypeError("repository must be RepositoryContext")
    if not isinstance(protocol, materialization.D7V1MaterializationProtocol):
        raise TypeError("protocol must be D7V1MaterializationProtocol")
    if not isinstance(c1, records.D7V1C1SourceSetRecord):
        raise TypeError("c1 must be D7V1C1SourceSetRecord")
    if not isinstance(c2, records.D7V1C2SourceClosureReceipt):
        raise TypeError("c2 must be D7V1C2SourceClosureReceipt")
    source = materialization._full_commit(source_commit, label="source_commit")
    _require_import_origins(repository)
    if materialization._verify_source_join(repository, protocol, c1, c2) != source:
        raise QualificationContractError(
            "source-selected supplier source rejoin returned a different commit"
        )

    supplier_member = _require_exact_source_member(
        repository,
        source_commit=source,
        c1=c1,
        repository_path=_MODULE_PATH,
    )
    design_member = _require_approved_design_source(
        repository,
        protocol=protocol,
        source_commit=source,
        c1=c1,
    )
    seed_slot_ids, supplier_role = _seed_slots_and_supplier_role(protocol)
    callable_contract = _fixed_callable_contract()

    predecessor_binding, predecessor_values = materialization._negative_seed_binding(
        repository,
        protocol,
    )
    if (
        predecessor_values != _EXPECTED_PREDECESSOR_SEED_VALUES
        or predecessor_values != tuple(sorted(predecessor_values))
        or len(set(predecessor_values)) != 2
    ):
        raise QualificationContractError("predecessor seed values differ")
    historical_sources, historical_bindings = (
        materialization._historical_sources_and_bindings(repository, protocol)
    )
    parent_values = _parent_selection_seed_values(historical_sources)
    parent_binding = historical_bindings.get("parent-protocol")
    if not isinstance(parent_binding, records.D7V1ArtifactBinding):
        raise QualificationContractError("parent protocol binding is absent")
    development_entries = _development_exclusion_entries()
    category_sets = (
        set(predecessor_values),
        set(parent_values),
        {seed for seed, _reason in development_entries},
    )
    if any(
        category_sets[left] & category_sets[right]
        for left in range(len(category_sets))
        for right in range(left + 1, len(category_sets))
    ):
        raise QualificationContractError("seed exclusion categories overlap")
    excluded_values = tuple(sorted(set().union(*category_sets)))
    if excluded_values != _EXPECTED_EXCLUDED_SEED_VALUES:
        raise QualificationContractError("combined seed exclusion values differ")

    c1_binding = materialization._record_binding(c1)
    c2_binding = materialization._record_binding(c2)
    protocol_binding = materialization._protocol_binding(protocol)
    route_source, route_document = materialization._route_source(repository, protocol)
    route_binding = records.D7V1ArtifactBinding(
        artifact_role=materialization._ROUTE_ROLE,
        artifact_contract_id=materialization._string(
            route_document.get("schema_version"),
            label="route schema_version",
        ),
        canonical_sha256=sha256_bytes(route_source),
        byte_count=len(route_source),
    )
    lineage_id = materialization._string(
        protocol.document.get("successor_lineage_id"),
        label="successor_lineage_id",
    )
    if lineage_id != "d7-spectral-moment-confirmation-v1":
        raise QualificationContractError("successor lineage differs")

    exclusion_registry_document = {
        "schema_version": _EXCLUSION_REGISTRY_SCHEMA,
        "contract_id": _EXCLUSION_REGISTRY_CONTRACT_ID,
        "artifact_role": _EXCLUSION_REGISTRY_ROLE,
        "successor_lineage_id": lineage_id,
        "source_commit": source,
        "predecessor_inventory": {
            "binding": predecessor_binding.to_dict(),
            "seed_values": list(predecessor_values),
        },
        "parent_selection": {
            "binding": parent_binding.to_dict(),
            "seed_values": list(parent_values),
        },
        "development": {
            "approved_design_source_member": design_member.to_dict(),
            "source_registry_schema": ("spirallens.d7-development-seed-exclusion.v0.1"),
            "source_registry_sha256": (_EXPECTED_DESIGN_DEVELOPMENT_REGISTRY_SHA256),
            "entries": [
                {"seed": seed, "reason": reason} for seed, reason in development_entries
            ],
        },
        "combined_seed_values": list(excluded_values),
        "policy": {
            "categories_pairwise_disjoint": True,
            "combined_values_sorted_unique": True,
            "successor_values_must_exclude_all_combined_values": True,
            "registry_persisted": False,
            "registry_is_execution_authority": False,
        },
    }
    exclusion_registry_source = canonical_json_bytes(exclusion_registry_document)
    materialization._parse_canonical_mapping(
        exclusion_registry_source,
        label="source-selected combined seed exclusion registry",
    )
    exclusion_registry_binding = _binding_for_source(
        artifact_role=_EXCLUSION_REGISTRY_ROLE,
        artifact_contract_id=_EXCLUSION_REGISTRY_SCHEMA,
        source=exclusion_registry_source,
    )

    identity_core = {
        "successor_lineage_id": lineage_id,
        "source_commit": source,
        "c1_binding": c1_binding.to_dict(),
        "c2_binding": c2_binding.to_dict(),
        "materialization_protocol_binding": protocol_binding.to_dict(),
        "route_binding": route_binding.to_dict(),
        "supplier_source_member": supplier_member.to_dict(),
        "approved_design_source_member": design_member.to_dict(),
        "exclusion_registry_binding": exclusion_registry_binding.to_dict(),
        "callable_contract": callable_contract,
        "entropy_contract": {
            "source_declared_api": "secrets.randbits",
            "bit_count_per_draw": 63,
            "operating_system_csprng_required": True,
            "live_entropy_callable_authenticated": False,
            "maximum_draw_count": _MAX_SUPPLIER_DRAWS,
        },
        "output_contract": {
            "container": "tuple",
            "required_seed_count": len(seed_slot_ids),
            "values_nonnegative_signed_int64": True,
            "values_unique": True,
            "values_canonically_sorted_ascending": True,
            "ordinal_slot_assignments": [
                {"ordinal": ordinal, "seed_slot_id": slot_id}
                for ordinal, slot_id in enumerate(seed_slot_ids)
            ],
            "combined_exclusion_registry_required": True,
        },
    }
    supplier_id = require_slug(
        f"{_SUPPLIER_ID_PREFIX}-"
        f"{sha256_bytes(canonical_json_bytes(identity_core))[:24]}",
        label="source-selected supplier_id",
    )
    supplier_identity_document = {
        "schema_version": _SUPPLIER_IDENTITY_SCHEMA,
        "contract_id": _SUPPLIER_IDENTITY_CONTRACT_ID,
        "artifact_role": supplier_role,
        "supplier_id": supplier_id,
        "identity_core": identity_core,
        "observations": {
            "supplier_invoked": False,
            "seed_values_present": False,
            "cryptographic_unseen_proof": False,
            "runtime_environment_authenticated": False,
            "identity_authenticated": False,
        },
        "authority": {
            "supplier_invocation_authorized": False,
            "seed_claim_authorized": False,
            "materialization_authorized": False,
            "execution_authorized": False,
            "scientific_claim_eligible": False,
        },
    }
    supplier_identity_source = canonical_json_bytes(supplier_identity_document)
    materialization._parse_canonical_mapping(
        supplier_identity_source,
        label="source-selected supplier identity",
    )
    supplier_identity_binding = _binding_for_source(
        artifact_role=supplier_role,
        artifact_contract_id=_SUPPLIER_IDENTITY_SCHEMA,
        source=supplier_identity_source,
    )
    result = D7V1SourceSelectedSeedSupplierCandidate(
        source_commit=source,
        c1_binding=c1_binding,
        c2_binding=c2_binding,
        seed_slot_ids=seed_slot_ids,
        supplier_id=supplier_id,
        supplier_identity_source=supplier_identity_source,
        supplier_identity_binding=supplier_identity_binding,
        exclusion_registry_source=exclusion_registry_source,
        exclusion_registry_binding=exclusion_registry_binding,
        excluded_seed_values=excluded_values,
        _factory_token=_CANDIDATE_FACTORY_TOKEN,
    )

    _require_import_origins(repository)
    _require_exact_source_member(
        repository,
        source_commit=source,
        c1=c1,
        repository_path=_MODULE_PATH,
    )
    _require_exact_source_member(
        repository,
        source_commit=source,
        c1=c1,
        repository_path=_EXECUTION_DESIGN_MODULE_PATH,
    )
    if materialization._verify_source_join(repository, protocol, c1, c2) != source:
        raise QualificationContractError(
            "final source-selected supplier source rejoin differs"
        )
    return result


def _require_same_deterministic_inputs(
    supplied: D7V1DeterministicInputContractCandidate,
    rebuilt: D7V1DeterministicInputContractCandidate,
) -> None:
    if (
        supplied.source_commit != rebuilt.source_commit
        or supplied.source_closure.c1.canonical_bytes
        != rebuilt.source_closure.c1.canonical_bytes
        or supplied.source_closure.c2.canonical_bytes
        != rebuilt.source_closure.c2.canonical_bytes
        or supplied.supplier_identity_role != rebuilt.supplier_identity_role
        or supplied.required_seed_count != rebuilt.required_seed_count
        or supplied.seed_slot_ids != rebuilt.seed_slot_ids
        or dict(supplied.full_design_field_roles)
        != dict(rebuilt.full_design_field_roles)
    ):
        raise QualificationContractError(
            "supplied deterministic-input contract differs from its fresh rebuild"
        )


def _build_d7_v1_source_selected_seed_supplier_candidate(
    repository: RepositoryContext,
    *,
    deterministic_inputs: D7V1DeterministicInputContractCandidate,
) -> D7V1SourceSelectedSeedSupplierCandidate:
    """Build the source-selected supplier from the exact clean current S."""

    from . import confirmation_v1_deterministic_inputs as deterministic_inputs_module
    from . import confirmation_v1_source_closure as source_closure_module

    if not isinstance(repository, RepositoryContext):
        raise TypeError("repository must be RepositoryContext")
    if not isinstance(
        deterministic_inputs,
        deterministic_inputs_module.D7V1DeterministicInputContractCandidate,
    ):
        raise TypeError(
            "deterministic_inputs must be D7V1DeterministicInputContractCandidate"
        )
    _require_import_origins(repository)
    rebuilt = (
        deterministic_inputs_module._build_d7_v1_deterministic_input_contract_candidate(
            repository,
            source_closure=deterministic_inputs.source_closure,
        )
    )
    _require_same_deterministic_inputs(deterministic_inputs, rebuilt)
    protocol = materialization._protocol_at_commit(
        repository,
        rebuilt.source_commit,
    )
    result = _derive_d7_v1_source_selected_seed_supplier_candidate(
        repository,
        protocol=protocol,
        source_commit=rebuilt.source_commit,
        c1=rebuilt.source_closure.c1,
        c2=rebuilt.source_closure.c2,
    )
    source_closure_module._require_exact_clean_head(
        repository,
        rebuilt.source_commit,
    )
    return result
