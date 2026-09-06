"""Frozen-reference spatial fidelity; truth is a scorer, never a locator.

This is a synthetic instrument bench, not graph admission or model evidence.
All new observations come from probes, not interpolated predecessor residuals.
"""

from __future__ import annotations

from itertools import product
import json

import numpy as np
from scipy.ndimage import label
from scipy.optimize import linear_sum_assignment

import prototype_p4_one_arm_zoom_v0_1 as zoom
from p4_dense_moment_adapter_v0_1 import DenseMomentAdapter
from spirallens.core import canonical_json_sha256
from spirallens.graphs.common import array_sha256

SCHEMA = "spirallens.p4-spatial-fidelity.v0.1"
FAMILIES = zoom.perturbation.FAMILIES
HYPOTHESES = ("F2", "F4")
REFERENCES = ("ideal", "A", "B")
COUNTS = (256, 512, 1024)
CELL_COUNTS = (64, 128, 256)
FIXTURES = ("double", "wide", "close", "reverse", "dipole", "constant", "zero")
FLOOR = 1e-6
IDEAL = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
FRAME = np.eye(3)[:, :2]


def finite(values, *, columns=None):
    result = np.asarray(values, dtype=np.float64)
    if not np.isfinite(result).all() or result.size == 0:
        raise ValueError("nonempty finite observations required")
    if columns is not None and (result.ndim != 2 or result.shape[1] != columns):
        raise ValueError("observation shape changed")
    return result


def complex_values(values):
    values = finite(values, columns=2)
    return values[:, 0] + 1j * values[:, 1]


def vector_values(values):
    values = np.asarray(values)
    if values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError("finite complex vector required")
    return np.column_stack((values.real, values.imag))


def square_boundary(count):
    if type(count) is not int or count < 8 or count % 4:
        raise ValueError("square count must be an integer multiple of four")
    t = np.arange(count // 4, dtype=np.float64) * (8.0 / count)
    return np.concatenate(
        [
            np.column_stack((-1 + t, np.full_like(t, -1))),
            np.column_stack((np.full_like(t, 1), -1 + t)),
            np.column_stack((1 - t, np.full_like(t, 1))),
            np.column_stack((np.full_like(t, -1), 1 - t)),
        ]
    )


def grid_coords(cells):
    if type(cells) is not int or cells < 4:
        raise ValueError("integer cell count >=4 required")
    axis = np.linspace(-1.0, 1.0, cells + 1)
    x, y = np.meshgrid(axis, axis, indexing="xy")
    return np.column_stack((x.ravel(), y.ravel()))


def measure(coords, residual, *, probe_count=128):
    """Fresh exact-cube probes, measured by the existing dense adapter."""
    coords = finite(coords, columns=2)
    residual = np.asarray(residual, dtype=np.complex128)
    if residual.shape != (len(coords),) or not np.isfinite(residual).all():
        raise ValueError("finite residual at every observation required")
    if type(probe_count) is not int or probe_count < 8 or probe_count % 8:
        raise ValueError("whole exact eight-cube repeats required")
    adapter = DenseMomentAdapter()
    cube = np.array(list(product((-1.0, 1.0), repeat=3)))
    result = {h: np.empty_like(coords) for h in HYPOTHESES}
    for start in range(0, len(coords), 512):
        stop = min(start + 512, len(coords))
        full = complex_values(coords[start:stop]) + residual[start:stop]
        values = vector_values(full)
        frames = np.broadcast_to(FRAME, (len(full), 3, 2))
        tensor = zoom.strength.reference.predecessor.tensor_from_values(values)
        covariance = (1 + np.abs(full))[:, None, None] * np.eye(3)
        covariance += frames @ tensor @ np.swapaxes(frames, -1, -2)
        root = np.linalg.cholesky(covariance)
        mean = np.einsum("ndi,ni->nd", frames, values)
        probes = mean[:, None, :] + np.einsum("pi,ndi->npd", cube, root)
        probes = np.tile(probes, (1, probe_count // 8, 1))
        measured = adapter.moments(frames, probes)
        for h in HYPOTHESES:
            result[h][start:stop] = measured[h]
    return result


def subtract(full, coords, coefficients):
    coords, full = finite(coords, columns=2), finite(full, columns=2)
    coefficients = finite(coefficients, columns=2)
    if full.shape != coords.shape or coefficients.shape != (3, 2):
        raise ValueError("fixed reference shape mismatch")
    return full - np.column_stack((np.ones(len(coords)), coords)) @ coefficients


def diagnostic(values, coords, *, reverse=False):
    rows = np.arange(len(coords), dtype=np.int64)
    if reverse:
        rows = rows[::-1]
    return zoom.scalar_diagnostic(values, rows, coords)


def errors(prediction, target):
    a, b = complex_values(prediction), complex_values(target)
    if a.shape != b.shape:
        raise ValueError("error denominator changed")
    valid = (np.abs(a) > FLOOR) & (np.abs(b) > FLOOR)
    phase = np.angle(a[valid] * np.conj(b[valid]))
    return {
        "points": len(a),
        "complex_rmse": float(np.sqrt(np.mean(np.abs(a - b) ** 2))),
        "maximum_vector_error": float(np.max(np.abs(a - b))),
        "amplitude_rmse": float(np.sqrt(np.mean((np.abs(a) - np.abs(b)) ** 2))),
        "phase_points": int(valid.sum()),
        "phase_rms_deg": float(np.rad2deg(np.sqrt(np.mean(phase**2))))
        if valid.any()
        else None,
        "phase_max_deg": float(np.rad2deg(np.max(np.abs(phase))))
        if valid.any()
        else None,
    }


def interpolate_boundary(values, audit_t):
    """Prediction only; never used as a new observed field or winding input."""
    values = finite(values, columns=2)
    audit_t = finite(audit_t)
    if audit_t.ndim != 1 or np.any(audit_t < 0) or np.any(audit_t >= 1):
        raise ValueError("audit positions must lie in [0,1)")
    scaled = audit_t * len(values)
    left = np.floor(scaled).astype(int)
    weight = scaled - left
    return (1 - weight[:, None]) * values[left] + weight[:, None] * values[
        (left + 1) % len(values)
    ]


def checked_reference(report, arrays):
    """Read-only full-evidence replay and fixed-frame/reference extraction."""
    if report["schema_version"] not in (zoom.SCHEMA, zoom.strength.SCHEMA):
        raise ValueError("unregistered predecessor schema")
    zoom.strength.clone(
        zoom.perturbation.analyze_pair, INPUT_SCHEMA=report["schema_version"]
    )(report, arrays)
    layout = report["array_layout"]["arms"]
    coords = arrays[layout["A"]["coords"]]
    if coords.shape != (4225, 2):
        raise ValueError("side65 predecessor required")
    coefficients = {f: {a: {} for a in ("A", "B")} for f in FAMILIES}
    seals = {}
    for f in FAMILIES:
        for arm in ("A", "B"):
            frame = arrays[layout[arm][f + "_frames"]]
            if not np.array_equal(frame, np.broadcast_to(FRAME, frame.shape)):
                raise ValueError(
                    "new coordinates require the declared constant xy frame"
                )
            if not arrays[layout[arm][f + "_support"]].all():
                raise ValueError("reference substrate has unsupported points")
            baseline = report["arms"][arm]["rows"][f]["baseline"]
            seals[f + "/" + arm] = baseline["seal_sha256"]
            for h in HYPOTHESES:
                c = finite(baseline["coefficients"][h], columns=2)
                if not np.array_equal(
                    c, arrays[f"baseline_{arm}_{f}_{h}_coefficients"]
                ):
                    raise ValueError(
                        "reference coefficients differ from retained arrays"
                    )
                predicted = np.column_stack((np.ones(len(coords)), coords)) @ c
                if not np.array_equal(
                    predicted, arrays[layout[arm][f + "_local_affine_" + h + "_values"]]
                ):
                    raise ValueError(
                        "reference does not reproduce the sealed affine field"
                    )
                coefficients[f][arm][h] = c
    return coefficients, {"baseline_seals": seals, "frames_verified": True}


def outer_unit(report, arrays):
    coefficients, receipt = checked_reference(report, arrays)
    alpha = report["spec"]["signal_strength"]
    audit_coords = square_boundary(2048)[1::2]
    audit_t = np.arange(1, 2048, 2) / 2048
    truth = vector_values(0.25 * alpha * complex_values(audit_coords) ** 2)
    full_audit = measure(audit_coords, complex_values(truth))
    retained = {"audit_coords": audit_coords, "audit_truth": truth}
    records, paired, anchor_checks = [], [], []
    for h in HYPOTHESES:
        retained["audit_full_" + h] = full_audit[h]
    for count in COUNTS:
        coords = square_boundary(count)
        full = measure(coords, 0.25 * alpha * complex_values(coords) ** 2)
        retained[f"coords_{count}"] = coords
        for h in HYPOTHESES:
            retained[f"full_{count}_{h}"] = full[h]
        for family in FAMILIES:
            for h in HYPOTHESES:
                arm_audit = {}
                for arm in ("A", "B"):
                    c = coefficients[family][arm][h]
                    values = subtract(full[h], coords, c)
                    audit = subtract(full_audit[h], audit_coords, c)
                    arm_audit[arm] = audit
                    key = f"{family}/{h}/{arm}/{count}"
                    retained[key] = values
                    retained[f"coefficient/{family}/{h}/{arm}"] = c
                    if count == 256:
                        layout = report["array_layout"]["arms"][arm]
                        vertices = np.asarray(
                            report["arms"][arm]["loop_vertices"]["outer"]
                        )
                        old_coords = arrays[layout["coords"]][vertices]
                        old_full = arrays[layout[family + "_full_" + h + "_values"]][
                            vertices
                        ]
                        old_values = arrays[
                            layout[family + "_residual_affine_" + h + "_values"]
                        ][vertices]
                        delta = max(
                            float(np.max(np.abs(values - old_values))),
                            float(np.max(np.abs(full[h] - old_full))),
                        )
                        if not np.array_equal(coords, old_coords) or delta > 1e-12:
                            raise ValueError(
                                "fresh 256-point observation failed anchor parity"
                            )
                        if not zoom.same_estimate(
                            diagnostic(values, coords),
                            diagnostic(old_values, old_coords),
                        ):
                            raise ValueError("anchor scalar state/reasons changed")
                        anchor_checks.append({"key": key, "maximum_error": delta})
                    prediction = interpolate_boundary(values, audit_t)
                    for reverse in (False, True):
                        records.append(
                            {
                                "family": family,
                                "hypothesis": h,
                                "arm": arm,
                                "count": count,
                                "orientation": "reverse" if reverse else "forward",
                                "diagnostic": diagnostic(
                                    values, coords, reverse=reverse
                                ),
                                "sampling_error": errors(prediction, audit),
                                "reference_error": errors(audit, truth),
                                "total_reconstruction_error": errors(prediction, truth),
                            }
                        )
                paired.append(
                    {
                        "family": family,
                        "hypothesis": h,
                        "count": count,
                        "A_B_error": errors(arm_audit["A"], arm_audit["B"]),
                    }
                )
    return {
        "lane": "outer",
        "spec": report["spec"],
        "readouts": records,
        "paired": paired,
        "anchor_checks": anchor_checks,
        "reference": receipt,
        "readout_count": len(records),
        "new_reference_fits": 0,
        "scientific_authority": False,
        "graph_admission_inherited": False,
    }, retained


def geometry(seed, fixture):
    if type(seed) is not int or seed < 0 or fixture not in FIXTURES:
        raise ValueError("registered geometry family and nonnegative seed required")
    rng = np.random.default_rng(np.random.SeedSequence([seed, 0x50345346]))
    xy = rng.uniform(-0.25, 0.25, 2)
    angle = float(rng.uniform(0, np.pi))
    c = complex(*xy)
    separation = 0.08 if fixture == "close" else 0.4
    d = separation / 2 * np.exp(1j * angle)
    centers = [c] if fixture == "double" else [c + d, c - d]
    charges = (
        [2]
        if fixture == "double"
        else [-1, -1]
        if fixture == "reverse"
        else [1, -1]
        if fixture == "dipole"
        else [1, 1]
    )
    if fixture in ("constant", "zero"):
        centers, charges = [], []
    return {
        "center": xy.tolist(),
        "angle": angle,
        "fixture": fixture,
        "centers": [[z.real, z.imag] for z in centers],
        "charges": charges,
        "everywhere_degenerate": fixture == "zero",
        "geometry_seed": seed,
    }


def injected_field(coords, construction):
    z = complex_values(coords)
    c = complex(*construction["center"])
    fixture = construction["fixture"]
    d = (0.04 if fixture == "close" else 0.2) * np.exp(1j * construction["angle"])
    if fixture == "double":
        return 0.025 * (z - c) ** 2
    if fixture in ("wide", "close", "reverse"):
        value = 0.025 * (z - c - d) * (z - c + d)
        return np.conj(value) if fixture == "reverse" else value
    if fixture == "dipole":
        return 0.025 * (z - c - d) * np.conj(z - c + d)
    if fixture == "constant":
        return np.full(len(z), 0.025 * np.exp(1j * construction["angle"]))
    if fixture == "zero":
        return np.zeros(len(z), dtype=np.complex128)
    raise ValueError("unknown construction")


def locate(coords, values):
    """Charge-blind cells only. No field function, truth or count argument."""
    coords, values = finite(coords, columns=2), finite(values, columns=2)
    side = int(round(np.sqrt(len(coords))))
    if (
        values.shape != coords.shape
        or side**2 != len(coords)
        or not np.array_equal(coords, grid_coords(side - 1))
    ):
        raise ValueError("complete ordered square-grid observations required")
    base = {
        "input_sha256": array_sha256(values),
        "coords_sha256": array_sha256(coords),
        "cells": side - 1,
        "scientific_authority": False,
        "components": [],
    }
    if np.max(np.linalg.norm(values, axis=1)) <= FLOOR:
        base.update(
            state="globally_below_floor", candidate_cell_count=0, mask_sha256=None
        )
    else:
        field = values.reshape(side, side, 2)
        corners = np.stack(
            (field[:-1, :-1], field[:-1, 1:], field[1:, :-1], field[1:, 1:])
        )
        mask = ((corners.min(axis=0) <= 1e-12) & (corners.max(axis=0) >= -1e-12)).all(
            axis=-1
        )
        labels, count = label(mask, structure=np.ones((3, 3), dtype=bool))
        cells = side - 1
        for component_id in range(1, count + 1):
            ys, xs = np.where(labels == component_id)
            x0, x1, y0, y1 = (
                int(xs.min()),
                int(xs.max()) + 1,
                int(ys.min()),
                int(ys.max()) + 1,
            )
            box = [x0, x1, y0, y1]
            expanded = [
                max(0, x0 - 1),
                min(cells, x1 + 1),
                max(0, y0 - 1),
                min(cells, y1 + 1),
            ]
            reasons = []
            if x0 == 0 or x1 == cells or y0 == 0 or y1 == cells:
                reasons.append("boundary-clipped")
            if max(x1 - x0, y1 - y0) * 2 / cells > 0.5:
                reasons.append("nonlocal-candidate")
            base["components"].append(
                {
                    "id": component_id,
                    "cell_count": len(xs),
                    "box_indices": box,
                    "loop_box_indices": expanded,
                    "box": [
                        -1 + 2 * x0 / cells,
                        -1 + 2 * x1 / cells,
                        -1 + 2 * y0 / cells,
                        -1 + 2 * y1 / cells,
                    ],
                    "position": [
                        -1 + 2 * float(np.mean(xs + 0.5)) / cells,
                        -1 + 2 * float(np.mean(ys + 0.5)) / cells,
                    ],
                    "unresolved_reasons": reasons,
                }
            )
        for i, component in enumerate(base["components"]):
            a = component["loop_box_indices"]
            for other in base["components"][i + 1 :]:
                b = other["loop_box_indices"]
                if max(a[0], b[0]) <= min(a[1], b[1]) and max(a[2], b[2]) <= min(
                    a[3], b[3]
                ):
                    component["unresolved_reasons"].append(
                        "overlapping-component-loops"
                    )
                    other["unresolved_reasons"].append("overlapping-component-loops")
        base.update(
            state="located",
            candidate_cell_count=int(mask.sum()),
            mask_sha256=array_sha256(mask),
        )
    return {**base, "candidate_seal_sha256": canonical_json_sha256(base)}


def rectangle_vertices(side, box):
    x0, x1, y0, y1 = box
    pairs = (
        [(x, y0) for x in range(x0, x1)]
        + [(x1, y) for y in range(y0, y1)]
        + [(x, y1) for x in range(x1, x0, -1)]
        + [(x0, y) for y in range(y1, y0, -1)]
    )
    return np.array([y * side + x for x, y in pairs], dtype=np.int64)


def read_local_loops(coords, values, candidates):
    """The sealed locator result is consumed before any winding read."""
    base = {k: v for k, v in candidates.items() if k != "candidate_seal_sha256"}
    if canonical_json_sha256(base) != candidates["candidate_seal_sha256"]:
        raise ValueError("candidate seal changed before charge read")
    if (
        array_sha256(values) != base["input_sha256"]
        or array_sha256(coords) != base["coords_sha256"]
    ):
        raise ValueError("candidate field changed before charge read")
    side = base["cells"] + 1
    records = []
    for candidate in base["components"]:
        indices = rectangle_vertices(side, candidate["loop_box_indices"])
        readout = diagnostic(values[indices], coords[indices])
        reasons = sorted(
            set(candidate["unresolved_reasons"] + readout["failure_reasons"])
        )
        records.append(
            {
                **candidate,
                "diagnostic": readout,
                "unresolved_reasons": reasons,
                "resolved_charged_component": not reasons
                and readout["sampled_winding"] != 0,
            }
        )
    outer = rectangle_vertices(side, [0, side - 1, 0, side - 1])
    return {
        "candidate_seal_sha256": candidates["candidate_seal_sha256"],
        "state": base["state"],
        "components": records,
        "outer": diagnostic(values[outer], coords[outer]),
        "chronology": ["candidate-sealed", "component-loops-read", "outer-loop-read"],
        "scientific_authority": False,
    }


def score(reconstruction, truth):
    """Truth is read only after the entire reconstruction has been produced."""
    candidates = [
        c for c in reconstruction["components"] if c["resolved_charged_component"]
    ]
    actual = np.asarray([c["position"] for c in candidates]).reshape(-1, 2)
    expected = np.asarray(truth["centers"]).reshape(-1, 2)
    n, m = len(actual), len(expected)
    # Dummy assignments cost 0.10/2 on each side; a longer match is forbidden.
    cost = np.full((n + m, n + m), 1e6)
    distances = np.linalg.norm(actual[:, None, :] - expected[None, :, :], axis=-1)
    cost[:n, :m] = np.where(distances <= 0.10, distances, 1e6)
    cost[:n, m:] = 0.05
    cost[n:, :m] = 0.05
    cost[n:, m:] = 0
    rows, cols = linear_sum_assignment(cost)
    matches = []
    for i, j in zip(rows, cols, strict=True):
        if i < n and j < m and distances[i, j] <= 0.10:
            matches.append(
                {
                    "candidate_id": candidates[i]["id"],
                    "truth_index": int(j),
                    "distance": float(distances[i, j]),
                    "measured_charge": candidates[i]["diagnostic"]["sampled_winding"],
                    "expected_charge": truth["charges"][j],
                    "charge_correct": candidates[i]["diagnostic"]["sampled_winding"]
                    == truth["charges"][j],
                }
            )
    return {
        "truth_center_count": m,
        "candidate_count": len(reconstruction["components"]),
        "resolved_charged_count": n,
        "matches": matches,
        "missed_truth_count": m - len(matches),
        "false_positive_count": n - len(matches),
        "exact_local_structure": len(matches) == n == m
        and all(k["charge_correct"] for k in matches),
        "maximum_matched_distance": max((k["distance"] for k in matches), default=None),
        "outer_charge_correct": reconstruction["outer"]["sampled_winding"]
        == sum(truth["charges"])
        if not truth["everywhere_degenerate"]
        else None,
        "everywhere_degenerate_truth": truth["everywhere_degenerate"],
        "truth_read_after_reconstruction": True,
    }


def local_unit(report, arrays, *, fixture, geometry_seed, cells):
    coefficients, receipt = checked_reference(report, arrays)
    if report["spec"]["signal_strength"] != 0.1:
        raise ValueError("local lane freezes alpha0.1 references")
    for f in FAMILIES[1:]:
        for arm in ("A", "B"):
            for h in HYPOTHESES:
                if not np.array_equal(
                    coefficients[f][arm][h], coefficients[FAMILIES[0]][arm][h]
                ):
                    raise ValueError("cannot deduplicate distinct field-row references")
    coords = grid_coords(cells)
    construction = geometry(geometry_seed, fixture)
    injection = injected_field(coords, construction)
    full = measure(coords, injection)
    retained = {"coords": coords, "injected_truth": vector_values(injection)}
    records = []
    for h in HYPOTHESES:
        retained["full_" + h] = full[h]
        for arm in REFERENCES:
            c = IDEAL if arm == "ideal" else coefficients[FAMILIES[0]][arm][h]
            values = subtract(full[h], coords, c)
            retained[arm + "_" + h] = values
            retained["coefficient_" + arm + "_" + h] = c
            candidates = locate(coords, values)
            reconstruction = read_local_loops(coords, values, candidates)
            # No oracle object is an input to either preceding function.
            scoring = score(reconstruction, construction)
            records.append(
                {
                    "hypothesis": h,
                    "reference": arm,
                    "family_aliases": list(FAMILIES),
                    "candidates": candidates,
                    "reconstruction": reconstruction,
                    "score": scoring,
                    "field_error": errors(values, vector_values(injection)),
                }
            )
    return {
        "lane": "local",
        "fixture": fixture,
        "geometry_seed": geometry_seed,
        "reference_seed": report["spec"]["seed"],
        "cells": cells,
        "truth": construction,
        "records": records,
        "reference": receipt,
        "distinct_reconstructions": len(records),
        "row_addressed_records": len(records) * len(FAMILIES),
        "new_reference_fits": 0,
        "scientific_authority": False,
    }, retained


def verify_replay(report, arrays):
    """Regenerate every reported measurement from retained field arrays."""
    if report["lane"] == "outer":
        for r in report["readouts"]:
            f, h, a, n = (r[k] for k in ("family", "hypothesis", "arm", "count"))
            coords, values = arrays[f"coords_{n}"], arrays[f"{f}/{h}/{a}/{n}"]
            audit = subtract(
                arrays["audit_full_" + h],
                arrays["audit_coords"],
                arrays[f"coefficient/{f}/{h}/{a}"],
            )
            expected = diagnostic(values, coords, reverse=r["orientation"] == "reverse")
            prediction = interpolate_boundary(values, np.arange(1, 2048, 2) / 2048)
            if (
                expected != r["diagnostic"]
                or errors(prediction, audit) != r["sampling_error"]
                or errors(audit, arrays["audit_truth"]) != r["reference_error"]
                or errors(prediction, arrays["audit_truth"])
                != r["total_reconstruction_error"]
            ):
                raise ValueError("outer readout failed raw-array replay")
        if len(report["readouts"]) != 72 or len(report["anchor_checks"]) != 12:
            raise ValueError("outer denominator changed")
    elif report["lane"] == "local":
        for r in report["records"]:
            values = arrays[r["reference"] + "_" + r["hypothesis"]]
            candidates = locate(arrays["coords"], values)
            reconstruction = read_local_loops(arrays["coords"], values, candidates)
            if (
                candidates != r["candidates"]
                or reconstruction != r["reconstruction"]
                or score(reconstruction, report["truth"]) != r["score"]
                or errors(values, arrays["injected_truth"]) != r["field_error"]
            ):
                raise ValueError("local reconstruction failed raw-array replay")
        if len(report["records"]) != 6 or report["row_addressed_records"] != 18:
            raise ValueError("local denominator changed")
    else:
        raise ValueError("unknown lane")
    # Reject non-finite or accidental ndarray content before persistence.
    json.dumps(report, allow_nan=False)
    return True
