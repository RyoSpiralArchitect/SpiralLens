from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import py_compile
import runpy
import ssl
import stat
import subprocess
import sys
from types import SimpleNamespace

import pytest

import spirallens.access as access
from spirallens.access import _pythia160_identity_acquisition as acquisition
from spirallens.atlas import engineering_protocol


ROOT = Path(__file__).resolve().parents[1]
KERNEL = ROOT / "src/spirallens/access/_pythia160_identity_acquisition.py"
SCRIPT = ROOT / "scripts/capture_pythia160_identity.py"
AUTHENTICATED_MODULE = "_spirallens_pythia160_identity_acquisition_authenticated"
REVISION = "1" * 40
SOURCE_COMMIT = "3" * 40


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _git_blob(source: bytes) -> str:
    header = f"blob {len(source)}\0".encode("ascii")
    return hashlib.sha1(header + source, usedforsecurity=False).hexdigest()


def _sources() -> tuple[bytes, bytes, bytes]:
    config = b'{"hidden_size":768,"model_type":"gpt_neox"}'
    default = _json_bytes(
        {
            "_id": "provider-record-default",
            "id": "EleutherAI/pythia-160m",
            "sha": REVISION,
        }
    )
    exact = _json_bytes(
        {
            "_id": "provider-record-exact",
            "id": "EleutherAI/pythia-160m",
            "sha": REVISION,
            # Deliberately unsorted: the receipt must canonicalize the manifest.
            "siblings": [
                {
                    "rfilename": "model.safetensors",
                    "size": 10,
                    "blobId": None,
                    "lfs": {"sha256": "2" * 64, "size": 10},
                },
                {
                    "rfilename": "tokenizer.json",
                    "size": 12,
                    "blobId": "4" * 40,
                },
                {
                    "rfilename": "config.json",
                    "size": len(config),
                    "blobId": _git_blob(config),
                },
            ],
        }
    )
    return default, exact, config


def _source_binding(
    *,
    script_source: bytes = b"reviewed-script",
    kernel_source: bytes = b"reviewed-kernel",
) -> dict[str, object]:
    return {
        "repository": "https://github.com/RyoSpiralArchitect/SpiralLens.git",
        "source_commit": SOURCE_COMMIT,
        "members": [
            {
                "repository_path": "scripts/capture_pythia160_identity.py",
                "byte_count": len(script_source),
                "sha256": hashlib.sha256(script_source).hexdigest(),
            },
            {
                "repository_path": (
                    "src/spirallens/access/_pythia160_identity_acquisition.py"
                ),
                "byte_count": len(kernel_source),
                "sha256": hashlib.sha256(kernel_source).hexdigest(),
            },
        ],
    }


def _receipt():
    default, exact, config = _sources()
    return acquisition._build_pythia160_identity_acquisition_receipt(
        default_model_info_source=default,
        exact_model_info_source=exact,
        config_source=config,
        source_binding=_source_binding(),
    )


@pytest.fixture
def script_namespace() -> dict[str, object]:
    sys.modules.pop(AUTHENTICATED_MODULE, None)
    namespace = runpy.run_path(str(SCRIPT), run_name="pythia160_capture_test")
    yield namespace["main"].__globals__
    sys.modules.pop(AUTHENTICATED_MODULE, None)


def test_synthetic_builder_roundtrip_and_provider_manifest_join() -> None:
    default, exact, config = _sources()
    receipt = acquisition._build_pythia160_identity_acquisition_receipt(
        default_model_info_source=default,
        exact_model_info_source=exact,
        config_source=config,
        source_binding=_source_binding(),
    )
    document = receipt.to_dict()

    assert acquisition._resolved_revision_from_model_info(default) == REVISION
    assert document["schema_version"] == (
        "spirallens.pythia160-identity-acquisition-receipt.v0.1"
    )
    assert document["status"] == "review_pending"
    assert document["model"] == {
        "model_id": "EleutherAI/pythia-160m",
        "selection_rule": "resolve-default-head-once-then-requery-exact-commit",
        "resolved_revision": REVISION,
        "review_status": "provider_resolved_unreviewed",
    }
    assert [item["repository_path"] for item in document["evidence"]["siblings"]] == [
        "config.json",
        "model.safetensors",
        "tokenizer.json",
    ]
    config_evidence = document["evidence"]["config"]
    assert config_evidence == {
        "repository_path": "config.json",
        "byte_count": len(config),
        "sha256": hashlib.sha256(config).hexdigest(),
        "git_blob_sha1": _git_blob(config),
        "provider_git_blob_oid": _git_blob(config),
        "content_status": "retrieved_bytes_joined_to_provider_git_blob",
        "profile_status": "not_derived_or_reviewed",
    }
    assert document["source_binding"]["review_status"] == (
        "source_bound_review_pending"
    )
    assert receipt.canonical_bytes == _json_bytes(document)
    assert (
        receipt.canonical_sha256 == hashlib.sha256(receipt.canonical_bytes).hexdigest()
    )
    assert receipt.sha256 == receipt.canonical_sha256
    assert (
        acquisition._Pythia160IdentityAcquisitionReceipt.from_canonical_bytes(
            receipt.canonical_bytes
        )
        == receipt
    )


def test_closed_access_verification_authority_and_claim_axes() -> None:
    document = _receipt().to_dict()
    assert document["access_facts"] == {
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
    assert document["verification_facts"] == {
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
    assert document["authority_facts"]
    assert all(value is False for value in document["authority_facts"].values())
    assert document["claim_boundary"] == {
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


@pytest.mark.parametrize(
    "mutation",
    [
        "revision",
        "model_id",
        "config_size",
        "config_blob",
        "missing_config",
        "duplicate_config",
        "duplicate_path",
        "config_lfs_empty",
        "config_lfs_sha",
    ],
)
def test_builder_rejects_revision_file_config_and_lfs_tamper(mutation: str) -> None:
    default, exact, config = _sources()
    document = json.loads(exact)
    if mutation == "revision":
        document["sha"] = "9" * 40
    elif mutation == "model_id":
        document["id"] = "EleutherAI/pythia-70m"
    elif mutation == "config_size":
        document["siblings"][2]["size"] += 1
    elif mutation == "config_blob":
        document["siblings"][2]["blobId"] = "8" * 40
    elif mutation == "missing_config":
        document["siblings"].pop(2)
    elif mutation == "duplicate_config":
        document["siblings"].append(deepcopy(document["siblings"][2]))
    elif mutation == "duplicate_path":
        document["siblings"][0]["rfilename"] = "tokenizer.json"
    elif mutation == "config_lfs_empty":
        document["siblings"][2]["lfs"] = {}
    else:
        document["siblings"][2]["lfs"] = {"sha256": "7" * 64, "size": len(config)}

    with pytest.raises(acquisition._Pythia160IdentityAcquisitionError):
        acquisition._build_pythia160_identity_acquisition_receipt(
            default_model_info_source=default,
            exact_model_info_source=_json_bytes(document),
            config_source=config,
            source_binding=_source_binding(),
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "blob_alias_conflict",
        "lfs_digest_alias_conflict",
        "lfs_sha_without_size",
        "lfs_size_without_sha",
    ],
)
def test_provider_aliases_and_lfs_metadata_must_be_unambiguous_and_complete(
    mutation: str,
) -> None:
    default, exact, config = _sources()
    document = json.loads(exact)
    model_file = document["siblings"][0]
    if mutation == "blob_alias_conflict":
        model_file["blobId"] = "4" * 40
        model_file["blob_id"] = "5" * 40
    elif mutation == "lfs_digest_alias_conflict":
        model_file["lfs"]["oid"] = "6" * 64
    elif mutation == "lfs_sha_without_size":
        del model_file["lfs"]["size"]
    else:
        del model_file["lfs"]["sha256"]

    with pytest.raises(acquisition._Pythia160IdentityAcquisitionError):
        acquisition._build_pythia160_identity_acquisition_receipt(
            default_model_info_source=default,
            exact_model_info_source=_json_bytes(document),
            config_source=config,
            source_binding=_source_binding(),
        )


@pytest.mark.parametrize(
    ("present", "digest", "byte_count"),
    [
        (True, None, None),
        (True, "2" * 64, None),
        (True, None, 10),
        (False, "2" * 64, 10),
    ],
)
def test_receipt_lfs_presence_is_exactly_equivalent_to_digest_and_size(
    present: bool, digest: str | None, byte_count: int | None
) -> None:
    document = _receipt().to_dict()
    sibling = next(
        item
        for item in document["evidence"]["siblings"]
        if item["repository_path"] == "model.safetensors"
    )
    sibling["provider_lfs_metadata_present"] = present
    sibling["provider_lfs_sha256"] = digest
    sibling["provider_lfs_byte_count"] = byte_count
    with pytest.raises(acquisition._Pythia160IdentityAcquisitionError):
        acquisition._Pythia160IdentityAcquisitionReceipt.from_payload(document)


@pytest.mark.parametrize(
    "path",
    [
        "../config.json",
        "/config.json",
        "./config.json",
        "a//config.json",
        "a\\config.json",
        "a\x00config.json",
    ],
)
def test_provider_sibling_paths_must_be_normalized_relative_posix(path: str) -> None:
    default, exact, config = _sources()
    document = json.loads(exact)
    document["siblings"][0]["rfilename"] = path
    with pytest.raises(acquisition._Pythia160IdentityAcquisitionError):
        acquisition._build_pythia160_identity_acquisition_receipt(
            default_model_info_source=default,
            exact_model_info_source=_json_bytes(document),
            config_source=config,
            source_binding=_source_binding(),
        )


@pytest.mark.parametrize(
    "source",
    [
        b'{"id":"EleutherAI/pythia-160m","id":"duplicate","sha":"' + b"1" * 40 + b'"}',
        b'{"id":"EleutherAI/pythia-160m","sha":"' + b"1" * 40 + b'","x":NaN}',
        b'{"id":"EleutherAI/pythia-160m","sha":"' + b"1" * 40 + b'","x":Infinity}',
        b'{"id":"EleutherAI/pythia-160m","sha":"' + b"1" * 40 + b'","x":1e999}',
        b'{"id":"EleutherAI/pythia-160m","sha":"' + b"1" * 40 + b'","x":-0}',
        b'{"id":"EleutherAI/pythia-160m","sha":"' + b"1" * 40 + b'","\\ud800":0}',
        b"[]",
        b"\xff",
    ],
)
def test_default_model_info_strict_json_adversaries(source: bytes) -> None:
    with pytest.raises(acquisition._Pythia160IdentityAcquisitionError):
        acquisition._resolved_revision_from_model_info(source)


@pytest.mark.parametrize(
    "source",
    [
        b"\xef\xbb\xbf" + _sources()[0],
        _sources()[0].decode("utf-8").encode("utf-16"),
        _sources()[0].decode("utf-8").encode("utf-16-le"),
        _sources()[0].decode("utf-8").encode("utf-16-be"),
        _sources()[0].decode("utf-8").encode("utf-32"),
        _sources()[0].decode("utf-8").encode("utf-32-le"),
        _sources()[0].decode("utf-8").encode("utf-32-be"),
    ],
)
def test_provider_json_is_strictly_unmarked_utf8(source: bytes) -> None:
    with pytest.raises(acquisition._Pythia160IdentityAcquisitionError):
        acquisition._resolved_revision_from_model_info(source)


def test_config_strict_json_and_raw_size_bounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    default, exact, _config = _sources()
    for config in (
        b'{"x":NaN}',
        b'{"x":1e999}',
        b'{"x":1,"x":2}',
        b"[]",
    ):
        with pytest.raises(acquisition._Pythia160IdentityAcquisitionError):
            acquisition._build_pythia160_identity_acquisition_receipt(
                default_model_info_source=default,
                exact_model_info_source=exact,
                config_source=config,
                source_binding=_source_binding(),
            )

    monkeypatch.setattr(acquisition, "_MAX_MODEL_INFO_BYTES", len(default) - 1)
    with pytest.raises(acquisition._Pythia160IdentityAcquisitionError):
        acquisition._resolved_revision_from_model_info(default)


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [
        ("access_facts", "model_loaded", True),
        ("verification_facts", "model_identity_reviewed", True),
        ("authority_facts", "scientific_claim_eligible", True),
        ("claim_boundary", "claim_ceiling", "level_1"),
    ],
)
def test_receipt_rejects_closed_fact_tamper(
    section: str, key: str, value: object
) -> None:
    document = _receipt().to_dict()
    document[section][key] = value
    with pytest.raises(acquisition._Pythia160IdentityAcquisitionError):
        acquisition._Pythia160IdentityAcquisitionReceipt.from_payload(document)


@pytest.mark.parametrize(
    ("section", "key", "alias"),
    [
        ("access_facts", "model_loaded", 0),
        ("access_facts", "network_accessed", 1),
        ("verification_facts", "external_witness_verified", 0),
        ("verification_facts", "config_git_blob_join_verified", 1),
        ("authority_facts", "scientific_claim_eligible", 0),
        ("claim_boundary", "identity_review_completed", 0),
    ],
)
def test_receipt_closed_boolean_facts_reject_integer_aliases(
    section: str, key: str, alias: int
) -> None:
    document = _receipt().to_dict()
    document[section][key] = alias
    with pytest.raises(acquisition._Pythia160IdentityAcquisitionError):
        acquisition._Pythia160IdentityAcquisitionReceipt.from_payload(document)


def test_receipt_rejects_noncanonical_duplicate_and_config_binding_tamper() -> None:
    receipt = _receipt()
    pretty = json.dumps(receipt.to_dict(), indent=2).encode("utf-8")
    with pytest.raises(acquisition._Pythia160IdentityAcquisitionError):
        acquisition._Pythia160IdentityAcquisitionReceipt.from_canonical_bytes(pretty)
    with pytest.raises(acquisition._Pythia160IdentityAcquisitionError):
        acquisition._Pythia160IdentityAcquisitionReceipt(pretty.decode("utf-8"))
    duplicate = receipt.canonical_bytes.replace(
        b'"artifact_role":', b'"artifact_role":"duplicate","artifact_role":', 1
    )
    with pytest.raises(acquisition._Pythia160IdentityAcquisitionError):
        acquisition._Pythia160IdentityAcquisitionReceipt.from_canonical_bytes(duplicate)

    document = receipt.to_dict()
    document["evidence"]["config"]["git_blob_sha1"] = "0" * 40
    with pytest.raises(acquisition._Pythia160IdentityAcquisitionError):
        acquisition._Pythia160IdentityAcquisitionReceipt.from_payload(document)


@pytest.mark.parametrize(
    ("descriptor", "byte_count"),
    [
        ("default_model_info", 4 * 1024 * 1024 + 1),
        ("exact_model_info", 4 * 1024 * 1024 + 1),
        ("config", 1024 * 1024 + 1),
    ],
)
def test_receipt_descriptors_cannot_claim_sources_above_acquisition_bounds(
    descriptor: str, byte_count: int
) -> None:
    document = _receipt().to_dict()
    if descriptor == "config":
        document["evidence"]["config"]["byte_count"] = byte_count
    else:
        document["evidence"][descriptor]["byte_count"] = byte_count
    with pytest.raises(acquisition._Pythia160IdentityAcquisitionError):
        acquisition._Pythia160IdentityAcquisitionReceipt.from_payload(document)


@pytest.mark.parametrize(
    "mutation",
    ["repository", "commit", "member_order", "member_path", "member_digest", "extra"],
)
def test_source_binding_contract_is_exact(mutation: str) -> None:
    default, exact, config = _sources()
    binding = _source_binding()
    if mutation == "repository":
        binding["repository"] = "https://example.invalid/repository.git"
    elif mutation == "commit":
        binding["source_commit"] = "main"
    elif mutation == "member_order":
        binding["members"].reverse()
    elif mutation == "member_path":
        binding["members"][0]["repository_path"] = "scripts/other.py"
    elif mutation == "member_digest":
        binding["members"][0]["sha256"] = "z" * 64
    else:
        binding["extra"] = False
    with pytest.raises(acquisition._Pythia160IdentityAcquisitionError):
        acquisition._build_pythia160_identity_acquisition_receipt(
            default_model_info_source=default,
            exact_model_info_source=exact,
            config_source=config,
            source_binding=binding,
        )


def test_script_exact_api_config_and_cache_url_contract(
    script_namespace: dict[str, object],
) -> None:
    validate = script_namespace["_validate_https_url"]
    default = script_namespace["_DEFAULT_INFO_URL"]
    validate(default, frozenset({default}))
    with pytest.raises(script_namespace["_CaptureError"]):
        validate(default + "&full=true", frozenset({default}))
    with pytest.raises(script_namespace["_CaptureError"]):
        validate(default.replace("https://", "http://"), frozenset({default}))
    with pytest.raises(script_namespace["_CaptureError"]):
        validate(
            default.replace("huggingface.co", "example.invalid"), frozenset({default})
        )
    with pytest.raises(script_namespace["_CaptureError"]):
        validate(
            default.replace("huggingface.co", "user@huggingface.co"),
            frozenset({default}),
        )

    allowed = script_namespace["_allowed_config_urls"](REVISION)
    direct = (
        f"https://huggingface.co/EleutherAI/pythia-160m/resolve/{REVISION}/config.json"
    )
    cache = (
        "https://huggingface.co/api/resolve-cache/models/EleutherAI/pythia-160m/"
        f"{REVISION}/config.json"
    )
    validate(direct, allowed)
    validate(cache + "?etag=abc123", allowed)
    with pytest.raises(script_namespace["_CaptureError"]):
        validate(cache + "?etag=one&etag=two", allowed)
    with pytest.raises(script_namespace["_CaptureError"]):
        validate(cache + "?etag=%GG", allowed)
    with pytest.raises(script_namespace["_CaptureError"]):
        validate(cache.replace("huggingface.co", "cdn-lfs.huggingface.co"), allowed)
    with pytest.raises(script_namespace["_CaptureError"]):
        validate(cache.replace("config.json", "%63onfig.json"), allowed)


def test_script_redirect_is_same_route_and_single_hop(
    script_namespace: dict[str, object],
) -> None:
    request_type = script_namespace["Request"]
    handler_type = script_namespace["_PinnedRedirectHandler"]
    capture_error = script_namespace["_CaptureError"]
    allowed = script_namespace["_allowed_config_urls"](REVISION)
    direct, cache = sorted(allowed)
    handler = handler_type(allowed)
    request = request_type(direct)
    redirected = handler.redirect_request(
        request, None, 302, "Found", {}, cache + "?etag=abc"
    )
    assert redirected.full_url == cache + "?etag=abc"
    with pytest.raises(capture_error, match="redirect count"):
        handler.redirect_request(request, None, 302, "Found", {}, direct)

    off_route = handler_type(allowed)
    with pytest.raises(capture_error, match="fixed HTTPS"):
        off_route.redirect_request(
            request, None, 302, "Found", {}, "https://example.invalid/config.json"
        )


@pytest.mark.parametrize(
    "environment_name",
    [
        "HF_TOKEN",
        "HUGGING_FACE_HUB_TOKEN",
        "HTTPS_PROXY",
        "NETRC",
        "OPENSSL_CONF",
        "OPENSSL_CONF_INCLUDE",
        "OPENSSL_ENGINES",
        "OPENSSL_MODULES",
        "SSL_CERT_FILE",
        "SSLKEYLOGFILE",
    ],
)
def test_script_refuses_credentials_proxy_and_ambient_tls(
    script_namespace: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    environment_name: str,
) -> None:
    for name in script_namespace["_FORBIDDEN_ENVIRONMENT"]:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(environment_name, "secret-or-route")
    with pytest.raises(script_namespace["_CaptureError"], match="refuses"):
        script_namespace["_refuse_ambient_network_authority"]()


@pytest.mark.parametrize(
    "environment_name",
    [
        "OPENSSL_CONF",
        "OPENSSL_CONF_INCLUDE",
        "OPENSSL_ENGINES",
        "OPENSSL_MODULES",
    ],
)
def test_openssl_environment_is_refused_before_tls_import_or_operation(
    tmp_path: Path,
    environment_name: str,
) -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert source.index("_FORBIDDEN_OPENSSL_ENVIRONMENT") < source.index("import ssl")
    assert source.index("_FORBIDDEN_OPENSSL_ENVIRONMENT") < source.index(
        "from urllib.error"
    )
    stage = ROOT / "experiments/pythia/model_identity/.pythia160-v0.1.stage"
    output = ROOT / "experiments/pythia/model_identity/pythia160-v0.1"
    assert not stage.exists()
    assert not output.exists()
    secret = "secret-openssl-route-and-module-path"

    completed = subprocess.run(
        [sys.executable, "-I", "-S", str(SCRIPT)],
        cwd=tmp_path,
        env={"PATH": "/usr/bin:/bin", environment_name: secret},
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert completed.stdout == ""
    assert completed.stderr == (
        "Pythia-160M identity capture refuses ambient OpenSSL configuration\n"
    )
    assert secret not in completed.stderr
    assert not stage.exists()
    assert not output.exists()


@pytest.mark.parametrize(
    "mutation",
    [
        {"st_uid": 501},
        {"st_nlink": 2},
        {"st_mode": stat.S_IFREG | 0o664},
        {"st_mode": stat.S_IFREG | 0o646},
        {"st_mode": stat.S_IFDIR | 0o644},
        {"st_size": 0},
        {"st_size": 4 * 1024 * 1024 + 1},
    ],
)
def test_fixed_ca_metadata_requires_exact_owner_mode_type_link_and_bound(
    script_namespace: dict[str, object], mutation: dict[str, int]
) -> None:
    assert script_namespace["_FIXED_CA_BUNDLE"] == Path("/private/etc/ssl/cert.pem")
    assert script_namespace["_MAX_CA_BUNDLE_BYTES"] == 4 * 1024 * 1024
    metadata = {
        "st_mode": stat.S_IFREG | 0o644,
        "st_nlink": 1,
        "st_uid": 0,
        "st_size": 1,
    }
    assert script_namespace["_safe_fixed_ca_metadata"](SimpleNamespace(**metadata))
    metadata.update(mutation)
    assert not script_namespace["_safe_fixed_ca_metadata"](SimpleNamespace(**metadata))


def _configure_synthetic_ca_bundle(
    namespace: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    path: Path,
    *,
    maximum_bytes: int = 64,
) -> None:
    monkeypatch.setitem(namespace, "_FIXED_CA_BUNDLE", path)
    monkeypatch.setitem(namespace, "_MAX_CA_BUNDLE_BYTES", maximum_bytes)

    def safe_for_unprivileged_test(metadata: os.stat_result) -> bool:
        return bool(
            stat.S_ISREG(metadata.st_mode)
            and metadata.st_nlink == 1
            and stat.S_IMODE(metadata.st_mode) & 0o022 == 0
            and 0 < metadata.st_size <= namespace["_MAX_CA_BUNDLE_BYTES"]
        )

    # Root ownership itself is covered by the pure metadata test above. This
    # substitution lets the held-descriptor reader be exercised in tmp_path.
    monkeypatch.setitem(
        namespace, "_safe_fixed_ca_metadata", safe_for_unprivileged_test
    )


def test_fixed_ca_reader_returns_exact_bytes_from_held_bounded_descriptor(
    script_namespace: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = b"synthetic-fixed-ca-pem"
    bundle = tmp_path / "cert.pem"
    bundle.write_bytes(source)
    bundle.chmod(0o444)
    _configure_synthetic_ca_bundle(script_namespace, monkeypatch, bundle)
    real_read = os.read
    requested: list[int] = []

    def tracked_read(descriptor: int, maximum: int) -> bytes:
        requested.append(maximum)
        return real_read(descriptor, maximum)

    monkeypatch.setattr(script_namespace["os"], "read", tracked_read)
    assert script_namespace["_read_fixed_ca_bundle"]() == source
    assert requested
    assert max(requested) <= script_namespace["_MAX_CA_BUNDLE_BYTES"] + 1


@pytest.mark.parametrize("kind", ["symlink", "directory", "empty", "oversize"])
def test_fixed_ca_reader_rejects_symlink_nonregular_empty_and_oversize(
    script_namespace: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    kind: str,
) -> None:
    bundle = tmp_path / "cert.pem"
    if kind == "symlink":
        target = tmp_path / "target.pem"
        target.write_bytes(b"certificate")
        target.chmod(0o444)
        bundle.symlink_to(target)
    elif kind == "directory":
        bundle.mkdir()
    elif kind == "empty":
        bundle.write_bytes(b"")
        bundle.chmod(0o444)
    else:
        bundle.write_bytes(b"x" * 65)
        bundle.chmod(0o444)
    _configure_synthetic_ca_bundle(script_namespace, monkeypatch, bundle)

    with pytest.raises(script_namespace["_CaptureError"], match="fixed TLS CA"):
        script_namespace["_read_fixed_ca_bundle"]()


def test_fixed_ca_reader_rejects_metadata_drift_during_held_read(
    script_namespace: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bundle = tmp_path / "cert.pem"
    bundle.write_bytes(b"stable-until-held-read")
    bundle.chmod(0o444)
    _configure_synthetic_ca_bundle(script_namespace, monkeypatch, bundle)
    real_read = os.read
    changed = False

    def drifting_read(descriptor: int, maximum: int) -> bytes:
        nonlocal changed
        source = real_read(descriptor, maximum)
        if source and not changed:
            changed = True
            metadata = bundle.stat()
            os.utime(
                bundle,
                ns=(metadata.st_atime_ns, metadata.st_mtime_ns + 1_000_000_000),
            )
        return source

    monkeypatch.setattr(script_namespace["os"], "read", drifting_read)
    with pytest.raises(script_namespace["_CaptureError"], match="changed during"):
        script_namespace["_read_fixed_ca_bundle"]()
    assert changed


def test_tls_builder_loads_only_supplied_fixed_ca_bytes(
    script_namespace: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    script_source = SCRIPT.read_text(encoding="utf-8")
    assert "create_default_context" not in script_source
    assert "load_default_certs" not in script_source
    assert "set_default_verify_paths" not in script_source
    supplied = b"-----BEGIN CERTIFICATE-----\nsynthetic\n-----END CERTIFICATE-----\n"
    protocol = object()

    class FakeTLSVersion:
        TLSv1_2 = 2

    class FakeContext:
        def __init__(self, selected_protocol: object) -> None:
            assert selected_protocol is protocol
            self.protocol = selected_protocol
            self.verify_mode = None
            self.check_hostname = False
            self.minimum_version = 0
            self.loaded: list[str] = []

        def load_verify_locations(self, *, cadata: str) -> None:
            self.loaded.append(cadata)

        def cert_store_stats(self) -> dict[str, int]:
            return {"x509_ca": len(self.loaded)}

    fake_ssl = SimpleNamespace(
        CERT_REQUIRED=2,
        PROTOCOL_TLS_CLIENT=protocol,
        SSLError=ssl.SSLError,
        SSLContext=FakeContext,
        TLSVersion=FakeTLSVersion,
    )
    monkeypatch.setitem(script_namespace, "ssl", fake_ssl)
    monkeypatch.setitem(script_namespace, "_read_fixed_ca_bundle", lambda: supplied)

    context = script_namespace["_build_fixed_tls_context"]()
    assert type(context) is FakeContext
    assert context.loaded == [supplied.decode("ascii")]
    assert context.verify_mode == fake_ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert context.minimum_version == fake_ssl.TLSVersion.TLSv1_2


def test_tls_builder_redacts_ca_parse_and_context_load_failures(
    script_namespace: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    capture_error = script_namespace["_CaptureError"]
    monkeypatch.setitem(
        script_namespace, "_read_fixed_ca_bundle", lambda: b"secret-\xff-ca-path"
    )
    with pytest.raises(capture_error) as non_ascii:
        script_namespace["_build_fixed_tls_context"]()
    assert "secret" not in str(non_ascii.value)
    assert "ASCII PEM" in str(non_ascii.value)

    secret = "secret-provider-ca-body-and-local-path"
    monkeypatch.setitem(
        script_namespace, "_read_fixed_ca_bundle", lambda: secret.encode("ascii")
    )
    with pytest.raises(capture_error) as invalid_pem:
        script_namespace["_build_fixed_tls_context"]()
    assert secret not in str(invalid_pem.value)
    assert "could not establish trust" in str(invalid_pem.value)


def test_tls_context_rejects_zero_ca_wrong_verify_hostname_and_minimum_before_open(
    script_namespace: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    cadata = script_namespace["_read_fixed_ca_bundle"]().decode("ascii")

    def populated_context() -> ssl.SSLContext:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.load_verify_locations(cadata=cadata)
        return context

    zero_ca = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    wrong_verify = populated_context()
    wrong_verify.check_hostname = False
    wrong_verify.verify_mode = ssl.CERT_NONE
    wrong_hostname = populated_context()
    wrong_hostname.check_hostname = False
    wrong_minimum = populated_context()
    wrong_minimum.minimum_version = ssl.TLSVersion.MINIMUM_SUPPORTED
    contexts = [zero_ca, wrong_verify, wrong_hostname, wrong_minimum]
    opener_calls = 0

    def forbidden_opener(*_handlers: object) -> object:
        nonlocal opener_calls
        opener_calls += 1
        raise AssertionError("invalid TLS context must fail before an HTTPS opener")

    monkeypatch.setitem(script_namespace, "build_opener", forbidden_opener)
    url = script_namespace["_DEFAULT_INFO_URL"]
    for context in contexts:
        with pytest.raises(
            script_namespace["_CaptureError"], match="usable verified client"
        ):
            script_namespace["_fetch_bytes"](
                url,
                allowed_urls=frozenset({url}),
                maximum_bytes=128,
                tls_context=context,
            )
    assert opener_calls == 0


def test_fetch_uses_explicit_proxyless_https_handler_with_exact_context(
    script_namespace: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    tls_context = object()
    handlers: list[object] = []
    validations: list[object] = []
    url = script_namespace["_DEFAULT_INFO_URL"]

    class Response:
        status = 200
        headers = {"Content-Encoding": "identity", "Content-Length": "2"}

        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def geturl(self) -> str:
            return url

        def read(self, _maximum: int) -> bytes:
            return b"{}"

    class Opener:
        def open(self, _request: object, *, timeout: int) -> Response:
            assert timeout == script_namespace["_TIMEOUT_SECONDS"]
            return Response()

    def build(*supplied_handlers: object) -> Opener:
        handlers.extend(supplied_handlers)
        return Opener()

    monkeypatch.setitem(
        script_namespace,
        "_require_usable_tls_context",
        lambda context: validations.append(context),
    )
    monkeypatch.setitem(script_namespace, "build_opener", build)

    assert (
        script_namespace["_fetch_bytes"](
            url,
            allowed_urls=frozenset({url}),
            maximum_bytes=128,
            tls_context=tls_context,
        )
        == b"{}"
    )
    assert validations == [tls_context]
    assert len(handlers) == 3
    assert type(handlers[0]) is script_namespace["ProxyHandler"]
    assert handlers[0].proxies == {}
    assert type(handlers[1]) is script_namespace["HTTPSHandler"]
    assert handlers[1]._context is tls_context
    assert type(handlers[2]) is script_namespace["_PinnedRedirectHandler"]


def test_tls_load_failure_is_sanitized_preflight_before_stage_or_network(
    script_namespace: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[str] = []
    stage = tmp_path / ".pythia160-v0.1.stage"
    output = tmp_path / "pythia160-v0.1"
    secret = "secret-invalid-ca-body-and-local-path"

    def ca_source() -> bytes:
        events.append("tls")
        return secret.encode("ascii")

    def forbidden(name: str):
        def operation(*_args: object, **_kwargs: object) -> object:
            events.append(name)
            raise AssertionError(f"{name} must not run after TLS preflight failure")

        return operation

    monkeypatch.setitem(script_namespace, "_STAGE_DIRECTORY", stage)
    monkeypatch.setitem(script_namespace, "_OUTPUT_DIRECTORY", output)
    monkeypatch.setitem(script_namespace, "_require_isolated_runtime", lambda: None)
    monkeypatch.setitem(
        script_namespace, "_refuse_ambient_network_authority", lambda: None
    )
    monkeypatch.setitem(
        script_namespace,
        "_verified_source",
        lambda **_kwargs: (SOURCE_COMMIT, b"kernel", b"script"),
    )
    monkeypatch.setitem(
        script_namespace, "_require_output_namespace_absent", lambda: None
    )
    monkeypatch.setitem(script_namespace, "_kernel", lambda _source: object())
    monkeypatch.setitem(script_namespace, "_read_fixed_ca_bundle", ca_source)
    monkeypatch.setitem(
        script_namespace, "_reserve_output_directory", forbidden("reserve")
    )
    monkeypatch.setitem(script_namespace, "_fetch_bytes", forbidden("network"))
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])

    with pytest.raises(script_namespace["_CaptureError"]) as caught:
        script_namespace["main"]()

    error = caught.value
    assert events == ["tls"]
    assert str(error) == "Pythia-160M identity capture failed during preflight"
    assert secret not in str(error)
    assert error.phase == "preflight"
    assert error.stage_retained is False
    assert error.publication_visible is False
    assert error.__cause__ is None
    assert error.__context__ is None
    assert not stage.exists()
    assert not output.exists()


def test_manual_authenticated_kernel_load_uses_supplied_head_bytes(
    script_namespace: dict[str, object],
) -> None:
    source = KERNEL.read_bytes()
    loaded = script_namespace["_kernel"](source)
    assert loaded.__all__ == ()
    assert loaded._resolved_revision_from_model_info(_sources()[0]) == REVISION
    assert loaded.__file__ == str(ROOT / script_namespace["_KERNEL_REPOSITORY_PATH"])
    sys.modules.pop(AUTHENTICATED_MODULE, None)

    with pytest.raises(script_namespace["_CaptureError"], match="exported"):
        script_namespace["_kernel"](source + b'\n__all__ = ("forged",)\n')
    assert AUTHENTICATED_MODULE not in sys.modules


def test_isolated_runtime_gate_is_exact_and_closed(
    script_namespace: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(script_namespace, "_ISOLATED_RUNTIME", False)
    with pytest.raises(script_namespace["_CaptureError"], match="python3 -I -S"):
        script_namespace["_require_isolated_runtime"]()

    monkeypatch.setitem(script_namespace, "_ISOLATED_RUNTIME", True)
    assert script_namespace["_require_isolated_runtime"]() is None


def test_main_rejects_nonisolated_runtime_before_any_operational_helper(
    script_namespace: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[str] = []
    stage = tmp_path / ".pythia160-v0.1.stage"
    output = tmp_path / "pythia160-v0.1"

    def touched(name: str):
        def operation(*_args: object, **_kwargs: object) -> object:
            events.append(name)
            raise AssertionError(f"{name} must not run")

        return operation

    monkeypatch.setitem(script_namespace, "_ISOLATED_RUNTIME", False)
    monkeypatch.setitem(script_namespace, "_STAGE_DIRECTORY", stage)
    monkeypatch.setitem(script_namespace, "_OUTPUT_DIRECTORY", output)
    for name in (
        "_refuse_ambient_network_authority",
        "_verified_source",
        "_require_output_namespace_absent",
        "_kernel",
        "_build_fixed_tls_context",
        "_reserve_output_directory",
        "_fetch_bytes",
    ):
        monkeypatch.setitem(script_namespace, name, touched(name))
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])

    with pytest.raises(script_namespace["_CaptureError"]) as caught:
        script_namespace["main"]()

    assert events == []
    error = caught.value
    assert error.phase == "preflight"
    assert error.stage_retained is False
    assert error.publication_visible is False
    assert error.cleanup_authorized is False
    assert error.resume_authorized is False
    assert error.retry_authorized is False
    assert error.__cause__ is None


def test_capture_failure_object_has_no_private_cause_or_context(
    script_namespace: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setitem(
        script_namespace, "_STAGE_DIRECTORY", tmp_path / ".pythia160-v0.1.stage"
    )
    monkeypatch.setitem(
        script_namespace, "_OUTPUT_DIRECTORY", tmp_path / "pythia160-v0.1"
    )

    error = script_namespace["_capture_failure"](phase="preflight")
    assert type(error) is script_namespace["_CaptureError"]
    assert error.__cause__ is None
    assert error.__context__ is None
    assert str(error) == "Pythia-160M identity capture failed during preflight"


def test_top_level_failure_stderr_is_closed_and_contains_no_injected_detail(
    tmp_path: Path,
) -> None:
    secret = "secret-provider-body-token-and-local-path"
    source = SCRIPT.read_text(encoding="utf-8")
    target = "        _require_isolated_runtime()\n"
    assert source.count(target) == 1
    source = source.replace(target, f"        raise OSError({secret!r})\n", 1)
    launcher = (
        f"namespace = {{'__name__': '__main__', '__file__': {str(SCRIPT)!r}}}; "
        f"source = {source!r}; "
        f"exec(compile(source, {str(SCRIPT)!r}, 'exec'), namespace)"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-S", "-c", launcher],
        cwd=tmp_path,
        env={"PATH": "/usr/bin:/bin"},
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert completed.stdout == ""
    assert completed.stderr == (
        "Pythia-160M identity capture blocked: phase=preflight; "
        "stage_retained=False; publication_visible=False; "
        "cleanup_authorized=false; resume_authorized=false; "
        "retry_authorized=false\n"
    )
    assert secret not in completed.stderr
    assert "OSError" not in completed.stderr
    assert "Traceback" not in completed.stderr


def test_nonisolated_sourceless_script_directory_shadow_is_never_imported(
    tmp_path: Path,
) -> None:
    script_directory = tmp_path / "scripts"
    script_directory.mkdir()
    copied_script = script_directory / SCRIPT.name
    copied_script.write_bytes(SCRIPT.read_bytes())
    marker = tmp_path / "shadow-imported"
    shadow_source = script_directory / "hashlib.py"
    shadow_bytecode = script_directory / "hashlib.pyc"
    shadow_source.write_text(
        f"open({str(marker)!r}, 'wb').write(b'imported')\n", encoding="utf-8"
    )
    py_compile.compile(str(shadow_source), cfile=str(shadow_bytecode), doraise=True)
    shadow_source.unlink()

    completed = subprocess.run(
        [sys.executable, str(copied_script)],
        cwd=tmp_path,
        env={"PATH": "/usr/bin:/bin"},
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert completed.stdout == ""
    assert "requires isolated `python3 -I -S`" in completed.stderr
    assert not marker.exists()


def test_main_source_preflight_happens_before_any_network(
    script_namespace: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[str] = []

    secret = "private-preflight-source-detail"

    def blocked_source(**_kwargs: object) -> object:
        events.append("source")
        raise OSError(secret)

    def network(*_args: object, **_kwargs: object) -> bytes:
        events.append("network")
        raise AssertionError("network must not be attempted")

    monkeypatch.setitem(
        script_namespace, "_refuse_ambient_network_authority", lambda: None
    )
    monkeypatch.setitem(script_namespace, "_require_isolated_runtime", lambda: None)
    monkeypatch.setitem(
        script_namespace, "_STAGE_DIRECTORY", tmp_path / ".pythia160-v0.1.stage"
    )
    monkeypatch.setitem(
        script_namespace, "_OUTPUT_DIRECTORY", tmp_path / "pythia160-v0.1"
    )
    monkeypatch.setitem(script_namespace, "_verified_source", blocked_source)
    monkeypatch.setitem(script_namespace, "_fetch_bytes", network)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])
    with pytest.raises(script_namespace["_CaptureError"]) as caught:
        script_namespace["main"]()
    assert events == ["source"]
    assert str(caught.value) == ("Pythia-160M identity capture failed during preflight")
    assert secret not in str(caught.value)
    assert caught.value.phase == "preflight"
    assert caught.value.stage_retained is False
    assert caught.value.publication_visible is False
    assert caught.value.cleanup_authorized is False
    assert caught.value.resume_authorized is False
    assert caught.value.retry_authorized is False
    assert caught.value.__cause__ is None


@pytest.mark.parametrize(
    ("stage_exists", "output_exists"),
    [(True, False), (False, True), (True, True)],
)
def test_preflight_failure_reports_existing_stage_and_output_without_authority(
    script_namespace: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    stage_exists: bool,
    output_exists: bool,
) -> None:
    repository = tmp_path / "repository"
    output_parent = repository / "experiments/pythia/model_identity"
    output_parent.mkdir(parents=True)
    output_parent.chmod(0o700)
    stage = output_parent / ".pythia160-v0.1.stage"
    output = output_parent / "pythia160-v0.1"
    if stage_exists:
        stage.mkdir()
    if output_exists:
        output.mkdir()
    calls = {"kernel": 0, "network": 0}

    def kernel(*_args: object, **_kwargs: object) -> object:
        calls["kernel"] += 1
        raise AssertionError("kernel must not load after occupied namespace")

    def network(*_args: object, **_kwargs: object) -> bytes:
        calls["network"] += 1
        raise AssertionError("network must not be attempted")

    monkeypatch.setitem(script_namespace, "_REPOSITORY", repository)
    monkeypatch.setitem(script_namespace, "_OUTPUT_PARENT", output_parent)
    monkeypatch.setitem(script_namespace, "_STAGE_DIRECTORY", stage)
    monkeypatch.setitem(script_namespace, "_OUTPUT_DIRECTORY", output)
    monkeypatch.setitem(script_namespace, "_require_isolated_runtime", lambda: None)
    monkeypatch.setitem(
        script_namespace, "_refuse_ambient_network_authority", lambda: None
    )
    monkeypatch.setitem(
        script_namespace,
        "_verified_source",
        lambda **_kwargs: (SOURCE_COMMIT, KERNEL.read_bytes(), SCRIPT.read_bytes()),
    )
    monkeypatch.setitem(script_namespace, "_kernel", kernel)
    monkeypatch.setitem(script_namespace, "_fetch_bytes", network)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])
    with pytest.raises(script_namespace["_CaptureError"]) as caught:
        script_namespace["main"]()

    error = caught.value
    assert str(error) == "Pythia-160M identity capture failed during preflight"
    assert error.phase == "preflight"
    assert error.stage_retained is stage_exists
    assert error.publication_visible is output_exists
    assert error.cleanup_authorized is False
    assert error.resume_authorized is False
    assert error.retry_authorized is False
    assert error.__cause__ is None
    assert error.__context__ is None
    assert calls == {"kernel": 0, "network": 0}


def _configure_fake_main(
    namespace: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[dict[str, bytes], list[tuple[str, bool]]]:
    repository = tmp_path / "repository"
    (repository / "experiments/pythia").mkdir(parents=True)
    output_parent = repository / "experiments/pythia/model_identity"
    output = output_parent / "pythia160-v0.1"
    stage = output_parent / ".pythia160-v0.1.stage"
    default, exact, config = _sources()
    kernel_source = KERNEL.read_bytes()
    script_source = SCRIPT.read_bytes()
    fetches: list[tuple[str, bool]] = []
    tls_context = object()
    real_reserve = namespace["_reserve_output_directory"]

    def verified_source(*, allow_owned_stage: bool = False):
        fetches.append(("source", allow_owned_stage))
        return SOURCE_COMMIT, kernel_source, script_source

    def fetch(url: str, **_kwargs: object) -> bytes:
        assert _kwargs["tls_context"] is tls_context
        assert stage.is_dir()
        assert list(stage.iterdir()) == []
        fetches.append((url, False))
        if "/revision/" in url:
            return exact
        if url.endswith("/config.json"):
            return config
        return default

    def reserve():
        owned = real_reserve()
        fetches.append(("reserve", False))
        return owned

    def build_tls_context() -> object:
        fetches.append(("tls", False))
        return tls_context

    monkeypatch.setitem(namespace, "_REPOSITORY", repository)
    monkeypatch.setitem(namespace, "_OUTPUT_PARENT", output_parent)
    monkeypatch.setitem(namespace, "_OUTPUT_DIRECTORY", output)
    monkeypatch.setitem(namespace, "_STAGE_DIRECTORY", stage)
    monkeypatch.setitem(
        namespace,
        "_DEFAULT_MODEL_INFO_OUTPUT",
        output / "provider-default-model-info.json",
    )
    monkeypatch.setitem(
        namespace, "_EXACT_MODEL_INFO_OUTPUT", output / "provider-exact-model-info.json"
    )
    monkeypatch.setitem(namespace, "_CONFIG_OUTPUT", output / "config.json")
    monkeypatch.setitem(namespace, "_RECEIPT_OUTPUT", output / "identity-receipt.json")
    monkeypatch.setitem(namespace, "_require_isolated_runtime", lambda: None)
    monkeypatch.setitem(namespace, "_refuse_ambient_network_authority", lambda: None)
    monkeypatch.setitem(namespace, "_verified_source", verified_source)
    monkeypatch.setitem(namespace, "_build_fixed_tls_context", build_tls_context)
    monkeypatch.setitem(namespace, "_reserve_output_directory", reserve)
    monkeypatch.setitem(namespace, "_fetch_bytes", fetch)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])
    return {"default": default, "exact": exact, "config": config}, fetches


def test_main_stages_and_atomically_publishes_exact_four_files(
    script_namespace: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    sources, events = _configure_fake_main(script_namespace, monkeypatch, tmp_path)
    stage = script_namespace["_STAGE_DIRECTORY"]
    output = script_namespace["_OUTPUT_DIRECTORY"]
    writes: list[str] = []
    real_write = script_namespace["_write_exclusive"]

    def tracked_write(owned: object, name: str, source: bytes) -> None:
        writes.append(name)
        real_write(owned, name, source)

    def fake_publish(owned: object, _expected: dict[str, bytes]) -> None:
        os.rename(
            stage.name,
            output.name,
            src_dir_fd=owned.parent_fd,
            dst_dir_fd=owned.parent_fd,
        )
        os.fsync(owned.parent_fd)

    monkeypatch.setitem(script_namespace, "_write_exclusive", tracked_write)
    monkeypatch.setitem(
        script_namespace, "_native_publish_stage_no_replace", fake_publish
    )
    assert script_namespace["main"]() == 0

    assert writes == [
        "provider-default-model-info.json",
        "provider-exact-model-info.json",
        "config.json",
        "identity-receipt.json",
    ]
    assert not stage.exists()
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    assert (output / writes[0]).read_bytes() == sources["default"]
    assert (output / writes[1]).read_bytes() == sources["exact"]
    assert (output / writes[2]).read_bytes() == sources["config"]
    receipt_source = (output / writes[3]).read_bytes()
    loaded = acquisition._Pythia160IdentityAcquisitionReceipt.from_canonical_bytes(
        receipt_source
    )
    assert loaded.to_dict()["source_binding"]["source_commit"] == SOURCE_COMMIT
    assert events[:3] == [
        ("source", False),
        ("tls", False),
        ("reserve", False),
    ]
    assert events[-2:] == [("source", False), ("source", True)]
    assert all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in output.iterdir())


def test_main_passes_one_tls_context_to_all_three_explicit_https_openers(
    script_namespace: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    real_fetch = script_namespace["_fetch_bytes"]
    sources, _events = _configure_fake_main(script_namespace, monkeypatch, tmp_path)
    stage = script_namespace["_STAGE_DIRECTORY"]
    output = script_namespace["_OUTPUT_DIRECTORY"]
    tls_context = object()
    opened_contexts: list[object] = []

    class Response:
        status = 200

        def __init__(self, url: str, source: bytes) -> None:
            self._url = url
            self._source = source
            self.headers = {
                "Content-Encoding": "identity",
                "Content-Length": str(len(source)),
            }

        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def geturl(self) -> str:
            return self._url

        def read(self, _maximum: int) -> bytes:
            return self._source

    class Opener:
        def open(self, request: object, *, timeout: int) -> Response:
            assert timeout == script_namespace["_TIMEOUT_SECONDS"]
            url = request.full_url
            if "/revision/" in url:
                source = sources["exact"]
            elif url.endswith("/config.json"):
                source = sources["config"]
            else:
                source = sources["default"]
            return Response(url, source)

    def build(*handlers: object) -> Opener:
        assert len(handlers) == 3
        assert type(handlers[0]) is script_namespace["ProxyHandler"]
        assert handlers[0].proxies == {}
        assert type(handlers[1]) is script_namespace["HTTPSHandler"]
        assert type(handlers[2]) is script_namespace["_PinnedRedirectHandler"]
        opened_contexts.append(handlers[1]._context)
        return Opener()

    def fake_publish(owned: object, _expected: dict[str, bytes]) -> None:
        os.rename(
            stage.name,
            output.name,
            src_dir_fd=owned.parent_fd,
            dst_dir_fd=owned.parent_fd,
        )
        os.fsync(owned.parent_fd)

    monkeypatch.setitem(
        script_namespace, "_build_fixed_tls_context", lambda: tls_context
    )
    monkeypatch.setitem(
        script_namespace,
        "_require_usable_tls_context",
        lambda context: (
            context is tls_context
            or (_ for _ in ()).throw(AssertionError("TLS context identity changed"))
        ),
    )
    monkeypatch.setitem(script_namespace, "build_opener", build)
    monkeypatch.setitem(script_namespace, "_fetch_bytes", real_fetch)
    monkeypatch.setitem(
        script_namespace, "_native_publish_stage_no_replace", fake_publish
    )

    assert script_namespace["main"]() == 0
    assert opened_contexts == [tls_context, tls_context, tls_context]
    assert output.is_dir()
    assert not stage.exists()


def test_provider_failure_retains_durable_empty_stage_and_never_writes(
    script_namespace: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _sources_by_name, events = _configure_fake_main(
        script_namespace, monkeypatch, tmp_path
    )
    stage = script_namespace["_STAGE_DIRECTORY"]
    output = script_namespace["_OUTPUT_DIRECTORY"]
    secret = "injected-provider-response-and-token-detail"

    def fail_provider(*_args: object, **_kwargs: object) -> bytes:
        assert stage.is_dir()
        assert list(stage.iterdir()) == []
        events.append(("failed-provider-request", False))
        raise OSError(secret)

    monkeypatch.setitem(script_namespace, "_fetch_bytes", fail_provider)
    monkeypatch.setitem(
        script_namespace,
        "_write_exclusive",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("provider failure must not write")
        ),
    )

    with pytest.raises(script_namespace["_CaptureError"]) as caught:
        script_namespace["main"]()

    error = caught.value
    assert events == [
        ("source", False),
        ("tls", False),
        ("reserve", False),
        ("failed-provider-request", False),
    ]
    assert str(error) == (
        "Pythia-160M identity capture failed during provider_acquisition"
    )
    assert secret not in str(error)
    assert error.phase == "provider_acquisition"
    assert error.stage_retained is True
    assert error.publication_visible is False
    assert error.cleanup_authorized is False
    assert error.resume_authorized is False
    assert error.retry_authorized is False
    assert error.__cause__ is None
    assert error.__context__ is None
    assert stage.is_dir()
    assert list(stage.iterdir()) == []
    assert not output.exists()


def test_partial_write_failure_retains_stage_and_never_publishes(
    script_namespace: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_fake_main(script_namespace, monkeypatch, tmp_path)
    stage = script_namespace["_STAGE_DIRECTORY"]
    output = script_namespace["_OUTPUT_DIRECTORY"]
    real_write = script_namespace["_write_exclusive"]
    count = 0
    secret = "injected-secret-token-and-config-detail"

    def fail_third(owned: object, name: str, source: bytes) -> None:
        nonlocal count
        count += 1
        if count == 3:
            raise OSError(secret)
        real_write(owned, name, source)

    monkeypatch.setitem(script_namespace, "_write_exclusive", fail_third)
    monkeypatch.setitem(
        script_namespace,
        "_native_publish_stage_no_replace",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("must not publish")
        ),
    )
    with pytest.raises(script_namespace["_CaptureError"]) as caught:
        script_namespace["main"]()
    error = caught.value
    assert str(error) == (
        "Pythia-160M identity capture failed during stage_publication"
    )
    assert secret not in str(error)
    assert error.phase == "stage_publication"
    assert error.stage_retained is True
    assert error.publication_visible is False
    assert error.cleanup_authorized is False
    assert error.resume_authorized is False
    assert error.retry_authorized is False
    assert error.__cause__ is None
    assert error.__context__ is None
    assert not output.exists()
    assert sorted(path.name for path in stage.iterdir()) == [
        "provider-default-model-info.json",
        "provider-exact-model-info.json",
    ]


def test_publish_failure_retains_complete_stage_for_review(
    script_namespace: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_fake_main(script_namespace, monkeypatch, tmp_path)
    stage = script_namespace["_STAGE_DIRECTORY"]
    output = script_namespace["_OUTPUT_DIRECTORY"]

    secret = "injected-private-publication-detail"

    def fail_publish(_owned: object, _expected: dict[str, bytes]) -> None:
        raise script_namespace["_CaptureError"](secret)

    monkeypatch.setitem(
        script_namespace, "_native_publish_stage_no_replace", fail_publish
    )
    with pytest.raises(script_namespace["_CaptureError"]) as caught:
        script_namespace["main"]()
    error = caught.value
    assert str(error) == (
        "Pythia-160M identity capture failed during stage_publication"
    )
    assert secret not in str(error)
    assert error.phase == "stage_publication"
    assert error.stage_retained is True
    assert error.publication_visible is False
    assert error.cleanup_authorized is False
    assert error.resume_authorized is False
    assert error.retry_authorized is False
    assert error.__cause__ is None
    assert error.__context__ is None
    assert not output.exists()
    assert sorted(path.name for path in stage.iterdir()) == [
        "config.json",
        "identity-receipt.json",
        "provider-default-model-info.json",
        "provider-exact-model-info.json",
    ]


def test_post_publication_verification_failure_reports_visible_output_without_authority(
    script_namespace: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_fake_main(script_namespace, monkeypatch, tmp_path)
    stage = script_namespace["_STAGE_DIRECTORY"]
    output = script_namespace["_OUTPUT_DIRECTORY"]
    real_reverify = script_namespace["_reverify_owned_stage"]
    secret = "injected-private-post-publication-detail"

    def fake_publish(owned: object, _expected: dict[str, bytes]) -> None:
        os.rename(
            stage.name,
            output.name,
            src_dir_fd=owned.parent_fd,
            dst_dir_fd=owned.parent_fd,
        )
        os.fsync(owned.parent_fd)

    def fail_after_publish(
        owned: object, expected: dict[str, bytes], *, published: bool
    ) -> None:
        real_reverify(owned, expected, published=published)
        if published:
            raise OSError(secret)

    monkeypatch.setitem(
        script_namespace, "_native_publish_stage_no_replace", fake_publish
    )
    monkeypatch.setitem(script_namespace, "_reverify_owned_stage", fail_after_publish)
    with pytest.raises(script_namespace["_CaptureError"]) as caught:
        script_namespace["main"]()

    error = caught.value
    assert str(error) == (
        "Pythia-160M identity capture failed during post_publication_verification"
    )
    assert secret not in str(error)
    assert error.phase == "post_publication_verification"
    assert error.stage_retained is False
    assert error.publication_visible is True
    assert error.cleanup_authorized is False
    assert error.resume_authorized is False
    assert error.retry_authorized is False
    assert error.__cause__ is None
    assert error.__context__ is None
    assert not stage.exists()
    assert sorted(path.name for path in output.iterdir()) == [
        "config.json",
        "identity-receipt.json",
        "provider-default-model-info.json",
        "provider-exact-model-info.json",
    ]


def test_held_descriptors_remain_live_through_postpublication_then_close(
    script_namespace: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_fake_main(script_namespace, monkeypatch, tmp_path)
    stage_path = script_namespace["_STAGE_DIRECTORY"]
    output_path = script_namespace["_OUTPUT_DIRECTORY"]
    configured_reserve = script_namespace["_reserve_output_directory"]
    real_reverify = script_namespace["_reverify_owned_stage"]
    captured: dict[str, object] = {}
    held_descriptors: list[int] = []

    def tracked_reserve():
        owned = configured_reserve()
        captured["owned"] = owned
        return owned

    def fake_publish(owned: object, _expected: dict[str, bytes]) -> None:
        os.rename(
            stage_path.name,
            output_path.name,
            src_dir_fd=owned.parent_fd,
            dst_dir_fd=owned.parent_fd,
        )
        os.fsync(owned.parent_fd)

    def tracked_reverify(
        owned: object, expected: dict[str, bytes], *, published: bool
    ) -> None:
        real_reverify(owned, expected, published=published)
        if published:
            descriptors = [
                owned.parent_fd,
                owned.stage_fd,
                *owned.file_fds.values(),
            ]
            assert len(descriptors) == 6
            for descriptor in descriptors:
                os.fstat(descriptor)
            held_descriptors[:] = descriptors

    monkeypatch.setitem(script_namespace, "_reserve_output_directory", tracked_reserve)
    monkeypatch.setitem(
        script_namespace, "_native_publish_stage_no_replace", fake_publish
    )
    monkeypatch.setitem(script_namespace, "_reverify_owned_stage", tracked_reverify)

    assert script_namespace["main"]() == 0
    owned = captured["owned"]
    assert held_descriptors
    assert owned.parent_fd == -1
    assert owned.stage_fd == -1
    assert owned.file_fds == {}
    for descriptor in held_descriptors:
        with pytest.raises(OSError):
            os.fstat(descriptor)


def _reserve_complete_owned_stage(
    namespace: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[object, dict[str, bytes], Path, Path]:
    repository = tmp_path / "repository"
    (repository / "experiments/pythia").mkdir(parents=True)
    output_parent = repository / "experiments/pythia/model_identity"
    stage_path = output_parent / ".pythia160-v0.1.stage"
    output_path = output_parent / "pythia160-v0.1"
    monkeypatch.setitem(namespace, "_REPOSITORY", repository)
    monkeypatch.setitem(namespace, "_OUTPUT_PARENT", output_parent)
    monkeypatch.setitem(namespace, "_STAGE_DIRECTORY", stage_path)
    monkeypatch.setitem(namespace, "_OUTPUT_DIRECTORY", output_path)
    owned = namespace["_reserve_output_directory"]()
    expected = {
        name: f"synthetic-{name}".encode("ascii") for name in namespace["_OUTPUT_NAMES"]
    }
    for name in namespace["_OUTPUT_NAMES"]:
        namespace["_write_exclusive"](owned, name, expected[name])
    namespace["_reverify_owned_stage"](owned, expected, published=False)
    return owned, expected, stage_path, output_path


def test_member_swap_between_verification_and_rename_is_detected_as_visible(
    script_namespace: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    owned, expected, _stage_path, output_path = _reserve_complete_owned_stage(
        script_namespace, monkeypatch, tmp_path
    )
    real_reverify = script_namespace["_reverify_owned_stage"]
    swapped = False
    member_name = "config.json"

    def swap_after_verification(
        stage: object, candidate: dict[str, bytes], *, published: bool
    ) -> None:
        nonlocal swapped
        real_reverify(stage, candidate, published=published)
        if not published and not swapped:
            swapped = True
            os.unlink(member_name, dir_fd=stage.stage_fd)
            descriptor = os.open(
                member_name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=stage.stage_fd,
            )
            try:
                os.write(descriptor, candidate[member_name])
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            os.fsync(stage.stage_fd)

    monkeypatch.setitem(
        script_namespace, "_reverify_owned_stage", swap_after_verification
    )
    try:
        with pytest.raises(script_namespace["_CaptureError"]):
            script_namespace["_native_publish_stage_no_replace"](owned, expected)
        failure = script_namespace["_capture_failure"](
            phase="stage_publication", owned_stage=owned
        )
        assert swapped is True
        assert failure.stage_retained is False
        assert failure.publication_visible is True
        assert failure.cleanup_authorized is False
        assert failure.resume_authorized is False
        assert failure.retry_authorized is False
        assert output_path.is_dir()
    finally:
        owned.close()


def test_stage_entry_swap_between_verification_and_rename_is_detected_as_unknown(
    script_namespace: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    owned, expected, stage_path, output_path = _reserve_complete_owned_stage(
        script_namespace, monkeypatch, tmp_path
    )
    real_reverify = script_namespace["_reverify_owned_stage"]
    displaced_name = ".pythia160-v0.1.displaced"
    swapped = False

    def swap_after_verification(
        stage: object, candidate: dict[str, bytes], *, published: bool
    ) -> None:
        nonlocal swapped
        real_reverify(stage, candidate, published=published)
        if not published and not swapped:
            swapped = True
            os.rename(
                stage_path.name,
                displaced_name,
                src_dir_fd=stage.parent_fd,
                dst_dir_fd=stage.parent_fd,
            )
            os.mkdir(stage_path.name, 0o700, dir_fd=stage.parent_fd)
            os.fsync(stage.parent_fd)

    monkeypatch.setitem(
        script_namespace, "_reverify_owned_stage", swap_after_verification
    )
    try:
        with pytest.raises(script_namespace["_CaptureError"]):
            script_namespace["_native_publish_stage_no_replace"](owned, expected)
        failure = script_namespace["_capture_failure"](
            phase="stage_publication", owned_stage=owned
        )
        assert swapped is True
        assert failure.stage_retained is None
        assert failure.publication_visible is None
        assert failure.cleanup_authorized is False
        assert failure.resume_authorized is False
        assert failure.retry_authorized is False
        assert output_path.is_dir()
    finally:
        owned.close()


def test_existing_output_or_stage_is_never_overwritten(
    script_namespace: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    (repository / "experiments/pythia/model_identity/pythia160-v0.1").mkdir(
        parents=True
    )
    marker = repository / "experiments/pythia/model_identity/pythia160-v0.1/keep"
    marker.write_bytes(b"existing")
    (repository / "experiments/pythia/model_identity").chmod(0o700)
    monkeypatch.setitem(script_namespace, "_REPOSITORY", repository)
    monkeypatch.setitem(
        script_namespace,
        "_OUTPUT_PARENT",
        repository / "experiments/pythia/model_identity",
    )
    monkeypatch.setitem(script_namespace, "_OUTPUT_DIRECTORY", marker.parent)
    monkeypatch.setitem(
        script_namespace,
        "_STAGE_DIRECTORY",
        repository / "experiments/pythia/model_identity/.pythia160-v0.1.stage",
    )
    with pytest.raises(script_namespace["_CaptureError"], match="must be empty"):
        script_namespace["_reserve_output_directory"]()
    assert marker.read_bytes() == b"existing"


def test_source_preflight_claims_only_local_origin_tracking_candidate() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    constants = {
        node.value
        for node in ast.walk(ast.parse(source, filename=str(SCRIPT)))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert (
        "identity capture requires HEAD equal to the local origin/main "
        "tracking candidate"
    ) in constants
    assert all("remote origin/main is verified" not in value for value in constants)


def test_private_inert_surface_and_no_model_or_cache_capability() -> None:
    kernel_tree = ast.parse(KERNEL.read_text(encoding="utf-8"), filename=str(KERNEL))
    script_tree = ast.parse(SCRIPT.read_text(encoding="utf-8"), filename=str(SCRIPT))

    def imports(tree: ast.AST) -> set[str]:
        return {
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        } | {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }

    forbidden = {
        "huggingface_hub",
        "numpy",
        "requests",
        "safetensors",
        "torch",
        "transformers",
    }
    assert imports(kernel_tree).isdisjoint(forbidden | {"os", "subprocess", "urllib"})
    assert imports(script_tree).isdisjoint(forbidden)
    forbidden_calls = {
        "from_pretrained",
        "forward",
        "generate",
        "hf_hub_download",
        "load",
        "snapshot_download",
    }
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in forbidden_calls
        for tree in (kernel_tree, script_tree)
        for node in ast.walk(tree)
    )
    assert acquisition.__all__ == ()
    assert not any("Pythia160Identity" in name for name in access.__all__)
    assert "capture_pythia160_identity" not in (ROOT / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    assert "_pythia160_identity_acquisition" not in (
        ROOT / "src/spirallens/access/__init__.py"
    ).read_text(encoding="utf-8")
    assert not (ROOT / "experiments/pythia/model_identity").exists()


def test_pr58_and_frozen_70m_invariants_remain_exact() -> None:
    expected = {
        ROOT / "src/spirallens/access/_pythia160_preobservation.py": (
            "daff98dfb6402ac568e1ed16ee46edf59c6bdd63ad0ef74fb512a085aac6b9b6"
        ),
        ROOT / "tests/test_pythia160_preobservation.py": (
            "319f177309daa061e4aff0dc8b6074b5c26b5179aeed7d2fdccd66dd642e433d"
        ),
        ROOT / "protocols/pythia70_public_example_plumbing_v0_1.yaml": (
            "ef93891c7450ef13cc2c5da54bf1a80d4a0b679df2df04964f2cc505e00aaf4c"
        ),
        ROOT
        / "experiments/pythia/receipts/pythia70_public_example_plumbing_v0_1.json": (
            "4ab51c1e01992dc63f9bea18a7f53e00293a0ec11617f4970abf2a400723ce82"
        ),
    }
    assert {
        path: hashlib.sha256(path.read_bytes()).hexdigest() for path in expected
    } == expected
    assert set(engineering_protocol._ENGINEERING_MODEL_PROFILES_BY_ID) == {
        "EleutherAI/pythia-70m"
    }
    with pytest.raises(engineering_protocol._UnsupportedEngineeringModelProfileError):
        engineering_protocol._require_engineering_model_profile(
            "EleutherAI/pythia-160m"
        )
