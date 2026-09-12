from __future__ import annotations

from dataclasses import replace
import hashlib
from itertools import product
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prototype_p4_signal_strength_v0_1 as kernel  # noqa: E402
import run_p4_signal_strength_v0_1 as runner  # noqa: E402

prototype = kernel.reference
previous = prototype.predecessor


@pytest.fixture(scope="module")
def coords():
    return previous.backend.make_domain(17)["coords"]


@pytest.fixture(scope="module")
def noisy_pair():
    return kernel.measure_pair(kernel.StrengthSpec(signal_strength=0.02, seed=7))


@pytest.mark.parametrize("alpha", [0, 1e-6, 0.02, 1])
def test_clean_observations_measure_prescribed_strength_not_scaled_residuals(
    coords, alpha
):
    spec = kernel.StrengthSpec(signal_strength=alpha, probe_count=8)
    probes = kernel.clean_probes(spec, coords)
    frames = np.broadcast_to(np.eye(3)[:, :2], (len(coords), 3, 2)).copy()
    values = prototype.DenseMomentAdapter().moments(frames, probes["evaluation"])
    z = coords[:, 0] + 1j * coords[:, 1]
    field = z + 0.25 * alpha * z**2
    for h in ("F2", "F4"):
        np.testing.assert_allclose(
            values[h], np.column_stack((field.real, field.imag)), atol=2e-14, rtol=2e-14
        )
    anchor = kernel.clean_probes(replace(spec, signal_strength=1), coords)
    np.testing.assert_array_equal(probes["plane"], anchor["plane"])
    if alpha != 1:
        assert not np.array_equal(probes["evaluation"], anchor["evaluation"])
        assert not np.array_equal(probes["evaluation"], alpha * anchor["evaluation"])


@pytest.mark.parametrize("count", [8, 32, 128])
def test_clean_anchor_is_byte_identical_to_predecessor_quadratic_probes(coords, count):
    spec = kernel.StrengthSpec(probe_count=count, baseline_noise=0)
    actual = kernel.clean_probes(spec, coords)
    old = prototype.sensitivity.make_probes(
        prototype.sensitivity.ProbeSpec(pattern="quadratic_excess", probe_count=count),
        coords,
    )
    for key in old:
        np.testing.assert_array_equal(actual[key], old[key])
        assert previous._hash(actual[key]) == previous._hash(old[key])


@pytest.mark.parametrize(
    "changes",
    [
        {"signal_strength": True},
        {"signal_strength": np.bool_(False)},
        {"signal_strength": float("nan")},
        {"signal_strength": float("inf")},
        {"signal_strength": -1},
        {"signal_strength": 1.1},
        {"signal_strength": 0.007},
        {"signal_strength": "0.02"},
        {"side": 257},
        {"side": True},
        {"k": 16},
        {"probe_count": 16},
        {"baseline_noise": 0.01},
        {"seed": -1},
        {"pattern": "curved_coherent"},
    ],
)
def test_fixed_design_rejects_unregistered_inputs(changes):
    with pytest.raises(ValueError):
        kernel.StrengthSpec(**changes)


def test_standard_draw_hashes_pair_across_strength_and_nested_probe_counts(coords):
    hashes = []
    full = None
    for alpha, count in product((0, 0.02, 1), (128, 32, 8)):
        receipt = {}
        spec = kernel.StrengthSpec(signal_strength=alpha, probe_count=count, seed=7)
        inputs = kernel.make_inputs(spec, coords, receipt=receipt)
        hashes.append(receipt["standard_normal_stream_sha256"])
        if count == 128:
            full = inputs
        for key in (
            "plane",
            "evaluation",
            "baseline_A",
            "baseline_B",
            "validation_probes",
        ):
            np.testing.assert_array_equal(inputs[key], full[key][:, :count])
        clean = kernel.clean_probes(spec, coords)["baseline"]
        if alpha == 0 and count == 128:
            zero_noise = inputs["baseline_A"] - clean
        elif count == 128:
            np.testing.assert_allclose(
                inputs["baseline_A"] - clean, zero_noise, atol=1e-15, rtol=1e-13
            )
    assert all(h == hashes[0] for h in hashes)
    assert len(set(hashes[0].values())) == 3
    other = {}
    kernel.make_inputs(kernel.StrengthSpec(seed=8), coords, receipt=other)
    assert set(other["standard_normal_stream_sha256"].values()).isdisjoint(
        hashes[0].values()
    )
    new = kernel.make_inputs(kernel.StrengthSpec(seed=7), coords)
    old = prototype.make_inputs(
        prototype.ReferenceSpec(pattern="quadratic_excess", probe_count=128, seed=7),
        coords,
    )
    assert not np.array_equal(new["baseline_A"], old["baseline_A"])


def test_noiseless_does_not_draw_noise_and_zero_residual_direction_stays_null(
    monkeypatch,
):
    def forbidden(*args, **kwargs):
        pytest.fail("noiseless control must consume no RNG draws")

    monkeypatch.setattr(kernel.np.random, "default_rng", forbidden)
    report, _ = kernel.measure_pair(
        kernel.StrengthSpec(signal_strength=0, baseline_noise=0, probe_count=8)
    )
    assert report["noise_receipt"]["standard_normal_stream_sha256"] == dict.fromkeys(
        "ABV"
    )
    assert report["noise_receipt"]["independent_noise_streams"] == 0
    assert report["arms"]["A"]["cells"] == report["arms"]["B"]["cells"]
    outer = kernel.compact_report(report)["loops"]["outer_forward"]
    for h in ("F2", "F4"):
        assert outer[h]["both_plus2_cells"] == 0
        assert outer[h]["paired_categories"]["neither_admitted"] == 9
        for row in outer[h]["rows"].values():
            m = row["measurement"]
            assert m["counts"]["both_directions_defined"] == 0
            assert m["summary"]["symmetric_relative"]["median"] is None
            assert m["summary"]["absolute_angle_rad"]["median"] is None


def test_pair_keeps_all_graph_rows_loops_categories_and_scope(noisy_pair):
    report, arrays = noisy_pair
    compact = kernel.compact_report(report)
    assert compact["loop_hypothesis_records"] == 180
    assert len(report["paired_cells"]) == 9
    assert len(compact["loops"]) == 10
    for loop in compact["loops"].values():
        assert set(loop) == {"F2", "F4"}
        for h, entry in loop.items():
            assert sum(entry["paired_categories"].values()) == 9
            assert set(entry["paired_categories"]) == set(kernel.CATEGORIES)
            assert set(entry["rows"]) == set(previous.FAMILIES)
            for row in entry["rows"].values():
                if row["measurement"] is not None:
                    assert "points" not in row["measurement"]
                    assert "counts" in row["measurement"]
                    if h == "F4":
                        assert (
                            row["coefficient_angle_convention"]
                            == "spin-two-not-physical-director"
                        )
    assert report["chronology"]["baseline_seals_before_any_arm_evaluation"] == 6
    assert report["chronology"]["core_seals_before_loops_per_arm"] == 36
    for key in (
        "scientific_authority",
        "physical_phase_transition_established",
        "calibrated_detection_threshold",
    ):
        assert compact["scope"][key] is False
    assert all(np.isfinite(a).all() for a in arrays.values())
    json.dumps(compact, allow_nan=False)


def test_measurement_does_not_mutate_predecessor_module_bindings():
    modules = (prototype, prototype.sensitivity, previous, kernel.perturbation)
    before = [dict(vars(m)) for m in modules]
    report, _ = kernel.measure_pair(kernel.StrengthSpec(baseline_noise=0))
    for m, values in zip(modules, before, strict=True):
        assert dict(vars(m)) == values
    assert all(
        e["both_plus2_cells"] == 9
        for e in kernel.compact_report(report)["loops"]["outer_forward"].values()
    )


def test_serialized_output_replays_and_tampering_fails_closed(tmp_path):
    spec = kernel.StrengthSpec(probe_count=8)
    directory = tmp_path / "unit"
    report, arrays = kernel.measure_pair(spec, directory)
    runner.write(directory / "compact.json", kernel.compact_report(report))
    assert runner.validate_unit(directory, spec)[0] == report
    with np.load(directory / "arrays.npz", allow_pickle=False) as saved:
        for key, expected in arrays.items():
            np.testing.assert_array_equal(saved[key], expected)
    with pytest.raises(FileExistsError):
        kernel.measure_pair(spec, directory)
    path = directory / "compact.json"
    saved_text = path.read_text()
    changed = json.loads(saved_text)
    changed["loops"]["outer_forward"]["F2"]["both_plus2_cells"] = 7
    path.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="compact"):
        runner.validate_unit(directory, spec)
    path.write_text(saved_text)
    raw = bytearray((directory / "arrays.npz").read_bytes())
    raw[-1] ^= 1
    (directory / "arrays.npz").write_bytes(raw)
    with pytest.raises(ValueError, match="hash"):
        runner.validate_unit(directory, spec)


def trace(flags):
    return [
        {
            "spec": {"signal_strength": a},
            "status": "failed" if f is None else "completed",
            "outer": {"F2": {"both_plus2_cells": 9 if f else 0}},
        }
        for a, f in zip(kernel.STRENGTHS, flags, strict=True)
    ]


def test_grid_descriptors_keep_first_reentry_and_suffix_separate():
    flags = [False] * 33
    flags[10] = True
    flags[20:] = [True] * 13
    result = kernel.trace_descriptor(trace(flags), "F2")
    assert result["first_all_cells_both_plus2"] == {
        "previous_strength": kernel.STRENGTHS[9],
        "sampled_strength": kernel.STRENGTHS[10],
    }
    assert (
        result["all_remaining_sampled_strengths_both_plus2"]["sampled_strength"]
        == kernel.STRENGTHS[20]
    )
    assert result["breaks_after_first"] == list(kernel.STRENGTHS[11:20])
    flags[5] = None
    result = kernel.trace_descriptor(trace(flags), "F2")
    assert result["first_all_cells_both_plus2"] is not None
    assert result["all_remaining_sampled_strengths_both_plus2"] is None
    assert result["trace_complete"] is False


def test_no_positive_observation_or_wrong_ladder_cannot_become_a_threshold():
    units = trace([False] * 33)
    result = kernel.trace_descriptor(units, "F2")
    assert result["first_all_cells_both_plus2"] is None
    assert result["all_remaining_sampled_strengths_both_plus2"] is None
    with pytest.raises(ValueError, match="33-level"):
        kernel.trace_descriptor(units[:-1], "F2")
    units[0]["spec"]["signal_strength"] = 0.007
    with pytest.raises(ValueError, match="33-level"):
        kernel.trace_descriptor(units, "F2")


def test_registered_panel_has_exact_denominator_and_order():
    specs = runner.case_specs()
    assert len(kernel.STRENGTHS) == len(set(kernel.STRENGTHS)) == 33
    assert len(specs) == len(set(specs)) == 429
    assert [(s.probe_count, s.seed, s.signal_strength) for s in specs[:396]] == list(
        product((8, 32, 128), (0, 1, 2, 3), kernel.STRENGTHS)
    )
    assert all(s.baseline_noise == 0.03 for s in specs[:396])
    assert all(
        s.side == 65 and s.k == 8 and s.pattern == "quadratic_excess" for s in specs
    )
    assert all(
        s.baseline_noise == 0 and s.probe_count == 128 and s.seed == 0
        for s in specs[396:]
    )
    lock = runner.source_lock()
    assert lock[runner.PROTOCOL] == runner.PROTOCOL_SHA256
    for path in (
        "scripts/prototype_p4_signal_strength_v0_1.py",
        "scripts/run_p4_signal_strength_v0_1.py",
        "tests/test_p4_signal_strength_v0_1.py",
    ):
        assert lock[path] == hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def test_changed_protocol_fails_before_output_or_subprocess(monkeypatch, tmp_path):
    monkeypatch.setattr(runner.platform, "system", lambda: "Linux")
    monkeypatch.setattr(runner, "sha", lambda path: "0" * 64)

    def forbidden(*args, **kwargs):
        pytest.fail("protocol mismatch must fail before subprocess")

    monkeypatch.setattr(runner.subprocess, "run", forbidden)
    with pytest.raises(ValueError, match="protocol"):
        runner.run(tmp_path / "bad")
    assert not (tmp_path / "bad").exists()


@pytest.mark.parametrize("first_timeout", [False, True])
def test_campaign_failure_keeps_all_429_positions_and_unknown_trace_flags(
    monkeypatch, tmp_path, first_timeout
):
    state = {"locks": 0, "children": 0}

    def changing_lock():
        state["locks"] += 1
        return {
            "lock": "before" if state["locks"] <= 1 + int(first_timeout) else "after"
        }

    def fake_process(command, **kwargs):
        if command == ["git", "rev-parse", "HEAD"]:
            return SimpleNamespace(stdout="1" * 40 + "\n", returncode=0)
        state["children"] += 1
        assert first_timeout and state["children"] == 1
        assert kwargs["timeout"] <= runner.CASE_SECONDS
        assert kwargs["env"]["OPENBLAS_NUM_THREADS"] == "1"
        raise runner.subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(runner.platform, "system", lambda: "Linux")
    monkeypatch.setattr(runner, "source_lock", changing_lock)
    monkeypatch.setattr(runner.subprocess, "run", fake_process)
    output = tmp_path / "retained"
    result = runner.run(output)
    assert result["paired_units"] == len(result["units"]) == 429
    assert result["arm_measurements_planned"] == 858
    assert result["completed"] == 0
    assert [r["index"] for r in result["units"]] == list(range(429))
    first, *rest = result["units"]
    assert first["status"] == ("timeout" if first_timeout else "not_run")
    assert all(
        r["status"] == "not_run" and r["reason"] == "source-changed" for r in rest
    )
    sections = json.loads((output / "cross_sections.json").read_text())
    assert len(sections["traces"]) == 13
    for group in sections["traces"]:
        for d in group["descriptors"].values():
            assert d["flags"] == [None] * 33
            assert d["all_remaining_sampled_strengths_both_plus2"] is None
    assert runner.sha(output / "cross_sections.json") == result["cross_sections_sha256"]
    assert runner.AS_BYTES == 8 * 2**30
    assert runner.DISK_BYTES == 12 * 2**30
    assert runner.TOTAL_SECONDS == 2400


def test_actual_moment_and_loop_calls_follow_six_reference_seals_and_each_arms_core_seals(
    monkeypatch,
):
    state = {
        "prepared": False,
        "arm": None,
        "baseline_moments": 0,
        "validation_moments": 0,
        "evaluation_moments": 0,
    }
    cores, loops = {"A": 0, "B": 0}, {"A": 0, "B": 0}
    prepare = prototype._prepare_pair
    arm_measurement = prototype._arm_measurement
    moments = prototype.DenseMomentAdapter.moments
    factory = prototype.sensitivity._isolated_measurement

    def checked_prepare(*args, **kwargs):
        assert all(not values.flags.writeable for values in args[3].values())
        result = prepare(*args, **kwargs)
        events = args[5]
        assert len(events) == 6
        assert all(
            event["event"] == "baseline_sealed" and event["seal_sha256"]
            for event in events
        )
        assert state["baseline_moments"] == 6
        state["prepared"] = True
        return result

    def checked_moments(adapter, frames, probes):
        if len(frames) == 5:
            assert state["prepared"] is False
            state["baseline_moments"] += 1
        elif len(frames) == 8:
            assert state["prepared"] is True
            state["validation_moments"] += 1
        elif len(frames) == 17**2:
            assert state["prepared"] is True
            assert state["validation_moments"] == 3
            state["evaluation_moments"] += 1
        else:
            pytest.fail(f"undeclared moment row count: {len(frames)}")
        return moments(adapter, frames, probes)

    def checked_arm(*args, **kwargs):
        assert state["prepared"] is True
        state["arm"] = args[1]
        return arm_measurement(*args, **kwargs)

    def checked_factory(*args, **kwargs):
        measure, namespace = factory(*args, **kwargs)
        core = namespace["core_record"]

        def checked_core(*core_args, **core_kwargs):
            result = core(*core_args, **core_kwargs)
            assert result[0]["seal_sha256"]
            cores[state["arm"]] += 1
            return result

        namespace["core_record"] = checked_core
        return measure, namespace

    def checked_loop(function):
        def wrapped(*args, **kwargs):
            assert state["prepared"] is True
            assert cores[state["arm"]] == 36
            loops[state["arm"]] += 1
            return function(*args, **kwargs)

        return wrapped

    # Only successor bindings and per-call namespaces are replaced. No frozen
    # predecessor or sensitivity module globals are assigned during this test.
    previous_proxy = SimpleNamespace(**vars(previous))
    previous_proxy.old = SimpleNamespace(**vars(previous.old))
    previous_proxy.old.chain = SimpleNamespace(**vars(previous.old.chain))
    previous_proxy.old.chain._geometry = checked_loop(previous.old.chain._geometry)
    previous_proxy.old.chain._winding = checked_loop(previous.old.chain._winding)
    sensitivity_proxy = SimpleNamespace(**vars(prototype.sensitivity))
    sensitivity_proxy._isolated_measurement = checked_factory
    monkeypatch.setattr(prototype, "predecessor", previous_proxy)
    monkeypatch.setattr(prototype, "sensitivity", sensitivity_proxy)
    monkeypatch.setattr(prototype, "_prepare_pair", checked_prepare)
    monkeypatch.setattr(prototype, "_arm_measurement", checked_arm)
    monkeypatch.setattr(prototype.DenseMomentAdapter, "moments", checked_moments)
    report, _ = kernel.measure_pair(
        kernel.StrengthSpec(signal_strength=0.02, probe_count=32)
    )
    assert state["baseline_moments"] == 6
    assert state["validation_moments"] == 3
    assert state["evaluation_moments"] == 6
    assert cores == {"A": 36, "B": 36}
    assert loops == {"A": 390, "B": 390}
    assert report["chronology"]["baseline_seals_before_any_arm_evaluation"] == 6
