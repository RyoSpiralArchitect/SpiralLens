from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[1]
PREPARE_SELECTION = REPOSITORY / "scripts" / "prepare_d0_d5_selection.py"
PREPARE_LAUNCH = REPOSITORY / "scripts" / "prepare_d0_d5_launch.py"
RUN_SELECTION = REPOSITORY / "scripts" / "run_d0_d5_selection.py"
SEAL_D6 = REPOSITORY / "scripts" / "seal_d6_surrogate_advancement.py"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _call_names(path: Path) -> tuple[str, ...]:
    tree = ast.parse(_source(path), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            names.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            names.append(node.func.attr)
    return tuple(names)


def test_selection_preparation_has_delayed_seed_supplier_and_no_execution() -> None:
    source = _source(PREPARE_SELECTION)
    calls = _call_names(PREPARE_SELECTION)

    assert "--selection-seed" not in source
    assert calls.count("prepare_closed_d0_d5_selection_protocol") == 1
    assert calls.count("_delayed_selection_seed_supplier") == 1
    for forbidden in (
        "begin_selection_execution",
        "claim_selection_attempt",
        "generate",
        "run_and_publish_calibration_selection",
        "run_calibration_selection",
    ):
        assert forbidden not in calls


def test_launch_preparation_claims_once_but_never_starts_execution() -> None:
    calls = _call_names(PREPARE_LAUNCH)

    assert calls.count("prepare_selection_launch") == 1
    assert calls.count("write_prepared_selection_launch_descriptor") == 1
    for forbidden in (
        "begin_selection_execution",
        "claim_selection_attempt",
        "run_and_publish_calibration_selection",
        "run_calibration_selection",
    ):
        assert forbidden not in calls


def test_fresh_runner_has_no_store_override_and_calls_only_orchestrator_once() -> None:
    source = _source(RUN_SELECTION)
    calls = _call_names(RUN_SELECTION)

    assert "--attempt-store" not in source
    assert "--protocol" not in source
    assert "--freeze" not in source
    assert "--claim-id" not in source
    assert calls.count("load_prepared_selection_launch") == 1
    assert calls.count("run_and_publish_calibration_selection") == 1
    assert calls.count("load_terminal_selection_consumption") == 1
    for forbidden in (
        "begin_selection_execution",
        "claim_selection_attempt",
        "publish_terminal_selection_consumption",
        "run_calibration_selection",
    ):
        assert forbidden not in calls


def test_d6_sealer_is_read_only_on_the_consumed_attempt() -> None:
    source = _source(SEAL_D6)
    calls = _call_names(SEAL_D6)

    assert "--selection-seed" not in source
    assert "--admission-output" not in source
    assert calls.count("publish_scope_limited_d6_decision") == 1
    for forbidden in (
        "begin_selection_execution",
        "build_selection_terminal_binding",
        "claim_selection_attempt",
        "generate",
        "load_committed_selection_terminal",
        "run_and_publish_calibration_selection",
        "run_calibration_selection",
        "write_advancement_artifact",
    ):
        assert forbidden not in calls


@pytest.mark.parametrize(
    "script",
    [PREPARE_SELECTION, PREPARE_LAUNCH, RUN_SELECTION, SEAL_D6],
)
def test_official_script_help_is_side_effect_free(script: Path) -> None:
    completed = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=REPOSITORY,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "usage:" in completed.stdout
