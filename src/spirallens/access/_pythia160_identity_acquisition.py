"""Private Pythia-160M provider-metadata acquisition receipt contract.

The pure kernel validates already-acquired Hugging Face response bytes.  It
performs no filesystem, cache, network, model, tokenizer, or runtime access.
Provider-reported sibling metadata is never promoted to locally verified file
content.  Only the separately supplied ``config.json`` bytes are joined to the
provider's exact Git-blob identifier and byte count.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import PurePosixPath
import re
from types import MappingProxyType
from typing import Final, Mapping


__all__ = ()

_SCHEMA_VERSION = "spirallens.pythia160-identity-acquisition-receipt.v0.1"
_MODEL_ID = "EleutherAI/pythia-160m"
_REPOSITORY = "https://github.com/RyoSpiralArchitect/SpiralLens.git"
_STATUS = "review_pending"
_ARTIFACT_ROLE = "provider-metadata-and-config-candidate-only"
_SELECTION_RULE = "resolve-default-head-once-then-requery-exact-commit"
_KERNEL_PATH = "src/spirallens/access/_pythia160_identity_acquisition.py"
_SCRIPT_PATH = "scripts/capture_pythia160_identity.py"
_SOURCE_PATHS = (_SCRIPT_PATH, _KERNEL_PATH)

_MAX_MODEL_INFO_BYTES = 4 * 1024 * 1024
_MAX_CONFIG_BYTES = 1024 * 1024
_MAX_RECEIPT_BYTES = 8 * 1024 * 1024
_MAX_SIBLINGS = 4096
_MAX_PATH_BYTES = 4096
_MAX_NUMBER_CHARACTERS = 128

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_COMMIT = _SHA1

_ACCESS_FACTS: Final = MappingProxyType(
    {
        "activation_values_accessed": False,
        "atlas_created": False,
        "cache_read": False,
        "config_bytes_accessed": True,
        "forward_executed": False,
        "hugging_face_accessed": True,
        "model_loaded": False,
        "network_accessed": True,
        "provider_metadata_accessed": True,
        "subject_values_accessed": False,
        "tokenizer_bytes_accessed": False,
        "tokenizer_loaded": False,
        "weight_bytes_accessed": False,
    }
)

_VERIFICATION_FACTS: Final = MappingProxyType(
    {
        "config_bytes_sha256_computed": True,
        "config_git_blob_join_verified": True,
        "default_exact_revision_join_verified": True,
        "external_witness_verified": False,
        "model_identity_reviewed": False,
        "model_profile_verified": False,
        "parameter_layout_verified": False,
        "provider_sibling_bytes_verified": False,
        "pythia160_runtime_verified": False,
        "sci_s1_terminal_transition_verified": False,
        "weight_bytes_verified": False,
        "zero_intervention_verified": False,
    }
)

_AUTHORITY_FACTS: Final = MappingProxyType(
    {
        "capture_authorized": False,
        "d0_d8_credit": False,
        "execution_authorized": False,
        "model_access_authorized": False,
        "pythia_access_authorized": False,
        "sci_s1_completion_credit": False,
        "sci_s2_authorized": False,
        "scientific_claim_eligible": False,
        "subject_execution_authorized": False,
        "subject_manifest_authorized": False,
        "subject_preparation_authorized": False,
        "topology_authority": False,
        "voy_v3_credit": False,
        "voy_v7_credit": False,
    }
)

_CLAIM_BOUNDARY: Final = MappingProxyType(
    {
        "claim_ceiling": "level_0",
        "claim_delta": "none",
        "config_profile_established": False,
        "execution_readiness_established": False,
        "identity_review_completed": False,
        "provider_is_independent_witness": False,
        "resource_sufficiency_established": False,
        "sci_s1_satisfied": False,
        "sci_s2_unblocked": False,
        "weight_manifest_reviewed": False,
    }
)


class _Pythia160IdentityAcquisitionError(ValueError):
    """Raised when private acquisition evidence is not exact."""


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _Pythia160IdentityAcquisitionError(
                f"JSON contains duplicate key {key!r}"
            )
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise _Pythia160IdentityAcquisitionError(
        f"JSON contains non-finite constant {value!r}"
    )


def _parse_int(value: str) -> int:
    if len(value) > _MAX_NUMBER_CHARACTERS:
        raise _Pythia160IdentityAcquisitionError("JSON integer is too large")
    if value == "-0":
        raise _Pythia160IdentityAcquisitionError(
            "JSON integer must not be negative zero"
        )
    return int(value, 10)


def _parse_float(value: str) -> float:
    if len(value) > _MAX_NUMBER_CHARACTERS:
        raise _Pythia160IdentityAcquisitionError("JSON number is too large")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise _Pythia160IdentityAcquisitionError("JSON number must be finite")
    return parsed


def _validate_json_tree(value: object, *, depth: int = 0) -> None:
    if depth > 128:
        raise _Pythia160IdentityAcquisitionError("JSON nesting is too deep")
    if value is None or type(value) in {bool, int}:
        return
    if type(value) is str:
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as error:
            raise _Pythia160IdentityAcquisitionError(
                "JSON string is not Unicode scalar text"
            ) from error
        return
    if type(value) is float:
        if not math.isfinite(value) or (
            value == 0.0 and math.copysign(1.0, value) < 0.0
        ):
            raise _Pythia160IdentityAcquisitionError(
                "JSON number must be finite and not negative zero"
            )
        return
    if type(value) is list:
        for item in value:
            _validate_json_tree(item, depth=depth + 1)
        return
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise _Pythia160IdentityAcquisitionError(
                "JSON objects must have exact string keys"
            )
        for key, item in value.items():
            _validate_json_tree(key, depth=depth + 1)
            _validate_json_tree(item, depth=depth + 1)
        return
    raise _Pythia160IdentityAcquisitionError("JSON contains an unsupported value")


def _canonical_json_bytes(value: object) -> bytes:
    _validate_json_tree(value)
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError) as error:
        raise _Pythia160IdentityAcquisitionError(
            "value cannot be encoded as canonical UTF-8 JSON"
        ) from error


def _parse_json_object(source: bytes, *, label: str, maximum: int) -> dict[str, object]:
    if type(source) is not bytes or not source or len(source) > maximum:
        raise _Pythia160IdentityAcquisitionError(
            f"{label} must be non-empty bytes no larger than {maximum}"
        )
    try:
        text = source.decode("utf-8")
        if text.startswith("\ufeff"):
            raise _Pythia160IdentityAcquisitionError(
                f"{label} must not contain a UTF-8 byte-order mark"
            )
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
            parse_int=_parse_int,
            parse_float=_parse_float,
        )
    except _Pythia160IdentityAcquisitionError:
        raise
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        RecursionError,
        ValueError,
    ) as error:
        raise _Pythia160IdentityAcquisitionError(
            f"{label} is not strict UTF-8 JSON: {error}"
        ) from error
    if type(value) is not dict:
        raise _Pythia160IdentityAcquisitionError(f"{label} must be a JSON object")
    _validate_json_tree(value)
    return value


def _plain_dict(value: object, *, label: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise _Pythia160IdentityAcquisitionError(
            f"{label} must be a plain string-keyed dictionary"
        )
    return value


def _exact_keys(value: Mapping[str, object], expected: set[str], *, label: str) -> None:
    if set(value) != expected:
        raise _Pythia160IdentityAcquisitionError(
            f"{label} fields differ from the private contract"
        )


def _sha256(value: object, *, label: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise _Pythia160IdentityAcquisitionError(
            f"{label} must be a lowercase SHA-256 digest"
        )
    return value


def _commit(value: object, *, label: str) -> str:
    if type(value) is not str or _COMMIT.fullmatch(value) is None:
        raise _Pythia160IdentityAcquisitionError(
            f"{label} must be a full lowercase 40-hex commit"
        )
    return value


def _byte_count(value: object, *, label: str, allow_zero: bool = False) -> int:
    minimum = 0 if allow_zero else 1
    if type(value) is not int or value < minimum or value > (1 << 63) - 1:
        raise _Pythia160IdentityAcquisitionError(
            f"{label} must be an exact bounded integer"
        )
    return value


def _nullable_byte_count(value: object, *, label: str) -> int | None:
    if value is None:
        return None
    return _byte_count(value, label=label, allow_zero=True)


def _nullable_digest(
    value: object, *, label: str, pattern: re.Pattern[str]
) -> str | None:
    if value is None:
        return None
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise _Pythia160IdentityAcquisitionError(f"{label} has invalid digest form")
    return value


def _repository_path(value: object, *, label: str) -> str:
    if (
        type(value) is not str
        or not value
        or "\x00" in value
        or "\\" in value
        or len(value.encode("utf-8")) > _MAX_PATH_BYTES
    ):
        raise _Pythia160IdentityAcquisitionError(f"{label} is not a bounded path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or str(path) != value
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise _Pythia160IdentityAcquisitionError(
            f"{label} must be a normalized relative repository path"
        )
    return value


def _model_id(value: Mapping[str, object], *, label: str) -> str:
    observed = [value[key] for key in ("id", "modelId") if key in value]
    if not observed or any(
        type(item) is not str or item != _MODEL_ID for item in observed
    ):
        raise _Pythia160IdentityAcquisitionError(
            f"{label} does not identify {_MODEL_ID!r}"
        )
    return _MODEL_ID


def _source_descriptor(source: bytes, *, role: str) -> dict[str, object]:
    return {
        "role": role,
        "byte_count": len(source),
        "sha256": hashlib.sha256(source).hexdigest(),
    }


def _git_blob_sha1(source: bytes) -> str:
    header = f"blob {len(source)}\0".encode("ascii")
    return hashlib.sha1(header + source, usedforsecurity=False).hexdigest()


def _provider_alias(
    value: Mapping[str, object],
    primary: str,
    alias: str,
    *,
    label: str,
) -> object:
    if primary in value and alias in value and value[primary] != value[alias]:
        raise _Pythia160IdentityAcquisitionError(
            f"{label} aliases report different values"
        )
    if primary in value:
        return value[primary]
    return value.get(alias)


def _sibling_manifest(value: Mapping[str, object]) -> list[dict[str, object]]:
    raw = value.get("siblings")
    if type(raw) is not list or not raw or len(raw) > _MAX_SIBLINGS:
        raise _Pythia160IdentityAcquisitionError(
            "exact model info must contain a bounded non-empty siblings list"
        )
    siblings: list[dict[str, object]] = []
    for index, candidate in enumerate(raw):
        item = _plain_dict(candidate, label=f"siblings[{index}]")
        path = _repository_path(
            item.get("rfilename"), label=f"siblings[{index}].rfilename"
        )
        size = _nullable_byte_count(item.get("size"), label=f"siblings[{index}].size")
        blob_id = _nullable_digest(
            _provider_alias(
                item,
                "blobId",
                "blob_id",
                label=f"siblings[{index}].blob_id",
            ),
            label=f"siblings[{index}].blob_id",
            pattern=_SHA1,
        )
        lfs_metadata_present = "lfs" in item and item["lfs"] is not None
        raw_lfs = item.get("lfs")
        if not lfs_metadata_present:
            lfs_sha256 = None
            lfs_size = None
        else:
            lfs = _plain_dict(raw_lfs, label=f"siblings[{index}].lfs")
            lfs_sha256 = _nullable_digest(
                _provider_alias(
                    lfs,
                    "sha256",
                    "oid",
                    label=f"siblings[{index}].lfs.sha256",
                ),
                label=f"siblings[{index}].lfs.sha256",
                pattern=_SHA256,
            )
            lfs_size = _nullable_byte_count(
                lfs.get("size"), label=f"siblings[{index}].lfs.size"
            )
            if lfs_sha256 is None or lfs_size is None:
                raise _Pythia160IdentityAcquisitionError(
                    f"siblings[{index}].lfs metadata is incomplete"
                )
        siblings.append(
            {
                "repository_path": path,
                "provider_byte_count": size,
                "provider_git_blob_oid": blob_id,
                "provider_lfs_sha256": lfs_sha256,
                "provider_lfs_byte_count": lfs_size,
                "provider_lfs_metadata_present": lfs_metadata_present,
                "metadata_status": "provider_reported_unrecomputed",
            }
        )
    paths = [item["repository_path"] for item in siblings]
    if len(paths) != len(set(paths)):
        raise _Pythia160IdentityAcquisitionError(
            "exact model-info siblings must be unique"
        )
    return sorted(siblings, key=lambda item: str(item["repository_path"]))


def _source_binding(value: object) -> dict[str, object]:
    item = _plain_dict(value, label="source_binding")
    allowed_keys = {"repository", "source_commit", "members"}
    if "review_status" in item:
        allowed_keys.add("review_status")
        if item["review_status"] != "source_bound_review_pending":
            raise _Pythia160IdentityAcquisitionError(
                "source_binding review status differs"
            )
    _exact_keys(item, allowed_keys, label="source_binding")
    if item["repository"] != _REPOSITORY:
        raise _Pythia160IdentityAcquisitionError("source_binding repository differs")
    source_commit = _commit(item["source_commit"], label="source_binding.source_commit")
    raw_members = item["members"]
    if type(raw_members) is not list or len(raw_members) != len(_SOURCE_PATHS):
        raise _Pythia160IdentityAcquisitionError(
            "source_binding must contain the exact producer members"
        )
    members: list[dict[str, object]] = []
    for index, raw in enumerate(raw_members):
        member = _plain_dict(raw, label=f"source_binding.members[{index}]")
        _exact_keys(
            member,
            {"repository_path", "byte_count", "sha256"},
            label=f"source_binding.members[{index}]",
        )
        members.append(
            {
                "repository_path": _repository_path(
                    member["repository_path"],
                    label=f"source_binding.members[{index}].repository_path",
                ),
                "byte_count": _byte_count(
                    member["byte_count"],
                    label=f"source_binding.members[{index}].byte_count",
                ),
                "sha256": _sha256(
                    member["sha256"],
                    label=f"source_binding.members[{index}].sha256",
                ),
            }
        )
    if tuple(member["repository_path"] for member in members) != _SOURCE_PATHS:
        raise _Pythia160IdentityAcquisitionError(
            "source_binding producer member order differs"
        )
    return {
        "repository": _REPOSITORY,
        "source_commit": source_commit,
        "members": members,
        "review_status": "source_bound_review_pending",
    }


def _closed_mapping(
    value: object, expected: Mapping[str, object], *, label: str
) -> dict[str, object]:
    item = _plain_dict(value, label=label)
    expected_dict = dict(expected)
    if set(item) != set(expected_dict) or any(
        type(item[key]) is not type(expected_dict[key])
        or item[key] != expected_dict[key]
        for key in expected_dict
    ):
        raise _Pythia160IdentityAcquisitionError(
            f"{label} differs from the closed non-authorizing contract"
        )
    return expected_dict


def _validate_payload(value: object) -> dict[str, object]:
    root = _plain_dict(value, label="identity acquisition receipt")
    _exact_keys(
        root,
        {
            "schema_version",
            "status",
            "artifact_role",
            "model",
            "evidence",
            "source_binding",
            "access_facts",
            "verification_facts",
            "authority_facts",
            "claim_boundary",
        },
        label="identity acquisition receipt",
    )
    if root["schema_version"] != _SCHEMA_VERSION or root["status"] != _STATUS:
        raise _Pythia160IdentityAcquisitionError("receipt schema or status differs")
    if root["artifact_role"] != _ARTIFACT_ROLE:
        raise _Pythia160IdentityAcquisitionError("receipt artifact role differs")
    model = _plain_dict(root["model"], label="model")
    _exact_keys(
        model,
        {"model_id", "selection_rule", "resolved_revision", "review_status"},
        label="model",
    )
    if model["model_id"] != _MODEL_ID or model["selection_rule"] != _SELECTION_RULE:
        raise _Pythia160IdentityAcquisitionError("model selection contract differs")
    _commit(model["resolved_revision"], label="model.resolved_revision")
    if model["review_status"] != "provider_resolved_unreviewed":
        raise _Pythia160IdentityAcquisitionError("model review status differs")

    evidence = _plain_dict(root["evidence"], label="evidence")
    _exact_keys(
        evidence,
        {"default_model_info", "exact_model_info", "config", "siblings"},
        label="evidence",
    )
    for key in ("default_model_info", "exact_model_info"):
        descriptor = _plain_dict(evidence[key], label=f"evidence.{key}")
        _exact_keys(
            descriptor, {"role", "byte_count", "sha256"}, label=f"evidence.{key}"
        )
        if descriptor["role"] != key:
            raise _Pythia160IdentityAcquisitionError(f"evidence.{key} role differs")
        byte_count = _byte_count(
            descriptor["byte_count"], label=f"evidence.{key}.byte_count"
        )
        if byte_count > _MAX_MODEL_INFO_BYTES:
            raise _Pythia160IdentityAcquisitionError(
                f"evidence.{key}.byte_count exceeds the model-info bound"
            )
        _sha256(descriptor["sha256"], label=f"evidence.{key}.sha256")
    config = _plain_dict(evidence["config"], label="evidence.config")
    _exact_keys(
        config,
        {
            "repository_path",
            "byte_count",
            "sha256",
            "git_blob_sha1",
            "provider_git_blob_oid",
            "content_status",
            "profile_status",
        },
        label="evidence.config",
    )
    if config["repository_path"] != "config.json":
        raise _Pythia160IdentityAcquisitionError("config path differs")
    config_byte_count = _byte_count(
        config["byte_count"], label="evidence.config.byte_count"
    )
    if config_byte_count > _MAX_CONFIG_BYTES:
        raise _Pythia160IdentityAcquisitionError(
            "evidence.config.byte_count exceeds the config bound"
        )
    _sha256(config["sha256"], label="evidence.config.sha256")
    if (
        any(
            type(config[name]) is not str or _SHA1.fullmatch(config[name]) is None
            for name in ("git_blob_sha1", "provider_git_blob_oid")
        )
        or config["git_blob_sha1"] != config["provider_git_blob_oid"]
    ):
        raise _Pythia160IdentityAcquisitionError("config Git-blob join differs")
    if (
        config["content_status"] != "retrieved_bytes_joined_to_provider_git_blob"
        or config["profile_status"] != "not_derived_or_reviewed"
    ):
        raise _Pythia160IdentityAcquisitionError("config status differs")
    siblings = evidence["siblings"]
    if type(siblings) is not list or not siblings or len(siblings) > _MAX_SIBLINGS:
        raise _Pythia160IdentityAcquisitionError("receipt sibling manifest is invalid")
    normalized_siblings: list[dict[str, object]] = []
    for index, raw in enumerate(siblings):
        sibling = _plain_dict(raw, label=f"evidence.siblings[{index}]")
        _exact_keys(
            sibling,
            {
                "repository_path",
                "provider_byte_count",
                "provider_git_blob_oid",
                "provider_lfs_sha256",
                "provider_lfs_byte_count",
                "provider_lfs_metadata_present",
                "metadata_status",
            },
            label=f"evidence.siblings[{index}]",
        )
        normalized_siblings.append(
            {
                "repository_path": _repository_path(
                    sibling["repository_path"],
                    label=f"evidence.siblings[{index}].repository_path",
                ),
                "provider_byte_count": _nullable_byte_count(
                    sibling["provider_byte_count"],
                    label=f"evidence.siblings[{index}].provider_byte_count",
                ),
                "provider_git_blob_oid": _nullable_digest(
                    sibling["provider_git_blob_oid"],
                    label=f"evidence.siblings[{index}].provider_git_blob_oid",
                    pattern=_SHA1,
                ),
                "provider_lfs_sha256": _nullable_digest(
                    sibling["provider_lfs_sha256"],
                    label=f"evidence.siblings[{index}].provider_lfs_sha256",
                    pattern=_SHA256,
                ),
                "provider_lfs_byte_count": _nullable_byte_count(
                    sibling["provider_lfs_byte_count"],
                    label=f"evidence.siblings[{index}].provider_lfs_byte_count",
                ),
                "provider_lfs_metadata_present": sibling[
                    "provider_lfs_metadata_present"
                ],
                "metadata_status": sibling["metadata_status"],
            }
        )
    paths = [item["repository_path"] for item in normalized_siblings]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise _Pythia160IdentityAcquisitionError("receipt siblings are not canonical")
    if any(
        type(item["provider_lfs_metadata_present"]) is not bool
        or item["metadata_status"] != "provider_reported_unrecomputed"
        or item["provider_lfs_metadata_present"]
        != (
            item["provider_lfs_sha256"] is not None
            and item["provider_lfs_byte_count"] is not None
        )
        for item in normalized_siblings
    ):
        raise _Pythia160IdentityAcquisitionError("sibling metadata status differs")
    config_siblings = [
        item for item in normalized_siblings if item["repository_path"] == "config.json"
    ]
    if len(config_siblings) != 1:
        raise _Pythia160IdentityAcquisitionError("receipt requires one config sibling")
    config_sibling = config_siblings[0]
    if (
        config_sibling["provider_byte_count"] != config["byte_count"]
        or config_sibling["provider_git_blob_oid"] != config["provider_git_blob_oid"]
        or config_sibling["provider_lfs_sha256"] is not None
        or config_sibling["provider_lfs_byte_count"] is not None
        or config_sibling["provider_lfs_metadata_present"] is not False
    ):
        raise _Pythia160IdentityAcquisitionError("config sibling join differs")

    validated = {
        "schema_version": _SCHEMA_VERSION,
        "status": _STATUS,
        "artifact_role": _ARTIFACT_ROLE,
        "model": dict(model),
        "evidence": {
            "default_model_info": dict(evidence["default_model_info"]),
            "exact_model_info": dict(evidence["exact_model_info"]),
            "config": dict(config),
            "siblings": normalized_siblings,
        },
        "source_binding": _source_binding(root["source_binding"]),
        "access_facts": _closed_mapping(
            root["access_facts"], _ACCESS_FACTS, label="access_facts"
        ),
        "verification_facts": _closed_mapping(
            root["verification_facts"], _VERIFICATION_FACTS, label="verification_facts"
        ),
        "authority_facts": _closed_mapping(
            root["authority_facts"], _AUTHORITY_FACTS, label="authority_facts"
        ),
        "claim_boundary": _closed_mapping(
            root["claim_boundary"], _CLAIM_BOUNDARY, label="claim_boundary"
        ),
    }
    return validated


@dataclass(frozen=True, slots=True)
class _Pythia160IdentityAcquisitionReceipt:
    """Canonical, review-pending provider evidence with no authority."""

    _canonical_json: str

    def __post_init__(self) -> None:
        if type(self._canonical_json) is not str:
            raise TypeError("receipt canonical JSON must be an exact string")
        source = self._canonical_json.encode("utf-8")
        validated = _validate_payload(
            _parse_json_object(
                source, label="receipt canonical JSON", maximum=_MAX_RECEIPT_BYTES
            )
        )
        if _canonical_json_bytes(validated) != source:
            raise _Pythia160IdentityAcquisitionError(
                "receipt constructor requires exact canonical JSON"
            )

    @classmethod
    def from_payload(
        cls, value: dict[str, object]
    ) -> _Pythia160IdentityAcquisitionReceipt:
        validated = _validate_payload(value)
        return cls(_canonical_json_bytes(validated).decode("utf-8"))

    @classmethod
    def from_canonical_bytes(
        cls, source: bytes
    ) -> _Pythia160IdentityAcquisitionReceipt:
        value = _parse_json_object(
            source, label="receipt source", maximum=_MAX_RECEIPT_BYTES
        )
        receipt = cls.from_payload(value)
        if receipt.canonical_bytes != source:
            raise _Pythia160IdentityAcquisitionError(
                "receipt source is not exact canonical JSON"
            )
        return receipt

    def to_dict(self) -> dict[str, object]:
        return _parse_json_object(
            self.canonical_bytes,
            label="receipt canonical JSON",
            maximum=_MAX_RECEIPT_BYTES,
        )

    @property
    def canonical_bytes(self) -> bytes:
        return self._canonical_json.encode("utf-8")

    @property
    def canonical_sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()

    @property
    def sha256(self) -> str:
        """Return the exact canonical receipt SHA-256."""

        return self.canonical_sha256


def _resolved_revision_from_model_info(source: bytes) -> str:
    value = _parse_json_object(
        source, label="default model info", maximum=_MAX_MODEL_INFO_BYTES
    )
    _model_id(value, label="default model info")
    return _commit(value.get("sha"), label="default model info.sha")


def _build_pythia160_identity_acquisition_receipt(
    *,
    default_model_info_source: bytes,
    exact_model_info_source: bytes,
    config_source: bytes,
    source_binding: dict[str, object],
) -> _Pythia160IdentityAcquisitionReceipt:
    """Build a review-pending receipt from already-acquired bounded bytes."""

    default_info = _parse_json_object(
        default_model_info_source,
        label="default model info",
        maximum=_MAX_MODEL_INFO_BYTES,
    )
    exact_info = _parse_json_object(
        exact_model_info_source,
        label="exact model info",
        maximum=_MAX_MODEL_INFO_BYTES,
    )
    _model_id(default_info, label="default model info")
    _model_id(exact_info, label="exact model info")
    revision = _commit(default_info.get("sha"), label="default model info.sha")
    if _commit(exact_info.get("sha"), label="exact model info.sha") != revision:
        raise _Pythia160IdentityAcquisitionError(
            "default and exact model-info revisions differ"
        )
    siblings = _sibling_manifest(exact_info)
    config = _parse_json_object(
        config_source, label="config source", maximum=_MAX_CONFIG_BYTES
    )
    del config
    config_entries = [
        item for item in siblings if item["repository_path"] == "config.json"
    ]
    if len(config_entries) != 1:
        raise _Pythia160IdentityAcquisitionError(
            "exact model info must contain exactly one config.json"
        )
    config_entry = config_entries[0]
    config_blob = _git_blob_sha1(config_source)
    if (
        config_entry["provider_byte_count"] != len(config_source)
        or config_entry["provider_git_blob_oid"] != config_blob
        or config_entry["provider_lfs_sha256"] is not None
        or config_entry["provider_lfs_byte_count"] is not None
        or config_entry["provider_lfs_metadata_present"] is not False
    ):
        raise _Pythia160IdentityAcquisitionError(
            "config bytes do not join the provider's non-LFS Git blob metadata"
        )

    payload: dict[str, object] = {
        "schema_version": _SCHEMA_VERSION,
        "status": _STATUS,
        "artifact_role": _ARTIFACT_ROLE,
        "model": {
            "model_id": _MODEL_ID,
            "selection_rule": _SELECTION_RULE,
            "resolved_revision": revision,
            "review_status": "provider_resolved_unreviewed",
        },
        "evidence": {
            "default_model_info": _source_descriptor(
                default_model_info_source, role="default_model_info"
            ),
            "exact_model_info": _source_descriptor(
                exact_model_info_source, role="exact_model_info"
            ),
            "config": {
                "repository_path": "config.json",
                "byte_count": len(config_source),
                "sha256": hashlib.sha256(config_source).hexdigest(),
                "git_blob_sha1": config_blob,
                "provider_git_blob_oid": config_blob,
                "content_status": "retrieved_bytes_joined_to_provider_git_blob",
                "profile_status": "not_derived_or_reviewed",
            },
            "siblings": siblings,
        },
        "source_binding": source_binding,
        "access_facts": dict(_ACCESS_FACTS),
        "verification_facts": dict(_VERIFICATION_FACTS),
        "authority_facts": dict(_AUTHORITY_FACTS),
        "claim_boundary": dict(_CLAIM_BOUNDARY),
    }
    return _Pythia160IdentityAcquisitionReceipt.from_payload(payload)
