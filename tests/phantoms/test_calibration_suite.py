from __future__ import annotations

from spirallens.calibration import run_analytic_calibration


def test_full_analytic_calibration_suite_passes() -> None:
    report = run_analytic_calibration(samples=512)

    report.require_passed()
    assert report.passed
    assert len(report.checks) >= 20
    assert {check.category for check in report.checks} >= {
        "continuous_holonomy",
        "sampled_winding",
        "nested_radius",
        "off_core_control",
        "orientation_reversal",
        "pure_gauge_null",
        "sampling_alias_boundary",
    }
