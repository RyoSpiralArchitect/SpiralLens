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
    NeighborAuditResult,
    load_neighbor_audit_result,
)


NEIGHBOR_AUDIT_RECEIPT_SCHEMA_VERSION = (
    "spirallens.neighbor-audit-receipt.v0.1"
)
_VERIFIED_RECEIPT_TOKEN = object()


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
    try:
        protocol = yaml.safe_load(protocol_bytes)
    except yaml.YAMLError as error:
        raise ValueError(
            f"invalid neighbor audit protocol: {path}"
        ) from error
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
) -> tuple[Mapping[str, object], CandidateSearchConfig]:
    try:
        payload = yaml.safe_load(payload_bytes)
    except yaml.YAMLError as error:
        raise ValueError("candidate protocol YAML is invalid") from error
    if not isinstance(payload, Mapping):
        raise ValueError("candidate protocol must contain a mapping")
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


def _validate_promotion_protocol(
    result: NeighborAuditResult,
    *,
    protocol_path: Path,
    protocol_bytes: bytes,
    protocol: Mapping[str, object],
) -> tuple[str, str]:
    """Match every promotion-bearing protocol field to the audit."""

    if (
        protocol.get("schema_version")
        != "spirallens.neighbor-audit-protocol.v0.1"
        or protocol.get("protocol_id")
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
        or scope.get("comparison_group") != expected_group
        or result.comparison_group != expected_group
    ):
        raise ValueError(
            "audit comparison group differs from frozen protocol"
        )

    candidate_binding = protocol.get("candidate_protocol")
    if not isinstance(candidate_binding, Mapping):
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
        "candidate_boundary_recall_min": (
            result.audit_config.candidate_recall_min
        ),
        "repeats": result.audit_config.repeats,
        "minimum_reference_candidates": (
            result.audit_config.minimum_reference_candidates
        ),
        "missing_pair_sample_limit": (
            result.audit_config.missing_pair_sample_limit
        ),
    }
    if (
        not isinstance(audit, Mapping)
        or any(
            audit.get(key) != value
            for key, value in expected_audit.items()
        )
        or audit.get("primary_metric")
        != "candidate_boundary_recall"
        or audit.get("repeat_mode")
        != "independent_cold_rebuild"
        or audit.get("zero_reference_candidates") != "insufficient"
        or audit.get("full_vocabulary_backend_promoted_by_this_protocol")
        is not True
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
    if any(
        sampling.get(key) != value
        for key, value in expected_sampling.items()
    ):
        raise ValueError(
            "audit query selection differs from frozen protocol"
        )
    if result.query.query_indices != selection.select(result.row_count):
        raise ValueError(
            "audit query rows differ from frozen selection"
        )

    subject = protocol.get("subject_backend")
    subject_parameters = dict(result.subject_backend.parameters)
    subject_runtime = dict(result.subject_backend.runtime)
    if (
        not isinstance(subject, Mapping)
        or subject.get("backend_id")
        != result.subject_backend.backend_id
        or str(subject.get("backend_version"))
        != result.subject_backend.backend_version
        or subject.get("kind_required_for_full_vocabulary")
        != "approximate"
        or subject.get("candidate_persistence_without_audit_receipt")
        != "forbidden"
        or not isinstance(subject.get("config"), Mapping)
        or any(
            subject_parameters.get(key) != value
            for key, value in subject["config"].items()
        )
    ):
        raise ValueError(
            "subject backend differs from frozen protocol"
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

    retrieval = protocol.get("retrieval_contract")
    if (
        not isinstance(retrieval, Mapping)
        or retrieval.get("input") != "resid_pre"
        or retrieval.get("metric") != "cosine"
        or retrieval.get("drift_available_to_backend") is not False
        or retrieval.get("decoded_strings_available_to_backend") is not False
        or retrieval.get("semantic_annotation_available_to_backend")
        is not False
        or retrieval.get("sae_annotation_available_to_backend") is not False
        or retrieval.get("projected_coordinates_available_to_backend")
        is not False
    ):
        raise ValueError(
            "retrieval isolation differs from frozen protocol"
        )
    rerank = protocol.get("exact_rerank")
    if (
        not isinstance(rerank, Mapping)
        or rerank.get("contract") != EXACT_RERANK_CONTRACT_VERSION
        or rerank.get("required_before_persist") is not True
        or rerank.get("backend_score_used_for_gate") is not False
        or rerank.get("false_persistable_candidates_allowed") != 0
    ):
        raise ValueError(
            "exact rerank policy differs from frozen protocol"
        )
    claim_boundary = protocol.get("claim_boundary")
    if (
        not isinstance(claim_boundary, Mapping)
        or claim_boundary.get("semantics_free") is not True
        or claim_boundary.get("candidate_is_not_verified_vortex")
        is not True
        or claim_boundary.get(
            "passing_audit_proves_retrieval_coverage_only"
        )
        is not True
    ):
        raise ValueError(
            "claim boundary differs from frozen protocol"
        )
    if (
        candidate_path.read_bytes() != candidate_bytes
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
