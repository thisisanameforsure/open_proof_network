"""Registrations of a target in a public registry (F25-R5, R7; D-3, D-10 v3.37).

``targets/<id>/registrations/<date>-<n>.yaml`` records a submission to, or a registration in,
Palomar, written by a curator or a listed steward of the target. Derived, never rewritten
(F08-T10's principle): the latest record per registry id is the one read, a record that has no
id yet is keyed by the wrapper commit it submitted, and a later record whose status is
``withdrawn`` sets the registration aside. The products publish the derivation on the target's
row (``targets-index/v10``) and document (``graph/v7``); nothing here is a verdict.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from opn_gate import schemas

SCHEMA = "registration/v1"
DIR = "registrations"
SUFFIXES = (".yaml", ".yml")
STATUSES: tuple[str, ...] = (
    "submitted",
    "registered",
    "revision_required",
    "rejected",
    "withdrawn",
)
WITHDRAWN = "withdrawn"
#: What the products publish per registration (F25-R7).
PUBLISHED_FIELDS: tuple[str, ...] = ("registry", "registry_id", "version", "status", "url")

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Record:
    """One registration record as filed."""

    path: Path
    doc: dict[str, Any]

    @property
    def key(self) -> str:
        """What a later record supersedes: the registry id, or the wrapper commit before one."""
        rid = self.doc.get("registry_id")
        if isinstance(rid, str):
            return f"{self.doc['registry']}:{rid}"
        return f"{self.doc['registry']}:pending:{self.doc['wrapper']['commit']}"

    @property
    def date(self) -> str:
        return str(self.doc["date"])


def directory(target_dir: Path) -> Path:
    return target_dir / DIR


def load(target_dir: Path) -> list[Record]:
    """Every record under the target's ``registrations/``, oldest first (by ``date``, then
    name). A file that does not validate is logged and passed over: the gate refused it at merge,
    and one bad file must never decide what the graph says (2026-09-17)."""
    found: list[Record] = []
    where = directory(target_dir)
    if not where.is_dir():
        return found
    for path in sorted(p for p in where.iterdir() if p.suffix in SUFFIXES):
        try:
            doc = schemas.load_yaml(path)
        except schemas.SchemaError as exc:
            log.warning("%s: a registration record does not read, passed over: %s", path, exc)
            continue
        bad = not isinstance(doc, dict) or doc.get("schema") != SCHEMA
        if bad or schemas.violations(doc, SCHEMA):
            log.warning("%s: a registration record that does not validate is passed over", path)
            continue
        found.append(Record(path, doc))
    found.sort(key=lambda r: (r.date, r.path.name))
    return found


def latest(records: list[Record]) -> dict[str, Record]:
    """The latest record per key, in first-seen order of key (``load`` orders by date)."""
    out: dict[str, Record] = {}
    for rec in records:
        out[rec.key] = rec
    return out


def derive(target_dir: Path) -> list[dict[str, Any]]:
    """F25-R7: what the products publish — the latest record per registry id, withdrawn ones set
    aside, each reduced to :data:`PUBLISHED_FIELDS`, in the order the registrations were first
    filed."""
    out: list[dict[str, Any]] = []
    for rec in latest(load(target_dir)).values():
        if rec.doc.get("status") == WITHDRAWN:
            continue
        out.append({k: rec.doc.get(k) for k in PUBLISHED_FIELDS})
    return out
