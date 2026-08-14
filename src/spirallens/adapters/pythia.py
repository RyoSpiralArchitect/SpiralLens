"""Minimal Hugging Face GPT-NeoX/Pythia observation adapter.

The adapter deliberately exposes architectural observations rather than
semantic labels.  It hooks each GPT-NeoX block at its input and output, copies
only the requested token position to CPU, and removes every hook in ``finally``.
No TransformerLens dependency is required.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version as package_version
import json
from typing import Any, Mapping, Sequence

import torch
from torch import Tensor, nn

from spirallens import __version__ as SPIRALLENS_VERSION
from spirallens._model_observer import (
    LOGIT_SUMMARY_COLUMNS as _LOGIT_SUMMARY_COLUMNS,
)


CAPTURE_IMPLEMENTATION_VERSION = "spirallens.pythia.residual_hooks.v2"
LOGIT_SUMMARY_COLUMNS = _LOGIT_SUMMARY_COLUMNS


class PythiaAdapterError(RuntimeError):
    """Raised when a model does not satisfy the GPT-NeoX adapter contract."""


@dataclass(frozen=True)
class BatchObservation:
    """CPU-resident observations for one input batch.

    ``resid_pre`` and ``resid_post`` have shape ``[batch, layer, hidden]``.
    ``norm_summary`` has shape ``[batch, layer, 2]`` with pre/post L2 norms.
    ``logit_summary`` has columns documented by
    :data:`LOGIT_SUMMARY_COLUMNS`.
    """

    resid_pre: Tensor
    resid_post: Tensor
    norm_summary: Tensor
    logit_summary: Tensor
    prediction_ids: Tensor

    def __post_init__(self) -> None:
        tensors = (
            self.resid_pre,
            self.resid_post,
            self.norm_summary,
            self.logit_summary,
            self.prediction_ids,
        )
        if any(t.device.type != "cpu" for t in tensors):
            raise ValueError("BatchObservation tensors must be CPU-resident")


def _first_tensor(value: Any, *, where: str) -> Tensor:
    """Return the first tensor in a common Hugging Face output container."""

    if isinstance(value, Tensor):
        return value
    if isinstance(value, (tuple, list)):
        for item in value:
            try:
                return _first_tensor(item, where=where)
            except PythiaAdapterError:
                continue
    if isinstance(value, Mapping):
        for item in value.values():
            try:
                return _first_tensor(item, where=where)
            except PythiaAdapterError:
                continue
    raise PythiaAdapterError(f"{where} did not contain a tensor")


def _json_safe(value: Any) -> Any:
    """Convert config metadata into finite, deterministic JSON values."""

    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if not torch.isfinite(torch.tensor(value)):
            raise PythiaAdapterError("model config contains a non-finite float")
        return value
    if isinstance(value, Mapping):
        return {
            str(key): _json_safe(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except (TypeError, ValueError):
            pass
    return str(value)


def _installed_package_version(distribution: str) -> str:
    try:
        return package_version(distribution)
    except PackageNotFoundError:
        return "not-installed"


class PythiaAdapter:
    """Observe a Hugging Face ``GPTNeoXForCausalLM``-compatible model."""

    def __init__(
        self,
        model: nn.Module,
        *,
        model_id: str,
        revision: str | None = None,
    ) -> None:
        self.model = model
        self.model_id = str(model_id)
        self.revision = revision
        self.config = getattr(model, "config", None)
        if self.config is None:
            raise PythiaAdapterError("model must expose a Hugging Face-style config")

        model_type = getattr(self.config, "model_type", None)
        if model_type not in (None, "gpt_neox"):
            raise PythiaAdapterError(
                f"expected config.model_type='gpt_neox', got {model_type!r}"
            )

        self.layers = self._find_layers(model)
        if not self.layers:
            raise PythiaAdapterError("GPT-NeoX model exposes no transformer layers")

        self.hidden_size = int(getattr(self.config, "hidden_size", 0))
        self.vocab_size = int(getattr(self.config, "vocab_size", 0))
        if self.hidden_size <= 0 or self.vocab_size <= 0:
            raise PythiaAdapterError(
                "config.hidden_size and config.vocab_size must be positive"
            )
        configured_layers = getattr(self.config, "num_hidden_layers", None)
        if configured_layers is not None and int(configured_layers) != len(self.layers):
            raise PythiaAdapterError(
                "config.num_hidden_layers does not match gpt_neox.layers: "
                f"{configured_layers} != {len(self.layers)}"
            )

    @classmethod
    def from_pretrained(
        cls,
        model_id: str,
        *,
        revision: str | None = None,
        device: str | torch.device | None = None,
        local_files_only: bool = False,
        **model_kwargs: Any,
    ) -> "PythiaAdapter":
        """Load a causal LM lazily through ``transformers``.

        ``device_map`` and quantization kwargs can be passed through
        ``model_kwargs``.  A direct ``device`` move is only performed when no
        device map was requested.
        """

        try:
            from transformers import AutoModelForCausalLM
        except ImportError as exc:  # pragma: no cover - import environment only
            raise PythiaAdapterError(
                "transformers is required to load a pretrained Pythia model"
            ) from exc

        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            revision=revision,
            local_files_only=local_files_only,
            **model_kwargs,
        )
        if device is not None and "device_map" not in model_kwargs:
            model.to(device)
        return cls(model, model_id=model_id, revision=revision)

    @staticmethod
    def _find_layers(model: nn.Module) -> Sequence[nn.Module]:
        candidates = (
            getattr(model, "gpt_neox", None),
            getattr(getattr(model, "model", None), "gpt_neox", None),
            getattr(model, "base_model", None),
        )
        for candidate in candidates:
            layers = getattr(candidate, "layers", None)
            if isinstance(layers, (nn.ModuleList, list, tuple)):
                return layers
            nested = getattr(candidate, "gpt_neox", None)
            layers = getattr(nested, "layers", None)
            if isinstance(layers, (nn.ModuleList, list, tuple)):
                return layers
        raise PythiaAdapterError(
            "could not locate GPT-NeoX layers at model.gpt_neox.layers"
        )

    @property
    def num_layers(self) -> int:
        return len(self.layers)

    @property
    def input_device(self) -> torch.device:
        """Device on which the model expects ``input_ids``."""

        get_embeddings = getattr(self.model, "get_input_embeddings", None)
        if callable(get_embeddings):
            embeddings = get_embeddings()
            weight = getattr(embeddings, "weight", None)
            if isinstance(weight, Tensor):
                return weight.device
        try:
            return next(self.model.parameters()).device
        except StopIteration as exc:
            raise PythiaAdapterError("model has no parameters") from exc

    def config_metadata(self) -> dict[str, Any]:
        """Return JSON-safe model metadata used for provenance fingerprints."""

        to_dict = getattr(self.config, "to_dict", None)
        raw_config = to_dict() if callable(to_dict) else vars(self.config)
        config = _json_safe(raw_config)
        # Assert serializability here rather than during a long-running sweep.
        json.dumps(config, sort_keys=True, allow_nan=False)
        architectures = getattr(self.config, "architectures", None)
        architecture = (
            str(architectures[0])
            if architectures
            else self.model.__class__.__name__
        )
        resolved_revision = getattr(self.config, "_commit_hash", None)
        parameter_count = sum(
            parameter.numel() for parameter in self.model.parameters()
        )
        parameter_dtypes = sorted(
            {
                str(parameter.dtype).removeprefix("torch.")
                for parameter in self.model.parameters()
            }
        )
        parameter_devices = sorted(
            {str(parameter.device) for parameter in self.model.parameters()}
        )
        return {
            "model_id": self.model_id,
            "requested_revision": self.revision,
            "resolved_revision": resolved_revision or self.revision,
            "architecture": architecture,
            "model_type": getattr(self.config, "model_type", None),
            "num_layers": self.num_layers,
            "hidden_size": self.hidden_size,
            "vocab_size": self.vocab_size,
            "parameter_count": parameter_count,
            "parameter_dtypes": parameter_dtypes,
            "parameter_devices": parameter_devices,
            "config": config,
            "rope": self.rope_metadata(),
        }

    def capture_metadata(self) -> dict[str, Any]:
        """Return the effective implementation/runtime capture contract.

        This is evaluated immediately before every run or resume, so moving or
        casting the model after an interrupted attempt changes the fingerprint.
        """

        grouped: dict[tuple[str, str], dict[str, Any]] = {}
        for parameter in self.model.parameters():
            device = str(parameter.device)
            dtype = str(parameter.dtype).removeprefix("torch.")
            entry = grouped.setdefault(
                (device, dtype),
                {
                    "device": device,
                    "dtype": dtype,
                    "parameter_tensors": 0,
                    "parameter_values": 0,
                },
            )
            entry["parameter_tensors"] += 1
            entry["parameter_values"] += parameter.numel()
        parameter_layout = [
            grouped[key] for key in sorted(grouped, key=lambda item: (item[0], item[1]))
        ]
        return {
            "capture_implementation": {
                "name": "PythiaAdapter.observe_batch.residual_hooks",
                "version": CAPTURE_IMPLEMENTATION_VERSION,
                "accelerator_to_cpu_copy": "synchronous",
                "activation_dtype": "float32",
            },
            "spirallens_version": SPIRALLENS_VERSION,
            "torch_version": str(torch.__version__),
            "transformers_version": _installed_package_version("transformers"),
            "effective_parameter_layout": parameter_layout,
        }

    def rope_metadata(self) -> dict[str, Any]:
        """Describe Pythia's known (usually partial) RoPE configuration."""

        num_heads = int(getattr(self.config, "num_attention_heads", 0))
        if num_heads <= 0 or self.hidden_size % num_heads:
            raise PythiaAdapterError(
                "hidden_size must be divisible by num_attention_heads"
            )
        head_dim = self.hidden_size // num_heads
        rotary_fraction = float(
            getattr(
                self.config,
                "partial_rotary_factor",
                getattr(self.config, "rotary_pct", 1.0),
            )
        )
        if not 0.0 <= rotary_fraction <= 1.0:
            raise PythiaAdapterError(
                f"invalid partial rotary fraction: {rotary_fraction}"
            )
        rotary_ndims = int(head_dim * rotary_fraction)
        return {
            "kind": "partial_rope" if rotary_fraction < 1.0 else "rope",
            "source": "model.config",
            "num_attention_heads": num_heads,
            "head_dim": head_dim,
            "rotary_fraction": rotary_fraction,
            "rotary_ndims": rotary_ndims,
            "base": float(
                getattr(
                    self.config,
                    "rope_theta",
                    getattr(self.config, "rotary_emb_base", 10_000.0),
                )
            ),
            "scaling": _json_safe(getattr(self.config, "rope_scaling", None)),
            "max_position_embeddings": int(
                getattr(self.config, "max_position_embeddings", 0)
            ),
        }

    def observe_batch(
        self,
        input_ids: Tensor,
        *,
        position: int,
        attention_mask: Tensor | None = None,
    ) -> BatchObservation:
        """Capture block inputs/outputs and compact logit statistics.

        Only the selected sequence position is copied from accelerator memory.
        The method is intentionally batch-scoped so callers can write each
        result directly to disk rather than building an in-memory atlas.
        """

        if input_ids.ndim != 2:
            raise ValueError(
                f"input_ids must have shape [batch, sequence], got {input_ids.shape}"
            )
        if input_ids.dtype != torch.long:
            raise ValueError(f"input_ids must use torch.long, got {input_ids.dtype}")
        if not 0 <= position < input_ids.shape[1]:
            raise ValueError(
                f"position must be in [0, {input_ids.shape[1] - 1}], got {position}"
            )
        if input_ids.shape[0] == 0:
            raise ValueError("input_ids batch must not be empty")
        if torch.any(input_ids < 0) or torch.any(input_ids >= self.vocab_size):
            raise ValueError("input_ids contain token IDs outside model vocabulary")

        model_input = input_ids.to(self.input_device)
        model_mask = None
        if attention_mask is not None:
            if attention_mask.shape != input_ids.shape:
                raise ValueError(
                    "attention_mask must have the same shape as input_ids"
                )
            model_mask = attention_mask.to(self.input_device)

        pre_by_layer: dict[int, Tensor] = {}
        post_by_layer: dict[int, Tensor] = {}
        handles: list[Any] = []

        def capture_pre(layer_index: int):
            def hook(_module: nn.Module, args: tuple[Any, ...]) -> None:
                hidden = _first_tensor(args, where=f"layer {layer_index} input")
                self._capture_position(
                    hidden, position, layer_index, "resid_pre", pre_by_layer
                )

            return hook

        def capture_post(layer_index: int):
            def hook(
                _module: nn.Module, _args: tuple[Any, ...], output: Any
            ) -> None:
                hidden = _first_tensor(output, where=f"layer {layer_index} output")
                self._capture_position(
                    hidden, position, layer_index, "resid_post", post_by_layer
                )

            return hook

        training_modes = tuple(
            (module, module.training) for module in self.model.modules()
        )
        try:
            self.model.eval()
            for layer_index, layer in enumerate(self.layers):
                handles.append(
                    layer.register_forward_pre_hook(capture_pre(layer_index))
                )
                handles.append(
                    layer.register_forward_hook(capture_post(layer_index))
                )
            with torch.inference_mode():
                outputs = self.model(
                    input_ids=model_input,
                    attention_mask=model_mask,
                    use_cache=False,
                )
        finally:
            for handle in handles:
                handle.remove()
            # ``model.train(previous_root_mode)`` would flatten a deliberately
            # mixed tree (for example, a frozen/eval submodule inside a
            # training model).  Observation restores every exact pre-call
            # module flag without recursively rewriting its descendants.
            for module, training in training_modes:
                module.training = training

        expected = set(range(self.num_layers))
        if set(pre_by_layer) != expected or set(post_by_layer) != expected:
            raise PythiaAdapterError(
                "incomplete layer capture: "
                f"pre={sorted(pre_by_layer)}, post={sorted(post_by_layer)}"
            )

        resid_pre = torch.stack(
            [pre_by_layer[index] for index in range(self.num_layers)], dim=1
        )
        resid_post = torch.stack(
            [post_by_layer[index] for index in range(self.num_layers)], dim=1
        )
        norm_summary = torch.stack(
            (
                torch.linalg.vector_norm(resid_pre, dim=-1),
                torch.linalg.vector_norm(resid_post, dim=-1),
            ),
            dim=-1,
        ).to(dtype=torch.float32)

        logits = self._extract_logits(outputs)
        if logits.ndim != 3:
            raise PythiaAdapterError(
                f"model logits must have shape [batch, sequence, vocab], got {logits.shape}"
            )
        if logits.shape[:2] != model_input.shape:
            raise PythiaAdapterError(
                "model logits batch/sequence dimensions do not match input_ids"
            )
        if logits.shape[-1] != self.vocab_size:
            raise PythiaAdapterError(
                f"logit vocabulary {logits.shape[-1]} != {self.vocab_size}"
            )

        logits_at_position = logits[:, position, :].to(dtype=torch.float32)
        logsumexp = torch.logsumexp(logits_at_position, dim=-1)
        log_probs = logits_at_position - logsumexp[:, None]
        probabilities = torch.exp(log_probs)
        input_tokens = model_input[:, position, None]
        logit_summary = torch.stack(
            (
                logits_at_position.max(dim=-1).values,
                logits_at_position.mean(dim=-1),
                logits_at_position.std(dim=-1, unbiased=False),
                logsumexp,
                -(probabilities * log_probs).sum(dim=-1),
                logits_at_position.gather(dim=-1, index=input_tokens).squeeze(-1),
            ),
            dim=-1,
        )
        prediction_ids = logits_at_position.argmax(dim=-1)

        return BatchObservation(
            resid_pre=resid_pre,
            resid_post=resid_post,
            norm_summary=norm_summary.cpu(),
            logit_summary=logit_summary.cpu(),
            prediction_ids=prediction_ids.to(device="cpu", dtype=torch.int64),
        )

    def _capture_position(
        self,
        hidden: Tensor,
        position: int,
        layer_index: int,
        label: str,
        destination: dict[int, Tensor],
    ) -> None:
        if hidden.ndim != 3:
            raise PythiaAdapterError(
                f"{label} at layer {layer_index} must be rank 3, got {hidden.shape}"
            )
        if hidden.shape[-1] != self.hidden_size:
            raise PythiaAdapterError(
                f"{label} hidden size at layer {layer_index} is "
                f"{hidden.shape[-1]}, expected {self.hidden_size}"
            )
        if position >= hidden.shape[1]:
            raise PythiaAdapterError(
                f"{label} sequence length at layer {layer_index} is too short"
            )
        if layer_index in destination:
            raise PythiaAdapterError(
                f"{label} hook at layer {layer_index} fired more than once"
            )
        destination[layer_index] = (
            hidden[:, position, :]
            .detach()
            # Keep the copy synchronous.  In particular, an asynchronous MPS
            # copy can outlive the hook while the accelerator reuses its
            # source buffer, producing intermittent non-finite atlas rows.
            # ``copy=True`` also makes CPU/float32 capture an owned snapshot;
            # without it, ``Tensor.to`` may return a detached view sharing the
            # model's storage when device and dtype already match.
            .to(
                device="cpu",
                dtype=torch.float32,
                non_blocking=False,
                copy=True,
            )
        )

    @staticmethod
    def _extract_logits(outputs: Any) -> Tensor:
        logits = getattr(outputs, "logits", None)
        if isinstance(logits, Tensor):
            return logits
        if isinstance(outputs, Mapping) and isinstance(outputs.get("logits"), Tensor):
            return outputs["logits"]
        return _first_tensor(outputs, where="model output logits")
