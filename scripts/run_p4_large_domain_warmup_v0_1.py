#!/usr/bin/env python3
"""One bounded local-on-Furnace synthetic campaign; never invokes a remote host.

Each case runs in its own single-threaded CPU subprocess. The parent retains
timeouts/errors/not-run rows rather than selecting only favorable results.
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

import prototype_p4_large_domain_v0_1 as kernel


ROOT = Path(__file__).resolve().parents[1]
CASE_TIMEOUT = 300
TOTAL_TIMEOUT = 1800
AS_BYTES = 16 * 2**30
DISK_BYTES = 8 * 2**30


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_lock():
    files = sorted((ROOT / "src").rglob("*.py")) + [
        ROOT / "scripts" / name
        for name in (
            "p4_sparse_graph_backend_v0_1.py",
            "prototype_p4_large_domain_v0_1.py",
            "prototype_p4_graph_cross_v0_1.py",
            "prototype_p4_estimand_comparison_v0_1.py",
            "prototype_p4_partial_patterns_v0_1.py",
            Path(__file__).name,
        )
    ]
    return {str(path.relative_to(ROOT)): _sha(path) for path in files}


def _limits():
    resource.setrlimit(resource.RLIMIT_AS, (AS_BYTES, AS_BYTES))
    resource.setrlimit(resource.RLIMIT_FSIZE, (2 * 2**30, 2 * 2**30))
    resource.setrlimit(resource.RLIMIT_CPU, (CASE_TIMEOUT, CASE_TIMEOUT + 1))
    os.nice(10)


def run(output: Path):
    if platform.system() != "Linux":
        raise ValueError("bounded campaign executor requires Linux resource limits")
    output.mkdir(parents=True, exist_ok=False)
    specs = kernel.campaign_specs()
    lock = source_lock()
    plan = {
        "schema_version": kernel.SCHEMA,
        "cases": [asdict(s) for s in specs],
        "case_count": len(specs),
        "source_sha256": lock,
        "resource_limits": {
            "seconds_per_case": CASE_TIMEOUT,
            "seconds_total": TOTAL_TIMEOUT,
            "address_space_bytes_per_case": AS_BYTES,
            "max_file_bytes": 2 * 2**30,
            "campaign_disk_budget_bytes": DISK_BYTES,
            "concurrent_cases": 1,
            "blas_threads": 1,
        },
        "thresholds": kernel.old.chain.development_thresholds(),
        "geometry_frobenius_tolerance": kernel.old.GEOMETRY_AGREEMENT_FRO,
        "pre_observation_plan": True,
        "scientific_authority": False,
        "model_accessed": False,
        "gpu_used": False,
    }
    kernel._write(output / "plan.json", plan)
    plan_hash = _sha(output / "plan.json")
    started = time.monotonic()
    records = []
    env = dict(os.environ)
    env.update(
        PYTHONPATH=str(ROOT / "src"),
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
    )
    for index, spec in enumerate(specs):
        elapsed = time.monotonic() - started
        used = sum(path.stat().st_size for path in output.rglob("*") if path.is_file())
        if elapsed >= TOTAL_TIMEOUT or used >= DISK_BYTES:
            reason = "total-time-budget" if elapsed >= TOTAL_TIMEOUT else "disk-budget"
            records.extend(
                {"case": i, "spec": asdict(s), "status": "not_run", "reason": reason}
                for i, s in enumerate(specs[index:], index)
            )
            break
        if source_lock() != lock:
            records.extend(
                {
                    "case": i,
                    "spec": asdict(s),
                    "status": "not_run",
                    "reason": "source-bytes-changed",
                }
                for i, s in enumerate(specs[index:], index)
            )
            break
        case_dir = output / f"case-{index:02d}"
        stdout_path, stderr_path = (
            output / f"case-{index:02d}.stdout",
            output / f"case-{index:02d}.stderr",
        )
        record = {
            "case": index,
            "spec": asdict(spec),
            "status": "running",
            "plan_sha256": plan_hash,
        }
        kernel._write(output / f"case-{index:02d}.attempt.json", record)
        began = time.monotonic()
        with stdout_path.open("x") as stdout, stderr_path.open("x") as stderr:
            try:
                process = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(ROOT / "scripts/prototype_p4_large_domain_v0_1.py"),
                        "--case",
                        str(index),
                        "--output",
                        str(case_dir),
                    ],
                    cwd=ROOT,
                    env=env,
                    stdout=stdout,
                    stderr=stderr,
                    timeout=min(CASE_TIMEOUT, TOTAL_TIMEOUT - elapsed),
                    preexec_fn=_limits,
                    check=False,
                )
                record["status"] = "completed" if process.returncode == 0 else "failed"
                record["returncode"] = process.returncode
            except subprocess.TimeoutExpired:
                record.update(status="timeout", reason="bounded-case-deadline")
        record["elapsed_seconds"] = time.monotonic() - began
        if record["status"] == "completed":
            report_path = case_dir / "report.json"
            report = json.loads(report_path.read_text())
            if report["spec"] != asdict(spec):
                raise ValueError("case result does not match prospective plan")
            record.update(
                report_sha256=_sha(report_path),
                array_artifact=report["array_artifact"],
                peak_rss_bytes=report["peak_rss_bytes"],
                summary=report["summary"],
                timing=report["timing"],
            )
        kernel._write(output / f"case-{index:02d}.terminal.json", record)
        records.append(record)
        print(
            json.dumps(
                {
                    "case": index,
                    "of": len(specs),
                    "status": record["status"],
                    "spec": asdict(spec),
                    "seconds": record["elapsed_seconds"],
                    "peak_rss_bytes": record.get("peak_rss_bytes"),
                }
            ),
            flush=True,
        )
    manifest = {
        "schema_version": kernel.SCHEMA,
        "plan_sha256": plan_hash,
        "host": platform.node(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "elapsed_seconds": time.monotonic() - started,
        "case_count": len(specs),
        "cases": records,
        "completed": sum(r["status"] == "completed" for r in records),
        "disk_bytes": sum(p.stat().st_size for p in output.rglob("*") if p.is_file()),
        "scientific_authority": False,
        "model_accessed": False,
        "gpu_used": False,
    }
    kernel._write(output / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output)
    print(
        json.dumps(
            {
                "completed": result["completed"],
                "planned": result["case_count"],
                "seconds": result["elapsed_seconds"],
                "disk_bytes": result["disk_bytes"],
            }
        )
    )
    return int(result["completed"] != result["case_count"])


if __name__ == "__main__":
    raise SystemExit(main())
