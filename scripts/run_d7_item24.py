#!/usr/bin/env python3
"""Fail closed for the superseded D7 v0.1 item-24 launch identity.

Review on 2026-08-09 found that item 23 ran without the chronology bindings
required by the 2026-07-29 Fundamental Frame.  The later descriptor does not
retroactively cure that deviation.  A different versioned successor must own
any future official invocation.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER_PATH = Path(__file__).resolve()
CHRONOLOGY_BLOCK_ID = "d7-v0-1-item23-chronology-deviation-2026-08-09"


def _require_exact_process_envelope() -> None:
    if Path(os.path.realpath(os.getcwd())) != REPOSITORY_ROOT:
        raise RuntimeError("item-24 launcher requires the exact repository cwd")
    if sys.argv != [str(LAUNCHER_PATH)]:
        raise RuntimeError("item-24 launcher accepts no arguments or alternate argv[0]")


def main() -> int:
    _require_exact_process_envelope()
    raise RuntimeError(
        "D7 v0.1 item-24 official invocation is blocked by chronology deviation: "
        f"{CHRONOLOGY_BLOCK_ID}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
