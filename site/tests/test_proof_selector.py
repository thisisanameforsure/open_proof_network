"""F18-T2 (R3; AC4), restated by F30 (Q4): a proof is a leaf of the selector.

The owner, on erdos-1050's page (2026-10-03): it is not clear which branches constitute the
proof and which nodes the proof does not need. The page drew every *declared* dependency, so a
proof that used one hole of four looked like it rested on all four, and an open hole under a
merged circularity claim (a label since D-12 v3.35, F04-T37; it was then drawn as a state) sat
under a proved root with nothing to say it was not needed. ``graph.json``'s ``target_proofs``
(F18-T1) names each proof with the nodes its term rests on; the page offers one leaf of the
selector per proof, whose view is the proof's closure with the edges its term follows, and a
note under the selector for each.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import fixture
from harness import TARGET, copy_graph
from test_node_proofs import proof_hash
from test_products import ROOT_NODE
from test_products import attest as gate_attest
from test_target_proofs import resolves_variant

from opn_gate import products
from opn_site import model, render

REPO = "https://github.com/example/graph"
A, B = "tutorial-and-swap", "and-reassoc"
PAGE = f"problems/{TARGET}/index.html"


def render_page(root: Path) -> str:
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    site = model.load_site(root, fixture.COMMIT)
    return render.render_site(site, repo_url=REPO)[PAGE]


def erdos_shape(tmp_path: Path) -> Path:
    """The root declares A and B; its proof term uses A; B is still open (erdos-1050's h1)."""
    root = copy_graph(tmp_path, publish=True)
    gate_attest(root, A, n=1, footprint={"nodes": []})
    gate_attest(
        root, ROOT_NODE, n=3, artifact_hash=proof_hash(root, ROOT_NODE), footprint={"nodes": [A]}
    )
    return root


def pill_classes(page: str) -> dict[str, set[str]]:
    out = {}
    for m in re.finditer(r'<g class="([^"]+)" data-node="([^"]+)"', page):
        out[m.group(2)] = set(m.group(1).split())
    return out


def edge_classes(page: str) -> dict[tuple[str, str], set[str]]:
    out = {}
    for m in re.finditer(r'<path class="([^"]+)" data-from="([^"]+)" data-to="([^"]+)"', page):
        out[(m.group(2), m.group(3))] = set(m.group(1).split())
    return out


def proof_leaves(page: str) -> list[str]:
    """The proof leaves of the selector, in drawing order, each its title (the proof's label)."""
    sel = page[page.index('<svg class="selector"') :] if '<svg class="selector"' in page else ""
    sel = sel[: sel.index("</svg>")] if sel else ""
    return re.findall(
        r'<g class="sel-node kind-proof"[^>]*data-view="proof/\d+"[^>]*><title>([^<]*)</title>', sel
    )


def layouts(page: str) -> dict[str, dict[str, Any]]:
    m = re.search(r'<script type="application/json" id="graph-layouts">(.*?)</script>', page, re.S)
    assert m is not None
    parsed: dict[str, dict[str, Any]] = json.loads(m.group(1))
    return parsed


def legend(page: str) -> str:
    m = re.search(r'<div class="dag-legend">(.*?)</div>', page, re.S)
    assert m is not None
    return m.group(1)


def test_the_proof_is_a_view_of_what_its_term_uses(tmp_path: Path) -> None:
    page = render_page(erdos_shape(tmp_path))
    assert len(proof_leaves(page)) == 1
    view = layouts(page)["proof/0"]
    assert set(view["nodes"]) == {ROOT_NODE, A}
    lines = [(src, dst) for src, dst, _k, _pts in view["lines"]]
    assert lines == [(A, ROOT_NODE)]  # B is declared and not used by the proof


def test_the_key_no_longer_marks_the_proof(tmp_path: Path) -> None:
    key = legend(render_page(erdos_shape(tmp_path)))
    assert "on this proof" not in key and "not needed by this proof" not in key


def test_the_panel_says_whether_a_statement_is_on_the_proof(tmp_path: Path) -> None:
    page = render_page(erdos_shape(tmp_path))
    panel_b = re.search(rf'<div class="card panel" data-node="{B}".*?</dl>', page, re.S)
    panel_a = re.search(rf'<div class="card panel" data-node="{A}".*?</dl>', page, re.S)
    assert panel_b is not None and "Not needed by any proof of this problem" in panel_b.group(0)
    assert panel_a is not None and "On proof 1" in panel_a.group(0)


def test_every_way_the_problem_is_proved_is_offered_in_record_order(tmp_path: Path) -> None:
    root = erdos_shape(tmp_path)
    resolves_variant(root, "variant-later", 9, "carol")
    resolves_variant(root, "variant-earlier", 5, "dave")
    page = render_page(root)
    entries = proof_leaves(page)
    assert len(entries) == 3, entries
    assert "root" in entries[0]
    assert "variant-earlier" in entries[1] and "dave" in entries[1]
    assert "variant-later" in entries[2] and "carol" in entries[2]
    # The script shows one view per leaf; the root's proof is index 0.
    assert set(layouts(page)["proof/1"]["nodes"]) == {"variant-earlier"}
    assert page.count('<p class="proof-note" data-view="proof/') == 3


def test_an_open_problem_has_no_proof_to_draw(tmp_path: Path) -> None:
    page = render_page(copy_graph(tmp_path, publish=True))
    assert proof_leaves(page) == []
    assert "proof/" not in layouts(page) and "proof-note" not in page


def test_an_unmeasured_proof_says_so(tmp_path: Path) -> None:
    """Before the backfill, every live closure is unmeasured: the page must not present a
    closure through declared dependencies as the proof term's own."""
    root = copy_graph(tmp_path, publish=True)
    gate_attest(root, A, n=1, footprint={"nodes": []})
    gate_attest(root, B, n=2, footprint={"nodes": []})
    gate_attest(root, ROOT_NODE, n=3, artifact_hash=proof_hash(root, ROOT_NODE), footprint=None)
    page = render_page(root)
    assert re.search(r'class="proof-note"[^>]*>[^<]*not yet measured', page)
