"""Expanded, inference-first resolution sampling with unchanged predecessor rules."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import prototype_p4_center_identifiability_v0_1 as base

prior, spatial = base.prior, base.spatial
HASH, SEAL, KS = base.HASH, base.SEAL, base.KS
SCHEMA = "spirallens.p4-center-resolution.v0.1"
ENVELOPE_FILE = "protocols/p4_center_resolution_envelope_v0_1.json"
ENVELOPE_SHA = "fc42c19e7d561eee00ce14abf4652d24a4b440e3aba1046d1bc82762a37a403b"
REFERENCE_SEEDS = tuple(range(800, 864))
GEOMETRY_SEEDS = tuple(range(900, 916))
ALPHAS = base.ALPHAS
SUPPORT = np.concatenate((base.FIT, base.HELDOUT))
DISTANCES = tuple(range(80, 161, 5))
FIXTURES = (
    "double",
    "pair-d040",
    *(f"pair-d{d:03d}" for d in DISTANCES),
    "pair-d400",
    "reverse-d080",
    "reverse-d160",
    "reverse-d400",
    "dipole",
    "constant",
    "zero",
    "linear",
    "cubic",
)
STRESS_FIXTURES = (
    "double",
    "pair-d080",
    "pair-d120",
    "pair-d160",
    "zero",
    "linear",
    "cubic",
)
LOCAL_FIXTURES = (
    "double",
    "pair-d080",
    "pair-d100",
    "pair-d120",
    "pair-d140",
    "pair-d160",
    "pair-d400",
    "zero",
)
STRESSES = (
    "constant-bias-0.5",
    "constant-bias-1",
    "constant-bias-2",
    "linear-bias-1",
    "evaluation-noise-1e-9",
    "evaluation-noise-1e-7",
    "evaluation-noise-1e-4",
)
STATES = (
    "one_not_excluded",
    "two_required_in_family",
    "zero_compatible",
    "nonzero_no_core_on_domain",
    "affine_unresolved",
    "out_of_family",
    "reference_envelope_mismatch",
)
COLUMNS = (
    "fixture",
    "reference_seed",
    "k",
    "hypothesis",
    "status",
    "separation_lower",
    "separation_upper",
    "center_x",
    "center_y",
    "center_radius",
    "discriminant_radius",
    "root_radius",
    "root_regions_disjoint",
    "reference_inside_envelope",
    "center_error",
    "center_covered",
    "separation_covered",
    "false_two",
    "pair_two_required",
    "single_not_excluded",
    "bound_constant",
    "bound_center_linear",
    "bound_numerical",
    "heldout_max_error",
    "reference_error_constant",
    "reference_error_x",
    "reference_error_y",
    "readout_seal_sha256",
    "coefficient_sha256",
    "reference_seal_sha256",
    "reason",
)
COL = {name: i for i, name in enumerate(COLUMNS)}


def inherited_envelope(root: Path):
    import hashlib

    path = root / ENVELOPE_FILE
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ENVELOPE_SHA:
        raise ValueError("inherited envelope bytes changed")
    document = json.loads(raw)
    body = {k: v for k, v in document.items() if k != "file_seal_sha256"}
    if (
        SEAL(body) != document["file_seal_sha256"]
        or document["scientific_authority"] is not False
    ):
        raise ValueError("inherited envelope file seal/claim changed")
    envelope = document["envelope"]
    base.validate_envelope(envelope)
    if envelope["seeds"] != list(base.ENVELOPE_SEEDS) or envelope["ks"] != list(KS):
        raise ValueError("inherited envelope cohort/prefix scope changed")
    return envelope


def geometry(seed, fixture):
    if type(seed) is not int or seed < 0 or fixture not in FIXTURES:
        raise ValueError("nonnegative geometry seed and registered fixture required")
    paired = fixture.startswith(("pair-d", "reverse-d"))
    original = (
        "reverse-008"
        if fixture.startswith("reverse-d")
        else "pair-008"
        if paired
        else fixture
    )
    truth = base.geometry(seed, original)
    if paired:
        distance = int(fixture.rsplit("d", 1)[1]) / 1000
        m = complex(*truth["center"])
        d = distance / 2 * np.exp(1j * truth["angle"])
        truth.update(separation=distance, centers=[base.cv(m + d), base.cv(m - d)])
    truth["fixture"] = fixture
    return truth


def observe(coords, truth, alpha, *, noise=0.0, geometry_seed=0):
    if (
        isinstance(alpha, bool)
        or alpha not in ALPHAS
        or not np.isfinite(noise)
        or noise < 0
    ):
        raise ValueError("registered strength and nonnegative finite noise required")
    injection = base.injected_field(coords, truth, alpha)
    values = coords + spatial.vector_values(injection)
    probes = prior.background_probes(values)
    if noise:
        z = np.random.default_rng(
            np.random.SeedSequence([geometry_seed, 0x50345253])
        ).normal(size=probes.shape)
        probes = probes + noise * z
    frames = np.broadcast_to(spatial.FRAME, (len(coords), 3, 2))
    full = spatial.DenseMomentAdapter().moments(frames, probes)
    return probes, full


def stress_parameters(mode):
    if mode == "none":
        return "none", 0.0
    if mode not in STRESSES:
        raise ValueError("unregistered stress")
    if mode.startswith("evaluation-noise-"):
        return "evaluation-noise", float(mode.removeprefix("evaluation-noise-"))
    kind, value = mode.rsplit("-", 1)
    return kind, float(value)


def transformed_reference(coefficients, radii, mode):
    kind, amount = stress_parameters(mode)
    c = spatial.finite(coefficients, columns=2).copy()
    if c.shape != (3, 2):
        raise ValueError("three affine rows required")
    if kind == "constant-bias":
        c[0] += base.cv(amount * radii[0] * np.exp(1j * np.pi / 7))
    elif kind == "linear-bias":
        c[1] += base.cv(radii[1] * np.exp(1j * np.pi / 7))
        c[2] += base.cv(radii[2] * np.exp(1j * (np.pi / 7 + np.pi / 3)))
    return c


def decomposition(readout):
    if readout["center_radius"] is None:
        return (None, None, None)
    a = abs(complex(*readout["active_a"]))
    m = np.linalg.norm(readout["center"])
    rm = readout["center_radius"]
    c = complex(*readout["polynomial_coefficients"][0])
    return (
        float(readout["radii"][0] / (a - base.TOL)),
        float(2 * m * rm + rm * rm),
        float(abs(c / complex(*readout["active_a"])) * base.TOL / (a - base.TOL)),
    )


def row(readout, score, truth, ref, coefficients):
    center = readout["center"] or [None, None]
    parts = decomposition(readout)
    if parts[0] is not None and not np.isclose(
        sum(parts), readout["discriminant_radius"], rtol=1e-12, atol=1e-15
    ):
        raise ValueError("discriminant decomposition changed")
    result = [
        truth["fixture"],
        ref["reference_seed"],
        ref["k"],
        ref["hypothesis"],
        readout["status"],
        readout["separation_lower"],
        readout["separation_upper"],
        *center,
        readout["center_radius"],
        readout["discriminant_radius"],
        readout["root_radius"],
        readout["root_regions_disjoint"],
        score["reference_inside_envelope"],
        score["center_error"],
        score["center_covered"],
        score["separation_covered"],
        score["false_two"],
        score["pair_two_required"],
        score["single_not_excluded"],
        *parts,
        readout["heldout_max_error"],
        *score["reference_error_rows"],
        readout["readout_seal_sha256"],
        HASH(coefficients),
        ref["reference_seal_sha256"],
        readout["reason"],
    ]
    if len(result) != len(COLUMNS) or result[COL["status"]] not in STATES:
        raise ValueError("compact inference columns/status changed")
    return result


def numerical_payload(readout):
    return {
        k: v
        for k, v in readout.items()
        if k not in ("input_sha256", "coords_sha256", "readout_seal_sha256")
    }


def choices(refs, envelope, mode, *, ideals):
    base.validate_envelope(envelope)
    budgets = {
        (r["k"], r["hypothesis"]): np.array(r["radii"]) for r in envelope["rows"]
    }
    result, keys = [], set()
    for ref in refs:
        c = base.validate_reference(ref)
        key = prior.reference_key(ref)
        if key in keys or ref["role"] != "evaluation_reference":
            raise ValueError("unique evaluation references required")
        keys.add(key)
        radii = budgets[(ref["k"], ref["hypothesis"])]
        result.append((ref, transformed_reference(c, radii, mode), radii))
    if not result:
        raise ValueError("no evaluation references")
    if ideals:
        if mode != "none":
            raise ValueError("stress ideal control not registered")
        for h in spatial.HYPOTHESES:
            ref = {
                "reference_seed": None,
                "k": None,
                "hypothesis": h,
                "reference_seal_sha256": None,
            }
            result.append((ref, spatial.IDEAL, np.full(3, base.TOL)))
    return result


def field_unit(
    refs,
    envelope,
    bank_seal,
    *,
    lane,
    alpha,
    geometry_seed,
    stress="none",
    fixture=None,
    saved=None,
):
    if lane not in ("primary", "stress", "local") or alpha not in ALPHAS:
        raise ValueError("registered field lane and strength required")
    if lane != "stress" and stress != "none":
        raise ValueError("stress cannot enter primary/local lane")
    kind, amount = stress_parameters(stress)
    if lane == "stress" and stress == "none":
        raise ValueError("stress lane requires a named stress")
    fixtures = (
        FIXTURES
        if lane == "primary"
        else STRESS_FIXTURES
        if lane == "stress"
        else (fixture,)
    )
    if lane == "local" and fixture not in LOCAL_FIXTURES:
        raise ValueError("unregistered local subset")
    selected = choices(refs, envelope, stress, ideals=lane != "stress")
    arrays = {
        "coords": SUPPORT.copy(),
        "coefficients": np.array([c for _, c, _ in selected]),
    }
    if lane == "local":
        arrays["grid_coords"] = spatial.grid_coords(256)
    records, local_records, truths = [], [], []
    for j, name in enumerate(fixtures):
        truth = geometry(geometry_seed, name)
        truths.append(truth)
        probes, full = observe(
            SUPPORT,
            truth,
            alpha,
            noise=amount if kind == "evaluation-noise" else 0.0,
            geometry_seed=geometry_seed,
        )
        arrays[f"probes-{j}"] = probes
        for h in spatial.HYPOTHESES:
            arrays[f"field-{j}-{h}"] = full[h]
        if lane == "local":
            grid = arrays["grid_coords"]
            entire = spatial.measure(grid, base.injected_field(grid, truth, alpha))
            ids = [np.flatnonzero(np.all(grid == p, axis=1))[0] for p in SUPPORT]
            for h in spatial.HYPOTHESES:
                arrays[f"grid-field-{h}"] = entire[h]
                if not np.array_equal(entire[h][ids], full[h]):
                    raise ValueError("support/full-grid measured values differ")
        # Saved observations are remeasured before they are used for replay.
        if saved is not None:
            for key in [f"probes-{j}", *(f"field-{j}-{h}" for h in spatial.HYPOTHESES)]:
                if not np.array_equal(arrays[key], saved[key]):
                    raise ValueError(
                        "saved observation differs from raw construction: " + key
                    )
            full = {h: saved[f"field-{j}-{h}"] for h in spatial.HYPOTHESES}
        for ref, c, radii in selected:
            residual = spatial.subtract(full[ref["hypothesis"]], SUPPORT, c)
            inference = base.infer(SUPPORT, residual, radii)
            if lane == "local":
                old = base.local_record(
                    grid, entire[ref["hypothesis"]], c, radii, truth
                )
                if numerical_payload(inference) != numerical_payload(old["inference"]):
                    raise ValueError("support/full-grid inference payload differs")
                local_records.append(
                    {
                        "reference_seed": ref["reference_seed"],
                        "k": ref["k"],
                        "hypothesis": ref["hypothesis"],
                        **old,
                    }
                )
            score = base.score_inference(inference, truth, c, radii)
            records.append(row(inference, score, truth, ref, c))
    report = {
        "schema_version": SCHEMA,
        "lane": lane,
        "alpha": alpha,
        "geometry_seed": geometry_seed,
        "stress": stress,
        "fixtures": list(fixtures),
        "truths": truths,
        "columns": list(COLUMNS),
        "records": records,
        "local_records": local_records,
        "reference_keys": [prior.reference_key(r) for r in refs],
        "bank_seal_sha256": bank_seal,
        "inherited_envelope_sha256": ENVELOPE_SHA,
        "envelope_seal_sha256": envelope["envelope_seal_sha256"],
        "support_sha256": HASH(SUPPORT),
        "record_seal_sha256": SEAL(records),
        "scientific_authority": False,
        "graph_admission_inherited": False,
        "chronology": [
            "inherited-envelope-fixed",
            "complete-reference-bank-sealed",
            "observed-support",
            "inference-sealed",
            "local-loops-sealed-if-in-subset",
            "truth-scored",
        ],
    }
    return report, arrays


def verify_field(report, arrays, refs, envelope, bank_seal, case):
    expected, raw = field_unit(refs, envelope, bank_seal, saved=arrays, **case)
    if set(raw) != set(arrays) or any(
        not np.array_equal(v, arrays[k]) for k, v in raw.items()
    ):
        raise ValueError("raw field closure/replay changed")
    if any(report[k] != v for k, v in expected.items()):
        raise ValueError("conditional record replay changed")
    return True


def bootstrap_weights(repeats=2000, references=64, geometries=16):
    if any(type(v) is not int or v <= 0 for v in (repeats, references, geometries)):
        raise ValueError("positive bootstrap dimensions required")
    rng = np.random.default_rng(np.random.SeedSequence([20260909, 0x50344253]))
    ref = np.zeros((repeats, references), dtype=float)
    geo = np.zeros((repeats, geometries), dtype=float)
    for i in range(repeats):
        ref[i] = (
            np.bincount(rng.integers(references, size=references), minlength=references)
            / references
        )
        geo[i] = (
            np.bincount(rng.integers(geometries, size=geometries), minlength=geometries)
            / geometries
        )
    return ref, geo


def decision_band(matrix, weights):
    values = np.asarray(matrix, dtype=float)
    ref, geo = weights
    if (
        values.shape != (geo.shape[1], ref.shape[1])
        or not np.isin(values, [0, 1]).all()
    ):
        raise ValueError("complete binary geometry x reference matrix required")
    sampled = np.einsum("rg,gn,rn->r", geo, values, ref, optimize=True)
    return {
        "fraction": float(values.mean()),
        "q05": float(np.quantile(sampled, 0.05)),
        "q95": float(np.quantile(sampled, 0.95)),
        "reference_fractions": values.mean(axis=0).tolist(),
        "geometry_fractions": values.mean(axis=1).tolist(),
        "bootstrap_repeats": len(ref),
        "calibrated_confidence_band": False,
    }
