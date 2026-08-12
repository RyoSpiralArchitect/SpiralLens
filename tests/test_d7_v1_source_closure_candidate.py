from __future__ import annotations

import ast
from collections.abc import Iterator
from dataclasses import fields
import importlib.util
import inspect
import io
import os
from pathlib import Path
import shlex
import shutil
import stat
import subprocess
import sys
from types import ModuleType

import pytest

import spirallens
from spirallens import _repository_context as repository_context_module
import spirallens.qualification as qualification
from spirallens.core import canonical as canonical_module
from spirallens.core.canonical import canonical_json_bytes, sha256_bytes
from spirallens.qualification import common as common_module
from spirallens.qualification import confirmation_v1_materialization as materialization
from spirallens.qualification import confirmation_v1_records as records
from spirallens.qualification import (
    confirmation_v1_source_closure as source_closure,
)
from spirallens.qualification.common import QualificationContractError


REPOSITORY = Path(__file__).resolve().parents[1]
MODULE_REPOSITORY_PATH = (
    "src/spirallens/qualification/confirmation_v1_source_closure.py"
)
DESIGN_REFERENT_DOCUMENTS_REPOSITORY_PATH = (
    "src/spirallens/qualification/confirmation_v1_design_referent_documents.py"
)
DESIGN_REFERENT_DOCUMENTS_MODULE_NAME = (
    "spirallens.qualification.confirmation_v1_design_referent_documents"
)
ORIGIN_BOUND_MODULES = (
    (MODULE_REPOSITORY_PATH, source_closure),
    ("src/spirallens/_repository_context.py", repository_context_module),
    ("src/spirallens/core/canonical.py", canonical_module),
    ("src/spirallens/qualification/common.py", common_module),
)
FIXED_SOURCE_PATHS = {
    "pyproject.toml",
    "requirements-d7-runtime-lock.txt",
    "protocols/d7_v1_pre_item23_materialization_v0_1.json",
    "protocols/voy_v1_v9_strict_successor_route_v0_1.json",
    "scripts/prepare_d7_v1_launch.py",
    "scripts/run_d7_v1.py",
}
EXPECTED_C1_ID = "d7-v1-c1-source-set-candidate"
EXPECTED_C2_ID = "d7-v1-c2-source-closure-candidate"
EXPECTED_ROOT_ALL_SHA256 = (
    "a67ce5620fe4a53824cc2b3e0e0b4d46a452298a72fdaa8974ace14e97f13b7c"
)
EXPECTED_QUALIFICATION_ALL_SHA256 = (
    "4dab13d8a847400280682f61fcf0b03fdd9ad51c68d8909ab63a463d07579023"
)
EXPECTED_STATIC_FILES = {
    "pyproject.toml": (
        1_698,
        "2e1b8c37167a811c1cee82450700cfe39e13dff64f7cd0c0c6b02fba0d2550ec",
    ),
    "requirements-d7-runtime-lock.txt": (
        119,
        "e9f4dc2380e4729c9e86cd38a1d48bd15efda9304b0cbfa42bd8367fa6575ef7",
    ),
    "protocols/d7_v1_pre_item23_materialization_v0_1.json": (
        43_288,
        "13d013e007fa30775abb4cd092b264482207dcad23f772aecd966a51cbafbaad",
    ),
    "protocols/voy_v1_v9_strict_successor_route_v0_1.json": (
        13_806,
        "c8d28138c95d16ab96f508c2386de1d62360e1659057e0b8f7cbe8a380a90e35",
    ),
}
TRUE_AXES = {
    "structural_only",
    "git_source_tree_reenumerated",
    "c1_c2_rejoined",
}
FALSE_AXES = {
    "source_reviewed",
    "source_selected",
    "identity_authenticated",
    "runtime_environment_authenticated",
    "runtime_lock_conformity_verified",
    "runtime_dependency_closure_verified",
    "legacy_source_reuse_authorized",
    "source_closure_established",
    "source_tree_authenticated",
    "c1_persisted",
    "c2_persisted",
    "artifact_chronology_verified",
    "external_store_observed",
    "external_namespace_reserved",
    "seed_claim_persisted",
    "seed_values_present",
    "supplier_invoked",
    "attempt_reserved",
    "chronology_receipt_persisted",
    "materialization_authorized",
    "publication_authorized",
    "artifact_commit_created",
    "artifact_commit_verified",
    "authority_granted",
    "execution_authorized",
    "execution_started",
    "result_produced",
    "result_commit_created",
    "result_commit_verified",
    "scientific_claim_eligible",
}


def _load_materialization_test_helpers() -> ModuleType:
    name = "_spirallens_pr50_materialization_test_helpers"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    path = REPOSITORY / "tests" / "test_d7_v1_materialization.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load D7 v1 materialization test helpers")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


@pytest.fixture(autouse=True)
def _remove_test_repository_hardlinks(tmp_path: Path) -> Iterator[None]:
    try:
        yield
    finally:
        loaded = sys.modules.get(DESIGN_REFERENT_DOCUMENTS_MODULE_NAME)
        referents = sys.modules.get(
            "spirallens.qualification.confirmation_v1_full_design_referents"
        )
        authenticated = getattr(
            referents,
            "_AUTHENTICATED_REFERENT_DOCUMENTS_MODULE",
            None,
        )
        if loaded is not None and loaded is authenticated:
            workspace_leaf = REPOSITORY.joinpath(
                *DESIGN_REFERENT_DOCUMENTS_REPOSITORY_PATH.split("/")
            )
            loaded.__file__ = str(workspace_leaf)
            loaded.__spec__.origin = str(workspace_leaf)
        shutil.rmtree(tmp_path, ignore_errors=True)


def _case(tmp_path: Path, **options: object) -> object:
    helpers = _load_materialization_test_helpers()
    return helpers._build_case(
        tmp_path,
        isolated_clone=True,
        sparse_checkout=False,
        **options,
    )


def _git(repository: Path, *arguments: str, stdin: bytes | None = None) -> bytes:
    return subprocess.run(
        ("git", "-C", str(repository), *arguments),
        input=stdin,
        check=True,
        capture_output=True,
    ).stdout


def _run(repository: Path, *arguments: str) -> str:
    return _git(repository, *arguments).decode("utf-8").strip()


def _independent_source_oracle(
    repository: Path,
    source_commit: str,
) -> tuple[records.D7V1SourceMember, ...]:
    listing = _git(
        repository,
        "ls-tree",
        "-r",
        "-l",
        "-z",
        "--full-tree",
        source_commit,
        "--",
        "src/spirallens",
        *sorted(FIXED_SOURCE_PATHS),
    )
    entries: dict[str, tuple[str, str, str, int]] = {}
    for item in (record for record in listing.split(b"\0") if record):
        metadata, encoded_path = item.split(b"\t", 1)
        mode, kind, object_id, size = metadata.decode("ascii").split()
        repository_path = encoded_path.decode("utf-8")
        assert repository_path not in entries
        entries[repository_path] = (mode, kind, object_id, int(size))
    expected_paths = {
        path for path in entries if path.startswith("src/spirallens/")
    } | FIXED_SOURCE_PATHS
    assert set(entries) == expected_paths
    assert all(
        kind == "blob" and mode in {"100644", "100755"}
        for mode, kind, _object_id, _size in entries.values()
    )

    ordered = tuple(sorted(entries))
    request = b"".join(f"{entries[path][2]}\n".encode("ascii") for path in ordered)
    response = _git(repository, "cat-file", "--batch", stdin=request)
    stream = io.BytesIO(response)
    members: list[records.D7V1SourceMember] = []
    for repository_path in ordered:
        mode, _kind, object_id, declared_size = entries[repository_path]
        header = stream.readline().decode("ascii").split()
        assert header == [object_id, "blob", str(declared_size)]
        source = stream.read(declared_size)
        assert len(source) == declared_size
        assert stream.read(1) == b"\n"
        members.append(
            records.D7V1SourceMember(
                repository_path=repository_path,
                git_mode=mode,
                sha256=sha256_bytes(source),
                byte_count=len(source),
            )
        )
    assert stream.read() == b""
    return tuple(members)


def _path_state(path: Path) -> tuple[object, ...]:
    try:
        observed = path.lstat()
    except FileNotFoundError:
        return ("absent",)
    return (
        "present",
        observed.st_dev,
        observed.st_ino,
        observed.st_mode,
        observed.st_size,
        observed.st_mtime_ns,
    )


def _official_states(case: object) -> dict[Path, tuple[object, ...]]:
    helpers = _load_materialization_test_helpers()
    paths = {
        case.repository.joinpath(*path.split("/"))
        for path in helpers._coordinate_paths(case.protocol).values()
    }
    layout = case.protocol["coordinate_and_member_layout"]
    paths.add(case.repository.joinpath(*str(layout["descriptive_result"]).split("/")))
    external = case.protocol["external_durable_chronology_contract"]
    route_paths = external["route_future_external_coordinates"]
    paths.update(
        {
            Path(str(route_paths["external_staging_path"])),
            Path(str(route_paths["external_store_path"])),
        }
    )
    return {path: _path_state(path) for path in paths}


def _build(case: object) -> source_closure.D7V1SourceClosureCandidate:
    return source_closure._build_d7_v1_source_closure_candidate(
        case.context,
        source_commit=case.source_commit,
    )


def test_bounded_git_output_cap_cleans_up_and_is_reusable(tmp_path: Path) -> None:
    case = _case(tmp_path / "bounded-git")
    with pytest.raises(
        QualificationContractError,
        match=r"git rev-parse HEAD output exceeds its cap",
    ):
        materialization._git_bounded(case.context, 8, "rev-parse", "HEAD")

    observed = materialization._git_bounded(
        case.context,
        41,
        "rev-parse",
        "HEAD",
    )
    assert observed == f"{case.source_commit}\n".encode("ascii")
    assert len(observed) == 41


def test_choice_free_candidate_is_deterministic_exact_and_non_authorizing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path / "exact")
    assert _git(case.repository, "status", "--porcelain=v1", "-z") == b""
    assert not (case.repository / ".git/objects/info/alternates").exists()
    before = _official_states(case)
    assert set(before.values()) == {("absent",)}
    oracle = _independent_source_oracle(case.repository, case.source_commit)

    first = _build(case)
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    fake_git = fake_bin / "git"
    fake_git.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
    fake_git.chmod(0o755)
    with monkeypatch.context() as hostile:
        for name, value in {
            "PATH": str(fake_bin),
            "GIT_INDEX_FILE": str(tmp_path / "foreign-index"),
            "GIT_OBJECT_DIRECTORY": str(tmp_path / "foreign-objects"),
            "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(tmp_path / "alternate-objects"),
            "GIT_CONFIG_GLOBAL": str(tmp_path / "foreign-config"),
            "GIT_CONFIG_SYSTEM": str(tmp_path / "foreign-system-config"),
            "GIT_NO_REPLACE_OBJECTS": "0",
        }.items():
            hostile.setenv(name, value)
        second = _build(case)

    assert first.source_commit == case.source_commit
    assert first.source_members == oracle
    assert first.c1.canonical_bytes == second.c1.canonical_bytes
    assert first.c2.canonical_bytes == second.c2.canonical_bytes
    assert first.c1.to_dict()["record_id"] == EXPECTED_C1_ID
    assert first.c2.to_dict()["record_id"] == EXPECTED_C2_ID
    member_paths = {member.repository_path for member in first.source_members}
    assert FIXED_SOURCE_PATHS <= member_paths
    assert MODULE_REPOSITORY_PATH in member_paths
    assert "src/spirallens/qualification/confirmation_source_closure.py" in member_paths

    protocol = materialization._protocol_at_commit(case.context, case.source_commit)
    coordinates = materialization._coordinates(protocol)
    c1_payload = first.c1.to_dict()["payload"]
    expected_c1 = records.D7V1C1SourceSetRecord.create(
        record_id=EXPECTED_C1_ID,
        repository_path=coordinates["c1_source_set"],
        route_binding=records.D7V1ArtifactBinding.from_dict(
            c1_payload["route_binding"]
        ),
        source_members=oracle,
    )
    expected_c2 = records.D7V1C2SourceClosureReceipt.create(
        record_id=EXPECTED_C2_ID,
        repository_path=coordinates["c2_source_closure_receipt"],
        c1=expected_c1,
        source_commit=case.source_commit,
    )
    assert first.c1.canonical_bytes == expected_c1.canonical_bytes
    assert first.c2.canonical_bytes == expected_c2.canonical_bytes
    assert (
        materialization._verify_source_join(
            case.context,
            protocol,
            first.c1,
            first.c2,
        )
        == case.source_commit
    )

    boolean_axes = {
        name: value
        for name, value in vars(source_closure.D7V1SourceClosureCandidate).items()
        if type(value) is bool
    }
    assert boolean_axes == {
        **{name: True for name in TRUE_AXES},
        **{name: False for name in FALSE_AXES},
    }
    assert dict(first.c1.typestate)["source_closure_established"] is False
    assert dict(first.c2.typestate)["source_tree_authenticated"] is False
    with pytest.raises(QualificationContractError, match="closed builder"):
        source_closure.D7V1SourceClosureCandidate(
            source_commit=first.source_commit,
            c1=first.c1,
            c2=first.c2,
        )

    assert _git(case.repository, "status", "--porcelain=v1", "-z") == b""
    assert _official_states(case) == before


@pytest.mark.parametrize(
    "condition, expected",
    (
        ("wrong-head", "exact current repository HEAD"),
        ("staged", "completely clean repository"),
        ("unstaged", "completely clean repository"),
        ("untracked", "zero untracked repository files"),
    ),
)
def test_candidate_rejects_wrong_head_or_any_dirty_state(
    tmp_path: Path,
    condition: str,
    expected: str,
) -> None:
    case = _case(tmp_path / condition)
    asserted = case.source_commit
    if condition == "wrong-head":
        asserted = _run(case.repository, "rev-parse", "HEAD^")
    elif condition == "staged":
        (case.repository / "staged.txt").write_text("staged\n", encoding="utf-8")
        _run(case.repository, "add", "staged.txt")
    elif condition == "unstaged":
        readme = case.repository / "README.md"
        readme.write_bytes(readme.read_bytes() + b"unstaged\n")
    else:
        (case.repository / "untracked.txt").write_text("untracked\n", encoding="utf-8")
    with pytest.raises(QualificationContractError, match=expected):
        source_closure._build_d7_v1_source_closure_candidate(
            case.context,
            source_commit=asserted,
        )


@pytest.mark.parametrize(
    ("config_name", "config_value"),
    (
        ("core.trustctime", "false"),
        ("core.checkstat", "minimal"),
    ),
)
def test_candidate_rejects_stat_cache_config_before_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    config_name: str,
    config_value: str,
) -> None:
    case = _case(tmp_path / config_name.replace(".", "-"))
    _run(case.repository, "config", config_name, config_value)
    original = materialization._git
    calls: list[tuple[str, ...]] = []

    def observe_git(repository: object, *arguments: str) -> bytes:
        calls.append(arguments)
        return original(repository, *arguments)

    monkeypatch.setattr(materialization, "_git", observe_git)
    with pytest.raises(
        QualificationContractError,
        match="mutable local Git indirection",
    ):
        _build(case)
    assert calls
    assert all(arguments[0] != "status" for arguments in calls)


def test_candidate_forces_filemode_detection_over_local_config(tmp_path: Path) -> None:
    case = _case(tmp_path / "filemode")
    _run(case.repository, "config", "core.filemode", "false")
    readme = case.repository / "README.md"
    readme.chmod(readme.stat().st_mode | stat.S_IXUSR)

    assert _git(case.repository, "status", "--porcelain=v1", "-z") == b""
    with pytest.raises(
        QualificationContractError,
        match="completely clean repository",
    ):
        _build(case)


@pytest.mark.parametrize(
    "drift, expected",
    (
        ("head", "exact current repository HEAD"),
        ("status", "completely clean repository"),
    ),
)
def test_candidate_repeats_the_clean_head_gate_after_construction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    drift: str,
    expected: str,
) -> None:
    case = _case(tmp_path / drift)
    original = materialization._enumerate_choice_free_d7_v1_source_members
    drifted = False

    def enumerate_then_drift(*args: object, **kwargs: object) -> object:
        nonlocal drifted
        result = original(*args, **kwargs)
        if not drifted:
            drifted = True
            readme = case.repository / "README.md"
            readme.write_bytes(readme.read_bytes() + b"mid-build drift\n")
            if drift == "head":
                _run(case.repository, "add", "README.md")
                _run(case.repository, "commit", "--quiet", "-m", "mid-build drift")
        return result

    monkeypatch.setattr(
        materialization,
        "_enumerate_choice_free_d7_v1_source_members",
        enumerate_then_drift,
    )
    with pytest.raises(QualificationContractError, match=expected):
        _build(case)
    assert drifted


def test_candidate_rejects_a_symlink_or_any_future_root_member(
    tmp_path: Path,
) -> None:
    symlink_case = _case(tmp_path / "symlink")
    link = symlink_case.repository / "src/spirallens/pr50_symlink.py"
    os.symlink("__init__.py", link)
    _run(symlink_case.repository, "add", str(link.relative_to(symlink_case.repository)))
    _run(symlink_case.repository, "commit", "--quiet", "-m", "tracked symlink")
    symlink_case.source_commit = _run(symlink_case.repository, "rev-parse", "HEAD")
    with pytest.raises(QualificationContractError, match="ordinary 100644/100755"):
        _build(symlink_case)

    materialized_case = _case(
        tmp_path / "coordinate",
        result_present_at_source=True,
    )
    with pytest.raises(QualificationContractError, match="entirely absent"):
        _build(materialized_case)

    foreign_case = _case(tmp_path / "foreign-root-member")
    root = foreign_case.protocol["coordinate_and_member_layout"]["repository_root"]
    foreign_path = f"{root}/foreign.txt"
    foreign = foreign_case.repository.joinpath(*foreign_path.split("/"))
    foreign.parent.mkdir(parents=True, exist_ok=True)
    foreign.write_text("foreign root member\n", encoding="utf-8")
    _run(foreign_case.repository, "add", foreign_path)
    _run(
        foreign_case.repository,
        "commit",
        "--quiet",
        "-m",
        "foreign future-root member",
    )
    foreign_case.source_commit = _run(foreign_case.repository, "rev-parse", "HEAD")
    with pytest.raises(QualificationContractError, match="entirely absent"):
        _build(foreign_case)


@pytest.mark.parametrize("mutation", ("mode", "blob"))
def test_mode_or_blob_drift_cannot_be_laundered_across_source_commits(
    tmp_path: Path,
    mutation: str,
) -> None:
    case = _case(tmp_path / mutation)
    first = _build(case)
    repository_path = "src/spirallens/semantics/annotations.py"
    target = case.repository.joinpath(*repository_path.split("/"))
    if mutation == "mode":
        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    else:
        target.write_bytes(target.read_bytes() + b"\n# source-S blob drift\n")
    _run(case.repository, "add", repository_path)
    _run(case.repository, "commit", "--quiet", "-m", f"{mutation} drift")
    second_commit = _run(case.repository, "rev-parse", "HEAD")
    case.source_commit = second_commit
    second = _build(case)
    assert first.c1.canonical_sha256 != second.c1.canonical_sha256
    assert first.c2.canonical_sha256 != second.c2.canonical_sha256
    first_member = {item.repository_path: item for item in first.source_members}[
        repository_path
    ]
    second_member = {item.repository_path: item for item in second.source_members}[
        repository_path
    ]
    if mutation == "mode":
        assert (first_member.git_mode, second_member.git_mode) == ("100644", "100755")
        assert first_member.sha256 == second_member.sha256
    else:
        assert first_member.git_mode == second_member.git_mode
        assert first_member.sha256 != second_member.sha256

    protocol = materialization._protocol_at_commit(case.context, second_commit)
    forged_c2 = records.D7V1C2SourceClosureReceipt.create(
        record_id=EXPECTED_C2_ID,
        repository_path=materialization._coordinates(protocol)[
            "c2_source_closure_receipt"
        ],
        c1=first.c1,
        source_commit=second_commit,
    )
    with pytest.raises(QualificationContractError, match="exact choice-free Git tree"):
        materialization._verify_source_join(
            case.context,
            protocol,
            first.c1,
            forged_c2,
        )


@pytest.mark.parametrize(
    "attack",
    (
        "alternates",
        "graft",
        "shallow",
        "replace-ref",
        "core-worktree",
        "core-fsmonitor",
        "assume-unchanged",
        "skip-worktree",
    ),
)
def test_candidate_rejects_hidden_history_config_or_index_state(
    tmp_path: Path,
    attack: str,
) -> None:
    case = _case(tmp_path / attack)
    git_directory = Path(
        _run(case.repository, "rev-parse", "--path-format=absolute", "--git-dir")
    )
    common_directory = Path(
        _run(
            case.repository,
            "rev-parse",
            "--path-format=absolute",
            "--git-common-dir",
        )
    )
    if attack == "alternates":
        alternate = Path(
            _run(
                REPOSITORY,
                "rev-parse",
                "--path-format=absolute",
                "--git-path",
                "objects",
            )
        )
        path = common_directory / "objects/info/alternates"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{alternate}\n", encoding="utf-8")
    elif attack == "graft":
        path = common_directory / "info/grafts"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{case.source_commit}\n", encoding="ascii")
    elif attack == "shallow":
        (common_directory / "shallow").write_text(
            f"{case.source_commit}\n", encoding="ascii"
        )
    elif attack == "replace-ref":
        parent = _run(case.repository, "rev-parse", "HEAD^")
        _run(case.repository, "replace", case.source_commit, parent)
    elif attack == "core-worktree":
        foreign = tmp_path / "foreign-worktree"
        foreign.mkdir()
        _run(case.repository, "config", "core.worktree", str(foreign))
    elif attack == "core-fsmonitor":
        hook = tmp_path / "fsmonitor"
        hook.write_text("#!/bin/sh\nprintf '2\\n'\n", encoding="utf-8")
        hook.chmod(0o755)
        _run(case.repository, "config", "core.fsmonitor", str(hook))
    else:
        flag = (
            "--assume-unchanged" if attack == "assume-unchanged" else "--skip-worktree"
        )
        _run(case.repository, "update-index", flag, "README.md")
        readme = case.repository / "README.md"
        readme.write_bytes(readme.read_bytes() + b"hidden index drift\n")
    assert git_directory.is_dir()
    with pytest.raises(QualificationContractError):
        _build(case)


@pytest.mark.parametrize(
    ("attack", "expected"),
    (
        ("local-filter", "mutable local Git indirection"),
        ("root-attributes", "tracked Git attribute files"),
        ("nested-attributes", "tracked Git attribute files"),
        ("untracked-root-attributes", "zero untracked repository files"),
        ("untracked-nested-attributes", "zero untracked repository files"),
        ("info-attributes", "mutable Git admin indirection"),
        ("core-attributesfile", "mutable local Git indirection"),
    ),
)
def test_candidate_rejects_clean_filter_callback_surfaces_before_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attack: str,
    expected: str,
) -> None:
    case = _case(tmp_path / attack)
    sentinel = tmp_path / f"{attack}-filter-called"
    hook = tmp_path / f"{attack}-filter"
    hook.write_text(
        f"#!/bin/sh\nprintf invoked > {shlex.quote(str(sentinel))}\ncat\n",
        encoding="utf-8",
    )
    hook.chmod(0o755)
    global_config = tmp_path / f"{attack}-global-config"
    _run(
        case.repository,
        "config",
        "--file",
        str(global_config),
        "filter.spiral.clean",
        str(hook),
    )

    dirty_target = case.repository / "README.md"
    if attack in {
        "root-attributes",
        "nested-attributes",
        "untracked-root-attributes",
        "untracked-nested-attributes",
    }:
        if attack in {"root-attributes", "untracked-root-attributes"}:
            attributes_path = case.repository / ".gitattributes"
            attributes_source = "README.md filter=spiral\n"
        else:
            attributes_path = case.repository / "src/spirallens/.gitattributes"
            attributes_source = "__init__.py filter=spiral\n"
            dirty_target = case.repository / "src/spirallens/__init__.py"
        attributes_path.write_text(attributes_source, encoding="utf-8")
        if not attack.startswith("untracked-"):
            _run(
                case.repository,
                "add",
                str(attributes_path.relative_to(case.repository)),
            )
            _run(case.repository, "commit", "--quiet", "-m", f"{attack} fixture")
            case.source_commit = _run(case.repository, "rev-parse", "HEAD")
    elif attack == "info-attributes":
        attributes_path = Path(
            _run(
                case.repository,
                "rev-parse",
                "--path-format=absolute",
                "--git-path",
                "info/attributes",
            )
        )
        attributes_path.parent.mkdir(parents=True, exist_ok=True)
        attributes_path.write_text("README.md filter=spiral\n", encoding="utf-8")
    elif attack == "core-attributesfile":
        attributes_path = tmp_path / "external-attributes"
        attributes_path.write_text("README.md filter=spiral\n", encoding="utf-8")
        _run(
            case.repository,
            "config",
            "core.attributesfile",
            str(attributes_path),
        )
    else:
        _run(case.repository, "config", "filter.spiral.clean", str(hook))

    dirty_target.write_bytes(dirty_target.read_bytes() + b"dirty before status\n")
    assert not sentinel.exists()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))
    with pytest.raises(QualificationContractError, match=expected):
        _build(case)
    assert not sentinel.exists()


def test_candidate_rejects_ignored_raw_untracked_files_before_status(
    tmp_path: Path,
) -> None:
    case = _case(tmp_path / "ignored-untracked")
    gitignore = case.repository / ".gitignore"
    gitignore.write_text("ignored-source.bin\n", encoding="utf-8")
    _run(case.repository, "add", ".gitignore")
    _run(case.repository, "commit", "--quiet", "-m", "ignored fixture")
    case.source_commit = _run(case.repository, "rev-parse", "HEAD")
    ignored = case.repository / "ignored-source.bin"
    ignored.write_bytes(b"must not be hidden from the clean gate\n")

    assert _git(case.repository, "status", "--porcelain=v1", "-z") == b""
    raw_untracked = set(
        item
        for item in _git(
            case.repository, "ls-files", "--others", "-z", "--", "."
        ).split(b"\0")
        if item
    )
    assert raw_untracked == {b"ignored-source.bin"}
    with pytest.raises(
        QualificationContractError,
        match="zero untracked repository files",
    ):
        _build(case)


def test_candidate_rejects_a_clean_tracked_gitlink(tmp_path: Path) -> None:
    case = _case(tmp_path / "gitlink")
    submodule_source = tmp_path / "submodule-source"
    submodule_source.mkdir()
    _run(submodule_source, "init", "--quiet")
    _run(submodule_source, "config", "user.name", "SpiralLens test")
    _run(
        submodule_source,
        "config",
        "user.email",
        "spirallens-test@example.invalid",
    )
    (submodule_source / "README.md").write_text("gitlink fixture\n", encoding="utf-8")
    _run(submodule_source, "add", "README.md")
    _run(submodule_source, "commit", "--quiet", "-m", "gitlink fixture")

    repository_path = "src/spirallens/pr50_gitlink"
    _run(
        case.repository,
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        "--quiet",
        str(submodule_source),
        repository_path,
    )
    _run(case.repository, "commit", "--quiet", "-m", "tracked gitlink")
    case.source_commit = _run(case.repository, "rev-parse", "HEAD")

    assert _git(case.repository, "status", "--porcelain=v1", "-z") == b""
    staged = _git(case.repository, "ls-files", "--stage", "-z", "--", repository_path)
    assert staged.startswith(b"160000 ")
    with pytest.raises(QualificationContractError, match="Git submodule entries"):
        _build(case)


def test_candidate_rejects_non_descendant_history(
    tmp_path: Path,
) -> None:
    old_case = _case(
        tmp_path / "old-history",
        source_base_commit="2645ab360598c9ff4f1d9e628b9a9fe1857aedf6",
    )
    with pytest.raises(QualificationContractError, match="protocol merge commit"):
        _build(old_case)


@pytest.mark.parametrize(
    ("repository_path", "imported_module"),
    ORIGIN_BOUND_MODULES,
    ids=("builder", "repository-context", "canonical", "common"),
)
def test_candidate_rejects_same_bytes_from_an_adjacent_import_origin(
    tmp_path: Path,
    repository_path: str,
    imported_module: ModuleType,
) -> None:
    adjacent_case = _case(tmp_path / "adjacent-origin")
    target = adjacent_case.repository.joinpath(*repository_path.split("/"))
    assert imported_module.__file__ is not None
    imported = Path(imported_module.__file__)
    assert target.samefile(imported)
    source = target.read_bytes()
    target.unlink()
    target.write_bytes(source)
    assert not target.samefile(imported)
    assert (
        _git(
            adjacent_case.repository,
            "status",
            "--porcelain=v1",
            "-z",
        )
        == b""
    )
    with pytest.raises(QualificationContractError, match="import origin"):
        _build(adjacent_case)


def test_candidate_rejects_document_kernel_same_bytes_from_adjacent_spec_origin(
    tmp_path: Path,
) -> None:
    loaded_before = DESIGN_REFERENT_DOCUMENTS_MODULE_NAME in sys.modules
    specification = importlib.util.find_spec(DESIGN_REFERENT_DOCUMENTS_MODULE_NAME)
    assert specification is not None
    assert specification.origin is not None
    assert (DESIGN_REFERENT_DOCUMENTS_MODULE_NAME in sys.modules) is loaded_before
    specification_origin = Path(specification.origin)

    adjacent_case = _case(tmp_path / "document-kernel-adjacent-origin")
    target = adjacent_case.repository.joinpath(
        *DESIGN_REFERENT_DOCUMENTS_REPOSITORY_PATH.split("/")
    )
    assert target.samefile(specification_origin)
    source = target.read_bytes()
    target.unlink()
    target.write_bytes(source)
    assert not target.samefile(specification_origin)
    assert _git(adjacent_case.repository, "status", "--porcelain=v1", "-z") == b""
    with pytest.raises(QualificationContractError, match="import specification"):
        _build(adjacent_case)


def test_private_surface_dependencies_and_docs_retain_the_candidate_boundary() -> None:
    assert source_closure.__all__ == ()
    signature = inspect.signature(
        source_closure._build_d7_v1_source_closure_candidate
    ).parameters
    assert tuple(signature) == ("repository", "source_commit")
    assert signature["repository"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert signature["source_commit"].kind is inspect.Parameter.KEYWORD_ONLY
    assert tuple(
        field.name for field in fields(source_closure.D7V1SourceClosureCandidate)
    ) == (
        "source_commit",
        "c1",
        "c2",
        "_factory_token",
    )
    assert sha256_bytes(canonical_json_bytes(spirallens.__all__)) == (
        EXPECTED_ROOT_ALL_SHA256
    )
    assert sha256_bytes(canonical_json_bytes(qualification.__all__)) == (
        EXPECTED_QUALIFICATION_ALL_SHA256
    )
    for repository_path, (byte_count, expected_sha256) in EXPECTED_STATIC_FILES.items():
        source = REPOSITORY.joinpath(*repository_path.split("/")).read_bytes()
        assert len(source) == byte_count
        assert sha256_bytes(source) == expected_sha256

    tree = ast.parse(
        REPOSITORY.joinpath(*MODULE_REPOSITORY_PATH.split("/")).read_text(
            encoding="utf-8"
        )
    )
    imported: set[str] = set()
    calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module)
            elif node.level:
                imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
    assert imported == {
        "__future__",
        "dataclasses",
        "os",
        "pathlib",
        "typing",
        "spirallens",
        "spirallens._repository_context",
        "common",
        "confirmation_v1_materialization",
        "confirmation_v1_records",
    }
    assert {
        "open",
        "mkdir",
        "write_bytes",
        "write_text",
        "unlink",
        "remove",
        "rename",
        "replace",
        "rmtree",
        "supplier",
        "from_pretrained",
        "load_model",
        "produce_d7_v1_official_result",
        "_publish_d7_v1_pre_item23_records_no_replace",
        "_publish_d7_v1_result_no_replace",
    }.isdisjoint(calls)
    assert not hasattr(source_closure, "publish")
    assert not hasattr(source_closure, "materialize")

    before = {
        Path("/Users/ryohiga/SpiralReality/.spirallens-d7-v1-store.staging"): (
            _path_state(
                Path("/Users/ryohiga/SpiralReality/.spirallens-d7-v1-store.staging")
            )
        ),
        Path("/Users/ryohiga/SpiralReality/spirallens-d7-v1-store"): _path_state(
            Path("/Users/ryohiga/SpiralReality/spirallens-d7-v1-store")
        ),
    }
    probe_name = "spirallens.qualification._source_closure_import_side_effect_probe"
    probe_spec = importlib.util.spec_from_file_location(
        probe_name,
        REPOSITORY.joinpath(*MODULE_REPOSITORY_PATH.split("/")),
    )
    if probe_spec is None or probe_spec.loader is None:
        raise AssertionError("cannot create source-closure import probe")
    probe = importlib.util.module_from_spec(probe_spec)
    sys.modules[probe_name] = probe
    try:
        probe_spec.loader.exec_module(probe)
    finally:
        sys.modules.pop(probe_name, None)
    assert {path: _path_state(path) for path in before} == before

    readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")
    roadmap = (REPOSITORY / "docs/ROADMAP.md").read_text(encoding="utf-8")
    ledger = (REPOSITORY / "docs/EXPERIMENT_INTERPRETATION_LEDGER.md").read_text(
        encoding="utf-8"
    )
    changelog = (REPOSITORY / "docs/SCHEMA_CHANGELOG.md").read_text(encoding="utf-8")
    normalized_readme = " ".join(readme.split())
    normalized_roadmap = " ".join(roadmap.split())
    normalized_ledger = " ".join(ledger.split())
    normalized_changelog = " ".join(changelog.split())
    assert (
        "private builder can now form an in-memory C1/C2 structural candidate" in readme
    )
    assert "Runtime-lock membership does not attest" in normalized_roadmap
    assert "### 3.22 D7 v1 choice-free source-closure candidate builder" in ledger
    assert "The candidate does not prove repository review, select S" in (
        normalized_ledger
    )
    assert (
        "## 2026-08-10 — D7 v1 choice-free source-closure candidate builder"
        in changelog
    )
    assert "no schema, persisted C1/C2 instance, artifact, authority" in (
        normalized_changelog
    )
    assert all(
        "entire frozen v1 repository root" in document
        for document in (
            normalized_readme,
            normalized_roadmap,
            normalized_ledger,
            normalized_changelog,
        )
    )
    assert "current-tree observation, not artifact-chronology proof" in (
        normalized_readme
    )
    assert "current-tree fact does not prove artifact chronology" in (
        normalized_roadmap
    )
    assert (
        "current-tree observation, not unique-introduction or "
        "artifact-chronology verification" in normalized_ledger
    )
    assert (
        "asserted current tree. This does not attest unique introduction history or "
        "artifact chronology" in normalized_changelog
    )
