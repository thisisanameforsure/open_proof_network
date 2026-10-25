"""F04-T57 (R15, AC20; D-36 v3.48): the home page says what the network is for and shows the
record moving, not counts. The hero leads with understanding; six contrasting lines say how the
network differs, each true of the record it is rendered from; a list of what happened lately is
read from the ledger and the gloss and explainer chains; three doors; and one problem drawn.

Written red first, against the counts card and the "Open now" list (2026-10-24)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import fixture
import pytest
from fixture import SIGNER_LOGIN, build_with_stewards
from harness import TARGET

from opn_gate import schemas
from opn_site import activity, config, model, render

REPO = "https://github.com/example/graph"
HERO = "A proof is finished when someone can explain it."
STEWARD_ANNOUNCED = (
    "Each problem has a named mathematician who answers for it, or says plainly that it does "
    "not have one yet."
)
STEWARD_ENFORCED = "Each problem has a named mathematician who answers for it."


def entry(
    line: str, node: str, date: str, *, artifact: str = "Proof.lean", **kw: Any
) -> dict[str, Any]:
    return {
        "line": line,
        "target": TARGET,
        "node": node,
        "artifact": artifact,
        "merge_commit": "1" * 40,
        "date": date,
        "tooling": "undeclared",
        "status": "active",
        **kw,
    }


def write_ledger(root: Path, identity: str, entries: list[dict[str, Any]]) -> None:
    (root / "ledger").mkdir(parents=True, exist_ok=True)
    doc = {"schema": "ledger/v1", "identity": identity, "entries": entries}
    (root / "ledger" / f"{identity}.json").write_bytes(schemas.canonical_json(doc))


@pytest.fixture(scope="module")
def ledgered(tmp_path_factory: pytest.TempPathFactory) -> tuple[model.Site, dict[str, str]]:
    root = fixture.build(tmp_path_factory.mktemp("home-ledger"))
    write_ledger(
        root,
        "alice",
        [
            entry("statement", "and-reassoc", "2026-09-08T09:00:00Z", artifact="Statement.lean"),
            entry("proof", "and-reassoc", "2026-09-10T12:00:00Z"),
            entry(
                "attempts",
                "tutorial-and-swap",
                "2026-09-11T08:00:00Z",
                artifact="attempts/2026-09-11-alice.yaml",
                route_class="induction",
            ),
            entry(
                "attempts",
                "and-reassoc",
                "2026-09-11T09:00:00Z",
                artifact="attempts/2026-09-11b-alice.yaml",
                route_class="induction",
            ),
            entry(
                "attempts",
                "and-reassoc",
                "2026-09-12T09:00:00Z",
                artifact="attempts/2026-09-12-alice.yaml",
                route_class="induction",
                status="revoked",
            ),
        ],
    )
    site = model.load_site(root, fixture.COMMIT)
    return site, render.render_site(site, repo_url=REPO, featured_target=TARGET)


@pytest.fixture(scope="module")
def stewarded(tmp_path_factory: pytest.TempPathFactory) -> tuple[model.Site, dict[str, str]]:
    site = model.load_site(
        build_with_stewards(tmp_path_factory.mktemp("home-signed")), fixture.COMMIT
    )
    return site, render.render_site(site, repo_url=REPO)


def rows(home: str) -> list[tuple[str, str, str]]:
    """(kind, date, row html) for each row of the record list, in page order."""
    return re.findall(
        r'<li class="pulse-row" data-kind="([a-z-]+)" data-date="([0-9-]+)">(.*?)</li>', home, re.S
    )


# -- what the page no longer says ----------------------------------------------------------------


def test_the_home_page_carries_no_network_counts(
    ledgered: tuple[model.Site, dict[str, str]],
) -> None:
    """R15: the counts card and the "Open now" list are gone; no count of the network's own
    stands on the page (the needs-a-steward link keeps its count: F23-R5 is an invitation)."""
    _site, pages = ledgered
    home = pages["index.html"]
    for gone in (
        'class="counts-card"',
        "proved statements explained",
        '<span class="l">open statements</span>',
        '<span class="l">stewards</span>',
        '<span class="l">problems</span>',
        'class="open-now"',
        "Open now",
    ):
        assert gone not in home, gone


# -- the hero and the six lines -------------------------------------------------------------------


def test_the_hero_leads_with_understanding(ledgered: tuple[model.Site, dict[str, str]]) -> None:
    _site, pages = ledgered
    home = pages["index.html"]
    assert f"<h1>{HERO}</h1>" in home
    assert home.index("<h1>") < home.index("Same machines. Different rules.")
    assert 'href="#worked"' in home  # "See how a problem is worked" scrolls to the drawing


def test_the_six_lines_are_pairs_each_crossing_out_one_thing(
    ledgered: tuple[model.Site, dict[str, str]],
) -> None:
    _site, pages = ledgered
    home = pages["index.html"]
    pairs = re.findall(r'<li class="rule-pair"><s>([^<]+)</s><span>([^<]+)</span></li>', home)
    assert len(pairs) == 6, pairs
    said = [here for _not, here in pairs]
    assert "Nothing is announced. The record is the announcement." in said
    assert "Every failed attempt is published, with where it stopped." in said
    assert "Done when a person has explained it." in said


def test_the_steward_line_claims_the_rule_only_when_the_record_enforces_it(
    ledgered: tuple[model.Site, dict[str, str]],
    stewarded: tuple[model.Site, dict[str, str]],
) -> None:
    """The owner's "keep it" (2026-10-24): the line stays, and says no more than the gate does —
    the strong sentence once ``policy.json`` enforces the rule, the honest one until then."""
    plain, plain_pages = ledgered
    ruled, ruled_pages = stewarded
    assert plain.steward_rule_enforced is False and ruled.steward_rule_enforced is True
    assert STEWARD_ANNOUNCED in plain_pages["index.html"]
    assert STEWARD_ENFORCED in ruled_pages["index.html"]
    assert STEWARD_ANNOUNCED not in ruled_pages["index.html"]


def test_no_line_claims_what_the_fixture_record_does_not_show(
    ledgered: tuple[model.Site, dict[str, str]],
) -> None:
    """Q55: the two lines found untrue of the live record on 2026-10-24 stay off the page."""
    _site, pages = ledgered
    home = pages["index.html"]
    assert "proposed by the mathematicians who care about them" not in home
    assert "signs that it says what the problem says" not in home
    assert "marked unchecked until someone who did not write it signs" in home


# -- the record, newest first ----------------------------------------------------------------------


def test_the_record_list_is_newest_first_and_skips_revoked_credit(
    ledgered: tuple[model.Site, dict[str, str]],
) -> None:
    _site, pages = ledgered
    found = rows(pages["index.html"])
    dates = [d for _k, d, _r in found]
    assert dates == sorted(dates, reverse=True), dates
    kinds = [k for k, _d, _r in found]
    assert "proved" in kinds and "proposed" in kinds and "dead-end" in kinds
    assert "2026-09-12" not in dates  # the revoked entry is credit withdrawn, not news (D-18)


def test_one_day_of_one_kind_on_one_problem_is_one_row(
    ledgered: tuple[model.Site, dict[str, str]],
) -> None:
    """Two postmortems filed the same day on one problem read as one row naming the count, so
    a batch cannot fill the list."""
    _site, pages = ledgered
    dead = [r for k, d, r in rows(pages["index.html"]) if k == "dead-end" and d == "2026-09-11"]
    assert len(dead) == 1
    assert "2 attempts" in dead[0]


def test_each_row_links_where_it_happened(ledgered: tuple[model.Site, dict[str, str]]) -> None:
    _site, pages = ledgered
    proved = next(r for k, _d, r in rows(pages["index.html"]) if k == "proved")
    assert f'href="/nodes/{TARGET}/and-reassoc/"' in proved


def test_words_and_their_signatures_reach_the_list(
    stewarded: tuple[model.Site, dict[str, str]],
) -> None:
    """A signed explainer is a person standing behind a proof: the list names them."""
    _site, pages = stewarded
    signed = [r for k, _d, r in rows(pages["index.html"]) if k == "vouched"]
    assert signed, rows(pages["index.html"])
    assert SIGNER_LOGIN in signed[0]


def test_the_list_says_so_when_the_record_is_empty(
    ledgered: tuple[model.Site, dict[str, str]],
) -> None:
    site, _pages = ledgered
    assert activity.events_of({}, []) == []
    html = render.Renderer(site, repo_url=REPO).record_list([])
    assert "Nothing is on the record yet." in html


def test_the_list_holds_at_most_eight_rows(tmp_path: Path) -> None:
    root = fixture.build(tmp_path)
    write_ledger(
        root,
        "bob",
        [entry("proof", "and-reassoc", f"2026-09-{day:02d}T12:00:00Z") for day in range(1, 20)],
    )
    pages = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)
    assert len(rows(pages["index.html"])) == activity.SHOWN


# -- one problem, drawn ----------------------------------------------------------------------------


def test_the_featured_problem_is_drawn_and_linked(
    ledgered: tuple[model.Site, dict[str, str]],
) -> None:
    _site, pages = ledgered
    home = pages["index.html"]
    worked = home[home.index('id="worked"') :]
    assert '<svg class="dag"' in worked
    assert f'href="/problems/{TARGET}/"' in worked


def test_a_missing_featured_problem_leaves_the_section_out(tmp_path: Path) -> None:
    root = fixture.build(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    home = render.render_site(site, repo_url=REPO, featured_target="no-such-target")["index.html"]
    assert 'id="worked"' not in home
    assert 'href="#worked"' not in home  # the hero's second button goes with it


def test_the_featured_problem_is_configuration() -> None:
    assert config.load({}).featured_target == config.DEFAULT_FEATURED_TARGET == "erdos-1094"
    assert config.load({"OPN_SITE_FEATURED_TARGET": "erdos-257"}).featured_target == "erdos-257"
    assert config.load({"OPN_SITE_FEATURED_TARGET": " "}).featured_target is None


# -- the three doors ----------------------------------------------------------------------------


def test_three_doors(ledgered: tuple[model.Site, dict[str, str]]) -> None:
    _site, pages = ledgered
    home = pages["index.html"]
    doors = re.findall(r'<span class="kicker">([^<]+)</span><h3>', home)
    assert doors == ["Mathematicians", "Readers of Lean", "Bringing an agent"], doors
    assert "hosted precheck" in home
