"""Strict one-file loader for canonical referent contract sets."""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path

from spirallens.core.canonical import CanonicalJsonError, parse_canonical_json

from .common import ReferentContractError, require_sha256
from .contracts import ReferentContractSet

MAX_REFERENT_CONTRACT_SET_BYTES = 1_048_576


@dataclass(frozen=True, slots=True)
class LoadedReferentContractSet:
    """One typed contract set and its exact source identity."""

    contract_set: ReferentContractSet
    source_path: Path
    source_sha256: str
    canonical_sha256: str
    read_trace: tuple[Path, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.contract_set, ReferentContractSet):
            raise TypeError("contract_set must be a ReferentContractSet")
        if not isinstance(self.source_path, Path) or not self.source_path.is_absolute():
            raise TypeError("source_path must be an absolute Path")
        require_sha256(self.source_sha256, label="source_sha256")
        require_sha256(self.canonical_sha256, label="canonical_sha256")
        if self.read_trace != (self.source_path,):
            raise ReferentContractError(
                "referent contract read trace must contain only its source"
            )


def _absolute_file(path: str | Path) -> Path:
    value = Path(os.path.abspath(Path(path)))
    if not value.name:
        raise ReferentContractError("referent contract path must name one file")
    return value


def _open_directory_chain(directory: Path) -> int:
    if not directory.is_absolute():
        raise ReferentContractError(
            "referent contract parent directory must be absolute"
        )
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    descriptor = os.open("/", flags)
    try:
        for component in directory.parts[1:]:
            next_flags = flags
            if hasattr(os, "O_NOFOLLOW"):
                next_flags |= os.O_NOFOLLOW
            next_descriptor = os.open(
                component,
                next_flags,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = next_descriptor
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _read_bounded_regular_file(path: Path) -> bytes:
    try:
        parent_descriptor = _open_directory_chain(path.parent)
    except OSError as error:
        raise ReferentContractError(
            f"cannot safely open referent contract parent: {path.parent}"
        ) from error
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = -1
    try:
        descriptor = os.open(path.name, flags, dir_fd=parent_descriptor)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ReferentContractError("referent contract must be a regular file")
        if before.st_nlink != 1:
            raise ReferentContractError("referent contract must have exactly one link")
        if before.st_size > MAX_REFERENT_CONTRACT_SET_BYTES:
            raise ReferentContractError("referent contract exceeds the size limit")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, 64 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_REFERENT_CONTRACT_SET_BYTES:
                raise ReferentContractError("referent contract exceeds the size limit")
            chunks.append(chunk)
        after = os.fstat(descriptor)
        before_identity = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
            before.st_nlink,
        )
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
            after.st_nlink,
        )
        if before_identity != after_identity or total != after.st_size:
            raise ReferentContractError("referent contract changed during read")
        return b"".join(chunks)
    except OSError as error:
        raise ReferentContractError(
            f"cannot safely read referent contract: {path}"
        ) from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        os.close(parent_descriptor)


def load_referent_contract_set(
    path: str | Path,
    *,
    expected_source_sha256: str,
    expected_canonical_sha256: str,
) -> LoadedReferentContractSet:
    """Load exactly one canonical contract file without any payload access."""

    expected_source = require_sha256(
        expected_source_sha256,
        label="expected_source_sha256",
    )
    expected_canonical = require_sha256(
        expected_canonical_sha256,
        label="expected_canonical_sha256",
    )
    source_path = _absolute_file(path)
    source = _read_bounded_regular_file(source_path)
    source_sha256 = hashlib.sha256(source).hexdigest()
    if source_sha256 != expected_source:
        raise ReferentContractError("referent contract source SHA-256 mismatch")
    try:
        parsed = parse_canonical_json(source, label="referent contract")
    except CanonicalJsonError as error:
        raise ReferentContractError(str(error)) from error
    if not isinstance(parsed, dict):
        raise ReferentContractError("referent contract must contain one object")
    contract_set = ReferentContractSet.from_dict(parsed)
    canonical_sha256 = contract_set.canonical_sha256
    if canonical_sha256 != expected_canonical:
        raise ReferentContractError("referent contract canonical SHA-256 mismatch")
    if contract_set.canonical_bytes != source:
        raise ReferentContractError("referent contract typed round-trip differs")
    return LoadedReferentContractSet(
        contract_set=contract_set,
        source_path=source_path,
        source_sha256=source_sha256,
        canonical_sha256=canonical_sha256,
        read_trace=(source_path,),
    )
