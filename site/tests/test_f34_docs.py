"""F34-T6 (R8, AC9): Docs is one page per topic with a sidebar; AGENTS.md is linked, never copied.

The single /docs/ page was 73,700px and copied AGENTS.md in whole (F04-Q6, which gives way:
F34-Q6). Each topic has its own page under /docs/, every page carries the same sidebar with the
current page marked, previous and next links, and its decisions once at its foot; AGENTS.md is
served whole at /AGENTS.md; every anchor of the old page still lands on a link to the page that
holds its content now; and the MCP command names the service from config, never a hostname.
"""

from __future__ import annotations

import re
from pathlib import Path

import fixture
import pytest
from docs_pages import docs_rels
from test_f34_codes import visible_codes

from opn_site import model, render

REPO = "https://github.com/example/graph"
API = "https://api.example.org"
#: A sentence from deep inside AGENTS.md: if it is on a docs page, the guide was copied in.
DEEP = "Refuted routes, counterexamples, partial proofs and typed postmortems are results"
GUIDE = """# AGENTS.md — how to contribute to this graph

## What this is

The Open Proof Network is a crowdsourced Lean 4 proof effort on open mathematical problems.
Refuted routes, counterexamples, partial proofs and typed postmortems are results, not failures.

## Glosses, explainers and outlines (D-3)

Three kinds of words sit beside the Lean.
"""
NEW_PAGES = (
    "docs/index.html",
    "docs/quick-start/index.html",
    "docs/token/index.html",
    "docs/words/index.html",
    "docs/how-it-works/index.html",  # T7
    "docs/claim/index.html",  # T7
    "docs/submit/index.html",  # T7
)


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root = fixture.build(tmp_path_factory.mktemp("f34-docs"))
    (root / "AGENTS.md").write_text(GUIDE, encoding="utf-8")
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO, api_url=API)


def docs_pages(pages: dict[str, str]) -> dict[str, str]:
    return {
        rel: html
        for rel, html in pages.items()
        if (rel.startswith("docs/") and rel.endswith("/index.html")) or rel == "docs/index.html"
    }


def test_each_topic_has_its_own_page(pages: dict[str, str]) -> None:
    for group, entries in render.DOCS_GROUPS:
        for slug, title, _f, _why in entries:
            if slug.startswith("/"):
                continue
            rel = f"docs/{slug}/index.html" if slug else "docs/index.html"
            assert rel in pages, (group, slug)
            assert f"<h1>{render.esc(title)}</h1>" in pages[rel], rel


def test_every_page_has_the_sidebar_with_itself_marked(pages: dict[str, str]) -> None:
    for rel, html in docs_pages(pages).items():
        side = html[
            html.index('<nav class="docs-side"') : html.index(
                "</nav>", html.index('<nav class="docs-side"')
            )
        ]
        assert side.count("<li>") >= 10, rel
        current = re.findall(r'<a href="([^"]+)" aria-current="page">', side)
        expected = "/" + rel.removesuffix("index.html")
        assert current == [expected], (rel, current)


def test_no_docs_page_copies_agents_md_and_it_is_served_whole(pages: dict[str, str]) -> None:
    assert pages["AGENTS.md"] == GUIDE
    for rel, html in docs_pages(pages).items():
        assert DEEP not in html, f"{rel} copies AGENTS.md"
        assert 'href="/AGENTS.md"' in html, f"{rel} does not link it"


def test_every_old_anchor_lands_on_a_link_to_its_page(pages: dict[str, str]) -> None:
    landing = pages["docs/index.html"]
    for old, slug in render.DOCS_OLD_ANCHORS.items():
        m = re.search(rf'<li id="{re.escape(old)}">.*?<a href="([^"]+)"', landing) or re.search(
            rf'<span id="{re.escape(old)}"></span><a href="([^"]+)"', landing
        )
        assert m is not None, f"#{old} is gone from /docs/"
        assert m.group(1) == f"/docs/{slug}/", (old, m.group(1))
        assert f"docs/{slug}/index.html" in pages


def test_the_site_links_to_pages_not_to_old_anchors(pages: dict[str, str]) -> None:
    stale = {
        rel: re.findall(r'href="/docs/#[^"]*"', html)
        for rel, html in pages.items()
        if rel.endswith(".html") and re.search(r'href="/docs/#', html)
    }
    assert stale == {}


def test_previous_and_next_follow_the_sidebar(pages: dict[str, str]) -> None:
    order = [
        slug
        for _g, entries in render.DOCS_GROUPS
        for slug, _t, _f, _w in entries
        if not slug.startswith("/")
    ]
    for i, slug in enumerate(order):
        html = pages[f"docs/{slug}/index.html" if slug else "docs/index.html"]
        nav = html[html.index('<nav class="prevnext"') :]
        nav = nav[: nav.index("</nav>")]
        if i + 1 < len(order):
            nxt = order[i + 1]
            assert f'class="next" href="/docs/{nxt}/"' in nav, (slug, nxt)
        if i > 0:
            prv = order[i - 1]
            assert f'class="prev" href="{"/docs/" + prv + "/" if prv else "/docs/"}"' in nav


def test_the_mcp_command_names_the_service_from_config(
    pages: dict[str, str], tmp_path: Path
) -> None:
    quick = pages["docs/quick-start/index.html"]
    assert f"claude mcp add --transport http open-proof-network {API}/mcp" in quick
    root = fixture.build(tmp_path)
    plain = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)
    assert "open-proof-network $OPN_API/mcp" in plain["docs/quick-start/index.html"]
    assert "api.example.org" not in plain["docs/quick-start/index.html"]


def test_a_graph_without_agents_md_links_its_place_in_the_repository(tmp_path: Path) -> None:
    root = fixture.build(tmp_path)
    assert not (root / "AGENTS.md").exists()
    built = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)
    assert "AGENTS.md" not in built
    assert f'href="{REPO}/blob/{fixture.COMMIT}/AGENTS.md"' in built["docs/index.html"]


@pytest.mark.parametrize("rel", NEW_PAGES)
def test_the_new_pages_carry_no_codes_in_prose_and_name_them_at_the_foot(
    pages: dict[str, str], rel: str
) -> None:
    html = pages[rel]
    main = html[html.index('<article class="docs-main">') : html.index("</article>")]
    prose_ = main.split('<p class="docs-foot">', 1)[0]
    assert visible_codes(prose_) == [], rel


def test_the_token_page_says_what_the_guide_says(pages: dict[str, str]) -> None:
    """Every fact checked against AGENTS.md's "Getting a token": the request, the answer, the
    reserved-name refusal, the idle lapse, renewal and re-acceptance."""
    token = pages["docs/token/index.html"]
    for fact in (
        '"kind": "tutorial"',
        '"dco": {"accepted": true',
        "201",
        "idle_days",
        "409 pseudonym-reserved",
        "/tokens/renew",
        "401 token-expired",
        "403 dco-reaccept-required",
        "/dco/accept",
        "/auth/github/start",
        "Apache-2.0",
        "CDLA-Permissive-2.0",
        "One to 39 letters, digits or hyphens",
    ):
        assert fact in token, fact
    assert "Protocol: decisions D-19, D-23" in token


@pytest.mark.parametrize("rel", NEW_PAGES)
def test_the_pages_t6_wrote_are_short(pages: dict[str, str], rel: str) -> None:
    """The landing and the three guides T6 wrote are summaries, not dumps; the pages moved from the
    old single page are rewritten by T7."""
    html = pages[rel]
    main = html[html.index('<article class="docs-main">') : html.index("</article>")]
    words = len(re.sub(r"<[^>]+>", " ", main).split())
    assert words < 900, (rel, words)


def test_every_docs_page_names_its_decisions_only_at_its_foot(pages: dict[str, str]) -> None:
    """F34-T7 (R6, handoff §3.3): "Decision codes appear once, at the foot of a page"."""
    for rel in docs_rels():
        html = pages[rel]
        main = html[html.index('<article class="docs-main">') : html.index("</article>")]
        prose_ = main.split('<p class="docs-foot">', 1)[0]
        assert visible_codes(prose_) == [], rel


def test_moving_a_code_keeps_it_on_the_page() -> None:
    """A parenthesis that holds only codes leaves the sentence and joins the foot; a parenthesis
    with words in it, and anything inside <pre> or <code>, is left alone."""
    body = (
        "<p>Intake is curated (D-6 v3.17), and stewards answer (D-32; D-33 v3.17).</p>"
        "<p>A grade (the curator's call) stands.</p><pre>LICENSE (D-23)</pre><code>(D-4)</code>"
    )
    out, codes = render.move_codes(body)
    assert out == (
        "<p>Intake is curated, and stewards answer.</p>"
        "<p>A grade (the curator's call) stands.</p><pre>LICENSE (D-23)</pre><code>(D-4)</code>"
    )
    assert codes == ["D-6", "D-32", "D-33"]


@pytest.mark.parametrize(
    ("slug", "facts"),
    [
        (
            "claim",
            (
                "frontier.json",
                "needs: proof",
                "needs: witness",
                "/proposals/witness",
                '"ttl_hours"',
                "open_submissions",
                "409 node-shelved",
                "409 node-blocked",
                "/claims/mine",
                "DELETE",
            ),
        ),
        (
            "submit",
            (
                "precheck_job_id",
                "400 automation-missing",
                "409 precheck-used",
                "manual",
                "autonomous",
                "/check",
                "carries no authority",
                "/submissions/&lt;id&gt;",
            ),
        ),
    ],
)
def test_the_operator_guides_say_what_the_guide_says(
    pages: dict[str, str], slug: str, facts: tuple[str, ...]
) -> None:
    """F34-T7: each fact checked against AGENTS.md's "Claiming a node" and "Precheck and
    submit"."""
    page = pages[f"docs/{slug}/index.html"]
    for fact in facts:
        assert fact in page, (slug, fact)
