#!/usr/bin/env python3
"""Preclaim one fixed local D0--D5 store and publish its launch descriptor."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from spirallens.qualification import (
    prepare_selection_launch,
    write_prepared_selection_launch_descriptor,
)


def _absolute(path: str) -> Path:
    return Path(os.path.abspath(path))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verify a frozen D0-D5 preparation, preclaim its one trusted "
            "local store, and publish the only launch descriptor accepted "
            "by the fresh execution process."
        )
    )
    parser.add_argument("--descriptor-id", required=True)
    parser.add_argument("--descriptor-output", required=True)
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--referent", required=True)
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--protocol-source-sha256", required=True)
    parser.add_argument("--protocol-canonical-sha256", required=True)
    parser.add_argument("--freeze", required=True)
    parser.add_argument("--freeze-source-sha256", required=True)
    parser.add_argument("--freeze-canonical-sha256", required=True)
    parser.add_argument("--attempt-store", required=True)
    parser.add_argument("--claim-id", required=True)
    return parser


def _ensure_attempt_store(path: Path) -> None:
    if path.is_symlink():
        raise RuntimeError("attempt store must not be a symbolic link")
    if path.exists():
        if not path.is_dir():
            raise RuntimeError("attempt store must be a real directory")
        return
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise RuntimeError("attempt-store parent must be an existing real directory")
    path.mkdir(mode=0o755)


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    descriptor_path = _absolute(arguments.descriptor_output)
    attempt_store = _absolute(arguments.attempt_store)
    if descriptor_path.exists() or descriptor_path.is_symlink():
        raise RuntimeError(
            f"refusing to overwrite launch descriptor: {descriptor_path}"
        )
    if not descriptor_path.parent.is_dir() or descriptor_path.parent.is_symlink():
        raise RuntimeError(
            "launch-descriptor parent must be an existing real directory"
        )
    _ensure_attempt_store(attempt_store)

    launch = prepare_selection_launch(
        descriptor_id=arguments.descriptor_id,
        repository_root=_absolute(arguments.repository_root),
        registry_path=_absolute(arguments.registry),
        referent_path=_absolute(arguments.referent),
        protocol_path=_absolute(arguments.protocol),
        protocol_source_sha256=arguments.protocol_source_sha256,
        protocol_canonical_sha256=arguments.protocol_canonical_sha256,
        freeze_path=_absolute(arguments.freeze),
        freeze_source_sha256=arguments.freeze_source_sha256,
        freeze_canonical_sha256=arguments.freeze_canonical_sha256,
        attempt_store_path=attempt_store,
        claim_id=arguments.claim_id,
    )
    loaded_descriptor = write_prepared_selection_launch_descriptor(
        descriptor_path,
        launch.descriptor,
    )
    if loaded_descriptor.descriptor != launch.descriptor:
        raise RuntimeError("launch descriptor differs after canonical round-trip")
    print(
        json.dumps(
            {
                "attempt_claim_canonical_sha256": (
                    launch.attempt_claim.canonical_sha256
                ),
                "attempt_claim_path": launch.descriptor.attempt_claim_path,
                "attempt_store_path": launch.descriptor.attempt_store_path,
                "cross_store_uniqueness_proved": False,
                "descriptor_canonical_sha256": (loaded_descriptor.canonical_sha256),
                "descriptor_path": str(loaded_descriptor.source_path),
                "descriptor_source_sha256": loaded_descriptor.source_sha256,
                "execution_started": False,
                "global_one_shot_proved": False,
                "source_readiness_summary_sha256": (
                    launch.descriptor.source_readiness_summary_sha256
                ),
                "terminal_publication_operationally_proved": False,
                "terminal_publication_symbol_resolved": True,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
