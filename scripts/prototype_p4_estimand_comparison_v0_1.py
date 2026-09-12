#!/usr/bin/env python3
"""Synthetic full/baseline/residual fields, not differences of winding numbers.

This development successor reuses the unchanged partial-pattern primitives.
There is no model intake, qualification, file writer, or launch operation.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from itertools import product

import numpy as np

import prototype_p4_partial_patterns_v0_1 as chain
from spirallens.core.canonical import canonical_json_sha256
from spirallens.referents.numeric import (
    derive_f2_section,
    derive_f4_spin_two,
    validate_observation_partition,
)


SCHEMA_VERSION = "spirallens.p4-estimand-comparison-development.v0.1"
PATTERNS = (
    "input_identity",
    "affine_offset",
    "quadratic_excess",
    "f2_nonlinear_only",
    "f4_nonlinear_only",
    "curved_coherent",
    "no_signal",
    "collapsed_support",
    "undersampled",
)
ESTIMANDS = (
    "full",
    "pass_through",
    "local_affine",
    "residual_affine",
    "residual_pass_through",
)
STENCIL_RADIUS = 0.5


@dataclass(frozen=True)
class ComparisonSpec:
    pattern: str
    side: int = 17
    noise: float = 0.0
    seed: int = 0
    gauge: str = "none"

    def __post_init__(self) -> None:
        if self.pattern not in PATTERNS:
            raise ValueError("unknown comparison pattern")
        chain.CaseSpec(
            "coherent",
            side=self.side,
            noise=self.noise,
            seed=self.seed,
            gauge=self.gauge,
        )


@dataclass(frozen=True)
class ComparisonBundle:
    coords: np.ndarray
    faces: np.ndarray
    plane_fit_probes: np.ndarray
    baseline_fit_probes: np.ndarray
    evaluation_probes: np.ndarray


def make_comparison_probes(spec: ComparisonSpec) -> ComparisonBundle:
    """Truth affects three independent synthetic streams, never estimator inputs."""
    side = 9 if spec.pattern == "undersampled" else spec.side
    axis = np.linspace(-1, 1, side)
    coords = np.array([(x, y) for y in axis for x in axis])
    faces = []
    for y, x in product(range(side - 1), repeat=2):
        row = y * side + x
        faces.extend(
            ((row, row + 1, row + side + 1), (row, row + side + 1, row + side))
        )
    z = coords[:, 0] + 1j * coords[:, 1]
    f2, f4 = z.copy(), np.zeros_like(z)
    if spec.pattern == "affine_offset":
        f2, f4 = 2 + z, 2 + z
    elif spec.pattern in {"quadratic_excess", "collapsed_support", "undersampled"}:
        f2, f4 = z + 0.25 * z**2, z + 0.25 * z**2
    elif spec.pattern == "f2_nonlinear_only":
        f2 = z + 0.25 * z**2
    elif spec.pattern == "f4_nonlinear_only":
        f4 = z + 0.25 * z**2
    elif spec.pattern == "curved_coherent":
        f2, f4 = np.full_like(z, 1 + 0.2j), np.full_like(z, 0.6 + 0.2j)
    elif spec.pattern == "no_signal":
        f2[:], f4[:] = 0, 0
    coefficients = np.array(list(product((-1.0, 1.0), repeat=3)))
    rngs = [
        np.random.default_rng(s) for s in np.random.SeedSequence(spec.seed).spawn(3)
    ]
    plane, baseline, evaluation = [], [], []
    for row, (x, y) in enumerate(coords):
        curvature = 0.5 if spec.pattern == "curved_coherent" else 0.0
        normal = np.array([-curvature * x, -curvature * y, 1.0])
        normal /= np.linalg.norm(normal)
        frame, _ = chain._polar_columns((np.eye(3) - np.outer(normal, normal))[:, :2])
        fit_coefficients = coefficients[:, :2] * [2.0, 1.0]
        if spec.pattern == "collapsed_support":
            fit_coefficients[:, 1] = 0
        plane.append(
            fit_coefficients @ frame.T + spec.noise * rngs[0].normal(size=(8, 3))
        )
        mean = frame @ np.array([f2[row].real, f2[row].imag])
        a, b = f4[row].real, f4[row].imag
        tensor = np.array([[a, b], [b, -a]])
        covariance = (1 + abs(f4[row])) * np.eye(3) + frame @ tensor @ frame.T
        root = np.linalg.cholesky(covariance)
        probes = mean + coefficients @ root.T
        baseline.append(probes + spec.noise * rngs[1].normal(size=(8, 3)))
        evaluation.append(probes + spec.noise * rngs[2].normal(size=(8, 3)))
    return ComparisonBundle(
        coords,
        np.asarray(faces, dtype="<i8"),
        np.array(plane),
        np.array(baseline),
        np.array(evaluation),
    )


def _validate_coords(coords: np.ndarray) -> None:
    side = math.isqrt(len(coords))
    axis = np.linspace(-1, 1, side)
    expected = np.array([(x, y) for y in axis for x in axis])
    if side < 9 or side > 33 or side % 4 != 1 or not np.array_equal(coords, expected):
        raise ValueError("requires bounded declared ordered square grid")


def _validate_probes(coords: np.ndarray, *roles: np.ndarray) -> None:
    _validate_coords(coords)
    for role in roles:
        if np.asarray(role).shape != (len(coords), 8, 3) or not np.isfinite(role).all():
            raise ValueError("each role requires finite (rows,8,3) probes")
    for index, role in enumerate(roles):
        if any(np.shares_memory(role, other) for other in roles[index + 1 :]):
            raise ValueError("probe roles must not share memory")


def _partition(count: int, role: int):
    rows = np.arange(count, dtype="<i8")
    return validate_observation_partition(
        np.column_stack((rows, np.zeros_like(rows))),
        np.column_stack((rows, np.full_like(rows, role))),
    )


def _reference_moments(
    frames: np.ndarray, gauges: np.ndarray, probes: np.ndarray, role: int
) -> dict:
    """Restore vector and tensor separately before any spatial regression."""
    partition = _partition(len(frames), role)
    rows = np.arange(len(frames), dtype="<i8")
    local_frames = frames @ gauges
    mean = probes.mean(axis=1)
    f2 = derive_f2_section(
        local_frames,
        mean,
        partition=partition,
        input_row_identities=rows,
        amplitude_floor=chain.AMPLITUDE_FLOOR,
    )
    centered = probes - mean[:, None, :]
    local = np.einsum("npd,ndi->npi", centered, local_frames)
    covariance = np.einsum("npi,npj->nij", local, local) / probes.shape[1]
    tensor = chain._traceless(covariance)
    restored = chain._traceless(gauges @ tensor @ np.swapaxes(gauges, 1, 2))
    f4 = derive_f4_spin_two(
        restored,
        partition=partition,
        input_row_identities=rows,
        amplitude_floor=chain.AMPLITUDE_FLOOR,
    )
    return {"F2": np.einsum("nij,nj->ni", gauges, f2.values), "F4": f4.traceless_tensor}


def fit_baseline(
    coords: np.ndarray,
    plane_fit_probes: np.ndarray,
    baseline_fit_probes: np.ndarray,
    *,
    gauge: str = "none",
) -> dict:
    """Seal finite-neighborhood affine coefficients with no evaluation argument."""
    _validate_probes(coords, plane_fit_probes, baseline_fit_probes)
    frames, support = chain.fit_frames(plane_fit_probes)
    gauges = chain._gauges(coords, gauge)
    targets = np.array(
        [
            [0, 0],
            [-STENCIL_RADIUS, 0],
            [STENCIL_RADIUS, 0],
            [0, -STENCIL_RADIUS],
            [0, STENCIL_RADIUS],
        ]
    )
    stencil_rows = np.array(
        [
            np.flatnonzero(np.isclose(coords, target, atol=1e-12, rtol=0).all(axis=1))[
                0
            ]
            for target in targets
        ]
    )
    design = np.column_stack((np.ones(len(stencil_rows)), coords[stencil_rows]))
    rank = int(np.linalg.matrix_rank(design))
    condition = float(np.linalg.cond(design))
    valid = bool(support[stencil_rows].all() and rank == 3 and condition < 100)
    coefficients, fit_rms = {}, {}
    if valid:
        # Only the fixed five baseline rows are read by the coefficient estimator.
        values = _reference_moments(
            frames[stencil_rows],
            gauges[stencil_rows],
            baseline_fit_probes[stencil_rows],
            1,
        )
        for name, data in values.items():
            flat = data.reshape(len(stencil_rows), -1)
            fit = np.linalg.lstsq(design, flat, rcond=None)[0]
            fit[fit == 0.0] = 0.0
            coefficients[name] = fit.reshape((3,) + data.shape[1:]).tolist()
            fit_rms[name] = float(np.sqrt(np.mean((design @ fit - flat) ** 2)))
    else:
        coefficients = {"F2": None, "F4": None}
        fit_rms = {"F2": None, "F4": None}
    receipt = {
        "state": "eligible" if valid else "insufficient",
        "reason": "fixed-neighborhood-affine-fit-not-exact-taylor"
        if valid
        else "stencil-plane-reference-or-design-support-insufficient",
        "basis": ["1", "x", "y"],
        "stencil_radius": STENCIL_RADIUS,
        "stencil_rows": stencil_rows.tolist(),
        "stencil_coords": coords[stencil_rows].tolist(),
        "rank": rank,
        "condition_number": condition,
        "coefficients": coefficients,
        "stencil_fit_rms": fit_rms,
        "frame_sha256": chain._array_hash(frames),
        "plane_probe_sha256": chain._array_hash(plane_fit_probes),
        "baseline_probe_sha256": chain._array_hash(baseline_fit_probes),
        "coords_sha256": chain._array_hash(coords),
        "evaluation_read": False,
        "evaluation_selected_stencil": False,
        "reference": "fit-only-plane-projector-polar-ambient-e1-e2",
        "field_operations": {
            "F2": "reference-vector-affine-regression",
            "F4": "reference-traceless-tensor-affine-regression",
        },
        "extrapolation_rule": "abs(x)+abs(y)>0.5; outside-fixed-stencil-convex-hull",
        "external_provenance_verified": False,
        "official_freeze": False,
    }
    receipt["baseline_sha256"] = canonical_json_sha256(receipt)
    return receipt


def _section(name: str, data: np.ndarray):
    count = len(data)
    partition, rows = _partition(count, 2), np.arange(count, dtype="<i8")
    if name == "F2":
        return derive_f2_section(
            np.tile(np.eye(2), (count, 1, 1)),
            data,
            partition=partition,
            input_row_identities=rows,
            amplitude_floor=chain.AMPLITUDE_FLOOR,
        )
    return derive_f4_spin_two(
        chain._traceless(data),
        partition=partition,
        input_row_identities=rows,
        amplitude_floor=chain.AMPLITUDE_FLOOR,
    ).section


def _make_field(
    name: str,
    estimand: str,
    data: np.ndarray | None,
    support: np.ndarray,
    bundle: ComparisonBundle,
    domain_hash: str,
    parents: dict,
    baseline: dict,
) -> dict:
    mask = support.copy() if data is not None else np.zeros_like(support)
    payload = {
        "hypothesis": name,
        "estimand": estimand,
        "state": "eligible" if data is not None and mask.all() else "insufficient",
        "values": None,
        "amplitude": None,
        "direction_defined": None,
        "fit_support": mask.tolist(),
        "amplitude_floor": chain.AMPLITUDE_FLOOR,
        "domain_sha256": domain_hash,
        "parents": parents,
        "reference": "fit-only-plane-projector-polar-ambient-e1-e2",
        "interpolation": "principal-angle-on-exact-declared-boundary; not-continuum-certified",
        "convention": "vector-angle"
        if name == "F2"
        else "doubled-director-angle; tensor-contrast-not-residual-probe-covariance",
        "subtraction_stage": "reference-vector"
        if name == "F2"
        else "reference-traceless-tensor",
        "baseline_extrapolated": (
            np.abs(bundle.coords).sum(axis=1) > STENCIL_RADIUS + 1e-12
        ).tolist()
        if estimand in {"local_affine", "residual_affine"}
        else None,
        "imposed_origin_zero": estimand == "origin_centered",
        "centering_origin_source": "same-evaluation-field; algebraic-control-not-fit-baseline"
        if estimand == "origin_centered"
        else None,
    }
    if data is not None:
        section = _section(name, data)
        payload.update(
            values=section.values.tolist(),
            amplitude=section.amplitude.tolist(),
            direction_defined=section.direction_defined.tolist(),
        )
        if name == "F4":
            tensor = chain._traceless(data)
            tensor[tensor == 0.0] = 0.0
            payload["traceless_tensor"] = tensor.tolist()
    else:
        payload["missing_reason"] = (
            "origin-plane-reference-insufficient"
            if estimand == "origin_centered"
            else "baseline-unavailable-no-field-fabricated"
        )
        payload["dependency_reason"] = (
            "origin-reference-not-supported"
            if estimand == "origin_centered"
            else baseline["reason"]
        )
    field_hash = canonical_json_sha256(payload)
    payload["field_sha256"] = field_hash
    if data is None:
        core = chain._branch(
            "insufficient",
            {"classification": "unresolved", "candidate_count": None, "components": []},
            payload["missing_reason"],
            0,
        )
        core.update(field_sha256=field_hash, charge_blind=True)
        core["seal_sha256"] = canonical_json_sha256(core)
    else:
        core = chain._core(
            np.asarray(payload["amplitude"]),
            mask,
            bundle.coords,
            bundle.faces,
            field_hash,
        )
    payload["core"] = core
    return payload


def measure_comparison(bundle: ComparisonBundle, *, gauge: str = "none") -> dict:
    """The evaluation route has no construction label or target charge input."""
    _validate_probes(
        bundle.coords,
        bundle.plane_fit_probes,
        bundle.baseline_fit_probes,
    )
    if any(
        np.shares_memory(bundle.evaluation_probes, role)
        for role in (bundle.plane_fit_probes, bundle.baseline_fit_probes)
    ):
        raise ValueError("probe roles must not share memory")
    domain_bundle = chain.ProbeBundle(
        bundle.coords, bundle.faces, bundle.plane_fit_probes, bundle.evaluation_probes
    )
    loops, domain = chain._domain_loops(domain_bundle)
    baseline = fit_baseline(
        bundle.coords, bundle.plane_fit_probes, bundle.baseline_fit_probes, gauge=gauge
    )
    # Coefficients and their digest exist before the evaluation moment read.
    _validate_probes(bundle.coords, bundle.evaluation_probes)
    frames, support = chain.fit_frames(bundle.plane_fit_probes)
    gauges = chain._gauges(bundle.coords, gauge)
    full = _reference_moments(frames, gauges, bundle.evaluation_probes, 2)
    input_mean = np.column_stack((bundle.coords, np.zeros(len(bundle.coords))))
    pass_through = {
        "F2": np.einsum("ndi,nd->ni", frames, input_mean),
        "F4": chain._traceless(np.einsum("ndi,ndj->nij", frames, frames)),
    }
    design = np.column_stack((np.ones(len(bundle.coords)), bundle.coords))
    affine = {name: None for name in ("F2", "F4")}
    if baseline["state"] == "eligible":
        for name in affine:
            coefficients = np.asarray(baseline["coefficients"][name])
            affine[name] = np.einsum("nc,c...->n...", design, coefficients)
    origin = int(np.flatnonzero((bundle.coords == 0).all(axis=1))[0])
    arrays = {
        "full": full,
        "pass_through": pass_through,
        "local_affine": affine,
        "residual_affine": {
            name: None if affine[name] is None else full[name] - affine[name]
            for name in full
        },
        "residual_pass_through": {
            name: full[name] - pass_through[name] for name in full
        },
        "origin_centered": {
            name: full[name] - full[name][origin] if support[origin] else None
            for name in full
        },
    }
    provenance = {
        "plane_probe_sha256": chain._array_hash(bundle.plane_fit_probes),
        "baseline_probe_sha256": chain._array_hash(bundle.baseline_fit_probes),
        "evaluation_probe_sha256": chain._array_hash(bundle.evaluation_probes),
        "role_contract": "three-independent-synthetic-streams; not-attested-external-observation-ids",
        "gauge": gauge,
        "external_probe_provenance_verified": False,
    }
    records = {}
    for estimand, fields in arrays.items():
        records[estimand] = {"fields": {}}
        for name, data in fields.items():
            parents = {"plane_probe_sha256": provenance["plane_probe_sha256"]}
            if estimand == "full":
                parents["evaluation_probe_sha256"] = provenance[
                    "evaluation_probe_sha256"
                ]
            elif estimand == "pass_through":
                parents["construction"] = (
                    "fixed-ambient-mean-(x,y,0)-and-isotropic-covariance-I3"
                )
            elif estimand == "local_affine":
                parents["baseline_sha256"] = baseline["baseline_sha256"]
            else:
                parents["full_field_sha256"] = records["full"]["fields"][name][
                    "field_sha256"
                ]
                if estimand in {"residual_affine", "residual_pass_through"}:
                    target = (
                        "local_affine"
                        if estimand == "residual_affine"
                        else "pass_through"
                    )
                    parents["subtracted_field_sha256"] = records[target]["fields"][
                        name
                    ]["field_sha256"]
                else:
                    parents["origin_row"] = origin
            records[estimand]["fields"][name] = _make_field(
                name,
                estimand,
                data,
                support,
                bundle,
                domain["domain_sha256"],
                parents,
                baseline,
            )
    # All twelve field-specific core seals precede every winding read.
    for record in records.values():
        for field in record["fields"].values():
            field["loops"] = {}
            for name, (rows, matched) in loops.items():
                field["loops"][name] = {}
                for direction, path in (
                    ("forward", rows),
                    ("reverse", np.r_[rows[:1], rows[:0:-1]]),
                ):
                    if field["values"] is None:
                        result = chain._branch(
                            "insufficient",
                            None,
                            field["missing_reason"],
                            0,
                        )
                        result["field_sha256"] = field["field_sha256"]
                    else:
                        result = chain._winding(
                            path,
                            matched,
                            bundle.coords,
                            np.asarray(field["fit_support"]),
                            np.asarray(field["values"]),
                            field["field_sha256"],
                        )
                    field["loops"][name][direction] = result
    geometry = {}
    for name, (rows, matched) in loops.items():
        geometry[name] = {
            "forward": chain._geometry(
                rows, matched, bundle.coords, frames @ gauges, support, gauges
            ),
            "reverse": chain._geometry(
                np.r_[rows[:1], rows[:0:-1]],
                matched,
                bundle.coords,
                frames @ gauges,
                support,
                gauges,
            ),
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "development_only_not_qualification",
        "co_primary_hypotheses": ["F2", "F4"],
        "winner_selected": False,
        "development_thresholds": chain.development_thresholds(),
        "provenance": provenance,
        "domain": domain,
        "baseline": baseline,
        "estimands": {name: records[name] for name in ESTIMANDS},
        "controls": {"origin_centered": records["origin_centered"]},
        "geometry": geometry,
        "geometry_scope": "shared-full-fit-plane-reference-connection; not-residual-model-geometry",
        "scope": {
            "synthetic_only": True,
            "model_free": True,
            "model_accessed": False,
            "network_accessed": False,
            "furnace_accessed": False,
            "protocol_freeze": False,
            "execution_authorized": False,
        },
        "claim_boundary": {
            "claim_ceiling": "level_0",
            "scientific_authority": False,
            "topology_authority": False,
            "semantic_authority": False,
            "publication_authority": False,
            "verified_core": False,
            "model_derived_order_parameter": False,
            "nonlinearity_proven": False,
        },
        "phase": chain._branch(
            "not_evaluated", None, "no-regime-or-checkpoint-series", 0
        ),
        "transition": chain._branch(
            "not_evaluated", None, "no-regime-or-checkpoint-series", 0
        ),
    }


def measure_case(spec: ComparisonSpec) -> dict:
    report = measure_comparison(make_comparison_probes(spec), gauge=spec.gauge)
    report["spec"] = asdict(spec)
    return report


def run_development_demo() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "development_only_not_qualification",
        "cases": [measure_case(ComparisonSpec(pattern)) for pattern in PATTERNS],
        "remaining": [
            "representation-graph-three-by-three",
            "fresh-crossed-nuisance-and-uncertainty-qualification",
            "model-access-and-protocol-freeze",
        ],
    }


def self_test() -> dict:
    identity = measure_case(ComparisonSpec("input_identity"))
    quadratic = measure_case(ComparisonSpec("quadratic_excess"))
    affine = measure_case(ComparisonSpec("affine_offset"))
    checks = []
    for name in ("F2", "F4"):
        checks.append(
            identity["estimands"]["residual_affine"]["fields"][name]["loops"]["outer"][
                "forward"
            ]["state"]
            == "insufficient"
        )
        checks.append(
            quadratic["estimands"]["residual_affine"]["fields"][name]["loops"]["outer"][
                "forward"
            ]["value"]["sampled_winding"]
            == 2
        )
        checks.append(
            affine["controls"]["origin_centered"]["fields"][name]["loops"]["outer"][
                "forward"
            ]["value"]["sampled_winding"]
            == 1
        )
    return {
        "status": "pass" if all(checks) else "fail",
        "check_count": len(checks),
        "scope": "synthetic-development-only",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--demo", action="store_true")
    mode.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    report = self_test() if args.self_test else run_development_demo()
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return int(report.get("status") == "fail")


if __name__ == "__main__":
    raise SystemExit(main())
