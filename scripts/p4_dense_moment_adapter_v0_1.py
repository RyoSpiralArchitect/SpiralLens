"""Optional float64 CUDA reductions; host graph/support/loop authority is unchanged.

Inputs are canonical host arrays, not backend-specific random draws. Every call
returns host float64 arrays. Timings include validation, transfers and CUDA
synchronization; no asynchronous launch-only speed is reported.
"""

from __future__ import annotations

import copy
import time

import numpy as np


class DenseMomentAdapter:
    def __init__(self, backend="numpy", batch_vertices=8192):
        if backend not in ("numpy", "cuda"):
            raise ValueError("backend must be numpy or cuda")
        if type(batch_vertices) is not int or not 1 <= batch_vertices <= 65536:
            raise ValueError("batch_vertices must be an integer in [1,65536]")
        self.backend = backend
        self.batch_vertices = batch_vertices
        self.torch = None
        self._receipt = {
            "backend": backend,
            "dtype": "float64",
            "gpu_used": False,
            "device": "cpu",
            "batch_vertices": batch_vertices,
            "operations": {
                name: {"calls": 0, "batches": 0, "seconds": 0.0}
                for name in ("covariance", "moments")
            },
            "timing_includes": [
                "validation",
                "host_to_device",
                "compute",
                "device_to_host",
                "synchronization",
            ],
            "peak_gpu_allocated_bytes": 0,
            "gpu_peak_scope": "process-torch-allocator-high-water-not-total-device-use",
            "silent_fallback": False,
        }
        if backend == "cuda":
            try:
                import torch
            except ImportError as exc:
                raise RuntimeError(
                    "CUDA backend requires an available PyTorch runtime"
                ) from exc
            if not torch.cuda.is_available():
                raise RuntimeError("CUDA requested but unavailable; no silent fallback")
            self.torch = torch
            torch.cuda.synchronize()
            self._receipt.update(
                cuda_available=True,
                device=torch.cuda.get_device_name(torch.cuda.current_device()),
                torch_version=torch.__version__,
                cuda_runtime=torch.version.cuda,
            )

    @staticmethod
    def _validate(probes, frames=None):
        if (
            not isinstance(probes, np.ndarray)
            or probes.dtype != np.float64
            or probes.ndim != 3
            or probes.shape[0] < 1
            or probes.shape[1] < 1
            or probes.shape[2] != 3
            or not np.isfinite(probes).all()
        ):
            raise ValueError("finite float64 probes with shape (N>=1,P>=1,3) required")
        if frames is not None and (
            not isinstance(frames, np.ndarray)
            or frames.dtype != np.float64
            or frames.shape != (len(probes), 3, 2)
            or not np.isfinite(frames).all()
        ):
            raise ValueError("finite float64 frames with shape (N,3,2) required")

    def _begin(self):
        if self.torch is not None:
            self.torch.cuda.synchronize()
        return time.perf_counter()

    def _finish(self, operation, started, batches):
        if self.torch is not None:
            self.torch.cuda.synchronize()
            self._receipt["gpu_used"] = True
            self._receipt["peak_gpu_allocated_bytes"] = int(
                self.torch.cuda.max_memory_allocated()
            )
        record = self._receipt["operations"][operation]
        record["calls"] += 1
        record["batches"] += batches
        record["seconds"] += time.perf_counter() - started

    def covariance(self, probes):
        started = self._begin()
        self._validate(probes)
        result = np.empty((len(probes), 3, 3), dtype=np.float64)
        batches = 0
        for start in range(0, len(probes), self.batch_vertices):
            stop = start + self.batch_vertices
            host = probes[start:stop]
            if self.torch is None:
                centered = host - host.mean(axis=1, keepdims=True)
                out = np.einsum("npi,npj->nij", centered, centered) / host.shape[1]
            else:
                tensor = self.torch.from_numpy(np.ascontiguousarray(host)).to("cuda")
                centered = tensor - tensor.mean(dim=1, keepdim=True)
                out = (centered.transpose(1, 2) @ centered) / host.shape[1]
                out = out.cpu().numpy()
            if not np.isfinite(out).all():
                raise ValueError("nonfinite covariance result")
            result[start:stop] = out
            batches += 1
        self._finish("covariance", started, batches)
        return result

    def moments(self, frames, probes):
        started = self._begin()
        self._validate(probes, frames)
        f2 = np.empty((len(probes), 2), dtype=np.float64)
        f4 = np.empty_like(f2)
        batches = 0
        for start in range(0, len(probes), self.batch_vertices):
            stop = start + self.batch_vertices
            host, frame = probes[start:stop], frames[start:stop]
            if self.torch is None:
                mean = host.mean(axis=1)
                local = np.einsum("npd,ndi->npi", host - mean[:, None, :], frame)
                covariance = np.einsum("npi,npj->nij", local, local) / host.shape[1]
                vector = np.einsum("ndi,nd->ni", frame, mean)
                tensor = np.column_stack(
                    (
                        (covariance[:, 0, 0] - covariance[:, 1, 1]) / 2,
                        (covariance[:, 0, 1] + covariance[:, 1, 0]) / 2,
                    )
                )
            else:
                device_probes = self.torch.from_numpy(np.ascontiguousarray(host)).to(
                    "cuda"
                )
                device_frames = self.torch.from_numpy(np.ascontiguousarray(frame)).to(
                    "cuda"
                )
                mean = device_probes.mean(dim=1)
                local = (device_probes - mean[:, None, :]) @ device_frames
                covariance = (local.transpose(1, 2) @ local) / host.shape[1]
                vector = (mean[:, None, :] @ device_frames)[:, 0, :].cpu().numpy()
                tensor = (
                    self.torch.stack(
                        (
                            (covariance[:, 0, 0] - covariance[:, 1, 1]) / 2,
                            (covariance[:, 0, 1] + covariance[:, 1, 0]) / 2,
                        ),
                        dim=1,
                    )
                    .cpu()
                    .numpy()
                )
            if not np.isfinite(vector).all() or not np.isfinite(tensor).all():
                raise ValueError("nonfinite moment result")
            f2[start:stop], f4[start:stop] = vector, tensor
            batches += 1
        self._finish("moments", started, batches)
        return {"F2": f2, "F4": f4}

    def receipt(self):
        return copy.deepcopy(self._receipt)
