"""F04-T63 (Q61): the Problems page groups problems by topic and names each one's collection.

Wave two (F14-T18) brings statements from outside the Erdős list — Wikipedia's Goldbach and
Schanuel, Green's problem 58, a graph-theory paper, a series — into a page that listed every
problem in one flat run sorted by id. The owner asked for the registry's own organisation: by
topic. Every problem sits under its first domain tag, each card says which collection its
statement came from, and a filter or search that empties a topic hides its heading.
"""

from __future__ import annotations

import functools
import http.server
import re
import shutil
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from fixture import COMMIT, LISTED_TARGET, build_with_listed_target
from harness import TARGET, take_in
from problem_rows import problem_row

from opn_site import model, render

REPO = "https://github.com/example/graph"
PAPER_TARGET = "graph-problem"
PAPER_ROOT = "graph-root"


def build(tmp_path: Path) -> Path:
    """The listed-target fixture plus a combinatorics problem imported from a paper."""
    root = build_with_listed_target(tmp_path)
    staged = tmp_path / PAPER_ROOT
    shutil.copytree(root / "targets" / TARGET / "nodes" / "and-reassoc", staged)
    meta = yaml.safe_load((staged / "META.yaml").read_text(encoding="utf-8"))
    meta["id"] = PAPER_ROOT
    (staged / "META.yaml").write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    (staged / "Proof.lean").unlink(missing_ok=True)
    take_in(
        root,
        target_id=PAPER_TARGET,
        root_dir=staged,
        title="A graph colouring bound",
        track="open",
        informal="Every graph's chromatic number is bounded by a function of two parameters.",
        domains=["combinatorics", "number-theory"],
        source={
            "kind": "formal-conjectures",
            "ref": "FormalConjectures/Paper/GraphBound.lean",
            "url": "https://github.com/example/fc/blob/abc/FormalConjectures/Paper/GraphBound.lean",
        },
        provenance={
            "statement_source": "formal-conjectures",
            "author": "The Formal Conjectures Authors",
            "adversarially_reviewed": False,
            "upstream_commit": "c" * 40,
            "upstream_path": "FormalConjectures/Paper/GraphBound.lean",
        },
    )
    from opn_gate import products  # noqa: PLC0415

    products.generate(root, rendered_from=COMMIT, commit_time="2026-09-11T00:00:00Z").write(root)
    return root


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build(tmp_path_factory.mktemp("by-topic"))


@pytest.fixture(scope="module")
def problems(built: Path) -> str:
    pages = render.render_site(model.load_site(built, COMMIT), repo_url=REPO)
    return pages["problems/index.html"]


def areas(page: str) -> dict[str, str]:
    """F34-T5: each problem's area, from its row's ``data-area``."""
    return dict(
        re.findall(r'<(?:article|tr)\b[^>]*data-id="([^"]+)"[^>]*data-area="([^"]+)"', page)
    )


def test_every_problem_sits_once_under_its_first_domain(problems: str) -> None:
    """F04-T63 (Q61), as F34-T5 carries it: the topic headings became area chips with counts
    and each row names its area; a problem counts once, under its first domain."""
    by_row = areas(problems)
    assert by_row == {
        PAPER_TARGET: "combinatorics",
        LISTED_TARGET: "number-theory",
        TARGET: "other",
    }, by_row
    assert problems.count(f'data-id="{PAPER_TARGET}"') == 1
    for word, tag in (
        ("Combinatorics", "combinatorics"),
        ("Number theory", "number-theory"),
        ("Other", "other"),
    ):
        assert re.search(
            rf'<button[^>]*data-area="{tag}"[^>]*>{word} <span class="n">1</span>', problems
        ), word


def test_a_card_names_the_collection_its_statement_came_from(problems: str) -> None:
    card = problem_row(problems, PAPER_TARGET)
    assert '<span class="collection">Papers</span>' in card
    # The network's own statement names no collection.
    own = problem_row(problems, TARGET)
    assert 'class="collection"' not in own


@pytest.mark.parametrize(
    ("path", "label"),
    [
        ("FormalConjectures/ErdosProblems/52.lean", "Erdős Problems"),
        ("FormalConjectures/Wikipedia/Schanuel.lean", "Wikipedia"),
        ("FormalConjectures/GreensOpenProblems/58.lean", "Green's open problems"),
        ("FormalConjectures/Millennium/RiemannHypothesis.lean", "Millennium problems"),
        ("FormalConjectures/OEIS/A000001.lean", "OEIS"),
        ("FormalConjectures/OpenQuantumProblems/1.lean", "Open Quantum Problems"),
    ],
)
def test_the_collection_label_reads_the_upstream_path(path: str, label: str) -> None:
    assert render.collection_label({"provenance": {"upstream_path": path}}) == label


# --- in a browser: an emptied topic hides its heading ---------------------------------------------


def serve(handler: Any) -> tuple[http.server.ThreadingHTTPServer, str]:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


@pytest.fixture(scope="module")
def served(built: Path, tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    site_dir = tmp_path_factory.mktemp("by-topic-site")
    render.write(render.render_site(model.load_site(built, COMMIT), repo_url=REPO), site_dir)

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_args: object) -> None:
            return

    server, origin = serve(functools.partial(Quiet, directory=str(site_dir)))
    yield origin
    server.shutdown()


VISIBLE_TOPICS = (
    "() => Array.from(document.querySelectorAll('.topic'))"
    ".filter(s => !s.hidden).map(s => s.dataset.topic)"
)


VISIBLE_ROWS = (
    "() => Array.from(document.querySelectorAll('[data-id]'))"
    ".filter(r => !r.hidden).map(r => r.dataset.id)"
)


def test_a_search_that_empties_a_topic_hides_its_heading(served: str) -> None:
    """Restated by F34-T5 (R7): the Problems page has no topic headings any more, only rows and
    an area filter; a search narrows the rows to the problems it matches, and one that matches
    nothing leaves none."""
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 900})
        page.goto(served + "/problems/")
        page.wait_for_selector('[name="q"]')
        assert page.evaluate(VISIBLE_TOPICS) == []  # no topic headings on the page
        assert PAPER_TARGET in page.evaluate(VISIBLE_ROWS)
        page.fill('[name="q"]', PAPER_TARGET)
        visible = page.evaluate(VISIBLE_ROWS)
        assert visible == [PAPER_TARGET], visible
        page.fill('[name="q"]', "nothing-matches-this")
        visible = page.evaluate(VISIBLE_ROWS)
        assert visible == [], visible
        browser.close()
