"""F25-T12 / AC17 (R17; D-10, D-19, D-23 v3.37): a target's registration on its page, the
Registries section and the two licences on the Docs page, Palomar by name on the About page.

The index is ``panel_fixture``'s v10 with ``registrations`` rows written by hand and validated
against the published schema, so the site is checked against the contract rather than against
what one gate commit happens to write. A registry url reaches the page as a link only when the
status is ``registered`` and the url is on the allowlist the validated records build
(F11-Q11); the renderer may not invent an outbound link, and a page that links a url no record
names is a build failure like any other (F04-R13).
"""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from pathlib import Path

import panel_fixture as pf
import pytest
from fixture import (
    CALIBRATION_TARGET,
    COMMIT,
    RESOLVED_TARGET,
    STEWARDED_TARGET,
    STEWARDLESS_TARGET,
)

from opn_site import links, model, render

REPO = "https://github.com/example/graph"
API = "https://api.example.org"
PALOMAR_HOME = "https://palomar-registry.org/"
LINE = '<p class="registration">'
REVISION_ID = "PALOMAR-2026-09-30-000777"
ROWS = {
    RESOLVED_TARGET: [pf.registration("registered")],
    STEWARDED_TARGET: [
        pf.registration("submitted", registry_id=None, version=None, url=pf.SUBMITTED_URL)
    ],
    STEWARDLESS_TARGET: [
        pf.registration("revision_required", registry_id=REVISION_ID, version=1),
        pf.registration("rejected", registry_id=None, version=None, url=None),
    ],
}


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


def parsed(fragment: str) -> _Text:
    p = _Text()
    p.feed(fragment)
    # The templates wrap sentences across lines; the words are the claim, not the line breaks.
    p.text = [" ".join(" ".join(p.text).split())]
    return p


def problem_path(target_id: str) -> str:
    return f"problems/{target_id}/index.html"


def registration_lines(page: str) -> list[str]:
    return re.findall(r'<p class="registration">.*?</p>', page, re.S)


def copy_links() -> frozenset[str]:
    """What the build admits besides the records: the copy's dated links and the service's own
    live claims url (``render_site`` passes exactly these beside ``cited_urls``)."""
    return render.COPY_LINKS | render.live_urls(API)


def section(page: str, sid: str) -> str:
    start = page.index(f'<h2 id="{sid}">')
    end = page.find("<h2", start + 1)
    return page[start : end if end >= 0 else len(page)]


@pytest.fixture(scope="module")
def root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return pf.with_registrations(pf.build(tmp_path_factory.mktemp("registrations")), ROWS)


@pytest.fixture(scope="module")
def site(root: Path) -> model.Site:
    return model.load_site(root, COMMIT)


@pytest.fixture(scope="module")
def pages(site: model.Site) -> dict[str, str]:
    return render.render_site(site, repo_url=REPO, api_url=API)


@pytest.fixture(scope="module")
def older(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    """The same graph under a v9 index, which has no ``registrations`` key at all."""
    root = pf.without_registrations(pf.build(tmp_path_factory.mktemp("older")))
    return render.render_site(model.load_site(root, COMMIT), repo_url=REPO, api_url=API)


# --- the model -------------------------------------------------------------------------------


def test_the_model_reads_the_rows_registrations_and_an_older_index_as_none(
    site: model.Site, tmp_path_factory: pytest.TempPathFactory
) -> None:
    assert site.targets[RESOLVED_TARGET].registrations == ROWS[RESOLVED_TARGET]
    assert site.targets[STEWARDLESS_TARGET].registrations == ROWS[STEWARDLESS_TARGET]
    assert site.targets[CALIBRATION_TARGET].registrations == []
    root = pf.without_registrations(pf.build(tmp_path_factory.mktemp("older-model")))
    old = model.load_site(root, COMMIT)
    assert all(tv.registrations == [] for tv in old.targets.values())


# --- the problem page: four states -----------------------------------------------------------


def test_a_registered_target_names_its_id_and_version_and_links_the_entry(
    pages: dict[str, str],
) -> None:
    head = pages[problem_path(RESOLVED_TARGET)]
    lines = registration_lines(head)
    assert len(lines) == 1, lines
    (line,) = lines
    text = " ".join(parsed(line).text)
    assert text == f"Registered in Palomar as {pf.PALOMAR_ID} v2", text
    assert parsed(line).hrefs == [pf.PALOMAR_URL]
    # Escaped as an attribute: the ampersand and the quotes never reach the page raw.
    assert f'href="{html.escape(pf.PALOMAR_URL, quote=True)}"' in line
    assert pf.PALOMAR_URL not in line
    # In the header, before the statements section, with the other status lines.
    assert head.index(LINE) < head.index('<section class="statements-section">')


def test_a_submitted_target_says_under_review_and_links_nothing(pages: dict[str, str]) -> None:
    (line,) = registration_lines(pages[problem_path(STEWARDED_TARGET)])
    assert " ".join(parsed(line).text) == "Submitted to Palomar, under review"
    assert parsed(line).hrefs == []  # a url on a submission is not a registry entry
    assert pf.SUBMITTED_URL not in line


def test_revisions_asked_and_declined_each_have_their_words_and_no_link(
    pages: dict[str, str],
) -> None:
    lines = registration_lines(pages[problem_path(STEWARDLESS_TARGET)])
    assert [" ".join(parsed(line).text) for line in lines] == [
        f"Palomar asked for revisions ({REVISION_ID} v1)",
        "Palomar declined",
    ]
    assert all(parsed(line).hrefs == [] for line in lines)
    assert pf.PALOMAR_URL not in pages[problem_path(STEWARDLESS_TARGET)]


def test_a_target_with_no_registration_has_no_line(pages: dict[str, str]) -> None:
    assert LINE not in pages[problem_path(CALIBRATION_TARGET)]
    assert "Palomar" not in pages[problem_path(CALIBRATION_TARGET)]


def test_an_older_index_without_the_key_renders_with_no_registration_line(
    older: dict[str, str],
) -> None:
    for rel, page in older.items():
        if rel.startswith("problems/"):
            assert LINE not in page, rel
    assert "Palomar" not in older[problem_path(RESOLVED_TARGET)]


# --- the allowlist ---------------------------------------------------------------------------


def test_the_registered_url_is_on_the_allowlist_only_because_the_record_names_it(
    site: model.Site, pages: dict[str, str]
) -> None:
    """The checker passes with the allowlist the validated records build, and refuses the same
    page once that url is withheld: the renderer has no other way to link it."""
    foreign = frozenset(k for k in pages if k.startswith("docs/") and k != "docs/index.html")
    cited = render.cited_urls(site)
    assert pf.PALOMAR_URL in cited
    assert pf.SUBMITTED_URL not in cited  # not registered: not a registry entry, never linked
    assert PALOMAR_HOME not in cited  # the Docs copy's link is COPY_LINKS', not a record's
    assert links.check(pages, repo_url=REPO, foreign=foreign, cited=cited | copy_links()) == []
    withheld = (cited - {pf.PALOMAR_URL}) | copy_links()
    refused = links.check(pages, repo_url=REPO, foreign=foreign, cited=withheld)
    assert refused == [f"{problem_path(RESOLVED_TARGET)}: external link {pf.PALOMAR_URL}"], refused


def test_an_invented_registry_url_is_a_build_failure(
    site: model.Site, pages: dict[str, str]
) -> None:
    invented = "https://palomar-registry.org/entries/PALOMAR-2026-10-10-000002"
    rel = problem_path(RESOLVED_TARGET)
    forged = {**pages, rel: pages[rel].replace(LINE, f'<p><a href="{invented}">x</a></p>{LINE}', 1)}
    foreign = frozenset(k for k in pages if k.startswith("docs/") and k != "docs/index.html")
    refused = links.check(
        forged, repo_url=REPO, foreign=foreign, cited=render.cited_urls(site) | copy_links()
    )
    assert refused == [f"{rel}: external link {invented}"], refused


# --- the Docs page ---------------------------------------------------------------------------


def test_docs_has_a_registries_section_between_propose_and_leiden(pages: dict[str, str]) -> None:
    docs = pages["docs/index.html"]
    assert '<h2 id="registries">Registries</h2>' in docs
    assert (
        docs.index('<h2 id="propose">')
        < docs.index('<h2 id="registries">')
        < docs.index('<h2 id="leiden">')
    )
    jump = docs[docs.index('<p class="jump">') : docs.index("</p>", docs.index('<p class="jump">'))]
    assert 'href="#registries"' in jump


def test_the_registries_section_says_what_palomar_is_and_how_the_network_uses_it(
    pages: dict[str, str],
) -> None:
    sec = section(pages["docs/index.html"], "registries")
    text = " ".join(parsed(sec).text)
    for phrase in (
        "Palomar",
        "a registry of Lean-verified results run by the Lean FRO and ICARM",
        "checks a proof with two independent kernels and reviews the statement with a model",
        'in its own words, "not peer review"',
        "A resolved open-track problem, or a formalization-track one a curator judges of "
        "research interest",
        "A curator",
        "never an agent on its own",
        "by pseudonym, or by a display name they record",
        "one-way publication",
        "withdraw",
        "read for prior art",
        "A literature record may cite a Palomar entry by its id",
        "Apache-2.0",
    ):
        assert phrase in text, phrase
    assert parsed(sec).hrefs.count(PALOMAR_HOME) == 1
    assert PALOMAR_HOME in render.COPY_LINKS


def test_the_licence_section_names_both_licences_and_keeps_the_sign_off_link(
    pages: dict[str, str],
) -> None:
    docs = pages["docs/index.html"]
    start = docs.index("<h2>License and sign-off</h2>")
    sec = docs[start : docs.index("</main>", start)]
    text = " ".join(parsed(sec).text)
    assert "The code is Apache-2.0" in text
    assert "the non-code record" in text and "CDLA-Permissive-2.0" in text
    assert "D-23 v3.37" in text
    assert f"{API}/dco.json" in parsed(sec).hrefs  # the existing link stays


def test_the_leiden_authorship_row_says_a_registrations_authors_are_people(
    pages: dict[str, str],
) -> None:
    row = next(r for r in render.LEIDEN_ROWS if r[0] == "Attribution, plagiarism, scooping")
    assert (
        "a registration's authors are the ledger's identities under their pseudonyms or recorded "
        "names and never a model (D-19 v3.37)"
    ) in row[1]
    assert html.escape(row[1]) in pages["docs/index.html"]


# --- the About page --------------------------------------------------------------------------


def test_about_names_palomar_in_the_report_back_sentence_without_linking_it(
    pages: dict[str, str],
) -> None:
    about = pages["about/index.html"]
    lead = about[about.index('<div class="lead" id="lead">') : about.index('<div class="rules"')]
    text = " ".join(parsed(lead).text)
    assert 'the source registry hears "kernel-checked, not yet explained", not "solved"' in text
    assert "Palomar" in text
    assert PALOMAR_HOME not in parsed(about).hrefs  # the Docs copy links it, the About does not
