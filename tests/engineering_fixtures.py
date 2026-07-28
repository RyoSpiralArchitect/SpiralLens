from __future__ import annotations

from spirallens.atlas.engineering_protocol import (
    token_ids_little_endian_i8_sha256,
)


def public_example_protocol_payload(
    *,
    token_ids: tuple[int, ...] = (0, 7, 42),
    output_id: str = "pythia70-public-example-smoke-v0.1",
) -> dict[str, object]:
    return {
        "schema_version": "spirallens.public-example-plumbing-protocol.v0.1",
        "protocol_id": "pythia70-public-example-smoke-v0.1",
        "status": "frozen_engineering",
        "purpose": "public_example_capture_plumbing",
        "claim_ceiling": "level_0",
        "execution_class": "public_example_engineering",
        "scientific_claim_eligible": False,
        "p1_instrument_consumed": False,
        "tokenizer_runtime_verified": False,
        "source": {
            "repository": "RyoSpiralArchitect/SpiralLens",
            "implementation_commit": "a" * 40,
            "implementation_repository_path": (
                "src/spirallens/adapters/pythia.py"
            ),
            "implementation_module_sha256": "b" * 64,
        },
        "model": {
            "id": "EleutherAI/pythia-70m",
            "revision": "c" * 40,
            "architecture": "GPTNeoXForCausalLM",
            "num_layers": 6,
            "hidden_size": 512,
            "vocab_size": 50304,
            "num_attention_heads": 8,
            "intermediate_size": 2048,
            "max_position_embeddings": 2048,
            "files": {
                "config.json": "d" * 64,
                "model.safetensors": "e" * 64,
            },
        },
        "context_bank": {
            "path": "protocols/context_bank_example_v0_1.yaml",
            "source_sha256": "f" * 64,
            "canonical_sha256": "1" * 64,
            "context_id": "synthetic-slot-only-001",
            "role": "example",
            "claim_eligible": False,
        },
        "token_selection": {
            "kind": "explicit_sorted_ids",
            "token_ids": list(token_ids),
            "token_ids_sha256": (
                token_ids_little_endian_i8_sha256(token_ids)
            ),
        },
        "capture": {
            "device": "cpu",
            "dtype": "float32",
            "batch_size": 2,
            "output_id": output_id,
            "observation_contract": "all_residual_pre_post_layers",
        },
        "resource_budget": {
            "estimator_id": (
                "pythia-atlas-conservative-static-estimate-v0.1"
            ),
            "safety_factor": 4,
            "estimated_output_bytes": 300_000,
            "max_estimated_output_bytes": 1_000_000,
            "estimated_peak_bytes": 600_000,
            "max_estimated_peak_bytes": 2_000_000,
            "claim_boundary": (
                "static-array-and-working-set-estimate-not-os-oom-guarantee"
            ),
        },
        "authorizations": {
            "example_model_access": True,
            "activation_atlas_capture": True,
            "network_access": False,
            "subject_protocol_preparation": False,
            "subject_execution": False,
            "instrument_bundle_conversion": False,
            "candidate_search": False,
            "neighbor_audit": False,
            "graph_construction": False,
            "field_estimation": False,
            "core_detection": False,
            "loop_construction": False,
            "holonomy_analysis": False,
            "winding_analysis": False,
            "semantic_analysis": False,
            "sae_analysis": False,
            "causal_analysis": False,
            "integer_output": False,
        },
        "stage_status": {
            **{f"D{index}": "not_run" for index in range(9)},
            "subject_protocol_preparation": "not_run",
            "subject_execution": "not_run",
            "instrument_bundle_conversion": "not_run",
            "candidate_search": "not_run",
            "neighbor_audit": "not_run",
            "graph_construction": "not_run",
            "field_estimation": "not_run",
            "core_detection": "not_run",
            "loop_construction": "not_run",
            "holonomy_analysis": "not_run",
            "winding_analysis": "not_run",
            "semantic_analysis": "not_run",
            "sae_analysis": "not_run",
            "causal_analysis": "not_run",
            "integer_output": "not_run",
        },
        "allowed_consumers": ["atlas_integrity_validation"],
    }


def passing_execution_preflight() -> dict[str, object]:
    return {
        "status": "pass",
        "estimator_id": (
            "pythia-atlas-conservative-static-estimate-v0.1"
        ),
        "model_file_bytes": 400_000,
        "minimum_peak_bytes": 500_000,
        "free_disk_bytes": 2_000_000,
        "physical_memory_bytes": 3_000_000,
        "disk_reserve_bytes": 1,
    }
