#!/usr/bin/env python3
"""Paired synthetic probe sensitivity with optional float64 CUDA reductions.

This successor does not edit or mutate the frozen large-domain prototype.
An isolated function namespace replaces only probe generation and dense moment
reductions; graph construction, eigenvectors, seals, and loop gates remain CPU.
Its maximum-width noise stream is a new protocol, not a prior-run replay.
"""

from __future__ import annotations

import argparse
import hashlib
import platform
import resource
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from types import FunctionType

import numpy as np

import prototype_p4_large_domain_v0_1 as predecessor
from p4_dense_moment_adapter_v0_1 import DenseMomentAdapter


SCHEMA = "spirallens.p4-probe-sensitivity-synthetic.v0.1"
NOISE_PROTOCOL = "role-seedsequence-vertex-major-max128-first-P.v0.1"
PROBE_COUNTS = (8, 32, 128)
NOISE_ROLES = ("all", "plane", "baseline", "evaluation", "none")
NOISE_CHUNK_VERTICES = 4096


@dataclass(frozen=True)
class ProbeSpec:
    side: int = 17
    k: int = 8
    pattern: str = "curved_coherent"
    probe_noise: float = 0.0
    warp: float = 0.0
    seed: int = 0
    probe_count: int = 8
    noise_role: str = "all"

    def __post_init__(self):
        predecessor.ScaleSpec(
            side=self.side,
            k=self.k,
            pattern=self.pattern,
            probe_noise=self.probe_noise,
            warp=self.warp,
            seed=self.seed,
        )
        if self.side not in (17, 65, 257):
            raise ValueError("prospective sensitivity sides are 17,65,257")
        if type(self.probe_count) is not int or self.probe_count not in PROBE_COUNTS:
            raise ValueError("prospective probe counts are 8,32,128")
        if self.noise_role not in NOISE_ROLES:
            raise ValueError("noise role must be all,plane,baseline,evaluation,none")
        if self.noise_role == "none" and self.probe_noise != 0:
            raise ValueError("noise_role none requires zero probe_noise")


def make_probes(spec: ProbeSpec, coords):
    """Canonical CPU inputs, paired by role and vertex across probe counts.

    Each role has its own seeded stream with conceptual shape (N,128,3).
    Every vertex consumes 128 draws even for smaller P, so coordinates in the
    same fixed domain receive exactly the first P noisy probes of the P128 run.
    Chunking only bounds temporary memory and does not alter stream ordering.
    Domains with different side lengths are deliberately not coordinate-paired.
    """
    coords = np.asarray(coords, dtype=np.float64)
    if (
        coords.ndim != 2
        or coords.shape[1] != 2
        or not 0 < len(coords) <= 257**2
        or not np.isfinite(coords).all()
    ):
        raise ValueError(
            "finite nonempty Nx2 coordinates within 66049 vertices required"
        )
    clean = predecessor.make_probes(replace(spec, probe_noise=0.0), coords)
    streams = np.random.SeedSequence(spec.seed).spawn(3)
    probes = {}
    for role, stream in zip(("plane", "baseline", "evaluation"), streams, strict=True):
        values = np.tile(clean[role], (1, spec.probe_count // 8, 1))
        if spec.probe_noise and spec.noise_role in ("all", role):
            rng = np.random.default_rng(stream)
            for start in range(0, len(coords), NOISE_CHUNK_VERTICES):
                stop = min(start + NOISE_CHUNK_VERTICES, len(coords))
                noise = rng.normal(size=(stop - start, max(PROBE_COUNTS), 3))
                values[start:stop] += spec.probe_noise * noise[:, : spec.probe_count]
        probes[role] = values
    return probes


def _isolated_measurement(adapter):
    """Bind reductions without any assignment into predecessor.__dict__.

    Both cloned functions share this per-call namespace. Their bytecode and all
    unreplaced gate functions are the predecessor's. The namespace is returned
    for instrumentation of chronology in tests, not as a public extension API.
    """
    namespace = dict(vars(predecessor))
    namespace.update(
        make_probes=make_probes,
        _covariance=adapter.covariance,
        moments=adapter.moments,
    )
    for name in ("prepare_row", "measure_case"):
        original = getattr(predecessor, name)
        function = FunctionType(
            original.__code__,
            namespace,
            original.__name__,
            original.__defaults__,
            original.__closure__,
        )
        function.__kwdefaults__ = original.__kwdefaults__
        namespace[name] = function
    return namespace["measure_case"], namespace


def _file_hash(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def measure_case(spec: ProbeSpec, backend="numpy", output: Path | None = None):
    if not isinstance(spec, ProbeSpec):
        raise TypeError(
            "ProbeSpec required for the separately registered noise protocol"
        )
    started = time.monotonic()
    if output is not None:
        output = Path(output)
        output.mkdir(parents=True, exist_ok=False)
    adapter = DenseMomentAdapter(backend=backend, batch_vertices=8192)
    measurement, _ = _isolated_measurement(adapter)
    report, data = measurement(spec, output=None)
    report["schema_version"] = SCHEMA
    report["spec"] = asdict(spec)
    report["numeric_adapter"] = adapter.receipt()
    report["design"].update(
        noise_protocol=NOISE_PROTOCOL,
        paired_across_probe_count=True,
        paired_across_noise_roles=True,
        same_seed_is_not_coordinate_paired_noise=True,
        noise_pairing_scope="same-fixed-domain-and-seed-across-probe-count-and-role",
        noise_paired_across_domain_refinement=False,
        deterministic_cube_repeats=spec.probe_count // 8,
        maximum_width_noise_stream=128,
        probe_noise_is_new_protocol_not_predecessor_replay=True,
        deterministic_repeats_are_not_independent_replicates=True,
    )
    report["dependency_injection"] = {
        "strategy": "isolated-per-call-function-namespace",
        "cloned_functions": ["prepare_row", "measure_case"],
        "replaced_bindings": ["make_probes", "_covariance", "moments"],
        "predecessor_globals_mutated": False,
        "predecessor_source_sha256": _file_hash(predecessor.__file__),
        "successor_source_sha256": _file_hash(__file__),
    }
    report["scope"].update(
        gpu_used=report["numeric_adapter"]["gpu_used"],
        cuda_scope="dense-covariance-and-moment-reductions-only",
        graph_backend="cpu-scipy-sparse",
        eigensolver_backend="cpu-numpy-float64",
        core_and_loop_gates_backend="unchanged-cpu",
        cpu_cuda_input_generation="same-canonical-cpu-float64-bytes",
    )
    report["timing"]["total_with_adapter_seconds"] = time.monotonic() - started
    if output is not None:
        arrays_path = output / "arrays.npz"
        with arrays_path.open("xb") as stream:
            np.savez_compressed(stream, **data)
        report["array_artifact"] = {
            "file": "arrays.npz",
            "bytes": arrays_path.stat().st_size,
            "sha256": _file_hash(arrays_path),
        }
        report["timing"]["total_with_serialization_seconds"] = (
            time.monotonic() - started
        )
    report["peak_rss_bytes"] = int(
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    ) * (1 if platform.system() == "Darwin" else 1024)
    if output is not None:
        predecessor._write(output / "report.json", report)
    return report, data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--backend", choices=("numpy", "cuda"), default="numpy")
    parser.add_argument("--side", type=int, choices=(17, 65, 257), default=17)
    parser.add_argument("--k", type=int, choices=(8, 16, 32), default=8)
    parser.add_argument("--probe-count", type=int, choices=PROBE_COUNTS, default=8)
    parser.add_argument("--noise-role", choices=NOISE_ROLES, default="all")
    parser.add_argument("--pattern", default="curved_coherent")
    parser.add_argument("--noise", type=float, default=0.0)
    parser.add_argument("--warp", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    spec = ProbeSpec(
        side=args.side,
        k=args.k,
        pattern=args.pattern,
        probe_noise=args.noise,
        warp=args.warp,
        seed=args.seed,
        probe_count=args.probe_count,
        noise_role=args.noise_role,
    )
    report, _ = measure_case(spec, backend=args.backend, output=args.output)
    print(
        predecessor.json.dumps(
            {
                "spec": report["spec"],
                "summary": report["summary"],
                "numeric_adapter": report["numeric_adapter"],
                "timing": report["timing"],
                "peak_rss_bytes": report["peak_rss_bytes"],
            },
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
