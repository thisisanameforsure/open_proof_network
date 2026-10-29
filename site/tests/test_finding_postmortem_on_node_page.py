"""F04-T62 (Q60): a postmortem's words are on its node's page.

Found 2026-10-29 after three agents filed nine postmortems on erdos-849: the node page counted
them under Attempts and showed none of their text. A postmortem reached the page only through
the partial it names (route, outcome and classes, never ``detail``), and 15 of the 16 on the
live target name none. ``detail`` is where a contributor says what was ruled out and what to try
next, so the record's account of a dead end was readable through the MCP and invisible to a
person. Each valid postmortem now renders under Attempts as untrusted prose with its typed
fields, newest first; a partial's own block is unchanged.
"""

from __future__ import annotations

import re
from pathlib import Path

import fixture
import samples
import yaml

from opn_gate import products
from opn_site import model, render

REPO = "https://github.com/example/graph"
PARENT = "and-swap-reassoc"
STANDALONE = "20261029T160207Z-t1029e-a.yaml"
OLDER = "20261027T120000Z-t1027e-b.yaml"
DETAIL = "Only an effective result can narrow this; Nagura then Schoenfeld leave m > 16597n/16598."


def _attempts(root: Path) -> Path:
    return fixture.nodes_dir(root) / PARENT / "attempts"


def _write(root: Path, name: str, **overrides: object) -> None:
    doc = samples.postmortem(node=PARENT, **overrides)
    (_attempts(root) / name).write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")


def _page(root: Path) -> str:
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    files = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)
    return files[f"nodes/propositional/{PARENT}/index.html"]


def _blocks(page: str) -> list[str]:
    return re.findall(
        r'<div class="prose-block untrusted" data-block="postmortem".*?</div></div>', page, re.S
    )


def test_a_postmortem_naming_no_partial_shows_its_words(tmp_path: Path) -> None:
    root = fixture.curated(tmp_path)
    _write(
        root,
        STANDALONE,
        schema="postmortem/v2",
        contributor="t1029e-a",
        route="Narrow the core by effective results only",
        route_class="reduction-to-known",
        outcome="exhausted",
        failure_class="route-dead-ends",
        detail=DETAIL,
        model_and_tooling="Claude Opus 5.5 through the MCP",
        artifacts={},
    )
    blocks = [b for b in _blocks(_page(root)) if STANDALONE in b]
    assert len(blocks) == 1, blocks
    block = blocks[0]
    assert "16597n/16598" in block, block
    assert "Narrow the core by effective results only" in block, block
    assert "exhausted" in block and "route-dead-ends" in block, block
    assert "reduction-to-known" in block, block
    assert "by t1029e-a" in block and "Claude Opus 5.5 through the MCP" in block, block
    assert "2026-10-29" in block, block
    assert f"nodes/{PARENT}/attempts/{STANDALONE}" in block, block


def test_a_postmortem_naming_a_partial_shows_its_words_once(tmp_path: Path) -> None:
    root = fixture.curated(tmp_path)
    page = _page(root)  # the fixture's 2026-09-01-a.yaml names 2026-09-01-a-partial.lean
    words = "the inductive step needs a uniform bound the route cannot supply"
    assert page.count(words) == 1, page.count(words)
    assert any("2026-09-01-a.yaml" in b and words in b for b in _blocks(page))


def test_the_goal_state_and_missing_lemmas_are_shown(tmp_path: Path) -> None:
    root = fixture.curated(tmp_path)
    _write(root, STANDALONE)
    block = next(b for b in _blocks(_page(root)) if STANDALONE in b)
    assert "hk : 2 &lt;= k" in block, block  # the sample's terminal_goal_state, escaped
    assert "<pre" in block, block
    assert "uniform bound on the partial sums" in block, block


def test_contributor_text_is_escaped(tmp_path: Path) -> None:
    root = fixture.curated(tmp_path)
    _write(root, STANDALONE, detail="<script>alert(1)</script> & <b>x</b>", route="<img src=x>")
    block = next(b for b in _blocks(_page(root)) if STANDALONE in b)
    assert "<script>" not in block and "<img" not in block and "<b>" not in block, block
    assert "&lt;script&gt;" in block, block


def test_postmortems_read_newest_first(tmp_path: Path) -> None:
    root = fixture.curated(tmp_path)
    _write(root, OLDER, detail="the older account")
    _write(root, STANDALONE, detail="the newer account")
    page = _page(root)
    assert page.index("the newer account") < page.index("the older account")


def test_an_unreadable_postmortem_does_not_take_the_page_down(tmp_path: Path) -> None:
    root = fixture.curated(tmp_path)  # the fixture's 2026-09-02-b.yaml is not valid YAML
    page = _page(root)
    assert "2026-09-02-b.yaml" not in "".join(_blocks(page))
    assert _blocks(page), "the valid postmortem still renders"
