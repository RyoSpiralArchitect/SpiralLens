from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from spirallens.atlas.engineering_receipt import (
    PUBLIC_EXAMPLE_PLUMBING_RECEIPT_SCHEMA_VERSION,
    PublicExamplePlumbingReceipt,
    PublicExamplePlumbingReceiptError,
    PublicExampleProtocolReceiptBinding,
    _receipt_from_validated_atlas_manifest,
    load_public_example_plumbing_receipt,
    write_public_example_plumbing_receipt,
)
from spirallens.atlas.engineering_protocol import (
    LoadedPublicExamplePlumbingProtocol,
    _build_public_example_plumbing_protocol_binding,
    public_example_plumbing_protocol_binding_sha256,
    public_example_plumbing_protocol_from_dict,
)
from spirallens.atlas.store import ATLAS_SCHEMA_VERSION, token_ids_sha256

from engineering_fixtures import (
    passing_execution_preflight,
    public_example_protocol_payload,
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _loaded_protocol() -> LoadedPublicExamplePlumbingProtocol:
    protocol = public_example_plumbing_protocol_from_dict(
        public_example_protocol_payload(
            token_ids=(7, 11),
            output_id="pythia70-public-example-v0.1",
        )
    )
    source_bytes = b"protocol-source"
    return LoadedPublicExamplePlumbingProtocol(
        protocol=protocol,
        source_bytes=source_bytes,
        source_path=Path("/fixture/protocol.yaml"),
        source_sha256=hashlib.sha256(source_bytes).hexdigest(),
        canonical_sha256=protocol.canonical_sha256,
    )


def _binding() -> PublicExampleProtocolReceiptBinding:
    loaded = _loaded_protocol()
    protocol = loaded.protocol
    return PublicExampleProtocolReceiptBinding(
        source_sha256=loaded.source_sha256,
        canonical_sha256=loaded.canonical_sha256,
        output_id=protocol.capture.output_id,
        token_ids=protocol.token_selection.token_ids,
        model_id=protocol.model.model_id,
        model_revision=protocol.model.revision,
        config_blob_sha256=dict(protocol.model.files)["config.json"],
        model_blob_sha256=dict(protocol.model.files)["model.safetensors"],
    )


def _manifest() -> dict[str, object]:
    loaded = _loaded_protocol()
    protocol = loaded.protocol
    binding = _binding()
    engineering_binding = _build_public_example_plumbing_protocol_binding(
        loaded,
        verified_model_files=dict(protocol.model.files),
        execution_preflight=passing_execution_preflight(),
    )
    capture = {
        "capture_implementation": {
            "name": "PythiaAdapter.observe_batch.residual_hooks",
            "version": "spirallens.pythia.residual_hooks.v1",
            "accelerator_to_cpu_copy": "synchronous",
            "activation_dtype": "float32",
        },
        "atlas_schema_version": ATLAS_SCHEMA_VERSION,
        "spirallens_version": "0.1.0",
        "torch_version": "2.7.0",
        "transformers_version": "4.52.0",
        "effective_parameter_layout": [
            {
                "device": "cpu",
                "dtype": "float32",
                "parameter_tensors": 76,
                "parameter_values": 70_426_624,
            }
        ],
    }
    capture_fingerprint = _digest(
        json.dumps(capture, sort_keys=True, separators=(",", ":"))
    )
    arrays = {
        name: {
            "path": f"{name}.npy",
            "shape": [2],
            "dtype": "float32",
            "sha256": _digest(name),
            "file_size_bytes": index + 1,
        }
        for index, name in enumerate(
            (
                "token_ids",
                "resid_pre",
                "resid_post",
                "norm_summary",
                "logit_summary",
                "prediction_ids",
            )
        )
    }
    return {
        "schema_version": ATLAS_SCHEMA_VERSION,
        "status": "complete",
        "run_id": "run-public-example-001",
        "capture": capture,
        "capture_fingerprint": capture_fingerprint,
        "request": {
            "model_id": binding.model_id,
            "requested_model_revision": binding.model_revision,
            "resolved_model_revision": binding.model_revision,
            "config_blob_sha256": binding.config_blob_sha256,
            "model_blob_sha256": binding.model_blob_sha256,
            "num_tokens": 2,
            "token_ids_sha256": token_ids_sha256(
                __import__("numpy").asarray(binding.token_ids, dtype="<i8")
            ),
            "request_identity_sha256": _digest("request"),
            "capture_fingerprint": capture_fingerprint,
            "selection": {
                "kind": "subset",
                "subset_size_before_limit": 2,
                "max_tokens": None,
            },
            "batch_size_initial": protocol.capture.batch_size,
            "batch_size_latest": protocol.capture.batch_size,
            "capture_dtype": "float32",
            "output_id": protocol.capture.output_id,
            "language_space_atlas": False,
            "semantic_unit": False,
            "context_bank_binding": {
                "bank": {
                    "source_sha256": (
                        protocol.context_bank.source_sha256
                    ),
                    "canonical_sha256": (
                        protocol.context_bank.canonical_sha256
                    ),
                    "content": {"claim_eligible": False},
                },
                "selected_context": {
                    "context_id": protocol.context_bank.context_id,
                    "role": "example",
                },
            },
            "public_example_plumbing_protocol_binding": (
                engineering_binding
            ),
            "public_example_plumbing_protocol_binding_sha256": (
                public_example_plumbing_protocol_binding_sha256(
                    engineering_binding
                )
            ),
        },
        "model": {
            "model_id": binding.model_id,
            "requested_revision": binding.model_revision,
            "resolved_revision": binding.model_revision,
            "architecture": protocol.model.architecture,
            "num_layers": protocol.model.num_layers,
            "hidden_size": protocol.model.hidden_size,
            "vocab_size": protocol.model.vocab_size,
            "parameter_devices": ["cpu"],
            "parameter_dtypes": ["float32"],
        },
        "environment": {
            "python": "3.12.0",
            "numpy": "2.2.0",
            "torch": "2.7.0",
        },
        "progress": {
            "completed_rows": 2,
            "total_rows": 2,
        },
        "arrays": arrays,
    }


def _receipt() -> PublicExamplePlumbingReceipt:
    return _receipt_from_validated_atlas_manifest(
        _manifest(),
        manifest_sha256=_digest("manifest"),
        protocol_binding=_binding(),
    )


def test_constructor_binds_complete_atlas_and_keeps_claims_closed() -> None:
    receipt = _receipt()
    payload = receipt.to_dict()

    assert payload["schema_version"] == PUBLIC_EXAMPLE_PLUMBING_RECEIPT_SCHEMA_VERSION
    assert payload["row_count"] == len(_binding().token_ids)
    assert payload["gates"] == {
        "capture": "pass",
        "storage": "pass",
        "checksum": "pass",
        "reload": "pass",
    }
    assert payload["execution_facts"] == {
        "model_accessed": True,
        "activation_values_persisted": True,
        "tokenizer_runtime_verified": False,
    }
    assert payload["claim_boundary"]["scientific_claim_eligible"] is False
    assert payload["claim_boundary"]["p1_instrument_consumed"] is False
    assert set(payload["d0_d8"].values()) == {"not_run"}
    assert set(payload["analysis_status"].values()) == {"not_run"}
    assert receipt.canonical_bytes == json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def test_constructor_rejects_generic_atlas_without_prerun_binding() -> None:
    manifest = _manifest()
    request = manifest["request"]
    assert isinstance(request, dict)
    request.pop("public_example_plumbing_protocol_binding")
    request.pop("public_example_plumbing_protocol_binding_sha256")

    with pytest.raises(
        PublicExamplePlumbingReceiptError,
        match="lacks its pre-run",
    ):
        _receipt_from_validated_atlas_manifest(
            manifest,
            manifest_sha256=_digest("manifest"),
            protocol_binding=_binding(),
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda manifest: manifest["request"].__setitem__("num_tokens", 1),
            "num_tokens",
        ),
        (
            lambda manifest: manifest["request"].__setitem__(
                "model_blob_sha256", _digest("different")
            ),
            "model_blob_sha256",
        ),
        (
            lambda manifest: manifest["capture"]["effective_parameter_layout"][
                0
            ].__setitem__("device", "mps"),
            "CPU",
        ),
    ],
)
def test_constructor_rejects_manifest_protocol_mismatch(
    mutation,
    message: str,
) -> None:
    manifest = _manifest()
    mutation(manifest)
    with pytest.raises(PublicExamplePlumbingReceiptError, match=message):
        _receipt_from_validated_atlas_manifest(
            manifest,
            manifest_sha256=_digest("manifest"),
            protocol_binding=_binding(),
        )


def test_receipt_has_exact_fields_and_relative_output_identity() -> None:
    payload = _receipt().to_dict()
    payload["unexpected"] = False
    with pytest.raises(
        PublicExamplePlumbingReceiptError,
        match="fields differ",
    ):
        PublicExamplePlumbingReceipt.from_payload(payload)

    binding = _binding()
    with pytest.raises(
        PublicExamplePlumbingReceiptError,
        match="relative output identity",
    ):
        PublicExampleProtocolReceiptBinding(
            source_sha256=binding.source_sha256,
            canonical_sha256=binding.canonical_sha256,
            output_id="/private/atlas",
            token_ids=binding.token_ids,
            model_id=binding.model_id,
            model_revision=binding.model_revision,
            config_blob_sha256=binding.config_blob_sha256,
            model_blob_sha256=binding.model_blob_sha256,
        )

    payload = _receipt().to_dict()
    payload["claim_boundary"]["scientific_claim_eligible"] = 0
    with pytest.raises(
        PublicExamplePlumbingReceiptError,
        match="closed engineering contract",
    ):
        PublicExamplePlumbingReceipt.from_payload(payload)


def test_loader_requires_both_expected_digests_and_rejects_bad_json(
    tmp_path: Path,
) -> None:
    receipt = _receipt()
    path = tmp_path / "receipt.json"
    path.write_bytes(receipt.canonical_bytes)
    assert (
        load_public_example_plumbing_receipt(
            path,
            expected_source_sha256=receipt.sha256,
            expected_canonical_sha256=receipt.canonical_sha256,
        )
        == receipt
    )
    with pytest.raises(PublicExamplePlumbingReceiptError, match="source"):
        load_public_example_plumbing_receipt(
            path,
            expected_source_sha256="0" * 64,
            expected_canonical_sha256=receipt.canonical_sha256,
        )

    for source, message in (
        (b'{"x":1,"x":2}', "duplicate"),
        (b'{"x":NaN}', "non-finite"),
    ):
        path.write_bytes(source)
        digest = hashlib.sha256(source).hexdigest()
        with pytest.raises(PublicExamplePlumbingReceiptError, match=message):
            load_public_example_plumbing_receipt(
                path,
                expected_source_sha256=digest,
                expected_canonical_sha256=digest,
            )


def test_writer_is_atomic_no_overwrite_and_strictly_reloads(
    tmp_path: Path,
) -> None:
    receipt = _receipt()
    path = tmp_path / "receipt.json"
    assert write_public_example_plumbing_receipt(path, receipt) == receipt
    assert path.read_bytes() == receipt.canonical_bytes

    with pytest.raises(
        PublicExamplePlumbingReceiptError,
        match="overwrite is forbidden",
    ):
        write_public_example_plumbing_receipt(path, receipt)
    assert path.read_bytes() == receipt.canonical_bytes
    assert not tuple(tmp_path.glob(".*.tmp"))
