"""Fail-closed YAML loading for the outcome-excluded P0 registry."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import yaml

from spirallens.core._strict_yaml import make_strict_safe_loader

from .canonical import sha256_bytes
from .common import (
    ClaimLevel,
    ContractValidationError,
    HypothesisId,
    RuleChoice,
    ScientificBranch,
    enum_from_value,
    exact_keys,
    require_bool,
    require_mapping,
    require_sha256,
    require_slug,
    require_string,
    string_tuple_from_list,
)
from .registry import (
    HYPOTHESIS_REGISTRY_SCHEMA_VERSION,
    HistoricalSelectionBoundary,
    HypothesisRegistry,
    HypothesisRegistryError,
    HypothesisRegistryPolicyError,
    HypothesisSpec,
    validate_p0_registry,
)


MAX_HYPOTHESIS_REGISTRY_BYTES = 1_048_576


class HypothesisRegistrySchemaError(HypothesisRegistryError):
    """Raised when registry YAML is ambiguous or outside the schema."""


class HypothesisRegistryIntegrityError(HypothesisRegistryError):
    """Raised when source or canonical content has an unexpected digest."""


_StrictSafeLoader = make_strict_safe_loader(HypothesisRegistrySchemaError)


@dataclass(frozen=True, slots=True)
class LoadedHypothesisRegistry:
    """A validated registry plus source-byte and canonical identities."""

    registry: HypothesisRegistry
    source_path: Path
    source_sha256: str
    canonical_sha256: str


_ROOT_KEYS = {
    "schema_version",
    "registry_id",
    "status",
    "policy_version",
    "historical_boundary",
    "real_model_claim_state",
    "winner_selected",
    "primary_integer_output_authorized",
    "subject_data_access_authorized",
    "hypotheses",
}
_BOUNDARY_KEYS = {
    "historical_snapshot_id",
    "historical_cutoff_commit",
    "historical_outcome_integration_commit",
    "historical_outcome_record_path",
    "historical_outcome_record_source_sha256",
    "historical_outcome_artifact_source_sha256",
    "registry_postdates_prior_outcome",
    "prior_outcome_allowed_for_selection",
    "allowed_selection_evidence",
    "forbidden_selection_inputs",
}
_HYPOTHESIS_KEYS = {
    "hypothesis_id",
    "branch",
    "current_claim_level",
    "claim_ceiling",
    "input_tensor",
    "observation_axis",
    "centering_rule",
    "residual_rule",
    "architecture_accounting_rule",
    "estimator",
    "fit_role",
    "domain_binding",
    "substrate_binding",
    "rank_convention",
    "gauge_law",
    "target_manifold",
    "charge_group",
    "amplitude_quantity",
    "support_quantities",
    "identifiability_quantities",
    "interpolation_rule",
    "lift_rule",
    "trivialization_rule",
    "reference_rule",
    "edge_connection_rule",
    "allowed_observables",
    "forbidden_labels",
    "required_controls",
    "winding_prerequisites",
    "failure_reasons",
    "integer_output_authorized",
}


def _reject_numeric_scalars(value: object, *, path: str = "$") -> None:
    """The P0 registry has no numerical observations, ranks, or thresholds."""

    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if isinstance(value, (int, float)):
        raise HypothesisRegistrySchemaError(f"{path} must not contain numeric values")
    if isinstance(value, Mapping):
        for key, item in value.items():
            _reject_numeric_scalars(item, path=f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_numeric_scalars(item, path=f"{path}[{index}]")


def _parse_boundary(value: object) -> HistoricalSelectionBoundary:
    boundary = require_mapping(value, label="historical_boundary")
    exact_keys(
        boundary,
        _BOUNDARY_KEYS,
        label="historical_boundary",
    )
    return HistoricalSelectionBoundary(
        historical_snapshot_id=require_slug(
            boundary["historical_snapshot_id"],
            label="historical_boundary.historical_snapshot_id",
        ),
        historical_cutoff_commit=require_string(
            boundary["historical_cutoff_commit"],
            label="historical_boundary.historical_cutoff_commit",
        ),
        historical_outcome_integration_commit=require_string(
            boundary["historical_outcome_integration_commit"],
            label=("historical_boundary.historical_outcome_integration_commit"),
        ),
        historical_outcome_record_path=require_string(
            boundary["historical_outcome_record_path"],
            label="historical_boundary.historical_outcome_record_path",
        ),
        historical_outcome_record_source_sha256=require_sha256(
            boundary["historical_outcome_record_source_sha256"],
            label=("historical_boundary.historical_outcome_record_source_sha256"),
        ),
        historical_outcome_artifact_source_sha256=require_sha256(
            boundary["historical_outcome_artifact_source_sha256"],
            label=("historical_boundary.historical_outcome_artifact_source_sha256"),
        ),
        registry_postdates_prior_outcome=require_bool(
            boundary["registry_postdates_prior_outcome"],
            label="historical_boundary.registry_postdates_prior_outcome",
        ),
        prior_outcome_allowed_for_selection=require_bool(
            boundary["prior_outcome_allowed_for_selection"],
            label="historical_boundary.prior_outcome_allowed_for_selection",
        ),
        allowed_selection_evidence=string_tuple_from_list(
            boundary["allowed_selection_evidence"],
            label="historical_boundary.allowed_selection_evidence",
            require_nonempty=True,
            require_canonical_order=True,
            require_slugs=True,
        ),
        forbidden_selection_inputs=string_tuple_from_list(
            boundary["forbidden_selection_inputs"],
            label="historical_boundary.forbidden_selection_inputs",
            require_nonempty=True,
            require_canonical_order=True,
            require_slugs=True,
        ),
    )


def _parse_hypothesis(value: object, *, index: int) -> HypothesisSpec:
    label = f"hypotheses[{index}]"
    item = require_mapping(value, label=label)
    exact_keys(item, _HYPOTHESIS_KEYS, label=label)

    def identifiers(name: str, *, allow_empty: bool = False) -> tuple[str, ...]:
        return string_tuple_from_list(
            item[name],
            label=f"{label}.{name}",
            require_nonempty=not allow_empty,
            require_canonical_order=True,
            require_slugs=True,
        )

    def choice(name: str) -> RuleChoice:
        raw = require_mapping(item[name], label=f"{label}.{name}")
        try:
            return RuleChoice.from_dict(raw)
        except ContractValidationError as error:
            raise HypothesisRegistrySchemaError(
                f"invalid {label}.{name}: {error}"
            ) from error

    return HypothesisSpec(
        hypothesis_id=enum_from_value(
            HypothesisId,
            item["hypothesis_id"],
            label=f"{label}.hypothesis_id",
        ),
        branch=enum_from_value(
            ScientificBranch,
            item["branch"],
            label=f"{label}.branch",
        ),
        current_claim_level=enum_from_value(
            ClaimLevel,
            item["current_claim_level"],
            label=f"{label}.current_claim_level",
        ),
        claim_ceiling=enum_from_value(
            ClaimLevel,
            item["claim_ceiling"],
            label=f"{label}.claim_ceiling",
        ),
        input_tensor=choice("input_tensor"),
        observation_axis=choice("observation_axis"),
        centering_rule=choice("centering_rule"),
        residual_rule=choice("residual_rule"),
        architecture_accounting_rule=choice("architecture_accounting_rule"),
        estimator=choice("estimator"),
        fit_role=choice("fit_role"),
        domain_binding=require_slug(
            item["domain_binding"], label=f"{label}.domain_binding"
        ),
        substrate_binding=require_slug(
            item["substrate_binding"], label=f"{label}.substrate_binding"
        ),
        rank_convention=require_slug(
            item["rank_convention"], label=f"{label}.rank_convention"
        ),
        gauge_law=require_slug(item["gauge_law"], label=f"{label}.gauge_law"),
        target_manifold=require_slug(
            item["target_manifold"], label=f"{label}.target_manifold"
        ),
        charge_group=require_slug(item["charge_group"], label=f"{label}.charge_group"),
        amplitude_quantity=require_slug(
            item["amplitude_quantity"], label=f"{label}.amplitude_quantity"
        ),
        support_quantities=identifiers("support_quantities"),
        identifiability_quantities=identifiers("identifiability_quantities"),
        interpolation_rule=choice("interpolation_rule"),
        lift_rule=choice("lift_rule"),
        trivialization_rule=choice("trivialization_rule"),
        reference_rule=choice("reference_rule"),
        edge_connection_rule=require_slug(
            item["edge_connection_rule"],
            label=f"{label}.edge_connection_rule",
        ),
        allowed_observables=identifiers("allowed_observables"),
        forbidden_labels=identifiers("forbidden_labels"),
        required_controls=identifiers("required_controls"),
        winding_prerequisites=identifiers(
            "winding_prerequisites",
            allow_empty=True,
        ),
        failure_reasons=identifiers("failure_reasons"),
        integer_output_authorized=require_bool(
            item["integer_output_authorized"],
            label=f"{label}.integer_output_authorized",
        ),
    )


def hypothesis_registry_from_dict(
    value: Mapping[str, object],
) -> HypothesisRegistry:
    """Parse one exact registry mapping without applying P0 policy."""

    try:
        document = require_mapping(value, label="hypothesis registry")
        exact_keys(document, _ROOT_KEYS, label="hypothesis registry")
        schema_version = require_string(
            document["schema_version"], label="schema_version"
        )
        if schema_version != HYPOTHESIS_REGISTRY_SCHEMA_VERSION:
            raise HypothesisRegistrySchemaError(
                f"unsupported hypothesis-registry schema {schema_version!r}"
            )
        raw_hypotheses = document["hypotheses"]
        if not isinstance(raw_hypotheses, list) or not raw_hypotheses:
            raise HypothesisRegistrySchemaError("hypotheses must be a non-empty list")
        return HypothesisRegistry(
            schema_version=schema_version,
            registry_id=require_slug(document["registry_id"], label="registry_id"),
            status=require_slug(document["status"], label="status"),
            policy_version=require_slug(
                document["policy_version"], label="policy_version"
            ),
            historical_boundary=_parse_boundary(document["historical_boundary"]),
            real_model_claim_state=enum_from_value(
                ClaimLevel,
                document["real_model_claim_state"],
                label="real_model_claim_state",
            ),
            winner_selected=require_bool(
                document["winner_selected"], label="winner_selected"
            ),
            primary_integer_output_authorized=require_bool(
                document["primary_integer_output_authorized"],
                label="primary_integer_output_authorized",
            ),
            subject_data_access_authorized=require_bool(
                document["subject_data_access_authorized"],
                label="subject_data_access_authorized",
            ),
            hypotheses=tuple(
                _parse_hypothesis(item, index=index)
                for index, item in enumerate(raw_hypotheses)
            ),
        )
    except HypothesisRegistrySchemaError:
        raise
    except (ContractValidationError, HypothesisRegistryError) as error:
        raise HypothesisRegistrySchemaError(
            f"invalid hypothesis registry: {error}"
        ) from error


def load_hypothesis_registry(
    path: str | Path,
    *,
    expected_source_sha256: str | None = None,
    expected_canonical_sha256: str | None = None,
) -> LoadedHypothesisRegistry:
    """Load one strict single-document YAML registry and apply P0 policy."""

    source_path = Path(path).resolve()
    with source_path.open("rb") as handle:
        raw = handle.read(MAX_HYPOTHESIS_REGISTRY_BYTES + 1)
    return _load_hypothesis_registry_from_bytes(
        raw,
        source_path=source_path,
        expected_source_sha256=expected_source_sha256,
        expected_canonical_sha256=expected_canonical_sha256,
    )


def _load_hypothesis_registry_from_bytes(
    raw: bytes,
    *,
    source_path: Path,
    expected_source_sha256: str | None = None,
    expected_canonical_sha256: str | None = None,
) -> LoadedHypothesisRegistry:
    """Validate already-opened registry bytes without reopening their path."""

    if len(raw) > MAX_HYPOTHESIS_REGISTRY_BYTES:
        raise HypothesisRegistrySchemaError(
            f"hypothesis registry exceeds {MAX_HYPOTHESIS_REGISTRY_BYTES} bytes"
        )
    source_sha256 = sha256_bytes(raw)
    if expected_source_sha256 is not None and source_sha256 != expected_source_sha256:
        raise HypothesisRegistryIntegrityError(
            "hypothesis-registry source SHA-256 does not match expected digest"
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise HypothesisRegistrySchemaError(
            "hypothesis registry must be UTF-8 YAML"
        ) from error
    try:
        document = yaml.load(text, Loader=_StrictSafeLoader)
    except HypothesisRegistrySchemaError:
        raise
    except yaml.YAMLError as error:
        raise HypothesisRegistrySchemaError(
            f"invalid hypothesis-registry YAML: {error}"
        ) from error

    _reject_numeric_scalars(document)
    if not isinstance(document, Mapping):
        raise HypothesisRegistrySchemaError("hypothesis registry must be a mapping")
    registry = hypothesis_registry_from_dict(document)
    try:
        validate_p0_registry(registry)
    except HypothesisRegistryPolicyError:
        raise
    canonical_sha256 = registry.canonical_sha256
    if (
        expected_canonical_sha256 is not None
        and canonical_sha256 != expected_canonical_sha256
    ):
        raise HypothesisRegistryIntegrityError(
            "hypothesis-registry canonical SHA-256 does not match expected digest"
        )
    return LoadedHypothesisRegistry(
        registry=registry,
        source_path=source_path,
        source_sha256=source_sha256,
        canonical_sha256=canonical_sha256,
    )
