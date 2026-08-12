from __future__ import annotations

import copy
import hashlib

import pytest
import yaml

from spirallens.access import AtlasConsumer
from spirallens.atlas.engineering_protocol import (
    EngineeringConsumerAuthorizationError,
    PublicExamplePlumbingProtocolIntegrityError,
    PublicExamplePlumbingProtocolSchemaError,
    _build_public_example_plumbing_protocol_binding,
    load_public_example_plumbing_protocol,
    public_example_plumbing_protocol_binding_sha256,
    public_example_plumbing_protocol_from_dict,
    require_engineering_consumer_authorized,
    token_ids_little_endian_i8_sha256,
    validate_engineering_request_binding,
)


def _payload() -> dict[str, object]:
    token_ids = (0, 7, 42)
    return {
        "schema_version": "spirallens.public-example-plumbing-protocol.v0.1",
        "protocol_id": "pythia70-public-example-smoke-v0.1",
        "status": "frozen_engineering",
        "purpose": "public_example_capture_plumbing",
        "claim_ceiling": "level_0",
        "execution_class": "public_example_engineering",
        "scientific_claim_eligible": False,
        "p1_instrument_consumed": False,
        "tokenizer_runtime_verified": False,
        "source": {
            "repository": "RyoSpiralArchitect/SpiralLens",
            "implementation_commit": "a" * 40,
            "implementation_repository_path": (
                "src/spirallens/adapters/pythia.py"
            ),
            "implementation_module_sha256": "b" * 64,
        },
        "model": {
            "id": "EleutherAI/pythia-70m",
            "revision": "c" * 40,
            "architecture": "GPTNeoXForCausalLM",
            "num_layers": 6,
            "hidden_size": 512,
            "vocab_size": 50304,
            "num_attention_heads": 8,
            "intermediate_size": 2048,
            "max_position_embeddings": 2048,
            "files": {
                "config.json": "d" * 64,
                "model.safetensors": "e" * 64,
            },
        },
        "context_bank": {
            "path": "protocols/context_bank_example_v0_1.yaml",
            "source_sha256": "f" * 64,
            "canonical_sha256": "1" * 64,
            "context_id": "synthetic-slot-only-001",
            "role": "example",
            "claim_eligible": False,
        },
        "token_selection": {
            "kind": "explicit_sorted_ids",
            "token_ids": list(token_ids),
            "token_ids_sha256": token_ids_little_endian_i8_sha256(token_ids),
        },
        "capture": {
            "device": "cpu",
            "dtype": "float32",
            "batch_size": 2,
            "output_id": "pythia70-public-example-smoke-v0.1",
            "observation_contract": "all_residual_pre_post_layers",
        },
        "resource_budget": {
            "estimator_id": ("pythia-atlas-conservative-static-estimate-v0.1"),
            "safety_factor": 4,
            "estimated_output_bytes": 300_000,
            "max_estimated_output_bytes": 1_000_000,
            "estimated_peak_bytes": 600_000,
            "max_estimated_peak_bytes": 2_000_000,
            "claim_boundary": (
                "static-array-and-working-set-estimate-not-os-oom-guarantee"
            ),
        },
        "authorizations": {
            "example_model_access": True,
            "activation_atlas_capture": True,
            "network_access": False,
            "subject_protocol_preparation": False,
            "subject_execution": False,
            "instrument_bundle_conversion": False,
            "candidate_search": False,
            "neighbor_audit": False,
            "graph_construction": False,
            "field_estimation": False,
            "core_detection": False,
            "loop_construction": False,
            "holonomy_analysis": False,
            "winding_analysis": False,
            "semantic_analysis": False,
            "sae_analysis": False,
            "causal_analysis": False,
            "integer_output": False,
        },
        "stage_status": {
            **{f"D{index}": "not_run" for index in range(9)},
            "subject_protocol_preparation": "not_run",
            "subject_execution": "not_run",
            "instrument_bundle_conversion": "not_run",
            "candidate_search": "not_run",
            "neighbor_audit": "not_run",
            "graph_construction": "not_run",
            "field_estimation": "not_run",
            "core_detection": "not_run",
            "loop_construction": "not_run",
            "holonomy_analysis": "not_run",
            "winding_analysis": "not_run",
            "semantic_analysis": "not_run",
            "sae_analysis": "not_run",
            "causal_analysis": "not_run",
            "integer_output": "not_run",
        },
        "allowed_consumers": ["atlas_integrity_validation"],
    }


def _write(tmp_path, payload: dict[str, object]):
    path = tmp_path / "protocol.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _request(loaded) -> dict[str, object]:
    protocol = loaded.protocol
    binding = _build_public_example_plumbing_protocol_binding(
        loaded,
        verified_model_files=dict(protocol.model.files),
        execution_preflight={
            "status": "pass",
            "estimator_id": protocol.resource_budget.estimator_id,
            "model_file_bytes": 400_000,
            "minimum_peak_bytes": 500_000,
            "free_disk_bytes": 2_000_000,
            "physical_memory_bytes": 3_000_000,
            "disk_reserve_bytes": 1,
        },
    )
    return {
        "model_id": protocol.model.model_id,
        "requested_model_revision": protocol.model.revision,
        "resolved_model_revision": protocol.model.revision,
        "config_blob_sha256": dict(protocol.model.files)["config.json"],
        "model_blob_sha256": dict(protocol.model.files)["model.safetensors"],
        "num_tokens": len(protocol.token_selection.token_ids),
        "token_ids_sha256": protocol.token_selection.token_ids_sha256,
        "selection": {
            "kind": "subset",
            "subset_size_before_limit": len(
                protocol.token_selection.token_ids
            ),
            "max_tokens": None,
        },
        "batch_size_initial": protocol.capture.batch_size,
        "batch_size_latest": 1,
        "capture_dtype": "float32",
        "output_id": protocol.capture.output_id,
        "language_space_atlas": False,
        "semantic_unit": False,
        "context_bank_binding": {
            "bank": {
                "source_sha256": protocol.context_bank.source_sha256,
                "canonical_sha256": protocol.context_bank.canonical_sha256,
                "content": {"claim_eligible": False},
            },
            "selected_context": {
                "context_id": protocol.context_bank.context_id,
                "role": "example",
            },
        },
        "public_example_plumbing_protocol_binding": binding,
        "public_example_plumbing_protocol_binding_sha256": (
            public_example_plumbing_protocol_binding_sha256(binding)
        ),
    }


def test_load_binds_source_and_canonical_digests(tmp_path) -> None:
    path = _write(tmp_path, _payload())
    loaded = load_public_example_plumbing_protocol(path)

    assert (
        loaded.source_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    )
    assert loaded.canonical_sha256 == loaded.protocol.canonical_sha256
    assert loaded.protocol.model.hidden_size == 512
    assert loaded.protocol.token_selection.token_ids == (0, 7, 42)

    again = load_public_example_plumbing_protocol(
        path,
        expected_source_sha256=loaded.source_sha256,
        expected_canonical_sha256=loaded.canonical_sha256,
    )
    assert again.protocol == loaded.protocol


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ("status", "draft"),
        ("purpose", "subject_capture"),
        ("claim_ceiling", "level_1"),
        ("scientific_claim_eligible", True),
        ("p1_instrument_consumed", True),
        ("tokenizer_runtime_verified", True),
    ],
)
def test_root_constants_are_closed(path, value) -> None:
    payload = _payload()
    payload[path] = value
    with pytest.raises(PublicExamplePlumbingProtocolSchemaError):
        public_example_plumbing_protocol_from_dict(payload)


def test_unknown_keys_aliases_and_duplicates_are_rejected(tmp_path) -> None:
    payload = _payload()
    payload["surprise"] = True
    with pytest.raises(
        PublicExamplePlumbingProtocolSchemaError, match="unknown"
    ):
        public_example_plumbing_protocol_from_dict(payload)

    alias = tmp_path / "alias.yaml"
    alias.write_text("base: &base {x: 1}\ncopy: *base\n", encoding="utf-8")
    with pytest.raises(
        PublicExamplePlumbingProtocolSchemaError, match="aliases"
    ):
        load_public_example_plumbing_protocol(alias)

    duplicate = tmp_path / "duplicate.yaml"
    duplicate.write_text(
        "schema_version: x\nschema_version: y\n", encoding="utf-8"
    )
    with pytest.raises(
        PublicExamplePlumbingProtocolSchemaError, match="duplicate"
    ):
        load_public_example_plumbing_protocol(duplicate)


@pytest.mark.parametrize(
    "unsafe",
    [
        "../context.yaml",
        "/tmp/context.yaml",
        "protocols/../context.yaml",
        r"protocols\context.yaml",
    ],
)
def test_context_bank_path_must_be_repository_relative(unsafe) -> None:
    payload = _payload()
    payload["context_bank"]["path"] = unsafe
    with pytest.raises(
        PublicExamplePlumbingProtocolSchemaError, match="relative"
    ):
        public_example_plumbing_protocol_from_dict(payload)


def test_token_ids_are_explicit_sorted_unique_and_little_endian_bound() -> (
    None
):
    payload = _payload()
    payload["token_selection"]["token_ids"] = [7, 0, 42]
    with pytest.raises(
        PublicExamplePlumbingProtocolSchemaError, match="sorted"
    ):
        public_example_plumbing_protocol_from_dict(payload)

    payload = _payload()
    payload["token_selection"]["token_ids_sha256"] = "0" * 64
    with pytest.raises(
        PublicExamplePlumbingProtocolIntegrityError, match="int64"
    ):
        public_example_plumbing_protocol_from_dict(payload)


def test_model_dimensions_files_and_resource_receipt_are_closed() -> None:
    payload = _payload()
    payload["model"]["id"] = "EleutherAI/pythia-160m"
    with pytest.raises(
        PublicExamplePlumbingProtocolSchemaError,
        match="not registered",
    ):
        public_example_plumbing_protocol_from_dict(payload)

    payload = _payload()
    payload["model"]["hidden_size"] = 513
    with pytest.raises(PublicExamplePlumbingProtocolSchemaError, match="512"):
        public_example_plumbing_protocol_from_dict(payload)

    payload = _payload()
    payload["model"]["files"]["weights.bin"] = "9" * 64
    with pytest.raises(
        PublicExamplePlumbingProtocolSchemaError, match="unknown"
    ):
        public_example_plumbing_protocol_from_dict(payload)

    payload = _payload()
    payload["resource_budget"]["estimated_output_bytes"] = 1
    with pytest.raises(
        PublicExamplePlumbingProtocolSchemaError, match="conservative"
    ):
        public_example_plumbing_protocol_from_dict(payload)


def test_authorizations_stages_and_consumers_are_closed() -> None:
    payload = _payload()
    payload["authorizations"]["candidate_search"] = True
    with pytest.raises(PublicExamplePlumbingProtocolSchemaError):
        public_example_plumbing_protocol_from_dict(payload)

    payload = _payload()
    payload["stage_status"]["D4"] = "pass"
    with pytest.raises(PublicExamplePlumbingProtocolSchemaError):
        public_example_plumbing_protocol_from_dict(payload)

    payload = _payload()
    payload["allowed_consumers"] = ["candidate_extraction"]
    with pytest.raises(PublicExamplePlumbingProtocolSchemaError):
        public_example_plumbing_protocol_from_dict(payload)


def test_binding_and_request_validation_are_pure_and_fail_closed(
    tmp_path,
) -> None:
    loaded = load_public_example_plumbing_protocol(
        _write(tmp_path, _payload())
    )
    request = _request(loaded)
    model = {
        "model_id": "EleutherAI/pythia-70m",
        "requested_revision": "c" * 40,
        "resolved_revision": "c" * 40,
        "architecture": "GPTNeoXForCausalLM",
        "num_layers": 6,
        "hidden_size": 512,
        "vocab_size": 50304,
        "parameter_devices": ["cpu"],
        "parameter_dtypes": ["float32"],
    }
    assert (
        validate_engineering_request_binding(request, model) == loaded.protocol
    )

    changed = copy.deepcopy(request)
    changed["token_ids_sha256"] = "0" * 64
    with pytest.raises(PublicExamplePlumbingProtocolIntegrityError):
        validate_engineering_request_binding(changed, model)

    changed = copy.deepcopy(request)
    changed["public_example_plumbing_protocol_binding"]["content"][
        "status"
    ] = "draft"
    with pytest.raises(PublicExamplePlumbingProtocolIntegrityError):
        validate_engineering_request_binding(changed, model)

    changed = copy.deepcopy(request)
    changed["public_example_plumbing_protocol_binding"][
        "interpretation_contract"
    ]["scientific_claim_eligible"] = 0
    changed["public_example_plumbing_protocol_binding_sha256"] = (
        public_example_plumbing_protocol_binding_sha256(
            changed["public_example_plumbing_protocol_binding"]
        )
    )
    with pytest.raises(PublicExamplePlumbingProtocolSchemaError):
        validate_engineering_request_binding(changed, model)

    changed = copy.deepcopy(request)
    changed["num_tokens"] = float(changed["num_tokens"])
    with pytest.raises(
        PublicExamplePlumbingProtocolIntegrityError,
        match="num_tokens",
    ):
        validate_engineering_request_binding(changed, model)

    changed = copy.deepcopy(request)
    changed["selection"]["subset_size_before_limit"] = 3.0
    with pytest.raises(
        PublicExamplePlumbingProtocolIntegrityError,
        match="selection",
    ):
        validate_engineering_request_binding(changed, model)

    changed_model = copy.deepcopy(model)
    changed_model["num_layers"] = 6.0
    with pytest.raises(
        PublicExamplePlumbingProtocolIntegrityError,
        match="manifest_model",
    ):
        validate_engineering_request_binding(request, changed_model)

    assert validate_engineering_request_binding({"legacy": True}) is None


def test_binding_requires_observed_model_hashes_and_passing_live_resources(
    tmp_path,
) -> None:
    loaded = load_public_example_plumbing_protocol(
        _write(tmp_path, _payload())
    )
    protocol = loaded.protocol
    with pytest.raises(
        PublicExamplePlumbingProtocolIntegrityError,
        match="observed model",
    ):
        _build_public_example_plumbing_protocol_binding(
            loaded,
            verified_model_files={
                **dict(protocol.model.files),
                "model.safetensors": "0" * 64,
            },
            execution_preflight={
                "status": "pass",
                "estimator_id": protocol.resource_budget.estimator_id,
                "model_file_bytes": 400_000,
                "minimum_peak_bytes": 500_000,
                "free_disk_bytes": 2_000_000,
                "physical_memory_bytes": 3_000_000,
                "disk_reserve_bytes": 1,
            },
        )

    with pytest.raises(
        PublicExamplePlumbingProtocolIntegrityError,
        match="resource preflight",
    ):
        _build_public_example_plumbing_protocol_binding(
            loaded,
            verified_model_files=dict(protocol.model.files),
            execution_preflight={
                "status": "pass",
                "estimator_id": protocol.resource_budget.estimator_id,
                "model_file_bytes": 400_000,
                "minimum_peak_bytes": 500_000,
                "free_disk_bytes": 1,
                "physical_memory_bytes": 3_000_000,
                "disk_reserve_bytes": 1,
            },
        )


def test_consumer_gate_allows_only_integrity_validation(tmp_path) -> None:
    loaded = load_public_example_plumbing_protocol(
        _write(tmp_path, _payload())
    )
    request = _request(loaded)
    require_engineering_consumer_authorized(
        request, "atlas_integrity_validation"
    )
    require_engineering_consumer_authorized(
        request, AtlasConsumer.ATLAS_INTEGRITY_VALIDATION
    )
    with pytest.raises(
        EngineeringConsumerAuthorizationError, match="candidate_extraction"
    ):
        require_engineering_consumer_authorized(
            request, "candidate_extraction"
        )
    with pytest.raises(
        EngineeringConsumerAuthorizationError, match="candidate_search"
    ):
        require_engineering_consumer_authorized(
            request, AtlasConsumer.CANDIDATE_SEARCH
        )
    require_engineering_consumer_authorized(
        {"legacy": True}, "candidate_extraction"
    )


def test_expected_source_and_canonical_digest_mismatches_fail(
    tmp_path,
) -> None:
    path = _write(tmp_path, _payload())
    with pytest.raises(
        PublicExamplePlumbingProtocolIntegrityError, match="source"
    ):
        load_public_example_plumbing_protocol(
            path, expected_source_sha256="0" * 64
        )
    with pytest.raises(
        PublicExamplePlumbingProtocolIntegrityError, match="canonical"
    ):
        load_public_example_plumbing_protocol(
            path, expected_canonical_sha256="0" * 64
        )
