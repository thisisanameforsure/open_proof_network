"""F05-T15 (testers 2026-09-24): ``waiting_on: products`` for a merged annex or witness too.

The story. The erdos-1050 MCP agent (``engineering/evidence/testers-2026-09-24/erdos-1050-mcp.md``,
line 22) submitted an annex at 12:31:08Z (graph #174), saw it merged by 12:33:04Z, and read
``get_submission 174``: ``pull_request.waiting_on`` was ``null``. Ten seconds later its
``precheck_submission`` of a skeleton citing that annex answered ``409 products-pending``,
``retry_after 240``. The guide says a merged submission reads ``products`` until the post-merge job
has rendered; the record said there was nothing left to wait for, and the precheck said there was.

The mechanism. ``pending.waiting_on_products`` (F05-T13) covered ``PROPOSAL_KINDS`` alone: a
proposal waits until its node is in the products. An annex is not a node, so nothing asked
whether the products had caught up with it, while ``precheck.check_cited_annex`` refuses a
skeleton citing it until the commit the products were rendered from carries the file. A merged
witness is the same shape: until the job re-renders, its node still reads ``witness-missing`` and
precheck answers ``products-pending`` (``precheck.witness_awaits_render``).

The rule. A merged annex waits on ``products`` while the commit its target's products were
rendered from lacks an annex that the merge commit carries on the node; a merged witness waits
while its node still reads ``witness-missing`` and ``main`` has the filled slot, the same test
precheck applies. A merged postmortem waits on nothing, since nothing is checked against it. A
graph or host that cannot be read changes nothing (C7): ``null``, as before.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from api_fakes import TUTORIAL_NODE, Harness
from test_pending_submissions import record

TARGET = "propositional"
RENDERED = "5" * 40  # the fixture graph.json's rendered_from
MERGE = "9" * 40
NODE_DIR = f"targets/{TARGET}/nodes/{TUTORIAL_NODE}/"
ANNEX = NODE_DIR + "annex/" + "e6849740" * 8 + ".md"
HOLE = "and-reassoc--h1"
HOLE_WITNESS = f"targets/{TARGET}/nodes/{HOLE}/Witness.lean"


def waiting_on(h: Harness, number: int) -> Any:
    r = h.client.get(f"/submissions/{number}")
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["pull_request"]["merged"] is True, doc
    return doc["pull_request"]["waiting_on"]


def merged_annex(h: Harness, number: int = 174) -> None:
    """#174's shape: an annex on the node, merged; ``main`` carries the file, the commit the
    products were rendered from does not."""
    h.store.put_submission(record(number, kind="annex", node_id=TUTORIAL_NODE))
    h.githost.set_pull_request_state(number, state="closed", merged=True, merge_commit_sha=MERGE)
    h.githost.files[ANNEX] = b"---\nschema: annex/v1\n---\nAn argument.\n"
    h.githost.absent_at[RENDERED] = {ANNEX}


def test_a_merged_annex_not_yet_rendered_waits_on_products(harness: Harness) -> None:
    merged_annex(harness)
    assert waiting_on(harness, 174) == "products"


def test_it_clears_once_rendered(harness: Harness) -> None:
    merged_annex(harness)
    assert waiting_on(harness, 174) == "products"
    del harness.githost.absent_at[RENDERED]  # the post-merge job rendered past the merge
    assert waiting_on(harness, 174) is None


def test_an_annex_rendered_before_anyone_asked_never_waits(harness: Harness) -> None:
    merged_annex(harness)
    harness.githost.absent_at.clear()
    assert waiting_on(harness, 174) is None


def seed_hole(h: Harness, *, cause: str | None) -> None:
    path = f"targets/{TARGET}/graph.json"
    doc = json.loads(h.githost.files[path])
    hole = {**doc["nodes"][0], "node_id": HOLE, "origin": "skeleton-hole"}
    doc["nodes"] = [n for n in doc["nodes"] if n["node_id"] != HOLE]
    doc["nodes"].append({**hole, "status": "blocked" if cause else "ready", "cause": cause})
    h.githost.files[path] = json.dumps(doc).encode()
    h.context.files.clear()


def test_a_merged_witness_waits_until_the_node_is_no_longer_witness_missing(
    harness: Harness,
) -> None:
    seed_hole(harness, cause="witness-missing")
    harness.githost.files[HOLE_WITNESS] = b"theorem witness : True := trivial\n"
    harness.store.put_submission(record(2, kind="witness", node_id=HOLE))
    harness.githost.set_pull_request_state(2, state="closed", merged=True, merge_commit_sha=MERGE)
    assert waiting_on(harness, 2) == "products"

    seed_hole(harness, cause=None)  # rendered: the node is no longer witness-missing
    assert waiting_on(harness, 2) is None


def test_a_merged_postmortem_never_waits(harness: Harness) -> None:
    """Nothing is checked against a postmortem, so there is nothing to wait for, and no host
    call is spent asking."""
    harness.store.put_submission(record(2, kind="postmortem", node_id=TUTORIAL_NODE))
    harness.githost.set_pull_request_state(2, state="closed", merged=True, merge_commit_sha=MERGE)
    harness.githost.absent_at[RENDERED] = {ANNEX}
    harness.githost.files[ANNEX] = b"an annex nobody is asking about\n"
    assert waiting_on(harness, 2) is None
    assert not [p for p, _ in harness.githost.fetches if p.endswith("/annex/")]


@pytest.mark.parametrize("kind", ["annex", "witness"])
def test_a_graph_read_failure_leaves_null(harness: Harness, kind: str) -> None:
    """C7: the record still answers, merged, with nothing claimed about the products."""
    if kind == "annex":
        merged_annex(harness, 2)
    else:
        seed_hole(harness, cause="witness-missing")
        harness.githost.files[HOLE_WITNESS] = b"theorem witness : True := trivial\n"
        harness.store.put_submission(record(2, kind="witness", node_id=HOLE))
        harness.githost.set_pull_request_state(
            2, state="closed", merged=True, merge_commit_sha=MERGE
        )
    harness.context.files.clear()
    harness.githost.unreachable = True
    assert waiting_on(harness, 2) is None


def test_a_merged_proposal_still_waits_as_before(harness: Harness) -> None:
    """Guard: F05-T13's proposal rule is unchanged."""
    harness.store.put_submission(record(7, kind="variant", node_id="variant-0badc0de"))
    harness.githost.set_pull_request_state(7, state="closed", merged=True, merge_commit_sha=MERGE)
    assert waiting_on(harness, 7) == "products"
