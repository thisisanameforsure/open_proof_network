"""F06-T8: a precheck that cannot pass yet is refused at once and says what it waits for
(testers 2026-09-21, finding 7).

A precheck job runs at the commit the products were rendered from (F06-Q10, Q12), not at
``main``. Two agents paid a whole hosted run for that, and each run blamed the contributor:

- erdos-69: a partial citing an annex whose pull request was still open was accepted (202) and
  failed ``annex-uncited`` two minutes later; after the annex merged, a second precheck was
  accepted, pinned to the render from before the merge, and failed the same way.
- erdos-1050: for three minutes after its witness merged, every precheck on the hole answered
  ``409 node-blocked ... a witness goes in through POST /proposals/witness``: already done.

Each test asserts the correct answer and was seen red first
(``engineering/evidence/F06/task-8.txt``).
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from api_fakes import Harness
from mcp_client import NODE, TARGET, seed_node
from test_finding_mcp_bootstrap import HOLE, WITNESS, add_hole

from opn_gate import schemas

NODE_DIR = f"targets/{TARGET}/nodes/{NODE}/"
GRAPH_PATH = f"targets/{TARGET}/graph.json"
PARTIAL_PATH = NODE_DIR + "attempts/20260921T064434Z-alice-partial.lean"
ANNEX_TEXT = "Split the sum at N, bound the tail, and the crux is arithmetic.\n"


def partial(digest: str) -> str:
    return (
        f"-- annex: {digest}\n"
        "theorem OpnProp.and_reassoc : True := by\n  have h : True := sorry\n  exact h\n"
    )


def rendered_from(h: Harness) -> str:
    commit: str = json.loads(h.githost.files[GRAPH_PATH])["rendered_from"]
    return commit


def precheck(h: Harness, token: str, node_id: str, bundle: dict[str, str]) -> httpx.Response:
    r: httpx.Response = h.client.post(
        "/precheck", json={"node_id": node_id, "bundle": bundle}, headers=h.auth(token)
    )
    return r


def no_job(h: Harness) -> None:
    assert h.githost.dispatches == [], "a hosted run was spent on a precheck that could not pass"
    assert h.store.jobs == {}


def refused(r: httpx.Response, status: int, code: str) -> dict[str, Any]:
    doc: dict[str, Any] = r.json()
    assert (r.status_code, doc.get("error")) == (status, code), r.text
    return doc


def test_an_annex_whose_pull_request_is_open_is_annex_pending(harness: Harness) -> None:
    seed_node(harness)
    token = harness.token_for("code_alice", "alice")
    posted = harness.client.post(
        "/annexes", json={"node_id": NODE, "text": ANNEX_TEXT}, headers=harness.auth(token)
    )
    assert posted.status_code == 201, posted.text
    digest, number = posted.json()["hash"], posted.json()["pr_number"]
    harness.githost.dispatches.clear()

    doc = refused(
        precheck(harness, token, NODE, {PARTIAL_PATH: partial(digest)}), 409, "annex-pending"
    )
    assert f"#{number}" in doc["message"] and doc["details"]["pr_number"] == number
    assert doc["details"]["annex"] == digest
    no_job(harness)


def test_an_annex_merged_but_not_rendered_is_products_pending(harness: Harness) -> None:
    """On ``main``, and absent at the commit the job would be pinned to."""
    seed_node(harness)
    token = harness.token_for("code_alice", "alice")
    content = b"---\nschema: annex/v1\n---\n" + ANNEX_TEXT.encode()
    digest = schemas.content_hash(content)
    path = f"{NODE_DIR}annex/{digest}.md"
    harness.githost.files[path] = content
    harness.githost.absent_at[rendered_from(harness)] = {path}

    r = precheck(harness, token, NODE, {PARTIAL_PATH: partial(digest)})
    doc = refused(r, 409, "products-pending")
    assert int(r.headers["Retry-After"]) > 0 and doc["details"]["annex"] == digest
    no_job(harness)


def test_an_annex_nobody_submitted_is_annex_unknown(harness: Harness) -> None:
    seed_node(harness)
    token = harness.token_for("code_alice", "alice")
    doc = refused(
        precheck(harness, token, NODE, {PARTIAL_PATH: partial("a" * 64)}), 400, "annex-unknown"
    )
    assert "POST /annexes" in doc["message"]
    no_job(harness)


def test_a_cited_annex_that_is_rendered_is_prechecked(harness: Harness) -> None:
    """The guard: the happy path still costs exactly one job."""
    seed_node(harness)
    token = harness.token_for("code_alice", "alice")
    content = b"---\nschema: annex/v1\n---\n" + ANNEX_TEXT.encode()
    digest = schemas.content_hash(content)
    harness.githost.files[f"{NODE_DIR}annex/{digest}.md"] = content
    r = precheck(harness, token, NODE, {PARTIAL_PATH: partial(digest)})
    assert r.status_code == 202, r.text
    assert len(harness.githost.dispatches) == 1


def test_a_partial_that_cites_nothing_is_prechecked(harness: Harness) -> None:
    seed_node(harness)
    token = harness.token_for("code_alice", "alice")
    text = "theorem OpnProp.and_reassoc : True := by\n  have h : True := sorry\n  exact h\n"
    assert precheck(harness, token, NODE, {PARTIAL_PATH: text}).status_code == 202


def test_a_witness_merged_but_not_rendered_is_products_pending(harness: Harness) -> None:
    """The products still say ``witness-missing``; ``main`` already carries the witness."""
    seed_node(harness)
    add_hole(harness)
    token = harness.token_for("code_alice", "alice")
    hole_dir = f"targets/{TARGET}/nodes/{HOLE}/"
    harness.githost.files[hole_dir + "Witness.lean"] = WITNESS.encode()
    r = precheck(harness, token, HOLE, {hole_dir + "Proof.lean": "theorem x : True := trivial\n"})
    doc = refused(r, 409, "products-pending")
    assert int(r.headers["Retry-After"]) > 0
    assert "/proposals/witness" not in doc["message"], "told to do what is already done"
    no_job(harness)


def test_an_unwitnessed_hole_is_still_told_to_supply_one(harness: Harness) -> None:
    """The guard: a stub slot on ``main``, or none, is the old answer."""
    seed_node(harness)
    add_hole(harness)
    token = harness.token_for("code_alice", "alice")
    hole_dir = f"targets/{TARGET}/nodes/{HOLE}/"
    for slot in (None, b"theorem witness : True := by\n  sorry\n"):
        if slot is not None:
            harness.githost.files[hole_dir + "Witness.lean"] = slot
        harness.context.files.clear()
        r = precheck(
            harness, token, HOLE, {hole_dir + "Proof.lean": "theorem x : True := trivial\n"}
        )
        doc = refused(r, 409, "node-blocked")
        assert "/proposals/witness" in doc["message"]


def test_a_claim_on_that_hole_says_the_same(harness: Harness) -> None:
    """One refusal for one state, on every route that refuses a blocked node (F05-T9)."""
    seed_node(harness)
    add_hole(harness)
    token = harness.token_for("code_alice", "alice")
    harness.githost.files[f"targets/{TARGET}/nodes/{HOLE}/Witness.lean"] = WITNESS.encode()
    r = harness.client.post("/claims", json={"node_id": HOLE}, headers=harness.auth(token))
    refused(r, 409, "products-pending")


def test_an_open_annex_on_another_node_does_not_count(harness: Harness) -> None:
    seed_node(harness)
    token = harness.token_for("code_alice", "alice")
    other = harness.client.post(
        "/annexes",
        json={"node_id": "tutorial-and-swap", "text": ANNEX_TEXT},
        headers=harness.auth(token),
    )
    assert other.status_code == 201, other.text
    harness.githost.dispatches.clear()
    r = precheck(harness, token, NODE, {PARTIAL_PATH: partial("b" * 64)})
    refused(r, 400, "annex-unknown")
