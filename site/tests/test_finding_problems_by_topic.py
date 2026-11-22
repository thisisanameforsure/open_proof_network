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


def topics(page: str) -> list[tuple[str, list[str]]]:
    """Each topic section in page order with the ids of the cards inside it."""
    out = []
    for m in re.finditer(
        r'<section class="topic" data-topic="([^"]+)"[^>]*>(.*?)</section>', page, re.S
    ):
        out.append(
            (
                m.group(1),
                re.findall(r'<article class="card problem"[^>]*id="p-([^"]+)"', m.group(2)),
            )
        )
    return out


def test_every_problem_sits_once_under_its_first_domain(problems: str) -> None:
    groups = topics(problems)
    # Topics in the order of their words; a problem with no curated record sits under "Other".
    assert [t for t, _ in groups] == ["combinatorics", "number-theory", "other"], groups
    by_topic = dict(groups)
    assert by_topic["combinatorics"] == [PAPER_TARGET]
    assert by_topic["number-theory"] == [LISTED_TARGET]
    assert by_topic["other"] == [TARGET]
    # Each card exactly once, whatever its second domain says.
    assert problems.count(f'id="p-{PAPER_TARGET}"') == 1
    assert re.search(
        r'<h2 class="topic-head"[^>]*>Combinatorics <span class="n">1</span>', problems
    )
    assert re.search(
        r'<h2 class="topic-head"[^>]*>Number theory <span class="n">1</span>', problems
    )
    assert re.search(r'<h2 class="topic-head"[^>]*>Other <span class="n">1</span>', problems)
    # A card knows its topic, so the filter script can hide an emptied heading.
    assert re.search(
        rf'<article class="card problem"[^>]*data-topic="combinatorics"[^>]*id="p-{PAPER_TARGET}"',
        problems,
    )


def test_a_card_names_the_collection_its_statement_came_from(problems: str) -> None:
    card = problems.split(f'id="p-{PAPER_TARGET}"', 1)[1].split("</article>", 1)[0]
    assert '<span class="collection">Papers</span>' in card
    # The network's own statement names no collection.
    own = problems.split(f'id="p-{TARGET}"', 1)[1].split("</article>", 1)[0]
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


def test_a_search_that_empties_a_topic_hides_its_heading(served: str) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 900})
        page.goto(served + "/problems/")
        page.wait_for_selector(".search:not([hidden])")
        visible = page.evaluate(VISIBLE_TOPICS)
        assert visible == ["combinatorics", "number-theory", "other"]
        page.fill(".search", PAPER_TARGET)
        visible = page.evaluate(VISIBLE_TOPICS)
        assert visible == ["combinatorics"], visible
        page.fill(".search", "nothing-matches-this")
        visible = page.evaluate(VISIBLE_TOPICS)
        assert visible == [], visible
        browser.close()
