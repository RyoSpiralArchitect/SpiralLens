from __future__ import annotations

from copy import deepcopy
import inspect
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prototype_p4_spatial_fidelity_v0_1 as kernel  # noqa: E402
import run_p4_spatial_fidelity_v0_1 as runner  # noqa: E402


@pytest.fixture(scope="module")
def predecessor():
    # New fixture seed, not the registered old reference/held-out geometry seeds.
    return kernel.zoom.strength.measure_pair(
        kernel.zoom.strength.StrengthSpec(
            side=65, signal_strength=0.1, seed=77, probe_count=128
        )
    )


def test_plan_grid_and_denominators():
    cases = runner.cases()
    assert runner.sha(ROOT / runner.PROTOCOL) == runner.PROTOCOL_SHA256
    assert len(cases) == 102
    assert sum(c["lane"] == "outer" for c in cases) == 18
    assert sum(c["lane"] == "local" for c in cases) == 84
    assert [(c["source_index"], c["alpha"]) for c in cases[16:18]] == [
        (68, 0.00825),
        (82, 0.01),
    ]
    assert {c["geometry_seed"] for c in cases[18:]} == {100, 101, 102, 103}
    assert len({(c["source"], c["source_index"]) for c in cases}) == 18


def test_nested_physical_loops_and_disjoint_common_audit():
    c256, c512, c1024 = [kernel.square_boundary(n) for n in kernel.COUNTS]
    np.testing.assert_array_equal(c256, c512[::2])
    np.testing.assert_array_equal(c256, c1024[::4])
    audit = set(map(tuple, kernel.square_boundary(2048)[1::2]))
    assert not audit.intersection(map(tuple, c1024))
    assert len(audit) == 1024


@pytest.mark.parametrize("count", [True, 6, 0, -8, 10.0])
def test_bad_loop_counts_rejected(count):
    with pytest.raises(ValueError):
        kernel.square_boundary(count)


def test_fresh_probe_convention_and_old_anchor_identity():
    coords = kernel.grid_coords(16)
    spec = kernel.zoom.strength.StrengthSpec(side=17, signal_strength=0.1)
    old = kernel.zoom.strength.clean_probes(spec, coords)
    expected = kernel.DenseMomentAdapter().moments(
        np.broadcast_to(kernel.FRAME, (len(coords), 3, 2)), old["evaluation"]
    )
    new = kernel.measure(coords, 0.025 * kernel.complex_values(coords) ** 2)
    for h in kernel.HYPOTHESES:
        np.testing.assert_array_equal(new[h], expected[h])
        np.testing.assert_allclose(
            kernel.subtract(new[h], coords, kernel.IDEAL),
            kernel.vector_values(0.025 * kernel.complex_values(coords) ** 2),
            atol=1e-14,
            rtol=0,
        )


def test_periodic_linear_prediction_is_not_observation():
    a = kernel.vector_values(
        0.025 * kernel.complex_values(kernel.square_boundary(256)) ** 2
    )
    b = kernel.vector_values(
        0.025 * kernel.complex_values(kernel.square_boundary(512)) ** 2
    )
    audit = kernel.vector_values(
        0.025 * kernel.complex_values(kernel.square_boundary(2048)[1::2]) ** 2
    )
    t = np.arange(1, 2048, 2) / 2048
    e256 = kernel.errors(kernel.interpolate_boundary(a, t), audit)
    e512 = kernel.errors(kernel.interpolate_boundary(b, t), audit)
    assert 3.8 < e256["complex_rmse"] / e512["complex_rmse"] < 4.2
    assert e512["complex_rmse"] > 0


def test_zero_has_no_phase_and_reverse_has_opposite_charge():
    coords = kernel.square_boundary(256)
    zero = np.zeros_like(coords)
    assert kernel.errors(zero, zero)["phase_points"] == 0
    assert kernel.errors(zero, zero)["phase_rms_deg"] is None
    assert kernel.diagnostic(zero, coords)["sampled_winding"] is None
    values = kernel.vector_values(kernel.complex_values(coords) ** 2)
    assert kernel.diagnostic(values, coords)["sampled_winding"] == 2
    assert kernel.diagnostic(values, coords, reverse=True)["sampled_winding"] == -2


@pytest.mark.parametrize("kind", ["nan", "wrong_shape", "bad_reference"])
def test_nonfinite_and_bad_shapes_fail(kind):
    coords = kernel.square_boundary(256)
    with pytest.raises(ValueError):
        if kind == "nan":
            kernel.measure(coords, np.full(len(coords), np.nan))
        elif kind == "wrong_shape":
            kernel.measure(coords, np.ones(2))
        else:
            kernel.subtract(coords, coords, kernel.IDEAL[:2])


def test_truth_blind_locator_signature_and_chronology():
    assert list(inspect.signature(kernel.locate).parameters) == ["coords", "values"]
    assert list(inspect.signature(kernel.read_local_loops).parameters) == [
        "coords",
        "values",
        "candidates",
    ]
    coords = kernel.grid_coords(64)
    construction = kernel.geometry(7, "wide")
    values = kernel.vector_values(kernel.injected_field(coords, construction))
    candidate = kernel.locate(coords, values)
    result = kernel.read_local_loops(coords, values, candidate)
    assert result["chronology"][0] == "candidate-sealed"
    assert len(candidate["components"]) == 2
    scored = kernel.score(result, construction)
    assert scored["exact_local_structure"]
    assert scored["outer_charge_correct"]
    altered = deepcopy(construction)
    altered["centers"] = [[0.9, 0.9], [0.8, 0.8]]
    assert not kernel.score(result, altered)["exact_local_structure"]
    assert kernel.read_local_loops(coords, values, candidate) == result


@pytest.mark.parametrize(
    "fixture,charges",
    [
        ("double", [2]),
        ("wide", [1, 1]),
        ("reverse", [-1, -1]),
        ("dipole", [-1, 1]),
        ("constant", []),
        ("zero", []),
    ],
)
def test_known_clean_local_controls(fixture, charges):
    coords = kernel.grid_coords(64)
    construction = kernel.geometry(7, fixture)
    values = kernel.vector_values(kernel.injected_field(coords, construction))
    candidates = kernel.locate(coords, values)
    result = kernel.read_local_loops(coords, values, candidates)
    measured = sorted(
        c["diagnostic"]["sampled_winding"]
        for c in result["components"]
        if c["resolved_charged_component"]
    )
    assert measured == charges
    assert kernel.score(result, construction)["exact_local_structure"]
    if fixture == "zero":
        assert result["state"] == "globally_below_floor"
        assert result["outer"]["sampled_winding"] is None


def test_close_pair_can_merge_without_changing_outer_integer():
    truth = kernel.geometry(7, "close")
    results = []
    for cells in (16, 128, 256):
        coords = kernel.grid_coords(cells)
        values = kernel.vector_values(kernel.injected_field(coords, truth))
        result = kernel.read_local_loops(coords, values, kernel.locate(coords, values))
        results.append(kernel.score(result, truth))
    assert all(r["outer_charge_correct"] for r in results)
    assert not results[0]["exact_local_structure"]
    # At 128 cells both charges are readable, but expanded loops still touch.
    # Keep that unresolved result instead of weakening the separation rule.
    assert results[1]["candidate_count"] == 2
    assert results[1]["resolved_charged_count"] == 0
    assert results[2]["exact_local_structure"]


@pytest.mark.parametrize("target", ["seal", "field", "coordinates"])
def test_tampering_before_charge_fails(target):
    coords = kernel.grid_coords(16)
    values = kernel.vector_values(kernel.complex_values(coords))
    candidates = kernel.locate(coords, values)
    if target == "seal":
        candidates["cells"] += 1
    elif target == "field":
        values[0, 0] += 1
    else:
        coords[0, 0] += 1
    with pytest.raises(ValueError):
        kernel.read_local_loops(coords, values, candidates)


def test_matching_keeps_missing_extra_and_wrong_charge():
    truth = {
        "centers": [[0, 0], [0.8, 0.8]],
        "charges": [1, 1],
        "everywhere_degenerate": False,
    }
    result = {
        "components": [
            {
                "id": 1,
                "position": [0.01, 0.01],
                "resolved_charged_component": True,
                "diagnostic": {"sampled_winding": -1},
            },
            {
                "id": 2,
                "position": [-0.8, -0.8],
                "resolved_charged_component": True,
                "diagnostic": {"sampled_winding": 1},
            },
        ],
        "outer": {"sampled_winding": 2},
    }
    scored = kernel.score(result, truth)
    assert scored["false_positive_count"] == scored["missed_truth_count"] == 1
    assert not scored["matches"][0]["charge_correct"]
    assert not scored["exact_local_structure"]
    assert scored["outer_charge_correct"]


def test_reference_verification_and_frozen_outer_replay(predecessor):
    result, arrays = kernel.outer_unit(*predecessor)
    assert result["readout_count"] == 72
    assert len(result["anchor_checks"]) == 12
    assert max(c["maximum_error"] for c in result["anchor_checks"]) <= 1e-12
    assert kernel.verify_replay(result, arrays)
    errors = [
        r["reference_error"]
        for r in result["readouts"]
        if r["family"] == "mutual-knn"
        and r["hypothesis"] == "F2"
        and r["arm"] == "A"
        and r["orientation"] == "forward"
    ]
    assert errors[0] == errors[1] == errors[2]
    changed = deepcopy(result)
    changed["readouts"][0]["sampling_error"]["complex_rmse"] += 1
    with pytest.raises(ValueError, match="replay"):
        kernel.verify_replay(changed, arrays)


def test_changed_reference_rejected(predecessor):
    report, arrays = predecessor
    changed = deepcopy(report)
    changed["arms"]["A"]["rows"]["mutual-knn"]["baseline"]["coefficients"]["F2"][0][
        0
    ] += 1
    with pytest.raises(ValueError):
        kernel.checked_reference(changed, arrays)


def test_local_unit_retains_every_arm_hypothesis_alias(predecessor):
    report, arrays = kernel.local_unit(
        *predecessor, fixture="wide", geometry_seed=7, cells=16
    )
    assert report["distinct_reconstructions"] == 6
    assert report["row_addressed_records"] == 18
    assert kernel.verify_replay(report, arrays)
    changed = deepcopy(report)
    changed["records"][0]["score"]["missed_truth_count"] += 1
    with pytest.raises(ValueError, match="replay"):
        kernel.verify_replay(changed, arrays)


def test_changed_missing_input_manifest_fails(tmp_path):
    with pytest.raises(OSError):
        runner.input_catalog({"strength": tmp_path})
    runner.write(tmp_path / "manifest.json", {"units": []})
    with pytest.raises(ValueError, match="manifest"):
        runner.input_catalog({"strength": tmp_path})


def test_reference_fit_can_absorb_translation_and_splitting():
    coords = kernel.zoom.strength.reference.FIT_COORDS
    z = kernel.complex_values(coords)
    c, d = 0.2 + 0.1j, 0.15 + 0.05j
    signal = z + 0.025 * ((z - c) ** 2 - d**2)
    design = np.column_stack((np.ones(len(z)), coords))
    coefficients = np.linalg.lstsq(design, kernel.vector_values(signal), rcond=None)[0]
    check = kernel.square_boundary(256)
    check_z = kernel.complex_values(check)
    residual = kernel.subtract(
        kernel.vector_values(check_z + 0.025 * ((check_z - c) ** 2 - d**2)),
        check,
        coefficients,
    )
    np.testing.assert_allclose(
        residual, kernel.vector_values(0.025 * check_z**2), atol=1e-14, rtol=0
    )
