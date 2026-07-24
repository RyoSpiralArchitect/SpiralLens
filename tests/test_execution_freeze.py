from __future__ import annotations

import copy
from pathlib import Path

import pytest

from spirallens.execution_freeze import (
    _load_protocol_document,
    _validate_candidate_protocol_lineage,
    _validate_neighbor_protocol_lineage,
    distribution_content_sha256,
    validate_subject_audit_execution_freeze,
)


def test_execution_freeze_rejects_untrusted_bytes_before_preflight(
    tmp_path: Path,
) -> None:
    source = b"schema_version: wrong\n"

    with pytest.raises(
        ValueError,
        match="out-of-band SHA-256",
    ):
        validate_subject_audit_execution_freeze(
            document={},
            source_bytes=source,
            source_path=tmp_path / "freeze.yaml",
            expected_sha256="0" * 64,
            manifest_path=tmp_path / "manifest.json",
            manifest_sha256="1" * 64,
            protocol_path=tmp_path / "protocol.yaml",
            protocol_sha256="2" * 64,
            candidate_protocol_path=tmp_path / "candidate.yaml",
            candidate_protocol_sha256="3" * 64,
            recall_gate_path=tmp_path / "gate.yaml",
            recall_gate_sha256="4" * 64,
            output_path=tmp_path / "audit.json",
            layer_index=0,
            comparison_group="layer_index=0",
            global_row_key_sha256="5" * 64,
            query_selection_sha256="6" * 64,
            audit_config_sha256="7" * 64,
            query_count=1,
            query_seed=1,
        )


def test_runtime_distribution_digest_is_content_addressed() -> None:
    digest = distribution_content_sha256("faiss-cpu")

    assert len(digest) == 64
    assert set(digest) <= set("0123456789abcdef")


def test_protocol_lineage_allows_only_reviewed_freeze_delta() -> None:
    root = Path(__file__).resolve().parents[1]
    candidate_path = (
        root
        / "protocols"
        / "pythia70_slot_only_001_layer0_candidate_v0_2.yaml"
    )
    frozen_candidate = _load_protocol_document(
        candidate_path,
        label="frozen candidate",
    )
    _validate_candidate_protocol_lineage(
        parent=_load_protocol_document(
            root / "protocols" / "pythia_candidate_v0_2.yaml",
            label="candidate parent",
        ),
        frozen=frozen_candidate,
        layer_index=0,
    )
    _validate_neighbor_protocol_lineage(
        parent=_load_protocol_document(
            root / "protocols" / "pythia_neighbor_v0_2.yaml",
            label="neighbor parent",
        ),
        frozen=_load_protocol_document(
            root
            / "protocols"
            / "pythia70_slot_only_001_layer0_neighbor_v0_2.yaml",
            label="frozen neighbor",
        ),
        repo_root=root,
        candidate_protocol_path=candidate_path,
        candidate_protocol_sha256=(
            "d6f60d38237825178f4d7c799e27da370049787d47ca999172121f07c84d212e"
        ),
        comparison_group="layer_index=0",
        global_row_key_sha256=(
            "d39cd127bd50f564a8ea13e080f19806a3ce390b9ed4436b49d2701054409c43"
        ),
    )

    forged_candidate = copy.deepcopy(frozen_candidate)
    forged_candidate["claim_ceiling"] = 2
    with pytest.raises(ValueError, match="allowlisted lineage"):
        _validate_candidate_protocol_lineage(
            parent=_load_protocol_document(
                root / "protocols" / "pythia_candidate_v0_2.yaml",
                label="candidate parent",
            ),
            frozen=forged_candidate,
            layer_index=0,
        )
