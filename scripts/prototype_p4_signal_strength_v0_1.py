"""Prospectively fixed signal-strength cross sections from synthetic probes.

Only quadratic signal strength changes on the same flat substrate. Shared
raw noise is paired across strengths/P; references are fitted separately at
each strength before held-out/evaluation reads. No predecessor is mutated.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
from itertools import product
import json
from pathlib import Path
import platform
import resource
import time
from types import FunctionType

import numpy as np

import analyze_p4_reference_perturbation_v0_1 as perturbation
import prototype_p4_reference_validation_v0_1 as reference


SCHEMA = "spirallens.p4-signal-strength.v0.1"
PROTOCOL_TAG = 0x50345353  # P4SS: new, prospectively fixed noise namespace.
NOISE_PROTOCOL = "seedsequence-seed-P4SS-A-B-V-vertex-major-max128-first-P.v0.1"
STRENGTHS = (
    0,
    1e-6,
    3e-6,
    1e-5,
    3e-5,
    1e-4,
    3e-4,
    0.001,
    0.002,
    0.003,
    0.004,
    0.006,
    0.008,
    0.01,
    0.0125,
    0.015,
    0.02,
    0.025,
    0.03,
    0.04,
    0.05,
    0.06,
    0.08,
    0.10,
    0.125,
    0.15,
    0.20,
    0.25,
    0.35,
    0.50,
    0.65,
    0.80,
    1.0,
)
CATEGORIES = (
    "both_admitted_equal",
    "both_admitted_different",
    "A_only_admitted",
    "B_only_admitted",
    "neither_admitted",
)


@dataclass(frozen=True)
class StrengthSpec:
    signal_strength: float = 1.0
    side: int = 17
    k: int = 8
    pattern: str = "quadratic_excess"
    probe_count: int = 128
    seed: int = 0
    baseline_noise: float = 0.03

    def __post_init__(self):
        reference.ReferenceSpec(
            side=self.side,
            k=self.k,
            pattern=self.pattern,
            probe_count=self.probe_count,
            seed=self.seed,
            baseline_noise=self.baseline_noise,
        )
        if self.side not in (17, 65) or self.pattern != "quadratic_excess":
            raise ValueError(
                "strength screen fixes flat quadratic family and side17/65"
            )
        if (
            isinstance(self.signal_strength, (bool, np.bool_))
            or not isinstance(self.signal_strength, (int, float))
            or self.signal_strength not in STRENGTHS
        ):
            raise ValueError("signal strength must be one of the fixed 33 levels")

    @property
    def warp(self):
        return 0.0


def clone(function, **bindings):
    namespace = dict(function.__globals__)
    namespace.update(bindings)
    result = FunctionType(
        function.__code__,
        namespace,
        function.__name__,
        function.__defaults__,
        function.__closure__,
    )
    result.__kwdefaults__ = function.__kwdefaults__
    return result


def clean_probes(spec, coords):
    """Generate means/covariances, not rescaled measured residual arrays."""
    coords = np.asarray(coords, dtype=np.float64)
    if coords.shape != (spec.side**2, 2) or not np.isfinite(coords).all():
        raise ValueError("finite declared square coordinates required")
    z = coords[:, 0] + 1j * coords[:, 1]
    field = z + (0.25 * spec.signal_strength) * z**2
    values = np.column_stack((field.real, field.imag))
    frames = np.broadcast_to(np.eye(3)[:, :2], (len(coords), 3, 2))
    cube = np.array(list(product((-1.0, 1.0), repeat=3)))
    plane = np.einsum("pi,ndi->npd", cube[:, :2] * [2.0, 1.0], frames)
    mean = np.einsum("ndi,ni->nd", frames, values)
    tensor = reference.predecessor.tensor_from_values(values)
    covariance = (1 + np.abs(field))[:, None, None] * np.eye(
        3
    ) + frames @ tensor @ np.swapaxes(frames, -1, -2)
    root = np.linalg.cholesky(covariance)
    response = mean[:, None, :] + np.einsum("pi,ndi->npd", cube, root)
    repeats = spec.probe_count // 8
    return {
        "plane": np.tile(plane, (1, repeats, 1)),
        "baseline": np.tile(response, (1, repeats, 1)),
        "evaluation": np.tile(response, (1, repeats, 1)),
    }


def make_inputs(spec, coords, *, receipt=None):
    coords = np.asarray(coords, dtype=np.float64)
    clean = clean_probes(spec, coords)
    fit_rows = reference._rows(coords, reference.FIT_COORDS)
    validation_rows = reference._rows(coords, reference.VALIDATION_COORDS)
    if np.intersect1d(fit_rows, validation_rows).size:
        raise ValueError("validation and affine fit stencils overlap")
    inputs = {
        "plane": clean["plane"],
        "evaluation": clean["evaluation"],
        "baseline_A": clean["baseline"].copy(),
        "baseline_B": clean["baseline"].copy(),
        "validation_probes": clean["baseline"][validation_rows].copy(),
        "validation_rows": validation_rows,
        "fit_rows": fit_rows,
    }
    streams = np.random.SeedSequence([spec.seed, PROTOCOL_TAG]).spawn(3)
    hashes = {}
    for arm, name, stream in zip(
        ("A", "B", "V"),
        ("baseline_A", "baseline_B", "validation_probes"),
        streams,
        strict=True,
    ):
        hashes[arm] = None
        if not spec.baseline_noise:
            continue
        digest = hashlib.sha256(
            f"{NOISE_PROTOCOL}:{arm}:{len(coords)},128,3\0".encode()
        )
        rng = np.random.default_rng(stream)
        for start in range(0, len(coords), 4096):
            stop = min(start + 4096, len(coords))
            noise = rng.normal(size=(stop - start, 128, 3))
            digest.update(np.ascontiguousarray(noise, dtype="<f8").tobytes())
            if arm == "V":
                selected = np.flatnonzero(
                    (validation_rows >= start) & (validation_rows < stop)
                )
                inputs[name][selected] += (
                    spec.baseline_noise
                    * noise[validation_rows[selected] - start, : spec.probe_count]
                )
            else:
                inputs[name][start:stop] += (
                    spec.baseline_noise * noise[:, : spec.probe_count]
                )
        hashes[arm] = digest.hexdigest()
    if receipt is not None:
        receipt.update(
            protocol=NOISE_PROTOCOL,
            standard_normal_stream_sha256=hashes,
            paired_across_strength=True,
            paired_across_probe_count=True,
            independent_reference_draws=2 if spec.baseline_noise else 0,
            independent_noise_streams=3 if spec.baseline_noise else 0,
            hashes_bind_full_max128_draws_not_strength_dependent_observations=True,
        )
    return inputs


def measure_pair(spec, output=None):
    if not isinstance(spec, StrengthSpec):
        raise TypeError("StrengthSpec required")
    started = time.monotonic()
    if output is not None:
        output = Path(output)
        output.mkdir(parents=True, exist_ok=False)
    noise_receipt = {}
    measurement = clone(
        reference.measure_pair,
        ReferenceSpec=StrengthSpec,
        make_inputs=lambda s, c: make_inputs(s, c, receipt=noise_receipt),
        SCHEMA=SCHEMA,
        PROTOCOL_TAG=PROTOCOL_TAG,
        NOISE_PROTOCOL=NOISE_PROTOCOL,
        __file__=__file__,
    )
    report, arrays = measurement(spec, output=None)
    diagnostics = clone(perturbation.analyze_pair, INPUT_SCHEMA=SCHEMA)(report, arrays)
    for hypotheses in diagnostics["diagnostics"].values():
        for loops in hypotheses.values():
            for entry in loops.values():
                if entry["measurement"] is not None:
                    for key in ("points", "reasons", "support"):
                        entry["measurement"].pop(key)
    report["perturbation"] = diagnostics
    report["noise_receipt"] = noise_receipt
    report["design"].update(
        signal_strength=spec.signal_strength,
        response="F2=F4=z+0.25*alpha*z^2",
        substrate="flat",
        zero_strength="linear-only-full-field; no injected quadratic component",
        baseline_refit_at_each_strength=True,
        observations_generated_at_strength_not_scaled_residuals=True,
        paired_across_strength=True,
        strength_trace_points_are_not_independent=True,
    )
    report["scope"].update(
        prospective_exploratory_strength_panel=True,
        physical_phase_transition_established=False,
        calibrated_detection_threshold=False,
    )
    for path in (reference.__file__, perturbation.__file__):
        report["source_sha256"][Path(path).name] = reference.sensitivity._file_hash(
            path
        )
    report["timing"]["with_perturbation_seconds"] = time.monotonic() - started
    if output is not None:
        artifact = output / "arrays.npz"
        with artifact.open("xb") as stream:
            np.savez_compressed(stream, **arrays)
        report["array_artifact"] = {
            "file": artifact.name,
            "bytes": artifact.stat().st_size,
            "sha256": reference.sensitivity._file_hash(artifact),
        }
        report["timing"]["total_with_serialization_seconds"] = (
            time.monotonic() - started
        )
    report["peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (
        1 if platform.system() == "Darwin" else 1024
    )
    if output is not None:
        reference.predecessor._write(output / "report.json", report)
    return report, arrays


def compact_report(report):
    """All original loops and graph rows, without raw arrays or full arm copies."""
    loops = {}
    for loop in perturbation.ORIENTED_LOOPS:
        loops[loop] = {}
        for h in ("F2", "F4"):
            categories = dict.fromkeys(CATEGORIES, 0)
            plus2 = 0
            for cell in report["paired_cells"]:
                pair = cell["loops"][loop][h]
                categories[perturbation._category(pair["A"], pair["B"])] += 1
                plus2 += int(
                    all(
                        pair[a]["state"] == "eligible"
                        and pair[a]["value"]["sampled_winding"] == 2
                        for a in ("A", "B")
                    )
                )
            rows = {}
            for family in perturbation.FAMILIES:
                d = report["perturbation"]["diagnostics"][family][h][loop]
                rows[family] = {
                    k: v for k, v in d.items() if k not in ("vertices", "measurement")
                }
                rows[family]["measurement"] = d["measurement"]
            loops[loop][h] = {
                "paired_categories": categories,
                "both_plus2_cells": plus2,
                "required_cells": 9,
                "rows": rows,
            }
    return {
        "schema_version": SCHEMA + ".compact",
        "spec": report["spec"],
        "noise_receipt": report["noise_receipt"],
        "loops": loops,
        "heldout": report["heldout"],
        "chronology": report["chronology"],
        "source_sha256": report["source_sha256"],
        "array_artifact": report.get("array_artifact"),
        "loop_hypothesis_records": 180,
        "scope": report["scope"],
    }


def trace_descriptor(units, hypothesis):
    """Finite-grid first/suffix +2 descriptors, never a continuous threshold."""
    if len(units) != len(STRENGTHS) or [
        u["spec"]["signal_strength"] for u in units
    ] != list(STRENGTHS):
        raise ValueError("exact ordered 33-level trace required")
    flags = [
        None
        if u["status"] != "completed"
        else u["outer"][hypothesis]["both_plus2_cells"] == 9
        for u in units
    ]
    indices = [i for i, flag in enumerate(flags) if flag is True]
    first = indices[0] if indices else None
    suffix = None
    if None not in flags:
        suffix = next((i for i in indices if all(flags[i:])), None)

    def bracket(i):
        return (
            None
            if i is None
            else {
                "previous_strength": None if i == 0 else STRENGTHS[i - 1],
                "sampled_strength": STRENGTHS[i],
            }
        )

    return {
        "first_all_cells_both_plus2": bracket(first),
        "all_remaining_sampled_strengths_both_plus2": bracket(suffix),
        "trace_complete": None not in flags,
        "flags": flags,
        "breaks_after_first": []
        if first is None
        else [STRENGTHS[i] for i in range(first + 1, len(flags)) if flags[i] is False],
        "not_a_continuous_or_calibrated_threshold": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--strength", type=float, choices=STRENGTHS, default=1)
    parser.add_argument("--side", type=int, choices=(17, 65), default=17)
    parser.add_argument("--probe-count", type=int, choices=(8, 32, 128), default=128)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--baseline-noise", type=float, choices=(0, 0.03), default=0.03)
    args = parser.parse_args()
    report, _ = measure_pair(
        StrengthSpec(
            signal_strength=args.strength,
            side=args.side,
            probe_count=args.probe_count,
            seed=args.seed,
            baseline_noise=args.baseline_noise,
        ),
        args.output,
    )
    print(json.dumps({"spec": report["spec"], "summary": report["summary"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
