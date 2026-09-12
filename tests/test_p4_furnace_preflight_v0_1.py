from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "prototype_p4_furnace_preflight_v0_1.py"
sys.path.insert(0, str(SCRIPT_PATH.parent))
import prototype_p4_furnace_preflight_v0_1 as prototype  # noqa: E402


def _rewrite_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, sort_keys=True, allow_nan=False) + "\n")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def frozen_fixtures(tmp_path_factory) -> Path:
    output = tmp_path_factory.mktemp("furnace-preflight") / "fixtures"
    prototype.make_fixtures(output)
    return output


@pytest.fixture
def fixture_copy(tmp_path, frozen_fixtures) -> Path:
    output = tmp_path / "fixtures"
    shutil.copytree(frozen_fixtures, output)
    return output


@pytest.fixture
def measured_hosts(tmp_path, frozen_fixtures, monkeypatch) -> tuple[Path, Path]:
    # This test checks artifact plumbing, not another expensive scientific run.
    def measure(bundle, *, gauge):
        assert gauge == "none"
        assert bundle.observations.coords.shape == (289, 2)
        assert not np.shares_memory(
            bundle.observations.plane_fit_probes,
            bundle.observations.evaluation_probes,
        )
        return {
            "state": "eligible",
            "sampled_winding": 2,
            "fit_support": [True, False],
            "matrix": [[1.0, 0.0], [0.0, 1.0]],
            "amplitude": 0.25,
            "missing": None,
            "field_sha256": "a" * 64,
            "nested": {"core_sha256": "b" * 64, "charge_authority": False},
        }

    monkeypatch.setattr(prototype.cross, "measure_graph_cross", measure)
    paths = tmp_path / "mac", tmp_path / "furnace"
    for path in paths:
        prototype.measure_fixtures(frozen_fixtures, path, path.name)
    return paths


def _replace_result(directory: Path, transform, *, update_digest=True) -> None:
    result_path = directory / "result-0.json"
    report = _read_json(result_path)
    transform(report)
    _rewrite_json(result_path, report)
    if update_digest:
        manifest_path = directory / "manifest.json"
        manifest = _read_json(manifest_path)
        manifest["cases"][0]["sha256"] = prototype.sha256(result_path)
        _rewrite_json(manifest_path, manifest)


def test_fixture_manifest_has_exact_four_anchors_and_kernel_bytes(frozen_fixtures):
    manifest = _read_json(frozen_fixtures / "manifest.json")
    assert manifest["schema_version"] == prototype.SCHEMA
    assert manifest["case_count"] == 4
    assert [record["file"] for record in manifest["cases"]] == [
        f"fixture-{i}.npz" for i in range(4)
    ]
    assert [record["spec"] for record in manifest["cases"]] == [
        asdict(spec) for spec in prototype.ANCHORS
    ]
    assert manifest["kernel_sha256"] == {
        name: hashlib.sha256((SCRIPT_PATH.parent / name).read_bytes()).hexdigest()
        for name in prototype.KERNEL_FILES
    }
    assert manifest["float_atol"] == manifest["float_rtol"] == 1e-10
    assert manifest["discrete_values_must_match_exactly"] is True
    assert manifest["model_data"] is manifest["scientific_authority"] is False


def test_fixture_arrays_are_portable_finite_and_role_separated(frozen_fixtures):
    manifest = _read_json(frozen_fixtures / "manifest.json")
    expected_keys = {
        "coords",
        "faces",
        "plane_fit_probes",
        "baseline_fit_probes",
        "evaluation_probes",
        "graph_states",
        "vertex_ids",
    }
    for record in manifest["cases"]:
        path = frozen_fixtures / record["file"]
        assert prototype.sha256(path) == record["sha256"]
        with np.load(path, allow_pickle=False) as arrays:
            assert set(arrays.files) == expected_keys
            assert arrays["coords"].shape == (289, 2)
            assert arrays["faces"].shape == (512, 3)
            assert arrays["graph_states"].shape == (289, 4)
            np.testing.assert_array_equal(arrays["vertex_ids"], np.arange(289))
            for name in expected_keys:
                assert np.isfinite(arrays[name]).all()
            roles = [
                arrays[name]
                for name in (
                    "plane_fit_probes",
                    "baseline_fit_probes",
                    "evaluation_probes",
                )
            ]
            assert all(role.shape == (289, 8, 3) for role in roles)
            assert not any(
                np.shares_memory(a, b)
                for i, a in enumerate(roles)
                for b in roles[i + 1 :]
            )


def test_fixture_creation_refuses_existing_directory_without_overwrite(fixture_copy):
    previous = prototype.sha256(fixture_copy / "manifest.json")
    with pytest.raises(FileExistsError):
        prototype.make_fixtures(fixture_copy)
    assert prototype.sha256(fixture_copy / "manifest.json") == previous


def test_json_writer_is_exclusive_and_rejects_nonfinite(tmp_path):
    path = tmp_path / "record.json"
    prototype._write_json(path, {"value": 1.0})
    with pytest.raises(FileExistsError):
        prototype._write_json(path, {"value": 2.0})
    assert _read_json(path) == {"value": 1.0}
    with pytest.raises(ValueError):
        prototype._write_json(tmp_path / "nonfinite.json", {"value": float("nan")})


@pytest.mark.parametrize("key,value", [("schema_version", "other"), ("case_count", 3)])
def test_changed_manifest_rejected_before_output(fixture_copy, tmp_path, key, value):
    manifest_path = fixture_copy / "manifest.json"
    manifest = _read_json(manifest_path)
    manifest[key] = value
    _rewrite_json(manifest_path, manifest)
    output = tmp_path / "rejected"
    with pytest.raises(ValueError, match="unexpected frozen fixture manifest"):
        prototype.measure_fixtures(fixture_copy, output, "mac")
    assert not output.exists()


@pytest.mark.parametrize("name", prototype.KERNEL_FILES)
def test_kernel_digest_change_rejected_before_output(fixture_copy, tmp_path, name):
    manifest_path = fixture_copy / "manifest.json"
    manifest = _read_json(manifest_path)
    manifest["kernel_sha256"][name] = "0" * 64
    _rewrite_json(manifest_path, manifest)
    output = tmp_path / "rejected"
    with pytest.raises(ValueError, match="kernel bytes differ"):
        prototype.measure_fixtures(fixture_copy, output, "mac")
    assert not output.exists()


@pytest.mark.parametrize("case_index", range(4))
def test_every_fixture_digest_verified_before_any_output(
    fixture_copy, tmp_path, case_index
):
    path = fixture_copy / f"fixture-{case_index}.npz"
    path.write_bytes(path.read_bytes() + b"changed")
    output = tmp_path / "rejected"
    with pytest.raises(ValueError, match="fixture digest differs"):
        prototype.measure_fixtures(fixture_copy, output, "furnace")
    assert not output.exists()


@pytest.mark.parametrize(
    "name", ["../fixture-0.npz", "other.npz", "/tmp/fixture-0.npz"]
)
def test_unexpected_fixture_path_rejected(fixture_copy, tmp_path, name):
    manifest_path = fixture_copy / "manifest.json"
    manifest = _read_json(manifest_path)
    manifest["cases"][0]["file"] = name
    _rewrite_json(manifest_path, manifest)
    output = tmp_path / "rejected"
    with pytest.raises(
        ValueError, match="frozen fixture order or specification differs"
    ):
        prototype.measure_fixtures(fixture_copy, output, "mac")
    assert not output.exists()


@pytest.mark.parametrize(
    "change", ["missing", "extra", "duplicate", "reordered", "spec"]
)
def test_actual_anchor_count_order_and_specs_are_fixed(fixture_copy, tmp_path, change):
    manifest_path = fixture_copy / "manifest.json"
    manifest = _read_json(manifest_path)
    cases = manifest["cases"]
    if change == "missing":
        cases.pop()
    elif change == "extra":
        cases.append(copy.deepcopy(cases[-1]))
    elif change == "duplicate":
        cases[1] = copy.deepcopy(cases[0])
    elif change == "reordered":
        cases[0], cases[1] = cases[1], cases[0]
    else:
        cases[2]["spec"]["seed"] = 123
    _rewrite_json(manifest_path, manifest)
    output = tmp_path / "rejected"
    with pytest.raises(ValueError, match="frozen fixture"):
        prototype.measure_fixtures(fixture_copy, output, "furnace")
    assert not output.exists()


def test_missing_fixture_rejected_without_execution_directory(fixture_copy, tmp_path):
    (fixture_copy / "fixture-3.npz").unlink()
    output = tmp_path / "rejected"
    with pytest.raises(FileNotFoundError):
        prototype.measure_fixtures(fixture_copy, output, "mac")
    assert not output.exists()


def test_measurement_preserves_provenance_and_no_scale_authority(
    measured_hosts, frozen_fixtures
):
    for path in measured_hosts:
        manifest = _read_json(path / "manifest.json")
        assert manifest["host_label"] == path.name
        assert manifest["fixture_manifest_sha256"] == prototype.sha256(
            frozen_fixtures / "manifest.json"
        )
        assert manifest["scope"] == {
            "synthetic_only": True,
            "model_accessed": False,
            "gpu_used": False,
            "large_scale_run": False,
            "scientific_authority": False,
        }
        assert len(manifest["cases"]) == 4
        assert set(manifest["runtime"]) == {
            "system",
            "machine",
            "python",
            "numpy",
            "scipy",
        }
        for record in manifest["cases"]:
            assert record["sha256"] == prototype.sha256(path / record["file"])
            assert record["elapsed_seconds"] >= 0


def test_measurement_refuses_overwriting_execution_artifacts(
    measured_hosts, frozen_fixtures
):
    output = measured_hosts[0]
    digest = prototype.sha256(output / "manifest.json")
    with pytest.raises(FileExistsError):
        prototype.measure_fixtures(frozen_fixtures, output, "mac")
    assert prototype.sha256(output / "manifest.json") == digest


@pytest.mark.parametrize(
    "left,right",
    [
        (True, 1),
        (2, 2.0),
        (None, "None"),
        ([1], (1,)),
        ("eligible", "insufficient"),
        ([1, 2], [1]),
        ({"a": 1}, {"b": 1}),
        ({"sampled_winding": 2}, {"sampled_winding": 3}),
        ([True, False], [True, True]),
    ],
)
def test_discrete_shape_and_type_changes_fail_exactly(left, right):
    assert prototype.compare_values(left, right)


@pytest.mark.parametrize("left,right", [(0.0, 5e-11), (1.0, 1.0 + 1e-10), (2.0, 2.0)])
def test_fixed_float_tolerance_allows_small_roundoff(left, right):
    assert prototype.compare_values(left, right) == []


@pytest.mark.parametrize("left,right", [(0.0, 2e-10), (1.0, 1.0 + 3e-10), (1.0, 1.1)])
def test_float_changes_beyond_tolerance_fail(left, right):
    assert prototype.compare_values(left, right)


@pytest.mark.parametrize(
    "left,right",
    [
        (float("inf"), float("inf")),
        (float("-inf"), float("-inf")),
        (float("nan"), float("nan")),
        (0.0, float("inf")),
        (float("nan"), 0.0),
    ],
)
def test_nonfinite_values_never_pass_parity(left, right):
    assert prototype.compare_values(left, right)


def test_nested_failure_path_is_precise():
    assert prototype.compare_values(
        {"cells": [{"sampled_winding": 2}]},
        {"cells": [{"sampled_winding": -2}]},
    ) == ["root.cells[0].sampled_winding: values differ"]


def test_portable_projection_only_omits_digest_keys_without_mutating_report():
    report = {
        "state": "insufficient",
        "field_sha256": "a" * 64,
        "array": [1, 2.0, False, None],
        "nested": [{"core_sha256": "b" * 64, "candidate_count": None}],
    }
    original = copy.deepcopy(report)
    assert prototype._portable_value(report) == {
        "state": "insufficient",
        "array": [1, 2.0, False, None],
        "nested": [{"candidate_count": None}],
    }
    assert report == original


def test_same_results_pass_without_granting_scale_or_scientific_authority(
    measured_hosts,
):
    report = prototype.compare_hosts(*measured_hosts)
    assert report["status"] == "pass"
    assert report["failures"] == []
    assert report["case_count"] == 4
    assert report["kernel_only_cross_host_parity"] is True
    assert report["gpu_parity"] is False
    assert report["large_scale_authority"] is False
    assert report["scientific_authority"] is False


def test_derived_digest_difference_does_not_break_numerical_parity(measured_hosts):
    _replace_result(
        measured_hosts[1], lambda report: report.update(field_sha256="c" * 64)
    )
    assert prototype.compare_hosts(*measured_hosts)["status"] == "pass"


@pytest.mark.parametrize(
    "change",
    [
        {"state": "insufficient"},
        {"sampled_winding": -2},
        {"sampled_winding": 2.0},
        {"fit_support": [True, True]},
        {"matrix": [[1.0, 0.1], [0.0, 1.0]]},
        {"amplitude": 0.3},
    ],
)
def test_rehashed_but_changed_result_fails_numerical_or_discrete_parity(
    measured_hosts, change
):
    _replace_result(measured_hosts[1], lambda report: report.update(change))
    report = prototype.compare_hosts(*measured_hosts)
    assert report["status"] == "fail"
    assert report["failures"]


def test_result_modified_without_digest_update_is_rejected(measured_hosts):
    _replace_result(
        measured_hosts[1],
        lambda report: report.update(amplitude=0.3),
        update_digest=False,
    )
    with pytest.raises(ValueError, match="execution artifact digest differs"):
        prototype.compare_hosts(*measured_hosts)


@pytest.mark.parametrize(
    "key", ["schema_version", "fixture_manifest_sha256", "kernel_sha256"]
)
def test_cross_host_manifest_identity_differences_fail(measured_hosts, key):
    manifest_path = measured_hosts[1] / "manifest.json"
    manifest = _read_json(manifest_path)
    manifest[key] = {} if key == "kernel_sha256" else "different"
    _rewrite_json(manifest_path, manifest)
    result = prototype.compare_hosts(*measured_hosts)
    assert result["status"] == "fail"
    assert f"manifest.{key}: differs" in result["failures"]


@pytest.mark.parametrize("case_index", range(4))
def test_each_result_is_bound_to_the_same_fixture_across_hosts(
    measured_hosts, case_index
):
    manifest_path = measured_hosts[1] / "manifest.json"
    manifest = _read_json(manifest_path)
    manifest["cases"][case_index]["fixture_sha256"] = "0" * 64
    _rewrite_json(manifest_path, manifest)
    report = prototype.compare_hosts(*measured_hosts)
    assert report["status"] == "fail"
    assert f"case[{case_index}]: fixture digest differs" in report["failures"]


@pytest.mark.parametrize("side", [0, 1])
def test_missing_anchor_manifest_record_fails_closed(measured_hosts, side):
    manifest_path = measured_hosts[side] / "manifest.json"
    manifest = _read_json(manifest_path)
    manifest["cases"].pop()
    _rewrite_json(manifest_path, manifest)
    with pytest.raises(ValueError, match="missing preflight anchor"):
        prototype.compare_hosts(*measured_hosts)


def test_result_filename_cannot_redirect_comparison(measured_hosts):
    manifest_path = measured_hosts[1] / "manifest.json"
    manifest = _read_json(manifest_path)
    manifest["cases"][0]["file"] = "../result-0.json"
    _rewrite_json(manifest_path, manifest)
    with pytest.raises(ValueError, match="execution artifact digest differs"):
        prototype.compare_hosts(*measured_hosts)


def test_missing_result_file_fails_closed(measured_hosts):
    (measured_hosts[1] / "result-3.json").unlink()
    with pytest.raises(FileNotFoundError):
        prototype.compare_hosts(*measured_hosts)


def test_cli_preserves_failed_parity_report_and_returns_nonzero(
    measured_hosts, tmp_path, monkeypatch, capsys
):
    _replace_result(measured_hosts[1], lambda report: report.update(sampled_winding=-2))
    output = tmp_path / "parity.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT_PATH),
            "compare",
            "--left",
            str(measured_hosts[0]),
            "--right",
            str(measured_hosts[1]),
            "--output",
            str(output),
        ],
    )
    assert prototype.main() == 1
    saved = _read_json(output)
    assert saved["status"] == "fail"
    assert saved == json.loads(capsys.readouterr().out)
    digest = prototype.sha256(output)
    with pytest.raises(FileExistsError):
        prototype.main()
    assert prototype.sha256(output) == digest
