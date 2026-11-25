"""mcpfix WB2 item 2 (testers 2026-11-25, t257b item 5, t883 item 10, t257 item 153): what merged
and is not in the products yet.

After a merge the products lag the post-merge render (a median of about fourteen minutes), so
``GET /frontier.json`` still listed a node whose proof had merged as ``claimable: true``, and
``list_words_needed`` still listed a subject whose gloss had merged. The service knows which of its
pull requests merged (``pending.recent_merges``: every live read that closes a record as merged
notes it in the store), and whether the target's products carry that merge (the merge commit is
the commit the target's ``graph.json`` was rendered from, or an ancestor of it).

``frontier/v8`` is hash-pinned and closed (D-34), so the overlay sets the entry's own
``claimable`` to false and puts what it waits on in a top-level ``pending_render`` map, keyed by
node id, added after the document is validated: ``{pr, kind, merged_at}``; with nothing waiting
the key is absent and the served document validates as frontier/v8 (F05-AC15). The words half is a
helper, ``frontier.pending_words(ctx, target_id)``, the subject keys whose gloss or explainer has
merged and is not rendered, for the MCP adapter's ``list_words_needed`` to drop.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from api_fakes import TUTORIAL_NODE, Harness
from test_pending_submissions import proof_record
from test_store_seam import dynamo

from opn_api import clock as clockmod
from opn_api import duplicates, frontier
from opn_api.store import MemoryStore, Store, Submission

TARGET = "propositional"
RENDERED = "5" * 40  # the fixture's rendered_from
MERGE = "9" * 40


def frontier_doc(h: Harness) -> dict[str, Any]:
    r = h.client.get("/frontier.json")
    assert r.status_code == 200, r.text
    doc: dict[str, Any] = r.json()
    return doc


def entry(doc: dict[str, Any], node_id: str) -> dict[str, Any]:
    found: list[dict[str, Any]] = [e for e in doc["entries"] if e["node_id"] == node_id]
    assert len(found) == 1, found
    return found[0]


def merged_through_the_route(h: Harness, *, rendered: bool) -> str:
    """A proof the service opened merges; a reader of ``GET /submissions/7`` closes its record."""
    proof_record(h)
    merged_at = clockmod.render(h.clock.now() - timedelta(minutes=3))
    h.githost.set_pull_request_state(
        7, state="closed", merged=True, merge_commit_sha=MERGE, merged_at=merged_at
    )
    h.githost.ancestry[(MERGE, RENDERED)] = rendered
    assert h.client.get("/submissions/7").status_code == 200
    return merged_at


def test_a_merged_proof_not_yet_rendered_is_not_claimable(harness: Harness) -> None:
    assert entry(frontier_doc(harness), TUTORIAL_NODE)["claimable"] is True
    merged_at = merged_through_the_route(harness, rendered=False)
    doc = frontier_doc(harness)
    assert entry(doc, TUTORIAL_NODE)["claimable"] is False
    assert doc["pending_render"] == {
        TUTORIAL_NODE: {"pr": 7, "kind": "proof", "merged_at": merged_at}
    }
    assert entry(doc, "and-reassoc")["claimable"] is True  # the other entries are untouched


def test_a_merge_the_products_carry_overlays_nothing(harness: Harness) -> None:
    merged_through_the_route(harness, rendered=True)
    doc = frontier_doc(harness)
    assert entry(doc, TUTORIAL_NODE)["claimable"] is True
    assert "pending_render" not in doc  # nothing waits: the frontier as committed (F05-AC15)


def test_a_host_that_cannot_say_overlays_nothing(harness: Harness) -> None:
    """C7: no answer about the products is no claim that they lag."""
    merged_through_the_route(harness, rendered=False)
    harness.githost.ancestry.clear()  # the fake's host failure
    harness.context.render_ancestry.clear()
    doc = frontier_doc(harness)
    assert entry(doc, TUTORIAL_NODE)["claimable"] is True
    assert "pending_render" not in doc  # nothing waits: the frontier as committed (F05-AC15)


def gloss_record(h: Harness, number: int, subject: str) -> str:
    key = duplicates.words_key(TARGET, subject)
    merged_at = clockmod.render(h.clock.now() - timedelta(minutes=2))
    h.store.put_submission(
        Submission(
            id=f"01M{number:023d}",
            kind="gloss",
            node_id=TUTORIAL_NODE,
            target_id=TARGET,
            pr_number=number,
            pr_url=f"https://github.com/pr/{number}",
            pseudonym="bob",
            precheck_job_id=None,
            created=merged_at,
            closed=merged_at,
            final_state={"merged": True, "merge_commit_sha": MERGE},
            fingerprints=("deadbeef", key),
        )
    )
    h.store.note_merged(number, h.clock.now() + timedelta(hours=1))
    return key


def test_pending_words_names_a_merged_gloss_until_it_is_rendered(harness: Harness) -> None:
    key = gloss_record(harness, 12, f"nodes/{TUTORIAL_NODE}/Statement.lean")
    harness.githost.ancestry[(MERGE, RENDERED)] = False
    assert frontier.pending_words(harness.context, TARGET) == {key}
    assert frontier.pending_words(harness.context, "elsewhere") == set()
    harness.context.render_ancestry.clear()
    harness.githost.ancestry[(MERGE, RENDERED)] = True
    assert frontier.pending_words(harness.context, TARGET) == set()


@pytest.fixture(params=["memory", "dynamodb"])
def both(request: pytest.FixtureRequest) -> Store:
    return MemoryStore() if request.param == "memory" else dynamo()


def test_recent_merges_expire_and_prune_in_both_stores(both: Store) -> None:
    now = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)
    both.note_merged(3, now + timedelta(minutes=5))
    both.note_merged(1, now + timedelta(hours=1))
    assert both.recently_merged(now) == [1, 3]
    later = now + timedelta(minutes=10)
    assert both.recently_merged(later) == [1]
    assert both.recently_merged(later) == [1]  # pruned, not resurrected
    assert both.recently_merged(now + timedelta(hours=2)) == []


def test_a_rendered_merge_leaves_the_index(harness: Harness) -> None:
    """Once the products carry a merge, it leaves the index, so a busy hour of merges does not
    cost every frontier read one record read per merge."""
    merged_through_the_route(harness, rendered=True)
    assert harness.store.recently_merged(harness.clock.now()) == [7]
    frontier_doc(harness)
    assert harness.store.recently_merged(harness.clock.now()) == []


def test_forget_merged_in_both_stores(both: Store) -> None:
    now = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)
    both.note_merged(3, now + timedelta(minutes=5))
    both.note_merged(4, now + timedelta(minutes=5))
    both.forget_merged(3)
    both.forget_merged(99)  # absent: nothing happens
    assert both.recently_merged(now) == [4]
