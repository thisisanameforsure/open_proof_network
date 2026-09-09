"""Loaders for the records the merge products are derived from (F03-T1; D-13, F03-Q3, Q5).

Three kinds of file, all schema-checked at the boundary (conventions §4):

- ``nodes/<id>/attempts/*.yaml`` — D-13 postmortems (``postmortem/v1``). A file that does not
  validate is never dropped silently: it is counted as ``invalid`` and named (F03-R7).
- ``nodes/<id>/status/*.yaml`` — curator or adjudication overrides (``node-status/v1``).
- ``targets/<id>/status/*.yaml`` — the target's declaration (``target-status/v1``).

For the status records the latest wins: ordered by ``date``, then file name.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from opn_gate import schemas

log = logging.getLogger(__name__)

POSTMORTEM_SCHEMA = "postmortem/v1"
NODE_STATUS_SCHEMA = "node-status/v1"
TARGET_STATUS_SCHEMA = "target-status/v1"
INVALID = "invalid"
ATTEMPT_SUFFIXES: tuple[str, ...] = (".yaml", ".yml")


@dataclass(frozen=True)
class AttemptSummary:
    """What the frontier publishes about a node's attempts (F03-R5, R7; D-25)."""

    count: int = 0
    refuted_route_classes: tuple[str, ...] = ()
    failure_class_histogram: dict[str, int] = field(default_factory=dict)
    invalid_files: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "attempts": self.count,
            "refuted_route_classes": list(self.refuted_route_classes),
            "failure_class_histogram": dict(sorted(self.failure_class_histogram.items())),
        }


def load_attempts(node_dir: Path) -> AttemptSummary:
    """Aggregate ``attempts/*.yaml``; invalid files count under ``invalid`` and are named."""
    attempts_dir = node_dir / "attempts"
    if not attempts_dir.is_dir():
        return AttemptSummary()
    files = sorted(p for p in attempts_dir.iterdir() if p.suffix in ATTEMPT_SUFFIXES)
    refuted: set[str] = set()
    histogram: Counter[str] = Counter()
    invalid: list[str] = []
    for path in files:
        try:
            doc = schemas.load_yaml(path, POSTMORTEM_SCHEMA)
        except schemas.SchemaError as exc:
            log.warning("attempt record %s is invalid and counted as such: %s", path, exc)
            invalid.append(path.name)
            histogram[INVALID] += 1
            continue
        if doc["outcome"] == "refuted-route":
            refuted.add(str(doc["route_class"]))
        failure_class = doc.get("failure_class")
        if failure_class is not None:
            histogram[str(failure_class)] += 1
    return AttemptSummary(
        count=len(files),
        refuted_route_classes=tuple(sorted(refuted)),
        failure_class_histogram=dict(histogram),
        invalid_files=tuple(invalid),
    )


@dataclass(frozen=True)
class StatusRecord:
    """A status override, with where it came from."""

    status: str
    author: str
    date: str
    path: Path
    doc: dict[str, Any]


def _latest_record(status_dir: Path, schema_id: str) -> StatusRecord | None:
    if not status_dir.is_dir():
        return None
    records: list[StatusRecord] = []
    for path in sorted(p for p in status_dir.iterdir() if p.suffix in ATTEMPT_SUFFIXES):
        doc = schemas.load_yaml(path, schema_id)  # a bad status record is a graph defect: raise
        records.append(
            StatusRecord(str(doc["status"]), str(doc["author"]), str(doc["date"]), path, doc)
        )
    if not records:
        return None
    records.sort(key=lambda r: (r.date, r.path.name))
    return records[-1]


def load_node_status(node_dir: Path) -> StatusRecord | None:
    """The node's effective override (F03-R1's last five statuses), or ``None``."""
    return _latest_record(node_dir / "status", NODE_STATUS_SCHEMA)


def load_target_status(target_dir: Path) -> StatusRecord | None:
    """The target's latest declaration (D-33; F03-Q5), or ``None``."""
    return _latest_record(target_dir / "status", TARGET_STATUS_SCHEMA)
