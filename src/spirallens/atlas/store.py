"""Fail-closed, resumable ``.npy`` storage for activation atlases."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
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


ATLAS_SCHEMA_VERSION = "spirallens.activation_atlas.v2"
NORM_SUMMARY_COLUMNS: tuple[str, ...] = ("resid_pre_l2", "resid_post_l2")


class AtlasStateError(RuntimeError):
    """Raised when an output directory cannot be safely initialized/resumed."""


class AtlasIntegrityError(RuntimeError):
    """Raised when persisted atlas data violates its manifest."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strict_json_load(path: Path) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise AtlasIntegrityError(
            f"{path.name} contains non-standard JSON constant {value}"
        )

    try:
        data = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)
    except (OSError, json.JSONDecodeError) as exc:
        raise AtlasIntegrityError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise AtlasIntegrityError(f"{path} must contain a JSON object")
    return data


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


def _canonical_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def token_ids_sha256(token_ids: np.ndarray) -> str:
    canonical = np.asarray(token_ids, dtype="<i8", order="C")
    return hashlib.sha256(canonical.tobytes(order="C")).hexdigest()


def _sha256_file(path: Path, *, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


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


def _validated_array(
    root: Path,
    name: str,
    spec: Mapping[str, Any],
    *,
    writable: bool,
) -> np.memmap:
    relative_path = spec.get("path")
    if (
        not isinstance(relative_path, str)
        or Path(relative_path).name != relative_path
    ):
        raise AtlasIntegrityError(f"unsafe array path for {name}: {relative_path!r}")
    path = root / relative_path
    if not path.is_file():
        raise AtlasIntegrityError(f"missing array file: {path}")
    try:
        array = np.load(path, mmap_mode="r+" if writable else "r", allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise AtlasIntegrityError(f"cannot open {path}: {exc}") from exc
    expected_shape = tuple(spec.get("shape", ()))
    expected_dtype = np.dtype(spec.get("dtype"))
    if array.shape != expected_shape:
        raise AtlasIntegrityError(
            f"{name} shape mismatch: {array.shape} != {expected_shape}"
        )
    if array.dtype != expected_dtype:
        raise AtlasIntegrityError(
            f"{name} dtype mismatch: {array.dtype} != {expected_dtype}"
        )
    if not isinstance(array, np.memmap):
        raise AtlasIntegrityError(f"{path} did not open as a memory map")
    return array


def _close_memmaps(arrays: Mapping[str, np.memmap]) -> None:
    for array in arrays.values():
        try:
            if array.flags.writeable:
                array.flush()
        except (OSError, ValueError):
            pass
        underlying = getattr(array, "_mmap", None)
        if underlying is not None:
            try:
                underlying.close()
            except (OSError, ValueError):
                pass


def _array_slice_sha256(
    name: str,
    array: np.ndarray,
    *,
    start_row: int,
    end_row: int,
) -> str:
    """Hash a persisted row slice with unambiguous structural framing."""

    view = np.ascontiguousarray(array[start_row:end_row])
    header = {
        "schema_version": ATLAS_SCHEMA_VERSION,
        "array": name,
        "start_row": start_row,
        "end_row": end_row,
        "shape": list(view.shape),
        "dtype": str(view.dtype),
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
    digest.update(memoryview(view).cast("B"))
    return digest.hexdigest()


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


def _verify_batch_commit_data(
    manifest: Mapping[str, Any],
    arrays: Mapping[str, np.ndarray],
) -> None:
    for commit in manifest["batch_commits"]:
        start_row = int(commit["start_row"])
        end_row = int(commit["end_row"])
        for name, expected in commit["array_sha256"].items():
            actual = _array_slice_sha256(
                name,
                arrays[name],
                start_row=start_row,
                end_row=end_row,
            )
            if actual != expected:
                raise AtlasIntegrityError(
                    "batch commit digest mismatch: "
                    f"batch={commit['batch_index']}, array={name}, "
                    f"rows=[{start_row}, {end_row})"
                )


def _verify_manifest_structure(manifest: Mapping[str, Any]) -> None:
    if manifest.get("schema_version") != ATLAS_SCHEMA_VERSION:
        raise AtlasIntegrityError(
            "unsupported atlas schema: "
            f"{manifest.get('schema_version')!r} != {ATLAS_SCHEMA_VERSION!r}"
        )
    if manifest.get("status") not in {"in_progress", "failed", "complete"}:
        raise AtlasIntegrityError(f"invalid atlas status: {manifest.get('status')!r}")
    arrays = manifest.get("arrays")
    if not isinstance(arrays, Mapping):
        raise AtlasIntegrityError("manifest.arrays must be an object")
    if set(arrays) != set(
        _array_specs(num_tokens=1, num_layers=1, hidden_size=1)
    ):
        raise AtlasIntegrityError("manifest contains missing or unknown arrays")
    progress = manifest.get("progress")
    if not isinstance(progress, Mapping):
        raise AtlasIntegrityError("manifest.progress must be an object")
    completed = progress.get("completed_rows")
    total = progress.get("total_rows")
    if (
        not isinstance(completed, int)
        or not isinstance(total, int)
        or total <= 0
        or not 0 <= completed <= total
    ):
        raise AtlasIntegrityError(
            f"invalid manifest progress: completed={completed}, total={total}"
        )
    if manifest.get("status") == "complete" and completed != total:
        raise AtlasIntegrityError("complete atlas does not have all rows committed")

    capture = manifest.get("capture")
    if not isinstance(capture, Mapping):
        raise AtlasIntegrityError("manifest.capture must be an object")
    implementation = capture.get("capture_implementation")
    if not isinstance(implementation, Mapping):
        raise AtlasIntegrityError(
            "manifest.capture.capture_implementation must be an object"
        )
    if (
        not isinstance(implementation.get("name"), str)
        or not isinstance(implementation.get("version"), str)
        or implementation.get("accelerator_to_cpu_copy") != "synchronous"
        or implementation.get("activation_dtype") != "float32"
    ):
        raise AtlasIntegrityError("invalid capture implementation contract")
    required_capture_fields = (
        "atlas_schema_version",
        "spirallens_version",
        "torch_version",
        "transformers_version",
        "effective_parameter_layout",
    )
    if any(field not in capture for field in required_capture_fields):
        raise AtlasIntegrityError("manifest.capture is missing required provenance")
    layout = capture["effective_parameter_layout"]
    if not isinstance(layout, list) or not layout:
        raise AtlasIntegrityError(
            "capture effective_parameter_layout must be non-empty"
        )
    for entry in layout:
        if (
            not isinstance(entry, Mapping)
            or not isinstance(entry.get("device"), str)
            or not isinstance(entry.get("dtype"), str)
            or not isinstance(entry.get("parameter_tensors"), int)
            or not isinstance(entry.get("parameter_values"), int)
        ):
            raise AtlasIntegrityError(
                "invalid effective parameter device/dtype entry"
            )
    if capture["atlas_schema_version"] != ATLAS_SCHEMA_VERSION:
        raise AtlasIntegrityError("capture contract schema does not match manifest")
    capture_fingerprint = manifest.get("capture_fingerprint")
    if (
        not isinstance(capture_fingerprint, str)
        or capture_fingerprint != _canonical_sha256(capture)
    ):
        raise AtlasIntegrityError("manifest capture fingerprint is invalid")
    request = manifest.get("request")
    if (
        not isinstance(request, Mapping)
        or request.get("capture_fingerprint") != capture_fingerprint
    ):
        raise AtlasIntegrityError(
            "request capture fingerprint does not match manifest"
        )

    attempts = manifest.get("attempts")
    if not isinstance(attempts, list) or not attempts:
        raise AtlasIntegrityError("manifest.attempts must be a non-empty list")
    for index, attempt in enumerate(attempts):
        if not isinstance(attempt, Mapping):
            raise AtlasIntegrityError(f"attempt {index} must be an object")
        if (
            attempt.get("capture") != capture
            or attempt.get("capture_fingerprint") != capture_fingerprint
        ):
            raise AtlasIntegrityError(
                f"attempt {index} capture provenance does not match run"
            )

    committed_batches = progress.get("committed_batches")
    batch_commits = manifest.get("batch_commits")
    if (
        not isinstance(committed_batches, int)
        or committed_batches < 0
        or not isinstance(batch_commits, list)
        or committed_batches != len(batch_commits)
    ):
        raise AtlasIntegrityError(
            "progress.committed_batches must match batch_commits length"
        )
    expected_start = 0
    array_names = set(arrays)
    for index, commit in enumerate(batch_commits):
        if not isinstance(commit, Mapping):
            raise AtlasIntegrityError(f"batch commit {index} must be an object")
        start_row = commit.get("start_row")
        end_row = commit.get("end_row")
        digests = commit.get("array_sha256")
        if (
            commit.get("batch_index") != index
            or start_row != expected_start
            or not isinstance(end_row, int)
            or not isinstance(start_row, int)
            or not start_row < end_row <= completed
            or not isinstance(digests, Mapping)
            or set(digests) != array_names
        ):
            raise AtlasIntegrityError(f"invalid batch commit structure at {index}")
        for name, digest in digests.items():
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                raise AtlasIntegrityError(
                    f"invalid batch commit digest at {index}:{name}"
                )
        expected_start = end_row
    if expected_start != completed:
        raise AtlasIntegrityError(
            "batch commit row coverage does not match completed_rows"
        )


def load_manifest(
    output_dir: str | Path,
    *,
    verify_checksums: bool = True,
) -> dict[str, Any]:
    """Load and validate a completed or partial atlas manifest.

    When checksums are present they are verified by default.  A complete
    manifest is required to have a checksum for every array.
    """

    root = Path(output_dir)
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise AtlasStateError(f"atlas manifest does not exist: {manifest_path}")
    manifest = _strict_json_load(manifest_path)
    _verify_manifest_structure(manifest)
    arrays: dict[str, np.memmap] = {}
    try:
        arrays = {
            name: _validated_array(root, name, spec, writable=False)
            for name, spec in manifest["arrays"].items()
        }
        expected_token_digest = manifest.get("request", {}).get(
            "token_ids_sha256"
        )
        if token_ids_sha256(arrays["token_ids"]) != expected_token_digest:
            raise AtlasIntegrityError(
                "token_ids data digest does not match request"
            )
        # Partial atlases do not yet have whole-file checksums, so their batch
        # journal is the authoritative integrity boundary.  For complete
        # atlases, whole-file checksums cover the same bytes more efficiently.
        if manifest["status"] != "complete" or not verify_checksums:
            _verify_batch_commit_data(manifest, arrays)
    finally:
        _close_memmaps(arrays)

    for name, spec in manifest["arrays"].items():
        checksum = spec.get("sha256")
        if manifest["status"] == "complete" and not checksum:
            raise AtlasIntegrityError(
                f"complete atlas is missing checksum for {name}"
            )
        if verify_checksums and checksum:
            actual = _sha256_file(root / spec["path"])
            if actual != checksum:
                raise AtlasIntegrityError(
                    f"{name} checksum mismatch: {actual} != {checksum}"
                )
    return manifest


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
                    name: _validated_array(
                        output_dir, name, spec, writable=True
                    )
                    for name, spec in manifest["arrays"].items()
                }
                persisted_ids = arrays["token_ids"]
                if not np.array_equal(persisted_ids, token_ids):
                    raise AtlasIntegrityError(
                        "persisted token_ids do not equal requested token_ids"
                    )
                if token_ids_sha256(persisted_ids) != request["token_ids_sha256"]:
                    raise AtlasIntegrityError(
                        "persisted token_ids digest is invalid"
                    )
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
                    "resume_from_row": resumed_manifest["progress"][
                        "completed_rows"
                    ],
                    "batch_size": batch_size,
                    "capture": deepcopy(dict(capture_metadata)),
                    "capture_fingerprint": capture_fingerprint,
                }
            )
            _atomic_json_write(manifest_path, resumed_manifest)
            return cls(
                root=output_dir, manifest=resumed_manifest, arrays=arrays
            )

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
            "unique_prediction_ids": int(
                np.unique(self.arrays["prediction_ids"]).size
            ),
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
                raise AtlasIntegrityError("persisted summary array contains non-finite data")
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
