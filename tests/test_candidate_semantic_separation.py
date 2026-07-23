from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from spirallens.semantics import (
    MinimalPair,
    SemanticAnnotation,
    read_semantic_annotations,
    top_sae_features,
    write_semantic_annotations,
)


def test_semantic_annotation_is_a_sha_bound_sidecar(tmp_path: Path) -> None:
    discovery = tmp_path / "candidate-ledger.jsonl"
    discovery.write_text('{"record_type":"candidate"}\n', encoding="utf-8")
    digest = hashlib.sha256(discovery.read_bytes()).hexdigest()
    output = tmp_path / "semantic-annotations.jsonl"
    annotation = SemanticAnnotation(
        candidate_id="cand_1234567890abcdef12345678",
        annotation_source="held-out-minimal-pairs-v1",
        split="held_out",
        labels={"contrast": "negation"},
        evidence_refs=("pair-17",),
    )

    assert write_semantic_annotations((annotation,), output, discovery_ledger_sha256=digest) == 1
    loaded = list(read_semantic_annotations(output))
    assert loaded == [annotation]
    assert discovery.read_text(encoding="utf-8") == '{"record_type":"candidate"}\n'


def test_sae_summary_has_no_implicit_semantic_label() -> None:
    features = top_sae_features(
        np.array([0.2, 1.5, 1.5, -0.1]),
        top_k=3,
        feature_ids=np.array([40, 30, 20, 10]),
    )
    assert [row["feature_id"] for row in features] == [20, 30, 40]
    assert all(set(row) == {"rank", "feature_id", "activation"} for row in features)

    pair = MinimalPair(
        pair_id="negation-1",
        left_text="The system is active.",
        right_text="The system is not active.",
        contrast_label="negation",
    )
    assert pair.split == "held_out"
