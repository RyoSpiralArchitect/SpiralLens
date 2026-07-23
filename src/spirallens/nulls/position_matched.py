"""Build metadata-matched controls without semantic labels."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any


def matched_index_pairs(
    records: Sequence[Mapping[str, Any]],
    *,
    match_fields: Sequence[str],
    contrast_field: str | None = None,
) -> list[tuple[int, int]]:
    """Return deterministic pairs equal on controls and optionally differing on one field."""

    if not match_fields:
        raise ValueError("match_fields must not be empty")
    groups: dict[tuple[Any, ...], list[int]] = defaultdict(list)
    for index, record in enumerate(records):
        try:
            key = tuple(record[field] for field in match_fields)
        except KeyError as error:
            raise ValueError(f"record {index} is missing match field {error.args[0]}") from error
        groups[key].append(index)

    pairs: list[tuple[int, int]] = []
    for key in sorted(groups, key=repr):
        indices = groups[key]
        for offset, left in enumerate(indices):
            for right in indices[offset + 1 :]:
                if contrast_field is not None:
                    if contrast_field not in records[left] or contrast_field not in records[right]:
                        raise ValueError(f"records are missing contrast field {contrast_field}")
                    if records[left][contrast_field] == records[right][contrast_field]:
                        continue
                pairs.append((left, right))
    return pairs
