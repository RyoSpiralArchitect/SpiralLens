from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from spirallens.atlas import ContextBankBinding
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
    decompose_difference,
    extract_candidates_from_manifest,
    iter_candidate_pairs,
    load_candidate_config_from_protocol,
    write_candidate_ledger,
)
from spirallens.metrics.candidate_pairs import read_candidate_records


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


def _write_atlas(tmp_path: Path, *, status: str = "complete") -> Path:
    token_ids = np.array([11, 12, 13], dtype=np.int64)
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
        "logit_summary": np.zeros((3, 6), dtype=np.float32),
        "prediction_ids": np.zeros(3, dtype=np.int64),
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
    completed_rows = 3 if status == "complete" else 2
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
            "selection": {"kind": "subset", "subset_size_before_limit": 3},
            "num_tokens": 3,
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
            "total_rows": 3,
            "committed_batches": 1,
        },
        "attempts": [
            {
                "started_at": "2026-01-01T00:00:00+00:00",
                "resume_from_row": 0,
                "batch_size": 3,
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


def _write_bound_atlas(tmp_path: Path) -> Path:
    manifest_path = _write_atlas(tmp_path)
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
            vocab_size=100,
        ),
        tokenizer=TokenizerBinding(
            tokenizer_id="test/tokenizer",
            requested_revision="test",
            resolved_revision="b" * 40,
            addressable_size=12,
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
                "size": 100,
                "model_vocab_size": 100,
                "tokenizer_addressable_size": 12,
            },
            "language_space_atlas": False,
            "semantic_unit": False,
        }
    )
    request_identity = dict(request)
    request_identity.pop("batch_size_initial", None)
    request_identity.pop("batch_size_latest", None)
    request["request_identity_sha256"] = _json_sha256(request_identity)
    manifest["model"].update(
        {
            "model_id": "test/pythia",
            "resolved_revision": "a" * 40,
        }
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


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
        "spirallens.candidate-ledger.v0.2"
    )
    assert rows[0]["source"]["atlas_run_id"] == "atlas-test-run"
    assert rows[0]["source"]["neighbor_retrieval"][
        "exact_rerank_required"
    ] is True
    assert rows[0]["source"]["neighbor_retrieval"][
        "backend_score_used_for_gates"
    ] is False
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
    assert candidates[0]["left"]["layer_index"] == 0
    assert candidates[0]["left"]["token_id"] == 11
    assert candidates[0]["right"]["token_id"] == 12
    assert candidates[0]["schema_version"] == "spirallens.candidate.v0.2"
    assert candidates[0]["retrieval"]["exact_reranked"] is True
    assert candidates[0]["retrieval"][
        "backend_score_used_for_gates"
    ] is False


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
