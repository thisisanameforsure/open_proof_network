"""F04-T49 (Q48): at phone width the problem page does not scroll sideways, and Lean keeps its
indentation.

On the live erdos-1094 page at 390 px the document was 779 px wide. T47's note blamed the statement
graph; measured element by element (task-49.txt) it is one link: the source URL in "Where the
statement comes from" (``ul.sources``), a 98-character URL with no break opportunity, 57 to 779
px. The graph keeps its drawn size on phones inside ``.dag-scroll``, which already scrolls on its
own and never widened the page; that stays guarded here with a graph drawn wider than a phone.
And the panel's Lean wrapped (``pre-wrap``, ``overflow-wrap: anywhere``), so a long hypothesis
broke mid-token and a partial proof's indentation bent at 390; now a panel's Lean scrolls inside
its block with its lines intact.

The browser test needs Playwright's Chromium (``uv run --frozen --with playwright pytest
site/tests/test_finding_mobile_scroll.py``); without it the test skips, which proves nothing, so
the evidence runs it. The stylesheet checks run in the fast tier.
"""

from __future__ import annotations

import functools
import http.server
import re
import socketserver
import threading
from pathlib import Path
from typing import Any

import fixture
import pytest
from harness import TARGET, copy_graph
from test_decompositions import add_hole
from test_products import ROOT_NODE, nodes_dir

from opn_gate import products
from opn_site import model, render

REPO = "https://github.com/example/graph"
#: Enough holes side by side that the graph is drawn wider than a phone.
WIDE = [f"{ROOT_NODE}--h{n}" for n in range(1, 9)]
LONG = (
    "theorem long_line : " + " ∧ ".join(f"(p{n} \\/ q{n})" for n in range(30)) + " := by\n  sorry\n"
)


def wide_tree(tmp_path: Path) -> Path:
    root = copy_graph(tmp_path, publish=True)
    for k, child in enumerate(WIDE):
        add_hole(root, child, f"h{k}")
    # A long statement line for the first hole's panel (its Lean is shown: no gloss).
    (nodes_dir(root) / WIDE[0] / "Statement.lean").write_text(LONG, encoding="utf-8")
    return root


def css_rule(selector: str) -> str:
    text = (render.STATIC / "site.css").read_text(encoding="utf-8")
    m = re.search(rf"(?m)^{re.escape(selector)} \{{([^}}]*)\}}", text)
    assert m is not None, selector
    return m.group(1)


def phone_rules() -> str:
    """Every rule inside ``@media (max-width: 700px)``, joined."""
    text = (render.STATIC / "site.css").read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r"@media \(max-width: 700px\) \{", text):
        depth, i = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        out.append(text[m.end() : i])
    return "\n".join(out)


def test_a_panels_lean_scrolls_in_its_block_on_a_phone() -> None:
    m = re.search(r"\.panel pre\.lean \{([^}]*)\}", phone_rules())
    assert m is not None, "no phone rule for a panel's Lean"
    assert "white-space: pre;" in m.group(1) and "overflow-x: auto" in m.group(1)
    assert "overflow-wrap: normal" in m.group(1)


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


#: A source URL as long as erdos-1094's, with no break opportunity in it.
LONG_URL = (
    "https://github.com/google-deepmind/formal-conjectures/blob/"
    "c7f31d5fd3d2ca3d69979f2d213eb9b58fe956ae/FormalConjectures/ErdosProblems/1094.lean"
)


def test_a_source_link_breaks_rather_than_widening_the_page() -> None:
    # The same at riemann-hypothesis (611 px): the catalog evidence's label names a 64-character
    # declaration in one code span, and a reason names a 45-character Mathlib path.
    assert "overflow-wrap: anywhere" in css_rule("ul.sources, .evidence .label, .evidence li")


def serve_and_measure(out: Path, path: str, script: str) -> Any:
    sync_api = pytest.importorskip("playwright.sync_api")
    handler = functools.partial(Quiet, directory=str(out))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        with sync_api.sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 390, "height": 900})
            pg.goto(f"http://127.0.0.1:{srv.server_address[1]}{path}")
            pg.wait_for_load_state("networkidle")
            value = pg.evaluate(script)
            b.close()
    return value


def test_no_sideways_page_scroll_at_390_with_a_long_source_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("playwright.sync_api")
    monkeypatch.setitem(fixture.UNLICENSED, "url", LONG_URL)
    root = fixture.build_with_listed_target(tmp_path / "graph")
    out = tmp_path / "site"
    render.write(render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO), out)
    width = serve_and_measure(
        out,
        f"/problems/{fixture.LISTED_TARGET}/",
        "document.documentElement.scrollWidth",
    )
    assert width == 390, f"the page scrolls sideways: {width}"


def test_the_graph_and_the_lean_scroll_in_their_own_boxes_at_390(tmp_path: Path) -> None:
    pytest.importorskip("playwright.sync_api")
    import yaml  # noqa: PLC0415

    from opn_gate import schemas  # noqa: PLC0415

    root = wide_tree(tmp_path)
    # The statement edit changes its hash; the META follows, as a curator's revision would.
    meta = nodes_dir(root) / WIDE[0] / "META.yaml"
    doc = yaml.safe_load(meta.read_text())
    doc["statement-hash"] = schemas.content_hash(
        (nodes_dir(root) / WIDE[0] / "Statement.lean").read_bytes()
    )
    meta.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    out = tmp_path / "site"
    render.write(render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO), out)
    page, graph, lean = serve_and_measure(
        out,
        f"/problems/{TARGET}/#node={WIDE[0]}",
        "(() => { const s = document.querySelector('.dag-scroll');"
        f" const e = document.querySelector('.panel[data-node=\"{WIDE[0]}\"] pre.lean.statement');"
        " return [document.documentElement.scrollWidth, [s.scrollWidth, s.clientWidth],"
        " [e.scrollWidth, e.clientWidth, getComputedStyle(e).whiteSpace]]; })()",
    )
    assert page == 390, f"the page scrolls sideways: {page}"
    assert graph[0] > graph[1], f"the graph is not wider than its box here: {graph}"
    assert lean[2] == "pre", lean
    assert lean[0] > lean[1], f"the long Lean line does not scroll in its block: {lean}"


# -- F04-T52 (Q51): the review's state pill wraps rather than widening the page -----------------
#
# F26-T12 put "review: needs an intent signer · 1 candidate, 1 cluster, 8 questions waiting" in
# the problem page's header row as a ``.tag``, and ``.tag`` is ``white-space: nowrap``, so at 390
# the pill reached x=450 and 25 of the 27 live problem pages scrolled sideways (task-52.txt).

#: The longest state the words can take: needs-intent-signer with two-digit counts.
LONG_REVIEW = {
    "state": "needs-intent-signer",
    "candidates": 12,
    "clusters": 10,
    "questions_waiting": 16,
}


def test_the_review_pill_may_wrap_and_the_status_pills_may_not() -> None:
    assert "white-space: normal" in css_rule(".review-state")
    # The short pills keep their one line: the base rule is untouched.
    assert "white-space: nowrap" in css_rule(".tag")


def test_no_sideways_page_scroll_at_390_with_a_review_state_pill(tmp_path: Path) -> None:
    pytest.importorskip("playwright.sync_api")
    root = fixture.build_with_review(tmp_path / "graph")
    fixture.publish_review_state(root, LONG_REVIEW)
    out = tmp_path / "site"
    render.write(render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO), out)
    page, pill, tags = serve_and_measure(
        out,
        f"/problems/{TARGET}/",
        "(() => { const r = document.querySelector('.problem-id-row .review-state')"
        ".getBoundingClientRect();"
        " const tags = [...document.querySelectorAll('.problem-id-row .tag')]"
        ".map(e => Math.round(e.getBoundingClientRect().right));"
        " return [document.documentElement.scrollWidth, [r.left, r.right], tags]; })()",
    )
    assert page == 390, f"the page scrolls sideways: {page}"
    assert pill[0] >= 0 and pill[1] <= 390, f"the review pill leaves the viewport: {pill}"
    assert all(right <= 390 for right in tags), f"a header pill leaves the viewport: {tags}"
