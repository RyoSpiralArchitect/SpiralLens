"""Level-0 representation-shaped development substrates and bundles.

This experimental namespace produces model-free software-correctness
fixtures.  Its outputs are not synthetic-qualified scientific instruments and
do not authorize subject access.
"""

from .protocol import (
    REPRESENTATION_PHANTOM_PROTOCOL_SCHEMA_VERSION,
    LoadedRepresentationPhantomProtocol,
    RepresentationPhantomProtocol,
    RepresentationPhantomProtocolError,
    RepresentationPhantomProtocolIntegrityError,
    RepresentationPhantomProtocolSchemaError,
    load_representation_phantom_protocol,
)
from .phantom_bundle import (
    EmittedRepresentationPhantomBundle,
    RepresentationPhantomBundleError,
    emit_representation_phantom_bundle,
)
from .representation_phantom import (
    ANGULAR_SECTION_POSITIVE,
    FIXED_DIRECTION_NULL,
    PhantomCase,
    RepresentationPhantom,
    RepresentationPhantomSpec,
)

__all__ = [
    "ANGULAR_SECTION_POSITIVE",
    "EmittedRepresentationPhantomBundle",
    "FIXED_DIRECTION_NULL",
    "REPRESENTATION_PHANTOM_PROTOCOL_SCHEMA_VERSION",
    "LoadedRepresentationPhantomProtocol",
    "PhantomCase",
    "RepresentationPhantom",
    "RepresentationPhantomBundleError",
    "RepresentationPhantomProtocol",
    "RepresentationPhantomProtocolError",
    "RepresentationPhantomProtocolIntegrityError",
    "RepresentationPhantomProtocolSchemaError",
    "RepresentationPhantomSpec",
    "emit_representation_phantom_bundle",
    "load_representation_phantom_protocol",
]
