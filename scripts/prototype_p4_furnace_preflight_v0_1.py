#!/usr/bin/env python3
"""Portable synthetic fixtures and numerical cross-host parity, not scale qualification.

Writes only to a new explicitly named directory. No network, model, launcher,
GPU backend, kernel mutation, or graph-size-cap changes are implemented here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
import scipy

import prototype_p4_graph_cross_v0_1 as cross


SCHEMA = "spirallens.p4-furnace-preflight.v0.1"
ATOL = 1e-10
RTOL = 1e-10
ANCHORS = (
    cross.GraphCrossSpec("quadratic_excess"),
    cross.GraphCrossSpec("quadratic_excess", warp=0.75),
    cross.GraphCrossSpec("curved_coherent", probe_noise=0.03),
    cross.GraphCrossSpec("collapsed_support"),
)
KERNEL_FILES = (
    "prototype_p4_graph_cross_v0_1.py",
    "prototype_p4_estimand_comparison_v0_1.py",
    "prototype_p4_partial_patterns_v0_1.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, allow_nan=False)
        stream.write("\n")


def make_fixtures(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    records = []
    for index, spec in enumerate(ANCHORS):
        bundle = cross.make_graph_cross_probes(spec)
        observations = bundle.observations
        path = output / f"fixture-{index}.npz"
        np.savez_compressed(
            path,
            coords=observations.coords,
            faces=observations.faces,
            plane_fit_probes=observations.plane_fit_probes,
            baseline_fit_probes=observations.baseline_fit_probes,
            evaluation_probes=observations.evaluation_probes,
            graph_states=bundle.graph_input.states,
            vertex_ids=bundle.graph_input.vertex_ids,
        )
        records.append(
            {"file": path.name, "sha256": sha256(path), "spec": asdict(spec)}
        )
    manifest = {
        "schema_version": SCHEMA,
        "case_count": len(records),
        "cases": records,
        "kernel_sha256": {
            name: sha256(Path(__file__).with_name(name)) for name in KERNEL_FILES
        },
        "float_atol": ATOL,
        "float_rtol": RTOL,
        "discrete_values_must_match_exactly": True,
        "model_data": False,
        "scientific_authority": False,
    }
    _write_json(output / "manifest.json", manifest)
    return manifest


def _portable_value(value):
    """Numerical parity omits derived digests, never discrete states or arrays.

    Digests and raw full results remain in the per-host artifact. Small LAPACK
    roundoff can change a downstream digest without changing an admitted value.
    """
    if isinstance(value, dict):
        return {
            key: _portable_value(item)
            for key, item in value.items()
            if "sha256" not in key
        }
    if isinstance(value, list):
        return [_portable_value(item) for item in value]
    return value


def measure_fixtures(fixtures: Path, output: Path, host_label: str) -> dict:
    manifest = json.loads((fixtures / "manifest.json").read_text())
    if manifest["schema_version"] != SCHEMA or manifest["case_count"] != len(ANCHORS):
        raise ValueError("unexpected frozen fixture manifest")
    if len(manifest["cases"]) != len(ANCHORS):
        raise ValueError("missing frozen fixture")
    for index, (record, spec) in enumerate(
        zip(manifest["cases"], ANCHORS, strict=True)
    ):
        if record["file"] != f"fixture-{index}.npz" or record["spec"] != asdict(spec):
            raise ValueError("frozen fixture order or specification differs")
    for name in KERNEL_FILES:
        if manifest["kernel_sha256"][name] != sha256(Path(__file__).with_name(name)):
            raise ValueError(f"kernel bytes differ: {name}")
    # Verify every fixture before producing an execution directory.
    for record in manifest["cases"]:
        path = fixtures / record["file"]
        if path.parent != fixtures or path.name not in {
            f"fixture-{i}.npz" for i in range(len(ANCHORS))
        }:
            raise ValueError("unexpected fixture name")
        if sha256(path) != record["sha256"]:
            raise ValueError("fixture digest differs")
    output.mkdir(parents=True, exist_ok=False)
    records = []
    for index, record in enumerate(manifest["cases"]):
        with np.load(fixtures / record["file"], allow_pickle=False) as arrays:
            observations = cross.comparison.ComparisonBundle(
                **{
                    key: arrays[key].copy()
                    for key in (
                        "coords",
                        "faces",
                        "plane_fit_probes",
                        "baseline_fit_probes",
                        "evaluation_probes",
                    )
                }
            )
            bundle = cross.GraphCrossBundle(
                observations,
                cross.GraphInput(
                    primary_unit_id="synthetic-graph-cross",
                    vertex_ids=arrays["vertex_ids"].copy(),
                    states=arrays["graph_states"].copy(),
                ),
            )
        started = time.monotonic()
        report = cross.measure_graph_cross(bundle, gauge=record["spec"]["gauge"])
        elapsed = time.monotonic() - started
        path = output / f"result-{index}.json"
        _write_json(path, report)
        records.append(
            {
                "file": path.name,
                "sha256": sha256(path),
                "fixture_sha256": record["sha256"],
                "elapsed_seconds": elapsed,
            }
        )
    result = {
        "schema_version": SCHEMA,
        "fixture_manifest_sha256": sha256(fixtures / "manifest.json"),
        "host_label": host_label,
        "runtime": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "cases": records,
        "kernel_sha256": manifest["kernel_sha256"],
        "scope": {
            "synthetic_only": True,
            "model_accessed": False,
            "gpu_used": False,
            "large_scale_run": False,
            "scientific_authority": False,
        },
        "kernel_scope_note": "Nested kernel scope records no remote-call capability; host_label records the actual execution location.",
    }
    _write_json(output / "manifest.json", result)
    return result


def compare_values(left, right, path: str = "root") -> list[str]:
    if type(left) is not type(right):
        return [f"{path}: type differs"]
    if isinstance(left, dict):
        if left.keys() != right.keys():
            return [f"{path}: keys differ"]
        return [
            failure
            for key in left
            for failure in compare_values(left[key], right[key], f"{path}.{key}")
        ]
    if isinstance(left, list):
        if len(left) != len(right):
            return [f"{path}: length differs"]
        return [
            failure
            for i, (a, b) in enumerate(zip(left, right, strict=True))
            for failure in compare_values(a, b, f"{path}[{i}]")
        ]
    equal = (
        bool(
            np.isfinite(left)
            and np.isfinite(right)
            and np.isclose(left, right, rtol=RTOL, atol=ATOL)
        )
        if isinstance(left, float)
        else left == right
    )
    return [] if equal else [f"{path}: values differ"]


def compare_hosts(left: Path, right: Path) -> dict:
    manifests = [
        json.loads((directory / "manifest.json").read_text())
        for directory in (left, right)
    ]
    failures = []
    for key in ("schema_version", "fixture_manifest_sha256", "kernel_sha256"):
        if manifests[0][key] != manifests[1][key]:
            failures.append(f"manifest.{key}: differs")
    if len(manifests[0]["cases"]) != len(ANCHORS) or len(manifests[1]["cases"]) != len(
        ANCHORS
    ):
        raise ValueError("missing preflight anchor")
    for index in range(len(ANCHORS)):
        if (
            manifests[0]["cases"][index]["fixture_sha256"]
            != manifests[1]["cases"][index]["fixture_sha256"]
        ):
            failures.append(f"case[{index}]: fixture digest differs")
        values = []
        for directory, manifest in zip((left, right), manifests, strict=True):
            record = manifest["cases"][index]
            path = directory / f"result-{index}.json"
            if record["file"] != path.name or sha256(path) != record["sha256"]:
                raise ValueError("execution artifact digest differs")
            values.append(_portable_value(json.loads(path.read_text())))
        failures.extend(compare_values(*values, path=f"case[{index}]"))
    return {
        "schema_version": SCHEMA,
        "status": "pass" if not failures else "fail",
        "case_count": len(ANCHORS),
        "float_atol": ATOL,
        "float_rtol": RTOL,
        "failures": failures,
        "kernel_only_cross_host_parity": True,
        "gpu_parity": False,
        "large_scale_authority": False,
        "scientific_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    fixture = modes.add_parser("fixtures")
    fixture.add_argument("--output", type=Path, required=True)
    measure = modes.add_parser("measure")
    measure.add_argument("--fixtures", type=Path, required=True)
    measure.add_argument("--output", type=Path, required=True)
    measure.add_argument("--host-label", required=True, choices=("mac", "furnace"))
    compare = modes.add_parser("compare")
    compare.add_argument("--left", type=Path, required=True)
    compare.add_argument("--right", type=Path, required=True)
    compare.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.mode == "fixtures":
        result = make_fixtures(args.output)
    elif args.mode == "measure":
        result = measure_fixtures(args.fixtures, args.output, args.host_label)
    else:
        result = compare_hosts(args.left, args.right)
        if args.output is not None:
            _write_json(args.output, result)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return int(result.get("status") == "fail")


if __name__ == "__main__":
    raise SystemExit(main())
