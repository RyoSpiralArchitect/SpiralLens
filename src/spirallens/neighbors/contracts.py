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
