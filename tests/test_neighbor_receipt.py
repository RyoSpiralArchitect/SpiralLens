from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import yaml

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
from spirallens.neighbors import (
    NeighborBackendDescriptor,
    NeighborIndexBuildReceipt,
    NeighborPair,
    NeighborQuery,
    canonical_json_sha256,
    state_matrix_sha256,
)


class PreparedAllPairsBackend:
    def __init__(
        self,
        states: np.ndarray,
        *,
        row_identity_sha256: str,
        comparison_group: str,
        recipe: str = "all-pairs-v1",
    ) -> None:
        states_sha256 = state_matrix_sha256(states)
        self._index_bytes = json.dumps(
            {
                "recipe": recipe,
                "states_sha256": states_sha256,
                "row_identity_sha256": row_identity_sha256,
                "comparison_group": comparison_group,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        index_sha256 = hashlib.sha256(self._index_bytes).hexdigest()
        self._descriptor = NeighborBackendDescriptor(
            backend_id="tests.prepared-all-pairs",
            backend_version="1",
            kind="approximate",
            deterministic=True,
            parameters=(
                ("comparison_group", comparison_group),
                ("hidden_size", int(states.shape[1])),
                ("index_sha256", index_sha256),
                (
                    "promotion_config_sha256",
                    hashlib.sha256(recipe.encode("utf-8")).hexdigest(),
                ),
                ("row_count", int(states.shape[0])),
                ("row_identity_sha256", row_identity_sha256),
                ("seed", 0),
                ("states_dtype", str(states.dtype)),
                ("states_sha256", states_sha256),
                ("thread_count", 1),
            ),
            runtime=(("runtime", "pytest"),),
        )
        self._receipt = NeighborIndexBuildReceipt(
            backend=self._descriptor,
            states_sha256=states_sha256,
            row_identity_sha256=row_identity_sha256,
            index_sha256=index_sha256,
            comparison_group=comparison_group,
            row_count=int(states.shape[0]),
            hidden_size=int(states.shape[1]),
            states_dtype=str(states.dtype),
        )

    @property
    def descriptor(self) -> NeighborBackendDescriptor:
        return self._descriptor

    @property
    def build_receipt(self) -> NeighborIndexBuildReceipt:
        return self._receipt

    def export_index_bytes(self) -> bytes:
        return self._index_bytes

    def iter_pairs(self, states, *, query):
        del states
        query_scope = (
            None
            if query.query_indices is None
            else set(query.query_indices)
        )
        for left_index in range(self._receipt.row_count):
            for right_index in range(
                left_index + 1,
                self._receipt.row_count,
            ):
                if (
                    query_scope is None
                    or left_index in query_scope
                    or right_index in query_scope
                ):
                    yield NeighborPair(left_index, right_index, 0.0)


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
    audit_config = NeighborAuditConfig()
    selection = NeighborQuerySelectionContract(
        seed=7,
        count=states.shape[0],
        global_row_key_sha256=row_identity_sha256,
    )
    candidate_path = tmp_path / "candidate.yaml"
    candidate_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "spirallens.protocol.v0.1",
                "protocol_id": "frozen-candidate-v0.1",
                "status": "frozen",
                "claim_ceiling": 1,
                "candidate_search": candidate_config.to_dict(),
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    protocol_path = tmp_path / "neighbor.yaml"
    protocol_document = {
        "schema_version": "spirallens.neighbor-audit-protocol.v0.1",
        "protocol_id": "frozen-neighbor-v0.1",
        "status": "frozen",
        "audit_scope": {"comparison_group": "layer_index=0"},
        "candidate_protocol": {
            "path": candidate_path.name,
            "sha256": hashlib.sha256(
                candidate_path.read_bytes()
            ).hexdigest(),
            "declared_id": "frozen-candidate-v0.1",
        },
        "retrieval_contract": {
            "input": "resid_pre",
            "metric": "cosine",
            "drift_available_to_backend": False,
            "decoded_strings_available_to_backend": False,
            "semantic_annotation_available_to_backend": False,
            "sae_annotation_available_to_backend": False,
            "projected_coordinates_available_to_backend": False,
        },
        "subject_backend": {
            "backend_id": "tests.prepared-all-pairs",
            "backend_version": "1",
            "kind_required_for_full_vocabulary": "approximate",
            "candidate_persistence_without_audit_receipt": (
                "forbidden"
            ),
            "config": {"seed": 0, "thread_count": 1},
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
            "backend_score_used_for_gate": False,
            "false_persistable_candidates_allowed": 0,
        },
        "audit": {
            "primary_metric": "candidate_boundary_recall",
            "candidate_boundary_recall_min": (
                audit_config.candidate_recall_min
            ),
            "repeats": audit_config.repeats,
            "repeat_mode": "independent_cold_rebuild",
            "minimum_reference_candidates": (
                audit_config.minimum_reference_candidates
            ),
            "missing_pair_sample_limit": (
                audit_config.missing_pair_sample_limit
            ),
            "zero_reference_candidates": "insufficient",
            "full_vocabulary_backend_promoted_by_this_protocol": True,
        },
        "claim_boundary": {
            "semantics_free": True,
            "candidate_is_not_verified_vortex": True,
            "passing_audit_proves_retrieval_coverage_only": True,
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
    }
    result = audit_neighbor_backend(
        states,
        drifts,
        subject_backend_factory=lambda snapshot: PreparedAllPairsBackend(
            snapshot,
            row_identity_sha256=row_identity_sha256,
            comparison_group="layer_index=0",
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


def _target(
    result,
    states,
    drifts,
    row_identity_sha256,
    manifest_sha256,
    receipt,
):
    backend = PreparedAllPairsBackend(
        states,
        row_identity_sha256=row_identity_sha256,
        comparison_group="layer_index=0",
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
    write_neighbor_audit(result, audit_path)
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
    with pytest.raises(ValueError, match="drifts"):
        receipt.validate_target(
            replace(target, drifts_sha256="f" * 64)
        )
    reconstructed = NeighborAuditReceipt.from_dict(receipt.to_dict())
    assert reconstructed.verified is False
    with pytest.raises(ValueError, match="verified audit/protocol"):
        reconstructed.validate_target(target)
    malformed = receipt.to_dict()
    malformed["row_count"] += 1
    with pytest.raises(ValueError, match="index build receipt"):
        NeighborAuditReceipt.from_dict(malformed)
    noncanonical = receipt.to_dict()
    noncanonical["row_count"] = float(noncanonical["row_count"])
    with pytest.raises(TypeError, match="row_count must be an integer"):
        NeighborAuditReceipt.from_dict(noncanonical)


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
        write_neighbor_audit(forged, audit_path)
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
    write_neighbor_audit(result, audit_path)

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
