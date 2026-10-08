"""F04-T36: three places the site cut or doubled contributor and record text.

Found 2026-10-08 on the live site (graph at or after ``6af6af057``), erdos-1094:

(c) The annex ``315301b1….md`` writes ``model_and_tooling`` as a plain YAML scalar folded over
    three lines; the front-matter reader split the head on newlines and kept the first physical
    line, so the label read "sources read via erdosproblems.com,, 2026-10-08…". The front matter
    is YAML (``annex/v2``), so it is read as YAML — every value as the string it is written as.
(d) An outline's title is its first line cut at 140 characters, mid-word ("… a reading of the
    formal statement agai"). It is cut at a word boundary and says it was cut ("…").
(e) The problem page's provenance line is ``<title>. <source>``; a title that already ends a
    sentence (erdos-1094's ends "exceptions.") read "exceptions.. Imported from …".
"""

from __future__ import annotations

import re
from pathlib import Path

import fixture
import pytest
import yaml
from harness import TARGET

from opn_gate import products
from opn_site import model, render

REPO = "https://github.com/example/graph"
NODE = "and-reassoc"

#: erdos-1094's annex front matter at graph 835f1239, byte for byte, with the body replaced.
LIVE_ANNEX = (
    "---\n"
    "contributor: t1008-c\n"
    "date: '2026-10-08T13:06:59Z'\n"
    "licence: CC-BY-4.0\n"
    "model_and_tooling: Claude Opus 5.5 as agent t1008-c; sources read via erdosproblems.com,\n"
    "  MathOverflow API, publisher abstracts; exception box checked by a Python Kummer-carry\n"
    "  script\n"
    f"node: {NODE}\n"
    "schema: annex/v2\n"
    "steps:\n"
    "- id: h_fixed_k\n"
    "  summary: 'for each fixed k > 0, only finitely many n >= k^2 have minFac C(n,k) >\n"
    "    n/k (indeed n < k! + k): elementary, Erdos''s observation'\n"
    "---\n"
    "# Short title\n\nBody.\n"
)
FOLDED = (
    "Claude Opus 5.5 as agent t1008-c; sources read via erdosproblems.com, MathOverflow API, "
    "publisher abstracts; exception box checked by a Python Kummer-carry script"
)
#: A live outline title (erdos-1094's prior-art annex), 168 characters.
LONG_TITLE = (
    "Prior art and the state of the problem (Erdős #1094, the Erdős\u2013Lacampagne\u2013Selfridge "
    "conjecture), with a reading of the formal statement against the published one, and gaps"
)


def _write_annex(root: Path, name: str, text: str) -> None:
    annex = root / "targets" / TARGET / "nodes" / NODE / "annex"
    annex.mkdir(exist_ok=True)
    (annex / name).write_text(text, encoding="utf-8")


def _render(root: Path) -> dict[str, str]:
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)


# --- (c) folded front matter -------------------------------------------------------------------


def test_a_folded_front_matter_value_is_read_whole(tmp_path: Path) -> None:
    f = tmp_path / "a.md"
    f.write_text(LIVE_ANNEX, encoding="utf-8")
    p = model.parse_prose(f, tmp_path)
    assert p.model == FOLDED
    assert (p.author, p.date, p.licence) == ("t1008-c", "2026-10-08T13:06:59Z", "CC-BY-4.0")
    assert p.text == "# Short title\n\nBody.\n"


def test_the_annex_label_shows_the_whole_model_and_no_double_comma(tmp_path: Path) -> None:
    root = fixture.curated(tmp_path)
    _write_annex(root, "3" * 64 + ".md", LIVE_ANNEX)
    page = _render(root)[f"nodes/{TARGET}/{NODE}/index.html"]
    labels = [s for s in page.split('<p class="label">')[1:] if s.startswith("Untrusted: annex")]
    assert len(labels) == 1, labels
    assert f"drafted with {render.esc(FOLDED)}, 2026-10-08T13:06:59Z" in labels[0], labels[0]
    assert ",," not in labels[0], labels[0]


def test_an_unquoted_timestamp_stays_the_text_it_was_written_as(tmp_path: Path) -> None:
    """YAML would read ``2026-10-08T13:06:59Z`` as a datetime and print it back differently; the
    label shows what the contributor wrote."""
    f = tmp_path / "a.md"
    f.write_text("---\nauthor: alice\ndate: 2026-10-08T13:06:59Z\n---\nbody\n", encoding="utf-8")
    assert model.parse_prose(f, tmp_path).date == "2026-10-08T13:06:59Z"


def test_front_matter_that_is_not_yaml_is_still_read_line_by_line(tmp_path: Path) -> None:
    """A contributor's malformed head must not take a page down, nor lose the fields it does
    state: a value with a second colon is not valid YAML and was read before."""
    f = tmp_path / "a.md"
    f.write_text("---\nauthor: alice\nmodel: tool: v2\n---\nbody\n", encoding="utf-8")
    p = model.parse_prose(f, tmp_path)
    assert (p.author, p.model) == ("alice", "tool: v2")


def test_a_null_model_is_still_no_model(tmp_path: Path) -> None:
    f = tmp_path / "a.md"
    f.write_text("---\ncontributor: bob\nmodel_and_tooling: null\n---\nbody\n", encoding="utf-8")
    p = model.parse_prose(f, tmp_path)
    assert (p.author, p.model) == ("bob", None)


# --- (d) outline titles ------------------------------------------------------------------------


def _outline_titles(page: str) -> list[str]:
    return re.findall(r'<span class="untrusted-title">(.*?)</span>', page)


@pytest.fixture(scope="module")
def outlines(tmp_path_factory: pytest.TempPathFactory) -> list[str]:
    root = fixture.curated(tmp_path_factory.mktemp("outline-titles"))
    _write_annex(root, "4" * 64 + ".md", f"# {LONG_TITLE}\n\nBody.\n")
    _write_annex(root, "5" * 64 + ".md", "# A short outline\n\nBody.\n")
    _write_annex(root, "6" * 64 + ".md", "x" * 200 + "\n")
    return _outline_titles(_render(root)[f"problems/{TARGET}/index.html"])


def test_a_long_outline_title_is_cut_at_a_word_and_says_so(outlines: list[str]) -> None:
    cut = next(t for t in outlines if t.startswith("Prior art"))
    assert cut.endswith("…"), cut
    kept = cut.removesuffix("…").rstrip()
    assert render.esc(LONG_TITLE).startswith(kept), cut
    rest = render.esc(LONG_TITLE)[len(kept) :]
    assert rest[:1] in {" ", ","}, f"cut mid-word: {cut!r}"
    assert len(kept) <= 140, len(kept)


def test_a_short_outline_title_is_left_whole(outlines: list[str]) -> None:
    assert "A short outline" in outlines


def test_a_title_with_no_space_to_cut_at_is_cut_and_marked(outlines: list[str]) -> None:
    cut = next(t for t in outlines if t.startswith("xxx"))
    assert cut == "x" * 140 + "…", cut


# --- (e) the sentence after a title ------------------------------------------------------------


def _provenance_line(tmp_path: Path, title: str) -> str:
    root = fixture.build_with_listed_target(tmp_path)
    record = root / "targets" / fixture.LISTED_TARGET / "target.yaml"
    doc = yaml.safe_load(record.read_text(encoding="utf-8"))
    doc["title"] = title
    record.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    page = _render(root)[f"problems/{fixture.LISTED_TARGET}/index.html"]
    m = re.search(r'<p class="provenance-line">(.*?)</p>', page, re.S)
    assert m is not None, "no provenance line"
    return m.group(1)


@pytest.mark.parametrize(
    ("title", "shown"),
    [
        ("with only finitely many exceptions.", "with only finitely many exceptions. Imported"),
        ("Is the sum irrational?", "Is the sum irrational? Imported"),
        ("Surely not!", "Surely not! Imported"),
        ("A note (see below.)", "A note (see below.) Imported"),
        ("A listed open problem", "A listed open problem. Imported"),
    ],
)
def test_a_title_that_ends_a_sentence_gets_no_second_full_stop(
    tmp_path: Path, title: str, shown: str
) -> None:
    line = _provenance_line(tmp_path, title)
    assert line.startswith(render.esc(shown)), line
    assert ".." not in line and "?." not in line and "!." not in line, line
