"""Deterministic metric whitening for activation-space measurements."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray


@dataclass(frozen=True)
class WhiteningTransform:
    """A fitted affine whitening map.

    ``matrix`` maps row vectors from the source width into a retained-rank
    whitened coordinate system.  Truncated eigen-directions are explicit in
    ``rank`` rather than silently receiving enormous inverse weights.
    """

    mean: NDArray[np.float64]
    matrix: NDArray[np.float64]
    eigenvalues: NDArray[np.float64]
    rank: int
    floor: float

    def transform(self, samples: ArrayLike) -> NDArray[np.float64]:
        values = np.asarray(samples, dtype=np.float64)
        if values.shape[-1] != self.mean.size:
            raise ValueError(
                f"last dimension {values.shape[-1]} does not match fitted width {self.mean.size}"
            )
        if not np.all(np.isfinite(values)):
            raise ValueError("samples must contain only finite values")
        return (values - self.mean) @ self.matrix

    def squared_distance(self, a: ArrayLike, b: ArrayLike) -> float:
        left = self.transform(np.asarray(a, dtype=np.float64))
        right = self.transform(np.asarray(b, dtype=np.float64))
        if left.ndim != 1 or right.ndim != 1:
            raise ValueError("squared_distance expects one-dimensional vectors")
        return float(np.dot(left - right, left - right))


def fit_whitening(
    samples: ArrayLike,
    *,
    relative_eigenvalue_floor: float = 1e-6,
    shrinkage: float = 0.0,
    max_rank: int | None = None,
) -> WhiteningTransform:
    """Fit a stable PCA whitening map from row-wise observations."""

    values = np.asarray(samples, dtype=np.float64)
    if values.ndim != 2 or values.shape[0] < 2:
        raise ValueError("samples must have shape (n >= 2, width)")
    if not np.all(np.isfinite(values)):
        raise ValueError("samples must contain only finite values")
    if not 0.0 <= shrinkage <= 1.0:
        raise ValueError("shrinkage must lie in [0, 1]")
    if relative_eigenvalue_floor <= 0.0:
        raise ValueError("relative_eigenvalue_floor must be positive")

    mean = values.mean(axis=0)
    centered = values - mean
    covariance = centered.T @ centered / float(values.shape[0] - 1)
    if shrinkage:
        isotropic = float(np.trace(covariance) / covariance.shape[0])
        covariance = (1.0 - shrinkage) * covariance + shrinkage * isotropic * np.eye(
            covariance.shape[0]
        )

    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    largest = max(float(eigenvalues[0]), np.finfo(np.float64).eps)
    floor = relative_eigenvalue_floor * largest
    rank = int(np.count_nonzero(eigenvalues >= floor))
    if max_rank is not None:
        if max_rank <= 0:
            raise ValueError("max_rank must be positive")
        rank = min(rank, max_rank)
    if rank == 0:
        raise ValueError("no covariance direction survives the eigenvalue floor")

    retained_values = eigenvalues[:rank]
    retained_vectors = eigenvectors[:, :rank]
    matrix = retained_vectors / np.sqrt(retained_values)[None, :]
    return WhiteningTransform(
        mean=mean,
        matrix=matrix,
        eigenvalues=retained_values,
        rank=rank,
        floor=floor,
    )
