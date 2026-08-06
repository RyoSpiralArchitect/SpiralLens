"""Repository-only item-23 post-D6 descriptive-analysis lifecycle.

The runner has one fixed repository-root input and one fixed output path.  Its
analysis-value lane reads only the frozen post-D6 plan, the five historical
parents named by that plan, and the item-22 full-design-freeze receipt.  A
separate validation lane reads source/runtime records and seed-bearing target
Git tree metadata without reading or parsing those target contents.  The
runner neither accepts nor returns an authority capability and never reads a
D7 result, official D7 seed, model, or subject value.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path, PurePosixPath

from spirallens._repository_context import RepositoryContext
from spirallens.core.canonical import (
    CanonicalJsonError,
    canonical_json_bytes,
    canonical_json_sha256,
    parse_canonical_json,
    sha256_bytes,
)

from spirallens.qualification import confirmation_attempt_authority as authority
from spirallens.qualification import confirmation_attempt_persistence as durable
from spirallens.qualification import confirmation_fused_start as fused_start
from spirallens.qualification import confirmation_preseed_authority as item21
from spirallens.qualification import confirmation_seed_supply_contracts as item22
from spirallens.qualification.common import QualificationContractError

from . import _post_d6_outputs_01_12 as outputs_01_12
from . import _post_d6_outputs_13_27 as outputs_13_27

__all__: tuple[str, ...] = ()

_PLAN_PATH = "protocols/post_d6_descriptive_analysis_v0_1.json"
_PLAN_SHA256 = "9b1a8d9c3857fd18fff7b4dfb20a75eade2f56f4933e05126830669cd8ccb981"
_PLAN_SOURCE_COMMIT = "4838cef49997a70f1d6281b8097905510e7ec351"

_PROTOCOL_PATH = "protocols/d0_d5_f2_cartesian_selection_v0_1.json"
_TERMINAL_PATH = (
    "experiments/qualification/d0_d5_f2_cartesian_selection_v0_1/attempt/"
    "f63dcc162a896d0957cb7a8d437eace87eeadfc2574921819e7f98a27a704d58"
    ".selection-terminal/terminal-artifact.json"
)
_MANIFEST_PATH = (
    "experiments/qualification/d0_d5_f2_cartesian_selection_v0_1/attempt/"
    "f63dcc162a896d0957cb7a8d437eace87eeadfc2574921819e7f98a27a704d58"
    ".selection-terminal/terminal-manifest.json"
)
_CONSUMPTION_PATH = (
    "experiments/qualification/d0_d5_f2_cartesian_selection_v0_1/attempt/"
    "f63dcc162a896d0957cb7a8d437eace87eeadfc2574921819e7f98a27a704d58"
    ".selection-terminal/selection-consumption.json"
)
_D6_DECISION_PATH = (
    "experiments/qualification/d0_d5_f2_cartesian_selection_v0_1/"
    "d6-surrogate-advancement-decision.json"
)
_FREEZE_PATH = item22.D7_ITEM22_FULL_DESIGN_FREEZE_REPOSITORY_PATH

_RESULT_DIRECTORY = item22.D7_ITEM22_DIRECTORY_REPOSITORY_PATH
_RESULT_LEAF = "post-d6-descriptive-analysis-result.json"
_RESULT_PATH = f"{_RESULT_DIRECTORY}/{_RESULT_LEAF}"
_FREEZE_RELATIVE_PATH = PurePosixPath(_FREEZE_PATH).relative_to(_RESULT_DIRECTORY)
if len(_FREEZE_RELATIVE_PATH.parts) != 2:
    raise RuntimeError("item-23 freeze path must have one fixed child directory")
_FREEZE_DIRECTORY_LEAF, _FREEZE_LEAF = _FREEZE_RELATIVE_PATH.parts
_SOURCE_PATH = (
    "experiments/qualification/d7_spectral_moment_confirmation_v0_1/"
    "post_d6_code/confirmation_post_d6_descriptive.py"
)
_DERIVATION_PATHS = (
    "experiments/qualification/d7_spectral_moment_confirmation_v0_1/"
    "post_d6_code/_post_d6_outputs_01_12.py",
    "experiments/qualification/d7_spectral_moment_confirmation_v0_1/"
    "post_d6_code/_post_d6_outputs_13_27.py",
)
_DERIVE_OUTPUTS_01_12 = outputs_01_12.derive_outputs_01_12
_DERIVE_OUTPUTS_13_27 = outputs_13_27.derive_outputs_13_27

_PR9_COMMIT = "22eb9bd6bcd447f9a9afde0a7c26b8a1aef42993"
_PR10_COMMIT = "f869d53d890ae35b43c3dbca2ce6363c78fea367"
_PARENT_SPECS = (
    (
        "parent-protocol",
        _PROTOCOL_PATH,
        "9908bb83bb5ff5642416aa09d9e468e0a9499185cec9305e69a54143f2578bd1",
        _PR9_COMMIT,
        "protocol_path",
        "protocol_source_sha256",
        "pr9_merge_commit",
    ),
    (
        "parent-result",
        _TERMINAL_PATH,
        "44749d8d237b8b35874099c605f8de3d76130691ce8beb92e1ccf80fa368c13a",
        _PR9_COMMIT,
        "terminal_result_path",
        "terminal_result_sha256",
        "pr9_merge_commit",
    ),
    (
        "parent-manifest",
        _MANIFEST_PATH,
        "518b66d715cf9bd05e12de62cb5681ec63ec7f978fd4d2538ba3c2594deed4b1",
        _PR9_COMMIT,
        "terminal_manifest_path",
        "terminal_manifest_sha256",
        "pr9_merge_commit",
    ),
    (
        "parent-consumption",
        _CONSUMPTION_PATH,
        "a42ae9cffb6a2c87de6ed645e0982e85b09046a4ed5ad3f815a8a8ce38c0cadb",
        _PR9_COMMIT,
        "terminal_consumption_path",
        "terminal_consumption_sha256",
        "pr9_merge_commit",
    ),
    (
        "parent-d6-decision",
        _D6_DECISION_PATH,
        "c1c3fbbb9a06e8df120755dcf159e015636d96993bd6ec3a6792312618587a07",
        _PR10_COMMIT,
        "d6_decision_path",
        "d6_decision_sha256",
        "pr10_merge_commit",
    ),
)
_ALLOWED_INPUT_PATHS = tuple(spec[1] for spec in _PARENT_SPECS)
_FROZEN_TARGET_PATHS = (
    item22.D7_ITEM22_EXCLUSIVE_SEED_SUPPLY_CLAIM_REPOSITORY_PATH,
    *(
        f"{item22.D7_ITEM22_ATOMIC_TARGET_DIRECTORY_REPOSITORY_PATH}/{filename}"
        for _role, filename in item22.D7_ITEM22_ATOMIC_TARGET_MEMBER_LAYOUT
    ),
)
_RESULT_SCHEMA = "spirallens.postselection-descriptive-analysis-result.v0.1"
_SOURCE_BINDING_SCHEMA = "spirallens.d7-item23-post-d6-source-binding.v0.1"
_MAX_INPUT_BYTES = 32 * 1024 * 1024
_MAX_SOURCE_BYTES = 4 * 1024 * 1024
_MAX_RESULT_BYTES = 16 * 1024 * 1024
_POSTPUBLICATION_BINDING_ERROR = (
    "item-23 result may already be visible or durable; "
    "post-publication binding is unproved, so do not republish "
    "or infer rollback"
)

_OUTPUT_DENOMINATOR_ROWS = (
    ("parent-identity-table", "bound-parent-identity", 9, ()),
    ("gate-scope-table", "declared-gate", 9, ()),
    ("non-claim-table", "claim-or-validation-boundary-assertion", 22, ()),
    (
        "signed-margin-by-analytic-check",
        "persisted-analytic-check",
        78,
        ("family", "case", "graph", "metric"),
    ),
    ("fragility-without-threshold-change", "d1-family-summary", 2, ("family",)),
    (
        "core-no-core-abstain-matrix",
        "boundary-collapsed-d2-scientific-input",
        32,
        ("seed", "control", "stress"),
    ),
    (
        "boundary-repeat-exact-agreement",
        "d2-field-graph-boundary-pair",
        96,
        ("boundary", "field-graph"),
    ),
    (
        "amplitude-identifiability-support-separation",
        "required-boundary-collapsed-d2-field-graph-row",
        96,
        ("field-graph",),
    ),
    ("ambient-basis-error", "d3-family-summary", 2, ("family",)),
    ("reference-o2-error", "d3-family-law-summary", 4, ("family", "law")),
    (
        "loop-reversal-signed-total-error",
        "d3-family-summary",
        2,
        ("family",),
    ),
    (
        "array-versus-observable-law-separation",
        "d3-law-or-graph-check",
        7,
        ("family", "law", "graph"),
    ),
    (
        "three-by-three-field-cycle-graph-matrix",
        "execution-loop-role-layer",
        128,
        ("graph-pair", "loop-role"),
    ),
    (
        "loop-role-separated-primary-boundary-and-offcore-control-table",
        "execution-loop-role-layer",
        128,
        ("graph-pair", "loop-role"),
    ),
    (
        "diagonal-offdiagonal-separation",
        "loop-role-pair-class-summary",
        4,
        ("graph-pair", "loop-role"),
    ),
    (
        "adjacency-output-loop-total-effects",
        "execution-field-graph-pair",
        192,
        ("field-graph-pair", "cycle-graph", "loop-role"),
    ),
    (
        "support-aware-cell-table",
        "crossed-loop-cell",
        1152,
        ("graph-pair", "loop-role"),
    ),
    (
        "worst-case-by-stress-stratum",
        "stress-graph-pair-role-summary",
        108,
        ("overlapping-stress-stratum", "graph-pair", "loop-role"),
    ),
    (
        "loop-role-separated-worst-case-and-coverage-table",
        "stress-loop-role-summary",
        12,
        ("overlapping-stress-stratum", "loop-role"),
    ),
    (
        "coverage-abstention-recall-specificity-table",
        "stress-stratum-summary",
        6,
        ("overlapping-stress-stratum",),
    ),
    (
        "mandatory-prerequisite-failure-table",
        "prerequisite-execution",
        16,
        ("graph-pair", "loop-role"),
    ),
    (
        "required-nonvacuity-evidence",
        "loop-execution",
        64,
        ("field-graph-pair", "component"),
    ),
    (
        "abstention-reason-table",
        "typed-abstention-leaf",
        339,
        ("record-kind",),
    ),
    ("typed-failure-coverage", "typed-logical-route", 6, ("record-kind",)),
    (
        "shared-generator-seed-graph-boundary-implementation-oracle-map",
        "evidence-dependence-dimension",
        9,
        (),
    ),
    (
        "replication-versus-construction-diversity-table",
        "replication-or-diversity-category",
        5,
        (),
    ),
    ("epistemic-independence-nonclaim", "artifact-nonclaim", 1, ()),
)

_SCIENTIFIC_DENOMINATORS = {
    "parent-identity-table": ("artifact-interpretation-unit", 1, "whole-table"),
    "gate-scope-table": ("declared-gate-record", 9, "whole-table"),
    "non-claim-table": ("artifact-interpretation-unit", 1, "whole-table"),
    "signed-margin-by-analytic-check": ("d1-matched-class-unit", 2, "whole-table"),
    "fragility-without-threshold-change": ("d1-matched-class-unit", 2, "whole-table"),
    "core-no-core-abstain-matrix": ("d2-scientific-input-unit", 32, "whole-table"),
    "boundary-repeat-exact-agreement": ("d2-scientific-input-unit", 32, "whole-table"),
    "amplitude-identifiability-support-separation": (
        "d2-scientific-input-unit",
        32,
        "required-full-scope",
    ),
    "ambient-basis-error": ("d3-matched-class-unit", 2, "whole-table"),
    "reference-o2-error": ("d3-matched-class-unit", 2, "whole-table"),
    "loop-reversal-signed-total-error": ("d3-matched-class-unit", 2, "whole-table"),
    "array-versus-observable-law-separation": (
        "d3-matched-class-unit",
        2,
        "whole-table",
    ),
    "three-by-three-field-cycle-graph-matrix": (
        "d4-d5-loop-execution-unit",
        64,
        "whole-table",
    ),
    "loop-role-separated-primary-boundary-and-offcore-control-table": (
        "d4-d5-loop-execution-unit",
        64,
        "whole-table",
    ),
    "diagonal-offdiagonal-separation": (
        "d4-d5-loop-execution-unit",
        64,
        "whole-table",
    ),
    "adjacency-output-loop-total-effects": (
        "d4-d5-loop-execution-unit",
        64,
        "whole-table",
    ),
    "support-aware-cell-table": (
        "d4-d5-loop-execution-unit",
        64,
        "whole-table",
    ),
    "worst-case-by-stress-stratum": (
        "unique-loop-execution",
        32,
        "per-overlapping-stratum-row",
    ),
    "loop-role-separated-worst-case-and-coverage-table": (
        "unique-loop-execution",
        32,
        "per-overlapping-stratum-row",
    ),
    "coverage-abstention-recall-specificity-table": (
        "unique-loop-execution",
        32,
        "per-overlapping-stratum-row",
    ),
    "mandatory-prerequisite-failure-table": (
        "prerequisite-loop-execution",
        16,
        "whole-table",
    ),
    "required-nonvacuity-evidence": (
        "d4-d5-loop-execution-unit",
        64,
        "whole-table",
    ),
    "abstention-reason-table": ("not-an-inferential-sample", None, "typed-leaf-ledger"),
    "typed-failure-coverage": ("artifact-interpretation-unit", 1, "whole-table"),
    "shared-generator-seed-graph-boundary-implementation-oracle-map": (
        "artifact-interpretation-unit",
        1,
        "whole-table",
    ),
    "replication-versus-construction-diversity-table": (
        "construction-family-unit",
        1,
        "whole-table",
    ),
    "epistemic-independence-nonclaim": (
        "artifact-interpretation-unit",
        1,
        "whole-table",
    ),
}


def _mapping(value: object, *, label: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise QualificationContractError(f"{label} must be a string-keyed object")
    return value


def _sequence(value: object, *, label: str) -> list[object]:
    if type(value) is not list:
        raise QualificationContractError(f"{label} must be an array")
    return value


def _require_runtime_source_origin(root: Path) -> None:
    context = RepositoryContext(root=root)
    imported = (
        (__file__, _SOURCE_PATH),
        (outputs_01_12.__file__, _DERIVATION_PATHS[0]),
        (outputs_13_27.__file__, _DERIVATION_PATHS[1]),
    )
    if not all(
        context.matches_imported_file(
            imported_file=imported_file,
            repository_path=repository_path,
        )
        for imported_file, repository_path in imported
    ):
        raise QualificationContractError(
            "item-23 runtime source origin differs from the supplied checkout"
        )
    if (
        outputs_01_12.derive_outputs_01_12 is not _DERIVE_OUTPUTS_01_12
        or outputs_13_27.derive_outputs_13_27 is not _DERIVE_OUTPUTS_13_27
    ):
        raise QualificationContractError("item-23 derivation callable identity differs")
    for module_name, module in tuple(sys.modules.items()):
        if not (module_name == "spirallens" or module_name.startswith("spirallens.")):
            continue
        imported_file = getattr(module, "__file__", None)
        if imported_file is None:
            continue
        imported_path = Path(imported_file)
        parts = module_name.split(".")[1:]
        if imported_path.name == "__init__.py":
            repository_path = PurePosixPath(
                "src", "spirallens", *parts, "__init__.py"
            ).as_posix()
        elif imported_path.suffix == ".py" and parts:
            repository_path = PurePosixPath(
                "src", "spirallens", *parts[:-1], f"{parts[-1]}.py"
            ).as_posix()
        else:
            raise QualificationContractError(
                f"item-23 loaded SpiralLens module origin is unsupported: {module_name}"
            )
        if not context.matches_imported_file(
            imported_file=imported_file,
            repository_path=repository_path,
        ):
            raise QualificationContractError(
                f"item-23 loaded SpiralLens module origin differs: {module_name}"
            )


def _canonical_document(source: bytes, *, label: str) -> dict[str, object]:
    if type(source) is not bytes or not source or len(source) > _MAX_INPUT_BYTES:
        raise QualificationContractError(f"{label} exceeds its byte contract")
    try:
        parsed = parse_canonical_json(source, label=label)
    except CanonicalJsonError as error:
        raise QualificationContractError(str(error)) from error
    document = _mapping(parsed, label=label)
    if canonical_json_bytes(document) != source:
        raise QualificationContractError(f"{label} is not canonical JSON")
    return document


def _read_repository_file(
    root: Path,
    repository_path: str,
    *,
    maximum_bytes: int,
    label: str,
) -> bytes:
    relative = PurePosixPath(repository_path)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise QualificationContractError(f"{label} repository path is unsafe")
    parent = durable._open_real_directory(
        root.joinpath(*relative.parts[:-1]),
        label=f"{label} parent directory",
    )
    try:
        source, _identity = durable._read_bounded_file(
            parent,
            relative.parts[-1],
            maximum_bytes=maximum_bytes,
            label=label,
        )
        durable._verify_anchor(parent, label=f"{label} parent directory")
        return source
    finally:
        os.close(parent.descriptor)


def _read_fixed_json(
    root: Path,
    *,
    role: str,
    repository_path: str,
    expected_sha256: str,
    source_commit: str,
) -> tuple[dict[str, object], dict[str, object], bytes]:
    source = _read_repository_file(
        root,
        repository_path,
        maximum_bytes=_MAX_INPUT_BYTES,
        label=role,
    )
    observed_sha256 = sha256_bytes(source)
    if observed_sha256 != expected_sha256:
        raise QualificationContractError(f"{role} SHA-256 differs before parse")
    _require_unchanged_bound_path_history(
        root,
        repository_path=repository_path,
        source_commit=source_commit,
        label=role,
    )
    if item21._blob(root, source_commit, repository_path) != source:
        raise QualificationContractError(f"{role} differs from its plan-bound Git blob")
    document = _canonical_document(source, label=role)
    trace = {
        "role": role,
        "repository_path": repository_path,
        "source_commit": source_commit,
        "sha256": observed_sha256,
        "byte_count": len(source),
        "canonical_json": True,
    }
    return document, trace, source


def _require_unchanged_bound_path_history(
    root: Path,
    *,
    repository_path: str,
    source_commit: str,
    label: str,
) -> None:
    head = item21._head(root)
    item21._require_ancestor(root, source_commit, head, label=f"{label}-to-HEAD")
    expected_entry = item21._tree_entry(root, source_commit, repository_path)
    if expected_entry is None or expected_entry[:2] != ("100644", "blob"):
        raise QualificationContractError(
            f"{label} is not one regular plan-bound Git blob"
        )
    events = item21._bounded_path_history(
        root,
        revision="HEAD",
        repository_paths=(repository_path,),
        ancestry_path=False,
        label=f"{label} full reachable path history",
    )
    for event in dict.fromkeys((head, *events)):
        if _is_ancestor(root, event, source_commit):
            continue
        if not _is_ancestor(root, source_commit, event):
            raise QualificationContractError(
                f"{label} has a reachable incomparable path-history event"
            )
        if item21._tree_entry(root, event, repository_path) != expected_entry:
            raise QualificationContractError(
                f"{label} Git tree entry changed after its plan-bound commit"
            )


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    completed = item21._git(
        root,
        "merge-base",
        "--is-ancestor",
        ancestor,
        descendant,
        check=False,
    )
    if completed.returncode not in (0, 1):
        raise QualificationContractError("cannot compare item-23 Git ancestry")
    return completed.returncode == 0


def _validate_plan(plan: dict[str, object]) -> dict[str, object]:
    if (
        plan.get("schema_version")
        != "spirallens.postselection-descriptive-analysis-plan.v0.1"
        or plan.get("analysis_class") != "postselection_descriptive_only"
        or plan.get("status") != "frozen_not_run"
    ):
        raise QualificationContractError("frozen post-D6 plan identity differs")
    policy = _mapping(plan.get("input_policy"), label="plan input_policy")
    allowed = _sequence(policy.get("allowed_input_paths"), label="allowed_input_paths")
    if tuple(allowed) != _ALLOWED_INPUT_PATHS:
        raise QualificationContractError("post-D6 allowed_input_paths differ")
    if (
        policy.get("confirmation_value_access_authorized") is not False
        or policy.get("model_access_authorized") is not False
        or policy.get("pythia_engineering_value_access_authorized") is not False
        or policy.get("subject_value_access_authorized") is not False
    ):
        raise QualificationContractError("post-D6 forbidden input authority differs")
    future = _mapping(
        policy.get("future_required_input"), label="future_required_input"
    )
    if future != {
        "cardinality": 1,
        "class": "committed-d7-full-design-freeze-receipt",
        "d7_design_metadata_authorized": True,
        "d7_result_or_confirmation_values_authorized": False,
        "exact_repo_relative_path_frozen_before_runner_execution": True,
        "git_blob_commit_and_sha256_binding_required": True,
    }:
        raise QualificationContractError("post-D6 future input contract differs")
    publication = _mapping(
        plan.get("publication_contract"), label="publication_contract"
    )
    if (
        publication.get("all_work_packages_mandatory") is not True
        or publication.get("atomic_publish_required") is not True
        or publication.get("no_overwrite") is not True
        or publication.get("d7_use_forbidden") is not True
        or publication.get("claim_delta") != "none"
    ):
        raise QualificationContractError("post-D6 publication boundary differs")
    parent = _mapping(plan.get("parent_evidence"), label="plan parent_evidence")
    for spec in _PARENT_SPECS:
        _role, path, digest, commit, path_key, digest_key, commit_key = spec
        if (
            parent.get(path_key) != path
            or parent.get(digest_key) != digest
            or parent.get(commit_key) != commit
        ):
            raise QualificationContractError(f"plan-bound parent {path_key} differs")
    return parent


def _load_freeze(
    root: Path,
    *,
    transaction: durable._DirectoryAnchor | None = None,
) -> tuple[
    authority.D7FullDesignFreezeInputRecord,
    bytes,
    str,
    dict[str, object],
]:
    owned_transaction = transaction is None
    if transaction is None:
        relative = PurePosixPath(_FREEZE_PATH)
        transaction = durable._open_real_directory(
            root.joinpath(*relative.parts[:-1]),
            label="item-22 frozen transaction directory",
        )
    try:
        freeze_source, _identity = durable._read_bounded_file(
            transaction,
            _FREEZE_LEAF,
            maximum_bytes=item22.MAX_D7_ITEM22_ARTIFACT_BYTES,
            label="item-22 full-design-freeze receipt",
        )
        freeze_sha256 = sha256_bytes(freeze_source)
        freeze_document = _canonical_document(
            freeze_source,
            label="item-22 full-design-freeze receipt",
        )
        try:
            freeze = authority.D7FullDesignFreezeInputRecord.from_dict(freeze_document)
        except (TypeError, ValueError) as error:
            raise QualificationContractError(
                "item-22 freeze record is invalid"
            ) from error
        if freeze.canonical_bytes != freeze_source:
            raise QualificationContractError("item-22 freeze canonical bytes differ")
        durable._verify_anchor(
            transaction, label="item-22 frozen transaction directory"
        )
    finally:
        if owned_transaction:
            os.close(transaction.descriptor)
    introduction = item22._immutable_introduction(
        root,
        repository_path=_FREEZE_PATH,
        expected_source=freeze_source,
        after_commit=freeze.authorization_commit,
    )
    item21._require_ancestor(
        root,
        freeze.freeze_commit,
        freeze.authorization_commit,
        label="item23-target-freeze-to-authorization",
    )
    item21._require_path_absent_at_commit(root, introduction, _RESULT_PATH)
    if not owned_transaction:
        durable._verify_anchor(
            transaction, label="item-22 frozen transaction directory"
        )
    trace = {
        "role": "d7-full-design-freeze-receipt",
        "repository_path": _FREEZE_PATH,
        "source_commit": introduction,
        "sha256": freeze_sha256,
        "byte_count": len(freeze_source),
        "canonical_json": True,
    }
    return freeze, freeze_source, introduction, trace


def _immutable_tree_introduction(
    root: Path,
    *,
    repository_path: str,
    after_commit: str,
    frozen_commit: str,
) -> str:
    history = item21._bounded_path_history(
        root,
        revision="HEAD",
        repository_paths=(repository_path,),
        ancestry_path=False,
        label="item-23 frozen-target tree history",
    )
    candidates: list[str] = []
    for commit in history:
        try:
            row = (
                item21._git(root, "rev-list", "--parents", "-n", "1", commit)
                .stdout.decode("ascii")
                .strip()
                .split()
            )
        except UnicodeDecodeError as error:
            raise QualificationContractError(
                "frozen-target tree history is not ASCII"
            ) from error
        if item21._tree_entry(root, commit, repository_path) is not None and all(
            item21._tree_entry(root, parent, repository_path) is None
            for parent in row[1:]
        ):
            candidates.append(commit)
    if len(candidates) != 1:
        raise QualificationContractError(
            "frozen-target path lacks one immutable introduction"
        )
    introduction = candidates[0]
    item21._require_ancestor(
        root,
        after_commit,
        introduction,
        label="item23-reanchor-to-frozen-target-introduction",
    )
    item21._require_ancestor(
        root,
        introduction,
        frozen_commit,
        label="item23-frozen-target-introduction-to-freeze",
    )
    expected_entry = item21._tree_entry(root, frozen_commit, repository_path)
    if expected_entry is None or expected_entry[:2] != ("100644", "blob"):
        raise QualificationContractError(
            "frozen-target path is not one regular Git blob at the freeze commit"
        )
    for event in (*history, item21._head(root)):
        item21._require_ancestor(
            root,
            introduction,
            event,
            label="item23-frozen-target immutable history",
        )
        if item21._tree_entry(root, event, repository_path) != expected_entry:
            raise QualificationContractError(
                "frozen-target Git tree entry changed after introduction"
            )
    return introduction


def _verify_frozen_target_tree(
    root: Path,
    *,
    reanchor_introduction: str,
    freeze: authority.D7FullDesignFreezeInputRecord,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for repository_path in _FROZEN_TARGET_PATHS:
        introduction = _immutable_tree_introduction(
            root,
            repository_path=repository_path,
            after_commit=reanchor_introduction,
            frozen_commit=freeze.freeze_commit,
        )
        entry = item21._tree_entry(root, freeze.freeze_commit, repository_path)
        if entry is None:
            raise QualificationContractError("frozen-target Git tree entry is absent")
        rows.append(
            {
                "repository_path": repository_path,
                "introduction_commit": introduction,
                "freeze_commit": freeze.freeze_commit,
                "git_mode": entry[0],
                "git_object_type": entry[1],
                "git_object_id": entry[2],
                "byte_count": entry[3],
                "content_bytes_read": False,
                "content_parsed": False,
            }
        )
    return rows


def _source_file_binding(root: Path, repository_path: str) -> dict[str, object]:
    source = _read_repository_file(
        root,
        repository_path,
        maximum_bytes=_MAX_SOURCE_BYTES,
        label=f"item-23 source {repository_path}",
    )
    head = item21._head(root)
    if item21._blob(root, head, repository_path) != source:
        raise QualificationContractError("item-23 source differs from current HEAD")
    return {
        "repository_path": repository_path,
        "sha256": sha256_bytes(source),
        "byte_count": len(source),
        "git_blob_matches_head": True,
    }


def _source_binding(
    root: Path,
    *,
    reanchor: item21._LoadedArtifact,
    freeze_introduction: str,
) -> dict[str, object]:
    _require_runtime_source_origin(root)
    reanchor_document = reanchor.document
    lineage = _mapping(reanchor_document.get("lineage"), label="reanchor lineage")
    repository_only_paths = (_SOURCE_PATH, *_DERIVATION_PATHS)
    if set(repository_only_paths) != set(fused_start._REPOSITORY_ONLY_SOURCE_PATHS):
        raise QualificationContractError(
            "item-23 repository-only source closure differs"
        )
    item23_module = _source_file_binding(root, _SOURCE_PATH)
    derivation_modules = [
        _source_file_binding(root, repository_path)
        for repository_path in _DERIVATION_PATHS
    ]
    observation = _mapping(
        reanchor_document.get("source_observation"),
        label="reanchor source_observation",
    )
    raw_members = _sequence(observation.get("members"), label="reanchor source members")
    members: dict[str, dict[str, object]] = {}
    for raw_member in raw_members:
        member = _mapping(raw_member, label="reanchor source member")
        repository_path = member.get("repository_path")
        if type(repository_path) is not str or repository_path in members:
            raise QualificationContractError("reanchor source member paths differ")
        members[repository_path] = member
    for binding in (item23_module, *derivation_modules):
        repository_path = str(binding["repository_path"])
        member = members.get(repository_path)
        if (
            member is None
            or member.get("git_mode") != "100644"
            or member.get("sha256") != binding["sha256"]
            or member.get("byte_count") != binding["byte_count"]
        ):
            raise QualificationContractError(
                "item-23 source is absent from the exact reanchor closure"
            )
    return {
        "schema_version": _SOURCE_BINDING_SCHEMA,
        "item23_module": item23_module,
        "derivation_modules": derivation_modules,
        "item22_reanchor": {
            "repository_path": reanchor.repository_path,
            "sha256": reanchor.canonical_sha256,
            "byte_count": reanchor.byte_count,
            "introduction_commit": reanchor.introduction_commit,
            "source_commit": lineage.get("source_commit"),
        },
        "full_design_freeze_introduction_commit": freeze_introduction,
        "runtime_import_origin_joined": True,
        "verified": True,
    }


def _load_inputs(
    root: Path,
    *,
    verify_reanchor_live: bool,
) -> tuple[
    dict[str, object],
    dict[str, dict[str, object]],
    list[dict[str, object]],
    dict[str, object],
    dict[str, object],
    dict[str, object],
]:
    plan, plan_trace, _plan_source = _read_fixed_json(
        root,
        role="frozen-plan",
        repository_path=_PLAN_PATH,
        expected_sha256=_PLAN_SHA256,
        source_commit=_PLAN_SOURCE_COMMIT,
    )
    _validate_plan(plan)
    documents: dict[str, dict[str, object]] = {}
    traces = [plan_trace]
    for spec in _PARENT_SPECS:
        role, path, digest, commit, _path_key, _digest_key, _commit_key = spec
        document, trace, _source = _read_fixed_json(
            root,
            role=role,
            repository_path=path,
            expected_sha256=digest,
            source_commit=commit,
        )
        documents[role] = document
        traces.append(trace)
    freeze, freeze_source, freeze_introduction, freeze_trace = _load_freeze(root)
    traces.append(freeze_trace)
    if len(traces) != 7:
        raise QualificationContractError("item-23 read trace must contain seven files")
    reanchor = (
        item22._verify_reanchor_live(root)
        if verify_reanchor_live
        else item22._load_reanchor(root)
    )
    item21._require_ancestor(
        root,
        reanchor.introduction_commit,
        freeze.freeze_commit,
        label="item22-reanchor-to-target-freeze",
    )
    frozen_target_tree = _verify_frozen_target_tree(
        root,
        reanchor_introduction=reanchor.introduction_commit,
        freeze=freeze,
    )
    source_binding = _source_binding(
        root,
        reanchor=reanchor,
        freeze_introduction=freeze_introduction,
    )
    runtime_freeze_row = {
        "identity_kind": "d7-full-design-freeze-receipt",
        "storage_kind": "file",
        "repository_path": _FREEZE_PATH,
        "source_sha256": sha256_bytes(freeze_source),
        "canonical_sha256": freeze.canonical_sha256,
        "parent_field_path": "plan.input_policy.future_required_input",
        "verified": True,
    }
    validation_observations = {
        "analysis_input_read_trace_scope": "seven-declared-canonical-json-files",
        "analysis_input_read_trace_complete": True,
        "source_runtime_reanchor_verified_before_publication": True,
        "frozen_target_git_tree_identity_checked": True,
        "frozen_target_tree_rows": frozen_target_tree,
        "seed_bearing_target_content_bytes_read": False,
        "seed_bearing_target_content_parsed": False,
        "target_digest_graph_recomputed": False,
        "freeze_binding_digests_reauthenticated": False,
    }
    return (
        plan,
        documents,
        traces,
        source_binding,
        runtime_freeze_row,
        validation_observations,
    )


def _annotate_output_table_contracts(
    plan: dict[str, object],
    outputs: list[dict[str, object]],
) -> None:
    denominator_specs = {
        output_id: (row_unit, count, repeat_axes)
        for output_id, row_unit, count, repeat_axes in _OUTPUT_DENOMINATOR_ROWS
    }
    if len(denominator_specs) != 27 or set(denominator_specs) != set(
        _SCIENTIFIC_DENOMINATORS
    ):
        raise QualificationContractError("item-23 table-contract universe differs")
    unit_ids_by_output: dict[str, list[str]] = {}
    for raw in _sequence(plan.get("work_packages"), label="plan work_packages"):
        package = _mapping(raw, label="plan work package")
        unit_ids = _sequence(package.get("unit_ids"), label="work-package unit_ids")
        if not unit_ids or any(type(value) is not str for value in unit_ids):
            raise QualificationContractError("work-package unit_ids differ")
        for output_id in _sequence(
            package.get("required_outputs"), label="work-package required_outputs"
        ):
            if type(output_id) is not str or output_id in unit_ids_by_output:
                raise QualificationContractError("output-to-unit mapping differs")
            unit_ids_by_output[output_id] = list(unit_ids)
    if set(unit_ids_by_output) != set(denominator_specs):
        raise QualificationContractError("output-to-unit universe differs")
    for output in outputs:
        output_id = output.get("output_id")
        if type(output_id) is not str or output_id not in denominator_specs:
            raise QualificationContractError("derived output table contract is unknown")
        row_unit, required_count, repeat_axes = denominator_specs[output_id]
        available_count = output.get("row_count")
        if type(available_count) is not int or available_count < 0:
            raise QualificationContractError("derived output row_count is invalid")
        if output_id == "amplitude-identifiability-support-separation":
            if available_count != 6 or output.get("status") != "blocked":
                raise QualificationContractError("blocked D2 table denominator differs")
        elif available_count != required_count:
            raise QualificationContractError("available table denominator differs")
        scientific_unit, scientific_count, scientific_scope = _SCIENTIFIC_DENOMINATORS[
            output_id
        ]
        available_required_count = (
            0
            if output_id == "amplitude-identifiability-support-separation"
            else available_count
        )
        table_contract: dict[str, object] = {
            "unit_ids": unit_ids_by_output[output_id],
            "row_unit": row_unit,
            "required_row_denominator": required_count,
            "available_required_row_count": available_required_count,
            "persisted_output_row_count": available_count,
            "scientific_denominator": {
                "unit": scientific_unit,
                "count": scientific_count,
                "scope": scientific_scope,
            },
            "repeat_axes": list(repeat_axes),
            "inferential_sample_size_claimed": False,
        }
        if output_id == "amplitude-identifiability-support-separation":
            table_contract["partial_evidence"] = {
                "row_unit": "d2-confounder-cell",
                "row_count": 6,
                "counts_toward_required_row_denominator": False,
            }
        output["table_contract"] = table_contract


def _package_rows(
    plan: dict[str, object],
    outputs: list[dict[str, object]],
) -> list[dict[str, object]]:
    by_id = {str(row.get("output_id")): row for row in outputs}
    packages: list[dict[str, object]] = []
    for raw in _sequence(plan.get("work_packages"), label="plan work_packages"):
        package = _mapping(raw, label="plan work package")
        sequence = package.get("sequence")
        if type(sequence) is not int:
            raise QualificationContractError("work-package sequence must be an integer")
        required_ids = _sequence(
            package.get("required_outputs"),
            label="work-package required_outputs",
        )
        selected: list[dict[str, object]] = []
        for output_id in required_ids:
            if type(output_id) is not str or output_id not in by_id:
                raise QualificationContractError("work-package output mapping differs")
            output = by_id[output_id]
            selected.append(
                {
                    "sequence": output["sequence"],
                    "output_id": output_id,
                    "status": output["status"],
                    "row_count": output["row_count"],
                }
            )
        blocked = [row["output_id"] for row in selected if row["status"] == "blocked"]
        status = "insufficient" if blocked else "available"
        if (sequence == 3) != (status == "insufficient"):
            raise QualificationContractError("only package 3 may be insufficient")
        packages.append(
            {
                "sequence": sequence,
                "analysis_id": package.get("analysis_id"),
                "unit_ids": list(
                    _sequence(package.get("unit_ids"), label="work-package unit_ids")
                ),
                "status": status,
                "operational_status": "complete",
                "required_outputs": selected,
                "blocked_required_outputs": blocked,
                "missing_required_outputs": [],
            }
        )
    if len(packages) != 8:
        raise QualificationContractError("item-23 requires exactly eight packages")
    return packages


def _build_result(root: Path, *, verify_reanchor_live: bool) -> dict[str, object]:
    (
        plan,
        parents,
        traces,
        source_binding,
        runtime_freeze_row,
        validation_observations,
    ) = _load_inputs(root, verify_reanchor_live=verify_reanchor_live)
    arguments = {
        "plan": plan,
        "protocol": parents["parent-protocol"],
        "terminal": parents["parent-result"],
        "manifest": parents["parent-manifest"],
        "consumption": parents["parent-consumption"],
        "d6_decision": parents["parent-d6-decision"],
    }
    first = _DERIVE_OUTPUTS_01_12(
        **arguments,
        runtime_freeze_row=runtime_freeze_row,
    )
    second = _DERIVE_OUTPUTS_13_27(**arguments)
    outputs = [*first, *second]
    _annotate_output_table_contracts(plan, outputs)
    expected_ids = [
        output_id
        for raw in _sequence(plan.get("work_packages"), label="plan work_packages")
        for output_id in _sequence(
            _mapping(raw, label="plan work package").get("required_outputs"),
            label="required_outputs",
        )
    ]
    if (
        len(outputs) != 27
        or [row.get("sequence") for row in outputs] != list(range(1, 28))
        or [row.get("output_id") for row in outputs] != expected_ids
    ):
        raise QualificationContractError("derived 27-output universe differs")
    blocked = [
        str(row["output_id"]) for row in outputs if row.get("status") == "blocked"
    ]
    available_count = sum(row.get("status") == "available" for row in outputs)
    if available_count != 26 or blocked != [
        "amplitude-identifiability-support-separation"
    ]:
        raise QualificationContractError("item-23 availability pattern differs")
    packages = _package_rows(plan, outputs)
    trace_sha256 = canonical_json_sha256(traces)
    result_identity = canonical_json_sha256(
        {
            "plan_sha256": _PLAN_SHA256,
            "read_trace_sha256": trace_sha256,
            "source_binding_sha256": canonical_json_sha256(source_binding),
            "outputs_sha256": canonical_json_sha256(outputs),
        }
    )[:24]
    claim_boundary = dict(
        _mapping(plan.get("claim_boundary"), label="plan claim_boundary")
    )
    claim_boundary["d7_admission_input_authorized"] = False
    result: dict[str, object] = {
        "schema_version": _RESULT_SCHEMA,
        "result_id": f"post-d6-descriptive-{result_identity}",
        "analysis_class": "postselection_descriptive_only",
        "status": "insufficient",
        "operational_status": "complete",
        "claim_ceiling": "level_0",
        "claim_delta": "none",
        "plan_binding": traces[0],
        "full_design_freeze_binding": runtime_freeze_row,
        "source_binding": source_binding,
        "read_trace": traces,
        "read_trace_sha256": trace_sha256,
        "outputs": outputs,
        "available_output_count": 26,
        "blocked_output_count": 1,
        "blocked_required_outputs": blocked,
        "missing_required_outputs": [],
        "work_packages": packages,
        "claim_boundary": claim_boundary,
        "validation_observations": validation_observations,
        "input_observations": {
            "full_design_freeze_receipt_accessed": True,
            "d7_design_metadata_accessed": True,
            "d7_result_accessed": False,
            "d7_confirmation_value_accessed": False,
            "d7_seed_value_accessed": False,
            "seed_bearing_target_content_parsed": False,
            "model_accessed": False,
            "network_accessed": False,
            "subject_accessed": False,
        },
        "gate_states": {"d7": "not_run", "d8": "not_run"},
        "publication": {
            "repository_path": _RESULT_PATH,
            "atomic": True,
            "no_overwrite": True,
        },
    }
    _validate_result(result)
    return result


def _validate_result(document: dict[str, object]) -> None:
    if (
        document.get("schema_version") != _RESULT_SCHEMA
        or document.get("status") != "insufficient"
        or document.get("operational_status") != "complete"
        or document.get("claim_ceiling") != "level_0"
        or document.get("claim_delta") != "none"
        or document.get("available_output_count") != 26
        or document.get("blocked_output_count") != 1
        or document.get("blocked_required_outputs")
        != ["amplitude-identifiability-support-separation"]
        or document.get("missing_required_outputs") != []
    ):
        raise QualificationContractError("item-23 result boundary differs")
    outputs = _sequence(document.get("outputs"), label="item-23 outputs")
    packages = _sequence(document.get("work_packages"), label="item-23 packages")
    if len(outputs) != 27 or len(packages) != 8:
        raise QualificationContractError("item-23 result cardinality differs")
    for raw in outputs:
        output = _mapping(raw, label="item-23 output")
        table = _mapping(output.get("table_contract"), label="output table_contract")
        if (
            table.get("inferential_sample_size_claimed") is not False
            or type(table.get("row_unit")) is not str
            or type(table.get("required_row_denominator")) is not int
            or type(table.get("available_required_row_count")) is not int
            or type(table.get("persisted_output_row_count")) is not int
        ):
            raise QualificationContractError("item-23 output table contract differs")
    if [_mapping(row, label="item-23 package").get("status") for row in packages] != [
        "available",
        "available",
        "insufficient",
        "available",
        "available",
        "available",
        "available",
        "available",
    ]:
        raise QualificationContractError("item-23 package status pattern differs")
    traces = _sequence(document.get("read_trace"), label="item-23 read_trace")
    if len(traces) != 7 or canonical_json_sha256(traces) != document.get(
        "read_trace_sha256"
    ):
        raise QualificationContractError("item-23 read trace differs")


def _result_anchor(root: Path) -> durable._DirectoryAnchor:
    return durable._open_real_directory(
        root / _RESULT_DIRECTORY,
        label="item-23 result directory",
    )


def _require_pristine_result_history(root: Path) -> None:
    history = item21._bounded_path_history(
        root,
        revision="HEAD",
        repository_paths=(_RESULT_PATH,),
        ancestry_path=False,
        label="item-23 prepublication result history",
    )
    if history:
        raise QualificationContractError(
            "item-23 result namespace has prepublication Git history"
        )


def _require_postpublication_repository_state(root: Path, *, head: str) -> None:
    if item21._head(root) != head:
        raise QualificationContractError("Git HEAD changed during item-23 publication")
    status = item21._git(
        root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    ).stdout
    expected = b"?? " + os.fsencode(_RESULT_PATH) + b"\0"
    if status != expected:
        raise QualificationContractError(
            "repository state changed outside the item-23 result publication"
        )


def _read_result_source(root: Path) -> bytes:
    anchor = _result_anchor(root)
    try:
        source, _identity = durable._read_bounded_file(
            anchor,
            _RESULT_LEAF,
            maximum_bytes=_MAX_RESULT_BYTES,
            label="item-23 post-D6 result",
        )
        durable._verify_anchor(anchor, label="item-23 result directory")
        return source
    finally:
        os.close(anchor.descriptor)


def observe_d7_item23_post_d6_descriptive_state(
    repository_root: str | Path,
    /,
) -> str:
    """Return the fixed item-23 publication state after strict validation."""

    root = item21._repository_root(repository_root)
    _require_runtime_source_origin(root)
    anchor = _result_anchor(root)
    try:
        present = durable._relative_stat(anchor, _RESULT_LEAF) is not None
        durable._verify_anchor(anchor, label="item-23 result directory")
    finally:
        os.close(anchor.descriptor)
    if not present:
        _require_pristine_result_history(root)
        _load_inputs(root, verify_reanchor_live=True)
        return "ready"
    load_d7_item23_post_d6_descriptive(root)
    return "complete"


def run_d7_item23_post_d6_descriptive(
    repository_root: str | Path,
    /,
) -> durable.D7PersistedRecordIdentity:
    """Derive and atomically publish the fixed post-D6 result once."""

    root = item21._repository_root(repository_root)
    _require_runtime_source_origin(root)
    anchor = _result_anchor(root)
    transaction: durable._DirectoryAnchor | None = None
    publication_attempted = False
    try:
        present = durable._relative_stat(anchor, _RESULT_LEAF) is not None
        durable._verify_anchor(anchor, label="item-23 result directory")
    finally:
        os.close(anchor.descriptor)
    if present:
        raise QualificationContractError("item-23 result is already present")
    # Surface the stronger no-republication boundary before the generic clean-tree
    # precondition.  An interrupted publication intentionally leaves its visible
    # result as evidence and must never look retryable merely because that file is
    # the sole untracked worktree entry.
    item21._require_clean(root)
    _require_pristine_result_history(root)
    head = item21._head(root)
    result = _build_result(root, verify_reanchor_live=True)
    payload = canonical_json_bytes(result)
    if not payload or len(payload) > _MAX_RESULT_BYTES:
        raise QualificationContractError("item-23 result exceeds its byte contract")
    if item21._head(root) != head:
        raise QualificationContractError("Git HEAD changed during item-23 derivation")
    anchor = _result_anchor(root)
    try:
        if durable._relative_stat(anchor, _RESULT_LEAF) is not None:
            raise QualificationContractError("item-23 result is already present")
        durable._verify_anchor(anchor, label="item-23 result directory")
        # Hold this exact directory descriptor across the final source/freeze
        # revalidation and no-replace publication point.
        transaction = durable._open_child_directory(
            anchor,
            leaf=_FREEZE_DIRECTORY_LEAF,
            label="item-22 frozen transaction directory",
            create=False,
        )
        item22._verify_reanchor_live(root)
        durable._verify_anchor(anchor, label="item-23 result directory")
        durable._verify_anchor(
            transaction, label="item-22 frozen transaction directory"
        )
        _freeze, freeze_source, _introduction, _trace = _load_freeze(
            root,
            transaction=transaction,
        )
        if (
            sha256_bytes(freeze_source)
            != result["full_design_freeze_binding"]["source_sha256"]
        ):  # type: ignore[index]
            raise QualificationContractError(
                "item-22 freeze changed before publication"
            )
        if item21._head(root) != head:
            raise QualificationContractError(
                "Git HEAD changed before item-23 publication"
            )
        item21._require_clean(root)
        durable._verify_anchor(
            transaction, label="item-22 frozen transaction directory"
        )
        durable._verify_anchor(anchor, label="item-23 result directory")
        publication_attempted = True
        identity = durable._write_canonical_file_no_replace(
            anchor,
            _RESULT_LEAF,
            payload,
            expected_sha256=sha256_bytes(payload),
            maximum_bytes=_MAX_RESULT_BYTES,
            label="item-23 post-D6 descriptive result",
            allow_identical_existing=False,
        )
        durable._require_durable(identity, label="item-23 post-D6 descriptive result")
        post_source, _post_identity = durable._read_bounded_file(
            transaction,
            _FREEZE_LEAF,
            maximum_bytes=item22.MAX_D7_ITEM22_ARTIFACT_BYTES,
            label="item-22 post-publication full-design-freeze receipt",
        )
        if post_source != freeze_source:
            raise QualificationContractError(
                "item-22 freeze changed across item-23 publication"
            )
        durable._verify_anchor(
            transaction, label="item-22 frozen transaction directory"
        )
        durable._verify_anchor(anchor, label="item-23 result directory")
        _require_postpublication_repository_state(root, head=head)
        durable._verify_anchor(
            transaction, label="item-22 frozen transaction directory"
        )
        durable._verify_anchor(anchor, label="item-23 result directory")
        final_result_source, final_result_stat = durable._read_bounded_file(
            anchor,
            _RESULT_LEAF,
            maximum_bytes=_MAX_RESULT_BYTES,
            label="item-23 post-publication descriptive result",
        )
        if (
            final_result_source != payload
            or final_result_stat.st_dev != identity.device
            or final_result_stat.st_ino != identity.inode
            or final_result_stat.st_size != identity.byte_count
        ):
            raise QualificationContractError(
                "item-23 result identity changed after publication"
            )
        durable._verify_anchor(anchor, label="item-23 result directory")
        return identity
    except Exception as error:
        if publication_attempted:
            raise QualificationContractError(_POSTPUBLICATION_BINDING_ERROR) from error
        raise
    finally:
        close_error: OSError | None = None
        for current in (transaction, anchor):
            if current is None:
                continue
            try:
                os.close(current.descriptor)
            except OSError as error:
                if close_error is None:
                    close_error = error
        if close_error is not None:
            if publication_attempted:
                raise QualificationContractError(
                    _POSTPUBLICATION_BINDING_ERROR
                ) from close_error
            raise close_error


def load_d7_item23_post_d6_descriptive(
    repository_root: str | Path,
    /,
) -> dict[str, object]:
    """Load the exact worktree result and rederive it from fixed parents."""

    root = item21._repository_root(repository_root)
    _require_runtime_source_origin(root)
    source = _read_result_source(root)
    observed_sha256 = sha256_bytes(source)
    document = _canonical_document(source, label="item-23 post-D6 result")
    _validate_result(document)
    expected = _build_result(root, verify_reanchor_live=False)
    expected_source = canonical_json_bytes(expected)
    if source != expected_source or observed_sha256 != sha256_bytes(expected_source):
        raise QualificationContractError("item-23 result differs from rederivation")
    return document


def load_committed_d7_item23_post_d6_descriptive(
    repository_root: str | Path,
    /,
) -> dict[str, object]:
    """Load one uniquely introduced result unchanged through current HEAD."""

    root = item21._repository_root(repository_root)
    item21._require_clean(root)
    document = load_d7_item23_post_d6_descriptive(root)
    source = canonical_json_bytes(document)
    freeze_source = _read_repository_file(
        root,
        _FREEZE_PATH,
        maximum_bytes=item22.MAX_D7_ITEM22_ARTIFACT_BYTES,
        label="item-22 full-design-freeze receipt",
    )
    freeze_document = _canonical_document(
        freeze_source,
        label="item-22 full-design-freeze receipt",
    )
    freeze = authority.D7FullDesignFreezeInputRecord.from_dict(freeze_document)
    freeze_introduction = item22._immutable_introduction(
        root,
        repository_path=_FREEZE_PATH,
        expected_source=freeze_source,
        after_commit=freeze.authorization_commit,
    )
    result_introduction = item22._immutable_introduction(
        root,
        repository_path=_RESULT_PATH,
        expected_source=source,
        after_commit=freeze_introduction,
    )
    item21._require_ancestor(
        root,
        freeze_introduction,
        result_introduction,
        label="item23-freeze-to-result-introduction",
    )
    return document
