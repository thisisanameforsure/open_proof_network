"""F06-T20 (bug B8, agent run 2026-11-19): ``products-pending`` says its wait in the body, and a
merged partial waits on ``products`` until its new holes are in the products.

Three agents polled blindly: a ``409 products-pending`` carried ``Retry-After: 240`` as a header
only, and an agent that reads the JSON body (every MCP client, and most HTTP ones) never saw it.
Every ``products-pending`` refusal now carries ``details.retry_after_s``, the header's number, and
``details.graph_commit``, the commit the service's products were read at (``ctx.head``), unless
the refusal already names the commit it was judged against (F06-T14, F06-T18 keep theirs).

Agent 9: ``GET /submissions/<id>`` said ``waiting_on: null`` for a merged partial whose holes
were still not claimable (``POST /claims`` on them answered ``products-pending``). A merged
partial attested by the post-merge job had nothing left in ``waiting_on_products`` to wait for;
it now waits on ``products`` while any node its record expects (``Submission.expected_nodes``,
the holes the precheck said would be new) is missing from the products the service reads.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from api_fakes import TUTORIAL_NODE, Harness, PrecheckKey, make_precheck_key
from test_finding_hole_child_pending import CHILD, EXISTING, claim, submitted_partial
from test_pending_submissions import MERGE_SHA, record, seed_attestation

from opn_api import pending


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


def assert_body_says_the_wait(r: Any) -> dict[str, Any]:
    assert (r.status_code, r.json()["error"]) == (409, "products-pending"), r.text
    details: dict[str, Any] = r.json()["details"]
    assert details["retry_after_s"] == int(r.headers["Retry-After"])
    assert "graph_commit" in details
    return details


def test_a_hole_child_refusal_carries_the_wait_in_its_body(
    harness: Harness, key: PrecheckKey
) -> None:
    harness.githost.head = "a" * 40  # main's head, as the API answers it (F05-T13)
    receipt = submitted_partial(harness, key)
    harness.githost.set_pull_request_state(receipt["pr_number"], state="closed", merged=True)
    details = assert_body_says_the_wait(claim(harness, CHILD))
    assert details["graph_commit"] == harness.context.head == "a" * 40  # where products were read


def test_with_no_head_ever_read_the_commit_is_null_not_invented(
    harness: Harness, key: PrecheckKey
) -> None:
    receipt = submitted_partial(harness, key)  # the fake's API names no head
    harness.githost.set_pull_request_state(receipt["pr_number"], state="closed", merged=True)
    assert assert_body_says_the_wait(claim(harness, CHILD))["graph_commit"] is None


def test_a_merged_witness_refusal_carries_the_wait_in_its_body(harness: Harness) -> None:
    """``precheck.awaits_render`` (F06-T8): the node still reads ``witness-missing`` while
    ``main`` has the filled slot."""
    from test_finding_waiting_on_products_appends import (  # noqa: PLC0415
        HOLE,
        HOLE_WITNESS,
        seed_hole,
    )

    seed_hole(harness, cause="witness-missing")
    harness.githost.files[HOLE_WITNESS] = b"theorem OpnFixture.w : True := trivial\n"
    harness.context.files.clear()
    details = assert_body_says_the_wait(claim(harness, HOLE))
    assert details["node_id"] == HOLE
    # the service does not know when this witness merged (it reads the tree): the flat wait
    assert details["retry_after_s"] == pending.PRODUCTS_RETRY_FLAT_S == 300


# --- the wait itself (B2's measurement, engineering/evidence/F07/task-87.txt) ---------------------


@pytest.mark.parametrize(
    ("minutes_ago", "expected"),
    [
        (2, 600),  # 840 - 120 = 720, capped at 600
        (8, 360),  # 840 - 480
        (13, 60),  # 840 - 780 = 60
        (20, 60),  # past the median: the floor
    ],
)
def test_a_known_merge_time_sets_the_wait(
    harness: Harness, key: PrecheckKey, minutes_ago: int, expected: int
) -> None:
    receipt = submitted_partial(harness, key)
    merged_at = (harness.clock.now() - timedelta(minutes=minutes_ago)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    harness.githost.set_pull_request_state(
        receipt["pr_number"], state="closed", merged=True, merged_at=merged_at
    )
    details = assert_body_says_the_wait(claim(harness, CHILD))
    assert details["retry_after_s"] == expected


def test_an_unknown_merge_time_is_the_flat_wait(harness: Harness) -> None:
    assert pending.products_retry_after_s(harness.context, None) == 300
    assert pending.products_retry_after_s(harness.context, "not a time") == 300


# --- waiting_on for a merged partial ------------------------------------------------------------


def merged_partial(h: Harness, number: int, expected: tuple[str, ...]) -> None:
    h.store.put_submission(
        record(number, kind="partial", node_id=TUTORIAL_NODE, expected_nodes=expected)
    )
    h.githost.set_pull_request_state(
        number, state="closed", merged=True, merge_commit_sha=MERGE_SHA
    )
    seed_attestation(h, number)  # the post-merge job has attested it


def waiting_on(h: Harness, number: int) -> Any:
    r = h.client.get(f"/submissions/{number}")
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["state"] == "merged" and doc["attestation"] is not None, doc
    return doc["pull_request"]["waiting_on"]


def test_a_merged_partial_waits_on_products_until_its_holes_are_rendered(
    harness: Harness,
) -> None:
    merged_partial(harness, 41, (CHILD,))  # the fixture's products have no such node
    assert waiting_on(harness, 41) == "products"


def test_a_merged_partial_whose_holes_are_rendered_waits_on_nothing(harness: Harness) -> None:
    merged_partial(harness, 43, (EXISTING,))  # a node the fixture's products carry
    assert waiting_on(harness, 43) is None


def test_a_merged_partial_with_no_new_holes_waits_on_nothing(harness: Harness) -> None:
    merged_partial(harness, 45, ())
    assert waiting_on(harness, 45) is None
