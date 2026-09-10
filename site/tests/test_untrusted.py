"""F04 untrusted content beyond AC2/AC3 (R3, R4; C9): every field from the graph that reaches
a page, in text and attribute context, with the injection strings a hostile contributor would
write. AC2 covers the explainer body and an annex; these cover everything else.
"""

from __future__ import annotations

import dataclasses
import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import fixture
import pytest

from opn_gate import schemas
from opn_site import model, prose, render

REPO = "https://github.com/example/graph"
TARGET = "propositional"
NODES = ("and-reassoc", "and-swap-reassoc", "tutorial-and-swap")
PAYLOAD = '<script>alert(1)</script>"onmouseover="x"'
ESCAPED = "&lt;script&gt;alert(1)&lt;/script&gt;&quot;onmouseover=&quot;x&quot;"


def _node_dir(root: Path, node_id: str) -> Path:
    return root / "targets" / TARGET / "nodes" / node_id


def _render(root: Path) -> dict[str, str]:
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)


class _Tags(HTMLParser):
    """Every tag the browser would see, with its attributes: escaped text never appears here."""

    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, dict(attrs)))


def _assert_clean(page: str) -> None:
    """Parsed as a browser would: no script or img element, no event-handler attribute, and no
    href or src with an active scheme survives anywhere on the page."""
    p = _Tags()
    p.feed(page)
    for tag, attrs in p.tags:
        assert tag not in ("img", "iframe", "object", "embed"), (tag, attrs)
        assert tag != "script" or attrs == {"src": "/frontier.js"}, attrs
        assert not any(k.lower().startswith("on") for k in attrs), (tag, attrs)
        for k in ("href", "src"):
            v = (attrs.get(k) or "").strip().lower()
            assert not v.startswith(("javascript:", "data:", "vbscript:")), (tag, attrs)


# --- prose front matter (R4: author and drafting model are contributor-written) ------------------


def test_front_matter_author_model_and_date_are_escaped(tmp_path: Path) -> None:
    root = fixture.build(tmp_path)
    explainer = _node_dir(root, "tutorial-and-swap") / "explainer" / "why.md"
    explainer.write_text(
        f"---\nauthor: {PAYLOAD}\nmodel: <img src=x onerror=alert(2)>\ndate: 2026 & later\n---\n"
        "Body.\n",
        encoding="utf-8",
    )
    page = _render(root)["nodes/propositional/tutorial-and-swap/index.html"]
    _assert_clean(page)
    assert "<img" not in page
    # parse_prose strips one layer of surrounding quotes from a value; what is left is escaped.
    assert f"by {render.esc(PAYLOAD.strip(chr(34)))}" in page
    assert "drafted with &lt;img src=x onerror=alert(2)&gt;" in page
    assert "2026 &amp; later" in page


def test_front_matter_only_reads_the_three_known_keys(tmp_path: Path) -> None:
    """A contributor cannot smuggle extra metadata into the label: unknown keys are dropped and
    a quoted value loses only its quotes."""
    p = tmp_path / "why.md"
    p.write_text(
        "---\nauthor: 'alice'\ntitle: <b>Boss</b>\nmodel: \"m\"\n---\nText\n", encoding="utf-8"
    )
    got = model.parse_prose(p, tmp_path)
    assert got == model.Prose(path="why.md", text="Text\n", author="alice", model="m", date=None)


def test_unclosed_front_matter_is_body_text(tmp_path: Path) -> None:
    """A `---` that never closes is not metadata; it is shown, escaped, as the text it is."""
    p = tmp_path / "why.md"
    p.write_text("---\nauthor: <x>\nnever closed\n", encoding="utf-8")
    got = model.parse_prose(p, tmp_path)
    assert got.author is None and got.text.startswith("---\n")
    assert prose.render(got.text) == "<p>--- author: &lt;x&gt; never closed</p>"


def test_crlf_front_matter_is_read_like_lf(tmp_path: Path) -> None:
    """Windows line endings are normalised on read, so the front matter still parses and its
    values are still untrusted text; nothing is dropped."""
    p = tmp_path / "why.md"
    p.write_bytes(b"---\r\nauthor: <x>\r\n---\r\nBody <y>\r\n")
    got = model.parse_prose(p, tmp_path)
    assert got.author == "<x>" and got.text == "Body <y>\n"
    assert render.esc(got.author) == "&lt;x&gt;"
    assert prose.render(got.text) == "<p>Body &lt;y&gt;</p>"


# --- the target page: note.md and approach file names ---------------------------------------------


def test_state_of_the_problem_note_is_escaped_in_an_untrusted_block(tmp_path: Path) -> None:
    root = fixture.build(tmp_path)
    (root / "targets" / TARGET / "note.md").write_text(f"Note {PAYLOAD}\n", encoding="utf-8")
    page = _render(root)["targets/propositional/index.html"]
    _assert_clean(page)
    block = page[page.index('<div class="prose-block untrusted">') :]
    assert "Untrusted: state-of-the-problem note (D-32)" in block
    assert block.index("Rendered from") < block.index(ESCAPED)


def test_approach_file_names_are_escaped_in_href_and_label(tmp_path: Path) -> None:
    """An approach record's file name lands in an attribute and in text; both are escaped and
    the link still points inside the graph repository, never at another origin."""
    root = fixture.build(tmp_path)
    approaches = root / "targets" / TARGET / "approaches"
    approaches.mkdir()
    # No path separator: that is the one character a file name cannot carry.
    (approaches / 'x"><script>alert(1)<script>.yaml').write_text("kind: x\n", encoding="utf-8")
    (approaches / "javascript:alert(2).yaml").write_text("kind: x\n", encoding="utf-8")
    page = _render(root)["targets/propositional/index.html"]
    _assert_clean(page)
    assert (
        f'href="{REPO}/blob/{fixture.COMMIT}/targets/propositional/approaches/'
        'x&quot;&gt;&lt;script&gt;alert(1)&lt;script&gt;.yaml"' in page
    )
    assert 'href="javascript:' not in page
    assert '/approaches/javascript:alert(2).yaml"' in page  # inside the repo URL, inert


# --- the node page: acknowledgments, attestation reviewer, unknown status ------------------------


def test_acknowledgment_fields_are_escaped(tmp_path: Path) -> None:
    """R4: an acknowledgment's checker, location and justification are contributor text."""
    root = fixture.build(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    nv = site.targets[TARGET].nodes["and-reassoc"]
    ack = {"checker": PAYLOAD, "location": "<b>loc</b>", "justification": f"because {PAYLOAD}"}
    nv = dataclasses.replace(nv, acknowledgments=(ack,))
    page = render.Renderer(site, repo_url=REPO, decisions_doc=None).node(nv)
    _assert_clean(page)
    assert "<b>loc</b>" not in page and "&lt;b&gt;loc&lt;/b&gt;" in page
    assert f"<code>{ESCAPED}</code>" in page
    assert f"<p>because {ESCAPED}</p>" in page
    assert '<div class="prose-block untrusted"><p class="label">Untrusted: acknowledgment' in page


def test_attestation_reviewer_and_review_kind_are_escaped(tmp_path: Path) -> None:
    """The reviewer id and review kind come from a graph file; the three review shapes all
    render escaped (R5)."""
    root = fixture.build(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    r = render.Renderer(site, repo_url=REPO, decisions_doc=None)
    nv = site.targets[TARGET].nodes["tutorial-and-swap"]
    assert nv.attestation is not None
    cases: list[tuple[dict[str, Any] | None, str]] = [
        ({"kind": "pr-approval", "reviewer": PAYLOAD, "reference": None}, ESCAPED),
        ({"kind": f"certified {PAYLOAD}", "reviewer": None}, f"none needed (certified {ESCAPED})"),
        (None, "not recorded"),
    ]
    for review, expected in cases:
        doc = {**nv.attestation, "review": review}
        page = r.node(dataclasses.replace(nv, attestation=doc))
        _assert_clean(page)
        assert f"<dt>Reviewer</dt><dd>{expected}</dd>" in page


def test_attestation_step_fields_are_escaped(tmp_path: Path) -> None:
    """Step names and results are graph data too; a result lands in a class attribute."""
    root = fixture.build(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    nv = site.targets[TARGET].nodes["tutorial-and-swap"]
    assert nv.attestation is not None
    steps = [{"step": "<1>", "name": PAYLOAD, "result": 'pass" onclick="x', "diagnostic": None}]
    page = render.Renderer(site, repo_url=REPO, decisions_doc=None).node(
        dataclasses.replace(nv, attestation={**nv.attestation, "steps": steps})
    )
    _assert_clean(page)
    assert 'onclick="x"' not in page
    assert '<td class="result-pass&quot; onclick=&quot;x">' in page
    assert f"<td>&lt;1&gt;</td><td>{ESCAPED}</td>" in page


def test_unknown_status_falls_back_to_the_escaped_raw_word() -> None:
    """A status outside STATUS_WORDS (an older or newer product) is shown as itself, escaped, in
    both the class attribute and the text."""
    mark = render.Renderer.status_mark('weird"><i>x')
    assert "<i>" not in mark
    assert 'class="status status-weird&quot;&gt;&lt;i&gt;x"' in mark
    assert mark.endswith("weird&quot;&gt;&lt;i&gt;x</span>")


def test_template_dollar_signs_in_graph_content_survive(tmp_path: Path) -> None:
    """Pages are string.Template substitutions; `$` in a statement or prose must not be
    interpreted as a placeholder or raise."""
    root = fixture.build(tmp_path)
    node = _node_dir(root, "and-reassoc")
    statement = (node / "Statement.lean").read_text(encoding="utf-8")
    statement = statement.replace("sorry", "sorry -- $title ${body} $$")
    (node / "Statement.lean").write_text(statement, encoding="utf-8")
    (node / "Proof.lean").unlink()
    import yaml  # noqa: PLC0415

    meta = yaml.safe_load((node / "META.yaml").read_text())
    meta["statement-hash"] = schemas.content_hash(statement.encode("utf-8"))
    (node / "META.yaml").write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    (node / "explainer" / "e.md").write_text("Costs $5 and ${more}.\n", encoding="utf-8")
    from opn_gate import products  # noqa: PLC0415

    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    page = _render(root)["nodes/propositional/and-reassoc/index.html"]
    assert "-- $title ${body} $$" in page
    assert "<p>Costs $5 and ${more}.</p>" in page


# --- ledger, docs page files ---------------------------------------------------------------------


def test_ledger_free_text_fields_are_escaped(tmp_path: Path) -> None:
    """R8: `tooling` and `artifact` are free strings in ledger/v1; `artifact` also becomes part
    of a file link's href, so a traversal there stays inside the repository URL."""
    root = fixture.build(tmp_path)
    doc = {
        "schema": "ledger/v1",
        "identity": "mallory",
        "entries": [
            {
                "line": "proof",
                "target": TARGET,
                "node": "and-reassoc",
                "artifact": f"../../{PAYLOAD}",
                "merge_commit": "1" * 40,
                "date": "2026-09-10T12:00:00Z",
                "tooling": PAYLOAD,
                "status": "revoked",
            }
        ],
    }
    (root / "ledger").mkdir()
    (root / "ledger" / "mallory.json").write_bytes(schemas.canonical_json(doc))
    page = _render(root)["contributors/index.html"]
    _assert_clean(page)
    assert f"<td>{ESCAPED}</td>" in page  # tooling, text context
    prefix = f'href="{REPO}/blob/{fixture.COMMIT}/targets/propositional/nodes/and-reassoc/'
    assert f"{prefix}../../" in page
    assert 'class="status status-revoked">revoked</span>' in page


@pytest.mark.parametrize("name", ["AGENTS.md", "LICENSE", "DCO"])
def test_docs_page_graph_files_are_escaped(name: str, tmp_path: Path) -> None:
    """R9: AGENTS.md, LICENSE and DCO are graph files, shown escaped; AGENTS.md is prose in an
    untrusted block, the other two are preformatted."""
    root = fixture.build(tmp_path)
    (root / name).write_text(f"{name} text {PAYLOAD}\n", encoding="utf-8")
    page = _render(root)["docs/index.html"]
    _assert_clean(page)
    assert ESCAPED in page
    if name == "AGENTS.md":
        assert "Untrusted: AGENTS.md" in page
    else:
        assert f'<h3>{name}</h3><pre class="prose">{name} text {ESCAPED}\n</pre>' in page
    assert f"{REPO}/blob/{fixture.COMMIT}/{name}" in page


# --- the frontier page: free-text fields inside otherwise patterned entries -----------------------


def test_frontier_free_text_cells_are_escaped(tmp_path: Path) -> None:
    """The frontier schema patterns ids and hashes but not library tags, failure-class keys or
    active claim ids; each is rendered escaped, and None/bools take fixed words."""
    root = fixture.build(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    entry = dict(site.frontier["entries"][0])
    entry["tags"] = {"deps": [], "library": [PAYLOAD]}
    entry["failure_class_histogram"] = {PAYLOAD: 1}
    entry["claims"] = {"active": [PAYLOAD], "history_count": 0}
    entry["ready_since"] = None
    entry["bounty"] = True
    doc = dict(site.frontier, entries=[entry])
    page = render.Renderer(
        dataclasses.replace(site, frontier=doc), repo_url=REPO, decisions_doc=None
    ).frontier()
    _assert_clean(page)
    assert f"library: {ESCAPED}" in page
    assert f"{ESCAPED} 1" in page
    assert "<td>1 active, 0 past</td>" in page and PAYLOAD not in page
    assert "<td>none</td>" in page and "<td>yes</td>" in page


# --- the prose renderer's edges (Q2) --------------------------------------------------------------


def test_prose_fence_variants() -> None:
    """A fence with a language tag or leading spaces still opens; inside a fence, whitespace and
    indentation are preserved; a fence marker mid-line is not a fence."""
    out = prose.render("```lean\n  theorem x : 1 < 2 := by\n    decide\n```\n")
    assert out == "<pre><code>  theorem x : 1 &lt; 2 := by\n    decide</code></pre>"
    assert prose.render("   ```\ncode\n   ```") == "<pre><code>code</code></pre>"
    assert prose.render("not a ``` fence") == "<p>not a ``` fence</p>"
    assert prose.render("   \n\n  \n") == ""


def test_prose_escapes_quotes_and_leaves_no_raw_markup() -> None:
    """Attribute-breaking characters are escaped in paragraphs and in fences alike."""
    text = 'a "quoted" \'single\' & <tag attr="v"> line\n\n```\n"</code><script>"\n```\n'
    out = prose.render(text)
    assert "<tag" not in out and "<script>" not in out and '"' not in out.replace('""', "")
    assert "&quot;quoted&quot; &#x27;single&#x27; &amp; &lt;tag attr=&quot;v&quot;&gt;" in out
    assert "<pre><code>&quot;&lt;/code&gt;&lt;script&gt;&quot;</code></pre>" in out


def test_prose_preserves_unicode_and_collapses_only_line_breaks() -> None:
    out = prose.render("∀ ε > 0,\n∃ δ > 0\n\nnext")
    assert out == "<p>∀ ε &gt; 0, ∃ δ &gt; 0</p>\n<p>next</p>"


# --- the commit string and the whole-page invariant ---------------------------------------------


def test_commit_string_is_escaped_in_href_and_text(tmp_path: Path) -> None:
    """The commit is a cli argument, not graph data, but it lands in every page's footer href;
    a hostile value cannot break out of the attribute."""
    root = fixture.build(tmp_path)
    site = model.load_site(root, 'abc"><script>alert(1)</script>')
    page = render.Renderer(site, repo_url=REPO, decisions_doc=None).home()
    _assert_clean(page)
    assert 'href="https://github.com/example/graph/tree/abc&quot;&gt;&lt;script&gt;' in page


def test_no_page_contains_the_raw_payload_anywhere(tmp_path: Path) -> None:
    """One payload in every contributor-writable place at once; no generated page carries it
    raw, in any context."""
    root = fixture.build(tmp_path)
    for node_id in NODES:
        d = _node_dir(root, node_id)
        (d / "explainer" / "z.md").write_text(f"---\nauthor: {PAYLOAD}\n---\n{PAYLOAD}\n")
        (d / "annex" / "z.md").write_text(PAYLOAD)
    (root / "targets" / TARGET / "note.md").write_text(PAYLOAD)
    for name in ("AGENTS.md", "LICENSE", "DCO"):
        (root / name).write_text(PAYLOAD)
    files = _render(root)
    for rel, content in files.items():
        if rel.endswith(".html") and rel != "docs/architecture-decisions.html":
            assert PAYLOAD not in content, rel
            assert 'onmouseover="x"' not in content, rel
    assert json.loads((root / "frontier.json").read_text())["entries"]  # the graph still had one
