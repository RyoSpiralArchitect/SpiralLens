#!/usr/bin/env python3
"""Fail-closed runner coordinate for the fresh D7 v1 successor.

The frozen v1 protocol declares this path and an official callable, but it
does not define the later launch-authority and execution-start transition
required to dispatch that callable.  This runner therefore authenticates the
source-only coordinate and then stops without calling the producer.

Import and ``--help`` perform no publication, execution, model access, subject
access, or mutation of the declared official and staging namespaces.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import os
from pathlib import Path
import sys
from typing import NoReturn


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RUNNER_SCRIPT = "scripts/run_d7_v1.py"
OFFICIAL_CALLABLE = (
    "spirallens.qualification.confirmation_v1_official_execution:"
    "produce_d7_v1_official_result"
)
RUNNER_BLOCK_ID = "d7-v1-launch-authority-and-start-contract-absent"

_BOOTSTRAP_SYS_PATH = tuple(sys.path)
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))
try:
    from spirallens._repository_context import RepositoryContext  # noqa: E402
    from spirallens.qualification import (  # noqa: E402
        confirmation_v1_materialization as verification,
    )
    from spirallens.qualification import (  # noqa: E402
        confirmation_v1_official_execution as official,
    )
    from spirallens.qualification.common import (  # noqa: E402
        QualificationContractError,
    )
finally:
    sys.path[:] = _BOOTSTRAP_SYS_PATH


def _parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        description=(
            "Validate the D7 v1 runner coordinate. Official dispatch remains "
            "blocked until a reviewed launch-authority and execution-start "
            "contract exists."
        )
    )


def _require_repository_cwd() -> None:
    if Path(os.path.realpath(os.getcwd())) != REPOSITORY_ROOT:
        raise RuntimeError("D7 v1 runner requires the exact repository cwd")


def _require_frozen_coordinates(repository: RepositoryContext) -> None:
    expected_module_path = (
        "src/spirallens/qualification/confirmation_v1_official_execution.py"
    )
    if not repository.matches_imported_file(
        imported_file=official.__file__, repository_path=expected_module_path
    ):
        raise QualificationContractError(
            "D7 v1 official callable import origin differs from this repository"
        )
    protocol = verification._load_d7_v1_materialization_protocol(repository)
    _route_source, route = verification._route_source(repository, protocol)
    _store, _staging, route_runner, route_callable = (
        verification._expected_route_coordinates(route)
    )
    if (
        route_runner != RUNNER_SCRIPT
        or route_callable != OFFICIAL_CALLABLE
        or official.D7_V1_OFFICIAL_CALLABLE != OFFICIAL_CALLABLE
        or official.D7_V1_EXECUTION_BLOCK_ID != RUNNER_BLOCK_ID
    ):
        raise QualificationContractError("D7 v1 runner coordinates differ")


def _raise_dispatch_block() -> NoReturn:
    raise RuntimeError(
        "D7 v1 official dispatch is blocked: the frozen protocol defines only "
        "a non-authorizing pre-start reservation and no reviewed launch-"
        f"authority or execution-start transition ({RUNNER_BLOCK_ID})"
    )


def main(argv: Sequence[str] | None = None) -> NoReturn:
    _parser().parse_args(argv)
    _require_repository_cwd()
    repository = RepositoryContext(root=REPOSITORY_ROOT)
    _require_frozen_coordinates(repository)
    _raise_dispatch_block()


if __name__ == "__main__":
    main()
