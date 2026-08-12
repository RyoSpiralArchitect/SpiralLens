"""Mechanism-only tests for the offline Pythia residual-hook adapter.

These tests use a tiny deterministic GPT-NeoX-shaped fake.  They qualify only
the adapter mechanics exercised here; they do not exercise Hugging Face model
loading, cached weights, or any real Pythia model (including Pythia-160M).
"""

from __future__ import annotations

from collections.abc import Callable
import hashlib
import json
from types import SimpleNamespace

import pytest
import torch
from torch import Tensor, nn

from spirallens.adapters import PythiaAdapter, PythiaAdapterError
from spirallens.atlas import AtlasStateError, SweepConfig, run_id_sweep


class _TinyConfig:
    model_type = "gpt_neox"
    architectures = ["_TraceableFakeNeoXForCausalLM"]
    vocab_size = 13
    hidden_size = 4
    num_hidden_layers = 3
    num_attention_heads = 2
    partial_rotary_factor = 0.5
    rope_theta = 10_000.0
    rope_scaling = None
    max_position_embeddings = 16


class _TraceBlock(nn.Module):
    def __init__(self, layer_index: int, *, dtype: torch.dtype) -> None:
        super().__init__()
        self.layer_index = layer_index
        self.mutate_input_after_output = False
        self.truncate_output = False
        self.register_buffer(
            "offset",
            torch.tensor(
                [
                    layer_index + 0.125,
                    layer_index + 0.25,
                    layer_index + 0.5,
                    layer_index + 0.75,
                ],
                dtype=dtype,
            ),
        )
        self.last_input: Tensor | None = None
        self.last_output: Tensor | None = None

    def forward(self, hidden: Tensor) -> Tensor:
        self.last_input = hidden.detach().clone()
        output = hidden + self.offset
        if self.truncate_output:
            output = output[..., :-1]
        self.last_output = output.detach().clone()
        if self.mutate_input_after_output:
            # Simulate an accelerator buffer being reused after the pre-hook.
            # The block output was already materialized, so only a capture that
            # aliases its source can be changed by this adversarial mutation.
            hidden.add_(4096.0)
        return output


class _TraceableFakeNeoX(nn.Module):
    def __init__(self, config: _TinyConfig, *, dtype: torch.dtype) -> None:
        super().__init__()
        self.embed_in = nn.Embedding(
            config.vocab_size,
            config.hidden_size,
            dtype=dtype,
        )
        self.layers = nn.ModuleList(
            _TraceBlock(layer_index, dtype=dtype)
            for layer_index in range(config.num_hidden_layers)
        )


class _TraceableFakeNeoXForCausalLM(nn.Module):
    """A deterministic fake exposing only the adapter's structural surface."""

    def __init__(self, *, dtype: torch.dtype = torch.float64) -> None:
        super().__init__()
        self.config = _TinyConfig()
        self.gpt_neox = _TraceableFakeNeoX(self.config, dtype=dtype)
        self.embed_out = nn.Linear(
            self.config.hidden_size,
            self.config.vocab_size,
            bias=False,
            dtype=dtype,
        )
        self.register_buffer(
            "nonpersistent_probe",
            torch.tensor([17.0, 19.0], dtype=dtype),
            persistent=False,
        )
        self.fail_after_layer: int | None = None
        self.omit_layer: int | None = None
        self.repeat_layer: int | None = None
        self.mutate_output_after_layer: int | None = None
        self.truncate_logits = False
        self.last_forward_contract: dict[str, object] | None = None
        self.last_logits: Tensor | None = None
        self.execution_order: list[int] = []
        with torch.no_grad():
            embedding_values = torch.arange(
                self.config.vocab_size * self.config.hidden_size,
                dtype=dtype,
            ).reshape(self.config.vocab_size, self.config.hidden_size)
            self.gpt_neox.embed_in.weight.copy_(embedding_values / 8.0)
            output_values = torch.arange(
                self.config.vocab_size * self.config.hidden_size,
                dtype=dtype,
            ).reshape(self.config.vocab_size, self.config.hidden_size)
            self.embed_out.weight.copy_((output_values + 1.0) / 64.0)

    def get_input_embeddings(self) -> nn.Embedding:
        return self.gpt_neox.embed_in

    def forward(
        self,
        *,
        input_ids: Tensor,
        attention_mask: Tensor | None = None,
        use_cache: bool | None = None,
    ) -> SimpleNamespace:
        self.last_forward_contract = {
            "attention_mask": (
                None if attention_mask is None else attention_mask.detach().clone()
            ),
            "grad_enabled": torch.is_grad_enabled(),
            "inference_mode": torch.is_inference_mode_enabled(),
            "model_training": self.training,
            "module_training": {
                name: module.training for name, module in self.named_modules()
            },
            "use_cache": use_cache,
        }
        self.execution_order = []
        hidden = self.gpt_neox.embed_in(input_ids)
        for layer_index, layer in enumerate(self.gpt_neox.layers):
            if layer_index == self.omit_layer:
                continue
            hidden = layer(hidden)
            self.execution_order.append(layer_index)
            if layer_index == self.mutate_output_after_layer:
                # This runs after the layer's forward hook has returned and
                # emulates immediate reuse of the output activation buffer.
                hidden.add_(8192.0)
            if layer_index == self.repeat_layer:
                hidden = layer(hidden)
                self.execution_order.append(layer_index)
            if layer_index == self.fail_after_layer:
                raise RuntimeError(f"fake failure after layer {layer_index}")
        logits = self.embed_out(hidden)
        if self.truncate_logits:
            logits = logits[..., :-1]
        self.last_logits = logits.detach().clone()
        return SimpleNamespace(logits=logits)


def _adapter(model: _TraceableFakeNeoXForCausalLM) -> PythiaAdapter:
    return PythiaAdapter(
        model,
        model_id="offline/mechanism-only-fake-neox",
        revision="test-fixture-no-model-artifact",
    )


def _input_ids() -> Tensor:
    return torch.tensor(
        [[0, 1, 2, 3], [8, 7, 6, 5]],
        dtype=torch.long,
    )


def _module_modes(model: nn.Module) -> dict[str, bool]:
    return {name: module.training for name, module in model.named_modules()}


def _state_and_buffer_digest(model: nn.Module) -> str:
    """Digest exact tensor metadata/bytes, including nonpersistent buffers."""

    digest = hashlib.sha256()
    sections = (
        ("state_dict", dict(model.state_dict())),
        ("all_buffers", dict(model.named_buffers())),
    )
    for section, tensors in sections:
        for name in sorted(tensors):
            tensor = tensors[name].detach().cpu().contiguous()
            header = (
                f"{section}\0{name}\0{tensor.dtype}\0{tuple(tensor.shape)!r}\0"
            ).encode()
            payload = tensor.view(torch.uint8).numpy().tobytes()
            digest.update(len(header).to_bytes(8, "big"))
            digest.update(header)
            digest.update(len(payload).to_bytes(8, "big"))
            digest.update(payload)
    return digest.hexdigest()


def _tensor_versions(model: nn.Module) -> dict[str, int]:
    tensors = {
        **dict(model.named_parameters()),
        **dict(model.named_buffers()),
    }
    return {name: tensor._version for name, tensor in tensors.items()}


def _hook_state(
    model: _TraceableFakeNeoXForCausalLM,
) -> tuple[
    tuple[dict[int, Callable[..., object]], dict[int, Callable[..., object]]], ...
]:
    return tuple(
        (dict(layer._forward_pre_hooks), dict(layer._forward_hooks))
        for layer in model.gpt_neox.layers
    )


def test_zero_intervention_preserves_baseline_output_and_model_state() -> None:
    model = _TraceableFakeNeoXForCausalLM()
    input_ids = _input_ids()

    model.eval()
    with torch.inference_mode():
        baseline_logits = (
            model(
                input_ids=input_ids,
                attention_mask=None,
                use_cache=False,
            )
            .logits.detach()
            .clone()
        )
    model.train()

    state_before = {
        name: value.detach().clone() for name, value in model.state_dict().items()
    }
    digest_before = _state_and_buffer_digest(model)
    tracked_tensors = {
        **dict(model.named_parameters()),
        **dict(model.named_buffers()),
    }
    buffer_ids_before = {name: id(value) for name, value in model.named_buffers()}
    versions_before = {name: value._version for name, value in tracked_tensors.items()}
    assert tracked_tensors
    assert buffer_ids_before
    assert all(parameter.grad is None for parameter in model.parameters())

    observation = _adapter(model).observe_batch(input_ids, position=2)

    assert model.last_logits is not None
    assert model.last_logits.shape == baseline_logits.shape
    assert model.last_logits.dtype == baseline_logits.dtype
    assert torch.equal(model.last_logits, baseline_logits)
    assert _state_and_buffer_digest(model) == digest_before
    state_after = model.state_dict()
    assert state_after.keys() == state_before.keys()
    for name, expected in state_before.items():
        assert torch.equal(state_after[name], expected)
    assert {
        name: id(value) for name, value in model.named_buffers()
    } == buffer_ids_before
    assert {
        name: value._version for name, value in tracked_tensors.items()
    } == versions_before
    assert all(parameter.grad is None for parameter in model.parameters())
    for tensor in (
        observation.resid_pre,
        observation.resid_post,
        observation.norm_summary,
        observation.logit_summary,
        observation.prediction_ids,
    ):
        assert tensor.grad_fn is None
        assert not tensor.requires_grad


def test_observation_forward_is_eval_inference_and_cache_free() -> None:
    model = _TraceableFakeNeoXForCausalLM()
    input_ids = _input_ids()
    attention_mask = torch.tensor(
        [[1, 1, 1, 1], [1, 1, 1, 0]],
        dtype=torch.long,
    )
    model.train()

    _adapter(model).observe_batch(
        input_ids,
        position=1,
        attention_mask=attention_mask,
    )

    contract = model.last_forward_contract
    assert contract is not None
    assert contract["grad_enabled"] is False
    assert contract["inference_mode"] is True
    assert contract["model_training"] is False
    assert set(contract["module_training"].values()) == {False}  # type: ignore[union-attr]
    assert contract["use_cache"] is False
    torch.testing.assert_close(contract["attention_mask"], attention_mask)  # type: ignore[arg-type]


@pytest.mark.parametrize("initial_training", [False, True])
def test_uniform_train_or_eval_mode_is_restored(initial_training: bool) -> None:
    model = _TraceableFakeNeoXForCausalLM()
    model.train(initial_training)
    modes_before = _module_modes(model)

    _adapter(model).observe_batch(_input_ids(), position=0)

    assert _module_modes(model) == modes_before


@pytest.mark.parametrize("fail_during_forward", [False, True])
def test_heterogeneous_submodule_modes_are_restored_exactly(
    fail_during_forward: bool,
) -> None:
    model = _TraceableFakeNeoXForCausalLM()
    model.train()
    model.gpt_neox.embed_in.eval()
    model.gpt_neox.layers[0].eval()
    model.gpt_neox.layers[1].train()
    model.gpt_neox.layers[2].eval()
    model.embed_out.eval()
    modes_before = _module_modes(model)
    digest_before = _state_and_buffer_digest(model)
    versions_before = _tensor_versions(model)
    buffer_ids_before = {name: id(value) for name, value in model.named_buffers()}
    assert all(parameter.grad is None for parameter in model.parameters())
    if fail_during_forward:
        model.fail_after_layer = 1

    if fail_during_forward:
        with pytest.raises(RuntimeError, match="fake failure after layer 1"):
            _adapter(model).observe_batch(_input_ids(), position=0)
    else:
        _adapter(model).observe_batch(_input_ids(), position=0)

    assert _module_modes(model) == modes_before
    assert _state_and_buffer_digest(model) == digest_before
    assert _tensor_versions(model) == versions_before
    assert {name: id(value) for name, value in model.named_buffers()} == (
        buffer_ids_before
    )
    assert all(parameter.grad is None for parameter in model.parameters())


def test_hooks_capture_exact_layer_pre_post_and_selected_position() -> None:
    model = _TraceableFakeNeoXForCausalLM()
    position = 2

    observation = _adapter(model).observe_batch(_input_ids(), position=position)

    assert model.execution_order == [0, 1, 2]
    expected_pre: list[Tensor] = []
    expected_post: list[Tensor] = []
    for layer in model.gpt_neox.layers:
        assert layer.last_input is not None
        assert layer.last_output is not None
        expected_pre.append(layer.last_input[:, position, :].to(torch.float32))
        expected_post.append(layer.last_output[:, position, :].to(torch.float32))
    torch.testing.assert_close(
        observation.resid_pre,
        torch.stack(expected_pre, dim=1),
        rtol=0,
        atol=0,
    )
    torch.testing.assert_close(
        observation.resid_post,
        torch.stack(expected_post, dim=1),
        rtol=0,
        atol=0,
    )
    first_layer_other_position = model.gpt_neox.layers[0].last_input[:, 1, :]
    assert not torch.equal(
        observation.resid_pre[:, 0, :],
        first_layer_other_position.to(torch.float32),
    )


def test_residual_captures_are_cpu_float32_synchronous_transfers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _TraceableFakeNeoXForCausalLM()
    original_to = torch.Tensor.to
    capture_transfers: list[dict[str, object]] = []

    def observed_to(self: Tensor, *args: object, **kwargs: object) -> Tensor:
        if kwargs.get("device") == "cpu" and kwargs.get("dtype") == torch.float32:
            capture_transfers.append(dict(kwargs))
        return original_to(self, *args, **kwargs)

    monkeypatch.setattr(torch.Tensor, "to", observed_to)

    observation = _adapter(model).observe_batch(_input_ids(), position=3)

    assert len(capture_transfers) == 2 * model.config.num_hidden_layers
    assert all(transfer["non_blocking"] is False for transfer in capture_transfers)
    assert all(transfer["copy"] is True for transfer in capture_transfers)
    for tensor in (
        observation.resid_pre,
        observation.resid_post,
        observation.norm_summary,
        observation.logit_summary,
    ):
        assert tensor.device.type == "cpu"
        assert tensor.dtype == torch.float32
    assert observation.prediction_ids.device.type == "cpu"
    assert observation.prediction_ids.dtype == torch.int64


def test_cpu_float32_capture_owns_storage_before_source_can_be_mutated() -> None:
    model = _TraceableFakeNeoXForCausalLM(dtype=torch.float32)
    first_layer = model.gpt_neox.layers[0]
    first_layer.mutate_input_after_output = True
    model.mutate_output_after_layer = 0
    input_ids = _input_ids()
    position = 2
    expected_pre = model.gpt_neox.embed_in(input_ids)[:, position, :].detach().clone()
    expected_post = expected_pre + first_layer.offset

    observation = _adapter(model).observe_batch(input_ids, position=position)

    assert first_layer.last_input is not None
    torch.testing.assert_close(first_layer.last_input[:, position, :], expected_pre)
    torch.testing.assert_close(
        observation.resid_pre[:, 0, :],
        expected_pre,
        rtol=0,
        atol=0,
    )
    torch.testing.assert_close(
        observation.resid_post[:, 0, :],
        expected_post,
        rtol=0,
        atol=0,
    )
    assert observation.resid_pre.untyped_storage().data_ptr() != (
        first_layer.last_input.untyped_storage().data_ptr()
    )
    assert observation.resid_post.untyped_storage().data_ptr() != (
        first_layer.last_output.untyped_storage().data_ptr()
    )


@pytest.mark.parametrize("fail_during_forward", [False, True])
def test_adapter_hooks_are_cleaned_up_without_removing_existing_hooks(
    fail_during_forward: bool,
) -> None:
    model = _TraceableFakeNeoXForCausalLM()
    sentinel_calls: list[tuple[str, int]] = []
    sentinel_handles: list[torch.utils.hooks.RemovableHandle] = []
    for layer_index, layer in enumerate(model.gpt_neox.layers):
        sentinel_handles.append(
            layer.register_forward_pre_hook(
                lambda _module, _args, index=layer_index: sentinel_calls.append(
                    ("pre", index)
                )
            )
        )
        sentinel_handles.append(
            layer.register_forward_hook(
                lambda _module, _args, _output, index=layer_index: (
                    sentinel_calls.append(("post", index))
                )
            )
        )
    hooks_before = _hook_state(model)
    if fail_during_forward:
        model.fail_after_layer = 1

    try:
        if fail_during_forward:
            with pytest.raises(RuntimeError, match="fake failure after layer 1"):
                _adapter(model).observe_batch(_input_ids(), position=1)
        else:
            _adapter(model).observe_batch(_input_ids(), position=1)
        assert _hook_state(model) == hooks_before
        assert sentinel_calls
    finally:
        for handle in sentinel_handles:
            handle.remove()


@pytest.mark.parametrize(
    ("fault", "message"),
    [
        ("omit_layer", "incomplete layer capture"),
        ("repeat_layer", "fired more than once"),
        ("wrong_hidden_size", "resid_post hidden size at layer 1"),
        ("truncate_logits", "logit vocabulary"),
    ],
)
def test_capture_and_output_mismatches_are_rejected(
    fault: str,
    message: str,
) -> None:
    model = _TraceableFakeNeoXForCausalLM()
    if fault == "omit_layer":
        model.omit_layer = 1
    elif fault == "repeat_layer":
        model.repeat_layer = 1
    elif fault == "wrong_hidden_size":
        model.gpt_neox.layers[1].truncate_output = True
    else:
        model.truncate_logits = True

    with pytest.raises(PythiaAdapterError, match=message):
        _adapter(model).observe_batch(_input_ids(), position=2)

    assert all(
        not layer._forward_pre_hooks and not layer._forward_hooks
        for layer in model.gpt_neox.layers
    )


def test_constructor_rejects_configured_layer_count_mismatch() -> None:
    model = _TraceableFakeNeoXForCausalLM()
    model.config.num_hidden_layers = 4

    with pytest.raises(PythiaAdapterError, match="num_hidden_layers does not match"):
        _adapter(model)


@pytest.mark.parametrize("invalid_path", ["missing", "wrong_type"])
def test_constructor_rejects_missing_or_wrong_gpt_neox_layer_path(
    invalid_path: str,
) -> None:
    model = _TraceableFakeNeoXForCausalLM()
    if invalid_path == "missing":
        del model.gpt_neox
    else:
        model.gpt_neox.layers = nn.Linear(4, 4)

    with pytest.raises(PythiaAdapterError, match="could not locate GPT-NeoX layers"):
        _adapter(model)


def test_partial_v1_capture_cannot_resume_under_current_v2_adapter(
    tmp_path,
) -> None:
    output_dir = tmp_path / "v1-capture"
    model = _TraceableFakeNeoXForCausalLM()
    model.fail_after_layer = 1
    adapter = _adapter(model)
    current_capture_metadata = adapter.capture_metadata

    def v1_capture_metadata():
        capture = current_capture_metadata()
        capture["capture_implementation"]["version"] = (
            "spirallens.pythia.residual_hooks.v1"
        )
        return capture

    adapter.capture_metadata = v1_capture_metadata  # type: ignore[method-assign]
    config = SweepConfig(
        output_dir=output_dir,
        context_ids=(0,),
        position=0,
        subset=(0, 1, 2, 3),
        batch_size=2,
    )
    with pytest.raises(RuntimeError, match="fake failure after layer 1"):
        run_id_sweep(adapter, config)

    manifest_path = output_dir / "manifest.json"
    v1_source = manifest_path.read_bytes()
    v1_manifest = json.loads(v1_source)
    assert v1_manifest["status"] == "failed"
    assert v1_manifest["capture"]["capture_implementation"]["version"] == (
        "spirallens.pythia.residual_hooks.v1"
    )
    assert len(v1_manifest["attempts"]) == 1

    adapter.capture_metadata = current_capture_metadata  # type: ignore[method-assign]
    model.fail_after_layer = None
    with pytest.raises(AtlasStateError, match="fingerprint"):
        run_id_sweep(
            adapter,
            SweepConfig(
                output_dir=output_dir,
                context_ids=(0,),
                position=0,
                subset=(0, 1, 2, 3),
                batch_size=1,
                resume=True,
            ),
        )

    assert manifest_path.read_bytes() == v1_source
