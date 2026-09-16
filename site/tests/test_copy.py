"""F15-T11 / AC11: the site's copy for a sceptical mathematician (R11; D-27 v3.17, D-36 v3.17).

The home lead speaks before any count and carries no network number; the Docs page carries the
steward section, the proposal link built from the configured repository, the Leiden paragraph
with one table row per objection of the research note's §5, and the students sentence; and every
off-site link in the copy passes F04-R13's checker through the documented allowlist, never by
loosening the rule.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

import fixture
import pytest

from opn_gate import steward
from opn_site import links, model, render

REPO = "https://github.com/example/graph"


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root = fixture.build(tmp_path_factory.mktemp("copy"))
    site = model.load_site(root, fixture.COMMIT)
    return render.render_site(site, repo_url=REPO)


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text: list[str] = []
        self.hrefs: list[str] = []

    def handle_data(self, data: str) -> None:
        self.text.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.hrefs.append(href)


def parsed(html: str) -> _Text:
    p = _Text()
    p.feed(html)
    return p


def test_the_home_lead_comes_first_and_carries_no_network_number(pages: dict[str, str]) -> None:
    """R11, Q10: the lead precedes the counts table; once dates are removed it holds no digit,
    so no count of the network's own can hide in it; it says what goes wrong, what the network
    does and what AI brings with people in the chain, and what the network refuses to do."""
    home = pages["index.html"]
    lead_start = home.index('<div class="lead" id="lead">')
    lead_end = home.index("</div>", lead_start)
    assert lead_end < home.index('<table class="counts">')
    lead = parsed(home[lead_start:lead_end])
    text = " ".join(lead.text)
    without_dates = re.sub(r"\b\d{4}(?:-\d{2}){0,2}\b", "", text)
    assert not re.search(r"\d", without_dates), without_dates
    for phrase in (
        "what goes wrong",
        "already in the literature",
        "did not say what the conjecture said",
        "its steward",
        "takes no proof credit",
        "kernel-checked, not yet explained",
        "announces nothing",
        "no leaderboard",
        "publishes its failures",
        "after the certificate, by a person",
    ):
        assert phrase in text, phrase
    # Dated external evidence only: the declaration and a digestion, each an exact allowlisted url.
    assert set(lead.hrefs) <= render.COPY_LINKS
    assert "https://mathandai.org/" in lead.hrefs


def test_every_outbound_link_in_the_copy_is_on_the_allowlist(pages: dict[str, str]) -> None:
    """R11: the checker's rule is unchanged (an off-site link is a build failure); the copy's
    links pass because each exact url is in ``render.COPY_LINKS``, and the checker refuses the
    same pages with the allowlist withheld."""
    into_repo = REPO + "/"
    for rel in ("index.html", "docs/index.html"):
        for href in parsed(pages[rel]).hrefs:
            if links.resolve(href) is not None or href.startswith(("#", into_repo)):
                continue
            assert href in render.COPY_LINKS, (rel, href)
    copy_pages = {k: v for k, v in pages.items() if k in ("index.html", "docs/index.html")}
    refused = links.check(
        {**copy_pages, **{k: v for k, v in pages.items() if k not in copy_pages}},
        repo_url=REPO,
        foreign=frozenset(k for k in pages if k.startswith("docs/") and k != "docs/index.html"),
        cited=frozenset(),
    )
    assert any("external link https://mathandai.org/" in p for p in refused), refused
    for url in render.COPY_LINKS:
        assert url.startswith("https://") and url == url.strip()


def test_the_docs_page_has_the_steward_section_and_the_proposal_link(
    pages: dict[str, str],
) -> None:
    """R11: the commitment sentence verbatim, what is received, what is not, how to step down;
    the proposal link is the configured graph repository's form."""
    docs = pages["docs/index.html"]
    assert '<h2 id="stewards">Stewards</h2>' in docs
    assert render.esc(steward.COMMITMENT) in docs
    for heading in (
        "What you commit to.",
        "What you receive.",
        "What you do not receive.",
        "How to step down.",
    ):
        assert heading in docs, heading
    assert f'href="{REPO}/issues/new?template=problem-proposal.yml"' in docs
    assert "the proposal form" in docs and "No Lean is needed" in docs


def test_the_leiden_table_has_one_row_per_recommendation(pages: dict[str, str]) -> None:
    docs = pages["docs/index.html"]
    table = docs.split('<table class="leiden">', 1)[1].split("</table>", 1)[0]
    rows = table.split("<tbody>", 1)[1].count("<tr>")
    assert rows == len(render.LEIDEN_ROWS) == 9  # the research note's §5, nine objections
    assert "https://leidendeclaration.ai/" in docs
    for objection, _does, _gap in render.LEIDEN_ROWS:
        assert render.esc(objection) in table, objection
    assert "endorses nothing formally" in docs


def test_the_students_sentence_is_honest(pages: dict[str, str]) -> None:
    docs = pages["docs/index.html"]
    assert "a proof network has no answer for students" in docs
    assert "not claimed as any" in docs
