"""Conservative scalar summaries of continuous holonomy matrices."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike
from scipy.linalg import polar

from spirallens.contracts import ContinuousHolonomy


def principal_rotation_angle_2d(
    holonomy: ContinuousHolonomy | ArrayLike,
) -> float:
    """Return the principal angle of the orthogonal polar factor.

    This is a continuous transport summary in ``[-pi, pi]``. It is not an
    integer winding number and must not be used as one.
    """

    matrix = (
        holonomy.matrix
        if isinstance(holonomy, ContinuousHolonomy)
        else np.asarray(holonomy)
    )
    if matrix.shape != (2, 2):
        raise ValueError("principal_rotation_angle_2d requires a 2x2 matrix")
    if np.iscomplexobj(matrix):
        if not np.allclose(matrix.imag, 0.0, atol=1e-12):
            raise ValueError("principal_rotation_angle_2d requires a real matrix")
        matrix = matrix.real
    if not np.all(np.isfinite(matrix)):
        raise ValueError("matrix must contain only finite values")
    orthogonal, _positive = polar(matrix)
    if np.linalg.det(orthogonal) <= 0:
        raise ValueError("polar factor is a reflection, not a planar rotation")
    return float(np.arctan2(orthogonal[1, 0], orthogonal[0, 0]))
