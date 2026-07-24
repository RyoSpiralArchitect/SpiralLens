from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml

from spirallens.atlas import ContextBankBinding
from spirallens.audit_output import reserve_audit_output
from spirallens.contexts import (
    BankStatus,
    ContextBank,
    ContextRole,
    ContextSpec,
    LoadedContextBank,
    ModelBinding,
    SourceBinding,
    SweepDomain,
    TokenizerBinding,
)
from spirallens.metrics import (
    CandidateSearchConfig,
    NeighborAuditConfig,
    NeighborAuditProtocolBinding,
    NeighborQuerySelectionContract,
    decompose_difference,
    extract_candidates_from_manifest,
    iter_candidate_pairs,
    load_candidate_config_from_protocol,
    load_neighbor_audit_receipt,
    write_neighbor_audit,
    write_candidate_ledger,
)
from spirallens.metrics.candidate_pairs import (
    _audit_neighbor_backend_from_manifest,
    _validate_neighbor_audit_atlas_scope,
    atlas_global_row_key_sha256,
    read_candidate_records,
)
from spirallens.neighbors import (
    FaissHNSWBackend,
    FaissHNSWConfig,
    canonical_json_sha256,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_sha256(value: dict[str, object]) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


class _TestExecutionFreeze:
    def revalidate(self) -> None:
        return None

    def validate_subject_backend(self, descriptor: object) -> None:
        del descriptor


def _write_recall_gate_contract(
    tmp_path: Path,
    audit_config: NeighborAuditConfig,
) -> Path:
    source = (
        Path(__file__).resolve().parents[1]
        / "protocols"
        / "neighbor_recall_gate_v0_1.yaml"
    )
    document = yaml.safe_load(source.read_text(encoding="utf-8"))
    document["gate_id"] = "faiss-candidate-recall-gate-v0.1"
    document["thresholds"].update(
        {
            "aggregate_candidate_recall_min": (
                audit_config.candidate_recall_min
            ),
            "query_local_recall_min": (
                audit_config.query_local_recall_min
            ),
            "density_macro_and_joint_stratum_recall_min": (
                audit_config.stratum_recall_min
            ),
            "boundary_shell_width": (
                audit_config.boundary_shell_width
            ),
            "repeats": audit_config.repeats,
        }
    )
    document["support"].update(
        {
            "minimum_reference_candidates": (
                audit_config.minimum_reference_candidates
            ),
            "minimum_eligible_queries": (
                audit_config.minimum_eligible_queries
            ),
            "minimum_eligible_query_fraction": (
                audit_config.minimum_eligible_query_fraction
            ),
            "density_strata_count": audit_config.density_strata_count,
            "minimum_eligible_queries_per_density_stratum": (
                audit_config
                .minimum_eligible_queries_per_density_stratum
            ),
            "minimum_reference_candidates_per_joint_stratum": (
                audit_config.minimum_reference_candidates_per_stratum
            ),
        }
    )
    path = tmp_path / "faiss-recall-gate.yaml"
    path.write_text(
        yaml.safe_dump(document, sort_keys=False),
        encoding="utf-8",
    )
    return path


def _write_rehashed_ledger(
    path: Path,
    records: list[dict[str, Any]],
) -> None:
    body_lines = [
        json.dumps(
            record,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
        for record in records[:-1]
    ]
    footer = records[-1]
    footer_without_digest = dict(footer)
    footer_without_digest.pop("content_sha256")
    footer_identity = (
        json.dumps(
            footer_without_digest,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )
    footer["content_sha256"] = hashlib.sha256(
        "".join(body_lines + [footer_identity]).encode("utf-8")
    ).hexdigest()
    path.write_text(
        "".join(
            body_lines
            + [
                json.dumps(
                    footer,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            ]
        ),
        encoding="utf-8",
    )


def _refresh_candidate_id(candidate: dict[str, Any]) -> None:
    identity = {
        "source_run_id": candidate["source_run_id"],
        "group_key": candidate["comparison_group"],
        "left": candidate["left"],
        "right": candidate["right"],
    }
    candidate["candidate_id"] = (
        "cand_"
        + hashlib.sha256(
            json.dumps(
                identity,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()[:24]
    )


def _slice_sha256(
    name: str,
    array: np.ndarray,
    *,
    start_row: int,
    end_row: int,
) -> str:
    view = np.ascontiguousarray(array[start_row:end_row])
    header = {
        "schema_version": "spirallens.activation_atlas.v2",
        "array": name,
        "start_row": start_row,
        "end_row": end_row,
        "shape": list(view.shape),
        "dtype": str(view.dtype),
    }
    digest = hashlib.sha256()
    digest.update(
        json.dumps(
            header,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    )
    digest.update(b"\0")
    digest.update(memoryview(view).cast("B"))
    return digest.hexdigest()


def _write_atlas(
    tmp_path: Path,
    *,
    status: str = "complete",
    recall_gate_fixture: bool = False,
) -> Path:
    token_ids = np.array(
        [0, 1, 2, 3]
        if recall_gate_fixture
        else [11, 12, 13],
        dtype=np.int64,
    )
    if recall_gate_fixture:
        resid_pre = np.array(
            [
                [[1.0, 0.0, 0.0]],
                [[1.0, 0.001, 0.0]],
                [[1.0, -0.001, 0.0]],
                [[0.0, 1.0, 0.0]],
            ],
            dtype=np.float32,
        )
        drift = np.array(
            [
                [[0.0, 1.0, 0.0]],
                [[0.0, -1.0, 0.0]],
                [[0.0, 1.0, 0.0]],
                [[0.0, 0.1, 0.0]],
            ],
            dtype=np.float32,
        )
    else:
        resid_pre = np.array(
            [
                [[1.0, 0.0, 0.0]],
                [[0.9999995, 0.001, 0.0]],
                [[0.0, 1.0, 0.0]],
            ],
            dtype=np.float32,
        )
        drift = np.array(
            [
                [[0.0, 1.0, 0.0]],
                [[0.0, -1.0, 0.0]],
                [[0.0, 0.1, 0.0]],
            ],
            dtype=np.float32,
        )
    arrays = {
        "token_ids": token_ids,
        "resid_pre": resid_pre,
        "resid_post": resid_pre + drift,
        "norm_summary": np.stack(
            (
                np.linalg.norm(resid_pre, axis=-1),
                np.linalg.norm(resid_pre + drift, axis=-1),
            ),
            axis=-1,
        ).astype(np.float32),
        "logit_summary": np.zeros((token_ids.shape[0], 6), dtype=np.float32),
        "prediction_ids": np.zeros(token_ids.shape[0], dtype=np.int64),
    }
    columns = {
        "norm_summary": ["resid_pre_l2", "resid_post_l2"],
        "logit_summary": [
            "max_logit",
            "mean_logit",
            "std_logit",
            "logsumexp_logit",
            "entropy_nats",
            "input_token_logit",
        ],
    }
    descriptors: dict[str, dict[str, object]] = {}
    for name, array in arrays.items():
        path = tmp_path / f"{name}.npy"
        np.save(path, array, allow_pickle=False)
        descriptors[name] = {
            "path": path.name,
            "shape": list(array.shape),
            "dtype": str(array.dtype),
            "sha256": _sha256(path),
        }
        if name in columns:
            descriptors[name]["columns"] = columns[name]

    token_digest = hashlib.sha256(
        np.asarray(token_ids, dtype="<i8", order="C").tobytes(order="C")
    ).hexdigest()
    total_rows = int(token_ids.shape[0])
    completed_rows = total_rows if status == "complete" else 2
    capture = {
        "atlas_schema_version": "spirallens.activation_atlas.v2",
        "capture_implementation": {
            "name": "candidate-test-fixture",
            "version": "test.v1",
            "accelerator_to_cpu_copy": "synchronous",
            "activation_dtype": "float32",
        },
        "spirallens_version": "test",
        "torch_version": "test",
        "transformers_version": "test",
        "effective_parameter_layout": [
            {
                "device": "cpu",
                "dtype": "float32",
                "parameter_tensors": 1,
                "parameter_values": 1,
            }
        ],
    }
    capture_fingerprint = _json_sha256(capture)
    batch_commit = {
        "batch_index": 0,
        "start_row": 0,
        "end_row": completed_rows,
        "committed_at": "2026-01-01T00:00:00+00:00",
        "array_sha256": {
            name: _slice_sha256(
                name,
                array,
                start_row=0,
                end_row=completed_rows,
            )
            for name, array in sorted(arrays.items())
        },
    }
    manifest = {
        "schema_version": "spirallens.activation_atlas.v2",
        "status": status,
        "run_id": "atlas-test-run",
        "run_fingerprint": "f" * 64,
        "capture": capture,
        "capture_fingerprint": capture_fingerprint,
        "request": {
            "model_id": "test/pythia",
            "model_revision": "test-revision",
            "context_ids": [0, 1],
            "attention_mask": [1, 1],
            "position": 1,
            "selection": {
                "kind": "subset",
                "subset_size_before_limit": total_rows,
            },
            "num_tokens": total_rows,
            "token_ids_sha256": token_digest,
            "capture_dtype": "float32",
            "capture_fingerprint": capture_fingerprint,
            "config_sha256": "c" * 64,
        },
        "model": {
            "architecture": "GPTNeoXForCausalLM",
            "num_layers": 1,
            "hidden_size": 3,
            "vocab_size": 100,
            "config": {},
            "rope": {"rotary_pct": 0.25},
        },
        "arrays": descriptors,
        "progress": {
            "completed_rows": completed_rows,
            "total_rows": total_rows,
            "committed_batches": 1,
        },
        "attempts": [
            {
                "started_at": "2026-01-01T00:00:00+00:00",
                "resume_from_row": 0,
                "batch_size": total_rows,
                "capture": capture,
                "capture_fingerprint": capture_fingerprint,
            }
        ],
        "batch_commits": [batch_commit],
        "environment": {},
        "summaries": {},
        "failure": None,
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def _write_bound_atlas(
    tmp_path: Path,
    *,
    recall_gate_fixture: bool = False,
    full_vocabulary: bool = False,
) -> Path:
    manifest_path = _write_atlas(
        tmp_path,
        recall_gate_fixture=recall_gate_fixture,
    )
    token_ids = np.load(
        tmp_path / "token_ids.npy",
        allow_pickle=False,
    )
    vocabulary_size = (
        int(token_ids.shape[0])
        if full_vocabulary
        else 100
    )
    tokenizer_addressable_size = (
        vocabulary_size
        if full_vocabulary
        else 12
    )
    context = ContextSpec(
        context_id="bound-candidate-context",
        role=ContextRole.EXAMPLE,
        family_id="candidate-family",
        source_id="candidate-source",
        template_id="candidate-template",
        template_ids=(0, None),
        attention_mask=(1, 1),
        observation_position=1,
    )
    bank = ContextBank(
        bank_id="bound-candidate-bank",
        status=BankStatus.EXAMPLE,
        license="Apache-2.0",
        claim_eligible=False,
        source=SourceBinding(
            kind="project_authored_synthetic",
            source_id="candidate-fixture",
        ),
        model=ModelBinding(
            model_id="test/pythia",
            requested_revision="test",
            resolved_revision="a" * 40,
            vocab_size=vocabulary_size,
        ),
        tokenizer=TokenizerBinding(
            tokenizer_id="test/tokenizer",
            requested_revision="test",
            resolved_revision="b" * 40,
            addressable_size=tokenizer_addressable_size,
            tokenizer_class="TestTokenizer",
            implementation="fast",
            transformers_version="test",
            tokenizers_version="test",
            add_special_tokens=False,
            file_sha256=(("tokenizer.json", "8" * 64),),
        ),
        sweep_domain=SweepDomain.MODEL_EMBEDDING_ROWS,
        contexts=(context,),
    )
    binding = ContextBankBinding(
        loaded=LoadedContextBank(
            bank=bank,
            source_path=tmp_path / "bound-context-bank.yaml",
            source_sha256="9" * 64,
            canonical_sha256=bank.sha256,
        ),
        context_id=context.context_id,
        role=ContextRole.EXAMPLE,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    request = manifest["request"]
    request.update(
        {
            "requested_model_revision": "a" * 40,
            "resolved_model_revision": "a" * 40,
            "context_ids": [0, 0],
            "observation_position": 1,
            "sweep_position": 1,
            "context_bank_binding": binding.to_dict(),
            "context_bank_binding_sha256": binding.sha256,
            "token_domain": {
                "kind": "model_embedding_rows",
                "size": vocabulary_size,
                "model_vocab_size": vocabulary_size,
                "tokenizer_addressable_size": (
                    tokenizer_addressable_size
                ),
            },
            "language_space_atlas": False,
            "semantic_unit": False,
        }
    )
    if full_vocabulary:
        request["selection"] = {
            "kind": "full_vocabulary",
            "subset_size_before_limit": vocabulary_size,
            "max_tokens": None,
        }
    request_identity = dict(request)
    request_identity.pop("batch_size_initial", None)
    request_identity.pop("batch_size_latest", None)
    request["request_identity_sha256"] = _json_sha256(request_identity)
    manifest["model"].update(
        {
            "model_id": "test/pythia",
            "resolved_revision": "a" * 40,
            "vocab_size": vocabulary_size,
        }
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def test_neighbor_audit_scope_rejects_unbound_atlas(
    tmp_path: Path,
) -> None:
    manifest_path = _write_atlas(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    token_ids = np.load(tmp_path / "token_ids.npy", allow_pickle=False)

    with pytest.raises(
        ValueError,
        match="ContextBank-bound atlas",
    ):
        _validate_neighbor_audit_atlas_scope(
            manifest=manifest,
            token_ids=token_ids,
            layer_index=0,
        )


def test_neighbor_audit_scope_requires_exact_ordered_full_vocabulary(
    tmp_path: Path,
) -> None:
    manifest_path = _write_bound_atlas(
        tmp_path,
        recall_gate_fixture=True,
        full_vocabulary=True,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    token_ids = np.load(tmp_path / "token_ids.npy", allow_pickle=False)

    _validate_neighbor_audit_atlas_scope(
        manifest=manifest,
        token_ids=token_ids,
        layer_index=0,
    )
    with pytest.raises(
        ValueError,
        match=r"ordered token_ids 0\.\.vocab_size-1",
    ):
        _validate_neighbor_audit_atlas_scope(
            manifest=manifest,
            token_ids=token_ids[::-1],
            layer_index=0,
        )


def test_neighbor_audit_scope_rejects_partial_atlas(
    tmp_path: Path,
) -> None:
    manifest_path = _write_bound_atlas(
        tmp_path,
        recall_gate_fixture=True,
        full_vocabulary=True,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    token_ids = np.load(tmp_path / "token_ids.npy", allow_pickle=False)
    manifest["status"] = "in_progress"
    manifest["progress"]["completed_rows"] = 2

    with pytest.raises(
        ValueError,
        match="complete, layer-compatible atlas",
    ):
        _validate_neighbor_audit_atlas_scope(
            manifest=manifest,
            token_ids=token_ids,
            layer_index=0,
        )


def test_global_row_key_ignores_capture_instance_metadata(
    tmp_path: Path,
) -> None:
    manifest_path = _write_bound_atlas(
        tmp_path,
        recall_gate_fixture=True,
        full_vocabulary=True,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    token_ids = np.load(tmp_path / "token_ids.npy", allow_pickle=False)
    original = atlas_global_row_key_sha256(
        token_ids=token_ids,
        request=manifest["request"],
    )
    recaptured_request = dict(manifest["request"])
    recaptured_request.update(
        {
            "batch_size_initial": 999,
            "batch_size_latest": 1,
            "capture_fingerprint": "1" * 64,
            "config_sha256": "2" * 64,
        }
    )

    assert (
        atlas_global_row_key_sha256(
            token_ids=token_ids,
            request=recaptured_request,
        )
        == original
    )
    changed_scope = dict(recaptured_request)
    changed_scope["observation_position"] = 0
    assert (
        atlas_global_row_key_sha256(
            token_ids=token_ids,
            request=changed_scope,
        )
        != original
    )


def test_manifest_subject_audit_rejects_draft_before_backend_or_io(
    tmp_path: Path,
) -> None:
    protocol = NeighborAuditProtocolBinding(
        protocol_id="draft-test",
        status="preregistered-draft",
        source_sha256="a" * 64,
        candidate_config_sha256="b" * 64,
        audit_config_sha256="c" * 64,
        query_selection=NeighborQuerySelectionContract(
            seed=1,
            count=1,
            global_row_key_sha256="d" * 64,
        ),
    )
    candidate_config = CandidateSearchConfig(layer_indices=(0,))

    with pytest.raises(
        ValueError,
        match="require a frozen protocol binding",
    ):
        _audit_neighbor_backend_from_manifest(
            tmp_path / "missing-manifest.json",
            layer_index=0,
            subject_backend_factory=lambda _: pytest.fail(
                "backend factory must not run"
            ),
            protocol_binding=protocol,
            candidate_config=candidate_config,
            audit_config=NeighborAuditConfig(),
            execution_freeze=object(),
        )


def test_manifest_subject_audit_rejects_bare_freeze_digest(
    tmp_path: Path,
) -> None:
    protocol = NeighborAuditProtocolBinding(
        protocol_id="frozen-test",
        status="frozen",
        source_sha256="a" * 64,
        candidate_config_sha256="b" * 64,
        audit_config_sha256="c" * 64,
        query_selection=NeighborQuerySelectionContract(
            seed=1,
            count=1,
            global_row_key_sha256="d" * 64,
        ),
    )

    with pytest.raises(
        TypeError,
        match="validated execution-freeze capability",
    ):
        _audit_neighbor_backend_from_manifest(
            tmp_path / "missing-manifest.json",
            layer_index=0,
            subject_backend_factory=lambda _: pytest.fail(
                "backend factory must not run"
            ),
            protocol_binding=protocol,
            candidate_config=CandidateSearchConfig(
                layer_indices=(0,)
            ),
            audit_config=NeighborAuditConfig(),
            execution_freeze="e" * 64,
        )


def test_norm_decomposition_reconstructs_euclidean_distance() -> None:
    left = np.array([2.0, 0.0])
    right = np.array([0.0, 3.0])
    result = decompose_difference(left, right)

    assert result.radial_distance == pytest.approx(1.0)
    assert result.angular_distance == pytest.approx(np.sqrt(12.0))
    assert result.euclidean_distance == pytest.approx(np.sqrt(13.0))
    assert result.euclidean_distance**2 == pytest.approx(
        result.radial_distance**2 + result.angular_distance**2
    )


def test_blockwise_search_finds_only_norm_matched_divergent_pair() -> None:
    states = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.9999995, 0.001, 0.0],
            [1.2, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ]
    )
    drifts = np.array(
        [
            [0.0, 1.0, 0.0],
            [0.0, -1.0, 0.0],
            [0.0, -1.0, 0.0],
            [0.0, 0.1, 0.0],
        ]
    )
    config = CandidateSearchConfig(
        cosine_min=0.999,
        relative_norm_gap_max=0.05,
        drift_relative_divergence_min=1.5,
        block_size=1,
    )
    records = list(
        iter_candidate_pairs(
            states,
            drifts,
            references=[{"token_id": index} for index in range(4)],
            config=config,
            source_run_id="block-test",
            group_key="layer_index=0",
        )
    )

    assert len(records) == 1
    candidate = records[0]
    assert candidate["left"]["token_id"] == 0
    assert candidate["right"]["token_id"] == 1
    assert candidate["candidate_kind"] == "cosine_near_drift_divergent"
    assert candidate["discovery"] == {
        "semantic_annotation_used": False,
        "sae_annotation_used": False,
        "projection_used": False,
    }
    assert candidate["state_metrics"]["relative_norm_gap"] < 1e-6
    assert candidate["drift_metrics"]["relative_divergence"] == pytest.approx(2.0)


def test_manifest_extraction_writes_complete_auditable_ledger(tmp_path: Path) -> None:
    manifest_path = _write_atlas(tmp_path)
    ledger_path = tmp_path / "candidate-ledger.jsonl"
    config = CandidateSearchConfig(
        cosine_min=0.999,
        relative_norm_gap_max=0.05,
        drift_relative_divergence_min=1.5,
        block_size=1,
    )

    summary = extract_candidates_from_manifest(
        manifest_path,
        ledger_path,
        config=config,
    )
    candidates = list(read_candidate_records(ledger_path))
    rows = [json.loads(line) for line in ledger_path.read_text().splitlines()]

    assert summary.candidate_count == 1
    assert len(candidates) == 1
    assert rows[0]["record_type"] == "ledger_header"
    assert rows[0]["schema_version"] == (
        "spirallens.candidate-ledger.v0.3"
    )
    assert rows[0]["source"]["atlas_run_id"] == "atlas-test-run"
    retrieval = rows[0]["source"]["neighbor_retrieval"]
    assert retrieval["schema_version"] == (
        "spirallens.neighbor-retrieval-binding.v0.1"
    )
    group = retrieval["groups"]["layer_index=0"]
    assert group["exact_rerank_required"] is True
    assert group["backend_score_used_for_gates"] is False
    assert group["audit_receipt"] is None
    assert rows[0]["current_claim_level"] == 1
    assert rows[0]["protocol_claim_ceiling"] == 1
    assert rows[0]["protocol"] == {
        "claim_ceiling": 1,
        "declared_id": "ad-hoc-v0.1",
    }
    assert "claim_ceiling" not in rows[0]
    assert rows[0]["discovery_contract"]["candidate_is_not_verified_vortex"] is True
    assert rows[-1]["record_type"] == "ledger_footer"
    assert rows[-1]["status"] == "complete"
    assert len(rows[-1]["content_sha256"]) == 64
    assert rows[-1]["candidate_count_by_group"] == {"layer_index=0": 1}
    assert candidates[0]["left"]["layer_index"] == 0
    assert candidates[0]["left"]["token_id"] == 11
    assert candidates[0]["right"]["token_id"] == 12
    assert candidates[0]["schema_version"] == "spirallens.candidate.v0.3"
    assert candidates[0]["retrieval"]["exact_reranked"] is True
    assert candidates[0]["retrieval"][
        "backend_score_used_for_gates"
    ] is False
    wrong_run_path = tmp_path / "wrong-run.jsonl"
    with pytest.raises(ValueError, match="only through"):
        write_candidate_ledger(
            candidates,
            wrong_run_path,
            source={
                **rows[0]["source"],
                "atlas_run_id": "different-atlas-run",
            },
            config=config,
            protocol_id="ad-hoc-v0.1",
        )
    assert not wrong_run_path.exists()

    forged_rows = json.loads(json.dumps(rows))
    forged_candidate = forged_rows[1]
    forged_candidate["source_run_id"] = "different-atlas-run"
    _refresh_candidate_id(forged_candidate)
    forged_path = tmp_path / "forged-run.jsonl"
    _write_rehashed_ledger(forged_path, forged_rows)
    with pytest.raises(ValueError, match="differs from the ledger source"):
        list(read_candidate_records(forged_path))

    wrong_layer_config = CandidateSearchConfig(
        cosine_min=0.999,
        relative_norm_gap_max=0.05,
        drift_relative_divergence_min=1.5,
        block_size=1,
        layer_indices=(1,),
    )
    with pytest.raises(ValueError, match="layer scope differs"):
        write_candidate_ledger(
            candidates,
            tmp_path / "wrong-layer-scope.jsonl",
            source=rows[0]["source"],
            config=wrong_layer_config,
            protocol_id="ad-hoc-v0.1",
        )
    impossible_candidate = json.loads(json.dumps(candidates[0]))
    impossible_candidate["state_metrics"]["cosine_similarity"] = 2.0
    with pytest.raises(ValueError, match="metric domain"):
        write_candidate_ledger(
            (impossible_candidate,),
            tmp_path / "impossible-metric.jsonl",
            source={
                "kind": "unit-test",
                "neighbor_retrieval": rows[0]["source"][
                    "neighbor_retrieval"
                ],
            },
            config=config,
            protocol_id="ad-hoc-v0.1",
        )

    malformed_cases = (
        (
            "current-claim",
            lambda forged: forged[0].__setitem__(
                "current_claim_level",
                True,
            ),
            "header is invalid",
        ),
        (
            "claim-ceiling",
            lambda forged: (
                forged[0].__setitem__("protocol_claim_ceiling", 999),
                forged[0]["protocol"].__setitem__(
                    "claim_ceiling",
                    999,
                ),
            ),
            "header is invalid",
        ),
        (
            "candidate-claim",
            lambda forged: forged[1].__setitem__("claim_level", True),
            "record shape",
        ),
        (
            "metric-domain",
            lambda forged: forged[1]["state_metrics"].__setitem__(
                "cosine_similarity",
                2.0,
            ),
            "metric domain",
        ),
        (
            "metric-fraction",
            lambda forged: forged[1]["state_metrics"].__setitem__(
                "angular_fraction_sq",
                -10.0,
            ),
            "metric identities",
        ),
        (
            "metric-distance",
            lambda forged: forged[1]["state_metrics"].__setitem__(
                "euclidean_distance",
                -1.0,
            ),
            "metric identities",
        ),
        (
            "row-bound",
            lambda forged: (
                forged[1]["right"].__setitem__("row_index", 999),
                _refresh_candidate_id(forged[1]),
            ),
            "row identity",
        ),
        (
            "layer-bound",
            lambda forged: (
                forged[1]["left"].__setitem__("layer_index", 99),
                forged[1]["right"].__setitem__("layer_index", 99),
                _refresh_candidate_id(forged[1]),
            ),
            "reference layer",
        ),
        (
            "discovery-contract",
            lambda forged: forged[0][
                "discovery_contract"
            ].__setitem__("semantic_annotation_used", True),
            "discovery contract",
        ),
        (
            "config-layer",
            lambda forged: forged[0][
                "candidate_search"
            ].__setitem__("layer_indices", [1]),
            "layer scope differs",
        ),
    )
    for suffix, mutate, message in malformed_cases:
        malformed = json.loads(json.dumps(rows))
        mutate(malformed)
        malformed_path = tmp_path / f"malformed-{suffix}.jsonl"
        _write_rehashed_ledger(malformed_path, malformed)
        with pytest.raises(ValueError, match=message):
            list(read_candidate_records(malformed_path))


def test_candidate_ledger_reader_rejects_content_tamper(
    tmp_path: Path,
) -> None:
    manifest_path = _write_atlas(tmp_path)
    ledger_path = tmp_path / "tamper-ledger.jsonl"
    extract_candidates_from_manifest(
        manifest_path,
        ledger_path,
        config=CandidateSearchConfig(
            cosine_min=0.999,
            relative_norm_gap_max=0.05,
            drift_relative_divergence_min=1.5,
            block_size=1,
        ),
    )
    rows = ledger_path.read_text(encoding="utf-8").splitlines()
    candidate = json.loads(rows[1])
    candidate["state_metrics"]["cosine_similarity"] = 0.0
    rows[1] = json.dumps(
        candidate,
        sort_keys=True,
        separators=(",", ":"),
    )
    ledger_path.write_text(
        "\n".join(rows) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="declared gates|content digest mismatch",
    ):
        list(read_candidate_records(ledger_path))


def test_candidate_ledger_reader_rejects_rehashed_receipt_bypass(
    tmp_path: Path,
) -> None:
    manifest_path = _write_atlas(tmp_path)
    ledger_path = tmp_path / "forged-ledger.jsonl"
    extract_candidates_from_manifest(
        manifest_path,
        ledger_path,
        config=CandidateSearchConfig(
            cosine_min=0.999,
            relative_norm_gap_max=0.05,
            drift_relative_divergence_min=1.5,
            block_size=1,
        ),
    )
    records = [
        json.loads(line)
        for line in ledger_path.read_text(encoding="utf-8").splitlines()
    ]
    header, candidate, footer = records
    group = header["source"]["neighbor_retrieval"]["groups"][
        "layer_index=0"
    ]
    group["backend"]["kind"] = "approximate"
    group["backend_sha256"] = _json_sha256(group["backend"])
    candidate["retrieval"]["backend_kind"] = "approximate"
    candidate["retrieval"]["backend_sha256"] = group["backend_sha256"]
    canonical_lines = [
        json.dumps(
            record,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
        for record in (header, candidate)
    ]
    footer_without_digest = dict(footer)
    footer_without_digest.pop("content_sha256")
    footer_identity = (
        json.dumps(
            footer_without_digest,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )
    footer["content_sha256"] = hashlib.sha256(
        "".join(canonical_lines + [footer_identity]).encode("utf-8")
    ).hexdigest()
    ledger_path.write_text(
        "".join(
            canonical_lines
            + [
                json.dumps(
                    footer,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="audit receipt"):
        list(read_candidate_records(ledger_path))


def test_bound_candidate_references_keep_context_identity_and_domain(
    tmp_path: Path,
) -> None:
    manifest_path = _write_bound_atlas(tmp_path)
    ledger_path = tmp_path / "bound-candidates.jsonl"
    config = CandidateSearchConfig(
        cosine_min=0.999,
        relative_norm_gap_max=0.05,
        drift_relative_divergence_min=1.5,
        block_size=1,
    )

    summary = extract_candidates_from_manifest(
        manifest_path,
        ledger_path,
        config=config,
    )
    candidate = list(read_candidate_records(ledger_path))[0]

    assert summary.candidate_count == 1
    assert candidate["left"]["context_id"] == "bound-candidate-context"
    assert candidate["left"]["context_role"] == "example"
    assert candidate["left"]["context_entry_order_index"] == 0
    assert candidate["left"]["context_template_ids"] == [0, None]
    assert candidate["left"]["context_bank_sha256"]
    assert candidate["left"]["context_spec_sha256"]
    assert candidate["left"]["observation_position"] == 1
    assert candidate["left"]["sweep_position"] == 1
    assert candidate["left"]["sweep_domain"] == "model_embedding_rows"
    assert candidate["left"]["tokenizer_addressable"] is True
    assert candidate["right"]["token_id"] == 12
    assert candidate["right"]["tokenizer_addressable"] is False


def test_manifest_faiss_extraction_requires_and_binds_passing_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if importlib.util.find_spec("faiss") is None:
        pytest.skip("faiss optional dependency is absent")
    manifest_path = _write_bound_atlas(
        tmp_path,
        recall_gate_fixture=True,
        full_vocabulary=True,
    )
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    token_ids = np.load(tmp_path / "token_ids.npy", allow_pickle=False)
    row_identity_sha256 = atlas_global_row_key_sha256(
        token_ids=token_ids,
        request=manifest["request"],
    )
    candidate_config = CandidateSearchConfig(
        cosine_min=0.999,
        relative_norm_gap_max=0.05,
        drift_relative_divergence_min=1.5,
        block_size=1,
        layer_indices=(0,),
    )
    audit_config = NeighborAuditConfig(
        minimum_reference_candidates=1,
        minimum_eligible_queries=1,
        minimum_eligible_query_fraction=0.0,
        density_strata_count=1,
        minimum_eligible_queries_per_density_stratum=1,
        boundary_shell_width=0.000999,
        minimum_reference_candidates_per_stratum=1,
    )
    selection = NeighborQuerySelectionContract(
        seed=23,
        count=int(token_ids.shape[0]),
        global_row_key_sha256=row_identity_sha256,
    )
    faiss_config = FaissHNSWConfig(
        m=4,
        ef_construction=40,
        ef_search=40,
        query_batch_size=2,
        score_margin=audit_config.boundary_shell_width,
    )
    candidate_path = tmp_path / "faiss-candidate.yaml"
    candidate_document = yaml.safe_load(
        (
            Path(__file__).resolve().parents[1]
            / "protocols"
            / "pythia_candidate_v0_2.yaml"
        ).read_text(encoding="utf-8")
    )
    candidate_document["protocol_id"] = (
        "faiss-candidate-test-v0.2"
    )
    candidate_document["status"] = "frozen"
    candidate_document["candidate_search"] = (
        candidate_config.to_dict()
    )
    candidate_path.write_text(
        yaml.safe_dump(candidate_document, sort_keys=False),
        encoding="utf-8",
    )
    candidate_sha256 = hashlib.sha256(
        candidate_path.read_bytes()
    ).hexdigest()
    recall_gate_path = _write_recall_gate_contract(
        tmp_path,
        audit_config,
    )
    neighbor_path = tmp_path / "faiss-neighbor.yaml"
    neighbor_path.write_text(
        yaml.safe_dump(
                {
                    "schema_version": (
                        "spirallens.neighbor-audit-protocol.v0.2"
                    ),
                    "protocol_id": "faiss-manifest-test-v0.1",
                    "status": "frozen",
                    "claim_ceiling": 1,
                    "recall_gate_contract": {
                        "path": recall_gate_path.name,
                        "sha256": hashlib.sha256(
                            recall_gate_path.read_bytes()
                        ).hexdigest(),
                        "gate_id": (
                            "faiss-candidate-recall-gate-v0.1"
                        ),
                    },
                "audit_scope": {
                    "comparison_group": "layer_index=0"
                },
                "candidate_protocol": {
                    "path": candidate_path.name,
                    "sha256": candidate_sha256,
                        "declared_id": "faiss-candidate-test-v0.2",
                },
                    "retrieval_contract": {
                        "input": "resid_pre",
                        "input_snapshot": "detached_read_only",
                        "input_sha256_checked_before_and_after_each_rebuild": (
                            True
                        ),
                        "metric": "cosine",
                        "comparison_unit": [
                            "fixed_context_bank",
                            "fixed_context_id",
                            "fixed_observation_position",
                            "fixed_layer_index",
                        ],
                        "output": (
                            "canonical_unordered_global_row_pairs"
                        ),
                        "pair_order": "left_then_right_ascending",
                        "drift_available_to_backend": False,
                    "decoded_strings_available_to_backend": False,
                    "semantic_annotation_available_to_backend": False,
                    "sae_annotation_available_to_backend": False,
                        "projected_coordinates_available_to_backend": False,
                    },
                    "reference_backend": {
                        "backend_id": (
                            "spirallens.exact-blockwise-reference"
                        ),
                        "backend_version": "0.1",
                        "kind": "exact",
                        "deterministic": True,
                        "descriptor_sha256_bound_in_audit_identity": True,
                        "runtime_version_bound_in_descriptor": True,
                        "maximum_all_pair_rows": 10000,
                        "maximum_exact_comparisons": 50000000,
                        "inclusive_thresholds": True,
                    },
                    "subject_backend": {
                        "status": (
                            "implementation_selected_unpromoted"
                        ),
                        "backend_id": "spirallens.faiss-hnsw-range",
                    "backend_version": "0.1",
                    "distribution": "faiss-cpu",
                    "distribution_version": "1.14.3",
                        "kind_required_for_full_vocabulary": (
                            "approximate"
                        ),
                        "optional_dependency_only": True,
                        "candidate_persistence_without_audit_receipt": (
                            "forbidden"
                        ),
                        "config": faiss_config.to_dict(),
                        "required_provenance": [
                            "backend_id",
                            "backend_version",
                            "backend_config",
                            "runtime_versions",
                            "seed",
                            "thread_count",
                            "index_digest",
                        ],
                },
                "query_sampling": {
                    "method": "sha256_ranked_global_indices",
                    "seed": selection.seed,
                    "count": selection.count,
                    "global_row_key_sha256": (
                        row_identity_sha256
                    ),
                },
                "exact_rerank": {
                    "contract": (
                        "spirallens.candidate-exact-rerank.v0.1"
                        ),
                        "required_before_persist": True,
                        "source_values": (
                            "original_atlas_values_cast_to_float64"
                        ),
                        "backend_score_used_for_gate": False,
                    "false_persistable_candidates_allowed": 0,
                },
                "audit": {
                    "primary_metric": "candidate_boundary_recall",
                        "candidate_boundary_recall_min": (
                            audit_config.candidate_recall_min
                        ),
                        "query_local_recall_min": (
                            audit_config.query_local_recall_min
                        ),
                        "stratum_recall_min": (
                            audit_config.stratum_recall_min
                        ),
                        "repeats": audit_config.repeats,
                        "repeat_mode": "independent_cold_rebuild",
                        "minimum_reference_candidates": (
                            audit_config.minimum_reference_candidates
                        ),
                        "minimum_eligible_queries": (
                            audit_config.minimum_eligible_queries
                        ),
                        "minimum_eligible_query_fraction": (
                            audit_config.minimum_eligible_query_fraction
                        ),
                        "density_strata_count": (
                            audit_config.density_strata_count
                        ),
                        "minimum_eligible_queries_per_density_stratum": (
                            audit_config
                            .minimum_eligible_queries_per_density_stratum
                        ),
                        "boundary_shell_width": (
                            audit_config.boundary_shell_width
                        ),
                        "minimum_reference_candidates_per_stratum": (
                            audit_config
                            .minimum_reference_candidates_per_stratum
                        ),
                        "missing_pair_sample_limit": (
                            audit_config.missing_pair_sample_limit
                        ),
                        "zero_reference_candidates": "insufficient",
                        "top_k_recall_role": (
                            "not_applicable_range_search"
                        ),
                        "pooled_recall_can_override_failed_group": False,
                        "required_local_recall_contract": (
                            "spirallens.neighbor-local-recall.v0.1"
                        ),
                        "required_joint_strata": (
                            "density_rank_x_cosine_boundary"
                        ),
                        "issue_persistence_receipt_on_verified_pass": True,
                        "protocol_binding_required": True,
                        "source_identity_required": True,
                    },
                "claim_boundary": {
                    "semantics_free": True,
                    "candidate_is_not_verified_vortex": True,
                        "passing_audit_proves_retrieval_coverage_only": (
                            True
                        ),
                        "approximate_backend_currently_audited": False,
                    },
                    "promotion_readiness": {
                        "receipt_mechanism_implemented": True,
                        "full_index_subset_query_audit_implemented": True,
                        "frozen_recall_gate_methodology_available": True,
                        "query_local_worst_case_recall_gate_implemented": (
                            True
                        ),
                        "atlas_execution_bindings_frozen": True,
                        "tracked_protocol_can_issue_persistence_receipt": (
                            True
                        ),
                    },
                    "deviations": [],
                },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    protocol = NeighborAuditProtocolBinding(
        protocol_id="faiss-manifest-test-v0.1",
        status="frozen",
        source_sha256=hashlib.sha256(
            neighbor_path.read_bytes()
        ).hexdigest(),
        candidate_config_sha256=canonical_json_sha256(
            candidate_config.to_dict()
        ),
        audit_config_sha256=audit_config.sha256,
        query_selection=selection,
    )
    with pytest.raises(
        ValueError,
        match="require atlas checksum verification",
    ):
        _audit_neighbor_backend_from_manifest(
            manifest_path,
            layer_index=0,
            subject_backend_factory=lambda snapshot: FaissHNSWBackend(
                snapshot,
                row_identity_sha256=row_identity_sha256,
                comparison_group="layer_index=0",
                config=faiss_config,
            ),
            protocol_binding=protocol,
            candidate_config=candidate_config,
            audit_config=audit_config,
            execution_freeze=object(),
            verify_checksums=False,
        )
    monkeypatch.setattr(
        "spirallens.execution_freeze."
        "validated_execution_freeze_sha256",
        lambda capability: (
            "e" * 64
            if isinstance(capability, _TestExecutionFreeze)
            else pytest.fail("unexpected execution-freeze capability")
        ),
    )
    result = _audit_neighbor_backend_from_manifest(
        manifest_path,
        layer_index=0,
        subject_backend_factory=lambda snapshot: FaissHNSWBackend(
            snapshot,
            row_identity_sha256=row_identity_sha256,
            comparison_group="layer_index=0",
            config=faiss_config,
        ),
        protocol_binding=protocol,
        candidate_config=candidate_config,
        audit_config=audit_config,
        execution_freeze=_TestExecutionFreeze(),
    )
    audit_path = tmp_path / "faiss-audit.json"
    reservation = reserve_audit_output(audit_path)
    try:
        write_neighbor_audit(
            result,
            audit_path,
            _reservation=reservation,
        )
    finally:
        reservation.close()
    receipt = load_neighbor_audit_receipt(
        audit_path,
        protocol_path=neighbor_path,
        expected_audit_sha256=result.sha256,
        expected_protocol_sha256=hashlib.sha256(
            neighbor_path.read_bytes()
        ).hexdigest(),
    )
    ledger_path = tmp_path / "faiss-candidates.jsonl"

    summary = extract_candidates_from_manifest(
        manifest_path,
        ledger_path,
        config=candidate_config,
        protocol_id="faiss-candidate-test-v0.2",
        protocol_claim_ceiling=1,
        protocol_binding={
            "declared_id": "faiss-candidate-test-v0.2",
            "claim_ceiling": 1,
            "sha256": candidate_sha256,
        },
        neighbor_backend_factory=(
            lambda snapshot, row_sha, group: FaissHNSWBackend(
                snapshot,
                row_identity_sha256=row_sha,
                comparison_group=group,
                config=faiss_config,
            )
        ),
        neighbor_audit_receipts={"layer_index=0": receipt},
    )
    rows = [
        json.loads(line)
        for line in ledger_path.read_text(encoding="utf-8").splitlines()
    ]
    candidate = list(read_candidate_records(ledger_path))[0]
    binding = rows[0]["source"]["neighbor_retrieval"]["groups"][
        "layer_index=0"
    ]

    assert summary.candidate_count == 2
    assert binding["backend"]["kind"] == "approximate"
    assert binding["audit_receipt_sha256"] == receipt.sha256
    assert candidate["retrieval"]["audit_receipt_sha256"] == receipt.sha256
    assert rows[-1]["candidate_count_by_group"] == {"layer_index=0": 2}

    direct_path = tmp_path / "direct-approximate.jsonl"
    with pytest.raises(
        ValueError,
        match="only through extract_candidates_from_manifest",
    ):
        write_candidate_ledger(
            (candidate,),
            direct_path,
            source=rows[0]["source"],
            config=candidate_config,
            protocol_id="faiss-candidate-test-v0.2",
            protocol_claim_ceiling=1,
            protocol_binding=rows[0]["protocol"],
            neighbor_audit_receipts={"layer_index=0": receipt},
        )
    assert not direct_path.exists()

    for suffix, mutate in (
        (
            "config",
            lambda forged: forged[0]["candidate_search"].__setitem__(
                "cosine_min",
                0.998,
            ),
        ),
        (
            "protocol-sha",
            lambda forged: forged[0]["protocol"].__setitem__(
                "sha256",
                "f" * 64,
            ),
        ),
        (
            "protocol-id",
            lambda forged: (
                forged[0].__setitem__("protocol_id", "other-protocol"),
                forged[0]["protocol"].__setitem__(
                    "declared_id",
                    "other-protocol",
                ),
                forged[-1].__setitem__(
                    "protocol_id",
                    "other-protocol",
                ),
            ),
        ),
        (
            "atlas-manifest",
            lambda forged: forged[0]["source"].__setitem__(
                "atlas_manifest_sha256",
                "e" * 64,
            ),
        ),
        (
            "row-identity",
            lambda forged: forged[0]["source"].__setitem__(
                "global_row_key_sha256",
                "e" * 64,
            ),
        ),
        (
            "atlas-run",
            lambda forged: forged[0]["source"].__setitem__(
                "atlas_run_id",
                "other-atlas-run",
            ),
        ),
    ):
        forged = json.loads(json.dumps(rows))
        mutate(forged)
        forged_path = tmp_path / f"forged-{suffix}.jsonl"
        _write_rehashed_ledger(forged_path, forged)
        with pytest.raises(
            ValueError,
            match="neighbor (audit )?receipt",
        ):
            list(read_candidate_records(forged_path))

    malformed_candidate = json.loads(json.dumps(rows))
    malformed_candidate[1]["claim_level"] = 999
    malformed_path = tmp_path / "forged-candidate-shape.jsonl"
    _write_rehashed_ledger(malformed_path, malformed_candidate)
    with pytest.raises(ValueError, match="candidate record shape"):
        list(read_candidate_records(malformed_path))


def test_manifest_extraction_rejects_incomplete_atlas(tmp_path: Path) -> None:
    manifest_path = _write_atlas(tmp_path, status="in_progress")
    with pytest.raises(ValueError, match="status='complete'"):
        extract_candidates_from_manifest(
            manifest_path,
            tmp_path / "must-not-exist.jsonl",
            config=CandidateSearchConfig(block_size=1),
        )
    assert not (tmp_path / "must-not-exist.jsonl").exists()


def test_zero_candidate_ledger_is_still_complete(tmp_path: Path) -> None:
    output = tmp_path / "zero.jsonl"
    summary = write_candidate_ledger(
        (),
        output,
        source={"kind": "unit-test"},
        config=CandidateSearchConfig(),
        protocol_id="unit-test",
    )
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert summary.candidate_count == 0
    assert [row["record_type"] for row in rows] == ["ledger_header", "ledger_footer"]
    assert rows[-1]["candidate_count"] == 0


def test_candidate_ledger_refuses_existing_destination_by_default(
    tmp_path: Path,
) -> None:
    output = tmp_path / "owned.jsonl"
    output.write_text('{"owned_by":"user"}\n', encoding="utf-8")

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        write_candidate_ledger(
            (),
            output,
            source={"kind": "unit-test"},
            config=CandidateSearchConfig(),
            protocol_id="unit-test",
        )
    assert output.read_text(encoding="utf-8") == '{"owned_by":"user"}\n'

    summary = write_candidate_ledger(
        (),
        output,
        source={"kind": "unit-test"},
        config=CandidateSearchConfig(),
        protocol_id="unit-test",
        overwrite=True,
    )
    assert summary.candidate_count == 0
    assert json.loads(output.read_text().splitlines()[-1])["status"] == "complete"


def test_candidate_ledger_binds_protocol_provenance_and_rejects_id_mismatch(
    tmp_path: Path,
) -> None:
    output = tmp_path / "bound.jsonl"
    binding = {
        "protocol_path": "/protocols/pythia_v0_1.yaml",
        "sha256": "a" * 64,
        "status": "preregistered-draft",
        "declared_id": "pythia-v0.1",
        "claim_ceiling": 2,
        "exploratory_overrides": {"block_size": 4},
        "deviations": ["block_size"],
    }
    write_candidate_ledger(
        (),
        output,
        source={"kind": "unit-test"},
        config=CandidateSearchConfig(),
        protocol_id="pythia-v0.1",
        protocol_claim_ceiling=2,
        protocol_binding=binding,
    )
    header = json.loads(output.read_text().splitlines()[0])
    assert header["protocol"] == binding

    mismatch = tmp_path / "mismatch.jsonl"
    with pytest.raises(ValueError, match="declared_id must match"):
        write_candidate_ledger(
            (),
            mismatch,
            source={"kind": "unit-test"},
            config=CandidateSearchConfig(),
            protocol_id="pythia-v0.1",
            protocol_claim_ceiling=2,
            protocol_binding={**binding, "declared_id": "different-protocol"},
        )
    assert not mismatch.exists()


def test_protocol_loads_preregistered_candidate_gates() -> None:
    root = Path(__file__).resolve().parents[1]
    config = load_candidate_config_from_protocol(root / "protocols" / "pythia_v0_1.yaml")
    assert config.cosine_min == 0.995
    assert config.relative_norm_gap_max == 0.05
    assert config.block_size == 1024
    assert config.max_pairwise_rows == 10_000
    assert config.layer_indices is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"cosine_min": np.nan},
        {"drift_relative_divergence_min": np.inf},
        {"layer_indices": (True,)},
        {"layer_indices": (1.5,)},
        {"block_size": True},
    ],
)
def test_candidate_config_rejects_non_finite_or_ambiguous_types(
    kwargs: dict[str, object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        CandidateSearchConfig(**kwargs)


def test_exact_pairwise_search_fails_loudly_above_guard() -> None:
    states = np.ones((4, 2))
    with pytest.raises(ValueError, match="audited ANN"):
        list(
            iter_candidate_pairs(
                states,
                states,
                config=CandidateSearchConfig(max_pairwise_rows=3),
            )
        )


def test_all_zero_drift_gates_are_rejected_before_cosine_is_computed() -> None:
    with pytest.raises(ValueError, match="min_drift_norm must be positive"):
        CandidateSearchConfig(
            cosine_min=0.0,
            relative_norm_gap_max=0.0,
            drift_relative_divergence_min=0.0,
            drift_absolute_divergence_min=0.0,
            min_state_norm=0.0,
            min_drift_norm=0.0,
        )
