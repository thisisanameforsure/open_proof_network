"""F04-T21 (Q23): the Docs page draws how a statement and a problem change state, and names
the action behind each arrow.

The drawings are documentation of the gate, so the tests hold them to the gate's own vocabulary:
every status ``graph.json`` can publish is a box in the statement drawing (as the site's word),
every status ``target-status`` can declare is a box in the problem drawing, and every pull-request
mode the classifier knows is named in the actions table. A status or a mode added to the gate
turns this red until the page says what it does.
"""

from __future__ import annotations

import json
import re
import typing
from pathlib import Path

import fixture
import pytest

import opn_gate
from opn_gate import graph, modes
from opn_site import model, render

REPO = "https://github.com/example/graph"
SCHEMAS = Path(opn_gate.__file__).resolve().parents[1] / "schemas"


@pytest.fixture(scope="module")
def docs(tmp_path_factory: pytest.TempPathFactory) -> str:
    root = fixture.build(tmp_path_factory.mktemp("graph"))
    site = model.load_site(root, fixture.COMMIT)
    r = render.Renderer(site, repo_url=REPO, decisions_doc=None)
    page, _extra = r.docs()
    return page


def section(docs: str) -> str:
    start = docs.index('<h2 id="states">')
    return docs[start : docs.index('<h2 id="glossary">')]


def drawings(html: str) -> list[str]:
    return re.findall(r'<svg class="smap"[^>]*>.*?</svg>', html, re.S)


def names(svg: str) -> set[str]:
    return set(re.findall(r'<text class="name"[^>]*>([^<]+)</text>', svg))


def test_the_section_sits_before_the_glossary_and_is_self_contained(docs: str) -> None:
    """R10: inline SVG, no script or style of its own; before the words it explains."""
    html = section(docs)
    assert html.index("<h3>A statement</h3>") < html.index("<h3>A problem</h3>")
    assert html.index("<h3>A problem</h3>") < html.index("<h3>What an action is</h3>")
    assert "<script" not in html and "<style" not in html and 'href="http' not in html
    assert len(drawings(html)) == 2
    for svg in drawings(html):
        assert 'role="img"' in svg and 'aria-label="State diagram of a' in svg


def test_the_statement_drawing_shows_every_status_the_products_can_publish(docs: str) -> None:
    """graph/v3's status enum is ``graph.ALL_STATUSES``; each is a box, as the site's word
    (F03-Q8: speculative reads open, and the drawing says so in the protocol's words)."""
    statement, _problem = drawings(section(docs))
    expected = {"open" if s in render.CLAIMABLE_STATUSES else s for s in graph.ALL_STATUSES}
    # F04-T17: a hole waiting only for its witness is "needs a witness", not blocked.
    expected.add(render.STATE_LABELS[render.NEEDS_WITNESS])
    assert names(statement) == expected
    assert "ready · speculative" in statement  # the protocol words under the open box
    assert statement.count(">blocked</text>") == 1  # a wait on a dependency
    assert "witness-missing" in statement and "dep-refuted" in statement
    # D-12 v3.19 (F07-R22): nothing moves an open statement to blocked; a route leaves it open.
    assert "its holes become its dependencies" not in statement
    assert "stays open" in statement and "v3.19" in statement


def test_the_problem_drawing_shows_every_status_a_target_can_declare(docs: str) -> None:
    latest = sorted((SCHEMAS / "target-status").glob("v*.json"), key=lambda p: int(p.stem[1:]))[-1]
    enum = json.loads(latest.read_text(encoding="utf-8"))["properties"]["status"]["enum"]
    _statement, problem = drawings(section(docs))
    assert names(problem) == set(enum)
    for state in ("undigested", "explained", "written up"):
        assert f">{state}</text>" in problem  # D-33 v3.17's digestion strip


def test_each_key_item_is_the_site_hover_card_for_that_word(docs: str) -> None:
    """The keys reuse ``term`` and the Problems page's status tag, so a definition has one home
    (Q14): the statement key names every status the graph key can show, with its dot; the
    problem key names the five words a problem's tag can wear, with the tag's own text."""
    html = section(docs)
    keys = re.findall(r'<div class="smap-key">(.*?)</div>', html, re.S)
    assert len(keys) == 2
    statement_key, problem_key = keys
    dot_item = r'<span class="dot dot-([a-z-]+)"></span>([a-z ]+)<span class="term-card"'
    dots = re.findall(dot_item, statement_key)
    assert [d for d, _ in dots] == list(render.STATE_MAP_STATEMENT_KEYS)
    assert {d for d, _ in dots} == set(render.DOTTED_KEYS) | set(render.LEGEND_EXTRA)
    for key in render.STATE_MAP_STATEMENT_KEYS:
        _word, meaning, proto = render.GLOSSARY_BY_KEY[key]
        assert render.esc(meaning) in statement_key and render.esc(proto) in statement_key
    tag_item = r'<span class="term tag" tabindex="0">([a-z ]+)<span class="term-card"'
    words = re.findall(tag_item, problem_key)
    assert words == list(render.STATE_MAP_PROBLEM_KEYS)
    assert set(words) == set(render.PROBLEM_STATUS_DEFS)
    for word in words:
        assert render.esc(render.PROBLEM_STATUS_DEFS[word]) in problem_key


def test_the_actions_table_names_every_mode_the_classifier_knows(docs: str) -> None:
    """A pull request is classified into exactly one mode (F07-R3); the table says what each
    one moves, so a mode added to ``modes.Mode`` turns this red until the page does."""
    html = section(docs)
    table = html.split('<table class="actions">', 1)[1].split("</table>", 1)[0]
    for mode in typing.get_args(modes.Mode):
        assert f"<code>{mode}</code>" in table, mode
    commands = (
        "revise",
        "consolidate",
        "status &lt;node&gt; abandoned",
        "status &lt;target&gt; dormant",
    )
    for command in commands:
        assert command in table, command


def test_the_derivation_order_is_the_gates(docs: str) -> None:
    """The four rules read in ``graph.derive_statuses``' order: record, artifact, blocked, ready."""
    html = section(docs)
    rules = re.findall(r"<li><strong>(.*?)</strong>", html.split("</ol>", 1)[0])
    assert [r.split()[0] for r in rules] == ["The", "Else", "Else", "Else"]
    assert "status record wins" in rules[0] and "artifact" in rules[1]
    assert "blocked" in rules[2] and "open" in rules[3]
    first_rule = html.split("</li>", 1)[0]
    for status in graph.RECORD_STATUSES:
        assert f"<code>{status}</code>" in first_rule, status
