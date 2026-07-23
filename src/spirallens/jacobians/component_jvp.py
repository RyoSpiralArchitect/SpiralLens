"""Generic JVP implementations for component-level accounting."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TypeVar

import numpy as np
from numpy.typing import ArrayLike, NDArray


ArrayFunction = Callable[[NDArray[np.float64]], ArrayLike]
T = TypeVar("T")


@dataclass(frozen=True)
class JvpSketch:
    """Orthonormal probe directions and their Jacobian images."""

    directions: NDArray[np.float64]
    images: NDArray[np.float64]
    method: str
    step: float


def _default_step(point: NDArray[np.float64], tangent: NDArray[np.float64]) -> float:
    """Scale a central-difference step to the point and direction norms."""

    point_scale = max(1.0, float(np.linalg.norm(point)))
    tangent_scale = max(float(np.linalg.norm(tangent)), np.finfo(np.float64).tiny)
    return np.cbrt(np.finfo(np.float64).eps) * point_scale / tangent_scale


def finite_difference_jvp(
    function: ArrayFunction,
    point: ArrayLike,
    tangent: ArrayLike,
    *,
    step: float | None = None,
    method: str = "central",
) -> NDArray[np.float64]:
    """Compute a numerical JVP without constructing a dense Jacobian."""

    x = np.asarray(point, dtype=np.float64)
    v = np.asarray(tangent, dtype=np.float64)
    if x.shape != v.shape:
        raise ValueError(f"point/tangent shape mismatch: {x.shape} != {v.shape}")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(v)):
        raise ValueError("point and tangent must contain only finite values")
    if method not in {"central", "forward"}:
        raise ValueError("method must be 'central' or 'forward'")
    h = _default_step(x, v) if step is None else float(step)
    if not np.isfinite(h) or h <= 0.0:
        raise ValueError("step must be finite and positive")

    if method == "central":
        positive = np.asarray(function(x + h * v), dtype=np.float64)
        negative = np.asarray(function(x - h * v), dtype=np.float64)
        if positive.shape != negative.shape:
            raise ValueError("function output shape changed across the finite difference")
        result = (positive - negative) / (2.0 * h)
    else:
        baseline = np.asarray(function(x), dtype=np.float64)
        positive = np.asarray(function(x + h * v), dtype=np.float64)
        if positive.shape != baseline.shape:
            raise ValueError("function output shape changed across the finite difference")
        result = (positive - baseline) / h
    if not np.all(np.isfinite(result)):
        raise ValueError("JVP contains non-finite values")
    return result


def torch_jvp(
    function: Callable[[T], T],
    point: T,
    tangent: T,
    *,
    create_graph: bool = False,
    strict: bool = False,
) -> tuple[T, T]:
    """Compute an exact autodiff JVP when optional PyTorch is installed."""

    try:
        import torch
    except ImportError as error:  # pragma: no cover - exercised without model extra
        raise RuntimeError("torch_jvp requires the optional 'models' dependencies") from error
    output, image = torch.autograd.functional.jvp(
        function,
        point,
        tangent,
        create_graph=create_graph,
        strict=strict,
    )
    return output, image


def component_jvps(
    components: Mapping[str, ArrayFunction],
    point: ArrayLike,
    tangent: ArrayLike,
    *,
    step: float | None = None,
) -> dict[str, NDArray[np.float64]]:
    """Evaluate the same tangent through independently declared components."""

    if not components:
        raise ValueError("components must not be empty")
    return {
        name: finite_difference_jvp(function, point, tangent, step=step)
        for name, function in components.items()
    }


def randomized_jvp_sketch(
    function: ArrayFunction,
    point: ArrayLike,
    *,
    sketch_rank: int,
    seed: int,
    step: float | None = None,
) -> JvpSketch:
    """Probe a local operator with deterministic random orthonormal directions."""

    x = np.asarray(point, dtype=np.float64)
    if x.ndim != 1:
        raise ValueError("randomized_jvp_sketch expects a one-dimensional point")
    if not 1 <= sketch_rank <= x.size:
        raise ValueError("sketch_rank must lie between one and the input width")
    rng = np.random.default_rng(seed)
    raw_directions = rng.standard_normal((x.size, sketch_rank))
    directions, _ = np.linalg.qr(raw_directions, mode="reduced")
    used_step = _default_step(x, directions[:, 0]) if step is None else float(step)
    images = [
        np.ravel(
            finite_difference_jvp(
                function,
                x,
                directions[:, column],
                step=used_step,
            )
        )
        for column in range(sketch_rank)
    ]
    return JvpSketch(
        directions=directions,
        images=np.stack(images, axis=1),
        method="central_finite_difference",
        step=used_step,
    )
