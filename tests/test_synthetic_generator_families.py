from __future__ import annotations

from dataclasses import replace

import pytest

from spirallens.synthetic import (
    GeneratorFamilyContractError,
    GeneratorFamilyIdentity,
    GeneratorProtocol,
    SpectralMomentGenerator,
    representation_phantom_family_identity,
    require_distinct_construction_families,
)


def _identity(
    *,
    family_id: str,
    construction_family_id: str,
    implementation_id: str,
    source_character: str,
) -> GeneratorFamilyIdentity:
    return GeneratorFamilyIdentity(
        family_id=family_id,
        construction_family_id=construction_family_id,
        implementation_id=implementation_id,
        implementation_version="v0.1",
        source_sha256=source_character * 64,
    )


def test_generator_family_identity_is_canonical_and_closed() -> None:
    identity = _identity(
        family_id="spectral",
        construction_family_id="spectral-moment-quadrature",
        implementation_id="fourier-quadrature",
        source_character="a",
    )

    assert GeneratorFamilyIdentity.from_dict(identity.to_dict()) == identity
    assert len(identity.canonical_sha256) == 64
    unknown = {**identity.to_dict(), "seed": 1729}
    with pytest.raises(GeneratorFamilyContractError, match="unknown"):
        GeneratorFamilyIdentity.from_dict(unknown)


def test_seed_or_source_changes_cannot_fake_a_distinct_construction() -> None:
    first = _identity(
        family_id="family-a",
        construction_family_id="same-construction",
        implementation_id="implementation-a",
        source_character="a",
    )
    relabelled = _identity(
        family_id="family-b",
        construction_family_id="same-construction",
        implementation_id="implementation-b",
        source_character="b",
    )

    with pytest.raises(
        GeneratorFamilyContractError,
        match="seeds, sources, or implementations",
    ):
        require_distinct_construction_families((first, relabelled))

    source_only = replace(
        relabelled,
        construction_family_id="same-construction",
        source_sha256="c" * 64,
    )
    with pytest.raises(GeneratorFamilyContractError):
        require_distinct_construction_families((first, source_only))


def test_distinct_construction_and_implementation_are_both_required() -> None:
    first = _identity(
        family_id="family-a",
        construction_family_id="construction-a",
        implementation_id="shared-implementation",
        source_character="a",
    )
    second = _identity(
        family_id="family-b",
        construction_family_id="construction-b",
        implementation_id="shared-implementation",
        source_character="b",
    )
    with pytest.raises(
        GeneratorFamilyContractError,
        match="distinct implementations",
    ):
        require_distinct_construction_families((first, second))

    distinct = replace(second, implementation_id="implementation-b")
    require_distinct_construction_families((first, distinct))


def test_existing_and_spectral_constructions_form_a_distinct_pair() -> None:
    representation = representation_phantom_family_identity(
        source_sha256="a" * 64,
    )
    spectral = SpectralMomentGenerator().family_identity

    require_distinct_construction_families((representation, spectral))
    assert representation.construction_family_id != (spectral.construction_family_id)


def test_spectral_generator_conforms_to_typed_protocol() -> None:
    assert isinstance(SpectralMomentGenerator(), GeneratorProtocol)
