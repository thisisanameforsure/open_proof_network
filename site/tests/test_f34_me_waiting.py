"""F34-T19 (R20; handoff §3.5): My problems groups what waits for a steward by problem and
statement, and approves every waiting section of one statement's words with one act — one
``POST /approvals`` per version, carrying its sections.

The ``/me/`` shell is static: each statement's group carries, as data, exactly the approvals the
statement's own pages offer section by section (every ``words-approve`` slot not final), so
"Approve all" there is the same set of acts as pressing each Approve on the node pages.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from html import unescape
from typing import Any

import gloss_fixture as gf
import pytest
from harness import TARGET

from opn_site import model, render

REPO = "https://github.com/example/graph"
API = "https://api.example.org"

SLOT = re.compile(
    r'<div class="words-approve" data-target="([^"]*)" data-node="([^"]*)" data-kind="([^"]*)" '
    r'data-section="([^"]*)" data-version="([^"]*)" data-state="([^"]*)" hidden></div>'
)


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root = gf.glossed_tree(tmp_path_factory.mktemp("f34-me-waiting"))
    return render.render_site(model.load_site(root, gf.COMMIT), repo_url=REPO, api_url=API)


def offered(pages: dict[str, str], target: str) -> set[tuple[str, str, str, str]]:
    """Every approval the target's pages offer: (node, kind, version, section), not final."""
    found = set()
    for rel, page in pages.items():
        if rel == "me/index.html":
            continue
        for t, node, kind, section, version, state in SLOT.findall(page):
            if t == target and state != "verified":
                found.add((node, kind, version, section))
    return found


def groups(me: str, target: str) -> list[dict[str, Any]]:
    opening = f'<div class="waiting" data-target="{re.escape(target)}" hidden>'
    block = re.search(rf"{opening}(.*?)</div><!-- /waiting -->", me, re.S)
    assert block is not None, "no waiting block for the target"
    out = []
    section = (
        r'<section class="waiting-statement" data-node="([^"]*)" '
        r'data-approvals="([^"]*)">(.*?)</section>'
    )
    for m in re.finditer(section, block.group(1), re.S):
        approvals = json.loads(unescape(m.group(2)))
        out.append({"node": m.group(1), "approvals": approvals, "html": m.group(3)})
    return out


def test_each_statement_carries_exactly_the_approvals_its_pages_offer(
    pages: dict[str, str],
) -> None:
    me = pages["me/index.html"]
    found = groups(me, TARGET)
    assert found, "guard: the fixture has words waiting"
    carried = Counter(
        (g["node"], a["kind"], a["version"], s)
        for g in found
        for a in g["approvals"]
        for s in (a["sections"] or [""])
    )
    assert all(n == 1 for n in carried.values()), carried
    assert set(carried) == offered(pages, TARGET)


def test_one_post_per_version_and_one_group_per_statement(pages: dict[str, str]) -> None:
    found = groups(pages["me/index.html"], TARGET)
    nodes = [g["node"] for g in found]
    assert len(nodes) == len(set(nodes)), nodes
    for g in found:
        versions = [(a["kind"], a["version"]) for a in g["approvals"]]
        assert len(versions) == len(set(versions)), versions


def test_the_most_waiting_comes_first_and_each_says_how_many(pages: dict[str, str]) -> None:
    found = groups(pages["me/index.html"], TARGET)
    counts = [sum(len(a["sections"] or [""]) for a in g["approvals"]) for g in found]
    assert counts == sorted(counts, reverse=True), counts
    for g, n in zip(found, counts, strict=True):
        assert re.search(rf'<span class="waiting-count">{n} section', str(g["html"])), g["html"]
