"""Strict receipts for the bounded public-example engineering lane.

The receipt deliberately records engineering facts, not scientific evidence.
It can be constructed only from a complete, checksum-validated activation
atlas whose immutable request agrees with a pre-run protocol binding.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import numpy as np

from .engineering_protocol import (
    LoadedPublicExamplePlumbingProtocol,
    PublicExamplePlumbingProtocolError,
    _UnsupportedEngineeringModelProfileError,
    _require_engineering_model_profile,
    validate_engineering_request_binding,
)
from spirallens.adapters import CAPTURE_IMPLEMENTATION_VERSION

from .store import ATLAS_SCHEMA_VERSION, load_manifest, token_ids_sha256

PUBLIC_EXAMPLE_PLUMBING_RECEIPT_SCHEMA_VERSION = (
    "spirallens.public-example-plumbing-receipt.v0.1"
)
MAX_PUBLIC_EXAMPLE_PLUMBING_RECEIPT_BYTES = 1024 * 1024

_ARRAY_NAMES = (
    "logit_summary",
    "norm_summary",
    "prediction_ids",
    "resid_post",
    "resid_pre",
    "token_ids",
)
_D0_D8 = {f"d{index}": "not_run" for index in range(9)}
_ANALYSIS_STATUS = {
    name: "not_run"
    for name in (
        "candidate",
        "neighbor",
        "instrument",
        "graph",
        "field",
        "core",
        "loop",
        "holonomy",
        "winding",
        "semantic",
        "sae",
        "causal",
        "integer",
    )
}
_GATES = {
    "capture": "pass",
    "storage": "pass",
    "checksum": "pass",
    "reload": "pass",
}
_FACTS = {
    "model_accessed": True,
    "activation_values_persisted": True,
    "tokenizer_runtime_verified": False,
}
_BOUNDARIES = {
    "scientific_claim_eligible": False,
    "p1_instrument_consumed": False,
    "integer_output_authorized": False,
}


class PublicExamplePlumbingReceiptError(ValueError):
    """Raised when an engineering receipt violates its closed contract."""


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise PublicExamplePlumbingReceiptError(
            f"receipt contains a non-canonical JSON value: {error}"
        ) from error


def _reject_duplicate_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise PublicExamplePlumbingReceiptError(
                f"receipt JSON contains duplicate key {key!r}"
            )
        result[key] = value
    return result


def _reject_nonfinite_constant(value: str) -> None:
    raise PublicExamplePlumbingReceiptError(
        f"receipt JSON contains non-finite constant {value!r}"
    )


def _parse_canonical_json(source: bytes) -> dict[str, object]:
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError as error:
        raise PublicExamplePlumbingReceiptError("receipt must be UTF-8 JSON") from error
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_constant,
        )
    except PublicExamplePlumbingReceiptError:
        raise
    except json.JSONDecodeError as error:
        raise PublicExamplePlumbingReceiptError("receipt is invalid JSON") from error
    if not isinstance(value, dict):
        raise PublicExamplePlumbingReceiptError("receipt must contain one JSON object")
    if _canonical_bytes(value) != source:
        raise PublicExamplePlumbingReceiptError("receipt source is not canonical JSON")
    return value


def _mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise PublicExamplePlumbingReceiptError(f"{label} must be a JSON object")
    return value


def _exact_keys(
    value: Mapping[str, object],
    expected: set[str],
    *,
    label: str,
) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise PublicExamplePlumbingReceiptError(
            f"{label} fields differ from the contract: missing={missing}, extra={extra}"
        )


def _sha256(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise PublicExamplePlumbingReceiptError(
            f"{label} must be a lowercase SHA-256 digest"
        )
    return value


def _nonempty_string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise PublicExamplePlumbingReceiptError(f"{label} must be a non-empty string")
    return value


def _plain_positive_int(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PublicExamplePlumbingReceiptError(f"{label} must be a positive integer")
    return value


def _relative_output_id(value: object) -> str:
    output_id = _nonempty_string(value, label="manifest.output_id")
    if "\\" in output_id:
        raise PublicExamplePlumbingReceiptError(
            "manifest.output_id must use POSIX separators"
        )
    path = PurePosixPath(output_id)
    if (
        path.is_absolute()
        or output_id in {".", ".."}
        or any(part in {"", ".", ".."} for part in path.parts)
        or str(path) != output_id
    ):
        raise PublicExamplePlumbingReceiptError(
            "manifest.output_id must be a normalized relative output identity"
        )
    return output_id


def _string_map(value: object, *, label: str) -> dict[str, str]:
    item = _mapping(value, label=label)
    if not item:
        raise PublicExamplePlumbingReceiptError(f"{label} must not be empty")
    result: dict[str, str] = {}
    for key, raw in item.items():
        result[key] = _nonempty_string(raw, label=f"{label}.{key}")
    return result


@dataclass(frozen=True, slots=True)
class PublicExampleProtocolReceiptBinding:
    """Small integration seam between the tracked protocol and its receipt."""

    source_sha256: str
    canonical_sha256: str
    output_id: str
    token_ids: tuple[int, ...]
    model_id: str
    model_revision: str
    config_blob_sha256: str
    model_blob_sha256: str

    def __post_init__(self) -> None:
        _sha256(self.source_sha256, label="protocol.source_sha256")
        _sha256(self.canonical_sha256, label="protocol.canonical_sha256")
        _relative_output_id(self.output_id)
        if (
            not isinstance(self.token_ids, tuple)
            or not self.token_ids
            or any(
                isinstance(value, bool) or not isinstance(value, int) or value < 0
                for value in self.token_ids
            )
            or len(set(self.token_ids)) != len(self.token_ids)
        ):
            raise PublicExamplePlumbingReceiptError(
                "protocol token_ids must be a non-empty tuple of unique "
                "non-negative integers"
            )
        _nonempty_string(self.model_id, label="protocol.model_id")
        _nonempty_string(
            self.model_revision,
            label="protocol.model_revision",
        )
        _sha256(
            self.config_blob_sha256,
            label="protocol.config_blob_sha256",
        )
        _sha256(
            self.model_blob_sha256,
            label="protocol.model_blob_sha256",
        )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, object],
    ) -> PublicExampleProtocolReceiptBinding:
        """Build the explicit seam while the tracked protocol API stabilizes."""

        item = _mapping(value, label="protocol receipt binding")
        _exact_keys(
            item,
            {
                "source_sha256",
                "canonical_sha256",
                "output_id",
                "token_ids",
                "model_id",
                "model_revision",
                "config_blob_sha256",
                "model_blob_sha256",
            },
            label="protocol receipt binding",
        )
        raw_token_ids = item["token_ids"]
        if not isinstance(raw_token_ids, Sequence) or isinstance(
            raw_token_ids, (str, bytes, bytearray)
        ):
            raise PublicExamplePlumbingReceiptError(
                "protocol receipt binding token_ids must be a sequence"
            )
        return cls(
            source_sha256=_sha256(
                item["source_sha256"],
                label="protocol.source_sha256",
            ),
            canonical_sha256=_sha256(
                item["canonical_sha256"],
                label="protocol.canonical_sha256",
            ),
            output_id=_relative_output_id(item["output_id"]),
            token_ids=tuple(raw_token_ids),  # type: ignore[arg-type]
            model_id=_nonempty_string(
                item["model_id"],
                label="protocol.model_id",
            ),
            model_revision=_nonempty_string(
                item["model_revision"],
                label="protocol.model_revision",
            ),
            config_blob_sha256=_sha256(
                item["config_blob_sha256"],
                label="protocol.config_blob_sha256",
            ),
            model_blob_sha256=_sha256(
                item["model_blob_sha256"],
                label="protocol.model_blob_sha256",
            ),
        )


def _validate_receipt_payload(value: Mapping[str, object]) -> None:
    root = _mapping(value, label="public-example plumbing receipt")
    _exact_keys(
        root,
        {
            "schema_version",
            "protocol",
            "implementation",
            "manifest",
            "model",
            "runtime",
            "arrays",
            "row_count",
            "gates",
            "execution_facts",
            "claim_boundary",
            "d0_d8",
            "analysis_status",
        },
        label="public-example plumbing receipt",
    )
    if root["schema_version"] != (PUBLIC_EXAMPLE_PLUMBING_RECEIPT_SCHEMA_VERSION):
        raise PublicExamplePlumbingReceiptError(
            "unsupported public-example plumbing receipt schema"
        )

    protocol = _mapping(root["protocol"], label="protocol")
    _exact_keys(
        protocol,
        {"source_sha256", "canonical_sha256"},
        label="protocol",
    )
    _sha256(protocol["source_sha256"], label="protocol.source_sha256")
    _sha256(
        protocol["canonical_sha256"],
        label="protocol.canonical_sha256",
    )

    implementation = _mapping(root["implementation"], label="implementation")
    _exact_keys(
        implementation,
        {
            "repository",
            "commit",
            "repository_path",
            "module_sha256",
        },
        label="implementation",
    )
    _nonempty_string(
        implementation["repository"],
        label="implementation.repository",
    )
    commit = _nonempty_string(
        implementation["commit"],
        label="implementation.commit",
    )
    if len(commit) != 40 or any(
        character not in "0123456789abcdef" for character in commit
    ):
        raise PublicExamplePlumbingReceiptError(
            "implementation.commit must be a lowercase Git commit"
        )
    _nonempty_string(
        implementation["repository_path"],
        label="implementation.repository_path",
    )
    _sha256(
        implementation["module_sha256"],
        label="implementation.module_sha256",
    )

    manifest = _mapping(root["manifest"], label="manifest")
    _exact_keys(
        manifest,
        {
            "output_id",
            "sha256",
            "run_id",
            "request_identity_sha256",
            "capture_fingerprint",
        },
        label="manifest",
    )
    _relative_output_id(manifest["output_id"])
    _sha256(manifest["sha256"], label="manifest.sha256")
    _nonempty_string(manifest["run_id"], label="manifest.run_id")
    _sha256(
        manifest["request_identity_sha256"],
        label="manifest.request_identity_sha256",
    )
    _sha256(
        manifest["capture_fingerprint"],
        label="manifest.capture_fingerprint",
    )

    model = _mapping(root["model"], label="model")
    _exact_keys(
        model,
        {
            "model_id",
            "requested_revision",
            "resolved_revision",
            "config_blob_sha256",
            "model_blob_sha256",
        },
        label="model",
    )
    try:
        _require_engineering_model_profile(model["model_id"])
    except _UnsupportedEngineeringModelProfileError as error:
        raise PublicExamplePlumbingReceiptError(
            "receipt model is not registered for public-example engineering"
        ) from error
    requested_revision = _nonempty_string(
        model["requested_revision"],
        label="model.requested_revision",
    )
    resolved_revision = _nonempty_string(
        model["resolved_revision"],
        label="model.resolved_revision",
    )
    if requested_revision != resolved_revision:
        raise PublicExamplePlumbingReceiptError(
            "model requested and resolved revisions must be identical"
        )
    _sha256(
        model["config_blob_sha256"],
        label="model.config_blob_sha256",
    )
    _sha256(
        model["model_blob_sha256"],
        label="model.model_blob_sha256",
    )

    runtime = _mapping(root["runtime"], label="runtime")
    _exact_keys(
        runtime,
        {
            "device",
            "activation_dtype",
            "python_version",
            "numpy_version",
            "torch_version",
            "transformers_version",
            "spirallens_version",
        },
        label="runtime",
    )
    if runtime["device"] != "cpu":
        raise PublicExamplePlumbingReceiptError(
            "public-example plumbing runtime must be CPU"
        )
    if runtime["activation_dtype"] != "float32":
        raise PublicExamplePlumbingReceiptError(
            "public-example plumbing activation dtype must be float32"
        )
    for key in (
        "python_version",
        "numpy_version",
        "torch_version",
        "transformers_version",
        "spirallens_version",
    ):
        _nonempty_string(runtime[key], label=f"runtime.{key}")

    arrays = root["arrays"]
    if not isinstance(arrays, list) or len(arrays) != len(_ARRAY_NAMES):
        raise PublicExamplePlumbingReceiptError(
            "arrays must list every activation-atlas array"
        )
    observed_names: list[str] = []
    for index, raw in enumerate(arrays):
        item = _mapping(raw, label=f"arrays[{index}]")
        _exact_keys(
            item,
            {"name", "file_size_bytes", "sha256"},
            label=f"arrays[{index}]",
        )
        observed_names.append(
            _nonempty_string(item["name"], label=f"arrays[{index}].name")
        )
        _plain_positive_int(
            item["file_size_bytes"],
            label=f"arrays[{index}].file_size_bytes",
        )
        _sha256(
            item["sha256"],
            label=f"arrays[{index}].sha256",
        )
    if tuple(observed_names) != _ARRAY_NAMES:
        raise PublicExamplePlumbingReceiptError(
            "array names must be unique and canonically sorted"
        )

    row_count = _plain_positive_int(root["row_count"], label="row_count")
    del row_count
    for field, expected in (
        ("gates", _GATES),
        ("execution_facts", _FACTS),
        ("claim_boundary", _BOUNDARIES),
        ("d0_d8", _D0_D8),
        ("analysis_status", _ANALYSIS_STATUS),
    ):
        item = _mapping(root[field], label=field)
        exact = set(item) == set(expected) and all(
            (type(item[name]) is bool and item[name] is expected_value)
            if type(expected_value) is bool
            else (
                type(item[name]) is type(expected_value)
                and item[name] == expected_value
            )
            for name, expected_value in expected.items()
        )
        if not exact:
            raise PublicExamplePlumbingReceiptError(
                f"{field} differs from the closed engineering contract"
            )


@dataclass(frozen=True, slots=True)
class PublicExamplePlumbingReceipt:
    """One strict canonical public-example engineering receipt."""

    _canonical_json: str

    def __post_init__(self) -> None:
        if not isinstance(self._canonical_json, str):
            raise TypeError("receipt canonical JSON must be a string")
        _validate_receipt_payload(
            _parse_canonical_json(self._canonical_json.encode("utf-8"))
        )

    @classmethod
    def from_payload(
        cls,
        value: Mapping[str, object],
    ) -> PublicExamplePlumbingReceipt:
        _validate_receipt_payload(value)
        return cls(_canonical_bytes(dict(value)).decode("utf-8"))

    def to_dict(self) -> dict[str, object]:
        return _parse_canonical_json(self.canonical_bytes)

    @property
    def canonical_bytes(self) -> bytes:
        return self._canonical_json.encode("utf-8")

    @property
    def canonical_sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()

    @property
    def sha256(self) -> str:
        return self.canonical_sha256


def _protocol_binding(
    value: PublicExampleProtocolReceiptBinding | Mapping[str, object],
) -> PublicExampleProtocolReceiptBinding:
    if isinstance(value, PublicExampleProtocolReceiptBinding):
        return value
    return PublicExampleProtocolReceiptBinding.from_mapping(value)


def _manifest_array_receipts(
    manifest: Mapping[str, object],
) -> list[dict[str, object]]:
    raw_arrays = _mapping(manifest.get("arrays"), label="atlas arrays")
    if set(raw_arrays) != set(_ARRAY_NAMES):
        raise PublicExamplePlumbingReceiptError(
            "atlas arrays differ from the receipt contract"
        )
    arrays: list[dict[str, object]] = []
    for name in _ARRAY_NAMES:
        spec = _mapping(raw_arrays[name], label=f"atlas arrays.{name}")
        arrays.append(
            {
                "name": name,
                "file_size_bytes": _plain_positive_int(
                    spec.get("file_size_bytes"),
                    label=f"atlas arrays.{name}.file_size_bytes",
                ),
                "sha256": _sha256(
                    spec.get("sha256"),
                    label=f"atlas arrays.{name}.sha256",
                ),
            }
        )
    return arrays


def _receipt_from_validated_atlas_manifest(
    manifest: Mapping[str, object],
    *,
    manifest_sha256: str,
    protocol_binding: (PublicExampleProtocolReceiptBinding | Mapping[str, object]),
) -> PublicExamplePlumbingReceipt:
    """Cross-check a validated complete atlas against its pre-run binding.

    This is the integration seam for a protocol loader: callers pass its
    source/canonical identities and the exact frozen execution fields through
    :class:`PublicExampleProtocolReceiptBinding`.
    """

    binding = _protocol_binding(protocol_binding)
    if manifest.get("schema_version") != ATLAS_SCHEMA_VERSION:
        raise PublicExamplePlumbingReceiptError(
            "atlas schema does not match the public-example receipt"
        )
    if manifest.get("status") != "complete":
        raise PublicExamplePlumbingReceiptError(
            "public-example receipt requires a complete atlas"
        )
    request = _mapping(manifest.get("request"), label="atlas request")
    model = _mapping(manifest.get("model"), label="atlas model")
    try:
        embedded_protocol = validate_engineering_request_binding(
            request,
            manifest_model=model,
        )
    except (PublicExamplePlumbingProtocolError, TypeError) as error:
        raise PublicExamplePlumbingReceiptError(
            f"atlas engineering binding is invalid: {error}"
        ) from error
    if embedded_protocol is None:
        raise PublicExamplePlumbingReceiptError(
            "atlas lacks its pre-run public-example engineering binding"
        )
    embedded_binding = _mapping(
        request.get("public_example_plumbing_protocol_binding"),
        label="atlas engineering binding",
    )
    if (
        embedded_binding.get("source_sha256") != binding.source_sha256
        or embedded_binding.get("canonical_sha256") != binding.canonical_sha256
        or embedded_protocol.canonical_sha256 != binding.canonical_sha256
        or embedded_protocol.capture.output_id != binding.output_id
        or embedded_protocol.token_selection.token_ids != binding.token_ids
        or embedded_protocol.model.model_id != binding.model_id
        or embedded_protocol.model.revision != binding.model_revision
        or dict(embedded_protocol.model.files).get("config.json")
        != binding.config_blob_sha256
        or dict(embedded_protocol.model.files).get("model.safetensors")
        != binding.model_blob_sha256
    ):
        raise PublicExamplePlumbingReceiptError(
            "caller protocol identity differs from the atlas embedded binding"
        )
    capture = _mapping(manifest.get("capture"), label="atlas capture")
    environment = _mapping(
        manifest.get("environment"),
        label="atlas environment",
    )
    progress = _mapping(manifest.get("progress"), label="atlas progress")

    expected_token_ids = np.asarray(binding.token_ids, dtype="<i8")
    row_count = len(binding.token_ids)
    total_rows = _plain_positive_int(
        progress.get("total_rows"),
        label="atlas progress.total_rows",
    )
    completed_rows = _plain_positive_int(
        progress.get("completed_rows"),
        label="atlas progress.completed_rows",
    )
    if (
        request.get("num_tokens") != row_count
        or total_rows != row_count
        or completed_rows != row_count
        or request.get("token_ids_sha256") != token_ids_sha256(expected_token_ids)
    ):
        raise PublicExamplePlumbingReceiptError(
            "atlas rows do not equal the protocol's explicit token IDs"
        )

    if (
        request.get("model_id") != binding.model_id
        or model.get("model_id") != binding.model_id
        or request.get("requested_model_revision") != binding.model_revision
        or request.get("resolved_model_revision") != binding.model_revision
        or model.get("requested_revision") != binding.model_revision
        or model.get("resolved_revision") != binding.model_revision
    ):
        raise PublicExamplePlumbingReceiptError(
            "atlas model identity differs from the protocol binding"
        )
    if (
        request.get("config_blob_sha256") != binding.config_blob_sha256
        or request.get("model_blob_sha256") != binding.model_blob_sha256
    ):
        raise PublicExamplePlumbingReceiptError(
            "atlas config/model blob hashes differ from the protocol binding"
        )
    if request.get("request_identity_sha256") is None:
        raise PublicExamplePlumbingReceiptError(
            "atlas request is missing its immutable request identity"
        )
    request_identity_sha256 = _sha256(
        request["request_identity_sha256"],
        label="atlas request_identity_sha256",
    )
    capture_fingerprint = _sha256(
        manifest.get("capture_fingerprint"),
        label="atlas capture_fingerprint",
    )
    if request.get("capture_fingerprint") != capture_fingerprint:
        raise PublicExamplePlumbingReceiptError(
            "atlas request capture fingerprint differs from its manifest"
        )

    try:
        profile = _require_engineering_model_profile(binding.model_id)
    except _UnsupportedEngineeringModelProfileError as error:
        raise PublicExamplePlumbingReceiptError(
            "protocol model is not registered for public-example engineering"
        ) from error
    implementation = _mapping(
        capture.get("capture_implementation"),
        label="atlas capture implementation",
    )
    layout = capture.get("effective_parameter_layout")
    if (
        implementation
        != {
            "name": "PythiaAdapter.observe_batch.residual_hooks",
            "version": CAPTURE_IMPLEMENTATION_VERSION,
            "accelerator_to_cpu_copy": "synchronous",
            "activation_dtype": "float32",
        }
        or layout != profile.effective_parameter_layout
    ):
        raise PublicExamplePlumbingReceiptError(
            f"atlas capture is not the exact {profile.display_name} "
            "CPU/float32 production implementation"
        )

    runtime = {
        "device": "cpu",
        "activation_dtype": "float32",
        "python_version": _nonempty_string(
            environment.get("python"),
            label="atlas environment.python",
        ),
        "numpy_version": _nonempty_string(
            environment.get("numpy"),
            label="atlas environment.numpy",
        ),
        "torch_version": _nonempty_string(
            capture.get("torch_version"),
            label="atlas capture.torch_version",
        ),
        "transformers_version": _nonempty_string(
            capture.get("transformers_version"),
            label="atlas capture.transformers_version",
        ),
        "spirallens_version": _nonempty_string(
            capture.get("spirallens_version"),
            label="atlas capture.spirallens_version",
        ),
    }
    if environment.get("torch") != runtime["torch_version"]:
        raise PublicExamplePlumbingReceiptError(
            "atlas environment and capture torch versions differ"
        )

    payload = {
        "schema_version": (PUBLIC_EXAMPLE_PLUMBING_RECEIPT_SCHEMA_VERSION),
        "protocol": {
            "source_sha256": binding.source_sha256,
            "canonical_sha256": binding.canonical_sha256,
        },
        "implementation": {
            "repository": embedded_protocol.source.repository,
            "commit": embedded_protocol.source.implementation_commit,
            "repository_path": (
                embedded_protocol.source.implementation_repository_path
            ),
            "module_sha256": (embedded_protocol.source.implementation_module_sha256),
        },
        "manifest": {
            "output_id": binding.output_id,
            "sha256": _sha256(
                manifest_sha256,
                label="manifest_sha256",
            ),
            "run_id": _nonempty_string(
                manifest.get("run_id"),
                label="atlas run_id",
            ),
            "request_identity_sha256": request_identity_sha256,
            "capture_fingerprint": capture_fingerprint,
        },
        "model": {
            "model_id": binding.model_id,
            "requested_revision": binding.model_revision,
            "resolved_revision": binding.model_revision,
            "config_blob_sha256": binding.config_blob_sha256,
            "model_blob_sha256": binding.model_blob_sha256,
        },
        "runtime": runtime,
        "arrays": _manifest_array_receipts(manifest),
        "row_count": row_count,
        "gates": dict(_GATES),
        "execution_facts": dict(_FACTS),
        "claim_boundary": dict(_BOUNDARIES),
        "d0_d8": dict(_D0_D8),
        "analysis_status": dict(_ANALYSIS_STATUS),
    }
    return PublicExamplePlumbingReceipt.from_payload(payload)


def _build_public_example_plumbing_receipt(
    atlas_output_dir: str | Path,
    *,
    loaded_protocol: LoadedPublicExamplePlumbingProtocol,
) -> PublicExamplePlumbingReceipt:
    """Validate, checksum, reload, and bind one complete atlas directory."""

    if not isinstance(
        loaded_protocol,
        LoadedPublicExamplePlumbingProtocol,
    ):
        raise TypeError("loaded_protocol must be a LoadedPublicExamplePlumbingProtocol")
    protocol = loaded_protocol.protocol
    root = Path(atlas_output_dir).resolve()
    if root.name != protocol.capture.output_id:
        raise PublicExamplePlumbingReceiptError(
            "atlas directory basename differs from the frozen output_id"
        )
    manifest_path = root / "manifest.json"
    before = manifest_path.lstat()
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise PublicExamplePlumbingReceiptError(
            "atlas manifest must be a regular non-symlink file"
        )
    source_before = manifest_path.read_bytes()
    if len(source_before) > MAX_PUBLIC_EXAMPLE_PLUMBING_RECEIPT_BYTES * 16:
        raise PublicExamplePlumbingReceiptError(
            "atlas manifest exceeds the engineering receipt read limit"
        )
    manifest = load_manifest(root, verify_checksums=True)
    reloaded = load_manifest(root, verify_checksums=True)
    after = manifest_path.lstat()
    source_after = manifest_path.read_bytes()
    if (
        manifest != reloaded
        or source_before != source_after
        or stat.S_ISLNK(after.st_mode)
        or not stat.S_ISREG(after.st_mode)
        or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino)
    ):
        raise PublicExamplePlumbingReceiptError(
            "atlas manifest changed during checksum/reload validation"
        )
    binding = PublicExampleProtocolReceiptBinding(
        source_sha256=loaded_protocol.source_sha256,
        canonical_sha256=loaded_protocol.canonical_sha256,
        output_id=protocol.capture.output_id,
        token_ids=protocol.token_selection.token_ids,
        model_id=protocol.model.model_id,
        model_revision=protocol.model.revision,
        config_blob_sha256=dict(protocol.model.files)["config.json"],
        model_blob_sha256=dict(protocol.model.files)["model.safetensors"],
    )
    return _receipt_from_validated_atlas_manifest(
        manifest,
        manifest_sha256=hashlib.sha256(source_before).hexdigest(),
        protocol_binding=binding,
    )


def _safe_regular_file_bytes(path: Path) -> bytes:
    if not path.is_absolute():
        raise PublicExamplePlumbingReceiptError("receipt path must be absolute")
    for parent in reversed((path.parent, *path.parent.parents)):
        details = parent.lstat()
        if stat.S_ISLNK(details.st_mode) or not stat.S_ISDIR(details.st_mode):
            raise PublicExamplePlumbingReceiptError(
                "receipt parent chain must contain only real directories"
            )
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise PublicExamplePlumbingReceiptError("receipt must be a regular file")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(
                descriptor,
                min(
                    1024 * 1024,
                    MAX_PUBLIC_EXAMPLE_PLUMBING_RECEIPT_BYTES + 1 - total,
                ),
            )
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_PUBLIC_EXAMPLE_PLUMBING_RECEIPT_BYTES:
                raise PublicExamplePlumbingReceiptError(
                    "receipt exceeds the maximum size"
                )
    finally:
        os.close(descriptor)
    after = path.lstat()
    if (
        stat.S_ISLNK(after.st_mode)
        or not stat.S_ISREG(after.st_mode)
        or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino)
    ):
        raise PublicExamplePlumbingReceiptError("receipt identity changed during read")
    return b"".join(chunks)


def load_public_example_plumbing_receipt(
    path: str | Path,
    *,
    expected_source_sha256: str,
    expected_canonical_sha256: str,
) -> PublicExamplePlumbingReceipt:
    """Load only canonical bytes matching both caller-supplied identities."""

    expected_source = _sha256(
        expected_source_sha256,
        label="expected_source_sha256",
    )
    expected_canonical = _sha256(
        expected_canonical_sha256,
        label="expected_canonical_sha256",
    )
    source = _safe_regular_file_bytes(Path(path))
    if hashlib.sha256(source).hexdigest() != expected_source:
        raise PublicExamplePlumbingReceiptError(
            "receipt source SHA-256 differs from the expected digest"
        )
    receipt = PublicExamplePlumbingReceipt.from_payload(_parse_canonical_json(source))
    if receipt.canonical_sha256 != expected_canonical:
        raise PublicExamplePlumbingReceiptError(
            "receipt canonical SHA-256 differs from the expected digest"
        )
    if receipt.canonical_bytes != source:
        raise PublicExamplePlumbingReceiptError(
            "receipt canonical readback differs from its source"
        )
    return receipt


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise OSError("receipt write made no forward progress")
        offset += written


def write_public_example_plumbing_receipt(
    path: str | Path,
    receipt: PublicExamplePlumbingReceipt,
) -> PublicExamplePlumbingReceipt:
    """Atomically publish a complete receipt without replacing any leaf."""

    if not isinstance(receipt, PublicExamplePlumbingReceipt):
        raise TypeError("receipt must be a PublicExamplePlumbingReceipt")
    output = Path(path)
    if not output.is_absolute():
        raise PublicExamplePlumbingReceiptError("receipt output path must be absolute")
    for parent in reversed((output.parent, *output.parent.parents)):
        details = parent.lstat()
        if stat.S_ISLNK(details.st_mode) or not stat.S_ISDIR(details.st_mode):
            raise PublicExamplePlumbingReceiptError(
                "receipt output parent chain must contain real directories"
            )
    directory_flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        directory_flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        directory_flags |= os.O_NOFOLLOW
    parent_descriptor = os.open(output.parent, directory_flags)
    temporary_name = f".{output.name}.{uuid.uuid4().hex}.tmp"
    file_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        file_flags |= os.O_NOFOLLOW
    temporary_descriptor = os.open(
        temporary_name,
        file_flags,
        0o600,
        dir_fd=parent_descriptor,
    )
    reserved = os.fstat(temporary_descriptor)
    published = False
    try:
        _write_all(temporary_descriptor, receipt.canonical_bytes)
        os.fsync(temporary_descriptor)
        os.close(temporary_descriptor)
        temporary_descriptor = -1
        try:
            os.link(
                temporary_name,
                output.name,
                src_dir_fd=parent_descriptor,
                dst_dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
        except FileExistsError as error:
            raise PublicExamplePlumbingReceiptError(
                "receipt output already exists; overwrite is forbidden"
            ) from error
        published = True
        os.fsync(parent_descriptor)
    finally:
        if temporary_descriptor >= 0:
            os.close(temporary_descriptor)
        try:
            current = os.stat(
                temporary_name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            current = None
        if (
            current is not None
            and stat.S_ISREG(current.st_mode)
            and (current.st_dev, current.st_ino) == (reserved.st_dev, reserved.st_ino)
        ):
            os.unlink(temporary_name, dir_fd=parent_descriptor)
            os.fsync(parent_descriptor)
        os.close(parent_descriptor)

    if not published:
        raise PublicExamplePlumbingReceiptError("receipt publication did not complete")
    loaded = load_public_example_plumbing_receipt(
        output,
        expected_source_sha256=receipt.sha256,
        expected_canonical_sha256=receipt.canonical_sha256,
    )
    if loaded != receipt:
        raise PublicExamplePlumbingReceiptError(
            "published receipt strict reload differs"
        )
    return loaded
