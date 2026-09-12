"""Three registered strength windows with located winding-gate diagnostics.

Reuses the sealed P4SS construction without modifying predecessor bindings.
Derived sampling checks never replace the original loop admission records.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import platform
import resource
import time

import numpy as np

import prototype_p4_signal_strength_v0_1 as strength
from spirallens.graphs.common import array_sha256
from spirallens.topology.winding import estimate_winding

SCHEMA = "spirallens.p4-one-arm-zoom.v0.1"
perturbation = strength.perturbation
CATEGORIES = strength.CATEGORIES
NOISE_PROTOCOL = strength.NOISE_PROTOCOL
AMPLITUDE_FLOOR = 1e-6
BRANCH_MARGIN_RAD = 0.15
WINDOWS = (
    ("f4-p8-s1", 8, 1, "0.002", "0.003", "0.004", "F4", (41, 42, 43)),
    ("f4-p8-s3", 8, 3, "0.08", "0.10", "0.125", "F4", (121, 122, 123)),
    ("f2-p128-s0", 128, 0, "0.008", "0.01", "0.0125", "F2", (276, 277, 278)),
)


def grid(window):
    lo, center, hi = map(Decimal, window[3:6])
    return tuple(
        float(a + (b - a) * Decimal(i) / 16)
        for a, b, indices in ((lo, center, range(16)), (center, hi, range(17)))
        for i in indices
    )


@dataclass(frozen=True)
class ZoomSpec:
    signal_strength: float = 0.003
    side: int = 17
    k: int = 8
    pattern: str = "quadratic_excess"
    probe_count: int = 8
    seed: int = 1
    baseline_noise: float = 0.03

    def __post_init__(self):
        strength.reference.ReferenceSpec(
            side=self.side,
            k=self.k,
            pattern=self.pattern,
            probe_count=self.probe_count,
            seed=self.seed,
            baseline_noise=self.baseline_noise,
        )
        window = next(
            (w for w in WINDOWS if w[1:3] == (self.probe_count, self.seed)), None
        )
        if (
            window is None
            or self.side not in (17, 65)
            or self.pattern != "quadratic_excess"
            or self.baseline_noise != 0.03
            or isinstance(self.signal_strength, (bool, np.bool_))
            or not isinstance(self.signal_strength, (int, float))
            or self.signal_strength not in grid(window)
        ):
            raise ValueError("registered one-arm window/spec required")

    @property
    def warp(self):
        return 0.0


def case_specs():
    return [
        ZoomSpec(side=65, probe_count=w[1], seed=w[2], signal_strength=a)
        for w in WINDOWS
        for a in grid(w)
    ]


def scalar_diagnostic(values, vertices, coords):
    """Located estimator diagnostics on exactly the supplied ordered vertices."""
    values = np.asarray(values)
    vertices = np.asarray(vertices, dtype=np.int64)
    coords = np.asarray(coords)
    if (
        values.shape != (len(coords), 2)
        or coords.ndim != 2
        or coords.shape[1] != 2
        or not np.isfinite(values).all()
        or not np.isfinite(coords).all()
        or vertices.ndim != 1
        or len(vertices) < 3
        or len(set(vertices.tolist())) != len(vertices)
        or np.any(vertices < 0)
        or np.any(vertices >= len(values))
    ):
        raise ValueError("finite field/coordinates and unique loop vertices required")
    sample = values[vertices, 0] + 1j * values[vertices, 1]
    estimate = estimate_winding(
        sample, amplitude_floor=AMPLITUDE_FLOOR, branch_margin_rad=BRANCH_MARGIN_RAD
    )
    angles = np.angle(np.roll(sample, -1) * np.conjugate(sample))
    i = int(np.argmax(np.abs(angles)))
    j = (i + 1) % len(vertices)
    low = int(np.argmin(np.abs(sample)))
    return {
        "reliable": estimate.reliable,
        "failure_reasons": list(estimate.failure_reasons),
        "sampled_winding": estimate.nearest_integer if estimate.reliable else None,
        "minimum_amplitude": estimate.minimum_amplitude,
        "maximum_edge_angle_rad": estimate.maximum_edge_angle_rad,
        "amplitude_slack": estimate.minimum_amplitude - AMPLITUDE_FLOOR,
        "branch_slack_rad": np.pi - BRANCH_MARGIN_RAD - estimate.maximum_edge_angle_rad,
        "sample_count": estimate.sample_count,
        "worst_edge": {
            "index": i,
            "vertices": vertices[[i, j]].tolist(),
            "coords": coords[vertices[[i, j]]].tolist(),
            "values": values[vertices[[i, j]]].tolist(),
            "signed_angle_rad": float(angles[i]),
        },
        "minimum_vertex": {
            "index": low,
            "vertex": int(vertices[low]),
            "coords": coords[vertices[low]].tolist(),
        },
        "scope": "sampled-principal-angle-estimator-only",
        "scientific_authority": False,
    }


def same_estimate(a, b):
    return (
        a["reliable"] == b["reliable"]
        and a["sampled_winding"] == b["sampled_winding"]
        and a["failure_reasons"] == b["failure_reasons"]
        and all(
            np.isclose(a[k], b[k], rtol=1e-12, atol=1e-12)
            for k in ("minimum_amplitude", "maximum_edge_angle_rad")
        )
    )


def located_diagnostics(report, arrays):
    """Replay the sealed residuals; preserve original insufficient values."""
    # The predecessor checks every field seal, array hash, frame/support match,
    # residual identity, exact graph-cell set and loop denominator.
    strength.clone(perturbation.analyze_pair, INPUT_SCHEMA=SCHEMA)(report, arrays)
    layout = report["array_layout"]["arms"]
    coords = np.asarray(arrays[layout["A"]["coords"]])
    if not np.array_equal(coords, arrays[layout["B"]["coords"]]):
        raise ValueError("paired coordinates changed")
    paths = report["arms"]["A"]["loop_vertices"]
    for arm in ("A", "B"):
        domain = report["arms"][arm]["domain"]
        if array_sha256(coords) != domain["coords_sha256"]:
            raise ValueError("coordinate hash mismatch")
        for name, vertices in paths.items():
            if (
                array_sha256(np.asarray(vertices, dtype="<i8"))
                != domain["loops"][name]["boundary_sha256"]
            ):
                raise ValueError("loop path hash mismatch")
    cache, controls = {}, {}
    for family in perturbation.FAMILIES:
        controls[family] = {}
        for h in ("F2", "F4"):
            controls[family][h] = {}
            for arm in ("A", "B"):
                field = report["arms"][arm]["rows"][family]["fields"][
                    "residual_affine"
                ][h]
                values = (
                    None
                    if field["missing"]
                    else arrays[layout[arm][f"{family}_residual_affine_{h}_values"]]
                )
                support = arrays[layout[arm][family + "_support"]]
                for name, raw in paths.items():
                    forward = np.asarray(raw, dtype=np.int64)
                    for direction, vertices in (
                        ("forward", forward),
                        ("reverse", np.r_[forward[:1], forward[:0:-1]]),
                    ):
                        cache[family, h, arm, name + "_" + direction] = (
                            None
                            if values is None or not support[vertices].all()
                            else scalar_diagnostic(values, vertices, coords)
                        )
                outer = np.asarray(paths["outer"], dtype=np.int64)
                primary = cache[family, h, arm, "outer_forward"]
                checks = {}
                for label, vertices in (
                    ("cyclic_shift_one", np.roll(outer, 1)),
                    ("stride2_offset0", outer[::2]),
                    ("stride2_offset1", outer[1::2]),
                ):
                    checks[label] = (
                        None
                        if values is None or not support[vertices].all()
                        else scalar_diagnostic(values, vertices, coords)
                    )
                cyclic = checks["cyclic_shift_one"]
                if primary is not None and (
                    cyclic is None or not same_estimate(primary, cyclic)
                ):
                    raise ValueError("cyclic-origin estimator mismatch")
                controls[family][h][arm] = {
                    "primary": primary,
                    "checks": checks,
                    "inherits_original_graph_admission": False,
                    "new_observations": False,
                }
    cells = []
    swap_checks = 0
    swap = {"A_only_admitted": "B_only_admitted", "B_only_admitted": "A_only_admitted"}
    for cell in report["paired_cells"]:
        family = cell["field_graph"]
        loops = {}
        for loop, hypotheses in cell["loops"].items():
            loops[loop] = {}
            for h, pair in hypotheses.items():
                category = perturbation._category(pair["A"], pair["B"])
                exchanged = perturbation._category(pair["B"], pair["A"])
                if exchanged != swap.get(category, category):
                    raise ValueError("A/B exchange category mismatch")
                swap_checks += 1
                result = {"category": category, "exchanged_category": exchanged}
                for arm in ("A", "B"):
                    branch = pair[arm]
                    diagnostic = cache[family, h, arm, loop]
                    original = branch.get("diagnostic")
                    if original is not None:
                        if diagnostic is None or any(
                            not np.isclose(
                                original[k], diagnostic[k], rtol=1e-12, atol=1e-12
                            )
                            for k in ("minimum_amplitude", "maximum_edge_angle_rad")
                        ):
                            raise ValueError("original scalar diagnostic mismatch")
                        if (branch["state"] == "eligible") != diagnostic["reliable"]:
                            raise ValueError("original winding gate changed")
                    value = branch["value"]
                    winding = value["sampled_winding"] if value is not None else None
                    if branch["state"] == "eligible" and (
                        diagnostic is None or winding != diagnostic["sampled_winding"]
                    ):
                        raise ValueError("eligible original winding mismatch")
                    result[arm] = {
                        "state": branch["state"],
                        "reason": branch["reason"],
                        "sampled_winding": winding,
                        "field_sha256": branch["field_sha256"],
                        "diagnostic": diagnostic,
                    }
                loops[loop][h] = result
        cells.append(
            {"field_graph": family, "loop_graph": cell["loop_graph"], "loops": loops}
        )
    return {
        "cells": cells,
        "sampling_controls": controls,
        "label_exchange_checks": swap_checks,
        "derived_estimator_checks": 36,
        "amplitude_floor": AMPLITUDE_FLOOR,
        "branch_margin_rad": BRANCH_MARGIN_RAD,
        "selected_from_observed_outer_A_only_points": True,
        "scientific_authority": False,
    }


def measure_pair(spec, output=None):
    started = time.monotonic()
    if output is not None:
        output = Path(output)
        output.mkdir(parents=True, exist_ok=False)
    report, arrays = strength.clone(
        strength.measure_pair, StrengthSpec=ZoomSpec, SCHEMA=SCHEMA, __file__=__file__
    )(spec)
    report["zoom"] = located_diagnostics(report, arrays)
    report["scope"]["targeted_exploration_selected_after_predecessor_readout"] = True
    report["source_sha256"][Path(strength.__file__).name] = (
        strength.reference.sensitivity._file_hash(strength.__file__)
    )
    if output is not None:
        artifact = output / "arrays.npz"
        with artifact.open("xb") as stream:
            np.savez_compressed(stream, **arrays)
        report["array_artifact"] = {
            "file": artifact.name,
            "bytes": artifact.stat().st_size,
            "sha256": strength.reference.sensitivity._file_hash(artifact),
        }
    report["timing"]["total_with_zoom_seconds"] = time.monotonic() - started
    report["peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (
        1 if platform.system() == "Darwin" else 1024
    )
    if output is not None:
        strength.reference.predecessor._write(output / "report.json", report)
    return report, arrays


def compact_report(report):
    result = strength.clone(strength.compact_report, SCHEMA=SCHEMA)(report)
    result["zoom"] = report["zoom"]
    return result


def sampled_runs(alphas, categories):
    """All contiguous sampled categories, including unavailable positions."""
    if (
        len(alphas) != len(categories)
        or not alphas
        or any(a >= b for a, b in zip(alphas, alphas[1:]))
    ):
        raise ValueError("matched ordered strength/category sequence required")
    result, start = [], 0
    for stop in range(1, len(alphas) + 1):
        if stop < len(alphas) and categories[stop] == categories[start]:
            continue
        result.append(
            {
                "category": categories[start],
                "sample_count": stop - start,
                "first_sample": alphas[start],
                "last_sample": alphas[stop - 1],
                "preceding_sample": None if start == 0 else alphas[start - 1],
                "following_sample": None if stop == len(alphas) else alphas[stop],
                "continuous_interval_certified": False,
            }
        )
        start = stop
    return result
