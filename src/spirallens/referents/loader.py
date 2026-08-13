"""Strict one-file loader for canonical referent contract sets."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from spirallens._held_file import _read_bounded_regular_file as _read_held_file
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


def _read_bounded_regular_file(path: Path) -> bytes:
    messages = (
        f"cannot safely open referent contract parent: {path.parent}",
        f"cannot safely read referent contract: {path}",
        "referent contract must be a regular file",
        "referent contract must have exactly one link",
        "referent contract exceeds the size limit",
        "referent contract changed during read",
    )
    return _read_held_file(
        path,
        maximum_bytes=MAX_REFERENT_CONTRACT_SET_BYTES,
        error_type=ReferentContractError,
        messages=messages,
    )


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
