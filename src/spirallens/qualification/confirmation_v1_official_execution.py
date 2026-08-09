"""Blocked official-callable coordinate for the fresh D7 v1 successor.

The strict-successor route declares the callable coordinate implemented by
this module, but the currently frozen v1 protocol ends at a pre-start attempt
reservation and a post-D6 descriptive result.  It defines neither a launch
authority record nor an execution-start transition.  Consequently the
coordinate exists for source review and later C1 closure, while every call
fails before seed, supplier, model, subject, persistence, or scientific code
can be reached.

Importing this module performs no I/O.  This is fresh v1 source and deliberately
does not reuse the superseded v0.1 official-execution or fused-start machinery.
"""

from __future__ import annotations

from typing import NoReturn

from .common import QualificationContractError

__all__: tuple[str, ...] = ()


D7_V1_OFFICIAL_CALLABLE = (
    "spirallens.qualification.confirmation_v1_official_execution:"
    "produce_d7_v1_official_result"
)
D7_V1_OFFICIAL_PRODUCER_MODULE = (
    "spirallens.qualification.confirmation_v1_official_execution"
)
D7_V1_OFFICIAL_PRODUCER_QUALNAME = "produce_d7_v1_official_result"
D7_V1_EXECUTION_BLOCK_ID = "d7-v1-launch-authority-and-start-contract-absent"


def produce_d7_v1_official_result() -> NoReturn:
    """Refuse official execution until a reviewed v1 start contract exists."""

    raise QualificationContractError(
        "D7 v1 official execution is blocked: the frozen pre-item-23 contract "
        "contains only a non-authorizing attempt reservation and defines no "
        "launch-authority or execution-start transition "
        f"({D7_V1_EXECUTION_BLOCK_ID})"
    )
