from __future__ import annotations

import hashlib
import runpy
import subprocess
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import spirallens.qualification.contracts as qualification_contracts
from spirallens.core.canonical import (
    canonical_json_bytes,
    canonical_json_sha256,
    parse_canonical_json,
)
from spirallens.instrument_contracts import load_hypothesis_registry
from spirallens.qualification.common import (
    AttemptStatus,
    CorePredictionClass,
    LoopPredictionClass,
    QualificationContractError,
    QualificationState,
)
from spirallens.qualification.freeze import (
    SelectionFreezeArtifact,
    begin_selection_execution,
    claim_selection_attempt,
    load_terminal_selection_consumption,
    publish_terminal_selection_consumption,
)
from spirallens.qualification.persistence import LoadedQualificationProtocol
from spirallens.qualification.protocol import (
    EngineBinding,
    ModuleDigest,
    QualificationProtocol,
    RegistryBinding,
)
from spirallens.qualification.source_binding import (
    EVENT_LEDGER_SCHEMA_VERSION,
    BlindInputGeneratedEventPayload,
    OracleMaterializedEventPayload,
    PredictionSealedEventPayload,
    ProtocolVerifiedEventPayload,
    QualificationEventKind,
    QualificationEventLedger,
    QualificationEventLedgerReceipt,
    QualificationEventLedgerSummary,
    QualificationSourceBindingError,
    QualificationSourceBindingSummary,
    ResultAssembledEventPayload,
    ScoredEventPayload,
    module_repository_path,
    qualification_event_lane_ids,
    verify_protocol_source_binding_successor,
    verify_source_binding,
)
from spirallens.referents import canonical_f0_f4_referent_contracts

REPOSITORY = Path(__file__).resolve().parents[1]
TRACKED_REGISTRY = (
    REPOSITORY / "protocols" / "order_parameter_hypothesis_registry_v0_1.yaml"
)


def _git(repository: Path, *arguments: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
    ).stdout


def _sha256(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def _source_fixture(
    tmp_path: Path,
) -> tuple[Path, EngineBinding, RegistryBinding, Path, Path]:
    repository = tmp_path / "repository"
    module_path = repository / "src" / "spirallens" / "qualification" / "demo.py"
    registry_path = repository / "protocols" / "registry.yaml"
    referent_path = repository / "protocols" / "referents.json"
    module_path.parent.mkdir(parents=True)
    registry_path.parent.mkdir(parents=True)
    module_source = b'"""Bound demo module."""\n\nVALUE = 7\n'
    module_path.write_bytes(module_source)
    registry_source = TRACKED_REGISTRY.read_bytes()
    registry_path.write_bytes(registry_source)
    loaded_registry = load_hypothesis_registry(registry_path)
    referents = canonical_f0_f4_referent_contracts(loaded_registry.canonical_sha256)
    referent_path.write_bytes(referents.canonical_bytes)

    _git(repository, "init", "-q")
    _git(repository, "config", "user.name", "SpiralLens Test")
    _git(repository, "config", "user.email", "test@example.invalid")
    _git(repository, "add", ".")
    _git(repository, "commit", "-qm", "bound sources")
    commit = _git(repository, "rev-parse", "HEAD").decode("ascii").strip()

    engine = EngineBinding(
        repository="RyoSpiralArchitect/SpiralLens",
        commit=commit,
        modules=(
            ModuleDigest(
                module="spirallens.qualification.demo",
                sha256=_sha256(module_source),
            ),
        ),
    )
    registry = RegistryBinding(
        registry_source_sha256=loaded_registry.source_sha256,
        registry_canonical_sha256=loaded_registry.canonical_sha256,
        referent_canonical_sha256=referents.canonical_sha256,
    )
    return repository, engine, registry, registry_path, referent_path


def _verify_fixture(
    fixture: tuple[Path, EngineBinding, RegistryBinding, Path, Path],
):
    repository, engine, registry, registry_path, referent_path = fixture
    return verify_source_binding(
        engine=engine,
        registry=registry,
        repository_root=repository,
        registry_path=registry_path,
        referent_path=referent_path,
    )


def _protocol_for_source_fixture(
    fixture: tuple[Path, EngineBinding, RegistryBinding, Path, Path],
) -> QualificationProtocol:
    namespace = runpy.run_path(
        Path(__file__).with_name("test_qualification_protocol_hardening.py")
    )
    protocol = namespace["_protocol"]()
    assert isinstance(protocol, QualificationProtocol)
    _repository, engine, registry, _registry_path, _referent_path = fixture
    return replace(
        protocol,
        engine=engine,
        registry=registry,
    )


def test_source_binding_proves_ancestor_blobs_worktree_and_loader_sources(
    tmp_path: Path,
) -> None:
    fixture = _source_fixture(tmp_path)
    repository, engine, registry, _, _ = fixture

    receipt = _verify_fixture(fixture)

    assert receipt.engine == engine
    assert receipt.registry == registry
    assert receipt.head_commit == engine.commit
    assert receipt.git_ancestry_verified is True
    assert receipt.module_worktree_clean is True
    assert receipt.modules[0].declared_sha256 == receipt.modules[0].working_sha256
    assert receipt.modules[0].working_sha256 == receipt.modules[0].bound_blob_sha256
    assert receipt.modules[0].repository_path == (
        "src/spirallens/qualification/demo.py"
    )
    assert receipt.hypothesis_registry.repository_path == "protocols/registry.yaml"
    assert receipt.referent_contracts.repository_path == "protocols/referents.json"
    assert receipt.scientific_claim_eligible is False
    assert receipt.subject_access_authorized is False
    assert receipt.semantic_authority is False
    assert receipt.integer_or_topology_authority is False
    assert parse_canonical_json(receipt.canonical_bytes) == receipt.to_dict()
    assert _git(repository, "status", "--porcelain") == b""
    summary = QualificationSourceBindingSummary.from_receipt(receipt)
    summary.verify_receipt(receipt)
    assert summary.source_binding_receipt_sha256 == receipt.canonical_sha256
    assert summary.source_binding_verified is True
    assert (
        QualificationSourceBindingSummary.from_dict(
            parse_canonical_json(summary.canonical_bytes)
        )
        == summary
    )


def test_source_binding_binds_and_rejects_mutated_package_initializer(
    tmp_path: Path,
) -> None:
    fixture = _source_fixture(tmp_path)
    repository, engine, registry, registry_path, referent_path = fixture
    package_path = (
        repository
        / "src"
        / "spirallens"
        / "qualification"
        / "bound_dependency"
        / "__init__.py"
    )
    package_path.parent.mkdir()
    package_source = b'"""Executable package initializer."""\n\nVALUE = 11\n'
    package_path.write_bytes(package_source)
    _git(repository, "add", package_path.relative_to(repository).as_posix())
    _git(repository, "commit", "-qm", "bind package initializer")
    commit = _git(repository, "rev-parse", "HEAD").decode("ascii").strip()
    package_module = "spirallens.qualification.bound_dependency"
    package_digest = ModuleDigest(
        module=package_module,
        sha256=_sha256(package_source),
    )
    bound_engine = replace(
        engine,
        commit=commit,
        modules=tuple(
            sorted(
                (*engine.modules, package_digest),
                key=lambda item: item.module,
            )
        ),
    )

    receipt = verify_source_binding(
        engine=bound_engine,
        registry=registry,
        repository_root=repository,
        registry_path=registry_path,
        referent_path=referent_path,
    )

    package_receipt = next(
        item for item in receipt.modules if item.module == package_module
    )
    assert package_receipt.repository_path.endswith("/bound_dependency/__init__.py")
    assert (
        module_repository_path(
            package_module,
            repository_root=repository,
        )
        == package_receipt.repository_path
    )

    package_path.write_bytes(package_source + b"MUTATED = True\n")
    with pytest.raises(
        QualificationSourceBindingError,
        match="tracked or untracked worktree difference",
    ):
        verify_source_binding(
            engine=bound_engine,
            registry=registry,
            repository_root=repository,
            registry_path=registry_path,
            referent_path=referent_path,
        )


def test_source_binding_rejects_fake_commit_and_fake_module_digest(
    tmp_path: Path,
) -> None:
    fixture = _source_fixture(tmp_path)
    repository, engine, registry, registry_path, referent_path = fixture

    with pytest.raises(QualificationSourceBindingError):
        verify_source_binding(
            engine=replace(engine, commit="f" * 40),
            registry=registry,
            repository_root=repository,
            registry_path=registry_path,
            referent_path=referent_path,
        )

    false_module = ModuleDigest(
        module=engine.modules[0].module,
        sha256="0" * 64,
    )
    with pytest.raises(
        QualificationSourceBindingError,
        match="does not match its declared",
    ):
        verify_source_binding(
            engine=replace(engine, modules=(false_module,)),
            registry=registry,
            repository_root=repository,
            registry_path=registry_path,
            referent_path=referent_path,
        )


def test_source_binding_rejects_dirty_or_untracked_module(tmp_path: Path) -> None:
    fixture = _source_fixture(tmp_path)
    repository, engine, registry, registry_path, referent_path = fixture
    module_path = repository / module_repository_path(engine.modules[0].module)
    module_path.write_bytes(module_path.read_bytes() + b"\nDIRTY = True\n")

    with pytest.raises(
        QualificationSourceBindingError,
        match="tracked or untracked worktree difference",
    ):
        _verify_fixture(fixture)

    _git(repository, "restore", "--", module_repository_path(engine.modules[0].module))
    untracked_path = repository / "src" / "spirallens" / "qualification" / "new.py"
    untracked_path.write_bytes(b"VALUE = 1\n")
    untracked_engine = replace(
        engine,
        modules=(
            ModuleDigest(
                module="spirallens.qualification.new",
                sha256=_sha256(untracked_path.read_bytes()),
            ),
        ),
    )
    with pytest.raises(QualificationSourceBindingError):
        verify_source_binding(
            engine=untracked_engine,
            registry=registry,
            repository_root=repository,
            registry_path=registry_path,
            referent_path=referent_path,
        )


def test_source_binding_rejects_nonancestor_commit(tmp_path: Path) -> None:
    fixture = _source_fixture(tmp_path)
    repository, engine, registry, registry_path, referent_path = fixture
    main_branch = _git(repository, "branch", "--show-current").decode("ascii").strip()
    _git(repository, "checkout", "-qb", "side")
    side_path = repository / "side.txt"
    side_path.write_text("side\n", encoding="utf-8")
    _git(repository, "add", "side.txt")
    _git(repository, "commit", "-qm", "side commit")
    side_commit = _git(repository, "rev-parse", "HEAD").decode("ascii").strip()
    _git(repository, "checkout", "-q", main_branch)
    main_path = repository / "main.txt"
    main_path.write_text("main\n", encoding="utf-8")
    _git(repository, "add", "main.txt")
    _git(repository, "commit", "-qm", "main commit")

    with pytest.raises(
        QualificationSourceBindingError,
        match="not an ancestor",
    ):
        verify_source_binding(
            engine=replace(engine, commit=side_commit),
            registry=registry,
            repository_root=repository,
            registry_path=registry_path,
            referent_path=referent_path,
        )


def test_successor_source_binding_reconstructs_exact_execution_receipt(
    tmp_path: Path,
) -> None:
    fixture = _source_fixture(tmp_path)
    repository, _engine, _registry, registry_path, referent_path = fixture
    protocol = _protocol_for_source_fixture(fixture)
    execution_receipt = _verify_fixture(fixture)
    summary = QualificationSourceBindingSummary.from_receipt(execution_receipt)
    artifact_path = repository / "artifacts" / "qualification-result.json"
    artifact_path.parent.mkdir()
    artifact_path.write_text('{"result":"committed"}\n', encoding="utf-8")
    _git(repository, "add", artifact_path.relative_to(repository).as_posix())
    _git(repository, "commit", "-qm", "commit terminal artifact")

    reconstructed = verify_protocol_source_binding_successor(
        protocol,
        source_binding_summary=summary,
        repository_root=repository,
        registry_path=registry_path,
        referent_path=referent_path,
    )

    assert reconstructed == execution_receipt
    assert reconstructed.head_commit == summary.head_commit
    assert reconstructed.head_commit != (
        _git(repository, "rev-parse", "HEAD").decode("ascii").strip()
    )
    summary.verify_receipt(reconstructed)
    with pytest.raises(
        QualificationSourceBindingError,
        match="stored source-binding summary differs",
    ):
        verify_protocol_source_binding_successor(
            protocol,
            source_binding_summary=replace(
                summary,
                source_binding_receipt_sha256="0" * 64,
            ),
            repository_root=repository,
            registry_path=registry_path,
            referent_path=referent_path,
        )


def test_successor_source_binding_rejects_sibling_execution_head(
    tmp_path: Path,
) -> None:
    fixture = _source_fixture(tmp_path)
    repository, _engine, _registry, registry_path, referent_path = fixture
    protocol = _protocol_for_source_fixture(fixture)
    base_receipt = _verify_fixture(fixture)
    main_branch = _git(repository, "branch", "--show-current").decode("ascii").strip()
    _git(repository, "checkout", "-qb", "side")
    side_path = repository / "side-artifact.json"
    side_path.write_text("{}\n", encoding="utf-8")
    _git(repository, "add", side_path.relative_to(repository).as_posix())
    _git(repository, "commit", "-qm", "side artifact")
    side_head = _git(repository, "rev-parse", "HEAD").decode("ascii").strip()
    side_summary = QualificationSourceBindingSummary.from_receipt(
        replace(base_receipt, head_commit=side_head)
    )
    _git(repository, "checkout", "-q", main_branch)
    main_path = repository / "main-artifact.json"
    main_path.write_text("{}\n", encoding="utf-8")
    _git(repository, "add", main_path.relative_to(repository).as_posix())
    _git(repository, "commit", "-qm", "main artifact")

    with pytest.raises(
        QualificationSourceBindingError,
        match="stored execution HEAD is not an ancestor",
    ):
        verify_protocol_source_binding_successor(
            protocol,
            source_binding_summary=side_summary,
            repository_root=repository,
            registry_path=registry_path,
            referent_path=referent_path,
        )


def test_successor_source_binding_rejects_execution_blob_mismatch(
    tmp_path: Path,
) -> None:
    fixture = _source_fixture(tmp_path)
    repository, engine, _registry, registry_path, referent_path = fixture
    protocol = _protocol_for_source_fixture(fixture)
    base_receipt = _verify_fixture(fixture)
    module_path = repository / module_repository_path(
        engine.modules[0].module,
        repository_root=repository,
    )
    original_source = module_path.read_bytes()
    module_path.write_bytes(original_source + b"MUTATED_AT_EXECUTION = True\n")
    _git(repository, "add", module_path.relative_to(repository).as_posix())
    _git(repository, "commit", "-qm", "mismatched execution source")
    mismatched_head = _git(repository, "rev-parse", "HEAD").decode("ascii").strip()
    mismatched_summary = QualificationSourceBindingSummary.from_receipt(
        replace(base_receipt, head_commit=mismatched_head)
    )
    module_path.write_bytes(original_source)
    _git(repository, "add", module_path.relative_to(repository).as_posix())
    _git(repository, "commit", "-qm", "restore source after execution")

    with pytest.raises(
        QualificationSourceBindingError,
        match="stored execution HEAD differs",
    ):
        verify_protocol_source_binding_successor(
            protocol,
            source_binding_summary=mismatched_summary,
            repository_root=repository,
            registry_path=registry_path,
            referent_path=referent_path,
        )


def test_successor_source_binding_rejects_current_source_path_drift(
    tmp_path: Path,
) -> None:
    fixture = _source_fixture(tmp_path)
    repository, _engine, _registry, registry_path, referent_path = fixture
    protocol = _protocol_for_source_fixture(fixture)
    execution_receipt = _verify_fixture(fixture)
    summary = QualificationSourceBindingSummary.from_receipt(execution_receipt)
    moved_registry_path = registry_path.with_name("registry-moved.yaml")
    _git(
        repository,
        "mv",
        registry_path.relative_to(repository).as_posix(),
        moved_registry_path.relative_to(repository).as_posix(),
    )
    _git(repository, "commit", "-qm", "move registry path")

    with pytest.raises(
        QualificationSourceBindingError,
        match="absent from the execution HEAD",
    ):
        verify_protocol_source_binding_successor(
            protocol,
            source_binding_summary=summary,
            repository_root=repository,
            registry_path=moved_registry_path,
            referent_path=referent_path,
        )


def test_terminal_publish_and_load_accept_exact_source_successor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _source_fixture(tmp_path)
    repository, _engine, _registry, registry_path, referent_path = fixture
    protocol = _protocol_for_source_fixture(fixture)
    execution_receipt = _verify_fixture(fixture)
    summary = QualificationSourceBindingSummary.from_receipt(execution_receipt)
    loaded = LoadedQualificationProtocol(
        protocol=protocol,
        source_path=repository / "protocol.json",
        source_bytes=protocol.canonical_bytes,
        source_sha256=protocol.canonical_sha256,
        canonical_sha256=protocol.canonical_sha256,
    )
    freeze = SelectionFreezeArtifact.from_loaded_protocol(
        freeze_id="successor-terminal-freeze",
        loaded_protocol=loaded,
        seed_family_id="successor-terminal-family",
    )
    store = tmp_path / "terminal-store"
    store.mkdir()
    claim, _claim_identity = claim_selection_attempt(
        store,
        claim_id="successor-terminal-claim",
        freeze=freeze,
    )
    begin_selection_execution(
        store,
        freeze=freeze,
        attempt_claim=claim,
    )

    artifact_path = repository / "artifacts" / "post-execution-marker.json"
    artifact_path.parent.mkdir()
    artifact_path.write_text('{"phase":"post-execution"}\n', encoding="utf-8")
    _git(repository, "add", artifact_path.relative_to(repository).as_posix())
    _git(repository, "commit", "-qm", "post-execution artifact commit")
    validation_receipts: list[object] = []

    class FakeQualificationResult:
        loaded_instance: object

        def __init__(self) -> None:
            self.protocol_id = protocol.protocol_id
            self.protocol_source_sha256 = loaded.source_sha256
            self.protocol_canonical_sha256 = loaded.canonical_sha256
            self.selection_freeze_artifact_sha256 = freeze.canonical_sha256
            self.selection_attempt_claim_sha256 = claim.canonical_sha256
            self.selection_launch_authorization_sha256 = None
            self.source_binding = summary

        def to_dict(self) -> dict[str, object]:
            return {
                "kind": "successor-terminal-test-result",
                "source_binding": self.source_binding.to_dict(),
            }

        @property
        def canonical_bytes(self) -> bytes:
            return canonical_json_bytes(self.to_dict())

        @property
        def canonical_sha256(self) -> str:
            return canonical_json_sha256(self.to_dict())

        def validate_against_protocol(
            self,
            supplied_protocol: QualificationProtocol,
            *,
            protocol_source_sha256: str,
            source_binding_receipt: object,
            selection_freeze_artifact: object,
            selection_attempt_claim: object,
            selection_launch_authorization_sha256: str | None,
        ) -> None:
            assert supplied_protocol == protocol
            assert protocol_source_sha256 == loaded.source_sha256
            assert selection_freeze_artifact == freeze
            assert selection_attempt_claim == claim
            assert selection_launch_authorization_sha256 is None
            validation_receipts.append(source_binding_receipt)

        @classmethod
        def from_dict(cls, value: object) -> object:
            instance = cls.loaded_instance
            assert value == instance.to_dict()  # type: ignore[attr-defined]
            return instance

    result = FakeQualificationResult()
    FakeQualificationResult.loaded_instance = result
    monkeypatch.setattr(
        qualification_contracts,
        "QualificationResult",
        FakeQualificationResult,
    )

    consumption, identity = publish_terminal_selection_consumption(
        store,
        consumption_id="successor-terminal-consumption",
        freeze=freeze,
        attempt_claim=claim,
        terminal_artifact=result,
        loaded_protocol=loaded,
        repository_root=repository,
        registry_path=registry_path,
        referent_path=referent_path,
    )
    loaded_consumption, loaded_result = load_terminal_selection_consumption(
        identity.path,
        expected_manifest_sha256=identity.manifest_sha256,
        expected_terminal_artifact_sha256=identity.terminal_artifact_sha256,
        expected_consumption_sha256=identity.consumption_sha256,
        freeze=freeze,
        attempt_claim=claim,
        loaded_protocol=loaded,
        repository_root=repository,
        registry_path=registry_path,
        referent_path=referent_path,
    )

    assert loaded_consumption == consumption
    assert loaded_result is result
    assert validation_receipts == [execution_receipt, execution_receipt]


def test_source_binding_rejects_dummy_registry_or_referent_digest(
    tmp_path: Path,
) -> None:
    fixture = _source_fixture(tmp_path)
    repository, engine, registry, registry_path, referent_path = fixture

    with pytest.raises(
        QualificationSourceBindingError,
        match="hypothesis registry failed",
    ):
        verify_source_binding(
            engine=engine,
            registry=replace(registry, registry_source_sha256="0" * 64),
            repository_root=repository,
            registry_path=registry_path,
            referent_path=referent_path,
        )

    with pytest.raises(
        QualificationSourceBindingError,
        match="referent contract set failed",
    ):
        verify_source_binding(
            engine=engine,
            registry=replace(registry, referent_canonical_sha256="0" * 64),
            repository_root=repository,
            registry_path=registry_path,
            referent_path=referent_path,
        )


def _payloads(lane_id: str):
    protocol = ProtocolVerifiedEventPayload(
        lane_id=lane_id,
        protocol_id="protocol",
        protocol_source_sha256=_sha256(b"protocol-source"),
        protocol_canonical_sha256=_sha256(b"protocol-canonical"),
        selection_freeze_artifact_sha256=_sha256(b"selection-freeze"),
        selection_attempt_claim_sha256=_sha256(b"selection-attempt-claim"),
        source_binding_receipt_sha256=_sha256(b"source-binding"),
        lane_contract_sha256=_sha256(lane_id.encode()),
    )
    blind = BlindInputGeneratedEventPayload(
        lane_id=lane_id,
        protocol_payload_sha256=canonical_json_sha256(protocol.to_dict()),
        attempt_status=AttemptStatus.NOT_RUN,
        input_evidence_sha256=_sha256(b"input-evidence"),
        blind_input_fingerprint_sha256=None,
    )
    prediction_class = (
        CorePredictionClass.NONE.value
        if lane_id.startswith("core.")
        else LoopPredictionClass.NONE.value
    )
    prediction = PredictionSealedEventPayload(
        lane_id=lane_id,
        blind_input_payload_sha256=canonical_json_sha256(blind.to_dict()),
        attempt_status=AttemptStatus.NOT_RUN,
        prediction_evidence_sha256=_sha256(b"prediction-evidence"),
        prediction_fingerprint_sha256=None,
        prediction_class=prediction_class,
    )
    oracle = OracleMaterializedEventPayload(
        lane_id=lane_id,
        prediction_payload_sha256=canonical_json_sha256(prediction.to_dict()),
        attempt_status=AttemptStatus.NOT_RUN,
        oracle_evidence_sha256=_sha256(b"oracle-evidence"),
        oracle_fingerprint_sha256=None,
    )
    scored = ScoredEventPayload(
        lane_id=lane_id,
        oracle_payload_sha256=canonical_json_sha256(oracle.to_dict()),
        attempt_status=AttemptStatus.NOT_RUN,
        prediction_class=prediction_class,
        state=QualificationState.NOT_RUN,
        reason_codes=("not-run",),
        normalized_cell_summary_sha256=_sha256(b"cell-summary"),
    )
    result = ResultAssembledEventPayload(
        lane_id=lane_id,
        scored_payload_sha256=canonical_json_sha256(scored.to_dict()),
        result_id="result",
        result_evidence_root_sha256=_sha256(b"result-evidence-root"),
        selection_freeze_artifact_sha256=_sha256(b"selection-freeze"),
        selection_attempt_claim_sha256=_sha256(b"selection-attempt-claim"),
        normalized_primary_summary_sha256=_sha256(b"primary-summary"),
        normalized_nonvacuity_summary_sha256=(
            _sha256(b"nonvacuity-summary") if lane_id.startswith("loop.") else None
        ),
        normalized_strata_projection_sha256=_sha256(b"strata"),
    )
    return protocol, blind, prediction, oracle, scored, result


def _append_complete_lane(
    ledger: QualificationEventLedger,
    lane_id: str,
) -> QualificationEventLedger:
    for kind, payload in zip(QualificationEventKind, _payloads(lane_id), strict=True):
        ledger = ledger.append(
            lane_id=lane_id,
            event_kind=kind,
            payload=payload,
        )
    return ledger


def test_event_ledger_receipt_proves_complete_fixed_chronology() -> None:
    ledger = QualificationEventLedger.create(("cell.alpha",))
    ledger = _append_complete_lane(ledger, "cell.alpha")

    receipt = ledger.receipt()
    loaded_ledger = QualificationEventLedger.from_dict(
        parse_canonical_json(ledger.canonical_bytes)
    )
    loaded_receipt = QualificationEventLedgerReceipt.from_dict(
        parse_canonical_json(receipt.canonical_bytes)
    )

    assert ledger.schema_version == EVENT_LEDGER_SCHEMA_VERSION
    assert loaded_ledger == ledger
    assert loaded_receipt == receipt
    assert receipt.posthoc_logical_dependency_manifest_validated is True
    assert receipt.event_count == len(QualificationEventKind)
    assert receipt.entries[2].event_kind is QualificationEventKind.PREDICTION_SEALED
    assert receipt.entries[3].event_kind is QualificationEventKind.ORACLE_MATERIALIZED
    assert receipt.scientific_claim_eligible is False
    assert receipt.subject_access_authorized is False
    assert receipt.semantic_authority is False
    assert receipt.integer_or_topology_authority is False
    summary = QualificationEventLedgerSummary.from_receipt(receipt)
    summary.verify_receipt(receipt)
    assert summary.event_ledger_receipt_sha256 == receipt.canonical_sha256
    assert summary.event_ledger_canonical_sha256 == ledger.canonical_sha256
    assert summary.event_ledger_lane_count == 1
    assert summary.posthoc_logical_dependency_manifest_validated is True
    assert (
        QualificationEventLedgerSummary.from_dict(
            parse_canonical_json(summary.canonical_bytes)
        )
        == summary
    )

    with pytest.raises(QualificationContractError, match="differs"):
        replace(
            summary,
            event_ledger_chain_head_sha256="0" * 64,
        ).verify_receipt(receipt)


def test_event_ledger_supports_interleaving_but_enforces_each_lane() -> None:
    lanes = ("cell.alpha", "primary.beta")
    ledger = QualificationEventLedger.create(lanes)
    for kind in QualificationEventKind:
        for lane_id in reversed(lanes):
            payload = _payloads(lane_id)[tuple(QualificationEventKind).index(kind)]
            ledger = ledger.append(
                lane_id=lane_id,
                event_kind=kind,
                payload=payload,
            )

    assert ledger.is_complete
    assert ledger.completed_lane_ids == lanes
    assert ledger.receipt().event_count == 2 * len(QualificationEventKind)


def test_event_ledger_rejects_oracle_before_prediction_and_duplicates() -> None:
    ledger = QualificationEventLedger.create(("cell.alpha",))
    payloads = _payloads("cell.alpha")
    with pytest.raises(QualificationContractError, match="cannot precede"):
        ledger.append(
            lane_id="cell.alpha",
            event_kind=QualificationEventKind.ORACLE_MATERIALIZED,
            payload=payloads[3],
        )

    ledger = ledger.append(
        lane_id="cell.alpha",
        event_kind=QualificationEventKind.PROTOCOL_VERIFIED,
        payload=payloads[0],
    )
    with pytest.raises(QualificationContractError, match="cannot precede"):
        ledger.append(
            lane_id="cell.alpha",
            event_kind=QualificationEventKind.PROTOCOL_VERIFIED,
            payload=payloads[0],
        )
    with pytest.raises(QualificationContractError, match="every declared lane"):
        ledger.receipt()


def test_event_ledger_rejects_tamper_reorder_and_missing_lane() -> None:
    ledger = QualificationEventLedger.create(("cell.alpha",))
    ledger = _append_complete_lane(ledger, "cell.alpha")

    with pytest.raises(QualificationContractError, match="digest"):
        replace(ledger.entries[2], payload_sha256="0" * 64)

    with pytest.raises(QualificationContractError, match="sequence"):
        replace(
            ledger,
            entries=(
                ledger.entries[1],
                ledger.entries[0],
                *ledger.entries[2:],
            ),
        )

    incomplete = QualificationEventLedger.create(("cell.alpha", "cell.beta"))
    incomplete = _append_complete_lane(incomplete, "cell.alpha")
    with pytest.raises(QualificationContractError, match="every declared lane"):
        incomplete.receipt()


def test_event_ledger_rejects_untyped_payload_and_undeclared_lane() -> None:
    ledger = QualificationEventLedger.create(("cell.alpha",))
    with pytest.raises(QualificationContractError, match="payload type"):
        ledger.append(
            lane_id="cell.alpha",
            event_kind=QualificationEventKind.PROTOCOL_VERIFIED,
            payload=b'{"x": 1}',
        )  # type: ignore[arg-type]
    with pytest.raises(QualificationContractError, match="undeclared lane"):
        ledger.append(
            lane_id="cell.beta",
            event_kind=QualificationEventKind.PROTOCOL_VERIFIED,
            payload=_payloads("cell.beta")[0],
        )


def test_protocol_lane_manifest_is_exact_prefixed_and_canonical() -> None:
    protocol = object.__new__(QualificationProtocol)
    object.__setattr__(
        protocol,
        "expected_core_cells",
        (
            SimpleNamespace(core_cell_id="zeta"),
            SimpleNamespace(core_cell_id="alpha"),
        ),
    )
    object.__setattr__(
        protocol,
        "expected_cells",
        (
            SimpleNamespace(cell_id="beta"),
            SimpleNamespace(cell_id="alpha"),
        ),
    )

    assert qualification_event_lane_ids(protocol) == (
        "core.alpha",
        "core.zeta",
        "loop.alpha",
        "loop.beta",
    )


def test_event_ledger_rejects_mutable_lane_or_entry_containers() -> None:
    with pytest.raises(TypeError, match="immutable tuple"):
        QualificationEventLedger(expected_lane_ids=["cell.alpha"])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="immutable tuple"):
        QualificationEventLedger(
            expected_lane_ids=("cell.alpha",),
            entries=[],  # type: ignore[arg-type]
        )
