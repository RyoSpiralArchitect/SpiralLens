from __future__ import annotations

import pytest
import torch
from torch import nn

from spirallens.adapters import (
    CAPTURE_IMPLEMENTATION_VERSION,
    LOGIT_SUMMARY_COLUMNS,
    PythiaAdapter,
    PythiaAdapterError,
)

from fake_pythia import FakePythiaForCausalLM


def test_logit_summary_column_names_include_units_and_quantity() -> None:
    assert LOGIT_SUMMARY_COLUMNS == (
        "max_logit",
        "mean_logit",
        "std_logit",
        "logsumexp_logit",
        "entropy_nats",
        "input_token_logit",
    )


def test_fake_pythia_captures_every_layer_and_restores_hooks() -> None:
    model = FakePythiaForCausalLM()
    model.train()
    adapter = PythiaAdapter(model, model_id="offline/fake-pythia", revision="test")
    input_ids = torch.tensor([[0, 2, 4], [1, 3, 5]], dtype=torch.long)

    observation = adapter.observe_batch(input_ids, position=1)

    assert observation.resid_pre.shape == (2, 2, 6)
    assert observation.resid_post.shape == (2, 2, 6)
    assert observation.norm_summary.shape == (2, 2, 2)
    assert observation.logit_summary.shape == (2, len(LOGIT_SUMMARY_COLUMNS))
    assert observation.prediction_ids.shape == (2,)
    expected_embedding = model.gpt_neox.embed_in(input_ids)[:, 1, :].detach()
    torch.testing.assert_close(observation.resid_pre[:, 0, :], expected_embedding)
    torch.testing.assert_close(
        observation.resid_post[:, 0, :], expected_embedding + 1.0
    )
    torch.testing.assert_close(
        observation.resid_pre[:, 1, :], expected_embedding + 1.0
    )
    torch.testing.assert_close(
        observation.resid_post[:, 1, :], expected_embedding + 3.0
    )
    assert model.training is True
    for layer in model.gpt_neox.layers:
        assert not layer._forward_pre_hooks
        assert not layer._forward_hooks


def test_rope_and_config_metadata_are_explicit() -> None:
    adapter = PythiaAdapter(
        FakePythiaForCausalLM(), model_id="offline/fake-pythia"
    )

    rope = adapter.rope_metadata()
    metadata = adapter.config_metadata()

    assert rope == {
        "kind": "partial_rope",
        "source": "model.config",
        "num_attention_heads": 2,
        "head_dim": 3,
        "rotary_fraction": pytest.approx(1 / 3),
        "rotary_ndims": 1,
        "base": 10_000.0,
        "scaling": None,
        "max_position_embeddings": 32,
    }
    assert metadata["num_layers"] == 2
    assert metadata["hidden_size"] == 6
    assert metadata["vocab_size"] == 11
    assert metadata["parameter_count"] > 0
    assert metadata["parameter_dtypes"] == ["float32"]
    assert metadata["parameter_devices"] == ["cpu"]
    assert metadata["rope"] == rope


def test_capture_metadata_binds_versions_and_effective_parameter_layout() -> None:
    adapter = PythiaAdapter(
        FakePythiaForCausalLM(),
        model_id="offline/fake-pythia",
        revision="test",
    )

    capture = adapter.capture_metadata()

    assert capture["capture_implementation"] == {
        "name": "PythiaAdapter.observe_batch.residual_hooks",
        "version": CAPTURE_IMPLEMENTATION_VERSION,
        "accelerator_to_cpu_copy": "synchronous",
        "activation_dtype": "float32",
    }
    assert capture["spirallens_version"]
    assert capture["torch_version"] == str(torch.__version__)
    assert capture["transformers_version"]
    assert capture["effective_parameter_layout"] == [
        {
            "device": "cpu",
            "dtype": "float32",
            "parameter_tensors": 2,
            "parameter_values": 132,
        }
    ]


def test_hook_device_to_cpu_copy_is_explicitly_synchronous(monkeypatch) -> None:
    original_to = torch.Tensor.to
    non_blocking_values: list[object] = []

    def observed_to(self, *args, **kwargs):
        if kwargs.get("device") == "cpu" and kwargs.get("dtype") == torch.float32:
            non_blocking_values.append(kwargs.get("non_blocking"))
        return original_to(self, *args, **kwargs)

    monkeypatch.setattr(torch.Tensor, "to", observed_to)
    adapter = PythiaAdapter(
        FakePythiaForCausalLM(),
        model_id="offline/fake-pythia",
        revision="test",
    )

    adapter.observe_batch(torch.tensor([[0, 1]], dtype=torch.long), position=1)

    assert non_blocking_values
    assert set(non_blocking_values) == {False}


def test_hooks_are_removed_when_model_forward_fails() -> None:
    model = FakePythiaForCausalLM()
    model.fail_on_token = 3
    adapter = PythiaAdapter(model, model_id="offline/fake-pythia")

    with pytest.raises(RuntimeError, match="intentional failure"):
        adapter.observe_batch(torch.tensor([[3]], dtype=torch.long), position=0)

    for layer in model.gpt_neox.layers:
        assert not layer._forward_pre_hooks
        assert not layer._forward_hooks


def test_adapter_rejects_non_neox_model() -> None:
    class WrongConfig:
        model_type = "gpt2"
        hidden_size = 4
        vocab_size = 8

    class WrongModel(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.config = WrongConfig()

    with pytest.raises(PythiaAdapterError, match="model_type"):
        PythiaAdapter(WrongModel(), model_id="wrong")


def test_tiny_transformers_gpt_neox_contract_without_network() -> None:
    transformers = pytest.importorskip("transformers")
    config = transformers.GPTNeoXConfig(
        vocab_size=13,
        hidden_size=8,
        num_hidden_layers=2,
        num_attention_heads=2,
        intermediate_size=16,
        max_position_embeddings=8,
        partial_rotary_factor=0.5,
    )
    model = transformers.GPTNeoXForCausalLM(config)
    adapter = PythiaAdapter(model, model_id="offline/random-gpt-neox")

    observation = adapter.observe_batch(
        torch.tensor([[0, 1, 2], [3, 4, 5]], dtype=torch.long),
        position=2,
        attention_mask=torch.ones((2, 3), dtype=torch.long),
    )

    assert observation.resid_pre.shape == (2, 2, 8)
    assert observation.resid_post.shape == (2, 2, 8)
    assert torch.isfinite(observation.logit_summary).all()
