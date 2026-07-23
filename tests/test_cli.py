from __future__ import annotations

import json
from pathlib import Path

from spirallens.cli import main
from spirallens.metrics import LedgerSummary


def test_calibrate_cli_persists_a_complete_report(tmp_path, capsys) -> None:
    report_path = tmp_path / "calibration.json"

    exit_code = main(
        [
            "calibrate",
            "--samples",
            "256",
            "--output",
            str(report_path),
        ]
    )

    assert exit_code == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["summary"] == {"checks": 24, "failed": 0, "passed": 24}
    summary = json.loads(capsys.readouterr().out)
    assert summary["report"] == str(report_path.resolve())


def test_calibrate_cli_refuses_implicit_overwrite(tmp_path, capsys) -> None:
    report_path = tmp_path / "calibration.json"
    report_path.write_text('{"owned_by": "user"}\n', encoding="utf-8")

    exit_code = main(
        [
            "calibrate",
            "--samples",
            "256",
            "--output",
            str(report_path),
        ]
    )

    assert exit_code == 1
    assert json.loads(report_path.read_text(encoding="utf-8")) == {
        "owned_by": "user"
    }
    assert "refusing to overwrite" in capsys.readouterr().err


def test_atlas_cli_requires_explicit_run_scope(tmp_path, capsys) -> None:
    exit_code = main(
        [
            "atlas",
            "--output",
            str(tmp_path / "atlas"),
            "--context-ids",
            "0",
            "--position",
            "0",
        ]
    )

    assert exit_code == 1
    assert "choose --max-tokens/--subset" in capsys.readouterr().err


def test_context_bank_cli_validates_only_an_explicit_role(capsys) -> None:
    repository_root = Path(__file__).resolve().parents[1]
    bank_path = repository_root / "protocols/context_bank_example_v0_1.yaml"

    exit_code = main(
        [
            "context-bank",
            "validate",
            "--path",
            str(bank_path),
            "--allow-role",
            "example",
        ]
    )

    assert exit_code == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "valid"
    assert summary["role"] == "example"
    assert summary["claim_eligible"] is False
    assert summary["contexts"] == 8
    assert summary["model"]["vocab_size"] == 50_304
    assert summary["tokenizer"]["addressable_size"] == 50_277
    assert summary["language_space_atlas"] is False
    assert summary["semantic_unit"] is False


def test_context_bank_cli_rejects_role_mismatch(capsys) -> None:
    repository_root = Path(__file__).resolve().parents[1]
    bank_path = repository_root / "protocols/context_bank_example_v0_1.yaml"

    exit_code = main(
        [
            "context-bank",
            "validate",
            "--path",
            str(bank_path),
            "--allow-role",
            "discovery",
        ]
    )

    assert exit_code == 1
    assert "not in explicitly allowed roles" in capsys.readouterr().err


def test_atlas_cli_binds_context_bank_without_model_download(
    tmp_path,
    capsys,
    monkeypatch,
) -> None:
    import spirallens.adapters
    import spirallens.atlas

    repository_root = Path(__file__).resolve().parents[1]
    bank_path = repository_root / "protocols/context_bank_example_v0_1.yaml"
    captured = {}

    class FakeAdapter:
        pass

    def fake_from_pretrained(model_id, **kwargs):
        captured["model_id"] = model_id
        captured["model_kwargs"] = kwargs
        return FakeAdapter()

    def fake_run_id_sweep(adapter, config):
        captured["adapter"] = adapter
        captured["config"] = config
        return {
            "status": "complete",
            "run_id": "bound-test-run",
            "model": {"model_id": captured["model_id"]},
            "progress": {
                "completed_rows": 1,
                "total_rows": 1,
                "committed_batches": 1,
            },
            "request": {
                "context_bank_binding_sha256": (
                    config.context_bank_binding.sha256
                )
            },
        }

    monkeypatch.setattr(
        spirallens.adapters.PythiaAdapter,
        "from_pretrained",
        staticmethod(fake_from_pretrained),
    )
    monkeypatch.setattr(
        spirallens.atlas,
        "run_id_sweep",
        fake_run_id_sweep,
    )

    exit_code = main(
        [
            "atlas",
            "--output",
            str(tmp_path / "atlas"),
            "--context-bank",
            str(bank_path),
            "--context-id",
            "synthetic-bracketed-002",
            "--allow-role",
            "example",
            "--max-tokens",
            "1",
            "--local-files-only",
        ]
    )

    assert exit_code == 0
    assert captured["model_id"] == "EleutherAI/pythia-70m"
    assert captured["model_kwargs"]["revision"] == (
        "a39f36b100fe8a5377810d56c3f4789b9c53ac42"
    )
    config = captured["config"]
    assert config.context_ids == (2, 0, 3)
    assert config.position == 2
    assert config.effective_sweep_position == 1
    assert config.attention_mask == (1, 1, 1)
    assert config.context_bank_binding.context_id == "synthetic-bracketed-002"
    summary = json.loads(capsys.readouterr().out)
    assert (
        summary["context_bank_binding_sha256"]
        == config.context_bank_binding.sha256
    )


def test_candidates_cli_binds_protocol_and_propagates_overwrite(
    tmp_path,
    capsys,
    monkeypatch,
) -> None:
    import spirallens.metrics

    protocol = tmp_path / "protocol.yaml"
    protocol.write_text(
        "\n".join(
            (
                "protocol_id: test-protocol",
                "status: preregistered-draft",
                "claim_ceiling: 2",
                "candidate_search:",
                "  cosine_min: 0.995",
            )
        ),
        encoding="utf-8",
    )
    output = tmp_path / "candidates.jsonl"
    output.write_text("user-owned\n", encoding="utf-8")
    captured = {}

    def fake_extract(manifest, destination, **kwargs):
        captured.update(kwargs)
        return LedgerSummary(output_path=destination, candidate_count=0)

    monkeypatch.setattr(
        spirallens.metrics,
        "extract_candidates_from_manifest",
        fake_extract,
    )
    exit_code = main(
        [
            "candidates",
            "--manifest",
            str(tmp_path / "manifest.json"),
            "--output",
            str(output),
            "--protocol",
            str(protocol),
            "--cosine-min",
            "0.999",
            "--overwrite",
        ]
    )

    assert exit_code == 0
    assert captured["overwrite"] is True
    assert captured["protocol_id"] == "test-protocol"
    assert captured["protocol_claim_ceiling"] == 2
    binding = captured["protocol_binding"]
    assert binding["declared_status"] == "preregistered-draft"
    assert binding["execution_status"] == "exploratory_override"
    assert binding["candidate_search_overrides"] == {"cosine_min": 0.999}
    assert len(binding["sha256"]) == 64
    summary = json.loads(capsys.readouterr().out)
    assert summary["execution_status"] == "exploratory_override"
