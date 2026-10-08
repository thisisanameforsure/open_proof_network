"""F04-T38 (D-25, D-32 v3.35): a node carries its literature status, confirmed or proposed.

Three testers on erdos-1094 (2026-10-08) could not tell the open core (``--h2``) from a
literature theorem (``--h3``, Konyagin 1999) on the frontier: both read "open". Decisions v3.35
let any contributor append a literature record (``open``, ``known`` or ``elementary``, with
references and a summary) and a steward of the target or a curator confirm it; the products
publish the latest confirmed status as the row's ``literature`` and the latest uncovered
proposal as ``literature_proposed`` (``graph/v6``, ``frontier/v5``).

The site shows a confirmed status as a fact — the status's words, "confirmed by <login>", the
references (titles; urls linked only through the allowlist, F11-Q11) and the summary demarcated
as untrusted contributor text (D-31) — and an unconfirmed one as "Proposed by <contributor>,
awaiting a steward or curator"; both present, the confirmed one and beneath it "a later proposal
by X awaits confirmation". Nothing ranks or colours by it. ``/me/`` lists, per target and hidden,
the unconfirmed records a steward or curator may confirm; the control is the script's (F23-R15).
"""

from __future__ import annotations

import html
import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import fixture
import pytest
from harness import TARGET

from opn_gate import layout
from opn_site import model, render

REPO = "https://github.com/example/graph"
API = "https://api.example.test"
ROOT = "and-swap-reassoc"  # confirmed `known`, then a later proposal
DEP = "and-reassoc"  # a proposal only
NONE = "tutorial-and-swap"  # no record at all
URL = "https://www.erdosproblems.com/1094"
REFERENCES: list[dict[str, Any]] = [
    {"title": "S. V. Konyagin, a 1999 paper", "url": URL, "note": "Proves the stated bound."},
    {"title": "An earlier partial result (1996)", "url": None, "note": None},
]
SUMMARY = "Known since 1999; never formalised. <b>Untrusted text</b> & escaped."
BLOCK_START = '<div class="literature" data-block="literature">'


@pytest.fixture(scope="module", autouse=True)
def literature_dir_allowed() -> Iterator[None]:
    """D-3 v3.35 gives a node a ``literature/`` directory; the gate's layout rule learns it in
    F08, built in parallel. Until that lands here, the rule is told, so these tests feed the
    tree the amendment's shape; once the gate carries it this is a no-op."""
    with pytest.MonkeyPatch.context() as mp:
        if "literature" not in layout.OPTIONAL_DIRS:
            mp.setattr(layout, "OPTIONAL_DIRS", (*layout.OPTIONAL_DIRS, "literature"))
        yield


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[model.Site, dict[str, str]]:
    root = fixture.build(tmp_path_factory.mktemp("literature"))
    proposal = fixture.write_literature(
        root,
        ROOT,
        status="known",
        contributor="t1008-c",
        date="2026-10-08T14:05:40Z",
        references=REFERENCES,
        summary=SUMMARY,
    )
    confirmation = fixture.write_literature(
        root,
        ROOT,
        status="known",
        contributor="mike",
        date="2026-10-08T15:10:00Z",
        references=REFERENCES,
        summary="Confirmed as stated.",
        confirms=proposal,
        signed=True,
    )
    later = fixture.write_literature(
        root,
        ROOT,
        status="elementary",
        contributor="t1008-a",
        date="2026-10-08T16:20:00Z",
        summary="A later reading: routine once the lemma is in Mathlib.",
    )
    dep_proposal = fixture.write_literature(
        root,
        DEP,
        status="open",
        contributor="t1008-b",
        date="2026-10-08T14:02:11Z",
        summary="No proof is known.",
    )
    fixture.publish_v335(
        root,
        literature={
            ROOT: {
                "status": "known",
                "record": proposal,
                "contributor": "t1008-c",
                "confirmed_by": "mike",
                "confirmation": confirmation,
            },
        },
        literature_proposed={
            ROOT: {"status": "elementary", "record": later, "contributor": "t1008-a"},
            DEP: {"status": "open", "record": dep_proposal, "contributor": "t1008-b"},
        },
    )
    site = model.load_site(root, fixture.COMMIT)
    return site, render.render_site(site, repo_url=REPO, api_url=API)


def block(page: str) -> str:
    """The literature block, as the balanced ``<div>`` that opens it."""
    assert page.count(BLOCK_START) == 1, page
    start = page.index(BLOCK_START)
    depth = 0
    for m in re.finditer(r"<div\b|</div>", page[start:]):
        depth += 1 if m.group(0) == "<div" else -1
        if depth == 0:
            return page[start : start + m.end()]
    raise AssertionError("unbalanced literature block")


def test_the_model_reads_both_fields_and_the_records_they_name(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    site, _pages = built
    nodes = site.targets[TARGET].nodes
    lit = nodes[ROOT].literature
    assert lit is not None
    assert (lit.status, lit.contributor, lit.confirmed_by) == ("known", "t1008-c", "mike")
    assert lit.record == f"targets/{TARGET}/nodes/{ROOT}/literature/20261008T140540Z-t1008-c.yaml"
    node_dir = f"targets/{TARGET}/nodes/{ROOT}"
    assert lit.confirmation == f"{node_dir}/literature/20261008T151000Z-mike.yaml"
    assert lit.date == "2026-10-08T14:05:40Z"
    assert [r.title for r in lit.references] == [r["title"] for r in REFERENCES]
    assert [r.url for r in lit.references] == [URL, None]
    assert lit.summary == SUMMARY
    later = nodes[ROOT].literature_proposed
    assert later is not None and (later.status, later.contributor) == ("elementary", "t1008-a")
    assert later.confirmed_by is None and later.confirmation is None
    assert nodes[DEP].literature is None and nodes[DEP].literature_proposed is not None
    assert nodes[NONE].literature is None and nodes[NONE].literature_proposed is None


def test_an_older_graph_reads_no_literature(tmp_path: Path) -> None:
    root = fixture.build(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    nv = site.targets[TARGET].nodes[ROOT]
    assert "literature" not in nv.graph_entry
    assert nv.literature is None and nv.literature_proposed is None


def test_a_row_naming_a_record_the_tree_lacks_still_renders(tmp_path: Path) -> None:
    """C7: one node's missing record must not decide whether the graph has a site; the page
    carries what the row says and says the record could not be read."""
    root = fixture.build(tmp_path)
    fixture.publish_v335(
        root,
        literature_proposed={
            DEP: {
                "status": "open",
                "record": "literature/20261008T000000Z-x.yaml",
                "contributor": "x",
            }
        },
    )
    site = model.load_site(root, fixture.COMMIT)
    lit = site.targets[TARGET].nodes[DEP].literature_proposed
    assert lit is not None and lit.status == "open" and not lit.readable
    assert lit.references == () and lit.summary is None
    page = render.render_site(site, repo_url=REPO)[f"nodes/{TARGET}/{DEP}/index.html"]
    assert "could not be read" in block(page)


def test_a_confirmed_status_is_a_fact_with_its_references_and_demarcated_summary(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    _site, pages = built
    page = pages[f"nodes/{TARGET}/{ROOT}/index.html"]
    b = block(page)
    assert "Known: a proof is published and not formalised" in b
    assert "confirmed by <code>mike</code>" in b
    assert "Proposed by" not in b.split("later proposal")[0]
    # References: titles; a url only as a link the allowlist admits, none for a null url.
    assert f'<a href="{URL}">{render.esc(REFERENCES[0]["title"])}</a>' in b
    assert render.esc(REFERENCES[1]["title"]) in b and 'href="None"' not in b
    assert "Proves the stated bound." in b
    # The summary: untrusted contributor text, labelled, escaped.
    i = b.index('<div class="prose-block untrusted"')
    summary = b[i:]
    assert 'data-provenance="untrusted"' in summary
    assert "&lt;b&gt;Untrusted text&lt;/b&gt; &amp; escaped." in summary
    assert "<b>" not in summary
    # The records, linked at the commit (R2); the footer lists them among the files rendered.
    for rel in ("20261008T140540Z-t1008-c.yaml", "20261008T151000Z-mike.yaml"):
        url = f"{REPO}/blob/{fixture.COMMIT}/targets/{TARGET}/nodes/{ROOT}/literature/{rel}"
        assert page.count(url) >= 2, rel


def test_a_later_proposal_under_a_confirmed_status_awaits_beneath_it(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    _site, pages = built
    b = block(pages[f"nodes/{TARGET}/{ROOT}/index.html"])
    head, _sep, tail = b.partition("later proposal")
    assert "Known:" in head and "confirmed by" in head
    assert "by <code>t1008-a</code>" in tail
    assert "Elementary" in tail and "awaits confirmation" in tail


def test_a_proposal_alone_says_who_proposed_it_and_what_it_awaits(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    _site, pages = built
    b = block(pages[f"nodes/{TARGET}/{DEP}/index.html"])
    assert "Proposed by <code>t1008-b</code>, awaiting a steward or curator" in b
    assert "Open problem: no proof is known" in b
    assert "confirmed by" not in b and "later proposal" not in b


def test_a_node_with_no_record_shows_no_block(built: tuple[model.Site, dict[str, str]]) -> None:
    _site, pages = built
    assert 'data-block="literature"' not in pages[f"nodes/{TARGET}/{NONE}/index.html"]


def test_the_problem_pages_statement_cards_carry_the_same_block(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    _site, pages = built
    page = pages[f"problems/{TARGET}/index.html"]
    panels = dict(
        re.findall(
            r'<div class="card panel" data-node="([^"]+)"(.*?)(?=<div class="card panel"|$)',
            page,
            re.S,
        )
    )
    assert "Known: a proof is published and not formalised" in panels[ROOT]
    assert "confirmed by <code>mike</code>" in panels[ROOT]
    assert "Proposed by <code>t1008-b</code>" in panels[DEP]
    assert 'data-block="literature"' not in panels[NONE]


def test_nothing_ranks_or_colours_by_the_status(built: tuple[model.Site, dict[str, str]]) -> None:
    """D-25: a fact about the literature, never about difficulty: no class, dot or ordering keyed
    on the status value; the rows keep their order and their state dots."""
    _site, pages = built
    for nid in (ROOT, DEP):
        b = block(pages[f"nodes/{TARGET}/{nid}/index.html"])
        assert not re.search(r'class="[^"]*\b(open|known|elementary)\b', b), b
        assert "dot-" not in b
    listing = pages["problems/index.html"]
    ids = re.findall(
        r'<div class="stmt"[^>]*>.*?<a href="/nodes/propositional/([^/]+)/"', listing, re.S
    )
    assert ids == [ROOT, DEP, NONE], "the root first, then by id, as before"


def test_reference_urls_are_on_the_allowlist_from_the_validated_record(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    """F11-Q11: the renderer cannot invent an outbound link; the url a validated literature
    record names joins the allowlist the link checker admits, and nothing else does."""
    site, _pages = built
    assert URL in render.cited_urls(site)


# --- /me/ (F23-R13, R15): what waits for a steward's or curator's confirmation -------------------


def test_the_me_page_lists_the_unconfirmed_records_per_target_hidden(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    _site, pages = built
    page = pages["me/index.html"]
    lists = re.findall(
        r'<ul class="literature-waiting" data-target="([^"]+)" hidden>(.*?)</ul>', page, re.S
    )
    assert [t for t, _ in lists] == [TARGET]
    rows = re.findall(r'<li class="lit-row"([^>]*)>(.*?)</li>', lists[0][1], re.S)
    assert len(rows) == 2, rows
    by_node = {re.search(r'data-node="([^"]+)"', a).group(1): (a, body) for a, body in rows}  # type: ignore[union-attr]
    attrs, body = by_node[ROOT]
    assert 'data-record="literature/20261008T162000Z-t1008-a.yaml"' in attrs
    assert 'data-status="elementary"' in attrs
    refs = re.search(r"data-references=\"([^\"]*)\"", attrs)
    assert refs is not None
    record = json.loads(html.unescape(refs.group(1)))
    assert record == [{"title": "Where the problem is listed", "url": None, "note": None}]
    summary = re.search(r"data-summary=\"([^\"]*)\"", attrs)
    assert summary is not None and html.unescape(summary.group(1)).startswith("A later reading")
    assert f'href="/nodes/{TARGET}/{ROOT}/"' in body
    assert "Elementary" in body and "t1008-a" in body and "2026-10-08T16:20:00Z" in body
    later = f"targets/{TARGET}/nodes/{ROOT}/literature/20261008T162000Z-t1008-a.yaml"
    assert f"/blob/{fixture.COMMIT}/{later}" in body
    dep_attrs, dep_body = by_node[DEP]
    assert 'data-status="open"' in dep_attrs and "t1008-b" in dep_body
    # F23-R15: no control in the static page; the script adds Confirm after GET /session.
    main = page.split("<main>", 1)[1]
    assert not re.search(r"<(form|input|textarea|select|button)\b", main)


def test_a_target_with_nothing_to_confirm_has_no_list(tmp_path: Path) -> None:
    root = fixture.build(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    page = render.render_site(site, repo_url=REPO, api_url=API)["me/index.html"]
    assert "literature-waiting" not in page


def test_the_script_confirms_through_the_service_with_the_proposals_fields() -> None:
    """The control calls ``POST /literature/confirm`` with ``{node_id, record, status,
    references, summary}`` copied from the row, for a steward's targets and, for a curator,
    every target's list (``data-role``-free: the role comes from the session, the lists from the
    page)."""
    js = (Path(render.__file__).resolve().parent / "static" / "me.js").read_text(encoding="utf-8")
    assert '"/literature/confirm"' in js
    for key in ("node_id", "record", "status", "references", "summary"):
        assert re.search(rf"\b{key}\s*:", js), key
    assert ".literature-waiting" in js and "lit-row" in js
    assert "s.curator" in js, "a curator sees every target's list"
    assert "Confirm" in js
