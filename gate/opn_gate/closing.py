"""Closable nodes, read from a target's ``graph.json`` (F28-T1; draft decisions v3.41).

A node is *closable* when its proof exists in parts and only their join is missing. Three kinds of
link join a node to the proofs that would prove it, each kernel-checked already:

* a **route** (F27): a merged decomposition of the node, every hole of which is needed (D-12 #5);
* a node's own **circularity claim** (D-12 v3.23), whose exhibit proves that the claiming node
  implies the ancestor it names; the claim alone closes nothing (v3.35), a proof of the claiming
  node with it does;
* at the root, a **resolves variant** (D-30), whose ``Relation.lean`` takes a proof of the variant
  to a proof of the root.

The closable set is the least fixed point of "not proved, not dead, and some link has every input
proved or closable", so a cycle never supports itself (F28-R3). Each closable node names the link
the closing proof would use: the first *ready* one (every input proved) in record order — routes
in merge order, then claims, then variants — else the first satisfiable one (F28-R2).

Nothing here is a status. A closable node is still open until its closing proof merges (v3.41);
this only says which joins exist. Derived where it is read, like F27, so it needs no product field
and no re-pin (F28-Q2).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

# F27's reading of the record: rows by id, and each node's routes with their holes followed through
# revisions and unnamed holes assigned where that is unambiguous. Reused so the two features cannot
# disagree about what a route is.
from opn_gate.routes import DEAD_STATUSES, PROVED, RESOLVES, _hole_nodes, _rows

LinkKind = Literal["route", "claim", "variant"]

#: A circularity claim is named ``<hole>/defects/<file>`` (``graph/v9``'s ``circular``); a node's
#: own claims are the ones under its own id. The others in its list are v3.22's path labels
#: (F28-Q5).
DEFECTS_DIR = "/defects/"


@dataclass(frozen=True)
class Link:
    """What joins a node to the proofs that prove it: a route (``<node>@<k>``, F27), a node's own
    circularity claim (``<hole>/defects/<file>``, D-12 v3.23) or a ``resolves`` variant (D-30)."""

    kind: LinkKind
    id: str
    inputs: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "id": self.id, "inputs": list(self.inputs)}


@dataclass(frozen=True)
class Closable:
    """A node whose proof exists in parts: ``link`` names them; ``ready`` says every input is
    proved, so its closing proof can be written now rather than after another one merges."""

    node: str
    link: Link
    ready: bool

    def as_dict(self) -> dict[str, Any]:
        return {"node": self.node, "link": self.link.as_dict(), "ready": self.ready}


def _status(rows: Mapping[str, Mapping[str, Any]], node_id: str) -> str | None:
    row = rows.get(node_id)
    return None if row is None else str(row.get("status"))


def links(graph: Mapping[str, Any]) -> dict[str, list[Link]]:
    """Every link of every node, in record order: routes in merge order, then claims, then
    variants. A route with an unresolved hole is not a link (F27-R2)."""
    rows = _rows(graph)
    root = str(graph.get("root"))
    out: dict[str, list[Link]] = {node_id: [] for node_id in rows}
    for node_id in rows:
        for k, (_, holes) in enumerate(_hole_nodes(node_id, rows), start=1):
            nodes = [n for _, n in holes]
            if not nodes or any(n is None or n not in rows for n in nodes):
                continue
            # A route through a dead hole stays listed: a dead node is never proved or closable,
            # so the fixed point can never satisfy it, and no separate filter is needed.
            inputs = tuple(dict.fromkeys(str(n) for n in nodes))
            out[node_id].append(Link("route", f"{node_id}@{k}", inputs))
    for node_id, row in rows.items():
        for c in row.get("circular") or []:
            name, ancestor = str(c.get("claim")), str(c.get("ancestor"))
            if name.startswith(node_id + DEFECTS_DIR) and ancestor in out:
                out[ancestor].append(Link("claim", name, (node_id,)))
    if root in out:
        for node_id, row in rows.items():
            if node_id != root and row.get("relation") == RESOLVES:
                out[root].append(Link("variant", node_id, (node_id,)))
    return out


def closable(graph: Mapping[str, Any]) -> tuple[Closable, ...]:
    """Every closable node of the target, in the record's order."""
    rows = _rows(graph)
    by_node = links(graph)
    proved = {k for k in rows if _status(rows, k) == PROVED}
    candidates = [k for k in rows if k not in proved and _status(rows, k) not in DEAD_STATUSES]
    found: set[str] = set()
    changed = True
    while changed:
        changed = False
        for k in candidates:
            if k in found:
                continue
            if any(all(i in proved or i in found for i in lk.inputs) for lk in by_node[k]):
                found.add(k)
                changed = True
    out: list[Closable] = []
    for k in candidates:
        if k not in found:
            continue
        ready = [lk for lk in by_node[k] if all(i in proved for i in lk.inputs)]
        if ready:
            out.append(Closable(k, ready[0], ready=True))
            continue
        able = [lk for lk in by_node[k] if all(i in proved or i in found for i in lk.inputs)]
        out.append(Closable(k, able[0], ready=False))
    return tuple(out)
