"""F04-T34 (Q35, the owner's request 2026-10-06), as F34-T5 carries it: a problem takes one row.

F04-T34 folded every statement but the problem's own into a ``<details>`` on each card, because a
problem with fifteen nodes took five times the height of one with three. F34-T5 (the 2026-11-25
handoff, §3.2) goes the rest of the way: the Problems page lists problems only, each in one row of
the same shape whatever its size, and its statements are on its own page. What F04-T34 protected
still holds and is asserted here: no problem's height grows with its statements, and nothing a
row used to fold away is lost — each row links the page that lists them, and says how many are
open.
"""

from __future__ import annotations

import json

import pytest
from fixture import COMMIT, build_with_listed_target
from problem_rows import problem_row, row_ids

from opn_site import model, render

REPO = "https://github.com/example/graph"
PROBLEMS = "problems/index.html"
MANY = "propositional"


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[dict[str, str], dict[str, int]]:
    """The rendered pages, and each target's node count as ``targets/index.json`` declares it."""
    root = build_with_listed_target(tmp_path_factory.mktemp("collapsed"))
    index = json.loads((root / "targets" / "index.json").read_text(encoding="utf-8"))
    sizes = {
        str(t["target_id"]): len(
            json.loads(
                (root / "targets" / str(t["target_id"]) / "graph.json").read_text(encoding="utf-8")
            )["nodes"]
        )
        for t in index["targets"]
    }
    return render.render_site(model.load_site(root, COMMIT), repo_url=REPO), sizes


def test_the_page_lists_problems_not_statements(
    built: tuple[dict[str, str], dict[str, int]],
) -> None:
    pages, sizes = built
    page = pages[PROBLEMS]
    assert sizes[MANY] > 1, "guard: one problem has several statements"
    assert sorted(row_ids(page)) == sorted(sizes)
    assert 'class="stmt"' not in page and '<details class="more">' not in page


def test_a_row_is_the_same_shape_whatever_its_size(
    built: tuple[dict[str, str], dict[str, int]],
) -> None:
    pages, sizes = built
    for tid in sizes:
        row = problem_row(pages[PROBLEMS], tid)
        assert row.count("<a ") <= 3, (tid, "a row links its page and its steward, not its nodes")
        assert f'href="/problems/{tid}/"' in row


def test_a_row_says_how_many_statements_are_open_and_its_page_lists_them(
    built: tuple[dict[str, str], dict[str, int]],
) -> None:
    pages, sizes = built
    row = problem_row(pages[PROBLEMS], MANY)
    assert 'data-open="' in row
    page = pages[f"problems/{MANY}/index.html"]
    assert page.count('<div class="card panel" data-node=') == sizes[MANY]
