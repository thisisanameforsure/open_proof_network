"""F04-T20: the site's sentences say what the record says, and point where the work is (Q22).

An outside contributor's list, 2026-09-18, each a sentence the page could not back:

* "The network's own statement, no external source" on three targets whose record names
  ``formal-conjectures`` as the statement's source (the page read only the plural ``sources``);
* "Every problem has a named steward" above "0 stewards", and an *open* badge whose definition
  promised a steward on problems that have none;
* "Open problem →" as a link label on a problem with no open statement, and "This problem is open
  for work" on one whose every statement waits on another;
* an invitation to write "an account of this proof" on a statement with no proof;
* "run the checks locally, and you have a token": the token comes from the hosted precheck;
* "No sign-off (DCO) text is committed … yet" while the service refuses a token without it;
* a partial proof listed under "proof" on Contributors;
* nothing on the problem or statement page leading to the contributor guide, and no way to see
  pull requests in flight.
"""

from __future__ import annotations

import dataclasses

import fixture
import pytest
from harness import TARGET

from opn_site import model, render

REPO = "https://github.com/example/graph"
API = "https://api.example.org"
ROOT = "and-swap-reassoc"


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[model.Site, dict[str, str]]:
    root = fixture.build_with_revised_hole(tmp_path_factory.mktemp("copy"))
    site = model.load_site(root, fixture.COMMIT)
    return site, render.render_site(site, repo_url=REPO, api_url=API)


@pytest.fixture(scope="module")
def listed(tmp_path_factory: pytest.TempPathFactory) -> model.Site:
    root = fixture.build_with_listed_target(tmp_path_factory.mktemp("listed"))
    return model.load_site(root, fixture.COMMIT)


def with_record(tv: model.TargetView, **fields: object) -> model.TargetView:
    assert tv.record is not None
    return dataclasses.replace(tv, record={**tv.record, **fields})


# -- where the statement comes from --------------------------------------------------------------


def test_a_registry_statement_with_no_sources_list_is_not_called_the_networks_own(
    listed: model.Site,
) -> None:
    tv = with_record(
        listed.targets[fixture.LISTED_TARGET],
        sources=[],
        source={
            "kind": "formal-conjectures",
            "ref": "FormalConjectures/ErdosProblems/69.lean",
            "url": None,
        },
        provenance={"statement_source": "formal-conjectures", "author": "The Authors"},
    )
    r = render.Renderer(listed, repo_url=REPO)
    for words in (r.source_line(tv), r.sources_block(tv)):
        assert "network's own" not in words and "network&#x27;s own" not in words
        assert "formal-conjectures" in words and "FormalConjectures/ErdosProblems/69.lean" in words


def test_only_a_network_statement_is_called_the_networks_own(listed: model.Site) -> None:
    tv = with_record(
        listed.targets[fixture.LISTED_TARGET],
        sources=[],
        source=None,
        provenance={"statement_source": "network", "author": "curator"},
    )
    r = render.Renderer(listed, repo_url=REPO)
    assert "The network's own statement" in r.source_line(tv)


# -- stewards and status words -------------------------------------------------------------------


def test_home_does_not_promise_a_steward_on_every_problem(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    _site, pages = built
    assert "Every problem has a named" not in pages["index.html"]


def test_the_open_badge_promises_no_steward() -> None:
    assert "steward" not in render.PROBLEM_STATUS_DEFS["open"]


def test_the_card_link_is_a_verb_not_a_status(built: tuple[model.Site, dict[str, str]]) -> None:
    _site, pages = built
    assert "Open problem →" not in pages["problems/index.html"]
    assert "View problem →" in pages["problems/index.html"]


def test_open_for_work_is_said_only_when_a_statement_is_workable(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    site, _pages = built
    r = render.Renderer(site, repo_url=REPO)
    tv = site.targets[TARGET]
    assert "This problem is open for work." in r.target_claimable(tv)
    none_open = dataclasses.replace(
        tv,
        nodes={
            nid: dataclasses.replace(nv, graph_entry={**nv.graph_entry, "status": "stale"})
            for nid, nv in tv.nodes.items()
        },
    )
    words = r.target_claimable(none_open)
    assert "open for work" not in words and "no statement" in words


# -- the statement page --------------------------------------------------------------------------


def test_an_unproved_statement_is_not_invited_to_explain_a_proof(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    _site, pages = built
    page = pages[f"nodes/{TARGET}/{fixture.HOLE}/index.html"]
    assert "No explainer yet." in page
    assert "account of this proof" not in page and "until this statement is proved" in page
    proved = pages[f"nodes/{TARGET}/and-reassoc/index.html"]
    assert "account of this proof" in proved and "by pull request" in proved


def test_the_statement_page_leads_to_the_guide_and_the_pull_requests_in_flight(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    _site, pages = built
    page = pages[f"nodes/{TARGET}/{ROOT}/index.html"]
    assert 'href="/docs/#agents"' in page
    assert f'href="{API}/submissions.json"' in page


def test_without_a_service_url_no_service_link_is_drawn(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    site, _pages = built
    pages = render.render_site(site, repo_url=REPO)  # no api_url: C7, nothing knows a hostname
    assert "submissions.json" not in pages[f"nodes/{TARGET}/{ROOT}/index.html"]
    assert "dco.json" not in pages["docs/index.html"]


def test_the_problem_page_leads_to_the_guide(built: tuple[model.Site, dict[str, str]]) -> None:
    _site, pages = built
    assert 'href="/docs/#agents"' in pages[f"problems/{TARGET}/index.html"]


# -- Home, Docs, Contributors ---------------------------------------------------------------------


def test_home_says_where_a_token_comes_from(built: tuple[model.Site, dict[str, str]]) -> None:
    _site, pages = built
    assert "run the checks locally, and you have a token" not in pages["index.html"]
    assert "hosted precheck" in pages["index.html"]


def test_docs_say_what_the_sign_off_is_and_where_it_is_served(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    _site, pages = built
    docs = pages["docs/index.html"]
    assert "No sign-off (DCO) text is committed" not in docs
    assert f'href="{API}/dco.json"' in docs and "Developer Certificate of Origin" in docs
    assert "CC-BY-4.0" in docs  # annex prose carries its author's licence


def test_docs_open_with_jump_links(built: tuple[model.Site, dict[str, str]]) -> None:
    _site, pages = built
    head = pages["docs/index.html"].split('<h2 id="stewards">', 1)[0]
    for anchor in ("#agents", "#glossary", "#stewards"):
        assert f'href="{anchor}"' in head, anchor


def test_a_partial_is_not_listed_as_a_proof(built: tuple[model.Site, dict[str, str]]) -> None:
    site, _pages = built
    r = render.Renderer(site, repo_url=REPO)
    entry = {
        "line": "proof",
        "target": TARGET,
        "node": ROOT,
        "artifact": "attempts/20260917T000000Z-agent-partial.lean",
        "date": "2026-09-17",
    }
    assert "<td>partial proof</td>" in r._ledger_row(entry)
    assert "<td>proof</td>" in r._ledger_row({**entry, "artifact": "Proof.lean"})


def test_the_footer_names_the_products_commit_when_it_differs(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    site, pages = built
    assert "products rendered at" not in pages["index.html"]  # the fixture's agree
    behind = dataclasses.replace(site, frontier={**site.frontier, "rendered_from": "7" * 40})
    page = render.Renderer(behind, repo_url=REPO).home()
    assert "products rendered at" in page and "777777777777" in page
