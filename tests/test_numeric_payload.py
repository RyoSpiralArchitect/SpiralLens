from __future__ import annotations

import hashlib
import io
import os
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from test_instrument_bundle import _build_bundle

import spirallens.instrument_contracts.numeric_payload as numeric_module
from spirallens.access import (
    AtlasAccessPolicy,
    AtlasConsumer,
    AtlasConsumerDenied,
    ProvenanceTaint,
    bind_value_access_lineage,
)
from spirallens.instrument_contracts import (
    ContractValidationError,
    DecodedNumericArray,
    L2AmplitudeRelation,
    L2AmplitudeValidation,
    NumericArrayContract,
    NumericPayloadError,
    NumericValueRule,
    PayloadKind,
    PayloadRef,
    RowIdentityContract,
    VerifiedRowIdentity,
    open_numeric_payload_session,
)
from spirallens.instrument_contracts.numeric_payload import (
    _DECODED_ARRAY_FACTORY_TOKEN,
    _L2_VALIDATION_FACTORY_TOKEN,
    _NUMERIC_SESSION_FACTORY_TOKEN,
    _VERIFIED_ROW_FACTORY_TOKEN,
    NumericPayloadSession,
    _decode_exact_npy,
    _ordered_content_sha256,
)


def _policy(*, authorized: bool = True) -> AtlasAccessPolicy:
    return AtlasAccessPolicy(
        origin_execution_class="synthetic_calibration",
        claim_ceiling="level_0",
        scientific_claim_eligible=False,
        allowed_consumers=(
            frozenset({AtlasConsumer.NUMERIC_PAYLOAD_VALIDATION})
            if authorized
            else frozenset()
        ),
        provenance_taints=frozenset({ProvenanceTaint.INSTRUMENT_UNQUALIFIED}),
    )


def _npy_bytes(
    value: np.ndarray,
    *,
    version: tuple[int, int] | None = None,
) -> bytes:
    stream = io.BytesIO()
    if version is None:
        np.save(stream, value, allow_pickle=False)
    else:
        np.lib.format.write_array(
            stream,
            value,
            version=version,
            allow_pickle=False,
        )
    return stream.getvalue()


def _npy_bytes_with_shape_literal(
    value: np.ndarray,
    *,
    shape_literal: str,
) -> bytes:
    prefix = b"\x93NUMPY\x01\x00"
    header_text = (
        f"{{'descr': '<f8', 'fortran_order': False, 'shape': {shape_literal}, }}"
    ).encode("ascii")
    padding = (-(len(prefix) + 2 + len(header_text) + 1)) % np.lib.format.ARRAY_ALIGN
    header = header_text + (b" " * padding) + b"\n"
    return (
        prefix
        + len(header).to_bytes(2, byteorder="little")
        + header
        + value.astype("<f8", copy=False).tobytes(order="C")
    )


def _reference(
    source: bytes,
    *,
    dtype: str,
    shape: tuple[int, ...],
    row_identity_sha256: str = "a" * 64,
) -> PayloadRef:
    return PayloadRef(
        kind=PayloadKind.ARRAY,
        sha256=hashlib.sha256(source).hexdigest(),
        byte_length=len(source),
        media_type="application/x-npy",
        dtype=dtype,
        shape=shape,
        row_identity_sha256=row_identity_sha256,
    )


def _direct_session(
    tmp_path: Path,
    payloads: tuple[tuple[PayloadRef, bytes], ...],
) -> NumericPayloadSession:
    descriptors: dict[PayloadRef, int] = {}
    for index, (reference, source) in enumerate(payloads):
        path = tmp_path / f"payload-{index}.npy"
        path.write_bytes(source)
        descriptors[reference] = os.open(path, os.O_RDONLY)
    parent = _policy()
    lineage = bind_value_access_lineage(
        parent,
        expected_parent_policy_sha256=parent.sha256,
        consumer=AtlasConsumer.NUMERIC_PAYLOAD_VALIDATION,
    )
    loaded = SimpleNamespace(
        source_sha256="b" * 64,
        canonical_sha256="c" * 64,
    )
    return NumericPayloadSession(
        _factory_token=_NUMERIC_SESSION_FACTORY_TOKEN,
        loaded_bundle=loaded,
        descriptors=descriptors,
        lineage=lineage,
        requested_payloads=tuple(reference for reference, _ in payloads),
    )


def test_exact_npy_decoder_returns_bytes_backed_immutable_array() -> None:
    expected = np.arange(12, dtype="<f8").reshape(3, 4)
    source = _npy_bytes(expected)
    reference = _reference(source, dtype="<f8", shape=(3, 4))

    decoded = _decode_exact_npy(source, reference)

    assert np.array_equal(decoded.values, expected)
    assert decoded.values.dtype.str == "<f8"
    assert decoded.values.flags.c_contiguous
    assert not decoded.values.flags.owndata
    assert not decoded.values.flags.writeable
    with pytest.raises(ValueError):
        decoded.values[0, 0] = 99.0
    with pytest.raises(ValueError):
        decoded.values.setflags(write=True)


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("dtype", "npy_dtype_mismatch"),
        ("shape", "npy_shape_mismatch"),
        ("trailing", "npy_extent_mismatch"),
        ("nonfinite", "numeric_payload_nonfinite"),
        ("fortran", "npy_fortran_order_forbidden"),
        ("object", "npy_dtype_not_numeric"),
        ("version3", "npy_version_unsupported"),
    ],
)
def test_exact_npy_decoder_rejects_unsafe_or_inexact_streams(
    mutation: str,
    code: str,
) -> None:
    value = np.arange(6, dtype="<f8").reshape(2, 3)
    source = _npy_bytes(value)
    reference = _reference(source, dtype="<f8", shape=(2, 3))
    if mutation == "dtype":
        reference = replace(reference, dtype="<f4")
    elif mutation == "shape":
        reference = replace(reference, shape=(3, 2))
    elif mutation == "trailing":
        source += b"x"
        reference = _reference(source, dtype="<f8", shape=(2, 3))
    elif mutation == "nonfinite":
        value[0, 0] = np.nan
        source = _npy_bytes(value)
        reference = _reference(source, dtype="<f8", shape=(2, 3))
    elif mutation == "fortran":
        source = _npy_bytes(np.asfortranarray(value))
        reference = _reference(source, dtype="<f8", shape=(2, 3))
    elif mutation == "object":
        object_stream = io.BytesIO()
        np.save(
            object_stream,
            np.array([object()], dtype=object),
            allow_pickle=True,
        )
        source = object_stream.getvalue()
        reference = _reference(source, dtype="<i8", shape=(1,))
    elif mutation == "version3":
        source = _npy_bytes(value, version=(3, 0))
        reference = _reference(source, dtype="<f8", shape=(2, 3))

    with pytest.raises(NumericPayloadError) as caught:
        _decode_exact_npy(source, reference)

    assert caught.value.code == code


def test_exact_npy_decoder_rejects_boolean_header_dimension() -> None:
    source = _npy_bytes_with_shape_literal(
        np.array([[1.0, 2.0]], dtype="<f8"),
        shape_literal="(True, 2)",
    )
    reference = _reference(source, dtype="<f8", shape=(1, 2))

    with pytest.raises(NumericPayloadError) as caught:
        _decode_exact_npy(source, reference)

    assert caught.value.code == "npy_shape_invalid"


def test_scalar_payload_reference_is_rejected_before_row_binding() -> None:
    source = _npy_bytes(np.array(1.0, dtype="<f8"))

    with pytest.raises(ContractValidationError, match="shape must not be empty"):
        _reference(source, dtype="<f8", shape=())


def test_decoded_array_cannot_be_directly_forged() -> None:
    source = _npy_bytes(np.arange(2, dtype="<f8"))
    reference = _reference(source, dtype="<f8", shape=(2,))
    values = np.arange(2, dtype="<f8")
    values.setflags(write=False)

    with pytest.raises(NumericPayloadError) as caught:
        DecodedNumericArray(
            reference=reference,
            values=values,
            npy_version=(1, 0),
        )

    assert caught.value.code == "decoded_array_factory_required"


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("dtype", "decoded_array_dtype_mismatch"),
        ("shape", "decoded_array_shape_mismatch"),
        ("version", "npy_version_unsupported"),
    ],
)
def test_decoded_array_factory_still_enforces_exact_metadata(
    mutation: str,
    code: str,
) -> None:
    source = _npy_bytes(np.arange(2, dtype="<f8"))
    reference = _reference(source, dtype="<f8", shape=(2,))
    version: tuple[int, int] = (1, 0)
    if mutation == "dtype":
        reference = replace(reference, dtype="<f4")
    elif mutation == "shape":
        reference = replace(reference, shape=(1, 2))
    else:
        version = (2, 1)
    values = np.arange(2, dtype="<f8")
    values.setflags(write=False)

    with pytest.raises(NumericPayloadError) as caught:
        DecodedNumericArray(
            _factory_token=_DECODED_ARRAY_FACTORY_TOKEN,
            reference=reference,
            values=values,
            npy_version=version,
        )

    assert caught.value.code == code


def test_verified_row_identity_cannot_be_directly_forged() -> None:
    with pytest.raises(NumericPayloadError) as caught:
        VerifiedRowIdentity(
            sha256="a" * 64,
            row_count=2,
            source_payload_identity_sha256="b" * 64,
            domain="vertex-row-order",
        )

    assert caught.value.code == "verified_row_factory_required"


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"sha256": "A" * 64}, NumericPayloadError),
        ({"row_count": True}, TypeError),
        (
            {"source_payload_identity_sha256": "not-a-digest"},
            NumericPayloadError,
        ),
        ({"domain": " untrimmed"}, NumericPayloadError),
    ],
)
def test_verified_row_factory_enforces_all_proof_fields(
    overrides: dict[str, object],
    expected: type[Exception],
) -> None:
    fields: dict[str, object] = {
        "sha256": "a" * 64,
        "row_count": 2,
        "source_payload_identity_sha256": "b" * 64,
        "domain": "vertex-row-order",
    }
    fields.update(overrides)

    with pytest.raises(expected):
        VerifiedRowIdentity(
            _factory_token=_VERIFIED_ROW_FACTORY_TOKEN,
            **fields,
        )


def test_row_identity_and_l2_relation_are_content_verified(
    tmp_path: Path,
) -> None:
    row_ids = np.array([[10, 11], [20, 21], [30, 31]], dtype="<i8")
    row_digest = _ordered_content_sha256("vertex-row-order", row_ids)
    values = np.array([[3.0, 4.0], [5.0, 12.0], [8.0, 15.0]], dtype="<f8")
    amplitude = np.array([5.0, 13.0, 17.0], dtype="<f8")
    row_source = _npy_bytes(row_ids)
    values_source = _npy_bytes(values)
    amplitude_source = _npy_bytes(amplitude)
    row_reference = _reference(
        row_source,
        dtype="<i8",
        shape=row_ids.shape,
        row_identity_sha256=row_digest,
    )
    values_reference = _reference(
        values_source,
        dtype="<f8",
        shape=values.shape,
        row_identity_sha256=row_digest,
    )
    amplitude_reference = _reference(
        amplitude_source,
        dtype="<f8",
        shape=amplitude.shape,
        row_identity_sha256=row_digest,
    )

    session = _direct_session(
        tmp_path,
        (
            (row_reference, row_source),
            (values_reference, values_source),
            (amplitude_reference, amplitude_source),
        ),
    )
    with session:
        rows = session.decode_row_identity(
            RowIdentityContract(
                source=row_reference,
                domain="vertex-row-order",
            )
        )
        decoded = session.decode_array(
            NumericArrayContract(
                reference=values_reference,
                value_rule=NumericValueRule.FINITE,
            ),
            rows=rows,
        )
        validation = session.validate_l2_amplitude(
            L2AmplitudeRelation(
                values=values_reference,
                amplitude=amplitude_reference,
                axis=-1,
                rtol=0.0,
                atol=0.0,
            ),
            rows=rows,
        )

    assert np.array_equal(decoded.values, values)
    assert validation.passed is True
    assert session.closed


def test_row_identity_rejects_declared_digest_not_derived_from_content(
    tmp_path: Path,
) -> None:
    row_ids = np.arange(4, dtype="<i8")
    source = _npy_bytes(row_ids)
    reference = _reference(
        source,
        dtype="<i8",
        shape=(4,),
        row_identity_sha256="0" * 64,
    )

    with (
        _direct_session(tmp_path, ((reference, source),)) as session,
        pytest.raises(NumericPayloadError) as caught,
    ):
        session.decode_row_identity(
            RowIdentityContract(
                source=reference,
                domain="vertex-row-order",
            )
        )

    assert caught.value.code == "row_identity_digest_mismatch"


@pytest.mark.parametrize(
    ("row_ids", "code"),
    [
        (
            np.array([[1, 2], [1, 2]], dtype="<i8"),
            "row_identity_duplicate",
        ),
        (
            np.empty((2, 0), dtype="<i8"),
            "row_identity_components_empty",
        ),
    ],
)
def test_row_identity_rejects_nonidentifying_rows(
    tmp_path: Path,
    row_ids: np.ndarray,
    code: str,
) -> None:
    domain = "vertex-row-order"
    source = _npy_bytes(row_ids)
    reference = _reference(
        source,
        dtype="<i8",
        shape=row_ids.shape,
        row_identity_sha256=_ordered_content_sha256(domain, row_ids),
    )

    with (
        _direct_session(tmp_path, ((reference, source),)) as session,
        pytest.raises(NumericPayloadError) as caught,
    ):
        session.decode_row_identity(
            RowIdentityContract(source=reference, domain=domain)
        )

    assert caught.value.code == code


def test_l2_relation_rejects_nontrailing_axis_for_square_rows() -> None:
    row_digest = "a" * 64
    values_source = _npy_bytes(np.array([[3.0, 0.0], [4.0, 12.0]], dtype="<f8"))
    column_amplitude_source = _npy_bytes(np.array([5.0, 12.0], dtype="<f8"))
    values_reference = _reference(
        values_source,
        dtype="<f8",
        shape=(2, 2),
        row_identity_sha256=row_digest,
    )
    amplitude_reference = _reference(
        column_amplitude_source,
        dtype="<f8",
        shape=(2,),
        row_identity_sha256=row_digest,
    )

    with pytest.raises(NumericPayloadError) as caught:
        L2AmplitudeRelation(
            values=values_reference,
            amplitude=amplitude_reference,
            axis=0,
            rtol=0.0,
            atol=0.0,
        )

    assert caught.value.code == "l2_relation_axis_invalid"


def test_l2_validation_receipt_cannot_be_directly_forged() -> None:
    row_digest = "a" * 64
    values_source = _npy_bytes(np.array([[3.0, 4.0]], dtype="<f8"))
    amplitude_source = _npy_bytes(np.array([5.0], dtype="<f8"))
    relation = L2AmplitudeRelation(
        values=_reference(
            values_source,
            dtype="<f8",
            shape=(1, 2),
            row_identity_sha256=row_digest,
        ),
        amplitude=_reference(
            amplitude_source,
            dtype="<f8",
            shape=(1,),
            row_identity_sha256=row_digest,
        ),
        axis=-1,
        rtol=0.0,
        atol=0.0,
    )

    with pytest.raises(NumericPayloadError) as caught:
        L2AmplitudeValidation(
            relation=relation,
            row_identity_sha256=row_digest,
        )

    assert caught.value.code == "l2_validation_factory_required"

    with pytest.raises(NumericPayloadError) as caught:
        L2AmplitudeValidation(
            _factory_token=_L2_VALIDATION_FACTORY_TOKEN,
            relation=relation,
            row_identity_sha256="b" * 64,
        )

    assert caught.value.code == "l2_validation_row_identity_mismatch"


def test_l2_relation_failure_is_a_contract_error(tmp_path: Path) -> None:
    row_ids = np.arange(2, dtype="<i8")
    row_digest = _ordered_content_sha256("vertex-row-order", row_ids)
    values = np.array([[3.0, 4.0], [5.0, 12.0]], dtype="<f8")
    amplitude = np.array([5.0, 12.0], dtype="<f8")
    payload_values = (row_ids, values, amplitude)
    sources = tuple(_npy_bytes(item) for item in payload_values)
    references = (
        _reference(
            sources[0],
            dtype="<i8",
            shape=(2,),
            row_identity_sha256=row_digest,
        ),
        _reference(
            sources[1],
            dtype="<f8",
            shape=(2, 2),
            row_identity_sha256=row_digest,
        ),
        _reference(
            sources[2],
            dtype="<f8",
            shape=(2,),
            row_identity_sha256=row_digest,
        ),
    )

    with _direct_session(
        tmp_path,
        tuple(zip(references, sources, strict=True)),
    ) as session:
        rows = session.decode_row_identity(
            RowIdentityContract(
                source=references[0],
                domain="vertex-row-order",
            )
        )
        with pytest.raises(NumericPayloadError) as caught:
            session.validate_l2_amplitude(
                L2AmplitudeRelation(
                    values=references[1],
                    amplitude=references[2],
                    axis=-1,
                    rtol=0.0,
                    atol=0.0,
                ),
                rows=rows,
            )

    assert caught.value.code == "l2_relation_failed"


def test_authorization_denial_occurs_before_bundle_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened = False

    def fail_if_opened(*args: object, **kwargs: object) -> object:
        nonlocal opened
        opened = True
        raise AssertionError("bundle loader must not be reached")

    monkeypatch.setattr(
        numeric_module,
        "_load_instrument_bundle_retaining_payloads",
        fail_if_opened,
    )
    parent = _policy(authorized=False)
    dummy = _reference(
        _npy_bytes(np.arange(1, dtype="<i8")),
        dtype="<i8",
        shape=(1,),
    )

    with (
        pytest.raises(AtlasConsumerDenied),
        open_numeric_payload_session(
            "/path/must/not/be/inspected",
            requested_payloads=(dummy,),
            parent_policy=parent,
            expected_parent_policy_sha256=parent.sha256,
            expected_bundle_source_sha256="1" * 64,
            expected_bundle_canonical_sha256="2" * 64,
        ),
    ):
        pass

    assert opened is False


def test_bundle_validation_retains_selected_verified_descriptor(
    tmp_path: Path,
) -> None:
    fixture = _build_bundle(tmp_path)
    requested = next(
        entry.reference
        for entry in fixture.manifest.payloads
        if entry.reference.kind is PayloadKind.ARRAY
    )
    parent = _policy()

    with open_numeric_payload_session(
        fixture.manifest_path,
        requested_payloads=(requested,),
        parent_policy=parent,
        expected_parent_policy_sha256=parent.sha256,
        expected_bundle_source_sha256=fixture.manifest.canonical_sha256,
        expected_bundle_canonical_sha256=fixture.manifest.canonical_sha256,
    ) as session:
        assert session.requested_payloads == (requested,)
        assert not session.closed

    assert session.closed


def test_held_descriptor_survives_path_replacement(tmp_path: Path) -> None:
    row_ids = np.array([11, 22, 33], dtype="<i8")
    row_digest = _ordered_content_sha256("vertex-row-order", row_ids)
    source = _npy_bytes(row_ids)
    reference = _reference(
        source,
        dtype="<i8",
        shape=(3,),
        row_identity_sha256=row_digest,
    )
    path = tmp_path / "held.npy"
    path.write_bytes(source)
    descriptor = os.open(path, os.O_RDONLY)
    replacement = tmp_path / "replacement.npy"
    replacement.write_bytes(_npy_bytes(np.array([99, 99, 99], dtype="<i8")))
    os.replace(replacement, path)
    parent = _policy()
    lineage = bind_value_access_lineage(
        parent,
        expected_parent_policy_sha256=parent.sha256,
        consumer=AtlasConsumer.NUMERIC_PAYLOAD_VALIDATION,
    )
    session = NumericPayloadSession(
        _factory_token=_NUMERIC_SESSION_FACTORY_TOKEN,
        loaded_bundle=SimpleNamespace(
            source_sha256="b" * 64,
            canonical_sha256="c" * 64,
        ),
        descriptors={reference: descriptor},
        lineage=lineage,
        requested_payloads=(reference,),
    )

    with session:
        rows = session.decode_row_identity(
            RowIdentityContract(
                source=reference,
                domain="vertex-row-order",
            )
        )

    assert rows.sha256 == row_digest


def test_rejected_direct_session_construction_does_not_close_caller_fd(
    tmp_path: Path,
) -> None:
    source = _npy_bytes(np.arange(1, dtype="<i8"))
    reference = _reference(source, dtype="<i8", shape=(1,))
    path = tmp_path / "caller-owned.npy"
    path.write_bytes(source)
    descriptor = os.open(path, os.O_RDONLY)
    parent = _policy()
    lineage = bind_value_access_lineage(
        parent,
        expected_parent_policy_sha256=parent.sha256,
        consumer=AtlasConsumer.NUMERIC_PAYLOAD_VALIDATION,
    )

    try:
        with pytest.raises(NumericPayloadError) as caught:
            NumericPayloadSession(
                _factory_token=object(),
                loaded_bundle=SimpleNamespace(
                    source_sha256="b" * 64,
                    canonical_sha256="c" * 64,
                ),
                descriptors={reference: descriptor},
                lineage=lineage,
                requested_payloads=(reference,),
            )

        assert caught.value.code == "numeric_session_factory_required"
        os.fstat(descriptor)
    finally:
        os.close(descriptor)
