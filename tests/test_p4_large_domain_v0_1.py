from __future__ import annotations

import json
import sys
from itertools import product
from pathlib import Path

import numpy as np
import pytest
from scipy import sparse

from spirallens.graphs.common import GraphPurpose


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prototype_p4_large_domain_v0_1 as prototype  # noqa: E402


old = prototype.old
backend = prototype.backend
FAMILIES = prototype.FAMILIES
ESTIMANDS = prototype.ESTIMANDS
PARITY_SPECS = (
    prototype.ScaleSpec(pattern="quadratic_excess"),
    prototype.ScaleSpec(pattern="quadratic_excess", warp=0.75),
    prototype.ScaleSpec(pattern="curved_coherent"),
    prototype.ScaleSpec(pattern="curved_coherent", probe_noise=0.03, seed=7),
    prototype.ScaleSpec(pattern="input_identity"),
    prototype.ScaleSpec(pattern="no_signal"),
    prototype.ScaleSpec(pattern="collapsed_support"),
)


def _old_spec(spec):
    return old.GraphCrossSpec(
        pattern=spec.pattern,
        side=spec.side,
        probe_noise=spec.probe_noise,
        warp=spec.warp,
        seed=spec.seed,
    )


def _old_field(row, estimand, hypothesis):
    branch = "controls" if estimand == "origin_centered" else "estimands"
    return row[branch][estimand]["fields"][hypothesis]


def _assert_numeric_value(actual, expected):
    assert actual.keys() == expected.keys()
    for key in actual:
        if isinstance(expected[key], bool):
            assert actual[key] is expected[key], key
        else:
            np.testing.assert_allclose(actual[key], expected[key], atol=1e-9, rtol=1e-9)


@pytest.fixture(scope="module", params=PARITY_SPECS)
def parity(request):
    spec = request.param
    bundle = old.make_graph_cross_probes(_old_spec(spec))
    native_graphs, _ = old.build_graphs(
        bundle.graph_input, GraphPurpose.FIELD_ESTIMATION
    )
    report, arrays = prototype.measure_case(spec)
    previous = old.measure_graph_cross(bundle)
    return spec, bundle, native_graphs, report, arrays, previous


def test_small_probe_inputs_and_actual_graph_edges_match_exhaustive_predecessor(parity):
    _, bundle, native_graphs, report, arrays, _ = parity
    np.testing.assert_array_equal(arrays["coords"], bundle.observations.coords)
    np.testing.assert_array_equal(arrays["faces"], bundle.observations.faces)
    np.testing.assert_array_equal(arrays["graph_states"], bundle.graph_input.states)
    for new_role, old_role in (
        ("plane", "plane_fit_probes"),
        ("baseline", "baseline_fit_probes"),
        ("evaluation", "evaluation_probes"),
    ):
        np.testing.assert_allclose(
            arrays[new_role], getattr(bundle.observations, old_role), atol=1e-10, rtol=0
        )
    for family in FAMILIES:
        np.testing.assert_array_equal(
            arrays[family + "_edges"], native_graphs[family].canonical_edges
        )
        assert report["graphs"][family]["approximate_neighbors"] is False
        assert report["graphs"][family]["native_graph_receipt"] is False


def test_pooled_covariances_frames_support_and_affine_coefficients_have_small_parity(
    parity,
):
    _, bundle, native_graphs, report, arrays, previous = parity
    for family in FAMILIES:
        carrier, pooling = old.prepare_field_graph(
            bundle.observations, native_graphs[family]
        )
        frames, support = old.chain.fit_frames(carrier.plane_fit_probes)
        np.testing.assert_allclose(
            arrays[family + "_frames"], frames, atol=1e-10, rtol=0
        )
        np.testing.assert_array_equal(arrays[family + "_support"], support)
        np.testing.assert_allclose(
            arrays[family + "_pooled_covariance"],
            pooling["pooled_covariances"],
            atol=1e-10,
            rtol=0,
        )
        new_baseline = report["rows"][family]["baseline"]
        old_baseline = previous["rows"][family]["baseline"]
        assert new_baseline["state"] == old_baseline["state"]
        for hypothesis in ("F2", "F4"):
            actual = new_baseline["coefficients"][hypothesis]
            expected = old_baseline["coefficients"][hypothesis]
            if expected is None:
                assert actual is None
            else:
                expected = np.asarray(expected)
                if hypothesis == "F4":
                    expected = np.column_stack((expected[:, 0, 0], expected[:, 0, 1]))
                np.testing.assert_allclose(actual, expected, atol=1e-10, rtol=0)


def test_all_fields_and_exact_charge_blind_component_memberships_have_small_parity(
    parity,
):
    _, _, _, report, arrays, previous = parity
    for family, estimand, hypothesis in product(FAMILIES, ESTIMANDS, ("F2", "F4")):
        actual = report["rows"][family]["fields"][estimand][hypothesis]
        expected = _old_field(previous["rows"][family], estimand, hypothesis)
        key = f"{family}_{estimand}_{hypothesis}"
        assert actual["missing"] is (expected["values"] is None)
        assert actual["core"]["state"] == expected["core"]["state"]
        for name in ("classification", "candidate_count"):
            assert actual["core"][name] == expected["core"]["value"][name]
        if actual["missing"]:
            assert key + "_values" not in arrays
            continue
        np.testing.assert_allclose(
            arrays[key + "_values"], expected["values"], atol=1e-10, rtol=0
        )
        np.testing.assert_allclose(
            arrays[key + "_amplitude"], expected["amplitude"], atol=1e-10, rtol=0
        )
        low, labels = arrays[key + "_low_vertices"], arrays[key + "_component_labels"]
        components = [
            sorted(low[labels == label].tolist()) for label in np.unique(labels)
        ]
        assert sorted(components) == sorted(expected["core"]["value"]["components"])
        assert actual["core"]["charge_blind"] is True


def test_all_nine_cells_all_five_loops_both_directions_keep_exact_states_and_admitted_values(
    parity,
):
    _, _, _, report, _, previous = parity
    assert len(report["cells"]) == 9
    assert {(c["field_graph"], c["loop_graph"]) for c in report["cells"]} == set(
        product(FAMILIES, repeat=2)
    )
    for actual, expected in zip(report["cells"], previous["cells"], strict=True):
        assert (actual["field_graph"], actual["loop_graph"]) == (
            expected["field_graph"],
            expected["loop_graph"],
        )
        assert len(actual["loops"]) == 10
        for loop_key, loop in actual["loops"].items():
            name, direction = loop_key.rsplit("_", 1)
            before = expected["geometry"][name][direction]
            after = loop["geometry"]
            assert after["state"] == before["state"]
            if before["state"] == "eligible":
                _assert_numeric_value(after["value"], before["value"])
            else:
                assert after["value"] is before["value"] is None
            for estimand, hypothesis in product(ESTIMANDS, ("F2", "F4")):
                after = loop["fields"][estimand][hypothesis]
                before = _old_field(expected, estimand, hypothesis)["loops"][name][
                    direction
                ]
                context = (
                    actual["field_graph"],
                    actual["loop_graph"],
                    loop_key,
                    estimand,
                    hypothesis,
                )
                assert after["state"] == before["state"], context
                if before["state"] == "eligible":
                    _assert_numeric_value(after["value"], before["value"])
                    assert after["reason"] == before["reason"], context
                else:
                    assert after["value"] is before["value"] is None
                    if (
                        estimand == "pass_through"
                        and hypothesis == "F4"
                        and "diagnostic" in after
                    ):
                        # Prospective algebraic I2 correction: no tiny numerical
                        # anisotropy is assigned a direction or admitted charge.
                        assert "amplitude_at_or_below_floor" in after["reason"]
                        assert "amplitude_at_or_below_floor" in before["reason"]
                        assert after["diagnostic"]["minimum_amplitude"] == 0
                        assert (
                            before["diagnostic"]["minimum_amplitude"]
                            <= old.chain.AMPLITUDE_FLOOR
                        )
                    else:
                        assert after["reason"] == before["reason"], context


def test_reports_and_arrays_are_finite_and_preserve_unqualified_scope(parity):
    _, _, _, report, arrays, _ = parity
    json.dumps(report, allow_nan=False)
    assert all(np.isfinite(array).all() for array in arrays.values())
    assert report["design"]["axis_sizes"] == [3, 3, 1]
    assert report["design"]["all_nine_required"] is True
    assert report["design"]["independent_replicates"] is False
    assert report["scope"] == {
        "synthetic_only": True,
        "model_accessed": False,
        "gpu_used": False,
        "claim_ceiling": "level_0",
        "scientific_authority": False,
        "verified_core": False,
        "phase": "not_evaluated",
        "transition": "not_evaluated",
    }


def test_reference_positive_partial_and_abstention_outcomes_are_not_conflated(parity):
    spec, _, _, report, _, _ = parity
    for hypothesis in ("F2", "F4"):
        summary = report["summary"]["winding"]["residual_affine"][hypothesis]
        assert summary["required_cell_count"] == 9
        assert summary["eligible_cell_count"] + summary["insufficient_cell_count"] == 9
        assert summary["qualified_graph_invariance"] is False
        assert summary["independent_replication_count"] is None
        if spec.pattern == "quadratic_excess":
            eligible = 4 if spec.warp else 9
            assert summary["eligible_cell_count"] == eligible
            assert summary["eligible_values"] == [2] * eligible
            assert summary["complete_grid_agreement"] is (eligible == 9)
        elif spec.pattern in ("input_identity", "no_signal", "collapsed_support"):
            assert summary["eligible_cell_count"] == 0
            assert summary["eligible_values"] == []
            assert summary["eligible_subset_agrees"] is None
            assert summary["complete_grid_agreement"] is False
    if spec.pattern == "curved_coherent" and spec.probe_noise:
        assert report["summary"]["geometry"]["eligible_cell_count"] == 9
        assert report["summary"]["geometry"]["state"] == "complete_disagreement"


@pytest.mark.parametrize(
    "changes",
    [
        {"side": True},
        {"side": 9},
        {"side": 1000},
        {"k": True},
        {"k": 4},
        {"k": 64},
        {"seed": True},
        {"seed": -1},
        {"seed": 2**32},
        {"pattern": "model"},
        {"probe_noise": True},
        {"probe_noise": -0.1},
        {"probe_noise": float("nan")},
        {"probe_noise": float("inf")},
        {"warp": True},
        {"warp": -0.1},
        {"warp": float("nan")},
        {"warp": float("inf")},
    ],
)
def test_prospective_resource_and_finite_input_bounds(changes):
    with pytest.raises(ValueError):
        prototype.ScaleSpec(**changes)


@pytest.mark.parametrize("side", [17, 33])
def test_sparse_domain_boundaries_are_exact_without_dense_operators(side):
    domain = backend.make_domain(side)
    assert sparse.isspmatrix_csr(domain["d1"])
    assert sparse.isspmatrix_csr(domain["d2"])
    boundary_squared = domain["d1"] @ domain["d2"]
    boundary_squared.eliminate_zeros()
    assert boundary_squared.nnz == 0
    assert set(domain["loops"]) == set(backend.RECTANGLES)
    assert all(
        r["induced_boundary_verified"] for r in domain["receipt"]["loops"].values()
    )
    assert (
        domain["receipt"]["sparse_domain_bytes"]
        < domain["receipt"]["hypothetical_dense_float64_bytes"]["d1"]
    )


def test_supported_neighbors_cannot_promote_a_raw_rank_one_center():
    domain = backend.make_domain(17)
    coords = domain["coords"]
    probes = prototype.make_probes(prototype.ScaleSpec(), coords)
    origin = int(np.flatnonzero((coords == 0).all(axis=1))[0])
    probes["plane"][origin, :, 1:] = 0
    states = np.column_stack((coords, np.zeros((len(coords), 2))))
    for graph in backend.build_graphs(states).values():
        _, support, baseline, locality, pooled = prototype.prepare_row(
            coords, probes, graph
        )
        assert np.linalg.matrix_rank(pooled[origin]) >= 2
        assert not support[origin]
        assert locality["original_supported_count"] == len(coords) - 1
        assert baseline["state"] == "insufficient"
        assert all(value is None for value in baseline["coefficients"].values())


@pytest.mark.parametrize(
    "cap",
    [
        "MAX_TOTAL_QUERY_CANDIDATES",
        "MAX_BATCH_QUERY_CANDIDATES",
        "MAX_GRAPH_NNZ",
        "MAX_SHARED_PRODUCTS",
        "MAX_BATCH_SHARED_PRODUCTS",
    ],
)
def test_sparse_resource_bound_failures_are_explicit_not_empty_success(
    monkeypatch, cap
):
    coords = backend.make_domain(17)["coords"]
    states = np.column_stack((coords, np.zeros((len(coords), 2))))
    monkeypatch.setattr(backend, cap, 1)
    with pytest.raises(backend.SparseBudgetError):
        backend.build_graphs(states)


def test_three_baseline_seals_before_evaluation_and_thirty_six_core_seals_before_loops(
    monkeypatch,
):
    counts = {"baselines": 0, "cores": 0, "loops": 0}
    captured = {}
    make = prototype.make_probes
    prepare = prototype.prepare_row
    moments = prototype.moments
    core = prototype.core_record
    geometry, winding = old.chain._geometry, old.chain._winding

    def capture(*args, **kwargs):
        result = make(*args, **kwargs)
        captured.update(result)
        return result

    def checked_prepare(*args, **kwargs):
        result = prepare(*args, **kwargs)
        assert result[2]["seal_sha256"]
        counts["baselines"] += 1
        return result

    def checked_moments(frames, probes):
        if np.shares_memory(probes, captured["evaluation"]):
            assert counts["baselines"] == 3
        return moments(frames, probes)

    def checked_core(*args, **kwargs):
        result = core(*args, **kwargs)
        assert result[0]["seal_sha256"]
        counts["cores"] += 1
        return result

    def checked_loop(function):
        def wrapped(*args, **kwargs):
            assert counts["baselines"] == 3
            assert counts["cores"] == 36
            counts["loops"] += 1
            return function(*args, **kwargs)

        return wrapped

    monkeypatch.setattr(prototype, "make_probes", capture)
    monkeypatch.setattr(prototype, "prepare_row", checked_prepare)
    monkeypatch.setattr(prototype, "moments", checked_moments)
    monkeypatch.setattr(prototype, "core_record", checked_core)
    monkeypatch.setattr(old.chain, "_geometry", checked_loop(geometry))
    monkeypatch.setattr(old.chain, "_winding", checked_loop(winding))
    prototype.measure_case(prototype.ScaleSpec())
    assert counts == {"baselines": 3, "cores": 36, "loops": 390}


def test_campaign_keeps_declared_size_and_neighborhood_matrix_without_outcome_selection():
    specs = prototype.campaign_specs()
    assert len(specs) == 27
    assert len(set(specs)) == 27
    assert {s.side for s in specs} == {17, 33, 65, 129, 257}
    assert {s.k for s in specs} == {8, 16, 32}
    assert sum(s.k == 8 for s in specs) == 15
    assert {(s.side, s.k) for s in specs if s.k > 8} == set(
        product((65, 257), (16, 32))
    )


def test_serialized_small_run_is_numeric_replay_and_cannot_overwrite(tmp_path):
    output = tmp_path / "small"
    report, arrays = prototype.measure_case(
        prototype.ScaleSpec(pattern="input_identity"), output
    )
    saved = json.loads((output / "report.json").read_text())
    assert saved == report
    assert (
        report["array_artifact"]["sha256"]
        == old.chain.hashlib.sha256((output / "arrays.npz").read_bytes()).hexdigest()
    )
    with np.load(output / "arrays.npz", allow_pickle=False) as loaded:
        assert set(loaded.files) == set(arrays)
        for key, expected in arrays.items():
            np.testing.assert_array_equal(loaded[key], expected)
    with pytest.raises(FileExistsError):
        prototype.measure_case(prototype.ScaleSpec(), output)
