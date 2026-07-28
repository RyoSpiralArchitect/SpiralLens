"""Provisional pointwise referents for F0--F4.

The namespace provides model-free contracts and numeric relations only.
Synthetic correctness does not establish a model-side, semantic, physical,
or topological referent and does not authorize subject access.
"""

from .common import (
    ChargeConvention,
    DirectionRule,
    FitEvaluationRule,
    GaugeGroup,
    ReferentContractError,
    ReferentKind,
    TransformationLaw,
)
from .contracts import (
    CANONICAL_REFERENT_CONTRACT_SET_ID,
    REFERENT_CONTRACT_SET_SCHEMA_VERSION,
    SYNTHETIC_CONSTRUCT_VALIDITY_SCOPE,
    ReferentContractSet,
    ReferentDefinition,
    canonical_f0_f4_referent_contracts,
)
from .loader import (
    MAX_REFERENT_CONTRACT_SET_BYTES,
    LoadedReferentContractSet,
    load_referent_contract_set,
)
from .numeric import (
    ObservationPartition,
    SectionObservation,
    SpinTwoObservation,
    derive_f2_section,
    derive_f3_section,
    derive_f4_spin_two,
    validate_observation_partition,
)

__all__ = [
    "CANONICAL_REFERENT_CONTRACT_SET_ID",
    "MAX_REFERENT_CONTRACT_SET_BYTES",
    "REFERENT_CONTRACT_SET_SCHEMA_VERSION",
    "SYNTHETIC_CONSTRUCT_VALIDITY_SCOPE",
    "ChargeConvention",
    "DirectionRule",
    "FitEvaluationRule",
    "GaugeGroup",
    "LoadedReferentContractSet",
    "ObservationPartition",
    "ReferentContractError",
    "ReferentContractSet",
    "ReferentDefinition",
    "ReferentKind",
    "SectionObservation",
    "SpinTwoObservation",
    "TransformationLaw",
    "canonical_f0_f4_referent_contracts",
    "derive_f2_section",
    "derive_f3_section",
    "derive_f4_spin_two",
    "load_referent_contract_set",
    "validate_observation_partition",
]
