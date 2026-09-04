"""Bounded 99-unit Furnace campaign for the committed one-arm zoom plan."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

import numpy as np

import prototype_p4_one_arm_zoom_v0_1 as kernel
import run_p4_signal_strength_v0_1 as previous

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "docs/P4_ONE_ARM_ZOOM_PLAN.md"
PROTOCOL_SHA256 = "c26b3b6020d8a31e4d0568c61028a5805671924f732523c3ea5b7dd74309b8ba"
INPUT_MANIFEST_SHA256 = (
    "f0b5bc294ef7c18ca1ff2bbab99c9fe7aa9d3dabfa029aee11850718147357a7"
)
CASE_SECONDS, TOTAL_SECONDS = 180, 900
AS_BYTES, DISK_BYTES = 8 * 2**30, 4 * 2**30
sha, write = previous.sha, previous.write
limits = kernel.strength.clone(
    previous.limits, CASE_SECONDS=CASE_SECONDS, AS_BYTES=AS_BYTES
)


def source_lock():
    paths = sorted((ROOT / "src").rglob("*.py"))
    paths += sorted((ROOT / "scripts").glob("*p4*.py"))
    paths += [ROOT / PROTOCOL, ROOT / "tests/test_p4_one_arm_zoom_v0_1.py"]
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}


def validate_unit(directory, spec):
    report, compact = kernel.strength.clone(previous.validate_unit, kernel=kernel)(
        directory, spec
    )
    with np.load(directory / "arrays.npz", allow_pickle=False) as arrays:
        if kernel.located_diagnostics(report, arrays) != report["zoom"]:
            raise ValueError("located diagnostics do not replay from sealed arrays")
    return report, compact


def predecessor_anchors(directory):
    if sha(directory / "manifest.json") != INPUT_MANIFEST_SHA256:
        raise ValueError("predecessor manifest changed")
    manifest = json.loads((directory / "manifest.json").read_text())
    result = {}
    for w, window in enumerate(kernel.WINDOWS):
        for position, old_index in zip((0, 16, 32), window[7], strict=True):
            record = manifest["units"][old_index]
            path = directory / record["directory"] / "report.json"
            if sha(path) != record["report_sha256"]:
                raise ValueError("predecessor anchor report changed")
            report = json.loads(path.read_text())
            if report["spec"] != asdict(kernel.case_specs()[w * 33 + position]):
                raise ValueError("predecessor anchor spec changed")
            result[w * 33 + position] = (record, report)
    return result


def anchor_replay(report, old):
    keys = ("input_sha256", "noise_receipt", "paired_cells", "array_layout", "heldout")
    if any(report[k] != old[k] for k in keys):
        raise ValueError("old-anchor observations or readouts changed")
    for arm in ("A", "B"):
        if report["arms"][arm]["rows"] != old["arms"][arm]["rows"]:
            raise ValueError("old-anchor baseline or field seals changed")
    return True


def cross_sections(records, output):
    if len(records) != 99 or [r["spec"] for r in records] != [
        asdict(s) for s in kernel.case_specs()
    ]:
        raise ValueError("exact 99-unit sequence required")
    units = []
    for r in records:
        unit = {k: r[k] for k in ("index", "spec", "status")}
        unit["outer"] = None
        if r["status"] == "completed":
            path = output / r["directory"] / "compact.json"
            if sha(path) != r["compact_sha256"]:
                raise ValueError("compact bytes changed after receipt")
            compact = json.loads(path.read_text())
            unit.update(
                outer=compact["loops"]["outer_forward"],
                cells=[
                    {
                        **{k: c[k] for k in ("field_graph", "loop_graph")},
                        "hypotheses": c["loops"]["outer_forward"],
                    }
                    for c in compact["zoom"]["cells"]
                ],
                sampling_controls=compact["zoom"]["sampling_controls"],
                noise_receipt=compact["noise_receipt"],
                compact_sha256=r["compact_sha256"],
            )
        else:
            unit["reason"] = r.get("reason", r["status"])
        units.append(unit)
    windows = []
    for w, window in enumerate(kernel.WINDOWS):
        group = units[w * 33 : (w + 1) * 33]
        traces = {}
        for f in kernel.perturbation.FAMILIES:
            for g in kernel.perturbation.FAMILIES:
                for h in ("F2", "F4"):
                    labels = []
                    for u in group:
                        if u["status"] != "completed":
                            labels.append("unavailable")
                        else:
                            c = next(
                                c
                                for c in u["cells"]
                                if (c["field_graph"], c["loop_graph"]) == (f, g)
                            )
                            labels.append(c["hypotheses"][h]["category"])
                    traces[f + "/" + g + "/" + h] = kernel.sampled_runs(
                        kernel.grid(window), labels
                    )
        windows.append(
            {
                "name": window[0],
                "selected_hypothesis": window[6],
                "strengths": kernel.grid(window),
                "unit_indices": [u["index"] for u in group],
                "runs_by_cell_hypothesis": traces,
            }
        )
    return {
        "schema_version": kernel.SCHEMA + ".cross-sections",
        "units": units,
        "windows": windows,
        "protocol_sha256": PROTOCOL_SHA256,
        "paired_units": 99,
        "loop_hypothesis_records_planned": 17820,
        "derived_estimator_checks_planned": 3564,
        "correlated_targeted_followup": True,
        "scientific_authority": False,
    }


def run_child(index, output):
    specs = kernel.case_specs()
    if not 0 <= index < len(specs):
        raise ValueError("child index outside registered panel")
    report, _ = kernel.measure_pair(specs[index], output)
    write(output / "compact.json", kernel.compact_report(report))


def run(output, predecessor):
    if platform.system() != "Linux" or sha(ROOT / PROTOCOL) != PROTOCOL_SHA256:
        raise ValueError("Linux and unchanged registered protocol required")
    output, predecessor = output.resolve(), predecessor.resolve()
    if (
        output == predecessor
        or output in predecessor.parents
        or predecessor in output.parents
    ):
        raise ValueError("output must be disjoint from predecessor")
    anchors = predecessor_anchors(predecessor)
    specs, lock = kernel.case_specs(), source_lock()
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    output.mkdir(parents=True, exist_ok=False)
    write(
        output / "plan.json",
        {
            "schema_version": kernel.SCHEMA + ".campaign",
            "protocol": PROTOCOL,
            "protocol_sha256": PROTOCOL_SHA256,
            "source_sha256": lock,
            "checkout_revision": revision,
            "predecessor": str(predecessor),
            "predecessor_manifest_sha256": INPUT_MANIFEST_SHA256,
            "paired_units": 99,
            "arm_measurements": 198,
            "loop_hypothesis_records": 17820,
            "derived_estimator_checks": 3564,
            "cases": [asdict(s) for s in specs],
            "noise_protocol": kernel.NOISE_PROTOCOL,
            "reference_backend": "numpy",
            "gpu_used": False,
            "model_accessed": False,
            "resource_limits": {
                "case_seconds": CASE_SECONDS,
                "campaign_seconds": TOTAL_SECONDS,
                "address_space_bytes": AS_BYTES,
                "max_file_bytes": 2 * 2**30,
                "pre_unit_disk_admission_bytes": DISK_BYTES,
                "concurrent_children": 1,
                "blas_threads": 1,
            },
            "scientific_authority": False,
        },
    )
    plan_hash = sha(output / "plan.json")
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
    started, records, noise_hashes = time.monotonic(), [], {}
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
        directory = output / f"unit-{index:03d}"
        record = {
            "index": index,
            "spec": asdict(spec),
            "status": "running",
            "directory": directory.name,
            "plan_sha256": plan_hash,
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
        record["seconds"] = time.monotonic() - began
        if record["status"] == "completed":
            try:
                report, _ = validate_unit(directory, spec)
                hashes = report["noise_receipt"]["standard_normal_stream_sha256"]
                if hashes != noise_hashes.setdefault(spec.seed, hashes):
                    raise ValueError("raw noise changed within strength trace")
                if source_lock() != lock:
                    raise ValueError("source changed during child")
                if index in anchors:
                    old_record, old_report = anchors[index]
                    anchor_replay(report, old_report)
                    record["anchor_replay"] = {
                        "exact": True,
                        "old_index": old_record["index"],
                        "old_report_sha256": old_record["report_sha256"],
                    }
                record.update(
                    report_sha256=sha(directory / "report.json"),
                    compact_sha256=sha(directory / "compact.json"),
                    array_artifact=report["array_artifact"],
                    peak_rss_bytes=report["peak_rss_bytes"],
                )
            except (OSError, ValueError, KeyError, TypeError) as exc:
                record.update(
                    status="failed", reason="result-validation", error=str(exc)
                )
        write(output / f"unit-{index:03d}.terminal.json", record)
        records.append(record)
        print(json.dumps(record, allow_nan=False), flush=True)
    write(output / "cross_sections.json", cross_sections(records, output))
    manifest = {
        "plan_sha256": plan_hash,
        "protocol_sha256": PROTOCOL_SHA256,
        "cross_sections_sha256": sha(output / "cross_sections.json"),
        "host": platform.node(),
        "python": platform.python_version(),
        "paired_units": 99,
        "completed": sum(r["status"] == "completed" for r in records),
        "units": records,
        "elapsed_seconds": time.monotonic() - started,
        "disk_bytes": sum(p.stat().st_size for p in output.rglob("*") if p.is_file()),
        "final_source_lock_matches": source_lock() == lock,
        "scientific_authority": False,
        "model_accessed": False,
        "gpu_used": False,
    }
    write(output / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--predecessor", type=Path)
    parser.add_argument("--child", type=int)
    args = parser.parse_args()
    if args.child is not None:
        run_child(args.child, args.output)
        return 0
    if args.predecessor is None:
        parser.error("--predecessor is required for the campaign")
    result = run(args.output, args.predecessor)
    print(json.dumps({k: v for k, v in result.items() if k != "units"}), flush=True)
    return int(result["completed"] != 99)


if __name__ == "__main__":
    raise SystemExit(main())
