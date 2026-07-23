"""Analytic rotary-position rotation and de-rotation."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray


def rope_angles(
    position: ArrayLike,
    rotary_dimension: int,
    *,
    base: float = 10_000.0,
) -> NDArray[np.float64]:
    """Return RoPE angles with shape ``position.shape + (rotary_dimension / 2,)``."""

    if rotary_dimension <= 0 or rotary_dimension % 2:
        raise ValueError("rotary_dimension must be a positive even integer")
    if base <= 1.0:
        raise ValueError("base must be greater than one")
    positions = np.asarray(position, dtype=np.float64)
    frequencies = base ** (
        -np.arange(0, rotary_dimension, 2, dtype=np.float64) / rotary_dimension
    )
    return positions[..., None] * frequencies


def _rotate_pairs(
    value: ArrayLike,
    angles: ArrayLike,
    *,
    inverse: bool,
    layout: str,
) -> NDArray[np.float64]:
    x = np.asarray(value, dtype=np.float64)
    theta = np.asarray(angles, dtype=np.float64)
    rotary_dimension = theta.shape[-1] * 2
    if x.shape[-1] < rotary_dimension:
        raise ValueError("value width is smaller than the declared rotary dimension")
    if x.shape[:-1] != theta.shape[:-1]:
        try:
            theta = np.broadcast_to(theta, x.shape[:-1] + (theta.shape[-1],))
        except ValueError as error:
            raise ValueError("angles cannot be broadcast across value leading axes") from error

    signed = -theta if inverse else theta
    cosine = np.cos(signed)
    sine = np.sin(signed)
    rotary = x[..., :rotary_dimension]
    rotated = np.empty_like(rotary)
    if layout == "gpt_neox":
        # Hugging Face GPTNeoX/Pythia uses rotate_half: the rotary region is
        # split into two contiguous halves, not consecutive coordinate pairs.
        half = rotary_dimension // 2
        first = rotary[..., :half]
        second = rotary[..., half:]
        rotated[..., :half] = first * cosine - second * sine
        rotated[..., half:] = first * sine + second * cosine
    elif layout == "interleaved":
        even = rotary[..., 0::2]
        odd = rotary[..., 1::2]
        rotated[..., 0::2] = even * cosine - odd * sine
        rotated[..., 1::2] = even * sine + odd * cosine
    else:
        raise ValueError("layout must be 'gpt_neox' or 'interleaved'")
    if rotary_dimension == x.shape[-1]:
        return rotated
    return np.concatenate((rotated, x[..., rotary_dimension:]), axis=-1)


def apply_rope(
    value: ArrayLike,
    angles: ArrayLike,
    *,
    layout: str = "gpt_neox",
) -> NDArray[np.float64]:
    """Apply RoPE using an explicit coordinate layout.

    ``gpt_neox`` is the default because Pythia splits the rotary region into
    contiguous first/second halves.  ``interleaved`` is available for model
    families that rotate consecutive even/odd coordinate pairs.
    """

    return _rotate_pairs(value, angles, inverse=False, layout=layout)


def derotate_rope(
    value: ArrayLike,
    angles: ArrayLike,
    *,
    layout: str = "gpt_neox",
) -> NDArray[np.float64]:
    """Apply the exact inverse of :func:`apply_rope`."""

    return _rotate_pairs(value, angles, inverse=True, layout=layout)
