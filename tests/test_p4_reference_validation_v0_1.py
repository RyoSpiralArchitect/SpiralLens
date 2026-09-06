from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import replace
from itertools import product
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prototype_p4_reference_validation_v0_1 as prototype  # noqa: E402
import run_p4_reference_validation_v0_1 as runner  # noqa: E402


previous = prototype.predecessor
FAMILIES = previous.FAMILIES
ESTIMANDS = previous.ESTIMANDS
HYPOTHESES = ("F2", "F4")


def _arm_arrays(report, arrays, arm):
    return {
        key: arrays[stored_key]
        for key, stored_key in report["array_layout"]["arms"][arm].items()
    }


@pytest.fixture(scope="module")
def coords():
    return previous.backend.make_domain(17)["coords"]


@pytest.fixture(scope="module")
def noisy_pair():
    return prototype.measure_pair(prototype.ReferenceSpec(seed=7))


@pytest.mark.parametrize("count", [8, 32, 128])
def test_independent_reference_streams_have_nested_per_vertex_probe_prefixes(
    coords, count
):
    spec = prototype.ReferenceSpec(probe_count=128, seed=7)
    largest = prototype.make_inputs(spec, coords)
    current = prototype.make_inputs(replace(spec, probe_count=count), coords)
    for role in (
        "plane",
        "evaluation",
        "baseline_A",
        "baseline_B",
        "validation_probes",
    ):
        assert current[role].dtype == np.float64
        np.testing.assert_array_equal(current[role], largest[role][:, :count])


def test_baseline_and_heldout_streams_are_independent_of_clean_shared_inputs(coords):
    spec = prototype.ReferenceSpec(probe_count=32, seed=17)
    noisy = prototype.make_inputs(spec, coords)
    clean = prototype.make_inputs(replace(spec, baseline_noise=0), coords)
    for role in ("plane", "evaluation"):
        np.testing.assert_array_equal(noisy[role], clean[role])
    noise = {
        role: noisy[role] - clean[role]
        for role in ("baseline_A", "baseline_B", "validation_probes")
    }
    rows = noisy["validation_rows"]
    assert not np.array_equal(noise["baseline_A"], noise["baseline_B"])
    for role in ("baseline_A", "baseline_B"):
        assert np.any(noise[role] != 0)
        assert not np.array_equal(noise[role][rows], noise["validation_probes"])
    assert np.any(noise["validation_probes"] != 0)
    another = prototype.make_inputs(replace(spec, seed=18), coords)
    for role in ("baseline_A", "baseline_B", "validation_probes"):
        assert not np.array_equal(noisy[role], another[role])


def test_heldout_locations_are_eight_unique_rows_disjoint_from_fixed_five_fit_rows(
    coords,
):
    inputs = prototype.make_inputs(prototype.ReferenceSpec(), coords)
    fit_rows, validation_rows = inputs["fit_rows"], inputs["validation_rows"]
    assert fit_rows.dtype.kind in "iu"
    assert validation_rows.dtype.kind in "iu"
    assert fit_rows.shape == (5,)
    assert validation_rows.shape == (8,)
    assert len(set(fit_rows)) == 5
    assert len(set(validation_rows)) == 8
    assert set(fit_rows).isdisjoint(validation_rows)
    assert inputs["validation_probes"].shape == (8, 8, 3)
    np.testing.assert_array_equal(
        coords[fit_rows],
        np.array([[0, 0], [-0.5, 0], [0.5, 0], [0, -0.5], [0, 0.5]]),
    )
    np.testing.assert_array_equal(
        coords[validation_rows],
        np.array(
            [
                [-0.5, -0.5],
                [-0.5, 0.5],
                [0.5, -0.5],
                [0.5, 0.5],
                [-0.25, 0],
                [0.25, 0],
                [0, -0.25],
                [0, 0.25],
            ]
        ),
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"side": True},
        {"side": 33},
        {"side": 513},
        {"k": True},
        {"k": 16},
        {"probe_count": True},
        {"probe_count": 16},
        {"probe_count": 256},
        {"seed": True},
        {"seed": -1},
        {"seed": 2**32},
        {"baseline_noise": True},
        {"baseline_noise": -0.1},
        {"baseline_noise": 0.1},
        {"baseline_noise": float("nan")},
        {"baseline_noise": float("inf")},
        {"pattern": "no_signal"},
        {"pattern": "model"},
    ],
)
def test_reference_design_is_explicitly_bounded(changes):
    with pytest.raises(ValueError):
        prototype.ReferenceSpec(**changes)


def test_both_reference_arms_retain_all_graph_cells_and_each_loop_estimand(noisy_pair):
    report, arrays = noisy_pair
    assert set(report["arms"]) == {"A", "B"}
    for arm in ("A", "B"):
        arm_report = report["arms"][arm]
        arm_arrays = _arm_arrays(report, arrays, arm)
        assert len(arm_report["cells"]) == 9
        assert {
            (cell["field_graph"], cell["loop_graph"]) for cell in arm_report["cells"]
        } == set(product(FAMILIES, repeat=2))
        for cell in arm_report["cells"]:
            assert len(cell["loops"]) == 10
            for loop in cell["loops"].values():
                assert set(loop["fields"]) == set(ESTIMANDS)
                assert "geometry" in loop
                for fields in loop["fields"].values():
                    assert set(fields) == set(HYPOTHESES)
                    for result in fields.values():
                        assert result["state"] in ("eligible", "insufficient")
                        if result["state"] != "eligible":
                            assert result["value"] is None
        assert arm_report["chronology"]["core_seal_count_before_loops"] == 36
        for family in FAMILIES:
            np.testing.assert_array_equal(
                arm_report["rows"][family]["baseline"]["stencil_rows"],
                report["heldout"]["fit_rows"],
            )
        assert all(np.isfinite(value).all() for value in arm_arrays.values())
    json.dumps(report, allow_nan=False)


def test_reference_arms_share_identical_plane_and_evaluation_bytes(noisy_pair):
    report, arrays = noisy_pair
    a, b = (_arm_arrays(report, arrays, arm) for arm in ("A", "B"))
    for key in ("plane", "evaluation", "coords", "faces", "graph_states"):
        np.testing.assert_array_equal(a[key], b[key])
        assert previous._hash(a[key]) == previous._hash(b[key])
    assert not np.array_equal(a["baseline"], b["baseline"])
    for family in FAMILIES:
        for suffix in ("frames", "support", "pooled_covariance", "edges"):
            np.testing.assert_array_equal(
                a[f"{family}_{suffix}"], b[f"{family}_{suffix}"]
            )
        for hypothesis in HYPOTHESES:
            np.testing.assert_array_equal(
                a[f"{family}_full_{hypothesis}_values"],
                b[f"{family}_full_{hypothesis}_values"],
            )


def test_residual_change_is_negative_reference_prediction_change_with_fixed_full_field(
    noisy_pair,
):
    report, arrays = noisy_pair
    a, b = (_arm_arrays(report, arrays, arm) for arm in ("A", "B"))
    for family, hypothesis in product(FAMILIES, HYPOTHESES):
        residual = f"{family}_residual_affine_{hypothesis}_values"
        baseline = f"{family}_local_affine_{hypothesis}_values"
        np.testing.assert_allclose(
            a[residual] - b[residual],
            -(a[baseline] - b[baseline]),
            atol=1e-12,
            rtol=1e-12,
        )
        observation = report["paired_residual"][family][hypothesis]
        assert observation["state"] == "available"
        assert observation["maximum_identity_error"] <= 1e-12


@pytest.mark.parametrize("pattern", ["curved_coherent", "quadratic_excess"])
@pytest.mark.parametrize("probe_count", [8, 128])
def test_noiseless_reference_arms_are_duplicate_controls_with_unchanged_predecessor_fields(
    pattern, probe_count
):
    report, arrays = prototype.measure_pair(
        prototype.ReferenceSpec(
            pattern=pattern, probe_count=probe_count, baseline_noise=0
        )
    )
    assert report["design"]["independent_noise_realizations"] is False
    assert report["design"]["independent_noise_stream_count"] == 0
    assert report["design"]["independent_reference_draw_count"] == 0
    a, b = (_arm_arrays(report, arrays, arm) for arm in ("A", "B"))
    assert a.keys() == b.keys()
    for key in a:
        np.testing.assert_array_equal(a[key], b[key], err_msg=key)
    assert report["arms"]["A"]["cells"] == report["arms"]["B"]["cells"]
    _, reference = previous.measure_case(previous.ScaleSpec(pattern=pattern))
    for family, estimand, hypothesis in product(FAMILIES, ESTIMANDS, HYPOTHESES):
        key = f"{family}_{estimand}_{hypothesis}_values"
        if key not in reference:
            assert key not in a
        else:
            np.testing.assert_allclose(a[key], reference[key], atol=1e-10, rtol=1e-10)
    for family, hypothesis in product(FAMILIES, HYPOTHESES):
        coefficients_a = report["arms"]["A"]["rows"][family]["baseline"][
            "coefficients"
        ][hypothesis]
        coefficients_b = report["arms"]["B"]["rows"][family]["baseline"][
            "coefficients"
        ][hypothesis]
        assert coefficients_a == coefficients_b
        assert (
            report["paired_residual"][family][hypothesis]["maximum_identity_error"] == 0
        )


def test_heldout_prediction_errors_replay_without_selecting_or_admitting_a_reference(
    noisy_pair,
):
    report, arrays = noisy_pair
    heldout = report["heldout"]
    assert heldout["heldout_used_for_fit_or_selection"] is False
    assert heldout["new_admission_threshold"] is None
    assert report["design"]["selection_performed"] is False
    assert report["scope"]["reference_selected"] is False
    assert report["design"]["independent_reference_draw_count"] == 2
    assert report["design"]["independent_noise_stream_count"] == 3
    for family, hypothesis in product(FAMILIES, HYPOTHESES):
        observed = arrays[f"validation_{family}_{hypothesis}_values"]
        for arm in ("A", "B"):
            entry = heldout["rows"][family][hypothesis][arm]
            assert entry["state"] == "available"
            assert entry["required_vertex_count"] == 8
            assert entry["selection_performed"] is False
            prediction = arrays[f"validation_{arm}_{family}_{hypothesis}_prediction"]
            errors = np.linalg.norm(prediction - observed, axis=1)
            np.testing.assert_array_equal(
                errors, arrays[f"validation_{arm}_{family}_{hypothesis}_errors"]
            )
            np.testing.assert_allclose(entry["prediction_errors"], errors)
            assert entry["euclidean_rmse"] == pytest.approx(np.sqrt(np.mean(errors**2)))
            assert entry["maximum_error"] == pytest.approx(errors.max())
            assert (
                entry["baseline_seal_sha256"]
                == report["arms"][arm]["rows"][family]["baseline"]["seal_sha256"]
            )
            assert entry["validation_probe_sha256"] == previous._hash(
                arrays["validation_probes"]
            )


def test_pair_summary_keeps_unavailable_cells_separate_from_winding_agreement(
    noisy_pair,
):
    report, _ = noisy_pair
    assert len(report["paired_cells"]) == 9
    assert report["summary"]["required_cell_count"] == 9
    for hypothesis in HYPOTHESES:
        expected = dict.fromkeys(
            (
                "both_admitted_equal",
                "both_admitted_different",
                "A_only_admitted",
                "B_only_admitted",
                "neither_admitted",
            ),
            0,
        )
        for cell in report["paired_cells"]:
            assert len(cell["loops"]) == 10
            for loop in cell["loops"].values():
                pair = loop[hypothesis]
                admitted_a = pair["A"]["state"] == "eligible"
                admitted_b = pair["B"]["state"] == "eligible"
                assert pair["both_eligible"] is (admitted_a and admitted_b)
                if not pair["both_eligible"]:
                    assert pair["same_sampled_winding"] is None
            pair = cell["loops"]["outer_forward"][hypothesis]
            if pair["both_eligible"]:
                category = (
                    "both_admitted_equal"
                    if pair["same_sampled_winding"]
                    else "both_admitted_different"
                )
            elif pair["A"]["state"] == "eligible":
                category = "A_only_admitted"
            elif pair["B"]["state"] == "eligible":
                category = "B_only_admitted"
            else:
                category = "neither_admitted"
            expected[category] += 1
        assert report["summary"][hypothesis] == expected
        assert sum(expected.values()) == 9


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
    report, _ = prototype.measure_pair(prototype.ReferenceSpec(probe_count=32))
    assert state["baseline_moments"] == 6
    assert state["validation_moments"] == 3
    assert state["evaluation_moments"] == 6
    assert cores == {"A": 36, "B": 36}
    assert loops == {"A": 390, "B": 390}
    assert report["chronology"]["baseline_seals_before_any_arm_evaluation"] == 6


def test_validation_probe_mutation_cannot_change_fits_fields_or_any_loop(monkeypatch):
    spec = prototype.ReferenceSpec(probe_count=32, seed=13)
    original, original_arrays = prototype.measure_pair(spec)
    make_inputs = prototype.make_inputs

    def changed_validation(*args, **kwargs):
        inputs = make_inputs(*args, **kwargs)
        inputs["validation_probes"] = inputs["validation_probes"] + np.array(
            [0.75, -0.5, 0.25]
        )
        return inputs

    monkeypatch.setattr(prototype, "make_inputs", changed_validation)
    changed, changed_arrays = prototype.measure_pair(spec)
    assert (
        changed["heldout"]["validation_probe_sha256"]
        != original["heldout"]["validation_probe_sha256"]
    )
    assert changed["heldout"]["rows"] != original["heldout"]["rows"]
    for arm in ("A", "B"):
        for key in ("rows", "cells", "summary"):
            assert changed["arms"][arm][key] == original["arms"][arm][key]
        before = _arm_arrays(original, original_arrays, arm)
        after = _arm_arrays(changed, changed_arrays, arm)
        assert before.keys() == after.keys()
        for key in before:
            np.testing.assert_array_equal(after[key], before[key], err_msg=key)


def test_mutating_reference_b_cannot_change_reference_a(monkeypatch):
    spec = prototype.ReferenceSpec(probe_count=32, seed=13)
    original, original_arrays = prototype.measure_pair(spec)
    make_inputs = prototype.make_inputs

    def changed_b(*args, **kwargs):
        inputs = make_inputs(*args, **kwargs)
        inputs["baseline_B"] = inputs["baseline_B"] + np.array([0.5, -0.25, 0.0])
        return inputs

    monkeypatch.setattr(prototype, "make_inputs", changed_b)
    changed, changed_arrays = prototype.measure_pair(spec)
    for key in ("rows", "cells", "summary"):
        assert changed["arms"]["A"][key] == original["arms"]["A"][key]
    before = _arm_arrays(original, original_arrays, "A")
    after = _arm_arrays(changed, changed_arrays, "A")
    for key in before:
        np.testing.assert_array_equal(after[key], before[key], err_msg=key)
    family = FAMILIES[0]
    assert (
        changed["arms"]["B"]["rows"][family]["baseline"]["coefficients"]
        != original["arms"]["B"]["rows"][family]["baseline"]["coefficients"]
    )


def test_measurement_does_not_mutate_predecessor_globals():
    names = ("make_probes", "moments", "_covariance", "prepare_row", "measure_case")
    before = {name: getattr(previous, name) for name in names}
    prototype.measure_pair(prototype.ReferenceSpec())
    assert {name: getattr(previous, name) for name in names} == before


def test_serialized_pair_replays_every_array_and_refuses_overwrite(tmp_path):
    output = tmp_path / "reference-pair"
    report, arrays = prototype.measure_pair(prototype.ReferenceSpec(), output=output)
    assert json.loads((output / "report.json").read_text()) == report
    assert (
        report["array_artifact"]["sha256"]
        == hashlib.sha256((output / "arrays.npz").read_bytes()).hexdigest()
    )
    with np.load(output / "arrays.npz", allow_pickle=False) as saved:
        assert set(saved.files) == set(arrays)
        for key, expected in arrays.items():
            np.testing.assert_array_equal(saved[key], expected, err_msg=key)
    with pytest.raises(FileExistsError):
        prototype.measure_pair(prototype.ReferenceSpec(), output=output)


def test_campaign_preserves_registered_thirty_two_pair_denominator_and_noiseless_controls():
    specs = runner.case_specs()
    assert len(specs) == len(set(specs)) == 32
    primary, sentinels, controls = specs[:24], specs[24:28], specs[28:]
    patterns = ("curved_coherent", "quadratic_excess")
    assert {(s.pattern, s.seed, s.probe_count) for s in primary} == set(
        product(patterns, (0, 1, 2, 3), (8, 32, 128))
    )
    assert all(s.side == 65 and s.baseline_noise == 0.03 for s in primary)
    assert {(s.pattern, s.seed) for s in sentinels} == set(product(patterns, (0, 1)))
    assert all(
        s.side == 257 and s.probe_count == 128 and s.baseline_noise == 0.03
        for s in sentinels
    )
    assert {(s.pattern, s.probe_count) for s in controls} == set(
        product(patterns, (8, 128))
    )
    assert all(s.side == 65 and s.seed == 0 and s.baseline_noise == 0 for s in controls)
    assert all(s.k == 8 for s in specs)


def test_campaign_source_lock_includes_committed_protocol_and_current_test_bytes():
    lock = runner.source_lock()
    assert lock[runner.PROTOCOL] == runner.PROTOCOL_SHA256
    required = {
        runner.PROTOCOL,
        "scripts/prototype_p4_reference_validation_v0_1.py",
        "scripts/run_p4_reference_validation_v0_1.py",
        "scripts/p4_dense_moment_adapter_v0_1.py",
        "tests/test_p4_reference_validation_v0_1.py",
    }
    assert required <= lock.keys()
    assert any(key.startswith("src/") for key in lock)
    for path, expected in lock.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected


def test_changed_protocol_fails_before_output_or_subprocess(monkeypatch, tmp_path):
    monkeypatch.setattr(runner.platform, "system", lambda: "Linux")
    monkeypatch.setattr(runner, "sha", lambda path: "0" * 64)

    def forbidden_process(*args, **kwargs):
        pytest.fail("changed protocol must fail before any subprocess")

    monkeypatch.setattr(runner.subprocess, "run", forbidden_process)
    output = tmp_path / "changed-protocol"
    with pytest.raises(ValueError, match="protocol"):
        runner.run(output)
    assert not output.exists()


@pytest.mark.parametrize("first_timeout", [False, True])
def test_campaign_preserves_failed_attempt_and_all_unrun_pairs_when_source_changes(
    monkeypatch, tmp_path, first_timeout
):
    counts = {"locks": 0, "children": 0}

    def changing_lock():
        counts["locks"] += 1
        before_count = 2 if first_timeout else 1
        return {"test-lock": "before" if counts["locks"] <= before_count else "after"}

    def fake_process(command, **kwargs):
        if command == ["git", "rev-parse", "HEAD"]:
            return SimpleNamespace(stdout="1" * 40 + "\n", returncode=0)
        assert first_timeout is True
        counts["children"] += 1
        assert counts["children"] == 1
        assert kwargs["timeout"] <= runner.CASE_SECONDS
        assert kwargs["env"]["OPENBLAS_NUM_THREADS"] == "1"
        assert kwargs["env"]["OMP_NUM_THREADS"] == "1"
        assert kwargs["preexec_fn"] is runner.limits
        raise runner.subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(runner.platform, "system", lambda: "Linux")
    monkeypatch.setattr(runner, "source_lock", changing_lock)
    monkeypatch.setattr(runner.subprocess, "run", fake_process)
    output = tmp_path / "retained-campaign"
    manifest = runner.run(output)
    plan = json.loads((output / "plan.json").read_text())
    assert plan["paired_units"] == manifest["paired_units"] == 32
    assert plan["arm_measurements"] == manifest["arm_measurements_planned"] == 64
    assert len(manifest["units"]) == len(plan["cases"]) == 32
    assert manifest["completed"] == 0
    assert [unit["index"] for unit in manifest["units"]] == list(range(32))
    assert plan["resource_limits"] == {
        "case_seconds": 180,
        "campaign_seconds": 1200,
        "address_space_bytes": 16 * 2**30,
        "max_file_bytes": 2 * 2**30,
        "pre_unit_disk_admission_bytes": 8 * 2**30,
        "concurrent_children": 1,
        "blas_threads": 1,
    }
    assert plan["reference_backend"] == "numpy"
    assert plan["gpu_used"] is False
    assert plan["baseline_selection_performed"] is False
    assert plan["heldout_acceptance_threshold"] is None
    remaining = manifest["units"]
    if first_timeout:
        first, remaining = remaining[0], remaining[1:]
        assert first["status"] == "timeout"
        assert first["reason"] == "bounded-unit-deadline"
        assert (output / "unit-00.attempt.json").is_file()
        assert (output / "unit-00.terminal.json").is_file()
    assert all(
        unit["status"] == "not_run" and unit["reason"] == "source-changed"
        for unit in remaining
    )
    assert (
        manifest["plan_sha256"]
        == hashlib.sha256((output / "plan.json").read_bytes()).hexdigest()
    )
