"""Finding site-status-cause (2026-09-13, the Euclid tester): a witness-missing hole reads
"blocked on a dependency".

The four holes the Euclid skeleton spawned have no dependencies; ``graph.json`` records them
``blocked`` with ``cause: witness-missing`` (D-29, F07-R6). The node page renders the status
word alone, and ``STATUS_WORDS["blocked"]`` is "blocked on a dependency" — so the page states a
reason that is false, and hides the true one and its cure.

Mike's decision (2026-09-14, plan F04-T10): ``Renderer.status_mark(status, cause=None)``; a
witness-missing cause reads as a missing witness with the route that proposes one, and the node
page passes the row's cause. ``cause: None`` keeps today's words (pinned, unmarked). The new
keyword is looked up by signature inside the test, never called blind. Strict xfails until
F04-T10 lands (conventions §2).
"""

from __future__ import annotations

import dataclasses
import inspect
import re
from pathlib import Path
from typing import Any

import fixture

from opn_site import model, render

REPO = "https://github.com/example/graph"
TARGET = "propositional"
NODE = "and-reassoc"
FINDING = "finding site-status-cause (F04-R5, D-29, F07-R6): {}; fix: F04-T10 (Mike, 2026-09-14)"


def lead(page: str) -> str:
    m = re.search(r'<p class="lead">(.*?)</p>', page, re.S)
    assert m is not None, "the node page has no lead paragraph"
    return m.group(1)


def blocked_page(tmp_path: Path, cause: str | None) -> str:
    root = fixture.build(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    nv = site.targets[TARGET].nodes[NODE]
    entry = {**nv.graph_entry, "status": "blocked", "cause": cause, "deps": []}
    r = render.Renderer(site, repo_url=REPO, decisions_doc=None)
    return r.node(dataclasses.replace(nv, graph_entry=entry))


def test_status_mark_says_a_witness_is_missing() -> None:
    assert "cause" in inspect.signature(render.Renderer.status_mark).parameters
    mark_fn: Any = render.Renderer.status_mark
    mark = str(mark_fn("blocked", cause="witness-missing"))
    assert "witness" in mark, mark
    assert "dependency" not in mark, mark
    assert 'class="status status-blocked"' in mark


def test_node_page_of_a_witness_missing_hole_names_the_cause(tmp_path: Path) -> None:
    page = blocked_page(tmp_path, "witness-missing")
    words = lead(page)
    assert "status-blocked" in words, "guard: the page shows the blocked status"
    assert "witness" in words, words
    assert "dependency" not in words, words
    assert "/proposals/witness" in page


def test_pin_a_blocked_node_with_no_cause_reads_blocked_on_a_dependency(tmp_path: Path) -> None:
    """**PIN.** A node blocked by its dependencies (``cause: None``) keeps today's words, on the
    mark and on the page."""
    assert "blocked on a dependency" in render.Renderer.status_mark("blocked")
    assert "blocked on a dependency" in lead(blocked_page(tmp_path, None))


def test_a_refuted_dependency_has_its_own_words(tmp_path: Path) -> None:
    """``dep-refuted`` (F03-R8) is neither the witness words nor the no-cause words."""
    mark = render.Renderer.status_mark("blocked", cause="dep-refuted")
    assert "refuted" in mark and "witness" not in mark
    assert "blocked on a dependency" not in mark
    words = lead(blocked_page(tmp_path, "dep-refuted"))
    assert "a dependency was refuted" in words, words


def test_an_unknown_cause_is_shown_as_itself_escaped() -> None:
    """A cause this generator has no words for (a newer product) is named, escaped, not replaced
    by a reason it is not; a cause on a status other than blocked changes nothing."""
    payload = '<b onclick="x">new-cause'
    mark = render.Renderer.status_mark("blocked", cause=payload)
    assert "<b" not in mark and 'onclick="x"' not in mark
    assert "blocked: &lt;b onclick=&quot;x&quot;&gt;new-cause" in mark
    assert "dependency" not in mark
    assert render.Renderer.status_mark("ready", cause="witness-missing") == (
        render.Renderer.status_mark("ready")
    )
