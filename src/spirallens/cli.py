"""Command-line entry points for the auditable SpiralLens v0.1 pipeline."""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Sequence

from spirallens import __version__


OBSERVATION_ONLY_NEIGHBOR_AUDIT_PROTOCOL_SCHEMA_VERSION = (
    "spirallens.neighbor-audit-protocol.v0.3"
)
QUALIFIED_NEIGHBOR_AUDIT_PROTOCOL_SCHEMA_VERSIONS = {
    OBSERVATION_ONLY_NEIGHBOR_AUDIT_PROTOCOL_SCHEMA_VERSION,
    "spirallens.neighbor-audit-protocol.v0.4",
}
ACTIVE_FAISS_PREFLIGHT_PROTOCOL_SCHEMA_VERSION = (
    "spirallens.neighbor-audit-protocol.v0.4"
)
ACTIVE_FAISS_QUALIFICATION_SCHEMA_VERSION = (
    "spirallens.faiss-hnsw-range-qualification.v0.2"
)
ACTIVE_FAISS_QUALIFICATION_PATH = (
    "protocols/"
    "pythia70_slot_only_001_layer0_faiss_range_qualification_v0_2.json"
)


def _write_json_atomic(
    path: Path,
    payload: dict[str, Any],
    *,
    overwrite: bool,
) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"refusing to overwrite {path}; pass --overwrite explicitly"
        )
    encoded = json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    )
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _print_json(payload: dict[str, Any]) -> None:
    print(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
    )


def _load_yaml_mapping(path: Path, *, label: str) -> tuple[bytes, dict[str, Any]]:
    import yaml

    class _UniqueKeyLoader(yaml.SafeLoader):
        pass

    def construct_mapping(
        loader: _UniqueKeyLoader,
        node: Any,
        deep: bool = False,
    ) -> dict[Any, Any]:
        mapping: dict[Any, Any] = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            try:
                duplicate = key in mapping
            except TypeError as error:
                raise ValueError(
                    f"{label} contains an invalid mapping key"
                ) from error
            if duplicate:
                raise ValueError(
                    f"{label} contains duplicate key {key!r}"
                )
            mapping[key] = loader.construct_object(
                value_node,
                deep=deep,
            )
        return mapping

    _UniqueKeyLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping,
    )
    source = path.resolve()
    payload_bytes = source.read_bytes()
    try:
        payload = yaml.load(payload_bytes, Loader=_UniqueKeyLoader)
    except yaml.YAMLError as error:
        raise ValueError(f"{label} is invalid YAML") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a YAML mapping")
    return payload_bytes, payload


def _faiss_config_from_neighbor_protocol(
    document: dict[str, Any],
) -> Any:
    from spirallens.neighbors import (
        FAISS_HNSW_BACKEND_ID,
        FaissHNSWConfig,
    )

    subject = document.get("subject_backend")
    schema_version = document.get("schema_version")
    expected_backend_version = {
        "spirallens.neighbor-audit-protocol.v0.2": "0.1",
        "spirallens.neighbor-audit-protocol.v0.3": "0.2",
        "spirallens.neighbor-audit-protocol.v0.4": "0.2",
    }.get(schema_version)
    if (
        expected_backend_version is None
        or not isinstance(subject, dict)
        or subject.get("backend_id") != FAISS_HNSW_BACKEND_ID
        or str(subject.get("backend_version"))
        != expected_backend_version
        or subject.get("distribution") != "faiss-cpu"
        or str(subject.get("distribution_version")) != "1.14.3"
        or not isinstance(subject.get("config"), dict)
    ):
        raise ValueError(
            "neighbor protocol does not select a supported Faiss HNSW "
            "backend"
        )
    config = FaissHNSWConfig(**subject["config"])
    if (
        expected_backend_version == "0.1"
        and config.range_call_batch_size is not None
    ) or (
        expected_backend_version == "0.2"
        and config.range_call_batch_size != 1
    ):
        raise ValueError(
            "neighbor protocol backend version and native range-call "
            "batch contract differ"
        )
    return config


def _candidate_config_from_protocol_document(
    document: dict[str, Any],
) -> Any:
    from spirallens.metrics import CandidateSearchConfig

    search = document.get("candidate_search")
    if not isinstance(search, dict):
        raise ValueError(
            "protocol is missing a candidate_search mapping"
        )
    allowed = set(CandidateSearchConfig.__dataclass_fields__)
    unknown = set(search) - allowed
    if unknown:
        raise ValueError(
            f"unknown candidate_search fields: {sorted(unknown)}"
        )
    values = dict(search)
    if values.get("layer_indices") is not None:
        values["layer_indices"] = tuple(values["layer_indices"])
    return CandidateSearchConfig(**values)


def _resolve_protocol_reference(
    protocol_path: Path,
    declared_path: object,
) -> Path:
    if not isinstance(declared_path, str) or not declared_path:
        raise ValueError("protocol reference path is invalid")
    reference = Path(declared_path)
    candidates = (
        reference.resolve()
        if reference.is_absolute()
        else (protocol_path.parent / reference).resolve(),
        (protocol_path.parent.parent / reference).resolve(),
    )
    existing = tuple(
        dict.fromkeys(path for path in candidates if path.is_file())
    )
    if len(existing) != 1:
        raise ValueError(
            f"protocol reference does not resolve uniquely: {declared_path}"
        )
    return existing[0]


def _neighbor_audit_config_from_protocol(
    document: dict[str, Any],
) -> Any:
    from spirallens.metrics import NeighborAuditConfig
    from spirallens.metrics.neighbor_audit import (
        LOCAL_RECALL_CONTRACT_VERSION,
    )

    audit = document.get("audit")
    if not isinstance(audit, dict):
        raise ValueError("neighbor protocol lacks audit settings")
    config_fields = {
        "candidate_boundary_recall_min",
        "query_local_recall_min",
        "stratum_recall_min",
        "repeats",
        "minimum_reference_candidates",
        "minimum_eligible_queries",
        "minimum_eligible_query_fraction",
        "density_strata_count",
        "minimum_eligible_queries_per_density_stratum",
        "boundary_shell_width",
        "minimum_reference_candidates_per_stratum",
        "missing_pair_sample_limit",
    }
    policy_fields = {
        "primary_metric",
        "repeat_mode",
        "zero_reference_candidates",
        "top_k_recall_role",
        "pooled_recall_can_override_failed_group",
        "required_local_recall_contract",
        "required_joint_strata",
        "issue_persistence_receipt_on_verified_pass",
        "protocol_binding_required",
        "source_identity_required",
    }
    if set(audit) != config_fields | policy_fields:
        raise ValueError(
            "neighbor protocol audit fields differ from v0.2 schema"
        )
    if (
        audit["primary_metric"] != "candidate_boundary_recall"
        or audit["repeat_mode"] != "independent_cold_rebuild"
        or audit["zero_reference_candidates"] != "insufficient"
        or audit["top_k_recall_role"]
        != "not_applicable_range_search"
        or audit["pooled_recall_can_override_failed_group"] is not False
        or audit["required_local_recall_contract"]
        != LOCAL_RECALL_CONTRACT_VERSION
        or audit["required_joint_strata"]
        != "density_rank_x_cosine_boundary"
        or audit["protocol_binding_required"] is not True
        or audit["source_identity_required"] is not True
    ):
        raise ValueError(
            "neighbor protocol audit methodology is invalid"
        )
    return NeighborAuditConfig(
        candidate_recall_min=audit[
            "candidate_boundary_recall_min"
        ],
        query_local_recall_min=audit["query_local_recall_min"],
        stratum_recall_min=audit["stratum_recall_min"],
        repeats=audit["repeats"],
        minimum_reference_candidates=audit[
            "minimum_reference_candidates"
        ],
        minimum_eligible_queries=audit[
            "minimum_eligible_queries"
        ],
        minimum_eligible_query_fraction=audit[
            "minimum_eligible_query_fraction"
        ],
        density_strata_count=audit["density_strata_count"],
        minimum_eligible_queries_per_density_stratum=audit[
            "minimum_eligible_queries_per_density_stratum"
        ],
        boundary_shell_width=audit["boundary_shell_width"],
        minimum_reference_candidates_per_stratum=audit[
            "minimum_reference_candidates_per_stratum"
        ],
        missing_pair_sample_limit=audit[
            "missing_pair_sample_limit"
        ],
    )


def _validate_recall_gate_contract(
    *,
    protocol_path: Path,
    document: dict[str, Any],
    audit_config: Any,
) -> tuple[Path, bytes, dict[str, Any]]:
    from spirallens.metrics.neighbor_receipt import (
        validate_recall_gate_contract,
    )

    gate_path, gate_bytes, gate = validate_recall_gate_contract(
        audit_config=audit_config,
        protocol_path=protocol_path,
        protocol=document,
    )
    return gate_path, gate_bytes, dict(gate)


def _neighbor_audit_exit_code(
    *,
    protocol_status: str,
    audit_status: str,
    promotion_eligible: bool,
) -> int:
    if audit_status != "pass":
        return 2
    if protocol_status == "frozen" and not promotion_eligible:
        return 2
    return 0


def _run_faiss_range_preflight(args: argparse.Namespace) -> int:
    """Qualify the versioned native range-call path without subject data."""

    import numpy as np

    from spirallens.metrics.neighbor_receipt import (
        _candidate_config_from_bytes,
        validate_neighbor_protocol_static_contract,
    )
    from spirallens.neighbors.faiss_qualification import (
        run_faiss_hnsw_qualification,
    )

    repo_root = Path(__file__).resolve().parents[2]
    expected_protocol_path = (
        repo_root / "protocols" / "pythia_neighbor_v0_4.yaml"
    )
    protocol_path = args.protocol.resolve()
    protocol_bytes, protocol = _load_yaml_mapping(
        protocol_path,
        label="Faiss range preflight protocol",
    )
    protocol_sha256 = hashlib.sha256(protocol_bytes).hexdigest()
    if protocol_sha256 != args.expected_protocol_sha256:
        raise ValueError(
            "preflight protocol does not match "
            "--expected-protocol-sha256"
        )
    validate_neighbor_protocol_static_contract(protocol)
    if (
        protocol.get("schema_version")
        != ACTIVE_FAISS_PREFLIGHT_PROTOCOL_SCHEMA_VERSION
        or protocol.get("status") != "preregistered-draft"
    ):
        raise ValueError(
            "Faiss range preflight requires the v0.4 preregistered "
            "draft protocol"
        )
    if protocol_path != expected_protocol_path:
        raise ValueError(
            "Faiss range preflight requires the canonical tracked v0.4 "
            "protocol path"
        )
    qualification_binding = protocol.get("backend_qualification")
    if (
        not isinstance(qualification_binding, dict)
        or qualification_binding.get("schema_version")
        != ACTIVE_FAISS_QUALIFICATION_SCHEMA_VERSION
        or qualification_binding.get("path")
        != ACTIVE_FAISS_QUALIFICATION_PATH
    ):
        raise ValueError(
            "Faiss range preflight qualification identity differs from "
            "the v0.4 contract"
        )
    expected_output_path = Path(
        os.path.abspath(repo_root / ACTIVE_FAISS_QUALIFICATION_PATH)
    )
    output_path = Path(os.path.abspath(args.output))
    if output_path != expected_output_path:
        raise ValueError(
            "Faiss range preflight output must equal the v0.4 "
            "qualification path"
        )
    faiss_config = _faiss_config_from_neighbor_protocol(protocol)
    expected_faiss_config = {
        "m": 32,
        "ef_construction": 200,
        "ef_search": 256,
        "seed": 1729,
        "thread_count": 1,
        "query_batch_size": 512,
        "range_call_batch_size": 1,
        "score_margin": 0.0001,
        "max_raw_hits": 20_000_000,
        "max_proposed_pairs": 10_000_000,
    }
    if faiss_config.to_dict() != expected_faiss_config:
        raise ValueError(
            "Faiss range preflight protocol config differs from the "
            "fixed production-shape qualification"
        )
    candidate_binding = protocol.get("candidate_protocol")
    if not isinstance(candidate_binding, dict):
        raise ValueError(
            "Faiss range preflight protocol lacks candidate binding"
        )
    candidate_path = _resolve_protocol_reference(
        protocol_path,
        candidate_binding.get("path"),
    )
    candidate_bytes = candidate_path.read_bytes()
    if (
        hashlib.sha256(candidate_bytes).hexdigest()
        != candidate_binding.get("sha256")
    ):
        raise ValueError(
            "Faiss range preflight candidate binding differs"
        )
    _, candidate_config = _candidate_config_from_bytes(
        candidate_bytes,
        layer_index=0,
        require_frozen=False,
    )
    radius = float(
        np.nextafter(
            np.float32(
                max(
                    -1.0,
                    candidate_config.cosine_min
                    - faiss_config.score_margin,
                )
            ),
            np.float32(-np.inf),
        )
    )
    expected_radius = float(
        np.nextafter(
            np.float32(0.9949),
            np.float32(-np.inf),
        )
    )
    if radius != expected_radius:
        raise ValueError(
            "Faiss range preflight radius differs from the fixed "
            "qualification"
        )
    receipt = run_faiss_hnsw_qualification(output_path)
    receipt_payload = receipt.to_dict()
    if (
        receipt_payload.get("schema_version")
        != ACTIVE_FAISS_QUALIFICATION_SCHEMA_VERSION
    ):
        raise ValueError(
            "Faiss range preflight receipt schema differs from the "
            "v0.4 protocol"
        )
    expected_search = {
        "m": faiss_config.m,
        "ef_construction": faiss_config.ef_construction,
        "ef_search": faiss_config.ef_search,
        "seed": faiss_config.seed,
        "thread_count": faiss_config.thread_count,
        "query_batch_size": faiss_config.query_batch_size,
        "range_call_batch_size": faiss_config.range_call_batch_size,
        "cosine_min": candidate_config.cosine_min,
        "score_margin": faiss_config.score_margin,
        "radius": radius,
        "max_native_call_hits": 50_304,
        "max_raw_hits": faiss_config.max_raw_hits,
    }
    if dict(receipt.search) != expected_search:
        raise ValueError(
            "Faiss range qualification search contract differs from "
            "the protocol"
        )
    if protocol_path.read_bytes() != protocol_bytes:
        raise ValueError(
            "Faiss range preflight protocol changed during execution"
        )
    if candidate_path.read_bytes() != candidate_bytes:
        raise ValueError(
            "Faiss range preflight candidate changed during execution"
        )
    _print_json(
        {
            "command": "faiss-range-preflight",
            "status": receipt.status,
            "protocol_sha256": protocol_sha256,
            "receipt": str(output_path),
            "receipt_sha256": receipt.sha256,
            "fixture_sha256": receipt.fixture_sha256,
            "backend_version": receipt.backend_version,
            "cold_process_runs": len(receipt.cold_process_runs),
            "implementation_commit": receipt.implementation_commit,
            "spirallens_package_tree": (
                receipt.spirallens_package_tree
            ),
        }
    )
    return 0


def _calibration_payload(report: Any, *, samples: int) -> dict[str, Any]:
    checks = [
        {
            "name": check.name,
            "category": check.category,
            "observed": check.observed,
            "expected": check.expected,
            "tolerance": check.tolerance,
            "absolute_error": check.absolute_error,
            "passed": check.passed,
            "details": dict(check.details),
        }
        for check in report.checks
    ]
    return {
        "schema_version": "spirallens.calibration-report.v0.1",
        "suite_name": report.suite_name,
        "samples": samples,
        "status": "passed" if report.passed else "failed",
        "summary": {
            "checks": len(checks),
            "passed": sum(check["passed"] for check in checks),
            "failed": len(report.failed),
        },
        "checks": checks,
    }


def _run_calibrate(args: argparse.Namespace) -> int:
    from spirallens.calibration import run_analytic_calibration

    report = run_analytic_calibration(samples=args.samples)
    payload = _calibration_payload(report, samples=args.samples)
    output = None
    if args.output is not None:
        output = args.output.resolve()
        _write_json_atomic(output, payload, overwrite=args.overwrite)
    _print_json(
        {
            "command": "calibrate",
            "status": payload["status"],
            **payload["summary"],
            "report": str(output) if output is not None else None,
        }
    )
    return 0 if report.passed else 1


def _automatic_device(torch: Any) -> str:
    if torch.cuda.is_available():
        return "cuda"
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return "mps"
    return "cpu"


def _run_atlas(args: argparse.Namespace) -> int:
    import torch

    from spirallens.adapters import PythiaAdapter
    from spirallens.atlas import ContextBankBinding, SweepConfig, run_id_sweep
    from spirallens.contexts import load_context_bank

    if args.full_vocabulary and (
        args.subset is not None or args.max_tokens is not None
    ):
        raise ValueError(
            "--full-vocabulary cannot be combined with --subset or --max-tokens"
        )
    if (
        not args.full_vocabulary
        and args.subset is None
        and args.max_tokens is None
    ):
        raise ValueError(
            "choose --max-tokens/--subset for a bounded run, or explicitly pass "
            "--full-vocabulary"
        )

    context_binding = None
    if args.context_bank is not None:
        if args.context_ids is not None:
            raise ValueError(
                "--context-bank cannot be combined with --context-ids"
            )
        if args.position is not None or args.sweep_position is not None:
            raise ValueError(
                "bank-bound positions come from ContextSpec; do not pass "
                "--position or --sweep-position"
            )
        if args.attention_mask is not None:
            raise ValueError(
                "bank-bound attention masks come from ContextSpec"
            )
        if args.context_id is None or not args.allow_role:
            raise ValueError(
                "--context-bank requires --context-id and explicit --allow-role"
            )
        loaded = load_context_bank(
            args.context_bank,
            allowed_roles=set(args.allow_role),
            expected_source_sha256=(
                args.expected_context_bank_source_sha256
            ),
            expected_canonical_sha256=(
                args.expected_context_bank_canonical_sha256
            ),
        )
        context_binding = ContextBankBinding(
            loaded=loaded,
            context_id=args.context_id,
            role=loaded.bank.role,
        )
        context_ids = context_binding.materialized_context_ids
        position = context_binding.context.observation_position
        attention_mask = None
        sweep_position = None
        model_id = loaded.bank.model.model_id
        revision = loaded.bank.model.resolved_revision
        if args.model is not None and args.model != model_id:
            raise ValueError("--model does not match the bound context bank")
        if args.revision is not None and args.revision != revision:
            raise ValueError("--revision does not match the bound context bank")
    else:
        bank_only_values = (
            args.context_id,
            args.allow_role,
            args.expected_context_bank_source_sha256,
            args.expected_context_bank_canonical_sha256,
        )
        if any(value is not None for value in bank_only_values):
            raise ValueError(
                "context-bank selection options require --context-bank"
            )
        if args.context_ids is None or args.position is None:
            raise ValueError(
                "raw atlas capture requires --context-ids and --position"
            )
        context_ids = tuple(args.context_ids)
        position = args.position
        attention_mask = (
            None
            if args.attention_mask is None
            else tuple(args.attention_mask)
        )
        sweep_position = args.sweep_position
        model_id = args.model or "EleutherAI/pythia-70m"
        revision = args.revision

    device = _automatic_device(torch) if args.device == "auto" else args.device
    model_kwargs: dict[str, Any] = {}
    if args.dtype != "auto":
        model_kwargs["torch_dtype"] = {
            "float32": torch.float32,
            "float16": torch.float16,
            "bfloat16": torch.bfloat16,
        }[args.dtype]

    adapter = PythiaAdapter.from_pretrained(
        model_id,
        revision=revision,
        device=device,
        local_files_only=args.local_files_only,
        **model_kwargs,
    )
    manifest = run_id_sweep(
        adapter,
        SweepConfig(
            output_dir=args.output,
            context_ids=context_ids,
            position=position,
            batch_size=args.batch_size,
            subset=None if args.subset is None else tuple(args.subset),
            max_tokens=args.max_tokens,
            attention_mask=attention_mask,
            resume=args.resume,
            sweep_position=sweep_position,
            context_bank_binding=context_binding,
        ),
    )
    _print_json(
        {
            "command": "atlas",
            "status": manifest["status"],
            "run_id": manifest["run_id"],
            "model": manifest["model"]["model_id"],
            "device": device,
            "rows": manifest["progress"],
            "context_bank_binding_sha256": manifest["request"].get(
                "context_bank_binding_sha256"
            ),
            "manifest": str((args.output / "manifest.json").resolve()),
        }
    )
    return 0


def _run_context_bank_validate(args: argparse.Namespace) -> int:
    from spirallens.contexts import load_context_bank

    loaded = load_context_bank(
        args.path,
        allowed_roles=set(args.allow_role),
        expected_source_sha256=args.expected_source_sha256,
        expected_canonical_sha256=args.expected_canonical_sha256,
    )
    bank = loaded.bank
    _print_json(
        {
            "command": "context-bank validate",
            "status": "valid",
            "schema_version": bank.to_dict()["schema_version"],
            "bank_id": bank.bank_id,
            "bank_status": bank.status.value,
            "role": bank.role.value,
            "claim_eligible": bank.claim_eligible,
            "contexts": len(bank.contexts),
            "source_path": str(loaded.source_path),
            "source_sha256": loaded.source_sha256,
            "canonical_sha256": loaded.canonical_sha256,
            "model": {
                "id": bank.model.model_id,
                "resolved_revision": bank.model.resolved_revision,
                "vocab_size": bank.model.vocab_size,
            },
            "tokenizer": {
                "id": bank.tokenizer.tokenizer_id,
                "resolved_revision": bank.tokenizer.resolved_revision,
                "addressable_size": bank.tokenizer.addressable_size,
                "provenance_sha256": bank.tokenizer.sha256,
            },
            "sweep_domain": bank.sweep_domain.value,
            "language_space_atlas": False,
            "semantic_unit": False,
        }
    )
    return 0


def _run_hypothesis_registry_validate(args: argparse.Namespace) -> int:
    from spirallens.instrument_contracts.registry_loader import (
        load_hypothesis_registry,
    )

    loaded = load_hypothesis_registry(
        args.path,
        expected_source_sha256=args.expected_source_sha256,
        expected_canonical_sha256=args.expected_canonical_sha256,
    )
    registry = loaded.registry
    _print_json(
        {
            "command": "hypothesis-registry validate",
            "status": "valid",
            "schema_version": registry.schema_version,
            "registry_id": registry.registry_id,
            "hypotheses": len(registry.hypotheses),
            "hypothesis_ids": [
                hypothesis.hypothesis_id.value
                for hypothesis in registry.hypotheses
            ],
            "real_model_claim_state": (
                registry.real_model_claim_state.value
            ),
            "winner_selected": registry.winner_selected,
            "primary_integer_output_authorized": (
                registry.primary_integer_output_authorized
            ),
            "subject_data_access_authorized": (
                registry.subject_data_access_authorized
            ),
            "source_path": str(loaded.source_path),
            "source_sha256": loaded.source_sha256,
            "canonical_sha256": loaded.canonical_sha256,
        }
    )
    return 0


def _run_instrument_artifact_validate(args: argparse.Namespace) -> int:
    from spirallens.instrument_contracts.artifact_loader import (
        load_instrument_artifact,
    )

    loaded = load_instrument_artifact(
        args.path,
        expected_source_sha256=args.expected_source_sha256,
        expected_canonical_sha256=args.expected_canonical_sha256,
    )
    artifact = loaded.artifact
    claim_ceiling = getattr(artifact, "claim_ceiling", None)
    _print_json(
        {
            "command": "instrument-artifact validate",
            "status": "valid",
            "artifact_type": artifact.artifact_type.value,
            "schema_version": artifact.schema_version,
            "artifact_id": artifact.artifact_id,
            "claim_ceiling": (
                None
                if claim_ceiling is None
                else claim_ceiling.value
            ),
            "source_path": str(loaded.source_path),
            "source_sha256": loaded.source_sha256,
            "canonical_sha256": loaded.canonical_sha256,
            "payloads_dereferenced": False,
            "subject_data_accessed": False,
            "validation_scope": "single_manifest",
            "references_resolved": False,
            "bundle_validated": False,
        }
    )
    return 0


def _run_instrument_bundle_validate(args: argparse.Namespace) -> int:
    from spirallens.instrument_contracts.bundle_loader import (
        load_instrument_bundle,
    )

    loaded = load_instrument_bundle(
        args.path,
        expected_source_sha256=args.expected_source_sha256,
        expected_canonical_sha256=args.expected_canonical_sha256,
    )
    _print_json(
        {
            "command": "instrument-bundle validate",
            "status": "valid",
            "validation_scope": "closed_integrity_bundle",
            "schema_version": loaded.manifest.schema_version,
            "bundle_id": loaded.manifest.bundle_id,
            "source_path": str(loaded.source_path),
            "source_sha256": loaded.source_sha256,
            "canonical_sha256": loaded.canonical_sha256,
            "root_artifacts": len(loaded.manifest.roots),
            "artifact_entries": len(loaded.artifacts),
            "payload_entries": len(loaded.payloads),
            "artifact_reference_count": loaded.artifact_reference_count,
            "payload_reference_count": loaded.payload_reference_count,
            "cross_manifest_join_count": (
                loaded.cross_manifest_join_count
            ),
            "bundle_integrity_validated": True,
            "artifact_references_resolved": True,
            "payload_references_resolved": True,
            "payload_bytes_read_for_integrity": bool(loaded.payloads),
            "payload_content_decoded": False,
            "row_identity_content_recomputed": False,
            "dependency_graph_acyclic": True,
            "unreferenced_entries": 0,
            "cross_manifest_metadata_joins_validated": True,
            "context_role_fit_role_mapping_validated": False,
            "cell_completeness_validated": False,
            "d0_d8_qualified": False,
            "scientific_bundle_qualified": False,
            "model_loaded": False,
            "estimator_executed": False,
            "graph_constructed": False,
            "subject_roles_allowed": False,
            "subject_data_accessed": False,
            "subject_execution_performed": False,
        }
    )
    return 0


def _run_synthetic_bundle_generate(args: argparse.Namespace) -> int:
    from spirallens.synthetic import emit_representation_phantom_bundle

    emitted = emit_representation_phantom_bundle(
        protocol_path=args.protocol,
        output_dir=args.output_dir,
    )
    _print_json(emitted.to_dict())
    return 0


def _run_candidates(args: argparse.Namespace) -> int:
    from spirallens.metrics import (
        CandidateSearchConfig,
        extract_candidates_from_manifest,
        load_neighbor_audit_receipt,
    )

    if args.output.exists() and not args.overwrite:
        raise FileExistsError(
            f"refusing to overwrite {args.output.resolve()}; "
            "pass --overwrite explicitly"
        )

    protocol_binding: dict[str, Any]
    if args.protocol is not None:
        import yaml

        protocol_path = args.protocol.resolve()
        protocol_bytes = protocol_path.read_bytes()
        protocol_document = yaml.safe_load(protocol_bytes)
        if not isinstance(protocol_document, dict):
            raise ValueError("protocol must contain a YAML mapping")
        declared_id = protocol_document.get("protocol_id")
        declared_status = protocol_document.get("status")
        declared_ceiling = protocol_document.get("claim_ceiling")
        if not isinstance(declared_id, str) or not declared_id:
            raise ValueError("protocol.protocol_id must be a non-empty string")
        if not isinstance(declared_status, str) or not declared_status:
            raise ValueError("protocol.status must be a non-empty string")
        if (
            isinstance(declared_ceiling, bool)
            or not isinstance(declared_ceiling, int)
            or not 1 <= declared_ceiling <= 3
        ):
            raise ValueError("protocol.claim_ceiling must be an integer in [1, 3]")
        if args.protocol_id is not None and args.protocol_id != declared_id:
            raise ValueError(
                f"--protocol-id {args.protocol_id!r} does not match "
                f"protocol declaration {declared_id!r}"
            )
        protocol_id = declared_id
        protocol_claim_ceiling = declared_ceiling
        config = _candidate_config_from_protocol_document(
            protocol_document
        )
        if protocol_path.read_bytes() != protocol_bytes:
            raise RuntimeError("protocol changed while it was being bound")
        protocol_binding = {
            "declared_id": declared_id,
            "declared_status": declared_status,
            "claim_ceiling": declared_ceiling,
            "path": str(protocol_path),
            "sha256": hashlib.sha256(protocol_bytes).hexdigest(),
        }
    else:
        protocol_id = args.protocol_id or "ad-hoc-v0.1"
        protocol_claim_ceiling = 1
        config = CandidateSearchConfig()
        protocol_binding = {
            "declared_id": protocol_id,
            "declared_status": "exploratory_ad_hoc",
            "claim_ceiling": 1,
            "path": None,
            "sha256": None,
        }
    overrides: dict[str, Any] = {}
    for name in (
        "cosine_min",
        "relative_norm_gap_max",
        "drift_relative_divergence_min",
        "drift_absolute_divergence_min",
        "min_state_norm",
        "min_drift_norm",
        "block_size",
        "max_pairwise_rows",
    ):
        value = getattr(args, name)
        if value is not None:
            overrides[name] = value
    if args.layers is not None:
        overrides["layer_indices"] = tuple(args.layers)
    if overrides:
        config = replace(config, **overrides)
    protocol_binding["candidate_search_overrides"] = {
        key: list(value) if isinstance(value, tuple) else value
        for key, value in overrides.items()
    }
    protocol_binding["execution_status"] = (
        "exploratory_override"
        if overrides
        else protocol_binding["declared_status"]
    )
    protocol_binding["deviates_from_declared_search"] = bool(overrides)

    neighbor_backend_factory = None
    neighbor_audit_receipts = None
    if args.neighbor_backend == "faiss-hnsw":
        if (
            args.neighbor_audit is None
            or args.neighbor_audit_protocol is None
            or args.expected_audit_sha256 is None
            or args.expected_neighbor_protocol_sha256 is None
        ):
            raise ValueError(
                "--neighbor-backend faiss-hnsw requires "
                "--neighbor-audit, --neighbor-audit-protocol, "
                "--expected-audit-sha256, and "
                "--expected-neighbor-protocol-sha256"
            )
        if args.protocol is None:
            raise ValueError(
                "receipt-authorized Faiss extraction requires "
                "--protocol"
            )
        if args.skip_checksums:
            raise ValueError(
                "receipt-authorized Faiss extraction cannot skip "
                "atlas checksums"
            )
        if args.overwrite:
            raise ValueError(
                "receipt-authorized approximate ledgers cannot overwrite"
            )
        if config.layer_indices is None or len(config.layer_indices) != 1:
            raise ValueError(
                "Faiss candidate extraction requires exactly one --layers "
                "value"
            )
        neighbor_protocol_bytes, neighbor_document = _load_yaml_mapping(
            args.neighbor_audit_protocol,
            label="neighbor audit protocol",
        )
        if hashlib.sha256(neighbor_protocol_bytes).hexdigest() != (
            args.expected_neighbor_protocol_sha256
        ):
            raise ValueError(
                "neighbor protocol does not match "
                "--expected-neighbor-protocol-sha256"
            )
        if neighbor_document.get("schema_version") == (
            OBSERVATION_ONLY_NEIGHBOR_AUDIT_PROTOCOL_SCHEMA_VERSION
        ):
            raise ValueError(
                "neighbor protocol v0.3 is observation-only and cannot "
                "authorize candidate persistence; use v0.4"
            )
        faiss_config = _faiss_config_from_neighbor_protocol(
            neighbor_document
        )
        qualification_receipt = None
        if neighbor_document.get("schema_version") in (
            QUALIFIED_NEIGHBOR_AUDIT_PROTOCOL_SCHEMA_VERSIONS
        ):
            from spirallens.neighbors.faiss_qualification import (
                load_faiss_hnsw_qualification_receipt,
            )

            qualification_binding = neighbor_document.get(
                "backend_qualification"
            )
            if not isinstance(qualification_binding, dict):
                raise ValueError(
                    "qualified neighbor protocol lacks its preflight "
                    "receipt binding"
                )
            qualification_path = _resolve_protocol_reference(
                args.neighbor_audit_protocol.resolve(),
                qualification_binding.get("path"),
            )
            qualification_receipt = (
                load_faiss_hnsw_qualification_receipt(
                    qualification_path,
                    expected_sha256=qualification_binding.get("sha256"),
                )
            )
            if (
                qualification_receipt.fixture_sha256
                != qualification_binding.get("fixture_sha256")
            ):
                raise ValueError(
                    "qualified neighbor protocol fixture binding differs"
                )
        receipt = load_neighbor_audit_receipt(
            args.neighbor_audit,
            protocol_path=args.neighbor_audit_protocol,
            expected_audit_sha256=args.expected_audit_sha256,
            expected_protocol_sha256=(
                args.expected_neighbor_protocol_sha256
            ),
        )
        if (
            receipt.protocol_source_sha256
            != args.expected_neighbor_protocol_sha256
            or args.neighbor_audit_protocol.resolve().read_bytes()
            != neighbor_protocol_bytes
        ):
            raise ValueError(
                "neighbor protocol changed during receipt validation"
            )
        group_key = f"layer_index={config.layer_indices[0]}"
        if receipt.comparison_group != group_key:
            raise ValueError(
                "neighbor audit receipt group differs from --layers"
            )
        from spirallens.neighbors import FaissHNSWBackend

        def build_neighbor_backend(
            snapshot: Any,
            row_sha: str,
            group: str,
        ) -> FaissHNSWBackend:
            return FaissHNSWBackend(
                snapshot,
                row_identity_sha256=row_sha,
                comparison_group=group,
                config=faiss_config,
                worker_runtime_contract=dict(
                    receipt.subject_backend.runtime
                ),
                qualification_receipt=qualification_receipt,
            )

        neighbor_backend_factory = build_neighbor_backend
        neighbor_audit_receipts = {group_key: receipt}
    elif (
        args.neighbor_audit is not None
        or args.neighbor_audit_protocol is not None
        or args.expected_audit_sha256 is not None
        or args.expected_neighbor_protocol_sha256 is not None
    ):
        raise ValueError(
            "neighbor audit flags require --neighbor-backend faiss-hnsw"
        )

    summary = extract_candidates_from_manifest(
        args.manifest,
        args.output,
        config=config,
        protocol_id=protocol_id,
        verify_checksums=not args.skip_checksums,
        overwrite=args.overwrite,
        protocol_claim_ceiling=protocol_claim_ceiling,
        protocol_binding=protocol_binding,
        neighbor_backend_factory=neighbor_backend_factory,
        neighbor_audit_receipts=neighbor_audit_receipts,
    )
    _print_json(
        {
            "command": "candidates",
            "status": "complete",
            "candidate_count": summary.candidate_count,
            "ledger": str(summary.output_path.resolve()),
            "protocol_id": protocol_id,
            "execution_status": protocol_binding["execution_status"],
            "neighbor_backend": args.neighbor_backend,
        }
    )
    return 0


def _run_neighbor_audit(args: argparse.Namespace) -> int:
    from spirallens.atlas import load_manifest
    from spirallens.audit_output import reserve_audit_output
    from spirallens.execution_freeze import (
        validate_subject_audit_execution_freeze,
    )
    from spirallens.metrics import (
        NeighborAuditProtocolBinding,
        NeighborQuerySelectionContract,
        atlas_global_row_key_sha256,
        load_neighbor_audit_receipt,
        write_neighbor_audit,
    )
    from spirallens.metrics.candidate_pairs import (
        _audit_neighbor_backend_from_manifest,
        _load_manifest_array,
        _validate_neighbor_audit_atlas_scope,
    )
    from spirallens.metrics.neighbor_receipt import (
        _candidate_config_from_bytes,
        validate_neighbor_protocol_static_contract,
    )
    from spirallens.neighbors import FaissHNSWBackend, canonical_json_sha256

    protocol_path = args.protocol.resolve()
    protocol_bytes, document = _load_yaml_mapping(
        protocol_path,
        label="neighbor audit protocol",
    )
    protocol_sha256 = hashlib.sha256(protocol_bytes).hexdigest()
    if (
        args.expected_protocol_sha256 is not None
        and args.expected_protocol_sha256 != protocol_sha256
    ):
        raise ValueError(
            "neighbor protocol does not match --expected-protocol-sha256"
        )
    protocol_id = document.get("protocol_id")
    protocol_status = document.get("status")
    protocol_schema_version = document.get("schema_version")
    qualified_protocol = protocol_schema_version in (
        QUALIFIED_NEIGHBOR_AUDIT_PROTOCOL_SCHEMA_VERSIONS
    )
    if (
        protocol_schema_version
        not in {
            "spirallens.neighbor-audit-protocol.v0.2",
            *QUALIFIED_NEIGHBOR_AUDIT_PROTOCOL_SCHEMA_VERSIONS,
        }
        or not isinstance(protocol_id, str)
        or protocol_status not in {"preregistered-draft", "frozen"}
    ):
        raise ValueError("neighbor audit protocol identity is invalid")
    validate_neighbor_protocol_static_contract(document)
    if protocol_schema_version == (
        OBSERVATION_ONLY_NEIGHBOR_AUDIT_PROTOCOL_SCHEMA_VERSION
    ) and (protocol_status == "frozen" or not args.prepare_only):
        raise ValueError(
            "neighbor protocol v0.3 is observation-only and cannot "
            "authorize a subject audit; use v0.4"
        )
    if protocol_status != "frozen" and not args.prepare_only:
        raise ValueError(
            "subject neighbor audits require a frozen protocol; "
            "draft protocols are prepare-only"
        )
    if (
        protocol_status == "frozen"
        and args.expected_protocol_sha256 is None
    ):
        raise ValueError(
            "frozen audits require --expected-protocol-sha256"
        )
    if protocol_status == "frozen" and args.skip_checksums:
        raise ValueError(
            "frozen neighbor audits cannot skip atlas checksums"
        )
    if protocol_status == "frozen" and args.overwrite:
        raise ValueError(
            "frozen neighbor audits cannot overwrite an audit artifact"
        )
    if not args.prepare_only and (
        args.execution_freeze is None
        or args.expected_execution_freeze_sha256 is None
    ):
        raise ValueError(
            "subject neighbor audits require --execution-freeze and "
            "--expected-execution-freeze-sha256"
        )
    candidate_binding = document.get("candidate_protocol")
    if not isinstance(candidate_binding, dict):
        raise ValueError("neighbor protocol lacks candidate_protocol")
    candidate_path = _resolve_protocol_reference(
        protocol_path,
        candidate_binding.get("path"),
    )
    candidate_bytes = candidate_path.read_bytes()
    if hashlib.sha256(candidate_bytes).hexdigest() != candidate_binding.get(
        "sha256"
    ):
        raise ValueError(
            "candidate protocol bytes differ from neighbor protocol binding"
        )
    candidate_document, candidate_config = (
        _candidate_config_from_bytes(
            candidate_bytes,
            layer_index=args.layer,
            require_frozen=protocol_status == "frozen",
        )
    )
    if (
        candidate_binding.get("declared_id")
        != candidate_document.get("protocol_id")
    ):
        raise ValueError(
            "candidate protocol ID differs from neighbor binding"
        )
    audit_config = _neighbor_audit_config_from_protocol(document)
    gate_path, gate_bytes, gate_document = (
        _validate_recall_gate_contract(
            protocol_path=protocol_path,
            document=document,
            audit_config=audit_config,
        )
    )
    audit_values = document["audit"]
    assert isinstance(audit_values, dict)
    readiness = document.get("promotion_readiness")
    expected_readiness_fields = {
        "receipt_mechanism_implemented",
        "full_index_subset_query_audit_implemented",
        "frozen_recall_gate_methodology_available",
        "query_local_worst_case_recall_gate_implemented",
        "atlas_execution_bindings_frozen",
        "tracked_protocol_can_issue_persistence_receipt",
    }
    if qualified_protocol:
        expected_readiness_fields.add(
            "production_shape_subprocess_qualified"
        )
    if (
        not isinstance(readiness, dict)
        or set(readiness) != expected_readiness_fields
        or readiness["receipt_mechanism_implemented"] is not True
        or readiness[
            "full_index_subset_query_audit_implemented"
        ]
        is not True
        or readiness[
            "frozen_recall_gate_methodology_available"
        ]
        is not True
        or readiness[
            "query_local_worst_case_recall_gate_implemented"
        ]
        is not True
        or (
            qualified_protocol
            and protocol_status == "frozen"
            and readiness[
                "production_shape_subprocess_qualified"
            ]
            is not True
        )
    ):
        raise ValueError(
            "neighbor protocol promotion readiness is invalid"
        )
    if protocol_status == "frozen":
        if (
            candidate_document.get("status") != "frozen"
            or readiness["atlas_execution_bindings_frozen"] is not True
            or readiness[
                "tracked_protocol_can_issue_persistence_receipt"
            ]
            is not True
            or audit_values[
                "issue_persistence_receipt_on_verified_pass"
            ]
            is not True
        ):
            raise ValueError(
                "frozen neighbor protocol is not promotion-ready"
            )
    elif (
        readiness["atlas_execution_bindings_frozen"] is not False
        or readiness[
            "tracked_protocol_can_issue_persistence_receipt"
        ]
        is not False
        or audit_values[
            "issue_persistence_receipt_on_verified_pass"
        ]
        is not False
    ):
        raise ValueError(
            "draft neighbor protocol cannot authorize promotion"
        )
    faiss_config = _faiss_config_from_neighbor_protocol(document)
    if (
        faiss_config.score_margin
        != audit_config.boundary_shell_width
    ):
        raise ValueError(
            "boundary_shell_width must equal subject score_margin"
        )
    qualification_receipt = None
    qualification_path = None
    qualification_bytes = None
    if qualified_protocol and protocol_status == "frozen":
        from spirallens.neighbors.faiss_qualification import (
            load_faiss_hnsw_qualification_receipt,
        )

        qualification_binding = document.get(
            "backend_qualification"
        )
        if not isinstance(qualification_binding, dict):
            raise ValueError(
                "frozen neighbor protocol lacks backend qualification"
            )
        qualification_path = _resolve_protocol_reference(
            protocol_path,
            qualification_binding.get("path"),
        )
        qualification_bytes = qualification_path.read_bytes()
        qualification_receipt = (
            load_faiss_hnsw_qualification_receipt(
                qualification_path,
                expected_sha256=qualification_binding.get("sha256"),
            )
        )
        if (
            qualification_receipt.fixture_sha256
            != qualification_binding.get("fixture_sha256")
        ):
            raise ValueError(
                "backend qualification fixture differs from the "
                "frozen neighbor protocol"
            )

    requested_manifest = args.manifest.resolve()
    manifest_path = (
        requested_manifest / "manifest.json"
        if requested_manifest.is_dir()
        else requested_manifest
    )
    manifest_bytes = manifest_path.read_bytes()
    manifest = load_manifest(
        manifest_path.parent,
        verify_checksums=not args.skip_checksums,
    )
    if manifest_path.read_bytes() != manifest_bytes:
        raise ValueError("atlas manifest changed during audit setup")
    request = manifest.get("request")
    model = manifest.get("model")
    run_id = manifest.get("run_id")
    if (
        not isinstance(request, dict)
        or not isinstance(model, dict)
        or not isinstance(run_id, str)
    ):
        raise ValueError("atlas manifest audit provenance is invalid")
    token_ids = _load_manifest_array(
        manifest_path.parent,
        manifest,
        "token_ids",
        verify_checksums=not args.skip_checksums,
    )
    _validate_neighbor_audit_atlas_scope(
        manifest=manifest,
        token_ids=token_ids,
        layer_index=args.layer,
    )
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    row_identity_sha256 = atlas_global_row_key_sha256(
        token_ids=token_ids,
        request=request,
    )
    sampling = document.get("query_sampling")
    if (
        not isinstance(sampling, dict)
        or sampling.get("method")
        != "sha256_ranked_global_indices"
    ):
        raise ValueError("neighbor protocol query_sampling is invalid")
    declared_row_identity = sampling.get("global_row_key_sha256")
    if (
        declared_row_identity is not None
        and declared_row_identity != row_identity_sha256
    ):
        raise ValueError(
            "neighbor protocol row identity differs from atlas"
        )
    if protocol_status == "frozen" and (
        declared_row_identity != row_identity_sha256
    ):
        raise ValueError(
            "frozen neighbor protocol must bind global_row_key_sha256"
        )
    selection = NeighborQuerySelectionContract(
        seed=sampling.get("seed"),
        count=sampling.get("count"),
        global_row_key_sha256=row_identity_sha256,
    )
    selection.select(int(token_ids.shape[0]))
    group_key = f"layer_index={args.layer}"
    audit_scope = document.get("audit_scope")
    declared_group = (
        audit_scope.get("comparison_group")
        if isinstance(audit_scope, dict)
        else None
    )
    if declared_group is not None and declared_group != group_key:
        raise ValueError(
            "neighbor protocol comparison_group differs from --layer"
        )
    if protocol_status == "frozen" and declared_group != group_key:
        raise ValueError(
            "frozen neighbor protocol must bind comparison_group"
        )
    deviations = document.get("deviations", [])
    if (
        not isinstance(deviations, list)
        or any(
            not isinstance(value, str) or not value
            for value in deviations
        )
    ):
        raise ValueError("neighbor protocol deviations are invalid")
    if args.prepare_only:
        if protocol_path.read_bytes() != protocol_bytes:
            raise ValueError(
                "neighbor protocol changed during binding preparation"
            )
        if candidate_path.read_bytes() != candidate_bytes:
            raise ValueError(
                "candidate protocol changed during binding preparation"
            )
        if gate_path.read_bytes() != gate_bytes:
            raise ValueError(
                "recall gate contract changed during binding preparation"
            )
        if (
            qualification_path is not None
            and qualification_path.read_bytes()
            != qualification_bytes
        ):
            raise ValueError(
                "backend qualification changed during binding preparation"
            )
        _print_json(
            {
                "command": "neighbor-audit",
                "mode": "prepare-only",
                "status": "bindings-ready",
                "atlas_manifest_sha256": manifest_sha256,
                "atlas_run_id": run_id,
                "global_row_key_sha256": row_identity_sha256,
                "comparison_group": group_key,
                "neighbor_protocol_sha256": protocol_sha256,
                "candidate_protocol_sha256": hashlib.sha256(
                    candidate_bytes
                ).hexdigest(),
                "recall_gate_id": gate_document["gate_id"],
                "recall_gate_sha256": hashlib.sha256(
                    gate_bytes
                ).hexdigest(),
                "local_recall_contract": gate_document[
                    "local_recall_contract"
                ],
                "audit_config": audit_config.to_dict(),
                "audit_config_sha256": audit_config.sha256,
                "query_selection_sha256": selection.sha256,
                "promotion_policy_declared": audit_values.get(
                    "issue_persistence_receipt_on_verified_pass"
                ),
                "backend_qualification_sha256": (
                    None
                    if qualification_receipt is None
                    else qualification_receipt.sha256
                ),
                "backend_qualification_fixture_sha256": (
                    None
                    if qualification_receipt is None
                    else qualification_receipt.fixture_sha256
                ),
            }
        )
        return 0
    if args.output is None:
        raise ValueError(
            "--output is required unless --prepare-only is used"
        )
    requested_output_path = Path(os.path.abspath(args.output))
    assert args.execution_freeze is not None
    assert args.expected_execution_freeze_sha256 is not None
    freeze_path = args.execution_freeze.resolve()
    freeze_bytes, freeze_document = _load_yaml_mapping(
        freeze_path,
        label="subject audit execution freeze",
    )
    execution_freeze = (
        validate_subject_audit_execution_freeze(
            document=freeze_document,
            source_bytes=freeze_bytes,
            source_path=freeze_path,
            expected_sha256=(
                args.expected_execution_freeze_sha256
            ),
            manifest_path=manifest_path,
            manifest_sha256=manifest_sha256,
            protocol_path=protocol_path,
            protocol_sha256=protocol_sha256,
            candidate_protocol_path=candidate_path.resolve(),
            candidate_protocol_sha256=hashlib.sha256(
                candidate_bytes
            ).hexdigest(),
            recall_gate_path=gate_path.resolve(),
            recall_gate_sha256=hashlib.sha256(
                gate_bytes
            ).hexdigest(),
            output_path=requested_output_path,
            layer_index=args.layer,
            comparison_group=group_key,
            global_row_key_sha256=row_identity_sha256,
            query_selection_sha256=selection.sha256,
            audit_config_sha256=audit_config.sha256,
            query_count=selection.count,
            query_seed=selection.seed,
        )
    )
    protocol_binding = NeighborAuditProtocolBinding(
        protocol_id=protocol_id,
        status=protocol_status,
        source_sha256=protocol_sha256,
        candidate_config_sha256=canonical_json_sha256(
            candidate_config.to_dict()
        ),
        audit_config_sha256=audit_config.sha256,
        deviations=tuple(sorted(set(deviations))),
        query_selection=selection,
    )
    output_reservation = reserve_audit_output(requested_output_path)
    try:
        result = _audit_neighbor_backend_from_manifest(
            manifest_path,
            layer_index=args.layer,
            subject_backend_factory=lambda snapshot: FaissHNSWBackend(
                snapshot,
                row_identity_sha256=row_identity_sha256,
                comparison_group=group_key,
                config=faiss_config,
                worker_runtime_contract=(
                    execution_freeze.worker_runtime_contract()
                ),
                qualification_receipt=qualification_receipt,
            ),
            protocol_binding=protocol_binding,
            candidate_config=candidate_config,
            audit_config=audit_config,
            execution_freeze=execution_freeze,
            verify_checksums=not args.skip_checksums,
        )
        if protocol_path.read_bytes() != protocol_bytes:
            raise ValueError("neighbor protocol changed during audit")
        if candidate_path.read_bytes() != candidate_bytes:
            raise ValueError("candidate protocol changed during audit")
        if gate_path.read_bytes() != gate_bytes:
            raise ValueError("recall gate contract changed during audit")
        if (
            qualification_path is not None
            and qualification_path.read_bytes()
            != qualification_bytes
        ):
            raise ValueError(
                "backend qualification changed during audit"
            )
        if freeze_path.read_bytes() != freeze_bytes:
            raise ValueError(
                "subject audit execution freeze changed during audit"
            )
        execution_freeze.revalidate()
        execution_freeze.validate_subject_backend(
            result.subject_backend
        )
        output_path = write_neighbor_audit(
            result,
            requested_output_path,
            _reservation=output_reservation,
        )
    finally:
        output_reservation.close()
    try:
        load_neighbor_audit_receipt(
            output_path,
            protocol_path=protocol_path,
            expected_audit_sha256=result.sha256,
            expected_protocol_sha256=protocol_sha256,
        )
    except (TypeError, ValueError) as error:
        promotion_eligible = False
        promotion_ineligibility_reason = str(error)
    else:
        promotion_eligible = True
        promotion_ineligibility_reason = None
    _print_json(
        {
            "command": "neighbor-audit",
            "status": result.status,
            "promotion_eligible": promotion_eligible,
            "promotion_ineligibility_reason": (
                promotion_ineligibility_reason
            ),
            "audit": str(output_path.resolve()),
            "audit_sha256": result.sha256,
            "audit_identity_sha256": result.identity_sha256,
            "coverage_contract_sha256": (
                result.coverage_contract_sha256
            ),
            "coverage_evidence_sha256": (
                result.coverage_evidence_sha256
            ),
            "coverage_gate_status": (
                result.coverage_gate_statuses()
            ),
            "comparison_group": group_key,
            "reference_candidate_count": (
                result.reference_candidate_count
            ),
            "candidate_boundary_recall": list(
                result.candidate_boundary_recall
            ),
        }
    )
    return _neighbor_audit_exit_code(
        protocol_status=protocol_status,
        audit_status=result.status,
        promotion_eligible=promotion_eligible,
    )


def _add_calibrate_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "calibrate",
        help="run model-free winding and holonomy phantoms",
    )
    parser.add_argument("--samples", type=int, default=512)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace an existing report path",
    )
    parser.set_defaults(handler=_run_calibrate)


def _add_atlas_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "atlas",
        help="stream a fixed-context Pythia token-ID activation atlas",
    )
    parser.add_argument(
        "--model",
        help=(
            "Hugging Face model ID; defaults to Pythia-70M for raw capture "
            "and is derived from --context-bank for bound capture"
        ),
    )
    parser.add_argument("--revision")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--context-ids",
        type=int,
        nargs="+",
        metavar="ID",
        help=(
            "fixed token IDs; the ID at --sweep-position is replaced during "
            "the sweep"
        ),
    )
    parser.add_argument(
        "--position",
        type=int,
        help="residual observation position (also the sweep position by default)",
    )
    parser.add_argument(
        "--sweep-position",
        type=int,
        help="slot replaced during the sweep; defaults to --position",
    )
    parser.add_argument("--attention-mask", type=int, nargs="+", metavar="BIT")
    parser.add_argument(
        "--context-bank",
        type=Path,
        help="strict context-bank YAML to bind into capture and resume",
    )
    parser.add_argument(
        "--context-id",
        help="entry selected from --context-bank",
    )
    parser.add_argument(
        "--allow-role",
        action="append",
        choices=("example", "discovery", "held_out"),
        help=(
            "explicitly allowed bank role; pass exactly once with "
            "--context-bank"
        ),
    )
    parser.add_argument("--expected-context-bank-source-sha256")
    parser.add_argument("--expected-context-bank-canonical-sha256")
    parser.add_argument("--subset", type=int, nargs="+", metavar="ID")
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument(
        "--full-vocabulary",
        action="store_true",
        help="explicitly authorize every ID in the declared sweep domain",
    )
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--device", default="auto")
    parser.add_argument(
        "--dtype",
        choices=("auto", "float32", "float16", "bfloat16"),
        default="auto",
    )
    parser.add_argument(
        "--local-files-only",
        action="store_true",
        help="fail instead of downloading uncached model files",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="resume a matching interrupted atlas",
    )
    parser.set_defaults(handler=_run_atlas)


def _add_context_bank_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "context-bank",
        help="inspect strict, semantics-free context-bank artifacts",
    )
    commands = parser.add_subparsers(
        dest="context_bank_command",
        required=True,
    )
    validate = commands.add_parser(
        "validate",
        help="validate schema, roles, provenance, and canonical identity",
    )
    validate.add_argument("--path", type=Path, required=True)
    validate.add_argument(
        "--allow-role",
        action="append",
        choices=("example", "discovery", "held_out"),
        required=True,
        help=(
            "explicitly allowed bank role; pass exactly once"
        ),
    )
    validate.add_argument("--expected-source-sha256")
    validate.add_argument("--expected-canonical-sha256")
    validate.set_defaults(handler=_run_context_bank_validate)


def _add_hypothesis_registry_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "hypothesis-registry",
        help="inspect the outcome-excluded P0 hypothesis registry",
    )
    commands = parser.add_subparsers(
        dest="hypothesis_registry_command",
        required=True,
    )
    validate = commands.add_parser(
        "validate",
        help="validate the strict F0-F4 registry and its canonical identity",
    )
    validate.add_argument("--path", type=Path, required=True)
    validate.add_argument("--expected-source-sha256")
    validate.add_argument("--expected-canonical-sha256")
    validate.set_defaults(handler=_run_hypothesis_registry_validate)


def _add_instrument_artifact_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "instrument-artifact",
        help="inspect one canonical metadata-only instrument artifact",
    )
    commands = parser.add_subparsers(
        dest="instrument_artifact_command",
        required=True,
    )
    validate = commands.add_parser(
        "validate",
        help="validate exact schema, canonical bytes, and digest identity",
    )
    validate.add_argument("--path", type=Path, required=True)
    validate.add_argument("--expected-source-sha256")
    validate.add_argument("--expected-canonical-sha256")
    validate.set_defaults(handler=_run_instrument_artifact_validate)


def _add_instrument_bundle_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "instrument-bundle",
        help="validate one canonical closed integrity bundle",
    )
    commands = parser.add_subparsers(
        dest="instrument_bundle_command",
        required=True,
    )
    validate = commands.add_parser(
        "validate",
        help=(
            "resolve artifact/payload identities and cross-manifest "
            "metadata joins without decoding payload values"
        ),
    )
    validate.add_argument("--path", type=Path, required=True)
    validate.add_argument("--expected-source-sha256")
    validate.add_argument("--expected-canonical-sha256")
    validate.set_defaults(handler=_run_instrument_bundle_validate)


def _add_synthetic_bundle_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "synthetic-bundle",
        help=(
            "generate a Level-0 representation-shaped development bundle"
        ),
    )
    commands = parser.add_subparsers(
        dest="synthetic_bundle_command",
        required=True,
    )
    generate = commands.add_parser(
        "generate",
        help=(
            "emit and self-validate a canonical closed-integrity bundle; "
            "this does not qualify D0-D8"
        ),
    )
    generate.add_argument("--protocol", type=Path, required=True)
    generate.add_argument("--output-dir", type=Path, required=True)
    generate.set_defaults(handler=_run_synthetic_bundle_generate)


def _add_candidates_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "candidates",
        help="emit a structural, semantics-free candidate ledger",
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--protocol", type=Path)
    parser.add_argument(
        "--protocol-id",
        help="must match protocol_id when --protocol is supplied",
    )
    parser.add_argument("--layers", type=int, nargs="+", metavar="LAYER")
    parser.add_argument("--cosine-min", type=float)
    parser.add_argument("--relative-norm-gap-max", type=float)
    parser.add_argument("--drift-relative-divergence-min", type=float)
    parser.add_argument("--drift-absolute-divergence-min", type=float)
    parser.add_argument("--min-state-norm", type=float)
    parser.add_argument("--min-drift-norm", type=float)
    parser.add_argument("--block-size", type=int)
    parser.add_argument(
        "--neighbor-backend",
        choices=("exact", "faiss-hnsw"),
        default="exact",
        help=(
            "retrieval backend; faiss-hnsw requires a frozen passing "
            "neighbor-audit receipt for the same full atlas and layer"
        ),
    )
    parser.add_argument(
        "--neighbor-audit",
        type=Path,
        help="passing audit artifact authorizing approximate persistence",
    )
    parser.add_argument(
        "--neighbor-audit-protocol",
        type=Path,
        help="exact frozen protocol bytes bound by --neighbor-audit",
    )
    parser.add_argument(
        "--expected-audit-sha256",
        help="required out-of-band digest for Faiss promotion",
    )
    parser.add_argument(
        "--expected-neighbor-protocol-sha256",
        help="required out-of-band digest for the frozen neighbor protocol",
    )
    parser.add_argument(
        "--max-pairwise-rows",
        type=int,
        help="fail loudly above this exact pairwise-search size",
    )
    parser.add_argument(
        "--skip-checksums",
        action="store_true",
        help="skip whole-file hashes (schema and batch journal remain validated)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace an existing ledger path",
    )
    parser.set_defaults(handler=_run_candidates)


def _add_neighbor_audit_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "neighbor-audit",
        help=(
            "compare one full-atlas Faiss HNSW index against a "
            "preregistered exact query subset"
        ),
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--layer", type=int, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help=(
            "print atlas row/group bindings without building an index "
            "or observing audit outcomes"
        ),
    )
    parser.add_argument(
        "--expected-protocol-sha256",
        help="optional fail-closed digest for the neighbor protocol",
    )
    parser.add_argument(
        "--execution-freeze",
        type=Path,
        help="tracked source/runtime/invocation freeze for subject audits",
    )
    parser.add_argument(
        "--expected-execution-freeze-sha256",
        help="required out-of-band digest for --execution-freeze",
    )
    parser.add_argument(
        "--skip-checksums",
        action="store_true",
        help="skip whole-file atlas hashes (manifest structure is still checked)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace an existing audit path",
    )
    parser.set_defaults(handler=_run_neighbor_audit)


def _add_faiss_range_preflight_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "faiss-range-preflight",
        help=(
            "run the fixed production-shape synthetic qualification for "
            "the versioned Faiss native range-call path"
        ),
    )
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument(
        "--expected-protocol-sha256",
        required=True,
        help="required out-of-band digest for the v0.4 draft protocol",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.set_defaults(handler=_run_faiss_range_preflight)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spirallens",
        description=(
            "Auditable calibration, Pythia activation-atlas, and structural "
            "candidate instrumentation."
        ),
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--traceback",
        action="store_true",
        help="show a Python traceback when a command fails",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_calibrate_parser(subparsers)
    _add_context_bank_parser(subparsers)
    _add_hypothesis_registry_parser(subparsers)
    _add_instrument_artifact_parser(subparsers)
    _add_instrument_bundle_parser(subparsers)
    _add_synthetic_bundle_parser(subparsers)
    _add_atlas_parser(subparsers)
    _add_faiss_range_preflight_parser(subparsers)
    _add_neighbor_audit_parser(subparsers)
    _add_candidates_parser(subparsers)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
    except Exception as exc:
        if args.traceback:
            raise
        print(f"spirallens: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
