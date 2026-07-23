"""Subspace gauge alignment and Procrustes connections."""

from spirallens.gauge.procrustes_connection import (
    ProcrustesConnection,
    procrustes_connection,
)
from spirallens.gauge.subspace_tracking import (
    TrackedSubspaces,
    orthonormal_frame,
    principal_angles,
    track_subspaces,
)

__all__ = [
    "ProcrustesConnection",
    "TrackedSubspaces",
    "orthonormal_frame",
    "principal_angles",
    "procrustes_connection",
    "track_subspaces",
]
