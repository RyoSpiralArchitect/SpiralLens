#!/usr/bin/env python3
"""Independent affine references and heldout observations; CPU synthetic only.

Both A/B references are sealed before either evaluation arm is read. A third,
independent probe stream is observed only at the fixed eight heldout vertices.
Heldout errors are diagnostics: they do not select, refit, or admit either arm.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import platform
import resource
import time
from types import SimpleNamespace

import numpy as np

import p4_dense_moment_adapter_v0_1 as dense_adapter
import prototype_p4_large_domain_v0_1 as predecessor
import prototype_p4_probe_sensitivity_v0_1 as sensitivity
from p4_dense_moment_adapter_v0_1 import DenseMomentAdapter


SCHEMA = "spirallens.p4-independent-reference-validation.v0.1"
PROTOCOL_TAG = 0x50345256  # ASCII P4RV; frozen stream namespace, not a user seed.
NOISE_PROTOCOL = "seedsequence-seed-P4RV-A-B-V-vertex-major-max128-first-P.v0.1"
FIT_COORDS = np.array([[0, 0], [-0.5, 0], [0.5, 0], [0, -0.5], [0, 0.5]])
VALIDATION_COORDS = np.array(
    [
        [-0.5, -0.5],
        [-0.5, 0.5],
        [0.5, -0.5],
        [0.5, 0.5],
        [-0.25, 0],
        [0.25, 0],
        [0, -0.25],
        [0, 0.25],
    ]
)
NOISE_CHUNK_VERTICES = 4096


@dataclass(frozen=True)
class ReferenceSpec:
    side: int = 17
    k: int = 8
    pattern: str = "curved_coherent"
    probe_count: int = 8
    seed: int = 0
    baseline_noise: float = 0.03

    def __post_init__(self):
        if type(self.side) is not int or self.side not in (17, 65, 257):
            raise ValueError("reference sides are 17,65,257")
        if type(self.k) is not int or self.k != 8:
            raise ValueError("reference screen fixes k=8")
        if self.pattern not in ("curved_coherent", "quadratic_excess"):
            raise ValueError("only curved_coherent/quadratic_excess are declared")
        if type(self.probe_count) is not int or self.probe_count not in (8, 32, 128):
            raise ValueError("reference probe counts are 8,32,128")
        if type(self.seed) is not int or not 0 <= self.seed < 2**32:
            raise ValueError("seed must be uint32")
        if (
            isinstance(self.baseline_noise, bool)
            or not np.isfinite(self.baseline_noise)
            or self.baseline_noise not in (0.0, 0.03)
        ):
            raise ValueError("registered baseline_noise must be 0 or 0.03")

    @property
    def warp(self):
        return 0.0


def _rows(coords, targets):
    result = []
    for target in targets:
        matches = np.flatnonzero(np.isclose(coords, target, rtol=0, atol=1e-12).all(1))
        if len(matches) != 1:
            raise ValueError("each preregistered stencil coordinate must occur once")
        result.append(int(matches[0]))
    return np.asarray(result, dtype=np.int64)


def make_inputs(spec: ReferenceSpec, coords):
    """Return shared clean inputs, independent A/B references, and heldout V.

    All streams consume conceptual (N,128,3) draws, even at P8 or P32. Only
    heldout V rows are retained or subsequently evaluated. No V values are
    used to choose the heldout vertices, fit references, or evaluate loops.
    """
    coords = np.asarray(coords, dtype=np.float64)
    if coords.shape != (spec.side**2, 2) or not np.isfinite(coords).all():
        raise ValueError("finite coordinates for the declared square required")
    fit_rows = _rows(coords, FIT_COORDS)
    validation_rows = _rows(coords, VALIDATION_COORDS)
    if np.intersect1d(fit_rows, validation_rows).size:
        raise ValueError("heldout rows must be disjoint from affine-fit rows")
    clean = sensitivity.make_probes(
        sensitivity.ProbeSpec(
            side=spec.side,
            k=spec.k,
            pattern=spec.pattern,
            probe_count=spec.probe_count,
            probe_noise=0,
            noise_role="none",
            seed=spec.seed,
        ),
        coords,
    )
    streams = np.random.SeedSequence([spec.seed, PROTOCOL_TAG]).spawn(3)
    result = {
        "plane": clean["plane"],
        "evaluation": clean["evaluation"],
        "baseline_A": clean["baseline"].copy(),
        "baseline_B": clean["baseline"].copy(),
        "validation_probes": clean["baseline"][validation_rows].copy(),
        "validation_rows": validation_rows,
        "fit_rows": fit_rows,
    }
    for name, stream in zip(
        ("baseline_A", "baseline_B", "validation_probes"), streams, strict=True
    ):
        if not spec.baseline_noise:
            continue
        rng = np.random.default_rng(stream)
        for start in range(0, len(coords), NOISE_CHUNK_VERTICES):
            stop = min(start + NOISE_CHUNK_VERTICES, len(coords))
            noise = rng.normal(size=(stop - start, 128, 3))
            if name == "validation_probes":
                selected = np.flatnonzero(
                    (validation_rows >= start) & (validation_rows < stop)
                )
                result[name][selected] += (
                    spec.baseline_noise
                    * noise[validation_rows[selected] - start, : spec.probe_count]
                )
            else:
                result[name][start:stop] += (
                    spec.baseline_noise * noise[:, : spec.probe_count]
                )
    return result


def _arm_probes(inputs, arm):
    return {
        "plane": inputs["plane"],
        "baseline": inputs["baseline_" + arm],
        "evaluation": inputs["evaluation"],
    }


def _prepare_pair(spec, coords, graphs, inputs, adapter, events):
    _, namespace = sensitivity._isolated_measurement(adapter)
    prepared = {}
    for arm in ("A", "B"):
        prepared[arm] = {}
        for family in predecessor.FAMILIES:
            row = namespace["prepare_row"](
                coords, _arm_probes(inputs, arm), graphs[family]
            )
            if row[2]["stencil_rows"] != inputs["fit_rows"].tolist():
                raise ValueError("inherited fit stencil differs from registered rows")
            prepared[arm][family] = row
            events.append(
                {
                    "event": "baseline_sealed",
                    "arm": arm,
                    "family": family,
                    "seal_sha256": row[2]["seal_sha256"],
                }
            )
    return prepared


def _arm_measurement(spec, arm, inputs, prepared, adapter, events, coords, graphs):
    measurement, namespace = sensitivity._isolated_measurement(adapter)
    namespace["make_probes"] = lambda received, positions: _arm_probes(inputs, arm)

    def cached_row(positions, probes, graph):
        if not np.array_equal(positions, coords):
            raise ValueError("arm domain drifted from the presealed domain")
        if graph.fingerprint_sha256 != graphs[graph.family].fingerprint_sha256:
            raise ValueError("arm graph drifted from the presealed graph")
        for role, expected in _arm_probes(inputs, arm).items():
            if probes[role] is not expected:
                raise ValueError("arm probe binding changed after the baseline seal")
        return prepared[arm][graph.family]

    def evaluation_moments(frames, probes):
        if sum(e["event"] == "baseline_sealed" for e in events) != 6:
            raise ValueError(
                "both arms require all six baseline seals before evaluation"
            )
        events.append({"event": "evaluation_moment_read", "arm": arm})
        return adapter.moments(frames, probes)

    namespace["prepare_row"] = cached_row
    namespace["moments"] = evaluation_moments
    chain_proxy = SimpleNamespace(**vars(predecessor.old.chain))
    old_proxy = SimpleNamespace(**vars(predecessor.old))
    old_proxy.chain = chain_proxy
    loop_started = False

    def geometry(*args, **kwargs):
        nonlocal loop_started
        if not loop_started:
            events.append({"event": "loop_readouts_started", "arm": arm})
            loop_started = True
        return predecessor.old.chain._geometry(*args, **kwargs)

    chain_proxy._geometry = geometry
    namespace["old"] = old_proxy
    return measurement(spec, output=None)


def _heldout(inputs, prepared, coords, adapter, events):
    if sum(e["event"] == "baseline_sealed" for e in events) != 6:
        raise ValueError("heldout observations require both arms' sealed baselines")
    selected = inputs["validation_rows"]
    design = np.column_stack((np.ones(len(selected)), coords[selected]))
    report = {
        "validation_rows": selected.tolist(),
        "validation_coords": coords[selected].tolist(),
        "fit_rows": inputs["fit_rows"].tolist(),
        "validation_rows_sha256": predecessor._hash(selected),
        "validation_coords_sha256": predecessor._hash(coords[selected]),
        "fit_rows_sha256": predecessor._hash(inputs["fit_rows"]),
        "fit_coords_sha256": predecessor._hash(coords[inputs["fit_rows"]]),
        "validation_probe_sha256": predecessor._hash(inputs["validation_probes"]),
        "heldout_used_for_fit_or_selection": False,
        "new_admission_threshold": None,
        "error_definition": "Euclidean norm of predicted minus observed F2/F4 values",
        "rows": {},
    }
    arrays = {}
    for family in predecessor.FAMILIES:
        frames, support, _, _, _ = prepared["A"][family]
        if not np.array_equal(frames, prepared["B"][family][0]) or not np.array_equal(
            support, prepared["B"][family][1]
        ):
            raise ValueError(
                "clean common plane inputs must yield identical arm frames"
            )
        events.append({"event": "heldout_moment_read", "family": family})
        values = adapter.moments(frames[selected], inputs["validation_probes"])
        report["rows"][family] = {}
        for hypothesis, observed in values.items():
            arrays[f"validation_{family}_{hypothesis}_values"] = observed
            report["rows"][family][hypothesis] = {}
            for arm in ("A", "B"):
                baseline = prepared[arm][family][2]
                coefficients = baseline["coefficients"][hypothesis]
                available = coefficients is not None and bool(support[selected].all())
                entry = {
                    "state": "available" if available else "insufficient",
                    "baseline_seal_sha256": baseline["seal_sha256"],
                    "validation_probe_sha256": report["validation_probe_sha256"],
                    "validation_values_sha256": predecessor._hash(observed),
                    "supported_vertex_count": int(support[selected].sum()),
                    "required_vertex_count": len(selected),
                    "prediction_errors": None,
                    "euclidean_rmse": None,
                    "maximum_error": None,
                    "selection_performed": False,
                }
                if available:
                    prediction = design @ np.asarray(coefficients)
                    errors = np.linalg.norm(prediction - observed, axis=1)
                    entry.update(
                        prediction_errors=errors.tolist(),
                        euclidean_rmse=float(np.sqrt(np.mean(errors**2))),
                        maximum_error=float(errors.max()),
                    )
                    arrays[f"validation_{arm}_{family}_{hypothesis}_prediction"] = (
                        prediction
                    )
                    arrays[f"validation_{arm}_{family}_{hypothesis}_errors"] = errors
                    arrays[f"baseline_{arm}_{family}_{hypothesis}_coefficients"] = (
                        np.asarray(coefficients)
                    )
                report["rows"][family][hypothesis][arm] = entry
    return report, arrays


def _paired_residual(arms, arm_arrays):
    report, arrays = {}, {}
    for family in predecessor.FAMILIES:
        report[family] = {}
        for hypothesis in ("F2", "F4"):
            residual_key = f"{family}_residual_affine_{hypothesis}_values"
            affine_key = f"{family}_local_affine_{hypothesis}_values"
            if not all(residual_key in arm_arrays[a] for a in ("A", "B")):
                report[family][hypothesis] = {
                    "state": "insufficient",
                    "maximum_identity_error": None,
                    "reason": "one-or-both-affine-references-unavailable",
                }
                continue
            residual_delta = (
                arm_arrays["A"][residual_key] - arm_arrays["B"][residual_key]
            )
            affine_delta = arm_arrays["A"][affine_key] - arm_arrays["B"][affine_key]
            report[family][hypothesis] = {
                "state": "available",
                "identity": "residual_A-residual_B == -(affine_A-affine_B)",
                "maximum_identity_error": float(
                    np.max(np.abs(residual_delta + affine_delta))
                ),
                "residual_delta_sha256": predecessor._hash(residual_delta),
                "affine_delta_sha256": predecessor._hash(affine_delta),
                "new_admission_threshold": None,
            }
            arrays[f"residual_delta_{family}_{hypothesis}"] = residual_delta
            arrays[f"affine_delta_{family}_{hypothesis}"] = affine_delta
    paired_cells = []
    for cell_a, cell_b in zip(arms["A"]["cells"], arms["B"]["cells"], strict=True):
        identity = (cell_a["field_graph"], cell_a["loop_graph"])
        if identity != (cell_b["field_graph"], cell_b["loop_graph"]):
            raise ValueError("paired graph cell identities differ")
        cell = {"field_graph": identity[0], "loop_graph": identity[1], "loops": {}}
        for loop in cell_a["loops"]:
            fields = {}
            for hypothesis in ("F2", "F4"):
                pair = {
                    arm: source["loops"][loop]["fields"]["residual_affine"][hypothesis]
                    for arm, source in (("A", cell_a), ("B", cell_b))
                }
                both = all(v["state"] == "eligible" for v in pair.values())
                fields[hypothesis] = {
                    **pair,
                    "same_state": pair["A"]["state"] == pair["B"]["state"],
                    "same_reason": pair["A"]["reason"] == pair["B"]["reason"],
                    "both_eligible": both,
                    "same_sampled_winding": (
                        pair["A"]["value"]["sampled_winding"]
                        == pair["B"]["value"]["sampled_winding"]
                        if both
                        else None
                    ),
                }
            cell["loops"][loop] = fields
        paired_cells.append(cell)
    return report, paired_cells, arrays


def _deduplicate(arm_arrays, inputs, extra):
    arrays = dict(extra)
    arrays.update({name: value for name, value in inputs.items()})
    layout = {"A": {}, "B": {}}
    for key in sorted(arm_arrays["A"].keys() | arm_arrays["B"].keys()):
        if key == "baseline":
            for arm in ("A", "B"):
                layout[arm][key] = "baseline_" + arm
        elif key in ("plane", "evaluation"):
            for arm in ("A", "B"):
                layout[arm][key] = key
        elif (
            key in arm_arrays["A"]
            and key in arm_arrays["B"]
            and np.array_equal(arm_arrays["A"][key], arm_arrays["B"][key])
        ):
            stored = "shared__" + key
            arrays[stored] = arm_arrays["A"][key]
            layout["A"][key] = layout["B"][key] = stored
        else:
            for arm in ("A", "B"):
                if key in arm_arrays[arm]:
                    stored = arm + "__" + key
                    arrays[stored] = arm_arrays[arm][key]
                    layout[arm][key] = stored
    return arrays, {"arms": layout, "shared_equal_arrays_stored_once": True}


def _summary(paired_cells):
    summary = {
        "loop": "outer_forward",
        "estimand": "residual_affine",
        "required_cell_count": 9,
    }
    for hypothesis in ("F2", "F4"):
        counts = dict.fromkeys(
            (
                "both_admitted_equal",
                "both_admitted_different",
                "A_only_admitted",
                "B_only_admitted",
                "neither_admitted",
            ),
            0,
        )
        for cell in paired_cells:
            pair = cell["loops"]["outer_forward"][hypothesis]
            if pair["both_eligible"]:
                name = (
                    "both_admitted_equal"
                    if pair["same_sampled_winding"]
                    else "both_admitted_different"
                )
            elif pair["A"]["state"] == "eligible":
                name = "A_only_admitted"
            elif pair["B"]["state"] == "eligible":
                name = "B_only_admitted"
            else:
                name = "neither_admitted"
            counts[name] += 1
        summary[hypothesis] = counts
    return summary


def measure_pair(spec: ReferenceSpec, output: Path | None = None):
    if not isinstance(spec, ReferenceSpec):
        raise TypeError("ReferenceSpec required")
    started = time.monotonic()
    if output is not None:
        output = Path(output)
        output.mkdir(parents=True, exist_ok=False)
    domain = predecessor.backend.make_domain(spec.side)
    coords = domain["coords"]
    x, y = coords.T
    states = np.column_stack(
        (x, y, 0.2 * x * y, 0.15 * np.sin(np.pi * x) * np.sin(np.pi * y))
    )
    graphs = predecessor.backend.build_graphs(states, k=spec.k)
    inputs = make_inputs(spec, coords)
    for value in inputs.values():
        value.setflags(write=False)
    adapter = DenseMomentAdapter(backend="numpy", batch_vertices=8192)
    events = []
    prepared = _prepare_pair(spec, coords, graphs, inputs, adapter, events)
    input_hashes = {name: predecessor._hash(value) for name, value in inputs.items()}
    heldout, extra = _heldout(inputs, prepared, coords, adapter, events)
    arms, arm_arrays = {}, {}
    for arm in ("A", "B"):
        arms[arm], arm_arrays[arm] = _arm_measurement(
            spec, arm, inputs, prepared, adapter, events, coords, graphs
        )
        arms[arm]["schema_version"] = SCHEMA + ".arm"
        arms[arm]["reference_arm"] = arm
        arms[arm]["spec"] = asdict(spec)
        arms[arm]["design"].update(
            noise_protocol=NOISE_PROTOCOL,
            reference_arm=arm,
            shared_clean_plane_and_evaluation=True,
            other_reference_sealed_before_evaluation=True,
            heldout_used_for_fit_or_selection=False,
        )
    if input_hashes != {
        name: predecessor._hash(value) for name, value in inputs.items()
    }:
        raise ValueError("frozen input bytes changed during measurement")
    residual, paired_cells, deltas = _paired_residual(arms, arm_arrays)
    extra.update(deltas)
    arrays, layout = _deduplicate(arm_arrays, inputs, extra)
    report = {
        "schema_version": SCHEMA,
        "spec": asdict(spec),
        "vertex_count": len(coords),
        "arms": arms,
        "heldout": heldout,
        "paired_residual": residual,
        "paired_cells": paired_cells,
        "summary": _summary(paired_cells),
        "array_layout": layout,
        "input_sha256": input_hashes,
        "numeric_adapter": adapter.receipt(),
        "design": {
            "axis_sizes_per_arm": [3, 3, 1],
            "noise_protocol": NOISE_PROTOCOL,
            "seed_sequence_entropy": [spec.seed, PROTOCOL_TAG],
            "stream_order": ["A", "B", "V"],
            "independent_noise_realizations": spec.baseline_noise > 0,
            "independent_noise_stream_count": 3 if spec.baseline_noise > 0 else 0,
            "independent_reference_draw_count": 2 if spec.baseline_noise > 0 else 0,
            "paired_across_probe_count": True,
            "noise_paired_across_domain_refinement": False,
            "shared_clean_plane_and_evaluation": True,
            "validation_rows_disjoint_from_fit_rows": True,
            "validation_noise_scale": spec.baseline_noise,
            "validation_noise_role": "independent-noisy-reference-observations",
            "new_admission_threshold": None,
            "selection_performed": False,
        },
        "chronology": {
            "baseline_seals_before_any_arm_evaluation": 6,
            "both_references_before_validation": True,
            "core_seals_before_loops_per_arm": 36,
            "events": events,
        },
        "scope": {
            "synthetic_only": True,
            "claim_ceiling": "level_0",
            "model_accessed": False,
            "gpu_used": False,
            "scientific_authority": False,
            "verified_core": False,
            "reference_selected": False,
            "phase": "not_evaluated",
            "transition": "not_evaluated",
        },
        "source_sha256": {
            Path(path).name: sensitivity._file_hash(path)
            for path in (
                __file__,
                predecessor.__file__,
                sensitivity.__file__,
                dense_adapter.__file__,
            )
        },
        "runtime": {"python": platform.python_version(), "numpy": np.__version__},
        "timing": {"measurement_seconds": time.monotonic() - started},
    }
    if output is not None:
        artifact = output / "arrays.npz"
        with artifact.open("xb") as stream:
            np.savez_compressed(stream, **arrays)
        report["array_artifact"] = {
            "file": artifact.name,
            "bytes": artifact.stat().st_size,
            "sha256": sensitivity._file_hash(artifact),
        }
        report["timing"]["total_with_serialization_seconds"] = (
            time.monotonic() - started
        )
    report["peak_rss_bytes"] = int(
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    ) * (1 if platform.system() == "Darwin" else 1024)
    if output is not None:
        predecessor._write(output / "report.json", report)
    return report, arrays


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--side", type=int, choices=(17, 65, 257), default=17)
    parser.add_argument("--probe-count", type=int, choices=(8, 32, 128), default=8)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--pattern",
        choices=("curved_coherent", "quadratic_excess"),
        default="curved_coherent",
    )
    parser.add_argument("--baseline-noise", type=float, default=0.03)
    args = parser.parse_args()
    report, _ = measure_pair(
        ReferenceSpec(
            side=args.side,
            probe_count=args.probe_count,
            seed=args.seed,
            pattern=args.pattern,
            baseline_noise=args.baseline_noise,
        ),
        output=args.output,
    )
    print(
        json.dumps(
            {
                k: report[k]
                for k in ("spec", "paired_residual", "timing", "peak_rss_bytes")
            },
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
