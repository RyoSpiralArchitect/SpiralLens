"""Run the registered 32-unit independent-reference synthetic CPU panel.

No baseline is selected by its result. Attempts, failures and unrun units are
retained. The committed protocol is pinned separately from the launch source.
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

import prototype_p4_reference_validation_v0_1 as kernel

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "docs/P4_REFERENCE_VALIDATION_PLAN.md"
PROTOCOL_SHA256 = "a2b9deb11e338e77a7228a47eb414fbdc4826a8ad6f3310c1beef12d7ab10212"
CASE_SECONDS = 180
TOTAL_SECONDS = 1200
AS_BYTES = 16 * 2**30
DISK_BYTES = 8 * 2**30


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, data):
    with path.open("x") as stream:
        json.dump(data, stream, sort_keys=True, allow_nan=False)
        stream.write("\n")


def case_specs():
    specs = [
        kernel.ReferenceSpec(
            side=65, pattern=pattern, seed=seed, probe_count=count, baseline_noise=0.03
        )
        for pattern in ("curved_coherent", "quadratic_excess")
        for seed in (0, 1, 2, 3)
        for count in (8, 32, 128)
    ]
    specs += [
        kernel.ReferenceSpec(
            side=257, pattern=pattern, seed=seed, probe_count=128, baseline_noise=0.03
        )
        for pattern in ("curved_coherent", "quadratic_excess")
        for seed in (0, 1)
    ]
    specs += [
        kernel.ReferenceSpec(
            side=65, pattern=pattern, seed=0, probe_count=count, baseline_noise=0.0
        )
        for pattern in ("curved_coherent", "quadratic_excess")
        for count in (8, 128)
    ]
    return specs


def source_lock():
    files = sorted((ROOT / "src").rglob("*.py"))
    files += sorted((ROOT / "scripts").glob("*p4*.py"))
    files += [ROOT / PROTOCOL, ROOT / "tests/test_p4_reference_validation_v0_1.py"]
    return {str(path.relative_to(ROOT)): sha(path) for path in files}


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (AS_BYTES, AS_BYTES))
    resource.setrlimit(resource.RLIMIT_CPU, (CASE_SECONDS, CASE_SECONDS + 1))
    resource.setrlimit(resource.RLIMIT_FSIZE, (2 * 2**30, 2 * 2**30))
    os.nice(10)


def run_child(index, output):
    specs = case_specs()
    if not 0 <= index < len(specs):
        raise ValueError("child index outside the registered 32-unit panel")
    report, _ = kernel.measure_pair(specs[index], output=output)
    print(
        json.dumps(
            {"index": index, "spec": report["spec"], "summary": report["summary"]},
            allow_nan=False,
        ),
        flush=True,
    )


def run(output):
    if platform.system() != "Linux":
        raise ValueError("bounded reference campaign requires Linux")
    if sha(ROOT / PROTOCOL) != PROTOCOL_SHA256:
        raise ValueError("registered protocol bytes changed")
    specs = case_specs()
    lock = source_lock()
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    output.mkdir(parents=True, exist_ok=False)
    plan = {
        "schema": "spirallens.p4-reference-validation-campaign.v0.1",
        "protocol": PROTOCOL,
        "protocol_sha256": PROTOCOL_SHA256,
        "source_sha256": lock,
        "checkout_revision": revision,
        "paired_units": len(specs),
        "arm_measurements": 2 * len(specs),
        "cases": [asdict(s) for s in specs],
        "reference_backend": "numpy",
        "gpu_used": False,
        "resource_limits": {
            "case_seconds": CASE_SECONDS,
            "campaign_seconds": TOTAL_SECONDS,
            "address_space_bytes": AS_BYTES,
            "max_file_bytes": 2 * 2**30,
            "pre_unit_disk_admission_bytes": DISK_BYTES,
            "concurrent_children": 1,
            "blas_threads": 1,
        },
        "baseline_selection_performed": False,
        "heldout_acceptance_threshold": None,
        "model_accessed": False,
        "scientific_authority": False,
    }
    write(output / "plan.json", plan)
    plan_hash = sha(output / "plan.json")
    env = dict(
        os.environ,
        PYTHONPATH=str(ROOT / "src"),
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
    )
    started = time.monotonic()
    records = []
    for index, spec in enumerate(specs):
        elapsed = time.monotonic() - started
        used = sum(p.stat().st_size for p in output.rglob("*") if p.is_file())
        reason = (
            "campaign-time-budget"
            if elapsed >= TOTAL_SECONDS
            else "disk-admission-budget"
            if used >= DISK_BYTES
            else "source-changed"
            if source_lock() != lock
            else None
        )
        if reason:
            records.extend(
                {"index": i, "spec": asdict(s), "status": "not_run", "reason": reason}
                for i, s in enumerate(specs[index:], index)
            )
            break
        directory = output / f"unit-{index:02d}"
        record = {
            "index": index,
            "spec": asdict(spec),
            "status": "running",
            "directory": directory.name,
            "plan_sha256": plan_hash,
        }
        write(output / f"unit-{index:02d}.attempt.json", record)
        began = time.monotonic()
        with (
            (output / f"unit-{index:02d}.stdout").open("x") as stdout,
            (output / f"unit-{index:02d}.stderr").open("x") as stderr,
        ):
            try:
                process = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(Path(__file__).resolve()),
                        "--child",
                        str(index),
                        "--output",
                        str(directory),
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
                    status="completed" if process.returncode == 0 else "failed",
                    returncode=process.returncode,
                )
            except subprocess.TimeoutExpired:
                record.update(status="timeout", reason="bounded-unit-deadline")
            except OSError as exc:
                record.update(
                    status="failed", reason="child-launch-error", error=str(exc)
                )
        record["seconds"] = time.monotonic() - began
        if record["status"] == "completed":
            try:
                report = json.loads((directory / "report.json").read_text())
                if report["spec"] != asdict(spec) or set(report["arms"]) != {"A", "B"}:
                    raise ValueError(
                        "returned unit does not match registered spec/arms"
                    )
                if any(len(a["cells"]) != 9 for a in report["arms"].values()):
                    raise ValueError("returned arm lost the nine-cell denominator")
                array = directory / report["array_artifact"]["file"]
                if (
                    array != directory / "arrays.npz"
                    or array.stat().st_size != report["array_artifact"]["bytes"]
                ):
                    raise ValueError(
                        "returned array artifact does not match recorded path/size"
                    )
                record.update(
                    report_sha256=sha(directory / "report.json"),
                    array_artifact=report["array_artifact"],
                    summary=report["summary"],
                    peak_rss_bytes=report["peak_rss_bytes"],
                    timing=report["timing"],
                )
            except (OSError, ValueError, KeyError, TypeError) as exc:
                record.update(
                    status="failed", reason="result-validation", error=str(exc)
                )
        write(output / f"unit-{index:02d}.terminal.json", record)
        records.append(record)
        print(
            json.dumps(
                {
                    k: v
                    for k, v in record.items()
                    if k not in ("summary", "array_artifact")
                }
            ),
            flush=True,
        )
    manifest = {
        "plan_sha256": plan_hash,
        "protocol_sha256": PROTOCOL_SHA256,
        "host": platform.node(),
        "python": platform.python_version(),
        "paired_units": len(specs),
        "arm_measurements_planned": 2 * len(specs),
        "completed": sum(r["status"] == "completed" for r in records),
        "units": records,
        "elapsed_seconds": time.monotonic() - started,
        "disk_bytes": sum(p.stat().st_size for p in output.rglob("*") if p.is_file()),
        "baseline_selection_performed": False,
        "model_accessed": False,
        "gpu_used": False,
        "scientific_authority": False,
    }
    write(output / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--child", type=int)
    args = parser.parse_args()
    if args.child is not None:
        run_child(args.child, args.output)
        return 0
    result = run(args.output)
    print(json.dumps({k: v for k, v in result.items() if k != "units"}))
    return int(result["completed"] != result["paired_units"])


if __name__ == "__main__":
    raise SystemExit(main())
