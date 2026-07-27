from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path

import pytest
import yaml

from spirallens.instrument_contracts.artifacts import (
    _P0_CALIBRATION_SELECTIONS_BY_HYPOTHESIS,
    _P0_FIXED_SELECTIONS_BY_HYPOTHESIS,
)
from spirallens.instrument_contracts.common import (
    ClaimLevel,
    HypothesisId,
    ResolutionState,
)
from spirallens.instrument_contracts.registry import (
    HYPOTHESIS_REGISTRY_SCHEMA_VERSION,
    P0_HISTORICAL_CUTOFF_COMMIT,
    P0_HISTORICAL_OUTCOME_ARTIFACT_SOURCE_SHA256,
    P0_HISTORICAL_OUTCOME_INTEGRATION_COMMIT,
    P0_HISTORICAL_OUTCOME_RECORD_PATH,
    P0_HISTORICAL_OUTCOME_RECORD_SOURCE_SHA256,
    P0_HISTORICAL_SNAPSHOT_ID,
    HypothesisRegistryPolicyError,
    validate_p0_registry,
)
from spirallens.instrument_contracts.registry_loader import (
    MAX_HYPOTHESIS_REGISTRY_BYTES,
    HypothesisRegistryIntegrityError,
    HypothesisRegistrySchemaError,
    hypothesis_registry_from_dict,
    load_hypothesis_registry,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TRACKED_REGISTRY = (
    REPOSITORY_ROOT
    / "protocols/order_parameter_hypothesis_registry_v0_1.yaml"
)


def _document() -> dict[str, object]:
    value = yaml.safe_load(TRACKED_REGISTRY.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _write(
    tmp_path: Path,
    document: object,
    *,
    name: str = "registry.yaml",
    sort_keys: bool = False,
) -> Path:
    path = tmp_path / name
    path.write_text(
        yaml.safe_dump(document, sort_keys=sort_keys),
        encoding="utf-8",
    )
    return path


def _hypothesis(
    document: dict[str, object],
    hypothesis_id: str,
) -> dict[str, object]:
    hypotheses = document["hypotheses"]
    assert isinstance(hypotheses, list)
    for value in hypotheses:
        assert isinstance(value, dict)
        if value["hypothesis_id"] == hypothesis_id:
            return value
    raise AssertionError(hypothesis_id)


def test_tracked_registry_is_exact_outcome_excluded_f0_through_f4() -> None:
    loaded = load_hypothesis_registry(TRACKED_REGISTRY)
    registry = loaded.registry

    assert registry.schema_version == HYPOTHESIS_REGISTRY_SCHEMA_VERSION
    assert registry.status == "preparation"
    assert registry.real_model_claim_state is ClaimLevel.LEVEL_0
    assert registry.winner_selected is False
    assert registry.primary_integer_output_authorized is False
    assert registry.subject_data_access_authorized is False
    assert tuple(item.hypothesis_id for item in registry.hypotheses) == tuple(
        HypothesisId
    )
    assert registry.require(HypothesisId.F0_SUPPORT).claim_ceiling is ClaimLevel.LEVEL_1G
    assert registry.require(HypothesisId.F1_PROJECTOR_CONNECTION).claim_ceiling is ClaimLevel.LEVEL_2G
    assert registry.require(HypothesisId.F2_LOCAL_COVARIANT_SECTION).claim_ceiling is ClaimLevel.LEVEL_2T
    assert registry.require(HypothesisId.F3_GLOBAL_PLANE_SECTION).claim_ceiling is ClaimLevel.LEVEL_1D
    assert registry.require(HypothesisId.F4_SPIN_TWO_ANISOTROPY).claim_ceiling is ClaimLevel.LEVEL_2T
    assert all(
        item.current_claim_level is ClaimLevel.LEVEL_0
        and not item.integer_output_authorized
        for item in registry.hypotheses
    )
    assert loaded.source_sha256 == hashlib.sha256(
        TRACKED_REGISTRY.read_bytes()
    ).hexdigest()
    assert loaded.canonical_sha256 == registry.canonical_sha256
    assert len(loaded.canonical_sha256) == 64
    assert hypothesis_registry_from_dict(registry.to_dict()) == registry


def test_artifact_choice_closure_policy_matches_tracked_registry() -> None:
    registry = load_hypothesis_registry(TRACKED_REGISTRY).registry
    choice_fields = (
        "input_tensor",
        "observation_axis",
        "centering_rule",
        "residual_rule",
        "architecture_accounting_rule",
        "estimator",
        "fit_role",
        "interpolation_rule",
        "lift_rule",
        "trivialization_rule",
        "reference_rule",
    )

    for hypothesis_id in HypothesisId:
        hypothesis = registry.require(hypothesis_id)
        calibration = {
            field_name: set(choice.candidate_ids)
            for field_name in choice_fields
            if (
                choice := getattr(hypothesis, field_name)
            ).resolution
            is ResolutionState.CALIBRATION_SELECTION
        }
        fixed = {
            field_name: {choice.selected_id}
            for field_name in choice_fields
            if (
                choice := getattr(hypothesis, field_name)
            ).resolution
            is ResolutionState.FIXED_BY_HYPOTHESIS
        }

        assert (
            _P0_CALIBRATION_SELECTIONS_BY_HYPOTHESIS[hypothesis_id]
            == calibration
        )
        assert _P0_FIXED_SELECTIONS_BY_HYPOTHESIS[hypothesis_id] == fixed


def test_registry_binds_chronology_without_storing_an_outcome_value() -> None:
    boundary = load_hypothesis_registry(
        TRACKED_REGISTRY
    ).registry.historical_boundary

    assert boundary.historical_snapshot_id == P0_HISTORICAL_SNAPSHOT_ID
    assert boundary.historical_cutoff_commit == P0_HISTORICAL_CUTOFF_COMMIT
    assert (
        boundary.historical_outcome_integration_commit
        == P0_HISTORICAL_OUTCOME_INTEGRATION_COMMIT
    )
    assert (
        boundary.historical_outcome_record_path
        == P0_HISTORICAL_OUTCOME_RECORD_PATH
    )
    assert (
        boundary.historical_outcome_record_source_sha256
        == P0_HISTORICAL_OUTCOME_RECORD_SOURCE_SHA256
    )
    assert (
        boundary.historical_outcome_artifact_source_sha256
        == P0_HISTORICAL_OUTCOME_ARTIFACT_SOURCE_SHA256
    )
    outcome_record = REPOSITORY_ROOT / P0_HISTORICAL_OUTCOME_RECORD_PATH
    retained_artifact = (
        REPOSITORY_ROOT
        / "runs/pythia70-full-slot-only-001/"
        "layer-0-neighbor-audit-v0-4.json"
    )
    assert hashlib.sha256(outcome_record.read_bytes()).hexdigest() == (
        P0_HISTORICAL_OUTCOME_RECORD_SOURCE_SHA256
    )
    assert hashlib.sha256(retained_artifact.read_bytes()).hexdigest() == (
        P0_HISTORICAL_OUTCOME_ARTIFACT_SOURCE_SHA256
    )
    assert boundary.registry_postdates_prior_outcome is True
    assert boundary.prior_outcome_allowed_for_selection is False

    document = _document()
    forbidden_data_fields = {
        "model_id",
        "numeric_threshold",
        "observed_outcome",
        "outcome_value",
        "sae_id",
        "semantic_label",
        "subject_id",
        "threshold",
    }

    def visit(value: object) -> None:
        if isinstance(value, dict):
            assert forbidden_data_fields.isdisjoint(value)
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            raise AssertionError("P0 registry must not contain numeric values")

    visit(document)


def test_yaml_formatting_changes_only_source_digest(tmp_path: Path) -> None:
    document = _document()
    first = _write(tmp_path, document, name="first.yaml")
    second = tmp_path / "second.yaml"
    second.write_text(
        "# formatting-only change\n"
        + yaml.safe_dump(document, sort_keys=True),
        encoding="utf-8",
    )

    loaded_first = load_hypothesis_registry(first)
    loaded_second = load_hypothesis_registry(second)

    assert loaded_first.source_sha256 != loaded_second.source_sha256
    assert loaded_first.canonical_sha256 == loaded_second.canonical_sha256


def test_valid_semantic_change_changes_canonical_digest(tmp_path: Path) -> None:
    first_document = _document()
    second_document = deepcopy(first_document)
    second_document["registry_id"] = "p0_order_parameter_hypotheses_v0_1_copy"

    first = load_hypothesis_registry(_write(tmp_path, first_document, name="a.yaml"))
    second = load_hypothesis_registry(_write(tmp_path, second_document, name="b.yaml"))

    assert first.canonical_sha256 != second.canonical_sha256


def test_structural_parse_and_p0_policy_validation_are_separate() -> None:
    document = _document()
    document["winner_selected"] = True

    registry = hypothesis_registry_from_dict(document)
    assert registry.winner_selected is True
    with pytest.raises(HypothesisRegistryPolicyError, match="winning"):
        validate_p0_registry(registry)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("status", "selected", "status"),
        ("winner_selected", True, "winning"),
        ("primary_integer_output_authorized", True, "integer"),
        ("subject_data_access_authorized", True, "subject-data"),
        ("real_model_claim_state", "level_1g", "level_0"),
    ),
)
def test_root_p0_boundaries_fail_closed(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    document = _document()
    document[field] = value
    with pytest.raises(HypothesisRegistryPolicyError, match=message):
        load_hypothesis_registry(_write(tmp_path, document))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("historical_snapshot_id", "other_snapshot", "snapshot"),
        ("historical_cutoff_commit", "0" * 40, "cutoff"),
        (
            "historical_outcome_integration_commit",
            "0" * 40,
            "integration",
        ),
        (
            "historical_outcome_record_path",
            "protocols/other.yaml",
            "outcome record",
        ),
        (
            "historical_outcome_record_source_sha256",
            "0" * 64,
            "record digest",
        ),
        (
            "historical_outcome_artifact_source_sha256",
            "0" * 64,
            "artifact digest",
        ),
        ("registry_postdates_prior_outcome", False, "chronology"),
        ("prior_outcome_allowed_for_selection", True, "must not select"),
    ),
)
def test_historical_firewall_is_exact(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    document = _document()
    boundary = document["historical_boundary"]
    assert isinstance(boundary, dict)
    boundary[field] = value
    with pytest.raises(HypothesisRegistryPolicyError, match=message):
        load_hypothesis_registry(_write(tmp_path, document))


def test_p0_requires_exactly_once_f0_through_f4_in_order(tmp_path: Path) -> None:
    missing = _document()
    missing["hypotheses"] = missing["hypotheses"][:-1]  # type: ignore[index]
    with pytest.raises(HypothesisRegistryPolicyError, match="exactly"):
        load_hypothesis_registry(_write(tmp_path, missing, name="missing.yaml"))

    duplicate = _document()
    duplicate["hypotheses"][-1] = deepcopy(duplicate["hypotheses"][0])  # type: ignore[index]
    with pytest.raises(HypothesisRegistrySchemaError, match="unique"):
        load_hypothesis_registry(_write(tmp_path, duplicate, name="duplicate.yaml"))

    reordered = _document()
    reordered["hypotheses"][0], reordered["hypotheses"][1] = (  # type: ignore[index]
        reordered["hypotheses"][1],  # type: ignore[index]
        reordered["hypotheses"][0],  # type: ignore[index]
    )
    with pytest.raises(HypothesisRegistryPolicyError, match="canonical order"):
        load_hypothesis_registry(_write(tmp_path, reordered, name="order.yaml"))


def test_f0_never_becomes_phase_winding_or_defect(tmp_path: Path) -> None:
    document = _document()
    f0 = _hypothesis(document, "f0_support")
    f0["forbidden_labels"] = ["defect", "phase"]
    with pytest.raises(HypothesisRegistryPolicyError, match="winding"):
        load_hypothesis_registry(_write(tmp_path, document))


def test_f1_matrix_holonomy_cannot_authorize_an_integer(tmp_path: Path) -> None:
    document = _document()
    f1 = _hypothesis(document, "f1_projector_connection")
    f1["integer_output_authorized"] = True
    with pytest.raises(HypothesisRegistryPolicyError, match="integer"):
        load_hypothesis_registry(_write(tmp_path, document))


def test_instrument_dev_execution_state_cannot_enter_the_registry(
    tmp_path: Path,
) -> None:
    document = _document()
    choice = _hypothesis(
        document,
        "f2_local_covariant_section",
    )["input_tensor"]
    assert isinstance(choice, dict)
    choice["resolution"] = "instrument_dev_executed"
    choice["selected_id"] = "raw_state"
    choice["candidate_ids"] = []

    with pytest.raises(
        HypothesisRegistrySchemaError,
        match="reserved for graph construction",
    ):
        load_hypothesis_registry(_write(tmp_path, document))


def test_f2_requires_all_conditional_winding_prerequisites(tmp_path: Path) -> None:
    document = _document()
    f2 = _hypothesis(document, "f2_local_covariant_section")
    prerequisites = f2["winding_prerequisites"]
    assert isinstance(prerequisites, list)
    prerequisites.remove("orientable_bundle")
    with pytest.raises(HypothesisRegistryPolicyError, match="prerequisites"):
        load_hypothesis_registry(_write(tmp_path, document))


def test_f3_requires_all_projection_dependence_controls(tmp_path: Path) -> None:
    document = _document()
    f3 = _hypothesis(document, "f3_global_plane_section")
    controls = f3["required_controls"]
    assert isinstance(controls, list)
    controls.remove("random_plane_ensemble_control")
    with pytest.raises(HypothesisRegistryPolicyError, match="random_plane"):
        load_hypothesis_registry(_write(tmp_path, document))


def test_f4_must_keep_spin_two_and_ordinary_vector_conventions_separate(
    tmp_path: Path,
) -> None:
    document = _document()
    f4 = _hypothesis(document, "f4_spin_two_anisotropy")
    f4["gauge_law"] = "ordinary_vector_angle"
    with pytest.raises(HypothesisRegistryPolicyError, match="gauge"):
        load_hypothesis_registry(_write(tmp_path, document))


def test_p0_rule_choices_retain_only_allowed_fit_and_axis_candidates() -> None:
    registry = load_hypothesis_registry(TRACKED_REGISTRY).registry
    for hypothesis in registry.hypotheses:
        assert hypothesis.observation_axis.resolution is ResolutionState.CALIBRATION_SELECTION
        assert set(hypothesis.observation_axis.candidate_ids) == {
            "layer_index",
            "token_position",
            "training_step",
        }
        assert set(hypothesis.fit_role.candidate_ids) == {
            "calibration_selection",
            "instrument_dev",
        }


@pytest.mark.parametrize(
    "forbidden",
    (
        "model_id",
        "numeric_threshold",
        "observed_outcome",
        "sae_id",
        "semantic_label",
        "subject_id",
    ),
)
def test_unknown_leaky_fields_are_rejected(
    tmp_path: Path,
    forbidden: str,
) -> None:
    document = _document()
    _hypothesis(document, "f2_local_covariant_section")[forbidden] = "leak"
    with pytest.raises(HypothesisRegistrySchemaError, match="unknown"):
        load_hypothesis_registry(
            _write(tmp_path, document, name=f"{forbidden}.yaml")
        )


def test_numeric_values_and_boolean_as_string_fields_are_rejected(
    tmp_path: Path,
) -> None:
    numeric = _document()
    _hypothesis(numeric, "f1_projector_connection")["rank_convention"] = 2
    with pytest.raises(HypothesisRegistrySchemaError, match="numeric"):
        load_hypothesis_registry(_write(tmp_path, numeric, name="numeric.yaml"))

    boolean_alias = _document()
    boolean_alias["winner_selected"] = 0
    with pytest.raises(HypothesisRegistrySchemaError, match="numeric"):
        load_hypothesis_registry(
            _write(tmp_path, boolean_alias, name="boolean.yaml")
        )


def test_unknown_schema_enum_and_field_fail_closed(tmp_path: Path) -> None:
    wrong_schema = _document()
    wrong_schema["schema_version"] = "spirallens.hypothesis-registry.v9"
    with pytest.raises(HypothesisRegistrySchemaError, match="unsupported"):
        load_hypothesis_registry(_write(tmp_path, wrong_schema, name="schema.yaml"))

    wrong_enum = _document()
    _hypothesis(wrong_enum, "f0_support")["branch"] = "meaning"
    with pytest.raises(HypothesisRegistrySchemaError, match="must be one of"):
        load_hypothesis_registry(_write(tmp_path, wrong_enum, name="enum.yaml"))

    unknown = _document()
    unknown["threshold"] = "forbidden"
    with pytest.raises(HypothesisRegistrySchemaError, match="unknown"):
        load_hypothesis_registry(_write(tmp_path, unknown, name="unknown.yaml"))


def test_yaml_ambiguity_and_executable_features_are_rejected(
    tmp_path: Path,
) -> None:
    valid = TRACKED_REGISTRY.read_text(encoding="utf-8")
    malformed = {
        "duplicate": valid.replace(
            "status: preparation",
            "status: preparation\nstatus: selected",
            1,
        ),
        "alias": "first: &shared {}\nsecond: *shared\n",
        "merge": "root:\n  <<: {field: value}\n",
        "tag": "schema_version: !unsafe value\n",
        "multidoc": valid + "\n---\nsecond: document\n",
        "nonstring": "1: value\n",
    }
    expected = {
        "duplicate": "duplicate YAML key",
        "alias": "aliases are not allowed",
        "merge": "merge keys are not allowed",
        "tag": "invalid hypothesis-registry YAML",
        "multidoc": "invalid hypothesis-registry YAML",
        "nonstring": "mapping keys must be strings",
    }
    for name, text in malformed.items():
        path = tmp_path / f"{name}.yaml"
        path.write_text(text, encoding="utf-8")
        with pytest.raises(HypothesisRegistrySchemaError, match=expected[name]):
            load_hypothesis_registry(path)


def test_oversize_and_invalid_utf8_are_rejected(tmp_path: Path) -> None:
    oversize = tmp_path / "oversize.yaml"
    oversize.write_bytes(b"x" * (MAX_HYPOTHESIS_REGISTRY_BYTES + 1))
    with pytest.raises(HypothesisRegistrySchemaError, match="exceeds"):
        load_hypothesis_registry(oversize)

    invalid = tmp_path / "invalid.yaml"
    invalid.write_bytes(b"\xff\xfe")
    with pytest.raises(HypothesisRegistrySchemaError, match="UTF-8"):
        load_hypothesis_registry(invalid)


def test_expected_source_and_canonical_digests_are_checked(tmp_path: Path) -> None:
    path = _write(tmp_path, _document())
    loaded = load_hypothesis_registry(path)

    assert load_hypothesis_registry(
        path,
        expected_source_sha256=loaded.source_sha256,
        expected_canonical_sha256=loaded.canonical_sha256,
    ) == loaded
    with pytest.raises(HypothesisRegistryIntegrityError, match="source"):
        load_hypothesis_registry(path, expected_source_sha256="0" * 64)
    with pytest.raises(HypothesisRegistryIntegrityError, match="canonical"):
        load_hypothesis_registry(path, expected_canonical_sha256="0" * 64)
