"""Sampled-point reference perturbations in a shared 2D coefficient frame.

Pure NumPy diagnostics: no file access, fitting, resampling, winding admission,
or predecessor imports. F4 angles are spin-two coefficient phases, not halved
physical director angles. The reference segment is algebraic interpolation,
not a new observation or a certificate about continuous spatial topology.
"""

from __future__ import annotations

import numpy as np


SCHEMA = "spirallens.p4-reference-perturbation-points.v0.1"
DEFAULT_AMPLITUDE_FLOOR = 1e-6


def _inputs(residual_a, residual_b, support, amplitude_floor):
    for values in (residual_a, residual_b):
        if (
            not isinstance(values, np.ndarray)
            or values.ndim != 2
            or values.shape[1] != 2
            or values.dtype.kind not in "fiu"
            or not np.isfinite(values).all()
        ):
            raise ValueError(
                "finite real numeric NumPy arrays with shape (N,2) required"
            )
    if residual_a.shape != residual_b.shape:
        raise ValueError("residual A/B shapes must match")
    if (
        not isinstance(support, np.ndarray)
        or support.dtype != np.bool_
        or support.shape != (len(residual_a),)
    ):
        raise ValueError("support must be a boolean NumPy array with shape (N,)")
    if isinstance(amplitude_floor, (bool, np.bool_)) or not isinstance(
        amplitude_floor, (int, float, np.integer, np.floating)
    ):
        raise ValueError("amplitude_floor must be a finite positive real scalar")
    try:
        floor = float(amplitude_floor)
    except (OverflowError, ValueError) as exc:
        raise ValueError("amplitude_floor must be finite and positive") from exc
    if not np.isfinite(floor) or floor <= 0:
        raise ValueError("amplitude_floor must be finite and positive")
    with np.errstate(over="ignore", invalid="ignore"):
        a = np.asarray(residual_a, dtype=np.float64)
        b = np.asarray(residual_b, dtype=np.float64)
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("residuals must be representable as finite float64 values")
    return a, b, support, floor


def _fixed_summary(values):
    ordered = np.sort(values)
    count = len(ordered)
    if not count:
        return dict(count=0, min=None, q25=None, median=None, q75=None, max=None)

    def percentile(q):
        location = (count - 1) * q
        lower = int(np.floor(location))
        upper = int(np.ceil(location))
        fraction = location - lower
        # Weighted endpoints avoid overflow from (upper-lower) when the two
        # finite values have large opposite signs. This is linear quantiling.
        return float((1 - fraction) * ordered[lower] + fraction * ordered[upper])

    return {
        "count": count,
        "min": float(ordered[0]),
        "q25": percentile(0.25),
        "median": percentile(0.5),
        "q75": percentile(0.75),
        "max": float(ordered[-1]),
    }


def point_diagnostics(
    residual_a,
    residual_b,
    support,
    *,
    amplitude_floor=DEFAULT_AMPLITUDE_FLOOR,
):
    """Return JSON-ready point series, reasons, fixed summaries, and counts.

    Unsupported points have null values in every series. Small amplitudes
    retain amplitude/segment diagnostics but never gain a direction by an
    epsilon replacement. Nonrepresentable derived quantities remain null with
    a numerical reason. Empty (0,2) inputs are allowed and preserve zero counts.
    Endpoint slopes use the same forward perturbation d=rB-rA at both ends.
    """
    ra, rb, supported, floor = _inputs(residual_a, residual_b, support, amplitude_floor)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore", under="ignore"):
        d = rb - ra
        amplitude_a = np.hypot(ra[:, 0], ra[:, 1])
        amplitude_b = np.hypot(rb[:, 0], rb[:, 1])
        perturbation = np.hypot(d[:, 0], d[:, 1])
        defined_a = supported & np.isfinite(amplitude_a) & (amplitude_a > floor)
        defined_b = supported & np.isfinite(amplitude_b) & (amplitude_b > floor)
        both = defined_a & defined_b
        unit_a = np.zeros_like(ra)
        unit_b = np.zeros_like(rb)
        unit_a[defined_a] = ra[defined_a] / amplitude_a[defined_a, None]
        unit_b[defined_b] = rb[defined_b] / amplitude_b[defined_b, None]
        radial_a = np.sum(unit_a * d, axis=1)
        transverse_a = unit_a[:, 0] * d[:, 1] - unit_a[:, 1] * d[:, 0]
        transverse_b = unit_b[:, 0] * d[:, 1] - unit_b[:, 1] * d[:, 0]
        signed_angle = np.arctan2(
            unit_a[:, 0] * unit_b[:, 1] - unit_a[:, 1] * unit_b[:, 0],
            np.sum(unit_a * unit_b, axis=1),
        )

        closest = np.full(len(ra), np.nan)
        zero_perturbation = np.isfinite(perturbation) & (perturbation == 0)
        nonzero_perturbation = np.isfinite(perturbation) & (perturbation > 0)
        closest[zero_perturbation] = 0.0
        # The normalized form equals -dot(rA,d)/D^2 without squaring D or
        # multiplying two large vectors. No denominator floor is substituted.
        q = nonzero_perturbation
        projected = (
            -np.sum(ra[q] * (d[q] / perturbation[q, None]), axis=1) / perturbation[q]
        )
        closest[q] = np.clip(projected, 0.0, 1.0)
        segment_point = (1 - closest[:, None]) * ra + closest[:, None] * rb
        minimum_segment = np.hypot(segment_point[:, 0], segment_point[:, 1])
        minimum_endpoint = np.minimum(amplitude_a, amplitude_b)

        metric_values = {
            "amplitude_A": amplitude_a,
            "amplitude_B": amplitude_b,
            "perturbation_norm": perturbation,
            "amplitude_change": amplitude_b - amplitude_a,
            "relative_to_A": perturbation / amplitude_a,
            "relative_to_B": perturbation / amplitude_b,
            "symmetric_relative": perturbation / minimum_endpoint,
            "signed_angle_rad": signed_angle,
            "absolute_angle_rad": np.abs(signed_angle),
            "radial_A": radial_a,
            "transverse_A": transverse_a,
            "angular_slope_at_A": transverse_a / amplitude_a,
            "angular_slope_at_B": transverse_b / amplitude_b,
            "closest_lambda": closest,
            "minimum_segment_amplitude": minimum_segment,
            "segment_to_endpoint_ratio": minimum_segment / minimum_endpoint,
        }

    a_metrics = {"relative_to_A", "radial_A", "transverse_A", "angular_slope_at_A"}
    b_metrics = {"relative_to_B", "angular_slope_at_B"}
    both_metrics = {
        "symmetric_relative",
        "signed_angle_rad",
        "absolute_angle_rad",
        "segment_to_endpoint_ratio",
    }
    points, reasons, summary = {}, {}, {}
    for name, values in metric_values.items():
        needs_a = name in a_metrics or name in both_metrics
        needs_b = name in b_metrics or name in both_metrics
        admitted = supported.copy()
        if needs_a:
            admitted &= defined_a
        if needs_b:
            admitted &= defined_b
        finite = np.isfinite(values)
        valid = admitted & finite
        series, failures = [], []
        for i in range(len(values)):
            if valid[i]:
                series.append(float(values[i]))
                failures.append(None)
                continue
            series.append(None)
            if not supported[i]:
                failures.append("unsupported_point")
                continue
            causes = []
            for required, defined, amplitude, arm in (
                (needs_a, defined_a, amplitude_a, "A"),
                (needs_b, defined_b, amplitude_b, "B"),
            ):
                if required and not defined[i]:
                    causes.append(
                        f"amplitude_{arm}_at_or_below_floor"
                        if np.isfinite(amplitude[i])
                        else f"amplitude_{arm}_nonfinite"
                    )
            if not causes:
                causes.append("nonfinite_derived_value")
            failures.append(";".join(causes))
        points[name] = series
        reasons[name] = failures
        summary[name] = _fixed_summary(values[valid])

    count = int(supported.sum())
    return {
        "schema_version": SCHEMA,
        "amplitude_floor": floor,
        "support": supported.tolist(),
        "support_status": (
            "unavailable"
            if count == 0
            else "complete"
            if count == len(ra)
            else "incomplete"
        ),
        "points": points,
        "reasons": reasons,
        "summary": summary,
        "counts": {
            "total": len(ra),
            "supported": count,
            "unsupported": len(ra) - count,
            "direction_A_defined": int(defined_a.sum()),
            "direction_B_defined": int(defined_b.sum()),
            "both_directions_defined": int(both.sum()),
            "closest_at_or_below_floor": int(
                (
                    supported
                    & np.isfinite(minimum_segment)
                    & (minimum_segment <= floor)
                ).sum()
            ),
            "closest_amplitude_defined": summary["minimum_segment_amplitude"]["count"],
        },
        "conventions": {
            "perturbation": "d=residual_B-residual_A",
            "endpoint_slope_direction": "same-forward-d-at-A-and-B",
            "angle": "principal-atan2-coefficient-space; antipodal-pi-sign-is-branch-dependent",
            "F4_angle": "spin-two-coefficient-phase-not-physical-director-angle; not halved",
            "segment": "fixed-algebraic-reference-interpolation; not new observations",
            "summary_quantiles": "linear interpolation at 0.25,0.5,0.75",
            "undefined_values": "null; no amplitude-floor replacement or ratio clipping",
        },
        "scope": {
            "sampled_points_only": True,
            "selection_performed": False,
            "new_threshold_fitted": False,
            "winding_recomputed": False,
            "scientific_authority": False,
            "continuous_topology_established": False,
            "probability_calibrated": False,
        },
    }
