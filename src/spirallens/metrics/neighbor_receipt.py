"""Promotion receipts for approximate-neighbor candidate persistence."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json
from numbers import Integral
from pathlib import Path
from typing import Mapping

import yaml

from spirallens.neighbors import (
    FAISS_HNSW_BACKEND_ID,
    NeighborBackendDescriptor,
    NeighborIndexBuildReceipt,
    NeighborQuery,
    canonical_json_sha256,
)

from .candidate_pairs import (
    EXACT_RERANK_CONTRACT_VERSION,
    CandidateSearchConfig,
)
from .neighbor_audit import (
    BUILTIN_FAISS_AUDIT_RUNNER_CONTRACT,
    COVERAGE_EVALUATOR_VERSION,
    LOCAL_RECALL_CONTRACT_VERSION,
    NeighborAuditConfig,
    NeighborAuditResult,
    load_neighbor_audit_result,
)


NEIGHBOR_AUDIT_RECEIPT_SCHEMA_VERSION = (
    "spirallens.neighbor-audit-receipt.v0.2"
)
NEIGHBOR_AUDIT_PROTOCOL_SCHEMA_VERSION = (
    "spirallens.neighbor-audit-protocol.v0.2"
)
QUALIFIED_NEIGHBOR_AUDIT_PROTOCOL_SCHEMA_VERSION = (
    "spirallens.neighbor-audit-protocol.v0.3"
)
FRESH_SUBPROCESS_NEIGHBOR_AUDIT_PROTOCOL_SCHEMA_VERSION = (
    "spirallens.neighbor-audit-protocol.v0.4"
)
QUALIFIED_NEIGHBOR_AUDIT_PROTOCOL_SCHEMA_VERSIONS = {
    QUALIFIED_NEIGHBOR_AUDIT_PROTOCOL_SCHEMA_VERSION,
    FRESH_SUBPROCESS_NEIGHBOR_AUDIT_PROTOCOL_SCHEMA_VERSION,
}
SUPPORTED_NEIGHBOR_AUDIT_PROTOCOL_SCHEMA_VERSIONS = {
    NEIGHBOR_AUDIT_PROTOCOL_SCHEMA_VERSION,
    *QUALIFIED_NEIGHBOR_AUDIT_PROTOCOL_SCHEMA_VERSIONS,
}
V0_4_QUALIFICATION_SCHEMA_VERSION = (
    "spirallens.faiss-hnsw-range-qualification.v0.2"
)
V0_4_QUALIFICATION_PATH = (
    "protocols/"
    "pythia70_slot_only_001_layer0_faiss_range_qualification_v0_2.json"
)
REQUIRED_COVERAGE_GATES = (
    "aggregate",
    "query_local",
    "density_macro",
    "density_boundary_joint",
    "determinism",
)
_VERIFIED_RECEIPT_TOKEN = object()


def _qualification_contract(
    schema_version: object,
) -> tuple[str, str | None] | None:
    if schema_version == QUALIFIED_NEIGHBOR_AUDIT_PROTOCOL_SCHEMA_VERSION:
        return (
            "spirallens.faiss-hnsw-range-qualification.v0.1",
            None,
        )
    if (
        schema_version
        == FRESH_SUBPROCESS_NEIGHBOR_AUDIT_PROTOCOL_SCHEMA_VERSION
    ):
        return V0_4_QUALIFICATION_SCHEMA_VERSION, V0_4_QUALIFICATION_PATH
    return None


def _expected_promotion_readiness(
    *,
    qualified_protocol: bool,
    frozen: bool,
) -> dict[str, bool]:
    readiness = {
        "receipt_mechanism_implemented": True,
        "full_index_subset_query_audit_implemented": True,
        "frozen_recall_gate_methodology_available": True,
        "query_local_worst_case_recall_gate_implemented": True,
    }
    if qualified_protocol:
        readiness["production_shape_subprocess_qualified"] = frozen
    readiness.update(
        {
            "atlas_execution_bindings_frozen": frozen,
            "tracked_protocol_can_issue_persistence_receipt": frozen,
        }
    )
    return readiness


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""

    def construct_mapping(
        self,
        node: yaml.Node,
        deep: bool = False,
    ) -> object:
        if not isinstance(node, yaml.MappingNode):
            raise yaml.constructor.ConstructorError(
                None,
                None,
                "expected a mapping node",
                node.start_mark,
            )
        self.flatten_mapping(node)
        mapping: dict[object, object] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                duplicate = key in mapping
            except TypeError as error:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found an unhashable mapping key",
                    key_node.start_mark,
                ) from error
            if duplicate:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"found duplicate key {key!r}",
                    key_node.start_mark,
                )
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def _strict_yaml_load(payload_bytes: bytes, *, label: str) -> object:
    try:
        return yaml.load(payload_bytes, Loader=_UniqueKeySafeLoader)
    except yaml.YAMLError as error:
        raise ValueError(f"{label} YAML is invalid: {error}") from error


def _require_sha256(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def neighbor_query_boundary_dict(
    query: NeighborQuery,
) -> dict[str, object]:
    """Return the query contract without its selected row scope."""

    payload = query.to_dict()
    payload.pop("query_indices")
    return payload


def _load_protocol_mapping(
    path: Path,
) -> tuple[bytes, Mapping[str, object]]:
    protocol_bytes = path.read_bytes()
    protocol = _strict_yaml_load(
        protocol_bytes,
        label=f"neighbor audit protocol {path}",
    )
    if not isinstance(protocol, Mapping):
        raise ValueError(
            "neighbor audit protocol must contain a mapping"
        )
    return protocol_bytes, protocol


def _resolve_protocol_reference(
    protocol_path: Path,
    declared_path: object,
) -> Path:
    if not isinstance(declared_path, str) or not declared_path:
        raise ValueError(
            "candidate protocol path must be a non-empty string"
        )
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
            "candidate protocol reference does not resolve uniquely"
        )
    return existing[0]


def _candidate_config_from_bytes(
    payload_bytes: bytes,
    *,
    layer_index: int,
    require_frozen: bool = True,
) -> tuple[Mapping[str, object], CandidateSearchConfig]:
    payload = _strict_yaml_load(
        payload_bytes,
        label="candidate protocol",
    )
    if not isinstance(payload, Mapping):
        raise ValueError("candidate protocol must contain a mapping")
    expected_top_level = {
        "schema_version",
        "protocol_id",
        "status",
        "claim_ceiling",
        "scope",
        "candidate_search",
        "discovery_contract",
        "required_followup_before_level_2",
        "semantic_evaluation",
    }
    expected_scope = {
        "discovery_unit": [
            "token_id",
            "fixed_context_ids",
            "token_position",
            "layer_index",
        ],
        "pythia_70m_role": "plumbing_smoke",
        "pythia_160m_role": "first_scientific_target",
        "atlas_schema_version": "spirallens.activation_atlas.v2",
        "excluded_from_v0_2": [
            "semantic_labels_during_discovery",
            "sae_features_during_discovery",
            "projected_curl",
            "training_checkpoint_trajectory",
            "transfer_operator",
        ],
    }
    expected_discovery_contract = {
        "input_state": "resid_pre",
        "update_vector": "resid_post_minus_resid_pre",
        "pairwise_processing": (
            "exact_or_verified_receipt_gated_approximate"
        ),
        "exact_backend": {
            "backend_id": "spirallens.exact-blockwise-reference",
            "row_guard": "fail_loud_above_10000",
        },
        "approximate_backend": {
            "allowed_only_with_verified_neighbor_audit_receipt": True,
            "receipt_scope": "same_full_input_index_group",
            "full_index_required": True,
            "exact_rerank_required": True,
            "persistence_without_verified_receipt": "forbidden",
        },
        "full_pair_matrix_persisted": False,
        "semantic_annotation_used": False,
        "sae_annotation_used": False,
        "projection_used": False,
        "output_record_name": "candidate",
        "candidate_is_not_verified_vortex": True,
        "zero_candidate_run_is_valid": True,
    }
    expected_followup = [
        "basis_reparameterization",
        "orientation_reversal",
        "radius_sweep",
        "sampling_density_sweep",
        "rope_accounting",
        "layernorm_accounting",
        "fixed_routing_accounting",
        "matched_null",
    ]
    expected_semantic_evaluation = {
        "stage": "post_discovery_only",
        "storage": "separate_sha256_bound_sidecar",
        "required_split_for_confirmatory_claim": "held_out",
    }
    if (
        set(payload) != expected_top_level
        or payload.get("schema_version")
        != "spirallens.candidate-protocol.v0.2"
        or not isinstance(payload.get("protocol_id"), str)
        or not payload["protocol_id"]
        or payload.get("status")
        not in {"preregistered-draft", "frozen"}
        or (
            require_frozen
            and payload.get("status") != "frozen"
        )
        or payload.get("claim_ceiling") != 1
        or payload.get("scope") != expected_scope
        or payload.get("discovery_contract")
        != expected_discovery_contract
        or payload.get("required_followup_before_level_2")
        != expected_followup
        or payload.get("semantic_evaluation")
        != expected_semantic_evaluation
    ):
        raise ValueError(
            "candidate protocol does not authorize receipt-gated "
            "approximate discovery"
        )
    search = payload.get("candidate_search")
    if not isinstance(search, Mapping):
        raise ValueError(
            "candidate protocol is missing candidate_search"
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
    declared_config = CandidateSearchConfig(**values)
    if declared_config.layer_indices not in {
        None,
        (layer_index,),
    }:
        raise ValueError(
            "candidate protocol layer scope differs from audit layer"
        )
    config = replace(declared_config, layer_indices=(layer_index,))
    return payload, config


def validate_recall_gate_contract(
    *,
    audit_config: NeighborAuditConfig,
    protocol_path: Path,
    protocol: Mapping[str, object],
) -> tuple[Path, bytes, Mapping[str, object]]:
    """Validate the separately frozen local-recall methodology contract."""

    if not isinstance(audit_config, NeighborAuditConfig):
        raise TypeError("audit_config must be a NeighborAuditConfig")
    binding = protocol.get("recall_gate_contract")
    if (
        not isinstance(binding, Mapping)
        or set(binding) != {"path", "sha256", "gate_id"}
    ):
        raise ValueError(
            "frozen protocol is missing an exact recall_gate_contract binding"
        )
    gate_path = _resolve_protocol_reference(
        protocol_path,
        binding.get("path"),
    )
    gate_bytes = gate_path.read_bytes()
    if hashlib.sha256(gate_bytes).hexdigest() != binding.get("sha256"):
        raise ValueError(
            "recall gate bytes differ from frozen protocol binding"
        )
    gate = _strict_yaml_load(gate_bytes, label="recall gate")
    if not isinstance(gate, Mapping):
        raise ValueError("recall gate must contain a mapping")
    expected_top_level = {
        "schema_version",
        "gate_id",
        "status",
        "local_recall_contract",
        "methodology",
        "density",
        "boundary",
        "thresholds",
        "support",
        "gate_logic",
        "evidence",
        "claim_boundary",
    }
    if (
        set(gate) != expected_top_level
        or gate.get("schema_version")
        != "spirallens.neighbor-recall-gate.v0.1"
        or gate.get("gate_id") != binding.get("gate_id")
        or gate.get("status") != "frozen"
        or gate.get("local_recall_contract")
        != LOCAL_RECALL_CONTRACT_VERSION
    ):
        raise ValueError(
            "recall gate identity differs from its frozen binding"
        )

    expected_methodology = {
        "subject_output_unit": "canonical_unordered_global_row_pair",
        "reference_retrieval_set": (
            "exact_state_boundary_pairs_touching_selected_queries"
        ),
        "reference_candidate_set": (
            "exact_reranked_reference_candidates"
        ),
        "subject_candidate_set": (
            "subject_proposals_after_shared_exact_rerank"
        ),
        "subject_candidates_must_be_subset_of_reference_candidates": True,
        "query_local_denominator": (
            "exact_reference_candidate_incidence"
        ),
        "sampled_query_pair_ownership": {
            "query_local": "count_once_for_each_selected_endpoint",
            "pooled_pair_sets": "count_once",
        },
        "zero_denominator_query": "null_not_pass",
        "low_support_query_removed_from_worst_case": False,
        "repeat_pooling_or_union_override": "forbidden",
    }
    expected_density = {
        "basis": "exact_reference_retrieval_incident_degree",
        "subject_output_used_for_assignment": False,
        "eligible_queries": (
            "selected_queries_with_positive_reference_candidate_degree"
        ),
        "assignment": "stable_equal_count_rank",
        "sort_key": [
            "exact_reference_retrieval_incident_degree_ascending",
            "global_row_index_ascending",
        ],
        "stratum_id": "density_rank_index_of_count",
        "aggregation": "macro_query_local_candidate_recall",
        "micro_recall_role": "diagnostic_only",
    }
    expected_boundary = {
        "candidate_universe": "exact_reranked_reference_candidates",
        "score_source": "original_states_canonical_float64_cosine",
        "subject_score_used_for_assignment": False,
        "slack": "exact_cosine_minus_candidate_cosine_min",
        "strata": {
            "cosine_shell": {
                "lower": 0.0,
                "lower_inclusive": True,
                "upper_source": "thresholds.boundary_shell_width",
                "upper_inclusive": True,
            },
            "interior": {
                "lower_source": "thresholds.boundary_shell_width",
                "lower_inclusive": False,
                "upper": "unbounded",
            },
        },
        "joint_cells": "density_stratum_x_boundary_stratum",
        "pair_membership_within_joint_cell": "unique",
        "selected_pair_may_enter_two_density_cells": True,
    }
    config = audit_config
    expected_thresholds = {
        "aggregate_candidate_recall_min": config.candidate_recall_min,
        "query_local_recall_min": config.query_local_recall_min,
        "density_macro_and_joint_stratum_recall_min": (
            config.stratum_recall_min
        ),
        "boundary_shell_width": config.boundary_shell_width,
        "boundary_shell_width_must_equal_subject_score_margin": True,
        "repeats": config.repeats,
        "repeat_mode": "independent_cold_rebuild_same_frozen_seed",
    }
    expected_support = {
        "minimum_reference_candidates": (
            config.minimum_reference_candidates
        ),
        "minimum_eligible_queries": config.minimum_eligible_queries,
        "minimum_eligible_query_fraction": (
            config.minimum_eligible_query_fraction
        ),
        "density_strata_count": config.density_strata_count,
        "minimum_eligible_queries_per_density_stratum": (
            config.minimum_eligible_queries_per_density_stratum
        ),
        "minimum_reference_candidates_per_joint_stratum": (
            config.minimum_reference_candidates_per_stratum
        ),
        "zero_reference_candidates": "insufficient",
        "empty_required_cell": "insufficient",
        "under_supported_required_cell": "insufficient",
    }
    expected_gate_logic = {
        "required": [
            "aggregate_candidate_recall_each_repeat",
            "query_local_recall_each_eligible_query_each_repeat",
            "density_macro_recall_each_stratum_each_repeat",
            "density_boundary_joint_recall_each_cell_each_repeat",
            "deterministic_repeat_membership",
            "support_requirements",
        ],
        "overall_precedence": [
            "any_known_failure_is_fail",
            "otherwise_any_missing_or_insufficient_support_is_insufficient",
            "otherwise_all_required_gates_pass",
        ],
        "worst_case_reduction": (
            "minimum_over_all_required_cells_and_repeats"
        ),
        "pooled_recall_can_override_failed_cell": False,
        "missing_or_not_run_can_issue_receipt": False,
    }
    expected_evidence = {
        "evaluator_contract": COVERAGE_EVALUATOR_VERSION,
        "evaluator_runtime_bound_in_audit_identity": [
            "spirallens_version",
            "numpy_version",
        ],
        "query_record_fields": [
            "query_index",
            "reference_retrieval_degree",
            "reference_candidate_degree",
            "reference_candidate_sha256",
            "density_stratum",
            "repeat_match_counts",
            "repeat_recall",
        ],
        "joint_stratum_record_fields": [
            "stratum_id",
            "reference_candidate_count",
            "reference_candidate_sha256",
            "repeat_match_counts",
            "repeat_recall",
        ],
        "zero_reference_query_count_required": True,
        "zero_reference_query_indices_sha256_required": True,
        "coverage_contract_sha256_required": True,
        "coverage_evidence_sha256_required": True,
        "audit_and_protocol_digests_must_be_supplied_out_of_band_for_receipt": (
            True
        ),
    }
    expected_claim_boundary = {
        "passing_gate_proves_retrieval_coverage_only": True,
        "semantic_claim": False,
        "topological_claim": False,
        "causal_claim": False,
        "backend_audit_outcome_declared_here": False,
    }
    expected_sections = {
        "methodology": expected_methodology,
        "density": expected_density,
        "boundary": expected_boundary,
        "thresholds": expected_thresholds,
        "support": expected_support,
        "gate_logic": expected_gate_logic,
        "evidence": expected_evidence,
        "claim_boundary": expected_claim_boundary,
    }
    if any(
        not isinstance(gate.get(name), Mapping)
        or dict(gate[name]) != expected
        for name, expected in expected_sections.items()
    ):
        raise ValueError(
            "recall gate methodology or thresholds differ from the audit"
        )
    if gate_path.read_bytes() != gate_bytes:
        raise ValueError(
            "recall gate bytes changed during receipt validation"
        )
    return gate_path, gate_bytes, gate


def validate_neighbor_protocol_static_contract(
    protocol: Mapping[str, object],
) -> None:
    """Reject ambiguous or contradictory neighbor protocol declarations."""

    schema_version = protocol.get("schema_version")
    qualification_contract = _qualification_contract(schema_version)
    qualified_protocol = qualification_contract is not None
    expected_top_level = {
        "schema_version",
        "protocol_id",
        "status",
        "claim_ceiling",
        "recall_gate_contract",
        "audit_scope",
        "candidate_protocol",
        "retrieval_contract",
        "reference_backend",
        "subject_backend",
        "query_sampling",
        "exact_rerank",
        "audit",
        "claim_boundary",
        "promotion_readiness",
        "deviations",
    }
    if qualified_protocol:
        expected_top_level.add("backend_qualification")
    status = protocol.get("status")
    if (
        set(protocol) != expected_top_level
        or schema_version
        not in SUPPORTED_NEIGHBOR_AUDIT_PROTOCOL_SCHEMA_VERSIONS
        or not isinstance(protocol.get("protocol_id"), str)
        or not protocol["protocol_id"]
        or status not in {"preregistered-draft", "frozen"}
        or protocol.get("claim_ceiling") != 1
        or protocol.get("deviations") != []
    ):
        raise ValueError(
            "neighbor protocol top-level contract is invalid"
        )
    recall_binding = protocol.get("recall_gate_contract")
    candidate_binding = protocol.get("candidate_protocol")
    if (
        not isinstance(recall_binding, Mapping)
        or set(recall_binding) != {"path", "sha256", "gate_id"}
        or not isinstance(candidate_binding, Mapping)
        or set(candidate_binding)
        != {"path", "sha256", "declared_id"}
    ):
        raise ValueError(
            "neighbor protocol reference bindings are invalid"
        )

    expected_retrieval = {
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
    }
    expected_reference = {
        "backend_id": "spirallens.exact-blockwise-reference",
        "backend_version": "0.1",
        "kind": "exact",
        "deterministic": True,
        "descriptor_sha256_bound_in_audit_identity": True,
        "runtime_version_bound_in_descriptor": True,
        "maximum_all_pair_rows": 10000,
        "maximum_exact_comparisons": 50000000,
        "inclusive_thresholds": True,
    }
    expected_rerank = {
        "contract": EXACT_RERANK_CONTRACT_VERSION,
        "required_before_persist": True,
        "source_values": "original_atlas_values_cast_to_float64",
        "backend_score_used_for_gate": False,
        "false_persistable_candidates_allowed": 0,
    }
    expected_claim = {
        "semantics_free": True,
        "candidate_is_not_verified_vortex": True,
        "passing_audit_proves_retrieval_coverage_only": True,
        "approximate_backend_currently_audited": False,
    }
    if (
        protocol.get("retrieval_contract") != expected_retrieval
        or protocol.get("reference_backend") != expected_reference
        or protocol.get("exact_rerank") != expected_rerank
        or protocol.get("claim_boundary") != expected_claim
    ):
        raise ValueError(
            "neighbor protocol static methodology is invalid"
        )

    subject = protocol.get("subject_backend")
    expected_backend_version = "0.2" if qualified_protocol else "0.1"
    expected_required_provenance = [
        "backend_id",
        "backend_version",
        "backend_config",
        "runtime_versions",
        "seed",
        "thread_count",
        "index_digest",
    ]
    if qualified_protocol:
        expected_required_provenance.extend(
            [
                "qualification_receipt_digest",
                "qualification_fixture_digest",
            ]
        )
    expected_subject_fields = {
        "status",
        "backend_id",
        "backend_version",
        "distribution",
        "distribution_version",
        "kind_required_for_full_vocabulary",
        "optional_dependency_only",
        "candidate_persistence_without_audit_receipt",
        "config",
        "required_provenance",
    }
    if (
        not isinstance(subject, Mapping)
        or set(subject) != expected_subject_fields
        or subject.get("status")
        != "implementation_selected_unpromoted"
        or subject.get("backend_id") != FAISS_HNSW_BACKEND_ID
        or str(subject.get("backend_version"))
        != expected_backend_version
        or subject.get("distribution") != "faiss-cpu"
        or str(subject.get("distribution_version")) != "1.14.3"
        or subject.get("kind_required_for_full_vocabulary")
        != "approximate"
        or subject.get("optional_dependency_only") is not True
        or subject.get("candidate_persistence_without_audit_receipt")
        != "forbidden"
        or not isinstance(subject.get("config"), Mapping)
        or subject.get("required_provenance")
        != expected_required_provenance
    ):
        raise ValueError(
            "neighbor protocol subject declaration is invalid"
        )

    scope = protocol.get("audit_scope")
    sampling = protocol.get("query_sampling")
    readiness = protocol.get("promotion_readiness")
    if not all(
        isinstance(value, Mapping)
        for value in (scope, sampling, readiness)
    ):
        raise ValueError(
            "neighbor protocol execution binding is invalid"
        )
    assert isinstance(scope, Mapping)
    assert isinstance(sampling, Mapping)
    assert isinstance(readiness, Mapping)
    if status == "preregistered-draft":
        expected_scope = {
            "comparison_group": None,
            "binding_rule": "must_be_filled_before_status_frozen",
        }
        if (
            set(sampling)
            != {
                "method",
                "seed",
                "count",
                "global_row_key_sha256",
                "binding_rule",
            }
            or sampling.get("global_row_key_sha256") is not None
            or sampling.get("binding_rule")
            != "must_be_filled_before_status_frozen"
            or dict(readiness)
            != _expected_promotion_readiness(
                qualified_protocol=qualified_protocol,
                frozen=False,
            )
        ):
            raise ValueError(
                "draft neighbor protocol binding is invalid"
            )
    else:
        expected_scope = {
            "comparison_group": scope.get("comparison_group")
        }
        if (
            set(scope) != {"comparison_group"}
            or not isinstance(scope.get("comparison_group"), str)
            or not scope["comparison_group"]
            or set(sampling)
            != {
                "method",
                "seed",
                "count",
                "global_row_key_sha256",
            }
            or not isinstance(
                sampling.get("global_row_key_sha256"),
                str,
            )
            or dict(readiness)
            != _expected_promotion_readiness(
                qualified_protocol=qualified_protocol,
                frozen=True,
            )
        ):
            raise ValueError(
                "frozen neighbor protocol binding is invalid"
            )
    if qualified_protocol:
        qualification = protocol.get("backend_qualification")
        assert qualification_contract is not None
        qualification_schema_version, required_path = (
            qualification_contract
        )
        if not isinstance(qualification, Mapping):
            raise ValueError(
                "neighbor protocol backend qualification is invalid"
            )
        if status == "preregistered-draft":
            expected_qualification = {
                "schema_version": qualification_schema_version,
                "path": required_path,
                "sha256": None,
                "fixture_sha256": None,
                "binding_rule": "must_be_filled_before_status_frozen",
            }
        else:
            expected_qualification = {
                "schema_version": qualification_schema_version,
                "path": qualification.get("path"),
                "sha256": qualification.get("sha256"),
                "fixture_sha256": qualification.get(
                    "fixture_sha256"
                ),
            }
            if (
                not isinstance(qualification.get("path"), str)
                or not qualification["path"]
            ):
                raise ValueError(
                    "frozen backend qualification path is invalid"
                )
            if (
                required_path is not None
                and qualification.get("path") != required_path
            ):
                raise ValueError(
                    "frozen backend qualification path differs from "
                    "the versioned contract"
                )
            for field_name in ("sha256", "fixture_sha256"):
                _require_sha256(
                    qualification.get(field_name),
                    label=f"backend_qualification.{field_name}",
                )
        if dict(qualification) != expected_qualification:
            raise ValueError(
                "neighbor protocol backend qualification is invalid"
            )
    if (
        dict(scope) != expected_scope
        or sampling.get("method")
        != "sha256_ranked_global_indices"
        or isinstance(sampling.get("seed"), bool)
        or not isinstance(sampling.get("seed"), Integral)
        or isinstance(sampling.get("count"), bool)
        or not isinstance(sampling.get("count"), Integral)
        or sampling["count"] <= 0
    ):
        raise ValueError(
            "neighbor protocol query sampling is invalid"
        )


def _validate_promotion_protocol(
    result: NeighborAuditResult,
    *,
    protocol_path: Path,
    protocol_bytes: bytes,
    protocol: Mapping[str, object],
) -> tuple[str, str]:
    """Match every promotion-bearing protocol field to the audit."""

    validate_neighbor_protocol_static_contract(protocol)
    qualified_protocol = (
        _qualification_contract(protocol.get("schema_version")) is not None
    )
    expected_subject_backend_version = (
        "0.2" if qualified_protocol else "0.1"
    )
    if (
        protocol.get("protocol_id")
        != result.protocol_binding.protocol_id
        or protocol.get("status") != "frozen"
        or result.protocol_binding.status != "frozen"
        or hashlib.sha256(protocol_bytes).hexdigest()
        != result.protocol_binding.source_sha256
    ):
        raise ValueError(
            "audit result does not match the supplied frozen protocol"
        )
    if result.protocol_binding.deviations != tuple(
        sorted(set(protocol.get("deviations", ())))
    ):
        raise ValueError(
            "audit deviations differ from the frozen protocol"
        )
    gate_path, gate_bytes, _ = validate_recall_gate_contract(
        audit_config=result.audit_config,
        protocol_path=protocol_path,
        protocol=protocol,
    )
    gate_statuses = result.coverage_gate_statuses()
    if (
        set(gate_statuses) != set(REQUIRED_COVERAGE_GATES)
        or any(
            gate_statuses[name] != "pass"
            for name in REQUIRED_COVERAGE_GATES
        )
    ):
        raise ValueError(
            "all frozen aggregate, local, stratified, and determinism "
            "coverage gates must pass"
        )
    if (
        result.subject_runner_contract
        != BUILTIN_FAISS_AUDIT_RUNNER_CONTRACT
    ):
        raise ValueError(
            "persistence receipts require the built-in Faiss audit "
            "runner"
        )
    if (
        result.candidate_config.layer_indices is None
        or len(result.candidate_config.layer_indices) != 1
    ):
        raise ValueError(
            "promotion protocol must bind exactly one layer"
        )
    layer_index = result.candidate_config.layer_indices[0]
    expected_group = f"layer_index={layer_index}"
    scope = protocol.get("audit_scope")
    if (
        not isinstance(scope, Mapping)
        or set(scope) != {"comparison_group"}
        or scope.get("comparison_group") != expected_group
        or result.comparison_group != expected_group
    ):
        raise ValueError(
            "audit comparison group differs from frozen protocol"
        )

    candidate_binding = protocol.get("candidate_protocol")
    if (
        not isinstance(candidate_binding, Mapping)
        or set(candidate_binding)
        != {"path", "sha256", "declared_id"}
    ):
        raise ValueError(
            "frozen protocol is missing candidate_protocol"
        )
    candidate_path = _resolve_protocol_reference(
        protocol_path,
        candidate_binding.get("path"),
    )
    candidate_bytes = candidate_path.read_bytes()
    if hashlib.sha256(candidate_bytes).hexdigest() != (
        candidate_binding.get("sha256")
    ):
        raise ValueError(
            "candidate protocol bytes differ from frozen binding"
        )
    candidate_document, expected_candidate_config = (
        _candidate_config_from_bytes(
            candidate_bytes,
            layer_index=layer_index,
        )
    )
    if (
        candidate_binding.get("declared_id")
        != candidate_document.get("protocol_id")
        or expected_candidate_config != result.candidate_config
    ):
        raise ValueError(
            "effective candidate config differs from frozen protocol"
        )

    audit = protocol.get("audit")
    expected_audit = {
        "primary_metric": "candidate_boundary_recall",
        "candidate_boundary_recall_min": (
            result.audit_config.candidate_recall_min
        ),
        "query_local_recall_min": (
            result.audit_config.query_local_recall_min
        ),
        "stratum_recall_min": result.audit_config.stratum_recall_min,
        "repeats": result.audit_config.repeats,
        "repeat_mode": "independent_cold_rebuild",
        "minimum_reference_candidates": (
            result.audit_config.minimum_reference_candidates
        ),
        "minimum_eligible_queries": (
            result.audit_config.minimum_eligible_queries
        ),
        "minimum_eligible_query_fraction": (
            result.audit_config.minimum_eligible_query_fraction
        ),
        "density_strata_count": (
            result.audit_config.density_strata_count
        ),
        "minimum_eligible_queries_per_density_stratum": (
            result.audit_config
            .minimum_eligible_queries_per_density_stratum
        ),
        "boundary_shell_width": (
            result.audit_config.boundary_shell_width
        ),
        "minimum_reference_candidates_per_stratum": (
            result.audit_config.minimum_reference_candidates_per_stratum
        ),
        "missing_pair_sample_limit": (
            result.audit_config.missing_pair_sample_limit
        ),
        "zero_reference_candidates": "insufficient",
        "top_k_recall_role": "not_applicable_range_search",
        "pooled_recall_can_override_failed_group": False,
        "required_local_recall_contract": (
            LOCAL_RECALL_CONTRACT_VERSION
        ),
        "required_joint_strata": "density_rank_x_cosine_boundary",
        "issue_persistence_receipt_on_verified_pass": True,
        "protocol_binding_required": True,
        "source_identity_required": True,
    }
    if (
        not isinstance(audit, Mapping)
        or dict(audit) != expected_audit
    ):
        raise ValueError(
            "audit settings or promotion policy differ from the result"
        )

    sampling = protocol.get("query_sampling")
    selection = result.protocol_binding.query_selection
    if selection is None or not isinstance(sampling, Mapping):
        raise ValueError(
            "frozen protocol is missing query sampling provenance"
        )
    expected_sampling = {
        "method": "sha256_ranked_global_indices",
        "seed": selection.seed,
        "count": selection.count,
        "global_row_key_sha256": selection.global_row_key_sha256,
    }
    if dict(sampling) != expected_sampling:
        raise ValueError(
            "audit query selection differs from frozen protocol"
        )
    if result.query.query_indices != selection.select(result.row_count):
        raise ValueError(
            "audit query rows differ from frozen selection"
        )

    expected_reference = {
        "backend_id": "spirallens.exact-blockwise-reference",
        "backend_version": "0.1",
        "kind": "exact",
        "deterministic": True,
        "descriptor_sha256_bound_in_audit_identity": True,
        "runtime_version_bound_in_descriptor": True,
        "maximum_all_pair_rows": 10000,
        "maximum_exact_comparisons": 50000000,
        "inclusive_thresholds": True,
    }
    reference = protocol.get("reference_backend")
    if (
        not isinstance(reference, Mapping)
        or dict(reference) != expected_reference
    ):
        raise ValueError(
            "exact reference declaration differs from frozen protocol"
        )

    subject = protocol.get("subject_backend")
    subject_parameters = dict(result.subject_backend.parameters)
    subject_runtime = dict(result.subject_backend.runtime)
    expected_required_provenance = [
        "backend_id",
        "backend_version",
        "backend_config",
        "runtime_versions",
        "seed",
        "thread_count",
        "index_digest",
    ]
    if qualified_protocol:
        expected_required_provenance.extend(
            [
                "qualification_receipt_digest",
                "qualification_fixture_digest",
            ]
        )
    expected_subject_fields = {
        "status",
        "backend_id",
        "backend_version",
        "distribution",
        "distribution_version",
        "kind_required_for_full_vocabulary",
        "optional_dependency_only",
        "candidate_persistence_without_audit_receipt",
        "config",
        "required_provenance",
    }
    if (
        not isinstance(subject, Mapping)
        or set(subject) != expected_subject_fields
        or subject.get("status")
        != "implementation_selected_unpromoted"
        or result.subject_backend.backend_id
        != FAISS_HNSW_BACKEND_ID
        or result.subject_backend.backend_version
        != expected_subject_backend_version
        or subject.get("backend_id")
        != result.subject_backend.backend_id
        or str(subject.get("backend_version"))
        != result.subject_backend.backend_version
        or subject.get("kind_required_for_full_vocabulary")
        != "approximate"
        or subject.get("optional_dependency_only") is not True
        or subject.get("candidate_persistence_without_audit_receipt")
        != "forbidden"
        or subject.get("required_provenance")
        != expected_required_provenance
        or not isinstance(subject.get("config"), Mapping)
        or any(
            subject_parameters.get(key) != value
            for key, value in subject["config"].items()
        )
    ):
        raise ValueError(
            "subject backend differs from frozen protocol"
        )
    if subject_parameters.get("score_margin") != (
        result.audit_config.boundary_shell_width
    ):
        raise ValueError(
            "boundary shell width differs from the subject score margin"
        )
    if result.subject_backend.backend_id == (
        "spirallens.faiss-hnsw-range"
    ):
        from spirallens.neighbors import FaissHNSWConfig

        try:
            declared_faiss_config = FaissHNSWConfig(
                **dict(subject["config"])
            ).to_dict()
        except (TypeError, ValueError) as error:
            raise ValueError(
                "frozen Faiss config is incomplete or invalid"
            ) from error
        actual_faiss_config = {
            key: subject_parameters.get(key)
            for key in declared_faiss_config
        }
        if (
            subject.get("distribution") != "faiss-cpu"
            or str(subject.get("distribution_version")) != "1.14.3"
            or subject_runtime.get("faiss_version") != "1.14.3"
            or actual_faiss_config != declared_faiss_config
        ):
            raise ValueError(
                "Faiss distribution/runtime differs from frozen "
                "protocol"
            )
    if qualified_protocol:
        from spirallens.neighbors.faiss_qualification import (
            load_faiss_hnsw_qualification_receipt,
        )

        qualification = protocol.get("backend_qualification")
        if not isinstance(qualification, Mapping):
            raise ValueError(
                "frozen protocol lacks backend qualification"
            )
        qualification_path = _resolve_protocol_reference(
            protocol_path,
            qualification.get("path"),
        )
        receipt = load_faiss_hnsw_qualification_receipt(
            qualification_path,
            expected_sha256=qualification.get("sha256"),
        )
        if (
            receipt.fixture_sha256
            != qualification.get("fixture_sha256")
            or subject_parameters.get(
                "qualification_receipt_sha256"
            )
            != receipt.sha256
            or subject_parameters.get(
                "qualification_fixture_sha256"
            )
            != receipt.fixture_sha256
            or subject_parameters.get("range_call_batch_size") != 1
            or subject_runtime.get("faiss_native_sha256")
            != receipt.runtime["faiss_native_sha256"]
        ):
            raise ValueError(
                "subject backend qualification differs from the "
                "frozen protocol, receipt, or runtime"
            )

    retrieval = protocol.get("retrieval_contract")
    expected_retrieval = {
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
    }
    if (
        not isinstance(retrieval, Mapping)
        or dict(retrieval) != expected_retrieval
    ):
        raise ValueError(
            "retrieval isolation differs from frozen protocol"
        )
    rerank = protocol.get("exact_rerank")
    expected_rerank = {
        "contract": EXACT_RERANK_CONTRACT_VERSION,
        "required_before_persist": True,
        "source_values": "original_atlas_values_cast_to_float64",
        "backend_score_used_for_gate": False,
        "false_persistable_candidates_allowed": 0,
    }
    if (
        not isinstance(rerank, Mapping)
        or dict(rerank) != expected_rerank
    ):
        raise ValueError(
            "exact rerank policy differs from frozen protocol"
        )
    claim_boundary = protocol.get("claim_boundary")
    expected_claim_boundary = {
        "semantics_free": True,
        "candidate_is_not_verified_vortex": True,
        "passing_audit_proves_retrieval_coverage_only": True,
        "approximate_backend_currently_audited": False,
    }
    if (
        not isinstance(claim_boundary, Mapping)
        or dict(claim_boundary) != expected_claim_boundary
    ):
        raise ValueError(
            "claim boundary differs from frozen protocol"
        )
    promotion_readiness = protocol.get("promotion_readiness")
    expected_promotion_readiness = _expected_promotion_readiness(
        qualified_protocol=qualified_protocol,
        frozen=True,
    )
    if (
        not isinstance(promotion_readiness, Mapping)
        or dict(promotion_readiness) != expected_promotion_readiness
    ):
        raise ValueError(
            "promotion readiness does not authorize a persistence receipt"
        )
    if (
        candidate_path.read_bytes() != candidate_bytes
        or gate_path.read_bytes() != gate_bytes
        or protocol_path.read_bytes() != protocol_bytes
    ):
        raise ValueError(
            "protocol bytes changed during receipt validation"
        )
    candidate_protocol_id = candidate_document.get("protocol_id")
    if (
        not isinstance(candidate_protocol_id, str)
        or not candidate_protocol_id
    ):
        raise ValueError("candidate protocol ID is invalid")
    return (
        candidate_protocol_id,
        hashlib.sha256(candidate_bytes).hexdigest(),
    )


@dataclass(frozen=True)
class NeighborPersistenceTarget:
    """The exact full-input/group retrieval a receipt may authorize."""

    backend: NeighborBackendDescriptor
    build_receipt: NeighborIndexBuildReceipt
    candidate_config: CandidateSearchConfig
    candidate_protocol_id: str
    candidate_protocol_sha256: str
    query: NeighborQuery
    atlas_manifest_sha256: str
    atlas_run_id: str
    global_row_key_sha256: str
    source_run_id: str
    comparison_group: str
    states_sha256: str
    drifts_sha256: str
    row_count: int
    hidden_size: int
    states_dtype: str
    drifts_dtype: str

    def __post_init__(self) -> None:
        if self.backend.kind != "approximate":
            raise ValueError(
                "neighbor persistence target must use an approximate backend"
            )
        if self.build_receipt.backend != self.backend:
            raise ValueError(
                "target backend differs from its index build receipt"
            )
        if not isinstance(self.candidate_config, CandidateSearchConfig):
            raise TypeError(
                "candidate_config must be CandidateSearchConfig"
            )
        if not isinstance(self.query, NeighborQuery):
            raise TypeError("query must be NeighborQuery")
        if (
            not isinstance(self.candidate_protocol_id, str)
            or not self.candidate_protocol_id
        ):
            raise TypeError(
                "candidate_protocol_id must be a non-empty string"
            )
        _require_sha256(
            self.candidate_protocol_sha256,
            label="candidate_protocol_sha256",
        )
        if self.query.query_indices is not None:
            raise ValueError(
                "persistence target query must cover all rows"
            )
        for field_name in (
            "atlas_manifest_sha256",
            "global_row_key_sha256",
            "states_sha256",
            "drifts_sha256",
        ):
            _require_sha256(getattr(self, field_name), label=field_name)
        for field_name in (
            "atlas_run_id",
            "source_run_id",
            "comparison_group",
            "states_dtype",
            "drifts_dtype",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value:
                raise TypeError(f"{field_name} must be a non-empty string")
        if self.source_run_id != self.atlas_run_id:
            raise ValueError("target source_run_id must equal atlas_run_id")
        if (
            self.row_count != self.build_receipt.row_count
            or self.hidden_size != self.build_receipt.hidden_size
            or self.states_dtype != self.build_receipt.states_dtype
            or self.states_sha256 != self.build_receipt.states_sha256
            or self.global_row_key_sha256
            != self.build_receipt.row_identity_sha256
            or self.comparison_group
            != self.build_receipt.comparison_group
        ):
            raise ValueError(
                "target input/group differs from its index build receipt"
            )


@dataclass(frozen=True)
class NeighborAuditReceipt:
    """A pass-only authorization for one identical full index/group."""

    audit_sha256: str
    audit_identity_sha256: str
    protocol_binding_sha256: str
    protocol_source_sha256: str
    source_identity_sha256: str
    atlas_manifest_sha256: str
    atlas_run_id: str
    global_row_key_sha256: str
    source_run_id: str
    comparison_group: str
    states_sha256: str
    drifts_sha256: str
    row_count: int
    hidden_size: int
    states_dtype: str
    drifts_dtype: str
    subject_backend: NeighborBackendDescriptor
    subject_build_receipt: NeighborIndexBuildReceipt
    candidate_config_sha256: str
    candidate_protocol_id: str
    candidate_protocol_sha256: str
    audit_query_sha256: str
    query_boundary_sha256: str
    authorized_target_query_sha256: str
    query_selection_sha256: str
    coverage_contract_sha256: str
    coverage_evidence_sha256: str
    exact_rerank_contract: str = EXACT_RERANK_CONTRACT_VERSION
    schema_version: str = NEIGHBOR_AUDIT_RECEIPT_SCHEMA_VERSION
    _verification_token: object | None = field(
        default=None,
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        for field_name in (
            "audit_sha256",
            "audit_identity_sha256",
            "protocol_binding_sha256",
            "protocol_source_sha256",
            "source_identity_sha256",
            "atlas_manifest_sha256",
            "global_row_key_sha256",
            "states_sha256",
            "drifts_sha256",
            "candidate_config_sha256",
            "candidate_protocol_sha256",
            "audit_query_sha256",
            "query_boundary_sha256",
            "authorized_target_query_sha256",
            "query_selection_sha256",
            "coverage_contract_sha256",
            "coverage_evidence_sha256",
        ):
            _require_sha256(getattr(self, field_name), label=field_name)
        if self.schema_version != NEIGHBOR_AUDIT_RECEIPT_SCHEMA_VERSION:
            raise ValueError("neighbor audit receipt schema is invalid")
        if self.exact_rerank_contract != EXACT_RERANK_CONTRACT_VERSION:
            raise ValueError("neighbor audit receipt rerank contract is invalid")
        for field_name in ("row_count", "hidden_size"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, Integral):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
            object.__setattr__(self, field_name, int(value))
        if self.subject_backend.kind != "approximate":
            raise ValueError(
                "neighbor audit receipt subject must be approximate"
            )
        if self.subject_build_receipt.backend != self.subject_backend:
            raise ValueError(
                "receipt subject backend differs from its index build receipt"
            )
        build_binding = {
            "states_sha256": self.subject_build_receipt.states_sha256,
            "global_row_key_sha256": (
                self.subject_build_receipt.row_identity_sha256
            ),
            "comparison_group": (
                self.subject_build_receipt.comparison_group
            ),
            "row_count": self.subject_build_receipt.row_count,
            "hidden_size": self.subject_build_receipt.hidden_size,
            "states_dtype": self.subject_build_receipt.states_dtype,
        }
        if any(
            getattr(self, field_name) != expected
            for field_name, expected in build_binding.items()
        ):
            raise ValueError(
                "receipt input identity differs from its index build receipt"
            )
        if (
            not isinstance(self.candidate_protocol_id, str)
            or not self.candidate_protocol_id
        ):
            raise TypeError(
                "candidate_protocol_id must be a non-empty string"
            )
        for field_name in (
            "atlas_run_id",
            "source_run_id",
            "comparison_group",
            "states_dtype",
            "drifts_dtype",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value:
                raise TypeError(f"{field_name} must be a non-empty string")
        if self.source_run_id != self.atlas_run_id:
            raise ValueError("receipt source_run_id must equal atlas_run_id")

    @classmethod
    def _from_result(
        cls,
        result: NeighborAuditResult,
        *,
        protocol_path: str | Path,
    ) -> "NeighborAuditReceipt":
        """Build a receipt record after full protocol validation."""

        if not isinstance(result, NeighborAuditResult):
            raise TypeError("result must be NeighborAuditResult")
        protocol_source = Path(protocol_path).resolve()
        protocol_bytes, protocol = _load_protocol_mapping(
            protocol_source
        )
        (
            candidate_protocol_id,
            candidate_protocol_sha256,
        ) = _validate_promotion_protocol(
            result,
            protocol_path=protocol_source,
            protocol_bytes=protocol_bytes,
            protocol=protocol,
        )
        if result.status != "pass":
            raise ValueError("only a passing audit can produce a receipt")
        if result.protocol_binding.status != "frozen":
            raise ValueError(
                "audit protocol must be frozen before promotion"
            )
        if result.protocol_binding.deviations:
            raise ValueError(
                "audit deviations prevent promotion"
            )
        selection = result.protocol_binding.query_selection
        if selection is None:
            raise ValueError(
                "promotion requires a preregistered query selection"
            )
        if result.query.query_indices is None:
            raise ValueError(
                "promotion audit must use a preregistered query subset"
            )
        source = json.loads(result.source_identity_json)
        if source.get("kind") != "atlas_subset":
            raise ValueError(
                "only an atlas_subset audit can authorize persistence"
            )
        if result.source_run_id != source.get("atlas_run_id"):
            raise ValueError(
                "audit source_run_id differs from atlas source"
            )
        if (
            selection.global_row_key_sha256
            != source.get("global_row_key_sha256")
            or result.query.query_indices
            != selection.select(result.row_count)
        ):
            raise ValueError(
                "promotion query differs from preregistered selection"
            )
        if result.subject_backend.kind != "approximate":
            raise ValueError(
                "promotion audit subject must be approximate"
            )
        if (
            result.candidate_config.layer_indices is None
            or len(result.candidate_config.layer_indices) != 1
            or result.comparison_group
            != (
                "layer_index="
                f"{result.candidate_config.layer_indices[0]}"
            )
        ):
            raise ValueError(
                "promotion receipt must bind exactly one layer group"
            )
        parameters = dict(result.subject_backend.parameters)
        build_receipt = NeighborIndexBuildReceipt(
            backend=result.subject_backend,
            states_sha256=result.states_sha256,
            row_identity_sha256=source["global_row_key_sha256"],
            index_sha256=parameters["index_sha256"],
            comparison_group=result.comparison_group,
            row_count=result.row_count,
            hidden_size=result.hidden_size,
            states_dtype=result.states_dtype,
        )
        target_query = NeighborQuery(
            cosine_min=result.query.cosine_min,
            relative_norm_gap_max=result.query.relative_norm_gap_max,
            min_state_norm=result.query.min_state_norm,
            epsilon=result.query.epsilon,
            query_indices=None,
        )
        return cls(
            audit_sha256=result.sha256,
            audit_identity_sha256=result.identity_sha256,
            protocol_binding_sha256=result.protocol_binding.sha256,
            protocol_source_sha256=(
                result.protocol_binding.source_sha256
            ),
            source_identity_sha256=canonical_json_sha256(source),
            atlas_manifest_sha256=source["atlas_manifest_sha256"],
            atlas_run_id=source["atlas_run_id"],
            global_row_key_sha256=source["global_row_key_sha256"],
            source_run_id=result.source_run_id,
            comparison_group=result.comparison_group,
            states_sha256=result.states_sha256,
            drifts_sha256=result.drifts_sha256,
            row_count=result.row_count,
            hidden_size=result.hidden_size,
            states_dtype=result.states_dtype,
            drifts_dtype=result.drifts_dtype,
            subject_backend=result.subject_backend,
            subject_build_receipt=build_receipt,
            candidate_config_sha256=canonical_json_sha256(
                result.candidate_config.to_dict()
            ),
            candidate_protocol_id=candidate_protocol_id,
            candidate_protocol_sha256=candidate_protocol_sha256,
            audit_query_sha256=result.query.sha256,
            query_boundary_sha256=canonical_json_sha256(
                neighbor_query_boundary_dict(result.query)
            ),
            authorized_target_query_sha256=target_query.sha256,
            query_selection_sha256=selection.sha256,
            coverage_contract_sha256=result.coverage_contract_sha256,
            coverage_evidence_sha256=result.coverage_evidence_sha256,
        )

    def validate_target(
        self,
        target: NeighborPersistenceTarget,
    ) -> None:
        """Fail closed unless the target is the audited full index/group."""

        if not self.verified:
            raise ValueError(
                "neighbor audit receipt was not loaded through the "
                "verified audit/protocol path"
            )
        if not isinstance(target, NeighborPersistenceTarget):
            raise TypeError("target must be NeighborPersistenceTarget")
        checks = {
            "backend": target.backend == self.subject_backend,
            "build_receipt": (
                target.build_receipt == self.subject_build_receipt
            ),
            "candidate_config": (
                canonical_json_sha256(target.candidate_config.to_dict())
                == self.candidate_config_sha256
            ),
            "candidate_protocol_id": (
                target.candidate_protocol_id
                == self.candidate_protocol_id
            ),
            "candidate_protocol_sha256": (
                target.candidate_protocol_sha256
                == self.candidate_protocol_sha256
            ),
            "query_boundary": (
                canonical_json_sha256(
                    neighbor_query_boundary_dict(target.query)
                )
                == self.query_boundary_sha256
            ),
            "target_query": (
                target.query.sha256
                == self.authorized_target_query_sha256
            ),
            "atlas_manifest": (
                target.atlas_manifest_sha256
                == self.atlas_manifest_sha256
            ),
            "atlas_run": target.atlas_run_id == self.atlas_run_id,
            "row_identity": (
                target.global_row_key_sha256
                == self.global_row_key_sha256
            ),
            "source_run": target.source_run_id == self.source_run_id,
            "comparison_group": (
                target.comparison_group == self.comparison_group
            ),
            "states": target.states_sha256 == self.states_sha256,
            "drifts": target.drifts_sha256 == self.drifts_sha256,
            "row_count": target.row_count == self.row_count,
            "hidden_size": target.hidden_size == self.hidden_size,
            "states_dtype": target.states_dtype == self.states_dtype,
            "drifts_dtype": target.drifts_dtype == self.drifts_dtype,
        }
        failed = sorted(name for name, passed in checks.items() if not passed)
        if failed:
            raise ValueError(
                "neighbor audit receipt does not authorize target: "
                + ", ".join(failed)
            )

    @property
    def verified(self) -> bool:
        """Whether the receipt came from verified persisted inputs."""

        return self._verification_token is _VERIFIED_RECEIPT_TOKEN

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, object],
    ) -> "NeighborAuditReceipt":
        """Reconstruct and validate an embedded receipt recursively."""

        if not isinstance(payload, Mapping):
            raise TypeError("neighbor audit receipt must be a mapping")
        if (
            payload.get("schema_version")
            != NEIGHBOR_AUDIT_RECEIPT_SCHEMA_VERSION
        ):
            raise ValueError(
                "neighbor audit receipt schema is invalid"
            )
        backend_payload = payload.get("subject_backend")
        build_payload = payload.get("subject_build_receipt")
        if (
            not isinstance(backend_payload, Mapping)
            or not isinstance(build_payload, Mapping)
            or not isinstance(backend_payload.get("parameters"), Mapping)
            or not isinstance(backend_payload.get("runtime"), Mapping)
        ):
            raise ValueError(
                "neighbor audit receipt backend is malformed"
            )
        backend = NeighborBackendDescriptor(
            backend_id=backend_payload["backend_id"],
            backend_version=backend_payload["backend_version"],
            kind=backend_payload["kind"],
            deterministic=backend_payload["deterministic"],
            parameters=tuple(
                backend_payload["parameters"].items()
            ),
            runtime=tuple(backend_payload["runtime"].items()),
        )
        build_receipt = NeighborIndexBuildReceipt(
            backend=backend,
            states_sha256=build_payload["states_sha256"],
            row_identity_sha256=build_payload[
                "row_identity_sha256"
            ],
            index_sha256=build_payload["index_sha256"],
            comparison_group=build_payload["comparison_group"],
            row_count=build_payload["row_count"],
            hidden_size=build_payload["hidden_size"],
            states_dtype=build_payload["states_dtype"],
        )
        receipt = cls(
            audit_sha256=payload["audit_sha256"],
            audit_identity_sha256=payload[
                "audit_identity_sha256"
            ],
            protocol_binding_sha256=payload[
                "protocol_binding_sha256"
            ],
            protocol_source_sha256=payload[
                "protocol_source_sha256"
            ],
            source_identity_sha256=payload[
                "source_identity_sha256"
            ],
            atlas_manifest_sha256=payload[
                "atlas_manifest_sha256"
            ],
            atlas_run_id=payload["atlas_run_id"],
            global_row_key_sha256=payload[
                "global_row_key_sha256"
            ],
            source_run_id=payload["source_run_id"],
            comparison_group=payload["comparison_group"],
            states_sha256=payload["states_sha256"],
            drifts_sha256=payload["drifts_sha256"],
            row_count=payload["row_count"],
            hidden_size=payload["hidden_size"],
            states_dtype=payload["states_dtype"],
            drifts_dtype=payload["drifts_dtype"],
            subject_backend=backend,
            subject_build_receipt=build_receipt,
            candidate_config_sha256=payload[
                "candidate_config_sha256"
            ],
            candidate_protocol_id=payload[
                "candidate_protocol_id"
            ],
            candidate_protocol_sha256=payload[
                "candidate_protocol_sha256"
            ],
            audit_query_sha256=payload["audit_query_sha256"],
            query_boundary_sha256=payload[
                "query_boundary_sha256"
            ],
            authorized_target_query_sha256=payload[
                "authorized_target_query_sha256"
            ],
            query_selection_sha256=payload[
                "query_selection_sha256"
            ],
            coverage_contract_sha256=payload[
                "coverage_contract_sha256"
            ],
            coverage_evidence_sha256=payload[
                "coverage_evidence_sha256"
            ],
            exact_rerank_contract=payload[
                "exact_rerank_contract"
            ],
        )
        if receipt.to_dict() != dict(payload):
            raise ValueError(
                "neighbor audit receipt nested field or digest mismatch"
            )
        return receipt

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "authorization_scope": "same_full_input_index_group",
            "audit_sha256": self.audit_sha256,
            "audit_identity_sha256": self.audit_identity_sha256,
            "protocol_binding_sha256": self.protocol_binding_sha256,
            "protocol_source_sha256": self.protocol_source_sha256,
            "source_identity_sha256": self.source_identity_sha256,
            "atlas_manifest_sha256": self.atlas_manifest_sha256,
            "atlas_run_id": self.atlas_run_id,
            "global_row_key_sha256": self.global_row_key_sha256,
            "source_run_id": self.source_run_id,
            "comparison_group": self.comparison_group,
            "states_sha256": self.states_sha256,
            "drifts_sha256": self.drifts_sha256,
            "row_count": self.row_count,
            "hidden_size": self.hidden_size,
            "states_dtype": self.states_dtype,
            "drifts_dtype": self.drifts_dtype,
            "subject_backend": self.subject_backend.to_dict(),
            "subject_backend_sha256": self.subject_backend.sha256,
            "subject_build_receipt": self.subject_build_receipt.to_dict(),
            "subject_build_receipt_sha256": (
                self.subject_build_receipt.sha256
            ),
            "candidate_config_sha256": self.candidate_config_sha256,
            "candidate_protocol_id": self.candidate_protocol_id,
            "candidate_protocol_sha256": (
                self.candidate_protocol_sha256
            ),
            "audit_query_sha256": self.audit_query_sha256,
            "query_boundary_sha256": self.query_boundary_sha256,
            "authorized_target_query_sha256": (
                self.authorized_target_query_sha256
            ),
            "query_selection_sha256": self.query_selection_sha256,
            "coverage_contract_sha256": (
                self.coverage_contract_sha256
            ),
            "coverage_evidence_sha256": (
                self.coverage_evidence_sha256
            ),
            "exact_rerank_contract": self.exact_rerank_contract,
        }

    @property
    def sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


def load_neighbor_audit_receipt(
    audit_path: str | Path,
    *,
    protocol_path: str | Path,
    expected_audit_sha256: str,
    expected_protocol_sha256: str,
) -> NeighborAuditReceipt:
    """Load an audit and protocol against out-of-band trusted digests."""

    _require_sha256(
        expected_audit_sha256,
        label="expected_audit_sha256",
    )
    _require_sha256(
        expected_protocol_sha256,
        label="expected_protocol_sha256",
    )
    if hashlib.sha256(Path(protocol_path).read_bytes()).hexdigest() != (
        expected_protocol_sha256
    ):
        raise ValueError(
            "neighbor protocol does not match expected digest"
        )
    result = load_neighbor_audit_result(
        audit_path,
        expected_audit_sha256=expected_audit_sha256,
    )
    receipt = NeighborAuditReceipt._from_result(
        result,
        protocol_path=protocol_path,
    )
    if (
        receipt.protocol_source_sha256 != expected_protocol_sha256
        or hashlib.sha256(Path(protocol_path).read_bytes()).hexdigest()
        != expected_protocol_sha256
    ):
        raise ValueError(
            "neighbor protocol changed during receipt validation"
        )
    object.__setattr__(
        receipt,
        "_verification_token",
        _VERIFIED_RECEIPT_TOKEN,
    )
    return receipt
