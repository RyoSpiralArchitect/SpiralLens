"""Continuous closed-loop transport.

This package does not expose integer winding; see :mod:`spirallens.topology`.
"""

from .connection import (
    connection_edge_transports,
    integrate_matrix_connection,
)
from .discrete import (
    compose_edge_transports,
    gauge_transform_edge_transports,
    pure_gauge_edge_transports,
    relative_holonomy,
    reverse_edge_transports,
)
from .metrics import principal_rotation_angle_2d

__all__ = [
    "compose_edge_transports",
    "connection_edge_transports",
    "gauge_transform_edge_transports",
    "integrate_matrix_connection",
    "principal_rotation_angle_2d",
    "pure_gauge_edge_transports",
    "relative_holonomy",
    "reverse_edge_transports",
]
