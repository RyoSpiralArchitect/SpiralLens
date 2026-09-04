from __future__ import annotations

import copy
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
import p4_dense_moment_adapter_v0_1 as dense  # noqa: E402
import prototype_p4_large_domain_v0_1 as previous  # noqa: E402
import prototype_p4_probe_sensitivity_v0_1 as prototype  # noqa: E402
import run_p4_probe_sensitivity_v0_1 as runner  # noqa: E402


ROLES = ("plane", "baseline", "evaluation")
FAMILIES = previous.FAMILIES
ESTIMANDS = previous.ESTIMANDS
HYPOTHESES = ("F2", "F4")
NUMERIC_ATOL = 1e-9
NUMERIC_RTOL = 1e-9


def _assert_values(actual, expected, context):
    assert actual.keys() == expected.keys(), context
    for key, expected_value in expected.items():
        if isinstance(expected_value, bool):
            assert actual[key] is expected_value, (*context, key)
        else:
            np.testing.assert_allclose(
                actual[key],
                expected_value,
                atol=NUMERIC_ATOL,
                rtol=NUMERIC_RTOL,
                err_msg=str((*context, key)),
            )


def _assert_measurement_parity(actual, expected, actual_arrays, expected_arrays):
    """Check every outcome, not just the selected summary or admitted cells."""
    assert actual_arrays.keys() == expected_arrays.keys()
    for key, before in expected_arrays.items():
        after = actual_arrays[key]
        assert after.dtype == before.dtype, key
        if before.dtype.kind in "biu" or key in (*ROLES, "coords", "graph_states"):
            np.testing.assert_array_equal(after, before, err_msg=key)
        else:
            np.testing.assert_allclose(
                after, before, atol=NUMERIC_ATOL, rtol=NUMERIC_RTOL, err_msg=key
            )
    for family in FAMILIES:
        after_baseline = actual["rows"][family]["baseline"]
        before_baseline = expected["rows"][family]["baseline"]
        assert after_baseline["state"] == before_baseline["state"], family
        assert after_baseline["stencil_rows"] == before_baseline["stencil_rows"]
        assert (
            after_baseline["baseline_probe_sha256"]
            == before_baseline["baseline_probe_sha256"]
        )
        for hypothesis in HYPOTHESES:
            after = after_baseline["coefficients"][hypothesis]
            before = before_baseline["coefficients"][hypothesis]
            if before is None:
                assert after is None
            else:
                np.testing.assert_allclose(
                    after, before, atol=NUMERIC_ATOL, rtol=NUMERIC_RTOL
                )
        for estimand, hypothesis in product(ESTIMANDS, HYPOTHESES):
            after = actual["rows"][family]["fields"][estimand][hypothesis]
            before = expected["rows"][family]["fields"][estimand][hypothesis]
            context = (family, estimand, hypothesis)
            assert after["missing"] == before["missing"], context
            for key in ("state", "classification", "candidate_count", "charge_blind"):
                assert after["core"][key] == before["core"][key], (*context, key)
    assert len(actual["cells"]) == len(expected["cells"]) == 9
    for after_cell, before_cell in zip(actual["cells"], expected["cells"], strict=True):
        identity = (after_cell["field_graph"], after_cell["loop_graph"])
        assert identity == (
            before_cell["field_graph"],
            before_cell["loop_graph"],
        )
        assert len(after_cell["loops"]) == len(before_cell["loops"]) == 10
        assert after_cell["loops"].keys() == before_cell["loops"].keys()
        for loop_name, after_loop in after_cell["loops"].items():
            before_loop = before_cell["loops"][loop_name]
            observations = [
                ("geometry", after_loop["geometry"], before_loop["geometry"])
            ]
            observations.extend(
                (
                    f"{estimand}/{hypothesis}",
                    after_loop["fields"][estimand][hypothesis],
                    before_loop["fields"][estimand][hypothesis],
                )
                for estimand, hypothesis in product(ESTIMANDS, HYPOTHESES)
            )
            for name, after, before in observations:
                context = (*identity, loop_name, name)
                assert after["state"] == before["state"], context
                assert after["reason"] == before["reason"], context
                if before["value"] is None:
                    assert after["value"] is None, context
                else:
                    _assert_values(after["value"], before["value"], context)


@pytest.fixture(scope="module")
def coords():
    return previous.backend.make_domain(17)["coords"]


@pytest.mark.parametrize("probe_count", [8, 32, 128])
def test_probe_count_has_nested_per_vertex_role_noise_not_reshaped_rng_stream(
    coords, probe_count
):
    spec = prototype.ProbeSpec(probe_count=128, probe_noise=0.03, seed=17)
    largest = prototype.make_probes(spec, coords)
    current = prototype.make_probes(replace(spec, probe_count=probe_count), coords)
    for role in ROLES:
        assert current[role].shape == (len(coords), probe_count, 3)
        assert current[role].dtype == np.float64
        np.testing.assert_array_equal(current[role], largest[role][:, :probe_count])


@pytest.mark.parametrize("role", ROLES)
def test_noise_role_changes_only_selected_inputs_with_same_noise_realization(
    coords, role
):
    spec = prototype.ProbeSpec(probe_count=32, probe_noise=0.03, seed=19)
    all_roles = prototype.make_probes(spec, coords)
    selected = prototype.make_probes(replace(spec, noise_role=role), coords)
    clean = prototype.make_probes(
        replace(spec, noise_role="none", probe_noise=0), coords
    )
    for name in ROLES:
        if name == role:
            np.testing.assert_array_equal(selected[name], all_roles[name])
            assert not np.array_equal(selected[name], clean[name])
        else:
            np.testing.assert_array_equal(selected[name], clean[name])
    assert not np.array_equal(
        all_roles["baseline"] - clean["baseline"],
        all_roles["evaluation"] - clean["evaluation"],
    )


@pytest.mark.parametrize("probe_count", [32, 128])
def test_more_noiseless_probes_repeat_cube_without_new_directions(coords, probe_count):
    base = prototype.ProbeSpec(probe_noise=0, noise_role="none")
    eight = prototype.make_probes(base, coords)
    more = prototype.make_probes(replace(base, probe_count=probe_count), coords)
    for role in ROLES:
        np.testing.assert_array_equal(
            more[role], np.tile(eight[role], (1, probe_count // 8, 1))
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"side": True},
        {"side": 33},
        {"side": 513},
        {"k": True},
        {"k": 4},
        {"probe_count": True},
        {"probe_count": 16},
        {"probe_count": 256},
        {"seed": True},
        {"seed": -1},
        {"seed": 2**32},
        {"noise_role": "unknown"},
        {"noise_role": "none", "probe_noise": 0.03},
        {"probe_noise": True},
        {"probe_noise": -0.1},
        {"probe_noise": float("nan")},
        {"probe_noise": float("inf")},
        {"warp": True},
        {"warp": float("nan")},
        {"pattern": "model"},
    ],
)
def test_prospective_probe_spec_is_finite_and_bounded(changes):
    with pytest.raises(ValueError):
        prototype.ProbeSpec(**changes)


@pytest.mark.parametrize("backend", ["numpy", "bogus", "auto"])
def test_adapter_backend_is_explicit(backend):
    if backend == "numpy":
        assert dense.DenseMomentAdapter(backend=backend).receipt()["backend"] == backend
    else:
        with pytest.raises(ValueError):
            dense.DenseMomentAdapter(backend=backend)


@pytest.mark.parametrize("batch_vertices", [True, 0, -1, 1.5, 65537])
def test_adapter_rejects_invalid_batch_sizes(batch_vertices):
    with pytest.raises(ValueError):
        dense.DenseMomentAdapter(backend="numpy", batch_vertices=batch_vertices)


@pytest.mark.parametrize("batch_vertices", [1, 7, 64])
@pytest.mark.parametrize("probe_count", [8, 128])
def test_numpy_adapter_batched_covariance_and_moments_match_reference(
    batch_vertices, probe_count
):
    rng = np.random.default_rng(421)
    probes = rng.normal(size=(19, probe_count, 3))
    frames = np.broadcast_to(np.eye(3)[:, :2], (19, 3, 2)).copy()
    adapter = dense.DenseMomentAdapter(backend="numpy", batch_vertices=batch_vertices)
    covariance = adapter.covariance(probes)
    moments = adapter.moments(frames, probes)
    np.testing.assert_allclose(
        covariance, previous._covariance(probes), atol=1e-12, rtol=1e-12
    )
    assert covariance.shape == (19, 3, 3)
    assert covariance.dtype == np.float64
    assert moments.keys() == {"F2", "F4"}
    expected = previous.moments(frames, probes)
    for hypothesis in HYPOTHESES:
        assert moments[hypothesis].shape == (19, 2)
        assert moments[hypothesis].dtype == np.float64
        np.testing.assert_allclose(
            moments[hypothesis], expected[hypothesis], atol=1e-12, rtol=1e-12
        )
    receipt = adapter.receipt()
    json.dumps(receipt, allow_nan=False)
    assert receipt["backend"] == "numpy"
    assert receipt["dtype"] == "float64"
    assert receipt["gpu_used"] is False
    assert receipt["batch_vertices"] == batch_vertices
    for operation in ("covariance", "moments"):
        assert receipt["operations"][operation]["calls"] == 1
        assert (
            receipt["operations"][operation]["batches"]
            == (19 + batch_vertices - 1) // batch_vertices
        )
        assert receipt["operations"][operation]["seconds"] >= 0


@pytest.mark.parametrize(
    "probes",
    [
        np.ones((2, 8, 3), dtype=np.float32),
        np.ones((2, 8, 3), dtype=np.int64),
        np.ones((2, 8)),
        np.ones((2, 8, 2)),
        np.ones((0, 8, 3)),
        np.ones((2, 0, 3)),
        np.full((2, 8, 3), np.nan),
        np.full((2, 8, 3), np.inf),
    ],
)
def test_adapter_rejects_invalid_probe_dtype_shape_and_finiteness(probes):
    adapter = dense.DenseMomentAdapter(backend="numpy")
    with pytest.raises((TypeError, ValueError)):
        adapter.covariance(probes)
    with pytest.raises((TypeError, ValueError)):
        adapter.moments(np.ones((2, 3, 2)), probes)


@pytest.mark.parametrize(
    "frames",
    [
        np.ones((2, 3, 2), dtype=np.float32),
        np.ones((2, 3, 2), dtype=np.int64),
        np.ones((3, 3, 2)),
        np.ones((2, 2, 3)),
        np.ones((2, 3)),
        np.full((2, 3, 2), np.nan),
        np.full((2, 3, 2), np.inf),
    ],
)
def test_adapter_rejects_invalid_frame_dtype_shape_and_finiteness(frames):
    with pytest.raises((TypeError, ValueError)):
        dense.DenseMomentAdapter(backend="numpy").moments(frames, np.ones((2, 8, 3)))


def test_adapter_accepts_rank_deficient_observations_without_inventing_support():
    adapter = dense.DenseMomentAdapter(backend="numpy", batch_vertices=1)
    probes = np.zeros((3, 8, 3))
    frames = np.broadcast_to(np.eye(3)[:, :2], (3, 3, 2)).copy()
    np.testing.assert_array_equal(adapter.covariance(probes), np.zeros((3, 3, 3)))
    for values in adapter.moments(frames, probes).values():
        np.testing.assert_array_equal(values, np.zeros((3, 2)))


def test_adapter_accepts_noncontiguous_float64_without_mutating_inputs_or_receipts():
    probes = np.arange(9 * 16 * 3, dtype=np.float64).reshape(9, 16, 3)[:, ::2, ::-1]
    frames = np.tile(np.eye(3)[:, :2], (9, 1, 1))[:, ::-1, :]
    probes_before, frames_before = probes.copy(), frames.copy()
    adapter = dense.DenseMomentAdapter(backend="numpy", batch_vertices=7)
    covariance = adapter.covariance(probes)
    result = adapter.moments(frames, probes)
    np.testing.assert_allclose(covariance, previous._covariance(probes))
    for key, expected in previous.moments(frames, probes).items():
        np.testing.assert_allclose(result[key], expected)
    np.testing.assert_array_equal(probes, probes_before)
    np.testing.assert_array_equal(frames, frames_before)
    receipt = adapter.receipt()
    receipt["operations"]["moments"]["calls"] = 987
    assert adapter.receipt()["operations"]["moments"]["calls"] == 1


def _cuda_available():
    try:
        import torch
    except ImportError:
        return False
    return torch.cuda.is_available()


def test_unavailable_cuda_is_an_explicit_failure_not_cpu_fallback():
    if _cuda_available():
        pytest.skip("CUDA is available; actual CUDA execution is checked below")
    with pytest.raises(RuntimeError, match="(?i)(cuda|torch|pytorch)"):
        adapter = dense.DenseMomentAdapter(backend="cuda")
        adapter.covariance(np.ones((2, 8, 3)))


@pytest.mark.parametrize("installed_without_cuda", [False, True])
def test_cuda_runtime_absence_is_fail_closed_even_on_gpu_test_hosts(
    monkeypatch, installed_without_cuda
):
    fake_torch = (
        SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))
        if installed_without_cuda
        else None
    )
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    with pytest.raises(RuntimeError, match="(?i)(cuda|torch|pytorch)"):
        dense.DenseMomentAdapter(backend="cuda")


@pytest.mark.parametrize(
    "pattern",
    [
        "quadratic_excess",
        "curved_coherent",
        "input_identity",
        "no_signal",
        "collapsed_support",
    ],
)
def test_noiseless_eight_probe_numpy_measurement_matches_previous_all_cells(pattern):
    spec = prototype.ProbeSpec(pattern=pattern, noise_role="none", probe_noise=0)
    report, arrays = prototype.measure_case(spec, backend="numpy")
    before, before_arrays = previous.measure_case(previous.ScaleSpec(pattern=pattern))
    _assert_measurement_parity(report, before, arrays, before_arrays)
    assert report["scope"]["gpu_used"] is False
    assert report["scope"]["model_accessed"] is False
    assert report["scope"]["claim_ceiling"] == "level_0"
    assert report["scope"]["scientific_authority"] is False
    assert report["scope"]["verified_core"] is False
    assert report["numeric_adapter"]["backend"] == "numpy"
    assert report["numeric_adapter"]["gpu_used"] is False
    assert report["design"]["axis_sizes"] == [3, 3, 1]
    assert report["design"]["all_nine_required"] is True


def test_sensitivity_does_not_mutate_predecessor_dependency_globals():
    before = {
        name: getattr(previous, name)
        for name in (
            "make_probes",
            "moments",
            "_covariance",
            "prepare_row",
            "measure_case",
        )
    }
    prototype.measure_case(
        prototype.ProbeSpec(probe_count=32, noise_role="evaluation", probe_noise=0.03)
    )
    assert {name: getattr(previous, name) for name in before} == before


def test_isolated_measurement_namespaces_are_not_shared_between_backends():
    adapter_a = dense.DenseMomentAdapter(backend="numpy", batch_vertices=1)
    adapter_b = dense.DenseMomentAdapter(backend="numpy", batch_vertices=31)
    function_a, namespace_a = prototype._isolated_measurement(adapter_a)
    function_b, namespace_b = prototype._isolated_measurement(adapter_b)
    assert namespace_a is not namespace_b
    assert function_a.__globals__ is namespace_a
    assert function_b.__globals__ is namespace_b
    assert namespace_a["prepare_row"].__globals__ is namespace_a
    assert namespace_b["prepare_row"].__globals__ is namespace_b
    assert namespace_a["_covariance"].__self__ is adapter_a
    assert namespace_b["_covariance"].__self__ is adapter_b
    assert namespace_a["moments"].__self__ is adapter_a
    assert namespace_b["moments"].__self__ is adapter_b
    assert namespace_a is not vars(previous)
    assert namespace_b is not vars(previous)


def test_real_call_order_keeps_three_baselines_then_thirty_six_core_seals_before_loops():
    counts = {"baselines": 0, "cores": 0, "loops": 0}
    captured = {}
    adapter = dense.DenseMomentAdapter(backend="numpy", batch_vertices=17)
    measure, namespace = prototype._isolated_measurement(adapter)
    make, prepare, moments, core = (
        namespace[name]
        for name in ("make_probes", "prepare_row", "moments", "core_record")
    )

    def capture(*args, **kwargs):
        probes = make(*args, **kwargs)
        captured.update(probes)
        return probes

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

    # Replace only this call's namespace, including gate proxies; not the frozen
    # predecessor module or chain module globals, even during instrumentation.
    old_proxy = SimpleNamespace(**vars(namespace["old"]))
    chain_proxy = SimpleNamespace(**vars(old_proxy.chain))
    chain_proxy._geometry = checked_loop(chain_proxy._geometry)
    chain_proxy._winding = checked_loop(chain_proxy._winding)
    old_proxy.chain = chain_proxy
    namespace.update(
        make_probes=capture,
        prepare_row=checked_prepare,
        moments=checked_moments,
        core_record=checked_core,
        old=old_proxy,
    )
    report, _ = measure(prototype.ProbeSpec(probe_count=32, probe_noise=0.03))
    assert counts == {"baselines": 3, "cores": 36, "loops": 390}
    assert report["chronology"] == {
        "baselines_before_evaluation": True,
        "core_seal_count_before_loops": 36,
    }


def test_sensitivity_arrays_replay_and_output_is_never_overwritten(tmp_path):
    output = tmp_path / "probe-sensitivity"
    report, arrays = prototype.measure_case(
        prototype.ProbeSpec(pattern="input_identity", probe_count=32),
        backend="numpy",
        output=output,
    )
    assert json.loads((output / "report.json").read_text()) == report
    assert (
        report["array_artifact"]["sha256"]
        == hashlib.sha256((output / "arrays.npz").read_bytes()).hexdigest()
    )
    with np.load(output / "arrays.npz", allow_pickle=False) as saved:
        assert set(saved.files) == set(arrays)
        for key, values in arrays.items():
            np.testing.assert_array_equal(saved[key], values)
    with pytest.raises(FileExistsError):
        prototype.measure_case(prototype.ProbeSpec(), backend="numpy", output=output)


@pytest.fixture(scope="module")
def runner_reference():
    return prototype.measure_case(
        prototype.ProbeSpec(pattern="quadratic_excess", probe_count=8),
        backend="numpy",
    )


def test_runner_comparison_accepts_same_measurement_without_hash_identity_requirement(
    runner_reference,
):
    report, arrays = runner_reference
    compared = copy.deepcopy(report)
    compared["dependency_injection"]["successor_source_sha256"] = "0" * 64
    result = runner.compare(report, compared, arrays, arrays)
    assert result["passed"] is True
    assert result["failures"] == []
    assert result["maximum_array_absolute_difference"] == 0


@pytest.mark.parametrize("field", ["state", "stencil_rows", "coefficients"])
def test_runner_comparison_rejects_baseline_gate_stencil_or_coefficient_mutation(
    runner_reference, field
):
    report, arrays = runner_reference
    mutated = copy.deepcopy(report)
    baseline = mutated["rows"][FAMILIES[0]]["baseline"]
    if field == "state":
        baseline["state"] = "insufficient"
    elif field == "stencil_rows":
        baseline["stencil_rows"][0] += 1
    else:
        baseline["coefficients"]["F2"][0][0] += 0.25
    result = runner.compare(report, mutated, arrays, arrays)
    assert result["passed"] is False
    assert result["failures"]


@pytest.mark.parametrize("field", ["field_graph", "loop_graph"])
def test_runner_comparison_rejects_cell_graph_identity_mutation(
    runner_reference, field
):
    report, arrays = runner_reference
    mutated = copy.deepcopy(report)
    mutated["cells"][0][field] = FAMILIES[1]
    result = runner.compare(report, mutated, arrays, arrays)
    assert result["passed"] is False
    assert result["failures"]


@pytest.mark.parametrize("mutation", ["dtype", "shape", "missing"])
def test_runner_comparison_rejects_array_contract_mutation_without_broadcasting(
    runner_reference, mutation
):
    report, arrays = runner_reference
    mutated = dict(arrays)
    key = FAMILIES[0] + "_frames"
    if mutation == "dtype":
        mutated[key] = mutated[key].astype(np.float32)
    elif mutation == "shape":
        mutated[key] = mutated[key][:-1]
    else:
        del mutated[key]
    result = runner.compare(report, report, arrays, mutated)
    assert result["passed"] is False
    assert result["failures"]


def test_runner_fixes_twenty_eight_sensitivity_conditions_before_any_result():
    specs = runner.case_specs()
    assert len(specs) == len(set(specs)) == 28
    noisy, clean = specs[:24], specs[24:]
    assert {(spec.side, spec.probe_count, spec.noise_role) for spec in noisy} == set(
        product((65, 257), (8, 32, 128), ("all", "plane", "baseline", "evaluation"))
    )
    assert all(
        spec.probe_noise == 0.03 and spec.pattern == "curved_coherent" for spec in noisy
    )
    assert {(spec.pattern, spec.probe_count) for spec in clean} == set(
        product(("quadratic_excess", "curved_coherent"), (8, 128))
    )
    assert all(
        spec.side == 65 and spec.probe_noise == 0 and spec.noise_role == "none"
        for spec in clean
    )
    assert all(spec.k == 8 and spec.seed == 0 and spec.warp == 0 for spec in specs)


def test_runner_source_lock_covers_actual_dependencies_with_current_file_hashes():
    lock = runner.source_lock()
    required = {
        "scripts/p4_dense_moment_adapter_v0_1.py",
        "scripts/p4_sparse_graph_backend_v0_1.py",
        "scripts/prototype_p4_large_domain_v0_1.py",
        "scripts/prototype_p4_probe_sensitivity_v0_1.py",
        "scripts/run_p4_probe_sensitivity_v0_1.py",
    }
    assert required <= lock.keys()
    assert any(key.startswith("src/") for key in lock)
    for path, expected in lock.items():
        assert len(expected) == 64
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected


def test_runner_keeps_three_execution_stages_and_all_twenty_eight_unrun_cases(
    monkeypatch, tmp_path
):
    calls = {"lock": 0}

    def changing_lock():
        calls["lock"] += 1
        return {"synthetic-test-lock": "before" if calls["lock"] == 1 else "after"}

    def forbidden_process(*args, **kwargs):
        pytest.fail("source-change admission must stop before launching a subprocess")

    monkeypatch.setattr(runner.platform, "system", lambda: "Linux")
    monkeypatch.setattr(runner, "source_lock", changing_lock)
    monkeypatch.setattr(runner.subprocess, "run", forbidden_process)
    output = tmp_path / "source-changed"
    manifest = runner.run(output)
    plan = json.loads((output / "plan.json").read_text())
    expected_stages = [["parity", 0], ["parity", 1], ["benchmark", 0]] + [
        ["science", index] for index in range(28)
    ]
    assert plan["stages"] == expected_stages
    assert len(plan["cases"]) == 28
    assert plan["reference_backend"] == "numpy"
    assert plan["cuda_auto_selected"] is False
    assert plan["concurrent_children"] == 1
    assert manifest["planned"] == len(manifest["stages"]) == 31
    assert manifest["completed"] == 0
    assert [
        [stage["mode"], stage["index"]] for stage in manifest["stages"]
    ] == expected_stages
    assert all(
        stage["status"] == "not_run" and stage["reason"] == "source-changed"
        for stage in manifest["stages"]
    )
    assert (
        manifest["plan_sha256"]
        == hashlib.sha256((output / "plan.json").read_bytes()).hexdigest()
    )
    assert not list(output.glob("*.attempt.json"))


@pytest.mark.skipif(
    not _cuda_available(), reason="CUDA device unavailable; no CPU fallback"
)
@pytest.mark.parametrize("probe_count", [8, 128])
@pytest.mark.parametrize(
    "pattern,noise",
    [("quadratic_excess", 0.0), ("curved_coherent", 0.03), ("collapsed_support", 0.0)],
)
def test_cuda_matches_numpy_inputs_all_arrays_support_cores_and_every_loop(
    probe_count, pattern, noise
):
    spec = prototype.ProbeSpec(
        pattern=pattern, probe_count=probe_count, probe_noise=noise, seed=7
    )
    cpu, cpu_arrays = prototype.measure_case(spec, backend="numpy")
    cuda, cuda_arrays = prototype.measure_case(spec, backend="cuda")
    _assert_measurement_parity(cuda, cpu, cuda_arrays, cpu_arrays)
    assert cuda["numeric_adapter"]["backend"] == "cuda"
    assert cuda["numeric_adapter"]["gpu_used"] is True
    assert cuda["scope"]["gpu_used"] is True
    assert cuda["numeric_adapter"]["dtype"] == "float64"
    assert cuda["numeric_adapter"]["operations"]["covariance"]["calls"] > 0
    assert cuda["numeric_adapter"]["operations"]["moments"]["calls"] > 0


@pytest.mark.skipif(
    not _cuda_available(), reason="CUDA device unavailable; no CPU fallback"
)
@pytest.mark.parametrize("probe_count", [8, 128])
def test_cuda_dense_batches_preserve_float64_outputs_and_count_completed_work(
    probe_count,
):
    rng = np.random.default_rng(491)
    probes = rng.normal(size=(19, probe_count * 2, 3))[:, ::2, ::-1]
    frames = np.broadcast_to(np.eye(3)[:, :2], (19, 3, 2))[:, ::-1, :]
    probes_before, frames_before = probes.copy(), frames.copy()
    expected_covariance = previous._covariance(probes)
    expected_moments = previous.moments(frames, probes)
    results = []
    for batch_vertices in (1, 7, 64):
        adapter = dense.DenseMomentAdapter(
            backend="cuda", batch_vertices=batch_vertices
        )
        assert adapter.receipt()["gpu_used"] is False
        covariance = adapter.covariance(probes)
        moments = adapter.moments(frames, probes)
        assert covariance.dtype == np.float64
        np.testing.assert_allclose(
            covariance, expected_covariance, atol=1e-12, rtol=1e-12
        )
        for hypothesis in HYPOTHESES:
            assert moments[hypothesis].dtype == np.float64
            np.testing.assert_allclose(
                moments[hypothesis],
                expected_moments[hypothesis],
                atol=1e-12,
                rtol=1e-12,
            )
        receipt = adapter.receipt()
        assert receipt["gpu_used"] is True
        assert receipt["cuda_available"] is True
        assert receipt["silent_fallback"] is False
        assert receipt["peak_gpu_allocated_bytes"] > 0
        assert set(receipt["timing_includes"]) == {
            "validation",
            "host_to_device",
            "compute",
            "device_to_host",
            "synchronization",
        }
        for operation in ("covariance", "moments"):
            assert receipt["operations"][operation]["calls"] == 1
            assert (
                receipt["operations"][operation]["batches"]
                == (19 + batch_vertices - 1) // batch_vertices
            )
        results.append((covariance, moments))
    for covariance, moments in results[1:]:
        np.testing.assert_allclose(covariance, results[0][0], atol=1e-12, rtol=1e-12)
        for hypothesis in HYPOTHESES:
            np.testing.assert_allclose(
                moments[hypothesis], results[0][1][hypothesis], atol=1e-12, rtol=1e-12
            )
    np.testing.assert_array_equal(probes, probes_before)
    np.testing.assert_array_equal(frames, frames_before)
