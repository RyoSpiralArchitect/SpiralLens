from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prototype_p4_one_arm_zoom_v0_1 as kernel  # noqa: E402
import run_p4_one_arm_zoom_v0_1 as runner  # noqa: E402


@pytest.fixture(scope="module")
def pair():
    return kernel.measure_pair(kernel.ZoomSpec())


def test_registered_grid_keeps_exact_old_anchors_and_denominator():
    specs = kernel.case_specs()
    assert len(specs) == 99
    assert runner.sha(ROOT / runner.PROTOCOL) == runner.PROTOCOL_SHA256
    for i, w in enumerate(kernel.WINDOWS):
        points = kernel.grid(w)
        assert len(points) == len(set(points)) == 33
        assert [points[j] for j in (0, 16, 32)] == list(map(float, w[3:6]))
        assert all(a < b for a, b in zip(points, points[1:]))
        assert [s.signal_strength for s in specs[i * 33 : (i + 1) * 33]] == list(points)
    assert kernel.grid(kernel.WINDOWS[0])[1] == 0.0020625
    assert kernel.grid(kernel.WINDOWS[1])[17] == 0.1015625


@pytest.mark.parametrize(
    "changes",
    [
        {"signal_strength": True},
        {"signal_strength": float("nan")},
        {"signal_strength": 0.002001},
        {"side": 257},
        {"seed": 2},
        {"baseline_noise": 0},
        {"k": 16},
        {"probe_count": 32},
        {"pattern": "curved_coherent"},
    ],
)
def test_unregistered_conditions_rejected(changes):
    with pytest.raises(ValueError):
        kernel.ZoomSpec(**changes)


def test_old_anchor_observations_fields_and_gates_are_exact(pair):
    report, arrays = pair
    old, old_arrays = kernel.strength.measure_pair(
        kernel.strength.StrengthSpec(**report["spec"])
    )
    assert runner.anchor_replay(report, old)
    assert set(arrays) == set(old_arrays)
    for key in arrays:
        np.testing.assert_array_equal(arrays[key], old_arrays[key])
    changed = deepcopy(report)
    changed["input_sha256"]["plane"] = "changed"
    with pytest.raises(ValueError, match="old-anchor"):
        runner.anchor_replay(changed, old)


def test_noise_pairing_new_intermediate_alpha_reuses_predecessor_streams():
    coords = kernel.strength.reference.predecessor.backend.make_domain(17)["coords"]
    hashes = []
    for alpha in kernel.grid(kernel.WINDOWS[0])[0:3]:
        receipt = {}
        kernel.strength.make_inputs(
            kernel.ZoomSpec(signal_strength=alpha), coords, receipt=receipt
        )
        hashes.append(receipt["standard_normal_stream_sha256"])
    assert hashes[0] == hashes[1] == hashes[2]
    assert len(set(hashes[0].values())) == 3


def test_complete_records_preserve_nulls_chronology_and_original_gates(pair):
    report, _ = pair
    zoom = report["zoom"]
    assert len(zoom["cells"]) == 9
    assert zoom["label_exchange_checks"] == 180
    assert zoom["derived_estimator_checks"] == 36
    assert report["chronology"]["baseline_seals_before_any_arm_evaluation"] == 6
    assert report["chronology"]["core_seals_before_loops_per_arm"] == 36
    for c, original in zip(zoom["cells"], report["paired_cells"], strict=True):
        assert set(c["loops"]) == set(kernel.perturbation.ORIENTED_LOOPS)
        for loop in c["loops"]:
            for h in ("F2", "F4"):
                for arm in ("A", "B"):
                    b = c["loops"][loop][h][arm]
                    o = original["loops"][loop][h][arm]
                    assert b["state"] == o["state"] and b["reason"] == o["reason"]
                    assert b["sampled_winding"] == (
                        None if o["value"] is None else o["value"]["sampled_winding"]
                    )
    assert kernel.compact_report(report)["zoom"] == zoom
    json.dumps(kernel.compact_report(report), allow_nan=False)


def test_edge_orientation_floor_and_branch_nulls():
    coords = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
    values = np.array([[1.0, 0.0], [-1.0, 0.01], [0.0, -1.0], [1.0, -1.0]])
    vertices = np.arange(4)
    d = kernel.scalar_diagnostic(values, vertices, coords)
    assert not d["reliable"] and d["sampled_winding"] is None
    assert d["failure_reasons"] == ["branch_cut_or_undersampling_ambiguity"]
    assert d["amplitude_slack"] > 0 and d["branch_slack_rad"] < 0
    assert d["worst_edge"]["vertices"] == [0, 1]
    reverse = kernel.scalar_diagnostic(values, np.array([0, 3, 2, 1]), coords)
    assert reverse["worst_edge"]["vertices"] == [1, 0]
    assert (
        reverse["worst_edge"]["signed_angle_rad"]
        == -d["worst_edge"]["signed_angle_rad"]
    )
    values[0] = [0, 0]
    zero = kernel.scalar_diagnostic(values, vertices, coords)
    assert "amplitude_at_or_below_floor" in zero["failure_reasons"]
    assert zero["sampled_winding"] is None
    assert zero["minimum_vertex"]["vertex"] == 0


def test_sampling_controls_are_estimator_only_and_cyclic_invariant(pair):
    for row in pair[0]["zoom"]["sampling_controls"].values():
        for hypotheses in row.values():
            for entry in hypotheses.values():
                assert not entry["inherits_original_graph_admission"]
                assert not entry["new_observations"]
                assert kernel.same_estimate(
                    entry["primary"], entry["checks"]["cyclic_shift_one"]
                )
                for offset in (0, 1):
                    d = entry["checks"][f"stride2_offset{offset}"]
                    assert d["sample_count"] * 2 == entry["primary"]["sample_count"]


def test_algebraic_exchange_swaps_only_one_arm_labels():
    admitted = {"state": "eligible", "value": {"sampled_winding": 0}}
    stopped = {"state": "insufficient", "value": None}
    assert kernel.perturbation._category(admitted, stopped) == "A_only_admitted"
    assert kernel.perturbation._category(stopped, admitted) == "B_only_admitted"


def test_diagnostics_do_not_mutate_sources_and_tampered_arrays_fail(pair):
    report, arrays = pair
    before = json.dumps(report, sort_keys=True)
    modules = (kernel.strength, kernel.strength.reference, kernel.perturbation)
    bindings = [dict(vars(m)) for m in modules]
    assert kernel.located_diagnostics(report, arrays) == report["zoom"]
    assert json.dumps(report, sort_keys=True) == before
    assert all(dict(vars(m)) == b for m, b in zip(modules, bindings, strict=True))
    changed = dict(arrays)
    name = report["array_layout"]["arms"]["A"]["mutual-knn_residual_affine_F2_values"]
    changed[name] = changed[name].copy()
    changed[name][0, 0] += 1
    with pytest.raises(ValueError, match="hash"):
        kernel.located_diagnostics(report, changed)
    changed = dict(arrays)
    coordinate_key = report["array_layout"]["arms"]["A"]["coords"]
    changed[coordinate_key] = changed[coordinate_key].copy()
    changed[coordinate_key][0, 0] += 0.1
    with pytest.raises(ValueError, match="coordinate hash"):
        kernel.located_diagnostics(report, changed)


def test_runs_keep_disconnected_one_arm_bands_and_unavailable_gaps():
    result = kernel.sampled_runs([0, 1, 2, 3, 4], ["A", "A", "unavailable", "A", "B"])
    assert [r["category"] for r in result] == ["A", "unavailable", "A", "B"]
    assert result[0]["first_sample"] == 0 and result[0]["last_sample"] == 1
    assert result[0]["following_sample"] == 2
    assert result[2]["preceding_sample"] == 2
    assert not any(r["continuous_interval_certified"] for r in result)


def test_all_unrun_cross_sections_keep_99_positions_and_all_cells(tmp_path):
    records = [
        {"index": i, "spec": asdict(s), "status": "not_run", "reason": "budget"}
        for i, s in enumerate(kernel.case_specs())
    ]
    cross = runner.cross_sections(records, tmp_path)
    assert len(cross["units"]) == 99
    assert all(u["outer"] is None for u in cross["units"])
    for w in cross["windows"]:
        assert len(w["runs_by_cell_hypothesis"]) == 18
        assert all(
            r[0]["category"] == "unavailable"
            for r in w["runs_by_cell_hypothesis"].values()
        )
    with pytest.raises(ValueError, match="99"):
        runner.cross_sections(records[:-1], tmp_path)


def test_serialized_receipts_replay_and_tampering_is_detected(tmp_path):
    directory = tmp_path / "unit"
    spec = replace(kernel.ZoomSpec(), signal_strength=0.0020625)
    report, _ = kernel.measure_pair(spec, directory)
    runner.write(directory / "compact.json", kernel.compact_report(report))
    assert runner.validate_unit(directory, spec)[0] == report
    with pytest.raises(FileExistsError):
        kernel.measure_pair(spec, directory)
    compact = json.loads((directory / "compact.json").read_text())
    compact["zoom"]["label_exchange_checks"] = 0
    (directory / "compact.json").write_text(json.dumps(compact))
    with pytest.raises(ValueError, match="compact"):
        runner.validate_unit(directory, spec)
