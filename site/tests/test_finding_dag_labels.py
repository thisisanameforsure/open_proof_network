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
from typing import Any

from opn_site import dag

ROOT = "infinitude-of-primes"
HOLES = [f"{ROOT}--h{i}" for i in range(1, 5)]
NODES: list[dict[str, Any]] = [
    {"node_id": ROOT, "status": "blocked", "deps": HOLES},
    *({"node_id": h, "status": "blocked", "deps": []} for h in HOLES),
]
LABEL_MAX = 22  # what fits NODE_W today (21 characters and the ellipsis)


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
