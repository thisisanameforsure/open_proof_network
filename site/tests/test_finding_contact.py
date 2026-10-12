"""F04-T40 (Q41): the site says who runs it and how to reach them.

Every page's footer links the About page's contact section; that section names the person who runs
the network, their email and their LinkedIn profile, and sends bugs and proposals to the graph
repository's issues, where they are public. The two off-site links pass F04-R13's checker as exact
urls, the way the copy's other links do (F15-R11), so the checker still refuses any other mailto or
profile link.
"""

from __future__ import annotations

from html.parser import HTMLParser

import fixture
import pytest

from opn_site import links, model, render

REPO = "https://github.com/example/graph"
EMAIL = "michael.higgins.data@gmail.com"
LINKEDIN = "https://www.linkedin.com/in/michael-higgins-data/"


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root = fixture.build(tmp_path_factory.mktemp("contact"))
    site = model.load_site(root, fixture.COMMIT)
    return render.render_site(site, repo_url=REPO)


class _Footer(HTMLParser):
    """The hrefs inside the page frame's ``<footer>``."""

    def __init__(self) -> None:
        super().__init__()
        self.inside = False
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "footer":
            self.inside = True
        elif tag == "a" and self.inside:
            self.hrefs.append(dict(attrs).get("href") or "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "footer":
            self.inside = False


def footer_hrefs(html: str) -> list[str]:
    p = _Footer()
    p.feed(html)
    return p.hrefs


def test_every_framed_page_footer_links_the_contact_section(pages: dict[str, str]) -> None:
    framed = {rel: html for rel, html in pages.items() if '<footer class="provenance">' in html}
    assert len(framed) > 10  # the frame is every page's, not one template's
    missing = [rel for rel, html in framed.items() if "/about/#contact" not in footer_hrefs(html)]
    assert missing == []


def test_about_page_names_the_person_and_both_ways_to_reach_them(pages: dict[str, str]) -> None:
    about = pages["about/index.html"]
    assert 'id="contact"' in about
    section = about[about.index('id="contact"') :]
    assert "Michael Higgins" in section
    assert f'href="mailto:{EMAIL}"' in section
    assert EMAIL in section  # the address is readable, not only a link
    assert f'href="{LINKEDIN}"' in section
    # Bugs and proposals go where they are public and on the record.
    assert f'href="{REPO}/issues"' in section


def test_about_page_on_page_nav_reaches_the_contact_section(pages: dict[str, str]) -> None:
    about = pages["about/index.html"]
    nav = about[about.index('class="on-page"') :]
    assert 'href="#contact"' in nav[: nav.index("</nav>")]


def test_contact_links_are_admitted_as_exact_urls_only() -> None:
    """Guard: the allowlist is a set of urls, so another address or profile is still refused."""
    page = (
        f'<p><a href="mailto:{EMAIL}">a</a> <a href="{LINKEDIN}">b</a> '
        '<a href="mailto:someone@example.com">c</a> '
        '<a href="https://www.linkedin.com/in/someone-else/">d</a></p>'
    )
    problems = links.check(
        {"x.html": page}, repo_url=REPO, cited=frozenset({f"mailto:{EMAIL}", LINKEDIN})
    )
    assert problems == [
        "x.html: external link mailto:someone@example.com",
        "x.html: external link https://www.linkedin.com/in/someone-else/",
    ]
