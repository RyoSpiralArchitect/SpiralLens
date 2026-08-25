#!/usr/bin/env python3
"""Frozen, model-free P4 graph evaluability calibration v0.2 successor.

The official path is deliberately a three-commit chronology:

1. commit this runner and its protocol;
2. run ``--prepare-launch`` and commit the resulting launch descriptor;
3. run ``--preflight``, then ``--run``, and separately commit the repository
   projection of the already durable external terminal.

Launch preparation and preflight do not instantiate either frozen phantom.
The run selects graph scales on the calibration substrate without reading a
field, core, phase, holonomy, winding, charge, subject, model, cache, raw
capture, or Pythia terminal candidate value.  Only after a calibration
triplet is fixed does it instantiate the disjoint confirmation substrate.
Catchable execution outcomes are folded into at most one deterministic,
no-replace terminal.  A persistence failure or uncatchable interruption leaves
the reserved stage unresolved, emits no terminal, permanently consumes the
attempt, and authorizes no retry, resume, rescue, cleanup, or terminalization.
No integer or topology claim is emitted.  This successor is explicitly bound
to the consumed-invalid v0.1 attempt and terminal.  Its calibration substrate
is exposed regression input; its confirmation substrate has a new seed and a
stronger, predeclared density-warp coordinate.  That definition-level
separation prevents direct v0.1 confirmation-input reuse but does not restore
independence, preregistration, cryptographic-unseen proof, or scientific
authority.

``cache_accessed`` is scoped only to model or subject-data caches.  Python
bytecode-cache isolation is a separate pre-import/post-import/post-execution
process boundary and is reported separately.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import math
import os
import platform
import stat
import struct
import subprocess
import sys
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Iterable, Mapping, Sequence

_BOOTSTRAP_REPOSITORY = Path(__file__).resolve().parents[1]
_BOOTSTRAP_SOURCE = _BOOTSTRAP_REPOSITORY / "src"
_BOOTSTRAP_RUNNER = Path(__file__).resolve()
_BOOTSTRAP_PYCACHE_PREFIX = (
    _BOOTSTRAP_REPOSITORY.parent
    / ".spirallens-p4-graph-evaluability-calibration-v0-2-python-cache"
).absolute()
_BOOTSTRAP_OFFICIAL_PLATFORM = "darwin"
_BOOTSTRAP_LOGICAL_EXECUTABLE = (
    _BOOTSTRAP_REPOSITORY / ".venv" / "bin" / "python"
).absolute()
_BOOTSTRAP_RESOLVED_BASE_EXECUTABLE = Path(
    "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13"
)
_BOOTSTRAP_RESOLVED_BASE_EXECUTABLE_SHA256 = (
    "bdc6b50ebbf1fa5d1fc4ed8f3ab7decb640e60b55088ae0be4bf63bb914a89d5"
)
_BOOTSTRAP_PHYSICAL_LAUNCHER = Path(
    "/Library/Frameworks/Python.framework/Versions/3.13/"
    "Resources/Python.app/Contents/MacOS/Python"
)
_BOOTSTRAP_PHYSICAL_LAUNCHER_SHA256 = (
    "7ee125c1edcfa2d6404a28caaa5724b7b239da901c86bbc1eb91d6a784deeef3"
)


def _bootstrap_expected_orig_argv_tail(mode: str) -> list[str]:
    return [
        "-I",
        "-B",
        "-X",
        f"pycache_prefix={_BOOTSTRAP_PYCACHE_PREFIX}",
        str(_BOOTSTRAP_RUNNER),
        mode,
    ]


def _bootstrap_expected_python_argv(mode: str) -> list[str]:
    """Return the lexical operator argv, not CPython's physical orig_argv."""

    return [
        str(_BOOTSTRAP_LOGICAL_EXECUTABLE),
        *_bootstrap_expected_orig_argv_tail(mode),
    ]


def _bootstrap_stable_regular_sha256(path: Path, *, label: str) -> str:
    """Hash one exact early-process executable without following aliases."""

    try:
        if not path.is_absolute() or path.absolute() != path.resolve(strict=True):
            raise RuntimeError(f"{label} must be an absolute non-symlink path")
        descriptor = os.open(
            path,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        )
    except OSError as error:
        raise RuntimeError(f"cannot open {label}") from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise RuntimeError(f"{label} must be a regular nlink=1 file")
        digest = hashlib.sha256()
        while True:
            block = os.read(descriptor, 65_536)
            if not block:
                break
            digest.update(block)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        raise RuntimeError(f"{label} changed while being hashed")
    return digest.hexdigest()


def _bootstrap_python_process_observation() -> dict[str, object]:
    try:
        os.lstat(_BOOTSTRAP_PYCACHE_PREFIX)
    except FileNotFoundError:
        prefix_absent = True
    except OSError as error:
        raise RuntimeError(
            "cannot lstat the dedicated Python bytecode-cache prefix"
        ) from error
    else:
        prefix_absent = False
    original_argv = list(getattr(sys, "orig_argv", ()))
    effective_argv0 = original_argv[0] if original_argv else None
    original_tail = original_argv[1:] if original_argv else []
    try:
        logical_resolved = Path(sys.executable).resolve(strict=True)
    except OSError as error:
        raise RuntimeError("cannot resolve the logical Python executable") from error
    base_executable = getattr(sys, "_base_executable", None)
    if not isinstance(base_executable, str) or not isinstance(effective_argv0, str):
        raise RuntimeError("Python executable/orig_argv0 coordinates are unavailable")
    try:
        base_resolved = Path(base_executable).resolve(strict=True)
        launcher_resolved = Path(effective_argv0).resolve(strict=True)
    except OSError as error:
        raise RuntimeError("cannot resolve Python base/launcher coordinates") from error
    return {
        "platform": sys.platform,
        "logical_executable": sys.executable,
        "logical_executable_resolved": str(logical_resolved),
        "base_executable": base_executable,
        "base_executable_sha256": _bootstrap_stable_regular_sha256(
            base_resolved,
            label="resolved base Python executable",
        ),
        "effective_orig_argv0": effective_argv0,
        "physical_launcher_sha256": _bootstrap_stable_regular_sha256(
            launcher_resolved,
            label="effective physical Python launcher",
        ),
        "orig_argv_tail": original_tail,
        "sys_argv": list(sys.argv),
        "isolated": sys.flags.isolated,
        "dont_write_bytecode_flag": sys.flags.dont_write_bytecode,
        "dont_write_bytecode_runtime": sys.dont_write_bytecode,
        "pycache_prefix": sys.pycache_prefix,
        "xoptions": dict(sys._xoptions),
        "pycache_prefix_lstat_absent": prefix_absent,
    }


def _bootstrap_expected_python_process_observation(mode: str) -> dict[str, object]:
    expected_prefix = str(_BOOTSTRAP_PYCACHE_PREFIX)
    return {
        "platform": _BOOTSTRAP_OFFICIAL_PLATFORM,
        "logical_executable": str(_BOOTSTRAP_LOGICAL_EXECUTABLE),
        "logical_executable_resolved": str(_BOOTSTRAP_RESOLVED_BASE_EXECUTABLE),
        "base_executable": str(_BOOTSTRAP_RESOLVED_BASE_EXECUTABLE),
        "base_executable_sha256": _BOOTSTRAP_RESOLVED_BASE_EXECUTABLE_SHA256,
        "effective_orig_argv0": str(_BOOTSTRAP_PHYSICAL_LAUNCHER),
        "physical_launcher_sha256": _BOOTSTRAP_PHYSICAL_LAUNCHER_SHA256,
        "orig_argv_tail": _bootstrap_expected_orig_argv_tail(mode),
        "sys_argv": [str(_BOOTSTRAP_RUNNER), mode],
        "isolated": 1,
        "dont_write_bytecode_flag": 1,
        "dont_write_bytecode_runtime": True,
        "pycache_prefix": expected_prefix,
        "xoptions": {"pycache_prefix": expected_prefix},
        "pycache_prefix_lstat_absent": True,
    }


def _bootstrap_validate_python_process_observation(
    mode: str,
    observed: Mapping[str, object],
) -> dict[str, object]:
    expected = _bootstrap_expected_python_process_observation(mode)
    materialized = dict(observed)
    if materialized != expected:
        raise RuntimeError(
            f"P4 {mode} Python process flags/cache boundary differ from freeze"
        )
    return materialized


def _bootstrap_validate_python_process(mode: str) -> dict[str, object]:
    observed = _bootstrap_python_process_observation()
    return _bootstrap_validate_python_process_observation(mode, observed)


_BOOTSTRAP_GUARDED_MODE = next(
    (mode for mode in ("--run", "--prepare-launch") if mode in sys.argv[1:]),
    None,
)
_BOOTSTRAP_PRE_IMPORT_PYTHON_OBSERVATION = (
    _bootstrap_validate_python_process(_BOOTSTRAP_GUARDED_MODE)
    if _BOOTSTRAP_GUARDED_MODE is not None
    else None
)

if str(_BOOTSTRAP_SOURCE) not in sys.path:
    sys.path.insert(0, str(_BOOTSTRAP_SOURCE))

import numpy as np
import spirallens

from spirallens.core.canonical import (
    canonical_json_bytes,
    canonical_json_sha256,
    parse_canonical_json,
)
from spirallens.gauge.procrustes_connection import procrustes_connection
from spirallens.graphs import (
    BoundaryRefinementRule,
    GraphConstructionReceipt,
    GraphFamily,
    GraphInput,
    GraphPurpose,
    MutualKnnSpec,
    RadiusGraphSpec,
    SharedNeighborSpec,
    bind_cycle_class,
    build_discrete_domain_complex,
    construct_mutual_knn,
    construct_radius_graph,
    construct_shared_neighbor_graph,
    define_boundary_cycle_class,
)
from spirallens.graphs.common import (
    array_sha256,
    coordinate_order_invariant_euclidean_norm,
)
from spirallens.qualification.common import AttemptStatus, QualificationState
from spirallens.qualification.crossed import (
    build_crossed_blind_loop_input,
    build_crossed_graph_execution,
    rectangular_grid_support_faces,
)
from spirallens.qualification.metamorphic import (
    local_frame_gauge_check,
    loop_reversal_check,
    nonorientable_control_check,
    sampled_phase_total,
)
from spirallens.qualification.protocol import GraphAxes, GraphDeclaration
from spirallens.qualification.winding import (
    LoopPhasePolicy,
    build_blind_loop_input,
    estimate_and_seal_loop,
)
from spirallens.synthetic.cartesian_fourier_domain_phantom import (
    CartesianFourierDomainGenerator,
    CartesianFourierDomainSpec,
)
from spirallens.synthetic.cartesian_fourier_estimator import (
    estimate_cartesian_fourier_field,
)


_BOOTSTRAP_POST_IMPORT_PYTHON_OBSERVATION = (
    _bootstrap_validate_python_process(_BOOTSTRAP_GUARDED_MODE)
    if _BOOTSTRAP_GUARDED_MODE is not None
    else None
)


SCHEMA_VERSION = "spirallens.p4-graph-evaluability-terminal.v0.2"
PROTOCOL_SCHEMA_VERSION = "spirallens.p4-graph-evaluability-protocol.v0.2"
LAUNCH_SCHEMA_VERSION = "spirallens.p4-graph-evaluability-launch.v0.2"
ATTEMPT_SCHEMA_VERSION = "spirallens.p4-exact-one-attempt.v0.2"
GRAPH_SELECTION_SEAL_SCHEMA_VERSION = "spirallens.p4-graph-selection-seal.v0.2"
THRESHOLD_SEAL_SCHEMA_VERSION = "spirallens.p4-threshold-decision-seal.v0.2"
CONFIRMATION_ACCESS_SEAL_SCHEMA_VERSION = "spirallens.p4-confirmation-access-seal.v0.2"
STORE_MANIFEST_SCHEMA_VERSION = "spirallens.p4-external-store-manifest.v0.2"
SELECTOR_PROJECTION_SCHEMA_VERSION = "spirallens.p4-selector-projection.v0.2"
CONFIRMATION_STRUCTURAL_PROJECTION_SCHEMA_VERSION = (
    "spirallens.p4-confirmation-structural-projection.v0.2"
)
EXPERIMENT_ID = "p4-graph-evaluability-calibration-v0.2"

REPOSITORY_PROTOCOL = Path("protocols/p4_graph_evaluability_calibration_v0_2.json")
REPOSITORY_RUNNER = Path("scripts/run_p4_graph_evaluability_calibration_v0_2.py")
REPOSITORY_HYPOTHESES = Path(
    "experiments/pythia/gate_state_development_v0_1/next-hypotheses.json"
)
REPOSITORY_LAUNCH = Path(
    "experiments/qualification/p4_graph_evaluability_calibration_v0_2/launch.json"
)
REPOSITORY_ATTEMPT = Path(
    "experiments/qualification/p4_graph_evaluability_calibration_v0_2/attempt.json"
)
REPOSITORY_TERMINAL = Path(
    "experiments/qualification/p4_graph_evaluability_calibration_v0_2/terminal-result.json"
)

PREDECESSOR_EXPERIMENT_ID = "p4-graph-evaluability-calibration-v0.1"
PREDECESSOR_SOURCE_COMMIT = "4875838eb64bff8f3bdb0f5ac26d47748be4e468"
PREDECESSOR_EVIDENCE_COMMIT = "f0f6c3a58108b585eaaf2e8f63fb68c72c6454ee"
PREDECESSOR_PROTOCOL = Path("protocols/p4_graph_evaluability_calibration_v0_1.json")
PREDECESSOR_RUNNER = Path("scripts/run_p4_graph_evaluability_calibration.py")
PREDECESSOR_LAUNCH = Path(
    "experiments/qualification/p4_graph_evaluability_calibration_v0_1/launch.json"
)
PREDECESSOR_ATTEMPT = Path(
    "experiments/qualification/p4_graph_evaluability_calibration_v0_1/attempt.json"
)
PREDECESSOR_TERMINAL = Path(
    "experiments/qualification/p4_graph_evaluability_calibration_v0_1/terminal-result.json"
)
PREDECESSOR_PROTOCOL_SHA256 = (
    "e5634ad221c263424f279896ca56d64edff52dbeba1edc280a0760f31df6ce33"
)
PREDECESSOR_RUNNER_SHA256 = (
    "8934bfff9c71edfbe02fa688dc0afb945da5fe96a3919fb27e3f2101d6e082c1"
)
PREDECESSOR_LAUNCH_SHA256 = (
    "31f6147046ebcab8b1b9c31c5a7ce46bb5d66a93ba3af139f3669082151e2944"
)
PREDECESSOR_ATTEMPT_SHA256 = (
    "2e3246d766c6372589f005dd9a4e31bfee44ebf63afefdf050160f08edd24615"
)
PREDECESSOR_TERMINAL_SHA256 = (
    "28842e1f90823349d550c7d52921af424493794e676898c00aa41cdfaeeb55cf"
)

NEXT_HYPOTHESES_SHA256 = (
    "eededce1bf22e1adc34e9d7ec85a909695979fa18b7ab5e614ac78b50104f11c"
)
CANONICAL_BYTE_LIMIT = 262_144
EXTERNAL_STAGE = Path(
    "/Users/ryohiga/SpiralReality/"
    ".spirallens-p4-graph-evaluability-calibration-v0-2-store.staging"
)
EXTERNAL_STORE = Path(
    "/Users/ryohiga/SpiralReality/"
    "spirallens-p4-graph-evaluability-calibration-v0-2-store"
)
ATTEMPT_NAME = "attempt.json"
GRAPH_SELECTION_SEAL_NAME = "graph-selection-seal.json"
THRESHOLD_SEAL_NAME = "threshold-seal.json"
CONFIRMATION_ACCESS_SEAL_NAME = "confirmation-access-seal.json"
TERMINAL_NAME = "terminal-result.json"
STORE_MANIFEST_NAME = "store-manifest.json"
GIT_BINARY = Path("/usr/bin/git")
GIT_ARGV_PREFIX = (
    str(GIT_BINARY),
    "-c",
    "core.fsmonitor=false",
    "-c",
    "core.untrackedCache=false",
    "-c",
    "core.hooksPath=/dev/null",
)
PYTHON_BYTECODE_CACHE_NAME = (
    ".spirallens-p4-graph-evaluability-calibration-v0-2-python-cache"
)
EXTERNAL_MEMBER_ORDER = (
    ATTEMPT_NAME,
    GRAPH_SELECTION_SEAL_NAME,
    THRESHOLD_SEAL_NAME,
    CONFIRMATION_ACCESS_SEAL_NAME,
    TERMINAL_NAME,
)
FAMILY_ORDER = (
    GraphFamily.MUTUAL_KNN.value,
    GraphFamily.FIXED_RADIUS.value,
    GraphFamily.SHARED_NEIGHBOR.value,
)
CROSSED_CASES = (
    ("positive", 1.0),
    ("fixed_null", 0.0),
    ("no_core_null", 0.0),
)
CYCLE_CLASS_ORDER = ("central", "wide")
CONFIRMATION_TRIPLET_MEASUREMENT_KEYS = frozenset(
    {
        "edge_count_minimum",
        "edge_count_maximum",
        "edge_count_spread",
        "edge_count_ratio",
        "mean_degree_target_deviation_sum",
        "mean_degree_target_deviation_numerator",
        "largest_component_vertex_count_spread",
        "two_core_vertex_count_spread",
        "common_two_core_intersection_count",
        "component_count_sum",
        "pairwise",
        "pairwise_edge_sets_must_differ",
        "pairwise_edge_jaccard_at_most_0_85",
    }
)
SELECTOR_ONLY_TRIPLET_MEASUREMENT_KEYS = frozenset(
    {"lexicographic_objective", "jaccard_used_as_objective"}
)
SELECTOR_TRIPLET_MEASUREMENT_KEYS = (
    CONFIRMATION_TRIPLET_MEASUREMENT_KEYS | SELECTOR_ONLY_TRIPLET_MEASUREMENT_KEYS
)
MATRIX_INSUFFICIENT_REASONS = frozenset(
    {
        "boundary_amplitude_at_or_below_floor",
        "boundary_coherence_at_or_below_floor",
        "boundary_identifiability_at_or_below_floor",
        "phase_edge_inside_branch_margin",
        "representative_loop_rows_repeated",
        "representative_loop_has_fewer_than_three_unique_rows",
        "sampled_phase_total_outside_integer_residual_band",
    }
)
EXPECTED_RAW_CONTROL_STATES = {
    "known_positive_connection": "pass",
    "zero_holonomy_finite_amplitude_null": "pass",
    "radial_amplitude_depression_without_holonomy": "pass",
    "pure_so2_gauge": "pass",
    "degree_preserving_rewire": "pass",
    "amplitude_label_permutation": "pass",
    "orientation_reversal": "pass",
    "density_warp_confirmation": "pass",
    "joint_vertex_permutation": "pass",
    "ambient_orthogonal_transform": "pass",
    "global_norm_scaling": "pass",
    "collapsed_cycleless_phantom": "insufficient",
    "field_only_shuffle": "pass",
    "zero_amplitude": "insufficient",
    "low_coherence": "insufficient",
    "non_orientable_frame": "insufficient",
}


def _cell_id(
    role: str,
    case_name: str,
    cycle_class: str,
    field_family: str,
    cycle_family: str,
) -> str:
    return "|".join((role, case_name, cycle_class, field_family, cycle_family))


def _required_cell_ids(role: str, cases: Sequence[str]) -> list[str]:
    return [
        _cell_id(role, case_name, cycle_class, field_family, cycle_family)
        for case_name, cycle_class, field_family, cycle_family in product(
            cases,
            CYCLE_CLASS_ORDER,
            FAMILY_ORDER,
            FAMILY_ORDER,
        )
    ]


def _span_id(role: str, case_name: str, cycle_class: str) -> str:
    return "|".join((role, case_name, cycle_class))


def _required_span_ids(role: str, cases: Sequence[str]) -> list[str]:
    return [
        _span_id(role, case_name, cycle_class)
        for case_name, cycle_class in product(cases, CYCLE_CLASS_ORDER)
    ]


def _control_contracts_document() -> list[dict[str, object]]:
    """Closed control sources and acceptance rules in authority order."""

    cases = tuple(name for name, _expected in CROSSED_CASES)
    family_observations = lambda control_id: [
        f"{control_id}|{family}" for family in FAMILY_ORDER
    ]
    documents = {
        "known_positive_connection": {
            "evaluation_kind": "held-out-confirmation-case",
            "required_cell_ids": _required_cell_ids("confirmation", ("positive",)),
            "required_span_ids": [],
            "required_observation_ids": [],
            "acceptance_rule": (
                "all-18-absolute-errors-finite-and-le-oracle-and-null-threshold"
            ),
        },
        "zero_holonomy_finite_amplitude_null": {
            "evaluation_kind": "held-out-confirmation-case",
            "required_cell_ids": _required_cell_ids("confirmation", ("no_core_null",)),
            "required_span_ids": [],
            "required_observation_ids": [],
            "acceptance_rule": (
                "all-18-absolute-errors-finite-and-le-oracle-and-null-threshold-and-no-core-loop-boundary-minimum-amplitude-above-floor"
            ),
        },
        "radial_amplitude_depression_without_holonomy": {
            "evaluation_kind": "held-out-confirmation-case",
            "required_cell_ids": _required_cell_ids("confirmation", ("fixed_null",)),
            "required_span_ids": [],
            "required_observation_ids": [],
            "acceptance_rule": (
                "all-18-absolute-errors-finite-and-le-oracle-and-null-threshold-and-fixed-null-all-three-center-amplitudes-at-or-below-floor-and-loop-boundary-minimum-above-floor"
            ),
        },
        "pure_so2_gauge": {
            "evaluation_kind": "algebraic-calibration-canary",
            "required_cell_ids": [],
            "required_span_ids": [],
            "required_observation_ids": [
                "pure_so2_gauge|procrustes-connection",
                "pure_so2_gauge|local-frame-gauge",
            ],
            "acceptance_rule": (
                "phase-total-global-so2-gauge-delta-le-1e-8-cycles-and-coordinate-law-connection-canaries-pass-in-declared-units"
            ),
        },
        "degree_preserving_rewire": {
            "evaluation_kind": "deterministic-graph-mutation",
            "required_cell_ids": [],
            "required_span_ids": [],
            "required_observation_ids": family_observations("degree_preserving_rewire"),
            "acceptance_rule": (
                "all-three-families-canonical-simple-two-switch-degree-preserved-edge-set-changed-symmetric-difference-four-or-raw-insufficient-if-no-switch"
            ),
        },
        "amplitude_label_permutation": {
            "evaluation_kind": "calibration-positive-central-representative",
            "required_cell_ids": [],
            "required_span_ids": [],
            "required_observation_ids": [
                f"amplitude_label_permutation|{cycle_class}"
                for cycle_class in CYCLE_CLASS_ORDER
            ],
            "acceptance_rule": (
                "amplitude-multiset-exact-transform-nonidentity-and-absolute-phase-total-change-le-1e-8-cycles-identity-is-insufficient"
            ),
        },
        "orientation_reversal": {
            "evaluation_kind": "algebraic-calibration-canary",
            "required_cell_ids": [],
            "required_span_ids": [],
            "required_observation_ids": [
                f"orientation_reversal|{cycle_class}"
                for cycle_class in CYCLE_CLASS_ORDER
            ],
            "acceptance_rule": "receipt-pass-and-error-le-1e-8-cycles",
        },
        "density_warp_confirmation": {
            "evaluation_kind": "held-out-confirmation-matrix",
            "required_cell_ids": _required_cell_ids("confirmation", cases),
            "required_span_ids": _required_span_ids("confirmation", cases),
            "required_observation_ids": [
                "density_warp_confirmation|fixed-triplet-structural-support"
            ],
            "acceptance_rule": (
                "all-54-cell-errors-le-oracle-threshold-and-all-6-spans-le-graph-threshold"
            ),
        },
        "joint_vertex_permutation": {
            "evaluation_kind": "graph-input-metamorphic",
            "required_cell_ids": [],
            "required_span_ids": [],
            "required_observation_ids": family_observations("joint_vertex_permutation"),
            "acceptance_rule": "vertex-id-edge-content-preserved",
        },
        "ambient_orthogonal_transform": {
            "evaluation_kind": "graph-input-metamorphic",
            "required_cell_ids": [],
            "required_span_ids": [],
            "required_observation_ids": family_observations(
                "ambient_orthogonal_transform"
            ),
            "acceptance_rule": "canonical-adjacency-preserved",
        },
        "global_norm_scaling": {
            "evaluation_kind": "graph-input-metamorphic",
            "required_cell_ids": [],
            "required_span_ids": [],
            "required_observation_ids": family_observations("global_norm_scaling"),
            "acceptance_rule": "canonical-adjacency-preserved-with-radius-covariance",
        },
        "collapsed_cycleless_phantom": {
            "evaluation_kind": "collapsed-graph-selector-control",
            "required_cell_ids": [],
            "required_span_ids": [],
            "required_observation_ids": [
                "collapsed_cycleless_phantom|path-graph",
                "collapsed_cycleless_phantom|central-binding",
                "collapsed_cycleless_phantom|wide-binding",
            ],
            "acceptance_rule": (
                "path-edge48-component1-lcc49-cycle-rank0-two-core0-and-central-wide-unmatched"
            ),
        },
        "field_only_shuffle": {
            "evaluation_kind": "held-out-confirmation-positive-cells",
            "required_cell_ids": [],
            "required_span_ids": [],
            "required_observation_ids": [
                f"field_only_shuffle|{cell_id}"
                for cell_id in _required_cell_ids("confirmation", ("positive",))
            ],
            "acceptance_rule": (
                "all-18-exact-row-reversals-satisfy-absolute-shuffled-plus-base-le-1e-8-cycles"
            ),
        },
        "zero_amplitude": {
            "evaluation_kind": "blind-loop-prerequisite-control",
            "required_cell_ids": [],
            "required_span_ids": [],
            "required_observation_ids": [
                f"zero_amplitude|{cycle_class}" for cycle_class in CYCLE_CLASS_ORDER
            ],
            "acceptance_rule": (
                "central-and-wide-raw-insufficient-with-exact-boundary-amplitude-at-or-below-floor-reason"
            ),
        },
        "low_coherence": {
            "evaluation_kind": "blind-loop-prerequisite-control",
            "required_cell_ids": [],
            "required_span_ids": [],
            "required_observation_ids": [
                f"low_coherence|{cycle_class}" for cycle_class in CYCLE_CLASS_ORDER
            ],
            "acceptance_rule": (
                "central-and-wide-raw-insufficient-with-exact-boundary-coherence-at-or-below-floor-reason"
            ),
        },
        "non_orientable_frame": {
            "evaluation_kind": "orientation-prerequisite-control",
            "required_cell_ids": [],
            "required_span_ids": [],
            "required_observation_ids": [
                "non_orientable_frame|odd-reflection",
                "non_orientable_frame|orientable-companion",
            ],
            "acceptance_rule": (
                "odd-one-reflection-insufficient-orientation-reversing-cycle-and-even-two-reflection-companion-fail-nontrigger"
            ),
        },
    }
    return [
        {
            "control_id": control_id,
            "expected_raw_state": EXPECTED_RAW_CONTROL_STATES[control_id],
            **documents[control_id],
        }
        for control_id in EXPECTED_RAW_CONTROL_STATES
    ]


RESULT_KEYS = {
    "terminal_state",
    "reason",
    "calibration_selector",
    "graph_selection_seal_sha256",
    "threshold_seal_sha256",
    "confirmation_access_seal_sha256",
    "calibration_matrix",
    "calibration_algebraic_diagnostics",
    "calibration_scalar_inventory",
    "effective_thresholds",
    "confirmation_structural",
    "confirmation_matrix",
    "confirmation_accessed",
    "graph_selection_sealed",
    "threshold_decision_sealed",
    "controls",
}


class P4ProtocolError(ValueError):
    """Raised when a closed protocol or persisted-result contract is violated.

    Before attempt reservation this blocks entry.  After reservation, result
    conformance failures are folded into the one caught-error terminal; they
    never imply that the attempt was unconsumed or reusable.
    """


class P4RunError(RuntimeError):
    """Raised after a committed launch authorizes one deterministic attempt."""


class P4PersistenceError(P4RunError):
    """Raised when durable persistence fails after the attempt is consumed.

    This class is deliberately excluded from caught scientific terminalization.
    The already reserved external stage remains unresolved and permanently
    consumes the one attempt.
    """


def _sha256_bytes(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _mapping(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise P4ProtocolError(f"{label} must be a string-keyed mapping")
    return dict(value)


def _sequence(value: object, *, label: str) -> list[object]:
    if not isinstance(value, list):
        raise P4ProtocolError(f"{label} must be an array")
    return value


def _exact_keys(
    value: Mapping[str, object], keys: Iterable[str], *, label: str
) -> None:
    expected = set(keys)
    actual = set(value)
    if actual != expected:
        raise P4ProtocolError(
            f"{label} keys differ: missing={sorted(expected - actual)}, "
            f"unknown={sorted(actual - expected)}"
        )


def _type_exact_equal(value: object, expected: object) -> bool:
    if type(value) is not type(expected):
        return False
    if isinstance(expected, dict):
        assert isinstance(value, dict)
        return set(value) == set(expected) and all(
            _type_exact_equal(value[key], expected[key]) for key in expected
        )
    if isinstance(expected, list):
        assert isinstance(value, list)
        return len(value) == len(expected) and all(
            _type_exact_equal(left, right)
            for left, right in zip(value, expected, strict=True)
        )
    return value == expected


def _constant(value: object, expected: object, *, label: str) -> None:
    if not _type_exact_equal(value, expected):
        raise P4ProtocolError(f"{label} must equal {expected!r}")


def _git_environment() -> dict[str, str]:
    """Return the complete, non-inherited environment for every Git query."""

    return {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "LANG": "C",
        "LC_ALL": "C",
    }


def _git_bytes(
    repo_root: Path,
    *arguments: str,
    check: bool = True,
) -> bytes:
    completed = _git_completed(repo_root, *arguments)
    if check and completed.returncode != 0:
        raw_detail = completed.stderr.strip() or completed.stdout.strip()
        detail = raw_detail.decode("utf-8", errors="replace")
        raise P4ProtocolError(f"git {' '.join(arguments)} failed: {detail}")
    return completed.stdout


def _git_completed(
    repo_root: Path,
    *arguments: str,
) -> subprocess.CompletedProcess[bytes]:
    """Run every Git query through the one frozen argv/env boundary."""

    return subprocess.run(
        (*GIT_ARGV_PREFIX, *arguments),
        cwd=repo_root,
        env=_git_environment(),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _git(repo_root: Path, *arguments: str, check: bool = True) -> str:
    try:
        return _git_bytes(repo_root, *arguments, check=check).decode("utf-8")
    except UnicodeDecodeError as error:
        raise P4ProtocolError("Git output is not strict UTF-8") from error


def _split_nul(source: bytes, *, label: str) -> list[str]:
    if not source:
        return []
    if not source.endswith(b"\0"):
        raise P4ProtocolError(f"{label} is not NUL terminated")
    try:
        return [item.decode("utf-8") for item in source[:-1].split(b"\0")]
    except UnicodeDecodeError as error:
        raise P4ProtocolError(f"{label} contains non-UTF-8 paths") from error


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_canonical(
    path: Path,
    *,
    label: str,
    allow_bound_single_trailing_lf: bool = False,
) -> dict[str, object]:
    try:
        source = path.read_bytes()
        if allow_bound_single_trailing_lf and source.endswith(b"\n"):
            if source.endswith(b"\n\n"):
                raise ValueError(f"{label} has more than one trailing LF")
            source = source[:-1]
        parsed = parse_canonical_json(source, label=label)
    except (OSError, ValueError) as error:
        raise P4ProtocolError(f"cannot load {label}: {error}") from error
    return _mapping(parsed, label=label)


def _validate_spec(value: object, *, label: str) -> dict[str, object]:
    item = _mapping(value, label=label)
    expected = {
        "seed",
        "grid_side",
        "ambient_dimension",
        "samples_per_split",
        "baseline",
        "second_harmonic_scale",
        "noise_scale",
        "density_warp_strength",
    }
    _exact_keys(item, expected, label=label)
    if type(item["seed"]) is not int or int(item["seed"]) < 0:
        raise P4ProtocolError(f"{label}.seed must be a nonnegative integer")
    _constant(item["grid_side"], 7, label=f"{label}.grid_side")
    _constant(item["ambient_dimension"], 12, label=f"{label}.ambient_dimension")
    _constant(item["samples_per_split"], 8, label=f"{label}.samples_per_split")
    _constant(item["baseline"], 1.25, label=f"{label}.baseline")
    _constant(
        item["second_harmonic_scale"],
        0.35,
        label=f"{label}.second_harmonic_scale",
    )
    _constant(item["noise_scale"], 0.0, label=f"{label}.noise_scale")
    warp = item["density_warp_strength"]
    if isinstance(warp, bool) or not isinstance(warp, (int, float)):
        raise P4ProtocolError(f"{label}.density_warp_strength must be numeric")
    return item


def _predecessor_binding_document() -> dict[str, object]:
    return {
        "experiment_id": PREDECESSOR_EXPERIMENT_ID,
        "source_commit": PREDECESSOR_SOURCE_COMMIT,
        "evidence_commit": PREDECESSOR_EVIDENCE_COMMIT,
        "protocol": {
            "path": str(PREDECESSOR_PROTOCOL),
            "sha256": PREDECESSOR_PROTOCOL_SHA256,
        },
        "runner": {
            "path": str(PREDECESSOR_RUNNER),
            "sha256": PREDECESSOR_RUNNER_SHA256,
        },
        "launch": {
            "path": str(PREDECESSOR_LAUNCH),
            "sha256": PREDECESSOR_LAUNCH_SHA256,
        },
        "attempt": {
            "path": str(PREDECESSOR_ATTEMPT),
            "sha256": PREDECESSOR_ATTEMPT_SHA256,
        },
        "terminal": {
            "path": str(PREDECESSOR_TERMINAL),
            "sha256": PREDECESSOR_TERMINAL_SHA256,
        },
        "identity_consumed": True,
        "execution_terminal": "caught_error",
        "terminal_state": "invalid",
        "confirmation_accessed": True,
        "error_message_sha256": (
            "87a33ed056891afa3ba25effd7b9d55a259e271e5673e305dd0551c8d2cf410c"
        ),
        "retry_resume_rescue_authorized": False,
        "authority_transfer": False,
        "outcome_reconstruction_authorized": False,
        "external_store_required_for_source_validation": False,
    }


def _confirmation_input_binding_document() -> dict[str, object]:
    return {
        "calibration": {
            "seed": 314159,
            "density_warp_strength": 0.0,
            "reuse_classification": (
                "same-exposed-definition-successor-local-regression"
            ),
            "fresh_or_independent_claimed": False,
        },
        "predecessor_confirmation": {
            "seed": 271828,
            "density_warp_strength": 0.25,
            "accessed": True,
        },
        "successor_confirmation": {
            "seed": 271829,
            "density_warp_strength": 0.5,
        },
        "selection_rule": (
            "increment-predecessor-seed-by-one-and-double-density-warp-"
            "without-generation-or-screening"
        ),
        "disjointness_scope": "seed-and-density-warp-definition",
        "confirmation_definition_disjoint": True,
        "official_confirmation_constructed_before_freeze": False,
        "generated_values_accessed_before_freeze": False,
        "generated_input_disjointness_observed": False,
        "bytewise_disjointness_claimed": False,
        "independence_restored": False,
        "preregistration_restored": False,
        "cryptographic_unseen_restored": False,
        "scientific_authority_restored": False,
    }


def _measurement_schemas_document() -> dict[str, object]:
    return {
        "confirmation_fixed_triplet": {
            "schema_version": CONFIRMATION_STRUCTURAL_PROJECTION_SCHEMA_VERSION,
            "exact_key_count": 13,
            "exact_keys": sorted(CONFIRMATION_TRIPLET_MEASUREMENT_KEYS),
            "selector_only_keys_forbidden": sorted(
                SELECTOR_ONLY_TRIPLET_MEASUREMENT_KEYS
            ),
        },
        "selector": {
            "schema_version": SELECTOR_PROJECTION_SCHEMA_VERSION,
            "exact_key_count": 15,
            "exact_keys": sorted(SELECTOR_TRIPLET_MEASUREMENT_KEYS),
            "selector_only_keys": sorted(SELECTOR_ONLY_TRIPLET_MEASUREMENT_KEYS),
        },
        "producer_to_validator_round_trip_required": True,
        "schemas_are_not_interchangeable": True,
    }


def _validate_predecessor_evidence(
    repo_root: Path,
    binding: Mapping[str, object],
) -> None:
    _constant(binding, _predecessor_binding_document(), label="predecessor binding")
    for path, digest, label in (
        (PREDECESSOR_PROTOCOL, PREDECESSOR_PROTOCOL_SHA256, "protocol"),
        (PREDECESSOR_RUNNER, PREDECESSOR_RUNNER_SHA256, "runner"),
        (PREDECESSOR_LAUNCH, PREDECESSOR_LAUNCH_SHA256, "launch"),
        (PREDECESSOR_ATTEMPT, PREDECESSOR_ATTEMPT_SHA256, "attempt"),
        (PREDECESSOR_TERMINAL, PREDECESSOR_TERMINAL_SHA256, "terminal"),
    ):
        if _sha256_file(repo_root / path) != digest:
            raise P4ProtocolError(f"predecessor {label} bytes changed")
    for ancestor, descendant, label in (
        (
            PREDECESSOR_SOURCE_COMMIT,
            PREDECESSOR_EVIDENCE_COMMIT,
            "source-to-evidence chronology",
        ),
        (
            PREDECESSOR_EVIDENCE_COMMIT,
            "HEAD",
            "evidence-to-current chronology",
        ),
    ):
        if (
            _git_completed(
                repo_root,
                "merge-base",
                "--is-ancestor",
                ancestor,
                descendant,
            ).returncode
            != 0
        ):
            raise P4ProtocolError(f"predecessor {label} is not in the current DAG")
    launch = _load_canonical(repo_root / PREDECESSOR_LAUNCH, label="predecessor launch")
    attempt = _load_canonical(
        repo_root / PREDECESSOR_ATTEMPT, label="predecessor attempt"
    )
    terminal = _load_canonical(
        repo_root / PREDECESSOR_TERMINAL,
        label="predecessor terminal",
    )
    _constant(
        launch.get("source_commit"),
        PREDECESSOR_SOURCE_COMMIT,
        label="predecessor source commit",
    )
    _constant(
        attempt.get("identity_consumed"), True, label="predecessor consumed identity"
    )
    _constant(
        attempt.get("retry_resume_rescue_authorized"),
        False,
        label="predecessor retry boundary",
    )
    _constant(
        terminal.get("execution_terminal"),
        "caught_error",
        label="predecessor execution terminal",
    )
    result = _mapping(terminal.get("result"), label="predecessor result")
    _constant(result.get("terminal_state"), "invalid", label="predecessor state")
    _constant(
        result.get("confirmation_accessed"),
        True,
        label="predecessor confirmation access",
    )
    error = _mapping(terminal.get("error"), label="predecessor error")
    _constant(
        error.get("message_sha256"),
        _predecessor_binding_document()["error_message_sha256"],
        label="predecessor error digest",
    )


def load_and_validate_protocol(
    repo_root: Path,
    protocol_path: Path = REPOSITORY_PROTOCOL,
) -> dict[str, object]:
    """Validate the closed freeze without constructing a phantom."""

    root = repo_root.resolve()
    protocol = _load_canonical(root / protocol_path, label="P4 protocol")
    _exact_keys(
        protocol,
        {
            "schema_version",
            "experiment_id",
            "decision_date",
            "status",
            "authority_binding",
            "successor_authorization",
            "predecessor_binding",
            "confirmation_input_binding",
            "measurement_schemas",
            "chronology",
            "claim_boundary",
            "execution_boundary",
            "source_bindings",
            "substrates",
            "graph_selector",
            "cycle_classes",
            "cycle_representative_semantics",
            "crossed_matrix",
            "controls",
            "control_contracts",
            "readout_threshold_rule",
            "threshold_calibration",
            "scale_selection_forbidden_reads",
            "stop_rules",
            "publication_contract",
        },
        label="P4 protocol",
    )
    _constant(protocol["schema_version"], PROTOCOL_SCHEMA_VERSION, label="schema")
    _constant(protocol["experiment_id"], EXPERIMENT_ID, label="experiment_id")
    _constant(protocol["decision_date"], "2026-08-25", label="decision_date")
    _constant(protocol["status"], "frozen_not_run", label="status")

    _constant(
        protocol["successor_authorization"],
        {
            "decision_date": "2026-08-25",
            "scope": "level-0-source-freeze-only",
            "source_freeze_authorized": True,
            "launch_created_by_source_freeze": False,
            "attempt_authorized_by_source_freeze": False,
            "execution_performed_by_source_freeze": False,
            "authority_transfer_from_predecessor": False,
            "scientific_authority": False,
        },
        label="successor authorization",
    )
    predecessor_binding = _mapping(
        protocol["predecessor_binding"], label="predecessor_binding"
    )
    _validate_predecessor_evidence(root, predecessor_binding)
    _constant(
        protocol["confirmation_input_binding"],
        _confirmation_input_binding_document(),
        label="confirmation input binding",
    )
    _constant(
        protocol["measurement_schemas"],
        _measurement_schemas_document(),
        label="measurement schemas",
    )

    hypotheses_path = root / REPOSITORY_HYPOTHESES
    if _sha256_file(hypotheses_path) != NEXT_HYPOTHESES_SHA256:
        raise P4ProtocolError("authoritative next-hypotheses bytes changed")
    hypotheses = _load_canonical(
        hypotheses_path,
        label="next-hypotheses",
        allow_bound_single_trailing_lf=True,
    )
    next_experiment = _mapping(
        hypotheses.get("next_experiment"), label="next_experiment"
    )

    authority = _mapping(protocol["authority_binding"], label="authority_binding")
    _exact_keys(authority, {"path", "sha256", "experiment_id"}, label="authority")
    _constant(authority["path"], str(REPOSITORY_HYPOTHESES), label="authority.path")
    _constant(authority["sha256"], NEXT_HYPOTHESES_SHA256, label="authority.sha256")
    _constant(
        authority["experiment_id"],
        next_experiment["experiment_id"],
        label="authority.experiment_id",
    )

    chronology = _mapping(protocol["chronology"], label="chronology")
    _constant(
        chronology,
        {
            "operator_prior_outcome_exposure": True,
            "cryptographic_unseen": False,
            "development_only": True,
            "independent": False,
            "preregistered": False,
            "exact_confirmation_inputs_frozen_before_access": True,
        },
        label="chronology",
    )

    claim = _mapping(protocol["claim_boundary"], label="claim_boundary")
    _constant(
        claim,
        {
            "claim_ceiling": "level_0",
            "scientific_authority": False,
            "topology_authority": False,
            "integer_output_authority": False,
            "D7_state_change": False,
            "D8_state_change": False,
            "Pythia160_protocol_change": False,
            "SCI_stage_change": False,
            "model_or_subject_claim": False,
        },
        label="claim boundary",
    )

    execution = _mapping(protocol["execution_boundary"], label="execution_boundary")
    _constant(
        execution,
        {
            "model_access_authorized": False,
            "network_access_authorized": False,
            "pythia_raw_capture_access_authorized": False,
            "subject_data_access_authorized": False,
            "cache_access_authorized": False,
            "python_bytecode_cache_access_authorized": False,
            "launch_required": True,
            "launch_must_be_separately_committed": True,
            "official_inputs_must_not_be_accessed_by_prepare_launch": True,
            "graph_selection_seal_before_field_readout": True,
            "threshold_seal_before_confirmation_access": True,
        },
        label="execution boundary",
    )

    bindings = _mapping(protocol["source_bindings"], label="source_bindings")
    _exact_keys(bindings, {"runner", "runtime_files"}, label="source_bindings")
    runner_binding = _mapping(bindings["runner"], label="source_bindings.runner")
    _exact_keys(runner_binding, {"path", "sha256"}, label="runner binding")
    _constant(runner_binding["path"], str(REPOSITORY_RUNNER), label="runner path")
    runtime_bindings = _runtime_source_bindings(protocol)
    for source_path, digest in runtime_bindings.items():
        if _sha256_file(root / source_path) != digest:
            raise P4ProtocolError(f"source binding changed: {source_path}")
    if _sha256_file(root / str(runner_binding["path"])) != runner_binding["sha256"]:
        raise P4ProtocolError("runner source binding changed")

    substrates = _mapping(protocol["substrates"], label="substrates")
    _exact_keys(substrates, {"calibration", "confirmation"}, label="substrates")
    calibration = _validate_spec(substrates["calibration"], label="calibration")
    confirmation = _validate_spec(substrates["confirmation"], label="confirmation")
    _constant(calibration["seed"], 314159, label="calibration.seed")
    _constant(calibration["density_warp_strength"], 0.0, label="calibration.warp")
    _constant(confirmation["seed"], 271829, label="confirmation.seed")
    _constant(confirmation["density_warp_strength"], 0.5, label="confirmation.warp")

    expected_selector = _mapping(next_experiment["graph_selector"], label="selector")
    _constant(
        protocol["graph_selector"], expected_selector, label="graph selector authority"
    )
    expected_controls = _sequence(next_experiment["controls"], label="controls")
    _constant(protocol["controls"], expected_controls, label="control authority")
    _constant(
        protocol["control_contracts"],
        _control_contracts_document(),
        label="control contracts",
    )
    expected_threshold = _mapping(
        next_experiment["readout_threshold_rule"], label="readout threshold"
    )
    _constant(
        protocol["readout_threshold_rule"],
        expected_threshold,
        label="readout threshold authority",
    )
    design = _mapping(next_experiment["design"], label="next_experiment.design")
    _constant(
        protocol["scale_selection_forbidden_reads"],
        design["scale_selection_forbidden_reads"],
        label="scale-selection forbidden reads authority",
    )
    _constant(
        protocol["stop_rules"],
        next_experiment["stop_rules"],
        label="stop-rules authority",
    )

    cycle_classes = _mapping(protocol["cycle_classes"], label="cycle_classes")
    _constant(
        cycle_classes,
        {"central": [2, 2, 4, 4], "wide": [1, 1, 5, 5]},
        label="cycle classes",
    )

    semantics = _mapping(
        protocol["cycle_representative_semantics"],
        label="cycle_representative_semantics",
    )
    _constant(
        semantics,
        {
            "operational_definition": (
                "field-blind-canonical-graph-supported-representative-of-a-"
                "predeclared-domain-boundary"
            ),
            "uses_adjacency_and_max_span_only": True,
            "graph_only_cycle_discovery_claimed": False,
            "selection_independence_claimed": False,
            "topology_claimed": False,
            "homology_claimed": False,
        },
        label="cycle representative semantics",
    )

    matrix = _mapping(protocol["crossed_matrix"], label="crossed_matrix")
    _constant(
        matrix,
        {
            "split_roles": ["calibration", "confirmation"],
            "case_order": [name for name, _expected in CROSSED_CASES],
            "cycle_class_order": list(CYCLE_CLASS_ORDER),
            "graph_family_order": list(FAMILY_ORDER),
            "field_graph_count": 3,
            "cycle_graph_count": 3,
            "cycle_class_count": 2,
            "case_count": 3,
            "base_cell_count_per_role": 54,
            "total_base_cell_count": 108,
            "aggregate_control_receipt_count": 16,
            "control_subobservation_count": 46,
            "total_unique_observation_count": 154,
            "controls_are_not_a_cartesian_cell_axis": True,
            "purpose_adjacency_check_count_per_role": 18,
        },
        label="crossed matrix",
    )

    threshold_calibration = _mapping(
        protocol["threshold_calibration"], label="threshold_calibration"
    )
    _constant(
        threshold_calibration,
        {
            "role": "calibration",
            "case_cycle_class_graph_cells": {
                "cases": ["positive", "fixed_null", "no_core_null"],
                "cycle_classes": ["central", "wide"],
                "field_graph_families": list(FAMILY_ORDER),
                "cycle_graph_families": list(FAMILY_ORDER),
                "cell_count": 54,
            },
            "metrics": [
                "absolute_oracle_or_null_error_cycles",
                "graph_family_span_cycles",
                "pure_so2_gauge_error_cycles",
                "orientation_reversal_error_cycles",
            ],
            "aggregation": {
                "oracle_and_null": "maximum-over-54-declared-finite-absolute-errors",
                "graph_family_span": "maximum-over-6-declared-finite-spans",
                "algebraic": "two-fixed-1e-8-gates-not-threshold-inputs",
            },
            "scalar_inventory": {
                "absolute_oracle_or_null_error_cycles": 54,
                "graph_family_span_cycles": 6,
                "pure_so2_gauge_error_cycles": 1,
                "orientation_reversal_error_cycles": 1,
                "total": 62,
            },
            "empty_or_nonfinite_state": "insufficient_calibration_resolution",
        },
        label="threshold calibration",
    )

    publication = _mapping(protocol["publication_contract"], label="publication")
    _constant(
        publication,
        {
            "launch_path": str(REPOSITORY_LAUNCH),
            "attempt_path": str(REPOSITORY_ATTEMPT),
            "terminal_path": str(REPOSITORY_TERMINAL),
            "external_staging_path": str(EXTERNAL_STAGE),
            "external_store_path": str(EXTERNAL_STORE),
            "attempt_record_name": ATTEMPT_NAME,
            "graph_selection_seal_name": GRAPH_SELECTION_SEAL_NAME,
            "threshold_seal_name": THRESHOLD_SEAL_NAME,
            "confirmation_access_seal_name": CONFIRMATION_ACCESS_SEAL_NAME,
            "external_terminal_name": TERMINAL_NAME,
            "external_store_manifest_name": STORE_MANIFEST_NAME,
            "canonical_byte_limit": CANONICAL_BYTE_LIMIT,
            "dynamic_timestamp_in_payload": False,
            "attempt_exactly_one": True,
            "terminal_at_most_one": True,
            "terminal_guaranteed": False,
            "terminal_no_replace": True,
            "external_store_authoritative": True,
            "external_member_manifest_exact": True,
            "repository_attempt_projection_byte_identical": True,
            "repository_terminal_projection_byte_identical": True,
            "repository_projection_atomic_no_replace": True,
            "projection_only_repair_authorized": True,
            "scientific_retry_resume_rescue_authorized": False,
            "unresolved_stage_consumes_attempt": True,
            "unresolved_stage_terminalization_authorized": False,
            "unresolved_stage_retry_resume_rescue_authorized": False,
            "source_closure_pre_post_required": True,
            "sanitized_absolute_git_required": True,
            "python_bytecode_cache_access_recorded_separately": True,
        },
        label="publication contract",
    )
    return protocol


@dataclass(frozen=True, slots=True)
class StructuralCandidate:
    """Compact graph-only candidate used by the exact triplet selector."""

    family: str
    parameters: tuple[tuple[str, int | float], ...]
    graph_input_fingerprint_sha256: str
    vertex_order_sha256: str
    state_sha256: str
    specification_fingerprint_sha256: str
    family_identity_fingerprint_sha256: str
    graph_fingerprint_sha256: str
    edge_fingerprint_sha256: str
    component_labels_sha256: str
    degree_sha256: str
    two_core_mask_sha256: str
    edges: frozenset[tuple[int, int]]
    two_core_rows: frozenset[int]
    edge_count: int
    component_count: int
    largest_component_vertex_count: int
    two_core_vertex_count: int
    cycle_rank: int
    matched_cycle_classes: tuple[str, ...]
    cycle_binding_fingerprints: tuple[tuple[str, str], ...]

    @property
    def mean_degree(self) -> float:
        return 2.0 * float(self.edge_count) / 49.0

    @property
    def parameter_key(self) -> tuple[int | float, ...]:
        values = dict(self.parameters)
        if self.family == GraphFamily.MUTUAL_KNN.value:
            return (int(values["neighbor_count"]),)
        if self.family == GraphFamily.FIXED_RADIUS.value:
            radius = float(values["radius"])
            return (struct.unpack(">Q", struct.pack(">d", radius))[0],)
        if self.family == GraphFamily.SHARED_NEIGHBOR.value:
            return (
                int(values["neighbor_count"]),
                int(values["minimum_shared_neighbors"]),
            )
        raise P4ProtocolError(f"unsupported graph family {self.family!r}")

    def to_dict(self) -> dict[str, object]:
        parameter_bits = {
            name: (
                struct.pack(">d", float(value)).hex()
                if isinstance(value, float)
                else None
            )
            for name, value in self.parameters
        }
        return {
            "projection_schema_version": (
                "spirallens.p4-structural-candidate-projection.v0.1"
            ),
            "persisted_projection_of_in_memory_receipt": True,
            "receipt_round_trip_claimed": False,
            "family": self.family,
            "parameters": dict(self.parameters),
            "float64_parameter_big_endian_bits": parameter_bits,
            "graph_input_fingerprint_sha256": self.graph_input_fingerprint_sha256,
            "vertex_order_sha256": self.vertex_order_sha256,
            "state_sha256": self.state_sha256,
            "specification_fingerprint_sha256": (self.specification_fingerprint_sha256),
            "family_identity_fingerprint_sha256": (
                self.family_identity_fingerprint_sha256
            ),
            "graph_fingerprint_sha256": self.graph_fingerprint_sha256,
            "edge_fingerprint_sha256": self.edge_fingerprint_sha256,
            "component_labels_sha256": self.component_labels_sha256,
            "degree_sha256": self.degree_sha256,
            "two_core_mask_sha256": self.two_core_mask_sha256,
            "canonical_edges": [list(edge) for edge in sorted(self.edges)],
            "edge_count": self.edge_count,
            "mean_degree": self.mean_degree,
            "component_count": self.component_count,
            "largest_component_vertex_count": self.largest_component_vertex_count,
            "two_core_vertex_count": self.two_core_vertex_count,
            "cycle_rank": self.cycle_rank,
            "matched_cycle_classes": list(self.matched_cycle_classes),
            "cycle_binding_fingerprints": dict(self.cycle_binding_fingerprints),
        }


def _per_graph_rejection_reasons(candidate: StructuralCandidate) -> tuple[str, ...]:
    reasons: list[str] = []
    if not 98 <= candidate.edge_count <= 196:
        reasons.append("mean-degree-outside-four-to-eight")
    if candidate.largest_component_vertex_count < 45:
        reasons.append("largest-component-below-45")
    if candidate.two_core_vertex_count < 40:
        reasons.append("two-core-below-40")
    if candidate.cycle_rank < 2:
        reasons.append("cycle-rank-below-2")
    if candidate.matched_cycle_classes != ("central", "wide"):
        reasons.append("central-or-wide-boundary-unmatched")
    return tuple(sorted(reasons))


def _candidate_meets_per_graph(candidate: StructuralCandidate) -> bool:
    return not _per_graph_rejection_reasons(candidate)


def _pair_jaccard_counts(
    left: StructuralCandidate,
    right: StructuralCandidate,
) -> tuple[int, int]:
    return len(left.edges & right.edges), len(left.edges | right.edges)


def _triplet_measurements(
    triplet: tuple[StructuralCandidate, StructuralCandidate, StructuralCandidate],
) -> dict[str, object]:
    edges = [candidate.edge_count for candidate in triplet]
    lcc = [candidate.largest_component_vertex_count for candidate in triplet]
    cores = [candidate.two_core_vertex_count for candidate in triplet]
    common_core = len(set.intersection(*(set(item.two_core_rows) for item in triplet)))
    pairwise: list[dict[str, object]] = []
    all_different = True
    jaccard_gate = True
    for left_index, right_index in ((0, 1), (0, 2), (1, 2)):
        left = triplet[left_index]
        right = triplet[right_index]
        intersection, union = _pair_jaccard_counts(left, right)
        different = left.edges != right.edges
        within = union > 0 and 20 * intersection <= 17 * union
        all_different = all_different and different
        jaccard_gate = jaccard_gate and within
        pairwise.append(
            {
                "left_family": left.family,
                "right_family": right.family,
                "intersection_count": intersection,
                "union_count": union,
                "jaccard": intersection / union if union else None,
                "edge_sets_differ": different,
                "jaccard_at_most_0_85": within,
            }
        )
    return {
        "edge_count_minimum": min(edges),
        "edge_count_maximum": max(edges),
        "edge_count_spread": max(edges) - min(edges),
        "edge_count_ratio": max(edges) / min(edges),
        "mean_degree_target_deviation_sum": sum(
            abs(candidate.mean_degree - 6.0) for candidate in triplet
        ),
        "mean_degree_target_deviation_numerator": sum(
            abs(2 * candidate.edge_count - 294) for candidate in triplet
        ),
        "largest_component_vertex_count_spread": max(lcc) - min(lcc),
        "two_core_vertex_count_spread": max(cores) - min(cores),
        "common_two_core_intersection_count": common_core,
        "component_count_sum": sum(candidate.component_count for candidate in triplet),
        "pairwise": pairwise,
        "pairwise_edge_sets_must_differ": all_different,
        "pairwise_edge_jaccard_at_most_0_85": jaccard_gate,
    }


def _triplet_meets_requirements(measurements: Mapping[str, object]) -> bool:
    return (
        4 * int(measurements["edge_count_maximum"])
        <= 5 * int(measurements["edge_count_minimum"])
        and int(measurements["largest_component_vertex_count_spread"]) <= 2
        and int(measurements["two_core_vertex_count_spread"]) <= 4
        and int(measurements["common_two_core_intersection_count"]) >= 35
        and measurements["pairwise_edge_sets_must_differ"] is True
        and measurements["pairwise_edge_jaccard_at_most_0_85"] is True
    )


def _triplet_rejection_reasons(measurements: Mapping[str, object]) -> tuple[str, ...]:
    reasons: list[str] = []
    if 4 * int(measurements["edge_count_maximum"]) > 5 * int(
        measurements["edge_count_minimum"]
    ):
        reasons.append("edge-count-ratio-above-1.25")
    if int(measurements["largest_component_vertex_count_spread"]) > 2:
        reasons.append("largest-component-spread-above-2")
    if int(measurements["two_core_vertex_count_spread"]) > 4:
        reasons.append("two-core-spread-above-4")
    if int(measurements["common_two_core_intersection_count"]) < 35:
        reasons.append("common-two-core-below-35")
    if measurements["pairwise_edge_sets_must_differ"] is not True:
        reasons.append("pairwise-edge-sets-not-distinct")
    if measurements["pairwise_edge_jaccard_at_most_0_85"] is not True:
        reasons.append("pairwise-edge-jaccard-above-0.85")
    return tuple(sorted(reasons))


def choose_graph_triplet(
    candidates: Sequence[StructuralCandidate],
) -> tuple[
    tuple[StructuralCandidate, StructuralCandidate, StructuralCandidate] | None,
    dict[str, object] | None,
    dict[str, object],
]:
    """Apply the frozen hard gates and lexicographic objective.

    Jaccard is an eligibility gate only and is intentionally absent from the
    objective.  The integer numerator for mean-degree deviation avoids a
    floating-point tie decision.
    """

    ordered_candidates = tuple(
        sorted(
            candidates,
            key=lambda item: (FAMILY_ORDER.index(item.family), item.parameter_key),
        )
    )
    all_candidate_projection = [item.to_dict() for item in ordered_candidates]
    by_family: dict[str, tuple[StructuralCandidate, ...]] = {}
    generated_counts: dict[str, int] = {}
    eligible_counts: dict[str, int] = {}
    per_graph_rejections: dict[str, int] = {}
    per_graph_decisions: list[dict[str, object]] = []
    for family in FAMILY_ORDER:
        generated = tuple(item for item in ordered_candidates if item.family == family)
        eligible_family: list[StructuralCandidate] = []
        for candidate in generated:
            reasons = _per_graph_rejection_reasons(candidate)
            per_graph_decisions.append(
                {
                    "family": candidate.family,
                    "parameter_key": list(candidate.parameter_key),
                    "graph_fingerprint_sha256": candidate.graph_fingerprint_sha256,
                    "rejection_reasons": list(reasons),
                }
            )
            if not reasons:
                eligible_family.append(candidate)
            for reason in reasons:
                per_graph_rejections[reason] = per_graph_rejections.get(reason, 0) + 1
        by_family[family] = tuple(eligible_family)
        generated_counts[family] = len(generated)
        eligible_counts[family] = len(eligible_family)
    decision_hasher = hashlib.sha256()
    triplet_rejections: dict[str, int] = {}
    triplets_considered = 0
    eligible: list[
        tuple[
            tuple[int | float | tuple[int | float, ...], ...],
            tuple[StructuralCandidate, StructuralCandidate, StructuralCandidate],
            dict[str, object],
        ]
    ] = []
    for raw in product(*(by_family[family] for family in FAMILY_ORDER)):
        triplets_considered += 1
        triplet = (raw[0], raw[1], raw[2])
        measurements = _triplet_measurements(triplet)
        reasons = _triplet_rejection_reasons(measurements)
        decision_record = {
            "parameter_tuple": [
                item for candidate in triplet for item in candidate.parameter_key
            ],
            "graph_fingerprints": [
                candidate.graph_fingerprint_sha256 for candidate in triplet
            ],
            "rejection_reasons": list(reasons),
        }
        encoded = canonical_json_bytes(decision_record)
        decision_hasher.update(len(encoded).to_bytes(8, "big"))
        decision_hasher.update(encoded)
        if reasons:
            for reason in reasons:
                triplet_rejections[reason] = triplet_rejections.get(reason, 0) + 1
            continue
        objective: tuple[int | float | tuple[int | float, ...], ...] = (
            int(measurements["edge_count_spread"]),
            int(measurements["mean_degree_target_deviation_numerator"]),
            -int(measurements["common_two_core_intersection_count"]),
            int(measurements["component_count_sum"]),
            tuple(item for candidate in triplet for item in candidate.parameter_key),
        )
        eligible.append((objective, triplet, measurements))
    audit: dict[str, object] = {
        "generated_candidate_counts": generated_counts,
        "per_graph_eligible_candidate_counts": eligible_counts,
        "per_graph_rejection_reason_counts": dict(sorted(per_graph_rejections.items())),
        "all_candidate_projection_sha256": canonical_json_sha256(
            all_candidate_projection
        ),
        "per_graph_decision_count": len(per_graph_decisions),
        "all_per_graph_decisions_sha256": canonical_json_sha256(per_graph_decisions),
        "triplets_considered": triplets_considered,
        "triplet_rejection_reason_counts": dict(sorted(triplet_rejections.items())),
        "all_triplet_decisions_sha256": decision_hasher.hexdigest(),
        "eligible_triplets": len(eligible),
    }
    if not eligible:
        return None, None, audit
    eligible.sort(key=lambda item: item[0])
    _objective, selected, measurements = eligible[0]
    measurements = dict(measurements)
    measurements["lexicographic_objective"] = [
        measurements["edge_count_spread"],
        measurements["mean_degree_target_deviation_numerator"],
        -int(measurements["common_two_core_intersection_count"]),
        measurements["component_count_sum"],
        [item for candidate in selected for item in candidate.parameter_key],
    ]
    measurements["jaccard_used_as_objective"] = False
    return selected, measurements, audit


def _graph_metrics(receipt: GraphConstructionReceipt) -> tuple[int, int, int, int, int]:
    edge_count = int(receipt.canonical_edges.shape[0])
    labels, counts = np.unique(receipt.component_labels, return_counts=True)
    component_count = int(labels.shape[0])
    largest = int(np.max(counts))
    two_core = int(np.count_nonzero(receipt.two_core_mask))
    cycle_rank = edge_count - 49 + component_count
    return edge_count, component_count, largest, two_core, cycle_rank


def _candidate_from_receipt(
    receipt: GraphConstructionReceipt,
    *,
    domain: object,
    cycle_specs: Mapping[str, object],
    refinement_rule: BoundaryRefinementRule,
) -> StructuralCandidate:
    edge_count, component_count, largest, two_core, cycle_rank = _graph_metrics(receipt)
    attempts = {
        name: bind_cycle_class(receipt, spec, refinement_rule)
        for name, spec in cycle_specs.items()
    }
    matched = tuple(name for name in ("central", "wide") if attempts[name].matched)
    bindings = tuple(
        (
            name,
            attempts[name].binding.fingerprint_sha256
            if attempts[name].binding is not None
            else "",
        )
        for name in ("central", "wide")
    )
    specification = receipt.specification
    if isinstance(specification, MutualKnnSpec):
        parameters: tuple[tuple[str, int | float], ...] = (
            ("neighbor_count", specification.neighbor_count),
        )
    elif isinstance(specification, RadiusGraphSpec):
        parameters = (("radius", specification.radius),)
    elif isinstance(specification, SharedNeighborSpec):
        parameters = (
            ("minimum_shared_neighbors", specification.minimum_shared_neighbors),
            ("neighbor_count", specification.neighbor_count),
        )
    else:  # pragma: no cover - graph receipt contract is closed
        raise AssertionError("unsupported graph specification")
    return StructuralCandidate(
        family=specification.family.value,
        parameters=parameters,
        graph_input_fingerprint_sha256=receipt.graph_input.fingerprint_sha256,
        vertex_order_sha256=receipt.graph_input.vertex_order_sha256,
        state_sha256=receipt.graph_input.state_sha256,
        specification_fingerprint_sha256=specification.fingerprint_sha256,
        family_identity_fingerprint_sha256=receipt.family_identity.fingerprint_sha256,
        graph_fingerprint_sha256=receipt.fingerprint_sha256,
        edge_fingerprint_sha256=receipt.edge_order_sha256,
        component_labels_sha256=array_sha256(receipt.component_labels),
        degree_sha256=array_sha256(receipt.degree),
        two_core_mask_sha256=array_sha256(receipt.two_core_mask),
        edges=frozenset(
            (int(left), int(right)) for left, right in receipt.canonical_edges.tolist()
        ),
        two_core_rows=frozenset(
            int(row) for row in np.flatnonzero(receipt.two_core_mask)
        ),
        edge_count=edge_count,
        component_count=component_count,
        largest_component_vertex_count=largest,
        two_core_vertex_count=two_core,
        cycle_rank=cycle_rank,
        matched_cycle_classes=matched,
        cycle_binding_fingerprints=bindings,
    )


def _cycle_context(
    graph_input: GraphInput,
    oriented_faces: object,
    protocol: Mapping[str, object],
) -> tuple[object, dict[str, object], BoundaryRefinementRule]:
    domain = build_discrete_domain_complex(
        graph_input,
        oriented_faces,
        domain_id=f"p4-v0-2-domain-{graph_input.primary_unit_id}",
        primary_unit_id=graph_input.primary_unit_id,
    )
    class_rectangles = _mapping(protocol["cycle_classes"], label="cycle classes")
    classes: dict[str, object] = {}
    for name in ("central", "wide"):
        rectangle = _sequence(class_rectangles[name], label=f"cycle class {name}")
        classes[name] = define_boundary_cycle_class(
            domain,
            rectangular_grid_support_faces(
                grid_side=7,
                x_min=rectangle[0],
                y_min=rectangle[1],
                x_max=rectangle[2],
                y_max=rectangle[3],
            ),
            cycle_class_spec_id=f"p4-v0-2-{name}",
            primary_unit_id=graph_input.primary_unit_id,
            matched_set_id=f"p4-v0-2-matched-{name}",
        )
    rule = BoundaryRefinementRule(
        rule_id="p4-v0-2-forward-span-four",
        max_domain_edges_per_graph_edge=4,
    )
    return domain, classes, rule


def _pairwise_distances(graph_input: GraphInput) -> np.ndarray:
    rows = graph_input.states.shape[0]
    distances = np.empty((rows, rows), dtype="<f8")
    for row in range(rows):
        distances[row] = coordinate_order_invariant_euclidean_norm(
            graph_input.states - graph_input.states[row], axis=1
        )
    distances[distances == 0.0] = 0.0
    np.fill_diagonal(distances, np.inf)
    return distances


def enumerate_structural_candidates(
    graph_input: GraphInput,
    oriented_faces: object,
    protocol: Mapping[str, object],
) -> tuple[StructuralCandidate, ...]:
    """Enumerate the exact field-blind candidate sets from the freeze."""

    if graph_input.states.shape[0] != 49:
        raise P4RunError("selector requires exactly 49 vertices")
    domain, cycle_specs, rule = _cycle_context(graph_input, oriented_faces, protocol)
    candidates: list[StructuralCandidate] = []
    for neighbor_count in range(2, 17):
        receipt = construct_mutual_knn(
            graph_input,
            MutualKnnSpec(
                spec_id=f"p4-v0-2-mutual-k{neighbor_count:02d}",
                purpose=GraphPurpose.CYCLE_CONSTRUCTION,
                neighbor_count=neighbor_count,
            ),
        )
        candidates.append(
            _candidate_from_receipt(
                receipt, domain=domain, cycle_specs=cycle_specs, refinement_rule=rule
            )
        )

    distances = _pairwise_distances(graph_input)
    upper = distances[np.triu_indices(49, k=1)]
    unique_distances = sorted(
        float(item) for item in np.unique(upper[np.isfinite(upper)])
    )
    for rank, radius in enumerate(unique_distances):
        implied_edges = int(np.count_nonzero(upper <= radius))
        if not 98 <= implied_edges <= 196:
            continue
        if radius == 0.0:
            continue
        radius_digest = hashlib.sha256(float(radius).hex().encode("ascii")).hexdigest()[
            :12
        ]
        receipt = construct_radius_graph(
            graph_input,
            RadiusGraphSpec(
                spec_id=f"p4-v0-2-radius-r{rank:04d}-{radius_digest}",
                purpose=GraphPurpose.CYCLE_CONSTRUCTION,
                radius=radius,
            ),
        )
        candidates.append(
            _candidate_from_receipt(
                receipt, domain=domain, cycle_specs=cycle_specs, refinement_rule=rule
            )
        )

    for neighbor_count in range(2, 17):
        for minimum_shared_neighbors in range(1, neighbor_count + 1):
            receipt = construct_shared_neighbor_graph(
                graph_input,
                SharedNeighborSpec(
                    spec_id=(
                        f"p4-v0-2-shared-k{neighbor_count:02d}-"
                        f"m{minimum_shared_neighbors:02d}"
                    ),
                    purpose=GraphPurpose.CYCLE_CONSTRUCTION,
                    neighbor_count=neighbor_count,
                    minimum_shared_neighbors=minimum_shared_neighbors,
                ),
            )
            candidates.append(
                _candidate_from_receipt(
                    receipt,
                    domain=domain,
                    cycle_specs=cycle_specs,
                    refinement_rule=rule,
                )
            )
    return tuple(candidates)


def select_structural_triplet(
    graph_input: GraphInput,
    oriented_faces: object,
    protocol: Mapping[str, object],
) -> dict[str, object]:
    candidates = enumerate_structural_candidates(graph_input, oriented_faces, protocol)
    selected, measurements, counts = choose_graph_triplet(candidates)
    distances = _pairwise_distances(graph_input)
    upper = distances[np.triu_indices(49, k=1)]
    finite_upper = upper[np.isfinite(upper)]
    zero_pair_count = int(np.count_nonzero(finite_upper == 0.0))
    unique = sorted(float(item) for item in np.unique(finite_upper))
    radius_scan = [
        {
            "float64_big_endian_bits": struct.pack(">d", value).hex(),
            "edge_count": int(np.count_nonzero(upper <= value)),
            "within_edge_budget": 98 <= int(np.count_nonzero(upper <= value)) <= 196,
            "positive": value > 0.0,
            "constructor_representable": value > 0.0,
        }
        for value in unique
    ]
    counts = {
        **counts,
        "radius_unique_finite_distance_count": len(radius_scan),
        "radius_budget_eligible_distance_count": sum(
            item["within_edge_budget"] is True for item in radius_scan
        ),
        "radius_distance_scan_sha256": canonical_json_sha256(radius_scan),
        "radius_zero_pair_count": zero_pair_count,
        "radius_float64_uint64_order": True,
        "radius_budget_eligible_zero_unrepresentable": any(
            item["within_edge_budget"] is True
            and item["constructor_representable"] is False
            for item in radius_scan
        ),
    }
    zero_unrepresentable = bool(counts["radius_budget_eligible_zero_unrepresentable"])
    if zero_unrepresentable:
        raise P4RunError(
            "budget-eligible zero radius is outside the frozen constructor domain"
        )
    return {
        "projection_schema_version": SELECTOR_PROJECTION_SCHEMA_VERSION,
        "state": "pass" if selected is not None else "insufficient",
        "reason": (
            "ok" if selected is not None else "no-eligible-three-family-triplet"
        ),
        "selector_input": {
            "input_type": "GraphInput-plus-oriented-domain-faces-only",
            "graph_input_fingerprint_sha256": graph_input.fingerprint_sha256,
            "vertex_order_sha256": graph_input.vertex_order_sha256,
            "state_sha256": graph_input.state_sha256,
            "oriented_faces_sha256": array_sha256(np.asarray(oriented_faces)),
            "case_object_accepted": False,
            "truth_object_accepted": False,
            "field_object_accepted": False,
            "core_object_accepted": False,
        },
        "selector_audit": counts,
        "selected": (
            [item.to_dict() for item in selected] if selected is not None else None
        ),
        "objective": (
            measurements["lexicographic_objective"]
            if measurements is not None
            else None
        ),
        "triplet_measurements": measurements,
        "field_read": False,
        "core_read": False,
        "holonomy_read": False,
        "phase_read": False,
        "winding_read": False,
        "charge_read": False,
        "pythia_terminal_candidate_values_read": False,
    }


def _spec_from_document(
    family: str,
    parameters: Mapping[str, object],
    *,
    purpose: GraphPurpose,
    graph_id: str,
) -> MutualKnnSpec | RadiusGraphSpec | SharedNeighborSpec:
    if family == GraphFamily.MUTUAL_KNN.value:
        return MutualKnnSpec(
            spec_id=graph_id,
            purpose=purpose,
            neighbor_count=int(parameters["neighbor_count"]),
        )
    if family == GraphFamily.FIXED_RADIUS.value:
        return RadiusGraphSpec(
            spec_id=graph_id,
            purpose=purpose,
            radius=float(parameters["radius"]),
        )
    if family == GraphFamily.SHARED_NEIGHBOR.value:
        return SharedNeighborSpec(
            spec_id=graph_id,
            purpose=purpose,
            neighbor_count=int(parameters["neighbor_count"]),
            minimum_shared_neighbors=int(parameters["minimum_shared_neighbors"]),
        )
    raise P4RunError(f"unsupported selected family {family!r}")


def _construct_specified(
    graph_input: GraphInput,
    family: str,
    parameters: Mapping[str, object],
    *,
    purpose: GraphPurpose,
    graph_id: str,
) -> GraphConstructionReceipt:
    spec = _spec_from_document(family, parameters, purpose=purpose, graph_id=graph_id)
    if isinstance(spec, MutualKnnSpec):
        return construct_mutual_knn(graph_input, spec)
    if isinstance(spec, RadiusGraphSpec):
        return construct_radius_graph(graph_input, spec)
    return construct_shared_neighbor_graph(graph_input, spec)


def assess_fixed_triplet(
    graph_input: GraphInput,
    oriented_faces: object,
    protocol: Mapping[str, object],
    selected_documents: Sequence[object],
) -> tuple[dict[str, object], tuple[StructuralCandidate, ...]]:
    domain, cycle_specs, rule = _cycle_context(graph_input, oriented_faces, protocol)
    candidates: list[StructuralCandidate] = []
    for index, raw in enumerate(selected_documents):
        item = _mapping(raw, label=f"selected[{index}]")
        family = item["family"]
        parameters = _mapping(item["parameters"], label="selected parameters")
        if not isinstance(family, str):
            raise P4RunError("selected family must be a string")
        receipt = _construct_specified(
            graph_input,
            family,
            parameters,
            purpose=GraphPurpose.CYCLE_CONSTRUCTION,
            graph_id=f"p4-v0-2-confirm-{index}",
        )
        candidates.append(
            _candidate_from_receipt(
                receipt, domain=domain, cycle_specs=cycle_specs, refinement_rule=rule
            )
        )
    if tuple(item.family for item in candidates) != FAMILY_ORDER:
        raise P4RunError("selected triplet family order changed")
    triplet = (candidates[0], candidates[1], candidates[2])
    measurements = _triplet_measurements(triplet)
    passed = all(_candidate_meets_per_graph(item) for item in triplet) and (
        _triplet_meets_requirements(measurements)
    )
    return (
        {
            "projection_schema_version": (
                CONFIRMATION_STRUCTURAL_PROJECTION_SCHEMA_VERSION
            ),
            "state": "pass" if passed else "insufficient",
            "reason": "ok" if passed else "fixed-triplet-failed-confirmation-support",
            "selected": [item.to_dict() for item in triplet],
            "triplet_measurements": measurements,
            "selector_rerun": False,
        },
        triplet,
    )


def _graph_axes(selected: Sequence[object]) -> GraphAxes:
    field: list[GraphDeclaration] = []
    cycle: list[GraphDeclaration] = []
    for prefix, purpose, target in (
        ("a", GraphPurpose.FIELD_ESTIMATION, field),
        ("b", GraphPurpose.CYCLE_CONSTRUCTION, cycle),
    ):
        for raw in selected:
            item = _mapping(raw, label="selected graph")
            family = GraphFamily(str(item["family"]))
            parameters = _mapping(item["parameters"], label="selected parameters")
            target.append(
                GraphDeclaration(
                    graph_id=f"p4-v0-2-{prefix}-{family.value}",
                    family=family,
                    purpose=purpose,
                    parameters=tuple(
                        (key, value) for key, value in sorted(parameters.items())
                    ),
                )
            )
    return GraphAxes(field_estimation=tuple(field), cycle_construction=tuple(cycle))


def _phantom_spec(document: Mapping[str, object]) -> CartesianFourierDomainSpec:
    return CartesianFourierDomainSpec(
        seed=int(document["seed"]),
        grid_side=int(document["grid_side"]),
        ambient_dimension=int(document["ambient_dimension"]),
        samples_per_split=int(document["samples_per_split"]),
        baseline=float(document["baseline"]),
        second_harmonic_scale=float(document["second_harmonic_scale"]),
        noise_scale=float(document["noise_scale"]),
        density_warp_strength=float(document["density_warp_strength"]),
    )


def _loop_policy() -> LoopPhasePolicy:
    return LoopPhasePolicy(
        policy_id="p4-v0-2-model-free-continuous-readout",
        amplitude_floor=1e-12,
        identifiability_floor=1e-12,
        coherence_floor=1e-12,
        branch_margin_radians=1e-9,
        integer_residual_tolerance_cycles=0.05,
        nonzero_floor_cycles=0.5,
    )


def _matrix_readouts(
    *,
    role: str,
    phantom: object,
    selected: Sequence[object],
    protocol: Mapping[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    axes = _graph_axes(selected)
    policy = _loop_policy()
    cells: list[dict[str, object]] = []
    purpose_adjacency_checks: list[dict[str, object]] = []
    representatives: dict[str, object] = {}
    blinds_by_case: dict[str, dict[str, object]] = {
        name: {} for name, _expected in CROSSED_CASES
    }
    center_amplitudes_by_case: dict[str, dict[str, float]] = {
        name: {} for name, _expected in CROSSED_CASES
    }
    for case_name, expected in CROSSED_CASES:
        case = getattr(phantom, case_name)
        inputs = case.estimator_inputs
        graph_input = GraphInput(
            primary_unit_id=f"p4-v0-2-{role}-{case_name.replace('_', '-')}",
            vertex_ids=inputs.row_ids,
            states=inputs.states,
        )
        estimates_by_class: dict[str, tuple[object, ...]] = {}
        for class_name, rectangle_raw in _mapping(
            protocol["cycle_classes"], label="cycle classes"
        ).items():
            rectangle = _sequence(rectangle_raw, label=f"{class_name} rectangle")
            execution = build_crossed_graph_execution(
                graph_input=graph_input,
                graph_axes=axes,
                oriented_faces=inputs.oriented_faces,
                support_face_indices=rectangular_grid_support_faces(
                    grid_side=7,
                    x_min=rectangle[0],
                    y_min=rectangle[1],
                    x_max=rectangle[2],
                    y_max=rectangle[3],
                ),
                domain_id=f"p4-v0-2-{role}-{case_name}-{class_name}",
                cycle_class_spec_id=f"p4-v0-2-{class_name}",
                matched_set_id=f"p4-v0-2-{role}-{class_name}",
                refinement_rule=BoundaryRefinementRule(
                    rule_id="p4-v0-2-forward-span-four",
                    max_domain_edges_per_graph_edge=4,
                ),
            )
            if not all(attempt.matched for attempt in execution.cycle_attempts):
                raise P4RunError("fixed triplet lost a required cycle-class binding")
            for field_graph, cycle_graph in zip(
                execution.field_graphs, execution.cycle_graphs, strict=True
            ):
                same_edges = np.array_equal(
                    field_graph.canonical_edges, cycle_graph.canonical_edges
                )
                same_order_digest = (
                    field_graph.edge_order_sha256 == cycle_graph.edge_order_sha256
                )
                purpose_adjacency_checks.append(
                    {
                        "case": case_name,
                        "cycle_class": class_name,
                        "family": field_graph.specification.family.value,
                        "field_graph_fingerprint_sha256": (
                            field_graph.fingerprint_sha256
                        ),
                        "cycle_graph_fingerprint_sha256": (
                            cycle_graph.fingerprint_sha256
                        ),
                        "field_canonical_edge_order_sha256": (
                            field_graph.edge_order_sha256
                        ),
                        "cycle_canonical_edge_order_sha256": (
                            cycle_graph.edge_order_sha256
                        ),
                        "fingerprint_equality_required": False,
                        "canonical_adjacency_equal": same_edges,
                        "canonical_edge_order_sha256_equal": same_order_digest,
                    }
                )
                if not same_edges or not same_order_digest:
                    raise P4RunError(
                        "field-purpose and cycle-purpose adjacency/order differ"
                    )
            estimates = tuple(
                estimate_cartesian_fourier_field(inputs, graph)
                for graph in execution.field_graphs
            )
            estimates_by_class[class_name] = estimates
            if class_name == "central":
                for estimate, field_graph in zip(
                    estimates, execution.field_graphs, strict=True
                ):
                    center_amplitudes_by_case[case_name][
                        field_graph.specification.family.value
                    ] = float(estimate.amplitude[24])
            for estimate, field_graph in zip(
                estimates, execution.field_graphs, strict=True
            ):
                for cycle_graph in execution.cycle_graphs:
                    blind = build_crossed_blind_loop_input(
                        execution,
                        estimate,
                        cycle_graph_id=cycle_graph.specification.spec_id,
                        primary_unit_sha256=hashlib.sha256(
                            f"{role}:{case_name}:{class_name}".encode("ascii")
                        ).hexdigest(),
                    )
                    prediction = estimate_and_seal_loop(blind, policy)
                    cell_identifier = _cell_id(
                        role,
                        case_name,
                        class_name,
                        field_graph.specification.family.value,
                        cycle_graph.specification.family.value,
                    )
                    blinds_by_case[case_name][cell_identifier] = blind
                    if case_name == "positive":
                        representatives.setdefault(class_name, blind)
                    total = prediction.signed_total_cycles
                    error = abs(total - expected) if total is not None else None
                    cells.append(
                        {
                            "cell_id": cell_identifier,
                            "case": case_name,
                            "cycle_class": class_name,
                            "field_graph_family": field_graph.specification.family.value,
                            "cycle_graph_family": cycle_graph.specification.family.value,
                            "attempt_status": prediction.observed_attempt_status.value,
                            "signed_total_cycles": total,
                            "expected_continuous_cycles": expected,
                            "absolute_error_cycles": error,
                            "reason_codes": list(prediction.reason_codes),
                        }
                    )
    if set(representatives) != set(CYCLE_CLASS_ORDER):
        raise P4RunError("positive representatives do not cover both cycle classes")
    required_cell_ids = _required_cell_ids(
        role, tuple(name for name, _expected in CROSSED_CASES)
    )
    observed_cell_ids = [str(item["cell_id"]) for item in cells]
    if (
        len(cells) != 54
        or len(set(observed_cell_ids)) != 54
        or set(observed_cell_ids) != set(required_cell_ids)
        or len(purpose_adjacency_checks) != 18
        or any(len(value) != 18 for value in blinds_by_case.values())
        or any(len(value) != 3 for value in center_amplitudes_by_case.values())
    ):
        raise P4RunError("crossed matrix does not cover the frozen cell manifest")
    evaluable_errors = [
        float(item["absolute_error_cycles"])
        for item in cells
        if item["absolute_error_cycles"] is not None
    ]
    spans: list[dict[str, object]] = []
    for case_name, class_name in product(
        (name for name, _expected in CROSSED_CASES), CYCLE_CLASS_ORDER
    ):
        totals = [
            float(item["signed_total_cycles"])
            for item in cells
            if item["case"] == case_name
            and item["cycle_class"] == class_name
            and item["signed_total_cycles"] is not None
        ]
        spans.append(
            {
                "span_id": _span_id(role, case_name, class_name),
                "case": case_name,
                "cycle_class": class_name,
                "graph_family_span_cycles": max(totals) - min(totals)
                if totals
                else None,
            }
        )
    return (
        {
            "role": role,
            "cell_count": len(cells),
            "required_cell_ids_sha256": canonical_json_sha256(required_cell_ids),
            "cells": cells,
            "purpose_adjacency_checks": purpose_adjacency_checks,
            "purpose_adjacency_check_count": len(purpose_adjacency_checks),
            "purpose_adjacency_checks_sha256": canonical_json_sha256(
                purpose_adjacency_checks
            ),
            "worst_oracle_or_null_error_cycles": (
                max(evaluable_errors) if evaluable_errors else None
            ),
            "graph_family_spans": spans,
        },
        {
            "representatives": representatives,
            "blinds_by_case": blinds_by_case,
            "center_amplitudes_by_case": center_amplitudes_by_case,
        },
    )


def _edge_ids(receipt: GraphConstructionReceipt) -> frozenset[tuple[int, int]]:
    ids = receipt.graph_input.vertex_ids
    return frozenset(
        tuple(sorted((int(ids[left]), int(ids[right]))))
        for left, right in receipt.canonical_edges.tolist()
    )


def _edge_content_sha256(receipt: GraphConstructionReceipt) -> str:
    return canonical_json_sha256([list(edge) for edge in sorted(_edge_ids(receipt))])


def _row_edge_content_sha256(edges: Iterable[tuple[int, int]]) -> str:
    return canonical_json_sha256([list(edge) for edge in sorted(set(edges))])


def _vertex_id_edges_from_rows(
    edges: Iterable[tuple[int, int]],
    vertex_ids: Sequence[int],
) -> frozenset[tuple[int, int]]:
    return frozenset(
        tuple(sorted((int(vertex_ids[left]), int(vertex_ids[right]))))
        for left, right in edges
    )


def _derive_canonical_rewire_observation(
    edges: Iterable[tuple[int, int]],
    *,
    family: str,
) -> dict[str, object]:
    """Apply, or exhaust, the frozen lexicographic two-switch scan."""

    edges = set(edges)
    ordered = sorted(edges)
    for first_index, (a, b) in enumerate(ordered):
        for c, d in ordered[first_index + 1 :]:
            if len({a, b, c, d}) != 4:
                continue
            replacement = {tuple(sorted((a, c))), tuple(sorted((b, d)))}
            if len(replacement) != 2 or replacement & edges:
                continue
            rewired = (edges - {(a, b), (c, d)}) | replacement
            before = [0] * 49
            after = [0] * 49
            for left, right in edges:
                before[left] += 1
                before[right] += 1
            for left, right in rewired:
                after[left] += 1
                after[right] += 1
            simple_graph = all(
                left < right and left != right for left, right in rewired
            ) and len(rewired) == len(edges)
            symmetric_difference = len(edges ^ rewired)
            passed = (
                before == after
                and rewired != edges
                and simple_graph
                and symmetric_difference == 4
            )
            return {
                "observation_id": f"degree_preserving_rewire|{family}",
                "state": "pass" if passed else "fail",
                "degree_preserved": before == after,
                "edge_set_changed": rewired != edges,
                "simple_graph_verified": simple_graph,
                "symmetric_difference_edge_count": symmetric_difference,
                "removed_edges": [[a, b], [c, d]],
                "added_edges": [list(item) for item in sorted(replacement)],
            }
    return {
        "observation_id": f"degree_preserving_rewire|{family}",
        "state": "insufficient",
        "degree_preserved": False,
        "edge_set_changed": False,
        "simple_graph_verified": False,
        "symmetric_difference_edge_count": 0,
        "reason": "no-canonical-two-switch",
    }


def _rewire_observation(candidate: StructuralCandidate) -> dict[str, object]:
    return _derive_canonical_rewire_observation(
        candidate.edges,
        family=candidate.family,
    )


def _rewire_control(candidates: Sequence[StructuralCandidate]) -> dict[str, object]:
    observations = [_rewire_observation(candidate) for candidate in candidates]
    return {
        "control_id": "degree_preserving_rewire",
        "observed_state": (
            "pass"
            if all(item["state"] == "pass" for item in observations)
            else (
                "insufficient"
                if any(item["state"] == "insufficient" for item in observations)
                else "fail"
            )
        ),
        "observations": observations,
    }


def _graph_invariance_controls(
    graph_input: GraphInput,
    selected_documents: Sequence[object],
) -> list[dict[str, object]]:
    """Compare constructed-receipt edges; this is not raw-transform proof."""

    base: list[GraphConstructionReceipt] = []
    for index, raw in enumerate(selected_documents):
        item = _mapping(raw, label="selected graph")
        base.append(
            _construct_specified(
                graph_input,
                str(item["family"]),
                _mapping(item["parameters"], label="parameters"),
                purpose=GraphPurpose.CYCLE_CONSTRUCTION,
                graph_id=f"p4-v0-2-control-base-{index}",
            )
        )

    permutation = np.arange(48, -1, -1, dtype="<i8")
    permuted_input = GraphInput(
        primary_unit_id="p4-v0-2-joint-permutation",
        vertex_ids=graph_input.vertex_ids[permutation],
        states=graph_input.states[permutation],
    )
    joint_observations: list[dict[str, object]] = []
    ambient_observations: list[dict[str, object]] = []
    scaling_observations: list[dict[str, object]] = []
    dimension_permutation = np.arange(graph_input.states.shape[1] - 1, -1, -1)
    signs = np.where(np.arange(graph_input.states.shape[1]) % 2 == 0, 1.0, -1.0)
    orthogonal_states = graph_input.states[:, dimension_permutation] * signs
    orthogonal_input = GraphInput(
        primary_unit_id="p4-v0-2-ambient-orthogonal",
        vertex_ids=graph_input.vertex_ids,
        states=orthogonal_states,
    )
    scaled_input = GraphInput(
        primary_unit_id="p4-v0-2-global-scaling",
        vertex_ids=graph_input.vertex_ids,
        states=2.0 * graph_input.states,
    )
    for index, (raw, base_graph) in enumerate(
        zip(selected_documents, base, strict=True)
    ):
        item = _mapping(raw, label="selected graph")
        family = str(item["family"])
        parameters = _mapping(item["parameters"], label="parameters")
        permuted_graph = _construct_specified(
            permuted_input,
            family,
            parameters,
            purpose=GraphPurpose.CYCLE_CONSTRUCTION,
            graph_id=f"p4-v0-2-control-permuted-{index}",
        )
        orthogonal_graph = _construct_specified(
            orthogonal_input,
            family,
            parameters,
            purpose=GraphPurpose.CYCLE_CONSTRUCTION,
            graph_id=f"p4-v0-2-control-orthogonal-{index}",
        )
        scaled_parameters = dict(parameters)
        if family == GraphFamily.FIXED_RADIUS.value:
            scaled_parameters["radius"] = 2.0 * float(parameters["radius"])
        scaled_graph = _construct_specified(
            scaled_input,
            family,
            scaled_parameters,
            purpose=GraphPurpose.CYCLE_CONSTRUCTION,
            graph_id=f"p4-v0-2-control-scaled-{index}",
        )
        joint_equal = _edge_ids(base_graph) == _edge_ids(permuted_graph)
        ambient_equal = (
            base_graph.edge_order_sha256 == orthogonal_graph.edge_order_sha256
        )
        scaling_equal = base_graph.edge_order_sha256 == scaled_graph.edge_order_sha256
        if base_graph.edge_order_sha256 != item["edge_fingerprint_sha256"]:
            raise P4RunError(
                "invariance-control base graph differs from the sealed family"
            )
        base_edges = frozenset(
            (int(left), int(right))
            for left, right in base_graph.canonical_edges.tolist()
        )
        permuted_edges = frozenset(
            (int(left), int(right))
            for left, right in permuted_graph.canonical_edges.tolist()
        )
        orthogonal_edges = frozenset(
            (int(left), int(right))
            for left, right in orthogonal_graph.canonical_edges.tolist()
        )
        scaled_edges = frozenset(
            (int(left), int(right))
            for left, right in scaled_graph.canonical_edges.tolist()
        )
        base_vertex_ids = [int(value) for value in graph_input.vertex_ids]
        transformed_vertex_ids = [int(value) for value in permuted_input.vertex_ids]
        if array_sha256(graph_input.vertex_ids) != item["vertex_order_sha256"]:
            raise P4RunError(
                "invariance-control base vertex order differs from sealed family"
            )
        common_evidence = {
            "base_edge_order_sha256": base_graph.edge_order_sha256,
            "sealed_family_edge_order_sha256": item["edge_fingerprint_sha256"],
            "receipt_equality_scope": ("constructed-graph-receipt-edge-equality-only"),
        }
        joint_observations.append(
            {
                "observation_id": f"joint_vertex_permutation|{family}",
                "state": "pass" if joint_equal else "fail",
                "vertex_id_edge_content_preserved": joint_equal,
                **common_evidence,
                "base_vertex_ids": base_vertex_ids,
                "base_vertex_order_sha256": array_sha256(graph_input.vertex_ids),
                "transformed_vertex_ids": transformed_vertex_ids,
                "transformed_vertex_order_sha256": array_sha256(
                    permuted_input.vertex_ids
                ),
                "transformed_canonical_edges": [
                    list(edge) for edge in sorted(permuted_edges)
                ],
                "base_edge_content_sha256": _row_edge_content_sha256(
                    _vertex_id_edges_from_rows(base_edges, base_vertex_ids)
                ),
                "transformed_edge_content_sha256": _edge_content_sha256(permuted_graph),
                "transformed_edge_order_sha256": (permuted_graph.edge_order_sha256),
            }
        )
        ambient_observations.append(
            {
                "observation_id": f"ambient_orthogonal_transform|{family}",
                "state": "pass" if ambient_equal else "fail",
                "canonical_adjacency_preserved": ambient_equal,
                **common_evidence,
                "transformed_canonical_edges": [
                    list(edge) for edge in sorted(orthogonal_edges)
                ],
                "base_edge_content_sha256": _row_edge_content_sha256(base_edges),
                "transformed_edge_content_sha256": _row_edge_content_sha256(
                    orthogonal_edges
                ),
                "transformed_edge_order_sha256": (orthogonal_graph.edge_order_sha256),
            }
        )
        scaling_observations.append(
            {
                "observation_id": f"global_norm_scaling|{family}",
                "state": "pass" if scaling_equal else "fail",
                "canonical_adjacency_preserved_with_radius_covariance": (scaling_equal),
                **common_evidence,
                "transformed_canonical_edges": [
                    list(edge) for edge in sorted(scaled_edges)
                ],
                "base_edge_content_sha256": _row_edge_content_sha256(base_edges),
                "transformed_edge_content_sha256": _row_edge_content_sha256(
                    scaled_edges
                ),
                "transformed_edge_order_sha256": scaled_graph.edge_order_sha256,
            }
        )
    return [
        {
            "control_id": "joint_vertex_permutation",
            "observed_state": (
                "pass"
                if all(item["state"] == "pass" for item in joint_observations)
                else "fail"
            ),
            "observations": joint_observations,
        },
        {
            "control_id": "ambient_orthogonal_transform",
            "observed_state": (
                "pass"
                if all(item["state"] == "pass" for item in ambient_observations)
                else "fail"
            ),
            "observations": ambient_observations,
        },
        {
            "control_id": "global_norm_scaling",
            "observed_state": (
                "pass"
                if all(item["state"] == "pass" for item in scaling_observations)
                else "fail"
            ),
            "observations": scaling_observations,
        },
    ]


def _collapsed_cycleless_control(
    graph_input: GraphInput,
    oriented_faces: object,
    protocol: Mapping[str, object],
) -> dict[str, object]:
    """Construct the frozen rank-one path; never rely on tied kNN graphs."""

    states = np.zeros_like(graph_input.states)
    states[:, 0] = np.arange(states.shape[0], dtype="<f8")
    collapsed_input = GraphInput(
        primary_unit_id="p4-v0-2-collapsed-rank-one-path",
        vertex_ids=graph_input.vertex_ids,
        states=states,
    )
    receipt = construct_radius_graph(
        collapsed_input,
        RadiusGraphSpec(
            spec_id="p4-v0-2-collapsed-unit-radius-path",
            purpose=GraphPurpose.CYCLE_CONSTRUCTION,
            radius=1.0,
        ),
    )
    domain, cycle_specs, rule = _cycle_context(
        collapsed_input, oriented_faces, protocol
    )
    candidate = _candidate_from_receipt(
        receipt,
        domain=domain,
        cycle_specs=cycle_specs,
        refinement_rule=rule,
    )
    bindings = dict(candidate.cycle_binding_fingerprints)
    graph_ok = (
        candidate.edge_count == 48
        and candidate.component_count == 1
        and candidate.largest_component_vertex_count == 49
        and candidate.two_core_vertex_count == 0
        and candidate.cycle_rank == 0
    )
    central_unmatched = "central" not in candidate.matched_cycle_classes
    wide_unmatched = "wide" not in candidate.matched_cycle_classes
    observations = [
        {
            "observation_id": "collapsed_cycleless_phantom|path-graph",
            "state": "insufficient" if graph_ok else "fail",
            "edge_count": candidate.edge_count,
            "component_count": candidate.component_count,
            "largest_component_vertex_count": (
                candidate.largest_component_vertex_count
            ),
            "two_core_vertex_count": candidate.two_core_vertex_count,
            "cycle_rank": candidate.cycle_rank,
            "edge_fingerprint_sha256": candidate.edge_fingerprint_sha256,
            "canonical_edges": [list(edge) for edge in sorted(candidate.edges)],
            "state_sha256": candidate.state_sha256,
        },
        {
            "observation_id": "collapsed_cycleless_phantom|central-binding",
            "state": "insufficient" if central_unmatched else "fail",
            "matched": not central_unmatched,
            "binding_fingerprint_sha256": bindings.get("central", ""),
        },
        {
            "observation_id": "collapsed_cycleless_phantom|wide-binding",
            "state": "insufficient" if wide_unmatched else "fail",
            "matched": not wide_unmatched,
            "binding_fingerprint_sha256": bindings.get("wide", ""),
        },
    ]
    return {
        "control_id": "collapsed_cycleless_phantom",
        "observed_state": (
            "insufficient"
            if graph_ok and central_unmatched and wide_unmatched
            else "fail"
        ),
        "observations": observations,
    }


def _derived_blind(
    base: object, *, control_id: str, section: np.ndarray, coherence: np.ndarray
) -> object:
    amplitude = np.linalg.norm(section, axis=1)
    return build_blind_loop_input(
        primary_unit_sha256=hashlib.sha256(control_id.encode("ascii")).hexdigest(),
        estimator_input_fingerprint_sha256=base.estimator_input_fingerprint_sha256,
        field_graph_fingerprint_sha256=base.field_graph_fingerprint_sha256,
        field_estimate_fingerprint_sha256=hashlib.sha256(
            f"{control_id}:field".encode("ascii")
        ).hexdigest(),
        cycle_graph_fingerprint_sha256=base.cycle_graph_fingerprint_sha256,
        cycle_binding_fingerprint_sha256=base.cycle_binding_fingerprint_sha256,
        representative_content_sha256=base.representative_content_sha256,
        ordered_loop_rows=base.ordered_loop_rows,
        section_values=section,
        boundary_amplitude=amplitude,
        boundary_identifiability_score=base.boundary_identifiability_score,
        boundary_coherence=coherence,
    )


def _control_receipts(
    *,
    protocol: Mapping[str, object],
    calibration_matrix: Mapping[str, object],
    confirmation_matrix: Mapping[str, object],
    calibration_supports: Mapping[str, object],
    confirmation_supports: Mapping[str, object],
    calibration_graph_input: GraphInput,
    calibration_oriented_faces: object,
    selected_candidates: Sequence[StructuralCandidate],
    selected_documents: Sequence[object],
    confirmation_structural: Mapping[str, object],
    oracle_threshold: float,
    graph_threshold: float,
    algebraic_tolerance: float,
) -> list[dict[str, object]]:
    controls: list[dict[str, object]] = []
    del (
        calibration_matrix
    )  # Calibration values set thresholds; controls use held-out cells.
    contracts = {
        str(item["control_id"]): item for item in _control_contracts_document()
    }
    confirmation_cells = {
        str(item["cell_id"]): item
        for raw in _sequence(confirmation_matrix["cells"], label="confirmation cells")
        for item in (_mapping(raw, label="confirmation cell"),)
    }
    confirmation_spans = {
        str(item["span_id"]): item
        for raw in _sequence(
            confirmation_matrix["graph_family_spans"], label="confirmation spans"
        )
        for item in (_mapping(raw, label="confirmation span"),)
    }
    confirmation_blinds_by_case = _mapping(
        confirmation_supports["blinds_by_case"],
        label="confirmation blinds by case",
    )
    confirmation_centers_by_case = _mapping(
        confirmation_supports["center_amplitudes_by_case"],
        label="confirmation center amplitudes by case",
    )
    amplitude_floor = float(_loop_policy().amplitude_floor)

    for control_id in (
        "known_positive_connection",
        "zero_holonomy_finite_amplitude_null",
        "radial_amplitude_depression_without_holonomy",
    ):
        required = list(contracts[control_id]["required_cell_ids"])
        values = [confirmation_cells.get(cell_id) for cell_id in required]
        errors = [
            item.get("absolute_error_cycles") if item is not None else None
            for item in values
        ]
        evaluable = len(required) == 18 and all(
            item is not None and item.get("attempt_status") == "evaluable"
            for item in values
        )
        finite = evaluable and all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
            and 0.0 <= float(value)
            for value in errors
        )
        nuisance_diagnostics: dict[str, object] | None = None
        nuisance_finite = True
        nuisance_passes = True
        if control_id == "zero_holonomy_finite_amplitude_null":
            no_core_blinds = _mapping(
                confirmation_blinds_by_case["no_core_null"],
                label="confirmation no-core blinds",
            )
            boundary_values = [
                float(amplitude)
                for cell_id in required
                if (blind := no_core_blinds.get(cell_id)) is not None
                for amplitude in np.asarray(blind.boundary_amplitude).reshape(-1)
            ]
            nuisance_finite = bool(boundary_values) and all(
                math.isfinite(value) and value >= 0.0 for value in boundary_values
            )
            minimum_boundary = min(boundary_values) if nuisance_finite else None
            nuisance_passes = bool(
                nuisance_finite
                and minimum_boundary is not None
                and minimum_boundary > amplitude_floor
            )
            nuisance_diagnostics = {
                "definition": "no_core_finite_loop_boundary_amplitude",
                "amplitude_floor": amplitude_floor,
                "minimum_loop_boundary_amplitude": minimum_boundary,
                "finite": nuisance_finite,
                "passes": nuisance_passes,
            }
        elif control_id == "radial_amplitude_depression_without_holonomy":
            fixed_blinds = _mapping(
                confirmation_blinds_by_case["fixed_null"],
                label="confirmation fixed-null blinds",
            )
            fixed_centers = _mapping(
                confirmation_centers_by_case["fixed_null"],
                label="confirmation fixed-null centers",
            )
            boundary_values = [
                float(amplitude)
                for cell_id in required
                if (blind := fixed_blinds.get(cell_id)) is not None
                for amplitude in np.asarray(blind.boundary_amplitude).reshape(-1)
            ]
            center_values = [
                float(fixed_centers[family])
                for family in FAMILY_ORDER
                if family in fixed_centers
            ]
            nuisance_finite = (
                len(center_values) == 3
                and bool(boundary_values)
                and all(
                    math.isfinite(value) and value >= 0.0
                    for value in (*center_values, *boundary_values)
                )
            )
            maximum_center = max(center_values) if nuisance_finite else None
            minimum_boundary = min(boundary_values) if nuisance_finite else None
            nuisance_passes = bool(
                nuisance_finite
                and maximum_center is not None
                and minimum_boundary is not None
                and maximum_center <= amplitude_floor
                and minimum_boundary > amplitude_floor
            )
            nuisance_diagnostics = {
                "definition": "fixed_null_depressed_center_finite_loop_boundary",
                "amplitude_floor": amplitude_floor,
                "center_amplitude_count": len(center_values),
                "maximum_center_amplitude": maximum_center,
                "minimum_loop_boundary_amplitude": minimum_boundary,
                "finite": nuisance_finite,
                "passes": nuisance_passes,
            }
        passed = (
            finite
            and nuisance_finite
            and nuisance_passes
            and all(float(value) <= oracle_threshold for value in errors)
        )
        raw_state = (
            "insufficient"
            if not finite or not nuisance_finite
            else ("pass" if passed else "fail")
        )
        receipt: dict[str, object] = {
            "control_id": control_id,
            "observed_state": raw_state,
            "required_cell_count": len(required),
            "observed_cell_count": sum(item is not None for item in values),
            "worst_error_cycles": (
                max(float(value) for value in errors) if finite else None
            ),
            "oracle_and_null_threshold_cycles": oracle_threshold,
            "observations": [],
        }
        if nuisance_diagnostics is not None:
            receipt["nuisance_diagnostics"] = nuisance_diagnostics
        controls.append(receipt)

    angle = 0.271
    source = np.eye(2, dtype="<f8")
    target = np.asarray(
        ((math.cos(angle), -math.sin(angle)), (math.sin(angle), math.cos(angle))),
        dtype="<f8",
    )
    connection = procrustes_connection(source, target)
    connection_angle_error = abs(
        math.atan2(connection.rotation[1, 0], connection.rotation[0, 0]) - angle
    )
    connection_residual = connection.residual_frobenius
    representatives = _mapping(
        calibration_supports["representatives"], label="calibration representatives"
    )
    central_blind = representatives["central"]
    row_count = central_blind.section_values.shape[0]
    frames = np.broadcast_to(np.eye(2), (row_count, 2, 2)).copy()
    coordinates = np.asarray(central_blind.section_values)
    angles = 0.11 + 0.017 * np.arange(row_count)
    gauges = np.empty((row_count, 2, 2), dtype="<f8")
    gauges[:, 0, 0] = np.cos(angles)
    gauges[:, 0, 1] = -np.sin(angles)
    gauges[:, 1, 0] = np.sin(angles)
    gauges[:, 1, 1] = np.cos(angles)
    gauge = local_frame_gauge_check(
        local_frames=frames,
        local_coordinates=coordinates,
        gauges=gauges,
        tolerance=algebraic_tolerance,
    )
    reversal = loop_reversal_check(
        section_values=central_blind.section_values,
        loop_rows=np.arange(row_count, dtype="<i8"),
        tolerance=algebraic_tolerance,
    )
    global_rotation = np.asarray(
        ((math.cos(angle), -math.sin(angle)), (math.sin(angle), math.cos(angle))),
        dtype="<f8",
    )
    gauge_base_total = sampled_phase_total(
        central_blind.section_values, np.arange(row_count, dtype="<i8")
    )
    gauge_rotated_total = sampled_phase_total(
        central_blind.section_values @ global_rotation.T,
        np.arange(row_count, dtype="<i8"),
    )
    gauge_phase_delta = abs(gauge_rotated_total - gauge_base_total)
    pure_observations = [
        {
            "observation_id": "pure_so2_gauge|procrustes-connection",
            "state": (
                "pass"
                if connection_angle_error <= algebraic_tolerance
                and connection_residual <= algebraic_tolerance
                else "fail"
            ),
            "angle_error_radians": connection_angle_error,
            "angle_tolerance_radians": algebraic_tolerance,
            "residual_frobenius": connection_residual,
            "residual_tolerance": algebraic_tolerance,
        },
        {
            "observation_id": "pure_so2_gauge|local-frame-gauge",
            "state": (
                "pass"
                if gauge.state is QualificationState.PASS
                and gauge_phase_delta <= algebraic_tolerance
                else "fail"
            ),
            "phase_total_gauge_delta_cycles": gauge_phase_delta,
            "phase_total_tolerance_cycles": algebraic_tolerance,
            "coordinate_law_error": gauge.observed_error,
            "coordinate_law_tolerance": algebraic_tolerance,
            "receipt_sha256": gauge.fingerprint_sha256,
        },
    ]
    controls.append(
        {
            "control_id": "pure_so2_gauge",
            "observed_state": (
                "pass"
                if all(item["state"] == "pass" for item in pure_observations)
                else "fail"
            ),
            "observations": pure_observations,
        }
    )
    controls.append(_rewire_control(selected_candidates))

    amplitude_observations: list[dict[str, object]] = []
    reversal_observations: list[dict[str, object]] = []
    for cycle_class in CYCLE_CLASS_ORDER:
        blind = representatives[cycle_class]
        count = blind.section_values.shape[0]
        amplitudes = np.asarray(blind.boundary_amplitude)
        if np.any(amplitudes <= 0.0):
            amplitude_error = None
            amplitude_state = "insufficient"
            multiset_exact = False
            transform_nonidentity = False
        else:
            shifted_amplitudes = np.roll(amplitudes, 1)
            multiset_exact = np.array_equal(
                np.sort(shifted_amplitudes), np.sort(amplitudes)
            )
            transform_nonidentity = not np.array_equal(shifted_amplitudes, amplitudes)
            unit = blind.section_values / amplitudes[:, None]
            permuted_section = unit * shifted_amplitudes[:, None]
            amplitude_total = sampled_phase_total(
                permuted_section, np.arange(count, dtype="<i8")
            )
            base_total = sampled_phase_total(
                blind.section_values, np.arange(count, dtype="<i8")
            )
            amplitude_error = abs(amplitude_total - base_total)
            amplitude_state = (
                "insufficient"
                if not transform_nonidentity
                else (
                    "pass"
                    if multiset_exact and amplitude_error <= algebraic_tolerance
                    else "fail"
                )
            )
        amplitude_observations.append(
            {
                "observation_id": f"amplitude_label_permutation|{cycle_class}",
                "state": amplitude_state,
                "absolute_error_cycles": amplitude_error,
                "tolerance_cycles": algebraic_tolerance,
                "amplitude_multiset_exact": multiset_exact,
                "transformation_nonidentity": transform_nonidentity,
            }
        )
        check = loop_reversal_check(
            section_values=blind.section_values,
            loop_rows=np.arange(count, dtype="<i8"),
            tolerance=algebraic_tolerance,
        )
        reversal_observations.append(
            {
                "observation_id": f"orientation_reversal|{cycle_class}",
                "state": check.state.value,
                "error_cycles": check.observed_error,
                "tolerance_cycles": algebraic_tolerance,
                "receipt_sha256": check.fingerprint_sha256,
            }
        )
    controls.append(
        {
            "control_id": "amplitude_label_permutation",
            "observed_state": (
                "pass"
                if all(item["state"] == "pass" for item in amplitude_observations)
                else (
                    "fail"
                    if any(item["state"] == "fail" for item in amplitude_observations)
                    else "insufficient"
                )
            ),
            "observations": amplitude_observations,
        }
    )
    controls.append(
        {
            "control_id": "orientation_reversal",
            "observed_state": (
                "pass"
                if all(item["state"] == "pass" for item in reversal_observations)
                else "fail"
            ),
            "observations": reversal_observations,
        }
    )
    density_required_cells = list(
        contracts["density_warp_confirmation"]["required_cell_ids"]
    )
    density_required_spans = list(
        contracts["density_warp_confirmation"]["required_span_ids"]
    )
    density_cell_values = [
        confirmation_cells.get(item) for item in density_required_cells
    ]
    density_span_values = [
        confirmation_spans.get(item) for item in density_required_spans
    ]
    density_cells_evaluable = len(density_required_cells) == 54 and all(
        item is not None and item.get("attempt_status") == "evaluable"
        for item in density_cell_values
    )
    density_cells_finite = density_cells_evaluable and all(
        item is not None
        and isinstance(item.get("absolute_error_cycles"), (int, float))
        and not isinstance(item.get("absolute_error_cycles"), bool)
        and math.isfinite(float(item["absolute_error_cycles"]))
        and float(item["absolute_error_cycles"]) >= 0.0
        for item in density_cell_values
    )
    density_spans_finite = len(density_required_spans) == 6 and all(
        item is not None
        and isinstance(item.get("graph_family_span_cycles"), (int, float))
        and not isinstance(item.get("graph_family_span_cycles"), bool)
        and math.isfinite(float(item["graph_family_span_cycles"]))
        and float(item["graph_family_span_cycles"]) >= 0.0
        for item in density_span_values
    )
    density_cells_ok = density_cells_finite and all(
        float(item["absolute_error_cycles"]) <= oracle_threshold
        for item in density_cell_values
        if item is not None
    )
    density_spans_ok = density_spans_finite and all(
        float(item["graph_family_span_cycles"]) <= graph_threshold
        for item in density_span_values
        if item is not None
    )
    structural_ok = confirmation_structural.get("state") == "pass"
    density_raw_state = (
        "insufficient"
        if not structural_ok or not density_cells_finite or not density_spans_finite
        else ("pass" if density_cells_ok and density_spans_ok else "fail")
    )
    controls.append(
        {
            "control_id": "density_warp_confirmation",
            "observed_state": density_raw_state,
            "confirmation_matrix_sha256": canonical_json_sha256(confirmation_matrix),
            "required_cell_count": len(density_required_cells),
            "required_span_count": len(density_required_spans),
            "observations": [
                {
                    "observation_id": (
                        "density_warp_confirmation|fixed-triplet-structural-support"
                    ),
                    "state": "pass" if structural_ok else "insufficient",
                    "confirmation_structural_sha256": canonical_json_sha256(
                        confirmation_structural
                    ),
                }
            ],
        }
    )
    controls.extend(
        _graph_invariance_controls(calibration_graph_input, selected_documents)
    )
    controls.append(
        _collapsed_cycleless_control(
            calibration_graph_input,
            calibration_oriented_faces,
            protocol,
        )
    )

    confirmation_positive_blinds = _mapping(
        confirmation_blinds_by_case["positive"], label="confirmation positive blinds"
    )
    field_shuffle_observations: list[dict[str, object]] = []
    for cell_id in _required_cell_ids("confirmation", ("positive",)):
        blind = confirmation_positive_blinds.get(cell_id)
        if blind is None:
            field_shuffle_observations.append(
                {
                    "observation_id": f"field_only_shuffle|{cell_id}",
                    "state": "fail",
                    "reason": "required-blind-cell-missing",
                }
            )
            continue
        count = blind.section_values.shape[0]
        base_total = sampled_phase_total(
            blind.section_values, np.arange(count, dtype="<i8")
        )
        shuffled_total = sampled_phase_total(
            blind.section_values[::-1], np.arange(count, dtype="<i8")
        )
        sign_error = abs(shuffled_total + base_total)
        field_shuffle_observations.append(
            {
                "observation_id": f"field_only_shuffle|{cell_id}",
                "state": "pass" if sign_error <= algebraic_tolerance else "fail",
                "base_total_cycles": base_total,
                "shuffled_total_cycles": shuffled_total,
                "sign_reversal_error_cycles": sign_error,
                "tolerance_cycles": algebraic_tolerance,
            }
        )
    controls.append(
        {
            "control_id": "field_only_shuffle",
            "observed_state": (
                "pass"
                if len(field_shuffle_observations) == 18
                and all(item["state"] == "pass" for item in field_shuffle_observations)
                else "fail"
            ),
            "observations": field_shuffle_observations,
        }
    )
    zero_observations: list[dict[str, object]] = []
    low_observations: list[dict[str, object]] = []
    for cycle_class in CYCLE_CLASS_ORDER:
        blind = representatives[cycle_class]
        count = blind.section_values.shape[0]
        zero_blind = _derived_blind(
            blind,
            control_id=f"zero_amplitude:{cycle_class}",
            section=np.zeros_like(blind.section_values),
            coherence=np.asarray(blind.boundary_coherence),
        )
        zero_prediction = estimate_and_seal_loop(zero_blind, _loop_policy())
        zero_exact = (
            zero_prediction.observed_attempt_status is AttemptStatus.INSUFFICIENT
            and tuple(zero_prediction.reason_codes)
            == ("boundary_amplitude_at_or_below_floor",)
        )
        zero_observations.append(
            {
                "observation_id": f"zero_amplitude|{cycle_class}",
                "state": "insufficient" if zero_exact else "fail",
                "reason_codes": list(zero_prediction.reason_codes),
            }
        )
        low_blind = _derived_blind(
            blind,
            control_id=f"low_coherence:{cycle_class}",
            section=np.asarray(blind.section_values),
            coherence=np.zeros(count, dtype="<f8"),
        )
        low_prediction = estimate_and_seal_loop(low_blind, _loop_policy())
        low_exact = (
            low_prediction.observed_attempt_status is AttemptStatus.INSUFFICIENT
            and tuple(low_prediction.reason_codes)
            == ("boundary_coherence_at_or_below_floor",)
        )
        low_observations.append(
            {
                "observation_id": f"low_coherence|{cycle_class}",
                "state": "insufficient" if low_exact else "fail",
                "reason_codes": list(low_prediction.reason_codes),
            }
        )
    controls.append(
        {
            "control_id": "zero_amplitude",
            "observed_state": (
                "insufficient"
                if all(item["state"] == "insufficient" for item in zero_observations)
                else "fail"
            ),
            "observations": zero_observations,
        }
    )
    controls.append(
        {
            "control_id": "low_coherence",
            "observed_state": (
                "insufficient"
                if all(item["state"] == "insufficient" for item in low_observations)
                else "fail"
            ),
            "observations": low_observations,
        }
    )
    nonorientable = nonorientable_control_check(
        edge_determinants=np.asarray((-1.0, 1.0, 1.0), dtype="<f8"),
        cycle_edge_rows=np.asarray((0, 1, 2), dtype="<i8"),
    )
    orientable_companion = nonorientable_control_check(
        edge_determinants=np.asarray((-1.0, -1.0, 1.0), dtype="<f8"),
        cycle_edge_rows=np.asarray((0, 1, 2), dtype="<i8"),
    )
    parity_exact = (
        nonorientable.state is QualificationState.INSUFFICIENT
        and tuple(nonorientable.reason_codes) == ("orientation-reversing-cycle",)
        and orientable_companion.state is QualificationState.FAIL
        and tuple(orientable_companion.reason_codes)
        == ("nonorientable-control-did-not-trigger",)
    )
    controls.append(
        {
            "control_id": "non_orientable_frame",
            "observed_state": "insufficient" if parity_exact else "fail",
            "observations": [
                {
                    "observation_id": "non_orientable_frame|odd-reflection",
                    "state": nonorientable.state.value,
                    "reason_codes": list(nonorientable.reason_codes),
                    "receipt_sha256": nonorientable.fingerprint_sha256,
                },
                {
                    "observation_id": "non_orientable_frame|orientable-companion",
                    "state": orientable_companion.state.value,
                    "reason_codes": list(orientable_companion.reason_codes),
                    "receipt_sha256": orientable_companion.fingerprint_sha256,
                },
            ],
        }
    )
    by_id = {str(item["control_id"]): item for item in controls}
    expected_ids = tuple(EXPECTED_RAW_CONTROL_STATES)
    if set(by_id) != set(expected_ids) or len(controls) != len(expected_ids):
        raise P4RunError("control receipt inventory differs from the frozen matrix")
    normalized: list[dict[str, object]] = []
    for control_id in expected_ids:
        item = dict(by_id[control_id])
        raw_state = str(item.pop("observed_state"))
        expected_raw = EXPECTED_RAW_CONTROL_STATES[control_id]
        contract = contracts[control_id]
        observations = _sequence(
            item.get("observations"), label=f"{control_id} observations"
        )
        observed_ids = [
            str(_mapping(value, label=f"{control_id} observation")["observation_id"])
            for value in observations
        ]
        required_observation_ids = list(contract["required_observation_ids"])
        if observed_ids != required_observation_ids:
            raise P4RunError(f"{control_id} observation manifest differs from freeze")
        normalized.append(
            {
                "control_id": control_id,
                "attempted": True,
                "expected_raw_state": expected_raw,
                "raw_state": raw_state,
                "control_verdict": (
                    "pass"
                    if raw_state == expected_raw
                    else ("insufficient" if raw_state == "insufficient" else "fail")
                ),
                "control_contract_sha256": canonical_json_sha256(contract),
                "required_cell_count": len(contract["required_cell_ids"]),
                "required_cell_ids_sha256": canonical_json_sha256(
                    contract["required_cell_ids"]
                ),
                "required_span_count": len(contract["required_span_ids"]),
                "required_span_ids_sha256": canonical_json_sha256(
                    contract["required_span_ids"]
                ),
                "required_observation_count": len(required_observation_ids),
                "required_observation_ids_sha256": canonical_json_sha256(
                    required_observation_ids
                ),
                **item,
            }
        )
    if sum(int(item["required_observation_count"]) for item in normalized) != 46:
        raise P4RunError("control subobservation inventory is not exactly 46")
    return normalized


def _not_run_controls(reason: str) -> list[dict[str, object]]:
    return [
        {
            "control_id": control_id,
            "attempted": False,
            "expected_raw_state": expected,
            "raw_state": "not_run",
            "control_verdict": "not_run",
            "upstream_reason": reason,
        }
        for control_id, expected in EXPECTED_RAW_CONTROL_STATES.items()
    ]


def _effective_threshold(worst_error: float, *, cap: float) -> tuple[float, bool]:
    threshold = max(1e-8, 1.25 * worst_error)
    return threshold, threshold <= cap


def _nonnegative_finite_scalar(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    scalar = float(value)
    if not math.isfinite(scalar) or scalar < 0.0:
        return None
    return scalar


def _calibration_algebraic_diagnostics(
    representative_blind: object,
) -> dict[str, object]:
    tolerance = 1e-8
    row_count = representative_blind.section_values.shape[0]
    frames = np.broadcast_to(np.eye(2), (row_count, 2, 2)).copy()
    coordinates = np.asarray(representative_blind.section_values)
    angles = 0.11 + 0.017 * np.arange(row_count)
    gauges = np.empty((row_count, 2, 2), dtype="<f8")
    gauges[:, 0, 0] = np.cos(angles)
    gauges[:, 0, 1] = -np.sin(angles)
    gauges[:, 1, 0] = np.sin(angles)
    gauges[:, 1, 1] = np.cos(angles)
    gauge = local_frame_gauge_check(
        local_frames=frames,
        local_coordinates=coordinates,
        gauges=gauges,
        tolerance=tolerance,
    )
    reversal = loop_reversal_check(
        section_values=representative_blind.section_values,
        loop_rows=np.arange(row_count, dtype="<i8"),
        tolerance=tolerance,
    )
    global_angle = 0.271
    global_rotation = np.asarray(
        (
            (math.cos(global_angle), -math.sin(global_angle)),
            (math.sin(global_angle), math.cos(global_angle)),
        ),
        dtype="<f8",
    )
    base_total = sampled_phase_total(
        representative_blind.section_values, np.arange(row_count, dtype="<i8")
    )
    rotated_total = sampled_phase_total(
        representative_blind.section_values @ global_rotation.T,
        np.arange(row_count, dtype="<i8"),
    )
    phase_gauge_delta = abs(rotated_total - base_total)
    return {
        "pure_so2_gauge": {
            "state": (
                "pass"
                if gauge.state is QualificationState.PASS
                and phase_gauge_delta <= tolerance
                else "fail"
            ),
            "error_cycles": phase_gauge_delta,
            "coordinate_law_error": gauge.observed_error,
            "coordinate_law_tolerance": tolerance,
            "receipt_sha256": gauge.fingerprint_sha256,
        },
        "orientation_reversal": {
            "state": reversal.state.value,
            "error_cycles": reversal.observed_error,
            "receipt_sha256": reversal.fingerprint_sha256,
        },
    }


@dataclass(frozen=True, slots=True)
class _CalibrationSelectorRecomputation:
    projection: dict[str, object]
    phantom: object
    inputs: object
    graph_input: GraphInput


def _recompute_calibration_selector(
    protocol: Mapping[str, object],
) -> _CalibrationSelectorRecomputation:
    """Recreate the frozen graph-only winner from calibration inputs only."""

    substrates = _mapping(protocol["substrates"], label="substrates")
    calibration_spec = _phantom_spec(
        _mapping(substrates["calibration"], label="calibration")
    )
    calibration_phantom = CartesianFourierDomainGenerator().generate(calibration_spec)
    calibration_inputs = calibration_phantom.positive.estimator_inputs
    calibration_graph_input = GraphInput(
        primary_unit_id="p4-v0-2-calibration-selector",
        vertex_ids=calibration_inputs.row_ids,
        states=calibration_inputs.states,
    )
    selection = select_structural_triplet(
        calibration_graph_input,
        calibration_inputs.oriented_faces,
        protocol,
    )
    return _CalibrationSelectorRecomputation(
        projection=selection,
        phantom=calibration_phantom,
        inputs=calibration_inputs,
        graph_input=calibration_graph_input,
    )


def _require_exact_recomputed_calibration_selector(
    persisted: object,
    *,
    protocol: Mapping[str, object],
) -> None:
    """Reject any semantically plausible selector other than the frozen winner."""

    recomputed = _recompute_calibration_selector(protocol).projection
    _constant(
        persisted,
        recomputed,
        label="persisted calibration selector frozen recomputation",
    )


def execute_calibration(
    protocol: Mapping[str, object],
    *,
    seal_graph_selection: object,
    seal_threshold_decision: object,
    mark_confirmation_access: object,
) -> dict[str, object]:
    """Execute the frozen official matrix; caller must first validate launch."""

    substrates = _mapping(protocol["substrates"], label="substrates")
    recomputed_selector = _recompute_calibration_selector(protocol)
    calibration_phantom = recomputed_selector.phantom
    calibration_inputs = recomputed_selector.inputs
    calibration_graph_input = recomputed_selector.graph_input
    selection = recomputed_selector.projection
    if not callable(seal_graph_selection):
        raise P4RunError("graph-selection seal callback is not callable")
    graph_selection_seal_sha256 = seal_graph_selection(
        {
            "schema_version": GRAPH_SELECTION_SEAL_SCHEMA_VERSION,
            "experiment_id": EXPERIMENT_ID,
            "calibration_selector": selection,
            "field_read_before_seal": False,
            "readout_before_seal": False,
            "confirmation_accessed_before_seal": False,
        }
    )
    if selection["state"] != "pass":
        return {
            "terminal_state": "insufficient",
            "reason": "no-distinct-three-family-scale-triplet",
            "calibration_selector": selection,
            "graph_selection_seal_sha256": graph_selection_seal_sha256,
            "threshold_seal_sha256": None,
            "confirmation_access_seal_sha256": None,
            "calibration_matrix": None,
            "calibration_algebraic_diagnostics": None,
            "calibration_scalar_inventory": None,
            "effective_thresholds": None,
            "confirmation_structural": None,
            "confirmation_matrix": None,
            "confirmation_accessed": False,
            "graph_selection_sealed": True,
            "threshold_decision_sealed": False,
            "controls": _not_run_controls("no-distinct-three-family-scale-triplet"),
        }
    selected_documents = _sequence(selection["selected"], label="selected")
    calibration_structural, selected_calibration_candidates = assess_fixed_triplet(
        calibration_graph_input,
        calibration_inputs.oriented_faces,
        protocol,
        selected_documents,
    )
    if calibration_structural["state"] != "pass":
        raise P4RunError("sealed calibration triplet failed its own fixed assessment")

    calibration_matrix, calibration_supports = _matrix_readouts(
        role="calibration",
        phantom=calibration_phantom,
        selected=selected_documents,
        protocol=protocol,
    )
    calibration_representatives = _mapping(
        calibration_supports["representatives"],
        label="calibration representatives",
    )
    algebraic = _calibration_algebraic_diagnostics(
        calibration_representatives["central"]
    )
    calibration_cells = _sequence(
        calibration_matrix["cells"], label="calibration cells"
    )
    raw_errors = [
        _mapping(item, label="calibration cell").get("absolute_error_cycles")
        for item in calibration_cells
    ]
    raw_spans = [
        _mapping(item, label="span").get("graph_family_span_cycles")
        for item in _sequence(calibration_matrix["graph_family_spans"], label="spans")
    ]
    raw_algebraic = [
        _mapping(value, label="algebraic diagnostic").get("error_cycles")
        for value in algebraic.values()
    ]
    converted_errors = [_nonnegative_finite_scalar(value) for value in raw_errors]
    converted_spans = [_nonnegative_finite_scalar(value) for value in raw_spans]
    converted_algebraic = [_nonnegative_finite_scalar(value) for value in raw_algebraic]
    error_scalars = [value for value in converted_errors if value is not None]
    calibration_spans = [value for value in converted_spans if value is not None]
    algebraic_scalars = [value for value in converted_algebraic if value is not None]
    scalar_inventory = {
        "absolute_oracle_or_null_error_cycles": len(error_scalars),
        "graph_family_span_cycles": len(calibration_spans),
        "pure_so2_gauge_error_cycles": (1 if converted_algebraic[0] is not None else 0),
        "orientation_reversal_error_cycles": (
            1 if converted_algebraic[1] is not None else 0
        ),
        "total": len(error_scalars) + len(calibration_spans) + len(algebraic_scalars),
    }
    finite_complete = (
        len(raw_errors) == 54
        and len(error_scalars) == 54
        and len(raw_spans) == 6
        and len(calibration_spans) == 6
        and len(raw_algebraic) == 2
        and len(algebraic_scalars) == 2
    )
    if not finite_complete:
        if not callable(seal_threshold_decision):
            raise P4RunError("threshold-decision seal callback is not callable")
        threshold_seal_sha256 = seal_threshold_decision(
            {
                "schema_version": THRESHOLD_SEAL_SCHEMA_VERSION,
                "experiment_id": EXPERIMENT_ID,
                "graph_selection_seal_sha256": graph_selection_seal_sha256,
                "decision_state": "insufficient_calibration_resolution",
                "calibration_scalar_inventory": scalar_inventory,
                "oracle_and_null_selection_worst_error_cycles": None,
                "graph_family_span_selection_worst_error_cycles": None,
                "empty_or_nonfinite_detected": True,
                "confirmation_accessed_before_seal": False,
            }
        )
        return {
            "terminal_state": "insufficient",
            "reason": "insufficient_calibration_resolution",
            "calibration_selector": selection,
            "graph_selection_seal_sha256": graph_selection_seal_sha256,
            "threshold_seal_sha256": threshold_seal_sha256,
            "confirmation_access_seal_sha256": None,
            "calibration_matrix": calibration_matrix,
            "calibration_algebraic_diagnostics": algebraic,
            "calibration_scalar_inventory": scalar_inventory,
            "effective_thresholds": None,
            "confirmation_structural": None,
            "confirmation_matrix": None,
            "confirmation_accessed": False,
            "graph_selection_sealed": True,
            "threshold_decision_sealed": True,
            "controls": _not_run_controls("insufficient-calibration-resolution"),
        }
    oracle_selection_worst = max(error_scalars)
    graph_selection_worst = max(calibration_spans)
    oracle_threshold, oracle_within_cap = _effective_threshold(
        oracle_selection_worst, cap=0.05
    )
    graph_threshold, graph_within_cap = _effective_threshold(
        graph_selection_worst, cap=0.1
    )
    algebraic_resolved = all(
        _mapping(value, label="algebraic diagnostic")["state"] == "pass"
        and float(_mapping(value, label="algebraic diagnostic")["error_cycles"]) <= 1e-8
        for value in algebraic.values()
    )
    if not oracle_within_cap or not graph_within_cap or not algebraic_resolved:
        reason = (
            "orientation-or-reverse-consistency-unresolved"
            if not algebraic_resolved
            else "insufficient_calibration_resolution"
        )
        if not callable(seal_threshold_decision):
            raise P4RunError("threshold-decision seal callback is not callable")
        threshold_seal_sha256 = seal_threshold_decision(
            {
                "schema_version": THRESHOLD_SEAL_SCHEMA_VERSION,
                "experiment_id": EXPERIMENT_ID,
                "graph_selection_seal_sha256": graph_selection_seal_sha256,
                "decision_state": reason.replace("-", "_"),
                "calibration_scalar_inventory": scalar_inventory,
                "oracle_and_null_selection_worst_error_cycles": (
                    oracle_selection_worst
                ),
                "graph_family_span_selection_worst_error_cycles": (
                    graph_selection_worst
                ),
                "oracle_and_null_cycles": oracle_threshold,
                "oracle_and_null_cap_cycles": 0.05,
                "graph_family_span_cycles": graph_threshold,
                "graph_family_span_cap_cycles": 0.1,
                "algebraic_gauge_and_reversal_error_cycles": 1e-8,
                "no_clamping_applied": True,
                "confirmation_accessed_before_seal": False,
            }
        )
        return {
            "terminal_state": "insufficient",
            "reason": reason,
            "calibration_selector": selection,
            "graph_selection_seal_sha256": graph_selection_seal_sha256,
            "threshold_seal_sha256": threshold_seal_sha256,
            "confirmation_access_seal_sha256": None,
            "calibration_matrix": calibration_matrix,
            "calibration_algebraic_diagnostics": algebraic,
            "calibration_scalar_inventory": scalar_inventory,
            "effective_thresholds": {
                "oracle_and_null_selection_worst_error_cycles": (
                    oracle_selection_worst
                ),
                "graph_family_span_selection_worst_error_cycles": (
                    graph_selection_worst
                ),
                "oracle_and_null_cycles": oracle_threshold,
                "graph_family_span_cycles": graph_threshold,
            },
            "confirmation_structural": None,
            "confirmation_matrix": None,
            "confirmation_accessed": False,
            "graph_selection_sealed": True,
            "threshold_decision_sealed": True,
            "controls": _not_run_controls(reason.replace("_", "-")),
        }

    if not callable(seal_threshold_decision):
        raise P4RunError("threshold-decision seal callback is not callable")
    threshold_seal_document = {
        "schema_version": THRESHOLD_SEAL_SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "graph_selection_seal_sha256": graph_selection_seal_sha256,
        "decision_state": "pass",
        "calibration_scalar_inventory": scalar_inventory,
        "oracle_and_null_selection_worst_error_cycles": oracle_selection_worst,
        "oracle_and_null_selection_worst_metric": (
            "maximum-over-54-declared-finite-absolute-errors"
        ),
        "graph_family_span_selection_worst_error_cycles": graph_selection_worst,
        "graph_family_span_selection_worst_metric": (
            "maximum-over-6-declared-finite-spans"
        ),
        "oracle_and_null_cycles": oracle_threshold,
        "oracle_and_null_cap_cycles": 0.05,
        "graph_family_span_cycles": graph_threshold,
        "graph_family_span_cap_cycles": 0.1,
        "algebraic_gauge_and_reversal_error_cycles": 1e-8,
        "no_clamping_applied": True,
        "confirmation_accessed_before_seal": False,
    }
    threshold_seal_sha256 = seal_threshold_decision(threshold_seal_document)

    if not callable(mark_confirmation_access):
        raise P4RunError("confirmation access observer is not callable")
    confirmation_access_seal_sha256 = mark_confirmation_access()
    _require_sha256(
        confirmation_access_seal_sha256,
        label="confirmation-access seal digest",
    )
    # The exact confirmation substrate is first instantiated only after both
    # durable decisions above exist.
    confirmation_spec = _phantom_spec(
        _mapping(substrates["confirmation"], label="confirmation")
    )
    confirmation_phantom = CartesianFourierDomainGenerator().generate(confirmation_spec)
    confirmation_inputs = confirmation_phantom.positive.estimator_inputs
    confirmation_graph_input = GraphInput(
        primary_unit_id="p4-v0-2-confirmation-fixed-triplet",
        vertex_ids=confirmation_inputs.row_ids,
        states=confirmation_inputs.states,
    )
    confirmation_structural, _selected_confirmation = assess_fixed_triplet(
        confirmation_graph_input,
        confirmation_inputs.oriented_faces,
        protocol,
        selected_documents,
    )
    if confirmation_structural["state"] != "pass":
        return {
            "terminal_state": "insufficient",
            "reason": "held-out-confirmation-structural-gate",
            "calibration_selector": selection,
            "graph_selection_seal_sha256": graph_selection_seal_sha256,
            "threshold_seal_sha256": threshold_seal_sha256,
            "confirmation_access_seal_sha256": confirmation_access_seal_sha256,
            "calibration_matrix": calibration_matrix,
            "calibration_algebraic_diagnostics": algebraic,
            "calibration_scalar_inventory": scalar_inventory,
            "effective_thresholds": {
                "oracle_and_null_selection_worst_error_cycles": (
                    oracle_selection_worst
                ),
                "graph_family_span_selection_worst_error_cycles": (
                    graph_selection_worst
                ),
                "oracle_and_null_cycles": oracle_threshold,
                "graph_family_span_cycles": graph_threshold,
                "algebraic_gauge_and_reversal_error_cycles": 1e-8,
            },
            "confirmation_structural": confirmation_structural,
            "confirmation_matrix": None,
            "confirmation_accessed": True,
            "graph_selection_sealed": True,
            "threshold_decision_sealed": True,
            "controls": _not_run_controls("held-out-confirmation-structural-gate"),
        }

    confirmation_matrix, confirmation_supports = _matrix_readouts(
        role="confirmation",
        phantom=confirmation_phantom,
        selected=selected_documents,
        protocol=protocol,
    )
    controls = _control_receipts(
        protocol=protocol,
        calibration_matrix=calibration_matrix,
        confirmation_matrix=confirmation_matrix,
        calibration_supports=calibration_supports,
        confirmation_supports=confirmation_supports,
        calibration_graph_input=calibration_graph_input,
        calibration_oriented_faces=calibration_inputs.oriented_faces,
        selected_candidates=selected_calibration_candidates,
        selected_documents=selected_documents,
        confirmation_structural=confirmation_structural,
        oracle_threshold=oracle_threshold,
        graph_threshold=graph_threshold,
        algebraic_tolerance=1e-8,
    )

    confirmation_cells = _sequence(
        confirmation_matrix["cells"], label="confirmation cells"
    )
    oracle_ok = all(
        (value := _nonnegative_finite_scalar(item["absolute_error_cycles"])) is not None
        and value <= oracle_threshold
        for item in (
            _mapping(raw, label="confirmation cell") for raw in confirmation_cells
        )
    )
    span_ok = all(
        (value := _nonnegative_finite_scalar(item["graph_family_span_cycles"]))
        is not None
        and value <= graph_threshold
        for item in (
            _mapping(raw, label="confirmation span")
            for raw in _sequence(
                confirmation_matrix["graph_family_spans"], label="spans"
            )
        )
    )
    terminal_state, reason = _fold_attempted_controls(
        controls, oracle_ok=oracle_ok, span_ok=span_ok
    )
    return {
        "terminal_state": terminal_state,
        "reason": reason,
        "calibration_selector": selection,
        "graph_selection_seal_sha256": graph_selection_seal_sha256,
        "threshold_seal_sha256": threshold_seal_sha256,
        "confirmation_access_seal_sha256": confirmation_access_seal_sha256,
        "confirmation_structural": confirmation_structural,
        "effective_thresholds": {
            "oracle_and_null_selection_worst_error_cycles": (oracle_selection_worst),
            "graph_family_span_selection_worst_error_cycles": (graph_selection_worst),
            "oracle_and_null_cycles": oracle_threshold,
            "graph_family_span_cycles": graph_threshold,
            "algebraic_gauge_and_reversal_error_cycles": 1e-8,
        },
        "calibration_matrix": calibration_matrix,
        "calibration_algebraic_diagnostics": algebraic,
        "calibration_scalar_inventory": scalar_inventory,
        "confirmation_matrix": confirmation_matrix,
        "controls": controls,
        "confirmation_accessed": True,
        "graph_selection_sealed": True,
        "threshold_decision_sealed": True,
    }


def _tracked_head_bytes(repo_root: Path, path: Path) -> bytes:
    return _tracked_commit_bytes(repo_root, "HEAD", path)


def _tracked_commit_bytes(repo_root: Path, commit: str, path: Path) -> bytes:
    completed = _git_completed(repo_root, "show", f"{commit}:{path.as_posix()}")
    if completed.returncode != 0:
        raise P4ProtocolError(f"{path} is not tracked at {commit}")
    return completed.stdout


def _require_clean_worktree(repo_root: Path) -> None:
    output = _git_bytes(
        repo_root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    )
    if _split_nul(output, label="Git status"):
        raise P4ProtocolError("P4 lifecycle requires an exactly clean worktree")


def _require_clean_except_projections(repo_root: Path) -> None:
    output = _git_bytes(
        repo_root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    )
    allowed = {
        f"?? {REPOSITORY_ATTEMPT.as_posix()}",
        f"?? {REPOSITORY_TERMINAL.as_posix()}",
        f"?? {_projection_temp_path(REPOSITORY_ATTEMPT).as_posix()}",
        f"?? {_projection_temp_path(REPOSITORY_TERMINAL).as_posix()}",
    }
    unexpected = [
        line
        for line in _split_nul(output, label="Git projection status")
        if line not in allowed
    ]
    if unexpected:
        raise P4ProtocolError(
            "projection repair permits only the two untracked repository projections"
        )


def _source_paths(protocol: Mapping[str, object]) -> tuple[Path, ...]:
    bindings = _mapping(protocol["source_bindings"], label="source_bindings")
    runner = _mapping(bindings["runner"], label="runner")
    paths = [
        Path(str(runner["path"])),
        REPOSITORY_PROTOCOL,
        REPOSITORY_HYPOTHESES,
        PREDECESSOR_PROTOCOL,
        PREDECESSOR_RUNNER,
        PREDECESSOR_LAUNCH,
        PREDECESSOR_ATTEMPT,
        PREDECESSOR_TERMINAL,
    ]
    paths.extend(Path(path) for path in _runtime_source_bindings(protocol))
    return tuple(dict.fromkeys(paths))


def _read_stable_regular_file(
    path: Path,
    *,
    label: str,
    require_nlink_one: bool,
) -> bytes:
    """Read one regular file through a held no-follow descriptor."""

    try:
        lexical = path.absolute()
        resolved = path.resolve(strict=True)
        if lexical != resolved:
            raise P4ProtocolError(f"{label} must not traverse a symlink")
        descriptor = os.open(
            lexical,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        )
    except OSError as error:
        raise P4ProtocolError(f"cannot open {label}") from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or (
            require_nlink_one and before.st_nlink != 1
        ):
            raise P4ProtocolError(
                f"{label} must be a regular"
                + (" nlink=1" if require_nlink_one else "")
                + " file"
            )
        chunks: list[bytes] = []
        while True:
            block = os.read(descriptor, 65_536)
            if not block:
                break
            chunks.append(block)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        raise P4ProtocolError(f"{label} changed while being read")
    source = b"".join(chunks)
    if len(source) != before.st_size:
        raise P4ProtocolError(f"{label} size changed while being read")
    return source


def _runtime_source_bindings(
    protocol: Mapping[str, object],
) -> dict[str, str]:
    bindings = _mapping(protocol["source_bindings"], label="source bindings")
    result: dict[str, str] = {}
    for index, raw in enumerate(
        _sequence(bindings["runtime_files"], label="runtime files")
    ):
        item = _mapping(raw, label=f"runtime file {index}")
        path = item.get("path")
        digest = item.get("sha256")
        if type(path) is not str:
            raise P4ProtocolError("runtime file path must be a string")
        candidate = Path(path)
        if (
            not path
            or candidate.is_absolute()
            or candidate.as_posix() != path
            or any(part in {"", ".", ".."} for part in candidate.parts)
            or not path.startswith("src/spirallens/")
            or candidate.suffix != ".py"
        ):
            raise P4ProtocolError(
                f"runtime file path is not canonical worktree source: {path!r}"
            )
        _require_sha256(digest, label=f"runtime file {path}")
        if path in result:
            raise P4ProtocolError(f"runtime file binding is duplicated: {path}")
        result[path] = str(digest)
    return result


def _loaded_spirallens_source_manifest(
    repo_root: Path,
    protocol: Mapping[str, object],
    *,
    modules: Mapping[str, object] | None = None,
) -> list[dict[str, object]]:
    """Bind every loaded ``spirallens`` module to one frozen ``.py`` source."""

    root = repo_root.resolve()
    source_root = (root / "src" / "spirallens").resolve()
    declared = _runtime_source_bindings(protocol)
    namespace = sys.modules if modules is None else modules
    records: list[dict[str, object]] = []
    for module_name in sorted(namespace):
        if module_name != "spirallens" and not module_name.startswith("spirallens."):
            continue
        module = namespace[module_name]
        origin = getattr(getattr(module, "__spec__", None), "origin", None)
        module_file = getattr(module, "__file__", None)
        if not isinstance(origin, str) or not isinstance(module_file, str):
            raise P4ProtocolError(
                f"loaded {module_name} lacks exact __spec__.origin and __file__"
            )
        origin_path = Path(origin)
        file_path = Path(module_file)
        if origin_path.suffix != ".py" or file_path.suffix != ".py":
            raise P4ProtocolError(
                f"loaded {module_name} did not originate from frozen .py source"
            )
        try:
            if not origin_path.is_absolute() or not file_path.is_absolute():
                raise ValueError("module paths are not absolute")
            resolved = origin_path.resolve(strict=True)
            file_resolved = file_path.resolve(strict=True)
            resolved.relative_to(source_root)
            relative = resolved.relative_to(root).as_posix()
        except (OSError, ValueError) as error:
            raise P4ProtocolError(
                f"loaded {module_name} escaped the exact worktree source"
            ) from error
        if origin_path.absolute() != resolved or file_path.absolute() != file_resolved:
            raise P4ProtocolError(f"loaded {module_name} traversed a symlink")
        origin_metadata = os.stat(origin_path, follow_symlinks=False)
        file_metadata = os.stat(file_path, follow_symlinks=False)
        if resolved != file_resolved or (
            origin_metadata.st_dev,
            origin_metadata.st_ino,
        ) != (file_metadata.st_dev, file_metadata.st_ino):
            raise P4ProtocolError(
                f"loaded {module_name} __spec__.origin and __file__ differ"
            )
        if relative not in declared:
            raise P4ProtocolError(
                f"loaded {module_name} source is absent from protocol runtime_files"
            )
        source = _read_stable_regular_file(
            resolved,
            label=f"loaded source {module_name}",
            require_nlink_one=True,
        )
        digest = _sha256_bytes(source)
        _constant(digest, declared[relative], label=f"loaded {module_name} digest")
        records.append({"module": module_name, "path": relative, "sha256": digest})
    if modules is None and not any(item["module"] == "spirallens" for item in records):
        raise P4ProtocolError("spirallens root module is not loaded")
    loaded_paths = [str(item["path"]) for item in records]
    if len(loaded_paths) != len(set(loaded_paths)) or set(loaded_paths) != set(
        declared
    ):
        raise P4ProtocolError(
            "loaded spirallens source set differs from protocol runtime_files"
        )
    return records


def _python_bytecode_cache_prefix(repo_root: Path) -> Path:
    return (repo_root.resolve().parent / PYTHON_BYTECODE_CACHE_NAME).absolute()


def _require_python_bytecode_cache_absent(repo_root: Path) -> Path:
    prefix = _python_bytecode_cache_prefix(repo_root)
    if not _entry_absent(prefix):
        raise P4ProtocolError("dedicated Python bytecode cache prefix is not absent")
    return prefix


def _source_closure_snapshot(
    repo_root: Path,
    protocol: Mapping[str, object],
) -> dict[str, object]:
    """Bind sources, Git, and Python-cache absence without model/cache access."""

    root = repo_root.resolve()
    source_records: list[dict[str, object]] = []
    for relative in _source_paths(protocol):
        source = _read_stable_regular_file(
            root / relative,
            label=f"bound source {relative}",
            require_nlink_one=True,
        )
        source_records.append(
            {
                "path": relative.as_posix(),
                "sha256": _sha256_bytes(source),
            }
        )
    git_source = _read_stable_regular_file(
        GIT_BINARY,
        label="Git binary",
        require_nlink_one=False,
    )
    pycache_prefix = _require_python_bytecode_cache_absent(root)
    loaded = _loaded_spirallens_source_manifest(root, protocol)
    return {
        "bound_sources": source_records,
        "bound_sources_sha256": canonical_json_sha256(source_records),
        "loaded_spirallens_sources": loaded,
        "loaded_spirallens_sources_sha256": canonical_json_sha256(loaded),
        "git_binary": {
            "path": str(GIT_BINARY),
            "sha256": _sha256_bytes(git_source),
        },
        "git_environment": _git_environment(),
        "git_argv_prefix": list(GIT_ARGV_PREFIX),
        "python_bytecode_cache_prefix": str(pycache_prefix),
        "python_bytecode_cache_prefix_absent": True,
    }


def _expected_python_process_observation(
    repo_root: Path,
    *,
    mode: str,
) -> dict[str, object]:
    if repo_root.resolve() != _BOOTSTRAP_REPOSITORY:
        raise P4ProtocolError("Python process expectation repository differs")
    return _bootstrap_expected_python_process_observation(mode)


def _validated_current_python_process(
    repo_root: Path,
    *,
    mode: str,
) -> dict[str, object]:
    if repo_root.resolve() != _BOOTSTRAP_REPOSITORY:
        raise P4ProtocolError("Python process guard repository differs from bootstrap")
    try:
        observed = _bootstrap_validate_python_process(mode)
    except RuntimeError as error:
        raise P4ProtocolError(str(error)) from error
    _constant(
        observed,
        _expected_python_process_observation(repo_root, mode=mode),
        label=f"{mode} Python process observation",
    )
    return observed


def _runtime_binding(
    repo_root: Path,
    protocol: Mapping[str, object],
    *,
    preparation_observation: Mapping[str, object] | None = None,
) -> dict[str, object]:
    executable = Path(sys.executable).resolve()
    closure = _source_closure_snapshot(repo_root, protocol)
    expected_preparation = _expected_python_process_observation(
        repo_root, mode="--prepare-launch"
    )
    preparation = (
        dict(expected_preparation)
        if preparation_observation is None
        else dict(preparation_observation)
    )
    _constant(
        preparation,
        expected_preparation,
        label="prepare-launch Python process observation",
    )
    expected_run = _expected_python_process_observation(repo_root, mode="--run")
    return {
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "python_executable": str(executable),
        "python_executable_sha256": _sha256_file(executable),
        "python_logical_executable": preparation["logical_executable"],
        "python_resolved_base_executable": preparation["logical_executable_resolved"],
        "python_resolved_base_executable_sha256": preparation["base_executable_sha256"],
        "python_physical_launcher_argv0": preparation["effective_orig_argv0"],
        "python_physical_launcher_sha256": preparation["physical_launcher_sha256"],
        "numpy_version": np.__version__,
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
        "repository_root": str(repo_root.resolve()),
        "spirallens_import_root": str(
            (repo_root.resolve() / "src" / "spirallens").resolve()
        ),
        "isolated_python": preparation["isolated"] == 1,
        "bytecode_writes_disabled": (
            preparation["dont_write_bytecode_flag"] == 1
            and preparation["dont_write_bytecode_runtime"] is True
        ),
        "dedicated_pycache_prefix_enabled": (
            preparation["pycache_prefix"]
            == str(_python_bytecode_cache_prefix(repo_root))
        ),
        "python_bytecode_cache_accessed": not bool(
            preparation["pycache_prefix_lstat_absent"]
        ),
        "python_bytecode_cache_claim_scope": (
            "dedicated-prefix-lstat-absence-under-isolated-no-write-process"
        ),
        "prepare_python_process_observed": preparation,
        "expected_run_python_process": expected_run,
        "source_closure": closure,
        "source_closure_sha256": canonical_json_sha256(closure),
    }


def _write_exclusive(path: Path, source: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o444)
    try:
        view = memoryview(source)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("exclusive write made no progress")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _projection_temp_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.p4-projection.staging")


def _native_file_no_replace(
    parent_fd: int,
    source_name: str,
    target_name: str,
) -> int | None:
    """Rename one same-directory file without replacement; return errno on failure."""

    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        function = getattr(libc, "renameatx_np", None)
        flag = 0x00000004
    elif sys.platform.startswith("linux"):
        function = getattr(libc, "renameat2", None)
        flag = 0x00000001
    else:
        function = None
        flag = 0
    if function is None:
        raise P4PersistenceError("native file no-replace promotion is unavailable")
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
        parent_fd,
        os.fsencode(source_name),
        parent_fd,
        os.fsencode(target_name),
        flag,
    )
    return None if result == 0 else (ctypes.get_errno() or errno.EIO)


def _read_projection_candidate(
    path: Path, *, label: str
) -> tuple[bytes, os.stat_result]:
    try:
        metadata = os.lstat(path)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_size > CANONICAL_BYTE_LIMIT
        ):
            raise P4ProtocolError(f"{label} must be a bounded regular nlink=1 file")
        source = path.read_bytes()
        after = os.lstat(path)
    except OSError as error:
        raise P4PersistenceError(f"cannot read {label}") from error
    if (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        raise P4PersistenceError(f"{label} changed while being read")
    return source, metadata


def _publish_repository_projection(path: Path, source: bytes) -> str:
    """Atomically publish or resume one exact repository projection.

    The deterministic owned temporary may contain only an exact prefix of the
    intended canonical bytes.  That makes an interrupted sequential write
    resumable without truncation or replacement.  A different final or temp is
    rejected without mutation.
    """

    if len(source) > CANONICAL_BYTE_LIMIT:
        raise P4ProtocolError("repository projection exceeds the byte limit")
    try:
        parsed = parse_canonical_json(source, label="repository projection source")
        if canonical_json_bytes(parsed) != source:
            raise ValueError("projection source does not round-trip")
    except ValueError as error:
        raise P4ProtocolError(
            "repository projection source is not canonical"
        ) from error
    parent = path.parent
    temporary = _projection_temp_path(path)
    parent.mkdir(parents=True, exist_ok=True)
    parent_meta = os.lstat(parent)
    if not stat.S_ISDIR(parent_meta.st_mode):
        raise P4ProtocolError("repository projection parent must be a real directory")
    parent_fd = os.open(
        parent,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        held_parent = os.fstat(parent_fd)
        if (held_parent.st_dev, held_parent.st_ino) != (
            parent_meta.st_dev,
            parent_meta.st_ino,
        ):
            raise P4PersistenceError("repository projection parent identity changed")
        if not _entry_absent(path):
            existing, _metadata = _read_projection_candidate(
                path, label="repository projection target"
            )
            if existing != source:
                raise P4ProtocolError("existing repository projection differs")
            if not _entry_absent(temporary):
                staged, staged_meta = _read_projection_candidate(
                    temporary, label="stale repository projection temp"
                )
                if not source.startswith(staged) or staged_meta.st_uid != os.geteuid():
                    raise P4ProtocolError(
                        "stale repository projection temp is not owned prefix"
                    )
                os.unlink(temporary.name, dir_fd=parent_fd)
                os.fsync(parent_fd)
            return "already_exact"

        created = False
        if _entry_absent(temporary):
            flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(temporary.name, flags, 0o600, dir_fd=parent_fd)
            created = True
        else:
            staged, staged_meta = _read_projection_candidate(
                temporary, label="repository projection temp"
            )
            if staged_meta.st_uid != os.geteuid() or not source.startswith(staged):
                raise P4ProtocolError(
                    "repository projection temp is not an owned exact prefix"
                )
            mode = stat.S_IMODE(staged_meta.st_mode)
            if len(staged) < len(source) and mode != 0o600:
                raise P4ProtocolError(
                    "partial repository projection temp is not writable-owned"
                )
            descriptor = os.open(
                temporary.name,
                (os.O_RDWR if len(staged) < len(source) else os.O_RDONLY)
                | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=parent_fd,
            )
        try:
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_nlink != 1
                or metadata.st_uid != os.geteuid()
            ):
                raise P4ProtocolError("repository projection temp identity is invalid")
            prefix_size = metadata.st_size
            if prefix_size > len(source):
                raise P4ProtocolError(
                    "repository projection temp exceeds intended bytes"
                )
            if prefix_size < len(source):
                os.lseek(descriptor, prefix_size, os.SEEK_SET)
                view = memoryview(source)[prefix_size:]
                while view:
                    written = os.write(descriptor, view)
                    if written <= 0:
                        raise P4PersistenceError(
                            "repository projection temp write stalled"
                        )
                    view = view[written:]
                os.fsync(descriptor)
                os.fchmod(descriptor, 0o444)
                os.fsync(descriptor)
            elif created or stat.S_IMODE(metadata.st_mode) != 0o444:
                os.fchmod(descriptor, 0o444)
                os.fsync(descriptor)
        finally:
            os.close(descriptor)
        staged, _staged_meta = _read_projection_candidate(
            temporary, label="completed repository projection temp"
        )
        if staged != source:
            raise P4PersistenceError("completed repository projection temp differs")
        os.fsync(parent_fd)
        observed_errno = _native_file_no_replace(parent_fd, temporary.name, path.name)
        if observed_errno is not None:
            if observed_errno not in {errno.EEXIST, errno.ENOTEMPTY}:
                raise P4PersistenceError(
                    f"repository projection no-replace failed with errno {observed_errno}"
                )
            existing, _metadata = _read_projection_candidate(
                path, label="raced repository projection target"
            )
            if existing != source:
                raise P4ProtocolError("raced repository projection target differs")
            os.unlink(temporary.name, dir_fd=parent_fd)
        os.fsync(parent_fd)
        final_source, _final_metadata = _read_projection_candidate(
            path, label="repository projection target"
        )
        if final_source != source:
            raise P4PersistenceError(
                "repository projection target differs after publish"
            )
        return "published"
    except (P4ProtocolError, P4PersistenceError):
        raise
    except OSError as error:
        raise P4PersistenceError("repository projection persistence failed") from error
    finally:
        os.close(parent_fd)


def _require_regular_head_file(repo_root: Path, path: Path) -> None:
    live = repo_root / path
    source = _read_stable_regular_file(
        live,
        label=f"bound source {path}",
        require_nlink_one=True,
    )
    if _tracked_head_bytes(repo_root, path) != source:
        raise P4ProtocolError(f"working bytes differ from HEAD: {path}")


def _require_import_root(repo_root: Path) -> None:
    expected = (repo_root / "src" / "spirallens").resolve()
    observed = Path(spirallens.__file__).resolve()
    try:
        observed.relative_to(expected)
    except ValueError as error:
        raise P4ProtocolError(
            f"spirallens import escaped the exact worktree source: {observed}"
        ) from error


def _entry_absent(path: Path) -> bool:
    try:
        os.lstat(path)
    except FileNotFoundError:
        return True
    return False


def _probe_native_no_replace() -> str:
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin" and getattr(libc, "renameatx_np", None) is not None:
        return "darwin.renameatx_np.RENAME_EXCL"
    if (
        sys.platform.startswith("linux")
        and getattr(libc, "renameat2", None) is not None
    ):
        return "linux.renameat2.RENAME_NOREPLACE"
    raise P4ProtocolError("native no-replace directory promotion is unavailable")


@dataclass(slots=True)
class _OwnedStage:
    parent_path: Path
    stage_path: Path
    store_path: Path
    parent_fd: int
    stage_fd: int
    device: int
    inode: int
    promoted: bool = False

    def close(self) -> None:
        for descriptor_name in ("stage_fd", "parent_fd"):
            descriptor = getattr(self, descriptor_name)
            if descriptor >= 0:
                os.close(descriptor)
                setattr(self, descriptor_name, -1)


def _reserve_external_stage() -> _OwnedStage:
    if EXTERNAL_STAGE.parent != EXTERNAL_STORE.parent:
        raise P4ProtocolError("external stage and store must share one parent")
    parent = EXTERNAL_STAGE.parent
    parent_meta = os.lstat(parent)
    if not stat.S_ISDIR(parent_meta.st_mode):
        raise P4ProtocolError("external parent must be a real directory")
    parent_fd = os.open(
        parent,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    stage_fd = -1
    try:
        os.mkdir(EXTERNAL_STAGE.name, mode=0o700, dir_fd=parent_fd)
        os.fsync(parent_fd)
        stage_fd = os.open(
            EXTERNAL_STAGE.name,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
        held = os.fstat(stage_fd)
        live = os.stat(EXTERNAL_STAGE.name, dir_fd=parent_fd, follow_symlinks=False)
        if not stat.S_ISDIR(held.st_mode) or (held.st_dev, held.st_ino) != (
            live.st_dev,
            live.st_ino,
        ):
            raise P4RunError("reserved external stage identity is unstable")
        return _OwnedStage(
            parent_path=parent,
            stage_path=EXTERNAL_STAGE,
            store_path=EXTERNAL_STORE,
            parent_fd=parent_fd,
            stage_fd=stage_fd,
            device=held.st_dev,
            inode=held.st_ino,
        )
    except Exception:
        if stage_fd >= 0:
            os.close(stage_fd)
        os.close(parent_fd)
        raise


def _validate_stage_anchor(stage: _OwnedStage) -> None:
    try:
        held = os.fstat(stage.stage_fd)
        if (held.st_dev, held.st_ino) != (stage.device, stage.inode):
            raise P4PersistenceError("held external stage descriptor identity changed")
        live_name = stage.store_path.name if stage.promoted else stage.stage_path.name
        live = os.stat(live_name, dir_fd=stage.parent_fd, follow_symlinks=False)
        if (live.st_dev, live.st_ino) != (stage.device, stage.inode):
            raise P4PersistenceError("external stage/store namespace identity changed")
    except OSError as error:
        raise P4PersistenceError("cannot validate external stage identity") from error


def _write_stage_document(
    stage: _OwnedStage,
    name: str,
    document: Mapping[str, object],
) -> tuple[bytes, str]:
    if "/" in name or not name:
        raise P4RunError("stage member name is invalid")
    source = canonical_json_bytes(document)
    if len(source) > CANONICAL_BYTE_LIMIT:
        raise P4RunError(f"stage member {name} exceeds the byte limit")
    try:
        _validate_stage_anchor(stage)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(name, flags, 0o400, dir_fd=stage.stage_fd)
        try:
            view = memoryview(source)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise P4PersistenceError(
                        f"stage member {name} write made no progress"
                    )
                view = view[written:]
            os.fsync(descriptor)
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_nlink != 1
                or metadata.st_size != len(source)
            ):
                raise P4PersistenceError(f"stage member {name} identity is invalid")
        finally:
            os.close(descriptor)
        os.fsync(stage.stage_fd)
        read_fd = os.open(
            name,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=stage.stage_fd,
        )
        try:
            observed = b""
            while True:
                block = os.read(read_fd, 65_536)
                if not block:
                    break
                observed += block
        finally:
            os.close(read_fd)
    except P4PersistenceError:
        raise
    except OSError as error:
        raise P4PersistenceError(f"cannot persist stage member {name}") from error
    if observed != source:
        raise P4PersistenceError(f"stage member {name} round-trip differs")
    return source, _sha256_bytes(source)


def _promote_external_stage(stage: _OwnedStage) -> None:
    _validate_stage_anchor(stage)
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        function = getattr(libc, "renameatx_np", None)
        flag = 0x00000004
    elif sys.platform.startswith("linux"):
        function = getattr(libc, "renameat2", None)
        flag = 0x00000001
    else:  # pragma: no cover - preflight rejects this
        function = None
        flag = 0
    if function is None:
        raise P4PersistenceError("native no-replace directory promotion disappeared")
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
        stage.parent_fd,
        os.fsencode(stage.stage_path.name),
        stage.parent_fd,
        os.fsencode(stage.store_path.name),
        flag,
    )
    if result != 0:
        observed_errno = ctypes.get_errno() or errno.EIO
        raise P4PersistenceError(
            f"native external no-replace promotion failed with errno {observed_errno}"
        )
    stage.promoted = True
    try:
        os.fsync(stage.parent_fd)
    except OSError as error:
        raise P4PersistenceError(
            "cannot fsync external parent after promotion"
        ) from error
    _validate_stage_anchor(stage)


def _exact_run_argv(repo_root: Path) -> list[str]:
    lexical_python = repo_root / ".venv" / "bin" / "python"
    return [
        str(lexical_python),
        "-I",
        "-B",
        "-X",
        f"pycache_prefix={_python_bytecode_cache_prefix(repo_root)}",
        str((repo_root / REPOSITORY_RUNNER).resolve()),
        "--run",
    ]


def _validate_exact_run_argv(value: object, *, repo_root: Path, label: str) -> None:
    argv = _sequence(value, label=label)
    _constant(argv, _exact_run_argv(repo_root), label=label)
    _constant(argv.count("-I"), 1, label=f"{label} isolated flag count")
    _constant(argv.count("-B"), 1, label=f"{label} no-bytecode flag count")
    _constant(argv.count("-X"), 1, label=f"{label} -X flag count")
    expected_prefix = f"pycache_prefix={_python_bytecode_cache_prefix(repo_root)}"
    _constant(argv.count(expected_prefix), 1, label=f"{label} pycache prefix count")


def _require_sha256(value: object, *, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise P4RunError(f"{label} must be a lowercase SHA-256")
    return value


def _require_plain_nonnegative_int(value: object, *, label: str) -> int:
    if type(value) is not int or value < 0:
        raise P4RunError(f"{label} must be a nonnegative integer")
    return value


def _require_finite_scalar(value: object, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise P4RunError(f"{label} must be a finite number")
    scalar = float(value)
    if not math.isfinite(scalar):
        raise P4RunError(f"{label} must be a finite number")
    return scalar


def _reconstruct_canonical_graph(
    value: object,
    *,
    label: str,
) -> dict[str, object]:
    """Reconstruct the closed 49-row graph projection from persisted edges."""

    rows = _sequence(value, label=f"{label} canonical edges")
    canonical: list[tuple[int, int]] = []
    for index, raw in enumerate(rows):
        edge = _sequence(raw, label=f"{label} canonical edge {index}")
        if (
            len(edge) != 2
            or type(edge[0]) is not int
            or type(edge[1]) is not int
            or not 0 <= edge[0] < edge[1] < 49
        ):
            raise P4RunError(f"{label} canonical edge {index} is invalid")
        canonical.append((edge[0], edge[1]))
    if canonical != sorted(set(canonical)):
        raise P4RunError(f"{label} canonical edges must be sorted and unique")

    adjacency: list[list[int]] = [[] for _ in range(49)]
    degree = np.zeros(49, dtype="<i8")
    for left, right in canonical:
        adjacency[left].append(right)
        adjacency[right].append(left)
        degree[left] += 1
        degree[right] += 1

    components = np.full(49, -1, dtype="<i8")
    next_component = 0
    for start in range(49):
        if components[start] >= 0:
            continue
        components[start] = next_component
        stack = [start]
        while stack:
            vertex = stack.pop()
            for neighbor in adjacency[vertex]:
                if components[neighbor] < 0:
                    components[neighbor] = next_component
                    stack.append(neighbor)
        next_component += 1

    two_core = np.ones(49, dtype="|b1")
    residual_degree = degree.copy()
    queue = [int(index) for index in np.flatnonzero(residual_degree < 2)]
    cursor = 0
    while cursor < len(queue):
        vertex = queue[cursor]
        cursor += 1
        if not two_core[vertex]:
            continue
        two_core[vertex] = False
        for neighbor in adjacency[vertex]:
            if two_core[neighbor]:
                residual_degree[neighbor] -= 1
                if residual_degree[neighbor] == 1:
                    queue.append(neighbor)

    edge_array = np.asarray(canonical, dtype="<i8").reshape((-1, 2))
    component_counts = np.bincount(components)
    edge_count = len(canonical)
    component_count = int(component_counts.shape[0])
    return {
        "edges": frozenset(canonical),
        "two_core_rows": frozenset(int(row) for row in np.flatnonzero(two_core)),
        "edge_count": edge_count,
        "component_count": component_count,
        "largest_component_vertex_count": int(np.max(component_counts)),
        "two_core_vertex_count": int(np.count_nonzero(two_core)),
        "cycle_rank": edge_count - 49 + component_count,
        "edge_fingerprint_sha256": array_sha256(edge_array),
        "component_labels_sha256": array_sha256(components),
        "degree_sha256": array_sha256(degree),
        "two_core_mask_sha256": array_sha256(two_core),
    }


def _validate_structural_candidate_projection(
    value: object,
    *,
    family: str,
    label: str,
    require_gates: bool = True,
) -> dict[str, object]:
    item = _mapping(value, label=label)
    _exact_keys(
        item,
        {
            "projection_schema_version",
            "persisted_projection_of_in_memory_receipt",
            "receipt_round_trip_claimed",
            "family",
            "parameters",
            "float64_parameter_big_endian_bits",
            "graph_input_fingerprint_sha256",
            "vertex_order_sha256",
            "state_sha256",
            "specification_fingerprint_sha256",
            "family_identity_fingerprint_sha256",
            "graph_fingerprint_sha256",
            "edge_fingerprint_sha256",
            "component_labels_sha256",
            "degree_sha256",
            "two_core_mask_sha256",
            "canonical_edges",
            "edge_count",
            "mean_degree",
            "component_count",
            "largest_component_vertex_count",
            "two_core_vertex_count",
            "cycle_rank",
            "matched_cycle_classes",
            "cycle_binding_fingerprints",
        },
        label=label,
    )
    _constant(
        item["projection_schema_version"],
        "spirallens.p4-structural-candidate-projection.v0.1",
        label=f"{label} schema",
    )
    _constant(
        item["persisted_projection_of_in_memory_receipt"],
        True,
        label=f"{label} persisted projection",
    )
    _constant(
        item["receipt_round_trip_claimed"],
        False,
        label=f"{label} round-trip claim",
    )
    _constant(item["family"], family, label=f"{label} family")
    parameters = _mapping(item["parameters"], label=f"{label} parameters")
    bits = _mapping(
        item["float64_parameter_big_endian_bits"],
        label=f"{label} parameter bits",
    )
    if family == GraphFamily.MUTUAL_KNN.value:
        _exact_keys(parameters, {"neighbor_count"}, label=f"{label} parameters")
        neighbor_count = _require_plain_nonnegative_int(
            parameters["neighbor_count"], label=f"{label} neighbor count"
        )
        if not 2 <= neighbor_count <= 16:
            raise P4RunError(f"{label} neighbor count is outside the freeze")
        expected_bits = {"neighbor_count": None}
    elif family == GraphFamily.FIXED_RADIUS.value:
        _exact_keys(parameters, {"radius"}, label=f"{label} parameters")
        radius = _require_finite_scalar(parameters["radius"], label=f"{label} radius")
        if radius <= 0.0 or type(parameters["radius"]) is not float:
            raise P4RunError(f"{label} radius must be positive float64")
        expected_bits = {"radius": struct.pack(">d", radius).hex()}
    elif family == GraphFamily.SHARED_NEIGHBOR.value:
        _exact_keys(
            parameters,
            {"neighbor_count", "minimum_shared_neighbors"},
            label=f"{label} parameters",
        )
        neighbor_count = _require_plain_nonnegative_int(
            parameters["neighbor_count"], label=f"{label} neighbor count"
        )
        minimum = _require_plain_nonnegative_int(
            parameters["minimum_shared_neighbors"],
            label=f"{label} shared-neighbor minimum",
        )
        if not 2 <= neighbor_count <= 16 or not 1 <= minimum <= neighbor_count:
            raise P4RunError(f"{label} shared-neighbor parameters are outside freeze")
        expected_bits = {
            "minimum_shared_neighbors": None,
            "neighbor_count": None,
        }
    else:
        raise P4RunError(f"{label} family is outside the freeze")
    _constant(bits, expected_bits, label=f"{label} parameter bits")
    for key in (
        "graph_input_fingerprint_sha256",
        "vertex_order_sha256",
        "state_sha256",
        "specification_fingerprint_sha256",
        "family_identity_fingerprint_sha256",
        "graph_fingerprint_sha256",
        "edge_fingerprint_sha256",
        "component_labels_sha256",
        "degree_sha256",
        "two_core_mask_sha256",
    ):
        _require_sha256(item[key], label=f"{label} {key}")
    reconstructed = _reconstruct_canonical_graph(item["canonical_edges"], label=label)
    for key in (
        "edge_count",
        "component_count",
        "largest_component_vertex_count",
        "two_core_vertex_count",
        "cycle_rank",
        "edge_fingerprint_sha256",
        "component_labels_sha256",
        "degree_sha256",
        "two_core_mask_sha256",
    ):
        _constant(item[key], reconstructed[key], label=f"{label} reconstructed {key}")
    edge_count = _require_plain_nonnegative_int(
        item["edge_count"], label=f"{label} edge count"
    )
    component_count = _require_plain_nonnegative_int(
        item["component_count"], label=f"{label} component count"
    )
    largest = _require_plain_nonnegative_int(
        item["largest_component_vertex_count"], label=f"{label} largest component"
    )
    core = _require_plain_nonnegative_int(
        item["two_core_vertex_count"], label=f"{label} two-core count"
    )
    cycle_rank = _require_plain_nonnegative_int(
        item["cycle_rank"], label=f"{label} cycle rank"
    )
    _constant(
        item["mean_degree"], 2.0 * edge_count / 49.0, label=f"{label} mean degree"
    )
    if component_count < 1 or largest > 49 or core > 49:
        raise P4RunError(f"{label} has impossible graph metrics")
    if require_gates and (
        not 98 <= edge_count <= 196
        or not 45 <= largest <= 49
        or not 40 <= core <= 49
        or cycle_rank < 2
    ):
        raise P4RunError(f"{label} does not meet the sealed per-graph gates")
    matched_classes = _sequence(
        item["matched_cycle_classes"], label=f"{label} matched cycle classes"
    )
    if matched_classes != [
        cycle_class
        for cycle_class in CYCLE_CLASS_ORDER
        if cycle_class in matched_classes
    ] or len(matched_classes) != len(set(matched_classes)):
        raise P4RunError(f"{label} matched cycle classes are not canonical")
    if require_gates:
        _constant(
            matched_classes,
            list(CYCLE_CLASS_ORDER),
            label=f"{label} matched cycle classes",
        )
    bindings = _mapping(
        item["cycle_binding_fingerprints"], label=f"{label} cycle bindings"
    )
    _exact_keys(bindings, set(CYCLE_CLASS_ORDER), label=f"{label} cycle bindings")
    for cycle_class in CYCLE_CLASS_ORDER:
        if cycle_class in matched_classes:
            _require_sha256(
                bindings[cycle_class], label=f"{label} {cycle_class} binding"
            )
        else:
            _constant(
                bindings[cycle_class],
                "",
                label=f"{label} unmatched {cycle_class} binding",
            )
    return item


def _validate_base_triplet_measurement_semantics(
    measurements: Mapping[str, object],
    *,
    selected: Sequence[Mapping[str, object]],
    require_gates: bool = True,
) -> tuple[dict[str, object], dict[str, int | float], int]:
    """Recompute the 13 common structural fields without choosing a schema."""

    normalized = dict(measurements)
    edges = [int(item["edge_count"]) for item in selected]
    largest = [int(item["largest_component_vertex_count"]) for item in selected]
    cores = [int(item["two_core_vertex_count"]) for item in selected]
    components = [int(item["component_count"]) for item in selected]
    reconstructed = [
        _reconstruct_canonical_graph(
            item["canonical_edges"], label=f"selected {item['family']}"
        )
        for item in selected
    ]
    derived = {
        "edge_count_minimum": min(edges),
        "edge_count_maximum": max(edges),
        "edge_count_spread": max(edges) - min(edges),
        "edge_count_ratio": max(edges) / min(edges),
        "mean_degree_target_deviation_sum": sum(
            abs(2.0 * edge / 49.0 - 6.0) for edge in edges
        ),
        "mean_degree_target_deviation_numerator": sum(
            abs(2 * edge - 294) for edge in edges
        ),
        "largest_component_vertex_count_spread": max(largest) - min(largest),
        "two_core_vertex_count_spread": max(cores) - min(cores),
        "component_count_sum": sum(components),
    }
    for key, expected in derived.items():
        _constant(normalized[key], expected, label=f"triplet {key}")
    common_core = len(
        set.intersection(*(set(item["two_core_rows"]) for item in reconstructed))
    )
    _constant(
        normalized["common_two_core_intersection_count"],
        common_core,
        label="triplet common two-core count",
    )
    if require_gates and common_core < 35:
        raise P4RunError("triplet common two-core count violates the frozen gate")
    pairwise = [
        _mapping(item, label="selector pairwise measurement")
        for item in _sequence(normalized["pairwise"], label="triplet pairwise")
    ]
    expected_pairs = ((0, 1), (0, 2), (1, 2))
    if len(pairwise) != len(expected_pairs):
        raise P4RunError("selector triplet must carry exactly three pairwise rows")
    all_different = True
    all_within = True
    for item, (left_index, right_index) in zip(pairwise, expected_pairs, strict=True):
        _exact_keys(
            item,
            {
                "left_family",
                "right_family",
                "intersection_count",
                "union_count",
                "jaccard",
                "edge_sets_differ",
                "jaccard_at_most_0_85",
            },
            label="selector pairwise measurement",
        )
        _constant(
            item["left_family"],
            selected[left_index]["family"],
            label="pairwise left family",
        )
        _constant(
            item["right_family"],
            selected[right_index]["family"],
            label="pairwise right family",
        )
        left_edge_set = set(reconstructed[left_index]["edges"])
        right_edge_set = set(reconstructed[right_index]["edges"])
        intersection = len(left_edge_set & right_edge_set)
        union = len(left_edge_set | right_edge_set)
        _constant(
            item["intersection_count"],
            intersection,
            label="pairwise reconstructed intersection",
        )
        _constant(
            item["union_count"],
            union,
            label="pairwise reconstructed union",
        )
        if union == 0:
            raise P4RunError("pairwise union is empty")
        _constant(item["jaccard"], intersection / union, label="pairwise Jaccard")
        different = left_edge_set != right_edge_set
        within = 20 * intersection <= 17 * union
        _constant(item["edge_sets_differ"], different, label="pairwise distinctness")
        _constant(item["jaccard_at_most_0_85"], within, label="pairwise Jaccard gate")
        all_different = all_different and different
        all_within = all_within and within
    _constant(
        normalized["pairwise_edge_sets_must_differ"],
        all_different,
        label="triplet pairwise distinct fold",
    )
    _constant(
        normalized["pairwise_edge_jaccard_at_most_0_85"],
        all_within,
        label="triplet pairwise Jaccard fold",
    )
    if require_gates and (not all_different or not all_within):
        raise P4RunError("sealed selector triplet violates pairwise gates")
    if require_gates:
        _constant(
            4 * int(normalized["edge_count_maximum"])
            <= 5 * int(normalized["edge_count_minimum"]),
            True,
            label="triplet edge ratio gate",
        )
        if (
            derived["largest_component_vertex_count_spread"] > 2
            or derived["two_core_vertex_count_spread"] > 4
        ):
            raise P4RunError("sealed selector triplet violates spread gates")
    return normalized, derived, common_core


def _validate_confirmation_triplet_measurements(
    value: object,
    *,
    selected: Sequence[Mapping[str, object]],
    require_gates: bool = True,
) -> dict[str, object]:
    measurements = _mapping(value, label="confirmation triplet measurements")
    _exact_keys(
        measurements,
        CONFIRMATION_TRIPLET_MEASUREMENT_KEYS,
        label="confirmation triplet measurements",
    )
    normalized, _derived, _common_core = _validate_base_triplet_measurement_semantics(
        measurements,
        selected=selected,
        require_gates=require_gates,
    )
    return normalized


def _selector_parameter_key(
    selected: Sequence[Mapping[str, object]],
) -> list[int]:
    parameter_key: list[int] = []
    for item in selected:
        parameters = _mapping(item["parameters"], label="selected parameters")
        family = str(item["family"])
        if family == GraphFamily.MUTUAL_KNN.value:
            parameter_key.append(int(parameters["neighbor_count"]))
        elif family == GraphFamily.FIXED_RADIUS.value:
            parameter_key.append(
                struct.unpack(">Q", struct.pack(">d", float(parameters["radius"])))[0]
            )
        else:
            parameter_key.extend(
                (
                    int(parameters["neighbor_count"]),
                    int(parameters["minimum_shared_neighbors"]),
                )
            )
    return parameter_key


def _validate_selector_triplet_measurements(
    value: object,
    *,
    selected: Sequence[Mapping[str, object]],
    require_gates: bool = True,
) -> dict[str, object]:
    measurements = _mapping(value, label="selector triplet measurements")
    _exact_keys(
        measurements,
        SELECTOR_TRIPLET_MEASUREMENT_KEYS,
        label="selector triplet measurements",
    )
    base = {key: measurements[key] for key in CONFIRMATION_TRIPLET_MEASUREMENT_KEYS}
    _normalized, derived, common_core = _validate_base_triplet_measurement_semantics(
        base,
        selected=selected,
        require_gates=require_gates,
    )
    objective = [
        derived["edge_count_spread"],
        derived["mean_degree_target_deviation_numerator"],
        -common_core,
        derived["component_count_sum"],
        _selector_parameter_key(selected),
    ]
    _constant(
        measurements["lexicographic_objective"],
        objective,
        label="triplet lexicographic objective",
    )
    _constant(
        measurements["jaccard_used_as_objective"],
        False,
        label="triplet Jaccard objective flag",
    )
    return measurements


def _validate_selector_projection(value: object) -> dict[str, object]:
    selector = _mapping(value, label="selector projection")
    _exact_keys(
        selector,
        {
            "projection_schema_version",
            "state",
            "reason",
            "selector_input",
            "selector_audit",
            "selected",
            "objective",
            "triplet_measurements",
            "field_read",
            "core_read",
            "holonomy_read",
            "phase_read",
            "winding_read",
            "charge_read",
            "pythia_terminal_candidate_values_read",
        },
        label="selector projection",
    )
    _constant(
        selector["projection_schema_version"],
        SELECTOR_PROJECTION_SCHEMA_VERSION,
        label="selector schema",
    )
    for key in (
        "field_read",
        "core_read",
        "holonomy_read",
        "phase_read",
        "winding_read",
        "charge_read",
        "pythia_terminal_candidate_values_read",
    ):
        _constant(selector[key], False, label=f"selector {key}")
    selector_input = _mapping(selector["selector_input"], label="selector input")
    _exact_keys(
        selector_input,
        {
            "input_type",
            "graph_input_fingerprint_sha256",
            "vertex_order_sha256",
            "state_sha256",
            "oriented_faces_sha256",
            "case_object_accepted",
            "truth_object_accepted",
            "field_object_accepted",
            "core_object_accepted",
        },
        label="selector input",
    )
    _constant(
        selector_input["input_type"],
        "GraphInput-plus-oriented-domain-faces-only",
        label="selector input type",
    )
    for key in (
        "graph_input_fingerprint_sha256",
        "vertex_order_sha256",
        "state_sha256",
        "oriented_faces_sha256",
    ):
        _require_sha256(selector_input[key], label=f"selector input {key}")
    for key in (
        "case_object_accepted",
        "truth_object_accepted",
        "field_object_accepted",
        "core_object_accepted",
    ):
        _constant(selector_input[key], False, label=f"selector input {key}")
    audit = _mapping(selector["selector_audit"], label="selector audit")
    _exact_keys(
        audit,
        {
            "generated_candidate_counts",
            "per_graph_eligible_candidate_counts",
            "per_graph_rejection_reason_counts",
            "all_candidate_projection_sha256",
            "per_graph_decision_count",
            "all_per_graph_decisions_sha256",
            "triplets_considered",
            "triplet_rejection_reason_counts",
            "all_triplet_decisions_sha256",
            "eligible_triplets",
            "radius_unique_finite_distance_count",
            "radius_budget_eligible_distance_count",
            "radius_distance_scan_sha256",
            "radius_zero_pair_count",
            "radius_float64_uint64_order",
            "radius_budget_eligible_zero_unrepresentable",
        },
        label="selector audit",
    )
    for key in (
        "all_candidate_projection_sha256",
        "all_per_graph_decisions_sha256",
        "all_triplet_decisions_sha256",
        "radius_distance_scan_sha256",
    ):
        _require_sha256(audit[key], label=f"selector audit {key}")
    for key in (
        "per_graph_decision_count",
        "triplets_considered",
        "eligible_triplets",
        "radius_unique_finite_distance_count",
        "radius_budget_eligible_distance_count",
        "radius_zero_pair_count",
    ):
        if type(audit[key]) is not int or int(audit[key]) < 0:
            raise P4RunError(f"selector audit {key} must be nonnegative integer")
    for key in (
        "generated_candidate_counts",
        "per_graph_eligible_candidate_counts",
    ):
        counts = _mapping(audit[key], label=f"selector audit {key}")
        _exact_keys(counts, set(FAMILY_ORDER), label=f"selector audit {key}")
        for family in FAMILY_ORDER:
            _require_plain_nonnegative_int(
                counts[family], label=f"selector audit {key}.{family}"
            )
    for key in (
        "per_graph_rejection_reason_counts",
        "triplet_rejection_reason_counts",
    ):
        counts = _mapping(audit[key], label=f"selector audit {key}")
        for reason, count in counts.items():
            if not reason:
                raise P4RunError(f"selector audit {key} has an empty reason")
            _require_plain_nonnegative_int(
                count, label=f"selector audit {key}.{reason}"
            )
    _constant(audit["radius_float64_uint64_order"], True, label="radius bit ordering")
    if type(audit["radius_budget_eligible_zero_unrepresentable"]) is not bool:
        raise P4RunError("zero-radius audit flag must be boolean")
    state = selector["state"]
    if state == "pass":
        selected = _sequence(selector["selected"], label="selected triplet")
        if len(selected) != 3:
            raise P4RunError("passing selector must persist exactly three graphs")
        normalized_selected = [
            _validate_structural_candidate_projection(
                item,
                family=family,
                label=f"selected candidate {family}",
            )
            for item, family in zip(selected, FAMILY_ORDER, strict=True)
        ]
        measurements = _validate_selector_triplet_measurements(
            selector["triplet_measurements"], selected=normalized_selected
        )
        _constant(
            selector["objective"],
            measurements["lexicographic_objective"],
            label="selector objective",
        )
        if int(audit["eligible_triplets"]) < 1:
            raise P4RunError("passing selector requires at least one eligible triplet")
        _constant(selector["reason"], "ok", label="selector pass reason")
    elif state == "insufficient":
        if selector["selected"] is not None or selector["objective"] is not None:
            raise P4RunError("insufficient selector cannot persist a winner/objective")
        if selector["triplet_measurements"] is not None:
            raise P4RunError(
                "insufficient selector cannot persist triplet measurements"
            )
        if selector["reason"] != "no-eligible-three-family-triplet":
            raise P4RunError("selector insufficient reason is outside the freeze")
        _constant(audit["eligible_triplets"], 0, label="insufficient eligible count")
    else:
        raise P4RunError("selector state is outside the closed vocabulary")
    return selector


def _validate_confirmation_structural_projection(
    value: object,
    *,
    selector: Mapping[str, object],
    expected_state: str,
) -> dict[str, object]:
    structural = _mapping(value, label="confirmation structural")
    _exact_keys(
        structural,
        {
            "projection_schema_version",
            "state",
            "reason",
            "selected",
            "triplet_measurements",
            "selector_rerun",
        },
        label="confirmation structural",
    )
    _constant(
        structural["projection_schema_version"],
        CONFIRMATION_STRUCTURAL_PROJECTION_SCHEMA_VERSION,
        label="confirmation structural schema",
    )
    _constant(
        structural["state"], expected_state, label="confirmation structural state"
    )
    _constant(
        structural["reason"],
        "ok"
        if expected_state == "pass"
        else "fixed-triplet-failed-confirmation-support",
        label="confirmation structural reason",
    )
    _constant(
        structural["selector_rerun"],
        False,
        label="confirmation selector rerun",
    )
    selected = _sequence(structural["selected"], label="confirmation selected")
    sealed_selected = _sequence(selector["selected"], label="sealed selected")
    if len(selected) != 3 or len(sealed_selected) != 3:
        raise P4RunError("confirmation and sealed selector require three graphs")
    normalized = [
        _validate_structural_candidate_projection(
            raw,
            family=family,
            label=f"confirmation candidate {family}",
            require_gates=expected_state == "pass",
        )
        for raw, family in zip(selected, FAMILY_ORDER, strict=True)
    ]
    for confirmation_item, sealed_raw in zip(normalized, sealed_selected, strict=True):
        sealed_item = _mapping(sealed_raw, label="sealed selector winner")
        _constant(
            confirmation_item["family"],
            sealed_item["family"],
            label="confirmation winner family binding",
        )
        _constant(
            confirmation_item["parameters"],
            sealed_item["parameters"],
            label="confirmation winner parameter binding",
        )
    measurements = _validate_confirmation_triplet_measurements(
        structural["triplet_measurements"],
        selected=normalized,
        require_gates=expected_state == "pass",
    )
    if expected_state == "pass" and not _triplet_meets_requirements(measurements):
        raise P4RunError("passing confirmation triplet fails frozen measurements")
    if expected_state == "insufficient" and _triplet_meets_requirements(measurements):
        per_graph_pass = all(
            98 <= int(item["edge_count"]) <= 196
            and int(item["largest_component_vertex_count"]) >= 45
            and int(item["two_core_vertex_count"]) >= 40
            and int(item["cycle_rank"]) >= 2
            and item["matched_cycle_classes"] == list(CYCLE_CLASS_ORDER)
            for item in normalized
        )
        if per_graph_pass:
            raise P4RunError(
                "insufficient confirmation triplet passes every frozen gate"
            )
    return structural


def _validate_matrix_projection(
    value: object,
    *,
    role: str,
    sealed_selected: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    matrix = _mapping(value, label=f"{role} matrix")
    _exact_keys(
        matrix,
        {
            "role",
            "cell_count",
            "required_cell_ids_sha256",
            "cells",
            "purpose_adjacency_checks",
            "purpose_adjacency_check_count",
            "purpose_adjacency_checks_sha256",
            "worst_oracle_or_null_error_cycles",
            "graph_family_spans",
        },
        label=f"{role} matrix",
    )
    _constant(matrix["role"], role, label=f"{role} matrix role")
    _constant(matrix["cell_count"], 54, label=f"{role} matrix cell count")
    required_ids = _required_cell_ids(
        role, tuple(name for name, _expected in CROSSED_CASES)
    )
    _constant(
        matrix["required_cell_ids_sha256"],
        canonical_json_sha256(required_ids),
        label=f"{role} required cell digest",
    )
    cells = [
        _mapping(item, label=f"{role} cell")
        for item in _sequence(matrix["cells"], label=f"{role} cells")
    ]
    if len(cells) != 54:
        raise P4RunError(f"{role} matrix must carry 54 cells")
    _constant(
        [item.get("cell_id") for item in cells], required_ids, label=f"{role} cell ids"
    )
    expected_by_case = dict(CROSSED_CASES)
    expected_axes = list(
        product(
            (name for name, _expected in CROSSED_CASES),
            CYCLE_CLASS_ORDER,
            FAMILY_ORDER,
            FAMILY_ORDER,
        )
    )
    errors: list[float] = []
    totals_by_span: dict[str, list[float]] = {
        item: []
        for item in _required_span_ids(
            role, tuple(name for name, _expected in CROSSED_CASES)
        )
    }
    for item, axes in zip(cells, expected_axes, strict=True):
        _exact_keys(
            item,
            {
                "cell_id",
                "case",
                "cycle_class",
                "field_graph_family",
                "cycle_graph_family",
                "attempt_status",
                "signed_total_cycles",
                "expected_continuous_cycles",
                "absolute_error_cycles",
                "reason_codes",
            },
            label=f"{role} cell",
        )
        case_name, cycle_class, field_family, cycle_family = axes
        _constant(item["cell_id"], _cell_id(role, *axes), label=f"{role} cell id")
        _constant(item["case"], case_name, label=f"{role} cell case")
        _constant(item["cycle_class"], cycle_class, label=f"{role} cell cycle class")
        _constant(
            item["field_graph_family"],
            field_family,
            label=f"{role} cell field family",
        )
        _constant(
            item["cycle_graph_family"],
            cycle_family,
            label=f"{role} cell cycle family",
        )
        if case_name not in expected_by_case:
            raise P4RunError(f"{role} cell case is outside the freeze")
        _constant(
            item["expected_continuous_cycles"],
            expected_by_case[str(case_name)],
            label=f"{role} expected cycles",
        )
        status = item["attempt_status"]
        if type(status) is not str or status not in {"evaluable", "insufficient"}:
            raise P4RunError(f"{role} cell attempt status is invalid")
        if not isinstance(item["reason_codes"], list) or any(
            type(reason) is not str for reason in item["reason_codes"]
        ):
            raise P4RunError(f"{role} cell reason codes are invalid")
        reasons = item["reason_codes"]
        if reasons != sorted(set(reasons)) or any(
            reason not in MATRIX_INSUFFICIENT_REASONS for reason in reasons
        ):
            raise P4RunError(f"{role} cell reason codes are outside the freeze")
        signed_raw = item["signed_total_cycles"]
        signed = (
            _require_finite_scalar(signed_raw, label=f"{role} signed total")
            if isinstance(signed_raw, (int, float)) and not isinstance(signed_raw, bool)
            else None
        )
        error = _nonnegative_finite_scalar(item["absolute_error_cycles"])
        phase_residual_only = reasons == [
            "sampled_phase_total_outside_integer_residual_band"
        ]
        if status == "evaluable":
            if reasons or signed is None or error is None:
                raise P4RunError(
                    f"{role} evaluable cell requires finite values and no reasons"
                )
        else:
            if not reasons:
                raise P4RunError(f"{role} insufficient cell requires reasons")
            if phase_residual_only:
                if signed is None or error is None:
                    raise P4RunError(
                        f"{role} phase-residual cell requires finite values"
                    )
            elif signed_raw is not None or item["absolute_error_cycles"] is not None:
                raise P4RunError(
                    f"{role} prerequisite/branch insufficiency requires null values"
                )
        if signed is not None:
            if error is None:
                raise P4RunError(f"{role} finite cell total requires finite error")
            expected_error = abs(signed - float(expected_by_case[str(case_name)]))
            if error != expected_error:
                raise P4RunError(f"{role} cell error does not recompute")
            errors.append(error)
            totals_by_span[_span_id(role, case_name, cycle_class)].append(signed)
    worst = max(errors) if errors else None
    _constant(
        matrix["worst_oracle_or_null_error_cycles"], worst, label=f"{role} worst error"
    )
    checks = [
        _mapping(item, label=f"{role} purpose check")
        for item in _sequence(
            matrix["purpose_adjacency_checks"], label="purpose checks"
        )
    ]
    _constant(
        matrix["purpose_adjacency_check_count"], 18, label=f"{role} purpose count"
    )
    if len(checks) != 18:
        raise P4RunError(f"{role} matrix must carry 18 purpose checks")
    expected_purpose_axes = list(
        product(
            (name for name, _expected in CROSSED_CASES),
            CYCLE_CLASS_ORDER,
            FAMILY_ORDER,
        )
    )
    selected_edge_order = {
        str(item["family"]): item["edge_fingerprint_sha256"] for item in sealed_selected
    }
    if list(selected_edge_order) != list(FAMILY_ORDER):
        raise P4RunError(f"{role} matrix lacks the sealed family triplet")
    for item, (case_name, cycle_class, family) in zip(
        checks, expected_purpose_axes, strict=True
    ):
        _exact_keys(
            item,
            {
                "case",
                "cycle_class",
                "family",
                "field_graph_fingerprint_sha256",
                "cycle_graph_fingerprint_sha256",
                "field_canonical_edge_order_sha256",
                "cycle_canonical_edge_order_sha256",
                "fingerprint_equality_required",
                "canonical_adjacency_equal",
                "canonical_edge_order_sha256_equal",
            },
            label=f"{role} purpose check",
        )
        _constant(item["case"], case_name, label=f"{role} purpose case")
        _constant(
            item["cycle_class"],
            cycle_class,
            label=f"{role} purpose cycle class",
        )
        _constant(item["family"], family, label=f"{role} purpose family")
        _constant(
            item["fingerprint_equality_required"],
            False,
            label="fingerprint equality requirement",
        )
        _constant(
            item["canonical_adjacency_equal"], True, label="purpose adjacency equality"
        )
        _constant(
            item["canonical_edge_order_sha256_equal"],
            True,
            label="purpose edge order equality",
        )
        _require_sha256(
            item["field_graph_fingerprint_sha256"], label="field graph fingerprint"
        )
        _require_sha256(
            item["cycle_graph_fingerprint_sha256"], label="cycle graph fingerprint"
        )
        field_edge_order = _require_sha256(
            item["field_canonical_edge_order_sha256"],
            label="field graph edge order",
        )
        cycle_edge_order = _require_sha256(
            item["cycle_canonical_edge_order_sha256"],
            label="cycle graph edge order",
        )
        _constant(
            field_edge_order,
            selected_edge_order[family],
            label=f"{role} {family} sealed field edge order",
        )
        _constant(
            cycle_edge_order,
            selected_edge_order[family],
            label=f"{role} {family} sealed cycle edge order",
        )
    _constant(
        matrix["purpose_adjacency_checks_sha256"],
        canonical_json_sha256(checks),
        label=f"{role} purpose-check digest",
    )
    spans = [
        _mapping(item, label=f"{role} span")
        for item in _sequence(matrix["graph_family_spans"], label=f"{role} spans")
    ]
    required_span_ids = list(totals_by_span)
    if len(spans) != 6:
        raise P4RunError(f"{role} matrix must carry six spans")
    _constant(
        [item.get("span_id") for item in spans],
        required_span_ids,
        label=f"{role} span ids",
    )
    expected_span_axes = list(
        product((name for name, _expected in CROSSED_CASES), CYCLE_CLASS_ORDER)
    )
    for item, (case_name, cycle_class) in zip(spans, expected_span_axes, strict=True):
        _exact_keys(
            item,
            {"span_id", "case", "cycle_class", "graph_family_span_cycles"},
            label=f"{role} span",
        )
        _constant(item["case"], case_name, label=f"{role} span case")
        _constant(item["cycle_class"], cycle_class, label=f"{role} span cycle class")
        totals = totals_by_span[str(item["span_id"])]
        expected_span = max(totals) - min(totals) if totals else None
        _constant(
            item["graph_family_span_cycles"], expected_span, label=f"{role} span value"
        )
    return matrix


def _observation_keys(observation_id: str, state: object) -> set[str]:
    control_id = observation_id.split("|", 1)[0]
    if observation_id == "pure_so2_gauge|procrustes-connection":
        return {
            "observation_id",
            "state",
            "angle_error_radians",
            "angle_tolerance_radians",
            "residual_frobenius",
            "residual_tolerance",
        }
    if observation_id == "pure_so2_gauge|local-frame-gauge":
        return {
            "observation_id",
            "state",
            "phase_total_gauge_delta_cycles",
            "phase_total_tolerance_cycles",
            "coordinate_law_error",
            "coordinate_law_tolerance",
            "receipt_sha256",
        }
    if control_id == "degree_preserving_rewire":
        return (
            {
                "observation_id",
                "state",
                "degree_preserved",
                "edge_set_changed",
                "simple_graph_verified",
                "symmetric_difference_edge_count",
                "reason",
            }
            if state == "insufficient"
            else {
                "observation_id",
                "state",
                "degree_preserved",
                "edge_set_changed",
                "simple_graph_verified",
                "symmetric_difference_edge_count",
                "removed_edges",
                "added_edges",
            }
        )
    if control_id == "amplitude_label_permutation":
        return {
            "observation_id",
            "state",
            "absolute_error_cycles",
            "tolerance_cycles",
            "amplitude_multiset_exact",
            "transformation_nonidentity",
        }
    if control_id == "orientation_reversal":
        return {
            "observation_id",
            "state",
            "error_cycles",
            "tolerance_cycles",
            "receipt_sha256",
        }
    if control_id == "density_warp_confirmation":
        return {"observation_id", "state", "confirmation_structural_sha256"}
    if control_id == "joint_vertex_permutation":
        return {
            "observation_id",
            "state",
            "vertex_id_edge_content_preserved",
            "base_vertex_ids",
            "base_vertex_order_sha256",
            "transformed_vertex_ids",
            "transformed_vertex_order_sha256",
            "transformed_canonical_edges",
            "base_edge_content_sha256",
            "transformed_edge_content_sha256",
            "base_edge_order_sha256",
            "transformed_edge_order_sha256",
            "sealed_family_edge_order_sha256",
            "receipt_equality_scope",
        }
    if control_id == "ambient_orthogonal_transform":
        return {
            "observation_id",
            "state",
            "canonical_adjacency_preserved",
            "transformed_canonical_edges",
            "base_edge_content_sha256",
            "transformed_edge_content_sha256",
            "base_edge_order_sha256",
            "transformed_edge_order_sha256",
            "sealed_family_edge_order_sha256",
            "receipt_equality_scope",
        }
    if control_id == "global_norm_scaling":
        return {
            "observation_id",
            "state",
            "canonical_adjacency_preserved_with_radius_covariance",
            "transformed_canonical_edges",
            "base_edge_content_sha256",
            "transformed_edge_content_sha256",
            "base_edge_order_sha256",
            "transformed_edge_order_sha256",
            "sealed_family_edge_order_sha256",
            "receipt_equality_scope",
        }
    if observation_id == "collapsed_cycleless_phantom|path-graph":
        return {
            "observation_id",
            "state",
            "edge_count",
            "component_count",
            "largest_component_vertex_count",
            "two_core_vertex_count",
            "cycle_rank",
            "edge_fingerprint_sha256",
            "canonical_edges",
            "state_sha256",
        }
    if control_id == "collapsed_cycleless_phantom":
        return {"observation_id", "state", "matched", "binding_fingerprint_sha256"}
    if control_id == "field_only_shuffle":
        return (
            {"observation_id", "state", "reason"}
            if state == "fail"
            else {
                "observation_id",
                "state",
                "base_total_cycles",
                "shuffled_total_cycles",
                "sign_reversal_error_cycles",
                "tolerance_cycles",
            }
        )
    if control_id in {"zero_amplitude", "low_coherence"}:
        return {"observation_id", "state", "reason_codes"}
    if control_id == "non_orientable_frame":
        return {"observation_id", "state", "reason_codes", "receipt_sha256"}
    raise P4RunError(f"unknown control observation {observation_id!r}")


def _require_bool(value: object, *, label: str) -> bool:
    if type(value) is not bool:
        raise P4RunError(f"{label} must be boolean")
    return value


def _derive_control_raw_state(
    control_id: str,
    row: Mapping[str, object],
    *,
    selected_candidates: Mapping[str, Mapping[str, object]],
    confirmation_matrix: Mapping[str, object],
    confirmation_structural: Mapping[str, object],
    oracle_threshold: float,
    graph_threshold: float,
) -> str:
    """Recompute one persisted control solely from its closed dependencies."""

    observations = [
        _mapping(item, label=f"{control_id} observation")
        for item in _sequence(row["observations"], label=f"{control_id} observations")
    ]
    cells = {
        str(item["cell_id"]): item
        for raw in _sequence(confirmation_matrix["cells"], label="confirmation cells")
        for item in (_mapping(raw, label="confirmation cell"),)
    }
    spans = {
        str(item["span_id"]): item
        for raw in _sequence(
            confirmation_matrix["graph_family_spans"], label="confirmation spans"
        )
        for item in (_mapping(raw, label="confirmation span"),)
    }
    contracts = {
        str(item["control_id"]): item for item in _control_contracts_document()
    }
    contract = contracts[control_id]

    if control_id in {
        "known_positive_connection",
        "zero_holonomy_finite_amplitude_null",
        "radial_amplitude_depression_without_holonomy",
    }:
        required = list(contract["required_cell_ids"])
        values = [cells.get(cell_id) for cell_id in required]
        evaluable = len(values) == 18 and all(
            item is not None and item["attempt_status"] == "evaluable"
            for item in values
        )
        errors = [
            _nonnegative_finite_scalar(
                item["absolute_error_cycles"] if item is not None else None
            )
            for item in values
        ]
        finite = evaluable and all(value is not None for value in errors)
        _constant(
            row["observed_cell_count"],
            sum(item is not None for item in values),
            label=f"{control_id} observed cell count",
        )
        _constant(
            row["worst_error_cycles"],
            max(float(value) for value in errors if value is not None)
            if finite
            else None,
            label=f"{control_id} worst error",
        )
        _constant(
            row["oracle_and_null_threshold_cycles"],
            oracle_threshold,
            label=f"{control_id} oracle threshold",
        )
        nuisance_finite = True
        nuisance_passes = True
        if control_id in {
            "zero_holonomy_finite_amplitude_null",
            "radial_amplitude_depression_without_holonomy",
        }:
            nuisance = _mapping(
                row["nuisance_diagnostics"], label=f"{control_id} nuisance"
            )
            nuisance_finite = _require_bool(
                nuisance["finite"], label=f"{control_id} nuisance finite"
            )
            nuisance_passes = _require_bool(
                nuisance["passes"], label=f"{control_id} nuisance passes"
            )
        passed = (
            finite
            and nuisance_finite
            and nuisance_passes
            and all(
                float(value) <= oracle_threshold
                for value in errors
                if value is not None
            )
        )
        return (
            "insufficient"
            if not finite or not nuisance_finite
            else ("pass" if passed else "fail")
        )

    if control_id == "pure_so2_gauge":
        first, second = observations
        angle_error = _nonnegative_finite_scalar(first["angle_error_radians"])
        residual = _nonnegative_finite_scalar(first["residual_frobenius"])
        _constant(first["angle_tolerance_radians"], 1e-8, label="SO2 angle tolerance")
        _constant(first["residual_tolerance"], 1e-8, label="SO2 residual tolerance")
        first_state = (
            "pass"
            if angle_error is not None
            and residual is not None
            and angle_error <= 1e-8
            and residual <= 1e-8
            else "fail"
        )
        _constant(first["state"], first_state, label="SO2 procrustes state")
        phase_error = _nonnegative_finite_scalar(
            second["phase_total_gauge_delta_cycles"]
        )
        coordinate_error = _nonnegative_finite_scalar(second["coordinate_law_error"])
        _constant(
            second["phase_total_tolerance_cycles"],
            1e-8,
            label="SO2 phase tolerance",
        )
        _constant(
            second["coordinate_law_tolerance"],
            1e-8,
            label="SO2 coordinate tolerance",
        )
        _require_sha256(second["receipt_sha256"], label="SO2 receipt")
        second_state = (
            "pass"
            if phase_error is not None
            and coordinate_error is not None
            and phase_error <= 1e-8
            and coordinate_error <= 1e-8
            else "fail"
        )
        _constant(second["state"], second_state, label="SO2 gauge state")
        return "pass" if first_state == second_state == "pass" else "fail"

    if control_id == "degree_preserving_rewire":
        states: list[str] = []
        for item in observations:
            family = str(item["observation_id"]).split("|", 1)[1]
            selected = selected_candidates.get(family)
            if selected is None:
                raise P4RunError("rewire observation has no sealed family evidence")
            graph = _reconstruct_canonical_graph(
                selected["canonical_edges"], label=f"rewire sealed {family}"
            )
            expected_observation = _derive_canonical_rewire_observation(
                graph["edges"], family=family
            )
            _constant(
                item,
                expected_observation,
                label=f"rewire {family} raw-edge derivation",
            )
            states.append(str(expected_observation["state"]))
        return (
            "pass"
            if all(state == "pass" for state in states)
            else ("insufficient" if "insufficient" in states else "fail")
        )

    if control_id == "amplitude_label_permutation":
        states = []
        for item in observations:
            error = _nonnegative_finite_scalar(item["absolute_error_cycles"])
            _constant(item["tolerance_cycles"], 1e-8, label="amplitude tolerance")
            multiset = _require_bool(
                item["amplitude_multiset_exact"], label="amplitude multiset"
            )
            nonidentity = _require_bool(
                item["transformation_nonidentity"], label="amplitude nonidentity"
            )
            expected = (
                "insufficient"
                if not nonidentity
                else (
                    "pass"
                    if multiset and error is not None and error <= 1e-8
                    else "fail"
                )
            )
            _constant(item["state"], expected, label="amplitude observation state")
            states.append(expected)
        return (
            "pass"
            if all(state == "pass" for state in states)
            else ("fail" if "fail" in states else "insufficient")
        )

    if control_id == "orientation_reversal":
        states = []
        for item in observations:
            error = _nonnegative_finite_scalar(item["error_cycles"])
            _constant(item["tolerance_cycles"], 1e-8, label="reversal tolerance")
            _require_sha256(item["receipt_sha256"], label="reversal receipt")
            expected = "pass" if error is not None and error <= 1e-8 else "fail"
            _constant(item["state"], expected, label="reversal observation state")
            states.append(expected)
        return "pass" if all(state == "pass" for state in states) else "fail"

    if control_id == "density_warp_confirmation":
        required_cells = [cells.get(item) for item in contract["required_cell_ids"]]
        required_spans = [spans.get(item) for item in contract["required_span_ids"]]
        cell_values = [
            _nonnegative_finite_scalar(
                item["absolute_error_cycles"] if item is not None else None
            )
            for item in required_cells
        ]
        span_values = [
            _nonnegative_finite_scalar(
                item["graph_family_span_cycles"] if item is not None else None
            )
            for item in required_spans
        ]
        cells_finite = (
            len(required_cells) == 54
            and all(
                item is not None and item["attempt_status"] == "evaluable"
                for item in required_cells
            )
            and all(value is not None for value in cell_values)
        )
        spans_finite = len(required_spans) == 6 and all(
            value is not None for value in span_values
        )
        structural_ok = confirmation_structural["state"] == "pass"
        observation = observations[0]
        _constant(
            observation["confirmation_structural_sha256"],
            canonical_json_sha256(confirmation_structural),
            label="density structural digest",
        )
        _constant(
            observation["state"],
            "pass" if structural_ok else "insufficient",
            label="density structural state",
        )
        _constant(
            row["confirmation_matrix_sha256"],
            canonical_json_sha256(confirmation_matrix),
            label="density confirmation-matrix digest",
        )
        if not structural_ok or not cells_finite or not spans_finite:
            return "insufficient"
        return (
            "pass"
            if all(
                float(value) <= oracle_threshold
                for value in cell_values
                if value is not None
            )
            and all(
                float(value) <= graph_threshold
                for value in span_values
                if value is not None
            )
            else "fail"
        )

    boolean_fields = {
        "joint_vertex_permutation": "vertex_id_edge_content_preserved",
        "ambient_orthogonal_transform": "canonical_adjacency_preserved",
        "global_norm_scaling": "canonical_adjacency_preserved_with_radius_covariance",
    }
    if control_id in boolean_fields:
        states = []
        field = boolean_fields[control_id]
        for item in observations:
            family = str(item["observation_id"]).split("|", 1)[1]
            selected = selected_candidates.get(family)
            if selected is None:
                raise P4RunError(f"{control_id} lacks sealed family edge evidence")
            _constant(
                item["receipt_equality_scope"],
                "constructed-graph-receipt-edge-equality-only",
                label=f"{control_id} evidence scope",
            )
            base_graph = _reconstruct_canonical_graph(
                selected["canonical_edges"], label=f"{control_id} sealed base"
            )
            transformed_graph = _reconstruct_canonical_graph(
                item["transformed_canonical_edges"],
                label=f"{control_id} transformed receipt",
            )
            sealed_order = _require_sha256(
                item["sealed_family_edge_order_sha256"],
                label=f"{control_id} sealed family edge order",
            )
            _constant(
                sealed_order,
                selected["edge_fingerprint_sha256"],
                label=f"{control_id} sealed family binding",
            )
            _constant(
                item["base_edge_order_sha256"],
                sealed_order,
                label=f"{control_id} base family binding",
            )
            _constant(
                item["transformed_edge_order_sha256"],
                transformed_graph["edge_fingerprint_sha256"],
                label=f"{control_id} transformed edge-order derivation",
            )
            base_edges = set(base_graph["edges"])
            transformed_edges = set(transformed_graph["edges"])
            if control_id == "joint_vertex_permutation":
                base_vertex_ids = _sequence(
                    item["base_vertex_ids"], label="joint base vertex ids"
                )
                transformed_vertex_ids = _sequence(
                    item["transformed_vertex_ids"],
                    label="joint transformed vertex ids",
                )
                if (
                    len(base_vertex_ids) != 49
                    or len(set(base_vertex_ids)) != 49
                    or any(type(value) is not int for value in base_vertex_ids)
                ):
                    raise P4RunError(
                        "joint base vertex ids must be 49 unique plain integers"
                    )
                _constant(
                    transformed_vertex_ids,
                    list(reversed(base_vertex_ids)),
                    label="joint frozen reversed vertex ids",
                )
                try:
                    base_vertex_array = np.asarray(base_vertex_ids, dtype="<i8")
                    transformed_vertex_array = np.asarray(
                        transformed_vertex_ids, dtype="<i8"
                    )
                except (OverflowError, ValueError) as error:
                    raise P4RunError("joint vertex ids exceed int64") from error
                base_vertex_order = array_sha256(base_vertex_array)
                transformed_vertex_order = array_sha256(transformed_vertex_array)
                _constant(
                    item["base_vertex_order_sha256"],
                    base_vertex_order,
                    label="joint base vertex-order derivation",
                )
                _constant(
                    base_vertex_order,
                    selected["vertex_order_sha256"],
                    label="joint sealed vertex-order binding",
                )
                _constant(
                    item["transformed_vertex_order_sha256"],
                    transformed_vertex_order,
                    label="joint transformed vertex-order derivation",
                )
                base_id_edges = _vertex_id_edges_from_rows(base_edges, base_vertex_ids)
                transformed_id_edges = _vertex_id_edges_from_rows(
                    transformed_edges, transformed_vertex_ids
                )
                base_content = _row_edge_content_sha256(base_id_edges)
                transformed_content = _row_edge_content_sha256(transformed_id_edges)
                equality = base_id_edges == transformed_id_edges
            else:
                base_content = _row_edge_content_sha256(base_edges)
                transformed_content = _row_edge_content_sha256(transformed_edges)
                equality = base_edges == transformed_edges
            _constant(
                item["base_edge_content_sha256"],
                base_content,
                label=f"{control_id} base edge-content derivation",
            )
            _constant(
                item["transformed_edge_content_sha256"],
                transformed_content,
                label=f"{control_id} transformed edge-content derivation",
            )
            _constant(item[field], equality, label=f"{control_id} derived equality")
            expected = "pass" if equality else "fail"
            _constant(item["state"], expected, label=f"{control_id} observation state")
            states.append(expected)
        return "pass" if all(state == "pass" for state in states) else "fail"

    if control_id == "collapsed_cycleless_phantom":
        path_observation, central, wide = observations
        _constant(
            path_observation["canonical_edges"],
            [[row, row + 1] for row in range(48)],
            label="collapsed exact canonical path edges",
        )
        reconstructed = _reconstruct_canonical_graph(
            path_observation["canonical_edges"], label="collapsed path"
        )
        for key in (
            "edge_count",
            "component_count",
            "largest_component_vertex_count",
            "two_core_vertex_count",
            "cycle_rank",
            "edge_fingerprint_sha256",
        ):
            _constant(
                path_observation[key],
                reconstructed[key],
                label=f"collapsed reconstructed {key}",
            )
        graph_exact = (
            path_observation["edge_count"] == 48
            and path_observation["component_count"] == 1
            and path_observation["largest_component_vertex_count"] == 49
            and path_observation["two_core_vertex_count"] == 0
            and path_observation["cycle_rank"] == 0
        )
        for key in (
            "edge_count",
            "component_count",
            "largest_component_vertex_count",
            "two_core_vertex_count",
            "cycle_rank",
        ):
            _require_plain_nonnegative_int(
                path_observation[key], label=f"collapsed {key}"
            )
        _require_sha256(
            path_observation["edge_fingerprint_sha256"],
            label="collapsed edge fingerprint",
        )
        _require_sha256(
            path_observation["state_sha256"], label="collapsed state digest"
        )
        _constant(
            path_observation["state"],
            "insufficient" if graph_exact else "fail",
            label="collapsed path state",
        )
        unmatched: list[bool] = []
        for item in (central, wide):
            matched = _require_bool(item["matched"], label="collapsed binding matched")
            fingerprint = item["binding_fingerprint_sha256"]
            if matched:
                _require_sha256(fingerprint, label="collapsed binding fingerprint")
            else:
                _constant(fingerprint, "", label="unmatched binding fingerprint")
            _constant(
                item["state"],
                "fail" if matched else "insufficient",
                label="collapsed binding state",
            )
            unmatched.append(not matched)
        return "insufficient" if graph_exact and all(unmatched) else "fail"

    if control_id == "field_only_shuffle":
        states = []
        for item in observations:
            if "reason" in item:
                _constant(
                    item["reason"],
                    "required-blind-cell-missing",
                    label="field shuffle missing reason",
                )
                expected = "fail"
            else:
                base = _require_finite_scalar(
                    item["base_total_cycles"], label="field shuffle base total"
                )
                shuffled = _require_finite_scalar(
                    item["shuffled_total_cycles"],
                    label="field shuffle transformed total",
                )
                error = _nonnegative_finite_scalar(item["sign_reversal_error_cycles"])
                _constant(
                    item["tolerance_cycles"], 1e-8, label="field shuffle tolerance"
                )
                _constant(
                    error, abs(shuffled + base), label="field shuffle recomputed error"
                )
                expected = "pass" if error is not None and error <= 1e-8 else "fail"
            _constant(item["state"], expected, label="field shuffle observation state")
            states.append(expected)
        return (
            "pass"
            if len(states) == 18 and all(state == "pass" for state in states)
            else "fail"
        )

    if control_id in {"zero_amplitude", "low_coherence"}:
        expected_reason = (
            "boundary_amplitude_at_or_below_floor"
            if control_id == "zero_amplitude"
            else "boundary_coherence_at_or_below_floor"
        )
        exact = []
        for item in observations:
            matches = item["reason_codes"] == [expected_reason]
            _constant(
                item["state"],
                "insufficient" if matches else "fail",
                label=f"{control_id} observation state",
            )
            exact.append(matches)
        return "insufficient" if all(exact) else "fail"

    if control_id == "non_orientable_frame":
        odd, companion = observations
        for item in observations:
            _require_sha256(item["receipt_sha256"], label="non-orientable receipt")
        parity_exact = (
            odd["state"] == "insufficient"
            and odd["reason_codes"] == ["orientation-reversing-cycle"]
            and companion["state"] == "fail"
            and companion["reason_codes"] == ["nonorientable-control-did-not-trigger"]
        )
        return "insufficient" if parity_exact else "fail"

    raise P4RunError(f"cannot derive unknown control {control_id}")


def _fold_attempted_controls(
    controls: Sequence[Mapping[str, object]],
    *,
    oracle_ok: bool,
    span_ok: bool,
) -> tuple[str, str]:
    known_ids = {
        "known_positive_connection",
        "zero_holonomy_finite_amplitude_null",
        "radial_amplitude_depression_without_holonomy",
    }
    orientation_ids = {"pure_so2_gauge", "orientation_reversal", "non_orientable_frame"}
    known = [
        str(item["control_verdict"])
        for item in controls
        if item["control_id"] in known_ids
    ]
    orientation = [
        str(item["control_verdict"])
        for item in controls
        if item["control_id"] in orientation_ids
    ]
    other = [
        str(item["control_verdict"])
        for item in controls
        if item["control_id"] not in known_ids | orientation_ids
    ]
    if "fail" in known or (not oracle_ok and "insufficient" not in known):
        return "fail", "known-positive-or-required-null-wrong"
    if "insufficient" in known:
        return "insufficient", "known-positive-or-required-null-unresolved"
    if any(value != "pass" for value in orientation):
        return "insufficient", "orientation-or-reverse-consistency-unresolved"
    if not span_ok or "fail" in other:
        return "fail", "required-control-or-graph-span-wrong"
    if "insufficient" in other:
        return "insufficient", "required-control-unresolved"
    return "pass", "model-free-evaluability-qualified"


def _validate_calibration_algebraic(
    value: object,
) -> tuple[dict[str, object], list[float | None]]:
    algebraic = _mapping(value, label="calibration algebraic")
    _exact_keys(
        algebraic,
        {"pure_so2_gauge", "orientation_reversal"},
        label="calibration algebraic",
    )
    values: list[float | None] = []
    for key in ("pure_so2_gauge", "orientation_reversal"):
        item = _mapping(algebraic[key], label=f"algebraic {key}")
        expected_keys = {"state", "error_cycles", "receipt_sha256"}
        if key == "pure_so2_gauge":
            expected_keys |= {"coordinate_law_error", "coordinate_law_tolerance"}
        _exact_keys(item, expected_keys, label=f"algebraic {key}")
        error = _nonnegative_finite_scalar(item["error_cycles"])
        _require_sha256(item["receipt_sha256"], label=f"algebraic {key} receipt")
        if key == "pure_so2_gauge":
            coordinate_error = _nonnegative_finite_scalar(item["coordinate_law_error"])
            _constant(
                item["coordinate_law_tolerance"],
                1e-8,
                label="algebraic coordinate tolerance",
            )
            expected_state = (
                "insufficient"
                if error is None or coordinate_error is None
                else ("pass" if error <= 1e-8 and coordinate_error <= 1e-8 else "fail")
            )
        else:
            expected_state = (
                "insufficient"
                if error is None
                else ("pass" if error <= 1e-8 else "fail")
            )
        _constant(item["state"], expected_state, label=f"algebraic {key} state")
        values.append(error)
    return algebraic, values


def _calibration_summary(
    matrix: Mapping[str, object],
    algebraic: Mapping[str, object],
) -> dict[str, object]:
    error_values = [
        _nonnegative_finite_scalar(
            _mapping(item, label="calibration cell")["absolute_error_cycles"]
        )
        for item in _sequence(matrix["cells"], label="calibration cells")
    ]
    span_values = [
        _nonnegative_finite_scalar(
            _mapping(item, label="calibration span")["graph_family_span_cycles"]
        )
        for item in _sequence(matrix["graph_family_spans"], label="calibration spans")
    ]
    algebraic_values = [
        _nonnegative_finite_scalar(
            _mapping(algebraic[key], label=f"algebraic {key}")["error_cycles"]
        )
        for key in ("pure_so2_gauge", "orientation_reversal")
    ]
    finite_errors = [value for value in error_values if value is not None]
    finite_spans = [value for value in span_values if value is not None]
    finite_algebraic = [value for value in algebraic_values if value is not None]
    inventory = {
        "absolute_oracle_or_null_error_cycles": len(finite_errors),
        "graph_family_span_cycles": len(finite_spans),
        "pure_so2_gauge_error_cycles": (1 if algebraic_values[0] is not None else 0),
        "orientation_reversal_error_cycles": (
            1 if algebraic_values[1] is not None else 0
        ),
        "total": len(finite_errors) + len(finite_spans) + len(finite_algebraic),
    }
    finite_complete = (
        len(finite_errors) == 54
        and len(finite_spans) == 6
        and len(finite_algebraic) == 2
    )
    return {
        "inventory": inventory,
        "finite_complete": finite_complete,
        "oracle_worst": max(finite_errors) if finite_complete else None,
        "span_worst": max(finite_spans) if finite_complete else None,
        "algebraic_resolved": finite_complete
        and all(
            _mapping(algebraic[key], label=f"algebraic {key}")["state"] == "pass"
            and float(algebraic_values[index]) <= 1e-8
            for index, key in enumerate(("pure_so2_gauge", "orientation_reversal"))
        ),
    }


def _expected_effective_thresholds(
    summary: Mapping[str, object],
    *,
    include_algebraic: bool,
) -> dict[str, object]:
    oracle_worst = float(summary["oracle_worst"])
    span_worst = float(summary["span_worst"])
    oracle_threshold, _oracle_cap = _effective_threshold(oracle_worst, cap=0.05)
    graph_threshold, _graph_cap = _effective_threshold(span_worst, cap=0.1)
    result: dict[str, object] = {
        "oracle_and_null_selection_worst_error_cycles": oracle_worst,
        "graph_family_span_selection_worst_error_cycles": span_worst,
        "oracle_and_null_cycles": oracle_threshold,
        "graph_family_span_cycles": graph_threshold,
    }
    if include_algebraic:
        result["algebraic_gauge_and_reversal_error_cycles"] = 1e-8
    return result


def _validate_not_run_controls_reason(
    controls: Sequence[Mapping[str, object]],
    *,
    reason: str,
) -> None:
    for row in controls:
        _constant(
            row["upstream_reason"],
            reason,
            label=f"{row['control_id']} upstream reason",
        )


def _validate_not_run_result_branch(
    result: Mapping[str, object],
    controls: Sequence[Mapping[str, object]],
) -> None:
    state = result["terminal_state"]
    reason = result["reason"]
    if state == "invalid":
        _constant(reason, "caught-execution-error", label="caught invalid reason")
        for key in (
            "calibration_selector",
            "calibration_matrix",
            "calibration_algebraic_diagnostics",
            "calibration_scalar_inventory",
            "effective_thresholds",
            "confirmation_structural",
            "confirmation_matrix",
        ):
            _constant(result[key], None, label=f"caught invalid {key}")
        _validate_not_run_controls_reason(controls, reason="caught-execution-error")
        return

    _constant(state, "insufficient", label="not-run terminal state")
    selector = _validate_selector_projection(result["calibration_selector"])
    if reason == "no-distinct-three-family-scale-triplet":
        _constant(selector["state"], "insufficient", label="selector-stop state")
        _constant(
            result["graph_selection_sealed"], True, label="selector-stop graph seal"
        )
        _constant(
            result["threshold_decision_sealed"],
            False,
            label="selector-stop threshold seal",
        )
        _constant(result["confirmation_accessed"], False, label="selector-stop access")
        for key in (
            "calibration_matrix",
            "calibration_algebraic_diagnostics",
            "calibration_scalar_inventory",
            "effective_thresholds",
            "confirmation_structural",
            "confirmation_matrix",
        ):
            _constant(result[key], None, label=f"selector-stop {key}")
        _validate_not_run_controls_reason(controls, reason=reason)
        return

    _constant(selector["state"], "pass", label="post-selector state")
    _constant(result["graph_selection_sealed"], True, label="post-selector graph seal")
    _constant(
        result["threshold_decision_sealed"], True, label="post-selector threshold seal"
    )
    calibration_matrix = _validate_matrix_projection(
        result["calibration_matrix"],
        role="calibration",
        sealed_selected=_sequence(selector["selected"], label="selector selected"),
    )
    algebraic, _values = _validate_calibration_algebraic(
        result["calibration_algebraic_diagnostics"]
    )
    summary = _calibration_summary(calibration_matrix, algebraic)
    _constant(
        result["calibration_scalar_inventory"],
        summary["inventory"],
        label="calibration scalar inventory",
    )
    if not bool(summary["finite_complete"]):
        _constant(
            reason,
            "insufficient_calibration_resolution",
            label="nonfinite calibration reason",
        )
        _constant(result["effective_thresholds"], None, label="nonfinite thresholds")
        _constant(result["confirmation_accessed"], False, label="nonfinite access")
        _constant(result["confirmation_structural"], None, label="nonfinite structural")
        _constant(
            result["confirmation_matrix"], None, label="nonfinite confirmation matrix"
        )
        _validate_not_run_controls_reason(
            controls, reason="insufficient-calibration-resolution"
        )
        return

    expected_four = _expected_effective_thresholds(summary, include_algebraic=False)
    oracle_threshold = float(expected_four["oracle_and_null_cycles"])
    graph_threshold = float(expected_four["graph_family_span_cycles"])
    oracle_cap = oracle_threshold <= 0.05
    graph_cap = graph_threshold <= 0.1
    algebraic_resolved = bool(summary["algebraic_resolved"])
    if not algebraic_resolved or not oracle_cap or not graph_cap:
        expected_reason = (
            "orientation-or-reverse-consistency-unresolved"
            if not algebraic_resolved
            else "insufficient_calibration_resolution"
        )
        _constant(reason, expected_reason, label="calibration gate reason")
        _constant(
            result["effective_thresholds"],
            expected_four,
            label="calibration gate thresholds",
        )
        _constant(
            result["confirmation_accessed"], False, label="calibration gate access"
        )
        _constant(
            result["confirmation_structural"], None, label="calibration gate structural"
        )
        _constant(result["confirmation_matrix"], None, label="calibration gate matrix")
        _validate_not_run_controls_reason(
            controls, reason=expected_reason.replace("_", "-")
        )
        return

    _constant(
        reason,
        "held-out-confirmation-structural-gate",
        label="held-out structural reason",
    )
    _constant(result["confirmation_accessed"], True, label="structural access")
    _constant(
        result["effective_thresholds"],
        _expected_effective_thresholds(summary, include_algebraic=True),
        label="structural-stop thresholds",
    )
    _validate_confirmation_structural_projection(
        result["confirmation_structural"],
        selector=selector,
        expected_state="insufficient",
    )
    _constant(result["confirmation_matrix"], None, label="structural-stop matrix")
    _validate_not_run_controls_reason(controls, reason=reason)


def _normalize_result(value: Mapping[str, object]) -> dict[str, object]:
    result = _mapping(value, label="terminal result")
    _exact_keys(result, RESULT_KEYS, label="terminal result")
    controls = result["controls"]
    if not isinstance(controls, list) or len(controls) != len(
        EXPECTED_RAW_CONTROL_STATES
    ):
        raise P4RunError("terminal result must carry all 16 control rows")
    control_rows = [_mapping(item, label="terminal control") for item in controls]
    observed_ids = [str(item["control_id"]) for item in control_rows]
    if observed_ids != list(EXPECTED_RAW_CONTROL_STATES):
        raise P4RunError("terminal controls are not in frozen canonical order")
    if type(result["terminal_state"]) is not str or result["terminal_state"] not in {
        "pass",
        "fail",
        "insufficient",
        "invalid",
    }:
        raise P4RunError("terminal_state is outside the closed vocabulary")
    if type(result["reason"]) is not str or not result["reason"]:
        raise P4RunError("terminal reason must be a nonempty string")
    if type(result["confirmation_accessed"]) is not bool:
        raise P4RunError("confirmation_accessed must be a closed boolean")
    if type(result["graph_selection_sealed"]) is not bool:
        raise P4RunError("graph_selection_sealed must be a closed boolean")
    if type(result["threshold_decision_sealed"]) is not bool:
        raise P4RunError("threshold_decision_sealed must be a closed boolean")
    if result["confirmation_accessed"] and not result["threshold_decision_sealed"]:
        raise P4RunError("confirmation access requires a sealed threshold decision")
    if result["threshold_decision_sealed"] and not result["graph_selection_sealed"]:
        raise P4RunError("threshold decision requires sealed graph selection")
    for flag, digest_key in (
        ("graph_selection_sealed", "graph_selection_seal_sha256"),
        ("threshold_decision_sealed", "threshold_seal_sha256"),
        ("confirmation_accessed", "confirmation_access_seal_sha256"),
    ):
        digest = result[digest_key]
        if result[flag]:
            if (
                type(digest) is not str
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                raise P4RunError(f"{digest_key} must be a lowercase SHA-256")
        elif digest is not None:
            raise P4RunError(f"{digest_key} must be null before its seal exists")
    contracts = {
        str(item["control_id"]): item for item in _control_contracts_document()
    }
    attempted_values: list[bool] = []
    for row in control_rows:
        control_id = str(row["control_id"])
        if type(row.get("attempted")) is not bool:
            raise P4RunError(f"{control_id}.attempted must be boolean")
        attempted = bool(row["attempted"])
        attempted_values.append(attempted)
        expected_raw = EXPECTED_RAW_CONTROL_STATES[control_id]
        _constant(
            row.get("expected_raw_state"), expected_raw, label=f"{control_id} expected"
        )
        if attempted:
            base_attempted_keys = {
                "control_id",
                "attempted",
                "expected_raw_state",
                "raw_state",
                "control_verdict",
                "control_contract_sha256",
                "required_cell_count",
                "required_cell_ids_sha256",
                "required_span_count",
                "required_span_ids_sha256",
                "required_observation_count",
                "required_observation_ids_sha256",
                "observations",
            }
            extras = {
                "known_positive_connection": {
                    "observed_cell_count",
                    "worst_error_cycles",
                    "oracle_and_null_threshold_cycles",
                },
                "zero_holonomy_finite_amplitude_null": {
                    "observed_cell_count",
                    "worst_error_cycles",
                    "oracle_and_null_threshold_cycles",
                    "nuisance_diagnostics",
                },
                "radial_amplitude_depression_without_holonomy": {
                    "observed_cell_count",
                    "worst_error_cycles",
                    "oracle_and_null_threshold_cycles",
                    "nuisance_diagnostics",
                },
                "density_warp_confirmation": {"confirmation_matrix_sha256"},
            }.get(control_id, set())
            _exact_keys(
                row,
                base_attempted_keys | extras,
                label=f"{control_id} attempted row",
            )
            if row.get("raw_state") not in {"pass", "fail", "insufficient"}:
                raise P4RunError(f"{control_id} raw_state is outside the vocabulary")
            expected_verdict = (
                "pass"
                if row["raw_state"] == expected_raw
                else ("insufficient" if row["raw_state"] == "insufficient" else "fail")
            )
            _constant(
                row.get("control_verdict"),
                expected_verdict,
                label=f"{control_id} verdict",
            )
            contract = contracts[control_id]
            _constant(
                row.get("control_contract_sha256"),
                canonical_json_sha256(contract),
                label=f"{control_id} contract digest",
            )
            _constant(
                row.get("required_cell_count"),
                len(contract["required_cell_ids"]),
                label=f"{control_id} required cell count",
            )
            _constant(
                row.get("required_span_count"),
                len(contract["required_span_ids"]),
                label=f"{control_id} required span count",
            )
            _constant(
                row.get("required_observation_count"),
                len(contract["required_observation_ids"]),
                label=f"{control_id} observation count",
            )
            _constant(
                row.get("required_cell_ids_sha256"),
                canonical_json_sha256(contract["required_cell_ids"]),
                label=f"{control_id} required-cell digest",
            )
            _constant(
                row.get("required_span_ids_sha256"),
                canonical_json_sha256(contract["required_span_ids"]),
                label=f"{control_id} required-span digest",
            )
            _constant(
                row.get("required_observation_ids_sha256"),
                canonical_json_sha256(contract["required_observation_ids"]),
                label=f"{control_id} required-observation digest",
            )
            observations = _sequence(
                row.get("observations"), label=f"{control_id} observations"
            )
            observation_ids = [
                str(_mapping(item, label="control observation").get("observation_id"))
                for item in observations
            ]
            _constant(
                observation_ids,
                contract["required_observation_ids"],
                label=f"{control_id} observation ids",
            )
            for observation in observations:
                item = _mapping(observation, label=f"{control_id} observation")
                observation_id = str(item["observation_id"])
                expected_keys = _observation_keys(observation_id, item.get("state"))
                if (
                    control_id == "field_only_shuffle"
                    and item.get("state") == "fail"
                    and "reason" not in item
                ):
                    expected_keys = {
                        "observation_id",
                        "state",
                        "base_total_cycles",
                        "shuffled_total_cycles",
                        "sign_reversal_error_cycles",
                        "tolerance_cycles",
                    }
                _exact_keys(item, expected_keys, label=f"{observation_id} payload")
                if item.get("state") not in {"pass", "fail", "insufficient"}:
                    raise P4RunError(f"{observation_id} state is invalid")
            if control_id == "zero_holonomy_finite_amplitude_null":
                nuisance = _mapping(
                    row["nuisance_diagnostics"], label=f"{control_id} nuisance"
                )
                _exact_keys(
                    nuisance,
                    {
                        "definition",
                        "amplitude_floor",
                        "minimum_loop_boundary_amplitude",
                        "finite",
                        "passes",
                    },
                    label=f"{control_id} nuisance",
                )
                _constant(
                    nuisance["definition"],
                    "no_core_finite_loop_boundary_amplitude",
                    label=f"{control_id} nuisance definition",
                )
                _constant(
                    nuisance["amplitude_floor"],
                    1e-12,
                    label=f"{control_id} amplitude floor",
                )
                if (
                    type(nuisance["finite"]) is not bool
                    or type(nuisance["passes"]) is not bool
                ):
                    raise P4RunError(f"{control_id} nuisance flags must be boolean")
                minimum = _nonnegative_finite_scalar(
                    nuisance["minimum_loop_boundary_amplitude"]
                )
                _constant(
                    nuisance["finite"],
                    minimum is not None,
                    label=f"{control_id} nuisance finite",
                )
                _constant(
                    nuisance["passes"],
                    minimum is not None and minimum > 1e-12,
                    label=f"{control_id} nuisance pass",
                )
            elif control_id == "radial_amplitude_depression_without_holonomy":
                nuisance = _mapping(
                    row["nuisance_diagnostics"], label=f"{control_id} nuisance"
                )
                _exact_keys(
                    nuisance,
                    {
                        "definition",
                        "amplitude_floor",
                        "center_amplitude_count",
                        "maximum_center_amplitude",
                        "minimum_loop_boundary_amplitude",
                        "finite",
                        "passes",
                    },
                    label=f"{control_id} nuisance",
                )
                _constant(
                    nuisance["definition"],
                    "fixed_null_depressed_center_finite_loop_boundary",
                    label=f"{control_id} nuisance definition",
                )
                _constant(
                    nuisance["amplitude_floor"],
                    1e-12,
                    label=f"{control_id} amplitude floor",
                )
                if type(nuisance["center_amplitude_count"]) is not int:
                    raise P4RunError(f"{control_id} center count must be integer")
                if (
                    type(nuisance["finite"]) is not bool
                    or type(nuisance["passes"]) is not bool
                ):
                    raise P4RunError(f"{control_id} nuisance flags must be boolean")
                maximum = _nonnegative_finite_scalar(
                    nuisance["maximum_center_amplitude"]
                )
                minimum = _nonnegative_finite_scalar(
                    nuisance["minimum_loop_boundary_amplitude"]
                )
                finite_expected = (
                    nuisance["center_amplitude_count"] == 3
                    and maximum is not None
                    and minimum is not None
                )
                _constant(
                    nuisance["finite"],
                    finite_expected,
                    label=f"{control_id} nuisance finite",
                )
                _constant(
                    nuisance["passes"],
                    finite_expected and maximum <= 1e-12 and minimum > 1e-12,
                    label=f"{control_id} nuisance pass",
                )
        else:
            _exact_keys(
                row,
                {
                    "control_id",
                    "attempted",
                    "expected_raw_state",
                    "raw_state",
                    "control_verdict",
                    "upstream_reason",
                },
                label=f"{control_id} not-run row",
            )
            _constant(row["raw_state"], "not_run", label=f"{control_id} raw state")
            _constant(row["control_verdict"], "not_run", label=f"{control_id} verdict")
            if type(row["upstream_reason"]) is not str or not row["upstream_reason"]:
                raise P4RunError(f"{control_id} upstream reason must be nonempty")
    if any(attempted_values) and not all(attempted_values):
        raise P4RunError("controls must be all attempted or all not-run")
    if all(attempted_values):
        _constant(
            result["confirmation_accessed"], True, label="attempted confirmation access"
        )
        _constant(result["graph_selection_sealed"], True, label="attempted graph seal")
        _constant(
            result["threshold_decision_sealed"], True, label="attempted threshold seal"
        )
        selector = _validate_selector_projection(result["calibration_selector"])
        _constant(selector["state"], "pass", label="attempted-control selector state")
        selector_selected = _sequence(selector["selected"], label="selector selected")
        calibration_matrix = _validate_matrix_projection(
            result["calibration_matrix"],
            role="calibration",
            sealed_selected=selector_selected,
        )
        structural = _validate_confirmation_structural_projection(
            result["confirmation_structural"],
            selector=selector,
            expected_state="pass",
        )
        confirmation_matrix = _validate_matrix_projection(
            result["confirmation_matrix"],
            role="confirmation",
            sealed_selected=_sequence(
                structural["selected"], label="confirmation selected"
            ),
        )
        algebraic, _algebraic_values = _validate_calibration_algebraic(
            result["calibration_algebraic_diagnostics"]
        )
        summary = _calibration_summary(calibration_matrix, algebraic)
        _constant(
            result["calibration_scalar_inventory"],
            summary["inventory"],
            label="terminal scalar inventory",
        )
        if not bool(summary["finite_complete"]) or not bool(
            summary["algebraic_resolved"]
        ):
            raise P4RunError("attempted controls require complete resolved calibration")
        oracle_worst = float(summary["oracle_worst"])
        span_worst = float(summary["span_worst"])
        oracle_threshold, oracle_cap = _effective_threshold(oracle_worst, cap=0.05)
        graph_threshold, graph_cap = _effective_threshold(span_worst, cap=0.1)
        if not oracle_cap or not graph_cap:
            raise P4RunError(
                "attempted controls require calibration thresholds within caps"
            )
        _constant(
            result["effective_thresholds"],
            _expected_effective_thresholds(summary, include_algebraic=True),
            label="effective thresholds",
        )
        confirmation_errors = [
            _nonnegative_finite_scalar(item["absolute_error_cycles"])
            for item in confirmation_matrix["cells"]
        ]
        confirmation_spans = [
            _nonnegative_finite_scalar(item["graph_family_span_cycles"])
            for item in confirmation_matrix["graph_family_spans"]
        ]
        oracle_ok = all(
            value is not None and value <= oracle_threshold
            for value in confirmation_errors
        )
        span_ok = all(
            value is not None and value <= graph_threshold
            for value in confirmation_spans
        )
        for row in control_rows:
            control_id = str(row["control_id"])
            derived_raw = _derive_control_raw_state(
                control_id,
                row,
                selected_candidates={
                    str(item["family"]): item for item in selector_selected
                },
                confirmation_matrix=confirmation_matrix,
                confirmation_structural=structural,
                oracle_threshold=oracle_threshold,
                graph_threshold=graph_threshold,
            )
            _constant(
                row["raw_state"], derived_raw, label=f"{control_id} derived raw state"
            )
            expected_raw = EXPECTED_RAW_CONTROL_STATES[control_id]
            derived_verdict = (
                "pass"
                if derived_raw == expected_raw
                else ("insufficient" if derived_raw == "insufficient" else "fail")
            )
            _constant(
                row["control_verdict"],
                derived_verdict,
                label=f"{control_id} derived verdict",
            )
        folded_state, folded_reason = _fold_attempted_controls(
            control_rows, oracle_ok=oracle_ok, span_ok=span_ok
        )
        _constant(
            result["terminal_state"], folded_state, label="terminal attempted fold"
        )
        _constant(result["reason"], folded_reason, label="terminal attempted reason")
    else:
        _validate_not_run_result_branch(result, control_rows)
    return result


def _build_terminal(
    *,
    base: Mapping[str, object],
    attempt_sha256: str,
    execution_terminal: str,
    error: object,
    result: Mapping[str, object],
) -> dict[str, object]:
    if execution_terminal == "complete":
        if error is not None or result.get("terminal_state") == "invalid":
            raise P4RunError(
                "complete terminal requires non-invalid result and null error"
            )
    elif execution_terminal == "caught_error":
        if result.get("terminal_state") != "invalid":
            raise P4RunError("caught_error requires invalid result")
        error_mapping = _mapping(error, label="caught error")
        _exact_keys(error_mapping, {"class", "message_sha256"}, label="caught error")
        if type(error_mapping["class"]) is not str:
            raise P4RunError("caught error class must be a string")
        message_digest = error_mapping["message_sha256"]
        if type(message_digest) is not str or len(message_digest) != 64:
            raise P4RunError("caught error message digest is malformed")
    else:
        raise P4RunError("execution_terminal is outside the closed vocabulary")
    terminal = {
        **base,
        "attempt_sha256": attempt_sha256,
        "execution_terminal": execution_terminal,
        "error": error,
        "result": _normalize_result(result),
    }
    expected_keys = {
        "schema_version",
        "experiment_id",
        "protocol_sha256",
        "runner_sha256",
        "launch_sha256",
        "source_commit",
        "attempt_sha256",
        "execution_terminal",
        "error",
        "result",
        "operator_prior_outcome_exposure",
        "cryptographic_unseen",
        "development_only",
        "independent",
        "claim_ceiling",
        "scientific_authority",
        "topology_authority",
        "integer_output_present",
        "model_accessed",
        "network_accessed",
        "cache_accessed",
        "cache_access_scope",
        "python_bytecode_cache_accessed",
        "python_process_pre_import_observation",
        "python_process_post_import_observation",
        "python_process_post_execution_observation",
        "source_closure_pre_sha256",
        "source_closure_post_sha256",
        "pythia_raw_capture_accessed",
        "subject_data_accessed",
        "dynamic_timestamp_present",
    }
    if set(terminal) != expected_keys:
        raise P4RunError("terminal root differs from the closed schema")
    return terminal


def prepare_launch(repo_root: Path) -> dict[str, object]:
    """Publish a launch descriptor without constructing official inputs."""

    root = repo_root.resolve()
    preparation_observation = _validated_current_python_process(
        root, mode="--prepare-launch"
    )
    _constant(
        _BOOTSTRAP_PRE_IMPORT_PYTHON_OBSERVATION,
        preparation_observation,
        label="pre-import prepare-launch Python process observation",
    )
    _constant(
        _BOOTSTRAP_POST_IMPORT_PYTHON_OBSERVATION,
        preparation_observation,
        label="post-import prepare-launch Python process observation",
    )
    protocol = load_and_validate_protocol(root)
    sources = _source_paths(protocol)
    _require_clean_worktree(root)
    _require_import_root(root)
    for path in sources:
        _require_regular_head_file(root, path)
    for path in (
        root / REPOSITORY_LAUNCH,
        root / REPOSITORY_ATTEMPT,
        root / REPOSITORY_TERMINAL,
        EXTERNAL_STAGE,
        EXTERNAL_STORE,
    ):
        if not _entry_absent(path):
            raise P4ProtocolError(f"launch/terminal namespace is not absent: {path}")
    primitive = _probe_native_no_replace()
    source_commit = _git(root, "rev-parse", "HEAD").strip()
    launch = {
        "schema_version": LAUNCH_SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "status": "launch_prepared_not_run",
        "source_commit": source_commit,
        "protocol": {
            "path": str(REPOSITORY_PROTOCOL),
            "sha256": _sha256_file(root / REPOSITORY_PROTOCOL),
        },
        "runner": {
            "path": str(REPOSITORY_RUNNER),
            "sha256": _sha256_file(root / REPOSITORY_RUNNER),
        },
        "authority": {
            "path": str(REPOSITORY_HYPOTHESES),
            "sha256": NEXT_HYPOTHESES_SHA256,
        },
        "coordinates": {
            "launch_path": str(REPOSITORY_LAUNCH),
            "repository_attempt_path": str(REPOSITORY_ATTEMPT),
            "repository_terminal_path": str(REPOSITORY_TERMINAL),
            "external_staging_path": str(EXTERNAL_STAGE),
            "external_store_path": str(EXTERNAL_STORE),
            "attempt_record_name": ATTEMPT_NAME,
            "graph_selection_seal_name": GRAPH_SELECTION_SEAL_NAME,
            "threshold_seal_name": THRESHOLD_SEAL_NAME,
            "confirmation_access_seal_name": CONFIRMATION_ACCESS_SEAL_NAME,
            "terminal_name": TERMINAL_NAME,
            "store_manifest_name": STORE_MANIFEST_NAME,
            "python_bytecode_cache_prefix": str(_python_bytecode_cache_prefix(root)),
        },
        "exact_argv": _exact_run_argv(root),
        "runtime": _runtime_binding(
            root,
            protocol,
            preparation_observation=preparation_observation,
        ),
        "authorizations": {
            "operator_authorized_exact_one_attempt": True,
            "execution_authorized": True,
            "model_access_authorized": False,
            "network_access_authorized": False,
            "cache_access_authorized": False,
            "python_bytecode_cache_access_authorized": False,
            "pythia_raw_capture_access_authorized": False,
            "subject_data_access_authorized": False,
        },
        "absence_precondition": {
            "external_staging_absent": True,
            "external_store_absent": True,
            "repository_attempt_absent": True,
            "repository_terminal_absent": True,
            "python_bytecode_cache_prefix_absent": True,
        },
        "native_no_replace_primitive": primitive,
        "chronology": {
            "source_committed_before_launch_prepare": True,
            "launch_committed_before_execution_required": True,
            "official_phantom_constructed": False,
            "selector_executed": False,
            "confirmation_accessed": False,
            "operator_prior_outcome_exposure": True,
            "cryptographic_unseen": False,
            "independent": False,
        },
        "exact_one": {
            "attempt_exactly_one": True,
            "terminal_at_most_one": True,
            "terminal_guaranteed": False,
            "terminal_no_replace": True,
            "retry_resume_rescue_authorized": False,
            "projection_only_repair_authorized": True,
            "unresolved_stage_consumes_attempt": True,
            "unresolved_stage_terminalization_authorized": False,
            "unresolved_stage_retry_resume_rescue_authorized": False,
        },
    }
    source = canonical_json_bytes(launch)
    _write_exclusive(root / REPOSITORY_LAUNCH, source)
    return launch


def validate_committed_launch(
    repo_root: Path,
    *,
    require_exact_argv: bool = False,
    projection_repair: bool = False,
) -> tuple[dict[str, object], dict[str, object]]:
    """Validate committed launch and output absence without phantom access."""

    root = repo_root.resolve()
    protocol = load_and_validate_protocol(root)
    launch = _load_canonical(root / REPOSITORY_LAUNCH, label="P4 launch")
    _exact_keys(
        launch,
        {
            "schema_version",
            "experiment_id",
            "status",
            "source_commit",
            "protocol",
            "runner",
            "authority",
            "coordinates",
            "exact_argv",
            "runtime",
            "authorizations",
            "absence_precondition",
            "native_no_replace_primitive",
            "chronology",
            "exact_one",
        },
        label="P4 launch",
    )
    if (
        _tracked_head_bytes(root, REPOSITORY_LAUNCH)
        != (root / REPOSITORY_LAUNCH).read_bytes()
    ):
        raise P4ProtocolError("launch is not committed byte-identically at HEAD")
    if projection_repair:
        _require_clean_except_projections(root)
    else:
        _require_clean_worktree(root)
    _require_import_root(root)
    for path in (*_source_paths(protocol), REPOSITORY_LAUNCH):
        _require_regular_head_file(root, path)
    _constant(
        launch.get("schema_version"), LAUNCH_SCHEMA_VERSION, label="launch schema"
    )
    _constant(launch.get("experiment_id"), EXPERIMENT_ID, label="launch experiment")
    _constant(launch.get("status"), "launch_prepared_not_run", label="launch status")
    source_commit = launch.get("source_commit")
    if not isinstance(source_commit, str) or len(source_commit) != 40:
        raise P4ProtocolError("launch source_commit is malformed")
    if (
        _git_completed(
            root,
            "merge-base",
            "--is-ancestor",
            source_commit,
            "HEAD",
        ).returncode
        != 0
    ):
        raise P4ProtocolError("launch source_commit is not an ancestor of HEAD")
    if (
        _git_completed(
            root,
            "cat-file",
            "-e",
            f"{source_commit}:{REPOSITORY_LAUNCH}",
        ).returncode
        == 0
    ):
        raise P4ProtocolError("launch already existed in its bound source commit")
    changed_paths = set(
        _split_nul(
            _git_bytes(
                root,
                "diff",
                "--name-only",
                "-z",
                f"{source_commit}..HEAD",
            ),
            label="Git source-to-launch diff",
        )
    )
    allowed_post_source_paths = {
        REPOSITORY_LAUNCH.as_posix(),
        REPOSITORY_ATTEMPT.as_posix(),
        REPOSITORY_TERMINAL.as_posix(),
    }
    if (
        REPOSITORY_LAUNCH.as_posix() not in changed_paths
        or not changed_paths <= allowed_post_source_paths
        or (not projection_repair and changed_paths != {REPOSITORY_LAUNCH.as_posix()})
    ):
        raise P4ProtocolError(
            "post-source commits may contain only launch and validated projections"
        )
    for path in _source_paths(protocol):
        committed_source = _tracked_commit_bytes(root, source_commit, path)
        live_source = (root / path).read_bytes()
        if committed_source != live_source:
            raise P4ProtocolError(
                f"bound source bytes differ from source_commit: {path}"
            )
    protocol_binding = _mapping(launch.get("protocol"), label="launch.protocol")
    runner_binding = _mapping(launch.get("runner"), label="launch.runner")
    _constant(
        protocol_binding,
        {
            "path": str(REPOSITORY_PROTOCOL),
            "sha256": _sha256_file(root / REPOSITORY_PROTOCOL),
        },
        label="launch protocol binding",
    )
    _constant(
        runner_binding,
        {
            "path": str(REPOSITORY_RUNNER),
            "sha256": _sha256_file(root / REPOSITORY_RUNNER),
        },
        label="launch runner binding",
    )
    _constant(
        launch.get("authority"),
        {
            "path": str(REPOSITORY_HYPOTHESES),
            "sha256": NEXT_HYPOTHESES_SHA256,
        },
        label="launch authority binding",
    )
    _constant(
        launch.get("runtime"),
        _runtime_binding(root, protocol),
        label="runtime binding",
    )
    _validate_exact_run_argv(
        launch.get("exact_argv"), repo_root=root, label="exact argv"
    )
    if require_exact_argv:
        observed_process = _validated_current_python_process(root, mode="--run")
        observed_argv = [
            str(observed_process["logical_executable"]),
            *_sequence(
                observed_process["orig_argv_tail"],
                label="observed run orig argv tail",
            ),
        ]
        _validate_exact_run_argv(
            observed_argv, repo_root=root, label="observed run argv"
        )
    _constant(
        launch.get("native_no_replace_primitive"),
        _probe_native_no_replace(),
        label="native no-replace primitive",
    )
    coordinates = _mapping(launch.get("coordinates"), label="launch.coordinates")
    _constant(
        coordinates,
        {
            "launch_path": str(REPOSITORY_LAUNCH),
            "repository_attempt_path": str(REPOSITORY_ATTEMPT),
            "repository_terminal_path": str(REPOSITORY_TERMINAL),
            "external_staging_path": str(EXTERNAL_STAGE),
            "external_store_path": str(EXTERNAL_STORE),
            "attempt_record_name": ATTEMPT_NAME,
            "graph_selection_seal_name": GRAPH_SELECTION_SEAL_NAME,
            "threshold_seal_name": THRESHOLD_SEAL_NAME,
            "confirmation_access_seal_name": CONFIRMATION_ACCESS_SEAL_NAME,
            "terminal_name": TERMINAL_NAME,
            "store_manifest_name": STORE_MANIFEST_NAME,
            "python_bytecode_cache_prefix": str(_python_bytecode_cache_prefix(root)),
        },
        label="launch coordinates",
    )
    _constant(
        launch.get("authorizations"),
        {
            "operator_authorized_exact_one_attempt": True,
            "execution_authorized": True,
            "model_access_authorized": False,
            "network_access_authorized": False,
            "cache_access_authorized": False,
            "python_bytecode_cache_access_authorized": False,
            "pythia_raw_capture_access_authorized": False,
            "subject_data_access_authorized": False,
        },
        label="launch authorizations",
    )
    _constant(
        launch.get("absence_precondition"),
        {
            "external_staging_absent": True,
            "external_store_absent": True,
            "repository_attempt_absent": True,
            "repository_terminal_absent": True,
            "python_bytecode_cache_prefix_absent": True,
        },
        label="launch absence precondition",
    )
    _constant(
        launch.get("exact_one"),
        {
            "attempt_exactly_one": True,
            "terminal_at_most_one": True,
            "terminal_guaranteed": False,
            "terminal_no_replace": True,
            "retry_resume_rescue_authorized": False,
            "projection_only_repair_authorized": True,
            "unresolved_stage_consumes_attempt": True,
            "unresolved_stage_terminalization_authorized": False,
            "unresolved_stage_retry_resume_rescue_authorized": False,
        },
        label="launch exact one",
    )
    _constant(
        launch.get("chronology"),
        {
            "source_committed_before_launch_prepare": True,
            "launch_committed_before_execution_required": True,
            "official_phantom_constructed": False,
            "selector_executed": False,
            "confirmation_accessed": False,
            "operator_prior_outcome_exposure": True,
            "cryptographic_unseen": False,
            "independent": False,
        },
        label="launch chronology",
    )
    if not projection_repair:
        for path in (
            root / REPOSITORY_ATTEMPT,
            root / REPOSITORY_TERMINAL,
            EXTERNAL_STAGE,
            EXTERNAL_STORE,
        ):
            if not _entry_absent(path):
                raise P4ProtocolError(f"terminal namespace is not absent: {path}")
    return protocol, launch


def _read_regular_canonical_document(
    path: Path, *, label: str
) -> tuple[bytes, dict[str, object]]:
    metadata = os.lstat(path)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise P4ProtocolError(f"{label} must be a regular nlink=1 file")
    if metadata.st_size > CANONICAL_BYTE_LIMIT:
        raise P4ProtocolError(f"{label} exceeds the canonical byte limit")
    source = path.read_bytes()
    try:
        parsed = parse_canonical_json(source, label=label)
    except ValueError as error:
        raise P4ProtocolError(f"{label} is not canonical: {error}") from error
    return source, _mapping(parsed, label=label)


def _validate_attempt_document(
    attempt: Mapping[str, object],
    *,
    repo_root: Path,
    launch: Mapping[str, object],
) -> None:
    launch_sha256 = canonical_json_sha256(launch)
    _constant(
        dict(attempt),
        {
            "schema_version": ATTEMPT_SCHEMA_VERSION,
            "experiment_id": EXPERIMENT_ID,
            "launch_sha256": launch_sha256,
            "source_commit": launch["source_commit"],
            "protocol_sha256": _sha256_file(repo_root / REPOSITORY_PROTOCOL),
            "runner_sha256": _sha256_file(repo_root / REPOSITORY_RUNNER),
            "identity_consumed": True,
            "official_input_access_before_attempt": False,
            "attempt_exactly_one": True,
            "terminal_at_most_one": True,
            "terminal_guaranteed": False,
            "unresolved_stage_consumes_attempt": True,
            "retry_resume_rescue_authorized": False,
        },
        label="external attempt",
    )


def _validate_terminal_document(
    terminal: Mapping[str, object],
    *,
    repo_root: Path,
    launch: Mapping[str, object],
    attempt_sha256: str,
) -> None:
    item = dict(terminal)
    expected_keys = {
        "schema_version",
        "experiment_id",
        "protocol_sha256",
        "runner_sha256",
        "launch_sha256",
        "source_commit",
        "attempt_sha256",
        "execution_terminal",
        "error",
        "result",
        "operator_prior_outcome_exposure",
        "cryptographic_unseen",
        "development_only",
        "independent",
        "claim_ceiling",
        "scientific_authority",
        "topology_authority",
        "integer_output_present",
        "model_accessed",
        "network_accessed",
        "cache_accessed",
        "cache_access_scope",
        "python_bytecode_cache_accessed",
        "python_process_pre_import_observation",
        "python_process_post_import_observation",
        "python_process_post_execution_observation",
        "source_closure_pre_sha256",
        "source_closure_post_sha256",
        "pythia_raw_capture_accessed",
        "subject_data_accessed",
        "dynamic_timestamp_present",
    }
    _exact_keys(item, expected_keys, label="external terminal")
    static_expected = {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "protocol_sha256": _sha256_file(repo_root / REPOSITORY_PROTOCOL),
        "runner_sha256": _sha256_file(repo_root / REPOSITORY_RUNNER),
        "launch_sha256": canonical_json_sha256(launch),
        "source_commit": launch["source_commit"],
        "attempt_sha256": attempt_sha256,
        "operator_prior_outcome_exposure": True,
        "cryptographic_unseen": False,
        "development_only": True,
        "independent": False,
        "claim_ceiling": "level_0",
        "scientific_authority": False,
        "topology_authority": False,
        "integer_output_present": False,
        "model_accessed": False,
        "network_accessed": False,
        "cache_accessed": False,
        "cache_access_scope": "model-or-subject-data-cache-only",
        "python_bytecode_cache_accessed": False,
        "python_process_pre_import_observation": (
            _expected_python_process_observation(repo_root, mode="--run")
        ),
        "python_process_post_import_observation": (
            _expected_python_process_observation(repo_root, mode="--run")
        ),
        "python_process_post_execution_observation": (
            _expected_python_process_observation(repo_root, mode="--run")
        ),
        "source_closure_pre_sha256": _mapping(
            launch["runtime"], label="launch runtime"
        )["source_closure_sha256"],
        "source_closure_post_sha256": _mapping(
            launch["runtime"], label="launch runtime"
        )["source_closure_sha256"],
        "pythia_raw_capture_accessed": False,
        "subject_data_accessed": False,
        "dynamic_timestamp_present": False,
    }
    for key, expected in static_expected.items():
        _constant(item[key], expected, label=f"external terminal {key}")
    terminal_result = _mapping(item["result"], label="external terminal result")
    persisted_selector = terminal_result.get("calibration_selector")
    if persisted_selector is not None:
        frozen_protocol = _load_canonical(
            repo_root / REPOSITORY_PROTOCOL,
            label="P4 protocol for post-attempt selector recomputation",
        )
        _require_exact_recomputed_calibration_selector(
            persisted_selector,
            protocol=frozen_protocol,
        )
    rebuilt = _build_terminal(
        base={key: item[key] for key in static_expected if key != "attempt_sha256"},
        attempt_sha256=attempt_sha256,
        execution_terminal=item["execution_terminal"],
        error=item["error"],
        result=terminal_result,
    )
    _constant(rebuilt, item, label="external terminal reconstruction")


def _read_canonical_member_at(
    directory_fd: int,
    name: str,
    *,
    label: str,
) -> tuple[bytes, dict[str, object]]:
    """Read one bounded, unaliased canonical member through a held directory."""

    if not name or "/" in name or name in {".", ".."}:
        raise P4ProtocolError(f"{label} has an invalid member name")
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=directory_fd,
        )
    except OSError as error:
        raise P4ProtocolError(f"cannot open {label}") from error
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size > CANONICAL_BYTE_LIMIT
        ):
            raise P4ProtocolError(f"{label} must be a bounded regular nlink=1 file")
        chunks: list[bytes] = []
        remaining = CANONICAL_BYTE_LIMIT + 1
        while remaining:
            block = os.read(descriptor, min(65_536, remaining))
            if not block:
                break
            chunks.append(block)
            remaining -= len(block)
        source = b"".join(chunks)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if len(source) > CANONICAL_BYTE_LIMIT or (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        raise P4ProtocolError(f"{label} changed while being read")
    try:
        parsed = parse_canonical_json(source, label=label)
    except ValueError as error:
        raise P4ProtocolError(f"{label} is not canonical: {error}") from error
    return source, _mapping(parsed, label=label)


def _expected_external_payload_names(result: Mapping[str, object]) -> list[str]:
    names = [ATTEMPT_NAME]
    for flag, name in (
        ("graph_selection_sealed", GRAPH_SELECTION_SEAL_NAME),
        ("threshold_decision_sealed", THRESHOLD_SEAL_NAME),
        ("confirmation_accessed", CONFIRMATION_ACCESS_SEAL_NAME),
    ):
        if result.get(flag) is True:
            names.append(name)
        elif result.get(flag) is not False:
            raise P4ProtocolError(f"terminal result {flag} must be boolean")
    names.append(TERMINAL_NAME)
    return names


def _validate_graph_selection_seal(
    seal: Mapping[str, object],
    *,
    result: Mapping[str, object],
    protocol: Mapping[str, object],
    attempt_sha256: str,
    launch_sha256: str,
) -> None:
    _exact_keys(
        seal,
        {
            "schema_version",
            "experiment_id",
            "calibration_selector",
            "field_read_before_seal",
            "readout_before_seal",
            "confirmation_accessed_before_seal",
            "attempt_sha256",
            "launch_sha256",
        },
        label="graph-selection seal",
    )
    _constant(
        seal["schema_version"],
        GRAPH_SELECTION_SEAL_SCHEMA_VERSION,
        label="graph-selection seal schema",
    )
    _constant(seal["experiment_id"], EXPERIMENT_ID, label="graph-selection experiment")
    _constant(seal["attempt_sha256"], attempt_sha256, label="graph-selection attempt")
    _constant(seal["launch_sha256"], launch_sha256, label="graph-selection launch")
    for key in (
        "field_read_before_seal",
        "readout_before_seal",
        "confirmation_accessed_before_seal",
    ):
        _constant(seal[key], False, label=f"graph-selection {key}")
    sealed_selector = _validate_selector_projection(seal["calibration_selector"])
    _require_exact_recomputed_calibration_selector(
        sealed_selector,
        protocol=protocol,
    )
    if result["terminal_state"] != "invalid":
        _constant(
            sealed_selector,
            result["calibration_selector"],
            label="graph-selection selector binding",
        )


def _validate_threshold_seal_payload(seal: Mapping[str, object]) -> None:
    inventory = _mapping(
        seal["calibration_scalar_inventory"], label="threshold scalar inventory"
    )
    _exact_keys(
        inventory,
        {
            "absolute_oracle_or_null_error_cycles",
            "graph_family_span_cycles",
            "pure_so2_gauge_error_cycles",
            "orientation_reversal_error_cycles",
            "total",
        },
        label="threshold scalar inventory",
    )
    counts = {
        key: _require_plain_nonnegative_int(
            inventory[key], label=f"threshold inventory {key}"
        )
        for key in inventory
    }
    _constant(
        counts["total"],
        sum(value for key, value in counts.items() if key != "total"),
        label="threshold scalar inventory total",
    )
    nonfinite_variant = "empty_or_nonfinite_detected" in seal
    passing_variant = "oracle_and_null_selection_worst_metric" in seal
    if nonfinite_variant:
        _constant(
            seal["decision_state"],
            "insufficient_calibration_resolution",
            label="nonfinite threshold decision",
        )
        _constant(
            seal["empty_or_nonfinite_detected"],
            True,
            label="threshold nonfinite flag",
        )
        _constant(
            seal["oracle_and_null_selection_worst_error_cycles"],
            None,
            label="nonfinite oracle worst",
        )
        _constant(
            seal["graph_family_span_selection_worst_error_cycles"],
            None,
            label="nonfinite span worst",
        )
        if counts["total"] >= 62:
            raise P4RunError("nonfinite threshold seal claims a complete inventory")
        return

    _constant(
        inventory,
        {
            "absolute_oracle_or_null_error_cycles": 54,
            "graph_family_span_cycles": 6,
            "pure_so2_gauge_error_cycles": 1,
            "orientation_reversal_error_cycles": 1,
            "total": 62,
        },
        label="finite threshold inventory",
    )
    oracle_worst = _nonnegative_finite_scalar(
        seal["oracle_and_null_selection_worst_error_cycles"]
    )
    span_worst = _nonnegative_finite_scalar(
        seal["graph_family_span_selection_worst_error_cycles"]
    )
    if oracle_worst is None or span_worst is None:
        raise P4RunError("finite threshold seal requires finite worst values")
    oracle_threshold, oracle_cap = _effective_threshold(oracle_worst, cap=0.05)
    graph_threshold, graph_cap = _effective_threshold(span_worst, cap=0.1)
    _constant(
        seal["oracle_and_null_cycles"], oracle_threshold, label="threshold oracle value"
    )
    _constant(seal["oracle_and_null_cap_cycles"], 0.05, label="threshold oracle cap")
    _constant(
        seal["graph_family_span_cycles"], graph_threshold, label="threshold graph value"
    )
    _constant(seal["graph_family_span_cap_cycles"], 0.1, label="threshold graph cap")
    _constant(
        seal["algebraic_gauge_and_reversal_error_cycles"],
        1e-8,
        label="threshold algebraic gate",
    )
    _constant(seal["no_clamping_applied"], True, label="threshold no-clamp flag")
    decision = seal["decision_state"]
    if decision == "pass":
        if not passing_variant or not oracle_cap or not graph_cap:
            raise P4RunError("passing threshold seal violates its closed variant")
        _constant(
            seal["oracle_and_null_selection_worst_metric"],
            "maximum-over-54-declared-finite-absolute-errors",
            label="threshold oracle metric",
        )
        _constant(
            seal["graph_family_span_selection_worst_metric"],
            "maximum-over-6-declared-finite-spans",
            label="threshold graph metric",
        )
    elif decision == "insufficient_calibration_resolution":
        if passing_variant or (oracle_cap and graph_cap):
            raise P4RunError("cap-stop threshold seal does not breach either cap")
    elif decision == "orientation_or_reverse_consistency_unresolved":
        if passing_variant:
            raise P4RunError("algebraic-stop threshold seal uses passing keys")
    else:
        raise P4RunError("threshold decision state is outside the branch table")


def _expected_threshold_seal_document(
    result: Mapping[str, object],
    *,
    attempt_sha256: str,
    launch_sha256: str,
    graph_selection_sha256: str,
) -> dict[str, object]:
    selector = _validate_selector_projection(result["calibration_selector"])
    matrix = _validate_matrix_projection(
        result["calibration_matrix"],
        role="calibration",
        sealed_selected=_sequence(selector["selected"], label="selector selected"),
    )
    algebraic, _values = _validate_calibration_algebraic(
        result["calibration_algebraic_diagnostics"]
    )
    summary = _calibration_summary(matrix, algebraic)
    common: dict[str, object] = {
        "schema_version": THRESHOLD_SEAL_SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "graph_selection_seal_sha256": graph_selection_sha256,
        "calibration_scalar_inventory": summary["inventory"],
        "oracle_and_null_selection_worst_error_cycles": summary["oracle_worst"],
        "graph_family_span_selection_worst_error_cycles": summary["span_worst"],
        "confirmation_accessed_before_seal": False,
        "attempt_sha256": attempt_sha256,
        "launch_sha256": launch_sha256,
    }
    if not bool(summary["finite_complete"]):
        return {
            **common,
            "decision_state": "insufficient_calibration_resolution",
            "empty_or_nonfinite_detected": True,
        }
    effective = _expected_effective_thresholds(summary, include_algebraic=True)
    decision = (
        "pass"
        if result["confirmation_accessed"] is True
        else str(result["reason"]).replace("-", "_")
    )
    finite: dict[str, object] = {
        **common,
        "decision_state": decision,
        "oracle_and_null_cycles": effective["oracle_and_null_cycles"],
        "oracle_and_null_cap_cycles": 0.05,
        "graph_family_span_cycles": effective["graph_family_span_cycles"],
        "graph_family_span_cap_cycles": 0.1,
        "algebraic_gauge_and_reversal_error_cycles": 1e-8,
        "no_clamping_applied": True,
    }
    if decision == "pass":
        finite.update(
            {
                "oracle_and_null_selection_worst_metric": (
                    "maximum-over-54-declared-finite-absolute-errors"
                ),
                "graph_family_span_selection_worst_metric": (
                    "maximum-over-6-declared-finite-spans"
                ),
            }
        )
    return finite


def _validate_threshold_seal(
    seal: Mapping[str, object],
    *,
    result: Mapping[str, object],
    attempt_sha256: str,
    launch_sha256: str,
    graph_selection_sha256: str,
) -> None:
    common = {
        "schema_version",
        "experiment_id",
        "graph_selection_seal_sha256",
        "decision_state",
        "calibration_scalar_inventory",
        "oracle_and_null_selection_worst_error_cycles",
        "graph_family_span_selection_worst_error_cycles",
        "confirmation_accessed_before_seal",
        "attempt_sha256",
        "launch_sha256",
    }
    nonfinite = common | {"empty_or_nonfinite_detected"}
    finite = common | {
        "oracle_and_null_cycles",
        "oracle_and_null_cap_cycles",
        "graph_family_span_cycles",
        "graph_family_span_cap_cycles",
        "algebraic_gauge_and_reversal_error_cycles",
        "no_clamping_applied",
    }
    passing = finite | {
        "oracle_and_null_selection_worst_metric",
        "graph_family_span_selection_worst_metric",
    }
    observed_keys = set(seal)
    if observed_keys not in (nonfinite, finite, passing):
        raise P4ProtocolError("threshold seal keys differ from every frozen variant")
    _constant(
        seal["schema_version"],
        THRESHOLD_SEAL_SCHEMA_VERSION,
        label="threshold seal schema",
    )
    _constant(seal["experiment_id"], EXPERIMENT_ID, label="threshold experiment")
    _constant(seal["attempt_sha256"], attempt_sha256, label="threshold attempt")
    _constant(seal["launch_sha256"], launch_sha256, label="threshold launch")
    _constant(
        seal["graph_selection_seal_sha256"],
        graph_selection_sha256,
        label="threshold graph-selection chain",
    )
    _validate_threshold_seal_payload(seal)
    if result["terminal_state"] != "invalid":
        _constant(
            seal["calibration_scalar_inventory"],
            result["calibration_scalar_inventory"],
            label="threshold scalar inventory binding",
        )
    _constant(
        seal["confirmation_accessed_before_seal"],
        False,
        label="threshold pre-access flag",
    )
    if result["terminal_state"] != "invalid":
        _constant(
            dict(seal),
            _expected_threshold_seal_document(
                result,
                attempt_sha256=attempt_sha256,
                launch_sha256=launch_sha256,
                graph_selection_sha256=graph_selection_sha256,
            ),
            label="threshold seal result cross-binding",
        )


def _validate_confirmation_access_seal(
    seal: Mapping[str, object],
    *,
    attempt_sha256: str,
    launch_sha256: str,
    graph_selection_sha256: str,
    threshold_sha256: str,
) -> None:
    _constant(
        dict(seal),
        {
            "schema_version": CONFIRMATION_ACCESS_SEAL_SCHEMA_VERSION,
            "experiment_id": EXPERIMENT_ID,
            "attempt_sha256": attempt_sha256,
            "launch_sha256": launch_sha256,
            "graph_selection_seal_sha256": graph_selection_sha256,
            "threshold_seal_sha256": threshold_sha256,
            "confirmation_access_before_seal": False,
            "confirmation_access_authorized_after_seal": True,
        },
        label="confirmation-access seal",
    )


def _build_store_manifest(
    directory_fd: int,
    *,
    terminal: Mapping[str, object],
) -> dict[str, object]:
    result = _mapping(terminal["result"], label="manifest terminal result")
    names = _expected_external_payload_names(result)
    observed = sorted(os.listdir(directory_fd))
    if observed != sorted(names):
        raise P4PersistenceError(
            "external stage members differ before manifest publication"
        )
    members: list[dict[str, object]] = []
    for name in names:
        source, _document = _read_canonical_member_at(
            directory_fd, name, label=f"manifest source {name}"
        )
        members.append(
            {"name": name, "sha256": _sha256_bytes(source), "size_bytes": len(source)}
        )
    by_name = {str(item["name"]): item for item in members}
    return {
        "schema_version": STORE_MANIFEST_SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "attempt_sha256": by_name[ATTEMPT_NAME]["sha256"],
        "terminal_sha256": by_name[TERMINAL_NAME]["sha256"],
        "member_count": len(members),
        "members": members,
        "attempt_exactly_one": True,
        "terminal_at_most_one": True,
        "terminal_guaranteed": False,
        "retry_resume_rescue_authorized": False,
    }


def _validate_external_bundle_fd(
    directory_fd: int,
    *,
    repo_root: Path,
    launch: Mapping[str, object],
) -> dict[str, object]:
    """Validate the exact durable member set and all seal chains."""

    names = sorted(os.listdir(directory_fd))
    if STORE_MANIFEST_NAME not in names:
        raise P4ProtocolError("external store manifest is absent")
    manifest_source, manifest = _read_canonical_member_at(
        directory_fd, STORE_MANIFEST_NAME, label="external store manifest"
    )
    _exact_keys(
        manifest,
        {
            "schema_version",
            "experiment_id",
            "attempt_sha256",
            "terminal_sha256",
            "member_count",
            "members",
            "attempt_exactly_one",
            "terminal_at_most_one",
            "terminal_guaranteed",
            "retry_resume_rescue_authorized",
        },
        label="external store manifest",
    )
    _constant(
        manifest["schema_version"],
        STORE_MANIFEST_SCHEMA_VERSION,
        label="external store manifest schema",
    )
    _constant(manifest["experiment_id"], EXPERIMENT_ID, label="manifest experiment")
    _constant(
        manifest["attempt_exactly_one"], True, label="manifest attempt exactly one"
    )
    _constant(
        manifest["terminal_at_most_one"], True, label="manifest terminal at most one"
    )
    _constant(
        manifest["terminal_guaranteed"], False, label="manifest terminal guarantee"
    )
    _constant(
        manifest["retry_resume_rescue_authorized"],
        False,
        label="manifest retry authority",
    )
    records = [
        _mapping(item, label="external member record")
        for item in _sequence(manifest["members"], label="external manifest members")
    ]
    _constant(manifest["member_count"], len(records), label="manifest member count")
    for record in records:
        _exact_keys(
            record,
            {"name", "sha256", "size_bytes"},
            label="external member record",
        )
        _require_sha256(record["sha256"], label="external member digest")
        if type(record["size_bytes"]) is not int or int(record["size_bytes"]) < 0:
            raise P4ProtocolError("external member size must be nonnegative integer")
    record_names = [str(item["name"]) for item in records]
    if len(record_names) != len(set(record_names)):
        raise P4ProtocolError("external manifest repeats a member")
    _constant(
        names,
        sorted([*record_names, STORE_MANIFEST_NAME]),
        label="external directory member set",
    )
    sources: dict[str, bytes] = {}
    documents: dict[str, dict[str, object]] = {}
    for record in records:
        name = str(record["name"])
        source, document = _read_canonical_member_at(
            directory_fd, name, label=f"external member {name}"
        )
        _constant(record["sha256"], _sha256_bytes(source), label=f"{name} digest")
        _constant(record["size_bytes"], len(source), label=f"{name} size")
        sources[name] = source
        documents[name] = document
    if ATTEMPT_NAME not in documents or TERMINAL_NAME not in documents:
        raise P4ProtocolError("external bundle lacks attempt or terminal")
    attempt_source = sources[ATTEMPT_NAME]
    terminal_source = sources[TERMINAL_NAME]
    attempt_sha256 = _sha256_bytes(attempt_source)
    terminal_sha256 = _sha256_bytes(terminal_source)
    _constant(
        manifest["attempt_sha256"], attempt_sha256, label="manifest attempt digest"
    )
    _constant(
        manifest["terminal_sha256"], terminal_sha256, label="manifest terminal digest"
    )
    _validate_attempt_document(
        documents[ATTEMPT_NAME], repo_root=repo_root, launch=launch
    )
    _validate_terminal_document(
        documents[TERMINAL_NAME],
        repo_root=repo_root,
        launch=launch,
        attempt_sha256=attempt_sha256,
    )
    result = _mapping(documents[TERMINAL_NAME]["result"], label="external result")
    expected_names = _expected_external_payload_names(result)
    _constant(record_names, expected_names, label="external manifest member order")
    launch_sha256 = canonical_json_sha256(launch)
    graph_digest = result["graph_selection_seal_sha256"]
    threshold_digest = result["threshold_seal_sha256"]
    confirmation_digest = result["confirmation_access_seal_sha256"]
    if GRAPH_SELECTION_SEAL_NAME in documents:
        _constant(
            _sha256_bytes(sources[GRAPH_SELECTION_SEAL_NAME]),
            graph_digest,
            label="graph-selection terminal digest",
        )
        _validate_graph_selection_seal(
            documents[GRAPH_SELECTION_SEAL_NAME],
            result=result,
            protocol=_load_canonical(
                repo_root / REPOSITORY_PROTOCOL,
                label="P4 protocol for graph-selection seal recomputation",
            ),
            attempt_sha256=attempt_sha256,
            launch_sha256=launch_sha256,
        )
    if THRESHOLD_SEAL_NAME in documents:
        assert isinstance(graph_digest, str)
        _constant(
            _sha256_bytes(sources[THRESHOLD_SEAL_NAME]),
            threshold_digest,
            label="threshold terminal digest",
        )
        _validate_threshold_seal(
            documents[THRESHOLD_SEAL_NAME],
            result=result,
            attempt_sha256=attempt_sha256,
            launch_sha256=launch_sha256,
            graph_selection_sha256=graph_digest,
        )
    if CONFIRMATION_ACCESS_SEAL_NAME in documents:
        assert isinstance(graph_digest, str) and isinstance(threshold_digest, str)
        _constant(
            _sha256_bytes(sources[CONFIRMATION_ACCESS_SEAL_NAME]),
            confirmation_digest,
            label="confirmation-access terminal digest",
        )
        _validate_confirmation_access_seal(
            documents[CONFIRMATION_ACCESS_SEAL_NAME],
            attempt_sha256=attempt_sha256,
            launch_sha256=launch_sha256,
            graph_selection_sha256=graph_digest,
            threshold_sha256=threshold_digest,
        )
    return {
        "attempt_source": attempt_source,
        "terminal_source": terminal_source,
        "attempt_sha256": attempt_sha256,
        "terminal_sha256": terminal_sha256,
        "manifest_source": manifest_source,
        "manifest_sha256": _sha256_bytes(manifest_source),
    }


def _validate_external_bundle_path(
    path: Path,
    *,
    repo_root: Path,
    launch: Mapping[str, object],
) -> dict[str, object]:
    try:
        before = os.lstat(path)
        if not stat.S_ISDIR(before.st_mode):
            raise P4ProtocolError("external bundle path must be a real directory")
        descriptor = os.open(
            path,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
    except OSError as error:
        raise P4ProtocolError("cannot open external bundle directory") from error
    try:
        held = os.fstat(descriptor)
        if (held.st_dev, held.st_ino) != (before.st_dev, before.st_ino):
            raise P4ProtocolError("external bundle directory identity changed")
        return _validate_external_bundle_fd(
            descriptor, repo_root=repo_root, launch=launch
        )
    finally:
        os.close(descriptor)


def _validate_and_promote_external_stage(
    stage: _OwnedStage,
    *,
    repo_root: Path,
    launch: Mapping[str, object],
) -> dict[str, object]:
    """Validate, promote no-replace, and revalidate exactly the same bundle."""

    _validate_stage_anchor(stage)
    staged = _validate_external_bundle_fd(
        stage.stage_fd, repo_root=repo_root, launch=launch
    )
    _promote_external_stage(stage)
    authoritative = _validate_external_bundle_path(
        stage.store_path, repo_root=repo_root, launch=launch
    )
    if authoritative != staged:
        raise P4PersistenceError("external bundle changed across promotion")
    return authoritative


def repair_repository_projections(repo_root: Path) -> dict[str, object]:
    """Project an already complete external store; never rerun science."""

    root = repo_root.resolve()
    _protocol, launch = validate_committed_launch(root, projection_repair=True)
    if not _entry_absent(EXTERNAL_STAGE):
        raise P4ProtocolError("unresolved external stage cannot be repaired or resumed")
    bundle = _validate_external_bundle_path(
        EXTERNAL_STORE,
        repo_root=root,
        launch=launch,
    )
    attempt_source = bundle["attempt_source"]
    terminal_source = bundle["terminal_source"]
    assert isinstance(attempt_source, bytes) and isinstance(terminal_source, bytes)
    projected: list[str] = []
    for path, source in (
        (root / REPOSITORY_ATTEMPT, attempt_source),
        (root / REPOSITORY_TERMINAL, terminal_source),
    ):
        disposition = _publish_repository_projection(path, source)
        if disposition == "published":
            projected.append(str(path.relative_to(root)))
    return {
        "status": "repository_projections_complete",
        "projected_paths": projected,
        "attempt_sha256": bundle["attempt_sha256"],
        "terminal_sha256": bundle["terminal_sha256"],
        "external_manifest_sha256": bundle["manifest_sha256"],
        "scientific_execution_performed": False,
    }


def run_official(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    run_process_pre = _validated_current_python_process(root, mode="--run")
    _constant(
        _BOOTSTRAP_PRE_IMPORT_PYTHON_OBSERVATION,
        run_process_pre,
        label="pre-import run Python process observation",
    )
    _constant(
        _BOOTSTRAP_POST_IMPORT_PYTHON_OBSERVATION,
        run_process_pre,
        label="post-import run Python process observation",
    )
    protocol, launch = validate_committed_launch(root, require_exact_argv=True)
    launch_sha256 = canonical_json_sha256(launch)
    source_closure_pre = _source_closure_snapshot(root, protocol)
    source_closure_sha256 = canonical_json_sha256(source_closure_pre)
    launch_runtime = _mapping(launch["runtime"], label="launch runtime")
    _constant(
        launch_runtime["source_closure_sha256"],
        source_closure_sha256,
        label="pre-attempt source closure",
    )
    stage = _reserve_external_stage()
    base = {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "protocol_sha256": _sha256_file(root / REPOSITORY_PROTOCOL),
        "runner_sha256": _sha256_file(root / REPOSITORY_RUNNER),
        "launch_sha256": launch_sha256,
        "source_commit": launch["source_commit"],
        "operator_prior_outcome_exposure": True,
        "cryptographic_unseen": False,
        "development_only": True,
        "independent": False,
        "claim_ceiling": "level_0",
        "scientific_authority": False,
        "topology_authority": False,
        "integer_output_present": False,
        "model_accessed": False,
        "network_accessed": False,
        "cache_accessed": False,
        "cache_access_scope": "model-or-subject-data-cache-only",
        "python_bytecode_cache_accessed": False,
        "python_process_pre_import_observation": dict(run_process_pre),
        "python_process_post_import_observation": dict(
            _BOOTSTRAP_POST_IMPORT_PYTHON_OBSERVATION
        ),
        "python_process_post_execution_observation": None,
        "source_closure_pre_sha256": source_closure_sha256,
        "source_closure_post_sha256": source_closure_sha256,
        "pythia_raw_capture_accessed": False,
        "subject_data_accessed": False,
        "dynamic_timestamp_present": False,
    }
    try:
        attempt = {
            "schema_version": ATTEMPT_SCHEMA_VERSION,
            "experiment_id": EXPERIMENT_ID,
            "launch_sha256": launch_sha256,
            "source_commit": launch["source_commit"],
            "protocol_sha256": _sha256_file(root / REPOSITORY_PROTOCOL),
            "runner_sha256": _sha256_file(root / REPOSITORY_RUNNER),
            "identity_consumed": True,
            "official_input_access_before_attempt": False,
            "attempt_exactly_one": True,
            "terminal_at_most_one": True,
            "terminal_guaranteed": False,
            "unresolved_stage_consumes_attempt": True,
            "retry_resume_rescue_authorized": False,
        }
        attempt_source, attempt_sha256 = _write_stage_document(
            stage, ATTEMPT_NAME, attempt
        )

        def seal_graph_selection(document: Mapping[str, object]) -> str:
            bound = {
                **document,
                "attempt_sha256": attempt_sha256,
                "launch_sha256": launch_sha256,
            }
            _source, digest = _write_stage_document(
                stage, GRAPH_SELECTION_SEAL_NAME, bound
            )
            return digest

        def seal_threshold_decision(document: Mapping[str, object]) -> str:
            bound = {
                **document,
                "attempt_sha256": attempt_sha256,
                "launch_sha256": launch_sha256,
            }
            _source, digest = _write_stage_document(stage, THRESHOLD_SEAL_NAME, bound)
            return digest

        try:
            execution_observation = {
                "graph_selection_sealed": False,
                "graph_selection_seal_sha256": None,
                "threshold_decision_sealed": False,
                "threshold_seal_sha256": None,
                "confirmation_accessed": False,
                "confirmation_access_seal_sha256": None,
            }

            def observed_graph_seal(document: Mapping[str, object]) -> str:
                digest = seal_graph_selection(document)
                execution_observation["graph_selection_sealed"] = True
                execution_observation["graph_selection_seal_sha256"] = digest
                return digest

            def observed_threshold_seal(document: Mapping[str, object]) -> str:
                digest = seal_threshold_decision(document)
                execution_observation["threshold_decision_sealed"] = True
                execution_observation["threshold_seal_sha256"] = digest
                return digest

            def observed_confirmation_access() -> str:
                graph_digest = execution_observation["graph_selection_seal_sha256"]
                threshold_digest = execution_observation["threshold_seal_sha256"]
                _require_sha256(graph_digest, label="observed graph-selection seal")
                _require_sha256(threshold_digest, label="observed threshold seal")
                _source, digest = _write_stage_document(
                    stage,
                    CONFIRMATION_ACCESS_SEAL_NAME,
                    {
                        "schema_version": (CONFIRMATION_ACCESS_SEAL_SCHEMA_VERSION),
                        "experiment_id": EXPERIMENT_ID,
                        "attempt_sha256": attempt_sha256,
                        "launch_sha256": launch_sha256,
                        "graph_selection_seal_sha256": graph_digest,
                        "threshold_seal_sha256": threshold_digest,
                        "confirmation_access_before_seal": False,
                        "confirmation_access_authorized_after_seal": True,
                    },
                )
                execution_observation["confirmation_accessed"] = True
                execution_observation["confirmation_access_seal_sha256"] = digest
                return digest

            result = execute_calibration(
                protocol,
                seal_graph_selection=observed_graph_seal,
                seal_threshold_decision=observed_threshold_seal,
                mark_confirmation_access=observed_confirmation_access,
            )
            terminal = _build_terminal(
                base=base,
                attempt_sha256=attempt_sha256,
                execution_terminal="complete",
                error=None,
                result=result,
            )
        except P4PersistenceError:
            # A seal write/flush/identity failure is not a scientific outcome.
            # The unresolved stage consumes the attempt and must remain in place.
            raise
        except Exception as error:  # catchable post-attempt execution terminal
            caught_result = {
                "terminal_state": "invalid",
                "reason": "caught-execution-error",
                "calibration_selector": None,
                "graph_selection_seal_sha256": execution_observation[
                    "graph_selection_seal_sha256"
                ],
                "threshold_seal_sha256": execution_observation["threshold_seal_sha256"],
                "confirmation_access_seal_sha256": execution_observation[
                    "confirmation_access_seal_sha256"
                ],
                "calibration_matrix": None,
                "calibration_algebraic_diagnostics": None,
                "calibration_scalar_inventory": None,
                "effective_thresholds": None,
                "confirmation_structural": None,
                "confirmation_matrix": None,
                "confirmation_accessed": execution_observation["confirmation_accessed"],
                "graph_selection_sealed": execution_observation[
                    "graph_selection_sealed"
                ],
                "threshold_decision_sealed": execution_observation[
                    "threshold_decision_sealed"
                ],
                "controls": _not_run_controls("caught-execution-error"),
            }
            terminal = _build_terminal(
                base=base,
                attempt_sha256=attempt_sha256,
                execution_terminal="caught_error",
                error={
                    "class": f"{type(error).__module__}.{type(error).__qualname__}",
                    "message_sha256": hashlib.sha256(
                        str(error).encode("utf-8")
                    ).hexdigest(),
                },
                result=caught_result,
            )
        try:
            run_process_post = _validated_current_python_process(root, mode="--run")
            _constant(
                run_process_post,
                run_process_pre,
                label="post-execution run Python process observation",
            )
        except P4ProtocolError as error:
            raise P4PersistenceError(
                "Python process/cache boundary changed across consumed attempt"
            ) from error
        terminal["python_process_post_execution_observation"] = dict(run_process_post)
        source_closure_post = _source_closure_snapshot(root, protocol)
        if source_closure_post != source_closure_pre:
            raise P4PersistenceError(
                "source closure changed across the consumed official attempt"
            )
        terminal_source, _terminal_sha256 = _write_stage_document(
            stage, TERMINAL_NAME, terminal
        )
        manifest = _build_store_manifest(stage.stage_fd, terminal=terminal)
        _write_stage_document(stage, STORE_MANIFEST_NAME, manifest)
        authoritative_bundle = _validate_and_promote_external_stage(
            stage,
            repo_root=root,
            launch=launch,
        )
        if authoritative_bundle["attempt_source"] != attempt_source:
            raise P4PersistenceError("validated store attempt differs after promotion")
        if authoritative_bundle["terminal_source"] != terminal_source:
            raise P4PersistenceError("validated store terminal differs after promotion")
        _publish_repository_projection(root / REPOSITORY_ATTEMPT, attempt_source)
        _publish_repository_projection(root / REPOSITORY_TERMINAL, terminal_source)
        return terminal
    finally:
        stage.close()


def _parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--validate-protocol", action="store_true")
    modes.add_argument("--prepare-launch", action="store_true")
    modes.add_argument("--preflight", action="store_true")
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--repair-projections", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parse_arguments(argv)
    root = _repository_root()
    try:
        if arguments.validate_protocol:
            protocol = load_and_validate_protocol(root)
            response = {
                "status": "valid",
                "protocol_sha256": canonical_json_sha256(protocol),
                "official_phantom_constructed": False,
                "selector_executed": False,
                "confirmation_accessed": False,
            }
        elif arguments.prepare_launch:
            launch = prepare_launch(root)
            response = {
                "status": "launch_prepared_not_committed",
                "launch_sha256": canonical_json_sha256(launch),
                "next_required_action": "commit-launch-before-preflight-or-run",
                "official_phantom_constructed": False,
                "selector_executed": False,
                "confirmation_accessed": False,
            }
        elif arguments.preflight:
            _protocol, launch = validate_committed_launch(root)
            response = {
                "status": "ready",
                "launch_sha256": canonical_json_sha256(launch),
                "official_phantom_constructed": False,
                "selector_executed": False,
                "confirmation_accessed": False,
            }
        elif arguments.run:
            terminal = run_official(root)
            response = {
                "status": "terminal_published",
                "terminal_state": _mapping(terminal["result"], label="terminal result")[
                    "terminal_state"
                ],
                "terminal_sha256": canonical_json_sha256(terminal),
                "terminal_path": str(REPOSITORY_TERMINAL),
            }
        else:
            response = repair_repository_projections(root)
    except (OSError, P4ProtocolError, P4RunError, ValueError) as error:
        print(f"p4 graph evaluability: {error}", file=sys.stderr)
        return 2
    print(json.dumps(response, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
