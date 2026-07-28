"""Closed vocabularies and validation helpers for pointwise referents."""

from __future__ import annotations

import re
from collections.abc import Mapping
from enum import Enum
from typing import TypeVar

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")


class ReferentContractError(ValueError):
    """Raised when a referent contract or numeric relation is invalid."""


class ReferentKind(str, Enum):
    """The mathematical object named by one hypothesis family."""

    SUPPORT_DIAGNOSTIC = "support_diagnostic"
    RANK_TWO_PROJECTOR = "rank_two_projector"
    LOCAL_VECTOR_SECTION = "local_vector_section"
    GLOBAL_VECTOR_SECTION = "global_vector_section"
    SPIN_TWO_TRACELESS_TENSOR = "spin_two_traceless_tensor"


class GaugeGroup(str, Enum):
    """The coordinate freedom declared for one referent."""

    NONE = "none"
    AMBIENT_OD = "ambient_od"
    LOCAL_O2 = "local_o2"
    GLOBAL_O2 = "global_o2"


class TransformationLaw(str, Enum):
    """Exact transformation family to be exercised numerically."""

    SCALAR_INVARIANT = "scalar_invariant"
    PROJECTOR_CONJUGATION = "projector_conjugation"
    O2_COVARIANT_VECTOR = "o2_covariant_vector"
    SPIN_TWO_TRACELESS_SYMMETRIC = "spin_two_traceless_symmetric"


class DirectionRule(str, Enum):
    """How a direction is obtained, if one exists."""

    NOT_DEFINED = "not_defined"
    NORMALIZE_SAME_VECTOR = "normalize_same_vector"
    NORMALIZE_SPIN_TWO_VECTOR = "normalize_spin_two_vector"


class FitEvaluationRule(str, Enum):
    """How fitted geometry and evaluated values must be separated."""

    NOT_APPLICABLE = "not_applicable"
    FIT_ONLY_GEOMETRY = "fit_only_geometry"
    CROSS_FIT_REQUIRED = "cross_fit_required"
    CROSS_FIT_IF_LEARNED = "cross_fit_if_learned"


class ChargeConvention(str, Enum):
    """The only charge interpretation a referent may eventually request."""

    NONE = "none"
    CONDITIONAL_VECTOR_INTEGER = "conditional_vector_integer"
    PROJECTION_DEPENDENT_CANDIDATE = "projection_dependent_candidate"
    DOUBLED_ANGLE_INTEGER = "doubled_angle_integer"


EnumValue = TypeVar("EnumValue", bound=Enum)


def require_mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise ReferentContractError(f"{label} must be a string-keyed mapping")
    return value


def require_exact_keys(
    value: Mapping[str, object],
    *,
    expected: frozenset[str],
    label: str,
) -> None:
    actual = set(value)
    if actual != set(expected):
        raise ReferentContractError(
            f"{label} fields differ from the contract: "
            f"missing={sorted(set(expected) - actual)}, "
            f"unknown={sorted(actual - set(expected))}"
        )


def require_string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ReferentContractError(f"{label} must be a non-empty string")
    if value != value.strip():
        raise ReferentContractError(f"{label} must not have surrounding whitespace")
    return value


def require_slug(value: object, *, label: str) -> str:
    text = require_string(value, label=label)
    if _SLUG.fullmatch(text) is None:
        raise ReferentContractError(f"{label} must be a lowercase slug")
    return text


def require_sha256(value: object, *, label: str) -> str:
    text = require_string(value, label=label)
    if _SHA256.fullmatch(text) is None:
        raise ReferentContractError(f"{label} must be a lowercase SHA-256 digest")
    return text


def require_false(value: object, *, label: str) -> bool:
    if type(value) is not bool:
        raise ReferentContractError(f"{label} must be a boolean")
    if value:
        raise ReferentContractError(f"{label} must be false")
    return False


def require_bool(value: object, *, label: str) -> bool:
    if type(value) is not bool:
        raise ReferentContractError(f"{label} must be a boolean")
    return value


def parse_enum(
    enum_type: type[EnumValue],
    value: object,
    *,
    label: str,
) -> EnumValue:
    if not isinstance(value, str):
        raise ReferentContractError(f"{label} must be a string")
    try:
        return enum_type(value)
    except ValueError as error:
        allowed = ", ".join(member.value for member in enum_type)
        raise ReferentContractError(f"{label} must be one of: {allowed}") from error


def validate_slug_tuple(
    values: object,
    *,
    label: str,
    nonempty: bool = True,
) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ReferentContractError(f"{label} must be a tuple")
    if nonempty and not values:
        raise ReferentContractError(f"{label} must not be empty")
    parsed = tuple(
        require_slug(value, label=f"{label}[{index}]")
        for index, value in enumerate(values)
    )
    if parsed != tuple(sorted(set(parsed))):
        raise ReferentContractError(f"{label} must be unique and sorted")
    return parsed


def parse_slug_list(
    value: object,
    *,
    label: str,
    nonempty: bool = True,
) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ReferentContractError(f"{label} must be a list")
    return validate_slug_tuple(tuple(value), label=label, nonempty=nonempty)
