from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

import spirallens.atlas as atlas_api
from spirallens.atlas import engineering_protocol, engineering_receipt
from spirallens.atlas import engineering_run, id_sweep, store


EXPECTED_ATLAS_EXPORTS = [
    "ATLAS_SCHEMA_VERSION",
    "ATLAS_CONTEXT_BINDING_SCHEMA_VERSION",
    "AtlasIntegrityError",
    "AtlasStateError",
    "ContextBankBinding",
    "EngineeringConsumerAuthorizationError",
    "LoadedPublicExamplePlumbingProtocol",
    "PublicExamplePlumbingProtocolError",
    "PublicExamplePlumbingReceiptError",
    "PublicExamplePlumbingRunError",
    "SweepConfig",
    "load_manifest",
    "load_manifest_metadata",
    "load_public_example_plumbing_protocol",
    "load_public_example_plumbing_receipt",
    "require_engineering_consumer_authorized",
    "run_id_sweep",
    "run_public_example_plumbing",
    "select_token_ids",
    "validate_engineering_request_binding",
]

EXPECTED_SYMBOL_MODULES = {
    "AtlasIntegrityError": "spirallens.atlas.store",
    "AtlasStateError": "spirallens.atlas.store",
    "ContextBankBinding": "spirallens.atlas.id_sweep",
    "EngineeringConsumerAuthorizationError": ("spirallens.atlas.engineering_protocol"),
    "LoadedPublicExamplePlumbingProtocol": ("spirallens.atlas.engineering_protocol"),
    "PublicExamplePlumbingProtocolError": ("spirallens.atlas.engineering_protocol"),
    "PublicExamplePlumbingReceiptError": ("spirallens.atlas.engineering_receipt"),
    "PublicExamplePlumbingRunError": "spirallens.atlas.engineering_run",
    "SweepConfig": "spirallens.atlas.id_sweep",
    "load_manifest": "spirallens.atlas.store",
    "load_manifest_metadata": "spirallens.atlas.store",
    "load_public_example_plumbing_protocol": ("spirallens.atlas.engineering_protocol"),
    "load_public_example_plumbing_receipt": ("spirallens.atlas.engineering_receipt"),
    "require_engineering_consumer_authorized": (
        "spirallens.atlas.engineering_protocol"
    ),
    "run_id_sweep": "spirallens.atlas.id_sweep",
    "run_public_example_plumbing": "spirallens.atlas.engineering_run",
    "select_token_ids": "spirallens.atlas.id_sweep",
    "validate_engineering_request_binding": ("spirallens.atlas.engineering_protocol"),
}


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _slice_sha256(
    name: str,
    array: np.ndarray,
    *,
    start_row: int,
    end_row: int,
) -> str:
    view = np.ascontiguousarray(array[start_row:end_row])
    header = {
        "schema_version": store.ATLAS_SCHEMA_VERSION,
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


def _write_minimal_complete_atlas(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    root = tmp_path / "atlas"
    root.mkdir()
    arrays = {
        "token_ids": np.asarray([7], dtype=np.int64),
        "resid_pre": np.asarray([[[1.0, 0.0]]], dtype=np.float32),
        "resid_post": np.asarray([[[1.0, 1.0]]], dtype=np.float32),
        "norm_summary": np.asarray([[[1.0, 2.0**0.5]]], dtype=np.float32),
        "logit_summary": np.zeros((1, 6), dtype=np.float32),
        "prediction_ids": np.asarray([3], dtype=np.int64),
    }
    columns = {
        "norm_summary": ["resid_pre_l2", "resid_post_l2"],
        "logit_summary": [
            "max_logit",
            "mean_logit",
            "std_logit",
            "logsumexp_logit",
            "entropy_nats",
            "input_token_logit",
        ],
    }
    descriptors: dict[str, dict[str, object]] = {}
    for name, array in arrays.items():
        path = root / f"{name}.npy"
        np.save(path, array, allow_pickle=False)
        descriptors[name] = {
            "path": path.name,
            "shape": list(array.shape),
            "dtype": str(array.dtype),
            "sha256": _file_sha256(path),
        }
        if name in columns:
            descriptors[name]["columns"] = columns[name]

    capture = {
        "atlas_schema_version": store.ATLAS_SCHEMA_VERSION,
        "capture_implementation": {
            "name": "reader-characterization-fixture",
            "version": "test.v1",
            "accelerator_to_cpu_copy": "synchronous",
            "activation_dtype": "float32",
        },
        "spirallens_version": "test",
        "torch_version": "test",
        "transformers_version": "test",
        "effective_parameter_layout": [
            {
                "device": "cpu",
                "dtype": "float32",
                "parameter_tensors": 1,
                "parameter_values": 1,
            }
        ],
    }
    capture_fingerprint = _canonical_sha256(capture)
    token_digest = hashlib.sha256(
        np.asarray(arrays["token_ids"], dtype="<i8", order="C").tobytes(order="C")
    ).hexdigest()
    batch_commit = {
        "batch_index": 0,
        "start_row": 0,
        "end_row": 1,
        "committed_at": "2026-01-01T00:00:00+00:00",
        "array_sha256": {
            name: _slice_sha256(name, array, start_row=0, end_row=1)
            for name, array in sorted(arrays.items())
        },
    }
    manifest: dict[str, object] = {
        "schema_version": store.ATLAS_SCHEMA_VERSION,
        "status": "complete",
        "run_id": "reader-characterization-atlas",
        "run_fingerprint": "f" * 64,
        "capture": capture,
        "capture_fingerprint": capture_fingerprint,
        "request": {
            "model_id": "test/pythia",
            "model_revision": "test-revision",
            "context_ids": [0, 1],
            "attention_mask": [1, 1],
            "position": 1,
            "selection": {
                "kind": "subset",
                "subset_size_before_limit": 1,
            },
            "num_tokens": 1,
            "token_ids_sha256": token_digest,
            "capture_dtype": "float32",
            "capture_fingerprint": capture_fingerprint,
            "config_sha256": "c" * 64,
        },
        "model": {
            "architecture": "GPTNeoXForCausalLM",
            "num_layers": 1,
            "hidden_size": 2,
            "vocab_size": 100,
            "config": {},
            "rope": {"rotary_pct": 0.25},
        },
        "arrays": descriptors,
        "progress": {
            "completed_rows": 1,
            "total_rows": 1,
            "committed_batches": 1,
        },
        "attempts": [
            {
                "started_at": "2026-01-01T00:00:00+00:00",
                "resume_from_row": 0,
                "batch_size": 1,
                "capture": capture,
                "capture_fingerprint": capture_fingerprint,
            }
        ],
        "batch_commits": [batch_commit],
        "environment": {},
        "summaries": {},
        "failure": None,
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True),
        encoding="utf-8",
    )
    return root, manifest


def _assert_no_exception_chain(error: BaseException) -> None:
    assert error.__cause__ is None
    assert error.__context__ is None


def test_atlas_reader_public_surface_signatures_and_symbol_identities() -> None:
    assert atlas_api.__all__ == EXPECTED_ATLAS_EXPORTS
    assert str(inspect.signature(atlas_api.load_manifest)) == (
        "(output_dir: 'str | Path', *, verify_checksums: 'bool' = True) "
        "-> 'dict[str, Any]'"
    )
    assert str(inspect.signature(atlas_api.load_manifest_metadata)) == (
        "(output_dir: 'str | Path') -> 'dict[str, Any]'"
    )
    assert atlas_api.load_manifest is store.load_manifest
    assert atlas_api.load_manifest_metadata is store.load_manifest_metadata
    assert atlas_api.AtlasIntegrityError is store.AtlasIntegrityError
    assert atlas_api.AtlasStateError is store.AtlasStateError
    assert atlas_api.ContextBankBinding is id_sweep.ContextBankBinding
    assert atlas_api.SweepConfig is id_sweep.SweepConfig
    assert atlas_api.run_id_sweep is id_sweep.run_id_sweep
    assert (
        atlas_api.run_public_example_plumbing
        is engineering_run.run_public_example_plumbing
    )
    assert (
        atlas_api.load_public_example_plumbing_receipt
        is engineering_receipt.load_public_example_plumbing_receipt
    )
    assert (
        atlas_api.load_public_example_plumbing_protocol
        is engineering_protocol.load_public_example_plumbing_protocol
    )
    assert {
        name: getattr(getattr(atlas_api, name), "__module__", None)
        for name in EXPECTED_SYMBOL_MODULES
    } == EXPECTED_SYMBOL_MODULES


def test_atlas_reader_imports_are_capture_runtime_free_and_lazy_exports_hold() -> None:
    """Prove the reader closure under an adversarial import blocker."""

    source_root = Path(__file__).resolve().parents[1] / "src"
    probe = f"""
import importlib
import importlib.abc
import json
import sys

sys.path.insert(0, {str(source_root)!r})

forbidden = (
    "torch",
    "transformers",
    "huggingface_hub",
    "safetensors",
    "spirallens.adapters",
    "spirallens.atlas.id_sweep",
    "spirallens.atlas.engineering_run",
    "spirallens.atlas._capture_store",
)
capture_modules = (
    "spirallens.atlas._capture_store",
    "spirallens.atlas.engineering_run",
    "spirallens.atlas.id_sweep",
)
expected_exports = {EXPECTED_ATLAS_EXPORTS!r}


def matches(name, prefix):
    return name == prefix or name.startswith(prefix + ".")


class Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(matches(fullname, prefix) for prefix in forbidden):
            raise ModuleNotFoundError(f"blocked capture dependency: {{fullname}}")
        return None


blocker = Blocker()
sys.meta_path.insert(0, blocker)
import spirallens.atlas as atlas
store = importlib.import_module("spirallens.atlas.store")
receipt = importlib.import_module("spirallens.atlas.engineering_receipt")

blocked_loaded = sorted(
    prefix
    for prefix in forbidden
    if any(matches(name, prefix) for name in sys.modules)
)
capture_before = sorted(name for name in capture_modules if name in sys.modules)
ordered_exports = list(atlas.__all__)
dir_has_all_exports = set(expected_exports).issubset(dir(atlas))
reader_symbol_modules = [
    atlas.load_manifest.__module__,
    atlas.load_manifest_metadata.__module__,
]
reader_identities = (
    atlas.load_manifest is store.load_manifest
    and atlas.load_manifest_metadata is store.load_manifest_metadata
    and atlas.AtlasIntegrityError is store.AtlasIntegrityError
    and atlas.AtlasStateError is store.AtlasStateError
    and atlas.load_public_example_plumbing_receipt
    is receipt.load_public_example_plumbing_receipt
)

sys.meta_path.remove(blocker)
context_binding = atlas.ContextBankBinding
id_sweep = importlib.import_module("spirallens.atlas.id_sweep")
capture_after_id_sweep = sorted(
    name for name in capture_modules if name in sys.modules
)
run_public_example_plumbing = atlas.run_public_example_plumbing
engineering_run = importlib.import_module("spirallens.atlas.engineering_run")
capture_after_engineering_run = sorted(
    name for name in capture_modules if name in sys.modules
)

star_namespace = {{}}
exec("from spirallens.atlas import *", star_namespace)
from_star_identity = all(
    star_namespace[name] is getattr(atlas, name) for name in expected_exports
)
lazy_values_cached = all(
    name in atlas.__dict__
    for name in (
        "ATLAS_CONTEXT_BINDING_SCHEMA_VERSION",
        "ContextBankBinding",
        "PublicExamplePlumbingRunError",
        "SweepConfig",
        "run_id_sweep",
        "run_public_example_plumbing",
        "select_token_ids",
    )
)

print(json.dumps({{
    "blocked_modules_loaded": blocked_loaded,
    "capture_after_engineering_run": capture_after_engineering_run,
    "capture_after_id_sweep": capture_after_id_sweep,
    "capture_before": capture_before,
    "dir_has_all_exports": dir_has_all_exports,
    "from_star_identity": from_star_identity,
    "lazy_symbol_identities": (
        context_binding is id_sweep.ContextBankBinding
        and run_public_example_plumbing
        is engineering_run.run_public_example_plumbing
    ),
    "lazy_values_cached": lazy_values_cached,
    "ordered_exports": ordered_exports,
    "reader_identities": reader_identities,
    "reader_symbol_modules": reader_symbol_modules,
}}, sort_keys=True))
"""
    completed = subprocess.run(
        [sys.executable, "-P", "-c", probe],
        cwd=source_root.parent,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "blocked_modules_loaded": [],
        "capture_after_engineering_run": [
            "spirallens.atlas._capture_store",
            "spirallens.atlas.engineering_run",
            "spirallens.atlas.id_sweep",
        ],
        "capture_after_id_sweep": [
            "spirallens.atlas._capture_store",
            "spirallens.atlas.id_sweep",
        ],
        "capture_before": [],
        "dir_has_all_exports": True,
        "from_star_identity": True,
        "lazy_symbol_identities": True,
        "lazy_values_cached": True,
        "ordered_exports": EXPECTED_ATLAS_EXPORTS,
        "reader_identities": True,
        "reader_symbol_modules": [
            "spirallens.atlas.store",
            "spirallens.atlas.store",
        ],
    }


def test_manifest_readers_preserve_success_and_checksum_switch(
    tmp_path: Path,
) -> None:
    root, manifest = _write_minimal_complete_atlas(tmp_path)

    assert atlas_api.load_manifest_metadata(root) == manifest
    assert atlas_api.load_manifest(root) == manifest

    manifest_path = root / "manifest.json"
    with_invalid_checksum = json.loads(manifest_path.read_text(encoding="utf-8"))
    with_invalid_checksum["arrays"]["resid_pre"]["sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(with_invalid_checksum, sort_keys=True),
        encoding="utf-8",
    )

    assert (
        atlas_api.load_manifest(root, verify_checksums=False) == with_invalid_checksum
    )
    actual = _file_sha256(root / "resid_pre.npy")
    with pytest.raises(store.AtlasIntegrityError) as caught:
        atlas_api.load_manifest(root)
    assert str(caught.value) == (f"resid_pre checksum mismatch: {actual} != {'0' * 64}")
    _assert_no_exception_chain(caught.value)


def test_manifest_reader_failure_order_and_exception_chains(tmp_path: Path) -> None:
    missing_root = tmp_path / "missing"
    with pytest.raises(store.AtlasStateError) as missing:
        atlas_api.load_manifest_metadata(missing_root)
    assert str(missing.value) == (
        f"atlas manifest does not exist: {missing_root / 'manifest.json'}"
    )
    _assert_no_exception_chain(missing.value)

    malformed_root = tmp_path / "malformed"
    malformed_root.mkdir()
    malformed_path = malformed_root / "manifest.json"
    malformed_path.write_text("{", encoding="utf-8")
    with pytest.raises(store.AtlasIntegrityError) as malformed:
        atlas_api.load_manifest_metadata(malformed_root)
    assert str(malformed.value) == (
        f"cannot read {malformed_path}: Expecting property name enclosed in "
        "double quotes: line 1 column 2 (char 1)"
    )
    assert isinstance(malformed.value.__cause__, json.JSONDecodeError)
    assert malformed.value.__context__ is malformed.value.__cause__

    non_object_root = tmp_path / "non-object"
    non_object_root.mkdir()
    non_object_path = non_object_root / "manifest.json"
    non_object_path.write_text("[]", encoding="utf-8")
    with pytest.raises(store.AtlasIntegrityError) as non_object:
        atlas_api.load_manifest_metadata(non_object_root)
    assert str(non_object.value) == f"{non_object_path} must contain a JSON object"
    _assert_no_exception_chain(non_object.value)

    old_schema_root = tmp_path / "old-schema"
    old_schema_root.mkdir()
    (old_schema_root / "manifest.json").write_text(
        json.dumps({"schema_version": "spirallens.activation_atlas.v1"}),
        encoding="utf-8",
    )
    with pytest.raises(store.AtlasIntegrityError) as old_schema:
        atlas_api.load_manifest_metadata(old_schema_root)
    assert str(old_schema.value) == (
        "unsupported atlas schema: 'spirallens.activation_atlas.v1' != "
        "'spirallens.activation_atlas.v2'"
    )
    _assert_no_exception_chain(old_schema.value)
