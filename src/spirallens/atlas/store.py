"""Fail-closed, resumable ``.npy`` storage for activation atlases."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np
from spirallens.atlas.engineering_protocol import (
    PublicExamplePlumbingProtocolError,
    validate_engineering_request_binding,
)
from spirallens.contexts import ContextContractError, context_bank_from_dict


ATLAS_SCHEMA_VERSION = "spirallens.activation_atlas.v2"
_ATLAS_ARRAY_NAMES: tuple[str, ...] = (
    "token_ids",
    "resid_pre",
    "resid_post",
    "norm_summary",
    "logit_summary",
    "prediction_ids",
)


class AtlasStateError(RuntimeError):
    """Raised when an output directory cannot be safely initialized/resumed."""


class AtlasIntegrityError(RuntimeError):
    """Raised when persisted atlas data violates its manifest."""


def _strict_json_load(path: Path) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise AtlasIntegrityError(
            f"{path.name} contains non-standard JSON constant {value}"
        )

    try:
        data = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)
    except (OSError, json.JSONDecodeError) as exc:
        raise AtlasIntegrityError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise AtlasIntegrityError(f"{path} must contain a JSON object")
    return data


def _canonical_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _request_resume_identity(request: Mapping[str, Any]) -> dict[str, Any]:
    """Return the immutable request fields; batch size may change on resume."""

    identity = deepcopy(dict(request))
    identity.pop("batch_size_initial", None)
    identity.pop("batch_size_latest", None)
    return identity


def _require_sha256(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise AtlasIntegrityError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _verify_context_bank_binding(
    request: Mapping[str, Any],
    *,
    manifest_model: object,
) -> None:
    """Recompute an optional v1 bank binding from its canonical content."""

    binding = request.get("context_bank_binding")
    binding_sha256 = request.get("context_bank_binding_sha256")
    if binding is None:
        bound_only_fields = {
            "context_bank_binding_sha256",
            "request_identity_sha256",
            "token_domain",
            "language_space_atlas",
            "semantic_unit",
        }
        unexpected = sorted(bound_only_fields.intersection(request))
        if unexpected:
            raise AtlasIntegrityError(
                "unbound request retains context-bank-only fields: "
                + ", ".join(unexpected)
            )
        return
    if not isinstance(binding, Mapping):
        raise AtlasIntegrityError("context_bank_binding must be an object")
    expected_binding_sha256 = _require_sha256(
        binding_sha256,
        label="context_bank_binding_sha256",
    )
    if _canonical_sha256(binding) != expected_binding_sha256:
        raise AtlasIntegrityError("context-bank binding digest mismatch")
    if binding.get("schema_version") != "spirallens.atlas-context-binding.v1":
        raise AtlasIntegrityError("unsupported context-bank binding schema")
    expected_binding_fields = {
        "schema_version",
        "bank",
        "selected_context",
        "tokenizer_provenance_sha256",
        "observation_key_schema_version",
        "interpretation_contract",
    }
    if set(binding) != expected_binding_fields:
        raise AtlasIntegrityError(
            "context-bank binding fields differ from the v1 contract"
        )
    interpretation = binding.get("interpretation_contract")
    expected_interpretation = {
        "language_space_atlas": False,
        "semantic_unit": False,
        "decoded_strings_used_for_selection": False,
        "semantic_annotation_used": False,
        "sae_annotation_used": False,
        "projection_used": False,
    }
    if (
        interpretation != expected_interpretation
        or binding.get("observation_key_schema_version")
        != "spirallens.observation-key.v1"
        or request.get("language_space_atlas") is not False
        or request.get("semantic_unit") is not False
    ):
        raise AtlasIntegrityError(
            "context-bank interpretation flags violate the v1 contract"
        )
    request_identity_sha256 = _require_sha256(
        request.get("request_identity_sha256"),
        label="request_identity_sha256",
    )
    request_identity = _request_resume_identity(request)
    request_identity.pop("request_identity_sha256", None)
    if _canonical_sha256(request_identity) != request_identity_sha256:
        raise AtlasIntegrityError("bound request identity digest mismatch")

    bank = binding.get("bank")
    selected = binding.get("selected_context")
    token_domain = request.get("token_domain")
    if not all(
        isinstance(value, Mapping)
        for value in (bank, selected, token_domain, manifest_model)
    ):
        raise AtlasIntegrityError(
            "context-bank binding is missing structured provenance"
        )
    assert isinstance(bank, Mapping)
    assert isinstance(selected, Mapping)
    assert isinstance(token_domain, Mapping)
    assert isinstance(manifest_model, Mapping)

    if set(bank) != {"source_sha256", "canonical_sha256", "content"}:
        raise AtlasIntegrityError("bound bank fields differ from the v1 contract")
    _require_sha256(bank.get("source_sha256"), label="bank.source_sha256")
    bank_canonical_sha256 = _require_sha256(
        bank.get("canonical_sha256"), label="bank.canonical_sha256"
    )
    bank_content = bank.get("content")
    if not isinstance(bank_content, Mapping):
        raise AtlasIntegrityError("bank.content must be an object")
    if _canonical_sha256(bank_content) != bank_canonical_sha256:
        raise AtlasIntegrityError("bound bank canonical digest mismatch")
    try:
        validated_bank = context_bank_from_dict(bank_content)
    except (ContextContractError, TypeError, KeyError) as exc:
        raise AtlasIntegrityError(
            f"bound bank content violates its schema: {exc}"
        ) from exc
    if validated_bank.sha256 != bank_canonical_sha256:
        raise AtlasIntegrityError("validated bank canonical digest mismatch")
    expected_bank_fields = {
        "schema_version",
        "bank_id",
        "status",
        "license",
        "claim_eligible",
        "source",
        "model",
        "tokenizer",
        "sweep_domain",
        "contexts",
    }
    if (
        set(bank_content) != expected_bank_fields
        or bank_content.get("schema_version") != "spirallens.context-bank.v1"
    ):
        raise AtlasIntegrityError(
            "bound bank content differs from the context-bank v1 schema"
        )
    model = bank_content.get("model")
    tokenizer = bank_content.get("tokenizer")
    source = bank_content.get("source")
    contexts = bank_content.get("contexts")
    expected_model_fields = {
        "id",
        "requested_revision",
        "resolved_revision",
        "vocab_size",
    }
    expected_tokenizer_fields = {
        "id",
        "requested_revision",
        "resolved_revision",
        "addressable_size",
        "tokenizer_class",
        "implementation",
        "transformers_version",
        "tokenizers_version",
        "add_special_tokens",
        "files",
    }
    if (
        not isinstance(model, Mapping)
        or not isinstance(tokenizer, Mapping)
        or not isinstance(source, Mapping)
        or set(model) != expected_model_fields
        or set(tokenizer) != expected_tokenizer_fields
        or set(source) != {"kind", "source_id"}
        or not isinstance(contexts, list)
        or not contexts
        or any(not isinstance(value, Mapping) for value in contexts)
    ):
        raise AtlasIntegrityError("bound bank content is structurally invalid")
    tokenizer_provenance_sha256 = _require_sha256(
        binding.get("tokenizer_provenance_sha256"),
        label="tokenizer_provenance_sha256",
    )
    if _canonical_sha256(tokenizer) != tokenizer_provenance_sha256:
        raise AtlasIntegrityError("bound tokenizer provenance digest mismatch")

    expected_selected_fields = {
        "context_id",
        "role",
        "entry_order_index",
        "context_spec_sha256",
        "context_input_sha256",
        "sweep_position",
        "observation_position",
    }
    if set(selected) != expected_selected_fields:
        raise AtlasIntegrityError(
            "selected-context fields differ from the v1 contract"
        )
    selected_spec_sha256 = _require_sha256(
        selected.get("context_spec_sha256"),
        label="selected_context.context_spec_sha256",
    )
    selected_input_sha256 = _require_sha256(
        selected.get("context_input_sha256"),
        label="selected_context.context_input_sha256",
    )
    entry_index = selected.get("entry_order_index")
    context_id = selected.get("context_id")
    if (
        isinstance(entry_index, bool)
        or not isinstance(entry_index, int)
        or not 0 <= entry_index < len(contexts)
    ):
        raise AtlasIntegrityError(
            "selected context does not match the bound bank entry order"
        )
    context_content = contexts[entry_index]
    assert isinstance(context_content, Mapping)
    context_ids_in_order = [value.get("context_id") for value in contexts]
    expected_context_fields = {
        "context_id",
        "role",
        "family_id",
        "source_id",
        "template_id",
        "template_ids",
        "attention_mask",
        "observation_position",
    }
    if (
        any(not isinstance(value, str) for value in context_ids_in_order)
        or len(context_ids_in_order) != len(set(context_ids_in_order))
        or any(set(value) != expected_context_fields for value in contexts)
        or context_ids_in_order[entry_index] != context_id
        or context_content.get("role") != selected.get("role")
        or any(
            value.get("role") != selected.get("role")
            for value in contexts
        )
    ):
        raise AtlasIntegrityError(
            "selected context identity does not match the bank entry order"
        )

    template_ids = context_content.get("template_ids")
    attention_mask = context_content.get("attention_mask")
    context_ids = request.get("context_ids")
    sweep_position = selected.get("sweep_position")
    observation_position = selected.get("observation_position")
    if (
        not isinstance(template_ids, list)
        or template_ids.count(None) != 1
        or not isinstance(attention_mask, list)
        or len(attention_mask) != len(template_ids)
        or not isinstance(context_ids, list)
        or len(context_ids) != len(template_ids)
        or isinstance(sweep_position, bool)
        or not isinstance(sweep_position, int)
        or not 0 <= sweep_position < len(template_ids)
        or template_ids[sweep_position] is not None
        or isinstance(observation_position, bool)
        or not isinstance(observation_position, int)
        or not 0 <= observation_position < len(template_ids)
        or context_content.get("observation_position")
        != observation_position
    ):
        raise AtlasIntegrityError(
            "bound context template, mask, or positions are invalid"
        )
    input_payload = {
        "schema_version": "spirallens.context-spec.v1",
        "template_ids": template_ids,
        "attention_mask": attention_mask,
        "sweep_position": sweep_position,
        "observation_position": observation_position,
    }
    spec_payload = {
        "schema_version": "spirallens.context-spec.v1",
        **dict(context_content),
        "sweep_position": sweep_position,
    }
    if (
        _canonical_sha256(input_payload) != selected_input_sha256
        or _canonical_sha256(spec_payload) != selected_spec_sha256
    ):
        raise AtlasIntegrityError("selected ContextSpec digest mismatch")
    expected_context_ids = [
        0 if value is None else value for value in template_ids
    ]
    if (
        context_ids != expected_context_ids
        or request.get("attention_mask") != attention_mask
        or request.get("sweep_position") != sweep_position
        or request.get("observation_position") != observation_position
        or request.get("position") != observation_position
    ):
        raise AtlasIntegrityError(
            "atlas request does not match its bound ContextSpec"
        )
    model_vocab_size = model.get("vocab_size")
    tokenizer_addressable_size = tokenizer.get("addressable_size")
    sweep_domain = bank_content.get("sweep_domain")
    if (
        isinstance(model_vocab_size, bool)
        or not isinstance(model_vocab_size, int)
        or model_vocab_size <= 0
        or isinstance(tokenizer_addressable_size, bool)
        or not isinstance(tokenizer_addressable_size, int)
        or not 0 < tokenizer_addressable_size <= model_vocab_size
        or sweep_domain
        not in {"model_embedding_rows", "tokenizer_addressable"}
    ):
        raise AtlasIntegrityError("bound model/tokenizer domain is invalid")
    expected_domain_size = (
        model_vocab_size
        if sweep_domain == "model_embedding_rows"
        else tokenizer_addressable_size
    )
    if (
        request.get("model_id") != model.get("id")
        or request.get("resolved_model_revision")
        != model.get("resolved_revision")
        or token_domain.get("kind") != sweep_domain
        or token_domain.get("size") != expected_domain_size
        or token_domain.get("model_vocab_size") != model_vocab_size
        or token_domain.get("tokenizer_addressable_size")
        != tokenizer_addressable_size
        or manifest_model.get("model_id") != model.get("id")
        or manifest_model.get("resolved_revision")
        != model.get("resolved_revision")
        or manifest_model.get("vocab_size") != model_vocab_size
    ):
        raise AtlasIntegrityError(
            "atlas model or token domain does not match its context bank"
        )


def token_ids_sha256(token_ids: np.ndarray) -> str:
    canonical = np.asarray(token_ids, dtype="<i8", order="C")
    return hashlib.sha256(canonical.tobytes(order="C")).hexdigest()


def _sha256_file(path: Path, *, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _validated_array(
    root: Path,
    name: str,
    spec: Mapping[str, Any],
    *,
    writable: bool,
) -> np.memmap:
    relative_path = spec.get("path")
    if (
        not isinstance(relative_path, str)
        or Path(relative_path).name != relative_path
    ):
        raise AtlasIntegrityError(f"unsafe array path for {name}: {relative_path!r}")
    path = root / relative_path
    if not path.is_file():
        raise AtlasIntegrityError(f"missing array file: {path}")
    try:
        array = np.load(path, mmap_mode="r+" if writable else "r", allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise AtlasIntegrityError(f"cannot open {path}: {exc}") from exc
    expected_shape = tuple(spec.get("shape", ()))
    expected_dtype = np.dtype(spec.get("dtype"))
    if array.shape != expected_shape:
        raise AtlasIntegrityError(
            f"{name} shape mismatch: {array.shape} != {expected_shape}"
        )
    if array.dtype != expected_dtype:
        raise AtlasIntegrityError(
            f"{name} dtype mismatch: {array.dtype} != {expected_dtype}"
        )
    if not isinstance(array, np.memmap):
        raise AtlasIntegrityError(f"{path} did not open as a memory map")
    return array


def _close_memmaps(arrays: Mapping[str, np.memmap]) -> None:
    for array in arrays.values():
        try:
            if array.flags.writeable:
                array.flush()
        except (OSError, ValueError):
            pass
        underlying = getattr(array, "_mmap", None)
        if underlying is not None:
            try:
                underlying.close()
            except (OSError, ValueError):
                pass


def _array_slice_sha256(
    name: str,
    array: np.ndarray,
    *,
    start_row: int,
    end_row: int,
) -> str:
    """Hash a persisted row slice with unambiguous structural framing."""

    view = np.ascontiguousarray(array[start_row:end_row])
    header = {
        "schema_version": ATLAS_SCHEMA_VERSION,
        "array": name,
        "start_row": start_row,
        "end_row": end_row,
        "shape": list(view.shape),
        "dtype": str(view.dtype),
    }
    digest = hashlib.sha256()
    digest.update(
        json.dumps(
            header,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    )
    digest.update(b"\0")
    digest.update(memoryview(view).cast("B"))
    return digest.hexdigest()


def _verify_batch_commit_data(
    manifest: Mapping[str, Any],
    arrays: Mapping[str, np.ndarray],
) -> None:
    for commit in manifest["batch_commits"]:
        start_row = int(commit["start_row"])
        end_row = int(commit["end_row"])
        for name, expected in commit["array_sha256"].items():
            actual = _array_slice_sha256(
                name,
                arrays[name],
                start_row=start_row,
                end_row=end_row,
            )
            if actual != expected:
                raise AtlasIntegrityError(
                    "batch commit digest mismatch: "
                    f"batch={commit['batch_index']}, array={name}, "
                    f"rows=[{start_row}, {end_row})"
                )


def _verify_manifest_structure(manifest: Mapping[str, Any]) -> None:
    if manifest.get("schema_version") != ATLAS_SCHEMA_VERSION:
        raise AtlasIntegrityError(
            "unsupported atlas schema: "
            f"{manifest.get('schema_version')!r} != {ATLAS_SCHEMA_VERSION!r}"
        )
    if manifest.get("status") not in {"in_progress", "failed", "complete"}:
        raise AtlasIntegrityError(f"invalid atlas status: {manifest.get('status')!r}")
    arrays = manifest.get("arrays")
    if not isinstance(arrays, Mapping):
        raise AtlasIntegrityError("manifest.arrays must be an object")
    if set(arrays) != set(_ATLAS_ARRAY_NAMES):
        raise AtlasIntegrityError("manifest contains missing or unknown arrays")
    progress = manifest.get("progress")
    if not isinstance(progress, Mapping):
        raise AtlasIntegrityError("manifest.progress must be an object")
    completed = progress.get("completed_rows")
    total = progress.get("total_rows")
    if (
        type(completed) is not int
        or type(total) is not int
        or total <= 0
        or not 0 <= completed <= total
    ):
        raise AtlasIntegrityError(
            f"invalid manifest progress: completed={completed}, total={total}"
        )
    if manifest.get("status") == "complete" and completed != total:
        raise AtlasIntegrityError("complete atlas does not have all rows committed")

    capture = manifest.get("capture")
    if not isinstance(capture, Mapping):
        raise AtlasIntegrityError("manifest.capture must be an object")
    implementation = capture.get("capture_implementation")
    if not isinstance(implementation, Mapping):
        raise AtlasIntegrityError(
            "manifest.capture.capture_implementation must be an object"
        )
    if (
        not isinstance(implementation.get("name"), str)
        or not isinstance(implementation.get("version"), str)
        or implementation.get("accelerator_to_cpu_copy") != "synchronous"
        or implementation.get("activation_dtype") != "float32"
    ):
        raise AtlasIntegrityError("invalid capture implementation contract")
    required_capture_fields = (
        "atlas_schema_version",
        "spirallens_version",
        "torch_version",
        "transformers_version",
        "effective_parameter_layout",
    )
    if any(field not in capture for field in required_capture_fields):
        raise AtlasIntegrityError("manifest.capture is missing required provenance")
    layout = capture["effective_parameter_layout"]
    if not isinstance(layout, list) or not layout:
        raise AtlasIntegrityError(
            "capture effective_parameter_layout must be non-empty"
        )
    for entry in layout:
        if (
            not isinstance(entry, Mapping)
            or not isinstance(entry.get("device"), str)
            or not isinstance(entry.get("dtype"), str)
            or not isinstance(entry.get("parameter_tensors"), int)
            or not isinstance(entry.get("parameter_values"), int)
        ):
            raise AtlasIntegrityError(
                "invalid effective parameter device/dtype entry"
            )
    if capture["atlas_schema_version"] != ATLAS_SCHEMA_VERSION:
        raise AtlasIntegrityError("capture contract schema does not match manifest")
    capture_fingerprint = manifest.get("capture_fingerprint")
    if (
        not isinstance(capture_fingerprint, str)
        or capture_fingerprint != _canonical_sha256(capture)
    ):
        raise AtlasIntegrityError("manifest capture fingerprint is invalid")
    request = manifest.get("request")
    if (
        not isinstance(request, Mapping)
        or request.get("capture_fingerprint") != capture_fingerprint
    ):
        raise AtlasIntegrityError(
            "request capture fingerprint does not match manifest"
        )
    _verify_context_bank_binding(
        request,
        manifest_model=manifest.get("model"),
    )
    try:
        validate_engineering_request_binding(
            request,
            manifest_model=manifest.get("model"),
        )
    except (PublicExamplePlumbingProtocolError, TypeError) as exc:
        raise AtlasIntegrityError(
            f"public-example engineering binding is invalid: {exc}"
        ) from exc

    attempts = manifest.get("attempts")
    if not isinstance(attempts, list) or not attempts:
        raise AtlasIntegrityError("manifest.attempts must be a non-empty list")
    for index, attempt in enumerate(attempts):
        if not isinstance(attempt, Mapping):
            raise AtlasIntegrityError(f"attempt {index} must be an object")
        if (
            attempt.get("capture") != capture
            or attempt.get("capture_fingerprint") != capture_fingerprint
        ):
            raise AtlasIntegrityError(
                f"attempt {index} capture provenance does not match run"
            )

    committed_batches = progress.get("committed_batches")
    batch_commits = manifest.get("batch_commits")
    if (
        type(committed_batches) is not int
        or committed_batches < 0
        or not isinstance(batch_commits, list)
        or committed_batches != len(batch_commits)
    ):
        raise AtlasIntegrityError(
            "progress.committed_batches must match batch_commits length"
        )
    expected_start = 0
    array_names = set(arrays)
    for index, commit in enumerate(batch_commits):
        if not isinstance(commit, Mapping):
            raise AtlasIntegrityError(f"batch commit {index} must be an object")
        start_row = commit.get("start_row")
        end_row = commit.get("end_row")
        digests = commit.get("array_sha256")
        if (
            commit.get("batch_index") != index
            or start_row != expected_start
            or not isinstance(end_row, int)
            or not isinstance(start_row, int)
            or not start_row < end_row <= completed
            or not isinstance(digests, Mapping)
            or set(digests) != array_names
        ):
            raise AtlasIntegrityError(f"invalid batch commit structure at {index}")
        for name, digest in digests.items():
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                raise AtlasIntegrityError(
                    f"invalid batch commit digest at {index}:{name}"
                )
        expected_start = end_row
    if expected_start != completed:
        raise AtlasIntegrityError(
            "batch commit row coverage does not match completed_rows"
        )


def load_manifest_metadata(
    output_dir: str | Path,
) -> dict[str, Any]:
    """Load the entire outcome-bearing manifest without opening its arrays.

    The returned mapping includes data-derived summaries and run state. It is
    not a sanitized or subject prepare-only view.
    """

    root = Path(output_dir)
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise AtlasStateError(f"atlas manifest does not exist: {manifest_path}")
    manifest = _strict_json_load(manifest_path)
    _verify_manifest_structure(manifest)
    return manifest

def load_manifest(
    output_dir: str | Path,
    *,
    verify_checksums: bool = True,
) -> dict[str, Any]:
    """Load and validate a completed or partial atlas manifest.

    When checksums are present they are verified by default.  A complete
    manifest is required to have a checksum for every array.
    """

    root = Path(output_dir)
    manifest = load_manifest_metadata(root)
    arrays: dict[str, np.memmap] = {}
    try:
        arrays = {
            name: _validated_array(root, name, spec, writable=False)
            for name, spec in manifest["arrays"].items()
        }
        expected_token_digest = manifest.get("request", {}).get(
            "token_ids_sha256"
        )
        if token_ids_sha256(arrays["token_ids"]) != expected_token_digest:
            raise AtlasIntegrityError(
                "token_ids data digest does not match request"
            )
        request = manifest.get("request", {})
        if request.get("context_bank_binding") is not None:
            token_domain = request.get("token_domain")
            if not isinstance(token_domain, Mapping):
                raise AtlasIntegrityError(
                    "bound atlas is missing its token domain"
                )
            domain_size = token_domain.get("size")
            if (
                isinstance(domain_size, bool)
                or not isinstance(domain_size, int)
                or domain_size <= 0
                or np.any(arrays["token_ids"] < 0)
                or np.any(arrays["token_ids"] >= domain_size)
            ):
                raise AtlasIntegrityError(
                    "token_ids data exceeds the bound sweep domain"
                )
        # Partial atlases do not yet have whole-file checksums, so their batch
        # journal is the authoritative integrity boundary.  For complete
        # atlases, whole-file checksums cover the same bytes more efficiently.
        if manifest["status"] != "complete" or not verify_checksums:
            _verify_batch_commit_data(manifest, arrays)
    finally:
        _close_memmaps(arrays)

    for name, spec in manifest["arrays"].items():
        checksum = spec.get("sha256")
        if manifest["status"] == "complete" and not checksum:
            raise AtlasIntegrityError(
                f"complete atlas is missing checksum for {name}"
            )
        if verify_checksums and checksum:
            actual = _sha256_file(root / spec["path"])
            if actual != checksum:
                raise AtlasIntegrityError(
                    f"{name} checksum mismatch: {actual} != {checksum}"
                )
    return manifest
