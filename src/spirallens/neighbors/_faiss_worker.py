"""Private subprocess worker for the optional Faiss backend."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform

import numpy as np


def _load_faiss():
    try:
        import faiss
    except ImportError as error:
        raise ImportError(
            "Faiss HNSW requires `pip install 'spirallens[ann]'`"
        ) from error
    return faiss


def _atomic_json(path: Path, payload: dict[str, object]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ),
        encoding="utf-8",
    )
    temporary.replace(path)


def _run_build(args: argparse.Namespace) -> int:
    faiss = _load_faiss()
    rows = np.array(
        np.load(args.states, mmap_mode="r", allow_pickle=False),
        dtype=np.float32,
        order="C",
        copy=True,
    )
    if rows.ndim != 2 or not np.all(np.isfinite(rows)):
        raise ValueError("worker states must be a finite row matrix")
    worker_states_sha256 = hashlib.sha256(
        memoryview(rows).cast("B")
    ).hexdigest()
    faiss.normalize_L2(rows)
    normalized_sha256 = hashlib.sha256(
        memoryview(rows).cast("B")
    ).hexdigest()
    faiss.omp_set_num_threads(1)
    index = faiss.IndexHNSWFlat(
        int(rows.shape[1]),
        args.m,
        faiss.METRIC_INNER_PRODUCT,
    )
    index.hnsw.efConstruction = args.ef_construction
    index.hnsw.efSearch = args.ef_search
    index.hnsw.rng = faiss.RandomGenerator(args.seed)
    index.add(rows)
    faiss.write_index(index, str(args.index))
    index_sha256 = hashlib.sha256(args.index.read_bytes()).hexdigest()
    _atomic_json(
        args.metadata,
        {
            "faiss_version": str(faiss.__version__),
            "faiss_compile_options": str(faiss.get_compile_options()),
            "numpy_version": np.__version__,
            "python_version": platform.python_version(),
            "system": platform.system(),
            "machine": platform.machine(),
            "normalized_states_sha256": normalized_sha256,
            "worker_states_sha256": worker_states_sha256,
            "index_sha256": index_sha256,
            "row_count": int(rows.shape[0]),
            "hidden_size": int(rows.shape[1]),
            "thread_count": 1,
        },
    )
    return 0


def _run_search(args: argparse.Namespace) -> int:
    faiss = _load_faiss()
    rows = np.load(args.states, mmap_mode="r", allow_pickle=False)
    query_indices = np.load(
        args.query_indices,
        allow_pickle=False,
    )
    if (
        rows.ndim != 2
        or query_indices.ndim != 1
        or query_indices.dtype != np.int64
    ):
        raise ValueError("worker search inputs are malformed")
    faiss.omp_set_num_threads(1)
    index = faiss.read_index(str(args.index))
    index.hnsw.efSearch = args.ef_search
    output_files: list[str] = []
    raw_hit_count = 0
    for start in range(0, query_indices.size, args.query_batch_size):
        batch_indices = query_indices[
            start : start + args.query_batch_size
        ]
        queries = np.array(
            rows[batch_indices],
            dtype=np.float32,
            order="C",
            copy=True,
        )
        faiss.normalize_L2(queries)
        limits, scores, labels = index.range_search(
            queries,
            args.radius,
        )
        raw_hit_count += int(labels.size)
        if raw_hit_count > args.max_raw_hits:
            raise ValueError(
                "Faiss HNSW raw hit count exceeds max_raw_hits"
            )
        filename = f"hits-{start:09d}.npz"
        np.savez(
            args.output_dir / filename,
            batch_indices=batch_indices,
            limits=limits,
            scores=scores,
            labels=labels,
        )
        output_files.append(filename)
    _atomic_json(
        args.manifest,
        {
            "files": output_files,
            "raw_hit_count": raw_hit_count,
            "query_count": int(query_indices.size),
        },
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build")
    build.add_argument("--states", type=Path, required=True)
    build.add_argument("--index", type=Path, required=True)
    build.add_argument("--metadata", type=Path, required=True)
    build.add_argument("--m", type=int, required=True)
    build.add_argument("--ef-construction", type=int, required=True)
    build.add_argument("--ef-search", type=int, required=True)
    build.add_argument("--seed", type=int, required=True)
    build.set_defaults(handler=_run_build)

    search = commands.add_parser("search")
    search.add_argument("--states", type=Path, required=True)
    search.add_argument("--index", type=Path, required=True)
    search.add_argument("--query-indices", type=Path, required=True)
    search.add_argument("--output-dir", type=Path, required=True)
    search.add_argument("--manifest", type=Path, required=True)
    search.add_argument("--ef-search", type=int, required=True)
    search.add_argument("--query-batch-size", type=int, required=True)
    search.add_argument("--max-raw-hits", type=int, required=True)
    search.add_argument("--radius", type=float, required=True)
    search.set_defaults(handler=_run_search)
    return parser


def main() -> int:
    args = _parser().parse_args()
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
