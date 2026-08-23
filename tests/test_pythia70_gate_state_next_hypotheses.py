from __future__ import annotations

import copy
import errno
import importlib.util
import json
import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/publish_pythia70_gate_state_next_hypotheses.py"
FREEZE = ROOT / "protocols/pythia70_gate_state_development_freeze_v0_1.json"
ATTEMPT = ROOT / "experiments/pythia/gate_state_development_v0_1/attempt.json"
TERMINAL = (
    ROOT / "experiments/pythia/gate_state_development_v0_1/terminal-result.json"
)


def _load_script():
    spec = importlib.util.spec_from_file_location("next_hypothesis_publisher", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _canonical(document: object) -> bytes:
    return (
        json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def _record(module):
    terminal, terminal_source = module._load_canonical(TERMINAL)
    freeze_source = module._read_bounded_regular(
        FREEZE,
        maximum_bytes=module.MAX_FREEZE_BYTES,
    )
    _attempt, attempt_source = module._load_canonical(ATTEMPT)
    module._require_publisher_lineage = lambda _commit, _sha256: None
    record = module._build_record(
        terminal=terminal,
        terminal_source=terminal_source,
        freeze_source=freeze_source,
        attempt_source=attempt_source,
        publisher_commit="a" * 40,
        publisher_sha256=module._sha256(SCRIPT.read_bytes()),
    )
    return record, terminal_source


def test_record_binds_consumed_terminal_and_retains_zero_authority() -> None:
    module = _load_script()
    record, terminal_source = _record(module)
    assert module._validate_record(
        record,
        expected_terminal_source=terminal_source,
    ) == record

    assert record["decision_date"] == "2026-08-24"
    assert record["chronology"] == {
        "cryptographic_unseen_proof": False,
        "independent": False,
        "operator_prior_model_free_calibration_outcome_exposure": True,
        "post_outcome": True,
        "preregistered": False,
        "publication_wall_clock_attested": False,
        "terminal_result_preexisted": True,
    }
    assert set(record["planning_authority"].values()) == {False}
    assert record["claim_boundary"]["claim_delta"] == "none"
    assert record["claim_boundary"]["milestone_credit"] == "none"
    assert record["claim_boundary"]["evidence_eligible"] is False
    assert record["bindings"]["terminal_sha256"] == (
        module.EXPECTED_TERMINAL_SHA256
    )
    assert record["terminal_observation"]["cell_state_counts"] == {
        "fail": 6,
        "insufficient": 761,
        "not_run": 0,
        "pass": 127,
    }

    diagnostic = record["derived_structural_diagnostics"]
    assert diagnostic["ring_prerequisite_cascade_cell_count"] == 702
    assert diagnostic["ring_prerequisite_cascade_insufficient_denominator"] == 761
    assert diagnostic["graphs_with_positive_cycle_rank"] == 16
    assert diagnostic["total_fundamental_cycle_rank"] == 2592
    assert len(diagnostic["graph_cycle_ranks"]) == 18
    assert record["state_transition"] == {
        "calibration_state": "planned_not_frozen_not_run",
        "from_repository_state": "1110",
        "target_repository_state": "1111",
        "terminal_lifecycle": "terminal_consumed",
    }


def test_record_freezes_competing_hypotheses_and_model_free_stop_gate() -> None:
    module = _load_script()
    record, _terminal_source = _record(module)

    assert [item["hypothesis_id"] for item in record["competing_hypotheses"]] == [
        "h-address-grid-mismatch",
        "h-graph-scale-mismatch",
        "h-frame-gauge-instability",
        "h-representation-graph-sensitivity",
        "h-genuine-support-scarcity",
        "h-no-stable-structure-at-tested-resolution",
    ]
    experiment = record["next_experiment"]
    assert experiment["experiment_id"] == "model-free-evaluability-calibration-v0.1"
    assert set(experiment["execution_boundary"].values()) == {False}
    assert experiment["design"]["scale_selection_forbidden_reads"] == [
        "field",
        "core",
        "holonomy",
        "phase",
        "winding",
        "charge",
        "pythia_terminal_candidate_values",
    ]
    assert experiment["stop_rules"][-1] == (
        "stop_before_any_model_run_if_held_out_confirmation_does_not_pass"
    )
    assert experiment["graph_selector"]["triplet_requirements"] == {
        "common_two_core_intersection_minimum": 35,
        "edge_count_maximum_to_minimum_ratio_maximum": 1.25,
        "largest_component_vertex_count_spread_maximum": 2,
        "matched_cycle_classes": ["central", "wide"],
        "max_domain_edges_per_graph_edge": 4,
        "pairwise_edge_jaccard_maximum": 0.85,
        "pairwise_edge_sets_must_differ": True,
        "two_core_vertex_count_spread_maximum": 4,
    }


def test_record_rejects_terminal_or_authority_mutation() -> None:
    module = _load_script()
    record, terminal_source = _record(module)

    forged_record = copy.deepcopy(record)
    forged_record["planning_authority"]["calibration_execution_authorized"] = True
    with pytest.raises(module.PublicationError, match="must be false"):
        module._validate_record(
            forged_record,
            expected_terminal_source=terminal_source,
        )

    terminal = json.loads(terminal_source)
    terminal["cell_records"][0]["state"] = "insufficient"
    with pytest.raises(module.PublicationError, match="cell counts differ"):
        module._terminal_observation(terminal)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda record: record["claim_boundary"].__setitem__(
                "scientific_authority", 0
            ),
            "claim boundary differs",
        ),
        (
            lambda record: record["next_experiment"]["execution_boundary"].__setitem__(
                "model_access_authorized", 0
            ),
            "next experiment differs",
        ),
        (
            lambda record: record["terminal_observation"][
                "cell_state_counts"
            ].__setitem__("not_run", False),
            "terminal observation projection differs",
        ),
    ],
)
def test_nested_validation_is_type_exact(mutation, message: str) -> None:
    module = _load_script()
    record, terminal_source = _record(module)
    forged = copy.deepcopy(record)
    mutation(forged)
    with pytest.raises(module.PublicationError, match=message):
        module._validate_record(forged, expected_terminal_source=terminal_source)


def test_closed_schema_rejects_unknown_and_duplicate_fields(tmp_path: Path) -> None:
    module = _load_script()
    record, terminal_source = _record(module)

    forged = copy.deepcopy(record)
    forged["unknown"] = False
    with pytest.raises(module.PublicationError, match="closed schema"):
        module._validate_record(forged, expected_terminal_source=terminal_source)

    duplicate = tmp_path / "duplicate.json"
    duplicate.write_bytes(b'{"x":1,"x":2}\n')
    with pytest.raises(module.PublicationError, match="duplicate JSON key"):
        module._load_canonical(duplicate)


def test_pair_publication_is_no_replace_and_repairable_from_external(
    tmp_path: Path,
) -> None:
    module = _load_script()
    record, _terminal_source = _record(module)
    source = _canonical(record)
    external = tmp_path / "external-next.json"
    repository = tmp_path / "repository-next.json"

    assert module._publish_pair(
        external_path=external,
        repository_path=repository,
        source=source,
    ) == "published"
    assert external.read_bytes() == repository.read_bytes() == source
    with pytest.raises(module.PublicationError, match="expected 'absent'"):
        module._publish_pair(
            external_path=external,
            repository_path=repository,
            source=source,
        )

    repaired_external = tmp_path / "repair-external.json"
    repaired_repository = tmp_path / "repair-repository.json"
    module._publish_file_native_no_replace(repaired_external, source)
    repaired = module._repair_repository_projection(
        external_path=repaired_external,
        repository_path=repaired_repository,
        expected_terminal_source=_terminal_source,
    )
    assert repaired == source
    assert repaired_external.read_bytes() == repaired_repository.read_bytes()


def test_pair_publication_rejects_split_or_mismatched_state(tmp_path: Path) -> None:
    module = _load_script()
    source = b'{"a":1}\n'
    external = tmp_path / "external.json"
    repository = tmp_path / "repository.json"

    repository.write_bytes(source)
    with pytest.raises(module.PublicationError, match="expected 'absent'"):
        module._publish_pair(
            external_path=external,
            repository_path=repository,
            source=source,
        )

    repository.unlink()
    external.write_bytes(b'{"a":2}\n')
    with pytest.raises(module.PublicationError, match="expected 'absent'"):
        module._publish_pair(
            external_path=external,
            repository_path=repository,
            source=source,
        )


def test_pair_namespace_classifier_is_closed(tmp_path: Path) -> None:
    module = _load_script()
    external = tmp_path / "external.json"
    repository = tmp_path / "repository.json"
    external_stage = tmp_path / module._staging_leaf(external)
    repository_stage = tmp_path / module._staging_leaf(repository)

    assert module._pair_namespace_state(
        external_path=external,
        repository_path=repository,
    ) == "absent"
    external_stage.write_bytes(b'{}\n')
    assert module._pair_namespace_state(
        external_path=external,
        repository_path=repository,
    ) == "external_stage_unresolved"
    external_stage.unlink()
    external.write_bytes(b'{}\n')
    assert module._pair_namespace_state(
        external_path=external,
        repository_path=repository,
    ) == "external_only"
    repository_stage.write_bytes(b'{}\n')
    assert module._pair_namespace_state(
        external_path=external,
        repository_path=repository,
    ) == "external_plus_repository_stage_candidate"
    repository_stage.unlink()
    repository.write_bytes(b'{}\n')
    assert module._pair_namespace_state(
        external_path=external,
        repository_path=repository,
    ) == "complete"
    external_stage.write_bytes(b'{}\n')
    assert module._pair_namespace_state(
        external_path=external,
        repository_path=repository,
    ) == "invalid"


def test_repair_promotes_only_an_exact_repository_stage(tmp_path: Path) -> None:
    module = _load_script()
    record, terminal_source = _record(module)
    source = _canonical(record)
    external = tmp_path / "external.json"
    repository = tmp_path / "repository.json"
    repository_stage = tmp_path / module._staging_leaf(repository)
    module._publish_file_native_no_replace(external, source)
    repository_stage.write_bytes(source)
    repository_stage.chmod(0o600)

    assert module._repair_repository_projection(
        external_path=external,
        repository_path=repository,
        expected_terminal_source=terminal_source,
    ) == source
    assert not repository_stage.exists()
    assert repository.read_bytes() == source

    mismatch_external = tmp_path / "mismatch-external.json"
    mismatch_repository = tmp_path / "mismatch-repository.json"
    mismatch_stage = tmp_path / module._staging_leaf(mismatch_repository)
    module._publish_file_native_no_replace(mismatch_external, source)
    mismatch_stage.write_bytes(b'{}\n')
    mismatch_stage.chmod(0o600)
    with pytest.raises(module.PublicationError, match="differs from external"):
        module._repair_repository_projection(
            external_path=mismatch_external,
            repository_path=mismatch_repository,
            expected_terminal_source=terminal_source,
        )
    assert mismatch_stage.read_bytes() == b'{}\n'
    assert not mismatch_repository.exists()


def test_repair_rejoins_running_publisher_and_rejects_repository_only(
    tmp_path: Path,
) -> None:
    module = _load_script()
    record, terminal_source = _record(module)
    forged = copy.deepcopy(record)
    forged["bindings"]["publisher_sha256"] = "b" * 64
    external = tmp_path / "external.json"
    repository = tmp_path / "repository.json"
    module._publish_file_native_no_replace(external, _canonical(forged))
    with pytest.raises(module.PublicationError, match="running publisher differs"):
        module._repair_repository_projection(
            external_path=external,
            repository_path=repository,
            expected_terminal_source=terminal_source,
        )
    assert not repository.exists()

    repository_only_external = tmp_path / "missing-external.json"
    repository_only = tmp_path / "repository-only.json"
    repository_only.write_bytes(_canonical(record))
    with pytest.raises(module.PublicationError, match="not explicitly repairable"):
        module._repair_repository_projection(
            external_path=repository_only_external,
            repository_path=repository_only,
            expected_terminal_source=terminal_source,
        )


def test_promotion_accepts_observed_inode_move_despite_reported_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_script()
    path = tmp_path / "record.json"
    stage = tmp_path / module._staging_leaf(path)

    def moved_with_error(_parent_fd: int, _source: str, _destination: str):
        os.rename(stage, path)
        return -1, errno.EIO

    monkeypatch.setattr(module, "_native_rename_no_replace", moved_with_error)
    module._publish_file_native_no_replace(path, b'{}\n')
    assert path.read_bytes() == b'{}\n'
    assert not stage.exists()


def test_promotion_rejects_success_without_move_and_retains_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_script()
    path = tmp_path / "record.json"
    stage = tmp_path / module._staging_leaf(path)
    monkeypatch.setattr(
        module,
        "_native_rename_no_replace",
        lambda _parent_fd, _source, _destination: (0, errno.EIO),
    )
    with pytest.raises(module.PublicationError, match="invalid namespace"):
        module._publish_file_native_no_replace(path, b'{}\n')
    assert stage.read_bytes() == b'{}\n'
    assert not path.exists()


def test_promotion_rejects_same_bytes_from_a_different_inode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_script()
    path = tmp_path / "record.json"
    stage = tmp_path / module._staging_leaf(path)

    def substitute(_parent_fd: int, _source: str, _destination: str):
        stage.unlink()
        replacement = tmp_path / "replacement.json"
        replacement.write_bytes(b'{}\n')
        os.rename(replacement, path)
        return 0, errno.EIO

    monkeypatch.setattr(module, "_native_rename_no_replace", substitute)
    with pytest.raises(module.PublicationError, match="invalid namespace"):
        module._publish_file_native_no_replace(path, b'{}\n')
    assert path.read_bytes() == b'{}\n'


def test_destination_competitor_never_replaces_the_held_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_script()
    path = tmp_path / "record.json"
    stage = tmp_path / module._staging_leaf(path)

    def compete(_parent_fd: int, _source: str, _destination: str):
        path.write_bytes(b'{"competitor":true}\n')
        return -1, errno.EEXIST

    monkeypatch.setattr(module, "_native_rename_no_replace", compete)
    with pytest.raises(module.PublicationError, match="invalid namespace"):
        module._publish_file_native_no_replace(path, b'{}\n')
    assert stage.read_bytes() == b'{}\n'
    assert path.read_bytes() == b'{"competitor":true}\n'


def test_publisher_source_names_no_model_cache_network_or_raw_capture_path() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "raw-captures" not in source
    assert "requests" not in source
    assert "transformers" not in source
    assert "torch" not in source
    assert "huggingface" not in source
    assert "subprocess.run" in source
    assert "terminal-result.json" in source


def test_bounded_reader_rejects_symlink_and_oversize(tmp_path: Path) -> None:
    module = _load_script()
    target = tmp_path / "target.json"
    target.write_bytes(b'{"x":1}\n')
    symlink = tmp_path / "symlink.json"
    symlink.symlink_to(target)

    with pytest.raises(module.PublicationError):
        module._read_bounded_regular(symlink, maximum_bytes=1024)
    with pytest.raises(module.PublicationError, match="bounded regular-file"):
        module._read_bounded_regular(target, maximum_bytes=2)

    nonfinite = tmp_path / "nonfinite.json"
    nonfinite.write_bytes(b'{"x":1e400}\n')
    with pytest.raises(module.PublicationError, match="non-canonical JSON value"):
        module._load_canonical(nonfinite)

    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    alias_parent = tmp_path / "alias-parent"
    alias_parent.symlink_to(real_parent, target_is_directory=True)
    with pytest.raises(module.PublicationError, match="directory anchor"):
        module._publish_file_native_no_replace(alias_parent / "record.json", b'{}\n')


def test_git_checks_ignore_caller_repository_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_script()
    for key, value in {
        "PATH": "/definitely/not/git",
        "GIT_DIR": "/tmp/not-a-repository",
        "GIT_WORK_TREE": "/tmp/not-a-worktree",
        "GIT_OBJECT_DIRECTORY": "/tmp/not-objects",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": "/tmp/not-alternates",
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.fsmonitor",
        "GIT_CONFIG_VALUE_0": "true",
    }.items():
        monkeypatch.setenv(key, value)
    assert module._git("rev-parse", "--show-toplevel").decode().strip() == str(ROOT)
    assert SCRIPT.read_text(encoding="utf-8").count("subprocess.run(") == 1


def test_live_repository_projection_is_strict_when_present() -> None:
    module = _load_script()
    repository_output = ROOT / module.REPOSITORY_OUTPUT_RELATIVE
    state = "".join(
        "1" if os.path.lexists(path) else "0"
        for path in (
            ROOT
            / "experiments/pythia/gate_state_development_v0_1/launch-authorization.json",
            ATTEMPT,
            TERMINAL,
            repository_output,
        )
    )
    assert state in {"1110", "1111"}
    if state == "1110":
        return
    record, _source = module._load_canonical(
        repository_output,
        maximum_bytes=module.MAX_NEXT_HYPOTHESES_BYTES,
    )
    _terminal, terminal_source = module._load_canonical(
        TERMINAL,
        maximum_bytes=module.MAX_TERMINAL_BYTES,
    )
    assert module._validate_record(
        record,
        expected_terminal_source=terminal_source,
    ) == record


def test_cli_requires_one_explicit_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_script()
    monkeypatch.setattr("sys.argv", [str(SCRIPT)])
    with pytest.raises(SystemExit):
        module._parse_args()
