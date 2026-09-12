"""Observe a background-only reference; propagate its empirical uncertainty.

The calibration estimand is explicitly new. Geometry truth is not a fitter,
locator, reference selector or uncertainty-interval calibration procedure.
"""

from __future__ import annotations

from collections import Counter
from itertools import product
import json

import numpy as np

import prototype_p4_spatial_fidelity_v0_1 as spatial

SCHEMA = "spirallens.p4-reference-uncertainty.v0.1"
KS = (1, 4, 16, 64, 256)
REFERENCE_SEEDS = tuple(range(200, 216))
GEOMETRY_SEEDS = tuple(range(400, 404))
ALPHAS = (0.08, 0.10)
TAG = 0x50345255
FIT = spatial.zoom.strength.reference.FIT_COORDS.astype(np.float64)
HELDOUT = spatial.zoom.strength.reference.VALIDATION_COORDS.astype(np.float64)
HASH = spatial.array_sha256
SEAL = spatial.canonical_json_sha256


def background_probes(coords):
    """The same probe construction, with background z and no injected residual."""
    coords = spatial.finite(coords, columns=2)
    frames = np.broadcast_to(spatial.FRAME, (len(coords), 3, 2))
    cube = np.array(list(product((-1.0, 1.0), repeat=3)))
    z = spatial.complex_values(coords)
    tensor = spatial.zoom.strength.reference.predecessor.tensor_from_values(coords)
    covariance = (1 + np.abs(z))[:, None, None] * np.eye(3)
    covariance += frames @ tensor @ np.swapaxes(frames, -1, -2)
    mean = np.einsum("ndi,ni->nd", frames, coords)
    root = np.linalg.cholesky(covariance)
    return np.tile(mean[:, None, :] + np.einsum("pi,ndi->npd", cube, root), (1, 16, 1))


def calibration_draws(seed, repeats):
    if (
        type(seed) is not int
        or not 0 <= seed < 2**32
        or type(repeats) is not int
        or not 1 <= repeats <= 256
    ):
        raise ValueError("uint32 seed and1..256 repeats required")
    clean = background_probes(FIT)
    probes = np.empty((repeats, 5, 128, 3), dtype=np.float64)
    for repeat in range(repeats):
        noise = np.random.default_rng(
            np.random.SeedSequence([seed, TAG, repeat])
        ).normal(size=(5, 128, 3))
        probes[repeat] = clean + 0.03 * noise
    return probes


def fit_repeats(probes):
    if (
        not isinstance(probes, np.ndarray)
        or probes.dtype != np.float64
        or probes.ndim != 4
        or probes.shape[1:] != (5, 128, 3)
        or not 1 <= len(probes) <= 256
        or not np.isfinite(probes).all()
    ):
        raise ValueError("finite repeat x5 x128 x3 calibration probes required")
    observations = probes.reshape(-1, 128, 3)
    frames = np.broadcast_to(spatial.FRAME, (len(observations), 3, 2))
    moments = spatial.DenseMomentAdapter().moments(frames, observations)
    design = np.column_stack((np.ones(5), FIT))
    values, coefficients = {}, {}
    for h in spatial.HYPOTHESES:
        values[h] = moments[h].reshape(len(probes), 5, 2)
        rhs = values[h].transpose(1, 0, 2).reshape(5, -1)
        fitted = np.linalg.lstsq(design, rhs, rcond=None)[0]
        coefficients[h] = fitted.reshape(3, len(probes), 2).transpose(1, 0, 2)
    return values, coefficients


def prefix_references(seed, probes, values, coefficients, ks):
    if (
        not ks
        or any(type(k) is not int or k not in KS or k > len(probes) for k in ks)
        or tuple(sorted(set(ks))) != tuple(ks)
    ):
        raise ValueError("unique ordered registered prefixes required")
    refs = []
    for k in ks:
        for h in spatial.HYPOTHESES:
            c = coefficients[h][:k].mean(axis=0)
            ref = {
                "reference_seed": seed,
                "k": k,
                "hypothesis": h,
                "coefficients": c.tolist(),
                "coefficient_sha256": HASH(c),
                "probe_prefix_sha256": HASH(probes[:k]),
                "moment_prefix_sha256": HASH(values[h][:k]),
                "fit_coords_sha256": HASH(FIT),
                "observation_frame_sha256": HASH(spatial.FRAME),
                "estimand": "mean-of-separately-fitted-background-only-references",
                "scientific_authority": False,
            }
            refs.append({**ref, "reference_seal_sha256": SEAL(ref)})
    return refs


def calibrate(seed, *, repeats=256, ks=KS):
    probes = calibration_draws(seed, repeats)
    values, coefficients = fit_repeats(probes)
    refs = prefix_references(seed, probes, values, coefficients, ks)
    arrays = {"probes": probes, "fit_coords": FIT}
    for h in spatial.HYPOTHESES:
        arrays["moments_" + h], arrays["fits_" + h] = values[h], coefficients[h]
    return {
        "lane": "calibration",
        "reference_seed": seed,
        "repeats": repeats,
        "ks": list(ks),
        "references": refs,
        "schema_version": SCHEMA,
        "geometry_observed": False,
        "heldout_observed": False,
        "scientific_authority": False,
    }, arrays


def verify_calibration(report, arrays):
    seed, repeats = report["reference_seed"], report["repeats"]
    probes = calibration_draws(seed, repeats)
    if not np.array_equal(arrays["probes"], probes) or not np.array_equal(
        arrays["fit_coords"], FIT
    ):
        raise ValueError("calibration stream or ordered stencil changed")
    values, coefficients = fit_repeats(arrays["probes"])
    for h in spatial.HYPOTHESES:
        if not np.array_equal(values[h], arrays["moments_" + h]) or not np.array_equal(
            coefficients[h], arrays["fits_" + h]
        ):
            raise ValueError("calibration moments/fits do not replay")
    if (
        prefix_references(seed, probes, values, coefficients, report["ks"])
        != report["references"]
    ):
        raise ValueError(
            "prefix references do not replay from calibration observations"
        )
    if (
        report["geometry_observed"] is not False
        or report["heldout_observed"] is not False
    ):
        raise ValueError("calibration consumed downstream observations")
    return True


def validate_reference(ref):
    body = {k: v for k, v in ref.items() if k != "reference_seal_sha256"}
    c = spatial.finite(ref["coefficients"], columns=2)
    if (
        c.shape != (3, 2)
        or HASH(c) != ref["coefficient_sha256"]
        or SEAL(body) != ref["reference_seal_sha256"]
    ):
        raise ValueError("reference seal or coefficient binding changed")
    if (
        ref["scientific_authority"] is not False
        or ref["fit_coords_sha256"] != HASH(FIT)
        or ref["observation_frame_sha256"] != HASH(spatial.FRAME)
    ):
        raise ValueError("reference frame/stencil/scope changed")
    return c


def measured_shape(reconstruction):
    """No truth input. Missing components never imply center zero or span zero."""
    resolved = [
        c for c in reconstruction["components"] if c["resolved_charged_component"]
    ]
    count = len(resolved)
    charges = [c["diagnostic"]["sampled_winding"] for c in resolved]
    positions = np.array([c["position"] for c in resolved]).reshape(-1, 2)
    centroid = (
        np.average(positions, weights=np.abs(charges), axis=0).tolist()
        if count
        else None
    )
    span = (
        float(np.linalg.norm(positions[:, None] - positions[None, :], axis=-1).max())
        if count
        else None
    )
    return {
        "resolved_count": count,
        "charge_pattern": sorted(charges),
        "absolute_charge_centroid": centroid,
        "span": span,
        "signed_charge_sum": sum(charges) if count else None,
        "outer_winding": reconstruction["outer"]["sampled_winding"],
    }


def shape_errors(observable, truth):
    centers = np.asarray(truth["centers"]).reshape(-1, 2)
    if not len(centers):
        return {
            "centroid_error": None,
            "span_error": None,
            "truth_centroid": None,
            "truth_span": None,
        }
    centroid = np.average(centers, weights=np.abs(truth["charges"]), axis=0)
    span = float(np.linalg.norm(centers[:, None] - centers[None, :], axis=-1).max())
    return {
        "centroid_error": float(
            np.linalg.norm(
                np.asarray(observable["absolute_charge_centroid"]) - centroid
            )
        )
        if observable["absolute_charge_centroid"] is not None
        else None,
        "span_error": abs(observable["span"] - span)
        if observable["span"] is not None
        else None,
        "truth_centroid": centroid.tolist(),
        "truth_span": span,
    }


def strict_score(reconstruction, truth):
    """Secondary0.01 matching; never changes the original primary scorer."""
    candidates = [
        c for c in reconstruction["components"] if c["resolved_charged_component"]
    ]
    actual = np.array([c["position"] for c in candidates]).reshape(-1, 2)
    expected = np.array(truth["centers"]).reshape(-1, 2)
    n, m = len(actual), len(expected)
    distance = np.linalg.norm(actual[:, None] - expected[None, :], axis=-1)
    cost = np.full((n + m, n + m), 1e6)
    cost[:n, :m] = np.where(distance <= 0.01, distance, 1e6)
    cost[:n, m:], cost[n:, :m], cost[n:, m:] = 0.005, 0.005, 0
    rows, cols = spatial.linear_sum_assignment(cost)
    matches = [
        (i, j)
        for i, j in zip(rows, cols, strict=True)
        if i < n and j < m and distance[i, j] <= 0.01
    ]
    return {
        "match_tolerance": 0.01,
        "matches": len(matches),
        "false_positive_count": n - len(matches),
        "missed_truth_count": m - len(matches),
        "exact_local_structure": len(matches) == n == m
        and all(
            candidates[i]["diagnostic"]["sampled_winding"] == truth["charges"][j]
            for i, j in matches
        ),
    }


def reference_key(ref):
    return f"s{ref['reference_seed']}-k{ref['k']}-{ref['hypothesis']}"


def reconstruct_record(coords, full, c, truth):
    values = spatial.subtract(full, coords, c)
    candidates = spatial.locate(coords, values)
    reconstruction = spatial.read_local_loops(coords, values, candidates)
    observable = measured_shape(reconstruction)
    return {
        "candidates": candidates,
        "reconstruction": reconstruction,
        "observable": observable,
        "shape_error": shape_errors(observable, truth),
        "score": spatial.score(reconstruction, truth),
        "secondary_score": strict_score(reconstruction, truth),
    }


def local_unit(references, bank_seal, *, alpha, geometry_seed, fixture, cells=256):
    if (
        alpha not in ALPHAS
        or isinstance(alpha, bool)
        or fixture not in spatial.FIXTURES
    ):
        raise ValueError("registered strength and fixture required")
    keys = [reference_key(r) for r in references]
    if (
        len(set(keys)) != len(keys)
        or not references
        or not isinstance(bank_seal, str)
        or len(bank_seal) != 64
    ):
        raise ValueError("complete sealed unique reference bank required")
    # Validate the complete bank before generating/evaluating geometry or V.
    coefficients = {reference_key(r): validate_reference(r) for r in references}
    coords = spatial.grid_coords(cells)
    truth = spatial.geometry(geometry_seed, fixture)
    injection = spatial.injected_field(coords, truth) * (alpha / 0.1)
    full = spatial.measure(coords, injection)
    validation = spatial.measure(HELDOUT, np.zeros(len(HELDOUT)))
    design = np.column_stack((np.ones(len(HELDOUT)), HELDOUT))
    arrays = {
        "coords": coords,
        "injected_truth": spatial.vector_values(injection),
        "heldout_coords": HELDOUT,
    }
    records = []
    for h in spatial.HYPOTHESES:
        arrays["full_" + h], arrays["heldout_" + h] = full[h], validation[h]
        candidates = [
            {
                "hypothesis": h,
                "key": "ideal-" + h,
                "reference_seed": None,
                "k": None,
                "reference_seal_sha256": None,
            }
        ] + [dict(r, key=reference_key(r)) for r in references if r["hypothesis"] == h]
        for ref in candidates:
            key = ref["key"]
            c = spatial.IDEAL if ref["k"] is None else coefficients[key]
            arrays["coefficient-" + key] = c
            record = reconstruct_record(coords, full[h], c, truth)
            record.update(
                key=key,
                hypothesis=h,
                reference_seed=ref["reference_seed"],
                k=ref["k"],
                reference_seal_sha256=ref["reference_seal_sha256"],
                coefficient_sha256=HASH(c),
                heldout_error=spatial.errors(design @ c, validation[h]),
            )
            records.append(record)
    return {
        "schema_version": SCHEMA,
        "lane": "geometry",
        "alpha": alpha,
        "geometry_seed": geometry_seed,
        "fixture": fixture,
        "cells": cells,
        "truth": truth,
        "records": records,
        "bank_seal_sha256": bank_seal,
        "reference_keys": keys,
        "chronology": [
            "all-bank-references-validated",
            "evaluation-and-heldout-observed",
            "candidates-sealed-before-loops",
            "truth-scored-after-reconstruction",
        ],
        "scientific_authority": False,
        "graph_admission_inherited": False,
    }, arrays


def verify_local(report, arrays, references, bank_seal):
    expected_truth = spatial.geometry(report["geometry_seed"], report["fixture"])
    if report["truth"] != expected_truth or report["scientific_authority"] is not False:
        raise ValueError("truth-side construction or scope changed")
    if report["bank_seal_sha256"] != bank_seal or report["reference_keys"] != [
        reference_key(r) for r in references
    ]:
        raise ValueError("reference bank join changed")
    expected = {(h, None, None) for h in spatial.HYPOTHESES} | {
        (r["hypothesis"], r["reference_seed"], r["k"]) for r in references
    }
    keys = [(r["hypothesis"], r["reference_seed"], r["k"]) for r in report["records"]]
    if len(keys) != len(expected) or set(keys) != expected:
        raise ValueError("local reference/hypothesis denominator changed")
    refs = {reference_key(r): r for r in references}
    if not np.array_equal(
        arrays["coords"], spatial.grid_coords(report["cells"])
    ) or not np.array_equal(arrays["heldout_coords"], HELDOUT):
        raise ValueError("measurement coordinates changed")
    design = np.column_stack((np.ones(len(HELDOUT)), HELDOUT))
    injection = spatial.injected_field(arrays["coords"], expected_truth) * (
        report["alpha"] / 0.1
    )
    if not np.array_equal(arrays["injected_truth"], spatial.vector_values(injection)):
        raise ValueError("saved truth field changed")
    full = spatial.measure(arrays["coords"], injection)
    heldout = spatial.measure(HELDOUT, np.zeros(len(HELDOUT)))
    if any(
        not np.array_equal(arrays["full_" + h], full[h])
        or not np.array_equal(arrays["heldout_" + h], heldout[h])
        for h in spatial.HYPOTHESES
    ):
        raise ValueError("fresh probe/moment construction does not replay")
    for r in report["records"]:
        h, key = r["hypothesis"], r["key"]
        c = arrays["coefficient-" + key]
        target = spatial.IDEAL if r["k"] is None else validate_reference(refs[key])
        seal = None if r["k"] is None else refs[key]["reference_seal_sha256"]
        if r["reference_seal_sha256"] != seal:
            raise ValueError("record reference seal join changed")
        if not np.array_equal(c, target) or HASH(c) != r["coefficient_sha256"]:
            raise ValueError("reconstruction reference changed")
        expected_record = reconstruct_record(
            arrays["coords"], arrays["full_" + h], c, report["truth"]
        )
        if (
            any(r[k] != v for k, v in expected_record.items())
            or spatial.errors(design @ c, arrays["heldout_" + h]) != r["heldout_error"]
        ):
            raise ValueError(
                "local record does not replay from saved full field/reference"
            )
    json.dumps(report, allow_nan=False)
    return True


def distribution(values):
    values = [v for v in values if v is not None]
    return {
        "valid": len(values),
        "median": float(np.median(values)) if values else None,
        "q90": float(np.quantile(values, 0.9, method="linear")) if values else None,
        "min": float(min(values)) if values else None,
        "max": float(max(values)) if values else None,
    }


def summarize_group(records):
    positions = [
        r["observable"]["absolute_charge_centroid"]
        for r in records
        if r["observable"]["absolute_charge_centroid"] is not None
    ]
    center = np.median(positions, axis=0) if positions else None
    radius = (
        float(
            np.quantile(
                np.linalg.norm(np.asarray(positions) - center, axis=1),
                0.9,
                method="linear",
            )
        )
        if positions
        else None
    )
    return {
        "cohorts": len(records),
        "resolved_count_histogram": dict(
            Counter(str(r["observable"]["resolved_count"]) for r in records)
        ),
        "center_valid": len(positions),
        "center_missing": len(records) - len(positions),
        "empirical_center_median": center.tolist() if positions else None,
        "empirical_center_radius_q90": radius,
        "centroid_error": distribution(
            r["shape_error"]["centroid_error"] for r in records
        ),
        "span_error": distribution(r["shape_error"]["span_error"] for r in records),
        "span": distribution(r["observable"]["span"] for r in records),
        "heldout_rmse": distribution(
            r["heldout_error"]["complex_rmse"] for r in records
        ),
        "primary_exact": sum(r["score"]["exact_local_structure"] for r in records),
        "secondary_exact": sum(
            r["secondary_score"]["exact_local_structure"] for r in records
        ),
        "false_positive_cases": sum(
            r["score"]["false_positive_count"] > 0 for r in records
        ),
        "false_positive_components": sum(
            r["score"]["false_positive_count"] for r in records
        ),
        "missed_truth_components": sum(
            r["score"]["missed_truth_count"] for r in records
        ),
        "outer_correct": sum(
            r["score"]["outer_charge_correct"] is True for r in records
        ),
        "outer_undefined_truth": sum(
            r["score"]["outer_charge_correct"] is None for r in records
        ),
        "spread_is_calibrated_confidence_region": False,
    }
