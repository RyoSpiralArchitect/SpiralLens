"""Conditional affine-reference budgets from a separately declared witness.

There is no truth/oracle input and no correction of either observed channel.
``witness_independent`` declares a synthetic assumption; this helper cannot
verify physical independence or exclude bias shared by the two channels.
The rowwise triangle bound adds a fixed 1e-12 numerical margin. It is neither
an empirical interval nor calibrated confidence nor a general roundoff proof.
"""

from __future__ import annotations

import numpy as np

from spirallens.core import canonical_json_sha256 as SEAL
from spirallens.core.canonical import canonical_json_bytes
from spirallens.graphs.common import array_sha256 as HASH

SCHEMA = "spirallens.p4-bounded-reference.v0.1"
WITNESS_SCHEMA = "spirallens.p4-affine-witness.v0.1"
NUMERICAL_MARGIN = 1e-12
PLACEMENT_RADII = (0.5, 1.0)


def _array(values, shape, label, *, nonnegative=False):
    try:
        raw = np.asarray(values)
        objects = np.asarray(values, dtype=object)
        if raw.dtype.kind not in "fiu" or any(
            isinstance(v, (bool, np.bool_)) for v in objects.flat
        ):
            raise ValueError("real numeric values without booleans required")
        result = np.array(raw, dtype=np.float64, copy=True)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{label}: finite real array required") from error
    if result.shape != shape or not np.isfinite(result).all():
        raise ValueError(f"{label}: finite shape {shape} required")
    if nonnegative and np.any(result < 0):
        raise ValueError(f"{label}: nonnegative bounds required")
    # Canonical JSON forbids negative zero; normalize only on this owned copy.
    result[result == 0] = 0.0
    return result


def _scope():
    return {
        "scope": "synthetic-conditional",
        "scientific_authority": False,
        "empirical_confidence": False,
        "calibrated_confidence": False,
        "physical_independence_verified": False,
    }


def reference_budget(
    reference,
    witness=None,
    witness_radii=None,
    *,
    witness_independent=False,
    witness_id=None,
):
    """Seal a bound conditional on a declared bounded, distinct witness.

    A missing/unbounded/nonindependent witness returns ``radii=None``. Supplying
    metadata for an absent witness, or declaring independence without a witness
    identifier, is inconsistent and rejected. The identifier is a declaration,
    not proof of provenance. A bounded witness must itself bound every common
    error affecting that witness; small channel disagreement cannot prove this.
    """
    reference = _array(reference, (3, 2), "reference")
    if type(witness_independent) is not bool:
        raise ValueError("witness_independent must be a genuine boolean")
    if witness_id is not None and (
        type(witness_id) is not str
        or not witness_id.strip()
        or witness_id != witness_id.strip()
        or any(ord(char) < 32 for char in witness_id)
    ):
        raise ValueError("witness_id must be a nonempty clean string or None")
    if witness is None:
        if witness_radii is not None or witness_independent or witness_id is not None:
            raise ValueError("absent witness cannot carry witness metadata")
        observed_witness = bounds = None
        reason = "witness_missing"
    else:
        observed_witness = _array(witness, (3, 2), "witness")
        if witness_independent and witness_id is None:
            raise ValueError("declared independent witness requires witness_id")
        bounds = (
            None
            if witness_radii is None
            else _array(witness_radii, (3,), "witness_radii", nonnegative=True)
        )
        reason = (
            "witness_error_unbounded"
            if bounds is None
            else "witness_independence_not_declared"
        )
    radii = disagreement = None
    if observed_witness is not None:
        with np.errstate(over="ignore", invalid="ignore"):
            difference = reference - observed_witness
            disagreement = np.hypot(difference[:, 0], difference[:, 1])
        if not np.isfinite(disagreement).all():
            raise ValueError("channel disagreement is not finite")
    bounded = (
        observed_witness is not None and bounds is not None and witness_independent
    )
    if bounded:
        with np.errstate(over="ignore", invalid="ignore"):
            radii = disagreement + bounds + NUMERICAL_MARGIN
        if not np.isfinite(radii).all():
            raise ValueError("reference budget is not finite")
        reason = "conditional_triangle_bound"
    body = {
        "schema_version": SCHEMA,
        **_scope(),
        "status": "bounded_relative_to_witness"
        if bounded
        else "common_mode_unidentified",
        "reason": reason,
        "reference_sha256": HASH(reference),
        "witness_coefficients": None
        if observed_witness is None
        else observed_witness.tolist(),
        "witness_sha256": None if observed_witness is None else HASH(observed_witness),
        "witness_radii": None if bounds is None else bounds.tolist(),
        "witness_id": witness_id,
        "witness_independent_declared": witness_independent,
        "witness_error_bound_is_declared_assumption": bounds is not None,
        "row_disagreement": None if disagreement is None else disagreement.tolist(),
        "radii": None if radii is None else radii.tolist(),
        "numerical_margin": NUMERICAL_MARGIN,
        "budget_rule": "row_l2(reference-witness)+witness_radius+numerical_margin",
        "reference_corrected": False,
        "shared_bias_diagnosed": False,
    }
    return {**body, "budget_seal_sha256": SEAL(body)}


def verify_budget(
    report,
    reference,
    witness=None,
    witness_radii=None,
    *,
    witness_independent=False,
    witness_id=None,
):
    """Replay external inputs and compare the entire canonical sealed record."""
    expected = reference_budget(
        reference,
        witness,
        witness_radii,
        witness_independent=witness_independent,
        witness_id=witness_id,
    )
    if type(report) is not dict or canonical_json_bytes(report) != canonical_json_bytes(
        expected
    ):
        raise ValueError("reference budget does not exactly replay")
    return True


def validate_budget(report, reference):
    """Validate a consumer contract, not the truth of its witness assumptions.

    External witness provenance remains a separate obligation. For binding to
    separately retained witness data, use ``verify_budget`` with those inputs.
    """
    if type(report) is not dict:
        raise ValueError("reference budget must be a JSON object")
    try:
        return verify_budget(
            report,
            reference,
            report["witness_coefficients"],
            report["witness_radii"],
            witness_independent=report["witness_independent_declared"],
            witness_id=report["witness_id"],
        )
    except KeyError as error:
        raise ValueError("reference budget declaration is incomplete") from error


def witness_stencil(placement_radius):
    """Return one of the two registered, well-conditioned five-point crosses."""
    if (
        isinstance(placement_radius, (bool, np.bool_))
        or not isinstance(placement_radius, (float, int, np.floating, np.integer))
        or placement_radius not in PLACEMENT_RADII
    ):
        raise ValueError("registered witness placement radius .5 or 1.0 required")
    h = float(placement_radius)
    return np.array([[0.0, 0.0], [-h, 0.0], [h, 0.0], [0.0, -h], [0.0, h]])


def fit_affine_witness(coords, values, point_bounds):
    """Fit a witness and propagate declared pointwise L2 errors linearly.

    This is conditional on an affine underlying channel over these coordinates.
    It does not bound model misspecification or certify independence. Pointwise
    bounds must already include any common-mode errors; observed fit residuals
    cannot establish them. Each coefficient row receives ``abs(pinv(X)) @
    point_bounds + 1e-12``. Placement changes slope bounds, not common bias.
    """
    coords = _array(coords, (5, 2), "witness coords")
    values = _array(values, (5, 2), "witness values")
    point_bounds = _array(point_bounds, (5,), "point_bounds", nonnegative=True)
    placement = next(
        (
            h
            for h in PLACEMENT_RADII
            if set(map(tuple, coords)) == set(map(tuple, witness_stencil(h)))
        ),
        None,
    )
    if placement is None:
        raise ValueError("unique registered five-point cross required")
    design = np.column_stack((np.ones(5), coords))
    inverse = np.linalg.pinv(design)
    coefficients, _, rank, _ = np.linalg.lstsq(design, values, rcond=None)
    if rank != 3:
        raise ValueError("full-rank affine witness design required")
    with np.errstate(over="ignore", invalid="ignore"):
        radii = np.abs(inverse) @ point_bounds + NUMERICAL_MARGIN
        residual = values - design @ coefficients
        errors = np.hypot(residual[:, 0], residual[:, 1])
    if not all(np.isfinite(v).all() for v in (coefficients, radii, errors)):
        raise ValueError("affine witness fit or bounds are not finite")
    coefficients[coefficients == 0] = 0.0
    body = {
        "schema_version": WITNESS_SCHEMA,
        **_scope(),
        "placement_radius": placement,
        "coords_sha256": HASH(coords),
        "values_sha256": HASH(values),
        "point_bounds": point_bounds.tolist(),
        "coefficients": coefficients.tolist(),
        "coefficient_sha256": HASH(coefficients),
        "radii": radii.tolist(),
        "fit_max_error": float(errors.max()),
        "affine_channel_is_declared_assumption": True,
        "point_error_bounds_are_declared_assumptions": True,
        "fit_residual_used_as_error_bound": False,
        "numerical_margin": NUMERICAL_MARGIN,
        "budget_rule": "abs(pinv([1,x,y]))@point_bounds+numerical_margin",
    }
    return {**body, "witness_fit_seal_sha256": SEAL(body)}
