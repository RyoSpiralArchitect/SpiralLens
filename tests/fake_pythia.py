"""Small deterministic GPT-NeoX-shaped model for offline tests."""

from __future__ import annotations

from types import SimpleNamespace

import torch
from torch import Tensor, nn


class FakeConfig:
    model_type = "gpt_neox"
    architectures = ["FakePythiaForCausalLM"]
    vocab_size = 11
    hidden_size = 6
    num_hidden_layers = 2
    num_attention_heads = 2
    partial_rotary_factor = 1 / 3
    rotary_pct = 1 / 3
    rope_theta = 10_000.0
    rope_scaling = None
    max_position_embeddings = 32
    use_parallel_residual = True

    def to_dict(self) -> dict[str, object]:
        return {
            "model_type": self.model_type,
            "architectures": self.architectures,
            "vocab_size": self.vocab_size,
            "hidden_size": self.hidden_size,
            "num_hidden_layers": self.num_hidden_layers,
            "num_attention_heads": self.num_attention_heads,
            "partial_rotary_factor": self.partial_rotary_factor,
            "rope_theta": self.rope_theta,
            "rope_scaling": self.rope_scaling,
            "max_position_embeddings": self.max_position_embeddings,
            "use_parallel_residual": self.use_parallel_residual,
        }


class FakeBlock(nn.Module):
    def __init__(self, offset: float) -> None:
        super().__init__()
        self.offset = offset

    def forward(self, hidden: Tensor) -> Tensor:
        return hidden + self.offset


class FakeNeoX(nn.Module):
    def __init__(self, config: FakeConfig) -> None:
        super().__init__()
        self.embed_in = nn.Embedding(config.vocab_size, config.hidden_size)
        self.layers = nn.ModuleList((FakeBlock(1.0), FakeBlock(2.0)))


class FakePythiaForCausalLM(nn.Module):
    """A deterministic model with the attributes used by ``PythiaAdapter``."""

    def __init__(self) -> None:
        super().__init__()
        self.config = FakeConfig()
        self.gpt_neox = FakeNeoX(self.config)
        self.embed_out = nn.Linear(
            self.config.hidden_size, self.config.vocab_size, bias=False
        )
        self.fail_on_token: int | None = None
        with torch.no_grad():
            values = torch.arange(
                self.config.vocab_size * self.config.hidden_size,
                dtype=torch.float32,
            ).reshape(self.config.vocab_size, self.config.hidden_size)
            self.gpt_neox.embed_in.weight.copy_(values / 10.0)
            output_values = torch.arange(
                self.config.vocab_size * self.config.hidden_size,
                dtype=torch.float32,
            ).reshape(self.config.vocab_size, self.config.hidden_size)
            self.embed_out.weight.copy_((output_values + 1.0) / 100.0)

    def get_input_embeddings(self) -> nn.Embedding:
        return self.gpt_neox.embed_in

    def forward(
        self,
        *,
        input_ids: Tensor,
        attention_mask: Tensor | None = None,
        use_cache: bool = False,
    ) -> SimpleNamespace:
        del attention_mask, use_cache
        if self.fail_on_token is not None and torch.any(
            input_ids == self.fail_on_token
        ):
            raise RuntimeError(f"intentional failure for token {self.fail_on_token}")
        hidden = self.gpt_neox.embed_in(input_ids)
        for layer in self.gpt_neox.layers:
            hidden = layer(hidden)
        return SimpleNamespace(logits=self.embed_out(hidden))
