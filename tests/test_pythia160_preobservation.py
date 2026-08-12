from __future__ import annotations

import ast
from collections.abc import Iterator, Mapping
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

import spirallens.access as access
from spirallens.access import _pythia160_preobservation as preobservation
from spirallens.access._pythia160_preobservation import (
    _Pythia160PreobservationAssessment,
    _Pythia160PreobservationContractError,
    _Pythia160PreobservationDeclaration,
    _assess_pythia160_preobservation_declaration,
)
from spirallens.atlas import engineering_protocol


ROOT = Path(__file__).resolve().parents[1]


def _declaration_document() -> dict[str, object]:
    return {
        "schema_version": ("spirallens.pythia160-preobservation-declaration.v0.1"),
        "declaration_id": "pythia160-source-only-test-001",
        "model": {
            "model_id": "EleutherAI/pythia-160m",
            "revision": "1" * 40,
            "identity_status": "declared_unverified",
            "architecture": "test-only-unverified-architecture-declaration",
            "architecture_status": "declared_unverified",
            "files": [
                {
                    "role": "config",
                    "name": "test-only-declared-config-entry",
                    "sha256": "2" * 64,
                    "byte_count": 100,
                },
                {
                    "role": "weights",
                    "name": "test-only-declared-weights-entry",
                    "sha256": "3" * 64,
                    "byte_count": 1000,
                },
            ],
            "files_status": "declared_unverified",
            "profile": {
                "num_layers": 3,
                "hidden_size": 16,
                "vocab_size": 100,
                "num_attention_heads": 2,
                "intermediate_size": 32,
                "max_position_embeddings": 64,
                "parameter_count": 1000,
                "parameter_tensor_count": 10,
                "status": "declared_unverified",
            },
        },
        "capture": {
            "implementation_version": "spirallens.pythia.residual_hooks.v1",
            "device": "cpu",
            "dtype": "float32",
            "observation_contract": "all_residual_pre_post_layers",
            "batch_size": 2,
            "context_tokens": 8,
            "row_count": 5,
            "hook_parity_status": "not_run",
            "zero_intervention_status": "not_run",
        },
        "resource_plan": {
            "estimator_id": "pythia-preobservation-static-estimate-v0.1",
            "safety_factor": 2,
            "max_estimated_output_bytes": 4480,
            "max_estimated_peak_bytes": 16_748,
        },
    }


def _set_path(
    document: dict[str, object], path: tuple[object, ...], value: object
) -> None:
    target: object = document
    for segment in path[:-1]:
        if isinstance(segment, int):
            assert isinstance(target, list)
            target = target[segment]
        else:
            assert isinstance(target, dict)
            target = target[segment]
    final = path[-1]
    if isinstance(final, int):
        assert isinstance(target, list)
        target[final] = value
    else:
        assert isinstance(target, dict)
        target[final] = value


def test_exact_declaration_assessment_roundtrip_and_static_oracle() -> None:
    document = _declaration_document()
    declaration = _Pythia160PreobservationDeclaration.from_dict(document)
    assessment = _assess_pythia160_preobservation_declaration(declaration)

    assert declaration.to_dict() == document
    assert (
        _Pythia160PreobservationDeclaration.from_dict(declaration.to_dict())
        == declaration
    )
    assert (
        _Pythia160PreobservationAssessment.from_dict(assessment.to_dict()) == assessment
    )
    assert hashlib.sha256(declaration.canonical_bytes).hexdigest() == (
        declaration.canonical_sha256
    )
    assert hashlib.sha256(assessment.canonical_bytes).hexdigest() == (
        assessment.canonical_sha256
    )
    assert (len(declaration.canonical_bytes), declaration.canonical_sha256) == (
        1384,
        "02a668e491126f9e826c636ca00ec9906da4826322fd38c76e56c889921f0438",
    )
    assert (len(assessment.canonical_bytes), assessment.canonical_sha256) == (
        4600,
        "eb0b407237c42cf24cae6098c71fc37fe79607263d1d15b609548803e0cc68d6",
    )

    expected_row_bytes = 8 + 2 * 3 * 16 * 4 + 3 * 2 * 4 + 6 * 4 + 8
    expected_output = 5 * expected_row_bytes * 2
    expected_working = 2 * (8 * 100 * 4 + 2 * 3 * 16 * 4)
    expected_peak = 1100 + 1000 * 4 + expected_working + expected_output
    assert dict(assessment.static_estimate) == {
        "estimator_id": "pythia-preobservation-static-estimate-v0.1",
        "dtype_bytes": 4,
        "declared_model_file_bytes": 1100,
        "declared_parameter_bytes": 4000,
        "declared_row_bytes": expected_row_bytes,
        "estimated_output_bytes": expected_output,
        "estimated_working_bytes": expected_working,
        "estimated_peak_bytes": expected_peak,
        "max_estimated_output_bytes": expected_output,
        "max_estimated_peak_bytes": expected_peak,
        "physical_memory_observed": False,
        "free_disk_observed": False,
        "oom_safety_proved": False,
    }
    assert assessment.status == "blocked_external_prerequisites"
    assert assessment.declaration_canonical_sha256 == declaration.canonical_sha256
    assert assessment.blocking_prerequisites == tuple(
        sorted(assessment.blocking_prerequisites)
    )
    assert all(value is False for value in assessment.access.values())
    assert all(value is False for value in assessment.verification.values())
    assert all(value is False for value in assessment.authority.values())
    assert assessment.claim_boundary == {
        "claim_ceiling": "level_0",
        "claim_delta": "none",
        "declaration_inputs_verified": False,
        "execution_readiness_established": False,
        "persistence_supported": False,
        "public_schema_supported": False,
        "record_scope": "in_memory_fingerprint_only",
        "resource_sufficiency_established": False,
        "sci_s1_satisfied": False,
        "sci_s2_unblocked": False,
        "scientific_result_produced": False,
    }


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("schema_version",), "spirallens.pythia160.v9"),
        (("declaration_id",), "Not Canonical"),
        (("model", "model_id"), "EleutherAI/pythia-70m"),
        (("model", "revision"), "main"),
        (("model", "revision"), "A" * 40),
        (("model", "identity_status"), "verified"),
        (("model", "architecture"), ""),
        (("model", "architecture_status"), "verified"),
        (("model", "files_status"), "verified"),
        (("model", "files", 0, "sha256"), "z" * 64),
        (("model", "files", 0, "byte_count"), True),
        (("model", "profile", "num_layers"), 0),
        (("model", "profile", "hidden_size"), 1.0),
        (("model", "profile", "parameter_count"), True),
        (("model", "profile", "status"), "verified"),
        (("capture", "implementation_version"), "unknown"),
        (("capture", "device"), "mps"),
        (("capture", "dtype"), "float16"),
        (("capture", "observation_contract"), "post_only"),
        (("capture", "batch_size"), False),
        (("capture", "hook_parity_status"), "pass"),
        (("capture", "zero_intervention_status"), "pass"),
        (("resource_plan", "estimator_id"), "unknown"),
        (("resource_plan", "safety_factor"), True),
    ],
)
def test_invalid_constants_types_and_unverified_statuses_fail_closed(
    path: tuple[object, ...], value: object
) -> None:
    document = _declaration_document()
    _set_path(document, path, value)
    with pytest.raises(_Pythia160PreobservationContractError):
        _Pythia160PreobservationDeclaration.from_dict(document)


@pytest.mark.parametrize(
    "mutation",
    [
        "root_extra",
        "root_missing",
        "model_extra",
        "file_extra",
        "profile_extra",
        "capture_extra",
        "resource_extra",
    ],
)
def test_every_mapping_has_an_exact_keyset(mutation: str) -> None:
    document = _declaration_document()
    if mutation == "root_extra":
        document["extra"] = False
    elif mutation == "root_missing":
        del document["declaration_id"]
    elif mutation == "model_extra":
        document["model"]["extra"] = False  # type: ignore[index]
    elif mutation == "file_extra":
        document["model"]["files"][0]["extra"] = False  # type: ignore[index]
    elif mutation == "profile_extra":
        document["model"]["profile"]["extra"] = False  # type: ignore[index]
    elif mutation == "capture_extra":
        document["capture"]["extra"] = False  # type: ignore[index]
    else:
        document["resource_plan"]["extra"] = False  # type: ignore[index]
    with pytest.raises(
        _Pythia160PreobservationContractError,
        match="(?:field count|fields) differ",
    ):
        _Pythia160PreobservationDeclaration.from_dict(document)


@pytest.mark.parametrize(
    "mutation",
    [
        "empty_files",
        "files_not_list",
        "missing_config",
        "duplicate_config",
        "missing_weights",
        "unsorted",
        "duplicate_identity",
        "duplicate_name",
        "context_overflow",
        "output_budget_underflow",
        "peak_budget_underflow",
        "integer_above_bound",
    ],
)
def test_file_shape_context_and_static_budgets_fail_closed(mutation: str) -> None:
    document = _declaration_document()
    model = document["model"]
    assert isinstance(model, dict)
    files = model["files"]
    assert isinstance(files, list)
    if mutation == "empty_files":
        model["files"] = []
    elif mutation == "files_not_list":
        model["files"] = tuple(files)
    elif mutation == "missing_config":
        files.pop(0)
    elif mutation == "duplicate_config":
        duplicate = deepcopy(files[0])
        duplicate["name"] = "test-only-second-config"
        files.insert(1, duplicate)
    elif mutation == "missing_weights":
        files.pop(1)
    elif mutation == "unsorted":
        files.reverse()
    elif mutation == "duplicate_identity":
        files.append(deepcopy(files[1]))
    elif mutation == "duplicate_name":
        auxiliary = deepcopy(files[1])
        auxiliary["role"] = "auxiliary"
        files.insert(0, auxiliary)
    elif mutation == "context_overflow":
        document["capture"]["context_tokens"] = 65  # type: ignore[index]
    elif mutation == "output_budget_underflow":
        document["resource_plan"]["max_estimated_output_bytes"] = 4479  # type: ignore[index]
    elif mutation == "peak_budget_underflow":
        document["resource_plan"]["max_estimated_peak_bytes"] = 16_747  # type: ignore[index]
    else:
        model["profile"]["parameter_count"] = 1 << 63  # type: ignore[index]
    with pytest.raises(_Pythia160PreobservationContractError):
        _Pythia160PreobservationDeclaration.from_dict(document)


def test_assessment_rederivation_rejects_every_boundary_tamper() -> None:
    declaration = _Pythia160PreobservationDeclaration.from_dict(_declaration_document())
    assessment = _assess_pythia160_preobservation_declaration(declaration)
    source = assessment.to_dict()

    root_tampers = {
        "schema_version": "spirallens.pythia160-preobservation-assessment.v9",
        "status": "ready",
        "declaration_canonical_sha256": "0" * 64,
    }
    for key, value in root_tampers.items():
        document = deepcopy(source)
        document[key] = value
        with pytest.raises(_Pythia160PreobservationContractError):
            _Pythia160PreobservationAssessment.from_dict(document)

    document = deepcopy(source)
    document["blocking_prerequisites"] = document["blocking_prerequisites"][:-1]
    with pytest.raises(_Pythia160PreobservationContractError):
        _Pythia160PreobservationAssessment.from_dict(document)

    for section in ("access", "verification", "authority"):
        section_document = source[section]
        assert isinstance(section_document, dict)
        for key in section_document:
            document = deepcopy(source)
            document[section][key] = True
            with pytest.raises(_Pythia160PreobservationContractError):
                _Pythia160PreobservationAssessment.from_dict(document)

    claim = source["claim_boundary"]
    assert isinstance(claim, dict)
    for key, original in claim.items():
        document = deepcopy(source)
        document["claim_boundary"][key] = True if original is False else "tampered"
        with pytest.raises(_Pythia160PreobservationContractError):
            _Pythia160PreobservationAssessment.from_dict(document)

    estimate = source["static_estimate"]
    assert isinstance(estimate, dict)
    for key, original in estimate.items():
        document = deepcopy(source)
        if original is False:
            document["static_estimate"][key] = True
        elif isinstance(original, int):
            document["static_estimate"][key] = original + 1
        else:
            document["static_estimate"][key] = "tampered"
        with pytest.raises(_Pythia160PreobservationContractError):
            _Pythia160PreobservationAssessment.from_dict(document)


def test_frozen_records_and_direct_constructor_boundary_cannot_be_forged() -> None:
    declaration = _Pythia160PreobservationDeclaration.from_dict(_declaration_document())
    assessment = _assess_pythia160_preobservation_declaration(declaration)
    with pytest.raises(FrozenInstanceError):
        declaration.declaration_id = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        assessment.authority["scientific_claim_eligible"] = True  # type: ignore[index]

    for field in ("access", "verification", "authority", "claim_boundary"):
        tampered = dict(getattr(assessment, field))
        false_key = next(key for key, value in tampered.items() if value is False)
        tampered[false_key] = 0
        with pytest.raises(_Pythia160PreobservationContractError):
            replace(assessment, **{field: tampered})
    tampered_estimate = dict(assessment.static_estimate)
    tampered_estimate["physical_memory_observed"] = 0
    with pytest.raises(_Pythia160PreobservationContractError):
        replace(assessment, static_estimate=tampered_estimate)

    owned = {
        field: dict(getattr(assessment, field))
        for field in (
            "static_estimate",
            "access",
            "verification",
            "authority",
            "claim_boundary",
        )
    }
    snapshotted = replace(assessment, **owned)
    stable_bytes = snapshotted.canonical_bytes
    for field, mapping in owned.items():
        key = next(iter(mapping))
        mapping[key] = "caller-mutation"
        assert dict(getattr(snapshotted, field))[key] != "caller-mutation"
    assert snapshotted.canonical_bytes == stable_bytes


def test_custom_mapping_callbacks_are_rejected_without_iteration() -> None:
    class CallbackMapping(Mapping[str, object]):
        def __init__(self) -> None:
            self.iterated = False

        def __getitem__(self, key: str) -> object:
            raise AssertionError("custom mapping item access must not occur")

        def __iter__(self) -> Iterator[str]:
            self.iterated = True
            raise AssertionError("custom mapping iteration must not occur")

        def __len__(self) -> int:
            raise AssertionError("custom mapping length must not be read")

    document = CallbackMapping()
    with pytest.raises(
        _Pythia160PreobservationContractError, match="plain string-keyed dictionary"
    ):
        _Pythia160PreobservationDeclaration.from_dict(document)
    assert document.iterated is False

    declaration = _Pythia160PreobservationDeclaration.from_dict(_declaration_document())
    assessment = _assess_pythia160_preobservation_declaration(declaration)
    boundary = CallbackMapping()
    with pytest.raises(
        _Pythia160PreobservationContractError,
        match="plain dictionary",
    ):
        replace(assessment, authority=boundary)
    assert boundary.iterated is False

    proxied = preobservation.MappingProxyType(boundary)
    with pytest.raises(
        _Pythia160PreobservationContractError,
        match="plain dictionary",
    ):
        replace(assessment, authority=proxied)
    assert boundary.iterated is False


def test_file_count_bound_is_checked_before_entry_parsing() -> None:
    class ExplodingDict(dict[str, object]):
        def __getitem__(self, key: str) -> object:
            raise AssertionError("oversized file entries must not be parsed")

    document = _declaration_document()
    document["model"]["files"] = [  # type: ignore[index]
        ExplodingDict() for _ in range(1025)
    ]
    with pytest.raises(
        _Pythia160PreobservationContractError,
        match="bounded non-empty JSON array",
    ):
        _Pythia160PreobservationDeclaration.from_dict(document)


def test_string_subclass_keys_fail_before_custom_hash_reentry() -> None:
    class ReentrantString(str):
        calls = 0

        def __hash__(self) -> int:
            type(self).calls += 1
            return super().__hash__()

    key = ReentrantString("extra")
    document = _declaration_document()
    document[key] = False
    calls_before = ReentrantString.calls
    with pytest.raises(_Pythia160PreobservationContractError):
        _Pythia160PreobservationDeclaration.from_dict(document)
    assert ReentrantString.calls == calls_before


def test_private_module_is_inert_framework_neutral_and_not_exported() -> None:
    module_path = ROOT / "src/spirallens/access/_pythia160_preobservation.py"
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    } | {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert imports <= {
        "__future__",
        "collections",
        "dataclasses",
        "re",
        "types",
        "spirallens",
    }
    forbidden_tokens = {
        "pathlib",
        "subprocess",
        "socket",
        "requests",
        "urllib",
        "huggingface_hub",
        "transformers",
        "torch",
        "safetensors",
        "numpy",
        "importlib",
    }
    assert imports.isdisjoint(forbidden_tokens)
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"open", "exec", "eval", "compile", "__import__"}
        for node in ast.walk(tree)
    )
    assert not any(
        isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
        for node in tree.body
    )
    assert preobservation.__all__ == ()
    assert not any(
        token in name.lower()
        for name in vars(preobservation)
        if not name.startswith("__")
        for token in ("loader", "writer", "from_path", "to_path")
    )
    assert not any(
        isinstance(
            value,
            (
                _Pythia160PreobservationDeclaration,
                _Pythia160PreobservationAssessment,
            ),
        )
        for value in vars(preobservation).values()
    )
    assert not any("Pythia160" in name for name in access.__all__)
    assert "_pythia160_preobservation" not in (
        ROOT / "src/spirallens/cli.py"
    ).read_text(encoding="utf-8")
    assert "_pythia160_preobservation" not in (ROOT / "pyproject.toml").read_text(
        encoding="utf-8"
    )

    probe = """
import json, sys
import spirallens.access
forbidden = ['faiss','huggingface_hub','safetensors','torch','transformers']
print(json.dumps({
    'private_loaded': 'spirallens.access._pythia160_preobservation' in sys.modules,
    'forbidden': sorted(name for name in forbidden if name in sys.modules),
}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(ROOT / "src")},
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "private_loaded": False,
        "forbidden": [],
    }


def test_pythia70_registry_and_frozen_artifacts_remain_exact() -> None:
    assert set(engineering_protocol._ENGINEERING_MODEL_PROFILES_BY_ID) == {
        "EleutherAI/pythia-70m"
    }
    with pytest.raises(engineering_protocol._UnsupportedEngineeringModelProfileError):
        engineering_protocol._require_engineering_model_profile(
            "EleutherAI/pythia-160m"
        )

    expected = {
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


def test_current_documentation_keeps_the_160m_boundary_closed() -> None:
    roadmap = (ROOT / "docs/ROADMAP.md").read_text(encoding="utf-8")
    access_boundary = (ROOT / "docs/ACCESS_BOUNDARY.md").read_text(encoding="utf-8")
    changelog = (ROOT / "docs/SCHEMA_CHANGELOG.md").read_text(encoding="utf-8")
    assert "**Status:** blocked on `SCI-S1` by design." in roadmap
    assert "`blocked_external_prerequisites`" in roadmap
    assert "cannot satisfy or transition `SCI-S1`" in roadmap
    assert "does not register a\n160M engineering profile" in roadmap
    assert "Its only status is `blocked_external_prerequisites`" in access_boundary
    assert "neither the\ndescriptor-only prepare view" in access_boundary
    assert "private,\n  nonpersisted, and unsupported" in changelog
    assert "No network, Hugging Face" in changelog
    assert "no Pythia-160M run or subject preparation begins" in changelog
