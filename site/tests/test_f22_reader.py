"""F22-T18: what the 2026-10-06 reader (R1) needed and could not get (feature requests I, J, L-S).

A research mathematician who does not read Lean was asked how Erdős 1050 was resolved. The page
had the answer, but buried: the proof's words were three pages down a 34,000px reading view with
no contents, the problem page said nothing in words about how it was proved, every statement read
``:= by sorry``, the node page listed four dependencies when the proof uses one, the spec-* nodes
had no names, a steps column printed 22 Lean claims before a section's words, an escaped step id
(``h_x3a9div``) hid its Lean name (``hΩdiv``), explainer versions carried no date, and on a phone
the graph's labels were 6px and the page said "hover".
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path

import fixture
import gloss_fixture as gf
import pytest
import reading_fixture as rf
from harness import TARGET

from opn_gate import explainers
from opn_site import model, render

REPO = "https://github.com/example/graph"
OVERVIEW = "The root follows from the middle lemma, which reassociates; nothing else is needed."
EXPLAINER = (
    f"## Overview\n{OVERVIEW}\n\n## The one step {{steps: h2}}\nThe step names the middle lemma.\n"
)
DOCS_READING = "/docs/#reading"


def tree(tmp_path: Path) -> Path:
    """The chain tree, the root's proof explained, and the root's term using only the middle
    lemma, so its declared dependency on the tutorial is declared and not used."""
    root = rf.chain_tree(tmp_path)
    gf.explainer(root, rf.ROOT, EXPLAINER, author="alice", date="2026-10-05")
    fixture.attest(root, rf.ROOT, 3, footprint={"nodes": [rf.MIDDLE]})
    rf.write_products(root)
    return root


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> model.Site:
    return model.load_site(tree(tmp_path_factory.mktemp("reader")), fixture.COMMIT)


@pytest.fixture(scope="module")
def pages(site: model.Site) -> dict[str, str]:
    return render.render_site(site, repo_url=REPO)


def reading_page(pages: dict[str, str]) -> str:
    (key,) = [k for k in pages if k.startswith(f"problems/{TARGET}/proofs/")]
    return pages[key]


# --- M: the problem page says in words how it was proved ------------------------------------------


def test_the_problem_page_shows_the_root_proofs_overview_in_words(pages: dict[str, str]) -> None:
    page = pages[f"problems/{TARGET}/index.html"]
    head = "<h2>How it was proved (in words, unverified)</h2>"
    assert head in page
    section = page[page.index(head) :]
    section = section[: section.index("<h2", len(head))]
    assert OVERVIEW in section
    assert "The step names the middle lemma" not in section  # the overview, not every section
    assert "written by alice" in section and "2026-10-05" in section
    assert "Informal account, unverified" in section
    assert f'href="/nodes/{TARGET}/{rf.ROOT}/#explainer"' in section


def test_the_section_cites_the_records_sources_when_it_has_any(site: model.Site) -> None:
    tv = site.targets[TARGET]
    source = {
        "url": "https://doi.org/10.1016/0022-314X(91)90118-A",
        "attribution": "P. B. Borwein, J. Number Theory 37 (1991)",
        "licence": "citation",
        "quote_policy": "cite",
    }
    cited = dataclasses.replace(tv, record={**(tv.record or {}), "sources": [source]})
    html = render.Renderer(site, repo_url=REPO).proved_in_words(cited)
    assert "P. B. Borwein, J. Number Theory 37 (1991)" in html


# --- N: the reading view has contents and two orders ----------------------------------------------


def test_the_reading_view_has_a_table_of_contents_in_page_order(pages: dict[str, str]) -> None:
    page = reading_page(pages)
    nav = re.search(r'<nav class="rv-toc"[^>]*>(.*?)</nav>', page, re.S)
    assert nav is not None
    toc = re.findall(r'href="#rv-([^"]+)"', nav.group(1))
    shown = re.findall(r'<li class="rv-node" id="rv-([^"]+)"', page)
    assert toc == shown == [rf.TUTORIAL, rf.MIDDLE, rf.ROOT]


def test_the_reading_view_offers_root_first_without_changing_the_default(
    pages: dict[str, str],
) -> None:
    page = reading_page(pages)
    assert "<h2 data-order-heading>The proof, dependencies first</h2>" in page
    # Links, not buttons: the page takes no input (D-36), and a link that reorders it is not one.
    links = re.findall(r'<a class="chip" href="#rv-toc" data-order="([a-z]+)"', page)
    assert links == ["deps", "root"]
    assert '<div class="rv-order" hidden' in page  # shown by the script; no script, no buttons
    assert '<script src="/reading.js"></script>' in page
    assert "/reading.js" in render.SCRIPTS
    script = (render.STATIC / "reading.js").read_text(encoding="utf-8")
    assert "rv-nodes" in script and "rv-toc" in script


# --- O: which declared dependencies the proof uses ------------------------------------------------


def test_the_node_page_marks_which_dependencies_the_term_uses(pages: dict[str, str]) -> None:
    page = pages[f"nodes/{TARGET}/{rf.ROOT}/index.html"]
    deps = page[page.index('<div class="deps">') :]
    deps = deps[: deps.index("</div>")]
    items = dict(re.findall(r'<li><a href="/nodes/[^/]+/([^/]+)/">[^<]*</a>(.*?)</li>', deps, re.S))
    assert "used by the proof" in items[rf.MIDDLE]
    assert "declared; the proof does not use it" in items[rf.TUTORIAL]


# --- P, Q: the placeholder proof, and the way to the reading guide --------------------------------


@pytest.mark.parametrize(
    "rel",
    [f"problems/{TARGET}/index.html", f"nodes/{TARGET}/{rf.ROOT}/index.html", "reading"],
)
def test_every_statement_block_explains_its_sorry(pages: dict[str, str], rel: str) -> None:
    page = reading_page(pages) if rel == "reading" else pages[rel]
    blocks = re.findall(r'<pre class="lean statement[^"]*">.*?</pre>(.{0,400})', page, re.S)
    assert blocks
    for after in blocks:
        assert after.startswith('<p class="sorry-note">'), after[:120]
        assert "sorry" in after and "Proof.lean" in after
        assert f'href="{DOCS_READING}"' in after


def test_the_docs_reading_section_is_there_to_link(pages: dict[str, str]) -> None:
    assert 'id="reading"' in pages["docs/index.html"]


# --- R: phones ------------------------------------------------------------------------------------


def css() -> str:
    return (render.STATIC / "site.css").read_text(encoding="utf-8")


def media(width: int) -> str:
    """Every rule inside ``@media (max-width: <width>px)``, joined."""
    out = []
    text = css()
    for m in re.finditer(rf"@media \(max-width: {width}px\) \{{", text):
        depth, i = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        out.append(text[m.end() : i])
    return "\n".join(out)


def test_on_a_phone_the_words_come_before_the_steps() -> None:
    assert re.search(r"\.ex-prose\s*\{[^}]*order:\s*-1", media(700))


def test_on_a_phone_the_graph_keeps_its_size_and_scrolls() -> None:
    assert re.search(r"\.dag\s*\{[^}]*max-width:\s*none", media(700))


def test_touch_screens_read_tap_not_hover(pages: dict[str, str]) -> None:
    page = pages[f"problems/{TARGET}/index.html"]
    caption = re.search(r'<span class="dag-caption">(.*?)</span></div>', page, re.S)
    assert caption is not None
    assert '<span class="on-hover">hover</span><span class="on-touch">tap</span>' in caption.group(
        1
    )
    assert re.search(r"@media \(hover: none\)\s*\{[^}]*\.on-hover[^}]*display:\s*none", css())


# --- S: a spec node's theorem name ----------------------------------------------------------------


def test_a_spec_node_is_labelled_with_its_theorem_name(site: model.Site) -> None:
    tv = site.targets[TARGET]
    spec = "spec-0123abcd"
    nv = dataclasses.replace(tv.nodes[rf.MIDDLE], node_id=spec)
    tv.nodes[spec] = nv
    try:
        r = render.Renderer(site, repo_url=REPO)
        link = r.node_link(TARGET, spec)
        assert ">spec-0123abcd</a>" in link
        assert '<code class="thm-name">OpnProp.and_reassoc</code>' in link
        assert "thm-name" not in r.node_link(TARGET, rf.MIDDLE)  # only the unnamed ids
    finally:
        del tv.nodes[spec]


# --- I, J: the steps column -----------------------------------------------------------------------


def section_html(steps: dict[str, dict[str, object]]) -> str:
    r = render.Renderer.__new__(render.Renderer)
    sec = explainers.Section(heading="A section", steps=tuple(steps), text="Words.")
    return r.explainer_section(sec, steps, key="k", linked=False)


def step(sid: str, name: str | None = None) -> dict[str, object]:
    return {"id": sid, "kind": "have", "name": name, "claim": None}


def test_more_than_six_steps_fold() -> None:
    many = section_html({f"s{i}": step(f"s{i}") for i in range(7)})
    assert '<details class="ex-steps-fold"><summary>7 steps</summary>' in many
    few = section_html({f"s{i}": step(f"s{i}") for i in range(6)})
    assert "<details" not in few


def test_an_escaped_step_id_shows_its_lean_name() -> None:
    html = section_html({"hcore.h_x3a9div": step("hcore.h_x3a9div", "hΩdiv")})
    assert '<code>hcore.h_x3a9div</code> <span class="po-name">(<code>hΩdiv</code>)</span>' in html
    plain = section_html({"T_facts.hpos.s1": step("T_facts.hpos.s1", "this")})
    assert "po-name" not in plain  # an unescaped id is its name already, or names a placeholder


# --- L: a date on each explainer version ----------------------------------------------------------


def test_each_explainer_version_carries_its_date(tmp_path: Path) -> None:
    root, _ = gf.sectioned_tree(tmp_path)
    pages = render.render_site(model.load_site(root, gf.COMMIT), repo_url=REPO)
    page = pages[f"nodes/{TARGET}/{gf.TUTORIAL}/index.html"]
    labels = re.findall(r'<p class="label">Unverified: explainer, its words from (.*?)</p>', page)
    assert labels
    for label in labels:
        versions = label.count('<a class="file"')
        assert versions and len(re.findall(r"\b20\d\d-\d\d-\d\d\b", label)) == versions, label


# --- the Docs section names what a reader now sees ------------------------------------------------


def test_the_docs_reading_section_explains_the_new_things(pages: dict[str, str]) -> None:
    docs = pages["docs/index.html"]
    section = docs[docs.index('id="reading"') : docs.index('id="glossary"')]
    for words in ("contents", "root first", "by sorry", "does not use", "tap"):
        assert words in section, words
