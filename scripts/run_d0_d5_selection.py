#!/usr/bin/env python3
"""Run one frozen D0--D5 selection attempt through its terminal transaction."""

from __future__ import annotations

import argparse
import json

from spirallens.qualification import (
    load_prepared_selection_launch,
    load_terminal_selection_consumption,
    run_and_publish_calibration_selection,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Load one exact preclaimed launch and execute its frozen D0-D5 "
            "selection family. "
            "After execution start, every ordinary outcome is terminal."
        )
    )
    parser.add_argument("--launch-descriptor", required=True)
    parser.add_argument("--launch-descriptor-source-sha256", required=True)
    parser.add_argument("--launch-descriptor-canonical-sha256", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    launch = load_prepared_selection_launch(
        arguments.launch_descriptor,
        expected_descriptor_source_sha256=(arguments.launch_descriptor_source_sha256),
        expected_descriptor_canonical_sha256=(
            arguments.launch_descriptor_canonical_sha256
        ),
    )
    result, consumption, terminal_identity = run_and_publish_calibration_selection(
        launch.loaded_protocol,
        source_binding_receipt=launch.source_binding_receipt,
        selection_freeze_artifact=launch.selection_freeze_artifact,
        attempt_claim=launch.attempt_claim,
        attempt_store_directory=launch.descriptor.attempt_store_path,
        launch_authorization=launch.launch_authorization,
    )
    loaded_consumption, loaded_terminal = load_terminal_selection_consumption(
        terminal_identity.path,
        expected_manifest_sha256=terminal_identity.manifest_sha256,
        expected_terminal_artifact_sha256=(terminal_identity.terminal_artifact_sha256),
        expected_consumption_sha256=terminal_identity.consumption_sha256,
        freeze=launch.selection_freeze_artifact,
        attempt_claim=launch.attempt_claim,
        loaded_protocol=launch.loaded_protocol,
        launch_authorization=launch.launch_authorization,
        repository_root=launch.descriptor.repository_root,
        registry_path=launch.descriptor.registry_path,
        referent_path=launch.descriptor.referent_path,
    )
    if loaded_consumption != consumption or loaded_terminal != result:
        raise RuntimeError(
            "terminal transaction differs from the official in-process result"
        )
    print(
        json.dumps(
            {
                "claim_canonical_sha256": (launch.attempt_claim.canonical_sha256),
                "claim_path": launch.descriptor.attempt_claim_path,
                "consumption_canonical_sha256": (consumption.canonical_sha256),
                "gate_results": [
                    {
                        "gate_id": gate.gate_id.value,
                        "reason_codes": list(gate.reason_codes),
                        "state": gate.state.value,
                    }
                    for gate in result.gate_results
                ],
                "localized_core_loop_join_established": (
                    result.localized_core_loop_join_established
                ),
                "p0_winner_selected": result.p0_winner_selected,
                "representation_d2_d5_qualified": (
                    result.representation_d2_d5_qualified
                ),
                "result_canonical_sha256": result.canonical_sha256,
                "result_id": result.result_id,
                "synthetic_qualified": result.synthetic_qualified,
                "terminal_round_trip_verified": True,
                "terminal_consumption_sha256": (terminal_identity.consumption_sha256),
                "terminal_manifest_sha256": (terminal_identity.manifest_sha256),
                "terminal_path": str(terminal_identity.path),
                "terminal_result_sha256": (terminal_identity.terminal_artifact_sha256),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
