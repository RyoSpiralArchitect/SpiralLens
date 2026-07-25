from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path

import pytest
import yaml

from spirallens.contexts import (
    BankStatus,
    CaptureStage,
    ContextBankIntegrityError,
    ContextBankSchemaError,
    ContextContractError,
    ContextRole,
    ObservationKey,
    SweepDomain,
    context_bank_from_dict,
    load_context_bank,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_BANK = REPOSITORY_ROOT / "protocols/context_bank_example_v0_1.yaml"


def _document() -> dict[str, object]:
    return {
        "schema_version": "spirallens.context-bank.v1",
        "bank_id": "synthetic-example-v1",
        "status": "example",
        "license": "Apache-2.0",
        "claim_eligible": False,
        "source": {
            "kind": "project_authored_synthetic",
            "source_id": "test-fixture",
        },
        "model": {
            "id": "test/pythia",
            "requested_revision": "main",
            "resolved_revision": "a" * 40,
            "vocab_size": 12,
        },
        "tokenizer": {
            "id": "test/pythia",
            "requested_revision": "main",
            "resolved_revision": "a" * 40,
            "addressable_size": 10,
            "tokenizer_class": "SyntheticTokenizerFast",
            "implementation": "fast",
            "transformers_version": "test",
            "tokenizers_version": "test",
            "add_special_tokens": False,
            "files": {
                "tokenizer.json": "1" * 64,
                "tokenizer_config.json": "2" * 64,
                "special_tokens_map.json": "3" * 64,
            },
        },
        "sweep_domain": "model_embedding_rows",
        "contexts": [
            {
                "context_id": "synthetic-a",
                "role": "example",
                "family_id": "family-a",
                "source_id": "source-a",
                "template_id": "template-a",
                "template_ids": [None],
                "attention_mask": [1],
                "observation_position": 0,
            },
            {
                "context_id": "synthetic-b",
                "role": "example",
                "family_id": "family-a",
                "source_id": "source-a",
                "template_id": "template-a",
                "template_ids": [1, None, 2],
                "attention_mask": [1, 1, 1],
                "observation_position": 2,
            },
        ],
    }


def _write_document(
    tmp_path: Path,
    document: dict[str, object],
    *,
    name: str = "bank.yaml",
) -> Path:
    path = tmp_path / name
    path.write_text(
        yaml.safe_dump(document, sort_keys=False),
        encoding="utf-8",
    )
    return path


def test_tracked_example_bank_is_claim_ineligible_and_provenance_bound() -> None:
    loaded = load_context_bank(EXAMPLE_BANK, allowed_roles={"example"})
    bank = loaded.bank

    assert bank.role is ContextRole.EXAMPLE
    assert bank.status is BankStatus.EXAMPLE
    assert bank.claim_eligible is False
    assert len(bank.contexts) == 8
    assert bank.model.vocab_size == 50_304
    assert bank.tokenizer.addressable_size == 50_277
    assert bank.model.resolved_revision == bank.tokenizer.resolved_revision
    assert loaded.source_sha256 == hashlib.sha256(
        EXAMPLE_BANK.read_bytes()
    ).hexdigest()
    assert loaded.canonical_sha256 == bank.sha256
    assert context_bank_from_dict(bank.to_dict()) == bank
    assert len(bank.tokenizer.sha256) == 64
    assert (
        bank.contexts[1].template_id
        == bank.contexts[2].template_id
        == "prefix-one"
    )


def test_slot_materialization_changes_only_the_slot() -> None:
    bank = load_context_bank(EXAMPLE_BANK, allowed_roles={"example"}).bank
    context = bank.require(
        "synthetic-bracketed-002",
        role=ContextRole.EXAMPLE,
    )

    assert context.sweep_position == 1
    assert context.observation_position == 2
    assert context.materialize(
        50_290,
        model_vocab_size=bank.model.vocab_size,
    ) == (2, 50_290, 3)


def test_model_rows_and_tokenizer_addressable_ids_are_distinct_domains() -> None:
    bank = load_context_bank(EXAMPLE_BANK, allowed_roles={"example"}).bank

    assert bank.validate_swept_token_id(50_276) is True
    assert bank.validate_swept_token_id(50_277) is False
    assert bank.validate_swept_token_id(50_303) is False
    with pytest.raises(ContextContractError, match="must be in"):
        bank.validate_swept_token_id(50_304)

    lexical_bank = replace(
        bank,
        sweep_domain=SweepDomain.TOKENIZER_ADDRESSABLE,
    )
    assert lexical_bank.validate_swept_token_id(50_276) is True
    with pytest.raises(ContextContractError, match="must be in"):
        lexical_bank.validate_swept_token_id(50_277)


def test_context_fixed_ids_must_be_tokenizer_addressable(tmp_path: Path) -> None:
    document = _document()
    document["contexts"][1]["template_ids"] = [10, None, 2]  # type: ignore[index]

    with pytest.raises(ContextContractError, match="tokenizer-addressable"):
        load_context_bank(
            _write_document(tmp_path, document),
            allowed_roles={"example"},
        )


def test_observation_key_round_trip_and_one_field_change() -> None:
    bank = load_context_bank(EXAMPLE_BANK, allowed_roles={"example"}).bank
    key = bank.observation_key(
        context_id="synthetic-slot-only-001",
        role=ContextRole.EXAMPLE,
        swept_token_id=50_277,
        layer_index=3,
        capture_stage=CaptureStage.RESID_PRE,
    )

    assert key.context_role is ContextRole.EXAMPLE
    assert key.tokenizer_addressable is False
    assert key.sweep_domain is SweepDomain.MODEL_EMBEDDING_ROWS
    assert ObservationKey.from_dict(key.to_dict()) == key
    assert bank.validate_observation_key(key) is key
    assert len(key.observation_id) == 64
    assert replace(key, layer_index=4).observation_id != key.observation_id

    extra = {**key.to_dict(), "meaning": "forbidden"}
    with pytest.raises(ContextContractError, match="unknown"):
        ObservationKey.from_dict(extra)
    with pytest.raises(ContextContractError, match="string names"):
        ObservationKey.from_dict({**key.to_dict(), 1: "forbidden"})


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("model_id", "other/model"),
        ("resolved_model_revision", "b" * 40),
        ("context_bank_sha256", "b" * 64),
        ("context_spec_sha256", "c" * 64),
        ("model_vocab_size", 50_305),
        ("tokenizer_addressable_size", 50_276),
        ("sweep_domain", SweepDomain.TOKENIZER_ADDRESSABLE),
        ("sweep_position", 1),
        ("observation_position", 1),
    ),
)
def test_observation_key_must_validate_against_its_bank(
    field: str,
    value: object,
) -> None:
    bank = load_context_bank(EXAMPLE_BANK, allowed_roles={"example"}).bank
    key = bank.observation_key(
        context_id="synthetic-slot-only-001",
        role=ContextRole.EXAMPLE,
        swept_token_id=7,
        layer_index=0,
        capture_stage=CaptureStage.RESID_POST,
    )
    tampered = replace(key, **{field: value})

    with pytest.raises(ContextContractError, match="does not match"):
        bank.validate_observation_key(tampered)


def test_observation_key_enforces_domain_bound_and_addressability_flag() -> None:
    bank = load_context_bank(EXAMPLE_BANK, allowed_roles={"example"}).bank
    key = bank.observation_key(
        context_id="synthetic-slot-only-001",
        role=ContextRole.EXAMPLE,
        swept_token_id=50_303,
        layer_index=0,
        capture_stage=CaptureStage.RESID_PRE,
    )

    with pytest.raises(ContextContractError, match="outside"):
        replace(key, swept_token_id=50_304)
    with pytest.raises(ContextContractError, match="does not match"):
        replace(key, tokenizer_addressable=True)


def test_yaml_formatting_changes_only_source_digest(tmp_path: Path) -> None:
    document = _document()
    first = _write_document(tmp_path, document, name="first.yaml")
    second = tmp_path / "second.yaml"
    second.write_text(
        "# formatting-only change\n"
        + yaml.safe_dump(document, sort_keys=True),
        encoding="utf-8",
    )

    loaded_first = load_context_bank(first, allowed_roles={"example"})
    loaded_second = load_context_bank(second, allowed_roles={"example"})

    assert loaded_first.source_sha256 != loaded_second.source_sha256
    assert loaded_first.canonical_sha256 == loaded_second.canonical_sha256


def test_canonical_digest_binds_order_role_family_source_and_license(
    tmp_path: Path,
) -> None:
    base = load_context_bank(
        _write_document(tmp_path, _document()),
        allowed_roles={"example"},
    ).bank
    assert replace(base, contexts=tuple(reversed(base.contexts))).sha256 != base.sha256
    assert replace(base, license="CC0-1.0").sha256 != base.sha256
    assert replace(
        base,
        source=replace(base.source, source_id="other-source"),
    ).sha256 != base.sha256
    assert replace(
        base,
        contexts=(
            replace(base.contexts[0], family_id="other-family"),
            base.contexts[1],
        ),
    ).sha256 != base.sha256

    discovery_contexts = tuple(
        replace(context, role=ContextRole.DISCOVERY)
        for context in base.contexts
    )
    discovery = replace(
        base,
        status=BankStatus.DRAFT,
        contexts=discovery_contexts,
    )
    assert discovery.sha256 != base.sha256

    independently_versioned_tokenizer = replace(
        base.tokenizer,
        tokenizer_id="other/tokenizer",
        resolved_revision="b" * 40,
        file_sha256=(("tokenizer.model", "4" * 64),),
    )
    rebound = replace(base, tokenizer=independently_versioned_tokenizer)
    assert rebound.sha256 != base.sha256


def test_bank_lifecycle_claim_boundaries_fail_closed(tmp_path: Path) -> None:
    base = load_context_bank(
        _write_document(tmp_path, _document()),
        allowed_roles={"example"},
    ).bank

    with pytest.raises(ContextContractError, match="example banks"):
        replace(base, claim_eligible=True)
    with pytest.raises(ContextContractError, match="example banks"):
        replace(base, status=BankStatus.DRAFT)

    discovery_contexts = tuple(
        replace(context, role=ContextRole.DISCOVERY)
        for context in base.contexts
    )
    with pytest.raises(ContextContractError, match="reserved"):
        replace(base, contexts=discovery_contexts)
    with pytest.raises(ContextContractError, match="status=frozen"):
        replace(
            base,
            status=BankStatus.DRAFT,
            claim_eligible=True,
            contexts=discovery_contexts,
        )

    held_out_contexts = tuple(
        replace(context, role=ContextRole.HELD_OUT)
        for context in base.contexts
    )
    with pytest.raises(ContextContractError, match="must be frozen"):
        replace(
            base,
            status=BankStatus.DRAFT,
            contexts=held_out_contexts,
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("template_ids", [], "must not be empty"),
        ("template_ids", [1, 2], "exactly one null"),
        ("template_ids", [None, None], "exactly one null"),
        ("template_ids", [True, None], "must be an integer"),
        ("attention_mask", [1, 0, 1], "length must match"),
        ("observation_position", True, "must be an integer"),
        ("observation_position", 3, "outside"),
    ),
)
def test_invalid_slot_mask_and_position_fail_closed(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    document = _document()
    document["contexts"][0][field] = value  # type: ignore[index]

    with pytest.raises((ContextBankSchemaError, ContextContractError), match=message):
        load_context_bank(
            _write_document(tmp_path, document),
            allowed_roles={"example"},
        )


def test_masked_slot_and_observation_positions_are_rejected(
    tmp_path: Path,
) -> None:
    slot_masked = _document()
    slot_masked["contexts"][1]["attention_mask"] = [1, 0, 1]  # type: ignore[index]
    with pytest.raises(ContextContractError, match="sweep slot"):
        load_context_bank(
            _write_document(tmp_path, slot_masked, name="slot.yaml"),
            allowed_roles={"example"},
        )

    observation_masked = _document()
    observation_masked["contexts"][1]["attention_mask"] = [1, 1, 0]  # type: ignore[index]
    with pytest.raises(ContextContractError, match="observation position"):
        load_context_bank(
            _write_document(tmp_path, observation_masked, name="observation.yaml"),
            allowed_roles={"example"},
        )


def test_duplicate_numeric_inputs_are_rejected(tmp_path: Path) -> None:
    document = _document()
    duplicate = deepcopy(document["contexts"][0])  # type: ignore[index]
    duplicate.update(
        {
            "context_id": "synthetic-c",
            "family_id": "family-c",
            "source_id": "source-c",
            "template_id": "template-c",
        }
    )
    document["contexts"].append(duplicate)  # type: ignore[union-attr]

    with pytest.raises(ContextContractError, match="duplicate numeric"):
        load_context_bank(
            _write_document(tmp_path, document),
            allowed_roles={"example"},
        )


def test_roles_are_explicit_single_artifact_and_never_implicitly_filtered(
    tmp_path: Path,
) -> None:
    path = _write_document(tmp_path, _document())

    with pytest.raises(ContextBankSchemaError, match="must not be empty"):
        load_context_bank(path, allowed_roles=set())
    with pytest.raises(ContextBankSchemaError, match="not in explicitly"):
        load_context_bank(path, allowed_roles={"discovery"})
    with pytest.raises(ContextBankSchemaError, match="unknown allowed role"):
        load_context_bank(path, allowed_roles={"training"})
    with pytest.raises(ContextBankSchemaError, match="exactly one"):
        load_context_bank(
            path,
            allowed_roles={"example", "held_out"},
        )

    mixed = _document()
    mixed["contexts"][1]["role"] = "held_out"  # type: ignore[index]
    with pytest.raises(ContextContractError, match="exactly one role"):
        load_context_bank(
            _write_document(tmp_path, mixed, name="mixed.yaml"),
            allowed_roles={"example"},
        )


def test_semantic_and_unknown_fields_are_rejected(tmp_path: Path) -> None:
    for forbidden in ("meaning", "label", "category", "expected_pair", "sae_id"):
        document = _document()
        document["contexts"][0][forbidden] = "leak"  # type: ignore[index]
        with pytest.raises(ContextBankSchemaError, match="unknown"):
            load_context_bank(
                _write_document(tmp_path, document, name=f"{forbidden}.yaml"),
                allowed_roles={"example"},
            )


def test_duplicate_keys_aliases_merge_keys_and_custom_tags_are_rejected(
    tmp_path: Path,
) -> None:
    valid = yaml.safe_dump(_document(), sort_keys=False)
    malformed = {
        "duplicate": valid.replace(
            "bank_id: synthetic-example-v1",
            "bank_id: synthetic-example-v1\nbank_id: duplicate",
        ),
        "alias": "first: &shared {}\nsecond: *shared\n",
        "merge": "source:\n  <<: {kind: synthetic}\n  source_id: fixture\n",
        "tag": "schema_version: !unsafe value\n",
    }
    expected = {
        "duplicate": "duplicate YAML key",
        "alias": "aliases are not allowed",
        "merge": "merge keys are not allowed",
        "tag": "invalid context-bank YAML",
    }
    for name, text in malformed.items():
        path = tmp_path / f"{name}.yaml"
        path.write_text(text, encoding="utf-8")
        with pytest.raises(ContextBankSchemaError, match=expected[name]):
            load_context_bank(path, allowed_roles={"example"})


def test_expected_digests_are_checked_before_use(tmp_path: Path) -> None:
    path = _write_document(tmp_path, _document())
    loaded = load_context_bank(path, allowed_roles={"example"})

    assert load_context_bank(
        path,
        allowed_roles={"example"},
        expected_source_sha256=loaded.source_sha256,
        expected_canonical_sha256=loaded.canonical_sha256,
    ) == loaded
    with pytest.raises(ContextBankIntegrityError, match="source"):
        load_context_bank(
            path,
            allowed_roles={"example"},
            expected_source_sha256="0" * 64,
        )
    with pytest.raises(ContextBankIntegrityError, match="canonical"):
        load_context_bank(
            path,
            allowed_roles={"example"},
            expected_canonical_sha256="0" * 64,
        )
