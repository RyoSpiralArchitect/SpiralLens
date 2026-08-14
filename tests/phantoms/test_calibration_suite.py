from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import numpy as np

from spirallens.calibration import run_analytic_calibration


def test_full_analytic_calibration_suite_passes(tmp_path: Path) -> None:
    report = run_analytic_calibration(samples=512)

    expected = (  # noqa: SIM905 - compact exact-order ratchet stays within the test cap
        "winding:q=-2 sampled_winding winding:q=-2:reverse orientation_reversal winding:q=-1 sampled_winding winding:q=-1:reverse orientation_reversal "
        "winding:q=1 sampled_winding winding:q=1:reverse orientation_reversal winding:q=2 sampled_winding winding:q=2:reverse orientation_reversal "
        "winding:off_core off_core_control winding:vortex:nested:r=0.35 nested_radius winding:vortex:nested:r=0.75 nested_radius winding:vortex:nested:r=1.5 nested_radius "
        "winding:alias:q=129:samples=128 sampling_alias_boundary winding:alias:q=129:samples=512 sampling_alias_boundary "
        "holonomy:injected_rotation continuous_holonomy holonomy:injected_rotation:reverse orientation_reversal "
        "holonomy:null:stretch pure_gauge_null holonomy:null:radial_scale pure_gauge_null holonomy:null:non_normal_shear pure_gauge_null holonomy:null:basis_rotation pure_gauge_null "
        "holonomy:connection:nested:r=0.4 nested_radius holonomy:connection:nested:r=0.9 nested_radius holonomy:connection:nested:r=1.6 nested_radius holonomy:connection:off_core off_core_control"
    ).split()
    observed = [
        item for check in report.checks for item in (check.name, check.category)
    ]
    assert (len(report.checks), report.suite_name) == (24, "analytic_phantoms_v0_1")
    assert observed == expected
    assert np.isfinite(
        [(check.observed, check.expected, check.tolerance) for check in report.checks]
    ).all()
    assert all(
        check.passed is (abs(check.observed - check.expected) <= check.tolerance)
        for check in report.checks
    )
    assert report.passed and report.require_passed() is None
    default_root = Path(__file__).resolve().parents[2] / "src"
    expected_root = Path(
        os.environ.get("SPIRALLENS_EXPECTED_IMPORT_ROOT", default_root)
    ).resolve(strict=True)
    numpy_root = Path(np.__file__).resolve(strict=True).parent.parent
    probe = """
import importlib.abc, pathlib, sys
numpy_root, expected_root = [pathlib.Path(item).resolve(strict=True) for item in sys.argv[1:]]
sys.path[:0] = [str(expected_root), str(numpy_root)]; import numpy
assert pathlib.Path(numpy.__file__).resolve().is_relative_to(numpy_root)
blocked = 'torch transformers huggingface_hub safetensors faiss spirallens._repository_context'.split()
class Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == item or fullname.startswith(item + '.') for item in blocked):
            raise ModuleNotFoundError(fullname)
sys.meta_path.insert(0, Blocker())
from spirallens.calibration import run_analytic_calibration; report = run_analytic_calibration(samples=512)
packages = set('spirallens spirallens.calibration spirallens.contracts spirallens.holonomy spirallens.loops spirallens.topology'.split())
definitions = set('spirallens.calibration.phantoms spirallens.calibration.suite spirallens.contracts.calibration spirallens.contracts.math spirallens.holonomy.connection spirallens.holonomy.discrete spirallens.holonomy.metrics spirallens.loops.sampled spirallens.topology.winding'.split())
loaded = {name for name in sys.modules if name.split('.')[0] == 'spirallens'}; assert loaded == packages | definitions
for name in loaded:
    module = sys.modules[name]; path = pathlib.Path(*name.split('.'))
    relative = path / '__init__.py' if name in packages else path.with_suffix('.py')
    expected = (expected_root / relative).resolve(strict=True)
    assert {pathlib.Path(module.__file__).resolve(), pathlib.Path(module.__spec__.origin).resolve()} == {expected}
assert not any(name == item or name.startswith(item + '.') for name in sys.modules for item in blocked); report.require_passed()
"""
    subprocess.run(
        [sys.executable, "-I", "-B", "-c", probe, str(numpy_root), str(expected_root)],
        cwd=tmp_path,
        env={},
        check=True,
    )
