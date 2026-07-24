from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import yaml

from spirallens.audit_output import reserve_audit_output
from spirallens.metrics import (
    CandidateSearchConfig,
    NeighborAuditConfig,
    NeighborAuditProtocolBinding,
    NeighborAuditReceipt,
    NeighborPersistenceTarget,
    NeighborQuerySelectionContract,
    audit_neighbor_backend,
    load_neighbor_audit_receipt,
    write_neighbor_audit,
)
from spirallens.metrics.neighbor_receipt import (
    _expected_promotion_readiness,
    validate_neighbor_protocol_static_contract,
)
from spirallens.neighbors import (
    FaissHNSWBackend,
    FaissHNSWConfig,
    NeighborBackendDescriptor,
    NeighborQuery,
    canonical_json_sha256,
    state_matrix_sha256,
)


def test_v03_draft_protocol_declares_pending_native_qualification() -> None:
    protocol_path = (
        Path(__file__).resolve().parents[1]
        / "protocols"
        / "pythia_neighbor_v0_3.yaml"
    )
    protocol = yaml.safe_load(protocol_path.read_bytes())

    validate_neighbor_protocol_static_contract(protocol)

    assert protocol["subject_backend"]["backend_version"] == "0.2"
    assert protocol["subject_backend"]["config"][
        "range_call_batch_size"
    ] == 1
    assert protocol["backend_qualification"][
        "binding_rule"
    ] == "must_be_filled_before_status_frozen"
    assert protocol["promotion_readiness"][
        "production_shape_subprocess_qualified"
    ] is False


def test_v03_frozen_readiness_includes_production_qualification() -> None:
    assert _expected_promotion_readiness(
        qualified_protocol=True,
        frozen=True,
    ) == {
        "receipt_mechanism_implemented": True,
        "full_index_subset_query_audit_implemented": True,
        "frozen_recall_gate_methodology_available": True,
        "query_local_worst_case_recall_gate_implemented": True,
        "production_shape_subprocess_qualified": True,
        "atlas_execution_bindings_frozen": True,
        "tracked_protocol_can_issue_persistence_receipt": True,
    }


def _fixture() -> tuple[np.ndarray, np.ndarray]:
    states = np.array(
        [
            [1.0, 0.0],
            [1.0, 0.001],
            [1.0, -0.001],
            [0.0, 1.0],
            [0.0, 0.0],
        ],
        dtype=np.float64,
    )
    drifts = np.array(
        [
            [0.0, 1.0],
            [0.0, -1.0],
            [0.0, 1.0],
            [0.1, 0.0],
            [0.0, 0.1],
        ],
        dtype=np.float64,
    )
    return states, drifts


def _faiss_config(
    audit_config: NeighborAuditConfig,
) -> FaissHNSWConfig:
    return FaissHNSWConfig(
        m=4,
        ef_construction=40,
        ef_search=40,
        query_batch_size=2,
        score_margin=audit_config.boundary_shell_width,
    )


def _write_recall_gate(
    tmp_path: Path,
    audit_config: NeighborAuditConfig,
) -> Path:
    source = (
        Path(__file__).resolve().parents[1]
        / "protocols"
        / "neighbor_recall_gate_v0_1.yaml"
    )
    document = yaml.safe_load(source.read_text(encoding="utf-8"))
    document["gate_id"] = "tests-neighbor-recall-gate-v0.1"
    document["thresholds"].update(
        {
            "aggregate_candidate_recall_min": (
                audit_config.candidate_recall_min
            ),
            "query_local_recall_min": (
                audit_config.query_local_recall_min
            ),
            "density_macro_and_joint_stratum_recall_min": (
                audit_config.stratum_recall_min
            ),
            "boundary_shell_width": (
                audit_config.boundary_shell_width
            ),
            "repeats": audit_config.repeats,
        }
    )
    document["support"].update(
        {
            "minimum_reference_candidates": (
                audit_config.minimum_reference_candidates
            ),
            "minimum_eligible_queries": (
                audit_config.minimum_eligible_queries
            ),
            "minimum_eligible_query_fraction": (
                audit_config.minimum_eligible_query_fraction
            ),
            "density_strata_count": audit_config.density_strata_count,
            "minimum_eligible_queries_per_density_stratum": (
                audit_config
                .minimum_eligible_queries_per_density_stratum
            ),
            "minimum_reference_candidates_per_joint_stratum": (
                audit_config.minimum_reference_candidates_per_stratum
            ),
        }
    )
    path = tmp_path / "recall-gate.yaml"
    path.write_text(
        yaml.safe_dump(document, sort_keys=False),
        encoding="utf-8",
    )
    return path


def _frozen_result(
    tmp_path: Path,
):
    states, drifts = _fixture()
    row_identity_sha256 = hashlib.sha256(b"atlas-row-keys").hexdigest()
    manifest_sha256 = hashlib.sha256(b"atlas-manifest").hexdigest()
    candidate_config = CandidateSearchConfig(
        cosine_min=0.999,
        relative_norm_gap_max=0.05,
        drift_relative_divergence_min=1.5,
        block_size=2,
        layer_indices=(0,),
    )
    audit_config = NeighborAuditConfig(
        candidate_recall_min=0.99,
        query_local_recall_min=0.99,
        stratum_recall_min=0.99,
        minimum_reference_candidates=1,
        minimum_eligible_queries=1,
        minimum_eligible_query_fraction=0.0,
        density_strata_count=1,
        minimum_eligible_queries_per_density_stratum=1,
        boundary_shell_width=0.000999,
        minimum_reference_candidates_per_stratum=1,
    )
    selection = NeighborQuerySelectionContract(
        seed=7,
        count=states.shape[0],
        global_row_key_sha256=row_identity_sha256,
    )
    candidate_path = tmp_path / "candidate.yaml"
    candidate_document = yaml.safe_load(
        (
            Path(__file__).resolve().parents[1]
            / "protocols"
            / "pythia_candidate_v0_2.yaml"
        ).read_text(encoding="utf-8")
    )
    candidate_document["protocol_id"] = "frozen-candidate-v0.2"
    candidate_document["status"] = "frozen"
    candidate_document["candidate_search"] = (
        candidate_config.to_dict()
    )
    candidate_path.write_text(
        yaml.safe_dump(candidate_document, sort_keys=False),
        encoding="utf-8",
    )
    recall_gate_path = _write_recall_gate(tmp_path, audit_config)
    protocol_path = tmp_path / "neighbor.yaml"
    protocol_document = {
        "schema_version": "spirallens.neighbor-audit-protocol.v0.2",
        "protocol_id": "frozen-neighbor-v0.1",
        "status": "frozen",
        "claim_ceiling": 1,
        "recall_gate_contract": {
            "path": recall_gate_path.name,
            "sha256": hashlib.sha256(
                recall_gate_path.read_bytes()
            ).hexdigest(),
            "gate_id": "tests-neighbor-recall-gate-v0.1",
        },
        "audit_scope": {"comparison_group": "layer_index=0"},
        "candidate_protocol": {
            "path": candidate_path.name,
            "sha256": hashlib.sha256(
                candidate_path.read_bytes()
            ).hexdigest(),
            "declared_id": "frozen-candidate-v0.2",
        },
        "retrieval_contract": {
            "input": "resid_pre",
            "input_snapshot": "detached_read_only",
            "input_sha256_checked_before_and_after_each_rebuild": True,
            "metric": "cosine",
            "comparison_unit": [
                "fixed_context_bank",
                "fixed_context_id",
                "fixed_observation_position",
                "fixed_layer_index",
            ],
            "output": "canonical_unordered_global_row_pairs",
            "pair_order": "left_then_right_ascending",
            "drift_available_to_backend": False,
            "decoded_strings_available_to_backend": False,
            "semantic_annotation_available_to_backend": False,
            "sae_annotation_available_to_backend": False,
            "projected_coordinates_available_to_backend": False,
        },
        "reference_backend": {
            "backend_id": "spirallens.exact-blockwise-reference",
            "backend_version": "0.1",
            "kind": "exact",
            "deterministic": True,
            "descriptor_sha256_bound_in_audit_identity": True,
            "runtime_version_bound_in_descriptor": True,
            "maximum_all_pair_rows": 10000,
            "maximum_exact_comparisons": 50000000,
            "inclusive_thresholds": True,
        },
        "subject_backend": {
            "status": "implementation_selected_unpromoted",
            "backend_id": "spirallens.faiss-hnsw-range",
            "backend_version": "0.1",
            "distribution": "faiss-cpu",
            "distribution_version": "1.14.3",
            "kind_required_for_full_vocabulary": "approximate",
            "optional_dependency_only": True,
            "candidate_persistence_without_audit_receipt": (
                "forbidden"
            ),
            "config": _faiss_config(audit_config).to_dict(),
            "required_provenance": [
                "backend_id",
                "backend_version",
                "backend_config",
                "runtime_versions",
                "seed",
                "thread_count",
                "index_digest",
            ],
        },
        "query_sampling": {
            "method": "sha256_ranked_global_indices",
            "seed": 7,
            "count": int(states.shape[0]),
            "global_row_key_sha256": row_identity_sha256,
        },
        "exact_rerank": {
            "contract": "spirallens.candidate-exact-rerank.v0.1",
            "required_before_persist": True,
            "source_values": "original_atlas_values_cast_to_float64",
            "backend_score_used_for_gate": False,
            "false_persistable_candidates_allowed": 0,
        },
        "audit": {
            "primary_metric": "candidate_boundary_recall",
            "candidate_boundary_recall_min": (
                audit_config.candidate_recall_min
            ),
            "query_local_recall_min": (
                audit_config.query_local_recall_min
            ),
            "stratum_recall_min": (
                audit_config.stratum_recall_min
            ),
            "repeats": audit_config.repeats,
            "repeat_mode": "independent_cold_rebuild",
            "minimum_reference_candidates": (
                audit_config.minimum_reference_candidates
            ),
            "minimum_eligible_queries": (
                audit_config.minimum_eligible_queries
            ),
            "minimum_eligible_query_fraction": (
                audit_config.minimum_eligible_query_fraction
            ),
            "density_strata_count": (
                audit_config.density_strata_count
            ),
            "minimum_eligible_queries_per_density_stratum": (
                audit_config
                .minimum_eligible_queries_per_density_stratum
            ),
            "boundary_shell_width": (
                audit_config.boundary_shell_width
            ),
            "minimum_reference_candidates_per_stratum": (
                audit_config.minimum_reference_candidates_per_stratum
            ),
            "missing_pair_sample_limit": (
                audit_config.missing_pair_sample_limit
            ),
            "zero_reference_candidates": "insufficient",
            "top_k_recall_role": "not_applicable_range_search",
            "pooled_recall_can_override_failed_group": False,
            "required_local_recall_contract": (
                "spirallens.neighbor-local-recall.v0.1"
            ),
            "required_joint_strata": (
                "density_rank_x_cosine_boundary"
            ),
            "issue_persistence_receipt_on_verified_pass": True,
            "protocol_binding_required": True,
            "source_identity_required": True,
        },
        "claim_boundary": {
            "semantics_free": True,
            "candidate_is_not_verified_vortex": True,
            "passing_audit_proves_retrieval_coverage_only": True,
            "approximate_backend_currently_audited": False,
        },
        "promotion_readiness": {
            "receipt_mechanism_implemented": True,
            "full_index_subset_query_audit_implemented": True,
            "frozen_recall_gate_methodology_available": True,
            "query_local_worst_case_recall_gate_implemented": True,
            "atlas_execution_bindings_frozen": True,
            "tracked_protocol_can_issue_persistence_receipt": True,
        },
        "deviations": [],
    }
    protocol_path.write_text(
        yaml.safe_dump(protocol_document, sort_keys=False),
        encoding="utf-8",
    )
    protocol_sha256 = hashlib.sha256(
        protocol_path.read_bytes()
    ).hexdigest()
    query_indices = selection.select(states.shape[0])
    protocol = NeighborAuditProtocolBinding(
        protocol_id="frozen-neighbor-v0.1",
        status="frozen",
        source_sha256=protocol_sha256,
        candidate_config_sha256=canonical_json_sha256(
            candidate_config.to_dict()
        ),
        audit_config_sha256=audit_config.sha256,
        query_selection=selection,
    )
    source = {
        "kind": "atlas_subset",
        "atlas_manifest_sha256": manifest_sha256,
        "atlas_run_id": "atlas-run-1",
        "observation_scope_sha256": hashlib.sha256(
            b"layer-0-scope"
        ).hexdigest(),
        "global_row_key_sha256": row_identity_sha256,
        "execution_freeze_sha256": "e" * 64,
    }
    result = audit_neighbor_backend(
        states,
        drifts,
        subject_backend_factory=lambda snapshot: FaissHNSWBackend(
            snapshot,
            row_identity_sha256=row_identity_sha256,
            comparison_group="layer_index=0",
            config=_faiss_config(audit_config),
        ),
        protocol_binding=protocol,
        source_identity=source,
        candidate_config=candidate_config,
        audit_config=audit_config,
        query_indices=query_indices,
        source_run_id="atlas-run-1",
        group_key="layer_index=0",
    )
    return (
        result,
        states,
        drifts,
        row_identity_sha256,
        manifest_sha256,
        protocol_path,
    )


def _rebind_result_to_protocol(result, protocol_path: Path):
    return replace(
        result,
        protocol_binding=replace(
            result.protocol_binding,
            source_sha256=hashlib.sha256(
                protocol_path.read_bytes()
            ).hexdigest(),
        ),
    )


def _write_rebound_audit(
    tmp_path: Path,
    result,
    protocol_path: Path,
    *,
    name: str,
):
    rebound = _rebind_result_to_protocol(result, protocol_path)
    audit_path = tmp_path / name
    _write_atlas_audit(rebound, audit_path)
    return rebound, audit_path


def _write_atlas_audit(result, audit_path: Path) -> None:
    reservation = reserve_audit_output(audit_path)
    try:
        write_neighbor_audit(
            result,
            audit_path,
            _reservation=reservation,
        )
    finally:
        reservation.close()


def test_atlas_audit_requires_exclusive_output_reservation(
    tmp_path: Path,
) -> None:
    result, *_ = _frozen_result(tmp_path)

    with pytest.raises(
        ValueError,
        match="require an exclusive output reservation",
    ):
        write_neighbor_audit(result, tmp_path / "unreserved-audit.json")


def _target(
    result,
    states,
    drifts,
    row_identity_sha256,
    manifest_sha256,
    receipt,
):
    backend = FaissHNSWBackend(
        states,
        row_identity_sha256=row_identity_sha256,
        comparison_group="layer_index=0",
        config=_faiss_config(result.audit_config),
    )
    return NeighborPersistenceTarget(
        backend=backend.descriptor,
        build_receipt=backend.build_receipt,
        candidate_config=result.candidate_config,
        candidate_protocol_id=receipt.candidate_protocol_id,
        candidate_protocol_sha256=(
            receipt.candidate_protocol_sha256
        ),
        query=NeighborQuery(
            cosine_min=result.query.cosine_min,
            relative_norm_gap_max=result.query.relative_norm_gap_max,
            min_state_norm=result.query.min_state_norm,
            epsilon=result.query.epsilon,
        ),
        atlas_manifest_sha256=manifest_sha256,
        atlas_run_id="atlas-run-1",
        global_row_key_sha256=row_identity_sha256,
        source_run_id="atlas-run-1",
        comparison_group="layer_index=0",
        states_sha256=state_matrix_sha256(states),
        drifts_sha256=state_matrix_sha256(drifts),
        row_count=int(states.shape[0]),
        hidden_size=int(states.shape[1]),
        states_dtype=str(states.dtype),
        drifts_dtype=str(drifts.dtype),
    )


def test_receipt_authorizes_only_identical_full_input_index_group(
    tmp_path: Path,
) -> None:
    (
        result,
        states,
        drifts,
        row_identity,
        manifest_sha,
        protocol_path,
    ) = _frozen_result(tmp_path)
    audit_path = tmp_path / "audit.json"
    _write_atlas_audit(result, audit_path)
    receipt = load_neighbor_audit_receipt(
        audit_path,
        protocol_path=protocol_path,
        expected_audit_sha256=result.sha256,
        expected_protocol_sha256=hashlib.sha256(
            protocol_path.read_bytes()
        ).hexdigest(),
    )
    target = _target(
        result,
        states,
        drifts,
        row_identity,
        manifest_sha,
        receipt,
    )

    receipt.validate_target(target)
    assert receipt.subject_backend == target.backend
    assert receipt.authorized_target_query_sha256 == target.query.sha256
    assert receipt.schema_version == (
        "spirallens.neighbor-audit-receipt.v0.2"
    )
    assert (
        receipt.coverage_contract_sha256
        == result.coverage_contract_sha256
    )
    assert (
        receipt.coverage_evidence_sha256
        == result.coverage_evidence_sha256
    )
    with pytest.raises(ValueError, match="drifts"):
        receipt.validate_target(
            replace(target, drifts_sha256="f" * 64)
        )
    reconstructed = NeighborAuditReceipt.from_dict(receipt.to_dict())
    assert reconstructed.verified is False
    with pytest.raises(ValueError, match="verified audit/protocol"):
        reconstructed.validate_target(target)
    legacy = receipt.to_dict()
    legacy["schema_version"] = (
        "spirallens.neighbor-audit-receipt.v0.1"
    )
    with pytest.raises(ValueError, match="receipt schema"):
        NeighborAuditReceipt.from_dict(legacy)
    malformed = receipt.to_dict()
    malformed["row_count"] += 1
    with pytest.raises(ValueError, match="index build receipt"):
        NeighborAuditReceipt.from_dict(malformed)
    noncanonical = receipt.to_dict()
    noncanonical["row_count"] = float(noncanonical["row_count"])
    with pytest.raises(TypeError, match="row_count must be an integer"):
        NeighborAuditReceipt.from_dict(noncanonical)


def test_v03_pass_loads_positive_qualification_and_issues_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        result,
        states,
        drifts,
        row_identity,
        manifest_sha,
        protocol_path,
    ) = _frozen_result(tmp_path)
    protocol = yaml.safe_load(protocol_path.read_bytes())
    qualification_path = tmp_path / "qualification.json"
    qualification_bytes = b"{}"
    qualification_path.write_bytes(qualification_bytes)
    qualification_sha256 = hashlib.sha256(
        qualification_bytes
    ).hexdigest()
    fixture_sha256 = "f" * 64
    runtime = dict(result.subject_backend.runtime)
    native_sha256 = runtime["faiss_native_sha256"]
    fake_qualification = SimpleNamespace(
        sha256=qualification_sha256,
        fixture_sha256=fixture_sha256,
        runtime={"faiss_native_sha256": native_sha256},
    )
    import spirallens.neighbors.faiss_qualification as qualification_module

    monkeypatch.setattr(
        qualification_module,
        "load_faiss_hnsw_qualification_receipt",
        lambda path, expected_sha256: fake_qualification,
    )
    protocol["schema_version"] = (
        "spirallens.neighbor-audit-protocol.v0.3"
    )
    protocol["backend_qualification"] = {
        "schema_version": (
            "spirallens.faiss-hnsw-range-qualification.v0.1"
        ),
        "path": qualification_path.name,
        "sha256": qualification_sha256,
        "fixture_sha256": fixture_sha256,
    }
    protocol["subject_backend"]["backend_version"] = "0.2"
    protocol["subject_backend"]["config"][
        "range_call_batch_size"
    ] = 1
    protocol["subject_backend"]["required_provenance"].extend(
        [
            "qualification_receipt_digest",
            "qualification_fixture_digest",
        ]
    )
    protocol["promotion_readiness"][
        "production_shape_subprocess_qualified"
    ] = True
    protocol_path.write_text(
        yaml.safe_dump(protocol, sort_keys=False),
        encoding="utf-8",
    )

    parameters = dict(result.subject_backend.parameters)
    parameters.update(
        {
            "range_call_batch_size": 1,
            "max_native_call_hits": result.row_count,
            "qualification_receipt_sha256": (
                qualification_sha256
            ),
            "qualification_fixture_sha256": fixture_sha256,
        }
    )
    qualified_result = replace(
        result,
        subject_backend=NeighborBackendDescriptor(
            backend_id=result.subject_backend.backend_id,
            backend_version="0.2",
            kind=result.subject_backend.kind,
            deterministic=result.subject_backend.deterministic,
            parameters=tuple(parameters.items()),
            runtime=result.subject_backend.runtime,
        ),
        protocol_binding=replace(
            result.protocol_binding,
            source_sha256=hashlib.sha256(
                protocol_path.read_bytes()
            ).hexdigest(),
        ),
    )
    audit_path = tmp_path / "qualified-audit.json"
    _write_atlas_audit(qualified_result, audit_path)

    receipt = load_neighbor_audit_receipt(
        audit_path,
        protocol_path=protocol_path,
        expected_audit_sha256=qualified_result.sha256,
        expected_protocol_sha256=hashlib.sha256(
            protocol_path.read_bytes()
        ).hexdigest(),
    )

    assert receipt.subject_backend.backend_version == "0.2"
    assert dict(receipt.subject_backend.parameters)[
        "qualification_receipt_sha256"
    ] == qualification_sha256
    target = NeighborPersistenceTarget(
        backend=receipt.subject_backend,
        build_receipt=receipt.subject_build_receipt,
        candidate_config=qualified_result.candidate_config,
        candidate_protocol_id=receipt.candidate_protocol_id,
        candidate_protocol_sha256=(
            receipt.candidate_protocol_sha256
        ),
        query=NeighborQuery(
            cosine_min=qualified_result.query.cosine_min,
            relative_norm_gap_max=(
                qualified_result.query.relative_norm_gap_max
            ),
            min_state_norm=qualified_result.query.min_state_norm,
            epsilon=qualified_result.query.epsilon,
        ),
        atlas_manifest_sha256=manifest_sha,
        atlas_run_id="atlas-run-1",
        global_row_key_sha256=row_identity,
        source_run_id="atlas-run-1",
        comparison_group="layer_index=0",
        states_sha256=state_matrix_sha256(states),
        drifts_sha256=state_matrix_sha256(drifts),
        row_count=int(states.shape[0]),
        hidden_size=int(states.shape[1]),
        states_dtype=str(states.dtype),
        drifts_dtype=str(drifts.dtype),
    )

    assert receipt.verified is True
    receipt.validate_target(target)


def test_audit_result_rejects_query_selection_rewrite(
    tmp_path: Path,
) -> None:
    result, *_ = _frozen_result(tmp_path)

    with pytest.raises(
        ValueError,
        match="preregistered selection",
    ):
        replace(
            result,
            query=replace(result.query, query_indices=(0,)),
        )


def test_receipt_rejects_draft_or_deviated_audit(
    tmp_path: Path,
) -> None:
    result, *_, protocol_path = _frozen_result(tmp_path)
    bindings = (
        replace(
            result.protocol_binding,
            status="preregistered-draft",
        ),
        replace(
            result.protocol_binding,
            deviations=("test-deviation",),
        ),
    )

    for index, binding in enumerate(bindings):
        forged = replace(
            result,
            protocol_binding=binding,
        )
        audit_path = tmp_path / f"forged-{index}.json"
        _write_atlas_audit(forged, audit_path)
        with pytest.raises(ValueError):
            load_neighbor_audit_receipt(
                audit_path,
                protocol_path=protocol_path,
                expected_audit_sha256=forged.sha256,
                expected_protocol_sha256=hashlib.sha256(
                    protocol_path.read_bytes()
                ).hexdigest(),
            )


def test_load_receipt_binds_actual_frozen_protocol_bytes(
    tmp_path: Path,
) -> None:
    result, *_, protocol_path = _frozen_result(tmp_path)
    audit_path = tmp_path / "audit.json"
    _write_atlas_audit(result, audit_path)

    receipt = load_neighbor_audit_receipt(
        audit_path,
        protocol_path=protocol_path,
        expected_audit_sha256=result.sha256,
        expected_protocol_sha256=hashlib.sha256(
            protocol_path.read_bytes()
        ).hexdigest(),
    )

    assert receipt.audit_sha256 == result.sha256
    protocol_path.write_text(
        protocol_path.read_text(encoding="utf-8") + "# changed\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="supplied frozen protocol"):
        load_neighbor_audit_receipt(
            audit_path,
            protocol_path=protocol_path,
            expected_audit_sha256=result.sha256,
            expected_protocol_sha256=hashlib.sha256(
                protocol_path.read_bytes()
            ).hexdigest(),
        )


@pytest.mark.parametrize(
    ("mutate", "match"),
    (
        (
            lambda document: document.__setitem__(
                "schema_version",
                "spirallens.neighbor-audit-protocol.v0.1",
            ),
            "top-level contract",
        ),
        (
            lambda document: document["audit"].__setitem__(
                "query_local_recall_min",
                0.98,
            ),
            "audit settings",
        ),
        (
            lambda document: document["audit"].__setitem__(
                "pooled_recall_can_override_failed_group",
                True,
            ),
            "audit settings",
        ),
        (
            lambda document: document["promotion_readiness"].__setitem__(
                "tracked_protocol_can_issue_persistence_receipt",
                False,
            ),
            "frozen neighbor protocol binding",
        ),
    ),
)
def test_receipt_rejects_legacy_or_incomplete_promotion_contract(
    tmp_path: Path,
    mutate,
    match: str,
) -> None:
    result, *_, protocol_path = _frozen_result(tmp_path)
    document = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
    mutate(document)
    protocol_path.write_text(
        yaml.safe_dump(document, sort_keys=False),
        encoding="utf-8",
    )
    rebound, audit_path = _write_rebound_audit(
        tmp_path,
        result,
        protocol_path,
        name=f"invalid-{match.replace(' ', '-')}.json",
    )

    with pytest.raises(ValueError, match=match):
        load_neighbor_audit_receipt(
            audit_path,
            protocol_path=protocol_path,
            expected_audit_sha256=rebound.sha256,
            expected_protocol_sha256=hashlib.sha256(
                protocol_path.read_bytes()
            ).hexdigest(),
        )


def test_receipt_rejects_rehashed_recall_gate_methodology_change(
    tmp_path: Path,
) -> None:
    result, *_, protocol_path = _frozen_result(tmp_path)
    protocol = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
    gate_path = protocol_path.parent / protocol["recall_gate_contract"]["path"]
    gate = yaml.safe_load(gate_path.read_text(encoding="utf-8"))
    gate["gate_logic"]["pooled_recall_can_override_failed_cell"] = True
    gate_path.write_text(
        yaml.safe_dump(gate, sort_keys=False),
        encoding="utf-8",
    )
    protocol["recall_gate_contract"]["sha256"] = hashlib.sha256(
        gate_path.read_bytes()
    ).hexdigest()
    protocol_path.write_text(
        yaml.safe_dump(protocol, sort_keys=False),
        encoding="utf-8",
    )
    rebound, audit_path = _write_rebound_audit(
        tmp_path,
        result,
        protocol_path,
        name="changed-methodology.json",
    )

    with pytest.raises(ValueError, match="recall gate methodology"):
        load_neighbor_audit_receipt(
            audit_path,
            protocol_path=protocol_path,
            expected_audit_sha256=rebound.sha256,
            expected_protocol_sha256=hashlib.sha256(
                protocol_path.read_bytes()
            ).hexdigest(),
        )


@pytest.mark.parametrize(
    "mutation",
    ("exact_only", "draft_status"),
)
def test_receipt_rejects_candidate_protocol_without_ann_authorization(
    tmp_path: Path,
    mutation: str,
) -> None:
    result, *_, protocol_path = _frozen_result(tmp_path)
    protocol = yaml.safe_load(
        protocol_path.read_text(encoding="utf-8")
    )
    candidate_path = (
        protocol_path.parent
        / protocol["candidate_protocol"]["path"]
    )
    candidate = yaml.safe_load(
        candidate_path.read_text(encoding="utf-8")
    )
    if mutation == "exact_only":
        candidate["discovery_contract"]["pairwise_processing"] = (
            "exact_blockwise"
        )
    else:
        candidate["status"] = "preregistered-draft"
    candidate_path.write_text(
        yaml.safe_dump(candidate, sort_keys=False),
        encoding="utf-8",
    )
    protocol["candidate_protocol"]["sha256"] = hashlib.sha256(
        candidate_path.read_bytes()
    ).hexdigest()
    protocol_path.write_text(
        yaml.safe_dump(protocol, sort_keys=False),
        encoding="utf-8",
    )
    rebound, audit_path = _write_rebound_audit(
        tmp_path,
        result,
        protocol_path,
        name=f"candidate-{mutation}.json",
    )

    with pytest.raises(
        ValueError,
        match="does not authorize receipt-gated approximate discovery",
    ):
        load_neighbor_audit_receipt(
            audit_path,
            protocol_path=protocol_path,
            expected_audit_sha256=rebound.sha256,
            expected_protocol_sha256=hashlib.sha256(
                protocol_path.read_bytes()
            ).hexdigest(),
        )


def test_receipt_rejects_duplicate_protocol_or_gate_keys(
    tmp_path: Path,
) -> None:
    result, *_, protocol_path = _frozen_result(tmp_path)
    audit_path = tmp_path / "audit.json"
    _write_atlas_audit(result, audit_path)
    protocol_path.write_text(
        protocol_path.read_text(encoding="utf-8") + "status: frozen\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate key"):
        load_neighbor_audit_receipt(
            audit_path,
            protocol_path=protocol_path,
            expected_audit_sha256=result.sha256,
            expected_protocol_sha256=hashlib.sha256(
                protocol_path.read_bytes()
            ).hexdigest(),
        )

    gate_case = tmp_path / "gate-case" / "nested"
    gate_case.mkdir(parents=True)
    result, *_, protocol_path = _frozen_result(gate_case)
    protocol = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
    gate_path = protocol_path.parent / protocol["recall_gate_contract"]["path"]
    gate_path.write_text(
        gate_path.read_text(encoding="utf-8") + "status: frozen\n",
        encoding="utf-8",
    )
    protocol["recall_gate_contract"]["sha256"] = hashlib.sha256(
        gate_path.read_bytes()
    ).hexdigest()
    protocol_path.write_text(
        yaml.safe_dump(protocol, sort_keys=False),
        encoding="utf-8",
    )
    rebound, audit_path = _write_rebound_audit(
        gate_case,
        result,
        protocol_path,
        name="duplicate-gate.json",
    )
    with pytest.raises(ValueError, match="duplicate key"):
        load_neighbor_audit_receipt(
            audit_path,
            protocol_path=protocol_path,
            expected_audit_sha256=rebound.sha256,
            expected_protocol_sha256=hashlib.sha256(
                protocol_path.read_bytes()
            ).hexdigest(),
        )
