#!/usr/bin/env python3
"""Run the frozen, claim-ineligible Pythia-70M gate-state development lane.

This is a private repository runner, not a SpiralLens public API.  Its normal
mode is a single, non-resumable attempt.  ``--validate-launch-only`` performs
the complete value-free launch/source/platform preflight without reading a
model file or the Hugging Face cache.
"""

from __future__ import annotations

import argparse
import contextlib
import ctypes
import errno
import hashlib
import importlib.metadata
import io
import itertools
import json
import math
import mmap
import os
import platform
import signal
import stat
import subprocess
import sys
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, NoReturn, Self

import numpy as np
from numpy.typing import NDArray

_REPOSITORY = Path(__file__).resolve().parents[1]
_RUNNER_RELATIVE = "scripts/run_pythia70_gate_state_development.py"
_FREEZE_RELATIVE = "protocols/pythia70_gate_state_development_freeze_v0_1.json"
_LAUNCH_RELATIVE = (
    "experiments/pythia/gate_state_development_v0_1/launch-authorization.json"
)
_FREEZE_SHA256 = "fe85ebb15e0a9794a02d72b4fdefd0178b52662528e8e066530d873516b52452"
_FREEZE_MAX_BYTES = 1_048_576
_LAUNCH_MAX_BYTES = 1_048_576
_JSON_MAX_BYTES = 1_048_576
_MODEL_ID = "EleutherAI/pythia-70m"
_MODEL_REVISION = "a39f36b100fe8a5377810d56c3f4789b9c53ac42"
_TOKEN_IDS = np.arange(49, dtype="<i8")
_FIT_CONTEXT_INDICES = (0, 2, 4, 6)
_EVALUATION_CONTEXT_INDICES = (1, 3, 5, 7)
_STAGES = ("resid_pre", "resid_post")
_FAMILIES = ("mutual-knn", "fixed-radius", "shared-neighbor")
_SPLITS = ("fit", "evaluation")
_CANDIDATES = ("F2", "F4")
_GATE_IDS = (
    "capture_integrity",
    "measurable_drift",
    "f2_section_support",
    "f4_tensor_support",
    "low_amplitude_set_repeatability",
    "address_loop_support",
    "continuous_holonomy_consistency",
    "address_ring_phase_resolution",
    "graph_family_agreement",
    "negative_controls",
)
_DEPENDENCY_DISTRIBUTIONS = {
    "huggingface_hub": "huggingface-hub",
    "numpy": "numpy",
    "safetensors": "safetensors",
    "scipy": "scipy",
    "spirallens": "spirallens",
    "torch": "torch",
    "transformers": "transformers",
}
_DIRECTORY_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_CLOEXEC", 0)
)
_FILE_READ_FLAGS = (
    os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
)
_FILE_WRITE_FLAGS = (
    os.O_RDWR
    | os.O_CREAT
    | os.O_EXCL
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_CLOEXEC", 0)
)

FloatArray = NDArray[np.float64]
Float32Array = NDArray[np.float32]
BoolArray = NDArray[np.bool_]


class _RunError(RuntimeError):
    """Closed runner failure with one frozen terminal error stage."""

    def __init__(self, stage: str, message: str) -> None:
        super().__init__(message)
        self.stage = stage


class _PreflightError(_RunError):
    def __init__(self, message: str) -> None:
        super().__init__("preflight", message)


class _DeferredSignal(RuntimeError):
    pass


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _require_utc_timestamp(value: str, *, label: str) -> None:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC)
    except ValueError as error:
        raise _RunError(
            "terminal_persistence", f"{label} is not RFC3339 UTC"
        ) from error
    if parsed.strftime("%Y-%m-%dT%H:%M:%S.%fZ") != value:
        raise _RunError(
            "terminal_persistence", f"{label} does not have exactly six fractions"
        )


def _sha256(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


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


def _canonical_value_bytes(document: object) -> bytes:
    return json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _canonical_numeric_zero(value: object) -> object:
    if isinstance(value, float):
        return 0.0 if value == 0.0 else value
    if isinstance(value, list):
        return [_canonical_numeric_zero(item) for item in value]
    if isinstance(value, tuple):
        return [_canonical_numeric_zero(item) for item in value]
    if isinstance(value, Mapping):
        return {key: _canonical_numeric_zero(item) for key, item in value.items()}
    return value


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if not isinstance(key, str):
            raise _PreflightError("JSON mapping keys must be strings")
        if key in result:
            raise _PreflightError(f"duplicate JSON field {key!r}")
        result[key] = value
    return result


def _strict_json_bytes(source: bytes, *, label: str) -> dict[str, object]:
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError as error:
        raise _PreflightError(f"{label} must be UTF-8") from error
    try:
        value = json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=lambda item: _raise_invalid_constant(item, label=label),
        )
    except _PreflightError:
        raise
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise _PreflightError(f"{label} is not strict JSON") from error
    if not isinstance(value, dict):
        raise _PreflightError(f"{label} root must be an object")
    return value


def _raise_invalid_constant(value: str, *, label: str) -> NoReturn:
    raise _PreflightError(f"{label} contains forbidden numeric constant {value!r}")


def _read_bounded(path: Path, maximum: int, *, label: str) -> bytes:
    try:
        with path.open("rb") as handle:
            source = handle.read(maximum + 1)
    except OSError as error:
        raise _PreflightError(f"cannot read {label}") from error
    if len(source) > maximum:
        raise _PreflightError(f"{label} exceeds {maximum} bytes")
    return source


def _mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise _PreflightError(f"{label} must be a string-keyed object")
    return value


def _sequence(value: object, *, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise _PreflightError(f"{label} must be an array")
    return value


def _exact_keys(
    value: Mapping[str, object], expected: Iterable[str], *, label: str
) -> None:
    wanted = set(expected)
    actual = set(value)
    if actual != wanted:
        raise _PreflightError(
            f"{label} fields differ: missing={sorted(wanted - actual)!r}, "
            f"unknown={sorted(actual - wanted)!r}"
        )


def _deep_exact_equal(left: object, right: object) -> bool:
    """Compare strict JSON values without Python's ``True == 1`` coercion."""

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
        raise _PreflightError(f"{label} differs")


def _require_lower_hex(value: object, length: int, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise _PreflightError(f"{label} must be {length} lowercase hex digits")
    return value


def _git(*arguments: str, binary: bool = False) -> bytes | str:
    environment = {
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": "/usr/bin:/bin",
    }
    completed = subprocess.run(
        [
            "/usr/bin/git",
            "--no-replace-objects",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.untrackedCache=false",
            *arguments,
        ],
        cwd=_REPOSITORY,
        env=environment,
        check=False,
        capture_output=True,
        text=not binary,
    )
    if completed.returncode != 0:
        stderr = completed.stderr
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        raise _PreflightError(f"sanitized Git check failed: {stderr.strip()}")
    if binary:
        assert isinstance(completed.stdout, bytes)
        return completed.stdout
    assert isinstance(completed.stdout, str)
    return completed.stdout.rstrip("\n")


def _require_regular_live_head_blob(
    repository_path: str, *, commit: str = "HEAD"
) -> bytes:
    live_path = _REPOSITORY / repository_path
    try:
        metadata = live_path.lstat()
    except OSError as error:
        raise _PreflightError(f"missing bound source {repository_path}") from error
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise _PreflightError(f"{repository_path} must be one ordinary file")
    live = live_path.read_bytes()
    committed = _git("cat-file", "blob", f"{commit}:{repository_path}", binary=True)
    assert isinstance(committed, bytes)
    if committed != live:
        raise _PreflightError(f"live {repository_path} differs from {commit}")
    return live


def _dependency_versions() -> dict[str, str]:
    observed: dict[str, str] = {}
    for key, distribution in _DEPENDENCY_DISTRIBUTIONS.items():
        try:
            observed[key] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            observed[key] = "not-installed"
    return observed


def _pin_repository_source_root() -> Path:
    """Make this worktree the only admissible SpiralLens implementation root."""

    source_root = (_REPOSITORY / "src").resolve()
    source_text = str(source_root)
    for name, module in tuple(sys.modules.items()):
        if name != "spirallens" and not name.startswith("spirallens."):
            continue
        origin = getattr(getattr(module, "__spec__", None), "origin", None)
        file_name = getattr(module, "__file__", None)
        if not isinstance(origin, str) or not isinstance(file_name, str):
            raise _PreflightError(f"preloaded module {name!r} has no file origin")
        try:
            Path(origin).resolve().relative_to(source_root)
            Path(file_name).resolve().relative_to(source_root)
        except ValueError as error:
            raise _PreflightError(
                f"preloaded module {name!r} is outside the current worktree"
            ) from error
    sys.path[:] = [
        item for item in sys.path if Path(item or ".").resolve() != source_root
    ]
    sys.path.insert(0, source_text)
    return source_root


def _require_loaded_spirallens_origins(*, join_head: bool) -> tuple[str, ...]:
    source_root = (_REPOSITORY / "src").resolve()
    observed: list[str] = []
    for name, module in sorted(sys.modules.items()):
        if name != "spirallens" and not name.startswith("spirallens."):
            continue
        origin = getattr(getattr(module, "__spec__", None), "origin", None)
        file_name = getattr(module, "__file__", None)
        if not isinstance(origin, str) or not isinstance(file_name, str):
            raise _PreflightError(f"loaded module {name!r} has no file origin")
        origin_path = Path(origin).resolve()
        file_path = Path(file_name).resolve()
        if origin_path != file_path:
            raise _PreflightError(f"loaded module {name!r} origin/file differ")
        try:
            relative = file_path.relative_to(_REPOSITORY).as_posix()
            file_path.relative_to(source_root)
        except ValueError as error:
            raise _PreflightError(
                f"loaded module {name!r} is outside the current worktree source root"
            ) from error
        if join_head:
            _require_regular_live_head_blob(relative)
        observed.append(name)
    if "spirallens" not in observed:
        raise _PreflightError(
            "SpiralLens root package was not loaded from this worktree"
        )
    return tuple(observed)


def _validate_context_bank_binding(freeze: Mapping[str, object]) -> None:
    try:
        from spirallens.contexts import ContextRole, load_context_bank
    except BaseException as error:
        raise _PreflightError(
            "cannot import bound context-bank implementation"
        ) from error
    binding = _mapping(
        _mapping(freeze["bindings"], label="freeze.bindings")["context_bank"],
        label="context bank binding",
    )
    try:
        loaded = load_context_bank(
            _REPOSITORY / str(binding["path"]),
            allowed_roles={ContextRole.DISCOVERY},
            expected_source_sha256=str(binding["source_sha256"]),
            expected_canonical_sha256=str(binding["canonical_sha256"]),
        )
    except BaseException as error:
        raise _PreflightError(
            "bound discovery context bank failed validation"
        ) from error
    bank = loaded.bank
    expected_context_ids = list(
        _sequence(
            _mapping(
                _mapping(freeze["input_plan"], label="input plan")["contexts"],
                label="input contexts",
            )["ordered_ids"],
            label="ordered context IDs",
        )
    )
    if (
        bank.bank_id != binding["bank_id"]
        or bank.status.value != binding["status"]
        or bank.role.value != binding["role"]
        or bank.claim_eligible is not binding["claim_eligible"]
        or [context.context_id for context in bank.contexts] != expected_context_ids
        or bank.model.model_id != _MODEL_ID
        or bank.model.resolved_revision != _MODEL_REVISION
        or bank.model.vocab_size != 50_304
    ):
        raise _PreflightError("bound discovery context-bank values differ")


def _probe_native_no_replace() -> str:
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        function = getattr(libc, "renameatx_np", None)
        if function is None:
            raise _PreflightError("Darwin renameatx_np is unavailable")
        return "darwin.renameatx_np.RENAME_EXCL"
    if sys.platform.startswith("linux"):
        function = getattr(libc, "renameat2", None)
        if function is None:
            raise _PreflightError("Linux renameat2 is unavailable")
        return "linux.renameat2.RENAME_NOREPLACE"
    raise _PreflightError("native no-replace directory promotion is unsupported")


def _load_freeze() -> tuple[dict[str, object], bytes]:
    source = _read_bounded(
        _REPOSITORY / _FREEZE_RELATIVE,
        _FREEZE_MAX_BYTES,
        label="development freeze",
    )
    if _sha256(source) != _FREEZE_SHA256:
        raise _PreflightError("development freeze source SHA-256 differs")
    document = _strict_json_bytes(source, label="development freeze")
    if document.get("freeze_id") != "pythia70-gate-state-development-v0.1":
        raise _PreflightError("development freeze ID differs")
    if document.get("status") != "frozen_not_run":
        raise _PreflightError("development freeze status differs")
    return document, source


def _source_sha256(path: str, expected: object, *, label: str) -> bytes:
    digest = _require_lower_hex(expected, 64, label=f"{label}.source_sha256")
    source = _require_regular_live_head_blob(path)
    if _sha256(source) != digest:
        raise _PreflightError(f"{label} source SHA-256 differs")
    return source


@dataclass(frozen=True, slots=True)
class _Preflight:
    freeze: dict[str, object]
    launch: dict[str, object]
    freeze_source: bytes
    launch_source: bytes
    launch_sha256: str
    runner_source: bytes
    runtime_source_commit: str
    no_replace_primitive: str


def _validate_bound_sources(freeze: Mapping[str, object]) -> None:
    bindings = _mapping(freeze["bindings"], label="freeze.bindings")
    simple = (
        "context_bank",
        "public_example_comparator",
        "candidate_registry",
        "referent_contract_set",
        "numeric_reference_implementation",
        "strict_route",
        "claim_ladder",
        "fundamental_frame",
    )
    for key in simple:
        item = _mapping(bindings[key], label=f"freeze.bindings.{key}")
        _source_sha256(
            str(item["path"]), item["source_sha256"], label=f"freeze.bindings.{key}"
        )
    for index, raw in enumerate(
        _sequence(
            bindings["graph_and_transport_reference_implementations"],
            label="freeze graph implementation bindings",
        )
    ):
        item = _mapping(raw, label=f"graph implementation binding {index}")
        _source_sha256(
            str(item["path"]),
            item["source_sha256"],
            label=f"graph implementation binding {index}",
        )
    for index, raw in enumerate(
        _sequence(bindings["policy_documents"], label="freeze policy documents")
    ):
        item = _mapping(raw, label=f"policy document binding {index}")
        _source_sha256(
            str(item["path"]),
            item["source_sha256"],
            label=f"policy document binding {index}",
        )
    route = _mapping(freeze["route_amendment"], label="freeze.route_amendment")
    _source_sha256(
        str(route["path"]), route["source_sha256"], label="freeze.route_amendment"
    )


def _validate_launch(
    freeze: Mapping[str, object], launch: Mapping[str, object], launch_source: bytes
) -> None:
    contract = _mapping(
        freeze["launch_authorization_contract"], label="launch authorization contract"
    )
    expected_root = [
        str(item)
        for item in _sequence(
            contract["required_root_fields"], label="launch required root fields"
        )
    ]
    _exact_keys(launch, expected_root, label="launch authorization")
    if launch_source != _canonical_json_bytes(dict(launch)):
        raise _PreflightError(
            "launch authorization bytes are not strict canonical JSON"
        )
    fixed = _mapping(contract["required_fixed_values"], label="launch fixed values")
    for key in ("schema_version", "launch_id", "attempt_id", "status"):
        _require_exact_value(launch.get(key), fixed[key], label=f"launch {key}")
    decision_date = launch.get("decision_date")
    if not isinstance(decision_date, str):
        raise _PreflightError("launch decision_date must be a string")
    try:
        launch_date = date.fromisoformat(decision_date)
        freeze_date = date.fromisoformat(
            str(_mapping(freeze["decision"], label="freeze.decision")["decision_date"])
        )
    except ValueError as error:
        raise _PreflightError("launch or freeze decision date is invalid") from error
    if launch_date < freeze_date:
        raise _PreflightError("launch decision predates the freeze")
    if launch_date.isoformat() != decision_date:
        raise _PreflightError("launch decision_date is not exact ISO-8601 date form")

    required_bindings = _mapping(
        contract["required_bindings"], label="launch required bindings"
    )
    for name, raw_fields in required_bindings.items():
        fields = [
            str(item)
            for item in _sequence(raw_fields, label=f"launch {name} required fields")
        ]
        _exact_keys(
            _mapping(launch[name], label=f"launch.{name}"),
            fields,
            label=f"launch.{name}",
        )

    bindings = _mapping(freeze["bindings"], label="freeze.bindings")
    expected_freeze = {
        "path": _FREEZE_RELATIVE,
        "source_sha256": _sha256(
            _read_bounded(
                _REPOSITORY / _FREEZE_RELATIVE,
                _FREEZE_MAX_BYTES,
                label="development freeze",
            )
        ),
        "freeze_id": freeze["freeze_id"],
    }
    _require_exact_value(
        launch["freeze"], expected_freeze, label="launch freeze binding"
    )
    frozen_context = dict(
        _mapping(bindings["context_bank"], label="freeze.bindings.context_bank")
    )
    _require_exact_value(
        launch["context_bank"], frozen_context, label="launch context bank binding"
    )
    route = _mapping(freeze["route_amendment"], label="freeze.route_amendment")
    expected_route = {
        key: route[key]
        for key in ("path", "source_sha256", "route_id", "execution_class")
    }
    _require_exact_value(launch["route"], expected_route, label="launch route binding")
    _require_exact_value(
        launch["execution_class"],
        route["execution_class"],
        label="launch execution class",
    )
    frame = _mapping(bindings["fundamental_frame"], label="freeze fundamental frame")
    expected_frame = {
        key: frame[key] for key in ("path", "source_sha256", "ledger_amendment_anchor")
    }
    _require_exact_value(launch["frame"], expected_frame, label="launch frame binding")
    policy = [
        _mapping(item, label=f"freeze policy document {index}")
        for index, item in enumerate(
            _sequence(bindings["policy_documents"], label="freeze policy documents")
        )
    ]
    expected_policy = {
        "ledger_path": policy[0]["path"],
        "ledger_sha256": policy[0]["source_sha256"],
        "roadmap_path": policy[1]["path"],
        "roadmap_sha256": policy[1]["source_sha256"],
        "next_experiment_preparation_path": policy[2]["path"],
        "next_experiment_preparation_sha256": policy[2]["source_sha256"],
    }
    _require_exact_value(
        launch["merged_policy_docs"],
        expected_policy,
        label="launch merged policy binding",
    )

    artifacts = _mapping(freeze["artifact_coordinates"], label="artifact coordinates")
    runner = _mapping(launch["runner"], label="launch.runner")
    if runner["path"] != artifacts["prospective_runner_path"]:
        raise _PreflightError("launch runner path differs")
    runner_digest = _require_lower_hex(
        runner["source_sha256"], 64, label="launch runner source SHA-256"
    )
    if runner_digest != _sha256((_REPOSITORY / _RUNNER_RELATIVE).read_bytes()):
        raise _PreflightError("launch runner source SHA-256 differs")
    implementation_commit = _require_lower_hex(
        runner["implementation_commit"], 40, label="runner implementation commit"
    )
    committed_runner = _git(
        "cat-file", "blob", f"{implementation_commit}:{_RUNNER_RELATIVE}", binary=True
    )
    assert isinstance(committed_runner, bytes)
    if committed_runner != (_REPOSITORY / _RUNNER_RELATIVE).read_bytes():
        raise _PreflightError("implementation commit runner blob differs")
    ancestor = subprocess.run(
        [
            "/usr/bin/git",
            "--no-replace-objects",
            "merge-base",
            "--is-ancestor",
            implementation_commit,
            "HEAD",
        ],
        cwd=_REPOSITORY,
        env={
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": "/usr/bin:/bin",
        },
        check=False,
        capture_output=True,
    )
    if ancestor.returncode != 0:
        raise _PreflightError("runner implementation commit is not an ancestor of HEAD")

    command = _mapping(launch["command"], label="launch.command")
    exact_argv = _sequence(command["exact_argv"], label="launch exact argv")
    if not exact_argv or any(not isinstance(item, str) for item in exact_argv):
        raise _PreflightError("launch exact argv must be a nonempty string array")
    if command["working_directory"] != str(_REPOSITORY):
        raise _PreflightError("launch working directory differs")
    runtime = _mapping(launch["runtime"], label="launch.runtime")
    _require_exact_value(
        runtime["python_executable"],
        sys.executable,
        label="launch Python executable",
    )
    if runtime["python_version"] != platform.python_version():
        raise _PreflightError("launch Python version differs")
    dependencies = _mapping(
        runtime["dependency_versions"], label="launch dependency versions"
    )
    observed_dependencies = _dependency_versions()
    _require_exact_value(
        dict(dependencies), observed_dependencies, label="launch dependency versions"
    )

    frozen_model = _mapping(bindings["model"], label="freeze model")
    expected_model = {
        "id": frozen_model["id"],
        "revision": frozen_model["revision"],
        "file_sha256_and_sizes": frozen_model["files"],
    }
    _require_exact_value(launch["model"], expected_model, label="launch model binding")
    expected_artifacts = {
        "external_staging_path": artifacts["external_staging_path"],
        "external_store_path": artifacts["external_store_path"],
        "external_next_hypotheses_path": artifacts["external_next_hypotheses_path"],
        "repository_projection_paths": [
            artifacts["attempt_record"],
            artifacts["terminal_result"],
            artifacts["next_hypotheses"],
        ],
    }
    _require_exact_value(
        launch["artifacts"], expected_artifacts, label="launch artifact coordinates"
    )
    expected_absence = [
        artifacts["external_staging_path"],
        artifacts["external_store_path"],
        artifacts["external_next_hypotheses_path"],
        artifacts["attempt_record"],
        artifacts["terminal_result"],
        artifacts["next_hypotheses"],
    ]
    expected_absence_binding = {
        "coordinates_required_absent": expected_absence,
        "runner_must_observe_absence_and_exclusively_start_in_same_process": True,
    }
    _require_exact_value(
        launch["absence_precondition"],
        expected_absence_binding,
        label="launch absence precondition",
    )
    budget = _mapping(freeze["resource_budget"], label="freeze resource budget")
    expected_budget = {
        "wall_clock_seconds_hard": budget["wall_clock_seconds_hard"],
        "model_loads_maximum": budget["model_loads_maximum"],
        "forward_batches_maximum": budget["forward_batches_maximum"],
        "byte_limits": {
            "raw_capture_bytes_hard": budget["raw_capture_bytes_hard"],
            "terminal_result_bytes_hard": budget["terminal_result_bytes_hard"],
            "next_hypotheses_bytes_hard": budget["next_hypotheses_bytes_hard"],
            "max_estimated_peak_bytes": budget["max_estimated_peak_bytes"],
        },
    }
    _require_exact_value(
        launch["resource_budget"], expected_budget, label="launch resource budget"
    )
    _require_exact_value(
        launch["authorizations"],
        {
            "operator_authorized_exact_one_attempt": True,
            "execution_authorized": True,
            "model_access_authorized": True,
        },
        label="launch authorizations",
    )
    claim = _mapping(freeze["claim_boundary"], label="freeze claim boundary")
    expected_claim = {
        key: claim[key]
        for key in (
            "claim_ceiling",
            "claim_delta",
            "milestone_credit",
            "evidence_eligible",
        )
    }
    _require_exact_value(
        launch["claim_boundary"], expected_claim, label="launch claim boundary"
    )


def _preflight(*, validate_launch_only: bool) -> _Preflight:
    if Path.cwd().resolve() != _REPOSITORY:
        raise _PreflightError("runner working directory differs from repository root")
    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise _PreflightError("runner requires O_DIRECTORY and O_NOFOLLOW")
    _pin_repository_source_root()
    freeze, freeze_source = _load_freeze()
    launch_source = _read_bounded(
        _REPOSITORY / _LAUNCH_RELATIVE,
        _LAUNCH_MAX_BYTES,
        label="launch authorization",
    )
    launch = _strict_json_bytes(launch_source, label="launch authorization")
    _validate_bound_sources(freeze)
    _validate_context_bank_binding(freeze)
    _require_loaded_spirallens_origins(join_head=True)
    _validate_launch(freeze, launch, launch_source)
    top = _git("rev-parse", "--show-toplevel")
    if top != str(_REPOSITORY):
        raise _PreflightError("Git repository root differs")
    runtime_commit = _require_lower_hex(
        _git("rev-parse", "--verify", "HEAD^{commit}"),
        40,
        label="runtime source commit",
    )
    status = _git("status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise _PreflightError("runner requires an exactly clean worktree")
    runner_source = _require_regular_live_head_blob(_RUNNER_RELATIVE)
    _require_regular_live_head_blob(_FREEZE_RELATIVE)
    primitive = _probe_native_no_replace()
    _observe_required_absence(freeze)
    if not validate_launch_only:
        exact_argv = list(
            _sequence(
                _mapping(launch["command"], label="launch.command")["exact_argv"],
                label="launch exact argv",
            )
        )
        observed_argv = list(getattr(sys, "orig_argv", [sys.executable, *sys.argv]))
        if exact_argv != observed_argv:
            raise _PreflightError("runtime argv differs from launch exact argv")
    return _Preflight(
        freeze=freeze,
        launch=launch,
        freeze_source=freeze_source,
        launch_source=launch_source,
        launch_sha256=_sha256(launch_source),
        runner_source=runner_source,
        runtime_source_commit=runtime_commit,
        no_replace_primitive=primitive,
    )


def _artifact_paths(freeze: Mapping[str, object]) -> dict[str, Path]:
    artifacts = _mapping(freeze["artifact_coordinates"], label="artifact coordinates")
    result: dict[str, Path] = {}
    for key in (
        "external_staging_path",
        "external_store_path",
        "external_next_hypotheses_path",
    ):
        result[key] = Path(str(artifacts[key]))
    for key in ("attempt_record", "terminal_result", "next_hypotheses"):
        result[key] = _REPOSITORY / str(artifacts[key])
    return result


def _observe_required_absence(freeze: Mapping[str, object]) -> tuple[str, ...]:
    paths = _artifact_paths(freeze)
    ordered = (
        "external_staging_path",
        "external_store_path",
        "external_next_hypotheses_path",
        "attempt_record",
        "terminal_result",
        "next_hypotheses",
    )
    for key in ordered:
        try:
            os.lstat(paths[key])
        except FileNotFoundError:
            continue
        except OSError as error:
            raise _PreflightError(f"cannot observe absence of {key}") from error
        raise _PreflightError(f"required absent coordinate already exists: {key}")
    for key in ("attempt_record", "terminal_result"):
        path = paths[key]
        temporary = path.parent / f".{path.name}.pythia70-gate-state-v0-1.staging"
        try:
            os.lstat(temporary)
        except FileNotFoundError:
            continue
        except OSError as error:
            raise _PreflightError(
                f"cannot observe absence of repository projection staging for {key}"
            ) from error
        raise _PreflightError(f"repository projection staging already exists for {key}")
    return ordered


def _open_absolute_directory(path: Path) -> int:
    if not path.is_absolute():
        raise _RunError("terminal_persistence", "directory anchor must be absolute")
    descriptor = os.open("/", _DIRECTORY_FLAGS)
    try:
        for component in path.parts[1:]:
            child = os.open(component, _DIRECTORY_FLAGS, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _stat_identity(metadata: os.stat_result) -> tuple[int, int, int]:
    return metadata.st_dev, metadata.st_ino, stat.S_IFMT(metadata.st_mode)


def _entry_metadata(parent_fd: int, name: str) -> os.stat_result | None:
    try:
        return os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None


def _require_live_directory_anchor(path: Path, descriptor: int, *, stage: str) -> None:
    live = _open_absolute_directory(path)
    try:
        if _stat_identity(os.fstat(live)) != _stat_identity(os.fstat(descriptor)):
            raise _RunError(stage, "held directory anchor differs from live path")
    finally:
        os.close(live)


def _write_all(descriptor: int, source: bytes) -> None:
    view = memoryview(source)
    while view:
        written = os.write(descriptor, view)
        if written < 1:
            raise OSError(errno.EIO, "write made no progress")
        view = view[written:]


def _read_descriptor(descriptor: int, maximum: int) -> bytes:
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    remaining = maximum + 1
    while remaining:
        chunk = os.read(descriptor, min(1024 * 1024, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    source = b"".join(chunks)
    if len(source) > maximum:
        raise _RunError("terminal_persistence", "bounded descriptor read overflowed")
    return source


def _write_exclusive_at(
    parent_fd: int,
    name: str,
    source: bytes,
    *,
    maximum: int,
    stage: str,
) -> int:
    if len(source) > maximum:
        raise _RunError(stage, f"{name} exceeds its byte limit")
    descriptor = -1
    try:
        descriptor = os.open(name, _FILE_WRITE_FLAGS, 0o600, dir_fd=parent_fd)
        os.fchmod(descriptor, 0o600)
        _write_all(descriptor, source)
        os.fsync(descriptor)
        held = os.fstat(descriptor)
        live = _entry_metadata(parent_fd, name)
        if (
            live is None
            or _stat_identity(live) != _stat_identity(held)
            or not stat.S_ISREG(held.st_mode)
            or held.st_nlink != 1
            or stat.S_IMODE(held.st_mode) != 0o600
            or held.st_size != len(source)
            or _read_descriptor(descriptor, maximum) != source
        ):
            raise _RunError(stage, f"exclusive file {name!r} failed reread")
        os.fsync(parent_fd)
        return descriptor
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        raise


@dataclass(slots=True)
class _OwnedStage:
    parent_path: Path
    stage_name: str
    store_name: str
    parent_fd: int
    stage_fd: int
    file_fds: list[int] = field(default_factory=list)
    published: bool = False

    def close(self) -> None:
        for descriptor in self.file_fds:
            with contextlib.suppress(OSError):
                os.close(descriptor)
        self.file_fds.clear()
        for field_name in ("stage_fd", "parent_fd"):
            descriptor = getattr(self, field_name)
            if descriptor >= 0:
                with contextlib.suppress(OSError):
                    os.close(descriptor)
                setattr(self, field_name, -1)


def _reserve_stage(freeze: Mapping[str, object]) -> tuple[_OwnedStage, os.stat_result]:
    paths = _artifact_paths(freeze)
    stage_path = paths["external_staging_path"]
    store_path = paths["external_store_path"]
    if stage_path.parent != store_path.parent:
        raise _RunError("terminal_persistence", "stage/store parents differ")
    parent_fd = _open_absolute_directory(stage_path.parent)
    stage_fd = -1
    try:
        _require_live_directory_anchor(
            stage_path.parent, parent_fd, stage="terminal_persistence"
        )
        if _entry_metadata(parent_fd, stage_path.name) is not None:
            raise _RunError("terminal_persistence", "external stage already exists")
        if _entry_metadata(parent_fd, store_path.name) is not None:
            raise _RunError("terminal_persistence", "external store already exists")
        os.mkdir(stage_path.name, 0o700, dir_fd=parent_fd)
        stage_fd = os.open(stage_path.name, _DIRECTORY_FLAGS, dir_fd=parent_fd)
        os.fchmod(stage_fd, 0o700)
        os.fsync(parent_fd)
        held = os.fstat(stage_fd)
        live = _entry_metadata(parent_fd, stage_path.name)
        if (
            live is None
            or _stat_identity(live) != _stat_identity(held)
            or not stat.S_ISDIR(held.st_mode)
            or stat.S_IMODE(held.st_mode) != 0o700
        ):
            raise _RunError("terminal_persistence", "reserved stage identity differs")
        _require_live_directory_anchor(
            stage_path.parent, parent_fd, stage="terminal_persistence"
        )
        stage = _OwnedStage(
            parent_path=stage_path.parent,
            stage_name=stage_path.name,
            store_name=store_path.name,
            parent_fd=parent_fd,
            stage_fd=stage_fd,
        )
        parent_fd = -1
        stage_fd = -1
        return stage, held
    finally:
        if stage_fd >= 0:
            os.close(stage_fd)
        if parent_fd >= 0:
            os.close(parent_fd)


def _promote_stage(stage: _OwnedStage) -> None:
    if stage.published:
        raise _RunError("terminal_persistence", "stage was already promoted")
    _require_live_directory_anchor(
        stage.parent_path, stage.parent_fd, stage="terminal_persistence"
    )
    held = os.fstat(stage.stage_fd)

    def namespace_state() -> str:
        live_stage = _entry_metadata(stage.parent_fd, stage.stage_name)
        live_store = _entry_metadata(stage.parent_fd, stage.store_name)
        staged = (
            live_stage is not None
            and _stat_identity(live_stage) == _stat_identity(held)
            and live_store is None
        )
        published = (
            live_stage is None
            and live_store is not None
            and _stat_identity(live_store) == _stat_identity(held)
        )
        if staged:
            return "staged"
        if published:
            return "published"
        return "invalid"

    if namespace_state() != "staged":
        raise _RunError(
            "terminal_persistence", "stage namespace differs before promotion"
        )
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
        raise _RunError("terminal_persistence", "native no-replace rename unavailable")
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
        os.fsencode(stage.stage_name),
        stage.parent_fd,
        os.fsencode(stage.store_name),
        flag,
    )
    observed_errno = ctypes.get_errno() or errno.EIO
    observed_namespace = namespace_state()
    if observed_namespace == "published":
        stage.published = True
        try:
            os.fsync(stage.parent_fd)
        except OSError as error:
            raise _RunError(
                "terminal_persistence",
                "promoted namespace exists but parent fsync failed",
            ) from error
        _require_live_directory_anchor(
            stage.parent_path, stage.parent_fd, stage="terminal_persistence"
        )
        if namespace_state() != "published":
            raise _RunError("terminal_persistence", "promoted store identity changed")
        return
    if observed_namespace != "staged":
        raise _RunError("terminal_persistence", "promotion left an invalid namespace")
    if result == 0:
        raise _RunError(
            "terminal_persistence", "native promotion reported success without rename"
        )
    raise _RunError(
        "terminal_persistence",
        f"native no-replace promotion failed with errno {observed_errno}",
    )


class _SignalLatch:
    def __init__(self) -> None:
        self.signum: int | None = None
        self._previous: dict[int, Any] = {}
        self._previous_timer: tuple[float, float] | None = None

    def __enter__(self) -> Self:
        numbers = [signal.SIGINT, signal.SIGTERM]
        if hasattr(signal, "SIGHUP"):
            numbers.append(signal.SIGHUP)
        if hasattr(signal, "SIGALRM") and hasattr(signal, "ITIMER_REAL"):
            numbers.append(signal.SIGALRM)
        for number in numbers:
            self._previous[number] = signal.getsignal(number)
            signal.signal(number, self._handler)
        return self

    def __exit__(self, *_args: object) -> None:
        if self._previous_timer is not None:
            signal.setitimer(signal.ITIMER_REAL, *self._previous_timer)
        for number, handler in self._previous.items():
            signal.signal(number, handler)

    def _handler(self, signum: int, _frame: object) -> None:
        if self.signum is None:
            self.signum = signum

    def check(self) -> None:
        if self.signum is not None:
            raise _DeferredSignal(f"deferred signal {self.signum}")

    def arm_wall_limit(self, seconds: float) -> None:
        if seconds <= 0.0:
            raise _DeferredSignal("wall-clock budget is already exhausted")
        if hasattr(signal, "ITIMER_REAL"):
            self._previous_timer = signal.setitimer(signal.ITIMER_REAL, seconds)


_ERROR_STAGES = frozenset(
    {
        "model_file_hash",
        "model_load",
        "capture",
        "raw_capture_persist",
        "graph_construction",
        "f2_f4_derivation",
        "gate_evaluation",
        "resource_budget",
        "terminal_serialization",
        "terminal_persistence",
    }
)


@dataclass(slots=True)
class _RunState:
    preflight: _Preflight
    stage: _OwnedStage
    started_at_utc: str
    started_monotonic: float
    attempt_source: bytes
    attempt_sha256: str
    observed_model_file_slots: list[dict[str, object]] = field(default_factory=list)
    capture_manifest: list[dict[str, object]] = field(default_factory=list)
    graph_receipts: list[dict[str, object]] = field(default_factory=list)
    gate_records: list[dict[str, object]] = field(default_factory=list)
    cell_records: list[dict[str, object]] = field(default_factory=list)
    model_loads: int = 0
    forward_batches: int = 0
    raw_capture_bytes: int = 0
    active_stage: str = "model_file_hash"

    @property
    def freeze(self) -> Mapping[str, object]:
        return self.preflight.freeze

    @property
    def budget(self) -> Mapping[str, object]:
        return _mapping(self.freeze["resource_budget"], label="resource budget")

    def wall_clock_seconds(self) -> float:
        return max(0.0, time.monotonic() - self.started_monotonic)

    def hard_limit_breaches(self) -> list[str]:
        checks = {
            "wall_clock_seconds": (
                self.wall_clock_seconds(),
                float(self.budget["wall_clock_seconds_hard"]),
            ),
            "model_loads": (
                self.model_loads,
                int(self.budget["model_loads_maximum"]),
            ),
            "forward_batches": (
                self.forward_batches,
                int(self.budget["forward_batches_maximum"]),
            ),
            "raw_capture_bytes": (
                self.raw_capture_bytes,
                int(self.budget["raw_capture_bytes_hard"]),
            ),
            "peak_bytes_estimated_not_measured": (
                int(self.budget["estimated_peak_bytes"]),
                int(self.budget["max_estimated_peak_bytes"]),
            ),
        }
        return sorted(
            name for name, (actual, limit) in checks.items() if actual > limit
        )

    def checkpoint(self, signals: _SignalLatch) -> None:
        if self.hard_limit_breaches():
            self.active_stage = "resource_budget"
            raise _RunError(
                "resource_budget", "one or more hard resource limits exceeded"
            )
        signals.check()


@contextlib.contextmanager
def _active_stage(state: _RunState, stage: str) -> Iterable[None]:
    if stage not in _ERROR_STAGES:
        raise AssertionError(f"unknown runner stage {stage!r}")
    previous = state.active_stage
    state.active_stage = stage
    try:
        yield
    except Exception:
        state.active_stage = stage
        raise
    else:
        state.active_stage = previous


def _build_attempt_record(
    preflight: _Preflight,
    *,
    observed_at_utc: str,
    reserved_at_utc: str,
    stage_metadata: os.stat_result,
) -> dict[str, object]:
    _require_utc_timestamp(observed_at_utc, label="attempt observed_at_utc")
    _require_utc_timestamp(reserved_at_utc, label="attempt reserved_at_utc")
    if observed_at_utc > reserved_at_utc:
        raise _RunError(
            "terminal_persistence", "attempt observation occurs after reservation"
        )
    freeze = preflight.freeze
    launch = preflight.launch
    lifecycle = _mapping(freeze["lifecycle"], label="freeze.lifecycle")
    contract = _mapping(
        lifecycle["attempt_record_contract"], label="attempt record contract"
    )
    artifacts = _mapping(freeze["artifact_coordinates"], label="artifact coordinates")
    bindings = _mapping(freeze["bindings"], label="freeze.bindings")
    observed_absent = [
        "external_staging_path",
        "external_store_path",
        "external_next_hypotheses_path",
        "attempt_record",
        "terminal_result",
        "next_hypotheses",
    ]
    document: dict[str, object] = {
        "schema_version": contract["schema_version"],
        "attempt_id": launch["attempt_id"],
        "launch_id": launch["launch_id"],
        "started_at_utc": reserved_at_utc,
        "absence_and_reservation": {
            "observed_at_utc": observed_at_utc,
            "observed_absent_coordinates": observed_absent,
            "reserved_at_utc": reserved_at_utc,
            "stage_path": artifacts["external_staging_path"],
            "stage_device": stage_metadata.st_dev,
            "stage_inode": stage_metadata.st_ino,
            "stage_mode": stat.S_IMODE(stage_metadata.st_mode),
            "parent_directory_fsynced": True,
        },
        "bindings": {
            "launch_authorization_sha256": preflight.launch_sha256,
            "freeze_source_sha256": _sha256(preflight.freeze_source),
            "context_bank_source_sha256": _mapping(
                bindings["context_bank"], label="context bank binding"
            )["source_sha256"],
            "context_bank_canonical_sha256": _mapping(
                bindings["context_bank"], label="context bank binding"
            )["canonical_sha256"],
            "route_source_sha256": _mapping(
                freeze["route_amendment"], label="route amendment"
            )["source_sha256"],
            "runner_source_sha256": _sha256(preflight.runner_source),
            "runner_implementation_commit": _mapping(
                launch["runner"], label="launch.runner"
            )["implementation_commit"],
            "runtime_source_commit": preflight.runtime_source_commit,
            "exact_argv": _mapping(launch["command"], label="launch.command")[
                "exact_argv"
            ],
            "runtime_versions": launch["runtime"],
            "expected_model_file_sha256_and_sizes": _mapping(
                bindings["model"], label="freeze model binding"
            )["files"],
            "all_external_and_repository_coordinates": dict(artifacts),
            "resource_budget": freeze["resource_budget"],
            "claim_boundary": freeze["claim_boundary"],
        },
        "artifact_coordinates": dict(artifacts),
        "resource_budget": freeze["resource_budget"],
        "claim_boundary": freeze["claim_boundary"],
    }
    expected_root = [
        str(item)
        for item in _sequence(contract["root_fields"], label="attempt root fields")
    ]
    _exact_keys(document, expected_root, label="attempt record")
    expected_binding_fields = [
        str(item)
        for item in _sequence(
            lifecycle["attempt_record_required_bindings"],
            label="attempt required bindings",
        )
    ]
    _exact_keys(
        _mapping(document["bindings"], label="attempt.bindings"),
        expected_binding_fields,
        label="attempt.bindings",
    )
    return document


def _write_attempt(
    preflight: _Preflight,
    stage: _OwnedStage,
    *,
    observed_at_utc: str,
    reserved_at_utc: str,
    stage_metadata: os.stat_result,
) -> tuple[bytes, str]:
    document = _build_attempt_record(
        preflight,
        observed_at_utc=observed_at_utc,
        reserved_at_utc=reserved_at_utc,
        stage_metadata=stage_metadata,
    )
    source = _canonical_json_bytes(document)
    descriptor = _write_exclusive_at(
        stage.stage_fd,
        "attempt.json",
        source,
        maximum=_JSON_MAX_BYTES,
        stage="terminal_persistence",
    )
    stage.file_fds.append(descriptor)
    reloaded = _strict_json_bytes(source, label="attempt record")
    if _canonical_json_bytes(reloaded) != source:
        raise _RunError("terminal_persistence", "attempt record strict reload differs")
    return source, _sha256(source)


def _not_run_model_slot(relative_name: str) -> dict[str, object]:
    return {
        "relative_name": relative_name,
        "status": "not_run",
        "size_bytes": None,
        "sha256": None,
        "error_type": None,
        "error_message": None,
    }


def _bounded_model_file_observation(
    snapshot: Path,
    relative_name: str,
    expected: Mapping[str, object],
) -> dict[str, object]:
    record: dict[str, object] = {
        "relative_name": relative_name,
        "status": "read_error",
        "size_bytes": None,
        "sha256": None,
        "error_type": None,
        "error_message": None,
    }
    candidate = snapshot / relative_name
    try:
        lexical = candidate.lstat()
    except FileNotFoundError:
        record.update(status="missing", error_message="file_missing")
        return record
    except OSError as error:
        record.update(error_type=type(error).__name__, error_message=str(error))
        return record
    repository_cache_root = snapshot.parent.parent
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(repository_cache_root.resolve(strict=True))
        metadata = resolved.stat()
        if not (stat.S_ISREG(metadata.st_mode) and metadata.st_nlink >= 1):
            raise OSError("resolved model member is not an ordinary file")
        if not (stat.S_ISREG(lexical.st_mode) or stat.S_ISLNK(lexical.st_mode)):
            raise OSError("snapshot model member is not a file or symlink")
        expected_size = int(expected["size_bytes"])
        if metadata.st_size > max(expected_size, 1) + 1:
            raise OSError("model member exceeds its frozen bounded read")
        descriptor = os.open(resolved, _FILE_READ_FLAGS)
        try:
            held_before = os.fstat(descriptor)
            source = _read_descriptor(descriptor, expected_size + 1)
            held_after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        if _stat_identity(held_before) != _stat_identity(held_after):
            raise OSError("model member changed during its read")
        digest = _sha256(source)
        record.update(
            status="verified",
            size_bytes=len(source),
            sha256=digest,
            error_type=None,
            error_message=None,
        )
        if len(source) != expected_size or digest != expected["sha256"]:
            record["status"] = "mismatch"
        return record
    except Exception as error:  # noqa: BLE001 - persist exact read-error class.
        record.update(error_type=type(error).__name__, error_message=str(error))
        return record


def _resolve_and_verify_model_files(state: _RunState) -> Path:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    try:
        from huggingface_hub import snapshot_download

        snapshot = Path(
            snapshot_download(
                repo_id=_MODEL_ID,
                revision=_MODEL_REVISION,
                local_files_only=True,
                allow_patterns=["config.json", "model.safetensors"],
            )
        ).resolve(strict=True)
        if not snapshot.is_dir():
            raise OSError("resolved model snapshot is not a directory")
    except BaseException as error:
        state.observed_model_file_slots = [
            {
                "relative_name": "config.json",
                "status": "read_error",
                "size_bytes": None,
                "sha256": None,
                "error_type": type(error).__name__,
                "error_message": str(error),
            },
            _not_run_model_slot("model.safetensors"),
        ]
        raise _RunError(
            "model_file_hash", "local-only model snapshot resolution failed"
        ) from error
    expected_files = _mapping(
        _mapping(
            _mapping(state.freeze["bindings"], label="freeze.bindings")["model"],
            label="freeze model",
        )["files"],
        label="expected model files",
    )
    records: list[dict[str, object]] = []
    for index, relative_name in enumerate(("config.json", "model.safetensors")):
        if records and records[-1]["status"] != "verified":
            records.append(_not_run_model_slot(relative_name))
            continue
        expected = _mapping(expected_files[relative_name], label=relative_name)
        records.append(
            _bounded_model_file_observation(snapshot, relative_name, expected)
        )
        if records[-1]["status"] != "verified":
            for later in ("config.json", "model.safetensors")[index + 1 :]:
                records.append(_not_run_model_slot(later))
            break
    state.observed_model_file_slots = records
    if len(records) != 2 or any(record["status"] != "verified" for record in records):
        raise _RunError("model_file_hash", "model file observation did not verify")
    return snapshot


def _reverify_model_files(state: _RunState, snapshot: Path) -> None:
    expected_files = _mapping(
        _mapping(
            _mapping(state.freeze["bindings"], label="freeze.bindings")["model"],
            label="freeze model",
        )["files"],
        label="expected model files",
    )
    observed = [
        _bounded_model_file_observation(
            snapshot,
            relative_name,
            _mapping(expected_files[relative_name], label=relative_name),
        )
        for relative_name in ("config.json", "model.safetensors")
    ]
    if not _deep_exact_equal(observed, state.observed_model_file_slots):
        raise _RunError("model_load", "verified model files changed around load")


def _load_exact_model(state: _RunState, snapshot: Path) -> object:
    state.model_loads += 1
    if state.model_loads > int(state.budget["model_loads_maximum"]):
        raise _RunError("resource_budget", "model load limit exceeded")
    try:
        _pin_repository_source_root()
        _reverify_model_files(state, snapshot)
        from transformers import AutoModelForCausalLM

        from spirallens.adapters import PythiaAdapter

        model = AutoModelForCausalLM.from_pretrained(
            str(snapshot),
            local_files_only=True,
            trust_remote_code=False,
            use_safetensors=True,
        )
        model.to("cpu")
        adapter = PythiaAdapter(
            model,
            model_id=_MODEL_ID,
            revision=_MODEL_REVISION,
        )
        _require_loaded_spirallens_origins(join_head=True)
        _reverify_model_files(state, snapshot)
    except BaseException as error:
        raise _RunError("model_load", "exact local-only model load failed") from error
    metadata = adapter.config_metadata()
    expected = _mapping(
        _mapping(state.freeze["bindings"], label="freeze.bindings")["model"],
        label="freeze model",
    )
    checks = {
        "model_id": expected["id"],
        "resolved_revision": expected["revision"],
        "architecture": expected["architecture"],
        "num_layers": expected["num_layers"],
        "hidden_size": expected["hidden_size"],
        "vocab_size": expected["vocab_size"],
    }
    observed = dict(metadata)
    if observed.get("resolved_revision") is None:
        observed["resolved_revision"] = adapter.revision
    if any(observed.get(key) != value for key, value in checks.items()):
        raise _RunError("model_load", "loaded model metadata differs from freeze")
    return adapter


def _mkdir_open_at(parent_fd: int, name: str, *, stage: str) -> int:
    try:
        os.mkdir(name, 0o700, dir_fd=parent_fd)
        descriptor = os.open(name, _DIRECTORY_FLAGS, dir_fd=parent_fd)
        os.fchmod(descriptor, 0o700)
        os.fsync(parent_fd)
    except OSError as error:
        raise _RunError(stage, f"cannot create private directory {name!r}") from error
    held = os.fstat(descriptor)
    live = _entry_metadata(parent_fd, name)
    if (
        live is None
        or _stat_identity(live) != _stat_identity(held)
        or not stat.S_ISDIR(held.st_mode)
        or stat.S_IMODE(held.st_mode) != 0o700
    ):
        os.close(descriptor)
        raise _RunError(stage, f"private directory {name!r} identity differs")
    return descriptor


@dataclass(slots=True)
class _NpySink:
    descriptor: int
    mapping: mmap.mmap
    array: Float32Array
    parent_fd: int
    name: str
    header_size: int

    @classmethod
    def create(cls, parent_fd: int, name: str) -> _NpySink:
        shape = (49, 6, 512)
        header_stream = io.BytesIO()
        np.lib.format.write_array_header_1_0(
            header_stream,
            {"descr": "<f4", "fortran_order": False, "shape": shape},
        )
        header = header_stream.getvalue()
        total_size = len(header) + int(np.prod(shape)) * np.dtype("<f4").itemsize
        descriptor = -1
        mapped: mmap.mmap | None = None
        try:
            descriptor = os.open(name, _FILE_WRITE_FLAGS, 0o600, dir_fd=parent_fd)
            os.fchmod(descriptor, 0o600)
            os.fsync(parent_fd)
            _write_all(descriptor, header)
            os.ftruncate(descriptor, total_size)
            os.fsync(descriptor)
            os.fsync(parent_fd)
            mapped = mmap.mmap(descriptor, total_size, access=mmap.ACCESS_WRITE)
            array = np.ndarray(
                shape,
                dtype="<f4",
                buffer=mapped,
                offset=len(header),
                order="C",
            )
            return cls(
                descriptor=descriptor,
                mapping=mapped,
                array=array,
                parent_fd=parent_fd,
                name=name,
                header_size=len(header),
            )
        except BaseException:
            if mapped is not None:
                mapped.close()
            if descriptor >= 0:
                os.close(descriptor)
            raise

    def write_rows(self, start: int, values: Float32Array) -> None:
        self.array[start : start + values.shape[0]] = values
        self.mapping.flush()
        os.fsync(self.descriptor)

    def finish(
        self, *, relative_path: str, context_id: str, capture_stage: str
    ) -> dict[str, object]:
        self.mapping.flush()
        os.fsync(self.descriptor)
        source = _read_descriptor(self.descriptor, 2 * 1024 * 1024)
        reloaded = np.load(io.BytesIO(source), allow_pickle=False)
        if (
            reloaded.shape != (49, 6, 512)
            or reloaded.dtype.str != "<f4"
            or not reloaded.flags.c_contiguous
            or not np.array_equal(reloaded, self.array, equal_nan=True)
        ):
            raise _RunError("raw_capture_persist", "persisted capture reread differs")
        raw = np.asarray(self.array, dtype="<f4", order="C").tobytes(order="C")
        return {
            "relative_path": relative_path,
            "context_id": context_id,
            "capture_stage": capture_stage,
            "shape": [49, 6, 512],
            "dtype": "<f4",
            "finite": bool(np.all(np.isfinite(self.array))),
            "raw_array_sha256": _sha256(raw),
            "file_sha256": _sha256(source),
            "size_bytes": len(source),
        }

    def close(self) -> None:
        if hasattr(self, "array"):
            del self.array
        with contextlib.suppress(BufferError, OSError):
            self.mapping.close()
        with contextlib.suppress(OSError):
            os.close(self.descriptor)


def _capture_all(
    state: _RunState,
    adapter: object,
    loaded_bank: object,
    signals: _SignalLatch,
) -> Float32Array:
    import torch

    bank = loaded_bank.bank
    expected_context_ids = list(
        _mapping(
            _mapping(state.freeze["input_plan"], label="input plan")["contexts"],
            label="context plan",
        )["ordered_ids"]
    )
    contexts = list(bank.contexts)
    if [context.context_id for context in contexts] != expected_context_ids:
        raise _RunError("capture", "loaded context order differs from freeze")
    cube = np.empty((8, 2, 49, 6, 512), dtype="<f4")
    raw_fd = _mkdir_open_at(
        state.stage.stage_fd, "raw-captures", stage="raw_capture_persist"
    )
    try:
        for context_index, context in enumerate(contexts):
            state.checkpoint(signals)
            context_fd = _mkdir_open_at(
                raw_fd, context.context_id, stage="raw_capture_persist"
            )
            sinks: list[_NpySink] = []
            try:
                sinks.append(_NpySink.create(context_fd, "resid_pre.npy"))
                sinks.append(_NpySink.create(context_fd, "resid_post.npy"))
                for start in range(0, 49, 7):
                    state.checkpoint(signals)
                    end = start + 7
                    materialized = np.asarray(
                        [
                            context.materialize(
                                int(token_id),
                                model_vocab_size=bank.model.vocab_size,
                            )
                            for token_id in _TOKEN_IDS[start:end]
                        ],
                        dtype="<i8",
                    )
                    mask = np.broadcast_to(
                        np.asarray(context.attention_mask, dtype="<i8"),
                        materialized.shape,
                    ).copy()
                    state.forward_batches += 1
                    if state.forward_batches > int(
                        state.budget["forward_batches_maximum"]
                    ):
                        raise _RunError(
                            "resource_budget", "forward batch limit exceeded"
                        )
                    try:
                        observation = adapter.observe_batch(
                            torch.from_numpy(materialized),
                            position=context.observation_position,
                            attention_mask=torch.from_numpy(mask),
                        )
                    except BaseException as error:
                        raise _RunError(
                            "capture", "Pythia residual capture failed"
                        ) from error
                    batches = (observation.resid_pre, observation.resid_post)
                    for stage_index, tensor in enumerate(batches):
                        if (
                            tensor.device.type != "cpu"
                            or tensor.dtype != torch.float32
                            or tuple(tensor.shape) != (7, 6, 512)
                        ):
                            raise _RunError(
                                "capture", "captured tensor contract differs"
                            )
                        array = np.array(
                            tensor.numpy(), dtype="<f4", order="C", copy=True
                        )
                        if not np.all(np.isfinite(array)):
                            raise _RunError("capture", "captured tensor is non-finite")
                        state.raw_capture_bytes += array.nbytes
                        sinks[stage_index].write_rows(start, array)
                        cube[context_index, stage_index, start:end] = array
                    state.checkpoint(signals)
                records = [
                    sinks[index].finish(
                        relative_path=(
                            f"raw-captures/{context.context_id}/{_STAGES[index]}.npy"
                        ),
                        context_id=context.context_id,
                        capture_stage=_STAGES[index],
                    )
                    for index in range(2)
                ]
                if any(not record["finite"] for record in records):
                    raise _RunError(
                        "capture", "capture manifest contains non-finite data"
                    )
                state.capture_manifest.extend(records)
            finally:
                for sink in sinks:
                    sink.close()
                try:
                    os.fsync(context_fd)
                except OSError as error:
                    raise _RunError(
                        "raw_capture_persist", "context directory fsync failed"
                    ) from error
                finally:
                    os.close(context_fd)
    finally:
        try:
            os.fsync(raw_fd)
        except OSError as error:
            raise _RunError(
                "raw_capture_persist", "raw-capture directory fsync failed"
            ) from error
        finally:
            os.close(raw_fd)
            try:
                os.fsync(state.stage.stage_fd)
            except OSError as error:
                raise _RunError(
                    "raw_capture_persist", "stage directory fsync failed"
                ) from error
    if state.forward_batches != 56 or state.raw_capture_bytes != 9_633_792:
        raise _RunError("resource_budget", "capture resource counts differ from freeze")
    return cube


@dataclass(frozen=True, slots=True)
class _NumericInterfaces:
    GraphInput: Any
    GraphPurpose: Any
    MutualKnnSpec: Any
    RadiusGraphSpec: Any
    SharedNeighborSpec: Any
    construct_mutual_knn: Any
    construct_radius_graph: Any
    construct_shared_neighbor_graph: Any
    validate_observation_partition: Any
    derive_f2_section: Any
    derive_f4_spin_two: Any
    procrustes_connection: Any
    compose_edge_transports: Any
    principal_rotation_angle_2d: Any


def _load_bound_numeric_interfaces(freeze: Mapping[str, object]) -> _NumericInterfaces:
    """Import only the frozen numeric implementations from this worktree."""

    _pin_repository_source_root()
    try:
        import spirallens.topology.winding  # noqa: F401
        from spirallens.gauge.procrustes_connection import procrustes_connection
        from spirallens.graphs.common import GraphPurpose
        from spirallens.graphs.constructors import (
            construct_mutual_knn,
            construct_radius_graph,
            construct_shared_neighbor_graph,
        )
        from spirallens.graphs.contracts import (
            GraphInput,
            MutualKnnSpec,
            RadiusGraphSpec,
            SharedNeighborSpec,
        )
        from spirallens.holonomy.discrete import compose_edge_transports
        from spirallens.holonomy.metrics import principal_rotation_angle_2d
        from spirallens.referents.numeric import (
            derive_f2_section,
            derive_f4_spin_two,
            validate_observation_partition,
        )
    except BaseException as error:
        raise _RunError(
            "f2_f4_derivation", "cannot import frozen numeric implementations"
        ) from error
    required_modules = {
        "spirallens.referents.numeric": _mapping(
            _mapping(freeze["bindings"], label="freeze.bindings")[
                "numeric_reference_implementation"
            ],
            label="numeric implementation binding",
        )["path"]
    }
    for raw in _sequence(
        _mapping(freeze["bindings"], label="freeze.bindings")[
            "graph_and_transport_reference_implementations"
        ],
        label="graph implementation bindings",
    ):
        binding = _mapping(raw, label="graph implementation binding")
        path = str(binding["path"])
        module_name = path.removeprefix("src/").removesuffix(".py").replace("/", ".")
        required_modules[module_name] = path
    for module_name, raw_path in required_modules.items():
        module = sys.modules.get(module_name)
        origin = getattr(getattr(module, "__spec__", None), "origin", None)
        expected = (_REPOSITORY / str(raw_path)).resolve()
        if not isinstance(origin, str) or Path(origin).resolve() != expected:
            raise _RunError(
                "f2_f4_derivation",
                f"frozen implementation origin differs for {module_name}",
            )
    _require_loaded_spirallens_origins(join_head=True)
    return _NumericInterfaces(
        GraphInput=GraphInput,
        GraphPurpose=GraphPurpose,
        MutualKnnSpec=MutualKnnSpec,
        RadiusGraphSpec=RadiusGraphSpec,
        SharedNeighborSpec=SharedNeighborSpec,
        construct_mutual_knn=construct_mutual_knn,
        construct_radius_graph=construct_radius_graph,
        construct_shared_neighbor_graph=construct_shared_neighbor_graph,
        validate_observation_partition=validate_observation_partition,
        derive_f2_section=derive_f2_section,
        derive_f4_spin_two=derive_f4_spin_two,
        procrustes_connection=procrustes_connection,
        compose_edge_transports=compose_edge_transports,
        principal_rotation_angle_2d=principal_rotation_angle_2d,
    )


def _load_context_bank_for_capture(freeze: Mapping[str, object]) -> object:
    try:
        from spirallens.contexts import ContextRole, load_context_bank

        binding = _mapping(
            _mapping(freeze["bindings"], label="freeze.bindings")["context_bank"],
            label="context bank binding",
        )
        loaded = load_context_bank(
            _REPOSITORY / str(binding["path"]),
            allowed_roles={ContextRole.DISCOVERY},
            expected_source_sha256=str(binding["source_sha256"]),
            expected_canonical_sha256=str(binding["canonical_sha256"]),
        )
    except BaseException as error:
        raise _RunError("capture", "bound context bank reload failed") from error
    _require_loaded_spirallens_origins(join_head=True)
    return loaded


@dataclass(frozen=True, slots=True)
class _FrameFit:
    basis: FloatArray
    singular_values: FloatArray
    metrics: tuple[float, float, float]
    minimum_metric: float
    supported: bool
    reason_codes: tuple[str, ...]


def _fit_signed_frame(samples: object, *, minimum_rows: int) -> _FrameFit:
    values = np.asarray(samples, dtype="<f8")
    if values.ndim != 2 or values.shape[1] != 512 or values.shape[0] < 2:
        raise _RunError("f2_f4_derivation", "frame sample matrix shape differs")
    if not np.all(np.isfinite(values)):
        raise _RunError("f2_f4_derivation", "frame samples are non-finite")
    centered = values - np.mean(values, axis=0, dtype=np.float64)
    try:
        _left, singular, right = np.linalg.svd(centered, full_matrices=False)
    except np.linalg.LinAlgError as error:
        raise _RunError("f2_f4_derivation", "frame SVD failed") from error
    if right.shape[0] < 2:
        raise _RunError("f2_f4_derivation", "frame SVD has fewer than two axes")
    basis = np.array(right[:2].T, dtype="<f8", order="C", copy=True)
    for column in range(2):
        anchor = int(np.argmax(np.abs(basis[:, column])))
        if basis[anchor, column] < 0.0:
            basis[:, column] *= -1.0
    padded = np.zeros(3, dtype="<f8")
    padded[: min(3, singular.size)] = singular[:3]
    s1, s2, s3 = (float(item) for item in padded)
    metrics = (
        s2 / s1 if s1 > 0.0 else 0.0,
        (s1 - s2) / s1 if s1 > 0.0 else 0.0,
        (s2 - s3) / s2 if s2 > 0.0 else 0.0,
    )
    reasons: list[str] = []
    if values.shape[0] < minimum_rows:
        reasons.append("insufficient_frame_sample_rows")
    if min(metrics) < 1e-6:
        reasons.append("frame_identifiability_below_floor")
    if not np.allclose(basis.T @ basis, np.eye(2), rtol=1e-12, atol=1e-12):
        raise _RunError("f2_f4_derivation", "frame basis is not orthonormal")
    return _FrameFit(
        basis=basis,
        singular_values=np.array(singular, dtype="<f8", copy=True),
        metrics=metrics,
        minimum_metric=float(min(metrics)),
        supported=not reasons,
        reason_codes=tuple(reasons),
    )


@dataclass(frozen=True, slots=True)
class _GraphLayer:
    family: str
    layer_id: int
    adjacency: tuple[frozenset[int], ...] | None
    local_frames: FloatArray
    local_minimum_metrics: FloatArray
    local_supported: BoolArray
    global_frame: _FrameFit
    global_rotations: FloatArray
    global_minimum_singular_values: FloatArray
    global_supported: BoolArray
    global_reflections: BoolArray


def _graph_specs(interfaces: _NumericInterfaces) -> tuple[tuple[str, object, Any], ...]:
    purpose = interfaces.GraphPurpose.FIELD_ESTIMATION
    return (
        (
            "mutual-knn",
            interfaces.MutualKnnSpec(
                spec_id="pythia70-dev-mutual-knn-k4",
                purpose=purpose,
                neighbor_count=4,
            ),
            interfaces.construct_mutual_knn,
        ),
        (
            "fixed-radius",
            interfaces.RadiusGraphSpec(
                spec_id="pythia70-dev-fixed-radius-0.75",
                purpose=purpose,
                radius=0.75,
            ),
            interfaces.construct_radius_graph,
        ),
        (
            "shared-neighbor",
            interfaces.SharedNeighborSpec(
                spec_id="pythia70-dev-shared-neighbor-k6-s2",
                purpose=purpose,
                neighbor_count=6,
                minimum_shared_neighbors=2,
            ),
            interfaces.construct_shared_neighbor_graph,
        ),
    )


def _adjacency_from_edges(edges: object) -> tuple[frozenset[int], ...]:
    result: list[set[int]] = [set() for _ in range(49)]
    for raw_left, raw_right in np.asarray(edges, dtype="<i8"):
        left, right = int(raw_left), int(raw_right)
        result[left].add(right)
        result[right].add(left)
    return tuple(frozenset(sorted(items)) for items in result)


def _construct_graph_layers(
    state: _RunState,
    response: FloatArray,
    pre_capture: FloatArray,
    interfaces: _NumericInterfaces,
    signals: _SignalLatch,
) -> dict[tuple[str, int], _GraphLayer]:
    result: dict[tuple[str, int], _GraphLayer] = {}
    fit_response = np.mean(
        response[list(_FIT_CONTEXT_INDICES)], axis=0, dtype=np.float64
    )
    fit_pre = np.mean(pre_capture[list(_FIT_CONTEXT_INDICES)], axis=0, dtype=np.float64)
    for layer_id in range(6):
        state.checkpoint(signals)
        global_frame = _fit_signed_frame(fit_response[:, layer_id], minimum_rows=49)
        states = fit_pre[:, layer_id] - np.mean(
            fit_pre[:, layer_id], axis=0, dtype=np.float64
        )
        norms = np.linalg.norm(states, axis=1)
        state_supported = bool(np.all(np.isfinite(norms)) and np.all(norms > 1e-12))
        normalized = (
            states / norms[:, None]
            if state_supported
            else np.zeros((49, 512), dtype="<f8")
        )
        for family, specification, constructor in _graph_specs(interfaces):
            state.checkpoint(signals)
            receipt = None
            adjacency: tuple[frozenset[int], ...] | None = None
            if state_supported:
                try:
                    graph_input = interfaces.GraphInput(
                        primary_unit_id=f"pythia70-layer-{layer_id}",
                        vertex_ids=_TOKEN_IDS,
                        states=normalized,
                    )
                    receipt = constructor(graph_input, specification)
                except BaseException as error:
                    raise _RunError(
                        "graph_construction", "canonical graph constructor failed"
                    ) from error
                adjacency = _adjacency_from_edges(receipt.canonical_edges)
                receipt_dict = receipt.to_dict()
                receipt_source = receipt.fingerprint_bytes
                if _sha256(receipt_source) != receipt.fingerprint_sha256:
                    raise _RunError(
                        "graph_construction", "canonical graph receipt digest differs"
                    )
                state.graph_receipts.append(
                    {
                        "layer_id": layer_id,
                        "graph_family": family,
                        "spec_id": specification.spec_id,
                        "status": "constructed",
                        "reason_codes": [],
                        "receipt": receipt_dict,
                        "receipt_canonical_sha256": receipt.fingerprint_sha256,
                    }
                )
            else:
                state.graph_receipts.append(
                    {
                        "layer_id": layer_id,
                        "graph_family": family,
                        "spec_id": specification.spec_id,
                        "status": "insufficient",
                        "reason_codes": ["state_zero_norm_or_nonfinite"],
                        "receipt": None,
                        "receipt_canonical_sha256": None,
                    }
                )

            local_frames = np.empty((49, 512, 2), dtype="<f8")
            local_minimum = np.zeros(49, dtype="<f8")
            local_supported = np.zeros(49, dtype="|b1")
            for token_id in range(49):
                vertices = (
                    [token_id, *sorted(adjacency[token_id])]
                    if adjacency is not None
                    else [token_id]
                )
                samples = (
                    response[
                        np.asarray(_FIT_CONTEXT_INDICES)[:, None],
                        np.asarray(vertices)[None, :],
                        layer_id,
                        :,
                    ]
                    .transpose(1, 0, 2)
                    .reshape(-1, 512)
                )
                frame = _fit_signed_frame(samples, minimum_rows=12)
                local_frames[token_id] = frame.basis
                local_minimum[token_id] = frame.minimum_metric
                local_supported[token_id] = (
                    adjacency is not None and len(vertices) >= 3 and frame.supported
                )

            rotations = np.empty((49, 2, 2), dtype="<f8")
            global_singular = np.zeros(49, dtype="<f8")
            global_supported = np.zeros(49, dtype="|b1")
            reflections = np.zeros(49, dtype="|b1")
            for token_id in range(49):
                try:
                    connection = interfaces.procrustes_connection(
                        source_frame=local_frames[token_id],
                        target_frame=global_frame.basis,
                        require_proper_rotation=False,
                    )
                except BaseException as error:
                    raise _RunError(
                        "f2_f4_derivation", "global Procrustes alignment failed"
                    ) from error
                rotations[token_id] = connection.rotation
                minimum = float(np.min(connection.singular_values))
                global_singular[token_id] = minimum
                global_supported[token_id] = (
                    global_frame.supported
                    and local_supported[token_id]
                    and minimum >= 1e-6
                )
                reflections[token_id] = np.linalg.det(connection.rotation) < 0.0
            result[(family, layer_id)] = _GraphLayer(
                family=family,
                layer_id=layer_id,
                adjacency=adjacency,
                local_frames=local_frames,
                local_minimum_metrics=local_minimum,
                local_supported=local_supported,
                global_frame=global_frame,
                global_rotations=rotations,
                global_minimum_singular_values=global_singular,
                global_supported=global_supported,
                global_reflections=reflections,
            )
    if len(state.graph_receipts) != 18:
        raise _RunError("graph_construction", "graph receipt count differs")
    return result


@dataclass(frozen=True, slots=True)
class _CandidateSplit:
    local_amplitude: FloatArray
    global_complex: NDArray[np.complex128]
    global_amplitude: FloatArray
    local_supported: BoolArray
    top10: tuple[int, ...] | None


@dataclass(frozen=True, slots=True)
class _CandidateDerivation:
    candidate: str
    graph: _GraphLayer
    splits: Mapping[str, _CandidateSplit]


def _observation_partition(
    interfaces: _NumericInterfaces, freeze: Mapping[str, object]
) -> object:
    fit = np.column_stack(
        (_TOKEN_IDS, np.tile(np.asarray(_FIT_CONTEXT_INDICES, dtype="<i8"), (49, 1)))
    )
    evaluation = np.column_stack(
        (
            _TOKEN_IDS,
            np.tile(np.asarray(_EVALUATION_CONTEXT_INDICES, dtype="<i8"), (49, 1)),
        )
    )
    plan = _mapping(
        _mapping(freeze["derivation_plan"], label="derivation plan")[
            "observation_partition"
        ],
        label="observation partition plan",
    )
    if (
        _sha256(fit.tobytes(order="C")) != plan["fit_identity_matrix_raw_sha256"]
        or _sha256(evaluation.tobytes(order="C"))
        != plan["evaluation_identity_matrix_raw_sha256"]
    ):
        raise _RunError("f2_f4_derivation", "observation identity digest differs")
    partition = interfaces.validate_observation_partition(
        fit, evaluation, row_identity_column=0
    )
    if partition.canonical_sha256 != plan["expected_partition_canonical_sha256"]:
        raise _RunError("f2_f4_derivation", "observation partition digest differs")
    return partition


def _top10(amplitudes: FloatArray, eligible: BoolArray) -> tuple[int, ...] | None:
    candidates = [
        (float(amplitudes[token_id]), token_id)
        for token_id in range(49)
        if bool(eligible[token_id]) and math.isfinite(float(amplitudes[token_id]))
    ]
    if len(candidates) < 10:
        return None
    selected = sorted(candidates)[:10]
    return tuple(sorted(token_id for _amplitude, token_id in selected))


def _detrace(covariance: FloatArray) -> FloatArray:
    result = np.array(covariance, dtype="<f8", order="C", copy=True)
    half_trace = np.trace(result, axis1=1, axis2=2) / 2.0
    result[:, 0, 0] -= half_trace
    result[:, 1, 1] -= half_trace
    return result


def _spin_two_complex(tensors: FloatArray) -> NDArray[np.complex128]:
    return np.asarray(
        (tensors[:, 0, 0] - tensors[:, 1, 1]) / 2.0 + 1j * tensors[:, 0, 1],
        dtype=np.complex128,
    )


def _derive_candidates(
    freeze: Mapping[str, object],
    response: FloatArray,
    graph_layers: Mapping[tuple[str, int], _GraphLayer],
    interfaces: _NumericInterfaces,
    signals: _SignalLatch,
    state: _RunState,
) -> dict[tuple[str, str, int], _CandidateDerivation]:
    partition = _observation_partition(interfaces, freeze)
    result: dict[tuple[str, str, int], _CandidateDerivation] = {}
    split_indices = {
        "fit": _FIT_CONTEXT_INDICES,
        "evaluation": _EVALUATION_CONTEXT_INDICES,
    }
    for family in _FAMILIES:
        for layer_id in range(6):
            graph = graph_layers[(family, layer_id)]
            per_candidate: dict[str, dict[str, _CandidateSplit]] = {
                "F2": {},
                "F4": {},
            }
            for split, indices in split_indices.items():
                state.checkpoint(signals)
                split_rows = response[list(indices), :, layer_id, :]
                split_mean = np.mean(split_rows, axis=0, dtype=np.float64)
                manual_z = np.einsum(
                    "ndi,nd->ni", graph.local_frames, split_mean, optimize=False
                )
                if split == "evaluation":
                    try:
                        observation = interfaces.derive_f2_section(
                            graph.local_frames,
                            split_mean,
                            partition=partition,
                            input_row_identities=_TOKEN_IDS,
                            amplitude_floor=1e-8,
                        )
                    except BaseException as error:
                        raise _RunError(
                            "f2_f4_derivation", "canonical F2 derivation failed"
                        ) from error
                    z = np.asarray(observation.values, dtype="<f8")
                    if not np.allclose(z, manual_z, rtol=1e-12, atol=1e-12):
                        raise _RunError(
                            "f2_f4_derivation", "canonical F2 values differ"
                        )
                else:
                    z = manual_z
                local_amplitude = np.linalg.norm(z, axis=1)
                projected = np.einsum(
                    "ndi,ni->nd", graph.local_frames, z, optimize=False
                )
                w = projected @ graph.global_frame.basis
                global_complex = np.asarray(w[:, 0] + 1j * w[:, 1])
                global_amplitude = np.abs(global_complex)
                local_supported = graph.local_supported & (local_amplitude > 1e-8)
                eligible = graph.global_supported & np.isfinite(global_amplitude)
                per_candidate["F2"][split] = _CandidateSplit(
                    local_amplitude=np.asarray(local_amplitude, dtype="<f8"),
                    global_complex=np.asarray(global_complex, dtype=np.complex128),
                    global_amplitude=np.asarray(global_amplitude, dtype="<f8"),
                    local_supported=np.asarray(local_supported, dtype="|b1"),
                    top10=_top10(global_amplitude, eligible),
                )

                projected_contexts = np.einsum(
                    "ctd,tdi->tci", split_rows, graph.local_frames, optimize=False
                )
                centered = projected_contexts - np.mean(
                    projected_contexts, axis=1, keepdims=True, dtype=np.float64
                )
                covariance = (
                    np.einsum("tci,tcj->tij", centered, centered, optimize=False) / 3.0
                )
                if split == "evaluation":
                    try:
                        spin = interfaces.derive_f4_spin_two(
                            covariance,
                            partition=partition,
                            input_row_identities=_TOKEN_IDS,
                            amplitude_floor=1e-8,
                        )
                    except BaseException as error:
                        raise _RunError(
                            "f2_f4_derivation", "canonical F4 derivation failed"
                        ) from error
                    local_tensor = np.asarray(spin.traceless_tensor, dtype="<f8")
                else:
                    local_tensor = _detrace(covariance)
                local_complex = _spin_two_complex(local_tensor)
                transported = np.einsum(
                    "tji,tjk,tkl->til",
                    graph.global_rotations,
                    local_tensor,
                    graph.global_rotations,
                    optimize=False,
                )
                global_f4 = _spin_two_complex(transported)
                local_amp_f4 = np.abs(local_complex)
                global_amp_f4 = np.abs(global_f4)
                local_supported_f4 = graph.local_supported & (local_amp_f4 > 1e-8)
                eligible_f4 = graph.global_supported & np.isfinite(global_amp_f4)
                per_candidate["F4"][split] = _CandidateSplit(
                    local_amplitude=np.asarray(local_amp_f4, dtype="<f8"),
                    global_complex=np.asarray(global_f4, dtype=np.complex128),
                    global_amplitude=np.asarray(global_amp_f4, dtype="<f8"),
                    local_supported=np.asarray(local_supported_f4, dtype="|b1"),
                    top10=_top10(global_amp_f4, eligible_f4),
                )
            for candidate in _CANDIDATES:
                result[(candidate, family, layer_id)] = _CandidateDerivation(
                    candidate=candidate,
                    graph=graph,
                    splits=per_candidate[candidate],
                )
    return result


@dataclass(frozen=True, slots=True)
class _RingTransport:
    ring: tuple[int, ...]
    reverse_ring: tuple[int, ...]
    missing_edge_count: int
    supported_edge_count: int
    minimum_singular_value: float
    forward: FloatArray | None
    reverse: FloatArray | None


def _ring_transport(
    graph: _GraphLayer,
    ring: Sequence[int],
    interfaces: _NumericInterfaces,
) -> _RingTransport:
    ordered = tuple(int(item) for item in ring)
    reversed_order = (ordered[0], *reversed(ordered[1:]))
    if graph.adjacency is None:
        return _RingTransport(
            ring=ordered,
            reverse_ring=reversed_order,
            missing_edge_count=len(ordered),
            supported_edge_count=0,
            minimum_singular_value=0.0,
            forward=None,
            reverse=None,
        )
    forward_pairs = tuple(zip(ordered, ordered[1:] + ordered[:1], strict=True))
    missing = sum(right not in graph.adjacency[left] for left, right in forward_pairs)
    if missing:
        return _RingTransport(
            ring=ordered,
            reverse_ring=reversed_order,
            missing_edge_count=missing,
            supported_edge_count=0,
            minimum_singular_value=0.0,
            forward=None,
            reverse=None,
        )

    def compute(path: tuple[int, ...]) -> tuple[FloatArray, list[float], list[bool]]:
        matrices: list[FloatArray] = []
        minima: list[float] = []
        support: list[bool] = []
        for left, right in zip(path, path[1:] + path[:1], strict=True):
            try:
                connection = interfaces.procrustes_connection(
                    source_frame=graph.local_frames[right],
                    target_frame=graph.local_frames[left],
                    require_proper_rotation=False,
                )
            except BaseException as error:
                raise _RunError(
                    "f2_f4_derivation", "edge Procrustes alignment failed"
                ) from error
            minimum = float(np.min(connection.singular_values))
            matrices.append(np.asarray(connection.rotation, dtype="<f8"))
            minima.append(minimum)
            support.append(
                bool(
                    graph.local_supported[left]
                    and graph.local_supported[right]
                    and minimum >= 1e-6
                )
            )
        return np.stack(matrices), minima, support

    forward, forward_minima, forward_support = compute(ordered)
    reverse, reverse_minima, reverse_support = compute(reversed_order)
    if not np.all(np.isfinite(forward)) or not np.all(np.isfinite(reverse)):
        raise _RunError("f2_f4_derivation", "edge transport is non-finite")
    all_minima = forward_minima + reverse_minima
    supported_edges = min(sum(forward_support), sum(reverse_support))
    return _RingTransport(
        ring=ordered,
        reverse_ring=reversed_order,
        missing_edge_count=0,
        supported_edge_count=supported_edges,
        minimum_singular_value=float(min(all_minima)),
        forward=forward,
        reverse=reverse,
    )


@dataclass(frozen=True, slots=True)
class _HolonomyDiagnostics:
    supported: bool
    reason_codes: tuple[str, ...]
    forward_determinant: float | None
    reverse_determinant: float | None
    forward_angle: float | None
    reverse_angle: float | None
    angle_error: float | None
    matrix_error: float | None


def _holonomy_diagnostics(
    transport: _RingTransport, interfaces: _NumericInterfaces
) -> _HolonomyDiagnostics:
    if (
        transport.forward is None
        or transport.reverse is None
        or transport.supported_edge_count != len(transport.ring)
    ):
        return _HolonomyDiagnostics(
            False,
            ("ring_edge_support_below_floor",),
            None,
            None,
            None,
            None,
            None,
            None,
        )
    try:
        forward = interfaces.compose_edge_transports(
            transport.forward, loop_name="frozen-address-ring-forward"
        ).matrix
        reverse = interfaces.compose_edge_transports(
            transport.reverse, loop_name="frozen-address-ring-reverse"
        ).matrix
    except BaseException as error:
        raise _RunError("f2_f4_derivation", "holonomy composition failed") from error
    forward_det = float(np.linalg.det(forward))
    reverse_det = float(np.linalg.det(reverse))
    if forward_det <= 0.0 or reverse_det <= 0.0:
        return _HolonomyDiagnostics(
            False,
            ("composed_cycle_orientation_not_positive",),
            None,
            None,
            None,
            None,
            None,
            None,
        )
    try:
        forward_angle = float(interfaces.principal_rotation_angle_2d(forward))
        reverse_angle = float(interfaces.principal_rotation_angle_2d(reverse))
        matrix_error = float(
            np.linalg.norm(reverse - np.linalg.inv(forward), ord="fro")
        )
    except BaseException as error:
        raise _RunError("f2_f4_derivation", "holonomy diagnostics failed") from error
    angle_error = abs(
        math.atan2(
            math.sin(reverse_angle + forward_angle),
            math.cos(reverse_angle + forward_angle),
        )
    )
    values = (
        forward_det,
        reverse_det,
        forward_angle,
        reverse_angle,
        angle_error,
        matrix_error,
    )
    if not all(math.isfinite(value) for value in values):
        raise _RunError("f2_f4_derivation", "holonomy diagnostic is non-finite")
    return _HolonomyDiagnostics(
        True,
        (),
        forward_det,
        reverse_det,
        forward_angle,
        reverse_angle,
        angle_error,
        matrix_error,
    )


@dataclass(frozen=True, slots=True)
class _PhaseDiagnostics:
    total_cycles: float
    maximum_increment: float
    branch_margin: float
    residual_cycles: float


def _phase_diagnostics(
    values: NDArray[np.complex128], ring: Sequence[int]
) -> _PhaseDiagnostics:
    ring_values = np.asarray(values[np.asarray(ring, dtype="<i8")], dtype=np.complex128)
    edge_products = np.conjugate(ring_values) * np.roll(ring_values, -1)
    increments = np.arctan2(edge_products.imag, edge_products.real)
    total_cycles = float(np.sum(increments, dtype=np.float64) / (2.0 * np.pi))
    maximum = float(np.max(np.abs(increments)))
    margin = float(np.pi - maximum)
    residual = float(abs(total_cycles - np.rint(total_cycles)))
    if not all(
        math.isfinite(item) for item in (total_cycles, maximum, margin, residual)
    ):
        raise _RunError("f2_f4_derivation", "phase diagnostic is non-finite")
    return _PhaseDiagnostics(total_cycles, maximum, margin, residual)


@dataclass(frozen=True, slots=True)
class _ManifestCell:
    cell_id: str
    gate_id: str
    axes: tuple[str, ...]
    axis_values: Mapping[str, object]


def _required_cell_manifest(freeze: Mapping[str, object]) -> tuple[_ManifestCell, ...]:
    contract = _mapping(freeze["gate_state_contract"], label="gate-state contract")
    axis_domain = _mapping(contract["required_cell_axes"], label="cell axes")
    cells: list[_ManifestCell] = []
    for raw_manifest in _sequence(
        contract["required_cell_manifests"], label="required cell manifests"
    ):
        manifest = _mapping(raw_manifest, label="required cell manifest")
        gate_id = str(manifest["gate_id"])
        axes = tuple(
            str(item) for item in _sequence(manifest["axes"], label=f"{gate_id} axes")
        )
        block: list[_ManifestCell] = []
        domains = [
            list(_sequence(axis_domain[axis], label=f"{axis} domain")) for axis in axes
        ]
        for combination in itertools.product(*domains):
            axis_values = dict(zip(axes, combination, strict=True))
            suffix = "|".join(f"{axis}={axis_values[axis]}" for axis in axes)
            cell_id = gate_id if not suffix else f"{gate_id}|{suffix}"
            block.append(_ManifestCell(cell_id, gate_id, axes, axis_values))
        source = ("\n".join(cell.cell_id for cell in block) + "\n").encode()
        if (
            len(block) != int(manifest["expected_cell_count"])
            or _sha256(source) != manifest["cell_ids_sha256"]
        ):
            raise _RunError("gate_evaluation", f"{gate_id} cell manifest differs")
        cells.extend(block)
    if len(cells) != int(contract["total_required_cells"]) or len(cells) != 894:
        raise _RunError("gate_evaluation", "total cell manifest count differs")
    if len({cell.cell_id for cell in cells}) != len(cells):
        raise _RunError("gate_evaluation", "cell manifest IDs are not unique")
    return tuple(cells)


def _metric_fields(freeze: Mapping[str, object], gate_id: str) -> tuple[str, ...]:
    fields = _mapping(
        _mapping(freeze["terminal_result_contract"], label="terminal result contract")[
            "cell_metric_fields_by_gate"
        ],
        label="cell metric fields",
    )[gate_id]
    return tuple(str(item) for item in _sequence(fields, label=f"{gate_id} metrics"))


def _cell_record(
    freeze: Mapping[str, object],
    manifest: _ManifestCell,
    *,
    state: str,
    support_count: int,
    coverage_denominator: int,
    reasons: Iterable[str] = (),
    metrics: Mapping[str, object] | None = None,
) -> dict[str, object]:
    metric_names = _metric_fields(freeze, manifest.gate_id)
    if state not in {"not_run", "insufficient", "fail", "pass"}:
        raise _RunError("gate_evaluation", "unknown cell state")
    if support_count < 0 or support_count > coverage_denominator:
        raise _RunError("gate_evaluation", "cell support count is outside coverage")
    attempted = state != "not_run"
    evaluable = state in {"pass", "fail"}
    reason_codes = sorted({str(item) for item in reasons})
    if evaluable:
        if metrics is None or set(metrics) != set(metric_names):
            raise _RunError("gate_evaluation", "evaluable cell metrics differ")
        metric_record = {
            name: _canonical_numeric_zero(metrics[name]) for name in metric_names
        }
    else:
        if not reason_codes:
            raise _RunError("gate_evaluation", "non-evaluable cell requires a reason")
        metric_record = {name: None for name in metric_names}
    record = {
        "cell_id": manifest.cell_id,
        "gate_id": manifest.gate_id,
        "axis_values": dict(manifest.axis_values),
        "state": state,
        "attempted": attempted,
        "evaluable": evaluable,
        "support_count": support_count,
        "coverage_fraction": support_count / coverage_denominator,
        "reason_codes": reason_codes,
        "metrics": metric_record,
    }
    try:
        _canonical_json_bytes(record)
    except (TypeError, ValueError) as error:
        raise _RunError("gate_evaluation", "cell record is not finite JSON") from error
    return record


def _fold_cell_states(states: Sequence[str]) -> str:
    if "fail" in states:
        return "fail"
    if "insufficient" in states:
        return "insufficient"
    if states and all(state == "not_run" for state in states):
        return "not_run"
    if "not_run" in states:
        return "insufficient"
    if states and all(state == "pass" for state in states):
        return "pass"
    raise _RunError("gate_evaluation", "cell state fold is undefined")


def _append_gate_record(
    state: _RunState,
    freeze: Mapping[str, object],
    gate_id: str,
    records: Sequence[Mapping[str, object]],
) -> None:
    manifests = {
        str(_mapping(item, label="cell manifest")["gate_id"]): _mapping(
            item, label="cell manifest"
        )
        for item in _sequence(
            _mapping(freeze["gate_state_contract"], label="gate-state contract")[
                "required_cell_manifests"
            ],
            label="cell manifests",
        )
    }
    manifest = manifests[gate_id]
    expected_count = int(manifest["expected_cell_count"])
    if len(records) != expected_count:
        raise _RunError("gate_evaluation", f"{gate_id} cell block is incomplete")
    cell_ids = [str(record["cell_id"]) for record in records]
    ids_source = ("\n".join(cell_ids) + "\n").encode()
    if _sha256(ids_source) != manifest["cell_ids_sha256"]:
        raise _RunError("gate_evaluation", f"{gate_id} cell ID digest differs")
    states = [str(record["state"]) for record in records]
    evaluable_count = sum(
        bool(record["evaluable"]) and record["state"] in {"pass", "fail"}
        for record in records
    )
    folded_state = _fold_cell_states(states)
    state.gate_records.append(
        {
            "gate_id": gate_id,
            "state": folded_state,
            "attempted": any(bool(record["attempted"]) for record in records),
            "evaluable": folded_state in {"pass", "fail"},
            "support_count": evaluable_count,
            "coverage_fraction": evaluable_count / expected_count,
            "reason_codes": sorted(
                {
                    str(reason)
                    for record in records
                    for reason in _sequence(
                        record["reason_codes"], label="cell reason codes"
                    )
                }
            ),
            "cell_ids_sha256": manifest["cell_ids_sha256"],
            "cell_records_canonical_sha256": _sha256(
                _canonical_value_bytes(list(records))
            ),
        }
    )


def _jaccard(left: Sequence[int], right: Sequence[int]) -> float:
    one, two = set(left), set(right)
    return len(one & two) / len(one | two)


def _evaluate_cells(
    state: _RunState,
    cube: Float32Array,
    response: FloatArray,
    candidates: Mapping[tuple[str, str, int], _CandidateDerivation],
    interfaces: _NumericInterfaces,
    signals: _SignalLatch,
) -> None:
    freeze = state.freeze
    all_cells = _required_cell_manifest(freeze)
    blocks: dict[str, list[_ManifestCell]] = {gate_id: [] for gate_id in _GATE_IDS}
    for cell in all_cells:
        blocks[cell.gate_id].append(cell)
    ring_items = [
        _mapping(item, label="address ring")
        for item in _sequence(
            _mapping(freeze["address_grid_baseline"], label="address baseline")[
                "rings"
            ],
            label="address rings",
        )
    ]
    rings = {
        str(item["ring_id"]): tuple(
            int(token_id)
            for token_id in _sequence(item["ordered_token_ids"], label="ring tokens")
        )
        for item in ring_items
    }
    transport_cache: dict[tuple[str, int, str], _RingTransport] = {}
    holonomy_cache: dict[tuple[str, int, str], _HolonomyDiagnostics] = {}

    def candidate_for(cell: _ManifestCell) -> _CandidateDerivation:
        axes = cell.axis_values
        return candidates[
            (str(axes["candidate"]), str(axes["graph_family"]), int(axes["layer_id"]))
        ]

    def transport_for(family: str, layer_id: int, ring_id: str) -> _RingTransport:
        key = (family, layer_id, ring_id)
        if key not in transport_cache:
            graph = candidates[("F2", family, layer_id)].graph
            transport_cache[key] = _ring_transport(graph, rings[ring_id], interfaces)
        return transport_cache[key]

    def holonomy_for(family: str, layer_id: int, ring_id: str) -> _HolonomyDiagnostics:
        key = (family, layer_id, ring_id)
        if key not in holonomy_cache:
            holonomy_cache[key] = _holonomy_diagnostics(
                transport_for(family, layer_id, ring_id), interfaces
            )
        return holonomy_cache[key]

    capture_lookup = {
        (str(record["context_id"]), str(record["capture_stage"])): record
        for record in state.capture_manifest
    }
    context_order = list(
        _sequence(
            _mapping(
                _mapping(freeze["input_plan"], label="input plan")["contexts"],
                label="context plan",
            )["ordered_ids"],
            label="ordered contexts",
        )
    )
    split_indices = {
        "fit": _FIT_CONTEXT_INDICES,
        "evaluation": _EVALUATION_CONTEXT_INDICES,
    }
    capture_raw_join: dict[tuple[str, str], str] = {}
    for context_index, context_id in enumerate(context_order):
        for stage_index, capture_stage in enumerate(_STAGES):
            raw_digest = _sha256(
                np.asarray(
                    cube[context_index, stage_index], dtype="<f4", order="C"
                ).tobytes(order="C")
            )
            manifest_digest = capture_lookup[(str(context_id), capture_stage)][
                "raw_array_sha256"
            ]
            if raw_digest != manifest_digest:
                raise _RunError(
                    "capture", "analysis capture cube digest differs from manifest"
                )
            capture_raw_join[(str(context_id), capture_stage)] = raw_digest
    split_semantics = {
        candidate: _mapping(
            _mapping(freeze["derivation_plan"], label="derivation plan")[candidate],
            label=f"{candidate} derivation",
        )["split_semantics"]
        for candidate in _CANDIDATES
    }

    for gate_id in _GATE_IDS:
        block_records: list[dict[str, object]] = []
        for cell in blocks[gate_id]:
            state.checkpoint(signals)
            axes = cell.axis_values
            if gate_id == "capture_integrity":
                context_id = str(axes["context"])
                layer_id = int(axes["layer_id"])
                context_index = context_order.index(context_id)
                finite = bool(
                    np.all(np.isfinite(cube[context_index, :, :, layer_id, :]))
                )
                if not finite:
                    raise _RunError("capture", "capture integrity finite join failed")
                record = _cell_record(
                    freeze,
                    cell,
                    state="pass",
                    support_count=49,
                    coverage_denominator=49,
                    metrics={
                        "resid_pre_raw_sha256": capture_raw_join[
                            (context_id, "resid_pre")
                        ],
                        "resid_post_raw_sha256": capture_raw_join[
                            (context_id, "resid_post")
                        ],
                        "shape": [49, 6, 512],
                        "dtype": "<f4",
                        "all_finite": True,
                    },
                )
            elif gate_id == "measurable_drift":
                layer_id = int(axes["layer_id"])
                split = str(axes["split"])
                mean_response = np.mean(
                    response[list(split_indices[split]), :, layer_id, :],
                    axis=0,
                    dtype=np.float64,
                )
                norms = np.linalg.norm(mean_response, axis=1)
                support = int(np.count_nonzero(np.isfinite(norms)))
                median = float(np.median(norms))
                if not math.isfinite(median):
                    raise _RunError("gate_evaluation", "drift median is non-finite")
                record = _cell_record(
                    freeze,
                    cell,
                    state="pass" if median > 1e-8 else "insufficient",
                    support_count=support,
                    coverage_denominator=49,
                    reasons=() if median > 1e-8 else ("drift_at_or_below_floor",),
                    metrics={"median_token_l2_response": median},
                )
            elif gate_id in {"f2_section_support", "f4_tensor_support"}:
                candidate_name = "F2" if gate_id.startswith("f2") else "F4"
                layer_id = int(axes["layer_id"])
                family = str(axes["graph_family"])
                split = str(axes["split"])
                derived = candidates[(candidate_name, family, layer_id)]
                values = derived.splits[split]
                supported = np.asarray(values.local_supported, dtype="|b1")
                count = int(np.count_nonzero(supported))
                passed = count >= 35
                selected_metrics = derived.graph.local_minimum_metrics[supported]
                selected_amplitudes = values.local_amplitude[supported]
                metrics = (
                    {
                        "split_semantics": _mapping(
                            split_semantics[candidate_name], label="split semantics"
                        )[split],
                        "supported_token_count": count,
                        "minimum_frame_identifiability_metric": float(
                            np.min(selected_metrics)
                        ),
                        "minimum_amplitude": float(np.min(selected_amplitudes)),
                    }
                    if passed
                    else None
                )
                record = _cell_record(
                    freeze,
                    cell,
                    state="pass" if passed else "insufficient",
                    support_count=count,
                    coverage_denominator=49,
                    reasons=() if passed else ("supported_token_count_below_floor",),
                    metrics=metrics,
                )
            elif gate_id == "low_amplitude_set_repeatability":
                derived = candidate_for(cell)
                fit_set = derived.splits["fit"].top10
                evaluation_set = derived.splits["evaluation"].top10
                present = int(fit_set is not None) + int(evaluation_set is not None)
                if fit_set is None or evaluation_set is None:
                    record = _cell_record(
                        freeze,
                        cell,
                        state="insufficient",
                        support_count=present,
                        coverage_denominator=2,
                        reasons=("fewer_than_ten_eligible_vertices",),
                    )
                else:
                    jaccard = _jaccard(fit_set, evaluation_set)
                    if jaccard >= 0.3:
                        outcome, reasons = "pass", ()
                    elif jaccard <= 0.1:
                        outcome, reasons = (
                            "fail",
                            ("low_amplitude_jaccard_below_floor",),
                        )
                    else:
                        outcome, reasons = (
                            "insufficient",
                            ("low_amplitude_jaccard_middle",),
                        )
                    record = _cell_record(
                        freeze,
                        cell,
                        state=outcome,
                        support_count=2,
                        coverage_denominator=2,
                        reasons=reasons,
                        metrics={
                            "fit_token_ids": list(fit_set),
                            "evaluation_token_ids": list(evaluation_set),
                            "jaccard": jaccard,
                        },
                    )
            elif gate_id == "address_loop_support":
                derived = candidate_for(cell)
                split = derived.splits[str(axes["split"])]
                ring_id = str(axes["ring_id"])
                ring = rings[ring_id]
                transport = transport_for(
                    derived.graph.family, derived.graph.layer_id, ring_id
                )
                vertices = np.asarray(ring, dtype="<i8")
                vertex_mask = (
                    derived.graph.global_supported[vertices]
                    & np.isfinite(split.global_amplitude[vertices])
                    & (split.global_amplitude[vertices] > 1e-8)
                )
                vertex_count = int(np.count_nonzero(vertex_mask))
                support = vertex_count + transport.supported_edge_count
                full = support == 2 * len(ring)
                record = _cell_record(
                    freeze,
                    cell,
                    state="pass" if full else "insufficient",
                    support_count=support,
                    coverage_denominator=2 * len(ring),
                    reasons=()
                    if full
                    else ("ring_vertex_or_edge_support_below_floor",),
                    metrics={
                        "ring_vertex_count": len(ring),
                        "supported_vertex_count": vertex_count,
                        "minimum_amplitude": float(
                            np.min(split.global_amplitude[vertices])
                        ),
                        "minimum_edge_singular_value": transport.minimum_singular_value,
                        "missing_edge_count": transport.missing_edge_count,
                    }
                    if full
                    else None,
                )
            elif gate_id == "continuous_holonomy_consistency":
                family = str(axes["graph_family"])
                layer_id = int(axes["layer_id"])
                ring_id = str(axes["ring_id"])
                transport = transport_for(family, layer_id, ring_id)
                diagnostic = holonomy_for(family, layer_id, ring_id)
                if not diagnostic.supported:
                    record = _cell_record(
                        freeze,
                        cell,
                        state="insufficient",
                        support_count=transport.supported_edge_count,
                        coverage_denominator=len(transport.ring),
                        reasons=diagnostic.reason_codes,
                    )
                else:
                    assert all(
                        value is not None
                        for value in (
                            diagnostic.forward_determinant,
                            diagnostic.reverse_determinant,
                            diagnostic.forward_angle,
                            diagnostic.reverse_angle,
                            diagnostic.angle_error,
                            diagnostic.matrix_error,
                        )
                    )
                    passed = bool(
                        diagnostic.angle_error <= 1e-6
                        and diagnostic.matrix_error <= 1e-6
                    )
                    record = _cell_record(
                        freeze,
                        cell,
                        state="pass" if passed else "fail",
                        support_count=len(transport.ring),
                        coverage_denominator=len(transport.ring),
                        reasons=() if passed else ("holonomy_reverse_mismatch",),
                        metrics={
                            "ring_edge_count": len(transport.ring),
                            "supported_edge_count": transport.supported_edge_count,
                            "forward_determinant": diagnostic.forward_determinant,
                            "reverse_determinant": diagnostic.reverse_determinant,
                            "forward_angle_rad": diagnostic.forward_angle,
                            "reverse_angle_rad": diagnostic.reverse_angle,
                            "reverse_angle_error_rad": diagnostic.angle_error,
                            "reverse_matrix_frobenius_error": diagnostic.matrix_error,
                        },
                    )
            elif gate_id == "address_ring_phase_resolution":
                derived = candidate_for(cell)
                split = derived.splits[str(axes["split"])]
                ring_id = str(axes["ring_id"])
                ring = rings[ring_id]
                vertices = np.asarray(ring, dtype="<i8")
                transport = transport_for(
                    derived.graph.family, derived.graph.layer_id, ring_id
                )
                vertex_mask = (
                    derived.graph.global_supported[vertices]
                    & np.isfinite(split.global_amplitude[vertices])
                    & (split.global_amplitude[vertices] > 1e-8)
                )
                reasons: list[str] = []
                if derived.candidate == "F4" and np.any(
                    derived.graph.global_reflections[vertices]
                ):
                    reasons.append("f4_orientation_unresolved")
                vertex_count = int(np.count_nonzero(vertex_mask))
                support = vertex_count + transport.supported_edge_count
                if support != 2 * len(ring):
                    reasons.append("phase_vertex_or_edge_support_below_floor")
                if reasons:
                    record = _cell_record(
                        freeze,
                        cell,
                        state="insufficient",
                        support_count=support,
                        coverage_denominator=2 * len(ring),
                        reasons=reasons,
                    )
                else:
                    phase = _phase_diagnostics(split.global_complex, ring)
                    if phase.branch_margin <= 1e-6:
                        record = _cell_record(
                            freeze,
                            cell,
                            state="insufficient",
                            support_count=support,
                            coverage_denominator=2 * len(ring),
                            reasons=("phase_branch_margin_at_or_below_floor",),
                        )
                    else:
                        passed = phase.residual_cycles <= 1e-6
                        record = _cell_record(
                            freeze,
                            cell,
                            state="pass" if passed else "fail",
                            support_count=support,
                            coverage_denominator=2 * len(ring),
                            reasons=()
                            if passed
                            else ("phase_residual_above_tolerance",),
                            metrics={
                                "ring_vertex_count": len(ring),
                                "supported_vertex_count": vertex_count,
                                "unrounded_phase_total_cycles": phase.total_cycles,
                                "maximum_absolute_edge_increment_rad": phase.maximum_increment,
                                "branch_margin_rad": phase.branch_margin,
                                "nearest_integer_residual_cycles": phase.residual_cycles,
                            },
                        )
            elif gate_id == "graph_family_agreement":
                candidate_name = str(axes["candidate"])
                layer_id = int(axes["layer_id"])
                split_name = str(axes["split"])
                sets = [
                    candidates[(candidate_name, family, layer_id)]
                    .splits[split_name]
                    .top10
                    for family in _FAMILIES
                ]
                present = sum(item is not None for item in sets)
                if present != 3:
                    record = _cell_record(
                        freeze,
                        cell,
                        state="insufficient",
                        support_count=present * (present - 1) // 2,
                        coverage_denominator=3,
                        reasons=("graph_family_top10_missing",),
                    )
                else:
                    assert all(item is not None for item in sets)
                    concrete = [tuple(item) for item in sets if item is not None]
                    pairwise = [
                        _jaccard(concrete[0], concrete[1]),
                        _jaccard(concrete[0], concrete[2]),
                        _jaccard(concrete[1], concrete[2]),
                    ]
                    minimum = min(pairwise)
                    if minimum >= 0.5:
                        outcome, reasons = "pass", ()
                    elif minimum <= 0.2:
                        outcome, reasons = "fail", ("graph_family_jaccard_below_floor",)
                    else:
                        outcome, reasons = (
                            "insufficient",
                            ("graph_family_jaccard_middle",),
                        )
                    record = _cell_record(
                        freeze,
                        cell,
                        state=outcome,
                        support_count=3,
                        coverage_denominator=3,
                        reasons=reasons,
                        metrics={
                            "pairwise_jaccards": pairwise,
                            "minimum_pairwise_jaccard": minimum,
                        },
                    )
            elif gate_id == "negative_controls":
                derived = candidate_for(cell)
                split = derived.splits[str(axes["split"])]
                ring_id = str(axes["ring_id"])
                ring = rings[ring_id]
                vertices = np.asarray(ring, dtype="<i8")
                transport = transport_for(
                    derived.graph.family, derived.graph.layer_id, ring_id
                )
                holonomy = holonomy_for(
                    derived.graph.family, derived.graph.layer_id, ring_id
                )
                vertex_supported = bool(
                    np.all(derived.graph.global_supported[vertices])
                    and np.all(split.global_amplitude[vertices] > 1e-8)
                    and np.all(np.isfinite(split.global_amplitude[vertices]))
                )
                orientation_supported = not (
                    derived.candidate == "F4"
                    and np.any(derived.graph.global_reflections[vertices])
                )
                phase_prerequisites = (
                    vertex_supported
                    and orientation_supported
                    and holonomy.supported
                    and transport.supported_edge_count == len(ring)
                )
                if phase_prerequisites:
                    forward_phase = _phase_diagnostics(split.global_complex, ring)
                    reverse_phase = _phase_diagnostics(
                        split.global_complex, transport.reverse_ring
                    )
                    phase_prerequisites = (
                        forward_phase.branch_margin > 1e-6
                        and reverse_phase.branch_margin > 1e-6
                    )
                comparison_support = (2 if holonomy.supported else 0) + int(
                    phase_prerequisites
                )
                if comparison_support != 3:
                    record = _cell_record(
                        freeze,
                        cell,
                        state="insufficient",
                        support_count=comparison_support,
                        coverage_denominator=3,
                        reasons=("negative_control_prerequisite_missing",),
                    )
                else:
                    assert holonomy.forward_angle is not None
                    assert holonomy.reverse_angle is not None
                    assert holonomy.angle_error is not None
                    assert holonomy.matrix_error is not None
                    phase_error = abs(
                        reverse_phase.total_cycles + forward_phase.total_cycles
                    )
                    passed = bool(
                        holonomy.angle_error <= 1e-6
                        and holonomy.matrix_error <= 1e-6
                        and phase_error <= 1e-6
                    )
                    record = _cell_record(
                        freeze,
                        cell,
                        state="pass" if passed else "fail",
                        support_count=3,
                        coverage_denominator=3,
                        reasons=() if passed else ("negative_control_mismatch",),
                        metrics={
                            "forward_angle_rad": holonomy.forward_angle,
                            "reverse_angle_rad": holonomy.reverse_angle,
                            "reverse_angle_error_rad": holonomy.angle_error,
                            "reverse_matrix_frobenius_error": holonomy.matrix_error,
                            "forward_unrounded_phase_total_cycles": forward_phase.total_cycles,
                            "reverse_unrounded_phase_total_cycles": reverse_phase.total_cycles,
                            "reverse_phase_total_error_cycles": phase_error,
                        },
                    )
            else:  # pragma: no cover - frozen gate enumeration above
                raise AssertionError(gate_id)
            state.cell_records.append(record)
            block_records.append(record)
        _append_gate_record(state, freeze, gate_id, block_records)
    if len(state.cell_records) != 894 or len(state.gate_records) != 10:
        raise _RunError("gate_evaluation", "complete gate-state record count differs")


def _terminal_fold(gate_records: Sequence[Mapping[str, object]]) -> str:
    states = [str(record["state"]) for record in gate_records]
    if "fail" in states:
        return "fail"
    if any(state in {"insufficient", "not_run"} for state in states):
        return "insufficient"
    if len(states) == 10 and all(state == "pass" for state in states):
        return "pass"
    raise _RunError("terminal_serialization", "terminal gate fold is undefined")


def _resource_use(state: _RunState) -> dict[str, object]:
    return {
        "wall_clock_seconds": state.wall_clock_seconds(),
        "model_loads": state.model_loads,
        "forward_batches": state.forward_batches,
        "raw_capture_bytes": state.raw_capture_bytes,
        "terminal_result_size_verified_below_hard": True,
        "peak_bytes_estimated_not_measured": int(state.budget["estimated_peak_bytes"]),
        "hard_limit_breaches": state.hard_limit_breaches(),
    }


def _terminal_provenance(state: _RunState) -> dict[str, object]:
    launch = state.preflight.launch
    bindings = _mapping(
        _strict_json_bytes(state.attempt_source, label="attempt record")["bindings"],
        label="attempt bindings",
    )
    runner = _mapping(launch["runner"], label="launch.runner")
    command = _mapping(launch["command"], label="launch.command")
    runtime = _mapping(launch["runtime"], label="launch.runtime")
    model = _mapping(launch["model"], label="launch.model")
    return {
        "runtime_source_commit": bindings["runtime_source_commit"],
        "runner_path": runner["path"],
        "runner_source_sha256": bindings["runner_source_sha256"],
        "launch_authorization_sha256": bindings["launch_authorization_sha256"],
        "attempt_record_sha256": state.attempt_sha256,
        "freeze_source_sha256": bindings["freeze_source_sha256"],
        "context_bank_source_sha256": bindings["context_bank_source_sha256"],
        "context_bank_canonical_sha256": bindings["context_bank_canonical_sha256"],
        "route_source_sha256": bindings["route_source_sha256"],
        "model_id": model["id"],
        "model_revision": model["revision"],
        "expected_model_file_sha256_and_sizes": bindings[
            "expected_model_file_sha256_and_sizes"
        ],
        "observed_model_file_slots": list(state.observed_model_file_slots),
        "python_executable": runtime["python_executable"],
        "python_version": runtime["python_version"],
        "dependency_versions": runtime["dependency_versions"],
        "exact_argv": command["exact_argv"],
        "working_directory": command["working_directory"],
    }


def _validate_terminal_prefixes(state: _RunState, *, complete: bool) -> None:
    freeze = state.freeze
    expected_cells = _required_cell_manifest(freeze)
    if [record["cell_id"] for record in state.cell_records] != [
        cell.cell_id for cell in expected_cells[: len(state.cell_records)]
    ]:
        raise _RunError("terminal_serialization", "cell record prefix differs")
    graph_order = [(layer, family) for layer in range(6) for family in _FAMILIES]
    if [
        (int(record["layer_id"]), str(record["graph_family"]))
        for record in state.graph_receipts
    ] != graph_order[: len(state.graph_receipts)]:
        raise _RunError("terminal_serialization", "graph receipt prefix differs")
    context_order = list(
        _sequence(
            _mapping(
                _mapping(freeze["input_plan"], label="input plan")["contexts"],
                label="context plan",
            )["ordered_ids"],
            label="ordered contexts",
        )
    )
    capture_order = [
        (context, capture_stage)
        for context in context_order
        for capture_stage in _STAGES
    ]
    if [
        (record["context_id"], record["capture_stage"])
        for record in state.capture_manifest
    ] != capture_order[: len(state.capture_manifest)]:
        raise _RunError("terminal_serialization", "capture manifest prefix differs")
    if [record["gate_id"] for record in state.gate_records] != list(
        _GATE_IDS[: len(state.gate_records)]
    ):
        raise _RunError("terminal_serialization", "gate record prefix differs")
    if state.graph_receipts and len(state.capture_manifest) != 16:
        raise _RunError("terminal_serialization", "graph prefix precedes full capture")
    if state.cell_records and len(state.graph_receipts) != 18:
        raise _RunError("terminal_serialization", "cell prefix precedes full graphs")
    completed_blocks = 0
    cursor = 0
    manifests = _sequence(
        _mapping(freeze["gate_state_contract"], label="gate-state contract")[
            "required_cell_manifests"
        ],
        label="cell manifests",
    )
    for raw in manifests:
        count = int(_mapping(raw, label="cell manifest")["expected_cell_count"])
        if len(state.cell_records) >= cursor + count:
            completed_blocks += 1
        cursor += count
    if len(state.gate_records) != completed_blocks:
        raise _RunError(
            "terminal_serialization", "gate records differ from cell blocks"
        )
    if complete and (
        len(state.capture_manifest) != 16
        or len(state.graph_receipts) != 18
        or len(state.cell_records) != 894
        or len(state.gate_records) != 10
    ):
        raise _RunError("terminal_serialization", "complete record counts differ")


def _build_terminal_result(
    state: _RunState,
    *,
    error: BaseException | None,
    caught_at_utc: str | None,
) -> tuple[dict[str, object], bytes]:
    complete = error is None
    _validate_terminal_prefixes(state, complete=complete)
    if not state.observed_model_file_slots:
        state.observed_model_file_slots = [
            _not_run_model_slot("config.json"),
            _not_run_model_slot("model.safetensors"),
        ]
    terminal_error: dict[str, object] | None = None
    if error is not None:
        stage = error.stage if isinstance(error, _RunError) else state.active_stage
        if stage not in _ERROR_STAGES:
            stage = state.active_stage
        terminal_error = {
            "stage": stage,
            "exception_type": type(error).__name__,
            "message": str(error) or type(error).__name__,
            "caught_at_utc": caught_at_utc,
        }
    resource = _resource_use(state)
    if complete:
        if any(
            record["status"] != "verified" for record in state.observed_model_file_slots
        ):
            raise _RunError(
                "terminal_serialization", "complete model file slots are not verified"
            )
        if resource["hard_limit_breaches"]:
            raise _RunError(
                "resource_budget", "complete result exceeds a hard resource limit"
            )
    elif terminal_error is None or caught_at_utc is None:
        raise _RunError("terminal_serialization", "infrastructure error is incomplete")
    contract = _mapping(
        state.freeze["terminal_result_contract"], label="terminal result contract"
    )
    finished_at = _utc_now()
    if finished_at < state.started_at_utc or (
        caught_at_utc is not None
        and not (state.started_at_utc <= caught_at_utc <= finished_at)
    ):
        raise _RunError("terminal_serialization", "terminal chronology differs")
    document: dict[str, object] = {
        "schema_version": contract["schema_version"],
        "freeze_id": state.freeze["freeze_id"],
        "launch_id": state.preflight.launch["launch_id"],
        "attempt_id": state.preflight.launch["attempt_id"],
        "execution_terminal": "complete" if complete else "infrastructure_error",
        "started_at_utc": state.started_at_utc,
        "finished_at_utc": finished_at,
        "provenance": _terminal_provenance(state),
        "capture_manifest": list(state.capture_manifest),
        "graph_receipts": list(state.graph_receipts),
        "gate_records": list(state.gate_records),
        "cell_records": list(state.cell_records),
        "terminal_fold": _terminal_fold(state.gate_records) if complete else None,
        "resource_use": resource,
        "claim_boundary": state.freeze["claim_boundary"],
        "error": terminal_error,
    }
    _exact_keys(
        document,
        [
            str(item)
            for item in _sequence(contract["root_fields"], label="terminal root fields")
        ],
        label="terminal result",
    )
    _exact_keys(
        _mapping(document["provenance"], label="terminal provenance"),
        [
            str(item)
            for item in _sequence(
                contract["provenance_fields"], label="terminal provenance fields"
            )
        ],
        label="terminal provenance",
    )
    _exact_keys(
        _mapping(document["resource_use"], label="terminal resource use"),
        [
            str(item)
            for item in _sequence(
                contract["resource_use_fields"], label="resource use fields"
            )
        ],
        label="terminal resource use",
    )
    source = _canonical_json_bytes(document)
    hard = int(state.budget["terminal_result_bytes_hard"])
    if len(source) >= hard:
        raise _RunError(
            "terminal_serialization", "terminal result is not below its hard byte limit"
        )
    try:
        reloaded = _strict_json_bytes(source, label="terminal result")
    except _PreflightError as reload_error:
        raise _RunError(
            "terminal_serialization", "terminal strict reload failed"
        ) from reload_error
    if _canonical_json_bytes(reloaded) != source:
        raise _RunError("terminal_serialization", "terminal canonical rerender differs")
    return document, source


def _persist_and_promote_terminal(
    state: _RunState,
    source: bytes,
) -> None:
    descriptor = _write_exclusive_at(
        state.stage.stage_fd,
        "terminal-result.json",
        source,
        maximum=int(state.budget["terminal_result_bytes_hard"]),
        stage="terminal_persistence",
    )
    state.stage.file_fds.append(descriptor)
    _promote_stage(state.stage)


def _strict_reload_external_terminal(state: _RunState, expected: bytes) -> bytes:
    if not state.stage.published:
        raise _RunError("terminal_persistence", "external store is not published")
    store_fd = os.open(
        state.stage.store_name, _DIRECTORY_FLAGS, dir_fd=state.stage.parent_fd
    )
    terminal_fd = -1
    try:
        if _stat_identity(os.fstat(store_fd)) != _stat_identity(
            os.fstat(state.stage.stage_fd)
        ):
            raise _RunError("terminal_persistence", "external store inode differs")
        terminal_fd = os.open("terminal-result.json", _FILE_READ_FLAGS, dir_fd=store_fd)
        source = _read_descriptor(
            terminal_fd, int(state.budget["terminal_result_bytes_hard"])
        )
        if source != expected:
            raise _RunError("terminal_persistence", "external terminal bytes differ")
        try:
            reloaded = _strict_json_bytes(source, label="external terminal result")
        except _PreflightError as error:
            raise _RunError(
                "terminal_persistence", "external terminal strict reload failed"
            ) from error
        if _canonical_json_bytes(reloaded) != source:
            raise _RunError(
                "terminal_persistence", "external terminal canonical rerender differs"
            )
        return source
    finally:
        if terminal_fd >= 0:
            os.close(terminal_fd)
        os.close(store_fd)


def _write_repository_projection(path: Path, source: bytes) -> None:
    parent_fd = _open_absolute_directory(path.parent)
    descriptor = -1
    final_descriptor = -1
    temporary = f".{path.name}.pythia70-gate-state-v0-1.staging"
    try:
        _require_live_directory_anchor(
            path.parent, parent_fd, stage="terminal_persistence"
        )
        if (
            _entry_metadata(parent_fd, temporary) is not None
            or _entry_metadata(parent_fd, path.name) is not None
        ):
            raise _RunError(
                "terminal_persistence", "repository projection namespace is occupied"
            )
        descriptor = _write_exclusive_at(
            parent_fd,
            temporary,
            source,
            maximum=_JSON_MAX_BYTES,
            stage="terminal_persistence",
        )
        held = os.fstat(descriptor)
        libc = ctypes.CDLL(None, use_errno=True)
        if sys.platform == "darwin":
            function = getattr(libc, "renameatx_np", None)
            flag = 0x00000004
        elif sys.platform.startswith("linux"):
            function = getattr(libc, "renameat2", None)
            flag = 0x00000001
        else:  # pragma: no cover - preflight already rejects this platform.
            function = None
            flag = 0
        if function is None:
            raise _RunError(
                "terminal_persistence", "repository no-replace rename unavailable"
            )
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
            os.fsencode(temporary),
            parent_fd,
            os.fsencode(path.name),
            flag,
        )
        observed_errno = ctypes.get_errno() or errno.EIO
        live_temporary = _entry_metadata(parent_fd, temporary)
        live_final = _entry_metadata(parent_fd, path.name)
        published = (
            live_temporary is None
            and live_final is not None
            and _stat_identity(live_final) == _stat_identity(held)
        )
        staged = (
            live_temporary is not None
            and _stat_identity(live_temporary) == _stat_identity(held)
            and live_final is None
        )
        if not published:
            if staged and result != 0:
                raise _RunError(
                    "terminal_persistence",
                    f"repository projection rename failed with errno {observed_errno}",
                )
            raise _RunError(
                "terminal_persistence", "repository projection namespace is invalid"
            )
        os.fsync(parent_fd)
        _require_live_directory_anchor(
            path.parent, parent_fd, stage="terminal_persistence"
        )
        final_descriptor = os.open(path.name, _FILE_READ_FLAGS, dir_fd=parent_fd)
        if (
            _stat_identity(os.fstat(final_descriptor)) != _stat_identity(held)
            or _read_descriptor(final_descriptor, _JSON_MAX_BYTES) != source
        ):
            raise _RunError(
                "terminal_persistence", "repository projection final reread differs"
            )
    finally:
        if final_descriptor >= 0:
            os.close(final_descriptor)
        if descriptor >= 0:
            os.close(descriptor)
        os.close(parent_fd)


def _project_repository_records(state: _RunState, terminal_source: bytes) -> None:
    paths = _artifact_paths(state.freeze)
    _write_repository_projection(paths["attempt_record"], state.attempt_source)
    _write_repository_projection(paths["terminal_result"], terminal_source)
    for key in ("external_next_hypotheses_path", "next_hypotheses"):
        try:
            os.lstat(paths[key])
        except FileNotFoundError:
            continue
        raise _RunError(
            "terminal_persistence", "runner must not create next-hypotheses output"
        )


def _classify_runtime_error(state: _RunState, error: BaseException) -> BaseException:
    if isinstance(error, _RunError):
        return error
    if isinstance(error, _DeferredSignal):
        if state.hard_limit_breaches():
            return _RunError("resource_budget", str(error))
        return _RunError(state.active_stage, str(error))
    return _RunError(state.active_stage, f"{type(error).__name__}: {error}")


def _late_completion_error(state: _RunState, signals: _SignalLatch) -> _RunError | None:
    breaches = state.hard_limit_breaches()
    if breaches:
        return _RunError(
            "resource_budget",
            f"hard resource limits reached before publication: {breaches!r}",
        )
    try:
        signals.check()
    except _DeferredSignal as error:
        return _RunError("terminal_serialization", str(error))
    return None


def _run_started_attempt(
    preflight: _Preflight,
    stage: _OwnedStage,
    stage_metadata: os.stat_result,
    *,
    observed_at_utc: str,
    reserved_at_utc: str,
    reserved_monotonic: float,
    signals: _SignalLatch,
) -> int:
    attempt_source, attempt_sha256 = _write_attempt(
        preflight,
        stage,
        observed_at_utc=observed_at_utc,
        reserved_at_utc=reserved_at_utc,
        stage_metadata=stage_metadata,
    )
    state = _RunState(
        preflight=preflight,
        stage=stage,
        started_at_utc=reserved_at_utc,
        started_monotonic=reserved_monotonic,
        attempt_source=attempt_source,
        attempt_sha256=attempt_sha256,
        observed_model_file_slots=[
            _not_run_model_slot("config.json"),
            _not_run_model_slot("model.safetensors"),
        ],
    )
    caught: BaseException | None = None
    caught_at: str | None = None
    try:
        signals.arm_wall_limit(
            float(state.budget["wall_clock_seconds_hard"]) - state.wall_clock_seconds()
        )
        state.checkpoint(signals)
        with _active_stage(state, "model_file_hash"):
            snapshot = _resolve_and_verify_model_files(state)
        state.checkpoint(signals)
        with _active_stage(state, "model_load"):
            adapter = _load_exact_model(state, snapshot)
        loaded_bank = _load_context_bank_for_capture(state.freeze)
        with _active_stage(state, "capture"):
            cube32 = _capture_all(state, adapter, loaded_bank, signals)
        cube = np.asarray(cube32, dtype="<f8")
        response = cube[:, 1] - cube[:, 0]
        with _active_stage(state, "f2_f4_derivation"):
            interfaces = _load_bound_numeric_interfaces(state.freeze)
        with _active_stage(state, "graph_construction"):
            graphs = _construct_graph_layers(
                state, response, cube[:, 0], interfaces, signals
            )
        with _active_stage(state, "f2_f4_derivation"):
            candidates = _derive_candidates(
                state.freeze, response, graphs, interfaces, signals, state
            )
        with _active_stage(state, "gate_evaluation"):
            _evaluate_cells(state, cube32, response, candidates, interfaces, signals)
        state.checkpoint(signals)
    except Exception as error:  # noqa: BLE001 - one terminal maps every failure.
        caught = _classify_runtime_error(state, error)
        caught_at = _utc_now()

    state.active_stage = "terminal_serialization"
    late_error = _late_completion_error(state, signals) if caught is None else None
    if late_error is not None:
        caught = late_error
        caught_at = _utc_now()
    try:
        _document, terminal_source = _build_terminal_result(
            state, error=caught, caught_at_utc=caught_at
        )
    except BaseException as serialization_error:
        if caught is not None:
            raise
        caught = (
            serialization_error
            if isinstance(serialization_error, _RunError)
            else _RunError(
                "terminal_serialization",
                f"complete terminal construction failed: {serialization_error}",
            )
        )
        caught_at = _utc_now()
        _document, terminal_source = _build_terminal_result(
            state, error=caught, caught_at_utc=caught_at
        )
    if caught is None:
        late_error = _late_completion_error(state, signals)
        if late_error is not None:
            caught = late_error
            caught_at = _utc_now()
            _document, terminal_source = _build_terminal_result(
                state, error=caught, caught_at_utc=caught_at
            )
        else:
            _document, terminal_source = _build_terminal_result(
                state, error=None, caught_at_utc=None
            )
            late_error = _late_completion_error(state, signals)
            if late_error is not None:
                caught = late_error
                caught_at = _utc_now()
                _document, terminal_source = _build_terminal_result(
                    state, error=caught, caught_at_utc=caught_at
                )
    _persist_and_promote_terminal(state, terminal_source)
    external_source = _strict_reload_external_terminal(state, terminal_source)
    _project_repository_records(state, external_source)
    return 0 if caught is None else 1


def _validate_launch_only_receipt(preflight: _Preflight) -> dict[str, object]:
    return {
        "schema_version": "spirallens.pythia70-gate-state-launch-validation.v0.1",
        "status": "validated_not_started",
        "freeze_id": preflight.freeze["freeze_id"],
        "launch_id": preflight.launch["launch_id"],
        "runtime_source_commit": preflight.runtime_source_commit,
        "runner_source_sha256": _sha256(preflight.runner_source),
        "launch_authorization_sha256": preflight.launch_sha256,
        "no_replace_primitive": preflight.no_replace_primitive,
        "model_or_cache_accessed": False,
    }


def _run(*, validate_launch_only: bool) -> int:
    preflight = _preflight(validate_launch_only=validate_launch_only)
    if validate_launch_only:
        sys.stdout.buffer.write(
            _canonical_json_bytes(_validate_launch_only_receipt(preflight))
        )
        sys.stdout.buffer.flush()
        return 0
    with _SignalLatch() as signals:
        observed_at = _utc_now()
        _observe_required_absence(preflight.freeze)
        stage, stage_metadata = _reserve_stage(preflight.freeze)
        reserved_monotonic = time.monotonic()
        reserved_at = _utc_now()
        try:
            return _run_started_attempt(
                preflight,
                stage,
                stage_metadata,
                observed_at_utc=observed_at,
                reserved_at_utc=reserved_at,
                reserved_monotonic=reserved_monotonic,
                signals=signals,
            )
        finally:
            stage.close()


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--validate-launch-only",
        action="store_true",
        help="validate the value-free launch boundary without model/cache access",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parse_args(argv)
    try:
        return _run(validate_launch_only=bool(arguments.validate_launch_only))
    except _RunError as error:
        print(f"{error.stage}: {error}", file=sys.stderr)
        return 2
    except Exception as error:  # noqa: BLE001 - CLI must fail closed.
        print(f"unhandled: {type(error).__name__}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
