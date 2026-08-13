from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any

import pytest

from spirallens.atlas.engineering_protocol import (
    MAX_PUBLIC_EXAMPLE_PLUMBING_PROTOCOL_BYTES,
    PublicExamplePlumbingProtocolIntegrityError,
    PublicExamplePlumbingProtocolSchemaError,
    load_public_example_plumbing_protocol,
)
from spirallens.contexts import (
    ContextBankIntegrityError,
    ContextBankSchemaError,
    load_context_bank,
)
from spirallens.contexts.loader import MAX_CONTEXT_BANK_BYTES
from spirallens.instrument_contracts.registry_loader import (
    MAX_HYPOTHESIS_REGISTRY_BYTES,
    HypothesisRegistryIntegrityError,
    HypothesisRegistrySchemaError,
    load_hypothesis_registry,
)
from spirallens.synthetic.protocol import (
    MAX_REPRESENTATION_PHANTOM_PROTOCOL_BYTES,
    RepresentationPhantomProtocolIntegrityError,
    RepresentationPhantomProtocolSchemaError,
    load_representation_phantom_protocol,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class _Domain:
    name: str
    fixture: Path
    load: Callable[..., Any]
    schema_error: type[Exception]
    integrity_error: type[Exception]
    size_limit: int
    size_message: str
    utf8_message: str
    source_message: str
    invalid_yaml_prefix: str
    mapping_message: str
    nonstring_message: str
    root_message: str
    collection_message: str
    collection_cause: str | None
    source_sha256: str
    canonical_sha256: str


_DOMAINS = (
    _Domain(
        name="contexts",
        fixture=REPOSITORY_ROOT / "protocols/context_bank_example_v0_1.yaml",
        load=lambda path, **kwargs: load_context_bank(
            path, allowed_roles={"example"}, **kwargs
        ),
        schema_error=ContextBankSchemaError,
        integrity_error=ContextBankIntegrityError,
        size_limit=MAX_CONTEXT_BANK_BYTES,
        size_message=f"context bank exceeds {MAX_CONTEXT_BANK_BYTES} bytes",
        utf8_message="context bank must be UTF-8 YAML",
        source_message=(
            "context-bank source SHA-256 does not match the expected digest"
        ),
        invalid_yaml_prefix="invalid context-bank YAML: ",
        mapping_message="context bank must be a mapping",
        nonstring_message="all mapping keys must be strings",
        root_message=(
            "context bank fields differ from v1 contract: "
            "missing=['bank_id', 'claim_eligible', 'contexts', 'license', "
            "'model', 'schema_version', 'source', 'status', 'sweep_domain', "
            "'tokenizer'], unknown=['root']"
        ),
        collection_message=(
            "context bank fields differ from v1 contract: "
            "missing=['bank_id', 'claim_eligible', 'contexts', 'license', "
            "'model', 'schema_version', 'source', 'status', 'sweep_domain', "
            "'tokenizer'], unknown=['root']"
        ),
        collection_cause=None,
        source_sha256=(
            "db9df614ad68bd20646da29740354624b8be075719e7ef4ca2ad8023d4dcef4f"
        ),
        canonical_sha256=(
            "46c23fb8f1c0f2136537bab5717473c2cc8b03a9121d89db267a29b89ef0a438"
        ),
    ),
    _Domain(
        name="instrument_registry",
        fixture=(
            REPOSITORY_ROOT / "protocols/order_parameter_hypothesis_registry_v0_1.yaml"
        ),
        load=load_hypothesis_registry,
        schema_error=HypothesisRegistrySchemaError,
        integrity_error=HypothesisRegistryIntegrityError,
        size_limit=MAX_HYPOTHESIS_REGISTRY_BYTES,
        size_message=(
            f"hypothesis registry exceeds {MAX_HYPOTHESIS_REGISTRY_BYTES} bytes"
        ),
        utf8_message="hypothesis registry must be UTF-8 YAML",
        source_message=(
            "hypothesis-registry source SHA-256 does not match expected digest"
        ),
        invalid_yaml_prefix="invalid hypothesis-registry YAML: ",
        mapping_message="hypothesis registry must be a mapping",
        nonstring_message="all YAML mapping keys must be strings",
        root_message="$.root.x must not contain numeric values",
        collection_message=(
            "invalid hypothesis registry: hypothesis registry fields differ "
            "from the contract: missing=['historical_boundary', 'hypotheses', "
            "'policy_version', 'primary_integer_output_authorized', "
            "'real_model_claim_state', 'registry_id', 'schema_version', "
            "'status', 'subject_data_access_authorized', 'winner_selected'], "
            "unknown=['root']"
        ),
        collection_cause="ContractValidationError",
        source_sha256=(
            "8a953bf7ee0772ffa6d6facf8a6088f06cc3ae9cd39b4a7f624c8caa4bcfbd07"
        ),
        canonical_sha256=(
            "68d2869b87403f65b554b931b363446269e543661b598478233d536cb2fc9a93"
        ),
    ),
    _Domain(
        name="representation_phantom",
        fixture=REPOSITORY_ROOT / "protocols/p1_representation_phantom_v0_1.yaml",
        load=load_representation_phantom_protocol,
        schema_error=RepresentationPhantomProtocolSchemaError,
        integrity_error=RepresentationPhantomProtocolIntegrityError,
        size_limit=MAX_REPRESENTATION_PHANTOM_PROTOCOL_BYTES,
        size_message=(
            "representation phantom protocol exceeds "
            f"{MAX_REPRESENTATION_PHANTOM_PROTOCOL_BYTES} bytes"
        ),
        utf8_message="representation phantom protocol must be UTF-8 YAML",
        source_message=(
            "representation phantom protocol source SHA-256 does not match "
            "the expected digest"
        ),
        invalid_yaml_prefix="invalid representation phantom protocol YAML: ",
        mapping_message="representation phantom protocol must be a mapping",
        nonstring_message="all YAML mapping keys must be strings",
        root_message=(
            "representation phantom protocol fields differ from the contract: "
            "missing=['cases', 'claim_ceiling', 'execution', 'generator', "
            "'protocol_id', 'qualification_status', 'registry', "
            "'schema_version', 'source', 'status'], unknown=['root']"
        ),
        collection_message=(
            "representation phantom protocol fields differ from the contract: "
            "missing=['cases', 'claim_ceiling', 'execution', 'generator', "
            "'protocol_id', 'qualification_status', 'registry', "
            "'schema_version', 'source', 'status'], unknown=['root']"
        ),
        collection_cause=None,
        source_sha256=(
            "5d5b754ab7659401f2abf30ef9a0ed32506573c917a33be48725999cd17c3d26"
        ),
        canonical_sha256=(
            "8976818b6d1750b42ccd89e1b4efe1e5029353f917eb830c99020bc9eb22b235"
        ),
    ),
    _Domain(
        name="atlas_engineering",
        fixture=(
            REPOSITORY_ROOT / "protocols/pythia70_public_example_plumbing_v0_1.yaml"
        ),
        load=load_public_example_plumbing_protocol,
        schema_error=PublicExamplePlumbingProtocolSchemaError,
        integrity_error=PublicExamplePlumbingProtocolIntegrityError,
        size_limit=MAX_PUBLIC_EXAMPLE_PLUMBING_PROTOCOL_BYTES,
        size_message="public-example plumbing protocol exceeds the size limit",
        utf8_message="public-example plumbing protocol must be UTF-8 YAML",
        source_message="public-example protocol source SHA-256 mismatch",
        invalid_yaml_prefix="invalid public-example plumbing YAML: ",
        mapping_message="public-example plumbing protocol must be a mapping",
        nonstring_message="all YAML mapping keys must be strings",
        root_message=(
            "public-example plumbing protocol fields differ from the contract: "
            "missing=['allowed_consumers', 'authorizations', 'capture', "
            "'claim_ceiling', 'context_bank', 'execution_class', 'model', "
            "'p1_instrument_consumed', 'protocol_id', 'purpose', "
            "'resource_budget', 'schema_version', "
            "'scientific_claim_eligible', 'source', 'stage_status', 'status', "
            "'token_selection', 'tokenizer_runtime_verified'], unknown=['root']"
        ),
        collection_message=(
            "public-example plumbing protocol fields differ from the contract: "
            "missing=['allowed_consumers', 'authorizations', 'capture', "
            "'claim_ceiling', 'context_bank', 'execution_class', 'model', "
            "'p1_instrument_consumed', 'protocol_id', 'purpose', "
            "'resource_budget', 'schema_version', "
            "'scientific_claim_eligible', 'source', 'stage_status', 'status', "
            "'token_selection', 'tokenizer_runtime_verified'], unknown=['root']"
        ),
        collection_cause=None,
        source_sha256=(
            "ef93891c7450ef13cc2c5da54bf1a80d4a0b679df2df04964f2cc505e00aaf4c"
        ),
        canonical_sha256=(
            "968ad990e7c80ddae3cadcf71c5b39aa37f7b5cad88ea473df094cedb6b633d6"
        ),
    ),
)


@pytest.fixture(params=_DOMAINS, ids=lambda domain: domain.name)
def domain(request: pytest.FixtureRequest) -> _Domain:
    value = request.param
    assert isinstance(value, _Domain)
    return value


def _write(tmp_path: Path, payload: bytes, *, name: str = "input.yaml") -> Path:
    path = tmp_path / name
    path.write_bytes(payload)
    return path


def _assert_plain_domain_error(
    caught: pytest.ExceptionInfo[BaseException],
    *,
    domain: _Domain,
    message: str,
) -> None:
    assert type(caught.value) is domain.schema_error
    assert str(caught.value) == message
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert caught.value.__suppress_context__ is False


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (b"root:\n  nested: one\n  nested: two\n", "duplicate YAML key 'nested'"),
        (b"base: &shared {}\ncopy: *shared\n", "YAML aliases are not allowed"),
        (b"root:\n  <<: {field: value}\n", "YAML merge keys are not allowed"),
        (b"1: value\n", "domain-nonstring-message"),
    ],
    ids=("nested-duplicate", "alias", "merge", "non-string-key"),
)
def test_strict_yaml_rejections_preserve_exact_domain_failures(
    tmp_path: Path,
    domain: _Domain,
    payload: bytes,
    expected: str,
) -> None:
    path = _write(tmp_path, payload)
    with pytest.raises(domain.schema_error) as caught:
        domain.load(path)
    _assert_plain_domain_error(
        caught,
        domain=domain,
        message=(
            domain.nonstring_message
            if expected == "domain-nonstring-message"
            else expected
        ),
    )


@pytest.mark.parametrize(
    ("payload", "underlying_type", "underlying_prefix"),
    [
        (
            b"schema_version: !unsafe value\n",
            "ConstructorError",
            "could not determine a constructor for the tag '!unsafe'",
        ),
        (
            b"{}\n---\nsecond: document\n",
            "ComposerError",
            "expected a single document in the stream",
        ),
    ],
    ids=("custom-tag", "multiple-documents"),
)
def test_wrapped_yaml_errors_preserve_domain_prefix_and_direct_cause(
    tmp_path: Path,
    domain: _Domain,
    payload: bytes,
    underlying_type: str,
    underlying_prefix: str,
) -> None:
    path = _write(tmp_path, payload)
    with pytest.raises(domain.schema_error) as caught:
        domain.load(path)

    error = caught.value
    assert str(error).startswith(domain.invalid_yaml_prefix + underlying_prefix)
    assert error.__cause__ is error.__context__
    assert type(error.__cause__).__name__ == underlying_type
    assert str(error.__cause__).startswith(underlying_prefix)
    assert error.__suppress_context__ is True


@pytest.mark.parametrize(
    "payload",
    (b"", b"- one\n- two\n"),
    ids=("empty", "sequence"),
)
def test_empty_and_sequence_documents_preserve_mapping_failure(
    tmp_path: Path,
    domain: _Domain,
    payload: bytes,
) -> None:
    with pytest.raises(domain.schema_error) as caught:
        domain.load(_write(tmp_path, payload))
    _assert_plain_domain_error(caught, domain=domain, message=domain.mapping_message)


def test_anchor_definition_without_alias_preserves_accepted_document_identity(
    tmp_path: Path,
    domain: _Domain,
) -> None:
    raw = domain.fixture.read_bytes()
    anchored = _write(tmp_path, b"&document\n" + raw)

    baseline = domain.load(domain.fixture)
    loaded = domain.load(anchored)

    assert hashlib.sha256(raw).hexdigest() == domain.source_sha256
    assert baseline.source_sha256 == domain.source_sha256
    assert baseline.canonical_sha256 == domain.canonical_sha256
    assert loaded.canonical_sha256 == baseline.canonical_sha256
    assert loaded.source_sha256 == hashlib.sha256(anchored.read_bytes()).hexdigest()
    assert loaded.source_sha256 != baseline.source_sha256


@pytest.mark.parametrize("scalar", (b".nan", b".inf"), ids=("nan", "inf"))
def test_nonfinite_safe_yaml_scalars_preserve_downstream_domain_order(
    tmp_path: Path,
    domain: _Domain,
    scalar: bytes,
) -> None:
    path = _write(tmp_path, b"root: " + scalar + b"\n")
    with pytest.raises(domain.schema_error) as caught:
        domain.load(path)

    error = caught.value
    assert error.__cause__ is None
    assert error.__context__ is None
    assert error.__suppress_context__ is False
    if domain.name == "instrument_registry":
        assert str(error) == "$.root must not contain numeric values"
    else:
        assert str(error) == domain.root_message


@pytest.mark.parametrize(
    "tagged",
    (
        b"!!set {x: null}",
        b"!!omap [{x: 1}]",
        b"!!pairs [{x: 1}]",
    ),
    ids=("set", "omap", "pairs"),
)
def test_standard_safe_yaml_collection_tags_reach_domain_validation(
    tmp_path: Path,
    domain: _Domain,
    tagged: bytes,
) -> None:
    path = _write(tmp_path, b"root: " + tagged + b"\n")
    with pytest.raises(domain.schema_error) as caught:
        domain.load(path)

    error = caught.value
    assert str(error) == domain.collection_message
    if domain.collection_cause is not None:
        assert type(error.__cause__).__name__ == domain.collection_cause
        assert error.__cause__ is error.__context__
        assert error.__suppress_context__ is True
    else:
        assert error.__cause__ is None
        assert error.__context__ is None
        assert error.__suppress_context__ is False


def test_deep_recursion_remains_an_unwrapped_interpreter_failure(
    tmp_path: Path,
    domain: _Domain,
) -> None:
    payload = b"root: " + (b"[" * 2_000) + b"x" + (b"]" * 2_000) + b"\n"
    with pytest.raises(RecursionError) as caught:
        domain.load(_write(tmp_path, payload))
    assert str(caught.value) == "maximum recursion depth exceeded"
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert caught.value.__suppress_context__ is False


def test_size_digest_and_utf8_checks_preserve_precedence(
    tmp_path: Path,
    domain: _Domain,
) -> None:
    oversized = _write(tmp_path, b"\xff" * (domain.size_limit + 1), name="large.yaml")
    with pytest.raises(domain.schema_error) as caught_size:
        domain.load(oversized, expected_source_sha256="0" * 64)
    _assert_plain_domain_error(
        caught_size,
        domain=domain,
        message=domain.size_message,
    )

    invalid_utf8 = _write(tmp_path, b"\xff\xfe", name="invalid-utf8.yaml")
    with pytest.raises(domain.integrity_error) as caught_digest:
        domain.load(invalid_utf8, expected_source_sha256="0" * 64)
    assert type(caught_digest.value) is domain.integrity_error
    assert str(caught_digest.value) == domain.source_message
    assert caught_digest.value.__cause__ is None
    assert caught_digest.value.__context__ is None
    assert caught_digest.value.__suppress_context__ is False

    with pytest.raises(domain.schema_error) as caught_utf8:
        domain.load(invalid_utf8)
    assert type(caught_utf8.value) is domain.schema_error
    assert str(caught_utf8.value) == domain.utf8_message
    assert type(caught_utf8.value.__cause__) is UnicodeDecodeError
    assert caught_utf8.value.__cause__ is caught_utf8.value.__context__
    assert caught_utf8.value.__suppress_context__ is True
