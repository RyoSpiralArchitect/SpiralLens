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

from spirallens.neighbors import (
    EXACT_BACKEND_ID,
    EXACT_BACKEND_VERSION,
    ExactBlockwiseBackend,
    NeighborBackend,
    NeighborBackendDescriptor,
    NeighborPair,
    NeighborQuery,
    canonical_json_sha256,
    validate_neighbor_pairs,
)

from .candidate_pairs import (
    EXACT_RERANK_CONTRACT_VERSION,
    CandidateSearchConfig,
    iter_exact_reranked_candidates,
)


NEIGHBOR_AUDIT_SCHEMA_VERSION = "spirallens.neighbor-audit.v0.1"
NEIGHBOR_AUDIT_IDENTITY_SCHEMA_VERSION = (
    "spirallens.neighbor-audit-identity.v0.1"
)


def _require_sha256(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


@dataclass(frozen=True)
class NeighborAuditConfig:
    """Preregistered promotion gate for one exact-reference audit."""

    candidate_recall_min: float = 0.99
    repeats: int = 2
    minimum_reference_candidates: int = 1
    missing_pair_sample_limit: int = 20

    def __post_init__(self) -> None:
        if (
            isinstance(self.candidate_recall_min, bool)
            or not isinstance(self.candidate_recall_min, Real)
            or not np.isfinite(self.candidate_recall_min)
        ):
            raise TypeError("candidate_recall_min must be a finite real")
        if not 0.0 <= self.candidate_recall_min <= 1.0:
            raise ValueError("candidate_recall_min must lie in [0, 1]")
        object.__setattr__(
            self,
            "candidate_recall_min",
            float(self.candidate_recall_min),
        )
        for field_name in (
            "repeats",
            "minimum_reference_candidates",
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
            "repeats": self.repeats,
            "minimum_reference_candidates": (
                self.minimum_reference_candidates
            ),
            "missing_pair_sample_limit": self.missing_pair_sample_limit,
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
    elif kind == "atlas_subset":
        atlas_run_id = payload.get("atlas_run_id")
        if not isinstance(atlas_run_id, str) or not atlas_run_id:
            raise ValueError("atlas_subset source requires atlas_run_id")
        for field_name in (
            "atlas_manifest_sha256",
            "observation_scope_sha256",
            "global_row_key_sha256",
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


def _validate_subject_descriptor(
    descriptor: NeighborBackendDescriptor,
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
    deterministic: bool,
    audit_config: NeighborAuditConfig,
) -> Literal["pass", "fail", "insufficient"]:
    if (
        reference_candidate_count
        < audit_config.minimum_reference_candidates
    ):
        return "insufficient"
    values = [value for value in candidate_recalls if value is not None]
    if (
        len(values) == audit_config.repeats
        and min(values) >= audit_config.candidate_recall_min
        and deterministic
    ):
        return "pass"
    return "fail"


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
        _validate_subject_descriptor(self.subject_backend)
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

        for pair_count, match_count, recall in zip(
            self.repeat_pair_counts,
            self.repeat_pair_match_counts,
            self.retrieval_boundary_recall,
            strict=True,
        ):
            if (
                match_count > self.reference_pair_count
                or match_count > pair_count
            ):
                raise ValueError("retrieval match count is impossible")
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

        for candidate_count, recall in zip(
            self.repeat_candidate_counts,
            self.candidate_boundary_recall,
            strict=True,
        ):
            if candidate_count > self.reference_candidate_count:
                raise ValueError(
                    "subject candidates exceed the exact reference"
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
            deterministic=self.deterministic,
            audit_config=self.audit_config,
        )
        if self.status != expected_status:
            raise ValueError("audit status disagrees with promotion gates")

    def identity_dict(self) -> dict[str, object]:
        candidate_config = self.candidate_config.to_dict()
        audit_config = self.audit_config.to_dict()
        query = self.query.to_dict()
        reference_backend = self.reference_backend.to_dict()
        subject_backend = self.subject_backend.to_dict()
        protocol = self.protocol_binding.to_dict()
        return {
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
            "query": query,
            "query_sha256": self.query.sha256,
            "reference_backend": reference_backend,
            "reference_backend_sha256": self.reference_backend.sha256,
            "subject_backend": subject_backend,
            "subject_backend_sha256": self.subject_backend.sha256,
            "exact_rerank": {
                "contract": EXACT_RERANK_CONTRACT_VERSION,
                "required": True,
                "source_values": "atlas_values_cast_to_float64",
                "backend_score_used_for_gates": False,
            },
        }

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
    subject_backend_factory: Callable[[], NeighborBackend],
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

    subject_descriptor: NeighborBackendDescriptor | None = None
    built_backends: list[NeighborBackend] = []
    repeat_pair_counts: list[int] = []
    repeat_pair_match_counts: list[int] = []
    repeat_pair_digests: list[str] = []
    repeat_candidate_counts: list[int] = []
    repeat_candidate_digests: list[str] = []
    retrieval_recalls: list[float | None] = []
    candidate_recalls: list[float | None] = []
    missing_by_repeat: list[set[tuple[int, int]]] = []

    for _ in range(audit_settings.repeats):
        backend = subject_backend_factory()
        if not isinstance(backend, NeighborBackend):
            raise TypeError(
                "subject_backend_factory must return a NeighborBackend"
            )
        if any(backend is previous for previous in built_backends):
            raise ValueError(
                "subject_backend_factory must return a fresh backend "
                "for every cold rebuild"
            )
        built_backends.append(backend)
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
        missing_by_repeat.append(
            reference_candidate_set - subject_candidate_set
        )

    assert subject_descriptor is not None
    deterministic = (
        subject_descriptor.deterministic
        and len(set(repeat_pair_digests)) == 1
        and len(set(repeat_candidate_digests)) == 1
    )
    status = _expected_status(
        reference_candidate_count=len(reference_candidate_set),
        candidate_recalls=tuple(candidate_recalls),
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
) -> Path:
    """Atomically persist one content-addressed audit artifact."""

    if not isinstance(result, NeighborAuditResult):
        raise TypeError("result must be a NeighborAuditResult")
    if not isinstance(overwrite, bool):
        raise TypeError("overwrite must be a boolean")
    destination = Path(output_path)
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
    if not all(
        isinstance(value, Mapping)
        for value in (identity, reference, repeats, metrics, missing)
    ):
        raise ValueError("neighbor audit nested objects are invalid")
    assert isinstance(identity, Mapping)
    assert isinstance(reference, Mapping)
    assert isinstance(repeats, Mapping)
    assert isinstance(metrics, Mapping)
    assert isinstance(missing, Mapping)
    input_payload = identity.get("input")
    candidate_payload = identity.get("candidate_config")
    audit_payload = identity.get("audit_config")
    query_payload = identity.get("query")
    reference_backend_payload = identity.get("reference_backend")
    subject_backend_payload = identity.get("subject_backend")
    protocol_payload = identity.get("protocol")
    source_payload = identity.get("source_identity")
    if not all(
        isinstance(value, Mapping)
        for value in (
            input_payload,
            candidate_payload,
            audit_payload,
            query_payload,
            reference_backend_payload,
            subject_backend_payload,
            protocol_payload,
            source_payload,
        )
    ):
        raise ValueError("neighbor audit identity is invalid")
    assert isinstance(input_payload, Mapping)
    assert isinstance(candidate_payload, Mapping)
    assert isinstance(audit_payload, Mapping)
    assert isinstance(query_payload, Mapping)
    assert isinstance(reference_backend_payload, Mapping)
    assert isinstance(subject_backend_payload, Mapping)
    assert isinstance(protocol_payload, Mapping)
    assert isinstance(source_payload, Mapping)

    candidate_values = dict(candidate_payload)
    if candidate_values.get("layer_indices") is not None:
        candidate_values["layer_indices"] = tuple(
            candidate_values["layer_indices"]
        )
    candidate_config = CandidateSearchConfig(**candidate_values)
    audit_config = NeighborAuditConfig(**dict(audit_payload))
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
    protocol = NeighborAuditProtocolBinding(
        protocol_id=protocol_payload.get("protocol_id"),
        status=protocol_payload.get("status"),
        source_sha256=protocol_payload.get("source_sha256"),
        candidate_config_sha256=protocol_payload.get(
            "candidate_config_sha256"
        ),
        audit_config_sha256=protocol_payload.get("audit_config_sha256"),
        deviations=tuple(protocol_payload.get("deviations", ())),
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
        cold_rebuild=repeats.get("cold_rebuild"),
        deterministic=metrics.get("deterministic"),
        missing_candidate_pair_count=missing.get("count"),
        missing_candidate_pairs_sample=tuple(
            (item[0], item[1])
            for item in sample
            if isinstance(item, list) and len(item) == 2
        ),
    )


def load_neighbor_audit(
    path: str | Path,
    *,
    expected_audit_sha256: str | None = None,
    expected_identity_sha256: str | None = None,
) -> dict[str, object]:
    """Load an audit and independently revalidate every nested digest."""

    source = Path(path)
    try:
        artifact = json.loads(source.read_text(encoding="utf-8"))
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
    if reconstructed != artifact:
        raise ValueError("neighbor audit nested digest or field mismatch")
    if (
        expected_identity_sha256 is not None
        and result.identity_sha256 != expected_identity_sha256
    ):
        raise ValueError("neighbor audit identity does not match expected digest")
    return {**reconstructed, "audit_sha256": persisted_sha256}
