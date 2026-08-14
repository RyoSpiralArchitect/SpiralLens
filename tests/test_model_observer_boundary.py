from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import fields
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import scipy
import torch
import yaml
from fake_pythia import FakePythiaForCausalLM

from spirallens import _model_observer
from spirallens.adapters import (
    CAPTURE_IMPLEMENTATION_VERSION,
    LOGIT_SUMMARY_COLUMNS,
    BatchObservation,
    PythiaAdapter,
    pythia,
)
from spirallens.atlas import SweepConfig, load_manifest, run_id_sweep
from spirallens.atlas._capture_store import AtlasStore
from spirallens.atlas.store import (
    ATLAS_SCHEMA_VERSION,
    AtlasStateError,
    token_ids_sha256,
)

_ARRAY_NAMES = (
    "token_ids",
    "resid_pre",
    "resid_post",
    "norm_summary",
    "logit_summary",
    "prediction_ids",
)
_OBSERVATION_NAMES = _ARRAY_NAMES[1:]


def _initialize_store(
    output_dir: Path,
    *,
    torch_version: Callable[[], str],
) -> AtlasStore:
    token_ids = np.asarray((4, 2), dtype=np.int64)
    capture = {
        "atlas_schema_version": ATLAS_SCHEMA_VERSION,
        "capture_implementation": {
            "name": "test.model-observer-boundary",
            "version": "test.v1",
            "accelerator_to_cpu_copy": "synchronous",
            "activation_dtype": "float32",
        },
        "spirallens_version": "test",
        "torch_version": "test-torch",
        "transformers_version": "test-transformers",
        "effective_parameter_layout": [
            {
                "device": "cpu",
                "dtype": "float32",
                "parameter_tensors": 1,
                "parameter_values": 1,
            }
        ],
    }
    return AtlasStore.initialize(
        output_dir=output_dir,
        token_ids=token_ids,
        model_metadata={"num_layers": 1, "hidden_size": 2},
        request={"token_ids_sha256": token_ids_sha256(token_ids)},
        fingerprint_payload={"boundary": "test"},
        capture_metadata=capture,
        torch_version=torch_version,
        resume=False,
        batch_size=2,
    )


def test_private_observer_and_capture_store_import_without_model_stack(
    tmp_path: Path,
) -> None:
    source_root = Path(__file__).resolve().parents[1] / "src"
    dependency_roots = sorted(
        {
            str(Path(module.__file__).resolve().parent.parent)
            for module in (np, scipy, yaml)
        }
    )
    probe = f"""
import importlib
import importlib.abc
import json
from pathlib import Path
import sys

for root in {([str(source_root), *dependency_roots])!r}:
    sys.path.insert(0, root)

forbidden = (
    "torch",
    "transformers",
    "huggingface_hub",
    "safetensors",
    "spirallens.adapters",
)


def matches(name, prefix):
    return name == prefix or name.startswith(prefix + ".")


class Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(matches(fullname, prefix) for prefix in forbidden):
            raise ModuleNotFoundError(
                f"blocked model dependency: {{fullname}}", name=fullname
            )
        return None


sys.meta_path.insert(0, Blocker())
observer = importlib.import_module("spirallens._model_observer")
capture_store = importlib.import_module("spirallens.atlas._capture_store")
print(json.dumps({{
    "capture_store_origin": str(Path(capture_store.__file__).resolve()),
    "forbidden_loaded": sorted(
        prefix
        for prefix in forbidden
        if any(matches(name, prefix) for name in sys.modules)
    ),
    "observer_all": list(observer.__all__),
    "observer_origin": str(Path(observer.__file__).resolve()),
}}, sort_keys=True))
"""
    environment = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP", "VIRTUAL_ENV"):
        environment.pop(name, None)
    completed = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", probe],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "capture_store_origin": str(
            (source_root / "spirallens/atlas/_capture_store.py").resolve()
        ),
        "forbidden_loaded": [],
        "observer_all": [],
        "observer_origin": str(
            (source_root / "spirallens/_model_observer.py").resolve()
        ),
    }


def test_public_pythia_observation_identity_and_tensor_contract_are_unchanged() -> None:
    expected_fields = (
        "resid_pre",
        "resid_post",
        "norm_summary",
        "logit_summary",
        "prediction_ids",
    )

    assert LOGIT_SUMMARY_COLUMNS is pythia.LOGIT_SUMMARY_COLUMNS
    assert LOGIT_SUMMARY_COLUMNS is _model_observer.LOGIT_SUMMARY_COLUMNS
    assert BatchObservation.__module__ == "spirallens.adapters.pythia"
    assert tuple(field.name for field in fields(BatchObservation)) == expected_fields
    assert inspect.get_annotations(BatchObservation, eval_str=False) == {
        name: "Tensor" for name in expected_fields
    }
    parameters = tuple(inspect.signature(BatchObservation).parameters.values())
    assert tuple(parameter.name for parameter in parameters) == expected_fields
    assert all(
        parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and parameter.default is inspect.Parameter.empty
        and parameter.annotation == "Tensor"
        for parameter in parameters
    )
    assert CAPTURE_IMPLEMENTATION_VERSION == "spirallens.pythia.residual_hooks.v2"
    assert _model_observer.BatchObservationProtocol._is_runtime_protocol is False


def test_reference_pythia_observation_crosses_private_store_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = PythiaAdapter(
        FakePythiaForCausalLM(),
        model_id="offline/fake-pythia",
        revision="fixed-test-weights",
    )
    observed: list[BatchObservation] = []
    original = adapter.observe_batch

    def observe_batch(
        input_ids: torch.Tensor,
        *,
        position: int,
        attention_mask: torch.Tensor | None = None,
    ) -> BatchObservation:
        observation = original(
            input_ids,
            position=position,
            attention_mask=attention_mask,
        )
        observed.append(observation)
        return observation

    monkeypatch.setattr(adapter, "observe_batch", observe_batch)
    output_dir = tmp_path / "atlas"
    manifest = run_id_sweep(
        adapter,
        SweepConfig(
            output_dir=output_dir,
            context_ids=(0, 1, 2),
            position=1,
            subset=(4, 2),
            batch_size=2,
        ),
    )

    assert len(observed) == 1
    observation = observed[0]
    assert type(observation) is BatchObservation
    for name in _OBSERVATION_NAMES:
        np.testing.assert_array_equal(
            np.load(output_dir / f"{name}.npy", allow_pickle=False),
            getattr(observation, name).numpy(),
        )
    assert manifest["schema_version"] == "spirallens.activation_atlas.v2"
    assert manifest["capture"]["capture_implementation"]["version"] == (
        "spirallens.pythia.residual_hooks.v2"
    )
    assert manifest["environment"]["torch"] == str(torch.__version__)
    assert manifest["environment"]["torch"] == manifest["capture"]["torch_version"]
    assert load_manifest(output_dir, verify_checksums=True) == manifest


def test_store_preserves_observation_and_torch_version_order(tmp_path: Path) -> None:
    callback_observations: list[tuple[str, ...]] = []
    output_dir = tmp_path / "ordered"

    def torch_version() -> str:
        assert not (output_dir / "manifest.json").exists()
        callback_observations.append(
            tuple(sorted(path.name for path in output_dir.iterdir()))
        )
        return "test-torch"

    store = _initialize_store(output_dir, torch_version=torch_version)
    try:
        assert callback_observations == [
            tuple(f"{name}.npy" for name in sorted(_ARRAY_NAMES))
        ]
        assert store.manifest["environment"]["torch"] == "test-torch"

        events: list[str] = []

        class Array:
            def __init__(self, name: str, value: np.ndarray) -> None:
                self.name = name
                self.value = value

            @property
            def shape(self) -> tuple[int, ...]:
                events.append(f"shape:{self.name}")
                return self.value.shape

            def numpy(self) -> np.ndarray:
                events.append(f"numpy:{self.name}")
                return self.value

        values = {
            "resid_pre": np.ones((2, 1, 2), dtype=np.float32),
            "resid_post": np.full((2, 1, 2), 2, dtype=np.float32),
            "norm_summary": np.full((2, 1, 2), 3, dtype=np.float32),
            "logit_summary": np.full((2, 6), 4, dtype=np.float32),
            "prediction_ids": np.asarray((5, 6), dtype=np.int64),
        }
        observation = SimpleNamespace(
            **{name: Array(name, value) for name, value in values.items()}
        )
        store.write_batch(0, observation)

        assert events == [
            "shape:resid_pre",
            *(f"numpy:{name}" for name in _OBSERVATION_NAMES),
        ]
        for name, expected in values.items():
            np.testing.assert_array_equal(store.arrays[name], expected)
    finally:
        store.close()

    blocked_dir = tmp_path / "nonempty"
    blocked_dir.mkdir()
    (blocked_dir / "foreign").write_text("occupied", encoding="utf-8")
    with pytest.raises(AtlasStateError, match="non-empty directory"):
        _initialize_store(
            blocked_dir,
            torch_version=lambda: pytest.fail(
                "torch version observed before the existing output failure"
            ),
        )


def test_store_preserves_numpy_failure_identity_before_any_array_write(
    tmp_path: Path,
) -> None:
    store = _initialize_store(
        tmp_path / "failure",
        torch_version=lambda: "test-torch",
    )
    for array in store.arrays.values():
        array[:] = 0
        array.flush()
    events: list[str] = []
    failure = KeyboardInterrupt("observation conversion interrupted")

    class Array:
        def __init__(self, name: str, value: np.ndarray) -> None:
            self.name = name
            self.value = value

        @property
        def shape(self) -> tuple[int, ...]:
            events.append(f"shape:{self.name}")
            return self.value.shape

        def numpy(self) -> np.ndarray:
            events.append(f"numpy:{self.name}")
            if self.name == "norm_summary":
                raise failure
            return self.value

    values = {
        "resid_pre": np.ones((2, 1, 2), dtype=np.float32),
        "resid_post": np.ones((2, 1, 2), dtype=np.float32),
        "norm_summary": np.ones((2, 1, 2), dtype=np.float32),
        "logit_summary": np.ones((2, 6), dtype=np.float32),
        "prediction_ids": np.ones(2, dtype=np.int64),
    }
    observation = SimpleNamespace(
        **{name: Array(name, value) for name, value in values.items()}
    )
    try:
        with pytest.raises(KeyboardInterrupt) as captured:
            store.write_batch(0, observation)

        assert captured.value is failure
        assert failure.__cause__ is None
        assert failure.__context__ is None
        assert events == [
            "shape:resid_pre",
            "numpy:resid_pre",
            "numpy:resid_post",
            "numpy:norm_summary",
        ]
        assert store.manifest["progress"]["completed_rows"] == 0
        for array in store.arrays.values():
            assert not np.any(array)
    finally:
        store.close()
