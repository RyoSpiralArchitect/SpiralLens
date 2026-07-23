"""Sparse-autoencoder feature summaries for post-discovery annotation."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike


def top_sae_features(
    feature_activations: ArrayLike,
    *,
    top_k: int = 10,
    feature_ids: ArrayLike | None = None,
) -> list[dict[str, float | int]]:
    """Return deterministic top activations without assigning semantic meaning."""

    values = np.asarray(feature_activations, dtype=np.float64)
    if values.ndim != 1 or not np.all(np.isfinite(values)):
        raise ValueError("feature_activations must be a finite vector")
    if not 1 <= top_k <= values.size:
        raise ValueError("top_k must lie within the feature width")
    identifiers = (
        np.arange(values.size, dtype=np.int64)
        if feature_ids is None
        else np.asarray(feature_ids, dtype=np.int64)
    )
    if identifiers.shape != values.shape:
        raise ValueError("feature_ids must match feature_activations")
    # Lexsort makes ties reproducible by preferring the smaller feature ID.
    order = np.lexsort((identifiers, -values))[:top_k]
    return [
        {
            "rank": rank,
            "feature_id": int(identifiers[index]),
            "activation": float(values[index]),
        }
        for rank, index in enumerate(order, start=1)
    ]
