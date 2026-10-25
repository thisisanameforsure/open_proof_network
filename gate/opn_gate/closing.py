"""Closable nodes, read from a target's ``graph.json`` (F28-T1; draft decisions v3.41).

A node is *closable* when its proof exists in parts and only their join is missing. Three kinds of
link joined a node to the proofs that would prove it; two remain since D-12 v3.42 retired the
circularity claim (F08-T42), each kernel-checked already:

* a **route** (F27): a merged decomposition of the node, every hole of which is needed (D-12 #5);
* at the root, a **resolves variant** (D-30), whose ``Relation.lean`` takes a proof of the variant
  to a proof of the root — or (v3.46) a **refutes variant**, whose relation takes it to a proof
  of the root's negation, so the link's ``verdict`` is ``refuted`` (F28-T10).

The closable set is the least fixed point of "not proved, not dead, and some link has every input
proved or closable", so a cycle never supports itself (F28-R3). Each closable node names the link
the closing proof would use: the first *ready* one (every input proved) in record order — routes
in merge order, then variants — else the first satisfiable one (F28-R2).

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
from opn_gate import closure
from opn_gate.routes import (
    DEAD_STATUSES,
    PROVED,
    REFUTES,
    RESOLVES,
    _hole_nodes,
    _retired,
    _rows,
    _shelved,
)

LinkKind = Literal["route", "variant"]

#: F08-T42 (D-12 v3.42) retired the circularity claim, and with it F28's claim link: a proved hole
#: closes what it was cut from through a route (its parent's assembly), never through an exhibit.


@dataclass(frozen=True)
class Link:
    """What joins a node to the proofs that prove it: a route (``<node>@<k>``, F27) or a
    ``resolves`` variant (D-30)."""

    kind: LinkKind
    id: str
    inputs: tuple[str, ...]
    #: F28-T10 (D-12 v3.46): what joining this link yields — the node's theorem (``proved``), or
    #: through a ``refutes`` variant its negation (``refuted``). Not in ``as_dict``: that shape is
    #: published (the MCP's ``list_sufficient_sets`` result, closed) and the verdict is the
    #: record's (``closure.json``) and the row's status; the closing report carries it.
    verdict: str = closure.VERDICT_PROVED

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
    """Every link of every node, in record order: routes in merge order, then variants. A route
    with an unresolved hole is not a link (F27-R2)."""
    rows = _rows(graph)
    root = str(graph.get("root"))
    out: dict[str, list[Link]] = {node_id: [] for node_id in rows}
    for node_id in rows:
        for k, (_, holes) in enumerate(_hole_nodes(node_id, rows), start=1):
            nodes = [n for _, n in holes]
            if not nodes or any(n is None or n not in rows for n in nodes):
                continue
            # A route through a dead hole stays listed: a dead node is never proved or closable,
            # so the fixed point can never satisfy it, and no separate filter is needed. A
            # retired route is not a link (F31-R4, D-14 v3.47): its holes may all be proved, and
            # a closing proof would join a decomposition a steward or curator retired.
            if _retired(node_id, nodes, rows):
                continue
            inputs = tuple(dict.fromkeys(str(n) for n in nodes))
            out[node_id].append(Link("route", f"{node_id}@{k}", inputs))
    if root in out:
        for node_id, row in rows.items():
            if node_id == root:
                continue
            # D-30: a ``resolves`` variant implies the root; a ``refutes`` one (v3.46) implies its
            # negation, and joining it yields the root *refuted* (F28-T10).
            if row.get("relation") == RESOLVES:
                out[root].append(Link("variant", node_id, (node_id,)))
            elif row.get("relation") == REFUTES:
                out[root].append(
                    Link("variant", node_id, (node_id,), verdict=closure.VERDICT_REFUTED)
                )
    return out


def closable(graph: Mapping[str, Any]) -> tuple[Closable, ...]:
    """Every closable node of the target, in the record's order."""
    rows = _rows(graph)
    by_node = links(graph)
    proved = {k for k in rows if _status(rows, k) == PROVED}
    # F31-R4: a shelved node is never closable, whatever its links.
    candidates = [
        k
        for k in rows
        if k not in proved and _status(rows, k) not in DEAD_STATUSES and _shelved(rows[k]) is None
    ]
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
