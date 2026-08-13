"""Streaming token-ID activation atlas construction."""

from __future__ import annotations

from importlib import import_module

from .engineering_protocol import (
    EngineeringConsumerAuthorizationError,
    LoadedPublicExamplePlumbingProtocol,
    PublicExamplePlumbingProtocolError,
    load_public_example_plumbing_protocol,
    require_engineering_consumer_authorized,
    validate_engineering_request_binding,
)
from .engineering_receipt import (
    PublicExamplePlumbingReceiptError,
    load_public_example_plumbing_receipt,
)
from .store import (
    ATLAS_SCHEMA_VERSION,
    AtlasIntegrityError,
    AtlasStateError,
    load_manifest,
    load_manifest_metadata,
)

__all__ = [
    "ATLAS_SCHEMA_VERSION",
    "ATLAS_CONTEXT_BINDING_SCHEMA_VERSION",
    "AtlasIntegrityError",
    "AtlasStateError",
    "ContextBankBinding",
    "EngineeringConsumerAuthorizationError",
    "LoadedPublicExamplePlumbingProtocol",
    "PublicExamplePlumbingProtocolError",
    "PublicExamplePlumbingReceiptError",
    "PublicExamplePlumbingRunError",
    "SweepConfig",
    "load_manifest",
    "load_manifest_metadata",
    "load_public_example_plumbing_protocol",
    "load_public_example_plumbing_receipt",
    "require_engineering_consumer_authorized",
    "run_id_sweep",
    "run_public_example_plumbing",
    "select_token_ids",
    "validate_engineering_request_binding",
]

_LAZY_EXPORTS = {
    "ATLAS_CONTEXT_BINDING_SCHEMA_VERSION": (
        ".id_sweep",
        "ATLAS_CONTEXT_BINDING_SCHEMA_VERSION",
    ),
    "ContextBankBinding": (".id_sweep", "ContextBankBinding"),
    "PublicExamplePlumbingRunError": (
        ".engineering_run",
        "PublicExamplePlumbingRunError",
    ),
    "SweepConfig": (".id_sweep", "SweepConfig"),
    "run_id_sweep": (".id_sweep", "run_id_sweep"),
    "run_public_example_plumbing": (".engineering_run", "run_public_example_plumbing"),
    "select_token_ids": (".id_sweep", "select_token_ids"),
}


def __getattr__(name: str) -> object:
    try:
        module_name, attribute_name = _LAZY_EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(import_module(module_name, __name__), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
