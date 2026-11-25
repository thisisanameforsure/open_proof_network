"""F34-T1 (R1-R3): the Journal frame — tokens, vendored fonts, header and footer.

The design handoff of 2026-11-25 (``site/docs/design_handoff_2026-11/``) sets the site in a
light "Journal" scheme with a dark one derived from the same roles, three self-hosted type
families, a header that names the current section, and a footer whose commit and source list
sit inside one closed "Source of this page" disclosure.
"""

from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser

import fixture
import pytest

from opn_site import model, render

REPO = "https://github.com/example/graph"
FONTS = render.STATIC / "fonts"
CSS = (render.STATIC / "site.css").read_text(encoding="utf-8")

#: R1's text/ground pairs: every reading colour on both grounds.
TEXT = ("ink", "muted", "proved", "refuted")
GROUNDS = ("paper", "surface")


def _block(css: str, start: int) -> str:
    open_ = css.index("{", start)
    depth, i = 0, open_
    while True:
        if css[i] == "{":
            depth += 1
        elif css[i] == "}":
            depth -= 1
            if depth == 0:
                return css[open_ + 1 : i]
        i += 1


def _tokens(block: str) -> dict[str, str]:
    return dict(re.findall(r"--([a-z-]+):\s*(#[0-9A-Fa-f]{6})", block))


def schemes() -> dict[str, dict[str, str]]:
    """The light tokens (the first ``:root``) and the dark ones, as each scheme resolves them."""
    light = _tokens(_block(CSS, CSS.index(":root")))
    dark_at = CSS.index("@media (prefers-color-scheme: dark)")
    dark = {**light, **_tokens(_block(CSS, dark_at))}
    return {"light": light, "dark": dark}


def _luminance(hex_: str) -> float:
    def channel(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = (int(hex_[i : i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_token_contrast(scheme: str) -> None:
    tokens = schemes()[scheme]
    for name in (*TEXT, *GROUNDS, "tint", "rule", "rule-strong"):
        assert name in tokens, f"{scheme}: --{name} is not defined"
    low = {
        (t, g): round(contrast(tokens[t], tokens[g]), 2)
        for t in TEXT
        for g in GROUNDS
        if contrast(tokens[t], tokens[g]) < 4.5
    }
    assert low == {}, f"{scheme}: pairs under 4.5:1: {low}"


def test_dark_scheme_redefines_every_colour() -> None:
    light = schemes()["light"]
    dark = _tokens(_block(CSS, CSS.index("@media (prefers-color-scheme: dark)")))
    assert set(light) <= set(dark), set(light) - set(dark)


def _manifest() -> dict[str, str]:
    lines = (FONTS / "MANIFEST.txt").read_text(encoding="utf-8").splitlines()
    entries = [line.split("  ", 1) for line in lines if re.match(r"^[0-9a-f]{64}  ", line)]
    return {rel: digest for digest, rel in entries}


def test_fonts_vendored() -> None:
    expected = _manifest()
    on_disk = {
        p.relative_to(FONTS).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in FONTS.rglob("*")
        if p.is_file() and p.name != "MANIFEST.txt"
    }
    assert on_disk == expected
    urls = re.findall(r"@font-face\s*{[^}]*?url\(([^)]+)\)", CSS)
    assert urls, "the stylesheet declares no @font-face"
    for url in urls:
        assert url.startswith("/fonts/"), url
        assert url.removeprefix("/fonts/") in expected, url
    families = set(re.findall(r'@font-face\s*{[^}]*?font-family:\s*"([^"]+)"', CSS))
    assert families == {"Source Serif 4", "IBM Plex Sans", "IBM Plex Mono"}
    for family in ("source-serif-4", "ibm-plex-sans", "ibm-plex-mono"):
        assert f"{family}/OFL.txt" in expected, family


def test_reading_text_is_serif_and_controls_sans() -> None:
    assert re.search(r'--serif:\s*"Source Serif 4"', CSS)
    assert re.search(r'--sans:\s*"IBM Plex Sans"', CSS)
    assert re.search(r'--mono:\s*"IBM Plex Mono"', CSS)
    body = _block(CSS, CSS.index("\nbody {"))
    assert "var(--serif)" in body


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root = fixture.build(tmp_path_factory.mktemp("f34-frame"))
    site = model.load_site(root, fixture.COMMIT)
    return render.render_site(site, repo_url=REPO)


class _Frame(HTMLParser):
    """The header's links (href, label, current) and the footer's parts."""

    def __init__(self) -> None:
        super().__init__()
        self.where: list[str] = []
        self.nav: list[tuple[str, str, bool]] = []
        self.footer_links: list[tuple[str, bool]] = []  # (href, inside the disclosure)
        self.details: list[dict[str, str | None]] = []
        self.summary = ""
        self._a: tuple[str, bool] | None = None
        self._text = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag in ("header", "footer", "details", "summary"):
            self.where.append(tag)
            if tag == "details" and "footer" in self.where:
                self.details.append(a)
        elif tag == "a":
            self._a = (a.get("href") or "", "aria-current" in a)
            self._text = ""

    def handle_endtag(self, tag: str) -> None:
        if tag in ("header", "footer", "details", "summary") and tag in self.where:
            self.where.remove(tag)
        elif tag == "a" and self._a is not None:
            href, current = self._a
            if "header" in self.where:
                self.nav.append((href, self._text.strip(), current))
            elif "footer" in self.where:
                self.footer_links.append((href, "details" in self.where))
            self._a = None

    def handle_data(self, data: str) -> None:
        if self._a is not None:
            self._text += data
        if "summary" in self.where and "footer" in self.where:
            self.summary += data


def frame(html: str) -> _Frame:
    p = _Frame()
    p.feed(html)
    return p


SECTIONS = {
    "problems/index.html": "/problems/",
    "contributors/index.html": "/contributors/",
    "docs/index.html": "/docs/",
    "about/index.html": "/about/",
}


def test_header_names_four_sections_and_the_action(pages: dict[str, str]) -> None:
    f = frame(pages["index.html"])
    labels = [label for _href, label, _c in f.nav]
    for word in ("Problems", "Contributors", "Docs", "About", "Work on a statement"):
        assert word in labels, (word, labels)
    assert "Home" not in labels, "the wordmark is the way home (handoff §2)"
    assert f.nav[0][0] == "/", "the wordmark comes first and links home"


@pytest.mark.parametrize(("rel", "href"), sorted(SECTIONS.items()))
def test_header_marks_the_current_section(pages: dict[str, str], rel: str, href: str) -> None:
    current = [h for h, _label, c in frame(pages[rel]).nav if c]
    assert current == [href]


def test_header_footer(pages: dict[str, str]) -> None:
    framed = {rel: html for rel, html in pages.items() if '<footer class="provenance">' in html}
    assert len(framed) > 10
    for rel, html in framed.items():
        f = frame(html)
        assert len(f.details) == 1, rel
        assert "open" not in f.details[0], f"{rel}: the source disclosure starts closed"
        assert "Source of this page" in f.summary, rel
        inside = [h for h, d in f.footer_links if d]
        outside = [h for h, d in f.footer_links if not d]
        assert any(fixture.COMMIT in h for h in inside), f"{rel}: the commit is in the disclosure"
        assert not any(fixture.COMMIT in h for h in outside), f"{rel}: no commit outside it"
        assert "/rules/" in outside and "/about/#contact" in outside, rel
