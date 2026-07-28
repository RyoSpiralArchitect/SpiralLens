"""Framework-neutral access, provenance, and preparation contracts.

This package intentionally imports no model, atlas-storage, numerical, or
instrument-contract modules.  Observation producers depend on this package;
the access layer never depends on those producers.
"""

from __future__ import annotations

from .contracts import (
    ATLAS_PREPARATION_DESCRIPTOR_SCHEMA_VERSION,
    AtlasAccessContractError,
    AtlasAccessPolicy,
    AtlasConsumer,
    AtlasConsumerDenied,
    AtlasPreparationDescriptor,
    AttemptPolicy,
    CaptureDeclaration,
    ContextIdentity,
    InterpretationContract,
    ModelIdentity,
    ProtocolIdentity,
    ProvenanceEscalationError,
    ProvenanceTaint,
    RowDomainIdentity,
    require_atlas_consumer,
    restrict_atlas_access,
)
from .descriptor import (
    ATLAS_PREPARATION_VIEW_SCHEMA_VERSION,
    MAX_ATLAS_PREPARATION_DESCRIPTOR_BYTES,
    AtlasPreparationView,
    LoadedAtlasPreparationDescriptor,
    load_atlas_preparation_descriptor,
    prepare_descriptor_only_view,
    write_atlas_preparation_descriptor,
)
from .lifecycle import (
    ATTEMPT_TERMINAL_RECORD_SCHEMA_VERSION,
    AttemptAccessFacts,
    AttemptLifecycle,
    AttemptLifecycleError,
    AttemptPhase,
    AttemptTerminalRecord,
    AttemptTerminalState,
    QuarantineDisposition,
)
from .lineage import (
    VALUE_ACCESS_LINEAGE_SCHEMA_VERSION,
    ValueAccessLineage,
    ValueAccessTransition,
    bind_value_access_lineage,
    reverify_value_access_lineage,
)

__all__ = [
    "ATLAS_PREPARATION_DESCRIPTOR_SCHEMA_VERSION",
    "ATLAS_PREPARATION_VIEW_SCHEMA_VERSION",
    "ATTEMPT_TERMINAL_RECORD_SCHEMA_VERSION",
    "MAX_ATLAS_PREPARATION_DESCRIPTOR_BYTES",
    "VALUE_ACCESS_LINEAGE_SCHEMA_VERSION",
    "AtlasAccessContractError",
    "AtlasAccessPolicy",
    "AtlasConsumer",
    "AtlasConsumerDenied",
    "AtlasPreparationDescriptor",
    "AtlasPreparationView",
    "AttemptAccessFacts",
    "AttemptLifecycle",
    "AttemptLifecycleError",
    "AttemptPhase",
    "AttemptPolicy",
    "AttemptTerminalRecord",
    "AttemptTerminalState",
    "CaptureDeclaration",
    "ContextIdentity",
    "InterpretationContract",
    "LoadedAtlasPreparationDescriptor",
    "ModelIdentity",
    "ProtocolIdentity",
    "ProvenanceEscalationError",
    "ProvenanceTaint",
    "QuarantineDisposition",
    "RowDomainIdentity",
    "ValueAccessLineage",
    "ValueAccessTransition",
    "bind_value_access_lineage",
    "load_atlas_preparation_descriptor",
    "prepare_descriptor_only_view",
    "require_atlas_consumer",
    "restrict_atlas_access",
    "reverify_value_access_lineage",
    "write_atlas_preparation_descriptor",
]
