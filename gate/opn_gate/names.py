"""Display names a contributor chooses to be shown by (F25-R6; D-3, D-19 v3.37).

``names/<pseudonym>.yaml`` at the graph root (``display-name/v1``) is one file per pseudonym,
written only by the holder of the pseudonym through the service and signed by the approval key;
the gate admits it (``modes.check_display_name``). A later record replaces the file and a record
whose ``name`` is null withdraws the name; the history is the trail (F25-Q6). This module is the
one reader: ``display_name`` is what a registration's authors list shows in place of a pseudonym
(F25-T7's ``palomar.authors``), and nothing on the site reads it in this version. A file that does
not validate, or is not named for the pseudonym it carries, is passed over with a warning: the
gate refused it at the merge, and one bad file must never decide what the graph says.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from opn_gate import paths, schemas

SCHEMA = "display-name/v1"
DIR = paths.NAMES_DIR
SUFFIXES = paths.YAML_SUFFIXES

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Record:
    """One display-name record as filed."""

    path: Path
    doc: dict[str, Any]

    @property
    def pseudonym(self) -> str:
        return str(self.doc["pseudonym"])

    @property
    def name(self) -> str | None:
        found = self.doc.get("name")
        return found if isinstance(found, str) else None

    @property
    def link(self) -> str | None:
        found = self.doc.get("link")
        return found if isinstance(found, str) else None


def directory(graph_root: Path) -> Path:
    return graph_root / DIR


def path_for(graph_root: Path, pseudonym: str) -> Path:
    """Where the pseudonym's record lives, whether or not one has been written."""
    return directory(graph_root) / f"{pseudonym}.yaml"


def load(graph_root: Path) -> list[Record]:
    """Every valid record under ``names/``, by file name."""
    found: list[Record] = []
    where = directory(graph_root)
    if not where.is_dir():
        return found
    for path in sorted(p for p in where.iterdir() if p.suffix in SUFFIXES):
        try:
            doc = schemas.load_yaml(path)
        except schemas.SchemaError as exc:
            log.warning("%s: a display-name record does not read, passed over: %s", path, exc)
            continue
        bad = not isinstance(doc, dict) or doc.get("schema") != SCHEMA
        if bad or schemas.violations(doc, SCHEMA):
            log.warning("%s: a display-name record that does not validate is passed over", path)
            continue
        if path.stem != doc.get("pseudonym"):
            log.warning("%s: a record not named for its own pseudonym is passed over", path)
            continue
        found.append(Record(path, doc))
    return found


def latest(graph_root: Path) -> dict[str, Record]:
    """The record standing for each pseudonym: one file each, so the file is the latest."""
    return {rec.pseudonym: rec for rec in load(graph_root)}


def display_name(graph_root: Path, pseudonym: str) -> str | None:
    """The name ``pseudonym`` asked to be shown by, or ``None``: no record, or the latest record
    withdrew it (``name: null``)."""
    rec = latest(graph_root).get(pseudonym)
    return rec.name if rec is not None else None
