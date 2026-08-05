from __future__ import annotations

import json

import pytest

from spirallens.cli import main


def test_public_example_plumbing_cli_forwards_closed_run_contract(
    tmp_path,
    capsys,
    monkeypatch,
) -> None:
    import spirallens.atlas.engineering_run

    captured = {}

    def fake_run_public_example_plumbing(**kwargs):
        captured.update(kwargs)
        return {
            "command": "public-example-plumbing run",
            "status": "complete",
            "claim_boundary": {"scientific_claim_eligible": False},
        }

    monkeypatch.setattr(
        spirallens.atlas.engineering_run,
        "run_public_example_plumbing",
        fake_run_public_example_plumbing,
    )
    protocol = tmp_path / "protocol.yaml"
    output = tmp_path / "atlas"
    receipt = tmp_path / "receipt.json"
    repository_root = tmp_path / "repository"

    exit_code = main(
        [
            "public-example-plumbing",
            "run",
            "--repository-root",
            str(repository_root),
            "--protocol",
            str(protocol),
            "--output",
            str(output),
            "--receipt",
            str(receipt),
            "--expected-protocol-source-sha256",
            "a" * 64,
            "--expected-protocol-canonical-sha256",
            "b" * 64,
        ]
    )

    assert exit_code == 0
    assert captured == {
        "repository_root": repository_root,
        "protocol_path": protocol,
        "output_dir": output,
        "receipt_path": receipt,
        "expected_protocol_source_sha256": "a" * 64,
        "expected_protocol_canonical_sha256": "b" * 64,
    }
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "complete"
    assert summary["claim_boundary"]["scientific_claim_eligible"] is False


def test_public_example_plumbing_cli_requires_repository_root(tmp_path) -> None:
    with pytest.raises(SystemExit, match="2"):
        main(
            [
                "public-example-plumbing",
                "run",
                "--protocol",
                str(tmp_path / "protocol.yaml"),
                "--output",
                str(tmp_path / "atlas"),
                "--receipt",
                str(tmp_path / "receipt.json"),
                "--expected-protocol-source-sha256",
                "a" * 64,
                "--expected-protocol-canonical-sha256",
                "b" * 64,
            ]
        )
