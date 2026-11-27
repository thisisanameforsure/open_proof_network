"""F34-T35 (REMINDERS-erdos-257 item 14; mockup ``New-Select-Side``): the panel's tabs carry that
statement's counts, as the mockup draws "Proof 1" and "Work 3": Proof counts the ways it is being
proved (its decompositions, and its own proof if it has one), Work its attempts. A tab with
nothing to count carries no number; Claim, Known and Record carry none.
"""

from __future__ import annotations

import re
from pathlib import Path

import fixture
from harness import TARGET
from test_crux_band import band_tree
from test_routes_view import render_tree

from opn_site import model, render


def tabs_of(page: str) -> dict[str, dict[str, str | None]]:
    out: dict[str, dict[str, str | None]] = {}
    for m in re.finditer(
        r'<div class="card panel" data-node="(?P<id>[^"]+)".*?'
        r'<div class="panel-tabs"[^>]*>(?P<tabs>.*?)</div>',
        page,
        re.S,
    ):
        out[m["id"]] = {
            part: n or None
            for part, n in re.findall(
                r'data-tab="([a-z]+)"[^>]*>[A-Za-z]+(?: <span class="tab-n">(\d+)</span>)?'
                r"</button>",
                m["tabs"],
            )
        }
    return out


def test_proof_and_work_carry_the_statements_counts(tmp_path: Path) -> None:
    root = band_tree(tmp_path / "g")
    page = render_tree(root)[f"problems/{TARGET}/index.html"]
    tv = model.load_site(root, fixture.COMMIT).targets[TARGET]
    r = render.Renderer
    tabs = tabs_of(page)
    assert tabs, "every panel has its tabs"
    seen_proof = False
    for nid, t in tabs.items():
        nv = tv.nodes[nid]
        proofs = len(nv.graph_entry.get("decompositions") or []) + (
            1 if nv.proof_path and r.node_state(nv) == "proved" else 0
        )
        assert t["how"] == (str(proofs) if proofs else None), (nid, t)
        if "work" in t:
            n = nv.attempts.count
            assert t["work"] == (str(n) if n else None), (nid, t)
        for part in ("claim", "known", "record"):
            assert t.get(part) is None, (nid, part, t)
        seen_proof = seen_proof or bool(proofs)
    assert seen_proof, "the fixture counts at least one proof"
