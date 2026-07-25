"""Private subprocess worker for the optional Faiss backend."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import tempfile

import numpy as np


def _load_faiss():
    try:
        import faiss
    except ImportError as error:
        raise ImportError(
            "Faiss HNSW requires `pip install 'spirallens[ann]'`"
        ) from error
    return faiss


def _validated_runtime_contract() -> dict[str, str]:
    from spirallens.neighbors._faiss_runtime_worker import (
        _local_worker_runtime_contract,
    )

    raw = os.environ.get(
        "SPIRALLENS_FAISS_WORKER_RUNTIME_CONTRACT"
    )
    if not isinstance(raw, str) or not raw:
        raise ValueError("Faiss worker runtime contract is missing")
    try:
        expected = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(
            "Faiss worker runtime contract is invalid JSON"
        ) from error
    if (
        not isinstance(expected, dict)
        or not expected
        or any(
            not isinstance(key, str)
            or not key
            or not isinstance(value, str)
            or not value
            for key, value in expected.items()
        )
    ):
        raise ValueError("Faiss worker runtime contract is invalid")
    actual = _local_worker_runtime_contract(
        expected.get("execution_freeze_sha256")
    )
    if actual != expected:
        raise ValueError(
            "Faiss worker imports differ from the runtime contract"
        )
    return actual


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


def _array_sha256(values: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(values)
    return hashlib.sha256(memoryview(contiguous).cast("B")).hexdigest()


def _range_search_in_calls(
    index,
    queries: np.ndarray,
    *,
    radius: float,
    range_call_batch_size: int,
    max_native_call_hits: int | None,
    max_total_hits: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Run bounded native calls and return one validated aggregate result."""

    if (
        queries.ndim != 2
        or queries.dtype != np.float32
        or not queries.flags.c_contiguous
        or not np.all(np.isfinite(queries))
    ):
        raise ValueError("Faiss range queries must be finite contiguous float32")
    if range_call_batch_size <= 0 or max_total_hits <= 0:
        raise ValueError("Faiss range-search limits must be positive")
    if max_native_call_hits is not None and max_native_call_hits <= 0:
        raise ValueError("max_native_call_hits must be positive")
    ntotal = int(index.ntotal)
    if ntotal <= 0:
        raise ValueError("Faiss range-search index must contain rows")

    aggregate_limits = np.zeros(queries.shape[0] + 1, dtype=np.int64)
    score_parts: list[np.ndarray] = []
    label_parts: list[np.ndarray] = []
    raw_hit_count = 0
    for start in range(0, queries.shape[0], range_call_batch_size):
        stop = min(start + range_call_batch_size, queries.shape[0])
        call_queries = np.ascontiguousarray(queries[start:stop])
        theoretical_max_hits = int(call_queries.shape[0]) * ntotal
        if (
            max_native_call_hits is not None
            and theoretical_max_hits > max_native_call_hits
        ):
            raise ValueError(
                "Faiss native range call exceeds its prebound hit ceiling"
            )
        limits, scores, labels = index.range_search(
            call_queries,
            radius,
        )
        limits = np.asarray(limits)
        scores = np.asarray(scores)
        labels = np.asarray(labels)
        if (
            limits.ndim != 1
            or limits.shape[0] != call_queries.shape[0] + 1
            or limits.dtype.kind not in {"i", "u"}
            or scores.ndim != 1
            or labels.ndim != 1
            or labels.dtype.kind not in {"i", "u"}
            or int(limits[0]) != 0
            or np.any(limits[1:] < limits[:-1])
            or int(limits[-1]) != int(scores.size)
            or scores.size != labels.size
            or not np.all(np.isfinite(scores))
            or np.any(labels < 0)
            or np.any(labels >= ntotal)
        ):
            raise ValueError("Faiss native range result is malformed")
        call_hit_count = int(labels.size)
        if (
            max_native_call_hits is not None
            and call_hit_count > max_native_call_hits
        ):
            raise ValueError(
                "Faiss native range call exceeded its prebound hit ceiling"
            )
        raw_hit_count += call_hit_count
        if raw_hit_count > max_total_hits:
            raise ValueError(
                "Faiss HNSW raw hit count exceeds max_raw_hits"
            )
        aggregate_limits[start + 1 : stop + 1] = (
            raw_hit_count - call_hit_count + limits[1:]
        )
        score_parts.append(np.ascontiguousarray(scores))
        label_parts.append(np.ascontiguousarray(labels, dtype=np.int64))

    scores = (
        np.concatenate(score_parts)
        if score_parts
        else np.empty(0, dtype=np.float32)
    )
    labels = (
        np.concatenate(label_parts)
        if label_parts
        else np.empty(0, dtype=np.int64)
    )
    if (
        aggregate_limits.shape[0] != queries.shape[0] + 1
        or aggregate_limits[0] != 0
        or np.any(aggregate_limits[1:] < aggregate_limits[:-1])
        or aggregate_limits[-1] != scores.size
        or scores.size != labels.size
    ):
        raise RuntimeError("aggregated Faiss range result is malformed")
    return aggregate_limits, scores, labels


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
            "runtime": args.runtime_contract,
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
        limits, scores, labels = _range_search_in_calls(
            index,
            queries,
            radius=args.radius,
            range_call_batch_size=args.range_call_batch_size,
            max_native_call_hits=args.max_native_call_hits,
            max_total_hits=args.max_raw_hits - raw_hit_count,
        )
        raw_hit_count += int(labels.size)
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
            "query_batch_size": args.query_batch_size,
            "range_call_batch_size": args.range_call_batch_size,
            "max_native_call_hits": args.max_native_call_hits,
        },
    )
    return 0


def _run_preflight(args: argparse.Namespace) -> int:
    if (
        args.row_count <= 0
        or args.hidden_size <= 0
        or args.query_count <= 0
        or args.query_count > args.row_count
        or args.cluster_size <= 0
        or args.row_count % args.cluster_size != 0
    ):
        raise ValueError("Faiss preflight fixture shape is invalid")
    cluster_count = args.row_count // args.cluster_size
    generator = np.random.Generator(np.random.PCG64(args.fixture_seed))
    centers = generator.standard_normal(
        (cluster_count, args.hidden_size),
        dtype=np.float32,
    )
    rows = np.repeat(centers, args.cluster_size, axis=0)
    states_sha256 = _array_sha256(rows)
    query_indices = np.arange(args.query_count, dtype=np.int64)
    query_indices_sha256 = _array_sha256(query_indices)

    with tempfile.TemporaryDirectory(
        prefix="spirallens-faiss-preflight-worker-"
    ) as directory:
        root = Path(directory)
        states_path = root / "states.npy"
        index_path = root / "index.faiss"
        metadata_path = root / "metadata.json"
        query_indices_path = root / "query-indices.npy"
        search_manifest_path = root / "search-manifest.json"
        np.save(states_path, rows, allow_pickle=False)
        np.save(query_indices_path, query_indices, allow_pickle=False)
        _run_build(
            argparse.Namespace(
                states=states_path,
                index=index_path,
                metadata=metadata_path,
                m=args.m,
                ef_construction=args.ef_construction,
                ef_search=args.ef_search,
                seed=args.seed,
                runtime_contract=args.runtime_contract,
            )
        )
        _run_search(
            argparse.Namespace(
                states=states_path,
                index=index_path,
                query_indices=query_indices_path,
                output_dir=root,
                manifest=search_manifest_path,
                ef_search=args.ef_search,
                query_batch_size=args.query_batch_size,
                range_call_batch_size=args.range_call_batch_size,
                max_raw_hits=args.max_raw_hits,
                max_native_call_hits=args.max_native_call_hits,
                radius=args.radius,
            )
        )
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        search_manifest = json.loads(
            search_manifest_path.read_text(encoding="utf-8")
        )
        if (
            not isinstance(metadata, dict)
            or metadata.get("worker_states_sha256") != states_sha256
            or not isinstance(
                metadata.get("normalized_states_sha256"),
                str,
            )
            or search_manifest
            != {
                "files": ["hits-000000000.npz"],
                "raw_hit_count": search_manifest.get("raw_hit_count"),
                "query_count": args.query_count,
                "query_batch_size": args.query_batch_size,
                "range_call_batch_size": args.range_call_batch_size,
                "max_native_call_hits": args.max_native_call_hits,
            }
        ):
            raise ValueError(
                "Faiss preflight production-path metadata is malformed"
            )
        with np.load(
            root / "hits-000000000.npz",
            allow_pickle=False,
        ) as payload:
            batch_indices = payload["batch_indices"]
            limits = payload["limits"]
            scores = payload["scores"]
            labels = payload["labels"]
        raw_hit_count = search_manifest["raw_hit_count"]
        if (
            not isinstance(raw_hit_count, int)
            or raw_hit_count != int(labels.size)
            or not np.array_equal(batch_indices, query_indices)
            or limits.ndim != 1
            or limits.size != args.query_count + 1
            or int(limits[0]) != 0
            or np.any(limits[1:] < limits[:-1])
            or int(limits[-1]) != int(labels.size)
            or scores.ndim != 1
            or labels.ndim != 1
            or scores.size != labels.size
            or not np.all(np.isfinite(scores))
            or np.any(labels < 0)
            or np.any(labels >= args.row_count)
        ):
            raise ValueError(
                "Faiss preflight serialized range result is malformed"
            )
        normalized_states_sha256 = metadata[
            "normalized_states_sha256"
        ]
        index_sha256 = metadata["index_sha256"]
    _atomic_json(
        args.output,
        {
            "fixture": {
                "schema_version": args.fixture_schema_version,
                "generator": "numpy.pcg64.standard_normal.float32.cluster-repeat",
                "seed": args.fixture_seed,
                "row_count": args.row_count,
                "hidden_size": args.hidden_size,
                "cluster_size": args.cluster_size,
                "query_count": args.query_count,
                "states_sha256": states_sha256,
                "normalized_states_sha256": normalized_states_sha256,
                "query_indices_sha256": query_indices_sha256,
            },
            "search": {
                "m": args.m,
                "ef_construction": args.ef_construction,
                "ef_search": args.ef_search,
                "seed": args.seed,
                "thread_count": 1,
                "query_batch_size": args.query_batch_size,
                "range_call_batch_size": args.range_call_batch_size,
                "cosine_min": args.cosine_min,
                "score_margin": args.score_margin,
                "radius": args.radius,
                "max_native_call_hits": args.max_native_call_hits,
                "max_raw_hits": args.max_raw_hits,
            },
            "runtime": args.runtime_contract,
            "result": {
                "index_sha256": index_sha256,
                "limits_sha256": _array_sha256(limits),
                "scores_sha256": _array_sha256(scores),
                "labels_sha256": _array_sha256(labels),
                "raw_hit_count": int(labels.size),
                "limits_length": int(limits.size),
            },
        },
    )
    return 0


def _run_fixture(args: argparse.Namespace) -> int:
    if (
        args.row_count <= 0
        or args.hidden_size <= 0
        or args.query_count <= 0
        or args.query_count > args.row_count
        or args.cluster_size <= 0
        or args.row_count % args.cluster_size != 0
    ):
        raise ValueError("Faiss fixture shape is invalid")
    cluster_count = args.row_count // args.cluster_size
    generator = np.random.Generator(np.random.PCG64(args.fixture_seed))
    centers = generator.standard_normal(
        (cluster_count, args.hidden_size),
        dtype=np.float32,
    )
    rows = np.repeat(centers, args.cluster_size, axis=0)
    states_sha256 = _array_sha256(rows)
    query_indices = np.arange(args.query_count, dtype=np.int64)
    query_indices_sha256 = _array_sha256(query_indices)
    faiss = _load_faiss()
    faiss.omp_set_num_threads(1)
    faiss.normalize_L2(rows)
    _atomic_json(
        args.output,
        {
            "fixture": {
                "schema_version": args.fixture_schema_version,
                "generator": (
                    "numpy.pcg64.standard_normal.float32.cluster-repeat"
                ),
                "seed": args.fixture_seed,
                "row_count": args.row_count,
                "hidden_size": args.hidden_size,
                "cluster_size": args.cluster_size,
                "query_count": args.query_count,
                "states_sha256": states_sha256,
                "normalized_states_sha256": _array_sha256(rows),
                "query_indices_sha256": query_indices_sha256,
            },
            "runtime": args.runtime_contract,
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
    search.add_argument("--range-call-batch-size", type=int, required=True)
    search.add_argument("--max-raw-hits", type=int, required=True)
    search.add_argument("--max-native-call-hits", type=int)
    search.add_argument("--radius", type=float, required=True)
    search.set_defaults(handler=_run_search)

    preflight = commands.add_parser("preflight")
    preflight.add_argument("--output", type=Path, required=True)
    preflight.add_argument("--fixture-schema-version", required=True)
    preflight.add_argument("--row-count", type=int, required=True)
    preflight.add_argument("--hidden-size", type=int, required=True)
    preflight.add_argument("--cluster-size", type=int, required=True)
    preflight.add_argument("--query-count", type=int, required=True)
    preflight.add_argument("--fixture-seed", type=int, required=True)
    preflight.add_argument("--m", type=int, required=True)
    preflight.add_argument("--ef-construction", type=int, required=True)
    preflight.add_argument("--ef-search", type=int, required=True)
    preflight.add_argument("--seed", type=int, required=True)
    preflight.add_argument("--query-batch-size", type=int, required=True)
    preflight.add_argument("--range-call-batch-size", type=int, required=True)
    preflight.add_argument("--cosine-min", type=float, required=True)
    preflight.add_argument("--score-margin", type=float, required=True)
    preflight.add_argument("--radius", type=float, required=True)
    preflight.add_argument("--max-native-call-hits", type=int, required=True)
    preflight.add_argument("--max-raw-hits", type=int, required=True)
    preflight.set_defaults(handler=_run_preflight)

    fixture = commands.add_parser("fixture")
    fixture.add_argument("--output", type=Path, required=True)
    fixture.add_argument("--fixture-schema-version", required=True)
    fixture.add_argument("--row-count", type=int, required=True)
    fixture.add_argument("--hidden-size", type=int, required=True)
    fixture.add_argument("--cluster-size", type=int, required=True)
    fixture.add_argument("--query-count", type=int, required=True)
    fixture.add_argument("--fixture-seed", type=int, required=True)
    fixture.set_defaults(handler=_run_fixture)
    return parser


def main() -> int:
    args = _parser().parse_args()
    args.runtime_contract = _validated_runtime_contract()
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
