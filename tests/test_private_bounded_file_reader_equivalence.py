from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
import errno
import hashlib
import json
import os
from pathlib import Path
import stat

import pytest

from access_fixtures import preparation_descriptor
from spirallens.access import (
    AtlasAccessContractError,
    AtlasPreparationDescriptor,
    load_atlas_preparation_descriptor,
)
from spirallens.access import descriptor as access_descriptor_module
from spirallens.core.canonical import CanonicalJsonError
from spirallens.referents import (
    ReferentContractError,
    ReferentContractSet,
    canonical_f0_f4_referent_contracts,
    load_referent_contract_set,
)
from spirallens.referents import loader as referent_loader_module


_UNSET = object()
_DIGEST_ERROR = "must be a lowercase SHA-256 digest"
_HELD_FD_READER_SUPPORTED = (
    os.name == "posix"
    and os.open in os.supports_dir_fd
    and hasattr(os, "O_DIRECTORY")
    and hasattr(os, "O_NOFOLLOW")
)
requires_held_fd_reader = pytest.mark.skipif(
    not _HELD_FD_READER_SUPPORTED,
    reason="the current held-file readers require POSIX dir_fd and no-follow flags",
)


@dataclass(frozen=True, slots=True)
class _ReaderCase:
    name: str
    leaf_name: str
    source: bytes
    canonical_sha256: str
    expected_value: object
    loaded_value_attribute: str
    error_type: type[Exception]
    module: object
    limit_name: str
    typed_class: type[object]
    typed_replacement: object
    path_before_digest: bool
    path_error: str
    parent_subject: str
    read_subject: str
    regular_file_error: str
    one_link_error: str
    oversize_error: str
    changed_error: str
    source_mismatch_error: str
    invalid_json_error: str
    noncanonical_json_error: str
    object_error: str
    canonical_mismatch_error: str
    typed_roundtrip_error: str
    loader: Callable[[Path, object, object], object]

    @property
    def source_sha256(self) -> str:
        return hashlib.sha256(self.source).hexdigest()

    @property
    def max_bytes(self) -> int:
        value = getattr(self.module, self.limit_name)
        assert type(value) is int
        return value

    def load(
        self,
        path: Path,
        *,
        expected_source_sha256: object = _UNSET,
        expected_canonical_sha256: object = _UNSET,
    ) -> object:
        source = (
            self.source_sha256
            if expected_source_sha256 is _UNSET
            else expected_source_sha256
        )
        canonical = (
            self.canonical_sha256
            if expected_canonical_sha256 is _UNSET
            else expected_canonical_sha256
        )
        return self.loader(path, source, canonical)

    def parent_open_error(self, parent: Path) -> str:
        return f"cannot safely open {self.parent_subject} parent: {parent}"

    def leaf_read_error(self, path: Path) -> str:
        return f"cannot safely read {self.read_subject}: {path}"


_ATLAS_DESCRIPTOR = preparation_descriptor()
_ATLAS_REPLACEMENT = replace(
    _ATLAS_DESCRIPTOR,
    descriptor_id="atlas-access-equivalence-mutated",
)
_REFERENT_CONTRACTS = canonical_f0_f4_referent_contracts("4" * 64)
_REFERENT_REPLACEMENT = canonical_f0_f4_referent_contracts("5" * 64)


def _load_atlas(path: Path, source: object, canonical: object) -> object:
    return load_atlas_preparation_descriptor(
        path,
        expected_source_sha256=source,  # type: ignore[arg-type]
        expected_canonical_sha256=canonical,  # type: ignore[arg-type]
    )


def _load_referents(path: Path, source: object, canonical: object) -> object:
    return load_referent_contract_set(
        path,
        expected_source_sha256=source,  # type: ignore[arg-type]
        expected_canonical_sha256=canonical,  # type: ignore[arg-type]
    )


_READER_CASES = (
    _ReaderCase(
        name="atlas",
        leaf_name="atlas-access.json",
        source=_ATLAS_DESCRIPTOR.canonical_bytes,
        canonical_sha256=_ATLAS_DESCRIPTOR.canonical_sha256,
        expected_value=_ATLAS_DESCRIPTOR,
        loaded_value_attribute="descriptor",
        error_type=AtlasAccessContractError,
        module=access_descriptor_module,
        limit_name="MAX_ATLAS_PREPARATION_DESCRIPTOR_BYTES",
        typed_class=AtlasPreparationDescriptor,
        typed_replacement=_ATLAS_REPLACEMENT,
        path_before_digest=True,
        path_error="descriptor path must name one file",
        parent_subject="descriptor",
        read_subject="atlas preparation descriptor",
        regular_file_error="atlas preparation descriptor must be a regular file",
        one_link_error="atlas preparation descriptor must have exactly one link",
        oversize_error="atlas preparation descriptor exceeds the size limit",
        changed_error="atlas preparation descriptor changed during read",
        source_mismatch_error=("atlas preparation descriptor source SHA-256 mismatch"),
        invalid_json_error="atlas preparation descriptor is invalid JSON",
        noncanonical_json_error=("atlas preparation descriptor is not canonical JSON"),
        object_error="atlas preparation descriptor must contain one object",
        canonical_mismatch_error=(
            "atlas preparation descriptor canonical SHA-256 mismatch"
        ),
        typed_roundtrip_error=("atlas preparation descriptor typed round-trip differs"),
        loader=_load_atlas,
    ),
    _ReaderCase(
        name="referents",
        leaf_name="referents.json",
        source=_REFERENT_CONTRACTS.canonical_bytes,
        canonical_sha256=_REFERENT_CONTRACTS.canonical_sha256,
        expected_value=_REFERENT_CONTRACTS,
        loaded_value_attribute="contract_set",
        error_type=ReferentContractError,
        module=referent_loader_module,
        limit_name="MAX_REFERENT_CONTRACT_SET_BYTES",
        typed_class=ReferentContractSet,
        typed_replacement=_REFERENT_REPLACEMENT,
        path_before_digest=False,
        path_error="referent contract path must name one file",
        parent_subject="referent contract",
        read_subject="referent contract",
        regular_file_error="referent contract must be a regular file",
        one_link_error="referent contract must have exactly one link",
        oversize_error="referent contract exceeds the size limit",
        changed_error="referent contract changed during read",
        source_mismatch_error="referent contract source SHA-256 mismatch",
        invalid_json_error="referent contract is invalid JSON",
        noncanonical_json_error="referent contract is not canonical JSON",
        object_error="referent contract must contain one object",
        canonical_mismatch_error="referent contract canonical SHA-256 mismatch",
        typed_roundtrip_error="referent contract typed round-trip differs",
        loader=_load_referents,
    ),
)


@pytest.fixture(params=_READER_CASES, ids=lambda case: case.name)
def reader_case(request: pytest.FixtureRequest) -> _ReaderCase:
    case = request.param
    assert isinstance(case, _ReaderCase)
    return case


def _capture(call: Callable[[], object]) -> tuple[object | None, BaseException | None]:
    try:
        return call(), None
    except BaseException as error:
        return None, error


def _assert_policy_error(
    error: BaseException | None,
    case: _ReaderCase,
    message: str,
) -> None:
    assert error is not None
    assert type(error) is case.error_type
    assert str(error) == message
    assert error.__cause__ is None
    assert error.__context__ is None
    assert error.__suppress_context__ is False


def _assert_os_error(
    error: BaseException | None,
    case: _ReaderCase,
    message: str,
    *,
    expected_cause: OSError | None = None,
) -> None:
    assert error is not None
    assert type(error) is case.error_type
    assert str(error) == message
    assert isinstance(error.__cause__, OSError)
    if expected_cause is not None:
        assert error.__cause__ is expected_cause
    assert error.__context__ is error.__cause__
    assert error.__suppress_context__ is True


def _assert_canonical_json_error(
    error: BaseException | None,
    case: _ReaderCase,
    message: str,
) -> None:
    assert error is not None
    assert type(error) is case.error_type
    assert str(error) == message
    assert type(error.__cause__) is CanonicalJsonError
    assert error.__context__ is error.__cause__
    assert error.__suppress_context__ is True


@requires_held_fd_reader
def test_success_preserves_exact_value_source_identity_and_single_file_trace(
    reader_case: _ReaderCase,
    tmp_path: Path,
) -> None:
    root = tmp_path.resolve() / reader_case.name
    root.mkdir()
    path = root / reader_case.leaf_name
    path.write_bytes(reader_case.source)

    loaded = reader_case.load(path)

    assert getattr(loaded, reader_case.loaded_value_attribute) == (
        reader_case.expected_value
    )
    assert loaded.source_path == path
    assert loaded.source_sha256 == reader_case.source_sha256
    assert loaded.canonical_sha256 == reader_case.canonical_sha256
    assert loaded.read_trace == (path,)
    assert path.read_bytes() == reader_case.source


@requires_held_fd_reader
def test_root_path_and_bad_digest_preserve_domain_preprocessing_precedence(
    reader_case: _ReaderCase,
) -> None:
    _result, error = _capture(
        lambda: reader_case.load(
            Path("/"),
            expected_source_sha256="bad",
            expected_canonical_sha256="also-bad",
        )
    )

    expected = (
        reader_case.path_error
        if reader_case.path_before_digest
        else f"expected_source_sha256 {_DIGEST_ERROR}"
    )
    _assert_policy_error(error, reader_case, expected)


def test_source_digest_validation_precedes_canonical_digest_and_filesystem(
    reader_case: _ReaderCase,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path.resolve() / "must-not-open" / reader_case.leaf_name

    def forbidden_open(*_args: object, **_kwargs: object) -> int:
        raise AssertionError("digest validation must precede filesystem access")

    with monkeypatch.context() as patch:
        patch.setattr(os, "open", forbidden_open)
        _result, error = _capture(
            lambda: reader_case.load(
                path,
                expected_source_sha256="bad",
                expected_canonical_sha256="also-bad",
            )
        )

    _assert_policy_error(
        error,
        reader_case,
        f"expected_source_sha256 {_DIGEST_ERROR}",
    )


def test_canonical_digest_validation_precedes_filesystem_and_source_comparison(
    reader_case: _ReaderCase,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path.resolve() / "must-not-open" / reader_case.leaf_name

    def forbidden_open(*_args: object, **_kwargs: object) -> int:
        raise AssertionError("digest validation must precede filesystem access")

    with monkeypatch.context() as patch:
        patch.setattr(os, "open", forbidden_open)
        _result, error = _capture(
            lambda: reader_case.load(
                path,
                expected_source_sha256="0" * 64,
                expected_canonical_sha256="bad",
            )
        )

    _assert_policy_error(
        error,
        reader_case,
        f"expected_canonical_sha256 {_DIGEST_ERROR}",
    )


@pytest.mark.parametrize(
    ("scenario", "os_failure"),
    (
        ("missing_parent", True),
        ("symlinked_parent", True),
        ("missing_leaf", True),
        ("symlinked_leaf", True),
        ("directory_leaf", False),
        ("hardlinked_leaf", False),
        ("initial_oversize", False),
    ),
)
@requires_held_fd_reader
def test_real_filesystem_failures_preserve_exact_domain_boundary(
    reader_case: _ReaderCase,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scenario: str,
    os_failure: bool,
) -> None:
    root = tmp_path.resolve() / reader_case.name
    root.mkdir()

    if scenario == "missing_parent":
        path = root / "missing" / reader_case.leaf_name
        expected = reader_case.parent_open_error(path.parent)
    elif scenario == "symlinked_parent":
        real_parent = root / "real-parent"
        real_parent.mkdir()
        (real_parent / reader_case.leaf_name).write_bytes(reader_case.source)
        alias = root / "parent-alias"
        alias.symlink_to(real_parent, target_is_directory=True)
        path = alias / reader_case.leaf_name
        expected = reader_case.parent_open_error(path.parent)
    elif scenario == "missing_leaf":
        path = root / reader_case.leaf_name
        expected = reader_case.leaf_read_error(path)
    elif scenario == "symlinked_leaf":
        target = root / "target.json"
        target.write_bytes(reader_case.source)
        path = root / reader_case.leaf_name
        path.symlink_to(target)
        expected = reader_case.leaf_read_error(path)
    elif scenario == "directory_leaf":
        path = root / reader_case.leaf_name
        path.mkdir()
        expected = reader_case.regular_file_error
    elif scenario == "hardlinked_leaf":
        path = root / reader_case.leaf_name
        path.write_bytes(reader_case.source)
        os.link(path, root / "external-hardlink.json")
        expected = reader_case.one_link_error
    else:
        assert scenario == "initial_oversize"
        monkeypatch.setattr(reader_case.module, reader_case.limit_name, 8)
        source = b"x" * 9
        path = root / reader_case.leaf_name
        path.write_bytes(source)
        expected = reader_case.oversize_error

    _result, error = _capture(
        lambda: reader_case.load(
            path,
            expected_source_sha256=(
                hashlib.sha256(source).hexdigest()
                if scenario == "initial_oversize"
                else _UNSET
            ),
            expected_canonical_sha256=(
                "0" * 64 if scenario == "initial_oversize" else _UNSET
            ),
        )
    )

    if os_failure:
        _assert_os_error(error, reader_case, expected)
    else:
        _assert_policy_error(error, reader_case, expected)


@pytest.mark.parametrize(
    "stage",
    (
        "source_digest",
        "invalid_json",
        "noncanonical_json",
        "non_object",
        "canonical_digest",
    ),
)
@requires_held_fd_reader
def test_digest_and_parse_precedence_preserves_exact_failure(
    reader_case: _ReaderCase,
    tmp_path: Path,
    stage: str,
) -> None:
    root = tmp_path.resolve() / reader_case.name
    root.mkdir()
    path = root / reader_case.leaf_name

    if stage == "source_digest":
        source = b"{"
        expected_source = "0" * 64
        expected_canonical = "0" * 64
        expected = reader_case.source_mismatch_error
        canonical_failure = False
    elif stage == "invalid_json":
        source = b"{"
        expected_source = hashlib.sha256(source).hexdigest()
        expected_canonical = "0" * 64
        expected = reader_case.invalid_json_error
        canonical_failure = True
    elif stage == "noncanonical_json":
        source = json.dumps({"unused": 1}, indent=2).encode("utf-8")
        expected_source = hashlib.sha256(source).hexdigest()
        expected_canonical = "0" * 64
        expected = reader_case.noncanonical_json_error
        canonical_failure = True
    elif stage == "non_object":
        source = b"[]"
        expected_source = hashlib.sha256(source).hexdigest()
        expected_canonical = "0" * 64
        expected = reader_case.object_error
        canonical_failure = False
    else:
        assert stage == "canonical_digest"
        source = reader_case.source
        expected_source = reader_case.source_sha256
        expected_canonical = "0" * 64
        expected = reader_case.canonical_mismatch_error
        canonical_failure = False

    path.write_bytes(source)
    _result, error = _capture(
        lambda: reader_case.load(
            path,
            expected_source_sha256=expected_source,
            expected_canonical_sha256=expected_canonical,
        )
    )

    if canonical_failure:
        _assert_canonical_json_error(error, reader_case, expected)
    else:
        _assert_policy_error(error, reader_case, expected)


@requires_held_fd_reader
def test_typed_roundtrip_check_remains_after_canonical_digest_check(
    reader_case: _ReaderCase,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path.resolve() / reader_case.name
    root.mkdir()
    path = root / reader_case.leaf_name
    path.write_bytes(reader_case.source)

    def return_replacement(_cls: type[object], _value: object) -> object:
        return reader_case.typed_replacement

    with monkeypatch.context() as patch:
        patch.setattr(
            reader_case.typed_class,
            "from_dict",
            classmethod(return_replacement),
        )
        _result, error = _capture(
            lambda: reader_case.load(
                path,
                expected_canonical_sha256=(
                    reader_case.typed_replacement.canonical_sha256
                ),
            )
        )

    _assert_policy_error(error, reader_case, reader_case.typed_roundtrip_error)


@dataclass(frozen=True, slots=True)
class _FakeStat:
    st_mode: int = stat.S_IFREG | 0o600
    st_dev: int = 101
    st_ino: int = 202
    st_size: int = 1
    st_mtime_ns: int = 303
    st_ctime_ns: int = 404
    st_nlink: int = 1


class _FakeFileSystem:
    def __init__(
        self,
        *,
        fstats: list[_FakeStat | OSError] | None = None,
        reads: list[bytes | OSError] | None = None,
        open_errors: dict[int, OSError] | None = None,
        close_errors: dict[int, OSError] | None = None,
    ) -> None:
        self.fstats = list(fstats or [])
        self.reads = list(reads or [])
        self.open_errors = dict(open_errors or {})
        self.close_errors = dict(close_errors or {})
        self.events: list[tuple[object, ...]] = []
        self.open_fds: set[int] = set()
        self.open_calls = 0
        self.next_fd = 10

    def open(
        self,
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        del mode
        call_index = self.open_calls
        self.open_calls += 1
        path_text = os.fspath(path)
        pending = self.open_errors.get(call_index)
        if pending is not None:
            self.events.append(("open-error", path_text, dir_fd, flags))
            raise pending
        descriptor = self.next_fd
        self.next_fd += 1
        self.open_fds.add(descriptor)
        self.events.append(("open", path_text, dir_fd, descriptor, flags))
        return descriptor

    def fstat(self, descriptor: int) -> _FakeStat:
        self.events.append(("fstat", descriptor))
        if not self.fstats:
            raise AssertionError("unexpected fstat")
        result = self.fstats.pop(0)
        if isinstance(result, OSError):
            raise result
        return result

    def read(self, descriptor: int, byte_count: int) -> bytes:
        self.events.append(("read", descriptor, byte_count))
        if not self.reads:
            raise AssertionError("unexpected read")
        result = self.reads.pop(0)
        if isinstance(result, OSError):
            raise result
        return result

    def close(self, descriptor: int) -> None:
        self.events.append(("close", descriptor))
        if descriptor not in self.open_fds:
            raise AssertionError(f"descriptor {descriptor} closed twice")
        pending = self.close_errors.get(descriptor)
        if pending is not None:
            raise pending
        self.open_fds.remove(descriptor)


def _run_with_fake_filesystem(
    monkeypatch: pytest.MonkeyPatch,
    reader_case: _ReaderCase,
    fake: _FakeFileSystem,
) -> tuple[object | None, BaseException | None]:
    path = Path("/safe/parent") / reader_case.leaf_name
    with monkeypatch.context() as patch:
        patch.setattr(os, "open", fake.open)
        patch.setattr(os, "fstat", fake.fstat)
        patch.setattr(os, "read", fake.read)
        patch.setattr(os, "close", fake.close)
        return _capture(lambda: reader_case.load(path))


def _close_events(fake: _FakeFileSystem) -> list[int]:
    return [event[1] for event in fake.events if event[0] == "close"]


@requires_held_fd_reader
def test_fake_success_freezes_open_read_stat_and_close_order(
    reader_case: _ReaderCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metadata = _FakeStat(st_size=len(reader_case.source))
    fake = _FakeFileSystem(
        fstats=[metadata, metadata],
        reads=[reader_case.source, b""],
    )

    loaded, error = _run_with_fake_filesystem(monkeypatch, reader_case, fake)

    assert error is None
    assert loaded is not None
    assert getattr(loaded, reader_case.loaded_value_attribute) == (
        reader_case.expected_value
    )
    assert loaded.source_path == Path("/safe/parent") / reader_case.leaf_name
    assert loaded.read_trace == (loaded.source_path,)
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    component_flags = directory_flags | os.O_NOFOLLOW
    leaf_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    assert fake.events == [
        ("open", "/", None, 10, directory_flags),
        ("open", "safe", 10, 11, component_flags),
        ("close", 10),
        ("open", "parent", 11, 12, component_flags),
        ("close", 11),
        ("open", reader_case.leaf_name, 12, 13, leaf_flags),
        ("fstat", 13),
        ("read", 13, 64 * 1024),
        ("read", 13, 64 * 1024),
        ("fstat", 13),
        ("close", 13),
        ("close", 12),
    ]
    assert fake.open_fds == set()


@pytest.mark.parametrize(
    "phase",
    (
        "root_open",
        "parent_open",
        "leaf_open",
        "before_fstat",
        "read",
        "after_fstat",
    ),
)
@requires_held_fd_reader
def test_oserror_phases_preserve_domain_error_direct_cause_and_cleanup(
    reader_case: _ReaderCase,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
) -> None:
    failure = OSError(errno.EIO, f"synthetic {phase} failure")
    metadata = _FakeStat(st_size=len(reader_case.source))
    open_errors: dict[int, OSError] = {}
    fstats: list[_FakeStat | OSError] = []
    reads: list[bytes | OSError] = []

    if phase == "root_open":
        open_errors[0] = failure
        expected_closes: list[int] = []
    elif phase == "parent_open":
        open_errors[2] = failure
        expected_closes = [10, 11]
    elif phase == "leaf_open":
        open_errors[3] = failure
        expected_closes = [10, 11, 12]
    elif phase == "before_fstat":
        fstats = [failure]
        expected_closes = [10, 11, 13, 12]
    elif phase == "read":
        fstats = [metadata]
        reads = [failure]
        expected_closes = [10, 11, 13, 12]
    else:
        assert phase == "after_fstat"
        fstats = [metadata, failure]
        reads = [reader_case.source, b""]
        expected_closes = [10, 11, 13, 12]

    fake = _FakeFileSystem(
        fstats=fstats,
        reads=reads,
        open_errors=open_errors,
    )
    _loaded, error = _run_with_fake_filesystem(monkeypatch, reader_case, fake)
    path = Path("/safe/parent") / reader_case.leaf_name
    expected = (
        reader_case.parent_open_error(path.parent)
        if phase in {"root_open", "parent_open"}
        else reader_case.leaf_read_error(path)
    )

    _assert_os_error(
        error,
        reader_case,
        expected,
        expected_cause=failure,
    )
    assert _close_events(fake) == expected_closes
    assert fake.open_fds == set()


@pytest.mark.parametrize("close_target", ("leaf", "parent"))
@pytest.mark.parametrize(
    "active_policy_failure", (False, True), ids=("success", "policy")
)
@requires_held_fd_reader
def test_close_oserror_escapes_raw_with_active_error_context_and_exact_order(
    reader_case: _ReaderCase,
    monkeypatch: pytest.MonkeyPatch,
    close_target: str,
    active_policy_failure: bool,
) -> None:
    failure = OSError(errno.EIO, f"synthetic {close_target} close failure")
    close_descriptor = 13 if close_target == "leaf" else 12
    if active_policy_failure:
        fstats: list[_FakeStat | OSError] = [_FakeStat(st_mode=stat.S_IFDIR | 0o700)]
        reads: list[bytes | OSError] = []
    else:
        metadata = _FakeStat(st_size=len(reader_case.source))
        fstats = [metadata, metadata]
        reads = [reader_case.source, b""]
    fake = _FakeFileSystem(
        fstats=fstats,
        reads=reads,
        close_errors={close_descriptor: failure},
    )

    loaded, error = _run_with_fake_filesystem(monkeypatch, reader_case, fake)

    assert loaded is None
    assert error is failure
    assert type(error) is OSError
    assert str(error) == str(failure)
    assert error.__cause__ is None
    assert error.__suppress_context__ is False
    if active_policy_failure:
        context = error.__context__
        assert context is not None
        assert type(context) is reader_case.error_type
        assert str(context) == reader_case.regular_file_error
        assert context.__cause__ is None
        assert context.__context__ is None
        assert context.__suppress_context__ is False
    else:
        assert error.__context__ is None

    if close_target == "leaf":
        assert _close_events(fake) == [10, 11, 13]
        assert fake.open_fds == {12, 13}
    else:
        assert _close_events(fake) == [10, 11, 13, 12]
        assert fake.open_fds == {12}


@pytest.mark.parametrize(
    "policy_failure",
    ("non_regular", "multiple_links", "initial_oversize", "streaming_oversize"),
)
@requires_held_fd_reader
def test_policy_failure_order_has_no_cause_and_closes_every_descriptor(
    reader_case: _ReaderCase,
    monkeypatch: pytest.MonkeyPatch,
    policy_failure: str,
) -> None:
    if policy_failure == "non_regular":
        before = _FakeStat(
            st_mode=stat.S_IFDIR | 0o700,
            st_nlink=2,
            st_size=2,
        )
        fake = _FakeFileSystem(fstats=[before])
        expected = reader_case.regular_file_error
    elif policy_failure == "multiple_links":
        before = _FakeStat(st_nlink=2, st_size=2)
        fake = _FakeFileSystem(fstats=[before])
        expected = reader_case.one_link_error
    elif policy_failure == "initial_oversize":
        monkeypatch.setattr(reader_case.module, reader_case.limit_name, 1)
        before = _FakeStat(st_size=2)
        fake = _FakeFileSystem(fstats=[before])
        expected = reader_case.oversize_error
    else:
        assert policy_failure == "streaming_oversize"
        monkeypatch.setattr(reader_case.module, reader_case.limit_name, 1)
        before = _FakeStat(st_size=1)
        fake = _FakeFileSystem(fstats=[before], reads=[b"xx"])
        expected = reader_case.oversize_error

    _loaded, error = _run_with_fake_filesystem(monkeypatch, reader_case, fake)

    _assert_policy_error(error, reader_case, expected)
    assert _close_events(fake) == [10, 11, 13, 12]
    assert fake.open_fds == set()


@pytest.mark.parametrize(
    "identity_field",
    ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_nlink"),
)
@requires_held_fd_reader
def test_each_before_after_identity_drift_is_rejected_without_leaks(
    reader_case: _ReaderCase,
    monkeypatch: pytest.MonkeyPatch,
    identity_field: str,
) -> None:
    before = _FakeStat(st_size=1)
    after = replace(before, **{identity_field: getattr(before, identity_field) + 1})
    fake = _FakeFileSystem(
        fstats=[before, after],
        reads=[b"x", b""],
    )

    _loaded, error = _run_with_fake_filesystem(monkeypatch, reader_case, fake)

    _assert_policy_error(error, reader_case, reader_case.changed_error)
    assert _close_events(fake) == [10, 11, 13, 12]
    assert fake.open_fds == set()


@requires_held_fd_reader
def test_total_byte_count_drift_is_rejected_when_stat_identity_is_unchanged(
    reader_case: _ReaderCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metadata = _FakeStat(st_size=2)
    fake = _FakeFileSystem(
        fstats=[metadata, metadata],
        reads=[b"x", b""],
    )

    _loaded, error = _run_with_fake_filesystem(monkeypatch, reader_case, fake)

    _assert_policy_error(error, reader_case, reader_case.changed_error)
    assert _close_events(fake) == [10, 11, 13, 12]
    assert fake.open_fds == set()
