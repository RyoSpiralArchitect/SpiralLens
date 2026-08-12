from __future__ import annotations

import ast
from collections.abc import Callable, Iterator, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import errno
import importlib
import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
from unittest.mock import patch

import pytest

from spirallens._repository_context import RepositoryContext
from spirallens.core.canonical import sha256_bytes
from spirallens.qualification import confirmation_v1_materialization as materialization
from spirallens.qualification import (
    confirmation_v1_post_d6_descriptive as descriptive,
)
from spirallens.qualification import (
    confirmation_v1_private_publication as private_publication,
)
from spirallens.qualification import confirmation_v1_records as records
from spirallens.qualification import (
    confirmation_v1_source_selected_supplier as source_selected_supplier,
)
from spirallens.qualification.common import QualificationContractError


REPOSITORY = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    REPOSITORY
    / "src"
    / "spirallens"
    / "qualification"
    / "confirmation_v1_materialization.py"
)
RECORDS_MODULE_PATH = (
    REPOSITORY / "src" / "spirallens" / "qualification" / "confirmation_v1_records.py"
)
EXECUTION_DESIGN_REPOSITORY_PATH = (
    "src/spirallens/qualification/confirmation_execution_design.py"
)
EXECUTION_DESIGN_MODULE_PATH = REPOSITORY.joinpath(
    *EXECUTION_DESIGN_REPOSITORY_PATH.split("/")
)
DESCRIPTIVE_REPOSITORY_PATH = (
    "src/spirallens/qualification/confirmation_v1_post_d6_descriptive.py"
)
DESCRIPTIVE_MODULE_PATH = REPOSITORY.joinpath(*DESCRIPTIVE_REPOSITORY_PATH.split("/"))
DESCRIPTIVE_HELPER_REPOSITORY_PATHS = (
    "src/spirallens/qualification/confirmation_v1_descriptive_common.py",
    "src/spirallens/qualification/confirmation_v1_descriptive_d1.py",
    "src/spirallens/qualification/confirmation_v1_descriptive_d2.py",
    "src/spirallens/qualification/confirmation_v1_descriptive_d3.py",
    "src/spirallens/qualification/confirmation_v1_descriptive_d4.py",
    "src/spirallens/qualification/confirmation_v1_descriptive_d5_inputs.py",
    "src/spirallens/qualification/confirmation_v1_descriptive_d5_outputs.py",
    "src/spirallens/qualification/confirmation_v1_descriptive_independence.py",
)
DESCRIPTIVE_HELPER_MODULE_PATHS = tuple(
    REPOSITORY.joinpath(*repository_path.split("/"))
    for repository_path in DESCRIPTIVE_HELPER_REPOSITORY_PATHS
)
DESCRIPTIVE_HELPER_SOURCE_PATHS = dict(
    zip(
        DESCRIPTIVE_HELPER_REPOSITORY_PATHS,
        DESCRIPTIVE_HELPER_MODULE_PATHS,
        strict=True,
    )
)
PRIVATE_PUBLICATION_REPOSITORY_PATH = (
    "src/spirallens/qualification/confirmation_v1_private_publication.py"
)
PRIVATE_PUBLICATION_MODULE_PATH = REPOSITORY.joinpath(
    *PRIVATE_PUBLICATION_REPOSITORY_PATH.split("/")
)
RESULT_PUBLICATION_REPOSITORY_PATH = (
    "src/spirallens/qualification/confirmation_v1_result_publication.py"
)
RESULT_PUBLICATION_MODULE_PATH = REPOSITORY.joinpath(
    *RESULT_PUBLICATION_REPOSITORY_PATH.split("/")
)
SOURCE_CLOSURE_REPOSITORY_PATH = (
    "src/spirallens/qualification/confirmation_v1_source_closure.py"
)
SOURCE_CLOSURE_MODULE_PATH = REPOSITORY.joinpath(
    *SOURCE_CLOSURE_REPOSITORY_PATH.split("/")
)
SOURCE_SELECTED_SUPPLIER_REPOSITORY_PATH = (
    "src/spirallens/qualification/confirmation_v1_source_selected_supplier.py"
)
SOURCE_SELECTED_SUPPLIER_MODULE_PATH = REPOSITORY.joinpath(
    *SOURCE_SELECTED_SUPPLIER_REPOSITORY_PATH.split("/")
)
REPOSITORY_CONTEXT_REPOSITORY_PATH = "src/spirallens/_repository_context.py"
CANONICAL_REPOSITORY_PATH = "src/spirallens/core/canonical.py"
COMMON_REPOSITORY_PATH = "src/spirallens/qualification/common.py"
FOUNDATION_SOURCE_PATHS = {
    REPOSITORY_CONTEXT_REPOSITORY_PATH: REPOSITORY.joinpath(
        *REPOSITORY_CONTEXT_REPOSITORY_PATH.split("/")
    ),
    CANONICAL_REPOSITORY_PATH: REPOSITORY.joinpath(
        *CANONICAL_REPOSITORY_PATH.split("/")
    ),
    COMMON_REPOSITORY_PATH: REPOSITORY.joinpath(*COMMON_REPOSITORY_PATH.split("/")),
}
PROTOCOL_PATH = REPOSITORY / "protocols/d7_v1_pre_item23_materialization_v0_1.json"
ROUTE_PATH = REPOSITORY / "protocols/voy_v1_v9_strict_successor_route_v0_1.json"


@pytest.fixture(autouse=True)
def _remove_test_repository_hardlinks(tmp_path: Path) -> Iterator[None]:
    """Drop same-file test clones immediately after each isolated test."""

    yield
    shutil.rmtree(tmp_path, ignore_errors=True)


def _run(repository: Path, *arguments: str) -> str:
    process = subprocess.run(
        ("git", "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
        text=True,
    )
    return process.stdout.strip()


def _write(root: Path, repository_path: str, source: bytes) -> None:
    target = root.joinpath(*repository_path.split("/"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source)


def _external(role: str, marker: str) -> records.D7V1ArtifactBinding:
    return records.D7V1ArtifactBinding(
        artifact_role=role,
        artifact_contract_id=f"spirallens.test-{role}.v0.1",
        canonical_sha256=marker * 64,
        byte_count=17,
    )


def _bound(record: object) -> records.D7V1ArtifactBinding:
    assert isinstance(record, records._D7V1CanonicalRecord)
    return records.D7V1ArtifactBinding.from_record(record)


def _metadata_binding(
    metadata: Mapping[str, object],
    *,
    role_key: str = "artifact_binding_role",
) -> records.D7V1ArtifactBinding:
    return records.D7V1ArtifactBinding(
        artifact_role=str(metadata[role_key]),
        artifact_contract_id=str(metadata["artifact_contract_id"]),
        canonical_sha256=str(metadata["canonical_sha256"]),
        byte_count=int(metadata["byte_count"]),
    )


def _coordinate_paths(protocol: Mapping[str, object]) -> dict[str, str]:
    layout = protocol["coordinate_and_member_layout"]
    assert isinstance(layout, dict)
    role_map = layout["v3_exact_pre_item23_file_coordinate_roles"]
    assert isinstance(role_map, dict)
    return {str(role): str(layout[key]) for key, role in role_map.items()}


def _stage_relative(protocol: Mapping[str, object], repository_path: str) -> str:
    layout = protocol["coordinate_and_member_layout"]
    assert isinstance(layout, dict)
    prefix = f"{layout['repository_root']}/"
    assert repository_path.startswith(prefix)
    return repository_path.removeprefix(prefix)


def _build_records(
    *,
    repository: RepositoryContext,
    materialization_protocol: materialization.D7V1MaterializationProtocol,
    protocol: Mapping[str, object],
    route: Mapping[str, object],
    source_commit: str,
    source_members: Sequence[records.D7V1SourceMember],
    supplier_candidate: (
        source_selected_supplier.D7V1SourceSelectedSeedSupplierCandidate | None
    ) = None,
    supplier_identity_override: records.D7V1ArtifactBinding | None = None,
    supplier_id_override: str | None = None,
    seed_values: Sequence[int] = (8_100_001, 8_100_002),
) -> tuple[
    dict[str, records._D7V1CanonicalRecord],
    source_selected_supplier.D7V1SourceSelectedSeedSupplierCandidate,
]:
    paths = _coordinate_paths(protocol)
    route_binding_data = protocol["route_binding"]
    assert isinstance(route_binding_data, dict)
    route_binding = records.D7V1ArtifactBinding(
        artifact_role="navigation-route",
        artifact_contract_id=str(route["schema_version"]),
        canonical_sha256=str(route_binding_data["canonical_sha256"]),
        byte_count=int(route_binding_data["byte_count"]),
    )
    c1 = records.D7V1C1SourceSetRecord.create(
        record_id="d7-v1-test-c1",
        repository_path=paths[records.D7V1C1SourceSetRecord.artifact_role],
        route_binding=route_binding,
        source_members=source_members,
    )
    c2 = records.D7V1C2SourceClosureReceipt.create(
        record_id="d7-v1-test-c2",
        repository_path=paths[records.D7V1C2SourceClosureReceipt.artifact_role],
        c1=c1,
        source_commit=source_commit,
    )
    expected_supplier = supplier_candidate or (
        materialization._derive_source_selected_seed_supplier_candidate(
            repository,
            protocol=materialization_protocol,
            source_commit=source_commit,
            c1=c1,
            c2=c2,
        )
    )

    external_contract = protocol["external_durable_chronology_contract"]
    assert isinstance(external_contract, dict)
    claim_contract = external_contract["seed_supply_claim"]
    attempt_contract = external_contract["attempt_reservation"]
    route_external = external_contract["route_future_external_coordinates"]
    assert isinstance(claim_contract, dict)
    assert isinstance(attempt_contract, dict)
    assert isinstance(route_external, dict)
    supplier_identity = (
        supplier_identity_override or expected_supplier.supplier_identity_binding
    )
    supplier_id = supplier_id_override or expected_supplier.supplier_id
    claim = records.D7V1ExclusiveSeedSupplyClaim.create(
        record_id="d7-v1-test-seed-claim",
        repository_path=paths[records.D7V1ExclusiveSeedSupplyClaim.artifact_role],
        c2=c2,
        supplier_identity_binding=supplier_identity,
        supplier_id=supplier_id,
        external_claim_path=str(claim_contract["external_store_path"]),
    )

    historical = protocol["historical_input_policy"]
    assert isinstance(historical, dict)
    negative_inputs = historical["negative_exclusion_inputs"]
    assert isinstance(negative_inputs, list) and len(negative_inputs) == 1
    predecessor = negative_inputs[0]
    assert isinstance(predecessor, dict)
    predecessor_values = predecessor["pinned_predecessor_seed_values"]
    assert isinstance(predecessor_values, list)
    inventory = records.D7V1OfficialSeedInventory.create(
        record_id="d7-v1-test-seed-inventory",
        repository_path=paths[records.D7V1OfficialSeedInventory.artifact_role],
        claim=claim,
        supplier_identity_binding=supplier_identity,
        supplier_id=supplier_id,
        seeds=seed_values,
        predecessor_inventory_binding=_metadata_binding(predecessor),
        predecessor_seed_values=tuple(int(value) for value in predecessor_values),
    )

    full_design = records.D7V1EmbeddedFullDesign.create(
        design_id="d7-v1-spectral-moment-official-full-design",
        family_binding=_external("confirmation-family", "6"),
        admission_binding=_external("family-admission", "7"),
        protocol_binding=_external("confirmation-protocol", "8"),
        source_graph_binding=_external("source-graph", "9"),
        inventory_binding=_bound(inventory),
        graph_case_stress_aggregation_binding=_external(
            "graph-case-stress-aggregation", "a"
        ),
        lifecycle_binding=_external("lifecycle", "b"),
    )

    protocol_binding = records.D7V1ArtifactBinding(
        artifact_role="v1-materialization-protocol",
        artifact_contract_id=str(protocol["schema_version"]),
        canonical_sha256=sha256_bytes(PROTOCOL_PATH.read_bytes()),
        byte_count=len(PROTOCOL_PATH.read_bytes()),
    )
    historical_plan = historical["historical_plan_binding"]
    parents = historical["permitted_historical_scientific_parents"]
    assert isinstance(historical_plan, dict)
    assert isinstance(parents, list)
    pinned = {
        binding.artifact_role: binding
        for binding in (
            _metadata_binding(historical_plan),
            *(
                _metadata_binding(parent)
                for parent in parents
                if isinstance(parent, dict)
            ),
        )
    }
    transitive_by_role = {
        records.D7V1C1SourceSetRecord.artifact_role: _bound(c1),
        records.D7V1C2SourceClosureReceipt.artifact_role: _bound(c2),
        records.D7V1ExclusiveSeedSupplyClaim.artifact_role: _bound(claim),
        records.D7V1OfficialSeedInventory.artifact_role: _bound(inventory),
        "embedded-full-design": records.D7V1ArtifactBinding(
            artifact_role="embedded-full-design",
            artifact_contract_id=full_design.schema_version,
            canonical_sha256=full_design.canonical_sha256,
            byte_count=full_design.byte_count,
        ),
        "navigation-route": route_binding,
        "v1-materialization-protocol": protocol_binding,
        **pinned,
    }
    transitive = {
        key: transitive_by_role[role]
        for key, role in records._REPLAY_TRANSITIVE_ROLES.items()
        if key != "embedded_full_design_binding"
    }
    replay = records.D7V1ReplayTarget.create(
        record_id="d7-v1-test-replay-target",
        repository_path=paths[records.D7V1ReplayTarget.artifact_role],
        official_seed_inventory_binding=_bound(inventory),
        full_design=full_design,
        transitive_bindings=transitive,
    )
    replay_document = replay.to_dict()
    freeze = records.D7V1FullDesignFreeze.create(
        record_id="d7-v1-test-full-design-freeze",
        repository_path=paths[records.D7V1FullDesignFreeze.artifact_role],
        replay_target_binding=_bound(replay),
        full_design_binding=records.D7V1JsonPointerBinding.from_dict(
            replay_document["full_design_binding"]
        ),
        reviewed_source_commit=source_commit,
    )

    declaration = route["strict_successor_declaration"]
    assert isinstance(declaration, dict)
    entrypoints = declaration["future_entrypoint_coordinates"]
    assert isinstance(entrypoints, dict)
    launch = records.D7V1LaunchIntent.create(
        record_id="d7-v1-test-launch-intent",
        repository_path=paths[records.D7V1LaunchIntent.artifact_role],
        replay_target_binding=_bound(replay),
        full_design_freeze_binding=_bound(freeze),
        external_store_path=str(route_external["external_store_path"]),
        external_staging_path=str(route_external["external_staging_path"]),
        runner_script=str(entrypoints["runner_script"]),
        official_callable=str(entrypoints["official_callable"]),
    )
    attempt = records.D7V1OfficialExecutionAttemptReservation.create(
        record_id="d7-v1-test-attempt-reservation",
        repository_path=paths[
            records.D7V1OfficialExecutionAttemptReservation.artifact_role
        ],
        launch_intent=launch,
        replay_target=replay,
        seed_claim=claim,
        external_attempt_path=str(attempt_contract["external_store_path"]),
        external_store_path=str(route_external["external_store_path"]),
        reviewed_source_commit=source_commit,
    )
    result_path = str(
        protocol["coordinate_and_member_layout"]["descriptive_result"]  # type: ignore[index]
    )
    absence = records.D7V1NamespaceAbsenceObservation(
        repository_path=result_path,
        observed_at_reviewed_source_commit=source_commit,
    )
    predecessor_records = (c1, c2, claim, inventory, replay, freeze, launch, attempt)
    receipt = records.D7V1PreItem23ChronologyReceipt.create(
        record_id="d7-v1-test-pre-item23-receipt",
        repository_path=paths[records.D7V1PreItem23ChronologyReceipt.artifact_role],
        predecessor_bindings={
            record.artifact_role: _bound(record) for record in predecessor_records
        },
        pre_item23_file_inventory=paths,
        descriptive_result_namespace_absence=absence,
    )
    result = records.D7V1PostselectionDescriptiveResult.create(
        record_id="d7-v1-test-result",
        repository_path=result_path,
        parent_binding=_bound(attempt),
        chronology_receipt_binding=_bound(receipt),
        read_trace=(),
        status="failed",
        outputs=(),
    )
    return (
        {
            record.artifact_role: record
            for record in (*predecessor_records, receipt, result)
        },
        expected_supplier,
    )


@dataclass(slots=True)
class _Case:
    repository: Path
    context: RepositoryContext
    source_commit: str
    stage_root: Path
    protocol: dict[str, object]
    records_by_role: dict[str, records._D7V1CanonicalRecord]
    external_bytes: dict[Path, bytes]
    supplier_candidate: source_selected_supplier.D7V1SourceSelectedSeedSupplierCandidate

    @property
    def receipt(self) -> records.D7V1PreItem23ChronologyReceipt:
        value = self.records_by_role[
            records.D7V1PreItem23ChronologyReceipt.artifact_role
        ]
        assert isinstance(value, records.D7V1PreItem23ChronologyReceipt)
        return value

    @property
    def result(self) -> records.D7V1PostselectionDescriptiveResult:
        value = self.records_by_role[
            records.D7V1PostselectionDescriptiveResult.artifact_role
        ]
        assert isinstance(value, records.D7V1PostselectionDescriptiveResult)
        return value

    def external_reader(self, path: Path, max_bytes: int) -> bytes:
        source = self.external_bytes[path]
        if len(source) > max_bytes:
            raise QualificationContractError("external fixture exceeds byte cap")
        return source


def _build_case(
    tmp_path: Path,
    *,
    result_present_at_source: bool = False,
    prior_introduction: str | None = None,
    source_base_commit: str | None = None,
    isolated_clone: bool = False,
    sparse_checkout: bool = True,
    mutate_source_member: Callable[
        [tuple[records.D7V1SourceMember, ...]],
        tuple[records.D7V1SourceMember, ...],
    ]
    | None = None,
    supplier_identity_override: records.D7V1ArtifactBinding | None = None,
    supplier_id_override: str | None = None,
    seed_values: Sequence[int] = (8_100_001, 8_100_002),
) -> _Case:
    fixture_supplier_candidate = None
    if result_present_at_source or source_base_commit is not None:
        # Both options deliberately make the eventual source join invalid.  Use
        # one independently valid fixture case to obtain an exact supplier
        # candidate without consuming the loader rejection under test.
        fixture_supplier_candidate = _build_case(
            tmp_path / "supplier-fixture-baseline",
            isolated_clone=isolated_clone,
            sparse_checkout=sparse_checkout,
        ).supplier_candidate
    repository = tmp_path / "repository"
    clone_storage = ("--no-local",) if isolated_clone else ("--shared",)
    subprocess.run(
        (
            "git",
            "clone",
            "--quiet",
            *clone_storage,
            "--no-checkout",
            str(REPOSITORY),
            str(repository),
        ),
        check=True,
    )
    if sparse_checkout:
        _run(repository, "sparse-checkout", "init", "--no-cone")
        _run(
            repository,
            "sparse-checkout",
            "set",
            "--no-cone",
            "/README.md",
            "/protocols/*",
            "/scripts/*",
            "/src/spirallens/qualification/*",
            "/experiments/qualification/d7_spectral_moment_confirmation_v1/*",
        )
    _run(repository, "checkout", "--quiet", "HEAD")
    (repository / "experiments" / "qualification").mkdir(
        parents=True,
        exist_ok=True,
    )
    _run(repository, "config", "user.name", "SpiralLens test")
    _run(repository, "config", "user.email", "spirallens-test@example.invalid")
    if source_base_commit is not None:
        _run(repository, "checkout", "--quiet", "--detach", source_base_commit)
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    route = json.loads(ROUTE_PATH.read_text(encoding="utf-8"))
    if prior_introduction is not None:
        if prior_introduction == "artifact":
            prior_path = str(protocol["coordinate_and_member_layout"]["c1_source_set"])
        elif prior_introduction == "result":
            prior_path = str(
                protocol["coordinate_and_member_layout"]["descriptive_result"]
            )
        else:
            raise AssertionError(f"unknown prior_introduction: {prior_introduction}")
        base_branch = _run(repository, "branch", "--show-current")
        assert base_branch
        side_branch = f"hidden-prior-{prior_introduction}"
        _run(repository, "switch", "--quiet", "-c", side_branch)
        _write(repository, prior_path, b"historical collision\n")
        _run(repository, "add", "--all")
        _run(repository, "commit", "--quiet", "-m", "hidden prior addition")
        prior_file = repository.joinpath(*prior_path.split("/"))
        prior_file.unlink()
        _run(repository, "add", "--all")
        _run(repository, "commit", "--quiet", "-m", "hidden prior deletion")
        _run(repository, "switch", "--quiet", base_branch)
        _run(
            repository,
            "merge",
            "--quiet",
            "--no-ff",
            "-m",
            "merge hidden prior history",
            side_branch,
        )
    required = protocol["source_contract"]["required_new_source_paths"]
    assert isinstance(required, list)
    source_closure_paths = [
        *map(str, required),
        *FOUNDATION_SOURCE_PATHS,
        EXECUTION_DESIGN_REPOSITORY_PATH,
        *DESCRIPTIVE_HELPER_REPOSITORY_PATHS,
        PRIVATE_PUBLICATION_REPOSITORY_PATH,
        RESULT_PUBLICATION_REPOSITORY_PATH,
        SOURCE_CLOSURE_REPOSITORY_PATH,
        SOURCE_SELECTED_SUPPLIER_REPOSITORY_PATH,
    ]
    for repository_path in source_closure_paths:
        target = repository.joinpath(*repository_path.split("/"))
        if repository_path in FOUNDATION_SOURCE_PATHS:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.unlink(missing_ok=True)
            os.link(FOUNDATION_SOURCE_PATHS[repository_path], target)
            continue
        if repository_path == EXECUTION_DESIGN_REPOSITORY_PATH:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.unlink(missing_ok=True)
            os.link(EXECUTION_DESIGN_MODULE_PATH, target)
            continue
        if repository_path == (
            "src/spirallens/qualification/confirmation_v1_materialization.py"
        ):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.unlink(missing_ok=True)
            os.link(MODULE_PATH, target)
            continue
        if repository_path == (
            "src/spirallens/qualification/confirmation_v1_records.py"
        ):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.unlink(missing_ok=True)
            os.link(RECORDS_MODULE_PATH, target)
            continue
        if repository_path == DESCRIPTIVE_REPOSITORY_PATH:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.unlink(missing_ok=True)
            os.link(DESCRIPTIVE_MODULE_PATH, target)
            continue
        if repository_path in DESCRIPTIVE_HELPER_SOURCE_PATHS:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.unlink(missing_ok=True)
            os.link(DESCRIPTIVE_HELPER_SOURCE_PATHS[repository_path], target)
            continue
        if repository_path == PRIVATE_PUBLICATION_REPOSITORY_PATH:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.unlink(missing_ok=True)
            os.link(PRIVATE_PUBLICATION_MODULE_PATH, target)
            continue
        if repository_path == RESULT_PUBLICATION_REPOSITORY_PATH:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.unlink(missing_ok=True)
            os.link(RESULT_PUBLICATION_MODULE_PATH, target)
            continue
        if repository_path == SOURCE_CLOSURE_REPOSITORY_PATH:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.unlink(missing_ok=True)
            os.link(SOURCE_CLOSURE_MODULE_PATH, target)
            continue
        if repository_path == SOURCE_SELECTED_SUPPLIER_REPOSITORY_PATH:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.unlink(missing_ok=True)
            os.link(SOURCE_SELECTED_SUPPLIER_MODULE_PATH, target)
            continue
        if repository_path == ("protocols/d7_v1_pre_item23_materialization_v0_1.json"):
            _write(repository, repository_path, PROTOCOL_PATH.read_bytes())
            continue
        if not target.exists():
            source = b'"""Non-operational source-closure test fixture."""\n'
        else:
            continue
        _write(repository, repository_path, source)
    if result_present_at_source:
        result_path = str(
            protocol["coordinate_and_member_layout"]["descriptive_result"]
        )
        _write(repository, result_path, b"{}")
    _run(repository, "add", "--all")
    _run(
        repository,
        "commit",
        "--allow-empty",
        "--quiet",
        "-m",
        "test source S",
    )
    source_commit = _run(repository, "rev-parse", "HEAD")

    context = RepositoryContext(root=repository.resolve())
    loaded_protocol = materialization._load_protocol_source(PROTOCOL_PATH.read_bytes())
    members = materialization._enumerate_choice_free_d7_v1_source_members(
        context,
        loaded_protocol,
        source_commit,
    )
    records_by_role, supplier_candidate = _build_records(
        repository=context,
        materialization_protocol=loaded_protocol,
        protocol=protocol,
        route=route,
        source_commit=source_commit,
        source_members=members,
        supplier_candidate=fixture_supplier_candidate,
        supplier_identity_override=supplier_identity_override,
        supplier_id_override=supplier_id_override,
        seed_values=seed_values,
    )
    if mutate_source_member is not None:
        members = mutate_source_member(members)
        records_by_role, _supplier_candidate = _build_records(
            repository=context,
            materialization_protocol=loaded_protocol,
            protocol=protocol,
            route=route,
            source_commit=source_commit,
            source_members=members,
            supplier_candidate=supplier_candidate,
            supplier_identity_override=supplier_identity_override,
            supplier_id_override=supplier_id_override,
            seed_values=seed_values,
        )
    stage_root = tmp_path / "stage"
    paths = _coordinate_paths(protocol)
    for role, repository_path in paths.items():
        _write(
            stage_root,
            _stage_relative(protocol, repository_path),
            records_by_role[role].canonical_bytes,
        )

    external_contract = protocol["external_durable_chronology_contract"]
    claim_path = Path(external_contract["seed_supply_claim"]["external_store_path"])
    attempt_path = Path(external_contract["attempt_reservation"]["external_store_path"])
    external_bytes = {
        claim_path: records_by_role[
            records.D7V1ExclusiveSeedSupplyClaim.artifact_role
        ].canonical_bytes,
        attempt_path: records_by_role[
            records.D7V1OfficialExecutionAttemptReservation.artifact_role
        ].canonical_bytes,
    }
    return _Case(
        repository=repository,
        context=context,
        source_commit=source_commit,
        stage_root=stage_root,
        protocol=protocol,
        records_by_role=records_by_role,
        external_bytes=external_bytes,
        supplier_candidate=supplier_candidate,
    )


def _load_stage(
    case: _Case,
    *,
    external_reader: Callable[[Path, int], bytes] | None = None,
) -> materialization.D7V1JoinedRecords:
    with patch.object(
        materialization,
        "_default_external_reader",
        external_reader or case.external_reader,
    ):
        return materialization._load_d7_v1_staged_joined_records(
            case.context,
            case.stage_root,
            expected_receipt_sha256=case.receipt.canonical_sha256,
        )


def _verify_commit_a(
    case: _Case,
    artifact_commit: str,
) -> materialization.D7V1CommitVerification:
    with patch.object(
        materialization,
        "_default_external_reader",
        case.external_reader,
    ):
        return materialization._verify_and_load_d7_v1_commit_a(
            case.context,
            source_commit=case.source_commit,
            artifact_commit=artifact_commit,
        )


def _verify_commit_b(
    case: _Case,
    artifact_commit: str,
    result_commit: str,
) -> materialization.D7V1CommitVerification:
    with patch.object(
        materialization,
        "_default_external_reader",
        case.external_reader,
    ):
        return materialization._verify_and_load_d7_v1_commit_b(
            case.context,
            source_commit=case.source_commit,
            artifact_commit=artifact_commit,
            result_commit=result_commit,
        )


def _copy_pre_item23_to_repository(case: _Case) -> None:
    for repository_path in _coordinate_paths(case.protocol).values():
        stage_path = _stage_relative(case.protocol, repository_path)
        source = case.stage_root.joinpath(*stage_path.split("/"))
        _write(case.repository, repository_path, source.read_bytes())


def _commit_a(case: _Case, *, extra_delta: bool = False) -> str:
    _copy_pre_item23_to_repository(case)
    if extra_delta:
        _write(
            case.repository,
            "protocols/unexpected-test-a.txt",
            b"not part of commit A\n",
        )
    _run(case.repository, "add", "--all")
    _run(case.repository, "commit", "--quiet", "-m", "artifact-only A")
    return _run(case.repository, "rev-parse", "HEAD")


def _exact_descriptive_result(
    case: _Case,
) -> records.D7V1PostselectionDescriptiveResult:
    historical = case.protocol["historical_input_policy"]
    assert isinstance(historical, dict)
    entries = [
        historical["historical_plan_binding"],
        *historical["permitted_historical_scientific_parents"],
    ]
    sources: dict[str, bytes] = {}
    for entry in entries:
        assert isinstance(entry, dict)
        role = str(entry["artifact_binding_role"])
        sources[role] = subprocess.run(
            (
                "git",
                "-C",
                str(case.repository),
                "show",
                f"{entry['source_commit']}:{entry['repository_path']}",
            ),
            check=True,
            capture_output=True,
        ).stdout
    attempt = case.records_by_role[
        records.D7V1OfficialExecutionAttemptReservation.artifact_role
    ]
    assert isinstance(attempt, records.D7V1OfficialExecutionAttemptReservation)
    return descriptive._derive_d7_v1_post_d6_descriptive_result(
        historical_plan_source=sources["historical-post-d6-plan"],
        parent_protocol_source=sources["parent-protocol"],
        parent_result_source=sources["parent-result"],
        parent_manifest_source=sources["parent-manifest"],
        parent_consumption_source=sources["parent-consumption"],
        parent_d6_decision_source=sources["parent-d6-decision"],
        parent_attempt=attempt,
        chronology_receipt=case.receipt,
    )


def _commit_b(
    case: _Case,
    *,
    extra_delta: bool = False,
    exact_result: bool = False,
) -> str:
    result_path = str(
        case.protocol["coordinate_and_member_layout"]["descriptive_result"]
    )
    result = _exact_descriptive_result(case) if exact_result else case.result
    _write(case.repository, result_path, result.canonical_bytes)
    if extra_delta:
        _write(
            case.repository,
            "protocols/unexpected-test-b.txt",
            b"not part of commit B\n",
        )
    _run(case.repository, "add", "--all")
    _run(case.repository, "commit", "--quiet", "-m", "result-only B")
    return _run(case.repository, "rev-parse", "HEAD")


def test_staged_joined_loader_and_exact_commit_a_and_b_succeed(tmp_path: Path) -> None:
    case = _build_case(tmp_path)
    assert isinstance(_load_stage(case), materialization.D7V1JoinedRecords)
    commit_a = _commit_a(case)
    verified_a = _verify_commit_a(case, commit_a)
    assert isinstance(verified_a, materialization.D7V1CommitVerification)
    commit_b = _commit_b(case, exact_result=True)
    verified_b = _verify_commit_b(case, commit_a, commit_b)
    assert isinstance(verified_b, materialization.D7V1CommitVerification)


def test_commit_b_rejects_a_schema_valid_nonrederived_result(
    tmp_path: Path,
) -> None:
    case = _build_case(tmp_path)
    commit_a = _commit_a(case)
    commit_b = _commit_b(case)

    with pytest.raises(QualificationContractError, match="fresh six-input derivation"):
        _verify_commit_b(case, commit_a, commit_b)


def test_high_level_verifiers_have_no_external_reader_injection_surface(
    tmp_path: Path,
) -> None:
    case = _build_case(tmp_path)
    for function in (
        materialization._load_d7_v1_staged_joined_records,
        materialization._verify_and_load_d7_v1_commit_a,
        materialization._verify_and_load_d7_v1_commit_b,
    ):
        assert "external_reader" not in inspect.signature(function).parameters
    with pytest.raises(QualificationContractError, match="cannot open"):
        materialization._load_d7_v1_staged_joined_records(
            case.context,
            case.stage_root,
            expected_receipt_sha256=case.receipt.canonical_sha256,
        )


def test_staged_loader_rejects_locally_valid_but_cross_record_tampering(
    tmp_path: Path,
) -> None:
    case = _build_case(tmp_path)
    old_c1 = case.records_by_role[records.D7V1C1SourceSetRecord.artifact_role]
    assert isinstance(old_c1, records.D7V1C1SourceSetRecord)
    old_payload = old_c1.to_dict()["payload"]
    alternate_c1 = records.D7V1C1SourceSetRecord.create(
        record_id="d7-v1-test-alternate-c1",
        repository_path=str(old_payload["repository_path"]),
        route_binding=records.D7V1ArtifactBinding.from_dict(
            old_payload["route_binding"]
        ),
        source_members=tuple(
            records.D7V1SourceMember.from_dict(item)
            for item in old_payload["source_members"]
        ),
    )
    predecessors = {
        role: record
        for role, record in case.records_by_role.items()
        if role
        in {
            records.D7V1C1SourceSetRecord.artifact_role,
            records.D7V1C2SourceClosureReceipt.artifact_role,
            records.D7V1ExclusiveSeedSupplyClaim.artifact_role,
            records.D7V1OfficialSeedInventory.artifact_role,
            records.D7V1ReplayTarget.artifact_role,
            records.D7V1FullDesignFreeze.artifact_role,
            records.D7V1LaunchIntent.artifact_role,
            records.D7V1OfficialExecutionAttemptReservation.artifact_role,
        }
    }
    predecessors[alternate_c1.artifact_role] = alternate_c1
    old_receipt = case.receipt.to_dict()["payload"]
    tampered_receipt = records.D7V1PreItem23ChronologyReceipt.create(
        record_id="d7-v1-test-tampered-receipt",
        repository_path=str(old_receipt["repository_path"]),
        predecessor_bindings={
            role: _bound(record) for role, record in predecessors.items()
        },
        pre_item23_file_inventory={
            role: str(path)
            for role, path in old_receipt["pre_item23_file_inventory"].items()
        },
        descriptive_result_namespace_absence=(
            records.D7V1NamespaceAbsenceObservation.from_dict(
                old_receipt["descriptive_result_namespace_absence"]
            )
        ),
    )
    paths = _coordinate_paths(case.protocol)
    _write(
        case.stage_root,
        _stage_relative(case.protocol, paths[alternate_c1.artifact_role]),
        alternate_c1.canonical_bytes,
    )
    _write(
        case.stage_root,
        _stage_relative(case.protocol, paths[tampered_receipt.artifact_role]),
        tampered_receipt.canonical_bytes,
    )
    with pytest.raises(QualificationContractError):
        with patch.object(
            materialization,
            "_default_external_reader",
            case.external_reader,
        ):
            materialization._load_d7_v1_staged_joined_records(
                case.context,
                case.stage_root,
                expected_receipt_sha256=tampered_receipt.canonical_sha256,
            )


@pytest.mark.parametrize("external_role", ("claim", "attempt"))
def test_staged_loader_rejects_external_projection_byte_mismatch(
    tmp_path: Path,
    external_role: str,
) -> None:
    case = _build_case(tmp_path)
    external_contract = case.protocol["external_durable_chronology_contract"]
    key = "seed_supply_claim" if external_role == "claim" else "attempt_reservation"
    path = Path(external_contract[key]["external_store_path"])

    def mismatched_reader(candidate: Path, max_bytes: int) -> bytes:
        source = case.external_reader(candidate, max_bytes)
        return b"x" + source[1:] if candidate == path else source

    with pytest.raises(QualificationContractError):
        _load_stage(case, external_reader=mismatched_reader)


@pytest.mark.parametrize("mismatch", ("blob", "mode"))
def test_staged_loader_reenumerates_source_blob_and_mode(
    tmp_path: Path,
    mismatch: str,
) -> None:
    def mutate(
        members: tuple[records.D7V1SourceMember, ...],
    ) -> tuple[records.D7V1SourceMember, ...]:
        first, *rest = members
        changed = records.D7V1SourceMember(
            repository_path=first.repository_path,
            git_mode=("100755" if mismatch == "mode" else first.git_mode),
            sha256=("0" * 64 if mismatch == "blob" else first.sha256),
            byte_count=first.byte_count,
        )
        return (changed, *rest)

    case = _build_case(tmp_path, mutate_source_member=mutate)
    with pytest.raises(QualificationContractError):
        _load_stage(case)


@pytest.mark.parametrize(
    "repository_path",
    (
        "src/spirallens/qualification/confirmation_v1_materialization.py",
        "src/spirallens/qualification/confirmation_v1_records.py",
        DESCRIPTIVE_REPOSITORY_PATH,
    ),
)
def test_staged_loader_rejects_an_equivalent_but_different_import_origin(
    tmp_path: Path,
    repository_path: str,
) -> None:
    case = _build_case(tmp_path)
    commit_a = _commit_a(case)
    target = case.repository.joinpath(*repository_path.split("/"))
    source = target.read_bytes()
    target.unlink()
    target.write_bytes(source)
    with pytest.raises(QualificationContractError, match="import origin differs"):
        _load_stage(case)
    with pytest.raises(QualificationContractError, match="import origin differs"):
        _verify_commit_a(case, commit_a)


def test_staged_loader_rejects_dirty_executing_source_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _build_case(tmp_path)
    target = case.repository / MODULE_PATH.relative_to(REPOSITORY)
    original_read = materialization._safe_read_file

    def dirty_read(
        path: Path,
        maximum_bytes: int,
        *,
        require_single_link: bool = True,
    ) -> bytes:
        source = original_read(
            path,
            maximum_bytes,
            require_single_link=require_single_link,
        )
        if path == target:
            return source + b"\n"
        return source

    monkeypatch.setattr(materialization, "_safe_read_file", dirty_read)
    with pytest.raises(QualificationContractError, match="reviewed source S"):
        _load_stage(case)


def test_source_commit_must_descend_from_the_merged_protocol(tmp_path: Path) -> None:
    case = _build_case(
        tmp_path,
        source_base_commit="2645ab360598c9ff4f1d9e628b9a9fe1857aedf6",
    )
    with pytest.raises(QualificationContractError, match="protocol merge commit"):
        _load_stage(case)


def test_result_namespace_must_be_absent_at_source_commit(tmp_path: Path) -> None:
    case = _build_case(tmp_path, result_present_at_source=True)
    with pytest.raises(QualificationContractError):
        _load_stage(case)


def test_commit_a_rejects_merge_and_non_exact_delta_but_reads_committed_bytes(
    tmp_path: Path,
) -> None:
    merge_case = _build_case(tmp_path / "merge")
    branch = _run(merge_case.repository, "branch", "--show-current")
    _run(merge_case.repository, "switch", "--quiet", "-c", "artifact-side")
    side_commit = _commit_a(merge_case)
    assert side_commit
    _run(merge_case.repository, "switch", "--quiet", branch)
    _run(
        merge_case.repository,
        "merge",
        "--quiet",
        "--no-ff",
        "-m",
        "merge artifact side",
        "artifact-side",
    )
    merge_commit = _run(merge_case.repository, "rev-parse", "HEAD")
    with pytest.raises(QualificationContractError):
        _verify_commit_a(merge_case, merge_commit)

    dirty_case = _build_case(tmp_path / "dirty")
    dirty_a = _commit_a(dirty_case)
    (dirty_case.repository / "README.md").write_text("dirty\n", encoding="utf-8")
    dirty_verification = _verify_commit_a(dirty_case, dirty_a)
    assert dirty_verification.artifact_commit == dirty_a
    assert (dirty_case.repository / "README.md").read_text(encoding="utf-8") == (
        "dirty\n"
    )

    delta_case = _build_case(tmp_path / "delta")
    wrong_a = _commit_a(delta_case, extra_delta=True)
    with pytest.raises(QualificationContractError):
        _verify_commit_a(delta_case, wrong_a)


def test_commit_b_rejects_non_exact_result_delta(tmp_path: Path) -> None:
    case = _build_case(tmp_path)
    commit_a = _commit_a(case)
    commit_b = _commit_b(case, extra_delta=True)
    with pytest.raises(QualificationContractError):
        _verify_commit_b(case, commit_a, commit_b)


def test_git_replace_refs_cannot_substitute_a_valid_artifact_commit(
    tmp_path: Path,
) -> None:
    case = _build_case(tmp_path)
    valid_a = _commit_a(case)
    _run(case.repository, "reset", "--hard", case.source_commit)
    invalid_a = _commit_a(case, extra_delta=True)
    _run(case.repository, "replace", invalid_a, valid_a)
    with pytest.raises(QualificationContractError):
        _verify_commit_a(case, invalid_a)


def test_git_execution_ignores_caller_environment_overrides(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _build_case(tmp_path)
    commit_a = _commit_a(case)
    graft = tmp_path / "caller-grafts"
    graft.write_text(f"{commit_a}\n", encoding="ascii")
    shallow = tmp_path / "caller-shallow"
    shallow.write_text(f"{case.source_commit}\n", encoding="ascii")
    global_config = tmp_path / "caller-gitconfig"
    global_config.write_text(
        "[core]\nrepositoryformatversion = 999\n", encoding="utf-8"
    )
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    fake_git = fake_bin / "git"
    fake_git.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
    fake_git.chmod(0o755)
    overrides = {
        "GIT_COMMON_DIR": str(tmp_path / "not-the-common-dir"),
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_GLOBAL": str(global_config),
        "GIT_CONFIG_KEY_0": "core.repositoryformatversion",
        "GIT_CONFIG_VALUE_0": "999",
        "GIT_GRAFT_FILE": str(graft),
        "GIT_NO_LAZY_FETCH": "0",
        "GIT_SHALLOW_FILE": str(shallow),
        "PATH": str(fake_bin),
    }
    for name, value in overrides.items():
        monkeypatch.setenv(name, value)

    environment = materialization._git_environment()
    assert environment["PATH"] == os.defpath
    assert environment["GIT_NO_LAZY_FETCH"] == "1"
    assert environment["GIT_CONFIG_COUNT"] == "0"
    assert environment["GIT_CONFIG_GLOBAL"] == os.devnull
    assert not {
        "GIT_COMMON_DIR",
        "GIT_CONFIG_KEY_0",
        "GIT_CONFIG_VALUE_0",
        "GIT_GRAFT_FILE",
        "GIT_SHALLOW_FILE",
    } & set(environment)
    assert _verify_commit_a(case, commit_a).artifact_commit == commit_a


@pytest.mark.parametrize("history_override", ("graft", "shallow"))
def test_repository_local_incomplete_or_grafted_history_is_rejected(
    tmp_path: Path,
    history_override: str,
) -> None:
    case = _build_case(tmp_path)
    common = Path(
        _run(
            case.repository,
            "rev-parse",
            "--path-format=absolute",
            "--git-common-dir",
        )
    )
    if history_override == "graft":
        graft = common / "info" / "grafts"
        graft.parent.mkdir(parents=True, exist_ok=True)
        graft.write_text(f"{case.source_commit}\n", encoding="ascii")
        match = "graft"
    else:
        (common / "shallow").write_text(f"{case.source_commit}\n", encoding="ascii")
        match = "shallow"
    with pytest.raises(QualificationContractError, match=match):
        _load_stage(case)


@pytest.mark.parametrize("prior_introduction", ("artifact", "result"))
def test_full_history_rejects_a_prior_add_delete_merge_collision(
    tmp_path: Path,
    prior_introduction: str,
) -> None:
    case = _build_case(tmp_path, prior_introduction=prior_introduction)
    commit_a = _commit_a(case)
    if prior_introduction == "artifact":
        with pytest.raises(QualificationContractError, match="introduced exactly once"):
            _verify_commit_a(case, commit_a)
        return

    commit_b = _commit_b(case)
    with pytest.raises(QualificationContractError, match="introduced exactly once"):
        _verify_commit_b(case, commit_a, commit_b)


def test_staged_loader_rejects_an_extra_empty_directory(tmp_path: Path) -> None:
    case = _build_case(tmp_path)
    (case.stage_root / "unexpected-empty-directory").mkdir()
    with pytest.raises(QualificationContractError, match="exact nine-file tree"):
        _load_stage(case)


def test_commit_a_enforces_the_role_byte_cap_before_reading_the_blob(
    tmp_path: Path,
) -> None:
    case = _build_case(tmp_path)
    _copy_pre_item23_to_repository(case)
    c1_path = _coordinate_paths(case.protocol)[
        records.D7V1C1SourceSetRecord.artifact_role
    ]
    _write(
        case.repository,
        c1_path,
        b"x" * (records.D7_V1_DEFAULT_MAX_RECORD_BYTES + 1),
    )
    _run(case.repository, "add", "--all")
    _run(case.repository, "commit", "--quiet", "-m", "oversized artifact A")
    commit_a = _run(case.repository, "rev-parse", "HEAD")
    with pytest.raises(QualificationContractError, match="pre-read byte cap"):
        _verify_commit_a(case, commit_a)


def test_module_import_and_protocol_load_have_no_operational_side_effects() -> None:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    layout = protocol["coordinate_and_member_layout"]
    external = protocol["external_durable_chronology_contract"]
    watched = [
        *(REPOSITORY / path for path in _coordinate_paths(protocol).values()),
        REPOSITORY / str(layout["descriptive_result"]),
        Path(str(external["route_future_external_coordinates"]["external_store_path"])),
        Path(
            str(external["route_future_external_coordinates"]["external_staging_path"])
        ),
    ]
    assert all(not path.exists() for path in watched)
    before = {path: path.exists() for path in watched}
    importlib.reload(materialization)
    loaded = materialization._load_d7_v1_materialization_protocol(
        RepositoryContext(root=REPOSITORY.resolve())
    )
    assert isinstance(loaded, materialization.D7V1MaterializationProtocol)
    assert {path: path.exists() for path in watched} == before

    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imported: set[str] = set()
    calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
        elif isinstance(node, ast.Call):
            name = node.func
            parts: list[str] = []
            while isinstance(name, ast.Attribute):
                parts.append(name.attr)
                name = name.value
            if isinstance(name, ast.Name):
                parts.append(name.id)
            calls.add(".".join(reversed(parts)))
    forbidden_import_fragments = {
        "confirmation_attempt_",
        "confirmation_authoritative_start_persistence",
        "confirmation_c1",
        "confirmation_execution_design",
        "confirmation_execution_kernel",
        "confirmation_fused_",
        "confirmation_official_execution",
        "confirmation_preseed_authority",
        "confirmation_seed_supply_contracts",
        "confirmation_source_closure",
        "confirmation_terminal_operations",
    }
    assert not any(
        fragment in module_name
        for module_name in imported
        for fragment in forbidden_import_fragments
    )
    assert not imported & {"secrets", "torch", "transformers"}
    forbidden_calls = {
        "build_seed_free_d7_confirmation_execution_design",
        "_execute_d7_seed_slot_primary_runtime",
        "produce_d7_v1_official_result",
        "from_pretrained",
        "load_model",
    }
    assert not any(call.rsplit(".", 1)[-1] in forbidden_calls for call in calls)
    assert not hasattr(materialization, "_publish_pre_item23_directory_no_replace")
    assert not hasattr(materialization, "_rename_directory_no_replace")
    assert materialization.__all__ == ()


def test_v1_private_publication_boundary_is_projected_without_api_promotion() -> None:
    readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")
    roadmap = (REPOSITORY / "docs/ROADMAP.md").read_text(encoding="utf-8")
    ledger = (REPOSITORY / "docs/EXPERIMENT_INTERPRETATION_LEDGER.md").read_text(
        encoding="utf-8"
    )
    changelog = (REPOSITORY / "docs/SCHEMA_CHANGELOG.md").read_text(encoding="utf-8")

    assert "source-only primitive now owns its private repository stage" in readme
    assert "no caller-owned-stage publisher" in " ".join(roadmap.split())
    assert "### 3.18 D7 v1 private-stage publication mechanism" in ledger
    assert "## 2026-08-10 — D7 v1 private-stage publication primitive" in changelog
    assert "The primitive has not been" in changelog


def _private_publication_sources(case: _Case) -> dict[str, bytes]:
    return {
        role: case.records_by_role[role].canonical_bytes
        for role in materialization._ROLE_CLASSES
    }


def _private_publication_paths(case: _Case) -> tuple[Path, Path]:
    protocol = materialization._load_d7_v1_materialization_protocol(case.context)
    _parent, _destination_leaf, _stage_leaf, destination = (
        private_publication._publication_coordinates(
            case.context,
            protocol,
            case.receipt.canonical_sha256,
        )
    )
    stage = destination.parent / (
        f".{destination.name}{private_publication._STAGE_MARKER}"
        f"{case.receipt.canonical_sha256}"
    )
    return stage, destination


def _publish_private_case(
    case: _Case,
) -> private_publication.D7V1PrivatePublicationReceipt:
    with patch.object(
        materialization,
        "_default_external_reader",
        case.external_reader,
    ):
        return private_publication._publish_d7_v1_pre_item23_records_no_replace(
            case.context,
            _private_publication_sources(case),
            expected_receipt_sha256=case.receipt.canonical_sha256,
        )


def _tree_snapshot(root: Path) -> tuple[tuple[str, int, int, int, bytes | None], ...]:
    result: list[tuple[str, int, int, int, bytes | None]] = []
    for path in sorted(root.rglob("*")):
        observed = path.lstat()
        result.append(
            (
                path.relative_to(root).as_posix(),
                observed.st_mode,
                observed.st_ino,
                observed.st_size,
                path.read_bytes() if path.is_file() else None,
            )
        )
    return tuple(result)


def test_private_publication_fresh_success_observer_and_reentry(
    tmp_path: Path,
) -> None:
    case = _build_case(tmp_path)
    stage, destination = _private_publication_paths(case)
    assert (
        private_publication._observe_d7_v1_pre_item23_publication(
            case.context,
            receipt_sha256=case.receipt.canonical_sha256,
        )
        == "absent"
    )

    receipt = _publish_private_case(case)

    assert receipt.destination == destination
    assert receipt.source_commit == case.source_commit
    assert receipt.receipt_sha256 == case.receipt.canonical_sha256
    assert receipt.namespace_atomic is True
    assert receipt.parent_directory_fsync_completed is True
    assert receipt.retry_authorized is False
    assert receipt.cleanup_authorized is False
    assert receipt.authority_granted is False
    assert not stage.exists()
    assert (
        private_publication._observe_d7_v1_pre_item23_publication(
            case.context,
            receipt_sha256=case.receipt.canonical_sha256,
        )
        == "destination-present"
    )
    protocol = materialization._load_d7_v1_materialization_protocol(case.context)
    paths = materialization._expected_stage_files(protocol)
    sources = _private_publication_sources(case)
    assert {
        role: (destination / relative).read_bytes() for role, relative in paths.items()
    } == sources
    before = _tree_snapshot(destination)
    with pytest.raises(private_publication.D7V1PrivatePublicationFailure) as caught:
        _publish_private_case(case)
    assert caught.value.disposition == "destination_collision"
    assert caught.value.stage_path is None
    assert caught.value.stage_retained is None
    assert caught.value.publication_visible is None
    assert caught.value.retry_authorized is False
    assert caught.value.cleanup_authorized is False
    assert _tree_snapshot(destination) == before


@pytest.mark.parametrize("failing_fsync_call", (2, 3))
def test_private_publication_retains_stage_after_create_or_write_fsync_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failing_fsync_call: int,
) -> None:
    case = _build_case(tmp_path)
    stage, destination = _private_publication_paths(case)
    real_fsync = private_publication.os.fsync
    call_count = 0

    def fail_selected_fsync(descriptor: int) -> None:
        nonlocal call_count
        call_count += 1
        if call_count == failing_fsync_call:
            raise OSError(errno.EIO, "injected private-stage fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(private_publication.os, "fsync", fail_selected_fsync)
    with pytest.raises(private_publication.D7V1PrivatePublicationFailure) as caught:
        _publish_private_case(case)
    assert caught.value.disposition == "stage_partial_retained"
    assert caught.value.stage_retained is True
    assert caught.value.publication_visible is False
    assert stage.is_dir()
    assert not destination.exists()
    assert (
        private_publication._observe_d7_v1_pre_item23_publication(
            case.context,
            receipt_sha256=case.receipt.canonical_sha256,
        )
        == "exact-private-stage-present"
    )
    before = _tree_snapshot(stage)

    monkeypatch.setattr(private_publication.os, "fsync", real_fsync)
    with pytest.raises(private_publication.D7V1PrivatePublicationFailure) as second:
        _publish_private_case(case)
    assert second.value.disposition == "stage_collision"
    assert second.value.stage_path is None
    assert second.value.stage_retained is None
    assert second.value.publication_visible is None
    assert second.value.retry_authorized is False
    assert second.value.cleanup_authorized is False
    assert _tree_snapshot(stage) == before


def test_private_publication_preflight_fsync_failure_creates_no_namespace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _build_case(tmp_path)
    stage, destination = _private_publication_paths(case)
    real_fsync = private_publication.os.fsync
    failed = False

    def fail_first_fsync(descriptor: int) -> None:
        nonlocal failed
        if not failed:
            failed = True
            raise OSError(errno.EIO, "injected preflight parent fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(private_publication.os, "fsync", fail_first_fsync)
    with pytest.raises(private_publication.D7V1PrivatePublicationFailure) as caught:
        _publish_private_case(case)
    assert caught.value.disposition == "preflight_rejected"
    assert caught.value.stage_path is None
    assert caught.value.stage_retained is None
    assert caught.value.publication_visible is None
    assert not stage.exists()
    assert not destination.exists()


def test_private_publication_resolves_rename_then_error_by_owned_inode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _build_case(tmp_path)
    stage, destination = _private_publication_paths(case)
    primitive, real_rename = private_publication._native_exclusive_rename()

    def rename_factory() -> tuple[str, private_publication._NativeRename]:
        def rename_then_error(
            parent_fd: int,
            source_leaf: str,
            destination_leaf: str,
        ) -> None:
            real_rename(parent_fd, source_leaf, destination_leaf)
            raise OSError(errno.EIO, "injected ambiguous rename return")

        return primitive, rename_then_error

    monkeypatch.setattr(
        private_publication,
        "_native_exclusive_rename",
        rename_factory,
    )
    receipt = _publish_private_case(case)
    assert receipt.destination == destination
    assert receipt.native_primitive == primitive
    assert destination.is_dir()
    assert not stage.exists()


def test_private_publication_post_rename_destination_swap_is_unknown_not_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _build_case(tmp_path)
    _stage, destination = _private_publication_paths(case)
    primitive, real_rename = private_publication._native_exclusive_rename()
    moved_leaf = f"{destination.name}.moved-after-rename"

    def rename_factory() -> tuple[str, private_publication._NativeRename]:
        def rename_swap_then_interrupt(
            parent_fd: int,
            source_leaf: str,
            destination_leaf: str,
        ) -> None:
            real_rename(parent_fd, source_leaf, destination_leaf)
            os.rename(
                destination_leaf,
                moved_leaf,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
            )
            os.mkdir(destination_leaf, 0o700, dir_fd=parent_fd)
            raise RuntimeError("injected post-rename destination substitution")

        return primitive, rename_swap_then_interrupt

    monkeypatch.setattr(
        private_publication,
        "_native_exclusive_rename",
        rename_factory,
    )
    with pytest.raises(private_publication.D7V1PrivatePublicationFailure) as caught:
        _publish_private_case(case)
    assert caught.value.disposition == "rename_outcome_ambiguous"
    assert caught.value.stage_path is None
    assert caught.value.stage_retained is None
    assert caught.value.publication_visible is None
    assert caught.value.retry_authorized is False
    assert destination.is_dir()
    assert (destination.parent / moved_leaf).is_dir()


def test_private_publication_rename_to_foreign_leaf_is_unknown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _build_case(tmp_path)
    stage, destination = _private_publication_paths(case)
    foreign_leaf = f"{stage.name}.foreign"

    def rename_factory() -> tuple[str, private_publication._NativeRename]:
        def move_to_foreign_leaf_then_error(
            parent_fd: int,
            source_leaf: str,
            destination_leaf: str,
        ) -> None:
            del destination_leaf
            os.rename(
                source_leaf,
                foreign_leaf,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
            )
            raise OSError(errno.EIO, "injected foreign-leaf rename outcome")

        return "test.foreign-leaf-rename", move_to_foreign_leaf_then_error

    monkeypatch.setattr(
        private_publication,
        "_native_exclusive_rename",
        rename_factory,
    )
    with pytest.raises(private_publication.D7V1PrivatePublicationFailure) as caught:
        _publish_private_case(case)
    assert caught.value.disposition == "rename_outcome_ambiguous"
    assert caught.value.stage_path is None
    assert caught.value.stage_retained is None
    assert caught.value.publication_visible is None
    assert not stage.exists()
    assert not destination.exists()
    assert (destination.parent / foreign_leaf).is_dir()


def test_private_publication_reports_visible_but_undurable_after_parent_fsync_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _build_case(tmp_path)
    stage, destination = _private_publication_paths(case)
    primitive, real_rename = private_publication._native_exclusive_rename()
    real_fsync = private_publication.os.fsync
    renamed = False
    failed = False

    def rename_factory() -> tuple[str, private_publication._NativeRename]:
        def mark_rename(
            parent_fd: int,
            source_leaf: str,
            destination_leaf: str,
        ) -> None:
            nonlocal renamed
            real_rename(parent_fd, source_leaf, destination_leaf)
            renamed = True

        return primitive, mark_rename

    def fail_first_post_rename_fsync(descriptor: int) -> None:
        nonlocal failed
        if renamed and not failed:
            failed = True
            raise OSError(errno.EIO, "injected publication-parent fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(
        private_publication,
        "_native_exclusive_rename",
        rename_factory,
    )
    monkeypatch.setattr(
        private_publication.os,
        "fsync",
        fail_first_post_rename_fsync,
    )
    with pytest.raises(private_publication.D7V1PrivatePublicationFailure) as caught:
        _publish_private_case(case)
    assert caught.value.disposition == "published_durability_unknown"
    assert caught.value.publication_visible is True
    assert caught.value.stage_retained is False
    assert caught.value.retry_authorized is False
    assert destination.is_dir()
    assert not stage.exists()
    assert (
        private_publication._observe_d7_v1_pre_item23_publication(
            case.context,
            receipt_sha256=case.receipt.canonical_sha256,
        )
        == "destination-present"
    )


def test_private_publication_refuses_destination_and_stage_collisions(
    tmp_path: Path,
) -> None:
    destination_case = _build_case(tmp_path / "destination")
    _stage, destination = _private_publication_paths(destination_case)
    destination.mkdir()
    with pytest.raises(private_publication.D7V1PrivatePublicationFailure) as collision:
        _publish_private_case(destination_case)
    assert collision.value.disposition == "destination_collision"
    assert collision.value.stage_retained is None
    assert collision.value.publication_visible is None
    assert destination.is_dir()

    stage_case = _build_case(tmp_path / "stage")
    stage, stage_destination = _private_publication_paths(stage_case)
    stage.mkdir()
    with pytest.raises(private_publication.D7V1PrivatePublicationFailure) as partial:
        _publish_private_case(stage_case)
    assert partial.value.disposition == "stage_collision"
    assert partial.value.stage_path is None
    assert partial.value.stage_retained is None
    assert partial.value.publication_visible is None
    assert stage.is_dir()
    assert not stage_destination.exists()

    combined_case = _build_case(tmp_path / "combined")
    combined_stage, combined_destination = _private_publication_paths(combined_case)
    combined_stage.mkdir()
    combined_destination.mkdir()
    with pytest.raises(private_publication.D7V1PrivatePublicationFailure) as combined:
        _publish_private_case(combined_case)
    assert combined.value.disposition == "destination_collision"
    assert combined.value.stage_path is None
    assert combined.value.stage_retained is None
    assert combined.value.publication_visible is None
    assert (
        private_publication._observe_d7_v1_pre_item23_publication(
            combined_case.context,
            receipt_sha256=combined_case.receipt.canonical_sha256,
        )
        == "destination-and-private-stage-present"
    )


def test_private_publication_failure_before_namespace_scan_is_unknown(
    tmp_path: Path,
) -> None:
    case = _build_case(tmp_path)
    _stage, destination = _private_publication_paths(case)
    destination.mkdir()
    (destination / "foreign.json").write_bytes(b"foreign")
    sources = _private_publication_sources(case)
    first_role = sorted(sources)[0]
    sources[first_role] = b"{}"

    with patch.object(
        materialization,
        "_default_external_reader",
        case.external_reader,
    ):
        with pytest.raises(private_publication.D7V1PrivatePublicationFailure) as caught:
            private_publication._publish_d7_v1_pre_item23_records_no_replace(
                case.context,
                sources,
                expected_receipt_sha256=case.receipt.canonical_sha256,
            )
    assert caught.value.disposition == "preflight_rejected"
    assert caught.value.stage_path is None
    assert caught.value.stage_retained is None
    assert caught.value.publication_visible is None
    assert (
        private_publication._observe_d7_v1_pre_item23_publication(
            case.context,
            receipt_sha256=case.receipt.canonical_sha256,
        )
        == "destination-present"
    )


def test_private_publication_failed_stage_recovery_probe_is_unknown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _build_case(tmp_path)
    stage, destination = _private_publication_paths(case)

    def create_root_then_fail(
        parent_fd: int,
        *,
        stage_leaf: str,
        destination_leaf: str,
        paths_by_role: Mapping[str, str],
        sources_by_role: Mapping[str, bytes],
    ) -> private_publication._OwnedStage:
        del destination_leaf, paths_by_role, sources_by_role
        os.mkdir(stage_leaf, 0o700, dir_fd=parent_fd)
        raise OSError(errno.EIO, "injected post-mkdir failure")

    def fail_namespace_observation(
        _parent_fd: int, _leaf: str
    ) -> os.stat_result | None:
        raise OSError(errno.EIO, "injected namespace observation failure")

    monkeypatch.setattr(
        private_publication,
        "_create_owned_stage",
        create_root_then_fail,
    )
    monkeypatch.setattr(
        private_publication,
        "_entry_stat",
        fail_namespace_observation,
    )
    with pytest.raises(private_publication.D7V1PrivatePublicationFailure) as caught:
        _publish_private_case(case)
    assert caught.value.disposition == "stage_creation_state_unknown"
    assert caught.value.stage_path is None
    assert caught.value.stage_retained is None
    assert caught.value.publication_visible is None
    assert stage.is_dir()
    assert not destination.exists()


def test_private_publication_stage_create_collision_is_unknown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _build_case(tmp_path)
    stage, destination = _private_publication_paths(case)

    def collide_at_stage_create(
        parent_fd: int,
        *,
        stage_leaf: str,
        destination_leaf: str,
        paths_by_role: Mapping[str, str],
        sources_by_role: Mapping[str, bytes],
    ) -> private_publication._OwnedStage:
        del destination_leaf, paths_by_role, sources_by_role
        os.mkdir(stage_leaf, 0o700, dir_fd=parent_fd)
        raise FileExistsError(errno.EEXIST, "injected concurrent stage collision")

    monkeypatch.setattr(
        private_publication,
        "_create_owned_stage",
        collide_at_stage_create,
    )
    with pytest.raises(private_publication.D7V1PrivatePublicationFailure) as caught:
        _publish_private_case(case)
    assert caught.value.disposition == "stage_collision_state_unknown"
    assert caught.value.stage_path is None
    assert caught.value.stage_retained is None
    assert caught.value.publication_visible is None
    assert stage.is_dir()
    assert not destination.exists()


@pytest.mark.parametrize("collision_kind", ("file", "symlink"))
def test_private_publication_racing_arbitrary_collision_has_unknown_visibility(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    collision_kind: str,
) -> None:
    case = _build_case(tmp_path)
    stage, destination = _private_publication_paths(case)
    real_open_parent = private_publication._open_publication_parent
    inserted = False

    def open_parent_then_collide(
        repository: RepositoryContext,
        parent_parts: tuple[str, ...],
    ) -> int:
        nonlocal inserted
        descriptor = real_open_parent(repository, parent_parts)
        if not inserted:
            inserted = True
            if collision_kind == "file":
                collision = os.open(
                    destination.name,
                    private_publication._file_create_flags(),
                    0o600,
                    dir_fd=descriptor,
                )
                try:
                    os.write(collision, b"collision")
                finally:
                    os.close(collision)
            else:
                os.symlink(
                    "missing-collision-target",
                    destination.name,
                    dir_fd=descriptor,
                )
        return descriptor

    monkeypatch.setattr(
        private_publication,
        "_open_publication_parent",
        open_parent_then_collide,
    )
    with pytest.raises(private_publication.D7V1PrivatePublicationFailure) as caught:
        _publish_private_case(case)
    assert inserted is True
    assert caught.value.disposition == "destination_collision"
    assert caught.value.stage_path is None
    assert caught.value.stage_retained is None
    assert caught.value.publication_visible is None
    assert not stage.exists()
    if collision_kind == "file":
        assert destination.read_bytes() == b"collision"
    else:
        assert destination.is_symlink()


def test_private_publication_concurrency_has_one_complete_winner(
    tmp_path: Path,
) -> None:
    case = _build_case(tmp_path)
    stage, destination = _private_publication_paths(case)
    sources = _private_publication_sources(case)

    def publish() -> object:
        try:
            return private_publication._publish_d7_v1_pre_item23_records_no_replace(
                case.context,
                sources,
                expected_receipt_sha256=case.receipt.canonical_sha256,
            )
        except private_publication.D7V1PrivatePublicationFailure as error:
            return error

    with patch.object(
        materialization,
        "_default_external_reader",
        case.external_reader,
    ):
        with ThreadPoolExecutor(max_workers=4) as executor:
            outcomes = tuple(executor.map(lambda _index: publish(), range(4)))

    winners = tuple(
        item
        for item in outcomes
        if type(item) is private_publication.D7V1PrivatePublicationReceipt
    )
    losers = tuple(
        item
        for item in outcomes
        if type(item) is private_publication.D7V1PrivatePublicationFailure
    )
    assert len(winners) == 1
    assert len(losers) == 3
    assert all(item.retry_authorized is False for item in losers)
    for loser in losers:
        if "collision" in loser.disposition:
            assert loser.stage_retained is None
            assert loser.publication_visible is None
    assert destination.is_dir()
    assert not stage.exists()


@pytest.mark.parametrize("mutation", ("mode", "bytes", "same-name-replacement"))
def test_private_publication_rejects_owned_member_mutation_before_rename(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    case = _build_case(tmp_path)
    stage_path, destination = _private_publication_paths(case)
    real_revalidate = private_publication._revalidate_owned_stage
    injected = False

    def mutate_then_revalidate(
        stage: private_publication._OwnedStage,
        *,
        paths_by_role: Mapping[str, str],
        sources_by_role: Mapping[str, bytes],
        published: bool,
    ) -> dict[str, bytes]:
        nonlocal injected
        if not injected and not published:
            injected = True
            relative = sorted(stage.file_fds)[0]
            descriptor = stage.file_fds[relative]
            if mutation == "mode":
                os.fchmod(descriptor, 0o640)
            elif mutation == "bytes":
                os.lseek(descriptor, 0, os.SEEK_SET)
                original = os.read(descriptor, 1)
                os.lseek(descriptor, 0, os.SEEK_SET)
                os.write(descriptor, b"x" if original != b"x" else b"y")
                os.fsync(descriptor)
            else:
                parent, leaf = private_publication._path_parent(relative)
                parent_fd = stage.directory_fds[parent]
                moved = f"{leaf}.moved"
                os.rename(
                    leaf,
                    moved,
                    src_dir_fd=parent_fd,
                    dst_dir_fd=parent_fd,
                )
                replacement = os.open(
                    leaf,
                    private_publication._file_create_flags(),
                    0o600,
                    dir_fd=parent_fd,
                )
                try:
                    role = next(
                        role
                        for role, candidate in paths_by_role.items()
                        if candidate == relative
                    )
                    private_publication._write_all(
                        replacement,
                        sources_by_role[role],
                    )
                    os.fsync(replacement)
                finally:
                    os.close(replacement)
                os.unlink(moved, dir_fd=parent_fd)
        return real_revalidate(
            stage,
            paths_by_role=paths_by_role,
            sources_by_role=sources_by_role,
            published=published,
        )

    monkeypatch.setattr(
        private_publication,
        "_revalidate_owned_stage",
        mutate_then_revalidate,
    )
    with pytest.raises(private_publication.D7V1PrivatePublicationFailure) as caught:
        _publish_private_case(case)
    assert injected is True
    assert caught.value.disposition == "stage_partial_retained"
    assert caught.value.stage_retained is True
    assert stage_path.is_dir()
    assert not destination.exists()


def test_private_publication_rejects_live_parent_replacement_before_rename(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _build_case(tmp_path)
    stage, destination = _private_publication_paths(case)
    real_require_anchor = private_publication._require_live_parent_anchor
    moved_parent = destination.parent.with_name(f"{destination.parent.name}-moved")
    injected = False

    def replace_parent_then_require(
        repository: RepositoryContext,
        parent_parts: tuple[str, ...],
        anchored_parent_fd: int,
    ) -> None:
        nonlocal injected
        if not injected:
            injected = True
            live_parent = repository.root.joinpath(*parent_parts)
            live_parent.rename(moved_parent)
            live_parent.mkdir()
        real_require_anchor(repository, parent_parts, anchored_parent_fd)

    monkeypatch.setattr(
        private_publication,
        "_require_live_parent_anchor",
        replace_parent_then_require,
    )
    with pytest.raises(private_publication.D7V1PrivatePublicationFailure) as caught:
        _publish_private_case(case)
    assert injected is True
    assert caught.value.disposition == "namespace_reauthentication_failed"
    assert caught.value.stage_retained is None
    assert caught.value.publication_visible is None
    assert caught.value.stage_path is None
    assert not destination.exists()
    assert (moved_parent / stage.name).is_dir()


def test_private_publication_rejects_equivalent_different_import_origin(
    tmp_path: Path,
) -> None:
    case = _build_case(tmp_path)
    stage, destination = _private_publication_paths(case)
    target = case.repository.joinpath(*PRIVATE_PUBLICATION_REPOSITORY_PATH.split("/"))
    source = target.read_bytes()
    target.unlink()
    target.write_bytes(source)

    with pytest.raises(private_publication.D7V1PrivatePublicationFailure) as caught:
        _publish_private_case(case)
    assert caught.value.disposition == "preflight_rejected"
    assert not stage.exists()
    assert not destination.exists()


def test_private_publication_negative_capability_and_official_paths_untouched() -> None:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    layout = protocol["coordinate_and_member_layout"]
    external = protocol["external_durable_chronology_contract"]
    destination = REPOSITORY.joinpath(*str(layout["repository_root"]).split("/"))
    watched = {
        destination,
        destination.parent
        / f".{destination.name}{private_publication._STAGE_MARKER}{'0' * 64}",
        Path(str(external["route_future_external_coordinates"]["external_store_path"])),
        Path(
            str(external["route_future_external_coordinates"]["external_staging_path"])
        ),
    }
    before = {path: path.exists() or path.is_symlink() for path in watched}
    importlib.reload(private_publication)
    assert {path: path.exists() or path.is_symlink() for path in watched} == before
    assert private_publication.__all__ == ()

    signature = inspect.signature(
        private_publication._publish_d7_v1_pre_item23_records_no_replace
    )
    assert set(signature.parameters) == {
        "repository",
        "sources_by_role",
        "expected_receipt_sha256",
    }
    assert not {
        "stage_root",
        "destination",
        "external_reader",
        "native_rename",
        "supplier",
    } & set(signature.parameters)

    tree = ast.parse(PRIVATE_PUBLICATION_MODULE_PATH.read_text(encoding="utf-8"))
    imported: set[str] = set()
    calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
        elif isinstance(node, ast.Call):
            name = node.func
            parts: list[str] = []
            while isinstance(name, ast.Attribute):
                parts.append(name.attr)
                name = name.value
            if isinstance(name, ast.Name):
                parts.append(name.id)
            calls.add(".".join(reversed(parts)))
    forbidden_import_fragments = {
        "confirmation_attempt_",
        "confirmation_authoritative_start_persistence",
        "confirmation_c1",
        "confirmation_execution_design",
        "confirmation_execution_kernel",
        "confirmation_fused_",
        "confirmation_official_execution",
        "confirmation_preseed_authority",
        "confirmation_seed_supply_contracts",
        "confirmation_source_closure",
        "confirmation_terminal_operations",
    }
    assert not any(
        fragment in module_name
        for module_name in imported
        for fragment in forbidden_import_fragments
    )
    assert not imported & {"torch", "transformers"}
    forbidden_calls = {
        "from_pretrained",
        "load_model",
        "produce_d7_v1_official_result",
        "rmdir",
        "remove",
        "replace",
        "rmtree",
        "unlink",
    }
    assert not any(call.rsplit(".", 1)[-1] in forbidden_calls for call in calls)
