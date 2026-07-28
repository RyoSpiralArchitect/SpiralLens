from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import spirallens
import spirallens.access as access
import spirallens.core as core
from spirallens.core import canonical as core_canonical
from spirallens.instrument_contracts import canonical as legacy_canonical


EXPECTED_CORE_EXPORTS = [
    "CanonicalJsonError",
    "JsonScalar",
    "JsonValue",
    "canonical_json_bytes",
    "canonical_json_sha256",
    "parse_canonical_json",
    "sha256_bytes",
]

EXPECTED_ACCESS_EXPORTS = [
    "ATLAS_PREPARATION_DESCRIPTOR_SCHEMA_VERSION",
    "ATLAS_PREPARATION_VIEW_SCHEMA_VERSION",
    "ATTEMPT_TERMINAL_RECORD_SCHEMA_VERSION",
    "MAX_ATLAS_PREPARATION_DESCRIPTOR_BYTES",
    "AtlasAccessContractError",
    "AtlasAccessPolicy",
    "AtlasConsumer",
    "AtlasConsumerDenied",
    "AtlasPreparationDescriptor",
    "AtlasPreparationView",
    "AttemptAccessFacts",
    "AttemptLifecycle",
    "AttemptLifecycleError",
    "AttemptPhase",
    "AttemptPolicy",
    "AttemptTerminalRecord",
    "AttemptTerminalState",
    "CaptureDeclaration",
    "ContextIdentity",
    "InterpretationContract",
    "LoadedAtlasPreparationDescriptor",
    "ModelIdentity",
    "ProtocolIdentity",
    "ProvenanceEscalationError",
    "ProvenanceTaint",
    "QuarantineDisposition",
    "RowDomainIdentity",
    "load_atlas_preparation_descriptor",
    "prepare_descriptor_only_view",
    "require_atlas_consumer",
    "restrict_atlas_access",
    "write_atlas_preparation_descriptor",
]


def test_curated_public_export_snapshots_are_exact() -> None:
    assert spirallens.__all__ == ["__version__"]
    assert core.__all__ == EXPECTED_CORE_EXPORTS
    assert access.__all__ == EXPECTED_ACCESS_EXPORTS


def test_legacy_canonical_module_is_an_identity_preserving_reexport() -> None:
    for name in EXPECTED_CORE_EXPORTS:
        assert getattr(legacy_canonical, name) is getattr(core_canonical, name)


def test_access_import_is_framework_neutral_in_fresh_process() -> None:
    source_root = Path(__file__).resolve().parents[1] / "src"
    probe = f"""
import json
import sys
sys.path.insert(0, {str(source_root)!r})
import spirallens.access
forbidden = ["faiss", "huggingface_hub", "safetensors", "torch", "transformers"]
print(json.dumps(sorted(name for name in forbidden if name in sys.modules)))
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-c", probe],
        cwd=source_root.parent,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == []


def test_pr5_frozen_engineering_artifact_bytes_are_unchanged() -> None:
    repository = Path(__file__).resolve().parents[1]
    expected = {
        (
            repository / "protocols" / "pythia70_public_example_plumbing_v0_1.yaml"
        ): "ef93891c7450ef13cc2c5da54bf1a80d4a0b679df2df04964f2cc505e00aaf4c",
        (
            repository
            / "experiments"
            / "pythia"
            / "receipts"
            / "pythia70_public_example_plumbing_v0_1.json"
        ): "4ab51c1e01992dc63f9bea18a7f53e00293a0ec11617f4970abf2a400723ce82",
    }

    assert {
        path: hashlib.sha256(path.read_bytes()).hexdigest() for path in expected
    } == expected
