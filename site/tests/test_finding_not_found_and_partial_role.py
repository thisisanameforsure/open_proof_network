"""Testers 2026-10-27 (erdos-849), findings B-F3 and D-F-D4.

B-F3: ``/problems/erdos-849/variant-3969f1f7--h2--h1/`` answered 404 with the *home page* as its
body, because the distribution's one custom error response served ``/index.html`` for every
missing key. A reader guesses that URL, because the guide and the MCP name a statement by its id
and its panel lives on the problem page at ``#node=<id>``. The site now writes a real not-found
page, the distribution serves it, and every statement has a page at the guessed path that sends
the reader to its panel.

D-F-D4: the panel of a ``partial`` variant opened "A partial route to the problem." A partial
relation is a weaker version of the problem (the problem implies the variant), partial progress
and never a proof of it; a *route* is a decomposition. The role now says what the drawing key
says.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import fixture
import pytest
from test_finding_cache_headers import distribution

from opn_site import model, render

REPO = "https://github.com/example/graph"
TARGET = "propositional"


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[model.Site, dict[str, str]]:
    root = fixture.build(tmp_path_factory.mktemp("notfound"))
    site = model.load_site(root, fixture.COMMIT)
    return site, render.render_site(site, repo_url=REPO)


# -- B-F3: the not-found page ---------------------------------------------------------------------


def test_the_site_writes_a_not_found_page_that_is_not_the_home_page(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    _site, files = built
    page = files.get("404.html")
    assert page is not None, "no 404.html in the rendered site"
    assert page != files["index.html"]
    assert "Lately on the record" not in page
    assert "not found" in page.lower()
    assert 'href="/"' in page and 'href="/problems/"' in page


def test_the_distribution_serves_the_not_found_page_for_a_missing_key() -> None:
    responses = distribution()["CustomErrorResponses"]
    # The bucket is private behind origin access control, so a missing key is S3's 403.
    (missing,) = [r for r in responses if r["ErrorCode"] == 403]
    assert missing["ResponseCode"] == 404
    assert missing["ResponsePagePath"] == "/404.html"
    assert all(r.get("ResponsePagePath") != "/index.html" for r in responses)


def test_a_statement_at_the_guessed_problem_path_lands_on_its_panel(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    site, files = built
    nodes = site.targets[TARGET].nodes
    assert nodes
    for nid in nodes:
        page = files.get(f"problems/{TARGET}/{nid}/index.html")
        assert page is not None, nid
        to = f"/problems/{TARGET}/#node={nid}"
        assert f'<meta http-equiv="refresh" content="0; url={render.esc(to)}">' in page, nid
        assert f'href="{render.esc(to)}"' in page, nid


def test_a_guessed_path_never_replaces_a_problem_page_of_its_own(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    _site, files = built
    # The problem page and its other children keep their own content.
    assert (
        "#node="
        not in files[f"problems/{TARGET}/index.html"].split("<head>")[1].split("</head>")[0]
    )
    for rel, html in files.items():
        if (
            rel.startswith(f"problems/{TARGET}/proofs/")
            or rel == f"problems/{TARGET}/review/index.html"
        ):
            assert 'http-equiv="refresh"' not in html, rel


# -- D-F-D4: a partial variant's role ------------------------------------------------------------


def partial_variant_panel(site: model.Site) -> str:
    r = render.Renderer(site, repo_url=REPO)
    tv = site.targets[TARGET]
    nid = next(n for n in tv.nodes if n != tv.root)
    nv = tv.nodes[nid]
    entry = {**nv.graph_entry, "origin": "variant", "relation": "partial"}
    nv = dataclasses.replace(nv, graph_entry=entry)
    return r.panel_role(tv, nv)


def test_a_partial_variant_is_called_a_weaker_version_never_a_route(
    built: tuple[model.Site, dict[str, str]],
) -> None:
    site, _files = built
    role = partial_variant_panel(site)
    assert "route" not in role, role
    assert "A weaker version of the problem: partial progress, never a proof of it." in role
    assert render.RELATION_ROLES["partial"].startswith(
        render.GLOSSARY_BY_KEY["relation-partial"][0]
    ), "the panel's words are the drawing key's"


def test_no_relation_role_calls_a_variant_a_route() -> None:
    for relation, words in render.RELATION_ROLES.items():
        assert "route" not in words, relation


def test_the_sentence_has_one_home() -> None:
    src = Path(render.__file__).read_text(encoding="utf-8")
    assert "a partial route to the problem" not in src
