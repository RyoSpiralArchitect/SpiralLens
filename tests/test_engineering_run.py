from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

import pytest
import yaml

from spirallens.adapters import CAPTURE_IMPLEMENTATION_VERSION, PythiaAdapter
from spirallens.atlas import engineering_run
from spirallens.atlas.engineering_protocol import (
    PublicExamplePlumbingProtocolIntegrityError,
    PublicExamplePlumbingProtocolSchemaError,
    public_example_plumbing_protocol_from_dict,
)
from spirallens.atlas.engineering_run import (
    PublicExamplePlumbingRunError,
    _require_offline_environment,
    _resource_preflight,
    _stable_regular_file_sha256,
    _verify_model_metadata,
    _verify_protocol_git_anchor,
)

from engineering_fixtures import public_example_protocol_payload


def test_offline_environment_is_mandatory_and_refuses_credentials(
    monkeypatch,
) -> None:
    for name in (
        "HF_HUB_OFFLINE",
        "TRANSFORMERS_OFFLINE",
        "HF_TOKEN",
        "HUGGING_FACE_HUB_TOKEN",
    ):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(
        PublicExamplePlumbingRunError,
        match="offline environment",
    ):
        _require_offline_environment()

    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    _require_offline_environment()
    monkeypatch.setenv("HF_TOKEN", "must-not-be-used")
    with pytest.raises(
        PublicExamplePlumbingRunError,
        match="refuses inherited",
    ):
        _require_offline_environment()


def test_stable_model_file_hash_uses_content_bytes(tmp_path: Path) -> None:
    path = tmp_path / "model.safetensors"
    path.write_bytes(b"offline-model-fixture")
    assert (
        _stable_regular_file_sha256(path)
        == hashlib.sha256(path.read_bytes()).hexdigest()
    )


def test_resource_preflight_checks_live_disk_and_memory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config = tmp_path / "config.json"
    weights = tmp_path / "model.safetensors"
    config.write_bytes(b"{}")
    weights.write_bytes(b"x" * 1024)
    protocol = SimpleNamespace(
        capture=SimpleNamespace(batch_size=8),
        model=SimpleNamespace(
            model_id="EleutherAI/pythia-70m",
            vocab_size=50304,
            num_layers=6,
            hidden_size=512,
        ),
        resource_budget=SimpleNamespace(
            estimator_id=("pythia-atlas-conservative-static-estimate-v0.1"),
            estimated_output_bytes=4 * 1024 * 1024,
            max_estimated_output_bytes=16 * 1024 * 1024,
            estimated_peak_bytes=1024 * 1024 * 1024,
            max_estimated_peak_bytes=2 * 1024 * 1024 * 1024,
        ),
    )
    monkeypatch.setattr(
        "spirallens.atlas.engineering_run._physical_memory_bytes",
        lambda: 24 * 1024 * 1024 * 1024,
    )
    monkeypatch.setattr(
        shutil,
        "disk_usage",
        lambda path: SimpleNamespace(
            free=90 * 1024**3,
        ),
    )

    result = _resource_preflight(
        protocol=protocol,
        model_paths={
            "config.json": config,
            "model.safetensors": weights,
        },
        output_parent=tmp_path,
        context_length=1,
    )

    assert result["status"] == "pass"
    assert result["minimum_peak_bytes"] == 287_708_162
    assert result["physical_memory_bytes"] == 24 * 1024 * 1024 * 1024

    protocol.model.model_id = "EleutherAI/pythia-160m"
    with pytest.raises(
        PublicExamplePlumbingRunError,
        match="not registered",
    ):
        _resource_preflight(
            protocol=protocol,
            model_paths={
                "config.json": config,
                "model.safetensors": weights,
            },
            output_parent=tmp_path,
            context_length=1,
        )


def test_model_metadata_uses_the_closed_profile_layout() -> None:
    protocol = public_example_plumbing_protocol_from_dict(
        public_example_protocol_payload()
    )
    metadata = {
        "model_id": protocol.model.model_id,
        "requested_revision": protocol.model.revision,
        "resolved_revision": protocol.model.revision,
        "architecture": protocol.model.architecture,
        "num_layers": protocol.model.num_layers,
        "hidden_size": protocol.model.hidden_size,
        "vocab_size": protocol.model.vocab_size,
        "parameter_count": 70_426_624,
        "parameter_devices": ["cpu"],
        "parameter_dtypes": ["float32"],
        "config": {
            "num_attention_heads": protocol.model.num_attention_heads,
            "intermediate_size": protocol.model.intermediate_size,
            "max_position_embeddings": (
                protocol.model.max_position_embeddings
            ),
        },
    }
    capture = {
        "capture_implementation": {
            "name": "PythiaAdapter.observe_batch.residual_hooks",
            "version": CAPTURE_IMPLEMENTATION_VERSION,
            "accelerator_to_cpu_copy": "synchronous",
            "activation_dtype": "float32",
        },
        "effective_parameter_layout": [
            {
                "device": "cpu",
                "dtype": "float32",
                "parameter_tensors": 76,
                "parameter_values": 70_426_624,
            }
        ],
    }
    adapter = SimpleNamespace(
        config_metadata=lambda: metadata,
        capture_metadata=lambda: capture,
    )

    _verify_model_metadata(adapter, protocol)

    metadata["parameter_count"] = 1
    with pytest.raises(
        PublicExamplePlumbingProtocolIntegrityError,
        match="parameter_count",
    ):
        _verify_model_metadata(adapter, protocol)
    metadata["parameter_count"] = 70_426_624
    capture["effective_parameter_layout"][0]["parameter_tensors"] = 75
    with pytest.raises(
        PublicExamplePlumbingProtocolIntegrityError,
        match="production capture layout",
    ):
        _verify_model_metadata(adapter, protocol)


def test_git_anchor_accepts_only_clean_tracked_protocol_blob() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "protocols/context_bank_example_v0_1.yaml"
    head = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert (
        _verify_protocol_git_anchor(
            root=root,
            protocol_path=path,
            implementation_commit=head,
        )
        == head
    )


def test_public_runner_rejects_pythia160_before_model_context_or_output_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = public_example_protocol_payload()
    payload["model"]["id"] = "EleutherAI/pythia-160m"
    protocol_path = tmp_path / "pythia160-unsupported.yaml"
    source = yaml.safe_dump(payload, sort_keys=False).encode("utf-8")
    protocol_path.write_bytes(source)
    output = tmp_path / payload["capture"]["output_id"]
    receipt = tmp_path / "receipt.json"

    def forbidden(*args, **kwargs):
        del args, kwargs
        raise AssertionError("unsupported model reached forbidden I/O")

    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("HUGGING_FACE_HUB_TOKEN", raising=False)
    for name in (
        "_resolve_verified_model_files",
        "_resource_preflight",
        "load_context_bank",
        "run_id_sweep",
        "write_public_example_plumbing_receipt",
    ):
        monkeypatch.setattr(engineering_run, name, forbidden)
    monkeypatch.setattr(
        PythiaAdapter,
        "from_pretrained",
        forbidden,
    )

    with pytest.raises(
        PublicExamplePlumbingProtocolSchemaError,
        match="not registered",
    ):
        engineering_run.run_public_example_plumbing(
            repository_root=Path(__file__).resolve().parents[1],
            protocol_path=protocol_path,
            output_dir=output,
            receipt_path=receipt,
            expected_protocol_source_sha256=hashlib.sha256(source).hexdigest(),
            expected_protocol_canonical_sha256="0" * 64,
        )

    assert not output.exists()
    assert not receipt.exists()
