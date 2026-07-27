from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

import pytest

from spirallens.atlas.engineering_run import (
    PublicExamplePlumbingRunError,
    _require_offline_environment,
    _resource_preflight,
    _stable_regular_file_sha256,
    _verify_protocol_git_anchor,
)


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
    assert _stable_regular_file_sha256(path) == hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


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
            vocab_size=50304,
            num_layers=6,
            hidden_size=512,
        ),
        resource_budget=SimpleNamespace(
            estimator_id=(
                "pythia-atlas-conservative-static-estimate-v0.1"
            ),
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
    assert result["minimum_peak_bytes"] < (
        protocol.resource_budget.estimated_peak_bytes
    )
    assert result["physical_memory_bytes"] == 24 * 1024 * 1024 * 1024


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
