from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from spirallens.referents import (
    MAX_REFERENT_CONTRACT_SET_BYTES,
    ReferentContractError,
    canonical_f0_f4_referent_contracts,
    load_referent_contract_set,
)


def _load(path: Path, source: bytes, canonical_sha256: str):
    return load_referent_contract_set(
        path,
        expected_source_sha256=hashlib.sha256(source).hexdigest(),
        expected_canonical_sha256=canonical_sha256,
    )


def test_loader_reads_only_one_canonical_contract_file(tmp_path: Path) -> None:
    contract_set = canonical_f0_f4_referent_contracts("2" * 64)
    path = tmp_path / "referents.json"
    path.write_bytes(contract_set.canonical_bytes)

    loaded = _load(
        path,
        contract_set.canonical_bytes,
        contract_set.canonical_sha256,
    )

    assert loaded.contract_set == contract_set
    assert loaded.source_path == path.resolve()
    assert loaded.read_trace == (path.resolve(),)
    assert loaded.source_sha256 == contract_set.canonical_sha256


def test_loader_rejects_noncanonical_and_wrong_expected_digest(
    tmp_path: Path,
) -> None:
    contract_set = canonical_f0_f4_referent_contracts("3" * 64)
    pretty_source = json.dumps(
        contract_set.to_dict(),
        indent=2,
        sort_keys=True,
    ).encode("utf-8")
    path = tmp_path / "pretty.json"
    path.write_bytes(pretty_source)

    with pytest.raises(ReferentContractError, match="not canonical JSON"):
        _load(path, pretty_source, contract_set.canonical_sha256)

    path.write_bytes(contract_set.canonical_bytes)
    with pytest.raises(
        ReferentContractError,
        match="source SHA-256 mismatch",
    ):
        load_referent_contract_set(
            path,
            expected_source_sha256="0" * 64,
            expected_canonical_sha256=contract_set.canonical_sha256,
        )


def test_loader_rejects_symlinks_hardlinks_and_oversize(
    tmp_path: Path,
) -> None:
    contract_set = canonical_f0_f4_referent_contracts("4" * 64)
    target = tmp_path / "referents.json"
    target.write_bytes(contract_set.canonical_bytes)

    symlink = tmp_path / "symlink.json"
    symlink.symlink_to(target)
    with pytest.raises(ReferentContractError, match="cannot safely read"):
        _load(
            symlink,
            contract_set.canonical_bytes,
            contract_set.canonical_sha256,
        )

    hardlink = tmp_path / "hardlink.json"
    os.link(target, hardlink)
    with pytest.raises(ReferentContractError, match="exactly one link"):
        _load(
            target,
            contract_set.canonical_bytes,
            contract_set.canonical_sha256,
        )

    oversized = tmp_path / "oversized.json"
    source = b"x" * (MAX_REFERENT_CONTRACT_SET_BYTES + 1)
    oversized.write_bytes(source)
    with pytest.raises(ReferentContractError, match="exceeds the size limit"):
        _load(oversized, source, "0" * 64)
