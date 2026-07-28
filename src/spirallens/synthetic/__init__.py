"""Level-0 representation-shaped development substrates and bundles.

This experimental namespace produces model-free software-correctness
fixtures.  Its outputs are not synthetic-qualified scientific instruments and
do not authorize subject access.
"""

from .generators import (
    GENERATOR_FAMILY_IDENTITY_SCHEMA_VERSION,
    GeneratorFamilyContractError,
    GeneratorFamilyIdentity,
    GeneratorProtocol,
    representation_phantom_family_identity,
    require_distinct_construction_families,
)
from .phantom_bundle import (
    EmittedRepresentationPhantomBundle,
    RepresentationPhantomBundleError,
    emit_representation_phantom_bundle,
)
from .protocol import (
    REPRESENTATION_PHANTOM_PROTOCOL_SCHEMA_VERSION,
    LoadedRepresentationPhantomProtocol,
    RepresentationPhantomProtocol,
    RepresentationPhantomProtocolError,
    RepresentationPhantomProtocolIntegrityError,
    RepresentationPhantomProtocolSchemaError,
    load_representation_phantom_protocol,
)
from .representation_phantom import (
    ANGULAR_SECTION_POSITIVE,
    FIXED_DIRECTION_NULL,
    PhantomCase,
    RepresentationPhantom,
    RepresentationPhantomSpec,
)
from .spectral_moment_phantom import (
    SPECTRAL_MOMENT_FIXED_NULL,
    SPECTRAL_MOMENT_PHANTOM_RECEIPT_VERSION,
    SPECTRAL_MOMENT_POSITIVE,
    SPECTRAL_MOMENT_PREREQUISITE_FAILURE,
    ExpectedControlDisposition,
    SpectralMomentCase,
    SpectralMomentEstimatorInputs,
    SpectralMomentGenerator,
    SpectralMomentOracleTruth,
    SpectralMomentPhantom,
    SpectralMomentPhantomSpec,
)

__all__ = [
    "ANGULAR_SECTION_POSITIVE",
    "FIXED_DIRECTION_NULL",
    "GENERATOR_FAMILY_IDENTITY_SCHEMA_VERSION",
    "REPRESENTATION_PHANTOM_PROTOCOL_SCHEMA_VERSION",
    "SPECTRAL_MOMENT_FIXED_NULL",
    "SPECTRAL_MOMENT_PHANTOM_RECEIPT_VERSION",
    "SPECTRAL_MOMENT_POSITIVE",
    "SPECTRAL_MOMENT_PREREQUISITE_FAILURE",
    "EmittedRepresentationPhantomBundle",
    "ExpectedControlDisposition",
    "GeneratorFamilyContractError",
    "GeneratorFamilyIdentity",
    "GeneratorProtocol",
    "LoadedRepresentationPhantomProtocol",
    "PhantomCase",
    "RepresentationPhantom",
    "RepresentationPhantomBundleError",
    "RepresentationPhantomProtocol",
    "RepresentationPhantomProtocolError",
    "RepresentationPhantomProtocolIntegrityError",
    "RepresentationPhantomProtocolSchemaError",
    "RepresentationPhantomSpec",
    "SpectralMomentCase",
    "SpectralMomentEstimatorInputs",
    "SpectralMomentGenerator",
    "SpectralMomentOracleTruth",
    "SpectralMomentPhantom",
    "SpectralMomentPhantomSpec",
    "emit_representation_phantom_bundle",
    "load_representation_phantom_protocol",
    "representation_phantom_family_identity",
    "require_distinct_construction_families",
]
