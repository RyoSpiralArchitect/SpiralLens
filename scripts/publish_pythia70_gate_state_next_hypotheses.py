#!/usr/bin/env python3
"""Publish the consumed Pythia-70M GateState next-hypothesis receipt.

This is a post-outcome, claim-ineligible planning publisher.  It reads only
tracked canonical JSON records.  It never reads raw captures, model files, a
cache, or a network resource, and it cannot modify the consumed terminal.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_RELATIVE = "scripts/publish_pythia70_gate_state_next_hypotheses.py"
FREEZE_RELATIVE = "protocols/pythia70_gate_state_development_freeze_v0_1.json"
ATTEMPT_RELATIVE = "experiments/pythia/gate_state_development_v0_1/attempt.json"
TERMINAL_RELATIVE = (
    "experiments/pythia/gate_state_development_v0_1/terminal-result.json"
)
REPOSITORY_OUTPUT_RELATIVE = (
    "experiments/pythia/gate_state_development_v0_1/next-hypotheses.json"
)
EXTERNAL_OUTPUT = Path(
    "/Users/ryohiga/SpiralReality/"
    "spirallens-pythia70-gate-state-development-v0-1-next-hypotheses.json"
)
EXTERNAL_STORE = Path(
    "/Users/ryohiga/SpiralReality/"
    "spirallens-pythia70-gate-state-development-v0-1-store"
)
EXTERNAL_ATTEMPT = EXTERNAL_STORE / "attempt.json"
EXTERNAL_TERMINAL = EXTERNAL_STORE / "terminal-result.json"

EXPECTED_TERMINAL_SHA256 = (
    "ccf0daf3ae4d826bdd35f0d16bb91381e79335aa727556535a4bf86ff14f001f"
)
EXPECTED_ATTEMPT_SHA256 = (
    "fc9139165888c705837a56d90f16cae542fb796b5907577d73e9ff75bee9af59"
)
EXPECTED_FREEZE_SHA256 = (
    "fe85ebb15e0a9794a02d72b4fdefd0178b52662528e8e066530d873516b52452"
)
EXPECTED_CELL_COUNTS = {
    "fail": 6,
    "insufficient": 761,
    "not_run": 0,
    "pass": 127,
}
EXPECTED_GATE_COUNTS = {
    "address_loop_support": {"insufficient": 216},
    "address_ring_phase_resolution": {"insufficient": 216},
    "capture_integrity": {"pass": 48},
    "continuous_holonomy_consistency": {"insufficient": 54},
    "f2_section_support": {"insufficient": 18, "pass": 18},
    "f4_tensor_support": {"insufficient": 18, "pass": 18},
    "graph_family_agreement": {"fail": 6, "insufficient": 16, "pass": 2},
    "low_amplitude_set_repeatability": {"insufficient": 7, "pass": 29},
    "measurable_drift": {"pass": 12},
    "negative_controls": {"insufficient": 216},
}
EXPECTED_RING_CASCADE_GATES = (
    "address_loop_support",
    "continuous_holonomy_consistency",
    "address_ring_phase_resolution",
    "negative_controls",
)
EXPECTED_RING_CASCADE_COUNT = 702
EXPECTED_POSITIVE_CYCLE_RANK_GRAPHS = 16
EXPECTED_TOTAL_CYCLE_RANK = 2592
EXPECTED_GRAPH_COUNT = 18
EXPECTED_VERTEX_COUNT = 49

SCHEMA_VERSION = "spirallens.pythia70-gate-state-next-hypotheses.v0.1"
RECORD_ID = "pythia70-gate-state-development-v0.1-next-hypotheses"
DECISION_DATE = "2026-08-24"
MAX_NEXT_HYPOTHESES_BYTES = 262_144
MAX_TERMINAL_BYTES = 1_048_576
MAX_ATTEMPT_BYTES = 262_144
MAX_FREEZE_BYTES = 262_144
_STAGING_SUFFIX = ".staging-v0-1"
_DARWIN_RENAME_EXCL = 0x00000004
_DARWIN_RENAME_NOFOLLOW_ANY = 0x00000010
_DARWIN_RENAME_RESOLVE_BENEATH = 0x00000020
_LINUX_RENAME_NOREPLACE = 0x00000001
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")

EXPECTED_CLAIM_BOUNDARY = {
    "D7_state_change": False,
    "D8_state_change": False,
    "Pythia160_protocol_change": False,
    "SCI_stage_change": False,
    "VOY_stage_change": False,
    "claim_ceiling": "level_0",
    "claim_delta": "none",
    "core_score_or_core_candidate_constructed": False,
    "evidence_eligible": False,
    "integer_output_authority": False,
    "milestone_credit": "none",
    "negative_space_map_is_next_hypothesis_input_only": True,
    "order_parameter_field_constructed": False,
    "sampled_winding_or_winding_estimate_constructed": False,
    "scientific_authority": False,
    "semantic_authority": False,
    "support_compatibility_portability_or_API_claim": False,
    "topology_authority": False,
}


class PublicationError(RuntimeError):
    """Raised when publication cannot preserve the frozen boundary."""


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise PublicationError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _canonical_json_bytes(document: object) -> bytes:
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


def _read_bounded_regular(path: Path, *, maximum_bytes: int) -> bytes:
    if not path.is_absolute():
        raise PublicationError(f"path must be absolute: {path}")
    if type(maximum_bytes) is not int or maximum_bytes <= 0:
        raise PublicationError("maximum_bytes must be positive")
    parent = path.parent
    try:
        parent_path_stat = os.stat(parent, follow_symlinks=False)
        parent_descriptor = os.open(
            parent,
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0),
        )
    except OSError as error:
        raise PublicationError(f"cannot hold parent directory for {path}") from error
    try:
        parent_fd_stat = os.fstat(parent_descriptor)
        if (
            not stat.S_ISDIR(parent_path_stat.st_mode)
            or not stat.S_ISDIR(parent_fd_stat.st_mode)
            or (parent_path_stat.st_dev, parent_path_stat.st_ino)
            != (parent_fd_stat.st_dev, parent_fd_stat.st_ino)
        ):
            raise PublicationError(f"parent directory identity differs for {path}")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
        descriptor = os.open(path.name, flags, dir_fd=parent_descriptor)
        try:
            before = os.fstat(descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or before.st_size <= 0
                or before.st_size > maximum_bytes
            ):
                raise PublicationError(f"bounded regular-file contract failed for {path}")
            chunks: list[bytes] = []
            remaining = before.st_size
            while remaining:
                chunk = os.read(descriptor, min(remaining, 65_536))
                if not chunk:
                    raise PublicationError(f"short read from {path}")
                chunks.append(chunk)
                remaining -= len(chunk)
            if os.read(descriptor, 1):
                raise PublicationError(f"file grew while reading {path}")
            after = os.fstat(descriptor)
            if (
                (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            ):
                raise PublicationError(f"file identity changed while reading {path}")
            return b"".join(chunks)
        finally:
            os.close(descriptor)
    except OSError as error:
        raise PublicationError(f"cannot read {path}") from error
    finally:
        os.close(parent_descriptor)


def _load_canonical(
    path: Path,
    *,
    maximum_bytes: int = MAX_TERMINAL_BYTES,
) -> tuple[dict[str, object], bytes]:
    try:
        source = _read_bounded_regular(path, maximum_bytes=maximum_bytes)
    except PublicationError:
        raise
    try:
        value = json.loads(
            source,
            object_pairs_hook=_strict_object,
            parse_constant=lambda value: (_ for _ in ()).throw(
                PublicationError(f"non-standard JSON constant {value!r}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PublicationError(f"{path} is not strict JSON") from error
    if type(value) is not dict:
        raise PublicationError(f"{path} must contain a JSON object")
    try:
        canonical = _canonical_json_bytes(value)
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise PublicationError(f"{path} contains a non-canonical JSON value") from error
    if canonical != source:
        raise PublicationError(f"{path} is not canonical JSON")
    return value, source


def _sha256(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def _exact_keys(
    value: object,
    expected: tuple[str, ...],
    *,
    label: str,
) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise PublicationError(f"{label} must be a string-keyed object")
    if set(value) != set(expected):
        raise PublicationError(f"{label} fields differ from the closed schema")
    return value


def _string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise PublicationError(f"{label} must be a non-empty trimmed string")
    return value


def _sha(value: object, *, label: str) -> str:
    text = _string(value, label=label)
    if _SHA256.fullmatch(text) is None:
        raise PublicationError(f"{label} must be a lowercase SHA-256")
    return text


def _false(value: object, *, label: str) -> bool:
    if type(value) is not bool or value:
        raise PublicationError(f"{label} must be false")
    return False


def _true(value: object, *, label: str) -> bool:
    if type(value) is not bool or not value:
        raise PublicationError(f"{label} must be true")
    return True


def _integer(value: object, *, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise PublicationError(f"{label} must be an integer >= {minimum}")
    return value


def _deep_exact_equal(left: object, right: object) -> bool:
    """Compare JSON values without Python's ``False == 0`` coercion."""

    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        assert isinstance(right, dict)
        return set(left) == set(right) and all(
            _deep_exact_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        assert isinstance(right, list)
        return len(left) == len(right) and all(
            _deep_exact_equal(one, two) for one, two in zip(left, right, strict=True)
        )
    return bool(left == right)


def _require_exact_value(left: object, right: object, *, label: str) -> None:
    if not _deep_exact_equal(left, right):
        raise PublicationError(f"{label} differs")


def _git_environment() -> dict[str, str]:
    return {
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_CONFIG_COUNT": "0",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_LITERAL_PATHSPECS": "1",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_PAGER": "cat",
        "GIT_TERMINAL_PROMPT": "0",
        "LANG": "C",
        "LC_ALL": "C",
        "PAGER": "cat",
        "PATH": "/usr/bin:/bin",
    }


def _run_git(*arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        (
            "/usr/bin/git",
            "--no-replace-objects",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.untrackedCache=false",
            "-c",
            "core.attributesFile=/dev/null",
            "--no-optional-locks",
            *arguments,
        ),
        cwd=ROOT,
        env=_git_environment(),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _git(*arguments: str) -> bytes:
    completed = _run_git(*arguments)
    if completed.returncode != 0:
        raise PublicationError(
            f"git {' '.join(arguments)} failed: "
            f"{completed.stderr.decode('utf-8', errors='replace').strip()}"
        )
    return completed.stdout


def _historical_path_exists(commit: str, path: str) -> bool:
    output = _git("ls-tree", "-z", "--full-tree", commit, "--", path)
    if not output:
        return False
    entries = [entry for entry in output.split(b"\0") if entry]
    if len(entries) != 1 or not entries[0].endswith(b"\t" + path.encode("utf-8")):
        raise PublicationError("historical artifact tree entry is ambiguous")
    return True


def _require_clean_committed_source() -> tuple[str, str]:
    status = _git("status", "--porcelain", "--untracked-files=all")
    if status:
        raise PublicationError("publisher requires a clean worktree")
    commit = _git("rev-parse", "HEAD").decode("ascii").strip()
    if _COMMIT.fullmatch(commit) is None:
        raise PublicationError("HEAD is not a full lowercase commit")
    script_source = _read_bounded_regular(
        ROOT / SCRIPT_RELATIVE,
        maximum_bytes=MAX_NEXT_HYPOTHESES_BYTES,
    )
    committed = _git("cat-file", "blob", f"{commit}:{SCRIPT_RELATIVE}")
    if committed != script_source:
        raise PublicationError("publisher bytes differ from committed HEAD")
    if _historical_path_exists(commit, REPOSITORY_OUTPUT_RELATIVE):
        raise PublicationError("publisher commit already contains the output artifact")
    return commit, _sha256(script_source)


def _require_publisher_lineage(commit: object, source_sha256: object) -> None:
    commit_text = _string(commit, label="publisher_implementation_commit")
    if _COMMIT.fullmatch(commit_text) is None:
        raise PublicationError("publisher implementation commit is invalid")
    expected_sha = _sha(source_sha256, label="publisher_sha256")
    ancestor = _run_git("merge-base", "--is-ancestor", commit_text, "HEAD")
    if ancestor.returncode != 0:
        raise PublicationError("publisher implementation commit is not an ancestor")
    historical = _git("cat-file", "blob", f"{commit_text}:{SCRIPT_RELATIVE}")
    if _sha256(historical) != expected_sha:
        raise PublicationError("publisher historical blob differs from its binding")
    if _historical_path_exists(commit_text, REPOSITORY_OUTPUT_RELATIVE):
        raise PublicationError("publisher commit did not precede artifact publication")


def _require_external_store_matches(
    *,
    attempt_source: bytes,
    terminal_source: bytes,
) -> None:
    external_attempt = _read_bounded_regular(
        EXTERNAL_ATTEMPT,
        maximum_bytes=MAX_ATTEMPT_BYTES,
    )
    external_terminal = _read_bounded_regular(
        EXTERNAL_TERMINAL,
        maximum_bytes=MAX_TERMINAL_BYTES,
    )
    if external_attempt != attempt_source:
        raise PublicationError("external-store attempt differs from repository")
    if external_terminal != terminal_source:
        raise PublicationError("external-store terminal differs from repository")


def _counter(records: object, *, label: str) -> dict[str, int]:
    if not isinstance(records, list):
        raise PublicationError(f"{label} must be a list")
    states: Counter[str] = Counter()
    for record in records:
        if not isinstance(record, Mapping):
            raise PublicationError(f"{label} entries must be objects")
        state = record.get("state")
        if state not in {"pass", "fail", "insufficient", "not_run"}:
            raise PublicationError(f"{label} contains an unknown GateState")
        states[str(state)] += 1
    return {state: states[state] for state in sorted(states)}


def _terminal_observation(
    terminal: Mapping[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    if terminal.get("execution_terminal") != "complete":
        raise PublicationError("terminal execution state is not complete")
    if terminal.get("terminal_fold") != "fail" or terminal.get("error") is not None:
        raise PublicationError("terminal does not retain the frozen fail fold")
    if terminal.get("freeze_id") != "pythia70-gate-state-development-v0.1":
        raise PublicationError("terminal freeze identity differs")
    if terminal.get("attempt_id") != "pythia70-gate-state-development-v0.1-attempt-1":
        raise PublicationError("terminal attempt identity differs")
    if terminal.get("launch_id") != "pythia70-gate-state-development-launch-v0.1":
        raise PublicationError("terminal launch identity differs")
    _require_exact_value(
        terminal.get("claim_boundary"),
        EXPECTED_CLAIM_BOUNDARY,
        label="terminal claim boundary",
    )

    cells = terminal.get("cell_records")
    gates = terminal.get("gate_records")
    graphs = terminal.get("graph_receipts")
    captures = terminal.get("capture_manifest")
    if not isinstance(cells, list) or not isinstance(gates, list):
        raise PublicationError("terminal cells and gates must be lists")
    if not isinstance(graphs, list) or not isinstance(captures, list):
        raise PublicationError("terminal graphs and captures must be lists")
    cell_counts = _counter(cells, label="cell_records")
    _require_exact_value(
        {state: cell_counts.get(state, 0) for state in EXPECTED_CELL_COUNTS},
        EXPECTED_CELL_COUNTS,
        label="terminal cell counts",
    )

    by_gate: dict[str, list[Mapping[str, object]]] = {}
    for cell in cells:
        assert isinstance(cell, Mapping)
        gate_id = _string(cell.get("gate_id"), label="cell gate_id")
        by_gate.setdefault(gate_id, []).append(cell)
    observed_gate_counts = {
        gate_id: _counter(records, label=f"cells[{gate_id}]")
        for gate_id, records in sorted(by_gate.items())
    }
    _require_exact_value(
        observed_gate_counts,
        EXPECTED_GATE_COUNTS,
        label="per-gate counts",
    )

    ring_count = sum(len(by_gate[gate_id]) for gate_id in EXPECTED_RING_CASCADE_GATES)
    if ring_count != EXPECTED_RING_CASCADE_COUNT:
        raise PublicationError("ring prerequisite cascade count differs")

    graph_cycle_ranks: list[dict[str, object]] = []
    for record in graphs:
        if not isinstance(record, Mapping):
            raise PublicationError("graph receipt entries must be objects")
        receipt = record.get("receipt")
        if not isinstance(receipt, Mapping):
            raise PublicationError("graph receipt body must be an object")
        arrays = receipt.get("arrays")
        if not isinstance(arrays, Mapping):
            raise PublicationError("graph receipt arrays must be an object")
        degree = arrays.get("degree")
        if not isinstance(degree, Mapping) or degree.get("shape") != [EXPECTED_VERTEX_COUNT]:
            raise PublicationError("graph receipt vertex count differs")
        edge_count = _integer(receipt.get("edge_count"), label="edge_count")
        component_count = _integer(
            receipt.get("component_count"), label="component_count", minimum=1
        )
        cycle_rank = edge_count - EXPECTED_VERTEX_COUNT + component_count
        if cycle_rank < 0:
            raise PublicationError("graph cycle rank cannot be negative")
        graph_cycle_ranks.append(
            {
                "component_count": component_count,
                "cycle_rank": cycle_rank,
                "edge_count": edge_count,
                "graph_family": _string(
                    record.get("graph_family"), label="graph_family"
                ),
                "layer_id": _integer(record.get("layer_id"), label="layer_id"),
                "vertex_count": EXPECTED_VERTEX_COUNT,
            }
        )
    if len(graph_cycle_ranks) != EXPECTED_GRAPH_COUNT:
        raise PublicationError("graph count differs from the frozen result")
    if sum(item["cycle_rank"] > 0 for item in graph_cycle_ranks) != (
        EXPECTED_POSITIVE_CYCLE_RANK_GRAPHS
    ):
        raise PublicationError("positive-cycle-rank graph count differs")
    if sum(int(item["cycle_rank"]) for item in graph_cycle_ranks) != (
        EXPECTED_TOTAL_CYCLE_RANK
    ):
        raise PublicationError("total graph cycle rank differs")

    resource_use = terminal.get("resource_use")
    if not isinstance(resource_use, Mapping):
        raise PublicationError("resource_use must be an object")
    return {
        "capture_record_count": len(captures),
        "cell_count": len(cells),
        "cell_state_counts": EXPECTED_CELL_COUNTS,
        "error": None,
        "execution_terminal": "complete",
        "gate_count": len(gates),
        "gate_state_counts": EXPECTED_GATE_COUNTS,
        "graph_receipt_count": len(graphs),
        "resource_use": {
            "forward_batches": resource_use.get("forward_batches"),
            "hard_limit_breaches": resource_use.get("hard_limit_breaches"),
            "model_loads": resource_use.get("model_loads"),
            "raw_capture_bytes": resource_use.get("raw_capture_bytes"),
        },
        "terminal_fold": "fail",
    }, {
        "cycle_rank_formula": "edge_count-vertex_count+component_count",
        "graph_cycle_ranks": graph_cycle_ranks,
        "graphs_with_positive_cycle_rank": EXPECTED_POSITIVE_CYCLE_RANK_GRAPHS,
        "interpretation": (
            "candidate_graphs_have_graph_theoretic_cycles_while_the_frozen_"
            "artificial_address_rings_remained_unsupported"
        ),
        "ring_prerequisite_cascade_cell_count": EXPECTED_RING_CASCADE_COUNT,
        "ring_prerequisite_cascade_gate_ids": list(EXPECTED_RING_CASCADE_GATES),
        "ring_prerequisite_cascade_insufficient_denominator": (
            EXPECTED_CELL_COUNTS["insufficient"]
        ),
        "total_fundamental_cycle_rank": EXPECTED_TOTAL_CYCLE_RANK,
    }


def _hypotheses() -> list[dict[str, object]]:
    return [
        {
            "hypothesis_id": "h-address-grid-mismatch",
            "prediction": (
                "field_blind_canonical_graph_derived_cycles_restore_structural_"
                "loop_support"
            ),
            "falsifier": (
                "matched_graphs_retain_cycle_rank_but_graph_derived_cycles_do_not_"
                "reach_the_declared_support_floor"
            ),
            "discriminating_next_test": "canonical_graph_cycle_support_on_phantoms",
            "cannot_establish": "model_geometry_or_topology",
        },
        {
            "hypothesis_id": "h-graph-scale-mismatch",
            "prediction": (
                "nuisance_matched_distinct_graph_families_recover_cross_family_"
                "evaluability_on_held_out_synthetic_phantoms"
            ),
            "falsifier": (
                "no_scale_triplet_can_match_support_without_collapsing_graph_"
                "diversity"
            ),
            "discriminating_next_test": "field_blind_joint_graph_scale_selector",
            "cannot_establish": "a_winning_subject_graph_family",
        },
        {
            "hypothesis_id": "h-frame-gauge-instability",
            "prediction": (
                "known_o2_rotation_reflection_and_reverse_controls_separate_"
                "projector_stability_from_orientation_failure"
            ),
            "falsifier": (
                "orientation_remains_unresolved_on_known_identifiable_o2_controls"
            ),
            "discriminating_next_test": "common_graph_varying_known_frame_controls",
            "cannot_establish": "subject_phase_or_charge",
        },
        {
            "hypothesis_id": "h-representation-graph-sensitivity",
            "prediction": (
                "common_graph_varying_frame_projector_distance_and_principal_angle_"
                "controls_pass_but_varying_matched_graphs_retain_substantive_"
                "disagreement_in_a_later_new_identity_pythia70_run"
            ),
            "falsifier": (
                "matched_graphs_remove_disagreement_in_a_later_new_identity_"
                "pythia70_run"
            ),
            "discriminating_next_test": (
                "model_free_precondition_then_new_identity_pythia70_successor"
            ),
            "cannot_establish": "semantic_instability",
        },
        {
            "hypothesis_id": "h-genuine-support-scarcity",
            "prediction": (
                "no_frozen_scale_triplet_meets_support_budget_and_graph_diversity_"
                "on_calibration_and_confirmation_splits"
            ),
            "falsifier": (
                "one_fixed_selector_meets_every_support_and_diversity_gate_on_both_"
                "splits"
            ),
            "discriminating_next_test": "bounded_selector_calibration_and_confirmation",
            "cannot_establish": "absence_of_a_model_native_signal",
        },
        {
            "hypothesis_id": "h-no-stable-structure-at-tested-resolution",
            "prediction": (
                "after_model_free_preconditions_pass_a_later_new_identity_pythia70_"
                "run_remains_evaluable_but_positive_structure_is_not_stable"
            ),
            "falsifier": (
                "a_later_new_identity_pythia70_run_shows_preregistered_stability_"
                "across_required_graph_frame_and_control_cells"
            ),
            "discriminating_next_test": (
                "later_claim_ineligible_pythia70_successor_only_not_pr2"
            ),
            "cannot_establish": "global_absence_of_model_structure",
        },
    ]


def _next_experiment() -> dict[str, object]:
    return {
        "experiment_id": "model-free-evaluability-calibration-v0.1",
        "status": "planned_not_frozen_not_run",
        "design": {
            "calibration_and_confirmation_roles_disjoint": True,
            "canonical_graph_derived_cycles_field_blind": True,
            "crossed_axes": [
                "field_estimation_graph_x_cycle_construction_graph",
                "common_graph_x_varying_frame",
                "common_frame_x_varying_graph",
            ],
            "graph_families": [
                "mutual-knn",
                "fixed-radius",
                "shared-neighbor",
            ],
            "scale_selection_reads": [
                "common_vertex_support",
                "component_coverage",
                "two_core_and_cycle_coverage",
                "declared_edge_or_degree_budget",
                "pairwise_graph_diversity",
            ],
            "scale_selection_forbidden_reads": [
                "field",
                "core",
                "holonomy",
                "phase",
                "winding",
                "charge",
                "pythia_terminal_candidate_values",
            ],
        },
        "graph_selector": {
            "candidate_sets": {
                "fixed_radius": (
                    "all_unique_finite_pairwise_distances_that_can_meet_the_"
                    "per_graph_edge_budget"
                ),
                "mutual_knn_neighbor_count_inclusive": [2, 16],
                "shared_neighbor_count_inclusive": [2, 16],
                "shared_minimum_shared_neighbors": "integers_1_through_neighbor_count",
            },
            "per_graph_requirements": {
                "cycle_rank_minimum": 2,
                "largest_component_vertex_count_minimum": 45,
                "mean_degree_inclusive": [4.0, 8.0],
                "mean_degree_target": 6.0,
                "two_core_vertex_count_minimum": 40,
                "vertex_count_exact": 49,
            },
            "triplet_requirements": {
                "common_two_core_intersection_minimum": 35,
                "edge_count_maximum_to_minimum_ratio_maximum": 1.25,
                "largest_component_vertex_count_spread_maximum": 2,
                "matched_cycle_classes": ["central", "wide"],
                "max_domain_edges_per_graph_edge": 4,
                "pairwise_edge_jaccard_maximum": 0.85,
                "pairwise_edge_sets_must_differ": True,
                "two_core_vertex_count_spread_maximum": 4,
            },
            "lexicographic_objective": [
                "edge_count_spread",
                "sum_absolute_mean_degree_minus_six",
                "negative_common_two_core_count",
                "component_count_sum",
                "canonical_parameter_tuple",
            ],
            "jaccard_is_not_an_optimization_objective": True,
        },
        "controls": [
            "known_positive_connection",
            "zero_holonomy_finite_amplitude_null",
            "radial_amplitude_depression_without_holonomy",
            "pure_so2_gauge",
            "degree_preserving_rewire",
            "amplitude_label_permutation",
            "orientation_reversal",
            "density_warp_confirmation",
            "joint_vertex_permutation",
            "ambient_orthogonal_transform",
            "global_norm_scaling",
            "collapsed_cycleless_phantom",
            "field_only_shuffle",
            "zero_amplitude",
            "low_coherence",
            "non_orientable_frame",
        ],
        "execution_boundary": {
            "execution_authorized": False,
            "model_access_authorized": False,
            "network_access_authorized": False,
            "pythia_raw_capture_access_authorized": False,
            "subject_data_access_authorized": False,
        },
        "exposure_boundary": {
            "cryptographic_unseen_proof": False,
            "exact_confirmation_inputs_must_be_frozen_before_access": True,
            "operator_prior_model_free_calibration_outcome_exposure": True,
            "pythia_outcome_may_not_select_confirmation_inputs": True,
        },
        "readout_threshold_rule": {
            "algebraic_gauge_and_reversal_error_cycles_maximum": 1e-8,
            "graph_family_span_cap_cycles": 0.1,
            "graph_family_span_formula": (
                "max_1e-8_or_1.25_times_selection_worst_error"
            ),
            "oracle_and_null_cap_cycles": 0.05,
            "oracle_and_null_formula": (
                "max_1e-8_or_1.25_times_selection_worst_error"
            ),
            "selection_cap_breach_state": "insufficient_calibration_resolution",
        },
        "stop_rules": [
            "stop_insufficient_if_no_distinct_three_family_scale_triplet_meets_all_structural_nuisance_targets",
            "stop_fail_if_a_known_positive_or_required_null_control_is_wrong",
            "stop_insufficient_if_orientation_or_reverse_consistency_is_unresolved",
            "stop_before_any_model_run_if_held_out_confirmation_does_not_pass",
        ],
        "successor_if_pass": (
            "new_identity_disjoint_context_pythia70_claim_ineligible_exact_one_"
            "successor_requiring_separate_dated_decision"
        ),
    }


def _forbidden_uses() -> list[str]:
    return sorted(
        [
            "change_or_refold_the_consumed_terminal",
            "drop_a_failed_layer_or_graph_family",
            "drop_f2_or_f4_or_select_a_winner",
            "reconstruct_or_rerun_verified_b_d7",
            "reuse_pythia_raw_captures_as_new_evidence",
            "select_or_unlock_pythia160_sci_s1_or_sci_s2",
            "treat_insufficient_as_signal_absence",
        ]
    )


def _build_record(
    *,
    terminal: Mapping[str, object],
    terminal_source: bytes,
    freeze_source: bytes,
    attempt_source: bytes,
    publisher_commit: str,
    publisher_sha256: str,
) -> dict[str, object]:
    if _sha256(terminal_source) != EXPECTED_TERMINAL_SHA256:
        raise PublicationError("terminal SHA-256 differs from the frozen result")
    if _sha256(attempt_source) != EXPECTED_ATTEMPT_SHA256:
        raise PublicationError("attempt SHA-256 differs from the frozen attempt")
    if _sha256(freeze_source) != EXPECTED_FREEZE_SHA256:
        raise PublicationError("freeze SHA-256 differs from the frozen source")
    if _COMMIT.fullmatch(publisher_commit) is None:
        raise PublicationError("publisher_commit must be a lowercase commit")
    _sha(publisher_sha256, label="publisher_sha256")
    terminal_observation, structural = _terminal_observation(terminal)
    return {
        "bindings": {
            "attempt_path": ATTEMPT_RELATIVE,
            "attempt_sha256": EXPECTED_ATTEMPT_SHA256,
            "external_attempt_path": str(EXTERNAL_ATTEMPT),
            "external_next_hypotheses_path": str(EXTERNAL_OUTPUT),
            "external_terminal_path": str(EXTERNAL_TERMINAL),
            "freeze_path": FREEZE_RELATIVE,
            "freeze_sha256": EXPECTED_FREEZE_SHA256,
            "publisher_implementation_commit": publisher_commit,
            "publisher_path": SCRIPT_RELATIVE,
            "publisher_sha256": publisher_sha256,
            "repository_next_hypotheses_path": REPOSITORY_OUTPUT_RELATIVE,
            "terminal_path": TERMINAL_RELATIVE,
            "terminal_sha256": EXPECTED_TERMINAL_SHA256,
        },
        "chronology": {
            "cryptographic_unseen_proof": False,
            "independent": False,
            "operator_prior_model_free_calibration_outcome_exposure": True,
            "post_outcome": True,
            "preregistered": False,
            "publication_wall_clock_attested": False,
            "terminal_result_preexisted": True,
        },
        "claim_boundary": EXPECTED_CLAIM_BOUNDARY,
        "competing_hypotheses": _hypotheses(),
        "decision_date": DECISION_DATE,
        "derived_structural_diagnostics": structural,
        "forbidden_uses": _forbidden_uses(),
        "next_experiment": _next_experiment(),
        "planning_authority": {
            "calibration_execution_authorized": False,
            "f2_or_f4_winner_selected": False,
            "fresh_pythia70_execution_authorized": False,
            "pythia160_or_sci_gate_advanced": False,
            "raw_capture_reuse_authorized": False,
            "verified_b_reexecution_authorized": False,
        },
        "publication_contract": {
            "canonical_byte_limit": MAX_NEXT_HYPOTHESES_BYTES,
            "dynamic_timestamp_in_payload": False,
            "external_only_state": "repository_projection_pending_repairable",
            "external_record_is_authoritative_after_publish": True,
            "external_stage_unresolved_action": (
                "manual_review_without_cleanup_replacement_or_automatic_resume"
            ),
            "external_then_repository_order": True,
            "invalid_pair_state_action": "fail_closed_without_mutation",
            "native_file_rename_no_replace": True,
            "pair_namespace_states": [
                "absent",
                "complete",
                "external_only",
                "external_stage_unresolved",
                "external_plus_repository_stage_candidate",
                "invalid",
            ],
            "repair_may_only_publish_validated_external_bytes_no_replace": True,
            "repairable_pair_states": [
                "external_only",
                "external_plus_repository_stage_candidate_after_exact_byte_validation",
            ],
            "repository_projection_if_present_must_be_byte_identical": True,
        },
        "record_id": RECORD_ID,
        "schema_version": SCHEMA_VERSION,
        "state_transition": {
            "calibration_state": "planned_not_frozen_not_run",
            "from_repository_state": "1110",
            "target_repository_state": "1111",
            "terminal_lifecycle": "terminal_consumed",
        },
        "status": "published_post_outcome_claim_ineligible_planning",
        "terminal_observation": terminal_observation,
    }


def _validate_record(
    document: object,
    *,
    expected_terminal_source: bytes,
) -> Mapping[str, object]:
    record = _exact_keys(
        document,
        (
            "bindings",
            "chronology",
            "claim_boundary",
            "competing_hypotheses",
            "decision_date",
            "derived_structural_diagnostics",
            "forbidden_uses",
            "next_experiment",
            "planning_authority",
            "publication_contract",
            "record_id",
            "schema_version",
            "state_transition",
            "status",
            "terminal_observation",
        ),
        label="next-hypothesis record",
    )
    if record["schema_version"] != SCHEMA_VERSION or record["record_id"] != RECORD_ID:
        raise PublicationError("record identity differs")
    if record["status"] != "published_post_outcome_claim_ineligible_planning":
        raise PublicationError("record status differs")
    if record["decision_date"] != DECISION_DATE:
        raise PublicationError("decision date differs")
    chronology = _exact_keys(
        record["chronology"],
        (
            "cryptographic_unseen_proof",
            "independent",
            "operator_prior_model_free_calibration_outcome_exposure",
            "post_outcome",
            "preregistered",
            "publication_wall_clock_attested",
            "terminal_result_preexisted",
        ),
        label="chronology",
    )
    _false(chronology["independent"], label="chronology.independent")
    _false(
        chronology["cryptographic_unseen_proof"],
        label="chronology.cryptographic_unseen_proof",
    )
    _true(
        chronology["operator_prior_model_free_calibration_outcome_exposure"],
        label="chronology.operator_prior_model_free_calibration_outcome_exposure",
    )
    _true(chronology["post_outcome"], label="chronology.post_outcome")
    _false(chronology["preregistered"], label="chronology.preregistered")
    _false(
        chronology["publication_wall_clock_attested"],
        label="chronology.publication_wall_clock_attested",
    )
    _true(
        chronology["terminal_result_preexisted"],
        label="chronology.terminal_result_preexisted",
    )
    _require_exact_value(
        record["claim_boundary"], EXPECTED_CLAIM_BOUNDARY, label="claim boundary"
    )
    planning_authority = _exact_keys(
        record["planning_authority"],
        (
            "calibration_execution_authorized",
            "f2_or_f4_winner_selected",
            "fresh_pythia70_execution_authorized",
            "pythia160_or_sci_gate_advanced",
            "raw_capture_reuse_authorized",
            "verified_b_reexecution_authorized",
        ),
        label="planning_authority",
    )
    for key, value in planning_authority.items():
        _false(value, label=f"planning_authority.{key}")
    bindings = _exact_keys(
        record["bindings"],
        (
            "attempt_path",
            "attempt_sha256",
            "external_attempt_path",
            "external_next_hypotheses_path",
            "external_terminal_path",
            "freeze_path",
            "freeze_sha256",
            "publisher_implementation_commit",
            "publisher_path",
            "publisher_sha256",
            "repository_next_hypotheses_path",
            "terminal_path",
            "terminal_sha256",
        ),
        label="bindings",
    )
    exact_binding_values = {
        "attempt_path": ATTEMPT_RELATIVE,
        "attempt_sha256": EXPECTED_ATTEMPT_SHA256,
        "external_attempt_path": str(EXTERNAL_ATTEMPT),
        "external_next_hypotheses_path": str(EXTERNAL_OUTPUT),
        "external_terminal_path": str(EXTERNAL_TERMINAL),
        "freeze_path": FREEZE_RELATIVE,
        "freeze_sha256": EXPECTED_FREEZE_SHA256,
        "publisher_path": SCRIPT_RELATIVE,
        "repository_next_hypotheses_path": REPOSITORY_OUTPUT_RELATIVE,
        "terminal_path": TERMINAL_RELATIVE,
        "terminal_sha256": EXPECTED_TERMINAL_SHA256,
    }
    if any(bindings[key] != value for key, value in exact_binding_values.items()):
        raise PublicationError("exact path or digest binding differs")
    if bindings["terminal_sha256"] != _sha256(expected_terminal_source):
        raise PublicationError("terminal SHA binding differs")
    _require_publisher_lineage(
        bindings["publisher_implementation_commit"],
        bindings["publisher_sha256"],
    )
    hypotheses = record["competing_hypotheses"]
    if not isinstance(hypotheses, list):
        raise PublicationError("competing hypotheses must be a list")
    _require_exact_value(
        hypotheses,
        _hypotheses(),
        label="competing hypotheses",
    )
    _require_exact_value(
        record["next_experiment"],
        _next_experiment(),
        label="next experiment",
    )
    observation, structural = _terminal_observation(
        json.loads(expected_terminal_source, object_pairs_hook=_strict_object)
    )
    _require_exact_value(
        record["terminal_observation"],
        observation,
        label="terminal observation projection",
    )
    _require_exact_value(
        record["derived_structural_diagnostics"],
        structural,
        label="structural diagnostic projection",
    )
    forbidden = record["forbidden_uses"]
    _require_exact_value(forbidden, _forbidden_uses(), label="forbidden uses")
    state_transition = _exact_keys(
        record["state_transition"],
        (
            "calibration_state",
            "from_repository_state",
            "target_repository_state",
            "terminal_lifecycle",
        ),
        label="state_transition",
    )
    _require_exact_value(
        state_transition,
        {
            "calibration_state": "planned_not_frozen_not_run",
            "from_repository_state": "1110",
            "target_repository_state": "1111",
            "terminal_lifecycle": "terminal_consumed",
        },
        label="state transition",
    )
    publication = _exact_keys(
        record["publication_contract"],
        (
            "canonical_byte_limit",
            "dynamic_timestamp_in_payload",
            "external_only_state",
            "external_record_is_authoritative_after_publish",
            "external_stage_unresolved_action",
            "external_then_repository_order",
            "invalid_pair_state_action",
            "native_file_rename_no_replace",
            "pair_namespace_states",
            "repair_may_only_publish_validated_external_bytes_no_replace",
            "repairable_pair_states",
            "repository_projection_if_present_must_be_byte_identical",
        ),
        label="publication_contract",
    )
    _require_exact_value(
        publication,
        {
            "canonical_byte_limit": MAX_NEXT_HYPOTHESES_BYTES,
            "dynamic_timestamp_in_payload": False,
            "external_only_state": "repository_projection_pending_repairable",
            "external_record_is_authoritative_after_publish": True,
            "external_stage_unresolved_action": (
                "manual_review_without_cleanup_replacement_or_automatic_resume"
            ),
            "external_then_repository_order": True,
            "invalid_pair_state_action": "fail_closed_without_mutation",
            "native_file_rename_no_replace": True,
            "pair_namespace_states": [
                "absent",
                "complete",
                "external_only",
                "external_stage_unresolved",
                "external_plus_repository_stage_candidate",
                "invalid",
            ],
            "repair_may_only_publish_validated_external_bytes_no_replace": True,
            "repairable_pair_states": [
                "external_only",
                "external_plus_repository_stage_candidate_after_exact_byte_validation",
            ],
            "repository_projection_if_present_must_be_byte_identical": True,
        },
        label="publication contract",
    )
    return record


def _write_all(file_descriptor: int, source: bytes) -> None:
    offset = 0
    while offset < len(source):
        written = os.write(file_descriptor, source[offset:])
        if written <= 0:
            raise PublicationError("exclusive write made no progress")
        offset += written


def _entry_metadata(parent_descriptor: int, leaf: str) -> os.stat_result | None:
    try:
        return os.stat(leaf, dir_fd=parent_descriptor, follow_symlinks=False)
    except FileNotFoundError:
        return None
    except OSError as error:
        raise PublicationError(f"cannot inspect publication entry {leaf}") from error


def _stat_identity(metadata: os.stat_result) -> tuple[int, int]:
    return metadata.st_dev, metadata.st_ino


def _leaf_exists(parent_descriptor: int, leaf: str) -> bool:
    return _entry_metadata(parent_descriptor, leaf) is not None


def _staging_leaf(path: Path) -> str:
    return f".{path.name}{_STAGING_SUFFIX}"


def _require_parent_anchor(parent: Path, descriptor: int) -> None:
    live_descriptor = _open_absolute_directory(parent)
    try:
        live = os.fstat(live_descriptor)
        held = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(live.st_mode)
            or not stat.S_ISDIR(held.st_mode)
            or _stat_identity(live) != _stat_identity(held)
        ):
            raise PublicationError(f"publication parent identity changed: {parent}")
    except OSError as error:
        raise PublicationError(f"cannot revalidate publication parent {parent}") from error
    finally:
        os.close(live_descriptor)


def _open_absolute_directory(path: Path) -> int:
    if not path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts[1:]):
        raise PublicationError("directory anchor must be an absolute normalized path")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    descriptor = -1
    try:
        descriptor = os.open("/", flags)
        for component in path.parts[1:]:
            child = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except OSError as error:
        if descriptor >= 0:
            os.close(descriptor)
        raise PublicationError(f"cannot hold directory anchor {path}") from error


def _open_parent(path: Path) -> int:
    if not path.is_absolute() or path.name in {"", ".", ".."}:
        raise PublicationError("publication path must be an absolute file path")
    parent = path.parent
    descriptor = _open_absolute_directory(parent)
    _require_parent_anchor(parent, descriptor)
    return descriptor


def _read_descriptor_bounded(descriptor: int, *, maximum_bytes: int) -> bytes:
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size <= 0
            or before.st_size > maximum_bytes
        ):
            raise PublicationError("held publication file violates its byte contract")
        os.lseek(descriptor, 0, os.SEEK_SET)
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 65_536))
            if not chunk:
                raise PublicationError("short read from held publication file")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise PublicationError("held publication file grew while reading")
        after = os.fstat(descriptor)
    except OSError as error:
        raise PublicationError("cannot read held publication file") from error
    if (
        _stat_identity(before) != _stat_identity(after)
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or after.st_nlink != 1
    ):
        raise PublicationError("held publication file identity changed while reading")
    return b"".join(chunks)


def _require_canonical_source(source: bytes) -> None:
    if type(source) is not bytes or not source or len(source) > MAX_NEXT_HYPOTHESES_BYTES:
        raise PublicationError("publication source exceeds the bounded byte contract")
    try:
        document = json.loads(
            source,
            object_pairs_hook=_strict_object,
            parse_constant=lambda value: (_ for _ in ()).throw(
                PublicationError(f"non-standard JSON constant {value!r}")
            ),
        )
        canonical = _canonical_json_bytes(document)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise PublicationError("publication source is not canonical JSON") from error
    if type(document) is not dict or canonical != source:
        raise PublicationError("publication source is not one canonical JSON object")


def _native_rename_no_replace(
    parent_descriptor: int,
    source_leaf: str,
    destination_leaf: str,
) -> tuple[int, int]:
    library = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        function_name = "renameatx_np"
        flags = (
            _DARWIN_RENAME_EXCL
            | _DARWIN_RENAME_NOFOLLOW_ANY
            | _DARWIN_RENAME_RESOLVE_BENEATH
        )
    elif sys.platform.startswith("linux"):
        function_name = "renameat2"
        flags = _LINUX_RENAME_NOREPLACE
    else:
        raise PublicationError(
            f"native no-replace rename is unsupported on {sys.platform}"
        )
    try:
        function = getattr(library, function_name)
    except AttributeError as error:
        raise PublicationError(f"{function_name} is unavailable") from error
    function.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    function.restype = ctypes.c_int
    ctypes.set_errno(0)
    result = function(
        parent_descriptor,
        os.fsencode(source_leaf),
        parent_descriptor,
        os.fsencode(destination_leaf),
        flags,
    )
    return result, ctypes.get_errno() or errno.EIO


def _held_namespace_state(
    parent_descriptor: int,
    *,
    staging_leaf: str,
    final_leaf: str,
    descriptor: int,
) -> str:
    held = os.fstat(descriptor)
    live_stage = _entry_metadata(parent_descriptor, staging_leaf)
    live_final = _entry_metadata(parent_descriptor, final_leaf)
    staged = (
        live_stage is not None
        and _stat_identity(live_stage) == _stat_identity(held)
        and live_final is None
        and held.st_nlink == 1
    )
    published = (
        live_stage is None
        and live_final is not None
        and _stat_identity(live_final) == _stat_identity(held)
        and held.st_nlink == 1
    )
    if staged:
        return "staged"
    if published:
        return "published"
    return "invalid"


def _promote_held_stage_no_replace(
    *,
    path: Path,
    parent_descriptor: int,
    staging_leaf: str,
    descriptor: int,
    source: bytes,
) -> None:
    held = os.fstat(descriptor)
    if _held_namespace_state(
        parent_descriptor,
        staging_leaf=staging_leaf,
        final_leaf=path.name,
        descriptor=descriptor,
    ) != "staged":
        raise PublicationError("staging namespace differs before promotion")
    _require_parent_anchor(path.parent, parent_descriptor)
    os.fsync(parent_descriptor)
    result, observed_errno = _native_rename_no_replace(
        parent_descriptor,
        staging_leaf,
        path.name,
    )
    observed_state = _held_namespace_state(
        parent_descriptor,
        staging_leaf=staging_leaf,
        final_leaf=path.name,
        descriptor=descriptor,
    )
    if observed_state != "published":
        if observed_state == "staged" and result != 0:
            raise PublicationError(
                "native no-replace rename failed with "
                f"errno {observed_errno}: {os.strerror(observed_errno)}"
            )
        raise PublicationError("publication promotion left an invalid namespace")
    os.fsync(parent_descriptor)
    _require_parent_anchor(path.parent, parent_descriptor)
    final_descriptor = -1
    try:
        flags = (
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0)
        )
        final_descriptor = os.open(path.name, flags, dir_fd=parent_descriptor)
        final_metadata = os.fstat(final_descriptor)
        if (
            _stat_identity(final_metadata) != _stat_identity(held)
            or stat.S_IMODE(final_metadata.st_mode) != 0o600
        ):
            raise PublicationError("published final inode differs from held staging inode")
        if (
            _read_descriptor_bounded(
                final_descriptor,
                maximum_bytes=MAX_NEXT_HYPOTHESES_BYTES,
            )
            != source
        ):
            raise PublicationError("published final bytes differ from held source")
        if _held_namespace_state(
            parent_descriptor,
            staging_leaf=staging_leaf,
            final_leaf=path.name,
            descriptor=descriptor,
        ) != "published":
            raise PublicationError("published namespace changed during final reread")
    finally:
        if final_descriptor >= 0:
            os.close(final_descriptor)


def _publish_file_native_no_replace(path: Path, source: bytes) -> None:
    _require_canonical_source(source)
    parent_descriptor = _open_parent(path)
    staging_leaf = _staging_leaf(path)
    descriptor = -1
    try:
        _require_parent_anchor(path.parent, parent_descriptor)
        if _leaf_exists(parent_descriptor, path.name):
            raise PublicationError(f"refusing to replace existing {path}")
        if _leaf_exists(parent_descriptor, staging_leaf):
            raise PublicationError(f"staging artifact already exists for {path}")
        flags = (
            os.O_RDWR
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0)
        )
        descriptor = os.open(staging_leaf, flags, 0o600, dir_fd=parent_descriptor)
        os.fchmod(descriptor, 0o600)
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or stat.S_IMODE(opened.st_mode) != 0o600
        ):
            raise PublicationError("publication staging identity is invalid")
        _write_all(descriptor, source)
        os.fsync(descriptor)
        written = os.fstat(descriptor)
        if (
            _stat_identity(opened) != _stat_identity(written)
            or written.st_size != len(source)
            or not stat.S_ISREG(written.st_mode)
            or written.st_nlink != 1
            or stat.S_IMODE(written.st_mode) != 0o600
        ):
            raise PublicationError("publication staging identity changed")
        if (
            _read_descriptor_bounded(
                descriptor,
                maximum_bytes=MAX_NEXT_HYPOTHESES_BYTES,
            )
            != source
        ):
            raise PublicationError("staging bytes differ before promotion")
        _promote_held_stage_no_replace(
            path=path,
            parent_descriptor=parent_descriptor,
            staging_leaf=staging_leaf,
            descriptor=descriptor,
            source=source,
        )
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        os.close(parent_descriptor)


def _promote_existing_stage_no_replace(path: Path, source: bytes) -> None:
    _require_canonical_source(source)
    parent_descriptor = _open_parent(path)
    staging_leaf = _staging_leaf(path)
    descriptor = -1
    try:
        _require_parent_anchor(path.parent, parent_descriptor)
        if _leaf_exists(parent_descriptor, path.name):
            raise PublicationError("cannot repair over an existing repository final")
        flags = (
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0)
        )
        descriptor = os.open(staging_leaf, flags, dir_fd=parent_descriptor)
        held = os.fstat(descriptor)
        live = _entry_metadata(parent_descriptor, staging_leaf)
        if (
            live is None
            or _stat_identity(live) != _stat_identity(held)
            or stat.S_IMODE(held.st_mode) != 0o600
            or _read_descriptor_bounded(
                descriptor,
                maximum_bytes=MAX_NEXT_HYPOTHESES_BYTES,
            )
            != source
        ):
            raise PublicationError("repository staging artifact differs from external")
        _promote_held_stage_no_replace(
            path=path,
            parent_descriptor=parent_descriptor,
            staging_leaf=staging_leaf,
            descriptor=descriptor,
            source=source,
        )
    except OSError as error:
        raise PublicationError("cannot open exact repository staging artifact") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        os.close(parent_descriptor)


def _strict_reload(path: Path, expected: bytes) -> None:
    _document, source = _load_canonical(
        path,
        maximum_bytes=MAX_NEXT_HYPOTHESES_BYTES,
    )
    if source != expected:
        raise PublicationError(f"published bytes differ at {path}")


def _coordinate_presence(path: Path) -> tuple[bool, bool]:
    parent_descriptor = _open_parent(path)
    try:
        _require_parent_anchor(path.parent, parent_descriptor)
        return (
            _leaf_exists(parent_descriptor, path.name),
            _leaf_exists(parent_descriptor, _staging_leaf(path)),
        )
    finally:
        os.close(parent_descriptor)


def _pair_namespace_state(*, external_path: Path, repository_path: Path) -> str:
    external_final, external_stage = _coordinate_presence(external_path)
    repository_final, repository_stage = _coordinate_presence(repository_path)
    bits = (
        external_final,
        external_stage,
        repository_final,
        repository_stage,
    )
    if bits == (False, False, False, False):
        return "absent"
    if bits == (False, True, False, False):
        return "external_stage_unresolved"
    if bits == (True, False, True, False):
        return "complete"
    if bits == (True, False, False, False):
        return "external_only"
    if bits == (True, False, False, True):
        return "external_plus_repository_stage_candidate"
    return "invalid"


def _require_pair_state(
    expected: str,
    *,
    external_path: Path,
    repository_path: Path,
) -> None:
    observed = _pair_namespace_state(
        external_path=external_path,
        repository_path=repository_path,
    )
    if observed != expected:
        raise PublicationError(
            f"publication pair state is {observed!r}, expected {expected!r}"
        )


def _publish_pair(
    *,
    external_path: Path,
    repository_path: Path,
    source: bytes,
) -> str:
    _require_pair_state(
        "absent",
        external_path=external_path,
        repository_path=repository_path,
    )
    _publish_file_native_no_replace(external_path, source)
    _publish_file_native_no_replace(repository_path, source)
    _require_pair_state(
        "complete",
        external_path=external_path,
        repository_path=repository_path,
    )
    _strict_reload(repository_path, source)
    _strict_reload(external_path, source)
    return "published"


def _verify_existing_pair(
    *,
    external_path: Path,
    repository_path: Path,
    expected_terminal_source: bytes,
) -> bytes:
    _require_pair_state(
        "complete",
        external_path=external_path,
        repository_path=repository_path,
    )
    record, repository_source = _load_canonical(
        repository_path,
        maximum_bytes=MAX_NEXT_HYPOTHESES_BYTES,
    )
    _validate_record(record, expected_terminal_source=expected_terminal_source)
    _strict_reload(external_path, repository_source)
    return repository_source


def _require_running_publisher_binding(record: Mapping[str, object]) -> None:
    bindings = _exact_keys(
        record.get("bindings"),
        (
            "attempt_path",
            "attempt_sha256",
            "external_attempt_path",
            "external_next_hypotheses_path",
            "external_terminal_path",
            "freeze_path",
            "freeze_sha256",
            "publisher_implementation_commit",
            "publisher_path",
            "publisher_sha256",
            "repository_next_hypotheses_path",
            "terminal_path",
            "terminal_sha256",
        ),
        label="bindings",
    )
    running = _read_bounded_regular(
        ROOT / SCRIPT_RELATIVE,
        maximum_bytes=MAX_NEXT_HYPOTHESES_BYTES,
    )
    if _sha256(running) != bindings["publisher_sha256"]:
        raise PublicationError("running publisher differs from external record binding")
    _require_publisher_lineage(
        bindings["publisher_implementation_commit"],
        bindings["publisher_sha256"],
    )


def _repair_repository_projection(
    *,
    external_path: Path,
    repository_path: Path,
    expected_terminal_source: bytes,
) -> bytes:
    state = _pair_namespace_state(
        external_path=external_path,
        repository_path=repository_path,
    )
    if state not in {"external_only", "external_plus_repository_stage_candidate"}:
        raise PublicationError(f"pair state {state!r} is not explicitly repairable")
    external_record, source = _load_canonical(
        external_path,
        maximum_bytes=MAX_NEXT_HYPOTHESES_BYTES,
    )
    _validate_record(
        external_record,
        expected_terminal_source=expected_terminal_source,
    )
    _require_running_publisher_binding(external_record)
    if state == "external_only":
        _publish_file_native_no_replace(repository_path, source)
    else:
        _promote_existing_stage_no_replace(repository_path, source)
    return _verify_existing_pair(
        external_path=external_path,
        repository_path=repository_path,
        expected_terminal_source=expected_terminal_source,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--publish", action="store_true")
    mode.add_argument("--verify-existing", action="store_true")
    mode.add_argument("--repair-repository-projection", action="store_true")
    return parser.parse_args()


def main() -> int:
    arguments = _parse_args()
    terminal, terminal_source = _load_canonical(
        ROOT / TERMINAL_RELATIVE,
        maximum_bytes=MAX_TERMINAL_BYTES,
    )
    freeze_source = _read_bounded_regular(
        ROOT / FREEZE_RELATIVE,
        maximum_bytes=MAX_FREEZE_BYTES,
    )
    _attempt, attempt_source = _load_canonical(
        ROOT / ATTEMPT_RELATIVE,
        maximum_bytes=MAX_ATTEMPT_BYTES,
    )
    _require_external_store_matches(
        attempt_source=attempt_source,
        terminal_source=terminal_source,
    )
    if _sha256(terminal_source) != EXPECTED_TERMINAL_SHA256:
        raise PublicationError("repository terminal SHA-256 differs")
    if _sha256(attempt_source) != EXPECTED_ATTEMPT_SHA256:
        raise PublicationError("repository attempt SHA-256 differs")
    if _sha256(freeze_source) != EXPECTED_FREEZE_SHA256:
        raise PublicationError("repository freeze SHA-256 differs")
    repository_output = ROOT / REPOSITORY_OUTPUT_RELATIVE

    if arguments.verify_existing:
        source = _verify_existing_pair(
            external_path=EXTERNAL_OUTPUT,
            repository_path=repository_output,
            expected_terminal_source=terminal_source,
        )
        print(_sha256(source))
        return 0

    if arguments.repair_repository_projection:
        source = _repair_repository_projection(
            external_path=EXTERNAL_OUTPUT,
            repository_path=repository_output,
            expected_terminal_source=terminal_source,
        )
        print(f"repaired sha256={_sha256(source)} bytes={len(source)}")
        return 0

    publisher_commit, publisher_sha256 = _require_clean_committed_source()
    record = _build_record(
        terminal=terminal,
        terminal_source=terminal_source,
        freeze_source=freeze_source,
        attempt_source=attempt_source,
        publisher_commit=publisher_commit,
        publisher_sha256=publisher_sha256,
    )
    _validate_record(record, expected_terminal_source=terminal_source)
    source = _canonical_json_bytes(record)
    if len(source) > MAX_NEXT_HYPOTHESES_BYTES:
        raise PublicationError("next-hypothesis record exceeds its frozen budget")
    _require_pair_state(
        "absent",
        external_path=EXTERNAL_OUTPUT,
        repository_path=repository_output,
    )
    if arguments.preflight_only:
        print(f"preflight_pass sha256={_sha256(source)} bytes={len(source)}")
        return 0
    status = _publish_pair(
        external_path=EXTERNAL_OUTPUT,
        repository_path=repository_output,
        source=source,
    )
    print(f"{status} sha256={_sha256(source)} bytes={len(source)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PublicationError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from error
