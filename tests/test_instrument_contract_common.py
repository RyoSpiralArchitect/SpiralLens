from __future__ import annotations

from dataclasses import replace
import hashlib

import pytest

from spirallens.instrument_contracts.canonical import (
    CanonicalJsonError,
    canonical_json_bytes,
    canonical_json_sha256,
    parse_canonical_json,
    sha256_bytes,
)
from spirallens.instrument_contracts.common import (
    ARTIFACT_SCHEMA_VERSION_BY_TYPE,
    ArtifactRef,
    ArtifactType,
    ClaimLevel,
    ContractValidationError,
    EvolutionAxis,
    FitRole,
    GateState,
    HypothesisDisposition,
    HypothesisId,
    NeighborhoodMode,
    PayloadKind,
    PayloadRef,
    ResolutionState,
    RuleChoice,
    ScientificBranch,
    enum_from_value,
    exact_keys,
    require_mapping,
    require_plain_int,
    require_sha256,
    require_slug,
)


SHA_A = "a" * 64
SHA_B = "b" * 64


def test_canonical_json_is_sorted_compact_utf8_without_newline() -> None:
    value = {
        "z": ["渦", 3],
        "a": {"truth": True, "nothing": None},
    }

    encoded = canonical_json_bytes(value)

    assert encoded == (
        b'{"a":{"nothing":null,"truth":true},"z":["'
        + "渦".encode("utf-8")
        + b'",3]}'
    )
    assert not encoded.endswith(b"\n")
    assert parse_canonical_json(encoded) == value
    assert canonical_json_sha256(value) == hashlib.sha256(
        encoded
    ).hexdigest()
    assert sha256_bytes(encoded) == canonical_json_sha256(value)


@pytest.mark.parametrize(
    "source",
    (
        b'{"b":1,"a":2}',
        b'{"a": 2,"b":1}',
        b'{"a":2,"b":1}\n',
        b'{"text":"\\u6e26"}',
        b'{"number":1e0}',
    ),
)
def test_parser_rejects_noncanonical_json_bytes(source: bytes) -> None:
    with pytest.raises(CanonicalJsonError, match="not canonical"):
        parse_canonical_json(source)


@pytest.mark.parametrize(
    "source",
    (
        b'{"value":1,"value":2}',
        b'{"outer":{"value":1,"value":2}}',
    ),
)
def test_parser_rejects_duplicate_keys_at_every_depth(
    source: bytes,
) -> None:
    with pytest.raises(CanonicalJsonError, match="duplicate JSON key"):
        parse_canonical_json(source)


@pytest.mark.parametrize(
    "value",
    (float("nan"), float("inf"), float("-inf"), -0.0),
)
def test_encoder_rejects_nonfinite_and_negative_zero(value: float) -> None:
    with pytest.raises(CanonicalJsonError):
        canonical_json_bytes({"value": value})


@pytest.mark.parametrize(
    "source",
    (
        b'{"value":NaN}',
        b'{"value":Infinity}',
        b'{"value":-Infinity}',
        b'{"value":1e999}',
        b'{"value":-0.0}',
    ),
)
def test_parser_rejects_nonfinite_and_negative_zero(
    source: bytes,
) -> None:
    with pytest.raises(CanonicalJsonError):
        parse_canonical_json(source)


def test_canonical_json_rejects_non_json_types_and_cycles() -> None:
    with pytest.raises(CanonicalJsonError, match="unsupported"):
        canonical_json_bytes({"tuple": (1, 2)})
    with pytest.raises(CanonicalJsonError, match="keys must be strings"):
        canonical_json_bytes({1: "value"})

    cyclic: list[object] = []
    cyclic.append(cyclic)
    with pytest.raises(CanonicalJsonError, match="cycle"):
        canonical_json_bytes(cyclic)


def test_exact_key_and_scalar_validators_fail_closed() -> None:
    document = require_mapping({"a": 1}, label="fixture")
    exact_keys(document, {"a"}, label="fixture")

    with pytest.raises(ContractValidationError, match="unknown"):
        exact_keys({"a": 1, "extra": 2}, {"a"}, label="fixture")
    with pytest.raises(ContractValidationError, match="missing"):
        exact_keys({}, {"a"}, label="fixture")
    with pytest.raises(ContractValidationError, match="keys"):
        require_mapping({1: "bad"}, label="fixture")
    with pytest.raises(ContractValidationError, match="integer"):
        require_plain_int(True, label="count")
    with pytest.raises(ContractValidationError, match="match"):
        require_slug("Not Canonical", label="artifact_id")
    with pytest.raises(ContractValidationError, match="SHA-256"):
        require_sha256("A" * 64, label="digest")


def test_closed_enum_values_are_exact() -> None:
    assert {item.value for item in HypothesisId} == {
        "f0_support",
        "f1_projector_connection",
        "f2_local_covariant_section",
        "f3_global_plane_section",
        "f4_spin_two_anisotropy",
    }
    assert {item.value for item in ScientificBranch} == {
        "support",
        "geometry",
        "defect",
    }
    assert {item.value for item in ClaimLevel} == {
        "level_0",
        "level_1g",
        "level_1d",
        "level_2g",
        "level_2t",
        "level_3",
    }
    assert {item.value for item in EvolutionAxis} == {
        "synthetic_lattice",
        "token_position",
        "layer_index",
        "training_step",
    }
    assert {item.value for item in FitRole} == {
        "instrument_dev",
        "calibration_selection",
        "calibration_confirmation",
        "subject_discovery",
        "subject_confirmation",
    }
    assert {item.value for item in ResolutionState} == {
        "fixed_by_hypothesis",
        "calibration_selection",
        "calibration_resolved",
        "disabled",
        "not_applicable",
    }
    assert {item.value for item in NeighborhoodMode} == {
        "graph_free",
        "inherit_field_estimation_graph",
        "explicit_core_graph",
    }
    assert {item.value for item in HypothesisDisposition} == {
        "advance",
        "retain_diagnostic",
        "reject",
    }
    assert {item.value for item in GateState} == {
        "pass",
        "fail",
        "insufficient",
        "not_run",
    }
    assert len(ArtifactType) == 17
    assert ArtifactType.HYPOTHESIS_REGISTRY.value == "hypothesis_registry"
    assert ArtifactType.CONTEXT_BANK.value == "context_bank"

    with pytest.raises(ContractValidationError, match="must be one of"):
        enum_from_value(
            ClaimLevel,
            "level_2",
            label="claim_level",
        )


def test_rule_choice_round_trip_for_every_resolution_state() -> None:
    choices = (
        RuleChoice(
            family_id="target_rank",
            resolution=ResolutionState.FIXED_BY_HYPOTHESIS,
            selected_id="rank_two",
        ),
        RuleChoice(
            family_id="covariance_estimator",
            resolution=ResolutionState.CALIBRATION_SELECTION,
            candidate_ids=("empirical", "shrinkage"),
        ),
        RuleChoice(
            family_id="covariance_estimator",
            resolution=ResolutionState.CALIBRATION_RESOLVED,
            selected_id="shrinkage",
        ),
        RuleChoice(
            family_id="integer_output",
            resolution=ResolutionState.DISABLED,
        ),
        RuleChoice(
            family_id="charge_group",
            resolution=ResolutionState.NOT_APPLICABLE,
        ),
    )

    for choice in choices:
        restored = RuleChoice.from_dict(choice.to_dict())
        assert restored == choice
        assert restored.canonical_bytes == canonical_json_bytes(
            choice.to_dict()
        )
        assert restored.identity_sha256 == canonical_json_sha256(
            choice.to_dict()
        )


@pytest.mark.parametrize(
    "choice",
    (
        RuleChoice,
    ),
)
def test_rule_choice_class_is_importable(choice: type[RuleChoice]) -> None:
    assert choice is RuleChoice


def test_rule_choice_enforces_exclusive_resolution_payloads() -> None:
    with pytest.raises(
        ContractValidationError,
        match="requires selected_id",
    ):
        RuleChoice(
            family_id="rank",
            resolution=ResolutionState.FIXED_BY_HYPOTHESIS,
        )
    with pytest.raises(
        ContractValidationError,
        match="requires candidate_ids",
    ):
        RuleChoice(
            family_id="rank",
            resolution=ResolutionState.CALIBRATION_SELECTION,
        )
    with pytest.raises(
        ContractValidationError,
        match="mutually exclusive",
    ):
        RuleChoice(
            family_id="rank",
            resolution=ResolutionState.CALIBRATION_SELECTION,
            selected_id="rank_two",
            candidate_ids=("rank_three",),
        )
    with pytest.raises(
        ContractValidationError,
        match="cannot select candidates",
    ):
        RuleChoice(
            family_id="rank",
            resolution=ResolutionState.DISABLED,
            selected_id="rank_two",
        )
    with pytest.raises(
        ContractValidationError,
        match="unique and sorted",
    ):
        RuleChoice(
            family_id="rank",
            resolution=ResolutionState.CALIBRATION_SELECTION,
            candidate_ids=("rank_two", "rank_one"),
        )
    with pytest.raises(
        ContractValidationError,
        match="unique and sorted",
    ):
        RuleChoice(
            family_id="rank",
            resolution=ResolutionState.CALIBRATION_SELECTION,
            candidate_ids=("rank_two", "rank_two"),
        )


def test_rule_choice_rejects_schema_drift() -> None:
    value = RuleChoice(
        family_id="rank",
        resolution=ResolutionState.FIXED_BY_HYPOTHESIS,
        selected_id="rank_two",
    ).to_dict()

    with pytest.raises(ContractValidationError, match="unknown"):
        RuleChoice.from_dict({**value, "meaning": "forbidden"})
    without_field = dict(value)
    without_field.pop("candidate_ids")
    with pytest.raises(ContractValidationError, match="missing"):
        RuleChoice.from_dict(without_field)


def test_artifact_reference_round_trip_and_identity_digest() -> None:
    reference = ArtifactRef(
        artifact_type=ArtifactType.ORDER_PARAMETER_SPEC,
        schema_version=ARTIFACT_SCHEMA_VERSION_BY_TYPE[
            ArtifactType.ORDER_PARAMETER_SPEC
        ],
        artifact_id="f2-dev-spec",
        canonical_sha256=SHA_A,
    )

    assert ArtifactRef.from_dict(reference.to_dict()) == reference
    assert reference.identity_sha256 == hashlib.sha256(
        reference.canonical_bytes
    ).hexdigest()
    assert replace(
        reference,
        canonical_sha256=SHA_B,
    ).identity_sha256 != reference.identity_sha256

    with pytest.raises(ContractValidationError, match="unknown"):
        ArtifactRef.from_dict({**reference.to_dict(), "label": "leak"})

    with pytest.raises(
        ContractValidationError,
        match="does not match artifact_type",
    ):
        replace(
            reference,
            schema_version=ARTIFACT_SCHEMA_VERSION_BY_TYPE[
                ArtifactType.CORE_SCORE
            ],
        )


def test_payload_references_round_trip_for_every_kind() -> None:
    values = (
        PayloadRef(
            kind=PayloadKind.ARRAY,
            sha256=SHA_A,
            byte_length=128,
            media_type="application/x-npy",
            dtype="<f4",
            shape=(4, 8),
            row_identity_sha256=SHA_B,
        ),
        PayloadRef(
            kind=PayloadKind.TABLE,
            sha256=SHA_A,
            byte_length=64,
            media_type="application/vnd.apache.parquet",
            record_count=4,
            row_identity_sha256=SHA_B,
        ),
        PayloadRef(
            kind=PayloadKind.JSON_RECORDS,
            sha256=SHA_A,
            byte_length=32,
            media_type="application/x-ndjson",
            record_count=0,
        ),
        PayloadRef(
            kind=PayloadKind.OPAQUE,
            sha256=SHA_A,
            byte_length=8,
            media_type="application/octet-stream",
        ),
    )

    for value in values:
        restored = PayloadRef.from_dict(value.to_dict())
        assert restored == value
        assert restored.identity_sha256 == hashlib.sha256(
            restored.canonical_bytes
        ).hexdigest()


def test_payload_reference_enforces_kind_specific_metadata() -> None:
    common = {
        "sha256": SHA_A,
        "byte_length": 8,
        "media_type": "application/octet-stream",
    }
    with pytest.raises(ContractValidationError, match="dtype and shape"):
        PayloadRef(
            kind=PayloadKind.ARRAY,
            dtype="<f4",
            **common,
        )
    with pytest.raises(ContractValidationError, match="require dtype"):
        PayloadRef(kind=PayloadKind.ARRAY, **common)
    with pytest.raises(ContractValidationError, match="record_count"):
        PayloadRef(kind=PayloadKind.TABLE, **common)
    with pytest.raises(ContractValidationError, match="forbid dtype"):
        PayloadRef(
            kind=PayloadKind.JSON_RECORDS,
            dtype="<f4",
            shape=(1,),
            record_count=1,
            **common,
        )
    with pytest.raises(ContractValidationError, match="structured"):
        PayloadRef(
            kind=PayloadKind.OPAQUE,
            row_identity_sha256=SHA_B,
            **common,
        )
    with pytest.raises(
        ContractValidationError,
        match="row_identity_sha256",
    ):
        PayloadRef(
            kind=PayloadKind.ARRAY,
            dtype="<f4",
            shape=(1,),
            **common,
        )
    with pytest.raises(
        ContractValidationError,
        match="row_identity_sha256",
    ):
        PayloadRef(
            kind=PayloadKind.TABLE,
            record_count=1,
            **common,
        )
    with pytest.raises(ContractValidationError, match="integer"):
        PayloadRef(
            kind=PayloadKind.OPAQUE,
            byte_length=True,
            sha256=SHA_A,
            media_type="application/octet-stream",
        )


@pytest.mark.parametrize(
    "dtype",
    (
        "float32",
        "f4",
        "=f4",
        "O",
        "|O",
    ),
)
def test_array_payload_requires_canonical_safe_explicit_dtype(
    dtype: str,
) -> None:
    with pytest.raises(
        ContractValidationError,
        match="canonical explicit-endian",
    ):
        PayloadRef(
            kind=PayloadKind.ARRAY,
            sha256=SHA_A,
            byte_length=16,
            media_type="application/x-npy",
            dtype=dtype,
            shape=(2,),
            row_identity_sha256=SHA_B,
        )


def test_payload_reference_rejects_noncanonical_shape_and_fields() -> None:
    value = PayloadRef(
        kind=PayloadKind.ARRAY,
        sha256=SHA_A,
        byte_length=16,
        media_type="application/x-npy",
        dtype="<f8",
        shape=(2,),
        row_identity_sha256=SHA_B,
    ).to_dict()

    with pytest.raises(ContractValidationError, match="unknown"):
        PayloadRef.from_dict({**value, "semantic_label": "forbidden"})
    with pytest.raises(ContractValidationError, match="list"):
        PayloadRef.from_dict({**value, "shape": (2,)})
    with pytest.raises(ContractValidationError, match="integer"):
        PayloadRef.from_dict({**value, "shape": [True]})


def test_payload_reference_binds_kind_media_and_minimum_array_bytes() -> None:
    with pytest.raises(ContractValidationError, match="media_type"):
        PayloadRef(
            kind=PayloadKind.ARRAY,
            sha256=SHA_A,
            byte_length=128,
            media_type="image/png",
            dtype="<f4",
            shape=(4, 8),
            row_identity_sha256=SHA_B,
        )
    with pytest.raises(ContractValidationError, match="smaller"):
        PayloadRef(
            kind=PayloadKind.ARRAY,
            sha256=SHA_A,
            byte_length=1,
            media_type="application/x-npy",
            dtype="<f8",
            shape=(1_000_000,),
            row_identity_sha256=SHA_B,
        )
