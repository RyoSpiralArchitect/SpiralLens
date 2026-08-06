from __future__ import annotations

import inspect
import os
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments.qualification.d7_spectral_moment_confirmation_v0_1.post_d6_code import (
    confirmation_post_d6_descriptive as item23,
)
from experiments.qualification.d7_spectral_moment_confirmation_v0_1.post_d6_code._post_d6_outputs_01_12 import (
    derive_outputs_01_12,
)
from experiments.qualification.d7_spectral_moment_confirmation_v0_1.post_d6_code._post_d6_outputs_13_27 import (
    derive_outputs_13_27,
)
from spirallens.core.canonical import canonical_json_bytes, parse_canonical_json
from spirallens import qualification
from spirallens.qualification import confirmation_attempt_authority as authority
from spirallens.qualification import confirmation_fused_start as fused_start
from spirallens.qualification import (
    confirmation_runtime_observation as runtime_observation,
)
from spirallens.qualification import confirmation_seed_supply_contracts as item22
from spirallens.qualification.common import QualificationContractError


REPOSITORY = Path(__file__).resolve().parents[1]
SOURCE_PATHS = (
    "src/spirallens/qualification/confirmation_fused_start.py",
    "src/spirallens/qualification/confirmation_preseed_authority.py",
    "experiments/qualification/d7_spectral_moment_confirmation_v0_1/"
    "post_d6_code/_post_d6_outputs_01_12.py",
    "experiments/qualification/d7_spectral_moment_confirmation_v0_1/"
    "post_d6_code/_post_d6_outputs_13_27.py",
    "experiments/qualification/d7_spectral_moment_confirmation_v0_1/"
    "post_d6_code/confirmation_post_d6_descriptive.py",
)


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _configure_git(root: Path) -> None:
    _git(root, "config", "user.name", "SpiralLens Test")
    _git(root, "config", "user.email", "spirallens@example.invalid")


def _clone(source: Path, destination: Path) -> Path:
    subprocess.run(
        ["git", "clone", "--quiet", "--no-hardlinks", str(source), str(destination)],
        check=True,
        capture_output=True,
        text=True,
    )
    _configure_git(destination)
    return destination


def _commit(root: Path, message: str, *paths: str) -> str:
    _git(root, "add", *paths)
    _git(root, "commit", "--quiet", "-m", message)
    return _git(root, "rev-parse", "HEAD")


_ITEM23_PROCESS_SOURCE = r"""
import errno
import os
import sys
import shutil
from pathlib import Path
from types import SimpleNamespace

from spirallens.qualification import confirmation_runtime_observation as runtime_observation

original_lock_verifier = runtime_observation._verify_exact_dependency_lock

def verify_exact_lock(source):
    pins = runtime_observation._parse_exact_dependency_lock(source)
    distributions = tuple(
        SimpleNamespace(metadata={"Name": pin.name}, version=pin.version)
        for pin in pins
    )
    return original_lock_verifier(source, distributions=distributions)

runtime_observation._verify_exact_dependency_lock = verify_exact_lock

from experiments.qualification.d7_spectral_moment_confirmation_v0_1.post_d6_code import confirmation_post_d6_descriptive as item23
from spirallens.qualification import confirmation_seed_supply_contracts as item22

root = Path.cwd()
action = sys.argv[1]

if action == "run-forbid-observer":
    def forbidden_seed_parsing_observer(_root):
        raise AssertionError("item23 must not enter item22's seed-parsing observer")
    item22.observe_d7_item22_seed_supply_state = forbidden_seed_parsing_observer
elif action == "run-swap-result-directory":
    original_load_freeze = item23._load_freeze
    def load_then_swap(*args, **kwargs):
        value = original_load_freeze(*args, **kwargs)
        if kwargs.get("transaction") is not None:
            directory = root / item23._RESULT_DIRECTORY
            moved = directory.with_name(directory.name + "-swapped")
            directory.rename(moved)
            directory.mkdir()
        return value
    item23._load_freeze = load_then_swap
elif action == "run-swap-transaction-after-publication":
    original_write = item23.durable._write_canonical_file_no_replace
    def write_then_swap(*args, **kwargs):
        identity = original_write(*args, **kwargs)
        directory = root / item23._RESULT_DIRECTORY / item23._FREEZE_DIRECTORY_LEAF
        moved = directory.with_name(directory.name + "-swapped")
        directory.rename(moved)
        shutil.copytree(moved, directory)
        return identity
    item23.durable._write_canonical_file_no_replace = write_then_swap
elif action == "run-hardlink-result-after-publication":
    original_write = item23.durable._write_canonical_file_no_replace
    def write_then_link(*args, **kwargs):
        identity = original_write(*args, **kwargs)
        alias = root.parent / f"{root.name}-result-hardlink"
        os.link(identity.path, alias)
        return identity
    item23.durable._write_canonical_file_no_replace = write_then_link
elif action == "run-swap-result-file-after-publication":
    original_write = item23.durable._write_canonical_file_no_replace
    def write_then_replace(*args, **kwargs):
        identity = original_write(*args, **kwargs)
        replacement = identity.path.with_name(identity.path.name + ".replacement")
        replacement.write_bytes(identity.path.read_bytes())
        os.replace(replacement, identity.path)
        return identity
    item23.durable._write_canonical_file_no_replace = write_then_replace
elif action == "run-oserror-after-publication":
    original_read = item23.durable._read_bounded_file
    def read_then_error(*args, **kwargs):
        if kwargs.get("label") == "item-23 post-publication descriptive result":
            raise OSError(errno.EIO, "injected post-publication read failure")
        return original_read(*args, **kwargs)
    item23.durable._read_bounded_file = read_then_error

if action == "observe":
    print(item23.observe_d7_item23_post_d6_descriptive_state(root))
elif action in {
    "run-forbid-observer",
    "run-hardlink-result-after-publication",
    "run-oserror-after-publication",
    "run-swap-result-file-after-publication",
    "run-swap-result-directory",
    "run-swap-transaction-after-publication",
}:
    print(item23.run_d7_item23_post_d6_descriptive(root).canonical_sha256)
elif action == "load":
    print(item23.load_d7_item23_post_d6_descriptive(root)["status"])
elif action == "load-committed":
    print(item23.load_committed_d7_item23_post_d6_descriptive(root)["operational_status"])
else:
    raise AssertionError(f"unknown item23 test action: {action}")
"""


def _item23_process(
    root: Path,
    action: str,
    *,
    check: bool = True,
    package_root: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        (str(package_root or root / "src"), str(root))
    )
    return subprocess.run(
        [sys.executable, "-c", _ITEM23_PROCESS_SOURCE, action],
        cwd=root,
        env=environment,
        check=check,
        capture_output=True,
        text=True,
    )


def _load(repository_path: str) -> dict[str, object]:
    value = parse_canonical_json(
        (REPOSITORY / repository_path).read_bytes(),
        label=repository_path,
    )
    assert isinstance(value, dict)
    return value


def _derivation_arguments() -> tuple[dict[str, object], dict[str, object]]:
    plan = _load("protocols/post_d6_descriptive_analysis_v0_1.json")
    parent = plan["parent_evidence"]
    assert isinstance(parent, dict)
    return plan, {
        "plan": plan,
        "protocol": _load(str(parent["protocol_path"])),
        "terminal": _load(str(parent["terminal_result_path"])),
        "manifest": _load(str(parent["terminal_manifest_path"])),
        "consumption": _load(str(parent["terminal_consumption_path"])),
        "d6_decision": _load(str(parent["d6_decision_path"])),
    }


def _freeze_row() -> dict[str, object]:
    return {
        "identity_kind": "d7-full-design-freeze-receipt",
        "storage_kind": "file",
        "repository_path": item22.D7_ITEM22_FULL_DESIGN_FREEZE_REPOSITORY_PATH,
        "source_sha256": "a" * 64,
        "canonical_sha256": "a" * 64,
        "parent_field_path": "plan.input_policy.future_required_input",
        "verified": True,
    }


@pytest.fixture(scope="module", autouse=True)
def exact_locked_test_runtime() -> Iterator[None]:
    patcher = pytest.MonkeyPatch()
    original = runtime_observation._verify_exact_dependency_lock

    def verify(source: bytes):
        pins = runtime_observation._parse_exact_dependency_lock(source)
        distributions = tuple(
            SimpleNamespace(metadata={"Name": pin.name}, version=pin.version)
            for pin in pins
        )
        return original(source, distributions=distributions)

    patcher.setattr(runtime_observation, "_verify_exact_dependency_lock", verify)
    yield
    patcher.undo()


def _matching_freeze(
    root: Path,
    *,
    freeze_commit: str,
    authorization_commit: str,
) -> authority.D7FullDesignFreezeInputRecord:
    target = root / item22.D7_ITEM22_ATOMIC_TARGET_DIRECTORY_REPOSITORY_PATH
    replay = authority.D7ReplayTargetInputRecord.from_dict(
        parse_canonical_json((target / "replay-target.json").read_bytes())
    )
    manifest = parse_canonical_json((target / "transaction-manifest.json").read_bytes())
    assert isinstance(manifest, dict)
    chronology = tuple(
        authority.D7ChronologyInputRecord.from_dict(value)
        for value in manifest["chronology"]
    )
    return authority.D7FullDesignFreezeInputRecord(
        freeze_id="test-item23-full-design-freeze",
        full_design_binding=replay.full_design_binding.design_binding,
        replay_target_binding=item22._binding(
            "replay-target", replay.schema_version, replay.canonical_bytes
        ),
        atomic_publication_binding=chronology[-1].artifact_binding,
        freeze_commit=freeze_commit,
        authorization_commit=authorization_commit,
    )


@pytest.fixture(scope="module")
def frozen_repository(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = _clone(REPOSITORY, tmp_path_factory.mktemp("item23-frozen") / "repository")
    for repository_path in SOURCE_PATHS:
        destination = root / repository_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPOSITORY / repository_path, destination)
    if _git(root, "status", "--short", "--", *SOURCE_PATHS):
        _commit(root, "item23 final source", *SOURCE_PATHS)
    else:
        _git(
            root,
            "commit",
            "--quiet",
            "--allow-empty",
            "-m",
            "item23 final source marker",
        )

    item22.issue_d7_item22_current_source_runtime_reanchor(root)
    _commit(
        root,
        "item23 reviewed source runtime reanchor",
        item22.D7_ITEM22_CURRENT_SOURCE_RUNTIME_REANCHOR_REPOSITORY_PATH,
    )

    supplier_patch = pytest.MonkeyPatch()
    values = iter((8_023_001, 8_023_002))
    supplier_patch.setattr(item22.secrets, "randbits", lambda bits: next(values))
    try:
        item22.run_d7_item22_seed_supply_transaction_no_replace(root)
    finally:
        supplier_patch.undo()
    target_commit = _commit(
        root,
        "item23 test target",
        item22.D7_ITEM22_SEED_SUPPLY_DIRECTORY_REPOSITORY_PATH,
    )

    marker = (
        root
        / item22.D7_ITEM22_DIRECTORY_REPOSITORY_PATH
        / "test-freeze-authorization.json"
    )
    marker.write_bytes(canonical_json_bytes({"authorized": True}))
    authorization_commit = _commit(
        root,
        "item23 test freeze authorization",
        marker.relative_to(root).as_posix(),
    )
    freeze = _matching_freeze(
        root,
        freeze_commit=target_commit,
        authorization_commit=authorization_commit,
    )
    freeze_path = root / item22.D7_ITEM22_FULL_DESIGN_FREEZE_REPOSITORY_PATH
    freeze_path.write_bytes(freeze.canonical_bytes)
    _commit(
        root,
        "item23 test committed freeze",
        item22.D7_ITEM22_FULL_DESIGN_FREEZE_REPOSITORY_PATH,
    )
    assert item22.observe_d7_item22_seed_supply_state(root) == "full-design-frozen"
    assert _item23_process(root, "observe").stdout.strip() == "ready"
    return root


@pytest.fixture(scope="module")
def committed_result_repository(
    frozen_repository: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[Path, bytes]:
    root = _clone(
        frozen_repository,
        tmp_path_factory.mktemp("item23-complete") / "repository",
    )
    _item23_process(root, "run-forbid-observer")
    result_path = root / item23._RESULT_PATH
    source = result_path.read_bytes()
    assert _item23_process(root, "load").stdout.strip() == "insufficient"
    _commit(root, "item23 committed descriptive result", item23._RESULT_PATH)
    assert _item23_process(root, "load-committed").stdout.strip() == "complete"
    return root, source


def test_pure_derivations_cover_the_exact_frozen_27_output_contract() -> None:
    plan, arguments = _derivation_arguments()
    outputs = [
        *derive_outputs_01_12(**arguments, runtime_freeze_row=_freeze_row()),
        *derive_outputs_13_27(**arguments),
    ]
    required = [
        output_id
        for package in plan["work_packages"]
        for output_id in package["required_outputs"]
    ]

    assert item23.__all__ == ()
    assert set((item23._SOURCE_PATH, *item23._DERIVATION_PATHS)) == set(
        fused_start._REPOSITORY_ONLY_SOURCE_PATHS
    )
    assert all(
        not repository_path.startswith("src/")
        for repository_path in fused_start._REPOSITORY_ONLY_SOURCE_PATHS
    )
    for name in (
        "observe_d7_item23_post_d6_descriptive_state",
        "run_d7_item23_post_d6_descriptive",
        "load_d7_item23_post_d6_descriptive",
        "load_committed_d7_item23_post_d6_descriptive",
    ):
        assert not hasattr(qualification, name)
        signature = inspect.signature(getattr(item23, name))
        assert tuple(signature.parameters) == ("repository_root",)
        assert (
            signature.parameters["repository_root"].kind
            is inspect.Parameter.POSITIONAL_ONLY
        )
    assert [row["sequence"] for row in outputs] == list(range(1, 28))
    assert [row["output_id"] for row in outputs] == required
    assert [row["row_count"] for row in outputs] == [
        9,
        9,
        22,
        78,
        2,
        32,
        96,
        6,
        2,
        4,
        2,
        7,
        128,
        128,
        4,
        192,
        1152,
        108,
        12,
        6,
        16,
        64,
        339,
        6,
        9,
        5,
        1,
    ]
    assert [row["status"] for row in outputs].count("available") == 26
    assert [row["status"] for row in outputs].count("blocked") == 1

    blocked = outputs[7]
    assert blocked["blocked_reason_codes"] == [
        "historical-main-d2-amplitude-identifiability-support-values-not-persisted"
    ]
    assert blocked["data"]["partial_row_count"] == 6
    assert blocked["data"]["missing_scientific_unit_count"] == 32
    assert blocked["data"]["missing_field_graph_row_count"] == 96
    assert blocked["data"]["persisted_descriptor_bundle_count"] == 192
    assert blocked["data"]["persisted_relevant_array_descriptor_count"] == 576
    assert blocked["data"]["rerun_or_current_code_reconstruction_performed"] is False
    assert outputs[6]["data"]["all_declared_outcomes_equal"] is True
    assert outputs[6]["data"]["all_blind_array_descriptors_equal"] is True
    assert (
        outputs[6]["data"]["comparison_scope"]
        == "declared-outcomes-and-blind-array-descriptors-not-byte-or-graph-identity"
    )
    assert all(
        all(row["blind_array_descriptor_equalities"].values())
        for row in outputs[6]["data"]["rows"]
    )
    assert all(
        not any(row["boundary_specific_identity_equalities"].values())
        for row in outputs[6]["data"]["rows"]
    )
    assert sum(row["cell_count"] for row in outputs[14]["data"]["rows"]) == 1152
    assert outputs[22]["data"]["logical_reason_occurrence_count"] == 915
    assert outputs[26]["data"]["rows"][0]["independent_confirmation_count"] == 0

    item23._annotate_output_table_contracts(plan, outputs)
    packages = item23._package_rows(plan, outputs)
    assert all(output["table_contract"]["unit_ids"] for output in outputs)
    blocked_table = outputs[7]["table_contract"]
    assert blocked_table["required_row_denominator"] == 96
    assert blocked_table["available_required_row_count"] == 0
    assert blocked_table["persisted_output_row_count"] == 6
    assert blocked_table["partial_evidence"] == {
        "row_unit": "d2-confounder-cell",
        "row_count": 6,
        "counts_toward_required_row_denominator": False,
    }
    assert packages[2]["status"] == "insufficient"
    assert all(package["unit_ids"] for package in packages)


def test_runner_publishes_one_rederivable_level_zero_insufficient_result(
    committed_result_repository: tuple[Path, bytes],
) -> None:
    root, source = committed_result_repository
    result = parse_canonical_json(source)
    assert isinstance(result, dict)
    assert result["schema_version"] == item23._RESULT_SCHEMA
    assert result["status"] == "insufficient"
    assert result["operational_status"] == "complete"
    assert result["claim_ceiling"] == "level_0"
    assert result["claim_delta"] == "none"
    assert result["available_output_count"] == 26
    assert result["blocked_output_count"] == 1
    assert len(result["read_trace"]) == 7
    assert result["source_binding"]["runtime_import_origin_joined"] is True
    assert all(
        output["table_contract"]["inferential_sample_size_claimed"] is False
        and output["table_contract"]["unit_ids"]
        and output["table_contract"]["required_row_denominator"] > 0
        for output in result["outputs"]
    )
    assert all(package["unit_ids"] for package in result["work_packages"])
    assert [row["status"] for row in result["work_packages"]] == [
        "available",
        "available",
        "insufficient",
        "available",
        "available",
        "available",
        "available",
        "available",
    ]
    assert result["input_observations"] == {
        "full_design_freeze_receipt_accessed": True,
        "d7_design_metadata_accessed": True,
        "d7_result_accessed": False,
        "d7_confirmation_value_accessed": False,
        "d7_seed_value_accessed": False,
        "seed_bearing_target_content_parsed": False,
        "model_accessed": False,
        "network_accessed": False,
        "subject_accessed": False,
    }
    validation = result["validation_observations"]
    assert validation["analysis_input_read_trace_complete"] is True
    assert validation["frozen_target_git_tree_identity_checked"] is True
    assert validation["seed_bearing_target_content_bytes_read"] is False
    assert validation["seed_bearing_target_content_parsed"] is False
    assert validation["target_digest_graph_recomputed"] is False
    assert validation["freeze_binding_digests_reauthenticated"] is False
    assert _item23_process(root, "observe").stdout.strip() == "complete"
    repeated = _item23_process(root, "run-forbid-observer", check=False)
    assert repeated.returncode != 0
    assert "already present" in repeated.stderr


def test_runner_rejects_a_committed_plan_parent_digest_change(
    frozen_repository: Path,
    tmp_path: Path,
) -> None:
    root = _clone(frozen_repository, tmp_path / "tampered-parent")
    terminal_path = root / item23._TERMINAL_PATH
    terminal_path.write_bytes(canonical_json_bytes({"tampered": True}))
    _commit(root, "tamper with frozen terminal", item23._TERMINAL_PATH)
    attempted = _item23_process(root, "run-forbid-observer", check=False)
    assert attempted.returncode != 0
    assert "SHA-256 differs before parse" in attempted.stderr
    assert not (root / item23._RESULT_PATH).exists()


@pytest.mark.parametrize("repository_path", (item23._PLAN_PATH, item23._TERMINAL_PATH))
def test_observer_rejects_bound_input_change_then_revert_history(
    frozen_repository: Path,
    tmp_path: Path,
    repository_path: str,
) -> None:
    root = _clone(frozen_repository, tmp_path / Path(repository_path).name)
    path = root / repository_path
    original = path.read_bytes()
    path.write_bytes(canonical_json_bytes({"transient_tamper": True}))
    _commit(root, "transiently change bound item23 input", repository_path)
    path.write_bytes(original)
    _commit(root, "restore bound item23 input bytes", repository_path)

    attempted = _item23_process(root, "observe", check=False)
    assert attempted.returncode != 0
    assert "Git tree entry changed after its plan-bound commit" in attempted.stderr


def test_observer_rejects_incomparable_reachable_parent_history(
    frozen_repository: Path,
    tmp_path: Path,
) -> None:
    root = _clone(frozen_repository, tmp_path / "incomparable-parent-history")
    branch = _git(root, "branch", "--show-current")
    terminal_path = root / item23._TERMINAL_PATH
    original = terminal_path.read_bytes()
    _git(
        root, "switch", "--quiet", "-c", "hostile-parent-side", f"{item23._PR9_COMMIT}^"
    )
    terminal_path.parent.mkdir(parents=True, exist_ok=True)
    terminal_path.write_bytes(canonical_json_bytes({"side_branch_tamper": True}))
    _commit(root, "incomparable parent-path tamper", item23._TERMINAL_PATH)
    _git(root, "switch", "--quiet", branch)
    merged = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "merge",
            "--no-ff",
            "--no-commit",
            "hostile-parent-side",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert merged.returncode != 0
    terminal_path.write_bytes(original)
    _commit(
        root, "resolve merge while retaining canonical parent", item23._TERMINAL_PATH
    )

    attempted = _item23_process(root, "observe", check=False)
    assert attempted.returncode != 0
    assert "reachable incomparable path-history event" in attempted.stderr


def test_item23_rejects_whole_and_mixed_adjacent_checkout_origins(
    frozen_repository: Path,
) -> None:
    with pytest.raises(QualificationContractError, match="runtime source origin"):
        item23.observe_d7_item23_post_d6_descriptive_state(frozen_repository)

    mixed = _item23_process(
        frozen_repository,
        "observe",
        check=False,
        package_root=REPOSITORY / "src",
    )
    assert mixed.returncode != 0
    assert "loaded SpiralLens module origin differs" in mixed.stderr


def test_prepublication_real_directory_swap_cannot_publish(
    frozen_repository: Path,
    tmp_path: Path,
) -> None:
    root = _clone(frozen_repository, tmp_path / "prepublication-directory-swap")
    attempted = _item23_process(root, "run-swap-result-directory", check=False)
    assert attempted.returncode != 0
    experiment = root / item23._RESULT_DIRECTORY
    moved = experiment.with_name(experiment.name + "-swapped")
    assert not (experiment / item23._RESULT_LEAF).exists()
    assert not (moved / item23._RESULT_LEAF).exists()


def test_postpublication_transaction_swap_is_visible_but_never_successful(
    frozen_repository: Path,
    tmp_path: Path,
) -> None:
    root = _clone(frozen_repository, tmp_path / "postpublication-transaction-swap")
    attempted = _item23_process(
        root,
        "run-swap-transaction-after-publication",
        check=False,
    )
    assert attempted.returncode != 0
    assert "may already be visible or durable" in attempted.stderr
    assert (root / item23._RESULT_PATH).is_file()
    repeated = _item23_process(root, "run-forbid-observer", check=False)
    assert repeated.returncode != 0
    assert "already present" in repeated.stderr


@pytest.mark.parametrize(
    "action",
    (
        "run-hardlink-result-after-publication",
        "run-swap-result-file-after-publication",
        "run-oserror-after-publication",
    ),
)
def test_postpublication_result_binding_failure_is_visible_but_never_successful(
    frozen_repository: Path,
    tmp_path: Path,
    action: str,
) -> None:
    root = _clone(frozen_repository, tmp_path / action)
    attempted = _item23_process(root, action, check=False)
    assert attempted.returncode != 0
    assert "may already be visible or durable" in attempted.stderr
    assert (root / item23._RESULT_PATH).is_file()
    repeated = _item23_process(root, "run-forbid-observer", check=False)
    assert repeated.returncode != 0
    assert "already present" in repeated.stderr


def test_result_must_be_absent_at_the_freeze_introduction(
    frozen_repository: Path,
    tmp_path: Path,
) -> None:
    root = _clone(frozen_repository, tmp_path / "preexisting-result")
    freeze_source = (
        root / item22.D7_ITEM22_FULL_DESIGN_FREEZE_REPOSITORY_PATH
    ).read_bytes()
    freeze_introduction = _git(root, "rev-parse", "HEAD")
    authorization_commit = _git(root, "rev-parse", f"{freeze_introduction}^")
    _git(root, "switch", "--quiet", "-c", "preexisting-at-freeze", authorization_commit)
    result_path = root / item23._RESULT_PATH
    result_path.write_bytes(canonical_json_bytes({"premature": True}))
    (root / item22.D7_ITEM22_FULL_DESIGN_FREEZE_REPOSITORY_PATH).write_bytes(
        freeze_source
    )
    _commit(
        root,
        "introduce freeze with premature result",
        item22.D7_ITEM22_FULL_DESIGN_FREEZE_REPOSITORY_PATH,
        item23._RESULT_PATH,
    )
    result_path.unlink()
    _commit(root, "remove premature result", item23._RESULT_PATH)

    assert item22.observe_d7_item22_seed_supply_state(root) == "full-design-frozen"
    attempted = _item23_process(root, "run-forbid-observer", check=False)
    assert attempted.returncode != 0
    assert any(
        value in attempted.stderr for value in ("history", "absent", "too early")
    )


def test_committed_loader_rejects_change_then_revert_history(
    committed_result_repository: tuple[Path, bytes],
    tmp_path: Path,
) -> None:
    source_root, original = committed_result_repository
    root = _clone(source_root, tmp_path / "changed-result-history")
    result_path = root / item23._RESULT_PATH
    result_path.write_bytes(canonical_json_bytes({"changed": True}))
    _commit(root, "change item23 result", item23._RESULT_PATH)
    result_path.write_bytes(original)
    _commit(root, "restore item23 result bytes", item23._RESULT_PATH)

    assert _item23_process(root, "load").stdout.strip() == "insufficient"
    attempted = _item23_process(root, "load-committed", check=False)
    assert attempted.returncode != 0
    assert "changed after introduction" in attempted.stderr


def test_observer_rejects_a_symlinked_experiment_ancestor(
    frozen_repository: Path,
    tmp_path: Path,
) -> None:
    root = _clone(frozen_repository, tmp_path / "symlinked-experiment")
    experiment = root / item22.D7_ITEM22_DIRECTORY_REPOSITORY_PATH
    external = tmp_path / "external-experiment"
    experiment.rename(external)
    experiment.symlink_to(external, target_is_directory=True)

    attempted = _item23_process(root, "observe", check=False)
    assert attempted.returncode != 0
    assert any(value in attempted.stderr for value in ("real directory", "symbolic"))
