"""Held-out semantic contrast records for post-discovery evaluation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MinimalPair:
    pair_id: str
    left_text: str
    right_text: str
    contrast_label: str
    split: str = "held_out"

    def __post_init__(self) -> None:
        if not self.pair_id or not self.left_text or not self.right_text:
            raise ValueError("pair_id and both texts must not be empty")
        if self.left_text == self.right_text:
            raise ValueError("minimal-pair texts must differ")
        if not self.contrast_label:
            raise ValueError("contrast_label must not be empty")
        if self.split not in {"held_out", "calibration"}:
            raise ValueError("minimal pairs must be held_out or calibration")
