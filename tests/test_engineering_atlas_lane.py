from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import torch

from spirallens.adapters import BatchObservation
from spirallens.atlas import (
    ContextBankBinding,
    SweepConfig,
    load_manifest,
    run_id_sweep,
)
from spirallens.atlas.engineering_protocol import (
    LoadedPublicExamplePlumbingProtocol,
    _build_public_example_plumbing_protocol_binding,
    public_example_plumbing_protocol_from_dict,
)
from spirallens.atlas.engineering_receipt import (
    PublicExamplePlumbingReceiptError,
    _build_public_example_plumbing_receipt,
)
from spirallens.contexts import ContextRole, load_context_bank

from engineering_fixtures import (
    passing_execution_preflight,
    public_example_protocol_payload,
)


class _Pythia70ShapeAdapter:
    model_id = "EleutherAI/pythia-70m"
    revision = "a39f36b100fe8a5377810d56c3f4789b9c53ac42"
    vocab_size = 50304

    def config_metadata(self) -> dict[str, object]:
        return {
            "model_id": self.model_id,
            "requested_revision": self.revision,
            "resolved_revision": self.revision,
            "architecture": "GPTNeoXForCausalLM",
            "model_type": "gpt_neox",
            "num_layers": 6,
            "hidden_size": 512,
            "vocab_size": self.vocab_size,
            "parameter_count": 70_426_624,
            "parameter_dtypes": ["float32"],
            "parameter_devices": ["cpu"],
            "config": {
                "num_attention_heads": 8,
                "intermediate_size": 2048,
                "max_position_embeddings": 2048,
            },
            "rope": {"kind": "partial_rope"},
        }

    def capture_metadata(self) -> dict[str, object]:
        return {
            "capture_implementation": {
                "name": "test.public-example-shape-adapter",
                "version": "v1",
                "accelerator_to_cpu_copy": "synchronous",
                "activation_dtype": "float32",
            },
            "spirallens_version": "0.1.0",
            "torch_version": str(torch.__version__),
            "transformers_version": "test",
            "effective_parameter_layout": [
                {
                    "device": "cpu",
                    "dtype": "float32",
                    "parameter_tensors": 1,
                    "parameter_values": 70_426_624,
                }
            ],
        }

    def observe_batch(
        self,
        input_ids: torch.Tensor,
        *,
        position: int,
        attention_mask: torch.Tensor | None = None,
    ) -> BatchObservation:
        del position, attention_mask
        batch = input_ids.shape[0]
        resid_pre = torch.zeros((batch, 6, 512), dtype=torch.float32)
        resid_post = torch.ones((batch, 6, 512), dtype=torch.float32)
        return BatchObservation(
            resid_pre=resid_pre,
            resid_post=resid_post,
            norm_summary=torch.zeros((batch, 6, 2), dtype=torch.float32),
            logit_summary=torch.zeros((batch, 6), dtype=torch.float32),
            prediction_ids=torch.zeros(batch, dtype=torch.int64),
        )


def _loaded_protocol(
    *,
    bank_path: Path,
    source_sha256: str,
    canonical_sha256: str,
    output_id: str,
) -> LoadedPublicExamplePlumbingProtocol:
    payload = public_example_protocol_payload(
        token_ids=(0, 1),
        output_id=output_id,
    )
    payload["model"]["revision"] = _Pythia70ShapeAdapter.revision
    payload["context_bank"].update(
        {
            "path": "protocols/context_bank_example_v0_1.yaml",
            "source_sha256": source_sha256,
            "canonical_sha256": canonical_sha256,
            "context_id": "synthetic-slot-only-001",
        }
    )
    protocol = public_example_plumbing_protocol_from_dict(payload)
    source_bytes = b"frozen engineering protocol fixture"
    return LoadedPublicExamplePlumbingProtocol(
        protocol=protocol,
        source_bytes=source_bytes,
        source_path=bank_path.parent / "engineering-protocol.yaml",
        source_sha256=hashlib.sha256(source_bytes).hexdigest(),
        canonical_sha256=protocol.canonical_sha256,
    )


def test_engineering_binding_survives_atlas_and_receipt_roundtrip(
    tmp_path: Path,
) -> None:
    repository_root = Path(__file__).resolve().parents[1]
    bank_path = repository_root / "protocols/context_bank_example_v0_1.yaml"
    bank = load_context_bank(
        bank_path,
        allowed_roles={ContextRole.EXAMPLE},
    )
    output = tmp_path / "engineering-atlas"
    loaded = _loaded_protocol(
        bank_path=bank_path,
        source_sha256=bank.source_sha256,
        canonical_sha256=bank.canonical_sha256,
        output_id=output.name,
    )
    protocol = loaded.protocol
    context = ContextBankBinding(
        loaded=bank,
        context_id=protocol.context_bank.context_id,
        role=ContextRole.EXAMPLE,
    )
    binding = _build_public_example_plumbing_protocol_binding(
        loaded,
        verified_model_files=dict(protocol.model.files),
        execution_preflight=passing_execution_preflight(),
    )

    manifest = run_id_sweep(
        _Pythia70ShapeAdapter(),
        SweepConfig(
            output_dir=output,
            context_ids=context.materialized_context_ids,
            position=context.context.observation_position,
            batch_size=protocol.capture.batch_size,
            subset=protocol.token_selection.token_ids,
            context_bank_binding=context,
            public_example_plumbing_protocol_binding=binding,
        ),
    )

    assert manifest["status"] == "complete"
    assert manifest["request"]["output_id"] == output.name
    assert (
        manifest["request"]["model_blob_sha256"]
        == dict(protocol.model.files)["model.safetensors"]
    )
    assert load_manifest(output) == manifest

    with pytest.raises(
        PublicExamplePlumbingReceiptError,
        match="exact Pythia-70M",
    ):
        _build_public_example_plumbing_receipt(
            output,
            loaded_protocol=loaded,
        )
