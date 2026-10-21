"""The target DAG as inline SVG (F04-R6; Q34): longest-path layering, deps below. The root is on
top only while nothing depends on it; a variant that uses the root is drawn above it (F04-T24).

Layer 0 holds the nodes with no deps; a node sits one layer above its highest dep. F04-T33 (Q34,
replacing Q3's lexical order and straight lines): a line that skips layers gets a bend point in
every row it passes, each row is ordered by sweeps that pull a statement towards the middle of
what it joins (median, then adjacent swaps, keeping the order with fewest crossings), each
statement is then slid sideways towards its neighbours without overlapping another, and a line
is drawn as a curve through its bend points, so it never runs behind a pill it does not join.
Statements no line joins are drawn apart, below the tree. Every node is a ``<g>`` with class
``node status-<status>`` and every line a ``<path>`` with ``data-from`` and ``data-to``, so the
structure is testable and the colours come from the stylesheet, never from the data.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from html import escape
from itertools import pairwise
from statistics import median
from typing import Any

from opn_gate.graph import HOLE_ORIGINS, HOLE_SEPARATOR

NODE_H = 36
GAP_X = 24
GAP_Y = 56
PAD = 16
#: F04-T12: a pill hugs its label — the dot, the monospace text at about 7.8px a character,
#: and room for the selection halo — so every id short enough to keep is shown whole.
CHAR_W = 7.8
PILL_PAD = 46
#: F04-T24: the widest a row of pills may be. The stylesheet scales a drawing down to its column
#: (about 740px on the problem page), so a wider row shrinks every label with it; a layer that
#: would be wider is wrapped onto more rows instead, at full size.
MAX_ROW_W = 720
#: The gap between the wrapped rows of one layer: closer than two layers, but room for a line
#: passing between them to bend.
WRAP_GAP_Y = 30
#: F04-T33: the room a line passing through a row keeps from the pills beside it, and from
#: another passing line.
PASS_GAP = 14
PASS_SEP = 10
#: Sweeps of the row ordering and of the sideways balancing.
ORDER_SWEEPS = 24
BALANCE_SWEEPS = 24
#: The space above the group of statements no line joins, which holds its label.
GROUP_HEAD = 44


Prefix = str | tuple[str, ...] | None


#: F29-T5 (R9): the labels a drawing shows in place of ids, keyed by node id — each row's
#: ``label`` where ``label_source`` is not ``id`` (``labels_of``). ``None`` or an id not in the
#: mapping draws the short id as before.
Labels = Mapping[str, str] | None


def labels_of(nodes: Iterable[Mapping[str, Any]]) -> dict[str, str]:
    """The pill labels of ``graph.json`` rows (``graph/v12``, F29-R3): a row's ``label`` unless
    its ``label_source`` is ``id`` (or the row predates labels), when the id is drawn as before."""
    out: dict[str, str] = {}
    for n in nodes:
        label = n.get("label")
        if label and n.get("label_source") not in (None, "id"):
            out[str(n["node_id"])] = str(label)
    return out


def label_of(node_id: str, prefix: Prefix = None, labels: Labels = None) -> str:
    """F04-T33: a pill's text. On a problem's page a hole starts with the problem's own name or
    its root's, so the longest ``<prefix>--`` that matches is dropped (the whole id stays in the
    pill's title). F29-T5: a node with a label in ``labels`` shows that, whole (a label is at
    most 60 characters, D-3 v3.44)."""
    if labels and node_id in labels:
        return labels[node_id]
    names = (prefix,) if isinstance(prefix, str) else (prefix or ())
    for name in sorted(names, key=len, reverse=True):
        if name and node_id.startswith(name + "--") and len(node_id) > len(name) + 2:
            node_id = node_id[len(name) + 2 :]
            break
    return short_label(node_id)


#: F27-T3: a drawing may give some of its boxes their own widths (the routes drawing's junctions
#: are a dot, not a pill); every other box is sized by ``node_width``.
Widths = Mapping[str, int] | None


def node_width(
    node_id: str, prefix: Prefix = None, widths: Widths = None, labels: Labels = None
) -> int:
    if widths is not None and node_id in widths:
        return widths[node_id]
    return PILL_PAD + round(CHAR_W * len(label_of(node_id, prefix, labels)))


@dataclass(frozen=True)
class Placed:
    node_id: str
    status: str
    layer: int
    x: int
    y: int
    w: int


def lemmas_of(node: dict[str, Any]) -> list[str]:
    """F04-T39 (D-12 v3.38): the nodes a row's ``lemmas`` name (``graph/v8``; an older row has
    none) — restated nodes under other branches, with a hole's standing."""
    raw = node.get("lemmas") or []
    return [str(e["node"]) for e in raw if isinstance(e, dict) and e.get("node")]


def below(node: dict[str, Any]) -> list[str]:
    """What a node is drawn above: its deps, (F18-T2) the nodes its merged proof uses and
    (F04-T39) its lemmas, which it rests on as it rests on a hole child."""
    out = [str(d) for d in node["deps"]]
    out.extend(str(u) for u in node.get("uses") or [] if str(u) not in out)
    out.extend(lemma for lemma in lemmas_of(node) if lemma not in out)
    return out


@dataclass(frozen=True)
class ProofMarks:
    """F18-T2: one proof of the target as the drawing marks it: the nodes of its closure and the
    edges its term follows (``(from, to)``, the dep or used node first)."""

    nodes: frozenset[str]
    edges: frozenset[tuple[str, str]]


def proposed(nodes: Iterable[Mapping[str, Any]]) -> list[str]:
    """F30-T11 (D-14 v3.26 as amended by v3.46): the proposed cruxes — statements whose
    ``proposed_for`` names a statement of the graph and that carry no checked relation (one with
    a relation is a variant, D-30). A crux some statement declares as a *dependency* is not one:
    its solid line is structural and it stays in the tree (erdos-402's ``spec-fa8046e4``); a crux
    a merged proof only *uses* is one (the owner: "keep the specs on the band"). A superseded
    crux is not one (F30-T12): it is drawn as every superseded statement is, and the revision
    that replaced it holds its route and so its holes (erdos-257's ``spec-a70fcca4``)."""
    rows = {str(n["node_id"]): n for n in nodes}
    declared = {str(d) for n in rows.values() for d in n.get("deps") or []}
    return sorted(
        nid
        for nid, n in rows.items()
        if n.get("proposed_for")
        and str(n["proposed_for"]) in rows
        and not n.get("relation")
        and str(n.get("status")) != "superseded"
        and nid not in declared
    )


def band_of(nodes: Iterable[Mapping[str, Any]]) -> tuple[str, ...]:
    """The statements drawn in the band of proposed statements: the proposed cruxes and their
    hole children (a hole origin, an id under ``<crux>--h``), transitively, sorted."""
    rows = {str(n["node_id"]): n for n in nodes}
    band = set(proposed(rows.values()))
    for nid in sorted(rows, key=len):
        if nid in band or str(rows[nid].get("origin")) not in HOLE_ORIGINS:
            continue
        parent = nid.rsplit(HOLE_SEPARATOR, 1)[0]
        if parent != nid and parent in band:
            band.add(nid)
    return tuple(sorted(band))


def band_column(nodes: Iterable[Mapping[str, Any]]) -> tuple[str, ...]:
    """F30-T13 (the owner, 2026-10-21): the band's statements in the column's order, one per
    row. Each crux is followed by its own holes; then the cruxes are walked depth first, in id
    order, over every line among band statements (a dep, a use, a lemma, from a crux or one of
    its holes), so related statements sit above or below each other and unrelated ones follow.
    Nothing here is a layout of their relations: the column is a list."""
    rows = {str(n["node_id"]): n for n in nodes}
    band = band_of(rows.values())
    cruxes = [b for b in band if b in set(proposed(rows.values()))]
    group: dict[str, list[str]] = {c: [c] for c in cruxes}
    owner: dict[str, str] = {c: c for c in cruxes}
    for nid in band:  # band_of is sorted, so a hole follows the cruxes that may own it
        if nid in group:
            continue
        crux = max((c for c in cruxes if nid.startswith(c + HOLE_SEPARATOR)), key=len, default=None)
        if crux is not None:
            group[crux].append(nid)
            owner[nid] = crux
    near: dict[str, set[str]] = {c: set() for c in cruxes}
    for src, dst, _kind in lines([dict(rows[b]) for b in band]):
        a, b = owner.get(src), owner.get(dst)
        if a is not None and b is not None and a != b:
            near[a].add(b)
            near[b].add(a)
    out: list[str] = []
    seen: set[str] = set()

    def visit(c: str) -> None:
        if c in seen:
            return
        seen.add(c)
        out.extend(group[c])
        for other in sorted(near[c]):
            visit(other)

    for c in cruxes:
        visit(c)
    return tuple(out)


#: The line kinds between a variant and the root (F04-T55, D-30 v3.46): ``edge relation
#: <label>`` for each label a row's ``relations`` names.
RELATION_KIND = "edge relation"


def layers(nodes: list[dict[str, Any]]) -> dict[str, int]:
    """Longest path from a source: a node is one above its deepest dep (or used node, or the
    variant whose relation it draws, F04-T55). A proposed crux is layered by nothing: it is drawn
    apart, in the band (F30-T11)."""
    deps = {
        str(n["node_id"]): [*below(n), *(str(v) for v in (n.get("relations") or {}))] for n in nodes
    }
    memo: dict[str, int] = {}

    def depth(node_id: str, seen: tuple[str, ...]) -> int:
        if node_id in memo:
            return memo[node_id]
        if node_id in seen:
            msg = "dependency cycle: " + " -> ".join((*seen, node_id))
            raise ValueError(msg)
        below = [depth(d, (*seen, node_id)) for d in deps.get(node_id, []) if d in deps]
        memo[node_id] = 1 + max(below) if below else 0
        return memo[node_id]

    for node_id in sorted(deps):
        depth(node_id, ())
    return memo


def raised(layer_of: dict[str, int], edges: list[Line]) -> dict[str, int]:
    """F04-T33: each statement drawn just below the lowest statement that rests on it, not at
    the bottom: a hole sits under its parent, so their lines are short. A statement nothing
    rests on keeps its ``layers`` row."""
    above: dict[str, list[str]] = {}
    for src, dst, _kind in edges:
        above.setdefault(src, []).append(dst)
    out = dict(layer_of)
    for v in sorted(out, key=lambda v: (-out[v], v)):
        if above.get(v):
            out[v] = min(out[d] for d in above[v]) - 1
    return out


#: A line as ``(lower, upper, kind)``.
Line = tuple[str, str, str]


def lines(nodes: list[dict[str, Any]]) -> list[Line]:
    """Every line the drawing makes, as ``(lower, upper, kind)``, in a fixed order: the deps,
    the uses a dep does not already draw (F18-T2), the lemmas neither draws (F04-T39, D-12
    v3.38: ``edge lemma``, from the restated node up to the parent), and (F04-T55, D-30 v3.46)
    the relation trunks a row's ``relations`` names (``{variant: label}``), from the variant up
    to the row. A proposed crux's pointer draws no line (F30-T11, D-14 v3.26 as amended)."""
    ids = {str(n["node_id"]) for n in nodes}
    out: list[Line] = []
    for n in sorted(nodes, key=lambda n: str(n["node_id"])):
        nid = str(n["node_id"])
        deps = [str(d) for d in n["deps"]]
        kinds = {d: "edge" for d in deps}
        for u in n.get("uses") or []:
            kinds.setdefault(str(u), "edge use")
        for lemma in lemmas_of(n):
            kinds.setdefault(lemma, "edge lemma")
        for v, label in (n.get("relations") or {}).items():
            kinds.setdefault(str(v), f"{RELATION_KIND} {label}")
        out.extend((src, nid, kind) for src, kind in sorted(kinds.items()) if src in ids)
    return out


def wrap(
    ids: list[str], prefix: Prefix = None, widths: Widths = None, labels: Labels = None
) -> list[list[str]]:
    """One layer's nodes, in order, split into rows no wider than ``MAX_ROW_W`` (F04-T24). A
    single pill wider than that still gets a row of its own."""
    rows: list[list[str]] = [[]]
    used = 0
    for node_id in ids:
        w = node_width(node_id, prefix, widths, labels)
        extra = w if not rows[-1] else GAP_X + w
        if rows[-1] and used + extra > MAX_ROW_W:
            rows.append([])
            used, extra = 0, w
        rows[-1].append(node_id)
        used += extra
    return rows


def balanced_wrap(
    ids: list[str], prefix: Prefix = None, widths: Widths = None, labels: Labels = None
) -> list[list[str]]:
    """F04-T33: as many rows as ``wrap`` needs, in the same order, with the widths evened out so
    the last row is not a stub. Each row still fits ``MAX_ROW_W``."""
    greedy = wrap(ids, prefix, widths, labels)
    k = len(greedy)
    if k <= 1:
        return greedy
    total = row_width(ids, prefix, widths, labels)
    for slack in range(0, MAX_ROW_W, 8):
        target = min(MAX_ROW_W, total / k + slack)
        rows: list[list[str]] = [[]]
        used = 0.0
        for node_id in ids:
            w = node_width(node_id, prefix, widths, labels)
            extra = w if not rows[-1] else GAP_X + w
            if rows[-1] and used + extra > target and len(rows) < k:
                rows.append([])
                used, extra = 0.0, w
            rows[-1].append(node_id)
            used += extra
        if all(row_width(r, prefix, widths, labels) <= MAX_ROW_W for r in rows):
            return rows
    return greedy


def row_width(
    ids: list[str], prefix: Prefix = None, widths: Widths = None, labels: Labels = None
) -> int:
    return sum(node_width(n, prefix, widths, labels) for n in ids) + max(len(ids) - 1, 0) * GAP_X


@dataclass(frozen=True)
class Edge:
    """One drawn line: from the lower node (``src``, a dep, use or crux) up to ``dst``, through
    ``points`` (bottom first): the port on ``src``'s top, the foot and head of each bend point
    in a row the line passes, and the port on ``dst``'s bottom."""

    src: str
    dst: str
    kind: str
    points: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class Layout:
    placed: list[Placed]
    edges: list[Edge]
    width: int
    height: int
    #: The statements no line joins, drawn apart below the tree (F04-T33).
    loose: tuple[str, ...] = ()
    #: Where that group's label sits (its baseline), when there is a group.
    group_y: int = 0
    #: F30-T11: the band of proposed statements, drawn apart below everything else, and where
    #: its label sits; ``links`` are the measured lines between the band and the rest, which
    #: ``svg`` draws hidden until lit.
    band: tuple[str, ...] = ()
    band_y: int = 0
    links: tuple[Edge, ...] = ()


# -- ordering ---------------------------------------------------------------------------------

#: A bend point is named for its line and its row; real ids never contain a NUL.
_BEND = "\x00"


def _bend_id(src: str, dst: str, rank: int) -> str:
    return f"{_BEND}{src}{_BEND}{dst}{_BEND}{rank}"


def _is_bend(item: str) -> bool:
    return item.startswith(_BEND)


class _Ranks:
    """Rows bottom first, each a list of node ids and bend points, with the line segments
    between adjacent rows."""

    def __init__(self, rows: list[list[str]], segs: list[tuple[str, str]]) -> None:
        self.rows = rows
        self.down: dict[str, list[str]] = {}
        self.up: dict[str, list[str]] = {}
        for lo, hi in segs:
            self.up.setdefault(lo, []).append(hi)
            self.down.setdefault(hi, []).append(lo)

    def crossings_between(self, r: int) -> int:
        """Crossings between row ``r`` and the row above it."""
        if r + 1 >= len(self.rows):
            return 0
        at_lo = {v: i for i, v in enumerate(self.rows[r])}
        at_hi = {v: i for i, v in enumerate(self.rows[r + 1])}
        segs = sorted(
            (at_lo[v], at_hi[u]) for v in self.rows[r] for u in self.up.get(v, []) if u in at_hi
        )
        return sum(
            1
            for i, (a1, b1) in enumerate(segs)
            for a2, b2 in segs[i + 1 :]
            if a1 != a2 and b1 != b2 and (a1 - a2) * (b1 - b2) < 0
        )

    def crossings(self) -> int:
        return sum(self.crossings_between(r) for r in range(len(self.rows) - 1))

    def order(self) -> None:
        """Median sweeps down and up, each followed by adjacent swaps; keeps the best."""
        best = [list(r) for r in self.rows]
        best_c = self.crossings()
        for sweep in range(ORDER_SWEEPS):
            upward = sweep % 2 == 0
            span = range(1, len(self.rows)) if upward else range(len(self.rows) - 2, -1, -1)
            for r in span:
                ref = self.rows[r - 1] if upward else self.rows[r + 1]
                near = self.down if upward else self.up
                at = {v: i for i, v in enumerate(ref)}
                row = self.rows[r]

                def key(
                    item: str,
                    row: list[str] = row,
                    near: dict[str, list[str]] = near,
                    at: dict[str, int] = at,
                ) -> tuple[float, int]:
                    xs = [at[n] for n in near.get(item, []) if n in at]
                    here = row.index(item)
                    return (float(median(xs)) if xs else here * len(at) / max(len(row), 1), here)

                self.rows[r] = sorted(row, key=key)
            self._transpose()
            c = self.crossings()
            if c < best_c:
                best, best_c = [list(r) for r in self.rows], c
            if best_c == 0:
                break
        self.rows = best

    def _transpose(self) -> None:
        improved = True
        rounds = 0
        while improved and rounds < 8:
            improved = False
            rounds += 1
            for r, row in enumerate(self.rows):
                for i in range(len(row) - 1):
                    before = self._around(r)
                    row[i], row[i + 1] = row[i + 1], row[i]
                    if self._around(r) < before:
                        improved = True
                    else:
                        row[i], row[i + 1] = row[i + 1], row[i]

    def _around(self, r: int) -> int:
        return self.crossings_between(r) + (self.crossings_between(r - 1) if r else 0)


def _ranks(
    rows_of_layer: dict[int, list[list[str]]],
    edges: list[Line],
    seed: dict[str, float],
) -> tuple[_Ranks, dict[str, int]]:
    """Rows bottom first from each layer's rows (the top row of a layer listed first), with a
    bend point for every row a line passes; ``seed`` orders the bend points before the sweeps."""
    rows: list[list[str]] = []
    rank_of: dict[str, int] = {}
    for layer in sorted(rows_of_layer):
        for row in reversed(rows_of_layer[layer]):
            for v in row:
                rank_of[v] = len(rows)
            rows.append(list(row))
    segs: list[tuple[str, str]] = []
    for src, dst, _kind in edges:
        prev = src
        for r in range(rank_of[src] + 1, rank_of[dst]):
            p = _bend_id(src, dst, r)
            rows[r].append(p)
            segs.append((prev, p))
            prev = p
        segs.append((prev, dst))

    def where(item: str) -> float:
        if not _is_bend(item):
            return seed.get(item, 0.0)
        _, src, dst, _r = item.split(_BEND)
        return (seed.get(src, 0.0) + seed.get(dst, 0.0)) / 2

    for r, row in enumerate(rows):
        rows[r] = sorted(row, key=lambda v: (where(v), v))
    return _Ranks(rows, segs), rank_of


# -- sideways placement -----------------------------------------------------------------------


def _sep(a: str, b: str) -> float:
    if _is_bend(a) and _is_bend(b):
        return PASS_SEP
    if _is_bend(a) or _is_bend(b):
        return PASS_GAP
    return GAP_X


def _project(
    row: list[str], want: dict[str, float], wid: dict[str, float], span: float
) -> dict[str, float]:
    """The left edges closest (least squares) to ``want`` that keep the row in order, apart and
    inside ``[0, span]``: pool-adjacent-violators on the offsets."""
    offs: list[float] = []
    acc = 0.0
    for i, v in enumerate(row):
        offs.append(acc)
        acc += wid[v] + (_sep(v, row[i + 1]) if i + 1 < len(row) else 0.0)
    room = max(span - acc, 0.0)
    blocks: list[list[float]] = []  # [value, weight, count]
    for i, v in enumerate(row):
        weight = 2.0 if _is_bend(v) else 1.0
        blocks.append([want[v] - offs[i], weight, 1])
        while len(blocks) > 1 and blocks[-2][0] > blocks[-1][0]:
            v2, w2, n2 = blocks.pop()
            v1, w1, n1 = blocks.pop()
            blocks.append([(v1 * w1 + v2 * w2) / (w1 + w2), w1 + w2, n1 + n2])
    out: dict[str, float] = {}
    i = 0
    for value, _w, count in blocks:
        for _ in range(int(count)):
            out[row[i]] = min(max(value, 0.0), room) + offs[i]
            i += 1
    return out


def _balance(ranks: _Ranks, wid: dict[str, float]) -> tuple[dict[str, float], float]:
    """Left edges for every item and the width they fill. The widest row fixes the width; every
    other row slides towards the centres of what its items join."""

    def row_span(row: list[str]) -> float:
        return sum(wid[v] for v in row) + sum(_sep(a, b) for a, b in pairwise(row))

    widest = max((row_span(r) for r in ranks.rows), default=0.0)
    # Room to straighten a line up to the widest a row may be; trimmed to what is used below.
    span = max(widest, float(MAX_ROW_W))
    left: dict[str, float] = {}
    for row in ranks.rows:
        x = (span - row_span(row)) / 2
        for i, v in enumerate(row):
            left[v] = x
            x += wid[v] + (_sep(v, row[i + 1]) if i + 1 < len(row) else 0.0)
    # One side at a time: a downward pass hangs each row under the row above it, an upward pass
    # stands each row over the row below it; the last pass is upward, so a statement ends centred
    # over what it rests on and a chain of single steps stays one upright column.
    for sweep in range(BALANCE_SWEEPS):
        downward = sweep % 2 == 0
        order = range(len(ranks.rows) - 2, -1, -1) if downward else range(1, len(ranks.rows))
        side = ranks.up if downward else ranks.down
        for r in order:
            row = ranks.rows[r]
            want: dict[str, float] = {}
            for v in row:
                near = side.get(v, [])
                centre = (
                    sum(left[n] + wid[n] / 2 for n in near) / len(near)
                    if near
                    else left[v] + wid[v] / 2
                )
                want[v] = centre - wid[v] / 2
            left.update(_project(row, want, wid, span))
    if not left:
        return left, 0.0
    lo = min(left.values())
    hi = max(left[v] + wid[v] for v in left)
    return {v: x - lo for v, x in left.items()}, hi - lo


# -- the layout -------------------------------------------------------------------------------


def _loose(status: dict[str, str], edges: list[Line], root: str | None) -> tuple[str, ...]:
    """The statements no line joins, drawn apart (never the root; nothing when no line is
    drawn at all). Superseded ones last, so hiding them only shortens the last row."""
    if not edges:
        return ()
    joined = {x for src, dst, _k in edges for x in (src, dst)}
    alone = (v for v in status if v not in joined and v != root)
    return tuple(sorted(alone, key=lambda v: (status[v] == "superseded", v)))


def _rows(  # noqa: PLR0913, PLR0917 — the ordering's inputs (F30-T1 added the seed)
    layer_of: dict[str, int],
    edges: list[Line],
    names: Prefix,
    widths: Widths = None,
    labels: Labels = None,
    order: Mapping[str, float] | None = None,
) -> tuple[_Ranks, dict[str, int]]:
    """The ordered rows. Pass one orders one row per layer; each layer is then wrapped in that
    order (T24), what rests on nothing in its upper rows and what has lines down in its lower
    ones, nearest the statements those lines reach; pass two orders the wrapped rows as rows of
    their own, so a line passes between them. F30-T1 (Q2): ``order`` seeds pass one (each
    node's x in a reference layout), so a subset keeps the reference's order where the sweeps
    have no reason to change it."""
    by_layer: dict[int, list[str]] = {}
    for v in sorted(layer_of):
        by_layer.setdefault(layer_of[v], []).append(v)
    first, _ = _ranks({k: [ids] for k, ids in by_layer.items()}, edges, dict(order or {}))
    first.order()
    seed = {v: float(i) for row in first.rows for i, v in enumerate(row) if not _is_bend(v)}
    rests_on = {dst for _src, dst, _k in edges}
    rows_of_layer = {
        k: balanced_wrap(sorted(ids, key=lambda v: (v in rests_on, seed[v])), names, widths, labels)
        for k, ids in by_layer.items()
    }
    ranks, rank_of = _ranks(rows_of_layer, edges, seed)
    ranks.order()
    return ranks, rank_of


def _tops(ranks: _Ranks, layer_of: dict[str, int]) -> dict[int, float]:
    """Each row's top, the highest row first: a layer's wrapped rows close together, layers
    further apart."""

    def layer(r: int) -> int | None:
        return next((layer_of[v] for v in ranks.rows[r] if not _is_bend(v)), None)

    tops: dict[int, float] = {}
    y = float(PAD)
    for r in range(len(ranks.rows) - 1, -1, -1):
        if tops:
            y += NODE_H + (WRAP_GAP_Y if layer(r) == layer(r + 1) else GAP_Y)
        tops[r] = y
    return tops


def _route(
    edges: list[Line],
    rank_of: dict[str, int],
    bend_x: dict[str, float],
    tops: dict[int, float],
    at: dict[str, Placed],
) -> list[Edge]:
    """Every line through its bend points, with a port on each end spread along the pill in the
    order of what lies beyond it, so lines meeting at a pill do not cross there."""
    mids = [
        [bend_x[_bend_id(src, dst, r)] for r in range(rank_of[src] + 1, rank_of[dst])]
        for src, dst, _kind in edges
    ]
    beyond: dict[str, list[tuple[float, int]]] = {}
    for i, (src, dst, _kind) in enumerate(edges):
        up = mids[i][0] if mids[i] else at[dst].x + at[dst].w / 2
        down = mids[i][-1] if mids[i] else at[src].x + at[src].w / 2
        beyond.setdefault(f"up{_BEND}{src}", []).append((up, i))
        beyond.setdefault(f"down{_BEND}{dst}", []).append((down, i))
    port: dict[tuple[str, int], float] = {}
    for key, items in beyond.items():
        p = at[key.split(_BEND, 1)[1]]
        # F27-T3: a box narrower than a pill (a junction dot) takes every line at its centre.
        step = max(0.0, min(8.0, (p.w - 40) / max(len(items), 1)))
        for k, (_x, i) in enumerate(sorted(items)):
            port[(key, i)] = p.x + p.w / 2 + (k - (len(items) - 1) / 2) * step
    out: list[Edge] = []
    for i, (src, dst, kind) in enumerate(edges):
        pts: list[tuple[float, float]] = [(port[(f"up{_BEND}{src}", i)], float(at[src].y))]
        for r, x in zip(range(rank_of[src] + 1, rank_of[dst]), mids[i], strict=True):
            pts.extend(((x, tops[r] + NODE_H), (x, tops[r])))
        pts.append((port[(f"down{_BEND}{dst}", i)], float(at[dst].y + NODE_H)))
        out.append(Edge(src, dst, kind, tuple(pts)))
    return out


def layout(  # noqa: PLR0913, PLR0915 — the drawing's inputs (F30-T1 the seed, T11 the band)
    nodes: list[dict[str, Any]],
    *,
    root: str | None = None,
    prefix: str | None = None,
    widths: Widths = None,
    labels: Labels = None,
    order: Mapping[str, float] | None = None,
    apart: bool = True,
) -> Layout:
    """Coordinates for every statement and every line (F04-T33). With ``prefix`` (the target
    id) a label also drops the root's own name; ``widths`` (F27-T3) sizes the boxes it names;
    ``labels`` (F29-T5) are the names the pills show, which every box is measured from;
    ``order`` (F30-T1) seeds each row's order from a reference layout's x positions. F30-T11:
    the band's statements (``band_of``) are laid out as a tree of their own under everything
    else, and the measured lines between the band and the rest come back as ``links``; with
    ``apart`` false nothing is set aside — no "no line joins" group, no band — which is how the
    band itself is laid out."""
    names: Prefix = (prefix, root) if prefix and root else prefix
    nodes = sorted(nodes, key=lambda n: str(n["node_id"]))
    band = band_of(nodes) if apart else ()
    all_lines = lines(nodes)
    if band:
        tree_nodes = [n for n in nodes if str(n["node_id"]) not in band]
        crossing = [ln for ln in all_lines if (ln[0] in band) != (ln[1] in band)]
    else:
        tree_nodes, crossing = nodes, []
    status = {str(n["node_id"]): str(n["status"]) for n in tree_nodes}
    edges = lines(tree_nodes)
    loose = _loose(status, edges, root) if apart else ()
    layer_of = raised({v: k for v, k in layers(tree_nodes).items() if v not in loose}, edges)
    ranks, rank_of = _rows(layer_of, edges, names, widths, labels, order)
    wid: dict[str, float] = {v: float(node_width(v, names, widths, labels)) for v in status}
    wid.update({v: 0.0 for row in ranks.rows for v in row if _is_bend(v)})
    left, span = _balance(ranks, wid)
    tops = _tops(ranks, layer_of)
    tree_h = max(tops.values()) + NODE_H if tops else float(PAD)

    # The group no line joins, wrapped and centred under the tree.
    group_rows = wrap(list(loose), names, widths, labels) if loose else []
    width = max(
        span, float(max((row_width(r, names, widths, labels) for r in group_rows), default=0))
    )
    x0 = (width - span) / 2 + PAD
    placed = [
        Placed(v, status[v], layer_of[v], round(left[v] + x0), round(tops[r]), int(wid[v]))
        for r, row in enumerate(ranks.rows)
        for v in row
        if not _is_bend(v)
    ]
    group_y, height = 0, tree_h + PAD
    if group_rows:
        group_y = round(tree_h + GROUP_HEAD - 14)
        gy = tree_h + GROUP_HEAD - NODE_H - WRAP_GAP_Y
        for row in group_rows:
            gy += NODE_H + WRAP_GAP_Y
            x = PAD + (width - row_width(row, names, widths, labels)) / 2
            for v in row:
                placed.append(Placed(v, status[v], -1, round(x), round(gy), int(wid[v])))
                x += wid[v] + GAP_X
        height = gy + NODE_H + PAD
    bend_x = {v: left[v] + x0 for row in ranks.rows for v in row if _is_bend(v)}
    drawn = _route(edges, rank_of, bend_x, tops, {p.node_id: p for p in placed})
    placed.sort(key=lambda p: (p.layer < 0, p.layer, p.y, p.x))
    if not band:
        return Layout(placed, drawn, round(width + 2 * PAD), round(height), loose, group_y)

    # F30-T11: the band under everything, a tree of its own (its cruxes' pointers dropped, so
    # nothing in it is set aside again), centred; its lines offset into place.
    inner = layout(
        [{**n, "proposed_for": None} for n in nodes if str(n["node_id"]) in band],
        prefix=prefix,
        widths=widths,
        labels=labels,
        order=order,
        apart=False,
    )
    tree_w = width + 2 * PAD
    full_w = max(tree_w, inner.width)
    if tree_w < full_w:  # a wider band: the tree is centred over it
        shift = (full_w - tree_w) / 2
        placed = [
            Placed(p.node_id, p.status, p.layer, round(p.x + shift), p.y, p.w) for p in placed
        ]
        drawn = [
            Edge(e.src, e.dst, e.kind, tuple((x + shift, y) for x, y in e.points)) for e in drawn
        ]
    dx = (full_w - inner.width) / 2
    band_y = round(height + GROUP_HEAD - 14)
    dy = band_y + 14 + WRAP_GAP_Y - PAD
    placed.extend(
        Placed(p.node_id, p.status, p.layer, round(p.x + dx), round(p.y + dy), p.w)
        for p in inner.placed
    )
    drawn.extend(
        Edge(e.src, e.dst, e.kind, tuple((x + dx, y + dy) for x, y in e.points))
        for e in inner.edges
    )
    at = {p.node_id: p for p in placed}
    links = tuple(
        Edge(
            src,
            dst,
            kind,
            (
                (at[src].x + at[src].w / 2, float(at[src].y)),
                (at[dst].x + at[dst].w / 2, float(at[dst].y + NODE_H)),
            ),
        )
        for src, dst, kind in crossing
        if src in at and dst in at
    )
    return Layout(
        placed,
        drawn,
        round(full_w),
        round(dy + inner.height),
        loose,
        group_y,
        band,
        band_y,
        links,
    )


def place(nodes: list[dict[str, Any]]) -> tuple[list[Placed], int, int]:
    """Coordinates for every node and the drawing's width and height (see ``layout``)."""
    lay = layout(nodes)
    return lay.placed, lay.width, lay.height


def _curve(a: tuple[float, float], b: tuple[float, float]) -> tuple[tuple[float, float], ...]:
    """The two control points of the curve from ``a`` up to ``b``: upright at both ends."""
    mid = (a[1] + b[1]) / 2
    return (a[0], mid), (b[0], mid)


def curve_points(edge: Edge, per_segment: int = 16) -> list[tuple[float, float]]:
    """The drawn line sampled as a polyline: each step between rows a cubic curve, each pass
    through a row straight up."""
    pts = [edge.points[0]]
    for a, b in pairwise(edge.points):
        if a[0] == b[0]:
            pts.append(b)
            continue
        c1, c2 = _curve(a, b)
        for k in range(1, per_segment + 1):
            t = k / per_segment
            s = 1 - t
            pts.append(
                (
                    s**3 * a[0] + 3 * s * s * t * c1[0] + 3 * s * t * t * c2[0] + t**3 * b[0],
                    s**3 * a[1] + 3 * s * s * t * c1[1] + 3 * s * t * t * c2[1] + t**3 * b[1],
                )
            )
    return pts


def _num(v: float) -> str:
    return f"{v:.1f}".rstrip("0").rstrip(".")


def path_d(edge: Edge) -> str:
    """The SVG path of a line (``curve_points`` samples the same curve)."""
    a = edge.points[0]
    out = [f"M{_num(a[0])} {_num(a[1])}"]
    for p, q in pairwise(edge.points):
        if p[0] == q[0]:
            out.append(f"V{_num(q[1])}")
        else:
            c1, c2 = _curve(p, q)
            out.append("C" + " ".join(_num(v) for v in (*c1, *c2, *q)))
    return "".join(out)


#: The longest label a pill keeps whole: 31 characters and the ellipsis.
LABEL_MAX = 32
#: F04-T10: a long id keeps its tail, because a skeleton's holes differ only there
#: (``<parent>--h1`` ... ``--h4``); the whole id stays in the node's ``<title>``.
LABEL_TAIL = 8


def short_label(node_id: str) -> str:
    """The visible label of a node: the id when it fits, else its head, an ellipsis and its tail."""
    if len(node_id) <= LABEL_MAX:
        return node_id
    head = LABEL_MAX - 1 - LABEL_TAIL
    return node_id[:head] + "…" + node_id[-LABEL_TAIL:]


def proof_attrs(marks: Sequence[ProofMarks], on: Sequence[bool]) -> tuple[str, str]:
    """F18-T2: the classes and ``data-proofs`` for one mark: ``on-proof`` or ``off-proof`` for the
    first proof, which the page shows without its script, and the indices of every proof it is
    on, which the script switches between. Nothing when the target has no proof."""
    if not marks:
        return "", ""
    first = " on-proof" if on[0] else " off-proof"
    indices = " ".join(str(k) for k, hit in enumerate(on) if hit)
    return first, f' data-proofs="{indices}"'


def outline_mark(count: int, width: int) -> str:
    """F18-T4 (R5): a small numbered tab on a pill's top right corner when the node carries
    informal outlines (stepped annexes, D-31 v3.26; F04-T45 leaves notes uncounted); its panel
    says which skeleton followed each."""
    if count <= 0:
        return ""
    return (
        f'<g class="outline-mark" transform="translate({width - 8},-7)">'
        f'<rect width="15" height="14" rx="3"/><text x="7.5" y="10.5">{count}</text></g> '
    )


@dataclass(frozen=True)
class LitMark:
    """F04-T54 (D-25 v3.45): a node's literature status as the drawing marks it — the status
    word (``open``, ``known``, ``elementary``), whether a steward or curator has confirmed it
    (else it is a contributor's proposal awaiting one) and who: the confirmer, or the proposer.
    A fact about the literature, never about difficulty: the mark changes nothing else."""

    status: str
    confirmed: bool
    by: str

    @property
    def phase(self) -> str:
        return "confirmed" if self.confirmed else "proposed"

    @property
    def words(self) -> str:
        """The mark's title: ``Literature: known (proposed by t1009-c, awaits confirmation)``."""
        if self.confirmed:
            return f"Literature: {self.status} (confirmed by {self.by})"
        return f"Literature: {self.status} (proposed by {self.by}, awaits confirmation)"


#: The literature mark's geometry: a 7px square inside the pill's top-right corner, clear of
#: the label (which ends at ``w - 18`` and starts below ``y = 11``), the halo (``y`` 15 to 21
#: at ``w - 14``) and the outline tab (``x`` from ``w - 8``, ``y`` -7 to 7, outside the pill).
LIT_MARK = 7
LIT_MARK_TOP = 4
LIT_MARK_RIGHT = 9
#: What the mark may carry as data: the statuses ``graph.json`` can publish (D-25 v3.35).
Literature = Mapping[str, LitMark] | None


def literature_mark(mark: LitMark | None, width: int) -> str:
    """F04-T54: the small square on a pill that carries a literature status: hollow and dashed
    while only proposed, filled once confirmed, coloured by status through the stylesheet
    (``lit-<status>``), with its own title. Nothing for a node with no record. Markup only: the
    layout never reads it."""
    if mark is None:
        return ""
    x = width - LIT_MARK_RIGHT - LIT_MARK
    return (
        f'<g class="lit-mark lit-{escape(mark.status)} {mark.phase}" '
        f'data-literature="{escape(mark.status)}" data-phase="{mark.phase}" '
        f'transform="translate({x},{LIT_MARK_TOP})">'
        f"<title>{escape(mark.words)}</title> "
        f'<rect width="{LIT_MARK}" height="{LIT_MARK}" rx="1.5"/></g> '
    )


#: F04-T33: the label over the statements no line joins.
GROUP_LABEL = "Statements no line joins to the rest"
#: F30-T11: the band's heading and its one line of help (D-14 v3.26 as amended by v3.46).
BAND_LABEL = "Proposed statements"
BAND_HELP = (
    "statements proposed for this problem; a line to the tree is drawn only where the record "
    "measured one"
)


def svg(  # noqa: PLR0913 — the target's own names beside what the drawing marks
    nodes: list[dict[str, Any]],
    *,
    href: dict[str, str],
    proofs: Sequence[ProofMarks] = (),
    outlines: dict[str, int] | None = None,
    root: str | None = None,
    prefix: str | None = None,
    names: dict[str, str] | None = None,
    labels: Labels = None,
    literature: Literature = None,
) -> str:
    """The SVG markup; ``href`` maps node ids to page paths (every id must be present). With
    ``proofs`` (F18-T2) every node and edge says which proofs of the target it is on; ``root``
    keeps the root in the tree and ``prefix`` (the target id) is dropped from labels (T33).
    ``names`` (F22-T18, S) gives a pill's title the theorem name of an id that names nothing.
    ``labels`` (F29-T5, R9) are the statements' labels: a pill shows its label and its title
    keeps the id, with the label beside it. ``literature`` (F04-T54) marks the pills it names
    with their literature status; the layout is the same with or without it."""
    lay = layout(nodes, root=root, prefix=prefix, labels=labels)
    status = {p.node_id: p.status for p in lay.placed}
    parts = [
        f'<svg class="dag" viewBox="0 0 {lay.width} {lay.height}" width="{lay.width}" '
        f'height="{lay.height}" role="img" aria-label="dependency graph">',
    ]
    for e in sorted(lay.edges, key=lambda e: (e.dst, e.src)):
        cls, data = proof_attrs(proofs, [(e.src, e.dst) in m.edges for m in proofs])
        if "superseded" in (status[e.src], status[e.dst]):
            cls += " touches-superseded"
        parts.append(
            f'<path class="{e.kind}{cls}" data-from="{escape(e.src)}" data-to="{escape(e.dst)}"'
            f'{data} d="{path_d(e)}"/>'
        )
    if lay.loose:
        parts.append(
            f'<line class="dag-divider" x1="{PAD}" y1="{lay.group_y - 22}" '
            f'x2="{lay.width - PAD}" y2="{lay.group_y - 22}"/>'
            f'<text class="dag-group" x="{lay.width // 2}" y="{lay.group_y}">'
            f"{escape(GROUP_LABEL)}</text>"
        )
    if lay.band:
        # F30-T11: the band's heading, and its measured lines into the tree, hidden until lit.
        parts.append(
            f'<line class="dag-divider" x1="{PAD}" y1="{lay.band_y - 22}" '
            f'x2="{lay.width - PAD}" y2="{lay.band_y - 22}"/>'
            f'<text class="dag-group" x="{lay.width // 2}" y="{lay.band_y}">'
            f"{escape(BAND_LABEL)}</text>"
        )
        parts.extend(
            f'<path class="{e.kind} band-link" data-from="{escape(e.src)}" '
            f'data-to="{escape(e.dst)}" d="{path_d(e)}"/>'
            for e in sorted(lay.links, key=lambda e: (e.dst, e.src))
        )

    # F04-T12: each node is a pill — a status dot and the monospace label — with a halo dot the
    # page's script shows on the selected one; the colours come from the stylesheet.
    def named(node_id: str) -> str:
        name = (names or {}).get(node_id) or (labels or {}).get(node_id)
        return f" ({escape(name)})" if name else ""

    for p in lay.placed:
        label = label_of(p.node_id, (prefix, root) if prefix and root else prefix, labels)
        cls, data = proof_attrs(proofs, [p.node_id in m.nodes for m in proofs])
        # F04-T41: the title comes first (the pill's accessible name) and a space separates the
        # children, so a reader who strips the tags gets ``h2--h1 erdos-1094--h2--h1: ready``
        # rather than ``h2--h11erdos-…``; whitespace between SVG elements draws nothing.
        parts.append(
            f'<a href="{escape(href[p.node_id])}"><g class="node status-{escape(p.status)}{cls}" '
            f'data-node="{escape(p.node_id)}"{data} transform="translate({p.x},{p.y})">'
            f"<title>{escape(p.node_id)}{named(p.node_id)}: {escape(p.status)}</title> "
            f'<rect width="{p.w}" height="{NODE_H}" rx="8"/>'
            f'<circle cx="16" cy="{NODE_H // 2}" r="4"/>'
            f'<text x="28" y="{NODE_H // 2 + 5}">{escape(label)}</text> '
            f'<circle class="halo" cx="{p.w - 14}" cy="{NODE_H // 2}" r="3"/>'
            + outline_mark((outlines or {}).get(p.node_id, 0), p.w)
            + literature_mark((literature or {}).get(p.node_id), p.w)
            + "</g></a>"
        )
    parts.append("</svg>")
    return "\n".join(parts)
