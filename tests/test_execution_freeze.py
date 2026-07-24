from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

import spirallens.execution_freeze as execution_freeze_module
from spirallens.execution_freeze import (
    EXECUTION_FREEZE_SCHEMA_VERSION_V0_1,
    EXECUTION_FREEZE_SCHEMA_VERSION_V0_2,
    ValidatedExecutionFreeze,
    _CAPABILITY_TOKEN,
    _load_protocol_document,
    _read_repo_regular_file,
    _validate_backend_qualification,
    _validate_candidate_protocol_lineage,
    _validate_git_index_records,
    _validate_neighbor_protocol_lineage,
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


def test_execution_freeze_schema_dispatch_keeps_v0_1_and_adds_v0_2() -> None:
    assert EXECUTION_FREEZE_SCHEMA_VERSION_V0_1 == (
        "spirallens.subject-audit-freeze.v0.1"
    )
    assert EXECUTION_FREEZE_SCHEMA_VERSION_V0_2 == (
        "spirallens.subject-audit-freeze.v0.2"
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
