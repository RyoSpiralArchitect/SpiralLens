"""One-shot, honest-local D7 item-22 seed-supply transaction.

The persisted records are the existing D7 authority records.  This module owns
only the fixed item-22 paths, state table, re-anchor receipt, transaction
manifest, and abort evidence.  It grants no launch, execution, or scientific
authority; full-design freeze and the fused descriptor remain later steps.
"""

from __future__ import annotations

import os
import secrets
import stat
from pathlib import Path
from types import FunctionType

from spirallens.core.canonical import (
    CanonicalJsonError,
    canonical_json_bytes,
    canonical_json_sha256,
    parse_canonical_json,
    sha256_bytes,
)

from . import confirmation_attempt_authority as authority
from . import confirmation_attempt_persistence as durable
from . import confirmation_fused_authority as fused_authority
from . import confirmation_official_execution as official
from . import confirmation_preseed_authority as item21
from .common import QualificationContractError
from .persistence import (
    LoadedQualificationProtocol,
    PersistedQualificationIdentity,
    _atomic_write_no_overwrite,
)
from .protocol import QualificationProtocol

__all__: tuple[str, ...] = ()
D7_ITEM22_DIRECTORY_REPOSITORY_PATH = "experiments/qualification/d7_spectral_moment_confirmation_v0_1"
D7_ITEM22_CURRENT_SOURCE_RUNTIME_REANCHOR_REPOSITORY_PATH = f"{D7_ITEM22_DIRECTORY_REPOSITORY_PATH}/item22-current-source-runtime-reanchor.json"
D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH = f"{D7_ITEM22_DIRECTORY_REPOSITORY_PATH}/item22-seed-supply"
D7_ITEM22_EXCLUSIVE_SEED_SUPPLY_CLAIM_REPOSITORY_PATH = f"{D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH}/exclusive-seed-supply-claim.json"
D7_ITEM22_ATOMIC_TARGET_DIRECTORY_REPOSITORY_PATH = f"{D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH}/published-target"
D7_ITEM22_SINGLE_SUPPLIER_INVOCATION_REPOSITORY_PATH = f"{D7_ITEM22_ATOMIC_TARGET_DIRECTORY_REPOSITORY_PATH}/single-supplier-invocation.json"
D7_ITEM22_FULL_DESIGN_FREEZE_REPOSITORY_PATH = f"{D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH}/full-design-freeze.json"
D7_ITEM22_SEED_SUPPLY_ABORT_EVIDENCE_REPOSITORY_PATH = f"{D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH}/seed-supply-abort.json"
D7_ITEM22_FUTURE_LAUNCH_DESCRIPTOR_REPOSITORY_PATH = f"{D7_ITEM22_DIRECTORY_REPOSITORY_PATH}/launch.json"

D7_ITEM22_CURRENT_SOURCE_RUNTIME_REANCHOR_SCHEMA_VERSION = "spirallens.d7-item22-current-source-runtime-reanchor.v0.1"
D7_ITEM22_TRANSACTION_MANIFEST_SCHEMA_VERSION = "spirallens.d7-item22-seed-supply-transaction-manifest.v0.1"
D7_ITEM22_ABORT_EVIDENCE_SCHEMA_VERSION = "spirallens.d7-item22-seed-supply-abort-evidence.v0.1"
D7_ITEM22_SUPPLIER_IDENTITY_SCHEMA_VERSION = "spirallens.d7-item22-honest-local-os-csprng-supplier.v0.1"
D7_ITEM22_CLAIM_KEY_SCHEMA_VERSION = "spirallens.d7-item22-exclusive-seed-supply-claim-key.v0.1"
D7_ITEM22_CLAIM_KEY_DOMAIN = "spirallens:d7:item22:exclusive-seed-supply-claim:v0.1"
MAX_D7_ITEM22_ARTIFACT_BYTES = 4 * 1024 * 1024
_SIGNED_INT64_MAX = (1 << 63) - 1

D7_ITEM22_ATOMIC_TARGET_MEMBER_LAYOUT = (
    ("official-seed-inventory", "official-seed-inventory.json"),
    ("full-inventory", "full-inventory.json"),
    ("full-design", "full-design.json"),
    ("replay-target", "replay-target.json"),
    ("single-supplier-invocation", "single-supplier-invocation.json"),
    ("transaction-manifest", "transaction-manifest.json"),
)
D7_ITEM22_TARGET_DIGEST_EDGES = (
    ("full-inventory", "official-seed-inventory"),
    ("full-design", "official-seed-inventory"),
    ("full-design", "full-inventory"),
    ("replay-target", "official-seed-inventory"),
    ("replay-target", "full-design"),
    ("single-supplier-invocation", "official-seed-inventory"),
)
D7_ITEM22_CLAIM_KEY_FIELDS = (
    "exclusive_claim_repository_path",
    "historical_item21_bindings",
    "reviewed_current_source_runtime_reanchor_binding",
    "supplier_identity_binding",
    "development_seed_exclusion_registry_binding",
    "parent_selection_seed_exclusion_registry_binding",
)
D7_ITEM22_STATE_ROWS = (
    ("preclaim", False, False, False, False, False),
    ("claim-present-publication-absent-nonretryable", True, False, False, False, False),
    ("seed-supply-aborted-established", True, False, True, False, False),
    ("publication-complete-unfrozen", True, True, False, False, False),
    ("full-design-frozen", True, True, False, True, False),
    ("launch-intent-present", True, True, False, True, True),
)
_CODE_ROLE_PATHS = (
    ("lifecycle-code", "src/spirallens/qualification/confirmation_attempt_records.py"),
    ("result-code", "src/spirallens/qualification/confirmation_result_components.py"),
    ("terminal-code", "src/spirallens/qualification/confirmation_attempt_terminal_persistence.py"),
    ("witness-code", "src/spirallens/qualification/confirmation_external_witness.py"),
    ("runner-code", "src/spirallens/qualification/confirmation_runner.py"),
)
_TRANSACTION_ROOT_ALLOWED = {"exclusive-seed-supply-claim.json", "published-target", "seed-supply-abort.json", "full-design-freeze.json"}

def _mapping(value: object, *, label: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise QualificationContractError(f"{label} must be a JSON object")
    return dict(value)

def _canonical_document(source: bytes, *, label: str) -> dict[str, object]:
    if type(source) is not bytes or not source or len(source) > MAX_D7_ITEM22_ARTIFACT_BYTES:
        raise QualificationContractError(f"{label} exceeds its byte contract")
    try:
        value = parse_canonical_json(source, label=label)
    except CanonicalJsonError as error:
        raise QualificationContractError(str(error)) from error
    document = _mapping(value, label=label)
    if canonical_json_bytes(document) != source:
        raise QualificationContractError(f"{label} is not canonical JSON")
    return document

def _binding(role: str, contract_id: str, source: bytes) -> authority.D7AuthorityArtifactBinding:
    return authority.D7AuthorityArtifactBinding(
        artifact_role=role,
        artifact_contract_id=contract_id,
        canonical_sha256=sha256_bytes(source),
        byte_count=len(source),
    )
def _item21_artifacts(
    root: Path,
) -> tuple[item21._LoadedArtifact, item21._LoadedArtifact, item21._LoadedArtifact]:
    receipt = item21._load_source_receipt(root)
    readiness = item21._load_readiness(root, receipt)
    admission = item21._load_admission(root, receipt, readiness)
    item21._require_ancestor(
        root,
        admission.introduction_commit,
        item21._head(root),
        label="item-21 admission-to-current-HEAD",
    )
    return receipt, readiness, admission


def _historical_item21_bindings(
    artifacts: tuple[
        item21._LoadedArtifact,
        item21._LoadedArtifact,
        item21._LoadedArtifact,
    ],
) -> list[dict[str, object]]:
    specs = (
        ("execution-source-runtime-receipt", item21.D7_ITEM21_SOURCE_RUNTIME_RECEIPT_SCHEMA_VERSION, artifacts[0]),
        ("seed-free-readiness", item21.D7_ITEM21_SEED_FREE_READINESS_SCHEMA_VERSION, artifacts[1]),
        ("family-admission-receipt", item21.D7_ITEM21_REVIEWED_FAMILY_ADMISSION_SCHEMA_VERSION, artifacts[2]),
    )
    return [
        {
            "artifact_role": role,
            "repository_path": artifact.repository_path,
            "schema_version": schema,
            "canonical_sha256": artifact.canonical_sha256,
            "byte_count": artifact.byte_count,
            "introduction_commit": artifact.introduction_commit,
        }
        for role, schema, artifact in specs
    ]

def _reanchor_document(
    root: Path,
    *,
    source_commit: str,
    recorded_runtime: dict[str, object] | None,
) -> dict[str, object]:
    live = recorded_runtime is None
    document = item21._source_receipt_document(
        root,
        source_commit=source_commit,
        require_current_source_equality=live,
        require_installed_equality=live,
        recorded_runtime=recorded_runtime,
    )
    artifacts = _item21_artifacts(root)
    document["schema_version"] = D7_ITEM22_CURRENT_SOURCE_RUNTIME_REANCHOR_SCHEMA_VERSION
    document["receipt_id"] = "d7-item22-current-source-runtime-reanchor-v0-1"
    document["repository_path"] = D7_ITEM22_CURRENT_SOURCE_RUNTIME_REANCHOR_REPOSITORY_PATH
    document["status"] = "reviewed-exact-current-item22-source-runtime-reanchor"
    lineage = _mapping(document["lineage"], label="reanchor lineage")
    lineage["historical_item21_chain"] = _historical_item21_bindings(artifacts)
    document["lineage"] = lineage
    review = _mapping(document["final_code_review"], label="reanchor review")
    review["review_id"] = "d7-item22-final-source-review-v0-1"
    review["review_scope"] = [*review["review_scope"], "item22-one-shot-seed-supply-transaction"]
    document["final_code_review"] = review
    document["final_code_review_sha256"] = canonical_json_sha256(review)
    state = _mapping(document["state"], label="reanchor state")
    state["seed_free_readiness_present"] = True
    state["family_admission_present"] = True
    document["state"] = state
    return document

def build_d7_item22_current_source_runtime_reanchor(repository_root: str | Path) -> bytes:
    root = item21._repository_root(repository_root)
    item21._require_clean(root)
    destination = root / D7_ITEM22_CURRENT_SOURCE_RUNTIME_REANCHOR_REPOSITORY_PATH
    if destination.exists() or destination.is_symlink():
        raise QualificationContractError("item-22 re-anchor path is already present")
    item21._require_live_paths_absent(root)
    source_commit = item21._head(root)
    return canonical_json_bytes(_reanchor_document(root, source_commit=source_commit, recorded_runtime=None))

def issue_d7_item22_current_source_runtime_reanchor(repository_root: str | Path) -> PersistedQualificationIdentity:
    root = item21._repository_root(repository_root)
    source = build_d7_item22_current_source_runtime_reanchor(root)
    return _atomic_write_no_overwrite(
        root / D7_ITEM22_CURRENT_SOURCE_RUNTIME_REANCHOR_REPOSITORY_PATH,
        source,
        maximum_bytes=MAX_D7_ITEM22_ARTIFACT_BYTES,
        label="D7 item-22 current source/runtime re-anchor",
    )

def _load_reanchor(root: Path) -> item21._LoadedArtifact:
    path = root / D7_ITEM22_CURRENT_SOURCE_RUNTIME_REANCHOR_REPOSITORY_PATH
    source = item21._read_worktree_artifact(root, D7_ITEM22_CURRENT_SOURCE_RUNTIME_REANCHOR_REPOSITORY_PATH)
    document = _canonical_document(source, label="D7 item-22 re-anchor")
    if (
        document.get("schema_version")
        != D7_ITEM22_CURRENT_SOURCE_RUNTIME_REANCHOR_SCHEMA_VERSION
        or document.get("repository_path")
        != D7_ITEM22_CURRENT_SOURCE_RUNTIME_REANCHOR_REPOSITORY_PATH
    ):
        raise QualificationContractError("item-22 re-anchor identity differs")
    lineage = _mapping(document.get("lineage"), label="reanchor lineage")
    source_commit = item21._commit(lineage.get("source_commit"), label="reanchor source commit")
    runtime = _mapping(document.get("runtime_observation"), label="reanchor runtime")
    expected = _reanchor_document(root, source_commit=source_commit, recorded_runtime=runtime)
    if document != expected or source != canonical_json_bytes(expected):
        raise QualificationContractError("item-22 re-anchor differs from reconstruction")
    introduction = item21._introduction_commit(
        root,
        repository_path=D7_ITEM22_CURRENT_SOURCE_RUNTIME_REANCHOR_REPOSITORY_PATH,
        expected_parent=source_commit,
        expected_source=source,
    )
    return item21._LoadedArtifact(path.relative_to(root).as_posix(), source, introduction)

def _verify_reanchor_live(root: Path) -> item21._LoadedArtifact:
    item21._require_clean(root)
    loaded = _load_reanchor(root)
    item21._verify_live_runtime(root, loaded)
    document = loaded.document
    item21._recorded_components(
        root,
        source_observation=_mapping(document["source_observation"], label="source observation"),
        verify_current_implementation=True,
    )
    item21._current_code_side_execution_ingredients()
    return loaded

def _parse_record(source: bytes, record_type: type[object], *, label: str) -> object:
    document = _canonical_document(source, label=label)
    try:
        record = record_type.from_dict(document)  # type: ignore[attr-defined]
    except (TypeError, ValueError) as error:
        raise QualificationContractError(f"{label} is invalid") from error
    if record.canonical_bytes != source:  # type: ignore[attr-defined]
        raise QualificationContractError(f"{label} canonical bytes differ")
    return record

def _load_target(
    root: Path,
    transaction: durable._DirectoryAnchor,
    claim: authority.D7ExclusiveSeedSupplyClaimInputRecord,
    context: dict[str, object],
) -> tuple[
    authority.D7ReplayTargetInputRecord,
    authority.D7AuthorityArtifactBinding,
    dict[str, bytes],
]:
    del root
    target = durable._open_child_directory(
        transaction,
        leaf="published-target",
        label="item-22 published target",
        create=False,
    )
    target_identity = target.device, target.inode
    try:
        expected_names = {name for _role, name in D7_ITEM22_ATOMIC_TARGET_MEMBER_LAYOUT}
        if set(os.listdir(target.descriptor)) != expected_names:
            raise QualificationContractError("item-22 target member set differs")
        members = {
            role: durable._read_bounded_file(
                target,
                filename,
                maximum_bytes=MAX_D7_ITEM22_ARTIFACT_BYTES,
                label=f"item-22 {role}",
            )
            for role, filename in D7_ITEM22_ATOMIC_TARGET_MEMBER_LAYOUT
        }
        sources = {role: member[0] for role, member in members.items()}
        member_identities = {role: durable._stable_file_identity(member[1]) for role, member in members.items()}
    finally:
        os.close(target.descriptor)
    inventory = _parse_record(sources["official-seed-inventory"], authority.D7OfficialSeedInventoryRecord, label="official seed inventory")
    invocation = _parse_record(sources["single-supplier-invocation"], authority.D7SingleSupplierInvocationInputRecord, label="supplier invocation")
    replay_target = _parse_record(sources["replay-target"], authority.D7ReplayTargetInputRecord, label="replay target")
    manifest = _canonical_document(sources["transaction-manifest"], label="transaction manifest")
    manifest_fields = {"schema_version", "transaction_id", "claim_binding", "supplier_identity_binding", "members", "runtime_specification", "source_runtime_closure", "family_admission", "chronology", "claim_ceiling", "authority"}
    if set(manifest) != manifest_fields or manifest["schema_version"] != D7_ITEM22_TRANSACTION_MANIFEST_SCHEMA_VERSION:
        raise QualificationContractError("transaction manifest shape differs")
    member_bindings = [{"artifact_role": role, "filename": filename, "canonical_sha256": sha256_bytes(sources[role]), "byte_count": len(sources[role])} for role, filename in D7_ITEM22_ATOMIC_TARGET_MEMBER_LAYOUT[:-1]]
    if manifest["members"] != member_bindings:
        raise QualificationContractError("transaction manifest member bindings differ")
    claim_binding = _binding("exclusive-seed-supply-claim", claim.schema_version, claim.canonical_bytes)
    inventory_binding = _binding("official-seed-inventory", inventory.schema_version, inventory.canonical_bytes)  # type: ignore[attr-defined]
    design_binding = _binding("full-design", official.D7_OFFICIAL_FULL_DESIGN_SCHEMA_VERSION, sources["full-design"])
    inventory_document = _canonical_document(sources["full-inventory"], label="full inventory")
    design_document = _canonical_document(sources["full-design"], label="full design")
    if (
        manifest["claim_binding"] != claim_binding.to_dict()
        or invocation.claim_binding != claim_binding  # type: ignore[attr-defined]
        or invocation.official_seed_inventory_binding != inventory_binding  # type: ignore[attr-defined]
        or replay_target.official_seed_inventory_binding != inventory_binding  # type: ignore[attr-defined]
        or replay_target.full_design_binding.design_binding != design_binding  # type: ignore[attr-defined]
        or replay_target.full_design_binding.inventory_sha256 != sha256_bytes(sources["full-inventory"])  # type: ignore[attr-defined]
        or design_document.get("official_seed_inventory_sha256") != inventory_binding.canonical_sha256
        or design_document.get("full_inventory_sha256") != sha256_bytes(sources["full-inventory"])
        or inventory_document.get("official_seed_inventory_sha256") != inventory_binding.canonical_sha256
    ):
        raise QualificationContractError("item-22 target digest graph differs")
    try:
        records = tuple(authority.D7ChronologyInputRecord.from_dict(item) for item in manifest["chronology"])  # type: ignore[union-attr]
    except (KeyError, TypeError, ValueError) as error:
        raise QualificationContractError("item-22 target chronology is invalid") from error
    if (
        tuple(record.transition for record in records)
        != authority.D7_SEED_SUPPLY_TRANSITION_ORDER[:7]
        or any(records[index].predecessor_binding != records[index - 1].artifact_binding for index in range(1, 7))
    ):
        raise QualificationContractError("item-22 target chronology differs")
    authority.D7RuntimeSpecificationInputRecord.from_dict(manifest["runtime_specification"])
    authority.D7SourceRuntimeClosureInputRecord.from_dict(manifest["source_runtime_closure"])
    authority.D7FamilyAdmissionInputRecord.from_dict(manifest["family_admission"])
    seed_values = tuple(seed.seed for seed in inventory.seeds)  # type: ignore[attr-defined]
    if sources != _target_sources(context, seed_values):
        raise QualificationContractError("item-22 target differs from reconstruction")
    rejoined = durable._open_child_directory(transaction, leaf="published-target", label="item-22 published target rejoin", create=False)
    try:
        if (rejoined.device, rejoined.inode) != target_identity or set(os.listdir(rejoined.descriptor)) != expected_names:
            raise QualificationContractError("item-22 target directory identity changed")
        for role, filename in D7_ITEM22_ATOMIC_TARGET_MEMBER_LAYOUT:
            rejoined_member = durable._read_bounded_file(rejoined, filename, maximum_bytes=MAX_D7_ITEM22_ARTIFACT_BYTES, label=f"item-22 rejoined {role}")
            if rejoined_member[0] != sources[role] or durable._stable_file_identity(rejoined_member[1]) != member_identities[role]:
                raise QualificationContractError("item-22 target member identity or bytes changed before rejoin")
        durable._verify_anchor(rejoined, label="item-22 published target rejoin")
        durable._verify_anchor(transaction, label="item-22 transaction root")
    finally:
        os.close(rejoined.descriptor)
    return replay_target, records[-1].artifact_binding, sources  # type: ignore[return-value]


def _anchored_canonical(
    anchor: durable._DirectoryAnchor,
    leaf: str,
    *,
    label: str,
) -> bytes:
    source = durable._read_bounded_file(
        anchor,
        leaf,
        maximum_bytes=MAX_D7_ITEM22_ARTIFACT_BYTES,
        label=label,
    )[0]
    _canonical_document(source, label=label)
    return source


def _immutable_introduction(
    root: Path,
    *,
    repository_path: str,
    expected_source: bytes,
    after_commit: str,
) -> str:
    history = item21._bounded_path_history(
        root,
        revision="HEAD",
        repository_paths=(repository_path,),
        ancestry_path=False,
        label="item-22 freeze full Git history",
    )
    candidates: list[str] = []
    for commit in history:
        row = item21._git(root, "rev-list", "--parents", "-n", "1", commit).stdout
        try:
            commits = row.decode("ascii").strip().split()
        except UnicodeDecodeError as error:
            raise QualificationContractError("freeze history is not ASCII") from error
        if item21._tree_entry(root, commit, repository_path) is not None and all(
            item21._tree_entry(root, parent, repository_path) is None
            for parent in commits[1:]
        ):
            candidates.append(commit)
    if len(candidates) != 1:
        raise QualificationContractError("freeze lacks one immutable introduction")
    introduction = candidates[0]
    if introduction == after_commit:
        raise QualificationContractError("freeze introduction must follow authorization")
    item21._require_ancestor(
        root,
        after_commit,
        introduction,
        label="authorization-to-freeze-receipt",
    )
    entry = item21._tree_entry(root, introduction, repository_path)
    if entry is None or entry[:2] != ("100644", "blob"):
        raise QualificationContractError("freeze introduction is not one 100644 blob")
    for event in (*history, item21._head(root)):
        item21._require_ancestor(
            root,
            introduction,
            event,
            label="freeze immutable descendant history",
        )
        if item21._tree_entry(root, event, repository_path) != entry:
            raise QualificationContractError("freeze changed after introduction")
    if item21._blob(root, introduction, repository_path) != expected_source:
        raise QualificationContractError("freeze introduction bytes differ")
    return introduction


def _verify_freeze(
    root: Path,
    *,
    claim: authority.D7ExclusiveSeedSupplyClaimInputRecord,
    freeze: authority.D7FullDesignFreezeInputRecord,
    freeze_source: bytes,
    target_records: tuple[
        authority.D7ReplayTargetInputRecord,
        authority.D7AuthorityArtifactBinding,
        dict[str, bytes],
    ],
    context: dict[str, object],
) -> None:
    replay_target, publication_binding, sources = target_records
    if (
        freeze.full_design_binding != replay_target.full_design_binding.design_binding
        or freeze.replay_target_binding
        != _binding("replay-target", replay_target.schema_version, replay_target.canonical_bytes)
        or freeze.atomic_publication_binding != publication_binding
    ):
        raise QualificationContractError("item-22 freeze differs from target")
    source_commit = context["closure"].source_commit  # type: ignore[union-attr]
    reanchor_commit = str(context["reanchor_introduction_commit"])
    for earlier, later, label in (
        (source_commit, freeze.freeze_commit, "source-to-target-freeze"),
        (freeze.freeze_commit, freeze.authorization_commit, "target-freeze-to-authorization"),
    ):
        if earlier == later:
            raise QualificationContractError(f"{label} must be strict")
        item21._require_ancestor(root, earlier, later, label=label)
    _immutable_introduction(
        root,
        repository_path=D7_ITEM22_FULL_DESIGN_FREEZE_REPOSITORY_PATH,
        expected_source=freeze_source,
        after_commit=freeze.authorization_commit,
    )
    frozen_sources = ((D7_ITEM22_EXCLUSIVE_SEED_SUPPLY_CLAIM_REPOSITORY_PATH, claim.canonical_bytes), *((f"{D7_ITEM22_ATOMIC_TARGET_DIRECTORY_REPOSITORY_PATH}/{filename}", sources[role]) for role, filename in D7_ITEM22_ATOMIC_TARGET_MEMBER_LAYOUT))
    for repository_path, expected_source in frozen_sources:
        introduction = _immutable_introduction(root, repository_path=repository_path, expected_source=expected_source, after_commit=reanchor_commit)
        item21._require_ancestor(root, introduction, freeze.freeze_commit, label="frozen-member-to-target-freeze")
        if item21._blob(root, freeze.freeze_commit, repository_path) != expected_source:
            raise QualificationContractError("freeze commit member bytes differ")

def observe_d7_item22_seed_supply_state(repository_root: str | Path) -> str:
    root = item21._repository_root(repository_root)
    experiment = durable._open_real_directory(
        root / D7_ITEM22_DIRECTORY_REPOSITORY_PATH,
        label="item-22 experiment directory",
    )
    transaction = None
    try:
        if durable._relative_stat(experiment, "item22-seed-supply") is not None:
            transaction = durable._open_child_directory(
                experiment,
                leaf="item22-seed-supply",
                label="item-22 transaction root",
                create=False,
            )
            names = set(os.listdir(transaction.descriptor))
            if not names.issubset(_TRANSACTION_ROOT_ALLOWED):
                raise QualificationContractError("item-22 transaction root has unknown members")
        leaves = (
            "exclusive-seed-supply-claim.json",
            "published-target",
            "seed-supply-abort.json",
            "full-design-freeze.json",
        )
        transaction_present = tuple(
            transaction is not None and durable._relative_stat(transaction, leaf) is not None
            for leaf in leaves
        )
        present = (*transaction_present, durable._relative_stat(experiment, "launch.json") is not None)
        matches = [row[0] for row in D7_ITEM22_STATE_ROWS if tuple(row[1:]) == present]
        if len(matches) != 1:
            raise QualificationContractError("item-22 artifact presence state is invalid")
        claim = None
        context = None
        target_records = None
        freeze = None
        if present[0]:
            claim = _parse_record(
                _anchored_canonical(transaction, leaves[0], label="item-22 claim"),  # type: ignore[arg-type]
                authority.D7ExclusiveSeedSupplyClaimInputRecord,
                label="item-22 claim",
            )
            context = _foundation(root, _load_reanchor(root))
            if claim != context["claim"]:
                raise QualificationContractError("item-22 claim differs from reconstruction")
        if present[1]:
            target_records = _load_target(root, transaction, claim, context)  # type: ignore[arg-type]
        if present[2]:
            abort = _canonical_document(
                _anchored_canonical(transaction, leaves[2], label="item-22 abort"),  # type: ignore[arg-type]
                label="item-22 abort",
            )
            if (
                set(abort) != {"schema_version", "claim_binding", "failed_phase", "supplier_entry_possible", "target_published", "retry_authorized"}
                or abort["schema_version"] != D7_ITEM22_ABORT_EVIDENCE_SCHEMA_VERSION
                or abort["claim_binding"] != _binding("exclusive-seed-supply-claim", claim.schema_version, claim.canonical_bytes).to_dict()  # type: ignore[union-attr]
                    or abort["failed_phase"] not in ("supplier-entry", "target-construction", "atomic-target-publication")
                or abort["supplier_entry_possible"] is not True
                or abort["target_published"] is not False
                or abort["retry_authorized"] is not False
            ):
                raise QualificationContractError("item-22 abort evidence differs")
        if present[3]:
            freeze_source = _anchored_canonical(
                transaction,  # type: ignore[arg-type]
                leaves[3],
                label="item-22 freeze",
            )
            freeze = _parse_record(
                freeze_source,
                authority.D7FullDesignFreezeInputRecord,
                label="item-22 freeze",
            )
            _verify_freeze(
                root,
                claim=claim,  # type: ignore[arg-type]
                freeze=freeze,  # type: ignore[arg-type]
                freeze_source=freeze_source,
                target_records=target_records,  # type: ignore[arg-type]
                context=context,  # type: ignore[arg-type]
            )
        if present[4]:
            snapshot = fused_authority.load_d7_fused_authority_snapshot(
                experiment.path / "launch.json"
            )
            replay_target, _publication_binding, _sources = target_records  # type: ignore[misc]
            member_paths = {
                member.artifact_role: member.repository_path
                for member in snapshot.descriptor.inventory
            }
            if (
                snapshot.replay_target != replay_target
                or snapshot.full_design_freeze != freeze
                or member_paths["replay-target"] != f"{D7_ITEM22_ATOMIC_TARGET_DIRECTORY_REPOSITORY_PATH}/replay-target.json"
                or member_paths["full-design-freeze"] != D7_ITEM22_FULL_DESIGN_FREEZE_REPOSITORY_PATH
            ):
                raise QualificationContractError("item-22 launch descriptor differs from target or freeze")
        durable._verify_anchor(experiment, label="item-22 experiment directory")
        if transaction is not None:
            durable._verify_anchor(transaction, label="item-22 transaction root")
        return matches[0]
    finally:
        if transaction is not None:
            os.close(transaction.descriptor)
        os.close(experiment.descriptor)

def _supplier_identity() -> authority.D7AuthorityArtifactBinding:
    candidate = globals().get("_supply_official_seed_values")
    if (
        type(candidate) is not FunctionType
        or candidate is not _FIXED_SUPPLIER
        or candidate.__module__ != __name__
        or candidate.__qualname__ != "_supply_official_seed_values"
        or candidate.__code__.co_argcount != 0
        or candidate.__closure__ is not None
    ):
        raise QualificationContractError("fixed item-22 supplier identity differs")
    document = {"schema_version": D7_ITEM22_SUPPLIER_IDENTITY_SCHEMA_VERSION, "supplier_id": "d7-item22-honest-local-os-csprng-v0-1", "module": __name__, "qualname": candidate.__qualname__, "entropy_api": "secrets.randbits(63)", "output_contract": "two-unique-sorted-nonnegative-signed-int64-exclusion-clean", "cryptographic_unseen_proof": False}
    source = canonical_json_bytes(document)
    return _binding("seed-supplier-identity", D7_ITEM22_SUPPLIER_IDENTITY_SCHEMA_VERSION, source)

def _supply_official_seed_values() -> tuple[int, int]:
    excluded = {
        *(entry.seed for entry in authority.D7DevelopmentSeedExclusionRegistryRecord.exact().entries),
        *(entry.seed for entry in authority.D7ParentSelectionSeedExclusionRegistryRecord.exact().entries),
    }
    values: set[int] = set()
    for _attempt in range(256):
        value = secrets.randbits(63)
        if type(value) is int and 0 <= value <= _SIGNED_INT64_MAX and value not in excluded:
            values.add(value)
        if len(values) == 2:
            return tuple(sorted(values))  # type: ignore[return-value]
    raise QualificationContractError("fixed CSPRNG supplier did not produce two valid seeds")


_FIXED_SUPPLIER = _supply_official_seed_values

def _step(transition: authority.D7SeedSupplyTransition, ordinal: int, record_id: str, predecessor: authority.D7AuthorityArtifactBinding | None, subjects: tuple[authority.D7AuthorityArtifactBinding, ...]) -> authority.D7ChronologyInputRecord:
    return authority.D7ChronologyInputRecord(transition=transition, ordinal=ordinal, record_id=record_id, predecessor_binding=predecessor, subject_bindings=subjects)


def _recorded_design(root: Path, source_observation: dict[str, object]) -> object:
    head = item21._head(root)
    bindings = item21._recorded_components(
        root,
        source_observation=source_observation,
        verify_current_implementation=False,
    )
    c1_source = item21._blob(root, head, official.D7_C1_BUNDLE_REPOSITORY_PATH)
    c1_document = official.D7C1SeedFreeSourceSet.from_canonical_bytes(
        c1_source,
        expected_sha256=authority.D7_RECORDED_C1_CANONICAL_SHA256,
    ).to_dict()
    components = _mapping(c1_document.get("components"), label="recorded C1 components")
    design_component = _mapping(components.get("seed_free_execution_design"), label="recorded C1 design component")
    design_body = _mapping(design_component.get("body"), label="recorded C1 design body")
    design_document = _mapping(design_body.get("seed_free_execution_design"), label="recorded C1 design")
    design_source = canonical_json_bytes(design_document)
    design_binding = _mapping(bindings.get("seed_free_design"), label="recorded C1 design binding")
    if (
        design_binding.get("canonical_sha256") != sha256_bytes(design_source)
        or design_binding.get("byte_count") != len(design_source)
    ):
        raise QualificationContractError("recorded C1 design binding differs")
    parent_source = item21._blob(
        root,
        head,
        official.D7_OFFICIAL_PARENT_PROTOCOL_REPOSITORY_PATH,
    )
    if sha256_bytes(parent_source) != official.D7_OFFICIAL_PARENT_PROTOCOL_SHA256:
        raise QualificationContractError("recorded parent protocol binding differs")
    parent = QualificationProtocol.from_dict(
        _canonical_document(parent_source, label="recorded parent protocol")
    )
    loaded_parent = LoadedQualificationProtocol(
        protocol=parent,
        source_path=root / official.D7_OFFICIAL_PARENT_PROTOCOL_REPOSITORY_PATH,
        source_bytes=parent_source,
        source_sha256=official.D7_OFFICIAL_PARENT_PROTOCOL_SHA256,
        canonical_sha256=official.D7_OFFICIAL_PARENT_PROTOCOL_SHA256,
    )
    design = official._build_recorded_c1_d7_confirmation_execution_design(
        parent_protocol=loaded_parent,
        recorded_document=design_document,
    )
    if item21._head(root) != head:
        raise QualificationContractError("Git HEAD changed during recorded design reload")
    return design


def _foundation(root: Path, reanchor: item21._LoadedArtifact) -> dict[str, object]:
    receipt, readiness, admission = _item21_artifacts(root)
    document = reanchor.document
    runtime_document = _mapping(document["runtime_observation"], label="runtime observation")
    runtime = authority.D7RuntimeSpecificationInputRecord.from_dict(runtime_document["runtime_specification"])
    members = {
        str(item["repository_path"]): item
        for item in document["source_observation"]["members"]  # type: ignore[index]
    }
    code_bindings = tuple(authority.D7AuthorityArtifactBinding(artifact_role=role, artifact_contract_id="spirallens.python-source.v0.1", canonical_sha256=str(members[path]["sha256"]), byte_count=int(members[path]["byte_count"])) for role, path in _CODE_ROLE_PATHS)
    final_code = _step(authority.D7SeedSupplyTransition.FINAL_CODE_REVIEWED, 0, "d7-item22-final-code-reviewed-v0-1", None, code_bindings)
    reanchor_binding = _binding("execution-source-runtime-receipt", D7_ITEM22_CURRENT_SOURCE_RUNTIME_REANCHOR_SCHEMA_VERSION, reanchor.source)
    closure = authority.D7SourceRuntimeClosureInputRecord(closure_id="d7-item22-execution-source-runtime-closure-v0-1", receipt_binding=reanchor_binding, final_code_review_binding=final_code.artifact_binding, runtime_specification_binding=_binding("runtime-specification", runtime.schema_version, runtime.canonical_bytes), source_commit=str(document["lineage"]["source_commit"]), source_tree_sha256=str(document["source_observation"]["source_tree_sha256"]), transitive_dependency_set_sha256=str(runtime_document["installed_dependency_set_sha256"]))  # type: ignore[index]
    closure_step = _step(authority.D7SeedSupplyTransition.EXACT_SOURCE_RUNTIME_CLOSURE, 1, "d7-item22-source-runtime-closure-v0-1", final_code.artifact_binding, (reanchor_binding,))
    readiness_binding = _binding("seed-free-readiness", item21.D7_ITEM21_SEED_FREE_READINESS_SCHEMA_VERSION, readiness.source)
    readiness_step = _step(authority.D7SeedSupplyTransition.SEED_FREE_READINESS, 2, "d7-item22-seed-free-readiness-v0-1", closure_step.artifact_binding, (readiness_binding,))
    admission_binding = _binding("family-admission-receipt", item21.D7_ITEM21_REVIEWED_FAMILY_ADMISSION_SCHEMA_VERSION, admission.source)
    admission_document = admission.document
    admission_spec = _mapping(admission_document["successor_admission_spec"], label="admission spec")
    review_identity = _mapping(admission_spec["reviewed_successor_bindings"]["construction_diversity_review"], label="construction review")  # type: ignore[index]
    construction_binding = authority.D7AuthorityArtifactBinding(artifact_role="construction-review", artifact_contract_id=str(review_identity["schema_version"]), canonical_sha256=str(review_identity["canonical_sha256"]), byte_count=int(review_identity["byte_count"]))
    family = authority.D7FamilyAdmissionInputRecord(admission_id="d7-item22-reviewed-family-admission-v0-1", generator_family_id=authority.D7_CONFIRMATION_GENERATOR_FAMILY_ID, admission_receipt_binding=admission_binding, source_runtime_closure_binding=_binding("execution-source-runtime-closure", closure.schema_version, closure.canonical_bytes), seed_free_readiness_binding=readiness_binding, construction_review_binding=construction_binding, admission_spec_binding=_binding("admission-spec", str(admission_spec["schema_version"]), canonical_json_bytes(admission_spec)))
    admission_step = _step(authority.D7SeedSupplyTransition.REVIEWED_FAMILY_ADMISSION, 3, "d7-item22-reviewed-family-admission-v0-1", readiness_step.artifact_binding, (admission_binding,))
    development = authority.D7DevelopmentSeedExclusionRegistryRecord.exact()
    parent = authority.D7ParentSelectionSeedExclusionRegistryRecord.exact()
    supplier = _supplier_identity()
    claim_fields = {
        "exclusive_claim_repository_path": D7_ITEM22_EXCLUSIVE_SEED_SUPPLY_CLAIM_REPOSITORY_PATH,
        "historical_item21_bindings": _historical_item21_bindings((receipt, readiness, admission)),
        "reviewed_current_source_runtime_reanchor_binding": reanchor_binding.to_dict(),
        "supplier_identity_binding": supplier.to_dict(),
        "development_seed_exclusion_registry_binding": _binding("development-seed-exclusion-registry", development.schema_version, development.canonical_bytes).to_dict(),
        "parent_selection_seed_exclusion_registry_binding": _binding("parent-selection-seed-exclusion-registry", parent.schema_version, parent.canonical_bytes).to_dict(),
    }
    if tuple(claim_fields) != D7_ITEM22_CLAIM_KEY_FIELDS:
        raise QualificationContractError("item-22 claim-key field order differs")
    claim_key = canonical_json_sha256({"schema_version": D7_ITEM22_CLAIM_KEY_SCHEMA_VERSION, "domain_separator": D7_ITEM22_CLAIM_KEY_DOMAIN, **claim_fields})
    claim = authority.D7ExclusiveSeedSupplyClaimInputRecord(claim_id=f"d7-item22-claim-{claim_key}", supplier_identity_binding=supplier, development_exclusion_registry_binding=authority.D7AuthorityArtifactBinding.from_dict(claim_fields["development_seed_exclusion_registry_binding"]), parent_selection_exclusion_registry_binding=authority.D7AuthorityArtifactBinding.from_dict(claim_fields["parent_selection_seed_exclusion_registry_binding"]), seed_free_readiness_binding=readiness_binding, admission_receipt_binding=admission_binding, source_runtime_receipt_binding=reanchor_binding)
    return {"runtime": runtime, "closure": closure, "reanchor_introduction_commit": reanchor.introduction_commit, "family": family, "development": development, "parent": parent, "supplier": supplier, "claim": claim, "chronology": (final_code, closure_step, readiness_step, admission_step), "design": _recorded_design(root, _mapping(document["source_observation"], label="source observation"))}


def _target_sources(context: dict[str, object], seed_values: tuple[int, int]) -> dict[str, bytes]:
    development = context["development"]
    parent = context["parent"]
    claim = context["claim"]
    inventory = authority.D7OfficialSeedInventoryRecord(
        inventory_id="d7-item22-official-seed-inventory-v0-1",
        development_exclusion_registry_binding=_binding("development-seed-exclusion-registry", development.schema_version, development.canonical_bytes),  # type: ignore[attr-defined]
        parent_selection_exclusion_registry_binding=_binding("parent-selection-seed-exclusion-registry", parent.schema_version, parent.canonical_bytes),  # type: ignore[attr-defined]
        seeds=tuple(authority.D7OfficialSeed(seed_slot_id=slot, seed=value) for slot, value in zip(authority.D7_CONFIRMATION_SEED_SLOT_IDS, seed_values, strict=True)),
    )
    inventory_binding = _binding("official-seed-inventory", inventory.schema_version, inventory.canonical_bytes)
    full_inventory_document = official.build_d7_official_full_inventory_document(design=context["design"], official_seed_inventory=inventory)  # type: ignore[arg-type]
    full_inventory_source = canonical_json_bytes(full_inventory_document)
    aggregation_document = official.build_d7_official_aggregation_document(implementation_registry_sha256=official.D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_SHA256)
    aggregation_source = canonical_json_bytes(aggregation_document)
    full_design_document = official.build_d7_official_full_design_document(design=context["design"], official_seed_inventory=inventory, full_inventory_sha256=sha256_bytes(full_inventory_source), implementation_registry_sha256=official.D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_SHA256, aggregation_sha256=sha256_bytes(aggregation_source))  # type: ignore[arg-type]
    full_design_source = canonical_json_bytes(full_design_document)
    full_design_binding = _binding("full-design", official.D7_OFFICIAL_FULL_DESIGN_SCHEMA_VERSION, full_design_source)
    family = context["family"]
    closure = context["closure"]
    runtime = context["runtime"]
    result_schema = authority.attempt_records._result_schema_descriptor()
    implementation_binding = authority.D7AuthorityArtifactBinding(artifact_role="implementation-registry", artifact_contract_id=official.D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_SCHEMA_VERSION, canonical_sha256=official.D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_SHA256, byte_count=official.D7_RECORDED_C1_IMPLEMENTATION_REGISTRY_BYTE_COUNT)
    parents = (authority.D7AuthorityArtifactBinding("recorded-c1", authority.D7_RECORDED_C1_SCHEMA_VERSION, authority.D7_RECORDED_C1_CANONICAL_SHA256, authority.D7_RECORDED_C1_BYTE_COUNT), authority.D7AuthorityArtifactBinding("recorded-c2", authority.D7_RECORDED_C2_SCHEMA_VERSION, authority.D7_RECORDED_C2_CANONICAL_SHA256, authority.D7_RECORDED_C2_BYTE_COUNT), parent.parent_protocol_binding)  # type: ignore[attr-defined]
    admission_candidate = authority.D7TargetAdmissionBindingCandidate(receipt_binding=family.admission_receipt_binding, generator_family_id=family.generator_family_id, construction_review_binding=family.construction_review_binding, admission_spec_binding=family.admission_spec_binding, source_runtime_receipt_sha256=closure.receipt_binding.canonical_sha256)  # type: ignore[attr-defined]
    design_candidate = authority.D7TargetFullDesignBindingCandidate(design_binding=full_design_binding, inventory_binding=_binding("full-inventory", official.D7_OFFICIAL_FULL_INVENTORY_SCHEMA_VERSION, full_inventory_source), inventory_sha256=sha256_bytes(full_inventory_source), official_seed_inventory_sha256=inventory.canonical_sha256, implementation_registry_sha256=implementation_binding.canonical_sha256, aggregation_sha256=sha256_bytes(aggregation_source), result_payload_schema_sha256=canonical_json_sha256(result_schema))
    runtime_candidate = authority.D7TargetSourceRuntimeBindingCandidate(receipt_binding=closure.receipt_binding, runtime_specification_sha256=runtime.canonical_sha256)  # type: ignore[attr-defined]
    replay_target = authority.D7ReplayTargetInputRecord(replay_target_id="d7-item22-spectral-moment-replay-target-v0-1", parent_bindings=parents, admission_receipt_binding=admission_candidate, official_seed_inventory_binding=inventory_binding, full_design_binding=design_candidate, implementation_registry_binding=implementation_binding, aggregation_binding=_binding("aggregation", official.D7_OFFICIAL_AGGREGATION_SCHEMA_VERSION, aggregation_source), result_payload_schema_binding=_binding("result-payload-schema", authority.attempt_records.D7_RESULT_SCHEMA_DESCRIPTOR_VERSION, canonical_json_bytes(result_schema)), execution_source_runtime_closure_binding=runtime_candidate)
    invocation = authority.D7SingleSupplierInvocationInputRecord(invocation_id="d7-item22-single-supplier-invocation-v0-1", claim_binding=_binding("exclusive-seed-supply-claim", claim.schema_version, claim.canonical_bytes), supplier_identity_binding=context["supplier"], official_seed_inventory_binding=inventory_binding)  # type: ignore[attr-defined,arg-type]
    claim_step = _step(authority.D7SeedSupplyTransition.EXCLUSIVE_SEED_SUPPLY_CLAIM, 4, "d7-item22-exclusive-claim-v0-1", context["chronology"][-1].artifact_binding, (invocation.claim_binding,))  # type: ignore[index,union-attr]
    invocation_step = _step(authority.D7SeedSupplyTransition.SINGLE_SUPPLIER_INVOCATION, 5, "d7-item22-single-invocation-v0-1", claim_step.artifact_binding, (invocation.artifact_binding,))
    publication_step = _step(authority.D7SeedSupplyTransition.ATOMIC_DESIGN_TARGET_PUBLICATION, 6, "d7-item22-atomic-target-publication-v0-1", invocation_step.artifact_binding, (inventory_binding, full_design_binding, _binding("replay-target", replay_target.schema_version, replay_target.canonical_bytes)))
    sources = {"official-seed-inventory": inventory.canonical_bytes, "full-inventory": full_inventory_source, "full-design": full_design_source, "replay-target": replay_target.canonical_bytes, "single-supplier-invocation": invocation.canonical_bytes}
    manifest = {"schema_version": D7_ITEM22_TRANSACTION_MANIFEST_SCHEMA_VERSION, "transaction_id": claim.claim_id, "claim_binding": invocation.claim_binding.to_dict(), "supplier_identity_binding": context["supplier"].to_dict(), "members": [{"artifact_role": role, "filename": filename, "canonical_sha256": sha256_bytes(sources[role]), "byte_count": len(sources[role])} for role, filename in D7_ITEM22_ATOMIC_TARGET_MEMBER_LAYOUT[:-1]], "runtime_specification": runtime.to_dict(), "source_runtime_closure": closure.to_dict(), "family_admission": family.to_dict(), "chronology": [record.to_dict() for record in (*context["chronology"], claim_step, invocation_step, publication_step)], "claim_ceiling": "level_0", "authority": {"launch_authorized": False, "execution_authorized": False, "scientific_claim_eligible": False}}  # type: ignore[attr-defined,misc,union-attr]
    sources["transaction-manifest"] = canonical_json_bytes(manifest)
    return sources


def _ensure_transaction_root(root: Path) -> durable._DirectoryAnchor:
    parent = durable._open_real_directory(root / D7_ITEM22_DIRECTORY_REPOSITORY_PATH, label="item-22 experiment directory")
    try:
        return durable._open_child_directory(parent, leaf="item22-seed-supply", label="item-22 transaction root", create=True)
    finally:
        os.close(parent.descriptor)


def _publish_target(transaction: durable._DirectoryAnchor, sources: dict[str, bytes]) -> PersistedQualificationIdentity:
    stage_leaf = f".published-target.{secrets.token_hex(12)}.staging"
    stage = None
    published = False
    try:
        durable._verify_anchor(transaction, label="item-22 transaction root")
        os.mkdir(stage_leaf, 0o700, dir_fd=transaction.descriptor)
        os.fsync(transaction.descriptor)
        stage = durable._open_child_directory(transaction, leaf=stage_leaf, label="item-22 target stage", create=False)
        for role, filename in D7_ITEM22_ATOMIC_TARGET_MEMBER_LAYOUT:
            source = sources[role]
            durable._write_canonical_file_no_replace(stage, filename, source, expected_sha256=sha256_bytes(source), maximum_bytes=MAX_D7_ITEM22_ARTIFACT_BYTES, label=f"item-22 {role}", allow_identical_existing=False)
        if set(os.listdir(stage.descriptor)) != {name for _role, name in D7_ITEM22_ATOMIC_TARGET_MEMBER_LAYOUT}:
            raise QualificationContractError("item-22 staged target member set differs")
        os.fsync(stage.descriptor)
        durable._verify_anchor(transaction, label="item-22 transaction root")
        durable._rename_file_no_replace(transaction, stage_leaf, "published-target")
        published = True
        os.fsync(transaction.descriptor)
        durable._verify_anchor(transaction, label="item-22 transaction root")
    finally:
        if stage is not None and not published:
            for name in os.listdir(stage.descriptor):
                observed = durable._relative_stat(stage, name)
                if observed is not None and stat.S_ISREG(observed.st_mode):
                    os.unlink(name, dir_fd=stage.descriptor)
            os.fsync(stage.descriptor)
        if stage is not None:
            os.close(stage.descriptor)
        if not published and durable._relative_stat(transaction, stage_leaf) is not None:
            os.rmdir(stage_leaf, dir_fd=transaction.descriptor)
            os.fsync(transaction.descriptor)
    manifest = sources["transaction-manifest"]
    return PersistedQualificationIdentity(path=transaction.path / "published-target" / "transaction-manifest.json", source_sha256=sha256_bytes(manifest), canonical_sha256=sha256_bytes(manifest), byte_count=len(manifest))


def _persist_abort(transaction: durable._DirectoryAnchor, claim: authority.D7ExclusiveSeedSupplyClaimInputRecord, *, phase: str, supplier_entry_possible: bool) -> None:
    source = canonical_json_bytes({
        "schema_version": D7_ITEM22_ABORT_EVIDENCE_SCHEMA_VERSION,
        "claim_binding": _binding("exclusive-seed-supply-claim", claim.schema_version, claim.canonical_bytes).to_dict(),
        "failed_phase": phase,
        "supplier_entry_possible": supplier_entry_possible,
        "target_published": False,
        "retry_authorized": False,
    })
    identity = durable._write_canonical_file_no_replace(
        transaction,
        "seed-supply-abort.json",
        source,
        expected_sha256=sha256_bytes(source),
        maximum_bytes=MAX_D7_ITEM22_ARTIFACT_BYTES,
        label="D7 item-22 abort evidence",
        allow_identical_existing=False,
    )
    durable._require_durable(identity, label="D7 item-22 abort evidence")


def run_d7_item22_seed_supply_transaction_no_replace(repository_root: str | Path, /) -> PersistedQualificationIdentity:
    """Claim once, invoke the fixed OS CSPRNG supplier once, and publish once."""

    root = item21._repository_root(repository_root)
    if observe_d7_item22_seed_supply_state(root) != "preclaim":
        raise QualificationContractError("item-22 transaction is already consumed")
    reanchor = _verify_reanchor_live(root)
    context = _foundation(root, reanchor)
    claim = context["claim"]
    transaction = _ensure_transaction_root(root)
    try:
        _verify_reanchor_live(root)
        durable._verify_anchor(transaction, label="item-22 transaction root")
        if os.listdir(transaction.descriptor):
            raise QualificationContractError("item-22 transaction lost its preclaim state")
        claim_identity = durable._write_canonical_file_no_replace(
            transaction,
            "exclusive-seed-supply-claim.json",
            claim.canonical_bytes,  # type: ignore[union-attr]
            expected_sha256=claim.canonical_sha256,  # type: ignore[union-attr]
            maximum_bytes=MAX_D7_ITEM22_ARTIFACT_BYTES,
            label="D7 item-22 exclusive seed-supply claim",
            allow_identical_existing=False,
        )
        durable._require_durable(claim_identity, label="D7 item-22 exclusive seed-supply claim")
        durable._verify_anchor(transaction, label="item-22 transaction root after claim")
        claim_rejoin = durable._read_bounded_file(transaction, "exclusive-seed-supply-claim.json", maximum_bytes=MAX_D7_ITEM22_ARTIFACT_BYTES, label="item-22 claim rejoin")
        if claim_rejoin[0] != claim.canonical_bytes or durable._identity(claim_rejoin[1]) != (claim_identity.device, claim_identity.inode):  # type: ignore[union-attr]
            raise QualificationContractError("item-22 durable claim identity or bytes differ before supplier entry")
        phase = "supplier-entry"
        supplier_entry_possible = True
        try:
            seed_values = _FIXED_SUPPLIER()
            phase = "target-construction"
            sources = _target_sources(context, seed_values)
            phase = "atomic-target-publication"
            identity = _publish_target(transaction, sources)
            _load_target(root, transaction, claim, context)  # type: ignore[arg-type]
            return identity
        except BaseException as error:
            if durable._relative_stat(transaction, "published-target") is None:
                try:
                    _persist_abort(transaction, claim, phase=phase, supplier_entry_possible=supplier_entry_possible)  # type: ignore[arg-type]
                except BaseException as abort_error:
                    if hasattr(error, "add_note"):
                        error.add_note(f"item-22 abort evidence persistence failed: {abort_error}")
            raise
    finally:
        os.close(transaction.descriptor)
