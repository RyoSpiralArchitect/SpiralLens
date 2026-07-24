from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import yaml

from spirallens.metrics import (
    CandidateSearchConfig,
    NeighborAuditConfig,
    NeighborAuditProtocolBinding,
    audit_neighbor_backend,
    iter_candidate_pairs,
    load_neighbor_audit,
    write_candidate_ledger,
    write_neighbor_audit,
)
from spirallens.metrics.candidate_pairs import (
    EXACT_RERANK_CONTRACT_VERSION,
    _iter_candidate_pairs_v0_1_oracle,
)
from spirallens.neighbors import (
    ExactBlockwiseBackend,
    NeighborBackendDescriptor,
    NeighborIndexBuildReceipt,
    NeighborPair,
    NeighborQuery,
    canonical_json_sha256,
    exact_state_pair_metrics,
    finite_row_norms,
    state_matrix_sha256,
)


class StaticNeighborBackend:
    def __init__(
        self,
        pairs: tuple[tuple[int, int], ...],
        *,
        name: str,
        scores: tuple[float, ...] | None = None,
        deterministic: bool = True,
        states: np.ndarray | None = None,
        row_identity_sha256: str | None = None,
        comparison_group: str = "ungrouped",
    ) -> None:
        self._pairs = pairs
        self._scores = scores or tuple(0.0 for _ in pairs)
        parameters: list[tuple[str, object]] = [
            ("fixture", name),
            ("seed", 0),
            ("thread_count", 1),
        ]
        self._index_bytes: bytes | None = None
        self._build_receipt: NeighborIndexBuildReceipt | None = None
        if states is None:
            index_sha256 = hashlib.sha256(
                name.encode("utf-8")
            ).hexdigest()
        else:
            if row_identity_sha256 is None:
                raise ValueError(
                    "prepared static backend requires row identity"
                )
            states_sha256 = state_matrix_sha256(states)
            self._index_bytes = json.dumps(
                {
                    "name": name,
                    "states_sha256": states_sha256,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            index_sha256 = hashlib.sha256(
                self._index_bytes
            ).hexdigest()
            parameters.extend(
                (
                    ("comparison_group", comparison_group),
                    ("hidden_size", int(states.shape[1])),
                    (
                        "promotion_config_sha256",
                        hashlib.sha256(name.encode("utf-8")).hexdigest(),
                    ),
                    ("row_count", int(states.shape[0])),
                    (
                        "row_identity_sha256",
                        row_identity_sha256,
                    ),
                    ("states_dtype", str(states.dtype)),
                    ("states_sha256", states_sha256),
                )
            )
        parameters.append(("index_sha256", index_sha256))
        self._descriptor = NeighborBackendDescriptor(
            backend_id=f"tests.{name}",
            backend_version="1",
            kind="approximate",
            deterministic=deterministic,
            parameters=tuple(parameters),
            runtime=(("runtime", "pytest"),),
        )
        if states is not None:
            assert row_identity_sha256 is not None
            self._build_receipt = NeighborIndexBuildReceipt(
                backend=self._descriptor,
                states_sha256=state_matrix_sha256(states),
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
        if self._build_receipt is None:
            raise AttributeError("backend was not prepared")
        return self._build_receipt

    def export_index_bytes(self) -> bytes:
        if self._index_bytes is None:
            raise AttributeError("backend was not prepared")
        return self._index_bytes

    def iter_pairs(self, states, *, query):
        del states, query
        for (left_index, right_index), score in zip(
            self._pairs,
            self._scores,
            strict=True,
        ):
            yield NeighborPair(left_index, right_index, score)


class MutatingDescriptorBackend:
    def __init__(self) -> None:
        self._mutated = False

    @property
    def descriptor(self) -> NeighborBackendDescriptor:
        return NeighborBackendDescriptor(
            backend_id="tests.mutating",
            backend_version="2" if self._mutated else "1",
            kind="approximate",
            deterministic=True,
            parameters=(
                ("index_sha256", "b" * 64),
                ("seed", 0),
                ("thread_count", 1),
            ),
            runtime=(("runtime", "pytest"),),
        )

    def iter_pairs(self, states, *, query):
        del states, query
        yield NeighborPair(0, 1, 0.0)
        self._mutated = True


class SnapshotMutatingBackend(StaticNeighborBackend):
    def iter_pairs(self, states, *, query):
        owner = states
        while isinstance(owner.base, np.ndarray):
            owner = owner.base
        owner.setflags(write=True)
        owner[-1] = owner[0]
        yield from super().iter_pairs(states, query=query)


def _candidate_fixture() -> tuple[np.ndarray, np.ndarray]:
    states = np.array(
        [
            [1.0, 0.0],
            [1.0, 0.001],
            [1.0, -0.001],
            [0.0, 1.0],
        ],
        dtype=np.float64,
    )
    drifts = np.array(
        [
            [0.0, 1.0],
            [0.0, -1.0],
            [0.0, 1.0],
            [0.0, 0.1],
        ],
        dtype=np.float64,
    )
    return states, drifts


def _candidate_config(*, block_size: int = 2) -> CandidateSearchConfig:
    return CandidateSearchConfig(
        cosine_min=0.999,
        relative_norm_gap_max=0.05,
        drift_relative_divergence_min=1.5,
        block_size=block_size,
    )


def _audit_protocol_binding(
    candidate_config: CandidateSearchConfig,
    audit_config: NeighborAuditConfig,
) -> NeighborAuditProtocolBinding:
    return NeighborAuditProtocolBinding(
        protocol_id="tests-neighbor-audit-v0.1",
        status="preregistered-draft",
        source_sha256="a" * 64,
        candidate_config_sha256=canonical_json_sha256(
            candidate_config.to_dict()
        ),
        audit_config_sha256=audit_config.sha256,
        deviations=("synthetic_fixture",),
    )


def _synthetic_source() -> dict[str, object]:
    return {
        "kind": "synthetic_fixture",
        "fixture_id": "candidate-boundary-test-v1",
        "row_identity_sha256": hashlib.sha256(
            b"candidate-boundary-test-rows"
        ).hexdigest(),
    }


def _prepared_static_backend(
    states: np.ndarray,
    pairs: tuple[tuple[int, int], ...],
    *,
    name: str,
    scores: tuple[float, ...] | None = None,
    deterministic: bool = True,
    group_key: str = "ungrouped",
) -> StaticNeighborBackend:
    return StaticNeighborBackend(
        pairs,
        name=name,
        scores=scores,
        deterministic=deterministic,
        states=states,
        row_identity_sha256=_synthetic_source()[
            "row_identity_sha256"
        ],
        comparison_group=group_key,
    )


def _candidate_source_binding(
    backend: ExactBlockwiseBackend | StaticNeighborBackend,
    config: CandidateSearchConfig,
) -> dict[str, object]:
    query = NeighborQuery(
        cosine_min=config.cosine_min,
        relative_norm_gap_max=config.relative_norm_gap_max,
        min_state_norm=config.min_state_norm,
        epsilon=config.epsilon,
    )
    descriptor = backend.descriptor
    return {
        "kind": "unit-test",
        "neighbor_retrieval": {
            "schema_version": (
                "spirallens.neighbor-retrieval-binding.v0.1"
            ),
            "groups": {
                "ungrouped": {
                    "comparison_group": "ungrouped",
                    "backend": descriptor.to_dict(),
                    "backend_sha256": descriptor.sha256,
                    "query": query.to_dict(),
                    "query_sha256": query.sha256,
                    "exact_rerank_contract": (
                        EXACT_RERANK_CONTRACT_VERSION
                    ),
                    "exact_rerank_required": True,
                    "backend_score_used_for_gates": False,
                    "audit_receipt": None,
                    "audit_receipt_sha256": None,
                }
            },
        },
    }


def _candidate_core(record: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in record.items()
        if key not in {"schema_version", "retrieval"}
    }


def test_exact_backend_pairs_are_lexicographic_and_block_invariant() -> None:
    states = np.ones((6, 3), dtype=np.float64)
    query = NeighborQuery(
        cosine_min=1.0,
        relative_norm_gap_max=0.0,
        min_state_norm=0.0,
        epsilon=1e-12,
    )
    expected = tuple(
        (left_index, right_index)
        for left_index in range(6)
        for right_index in range(left_index + 1, 6)
    )

    for block_size in (1, 2, 4):
        backend = ExactBlockwiseBackend(
            block_size=block_size,
            max_rows=6,
            max_comparisons=15,
        )
        pairs = tuple(
            pair.key for pair in backend.iter_pairs(states, query=query)
        )
        assert pairs == expected


def test_exact_backend_uses_same_inclusive_boundary_as_reranker() -> None:
    states = np.random.default_rng(3).normal(size=(2, 37))
    norms = finite_row_norms(states, block_size=1, label="states")
    boundary = exact_state_pair_metrics(
        states[0],
        states[1],
        norm_a=float(norms[0]),
        norm_b=float(norms[1]),
        epsilon=1e-12,
    ).cosine_similarity
    drifts = np.zeros_like(states)
    drifts[0, 0] = 1.0
    drifts[1, 0] = -1.0

    for block_size in (1, 2):
        records = list(
            iter_candidate_pairs(
                states,
                drifts,
                config=CandidateSearchConfig(
                    cosine_min=boundary,
                    relative_norm_gap_max=2.0,
                    drift_relative_divergence_min=1.5,
                    block_size=block_size,
                ),
            )
        )
        assert [
            (record["left"]["row_index"], record["right"]["row_index"])
            for record in records
        ] == [(0, 1)]
        assert records[0]["state_metrics"]["cosine_similarity"] == boundary


def test_exact_boundary_is_independent_of_source_row_memory_layout() -> None:
    states = np.random.default_rng(1).normal(size=(2, 7))
    norms = finite_row_norms(states, block_size=1, label="states")
    boundary = exact_state_pair_metrics(
        states[0],
        states[1],
        norm_a=float(norms[0]),
        norm_b=float(norms[1]),
        epsilon=1e-12,
    ).cosine_similarity
    drifts = np.zeros_like(states)
    drifts[0, 0] = 1.0
    drifts[1, 0] = -1.0

    for block_size in (1, 2):
        records = list(
            iter_candidate_pairs(
                states,
                drifts,
                config=CandidateSearchConfig(
                    cosine_min=boundary,
                    relative_norm_gap_max=100.0,
                    drift_relative_divergence_min=0.0,
                    block_size=block_size,
                ),
            )
        )
        assert [
            (record["left"]["row_index"], record["right"]["row_index"])
            for record in records
        ] == [(0, 1)]
        assert records[0]["state_metrics"]["cosine_similarity"] == boundary


def test_exact_backend_query_subset_covers_only_touching_pairs() -> None:
    states = np.ones((5, 2), dtype=np.float64)
    query = NeighborQuery(
        cosine_min=0.999999,
        relative_norm_gap_max=0.0,
        min_state_norm=0.0,
        epsilon=1e-12,
        query_indices=(1, 3),
    )
    pairs = tuple(
        pair.key
        for pair in ExactBlockwiseBackend(
            block_size=2,
            max_rows=2,
            max_comparisons=7,
        ).iter_pairs(states, query=query)
    )

    assert pairs == (
        (0, 1),
        (0, 3),
        (1, 2),
        (1, 3),
        (1, 4),
        (2, 3),
        (3, 4),
    )


def test_candidate_results_and_order_do_not_depend_on_block_size() -> None:
    states, drifts = _candidate_fixture()
    outputs = []
    for block_size in (1, 2, 3):
        outputs.append(
            [
                _candidate_core(record)
                for record in iter_candidate_pairs(
                    states,
                    drifts,
                    config=_candidate_config(block_size=block_size),
                    source_run_id="block-invariant",
                    group_key="layer_index=0",
                )
            ]
        )

    assert outputs[0] == outputs[1] == outputs[2]
    assert [
        (record["left"]["row_index"], record["right"]["row_index"])
        for record in outputs[0]
    ] == [(0, 1), (1, 2)]


def test_exact_backend_preserves_pre_backend_candidate_oracle() -> None:
    states, drifts = _candidate_fixture()
    config = _candidate_config(block_size=1)
    references = [{"token_id": index} for index in range(states.shape[0])]
    legacy = [
        _candidate_core(record)
        for record in _iter_candidate_pairs_v0_1_oracle(
            states,
            drifts,
            references=references,
            config=config,
            source_run_id="parity",
            group_key="layer_index=0",
        )
    ]
    current = [
        _candidate_core(record)
        for record in iter_candidate_pairs(
            states,
            drifts,
            references=references,
            config=config,
            source_run_id="parity",
            group_key="layer_index=0",
        )
    ]

    assert len(current) == len(legacy)
    for current_record, legacy_record in zip(
        current,
        legacy,
        strict=True,
    ):
        for field in (
            "candidate_id",
            "candidate_kind",
            "claim_level",
            "source_run_id",
            "comparison_group",
            "left",
            "right",
            "discovery",
            "gates",
        ):
            assert current_record[field] == legacy_record[field]
        assert current_record["state_metrics"] == pytest.approx(
            legacy_record["state_metrics"],
            abs=1e-12,
        )
        assert current_record["drift_metrics"] == pytest.approx(
            legacy_record["drift_metrics"],
            abs=1e-12,
        )


@pytest.mark.parametrize(
    "pairs",
    (
        ((0, 2), (0, 1)),
        ((0, 1), (0, 1)),
    ),
)
def test_candidate_search_rejects_unordered_or_duplicate_backend_pairs(
    pairs: tuple[tuple[int, int], ...],
) -> None:
    states, drifts = _candidate_fixture()
    backend = StaticNeighborBackend(pairs, name="invalid-order")

    with pytest.raises(ValueError, match="lexicographically ordered"):
        list(
            iter_candidate_pairs(
                states,
                drifts,
                config=_candidate_config(),
                neighbor_backend=backend,
            )
        )


def test_candidate_search_rejects_out_of_range_backend_pair() -> None:
    states, drifts = _candidate_fixture()

    with pytest.raises(ValueError, match="exceeds row_count"):
        list(
            iter_candidate_pairs(
                states,
                drifts,
                config=_candidate_config(),
                neighbor_backend=StaticNeighborBackend(
                    ((0, 99),),
                    name="out-of-range",
                ),
            )
        )


def test_candidate_search_rejects_reference_row_mismatch() -> None:
    states, drifts = _candidate_fixture()
    references = [
        {"row_index": 99},
        {"row_index": 1},
        {"row_index": 2},
        {"row_index": 3},
    ]

    with pytest.raises(ValueError, match="must equal its matrix row"):
        list(
            iter_candidate_pairs(
                states,
                drifts,
                references=references,
                config=_candidate_config(),
            )
        )


def test_backend_score_never_changes_exact_candidate_metrics() -> None:
    states, drifts = _candidate_fixture()
    low_score = StaticNeighborBackend(
        ((0, 1),),
        name="low-score",
        scores=(-1_000_000.0,),
    )
    high_score = StaticNeighborBackend(
        ((0, 1),),
        name="high-score",
        scores=(1_000_000.0,),
    )
    low = list(
        iter_candidate_pairs(
            states,
            drifts,
            config=_candidate_config(),
            neighbor_backend=low_score,
        )
    )[0]
    high = list(
        iter_candidate_pairs(
            states,
            drifts,
            config=_candidate_config(),
            neighbor_backend=high_score,
        )
    )[0]

    assert low["state_metrics"] == high["state_metrics"]
    assert low["drift_metrics"] == high["drift_metrics"]
    assert low["candidate_id"] == high["candidate_id"]
    assert low["retrieval"]["backend_score_used_for_gates"] is False


def test_candidate_search_rejects_descriptor_mutation() -> None:
    states, drifts = _candidate_fixture()

    with pytest.raises(ValueError, match="descriptor changed"):
        list(
            iter_candidate_pairs(
                states,
                drifts,
                config=_candidate_config(),
                neighbor_backend=MutatingDescriptorBackend(),
            )
        )


def test_candidate_ledger_rejects_header_row_backend_mismatch(
    tmp_path: Path,
) -> None:
    states, drifts = _candidate_fixture()
    config = _candidate_config(block_size=1)
    records = list(
        iter_candidate_pairs(
            states,
            drifts,
            config=config,
            source_run_id="ledger-binding",
        )
    )
    different_backend = ExactBlockwiseBackend(
        block_size=2,
        max_rows=config.max_pairwise_rows,
        max_comparisons=(
            config.max_pairwise_rows
            * (config.max_pairwise_rows - 1)
            // 2
        ),
    )
    output = tmp_path / "mismatch.jsonl"

    with pytest.raises(ValueError, match="does not match"):
        write_candidate_ledger(
            records,
            output,
            source=_candidate_source_binding(
                different_backend,
                config,
            ),
            config=config,
            protocol_id="unit-test",
        )
    assert not output.exists()


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("backend_id", "tests.tampered"),
        ("backend_kind", "approximate"),
    ),
)
def test_candidate_ledger_rejects_redundant_backend_field_mismatch(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    states, drifts = _candidate_fixture()
    config = _candidate_config(block_size=1)
    backend = ExactBlockwiseBackend(
        block_size=config.block_size,
        max_rows=config.max_pairwise_rows,
        max_comparisons=(
            config.max_pairwise_rows
            * (config.max_pairwise_rows - 1)
            // 2
        ),
    )
    records = list(
        iter_candidate_pairs(
            states,
            drifts,
            config=config,
            source_run_id="ledger-redundant-binding",
            neighbor_backend=backend,
        )
    )
    records[0] = dict(records[0])
    records[0]["retrieval"] = dict(records[0]["retrieval"])
    records[0]["retrieval"][field] = value
    output = tmp_path / f"mismatch-{field}.jsonl"

    with pytest.raises(ValueError, match="does not match"):
        write_candidate_ledger(
            records,
            output,
            source=_candidate_source_binding(backend, config),
            config=config,
            protocol_id="unit-test",
        )
    assert not output.exists()


def test_candidate_ledger_blocks_approximate_persistence_without_receipt(
    tmp_path: Path,
) -> None:
    states, drifts = _candidate_fixture()
    config = _candidate_config()
    backend = StaticNeighborBackend(((0, 1),), name="unpromoted")
    records = list(
        iter_candidate_pairs(
            states,
            drifts,
            config=config,
            neighbor_backend=backend,
        )
    )

    with pytest.raises(ValueError, match="matching audit receipt"):
        write_candidate_ledger(
            records,
            tmp_path / "must-not-exist.jsonl",
            source=_candidate_source_binding(backend, config),
            config=config,
            protocol_id="unit-test",
        )


def test_candidate_boundary_audit_passes_only_after_exact_rerank() -> None:
    states, drifts = _candidate_fixture()
    pairs = (
        (
            0,
            1,
        ),
        (0, 2),
        (0, 3),
        (1, 2),
    )
    candidate_config = _candidate_config()
    audit_config = NeighborAuditConfig(candidate_recall_min=0.99)
    result = audit_neighbor_backend(
        states,
        drifts,
        subject_backend_factory=lambda backend_states: _prepared_static_backend(
            backend_states,
            pairs,
            name="complete-with-false-proposal",
        ),
        protocol_binding=_audit_protocol_binding(
            candidate_config,
            audit_config,
        ),
        source_identity=_synthetic_source(),
        candidate_config=candidate_config,
        audit_config=audit_config,
    )
    payload = result.to_dict()

    assert result.status == "pass"
    assert result.reference_candidate_count == 2
    assert result.repeat_candidate_counts == (2, 2)
    assert result.candidate_boundary_recall == (1.0, 1.0)
    assert result.retrieval_boundary_recall == (1.0, 1.0)
    assert payload["exact_rerank"]["false_persistable_candidates"] == 0
    assert payload["promotion_contract"][
        "actual_approximate_backend_promoted"
    ] is False
    assert payload["top_k_diagnostic"]["status"] == "not_run"


def test_candidate_boundary_audit_rejects_non_exact_reference_backend() -> None:
    states, drifts = _candidate_fixture()
    candidate_config = _candidate_config()
    audit_config = NeighborAuditConfig()
    fake_reference = StaticNeighborBackend(
        ((0, 1), (0, 2), (1, 2)),
        name="fake-reference",
    )

    with pytest.raises(TypeError, match="reference_backend"):
        audit_neighbor_backend(
            states,
            drifts,
            subject_backend_factory=lambda backend_states: _prepared_static_backend(
                backend_states,
                ((0, 1), (0, 2), (1, 2)),
                name="subject",
            ),
            protocol_binding=_audit_protocol_binding(
                candidate_config,
                audit_config,
            ),
            source_identity=_synthetic_source(),
            candidate_config=candidate_config,
            audit_config=audit_config,
            reference_backend=fake_reference,  # type: ignore[arg-type]
        )


def test_candidate_boundary_audit_rejects_subject_input_mutation() -> None:
    states, drifts = _candidate_fixture()
    original_states = states.copy()
    original_drifts = drifts.copy()
    candidate_config = _candidate_config()
    audit_config = NeighborAuditConfig()

    with pytest.raises(ValueError, match="input snapshot changed"):
        audit_neighbor_backend(
            states,
            drifts,
            subject_backend_factory=lambda backend_states: SnapshotMutatingBackend(
                ((0, 1), (0, 2), (1, 2)),
                name="input-mutator",
                states=backend_states,
                row_identity_sha256=_synthetic_source()[
                    "row_identity_sha256"
                ],
            ),
            protocol_binding=_audit_protocol_binding(
                candidate_config,
                audit_config,
            ),
            source_identity=_synthetic_source(),
            candidate_config=candidate_config,
            audit_config=audit_config,
        )

    np.testing.assert_array_equal(states, original_states)
    np.testing.assert_array_equal(drifts, original_drifts)


def test_candidate_boundary_audit_fails_for_lossy_backend() -> None:
    states, drifts = _candidate_fixture()
    candidate_config = _candidate_config()
    audit_config = NeighborAuditConfig(candidate_recall_min=0.99)
    result = audit_neighbor_backend(
        states,
        drifts,
        subject_backend_factory=lambda backend_states: _prepared_static_backend(
            backend_states,
            ((0, 1),),
            name="lossy",
        ),
        protocol_binding=_audit_protocol_binding(
            candidate_config,
            audit_config,
        ),
        source_identity=_synthetic_source(),
        candidate_config=candidate_config,
        audit_config=audit_config,
    )

    assert result.status == "fail"
    assert result.candidate_boundary_recall == (0.5, 0.5)
    assert result.missing_candidate_pair_count == 1
    assert result.missing_candidate_pairs_sample == ((1, 2),)


def test_zero_reference_candidates_are_insufficient_not_perfect() -> None:
    states, drifts = _candidate_fixture()
    drifts[:] = [0.0, 1.0]
    backend = ExactBlockwiseBackend(
        block_size=2,
        max_rows=4,
        max_comparisons=6,
    )
    candidate_config = _candidate_config()
    audit_config = NeighborAuditConfig()
    result = audit_neighbor_backend(
        states,
        drifts,
        subject_backend_factory=lambda _backend_states: ExactBlockwiseBackend(
            block_size=backend.block_size,
            max_rows=backend.max_rows,
            max_comparisons=backend.max_comparisons,
        ),
        protocol_binding=_audit_protocol_binding(
            candidate_config,
            audit_config,
        ),
        source_identity=_synthetic_source(),
        candidate_config=candidate_config,
        audit_config=audit_config,
    )

    assert result.status == "insufficient"
    assert result.reference_candidate_count == 0
    assert result.candidate_boundary_recall == (None, None)


def test_repeat_membership_change_fails_determinism_gate() -> None:
    states, drifts = _candidate_fixture()
    sequences = iter(
        (((0, 1), (0, 2), (1, 2)), ((0, 1),))
    )
    candidate_config = _candidate_config()
    audit_config = NeighborAuditConfig()
    result = audit_neighbor_backend(
        states,
        drifts,
        subject_backend_factory=lambda backend_states: _prepared_static_backend(
            backend_states,
            next(sequences),
            name="alternating",
        ),
        protocol_binding=_audit_protocol_binding(
            candidate_config,
            audit_config,
        ),
        source_identity=_synthetic_source(),
        candidate_config=candidate_config,
        audit_config=audit_config,
    )

    assert result.status == "fail"
    assert result.deterministic is False
    assert len(set(result.repeat_pair_sha256)) == 2


def test_neighbor_audit_artifact_is_atomic_and_tamper_evident(
    tmp_path: Path,
) -> None:
    states, drifts = _candidate_fixture()
    candidate_config = _candidate_config()
    audit_config = NeighborAuditConfig()
    result = audit_neighbor_backend(
        states,
        drifts,
        subject_backend_factory=lambda backend_states: _prepared_static_backend(
            backend_states,
            ((0, 1), (0, 2), (1, 2)),
            name="artifact",
        ),
        protocol_binding=_audit_protocol_binding(
            candidate_config,
            audit_config,
        ),
        source_identity=_synthetic_source(),
        candidate_config=candidate_config,
        audit_config=audit_config,
    )
    output = tmp_path / "neighbor-audit.json"
    write_neighbor_audit(result, output)
    loaded = load_neighbor_audit(output)

    assert loaded["audit_sha256"] == result.sha256
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        write_neighbor_audit(result, output)

    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["metrics"]["candidate_boundary_recall"][0] = 0.0
    output.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="digest mismatch"):
        load_neighbor_audit(output)

    payload_without_sha = {
        key: value
        for key, value in payload.items()
        if key != "audit_sha256"
    }
    payload["audit_sha256"] = canonical_json_sha256(payload_without_sha)
    output.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="candidate recall disagrees"):
        load_neighbor_audit(output)

    with pytest.raises(ValueError, match="determinism flag"):
        replace(result, deterministic=False)
    with pytest.raises(ValueError, match="reference_backend"):
        replace(
            result,
            reference_backend=StaticNeighborBackend(
                (),
                name="forged-reference",
            ).descriptor,
        )


def test_audit_identity_binds_run_and_comparison_group() -> None:
    states, drifts = _candidate_fixture()
    candidate_config = _candidate_config()
    audit_config = NeighborAuditConfig()
    binding = _audit_protocol_binding(candidate_config, audit_config)

    def run(source_run_id: str, group_key: str):
        return audit_neighbor_backend(
            states,
            drifts,
            subject_backend_factory=lambda backend_states: _prepared_static_backend(
                backend_states,
                ((0, 1), (0, 2), (1, 2)),
                name="identity",
                group_key=group_key,
            ),
            protocol_binding=binding,
            source_identity=_synthetic_source(),
            candidate_config=candidate_config,
            audit_config=audit_config,
            source_run_id=source_run_id,
            group_key=group_key,
        )

    left = run("run-a", "layer_index=0")
    right = run("run-b", "layer_index=99")

    assert left.identity_sha256 != right.identity_sha256
    assert left.sha256 != right.sha256


def test_tracked_neighbor_protocol_binds_unchanged_candidate_protocol() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "protocols" / "pythia_neighbor_v0_2.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    candidate_path = root / payload["candidate_protocol"]["path"]
    candidate_sha256 = hashlib.sha256(candidate_path.read_bytes()).hexdigest()

    assert payload["schema_version"] == (
        "spirallens.neighbor-audit-protocol.v0.1"
    )
    assert payload["candidate_protocol"]["sha256"] == candidate_sha256
    assert payload["audit"]["candidate_boundary_recall_min"] == 0.99
    assert payload["audit"]["minimum_reference_candidates"] == 100
    assert payload["audit"]["zero_reference_candidates"] == "insufficient"
    assert (
        payload["audit"][
            "full_vocabulary_backend_promoted_by_this_protocol"
        ]
        is False
    )
    assert payload["subject_backend"]["status"] == (
        "implementation_selected_unpromoted"
    )
    assert payload["subject_backend"]["backend_id"] == (
        "spirallens.faiss-hnsw-range"
    )
    assert payload["subject_backend"]["distribution_version"] == "1.14.3"
    assert payload["subject_backend"]["config"]["thread_count"] == 1
    assert payload["query_sampling"] == {
        "method": "sha256_ranked_global_indices",
        "seed": 1729,
        "count": 1000,
        "global_row_key_sha256": None,
        "binding_rule": "must_be_filled_before_status_frozen",
    }
    assert (
        payload["claim_boundary"]["approximate_backend_currently_audited"]
        is False
    )
    assert payload["promotion_readiness"][
        "query_local_worst_case_recall_gate_implemented"
    ] is False
    assert payload["claim_boundary"][
        "approximate_backend_currently_audited"
    ] is False
