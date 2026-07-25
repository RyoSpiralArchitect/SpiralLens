"""Production-shaped, subject-independent Faiss range-call qualification."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import hashlib
import json
from numbers import Integral
import os
from pathlib import Path
import stat
import tempfile

import numpy as np

from .contracts import canonical_json_sha256
from .faiss_hnsw import (
    FAISS_HNSW_BACKEND_ID,
    FAISS_HNSW_RANGE_CALL_BACKEND_VERSION,
    FaissHNSWConfig,
    _run_worker,
)


QUALIFICATION_SCHEMA_VERSION = (
    "spirallens.faiss-hnsw-range-qualification.v0.2"
)
QUALIFICATION_FIXTURE_SCHEMA_VERSION = (
    "spirallens.faiss-hnsw-range-fixture.v0.1"
)
QUALIFICATION_ROW_COUNT = 50_304
QUALIFICATION_HIDDEN_SIZE = 512
QUALIFICATION_CLUSTER_SIZE = 32
QUALIFICATION_QUERY_COUNT = 512
QUALIFICATION_COLD_RUNS = 2
QUALIFICATION_FIXTURE_SEED = 1729
QUALIFICATION_MAX_NATIVE_CALL_HITS = QUALIFICATION_ROW_COUNT
QUALIFICATION_MAX_RAW_HITS = 20_000_000
QUALIFICATION_COSINE_MIN = 0.995
QUALIFICATION_SCORE_MARGIN = 0.0001
_CONSUMER_VALIDATED_TOKEN = object()
_CONSUMER_VALIDATION = {
    "fixture_regeneration": "fresh_python_subprocess",
    "worker_runtime_bound": True,
}


def _qualification_radius() -> float:
    return float(
        np.nextafter(
            np.float32(
                max(
                    -1.0,
                    QUALIFICATION_COSINE_MIN
                    - QUALIFICATION_SCORE_MARGIN,
                )
            ),
            np.float32(-np.inf),
        )
    )


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _reject_duplicate_json_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    payload: dict[str, object] = {}
    for key, value in pairs:
        if key in payload:
            raise ValueError(
                f"Faiss qualification JSON contains duplicate key {key!r}"
            )
        payload[key] = value
    return payload


def _parse_canonical_json(
    source: bytes,
    *,
    label: str,
) -> dict[str, object]:
    try:
        payload = json.loads(
            source,
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is invalid JSON") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain one JSON object")
    if _canonical_bytes(payload) != source:
        raise ValueError(f"{label} is not canonical JSON")
    return payload


def _require_sha256(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _require_runtime(value: object) -> dict[str, str]:
    if (
        not isinstance(value, Mapping)
        or not value
        or any(
            not isinstance(key, str)
            or not key
            or not isinstance(item, str)
            or not item
            for key, item in value.items()
        )
    ):
        raise ValueError("Faiss qualification runtime is invalid")
    return dict(value)


def _require_git_object(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-1 Git object")
    return value


def _validate_source(value: object) -> dict[str, str]:
    expected_fields = {
        "repository",
        "branch",
        "implementation_commit",
        "spirallens_package_tree",
    }
    if not isinstance(value, Mapping) or set(value) != expected_fields:
        raise ValueError("Faiss qualification source fields differ")
    source = dict(value)
    if (
        not isinstance(source.get("repository"), str)
        or not source["repository"]
        or not isinstance(source.get("branch"), str)
        or not source["branch"]
    ):
        raise ValueError("Faiss qualification source identity is invalid")
    _require_git_object(
        source.get("implementation_commit"),
        label="Faiss qualification implementation commit",
    )
    _require_git_object(
        source.get("spirallens_package_tree"),
        label="Faiss qualification package tree",
    )
    return {
        key: str(item)
        for key, item in source.items()
    }


def _pushed_source_contract(
    output_path: Path,
    *,
    reserved_output_allowed: bool,
) -> dict[str, str]:
    """Capture one clean, live-pushed Git source snapshot."""

    from spirallens.execution_freeze import (
        _git_bytes,
        _git_output,
        _validate_git_index_records,
    )

    repo_root = Path(__file__).resolve().parents[3]
    git_executable = Path("/usr/bin/git")
    branch = _git_output(
        git_executable,
        repo_root,
        "branch",
        "--show-current",
    )
    repository = _git_output(
        git_executable,
        repo_root,
        "remote",
        "get-url",
        "origin",
    )
    head = _git_output(
        git_executable,
        repo_root,
        "rev-parse",
        "HEAD",
    )
    package_tree = _git_output(
        git_executable,
        repo_root,
        "rev-parse",
        "HEAD:src/spirallens",
    )
    expected_status: list[str] = []
    if reserved_output_allowed:
        try:
            relative_output = output_path.relative_to(repo_root)
        except ValueError:
            pass
        else:
            expected_status = [f"?? {relative_output.as_posix()}"]
    index_records = [
        record
        for record in _git_bytes(
            git_executable,
            repo_root,
            "ls-files",
            "-v",
            "-z",
            "--",
            ".",
        ).split(b"\0")
        if record
    ]
    _validate_git_index_records(index_records)
    upstream = _git_output(
        git_executable,
        repo_root,
        "rev-parse",
        f"refs/remotes/origin/{branch}",
    )
    remote_lines = _git_output(
        git_executable,
        repo_root,
        "ls-remote",
        "--heads",
        repository,
        f"refs/heads/{branch}",
    ).splitlines()
    if (
        not branch
        or not repository
        or _git_output(
            git_executable,
            repo_root,
            "status",
            "--porcelain",
            "--untracked-files=all",
        ).splitlines()
        != expected_status
        or _git_output(
            git_executable,
            repo_root,
            "status",
            "--porcelain",
            "--ignored",
            "--untracked-files=all",
            "--",
            "src/spirallens",
        )
        or _git_output(
            git_executable,
            repo_root,
            "rev-parse",
            "--show-object-format",
        )
        != "sha1"
        or upstream != head
        or remote_lines != [f"{head}\trefs/heads/{branch}"]
    ):
        raise ValueError(
            "Faiss qualification requires one exact clean, live-pushed "
            "source snapshot"
        )
    return _validate_source(
        {
            "repository": repository,
            "branch": branch,
            "implementation_commit": head,
            "spirallens_package_tree": package_tree,
        }
    )


def _expected_search() -> dict[str, object]:
    return {
        "m": 32,
        "ef_construction": 200,
        "ef_search": 256,
        "seed": 1729,
        "thread_count": 1,
        "query_batch_size": QUALIFICATION_QUERY_COUNT,
        "range_call_batch_size": 1,
        "cosine_min": QUALIFICATION_COSINE_MIN,
        "score_margin": QUALIFICATION_SCORE_MARGIN,
        "radius": _qualification_radius(),
        "max_native_call_hits": QUALIFICATION_MAX_NATIVE_CALL_HITS,
        "max_raw_hits": QUALIFICATION_MAX_RAW_HITS,
    }


def _regenerated_fixture_digests(
    runtime_contract: Mapping[str, str],
) -> dict[str, str]:
    runtime = _require_runtime(runtime_contract)
    with tempfile.TemporaryDirectory(
        prefix="spirallens-faiss-fixture-validation-"
    ) as directory:
        output = Path(directory) / "fixture.json"
        _run_worker(
            [
                "fixture",
                "--output",
                str(output),
                "--fixture-schema-version",
                QUALIFICATION_FIXTURE_SCHEMA_VERSION,
                "--row-count",
                str(QUALIFICATION_ROW_COUNT),
                "--hidden-size",
                str(QUALIFICATION_HIDDEN_SIZE),
                "--cluster-size",
                str(QUALIFICATION_CLUSTER_SIZE),
                "--query-count",
                str(QUALIFICATION_QUERY_COUNT),
                "--fixture-seed",
                str(QUALIFICATION_FIXTURE_SEED),
            ],
            runtime_contract=runtime,
        )
        payload = _parse_canonical_json(
            output.read_bytes(),
            label="Faiss qualification regenerated fixture",
        )
    if set(payload) != {"fixture", "runtime"}:
        raise ValueError(
            "Faiss qualification regenerated fixture fields differ"
        )
    fixture = _validate_fixture(payload.get("fixture"))
    if _require_runtime(payload.get("runtime")) != runtime:
        raise ValueError(
            "Faiss qualification regenerated fixture runtime differs"
        )
    return {
        field_name: str(fixture[field_name])
        for field_name in (
            "states_sha256",
            "normalized_states_sha256",
            "query_indices_sha256",
        )
    }


def _validate_fixture(value: object) -> dict[str, object]:
    expected_fields = {
        "schema_version",
        "generator",
        "seed",
        "row_count",
        "hidden_size",
        "cluster_size",
        "query_count",
        "states_sha256",
        "normalized_states_sha256",
        "query_indices_sha256",
    }
    if not isinstance(value, Mapping) or set(value) != expected_fields:
        raise ValueError("Faiss qualification fixture fields differ")
    fixture = dict(value)
    expected_values = {
        "schema_version": QUALIFICATION_FIXTURE_SCHEMA_VERSION,
        "generator": (
            "numpy.pcg64.standard_normal.float32.cluster-repeat"
        ),
        "seed": QUALIFICATION_FIXTURE_SEED,
        "row_count": QUALIFICATION_ROW_COUNT,
        "hidden_size": QUALIFICATION_HIDDEN_SIZE,
        "cluster_size": QUALIFICATION_CLUSTER_SIZE,
        "query_count": QUALIFICATION_QUERY_COUNT,
    }
    if any(fixture.get(key) != item for key, item in expected_values.items()):
        raise ValueError("Faiss qualification fixture contract differs")
    for field_name in (
        "states_sha256",
        "normalized_states_sha256",
        "query_indices_sha256",
    ):
        _require_sha256(fixture.get(field_name), label=field_name)
    return fixture


def _validate_result(value: object) -> dict[str, object]:
    expected_fields = {
        "index_sha256",
        "limits_sha256",
        "scores_sha256",
        "labels_sha256",
        "raw_hit_count",
        "limits_length",
    }
    if not isinstance(value, Mapping) or set(value) != expected_fields:
        raise ValueError("Faiss qualification result fields differ")
    result = dict(value)
    for field_name in (
        "index_sha256",
        "limits_sha256",
        "scores_sha256",
        "labels_sha256",
    ):
        _require_sha256(result.get(field_name), label=field_name)
    raw_hit_count = result.get("raw_hit_count")
    if (
        isinstance(raw_hit_count, bool)
        or not isinstance(raw_hit_count, Integral)
        or not 0 < int(raw_hit_count) <= QUALIFICATION_MAX_RAW_HITS
        or result.get("limits_length") != QUALIFICATION_QUERY_COUNT + 1
    ):
        raise ValueError("Faiss qualification result shape is invalid")
    return result


def _validate_worker_payload(
    payload: Mapping[str, object],
    *,
    expected_runtime: Mapping[str, str] | None = None,
) -> dict[str, object]:
    if set(payload) != {"fixture", "search", "runtime", "result"}:
        raise ValueError("Faiss qualification worker fields differ")
    fixture = _validate_fixture(payload.get("fixture"))
    if payload.get("search") != _expected_search():
        raise ValueError("Faiss qualification search contract differs")
    runtime = _require_runtime(payload.get("runtime"))
    if expected_runtime is not None and runtime != dict(expected_runtime):
        raise ValueError("Faiss qualification worker runtime differs")
    result = _validate_result(payload.get("result"))
    return {
        "fixture": fixture,
        "search": _expected_search(),
        "runtime": runtime,
        "result": result,
    }


def _validate_receipt_payload(payload: Mapping[str, object]) -> None:
    expected_fields = {
        "schema_version",
        "status",
        "backend",
        "source",
        "fixture",
        "fixture_sha256",
        "search",
        "runtime",
        "cold_runs",
        "consumer_validation",
    }
    if set(payload) != expected_fields:
        raise ValueError("Faiss qualification receipt fields differ")
    if (
        payload.get("schema_version") != QUALIFICATION_SCHEMA_VERSION
        or payload.get("status") != "pass"
        or payload.get("backend")
        != {
            "backend_id": FAISS_HNSW_BACKEND_ID,
            "backend_version": FAISS_HNSW_RANGE_CALL_BACKEND_VERSION,
        }
    ):
        raise ValueError("Faiss qualification receipt identity is invalid")
    _validate_source(payload.get("source"))
    fixture = _validate_fixture(payload.get("fixture"))
    if payload.get("fixture_sha256") != canonical_json_sha256(fixture):
        raise ValueError("Faiss qualification fixture digest differs")
    if payload.get("search") != _expected_search():
        raise ValueError("Faiss qualification receipt search differs")
    _require_runtime(payload.get("runtime"))
    consumer_validation = payload.get("consumer_validation")
    if (
        not isinstance(consumer_validation, Mapping)
        or set(consumer_validation) != set(_CONSUMER_VALIDATION)
        or consumer_validation.get("fixture_regeneration")
        != _CONSUMER_VALIDATION["fixture_regeneration"]
        or consumer_validation.get("worker_runtime_bound") is not True
    ):
        raise ValueError(
            "Faiss qualification consumer validation differs"
        )
    cold_runs = payload.get("cold_runs")
    if (
        not isinstance(cold_runs, list)
        or len(cold_runs) != QUALIFICATION_COLD_RUNS
    ):
        raise ValueError("Faiss qualification cold-run count differs")
    results = [_validate_result(value) for value in cold_runs]
    if any(result != results[0] for result in results[1:]):
        raise ValueError(
            "Faiss qualification is not repeatable across cold subprocesses"
        )


@dataclass(frozen=True)
class FaissHNSWQualificationReceipt:
    """Strict, canonical receipt for the fixed native-call qualification."""

    _canonical_json: str
    _consumer_validation_token: object | None = field(
        default=None,
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self._canonical_json, str):
            raise TypeError("qualification receipt JSON must be a string")
        payload = _parse_canonical_json(
            self._canonical_json.encode("utf-8"),
            label="Faiss qualification receipt",
        )
        _validate_receipt_payload(payload)

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, object],
    ) -> FaissHNSWQualificationReceipt:
        _validate_receipt_payload(payload)
        return cls(_canonical_bytes(dict(payload)).decode("utf-8"))

    @classmethod
    def _from_consumer_validation(
        cls,
        receipt: FaissHNSWQualificationReceipt,
        *,
        token: object,
    ) -> FaissHNSWQualificationReceipt:
        if token is not _CONSUMER_VALIDATED_TOKEN:
            raise TypeError("invalid Faiss qualification validation token")
        validated = cls(receipt._canonical_json)
        object.__setattr__(
            validated,
            "_consumer_validation_token",
            token,
        )
        return validated

    def _require_consumer_validation(self) -> None:
        if self._consumer_validation_token is not _CONSUMER_VALIDATED_TOKEN:
            raise ValueError(
                "Faiss qualification receipt was not consumer-validated"
            )

    def to_dict(self) -> dict[str, object]:
        return json.loads(self._canonical_json)

    @property
    def canonical_bytes(self) -> bytes:
        return self._canonical_json.encode("utf-8")

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()

    @property
    def status(self) -> str:
        value = self.to_dict()["status"]
        assert isinstance(value, str)
        return value

    @property
    def backend_id(self) -> str:
        value = self.to_dict()["backend"]
        assert isinstance(value, dict)
        backend_id = value["backend_id"]
        assert isinstance(backend_id, str)
        return backend_id

    @property
    def backend_version(self) -> str:
        value = self.to_dict()["backend"]
        assert isinstance(value, dict)
        backend_version = value["backend_version"]
        assert isinstance(backend_version, str)
        return backend_version

    @property
    def fixture_sha256(self) -> str:
        value = self.to_dict()["fixture_sha256"]
        assert isinstance(value, str)
        return value

    @property
    def source(self) -> dict[str, str]:
        value = self.to_dict()["source"]
        assert isinstance(value, dict)
        return {str(key): str(item) for key, item in value.items()}

    @property
    def implementation_commit(self) -> str:
        return self.source["implementation_commit"]

    @property
    def spirallens_package_tree(self) -> str:
        return self.source["spirallens_package_tree"]

    @property
    def runtime(self) -> dict[str, str]:
        value = self.to_dict()["runtime"]
        assert isinstance(value, dict)
        return {str(key): str(item) for key, item in value.items()}

    @property
    def search(self) -> dict[str, object]:
        value = self.to_dict()["search"]
        assert isinstance(value, dict)
        return dict(value)

    @property
    def search_sha256(self) -> str:
        return canonical_json_sha256(self.search)

    @property
    def cold_process_runs(self) -> tuple[dict[str, object], ...]:
        value = self.to_dict()["cold_runs"]
        assert isinstance(value, list)
        return tuple(dict(item) for item in value if isinstance(item, dict))

    @property
    def max_native_call_hits(self) -> int:
        search = self.to_dict()["search"]
        assert isinstance(search, dict)
        value = search["max_native_call_hits"]
        assert isinstance(value, int)
        return value

    def validate_for_backend(
        self,
        *,
        config: FaissHNSWConfig,
        row_count: int,
        hidden_size: int,
        runtime_contract: Mapping[str, str],
    ) -> None:
        self._require_consumer_validation()
        payload = self.to_dict()
        fixture = payload["fixture"]
        search = payload["search"]
        runtime = payload["runtime"]
        assert isinstance(fixture, dict)
        assert isinstance(search, dict)
        assert isinstance(runtime, dict)
        comparable_runtime = dict(runtime_contract)
        comparable_runtime.pop("execution_freeze_sha256", None)
        if (
            config.backend_version
            != FAISS_HNSW_RANGE_CALL_BACKEND_VERSION
            or row_count != fixture["row_count"]
            or hidden_size != fixture["hidden_size"]
            or comparable_runtime != runtime
            or config.m != search["m"]
            or config.ef_construction != search["ef_construction"]
            or config.ef_search != search["ef_search"]
            or config.seed != search["seed"]
            or config.thread_count != search["thread_count"]
            or config.query_batch_size != search["query_batch_size"]
            or config.range_call_batch_size
            != search["range_call_batch_size"]
            or config.score_margin != search["score_margin"]
            or config.max_raw_hits != search["max_raw_hits"]
        ):
            raise ValueError(
                "Faiss backend differs from its qualification receipt"
            )

    def validate_search_radius(
        self,
        *,
        cosine_min: float,
        score_margin: float,
        radius: float,
    ) -> None:
        self._require_consumer_validation()
        search = self.to_dict()["search"]
        assert isinstance(search, dict)
        if (
            cosine_min != search["cosine_min"]
            or score_margin != search["score_margin"]
            or radius != search["radius"]
        ):
            raise ValueError(
                "Faiss range query differs from its qualification receipt"
            )


def _consumer_validated_receipt(
    receipt: FaissHNSWQualificationReceipt,
) -> FaissHNSWQualificationReceipt:
    """Issue a capability only after isolated fixture/runtime validation."""

    fixture = receipt.to_dict()["fixture"]
    assert isinstance(fixture, dict)
    if any(
        fixture.get(key) != value
        for key, value in _regenerated_fixture_digests(
            receipt.runtime
        ).items()
    ):
        raise ValueError(
            "Faiss qualification fixture differs from regeneration"
        )
    if receipt.fixture_sha256 != canonical_json_sha256(fixture):
        raise ValueError("Faiss qualification fixture identity differs")
    return FaissHNSWQualificationReceipt._from_consumer_validation(
        receipt,
        token=_CONSUMER_VALIDATED_TOKEN,
    )


def load_faiss_hnsw_qualification_receipt(
    path: str | Path,
    expected_sha256: str,
) -> FaissHNSWQualificationReceipt:
    """Load canonical bytes only when their out-of-band digest matches."""

    expected = _require_sha256(
        expected_sha256,
        label="expected qualification receipt SHA-256",
    )
    source_path = Path(os.path.abspath(path))
    for component in (source_path, *source_path.parents):
        metadata = component.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(
                "Faiss qualification receipt path must not contain symlinks"
            )
    read_flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        read_flags |= os.O_NOFOLLOW
    descriptor = os.open(source_path, read_flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(
                "Faiss qualification receipt must be a regular file"
            )
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        source = b"".join(chunks)
    finally:
        os.close(descriptor)
    after = source_path.lstat()
    if (
        stat.S_ISLNK(after.st_mode)
        or not stat.S_ISREG(after.st_mode)
        or (before.st_dev, before.st_ino)
        != (after.st_dev, after.st_ino)
    ):
        raise ValueError(
            "Faiss qualification receipt identity changed during read"
        )
    if hashlib.sha256(source).hexdigest() != expected:
        raise ValueError(
            "Faiss qualification receipt differs from its expected SHA-256"
        )
    payload = _parse_canonical_json(
        source,
        label="Faiss qualification receipt",
    )
    receipt = FaissHNSWQualificationReceipt.from_payload(payload)
    if receipt.canonical_bytes != source or receipt.sha256 != expected:
        raise ValueError("Faiss qualification receipt readback differs")
    return _consumer_validated_receipt(receipt)


def _assert_safe_output_parent(path: Path) -> None:
    if not path.is_absolute():
        raise ValueError("Faiss qualification output path must be absolute")
    parent = path.parent
    chain = [parent, *parent.parents]
    for directory in reversed(chain):
        details = directory.lstat()
        if stat.S_ISLNK(details.st_mode) or not stat.S_ISDIR(
            details.st_mode
        ):
            raise ValueError(
                "Faiss qualification output directory chain is unsafe"
            )


def _write_all(file_descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(file_descriptor, payload[offset:])
        if written <= 0:
            raise OSError("failed to write Faiss qualification receipt")
        offset += written


def _strict_worker_payload(
    path: Path,
    *,
    expected_runtime: Mapping[str, str],
) -> dict[str, object]:
    source = path.read_bytes()
    payload = _parse_canonical_json(
        source,
        label="Faiss qualification worker result",
    )
    return _validate_worker_payload(
        payload,
        expected_runtime=expected_runtime,
    )


def run_faiss_hnsw_qualification(
    output_path: str | Path,
    *,
    worker_runtime_contract: Mapping[str, str] | None = None,
) -> FaissHNSWQualificationReceipt:
    """Run two fixed cold subprocesses and exclusively persist one receipt."""

    from spirallens.execution_freeze import (
        current_worker_runtime_contract,
    )

    actual_runtime = current_worker_runtime_contract(None)
    runtime = (
        actual_runtime
        if worker_runtime_contract is None
        else dict(worker_runtime_contract)
    )
    if runtime != actual_runtime:
        raise ValueError(
            "Faiss qualification runtime differs from current imports"
        )
    path = Path(os.path.abspath(output_path))
    _assert_safe_output_parent(path)
    source = _pushed_source_contract(
        path,
        reserved_output_allowed=False,
    )
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    file_descriptor = os.open(path, flags, 0o600)
    reserved = os.fstat(file_descriptor)
    try:
        _write_all(
            file_descriptor,
            b"spirallens-faiss-hnsw-qualification-reservation-v0.2\n",
        )
        os.fsync(file_descriptor)
        with tempfile.TemporaryDirectory(
            prefix="spirallens-faiss-qualification-"
        ) as directory:
            root = Path(directory)
            worker_payloads: list[dict[str, object]] = []
            for repeat_index in range(QUALIFICATION_COLD_RUNS):
                result_path = root / f"cold-run-{repeat_index}.json"
                _run_worker(
                    [
                        "preflight",
                        "--output",
                        str(result_path),
                        "--fixture-schema-version",
                        QUALIFICATION_FIXTURE_SCHEMA_VERSION,
                        "--row-count",
                        str(QUALIFICATION_ROW_COUNT),
                        "--hidden-size",
                        str(QUALIFICATION_HIDDEN_SIZE),
                        "--cluster-size",
                        str(QUALIFICATION_CLUSTER_SIZE),
                        "--query-count",
                        str(QUALIFICATION_QUERY_COUNT),
                        "--fixture-seed",
                        str(QUALIFICATION_FIXTURE_SEED),
                        "--m",
                        "32",
                        "--ef-construction",
                        "200",
                        "--ef-search",
                        "256",
                        "--seed",
                        "1729",
                        "--query-batch-size",
                        str(QUALIFICATION_QUERY_COUNT),
                        "--range-call-batch-size",
                        "1",
                        "--cosine-min",
                        repr(QUALIFICATION_COSINE_MIN),
                        "--score-margin",
                        repr(QUALIFICATION_SCORE_MARGIN),
                        "--radius",
                        repr(_qualification_radius()),
                        "--max-native-call-hits",
                        str(QUALIFICATION_MAX_NATIVE_CALL_HITS),
                        "--max-raw-hits",
                        str(QUALIFICATION_MAX_RAW_HITS),
                    ],
                    runtime_contract=runtime,
                )
                worker_payloads.append(
                    _strict_worker_payload(
                        result_path,
                        expected_runtime=runtime,
                    )
                )
        first = worker_payloads[0]
        if any(payload != first for payload in worker_payloads[1:]):
            raise ValueError(
                "Faiss qualification cold subprocesses differ"
            )
        fixture = first["fixture"]
        assert isinstance(fixture, dict)
        receipt = FaissHNSWQualificationReceipt.from_payload(
            {
                "schema_version": QUALIFICATION_SCHEMA_VERSION,
                "status": "pass",
                "backend": {
                    "backend_id": FAISS_HNSW_BACKEND_ID,
                    "backend_version": (
                        FAISS_HNSW_RANGE_CALL_BACKEND_VERSION
                    ),
                },
                "source": source,
                "fixture": fixture,
                "fixture_sha256": canonical_json_sha256(fixture),
                "search": first["search"],
                "runtime": first["runtime"],
                "cold_runs": [
                    payload["result"] for payload in worker_payloads
                ],
                "consumer_validation": dict(_CONSUMER_VALIDATION),
            }
        )
        if (
            _pushed_source_contract(
                path,
                reserved_output_allowed=True,
            )
            != source
        ):
            raise ValueError(
                "Faiss qualification source changed during execution"
            )
        current = path.lstat()
        if (
            stat.S_ISLNK(current.st_mode)
            or not stat.S_ISREG(current.st_mode)
            or (current.st_dev, current.st_ino)
            != (reserved.st_dev, reserved.st_ino)
        ):
            raise ValueError(
                "Faiss qualification output identity changed during execution"
            )
        receipt = _consumer_validated_receipt(receipt)
        os.lseek(file_descriptor, 0, os.SEEK_SET)
        os.ftruncate(file_descriptor, 0)
        _write_all(file_descriptor, receipt.canonical_bytes)
        os.fsync(file_descriptor)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        os.close(file_descriptor)

    read_flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        read_flags |= os.O_NOFOLLOW
    read_descriptor = os.open(path, read_flags)
    try:
        readback_details = os.fstat(read_descriptor)
        chunks: list[bytes] = []
        while chunk := os.read(read_descriptor, 1024 * 1024):
            chunks.append(chunk)
        readback = b"".join(chunks)
    finally:
        os.close(read_descriptor)
    if (
        (readback_details.st_dev, readback_details.st_ino)
        != (reserved.st_dev, reserved.st_ino)
        or readback != receipt.canonical_bytes
        or hashlib.sha256(readback).hexdigest() != receipt.sha256
    ):
        raise ValueError("Faiss qualification receipt strict readback failed")
    loaded = load_faiss_hnsw_qualification_receipt(path, receipt.sha256)
    if loaded != receipt:
        raise ValueError("Faiss qualification receipt reload differs")
    config = FaissHNSWConfig(
        m=32,
        ef_construction=200,
        ef_search=256,
        seed=1729,
        thread_count=1,
        query_batch_size=QUALIFICATION_QUERY_COUNT,
        range_call_batch_size=1,
        score_margin=QUALIFICATION_SCORE_MARGIN,
        max_raw_hits=QUALIFICATION_MAX_RAW_HITS,
        max_proposed_pairs=10_000_000,
    )
    loaded.validate_for_backend(
        config=config,
        row_count=QUALIFICATION_ROW_COUNT,
        hidden_size=QUALIFICATION_HIDDEN_SIZE,
        runtime_contract=actual_runtime,
    )
    loaded.validate_search_radius(
        cosine_min=QUALIFICATION_COSINE_MIN,
        score_margin=QUALIFICATION_SCORE_MARGIN,
        radius=_qualification_radius(),
    )
    return loaded
