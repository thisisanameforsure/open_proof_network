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

NODE_W = 176
NODE_H = 36
GAP_X = 24
GAP_Y = 56
PAD = 16


@dataclass(frozen=True)
class Placed:
    node_id: str
    status: str
    layer: int
    x: int
    y: int


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
    widest = max((len(ids) for ids in by_layer.values()), default=0)
    width = PAD * 2 + widest * NODE_W + max(widest - 1, 0) * GAP_X
    height = PAD * 2 + (top + 1) * NODE_H + top * GAP_Y
    placed: list[Placed] = []
    for layer, ids in sorted(by_layer.items()):
        ids.sort()
        row_w = len(ids) * NODE_W + (len(ids) - 1) * GAP_X
        x0 = (width - row_w) // 2
        y = PAD + (top - layer) * (NODE_H + GAP_Y)
        for i, node_id in enumerate(ids):
            placed.append(Placed(node_id, status[node_id], layer, x0 + i * (NODE_W + GAP_X), y))
    return placed, width, height


def svg(nodes: list[dict[str, Any]], *, href: dict[str, str]) -> str:
    """The SVG markup; ``href`` maps node ids to page paths (every id must be present)."""
    placed, width, height = place(nodes)
    at = {p.node_id: p for p in placed}
    deps = {str(n["node_id"]): [str(d) for d in n["deps"]] for n in nodes}
    parts = [
        f'<svg class="dag" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        'role="img" aria-label="dependency graph">',
        '<defs><marker id="arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="8" '
        'markerHeight="8" orient="auto"><path d="M0,0 L8,4 L0,8 z"/></marker></defs>',
    ]
    for node_id in sorted(deps):
        for dep in deps[node_id]:
            if dep not in at:
                continue
            a, b = at[dep], at[node_id]
            parts.append(
                f'<line class="edge" data-from="{escape(dep)}" data-to="{escape(node_id)}" '
                f'x1="{a.x + NODE_W // 2}" y1="{a.y}" x2="{b.x + NODE_W // 2}" y2="{b.y + NODE_H}" '
                'marker-end="url(#arrow)"/>'
            )
    for p in placed:
        label = p.node_id if len(p.node_id) <= 22 else p.node_id[:21] + "…"
        parts.append(
            f'<a href="{escape(href[p.node_id])}"><g class="node status-{escape(p.status)}" '
            f'data-node="{escape(p.node_id)}" transform="translate({p.x},{p.y})">'
            f'<rect width="{NODE_W}" height="{NODE_H}" rx="3"/>'
            f'<text x="12" y="{NODE_H // 2 + 5}">{escape(label)}</text>'
            f"<title>{escape(p.node_id)}: {escape(p.status)}</title></g></a>"
        )
    parts.append("</svg>")
    return "\n".join(parts)
