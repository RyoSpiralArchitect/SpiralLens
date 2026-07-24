"""Typed, semantics-free contracts for structural neighbor retrieval."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
import hashlib
import json
from numbers import Integral, Real
from typing import Literal, Protocol, runtime_checkable

import numpy as np
from numpy.typing import ArrayLike


NEIGHBOR_QUERY_SCHEMA_VERSION = "spirallens.neighbor-query.v0.1"
NEIGHBOR_BACKEND_SCHEMA_VERSION = "spirallens.neighbor-backend.v0.1"
NEIGHBOR_INDEX_BUILD_SCHEMA_VERSION = (
    "spirallens.neighbor-index-build.v0.1"
)

JsonScalar = str | int | float | bool | None


def canonical_json_sha256(payload: object) -> str:
    """Return the SHA-256 of one finite canonical JSON value."""

    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def state_matrix_sha256(
    states: ArrayLike,
    *,
    block_size: int = 1024,
) -> str:
    """Hash one state matrix with shape and dtype bound to its bytes."""

    if isinstance(block_size, bool) or not isinstance(
        block_size,
        Integral,
    ):
        raise TypeError("block_size must be an integer")
    if block_size <= 0:
        raise ValueError("block_size must be positive")
    rows = states if hasattr(states, "shape") else np.asanyarray(states)
    if rows.ndim != 2:
        raise ValueError("states must have shape (observations, hidden)")
    dtype = getattr(rows, "dtype", None)
    if dtype is None:
        if int(rows.shape[0]) == 0:
            raise ValueError("states without dtype must contain a row")
        dtype = np.asarray(rows[0:1]).dtype
    header = {
        "shape": [int(rows.shape[0]), int(rows.shape[1])],
        "dtype": str(dtype),
    }
    digest = hashlib.sha256()
    digest.update(
        json.dumps(
            header,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    )
    digest.update(b"\0")
    for start in range(0, int(rows.shape[0]), int(block_size)):
        stop = min(start + int(block_size), int(rows.shape[0]))
        block = np.ascontiguousarray(rows[start:stop])
        if block.ndim != 2 or block.shape[1] != rows.shape[1]:
            raise ValueError("state row blocks changed shape during hashing")
        if str(block.dtype) != str(dtype):
            raise ValueError("state row blocks changed dtype during hashing")
        digest.update(memoryview(block).cast("B"))
    return digest.hexdigest()


def _require_sha256(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _canonical_scalar_entries(
    values: tuple[tuple[str, JsonScalar], ...],
    *,
    label: str,
) -> tuple[tuple[str, JsonScalar], ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{label} must be a tuple of key/value pairs")
    normalized: list[tuple[str, JsonScalar]] = []
    seen: set[str] = set()
    for item in values:
        if not isinstance(item, tuple) or len(item) != 2:
            raise TypeError(f"{label} entries must be (key, value) tuples")
        key, value = item
        if not isinstance(key, str) or not key:
            raise TypeError(f"{label} keys must be non-empty strings")
        if key in seen:
            raise ValueError(f"{label} contains duplicate key {key!r}")
        if not isinstance(value, (str, int, float, bool, type(None))):
            raise TypeError(f"{label}.{key} must be a JSON scalar")
        if isinstance(value, float) and not np.isfinite(value):
            raise ValueError(f"{label}.{key} must be finite")
        seen.add(key)
        normalized.append((key, value))
    return tuple(sorted(normalized))


def _canonical_runtime_entries(
    values: tuple[tuple[str, str], ...],
) -> tuple[tuple[str, str], ...]:
    if not isinstance(values, tuple):
        raise TypeError("runtime must be a tuple of key/value pairs")
    normalized: list[tuple[str, str]] = []
    seen: set[str] = set()
    for item in values:
        if not isinstance(item, tuple) or len(item) != 2:
            raise TypeError("runtime entries must be (key, value) tuples")
        key, value = item
        if not isinstance(key, str) or not key:
            raise TypeError("runtime keys must be non-empty strings")
        if not isinstance(value, str) or not value:
            raise TypeError(f"runtime.{key} must be a non-empty string")
        if key in seen:
            raise ValueError(f"runtime contains duplicate key {key!r}")
        seen.add(key)
        normalized.append((key, value))
    return tuple(sorted(normalized))


@dataclass(frozen=True)
class NeighborQuery:
    """The exact state-space boundary a retrieval backend must cover.

    ``query_indices=None`` means every unordered row pair. Otherwise, only
    unordered pairs touching at least one declared query row are in scope.
    Retrieval receives states only; drift and semantic information are outside
    this contract.
    """

    cosine_min: float
    relative_norm_gap_max: float
    min_state_norm: float
    epsilon: float
    query_indices: tuple[int, ...] | None = None
    metric: Literal["cosine"] = field(default="cosine", init=False)
    schema_version: str = field(
        default=NEIGHBOR_QUERY_SCHEMA_VERSION,
        init=False,
    )

    def __post_init__(self) -> None:
        for field_name in (
            "cosine_min",
            "relative_norm_gap_max",
            "min_state_norm",
            "epsilon",
        ):
            value = getattr(self, field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, Real)
                or not np.isfinite(value)
            ):
                raise TypeError(f"{field_name} must be a finite real number")
            object.__setattr__(self, field_name, float(value))
        if not -1.0 <= self.cosine_min <= 1.0:
            raise ValueError("cosine_min must lie in [-1, 1]")
        if self.relative_norm_gap_max < 0.0:
            raise ValueError("relative_norm_gap_max must be non-negative")
        if self.min_state_norm < 0.0:
            raise ValueError("min_state_norm must be non-negative")
        if self.epsilon <= 0.0:
            raise ValueError("epsilon must be positive")
        if self.query_indices is not None:
            if not isinstance(self.query_indices, tuple):
                raise TypeError("query_indices must be a tuple or None")
            canonical: list[int] = []
            for index in self.query_indices:
                if isinstance(index, bool) or not isinstance(index, Integral):
                    raise TypeError("query_indices must contain integers")
                canonical.append(int(index))
            if any(index < 0 for index in canonical):
                raise ValueError("query_indices must be non-negative")
            if any(
                right <= left
                for left, right in zip(canonical, canonical[1:], strict=False)
            ):
                raise ValueError(
                    "query_indices must be unique and strictly increasing"
                )
            object.__setattr__(self, "query_indices", tuple(canonical))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "metric": self.metric,
            "cosine_min": self.cosine_min,
            "relative_norm_gap_max": self.relative_norm_gap_max,
            "min_state_norm": self.min_state_norm,
            "epsilon": self.epsilon,
            "query_indices": (
                None
                if self.query_indices is None
                else list(self.query_indices)
            ),
        }

    @property
    def sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


@dataclass(frozen=True)
class NeighborPair:
    """One canonical unordered pair proposed for exact reranking."""

    left_index: int
    right_index: int
    backend_score: float | None = field(default=None, compare=False)

    def __post_init__(self) -> None:
        for field_name in ("left_index", "right_index"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, Integral):
                raise TypeError(f"{field_name} must be an integer")
            object.__setattr__(self, field_name, int(value))
        if self.left_index < 0:
            raise ValueError("left_index must be non-negative")
        if self.left_index >= self.right_index:
            raise ValueError(
                "neighbor pairs must satisfy left_index < right_index"
            )
        if self.backend_score is not None:
            if (
                isinstance(self.backend_score, bool)
                or not isinstance(self.backend_score, Real)
                or not np.isfinite(self.backend_score)
            ):
                raise TypeError("backend_score must be a finite real or None")
            object.__setattr__(self, "backend_score", float(self.backend_score))

    @property
    def key(self) -> tuple[int, int]:
        return (self.left_index, self.right_index)


@dataclass(frozen=True)
class NeighborBackendDescriptor:
    """Canonical backend identity persisted independently of pair scores."""

    backend_id: str
    backend_version: str
    kind: Literal["exact", "approximate"]
    deterministic: bool
    parameters: tuple[tuple[str, JsonScalar], ...] = ()
    runtime: tuple[tuple[str, str], ...] = ()
    metric: Literal["cosine"] = field(default="cosine", init=False)
    schema_version: str = field(
        default=NEIGHBOR_BACKEND_SCHEMA_VERSION,
        init=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.backend_id, str) or not self.backend_id:
            raise TypeError("backend_id must be a non-empty string")
        if not isinstance(self.backend_version, str) or not self.backend_version:
            raise TypeError("backend_version must be a non-empty string")
        if self.kind not in {"exact", "approximate"}:
            raise ValueError("kind must be 'exact' or 'approximate'")
        if not isinstance(self.deterministic, bool):
            raise TypeError("deterministic must be a boolean")
        object.__setattr__(
            self,
            "parameters",
            _canonical_scalar_entries(self.parameters, label="parameters"),
        )
        object.__setattr__(
            self,
            "runtime",
            _canonical_runtime_entries(self.runtime),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "backend_id": self.backend_id,
            "backend_version": self.backend_version,
            "kind": self.kind,
            "metric": self.metric,
            "deterministic": self.deterministic,
            "parameters": dict(self.parameters),
            "runtime": dict(self.runtime),
        }

    @property
    def sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


@dataclass(frozen=True)
class NeighborIndexBuildReceipt:
    """Immutable binding between one prepared index and its full input."""

    backend: NeighborBackendDescriptor
    states_sha256: str
    row_identity_sha256: str
    index_sha256: str
    comparison_group: str
    row_count: int
    hidden_size: int
    states_dtype: str
    schema_version: str = field(
        default=NEIGHBOR_INDEX_BUILD_SCHEMA_VERSION,
        init=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.backend, NeighborBackendDescriptor):
            raise TypeError(
                "backend must be a NeighborBackendDescriptor"
            )
        for field_name in (
            "states_sha256",
            "row_identity_sha256",
            "index_sha256",
        ):
            _require_sha256(getattr(self, field_name), label=field_name)
        if (
            not isinstance(self.comparison_group, str)
            or not self.comparison_group
        ):
            raise TypeError(
                "comparison_group must be a non-empty string"
            )
        for field_name in ("row_count", "hidden_size"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, Integral):
                raise TypeError(f"{field_name} must be an integer")
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
            object.__setattr__(self, field_name, int(value))
        if not isinstance(self.states_dtype, str) or not self.states_dtype:
            raise TypeError("states_dtype must be a non-empty string")
        parameters = dict(self.backend.parameters)
        expected = {
            "states_sha256": self.states_sha256,
            "row_identity_sha256": self.row_identity_sha256,
            "index_sha256": self.index_sha256,
            "comparison_group": self.comparison_group,
            "row_count": self.row_count,
            "hidden_size": self.hidden_size,
            "states_dtype": self.states_dtype,
        }
        if any(parameters.get(key) != value for key, value in expected.items()):
            raise ValueError(
                "backend descriptor does not match its index build receipt"
            )

    def to_dict(self) -> dict[str, object]:
        backend = self.backend.to_dict()
        return {
            "schema_version": self.schema_version,
            "backend": backend,
            "backend_sha256": self.backend.sha256,
            "states_sha256": self.states_sha256,
            "row_identity_sha256": self.row_identity_sha256,
            "index_sha256": self.index_sha256,
            "comparison_group": self.comparison_group,
            "row_count": self.row_count,
            "hidden_size": self.hidden_size,
            "states_dtype": self.states_dtype,
        }

    @property
    def sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())


@runtime_checkable
class NeighborBackend(Protocol):
    """State-only retrieval protocol.

    Implementations must emit unique pairs in strict ``(left, right)``
    lexicographic order. They must never receive or use drift, decoded strings,
    semantic labels, SAE annotations, or projected coordinates.
    """

    @property
    def descriptor(self) -> NeighborBackendDescriptor: ...

    def iter_pairs(
        self,
        states: ArrayLike,
        *,
        query: NeighborQuery,
    ) -> Iterator[NeighborPair]: ...


@runtime_checkable
class PreparedNeighborBackend(NeighborBackend, Protocol):
    """A backend whose immutable index is already bound to full states."""

    @property
    def build_receipt(self) -> NeighborIndexBuildReceipt: ...

    def export_index_bytes(self) -> bytes: ...


def validate_prepared_backend(
    backend: PreparedNeighborBackend,
    *,
    states: ArrayLike,
    row_identity_sha256: str,
    comparison_group: str,
) -> NeighborIndexBuildReceipt:
    """Recompute every runner-visible binding for one prepared index."""

    if not isinstance(backend, PreparedNeighborBackend):
        raise TypeError(
            "approximate backend must implement PreparedNeighborBackend"
        )
    receipt = backend.build_receipt
    if not isinstance(receipt, NeighborIndexBuildReceipt):
        raise TypeError(
            "prepared backend build_receipt must be "
            "NeighborIndexBuildReceipt"
        )
    rows = np.asanyarray(states)
    if rows.ndim != 2:
        raise ValueError("states must have shape (observations, hidden)")
    _require_sha256(
        row_identity_sha256,
        label="row_identity_sha256",
    )
    if (
        receipt.backend != backend.descriptor
        or receipt.states_sha256 != state_matrix_sha256(rows)
        or receipt.row_identity_sha256 != row_identity_sha256
        or receipt.comparison_group != comparison_group
        or receipt.row_count != int(rows.shape[0])
        or receipt.hidden_size != int(rows.shape[1])
        or receipt.states_dtype != str(rows.dtype)
    ):
        raise ValueError(
            "prepared backend does not match the requested full input/group"
        )
    index_bytes = backend.export_index_bytes()
    if not isinstance(index_bytes, bytes) or not index_bytes:
        raise TypeError(
            "prepared backend must export non-empty immutable index bytes"
        )
    if hashlib.sha256(index_bytes).hexdigest() != receipt.index_sha256:
        raise ValueError(
            "prepared backend index bytes do not match its build receipt"
        )
    return receipt


def validate_neighbor_pairs(
    pairs: Iterator[NeighborPair],
    *,
    row_count: int,
) -> Iterator[NeighborPair]:
    """Fail closed on invalid, duplicate, or non-deterministically ordered pairs."""

    if isinstance(row_count, bool) or not isinstance(row_count, Integral):
        raise TypeError("row_count must be an integer")
    if row_count < 0:
        raise ValueError("row_count must be non-negative")
    previous: tuple[int, int] | None = None
    for pair in pairs:
        if not isinstance(pair, NeighborPair):
            raise TypeError("neighbor backend must yield NeighborPair values")
        if pair.right_index >= row_count:
            raise ValueError(
                f"neighbor pair {pair.key} exceeds row_count={row_count}"
            )
        if previous is not None and pair.key <= previous:
            raise ValueError(
                "neighbor backend pairs must be unique and strictly "
                "lexicographically ordered"
            )
        previous = pair.key
        yield pair
