#!/usr/bin/env python3
"""Inspect the frozen D7 v1 entrypoint coordinates, then fail closed.

This source coordinate is intentionally not a materializer.  A private source
now closes the frozen external chronology, but its mere presence grants no
review, source-selection, runtime-closure, invocation, or materialization
authority.  This script remains deliberately unwired from that operation: it
performs read-only coordinate checks and refuses to create either official or
staging paths.

Import and ``--help`` perform no supplier invocation, publication, execution,
or mutation of the declared official and staging namespaces.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import os
from pathlib import Path
import sys
from typing import NoReturn


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PREPARATION_SCRIPT = "scripts/prepare_d7_v1_launch.py"
RUNNER_SCRIPT = "scripts/run_d7_v1.py"
OFFICIAL_CALLABLE = (
    "spirallens.qualification.confirmation_v1_official_execution:"
    "produce_d7_v1_official_result"
)
OFFICIAL_EXTERNAL_STAGING_PATH = Path(
    "/Users/ryohiga/SpiralReality/.spirallens-d7-v1-store.staging"
)
OFFICIAL_EXTERNAL_STORE_PATH = Path(
    "/Users/ryohiga/SpiralReality/spirallens-d7-v1-store"
)
PREPARATION_BLOCK_ID = (
    "d7-v1-source-selection-runtime-closure-and-invocation-authority-absent"
)

_BOOTSTRAP_SYS_PATH = tuple(sys.path)
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))
try:
    from spirallens._repository_context import RepositoryContext  # noqa: E402
    from spirallens.qualification import (  # noqa: E402
        confirmation_v1_materialization as verification,
    )
    from spirallens.qualification import (  # noqa: E402
        confirmation_v1_private_publication as publication,
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
            "Validate the frozen D7 v1 source-only entrypoint coordinates. "
            "Materialization remains blocked until independent source review "
            "and selection, runtime closure, and invocation authority exist."
        )
    )


def _require_repository_cwd() -> None:
    if Path(os.path.realpath(os.getcwd())) != REPOSITORY_ROOT:
        raise RuntimeError("D7 v1 preparation requires the exact repository cwd")


def _require_source_origins(repository: RepositoryContext) -> None:
    expected = (
        (
            verification.__file__,
            "src/spirallens/qualification/confirmation_v1_materialization.py",
        ),
        (
            publication.__file__,
            "src/spirallens/qualification/confirmation_v1_private_publication.py",
        ),
        (
            official.__file__,
            "src/spirallens/qualification/confirmation_v1_official_execution.py",
        ),
    )
    if any(
        not repository.matches_imported_file(
            imported_file=imported_file,
            repository_path=repository_path,
        )
        for imported_file, repository_path in expected
    ):
        raise QualificationContractError(
            "D7 v1 preparation import origin differs from this repository"
        )


def _require_frozen_coordinates(repository: RepositoryContext) -> None:
    _require_source_origins(repository)
    protocol = verification._load_d7_v1_materialization_protocol(repository)
    _route_source, route = verification._route_source(repository, protocol)
    route_store, route_staging, route_runner, route_callable = (
        verification._expected_route_coordinates(route)
    )
    declaration = verification._mapping(
        route.get("strict_successor_declaration"),
        label="strict successor declaration",
    )
    entrypoints = verification._mapping(
        declaration.get("future_entrypoint_coordinates"),
        label="future entrypoint coordinates",
    )
    route_preparer = verification._relative_path(
        entrypoints.get("preparation_script"),
        label="route preparation script",
    )
    if (
        route_preparer != PREPARATION_SCRIPT
        or route_runner != RUNNER_SCRIPT
        or route_callable != OFFICIAL_CALLABLE
        or route_staging != OFFICIAL_EXTERNAL_STAGING_PATH
        or route_store != OFFICIAL_EXTERNAL_STORE_PATH
        or official.D7_V1_OFFICIAL_CALLABLE != OFFICIAL_CALLABLE
    ):
        raise QualificationContractError("D7 v1 entrypoint coordinates differ")

    facts = verification._mapping(
        protocol.document.get("facts_at_protocol_issue"),
        label="facts at protocol issue",
    )
    authority = verification._mapping(
        protocol.document.get("authority"),
        label="protocol authority",
    )
    if (
        facts.get("execution_started") is not False
        or facts.get("successor_materialized") is not False
        or authority.get("materialization_authorized_in_this_record") is not False
        or authority.get("d7_execution_authorized") is not False
    ):
        raise QualificationContractError(
            "D7 v1 frozen protocol no-authority facts differ"
        )

    # The reviewed private publisher is a callable source dependency, not an
    # authorization to call it with caller-invented bytes.
    if not callable(publication._publish_d7_v1_pre_item23_records_no_replace):
        raise QualificationContractError("D7 v1 private publisher is unavailable")


def _raise_source_only_block() -> NoReturn:
    raise RuntimeError(
        "D7 v1 preparation is source-only and blocked: the private chronology "
        "operation is intentionally unwired, and no independent reviewed "
        "source selection, runtime closure, or invocation authority has been "
        f"established ({PREPARATION_BLOCK_ID})"
    )


def main(argv: Sequence[str] | None = None) -> NoReturn:
    _parser().parse_args(argv)
    _require_repository_cwd()
    repository = RepositoryContext(root=REPOSITORY_ROOT)
    _require_frozen_coordinates(repository)
    _raise_source_only_block()


if __name__ == "__main__":
    main()
