"""Fixed synthetic probe/noise panel plus same-host CUDA parity and timing.

All reference sensitivity observations use NumPy prospectively. CUDA is an
explicit optional adapter, evaluated here rather than silently auto-selected.
Each stage is a bounded child; failed and unrun stages remain in the manifest.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time

import numpy as np

import prototype_p4_probe_sensitivity_v0_1 as kernel
from p4_dense_moment_adapter_v0_1 import DenseMomentAdapter

ROOT = Path(__file__).resolve().parents[1]
CASE_SECONDS = 180
TOTAL_SECONDS = 1200
DISK_BYTES = 8 * 2**30


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, data):
    with path.open("x") as stream:
        json.dump(data, stream, sort_keys=True, allow_nan=False)
        stream.write("\n")


def source_lock():
    files = sorted((ROOT / "src").rglob("*.py"))
    files += sorted((ROOT / "scripts").glob("*p4*.py"))
    return {str(p.relative_to(ROOT)): sha(p) for p in files}


def case_specs():
    specs = [
        kernel.ProbeSpec(
            side=side, probe_count=count, noise_role=role, probe_noise=0.03
        )
        for side in (65, 257)
        for count in (8, 32, 128)
        for role in ("all", "plane", "baseline", "evaluation")
    ]
    specs += [
        kernel.ProbeSpec(
            side=65,
            pattern=pattern,
            probe_count=count,
            noise_role="none",
            probe_noise=0.0,
        )
        for pattern in ("quadratic_excess", "curved_coherent")
        for count in (8, 128)
    ]
    return specs


def compare(cpu, gpu, left, right):
    """Exact gates/discrete data, 1e-9 numerical parity; no below-floor direction.

    Non-admitted supplemental diagnostics and provenance hashes are not observables.
    Admission state, reason, coverage, core membership and every eligible value are.
    """
    failures = []
    if left.keys() != right.keys():
        failures.append("array-keys")
    exact_keys = {"coords", "faces", "graph_states", "plane", "baseline", "evaluation"}
    maximum = 0.0
    for key in left.keys() & right.keys():
        a, b = left[key], right[key]
        if a.shape != b.shape or a.dtype != b.dtype:
            failures.append("array-shape-dtype:" + key)
            continue
        exact = key in exact_keys or a.dtype.kind in "biu"
        equal = (
            np.array_equal(a, b) if exact else np.allclose(a, b, atol=1e-9, rtol=1e-9)
        )
        if not equal:
            failures.append("array:" + key)
        if a.shape == b.shape and a.size and a.dtype.kind == "f":
            maximum = max(maximum, float(np.max(np.abs(a - b))))
    for family in cpu["rows"]:
        a, b = cpu["rows"][family]["baseline"], gpu["rows"][family]["baseline"]
        for field in ("state", "stencil_rows", "baseline_probe_sha256"):
            if a[field] != b[field]:
                failures.append(f"baseline:{family}:{field}")
        for h, value in a["coefficients"].items():
            other = b["coefficients"][h]
            if value is None or other is None:
                equal = value is other
            else:
                equal = np.shape(value) == np.shape(other) and np.allclose(
                    value, other, atol=1e-9, rtol=1e-9
                )
            if not equal:
                failures.append(f"baseline:{family}:coefficient:{h}")
        for estimand, hypotheses in cpu["rows"][family]["fields"].items():
            for h, record in hypotheses.items():
                a, b = (
                    record["core"],
                    gpu["rows"][family]["fields"][estimand][h]["core"],
                )
                for field in (
                    "state",
                    "classification",
                    "candidate_count",
                    "low_vertex_count",
                    "component_sizes",
                ):
                    if a.get(field) != b.get(field):
                        failures.append(f"core:{family}:{estimand}:{h}:{field}")
    if len(cpu["cells"]) != len(gpu["cells"]):
        failures.append("cell-count")
    for i, (a, b) in enumerate(zip(cpu["cells"], gpu["cells"])):
        for field in ("field_graph", "loop_graph"):
            if a[field] != b[field]:
                failures.append(f"cell:{i}:identity:{field}")
        if a["loops"].keys() != b["loops"].keys():
            failures.append(f"cell:{i}:loop-keys")
            continue
        for loop in a["loops"]:
            pairs = [
                ("geometry", a["loops"][loop]["geometry"], b["loops"][loop]["geometry"])
            ]
            pairs += [
                (f"{e}:{h}", av, b["loops"][loop]["fields"][e][h])
                for e, hs in a["loops"][loop]["fields"].items()
                for h, av in hs.items()
            ]
            for label, av, bv in pairs:
                prefix = f"cell:{i}:{loop}:{label}"
                for field in ("state", "reason", "coverage"):
                    if av[field] != bv[field]:
                        failures.append(prefix + ":" + field)
                if av["state"] == bv["state"] == "eligible":
                    if av["value"].keys() != bv["value"].keys():
                        failures.append(prefix + ":value-keys")
                    else:
                        for key, value in av["value"].items():
                            if not np.allclose(
                                value, bv["value"][key], atol=1e-9, rtol=1e-9
                            ):
                                failures.append(prefix + ":value:" + key)
    return {
        "passed": not failures,
        "failures": failures,
        "maximum_array_absolute_difference": maximum,
        "absolute_tolerance": 1e-9,
        "relative_tolerance": 1e-9,
        "ineligible_supplemental_direction_compared": False,
        "state_reason_coverage_compared_exactly": True,
    }


def parity_stage(index, output):
    spec = (
        kernel.ProbeSpec(
            side=65,
            pattern="quadratic_excess",
            probe_count=128,
            noise_role="none",
            probe_noise=0.0,
        )
        if index == 0
        else kernel.ProbeSpec(
            side=257, probe_count=128, noise_role="all", probe_noise=0.03
        )
    )
    records, arrays, seconds = {}, {}, {}
    for backend in ("numpy", "cuda"):
        started = time.perf_counter()
        records[backend], arrays[backend] = kernel.measure_case(spec, backend=backend)
        seconds[backend] = time.perf_counter() - started
        write(output / f"{backend}-report.json", records[backend])
    result = compare(records["numpy"], records["cuda"], arrays["numpy"], arrays["cuda"])
    result.update(
        spec=asdict(spec),
        elapsed_seconds=seconds,
        timing_scope="one-cold-call-per-backend-in-child-includes-init-generation-graphs-hashes-no-serialization",
        order=["numpy", "cuda"],
        report_sha256={b: sha(output / f"{b}-report.json") for b in records},
    )
    return result


def benchmark_stage(output):
    result = {
        "points": [],
        "repetitions": 3,
        "warmup_calls_per_backend_per_point": 1,
        "scope": "one-covariance-plus-one-moments-call; host validation/transfers/sync included; no graph/core/hashes/IO",
        "fixed_order_by_repeat": [
            ["numpy", "cuda"],
            ["cuda", "numpy"],
            ["numpy", "cuda"],
        ],
    }
    for count in (8, 32, 128):
        spec = kernel.ProbeSpec(
            side=257, probe_count=count, noise_role="all", probe_noise=0.03
        )
        domain = kernel.predecessor.backend.make_domain(spec.side)
        probes = kernel.make_probes(spec, domain["coords"])
        # Frames fixed on CPU and reused byte-identically by both backends.
        reference = DenseMomentAdapter("numpy")
        frames, _ = kernel.predecessor.fit_covariances(
            reference.covariance(probes["plane"])
        )
        adapters = {b: DenseMomentAdapter(b) for b in ("numpy", "cuda")}
        measurements = {b: [] for b in adapters}
        outputs = {}
        reference_outputs = None
        mismatches = []
        for repeat, order in enumerate(
            [list(adapters), *result["fixed_order_by_repeat"]]
        ):
            for b in order:
                started = time.perf_counter()
                covariance = adapters[b].covariance(probes["plane"])
                moments = adapters[b].moments(frames, probes["evaluation"])
                measurements[b].append(time.perf_counter() - started)
                outputs[b] = {"covariance": covariance, **moments}
                if reference_outputs is None:
                    reference_outputs = outputs[b]
                for key, value in outputs[b].items():
                    if not np.allclose(
                        value, reference_outputs[key], atol=1e-9, rtol=1e-9
                    ):
                        mismatches.append(
                            {
                                "repeat_including_warmup": repeat,
                                "backend": b,
                                "array": key,
                            }
                        )
        passed = not mismatches and all(
            np.allclose(outputs["numpy"][k], outputs["cuda"][k], atol=1e-9, rtol=1e-9)
            for k in outputs["numpy"]
        )
        medians = {b: float(np.median(v[1:])) for b, v in measurements.items()}
        point = {
            "probe_count": count,
            "vertex_count": len(frames),
            "parity_passed": passed,
            "parity_mismatches": mismatches,
            "every_repetition_checked": True,
            "seconds_including_warmup": measurements,
            "warm_median_seconds": medians,
            "cpu_over_cuda_ratio": medians["numpy"] / medians["cuda"],
            "input_sha256": {r: kernel.predecessor._hash(v) for r, v in probes.items()},
            "frames_sha256": kernel.predecessor._hash(frames),
            "adapters": {b: a.receipt() for b, a in adapters.items()},
        }
        result["points"].append(point)
        write(output / f"p{count}.json", point)
    result["passed"] = all(p["parity_passed"] for p in result["points"])
    return result


def child(mode, index, output):
    output.mkdir(parents=True, exist_ok=False)
    if mode == "parity":
        result = parity_stage(index, output)
    elif mode == "benchmark":
        result = benchmark_stage(output)
    else:
        # measure_case owns its output directory.
        report, _ = kernel.measure_case(
            case_specs()[index], backend="numpy", output=output / "measurement"
        )
        result = {
            "spec": report["spec"],
            "summary": report["summary"],
            "report_sha256": sha(output / "measurement/report.json"),
            "array_artifact": report["array_artifact"],
            "timing": report["timing"],
            "peak_rss_bytes": report["peak_rss_bytes"],
            "backend": "numpy",
        }
    write(output / "result.json", result)


def limits():
    # CUDA reserves a large virtual address range: RLIMIT_AS would reject valid
    # context initialization. Bound child lifetime/files and adapter batch instead.
    resource.setrlimit(resource.RLIMIT_CPU, (CASE_SECONDS, CASE_SECONDS + 1))
    resource.setrlimit(resource.RLIMIT_FSIZE, (2 * 2**30, 2 * 2**30))
    os.nice(10)


def run(output):
    if platform.system() != "Linux":
        raise ValueError("campaign resource limits require Linux")
    output.mkdir(parents=True, exist_ok=False)
    lock = source_lock()
    stages = [("parity", 0), ("parity", 1), ("benchmark", 0)] + [
        ("science", i) for i in range(len(case_specs()))
    ]
    plan = {
        "schema": "spirallens.p4-probe-sensitivity-campaign.v0.1",
        "source_sha256": lock,
        "cases": [asdict(s) for s in case_specs()],
        "stages": stages,
        "reference_backend": "numpy",
        "cuda_auto_selected": False,
        "case_seconds": CASE_SECONDS,
        "total_seconds": TOTAL_SECONDS,
        "pre_stage_disk_budget_bytes": DISK_BYTES,
        "max_file_bytes": 2 * 2**30,
        "adapter_batch_vertices": 8192,
        "concurrent_children": 1,
        "cuda_virtual_address_space_capped": False,
        "thresholds": kernel.predecessor.old.chain.development_thresholds(),
        "numeric_parity_atol": 1e-9,
        "numeric_parity_rtol": 1e-9,
        "exact_parity": [
            "inputs",
            "graphs",
            "support",
            "core membership",
            "state",
            "reason",
            "coverage",
        ],
        "excluded_parity": [
            "provenance hashes",
            "ineligible supplemental directional values",
        ],
        "scientific_authority": False,
        "model_accessed": False,
    }
    write(output / "plan.json", plan)
    started = time.monotonic()
    records = []
    env = dict(
        os.environ,
        PYTHONPATH=str(ROOT / "src"),
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
    )
    for number, (mode, index) in enumerate(stages):
        elapsed = time.monotonic() - started
        used = sum(p.stat().st_size for p in output.rglob("*") if p.is_file())
        reason = (
            "time-budget"
            if elapsed >= TOTAL_SECONDS
            else "disk-budget"
            if used >= DISK_BYTES
            else "source-changed"
            if source_lock() != lock
            else None
        )
        if reason:
            records.extend(
                {"mode": m, "index": i, "status": "not_run", "reason": reason}
                for m, i in stages[number:]
            )
            break
        destination = output / f"{number:02d}-{mode}-{index:02d}"
        record = {
            "mode": mode,
            "index": index,
            "status": "running",
            "directory": destination.name,
        }
        write(output / f"{number:02d}.attempt.json", record)
        began = time.monotonic()
        with (
            (output / f"{number:02d}.stdout").open("x") as stdout,
            (output / f"{number:02d}.stderr").open("x") as stderr,
        ):
            try:
                proc = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(Path(__file__).resolve()),
                        "--child",
                        mode,
                        "--index",
                        str(index),
                        "--output",
                        str(destination),
                    ],
                    cwd=ROOT,
                    env=env,
                    stdout=stdout,
                    stderr=stderr,
                    preexec_fn=limits,
                    timeout=min(CASE_SECONDS, TOTAL_SECONDS - elapsed),
                    check=False,
                )
                record.update(
                    status="completed" if proc.returncode == 0 else "failed",
                    returncode=proc.returncode,
                )
            except subprocess.TimeoutExpired:
                record.update(status="timeout", reason="bounded-stage-deadline")
        record["seconds"] = time.monotonic() - began
        if record["status"] == "completed":
            record["result_sha256"] = sha(destination / "result.json")
            record["result"] = json.loads((destination / "result.json").read_text())
        write(output / f"{number:02d}.terminal.json", record)
        records.append(record)
        print(
            json.dumps({k: v for k, v in record.items() if k != "result"}), flush=True
        )
    manifest = {
        "plan_sha256": sha(output / "plan.json"),
        "host": platform.node(),
        "python": platform.python_version(),
        "stages": records,
        "planned": len(stages),
        "completed": sum(r["status"] == "completed" for r in records),
        "elapsed_seconds": time.monotonic() - started,
        "model_accessed": False,
        "scientific_authority": False,
    }
    write(output / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--child", choices=("parity", "benchmark", "science"))
    parser.add_argument("--index", type=int, default=0)
    args = parser.parse_args()
    if args.child:
        child(args.child, args.index, args.output)
    else:
        result = run(args.output)
        print(json.dumps({k: v for k, v in result.items() if k != "stages"}))
        return int(result["completed"] != result["planned"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
