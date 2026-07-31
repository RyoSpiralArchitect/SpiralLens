"""Exact installed-distribution observation for the closed D7 runtime.

The D7 runtime lock is an inventory, not a dependency-solver request.  Every
line names one distribution and its exact installed version.  The inventory
includes both ``spirallens`` and ``pip``; neither is silently ignored.  The
live installed set must equal the parsed inventory before its digest can be
used by the fused-start verifier.  One physical metadata record is required
per normalized distribution name.  In particular, a dedicated editable
runtime must move aside its generated source-tree ``*.egg-info`` after the
environment's installed ``*.dist-info`` has been created; duplicate metadata
is not collapsed, even when both records state the same version.

This is a deep-internal qualification module.  It does not create a virtual
environment, install a package, resolve dependencies, attest a native runtime,
authorize execution, or establish an official D7 attempt.
"""

from __future__ import annotations

import importlib.metadata
import platform
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass

from spirallens.core.canonical import canonical_json_bytes, sha256_bytes

from .common import QualificationContractError

__all__: tuple[str, ...] = ()

D7_RUNTIME_DEPENDENCY_SET_SCHEME = (
    "spirallens.d7-fused-start-installed-dependency-set.v0.1"
)
D7_RUNTIME_LOCK_SELF_DISTRIBUTION = "spirallens"
D7_RUNTIME_LOCK_INSTALLER_DISTRIBUTION = "pip"
MAX_D7_RUNTIME_LOCK_BYTES = 64 * 1024
MAX_D7_RUNTIME_LOCK_DISTRIBUTIONS = 256

_EXACT_PIN_RE = re.compile(
    rb"(?P<name>[a-z0-9]+(?:-[a-z0-9]+)*)=="
    rb"(?P<version>(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*))*)"
)
_CANONICAL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True, order=True, slots=True)
class _ExactDistributionPin:
    name: str
    version: str

    def __post_init__(self) -> None:
        if (
            type(self.name) is not str
            or _CANONICAL_NAME_RE.fullmatch(self.name) is None
        ):
            raise QualificationContractError(
                "runtime-lock distribution name must be canonical lowercase"
            )
        if type(self.version) is not str:
            raise QualificationContractError(
                "runtime-lock distribution version must be text"
            )
        try:
            source = f"{self.name}=={self.version}".encode("ascii")
        except UnicodeEncodeError as error:
            raise QualificationContractError(
                "runtime-lock distribution version must be ASCII"
            ) from error
        match = _EXACT_PIN_RE.fullmatch(source)
        if match is None or match.group("version").decode("ascii") != self.version:
            raise QualificationContractError(
                "runtime-lock distribution version has forbidden syntax"
            )


@dataclass(frozen=True, slots=True)
class _RuntimeDependencyObservation:
    dependency_lock_sha256: str
    transitive_dependency_set_sha256: str
    distributions: tuple[_ExactDistributionPin, ...]


def _normalize_distribution_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _parse_exact_dependency_lock(source: bytes) -> tuple[_ExactDistributionPin, ...]:
    """Parse one canonical, closed installed-distribution inventory."""

    if type(source) is not bytes:
        raise QualificationContractError("D7 runtime lock source must be exact bytes")
    if not source or len(source) > MAX_D7_RUNTIME_LOCK_BYTES:
        raise QualificationContractError(
            "D7 runtime lock must be nonempty and within its fixed byte cap"
        )
    if not source.endswith(b"\n") or b"\r" in source or b"\0" in source:
        raise QualificationContractError(
            "D7 runtime lock must use canonical LF-terminated ASCII lines"
        )
    raw_lines = source[:-1].split(b"\n")
    if (
        not raw_lines
        or len(raw_lines) > MAX_D7_RUNTIME_LOCK_DISTRIBUTIONS
        or any(not line for line in raw_lines)
    ):
        raise QualificationContractError(
            "D7 runtime lock has an empty or oversized distribution inventory"
        )

    pins: list[_ExactDistributionPin] = []
    for index, line in enumerate(raw_lines):
        match = _EXACT_PIN_RE.fullmatch(line)
        if match is None:
            raise QualificationContractError(
                f"D7 runtime lock line {index + 1} is not one canonical exact pin"
            )
        pins.append(
            _ExactDistributionPin(
                name=match.group("name").decode("ascii"),
                version=match.group("version").decode("ascii"),
            )
        )

    observed = tuple(pins)
    if observed != tuple(sorted(observed)):
        raise QualificationContractError(
            "D7 runtime lock pins must be sorted by canonical name and version"
        )
    names = tuple(pin.name for pin in observed)
    if len(set(names)) != len(names):
        raise QualificationContractError(
            "D7 runtime lock contains a duplicate distribution"
        )
    for required in (
        D7_RUNTIME_LOCK_INSTALLER_DISTRIBUTION,
        D7_RUNTIME_LOCK_SELF_DISTRIBUTION,
    ):
        if required not in names:
            raise QualificationContractError(
                f"D7 runtime lock must explicitly include {required}"
            )
    return observed


def _observe_installed_distributions(
    distributions: Iterable[importlib.metadata.Distribution] | None = None,
) -> tuple[_ExactDistributionPin, ...]:
    """Observe the complete installed distribution set without exclusions."""

    source = (
        importlib.metadata.distributions() if distributions is None else distributions
    )
    observed: dict[str, str] = {}
    count = 0
    for distribution in source:
        count += 1
        if count > MAX_D7_RUNTIME_LOCK_DISTRIBUTIONS:
            raise QualificationContractError(
                "installed dependency set exceeds its fixed distribution cap"
            )
        name = distribution.metadata.get("Name")
        version = distribution.version
        if type(name) is not str or not name or type(version) is not str or not version:
            raise QualificationContractError(
                "installed distribution lacks a canonical name or version"
            )
        normalized = _normalize_distribution_name(name)
        pin = _ExactDistributionPin(name=normalized, version=version)
        if pin.name in observed:
            if observed[pin.name] != pin.version:
                raise QualificationContractError(
                    "installed dependency set contains conflicting versions"
                )
            raise QualificationContractError(
                "installed dependency set contains a duplicate distribution"
            )
        observed[pin.name] = pin.version
    return tuple(
        _ExactDistributionPin(name=name, version=observed[name])
        for name in sorted(observed)
    )


def _dependency_set_sha256(
    distributions: tuple[_ExactDistributionPin, ...],
) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "schema_version": D7_RUNTIME_DEPENDENCY_SET_SCHEME,
                "python_implementation": sys.implementation.name,
                "python_version": platform.python_version(),
                "distributions": [
                    {"name": pin.name, "version": pin.version} for pin in distributions
                ],
            }
        )
    )


def _verify_exact_dependency_lock(
    source: bytes,
    *,
    distributions: Iterable[importlib.metadata.Distribution] | None = None,
) -> _RuntimeDependencyObservation:
    """Require exact equality between the lock and every installed distribution."""

    expected = _parse_exact_dependency_lock(source)
    installed = _observe_installed_distributions(distributions)
    if installed != expected:
        expected_by_name = {pin.name: pin.version for pin in expected}
        installed_by_name = {pin.name: pin.version for pin in installed}
        missing = sorted(expected_by_name.keys() - installed_by_name.keys())
        unexpected = sorted(installed_by_name.keys() - expected_by_name.keys())
        mismatched = sorted(
            name
            for name in expected_by_name.keys() & installed_by_name.keys()
            if expected_by_name[name] != installed_by_name[name]
        )
        raise QualificationContractError(
            "installed dependency set differs from the exact D7 runtime lock "
            f"(missing={missing}, unexpected={unexpected}, "
            f"version_mismatch={mismatched})"
        )
    return _RuntimeDependencyObservation(
        dependency_lock_sha256=sha256_bytes(source),
        transitive_dependency_set_sha256=_dependency_set_sha256(installed),
        distributions=installed,
    )
