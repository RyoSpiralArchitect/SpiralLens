"""Semantic annotations live in a sidecar, never in the discovery ledger."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any


SEMANTIC_ANNOTATION_SCHEMA_VERSION = "spirallens.semantic-annotation.v0.1"


@dataclass(frozen=True)
class SemanticAnnotation:
    """A downstream interpretation attached by stable candidate ID."""

    candidate_id: str
    annotation_source: str
    split: str
    labels: Mapping[str, Any]
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.candidate_id.startswith("cand_"):
            raise ValueError("candidate_id must be a structural candidate identifier")
        if not self.annotation_source:
            raise ValueError("annotation_source must not be empty")
        if self.split not in {"held_out", "exploratory", "calibration"}:
            raise ValueError("split must be held_out, exploratory, or calibration")
        if not self.labels:
            raise ValueError("labels must not be empty")

    def to_record(self) -> dict[str, Any]:
        return {
            "schema_version": SEMANTIC_ANNOTATION_SCHEMA_VERSION,
            "record_type": "semantic_annotation",
            **asdict(self),
            "evidence_refs": list(self.evidence_refs),
            "discovery_ledger_mutated": False,
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_semantic_annotations(
    annotations: Iterable[SemanticAnnotation],
    output_path: str | Path,
    *,
    discovery_ledger_sha256: str,
) -> int:
    """Atomically write a provenance-bound annotation sidecar."""

    if len(discovery_ledger_sha256) != 64:
        raise ValueError("discovery_ledger_sha256 must be a SHA-256 hex digest")
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp-{os.getpid()}")
    count = 0
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            header = {
                "schema_version": SEMANTIC_ANNOTATION_SCHEMA_VERSION,
                "record_type": "annotation_header",
                "created_at": _utc_now(),
                "discovery_ledger_sha256": discovery_ledger_sha256,
                "semantic_annotations_were_not_used_for_discovery": True,
            }
            handle.write(json.dumps(header, sort_keys=True, allow_nan=False) + "\n")
            for annotation in annotations:
                handle.write(
                    json.dumps(
                        annotation.to_record(),
                        sort_keys=True,
                        allow_nan=False,
                    )
                    + "\n"
                )
                count += 1
            footer = {
                "schema_version": SEMANTIC_ANNOTATION_SCHEMA_VERSION,
                "record_type": "annotation_footer",
                "status": "complete",
                "annotation_count": count,
            }
            handle.write(json.dumps(footer, sort_keys=True, allow_nan=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return count


def read_semantic_annotations(path: str | Path) -> Iterator[SemanticAnnotation]:
    """Read annotation records and fail if the sidecar lacks a completion footer."""

    complete = False
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid JSON annotation at line {line_number}") from error
            if record.get("record_type") == "semantic_annotation":
                yield SemanticAnnotation(
                    candidate_id=record["candidate_id"],
                    annotation_source=record["annotation_source"],
                    split=record["split"],
                    labels=record["labels"],
                    evidence_refs=tuple(record.get("evidence_refs", ())),
                )
            elif record.get("record_type") == "annotation_footer":
                complete = record.get("status") == "complete"
    if not complete:
        raise ValueError("semantic annotation sidecar is incomplete")
