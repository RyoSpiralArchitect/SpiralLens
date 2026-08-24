from __future__ import annotations

import ast
import errno
import importlib
import inspect
import os
from pathlib import Path
import shutil
import stat
import sys
from collections.abc import Iterator
from typing import NoReturn
from unittest.mock import patch

import pytest

from spirallens.core.canonical import sha256_bytes
from spirallens.qualification import confirmation_v1_materialization as materialization
from spirallens.qualification import (
    confirmation_v1_full_design_referents as full_design_referents,
)
from spirallens.qualification import confirmation_v1_result_publication as publication
from spirallens.qualification import confirmation_v1_records as records
from spirallens.qualification.common import QualificationContractError

from test_d7_v1_materialization import (
    REPOSITORY,
    _Case,
    _build_case,
    _commit_a,
    _exact_descriptive_result,
    _run,
    _verify_commit_b,
    _write,
)


PUBLISHER_REPOSITORY_PATH = (
    "src/spirallens/qualification/confirmation_v1_result_publication.py"
)
PUBLISHER_MODULE_PATH = REPOSITORY.joinpath(*PUBLISHER_REPOSITORY_PATH.split("/"))

_FALSE_RECEIPT_AXES = (
    "retry_authorized",
    "cleanup_authorized",
    "authority_granted",
    "materialization_authorized",
    "result_commit_b_created",
    "result_commit_b_verified",
    "execution_authorized",
    "scientific_claim_eligible",
)
_TRUE_RECEIPT_AXES = (
    "artifact_commit_a_verified",
    "result_published",
    "namespace_atomic",
    "result_fsync_completed",
    "parent_directory_fsync_completed",
    "structural_only",
)


@pytest.fixture(autouse=True)
def _remove_test_repository_hardlinks(tmp_path: Path) -> Iterator[None]:
    """Remove same-file test clones before a later live-repository check."""

    def restore_authenticated_referent_documents_origin() -> None:
        loaded = sys.modules.get(
            "spirallens.qualification.confirmation_v1_design_referent_documents"
        )
        authenticated = getattr(
            full_design_referents,
            "_AUTHENTICATED_REFERENT_DOCUMENTS_MODULE",
            None,
        )
        if loaded is not None and loaded is authenticated:
            workspace_leaf = REPOSITORY / (
                "src/spirallens/qualification/"
                "confirmation_v1_design_referent_documents.py"
            )
            loaded.__file__ = str(workspace_leaf)
            if loaded.__spec__ is not None:
                loaded.__spec__.origin = str(workspace_leaf)

    restore_authenticated_referent_documents_origin()
    try:
        yield
    finally:
        restore_authenticated_referent_documents_origin()
        shutil.rmtree(tmp_path)


def _result_path(case: _Case) -> Path:
    layout = case.protocol["coordinate_and_member_layout"]
    assert isinstance(layout, dict)
    return case.repository.joinpath(*str(layout["descriptive_result"]).split("/"))


def _stage_path(case: _Case) -> Path:
    expected = _exact_descriptive_result(case)
    destination = _result_path(case)
    return destination.with_name(
        f".{destination.name}.private-stage.{expected.canonical_sha256}"
    )


def _publish(
    case: _Case,
    *,
    source_commit: str | None = None,
    artifact_commit: str | None = None,
) -> publication.D7V1PrivateResultPublicationReceipt:
    with patch.object(
        materialization,
        "_default_external_reader",
        case.external_reader,
    ):
        return publication._publish_d7_v1_descriptive_result_no_replace(
            case.context,
            source_commit=source_commit or case.source_commit,
            artifact_commit=artifact_commit
            or _run(case.repository, "rev-parse", "HEAD"),
        )


def _assert_failure_axes(error: publication.D7V1ResultPublicationFailure) -> None:
    assert error.retry_authorized is False
    assert error.cleanup_authorized is False
    assert error.resume_authorized is False
    for field in _FALSE_RECEIPT_AXES[2:]:
        assert not hasattr(error, field)


def _assert_no_result_namespace(case: _Case) -> None:
    destination = _result_path(case)
    assert not destination.exists()
    assert not destination.is_symlink()
    if destination.parent.is_dir():
        reserved_prefix = f".{destination.name}.private-stage."
        assert not any(
            entry.name.startswith(reserved_prefix)
            for entry in destination.parent.iterdir()
        )


def _path_state(path: Path) -> tuple[object, ...]:
    try:
        value = os.lstat(path)
    except FileNotFoundError:
        return ("absent",)
    payload = path.read_bytes() if stat.S_ISREG(value.st_mode) else None
    return (value.st_mode, value.st_ino, value.st_size, value.st_mtime_ns, payload)


def _official_paths() -> tuple[Path, ...]:
    protocol = materialization._load_d7_v1_materialization_protocol(
        materialization.RepositoryContext(root=REPOSITORY)
    ).document
    layout = materialization._mapping(
        protocol.get("coordinate_and_member_layout"), label="coordinate layout"
    )
    external = materialization._mapping(
        protocol.get("external_durable_chronology_contract"),
        label="external chronology",
    )
    route = materialization._mapping(
        external.get("route_future_external_coordinates"),
        label="route external coordinates",
    )
    return (
        REPOSITORY.joinpath(*str(layout["descriptive_result"]).split("/")),
        Path(str(route["external_store_path"])),
        Path(str(route["external_staging_path"])),
    )


def test_result_publication_exact_a_to_fixed_result_and_existing_commit_b_verifier(
    tmp_path: Path,
) -> None:
    case = _build_case(tmp_path)
    artifact_commit = _commit_a(case)
    expected = _exact_descriptive_result(case)
    official_before = {path: _path_state(path) for path in _official_paths()}

    receipt = _publish(case, artifact_commit=artifact_commit)

    destination = _result_path(case)
    assert receipt.destination == destination.resolve()
    assert receipt.source_commit == case.source_commit
    assert receipt.artifact_commit == artifact_commit
    assert receipt.result_sha256 == expected.canonical_sha256
    assert receipt.result_byte_count == len(expected.canonical_bytes)
    assert destination.read_bytes() == expected.canonical_bytes
    assert sha256_bytes(destination.read_bytes()) == receipt.result_sha256
    assert receipt.native_primitive
    for field in _TRUE_RECEIPT_AXES:
        assert getattr(receipt, field) is True
    for field in _FALSE_RECEIPT_AXES:
        assert getattr(receipt, field) is False
    assert not _stage_path(case).exists()
    assert {path: _path_state(path) for path in _official_paths()} == official_before
    assert _run(case.repository, "rev-parse", "HEAD") == artifact_commit
    assert _run(case.repository, "diff", "--cached", "--name-only") == ""
    assert _run(case.repository, "status", "--short") == (
        f"?? {destination.relative_to(case.repository)}"
    )

    _run(case.repository, "add", str(destination.relative_to(case.repository)))
    _run(case.repository, "commit", "--quiet", "-m", "result-only B")
    result_commit = _run(case.repository, "rev-parse", "HEAD")
    verified = _verify_commit_b(case, artifact_commit, result_commit)
    assert verified.result is not None
    assert verified.result.canonical_bytes == expected.canonical_bytes
    assert verified.source_commit == case.source_commit
    assert verified.artifact_commit == artifact_commit
    assert verified.result_commit == result_commit


def test_result_publisher_is_private_and_has_no_caller_controlled_io_surface() -> None:
    assert publication.__all__ == ()
    signature = inspect.signature(
        publication._publish_d7_v1_descriptive_result_no_replace
    )
    assert list(signature.parameters) == [
        "repository",
        "source_commit",
        "artifact_commit",
    ]
    assert signature.parameters["source_commit"].kind is inspect.Parameter.KEYWORD_ONLY
    assert (
        signature.parameters["artifact_commit"].kind is inspect.Parameter.KEYWORD_ONLY
    )
    assert not any(
        parameter.kind
        in {inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD}
        for parameter in signature.parameters.values()
    )
    forbidden = {
        "bytes",
        "source",
        "result",
        "path",
        "destination",
        "stage",
        "reader",
        "writer",
        "fsync",
        "rename",
        "callback",
    }
    assert not forbidden & set(signature.parameters)


@pytest.mark.parametrize("relation", ("after", "before"))
def test_result_publication_rejects_wrong_clean_head(
    tmp_path: Path,
    relation: str,
) -> None:
    case = _build_case(tmp_path)
    artifact_commit = _commit_a(case)
    if relation == "after":
        _run(case.repository, "commit", "--allow-empty", "--quiet", "-m", "wrong head")
    else:
        _run(case.repository, "checkout", "--quiet", case.source_commit)

    with pytest.raises(publication.D7V1ResultPublicationFailure) as caught:
        _publish(case, artifact_commit=artifact_commit)
    _assert_failure_axes(caught.value)
    assert "artifact commit A" in str(caught.value)
    _assert_no_result_namespace(case)


@pytest.mark.parametrize("dirty_kind", ("unstaged", "index", "untracked"))
def test_result_publication_rejects_every_unrelated_repository_change(
    tmp_path: Path,
    dirty_kind: str,
) -> None:
    case = _build_case(tmp_path)
    artifact_commit = _commit_a(case)
    if dirty_kind == "unstaged":
        (case.repository / "README.md").write_text("dirty\n", encoding="utf-8")
    else:
        relative = f"protocols/scratch-{dirty_kind}.txt"
        _write(case.repository, relative, b"dirty\n")
        if dirty_kind == "index":
            _run(case.repository, "add", relative)

    with pytest.raises(publication.D7V1ResultPublicationFailure) as caught:
        _publish(case, artifact_commit=artifact_commit)
    _assert_failure_axes(caught.value)
    _assert_no_result_namespace(case)


@pytest.mark.parametrize("invalid_kind", ("missing", "empty-commit", "source"))
def test_result_publication_requires_the_exact_valid_artifact_commit_a(
    tmp_path: Path,
    invalid_kind: str,
) -> None:
    case = _build_case(tmp_path)
    if invalid_kind == "missing":
        artifact_commit = "0" * 40
    elif invalid_kind == "source":
        artifact_commit = case.source_commit
    else:
        _run(case.repository, "commit", "--allow-empty", "--quiet", "-m", "not A")
        artifact_commit = _run(case.repository, "rev-parse", "HEAD")

    with pytest.raises(
        (publication.D7V1ResultPublicationFailure, QualificationContractError)
    ) as caught:
        _publish(case, artifact_commit=artifact_commit)
    if isinstance(caught.value, publication.D7V1ResultPublicationFailure):
        _assert_failure_axes(caught.value)
    _assert_no_result_namespace(case)


def test_result_publication_requires_its_source_in_c1(
    tmp_path: Path,
) -> None:
    def omit_publisher(
        members: tuple[records.D7V1SourceMember, ...],
    ) -> tuple[records.D7V1SourceMember, ...]:
        return tuple(
            member
            for member in members
            if member.repository_path != PUBLISHER_REPOSITORY_PATH
        )

    case = _build_case(tmp_path, mutate_source_member=omit_publisher)
    artifact_commit = _commit_a(case)
    with pytest.raises(publication.D7V1ResultPublicationFailure) as caught:
        _publish(case, artifact_commit=artifact_commit)
    _assert_failure_axes(caught.value)
    _assert_no_result_namespace(case)


def test_result_publication_rejects_equivalent_different_import_origin(
    tmp_path: Path,
) -> None:
    case = _build_case(tmp_path)
    artifact_commit = _commit_a(case)
    target = case.repository.joinpath(*PUBLISHER_REPOSITORY_PATH.split("/"))
    source = target.read_bytes()
    target.unlink()
    target.write_bytes(source)

    with pytest.raises(publication.D7V1ResultPublicationFailure) as caught:
        _publish(case, artifact_commit=artifact_commit)
    _assert_failure_axes(caught.value)
    _assert_no_result_namespace(case)


@pytest.mark.parametrize("coordinate", ("destination", "stage"))
@pytest.mark.parametrize("entry_kind", ("file", "directory", "symlink"))
def test_result_publication_refuses_all_result_and_stage_collisions(
    tmp_path: Path,
    coordinate: str,
    entry_kind: str,
) -> None:
    case = _build_case(tmp_path)
    artifact_commit = _commit_a(case)
    target = _result_path(case) if coordinate == "destination" else _stage_path(case)
    target.parent.mkdir(parents=True, exist_ok=True)
    if entry_kind == "file":
        target.write_bytes(b"collision\n")
    elif entry_kind == "directory":
        target.mkdir()
    else:
        target.symlink_to(target.with_name(f"{target.name}.dangling"))
    before = _path_state(target)

    with pytest.raises(publication.D7V1ResultPublicationFailure) as caught:
        _publish(case, artifact_commit=artifact_commit)
    _assert_failure_axes(caught.value)
    assert _path_state(target) == before
    other = _stage_path(case) if coordinate == "destination" else _result_path(case)
    assert not other.exists() and not other.is_symlink()


def test_result_publication_rejects_stage_member_mutation_before_rename(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _build_case(tmp_path)
    artifact_commit = _commit_a(case)
    real_read = publication._read_owned_result
    injected = False

    def mutate_then_read(*args: object, **kwargs: object) -> object:
        nonlocal injected
        if not injected:
            injected = True
            stage = _stage_path(case)
            original = stage.read_bytes()
            stage.write_bytes(b"x" + original[1:])
        return real_read(*args, **kwargs)

    monkeypatch.setattr(publication, "_read_owned_result", mutate_then_read)
    with pytest.raises(publication.D7V1ResultPublicationFailure) as caught:
        _publish(case, artifact_commit=artifact_commit)
    assert injected is True
    _assert_failure_axes(caught.value)
    assert caught.value.publication_visible is not True
    assert not _result_path(case).exists()


def test_result_publication_rejects_live_result_parent_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _build_case(tmp_path)
    artifact_commit = _commit_a(case)
    destination = _result_path(case)
    moved = destination.parent.with_name(f"{destination.parent.name}-moved")
    stage = _stage_path(case)
    primitive, _real_rename = publication.private_publication._native_exclusive_rename()
    real_outcome = publication._publication_outcome
    outcome_calls = 0
    injected = False

    def rename_factory() -> tuple[str, object]:
        def leave_stage_in_place(
            parent_fd: int,
            source_leaf: str,
            destination_leaf: str,
        ) -> None:
            assert source_leaf == stage.name
            assert destination_leaf == destination.name

        return primitive, leave_stage_in_place

    def observe_then_replace_parent(*args: object, **kwargs: object) -> str:
        nonlocal injected, outcome_calls
        outcome = real_outcome(*args, **kwargs)
        outcome_calls += 1
        if outcome_calls == 2 and outcome == "stage-retained":
            injected = True
            destination.parent.rename(moved)
            destination.parent.mkdir()
        return outcome

    monkeypatch.setattr(
        publication.private_publication,
        "_native_exclusive_rename",
        rename_factory,
    )
    monkeypatch.setattr(
        publication, "_publication_outcome", observe_then_replace_parent
    )
    with pytest.raises(publication.D7V1ResultPublicationFailure) as caught:
        _publish(case, artifact_commit=artifact_commit)
    assert injected is True
    _assert_failure_axes(caught.value)
    assert caught.value.stage_path is None
    assert caught.value.stage_retained is None
    assert caught.value.publication_visible is None
    assert not destination.exists()
    assert moved.joinpath(stage.name).is_file()


def test_result_publication_does_not_report_stale_stage_outcome(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _build_case(tmp_path)
    artifact_commit = _commit_a(case)
    destination = _result_path(case)
    stage = _stage_path(case)
    foreign = stage.with_name(f"{stage.name}.foreign")
    primitive, _real_rename = publication.private_publication._native_exclusive_rename()
    real_outcome = publication._publication_outcome
    injected = False

    def rename_factory() -> tuple[str, object]:
        def leave_stage_in_place(
            parent_fd: int,
            source_leaf: str,
            destination_leaf: str,
        ) -> None:
            assert source_leaf == stage.name
            assert destination_leaf == destination.name

        return primitive, leave_stage_in_place

    def observe_then_move_stage(*args: object, **kwargs: object) -> str:
        nonlocal injected
        outcome = real_outcome(*args, **kwargs)
        if not injected and outcome == "stage-retained":
            stage.rename(foreign)
            injected = True
        return outcome

    monkeypatch.setattr(
        publication.private_publication,
        "_native_exclusive_rename",
        rename_factory,
    )
    monkeypatch.setattr(publication, "_publication_outcome", observe_then_move_stage)
    with pytest.raises(publication.D7V1ResultPublicationFailure) as caught:
        _publish(case, artifact_commit=artifact_commit)
    assert injected is True, repr(caught.value)
    _assert_failure_axes(caught.value)
    assert caught.value.disposition == "rename_outcome_ambiguous"
    assert caught.value.stage_path is None
    assert caught.value.stage_retained is None
    assert caught.value.publication_visible is None
    assert not destination.exists()
    assert foreign.is_file()


def test_result_publication_retains_stage_after_pre_rename_result_fsync_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _build_case(tmp_path)
    artifact_commit = _commit_a(case)
    real_fsync = publication.os.fsync
    failed = False

    def fail_first_regular_file_fsync(descriptor: int) -> None:
        nonlocal failed
        if not failed and stat.S_ISREG(os.fstat(descriptor).st_mode):
            failed = True
            raise OSError(errno.EIO, "injected result fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(publication.os, "fsync", fail_first_regular_file_fsync)
    with pytest.raises(publication.D7V1ResultPublicationFailure) as caught:
        _publish(case, artifact_commit=artifact_commit)
    assert failed is True
    _assert_failure_axes(caught.value)
    assert caught.value.stage_retained is True
    assert caught.value.publication_visible is False
    assert _stage_path(case).is_file()
    assert not _result_path(case).exists()

    monkeypatch.setattr(publication.os, "fsync", real_fsync)
    with pytest.raises(publication.D7V1ResultPublicationFailure) as reentry:
        _publish(case, artifact_commit=artifact_commit)
    _assert_failure_axes(reentry.value)
    assert _stage_path(case).is_file()


def test_result_publication_reports_post_rename_parent_fsync_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _build_case(tmp_path)
    artifact_commit = _commit_a(case)
    primitive, real_rename = publication.private_publication._native_exclusive_rename()
    real_fsync = publication.os.fsync
    renamed = False
    failed = False

    def rename_factory() -> tuple[str, object]:
        def mark_rename(
            parent_fd: int, source_leaf: str, destination_leaf: str
        ) -> None:
            nonlocal renamed
            real_rename(parent_fd, source_leaf, destination_leaf)
            renamed = True

        return primitive, mark_rename

    def fail_after_rename(descriptor: int) -> None:
        nonlocal failed
        if renamed and not failed:
            failed = True
            raise OSError(errno.EIO, "injected parent fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(
        publication.private_publication, "_native_exclusive_rename", rename_factory
    )
    monkeypatch.setattr(publication.os, "fsync", fail_after_rename)
    with pytest.raises(publication.D7V1ResultPublicationFailure) as caught:
        _publish(case, artifact_commit=artifact_commit)
    assert failed is True
    _assert_failure_axes(caught.value)
    assert caught.value.publication_visible is True
    assert caught.value.stage_retained is False
    assert _result_path(case).is_file()
    assert not _stage_path(case).exists()


def test_result_publication_never_turns_rename_error_into_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _build_case(tmp_path)
    artifact_commit = _commit_a(case)
    primitive, real_rename = publication.private_publication._native_exclusive_rename()

    def rename_factory() -> tuple[str, object]:
        def rename_then_error(
            parent_fd: int,
            source_leaf: str,
            destination_leaf: str,
        ) -> NoReturn:
            real_rename(parent_fd, source_leaf, destination_leaf)
            raise OSError(errno.EIO, "injected ambiguous rename return")

        return primitive, rename_then_error

    monkeypatch.setattr(
        publication.private_publication, "_native_exclusive_rename", rename_factory
    )
    with pytest.raises(publication.D7V1ResultPublicationFailure) as caught:
        _publish(case, artifact_commit=artifact_commit)
    _assert_failure_axes(caught.value)
    assert caught.value.disposition == "published_durability_unknown"
    assert caught.value.stage_path is None
    assert caught.value.stage_retained is False
    assert caught.value.publication_visible is True
    assert (
        sha256_bytes(_result_path(case).read_bytes())
        == _exact_descriptive_result(case).canonical_sha256
    )
    assert not _stage_path(case).exists()


@pytest.mark.parametrize(
    "tamper_kind", ("oversize", "noncanonical", "schema-valid-nonrederived")
)
def test_result_publication_rejects_tampered_stage_before_parse(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tamper_kind: str,
) -> None:
    case = _build_case(tmp_path)
    artifact_commit = _commit_a(case)
    if tamper_kind == "oversize":
        replacement = b"x" * (records.D7_V1_POSTSELECTION_RESULT_MAX_RECORD_BYTES + 1)
    elif tamper_kind == "noncanonical":
        replacement = b'{"schema_version":"invalid"}\n'
    else:
        replacement = case.result.canonical_bytes
    real_write = publication.private_publication._write_all
    real_parse = records.parse_canonical_json
    stage_written = False
    post_write_parse_count = 0

    def write_tamper(descriptor: int, source: bytes) -> None:
        nonlocal stage_written
        assert source != replacement
        real_write(descriptor, replacement)
        stage_written = True

    def reject_post_write_parse(*args: object, **kwargs: object) -> object:
        nonlocal post_write_parse_count
        if stage_written:
            post_write_parse_count += 1
            pytest.fail(
                "tampered result reached canonical parse before digest rejection"
            )
        return real_parse(*args, **kwargs)

    monkeypatch.setattr(publication.private_publication, "_write_all", write_tamper)
    monkeypatch.setattr(records, "parse_canonical_json", reject_post_write_parse)
    with pytest.raises(publication.D7V1ResultPublicationFailure) as caught:
        _publish(case, artifact_commit=artifact_commit)
    assert stage_written is True
    assert post_write_parse_count == 0
    _assert_failure_axes(caught.value)
    assert caught.value.publication_visible is False
    assert caught.value.stage_retained is True
    assert not _result_path(case).exists()


@pytest.mark.parametrize(
    "foreign_outcome", ("foreign-inode", "destination-swap", "foreign-leaf")
)
def test_result_publication_never_accepts_a_foreign_post_rename_inode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    foreign_outcome: str,
) -> None:
    case = _build_case(tmp_path)
    artifact_commit = _commit_a(case)
    destination = _result_path(case)
    expected = _exact_descriptive_result(case)
    primitive, real_rename = publication.private_publication._native_exclusive_rename()
    foreign_leaf = f".{destination.name}.{foreign_outcome}"

    def rename_factory() -> tuple[str, object]:
        def foreign_rename(
            parent_fd: int,
            source_leaf: str,
            destination_leaf: str,
        ) -> None:
            if foreign_outcome == "foreign-leaf":
                os.rename(
                    source_leaf,
                    foreign_leaf,
                    src_dir_fd=parent_fd,
                    dst_dir_fd=parent_fd,
                )
                raise OSError(errno.EIO, "stage moved to a foreign leaf")
            real_rename(parent_fd, source_leaf, destination_leaf)
            os.rename(
                destination_leaf,
                foreign_leaf,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
            )
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            descriptor = os.open(destination_leaf, flags, 0o600, dir_fd=parent_fd)
            try:
                payload = (
                    expected.canonical_bytes
                    if foreign_outcome == "foreign-inode"
                    else b"foreign\n"
                )
                publication.private_publication._write_all(descriptor, payload)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            if foreign_outcome == "destination-swap":
                raise OSError(errno.EIO, "destination swapped after rename")

        return primitive, foreign_rename

    monkeypatch.setattr(
        publication.private_publication, "_native_exclusive_rename", rename_factory
    )
    with pytest.raises(publication.D7V1ResultPublicationFailure) as caught:
        _publish(case, artifact_commit=artifact_commit)
    _assert_failure_axes(caught.value)
    assert caught.value.stage_path is None
    assert caught.value.stage_retained is None
    assert caught.value.publication_visible is None
    assert not _stage_path(case).exists()


def test_result_publication_rejects_a_separately_reopened_foreign_inode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _build_case(tmp_path)
    artifact_commit = _commit_a(case)
    destination = _result_path(case)
    expected = _exact_descriptive_result(case)
    displaced = destination.with_name(f".{destination.name}.displaced")
    real_reload = publication._reload_published_result
    injected = False

    def swap_before_reopen(*args: object, **kwargs: object) -> object:
        nonlocal injected
        if not injected and destination.is_file():
            injected = True
            destination.rename(displaced)
            destination.write_bytes(expected.canonical_bytes)
        return real_reload(*args, **kwargs)

    monkeypatch.setattr(publication, "_reload_published_result", swap_before_reopen)
    with pytest.raises(publication.D7V1ResultPublicationFailure) as caught:
        _publish(case, artifact_commit=artifact_commit)
    assert injected is True
    _assert_failure_axes(caught.value)
    assert caught.value.stage_path is None
    assert caught.value.stage_retained is None
    assert caught.value.publication_visible is None
    assert destination.is_file()
    assert displaced.is_file()


def test_result_publication_reentry_is_nonretryable_and_does_not_replace(
    tmp_path: Path,
) -> None:
    case = _build_case(tmp_path)
    artifact_commit = _commit_a(case)
    receipt = _publish(case, artifact_commit=artifact_commit)
    before = _path_state(receipt.destination)

    with pytest.raises(publication.D7V1ResultPublicationFailure) as caught:
        _publish(case, artifact_commit=artifact_commit)
    _assert_failure_axes(caught.value)
    assert _path_state(receipt.destination) == before
    assert not _stage_path(case).exists()


def test_result_publication_never_invokes_a_git_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _build_case(tmp_path)
    artifact_commit = _commit_a(case)
    real_git = materialization._git
    observed: list[tuple[str, ...]] = []
    mutating = {
        "add",
        "am",
        "checkout",
        "clean",
        "commit",
        "merge",
        "mv",
        "rebase",
        "reset",
        "restore",
        "rm",
        "switch",
        "tag",
    }

    def reject_mutation(
        repository: materialization.RepositoryContext,
        *arguments: str,
    ) -> bytes:
        observed.append(arguments)
        assert arguments and arguments[0] not in mutating
        return real_git(repository, *arguments)

    monkeypatch.setattr(materialization, "_git", reject_mutation)
    _publish(case, artifact_commit=artifact_commit)
    assert observed
    assert _run(case.repository, "rev-parse", "HEAD") == artifact_commit


def test_result_publication_import_is_side_effect_free_and_source_ast_is_bounded() -> (
    None
):
    watched = _official_paths()
    before = {path: _path_state(path) for path in watched}
    importlib.reload(publication)
    assert {path: _path_state(path) for path in watched} == before
    assert publication.__all__ == ()

    tree = ast.parse(PUBLISHER_MODULE_PATH.read_text(encoding="utf-8"))
    imports = {
        imported
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for imported in (
            *(alias.name for alias in node.names),
            *((node.module or "",) if isinstance(node, ast.ImportFrom) else ()),
        )
    }
    forbidden_import_fragments = {
        "confirmation_attempt_",
        "confirmation_authoritative_start",
        "confirmation_fused_",
        "confirmation_official_execution",
        "confirmation_v1_official_execution",
        "confirmation_preseed_authority",
        "confirmation_seed_supply_contracts",
        "confirmation_terminal_operations",
        "torch",
        "transformers",
        "faiss",
    }
    assert not {
        fragment
        for fragment in forbidden_import_fragments
        if any(fragment in imported for imported in imports)
    }
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert (
        not {
            "unlink",
            "remove",
            "rmtree",
            "replace",
            "cleanup",
            "overwrite",
        }
        & called_attributes
    )
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not {"supplier", "model", "official", "cleanup", "overwrite"} & names


def _current_status_section(path: Path, start: str, end: str) -> str:
    document = path.read_text(encoding="utf-8")
    assert document.count(start) == 1
    section = document.split(start, 1)[1]
    assert end in section
    return start + section.split(end, 1)[0]


def test_result_publication_documentation_projects_only_the_current_source_boundary() -> (
    None
):
    sections = {
        "README": _current_status_section(
            REPOSITORY / "README.md",
            "The prospective\n[D7 v1 pre-item-23 materialization protocol]",
            "## Scientific interpretation anchors",
        ),
        "ROADMAP": _current_status_section(
            REPOSITORY / "docs" / "ROADMAP.md",
            "The canonical\n[`VOY-V1`–`VOY-V9` route]",
            "## 4. What “library” means",
        ),
        "LEDGER": _current_status_section(
            REPOSITORY / "docs" / "EXPERIMENT_INTERPRETATION_LEDGER.md",
            "### 3.20 D7 v1 private stage-17 result-publication primitive",
            "## 4. Summary reclassification",
        ),
        "CHANGELOG": _current_status_section(
            REPOSITORY / "docs" / "SCHEMA_CHANGELOG.md",
            "## 2026-08-10 — D7 v1 private result-publication primitive",
            "## 2026-08-10 — D7 v1 descriptive source and blocked entrypoint coordinates",
        ),
    }
    required = {
        "README": (
            "source-only",
            "stage-17",
            "uninvoked",
            "VOY-V3",
            "frozen_not_run",
            "commit S has not been\nselected",
            "public API",
            "library maturity",
        ),
        "ROADMAP": (
            "source-only stage-17",
            "uninvoked",
            "VOY-V3",
            "frozen_not_run",
            "S remains unselected",
            "public-API",
            "library completion credit",
        ),
        "LEDGER": (
            "source-only",
            "stage-17",
            "uninvoked",
            "VOY-V3",
            "frozen_not_run",
            "selected S",
            "public API",
            "library\nmilestone",
        ),
        "CHANGELOG": (
            "source-only",
            "stage-17",
            "uninvoked",
            "VOY-V3",
            "frozen_not_run",
            "S remains\n  unselected",
            "public API",
            "library\n  maturity",
        ),
    }
    for name, tokens in required.items():
        assert all(token in sections[name] for token in tokens), name
        current = sections[name].lower()
        assert "no stage-17 result publisher" not in current
        assert "no stage-17 descriptive-result publisher" not in current
