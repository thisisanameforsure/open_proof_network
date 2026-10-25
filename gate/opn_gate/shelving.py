"""Shelving (F31; D-14, D-25 v3.47): a steward's or curator's judgment that a statement, or one
merged decomposition of it, does not serve the root.

``nodes/<id>/shelving/<timestamp>-<login>.yaml`` (``shelving/v1``) says ``shelved`` or
``unshelved``, with ``scope: node`` (the statement and every hole child beneath it) or
``scope: route`` (one merged decomposition, named by its partial's file, and its holes), and a
cause. Always signed: by the approval key through the service for a signed-in login, or by the
signer's own key by hand. The gate decides which records count (``modes.check_shelving_record``
refuses the rest before merge: an unlisted signer, the root, a statement a merged proof uses, a
route that is not the node's); the products re-decide from the tree with the same rule.

Not a status: ``status`` is derived without it. :func:`derive` is the products' rule (F31-R2),
computed once, top-down over *arrivals* in dependency order — never as a fixed point and never
from the ``--h`` id prefix. Derive, never rewrite (F08-T10): nothing here writes; removing the
records restores the products byte for byte. Earns nothing; ranks nothing (D-25 v3.47).
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any

from opn_gate import closure, records, schemas, signed
from opn_gate.signer import Signer

if TYPE_CHECKING:
    from opn_gate.graph import NodeFacts

log = logging.getLogger(__name__)

SCHEMA = "shelving/v1"
#: Every version a record may carry (D-34).
SCHEMAS: tuple[str, ...] = (SCHEMA,)
DIR = "shelving"
SUFFIXES: tuple[str, ...] = (".yaml", ".yml")
SHELVED = "shelved"
UNSHELVED = "unshelved"
ACTIONS: tuple[str, ...] = (SHELVED, UNSHELVED)
SCOPE_NODE = "node"
SCOPE_ROUTE = "route"
SCOPES: tuple[str, ...] = (SCOPE_NODE, SCOPE_ROUTE)


@dataclass(frozen=True)
class Record:
    """One shelving record as written, validated against one of ``SCHEMAS``."""

    name: str  # the file name under shelving/
    doc: dict[str, Any]
    #: The node whose directory holds the record — the node it sits on, which a revision with
    #: the statement unchanged may read as its own (F31-Q8); ``record`` is relative to it.
    holder: str | None = None

    @property
    def path(self) -> str:
        """The record relative to its node, the shape the products publish."""
        return f"{DIR}/{self.name}"

    @property
    def node(self) -> str:
        return str(self.doc["node"])

    @property
    def contributor(self) -> str:
        return str(self.doc["contributor"])

    @property
    def date(self) -> str:
        return str(self.doc["date"])

    @property
    def action(self) -> str:
        return str(self.doc["action"])

    @property
    def scope(self) -> str:
        return str(self.doc["scope"])

    @property
    def route(self) -> str | None:
        named = self.doc.get("route")
        return str(named) if named else None

    @property
    def cause(self) -> str:
        return str(self.doc["cause"])

    @property
    def shelves(self) -> bool:
        return self.action == SHELVED

    def sort_key(self) -> tuple[str, str]:
        """``(date, file name)``: the login in the name makes the order total."""
        return (self.date, self.name)

    def published(self, *, via: str | None = None) -> dict[str, Any]:
        """The object ``graph/v15`` publishes for a node this record reaches; ``via`` is the
        node whose record it is — its holder unless the caller says otherwise."""
        via = via if via is not None else self.holder
        return {
            "cause": self.cause,
            "by": self.contributor,
            "date": self.date[:10],
            "record": self.path,
            "scope": self.scope,
            "via": via,
        }


def load(node_dir: Path, *, exclude: frozenset[str] = frozenset()) -> list[Record]:
    """Every record under the node's ``shelving/``, oldest first (by ``date``, then name),
    leaving out the files a curator's withdrawal names (``records.withdrawn_names``) and those
    in ``exclude`` (the records a pull request adds, when the gate asks what stood before it). A
    file that does not validate against its own version is logged and passed over: the gate
    refused it at merge, and one bad file must never decide what the graph says (2026-09-17)."""
    directory = node_dir / DIR
    if not directory.is_dir():
        return []
    gone = records.withdrawn_names(node_dir, DIR) | exclude
    found: list[Record] = []
    for path in sorted(p for p in directory.iterdir() if p.suffix in SUFFIXES):
        if path.name in gone:
            continue
        try:
            doc = schemas.load_yaml(path)
        except schemas.SchemaError as exc:
            log.warning("%s: a shelving record that does not read is passed over: %s", path, exc)
            continue
        version = doc.get("schema")
        if version not in SCHEMAS or schemas.violations(doc, str(version)):
            log.warning("%s: a shelving record that does not validate is passed over", path)
            continue
        found.append(Record(path.name, doc, holder=node_dir.name))
    found.sort(key=Record.sort_key)
    return found


@dataclass(frozen=True)
class Standing:
    """What a node's own records say, latest per key (F31-Q, the gate agent's reading of rule
    4): ``node`` is the latest ``scope: node`` record, ``routes`` the latest record per retired
    route's path. A retirement never shelves the node it sits on and a later retirement of a
    second route does not lift the first; an ``unshelved`` record lifts the key it names."""

    node: Record | None
    routes: dict[str, Record]

    @property
    def shelved(self) -> Record | None:
        return self.node if self.node is not None and self.node.shelves else None

    def retired(self, route: str) -> Record | None:
        found = self.routes.get(route)
        return found if found is not None and found.shelves else None


def standing(found: list[Record]) -> Standing:
    """The latest record per key of ``found`` (oldest first, as :func:`load` returns them)."""
    node: Record | None = None
    routes: dict[str, Record] = {}
    for record in found:
        if record.scope == SCOPE_ROUTE and record.route is not None:
            routes[record.route] = record
        else:
            node = record
    return Standing(node, routes)


def signature_problem(
    record: Record, *, signers: frozenset[str], approval_key: str | None, verifier: Signer
) -> tuple[str, str] | None:
    """Why a record does not count, as ``(code, reason)``, or ``None`` when it does. The codes
    are the gate's (``modes.check_shelving_record`` emits them): ``shelving-signature`` for a
    signature that does not verify under the record's key or claims the approval key and
    carries another; ``shelving-signer-unlisted`` for a signer who is neither an active steward
    of the target nor a listed curator (``signers``)."""
    if not signed.verifies(record.doc, verifier):
        return "shelving-signature", "the signature does not verify under the record's key"
    problem = signed.approval_key_problem(record.doc, approval_key)
    if problem is not None:
        return "shelving-signature", problem
    if record.contributor not in signers:
        return (
            "shelving-signer-unlisted",
            f"{record.contributor!r} is neither an active steward of the target nor a listed "
            "curator (D-32 v3.47)",
        )
    return None


#: An arrival into a node: the parent whose decomposition (its partial's path) or whose hole
#: child list (``None``) names it.
Arrival = tuple[str, str | None]


def arrivals(
    nodes: Mapping[str, NodeFacts],
    routes: Mapping[str, list[tuple[str, list[str | None]]]],
) -> dict[str, list[Arrival]]:
    """F31-R2 (the plan's edge rules): every arrival into every node — ``(P, route)`` for a
    node that is a hole of a merged decomposition of ``P`` (``products.route_holes``: the matching
    ``graph.json``'s ``decompositions`` publishes, never the ``--h`` id prefix), plus
    ``(P, None)`` for an entry of ``P``'s hole children no decomposition names. A superseded
    parent's arrivals are its revision's (``graph.load_nodes`` folds them), so they are left out
    here, or shelving the revision could never cut them."""
    from opn_gate.graph import is_superseded  # noqa: PLC0415 — graph imports this module lazily

    out: dict[str, list[Arrival]] = {n: [] for n in nodes}
    for parent in sorted(nodes):
        if is_superseded(nodes[parent]):
            continue
        named: set[str] = set()
        for path, holes in routes.get(parent, ()):
            for hole in holes:
                if hole is not None and hole in out:
                    out[hole].append((parent, path))
                    named.add(hole)
        for child in nodes[parent].holes:
            if child in out and child not in named:
                out[child].append((parent, None))
    return out


def _excluded(exclude: frozenset[str], node_id: str) -> frozenset[str]:
    """The file names of ``exclude`` (paths relative to the graph) under this node's directory."""
    return frozenset(
        PurePosixPath(p).name
        for p in exclude
        if PurePosixPath(p).parent.name == DIR and PurePosixPath(p).parent.parent.name == node_id
    )


def own_standing(
    nodes: Mapping[str, NodeFacts], node_id: str, *, exclude: frozenset[str] = frozenset()
) -> Standing:
    """A node's own records, latest per key — and, where it has none of its own, the records of
    the nodes it supersedes with the statement unchanged (F31-Q8: a same-statement revision
    inherits along the chain ``graph.same_statement_chain`` follows), nearer first."""
    from opn_gate.graph import same_statement_chain  # noqa: PLC0415 — see ``arrivals``

    node = nodes[node_id]
    found = standing(load(node.path, exclude=_excluded(exclude, node_id)))
    chain = same_statement_chain(node.path.parent, node_id)
    for prev in chain[1:]:
        if prev not in nodes:
            break
        older = standing(load(nodes[prev].path, exclude=_excluded(exclude, prev)))
        found = Standing(
            found.node if found.node is not None else older.node,
            {**older.routes, **found.routes},
        )
    return found


def derive(
    nodes: Mapping[str, NodeFacts],
    *,
    root: str,
    used: frozenset[str],
    exclude: frozenset[str] = frozenset(),
    routes: Mapping[str, list[tuple[str, list[str | None]]]] | None = None,
) -> dict[str, dict[str, Any] | None]:
    """F31-R2: the shelving each node publishes (``graph/v15``'s object), or ``None``.

    A node's own latest ``scope: node`` record decides for it: ``shelved`` shelves it (void on
    the root and on a statement in ``used``, rule 3 outranking the label), ``unshelved`` exempts
    it from anything inherited. Without one it is shelved exactly when it is not the root, not
    used, has at least one arrival and every arrival is *cut* — the parent shelved, or the
    decomposition retired by the parent's latest record naming that route. A route record never
    shelves the node it sits on and never climbs. Computed top-down, parents before holes, by one
    memoised pass (the DAG makes it deterministic); never a fixed point. The object an inherited
    node carries is the one that reached it, ``via`` the node whose record it is.

    ``exclude`` leaves out records a pull request adds (the gate judges the parent tree);
    ``routes`` is ``products.route_holes`` per node, read here when not given."""
    if routes is None:
        from opn_gate import products  # noqa: PLC0415 — products imports graph, which calls us

        routes = {
            n: [(p.path, [h for _, h in holes]) for p, holes in products.route_holes(nodes, n)]
            for n in nodes
        }
    arriving = arrivals(nodes, routes)
    own = {n: own_standing(nodes, n, exclude=exclude) for n in nodes}
    memo: dict[str, dict[str, Any] | None] = {}

    def state(node_id: str) -> dict[str, Any] | None:
        if node_id in memo:
            return memo[node_id]
        # On the path already (an arrival through a lemma could loop): read as not shelved, so a
        # cycle keeps a node available rather than shelving it by its own reflection.
        memo[node_id] = None
        mine = own[node_id]
        result: dict[str, Any] | None = None
        if mine.node is not None:
            if mine.node.shelves and node_id != root and node_id not in used:
                result = mine.node.published()
        elif node_id != root and node_id not in used and arriving[node_id]:
            reached: dict[str, Any] | None = None
            for parent, route in arriving[node_id]:
                cut = state(parent)
                if cut is None and route is not None:
                    retired = own[parent].retired(route)
                    cut = retired.published() if retired is not None else None
                if cut is None:
                    reached = None
                    break
                reached = reached or cut
            result = reached
        memo[node_id] = result
        return result

    return {n: state(n) for n in nodes}


def used_nodes(nodes: Mapping[str, NodeFacts]) -> frozenset[str]:
    """Rule 3: every statement a merged proof uses — named in any node's ``proofs[].used`` where
    the gate measured it, or an input of any node's closure link. Such a statement may not be
    shelved (``node-used``), and a record on one is void at derivation."""
    out: set[str] = set()
    for node in nodes.values():
        for proof in node.proofs:
            out.update(proof.used or ())
        if node.closure is not None:
            out.update(closure.link_of(node.closure).inputs)
    return frozenset(out)
