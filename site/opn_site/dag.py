"""The target DAG as inline SVG (F04-R6; Q3): longest-path layering, deps below. The root is on
top only while nothing depends on it; a variant that uses the root is drawn above it (F04-T24).

Layer 0 holds the nodes with no deps; a node sits one layer above its highest dep. Within a
layer nodes are ordered lexically. No crossing minimisation (Q3). Every node is a ``<g>`` with
class ``node status-<status>`` and every dep an edge line from the dep to the node, so the
structure is testable and the colours come from the stylesheet, never from the data.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from html import escape
from typing import Any

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
#: The gap between the wrapped rows of one layer: closer than two layers, which an edge crosses.
WRAP_GAP_Y = 14


def node_width(node_id: str) -> int:
    return PILL_PAD + round(CHAR_W * len(short_label(node_id)))


@dataclass(frozen=True)
class Placed:
    node_id: str
    status: str
    layer: int
    x: int
    y: int
    w: int


def below(node: dict[str, Any]) -> list[str]:
    """What a node is drawn above: its deps and (F18-T2) the nodes its merged proof uses."""
    out = [str(d) for d in node["deps"]]
    out.extend(str(u) for u in node.get("uses") or [] if str(u) not in out)
    return out


@dataclass(frozen=True)
class ProofMarks:
    """F18-T2: one proof of the target as the drawing marks it: the nodes of its closure and the
    edges its term follows (``(from, to)``, the dep or used node first)."""

    nodes: frozenset[str]
    edges: frozenset[tuple[str, str]]


def pointers(nodes: list[dict[str, Any]]) -> dict[str, list[str]]:
    """F18-R9: the cruxes proposed for each node that no merged proof of it uses yet — the dashed
    lines the drawing makes, keyed by the node they point at. A crux the node already rests on
    (a dep, or a use, F08-R19) needs no pointer: the solid line says more."""
    rows = {str(n["node_id"]): n for n in nodes}
    out: dict[str, list[str]] = {}
    for n in nodes:
        target = n.get("proposed_for")
        if not target or str(target) not in rows:
            continue
        crux, row = str(n["node_id"]), rows[str(target)]
        if crux in below(row):
            continue
        out.setdefault(str(target), []).append(crux)
    return out


def layers(nodes: list[dict[str, Any]]) -> dict[str, int]:
    """Longest path from a source: a node is one above its deepest dep (or used node, or a crux
    proposed for it, F18-R9, so the crux sits beneath the node it serves)."""
    pointed = pointers(nodes)
    deps = {str(n["node_id"]): [*below(n), *pointed.get(str(n["node_id"]), [])] for n in nodes}
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


def wrap(ids: list[str]) -> list[list[str]]:
    """One layer's nodes, in order, split into rows no wider than ``MAX_ROW_W`` (F04-T24). A
    single pill wider than that still gets a row of its own."""
    rows: list[list[str]] = [[]]
    used = 0
    for node_id in ids:
        w = node_width(node_id)
        extra = w if not rows[-1] else GAP_X + w
        if rows[-1] and used + extra > MAX_ROW_W:
            rows.append([])
            used, extra = 0, w
        rows[-1].append(node_id)
        used += extra
    return rows


def row_width(ids: list[str]) -> int:
    return sum(node_width(n) for n in ids) + max(len(ids) - 1, 0) * GAP_X


def place(nodes: list[dict[str, Any]]) -> tuple[list[Placed], int, int]:
    """Coordinates for every node and the drawing's width and height. Layers stack bottom-up,
    the topmost first; a layer too wide for one row is wrapped (``wrap``), its rows kept close
    together so they still read as one layer."""
    by_layer: dict[int, list[str]] = {}
    status = {str(n["node_id"]): str(n["status"]) for n in nodes}
    for node_id, layer in layers(nodes).items():
        by_layer.setdefault(layer, []).append(node_id)
    rows_of = {layer: wrap(sorted(ids)) for layer, ids in by_layer.items()}
    width = PAD * 2 + max((row_width(r) for rows in rows_of.values() for r in rows), default=0)
    placed: list[Placed] = []
    y = PAD
    for layer in sorted(rows_of, reverse=True):  # the top layer first
        for index, ids in enumerate(rows_of[layer]):
            if index:
                y += NODE_H + WRAP_GAP_Y
            x = (width - row_width(ids)) // 2
            for node_id in ids:
                w = node_width(node_id)
                placed.append(Placed(node_id, status[node_id], layer, x, y, w))
                x += w + GAP_X
        y += NODE_H + GAP_Y
    height = (y - GAP_Y + PAD) if rows_of else PAD * 2 + NODE_H
    placed.sort(key=lambda p: (p.layer, p.y, p.x))
    return placed, width, height


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
    informal outlines (annexes, D-31); its panel says which skeleton followed each."""
    if count <= 0:
        return ""
    return (
        f'<g class="outline-mark" transform="translate({width - 8},-7)">'
        f'<rect width="15" height="14" rx="3"/><text x="7.5" y="10.5">{count}</text></g>'
    )


def svg(
    nodes: list[dict[str, Any]],
    *,
    href: dict[str, str],
    proofs: Sequence[ProofMarks] = (),
    outlines: dict[str, int] | None = None,
) -> str:
    """The SVG markup; ``href`` maps node ids to page paths (every id must be present). With
    ``proofs`` (F18-T2) every node and edge says which proofs of the target it is on."""
    placed, width, height = place(nodes)
    at = {p.node_id: p for p in placed}
    deps = {str(n["node_id"]): [str(d) for d in n["deps"]] for n in nodes}
    used = {str(n["node_id"]): [str(u) for u in n.get("uses") or []] for n in nodes}
    pointed = pointers(nodes)
    parts = [
        f'<svg class="dag" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        'role="img" aria-label="dependency graph">',
    ]
    for node_id in sorted(deps):
        lines = [(d, "edge") for d in deps[node_id]]
        lines.extend((u, "edge use") for u in used[node_id] if u not in deps[node_id])
        lines.extend((c, "edge proposed") for c in pointed.get(node_id, []))
        for dep, kind in lines:
            if dep not in at:
                continue
            a, b = at[dep], at[node_id]
            cls, data = proof_attrs(proofs, [(dep, node_id) in m.edges for m in proofs])
            parts.append(
                f'<line class="{kind}{cls}" data-from="{escape(dep)}" data-to="{escape(node_id)}"'
                f'{data} x1="{a.x + a.w // 2}" y1="{a.y}" '
                f'x2="{b.x + b.w // 2}" y2="{b.y + NODE_H}"/>'
            )
    # F04-T12: each node is a pill — a status dot and the monospace label — with a halo dot the
    # page's script shows on the selected one; the colours come from the stylesheet.
    for p in placed:
        label = short_label(p.node_id)
        cls, data = proof_attrs(proofs, [p.node_id in m.nodes for m in proofs])
        parts.append(
            f'<a href="{escape(href[p.node_id])}"><g class="node status-{escape(p.status)}{cls}" '
            f'data-node="{escape(p.node_id)}"{data} transform="translate({p.x},{p.y})">'
            f'<rect width="{p.w}" height="{NODE_H}" rx="8"/>'
            f'<circle cx="16" cy="{NODE_H // 2}" r="4"/>'
            f'<text x="28" y="{NODE_H // 2 + 5}">{escape(label)}</text>'
            f'<circle class="halo" cx="{p.w - 14}" cy="{NODE_H // 2}" r="3"/>'
            + outline_mark((outlines or {}).get(p.node_id, 0), p.w)
            + f"<title>{escape(p.node_id)}: {escape(p.status)}</title></g></a>"
        )
    parts.append("</svg>")
    return "\n".join(parts)
