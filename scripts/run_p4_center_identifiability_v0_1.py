"""Registered144-position center-identifiability campaign on isolated Linux."""

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

import prototype_p4_center_identifiability_v0_1 as kernel
import run_p4_signal_strength_v0_1 as previous

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "docs/P4_CENTER_IDENTIFIABILITY_PLAN.md"
PROTOCOL_SHA256 = "ad65b0facdcf453dbd6e62a57b78e8e0da82bd81204a47eb04e050de8c791072"
CASE_SECONDS, TOTAL_SECONDS = 180, 2400
AS_BYTES, DISK_BYTES = 8 * 2**30, 8 * 2**30
sha, write = previous.sha, previous.write
limits = kernel.spatial.zoom.strength.clone(
    previous.limits, CASE_SECONDS=CASE_SECONDS, AS_BYTES=AS_BYTES
)


def cases():
    return (
        [
            {"lane": "envelope_calibration", "reference_seed": s}
            for s in kernel.ENVELOPE_SEEDS
        ]
        + [
            {"lane": "evaluation_reference", "reference_seed": s}
            for s in kernel.REFERENCE_SEEDS
        ]
        + [
            {
                "lane": "geometry",
                "alpha": a,
                "geometry_seed": s,
                "fixture": f,
                "cells": 256,
            }
            for a in kernel.ALPHAS
            for s in kernel.GEOMETRY_SEEDS
            for f in kernel.FIXTURES
        ]
    )


def source_lock():
    paths = sorted((ROOT / "src").rglob("*.py")) + sorted(
        (ROOT / "scripts").glob("*p4*.py")
    )
    paths += [ROOT / PROTOCOL, ROOT / "tests/test_p4_center_identifiability_v0_1.py"]
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}


def assert_source(plan):
    if (
        source_lock() != plan["source_sha256"]
        or plan["protocol_sha256"] != PROTOCOL_SHA256
        or plan["cases"] != cases()
    ):
        raise ValueError("registered source, protocol or case sequence changed")


def read_unit(directory, record, *, arrays=False):
    if (
        record["status"] != "completed"
        or record["directory"] != f"unit-{record['index']:03d}"
    ):
        raise ValueError("completed canonical unit required")
    unit = directory / record["directory"]
    if sha(unit / "report.json") != record["report_sha256"]:
        raise ValueError("report hash changed")
    report = json.loads((unit / "report.json").read_text())
    artifact = report["array_artifact"]
    if artifact != record["array_artifact"] or artifact["file"] != "arrays.npz":
        raise ValueError("array artifact binding changed")
    if arrays and (
        sha(unit / "arrays.npz") != artifact["sha256"]
        or (unit / "arrays.npz").stat().st_size != artifact["bytes"]
    ):
        raise ValueError("raw array bytes changed")
    return report


def reports_for(directory, records, indices):
    if len(records) != len(indices) or [r["index"] for r in records] != list(indices):
        raise ValueError("complete ordered calibration positions required")
    plan = json.loads((directory / "plan.json").read_text())
    reports = []
    for record in records:
        report = read_unit(directory, record)
        if (
            report["case"] != cases()[record["index"]]
            or report["source_sha256"] != plan["source_sha256"]
            or report["plan_sha256"] != sha(directory / "plan.json")
        ):
            raise ValueError("calibration condition/source/plan changed")
        if report["repeats"] != 4096 or report["ks"] != list(kernel.KS):
            raise ValueError("calibration repeat denominator changed")
        reports.append(report)
    return reports


def seal_file(path, body):
    write(path, {**body, "file_seal_sha256": kernel.SEAL(body)})


def load_sealed(path, directory):
    document = json.loads(path.read_text())
    body = {k: v for k, v in document.items() if k != "file_seal_sha256"}
    if (
        kernel.SEAL(body) != document["file_seal_sha256"]
        or document["plan_sha256"] != sha(directory / "plan.json")
        or document["scientific_authority"] is not False
    ):
        raise ValueError("bank file closure/claim/plan changed")
    return document


def close_envelope(directory, records):
    reports = reports_for(directory, records, range(32))
    envelope = kernel.make_envelope(reports)
    seal_file(
        directory / "envelope-bank.json",
        {
            "schema_version": kernel.SCHEMA + ".envelope-bank",
            "envelope": envelope,
            "calibration_units": records,
            "plan_sha256": sha(directory / "plan.json"),
            "evaluation_references_observed": False,
            "scientific_authority": False,
        },
    )
    return load_envelope(directory)


def load_envelope(directory):
    document = load_sealed(directory / "envelope-bank.json", directory)
    if (
        document["schema_version"] != kernel.SCHEMA + ".envelope-bank"
        or document["evaluation_references_observed"] is not False
    ):
        raise ValueError("envelope bank schema/chronology changed")
    reports = reports_for(directory, document["calibration_units"], range(32))
    if any(
        r["envelope_file_sha256"] is not None or r["bank_file_sha256"] is not None
        for r in reports
    ):
        raise ValueError("envelope calibration consumed downstream bank")
    expected = kernel.make_envelope(reports)
    if expected != document["envelope"]:
        raise ValueError("envelope differs from calibration reports")
    kernel.validate_envelope(expected)
    return document


def close_references(directory, records):
    envelope = load_envelope(directory)
    reports = reports_for(directory, records, range(32, 48))
    refs = [r for report in reports for r in report["references"]]
    seal_file(
        directory / "reference-bank.json",
        {
            "schema_version": kernel.SCHEMA + ".reference-bank",
            "envelope_file_sha256": sha(directory / "envelope-bank.json"),
            "envelope_seal_sha256": envelope["envelope"]["envelope_seal_sha256"],
            "reference_units": records,
            "references": refs,
            "plan_sha256": sha(directory / "plan.json"),
            "geometry_observed": False,
            "scientific_authority": False,
        },
    )
    return load_references(directory)


def load_references(directory):
    envelope = load_envelope(directory)
    bank = load_sealed(directory / "reference-bank.json", directory)
    if (
        bank["schema_version"] != kernel.SCHEMA + ".reference-bank"
        or bank["geometry_observed"] is not False
        or bank["envelope_file_sha256"] != sha(directory / "envelope-bank.json")
        or bank["envelope_seal_sha256"] != envelope["envelope"]["envelope_seal_sha256"]
    ):
        raise ValueError("evaluation reference bank envelope/chronology changed")
    reports = reports_for(directory, bank["reference_units"], range(32, 48))
    if any(
        r["envelope_file_sha256"] != sha(directory / "envelope-bank.json")
        or r["bank_file_sha256"] is not None
        or r["lane"] != "evaluation_reference"
        for r in reports
    ):
        raise ValueError("evaluation references lost prior envelope binding")
    refs = [r for report in reports for r in report["references"]]
    if refs != bank["references"] or [
        (r["reference_seed"], r["k"], r["hypothesis"]) for r in refs
    ] != [
        (s, k, h)
        for s in kernel.REFERENCE_SEEDS
        for k in kernel.KS
        for h in kernel.spatial.HYPOTHESES
    ]:
        raise ValueError("evaluation reference denominator changed")
    for ref in refs:
        kernel.validate_reference(ref)
        if ref["role"] != "evaluation_reference":
            raise ValueError("training reference reused in evaluation")
    return bank, envelope["envelope"]


def child(index, output, launch):
    plan = json.loads(launch.read_text())
    assert_source(plan)
    case, began = cases()[index], time.monotonic()
    envelope_hash, bank_hash = None, None
    if case["lane"] != "envelope_calibration":
        load_envelope(launch.parent)
        envelope_hash = sha(launch.parent / "envelope-bank.json")
    if case["lane"] == "geometry":
        bank, envelope = load_references(launch.parent)
        bank_hash = sha(launch.parent / "reference-bank.json")
        report, arrays = kernel.local_unit(
            bank["references"],
            envelope,
            bank["file_seal_sha256"],
            **{k: v for k, v in case.items() if k != "lane"},
        )
        kernel.verify_local(
            report, arrays, bank["references"], envelope, bank["file_seal_sha256"]
        )
        if (
            load_references(launch.parent) != (bank, envelope)
            or sha(launch.parent / "reference-bank.json") != bank_hash
        ):
            raise ValueError("reference bank changed during consumption")
    else:
        report, arrays = kernel.calibrate(case["reference_seed"], case["lane"])
        kernel.verify_calibration(report, arrays)
    if envelope_hash is not None:
        load_envelope(launch.parent)
        if sha(launch.parent / "envelope-bank.json") != envelope_hash:
            raise ValueError("envelope changed during consumption")
    assert_source(plan)
    output.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(output / "arrays.npz", **arrays)
    report.update(
        case=case,
        source_sha256=plan["source_sha256"],
        plan_sha256=sha(launch),
        envelope_file_sha256=envelope_hash,
        bank_file_sha256=bank_hash,
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


def validate_output(unit, case, directory):
    report = json.loads((unit / "report.json").read_text())
    if (
        report["case"] != case
        or report["schema_version"] != kernel.SCHEMA
        or report["scientific_authority"] is not False
    ):
        raise ValueError("returned unit schema/condition/claim changed")
    artifact = report["array_artifact"]
    if (
        artifact["file"] != "arrays.npz"
        or sha(unit / "arrays.npz") != artifact["sha256"]
        or (unit / "arrays.npz").stat().st_size != artifact["bytes"]
    ):
        raise ValueError("returned raw array binding changed")
    with np.load(unit / "arrays.npz", allow_pickle=False) as arrays:
        if case["lane"] == "geometry":
            bank, envelope = load_references(directory)
            if report["envelope_file_sha256"] != sha(
                directory / "envelope-bank.json"
            ) or report["bank_file_sha256"] != sha(directory / "reference-bank.json"):
                raise ValueError("geometry launch bank changed")
            kernel.verify_local(
                report, arrays, bank["references"], envelope, bank["file_seal_sha256"]
            )
        else:
            if report["repeats"] != 4096 or report["ks"] != list(kernel.KS):
                raise ValueError("calibration denominator changed")
            kernel.verify_calibration(report, arrays)
            expected_envelope = (
                sha(directory / "envelope-bank.json")
                if case["lane"] == "evaluation_reference"
                else None
            )
            if (
                report["envelope_file_sha256"] != expected_envelope
                or report["bank_file_sha256"] is not None
            ):
                raise ValueError("calibration chronology changed")
    return report


def run(output):
    if platform.system() != "Linux" or sha(ROOT / PROTOCOL) != PROTOCOL_SHA256:
        raise ValueError("committed protocol and Linux execution required")
    if subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True
    ).strip():
        raise ValueError("clean committed source required")
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
        "planned_units": 144,
        "envelope_cohorts": 32,
        "evaluation_reference_cohorts": 16,
        "repeat_fits": 393216,
        "local_records": 9408,
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
    }
    write(output / "plan.json", plan)
    records, began = [], time.monotonic()
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
        try:
            if index == 32:
                close_envelope(output, records)
            elif index == 48:
                close_references(output, records[32:48])
        except (ValueError, KeyError, OSError, TypeError) as exc:
            records.extend(
                {
                    "index": i,
                    "case": c,
                    "status": "not_run",
                    "reason": "incomplete-calibration-bank",
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
            "envelope_file_sha256": sha(output / "envelope-bank.json")
            if index >= 32
            else None,
            "bank_file_sha256": sha(output / "reference-bank.json")
            if index >= 48
            else None,
        }
        write(output / f"unit-{index:03d}.attempt.json", record)
        started = time.monotonic()
        with (
            (output / f"unit-{index:03d}.stdout").open("x") as stdout,
            (output / f"unit-{index:03d}.stderr").open("x") as stderr,
        ):
            try:
                execution = subprocess.run(
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
                    status="completed" if execution.returncode == 0 else "failed",
                    returncode=execution.returncode,
                )
            except subprocess.TimeoutExpired:
                record.update(status="timeout", reason="bounded-unit-deadline")
            except OSError as exc:
                record.update(
                    status="failed", reason="child-launch-error", error=str(exc)
                )
        if record["status"] == "completed":
            try:
                report = validate_output(unit, case, output)
                assert_source(plan)
                if report["source_sha256"] != lock or any(
                    report[k] != record[k]
                    for k in ("plan_sha256", "envelope_file_sha256", "bank_file_sha256")
                ):
                    raise ValueError("unit launch/source binding changed")
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
            "scientific_authority": False,
            "envelope_file_sha256": sha(output / "envelope-bank.json")
            if (output / "envelope-bank.json").exists()
            else None,
            "bank_file_sha256": sha(output / "reference-bank.json")
            if (output / "reference-bank.json").exists()
            else None,
        },
    )
    return (
        len(records) == 144
        and all(r["status"] == "completed" for r in records)
        and source_lock() == lock
    )


def verify(output):
    plan = json.loads((output / "plan.json").read_text())
    manifest = json.loads((output / "manifest.json").read_text())
    assert_source(plan)
    if (
        manifest["plan_sha256"] != sha(output / "plan.json")
        or [r["index"] for r in manifest["units"]] != list(range(144))
        or [r["case"] for r in manifest["units"]] != cases()
        or manifest["source_unchanged"] is not True
        or manifest["scientific_authority"] is not False
    ):
        raise ValueError("campaign denominator/source/plan changed")
    for name, key in (
        ("envelope-bank.json", "envelope_file_sha256"),
        ("reference-bank.json", "bank_file_sha256"),
    ):
        expected = sha(output / name) if (output / name).exists() else None
        if manifest[key] != expected:
            raise ValueError("campaign bank binding changed")
    if (output / "envelope-bank.json").exists():
        load_envelope(output)
    if (output / "reference-bank.json").exists():
        load_references(output)
    completed, fits, local = 0, 0, 0
    for record in manifest["units"]:
        if record["status"] != "completed":
            continue
        report = read_unit(output, record, arrays=True)
        if (
            json.loads(
                (output / f"unit-{record['index']:03d}.terminal.json").read_text()
            )
            != record
        ):
            raise ValueError("terminal differs from manifest")
        attempt = json.loads(
            (output / f"unit-{record['index']:03d}.attempt.json").read_text()
        )
        if attempt["status"] != "running" or any(
            attempt[k] != record[k] for k in attempt if k != "status"
        ):
            raise ValueError("attempt differs from terminal")
        checked = validate_output(output / record["directory"], record["case"], output)
        if (
            checked != report
            or report["source_sha256"] != plan["source_sha256"]
            or any(
                report[k] != record[k]
                for k in ("plan_sha256", "envelope_file_sha256", "bank_file_sha256")
            )
        ):
            raise ValueError("verified report differs from launch")
        fits += 8192 if record["case"]["lane"] != "geometry" else 0
        local += len(report["records"]) if record["case"]["lane"] == "geometry" else 0
        completed += 1
    assert_source(plan)
    return {
        "manifest_sha256": sha(output / "manifest.json"),
        "plan_sha256": sha(output / "plan.json"),
        "envelope_file_sha256": manifest["envelope_file_sha256"],
        "bank_file_sha256": manifest["bank_file_sha256"],
        "completed_units": completed,
        "planned_units": 144,
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
        if not 0 <= args.child < 144 or args.launch is None:
            parser.error("registered child/launch required")
        child(args.child, args.output, args.launch)
    elif args.verify:
        receipt = verify(args.output)
        write(args.output / "verification.json", receipt)
        print(json.dumps(receipt))
    elif not run(args.output):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
