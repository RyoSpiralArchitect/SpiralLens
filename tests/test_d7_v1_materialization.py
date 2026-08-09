from __future__ import annotations

import ast
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import importlib
import inspect
import json
import os
from pathlib import Path
import subprocess
from unittest.mock import patch

import pytest

from spirallens._repository_context import RepositoryContext
from spirallens.core.canonical import sha256_bytes
from spirallens.qualification import confirmation_v1_materialization as materialization
from spirallens.qualification import confirmation_v1_records as records
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
PROTOCOL_PATH = REPOSITORY / "protocols/d7_v1_pre_item23_materialization_v0_1.json"
ROUTE_PATH = REPOSITORY / "protocols/voy_v1_v9_strict_successor_route_v0_1.json"


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


def _source_members(
    repository: Path,
    source_commit: str,
    paths: Sequence[str],
) -> tuple[records.D7V1SourceMember, ...]:
    members: list[records.D7V1SourceMember] = []
    for repository_path in sorted(set(paths)):
        line = _run(repository, "ls-tree", source_commit, "--", repository_path)
        assert line, repository_path
        mode = line.split(maxsplit=1)[0]
        source = subprocess.run(
            (
                "git",
                "-C",
                str(repository),
                "show",
                f"{source_commit}:{repository_path}",
            ),
            check=True,
            capture_output=True,
        ).stdout
        members.append(
            records.D7V1SourceMember(
                repository_path=repository_path,
                git_mode=mode,
                sha256=sha256_bytes(source),
                byte_count=len(source),
            )
        )
    return tuple(members)


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
    protocol: Mapping[str, object],
    route: Mapping[str, object],
    source_commit: str,
    source_members: Sequence[records.D7V1SourceMember],
) -> dict[str, records._D7V1CanonicalRecord]:
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

    external_contract = protocol["external_durable_chronology_contract"]
    assert isinstance(external_contract, dict)
    claim_contract = external_contract["seed_supply_claim"]
    attempt_contract = external_contract["attempt_reservation"]
    route_external = external_contract["route_future_external_coordinates"]
    assert isinstance(claim_contract, dict)
    assert isinstance(attempt_contract, dict)
    assert isinstance(route_external, dict)
    supplier_identity = _external("supplier-identity", "5")
    claim = records.D7V1ExclusiveSeedSupplyClaim.create(
        record_id="d7-v1-test-seed-claim",
        repository_path=paths[records.D7V1ExclusiveSeedSupplyClaim.artifact_role],
        c2=c2,
        supplier_identity_binding=supplier_identity,
        supplier_id="test-local-csprng",
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
        supplier_id="test-local-csprng",
        seeds=(8_100_001, 8_100_002),
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
    return {
        record.artifact_role: record
        for record in (*predecessor_records, receipt, result)
    }


@dataclass(slots=True)
class _Case:
    repository: Path
    context: RepositoryContext
    source_commit: str
    stage_root: Path
    protocol: dict[str, object]
    records_by_role: dict[str, records._D7V1CanonicalRecord]
    external_bytes: dict[Path, bytes]

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
    mutate_source_member: Callable[
        [tuple[records.D7V1SourceMember, ...]],
        tuple[records.D7V1SourceMember, ...],
    ]
    | None = None,
) -> _Case:
    repository = tmp_path / "repository"
    subprocess.run(
        (
            "git",
            "clone",
            "--quiet",
            "--shared",
            "--no-checkout",
            str(REPOSITORY),
            str(repository),
        ),
        check=True,
    )
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
    for path_value in required:
        repository_path = str(path_value)
        target = repository.joinpath(*repository_path.split("/"))
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
    _run(repository, "commit", "--quiet", "-m", "test source S")
    source_commit = _run(repository, "rev-parse", "HEAD")

    source_paths = [
        *map(str, required),
        str(protocol["route_binding"]["repository_path"]),
    ]
    members = _source_members(repository, source_commit, source_paths)
    if mutate_source_member is not None:
        members = mutate_source_member(members)
    records_by_role = _build_records(
        protocol=protocol,
        route=route,
        source_commit=source_commit,
        source_members=members,
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
        context=RepositoryContext(root=repository.resolve()),
        source_commit=source_commit,
        stage_root=stage_root,
        protocol=protocol,
        records_by_role=records_by_role,
        external_bytes=external_bytes,
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


def _commit_b(case: _Case, *, extra_delta: bool = False) -> str:
    result_path = str(
        case.protocol["coordinate_and_member_layout"]["descriptive_result"]
    )
    _write(case.repository, result_path, case.result.canonical_bytes)
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
    commit_b = _commit_b(case)
    verified_b = _verify_commit_b(case, commit_a, commit_b)
    assert isinstance(verified_b, materialization.D7V1CommitVerification)


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


def test_read_only_verifier_boundary_is_projected_without_api_promotion() -> None:
    readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")
    roadmap = (REPOSITORY / "docs/ROADMAP.md").read_text(encoding="utf-8")
    ledger = (REPOSITORY / "docs/EXPERIMENT_INTERPRETATION_LEDGER.md").read_text(
        encoding="utf-8"
    )
    changelog = (REPOSITORY / "docs/SCHEMA_CHANGELOG.md").read_text(encoding="utf-8")

    assert "non-exported, read-only verifier" in readme
    assert "caller-owned stage cannot close the validate-to-rename race" in roadmap
    assert "### 3.17 D7 v1 read-only materialization verification kernel" in ledger
    assert "## 2026-08-10 — D7 v1 read-only joined verifier" in changelog
    assert "No publisher is provided." in changelog
