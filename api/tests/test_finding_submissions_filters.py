"""F22-T8 (testers 2026-10-06, feature request E, service half): words in review, for the page.

A node page is to show "In review: #N by X" under each subject, fetched live from the service
(F22-T19). So ``GET /submissions.json`` takes ``target``, ``node`` and ``kind`` filters — equality
only, ``kind=words`` meaning a gloss or an explainer — and names a filter it does not know; and
that one route answers with ``Access-Control-Allow-Origin`` for the site's origin, read from
config (``OPN_API_SITE_ORIGIN``, by default the public URL without its ``api.`` label): no
hostname is written in code (log 2026-09-09).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from api_fakes import Harness, make_harness
from mcp_client import McpClient
from test_glosses_route import make_h, make_keys, make_tree, post, statement_gloss

from opn_api import config

NODE = "and-reassoc"
OTHER = "tutorial-and-swap"


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory)


@pytest.fixture
def tree(tmp_path: Path, keys: dict[str, Path]) -> Path:
    return make_tree(tmp_path, keys)


@pytest.fixture
def h(tree: Path) -> Iterator[Harness]:
    yield from make_h(tree)


def opened(h: Harness) -> dict[str, int]:
    """A gloss on NODE, an annex on NODE and a gloss on OTHER, by what they are."""
    bob = h.token_for("code_bob", "bob")
    out: dict[str, int] = {}
    r = post(h, bob, statement_gloss())
    assert r.status_code == 201, r.text
    out["gloss"] = r.json()["pr_number"]
    r = h.client.post(
        "/annexes",
        json={"node_id": NODE, "text": "Symmetry.\n", "licence": "CC-BY-4.0"},
        headers=h.auth(bob),
    )
    assert r.status_code == 201, r.text
    out["annex"] = r.json()["pr_number"]
    other = statement_gloss()
    other["subject"] = {"kind": "statement", "node_id": OTHER}
    r = post(h, bob, other)
    assert r.status_code == 201, r.text
    out["other"] = r.json()["pr_number"]
    return out


def numbers(h: Harness, query: str) -> list[int]:
    r = h.client.get("/submissions.json" + query)
    assert r.status_code == 200, r.text
    return sorted(e["pr_number"] for e in r.json()["open"])


def test_the_filters_keep_what_they_name(h: Harness) -> None:
    prs = opened(h)
    assert numbers(h, "") == sorted(prs.values())
    assert numbers(h, f"?node={NODE}") == sorted([prs["gloss"], prs["annex"]])
    assert numbers(h, f"?node={NODE}&kind=words") == [prs["gloss"]]
    assert numbers(h, "?kind=words") == sorted([prs["gloss"], prs["other"]])
    assert numbers(h, "?kind=annex") == [prs["annex"]]
    assert numbers(h, "?target=propositional") == sorted(prs.values())
    assert numbers(h, "?target=elsewhere") == []


def test_a_filter_it_does_not_know_is_named(h: Harness) -> None:
    r = h.client.get("/submissions.json?author=bob")
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "filter-unknown"
    r = h.client.get("/submissions.json?node=Not_An_Id")
    assert r.status_code == 400 and r.json()["error"] == "node-id-invalid", r.text
    r = h.client.get("/submissions.json?target=..")
    assert r.status_code == 400 and r.json()["error"] == "target-id-invalid", r.text


def test_the_tool_takes_the_filters(h: Harness) -> None:
    prs = opened(h)
    out = McpClient(h).ok("list_submissions", {"node_id": NODE, "kind": "words"})
    assert [e["pr_number"] for e in out["open"]] == [prs["gloss"]]


# --- CORS, for the site's origin only -------------------------------------------------------------


def harness_with(env: dict[str, str]) -> Iterator[Harness]:
    h = make_harness(env)
    with h.client:
        yield h


def test_the_site_origin_is_the_public_url_without_its_api_label() -> None:
    assert config.load({"OPN_API_PUBLIC_URL": "https://api.example.org"}).site_origin == (
        "https://example.org"
    )
    assert config.load({}).site_origin is None  # the local runner: no site to answer
    named = {"OPN_API_PUBLIC_URL": "https://api.example.org", "OPN_API_SITE_ORIGIN": "https://x.y"}
    assert config.load(named).site_origin == "https://x.y"


def test_the_listing_answers_the_site_origin_and_nothing_else_does() -> None:
    for h in harness_with({"OPN_API_PUBLIC_URL": "https://api.example.org"}):
        r = h.client.get("/submissions.json", headers={"Origin": "https://example.org"})
        assert r.status_code == 200, r.text
        assert r.headers["access-control-allow-origin"] == "https://example.org"
        assert "Origin" in r.headers.get("vary", "")
        for path in ("/frontier.json", "/info.json", "/health"):
            assert "access-control-allow-origin" not in h.client.get(path).headers, path


def test_with_no_site_origin_no_header_is_sent() -> None:
    for h in harness_with({}):
        r = h.client.get("/submissions.json")
        assert r.status_code == 200
        assert "access-control-allow-origin" not in r.headers
