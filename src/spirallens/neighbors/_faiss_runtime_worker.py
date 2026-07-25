"""Private fresh-process reporter for the exact Faiss worker runtime."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import sys

import numpy as np


def _local_worker_runtime_contract(
    execution_freeze_sha256: str | None,
) -> dict[str, str]:
    """Inspect Faiss only inside a dedicated worker process."""

    import faiss
    import faiss._swigfaiss as faiss_native

    from spirallens.execution_freeze import (
        _require_sha256,
        _sha256_file,
        distribution_content_sha256,
        process_image_path,
    )

    package_root = Path(__file__).resolve().parents[1]
    numpy_import = Path(np.__file__).resolve()
    faiss_import = Path(faiss.__file__).resolve()
    faiss_native_import = Path(faiss_native.__file__).resolve()
    process_image = process_image_path()
    contract = {
        "faiss_compile_options": str(faiss.get_compile_options()),
        "faiss_distribution_sha256": distribution_content_sha256(
            "faiss-cpu"
        ),
        "faiss_hnsw_source_sha256": _sha256_file(
            package_root / "neighbors" / "faiss_hnsw.py"
        ),
        "faiss_import_file": str(faiss_import),
        "faiss_import_sha256": _sha256_file(faiss_import),
        "faiss_native_file": str(faiss_native_import),
        "faiss_native_sha256": _sha256_file(faiss_native_import),
        "faiss_runtime_worker_source_sha256": _sha256_file(
            Path(__file__).resolve()
        ),
        "faiss_version": str(faiss.__version__),
        "faiss_worker_source_sha256": _sha256_file(
            package_root / "neighbors" / "_faiss_worker.py"
        ),
        "machine": platform.machine(),
        "numpy_distribution_sha256": distribution_content_sha256(
            "numpy"
        ),
        "numpy_import_file": str(numpy_import),
        "numpy_import_sha256": _sha256_file(numpy_import),
        "numpy_version": np.__version__,
        "process_image": str(process_image),
        "process_image_sha256": _sha256_file(process_image),
        "python_version": platform.python_version(),
        "system": platform.system(),
    }
    if execution_freeze_sha256 is not None:
        contract["execution_freeze_sha256"] = _require_sha256(
            execution_freeze_sha256,
            label="execution_freeze_sha256",
        )
    return contract


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-freeze-sha256")
    return parser


def main() -> int:
    args = _parser().parse_args()
    payload = json.dumps(
        _local_worker_runtime_contract(args.execution_freeze_sha256),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    sys.stdout.buffer.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
