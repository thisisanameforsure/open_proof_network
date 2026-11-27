"""F31-T16 (Q19): a filed shelving is followed from the page until it is drawn.

The owner retired a route on erdos-257 (graph #2078, 2026-11-27 20:43Z). The record merged in a
minute and the page did not change for a quarter of an hour, because the products land a median
of fourteen minutes after a merge; the page said "Retirement filed: #2078" until the next reload
and then nothing at all. The service knew the whole time what the page could not: that the
record had merged and that the target's products were not rendered from that merge.

So, for the site's page (``static/shelve.js``):

- ``GET /submissions/{id}`` says ``pull_request.waiting_on: "products"`` for a merged shelving the
  products do not carry yet (it said ``null``, the word for "finished"), and answers the site's
  origin, as ``GET /submissions.json`` does, so a page may read it without credentials;
- ``GET /submissions.json`` carries ``awaiting_render``: the merged records the products do not
  show yet, each as ``open`` gives a record, under the same filters. A viewer who did not file
  the record sees it is on its way for the whole wait, not only the minute it is open.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from typing import Any

from api_fakes import TUTORIAL_NODE, Harness, make_harness
from test_mcpfix_wb2_pending_render import MERGE, RENDERED, TARGET

from opn_api import clock as clockmod
from opn_api.mcp import results
from opn_api.store import Submission

NUMBER = 31
SITE = {"OPN_API_PUBLIC_URL": "https://api.example.org"}


def shelving_record(h: Harness, number: int = NUMBER, *, kind: str = "shelving") -> str:
    """A record the service opened, merged two minutes ago and noted as merged."""
    merged_at = clockmod.render(h.clock.now() - timedelta(minutes=2))
    h.store.put_submission(
        Submission(
            id=f"01M{number:023d}",
            kind=kind,
            node_id=TUTORIAL_NODE,
            target_id=TARGET,
            pr_number=number,
            pr_url=f"https://github.com/pr/{number}",
            pseudonym="mike",
            precheck_job_id=None,
            created=merged_at,
            closed=merged_at,
            final_state={
                "number": number,
                "state": "closed",
                "merged": True,
                "merge_commit_sha": MERGE,
                "waiting_on": None,
            },
            fingerprints=(),
        )
    )
    h.store.note_merged(number, h.clock.now() + timedelta(hours=1))
    return merged_at


def one(h: Harness, number: int = NUMBER) -> dict[str, Any]:
    r = h.client.get(f"/submissions/{number}")
    assert r.status_code == 200, r.text
    doc: dict[str, Any] = r.json()
    return doc


def listing(h: Harness, query: str = "") -> dict[str, Any]:
    r = h.client.get("/submissions.json" + query)
    assert r.status_code == 200, r.text
    doc: dict[str, Any] = r.json()
    return doc


# --- GET /submissions/{id} -------------------------------------------------------------------


def test_a_merged_shelving_not_yet_rendered_waits_on_the_products(harness: Harness) -> None:
    shelving_record(harness)
    harness.githost.ancestry[(MERGE, RENDERED)] = False
    doc = one(harness)
    assert doc["state"] == "merged"
    assert doc["pull_request"]["waiting_on"] == "products"


def test_a_merged_shelving_the_products_carry_waits_on_nothing(harness: Harness) -> None:
    shelving_record(harness)
    harness.githost.ancestry[(MERGE, RENDERED)] = True
    assert one(harness)["pull_request"]["waiting_on"] is None


def test_a_host_that_cannot_compare_claims_no_wait(harness: Harness) -> None:
    """C7: no answer about the products is no claim that they lag."""
    shelving_record(harness)
    assert one(harness)["pull_request"]["waiting_on"] is None


def test_a_merged_postmortem_still_waits_on_nothing(harness: Harness) -> None:
    """F05-T13's rule is unchanged for the kinds whose merge changes no drawing."""
    shelving_record(harness, kind="postmortem")
    harness.githost.ancestry[(MERGE, RENDERED)] = False
    assert one(harness)["pull_request"]["waiting_on"] is None


def with_site() -> Iterator[Harness]:
    h = make_harness(SITE)
    with h.client:
        yield h


def test_one_submission_answers_the_site_origin() -> None:
    for h in with_site():
        shelving_record(h)
        r = h.client.get(f"/submissions/{NUMBER}", headers={"Origin": "https://example.org"})
        assert r.status_code == 200, r.text
        assert r.headers["access-control-allow-origin"] == "https://example.org"
        assert "Origin" in r.headers.get("vary", "")
        assert "access-control-allow-credentials" not in r.headers  # a public read, no cookie


def test_with_no_site_origin_one_submission_sends_no_header(harness: Harness) -> None:
    shelving_record(harness)
    r = harness.client.get(f"/submissions/{NUMBER}")
    assert "access-control-allow-origin" not in r.headers


# --- GET /submissions.json -------------------------------------------------------------------


def test_the_listing_names_a_merged_record_awaiting_render(harness: Harness) -> None:
    merged_at = shelving_record(harness)
    harness.githost.ancestry[(MERGE, RENDERED)] = False
    doc = listing(harness)
    assert doc["open"] == []
    (entry,) = doc["awaiting_render"]
    assert entry["pr_number"] == NUMBER
    assert entry["kind"] == "shelving"
    assert entry["node_id"] == TUTORIAL_NODE
    assert entry["target_id"] == TARGET
    assert entry["pseudonym"] == "mike"
    assert entry["closed"] == merged_at
    assert entry["queue"] is None  # merged: it has no place in the queue
    assert results.violations("list_submissions", doc) == []  # the tool's own result schema
    assert "fingerprints" not in entry and "final_state" not in entry


def test_a_rendered_merge_is_not_listed(harness: Harness) -> None:
    shelving_record(harness)
    harness.githost.ancestry[(MERGE, RENDERED)] = True
    assert listing(harness)["awaiting_render"] == []


def test_with_nothing_merged_the_list_is_empty(harness: Harness) -> None:
    assert listing(harness)["awaiting_render"] == []


def test_the_filters_reach_the_merged_records_too(harness: Harness) -> None:
    shelving_record(harness)
    shelving_record(harness, 32, kind="gloss")
    harness.githost.ancestry[(MERGE, RENDERED)] = False
    assert [e["pr_number"] for e in listing(harness)["awaiting_render"]] == [31, 32]
    by_kind = listing(harness, f"?target={TARGET}&kind=shelving")["awaiting_render"]
    assert [e["pr_number"] for e in by_kind] == [NUMBER]
    assert listing(harness, "?node=and-reassoc")["awaiting_render"] == []
    assert [e["pr_number"] for e in listing(harness, "?kind=words")["awaiting_render"]] == [32]
