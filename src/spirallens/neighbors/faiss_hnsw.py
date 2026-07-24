"""Prepared Faiss HNSW range-search backend.

Faiss build and search execute in private subprocesses. Besides avoiding
process-global OpenMP collisions with Torch, this keeps the ANN worker on the
state-only side of the discovery boundary.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
import hashlib
import importlib.util
import json
from numbers import Integral, Real
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np
from numpy.typing import ArrayLike

from .contracts import (
    NeighborBackendDescriptor,
    NeighborIndexBuildReceipt,
    NeighborPair,
    NeighborQuery,
    canonical_json_sha256,
    state_matrix_sha256,
)
from .scoring import conservative_dot_tolerance, finite_row_norms


FAISS_HNSW_BACKEND_ID = "spirallens.faiss-hnsw-range"
FAISS_HNSW_BACKEND_VERSION = "0.1"
FAISS_DISTRIBUTION_VERSION = "1.14.3"


def _require_sha256(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _require_faiss_distribution() -> None:
    if importlib.util.find_spec("faiss") is None:
        raise ImportError(
            "Faiss HNSW requires the optional ANN dependency; install "
            "with `pip install 'spirallens[ann]'`"
        )


def _run_worker(
    arguments: list[str],
    *,
    runtime_contract: Mapping[str, str],
) -> None:
    environment = os.environ.copy()
    environment["SPIRALLENS_FAISS_WORKER_RUNTIME_CONTRACT"] = (
        json.dumps(
            dict(runtime_contract),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "spirallens.neighbors._faiss_worker",
            *arguments,
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(
            "Faiss worker failed"
            + (f": {detail}" if detail else "")
        )


def _worker_state_bytes_sha256(path: Path) -> str:
    rows = np.load(path, mmap_mode="r", allow_pickle=False)
    if rows.ndim != 2 or rows.dtype != np.float32:
        raise ValueError("Faiss worker state cache is malformed")
    contiguous = np.ascontiguousarray(rows)
    return hashlib.sha256(memoryview(contiguous).cast("B")).hexdigest()


@dataclass(frozen=True)
class FaissHNSWConfig:
    """Construction and range-search settings frozen into index identity."""

    m: int = 32
    ef_construction: int = 200
    ef_search: int = 256
    seed: int = 1729
    thread_count: int = 1
    query_batch_size: int = 512
    score_margin: float = 1e-4
    max_raw_hits: int = 20_000_000
    max_proposed_pairs: int = 10_000_000

    def __post_init__(self) -> None:
        for field_name in (
            "m",
            "ef_construction",
            "ef_search",
            "seed",
            "thread_count",
            "query_batch_size",
            "max_raw_hits",
            "max_proposed_pairs",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, Integral):
                raise TypeError(f"{field_name} must be an integer")
            object.__setattr__(self, field_name, int(value))
        if self.m < 2:
            raise ValueError("m must be at least 2")
        if self.ef_construction <= 0 or self.ef_search <= 0:
            raise ValueError(
                "ef_construction and ef_search must be positive"
            )
        if self.thread_count != 1:
            raise ValueError(
                "thread_count must be 1 for reproducible HNSW builds"
            )
        if self.query_batch_size <= 0:
            raise ValueError("query_batch_size must be positive")
        if self.max_raw_hits <= 0 or self.max_proposed_pairs <= 0:
            raise ValueError(
                "max_raw_hits and max_proposed_pairs must be positive"
            )
        if (
            isinstance(self.score_margin, bool)
            or not isinstance(self.score_margin, Real)
            or not np.isfinite(self.score_margin)
        ):
            raise TypeError("score_margin must be a finite real")
        if not 0.0 <= self.score_margin <= 0.1:
            raise ValueError("score_margin must lie in [0, 0.1]")
        object.__setattr__(self, "score_margin", float(self.score_margin))

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class FaissHNSWBackend:
    """One prepared, full-input Faiss HNSW cosine index."""

    def __init__(
        self,
        states: ArrayLike,
        *,
        row_identity_sha256: str,
        comparison_group: str,
        config: FaissHNSWConfig | None = None,
        worker_runtime_contract: Mapping[str, str] | None = None,
    ) -> None:
        from spirallens.execution_freeze import (
            current_worker_runtime_contract,
        )

        settings = config or FaissHNSWConfig()
        if not isinstance(settings, FaissHNSWConfig):
            raise TypeError("config must be a FaissHNSWConfig")
        _require_faiss_distribution()
        _require_sha256(
            row_identity_sha256,
            label="row_identity_sha256",
        )
        if (
            not isinstance(comparison_group, str)
            or not comparison_group
        ):
            raise TypeError(
                "comparison_group must be a non-empty string"
            )
        frozen_runtime = (
            None
            if worker_runtime_contract is None
            else dict(worker_runtime_contract)
        )
        if frozen_runtime is not None and (
            not frozen_runtime
            or any(
                not isinstance(key, str)
                or not key
                or not isinstance(value, str)
                or not value
                for key, value in frozen_runtime.items()
            )
        ):
            raise ValueError("worker_runtime_contract is invalid")
        freeze_sha256 = (
            frozen_runtime.get("execution_freeze_sha256")
            if frozen_runtime is not None
            else None
        )
        actual_runtime = current_worker_runtime_contract(
            freeze_sha256
        )
        if (
            frozen_runtime is not None
            and frozen_runtime != actual_runtime
        ):
            raise ValueError(
                "current Faiss worker runtime differs from its contract"
            )
        self._worker_runtime_contract = actual_runtime
        source_rows = np.asanyarray(states)
        if source_rows.ndim != 2:
            raise ValueError(
                "states must have shape (observations, hidden)"
            )
        if source_rows.shape[0] <= 0 or source_rows.shape[1] <= 0:
            raise ValueError("states must contain at least one row/value")
        states_sha256 = state_matrix_sha256(source_rows)
        rows = np.array(
            source_rows,
            dtype=np.float32,
            order="C",
            copy=True,
        )
        if not np.all(np.isfinite(rows)):
            raise ValueError("states contain non-finite values")

        workdir = tempfile.TemporaryDirectory(
            prefix="spirallens-faiss-hnsw-"
        )
        root = Path(workdir.name)
        states_path = root / "states.npy"
        index_path = root / "index.faiss"
        metadata_path = root / "metadata.json"
        np.save(states_path, rows, allow_pickle=False)
        worker_states_sha256 = _worker_state_bytes_sha256(states_path)
        _run_worker(
            [
                "build",
                "--states",
                str(states_path),
                "--index",
                str(index_path),
                "--metadata",
                str(metadata_path),
                "--m",
                str(settings.m),
                "--ef-construction",
                str(settings.ef_construction),
                "--ef-search",
                str(settings.ef_search),
                "--seed",
                str(settings.seed),
            ],
            runtime_contract=self._worker_runtime_contract,
        )
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not isinstance(metadata, dict):
            raise RuntimeError("Faiss worker metadata is malformed")
        index_bytes = index_path.read_bytes()
        index_sha256 = hashlib.sha256(index_bytes).hexdigest()
        if (
            metadata.get("index_sha256") != index_sha256
            or metadata.get("runtime")
            != self._worker_runtime_contract
            or metadata.get("faiss_version")
            != FAISS_DISTRIBUTION_VERSION
            or metadata.get("worker_states_sha256")
            != worker_states_sha256
            or metadata.get("row_count") != int(source_rows.shape[0])
            or metadata.get("hidden_size") != int(source_rows.shape[1])
            or metadata.get("thread_count") != 1
        ):
            raise RuntimeError(
                "Faiss worker metadata differs from its build artifact"
            )
        normalized_states_sha256 = _require_sha256(
            metadata.get("normalized_states_sha256"),
            label="normalized_states_sha256",
        )
        runtime = tuple(sorted(self._worker_runtime_contract.items()))
        promotion_config = {
            "backend_id": FAISS_HNSW_BACKEND_ID,
            "backend_version": FAISS_HNSW_BACKEND_VERSION,
            "metric": "cosine",
            "index_type": "IndexHNSWFlat",
            "faiss_metric": "METRIC_INNER_PRODUCT",
            "normalization": "faiss.normalize_L2(float32)",
            "range_search": True,
            "worker_isolation": "fresh_python_subprocess",
            "config": settings.to_dict(),
            "runtime": dict(runtime),
        }
        promotion_config_sha256 = canonical_json_sha256(
            promotion_config
        )
        parameters = (
            ("build_dtype", "float32"),
            ("comparison_group", comparison_group),
            ("ef_construction", settings.ef_construction),
            ("ef_search", settings.ef_search),
            ("hidden_size", int(source_rows.shape[1])),
            ("index_sha256", index_sha256),
            ("index_type", "IndexHNSWFlat"),
            ("m", settings.m),
            ("max_raw_hits", settings.max_raw_hits),
            ("max_proposed_pairs", settings.max_proposed_pairs),
            ("normalization", "l2_float32_before_inner_product"),
            (
                "normalized_states_sha256",
                normalized_states_sha256,
            ),
            ("pair_order", "left_then_right_ascending"),
            (
                "promotion_config_sha256",
                promotion_config_sha256,
            ),
            ("query_batch_size", settings.query_batch_size),
            ("range_search", True),
            ("row_count", int(source_rows.shape[0])),
            ("row_identity_sha256", row_identity_sha256),
            ("score_margin", settings.score_margin),
            ("seed", settings.seed),
            ("seed_semantics", "faiss_hnsw_level_rng"),
            ("states_dtype", str(source_rows.dtype)),
            ("states_sha256", states_sha256),
            ("thread_count", settings.thread_count),
            ("worker_isolation", "fresh_python_subprocess"),
            ("worker_states_sha256", worker_states_sha256),
        )
        descriptor = NeighborBackendDescriptor(
            backend_id=FAISS_HNSW_BACKEND_ID,
            backend_version=FAISS_HNSW_BACKEND_VERSION,
            kind="approximate",
            deterministic=True,
            parameters=parameters,
            runtime=runtime,
        )
        receipt = NeighborIndexBuildReceipt(
            backend=descriptor,
            states_sha256=states_sha256,
            row_identity_sha256=row_identity_sha256,
            index_sha256=index_sha256,
            comparison_group=comparison_group,
            row_count=int(source_rows.shape[0]),
            hidden_size=int(source_rows.shape[1]),
            states_dtype=str(source_rows.dtype),
        )
        if state_matrix_sha256(source_rows) != states_sha256:
            raise ValueError("states changed during Faiss index build")

        self._config = settings
        self._descriptor = descriptor
        self._build_receipt = receipt
        self._index_bytes = index_bytes
        self._workdir = workdir
        self._states_path = states_path
        self._index_path = index_path
        self._worker_states_sha256 = worker_states_sha256

    @property
    def config(self) -> FaissHNSWConfig:
        return self._config

    @property
    def descriptor(self) -> NeighborBackendDescriptor:
        return self._descriptor

    @property
    def build_receipt(self) -> NeighborIndexBuildReceipt:
        return self._build_receipt

    def export_index_bytes(self) -> bytes:
        current = self._index_path.read_bytes()
        if current != self._index_bytes:
            raise ValueError("prepared Faiss index bytes changed on disk")
        return current

    def iter_pairs(
        self,
        states: ArrayLike,
        *,
        query: NeighborQuery,
    ):
        if not isinstance(query, NeighborQuery):
            raise TypeError("query must be a NeighborQuery")
        source_rows = np.asanyarray(states)
        receipt = self._build_receipt
        if (
            source_rows.ndim != 2
            or source_rows.shape
            != (receipt.row_count, receipt.hidden_size)
            or str(source_rows.dtype) != receipt.states_dtype
            or state_matrix_sha256(source_rows)
            != receipt.states_sha256
        ):
            raise ValueError(
                "query states do not match the prepared Faiss index"
            )
        if (
            query.query_indices
            and query.query_indices[-1] >= receipt.row_count
        ):
            raise ValueError(
                "query_indices contain a row outside the state matrix"
            )
        query_indices = np.asarray(
            (
                tuple(range(receipt.row_count))
                if query.query_indices is None
                else query.query_indices
            ),
            dtype=np.int64,
        )
        if query_indices.size == 0:
            return

        state_norms = finite_row_norms(
            source_rows,
            block_size=self._config.query_batch_size,
            label="states",
        )
        norm_tolerance = conservative_dot_tolerance(
            receipt.hidden_size
        )
        radius = float(
            np.nextafter(
                np.float32(
                    max(-1.0, query.cosine_min - self._config.score_margin)
                ),
                np.float32(-np.inf),
            )
        )
        proposed: dict[tuple[int, int], float] = {}
        if (
            _worker_state_bytes_sha256(self._states_path)
            != self._worker_states_sha256
        ):
            raise ValueError(
                "Faiss worker state cache differs from the prepared input"
            )
        with tempfile.TemporaryDirectory(
            prefix="search-",
            dir=self._workdir.name,
        ) as search_directory:
            search_root = Path(search_directory)
            query_path = search_root / "query-indices.npy"
            manifest_path = search_root / "manifest.json"
            np.save(query_path, query_indices, allow_pickle=False)
            _run_worker(
                [
                    "search",
                    "--states",
                    str(self._states_path),
                    "--index",
                    str(self._index_path),
                    "--query-indices",
                    str(query_path),
                    "--output-dir",
                    str(search_root),
                    "--manifest",
                    str(manifest_path),
                    "--ef-search",
                    str(self._config.ef_search),
                    "--query-batch-size",
                    str(self._config.query_batch_size),
                    "--max-raw-hits",
                    str(self._config.max_raw_hits),
                    "--radius",
                    repr(radius),
                ],
                runtime_contract=self._worker_runtime_contract,
            )
            manifest = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )
            if (
                not isinstance(manifest, dict)
                or manifest.get("query_count")
                != int(query_indices.size)
                or not isinstance(manifest.get("files"), list)
            ):
                raise RuntimeError(
                    "Faiss search worker manifest is malformed"
                )
            for filename in manifest["files"]:
                if (
                    not isinstance(filename, str)
                    or Path(filename).name != filename
                ):
                    raise RuntimeError(
                        "Faiss search worker emitted an unsafe path"
                    )
                with np.load(
                    search_root / filename,
                    allow_pickle=False,
                ) as payload:
                    batch_indices = payload["batch_indices"]
                    limits = payload["limits"]
                    scores = payload["scores"]
                    labels = payload["labels"]
                    for local_index, query_index_value in enumerate(
                        batch_indices
                    ):
                        query_index = int(query_index_value)
                        norm_a = float(state_norms[query_index])
                        lower = int(limits[local_index])
                        upper = int(limits[local_index + 1])
                        for offset in range(lower, upper):
                            neighbor_index = int(labels[offset])
                            if (
                                neighbor_index < 0
                                or neighbor_index == query_index
                            ):
                                continue
                            norm_b = float(state_norms[neighbor_index])
                            relative_norm_gap = abs(norm_a - norm_b) / max(
                                0.5 * (norm_a + norm_b),
                                query.epsilon,
                            )
                            if (
                                norm_a < query.min_state_norm
                                or norm_b < query.min_state_norm
                                or relative_norm_gap
                                > query.relative_norm_gap_max
                                + norm_tolerance
                            ):
                                continue
                            key = (
                                min(query_index, neighbor_index),
                                max(query_index, neighbor_index),
                            )
                            score = float(scores[offset])
                            previous = proposed.get(key)
                            if previous is None or score > previous:
                                proposed[key] = score
                            if (
                                len(proposed)
                                > self._config.max_proposed_pairs
                            ):
                                raise ValueError(
                                    "Faiss HNSW proposal count exceeds "
                                    "max_proposed_pairs"
                                )

        if state_matrix_sha256(source_rows) != receipt.states_sha256:
            raise ValueError("states changed during Faiss range search")
        if (
            _worker_state_bytes_sha256(self._states_path)
            != self._worker_states_sha256
        ):
            raise ValueError(
                "Faiss worker state cache changed during range search"
            )
        if hashlib.sha256(self.export_index_bytes()).hexdigest() != (
            receipt.index_sha256
        ):
            raise ValueError("Faiss index digest changed during search")
        for (left_index, right_index), score in sorted(
            proposed.items()
        ):
            yield NeighborPair(
                left_index=left_index,
                right_index=right_index,
                backend_score=score,
            )
