#!/usr/bin/env python3
"""Sparse single-domain synthetic scaling; no model, CUDA, or qualification.

Separate successor: fixed-k refinement changes both resolution and locality.
All baseline and charge-blind component seals precede any loop measurement.
The declared isotropic pass-through F4 is represented analytically as zero.
"""

from __future__ import annotations

import argparse
import json
import platform
import resource
import time
from dataclasses import asdict, dataclass
from itertools import product
from pathlib import Path

import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import connected_components

import p4_sparse_graph_backend_v0_1 as backend
import prototype_p4_graph_cross_v0_1 as old


SCHEMA = "spirallens.p4-large-domain-synthetic.v0.1"
FAMILIES = old.FAMILIES
ESTIMANDS = old.comparison.ESTIMANDS + ("origin_centered",)


@dataclass(frozen=True)
class ScaleSpec:
    side: int = 17
    k: int = 8
    pattern: str = "curved_coherent"
    probe_noise: float = 0.0
    warp: float = 0.0
    seed: int = 0

    def __post_init__(self):
        if type(self.side) is not int or self.side not in (17, 33, 65, 129, 257):
            raise ValueError("prospective side ladder is 17,33,65,129,257")
        if type(self.k) is not int or self.k not in (8, 16, 32):
            raise ValueError("prospective neighbor budgets are 8,16,32")
        if self.pattern not in (
            "curved_coherent",
            "quadratic_excess",
            "input_identity",
            "no_signal",
            "collapsed_support",
        ):
            raise ValueError("unknown synthetic construction")
        if type(self.seed) is not int or not 0 <= self.seed < 2**32:
            raise ValueError("seed must be uint32")
        for value in (self.probe_noise, self.warp):
            if isinstance(value, bool) or not np.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("finite noise/warp in [0,1] required")


def _hash(value):
    return old.chain._array_hash(np.asarray(value))


def _seal(value):
    return old.canonical_json_sha256(value)


def _write(path: Path, value):
    with path.open("x") as stream:
        json.dump(value, stream, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _polar(columns):
    gram = np.swapaxes(columns, -1, -2) @ columns
    eigenvalues, vectors = np.linalg.eigh(gram)
    safe = eigenvalues[:, 0] > 1e-10
    inverse = (
        vectors / np.sqrt(np.maximum(eigenvalues[:, None, :], 1e-30))
    ) @ np.swapaxes(vectors, -1, -2)
    frames = columns @ inverse
    frames[~safe] = np.eye(3)[:, :2]
    return frames, eigenvalues[:, 0]


def fit_covariances(covariances):
    eigenvalues, vectors = np.linalg.eigh(covariances)
    basis = vectors[:, :, -2:]
    frames, reference = _polar((basis @ np.swapaxes(basis, -1, -2))[:, :, :2])
    support = (
        (eigenvalues[:, 1] > 1e-6)
        & (
            eigenvalues[:, 1] - eigenvalues[:, 0]
            > 0.1 * np.maximum(eigenvalues[:, 2], 1e-6)
        )
        & (reference > 0.1)
    )
    return frames, support


def _covariance(probes):
    centered = probes - probes.mean(axis=1, keepdims=True)
    return np.einsum("npi,npj->nij", centered, centered) / probes.shape[1]


def make_probes(spec, coords):
    x, y = coords.T
    z = x + 1j * y
    f2, f4 = z.copy(), np.zeros_like(z)
    if spec.pattern in ("quadratic_excess", "collapsed_support"):
        f2, f4 = z + 0.25 * z**2, z + 0.25 * z**2
    elif spec.pattern == "curved_coherent":
        f2, f4 = np.full_like(z, 1 + 0.2j), np.full_like(z, 0.6 + 0.2j)
    elif spec.pattern == "no_signal":
        f2[:], f4[:] = 0, 0
    curvature = 0.5 if spec.pattern == "curved_coherent" else 0
    normals = np.column_stack((-curvature * x, -curvature * y, np.ones(len(x))))
    normals /= np.linalg.norm(normals, axis=1)[:, None]
    frames, _ = _polar(
        (np.eye(3) - np.einsum("ni,nj->nij", normals, normals))[:, :, :2]
    )
    cube = np.array(list(product((-1.0, 1.0), repeat=3)))
    fit_coefficients = cube[:, :2] * [
        2.0,
        0.0 if spec.pattern == "collapsed_support" else 1.0,
    ]
    plane = np.einsum("pi,ndi->npd", fit_coefficients, frames)
    mean = np.einsum("ndi,ni->nd", frames, np.column_stack((f2.real, f2.imag)))
    tensor = tensor_from_values(np.column_stack((f4.real, f4.imag)))
    covariance = (1 + np.abs(f4))[:, None, None] * np.eye(
        3
    ) + frames @ tensor @ np.swapaxes(frames, -1, -2)
    root = np.linalg.cholesky(covariance)
    response = mean[:, None, :] + np.einsum("pi,ndi->npd", cube, root)
    rngs = [
        np.random.default_rng(s) for s in np.random.SeedSequence(spec.seed).spawn(3)
    ]
    return {
        "plane": plane + spec.probe_noise * rngs[0].normal(size=plane.shape),
        "baseline": response + spec.probe_noise * rngs[1].normal(size=response.shape),
        "evaluation": response + spec.probe_noise * rngs[2].normal(size=response.shape),
    }


def tensor_from_values(values):
    tensor = np.empty((len(values), 2, 2))
    tensor[:, 0, 0], tensor[:, 1, 1] = values[:, 0], -values[:, 0]
    tensor[:, 0, 1], tensor[:, 1, 0] = values[:, 1], values[:, 1]
    return tensor


def moments(frames, probes):
    mean = probes.mean(axis=1)
    local = np.einsum("npd,ndi->npi", probes - mean[:, None, :], frames)
    covariance = np.einsum("npi,npj->nij", local, local) / probes.shape[1]
    return {
        "F2": np.einsum("ndi,nd->ni", frames, mean),
        "F4": np.column_stack(
            (
                (covariance[:, 0, 0] - covariance[:, 1, 1]) / 2,
                (covariance[:, 0, 1] + covariance[:, 1, 0]) / 2,
            )
        ),
    }


def prepare_row(coords, probes, graph):
    covariance = _covariance(probes["plane"])
    _, original_support = fit_covariances(covariance)
    pooled = (
        (graph.adjacency @ covariance.reshape(len(coords), 9))
        + covariance.reshape(len(coords), 9)
    ) / (graph.degree[:, None] + 1)
    pooled = pooled.reshape(-1, 3, 3)
    edge_dist = np.linalg.norm(
        coords[graph.canonical_edges[:, 0]] - coords[graph.canonical_edges[:, 1]],
        axis=1,
    )
    maximum = np.zeros(len(coords))
    for axis in (0, 1):
        np.maximum.at(maximum, graph.canonical_edges[:, axis], edge_dist)
    permitted = original_support & (graph.degree >= 2) & (maximum <= 0.75)
    effective = pooled.copy()
    effective[~permitted] = 0
    frames, support = fit_covariances(effective)
    support &= permitted
    targets = np.array([[0, 0], [-0.5, 0], [0.5, 0], [0, -0.5], [0, 0.5]])
    stencil = np.array(
        [
            np.flatnonzero(np.isclose(coords, target, rtol=0, atol=1e-12).all(axis=1))[
                0
            ]
            for target in targets
        ]
    )
    design = np.column_stack((np.ones(5), coords[stencil]))
    valid = bool(
        support[stencil].all()
        and np.linalg.matrix_rank(design) == 3
        and np.linalg.cond(design) < 100
    )
    coefficients = {name: None for name in ("F2", "F4")}
    if valid:
        values = moments(frames[stencil], probes["baseline"][stencil])
        coefficients = {
            name: np.linalg.lstsq(design, data, rcond=None)[0]
            for name, data in values.items()
        }
    baseline = {
        "state": "eligible" if valid else "insufficient",
        "stencil_rows": stencil.tolist(),
        "coefficients": {
            name: None if data is None else data.tolist()
            for name, data in coefficients.items()
        },
        "baseline_probe_sha256": _hash(probes["baseline"]),
        "frames_sha256": _hash(frames),
        "stencil_radius": 0.5,
        "coefficient_basis": "F2-vector-and-F4-traceless-tensor-(a,b)",
    }
    baseline["seal_sha256"] = _seal(baseline)
    locality = {
        "maximum_domain_distance": float(maximum.max()),
        "neighbor_mass_fraction_range": [
            float((graph.degree.min() + 1) / len(coords)),
            float((graph.degree.max() + 1) / len(coords)),
        ],
        "original_supported_count": int(original_support.sum()),
        "pooled_supported_count": int(support.sum()),
        "pooled_covariance_sha256": _hash(pooled),
        "support_sha256": _hash(support),
        "plane_probe_sha256": _hash(probes["plane"]),
    }
    return frames, support, baseline, locality, pooled


def core_record(amplitude, support, core_adjacency, coords, field_hash):
    low = np.flatnonzero(amplitude <= old.chain.CORE_CUTOFF)
    count, labels = connected_components(core_adjacency[low][:, low], directed=False)
    boundary_low = bool(np.isclose(np.abs(coords[low]), 1).any())
    unresolved = bool(not support.all() or len(low) == len(amplitude) or boundary_low)
    classification = (
        "unresolved"
        if unresolved
        else "zero"
        if count == 0
        else "one"
        if count == 1
        else "many"
    )
    record = {
        "state": "insufficient" if unresolved else "eligible",
        "classification": classification,
        "candidate_count": None if unresolved else int(count),
        "low_vertex_count": len(low),
        "low_vertex_sha256": _hash(low),
        "component_labels_sha256": _hash(labels),
        "component_sizes": np.bincount(labels).tolist(),
        "field_sha256": field_hash,
        "charge_blind": True,
        "cutoff": old.chain.CORE_CUTOFF,
        "verified_core": False,
    }
    record["seal_sha256"] = _seal(record)
    return record, low, labels


def measure_case(spec: ScaleSpec, output: Path | None = None):
    started = time.monotonic()
    if output is not None:
        output.mkdir(parents=True, exist_ok=False)
    domain = backend.make_domain(spec.side)
    coords = domain["coords"]
    x, y = coords.T
    states = np.column_stack(
        (
            x + spec.warp * x**3,
            y + spec.warp * y**3,
            0.2 * x * y,
            0.15 * np.sin(np.pi * x) * np.sin(np.pi * y),
        )
    )
    graphs = backend.build_graphs(states, k=spec.k)
    graph_seconds = time.monotonic() - started
    core_edges = domain["canonical_edges"]
    core_adjacency = sparse.coo_matrix(
        (
            np.ones(len(core_edges) * 2),
            (
                np.r_[core_edges[:, 0], core_edges[:, 1]],
                np.r_[core_edges[:, 1], core_edges[:, 0]],
            ),
        ),
        shape=(len(coords), len(coords)),
    ).tocsr()
    probes = make_probes(spec, coords)
    data = {
        "coords": coords,
        "faces": domain["faces"],
        "graph_states": states,
        **probes,
    }
    prepared, rows = {}, {}
    for family in FAMILIES:
        frames, support, baseline, locality, pooled = prepare_row(
            coords, probes, graphs[family]
        )
        prepared[family] = (frames, support, baseline)
        rows[family] = {"baseline": baseline, "locality": locality, "fields": {}}
        (
            data[family + "_frames"],
            data[family + "_support"],
            data[family + "_pooled_covariance"],
        ) = frames, support, pooled
        data[family + "_edges"] = graphs[family].canonical_edges
    # All three baselines now exist; no evaluation moment has been read.
    origin = int(np.flatnonzero((coords == 0).all(axis=1))[0])
    design = np.column_stack((np.ones(len(coords)), coords))
    field_arrays = {}
    for family in FAMILIES:
        frames, support, baseline = prepared[family]
        full = moments(frames, probes["evaluation"])
        # Algebraic isotropic covariance in an orthonormal two-plane is I2.
        passthrough = {
            "F2": np.einsum(
                "ndi,nd->ni", frames, np.column_stack((coords, np.zeros(len(coords))))
            ),
            "F4": np.zeros((len(coords), 2)),
        }
        affine = {
            name: None
            if baseline["coefficients"][name] is None
            else design @ np.array(baseline["coefficients"][name])
            for name in ("F2", "F4")
        }
        estimands = {
            "full": full,
            "pass_through": passthrough,
            "local_affine": affine,
            "residual_affine": {
                h: None if affine[h] is None else full[h] - affine[h] for h in full
            },
            "residual_pass_through": {h: full[h] - passthrough[h] for h in full},
            "origin_centered": {
                h: full[h] - full[h][origin] if support[origin] else None for h in full
            },
        }
        field_arrays[family] = estimands
        for estimand, fields in estimands.items():
            rows[family]["fields"][estimand] = {}
            for hypothesis, values in fields.items():
                key = f"{family}_{estimand}_{hypothesis}"
                record = {
                    "values_sha256": None if values is None else _hash(values),
                    "support_sha256": _hash(
                        support if values is not None else np.zeros_like(support)
                    ),
                    "estimand": estimand,
                    "hypothesis": hypothesis,
                    "baseline_sha256": baseline["seal_sha256"]
                    if estimand in {"local_affine", "residual_affine"}
                    else None,
                    "domain_sha256": domain["receipt"]["domain_sha256"],
                    "frames_sha256": _hash(frames),
                    "graph_sha256": graphs[family].fingerprint_sha256,
                    "evaluation_probe_sha256": _hash(probes["evaluation"])
                    if estimand not in {"pass_through", "local_affine"}
                    else None,
                    "missing": values is None,
                }
                record["field_sha256"] = _seal(record)
                if values is None:
                    core = {
                        "state": "insufficient",
                        "classification": "unresolved",
                        "candidate_count": None,
                        "charge_blind": True,
                        "field_sha256": record["field_sha256"],
                    }
                    core["seal_sha256"] = _seal(core)
                    record["core"] = core
                else:
                    amplitude = np.linalg.norm(values, axis=1)
                    core, low, labels = core_record(
                        amplitude,
                        support,
                        core_adjacency,
                        coords,
                        record["field_sha256"],
                    )
                    record.update(
                        core=core,
                        amplitude_quantiles=np.quantile(
                            amplitude, [0, 0.25, 0.5, 0.75, 1]
                        ).tolist(),
                        direction_defined_count=int(
                            (amplitude > old.chain.AMPLITUDE_FLOOR).sum()
                        ),
                    )
                    (
                        data[key + "_values"],
                        data[key + "_amplitude"],
                        data[key + "_low_vertices"],
                        data[key + "_component_labels"],
                    ) = values, amplitude, low, labels
                rows[family]["fields"][estimand][hypothesis] = record
    # All 36 charge-blind core seals exist before any winding or holonomy.
    cells = []
    gauges = np.tile(np.eye(2), (len(coords), 1, 1))
    for family in FAMILIES:
        frames, support, _ = prepared[family]
        readouts = {}
        for name, path in domain["loops"].items():
            match = {
                f: bool(np.asarray(graphs[f].adjacency[path, np.roll(path, -1)]).all())
                for f in FAMILIES
            }
            directions = {"forward": path, "reverse": np.r_[path[:1], path[:0:-1]]}
            for direction, vertices in directions.items():
                geometry = old.chain._geometry(
                    vertices, any(match.values()), coords, frames, support, gauges
                )
                fields = {}
                for estimand in ESTIMANDS:
                    fields[estimand] = {}
                    for hypothesis in ("F2", "F4"):
                        values = field_arrays[family][estimand][hypothesis]
                        field_hash = rows[family]["fields"][estimand][hypothesis][
                            "field_sha256"
                        ]
                        fields[estimand][hypothesis] = (
                            old.chain._branch(
                                "insufficient",
                                None,
                                "origin-plane-reference-insufficient"
                                if estimand == "origin_centered"
                                else "baseline-unavailable-no-field-fabricated",
                                0,
                            )
                            if values is None
                            else old.chain._winding(
                                vertices,
                                any(match.values()),
                                coords,
                                support,
                                values,
                                field_hash,
                            )
                        )
                readouts[name + "_" + direction] = {
                    "geometry": geometry,
                    "fields": fields,
                    "matches": match,
                }
        for loop_family in FAMILIES:
            loops = {}
            for name, readout in readouts.items():
                if readout["matches"][loop_family]:
                    loops[name] = {
                        "geometry": readout["geometry"],
                        "fields": readout["fields"],
                    }
                else:
                    unavailable = old.chain._branch(
                        "insufficient", None, "cycle-boundary-not-coverable", 0
                    )
                    loops[name] = {
                        "geometry": unavailable,
                        "fields": {
                            e: {h: unavailable for h in ("F2", "F4")} for e in ESTIMANDS
                        },
                    }
            cells.append(
                {"field_graph": family, "loop_graph": loop_family, "loops": loops}
            )
    distinct = len({_hash(g.canonical_edges) for g in graphs.values()}) == 3
    summary = {
        "geometry": old._aggregate(
            [c["loops"]["outer_forward"]["geometry"] for c in cells],
            distinct=distinct,
            geometry=True,
        ),
        "winding": {
            e: {
                h: old._aggregate(
                    [c["loops"]["outer_forward"]["fields"][e][h] for c in cells],
                    distinct=distinct,
                )
                for h in ("F2", "F4")
            }
            for e in ESTIMANDS
        },
    }
    report = {
        "schema_version": SCHEMA,
        "spec": asdict(spec),
        "vertex_count": len(coords),
        "graphs": {f: g.receipt for f, g in graphs.items()},
        "domain": domain["receipt"],
        "rows": rows,
        "cells": cells,
        "summary": summary,
        "loop_vertices": {k: v.tolist() for k, v in domain["loops"].items()},
        "chronology": {
            "baselines_before_evaluation": True,
            "core_seal_count_before_loops": 36,
        },
        "design": {
            "axis_sizes": [3, 3, 1],
            "isotropic_pass_through_f4": "analytic-traceless-I2-exact-zero",
            "refinement_changes_resolution_and_locality": True,
            "same_seed_is_not_coordinate_paired_noise": True,
            "independent_replicates": False,
            "all_nine_required": True,
        },
        "scope": {
            "synthetic_only": True,
            "model_accessed": False,
            "gpu_used": False,
            "claim_ceiling": "level_0",
            "scientific_authority": False,
            "verified_core": False,
            "phase": "not_evaluated",
            "transition": "not_evaluated",
        },
        "timing": {
            "graph_domain_seconds": graph_seconds,
            "measurement_seconds": time.monotonic() - started,
        },
        "peak_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        * (1 if platform.system() == "Darwin" else 1024),
    }
    if output is not None:
        np.savez_compressed(output / "arrays.npz", **data)
        report["timing"]["total_with_serialization_seconds"] = (
            time.monotonic() - started
        )
        report["array_artifact"] = {
            "file": "arrays.npz",
            "bytes": (output / "arrays.npz").stat().st_size,
            "sha256": old.chain.hashlib.sha256(
                (output / "arrays.npz").read_bytes()
            ).hexdigest(),
        }
        report["peak_rss_bytes"] = int(
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        ) * (1 if platform.system() == "Darwin" else 1024)
        _write(output / "report.json", report)
    return report, data


def campaign_specs():
    specs = [
        ScaleSpec(side=side, k=8, pattern=pattern, probe_noise=noise)
        for side in (17, 33, 65, 129, 257)
        for pattern, noise in (
            ("quadratic_excess", 0.0),
            ("curved_coherent", 0.0),
            ("curved_coherent", 0.03),
        )
    ]
    specs += [
        ScaleSpec(side=side, k=k, pattern=pattern, probe_noise=noise)
        for side in (65, 257)
        for k in (16, 32)
        for pattern, noise in (
            ("quadratic_excess", 0.0),
            ("curved_coherent", 0.0),
            ("curved_coherent", 0.03),
        )
    ]
    return specs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--case", type=int)
    parser.add_argument("--plan", action="store_true")
    args = parser.parse_args()
    specs = campaign_specs()
    if args.plan:
        args.output.mkdir(parents=True, exist_ok=False)
        _write(
            args.output / "plan.json",
            {
                "schema_version": SCHEMA,
                "case_count": len(specs),
                "cases": [asdict(s) for s in specs],
                "thresholds": old.chain.development_thresholds(),
                "timeout_seconds_per_case": 300,
                "address_space_limit_gib": 16,
                "disk_budget_gib": 8,
                "selection_performed": False,
                "scientific_authority": False,
            },
        )
        print(json.dumps({"planned": len(specs), "output": str(args.output)}))
        return 0
    if args.case is None or not 0 <= args.case < len(specs):
        parser.error("a valid --case or --plan is required")
    report, _ = measure_case(specs[args.case], args.output)
    print(
        json.dumps(
            {
                "case": args.case,
                "spec": report["spec"],
                "n": report["vertex_count"],
                "summary": report["summary"],
                "timing": report["timing"],
                "peak_rss_bytes": report["peak_rss_bytes"],
            },
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
