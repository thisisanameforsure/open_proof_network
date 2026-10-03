"""Proposed for (F18-R8; D-14 v3.26, D-3): which node of its target a statement was proposed for.

``nodes/<id>/proposed-for/<timestamp>-<pseudonym>.yaml`` is append-only and written by the node's
proposer (its ``META.yaml`` ``provenance.author``) or a listed curator; the gate's rule is
``modes.check_proposed_for``. The latest record by file name is the one shown, since the name
leads with its timestamp, as every other append-only record's does (D-13).

It is a pointer, not a dependency: no status, frontier entry or dependency is derived from it.
The products read it as ``NodeFacts.proposed_for`` and nothing else reads it.

This module reads the tree and nothing above it, so ``graph`` can import it; following a pointer
through a revision is ``graph``'s (``graph.current_id``).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from opn_gate import schemas

log = logging.getLogger(__name__)

SCHEMA = "proposed-for/v1"
DIR = "proposed-for"
SUFFIXES: tuple[str, ...] = (".yaml", ".yml")
#: What ``for`` may be: a node id, as the schema's pattern says.
NODE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def file_name(stamp: str, pseudonym: str) -> str:
    """``<timestamp>-<pseudonym>.yaml``, the stamp as every record carries it
    (``20261003T120000Z``)."""
    return f"{stamp}-{pseudonym}.yaml"


def document(for_node: str, author: str, date: str, note: str | None = None) -> dict[str, Any]:
    """A ``proposed-for/v1`` record, validated: ``date`` is a day (``2026-10-03``)."""
    return schemas.validate(
        {"schema": SCHEMA, "for": for_node, "author": author, "date": date, "note": note},
        SCHEMA,
    )


def latest(node_dir: Path) -> dict[str, Any] | None:
    """The node's latest valid record, by file name, or ``None``.

    A file that does not read as a valid record is logged and passed over: the records are
    appends, and one bad file must never decide whether the graph has products (2026-09-17).
    The gate refuses such a file at merge, so this only meets one a pin older than the rule let
    through."""
    directory = node_dir / DIR
    if not directory.is_dir():
        return None
    for path in sorted((p for p in directory.iterdir() if p.suffix in SUFFIXES), reverse=True):
        try:
            return schemas.load_yaml(path, SCHEMA)
        except schemas.SchemaError as exc:
            log.warning(
                "%s: a proposed-for record that does not validate is passed over: %s", path, exc
            )
    return None
