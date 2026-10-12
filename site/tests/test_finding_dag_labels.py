"""Finding site-dag-labels (2026-09-13, the Euclid tester): the DAG truncates hole labels
identically.

A skeleton's holes are named ``<parent>--h<n>`` (F07-R6), and ``dag.svg`` keeps the first 21
characters of a long id. Every hole of ``infinitude-of-primes`` is 24 characters, so all four
boxes read ``infinitude-of-primes-…`` — the part that tells them apart is the part cut off.

Mike's decision (2026-09-14, plan F04-T10): tail-preserving labels that still fit the box.
``test_dag.py``'s truncation test pins today's head-only rule and is rewritten with the fix.
Held as a strict xfail from f80151b until F04-T10 (2026-09-14).
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any

from opn_site import dag

ROOT = "infinitude-of-primes-progression"  # 32 characters: F04-T12 pills keep that many
HOLES = [f"{ROOT}--h{i}" for i in range(1, 5)]
NODES: list[dict[str, Any]] = [
    {"node_id": ROOT, "status": "blocked", "deps": HOLES},
    *({"node_id": h, "status": "blocked", "deps": []} for h in HOLES),
]
LABEL_MAX = dag.LABEL_MAX  # what a pill keeps whole (31 characters and the ellipsis)


def labels(out: str) -> dict[str, str]:
    """Each node's ``<text>`` label, keyed by its ``data-node``."""
    found = re.findall(r'data-node="([^"]+)"[^>]*>.*?<text[^>]*>([^<]*)</text>', out, re.S)
    return dict(found)


def test_hole_labels_are_distinct_and_keep_their_suffix() -> None:
    out = dag.svg(NODES, href={n["node_id"]: f"/nodes/t/{n['node_id']}/" for n in NODES})
    got = labels(out)
    assert set(got) == {ROOT, *HOLES}, "guard: one label per node"
    assert all(len(h) > LABEL_MAX for h in HOLES), "guard: every hole id is truncated"
    assert got[ROOT] == ROOT

    hole_labels = [got[h] for h in HOLES]
    assert len(set(hole_labels)) == len(HOLES), hole_labels
    for i, hole in enumerate(HOLES, start=1):
        assert got[hole].endswith(f"--h{i}"), (hole, got[hole])
        assert len(got[hole]) <= LABEL_MAX, got[hole]
        assert f"<title>{hole}: blocked</title>" in out, "the whole id stays in the title"


class _Strip(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.out: list[str] = []

    def handle_data(self, data: str) -> None:
        self.out.append(data)


def pill_text(svg: str, node_id: str) -> str:
    """One pill (its ``<a>``) as a tag-stripper reads it."""
    start = svg.rindex("<a ", 0, svg.index(f'data-node="{node_id}"'))
    p = _Strip()
    p.feed(svg[start : svg.index("</a>", start)])
    p.close()
    return "".join(p.out)


def test_no_pill_runs_its_label_into_its_badge_or_its_title() -> None:
    """F04-T41 (b): a pill's label, its outline badge's count, its circularity glyph and its
    title are separate words once the tags are stripped, so no pill reads
    ``h2--h11erdos-1094--h2--h1`` as the live erdos-1094 page did."""
    target = "erdos-1094"
    ids = [target, f"{target}--h2", f"{target}--h2--h1"]
    nodes: list[dict[str, Any]] = [
        {"node_id": ids[0], "status": "blocked", "deps": [ids[1]]},
        {"node_id": ids[1], "status": "blocked", "deps": [ids[2]]},
        {"node_id": ids[2], "status": "ready", "deps": []},
    ]
    out = dag.svg(
        nodes,
        href={i: f"/nodes/{target}/{i}/" for i in ids},
        outlines={ids[1]: 1, ids[2]: 2},
        labelled={ids[2]},
        root=target,
        prefix=target,
    )
    for node_id in ids:
        words = pill_text(out, node_id).split()
        label = dag.label_of(node_id, (target, target))
        assert label in words, (label, words)
        assert f"{node_id}:" in words, ("the title's id is a word of its own", words)
        assert not any(re.match(rf"{re.escape(label)}\d", w) for w in words), words
    assert "1" in pill_text(out, ids[1]).split()
    assert "⇒" in pill_text(out, ids[2]).split()
