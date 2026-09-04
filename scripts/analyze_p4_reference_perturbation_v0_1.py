"""Read-only, fixed-panel reanalysis of retained reference A/B residuals.

No fits, observations, winding readouts, or admission rules are changed.
The input panel was already observed; this is exploratory, not confirmation.
"""

from __future__ import annotations

import argparse
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

from p4_reference_perturbation_diagnostics_v0_1 import point_diagnostics

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "spirallens.p4-reference-perturbation.v0.1"
INPUT_SCHEMA = "spirallens.p4-independent-reference-validation.v0.1"
PROTOCOL = "docs/P4_REFERENCE_PERTURBATION_PLAN.md"
PROTOCOL_SHA256 = "53fbfd1409d03de7fb6c8ee44361213a8b1574920ca2d8b89120b289fb37c202"
INPUT_MANIFEST_SHA256 = (
    "a6268fa2cd5f7f0644fc7412c8c907afeb2d8d0f3f5763b7d3827d944300e857"
)
INPUT_PLAN_SHA256 = "b67fc15fe22e57410fe65e47980abd117a1b33d07a16b63b9bda532a7f779c3d"
INPUT_COMMIT = "465238be0fe9b63bbe83fbd40408b2484d7d75e8"
FAMILIES = ("mutual-knn", "fixed-radius", "shared-neighbor")
LOOPS = ("inner", "local_negative", "local_positive", "offcore", "outer")
ORIENTED_LOOPS = tuple(
    f"{name}_{direction}" for name in LOOPS for direction in ("forward", "reverse")
)
HYPOTHESES = ("F2", "F4")
CASE_SECONDS, TOTAL_SECONDS = 120, 900
AS_BYTES, FILE_BYTES, DISK_BYTES = 4 * 2**30, 256 * 2**20, 2**30


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def array_hash(value):
    array = np.ascontiguousarray(value, dtype="<f8")
    return hashlib.sha256(
        str(array.shape).encode("ascii") + b"\0" + array.tobytes()
    ).hexdigest()


def field_seal(record):
    # Exact predecessor pre-core field identity; core/amplitude summaries were
    # attached after this seal and are not part of its canonical JSON payload.
    keys = (
        "values_sha256",
        "support_sha256",
        "estimand",
        "hypothesis",
        "baseline_sha256",
        "domain_sha256",
        "frames_sha256",
        "graph_sha256",
        "evaluation_probe_sha256",
        "missing",
    )
    encoded = json.dumps(
        {key: record[key] for key in keys},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def write(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def disjoint_output(input_dir, output_dir):
    input_dir, output_dir = Path(input_dir).resolve(), Path(output_dir).resolve()
    _require(
        output_dir != input_dir
        and input_dir not in output_dir.parents
        and output_dir not in input_dir.parents,
        "analysis output must be disjoint from input campaign",
    )
    if output_dir.exists():
        raise FileExistsError(output_dir)
    return input_dir, output_dir


def _category(a, b):
    if a["state"] == b["state"] == "eligible":
        same = a["value"]["sampled_winding"] == b["value"]["sampled_winding"]
        return "both_admitted_equal" if same else "both_admitted_different"
    if a["state"] == "eligible":
        return "A_only_admitted"
    if b["state"] == "eligible":
        return "B_only_admitted"
    return "neither_admitted"


def analyze_pair(report, arrays):
    """Analyze validated retained field arrays, never modifying their inputs.

    ``arrays`` may be a mapping or a lazy NpzFile; large raw probe entries
    are never requested. Campaign IO separately verifies whole-file hashes.
    """
    _require(report["schema_version"] == INPUT_SCHEMA, "unexpected input schema")
    _require(set(report["arms"]) == {"A", "B"}, "exactly two original arms required")
    n = report["vertex_count"]
    _require(type(n) is int and n > 0, "positive vertex count required")
    arms = report["arms"]
    layout = report["array_layout"]["arms"]
    cache = {}

    def get(arm, key):
        stored = layout[arm][key]
        if stored not in cache:
            cache[stored] = np.asarray(arrays[stored])
        value = cache[stored]
        _require(
            value.dtype.kind in "bifu" and np.isfinite(value).all(),
            "nonfinite or nonnumeric retained array",
        )
        return value

    paths = arms["A"]["loop_vertices"]
    _require(paths == arms["B"]["loop_vertices"], "paired loop paths changed")
    _require(set(paths) == set(LOOPS), "all five original loops required")
    vertices = {}
    for name in LOOPS:
        raw = paths[name]
        _require(
            isinstance(raw, list)
            and len(raw) >= 3
            and all(type(i) is int and 0 <= i < n for i in raw),
            "invalid fixed loop vertices",
        )
        _require(len(set(raw)) == len(raw), "loop repeats a vertex")
        path = np.asarray(raw, dtype=np.int64)
        vertices[name + "_forward"] = path
        vertices[name + "_reverse"] = np.r_[path[:1], path[:0:-1]]
    expected_cells = {(f, g) for f in FAMILIES for g in FAMILIES}
    cell_maps = {}
    for arm in ("A", "B"):
        _require(
            arms[arm]["vertex_count"] == n and arms[arm]["spec"] == report["spec"],
            "arm spec/domain mismatch",
        )
        entries = arms[arm]["cells"]
        cell_maps[arm] = {(c["field_graph"], c["loop_graph"]): c for c in entries}
        _require(
            len(entries) == 9 and set(cell_maps[arm]) == expected_cells,
            "all nine distinct cells required",
        )
        _require(
            all(set(c["loops"]) == set(ORIENTED_LOOPS) for c in entries),
            "all ten oriented readouts required",
        )

    diagnostics, receipts = {}, {}
    for family in FAMILIES:
        support = get("A", family + "_support")
        _require(
            support.shape == (n,) and support.dtype.kind == "b",
            "boolean support required",
        )
        _require(
            np.array_equal(support, get("B", family + "_support")),
            "paired support changed",
        )
        frames = get("A", family + "_frames")
        _require(frames.shape == (n, 3, 2), "unexpected frame shape")
        _require(
            np.array_equal(frames, get("B", family + "_frames")),
            "paired frames changed",
        )
        receipts[family] = {
            "frames_sha256": array_hash(frames),
            "support_sha256": array_hash(support),
        }
        diagnostics[family] = {}
        for h in HYPOTHESES:
            fields = {}
            missing = False
            field_receipts = {}
            for arm in ("A", "B"):
                fields[arm] = {}
                field_receipts[arm] = {}
                for estimand in ("full", "local_affine", "residual_affine"):
                    record = arms[arm]["rows"][family]["fields"][estimand][h]
                    _require(
                        field_seal(record) == record["field_sha256"],
                        "retained field seal mismatch",
                    )
                    field_receipts[arm][estimand] = record["field_sha256"]
                    _require(
                        record["frames_sha256"] == array_hash(frames),
                        "retained frame hash mismatch",
                    )
                    if record["missing"]:
                        missing = True
                        continue
                    value = get(arm, f"{family}_{estimand}_{h}_values")
                    _require(
                        value.shape == (n, 2), "expected N by 2 coefficient values"
                    )
                    _require(
                        array_hash(value) == record["values_sha256"],
                        "retained field values hash mismatch",
                    )
                    _require(
                        array_hash(support) == record["support_sha256"],
                        "retained support hash mismatch",
                    )
                    fields[arm][estimand] = value
            receipts[family][h] = field_receipts
            if missing:
                diagnostics[family][h] = {
                    name: {
                        "state": "insufficient",
                        "reason": "one-or-both-retained-fields-unavailable",
                        "required_vertex_count": len(v),
                        "measurement": None,
                    }
                    for name, v in vertices.items()
                }
                continue
            _require(
                np.array_equal(fields["A"]["full"], fields["B"]["full"]),
                "paired clean full fields changed",
            )
            for arm in ("A", "B"):
                _require(
                    np.array_equal(
                        fields[arm]["residual_affine"],
                        fields[arm]["full"] - fields[arm]["local_affine"],
                    ),
                    "retained residual does not equal full minus affine",
                )
            a, b = fields["A"]["residual_affine"], fields["B"]["residual_affine"]
            delta_baseline = fields["B"]["local_affine"] - fields["A"]["local_affine"]
            identity_error = float(np.max(np.abs((b - a) + delta_baseline)))
            diagnostics[family][h] = {}
            for name, v in vertices.items():
                mask = support[v]
                diagnostics[family][h][name] = {
                    "state": "complete"
                    if mask.all()
                    else "incomplete"
                    if mask.any()
                    else "insufficient",
                    "reason": None if mask.any() else "no-supported-points",
                    "scope": "same-frame-sampled-point-diagnostic-not-loop-admission",
                    "coefficient_angle_convention": "vector"
                    if h == "F2"
                    else "spin-two-not-physical-director",
                    "vertices": v.tolist(),
                    "vertices_sha256": array_hash(v),
                    "maximum_subtraction_identity_error": identity_error,
                    "measurement": point_diagnostics(
                        a[v], b[v], mask, amplitude_floor=1e-6
                    ),
                }
    cells = []
    for f in FAMILIES:
        for g in FAMILIES:
            cell = {"field_graph": f, "loop_graph": g, "loops": {}}
            for loop in ORIENTED_LOOPS:
                cell["loops"][loop] = {}
                for h in HYPOTHESES:
                    endpoints = {
                        arm: cell_maps[arm][f, g]["loops"][loop]["fields"][
                            "residual_affine"
                        ][h]
                        for arm in ("A", "B")
                    }
                    covered = all(
                        e["reason"] != "cycle-boundary-not-coverable"
                        for e in endpoints.values()
                    )
                    diagnostic = diagnostics[f][h][loop]
                    available = covered and diagnostic["measurement"] is not None
                    cell["loops"][loop][h] = {
                        "endpoints": endpoints,
                        "paired_category": _category(endpoints["A"], endpoints["B"]),
                        "state": diagnostic["state"] if available else "insufficient",
                        "reason": diagnostic.get("reason")
                        if available
                        else "cycle-boundary-not-coverable"
                        if not covered
                        else "one-or-both-retained-fields-unavailable",
                        "diagnostic_ref": [f, h, loop] if available else None,
                    }
            cells.append(cell)
    return {
        "schema_version": SCHEMA,
        "spec": report["spec"],
        "vertex_count": n,
        "loop_hypothesis_records": 180,
        "cells": cells,
        "diagnostics": diagnostics,
        "input_field_receipts": receipts,
        "original_outer_summary": report["summary"],
        "scope": {
            "exploratory_reanalysis": True,
            "new_observations": 0,
            "new_fits": 0,
            "new_winding_readouts": 0,
            "reference_selected": False,
            "scientific_authority": False,
            "model_accessed": False,
            "gpu_used": False,
            "claim_ceiling": "level_0",
            "continuous_path_clearance_verified": False,
        },
    }


def load_campaign(input_dir):
    _require(
        sha(input_dir / "manifest.json") == INPUT_MANIFEST_SHA256,
        "input manifest hash mismatch",
    )
    _require(
        sha(input_dir / "plan.json") == INPUT_PLAN_SHA256, "input plan hash mismatch"
    )
    manifest = json.loads((input_dir / "manifest.json").read_text())
    plan = json.loads((input_dir / "plan.json").read_text())
    _require(
        plan["checkout_revision"] == INPUT_COMMIT
        and manifest["plan_sha256"] == INPUT_PLAN_SHA256,
        "input chronology mismatch",
    )
    _require(
        len(plan["cases"]) == len(manifest["units"]) == 32,
        "exact 32-pair denominator required",
    )
    for i, unit in enumerate(manifest["units"]):
        _require(
            unit["index"] == i and unit["spec"] == plan["cases"][i],
            "input unit order/spec mismatch",
        )
        if unit["status"] == "completed":
            _require(
                unit["directory"] == f"unit-{i:02d}", "unexpected input unit directory"
            )
    return manifest, plan


def analyze_unit(input_dir, index, output):
    input_dir, output = disjoint_output(input_dir, output)
    manifest, _ = load_campaign(input_dir)
    _require(
        type(index) is int and 0 <= index < 32, "unit index outside fixed denominator"
    )
    unit = manifest["units"][index]
    _require(unit["status"] == "completed", "source unit unavailable")
    directory = input_dir / f"unit-{index:02d}"
    report_path, array_path = directory / "report.json", directory / "arrays.npz"
    _require(sha(report_path) == unit["report_sha256"], "input report hash mismatch")
    report = json.loads(report_path.read_text())
    _require(report["spec"] == unit["spec"], "input report spec mismatch")
    _require(
        report["array_artifact"] == unit["array_artifact"],
        "input artifact receipt mismatch",
    )
    _require(
        array_path.stat().st_size == unit["array_artifact"]["bytes"]
        and sha(array_path) == unit["array_artifact"]["sha256"],
        "input NPZ size/hash mismatch",
    )
    started = time.monotonic()
    with np.load(array_path, allow_pickle=False) as arrays:
        result = analyze_pair(report, arrays)
    result["input_artifacts"] = {
        "manifest_sha256": INPUT_MANIFEST_SHA256,
        "plan_sha256": INPUT_PLAN_SHA256,
        "unit_index": index,
        "report_sha256": unit["report_sha256"],
        "npz_sha256": unit["array_artifact"]["sha256"],
        "npz_bytes": unit["array_artifact"]["bytes"],
    }
    result["timing_seconds"] = time.monotonic() - started
    result["peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (
        1 if platform.system() == "Darwin" else 1024
    )
    output.mkdir(parents=True, exist_ok=False)
    write(output / "report.json", result)
    print(
        json.dumps(
            {"index": index, "records": 180, "seconds": result["timing_seconds"]}
        ),
        flush=True,
    )


def source_lock():
    paths = [
        PROTOCOL,
        "scripts/p4_reference_perturbation_diagnostics_v0_1.py",
        "scripts/analyze_p4_reference_perturbation_v0_1.py",
        "tests/test_p4_reference_perturbation_v0_1.py",
    ]
    return {p: sha(ROOT / p) for p in paths}


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (AS_BYTES, AS_BYTES))
    resource.setrlimit(resource.RLIMIT_CPU, (CASE_SECONDS, CASE_SECONDS + 1))
    resource.setrlimit(resource.RLIMIT_FSIZE, (FILE_BYTES, FILE_BYTES))
    os.nice(10)


def run_campaign(input_dir, output_dir):
    input_dir, output_dir = disjoint_output(input_dir, output_dir)
    _require(platform.system() == "Linux", "bounded campaign requires Linux")
    _require(sha(ROOT / PROTOCOL) == PROTOCOL_SHA256, "analysis protocol changed")
    manifest, original_plan = load_campaign(input_dir)
    for path, digest in original_plan["source_sha256"].items():
        _require(sha(ROOT / path) == digest, "predecessor source changed: " + path)
    lock = source_lock()
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    output_dir.mkdir(parents=True, exist_ok=False)
    plan = {
        "schema_version": SCHEMA + ".campaign",
        "source_sha256": lock,
        "checkout_revision": revision,
        "protocol_sha256": PROTOCOL_SHA256,
        "input_manifest_sha256": INPUT_MANIFEST_SHA256,
        "input_plan_sha256": INPUT_PLAN_SHA256,
        "input_directory": str(input_dir),
        "input_source_entries_verified": len(original_plan["source_sha256"]),
        "paired_units": 32,
        "loop_hypothesis_records_planned": 5760,
        "cases": original_plan["cases"],
        "exploratory_reanalysis": True,
        "resource_limits": {
            "case_seconds": CASE_SECONDS,
            "total_seconds": TOTAL_SECONDS,
            "child_address_space_bytes": AS_BYTES,
            "file_bytes": FILE_BYTES,
            "pre_unit_disk_bytes": DISK_BYTES,
            "concurrent_children": 1,
            "blas_threads": 1,
        },
        "new_observations": 0,
        "reference_selected": False,
        "scientific_authority": False,
    }
    write(output_dir / "plan.json", plan)
    env = dict(
        os.environ,
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        PYTHONDONTWRITEBYTECODE="1",
    )
    started, records = time.monotonic(), []
    for index, unit in enumerate(manifest["units"]):
        elapsed = time.monotonic() - started
        used = sum(p.stat().st_size for p in output_dir.rglob("*") if p.is_file())
        reason = (
            "time-budget"
            if elapsed >= TOTAL_SECONDS
            else "disk-admission-budget"
            if used >= DISK_BYTES
            else "source-changed"
            if source_lock() != lock
            else None
        )
        if reason:
            records.extend(
                {"index": i, "spec": u["spec"], "status": "not_run", "reason": reason}
                for i, u in enumerate(manifest["units"][index:], index)
            )
            break
        record = {
            "index": index,
            "spec": unit["spec"],
            "status": "running",
            "planned_loop_hypothesis_records": 180,
        }
        write(output_dir / f"unit-{index:02d}.attempt.json", record)
        if unit["status"] != "completed":
            record.update(status="source_unavailable", reason=unit["status"])
        else:
            output = output_dir / f"unit-{index:02d}"
            began = time.monotonic()
            with (
                (output_dir / f"unit-{index:02d}.stdout").open("x") as stdout,
                (output_dir / f"unit-{index:02d}.stderr").open("x") as stderr,
            ):
                try:
                    child = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(Path(__file__).resolve()),
                            "--input",
                            str(input_dir),
                            "--output",
                            str(output),
                            "--child",
                            str(index),
                        ],
                        env=env,
                        cwd=ROOT,
                        stdout=stdout,
                        stderr=stderr,
                        timeout=min(CASE_SECONDS, TOTAL_SECONDS - elapsed),
                        preexec_fn=limits,
                        check=False,
                    )
                    record.update(
                        status="completed" if child.returncode == 0 else "failed",
                        returncode=child.returncode,
                    )
                except subprocess.TimeoutExpired:
                    record.update(status="timeout", reason="unit-deadline")
                except OSError as exc:
                    record.update(
                        status="failed", reason="child-launch-error", error=str(exc)
                    )
            record["seconds"] = time.monotonic() - began
            if record["status"] == "completed":
                try:
                    path = output / "report.json"
                    result = json.loads(path.read_text())
                    _require(
                        result["spec"] == unit["spec"]
                        and result["loop_hypothesis_records"] == 180
                        and len(result["cells"]) == 9,
                        "incomplete output denominator",
                    )
                    _require(
                        result["input_artifacts"]["npz_sha256"]
                        == unit["array_artifact"]["sha256"],
                        "output input binding mismatch",
                    )
                    record.update(
                        report_sha256=sha(path),
                        report_bytes=path.stat().st_size,
                        peak_rss_bytes=result["peak_rss_bytes"],
                        loop_hypothesis_records=180,
                    )
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    record.update(
                        status="failed",
                        reason="output-validation-failed",
                        error=str(exc),
                    )
        write(output_dir / f"unit-{index:02d}.terminal.json", record)
        records.append(record)
        print(json.dumps({"index": index, "status": record["status"]}), flush=True)
    result = {
        "schema_version": SCHEMA + ".campaign",
        "plan_sha256": sha(output_dir / "plan.json"),
        "paired_units": 32,
        "loop_hypothesis_records_planned": 5760,
        "completed": sum(r["status"] == "completed" for r in records),
        "loop_hypothesis_records_completed": sum(
            r.get("loop_hypothesis_records", 0) for r in records
        ),
        "units": records,
        "elapsed_seconds": time.monotonic() - started,
        "disk_bytes_before_manifest": sum(
            p.stat().st_size for p in output_dir.rglob("*") if p.is_file()
        ),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "host": platform.node(),
        "gpu_used": False,
        "model_accessed": False,
        "scientific_authority": False,
        "reference_selected": False,
        "new_observations": 0,
    }
    write(output_dir / "manifest.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--child", type=int)
    args = parser.parse_args()
    if args.child is not None:
        analyze_unit(args.input, args.child, args.output)
        return 0
    result = run_campaign(args.input, args.output)
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "completed",
                    "elapsed_seconds",
                    "loop_hypothesis_records_completed",
                )
            }
        ),
        flush=True,
    )
    return 0 if result["completed"] == 32 else 1


if __name__ == "__main__":
    raise SystemExit(main())
