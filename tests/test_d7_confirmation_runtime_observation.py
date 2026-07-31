from __future__ import annotations

import platform
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from spirallens import qualification
from spirallens.core.canonical import sha256_bytes
from spirallens.qualification import confirmation_fused_start as fused_start
from spirallens.qualification import confirmation_runtime_observation as runtime
from spirallens.qualification.common import QualificationContractError


_LOCK = (
    b"cffi==2.0.0\n"
    b"cryptography==46.0.7\n"
    b"numpy==2.4.4\n"
    b"pip==26.1.1\n"
    b"pycparser==3.0\n"
    b"pyyaml==6.0.3\n"
    b"scipy==1.17.1\n"
    b"spirallens==0.1.0\n"
)


def _distribution(name: str, version: str) -> SimpleNamespace:
    return SimpleNamespace(metadata={"Name": name}, version=version)


def _digest(label: str) -> str:
    return sha256_bytes(label.encode("ascii"))


def _distributions() -> tuple[SimpleNamespace, ...]:
    return (
        _distribution("cffi", "2.0.0"),
        _distribution("cryptography", "46.0.7"),
        _distribution("numpy", "2.4.4"),
        _distribution("pip", "26.1.1"),
        _distribution("pycparser", "3.0"),
        _distribution("PyYAML", "6.0.3"),
        _distribution("scipy", "1.17.1"),
        _distribution("spirallens", "0.1.0"),
    )


def test_runtime_observation_surface_is_deep_internal() -> None:
    assert runtime.__all__ == ()
    assert not hasattr(qualification, "verify_exact_dependency_lock")
    assert not hasattr(qualification, "RuntimeDependencyObservation")


def test_repository_runtime_lock_is_the_canonical_closed_inventory() -> None:
    lock_path = Path(__file__).parents[1] / "requirements-d7-runtime-lock.txt"
    source = lock_path.read_bytes()

    assert source == _LOCK
    pins = runtime._parse_exact_dependency_lock(source)
    assert tuple((pin.name, pin.version) for pin in pins) == (
        ("cffi", "2.0.0"),
        ("cryptography", "46.0.7"),
        ("numpy", "2.4.4"),
        ("pip", "26.1.1"),
        ("pycparser", "3.0"),
        ("pyyaml", "6.0.3"),
        ("scipy", "1.17.1"),
        ("spirallens", "0.1.0"),
    )


def test_exact_inventory_equality_precedes_dependency_set_digest() -> None:
    observation = runtime._verify_exact_dependency_lock(
        _LOCK,
        distributions=reversed(_distributions()),
    )

    assert observation.dependency_lock_sha256 == sha256_bytes(_LOCK)
    assert len(observation.transitive_dependency_set_sha256) == 64
    assert tuple(pin.name for pin in observation.distributions) == (
        "cffi",
        "cryptography",
        "numpy",
        "pip",
        "pycparser",
        "pyyaml",
        "scipy",
        "spirallens",
    )


def test_fused_runtime_observation_uses_exact_inventory_verifier(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    dependency_observation = runtime._RuntimeDependencyObservation(
        dependency_lock_sha256=sha256_bytes(_LOCK),
        transitive_dependency_set_sha256=_digest("dependency-set"),
        distributions=runtime._parse_exact_dependency_lock(_LOCK),
    )
    source_tree_sha256 = _digest("source-tree")
    native_runtime_sha256 = _digest("native-runtime")
    snapshot = SimpleNamespace(
        repository_root=tmp_path,
        runtime_specification=SimpleNamespace(
            python_implementation=sys.implementation.name,
            python_version=platform.python_version(),
            platform=sys.platform,
            machine=platform.machine().lower(),
            dependency_lock_sha256=dependency_observation.dependency_lock_sha256,
            native_runtime_sha256=native_runtime_sha256,
        ),
        source_runtime_closure=SimpleNamespace(
            source_commit="a" * 40,
            source_tree_sha256=source_tree_sha256,
            transitive_dependency_set_sha256=(
                dependency_observation.transitive_dependency_set_sha256
            ),
        ),
    )
    verifier_inputs: list[bytes] = []

    def verify(source: bytes) -> runtime._RuntimeDependencyObservation:
        verifier_inputs.append(source)
        return dependency_observation

    monkeypatch.setattr(fused_start, "_read_regular_file", lambda *_args, **_kw: _LOCK)
    monkeypatch.setattr(
        fused_start,
        "_source_tree_sha256",
        lambda _root, _commit: source_tree_sha256,
    )
    monkeypatch.setattr(
        fused_start,
        "_hash_regular_file",
        lambda *_args, **_kwargs: native_runtime_sha256,
    )
    monkeypatch.setattr(runtime, "_verify_exact_dependency_lock", verify)

    observed = fused_start._observe_runtime(snapshot)

    assert verifier_inputs == [_LOCK]
    assert observed.dependency_lock_sha256 == sha256_bytes(_LOCK)
    assert observed.transitive_dependency_set_sha256 == _digest("dependency-set")


@pytest.mark.parametrize(
    "source, match",
    (
        (b"", "nonempty"),
        (_LOCK[:-1], "LF-terminated"),
        (_LOCK.replace(b"\n", b"\r\n"), "LF-terminated"),
        (_LOCK + b"\n", "empty"),
        (b"# generated\n" + _LOCK, "canonical exact pin"),
        (_LOCK.replace(b"numpy==", b"NumPy=="), "canonical exact pin"),
        (_LOCK.replace(b"numpy==", b"numpy =="), "canonical exact pin"),
        (_LOCK.replace(b"numpy==2.4.4", b"numpy>=2.4.4"), "canonical exact pin"),
        (_LOCK.replace(b"numpy==2.4.4", b"numpy==02.4.4"), "canonical exact pin"),
        (_LOCK.replace(b"numpy==2.4.4", b"numpy==2.4.4rc1"), "canonical exact pin"),
        (
            _LOCK.replace(b"numpy==2.4.4", b"numpy==2.4.4; python_version>'3'"),
            "canonical exact pin",
        ),
        (
            _LOCK.replace(b"numpy==2.4.4", b"numpy==2.4.4 --hash=sha256:00"),
            "canonical exact pin",
        ),
        (
            _LOCK.replace(b"numpy==2.4.4", b"numpy @ https://invalid.example/n.whl"),
            "canonical exact pin",
        ),
        (
            _LOCK.replace(
                b"numpy==2.4.4\npip==26.1.1",
                b"pip==26.1.1\nnumpy==2.4.4",
            ),
            "sorted",
        ),
        (
            _LOCK.replace(b"numpy==2.4.4", b"pip==26.1.1"),
            "duplicate",
        ),
        (_LOCK.replace(b"pip==26.1.1\n", b""), "include pip"),
        (_LOCK.replace(b"spirallens==0.1.0\n", b""), "include spirallens"),
    ),
)
def test_lock_parser_rejects_noncanonical_or_implicit_inventory(
    source: bytes,
    match: str,
) -> None:
    with pytest.raises(QualificationContractError, match=match):
        runtime._parse_exact_dependency_lock(source)


@pytest.mark.parametrize(
    "distributions, match",
    (
        (_distributions()[:-1], "missing=\\['spirallens'\\]"),
        (
            _distributions() + (_distribution("setuptools", "81.0.0"),),
            "unexpected=\\['setuptools'\\]",
        ),
        (
            tuple(
                _distribution(item.metadata["Name"], "2.4.3")
                if item.metadata["Name"] == "numpy"
                else item
                for item in _distributions()
            ),
            "version_mismatch=\\['numpy'\\]",
        ),
    ),
)
def test_lock_equality_rejects_missing_unexpected_and_version_drift(
    distributions: tuple[SimpleNamespace, ...],
    match: str,
) -> None:
    with pytest.raises(QualificationContractError, match=match):
        runtime._verify_exact_dependency_lock(
            _LOCK,
            distributions=distributions,
        )


@pytest.mark.parametrize("conflicting", (False, True))
def test_installed_inventory_requires_one_physical_metadata_record_per_name(
    conflicting: bool,
) -> None:
    duplicate_version = "2.4.3" if conflicting else "2.4.4"
    distributions = _distributions() + (_distribution("NUMPY", duplicate_version),)
    expected = "conflicting versions" if conflicting else "duplicate distribution"

    with pytest.raises(QualificationContractError, match=expected):
        runtime._observe_installed_distributions(distributions)


@pytest.mark.parametrize(
    "distribution",
    (
        SimpleNamespace(metadata={}, version="1.0.0"),
        SimpleNamespace(metadata={"Name": "bad"}, version=""),
        SimpleNamespace(metadata={"Name": "-bad"}, version="1.0.0"),
        SimpleNamespace(metadata={"Name": "bad"}, version="latest"),
    ),
)
def test_installed_inventory_rejects_unidentified_or_unpinned_members(
    distribution: SimpleNamespace,
) -> None:
    with pytest.raises(QualificationContractError):
        runtime._observe_installed_distributions((distribution,))
