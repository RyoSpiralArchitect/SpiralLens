"""Closed, Level-0 primitives shared by in-memory qualification kernels."""

from __future__ import annotations

import hashlib
import math
import re
from enum import Enum
from typing import TypeVar

import numpy as np
from numpy.typing import NDArray

from spirallens.core.canonical import canonical_json_bytes, canonical_json_sha256

QUALIFICATION_RECORD_SCOPE = "in-memory-fingerprint-only"
QUALIFICATION_PERSISTENCE_ROUND_TRIP_SUPPORTED = False
QUALIFICATION_CLAIM_CEILING = "level_0"
QUALIFICATION_CLAIM_SCOPE = "model-free-instrument-qualification-only"

_SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

FloatArray = NDArray[np.float64]
Int64Array = NDArray[np.int64]


class QualificationContractError(ValueError):
    """Raised when a qualification input violates the closed contract."""


class QualificationState(str, Enum):
    """Gate verdicts; malformed inputs are exceptions, not states."""

    PASS = "pass"
    FAIL = "fail"
    FAIL_GRAPH_DEPENDENCE = "fail_graph_dependence"
    INSUFFICIENT = "insufficient"
    NOT_RUN = "not_run"


class AttemptStatus(str, Enum):
    """What the truth-blind estimator was able to emit."""

    EVALUABLE = "evaluable"
    INSUFFICIENT = "insufficient"
    NOT_RUN = "not_run"


class PredictionClass(str, Enum):
    """Aggregate-layer prediction vocabulary.

    Core localization and loop-phase kernels deliberately use their own
    domain-specific enums below.  This generic vocabulary remains only for
    later qualification aggregation records.
    """

    POSITIVE = "positive"
    NEGATIVE = "negative"
    ABSTAIN = "abstain"
    NONE = "none"


class ExpectedDisposition(str, Enum):
    """Aggregate-layer oracle vocabulary, not a kernel truth type."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    PREREQUISITE_FAILURE = "prerequisite_failure"


class CoreDisposition(str, Enum):
    """Oracle-side truth roles for the core-localization kernel only."""

    LOCALIZED_CORE = "localized_core"
    NO_CORE = "no_core"
    PREREQUISITE_FAILURE = "prerequisite_failure"


class CorePredictionClass(str, Enum):
    """Truth-blind decisions emitted by the core-localization kernel."""

    LOCALIZED_CORE = "localized_core"
    NO_CORE = "no_core"
    ABSTAIN = "abstain"
    NONE = "none"


class LoopDisposition(str, Enum):
    """Oracle-side truth roles for the sampled-loop kernel only."""

    NONZERO = "nonzero"
    NULL = "null"
    PREREQUISITE_FAILURE = "prerequisite_failure"


class LoopPredictionClass(str, Enum):
    """Truth-blind decisions emitted by the sampled-loop kernel."""

    NONZERO = "nonzero"
    NULL = "null"
    ABSTAIN = "abstain"
    NONE = "none"


class ObligationMode(str, Enum):
    """Whether one cell or its enclosing frozen stratum carries the gate."""

    INDIVIDUALLY_REQUIRED = "individually_required"
    STRATUM_SAMPLE = "stratum_sample"


class EvaluationUnit(str, Enum):
    """Closed evaluation units for later coverage aggregation."""

    VERTEX = "vertex"
    CORE = "core"
    BOUNDARY_LOOP = "boundary_loop"
    MATCHED_CLASS = "matched_class"
    GRAPH_CELL = "graph_cell"
    PHANTOM_INSTANCE = "phantom_instance"


EnumValue = TypeVar("EnumValue", bound=Enum)


def require_slug(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _SLUG.fullmatch(value) is None:
        raise QualificationContractError(f"{label} must be a lowercase portable slug")
    return value


def require_sha256(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise QualificationContractError(f"{label} must be a lowercase SHA-256 digest")
    return value


def require_bool(value: object, *, label: str) -> bool:
    if not isinstance(value, (bool, np.bool_)):
        raise QualificationContractError(f"{label} must be boolean")
    return bool(value)


def require_plain_int(
    value: object,
    *,
    label: str,
    minimum: int | None = None,
) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value,
        (int, np.integer),
    ):
        raise QualificationContractError(f"{label} must be an integer")
    result = int(value)
    if minimum is not None and result < minimum:
        raise QualificationContractError(f"{label} must be at least {minimum}")
    return result


def require_finite_real(
    value: object,
    *,
    label: str,
    minimum: float | None = None,
    maximum: float | None = None,
    minimum_inclusive: bool = True,
    maximum_inclusive: bool = True,
) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value,
        (int, float, np.integer, np.floating),
    ):
        raise QualificationContractError(f"{label} must be a real number")
    result = float(value)
    if not math.isfinite(result):
        raise QualificationContractError(f"{label} must be finite")
    if result == 0.0 and math.copysign(1.0, result) < 0.0:
        raise QualificationContractError(f"{label} must not be negative zero")
    if minimum is not None and (
        result < minimum or (not minimum_inclusive and result == minimum)
    ):
        relation = "greater than" if not minimum_inclusive else "at least"
        raise QualificationContractError(f"{label} must be {relation} {minimum}")
    if maximum is not None and (
        result > maximum or (not maximum_inclusive and result == maximum)
    ):
        relation = "less than" if not maximum_inclusive else "at most"
        raise QualificationContractError(f"{label} must be {relation} {maximum}")
    return result


def require_enum(
    enum_type: type[EnumValue],
    value: object,
    *,
    label: str,
) -> EnumValue:
    if not isinstance(value, enum_type):
        raise TypeError(f"{label} must be a {enum_type.__name__}")
    return value


def immutable_array(
    value: NDArray[np.generic],
    *,
    dtype: np.dtype[object],
) -> NDArray[np.generic]:
    """Return a C-order array backed by immutable bytes."""

    contiguous = np.array(value, dtype=dtype, order="C", copy=True)
    backing = contiguous.tobytes(order="C")
    return np.frombuffer(backing, dtype=dtype).reshape(contiguous.shape)


def float_matrix(value: object, *, label: str, width: int) -> FloatArray:
    source = np.asarray(value)
    if source.ndim != 2 or source.shape[1] != width or source.dtype.kind != "f":
        raise QualificationContractError(
            f"{label} must be a two-dimensional float array with width {width}"
        )
    result = np.array(source, dtype="<f8", order="C", copy=True)
    if result.shape[0] == 0:
        raise QualificationContractError(f"{label} must be nonempty")
    if not np.all(np.isfinite(result)):
        raise QualificationContractError(f"{label} must contain only finite values")
    result[result == 0.0] = 0.0
    return immutable_array(result, dtype=np.dtype("<f8"))  # type: ignore[return-value]


def float_vector(value: object, *, label: str, nonempty: bool = True) -> FloatArray:
    source = np.asarray(value)
    if source.ndim != 1 or source.dtype.kind != "f":
        raise QualificationContractError(
            f"{label} must be a one-dimensional float array"
        )
    result = np.array(source, dtype="<f8", order="C", copy=True)
    if nonempty and result.shape[0] == 0:
        raise QualificationContractError(f"{label} must be nonempty")
    if not np.all(np.isfinite(result)):
        raise QualificationContractError(f"{label} must contain only finite values")
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
        raise QualificationContractError(
            f"{label} must be a one-dimensional integer array"
        )
    try:
        result = np.array(source, dtype="<i8", order="C", copy=True)
    except (OverflowError, TypeError, ValueError) as error:
        raise QualificationContractError(
            f"{label} cannot be represented as int64"
        ) from error
    if not np.array_equal(result, source):
        raise QualificationContractError(f"{label} exceeds the int64 range")
    if nonempty and result.shape[0] == 0:
        raise QualificationContractError(f"{label} must be nonempty")
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
        raise QualificationContractError(
            f"{label} must be an integer matrix with width {width}"
        )
    try:
        result = np.array(source, dtype="<i8", order="C", copy=True)
    except (OverflowError, TypeError, ValueError) as error:
        raise QualificationContractError(
            f"{label} cannot be represented as int64"
        ) from error
    if not np.array_equal(result, source):
        raise QualificationContractError(f"{label} exceeds the int64 range")
    if nonempty and result.shape[0] == 0:
        raise QualificationContractError(f"{label} must be nonempty")
    return immutable_array(result, dtype=np.dtype("<i8"))  # type: ignore[return-value]


def array_fingerprint(
    value: NDArray[np.generic],
) -> dict[str, object]:
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


def fingerprint_mapping(value: dict[str, object]) -> str:
    return canonical_json_sha256(value)


def level0_boundary() -> dict[str, object]:
    """Return the identical non-claim boundary used by every D2 record."""

    return {
        "record_scope": QUALIFICATION_RECORD_SCOPE,
        "persistence_round_trip_supported": (
            QUALIFICATION_PERSISTENCE_ROUND_TRIP_SUPPORTED
        ),
        "claim_scope": QUALIFICATION_CLAIM_SCOPE,
        "claim_ceiling": QUALIFICATION_CLAIM_CEILING,
        "integer_output_authorized": False,
        "topology_claimed": False,
        "subject_access_authorized": False,
        "semantic_labels_present": False,
    }
