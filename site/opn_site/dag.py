"""The target DAG as inline SVG (F04-R6; Q3): longest-path layering, deps below, root on top.

Layer 0 holds the nodes with no deps; a node sits one layer above its highest dep. Within a
layer nodes are ordered lexically. No crossing minimisation (Q3). Every node is a ``<g>`` with
class ``node status-<status>`` and every dep an edge line from the dep to the node, so the
structure is testable and the colours come from the stylesheet, never from the data.
"""

from __future__ import annotations

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


def layers(nodes: list[dict[str, Any]]) -> dict[str, int]:
    """Longest path from a source: a node is one above its deepest dep."""
    deps = {str(n["node_id"]): [str(d) for d in n["deps"]] for n in nodes}
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


def place(nodes: list[dict[str, Any]]) -> tuple[list[Placed], int, int]:
    """Coordinates for every node and the drawing's width and height."""
    by_layer: dict[int, list[str]] = {}
    status = {str(n["node_id"]): str(n["status"]) for n in nodes}
    for node_id, layer in layers(nodes).items():
        by_layer.setdefault(layer, []).append(node_id)
    top = max(by_layer) if by_layer else 0
    for ids in by_layer.values():
        ids.sort()
    row_widths = {
        layer: sum(node_width(n) for n in ids) + (len(ids) - 1) * GAP_X
        for layer, ids in by_layer.items()
    }
    width = PAD * 2 + max(row_widths.values(), default=0)
    height = PAD * 2 + (top + 1) * NODE_H + top * GAP_Y
    placed: list[Placed] = []
    for layer, ids in sorted(by_layer.items()):
        x = (width - row_widths[layer]) // 2
        y = PAD + (top - layer) * (NODE_H + GAP_Y)
        for node_id in ids:
            w = node_width(node_id)
            placed.append(Placed(node_id, status[node_id], layer, x, y, w))
            x += w + GAP_X
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


def svg(nodes: list[dict[str, Any]], *, href: dict[str, str]) -> str:
    """The SVG markup; ``href`` maps node ids to page paths (every id must be present)."""
    placed, width, height = place(nodes)
    at = {p.node_id: p for p in placed}
    deps = {str(n["node_id"]): [str(d) for d in n["deps"]] for n in nodes}
    parts = [
        f'<svg class="dag" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        'role="img" aria-label="dependency graph">',
    ]
    for node_id in sorted(deps):
        for dep in deps[node_id]:
            if dep not in at:
                continue
            a, b = at[dep], at[node_id]
            parts.append(
                f'<line class="edge" data-from="{escape(dep)}" data-to="{escape(node_id)}" '
                f'x1="{a.x + a.w // 2}" y1="{a.y}" '
                f'x2="{b.x + b.w // 2}" y2="{b.y + NODE_H}"/>'
            )
    # F04-T12: each node is a pill — a status dot and the monospace label — with a halo dot the
    # page's script shows on the selected one; the colours come from the stylesheet.
    for p in placed:
        label = short_label(p.node_id)
        parts.append(
            f'<a href="{escape(href[p.node_id])}"><g class="node status-{escape(p.status)}" '
            f'data-node="{escape(p.node_id)}" transform="translate({p.x},{p.y})">'
            f'<rect width="{p.w}" height="{NODE_H}" rx="8"/>'
            f'<circle cx="16" cy="{NODE_H // 2}" r="4"/>'
            f'<text x="28" y="{NODE_H // 2 + 5}">{escape(label)}</text>'
            f'<circle class="halo" cx="{p.w - 14}" cy="{NODE_H // 2}" r="3"/>'
            f"<title>{escape(p.node_id)}: {escape(p.status)}</title></g></a>"
        )
    parts.append("</svg>")
    return "\n".join(parts)
