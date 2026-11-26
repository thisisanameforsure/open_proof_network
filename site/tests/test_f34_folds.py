"""F34-T24 (R15; handoff §3.4.2, §3.4.6), the outline's half: proved statements folded for every
reader, each fold a visible box naming how many proved statements it holds, which opens in place.

A fold is a run of sibling statements whose subtrees are entirely proved, holding at least two
statements (one proved statement is shown, not boxed). Without the script every row shows.
"""

from __future__ import annotations

import functools
import http.server
import re
import socketserver
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from harness import TARGET
from test_decompositions import HOLE_IDS
from test_products import attest as gate_attest
from test_products import nodes_dir
from test_routes_view import render_tree, two_routes

from opn_site import render

PAGE = f"problems/{TARGET}/index.html"


@pytest.mark.parametrize(
    ("rows", "proved", "folds"),
    [
        # a root, two proved holes side by side: one fold of both
        ([("r", 0), ("a", 1), ("b", 1)], {"a", "b"}, [(1, 3)]),
        # one proved hole beside an open one: nothing boxed
        ([("r", 0), ("a", 1), ("b", 1)], {"a"}, []),
        # a proved hole whose own hole is open is not folded; its proved sibling alone is not either
        ([("r", 0), ("a", 1), ("a1", 2), ("b", 1)], {"a", "b"}, []),
        # a proved subtree (a, a1) beside a proved leaf b: one fold of three statements
        ([("r", 0), ("a", 1), ("a1", 2), ("b", 1), ("c", 1)], {"a", "a1", "b"}, [(1, 4)]),
        # the root itself is never folded, even when proved
        ([("r", 0), ("a", 1), ("b", 1)], {"r", "a", "b"}, [(1, 3)]),
    ],
)
def test_runs_of_proved_siblings_fold(
    rows: list[tuple[str, int]], proved: set[str], folds: list[tuple[int, int]]
) -> None:
    assert render.outline_folds(rows, proved) == folds


def proved_pair(root: Path) -> Path:
    """``two_routes`` with both holes of the first split proved: that route has nothing open."""
    for n, hole in enumerate(HOLE_IDS, start=20):
        d = nodes_dir(root) / hole
        (d / "Proof.lean").write_text(
            (d / "Statement.lean").read_text(encoding="utf-8").replace("sorry", "trivial"),
            encoding="utf-8",
        )
        gate_attest(root, hole, n=n, footprint={"nodes": []})
    return root


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    return render_tree(proved_pair(two_routes(tmp_path_factory.mktemp("f34-folds") / "g")))


def test_the_outline_boxes_the_proved_pair(pages: dict[str, str]) -> None:
    page = pages[PAGE]
    box = re.search(
        r'<li class="fold depth-(\d+)" data-fold="(\d+)">'
        r'<button type="button" class="fold-box" aria-expanded="false" hidden>([^<]+)</button>',
        page,
    )
    assert box is not None
    assert box.group(3).startswith("2 proved statements")
    members = re.findall(
        rf'<li class="depth-\d+" data-node="([^"]+)" data-in-fold="{box.group(2)}">', page
    )
    assert sorted(members) == sorted(HOLE_IDS)


# -- in a browser ------------------------------------------------------------------------------


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def served(pages: dict[str, str], tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    out = tmp_path_factory.mktemp("f34-folds-site")
    render.write(pages, out)
    handler = functools.partial(_Quiet, directory=str(out))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        yield f"http://127.0.0.1:{srv.server_address[1]}/problems/{TARGET}/"
        srv.shutdown()


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def shown(page: Any) -> list[str]:
    return list(
        page.evaluate(
            "[...document.querySelectorAll('.route-outline > li[data-node]')]"
            ".filter(li => li.checkVisibility()).map(li => li.dataset.node)"
        )
    )


def test_the_fold_is_a_box_that_opens_in_place(served: str, browser: Any) -> None:
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.emulate_media(reduced_motion="reduce")
    page.goto(served, wait_until="load")
    box = page.locator(".route-outline .fold-box")
    box.wait_for(state="visible")
    assert "2 proved statements" in box.inner_text()
    assert not set(HOLE_IDS) & set(shown(page))
    box.click()
    assert set(HOLE_IDS) <= set(shown(page))
    assert box.get_attribute("aria-expanded") == "true"
    box.click()
    assert not set(HOLE_IDS) & set(shown(page))
    page.close()


def test_without_the_script_every_row_shows(served: str, browser: Any) -> None:
    ctx = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844})
    page = ctx.new_page()
    page.goto(served, wait_until="load")
    assert set(HOLE_IDS) <= set(shown(page))
    assert not page.is_visible(".route-outline .fold-box")
    ctx.close()
