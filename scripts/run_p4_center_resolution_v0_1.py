"""Bounded188-position expanded resolution campaign with immutable inherited radii."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import resource
import shutil
import subprocess
import sys
import time

import numpy as np

import prototype_p4_center_resolution_v0_1 as kernel
import run_p4_center_identifiability_v0_1 as previous

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "docs/P4_CENTER_RESOLUTION_PLAN.md"
PROTOCOL_SHA256 = "ac6975ab41369d316797a29c49769f5c1cbf051d4c0f706dd2acb49d7a6e7309"
CASE_SECONDS, TOTAL_SECONDS = 180, 3600
AS_BYTES, DISK_BYTES, FREE_BYTES = 8 * 2**30, 12 * 2**30, 16 * 2**30
sha, write, read_unit = previous.sha, previous.write, previous.read_unit
limits = kernel.spatial.zoom.strength.clone(
    previous.previous.limits, CASE_SECONDS=CASE_SECONDS, AS_BYTES=AS_BYTES
)


def cases():
    return (
        [
            {"lane": "evaluation_reference", "reference_seed": s}
            for s in kernel.REFERENCE_SEEDS
        ]
        + [
            {"lane": "primary", "alpha": a, "geometry_seed": s}
            for a in kernel.ALPHAS
            for s in kernel.GEOMETRY_SEEDS
        ]
        + [
            {"lane": "stress", "stress": m, "alpha": 0.10, "geometry_seed": s}
            for m in kernel.STRESSES
            for s in kernel.GEOMETRY_SEEDS[:4]
        ]
        + [
            {"lane": "local", "alpha": a, "geometry_seed": s, "fixture": f}
            for a in kernel.ALPHAS
            for s in kernel.GEOMETRY_SEEDS[:4]
            for f in kernel.LOCAL_FIXTURES
        ]
    )


def record_count(case):
    return {"evaluation_reference": 0, "primary": 10808, "stress": 896, "local": 26}[
        case["lane"]
    ]


def source_lock():
    paths = sorted((ROOT / "src").rglob("*.py")) + sorted(
        (ROOT / "scripts").glob("*p4*.py")
    )
    paths += [
        ROOT / PROTOCOL,
        ROOT / kernel.ENVELOPE_FILE,
        ROOT / "tests/test_p4_center_resolution_v0_1.py",
    ]
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}


def assert_source(plan):
    if (
        source_lock() != plan["source_sha256"]
        or plan["protocol_sha256"] != PROTOCOL_SHA256
        or sha(ROOT / PROTOCOL) != PROTOCOL_SHA256
        or plan["cases"] != cases()
        or plan["inherited_envelope_sha256"] != kernel.ENVELOPE_SHA
    ):
        raise ValueError("registered source/protocol/envelope/cases changed")
    kernel.inherited_envelope(ROOT)


def select_references(bank, case):
    refs = bank["references"]
    if case["lane"] == "stress":
        return [r for r in refs if r["k"] == 4096]
    if case["lane"] == "local":
        return [r for r in refs if r["reference_seed"] in kernel.REFERENCE_SEEDS[:4]]
    return refs


def reference_reports(directory, entries):
    if [r["index"] for r in entries] != list(range(64)):
        raise ValueError("complete ordered64 reference positions required")
    plan = json.loads((directory / "plan.json").read_text())
    reports = []
    for record in entries:
        report = read_unit(directory, record)
        if (
            report["case"] != cases()[record["index"]]
            or report["source_sha256"] != plan["source_sha256"]
            or report["plan_sha256"] != sha(directory / "plan.json")
            or report["inherited_envelope_sha256"] != kernel.ENVELOPE_SHA
            or report["bank_file_sha256"] is not None
            or report["repeats"] != 4096
            or report["ks"] != list(kernel.KS)
            or report["lane"] != "evaluation_reference"
            or report["schema_version"] != kernel.base.SCHEMA
            or report["scientific_authority"] is not False
        ):
            raise ValueError("reference launch/source/prefix/chronology changed")
        reports.append(report)
    return reports


def close_references(directory, entries):
    reports = reference_reports(directory, entries)
    envelope = kernel.inherited_envelope(ROOT)
    body = {
        "schema_version": kernel.SCHEMA + ".reference-bank",
        "reference_units": entries,
        "references": [r for u in reports for r in u["references"]],
        "inherited_envelope_sha256": kernel.ENVELOPE_SHA,
        "envelope_seal_sha256": envelope["envelope_seal_sha256"],
        "plan_sha256": sha(directory / "plan.json"),
        "geometry_observed": False,
        "scientific_authority": False,
    }
    write(
        directory / "reference-bank.json",
        {**body, "file_seal_sha256": kernel.SEAL(body)},
    )
    return load_references(directory)


def load_references(directory):
    envelope = kernel.inherited_envelope(ROOT)
    bank = json.loads((directory / "reference-bank.json").read_text())
    body = {k: v for k, v in bank.items() if k != "file_seal_sha256"}
    if (
        kernel.SEAL(body) != bank["file_seal_sha256"]
        or bank["schema_version"] != kernel.SCHEMA + ".reference-bank"
        or bank["inherited_envelope_sha256"] != kernel.ENVELOPE_SHA
        or bank["envelope_seal_sha256"] != envelope["envelope_seal_sha256"]
        or bank["plan_sha256"] != sha(directory / "plan.json")
        or bank["geometry_observed"] is not False
        or bank["scientific_authority"] is not False
    ):
        raise ValueError("sealed reference bank scope/source changed")
    reports = reference_reports(directory, bank["reference_units"])
    refs = [r for u in reports for r in u["references"]]
    expected = [
        (s, k, h)
        for s in kernel.REFERENCE_SEEDS
        for k in kernel.KS
        for h in kernel.spatial.HYPOTHESES
    ]
    if (
        refs != bank["references"]
        or [(r["reference_seed"], r["k"], r["hypothesis"]) for r in refs] != expected
    ):
        raise ValueError("reference bank denominator/order changed")
    for r in refs:
        kernel.base.validate_reference(r)
        if r["role"] != "evaluation_reference":
            raise ValueError("reference role changed")
    return bank, envelope


def child(index, output, launch):
    plan = json.loads(launch.read_text())
    assert_source(plan)
    case, began = cases()[index], time.monotonic()
    bank_hash = None
    if case["lane"] == "evaluation_reference":
        report, arrays = kernel.base.calibrate(
            case["reference_seed"], "evaluation_reference"
        )
        kernel.base.verify_calibration(report, arrays)
    else:
        bank, envelope = load_references(launch.parent)
        bank_hash = sha(launch.parent / "reference-bank.json")
        refs = select_references(bank, case)
        report, arrays = kernel.field_unit(
            refs, envelope, bank["file_seal_sha256"], **case
        )
        kernel.verify_field(
            report, arrays, refs, envelope, bank["file_seal_sha256"], case
        )
        if (
            load_references(launch.parent) != (bank, envelope)
            or sha(launch.parent / "reference-bank.json") != bank_hash
        ):
            raise ValueError("bank changed during consumption")
    assert_source(plan)
    output.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(output / "arrays.npz", **arrays)
    report.update(
        case=case,
        source_sha256=plan["source_sha256"],
        plan_sha256=sha(launch),
        inherited_envelope_sha256=kernel.ENVELOPE_SHA,
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
        or report["scientific_authority"] is not False
        or report["inherited_envelope_sha256"] != kernel.ENVELOPE_SHA
    ):
        raise ValueError("returned condition/claim/envelope changed")
    artifact = report["array_artifact"]
    if (
        artifact["file"] != "arrays.npz"
        or sha(unit / "arrays.npz") != artifact["sha256"]
        or (unit / "arrays.npz").stat().st_size != artifact["bytes"]
    ):
        raise ValueError("raw array artifact changed")
    with np.load(unit / "arrays.npz", allow_pickle=False) as arrays:
        if case["lane"] == "evaluation_reference":
            if (
                report["repeats"] != 4096
                or report["ks"] != list(kernel.KS)
                or report["bank_file_sha256"] is not None
            ):
                raise ValueError("reference repeat/bank chronology changed")
            kernel.base.verify_calibration(report, arrays)
        else:
            bank, envelope = load_references(directory)
            if report["bank_file_sha256"] != sha(
                directory / "reference-bank.json"
            ) or len(report["records"]) != record_count(case):
                raise ValueError("field bank/record denominator changed")
            kernel.verify_field(
                report,
                arrays,
                select_references(bank, case),
                envelope,
                bank["file_seal_sha256"],
                case,
            )
    return report


def run(output):
    if platform.system() != "Linux" or sha(ROOT / PROTOCOL) != PROTOCOL_SHA256:
        raise ValueError("registered protocol and Linux execution required")
    if subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True
    ).strip():
        raise ValueError("clean committed source required")
    kernel.inherited_envelope(ROOT)
    lock = source_lock()
    output.mkdir(parents=True, exist_ok=False)
    plan = {
        "schema_version": kernel.SCHEMA + ".campaign",
        "protocol_sha256": PROTOCOL_SHA256,
        "checkout_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "source_sha256": lock,
        "inherited_envelope_sha256": kernel.ENVELOPE_SHA,
        "cases": cases(),
        "planned_units": 188,
        "reference_cohorts": 64,
        "repeat_fits": 524288,
        "primary_records": 345856,
        "stress_records": 25088,
        "paired_local_records": 1664,
        "scientific_authority": False,
        "resource_limits": {
            "case_seconds": CASE_SECONDS,
            "campaign_seconds": TOTAL_SECONDS,
            "address_space_bytes": AS_BYTES,
            "output_disk_bytes": DISK_BYTES,
            "minimum_free_disk_bytes": FREE_BYTES,
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
            else "output-disk-budget"
            if used >= DISK_BYTES
            else "insufficient-free-disk"
            if shutil.disk_usage(output).free < FREE_BYTES
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
        if index == 64:
            try:
                close_references(output, records)
            except (ValueError, OSError, KeyError, TypeError) as exc:
                records.extend(
                    {
                        "index": i,
                        "case": c,
                        "status": "not_run",
                        "reason": "incomplete-reference-bank",
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
            "inherited_envelope_sha256": kernel.ENVELOPE_SHA,
            "bank_file_sha256": sha(output / "reference-bank.json")
            if index >= 64
            else None,
        }
        write(output / f"unit-{index:03d}.attempt.json", record)
        started = time.monotonic()
        with (
            (output / f"unit-{index:03d}.stdout").open("x") as stdout,
            (output / f"unit-{index:03d}.stderr").open("x") as stderr,
        ):
            try:
                executed = subprocess.run(
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
                    status="completed" if executed.returncode == 0 else "failed",
                    returncode=executed.returncode,
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
                    for k in (
                        "plan_sha256",
                        "inherited_envelope_sha256",
                        "bank_file_sha256",
                    )
                ):
                    raise ValueError("launch/source binding changed")
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
            "inherited_envelope_sha256": kernel.ENVELOPE_SHA,
            "bank_file_sha256": sha(output / "reference-bank.json")
            if (output / "reference-bank.json").exists()
            else None,
        },
    )
    return (
        len(records) == 188
        and all(r["status"] == "completed" for r in records)
        and source_lock() == lock
    )


def verify(output):
    plan = json.loads((output / "plan.json").read_text())
    manifest = json.loads((output / "manifest.json").read_text())
    assert_source(plan)
    if (
        manifest["plan_sha256"] != sha(output / "plan.json")
        or [r["index"] for r in manifest["units"]] != list(range(188))
        or [r["case"] for r in manifest["units"]] != cases()
        or manifest["source_unchanged"] is not True
        or manifest["scientific_authority"] is not False
        or manifest["inherited_envelope_sha256"] != kernel.ENVELOPE_SHA
    ):
        raise ValueError("manifest/source/scope changed")
    expected_bank = (
        sha(output / "reference-bank.json")
        if (output / "reference-bank.json").exists()
        else None
    )
    if manifest["bank_file_sha256"] != expected_bank:
        raise ValueError("manifest bank binding changed")
    if expected_bank:
        load_references(output)
    completed, fits = 0, 0
    counts = {"primary": 0, "stress": 0, "local": 0}
    for entry in manifest["units"]:
        if entry["status"] != "completed":
            continue
        report = read_unit(output, entry, arrays=True)
        if (
            json.loads(
                (output / f"unit-{entry['index']:03d}.terminal.json").read_text()
            )
            != entry
        ):
            raise ValueError("terminal/manifest mismatch")
        attempt = json.loads(
            (output / f"unit-{entry['index']:03d}.attempt.json").read_text()
        )
        if attempt["status"] != "running" or any(
            attempt[k] != entry[k] for k in attempt if k != "status"
        ):
            raise ValueError("attempt/terminal mismatch")
        if (
            validate_output(output / entry["directory"], entry["case"], output)
            != report
            or report["source_sha256"] != plan["source_sha256"]
        ):
            raise ValueError("raw report/source replay mismatch")
        if any(
            report[k] != entry[k]
            for k in ("plan_sha256", "inherited_envelope_sha256", "bank_file_sha256")
        ):
            raise ValueError("replayed launch join changed")
        completed += 1
        if entry["case"]["lane"] == "evaluation_reference":
            fits += 8192
        else:
            counts[entry["case"]["lane"]] += len(report["records"])
    assert_source(plan)
    return {
        "manifest_sha256": sha(output / "manifest.json"),
        "plan_sha256": sha(output / "plan.json"),
        "bank_file_sha256": expected_bank,
        "inherited_envelope_sha256": kernel.ENVELOPE_SHA,
        "completed_units": completed,
        "planned_units": 188,
        "replayed_repeat_fits": fits,
        "replayed_records": counts,
        "output_hashes_checked": completed * 2,
        "source_hashes_checked": len(plan["source_sha256"]),
        "scientific_authority": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--child", type=int)
    p.add_argument("--launch", type=Path)
    p.add_argument("--verify", action="store_true")
    args = p.parse_args()
    if args.child is not None:
        if not 0 <= args.child < 188 or args.launch is None:
            p.error("registered child and launch required")
        child(args.child, args.output, args.launch)
    elif args.verify:
        receipt = verify(args.output)
        write(args.output / "verification.json", receipt)
        print(json.dumps(receipt))
    elif not run(args.output):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
