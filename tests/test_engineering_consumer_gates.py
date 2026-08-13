from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pytest

import spirallens.atlas as atlas_api
from spirallens.atlas import engineering_protocol
from spirallens.atlas import store as atlas_store
import spirallens.cli as cli
from spirallens.metrics import (
    CandidateSearchConfig,
    NeighborAuditConfig,
    NeighborAuditProtocolBinding,
    NeighborQuerySelectionContract,
)
from spirallens.metrics import candidate_pairs


class _GateRejected(PermissionError):
    pass


_ATLAS_ARRAY_NAMES = (
    "token_ids",
    "resid_pre",
    "resid_post",
    "norm_summary",
    "logit_summary",
    "prediction_ids",
)


def _minimal_manifest_structure(
    request: dict[str, object],
) -> dict[str, object]:
    capture = {
        "capture_implementation": {
            "name": "test-capture",
            "version": "1",
            "accelerator_to_cpu_copy": "synchronous",
            "activation_dtype": "float32",
        },
        "atlas_schema_version": atlas_store.ATLAS_SCHEMA_VERSION,
        "spirallens_version": "test",
        "torch_version": "test",
        "transformers_version": "test",
        "effective_parameter_layout": [
            {
                "device": "cpu",
                "dtype": "float32",
                "parameter_tensors": 1,
                "parameter_values": 1,
            }
        ],
    }
    capture_fingerprint = atlas_store._canonical_sha256(capture)
    return {
        "schema_version": atlas_store.ATLAS_SCHEMA_VERSION,
        "status": "complete",
        "arrays": {name: {} for name in _ATLAS_ARRAY_NAMES},
        "progress": {
            "completed_rows": 1,
            "total_rows": 1,
        },
        "capture": capture,
        "capture_fingerprint": capture_fingerprint,
        "request": {
            "capture_fingerprint": capture_fingerprint,
            **request,
        },
        "model": {},
    }


def _consumer_manifest() -> dict[str, object]:
    return {
        "status": "complete",
        "progress": {
            "completed_rows": 1,
            "total_rows": 1,
        },
        "request": {"engineering_marker": True},
        "model": {},
        "run_id": "engineering-gate-test",
    }


def _persist_manifest(
    tmp_path: Path,
    manifest: dict[str, object],
) -> Path:
    root = tmp_path / "atlas"
    root.mkdir()
    path = root / "manifest.json"
    path.write_text(
        json.dumps(manifest, sort_keys=True),
        encoding="utf-8",
    )
    return path


def _install_rejecting_gate(
    monkeypatch: pytest.MonkeyPatch,
    calls: list[tuple[object, str]],
) -> None:
    def reject(request: object, consumer: str) -> None:
        calls.append((request, consumer))
        raise _GateRejected(consumer)

    monkeypatch.setattr(
        engineering_protocol,
        "require_engineering_consumer_authorized",
        reject,
    )


def _forbid_array_load(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        pytest.fail("manifest array loader ran before engineering authorization")

    monkeypatch.setattr(candidate_pairs, "_load_manifest_array", fail)


def _install_manifest_only_probe(
    monkeypatch: pytest.MonkeyPatch,
    manifest: dict[str, object],
) -> None:
    monkeypatch.setattr(
        atlas_api,
        "load_manifest_metadata",
        lambda *args, **kwargs: manifest,
    )

    def fail_full_load(*args: object, **kwargs: object) -> None:
        pytest.fail("full atlas load ran before engineering authorization")

    monkeypatch.setattr(atlas_api, "load_manifest", fail_full_load)


def test_manifest_structure_validates_engineering_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _minimal_manifest_structure({})
    seen: dict[str, object] = {}

    class _ValidationReached(RuntimeError):
        pass

    def stop(
        request: object,
        manifest_model: object = None,
    ) -> None:
        seen["request"] = request
        seen["model"] = manifest_model
        raise _ValidationReached

    monkeypatch.setattr(
        atlas_store,
        "validate_engineering_request_binding",
        stop,
    )

    with pytest.raises(_ValidationReached):
        atlas_store._verify_manifest_structure(manifest)

    assert seen == {
        "request": manifest["request"],
        "model": manifest["model"],
    }


def test_manifest_structure_wraps_malformed_engineering_binding() -> None:
    manifest = _minimal_manifest_structure(
        {"public_example_plumbing_protocol_binding": {}}
    )

    with pytest.raises(
        atlas_store.AtlasIntegrityError,
        match="public-example engineering binding is invalid",
    ):
        atlas_store._verify_manifest_structure(manifest)


def test_candidate_extraction_rejects_before_array_load(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _consumer_manifest()
    path = _persist_manifest(tmp_path, manifest)
    calls: list[tuple[object, str]] = []
    _install_manifest_only_probe(monkeypatch, manifest)
    _install_rejecting_gate(monkeypatch, calls)
    _forbid_array_load(monkeypatch)

    with pytest.raises(_GateRejected, match="candidate_extraction"):
        candidate_pairs.extract_candidates_from_manifest(
            path,
            tmp_path / "candidates.jsonl",
        )

    assert calls == [(manifest["request"], "candidate_extraction")]


def test_manifest_neighbor_audit_rejects_before_array_load(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import spirallens.execution_freeze as execution_freeze

    manifest = _consumer_manifest()
    path = _persist_manifest(tmp_path, manifest)
    calls: list[tuple[object, str]] = []
    _install_manifest_only_probe(monkeypatch, manifest)
    monkeypatch.setattr(
        execution_freeze,
        "validated_execution_freeze_sha256",
        lambda value: "f" * 64,
    )
    _install_rejecting_gate(monkeypatch, calls)
    _forbid_array_load(monkeypatch)

    protocol = NeighborAuditProtocolBinding(
        protocol_id="engineering-gate-test",
        status="frozen",
        source_sha256="a" * 64,
        candidate_config_sha256="b" * 64,
        audit_config_sha256="c" * 64,
        query_selection=NeighborQuerySelectionContract(
            seed=1,
            count=1,
            global_row_key_sha256="d" * 64,
        ),
    )

    class _Freeze:
        def revalidate(self) -> None:
            pass

    with pytest.raises(_GateRejected, match="neighbor_audit"):
        candidate_pairs._audit_neighbor_backend_from_manifest(
            path,
            layer_index=0,
            subject_backend_factory=lambda values: pytest.fail(
                "backend factory ran before engineering authorization"
            ),
            protocol_binding=protocol,
            candidate_config=CandidateSearchConfig(layer_indices=(0,)),
            audit_config=NeighborAuditConfig(),
            execution_freeze=_Freeze(),
        )

    assert calls == [(manifest["request"], "neighbor_audit")]


def test_cli_neighbor_audit_rejects_before_array_load(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _consumer_manifest()
    _persist_manifest(tmp_path, manifest)
    calls: list[tuple[object, str]] = []
    _install_manifest_only_probe(monkeypatch, manifest)
    _install_rejecting_gate(monkeypatch, calls)
    _forbid_array_load(monkeypatch)

    repository = Path(__file__).resolve().parents[1]
    protocol = (
        repository / "protocols" / "pythia70_slot_only_001_layer0_neighbor_v0_4.yaml"
    )
    arguments: argparse.Namespace = cli.build_parser().parse_args(
        [
            "neighbor-audit",
            "--manifest",
            str(tmp_path / "atlas"),
            "--layer",
            "0",
            "--protocol",
            str(protocol),
            "--expected-protocol-sha256",
            hashlib.sha256(protocol.read_bytes()).hexdigest(),
            "--prepare-only",
        ]
    )

    with pytest.raises(_GateRejected, match="neighbor_audit"):
        cli._run_neighbor_audit(arguments)

    assert calls == [(manifest["request"], "neighbor_audit")]
