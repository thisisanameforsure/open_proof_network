"""Loaders for the records the merge products are derived from (F03-T1; D-13, F03-Q3, Q5).

Three kinds of file, all schema-checked at the boundary (conventions §4):

- ``nodes/<id>/attempts/*.yaml`` — D-13 postmortems (``postmortem/v1``). A file that does not
  validate is never dropped silently: it is counted as ``invalid`` and named (F03-R7).
- ``nodes/<id>/status/*.yaml`` — curator or adjudication overrides (``node-status/v1``).
- ``targets/<id>/status/*.yaml`` — the target's declaration (``target-status/v1`` or ``v2``).

For the status records the latest wins: ordered by ``date``, then file name.
"""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from opn_gate import paths, schemas

log = logging.getLogger(__name__)

POSTMORTEM_SCHEMA = "postmortem/v1"
NODE_STATUS_SCHEMAS: tuple[str, ...] = ("node-status/v1",)
#: F11-R12: v2 renamed D-9's second rung, and D-34 forbids editing v1 — so both are live,
#: and a record is validated against the version it declares.
TARGET_STATUS_SCHEMAS: tuple[str, ...] = ("target-status/v1", "target-status/v2")
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


def count_attempts(records: int, lean_names: Iterable[str], named: Iterable[str]) -> int:
    """T7: the postmortem files, plus each partial assembly beside them that no valid record
    names in ``artifacts.partial_proof``. An alternate is a proof, not an attempt (D-25 v3.13).
    One rule for the frontier and for ``CONTEXT.json``, which reads through a host (F10-Q7)."""
    partials = {n for n in lean_names if not n.endswith(paths.ALTERNATE_SUFFIX)}
    return records + len(partials - {PurePosixPath(n).name for n in named})


def load_attempts(node_dir: Path) -> AttemptSummary:
    """Aggregate ``attempts/*.yaml``; invalid files count under ``invalid`` and are named.

    T7: the count also takes the partial assemblies filed beside them (D-3, D-12 #5), each an
    attempt on the node. A partial that a valid record names in ``artifacts.partial_proof`` is
    that record's attempt, counted once; an alternate is a proof, not an attempt (D-25 v3.13).
    """
    attempts_dir = node_dir / "attempts"
    if not attempts_dir.is_dir():
        return AttemptSummary()
    files = sorted(p for p in attempts_dir.iterdir() if p.suffix in ATTEMPT_SUFFIXES)
    lean_names = [p.name for p in attempts_dir.iterdir() if p.is_file() and p.suffix == ".lean"]
    named: set[str] = set()
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
        partial = (doc.get("artifacts") or {}).get("partial_proof")
        if isinstance(partial, str):
            named.add(PurePosixPath(partial).name)
    return AttemptSummary(
        count=count_attempts(len(files), lean_names, named),
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


def _latest_record(
    status_dir: Path, accepted: tuple[str, ...], exclude: frozenset[str] = frozenset()
) -> StatusRecord | None:
    """The latest record in ``status_dir``, each validated against the version it declares.

    A record names its own schema and several versions are live at once (D-34), so pinning one
    here would refuse a record the protocol publishes. What is pinned instead is the *set*: a
    record declaring anything outside it is a graph defect and raises, like a malformed one.
    ``exclude`` names files to leave out — the records a pull request adds, when the gate asks
    what the status was before it (status records are append-only, so that is the base's).
    """
    if not status_dir.is_dir():
        return None
    records: list[StatusRecord] = []
    for path in sorted(
        p for p in status_dir.iterdir() if p.suffix in ATTEMPT_SUFFIXES and p.name not in exclude
    ):
        doc = schemas.load_yaml(path)  # a bad status record is a graph defect: raise
        if str(doc.get("schema")) not in accepted:
            msg = f"{path} declares {doc.get('schema')!r}; expected one of {', '.join(accepted)}"
            raise schemas.SchemaError(msg)
        records.append(
            StatusRecord(str(doc["status"]), str(doc["author"]), str(doc["date"]), path, doc)
        )
    if not records:
        return None
    records.sort(key=lambda r: (r.date, r.path.name))
    return records[-1]


def load_node_status(node_dir: Path) -> StatusRecord | None:
    """The node's effective override (F03-R1's last five statuses), or ``None``."""
    return _latest_record(node_dir / "status", NODE_STATUS_SCHEMAS)


def load_target_status(
    target_dir: Path, *, exclude: frozenset[str] = frozenset()
) -> StatusRecord | None:
    """The target's latest declaration (D-33; F03-Q5), or ``None`` — leaving out the files named
    in ``exclude`` (the gate's view of the status before a pull request's own records, F11-T8)."""
    return _latest_record(target_dir / "status", TARGET_STATUS_SCHEMAS, exclude)


def declared_root(target_dir: Path) -> str | None:
    """The root the target's latest declaration names, or ``None`` (F11-R14; F03-Q5).

    The products read the root from the latest record alone, so every tool that writes a later
    target record carries this value forward: a record that left it out would undeclare the
    root, and the first variant or crux after it would stop the products (F08-Q19).
    """
    latest = load_target_status(target_dir)
    root = latest.doc.get("root") if latest is not None else None
    return str(root) if root else None
