#!/usr/bin/env python3
"""Prepare, but never execute, the closed D0--D5 selection family.

The two selection seeds are generated only when the source-readiness API
invokes the delayed supplier.  They are never accepted on the command line.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
from pathlib import Path

from spirallens.qualification import (
    CLOSED_D0_D5_KNOWN_SEED_EXCLUSION_REGISTRY,
    CLOSED_D0_D5_SELECTION_SEED_COUNT,
    SelectionFreezeArtifact,
    load_qualification_protocol,
    load_selection_freeze,
    prepare_closed_d0_d5_selection_protocol,
    write_qualification_protocol,
    write_selection_freeze,
)


def _absolute(path: str) -> Path:
    return Path(os.path.abspath(path))


def _git_text(repository_root: Path, arguments: list[str]) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository_root), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(arguments)} failed: {completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def _require_clean_engine_head(
    repository_root: Path,
    *,
    engine_commit: str,
) -> None:
    resolved = _git_text(
        repository_root,
        ["rev-parse", f"{engine_commit}^{{commit}}"],
    )
    head = _git_text(repository_root, ["rev-parse", "HEAD"])
    if resolved != engine_commit or head != engine_commit:
        raise RuntimeError(
            "engine commit must resolve exactly and equal the preparation HEAD"
        )
    status = _git_text(
        repository_root,
        [
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
            "--",
            "src/spirallens",
            "scripts/prepare_d0_d5_launch.py",
            "scripts/prepare_d0_d5_selection.py",
            "scripts/run_d0_d5_selection.py",
        ],
    )
    if status:
        raise RuntimeError(
            "engine source or official launch scripts differ from engine HEAD"
        )


def _preflight_output(path: Path, *, label: str) -> None:
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise RuntimeError(f"{label} parent must be an existing real directory")
    if path.exists() or path.is_symlink():
        raise RuntimeError(f"refusing to overwrite existing {label}: {path}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Publish pre-seed readiness, the 64-primary D0-D5 protocol, and "
            "an unopened freeze without generating synthetic outcomes."
        )
    )
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--engine-commit", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--referent", required=True)
    parser.add_argument("--source-readiness-output", required=True)
    parser.add_argument("--protocol-output", required=True)
    parser.add_argument("--freeze-output", required=True)
    parser.add_argument("--freeze-id", required=True)
    parser.add_argument("--seed-family-id", required=True)
    return parser


def _delayed_selection_seed_supplier() -> tuple[int, ...]:
    excluded = set(CLOSED_D0_D5_KNOWN_SEED_EXCLUSION_REGISTRY.seeds)
    seeds: set[int] = set()
    while len(seeds) < CLOSED_D0_D5_SELECTION_SEED_COUNT:
        candidate = secrets.randbits(63)
        if candidate not in excluded:
            seeds.add(candidate)
    return tuple(sorted(seeds))


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    repository_root = _absolute(arguments.repository_root)
    registry_path = _absolute(arguments.registry)
    referent_path = _absolute(arguments.referent)
    source_readiness_path = _absolute(arguments.source_readiness_output)
    protocol_path = _absolute(arguments.protocol_output)
    freeze_path = _absolute(arguments.freeze_output)
    output_paths = (source_readiness_path, protocol_path, freeze_path)
    if len(set(output_paths)) != len(output_paths):
        raise RuntimeError(
            "source-readiness, protocol, and freeze outputs must be distinct"
        )
    for path, label in (
        (source_readiness_path, "pre-seed readiness artifact"),
        (protocol_path, "qualification protocol"),
        (freeze_path, "selection freeze"),
    ):
        _preflight_output(path, label=label)

    _require_clean_engine_head(
        repository_root,
        engine_commit=arguments.engine_commit,
    )
    supplier_call_count = 0

    def supply_selection_seeds() -> tuple[int, ...]:
        nonlocal supplier_call_count
        supplier_call_count += 1
        if supplier_call_count != 1:
            raise RuntimeError("selection seed supplier may be called exactly once")
        return _delayed_selection_seed_supplier()

    protocol, source_readiness = prepare_closed_d0_d5_selection_protocol(
        engine_commit=arguments.engine_commit,
        repository_root=repository_root,
        registry_path=registry_path,
        referent_path=referent_path,
        preseed_readiness_path=source_readiness_path,
        selection_seed_supplier=supply_selection_seeds,
    )

    if protocol.preseed_readiness is None:
        raise RuntimeError("official protocol lacks pre-seed readiness binding")
    if (
        protocol.preseed_readiness.source_binding_receipt_sha256
        != source_readiness.canonical_sha256
    ):
        raise RuntimeError(
            "pre-seed readiness binding differs from verified source receipt"
        )
    source_readiness_sha256 = protocol.preseed_readiness.artifact_canonical_sha256
    protocol_identity = write_qualification_protocol(protocol_path, protocol)
    loaded_protocol = load_qualification_protocol(
        protocol_path,
        expected_source_sha256=protocol_identity.source_sha256,
        expected_canonical_sha256=protocol_identity.canonical_sha256,
    )
    freeze = SelectionFreezeArtifact.from_loaded_protocol(
        freeze_id=arguments.freeze_id,
        loaded_protocol=loaded_protocol,
        seed_family_id=arguments.seed_family_id,
    )
    freeze_identity = write_selection_freeze(freeze_path, freeze)
    loaded_freeze = load_selection_freeze(
        freeze_path,
        expected_source_sha256=freeze_identity.source_sha256,
        expected_canonical_sha256=freeze_identity.canonical_sha256,
        loaded_protocol=loaded_protocol,
    )
    if loaded_freeze != freeze:
        raise RuntimeError("selection freeze differs after canonical round-trip")
    print(
        json.dumps(
            {
                "engine_commit": arguments.engine_commit,
                "freeze_canonical_sha256": freeze_identity.canonical_sha256,
                "freeze_path": str(freeze_identity.path),
                "freeze_source_sha256": freeze_identity.source_sha256,
                "protocol_canonical_sha256": (protocol_identity.canonical_sha256),
                "protocol_path": str(protocol_identity.path),
                "protocol_source_sha256": protocol_identity.source_sha256,
                "referent_path": str(referent_path),
                "seed_family_id": arguments.seed_family_id,
                "selection_seed_count": len(protocol.selection.seeds),
                "selection_seed_supplier_call_count": supplier_call_count,
                "selection_seeds_generated_after_source_readiness": True,
                "preseed_chronology_claim": "official-process-attested",
                "source_readiness_path": str(source_readiness_path),
                "source_readiness_sha256": source_readiness_sha256,
                "synthetic_selection_outcomes_generated": False,
                "unseen_seed_cryptographic_proof": False,
                "human_or_external_process_unseen_proof": False,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
