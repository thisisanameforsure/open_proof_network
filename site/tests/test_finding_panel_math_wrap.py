"""F04-T51 (Q50): a statement panel's opening formula wraps instead of being clipped.

Measured live on erdos-1094--h2 at 1440 px (2026-10-14): the panel's "What is claimed" headline and
each "Split into" hole row showed the math-first gloss's opening ``$$…$$`` block in KaTeX display
mode, which never breaks a line. In the ~390 px panel the formulas were 393 to 449 px wide, so the
right end, the statement's conclusion ``⟹ k ≤ K``, was cut off. Those two slots now give the block
to KaTeX as inline math under ``\\displaystyle`` (``$\\displaystyle X$``, marked ``.math-break``):
the same size and layout, but KaTeX breaks the line after a top-level relation or binary operator.
A formula with no break opportunity wider than the box (a ``\\left…\\right`` group) scrolls inside
its ``.math-break`` box, which math.js marks ``.math-overflows`` and the stylesheet gives a visible
scrollbar. Display math anywhere else in contributor prose is unchanged.

The browser test needs Playwright's Chromium (``uv run --frozen --with playwright pytest
site/tests/test_finding_panel_math_wrap.py``); without it that test skips, which proves nothing,
so the evidence runs it. The markup and stylesheet checks run in the fast tier.
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
import gloss_fixture as gf
import pytest
from harness import TARGET, copy_graph
from test_decompositions import HOLE_IDS, add_hole, merged_partial
from test_outline_links import page_of, panel
from test_products import ROOT_NODE

from opn_site import model, render

REPO = "https://github.com/example/graph"
#: erdos-1094--h2's gloss as it stands on the record: one line, breakable at its relations.
H2 = (
    "\\exists K\\ \\forall n,k\\in\\mathbb{N}:\\quad 0<k,\\ \\ k^2\\le n,\\ \\ "
    "\\operatorname{lpf}\\tbinom{n}{k} > \\lfloor n/k\\rfloor \\implies k\\le K"
)
#: erdos-1094's root gloss: a set-builder in \Bigl…\Bigr, which is not a group, so it breaks too.
ROOT_MATH = (
    "\\Bigl\\{(n,k)\\in\\mathbb{N}^2 \\;:\\; 0<k,\\ \\ 2k\\le n,\\ \\ "
    "\\operatorname{lpf}\\tbinom{n}{k} > \\max\\bigl(\\lfloor n/k\\rfloor,\\,k\\bigr)\\Bigr\\}"
    "\\ \\text{ is finite}"
)
#: No break opportunity at the top level: one \left…\right group wider than any panel.
UNBREAKABLE = "\\left(" + " + ".join(f"a_{{{i}}} b_{{{i}}}" for i in range(1, 19)) + "\\right)"
NOTE_MATH = "$$\\sum_{i=1}^{n} i = \\frac{n(n+1)}{2}$$"


def wrap_tree(tmp_path: Path) -> Path:
    """The root split into two holes; the root's and the first hole's glosses open with the live
    formulas, the second hole's with one that cannot break. The root's gloss carries a display
    block further down, which keeps display mode."""
    root = copy_graph(tmp_path, publish=True)
    add_hole(root, HOLE_IDS[0], "hden")
    add_hole(root, HOLE_IDS[1], "hrem")
    merged_partial(root, 7, ["hden", "hrem"], annex=None)
    gf.gloss(
        root,
        f"$${ROOT_MATH}$$\n\n- A note, with a display of its own:\n\n{NOTE_MATH}",
        kind="statement",
        node=ROOT_NODE,
        author="alice",
    )
    gf.gloss(
        root,
        f"$${H2}$$\n\n- Lean writes it otherwise.",
        kind="statement",
        node=HOLE_IDS[0],
        author="alice",
    )
    gf.gloss(root, f"$${UNBREAKABLE}$$", kind="statement", node=HOLE_IDS[1], author="alice")
    return root


def test_the_headline_and_split_rows_give_katex_breakable_inline_math(tmp_path: Path) -> None:
    page = page_of(wrap_tree(tmp_path))
    body = panel(page, ROOT_NODE)
    head = re.search(r'<div class="prose claim-math">(.*?)</div>', body, re.S)
    assert head is not None
    assert "$$" not in head.group(1), "the headline is still display math"
    assert '<span class="math math-break">$\\displaystyle \\Bigl' in head.group(1)
    rows = re.findall(r'<div class="prose split-gloss">(.*?)</div>', body, re.S)
    assert len(rows) == 2
    for row in rows:
        assert "$$" not in row, "a split row is still display math"
        assert '<span class="math math-break">$\\displaystyle ' in row
    # The hole's own panel leads with the same breakable form.
    hole = re.search(r'<div class="prose claim-math">(.*?)</div>', panel(page, HOLE_IDS[0]), re.S)
    assert hole is not None and "math-break" in hole.group(1) and "$$" not in hole.group(1)


def test_display_math_elsewhere_in_the_gloss_keeps_display_mode(tmp_path: Path) -> None:
    body = panel(page_of(wrap_tree(tmp_path)), ROOT_NODE)
    notes = re.search(r'<div class="prose claim-notes">(.*?)</div>', body, re.S)
    assert notes is not None
    assert '<span class="math">$$\\sum_{i=1}' in notes.group(1)
    assert "math-break" not in notes.group(1)


def test_a_gloss_shown_whole_opens_with_the_breakable_form(tmp_path: Path) -> None:
    # The record details show the current gloss whole, and a revised gloss's history shows each
    # version: each opens with the statement, so each is the breakable form (measured live: the
    # versions were cut off at 390 too, task-51.txt).
    root = wrap_tree(tmp_path)
    first = gf.gloss(
        root, f"$${H2}$$", kind="statement", node=HOLE_IDS[1], author="bob", date="2026-10-05"
    )
    gf.gloss(
        root,
        f"$${H2}\\ $$\n\nRevised.",
        kind="statement",
        node=HOLE_IDS[1],
        author="bob",
        supersedes=first,
        date="2026-10-06",
    )
    page = page_of(root)
    body = panel(page, HOLE_IDS[1])
    whole = re.findall(r'<div class="prose gloss-prose">(.*?)</div>', body, re.S)
    assert whole and all("$$" not in w.split("</p>")[0] for w in whole)
    versions = re.findall(
        r'<details class="version-text">.*?<div class="prose">(.*?)</div></details>', page, re.S
    )
    assert versions, "no version history on the page"
    for v in versions:
        assert v.startswith('<p><span class="math math-break">$\\displaystyle '), v[:80]


def test_the_breakable_form_escapes_like_any_math() -> None:
    out = render.breakable_opening('<p><span class="math">$$a &lt; b$$</span> then</p>')
    assert out == '<p><span class="math math-break">$\\displaystyle a &lt; b$</span> then</p>'
    # Only the opening block: a second display in the paragraph is left as display.
    two = '<p><span class="math">$$a$$</span> <span class="math">$$b$$</span></p>'
    assert render.breakable_opening(two) == (
        '<p><span class="math math-break">$\\displaystyle a$</span> '
        '<span class="math">$$b$$</span></p>'
    )
    # Not opening with display math: unchanged.
    assert render.breakable_opening('<p>Words <span class="math">$$a$$</span></p>') == (
        '<p>Words <span class="math">$$a$$</span></p>'
    )


def test_the_fallback_box_scrolls_with_a_visible_bar() -> None:
    css = (render.STATIC / "site.css").read_text(encoding="utf-8")
    m = re.search(r"(?m)^\.math-break \{([^}]*)\}", css)
    assert m is not None and "overflow-x: auto" in m.group(1) and "display: block" in m.group(1)
    assert re.search(r"\.math-overflows::-webkit-scrollbar \{[^}]*height", css)
    assert "math-overflows" in (render.STATIC / "math.js").read_text(encoding="utf-8")


#: Every rendered formula under ``sel`` that is shown: its drawn extent (the union of KaTeX's
#: line boxes, ``.katex-base``) against the content width of the block it sits in, and whether an
#: ancestor up to the panel scrolls sideways to show the rest.
OVERFLOW = """(sel) => {
  const root = document.querySelector(sel);
  if (!root) return [];
  const out = [];
  for (const k of root.querySelectorAll('.katex')) {
    if (k.parentElement.closest('.katex')) continue;
    if (!k.checkVisibility()) continue;  // a hidden panel, or inside a closed fold
    const bases = k.querySelectorAll('.katex-html > .base, .katex-html > .katex-base');
    if (!bases.length) continue;
    let l = Infinity, r = -Infinity;
    for (const b of bases) {
      const rc = b.getBoundingClientRect();
      if (!rc.width) continue;
      l = Math.min(l, rc.left); r = Math.max(r, rc.right);
    }
    let box = k.parentElement;
    while (box && (getComputedStyle(box).display.startsWith('inline')
                   || box.classList.contains('katex-display'))) box = box.parentElement;
    const cs = getComputedStyle(box);
    const inner = box.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    let scrolls = false;
    for (let a = k.parentElement; a && a !== root.parentElement; a = a.parentElement) {
      const ox = getComputedStyle(a).overflowX;
      if ((ox === 'auto' || ox === 'scroll') && a.scrollWidth > a.clientWidth) scrolls = true;
    }
    const fb = k.closest('.math-break');
    const ann = k.querySelector('annotation');
    out.push({
      width: Math.round(r - l), box: Math.round(inner), over: r - l > inner + 1, scrolls,
      fallback: !!(fb && fb.classList.contains('math-overflows')),
      tex: ann ? ann.textContent : '',
      slot: (k.closest('.claim-math, .split-gloss, .claim-notes, .prose, li') || {}).className
        || '',
    });
  }
  return out;
}"""


OPEN_FOLDS = "(sel) => document.querySelectorAll(sel + ' details').forEach(d => { d.open = true; })"


#: Each marked fallback box: the height its horizontal scrollbar takes (0 when none is drawn).
BARS = (
    "(sel) => [...document.querySelectorAll(sel + ' .math-overflows')]"
    ".filter(e => e.checkVisibility()).map(e => e.offsetHeight - e.clientHeight)"
)


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


def measure_panels(out: Path, nodes: list[str], widths: tuple[int, ...]) -> dict[str, Any]:
    sync_api = pytest.importorskip("playwright.sync_api")
    handler = functools.partial(Quiet, directory=str(out))
    found: dict[str, Any] = {}
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_address[1]}/problems/{TARGET}/"
        with sync_api.sync_playwright() as p:
            # Headless Chromium hides every scrollbar unless told not to; the bar is measured.
            b = p.chromium.launch(ignore_default_args=["--hide-scrollbars"])
            for width in widths:
                pg = b.new_page(viewport={"width": width, "height": 900})
                pg.goto(base)
                pg.wait_for_load_state("networkidle")
                for nid in nodes:
                    pg.goto(f"{base}#node={nid}")
                    sel = f'.panel[data-node="{nid}"]'
                    # Every fold open: the record details show the gloss whole, opening formula
                    # first.
                    pg.evaluate(OPEN_FOLDS, sel)
                    pg.wait_for_timeout(100)
                    found[f"{nid}@{width}"] = pg.evaluate(OVERFLOW, sel)
                    found[f"bars:{nid}@{width}"] = pg.evaluate(BARS, sel)
                pg.close()
            b.close()
    return found


def test_no_panel_formula_is_clipped_at_1440_or_390(tmp_path: Path) -> None:
    pytest.importorskip("playwright.sync_api")
    root = wrap_tree(tmp_path / "graph")
    page_of(root)  # writes the products
    out = tmp_path / "site"
    render.write(render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO), out)
    found = measure_panels(out, [ROOT_NODE, *HOLE_IDS], (1440, 390))
    bars = {k: found.pop(k) for k in list(found) if k.startswith("bars:")}
    assert all(found.values()), f"a panel showed no formula: {found}"
    for where, formulas in found.items():
        for f in formulas:
            if not f["over"]:
                continue
            # Only the formula that cannot break may be wider than its box, and then it scrolls
            # in its marked fallback box.
            assert "\\left(" in f["tex"], f"{where}: clipped {f}"
            assert f["fallback"] and f["scrolls"], f"{where}: not in the scrolling box {f}"
    # The live formulas fit whole: no scrolling needed to read their conclusions.
    for nid in (ROOT_NODE, HOLE_IDS[0]):
        for width in (1440, 390):
            heads = [
                f
                for f in found[f"{nid}@{width}"]
                if "\\exists K" in f["tex"] or "\\Bigl" in f["tex"]
            ]
            assert heads and not any(f["over"] for f in heads), (nid, width, heads)
    # And the unbreakable one did need its fallback, at both widths, with a bar drawn.
    for width in (1440, 390):
        assert any(f["over"] for f in found[f"{HOLE_IDS[1]}@{width}"])
        assert bars[f"bars:{HOLE_IDS[1]}@{width}"], "no marked box"
        assert all(h > 0 for h in bars[f"bars:{HOLE_IDS[1]}@{width}"]), bars
