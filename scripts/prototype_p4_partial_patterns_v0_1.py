#!/usr/bin/env python3
"""Bounded, model-free representation-to-partial-pattern development demo.

No launch, file writer, model adapter, official gate, or qualified topology.
Truth lives in make_probes; measurement receives only probes and a domain.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from itertools import product

import numpy as np

from spirallens.core.canonical import canonical_json_sha256
from spirallens.gauge.procrustes_connection import procrustes_connection
from spirallens.graphs import (
    BoundaryRefinementRule,
    GraphInput,
    GraphPurpose,
    RadiusGraphSpec,
    bind_cycle_class,
    build_discrete_domain_complex,
    construct_radius_graph,
    define_boundary_cycle_class,
)
from spirallens.holonomy.discrete import compose_edge_transports, relative_holonomy
from spirallens.referents.numeric import (
    derive_f2_section,
    derive_f4_spin_two,
    validate_observation_partition,
)
from spirallens.topology.winding import estimate_winding


SCHEMA_VERSION = "spirallens.p4-partial-pattern-development.v0.1"
PATTERNS = (
    "f2_only",
    "f4_only",
    "coherent",
    "core_depression",
    "holonomy_only",
    "flat_defect",
    "dipole",
    "smooth_drift",
    "pure_gauge",
    "zero",
    "collapsed_support",
    "undersampled",
)
GAUGES = ("none", "local_o2", "reflection")
AMPLITUDE_FLOOR = 1e-6
CORE_CUTOFF = 0.05
MAX_DOMAIN_EDGE = 0.2
GEOMETRY_THRESHOLD_RAD = 0.05
BRANCH_MARGIN_RAD = 0.15


def development_thresholds() -> dict:
    return {
        "amplitude_floor": AMPLITUDE_FLOOR,
        "core_cutoff": CORE_CUTOFF,
        "max_domain_edge": MAX_DOMAIN_EDGE,
        "geometry_threshold_rad": GEOMETRY_THRESHOLD_RAD,
        "branch_margin_rad": BRANCH_MARGIN_RAD,
        "threshold_transfer_authorized": False,
    }


def _array_hash(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value, dtype="<f8")
    return hashlib.sha256(
        str(array.shape).encode("ascii") + b"\0" + array.tobytes()
    ).hexdigest()


@dataclass(frozen=True)
class CaseSpec:
    pattern: str
    side: int = 17
    amplitude: float = 1.0
    noise: float = 0.0
    seed: int = 0
    gauge: str = "none"

    def __post_init__(self) -> None:
        if self.pattern not in PATTERNS or self.gauge not in GAUGES:
            raise ValueError("unknown development pattern or gauge")
        if type(self.side) is not int or not 9 <= self.side <= 33 or self.side % 4 != 1:
            raise ValueError("side must be 4k+1 in [9,33]")
        if type(self.seed) is not int or not 0 <= self.seed < 2**32:
            raise ValueError("seed must be a nonnegative uint32 integer")
        for name in ("amplitude", "noise"):
            value = getattr(self, name)
            if isinstance(value, bool) or not np.isfinite(value) or not 0 <= value <= 4:
                raise ValueError(f"{name} must be finite in [0,4]")


@dataclass(frozen=True)
class ProbeBundle:
    coords: np.ndarray
    faces: np.ndarray
    fit_probes: np.ndarray
    evaluation_probes: np.ndarray


def _polar_columns(columns: np.ndarray) -> tuple[np.ndarray, float]:
    eigenvalues, eigenvectors = np.linalg.eigh(columns.T @ columns)
    minimum = float(eigenvalues[0])
    if minimum <= 1e-10:
        return np.eye(3)[:, :2], minimum
    return columns @ (eigenvectors / np.sqrt(eigenvalues)) @ eigenvectors.T, minimum


def make_probes(spec: CaseSpec) -> ProbeBundle:
    """Synthetic truths encode probe moments, never enter the estimator API."""
    side = 9 if spec.pattern == "undersampled" else spec.side
    axis = np.linspace(-1.0, 1.0, side)
    coords = np.array([(x, y) for y in axis for x in axis])
    faces = []
    for y, x in product(range(side - 1), repeat=2):
        a = y * side + x
        faces.extend(((a, a + 1, a + side + 1), (a, a + side + 1, a + side)))
    point = coords[:, 0] + 1j * coords[:, 1]
    f2 = np.ones(len(coords), dtype=complex) * (1 + 0.2j)
    f4 = np.ones(len(coords), dtype=complex) * (0.6 + 0.2j)
    if spec.pattern in {"flat_defect", "f2_only", "f4_only", "undersampled"}:
        f2, f4 = point.copy(), point.copy()
    elif spec.pattern == "dipole":
        f2 = (point + 0.5) * np.conjugate(point - 0.5)
        f4 = f2.copy()
    elif spec.pattern == "core_depression":
        f2 = np.abs(point) ** 2 + 0j
        f4 = f2.copy()
    elif spec.pattern == "smooth_drift":
        f2 = np.exp(0.7j * coords[:, 0])
        f4 = f2.copy()
    if spec.pattern in {"zero", "f4_only"}:
        f2[:] = 0
    if spec.pattern in {"zero", "f2_only"}:
        f4[:] = 0
    f2 *= spec.amplitude
    f4 *= spec.amplitude
    coefficients = np.tile(
        np.sqrt(2) * np.array([[1, 0], [-1, 0], [0, 1], [0, -1]]), (2, 1)
    )
    # Separate physical arrays and independent noise streams on the two sides.
    fit_rng, eval_rng = [
        np.random.default_rng(s) for s in np.random.SeedSequence(spec.seed).spawn(2)
    ]
    fit, evaluation = [], []
    for row, (x, y) in enumerate(coords):
        curvature = 0.5 if spec.pattern == "holonomy_only" else 0.0
        normal = np.array([-curvature * x, -curvature * y, 1.0])
        normal /= np.linalg.norm(normal)
        frame, _ = _polar_columns((np.eye(3) - np.outer(normal, normal))[:, :2])
        fit_coefficients = coefficients * np.array([2.0, 1.0])
        if spec.pattern == "collapsed_support":
            fit_coefficients[:, 1] = 0.0
        mean = np.array([f2[row].real, f2[row].imag])
        a, b = f4[row].real, f4[row].imag
        covariance = np.array([[a, b], [b, -a]]) + (1.0 + abs(f4[row])) * np.eye(2)
        root = np.linalg.cholesky(covariance)
        fit.append(
            fit_coefficients @ frame.T + spec.noise * fit_rng.normal(size=(8, 3))
        )
        evaluation.append(
            (mean + coefficients @ root.T) @ frame.T
            + spec.noise * eval_rng.normal(size=(8, 3))
        )
    return ProbeBundle(
        coords, np.asarray(faces, dtype="<i8"), np.array(fit), np.array(evaluation)
    )


def fit_frames(fit_probes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Fit planes and a fixed-reference chart without evaluation data or labels."""
    values = np.asarray(fit_probes, dtype=float)
    if (
        values.ndim != 3
        or values.shape[1] < 4
        or values.shape[2] != 3
        or not np.isfinite(values).all()
    ):
        raise ValueError("finite fit probes must have shape (rows, probes>=4, 3)")
    frames, support = [], []
    for probes in values:
        centered = probes - probes.mean(axis=0)
        eigenvalues, eigenvectors = np.linalg.eigh(centered.T @ centered / len(probes))
        basis = eigenvectors[:, -2:]
        frame, reference_support = _polar_columns((basis @ basis.T)[:, :2])
        frames.append(frame)
        support.append(
            bool(
                eigenvalues[1] > 1e-6
                and eigenvalues[1] - eigenvalues[0] > 0.1 * max(eigenvalues[2], 1e-6)
                and reference_support > 0.1
            )
        )
    return np.array(frames), np.array(support, dtype=bool)


def _gauges(coords: np.ndarray, mode: str) -> np.ndarray:
    if mode not in GAUGES:
        raise ValueError("unknown gauge")
    result = np.tile(np.eye(2), (len(coords), 1, 1))
    if mode == "reflection":
        result[:, 1, 1] = -1
    elif mode == "local_o2":
        for row, (x, y) in enumerate(coords):
            angle = 2.1 * x - 1.3 * y
            c, s = np.cos(angle), np.sin(angle)
            result[row] = [[c, -s], [s, c]]
            if row % 3 == 0:
                result[row, :, 1] *= -1
    return result


def _branch(state: str, value: object, reason: str, coverage: float = 1.0) -> dict:
    return {
        "state": state,
        "value": value,
        "reason": reason,
        "coverage": coverage,
        "uncertainty": {
            "calibrated": False,
            "scope": "single-synthetic-unit; numerical diagnostics only",
        },
        "strata": "declared-domain-development-only",
    }


def _traceless(tensors: np.ndarray) -> np.ndarray:
    """Stable exact-trace-zero projection, including nearly isotropic moments."""
    a = (tensors[:, 0, 0] - tensors[:, 1, 1]) / 2
    b = (tensors[:, 0, 1] + tensors[:, 1, 0]) / 2
    result = np.empty_like(tensors)
    result[:, 0, 0], result[:, 1, 1] = a, -a
    result[:, 0, 1], result[:, 1, 0] = b, b
    return result


def _core(
    amplitude: np.ndarray,
    support: np.ndarray,
    coords: np.ndarray,
    faces: np.ndarray,
    field_hash: str,
) -> dict:
    """Charge-blind sampled depressions: no loops, winding, or truth accepted."""
    low = set(np.flatnonzero(amplitude <= CORE_CUTOFF).tolist())
    components = []
    adjacent = {i: set() for i in low}
    for face in faces:
        for a, b in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            if int(a) in low and int(b) in low:
                adjacent[int(a)].add(int(b))
                adjacent[int(b)].add(int(a))
    remaining = set(low)
    while remaining:
        todo, found = [min(remaining)], set()
        while todo:
            row = todo.pop()
            if row not in found:
                found.add(row)
                todo.extend(adjacent[row] - found)
        remaining -= found
        components.append(sorted(found))
    boundary_low = any(np.any(np.isclose(np.abs(coords[row]), 1.0)) for row in low)
    unresolved = not support.all() or len(low) == len(amplitude) or boundary_low
    count = None if unresolved else len(components)
    classification = (
        "unresolved"
        if unresolved
        else "zero"
        if count == 0
        else "one"
        if count == 1
        else "many"
    )
    record = _branch(
        "insufficient" if unresolved else "eligible",
        {
            "classification": classification,
            "candidate_count": count,
            "components": components,
        },
        "unsupported-or-nonlocalized-low-amplitude"
        if unresolved
        else "sampled-depressions-only-not-verified-zeros",
        float(np.mean(support)),
    )
    record.update(
        field_sha256=field_hash,
        charge_blind=True,
        cutoff=CORE_CUTOFF,
        kind="sampled-low-amplitude-components",
    )
    record["seal_sha256"] = canonical_json_sha256(record)
    return record


def _domain_loops(bundle: ProbeBundle) -> tuple[dict, dict]:
    coords, faces = bundle.coords, bundle.faces
    graph_input = GraphInput(
        primary_unit_id="synthetic-unit",
        vertex_ids=np.arange(len(coords), dtype="<i8"),
        states=coords,
    )
    domain = build_discrete_domain_complex(
        graph_input,
        faces,
        domain_id="declared-square",
        primary_unit_id="synthetic-unit",
    )
    unique_x = np.unique(coords[:, 0])
    spacing = float(np.min(np.diff(unique_x)))
    graph = construct_radius_graph(
        graph_input,
        RadiusGraphSpec(
            spec_id="declared-coordinate-neighbors",
            purpose=GraphPurpose.CYCLE_CONSTRUCTION,
            radius=spacing * 1.01,
        ),
    )
    rectangles = {
        "outer": (-1, 1, -1, 1),
        "inner": (-0.5, 0.5, -0.5, 0.5),
        "local_positive": (-0.75, -0.25, -0.25, 0.25),
        "local_negative": (0.25, 0.75, -0.25, 0.25),
        "offcore": (-0.25, 0.25, 0.5, 1.0),
    }
    loops, receipts = {}, {}
    face_coords = coords[domain.canonical_faces]
    for name, (xmin, xmax, ymin, ymax) in rectangles.items():
        inside = (
            (face_coords[:, :, 0] >= xmin)
            & (face_coords[:, :, 0] <= xmax)
            & (face_coords[:, :, 1] >= ymin)
            & (face_coords[:, :, 1] <= ymax)
        ).all(axis=1)
        cycle = define_boundary_cycle_class(
            domain,
            np.flatnonzero(inside),
            cycle_class_spec_id=name,
            primary_unit_id="synthetic-unit",
            matched_set_id="fixed-synthetic-loops",
        )
        attempt = bind_cycle_class(
            graph,
            cycle,
            BoundaryRefinementRule(
                rule_id="exact-every-boundary-edge", max_domain_edges_per_graph_edge=1
            ),
        )
        rows = cycle.boundary_vertex_rows
        loops[name] = (rows, attempt.matched)
        receipts[name] = {
            "matched": attempt.matched,
            "reason": attempt.reason,
            "boundary_vertex_rows": rows.tolist(),
            "boundary_sha256": cycle.fingerprint_sha256,
            "binding_sha256": None
            if attempt.binding is None
            else attempt.binding.fingerprint_sha256,
            "support_selected_before_fields": True,
            "max_domain_edges_per_graph_edge": 1,
        }
    return loops, {
        "domain_sha256": domain.fingerprint_sha256,
        "graph_sha256": graph.fingerprint_sha256,
        "graph_scope": "one-declared-coordinate-radius-graph; not-M1-law-or-three-by-three",
        "loops": receipts,
    }


def _loop_gate(
    rows: np.ndarray, matched: bool, coords: np.ndarray, support: np.ndarray
) -> str | None:
    if not matched:
        return "exact-boundary-unavailable"
    if not support[rows].all():
        return "fit-plane-or-reference-support-insufficient"
    edges = np.roll(coords[rows], -1, axis=0) - coords[rows]
    if np.max(np.linalg.norm(edges, axis=1)) > MAX_DOMAIN_EDGE:
        return "development-domain-resolution-insufficient"
    return None


def _geometry(
    rows: np.ndarray,
    matched: bool,
    coords: np.ndarray,
    frames: np.ndarray,
    support: np.ndarray,
    gauges: np.ndarray,
) -> dict:
    reason = _loop_gate(rows, matched, coords, support)
    if reason:
        return _branch("insufficient", None, reason, float(np.mean(support[rows])))
    transports, baseline, singular = [], [], []
    for a, b in zip(rows, np.roll(rows, -1), strict=True):
        connection = procrustes_connection(frames[a], frames[b])
        transports.append(connection.rotation.T)
        singular.append(float(connection.singular_values[-1]))
        baseline.append(gauges[b].T @ gauges[a])
    if min(singular) <= 0.2:
        return _branch("insufficient", None, "edge-plane-overlap-insufficient")
    full = compose_edge_transports(transports)
    reference = compose_edge_transports(baseline)
    relative = relative_holonomy(full, reference)
    # Return signed diagnostics in the pinned reference, not an arbitrary O(2) gauge.
    matrix = gauges[rows[0]] @ relative.matrix @ gauges[rows[0]].T
    angle = float(np.arctan2(matrix[1, 0], matrix[0, 0]))
    return _branch(
        "eligible",
        {
            "angle_rad": angle,
            "matrix": matrix.tolist(),
            "minimum_edge_overlap": min(singular),
            "above_development_threshold": abs(angle) > GEOMETRY_THRESHOLD_RAD,
        },
        "continuous-relative-transport-not-winding",
    )


def _winding(
    rows: np.ndarray,
    matched: bool,
    coords: np.ndarray,
    support: np.ndarray,
    values: np.ndarray,
    field_hash: str,
) -> dict:
    reason = _loop_gate(rows, matched, coords, support)
    if reason:
        record = _branch("insufficient", None, reason, float(np.mean(support[rows])))
    else:
        sample = values[rows, 0] + 1j * values[rows, 1]
        estimate = estimate_winding(
            sample, amplitude_floor=AMPLITUDE_FLOOR, branch_margin_rad=BRANCH_MARGIN_RAD
        )
        if not estimate.reliable:
            record = _branch(
                "insufficient",
                None,
                ";".join(estimate.failure_reasons),
                float(np.mean(np.abs(sample) > AMPLITUDE_FLOOR)),
            )
        else:
            record = _branch(
                "eligible",
                {
                    "unrounded_winding": estimate.closed_loop_angle_rad / (2 * np.pi),
                    "sampled_winding": estimate.nearest_integer,
                    "closure_residual": estimate.residual_cycles,
                    "minimum_amplitude": estimate.minimum_amplitude,
                    "maximum_edge_angle_rad": estimate.maximum_edge_angle_rad,
                },
                "sampled-principal-branch-interpolation-only",
            )
        record["diagnostic"] = {
            "unrounded_winding": estimate.closed_loop_angle_rad / (2 * np.pi),
            "closure_residual": estimate.residual_cycles,
            "minimum_amplitude": estimate.minimum_amplitude,
            "maximum_edge_angle_rad": estimate.maximum_edge_angle_rad,
            "sample_count": estimate.sample_count,
            "charge_authority": False,
        }
    record["field_sha256"] = field_hash
    return record


def measure_probes(bundle: ProbeBundle, *, gauge: str = "none") -> dict:
    """Measure unlabeled probes; no generator pattern or injected field accepted."""
    coords = np.asarray(bundle.coords)
    evaluation = np.asarray(bundle.evaluation_probes)
    side = math.isqrt(len(coords))
    expected = np.array(
        [(x, y) for y in np.linspace(-1, 1, side) for x in np.linspace(-1, 1, side)]
    )
    if side < 9 or side > 33 or side % 4 != 1 or not np.array_equal(coords, expected):
        raise ValueError(
            "prototype accepts only the bounded declared ordered square grid"
        )
    if evaluation.shape != bundle.fit_probes.shape or not np.isfinite(evaluation).all():
        raise ValueError("evaluation probes must match the finite fit probe layout")
    if np.shares_memory(bundle.fit_probes, evaluation):
        raise ValueError("fit and evaluation probes must not share memory")
    loops, domain_receipt = _domain_loops(bundle)  # Supports fixed before field reads.
    canonical_frames, support = fit_frames(bundle.fit_probes)
    gauges = _gauges(coords, gauge)
    frames = canonical_frames @ gauges
    identities = np.arange(len(coords), dtype="<i8")
    partition = validate_observation_partition(
        np.column_stack((identities, np.zeros_like(identities))),
        np.column_stack((identities, np.ones_like(identities))),
    )
    responses = evaluation.mean(axis=1)
    f2 = derive_f2_section(
        frames,
        responses,
        partition=partition,
        input_row_identities=identities,
        amplitude_floor=AMPLITUDE_FLOOR,
    )
    centered = evaluation - responses[:, None, :]
    local_probes = np.einsum("npd,ndi->npi", centered, frames)
    tensors = (
        np.einsum("npi,npj->nij", local_probes, local_probes) / evaluation.shape[1]
    )
    f4 = derive_f4_spin_two(
        _traceless(tensors),
        partition=partition,
        input_row_identities=identities,
        amplitude_floor=AMPLITUDE_FLOOR,
    )
    # Spin two is restored via its tensor, never with the F2 vector rule.
    reference_tensors = gauges @ f4.traceless_tensor @ np.swapaxes(gauges, 1, 2)
    reference_f4 = derive_f4_spin_two(
        _traceless(reference_tensors),
        partition=partition,
        input_row_identities=identities,
        amplitude_floor=AMPLITUDE_FLOOR,
    )
    reference_values = {
        "F2": np.einsum("nij,nj->ni", gauges, f2.values),
        "F4": reference_f4.section.values,
    }
    fields = {}
    for name, values in reference_values.items():
        amplitude = np.linalg.norm(values, axis=1)
        payload = {
            "hypothesis": name,
            "estimand": "full-evaluation-moment-field",
            "values": values.tolist(),
            "amplitude": amplitude.tolist(),
            "direction_defined": (amplitude > AMPLITUDE_FLOOR).tolist(),
            "fit_support": support.tolist(),
            "amplitude_floor": AMPLITUDE_FLOOR,
            "reference": "fit-only-plane-projector-polar-ambient-e1-e2",
            "interpolation": "declared-boundary-principal-angular-increments; no-continuum-extension-certified",
            "convention": "vector-angle"
            if name == "F2"
            else "doubled-director-angle-integer; not-divided-by-two",
            "domain_sha256": domain_receipt["domain_sha256"],
            "partition_sha256": partition.canonical_sha256,
            "fit_probe_sha256": _array_hash(bundle.fit_probes),
            "evaluation_probe_sha256": _array_hash(evaluation),
        }
        field_hash = canonical_json_sha256(payload)
        payload["field_sha256"] = field_hash
        payload["core"] = _core(amplitude, support, coords, bundle.faces, field_hash)
        fields[name] = payload
    # Both co-primary core seals exist before ANY field winding is computed.
    for name, payload in fields.items():
        values = reference_values[name]
        field_hash = payload["field_sha256"]
        payload["loops"] = {}
        for loop_name, (rows, matched) in loops.items():
            reverse = np.r_[rows[:1], rows[:0:-1]]
            payload["loops"][loop_name] = {
                "forward": _winding(rows, matched, coords, support, values, field_hash),
                "reverse": _winding(
                    reverse, matched, coords, support, values, field_hash
                ),
            }
    geometry = {}
    for name, (rows, matched) in loops.items():
        reverse = np.r_[rows[:1], rows[:0:-1]]
        geometry[name] = {
            "forward": _geometry(rows, matched, coords, frames, support, gauges),
            "reverse": _geometry(reverse, matched, coords, frames, support, gauges),
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "development_thresholds": development_thresholds(),
        "co_primary_hypotheses": ["F2", "F4"],
        "winner_selected": False,
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
        },
        "provenance": {
            "partition": partition.to_dict(),
            "fit_frames_sha256": _array_hash(canonical_frames),
            "fit_only_arguments": True,
            "cross_fit_scope": "synthetic-generator-disjoint-streams; batch-role-labels-not-attested-external-identities",
            "external_probe_provenance_verified": False,
            "gauge": gauge,
            "effective_side": side,
        },
        "domain": domain_receipt,
        "fields": fields,
        "geometry": geometry,
        "phase": _branch("not_evaluated", None, "no-regime-or-checkpoint-series", 0),
        "transition": _branch(
            "not_evaluated", None, "no-regime-or-checkpoint-series", 0
        ),
        "residual_estimands": _branch(
            "not_evaluated",
            None,
            "must-recompute-full-field-not-subtract-winding-integers",
            0,
        ),
    }


def measure_case(spec: CaseSpec) -> dict:
    gauge = (
        "local_o2"
        if spec.pattern == "pure_gauge" and spec.gauge == "none"
        else spec.gauge
    )
    result = measure_probes(make_probes(spec), gauge=gauge)
    result["spec"] = asdict(spec)
    return result


def _wilson(successes: int, total: int) -> list[float] | None:
    if total == 0:
        return None
    z = 1.96
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = (
        z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    )
    return [max(0.0, center - half), min(1.0, center + half)]


def development_surface() -> list[dict]:
    """Crossed descriptive panel; three independent noise seeds, not graph cells."""
    rows = []
    for pattern, amplitude, noise, side in product(
        ("flat_defect", "coherent"), (0.25, 1.0), (0.0, 0.15), (9, 17)
    ):
        reports = [
            measure_case(CaseSpec(pattern, side, amplitude, noise, seed))
            for seed in (0, 1, 2)
        ]
        for hypothesis in ("F2", "F4"):
            branches = [
                report["fields"][hypothesis]["loops"]["outer"]["forward"]
                for report in reports
            ]
            eligible = [b for b in branches if b["state"] == "eligible"]
            detected = sum(b["value"]["sampled_winding"] != 0 for b in eligible)
            rows.append(
                {
                    "pattern": pattern,
                    "hypothesis": hypothesis,
                    "amplitude": amplitude,
                    "noise": noise,
                    "side": side,
                    "readout_scope": "outer-loop-sampled-winding-only",
                    "seed_count": 3,
                    "eligible_count": len(eligible),
                    "abstention_count": 3 - len(eligible),
                    "coverage": len(eligible) / 3,
                    "detected_count": detected,
                    "conditional_detection_rate": None
                    if not eligible
                    else detected / len(eligible),
                    "conditional_false_positive_rate": None
                    if pattern != "coherent" or not eligible
                    else detected / len(eligible),
                    "conditional_wilson_95": None
                    if noise == 0
                    else _wilson(detected, len(eligible)),
                    "uncertainty_scope": "illustrative-independent-noise-seeds-only; zero-noise-seeds-are-identical-not-replication",
                    "qualified_detection_limit": False,
                    "trials": [
                        {
                            "seed": seed,
                            "field_sha256": report["fields"][hypothesis][
                                "field_sha256"
                            ],
                            "core": report["fields"][hypothesis]["core"],
                            "loops": report["fields"][hypothesis]["loops"],
                            "geometry": report["geometry"],
                        }
                        for seed, report in enumerate(reports)
                    ],
                }
            )
    return rows


def run_development_demo() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "development_only_not_qualification",
        "thresholds": {
            "amplitude_floor": AMPLITUDE_FLOOR,
            "core_cutoff": CORE_CUTOFF,
            "max_domain_edge": MAX_DOMAIN_EDGE,
            "geometry_threshold_rad": GEOMETRY_THRESHOLD_RAD,
            "branch_margin_rad": BRANCH_MARGIN_RAD,
        },
        "threshold_transfer_authorized": False,
        "cases": [measure_case(CaseSpec(pattern)) for pattern in PATTERNS],
        "surface": development_surface(),
        "remaining": [
            "crossed-M1-transport-qualification",
            "three-by-three-representation-graph-panel",
            "full-pass-through-local-linear-residual-estimand-comparison",
            "held-out-detection-limit-calibration",
            "phase-regime-and-transition",
            "model-access-and-protocol-freeze",
        ],
    }


def self_test() -> dict:
    reports = {p: measure_case(CaseSpec(p)) for p in PATTERNS}
    checks = []
    for field in ("F2", "F4"):
        checks.extend(
            [
                reports["flat_defect"]["fields"][field]["loops"]["outer"]["forward"][
                    "value"
                ]["sampled_winding"]
                == 1,
                reports["coherent"]["fields"][field]["loops"]["outer"]["forward"][
                    "value"
                ]["sampled_winding"]
                == 0,
                reports["zero"]["fields"][field]["core"]["value"]["classification"]
                == "unresolved",
                reports["dipole"]["fields"][field]["loops"]["local_negative"][
                    "forward"
                ]["value"]["sampled_winding"]
                == -1,
                reports["undersampled"]["fields"][field]["loops"]["outer"]["forward"][
                    "state"
                ]
                == "insufficient",
            ]
        )
    checks.append(
        reports["holonomy_only"]["geometry"]["outer"]["forward"]["value"][
            "above_development_threshold"
        ]
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
