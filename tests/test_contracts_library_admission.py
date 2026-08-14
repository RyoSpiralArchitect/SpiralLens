from __future__ import annotations

import ast
import dataclasses
import importlib
import inspect
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from spirallens import contracts
from spirallens.contracts import calibration, math

# fmt: off
EXPORTS = ["CalibrationCheck", "CalibrationReport", "ContinuousHolonomy", "LoopOrientation", "SampledLoop", "SampledWinding", "WindingEstimate"]
DEFINITIONS = {"CalibrationCheck": calibration, "CalibrationReport": calibration, "ContinuousHolonomy": math, "LoopOrientation": math, "SampledLoop": math, "SampledWinding": math, "WindingEstimate": math}
SIGNATURES = {
    "CalibrationCheck": "(name: 'str', observed: 'float', expected: 'float', tolerance: 'float', passed: 'bool', category: 'str', details: 'Mapping[str, Any]' = <factory>) -> None",
    "CalibrationReport": "(checks: 'tuple[CalibrationCheck, ...]', suite_name: 'str' = 'analytic_phantoms_v0_1') -> None",
    "ContinuousHolonomy": "(matrix: 'NDArray[np.generic]', edge_count: 'int', loop_name: 'str' = 'loop', convention: 'str' = 'column_vectors:left_path_ordered', metadata: 'Mapping[str, Any]' = <factory>) -> None",
    "LoopOrientation": (
        "(value, names=None, *, module=None, qualname=None, type=None, start=1, boundary=None)"
        if sys.version_info < (3, 12)
        else "(*values)"
    ),
    "SampledLoop": "(points: 'NDArray[np.floating]', name: 'str' = 'loop', parameter_values: 'NDArray[np.floating] | None' = None, metadata: 'Mapping[str, Any]' = <factory>) -> None",
    "SampledWinding": "(charge: 'int', estimate: 'WindingEstimate') -> None",
    "WindingEstimate": "(closed_loop_angle_rad: 'float', nearest_integer: 'int', residual_cycles: 'float', minimum_amplitude: 'float', maximum_edge_angle_rad: 'float', sample_count: 'int', reliable: 'bool', failure_reasons: 'tuple[str, ...]' = (), loop_name: 'str' = 'loop') -> None",
}
FIELDS = {
    "CalibrationCheck": ("name", "observed", "expected", "tolerance", "passed", "category", "details"),
    "CalibrationReport": ("checks", "suite_name"),
    "ContinuousHolonomy": ("matrix", "edge_count", "loop_name", "convention", "metadata"),
    "SampledLoop": ("points", "name", "parameter_values", "metadata"),
    "SampledWinding": ("charge", "estimate"),
    "WindingEstimate": ("closed_loop_angle_rad", "nearest_integer", "residual_cycles", "minimum_amplitude", "maximum_edge_angle_rad", "sample_count", "reliable", "failure_reasons", "loop_name"),
}

def _check(**overrides: object) -> contracts.CalibrationCheck:
    values = {"name": "check", "observed": 2.0, "expected": 1.0, "tolerance": 1.0, "passed": True, "category": "unit"}
    values.update(overrides)
    return contracts.CalibrationCheck(**values)

def _loop(**overrides: object) -> contracts.SampledLoop:
    values = {"points": np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])}
    values.update(overrides)
    return contracts.SampledLoop(**values)

def _holonomy(**overrides: object) -> contracts.ContinuousHolonomy:
    values = {"matrix": np.eye(2), "edge_count": 3}
    values.update(overrides)
    return contracts.ContinuousHolonomy(**values)

def _estimate(**overrides: object) -> contracts.WindingEstimate:
    values = {"closed_loop_angle_rad": 2 * np.pi, "nearest_integer": 1, "residual_cycles": 0.0, "minimum_amplitude": 1.0, "maximum_edge_angle_rad": 0.2, "sample_count": 8, "reliable": True}
    values.update(overrides)
    return contracts.WindingEstimate(**values)
def test_exact_provisional_namespace_surface() -> None:
    default_root = Path(__file__).resolve().parents[1] / "src"
    expected_root = Path(
        os.environ.get("SPIRALLENS_EXPECTED_IMPORT_ROOT", default_root)
    ).resolve(strict=True)
    expected_modules = {
        sys.modules["spirallens"]: "spirallens/__init__.py",
        contracts: "spirallens/contracts/__init__.py",
        calibration: "spirallens/contracts/calibration.py",
        math: "spirallens/contracts/math.py",
    }
    for module, relative in expected_modules.items():
        expected = (expected_root / relative).resolve(strict=True)
        assert Path(module.__file__).resolve(strict=True) == expected
        assert Path(module.__spec__.origin).resolve(strict=True) == expected
    for name, module in sys.modules.items():
        if name == "spirallens" or name.startswith("spirallens."):
            for origin in (module.__file__, module.__spec__.origin):
                assert Path(origin).resolve(strict=True).is_relative_to(expected_root)
    assert contracts.__all__ == EXPORTS
    for name, defining_module in DEFINITIONS.items():
        value = getattr(contracts, name)
        assert value is getattr(defining_module, name)
        assert value.__module__ == defining_module.__name__
        assert str(inspect.signature(value)) == SIGNATURES[name]
    for name, expected_fields in FIELDS.items():
        value = getattr(contracts, name)
        assert tuple(field.name for field in dataclasses.fields(value)) == expected_fields
        assert value.__dataclass_params__.frozen is True
        assert "__dict__" not in value.__slots__
    assert tuple(contracts.LoopOrientation) == (contracts.LoopOrientation.COUNTERCLOCKWISE, contracts.LoopOrientation.CLOCKWISE)
    assert [item.sign for item in contracts.LoopOrientation] == [1, -1]


def test_manifest_and_exact_production_consumer_namespaces_join() -> None:
    repository = Path(contracts.__file__).parents[3]
    manifest = json.loads((repository / "distribution/spirallens_ordered_exports_v0_1.json").read_bytes())
    rows = [row for row in manifest["packages"] if row["module"] == "spirallens.contracts"]
    assert rows == [{"module": "spirallens.contracts", "initializer": "spirallens/contracts/__init__.py", "exports": EXPORTS}]
    expected_by_file = {
        "calibration/phantoms.py": ("SampledLoop",),
        "calibration/suite.py": ("CalibrationCheck", "CalibrationReport"),
        "holonomy/connection.py": ("ContinuousHolonomy", "SampledLoop"),
        "holonomy/discrete.py": ("ContinuousHolonomy",),
        "holonomy/metrics.py": ("ContinuousHolonomy",),
        "loops/sampled.py": ("LoopOrientation", "SampledLoop"),
        "topology/winding.py": ("SampledLoop", "SampledWinding", "WindingEstimate"),
    }
    members = json.loads((repository / "distribution/spirallens_python_members_v0_1.json").read_bytes())
    assert {f"spirallens/{relative}" for relative in expected_by_file} <= set(members["roles"]["shipped_runtime"])
    expected_by_name = {
        name: {f"spirallens.{module}" for module in modules.split()}
        for name, modules in {
            "CalibrationCheck": "calibration.suite",
            "CalibrationReport": "calibration.suite",
            "ContinuousHolonomy": "holonomy.connection holonomy.discrete holonomy.metrics",
            "LoopOrientation": "loops.sampled",
            "SampledLoop": "calibration.phantoms holonomy.connection loops.sampled topology.winding",
            "SampledWinding": "topology.winding",
            "WindingEstimate": "topology.winding",
        }.items()
    }
    observed_by_file, observed_by_name = {}, {name: set() for name in EXPORTS}
    trees_by_file, package_root = {}, repository / "src" / "spirallens"
    for path in package_root.rglob("*.py"):
        relative = path.relative_to(package_root).as_posix()
        trees_by_file[relative] = tree = ast.parse(path.read_bytes())
        assert not any(
            isinstance(node, ast.Import) and any(alias.name == "spirallens.contracts" for alias in node.names)
            or isinstance(node, ast.ImportFrom)
            and (
                (node.level, node.module) == (0, "spirallens") and any(alias.name == "contracts" for alias in node.names)
                or node.level == relative.count("/") + 1 and node.module == "contracts"
                or node.level == relative.count("/") + 1 and node.module is None and any(alias.name == "contracts" for alias in node.names)
            )
            for node in ast.walk(tree)
        )
        imports = [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module == "spirallens.contracts"]
        if not imports:
            continue
        assert len(imports) == 1
        aliases = imports[0].names
        assert all(alias.asname is None and alias.name in EXPORTS for alias in aliases)
        observed_by_file[relative] = names = tuple(alias.name for alias in aliases)
        module_name = "spirallens." + relative.removesuffix(".py").replace("/", ".")
        for name in names:
            observed_by_name[name].add(module_name)
    assert (observed_by_file, observed_by_name) == (expected_by_file, expected_by_name)
    def calls(relative: str, name: str) -> list[ast.Call]:
        return [
            node
            for node in ast.walk(trees_by_file[relative])
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == name
        ]
    assert calls("holonomy/discrete.py", "ContinuousHolonomy")
    assert not calls("holonomy/connection.py", "ContinuousHolonomy")
    assert calls("loops/sampled.py", "SampledLoop")
    assert any(
        len(call.args) > 1 and getattr(call.args[1], "id", None) == "ContinuousHolonomy"
        for call in calls("holonomy/metrics.py", "isinstance")
    )
    def loop_attrs(relative: str) -> set[str]:
        return {
            node.attr
            for node in ast.walk(trees_by_file[relative])
            if isinstance(node, ast.Attribute) and getattr(node.value, "id", None) == "loop"
        }
    assert loop_attrs("holonomy/connection.py") == loop_attrs("topology/winding.py") | {"ambient_dimension"}
    assert loop_attrs("topology/winding.py") == {"name", "points", "vertex_count"}
    # Direct-import module membership is not a consumer-independence decision.
    for relative, names in expected_by_file.items():
        module_name = "spirallens." + relative.removesuffix(".py").replace("/", ".")
        module = importlib.import_module(module_name)
        for name in names:
            assert getattr(module, name) is getattr(contracts, name)


def test_representative_value_behavior_is_copied_and_read_only() -> None:
    details = {"source": "fixture"}
    good, bad = _check(details=details), _check(name="bad", passed=False)
    details["source"] = "mutated"
    assert good.absolute_error == 1.0 and good.details == {"source": "fixture"}
    assert contracts.CalibrationReport((good,)).require_passed() is None
    report = contracts.CalibrationReport((good, bad))
    assert not report.passed and report.failed == (bad,)
    with pytest.raises(RuntimeError, match="^analytic calibration failed: bad$"):
        report.require_passed()
    source = np.array([[0.0, 0.0], [3.0, 0.0], [0.0, 4.0]])
    parameters = np.array([0.0, 0.25, 0.75])
    loop = contracts.SampledLoop(source, parameter_values=parameters, metadata={"role": "fixture"})
    source[0], parameters[0] = 99.0, 99.0
    assert (loop.vertex_count, loop.ambient_dimension, loop.perimeter) == (3, 2, 12.0)
    np.testing.assert_array_equal(loop.parameter_values, [0.0, 0.25, 0.75])
    assert not loop.points.flags.writeable and not loop.parameter_values.flags.writeable
    default = _loop()
    np.testing.assert_array_equal(default.parameter_values, np.arange(3) / 3)
    assert not default.parameter_values.flags.writeable
    with pytest.raises(ValueError, match="assignment destination is read-only"):
        default.parameter_values[0] = 1.0
    holonomy = _holonomy(metadata={"role": "fixture"})
    assert holonomy.fiber_dimension == 2 and holonomy.identity_deviation_fro == 0.0
    assert holonomy.determinant == 1 + 0j and not holonomy.matrix.flags.writeable
    estimate = _estimate(loop_name="fixture")
    assert estimate.cycles == 1.0 and contracts.SampledWinding(1, estimate).loop_name == "fixture"
    with pytest.raises(dataclasses.FrozenInstanceError):
        good.name = "changed"


FAILURES = [
    (lambda: _check(name=" ", observed=np.nan), ValueError, "calibration name and category must not be empty"),
    (lambda: _check(category=" ", observed=np.nan), ValueError, "calibration name and category must not be empty"),
    (lambda: _check(observed=np.nan, tolerance=-1.0), ValueError, "calibration scalar values must be finite"),
    (lambda: _check(expected=np.inf), ValueError, "calibration scalar values must be finite"),
    (lambda: _check(tolerance=-1.0), ValueError, "calibration tolerance must be non-negative"),
    (lambda: contracts.CalibrationReport((), " "), ValueError, "calibration report must contain at least one check"),
    (lambda: contracts.CalibrationReport((_check(),), " "), ValueError, "suite_name must not be empty"),
    (lambda: _loop(points=np.zeros(3), name=" "), ValueError, "points must have 2 dimensions, got 1"),
    (lambda: _loop(points=np.ones((3, 2), dtype=complex)), ValueError, "points must be real-valued"),
    (lambda: _loop(points=np.full((3, 2), "x")), TypeError, "points must be numeric"),
    (lambda: _loop(points=np.array([[0.0, 0.0], [1.0, np.nan], [0.0, 1.0]])), ValueError, "points must contain only finite values"),
    (lambda: _loop(points=np.zeros((2, 1)), name=" "), ValueError, "a sampled loop requires at least three vertices"),
    (lambda: _loop(points=np.arange(3.0)[:, None], name=" "), ValueError, "a sampled loop requires ambient dimension >= 2"),
    (lambda: _loop(name=" ", parameter_values=np.zeros((3, 1))), ValueError, "loop name must not be empty"),
    (lambda: _loop(points=np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 0.0]]), parameter_values=np.zeros((3, 1))), ValueError, "loop contains a zero-length edge; do not duplicate the endpoint"),
    (lambda: _loop(parameter_values=np.zeros((3, 1))), ValueError, "parameter_values must have 1 dimensions, got 2"),
    (lambda: _loop(parameter_values=np.ones(3, dtype=complex)), ValueError, "parameter_values must be real-valued"),
    (lambda: _loop(parameter_values=np.full(3, "x")), TypeError, "parameter_values must be numeric"),
    (lambda: _loop(parameter_values=np.array([0.0, np.nan, 1.0])), ValueError, "parameter_values must contain only finite values"),
    (lambda: _loop(parameter_values=np.arange(4.0)), ValueError, "parameter_values must contain one value per loop vertex"),
    (lambda: _loop(parameter_values=np.array([0.0, 0.5, 0.4])), ValueError, "parameter_values must be strictly increasing"),
    (lambda: _holonomy(matrix=np.ones(2), edge_count=0), ValueError, "matrix must have 2 dimensions, got 1"),
    (lambda: _holonomy(matrix=np.full((2, 2), "x")), TypeError, "matrix must be numeric"),
    (lambda: _holonomy(matrix=np.array([[1.0, np.nan], [0.0, 1.0]])), ValueError, "matrix must contain only finite values"),
    (lambda: _holonomy(matrix=np.ones((2, 3)), edge_count=0), ValueError, "holonomy matrix must be non-empty and square"),
    (lambda: _holonomy(matrix=np.empty((0, 0)), edge_count=0), ValueError, "holonomy matrix must be non-empty and square"),
    (lambda: _holonomy(edge_count=0, loop_name=" "), ValueError, "edge_count must be positive"),
    (lambda: _holonomy(loop_name=" ", convention=" "), ValueError, "loop_name must not be empty"),
    (lambda: _holonomy(convention=" "), ValueError, "convention must not be empty"),
    (lambda: _estimate(closed_loop_angle_rad=np.nan, sample_count=2), ValueError, "winding diagnostics must be finite"),
    (lambda: _estimate(sample_count=2, minimum_amplitude=-1.0), ValueError, "sample_count must be at least three"),
    (lambda: _estimate(minimum_amplitude=-1.0, maximum_edge_angle_rad=-1.0), ValueError, "minimum_amplitude must be non-negative"),
    (lambda: _estimate(maximum_edge_angle_rad=-1.0, residual_cycles=0.5), ValueError, "maximum_edge_angle_rad must be non-negative"),
    (lambda: _estimate(residual_cycles=0.5, failure_reasons=("later",)), ValueError, "residual_cycles is inconsistent with the angle"),
    (lambda: _estimate(failure_reasons=("unexpected",)), ValueError, "a reliable estimate cannot have failure reasons"),
    (lambda: _estimate(reliable=False), ValueError, "an unreliable estimate must explain why"),
    (lambda: contracts.SampledWinding(2, _estimate(reliable=False, failure_reasons=("gate",))), ValueError, "cannot construct SampledWinding from unreliable estimate"),
    (lambda: contracts.SampledWinding(2, _estimate()), ValueError, "charge must match estimate.nearest_integer"),
]
# fmt: on


@pytest.mark.parametrize(("factory", "exception", "message"), FAILURES)
def test_constructor_failures_and_validation_order(factory, exception, message) -> None:
    with pytest.raises(exception) as caught:
        factory()
    assert type(caught.value) is exception
    assert str(caught.value) == message
    assert caught.value.__cause__ is caught.value.__context__ is None


def test_isolated_import_needs_no_model_repository_or_external_action(tmp_path) -> None:
    source_root = str(Path(contracts.__file__).parents[2])
    numpy_root = str(Path(np.__file__).resolve().parent.parent)
    probe = f"""
import importlib.abc, pathlib, sys
sys.path[:0] = [sys.argv[2], sys.argv[1]]
import numpy
assert pathlib.Path(numpy.__file__).resolve().is_relative_to(pathlib.Path(sys.argv[1]).resolve())
blocked = ('torch', 'transformers', 'huggingface_hub', 'safetensors', 'faiss', 'spirallens._repository_context')
class Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == item or fullname.startswith(item + '.') for item in blocked):
            raise ModuleNotFoundError(fullname)
sys.meta_path.insert(0, Blocker())
def audit(event, args):
    write = event == 'open' and isinstance(args[1], str) and any(flag in args[1] for flag in 'wax+')
    if write or event.startswith(('socket.', 'subprocess.')) or event in {{'os.system', 'os.putenv', 'os.unsetenv'}}:
        raise RuntimeError(event)
sys.addaudithook(audit)
import spirallens.contracts as candidate
assert pathlib.Path(candidate.__file__).resolve().is_relative_to(pathlib.Path(sys.argv[2]).resolve())
assert candidate.__all__ == {EXPORTS!r}
assert not any(any(name == item or name.startswith(item + '.') for item in blocked) for name in sys.modules)
"""
    subprocess.run(
        [sys.executable, "-I", "-B", "-c", probe, numpy_root, source_root],
        cwd=tmp_path,
        env={},
        check=True,
        capture_output=True,
        text=True,
    )
