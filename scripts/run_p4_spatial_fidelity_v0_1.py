"""One-child, immutable-input Furnace execution of the 102-unit fidelity plan."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time

import numpy as np

import prototype_p4_spatial_fidelity_v0_1 as kernel
import run_p4_signal_strength_v0_1 as previous

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "docs/P4_SPATIAL_FIDELITY_PLAN.md"
PROTOCOL_SHA256 = "4047e7f318bc5b89a4716667299267eb2171c8862f5ba3d63e3fddaed601e3f4"
MANIFESTS = {
    "strength": "f0b5bc294ef7c18ca1ff2bbab99c9fe7aa9d3dabfa029aee11850718147357a7",
    "zoom": "7b5a8529f0332109cbef71804dbf3b365ca3064c8717b87f827df1a3ffbc3125",
}
CASE_SECONDS, TOTAL_SECONDS = 180, 1800
AS_BYTES, DISK_BYTES = 8 * 2**30, 4 * 2**30
sha, write = previous.sha, previous.write
limits = kernel.zoom.strength.clone(
    previous.limits, CASE_SECONDS=CASE_SECONDS, AS_BYTES=AS_BYTES
)


def cases():
    result = []
    for seed in range(4):
        for alpha in (0.04, 0.08, 0.1, 0.2):
            result.append(
                {
                    "lane": "outer",
                    "source": "strength",
                    "source_index": (8 + seed) * 33
                    + kernel.zoom.strength.STRENGTHS.index(alpha),
                    "reference_seed": seed,
                    "alpha": alpha,
                }
            )
    result += [
        {
            "lane": "outer",
            "source": "zoom",
            "source_index": i,
            "reference_seed": 0,
            "alpha": a,
        }
        for i, a in ((68, 0.00825), (82, 0.01))
    ]
    for seed in range(4):
        for fixture in kernel.FIXTURES:
            for cells in kernel.CELL_COUNTS:
                result.append(
                    {
                        "lane": "local",
                        "source": "strength",
                        "source_index": (8 + seed) * 33
                        + kernel.zoom.strength.STRENGTHS.index(0.1),
                        "reference_seed": seed,
                        "alpha": 0.1,
                        "fixture": fixture,
                        "geometry_seed": 100 + seed,
                        "cells": cells,
                    }
                )
    return result


def source_lock():
    paths = sorted((ROOT / "src").rglob("*.py"))
    paths += sorted((ROOT / "scripts").glob("*p4*.py"))
    paths += [ROOT / PROTOCOL, ROOT / "tests/test_p4_spatial_fidelity_v0_1.py"]
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}


def input_catalog(directories):
    catalog = {}
    for name, directory in directories.items():
        if sha(directory / "manifest.json") != MANIFESTS[name]:
            raise ValueError("predecessor manifest hash changed")
        manifest = json.loads((directory / "manifest.json").read_text())
        indices = sorted({c["source_index"] for c in cases() if c["source"] == name})
        for index in indices:
            record = manifest["units"][index]
            if record["index"] != index or record["status"] != "completed":
                raise ValueError("required predecessor not completed")
            unit = directory / record["directory"]
            if unit.parent != directory or not unit.name == f"unit-{index:03d}":
                raise ValueError("predecessor unit path changed")
            report_path = unit / "report.json"
            if sha(report_path) != record["report_sha256"]:
                raise ValueError("predecessor report changed")
            report = json.loads(report_path.read_text())
            artifact = report["array_artifact"]
            if (
                artifact["file"] != "arrays.npz"
                or sha(unit / "arrays.npz") != artifact["sha256"]
                or (unit / "arrays.npz").stat().st_size != artifact["bytes"]
            ):
                raise ValueError("predecessor array artifact changed")
            expected = next(
                c for c in cases() if c["source"] == name and c["source_index"] == index
            )
            if report["spec"] != {
                "baseline_noise": 0.03,
                "k": 8,
                "pattern": "quadratic_excess",
                "probe_count": 128,
                "seed": expected["reference_seed"],
                "side": 65,
                "signal_strength": expected["alpha"],
            }:
                raise ValueError("predecessor condition changed")
            catalog[f"{name}/{index}"] = {
                "directory": str(unit),
                "report_sha256": record["report_sha256"],
                "array_artifact": artifact,
            }
    return catalog


def load_input(entry):
    directory = Path(entry["directory"])
    if (
        sha(directory / "report.json") != entry["report_sha256"]
        or sha(directory / "arrays.npz") != entry["array_artifact"]["sha256"]
    ):
        raise ValueError("input changed after launch plan")
    report = json.loads((directory / "report.json").read_text())
    with np.load(directory / "arrays.npz", allow_pickle=False) as stored:
        arrays = {k: stored[k] for k in stored.files}
    return report, arrays


def run_child(index, output, launch):
    plan = json.loads(launch.read_text())
    case = cases()[index]
    if plan["cases"][index] != case or source_lock() != plan["source_sha256"]:
        raise ValueError("child source or condition changed")
    input_entry = plan["input_catalog"][f"{case['source']}/{case['source_index']}"]
    report, arrays = load_input(input_entry)
    started = time.monotonic()
    if case["lane"] == "outer":
        result, measured = kernel.outer_unit(report, arrays)
    else:
        result, measured = kernel.local_unit(
            report,
            arrays,
            fixture=case["fixture"],
            geometry_seed=case["geometry_seed"],
            cells=case["cells"],
        )
    kernel.verify_replay(result, measured)
    if (
        sha(Path(input_entry["directory"]) / "arrays.npz")
        != input_entry["array_artifact"]["sha256"]
        or sha(Path(input_entry["directory"]) / "report.json")
        != input_entry["report_sha256"]
        or source_lock() != plan["source_sha256"]
    ):
        raise ValueError("source/input changed during measurement")
    output.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(output / "arrays.npz", **measured)
    result.update(
        schema_version=kernel.SCHEMA,
        case=case,
        input=input_entry,
        seconds=time.monotonic() - started,
        peak_rss_bytes=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        * (1 if sys.platform == "darwin" else 1024),
        array_artifact={
            "file": "arrays.npz",
            "sha256": sha(output / "arrays.npz"),
            "bytes": (output / "arrays.npz").stat().st_size,
        },
        source_sha256=plan["source_sha256"],
        environment={
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
            "backend": "numpy",
            "gpu_used": False,
        },
        raw_array_replay_verified=True,
    )
    write(output / "report.json", result)


def validate_unit(directory, case):
    report = json.loads((directory / "report.json").read_text())
    artifact = report["array_artifact"]
    if (
        report["case"] != case
        or report["schema_version"] != kernel.SCHEMA
        or report["scientific_authority"] is not False
    ):
        raise ValueError("unit condition or authority changed")
    if (
        artifact["file"] != "arrays.npz"
        or sha(directory / "arrays.npz") != artifact["sha256"]
        or (directory / "arrays.npz").stat().st_size != artifact["bytes"]
    ):
        raise ValueError("output arrays changed")
    with np.load(directory / "arrays.npz", allow_pickle=False) as arrays:
        kernel.verify_replay(report, arrays)
    return report


def campaign(output, directories):
    output = output.resolve()
    if any(
        output == p or output in p.parents or p in output.parents
        for p in directories.values()
    ):
        raise ValueError("output and predecessor trees must be disjoint")
    if sha(ROOT / PROTOCOL) != PROTOCOL_SHA256:
        raise ValueError("registered protocol changed")
    if subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True
    ).strip():
        raise ValueError("clean tracked execution source required")
    lock, catalog = source_lock(), input_catalog(directories)
    output.mkdir(parents=True, exist_ok=False)
    write(
        output / "plan.json",
        {
            "schema_version": kernel.SCHEMA + ".campaign",
            "protocol": PROTOCOL,
            "protocol_sha256": PROTOCOL_SHA256,
            "checkout_revision": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "source_sha256": lock,
            "input_catalog": catalog,
            "predecessor_manifests": MANIFESTS,
            "cases": cases(),
            "units": 102,
            "outer_readouts": 1296,
            "distinct_local_reconstructions": 504,
            "row_addressed_local_records": 1512,
            "scientific_authority": False,
            "resource_limits": {
                "case_seconds": CASE_SECONDS,
                "campaign_seconds": TOTAL_SECONDS,
                "address_space_bytes": AS_BYTES,
                "pre_unit_disk_bytes": DISK_BYTES,
                "concurrent_children": 1,
                "blas_threads": 1,
                "gpu_used": False,
            },
        },
    )
    env = dict(
        os.environ,
        PYTHONPATH=str(ROOT / "src"),
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        PYTHONDONTWRITEBYTECODE="1",
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
    )
    started, records = time.monotonic(), []
    for index, case in enumerate(cases()):
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
                {"index": i, "case": c, "status": "not_run", "reason": reason}
                for i, c in enumerate(cases()[index:], index)
            )
            break
        directory = output / f"unit-{index:03d}"
        record = {
            "index": index,
            "case": case,
            "status": "running",
            "directory": directory.name,
            "plan_sha256": sha(output / "plan.json"),
        }
        write(output / f"unit-{index:03d}.attempt.json", record)
        began = time.monotonic()
        with (
            (output / f"unit-{index:03d}.stdout").open("x") as stdout,
            (output / f"unit-{index:03d}.stderr").open("x") as stderr,
        ):
            try:
                child = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(Path(__file__).resolve()),
                        "--child",
                        str(index),
                        "--output",
                        str(directory),
                        "--launch",
                        str(output / "plan.json"),
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
                    status="completed" if child.returncode == 0 else "failed",
                    returncode=child.returncode,
                )
            except subprocess.TimeoutExpired:
                record.update(status="timeout", reason="bounded-unit-deadline")
            except OSError as exc:
                record.update(
                    status="failed", reason="child-launch-error", error=str(exc)
                )
        if record["status"] == "completed":
            try:
                result = validate_unit(directory, case)
                if result["source_sha256"] != lock or source_lock() != lock:
                    raise ValueError("source changed during unit")
                record.update(
                    report_sha256=sha(directory / "report.json"),
                    array_artifact=result["array_artifact"],
                    peak_rss_bytes=result["peak_rss_bytes"],
                )
            except (OSError, ValueError, KeyError, TypeError) as exc:
                record.update(
                    status="failed", reason="result-validation", error=str(exc)
                )
        record["seconds"] = time.monotonic() - began
        write(output / f"unit-{index:03d}.terminal.json", record)
        records.append(record)
        print(
            json.dumps({k: record[k] for k in ("index", "case", "status", "seconds")}),
            flush=True,
        )
        if record["status"] != "completed":
            # Preserve failures; a systematic failure is not worth 101 repeats.
            records.extend(
                {
                    "index": i,
                    "case": c,
                    "status": "not_run",
                    "reason": "prior-unit-failed",
                }
                for i, c in enumerate(cases()[index + 1 :], index + 1)
            )
            break
    inputs_unchanged = input_catalog(directories) == catalog
    write(
        output / "manifest.json",
        {
            "schema_version": kernel.SCHEMA + ".manifest",
            "units": records,
            "seconds": time.monotonic() - started,
            "source_unchanged": source_lock() == lock,
            "inputs_unchanged": inputs_unchanged,
            "plan_sha256": sha(output / "plan.json"),
            "scientific_authority": False,
        },
    )
    return (
        all(r["status"] == "completed" for r in records)
        and inputs_unchanged
        and source_lock() == lock
    )


def verify(directory):
    plan = json.loads((directory / "plan.json").read_text())
    manifest = json.loads((directory / "manifest.json").read_text())
    if (
        manifest["plan_sha256"] != sha(directory / "plan.json")
        or plan["source_sha256"] != source_lock()
        or plan["protocol_sha256"] != PROTOCOL_SHA256
    ):
        raise ValueError("campaign source/plan changed")
    if [r["case"] for r in manifest["units"]] != cases() or [
        r["index"] for r in manifest["units"]
    ] != list(range(102)):
        raise ValueError("planned denominator changed")
    output_count, replay_count = 0, 0
    for r in manifest["units"]:
        if r["status"] == "completed":
            unit = directory / r["directory"]
            if (
                r["directory"] != f"unit-{r['index']:03d}"
                or sha(unit / "report.json") != r["report_sha256"]
            ):
                raise ValueError("reported output changed")
            report = validate_unit(unit, r["case"])
            if (
                report["source_sha256"] != plan["source_sha256"]
                or report["input"]
                != plan["input_catalog"][
                    f"{r['case']['source']}/{r['case']['source_index']}"
                ]
            ):
                raise ValueError("unit source/input receipt changed")
            replay_count += 72 if r["case"]["lane"] == "outer" else 6
            output_count += 2
    for entry in plan["input_catalog"].values():
        load_input(entry)
    if source_lock() != plan["source_sha256"]:
        raise ValueError("source changed during verification")
    return {
        "schema_version": kernel.SCHEMA + ".verification",
        "manifest_sha256": sha(directory / "manifest.json"),
        "plan_sha256": sha(directory / "plan.json"),
        "completed_units": sum(r["status"] == "completed" for r in manifest["units"]),
        "planned_units": 102,
        "output_hashes_checked": output_count,
        "replayed_readouts_and_reconstructions": replay_count,
        "source_files_checked": len(plan["source_sha256"]),
        "input_pairs_checked": len(plan["input_catalog"]),
        "scientific_authority": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--strength", type=Path)
    parser.add_argument("--zoom", type=Path)
    parser.add_argument("--child", type=int)
    parser.add_argument("--launch", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.child is not None:
        if not 0 <= args.child < 102 or args.launch is None:
            parser.error("registered child index and launch plan required")
        run_child(args.child, args.output, args.launch)
    elif args.verify:
        receipt = verify(args.output)
        write(args.output / "verification.json", receipt)
        print(json.dumps(receipt))
    else:
        if args.strength is None or args.zoom is None:
            parser.error("both immutable predecessor directories required")
        if not campaign(
            args.output,
            {"strength": args.strength.resolve(), "zoom": args.zoom.resolve()},
        ):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
