"""Empirical affine-error envelopes and conditional quadratic separation sets.

The inference lane sees measured fields and sealed reference-error budgets,
never fixture labels or expected roots. It does not merge legacy components.
"""

from __future__ import annotations

import json

import numpy as np

import prototype_p4_reference_uncertainty_v0_1 as prior

spatial = prior.spatial
HASH, SEAL = prior.HASH, prior.SEAL
SCHEMA = "spirallens.p4-center-identifiability.v0.1"
KS = (16, 256, 4096)
ENVELOPE_SEEDS = tuple(range(500, 532))
REFERENCE_SEEDS = tuple(range(600, 616))
GEOMETRY_SEEDS = tuple(range(700, 704))
ALPHAS = (0.08, 0.10)
FIXTURES = (
    "double",
    "pair-004",
    "pair-008",
    "pair-016",
    "pair-040",
    "reverse-008",
    "reverse-040",
    "dipole",
    "constant",
    "zero",
    "linear",
    "cubic",
)
TAG, TOL = 0x50344944, 1e-9
FIT = np.array([(x, y) for y in (-1.0, 0.0, 1.0) for x in (-1.0, 0.0, 1.0)])
HELDOUT = np.array(
    [(x, y) for y in (-0.75, -0.25, 0.25, 0.75) for x in (-0.75, -0.25, 0.25, 0.75)]
)


def draws(seed, repeats=4096):
    if (
        type(seed) is not int
        or not 0 <= seed < 2**32
        or type(repeats) is not int
        or not 1 <= repeats <= 4096
    ):
        raise ValueError("uint32 seed and1..4096 repeats required")
    clean = prior.background_probes(prior.FIT)
    probes = np.empty((repeats, 5, 128, 3), dtype=np.float64)
    for repeat in range(repeats):
        noise = np.random.default_rng(
            np.random.SeedSequence([seed, TAG, repeat])
        ).normal(size=(5, 128, 3))
        probes[repeat] = clean + 0.03 * noise
    return probes


def fit_chunks(probes):
    if (
        not isinstance(probes, np.ndarray)
        or probes.dtype != np.float64
        or probes.ndim != 4
        or probes.shape[1:] != (5, 128, 3)
        or not 1 <= len(probes) <= 4096
        or not np.isfinite(probes).all()
    ):
        raise ValueError("finite repeat x5 x128 x3 probes required")
    chunks = [
        prior.fit_repeats(probes[i : i + 256]) for i in range(0, len(probes), 256)
    ]
    return tuple(
        {h: np.concatenate([c[j][h] for c in chunks]) for h in spatial.HYPOTHESES}
        for j in (0, 1)
    )


def references(seed, role, probes, moments, fits, ks):
    if (
        role not in ("envelope_calibration", "evaluation_reference")
        or not ks
        or tuple(sorted(set(ks))) != tuple(ks)
        or any(type(k) is not int or k not in KS or k > len(probes) for k in ks)
    ):
        raise ValueError("registered role and unique ordered prefixes required")
    records = []
    for k in ks:
        for h in spatial.HYPOTHESES:
            c = fits[h][:k].mean(axis=0)
            body = {
                "schema_version": SCHEMA + ".reference",
                "reference_seed": seed,
                "role": role,
                "k": k,
                "hypothesis": h,
                "coefficients": c.tolist(),
                "coefficient_sha256": HASH(c),
                "probe_prefix_sha256": HASH(probes[:k]),
                "moment_prefix_sha256": HASH(moments[h][:k]),
                "fit_coords_sha256": HASH(prior.FIT),
                "observation_frame_sha256": HASH(spatial.FRAME),
                "estimand": "mean-of-separately-fitted-background-only-references",
                "scientific_authority": False,
            }
            records.append({**body, "reference_seal_sha256": SEAL(body)})
    return records


def calibrate(seed, role, *, repeats=4096, ks=KS):
    probes = draws(seed, repeats)
    moments, fits = fit_chunks(probes)
    arrays = {"probes": probes, "fit_coords": prior.FIT}
    for h in spatial.HYPOTHESES:
        arrays["moments_" + h], arrays["fits_" + h] = moments[h], fits[h]
    return {
        "schema_version": SCHEMA,
        "lane": role,
        "reference_seed": seed,
        "repeats": repeats,
        "ks": list(ks),
        "references": references(seed, role, probes, moments, fits, ks),
        "geometry_observed": False,
        "heldout_observed": False,
        "scientific_authority": False,
    }, arrays


def verify_calibration(report, arrays):
    if (
        report["schema_version"] != SCHEMA
        or report["scientific_authority"] is not False
        or report["geometry_observed"] is not False
        or report["heldout_observed"] is not False
    ):
        raise ValueError("calibration schema/chronology/claim changed")
    if not np.array_equal(
        arrays["probes"], draws(report["reference_seed"], report["repeats"])
    ) or not np.array_equal(arrays["fit_coords"], prior.FIT):
        raise ValueError("calibration stream changed")
    moments, fits = fit_chunks(arrays["probes"])
    for h in spatial.HYPOTHESES:
        if not np.array_equal(moments[h], arrays["moments_" + h]) or not np.array_equal(
            fits[h], arrays["fits_" + h]
        ):
            raise ValueError("calibration moments/fits changed")
    if (
        references(
            report["reference_seed"],
            report["lane"],
            arrays["probes"],
            moments,
            fits,
            report["ks"],
        )
        != report["references"]
    ):
        raise ValueError("reference prefix replay changed")
    return True


def validate_reference(ref):
    body = {k: v for k, v in ref.items() if k != "reference_seal_sha256"}
    c = spatial.finite(ref["coefficients"], columns=2)
    if (
        ref["schema_version"] != SCHEMA + ".reference"
        or c.shape != (3, 2)
        or HASH(c) != ref["coefficient_sha256"]
        or SEAL(body) != ref["reference_seal_sha256"]
        or ref["scientific_authority"] is not False
        or ref["role"] not in ("envelope_calibration", "evaluation_reference")
        or type(ref["reference_seed"]) is not int
        or not 0 <= ref["reference_seed"] < 2**32
        or type(ref["k"]) is not int
        or ref["k"] not in KS
        or ref["hypothesis"] not in spatial.HYPOTHESES
        or ref["fit_coords_sha256"] != HASH(prior.FIT)
        or ref["observation_frame_sha256"] != HASH(spatial.FRAME)
        or ref["estimand"] != "mean-of-separately-fitted-background-only-references"
    ):
        raise ValueError("reference seal/shape/role/estimand changed")
    return c


def make_envelope(reports, *, seeds=ENVELOPE_SEEDS, ks=KS):
    if (
        not seeds
        or len(seeds) % 2
        or len(set(seeds)) != len(seeds)
        or [r["reference_seed"] for r in reports] != list(seeds)
    ):
        raise ValueError("complete ordered envelope cohort pairs required")
    refs = {}
    for report in reports:
        if (
            report["lane"] != "envelope_calibration"
            or report["ks"] != list(ks)
            or report["geometry_observed"] is not False
            or report["heldout_observed"] is not False
        ):
            raise ValueError("envelope cohort role/chronology changed")
        if [(r["k"], r["hypothesis"]) for r in report["references"]] != [
            (k, h) for k in ks for h in spatial.HYPOTHESES
        ]:
            raise ValueError("envelope cohort lost a reference")
        for ref in report["references"]:
            validate_reference(ref)
            if (
                ref["role"] != "envelope_calibration"
                or ref["reference_seed"] != report["reference_seed"]
            ):
                raise ValueError("envelope reference join changed")
            refs[(ref["reference_seed"], ref["k"], ref["hypothesis"])] = ref
    rows = []
    for k in ks:
        for h in spatial.HYPOTHESES:
            pairs = []
            for a, b in zip(seeds[::2], seeds[1::2], strict=True):
                ra, rb = refs[(a, k, h)], refs[(b, k, h)]
                delta = np.linalg.norm(
                    np.asarray(ra["coefficients"]) - rb["coefficients"], axis=1
                )
                pairs.append(
                    {
                        "seeds": [a, b],
                        "row_differences": delta.tolist(),
                        "reference_seals": [
                            ra["reference_seal_sha256"],
                            rb["reference_seal_sha256"],
                        ],
                    }
                )
            body = {
                "k": k,
                "hypothesis": h,
                "pairs": pairs,
                "radii": (
                    np.max([p["row_differences"] for p in pairs], axis=0) + TOL
                ).tolist(),
                "numerical_margin": TOL,
                "calibrated_confidence_region": False,
                "scientific_authority": False,
            }
            rows.append({**body, "envelope_row_sha256": SEAL(body)})
    body = {
        "schema_version": SCHEMA + ".envelope",
        "seeds": list(seeds),
        "ks": list(ks),
        "rows": rows,
        "geometry_observed": False,
        "evaluation_references_observed": False,
        "oracle_baseline_used": False,
        "scientific_authority": False,
    }
    return {**body, "envelope_seal_sha256": SEAL(body)}


def validate_envelope(envelope):
    body = {k: v for k, v in envelope.items() if k != "envelope_seal_sha256"}
    if (
        envelope["schema_version"] != SCHEMA + ".envelope"
        or SEAL(body) != envelope["envelope_seal_sha256"]
        or any(
            envelope[k] is not False
            for k in (
                "geometry_observed",
                "evaluation_references_observed",
                "oracle_baseline_used",
                "scientific_authority",
            )
        )
    ):
        raise ValueError("envelope closure/chronology changed")
    if [(r["k"], r["hypothesis"]) for r in envelope["rows"]] != [
        (k, h) for k in envelope["ks"] for h in spatial.HYPOTHESES
    ]:
        raise ValueError("envelope row denominator changed")
    seeds = envelope["seeds"]
    if not seeds or len(seeds) % 2 or len(set(seeds)) != len(seeds):
        raise ValueError("envelope pairing changed")
    for row in envelope["rows"]:
        data = {k: v for k, v in row.items() if k != "envelope_row_sha256"}
        if SEAL(data) != row["envelope_row_sha256"] or [
            p["seeds"] for p in row["pairs"]
        ] != [list(p) for p in zip(seeds[::2], seeds[1::2], strict=True)]:
            raise ValueError("envelope row seal/pairing changed")
        delta = spatial.finite([p["row_differences"] for p in row["pairs"]])
        if (
            delta.shape != (len(seeds) // 2, 3)
            or np.any(delta < 0)
            or not np.array_equal(np.max(delta, axis=0) + TOL, row["radii"])
            or row["numerical_margin"] != TOL
            or row["calibrated_confidence_region"] is not False
            or row["scientific_authority"] is not False
        ):
            raise ValueError("envelope radii changed")
    return True


def geometry(seed, fixture):
    if fixture not in FIXTURES:
        raise ValueError("registered fixture required")
    base = spatial.geometry(seed, "double")
    c = complex(*base["center"])
    separation = (
        int(fixture.split("-")[1]) / 100
        if "-" in fixture
        else 0.4
        if fixture == "dipole"
        else 0.0
    )
    delta = separation / 2 * np.exp(1j * base["angle"])
    centers = [c + delta, c - delta] if separation else [c]
    charges = (
        [-1, -1]
        if fixture.startswith("reverse")
        else [1, -1]
        if fixture == "dipole"
        else [1, 1]
        if separation
        else [1]
        if fixture == "linear"
        else [3]
        if fixture == "cubic"
        else [2]
    )
    if fixture in ("zero", "constant"):
        centers, charges = [], []
    return {
        **base,
        "fixture": fixture,
        "separation": separation,
        "centers": [[p.real, p.imag] for p in centers],
        "charges": charges,
        "everywhere_degenerate": fixture == "zero",
    }


def injected_field(coords, truth, alpha):
    z = spatial.complex_values(coords) - complex(*truth["center"])
    d = truth["separation"] / 2 * np.exp(1j * truth["angle"])
    name = truth["fixture"]
    if name == "double":
        value = z**2
    elif name.startswith(("pair-", "reverse-")):
        value = (z - d) * (z + d)
        if name.startswith("reverse-"):
            value = np.conj(value)
    elif name == "dipole":
        value = (z - d) * np.conj(z + d)
    elif name == "linear":
        value = z
    elif name == "cubic":
        value = z**3
    elif name == "constant":
        value = np.full(len(z), np.exp(1j * truth["angle"]))
    elif name == "zero":
        value = np.zeros(len(z), dtype=np.complex128)
    else:
        raise ValueError("unknown fixture")
    return 0.025 * (alpha / 0.1) * value


def design(coords):
    x, y = spatial.finite(coords, columns=2).T
    return np.column_stack((np.ones(len(x)), x, y, x * x, x * y, y * y))


def cv(z):
    return [float(np.real(z)), float(np.imag(z))]


def infer(coords, residual, radii):
    """No geometry truth, expected count, loop reading or reference selector."""
    coords, residual = (
        spatial.finite(coords, columns=2),
        spatial.finite(residual, columns=2),
    )
    radii = spatial.finite(radii)
    if residual.shape != coords.shape or radii.shape != (3,) or np.any(radii < 0):
        raise ValueError("aligned observations and three nonnegative radii required")
    mapping = {tuple(p): i for i, p in enumerate(coords)}
    if len(mapping) != len(coords) or any(
        tuple(p) not in mapping for p in np.concatenate((FIT, HELDOUT))
    ):
        raise ValueError("unique fit/heldout observations required")
    fit_rows = [mapping[tuple(p)] for p in FIT]
    test_rows = [mapping[tuple(p)] for p in HELDOUT]
    fitted = np.linalg.lstsq(design(FIT), residual[fit_rows], rcond=None)[0]
    prediction = design(HELDOUT) @ fitted
    error = float(np.max(np.linalg.norm(prediction - residual[test_rows], axis=1)))
    c, bx, by, qxx, qxy, qyy = spatial.complex_values(fitted)
    A, B, C = (qxx - qyy - 1j * qxy) / 4, (qxx - qyy + 1j * qxy) / 4, (qxx + qyy) / 2
    out = {
        "schema_version": SCHEMA + ".readout",
        "input_sha256": HASH(residual),
        "coords_sha256": HASH(coords),
        "fit_coords_sha256": HASH(FIT),
        "heldout_coords_sha256": HASH(HELDOUT),
        "polynomial_coefficients": fitted.tolist(),
        "heldout_max_error": error,
        "curvature": {"A": cv(A), "B": cv(B), "C": cv(C)},
        "radii": radii.tolist(),
        "numerical_margin": TOL,
        "scope": "empirical-envelope-conditional-quadratic-coefficient-field",
        "calibrated_confidence_region": False,
        "scientific_authority": False,
        "status": None,
        "reason": None,
        "orientation": None,
        "center": None,
        "center_radius": None,
        "discriminant": None,
        "discriminant_radius": None,
        "separation_lower": None,
        "separation_upper": None,
        "estimated_roots": None,
        "root_radius": None,
        "root_regions_disjoint": None,
    }
    if error > TOL:
        out.update(status="out_of_family", reason="heldout-quadratic-prediction")
    elif max(abs(A), abs(B), abs(C)) <= TOL:
        if all(abs(v) <= r for v, r in zip((c, bx, by), radii, strict=True)):
            out.update(
                status="zero_compatible",
                reason="affine-coefficients-inside-error-disks",
            )
        elif abs(c) - abs(bx) - abs(by) - float(radii.sum()) > spatial.FLOOR:
            out.update(
                status="nonzero_no_core_on_domain",
                reason="positive-global-affine-amplitude-lower-bound",
            )
        else:
            out.update(
                status="affine_unresolved",
                reason="nonzero-affine-outside-quadratic-family",
            )
    else:
        positive = abs(A) > spatial.FLOOR and max(abs(B), abs(C)) <= TOL
        negative = abs(B) > spatial.FLOOR and max(abs(A), abs(C)) <= TOL
        if not (positive or negative):
            out.update(status="out_of_family", reason="unsupported-quadratic-curvature")
        else:
            a = A if positive else B
            L, M = (
                ((bx - 1j * by) / 2, (bx + 1j * by) / 2)
                if positive
                else ((bx + 1j * by) / 2, (bx - 1j * by) / 2)
            )
            r0, rx, ry = radii
            rL = (rx + ry) / 2
            out.update(
                orientation="holomorphic" if positive else "antiholomorphic",
                active_a=cv(a),
                active_L=cv(L),
                inactive_M=cv(M),
                inactive_linear_radius=float(rL),
            )
            if abs(M) > rL + TOL:
                out.update(
                    status="reference_envelope_mismatch",
                    reason="inactive-linear-term-exceeds-envelope",
                )
            else:
                m = -L / (2 * a)
                D = m * m - c / a
                rm = (rL + 2 * abs(m) * TOL) / (2 * (abs(a) - TOL))
                rd = (
                    2 * abs(m) * rm + rm * rm + (r0 + abs(c / a) * TOL) / (abs(a) - TOL)
                )
                lower, upper = (
                    2 * np.sqrt(max(0.0, abs(D) - rd)),
                    2 * np.sqrt(abs(D) + rd),
                )
                root_radius = rm + np.sqrt(rd)
                positions = [m + np.sqrt(D), m - np.sqrt(D)]
                physical_center = m if positive else np.conj(m)
                if negative:
                    positions = [np.conj(p) for p in positions]
                out.update(
                    status="two_required_in_family"
                    if lower > 0
                    else "one_not_excluded",
                    reason="zero-discriminant-excluded"
                    if lower > 0
                    else "zero-discriminant-not-excluded",
                    center=cv(physical_center),
                    center_radius=float(rm),
                    discriminant=cv(D),
                    discriminant_radius=float(rd),
                    separation_lower=float(lower),
                    separation_upper=float(upper),
                    estimated_roots=[cv(p) for p in positions],
                    root_radius=float(root_radius),
                    root_regions_disjoint=bool(
                        abs(positions[0] - positions[1]) > 2 * root_radius
                    ),
                )
    json.dumps(out, allow_nan=False)
    return {**out, "readout_seal_sha256": SEAL(out)}


def score_inference(readout, truth, coefficients, radii):
    body = {k: v for k, v in readout.items() if k != "readout_seal_sha256"}
    if SEAL(body) != readout["readout_seal_sha256"]:
        raise ValueError("inference changed before truth scoring")
    is_pair = truth["fixture"].startswith(("pair-", "reverse-"))
    admitted_truth = is_pair or truth["fixture"] == "double"
    reference_error = np.linalg.norm(np.asarray(coefficients) - spatial.IDEAL, axis=1)
    valid = admitted_truth and readout["center"] is not None
    center_error = (
        float(np.linalg.norm(np.asarray(readout["center"]) - truth["center"]))
        if valid
        else None
    )
    return {
        "truth_read_after_inference": True,
        "truth_quadratic_family": admitted_truth,
        "reference_error_rows": reference_error.tolist(),
        "reference_inside_envelope": bool(np.all(reference_error <= radii)),
        "center_error": center_error,
        "center_covered": center_error <= readout["center_radius"] if valid else None,
        "separation_covered": readout["separation_lower"]
        <= truth["separation"]
        <= readout["separation_upper"]
        if valid
        else None,
        "false_two": readout["status"] == "two_required_in_family" and not is_pair,
        "pair_two_required": readout["status"] == "two_required_in_family" and is_pair,
        "single_not_excluded": readout["status"] == "one_not_excluded"
        and truth["fixture"] == "double",
    }


def local_record(coords, full, coefficients, radii, truth):
    residual = spatial.subtract(full, coords, coefficients)
    inference = infer(coords, residual, radii)
    candidates = spatial.locate(coords, residual)
    reconstruction = spatial.read_local_loops(coords, residual, candidates)
    observable = prior.measured_shape(reconstruction)
    # Both evidence lanes are complete and sealed before any truth-side scoring.
    return {
        "inference": inference,
        "candidates": candidates,
        "reconstruction": reconstruction,
        "observable": observable,
        "legacy_score": spatial.score(reconstruction, truth),
        "legacy_secondary_score": prior.strict_score(reconstruction, truth),
        "inference_score": score_inference(inference, truth, coefficients, radii),
    }


def local_unit(refs, envelope, bank_seal, *, alpha, geometry_seed, fixture, cells=256):
    validate_envelope(envelope)
    coefficients = {prior.reference_key(r): validate_reference(r) for r in refs}
    if len(coefficients) != len(refs) or any(
        r["role"] != "evaluation_reference" for r in refs
    ):
        raise ValueError("unique evaluation references required")
    budgets = {(r["k"], r["hypothesis"]): r for r in envelope["rows"]}
    if any((r["k"], r["hypothesis"]) not in budgets for r in refs):
        raise ValueError("reference has no sealed envelope")
    coords = spatial.grid_coords(cells)
    truth = geometry(geometry_seed, fixture)
    injection = injected_field(coords, truth, alpha)
    full = spatial.measure(coords, injection)
    arrays = {"coords": coords, "injected_truth": spatial.vector_values(injection)}
    records = []
    for h in spatial.HYPOTHESES:
        arrays["full_" + h] = full[h]
        candidates = [
            {
                "key": "ideal-" + h,
                "hypothesis": h,
                "reference_seed": None,
                "k": None,
                "reference_seal_sha256": None,
            }
        ] + [dict(r, key=prior.reference_key(r)) for r in refs if r["hypothesis"] == h]
        for ref in candidates:
            key, k = ref["key"], ref["k"]
            c = spatial.IDEAL if k is None else coefficients[key]
            radii = (
                np.full(3, TOL) if k is None else np.asarray(budgets[(k, h)]["radii"])
            )
            arrays["coefficient-" + key] = c
            record = local_record(coords, full[h], c, radii, truth)
            record.update(
                key=key,
                hypothesis=h,
                reference_seed=ref["reference_seed"],
                k=k,
                reference_seal_sha256=ref["reference_seal_sha256"],
                coefficient_sha256=HASH(c),
                envelope_row_sha256=None
                if k is None
                else budgets[(k, h)]["envelope_row_sha256"],
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
        "envelope_seal_sha256": envelope["envelope_seal_sha256"],
        "reference_keys": [prior.reference_key(r) for r in refs],
        "chronology": [
            "envelope-sealed-before-evaluation-references",
            "reference-bank-validated-before-geometry",
            "inference-sealed",
            "candidate-and-loops-sealed",
            "truth-scored",
        ],
        "scientific_authority": False,
        "graph_admission_inherited": False,
    }, arrays


def verify_local(report, arrays, refs, envelope, bank_seal):
    validate_envelope(envelope)
    truth = geometry(report["geometry_seed"], report["fixture"])
    if (
        report["schema_version"] != SCHEMA
        or report["truth"] != truth
        or report["scientific_authority"] is not False
        or report["bank_seal_sha256"] != bank_seal
        or report["envelope_seal_sha256"] != envelope["envelope_seal_sha256"]
    ):
        raise ValueError("geometry source/scope/bank changed")
    keys = [prior.reference_key(r) for r in refs]
    expected = ["ideal-" + h for h in spatial.HYPOTHESES] + keys
    if (
        report["reference_keys"] != keys
        or len(report["records"]) != len(expected)
        or sorted(r["key"] for r in report["records"]) != sorted(expected)
    ):
        raise ValueError("local reference denominator changed")
    if not np.array_equal(arrays["coords"], spatial.grid_coords(report["cells"])):
        raise ValueError("geometry coordinates changed")
    injection = injected_field(arrays["coords"], truth, report["alpha"])
    if not np.array_equal(arrays["injected_truth"], spatial.vector_values(injection)):
        raise ValueError("injected construction changed")
    full = spatial.measure(arrays["coords"], injection)
    by_key = dict(zip(keys, refs, strict=True))
    budgets = {(r["k"], r["hypothesis"]): r for r in envelope["rows"]}
    for h in spatial.HYPOTHESES:
        if not np.array_equal(arrays["full_" + h], full[h]):
            raise ValueError("fresh probe moments changed")
    for r in report["records"]:
        h, k, key = r["hypothesis"], r["k"], r["key"]
        ref = None if k is None else by_key[key]
        c = arrays["coefficient-" + key]
        target = spatial.IDEAL if ref is None else validate_reference(ref)
        if (
            not np.array_equal(c, target)
            or HASH(c) != r["coefficient_sha256"]
            or r["reference_seal_sha256"]
            != (None if ref is None else ref["reference_seal_sha256"])
        ):
            raise ValueError("coefficient/reference binding changed")
        if ref is None:
            if key != "ideal-" + h or r["reference_seed"] is not None:
                raise ValueError("ideal record relabeled")
        elif (h, k, r["reference_seed"]) != (
            ref["hypothesis"],
            ref["k"],
            ref["reference_seed"],
        ):
            raise ValueError("reference condition relabeled")
        radii = np.full(3, TOL) if k is None else np.asarray(budgets[(k, h)]["radii"])
        if r["envelope_row_sha256"] != (
            None if k is None else budgets[(k, h)]["envelope_row_sha256"]
        ):
            raise ValueError("envelope budget join changed")
        expected_record = local_record(arrays["coords"], full[h], c, radii, truth)
        if any(r[key] != value for key, value in expected_record.items()):
            raise ValueError("inference/local record does not replay")
    json.dumps(report, allow_nan=False)
    return True
