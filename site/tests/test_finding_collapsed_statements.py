"""F04-T34 (Q35, the owner's request 2026-10-06): a problem card shows only its own statement.

The Problems page listed every statement under every problem, so a problem with fifteen nodes
took five times the height of one with three. Each card now shows the problem's own statement
(the root) and folds the rest into a native ``<details>`` whose summary says how many more there
are and how many of them are open. A problem with one statement draws no toggle. The owner's
calls: cards need not be exactly equal in height, and the "Open" filter leaves cards collapsed,
the summary's open count saying what is inside. Search opens a card whose match is folded away.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fixture import COMMIT, LISTED_ROOT, LISTED_TARGET, build_with_listed_target

from opn_site import model, render

REPO = "https://github.com/example/graph"
PROBLEMS = "problems/index.html"
MANY = "propositional"


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[dict[str, str], dict[str, str]]:
    """The rendered pages, and each target's root as ``targets/index.json`` declares it."""
    root = build_with_listed_target(tmp_path_factory.mktemp("collapsed"))
    index = json.loads((root / "targets" / "index.json").read_text(encoding="utf-8"))
    roots = {str(t["target_id"]): str(t["root"]) for t in index["targets"]}
    return render.render_site(model.load_site(root, COMMIT), repo_url=REPO), roots


@pytest.fixture(scope="module")
def pages(built: tuple[dict[str, str], dict[str, str]]) -> dict[str, str]:
    return built[0]


def card(page: str, tid: str) -> str:
    (found,) = [a for a in page.split("<article")[1:] if f'id="p-{tid}"' in a.split(">", 1)[0]]
    return found.split("</article>", 1)[0]


def rows(html: str) -> list[str]:
    return re.findall(r'<div class="stmt"[^>]*>.*?<span class="node">(.*?)</span>', html)


def test_a_card_shows_its_own_statement_and_folds_the_rest(
    built: tuple[dict[str, str], dict[str, str]],
) -> None:
    pages, roots = built
    many_root = roots[MANY]
    html = card(pages[PROBLEMS], MANY)
    assert html.count("<details") == 1, "one fold per card"
    before, folded = html.split("<details", 1)
    shown = rows(before)
    assert len(shown) == 1 and f">{many_root}<" in shown[0], "the root alone sits outside the fold"
    inside = rows(folded.split("</details>", 1)[0])
    assert len(inside) == 2, "every other statement sits inside the fold"
    assert not any(f">{many_root}<" in r for r in inside)


def test_the_fold_is_closed_and_says_what_it_holds(pages: dict[str, str]) -> None:
    html = card(pages[PROBLEMS], MANY)
    tag = re.search(r"<details[^>]*>", html)
    assert tag and " open" not in tag.group(0), "collapsed by default"
    summary = re.search(r"<summary[^>]*>(.*?)</summary>", html, re.S)
    assert summary
    words = re.sub(r"<[^>]+>", "", summary.group(1))
    assert "2 more statements" in words
    # The fold's open count is the workable rows inside it, the set the Open filter keeps.
    folded = html.split("<details", 1)[1].split("</details>", 1)[0]
    n_open = folded.count('data-workable="1"')
    if n_open:
        assert f"{n_open} open" in words
    else:
        assert "open" not in words


def test_a_one_statement_problem_draws_no_toggle(
    built: tuple[dict[str, str], dict[str, str]],
) -> None:
    pages, roots = built
    assert roots[LISTED_TARGET] == LISTED_ROOT
    html = card(pages[PROBLEMS], LISTED_TARGET)
    assert "<details" not in html and "<summary" not in html
    shown = rows(html)
    assert len(shown) == 1 and LISTED_ROOT in shown[0]


def test_one_more_statement_is_singular() -> None:
    assert render.more_statements_words(1, 0) == "1 more statement"
    assert render.more_statements_words(1, 1) == "1 more statement, 1 open"
    assert render.more_statements_words(14, 3) == "14 more statements, 3 open"


def test_search_opens_a_fold_that_holds_a_match_and_filters_hide_an_empty_one() -> None:
    script = (Path(render.STATIC) / "problems.js").read_text(encoding="utf-8")
    assert "details.more" in script, "the script finds each card's fold"
    assert re.search(r"\.open\s*=\s*true", script), "a search match inside the fold opens it"
    assert re.search(r"\.hidden\s*=\s*!\s*\w+", script)
    assert "data-auto-open" in script, "only a fold the search opened is closed again by it"
