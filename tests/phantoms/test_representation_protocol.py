from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path

import pytest
import yaml

from spirallens.synthetic.protocol import (
    REPRESENTATION_PHANTOM_PROTOCOL_SCHEMA_VERSION,
    RepresentationPhantomProtocolIntegrityError,
    RepresentationPhantomProtocolSchemaError,
    load_representation_phantom_protocol,
    representation_phantom_protocol_from_dict,
)


def _document() -> dict[str, object]:
    return {
        "schema_version": REPRESENTATION_PHANTOM_PROTOCOL_SCHEMA_VERSION,
        "protocol_id": "representation-phantom-v0.1",
        "status": "instrument_dev",
        "claim_ceiling": "level_0",
        "qualification_status": "not_evaluated",
        "source": {
            "repository": "RyoSpiralArchitect/SpiralLens",
            "generator_revision": "a" * 40,
            "generator_module_sha256": "b" * 64,
        },
        "generator": {
            "seed": 1729,
            "grid_side": 9,
            "ambient_dimension": 16,
            "probe_count": 8,
            "neighbor_count": 6,
            "radial_scale": 1.0,
            "probe_scale": 0.5,
            "nuisance_scale": 0.01,
        },
        "cases": [
            {
                "case_id": "angular-section-positive",
                "field_kind": "angular-unit-vector",
            },
            {
                "case_id": "fixed-direction-null",
                "field_kind": "fixed-unit-vector",
            },
        ],
        "registry": {
            "path": "protocols/order_parameter_hypothesis_registry_v0_1.yaml",
            "source_sha256": "c" * 64,
            "canonical_sha256": "d" * 64,
        },
        "execution": {
            "fit_role": "instrument_dev",
            "context_kind": "synthetic_lattice",
            "synthetic_context_claim_eligible": False,
            "model_access_authorized": False,
            "subject_data_access_authorized": False,
            "subject_execution_authorized": False,
            "subject_protocol_preparation_authorized": False,
            "calibration_selection_authorized": False,
            "integer_output_authorized": False,
        },
    }


def _write(
    tmp_path: Path,
    document: dict[str, object],
    *,
    name: str = "protocol.yaml",
) -> Path:
    path = tmp_path / name
    path.write_text(
        yaml.safe_dump(document, sort_keys=False),
        encoding="utf-8",
    )
    return path


def test_valid_protocol_has_source_and_canonical_identities(
    tmp_path: Path,
) -> None:
    path = _write(tmp_path, _document())
    loaded = load_representation_phantom_protocol(path)

    assert loaded.source_path == path.resolve()
    assert loaded.source_bytes == path.read_bytes()
    assert loaded.source_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert loaded.canonical_sha256 == hashlib.sha256(
        loaded.canonical_bytes
    ).hexdigest()
    assert loaded.to_dict() == _document()
    assert representation_phantom_protocol_from_dict(loaded.to_dict()) == (
        loaded.protocol
    )
    assert [case.case_id for case in loaded.protocol.cases] == [
        "angular-section-positive",
        "fixed-direction-null",
    ]


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("status",), "qualified"),
        (("claim_ceiling",), "level_1g"),
        (("qualification_status",), "pass"),
        (("source", "repository"), "Other/Repository"),
        (("source", "generator_revision"), "A" * 40),
        (("execution", "fit_role"), "calibration_selection"),
        (("execution", "context_kind"), "model_tokens"),
        (("execution", "synthetic_context_claim_eligible"), True),
        (("execution", "model_access_authorized"), True),
    ),
)
def test_authority_and_fixed_vocabulary_fail_closed(
    tmp_path: Path,
    path: tuple[str, ...],
    value: object,
) -> None:
    document = _document()
    target: dict[str, object] = document
    for component in path[:-1]:
        target = target[component]  # type: ignore[assignment]
    target[path[-1]] = value
    with pytest.raises(RepresentationPhantomProtocolSchemaError):
        load_representation_phantom_protocol(_write(tmp_path, document))


def test_unknown_missing_reordered_cases_and_unsafe_paths_are_rejected(
    tmp_path: Path,
) -> None:
    unknown = _document()
    unknown["semantic_label"] = "forbidden"
    with pytest.raises(RepresentationPhantomProtocolSchemaError, match="unknown"):
        load_representation_phantom_protocol(
            _write(tmp_path, unknown, name="unknown.yaml")
        )

    missing = _document()
    del missing["generator"]["seed"]  # type: ignore[index]
    with pytest.raises(RepresentationPhantomProtocolSchemaError, match="missing"):
        load_representation_phantom_protocol(
            _write(tmp_path, missing, name="missing.yaml")
        )

    reordered = _document()
    reordered["cases"] = list(reversed(reordered["cases"]))  # type: ignore[arg-type]
    with pytest.raises(RepresentationPhantomProtocolSchemaError, match="sorted"):
        load_representation_phantom_protocol(
            _write(tmp_path, reordered, name="reordered.yaml")
        )

    traversal = _document()
    traversal["registry"]["path"] = "../registry.yaml"  # type: ignore[index]
    with pytest.raises(RepresentationPhantomProtocolSchemaError, match="relative"):
        load_representation_phantom_protocol(
            _write(tmp_path, traversal, name="traversal.yaml")
        )


def test_legacy_context_bank_execution_fields_are_rejected(
    tmp_path: Path,
) -> None:
    document = _document()
    execution = document["execution"]
    assert isinstance(execution, dict)
    del execution["context_kind"]
    del execution["synthetic_context_claim_eligible"]
    execution["context_role"] = "example"
    execution["context_claim_eligible"] = False

    with pytest.raises(
        RepresentationPhantomProtocolSchemaError,
        match="fields differ",
    ):
        load_representation_phantom_protocol(
            _write(tmp_path, document, name="legacy-context.yaml")
        )


def test_plain_numeric_and_boolean_scalars_are_enforced(
    tmp_path: Path,
) -> None:
    boolean_integer = _document()
    boolean_integer["generator"]["seed"] = True  # type: ignore[index]
    with pytest.raises(RepresentationPhantomProtocolSchemaError, match="integer"):
        load_representation_phantom_protocol(
            _write(tmp_path, boolean_integer, name="bool-int.yaml")
        )

    integer_float = _document()
    integer_float["generator"]["radial_scale"] = 1  # type: ignore[index]
    with pytest.raises(
        RepresentationPhantomProtocolSchemaError,
        match="floating-point",
    ):
        load_representation_phantom_protocol(
            _write(tmp_path, integer_float, name="int-float.yaml")
        )

    string_boolean = _document()
    string_boolean["execution"]["synthetic_context_claim_eligible"] = "false"  # type: ignore[index]
    with pytest.raises(RepresentationPhantomProtocolSchemaError, match="boolean"):
        load_representation_phantom_protocol(
            _write(tmp_path, string_boolean, name="string-bool.yaml")
        )

    invalid_spec = _document()
    invalid_spec["generator"]["grid_side"] = 6  # type: ignore[index]
    with pytest.raises(
        RepresentationPhantomProtocolSchemaError,
        match="bound spec",
    ):
        load_representation_phantom_protocol(
            _write(tmp_path, invalid_spec, name="invalid-spec.yaml")
        )


def test_duplicate_alias_merge_custom_tag_and_multidoc_are_rejected(
    tmp_path: Path,
) -> None:
    valid = yaml.safe_dump(_document(), sort_keys=False)
    malformed = {
        "duplicate": valid.replace(
            "status: instrument_dev",
            "status: instrument_dev\nstatus: instrument_dev",
            1,
        ),
        "alias": "first: &shared {}\nsecond: *shared\n",
        "merge": "root:\n  <<: {field: value}\n",
        "tag": "schema_version: !unsafe value\n",
        "multidoc": valid + "\n---\nsecond: document\n",
    }
    expected = {
        "duplicate": "duplicate YAML key",
        "alias": "aliases are not allowed",
        "merge": "merge keys are not allowed",
        "tag": "invalid representation phantom protocol YAML",
        "multidoc": "invalid representation phantom protocol YAML",
    }
    for name, text in malformed.items():
        path = tmp_path / f"{name}.yaml"
        path.write_text(text, encoding="utf-8")
        with pytest.raises(
            RepresentationPhantomProtocolSchemaError,
            match=expected[name],
        ):
            load_representation_phantom_protocol(path)


def test_digest_mismatch_and_formatting_identity(tmp_path: Path) -> None:
    first = _write(tmp_path, _document(), name="first.yaml")
    second = tmp_path / "second.yaml"
    second.write_text(
        "# formatting changes source bytes only\n"
        + yaml.safe_dump(_document(), sort_keys=True),
        encoding="utf-8",
    )
    loaded_first = load_representation_phantom_protocol(first)
    loaded_second = load_representation_phantom_protocol(second)

    assert loaded_first.source_sha256 != loaded_second.source_sha256
    assert loaded_first.canonical_sha256 == loaded_second.canonical_sha256
    assert load_representation_phantom_protocol(
        first,
        expected_source_sha256=loaded_first.source_sha256,
        expected_canonical_sha256=loaded_first.canonical_sha256,
    ) == loaded_first
    with pytest.raises(
        RepresentationPhantomProtocolIntegrityError, match="source"
    ):
        load_representation_phantom_protocol(
            first, expected_source_sha256="0" * 64
        )
    with pytest.raises(
        RepresentationPhantomProtocolIntegrityError, match="canonical"
    ):
        load_representation_phantom_protocol(
            first, expected_canonical_sha256="0" * 64
        )


def test_source_size_utf8_and_input_nonmutation(tmp_path: Path) -> None:
    document = _document()
    before = deepcopy(document)
    representation_phantom_protocol_from_dict(document)
    assert document == before

    oversized = tmp_path / "oversized.yaml"
    oversized.write_bytes(b"x" * 1_048_577)
    with pytest.raises(RepresentationPhantomProtocolSchemaError, match="exceeds"):
        load_representation_phantom_protocol(oversized)

    invalid = tmp_path / "invalid.yaml"
    invalid.write_bytes(b"\xff\xfe")
    with pytest.raises(RepresentationPhantomProtocolSchemaError, match="UTF-8"):
        load_representation_phantom_protocol(invalid)
