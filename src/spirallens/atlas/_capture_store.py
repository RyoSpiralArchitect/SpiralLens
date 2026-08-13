"""Private mutable capture store for activation-atlas construction."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
from typing import Any, Mapping
import uuid

import numpy as np
from numpy.lib.format import open_memmap
import torch

from spirallens.adapters import LOGIT_SUMMARY_COLUMNS, BatchObservation

from .store import (
    ATLAS_SCHEMA_VERSION,
    AtlasIntegrityError,
    AtlasStateError,
    _array_slice_sha256,
    _canonical_sha256,
    _close_memmaps,
    _request_resume_identity,
    _sha256_file,
    _strict_json_load,
    _validated_array,
    _verify_batch_commit_data,
    _verify_manifest_structure,
    load_manifest,
    token_ids_sha256,
)


__all__: tuple[str, ...] = ()

NORM_SUMMARY_COLUMNS: tuple[str, ...] = ("resid_pre_l2", "resid_post_l2")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_json_write(path: Path, payload: Mapping[str, Any]) -> None:
    encoded = json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    )
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _array_specs(
    *,
    num_tokens: int,
    num_layers: int,
    hidden_size: int,
) -> dict[str, dict[str, Any]]:
    return {
        "token_ids": {
            "path": "token_ids.npy",
            "shape": [num_tokens],
            "dtype": "int64",
            "sha256": None,
        },
        "resid_pre": {
            "path": "resid_pre.npy",
            "shape": [num_tokens, num_layers, hidden_size],
            "dtype": "float32",
            "sha256": None,
        },
        "resid_post": {
            "path": "resid_post.npy",
            "shape": [num_tokens, num_layers, hidden_size],
            "dtype": "float32",
            "sha256": None,
        },
        "norm_summary": {
            "path": "norm_summary.npy",
            "shape": [num_tokens, num_layers, len(NORM_SUMMARY_COLUMNS)],
            "dtype": "float32",
            "columns": list(NORM_SUMMARY_COLUMNS),
            "sha256": None,
        },
        "logit_summary": {
            "path": "logit_summary.npy",
            "shape": [num_tokens, len(LOGIT_SUMMARY_COLUMNS)],
            "dtype": "float32",
            "columns": list(LOGIT_SUMMARY_COLUMNS),
            "sha256": None,
        },
        "prediction_ids": {
            "path": "prediction_ids.npy",
            "shape": [num_tokens],
            "dtype": "int64",
            "sha256": None,
        },
    }


def _build_batch_commit(
    arrays: Mapping[str, np.ndarray],
    *,
    batch_index: int,
    start_row: int,
    end_row: int,
) -> dict[str, Any]:
    return {
        "batch_index": batch_index,
        "start_row": start_row,
        "end_row": end_row,
        "committed_at": _utc_now(),
        "array_sha256": {
            name: _array_slice_sha256(
                name,
                arrays[name],
                start_row=start_row,
                end_row=end_row,
            )
            for name in sorted(arrays)
        },
    }


class AtlasStore:
    """Internal mutable store with manifest-last batch commits."""

    def __init__(
        self,
        *,
        root: Path,
        manifest: dict[str, Any],
        arrays: dict[str, np.memmap],
    ) -> None:
        self.root = root
        self.manifest = manifest
        self.arrays = arrays

    @classmethod
    def initialize(
        cls,
        *,
        output_dir: Path,
        token_ids: np.ndarray,
        model_metadata: Mapping[str, Any],
        request: Mapping[str, Any],
        fingerprint_payload: Mapping[str, Any],
        capture_metadata: Mapping[str, Any],
        resume: bool,
        batch_size: int,
    ) -> "AtlasStore":
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = output_dir / "manifest.json"
        entries = list(output_dir.iterdir())
        expected_specs = _array_specs(
            num_tokens=len(token_ids),
            num_layers=int(model_metadata["num_layers"]),
            hidden_size=int(model_metadata["hidden_size"]),
        )
        fingerprint = _canonical_sha256(fingerprint_payload)
        capture_fingerprint = _canonical_sha256(capture_metadata)

        if manifest_path.exists():
            if not resume:
                raise AtlasStateError(
                    f"{manifest_path} already exists; pass resume=True explicitly"
                )
            manifest = _strict_json_load(manifest_path)
            _verify_manifest_structure(manifest)
            if manifest.get("run_fingerprint") != fingerprint:
                raise AtlasStateError(
                    "resume request does not match the persisted run fingerprint"
                )
            persisted_request = manifest.get("request")
            if not isinstance(persisted_request, Mapping) or _request_resume_identity(
                persisted_request
            ) != _request_resume_identity(request):
                raise AtlasStateError(
                    "resume request fields do not match the persisted request"
                )
            if (
                manifest.get("capture") != capture_metadata
                or manifest.get("capture_fingerprint") != capture_fingerprint
            ):
                raise AtlasStateError(
                    "resume capture implementation/runtime does not match "
                    "the persisted run"
                )
            cls._verify_specs_match(manifest["arrays"], expected_specs)
            arrays: dict[str, np.memmap] = {}
            try:
                arrays = {
                    name: _validated_array(output_dir, name, spec, writable=True)
                    for name, spec in manifest["arrays"].items()
                }
                persisted_ids = arrays["token_ids"]
                if not np.array_equal(persisted_ids, token_ids):
                    raise AtlasIntegrityError(
                        "persisted token_ids do not equal requested token_ids"
                    )
                if token_ids_sha256(persisted_ids) != request["token_ids_sha256"]:
                    raise AtlasIntegrityError("persisted token_ids digest is invalid")
                if manifest["status"] != "complete":
                    # This happens before appending a new attempt or changing
                    # status, so a damaged committed row is never blessed.
                    _verify_batch_commit_data(manifest, arrays)
            except Exception:
                cls._close_arrays(arrays)
                raise
            if manifest["status"] == "complete":
                cls._close_arrays(arrays)
                load_manifest(output_dir, verify_checksums=True)
                # Reopen read/write only to keep a uniform return type.  The
                # caller immediately returns and closes these handles.
                arrays = {
                    name: _validated_array(output_dir, name, spec, writable=True)
                    for name, spec in manifest["arrays"].items()
                }
                return cls(root=output_dir, manifest=manifest, arrays=arrays)
            resumed_manifest = deepcopy(manifest)
            resumed_manifest["status"] = "in_progress"
            resumed_manifest["failure"] = None
            resumed_manifest["updated_at"] = _utc_now()
            resumed_manifest["request"]["batch_size_latest"] = batch_size
            attempts = resumed_manifest["attempts"]
            attempts.append(
                {
                    "started_at": resumed_manifest["updated_at"],
                    "resume_from_row": resumed_manifest["progress"]["completed_rows"],
                    "batch_size": batch_size,
                    "capture": deepcopy(dict(capture_metadata)),
                    "capture_fingerprint": capture_fingerprint,
                }
            )
            _atomic_json_write(manifest_path, resumed_manifest)
            return cls(root=output_dir, manifest=resumed_manifest, arrays=arrays)

        if entries:
            names = ", ".join(sorted(entry.name for entry in entries[:5]))
            raise AtlasStateError(
                "refusing to initialize a non-empty directory without a manifest: "
                f"{output_dir} ({names})"
            )
        if resume:
            raise AtlasStateError(
                f"resume=True but no manifest exists in empty directory {output_dir}"
            )

        arrays: dict[str, np.memmap] = {}
        try:
            estimated_array_bytes = sum(
                int(np.prod(spec["shape"], dtype=np.int64))
                * np.dtype(spec["dtype"]).itemsize
                for spec in expected_specs.values()
            )
            free_bytes = shutil.disk_usage(output_dir).free
            reserve_bytes = 64 * 1024 * 1024
            if free_bytes < estimated_array_bytes + reserve_bytes:
                raise AtlasStateError(
                    "insufficient free space for atlas arrays: "
                    f"need at least {estimated_array_bytes + reserve_bytes} bytes, "
                    f"have {free_bytes}"
                )
            for name, spec in expected_specs.items():
                arrays[name] = open_memmap(
                    output_dir / spec["path"],
                    mode="w+",
                    dtype=np.dtype(spec["dtype"]),
                    shape=tuple(spec["shape"]),
                )
            arrays["token_ids"][:] = token_ids
            arrays["token_ids"].flush()
            now = _utc_now()
            manifest = {
                "schema_version": ATLAS_SCHEMA_VERSION,
                "status": "in_progress",
                "run_id": str(uuid.uuid4()),
                "run_fingerprint": fingerprint,
                "capture": deepcopy(dict(capture_metadata)),
                "capture_fingerprint": capture_fingerprint,
                "created_at": now,
                "updated_at": now,
                "request": deepcopy(dict(request)),
                "model": deepcopy(dict(model_metadata)),
                "arrays": deepcopy(expected_specs),
                "progress": {
                    "completed_rows": 0,
                    "total_rows": len(token_ids),
                    "committed_batches": 0,
                },
                "attempts": [
                    {
                        "started_at": now,
                        "resume_from_row": 0,
                        "batch_size": batch_size,
                        "capture": deepcopy(dict(capture_metadata)),
                        "capture_fingerprint": capture_fingerprint,
                    }
                ],
                "batch_commits": [],
                "environment": {
                    "python": platform.python_version(),
                    "numpy": np.__version__,
                    "torch": torch.__version__,
                },
                "storage": {
                    "estimated_array_bytes": estimated_array_bytes,
                    "free_bytes_at_start": free_bytes,
                    "reserved_free_bytes": reserve_bytes,
                },
                "summaries": None,
                "failure": None,
            }
            _atomic_json_write(manifest_path, manifest)
            return cls(root=output_dir, manifest=manifest, arrays=arrays)
        except Exception:
            cls._close_arrays(arrays)
            raise

    @staticmethod
    def _verify_specs_match(
        persisted: Mapping[str, Any], expected: Mapping[str, Any]
    ) -> None:
        if set(persisted) != set(expected):
            raise AtlasIntegrityError("persisted array set does not match request")
        structural_keys = ("path", "shape", "dtype", "columns")
        for name in expected:
            for key in structural_keys:
                if persisted[name].get(key) != expected[name].get(key):
                    raise AtlasIntegrityError(
                        f"persisted {name}.{key} does not match request"
                    )

    @staticmethod
    def _close_arrays(arrays: Mapping[str, np.memmap]) -> None:
        _close_memmaps(arrays)

    @property
    def completed_rows(self) -> int:
        return int(self.manifest["progress"]["completed_rows"])

    @property
    def is_complete(self) -> bool:
        return self.manifest["status"] == "complete"

    def write_batch(self, start: int, observation: BatchObservation) -> None:
        batch_size = int(observation.resid_pre.shape[0])
        end = start + batch_size
        if start != self.completed_rows:
            raise AtlasStateError(
                f"non-contiguous commit: start={start}, completed={self.completed_rows}"
            )
        if end > self.manifest["progress"]["total_rows"]:
            raise AtlasStateError("batch would exceed declared atlas row count")

        values = {
            "resid_pre": observation.resid_pre.numpy(),
            "resid_post": observation.resid_post.numpy(),
            "norm_summary": observation.norm_summary.numpy(),
            "logit_summary": observation.logit_summary.numpy(),
            "prediction_ids": observation.prediction_ids.numpy(),
        }
        for name, value in values.items():
            expected = tuple(self.arrays[name].shape[1:])
            if value.shape != (batch_size, *expected):
                raise AtlasIntegrityError(
                    f"{name} batch shape {value.shape} != {(batch_size, *expected)}"
                )
            if np.issubdtype(value.dtype, np.floating) and not np.isfinite(value).all():
                raise AtlasIntegrityError(
                    f"{name} batch contains a non-finite observation"
                )

        # The progress marker is written only after every data array has been
        # flushed.  If interrupted before then, the same rows are overwritten.
        for name, value in values.items():
            self.arrays[name][start:end] = value
        for name in values:
            self.arrays[name].flush()

        commit = _build_batch_commit(
            self.arrays,
            batch_index=len(self.manifest["batch_commits"]),
            start_row=start,
            end_row=end,
        )
        committed_manifest = deepcopy(self.manifest)
        committed_manifest["batch_commits"].append(commit)
        committed_manifest["progress"]["completed_rows"] = end
        committed_manifest["progress"]["committed_batches"] += 1
        committed_manifest["updated_at"] = commit["committed_at"]
        # Only replace the in-memory state after the manifest rename succeeds.
        # A crash before this point leaves the prior progress marker, and the
        # uncommitted physical rows are deterministically overwritten.
        _atomic_json_write(self.root / "manifest.json", committed_manifest)
        self.manifest = committed_manifest

    def finalize(self) -> dict[str, Any]:
        total = self.manifest["progress"]["total_rows"]
        if self.completed_rows != total:
            raise AtlasStateError(
                f"cannot finalize partial atlas: {self.completed_rows}/{total}"
            )
        for array in self.arrays.values():
            array.flush()
        _verify_batch_commit_data(self.manifest, self.arrays)

        self.manifest["summaries"] = {
            "norm_summary": self._summarize_columns(
                self.arrays["norm_summary"], NORM_SUMMARY_COLUMNS
            ),
            "logit_summary": self._summarize_columns(
                self.arrays["logit_summary"], LOGIT_SUMMARY_COLUMNS
            ),
            "unique_prediction_ids": int(np.unique(self.arrays["prediction_ids"]).size),
        }
        for name, spec in self.manifest["arrays"].items():
            spec["sha256"] = _sha256_file(self.root / spec["path"])
            spec["file_size_bytes"] = (self.root / spec["path"]).stat().st_size
        self.manifest["status"] = "complete"
        self.manifest["failure"] = None
        self.manifest["updated_at"] = _utc_now()
        self.manifest["completed_at"] = self.manifest["updated_at"]
        _atomic_json_write(self.root / "manifest.json", self.manifest)
        return deepcopy(self.manifest)

    @staticmethod
    def _summarize_columns(
        array: np.ndarray,
        columns: tuple[str, ...],
        *,
        chunk_rows: int = 1024,
    ) -> dict[str, Any]:
        minima = np.full(len(columns), np.inf, dtype=np.float64)
        maxima = np.full(len(columns), -np.inf, dtype=np.float64)
        totals = np.zeros(len(columns), dtype=np.float64)
        count = 0
        for start in range(0, array.shape[0], chunk_rows):
            chunk = np.asarray(array[start : start + chunk_rows], dtype=np.float64)
            flat = chunk.reshape(-1, len(columns))
            if not np.isfinite(flat).all():
                raise AtlasIntegrityError(
                    "persisted summary array contains non-finite data"
                )
            minima = np.minimum(minima, flat.min(axis=0))
            maxima = np.maximum(maxima, flat.max(axis=0))
            totals += flat.sum(axis=0)
            count += flat.shape[0]
        if count == 0:
            raise AtlasIntegrityError("cannot summarize an empty atlas")
        return {
            column: {
                "min": float(minima[index]),
                "max": float(maxima[index]),
                "mean": float(totals[index] / count),
                "count": count,
            }
            for index, column in enumerate(columns)
        }

    def mark_failed(self, exc: BaseException) -> None:
        if self.manifest.get("status") == "complete":
            return
        self.manifest["status"] = "failed"
        self.manifest["updated_at"] = _utc_now()
        self.manifest["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc)[:2000],
            "at_row": self.completed_rows,
        }
        _atomic_json_write(self.root / "manifest.json", self.manifest)

    def close(self) -> None:
        self._close_arrays(self.arrays)
