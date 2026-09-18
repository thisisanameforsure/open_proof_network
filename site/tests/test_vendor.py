"""F04-T13: KaTeX vendored same-origin (R10; Q15), pinned by a manifest of hashes.

The site renders the TeX a curated record's informal text carries. Nothing external is loaded:
the release's script, its auto-render helper, its stylesheet (woff2 sources only) and the fonts
live under ``static/vendor/katex`` with the MIT licence, and ``MANIFEST.txt`` names each file's
sha256 so the copy cannot drift without the test saying so.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import fixture
import pytest

from opn_site import model, render

REPO = "https://github.com/example/graph"
VENDOR = render.STATIC / "vendor" / "katex"
VERSION = "0.18.7"


def manifest() -> dict[str, str]:
    lines = (VENDOR / "MANIFEST.txt").read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith(f"katex {VERSION} ")
    entries = [line.split("  ", 1) for line in lines if "  " in line and len(line) > 64]
    return {rel: digest for digest, rel in entries}


def test_every_vendored_file_is_in_the_manifest_and_matches_it() -> None:
    expected = manifest()
    on_disk = {
        p.relative_to(VENDOR).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in VENDOR.rglob("*")
        if p.is_file() and p.name != "MANIFEST.txt"
    }
    assert on_disk == expected
    for name in ("katex.min.js", "auto-render.min.js", "katex.min.css", "LICENSE"):
        assert name in expected, name
    assert "MIT License" in (VENDOR / "LICENSE").read_text(encoding="utf-8")
    fonts = [rel for rel in expected if rel.startswith("fonts/")]
    assert fonts and all(rel.endswith(".woff2") for rel in fonts)


def test_the_stylesheet_names_only_local_woff2_fonts() -> None:
    css = (VENDOR / "katex.min.css").read_text(encoding="utf-8")
    assert "http" not in css and "//" not in css.replace("/*", "").replace("*/", "")
    assert ".ttf" not in css and ".woff)" not in css and "url(fonts/" in css
    assert (VENDOR / "fonts" / "KaTeX_Main-Regular.woff2").is_file()


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root = fixture.build_with_listed_target(tmp_path_factory.mktemp("math"))
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)


def test_the_pages_with_record_prose_load_katex_same_origin(pages: dict[str, str]) -> None:
    """R10: the three page kinds that show an informal statement carry the stylesheet in their
    head and the scripts at their end, every one a path the generator itself emits; the
    statement record and Docs pages carry none."""
    for rel in (
        "index.html",
        "problems/index.html",
        f"problems/{fixture.LISTED_TARGET}/index.html",
    ):
        page = pages[rel]
        assert render.MATH_HEAD in page and render.MATH_SCRIPTS in page, rel
    for rel in (
        f"nodes/{fixture.LISTED_TARGET}/{fixture.LISTED_ROOT}/index.html",
        "docs/index.html",
    ):
        assert "katex" not in pages[rel], rel
    for src in render.SCRIPTS:
        assert src.lstrip("/") in pages, src
    assert "vendor/katex/katex.min.css" in pages
    assert pages["vendor/katex/katex.min.js"].startswith("!function")
    assert "renderMathInElement" in pages["math.js"] and "trust: false" in pages["math.js"]


def test_only_the_informal_text_is_marked_for_math(pages: dict[str, str]) -> None:
    """The informal statement is wrapped in ``.math``; Lean, ids and everything else are not,
    so a dollar sign in a statement or a file name is never read as a delimiter."""
    page = pages["problems/index.html"]
    assert f'<span class="math">{render.esc(fixture.PARAPHRASE)}</span>' in page
    assert page.count('class="math"') == 1  # the listed target's; the other has no record
    detail = pages[f"problems/{fixture.LISTED_TARGET}/index.html"]
    assert detail.count('class="math"') == 2  # the header and the record section
    assert '<pre class="lean statement' in detail and "math" not in detail.split("<pre", 1)[1][:200]


def test_the_fonts_are_written_beside_the_pages(tmp_path: Path) -> None:
    root = fixture.build(tmp_path)
    files = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)
    out = tmp_path / "out"
    written = render.write(files, out)
    assert (out / "vendor" / "katex" / "fonts" / "KaTeX_Main-Regular.woff2").is_file()
    assert (out / "vendor" / "katex" / "katex.min.css").is_file()
    assert any(p.suffix == ".woff2" for p in written)
