from __future__ import annotations

import json

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
