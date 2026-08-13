"""Candidate-boundary recall audits for pluggable neighbor backends."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
from numbers import Integral, Real
import os
from pathlib import Path
from typing import Literal
import uuid

import numpy as np
from numpy.typing import ArrayLike, NDArray

from spirallens import __version__ as SPIRALLENS_VERSION
from spirallens.neighbors import (
    EXACT_BACKEND_ID,
    EXACT_BACKEND_VERSION,
    ExactBlockwiseBackend,
    FaissHNSWBackend,
    NeighborBackend,
    NeighborBackendDescriptor,
    NeighborIndexBuildReceipt,
    NeighborPair,
    NeighborQuery,
    PreparedNeighborBackend,
    canonical_json_sha256,
    exact_state_pair_metrics,
    finite_row_norms,
    validate_prepared_backend,
    validate_neighbor_pairs,
)
from spirallens.neighbors.contracts import _require_sha256

from .candidate_pairs import (
    EXACT_RERANK_CONTRACT_VERSION,
    CandidateSearchConfig,
    iter_exact_reranked_candidates,
)


NEIGHBOR_AUDIT_SCHEMA_VERSION = "spirallens.neighbor-audit.v0.2"
NEIGHBOR_AUDIT_IDENTITY_SCHEMA_VERSION = (
    "spirallens.neighbor-audit-identity.v0.2"
)
QUERY_SELECTION_SCHEMA_VERSION = (
    "spirallens.query-selection.sha256-ranked-indices.v0.1"
)
LOCAL_RECALL_CONTRACT_VERSION = (
    "spirallens.neighbor-local-recall.v0.1"
)
COVERAGE_EVALUATOR_VERSION = (
    "spirallens.neighbor-coverage-evaluator.v0.1"
)
BUILTIN_FAISS_AUDIT_RUNNER_CONTRACT = (
    "spirallens.builtin-faiss-audit-runner.v0.1"
)
CUSTOM_AUDIT_RUNNER_CONTRACT = "spirallens.custom-audit-runner.unverified"


def _reject_duplicate_json_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    payload: dict[str, object] = {}
    for key, value in pairs:
        if key in payload:
            raise ValueError(
                f"neighbor audit JSON contains duplicate key {key!r}"
            )
        payload[key] = value
    return payload


@dataclass(frozen=True)
class NeighborAuditConfig:
    """Preregistered promotion gate for one exact-reference audit."""

    candidate_recall_min: float = 0.99
    query_local_recall_min: float = 0.99
    stratum_recall_min: float = 0.99
    repeats: int = 2
    minimum_reference_candidates: int = 1
    minimum_eligible_queries: int = 1
    minimum_eligible_query_fraction: float = 0.0
    density_strata_count: int = 1
    minimum_eligible_queries_per_density_stratum: int = 1
    boundary_shell_width: float = 1e-4
    minimum_reference_candidates_per_stratum: int = 1
    missing_pair_sample_limit: int = 20

    def __post_init__(self) -> None:
        for field_name in (
            "candidate_recall_min",
            "query_local_recall_min",
            "stratum_recall_min",
            "minimum_eligible_query_fraction",
            "boundary_shell_width",
        ):
            value = getattr(self, field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, Real)
                or not np.isfinite(value)
            ):
                raise TypeError(f"{field_name} must be a finite real")
            object.__setattr__(self, field_name, float(value))
        for field_name in (
            "candidate_recall_min",
            "query_local_recall_min",
            "stratum_recall_min",
            "minimum_eligible_query_fraction",
        ):
            if not 0.0 <= getattr(self, field_name) <= 1.0:
                raise ValueError(f"{field_name} must lie in [0, 1]")
        if not 0.0 < self.boundary_shell_width <= 2.0:
            raise ValueError(
                "boundary_shell_width must lie in (0, 2]"
            )
        for field_name in (
            "repeats",
            "minimum_reference_candidates",
            "minimum_eligible_queries",
            "density_strata_count",
            "minimum_eligible_queries_per_density_stratum",
            "minimum_reference_candidates_per_stratum",
            "missing_pair_sample_limit",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, Integral):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
            object.__setattr__(self, field_name, int(value))
        if self.repeats < 2:
            raise ValueError(
                "repeats must be at least 2 for a cold-rebuild audit"
            )
    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_recall_min": self.candidate_recall_min,
            "query_local_recall_min": self.query_local_recall_min,
            "stratum_recall_min": self.stratum_recall_min,
            "repeats": self.repeats,
            "minimum_reference_candidates": (
                self.minimum_reference_candidates
            ),
            "minimum_eligible_queries": self.minimum_eligible_queries,
            "minimum_eligible_query_fraction": (
                self.minimum_eligible_query_fraction
            ),
            "density_strata_count": self.density_strata_count,
            "minimum_eligible_queries_per_density_stratum": (
                self.minimum_eligible_queries_per_density_stratum
            ),
            "boundary_shell_width": self.boundary_shell_width,
            "minimum_reference_candidates_per_stratum": (
                self.minimum_reference_candidates_per_stratum
            ),
            "missing_pair_sample_limit": self.missing_pair_sample_limit,
        }

    @property
    def sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


@dataclass(frozen=True)
class NeighborQuerySelectionContract:
    """Outcome-independent query sampling bound to full row identity."""

    seed: int
    count: int
    global_row_key_sha256: str
    schema_version: str = QUERY_SELECTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in ("seed", "count"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, Integral):
                raise TypeError(f"{field_name} must be an integer")
            object.__setattr__(self, field_name, int(value))
        if self.count <= 0:
            raise ValueError("count must be positive")
        _require_sha256(
            self.global_row_key_sha256,
            label="global_row_key_sha256",
        )
        if self.schema_version != QUERY_SELECTION_SCHEMA_VERSION:
            raise ValueError("query selection schema is invalid")

    def select(self, row_count: int) -> tuple[int, ...]:
        if isinstance(row_count, bool) or not isinstance(
            row_count,
            Integral,
        ):
            raise TypeError("row_count must be an integer")
        if row_count <= 0:
            raise ValueError("row_count must be positive")
        if self.count > row_count:
            raise ValueError("query selection count exceeds row_count")
        ranked = sorted(
            range(int(row_count)),
            key=lambda index: (
                hashlib.sha256(
                    (
                        f"{self.schema_version}\0{self.seed}\0"
                        f"{self.global_row_key_sha256}\0{index}"
                    ).encode("utf-8")
                ).digest(),
                index,
            ),
        )
        return tuple(sorted(ranked[: self.count]))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "method": "sha256_ranked_global_indices",
            "seed": self.seed,
            "count": self.count,
            "global_row_key_sha256": self.global_row_key_sha256,
        }

    @property
    def sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


@dataclass(frozen=True)
class NeighborAuditProtocolBinding:
    """Bind an audit to one declared protocol and its effective configs."""

    protocol_id: str
    status: Literal["preregistered-draft", "frozen"]
    source_sha256: str
    candidate_config_sha256: str
    audit_config_sha256: str
    deviations: tuple[str, ...] = ()
    query_selection: NeighborQuerySelectionContract | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.protocol_id, str) or not self.protocol_id:
            raise TypeError("protocol_id must be a non-empty string")
        if self.status not in {"preregistered-draft", "frozen"}:
            raise ValueError(
                "protocol status must be preregistered-draft or frozen"
            )
        for field_name in (
            "source_sha256",
            "candidate_config_sha256",
            "audit_config_sha256",
        ):
            _require_sha256(getattr(self, field_name), label=field_name)
        if not isinstance(self.deviations, tuple):
            raise TypeError("deviations must be a tuple")
        if any(
            not isinstance(value, str) or not value
            for value in self.deviations
        ):
            raise TypeError("deviations must contain non-empty strings")
        if tuple(sorted(set(self.deviations))) != self.deviations:
            raise ValueError("deviations must be unique and sorted")
        if (
            self.query_selection is not None
            and not isinstance(
                self.query_selection,
                NeighborQuerySelectionContract,
            )
        ):
            raise TypeError(
                "query_selection must be a "
                "NeighborQuerySelectionContract or None"
            )

    def validate_against(
        self,
        candidate_config: CandidateSearchConfig,
        audit_config: NeighborAuditConfig,
    ) -> None:
        if (
            canonical_json_sha256(candidate_config.to_dict())
            != self.candidate_config_sha256
            or audit_config.sha256 != self.audit_config_sha256
        ):
            raise ValueError(
                "protocol binding does not match the effective audit configs"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "protocol_id": self.protocol_id,
            "status": self.status,
            "source_sha256": self.source_sha256,
            "candidate_config_sha256": self.candidate_config_sha256,
            "audit_config_sha256": self.audit_config_sha256,
            "deviations": list(self.deviations),
            "query_selection": (
                None
                if self.query_selection is None
                else self.query_selection.to_dict()
            ),
            "query_selection_sha256": (
                None
                if self.query_selection is None
                else self.query_selection.sha256
            ),
        }

    @property
    def sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


def _canonical_source_json(source: Mapping[str, object]) -> str:
    if not isinstance(source, Mapping):
        raise TypeError("source_identity must be a mapping")
    encoded = json.dumps(
        source,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    payload = json.loads(encoded)
    if not isinstance(payload, dict):
        raise TypeError("source_identity must encode a JSON object")
    kind = payload.get("kind")
    if kind == "synthetic_fixture":
        fixture_id = payload.get("fixture_id")
        if not isinstance(fixture_id, str) or not fixture_id:
            raise ValueError(
                "synthetic_fixture source requires fixture_id"
            )
        _require_sha256(
            payload.get("row_identity_sha256"),
            label="row_identity_sha256",
        )
    elif kind == "atlas_subset":
        atlas_run_id = payload.get("atlas_run_id")
        if not isinstance(atlas_run_id, str) or not atlas_run_id:
            raise ValueError("atlas_subset source requires atlas_run_id")
        for field_name in (
            "atlas_manifest_sha256",
            "observation_scope_sha256",
            "global_row_key_sha256",
            "execution_freeze_sha256",
        ):
            _require_sha256(payload.get(field_name), label=field_name)
    else:
        raise ValueError(
            "source_identity.kind must be synthetic_fixture or atlas_subset"
        )
    return encoded


def _array_sha256(array: NDArray[np.generic]) -> str:
    contiguous = np.ascontiguousarray(array)
    header = {
        "shape": list(contiguous.shape),
        "dtype": str(contiguous.dtype),
    }
    digest = hashlib.sha256()
    digest.update(
        json.dumps(
            header,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    )
    digest.update(b"\0")
    digest.update(memoryview(contiguous).cast("B"))
    return digest.hexdigest()


def _assert_input_snapshot_unchanged(
    states: NDArray[np.generic],
    drifts: NDArray[np.generic],
    *,
    states_sha256: str,
    drifts_sha256: str,
    stage: str,
) -> None:
    if (
        _array_sha256(states) != states_sha256
        or _array_sha256(drifts) != drifts_sha256
    ):
        raise ValueError(
            f"audit input snapshot changed during {stage}"
        )


def _pair_sha256(pairs: tuple[tuple[int, int], ...]) -> str:
    digest = hashlib.sha256()
    for left_index, right_index in pairs:
        digest.update(f"{left_index}:{right_index}\n".encode("ascii"))
    return digest.hexdigest()


def _candidate_pair_keys(
    candidates: list[dict[str, object]],
) -> tuple[tuple[int, int], ...]:
    keys: list[tuple[int, int]] = []
    for candidate in candidates:
        left = candidate.get("left")
        right = candidate.get("right")
        if not isinstance(left, Mapping) or not isinstance(right, Mapping):
            raise ValueError("exact reranker emitted malformed references")
        left_index = left.get("row_index")
        right_index = right.get("row_index")
        if (
            isinstance(left_index, bool)
            or not isinstance(left_index, int)
            or isinstance(right_index, bool)
            or not isinstance(right_index, int)
            or left_index >= right_index
        ):
            raise ValueError("exact reranker emitted a non-canonical pair")
        keys.append((left_index, right_index))
    if keys != sorted(set(keys)):
        raise ValueError(
            "exact reranker candidates must be unique and ordered"
        )
    return tuple(keys)


def _query_axis(
    query: NeighborQuery,
    *,
    row_count: int,
) -> tuple[int, ...]:
    if (
        query.query_indices is not None
        and query.query_indices
        and query.query_indices[-1] >= row_count
    ):
        raise ValueError("query index exceeds row_count")
    return (
        tuple(range(row_count))
        if query.query_indices is None
        else query.query_indices
    )


def _pair_incidence_composition(
    *,
    pair_count: int,
    incidence_count: int,
    selected_selected_capacity: int,
    selected_to_unselected_capacity: int,
) -> tuple[int, int] | None:
    selected_selected_count = incidence_count - pair_count
    selected_to_unselected_count = 2 * pair_count - incidence_count
    if not (
        0
        <= selected_selected_count
        <= selected_selected_capacity
        and 0
        <= selected_to_unselected_count
        <= selected_to_unselected_capacity
    ):
        return None
    return selected_selected_count, selected_to_unselected_count


def _density_stratum_incidence_is_valid(
    *,
    pair_count: int,
    selected_selected_count: int,
    row_count: int,
    query_indices: tuple[int, ...],
    query_pair_degrees: tuple[int, ...],
    density_strata: tuple[tuple[str, tuple[int, ...]], ...],
    joint_stratum_pair_counts: tuple[int, ...],
) -> bool:
    degree_by_query = dict(
        zip(query_indices, query_pair_degrees, strict=True)
    )
    eligible_query_count = sum(
        len(members) for _, members in density_strata
    )
    unselected_row_count = row_count - len(query_indices)
    cross_density_capacity = 0
    preceding_member_count = 0
    for _, members in density_strata:
        cross_density_capacity += preceding_member_count * len(members)
        preceding_member_count += len(members)
    total_unique_incidence = 0
    same_density_selected_selected = 0
    for density_index, (_, members) in enumerate(density_strata):
        query_degree_sum = sum(
            degree_by_query[query_index] for query_index in members
        )
        unique_pair_count = sum(
            joint_stratum_pair_counts[
                2 * density_index : 2 * density_index + 2
            ]
        )
        internal_pair_count = query_degree_sum - unique_pair_count
        external_pair_count = 2 * unique_pair_count - query_degree_sum
        member_count = len(members)
        external_endpoint_count = (
            eligible_query_count
            - member_count
            + unselected_row_count
        )
        if not (
            0
            <= internal_pair_count
            <= member_count * (member_count - 1) // 2
            and 0
            <= external_pair_count
            <= member_count * external_endpoint_count
        ):
            return False
        total_unique_incidence += unique_pair_count
        same_density_selected_selected += internal_pair_count
    cross_density_selected_selected = (
        selected_selected_count - same_density_selected_selected
    )
    return (
        0
        <= cross_density_selected_selected
        <= cross_density_capacity
        and total_unique_incidence
        == pair_count + cross_density_selected_selected
    )


def _density_stratum_id(index: int, count: int) -> str:
    return f"density_rank_{index:02d}_of_{count:02d}"


@dataclass(frozen=True)
class _CoverageLayout:
    query_indices: tuple[int, ...]
    retrieval_neighbor_counts: tuple[int, ...]
    reference_candidate_pairs_by_query: tuple[
        tuple[tuple[int, int], ...],
        ...,
    ]
    density_strata: tuple[tuple[str, tuple[int, ...]], ...]
    candidate_strata: tuple[
        tuple[str, tuple[tuple[int, int], ...]],
        ...,
    ]


def _incident_pair_sets(
    pairs: tuple[tuple[int, int], ...],
    *,
    query_indices: tuple[int, ...],
) -> tuple[tuple[tuple[int, int], ...], ...]:
    query_set = set(query_indices)
    incident: dict[int, list[tuple[int, int]]] = {
        index: [] for index in query_indices
    }
    for pair in pairs:
        left_index, right_index = pair
        if left_index in query_set:
            incident[left_index].append(pair)
        if right_index in query_set:
            incident[right_index].append(pair)
    return tuple(
        tuple(incident[index]) for index in query_indices
    )


def _rank_density_strata(
    *,
    query_indices: tuple[int, ...],
    retrieval_neighbor_counts: tuple[int, ...],
    reference_candidate_counts: tuple[int, ...],
    density_strata_count: int,
) -> tuple[tuple[str, tuple[int, ...]], ...]:
    eligible = tuple(
        query_index
        for query_index, reference_count in zip(
            query_indices,
            reference_candidate_counts,
            strict=True,
        )
        if reference_count > 0
    )
    count_by_query = dict(
        zip(query_indices, retrieval_neighbor_counts, strict=True)
    )
    ranked = sorted(
        eligible,
        key=lambda query_index: (
            count_by_query[query_index],
            query_index,
        ),
    )
    density_members: list[list[int]] = [
        [] for _ in range(density_strata_count)
    ]
    for rank, query_index in enumerate(ranked):
        stratum_index = min(
            density_strata_count - 1,
            density_strata_count * rank // max(1, len(ranked)),
        )
        density_members[stratum_index].append(query_index)
    return tuple(
        (
            _density_stratum_id(stratum_index, density_strata_count),
            tuple(sorted(members)),
        )
        for stratum_index, members in enumerate(density_members)
    )


def _build_coverage_layout(
    states: NDArray[np.generic],
    *,
    query: NeighborQuery,
    reference_pairs: tuple[tuple[int, int], ...],
    reference_candidates: tuple[tuple[int, int], ...],
    config: NeighborAuditConfig,
) -> _CoverageLayout:
    query_indices = _query_axis(
        query,
        row_count=int(states.shape[0]),
    )
    retrieval_by_query = _incident_pair_sets(
        reference_pairs,
        query_indices=query_indices,
    )
    candidates_by_query = _incident_pair_sets(
        reference_candidates,
        query_indices=query_indices,
    )
    retrieval_counts = tuple(
        len(pairs) for pairs in retrieval_by_query
    )
    density_strata = _rank_density_strata(
        query_indices=query_indices,
        retrieval_neighbor_counts=retrieval_counts,
        reference_candidate_counts=tuple(
            len(pairs) for pairs in candidates_by_query
        ),
        density_strata_count=config.density_strata_count,
    )

    state_norms = finite_row_norms(
        states,
        block_size=max(1, min(4096, int(states.shape[0]))),
        label="coverage states",
    )
    shell_pairs: set[tuple[int, int]] = set()
    for left_index, right_index in reference_candidates:
        metrics = exact_state_pair_metrics(
            np.asarray(states[left_index], dtype=np.float64),
            np.asarray(states[right_index], dtype=np.float64),
            norm_a=float(state_norms[left_index]),
            norm_b=float(state_norms[right_index]),
            epsilon=query.epsilon,
        )
        cosine_slack = (
            metrics.cosine_similarity - query.cosine_min
        )
        if cosine_slack < -1e-15:
            raise ValueError(
                "reference candidate lies outside the cosine boundary"
            )
        if cosine_slack <= config.boundary_shell_width:
            shell_pairs.add((left_index, right_index))
    reference_candidate_set = set(reference_candidates)
    interior_pairs = reference_candidate_set - shell_pairs
    candidate_by_query = dict(
        zip(query_indices, candidates_by_query, strict=True)
    )
    candidate_strata: list[
        tuple[str, tuple[tuple[int, int], ...]]
    ] = []
    for density_id, members in density_strata:
        density_pairs: set[tuple[int, int]] = set()
        for query_index in members:
            density_pairs.update(candidate_by_query[query_index])
        candidate_strata.extend(
            (
                (
                    f"{density_id}__cosine_shell",
                    tuple(sorted(density_pairs & shell_pairs)),
                ),
                (
                    f"{density_id}__interior",
                    tuple(sorted(density_pairs & interior_pairs)),
                ),
            )
        )
    return _CoverageLayout(
        query_indices=query_indices,
        retrieval_neighbor_counts=retrieval_counts,
        reference_candidate_pairs_by_query=candidates_by_query,
        density_strata=density_strata,
        candidate_strata=tuple(candidate_strata),
    )


def _recall(
    match_count: int,
    reference_count: int,
) -> float | None:
    return (
        None
        if reference_count == 0
        else match_count / reference_count
    )


def _query_recall_matrix(
    reference_counts: tuple[int, ...],
    repeat_match_counts: tuple[tuple[int, ...], ...],
) -> tuple[tuple[float | None, ...], ...]:
    return tuple(
        tuple(
            _recall(match_count, reference_count)
            for match_count, reference_count in zip(
                repeat_counts,
                reference_counts,
                strict=True,
            )
        )
        for repeat_counts in repeat_match_counts
    )


def _density_macro_recall(
    *,
    query_indices: tuple[int, ...],
    query_recalls: tuple[tuple[float | None, ...], ...],
    density_strata: tuple[tuple[str, tuple[int, ...]], ...],
) -> tuple[tuple[float | None, ...], ...]:
    position = {
        query_index: index
        for index, query_index in enumerate(query_indices)
    }
    return tuple(
        tuple(
            (
                None
                if not members
                else float(
                    np.mean(
                        [
                            repeat_recalls[position[query_index]]
                            for query_index in members
                        ]
                    )
                )
            )
            for _, members in density_strata
        )
        for repeat_recalls in query_recalls
    )


def _stratum_recall_matrix(
    reference_counts: tuple[int, ...],
    repeat_match_counts: tuple[tuple[int, ...], ...],
) -> tuple[tuple[float | None, ...], ...]:
    return _query_recall_matrix(
        reference_counts,
        repeat_match_counts,
    )


def _validate_subject_descriptor(
    descriptor: NeighborBackendDescriptor,
    *,
    expected_states_sha256: str | None = None,
    expected_row_identity_sha256: str | None = None,
    expected_comparison_group: str | None = None,
) -> None:
    if descriptor.kind != "approximate":
        return
    parameters = dict(descriptor.parameters)
    seed = parameters.get("seed")
    thread_count = parameters.get("thread_count")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError(
            "approximate backend descriptor requires integer seed"
        )
    if (
        isinstance(thread_count, bool)
        or not isinstance(thread_count, int)
        or thread_count <= 0
    ):
        raise ValueError(
            "approximate backend descriptor requires positive thread_count"
        )
    _require_sha256(
        parameters.get("index_sha256"),
        label="parameters.index_sha256",
    )
    _require_sha256(
        parameters.get("promotion_config_sha256"),
        label="parameters.promotion_config_sha256",
    )
    _require_sha256(
        parameters.get("states_sha256"),
        label="parameters.states_sha256",
    )
    _require_sha256(
        parameters.get("row_identity_sha256"),
        label="parameters.row_identity_sha256",
    )
    if (
        expected_states_sha256 is not None
        and parameters.get("states_sha256")
        != expected_states_sha256
    ):
        raise ValueError(
            "approximate backend states_sha256 does not match audit input"
        )
    if (
        expected_row_identity_sha256 is not None
        and parameters.get("row_identity_sha256")
        != expected_row_identity_sha256
    ):
        raise ValueError(
            "approximate backend row identity does not match audit source"
        )
    if (
        expected_comparison_group is not None
        and parameters.get("comparison_group")
        != expected_comparison_group
    ):
        raise ValueError(
            "approximate backend comparison group does not match audit"
        )
    if not descriptor.runtime:
        raise ValueError(
            "approximate backend descriptor requires runtime provenance"
        )


def _validate_reference_descriptor(
    descriptor: NeighborBackendDescriptor,
) -> None:
    parameters = dict(descriptor.parameters)
    runtime = dict(descriptor.runtime)
    if (
        descriptor.backend_id != EXACT_BACKEND_ID
        or descriptor.backend_version != EXACT_BACKEND_VERSION
        or descriptor.kind != "exact"
        or descriptor.deterministic is not True
        or set(parameters)
        != {
            "block_size",
            "max_comparisons",
            "max_rows",
            "pair_order",
        }
        or parameters.get("pair_order")
        != "left_then_right_ascending"
        or any(
            isinstance(parameters.get(name), bool)
            or not isinstance(parameters.get(name), int)
            or parameters[name] <= 0
            for name in ("block_size", "max_comparisons", "max_rows")
        )
        or set(runtime) != {"numpy_version"}
        or not isinstance(runtime.get("numpy_version"), str)
        or not runtime["numpy_version"]
    ):
        raise ValueError(
            "reference_backend must match the exact blockwise reference "
            f"contract {EXACT_BACKEND_ID}@{EXACT_BACKEND_VERSION}"
        )


def _expected_status(
    *,
    reference_candidate_count: int,
    candidate_recalls: tuple[float | None, ...],
    query_indices: tuple[int, ...],
    query_reference_candidate_counts: tuple[int, ...],
    repeat_query_candidate_match_counts: tuple[
        tuple[int, ...],
        ...,
    ],
    density_strata: tuple[tuple[str, tuple[int, ...]], ...],
    stratum_reference_candidate_counts: tuple[int, ...],
    repeat_stratum_candidate_match_counts: tuple[
        tuple[int, ...],
        ...,
    ],
    deterministic: bool,
    audit_config: NeighborAuditConfig,
) -> Literal["pass", "fail", "insufficient"]:
    query_recalls = _query_recall_matrix(
        query_reference_candidate_counts,
        repeat_query_candidate_match_counts,
    )
    density_recalls = _density_macro_recall(
        query_indices=query_indices,
        query_recalls=query_recalls,
        density_strata=density_strata,
    )
    stratum_recalls = _stratum_recall_matrix(
        stratum_reference_candidate_counts,
        repeat_stratum_candidate_match_counts,
    )
    eligible_count = sum(
        count > 0 for count in query_reference_candidate_counts
    )
    support_sufficient = (
        reference_candidate_count
        >= audit_config.minimum_reference_candidates
        and eligible_count >= audit_config.minimum_eligible_queries
        and eligible_count
        >= int(
            np.ceil(
                len(query_indices)
                * audit_config.minimum_eligible_query_fraction
            )
        )
        and all(
            len(members)
            >= audit_config.minimum_eligible_queries_per_density_stratum
            for _, members in density_strata
        )
        and all(
            count
            >= audit_config.minimum_reference_candidates_per_stratum
            for count in stratum_reference_candidate_counts
        )
    )
    aggregate_values = [
        value for value in candidate_recalls if value is not None
    ]
    query_values = [
        value
        for repeat_values in query_recalls
        for value in repeat_values
        if value is not None
    ]
    density_values = [
        value
        for repeat_values in density_recalls
        for value in repeat_values
        if value is not None
    ]
    stratum_values = [
        value
        for repeat_values in stratum_recalls
        for value in repeat_values
        if value is not None
    ]
    known_failure = (
        not deterministic
        or any(
            value < audit_config.candidate_recall_min
            for value in aggregate_values
        )
        or any(
            value < audit_config.query_local_recall_min
            for value in query_values
        )
        or any(
            value < audit_config.stratum_recall_min
            for value in (*density_values, *stratum_values)
        )
    )
    if known_failure:
        return "fail"
    if (
        not support_sufficient
        or len(aggregate_values) != audit_config.repeats
        or not query_values
        or not density_values
        or not stratum_values
    ):
        return "insufficient"
    return "pass"


@dataclass(frozen=True)
class NeighborAuditResult:
    """Deterministic, internally validated recall-audit result."""

    status: Literal["pass", "fail", "insufficient"]
    source_identity_json: str
    source_run_id: str
    comparison_group: str
    protocol_binding: NeighborAuditProtocolBinding
    row_count: int
    hidden_size: int
    states_dtype: str
    drifts_dtype: str
    states_sha256: str
    drifts_sha256: str
    candidate_config: CandidateSearchConfig
    audit_config: NeighborAuditConfig
    query: NeighborQuery
    reference_backend: NeighborBackendDescriptor
    subject_backend: NeighborBackendDescriptor
    subject_runner_contract: str
    reference_pair_count: int
    reference_pair_sha256: str
    reference_candidate_count: int
    reference_candidate_sha256: str
    repeat_pair_counts: tuple[int, ...]
    repeat_pair_match_counts: tuple[int, ...]
    repeat_pair_sha256: tuple[str, ...]
    repeat_candidate_counts: tuple[int, ...]
    repeat_candidate_sha256: tuple[str, ...]
    retrieval_boundary_recall: tuple[float | None, ...]
    candidate_boundary_recall: tuple[float | None, ...]
    query_retrieval_neighbor_counts: tuple[int, ...]
    query_reference_candidate_counts: tuple[int, ...]
    query_reference_candidate_sha256: tuple[str, ...]
    repeat_query_candidate_match_counts: tuple[
        tuple[int, ...],
        ...,
    ]
    density_strata_query_indices: tuple[
        tuple[str, tuple[int, ...]],
        ...,
    ]
    stratum_reference_candidate_counts: tuple[
        tuple[str, int],
        ...,
    ]
    stratum_reference_candidate_sha256: tuple[
        tuple[str, str],
        ...,
    ]
    repeat_stratum_candidate_match_counts: tuple[
        tuple[int, ...],
        ...,
    ]
    cold_rebuild: bool
    deterministic: bool
    missing_candidate_pair_count: int
    missing_candidate_pairs_sample: tuple[tuple[int, int], ...]

    def __post_init__(self) -> None:
        if self.status not in {"pass", "fail", "insufficient"}:
            raise ValueError("invalid audit status")
        if not isinstance(self.source_run_id, str) or not self.source_run_id:
            raise TypeError("source_run_id must be a non-empty string")
        if (
            not isinstance(self.comparison_group, str)
            or not self.comparison_group
        ):
            raise TypeError("comparison_group must be a non-empty string")
        source_payload = json.loads(self.source_identity_json)
        if _canonical_source_json(source_payload) != self.source_identity_json:
            raise ValueError("source identity is not canonical")
        self.protocol_binding.validate_against(
            self.candidate_config,
            self.audit_config,
        )
        for field_name in ("row_count", "hidden_size"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{field_name} must be an integer")
        if self.row_count < 0 or self.hidden_size <= 0:
            raise ValueError("audit input shape is invalid")
        if not self.states_dtype or not self.drifts_dtype:
            raise ValueError("audit input dtypes must be non-empty")
        for field_name in (
            "states_sha256",
            "drifts_sha256",
            "reference_pair_sha256",
            "reference_candidate_sha256",
        ):
            _require_sha256(getattr(self, field_name), label=field_name)
        _validate_reference_descriptor(self.reference_backend)
        row_identity_sha256 = (
            source_payload["global_row_key_sha256"]
            if source_payload["kind"] == "atlas_subset"
            else source_payload["row_identity_sha256"]
        )
        selection = self.protocol_binding.query_selection
        if selection is not None:
            if (
                source_payload["kind"] != "atlas_subset"
                or selection.global_row_key_sha256
                != row_identity_sha256
                or self.query.query_indices
                != selection.select(self.row_count)
            ):
                raise ValueError(
                    "audit query does not match the preregistered "
                    "selection"
                )
        _validate_subject_descriptor(
            self.subject_backend,
            expected_states_sha256=self.states_sha256,
            expected_row_identity_sha256=row_identity_sha256,
            expected_comparison_group=self.comparison_group,
        )
        if self.subject_runner_contract not in {
            BUILTIN_FAISS_AUDIT_RUNNER_CONTRACT,
            CUSTOM_AUDIT_RUNNER_CONTRACT,
        }:
            raise ValueError("audit subject runner contract is invalid")
        if (
            self.subject_runner_contract
            == BUILTIN_FAISS_AUDIT_RUNNER_CONTRACT
            and (
                self.subject_backend.backend_id
                != "spirallens.faiss-hnsw-range"
                or self.subject_backend.backend_version
                not in {"0.1", "0.2"}
            )
        ):
            raise ValueError(
                "built-in Faiss runner contract has a non-Faiss "
                "descriptor"
            )
        if (
            self.protocol_binding.status == "frozen"
            and self.subject_runner_contract
            != BUILTIN_FAISS_AUDIT_RUNNER_CONTRACT
        ):
            raise ValueError(
                "frozen audits require the built-in Faiss runner "
                "contract"
            )
        if not isinstance(self.cold_rebuild, bool) or not self.cold_rebuild:
            raise ValueError("audit repeats must be independent cold rebuilds")

        repeat_fields = (
            self.repeat_pair_counts,
            self.repeat_pair_match_counts,
            self.repeat_pair_sha256,
            self.repeat_candidate_counts,
            self.repeat_candidate_sha256,
            self.retrieval_boundary_recall,
            self.candidate_boundary_recall,
        )
        if any(
            len(values) != self.audit_config.repeats
            for values in repeat_fields
        ):
            raise ValueError("audit repeat arrays do not match repeats")
        for digest in (
            *self.repeat_pair_sha256,
            *self.repeat_candidate_sha256,
        ):
            _require_sha256(digest, label="repeat digest")
        count_values = (
            self.reference_pair_count,
            self.reference_candidate_count,
            self.missing_candidate_pair_count,
            *self.repeat_pair_counts,
            *self.repeat_pair_match_counts,
            *self.repeat_candidate_counts,
        )
        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            for value in count_values
        ):
            raise ValueError("audit counts must be non-negative integers")
        empty_digest = _pair_sha256(())
        counted_pair_digests = (
            (
                self.reference_pair_count,
                self.reference_pair_sha256,
            ),
            (
                self.reference_candidate_count,
                self.reference_candidate_sha256,
            ),
            *zip(
                self.repeat_pair_counts,
                self.repeat_pair_sha256,
                strict=True,
            ),
            *zip(
                self.repeat_candidate_counts,
                self.repeat_candidate_sha256,
                strict=True,
            ),
        )
        if any(
            (count == 0) != (digest == empty_digest)
            for count, digest in counted_pair_digests
        ):
            raise ValueError("pair-set digest disagrees with its count")
        if self.reference_candidate_count > self.reference_pair_count:
            raise ValueError(
                "reference candidates exceed reference retrieval pairs"
            )
        if (
            self.reference_candidate_count == self.reference_pair_count
            and self.reference_candidate_sha256
            != self.reference_pair_sha256
        ):
            raise ValueError(
                "complete reference candidate digest disagrees with "
                "retrieval membership"
            )
        if any(
            candidate_count > pair_count
            or candidate_count > pair_match_count
            for candidate_count, pair_count, pair_match_count in zip(
                self.repeat_candidate_counts,
                self.repeat_pair_counts,
                self.repeat_pair_match_counts,
                strict=True,
            )
        ):
            raise ValueError(
                "subject candidates exceed matched retrieval pairs"
            )
        if any(
            candidate_count == pair_count
            and candidate_digest != pair_digest
            for candidate_count, pair_count, candidate_digest, pair_digest in zip(
                self.repeat_candidate_counts,
                self.repeat_pair_counts,
                self.repeat_candidate_sha256,
                self.repeat_pair_sha256,
                strict=True,
            )
        ):
            raise ValueError(
                "complete subject candidate digest disagrees with "
                "retrieval membership"
            )
        query_indices = _query_axis(
            self.query,
            row_count=self.row_count,
        )
        query_count = len(query_indices)
        selected_to_unselected_capacity = query_count * (
            self.row_count - query_count
        )
        selected_selected_capacity = (
            query_count * (query_count - 1) // 2
        )
        query_scope_pair_capacity = (
            selected_to_unselected_capacity
            + selected_selected_capacity
        )
        if self.reference_pair_count > query_scope_pair_capacity:
            raise ValueError(
                "reference retrieval pairs exceed the query scope"
            )
        if any(
            pair_count > query_scope_pair_capacity
            for pair_count in self.repeat_pair_counts
        ):
            raise ValueError(
                "subject retrieval pairs exceed the query scope"
            )
        query_field_lengths = (
            len(self.query_retrieval_neighbor_counts),
            len(self.query_reference_candidate_counts),
            len(self.query_reference_candidate_sha256),
        )
        if any(length != len(query_indices) for length in query_field_lengths):
            raise ValueError(
                "query-local evidence does not match the query axis"
            )
        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            for value in (
                *self.query_retrieval_neighbor_counts,
                *self.query_reference_candidate_counts,
            )
        ):
            raise ValueError(
                "query-local counts must be non-negative integers"
            )
        maximum_query_degree = max(0, self.row_count - 1)
        if any(
            retrieval_count > maximum_query_degree
            for retrieval_count in self.query_retrieval_neighbor_counts
        ):
            raise ValueError(
                "query retrieval degree exceeds the row universe"
            )
        retrieval_incidence_count = sum(
            self.query_retrieval_neighbor_counts
        )
        retrieval_incidence_composition = _pair_incidence_composition(
            pair_count=self.reference_pair_count,
            incidence_count=retrieval_incidence_count,
            selected_selected_capacity=selected_selected_capacity,
            selected_to_unselected_capacity=(
                selected_to_unselected_capacity
            ),
        )
        if retrieval_incidence_composition is None:
            raise ValueError(
                "query retrieval incidences do not cover the reference"
            )
        if any(
            candidate_count > retrieval_count
            or candidate_count > self.reference_candidate_count
            for retrieval_count, candidate_count in zip(
                self.query_retrieval_neighbor_counts,
                self.query_reference_candidate_counts,
                strict=True,
            )
        ):
            raise ValueError("query-local reference counts are impossible")
        for digest in self.query_reference_candidate_sha256:
            _require_sha256(digest, label="query reference digest")
        if any(
            (count == 0) != (digest == empty_digest)
            for count, digest in zip(
                self.query_reference_candidate_counts,
                self.query_reference_candidate_sha256,
                strict=True,
            )
        ):
            raise ValueError("empty query evidence digest is invalid")
        query_incidence_count = sum(
            self.query_reference_candidate_counts
        )
        candidate_incidence_composition = _pair_incidence_composition(
            pair_count=self.reference_candidate_count,
            incidence_count=query_incidence_count,
            selected_selected_capacity=selected_selected_capacity,
            selected_to_unselected_capacity=(
                selected_to_unselected_capacity
            ),
        )
        if (
            candidate_incidence_composition is None
            or any(
                candidate_count > retrieval_count
                for candidate_count, retrieval_count in zip(
                    candidate_incidence_composition,
                    retrieval_incidence_composition,
                    strict=True,
                )
            )
        ):
            raise ValueError(
                "query-local incidences do not cover the reference"
            )
        expected_density_strata = _rank_density_strata(
            query_indices=query_indices,
            retrieval_neighbor_counts=(
                self.query_retrieval_neighbor_counts
            ),
            reference_candidate_counts=(
                self.query_reference_candidate_counts
            ),
            density_strata_count=(
                self.audit_config.density_strata_count
            ),
        )
        if self.density_strata_query_indices != expected_density_strata:
            raise ValueError(
                "density strata differ from exact-reference ranking"
            )
        expected_stratum_names = tuple(
            name
            for density_id, _ in expected_density_strata
            for name in (
                f"{density_id}__cosine_shell",
                f"{density_id}__interior",
            )
        )
        stratum_count_names = tuple(
            name for name, _ in self.stratum_reference_candidate_counts
        )
        stratum_digest_names = tuple(
            name for name, _ in self.stratum_reference_candidate_sha256
        )
        if (
            stratum_count_names != expected_stratum_names
            or stratum_digest_names != expected_stratum_names
        ):
            raise ValueError("candidate recall strata are invalid")
        stratum_reference_counts = tuple(
            count
            for _, count in self.stratum_reference_candidate_counts
        )
        if any(
            isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
            or count > self.reference_candidate_count
            for count in stratum_reference_counts
        ):
            raise ValueError("stratum reference counts are invalid")
        for _, digest in self.stratum_reference_candidate_sha256:
            _require_sha256(digest, label="stratum reference digest")
        if any(
            (count == 0) != (digest == empty_digest)
            for (_, count), (_, digest) in zip(
                self.stratum_reference_candidate_counts,
                self.stratum_reference_candidate_sha256,
                strict=True,
            )
        ):
            raise ValueError("empty stratum evidence digest is invalid")
        if not _density_stratum_incidence_is_valid(
            pair_count=self.reference_candidate_count,
            selected_selected_count=(
                candidate_incidence_composition[0]
            ),
            row_count=self.row_count,
            query_indices=query_indices,
            query_pair_degrees=(
                self.query_reference_candidate_counts
            ),
            density_strata=expected_density_strata,
            joint_stratum_pair_counts=stratum_reference_counts,
        ):
            raise ValueError(
                "candidate strata do not cover the reference"
            )
        if (
            len(self.repeat_query_candidate_match_counts)
            != self.audit_config.repeats
            or len(self.repeat_stratum_candidate_match_counts)
            != self.audit_config.repeats
        ):
            raise ValueError(
                "local recall repeat evidence does not match repeats"
            )
        for repeat_counts in self.repeat_query_candidate_match_counts:
            if len(repeat_counts) != len(query_indices) or any(
                isinstance(match_count, bool)
                or not isinstance(match_count, int)
                or match_count < 0
                or match_count > reference_count
                for match_count, reference_count in zip(
                    repeat_counts,
                    self.query_reference_candidate_counts,
                    strict=True,
                )
            ):
                raise ValueError(
                    "query-local repeat match counts are invalid"
                )
        for repeat_counts in self.repeat_stratum_candidate_match_counts:
            if len(repeat_counts) != len(expected_stratum_names) or any(
                isinstance(match_count, bool)
                or not isinstance(match_count, int)
                or match_count < 0
                or match_count > reference_count
                for match_count, reference_count in zip(
                    repeat_counts,
                    stratum_reference_counts,
                    strict=True,
                )
            ):
                raise ValueError(
                    "stratum repeat match counts are invalid"
                )
        for repeat_index, candidate_count in enumerate(
            self.repeat_candidate_counts
        ):
            repeat_query_match_counts = (
                self.repeat_query_candidate_match_counts[repeat_index]
            )
            repeat_stratum_match_counts = (
                self.repeat_stratum_candidate_match_counts[repeat_index]
            )
            repeat_incidence_composition = _pair_incidence_composition(
                pair_count=candidate_count,
                incidence_count=sum(repeat_query_match_counts),
                selected_selected_capacity=selected_selected_capacity,
                selected_to_unselected_capacity=(
                    selected_to_unselected_capacity
                ),
            )
            if not (
                repeat_incidence_composition is not None
                and all(
                    subject_count <= reference_count
                    for subject_count, reference_count in zip(
                        repeat_incidence_composition,
                        candidate_incidence_composition,
                        strict=True,
                    )
                )
                and _density_stratum_incidence_is_valid(
                    pair_count=candidate_count,
                    selected_selected_count=(
                        repeat_incidence_composition[0]
                    ),
                    row_count=self.row_count,
                    query_indices=query_indices,
                    query_pair_degrees=repeat_query_match_counts,
                    density_strata=expected_density_strata,
                    joint_stratum_pair_counts=(
                        repeat_stratum_match_counts
                    ),
                )
            ):
                raise ValueError(
                    "local recall matches do not cover subject candidates"
                )

        for pair_count, match_count, pair_digest, recall in zip(
            self.repeat_pair_counts,
            self.repeat_pair_match_counts,
            self.repeat_pair_sha256,
            self.retrieval_boundary_recall,
            strict=True,
        ):
            if (
                match_count > self.reference_pair_count
                or match_count > pair_count
            ):
                raise ValueError("retrieval match count is impossible")
            if (
                pair_count
                == match_count
                == self.reference_pair_count
                and pair_digest != self.reference_pair_sha256
            ):
                raise ValueError(
                    "complete retrieval membership digest disagrees "
                    "with the reference"
                )
            expected_recall = (
                None
                if self.reference_pair_count == 0
                else match_count / self.reference_pair_count
            )
            if (
                expected_recall is None
                and recall is not None
                or expected_recall is not None
                and (
                    recall is None
                    or not np.isclose(
                        recall,
                        expected_recall,
                        rtol=0.0,
                        atol=1e-15,
                    )
                )
            ):
                raise ValueError("retrieval recall disagrees with counts")

        for candidate_count, candidate_digest, recall in zip(
            self.repeat_candidate_counts,
            self.repeat_candidate_sha256,
            self.candidate_boundary_recall,
            strict=True,
        ):
            if candidate_count > self.reference_candidate_count:
                raise ValueError(
                    "subject candidates exceed the exact reference"
                )
            if (
                candidate_count == self.reference_candidate_count
                and candidate_digest != self.reference_candidate_sha256
            ):
                raise ValueError(
                    "complete candidate membership digest disagrees "
                    "with the reference"
                )
            expected_recall = (
                None
                if self.reference_candidate_count == 0
                else candidate_count / self.reference_candidate_count
            )
            if (
                expected_recall is None
                and recall is not None
                or expected_recall is not None
                and (
                    recall is None
                    or not np.isclose(
                        recall,
                        expected_recall,
                        rtol=0.0,
                        atol=1e-15,
                    )
                )
            ):
                raise ValueError("candidate recall disagrees with counts")

        expected_deterministic = (
            self.subject_backend.deterministic
            and len(set(self.repeat_pair_sha256)) == 1
            and len(set(self.repeat_candidate_sha256)) == 1
        )
        if self.deterministic is not expected_deterministic:
            raise ValueError("determinism flag disagrees with repeat digests")
        if self.deterministic and (
            len(set(self.repeat_query_candidate_match_counts)) != 1
            or len(set(self.repeat_stratum_candidate_match_counts)) != 1
        ):
            raise ValueError(
                "deterministic candidates have inconsistent local evidence"
            )
        expected_missing = max(
            (
                self.reference_candidate_count - count
                for count in self.repeat_candidate_counts
            ),
            default=0,
        )
        if self.missing_candidate_pair_count != expected_missing:
            raise ValueError("missing candidate count disagrees with repeats")
        sample = self.missing_candidate_pairs_sample
        if (
            sample != tuple(sorted(set(sample)))
            or len(sample) > self.missing_candidate_pair_count
            or len(sample) > self.audit_config.missing_pair_sample_limit
            or any(
                left < 0 or left >= right or right >= self.row_count
                for left, right in sample
            )
        ):
            raise ValueError("missing candidate sample is invalid")
        expected_status = _expected_status(
            reference_candidate_count=self.reference_candidate_count,
            candidate_recalls=self.candidate_boundary_recall,
            query_indices=query_indices,
            query_reference_candidate_counts=(
                self.query_reference_candidate_counts
            ),
            repeat_query_candidate_match_counts=(
                self.repeat_query_candidate_match_counts
            ),
            density_strata=self.density_strata_query_indices,
            stratum_reference_candidate_counts=(
                stratum_reference_counts
            ),
            repeat_stratum_candidate_match_counts=(
                self.repeat_stratum_candidate_match_counts
            ),
            deterministic=self.deterministic,
            audit_config=self.audit_config,
        )
        if self.status != expected_status:
            raise ValueError("audit status disagrees with promotion gates")

    @property
    def coverage_contract_sha256(self) -> str:
        return canonical_json_sha256(
            {
                "contract": LOCAL_RECALL_CONTRACT_VERSION,
                "evaluator": COVERAGE_EVALUATOR_VERSION,
                "spirallens_version": SPIRALLENS_VERSION,
                "numpy_version": np.__version__,
                "audit_config": self.audit_config.to_dict(),
            }
        )

    def _query_recalls(
        self,
    ) -> tuple[tuple[float | None, ...], ...]:
        return _query_recall_matrix(
            self.query_reference_candidate_counts,
            self.repeat_query_candidate_match_counts,
        )

    def _density_recalls(
        self,
    ) -> tuple[tuple[float | None, ...], ...]:
        return _density_macro_recall(
            query_indices=_query_axis(
                self.query,
                row_count=self.row_count,
            ),
            query_recalls=self._query_recalls(),
            density_strata=self.density_strata_query_indices,
        )

    def _stratum_recalls(
        self,
    ) -> tuple[tuple[float | None, ...], ...]:
        return _stratum_recall_matrix(
            tuple(
                count
                for _, count in self.stratum_reference_candidate_counts
            ),
            self.repeat_stratum_candidate_match_counts,
        )

    def _repeat_worst_case_recall(
        self,
    ) -> tuple[float | None, ...]:
        query_recalls = self._query_recalls()
        density_recalls = self._density_recalls()
        stratum_recalls = self._stratum_recalls()
        values: list[float | None] = []
        for repeat_index in range(self.audit_config.repeats):
            aggregate = self.candidate_boundary_recall[repeat_index]
            positive_query_values = tuple(
                value
                for value in query_recalls[repeat_index]
                if value is not None
            )
            density_values = density_recalls[repeat_index]
            stratum_values = stratum_recalls[repeat_index]
            if (
                aggregate is None
                or not positive_query_values
                or any(value is None for value in density_values)
                or any(value is None for value in stratum_values)
            ):
                values.append(None)
                continue
            values.append(
                min(
                    aggregate,
                    *positive_query_values,
                    *(
                        value
                        for value in density_values
                        if value is not None
                    ),
                    *(
                        value
                        for value in stratum_values
                        if value is not None
                    ),
                )
            )
        return tuple(values)

    @staticmethod
    def _gate_status(
        values: tuple[float, ...],
        *,
        threshold: float,
        support_sufficient: bool,
    ) -> Literal["pass", "fail", "insufficient"]:
        if any(value < threshold for value in values):
            return "fail"
        if not support_sufficient or not values:
            return "insufficient"
        return "pass"

    def coverage_gate_statuses(
        self,
    ) -> dict[str, Literal["pass", "fail", "insufficient"]]:
        query_indices = _query_axis(
            self.query,
            row_count=self.row_count,
        )
        query_recalls = self._query_recalls()
        density_recalls = self._density_recalls()
        stratum_recalls = self._stratum_recalls()
        eligible_count = sum(
            count > 0 for count in self.query_reference_candidate_counts
        )
        aggregate_values = tuple(
            value
            for value in self.candidate_boundary_recall
            if value is not None
        )
        query_values = tuple(
            value
            for repeat_values in query_recalls
            for value in repeat_values
            if value is not None
        )
        density_values = tuple(
            value
            for repeat_values in density_recalls
            for value in repeat_values
            if value is not None
        )
        stratum_values = tuple(
            value
            for repeat_values in stratum_recalls
            for value in repeat_values
            if value is not None
        )
        return {
            "aggregate": self._gate_status(
                aggregate_values,
                threshold=self.audit_config.candidate_recall_min,
                support_sufficient=(
                    self.reference_candidate_count
                    >= self.audit_config.minimum_reference_candidates
                ),
            ),
            "query_local": self._gate_status(
                query_values,
                threshold=self.audit_config.query_local_recall_min,
                support_sufficient=(
                    eligible_count
                    >= self.audit_config.minimum_eligible_queries
                    and eligible_count
                    >= int(
                        np.ceil(
                            len(query_indices)
                            * self.audit_config
                            .minimum_eligible_query_fraction
                        )
                    )
                ),
            ),
            "density_macro": self._gate_status(
                density_values,
                threshold=self.audit_config.stratum_recall_min,
                support_sufficient=all(
                    len(members)
                    >= self.audit_config
                    .minimum_eligible_queries_per_density_stratum
                    for _, members in self.density_strata_query_indices
                ),
            ),
            "density_boundary_joint": self._gate_status(
                stratum_values,
                threshold=self.audit_config.stratum_recall_min,
                support_sufficient=all(
                    count
                    >= self.audit_config
                    .minimum_reference_candidates_per_stratum
                    for _, count in (
                        self.stratum_reference_candidate_counts
                    )
                ),
            ),
            "determinism": (
                "pass" if self.deterministic else "fail"
            ),
        }

    def coverage_evidence_dict(self) -> dict[str, object]:
        query_indices = _query_axis(
            self.query,
            row_count=self.row_count,
        )
        query_recalls = self._query_recalls()
        density_recalls = self._density_recalls()
        stratum_recalls = self._stratum_recalls()
        density_by_query = {
            query_index: density_id
            for density_id, members in self.density_strata_query_indices
            for query_index in members
        }
        query_records = []
        for position, query_index in enumerate(query_indices):
            query_records.append(
                {
                    "query_index": query_index,
                    "reference_retrieval_degree": (
                        self.query_retrieval_neighbor_counts[position]
                    ),
                    "reference_candidate_degree": (
                        self.query_reference_candidate_counts[position]
                    ),
                    "reference_candidate_sha256": (
                        self.query_reference_candidate_sha256[position]
                    ),
                    "density_stratum": density_by_query.get(query_index),
                    "repeat_match_counts": [
                        repeat_counts[position]
                        for repeat_counts in (
                            self.repeat_query_candidate_match_counts
                        )
                    ],
                    "repeat_recall": [
                        repeat_values[position]
                        for repeat_values in query_recalls
                    ],
                }
            )
        stratum_records = []
        for position, ((stratum_id, count), (_, digest)) in enumerate(
            zip(
                self.stratum_reference_candidate_counts,
                self.stratum_reference_candidate_sha256,
                strict=True,
            )
        ):
            stratum_records.append(
                {
                    "stratum_id": stratum_id,
                    "reference_candidate_count": count,
                    "reference_candidate_sha256": digest,
                    "repeat_match_counts": [
                        repeat_counts[position]
                        for repeat_counts in (
                            self.repeat_stratum_candidate_match_counts
                        )
                    ],
                    "repeat_recall": [
                        repeat_values[position]
                        for repeat_values in stratum_recalls
                    ],
                }
            )
        zero_reference_queries = [
            query_index
            for query_index, count in zip(
                query_indices,
                self.query_reference_candidate_counts,
                strict=True,
            )
            if count == 0
        ]
        query_minima = [
            min(
                value
                for value in repeat_values
                if value is not None
            )
            if any(value is not None for value in repeat_values)
            else None
            for repeat_values in query_recalls
        ]
        density_minima = [
            min(
                value
                for value in repeat_values
                if value is not None
            )
            if any(value is not None for value in repeat_values)
            else None
            for repeat_values in density_recalls
        ]
        stratum_minima = [
            min(
                value
                for value in repeat_values
                if value is not None
            )
            if any(value is not None for value in repeat_values)
            else None
            for repeat_values in stratum_recalls
        ]
        return {
            "contract": LOCAL_RECALL_CONTRACT_VERSION,
            "contract_sha256": self.coverage_contract_sha256,
            "evaluator": {
                "contract": COVERAGE_EVALUATOR_VERSION,
                "spirallens_version": SPIRALLENS_VERSION,
                "numpy_version": np.__version__,
            },
            "basis": {
                "query_candidate_denominator": (
                    "exact_reference_candidate_incidence"
                ),
                "selected_selected_pair_ownership": (
                    "count_once_for_each_selected_endpoint"
                ),
                "zero_denominator_query": "null_not_pass",
                "density_basis": (
                    "exact_reference_retrieval_incident_degree"
                ),
                "density_assignment": (
                    "stable_equal_count_rank_degree_then_global_row"
                ),
                "density_aggregation": (
                    "macro_query_local_candidate_recall"
                ),
                "boundary_basis": (
                    "exact_float64_cosine_slack"
                ),
                "boundary_shell": (
                    "zero_to_width_inclusive"
                ),
                "interior": "greater_than_width",
                "joint_cells": "density_x_boundary",
                "pooling_override": False,
            },
            "zero_reference_queries": {
                "count": len(zero_reference_queries),
                "indices_sha256": canonical_json_sha256(
                    {"indices": zero_reference_queries}
                ),
            },
            "queries": query_records,
            "density_strata": [
                {
                    "stratum_id": density_id,
                    "query_indices": list(members),
                    "repeat_macro_recall": [
                        repeat_values[position]
                        for repeat_values in density_recalls
                    ],
                }
                for position, (density_id, members) in enumerate(
                    self.density_strata_query_indices
                )
            ],
            "candidate_strata": stratum_records,
            "repeat_worst_query_recall": query_minima,
            "repeat_worst_density_macro_recall": density_minima,
            "repeat_worst_joint_stratum_recall": stratum_minima,
            "repeat_worst_case_recall": list(
                self._repeat_worst_case_recall()
            ),
            "gate_status": self.coverage_gate_statuses(),
        }

    @property
    def coverage_evidence_sha256(self) -> str:
        return canonical_json_sha256(self.coverage_evidence_dict())

    def identity_dict(self) -> dict[str, object]:
        candidate_config = self.candidate_config.to_dict()
        audit_config = self.audit_config.to_dict()
        query = self.query.to_dict()
        reference_backend = self.reference_backend.to_dict()
        subject_backend = self.subject_backend.to_dict()
        protocol = self.protocol_binding.to_dict()
        identity = {
            "schema_version": NEIGHBOR_AUDIT_IDENTITY_SCHEMA_VERSION,
            "source_identity": json.loads(self.source_identity_json),
            "source_run_id": self.source_run_id,
            "comparison_group": self.comparison_group,
            "protocol": protocol,
            "protocol_sha256": self.protocol_binding.sha256,
            "input": {
                "row_count": self.row_count,
                "hidden_size": self.hidden_size,
                "states_dtype": self.states_dtype,
                "drifts_dtype": self.drifts_dtype,
                "states_sha256": self.states_sha256,
                "drifts_sha256": self.drifts_sha256,
            },
            "candidate_config": candidate_config,
            "candidate_config_sha256": canonical_json_sha256(
                candidate_config
            ),
            "audit_config": audit_config,
            "audit_config_sha256": self.audit_config.sha256,
            "coverage_contract": {
                "contract": LOCAL_RECALL_CONTRACT_VERSION,
                "evaluator": COVERAGE_EVALUATOR_VERSION,
                "spirallens_version": SPIRALLENS_VERSION,
                "numpy_version": np.__version__,
                "sha256": self.coverage_contract_sha256,
            },
            "query": query,
            "query_sha256": self.query.sha256,
            "reference_backend": reference_backend,
            "reference_backend_sha256": self.reference_backend.sha256,
            "subject_backend": subject_backend,
            "subject_backend_sha256": self.subject_backend.sha256,
            "subject_runner": {
                "contract": self.subject_runner_contract,
                "exact_python_type_required": (
                    self.subject_runner_contract
                    == BUILTIN_FAISS_AUDIT_RUNNER_CONTRACT
                ),
            },
            "exact_rerank": {
                "contract": EXACT_RERANK_CONTRACT_VERSION,
                "required": True,
                "source_values": "atlas_values_cast_to_float64",
                "backend_score_used_for_gates": False,
            },
        }
        if self.subject_backend.kind == "approximate":
            parameters = dict(self.subject_backend.parameters)
            build_receipt = NeighborIndexBuildReceipt(
                backend=self.subject_backend,
                states_sha256=self.states_sha256,
                row_identity_sha256=parameters["row_identity_sha256"],
                index_sha256=parameters["index_sha256"],
                comparison_group=self.comparison_group,
                row_count=self.row_count,
                hidden_size=self.hidden_size,
                states_dtype=self.states_dtype,
            )
            identity["subject_index_build"] = build_receipt.to_dict()
            identity["subject_index_build_sha256"] = (
                build_receipt.sha256
            )
        return identity

    @property
    def identity_sha256(self) -> str:
        return canonical_json_sha256(self.identity_dict())

    def to_dict(self) -> dict[str, object]:
        exact_rerank = {
            **self.identity_dict()["exact_rerank"],
            "false_persistable_candidates": 0,
        }
        return {
            "schema_version": NEIGHBOR_AUDIT_SCHEMA_VERSION,
            "status": self.status,
            "identity": self.identity_dict(),
            "audit_identity_sha256": self.identity_sha256,
            "exact_rerank": exact_rerank,
            "coverage": {
                **self.coverage_evidence_dict(),
                "evidence_sha256": self.coverage_evidence_sha256,
            },
            "reference": {
                "retrieval_pair_count": self.reference_pair_count,
                "retrieval_pair_sha256": self.reference_pair_sha256,
                "candidate_count": self.reference_candidate_count,
                "candidate_sha256": self.reference_candidate_sha256,
            },
            "repeats": {
                "cold_rebuild": self.cold_rebuild,
                "retrieval_pair_counts": list(self.repeat_pair_counts),
                "retrieval_pair_match_counts": list(
                    self.repeat_pair_match_counts
                ),
                "retrieval_pair_sha256": list(self.repeat_pair_sha256),
                "candidate_counts": list(self.repeat_candidate_counts),
                "candidate_sha256": list(
                    self.repeat_candidate_sha256
                ),
            },
            "metrics": {
                "retrieval_boundary_recall": list(
                    self.retrieval_boundary_recall
                ),
                "candidate_boundary_recall": list(
                    self.candidate_boundary_recall
                ),
                "minimum_candidate_boundary_recall": (
                    None
                    if any(
                        value is None
                        for value in self.candidate_boundary_recall
                    )
                    else min(
                        value
                        for value in self.candidate_boundary_recall
                        if value is not None
                    )
                ),
                "deterministic": self.deterministic,
                "worst_query_local_recall": min(
                    (
                        value
                        for repeat_values in self._query_recalls()
                        for value in repeat_values
                        if value is not None
                    ),
                    default=None,
                ),
                "worst_density_macro_recall": min(
                    (
                        value
                        for repeat_values in self._density_recalls()
                        for value in repeat_values
                        if value is not None
                    ),
                    default=None,
                ),
                "worst_density_boundary_joint_recall": min(
                    (
                        value
                        for repeat_values in self._stratum_recalls()
                        for value in repeat_values
                        if value is not None
                    ),
                    default=None,
                ),
                "worst_case_recall": (
                    None
                    if any(
                        value is None
                        for value in self._repeat_worst_case_recall()
                    )
                    else min(
                        value
                        for value in self._repeat_worst_case_recall()
                        if value is not None
                    )
                ),
            },
            "missing_candidates": {
                "count": self.missing_candidate_pair_count,
                "sample": [
                    [left_index, right_index]
                    for left_index, right_index
                    in self.missing_candidate_pairs_sample
                ],
            },
            "top_k_diagnostic": {
                "status": "not_run",
                "role": "diagnostic_only",
                "used_for_promotion": False,
            },
            "promotion_contract": {
                "candidate_boundary_recall_is_primary": True,
                "query_local_gate_required": True,
                "density_macro_gate_required": True,
                "density_boundary_joint_gate_required": True,
                "pooled_recall_can_override_local_failure": False,
                "zero_reference_candidates": "insufficient",
                "protocol_binding_required": True,
                "cold_rebuild_required": True,
                "actual_approximate_backend_promoted": False,
            },
        }

    @property
    def sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    def artifact(self) -> dict[str, object]:
        return {**self.to_dict(), "audit_sha256": self.sha256}


def _collect_pairs(
    backend: NeighborBackend,
    states: NDArray[np.generic],
    query: NeighborQuery,
) -> tuple[NeighborBackendDescriptor, tuple[NeighborPair, ...]]:
    descriptor = backend.descriptor
    if not isinstance(descriptor, NeighborBackendDescriptor):
        raise TypeError(
            "neighbor_backend.descriptor must be a "
            "NeighborBackendDescriptor"
        )
    _validate_subject_descriptor(descriptor)
    pairs = tuple(
        validate_neighbor_pairs(
            backend.iter_pairs(states, query=query),
            row_count=int(states.shape[0]),
        )
    )
    if backend.descriptor != descriptor:
        raise ValueError("backend descriptor changed during retrieval")
    return descriptor, pairs


def _reranked_pair_keys(
    states: NDArray[np.generic],
    drifts: NDArray[np.generic],
    pairs: tuple[NeighborPair, ...],
    *,
    descriptor: NeighborBackendDescriptor,
    query: NeighborQuery,
    config: CandidateSearchConfig,
    source_run_id: str,
    group_key: str,
) -> tuple[tuple[int, int], ...]:
    candidates = list(
        iter_exact_reranked_candidates(
            states,
            drifts,
            pairs,
            backend_descriptor=descriptor,
            query=query,
            config=config,
            source_run_id=source_run_id,
            group_key=group_key,
        )
    )
    return _candidate_pair_keys(candidates)


def audit_neighbor_backend(
    states: ArrayLike,
    drifts: ArrayLike,
    *,
    subject_backend_factory: Callable[
        [NDArray[np.generic]],
        NeighborBackend,
    ],
    protocol_binding: NeighborAuditProtocolBinding,
    source_identity: Mapping[str, object],
    candidate_config: CandidateSearchConfig | None = None,
    audit_config: NeighborAuditConfig | None = None,
    query_indices: tuple[int, ...] | None = None,
    reference_backend: ExactBlockwiseBackend | None = None,
    source_run_id: str = "neighbor-audit-array",
    group_key: str = "ungrouped",
) -> NeighborAuditResult:
    """Audit candidate recall using independently rebuilt subject backends."""

    if not callable(subject_backend_factory):
        raise TypeError("subject_backend_factory must be callable")
    if not isinstance(protocol_binding, NeighborAuditProtocolBinding):
        raise TypeError(
            "protocol_binding must be a NeighborAuditProtocolBinding"
        )
    settings = candidate_config or CandidateSearchConfig()
    audit_settings = audit_config or NeighborAuditConfig()
    protocol_binding.validate_against(settings, audit_settings)
    source_json = _canonical_source_json(source_identity)
    source_payload = json.loads(source_json)
    source_states = np.asanyarray(states)
    source_drifts = np.asanyarray(drifts)
    if source_states.ndim != 2 or source_drifts.ndim != 2:
        raise ValueError(
            "states and drifts must both have shape (observations, hidden)"
        )
    if source_states.shape != source_drifts.shape:
        raise ValueError("states and drifts must have identical shapes")
    # Audit external backends against detached, read-only snapshots. The base
    # arrays are also read-only so a backend cannot normally re-enable writes
    # on the view it receives. Digests below still detect a backend that
    # deliberately reaches through ``.base`` or another alias.
    state_storage = np.array(
        source_states,
        copy=True,
        order="C",
        subok=False,
    )
    drift_storage = np.array(
        source_drifts,
        copy=True,
        order="C",
        subok=False,
    )
    state_storage.setflags(write=False)
    drift_storage.setflags(write=False)
    state_rows = state_storage.view()
    drift_rows = drift_storage.view()
    state_rows.setflags(write=False)
    drift_rows.setflags(write=False)
    states_sha256 = _array_sha256(state_rows)
    drifts_sha256 = _array_sha256(drift_rows)
    row_identity_sha256 = (
        source_payload["global_row_key_sha256"]
        if source_payload["kind"] == "atlas_subset"
        else source_payload["row_identity_sha256"]
    )
    selection = protocol_binding.query_selection
    if selection is not None:
        if source_payload["kind"] != "atlas_subset":
            raise ValueError(
                "query selection contracts require an atlas_subset source"
            )
        if (
            selection.global_row_key_sha256
            != row_identity_sha256
            or query_indices != selection.select(int(state_rows.shape[0]))
        ):
            raise ValueError(
                "query_indices do not match the preregistered selection"
            )
    query = NeighborQuery(
        cosine_min=settings.cosine_min,
        relative_norm_gap_max=settings.relative_norm_gap_max,
        min_state_norm=settings.min_state_norm,
        epsilon=settings.epsilon,
        query_indices=query_indices,
    )
    if reference_backend is not None and not isinstance(
        reference_backend,
        ExactBlockwiseBackend,
    ):
        raise TypeError(
            "reference_backend must be an ExactBlockwiseBackend"
        )
    exact_backend = (
        reference_backend
        if reference_backend is not None
        else ExactBlockwiseBackend(
            block_size=settings.block_size,
            max_rows=settings.max_pairwise_rows,
            max_comparisons=max(
                1,
                settings.max_pairwise_rows
                * (settings.max_pairwise_rows - 1)
                // 2,
            ),
        )
    )
    reference_descriptor, reference_pairs = _collect_pairs(
        exact_backend,
        state_rows,
        query,
    )
    _assert_input_snapshot_unchanged(
        state_rows,
        drift_rows,
        states_sha256=states_sha256,
        drifts_sha256=drifts_sha256,
        stage="exact reference retrieval",
    )
    _validate_reference_descriptor(reference_descriptor)
    reference_keys = tuple(pair.key for pair in reference_pairs)
    reference_candidates = _reranked_pair_keys(
        state_rows,
        drift_rows,
        reference_pairs,
        descriptor=reference_descriptor,
        query=query,
        config=settings,
        source_run_id=source_run_id,
        group_key=group_key,
    )
    _assert_input_snapshot_unchanged(
        state_rows,
        drift_rows,
        states_sha256=states_sha256,
        drifts_sha256=drifts_sha256,
        stage="exact reference rerank",
    )
    reference_pair_set = set(reference_keys)
    reference_candidate_set = set(reference_candidates)
    coverage_layout = _build_coverage_layout(
        state_rows,
        query=query,
        reference_pairs=reference_keys,
        reference_candidates=reference_candidates,
        config=audit_settings,
    )
    query_reference_candidate_counts = tuple(
        len(pairs)
        for pairs in (
            coverage_layout.reference_candidate_pairs_by_query
        )
    )
    query_reference_candidate_sha256 = tuple(
        _pair_sha256(pairs)
        for pairs in (
            coverage_layout.reference_candidate_pairs_by_query
        )
    )
    stratum_reference_candidate_counts = tuple(
        (stratum_id, len(pairs))
        for stratum_id, pairs in coverage_layout.candidate_strata
    )
    stratum_reference_candidate_sha256 = tuple(
        (stratum_id, _pair_sha256(pairs))
        for stratum_id, pairs in coverage_layout.candidate_strata
    )
    query_reference_candidate_sets = tuple(
        frozenset(pairs)
        for pairs in coverage_layout.reference_candidate_pairs_by_query
    )
    stratum_reference_candidate_sets = tuple(
        frozenset(pairs)
        for _, pairs in coverage_layout.candidate_strata
    )

    subject_descriptor: NeighborBackendDescriptor | None = None
    subject_runner_contract: str | None = None
    built_backends: list[NeighborBackend] = []
    repeat_pair_counts: list[int] = []
    repeat_pair_match_counts: list[int] = []
    repeat_pair_digests: list[str] = []
    repeat_candidate_counts: list[int] = []
    repeat_candidate_digests: list[str] = []
    retrieval_recalls: list[float | None] = []
    candidate_recalls: list[float | None] = []
    repeat_query_candidate_match_counts: list[tuple[int, ...]] = []
    repeat_stratum_candidate_match_counts: list[tuple[int, ...]] = []
    missing_by_repeat: list[set[tuple[int, int]]] = []

    for _ in range(audit_settings.repeats):
        backend = subject_backend_factory(state_rows)
        if not isinstance(backend, NeighborBackend):
            raise TypeError(
                "subject_backend_factory must return a NeighborBackend"
            )
        if (
            protocol_binding.status == "frozen"
            and type(backend) is not FaissHNSWBackend
        ):
            raise TypeError(
                "frozen promotion audits require the built-in "
                "FaissHNSWBackend implementation"
            )
        current_runner_contract = (
            BUILTIN_FAISS_AUDIT_RUNNER_CONTRACT
            if type(backend) is FaissHNSWBackend
            else CUSTOM_AUDIT_RUNNER_CONTRACT
        )
        if subject_runner_contract is None:
            subject_runner_contract = current_runner_contract
        elif current_runner_contract != subject_runner_contract:
            raise ValueError(
                "subject backend runner changed between cold rebuilds"
            )
        if any(backend is previous for previous in built_backends):
            raise ValueError(
                "subject_backend_factory must return a fresh backend "
                "for every cold rebuild"
            )
        built_backends.append(backend)
        _assert_input_snapshot_unchanged(
            state_rows,
            drift_rows,
            states_sha256=states_sha256,
            drifts_sha256=drifts_sha256,
            stage="subject backend build",
        )
        prepared_receipt = None
        if backend.descriptor.kind == "approximate":
            if not isinstance(backend, PreparedNeighborBackend):
                raise TypeError(
                    "approximate audit subjects must be prepared backends"
                )
            prepared_receipt = validate_prepared_backend(
                backend,
                states=state_rows,
                row_identity_sha256=row_identity_sha256,
                comparison_group=group_key,
            )
        descriptor, subject_pairs = _collect_pairs(
            backend,
            state_rows,
            query,
        )
        _assert_input_snapshot_unchanged(
            state_rows,
            drift_rows,
            states_sha256=states_sha256,
            drifts_sha256=drifts_sha256,
            stage="subject backend retrieval",
        )
        if prepared_receipt is not None:
            post_retrieval_receipt = validate_prepared_backend(
                backend,
                states=state_rows,
                row_identity_sha256=row_identity_sha256,
                comparison_group=group_key,
            )
            if post_retrieval_receipt != prepared_receipt:
                raise ValueError(
                    "prepared backend build receipt changed during "
                    "retrieval"
                )
        if subject_descriptor is None:
            subject_descriptor = descriptor
        elif descriptor != subject_descriptor:
            raise ValueError(
                "subject backend descriptor changed between cold rebuilds"
            )
        subject_keys = tuple(pair.key for pair in subject_pairs)
        subject_candidates = _reranked_pair_keys(
            state_rows,
            drift_rows,
            subject_pairs,
            descriptor=descriptor,
            query=query,
            config=settings,
            source_run_id=source_run_id,
            group_key=group_key,
        )
        _assert_input_snapshot_unchanged(
            state_rows,
            drift_rows,
            states_sha256=states_sha256,
            drifts_sha256=drifts_sha256,
            stage="subject exact rerank",
        )
        subject_pair_set = set(subject_keys)
        subject_candidate_set = set(subject_candidates)
        extra_candidates = subject_candidate_set - reference_candidate_set
        if extra_candidates:
            raise ValueError(
                "subject exact rerank produced candidates outside the "
                "exact reference"
            )
        pair_match_count = len(reference_pair_set & subject_pair_set)
        repeat_pair_counts.append(len(subject_keys))
        repeat_pair_match_counts.append(pair_match_count)
        repeat_pair_digests.append(_pair_sha256(subject_keys))
        repeat_candidate_counts.append(len(subject_candidates))
        repeat_candidate_digests.append(
            _pair_sha256(subject_candidates)
        )
        retrieval_recalls.append(
            None
            if not reference_pair_set
            else pair_match_count / len(reference_pair_set)
        )
        candidate_recalls.append(
            None
            if not reference_candidate_set
            else len(subject_candidate_set)
            / len(reference_candidate_set)
        )
        repeat_query_candidate_match_counts.append(
            tuple(
                len(pairs & subject_candidate_set)
                for pairs in query_reference_candidate_sets
            )
        )
        repeat_stratum_candidate_match_counts.append(
            tuple(
                len(pairs & subject_candidate_set)
                for pairs in stratum_reference_candidate_sets
            )
        )
        missing_by_repeat.append(
            reference_candidate_set - subject_candidate_set
        )

    assert subject_descriptor is not None
    assert subject_runner_contract is not None
    deterministic = (
        subject_descriptor.deterministic
        and len(set(repeat_pair_digests)) == 1
        and len(set(repeat_candidate_digests)) == 1
    )
    status = _expected_status(
        reference_candidate_count=len(reference_candidate_set),
        candidate_recalls=tuple(candidate_recalls),
        query_indices=coverage_layout.query_indices,
        query_reference_candidate_counts=(
            query_reference_candidate_counts
        ),
        repeat_query_candidate_match_counts=tuple(
            repeat_query_candidate_match_counts
        ),
        density_strata=coverage_layout.density_strata,
        stratum_reference_candidate_counts=tuple(
            count
            for _, count in stratum_reference_candidate_counts
        ),
        repeat_stratum_candidate_match_counts=tuple(
            repeat_stratum_candidate_match_counts
        ),
        deterministic=deterministic,
        audit_config=audit_settings,
    )
    worst_repeat = max(
        range(len(missing_by_repeat)),
        key=lambda index: len(missing_by_repeat[index]),
    )
    missing = sorted(missing_by_repeat[worst_repeat])
    return NeighborAuditResult(
        status=status,
        source_identity_json=source_json,
        source_run_id=source_run_id,
        comparison_group=group_key,
        protocol_binding=protocol_binding,
        row_count=int(state_rows.shape[0]),
        hidden_size=int(state_rows.shape[1]),
        states_dtype=str(state_rows.dtype),
        drifts_dtype=str(drift_rows.dtype),
        states_sha256=states_sha256,
        drifts_sha256=drifts_sha256,
        candidate_config=settings,
        audit_config=audit_settings,
        query=query,
        reference_backend=reference_descriptor,
        subject_backend=subject_descriptor,
        subject_runner_contract=subject_runner_contract,
        reference_pair_count=len(reference_keys),
        reference_pair_sha256=_pair_sha256(reference_keys),
        reference_candidate_count=len(reference_candidates),
        reference_candidate_sha256=_pair_sha256(reference_candidates),
        repeat_pair_counts=tuple(repeat_pair_counts),
        repeat_pair_match_counts=tuple(repeat_pair_match_counts),
        repeat_pair_sha256=tuple(repeat_pair_digests),
        repeat_candidate_counts=tuple(repeat_candidate_counts),
        repeat_candidate_sha256=tuple(repeat_candidate_digests),
        retrieval_boundary_recall=tuple(retrieval_recalls),
        candidate_boundary_recall=tuple(candidate_recalls),
        query_retrieval_neighbor_counts=(
            coverage_layout.retrieval_neighbor_counts
        ),
        query_reference_candidate_counts=(
            query_reference_candidate_counts
        ),
        query_reference_candidate_sha256=(
            query_reference_candidate_sha256
        ),
        repeat_query_candidate_match_counts=tuple(
            repeat_query_candidate_match_counts
        ),
        density_strata_query_indices=coverage_layout.density_strata,
        stratum_reference_candidate_counts=(
            stratum_reference_candidate_counts
        ),
        stratum_reference_candidate_sha256=(
            stratum_reference_candidate_sha256
        ),
        repeat_stratum_candidate_match_counts=tuple(
            repeat_stratum_candidate_match_counts
        ),
        cold_rebuild=True,
        deterministic=deterministic,
        missing_candidate_pair_count=len(missing),
        missing_candidate_pairs_sample=tuple(
            missing[: audit_settings.missing_pair_sample_limit]
        ),
    )


def write_neighbor_audit(
    result: NeighborAuditResult,
    output_path: str | Path,
    *,
    overwrite: bool = False,
    _reservation: object | None = None,
) -> Path:
    """Durably persist one content-addressed audit artifact."""

    if not isinstance(result, NeighborAuditResult):
        raise TypeError("result must be a NeighborAuditResult")
    if not isinstance(overwrite, bool):
        raise TypeError("overwrite must be a boolean")
    source_payload = json.loads(result.source_identity_json)
    if (
        source_payload.get("kind") == "atlas_subset"
        and _reservation is None
    ):
        raise ValueError(
            "atlas-backed neighbor audits require an exclusive "
            "output reservation"
        )
    destination = Path(output_path)
    if _reservation is not None:
        from spirallens.audit_output import (
            persist_reserved_audit_output,
        )

        if overwrite:
            raise ValueError(
                "reserved neighbor audit output cannot use overwrite"
            )
        encoded = (
            json.dumps(
                result.artifact(),
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
            + b"\n"
        )
        return persist_reserved_audit_output(
            _reservation,
            destination=destination,
            payload=encoded,
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not overwrite:
        raise FileExistsError(
            f"refusing to overwrite existing neighbor audit: {destination}"
        )
    temporary = destination.with_name(
        f".{destination.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}"
    )
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(
                result.artifact(),
                handle,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if overwrite:
            os.replace(temporary, destination)
        else:
            try:
                os.link(temporary, destination)
            except FileExistsError as error:
                raise FileExistsError(
                    "refusing to overwrite existing neighbor audit: "
                    f"{destination}"
                ) from error
            temporary.unlink()
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return destination


def _descriptor_from_payload(
    payload: Mapping[str, object],
) -> NeighborBackendDescriptor:
    parameters = payload.get("parameters")
    runtime = payload.get("runtime")
    if not isinstance(parameters, Mapping) or not isinstance(runtime, Mapping):
        raise ValueError("backend descriptor parameters/runtime are invalid")
    return NeighborBackendDescriptor(
        backend_id=payload.get("backend_id"),
        backend_version=payload.get("backend_version"),
        kind=payload.get("kind"),
        deterministic=payload.get("deterministic"),
        parameters=tuple(parameters.items()),
        runtime=tuple(runtime.items()),
    )


def _result_from_payload(payload: Mapping[str, object]) -> NeighborAuditResult:
    expected_top_level = {
        "schema_version",
        "status",
        "identity",
        "audit_identity_sha256",
        "exact_rerank",
        "coverage",
        "reference",
        "repeats",
        "metrics",
        "missing_candidates",
        "top_k_diagnostic",
        "promotion_contract",
    }
    if set(payload) != expected_top_level:
        raise ValueError("neighbor audit fields differ from its schema")
    identity = payload.get("identity")
    reference = payload.get("reference")
    repeats = payload.get("repeats")
    metrics = payload.get("metrics")
    missing = payload.get("missing_candidates")
    coverage = payload.get("coverage")
    if not all(
        isinstance(value, Mapping)
        for value in (
            identity,
            reference,
            repeats,
            metrics,
            missing,
            coverage,
        )
    ):
        raise ValueError("neighbor audit nested objects are invalid")
    assert isinstance(identity, Mapping)
    assert isinstance(reference, Mapping)
    assert isinstance(repeats, Mapping)
    assert isinstance(metrics, Mapping)
    assert isinstance(missing, Mapping)
    assert isinstance(coverage, Mapping)
    coverage_evidence = dict(coverage)
    coverage_evidence_sha256 = coverage_evidence.pop(
        "evidence_sha256",
        None,
    )
    _require_sha256(
        coverage_evidence_sha256,
        label="coverage.evidence_sha256",
    )
    if (
        canonical_json_sha256(coverage_evidence)
        != coverage_evidence_sha256
    ):
        raise ValueError("coverage evidence digest mismatch")
    input_payload = identity.get("input")
    candidate_payload = identity.get("candidate_config")
    audit_payload = identity.get("audit_config")
    coverage_contract_payload = identity.get("coverage_contract")
    query_payload = identity.get("query")
    reference_backend_payload = identity.get("reference_backend")
    subject_backend_payload = identity.get("subject_backend")
    subject_runner_payload = identity.get("subject_runner")
    protocol_payload = identity.get("protocol")
    source_payload = identity.get("source_identity")
    if not all(
        isinstance(value, Mapping)
        for value in (
            input_payload,
            candidate_payload,
            audit_payload,
            coverage_contract_payload,
            query_payload,
            reference_backend_payload,
            subject_backend_payload,
            subject_runner_payload,
            protocol_payload,
            source_payload,
        )
    ):
        raise ValueError("neighbor audit identity is invalid")
    assert isinstance(input_payload, Mapping)
    assert isinstance(candidate_payload, Mapping)
    assert isinstance(audit_payload, Mapping)
    assert isinstance(coverage_contract_payload, Mapping)
    assert isinstance(query_payload, Mapping)
    assert isinstance(reference_backend_payload, Mapping)
    assert isinstance(subject_backend_payload, Mapping)
    assert isinstance(subject_runner_payload, Mapping)
    assert isinstance(protocol_payload, Mapping)
    assert isinstance(source_payload, Mapping)

    candidate_values = dict(candidate_payload)
    if candidate_values.get("layer_indices") is not None:
        candidate_values["layer_indices"] = tuple(
            candidate_values["layer_indices"]
        )
    candidate_config = CandidateSearchConfig(**candidate_values)
    audit_config = NeighborAuditConfig(**dict(audit_payload))
    expected_coverage_contract_sha256 = canonical_json_sha256(
        {
            "contract": LOCAL_RECALL_CONTRACT_VERSION,
            "evaluator": COVERAGE_EVALUATOR_VERSION,
            "spirallens_version": SPIRALLENS_VERSION,
            "numpy_version": np.__version__,
            "audit_config": audit_config.to_dict(),
        }
    )
    if dict(coverage_contract_payload) != {
        "contract": LOCAL_RECALL_CONTRACT_VERSION,
        "evaluator": COVERAGE_EVALUATOR_VERSION,
        "spirallens_version": SPIRALLENS_VERSION,
        "numpy_version": np.__version__,
        "sha256": expected_coverage_contract_sha256,
    }:
        raise ValueError("coverage contract binding is invalid")
    if (
        coverage.get("contract") != LOCAL_RECALL_CONTRACT_VERSION
        or coverage.get("contract_sha256")
        != expected_coverage_contract_sha256
    ):
        raise ValueError("coverage evidence contract is invalid")
    query_indices = query_payload.get("query_indices")
    query = NeighborQuery(
        cosine_min=query_payload.get("cosine_min"),
        relative_norm_gap_max=query_payload.get("relative_norm_gap_max"),
        min_state_norm=query_payload.get("min_state_norm"),
        epsilon=query_payload.get("epsilon"),
        query_indices=(
            None if query_indices is None else tuple(query_indices)
        ),
    )
    row_count = input_payload.get("row_count")
    if (
        isinstance(row_count, bool)
        or not isinstance(row_count, int)
        or row_count < 0
    ):
        raise ValueError("audit input row_count is invalid")
    if (
        query.query_indices is not None
        and query.query_indices
        and query.query_indices[-1] >= row_count
    ):
        raise ValueError("query index exceeds row_count")
    selection_payload = protocol_payload.get("query_selection")
    if selection_payload is not None and not isinstance(
        selection_payload,
        Mapping,
    ):
        raise ValueError("protocol query selection is invalid")
    query_selection = (
        None
        if selection_payload is None
        else NeighborQuerySelectionContract(
            seed=selection_payload.get("seed"),
            count=selection_payload.get("count"),
            global_row_key_sha256=selection_payload.get(
                "global_row_key_sha256"
            ),
            schema_version=selection_payload.get("schema_version"),
        )
    )
    if protocol_payload.get("query_selection_sha256") != (
        None if query_selection is None else query_selection.sha256
    ):
        raise ValueError("protocol query selection digest mismatch")
    protocol = NeighborAuditProtocolBinding(
        protocol_id=protocol_payload.get("protocol_id"),
        status=protocol_payload.get("status"),
        source_sha256=protocol_payload.get("source_sha256"),
        candidate_config_sha256=protocol_payload.get(
            "candidate_config_sha256"
        ),
        audit_config_sha256=protocol_payload.get("audit_config_sha256"),
        deviations=tuple(protocol_payload.get("deviations", ())),
        query_selection=query_selection,
    )
    query_records = coverage.get("queries")
    density_records = coverage.get("density_strata")
    stratum_records = coverage.get("candidate_strata")
    if not all(
        isinstance(records, list)
        for records in (
            query_records,
            density_records,
            stratum_records,
        )
    ):
        raise ValueError("coverage evidence records are invalid")
    assert isinstance(query_records, list)
    assert isinstance(density_records, list)
    assert isinstance(stratum_records, list)
    if not all(isinstance(record, Mapping) for record in query_records):
        raise ValueError("query-local coverage records are invalid")
    if not all(isinstance(record, Mapping) for record in density_records):
        raise ValueError("density coverage records are invalid")
    if not all(isinstance(record, Mapping) for record in stratum_records):
        raise ValueError("candidate stratum records are invalid")
    if (
        len(density_records) != audit_config.density_strata_count
        or len(stratum_records)
        != 2 * audit_config.density_strata_count
    ):
        raise ValueError(
            "coverage strata do not match density_strata_count"
        )
    expected_query_record_count = (
        row_count
        if query.query_indices is None
        else len(query.query_indices)
    )
    if len(query_records) != expected_query_record_count:
        raise ValueError(
            "query-local evidence does not match the query axis"
        )

    repeat_lists = (
        repeats.get("retrieval_pair_counts"),
        repeats.get("retrieval_pair_match_counts"),
        repeats.get("retrieval_pair_sha256"),
        repeats.get("candidate_counts"),
        repeats.get("candidate_sha256"),
        metrics.get("retrieval_boundary_recall"),
        metrics.get("candidate_boundary_recall"),
    )
    if not all(
        isinstance(values, list)
        and len(values) == audit_config.repeats
        for values in repeat_lists
    ):
        raise ValueError("audit repeat arrays do not match repeats")

    query_repeat_rows: list[tuple[object, ...]] = []
    for repeat_index in range(audit_config.repeats):
        repeat_row: list[object] = []
        for record in query_records:
            assert isinstance(record, Mapping)
            match_counts = record.get("repeat_match_counts")
            if (
                not isinstance(match_counts, list)
                or len(match_counts) != audit_config.repeats
            ):
                raise ValueError(
                    "query-local repeat match counts are invalid"
                )
            repeat_row.append(match_counts[repeat_index])
        query_repeat_rows.append(tuple(repeat_row))

    stratum_repeat_rows: list[tuple[object, ...]] = []
    for repeat_index in range(audit_config.repeats):
        repeat_row = []
        for record in stratum_records:
            assert isinstance(record, Mapping)
            match_counts = record.get("repeat_match_counts")
            if (
                not isinstance(match_counts, list)
                or len(match_counts) != audit_config.repeats
            ):
                raise ValueError(
                    "stratum repeat match counts are invalid"
                )
            repeat_row.append(match_counts[repeat_index])
        stratum_repeat_rows.append(tuple(repeat_row))

    density_strata: list[tuple[object, tuple[object, ...]]] = []
    for record in density_records:
        assert isinstance(record, Mapping)
        indices = record.get("query_indices")
        if not isinstance(indices, list):
            raise ValueError("density query indices are invalid")
        density_strata.append(
            (record.get("stratum_id"), tuple(indices))
        )

    sample = missing.get("sample")
    if not isinstance(sample, list):
        raise ValueError("missing candidate sample must be a list")
    return NeighborAuditResult(
        status=payload.get("status"),
        source_identity_json=_canonical_source_json(source_payload),
        source_run_id=identity.get("source_run_id"),
        comparison_group=identity.get("comparison_group"),
        protocol_binding=protocol,
        row_count=input_payload.get("row_count"),
        hidden_size=input_payload.get("hidden_size"),
        states_dtype=input_payload.get("states_dtype"),
        drifts_dtype=input_payload.get("drifts_dtype"),
        states_sha256=input_payload.get("states_sha256"),
        drifts_sha256=input_payload.get("drifts_sha256"),
        candidate_config=candidate_config,
        audit_config=audit_config,
        query=query,
        reference_backend=_descriptor_from_payload(
            reference_backend_payload
        ),
        subject_backend=_descriptor_from_payload(
            subject_backend_payload
        ),
        subject_runner_contract=subject_runner_payload.get(
            "contract"
        ),
        reference_pair_count=reference.get("retrieval_pair_count"),
        reference_pair_sha256=reference.get("retrieval_pair_sha256"),
        reference_candidate_count=reference.get("candidate_count"),
        reference_candidate_sha256=reference.get("candidate_sha256"),
        repeat_pair_counts=tuple(
            repeats.get("retrieval_pair_counts", ())
        ),
        repeat_pair_match_counts=tuple(
            repeats.get("retrieval_pair_match_counts", ())
        ),
        repeat_pair_sha256=tuple(
            repeats.get("retrieval_pair_sha256", ())
        ),
        repeat_candidate_counts=tuple(
            repeats.get("candidate_counts", ())
        ),
        repeat_candidate_sha256=tuple(
            repeats.get("candidate_sha256", ())
        ),
        retrieval_boundary_recall=tuple(
            metrics.get("retrieval_boundary_recall", ())
        ),
        candidate_boundary_recall=tuple(
            metrics.get("candidate_boundary_recall", ())
        ),
        query_retrieval_neighbor_counts=tuple(
            record.get("reference_retrieval_degree")
            for record in query_records
        ),
        query_reference_candidate_counts=tuple(
            record.get("reference_candidate_degree")
            for record in query_records
        ),
        query_reference_candidate_sha256=tuple(
            record.get("reference_candidate_sha256")
            for record in query_records
        ),
        repeat_query_candidate_match_counts=tuple(
            query_repeat_rows
        ),
        density_strata_query_indices=tuple(density_strata),
        stratum_reference_candidate_counts=tuple(
            (
                record.get("stratum_id"),
                record.get("reference_candidate_count"),
            )
            for record in stratum_records
        ),
        stratum_reference_candidate_sha256=tuple(
            (
                record.get("stratum_id"),
                record.get("reference_candidate_sha256"),
            )
            for record in stratum_records
        ),
        repeat_stratum_candidate_match_counts=tuple(
            stratum_repeat_rows
        ),
        cold_rebuild=repeats.get("cold_rebuild"),
        deterministic=metrics.get("deterministic"),
        missing_candidate_pair_count=missing.get("count"),
        missing_candidate_pairs_sample=tuple(
            (item[0], item[1])
            for item in sample
            if isinstance(item, list) and len(item) == 2
        ),
    )


def _load_neighbor_audit_result(
    path: str | Path,
    *,
    expected_audit_sha256: str | None = None,
    expected_identity_sha256: str | None = None,
) -> tuple[NeighborAuditResult, str]:
    """Load an audit and independently revalidate every nested digest."""

    source = Path(path)
    try:
        artifact = json.loads(
            source.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid neighbor audit JSON: {source}") from error
    if not isinstance(artifact, dict):
        raise ValueError("neighbor audit must contain a JSON object")
    persisted_sha256 = artifact.pop("audit_sha256", None)
    _require_sha256(persisted_sha256, label="audit_sha256")
    if canonical_json_sha256(artifact) != persisted_sha256:
        raise ValueError("neighbor audit digest mismatch")
    if (
        expected_audit_sha256 is not None
        and persisted_sha256 != expected_audit_sha256
    ):
        raise ValueError("neighbor audit does not match expected digest")
    if artifact.get("schema_version") != NEIGHBOR_AUDIT_SCHEMA_VERSION:
        raise ValueError("neighbor audit schema is invalid")
    result = _result_from_payload(artifact)
    reconstructed = result.to_dict()
    if canonical_json_sha256(reconstructed) != canonical_json_sha256(
        artifact
    ):
        raise ValueError("neighbor audit nested digest or field mismatch")
    if (
        expected_identity_sha256 is not None
        and result.identity_sha256 != expected_identity_sha256
    ):
        raise ValueError("neighbor audit identity does not match expected digest")
    return result, persisted_sha256


def load_neighbor_audit_result(
    path: str | Path,
    *,
    expected_audit_sha256: str | None = None,
    expected_identity_sha256: str | None = None,
) -> NeighborAuditResult:
    """Load one strongly typed, fully reconstructed audit result."""

    result, _ = _load_neighbor_audit_result(
        path,
        expected_audit_sha256=expected_audit_sha256,
        expected_identity_sha256=expected_identity_sha256,
    )
    return result


def load_neighbor_audit(
    path: str | Path,
    *,
    expected_audit_sha256: str | None = None,
    expected_identity_sha256: str | None = None,
) -> dict[str, object]:
    """Load one audit as its validated JSON-ready artifact."""

    result, persisted_sha256 = _load_neighbor_audit_result(
        path,
        expected_audit_sha256=expected_audit_sha256,
        expected_identity_sha256=expected_identity_sha256,
    )
    return {**result.to_dict(), "audit_sha256": persisted_sha256}
