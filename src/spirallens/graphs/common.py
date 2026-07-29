"""Closed validation and immutable-array helpers for graph foundations."""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Mapping
from enum import Enum
from pathlib import Path
from typing import TypeVar

import numpy as np
from numpy.typing import NDArray

from spirallens.core.canonical import canonical_json_bytes

GRAPH_RECORD_SCOPE = "in-memory-fingerprint-only"
GRAPH_PERSISTENCE_ROUND_TRIP_SUPPORTED = False
GRAPH_CLAIM_SCOPE = "model-free-graph-domain-foundation-only"
GRAPH_CLAIM_CEILING = "level_0"

GRAPH_RESOURCE_ESTIMATOR_ID = "graph-python-working-set-conservative-v0.2"
GRAPH_RESOURCE_SAFETY_FACTOR = 4
MAX_GRAPH_ESTIMATED_PEAK_BYTES = 256 * 1024 * 1024
_GRAPH_RESOURCE_BASE_OVERHEAD_BYTES = 1024 * 1024

_SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

FloatArray = NDArray[np.float64]
Int64Array = NDArray[np.int64]
BoolArray = NDArray[np.bool_]


class GraphContractError(ValueError):
    """Raised when a graph/domain foundation contract is invalid."""


class GraphFamily(str, Enum):
    """Declared adjacency mechanisms implemented by the development foundation."""

    MUTUAL_KNN = "mutual-knn"
    FIXED_RADIUS = "fixed-radius"
    SHARED_NEIGHBOR = "shared-neighbor"


class GraphPurpose(str, Enum):
    """Predeclared use of a graph, not a result selected from its output."""

    FIELD_ESTIMATION = "field-estimation"
    CYCLE_CONSTRUCTION = "cycle-construction"


EnumValue = TypeVar("EnumValue", bound=Enum)


def coordinate_order_invariant_euclidean_norm(
    value: NDArray[np.float64],
    *,
    axis: int = -1,
) -> NDArray[np.float64]:
    """Evaluate a float64 Euclidean norm in canonical magnitude order.

    Sorting absolute coordinates before the fixed ``hypot`` reduction makes
    the result bit-identical under signed coordinate permutations. This is
    required for deterministic distance ties in the graph constructors.
    """

    source = np.asarray(value)
    if source.dtype.kind != "f":
        raise TypeError("Euclidean norm input must have a floating dtype")
    ordered = np.sort(
        np.abs(np.asarray(source, dtype="<f8")),
        axis=axis,
        kind="stable",
    )
    return np.asarray(np.hypot.reduce(ordered, axis=axis), dtype="<f8")


def require_mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise GraphContractError(f"{label} must be a string-keyed mapping")
    return value


def require_exact_keys(
    value: Mapping[str, object],
    *,
    expected: set[str] | frozenset[str],
    label: str,
) -> None:
    actual = set(value)
    if actual != set(expected):
        raise GraphContractError(
            f"{label} fields differ from the contract: "
            f"missing={sorted(set(expected) - actual)}, "
            f"unknown={sorted(actual - set(expected))}"
        )


def require_slug(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _SLUG.fullmatch(value) is None:
        raise GraphContractError(f"{label} must be a lowercase portable slug")
    return value


def require_sha256(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise GraphContractError(f"{label} must be a lowercase SHA-256 digest")
    return value


def require_plain_int(value: object, *, label: str, minimum: int) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value,
        (int, np.integer),
    ):
        raise GraphContractError(f"{label} must be an integer")
    result = int(value)
    if result < minimum:
        raise GraphContractError(f"{label} must be at least {minimum}")
    return result


def require_positive_float(value: object, *, label: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value,
        (int, float, np.integer, np.floating),
    ):
        raise GraphContractError(f"{label} must be a real number")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise GraphContractError(f"{label} must be finite and positive")
    return result


def parse_enum(
    enum_type: type[EnumValue],
    value: object,
    *,
    label: str,
) -> EnumValue:
    if not isinstance(value, str):
        raise GraphContractError(f"{label} must be a string")
    try:
        return enum_type(value)
    except ValueError as error:
        raise GraphContractError(f"{label} is not supported") from error


def immutable_array(
    value: NDArray[np.generic],
    *,
    dtype: np.dtype[object],
) -> NDArray[np.generic]:
    contiguous = np.array(value, dtype=dtype, order="C", copy=True)
    backing = contiguous.tobytes(order="C")
    return np.frombuffer(backing, dtype=dtype).reshape(contiguous.shape)


def float_matrix(value: object, *, label: str) -> FloatArray:
    source = np.asarray(value)
    if source.ndim != 2 or source.dtype.kind != "f":
        raise GraphContractError(f"{label} must be a two-dimensional float array")
    result = np.array(source, dtype="<f8", order="C", copy=True)
    if result.shape[0] == 0 or result.shape[1] == 0:
        raise GraphContractError(f"{label} must have nonempty row and feature axes")
    if not np.all(np.isfinite(result)):
        raise GraphContractError(f"{label} must contain only finite values")
    result[result == 0.0] = 0.0
    return immutable_array(result, dtype=np.dtype("<f8"))  # type: ignore[return-value]


def float_vector(value: object, *, label: str) -> FloatArray:
    source = np.asarray(value)
    if source.ndim != 1 or source.dtype.kind != "f":
        raise GraphContractError(f"{label} must be a one-dimensional float array")
    result = np.array(source, dtype="<f8", order="C", copy=True)
    if not np.all(np.isfinite(result)):
        raise GraphContractError(f"{label} must contain only finite values")
    result[result == 0.0] = 0.0
    return immutable_array(result, dtype=np.dtype("<f8"))  # type: ignore[return-value]


def int64_vector(
    value: object,
    *,
    label: str,
    nonempty: bool = True,
) -> Int64Array:
    source = np.asarray(value)
    if source.ndim != 1 or source.dtype.kind not in {"i", "u"}:
        raise GraphContractError(f"{label} must be a one-dimensional integer array")
    try:
        result = np.array(source, dtype="<i8", order="C", copy=True)
    except (OverflowError, TypeError, ValueError) as error:
        raise GraphContractError(f"{label} cannot be represented as int64") from error
    if not np.array_equal(result, source):
        raise GraphContractError(f"{label} exceeds the int64 range")
    if nonempty and result.shape[0] == 0:
        raise GraphContractError(f"{label} must be nonempty")
    return immutable_array(result, dtype=np.dtype("<i8"))  # type: ignore[return-value]


def int64_matrix(
    value: object,
    *,
    label: str,
    width: int,
    nonempty: bool = False,
) -> Int64Array:
    source = np.asarray(value)
    if (
        source.ndim != 2
        or source.shape[1] != width
        or source.dtype.kind not in {"i", "u"}
    ):
        raise GraphContractError(
            f"{label} must be an integer matrix with width {width}"
        )
    try:
        result = np.array(source, dtype="<i8", order="C", copy=True)
    except (OverflowError, TypeError, ValueError) as error:
        raise GraphContractError(f"{label} cannot be represented as int64") from error
    if not np.array_equal(result, source):
        raise GraphContractError(f"{label} exceeds the int64 range")
    if nonempty and result.shape[0] == 0:
        raise GraphContractError(f"{label} must be nonempty")
    return immutable_array(result, dtype=np.dtype("<i8"))  # type: ignore[return-value]


def bool_vector(value: object, *, label: str) -> BoolArray:
    source = np.asarray(value)
    if source.ndim != 1 or source.dtype.kind != "b":
        raise GraphContractError(f"{label} must be a one-dimensional boolean array")
    return immutable_array(source, dtype=np.dtype("|b1"))  # type: ignore[return-value]


def array_fingerprint(value: NDArray[np.generic]) -> dict[str, object]:
    descriptor = canonical_json_bytes(
        {
            "dtype": value.dtype.str,
            "shape": list(value.shape),
        }
    )
    return {
        "dtype": value.dtype.str,
        "shape": list(value.shape),
        "sha256": hashlib.sha256(
            descriptor + b"\x00" + value.tobytes(order="C")
        ).hexdigest(),
    }


def array_sha256(value: NDArray[np.generic]) -> str:
    fingerprint = array_fingerprint(value)
    digest = fingerprint["sha256"]
    assert isinstance(digest, str)
    return digest


def graph_estimated_peak_bytes(*, row_count: int, feature_count: int) -> int:
    return GRAPH_RESOURCE_SAFETY_FACTOR * _graph_base_bytes(
        row_count=row_count,
        feature_count=feature_count,
    )


def graph_construction_estimated_peak_bytes(
    *,
    row_count: int,
    feature_count: int,
    family: GraphFamily,
    neighbor_count: int | None,
) -> int:
    """Conservatively include dense outputs and Python container overhead."""

    dense_edge_count = row_count * (row_count - 1) // 2
    dense_edge_container_bytes = dense_edge_count * 128
    adjacency_reference_bytes = 2 * dense_edge_count * 16
    receipt_audit_container_bytes = dense_edge_count * 96
    neighbor_container_bytes = 0
    if family in {GraphFamily.MUTUAL_KNN, GraphFamily.SHARED_NEIGHBOR}:
        if neighbor_count is None:
            raise GraphContractError(
                "neighbor_count is required for neighbor-based resource estimation"
            )
        neighbor_container_bytes = row_count * neighbor_count * 160
    base = (
        _graph_base_bytes(
            row_count=row_count,
            feature_count=feature_count,
        )
        + dense_edge_container_bytes
        + adjacency_reference_bytes
        + receipt_audit_container_bytes
        + neighbor_container_bytes
    )
    return GRAPH_RESOURCE_SAFETY_FACTOR * base


def _graph_base_bytes(*, row_count: int, feature_count: int) -> int:
    return (
        _GRAPH_RESOURCE_BASE_OVERHEAD_BYTES
        + row_count * row_count * (8 + 1 + 8)
        + row_count * feature_count * 16
    )


def module_sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
