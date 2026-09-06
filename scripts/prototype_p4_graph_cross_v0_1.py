#!/usr/bin/env python3
"""Synthetic 3 field graphs x 3 exact-boundary graphs x 1 fixed core complex.

Graph-conditioned fit moments change rows; columns test availability of the
same oriented boundary. This is development, not independent replication,
graph qualification, model topology, or an execution authorization.
"""

from __future__ import annotations

import argparse
import copy
import json
from dataclasses import asdict, dataclass, replace
from itertools import combinations, product

import numpy as np

import prototype_p4_estimand_comparison_v0_1 as comparison
import prototype_p4_partial_patterns_v0_1 as chain
from spirallens.core.canonical import canonical_json_sha256
from spirallens.graphs import (
    BoundaryRefinementRule,
    GraphInput,
    GraphPurpose,
    MutualKnnSpec,
    RadiusGraphSpec,
    SharedNeighborSpec,
    bind_cycle_class,
    build_discrete_domain_complex,
    construct_mutual_knn,
    construct_radius_graph,
    construct_shared_neighbor_graph,
    define_boundary_cycle_class,
    measure_graph_diversity,
)
from spirallens.graphs.common import coordinate_order_invariant_euclidean_norm


SCHEMA_VERSION = "spirallens.p4-graph-cross-development.v0.1"
FAMILIES = ("mutual-knn", "fixed-radius", "shared-neighbor")
PATTERNS = comparison.PATTERNS + ("collapsed_substrate",)
NEIGHBORS = 8
SCALE_NEIGHBORS = 4
RADIUS_MULTIPLIER = 1.15
MIN_SHARED = 3
MIN_DEGREE = 2
MAX_POOL_DOMAIN_DISTANCE = 0.75
GEOMETRY_AGREEMENT_FRO = 0.02


@dataclass(frozen=True)
class GraphCrossSpec:
    pattern: str = "quadratic_excess"
    side: int = 17
    warp: float = 0.0
    graph_noise: float = 0.0
    probe_noise: float = 0.0
    seed: int = 0
    gauge: str = "none"

    def __post_init__(self) -> None:
        if (
            self.pattern not in PATTERNS
            or type(self.side) is not int
            or self.side not in (9, 17)
        ):
            raise ValueError("bounded cross requires known pattern and side 9 or 17")
        comparison.ComparisonSpec(
            "input_identity", self.side, self.probe_noise, self.seed, self.gauge
        )
        for name, maximum in (("warp", 2.0), ("graph_noise", 1.0)):
            value = getattr(self, name)
            if (
                isinstance(value, (bool, np.bool_))
                or not isinstance(value, (int, float))
                or not np.isfinite(value)
                or not 0 <= value <= maximum
            ):
                raise ValueError(f"{name} is outside its finite development bound")


@dataclass(frozen=True)
class GraphCrossBundle:
    observations: comparison.ComparisonBundle
    graph_input: GraphInput


def make_graph_cross_probes(spec: GraphCrossSpec) -> GraphCrossBundle:
    pattern = (
        "curved_coherent" if spec.pattern == "collapsed_substrate" else spec.pattern
    )
    observations = comparison.make_comparison_probes(
        comparison.ComparisonSpec(
            pattern, spec.side, spec.probe_noise, spec.seed, spec.gauge
        )
    )
    x, y = observations.coords.T
    states = np.column_stack(
        (
            x + spec.warp * x**3,
            y + spec.warp * y**3,
            0.2 * x * y,
            0.15 * np.sin(np.pi * x) * np.sin(np.pi * y),
        )
    )
    rng = np.random.default_rng(np.random.SeedSequence(spec.seed).spawn(4)[3])
    spacing = 2 / (int(np.sqrt(len(x))) - 1)
    states += spec.graph_noise * spacing * rng.normal(size=states.shape)
    if spec.pattern == "collapsed_substrate":
        states[:] = 0
    graph_input = GraphInput(
        primary_unit_id="synthetic-graph-cross",
        vertex_ids=np.arange(len(x), dtype="<i8"),
        states=states,
    )
    return GraphCrossBundle(observations, graph_input)


def build_graphs(graph_input: GraphInput, purpose: GraphPurpose) -> tuple[dict, dict]:
    """Fixed field-blind construction; no observations, loop values, or selector."""
    if not isinstance(purpose, GraphPurpose):
        raise ValueError("graph purpose must be declared")
    count = len(graph_input.vertex_ids)
    if count not in (81, 289):
        raise ValueError("graph cross is bounded to 81 or 289 rows")
    local_distances = []
    for row in range(count):
        distances = coordinate_order_invariant_euclidean_norm(
            graph_input.states - graph_input.states[row], axis=1
        )
        distances[row] = np.inf
        local_distances.append(
            float(np.partition(distances, SCALE_NEIGHBORS - 1)[SCALE_NEIGHBORS - 1])
        )
    scale = float(np.median(local_distances))
    parameters = {
        "neighbor_count": NEIGHBORS,
        "scale_neighbor_count": SCALE_NEIGHBORS,
        "scale": scale,
        "radius_multiplier": RADIUS_MULTIPLIER,
        "minimum_shared_neighbors": MIN_SHARED,
        "selection_performed": False,
        "threshold_transfer_authorized": False,
    }
    if not np.isfinite(scale) or scale <= 0:
        return {name: None for name in FAMILIES}, {
            "parameters": parameters,
            "families": {
                name: {
                    "state": "insufficient",
                    "reason": "nonpositive-support-state-scale",
                    "canonical_edges": None,
                }
                for name in FAMILIES
            },
            "distinct_edge_sets": False,
            "diversity": None,
        }
    graphs = {
        "mutual-knn": construct_mutual_knn(
            graph_input, MutualKnnSpec("cross-mutual", purpose, NEIGHBORS)
        ),
        "fixed-radius": construct_radius_graph(
            graph_input,
            RadiusGraphSpec("cross-radius", purpose, RADIUS_MULTIPLIER * scale),
        ),
        "shared-neighbor": construct_shared_neighbor_graph(
            graph_input,
            SharedNeighborSpec("cross-shared", purpose, NEIGHBORS, MIN_SHARED),
        ),
    }
    receipts = {}
    for name, graph in graphs.items():
        receipts[name] = {
            "state": "constructed",
            "reason": "development-only-not-qualified",
            "receipt_sha256": graph.fingerprint_sha256,
            "edge_order_sha256": graph.edge_order_sha256,
            "canonical_edges": graph.canonical_edges.tolist(),
            "edge_count": len(graph.canonical_edges),
            "degree": graph.degree.tolist(),
            "specification": graph.specification.to_dict(),
        }
    distinct = len({g.edge_order_sha256 for g in graphs.values()}) == 3
    return graphs, {
        "parameters": parameters,
        "families": receipts,
        "distinct_edge_sets": distinct,
        "diversity": measure_graph_diversity(tuple(graphs.values())).to_dict(),
    }


def prepare_field_graph(
    observations: comparison.ComparisonBundle, graph
) -> tuple[comparison.ComparisonBundle, dict]:
    """Pool centered fit covariances only; carrier probes are not observations."""
    raw = observations.plane_fit_probes
    comparison._validate_probes(observations.coords, raw)
    _, original_support = chain.fit_frames(raw)
    centered = raw - raw.mean(axis=1, keepdims=True)
    covariances = np.einsum("npi,npj->nij", centered, centered) / raw.shape[1]
    neighbors = [set((row,)) for row in range(len(raw))]
    if graph is not None:
        if graph.specification.purpose is not GraphPurpose.FIELD_ESTIMATION:
            raise ValueError("field pooling requires field-estimation graph")
        if len(graph.graph_input.vertex_ids) != len(raw):
            raise ValueError("field graph and probe rows differ")
        for a, b in graph.canonical_edges:
            neighbors[int(a)].add(int(b))
            neighbors[int(b)].add(int(a))
    coefficients = np.array(list(product((-1.0, 1.0), repeat=3)))
    carriers, pooled, distances, degrees, permitted = [], [], [], [], []
    for row, vertices in enumerate(neighbors):
        indices = sorted(vertices)
        covariance = covariances[indices].mean(axis=0)
        eigenvalues, eigenvectors = np.linalg.eigh(covariance)
        if eigenvalues[0] < -1e-10:
            raise ValueError("pooled covariance not numerically positive semidefinite")
        root = (eigenvectors * np.sqrt(np.maximum(eigenvalues, 0))) @ eigenvectors.T
        distance = float(
            np.max(
                np.linalg.norm(
                    observations.coords[indices] - observations.coords[row], axis=1
                )
            )
        )
        degree = len(indices) - 1
        valid = (
            graph is not None
            and original_support[row]
            and degree >= MIN_DEGREE
            and distance <= MAX_POOL_DOMAIN_DISTANCE
        )
        carriers.append(coefficients @ root.T if valid else np.zeros((8, 3)))
        pooled.append(covariance)
        distances.append(distance)
        degrees.append(degree)
        permitted.append(bool(valid))
    carriers = np.asarray(carriers)
    _, final_support = chain.fit_frames(carriers)
    receipt = {
        "rule": "uniform-self-plus-neighbors-average-of-per-vertex-centered-fit-covariances",
        "carrier_kind": "deterministic-eight-point-moment-carrier-not-new-observations",
        "raw_plane_probe_sha256": chain._array_hash(raw),
        "pooled_covariance_sha256": chain._array_hash(np.array(pooled)),
        "carrier_sha256": chain._array_hash(carriers),
        "field_graph_sha256": None if graph is None else graph.fingerprint_sha256,
        "edge_order_sha256": None if graph is None else graph.edge_order_sha256,
        "original_support": original_support.tolist(),
        "carrier_permitted": permitted,
        "pooled_support": final_support.tolist(),
        "original_support_required": True,
        "evaluation_read": False,
        "neighbor_count_excluding_self": degrees,
        "neighbor_mass_fraction": [(degree + 1) / len(raw) for degree in degrees],
        "max_neighbor_domain_distance": distances,
        "locality_gate_domain_units": MAX_POOL_DOMAIN_DISTANCE,
        "minimum_neighbor_count": MIN_DEGREE,
        "pooled_covariances": np.asarray(pooled).tolist(),
    }
    receipt["pooling_sha256"] = canonical_json_sha256(receipt)
    return replace(observations, plane_fit_probes=carriers), receipt


def bind_loops(
    graph_input: GraphInput, coords: np.ndarray, faces: np.ndarray, loop_graphs: dict
) -> tuple[dict, dict]:
    domain = build_discrete_domain_complex(
        graph_input,
        faces,
        domain_id="cross-declared-square",
        primary_unit_id=graph_input.primary_unit_id,
    )
    rectangles = {
        "outer": (-1, 1, -1, 1),
        "inner": (-0.5, 0.5, -0.5, 0.5),
        "local_positive": (-0.75, -0.25, -0.25, 0.25),
        "local_negative": (0.25, 0.75, -0.25, 0.25),
        "offcore": (-0.25, 0.25, 0.5, 1),
    }
    face_coords = coords[domain.canonical_faces]
    loops, receipts = {}, {}
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
            primary_unit_id=graph_input.primary_unit_id,
            matched_set_id="graph-cross-common-boundary",
        )
        loops[name] = cycle.boundary_vertex_rows
        bindings = {}
        for family, graph in loop_graphs.items():
            if graph is None:
                bindings[family] = {
                    "matched": False,
                    "reason": "loop-graph-unavailable",
                    "binding_sha256": None,
                }
            else:
                attempt = bind_cycle_class(
                    graph,
                    cycle,
                    BoundaryRefinementRule("cross-exact-every-boundary-edge", 1),
                )
                bindings[family] = {
                    "matched": attempt.matched,
                    "reason": attempt.reason,
                    "binding_sha256": None
                    if attempt.binding is None
                    else attempt.binding.fingerprint_sha256,
                }
        receipts[name] = {
            "boundary_vertex_rows": cycle.boundary_vertex_rows.tolist(),
            "boundary_sha256": cycle.fingerprint_sha256,
            "max_domain_edges_per_graph_edge": 1,
            "bindings": bindings,
        }
    return loops, {
        "domain_sha256": domain.fingerprint_sha256,
        "coords_sha256": chain._array_hash(coords),
        "core_triangulation_sha256": chain._array_hash(faces),
        "loops": receipts,
    }


def _prepare_row(observations, pooling, domain, baseline, gauge):
    """No loop readouts here: prepare all three rows before visiting any cell."""
    frames, support = chain.fit_frames(observations.plane_fit_probes)
    gauges = chain._gauges(observations.coords, gauge)
    full = comparison._reference_moments(
        frames, gauges, observations.evaluation_probes, 2
    )
    input_mean = np.column_stack((observations.coords, np.zeros(len(frames))))
    passthrough = {
        "F2": np.einsum("ndi,nd->ni", frames, input_mean),
        "F4": chain._traceless(np.einsum("ndi,ndj->nij", frames, frames)),
    }
    design = np.column_stack((np.ones(len(frames)), observations.coords))
    affine = {name: None for name in full}
    if baseline["state"] == "eligible":
        affine = {
            name: np.einsum(
                "nc,c...->n...", design, np.asarray(baseline["coefficients"][name])
            )
            for name in full
        }
    origin = int(np.flatnonzero((observations.coords == 0).all(axis=1))[0])
    arrays = {
        "full": full,
        "pass_through": passthrough,
        "local_affine": affine,
        "residual_affine": {
            name: None if affine[name] is None else full[name] - affine[name]
            for name in full
        },
        "residual_pass_through": {
            name: full[name] - passthrough[name] for name in full
        },
        "origin_centered": {
            name: full[name] - full[name][origin] if support[origin] else None
            for name in full
        },
    }
    records = {}
    for estimand, fields in arrays.items():
        records[estimand] = {"fields": {}}
        for name, data in fields.items():
            parents = {
                "pooling_sha256": pooling["pooling_sha256"],
                "field_graph_sha256": pooling["field_graph_sha256"],
                "plane_probe_sha256": pooling["carrier_sha256"],
            }
            if estimand == "full":
                parents["evaluation_probe_sha256"] = chain._array_hash(
                    observations.evaluation_probes
                )
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
                if estimand == "origin_centered":
                    parents["origin_row"] = origin
                else:
                    target = (
                        "local_affine"
                        if estimand == "residual_affine"
                        else "pass_through"
                    )
                    parents["subtracted_field_sha256"] = records[target]["fields"][
                        name
                    ]["field_sha256"]
            records[estimand]["fields"][name] = comparison._make_field(
                name,
                estimand,
                data,
                support,
                observations,
                domain["domain_sha256"],
                parents,
                baseline,
            )
    return (
        {
            "estimands": {name: records[name] for name in comparison.ESTIMANDS},
            "controls": {"origin_centered": records["origin_centered"]},
            "baseline": baseline,
            "pooling": pooling,
            "frames_sha256": chain._array_hash(frames),
        },
        frames,
        support,
        gauges,
    )


def _unavailable(field, reason):
    result = chain._branch("insufficient", None, reason, 0)
    if field is not None:
        result["field_sha256"] = field["field_sha256"]
    return result


def _aggregate(branches, *, distinct: bool, geometry: bool = False) -> dict:
    eligible = [b for b in branches if b["state"] == "eligible"]
    if geometry:
        matrices = [np.asarray(b["value"]["matrix"]) for b in eligible]
        spread = (
            max(
                (float(np.linalg.norm(a - b)) for a, b in combinations(matrices, 2)),
                default=0.0,
            )
            if matrices
            else None
        )
        agree = None if not eligible else spread <= GEOMETRY_AGREEMENT_FRO
        values = [b["value"]["angle_rad"] for b in eligible]
    else:
        values = [b["value"]["sampled_winding"] for b in eligible]
        agree = None if not eligible else len(set(values)) == 1
        spread = None
    complete = len(eligible) == 9
    state = (
        "incomplete_support"
        if not complete
        else "graph_diversity_insufficient"
        if not distinct
        else "complete_agreement"
        if agree
        else "complete_disagreement"
    )
    return {
        "state": state,
        "required_cell_count": 9,
        "eligible_cell_count": len(eligible),
        "insufficient_cell_count": 9 - len(eligible),
        "coverage": len(eligible) / 9,
        "eligible_subset_agrees": agree,
        "eligible_values": values,
        "max_pairwise_matrix_frobenius": spread,
        "all_nine_eligible": complete,
        "distinct_edge_sets": distinct,
        "complete_grid_agreement": bool(complete and distinct and agree),
        "qualified_graph_invariance": False,
        "independent_replication_count": None,
        "uncertainty": "not-calibrated; graph cells are repeated measurements",
    }


def measure_graph_cross(bundle: GraphCrossBundle, *, gauge: str = "none") -> dict:
    observations, graph_input = bundle.observations, bundle.graph_input
    comparison._validate_probes(
        observations.coords,
        observations.plane_fit_probes,
        observations.baseline_fit_probes,
    )
    if len(observations.coords) not in (81, 289) or not np.array_equal(
        graph_input.vertex_ids, np.arange(len(observations.coords))
    ):
        raise ValueError("graph/probe exact ordered row identity mismatch")
    if any(
        np.shares_memory(observations.evaluation_probes, role)
        for role in (observations.plane_fit_probes, observations.baseline_fit_probes)
    ):
        raise ValueError("probe roles must not share memory")
    field_graphs, field_receipt = build_graphs(
        graph_input, GraphPurpose.FIELD_ESTIMATION
    )
    loop_graphs, loop_receipt = build_graphs(
        graph_input, GraphPurpose.CYCLE_CONSTRUCTION
    )
    loops, domain = bind_loops(
        graph_input, observations.coords, observations.faces, loop_graphs
    )
    conditioned, poolings, baselines = {}, {}, {}
    for family in FAMILIES:
        conditioned[family], poolings[family] = prepare_field_graph(
            observations, field_graphs[family]
        )
        baselines[family] = comparison.fit_baseline(
            observations.coords,
            conditioned[family].plane_fit_probes,
            observations.baseline_fit_probes,
            gauge=gauge,
        )
    # All graph choices and baseline seals precede any evaluation moment read.
    comparison._validate_probes(observations.coords, observations.evaluation_probes)
    rows, numerics = {}, {}
    for family in FAMILIES:
        row, frames, support, gauges = _prepare_row(
            conditioned[family], poolings[family], domain, baselines[family], gauge
        )
        rows[family] = row
        numerics[family] = (frames, support, gauges)
    # All 36 field/core seals now exist. Same boundary -> one numeric readout per row.
    cells = []
    for field_family in FAMILIES:
        row = rows[field_family]
        frames, support, gauges = numerics[field_family]
        readouts = {}
        for category in ("estimands", "controls"):
            readouts[category] = {}
            for estimand, record in row[category].items():
                readouts[category][estimand] = {"fields": {}}
                for hypothesis, field in record["fields"].items():
                    result = {
                        "field_sha256": field["field_sha256"],
                        "core_sha256": field["core"]["seal_sha256"],
                        "loops": {},
                    }
                    for name, path in loops.items():
                        any_match = any(
                            item["matched"]
                            for item in domain["loops"][name]["bindings"].values()
                        )
                        result["loops"][name] = {}
                        for direction, vertices in (
                            ("forward", path),
                            ("reverse", np.r_[path[:1], path[:0:-1]]),
                        ):
                            if field["values"] is None:
                                value = _unavailable(field, field["missing_reason"])
                            else:
                                value = chain._winding(
                                    vertices,
                                    any_match,
                                    observations.coords,
                                    np.asarray(field["fit_support"]),
                                    np.asarray(field["values"]),
                                    field["field_sha256"],
                                )
                            result["loops"][name][direction] = value
                    readouts[category][estimand]["fields"][hypothesis] = result
        geometry = {}
        for name, path in loops.items():
            any_match = any(
                item["matched"] for item in domain["loops"][name]["bindings"].values()
            )
            geometry[name] = {
                "forward": chain._geometry(
                    path,
                    any_match,
                    observations.coords,
                    frames @ gauges,
                    support,
                    gauges,
                ),
                "reverse": chain._geometry(
                    np.r_[path[:1], path[:0:-1]],
                    any_match,
                    observations.coords,
                    frames @ gauges,
                    support,
                    gauges,
                ),
            }
        for loop_family in FAMILIES:
            cell = copy.deepcopy(readouts)
            cell.update(
                field_graph=field_family,
                loop_graph=loop_family,
                geometry=copy.deepcopy(geometry),
            )
            for category in ("estimands", "controls"):
                for record in cell[category].values():
                    for field in record["fields"].values():
                        for name, branch in field["loops"].items():
                            binding = domain["loops"][name]["bindings"][loop_family]
                            for direction in ("forward", "reverse"):
                                if not binding["matched"]:
                                    branch[direction] = _unavailable(
                                        field, binding["reason"]
                                    )
                                branch[direction]["loop_binding_sha256"] = binding[
                                    "binding_sha256"
                                ]
            for name, branch in cell["geometry"].items():
                binding = domain["loops"][name]["bindings"][loop_family]
                for direction in ("forward", "reverse"):
                    if not binding["matched"]:
                        branch[direction] = _unavailable(None, binding["reason"])
                    branch[direction]["loop_binding_sha256"] = binding["binding_sha256"]
            cells.append(cell)
    distinct = (
        field_receipt["distinct_edge_sets"] and loop_receipt["distinct_edge_sets"]
    )
    winding_summary = {
        name: {
            hypothesis: _aggregate(
                [
                    cell["estimands"][name]["fields"][hypothesis]["loops"]["outer"][
                        "forward"
                    ]
                    for cell in cells
                ],
                distinct=distinct,
            )
            for hypothesis in ("F2", "F4")
        }
        for name in comparison.ESTIMANDS
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "development_only_not_qualification",
        "families": list(FAMILIES),
        "rows": rows,
        "cells": cells,
        "graphs": {"field": field_receipt, "loop": loop_receipt},
        "graph_input": {
            "fingerprint_sha256": graph_input.fingerprint_sha256,
            "state_sha256": graph_input.state_sha256,
            "vertex_order_sha256": graph_input.vertex_order_sha256,
            "primary_unit_id": graph_input.primary_unit_id,
        },
        "domain": domain,
        "summary": {
            "scope": "outer-loop-only; all other loop cells retained",
            "winding": winding_summary,
            "geometry": _aggregate(
                [cell["geometry"]["outer"]["forward"] for cell in cells],
                distinct=distinct,
                geometry=True,
            ),
        },
        "design": {
            "axis_sizes": [3, 3, 1],
            "core_axis": "fixed-declared-domain-triangulation-not-graph-free",
            "all_36_core_seals_before_loop_readout": True,
            "same_boundary_numeric_readouts_shared_across_supported_columns": True,
            "numeric_column_diversity_expected": False,
            "graph_cells_are_independent_replicates": False,
            "geometry_scope": "field-graph-fit-plane-reference-not-residual-model-geometry",
            "geometry_agreement_frobenius_tolerance": GEOMETRY_AGREEMENT_FRO,
        },
        "scope": {
            "synthetic_only": True,
            "model_free": True,
            "model_accessed": False,
            "network_accessed": False,
            "furnace_accessed": False,
            "protocol_freeze": False,
            "execution_authorized": False,
            "external_probe_provenance_verified": False,
            "raw_role_identity_attested": False,
        },
        "claim_boundary": {
            "claim_ceiling": "level_0",
            "scientific_authority": False,
            "topology_authority": False,
            "semantic_authority": False,
            "publication_authority": False,
            "verified_core": False,
            "model_derived_order_parameter": False,
            "complete_m8": False,
            "m1_qualified": False,
            "winner_selected": False,
        },
        "phase": chain._branch(
            "not_evaluated", None, "no-regime-or-checkpoint-series", 0
        ),
        "transition": chain._branch(
            "not_evaluated", None, "no-regime-or-checkpoint-series", 0
        ),
    }


def measure_case(spec: GraphCrossSpec) -> dict:
    report = measure_graph_cross(make_graph_cross_probes(spec), gauge=spec.gauge)
    report["spec"] = asdict(spec)
    return report


def run_development_demo() -> dict:
    specs = [
        GraphCrossSpec(pattern)
        for pattern in (
            "quadratic_excess",
            "input_identity",
            "affine_offset",
            "no_signal",
            "f2_nonlinear_only",
            "f4_nonlinear_only",
            "collapsed_support",
            "collapsed_substrate",
        )
    ]
    specs += [
        GraphCrossSpec("quadratic_excess", warp=0.75),
        GraphCrossSpec("curved_coherent", probe_noise=0.03),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "development_only_not_qualification",
        "cases": [measure_case(spec) for spec in specs],
    }


def run_nuisance_panel() -> dict:
    cases = []
    for side, warp, noise, seed in product((9, 17), (0.0, 0.75), (0.0, 0.2), (0, 1)):
        spec = GraphCrossSpec("curved_coherent", side, warp, noise, 0.0, seed)
        report = measure_case(spec)
        cases.append(
            {
                "spec": asdict(spec),
                "summary": report["summary"],
                "graph_parameters": report["graphs"]["field"]["parameters"],
                "distinct_edge_sets": report["graphs"]["field"]["distinct_edge_sets"],
                "graph_input": report["graph_input"],
                "locality": {
                    family: {
                        "pooling_sha256": row["pooling"]["pooling_sha256"],
                        "max_neighbor_domain_distance": max(
                            row["pooling"]["max_neighbor_domain_distance"]
                        ),
                        "neighbor_mass_fraction_range": [
                            min(row["pooling"]["neighbor_mass_fraction"]),
                            max(row["pooling"]["neighbor_mass_fraction"]),
                        ],
                        "original_supported_count": sum(
                            row["pooling"]["original_support"]
                        ),
                        "pooled_supported_count": sum(row["pooling"]["pooled_support"]),
                        "locality_gate_domain_units": row["pooling"][
                            "locality_gate_domain_units"
                        ],
                    }
                    for family, row in report["rows"].items()
                },
                "outer_cells": [
                    {
                        "field_graph": cell["field_graph"],
                        "loop_graph": cell["loop_graph"],
                        "geometry": cell["geometry"]["outer"]["forward"],
                        "estimands": {
                            name: {
                                hyp: cell["estimands"][name]["fields"][hyp]["loops"][
                                    "outer"
                                ]["forward"]
                                for hyp in ("F2", "F4")
                            }
                            for name in comparison.ESTIMANDS
                        },
                    }
                    for cell in report["cells"]
                ],
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "development_only_not_qualification",
        "case_count": len(cases),
        "cases": cases,
        "held_out_confirmation": False,
        "threshold_selection": False,
        "uncertainty": "not-calibrated; zero-noise seeds duplicate inputs, graph cells are repeated measures",
    }


def self_test() -> dict:
    quadratic = measure_case(GraphCrossSpec())
    collapsed = measure_case(GraphCrossSpec("collapsed_substrate"))
    checks = [
        len(quadratic["cells"]) == 9,
        quadratic["graphs"]["field"]["distinct_edge_sets"],
        quadratic["summary"]["winding"]["residual_affine"]["F2"][
            "complete_grid_agreement"
        ],
        all(
            cell["geometry"]["outer"]["forward"]["state"] == "insufficient"
            for cell in collapsed["cells"]
        ),
    ]
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
    mode.add_argument("--nuisance-panel", action="store_true")
    args = parser.parse_args(argv)
    report = (
        self_test()
        if args.self_test
        else run_nuisance_panel()
        if args.nuisance_panel
        else run_development_demo()
    )
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return int(report.get("status") == "fail")


if __name__ == "__main__":
    raise SystemExit(main())
