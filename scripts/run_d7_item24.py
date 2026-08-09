#!/usr/bin/env python3
"""Run the one fixed D7 item-24 fused invocation.

This repository-local launcher has no caller-configurable scientific input.
Its absolute argv[0], working directory, interpreter identity, and sole
producer are frozen into the committed launch descriptor before it is used.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER_PATH = Path(__file__).resolve()

# Use the reviewed checkout source while leaving installed-distribution
# enumeration to the separately frozen runtime.
_BOOTSTRAP_SYS_PATH = tuple(sys.path)
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from spirallens.qualification import confirmation_fused_start as fused_start  # noqa: E402
from spirallens.qualification import confirmation_official_execution as official  # noqa: E402

sys.path[:] = _BOOTSTRAP_SYS_PATH
if Path(official.__file__).resolve() != (
    REPOSITORY_ROOT / "src/spirallens/qualification/confirmation_official_execution.py"
):
    raise RuntimeError("item-24 official producer import origin differs")


def _require_exact_process_envelope() -> None:
    if Path(os.path.realpath(os.getcwd())) != REPOSITORY_ROOT:
        raise RuntimeError("item-24 launcher requires the exact repository cwd")
    if sys.argv != [str(LAUNCHER_PATH)]:
        raise RuntimeError("item-24 launcher accepts no arguments or alternate argv[0]")


def main() -> int:
    _require_exact_process_envelope()
    terminal = fused_start.run_d7_fused_verify_start_and_terminal_no_replace(
        REPOSITORY_ROOT / official.D7_OFFICIAL_FUSED_DESCRIPTOR_REPOSITORY_PATH,
        official.produce_d7_official_result,
    )
    print(
        json.dumps(
            {
                "atomic_no_replace": terminal.atomic_no_replace,
                "created_by_call": terminal.created_by_call,
                "parent_directory_fsync_proved": (
                    terminal.parent_directory_fsync_proved
                ),
                "path": str(terminal.path),
                "terminal_artifact_kind": terminal.terminal_artifact_kind.value,
                "terminal_artifact_sha256": terminal.terminal_artifact_sha256,
                "terminal_consumption_sha256": (terminal.terminal_consumption_sha256),
                "terminal_manifest_sha256": terminal.terminal_manifest_sha256,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
