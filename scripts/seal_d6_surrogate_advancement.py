#!/usr/bin/env python3
"""Publish a commit-pending D6 candidate from one committed D0--D5 terminal."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from spirallens.qualification.advancement import (
    publish_scope_limited_d6_decision,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Strictly reload one committed official D0-D5 terminal, bind its "
            "Cartesian-surrogate scope, and publish one commit-pending D6 "
            "decision bundle without overwrite. A clean tracked descendant "
            "reload is still required; D7 and D8 remain not_run."
        )
    )
    parser.add_argument("--launch-descriptor", required=True)
    parser.add_argument("--launch-descriptor-source-sha256", required=True)
    parser.add_argument("--launch-descriptor-canonical-sha256", required=True)
    parser.add_argument("--terminal-manifest-sha256", required=True)
    parser.add_argument("--terminal-result-sha256", required=True)
    parser.add_argument("--terminal-consumption-sha256", required=True)
    parser.add_argument("--admission-spec-id", required=True)
    parser.add_argument("--decision-id", required=True)
    parser.add_argument("--decision-output", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    loaded = publish_scope_limited_d6_decision(
        arguments.decision_output,
        decision_id=arguments.decision_id,
        admission_spec_id=arguments.admission_spec_id,
        launch_descriptor=Path(arguments.launch_descriptor).resolve(),
        launch_descriptor_source_sha256=(
            arguments.launch_descriptor_source_sha256
        ),
        launch_descriptor_canonical_sha256=(
            arguments.launch_descriptor_canonical_sha256
        ),
        terminal_manifest_sha256=arguments.terminal_manifest_sha256,
        terminal_result_sha256=arguments.terminal_result_sha256,
        terminal_consumption_sha256=(
            arguments.terminal_consumption_sha256
        ),
    )
    decision = loaded.decision
    print(
        json.dumps(
            {
                "admission_spec_id": (
                    decision.confirmation_admission_spec.admission_spec_id
                ),
                "admission_spec_sha256": (
                    decision.confirmation_admission_spec.canonical_sha256
                ),
                "decision_path": str(loaded.identity.path),
                "decision_sha256": loaded.identity.canonical_sha256,
                "decision_source_commit": decision.decision_source_commit,
                "parent_directory_fsync_verified": (
                    loaded.parent_directory_fsync_verified
                ),
                "committed_artifact_verified": False,
                "artifact_commit_required": True,
                "d6_state": decision.d6_state,
                "d6_scope": decision.d6_scope,
                "d7_state": decision.d7_state,
                "d8_state": decision.d8_state,
                "d6_d8_advanced": False,
                "synthetic_qualified": False,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
