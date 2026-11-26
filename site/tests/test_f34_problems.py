"""F34-T5 (R7): Problems lists the problems with work first, then the waiting ones as a table.

* No stat row: "All 445 · Open 602 · Proved 3" mixed statements and problems (handoff §6).
* "With work on the record" (F34-Q19): a problem with a ledger entry, a steward, or a settled
  status; one row each, sorted by its newest ledger entry, carrying its proved/open counts as a bar
  with a text label, its steward or the lack of one, its contributions and last activity.
* "Waiting for a first steward": every other problem, one table row each, all in the HTML.
* Every row carries the ``data-`` attributes ``problems.js`` filters, sorts and pages on.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import fixture
import pytest
from harness import TARGET
from test_f34_codes import visible_codes

from opn_gate import schemas
from opn_site import model, render

REPO = "https://github.com/example/graph"
ROW_ATTRS = (
    "data-id",
    "data-status",
    "data-stage",
    "data-steward",
    "data-area",
    "data-open",
    "data-name",
)


def entry(target: str, node: str, date: str, line: str = "proof") -> dict[str, Any]:
    return {
        "line": line,
        "target": target,
        "node": node,
        "artifact": "Proof.lean",
        "merge_commit": "1" * 40,
        "date": date,
        "tooling": "undeclared",
        "status": "active",
    }


def write_ledger(root: Path, identity: str, entries: list[dict[str, Any]]) -> None:
    (root / "ledger").mkdir(parents=True, exist_ok=True)
    doc = {"schema": "ledger/v1", "identity": identity, "entries": entries}
    (root / "ledger" / f"{identity}.json").write_bytes(schemas.canonical_json(doc))


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[model.Site, str]:
    root = fixture.build_with_stewards(tmp_path_factory.mktemp("f34-problems"))
    calibration_root = (
        model.load_site(root, fixture.COMMIT).targets[fixture.CALIBRATION_TARGET].root
    )
    write_ledger(
        root,
        "alice",
        [
            entry(TARGET, "and-reassoc", "2026-09-10T12:00:00Z"),
            entry(TARGET, "and-reassoc", "2026-09-11T08:00:00Z", line="attempts"),
        ],
    )
    write_ledger(
        root,
        "bob",
        [entry(fixture.CALIBRATION_TARGET, calibration_root, "2026-10-01T09:00:00Z")],
    )
    site = model.load_site(root, fixture.COMMIT)
    return site, render.render_site(site, repo_url=REPO)["problems/index.html"]


class _Rows(HTMLParser):
    """Each element with a ``data-id``: its tag, attributes, section and text."""

    def __init__(self) -> None:
        super().__init__()
        self.section = ""
        self.rows: list[dict[str, Any]] = []
        self._open: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: v or "" for k, v in attrs}
        if tag == "section" and a.get("data-section"):
            self.section = a["data-section"]
        if "data-id" in a:
            row = {"tag": tag, "attrs": a, "section": self.section, "text": ""}
            self.rows.append(row)
            self._open.append(row)
        elif self._open:
            self._open.append({"tag": tag})

    def handle_endtag(self, tag: str) -> None:
        if self._open:
            self._open.pop()

    def handle_data(self, data: str) -> None:
        for r in self._open:
            if "attrs" in r:
                r["text"] += data


def rows(html: str) -> list[dict[str, Any]]:
    p = _Rows()
    p.feed(html)
    return p.rows


def test_no_stat_row(built: tuple[model.Site, str]) -> None:
    _, html = built
    assert 'class="seg"' not in html
    assert not re.search(r"Open\s*<span class=\"n\">\d+", html)


def test_every_problem_appears_once_in_one_section(built: tuple[model.Site, str]) -> None:
    site, html = built
    found = rows(html)
    ids = [r["attrs"]["data-id"] for r in found]
    assert sorted(ids) == sorted(site.targets), ids
    assert {r["section"] for r in found} <= {"worked", "waiting"}


def test_worked_problems_come_first_newest_activity_first(built: tuple[model.Site, str]) -> None:
    _, html = built
    worked = [r for r in rows(html) if r["section"] == "worked"]
    ids = [r["attrs"]["data-id"] for r in worked]
    assert ids[:2] == [fixture.CALIBRATION_TARGET, TARGET], ids
    assert fixture.STEWARDED_TARGET in ids  # a steward is work on the record (Q19)
    lasts = [r["attrs"].get("data-last", "") for r in worked]
    dated = [x for x in lasts if x]
    assert dated == sorted(dated, reverse=True)
    assert worked[1]["attrs"]["data-last"] == "2026-09-11"
    assert "2 contributions" in worked[1]["text"] and "last 2026-09-11" in worked[1]["text"]


def test_waiting_problems_are_table_rows_with_a_steward_link(
    built: tuple[model.Site, str],
) -> None:
    _site, html = built
    waiting = [r for r in rows(html) if r["section"] == "waiting"]
    assert [r["attrs"]["data-id"] for r in waiting] == [fixture.STEWARDLESS_TARGET]
    assert waiting[0]["tag"] == "tr"
    assert f'href="/steward/{fixture.STEWARDLESS_TARGET}/"' in html


def test_each_row_carries_the_filter_attributes(built: tuple[model.Site, str]) -> None:
    _, html = built
    for r in rows(html):
        for attr in ROW_ATTRS:
            assert attr in r["attrs"], (r["attrs"]["data-id"], attr)
        assert r["attrs"]["data-stage"] in ("worked", "notstarted", "proved"), r["attrs"]
        assert r["attrs"]["data-steward"] in ("has", "needs", "none"), r["attrs"]


def test_the_bar_says_in_words_what_it_draws(built: tuple[model.Site, str]) -> None:
    site, html = built
    r = render.Renderer(site, repo_url=REPO)
    for row in (x for x in rows(html) if x["section"] == "worked"):
        tv = site.targets[row["attrs"]["data-id"]]
        proved, open_ = r.proved_count(tv), r.open_count(tv)
        assert f"{proved} proved · {open_} open" in row["text"], row["text"]
        assert row["attrs"]["data-open"] == str(open_)


def test_the_filters_are_controls_named_for_their_url_parameters(
    built: tuple[model.Site, str],
) -> None:
    _, html = built
    for name in ("q", "status", "steward", "sort"):
        assert re.search(rf'<(input|select)[^>]*name="{name}"', html), name
    chips = re.findall(r'<button[^>]*data-area="([^"]*)"', html)
    assert "" in chips and len(chips) >= 2, chips
    assert 'data-page-size="50"' in html


def test_the_page_shows_no_internal_codes(built: tuple[model.Site, str]) -> None:
    _, html = built
    assert visible_codes(html) == []
