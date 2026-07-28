"""Typed identities and structural interfaces for synthetic generators.

The contracts in this module distinguish a mathematical construction family
from its seed, source digest, and implementation label.  Distinct seeds or
source files are useful replay facts, but they cannot by themselves satisfy a
requirement for distinct construction families.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol, TypeVar, runtime_checkable

from spirallens.core.canonical import (
    canonical_json_bytes,
    canonical_json_sha256,
)

GENERATOR_FAMILY_IDENTITY_SCHEMA_VERSION = (
    "spirallens.synthetic-generator-family-identity.v0.1"
)

_SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class GeneratorFamilyContractError(ValueError):
    """Raised when generator-family metadata violates the closed contract."""


def _slug(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _SLUG.fullmatch(value) is None:
        raise GeneratorFamilyContractError(f"{label} must be a lowercase portable slug")
    return value


def _sha256(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise GeneratorFamilyContractError(
            f"{label} must be a lowercase SHA-256 digest"
        )
    return value


@dataclass(frozen=True, slots=True)
class GeneratorFamilyIdentity:
    """Canonical identity of one mathematical synthetic construction.

    ``construction_family_id`` identifies the mathematical/data-generating
    construction.  ``implementation_id`` and ``source_sha256`` identify one
    implementation of it.  Random seeds and case parameters intentionally do
    not appear here: changing them does not create a new family.
    """

    family_id: str
    construction_family_id: str
    implementation_id: str
    implementation_version: str
    source_sha256: str
    schema_version: str = GENERATOR_FAMILY_IDENTITY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != GENERATOR_FAMILY_IDENTITY_SCHEMA_VERSION:
            raise GeneratorFamilyContractError(
                "unsupported generator-family identity schema"
            )
        for name in (
            "family_id",
            "construction_family_id",
            "implementation_id",
            "implementation_version",
        ):
            _slug(getattr(self, name), label=name)
        _sha256(self.source_sha256, label="source_sha256")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "family_id": self.family_id,
            "construction_family_id": self.construction_family_id,
            "implementation_id": self.implementation_id,
            "implementation_version": self.implementation_version,
            "source_sha256": self.source_sha256,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @property
    def canonical_sha256(self) -> str:
        return canonical_json_sha256(self.to_dict())

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, object],
    ) -> GeneratorFamilyIdentity:
        if not isinstance(value, Mapping) or any(
            not isinstance(key, str) for key in value
        ):
            raise GeneratorFamilyContractError(
                "generator-family identity must be a string-keyed mapping"
            )
        expected = {
            "schema_version",
            "family_id",
            "construction_family_id",
            "implementation_id",
            "implementation_version",
            "source_sha256",
        }
        actual = set(value)
        if actual != expected:
            raise GeneratorFamilyContractError(
                "generator-family identity fields differ from the contract: "
                f"missing={sorted(expected - actual)}, "
                f"unknown={sorted(actual - expected)}"
            )
        for name in (
            "schema_version",
            "family_id",
            "construction_family_id",
            "implementation_id",
            "implementation_version",
            "source_sha256",
        ):
            if not isinstance(value[name], str):
                raise GeneratorFamilyContractError(f"{name} must be a string")
        return cls(
            schema_version=value["schema_version"],
            family_id=value["family_id"],
            construction_family_id=value["construction_family_id"],
            implementation_id=value["implementation_id"],
            implementation_version=value["implementation_version"],
            source_sha256=value["source_sha256"],
        )


SpecValue_contra = TypeVar("SpecValue_contra", contravariant=True)
GeneratedValue_co = TypeVar("GeneratedValue_co", covariant=True)


@runtime_checkable
class GeneratorProtocol(Protocol[SpecValue_contra, GeneratedValue_co]):
    """Structural interface shared by separately declared generators."""

    @property
    def family_identity(self) -> GeneratorFamilyIdentity:
        """Return the source-bound construction-family identity."""

    def generate(self, spec: SpecValue_contra) -> GeneratedValue_co:
        """Generate one deterministic typed synthetic product."""


def representation_phantom_family_identity(
    *,
    source_sha256: str,
) -> GeneratorFamilyIdentity:
    """Bind the existing probe-response phantom as one construction family.

    The caller supplies the exact source digest already bound by the tracked
    representation-phantom protocol.  This adapter adds no new execution path
    and does not reinterpret the existing phantom's frozen outputs.
    """

    return GeneratorFamilyIdentity(
        family_id="representation-probe-response-v0.1",
        construction_family_id="probe-response-local-covariance-lattice",
        implementation_id="numpy-probe-response-lattice",
        implementation_version="v0.1",
        source_sha256=source_sha256,
    )


def require_distinct_construction_families(
    identities: tuple[GeneratorFamilyIdentity, ...],
    *,
    minimum_family_count: int = 2,
) -> None:
    """Require genuinely distinct declared constructions.

    This is a necessary metadata check, not proof of scientific independence.
    In particular, changing only a seed, source digest, implementation label,
    or family display name cannot pass when the construction-family identifier
    remains the same.
    """

    if not isinstance(identities, tuple):
        raise TypeError("identities must be a tuple")
    if (
        isinstance(minimum_family_count, bool)
        or not isinstance(minimum_family_count, int)
        or minimum_family_count < 2
    ):
        raise ValueError("minimum_family_count must be an integer of at least two")
    if len(identities) < minimum_family_count:
        raise GeneratorFamilyContractError(
            "too few generator families for the declared comparison"
        )
    if any(not isinstance(item, GeneratorFamilyIdentity) for item in identities):
        raise TypeError("identities must contain only GeneratorFamilyIdentity values")

    family_ids = tuple(item.family_id for item in identities)
    if len(set(family_ids)) != len(family_ids):
        raise GeneratorFamilyContractError(
            "generator family identifiers must be unique"
        )
    construction_ids = tuple(item.construction_family_id for item in identities)
    if len(set(construction_ids)) != len(construction_ids):
        raise GeneratorFamilyContractError(
            "distinct seeds, sources, or implementations do not establish "
            "distinct construction families"
        )
    implementation_ids = tuple(item.implementation_id for item in identities)
    if len(set(implementation_ids)) != len(implementation_ids):
        raise GeneratorFamilyContractError(
            "distinct construction families require distinct implementations"
        )
