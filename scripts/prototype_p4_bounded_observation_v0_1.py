"""Conditional quadratic outer bounds with explicit moment-space error budgets.

No fixture truth, ideal reference, or learned error threshold enters inference.
The predecessor reader and its historical observations are not modified.
"""

from __future__ import annotations

import json

import numpy as np

import p4_bounded_reference_v0_1 as witness
import prototype_p4_center_identifiability_v0_1 as base
from spirallens.core.canonical import canonical_json_bytes

spatial = base.spatial
HASH, SEAL = base.HASH, base.SEAL
SCHEMA = "spirallens.p4-bounded-observation.v0.1"
NUM = 1e-12
SUPPORT = np.concatenate((base.FIT, base.HELDOUT))


def finite(value, shape):
    raw = np.asarray(value)
    if raw.dtype.kind not in "fiu" or any(
        isinstance(v, (bool, np.bool_)) for v in np.asarray(value, dtype=object).flat
    ):
        raise ValueError("real numeric arrays without booleans required")
    result = np.array(value, dtype=np.float64, copy=True)
    if result.shape != shape or not np.isfinite(result).all():
        raise ValueError(f"finite array of shape {shape} required")
    result[result == 0] = 0.0
    return result


def json_values(value):
    """Normalize computed signed zero, without coercing booleans or missingness."""
    if type(value) is float and value == 0:
        return 0.0
    if type(value) is list:
        return [json_values(v) for v in value]
    if type(value) is dict:
        return {k: json_values(v) for k, v in value.items()}
    return value


def polynomial_fit(residual, observation_bounds):
    """Triangle propagation of pointwise norm bounds; no independence needed."""
    residual = finite(residual, (25, 2))
    eps = finite(observation_bounds, (25,))
    if np.any(eps < 0):
        raise ValueError("nonnegative moment-space bounds required")
    qf, qv = base.design(base.FIT), base.design(base.HELDOUT)
    inverse = np.linalg.pinv(qf)
    coefficients = inverse @ residual[:9]
    radii = np.abs(inverse) @ eps[:9] + NUM
    prediction = qv @ coefficients
    errors = np.linalg.norm(prediction - residual[9:], axis=1)
    limits = eps[9:] + np.abs(qv @ inverse) @ eps[:9] + NUM
    return coefficients, radii, errors, limits


def infer(measured_field, reference, reference_budget, observation_bounds):
    """Only measured moments and declared contracts; roots are family-conditional."""
    measured_field = finite(measured_field, (25, 2))
    reference = finite(reference, (3, 2))
    witness.validate_budget(reference_budget, reference)
    residual = spatial.subtract(measured_field, SUPPORT, reference)
    fitted, noise_radii, errors, limits = polynomial_fit(residual, observation_bounds)
    c, bx, by, qxx, qxy, qyy = spatial.complex_values(fitted)
    A = (qxx - qyy - 1j * qxy) / 4
    B = (qxx - qyy + 1j * qxy) / 4
    C = (qxx + qyy) / 2
    rA = float((noise_radii[3] + noise_radii[4] + noise_radii[5]) / 4)
    rC = float((noise_radii[3] + noise_radii[5]) / 2)
    body = {
        "schema_version": SCHEMA + ".readout",
        "input_sha256": HASH(measured_field),
        "coords_sha256": HASH(SUPPORT),
        "reference_sha256": HASH(reference),
        "reference_budget_seal_sha256": reference_budget["budget_seal_sha256"],
        "observation_bounds": np.asarray(observation_bounds).tolist(),
        "noise_location": "post-adapter-moment-space",
        "polynomial_coefficients": fitted.tolist(),
        "coefficient_noise_radii": noise_radii.tolist(),
        "coefficient_radii": None,
        "heldout_errors": errors.tolist(),
        "heldout_limits": limits.tolist(),
        "heldout_compatible": bool(np.all(errors <= limits)),
        "curvature": {"A": base.cv(A), "B": base.cv(B), "C": base.cv(C)},
        "curvature_radii": {"A": rA, "B": rA, "C": rC},
        "numerical_allowance": NUM,
        "scope": "bounded-witness-and-moment-error-conditional-quadratic",
        "global_family_verified": False,
        "calibrated_confidence_region": False,
        "scientific_authority": False,
        "status": None,
        "reason": None,
        "orientation": None,
        "center": None,
        "center_radius": None,
        "discriminant": None,
        "discriminant_radius": None,
        "separation_lower": None,
        "separation_upper": None,
        "estimated_roots": None,
        "root_radius": None,
        "root_regions_disjoint": None,
    }

    def finish(status, reason):
        body.update(status=status, reason=reason)
        clean = json_values(body)
        json.dumps(clean, allow_nan=False)
        return {**clean, "readout_seal_sha256": SEAL(clean)}

    if reference_budget["radii"] is None:
        return finish("common_mode_unidentified", "no-independently-bounded-witness")
    radii = noise_radii.copy()
    radii[:3] += finite(reference_budget["radii"], (3,))
    body["coefficient_radii"] = radii.tolist()
    if not body["heldout_compatible"]:
        return finish("observation_model_mismatch", "heldout-family-or-error-contract")
    if abs(A) <= rA and abs(B) <= rA and abs(C) <= rC:
        zero_possible = bool(np.all(np.linalg.norm(fitted, axis=1) <= radii))
        return finish(
            "zero_not_excluded" if zero_possible else "curvature_unresolved",
            "zero-inside-coefficient-outer-disks"
            if zero_possible
            else "active-curvature-not-separated-from-zero",
        )
    rL = float((radii[1] + radii[2]) / 2)
    alternatives = []
    for orientation, active, inactive, L, M in (
        ("holomorphic", A, B, (bx - 1j * by) / 2, (bx + 1j * by) / 2),
        ("antiholomorphic", B, A, (bx + 1j * by) / 2, (bx - 1j * by) / 2),
    ):
        if abs(inactive) <= rA and abs(C) <= rC and abs(M) <= rL:
            alternatives.append((orientation, active, L, M))
    if not alternatives:
        return finish("out_of_family", "curvature-or-inactive-linear-incompatible")
    if len(alternatives) != 1 or abs(alternatives[0][1]) - rA <= spatial.FLOOR:
        return finish("curvature_unresolved", "orientation-or-denominator-unresolved")
    orientation, a, L, M = alternatives[0]
    m = -L / (2 * a)
    D = m * m - c / a
    rm = (rL + 2 * abs(m) * rA) / (2 * (abs(a) - rA))
    rd = 2 * abs(m) * rm + rm * rm + (radii[0] + abs(c / a) * rA) / (abs(a) - rA)
    lower = 2 * np.sqrt(max(0.0, abs(D) - rd))
    upper = 2 * np.sqrt(abs(D) + rd)
    root_radius = rm + np.sqrt(rd)
    positions = [m + np.sqrt(D), m - np.sqrt(D)]
    physical_center = m
    if orientation == "antiholomorphic":
        physical_center = np.conj(m)
        positions = [np.conj(p) for p in positions]
    body.update(
        orientation=orientation,
        active_a=base.cv(a),
        active_L=base.cv(L),
        inactive_M=base.cv(M),
        inactive_linear_radius=rL,
        center=base.cv(physical_center),
        center_radius=float(rm),
        discriminant=base.cv(D),
        discriminant_radius=float(rd),
        separation_lower=float(lower),
        separation_upper=float(upper),
        estimated_roots=[base.cv(p) for p in positions],
        root_radius=float(root_radius),
        root_regions_disjoint=bool(abs(positions[0] - positions[1]) > 2 * root_radius),
    )
    return finish(
        "two_required_in_family" if lower > 0 else "one_not_excluded",
        "zero-discriminant-excluded" if lower > 0 else "zero-discriminant-not-excluded",
    )


def verify_readout(
    report, measured_field, reference, reference_budget, observation_bounds
):
    expected = infer(measured_field, reference, reference_budget, observation_bounds)
    if type(report) is not dict or canonical_json_bytes(report) != canonical_json_bytes(
        expected
    ):
        raise ValueError("bounded readout does not replay")
    return True
