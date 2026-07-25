from __future__ import annotations

import builtins
import copy
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

import spirallens.execution_freeze as execution_freeze_module
from spirallens.execution_freeze import (
    EXECUTION_FREEZE_SCHEMA_VERSION_V0_1,
    EXECUTION_FREEZE_SCHEMA_VERSION_V0_2,
    EXECUTION_FREEZE_SCHEMA_VERSION_V0_3,
    ValidatedExecutionFreeze,
    _CAPABILITY_TOKEN,
    _execution_runtime_fields,
    _load_protocol_document,
    _qualified_freeze_profile,
    _read_repo_regular_file,
    _validate_backend_qualification,
    _validate_candidate_protocol_lineage,
    _validate_git_index_records,
    _validate_neighbor_protocol_lineage,
    _validate_qualification_predecessor,
    _validate_v0_3_implementation_delta,
    current_worker_runtime_contract,
    distribution_content_sha256,
    validate_subject_audit_execution_freeze,
)
from spirallens.neighbors import canonical_json_sha256
from spirallens.neighbors.contracts import NeighborBackendDescriptor


def test_execution_freeze_rejects_untrusted_bytes_before_preflight(
    tmp_path: Path,
) -> None:
    source = b"schema_version: wrong\n"

    with pytest.raises(
        ValueError,
        match="out-of-band SHA-256",
    ):
        validate_subject_audit_execution_freeze(
            document={},
            source_bytes=source,
            source_path=tmp_path / "freeze.yaml",
            expected_sha256="0" * 64,
            manifest_path=tmp_path / "manifest.json",
            manifest_sha256="1" * 64,
            protocol_path=tmp_path / "protocol.yaml",
            protocol_sha256="2" * 64,
            candidate_protocol_path=tmp_path / "candidate.yaml",
            candidate_protocol_sha256="3" * 64,
            recall_gate_path=tmp_path / "gate.yaml",
            recall_gate_sha256="4" * 64,
            output_path=tmp_path / "audit.json",
            layer_index=0,
            comparison_group="layer_index=0",
            global_row_key_sha256="5" * 64,
            query_selection_sha256="6" * 64,
            audit_config_sha256="7" * 64,
            query_count=1,
            query_seed=1,
        )


def test_runtime_distribution_digest_is_content_addressed() -> None:
    digest = distribution_content_sha256("faiss-cpu")

    assert len(digest) == 64
    assert set(digest) <= set("0123456789abcdef")


def test_worker_runtime_contract_probes_fresh_reporter_without_parent_faiss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "faiss" or name.startswith("faiss."):
            raise AssertionError("parent process attempted to import Faiss")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    runtime = current_worker_runtime_contract(None)

    assert runtime["faiss_version"]
    assert len(runtime["faiss_runtime_worker_source_sha256"]) == 64
    assert "execution_freeze_sha256" not in runtime


def test_protocol_lineage_allows_only_reviewed_freeze_delta() -> None:
    root = Path(__file__).resolve().parents[1]
    candidate_path = (
        root
        / "protocols"
        / "pythia70_slot_only_001_layer0_candidate_v0_2.yaml"
    )
    frozen_candidate = _load_protocol_document(
        candidate_path,
        label="frozen candidate",
    )
    _validate_candidate_protocol_lineage(
        parent=_load_protocol_document(
            root / "protocols" / "pythia_candidate_v0_2.yaml",
            label="candidate parent",
        ),
        frozen=frozen_candidate,
        layer_index=0,
    )
    _validate_neighbor_protocol_lineage(
        parent=_load_protocol_document(
            root / "protocols" / "pythia_neighbor_v0_2.yaml",
            label="neighbor parent",
        ),
        frozen=_load_protocol_document(
            root
            / "protocols"
            / "pythia70_slot_only_001_layer0_neighbor_v0_2.yaml",
            label="frozen neighbor",
        ),
        repo_root=root,
        candidate_protocol_path=candidate_path,
        candidate_protocol_sha256=(
            "d6f60d38237825178f4d7c799e27da370049787d47ca999172121f07c84d212e"
        ),
        comparison_group="layer_index=0",
        global_row_key_sha256=(
            "d39cd127bd50f564a8ea13e080f19806a3ce390b9ed4436b49d2701054409c43"
        ),
    )

    forged_candidate = copy.deepcopy(frozen_candidate)
    forged_candidate["claim_ceiling"] = 2
    with pytest.raises(ValueError, match="allowlisted lineage"):
        _validate_candidate_protocol_lineage(
            parent=_load_protocol_document(
                root / "protocols" / "pythia_candidate_v0_2.yaml",
                label="candidate parent",
            ),
            frozen=forged_candidate,
            layer_index=0,
        )


def test_execution_freeze_schema_dispatch_preserves_v0_2_and_adds_v0_3() -> None:
    assert EXECUTION_FREEZE_SCHEMA_VERSION_V0_1 == (
        "spirallens.subject-audit-freeze.v0.1"
    )
    assert EXECUTION_FREEZE_SCHEMA_VERSION_V0_2 == (
        "spirallens.subject-audit-freeze.v0.2"
    )
    assert EXECUTION_FREEZE_SCHEMA_VERSION_V0_3 == (
        "spirallens.subject-audit-freeze.v0.3"
    )
    v0_2 = _qualified_freeze_profile(
        EXECUTION_FREEZE_SCHEMA_VERSION_V0_2
    )
    v0_3 = _qualified_freeze_profile(
        EXECUTION_FREEZE_SCHEMA_VERSION_V0_3
    )
    assert v0_2 is not None
    assert v0_3 is not None
    assert v0_2["neighbor_parent_filename"] == "pythia_neighbor_v0_3.yaml"
    assert v0_2["qualification_schema_version"].endswith(".v0.1")
    assert v0_2["qualification_relative_path"] == ""
    assert v0_2["output_filename"] == "layer-0-neighbor-audit-v0-3.json"
    assert v0_3["neighbor_parent_filename"] == "pythia_neighbor_v0_4.yaml"
    assert v0_3["qualification_schema_version"].endswith(".v0.2")
    assert v0_3["qualification_relative_path"].endswith(
        "_qualification_v0_2.json"
    )
    assert v0_3["output_filename"] == "layer-0-neighbor-audit-v0-4.json"
    reporter_field = "faiss_runtime_worker_source_sha256"
    assert reporter_field not in _execution_runtime_fields(
        EXECUTION_FREEZE_SCHEMA_VERSION_V0_1
    )
    assert reporter_field not in _execution_runtime_fields(
        EXECUTION_FREEZE_SCHEMA_VERSION_V0_2
    )
    assert reporter_field in _execution_runtime_fields(
        EXECUTION_FREEZE_SCHEMA_VERSION_V0_3
    )


def test_repo_regular_file_rejects_symlink_indirection(
    tmp_path: Path,
) -> None:
    receipt = tmp_path / "receipt.json"
    receipt.write_bytes(b"receipt")
    assert _read_repo_regular_file(
        receipt,
        repo_root=tmp_path,
        label="receipt",
    ) == (b"receipt", "receipt.json")

    alias = tmp_path / "alias.json"
    alias.symlink_to(receipt)
    with pytest.raises(ValueError, match="symlinks"):
        _read_repo_regular_file(
            alias,
            repo_root=tmp_path,
            label="receipt",
        )


@pytest.mark.parametrize("tag", [b"h hidden.py", b"S sparse.py"])
def test_execution_freeze_rejects_hidden_git_index_flags(
    tag: bytes,
) -> None:
    with pytest.raises(
        ValueError,
        match="assume-unchanged or skip-worktree",
    ):
        _validate_git_index_records([b"H visible.py", tag])

    _validate_git_index_records([b"H visible.py"])


def test_validated_freeze_binds_qualified_backend_parameters() -> None:
    runtime = {"faiss_native_sha256": "a" * 64}
    capability = ValidatedExecutionFreeze(
        token=_CAPABILITY_TOKEN,
        sha256="b" * 64,
        revalidate=lambda: None,
        worker_runtime=runtime,
        backend_contract={
            "backend_id": "spirallens.faiss-hnsw-range",
            "backend_version": "0.2",
            "parameters": {
                "range_call_batch_size": 1,
                "max_native_call_hits": 50_304,
            },
        },
    )
    descriptor = NeighborBackendDescriptor(
        backend_id="spirallens.faiss-hnsw-range",
        backend_version="0.2",
        kind="approximate",
        deterministic=True,
        parameters=(
            ("max_native_call_hits", 50_304),
            ("range_call_batch_size", 1),
        ),
        runtime=tuple(runtime.items()),
    )
    capability.validate_subject_backend(descriptor)

    forged = NeighborBackendDescriptor(
        backend_id=descriptor.backend_id,
        backend_version=descriptor.backend_version,
        kind=descriptor.kind,
        deterministic=descriptor.deterministic,
        parameters=(
            ("max_native_call_hits", 50_304),
            ("range_call_batch_size", 2),
        ),
        runtime=descriptor.runtime,
    )
    with pytest.raises(ValueError, match="qualified execution freeze"):
        capability.validate_subject_backend(forged)


def test_v0_3_neighbor_lineage_binds_qualification() -> None:
    root = Path(__file__).resolve().parents[1]
    parent = _load_protocol_document(
        root / "protocols" / "pythia_neighbor_v0_3.yaml",
        label="qualified neighbor parent",
    )
    candidate_path = (
        root
        / "protocols"
        / "pythia70_slot_only_001_layer0_candidate_v0_2.yaml"
    )
    qualification_path = root / "protocols" / "qualification.json"
    frozen = copy.deepcopy(parent)
    frozen["protocol_id"] = (
        "pythia70-slot-only-001-layer0-neighbor-v0.3"
    )
    frozen["status"] = "frozen"
    frozen["audit_scope"] = {"comparison_group": "layer_index=0"}
    frozen["candidate_protocol"] = {
        "path": str(candidate_path.relative_to(root)),
        "sha256": (
            "d6f60d38237825178f4d7c799e27da370049787d47ca999172121f07c84d212e"
        ),
        "declared_id": (
            "pythia70-slot-only-001-layer0-candidate-v0.2"
        ),
    }
    frozen["backend_qualification"] = {
        "schema_version": (
            "spirallens.faiss-hnsw-range-qualification.v0.1"
        ),
        "path": str(qualification_path.relative_to(root)),
        "sha256": "a" * 64,
        "fixture_sha256": "b" * 64,
    }
    sampling = frozen["query_sampling"]
    sampling["global_row_key_sha256"] = "c" * 64
    sampling.pop("binding_rule")
    frozen["audit"][
        "issue_persistence_receipt_on_verified_pass"
    ] = True
    readiness = frozen["promotion_readiness"]
    readiness["production_shape_subprocess_qualified"] = True
    readiness["atlas_execution_bindings_frozen"] = True
    readiness["tracked_protocol_can_issue_persistence_receipt"] = True

    _validate_neighbor_protocol_lineage(
        parent=parent,
        frozen=frozen,
        repo_root=root,
        candidate_protocol_path=candidate_path,
        candidate_protocol_sha256=(
            "d6f60d38237825178f4d7c799e27da370049787d47ca999172121f07c84d212e"
        ),
        comparison_group="layer_index=0",
        global_row_key_sha256="c" * 64,
        qualification_path=qualification_path,
        qualification_sha256="a" * 64,
        qualification_fixture_sha256="b" * 64,
    )

    frozen["subject_backend"]["config"]["range_call_batch_size"] = 2
    with pytest.raises(ValueError, match="allowlisted lineage"):
        _validate_neighbor_protocol_lineage(
            parent=parent,
            frozen=frozen,
            repo_root=root,
            candidate_protocol_path=candidate_path,
            candidate_protocol_sha256=(
                "d6f60d38237825178f4d7c799e27da370049787d47ca999172121f07c84d212e"
            ),
            comparison_group="layer_index=0",
            global_row_key_sha256="c" * 64,
            qualification_path=qualification_path,
            qualification_sha256="a" * 64,
            qualification_fixture_sha256="b" * 64,
        )


def test_v0_4_neighbor_lineage_requires_v0_2_qualification() -> None:
    root = Path(__file__).resolve().parents[1]
    parent = _load_protocol_document(
        root / "protocols" / "pythia_neighbor_v0_4.yaml",
        label="v0.4 qualified neighbor parent",
    )
    candidate_path = (
        root
        / "protocols"
        / "pythia70_slot_only_001_layer0_candidate_v0_2.yaml"
    )
    qualification_path = (
        root
        / "protocols"
        / "pythia70_slot_only_001_layer0_"
        "faiss_range_qualification_v0_2.json"
    )
    frozen = copy.deepcopy(parent)
    frozen["protocol_id"] = (
        "pythia70-slot-only-001-layer0-neighbor-v0.4"
    )
    frozen["status"] = "frozen"
    frozen["audit_scope"] = {"comparison_group": "layer_index=0"}
    frozen["candidate_protocol"] = {
        "path": str(candidate_path.relative_to(root)),
        "sha256": (
            "d6f60d38237825178f4d7c799e27da370049787d47ca999172121f07c84d212e"
        ),
        "declared_id": (
            "pythia70-slot-only-001-layer0-candidate-v0.2"
        ),
    }
    frozen["backend_qualification"] = {
        "schema_version": (
            "spirallens.faiss-hnsw-range-qualification.v0.2"
        ),
        "path": str(qualification_path.relative_to(root)),
        "sha256": "a" * 64,
        "fixture_sha256": "b" * 64,
    }
    sampling = frozen["query_sampling"]
    sampling["global_row_key_sha256"] = "c" * 64
    sampling.pop("binding_rule")
    frozen["audit"][
        "issue_persistence_receipt_on_verified_pass"
    ] = True
    readiness = frozen["promotion_readiness"]
    readiness["production_shape_subprocess_qualified"] = True
    readiness["atlas_execution_bindings_frozen"] = True
    readiness["tracked_protocol_can_issue_persistence_receipt"] = True

    arguments = {
        "parent": parent,
        "frozen": frozen,
        "repo_root": root,
        "candidate_protocol_path": candidate_path,
        "candidate_protocol_sha256": (
            "d6f60d38237825178f4d7c799e27da370049787d47ca999172121f07c84d212e"
        ),
        "comparison_group": "layer_index=0",
        "global_row_key_sha256": "c" * 64,
        "qualification_path": qualification_path,
        "qualification_sha256": "a" * 64,
        "qualification_fixture_sha256": "b" * 64,
    }
    _validate_neighbor_protocol_lineage(**arguments)

    frozen["backend_qualification"]["schema_version"] = (
        "spirallens.faiss-hnsw-range-qualification.v0.1"
    )
    with pytest.raises(ValueError, match="allowlisted lineage"):
        _validate_neighbor_protocol_lineage(**arguments)


def test_qualification_predecessor_binds_observation_without_artifact_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = Path(__file__).resolve().parents[1]
    observation_relative = (
        "protocols/"
        "pythia70_slot_only_001_layer0_faiss_range_qualification_"
        "v0_1_observation.yaml"
    )
    observation_bytes = (root / observation_relative).read_bytes()
    observation_path = tmp_path / observation_relative
    observation_path.parent.mkdir()
    observation_path.write_bytes(observation_bytes)
    observation_sha256 = hashlib.sha256(observation_bytes).hexdigest()
    active_receipt = (
        tmp_path
        / "protocols"
        / "pythia70_slot_only_001_layer0_"
        "faiss_range_qualification_v0_2.json"
    )
    active_receipt_sha256 = "a" * 64
    active_preflight_commit = "b" * 40
    active_preflight_tree = "c" * 40
    implementation_commit = "d" * 40
    observed_commit = "dca11d116c2d5218d586bb5d089460d28e59e7d8"
    observed_tree = "d7003c09037cb34b9147a2992a4ae74c88f2e907"
    repository = "https://github.com/RyoSpiralArchitect/SpiralLens.git"
    branch = "SpiralReality/pythia70-subject-audit-v03"
    binding = {
        "schema_version": (
            "spirallens.subject-audit-qualification-predecessor.v0.1"
        ),
        "observation_path": str(observation_path),
        "observation_sha256": observation_sha256,
        "artifact_available": False,
        "raw_receipt_bytes_preserved": False,
        "record_is_original_receipt": False,
        "observed_receipt_schema_version": (
            "spirallens.faiss-hnsw-range-qualification.v0.1"
        ),
        "observed_receipt_sha256": (
            "572bed090750a314d4415eeaaef3c2f96662a08442437616c9dc85823c2b33cb"
        ),
        "observed_source_implementation_commit": observed_commit,
        "observed_source_package_tree": observed_tree,
        "producer_status": "pass",
        "consumer_binding_status": "unbound_before_subject_audit",
        "failure_stage": "prepare_only_consumer_validation",
        "subject_audit_runs_observed": 0,
        "subject_outcome_observed": False,
        "audit_artifact_written": False,
        "promotion_receipt_issued": False,
        "active_binding_allowed": False,
        "successor_schema_version": (
            "spirallens.faiss-hnsw-range-qualification.v0.2"
        ),
        "successor_path": str(active_receipt),
        "successor_sha256": active_receipt_sha256,
    }

    def fake_git_bytes(*args, **kwargs):
        del kwargs
        if "cat-file" in args:
            return (
                b"tree " + (b"e" * 40) + b"\nparent "
                + observed_commit.encode("ascii")
                + b"\nauthor test\n\nmessage\n"
            )
        if "show" in args:
            return observation_bytes
        raise AssertionError(f"unexpected Git bytes call: {args}")

    def fake_git_output(*args, **kwargs):
        del kwargs
        if "rev-parse" in args:
            return observed_tree
        if "ls-tree" in args:
            return ""
        raise AssertionError(f"unexpected Git output call: {args}")

    monkeypatch.setattr(
        execution_freeze_module,
        "_git_bytes",
        fake_git_bytes,
    )
    monkeypatch.setattr(
        execution_freeze_module,
        "_git_output",
        fake_git_output,
    )
    arguments = {
        "repo_root": tmp_path,
        "git_executable": Path("/usr/bin/git"),
        "repository": repository,
        "branch": branch,
        "active_preflight_commit": active_preflight_commit,
        "active_preflight_tree": active_preflight_tree,
        "implementation_commit": implementation_commit,
        "active_receipt_path": active_receipt,
        "active_receipt_sha256": active_receipt_sha256,
    }
    _validate_qualification_predecessor(binding, **arguments)

    forged = dict(binding)
    forged["active_binding_allowed"] = True
    with pytest.raises(ValueError, match="artifact boundary"):
        _validate_qualification_predecessor(forged, **arguments)

    def wrong_parent_git_bytes(*args, **kwargs):
        del kwargs
        if "cat-file" in args:
            return (
                b"tree " + (b"e" * 40) + b"\nparent "
                + (b"f" * 40)
                + b"\nauthor test\n\nmessage\n"
            )
        return observation_bytes

    monkeypatch.setattr(
        execution_freeze_module,
        "_git_bytes",
        wrong_parent_git_bytes,
    )
    with pytest.raises(ValueError, match="Git lineage"):
        _validate_qualification_predecessor(binding, **arguments)


def test_v0_3_implementation_delta_allows_only_receipt_and_protocol(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    qualification_path = (
        tmp_path / "protocols" / "qualification-v0-2.json"
    )
    frozen_protocol_path = tmp_path / "protocols" / "neighbor-v0-4.yaml"
    expected = "\n".join(
        [
            "protocols/neighbor-v0-4.yaml",
            "protocols/qualification-v0-2.json",
        ]
    )
    monkeypatch.setattr(
        execution_freeze_module,
        "_git_output",
        lambda *args, **kwargs: expected,
    )
    arguments = {
        "repo_root": tmp_path,
        "git_executable": Path("/usr/bin/git"),
        "preflight_commit": "a" * 40,
        "implementation_commit": "b" * 40,
        "qualification_path": qualification_path,
        "frozen_protocol_path": frozen_protocol_path,
    }
    _validate_v0_3_implementation_delta(**arguments)

    monkeypatch.setattr(
        execution_freeze_module,
        "_git_output",
        lambda *args, **kwargs: expected + "\nsrc/spirallens/forged.py",
    )
    with pytest.raises(ValueError, match="receipt/protocol allowlist"):
        _validate_v0_3_implementation_delta(**arguments)


def test_backend_qualification_cross_binds_freeze_protocol_and_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt_path = tmp_path / "protocols" / "qualification.json"
    receipt_path.parent.mkdir()
    receipt_bytes = b"canonical qualification receipt"
    receipt_path.write_bytes(receipt_bytes)
    receipt_sha256 = hashlib.sha256(receipt_bytes).hexdigest()
    fixture_sha256 = "f" * 64
    native_sha256 = "e" * 64
    implementation_commit = "1" * 40
    implementation_package_tree = "2" * 40
    preflight_commit = "0" * 40
    repository = "https://example.test/SpiralLens.git"
    branch = "SpiralReality/pythia70-subject-audit-v03"
    subject_config = {
        "m": 32,
        "ef_construction": 200,
        "ef_search": 256,
        "seed": 1729,
        "thread_count": 1,
        "query_batch_size": 512,
        "range_call_batch_size": 1,
        "score_margin": 0.0001,
        "max_raw_hits": 20_000_000,
        "max_proposed_pairs": 10_000_000,
    }
    radius = float(
        execution_freeze_module.np.nextafter(
            execution_freeze_module.np.float32(0.995 - 0.0001),
            execution_freeze_module.np.float32(-execution_freeze_module.np.inf),
        )
    )
    search = {
        key: subject_config[key]
        for key in (
            "m",
            "ef_construction",
            "ef_search",
            "seed",
            "thread_count",
            "query_batch_size",
            "range_call_batch_size",
            "score_margin",
            "max_raw_hits",
        )
    }
    search.update(
        {
            "cosine_min": 0.995,
            "radius": radius,
            "max_native_call_hits": 50_304,
        }
    )
    fake_receipt = SimpleNamespace(
        sha256=receipt_sha256,
        fixture_sha256=fixture_sha256,
        search_sha256=canonical_json_sha256(search),
        status="pass",
        backend_id="spirallens.faiss-hnsw-range",
        backend_version="0.2",
        cold_process_runs=({}, {}),
        runtime={"faiss_native_sha256": native_sha256},
        source={
            "repository": repository,
            "branch": branch,
            "implementation_commit": preflight_commit,
            "spirallens_package_tree": implementation_package_tree,
        },
        implementation_commit=preflight_commit,
        spirallens_package_tree=implementation_package_tree,
        search=search,
        max_native_call_hits=50_304,
    )
    import spirallens.neighbors.faiss_qualification as qualification_module

    monkeypatch.setattr(
        qualification_module,
        "load_faiss_hnsw_qualification_receipt",
        lambda path, expected_sha256: fake_receipt,
    )
    def fake_git_bytes(*args, **kwargs):
        del kwargs
        if "cat-file" in args:
            return (
                b"tree " + (b"3" * 40) + b"\nparent "
                + preflight_commit.encode("ascii")
                + b"\nauthor test\n\nmessage\n"
            )
        return receipt_bytes

    monkeypatch.setattr(
        execution_freeze_module,
        "_git_bytes",
        fake_git_bytes,
    )
    monkeypatch.setattr(
        execution_freeze_module,
        "_git_output",
        lambda *args, **kwargs: implementation_package_tree,
    )
    frozen_neighbor = {
        "subject_backend": {
            "backend_id": "spirallens.faiss-hnsw-range",
            "backend_version": "0.2",
            "config": subject_config,
        },
        "backend_qualification": {
            "schema_version": (
                "spirallens.faiss-hnsw-range-qualification.v0.1"
            ),
            "path": "protocols/qualification.json",
            "sha256": receipt_sha256,
            "fixture_sha256": fixture_sha256,
        },
    }
    binding = {
        "schema_version": (
            "spirallens.faiss-hnsw-range-qualification.v0.1"
        ),
        "path": str(receipt_path),
        "sha256": receipt_sha256,
        "fixture_sha256": fixture_sha256,
        "subject_config_sha256": canonical_json_sha256(subject_config),
        "search_sha256": canonical_json_sha256(search),
        "faiss_native_sha256": native_sha256,
        "range_call_batch_size": 1,
        "cold_process_runs": 2,
        "preflight_commit": preflight_commit,
        "preflight_package_tree": implementation_package_tree,
    }
    result = _validate_backend_qualification(
        binding,
        repo_root=tmp_path,
        implementation_commit=implementation_commit,
        implementation_package_tree=implementation_package_tree,
        repository=repository,
        branch=branch,
        git_executable=Path("/usr/bin/git"),
        frozen_neighbor=frozen_neighbor,
        frozen_candidate={"candidate_search": {"cosine_min": 0.995}},
        runtime={"faiss_native_sha256": native_sha256},
        atlas_row_count=50_304,
    )
    assert result[0] == receipt_path
    assert result[3]["parameters"]["max_native_call_hits"] == 50_304

    v0_2_binding = dict(binding)
    v0_2_binding["schema_version"] = (
        "spirallens.faiss-hnsw-range-qualification.v0.2"
    )
    v0_2_neighbor = copy.deepcopy(frozen_neighbor)
    v0_2_neighbor["backend_qualification"]["schema_version"] = (
        "spirallens.faiss-hnsw-range-qualification.v0.2"
    )
    _validate_backend_qualification(
        v0_2_binding,
        repo_root=tmp_path,
        implementation_commit=implementation_commit,
        implementation_package_tree=implementation_package_tree,
        repository=repository,
        branch=branch,
        git_executable=Path("/usr/bin/git"),
        frozen_neighbor=v0_2_neighbor,
        frozen_candidate={"candidate_search": {"cosine_min": 0.995}},
        runtime={"faiss_native_sha256": native_sha256},
        atlas_row_count=50_304,
        expected_schema_version=(
            "spirallens.faiss-hnsw-range-qualification.v0.2"
        ),
        expected_relative_path="protocols/qualification.json",
    )
    with pytest.raises(ValueError, match="qualification path"):
        _validate_backend_qualification(
            v0_2_binding,
            repo_root=tmp_path,
            implementation_commit=implementation_commit,
            implementation_package_tree=implementation_package_tree,
            repository=repository,
            branch=branch,
            git_executable=Path("/usr/bin/git"),
            frozen_neighbor=v0_2_neighbor,
            frozen_candidate={
                "candidate_search": {"cosine_min": 0.995}
            },
            runtime={"faiss_native_sha256": native_sha256},
            atlas_row_count=50_304,
            expected_schema_version=(
                "spirallens.faiss-hnsw-range-qualification.v0.2"
            ),
            expected_relative_path=(
                "protocols/forged-qualification.json"
            ),
        )

    def merge_parent_git_bytes(*args, **kwargs):
        del kwargs
        if "cat-file" in args:
            return (
                b"tree " + (b"3" * 40) + b"\nparent "
                + preflight_commit.encode("ascii")
                + b"\nparent "
                + (b"4" * 40)
                + b"\nauthor test\n\nmessage\n"
            )
        return receipt_bytes

    monkeypatch.setattr(
        execution_freeze_module,
        "_git_bytes",
        merge_parent_git_bytes,
    )
    with pytest.raises(ValueError, match="receipt, protocol, runtime"):
        _validate_backend_qualification(
            binding,
            repo_root=tmp_path,
            implementation_commit=implementation_commit,
            implementation_package_tree=implementation_package_tree,
            repository=repository,
            branch=branch,
            git_executable=Path("/usr/bin/git"),
            frozen_neighbor=frozen_neighbor,
            frozen_candidate={
                "candidate_search": {"cosine_min": 0.995}
            },
            runtime={"faiss_native_sha256": native_sha256},
            atlas_row_count=50_304,
        )
    monkeypatch.setattr(
        execution_freeze_module,
        "_git_bytes",
        fake_git_bytes,
    )

    forged_tree = dict(binding)
    forged_tree["preflight_package_tree"] = "4" * 40
    with pytest.raises(ValueError, match="receipt, protocol, runtime"):
        _validate_backend_qualification(
            forged_tree,
            repo_root=tmp_path,
            implementation_commit=implementation_commit,
            implementation_package_tree=implementation_package_tree,
            repository=repository,
            branch=branch,
            git_executable=Path("/usr/bin/git"),
            frozen_neighbor=frozen_neighbor,
            frozen_candidate={
                "candidate_search": {"cosine_min": 0.995}
            },
            runtime={"faiss_native_sha256": native_sha256},
            atlas_row_count=50_304,
        )

    forged = dict(binding)
    forged["range_call_batch_size"] = 2
    with pytest.raises(ValueError, match="receipt, protocol, runtime"):
        _validate_backend_qualification(
            forged,
            repo_root=tmp_path,
            implementation_commit=implementation_commit,
            implementation_package_tree=implementation_package_tree,
            repository=repository,
            branch=branch,
            git_executable=Path("/usr/bin/git"),
            frozen_neighbor=frozen_neighbor,
            frozen_candidate={"candidate_search": {"cosine_min": 0.995}},
            runtime={"faiss_native_sha256": native_sha256},
            atlas_row_count=50_304,
        )
