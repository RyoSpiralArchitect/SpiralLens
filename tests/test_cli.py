from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from spirallens.cli import (
    _load_yaml_mapping,
    _neighbor_audit_config_from_protocol,
    _neighbor_audit_exit_code,
    _validate_recall_gate_contract,
    build_parser,
    main,
)
from spirallens.metrics import LedgerSummary
from spirallens.metrics.neighbor_receipt import (
    validate_neighbor_protocol_static_contract,
)


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
    assert captured["neighbor_backend_factory"] is None
    assert captured["neighbor_audit_receipts"] is None
    binding = captured["protocol_binding"]
    assert binding["declared_status"] == "preregistered-draft"
    assert binding["execution_status"] == "exploratory_override"
    assert binding["candidate_search_overrides"] == {"cosine_min": 0.999}
    assert len(binding["sha256"]) == 64
    summary = json.loads(capsys.readouterr().out)
    assert summary["execution_status"] == "exploratory_override"
    assert summary["neighbor_backend"] == "exact"


def test_candidates_cli_requires_receipt_for_faiss(
    tmp_path,
    capsys,
) -> None:
    exit_code = main(
        [
            "candidates",
            "--manifest",
            str(tmp_path / "manifest.json"),
            "--output",
            str(tmp_path / "candidates.jsonl"),
            "--layers",
            "0",
            "--neighbor-backend",
            "faiss-hnsw",
        ]
    )

    assert exit_code == 1
    assert "--expected-neighbor-protocol-sha256" in (
        capsys.readouterr().err
    )


def test_neighbor_audit_cli_fails_closed_on_protocol_digest(
    tmp_path,
    capsys,
) -> None:
    protocol = tmp_path / "neighbor.yaml"
    protocol.write_text("{}\n", encoding="utf-8")

    exit_code = main(
        [
            "neighbor-audit",
            "--manifest",
            str(tmp_path / "atlas"),
            "--layer",
            "0",
            "--protocol",
            str(protocol),
            "--expected-protocol-sha256",
            "0" * 64,
            "--output",
            str(tmp_path / "audit.json"),
        ]
    )

    assert exit_code == 1
    assert "does not match --expected-protocol-sha256" in (
        capsys.readouterr().err
    )


def test_neighbor_audit_prepare_only_owns_optional_output() -> None:
    parser = build_parser()
    prepared = parser.parse_args(
        [
            "neighbor-audit",
            "--manifest",
            "atlas",
            "--layer",
            "0",
            "--protocol",
            "neighbor.yaml",
            "--prepare-only",
        ]
    )

    assert prepared.prepare_only is True
    assert prepared.output is None
    with pytest.raises(SystemExit):
        parser.parse_args(["atlas", "--max-tokens", "1"])


def test_frozen_neighbor_audit_refuses_overwrite(
    tmp_path: Path,
    capsys,
) -> None:
    root = Path(__file__).resolve().parents[1]
    protocol = (
        root
        / "protocols"
        / "pythia70_slot_only_001_layer0_neighbor_v0_2.yaml"
    )
    protocol_sha256 = hashlib.sha256(protocol.read_bytes()).hexdigest()

    exit_code = main(
        [
            "neighbor-audit",
            "--manifest",
            str(tmp_path / "unused-atlas"),
            "--layer",
            "0",
            "--protocol",
            str(protocol),
            "--expected-protocol-sha256",
            protocol_sha256,
            "--output",
            str(tmp_path / "audit.json"),
            "--overwrite",
        ]
    )

    assert exit_code == 1
    assert "cannot overwrite an audit artifact" in (
        capsys.readouterr().err
    )


def test_draft_neighbor_protocol_is_prepare_only(
    tmp_path: Path,
    capsys,
) -> None:
    root = Path(__file__).resolve().parents[1]
    protocol = root / "protocols" / "pythia_neighbor_v0_2.yaml"

    exit_code = main(
        [
            "neighbor-audit",
            "--manifest",
            str(tmp_path / "unused-atlas"),
            "--layer",
            "0",
            "--protocol",
            str(protocol),
            "--output",
            str(tmp_path / "audit.json"),
        ]
    )

    assert exit_code == 1
    assert "draft protocols are prepare-only" in (
        capsys.readouterr().err
    )


def test_neighbor_protocol_loader_rejects_duplicate_keys(
    tmp_path: Path,
) -> None:
    protocol = tmp_path / "duplicate.yaml"
    protocol.write_text(
        "schema_version: first\nschema_version: second\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate key"):
        _load_yaml_mapping(protocol, label="neighbor protocol")


def test_tracked_neighbor_protocol_binds_frozen_recall_gate() -> None:
    root = Path(__file__).resolve().parents[1]
    protocol_path = root / "protocols" / "pythia_neighbor_v0_2.yaml"
    _, protocol = _load_yaml_mapping(
        protocol_path,
        label="neighbor protocol",
    )
    audit_config = _neighbor_audit_config_from_protocol(protocol)
    validate_neighbor_protocol_static_contract(protocol)

    gate_path, gate_bytes, gate = _validate_recall_gate_contract(
        protocol_path=protocol_path,
        document=protocol,
        audit_config=audit_config,
    )

    assert gate_path.name == "neighbor_recall_gate_v0_1.yaml"
    assert gate["status"] == "frozen"
    assert protocol["recall_gate_contract"]["sha256"]
    assert gate_path.read_bytes() == gate_bytes
    assert audit_config.query_local_recall_min == 0.99
    assert audit_config.stratum_recall_min == 0.99

    contradictory = dict(protocol)
    contradictory["status_override_for_review"] = "frozen"
    with pytest.raises(ValueError, match="top-level contract"):
        validate_neighbor_protocol_static_contract(contradictory)


@pytest.mark.parametrize(
    ("protocol_status", "audit_status", "eligible", "expected"),
    (
        ("preregistered-draft", "fail", False, 2),
        ("preregistered-draft", "insufficient", False, 2),
        ("preregistered-draft", "pass", False, 0),
        ("frozen", "fail", False, 2),
        ("frozen", "insufficient", False, 2),
        ("frozen", "pass", False, 2),
        ("frozen", "pass", True, 0),
    ),
)
def test_frozen_neighbor_audit_exit_status_is_fail_closed(
    protocol_status: str,
    audit_status: str,
    eligible: bool,
    expected: int,
) -> None:
    assert (
        _neighbor_audit_exit_code(
            protocol_status=protocol_status,
            audit_status=audit_status,
            promotion_eligible=eligible,
        )
        == expected
    )
