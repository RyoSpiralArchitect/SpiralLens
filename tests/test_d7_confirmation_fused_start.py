from __future__ import annotations

import inspect
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import test_d7_confirmation_fused_authority as authority_repository_fixtures
import test_d7_confirmation_result_components as component_fixtures
from spirallens import qualification
from spirallens.core.canonical import canonical_json_bytes, sha256_bytes
from spirallens.qualification import confirmation_attempt_records as records
from spirallens.qualification import (
    confirmation_attempt_terminal_persistence as terminal_persistence,
)
from spirallens.qualification import (
    confirmation_authoritative_start_persistence as start_persistence,
)
from spirallens.qualification import confirmation_fused_start as fused_start
from spirallens.qualification import confirmation_runner as runner
from spirallens.qualification.common import QualificationContractError
from test_d7_confirmation_attempt_persistence import _h, _persist, _prefix


@pytest.fixture(scope="module")
def component_bundle() -> component_fixtures._Bundle:
    return component_fixtures.bundle.__wrapped__()


def _snapshot(
    values: SimpleNamespace,
    *,
    head_commit: str = "a" * 40,
    descriptor_label: str = "stable",
) -> SimpleNamespace:
    member_sha256 = {
        "launch-authority-input-bundle": _h(f"bundle-{descriptor_label}-{head_commit}"),
        "replay-target": values.declaration.replay_target_sha256,
        "launch-intent": values.declaration.launch_intent_sha256,
        "execution-source-runtime-closure": _h("source-runtime-closure"),
        "runtime-specification": values.authorization.runtime_specification_sha256,
        "family-admission": _h("family-admission"),
        "execution-identity": values.declaration.execution_identity_receipt_sha256,
        "physical-store-lane-identity": _h("physical-identity"),
        "full-design-freeze": (values.authorization.full_design_freeze_receipt_sha256),
    }
    inventory = tuple(
        fused_start.fused_authority._D7FusedAuthorityMember(
            artifact_role=role,
            artifact_contract_id=contract_id,
            repository_path=f"authority/{index:02d}-{role}.json",
            canonical_sha256=member_sha256[role],
            byte_count=1,
        )
        for index, (role, contract_id, _attribute, _record_type) in enumerate(
            fused_start.fused_authority._MEMBER_SPECS
        )
    )
    descriptor = fused_start.fused_authority._D7FusedAuthorityLaunchDescriptor(
        descriptor_id=f"test-{descriptor_label}",
        descriptor_repository_path="authority/raw-launch-descriptor.json",
        inventory=inventory,
    )
    replay_target = SimpleNamespace(
        full_design_binding=SimpleNamespace(
            inventory_sha256=component_fixtures._INVENTORY
        ),
        aggregation_binding=SimpleNamespace(
            canonical_sha256=component_fixtures._AGGREGATION
        ),
        result_payload_schema_binding=SimpleNamespace(
            canonical_sha256=(records.D7_SCIENTIFIC_RESULT_IMPLEMENTATION_SCHEMA_SHA256)
        ),
    )
    return SimpleNamespace(
        head_commit=head_commit,
        descriptor=descriptor,
        bundle=SimpleNamespace(
            canonical_sha256=member_sha256["launch-authority-input-bundle"]
        ),
        physical_identity=SimpleNamespace(store_path=str(values.store)),
        replay_target=replay_target,
        authority_member_sha256=member_sha256,
    )


def _verification(
    snapshot: SimpleNamespace,
    *,
    attempt_key_sha256: str,
) -> fused_start._D7FusedStartVerificationEvidence:
    return fused_start._D7FusedStartVerificationEvidence(
        descriptor_sha256=snapshot.descriptor.canonical_sha256,
        launch_bundle_sha256=snapshot.bundle.canonical_sha256,
        repository_head_commit=snapshot.head_commit,
        canonical_origin_observation_sha256=_h("canonical-origin-observation"),
        replay_target_sha256=snapshot.authority_member_sha256["replay-target"],
        launch_intent_sha256=snapshot.authority_member_sha256["launch-intent"],
        source_runtime_closure_sha256=snapshot.authority_member_sha256[
            "execution-source-runtime-closure"
        ],
        runtime_specification_sha256=snapshot.authority_member_sha256[
            "runtime-specification"
        ],
        family_admission_sha256=snapshot.authority_member_sha256["family-admission"],
        execution_identity_sha256=snapshot.authority_member_sha256[
            "execution-identity"
        ],
        physical_identity_sha256=snapshot.authority_member_sha256[
            "physical-store-lane-identity"
        ],
        full_design_freeze_sha256=snapshot.authority_member_sha256[
            "full-design-freeze"
        ],
        source_tree_sha256=_h("source-tree"),
        transitive_dependency_set_sha256=_h("dependency-set"),
        callable_identity_sha256=_h("callable-identity"),
        process_identity_sha256=_h("process-identity"),
        attempt_key_sha256=attempt_key_sha256,
    )


def _verified(
    values: SimpleNamespace,
    snapshot: SimpleNamespace,
) -> fused_start._VerifiedD7StartInputs:
    return fused_start._VerifiedD7StartInputs(
        snapshot=snapshot,
        origin=object(),
        runtime=object(),
        declaration=values.declaration,
        authorization_output_receipt=values.authorization_output,
        authorization_terminal_receipt=values.authorization_terminal,
        authorization=values.authorization,
        claim=values.claim,
        pre_start_output_receipt=values.pre_start_output,
        pre_start_terminal_receipt=values.pre_start_terminal,
        start=values.start,
        verification=_verification(
            snapshot,
            attempt_key_sha256=values.start.attempt_key_sha256,
        ),
        _factory_token=fused_start._VERIFIED_INPUT_FACTORY_TOKEN,
    )


def _context(
    directory: Path,
    *,
    head_commit: str = "a" * 40,
    descriptor_label: str = "stable",
) -> SimpleNamespace:
    directory.mkdir(parents=True, exist_ok=True)
    values = _prefix(directory)
    lane = directory / start_persistence.D7_AUTHORITATIVE_START_LANE_BASENAME
    lane.mkdir(mode=0o700)
    snapshot = _snapshot(
        values,
        head_commit=head_commit,
        descriptor_label=descriptor_label,
    )
    return SimpleNamespace(
        values=values,
        lane=lane,
        snapshot=snapshot,
        verified=_verified(values, snapshot),
        descriptor_path=directory / "raw-launch-descriptor.json",
    )


def _patch_stable_handoff(
    monkeypatch: pytest.MonkeyPatch,
    context: SimpleNamespace,
) -> None:
    def load_snapshot(_descriptor_path: object) -> SimpleNamespace:
        return context.snapshot

    def verify_snapshot(
        snapshot: SimpleNamespace,
        _producer: object,
    ) -> fused_start._VerifiedD7StartInputs:
        assert snapshot is context.snapshot
        return context.verified

    monkeypatch.setattr(
        fused_start.fused_authority,
        "load_d7_fused_authority_snapshot",
        load_snapshot,
    )
    monkeypatch.setattr(
        fused_start,
        "_verify_and_derive_start_inputs",
        verify_snapshot,
    )


def _producer_output(
    bundle: component_fixtures._Bundle,
) -> runner.D7ScientificProducerOutput:
    return runner.D7ScientificProducerOutput(
        event_ledger=bundle.event,
        core_cells=bundle.core,
        loop_cells=bundle.loop,
        primary_units=bundle.primary,
        required_strata=bundle.strata,
        aggregate_gates=bundle.gates,
        result_payload=bundle.result,
    )


def _only_start_path(context: SimpleNamespace) -> Path:
    paths = tuple(context.lane.glob("*.authoritative-start"))
    assert len(paths) == 1
    return paths[0]


def _load_start(
    context: SimpleNamespace,
) -> start_persistence.D7LoadedAuthoritativeStartTransaction:
    start_path = _only_start_path(context)
    manifest_source = (
        start_path / start_persistence.D7_AUTHORITATIVE_START_MANIFEST_FILENAME
    ).read_bytes()
    return start_persistence.load_d7_authoritative_start_transaction(
        context.values.store,
        attempt_key_sha256=context.values.start.attempt_key_sha256,
        expected_manifest_sha256=sha256_bytes(manifest_source),
    )


def _terminal_path(context: SimpleNamespace) -> Path:
    receipt = context.values.pre_start_terminal
    return Path(receipt.resolved_parent_realpath) / receipt.subject_basename


def _assert_visible_start_with_terminal_absent(context: SimpleNamespace) -> None:
    assert _only_start_path(context).is_dir()
    assert not _terminal_path(context).exists()


def test_surface_accepts_only_raw_descriptor_and_callback_and_stays_private() -> None:
    operation = fused_start.run_d7_fused_verify_start_and_terminal_no_replace
    signature = inspect.signature(operation)

    assert tuple(signature.parameters) == ("descriptor_path", "scientific_producer")
    assert all(
        parameter.kind is inspect.Parameter.POSITIONAL_ONLY
        for parameter in signature.parameters.values()
    )
    for forbidden in (
        "authorization_token",
        "ownership",
        "launch_authorization",
        "preverified_receipt",
        "seed",
        "supplier",
        "start",
        "trust_root",
    ):
        assert forbidden not in signature.parameters
        with pytest.raises(TypeError):
            signature.bind("descriptor.json", lambda: None, **{forbidden: object()})

    assert fused_start.__all__ == ()
    assert operation.__name__ not in qualification.__all__
    assert not hasattr(qualification, operation.__name__)
    assert not hasattr(qualification, "_VerifiedD7StartInputs")


def test_verification_evidence_limits_positive_authority_to_same_call_scope(
    tmp_path: Path,
) -> None:
    evidence = _context(tmp_path).verified.verification.to_dict()

    assert evidence["verification_scope"] == (
        "canonical-origin-main-clean-head-declared-runtime-and-physical-v0.1"
    )
    for name in (
        "descriptor_and_members_reopened",
        "canonical_origin_main_live_reobserved",
        "declared_source_runtime_surface_matched",
        "declared_execution_identity_fields_matched",
        "physical_identity_live_reobserved",
        "authorization_absence_observed",
        "pre_start_absence_observed",
        "canonical_repository_transition_checks_satisfied",
    ):
        assert evidence[name] is True
    for name in (
        "reusable_authorization_capability_present",
        "caller_authorization_token_accepted",
        "execution_observed",
        "scientific_claim_eligible",
        "d7_result_produced",
        "d8_execution_authorized",
        "persisted_replay_reauthenticates_live_observations",
        "all_live_observation_digests_semantically_rejoined",
    ):
        assert evidence[name] is False


@pytest.mark.parametrize(
    "mutation",
    (
        "unknown-field",
        "missing-field",
        "wrong-boolean-type",
        "wrong-digest",
        "wrong-scope",
        "wrong-commit-type",
        "noncanonical-bytes",
    ),
)
def test_verification_evidence_has_strict_canonical_replay_parser(
    tmp_path: Path,
    mutation: str,
) -> None:
    evidence = _context(tmp_path).verified.verification
    replayed = fused_start._D7FusedStartVerificationEvidence.from_canonical_bytes(
        evidence.canonical_bytes,
        expected_sha256=evidence.canonical_sha256,
    )
    assert replayed == evidence

    document = evidence.to_dict()
    if mutation == "unknown-field":
        document["unknown"] = False
    elif mutation == "missing-field":
        document.pop("attempt_key_sha256")
    elif mutation == "wrong-boolean-type":
        document["execution_observed"] = 0
    elif mutation == "wrong-digest":
        document["source_tree_sha256"] = "A" * 64
    elif mutation == "wrong-scope":
        document["verification_scope"] = "broader-authority"
    elif mutation == "wrong-commit-type":
        document["repository_head_commit"] = 7

    source = canonical_json_bytes(document)
    if mutation == "noncanonical-bytes":
        source += b"\n"
    with pytest.raises(QualificationContractError):
        fused_start._D7FusedStartVerificationEvidence.from_canonical_bytes(
            source,
            expected_sha256=sha256_bytes(source),
        )

    class MappingSubclass(dict[str, object]):
        pass

    with pytest.raises(QualificationContractError, match="exact JSON object"):
        fused_start._D7FusedStartVerificationEvidence.from_dict(
            MappingSubclass(evidence.to_dict())
        )


def test_source_runtime_tree_is_closed_against_later_tracked_members(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "source-repository"
    package = repository / "src" / "spirallens"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("__version__ = '0.0.0'\n", encoding="utf-8")
    (repository / "pyproject.toml").write_text(
        '[project]\nname = "spirallens-test"\nversion = "0.0.0"\n',
        encoding="utf-8",
    )
    (repository / fused_start.D7_RUNTIME_LOCK_REPOSITORY_PATH).write_text(
        "spirallens-test==0.0.0\n",
        encoding="utf-8",
    )
    fused_start._git(repository, "init", "-q")
    fused_start._git(repository, "config", "user.name", "SpiralLens Test")
    fused_start._git(
        repository,
        "config",
        "user.email",
        "spirallens@example.invalid",
    )
    fused_start._git(repository, "add", "--", ".")
    fused_start._git(repository, "commit", "-q", "-m", "freeze source")
    source_commit = (
        fused_start._git(repository, "rev-parse", "HEAD").stdout.decode("ascii").strip()
    )

    first = fused_start._source_tree_sha256(repository, source_commit)
    assert len(first) == 64

    (package / "later.py").write_text("LATER = True\n", encoding="utf-8")
    fused_start._git(repository, "add", "--", "src/spirallens/later.py")
    fused_start._git(repository, "commit", "-q", "-m", "later source")
    with pytest.raises(QualificationContractError, match="inventory differs"):
        fused_start._source_tree_sha256(repository, source_commit)


@pytest.mark.parametrize(
    "store_relation",
    ("same-as-repository", "inside-repository", "contains-repository"),
)
def test_attempt_store_must_be_tree_disjoint_from_repository(
    tmp_path: Path,
    store_relation: str,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    if store_relation == "same-as-repository":
        store = repository
    elif store_relation == "inside-repository":
        store = repository / "attempt-store"
        store.mkdir()
    else:
        store = tmp_path
    physical = SimpleNamespace(store_path=str(store))

    with pytest.raises(QualificationContractError, match="Git repository"):
        fused_start._verify_store_and_lane(repository, physical)


@pytest.mark.parametrize(
    "store_relation",
    ("same-as-repository", "inside-repository", "contains-repository"),
)
def test_case_variant_paths_cannot_bypass_physical_tree_disjointness(
    tmp_path: Path,
    store_relation: str,
) -> None:
    case_root = tmp_path / "CaseBoundary"
    case_root.mkdir()
    case_alias = tmp_path / "caseboundary"
    if not case_alias.is_dir() or not os.path.samefile(case_root, case_alias):
        pytest.skip("test requires a case-insensitive filesystem")

    if store_relation == "same-as-repository":
        repository = case_root
        store = case_alias
    elif store_relation == "inside-repository":
        repository = case_root
        store = case_root / "AttemptStore"
        store.mkdir()
        store = case_alias / "attemptstore"
    else:
        repository = case_root / "Repository"
        repository.mkdir()
        store = case_alias
        repository = case_root / "repository"

    assert store.is_dir()
    physical = SimpleNamespace(store_path=str(store))
    with pytest.raises(QualificationContractError, match="Git repository"):
        fused_start._verify_store_and_lane(repository, physical)


@pytest.mark.parametrize("case_variant", (False, True))
def test_physically_disjoint_sibling_trees_are_accepted(
    tmp_path: Path,
    case_variant: bool,
) -> None:
    repository_named = tmp_path / "RepositoryRoot"
    store_named = tmp_path / "AttemptStore"
    repository_named.mkdir()
    store_named.mkdir()
    lane_named = store_named / start_persistence.D7_AUTHORITATIVE_START_LANE_BASENAME
    lane_named.mkdir()
    repository = repository_named
    store = store_named
    if case_variant:
        repository = tmp_path / "repositoryroot"
        store = tmp_path / "attemptstore"
        if (
            not repository.is_dir()
            or not store.is_dir()
            or not os.path.samefile(repository_named, repository)
            or not os.path.samefile(store_named, store)
        ):
            pytest.skip("test requires a case-insensitive filesystem")
    lane = store / start_persistence.D7_AUTHORITATIVE_START_LANE_BASENAME
    store_status = store.stat()
    lane_status = lane.stat()
    physical = SimpleNamespace(
        store_path=str(store),
        store_device=store_status.st_dev,
        store_inode=store_status.st_ino,
        lane_path=str(lane),
        lane_device=lane_status.st_dev,
        lane_inode=lane_status.st_ino,
    )

    fused_start._verify_store_and_lane(repository, physical)


def test_physical_ancestry_walk_errors_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    directory = tmp_path / "directory"
    directory.mkdir()
    anchor = fused_start.p._open_real_directory(directory, label="test directory")
    original_open = fused_start.os.open

    def fail_parent_open(path: object, *args: object, **kwargs: object) -> int:
        if path == "..":
            raise OSError("simulated ancestry traversal failure")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(fused_start.os, "open", fail_parent_open)
    try:
        with pytest.raises(
            QualificationContractError,
            match="cannot traverse test directory physical ancestry",
        ):
            fused_start._physical_directory_ancestry(
                anchor,
                label="test directory",
            )
    finally:
        os.close(anchor.descriptor)


def test_real_start_record_derivation_rejoins_typed_snapshot_with_leaf_observers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository = authority_repository_fixtures._build_repository(tmp_path)
    snapshot = fused_start.fused_authority.load_d7_fused_authority_snapshot(
        repository.descriptor_path
    )
    physical = snapshot.physical_identity
    runtime = fused_start._RuntimeObservation(
        source_tree_sha256=snapshot.source_runtime_closure.source_tree_sha256,
        dependency_lock_sha256=(snapshot.runtime_specification.dependency_lock_sha256),
        transitive_dependency_set_sha256=(
            snapshot.source_runtime_closure.transitive_dependency_set_sha256
        ),
        native_runtime_sha256=snapshot.runtime_specification.native_runtime_sha256,
    )
    execution = fused_start._ExecutionObservation(
        executable_sha256=snapshot.execution_identity.executable_sha256,
        callable_identity_sha256=(snapshot.execution_identity.callable_identity_sha256),
        process_identity_sha256=snapshot.execution_identity.process_identity_sha256,
    )
    origin = fused_start._CanonicalOriginObservation(
        origin_url="https://github.com/RyoSpiralArchitect/SpiralLens.git",
        branch_name="main",
        local_head_commit=snapshot.head_commit,
        remote_main_commit=snapshot.head_commit,
    )

    monkeypatch.setattr(fused_start, "_observe_canonical_origin", lambda _value: origin)
    monkeypatch.setattr(fused_start, "_observe_runtime", lambda _value: runtime)
    monkeypatch.setattr(
        fused_start,
        "_observe_execution",
        lambda _value, _producer: execution,
    )
    monkeypatch.setattr(
        fused_start,
        "_verify_store_and_lane",
        lambda _root, _physical: None,
    )

    def observe_absence(
        observed_physical: object,
        subject_kind: fused_start.e.D7AbsentPathSubject,
    ) -> fused_start._AbsentSubjectObservation:
        assert observed_physical is physical
        is_output = subject_kind is fused_start.e.D7AbsentPathSubject.OUTPUT_NAMESPACE
        path = Path(
            physical.output_namespace_path if is_output else physical.terminal_path
        )
        parent_device, parent_inode = (
            (physical.output_parent_device, physical.output_parent_inode)
            if is_output
            else (physical.terminal_parent_device, physical.terminal_parent_inode)
        )
        return fused_start._AbsentSubjectObservation(
            subject_kind=subject_kind,
            resolved_parent_realpath=str(path.parent),
            subject_basename=path.name,
            parent_device=parent_device,
            parent_inode=parent_inode,
            subject_path_identity_sha256=fused_start.e.d7_path_identity_sha256(
                store_identity_sha256=physical.store_identity_sha256,
                resolved_parent_realpath=str(path.parent),
                subject_basename=path.name,
            ),
        )

    monkeypatch.setattr(fused_start, "_observe_absent_subject", observe_absence)

    def scientific_producer() -> runner.D7ScientificProducerOutput:
        raise AssertionError("derivation must not invoke the producer")

    verified = fused_start._verify_and_derive_start_inputs(
        snapshot,
        scientific_producer,
    )

    assert verified.declaration.replay_target_sha256 == (
        snapshot.replay_target.canonical_sha256
    )
    assert verified.authorization_output_receipt.subject_kind is (
        fused_start.e.D7AbsentPathSubject.OUTPUT_NAMESPACE
    )
    assert verified.authorization_terminal_receipt.subject_kind is (
        fused_start.e.D7AbsentPathSubject.TERMINAL_PATH
    )
    assert (
        verified.authorization.authorization_output_namespace_absence_receipt_sha256
        == (verified.authorization_output_receipt.canonical_sha256)
    )
    assert (
        verified.authorization.authorization_terminal_path_absence_receipt_sha256
        == (verified.authorization_terminal_receipt.canonical_sha256)
    )
    assert verified.start.pre_start_output_namespace_absence_receipt_sha256 == (
        verified.pre_start_output_receipt.canonical_sha256
    )
    assert verified.start.pre_start_terminal_path_absence_receipt_sha256 == (
        verified.pre_start_terminal_receipt.canonical_sha256
    )
    assert verified.verification.descriptor_sha256 == (
        snapshot.descriptor.canonical_sha256
    )
    assert verified.verification.source_tree_sha256 == runtime.source_tree_sha256
    assert verified.verification.callable_identity_sha256 == (
        execution.callable_identity_sha256
    )


def test_same_call_handoff_persists_actual_start_runs_and_publishes_terminal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    component_bundle: component_fixtures._Bundle,
) -> None:
    context = _context(tmp_path)
    evidence_prefix = _persist(context.values)
    _patch_stable_handoff(monkeypatch, context)
    calls = 0

    def scientific_producer() -> runner.D7ScientificProducerOutput:
        nonlocal calls
        calls += 1
        return _producer_output(component_bundle)

    identity = fused_start.run_d7_fused_verify_start_and_terminal_no_replace(
        context.descriptor_path,
        scientific_producer,
    )
    loaded_start = _load_start(context)
    loaded_terminal = terminal_persistence.load_d7_structural_terminal_transaction(
        loaded_start,
        expected_manifest_sha256=identity.terminal_manifest_sha256,
        expected_consumption_sha256=identity.terminal_consumption_sha256,
    )

    assert calls == 1
    assert (
        identity.terminal_artifact_kind
        is records.D7TerminalArtifactKind.SCIENTIFIC_RESULT
    )
    assert identity.parent_directory_fsync_proved is True
    assert loaded_start.start == context.values.start
    assert (
        loaded_start.immutable_member_sources[
            start_persistence.D7_LAUNCH_AUTHORITY_SOURCE_ENVELOPE_FILENAME
        ]
        == context.snapshot.descriptor.canonical_bytes
    )
    assert (
        loaded_start.immutable_member_sources[
            start_persistence.D7_AUTHORITY_VERIFICATION_EVIDENCE_FILENAME
        ]
        == context.verified.verification.canonical_bytes
    )
    assert loaded_terminal.terminal_artifact.canonical_sha256 == (
        identity.terminal_artifact_sha256
    )
    assert loaded_terminal.manifest.authoritative_start_manifest_sha256 == (
        loaded_start.manifest.canonical_sha256
    )
    assert (
        loaded_terminal.manifest.authoritative_start_directory_identity_sha256
        == loaded_start.directory_identity_sha256
    )
    assert loaded_terminal.manifest.authority_verification_evidence_sha256 == (
        loaded_start.verification_evidence_binding.canonical_sha256
    )
    with pytest.raises(
        QualificationContractError,
        match="authoritative-start lineage differs",
    ):
        terminal_persistence.load_d7_structural_terminal_transaction(
            evidence_prefix,
            expected_manifest_sha256=identity.terminal_manifest_sha256,
            expected_consumption_sha256=identity.terminal_consumption_sha256,
        )


def test_visible_start_rejects_sequential_retry_without_second_callback_or_replace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    _patch_stable_handoff(monkeypatch, context)
    calls = 0

    class SimulatedHardExit(BaseException):
        pass

    original = SimulatedHardExit("stop after callback entry")

    def scientific_producer() -> runner.D7ScientificProducerOutput:
        nonlocal calls
        calls += 1
        raise original

    with pytest.raises(SimulatedHardExit) as caught:
        fused_start.run_d7_fused_verify_start_and_terminal_no_replace(
            context.descriptor_path,
            scientific_producer,
        )
    assert caught.value is original
    manifest_path = (
        _only_start_path(context)
        / start_persistence.D7_AUTHORITATIVE_START_MANIFEST_FILENAME
    )
    original_manifest = manifest_path.read_bytes()

    with pytest.raises(QualificationContractError, match="replace existing"):
        fused_start.run_d7_fused_verify_start_and_terminal_no_replace(
            context.descriptor_path,
            scientific_producer,
        )

    assert calls == 1
    assert manifest_path.read_bytes() == original_manifest
    _assert_visible_start_with_terminal_absent(context)


def test_concurrent_calls_have_one_callback_and_one_no_replace_winner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    component_bundle: component_fixtures._Bundle,
) -> None:
    context = _context(tmp_path)
    initial_load_barrier = threading.Barrier(8)
    thread_state = threading.local()
    call_lock = threading.Lock()
    calls = 0

    def load_snapshot(_descriptor_path: object) -> SimpleNamespace:
        if not getattr(thread_state, "initial_load_complete", False):
            thread_state.initial_load_complete = True
            initial_load_barrier.wait(timeout=10)
        return context.snapshot

    def verify_snapshot(
        snapshot: SimpleNamespace,
        _producer: object,
    ) -> fused_start._VerifiedD7StartInputs:
        assert snapshot is context.snapshot
        return context.verified

    monkeypatch.setattr(
        fused_start.fused_authority,
        "load_d7_fused_authority_snapshot",
        load_snapshot,
    )
    monkeypatch.setattr(
        fused_start,
        "_verify_and_derive_start_inputs",
        verify_snapshot,
    )

    def scientific_producer() -> runner.D7ScientificProducerOutput:
        nonlocal calls
        with call_lock:
            calls += 1
        return _producer_output(component_bundle)

    def invoke() -> object:
        try:
            return fused_start.run_d7_fused_verify_start_and_terminal_no_replace(
                context.descriptor_path,
                scientific_producer,
            )
        except QualificationContractError as error:
            return error

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = tuple(executor.map(lambda _index: invoke(), range(8)))

    winners = tuple(
        outcome
        for outcome in outcomes
        if type(outcome) is terminal_persistence.D7PersistedStructuralTerminalIdentity
    )
    losers = tuple(
        outcome for outcome in outcomes if type(outcome) is QualificationContractError
    )
    assert len(winners) == 1
    assert len(losers) == 7
    assert calls == 1
    assert _only_start_path(context).is_dir()
    assert _terminal_path(context).is_dir()


def test_post_start_revalidation_drift_leaves_visible_start_and_zero_callbacks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    drifted_snapshot = _snapshot(
        context.values,
        head_commit="b" * 40,
        descriptor_label="drifted",
    )
    drifted_verified = _verified(context.values, drifted_snapshot)
    observations = iter((context.snapshot, drifted_snapshot))
    calls = 0

    monkeypatch.setattr(
        fused_start.fused_authority,
        "load_d7_fused_authority_snapshot",
        lambda _descriptor_path: next(observations),
    )

    def verify_snapshot(
        snapshot: SimpleNamespace,
        _producer: object,
    ) -> fused_start._VerifiedD7StartInputs:
        if snapshot is context.snapshot:
            return context.verified
        assert snapshot is drifted_snapshot
        return drifted_verified

    monkeypatch.setattr(
        fused_start,
        "_verify_and_derive_start_inputs",
        verify_snapshot,
    )

    def scientific_producer() -> runner.D7ScientificProducerOutput:
        nonlocal calls
        calls += 1
        raise AssertionError("callback must remain unreachable")

    with pytest.raises(QualificationContractError, match="changed at transition"):
        fused_start.run_d7_fused_verify_start_and_terminal_no_replace(
            context.descriptor_path,
            scientific_producer,
        )

    assert calls == 0
    _assert_visible_start_with_terminal_absent(context)


def test_start_reload_failure_before_callback_leaves_visible_start(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    _patch_stable_handoff(monkeypatch, context)
    loads = 0
    calls = 0

    def fail_transition_load(*args: object, **kwargs: object) -> object:
        del args, kwargs
        nonlocal loads
        loads += 1
        raise QualificationContractError("simulated start replacement")

    monkeypatch.setattr(
        start_persistence,
        "load_d7_authoritative_start_transaction",
        fail_transition_load,
    )

    def scientific_producer() -> runner.D7ScientificProducerOutput:
        nonlocal calls
        calls += 1
        raise AssertionError("callback must remain unreachable")

    with pytest.raises(QualificationContractError, match="start replacement"):
        fused_start.run_d7_fused_verify_start_and_terminal_no_replace(
            context.descriptor_path,
            scientific_producer,
        )

    assert loads == 1
    assert calls == 0
    _assert_visible_start_with_terminal_absent(context)


def test_unproved_start_parent_fsync_leaves_visible_start_and_zero_callbacks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    _patch_stable_handoff(monkeypatch, context)
    monkeypatch.setattr(
        start_persistence,
        "_fsync_published_parent",
        lambda _lane: False,
    )
    calls = 0

    def scientific_producer() -> runner.D7ScientificProducerOutput:
        nonlocal calls
        calls += 1
        raise AssertionError("callback must remain unreachable")

    with pytest.raises(QualificationContractError, match="durability is unproved"):
        fused_start.run_d7_fused_verify_start_and_terminal_no_replace(
            context.descriptor_path,
            scientific_producer,
        )

    assert calls == 0
    _assert_visible_start_with_terminal_absent(context)


def test_ordinary_exception_publishes_failed_terminal_and_reraises_same_object(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    _patch_stable_handoff(monkeypatch, context)
    original = RuntimeError("scientific producer failed")
    calls = 0

    def scientific_producer() -> runner.D7ScientificProducerOutput:
        nonlocal calls
        calls += 1
        raise original

    with pytest.raises(RuntimeError) as caught:
        fused_start.run_d7_fused_verify_start_and_terminal_no_replace(
            context.descriptor_path,
            scientific_producer,
        )

    assert caught.value is original
    assert calls == 1
    assert not hasattr(
        caught.value,
        runner.D7_PREPARED_FAILED_TERMINAL_ATTRIBUTE,
    )
    loaded_start = _load_start(context)
    terminal_path = _terminal_path(context)
    manifest_source = (
        terminal_path / records.D7_TERMINAL_MANIFEST_FILENAME
    ).read_bytes()
    manifest = records.D7TerminalManifestRecord.from_canonical_bytes(
        manifest_source,
        expected_sha256=sha256_bytes(manifest_source),
    )
    consumption_source = (
        terminal_path / records.D7_TERMINAL_CONSUMPTION_FILENAME
    ).read_bytes()
    loaded_terminal = terminal_persistence.load_d7_structural_terminal_transaction(
        loaded_start,
        expected_manifest_sha256=manifest.canonical_sha256,
        expected_consumption_sha256=sha256_bytes(consumption_source),
    )
    assert loaded_terminal.manifest.terminal_artifact_kind is (
        records.D7TerminalArtifactKind.FAILED_ATTEMPT
    )
    assert loaded_terminal.terminal_artifact.failure_stage is (
        records.D7FailureStage.EXECUTION_KERNEL
    )


def test_ordinary_exception_adds_unproved_failed_terminal_note_when_supported(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    _patch_stable_handoff(monkeypatch, context)
    original_publish = (
        fused_start.terminal_operations.persist_d7_prepared_terminal_no_replace
    )

    def publish_with_unproved_parent_fsync(
        loaded_start: object,
        prepared: object,
    ) -> terminal_persistence.D7PersistedStructuralTerminalIdentity:
        published = original_publish(loaded_start, prepared)
        return replace(published, parent_directory_fsync_proved=False)

    monkeypatch.setattr(
        fused_start.terminal_operations,
        "persist_d7_prepared_terminal_no_replace",
        publish_with_unproved_parent_fsync,
    )
    original = RuntimeError("scientific producer failed")

    with pytest.raises(RuntimeError) as caught:
        fused_start.run_d7_fused_verify_start_and_terminal_no_replace(
            context.descriptor_path,
            lambda: (_ for _ in ()).throw(original),
        )

    assert caught.value is original
    notes = getattr(caught.value, "__notes__", ())
    assert len(notes) == 2
    assert "spirallens_d7_prepared_failed_terminal=" in notes[0]
    assert "parent-directory durability is unproved" in notes[1]
    assert "terminal_manifest_sha256=" in notes[1]
    assert "terminal_consumption_sha256=" in notes[1]
    assert _terminal_path(context).is_dir()


def test_failed_terminal_durability_note_rejection_preserves_original_exception(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    _patch_stable_handoff(monkeypatch, context)
    original_publish = (
        fused_start.terminal_operations.persist_d7_prepared_terminal_no_replace
    )

    def publish_with_unproved_parent_fsync(
        loaded_start: object,
        prepared: object,
    ) -> terminal_persistence.D7PersistedStructuralTerminalIdentity:
        published = original_publish(loaded_start, prepared)
        return replace(published, parent_directory_fsync_proved=False)

    monkeypatch.setattr(
        fused_start.terminal_operations,
        "persist_d7_prepared_terminal_no_replace",
        publish_with_unproved_parent_fsync,
    )

    class NoteRejectingError(RuntimeError):
        def add_note(self, _note: str) -> None:
            raise RuntimeError("note mutation rejected")

    original = NoteRejectingError("scientific producer failed")
    with pytest.raises(NoteRejectingError) as caught:
        fused_start.run_d7_fused_verify_start_and_terminal_no_replace(
            context.descriptor_path,
            lambda: (_ for _ in ()).throw(original),
        )

    assert caught.value is original
    assert not hasattr(original, "__notes__")
    assert not hasattr(
        original,
        runner.D7_PREPARED_FAILED_TERMINAL_ATTRIBUTE,
    )
    assert _terminal_path(context).is_dir()


def test_failed_terminal_handoff_is_invalidated_and_cannot_cross_lanes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    _patch_stable_handoff(monkeypatch, context)
    original_publish = (
        fused_start.terminal_operations.persist_d7_prepared_terminal_no_replace
    )
    captured: list[runner.D7PreparedFailedTerminal] = []

    def fail_publication(
        _loaded_start: object,
        prepared: object,
    ) -> object:
        assert type(prepared) is runner.D7PreparedFailedTerminal
        captured.append(prepared)
        raise QualificationContractError("simulated terminal publication failure")

    monkeypatch.setattr(
        fused_start.terminal_operations,
        "persist_d7_prepared_terminal_no_replace",
        fail_publication,
    )
    original = RuntimeError("scientific producer failed")

    with pytest.raises(RuntimeError) as caught:
        fused_start.run_d7_fused_verify_start_and_terminal_no_replace(
            context.descriptor_path,
            lambda: (_ for _ in ()).throw(original),
        )

    assert caught.value is original
    assert not hasattr(
        caught.value,
        runner.D7_PREPARED_FAILED_TERMINAL_ATTRIBUTE,
    )
    assert len(captured) == 1
    prepared = captured[0]
    loaded_start = _load_start(context)
    evidence_prefix = _persist(context.values)

    with pytest.raises(QualificationContractError, match="already consumed"):
        original_publish(loaded_start, prepared)
    with pytest.raises(TypeError, match="kind differs"):
        original_publish(evidence_prefix, prepared)
    assert not _terminal_path(context).exists()


def test_success_terminal_prepublication_error_invalidates_ownership(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    component_bundle: component_fixtures._Bundle,
) -> None:
    context = _context(tmp_path)
    _patch_stable_handoff(monkeypatch, context)
    original_publish = (
        fused_start.terminal_operations.persist_d7_prepared_terminal_no_replace
    )
    captured: list[runner.D7PreparedScientificTerminal] = []

    def fail_before_publication(
        _loaded_start: object,
        prepared: object,
    ) -> object:
        assert type(prepared) is runner.D7PreparedScientificTerminal
        captured.append(prepared)
        raise QualificationContractError("simulated prepublication dispatch error")

    monkeypatch.setattr(
        fused_start.terminal_operations,
        "persist_d7_prepared_terminal_no_replace",
        fail_before_publication,
    )

    with pytest.raises(
        QualificationContractError,
        match="prepublication dispatch error",
    ):
        fused_start.run_d7_fused_verify_start_and_terminal_no_replace(
            context.descriptor_path,
            lambda: _producer_output(component_bundle),
        )

    assert len(captured) == 1
    with pytest.raises(QualificationContractError, match="already consumed"):
        original_publish(_load_start(context), captured[0])
    assert not _terminal_path(context).exists()


def test_runner_predispatch_error_invalidates_callback_ownership(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    component_bundle: component_fixtures._Bundle,
) -> None:
    context = _context(tmp_path)
    _patch_stable_handoff(monkeypatch, context)
    original_prepare = runner.prepare_d7_post_start_terminal
    captured: list[runner._D7PostStartOwnership] = []

    def fail_before_runner_entry(
        ownership: runner._D7PostStartOwnership,
        _scientific_producer: object,
        /,
    ) -> object:
        captured.append(ownership)
        raise QualificationContractError("simulated runner dispatch error")

    monkeypatch.setattr(
        runner,
        "prepare_d7_post_start_terminal",
        fail_before_runner_entry,
    )
    with pytest.raises(QualificationContractError, match="runner dispatch error"):
        fused_start.run_d7_fused_verify_start_and_terminal_no_replace(
            context.descriptor_path,
            lambda: _producer_output(component_bundle),
        )

    assert len(captured) == 1
    later_calls = 0

    def forbidden_later_callback() -> runner.D7ScientificProducerOutput:
        nonlocal later_calls
        later_calls += 1
        return _producer_output(component_bundle)

    with pytest.raises(QualificationContractError, match="already consumed"):
        original_prepare(captured[0], forbidden_later_callback)
    assert later_calls == 0
    _assert_visible_start_with_terminal_absent(context)


def test_unattached_failed_terminal_handoff_cannot_escape_through_traceback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    _patch_stable_handoff(monkeypatch, context)
    original_prepare = runner._prepare_failed_terminal
    captured: list[runner.D7PreparedFailedTerminal] = []

    def capture_prepared_failure(**kwargs: object) -> runner.D7PreparedFailedTerminal:
        prepared = original_prepare(**kwargs)  # type: ignore[arg-type]
        captured.append(prepared)
        return prepared

    monkeypatch.setattr(runner, "_prepare_failed_terminal", capture_prepared_failure)
    monkeypatch.setattr(runner, "_attach_failed_terminal", lambda *_args: None)
    original = RuntimeError("mutation-resistant exception simulation")

    with pytest.raises(RuntimeError) as caught:
        fused_start.run_d7_fused_verify_start_and_terminal_no_replace(
            context.descriptor_path,
            lambda: (_ for _ in ()).throw(original),
        )

    assert caught.value is original
    assert len(captured) == 1
    assert not hasattr(original, runner.D7_PREPARED_FAILED_TERMINAL_ATTRIBUTE)
    loaded_start = _load_start(context)
    with pytest.raises(QualificationContractError, match="already consumed"):
        fused_start.terminal_operations.persist_d7_prepared_terminal_no_replace(
            loaded_start,
            captured[0],
        )
    assert not _terminal_path(context).exists()


def test_failed_terminal_preparation_error_invalidates_traceback_ownership(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    _patch_stable_handoff(monkeypatch, context)
    captured: list[runner._D7PostStartOwnership] = []

    def fail_failure_preparation(**kwargs: object) -> object:
        ownership = kwargs["ownership"]
        assert type(ownership) is runner._D7PostStartOwnership
        captured.append(ownership)
        raise QualificationContractError("simulated failed-terminal preparation error")

    monkeypatch.setattr(runner, "_prepare_failed_terminal", fail_failure_preparation)

    with pytest.raises(
        QualificationContractError,
        match="failed-terminal preparation error",
    ):
        fused_start.run_d7_fused_verify_start_and_terminal_no_replace(
            context.descriptor_path,
            lambda: (_ for _ in ()).throw(RuntimeError("producer failed")),
        )

    assert len(captured) == 1
    with pytest.raises(QualificationContractError, match="already consumed"):
        captured[0]._consume_for_terminal_publication()
    assert not _terminal_path(context).exists()


def test_base_exception_leaves_visible_start_without_inferred_terminal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    _patch_stable_handoff(monkeypatch, context)
    original_prepare = runner.prepare_d7_post_start_terminal
    captured: list[runner._D7PostStartOwnership] = []

    def capture_ownership(
        ownership: runner._D7PostStartOwnership,
        scientific_producer: object,
        /,
    ) -> object:
        captured.append(ownership)
        return original_prepare(ownership, scientific_producer)  # type: ignore[arg-type]

    monkeypatch.setattr(
        runner,
        "prepare_d7_post_start_terminal",
        capture_ownership,
    )

    class SimulatedProcessExit(BaseException):
        pass

    original = SimulatedProcessExit("hard exit")
    calls = 0

    def scientific_producer() -> runner.D7ScientificProducerOutput:
        nonlocal calls
        calls += 1
        raise original

    with pytest.raises(SimulatedProcessExit) as caught:
        fused_start.run_d7_fused_verify_start_and_terminal_no_replace(
            context.descriptor_path,
            scientific_producer,
        )

    assert caught.value is original
    assert calls == 1
    assert len(captured) == 1
    with pytest.raises(QualificationContractError, match="already consumed"):
        captured[0]._consume_for_terminal_publication()
    assert not hasattr(original, runner.D7_PREPARED_FAILED_TERMINAL_ATTRIBUTE)
    _assert_visible_start_with_terminal_absent(context)
