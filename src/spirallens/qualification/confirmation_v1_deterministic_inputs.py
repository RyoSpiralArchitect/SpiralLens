"""Read-only deterministic-input contract candidate for D7 v1.

This module observes only source-closed structural declarations needed before
any external chronology may be implemented: the supplier-identity artifact
role, the seed-slot cardinality and identifiers, and the exact seven
full-design inventory field-to-role entries.  It deliberately does not choose
or describe a supplier, construct artifact bindings, generate seed values,
create records, write files, enter an official callable, or grant authority.

The sole builder accepts an already-constructed source-closure candidate but
does not trust it.  It rebuilds the choice-free C1/C2 candidate from the same
clean current ``HEAD``, requires byte-exact equality, rejoins source S, and
binds this module plus the approved execution-design source to both Git S and
the rebuilt C1 member inventory before returning an in-memory candidate.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import FunctionType, MappingProxyType
from typing import ClassVar

from spirallens import _repository_context as repository_context_module
from spirallens._repository_context import RepositoryContext
from spirallens.core.canonical import sha256_bytes

from .common import QualificationContractError
from . import confirmation_execution_design as execution_design
from . import confirmation_v1_materialization as materialization
from . import confirmation_v1_records as records
from . import confirmation_v1_source_closure as source_closure_module
from .confirmation_v1_source_closure import D7V1SourceClosureCandidate

__all__: tuple[str, ...] = ()


_MODULE_PATH = "src/spirallens/qualification/confirmation_v1_deterministic_inputs.py"
_REPOSITORY_CONTEXT_MODULE_PATH = "src/spirallens/_repository_context.py"
_EXECUTION_DESIGN_MODULE_PATH = (
    "src/spirallens/qualification/confirmation_execution_design.py"
)
_APPROVED_DESIGN_SYMBOL = "build_seed_free_d7_confirmation_execution_design"
_EXPECTED_SUPPLIER_IDENTITY_ROLE = "supplier-identity"
_EXPECTED_SEED_SLOT_IDS = (
    "confirmation-seed-slot-00",
    "confirmation-seed-slot-01",
)
_EXPECTED_FULL_DESIGN_FIELD_ROLES = {
    "admission_binding": "family-admission",
    "family_binding": "confirmation-family",
    "graph_case_stress_aggregation_binding": ("graph-case-stress-aggregation"),
    "inventory_binding": records.D7V1OfficialSeedInventory.artifact_role,
    "lifecycle_binding": "lifecycle",
    "protocol_binding": "confirmation-protocol",
    "source_graph_binding": "source-graph",
}
_CANDIDATE_FACTORY_TOKEN = object()


@dataclass(frozen=True, slots=True)
class D7V1DeterministicInputContractCandidate:
    """Source-rejoined declarations with no supplier, values, or bindings."""

    source_closure: D7V1SourceClosureCandidate
    supplier_identity_role: str
    required_seed_count: int
    seed_slot_ids: tuple[str, str]
    full_design_field_roles: Mapping[str, str]
    _factory_token: object = field(default=None, repr=False, compare=False)

    structural_only: ClassVar[bool] = True
    source_closure_rebuilt: ClassVar[bool] = True
    source_closure_rejoined: ClassVar[bool] = True
    executing_source_members_reauthenticated: ClassVar[bool] = True
    supplier_role_contract_observed: ClassVar[bool] = True
    seed_slot_contract_observed: ClassVar[bool] = True
    full_design_field_role_contract_observed: ClassVar[bool] = True

    source_reviewed: ClassVar[bool] = False
    source_selected: ClassVar[bool] = False
    source_closure_established: ClassVar[bool] = False
    source_tree_authenticated: ClassVar[bool] = False
    runtime_environment_authenticated: ClassVar[bool] = False
    runtime_dependency_closure_verified: ClassVar[bool] = False
    supplier_selected: ClassVar[bool] = False
    supplier_fixed: ClassVar[bool] = False
    supplier_identity_authenticated: ClassVar[bool] = False
    supplier_invoked: ClassVar[bool] = False
    seed_values_present: ClassVar[bool] = False
    seed_claim_created: ClassVar[bool] = False
    seed_claim_persisted: ClassVar[bool] = False
    official_seed_inventory_created: ClassVar[bool] = False
    official_seed_inventory_persisted: ClassVar[bool] = False
    seed_cardinality_authorized: ClassVar[bool] = False
    seed_slot_assignment_authorized: ClassVar[bool] = False
    binding_bytes_present: ClassVar[bool] = False
    binding_resolution_completed: ClassVar[bool] = False
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
                "deterministic-input contract candidate must be produced by "
                "its closed builder"
            )
        if not isinstance(self.source_closure, D7V1SourceClosureCandidate):
            raise TypeError("source_closure must be D7V1SourceClosureCandidate")
        if self.supplier_identity_role != _EXPECTED_SUPPLIER_IDENTITY_ROLE:
            raise QualificationContractError("supplier identity role differs")
        if self.required_seed_count != len(_EXPECTED_SEED_SLOT_IDS):
            raise QualificationContractError("required seed count differs")
        if self.seed_slot_ids != _EXPECTED_SEED_SLOT_IDS:
            raise QualificationContractError("seed slot identifiers differ")
        roles = dict(self.full_design_field_roles)
        if roles != _EXPECTED_FULL_DESIGN_FIELD_ROLES:
            raise QualificationContractError("full-design field-role map differs")
        object.__setattr__(
            self,
            "full_design_field_roles",
            MappingProxyType(dict(sorted(roles.items()))),
        )

    @property
    def source_commit(self) -> str:
        return self.source_closure.source_commit


def _require_import_origins(repository: RepositoryContext) -> None:
    for imported_file, repository_path, label in (
        (__file__, _MODULE_PATH, "deterministic-input module"),
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
    source_closure: D7V1SourceClosureCandidate,
    repository_path: str,
) -> records.D7V1SourceMember:
    matches = tuple(
        member
        for member in source_closure.source_members
        if member.repository_path == repository_path
    )
    if len(matches) != 1:
        raise QualificationContractError(
            f"C1 must bind exactly one executing source member: {repository_path}"
        )
    member = matches[0]
    mode, committed = materialization._git_blob(
        repository,
        source_closure.source_commit,
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


def _require_approved_execution_design_source(
    repository: RepositoryContext,
    protocol: materialization.D7V1MaterializationProtocol,
    source_closure: D7V1SourceClosureCandidate,
) -> None:
    source_contract = materialization._mapping(
        protocol.document.get("source_contract"),
        label="source_contract",
    )
    approved = tuple(
        materialization._mapping(item, label="approved runtime reuse")
        for item in materialization._sequence(
            source_contract.get("approved_exact_function_runtime_reuse"),
            label="approved_exact_function_runtime_reuse",
        )
        if isinstance(item, Mapping)
        and item.get("allowed_symbol") == _APPROVED_DESIGN_SYMBOL
    )
    if len(approved) != 1:
        raise QualificationContractError(
            "approved execution-design runtime source is not exact"
        )
    entry = approved[0]
    expected_keys = {
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
    }
    if set(entry) != expected_keys:
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
        source_closure.source_commit,
    ):
        raise QualificationContractError(
            "approved execution-design source is not an ancestor of source S"
        )
    expected_sha256 = records.require_sha256(
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
        source_closure,
        _EXECUTION_DESIGN_MODULE_PATH,
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


def _declared_contract(
    protocol: materialization.D7V1MaterializationProtocol,
) -> tuple[str, tuple[str, str], dict[str, str]]:
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
    if supplier_role != _EXPECTED_SUPPLIER_IDENTITY_ROLE:
        raise QualificationContractError("frozen supplier identity role differs")

    embedded = materialization._mapping(
        joins.get("embedded_full_design"),
        label="embedded_full_design",
    )
    joined_roles = materialization._mapping(
        embedded.get("binding_roles_exact"),
        label="embedded full-design binding_roles_exact",
    )
    replay = materialization._mapping(
        protocol.document.get("replay_target_contract"),
        label="replay_target_contract",
    )
    replay_roles = materialization._mapping(
        replay.get("embedded_full_design_inventory_field_roles"),
        label="embedded_full_design_inventory_field_roles",
    )
    record_roles = dict(records._DESIGN_INVENTORY_ROLES)
    if not (
        joined_roles
        == replay_roles
        == record_roles
        == _EXPECTED_FULL_DESIGN_FIELD_ROLES
    ):
        raise QualificationContractError(
            "protocol and records full-design field-role maps differ"
        )

    observed_slots = execution_design.D7_CONFIRMATION_SEED_SLOT_IDS
    if type(observed_slots) is not tuple or observed_slots != _EXPECTED_SEED_SLOT_IDS:
        raise QualificationContractError("approved execution-design seed slots differ")
    return supplier_role, observed_slots, dict(sorted(joined_roles.items()))


def _require_same_source_closure(
    supplied: D7V1SourceClosureCandidate,
    rebuilt: D7V1SourceClosureCandidate,
) -> None:
    if (
        supplied.source_commit != rebuilt.source_commit
        or supplied.c1.canonical_bytes != rebuilt.c1.canonical_bytes
        or supplied.c2.canonical_bytes != rebuilt.c2.canonical_bytes
        or supplied.source_members != rebuilt.source_members
    ):
        raise QualificationContractError(
            "supplied source closure differs from the fresh choice-free rebuild"
        )


def _build_d7_v1_deterministic_input_contract_candidate(
    repository: RepositoryContext,
    *,
    source_closure: D7V1SourceClosureCandidate,
) -> D7V1DeterministicInputContractCandidate:
    """Rebuild source closure and observe only frozen deterministic contracts."""

    if not isinstance(repository, RepositoryContext):
        raise TypeError("repository must be RepositoryContext")
    if not isinstance(source_closure, D7V1SourceClosureCandidate):
        raise TypeError("source_closure must be D7V1SourceClosureCandidate")
    _require_import_origins(repository)

    rebuilt = source_closure_module._build_d7_v1_source_closure_candidate(
        repository,
        source_commit=source_closure.source_commit,
    )
    _require_same_source_closure(source_closure, rebuilt)
    protocol = materialization._protocol_at_commit(
        repository,
        rebuilt.source_commit,
    )
    if (
        materialization._verify_source_join(
            repository,
            protocol,
            rebuilt.c1,
            rebuilt.c2,
        )
        != rebuilt.source_commit
    ):
        raise QualificationContractError(
            "deterministic-input source rejoin returned a different source commit"
        )

    _require_exact_source_member(repository, rebuilt, _MODULE_PATH)
    _require_approved_execution_design_source(repository, protocol, rebuilt)
    supplier_role, seed_slots, full_design_roles = _declared_contract(protocol)

    result = D7V1DeterministicInputContractCandidate(
        source_closure=rebuilt,
        supplier_identity_role=supplier_role,
        required_seed_count=len(seed_slots),
        seed_slot_ids=seed_slots,
        full_design_field_roles=full_design_roles,
        _factory_token=_CANDIDATE_FACTORY_TOKEN,
    )

    _require_exact_source_member(repository, rebuilt, _MODULE_PATH)
    _require_exact_source_member(
        repository,
        rebuilt,
        _EXECUTION_DESIGN_MODULE_PATH,
    )
    if (
        materialization._verify_source_join(
            repository,
            protocol,
            rebuilt.c1,
            rebuilt.c2,
        )
        != rebuilt.source_commit
    ):
        raise QualificationContractError(
            "final deterministic-input source rejoin differs"
        )
    source_closure_module._require_exact_clean_head(
        repository,
        rebuilt.source_commit,
    )
    return result
