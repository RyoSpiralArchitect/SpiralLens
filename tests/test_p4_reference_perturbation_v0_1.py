from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import p4_reference_perturbation_diagnostics_v0_1 as diagnostics  # noqa: E402
import analyze_p4_reference_perturbation_v0_1 as analyzer  # noqa: E402
import prototype_p4_reference_validation_v0_1 as reference  # noqa: E402


METRICS = (
    "amplitude_A",
    "amplitude_B",
    "perturbation_norm",
    "amplitude_change",
    "relative_to_A",
    "relative_to_B",
    "symmetric_relative",
    "signed_angle_rad",
    "absolute_angle_rad",
    "radial_A",
    "transverse_A",
    "angular_slope_at_A",
    "angular_slope_at_B",
    "closest_lambda",
    "minimum_segment_amplitude",
    "segment_to_endpoint_ratio",
)


def _single(a, b, support=True):
    return diagnostics.point_diagnostics(
        np.array([a], dtype=np.float64),
        np.array([b], dtype=np.float64),
        np.array([support]),
    )


def _assert_point(result, expected):
    for key, value in expected.items():
        if value is None:
            assert result["points"][key] == [None], key
            assert result["reasons"][key][0] is not None, key
        else:
            assert result["points"][key] == pytest.approx([value]), key
            assert result["reasons"][key] == [None], key


def test_identical_nonzero_vectors_have_zero_change_and_initial_closest_endpoint():
    result = _single([3, 4], [3, 4])
    _assert_point(
        result,
        {
            "amplitude_A": 5,
            "amplitude_B": 5,
            "perturbation_norm": 0,
            "amplitude_change": 0,
            "relative_to_A": 0,
            "relative_to_B": 0,
            "symmetric_relative": 0,
            "signed_angle_rad": 0,
            "absolute_angle_rad": 0,
            "radial_A": 0,
            "transverse_A": 0,
            "angular_slope_at_A": 0,
            "angular_slope_at_B": 0,
            "closest_lambda": 0,
            "minimum_segment_amplitude": 5,
            "segment_to_endpoint_ratio": 1,
        },
    )


@pytest.mark.parametrize(
    "a,b,radial,closest", [([2, 0], [4, 0], 2, 0), ([4, 0], [2, 0], -2, 1)]
)
def test_radial_change_has_zero_angle_and_closest_endpoint(a, b, radial, closest):
    result = _single(a, b)
    _assert_point(
        result,
        {
            "amplitude_A": a[0],
            "amplitude_B": b[0],
            "perturbation_norm": 2,
            "amplitude_change": radial,
            "relative_to_A": 2 / a[0],
            "relative_to_B": 2 / b[0],
            "symmetric_relative": 1,
            "signed_angle_rad": 0,
            "absolute_angle_rad": 0,
            "radial_A": radial,
            "transverse_A": 0,
            "angular_slope_at_A": 0,
            "angular_slope_at_B": 0,
            "closest_lambda": closest,
            "minimum_segment_amplitude": 2,
            "segment_to_endpoint_ratio": 1,
        },
    )


def test_transverse_change_uses_coefficient_angle_without_halving_and_forward_endpoint_slopes():
    result = _single([2, 0], [2, 2])
    _assert_point(
        result,
        {
            "amplitude_A": 2,
            "amplitude_B": np.sqrt(8),
            "perturbation_norm": 2,
            "amplitude_change": np.sqrt(8) - 2,
            "relative_to_A": 1,
            "relative_to_B": 1 / np.sqrt(2),
            "symmetric_relative": 1,
            "signed_angle_rad": np.pi / 4,
            "absolute_angle_rad": np.pi / 4,
            "radial_A": 0,
            "transverse_A": 2,
            "angular_slope_at_A": 1,
            "angular_slope_at_B": 0.5,
            "closest_lambda": 0,
            "minimum_segment_amplitude": 2,
            "segment_to_endpoint_ratio": 1,
        },
    )


def test_antipodal_segment_passes_zero_but_keeps_endpoint_direction_diagnostics():
    result = _single([2, 0], [-3, 0])
    _assert_point(
        result,
        {
            "amplitude_A": 2,
            "amplitude_B": 3,
            "perturbation_norm": 5,
            "relative_to_A": 2.5,
            "relative_to_B": 5 / 3,
            "symmetric_relative": 2.5,
            "radial_A": -5,
            "transverse_A": 0,
            "angular_slope_at_A": 0,
            "angular_slope_at_B": 0,
            "closest_lambda": 0.4,
            "minimum_segment_amplitude": 0,
            "segment_to_endpoint_ratio": 0,
        },
    )
    assert abs(result["points"]["signed_angle_rad"][0]) == pytest.approx(np.pi)
    assert result["points"]["absolute_angle_rad"] == pytest.approx([np.pi])
    assert result["counts"]["both_directions_defined"] == 1
    assert result["counts"]["closest_at_or_below_floor"] == 1


def test_interior_closest_segment_with_nonzero_minimum():
    result = _single([1, 1], [-1, 1])
    _assert_point(
        result,
        {
            "perturbation_norm": 2,
            "closest_lambda": 0.5,
            "minimum_segment_amplitude": 1,
            "segment_to_endpoint_ratio": 1 / np.sqrt(2),
            "signed_angle_rad": np.pi / 2,
        },
    )
    assert result["counts"]["closest_at_or_below_floor"] == 0


@pytest.mark.parametrize("amplitude", [0.0, 0.5e-6, 1e-6])
def test_at_or_below_floor_preserves_amplitudes_without_inventing_a_direction(
    amplitude,
):
    result = _single([amplitude, 0], [2e-6, 0])
    _assert_point(
        result,
        {
            "amplitude_A": amplitude,
            "amplitude_B": 2e-6,
            "perturbation_norm": 2e-6 - amplitude,
            "relative_to_A": None,
            "relative_to_B": (2e-6 - amplitude) / 2e-6,
            "symmetric_relative": None,
            "signed_angle_rad": None,
            "absolute_angle_rad": None,
            "radial_A": None,
            "transverse_A": None,
            "angular_slope_at_A": None,
            "angular_slope_at_B": 0,
            "minimum_segment_amplitude": amplitude,
            "segment_to_endpoint_ratio": None,
        },
    )
    assert result["counts"]["direction_A_defined"] == 0
    assert result["counts"]["direction_B_defined"] == 1
    assert result["counts"]["closest_at_or_below_floor"] == 1


def test_above_floor_ratios_are_not_clipped_or_stabilized_by_epsilon():
    amplitude = np.nextafter(1e-6, np.inf)
    result = _single([amplitude, 0], [1, 0])
    expected = (1 - amplitude) / amplitude
    assert result["points"]["relative_to_A"][0] == expected
    assert result["points"]["symmetric_relative"][0] == expected
    assert expected > 999_998
    assert result["counts"]["direction_A_defined"] == 1


def test_identical_zero_vectors_have_defined_segment_but_no_direction_or_ratios():
    result = _single([0, 0], [0, 0])
    _assert_point(
        result,
        {
            "amplitude_A": 0,
            "amplitude_B": 0,
            "perturbation_norm": 0,
            "amplitude_change": 0,
            "closest_lambda": 0,
            "minimum_segment_amplitude": 0,
            "relative_to_A": None,
            "relative_to_B": None,
            "symmetric_relative": None,
            "signed_angle_rad": None,
            "absolute_angle_rad": None,
            "radial_A": None,
            "transverse_A": None,
            "angular_slope_at_A": None,
            "angular_slope_at_B": None,
            "segment_to_endpoint_ratio": None,
        },
    )


def test_unsupported_points_never_receive_amplitudes_or_directional_values():
    result = _single([2, 0], [-3, 0], support=False)
    assert set(result["points"]) == set(METRICS)
    for key in METRICS:
        assert result["points"][key] == [None]
        assert result["reasons"][key][0] is not None
    assert result["counts"]["total"] == 1
    assert result["counts"]["supported"] == 0
    assert result["counts"]["unsupported"] == 1
    assert result["counts"]["closest_at_or_below_floor"] == 0


def test_point_permutation_and_reverse_order_only_reorder_pointwise_results():
    a = np.array([[2.0, 0], [0, 3], [0, 0], [1, 1], [4, -2]])
    b = np.array([[2.0, 2], [-2, 3], [1, 0], [-1, 1], [2, -4]])
    support = np.array([True, True, True, False, True])
    before = diagnostics.point_diagnostics(a, b, support)
    for order in (np.arange(len(a))[::-1], np.array([2, 4, 0, 3, 1])):
        after = diagnostics.point_diagnostics(a[order], b[order], support[order])
        for metric in METRICS:
            assert after["points"][metric] == [
                before["points"][metric][i] for i in order
            ]
            assert after["reasons"][metric] == [
                before["reasons"][metric][i] for i in order
            ]
        assert after["summary"] == before["summary"]
        assert after["counts"] == before["counts"]


def test_arm_swap_preserves_symmetric_metrics_and_reverses_oriented_angles_and_slopes():
    a = np.array([[2.0, 0], [3, 4], [1, 1], [2, 0]])
    b = np.array([[2.0, 2], [3, 4], [-1, 1], [-3, 0]])
    support = np.ones(len(a), dtype=bool)
    before = diagnostics.point_diagnostics(a, b, support)
    after = diagnostics.point_diagnostics(b, a, support)
    for metric in (
        "perturbation_norm",
        "symmetric_relative",
        "absolute_angle_rad",
        "minimum_segment_amplitude",
        "segment_to_endpoint_ratio",
    ):
        np.testing.assert_allclose(
            after["points"][metric], before["points"][metric], atol=1e-12
        )
    for left, right in (
        ("amplitude_A", "amplitude_B"),
        ("relative_to_A", "relative_to_B"),
    ):
        np.testing.assert_allclose(after["points"][left], before["points"][right])
        np.testing.assert_allclose(after["points"][right], before["points"][left])
    for left, right in (
        ("angular_slope_at_A", "angular_slope_at_B"),
        ("angular_slope_at_B", "angular_slope_at_A"),
    ):
        np.testing.assert_allclose(
            after["points"][left], -np.asarray(before["points"][right])
        )
    np.testing.assert_allclose(
        after["points"]["amplitude_change"],
        -np.asarray(before["points"]["amplitude_change"]),
    )
    for index, angle in enumerate(before["points"]["signed_angle_rad"]):
        inverse = after["points"]["signed_angle_rad"][index]
        if abs(angle) == np.pi:
            assert abs(inverse) == pytest.approx(np.pi)
        else:
            assert inverse == pytest.approx(-angle)
        expected_lambda = (
            0
            if np.array_equal(a[index], b[index])
            else 1 - before["points"]["closest_lambda"][index]
        )
        assert after["points"]["closest_lambda"][index] == pytest.approx(
            expected_lambda
        )


def test_quantiles_use_only_defined_values_and_keep_explicit_coverage():
    a = np.array([[1.0, 0], [2, 0], [4, 0], [1e-6, 0], [20, 0]])
    b = a + [1, 0]
    result = diagnostics.point_diagnostics(
        a, b, np.array([True, True, True, True, False])
    )
    for metric, points in result["points"].items():
        valid = [value for value in points if value is not None]
        summary = result["summary"][metric]
        assert summary["count"] == len(valid)
        for key, value in zip(
            ("min", "q25", "median", "q75", "max"),
            np.quantile(valid, [0, 0.25, 0.5, 0.75, 1]),
            strict=True,
        ):
            assert summary[key] == pytest.approx(value)
    assert result["counts"]["total"] == 5
    assert result["counts"]["supported"] == 4
    assert result["counts"]["direction_A_defined"] == 3
    json.dumps(result, allow_nan=False)


def test_empty_input_returns_zero_counts_and_null_summaries():
    result = diagnostics.point_diagnostics(
        np.empty((0, 2)), np.empty((0, 2)), np.array([], dtype=bool)
    )
    assert all(count == 0 for count in result["counts"].values())
    for metric in METRICS:
        assert result["points"][metric] == []
        assert result["summary"][metric]["count"] == 0
        assert all(
            value is None
            for key, value in result["summary"][metric].items()
            if key != "count"
        )
    json.dumps(result, allow_nan=False)


def test_inputs_are_not_mutated_including_noncontiguous_readonly_views():
    a = np.arange(24.0).reshape(6, 4)[:, ::2]
    b = a[::-1]
    support = np.ones(6, dtype=bool)
    before = [value.copy() for value in (a, b, support)]
    for value in (a, b, support):
        value.setflags(write=False)
    diagnostics.point_diagnostics(a, b, support)
    for value, expected in zip((a, b, support), before, strict=True):
        np.testing.assert_array_equal(value, expected)
        assert value.flags.writeable is False


@pytest.mark.parametrize(
    "bad",
    [
        np.ones((2,)),
        np.ones((2, 3)),
        np.ones((2, 2, 1)),
        np.full((2, 2), np.nan),
        np.full((2, 2), np.inf),
        np.ones((2, 2), dtype=bool),
        np.ones((2, 2), dtype=complex),
        np.full((2, 2), "1"),
    ],
)
def test_invalid_coefficient_shape_type_or_finiteness_is_rejected(bad):
    for a, b in ((bad, np.ones((2, 2))), (np.ones((2, 2)), bad)):
        with pytest.raises((TypeError, ValueError)):
            diagnostics.point_diagnostics(a, b, np.ones(2, dtype=bool))


@pytest.mark.parametrize(
    "support",
    [
        np.ones(2, dtype=int),
        np.ones(2),
        np.ones((2, 1), dtype=bool),
        np.ones(1, dtype=bool),
        np.array([True, None], dtype=object),
    ],
)
def test_invalid_support_shape_or_type_is_rejected(support):
    with pytest.raises((TypeError, ValueError)):
        diagnostics.point_diagnostics(np.ones((2, 2)), np.ones((2, 2)), support)


@pytest.mark.parametrize("floor", [True, 0, -1, float("nan"), float("inf")])
def test_invalid_amplitude_floor_is_rejected(floor):
    with pytest.raises((TypeError, ValueError)):
        diagnostics.point_diagnostics(
            np.ones((2, 2)),
            np.ones((2, 2)),
            np.ones(2, dtype=bool),
            amplitude_floor=floor,
        )


@pytest.fixture(scope="module")
def tiny_pair():
    # A new small fixture, not the retained 32-pair input campaign.
    return reference.measure_pair(reference.ReferenceSpec(side=17, seed=7))


def test_integration_retains_180_original_endpoint_records_and_only_reads_needed_arrays(
    tiny_pair,
):
    report, arrays = tiny_pair
    before = copy.deepcopy(report)
    accessed = []

    class LazyArrays:
        def __getitem__(self, key):
            accessed.append(key)
            assert key.endswith(("_values", "_frames", "_support"))
            return arrays[key]

    result = analyzer.analyze_pair(report, LazyArrays())
    assert report == before
    assert accessed
    assert result["loop_hypothesis_records"] == 180
    assert len(result["cells"]) == 9
    count = 0
    for cell in result["cells"]:
        original = {}
        for arm in ("A", "B"):
            original[arm] = next(
                c
                for c in report["arms"][arm]["cells"]
                if (c["field_graph"], c["loop_graph"])
                == (cell["field_graph"], cell["loop_graph"])
            )
        assert set(cell["loops"]) == set(analyzer.ORIENTED_LOOPS)
        for loop, hypotheses in cell["loops"].items():
            assert set(hypotheses) == {"F2", "F4"}
            for hypothesis, record in hypotheses.items():
                count += 1
                for arm in ("A", "B"):
                    assert (
                        record["endpoints"][arm]
                        == original[arm]["loops"][loop]["fields"]["residual_affine"][
                            hypothesis
                        ]
                    )
    assert count == 180
    assert result["original_outer_summary"] == report["summary"]
    assert result["scope"]["exploratory_reanalysis"] is True
    for key in ("new_observations", "new_fits", "new_winding_readouts"):
        assert result["scope"][key] == 0
    assert result["scope"]["reference_selected"] is False
    assert result["scope"]["scientific_authority"] is False
    for family in analyzer.FAMILIES:
        assert (
            result["diagnostics"][family]["F4"]["outer_forward"][
                "coefficient_angle_convention"
            ]
            == "spin-two-not-physical-director"
        )
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize(
    "mutation",
    [
        "schema",
        "path",
        "cell_count",
        "loop_count",
        "field_hash",
        "frame_hash",
        "support_hash",
        "field_seal",
    ],
)
def test_integration_rejects_changed_schema_readouts_and_field_receipts(
    tiny_pair, mutation
):
    report, arrays = tiny_pair
    changed = copy.deepcopy(report)
    family = analyzer.FAMILIES[0]
    field = changed["arms"]["A"]["rows"][family]["fields"]["full"]["F2"]
    if mutation == "schema":
        changed["schema_version"] = "unknown-schema"
    elif mutation == "path":
        changed["arms"]["B"]["loop_vertices"]["outer"][0] += 1
    elif mutation == "cell_count":
        changed["arms"]["B"]["cells"].pop()
    elif mutation == "loop_count":
        changed["arms"]["B"]["cells"][0]["loops"].pop("inner_forward")
    else:
        key = {
            "field_hash": "values_sha256",
            "frame_hash": "frames_sha256",
            "support_hash": "support_sha256",
            "field_seal": "field_sha256",
        }[mutation]
        field[key] = "0" * 64
    with pytest.raises((ValueError, KeyError)):
        analyzer.analyze_pair(changed, arrays)


@pytest.mark.parametrize(
    "mutation",
    ["field_value", "frame_shape", "support_dtype", "array_nonfinite", "array_mapping"],
)
def test_integration_rejects_mismatched_retained_arrays_and_mapping(
    tiny_pair, mutation
):
    report, arrays = tiny_pair
    changed_report = copy.deepcopy(report)
    changed_arrays = dict(arrays)
    family = analyzer.FAMILIES[0]
    key = f"{family}_full_F2_values"
    if mutation == "frame_shape":
        key = f"{family}_frames"
    elif mutation == "support_dtype":
        key = f"{family}_support"
    stored = report["array_layout"]["arms"]["A"][key]
    if mutation == "array_mapping":
        changed_report["array_layout"]["arms"]["A"][key] = "absent-array"
    else:
        values = arrays[stored].copy()
        if mutation == "field_value":
            values[0, 0] += 1
        elif mutation == "array_nonfinite":
            values[0, 0] = np.nan
        elif mutation == "frame_shape":
            values = values[:, :2, :]
        elif mutation == "support_dtype":
            values = values.astype(int)
        changed_arrays[stored] = values
    with pytest.raises((ValueError, KeyError)):
        analyzer.analyze_pair(changed_report, changed_arrays)


@pytest.mark.parametrize("any_supported", [False, True])
def test_partial_or_zero_support_stays_explicit_without_changing_original_winding(
    tiny_pair, any_supported
):
    report, arrays = tiny_pair
    changed_report, changed_arrays = copy.deepcopy(report), dict(arrays)
    family = analyzer.FAMILIES[0]
    support = np.zeros(report["vertex_count"], dtype=bool)
    path = report["arms"]["A"]["loop_vertices"]["outer"]
    if any_supported:
        support[path[0]] = True
    for arm in ("A", "B"):
        stored = report["array_layout"]["arms"][arm][f"{family}_support"]
        changed_arrays[stored] = support
        for estimand in ("full", "local_affine", "residual_affine"):
            for hypothesis in ("F2", "F4"):
                field = changed_report["arms"][arm]["rows"][family]["fields"][estimand][
                    hypothesis
                ]
                field["support_sha256"] = analyzer.array_hash(support)
                field["field_sha256"] = analyzer.field_seal(field)
    result = analyzer.analyze_pair(changed_report, changed_arrays)
    expected = "incomplete" if any_supported else "insufficient"
    for hypothesis in ("F2", "F4"):
        row = result["diagnostics"][family][hypothesis]["outer_forward"]
        assert row["state"] == expected
        assert row["measurement"]["counts"]["supported"] == int(any_supported)
        assert row["measurement"]["counts"]["total"] == len(path)
        if not any_supported:
            assert row["reason"] == "no-supported-points"
            assert all(
                value is None
                for series in row["measurement"]["points"].values()
                for value in series
            )


def test_uncoverable_graph_loop_cannot_be_promoted_by_point_diagnostics(tiny_pair):
    report, arrays = tiny_pair
    changed = copy.deepcopy(report)
    identity = changed["arms"]["A"]["cells"][0]
    for arm in ("A", "B"):
        endpoint = changed["arms"][arm]["cells"][0]["loops"]["outer_forward"]["fields"][
            "residual_affine"
        ]["F2"]
        endpoint.update(
            state="insufficient", reason="cycle-boundary-not-coverable", value=None
        )
    result = analyzer.analyze_pair(changed, arrays)
    cell = next(
        c
        for c in result["cells"]
        if (c["field_graph"], c["loop_graph"])
        == (identity["field_graph"], identity["loop_graph"])
    )
    point = cell["loops"]["outer_forward"]["F2"]
    assert point["state"] == "insufficient"
    assert point["reason"] == "cycle-boundary-not-coverable"
    assert point["diagnostic_ref"] is None
    assert point["paired_category"] == "neither_admitted"


@pytest.mark.parametrize("relative", ["same", "child", "parent", "symlink_child"])
def test_campaign_and_child_reject_outputs_overlapping_inputs_before_loading(
    tmp_path, monkeypatch, relative
):
    source = tmp_path / "inputs"
    source.mkdir()
    if relative == "same":
        output = source
    elif relative == "child":
        output = source / "output"
    elif relative == "parent":
        output = tmp_path
    else:
        link = tmp_path / "input-link"
        link.symlink_to(source, target_is_directory=True)
        output = link / "output"

    def forbidden_load(*args, **kwargs):
        pytest.fail("overlapping output must be refused before loading the campaign")

    monkeypatch.setattr(analyzer, "load_campaign", forbidden_load)
    with pytest.raises(ValueError, match="disjoint"):
        analyzer.run_campaign(source, output)
    with pytest.raises(ValueError, match="disjoint"):
        analyzer.analyze_unit(source, 0, output)


def test_existing_output_is_never_overwritten(tmp_path):
    source, output = tmp_path / "inputs", tmp_path / "outputs"
    source.mkdir()
    output.mkdir()
    for operation in (
        lambda: analyzer.run_campaign(source, output),
        lambda: analyzer.analyze_unit(source, 0, output),
    ):
        with pytest.raises(FileExistsError):
            operation()


def test_campaign_source_change_retains_all_32_units_and_5760_planned_records(
    tmp_path, monkeypatch
):
    source, output = tmp_path / "inputs", tmp_path / "outputs"
    source.mkdir()
    cases = [{"fixture_index": i} for i in range(32)]
    manifest = {
        "units": [
            {"index": i, "spec": spec, "status": "completed"}
            for i, spec in enumerate(cases)
        ]
    }
    plan = {"cases": cases, "source_sha256": {}}
    calls = {"lock": 0}

    def changing_lock():
        calls["lock"] += 1
        return {"fixture": "before" if calls["lock"] == 1 else "after"}

    def git_only(command, **kwargs):
        assert command == ["git", "rev-parse", "HEAD"]
        return SimpleNamespace(stdout="0" * 40 + "\n")

    monkeypatch.setattr(analyzer, "load_campaign", lambda _: (manifest, plan))
    monkeypatch.setattr(analyzer, "source_lock", changing_lock)
    monkeypatch.setattr(analyzer.platform, "system", lambda: "Linux")
    monkeypatch.setattr(analyzer.subprocess, "run", git_only)
    result = analyzer.run_campaign(source, output)
    assert result["paired_units"] == len(result["units"]) == 32
    assert result["loop_hypothesis_records_planned"] == 5760
    assert result["loop_hypothesis_records_completed"] == 0
    assert result["completed"] == 0
    assert [unit["index"] for unit in result["units"]] == list(range(32))
    assert all(
        unit["status"] == "not_run" and unit["reason"] == "source-changed"
        for unit in result["units"]
    )
    saved_plan = json.loads((output / "plan.json").read_text())
    assert saved_plan["resource_limits"] == {
        "case_seconds": 120,
        "total_seconds": 900,
        "child_address_space_bytes": 4 * 2**30,
        "file_bytes": 256 * 2**20,
        "pre_unit_disk_bytes": 2**30,
        "concurrent_children": 1,
        "blas_threads": 1,
    }
