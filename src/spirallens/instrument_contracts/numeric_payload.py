"""Secure, typed numerical decoding for closed instrument-bundle payloads.

The public bundle loader intentionally treats payload bytes as opaque.  This
module adds a separate value-level capability: authorization is checked before
any file is opened, selected payload descriptors are retained from the same
secure bundle-validation transaction, and numerical decoding consumes immutable
snapshots read from those descriptors without reopening a pathname.
"""

from __future__ import annotations

import hashlib
import io
import math
import os
import re
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Self

import numpy as np
from numpy.lib import format as npy_format
from numpy.typing import NDArray

from spirallens.access import (
    AtlasAccessPolicy,
    AtlasConsumer,
    ValueAccessLineage,
    bind_value_access_lineage,
)
from spirallens.core.canonical import canonical_json_bytes

from .bundle_loader import (
    LoadedInstrumentBundle,
    _load_instrument_bundle_retaining_payloads,
)
from .common import PayloadKind, PayloadRef

MAX_NUMERIC_PAYLOAD_BYTES = 256 * 1024 * 1024
MAX_NPY_HEADER_BYTES = 10_000
SUPPORTED_NPY_VERSIONS = frozenset({(1, 0), (2, 0)})
_NUMERIC_SESSION_FACTORY_TOKEN = object()
_DECODED_ARRAY_FACTORY_TOKEN = object()
_VERIFIED_ROW_FACTORY_TOKEN = object()
_L2_VALIDATION_FACTORY_TOKEN = object()
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class NumericPayloadError(ValueError):
    """Fail-closed numerical payload validation error with a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


class NumericValueRule(str, Enum):
    """Closed pointwise rules available to the generic numerical decoder."""

    FINITE = "finite"
    NONNEGATIVE_FINITE = "nonnegative_finite"
    BINARY_0_1 = "binary_0_1"
    ROW_IDENTITIES = "row_identities"


@dataclass(frozen=True, slots=True)
class NumericArrayContract:
    """Exact content reference and pointwise rule for one NPY payload."""

    reference: PayloadRef
    value_rule: NumericValueRule = NumericValueRule.FINITE

    def __post_init__(self) -> None:
        if not isinstance(self.reference, PayloadRef):
            raise TypeError("reference must be a PayloadRef")
        if self.reference.kind is not PayloadKind.ARRAY:
            raise NumericPayloadError(
                "numeric_payload_kind_invalid",
                "numeric array contracts require an array PayloadRef",
            )
        if self.reference.shape is None or not self.reference.shape:
            raise NumericPayloadError(
                "numeric_row_axis_missing",
                "row-bound numeric arrays require a first row axis",
            )
        if not isinstance(self.value_rule, NumericValueRule):
            raise TypeError("value_rule must be a NumericValueRule")


@dataclass(frozen=True, slots=True)
class RowIdentityContract:
    """Content-derived row identity for one ordered identity array."""

    source: PayloadRef
    domain: str

    def __post_init__(self) -> None:
        if not isinstance(self.source, PayloadRef):
            raise TypeError("source must be a PayloadRef")
        if self.source.kind is not PayloadKind.ARRAY:
            raise NumericPayloadError(
                "row_identity_source_kind_invalid",
                "row identity source must be an array payload",
            )
        if (
            not isinstance(self.domain, str)
            or not self.domain
            or self.domain != self.domain.strip()
        ):
            raise NumericPayloadError(
                "row_identity_domain_invalid",
                "row identity domain must be a non-empty trimmed string",
            )


def _require_sha256(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise NumericPayloadError(
            "numeric_digest_invalid",
            f"{label} must be a lowercase SHA-256 digest",
        )
    return value


def _require_domain(value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise NumericPayloadError(
            "row_identity_domain_invalid",
            "row identity domain must be a non-empty trimmed string",
        )
    return value


@dataclass(frozen=True, slots=True, init=False)
class VerifiedRowIdentity:
    """Session-bound proof that ordered row content produced its declared hash."""

    sha256: str
    row_count: int
    source_payload_identity_sha256: str
    domain: str

    def __init__(
        self,
        *,
        _factory_token: object = None,
        sha256: str,
        row_count: int,
        source_payload_identity_sha256: str,
        domain: str,
    ) -> None:
        if _factory_token is not _VERIFIED_ROW_FACTORY_TOKEN:
            raise NumericPayloadError(
                "verified_row_factory_required",
                "verified row identities must be produced by a numeric session",
            )
        digest = _require_sha256(sha256, label="sha256")
        if isinstance(row_count, bool) or not isinstance(row_count, int):
            raise TypeError("row_count must be an integer")
        if row_count < 0:
            raise NumericPayloadError(
                "row_identity_count_invalid",
                "row_count must be nonnegative",
            )
        source_digest = _require_sha256(
            source_payload_identity_sha256,
            label="source_payload_identity_sha256",
        )
        checked_domain = _require_domain(domain)
        object.__setattr__(self, "sha256", digest)
        object.__setattr__(self, "row_count", row_count)
        object.__setattr__(
            self,
            "source_payload_identity_sha256",
            source_digest,
        )
        object.__setattr__(self, "domain", checked_domain)


def _immutable_numeric_snapshot(
    values: NDArray[np.generic],
) -> NDArray[np.generic]:
    """Return a C-contiguous array whose ultimate backing object is ``bytes``."""

    if not isinstance(values, np.ndarray):
        raise TypeError("values must be a NumPy array")
    contiguous = np.array(values, dtype=values.dtype, order="C", copy=True)
    backing = contiguous.tobytes(order="C")
    return np.frombuffer(backing, dtype=contiguous.dtype).reshape(contiguous.shape)


def _has_immutable_bytes_backing(values: NDArray[np.generic]) -> bool:
    base: object = values
    while isinstance(base, np.ndarray):
        next_base = base.base
        if next_base is None:
            return False
        base = next_base
    return isinstance(base, bytes)


@dataclass(frozen=True, slots=True, init=False)
class DecodedNumericArray:
    """C-contiguous, bytes-backed immutable payload and exact identity."""

    reference: PayloadRef
    values: NDArray[np.generic]
    npy_version: tuple[int, int]

    def __init__(
        self,
        *,
        _factory_token: object = None,
        reference: PayloadRef,
        values: NDArray[np.generic],
        npy_version: tuple[int, int],
    ) -> None:
        if _factory_token is not _DECODED_ARRAY_FACTORY_TOKEN:
            raise NumericPayloadError(
                "decoded_array_factory_required",
                "decoded arrays must be produced by the exact NPY decoder",
            )
        if not isinstance(reference, PayloadRef):
            raise TypeError("reference must be a PayloadRef")
        if reference.kind is not PayloadKind.ARRAY:
            raise NumericPayloadError(
                "decoded_array_reference_kind_invalid",
                "decoded arrays require an array PayloadRef",
            )
        snapshot = _immutable_numeric_snapshot(values)
        if (
            snapshot.flags.writeable
            or not snapshot.flags.c_contiguous
            or not _has_immutable_bytes_backing(snapshot)
        ):
            raise NumericPayloadError(
                "decoded_array_not_immutable",
                "decoded numerical arrays must have immutable bytes backing",
            )
        if reference.dtype is None or snapshot.dtype.str != reference.dtype:
            raise NumericPayloadError(
                "decoded_array_dtype_mismatch",
                "decoded array dtype differs from its PayloadRef",
            )
        if reference.shape is None or snapshot.shape != reference.shape:
            raise NumericPayloadError(
                "decoded_array_shape_mismatch",
                "decoded array shape differs from its PayloadRef",
            )
        if not np.all(np.isfinite(snapshot)):
            raise NumericPayloadError(
                "decoded_array_nonfinite",
                "decoded array contains NaN or infinity",
            )
        if (
            not isinstance(npy_version, tuple)
            or len(npy_version) != 2
            or any(type(component) is not int for component in npy_version)
            or npy_version not in SUPPORTED_NPY_VERSIONS
        ):
            raise NumericPayloadError(
                "npy_version_unsupported",
                "decoded array uses an unsupported NPY version",
            )
        object.__setattr__(self, "reference", reference)
        object.__setattr__(self, "values", snapshot)
        object.__setattr__(self, "npy_version", npy_version)


@dataclass(frozen=True, slots=True)
class L2AmplitudeRelation:
    """Predeclared row-wise relation between vectors and their L2 amplitude."""

    values: PayloadRef
    amplitude: PayloadRef
    axis: int
    rtol: float
    atol: float
    relation_id: str = "l2_amplitude_equals_vector_norm"

    def __post_init__(self) -> None:
        for name in ("values", "amplitude"):
            reference = getattr(self, name)
            if not isinstance(reference, PayloadRef):
                raise TypeError(f"{name} must be a PayloadRef")
            if reference.kind is not PayloadKind.ARRAY:
                raise NumericPayloadError(
                    "l2_relation_payload_kind_invalid",
                    "L2 amplitude relations require array payloads",
                )
        if self.axis != -1 or type(self.axis) is not int:
            raise NumericPayloadError(
                "l2_relation_axis_invalid",
                "the vector component axis must be the trailing axis (-1)",
            )
        assert self.values.shape is not None
        assert self.amplitude.shape is not None
        if len(self.values.shape) < 2:
            raise NumericPayloadError(
                "l2_relation_values_rank_invalid",
                "row-wise vector values must have at least two axes",
            )
        if self.values.shape[-1] < 1:
            raise NumericPayloadError(
                "l2_relation_components_empty",
                "row-wise vectors must have at least one component",
            )
        if self.amplitude.shape != self.values.shape[:-1]:
            raise NumericPayloadError(
                "l2_relation_shape_mismatch",
                "amplitude shape must equal values.shape[:-1]",
            )
        if self.values.row_identity_sha256 != self.amplitude.row_identity_sha256:
            raise NumericPayloadError(
                "l2_relation_row_identity_mismatch",
                "relation payloads must declare the same ordered row identity",
            )
        assert self.amplitude.dtype is not None
        if np.dtype(self.amplitude.dtype).kind not in {"b", "i", "u", "f"}:
            raise NumericPayloadError(
                "l2_relation_amplitude_dtype_invalid",
                "amplitude must use a real numerical dtype",
            )
        for name in ("rtol", "atol"):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, float)
                or not math.isfinite(value)
                or value < 0.0
            ):
                raise NumericPayloadError(
                    "l2_relation_tolerance_invalid",
                    f"{name} must be a finite nonnegative float",
                )
        if self.relation_id != "l2_amplitude_equals_vector_norm":
            raise NumericPayloadError(
                "l2_relation_id_invalid",
                "unsupported L2 amplitude relation identifier",
            )


@dataclass(frozen=True, slots=True, init=False)
class L2AmplitudeValidation:
    """Typed pass receipt for one predeclared L2-amplitude relation."""

    relation: L2AmplitudeRelation
    row_identity_sha256: str
    passed: bool = True

    def __init__(
        self,
        *,
        _factory_token: object = None,
        relation: L2AmplitudeRelation,
        row_identity_sha256: str,
        passed: bool = True,
    ) -> None:
        if _factory_token is not _L2_VALIDATION_FACTORY_TOKEN:
            raise NumericPayloadError(
                "l2_validation_factory_required",
                "L2 validation receipts must be produced by a numeric session",
            )
        if not isinstance(relation, L2AmplitudeRelation):
            raise TypeError("relation must be an L2AmplitudeRelation")
        digest = _require_sha256(
            row_identity_sha256,
            label="row_identity_sha256",
        )
        if (
            relation.values.row_identity_sha256 != digest
            or relation.amplitude.row_identity_sha256 != digest
        ):
            raise NumericPayloadError(
                "l2_validation_row_identity_mismatch",
                "validation row identity differs from its relation payloads",
            )
        if type(passed) is not bool or not passed:
            raise NumericPayloadError(
                "l2_relation_not_passed",
                "an L2 validation receipt can represent only a pass",
            )
        object.__setattr__(self, "relation", relation)
        object.__setattr__(self, "row_identity_sha256", digest)
        object.__setattr__(self, "passed", passed)


def _ordered_content_sha256(
    domain: str,
    value: NDArray[np.generic],
) -> str:
    array = np.asarray(value)
    descriptor = canonical_json_bytes(
        {
            "schema_version": "spirallens.ordered-content-identity.v0.1",
            "domain": domain,
            "dtype": array.dtype.str,
            "shape": list(array.shape),
        }
    )
    return hashlib.sha256(descriptor + b"\x00" + array.tobytes(order="C")).hexdigest()


def _close_descriptor_quietly(descriptor: int) -> None:
    try:
        os.close(descriptor)
    except OSError:
        pass


def _read_verified_descriptor_snapshot(
    descriptor: int,
    reference: PayloadRef,
) -> bytes:
    if reference.byte_length > MAX_NUMERIC_PAYLOAD_BYTES:
        raise NumericPayloadError(
            "numeric_payload_too_large",
            f"numeric payload exceeds {MAX_NUMERIC_PAYLOAD_BYTES} bytes",
        )
    opened = os.fstat(descriptor)
    if not stat.S_ISREG(opened.st_mode):
        raise NumericPayloadError(
            "numeric_payload_descriptor_invalid",
            "retained numerical payload is not a regular file",
        )
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    size = 0
    read_limit = reference.byte_length + 1
    while size < read_limit:
        chunk = os.read(descriptor, min(1024 * 1024, read_limit - size))
        if not chunk:
            break
        chunks.append(chunk)
        size += len(chunk)
    source = b"".join(chunks)
    if len(source) != reference.byte_length:
        raise NumericPayloadError(
            "numeric_payload_byte_length_mismatch",
            "retained numerical payload byte length differs",
        )
    if hashlib.sha256(source).hexdigest() != reference.sha256:
        raise NumericPayloadError(
            "numeric_payload_digest_mismatch",
            "retained numerical payload SHA-256 differs",
        )
    return source


def _decode_exact_npy(
    source: bytes,
    reference: PayloadRef,
) -> DecodedNumericArray:
    if reference.dtype is None or reference.shape is None:
        raise NumericPayloadError(
            "numeric_payload_metadata_missing",
            "array reference lacks dtype or shape",
        )
    stream = io.BytesIO(source)
    try:
        version = npy_format.read_magic(stream)
    except (EOFError, ValueError) as error:
        raise NumericPayloadError(
            "npy_magic_invalid",
            "payload is not a supported NPY stream",
        ) from error
    if version not in SUPPORTED_NPY_VERSIONS:
        raise NumericPayloadError(
            "npy_version_unsupported",
            f"NPY version {version!r} is unsupported",
        )
    try:
        if version == (1, 0):
            shape, fortran_order, dtype = npy_format.read_array_header_1_0(
                stream,
                max_header_size=MAX_NPY_HEADER_BYTES,
            )
        else:
            shape, fortran_order, dtype = npy_format.read_array_header_2_0(
                stream,
                max_header_size=MAX_NPY_HEADER_BYTES,
            )
    except (EOFError, TypeError, ValueError) as error:
        raise NumericPayloadError(
            "npy_header_invalid",
            "NPY header is malformed or exceeds the fixed limit",
        ) from error
    if (
        not isinstance(shape, tuple)
        or not shape
        or any(type(dimension) is not int or dimension < 0 for dimension in shape)
    ):
        raise NumericPayloadError(
            "npy_shape_invalid",
            "NPY shape dimensions must be nonnegative plain integers",
        )
    if (
        dtype.hasobject
        or dtype.fields is not None
        or dtype.subdtype is not None
        or dtype.kind not in {"b", "i", "u", "f", "c"}
    ):
        raise NumericPayloadError(
            "npy_dtype_not_numeric",
            "NPY dtype must be a simple non-object numerical dtype",
        )
    if dtype.str != reference.dtype:
        raise NumericPayloadError(
            "npy_dtype_mismatch",
            "NPY header dtype differs from the PayloadRef",
        )
    if shape != reference.shape:
        raise NumericPayloadError(
            "npy_shape_mismatch",
            "NPY header shape differs from the PayloadRef",
        )
    if fortran_order:
        raise NumericPayloadError(
            "npy_fortran_order_forbidden",
            "numeric payloads must use C order",
        )
    data_offset = stream.tell()
    element_count = math.prod(reference.shape)
    expected_data_bytes = element_count * dtype.itemsize
    if data_offset + expected_data_bytes != len(source):
        raise NumericPayloadError(
            "npy_extent_mismatch",
            "NPY payload is truncated or contains trailing bytes",
        )
    try:
        view = np.frombuffer(
            source,
            dtype=dtype,
            count=element_count,
            offset=data_offset,
        ).reshape(reference.shape)
    except (TypeError, ValueError) as error:
        raise NumericPayloadError(
            "npy_data_invalid",
            "NPY numerical data cannot be decoded exactly",
        ) from error
    if not np.all(np.isfinite(view)):
        raise NumericPayloadError(
            "numeric_payload_nonfinite",
            "numeric payload contains NaN or infinity",
        )
    return DecodedNumericArray(
        _factory_token=_DECODED_ARRAY_FACTORY_TOKEN,
        reference=reference,
        values=view,
        npy_version=version,
    )


def _apply_value_rule(
    decoded: DecodedNumericArray,
    rule: NumericValueRule,
) -> None:
    values = decoded.values
    if rule is NumericValueRule.FINITE:
        return
    if rule is NumericValueRule.NONNEGATIVE_FINITE:
        if values.dtype.kind not in {"b", "i", "u", "f"} or np.any(values < 0):
            raise NumericPayloadError(
                "numeric_value_rule_failed",
                "payload does not satisfy nonnegative_finite",
            )
        return
    if rule is NumericValueRule.BINARY_0_1:
        if values.dtype.kind not in {"b", "i", "u"} or not np.all(
            np.logical_or(values == 0, values == 1)
        ):
            raise NumericPayloadError(
                "numeric_value_rule_failed",
                "payload does not satisfy binary_0_1",
            )
        return
    if rule is NumericValueRule.ROW_IDENTITIES:
        if values.dtype.kind not in {"i", "u"} or values.ndim < 1:
            raise NumericPayloadError(
                "numeric_value_rule_failed",
                "row identities must be a non-scalar integer array",
            )
        component_count = math.prod(values.shape[1:])
        if component_count < 1:
            raise NumericPayloadError(
                "row_identity_components_empty",
                "each row identity must contain at least one component",
            )
        flattened = values.reshape(values.shape[0], component_count)
        if np.unique(flattened, axis=0).shape[0] != values.shape[0]:
            raise NumericPayloadError(
                "row_identity_duplicate",
                "ordered row identities must be unique",
            )
        return
    raise AssertionError(f"unhandled numeric value rule {rule!r}")


class NumericPayloadSession:
    """One authorization-bound set of retained, verified payload descriptors."""

    __slots__ = (
        "_closed",
        "_decoded",
        "_descriptors",
        "_verified_rows",
        "bundle_canonical_sha256",
        "bundle_source_sha256",
        "lineage",
        "requested_payloads",
    )

    def __init__(
        self,
        *,
        _factory_token: object,
        loaded_bundle: LoadedInstrumentBundle,
        descriptors: dict[PayloadRef, int],
        lineage: ValueAccessLineage,
        requested_payloads: tuple[PayloadRef, ...],
    ) -> None:
        if _factory_token is not _NUMERIC_SESSION_FACTORY_TOKEN:
            raise NumericPayloadError(
                "numeric_session_factory_required",
                "numeric sessions must be created by the authorized opener",
            )
        if not isinstance(descriptors, dict) or any(
            not isinstance(reference, PayloadRef)
            or type(descriptor) is not int
            or descriptor < 0
            for reference, descriptor in descriptors.items()
        ):
            raise NumericPayloadError(
                "retained_descriptor_invalid",
                "retained descriptors must map PayloadRef values to file descriptors",
            )
        if len(set(descriptors.values())) != len(descriptors):
            raise NumericPayloadError(
                "retained_descriptor_duplicate",
                "each retained payload must own a distinct descriptor",
            )
        if (
            not isinstance(requested_payloads, tuple)
            or not requested_payloads
            or any(
                not isinstance(reference, PayloadRef)
                for reference in requested_payloads
            )
            or len(set(requested_payloads)) != len(requested_payloads)
        ):
            raise NumericPayloadError(
                "numeric_payload_request_invalid",
                "requested payloads must be a non-empty unique PayloadRef tuple",
            )
        if set(descriptors) != set(requested_payloads):
            raise NumericPayloadError(
                "retained_payload_set_mismatch",
                "retained descriptor set differs from the request",
            )
        if not isinstance(lineage, ValueAccessLineage):
            raise TypeError("lineage must be a ValueAccessLineage")
        if lineage.consumer is not AtlasConsumer.NUMERIC_PAYLOAD_VALIDATION:
            raise NumericPayloadError(
                "numeric_lineage_consumer_invalid",
                "numeric sessions require the numeric payload consumer lineage",
            )
        self.bundle_source_sha256 = _require_sha256(
            loaded_bundle.source_sha256,
            label="bundle_source_sha256",
        )
        self.bundle_canonical_sha256 = _require_sha256(
            loaded_bundle.canonical_sha256,
            label="bundle_canonical_sha256",
        )
        self.lineage = lineage
        self.requested_payloads = requested_payloads
        self._descriptors = descriptors
        self._decoded: dict[PayloadRef, DecodedNumericArray] = {}
        self._verified_rows: list[VerifiedRowIdentity] = []
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        if self._closed:
            return
        for descriptor in self._descriptors.values():
            _close_descriptor_quietly(descriptor)
        self._descriptors.clear()
        self._closed = True

    def _require_open(self) -> None:
        if self._closed:
            raise NumericPayloadError(
                "numeric_session_closed",
                "numeric payload session is closed",
            )

    def _decode_reference(self, reference: PayloadRef) -> DecodedNumericArray:
        self._require_open()
        cached = self._decoded.get(reference)
        if cached is not None:
            return cached
        descriptor = self._descriptors.pop(reference, None)
        if descriptor is None:
            raise NumericPayloadError(
                "numeric_payload_not_requested",
                "payload was not retained by this numeric session",
            )
        try:
            source = _read_verified_descriptor_snapshot(descriptor, reference)
            decoded = _decode_exact_npy(source, reference)
        except OSError as error:
            raise NumericPayloadError(
                "numeric_payload_descriptor_unreadable",
                "retained numerical payload descriptor could not be read",
            ) from error
        finally:
            _close_descriptor_quietly(descriptor)
        self._decoded[reference] = decoded
        return decoded

    def decode_row_identity(
        self,
        contract: RowIdentityContract,
    ) -> VerifiedRowIdentity:
        """Recompute one ordered row digest from the exact identity payload."""

        if not isinstance(contract, RowIdentityContract):
            raise TypeError("contract must be a RowIdentityContract")
        decoded = self._decode_reference(contract.source)
        _apply_value_rule(decoded, NumericValueRule.ROW_IDENTITIES)
        digest = _ordered_content_sha256(contract.domain, decoded.values)
        if digest != contract.source.row_identity_sha256:
            raise NumericPayloadError(
                "row_identity_digest_mismatch",
                "ordered identity content differs from its declared row identity",
            )
        assert contract.source.shape is not None
        verified = VerifiedRowIdentity(
            _factory_token=_VERIFIED_ROW_FACTORY_TOKEN,
            sha256=digest,
            row_count=contract.source.shape[0],
            source_payload_identity_sha256=contract.source.identity_sha256,
            domain=contract.domain,
        )
        self._verified_rows.append(verified)
        return verified

    def decode_array(
        self,
        contract: NumericArrayContract,
        *,
        rows: VerifiedRowIdentity,
    ) -> DecodedNumericArray:
        """Decode one row-bound numerical array under a session proof."""

        if not isinstance(contract, NumericArrayContract):
            raise TypeError("contract must be a NumericArrayContract")
        if not isinstance(rows, VerifiedRowIdentity) or not any(
            candidate is rows for candidate in self._verified_rows
        ):
            raise NumericPayloadError(
                "row_identity_not_verified_by_session",
                "row identity must be verified by this session",
            )
        reference = contract.reference
        if reference.row_identity_sha256 != rows.sha256:
            raise NumericPayloadError(
                "row_identity_join_mismatch",
                "payload and verified row identity differ",
            )
        assert reference.shape is not None
        if reference.shape[0] != rows.row_count:
            raise NumericPayloadError(
                "row_count_join_mismatch",
                "payload first axis differs from the verified row count",
            )
        decoded = self._decode_reference(reference)
        _apply_value_rule(decoded, contract.value_rule)
        return decoded

    def validate_l2_amplitude(
        self,
        relation: L2AmplitudeRelation,
        *,
        rows: VerifiedRowIdentity,
    ) -> L2AmplitudeValidation:
        """Require amplitude to equal a predeclared vector L2 norm."""

        if not isinstance(relation, L2AmplitudeRelation):
            raise TypeError("relation must be an L2AmplitudeRelation")
        values = self.decode_array(
            NumericArrayContract(
                reference=relation.values,
                value_rule=NumericValueRule.FINITE,
            ),
            rows=rows,
        ).values
        amplitude = self.decode_array(
            NumericArrayContract(
                reference=relation.amplitude,
                value_rule=NumericValueRule.NONNEGATIVE_FINITE,
            ),
            rows=rows,
        ).values
        axis = relation.axis
        expected_shape = values.shape[:-1]
        if amplitude.shape != expected_shape:
            raise NumericPayloadError(
                "l2_relation_shape_mismatch",
                "amplitude shape differs from the vector norm output",
            )
        expected = np.linalg.norm(values, axis=axis)
        if not np.all(np.isfinite(expected)) or not np.allclose(
            amplitude,
            expected,
            rtol=relation.rtol,
            atol=relation.atol,
            equal_nan=False,
        ):
            raise NumericPayloadError(
                "l2_relation_failed",
                "amplitude differs from the predeclared L2 norm relation",
            )
        return L2AmplitudeValidation(
            _factory_token=_L2_VALIDATION_FACTORY_TOKEN,
            relation=relation,
            row_identity_sha256=rows.sha256,
        )

    def __enter__(self) -> Self:
        self._require_open()
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()


@contextmanager
def open_numeric_payload_session(
    bundle_path: str | Path,
    *,
    requested_payloads: tuple[PayloadRef, ...],
    parent_policy: AtlasAccessPolicy,
    expected_parent_policy_sha256: str,
    expected_bundle_source_sha256: str,
    expected_bundle_canonical_sha256: str,
) -> Iterator[NumericPayloadSession]:
    """Authorize, validate, and retain exact payload fds without path reopening."""

    # This authorization and trusted-parent check intentionally precedes every
    # path inspection, bundle open, and payload byte read.
    lineage = bind_value_access_lineage(
        parent_policy,
        expected_parent_policy_sha256=expected_parent_policy_sha256,
        consumer=AtlasConsumer.NUMERIC_PAYLOAD_VALIDATION,
    )
    if not isinstance(requested_payloads, tuple) or not requested_payloads:
        raise NumericPayloadError(
            "numeric_payload_request_invalid",
            "requested_payloads must be a non-empty tuple",
        )
    if any(not isinstance(reference, PayloadRef) for reference in requested_payloads):
        raise TypeError("requested_payloads must contain only PayloadRef values")
    if len(set(requested_payloads)) != len(requested_payloads):
        raise NumericPayloadError(
            "numeric_payload_request_duplicate",
            "requested payload references must be unique",
        )
    if any(reference.kind is not PayloadKind.ARRAY for reference in requested_payloads):
        raise NumericPayloadError(
            "numeric_payload_kind_invalid",
            "numeric sessions retain only array payloads",
        )
    if any(
        reference.byte_length > MAX_NUMERIC_PAYLOAD_BYTES
        for reference in requested_payloads
    ):
        raise NumericPayloadError(
            "numeric_payload_too_large",
            f"numeric payload exceeds {MAX_NUMERIC_PAYLOAD_BYTES} bytes",
        )

    loaded, descriptors = _load_instrument_bundle_retaining_payloads(
        bundle_path,
        expected_source_sha256=expected_bundle_source_sha256,
        expected_canonical_sha256=expected_bundle_canonical_sha256,
        retained_payload_refs=frozenset(requested_payloads),
    )
    try:
        session = NumericPayloadSession(
            _factory_token=_NUMERIC_SESSION_FACTORY_TOKEN,
            loaded_bundle=loaded,
            descriptors=descriptors,
            lineage=lineage,
            requested_payloads=requested_payloads,
        )
    except BaseException:
        for descriptor in descriptors.values():
            _close_descriptor_quietly(descriptor)
        raise
    try:
        yield session
    finally:
        session.close()
