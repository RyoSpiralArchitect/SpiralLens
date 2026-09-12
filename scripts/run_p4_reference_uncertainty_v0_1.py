"""Registered72-position campaign; a complete reference bank precedes geometry."""

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

import prototype_p4_reference_uncertainty_v0_1 as kernel
import run_p4_signal_strength_v0_1 as previous

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "docs/P4_REFERENCE_UNCERTAINTY_PLAN.md"
PROTOCOL_SHA256 = "e4aa1f7d6a94c9d9274d9a16c858d47eeb813abff11fa52dd0a0d6a8df5b41ce"
CASE_SECONDS, TOTAL_SECONDS = 180, 1800
AS_BYTES, DISK_BYTES = 8 * 2**30, 4 * 2**30
sha, write = previous.sha, previous.write
limits = kernel.spatial.zoom.strength.clone(
    previous.limits, CASE_SECONDS=CASE_SECONDS, AS_BYTES=AS_BYTES
)


def cases():
    return [
        {"lane": "calibration", "reference_seed": seed}
        for seed in kernel.REFERENCE_SEEDS
    ] + [
        {
            "lane": "geometry",
            "alpha": alpha,
            "geometry_seed": seed,
            "fixture": fixture,
            "cells": 256,
        }
        for alpha in kernel.ALPHAS
        for seed in kernel.GEOMETRY_SEEDS
        for fixture in kernel.spatial.FIXTURES
    ]


def source_lock():
    paths = sorted((ROOT / "src").rglob("*.py")) + sorted(
        (ROOT / "scripts").glob("*p4*.py")
    )
    paths += [ROOT / PROTOCOL, ROOT / "tests/test_p4_reference_uncertainty_v0_1.py"]
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}


def assert_source(plan):
    if (
        source_lock() != plan["source_sha256"]
        or plan["protocol_sha256"] != PROTOCOL_SHA256
        or plan["cases"] != cases()
    ):
        raise ValueError("registered source, protocol or condition sequence changed")


def read_unit(directory, record):
    path = directory / record["directory"]
    if (
        record["directory"] != f"unit-{record['index']:03d}"
        or record["status"] != "completed"
        or sha(path / "report.json") != record["report_sha256"]
    ):
        raise ValueError("completed unit receipt changed")
    report = json.loads((path / "report.json").read_text())
    artifact = report["array_artifact"]
    if (
        artifact != record["array_artifact"]
        or artifact["file"] != "arrays.npz"
        or sha(path / "arrays.npz") != artifact["sha256"]
        or (path / "arrays.npz").stat().st_size != artifact["bytes"]
    ):
        raise ValueError("unit array artifact changed")
    return report


def close_bank(directory, records, plan):
    if (
        len(records) != 16
        or [r["index"] for r in records] != list(range(16))
        or any(r["status"] != "completed" for r in records)
    ):
        raise ValueError("all16 calibration cohorts must complete before geometry")
    references = []
    for record in records:
        report = read_unit(directory, record)
        if (
            report["case"] != cases()[record["index"]]
            or report["source_sha256"] != plan["source_sha256"]
        ):
            raise ValueError("calibration source/condition changed")
        references += report["references"]
    body = {
        "schema_version": kernel.SCHEMA + ".bank",
        "calibration_units": records,
        "references": references,
        "plan_sha256": sha(directory / "plan.json"),
        "all_references_sealed_before_geometry": True,
        "scientific_authority": False,
    }
    write(
        directory / "reference-bank.json",
        {**body, "bank_seal_sha256": kernel.SEAL(body)},
    )
    return load_bank(directory)


def load_bank(directory):
    path = directory / "reference-bank.json"
    bank = json.loads(path.read_text())
    body = {k: v for k, v in bank.items() if k != "bank_seal_sha256"}
    if (
        kernel.SEAL(body) != bank["bank_seal_sha256"]
        or bank["plan_sha256"] != sha(directory / "plan.json")
        or bank["scientific_authority"] is not False
        or bank["all_references_sealed_before_geometry"] is not True
    ):
        raise ValueError("reference bank closure/seal changed")
    expected = [
        (seed, k, h)
        for seed in kernel.REFERENCE_SEEDS
        for k in kernel.KS
        for h in kernel.spatial.HYPOTHESES
    ]
    if [
        (r["reference_seed"], r["k"], r["hypothesis"]) for r in bank["references"]
    ] != expected:
        raise ValueError("reference bank lost a cohort, prefix or hypothesis")
    if len(bank["calibration_units"]) != 16 or [
        r["index"] for r in bank["calibration_units"]
    ] != list(range(16)):
        raise ValueError("reference bank has incomplete calibration provenance")
    from_reports = []
    for r in bank["calibration_units"]:
        from_reports += read_unit(directory, r)["references"]
    if from_reports != bank["references"]:
        raise ValueError("bank references differ from calibration terminals")
    for ref in bank["references"]:
        kernel.validate_reference(ref)
    return bank


def child(index, output, launch):
    plan = json.loads(launch.read_text())
    assert_source(plan)
    case, began = cases()[index], time.monotonic()
    bank_hash = None
    if case["lane"] == "calibration":
        report, arrays = kernel.calibrate(case["reference_seed"])
        kernel.verify_calibration(report, arrays)
    else:
        bank = load_bank(launch.parent)
        bank_hash = sha(launch.parent / "reference-bank.json")
        report, arrays = kernel.local_unit(
            bank["references"],
            bank["bank_seal_sha256"],
            **{k: v for k, v in case.items() if k != "lane"},
        )
        kernel.verify_local(
            report, arrays, bank["references"], bank["bank_seal_sha256"]
        )
        if (
            load_bank(launch.parent) != bank
            or sha(launch.parent / "reference-bank.json") != bank_hash
        ):
            raise ValueError("reference bank changed during measurement")
    assert_source(plan)
    output.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(output / "arrays.npz", **arrays)
    report.update(
        case=case,
        source_sha256=plan["source_sha256"],
        bank_file_sha256=bank_hash,
        plan_sha256=sha(launch),
        seconds=time.monotonic() - began,
        peak_rss_bytes=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        * (1 if sys.platform == "darwin" else 1024),
        environment={
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
            "gpu_used": False,
            "model_accessed": False,
        },
        array_artifact={
            "file": "arrays.npz",
            "bytes": (output / "arrays.npz").stat().st_size,
            "sha256": sha(output / "arrays.npz"),
        },
    )
    write(output / "report.json", report)


def validate_output(directory, case, bank=None):
    report = json.loads((directory / "report.json").read_text())
    if (
        report["case"] != case
        or report["schema_version"] != kernel.SCHEMA
        or report["scientific_authority"] is not False
    ):
        raise ValueError("output condition/schema/scope changed")
    artifact = report["array_artifact"]
    if (
        artifact["file"] != "arrays.npz"
        or sha(directory / "arrays.npz") != artifact["sha256"]
        or (directory / "arrays.npz").stat().st_size != artifact["bytes"]
    ):
        raise ValueError("output arrays changed")
    with np.load(directory / "arrays.npz", allow_pickle=False) as arrays:
        if case["lane"] == "calibration":
            if report["repeats"] != 256 or report["ks"] != list(kernel.KS):
                raise ValueError("calibration repeat denominator changed")
            kernel.verify_calibration(report, arrays)
        else:
            if bank is None:
                raise ValueError("geometry cannot validate without a complete bank")
            kernel.verify_local(
                report, arrays, bank["references"], bank["bank_seal_sha256"]
            )
    return report


def run(output):
    if platform.system() != "Linux" or sha(ROOT / PROTOCOL) != PROTOCOL_SHA256:
        raise ValueError("registered protocol and Linux execution required")
    if subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True
    ).strip():
        raise ValueError("clean committed execution source required")
    lock = source_lock()
    output.mkdir(parents=True, exist_ok=False)
    plan = {
        "schema_version": kernel.SCHEMA + ".campaign",
        "protocol_sha256": PROTOCOL_SHA256,
        "checkout_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "source_sha256": lock,
        "cases": cases(),
        "planned_units": 72,
        "reference_cohorts": 16,
        "averaged_references": 160,
        "local_reconstructions": 9072,
        "scientific_authority": False,
        "calibration_estimand": "separately-observable-background-only-synthetic-channel",
        "resource_limits": {
            "case_seconds": CASE_SECONDS,
            "campaign_seconds": TOTAL_SECONDS,
            "address_space_bytes": AS_BYTES,
            "pre_unit_disk_bytes": DISK_BYTES,
            "concurrent_children": 1,
            "blas_threads": 1,
            "gpu_used": False,
        },
    }
    write(output / "plan.json", plan)
    records, bank, began = [], None, time.monotonic()
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
    for index, case in enumerate(cases()):
        elapsed = time.monotonic() - began
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
        if index == 16:
            try:
                bank = close_bank(output, records, plan)
            except (ValueError, KeyError, OSError, TypeError) as exc:
                records.extend(
                    {
                        "index": i,
                        "case": c,
                        "status": "not_run",
                        "reason": "reference-bank-incomplete",
                        "error": str(exc),
                    }
                    for i, c in enumerate(cases()[index:], index)
                )
                break
        unit = output / f"unit-{index:03d}"
        record = {
            "index": index,
            "case": case,
            "status": "running",
            "directory": unit.name,
            "plan_sha256": sha(output / "plan.json"),
            "bank_file_sha256": sha(output / "reference-bank.json") if bank else None,
        }
        write(output / f"unit-{index:03d}.attempt.json", record)
        started = time.monotonic()
        with (
            (output / f"unit-{index:03d}.stdout").open("x") as stdout,
            (output / f"unit-{index:03d}.stderr").open("x") as stderr,
        ):
            try:
                run = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(Path(__file__).resolve()),
                        "--child",
                        str(index),
                        "--launch",
                        str(output / "plan.json"),
                        "--output",
                        str(unit),
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
                    status="completed" if run.returncode == 0 else "failed",
                    returncode=run.returncode,
                )
            except subprocess.TimeoutExpired:
                record.update(status="timeout", reason="bounded-unit-deadline")
            except OSError as exc:
                record.update(
                    status="failed", reason="child-launch-error", error=str(exc)
                )
        if record["status"] == "completed":
            try:
                report = validate_output(unit, case, bank)
                assert_source(plan)
                if (
                    report["source_sha256"] != lock
                    or report["plan_sha256"] != record["plan_sha256"]
                    or report["bank_file_sha256"] != record["bank_file_sha256"]
                ):
                    raise ValueError("unit launch/source/bank binding changed")
                record.update(
                    report_sha256=sha(unit / "report.json"),
                    array_artifact=report["array_artifact"],
                    peak_rss_bytes=report["peak_rss_bytes"],
                )
            except (ValueError, OSError, KeyError, TypeError) as exc:
                record.update(
                    status="failed", reason="result-validation", error=str(exc)
                )
        record["seconds"] = time.monotonic() - started
        write(output / f"unit-{index:03d}.terminal.json", record)
        records.append(record)
        print(
            json.dumps({k: record[k] for k in ("index", "case", "status", "seconds")}),
            flush=True,
        )
        if record["status"] != "completed":
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
    write(
        output / "manifest.json",
        {
            "schema_version": kernel.SCHEMA + ".manifest",
            "units": records,
            "plan_sha256": sha(output / "plan.json"),
            "seconds": time.monotonic() - began,
            "source_unchanged": source_lock() == lock,
            "bank_file_sha256": sha(output / "reference-bank.json") if bank else None,
            "scientific_authority": False,
        },
    )
    return (
        len(records) == 72
        and all(r["status"] == "completed" for r in records)
        and source_lock() == lock
    )


def verify(output):
    plan = json.loads((output / "plan.json").read_text())
    manifest = json.loads((output / "manifest.json").read_text())
    assert_source(plan)
    if (
        manifest["plan_sha256"] != sha(output / "plan.json")
        or [r["index"] for r in manifest["units"]] != list(range(72))
        or [r["case"] for r in manifest["units"]] != cases()
    ):
        raise ValueError("campaign plan/denominator changed")
    bank = load_bank(output) if (output / "reference-bank.json").exists() else None
    if manifest["bank_file_sha256"] != (
        sha(output / "reference-bank.json") if bank else None
    ):
        raise ValueError("manifest/reference-bank binding changed")
    completed, local, fits = 0, 0, 0
    for r in manifest["units"]:
        if r["status"] != "completed":
            continue
        report = read_unit(output, r)
        validated = validate_output(output / r["directory"], r["case"], bank)
        if report != validated or report["source_sha256"] != plan["source_sha256"]:
            raise ValueError("verified report source changed")
        if r["case"]["lane"] == "calibration":
            fits += 512
        else:
            local += len(report["records"])
            if report["bank_file_sha256"] != sha(output / "reference-bank.json"):
                raise ValueError("geometry reference bank changed")
        completed += 1
    assert_source(plan)
    return {
        "manifest_sha256": sha(output / "manifest.json"),
        "plan_sha256": sha(output / "plan.json"),
        "bank_file_sha256": sha(output / "reference-bank.json") if bank else None,
        "completed_units": completed,
        "planned_units": 72,
        "replayed_repeat_fits": fits,
        "replayed_local_records": local,
        "output_hashes_checked": completed * 2,
        "source_hashes_checked": len(plan["source_sha256"]),
        "scientific_authority": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--child", type=int)
    parser.add_argument("--launch", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.child is not None:
        if not 0 <= args.child < 72 or args.launch is None:
            parser.error("registered child and launch plan required")
        child(args.child, args.output, args.launch)
    elif args.verify:
        receipt = verify(args.output)
        write(args.output / "verification.json", receipt)
        print(json.dumps(receipt))
    elif not run(args.output):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
