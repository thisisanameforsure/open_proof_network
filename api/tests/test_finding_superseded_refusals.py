"""F05-T11: a refusal on a superseded node names the node that replaced it (F05-Q12).

Found by an outside contributor, 2026-09-18, who was handed a link to ``erdos-69--h2-v2--h1``, a
hole a D-8 revision had replaced the evening before:

* ``POST /claims`` answered ``409 node-not-open`` — "is superseded and not on the frontier" — and
  named no replacement; the contributor guessed it from the ``-v2`` suffix;
* ``POST /precheck`` on it with a wrong path answered ``400 artifact-path-mismatch`` and never
  said the node was superseded at all, because ``check_open`` refuses ``blocked`` alone, so a
  proof of a replaced statement would have been dispatched and checked for nothing.

The replacement is on the graph already: the old node's newest ``node-status/v1`` record carries
``reference`` (``opn-gate revise`` writes it). The service reads that one record, best effort: a
host that cannot say leaves ``replacement`` null and the refusal stands.

The same visit found the guide promising ``409 node-blocked`` for a claim on a blocked node while
the live service answered 201 for a hole awaiting its witness. The 201 is the design (F03-T9:
such a hole is on the frontier and claimable, the witness being the work); the old refusal test
pinned the world before that, a hole the frontier did not list. Both are pinned here.
"""

from __future__ import annotations

import json
from typing import Any

import samples
import yaml
from api_fakes import Harness
from mcp_client import TARGET
from test_finding_mcp_bootstrap import HOLE, add_hole
from test_finding_precheck_blocked import bundle, nothing_started

GRAPH_PATH = f"targets/{TARGET}/graph.json"
OLD = "and-swap-reassoc--h2"
NEW = OLD + "-v2"
RECORD = f"targets/{TARGET}/nodes/{OLD}/status/20260917T173437Z-curator.yaml"


def add_row(harness: Harness, node_id: str, **fields: Any) -> None:
    doc = json.loads(harness.githost.files[GRAPH_PATH])
    row = {
        "node_id": node_id,
        "status": "blocked",
        "cause": "witness-missing",
        "deps": [],
        "origin": "compiler-derived",
        "statement_hash": "3" * 64,
        "relation": None,
        "tutorial": False,
        "trust_base": None,
        "proof_commit": None,
        **fields,
    }
    doc["nodes"] = [n for n in doc["nodes"] if n["node_id"] != node_id] + [row]
    harness.githost.files[GRAPH_PATH] = json.dumps(doc).encode()
    harness.context.files.clear()


def add_revision(harness: Harness, *, record: bool = True) -> None:
    """A superseded hole and its revision, as ``opn-gate revise`` leaves the graph."""
    add_row(harness, OLD, status="superseded", cause=None)
    add_row(harness, NEW)
    if record:
        doc = samples.node_status(
            status="superseded",
            cause=f"superseded by {NEW} on revision request x.yaml (wrong-domain; D-8)",
            reference=NEW,
        )
        harness.githost.files[RECORD] = yaml.safe_dump(doc).encode()


def put_on_frontier(harness: Harness, node_id: str) -> None:
    """The frontier the gate renders since F03-T9: a hole awaiting its witness is an entry."""
    frontier = json.loads(harness.githost.files["frontier.json"])
    entry = samples.frontier_entry(
        node_id=node_id,
        target_id=TARGET,
        origin="compiler-derived",
        statement_hash="1" * 64,
        ready_since=None,
        claimable=True,
    )
    frontier["entries"] = [e for e in frontier["entries"] if e["node_id"] != node_id] + [entry]
    harness.githost.files["frontier.json"] = json.dumps(frontier).encode()
    harness.context.files.clear()


def claim(harness: Harness, node_id: str) -> tuple[int, dict[str, Any]]:
    token = harness.token_for("code_alice", "alice-p")
    r = harness.client.post("/claims", json={"node_id": node_id}, headers=harness.auth(token))
    body: dict[str, Any] = r.json()
    return r.status_code, body


def test_a_claim_on_a_superseded_node_names_its_replacement(harness: Harness) -> None:
    add_revision(harness)
    status, body = claim(harness, OLD)
    assert (status, body.get("error")) == (409, "node-not-open"), body
    assert body["details"] == {"status": "superseded", "replacement": NEW}
    assert NEW in body["message"] and "superseded" in body["message"]
    assert harness.store.list_claims() == []


def test_precheck_refuses_a_superseded_node_before_any_job(harness: Harness) -> None:
    add_revision(harness)
    token = harness.token_for("code_alice", "alice-p")
    r = harness.client.post(
        "/precheck", json={"node_id": OLD, "bundle": bundle(OLD)}, headers=harness.auth(token)
    )
    body = r.json()
    assert (r.status_code, body.get("error")) == (409, "node-superseded"), body
    assert body["details"] == {"status": "superseded", "replacement": NEW}
    assert NEW in body["message"]
    nothing_started(harness)


def test_the_refusal_comes_before_the_path_check(harness: Harness) -> None:
    """What the contributor saw: a wrong path on a superseded node answered only about the path."""
    add_revision(harness)
    token = harness.token_for("code_alice", "alice-p")
    wrong = {f"targets/{TARGET}/nodes/{NEW}/Proof.lean": "theorem x : True := trivial\n"}
    r = harness.client.post(
        "/precheck", json={"node_id": OLD, "bundle": wrong}, headers=harness.auth(token)
    )
    assert r.json().get("error") == "node-superseded", r.text


def test_a_submission_against_a_superseded_node_is_refused_the_same_way(harness: Harness) -> None:
    add_revision(harness)
    token = harness.token_for("code_alice", "alice-p")
    r = harness.client.post(
        "/submissions",
        json={
            "node_id": OLD,
            "artifact_type": "proof",
            "precheck_job_id": "01M2TC4VB0K7D04GWGP4GDMZ9T",
        },
        headers=harness.auth(token),
    )
    body = r.json()
    assert (r.status_code, body.get("error")) == (409, "node-superseded"), body
    assert harness.githost.pushes == []


def test_with_no_record_the_refusal_stands_and_names_nothing(harness: Harness) -> None:
    add_revision(harness, record=False)
    status, body = claim(harness, OLD)
    assert (status, body.get("error")) == (409, "node-not-open"), body
    assert body["details"] == {"status": "superseded", "replacement": None}


def test_a_host_that_cannot_list_the_records_does_not_turn_a_refusal_into_an_error(
    harness: Harness,
) -> None:
    add_revision(harness)
    token = harness.token_for("code_alice", "alice-p")
    warm = harness.client.post("/claims", json={"node_id": OLD}, headers=harness.auth(token))
    assert warm.status_code == 409  # the products are cached; the record listing is not
    harness.githost.unreachable = True
    r = harness.client.post(
        "/precheck", json={"node_id": OLD, "bundle": bundle(OLD)}, headers=harness.auth(token)
    )
    body = r.json()
    assert (r.status_code, body.get("error")) == (409, "node-superseded"), body


def test_a_proved_node_names_no_replacement(harness: Harness) -> None:
    status, body = claim(harness, "already-proved")
    assert (status, body.get("error")) == (409, "node-not-open"), body
    assert body["details"] == {"status": "proved", "replacement": None}


def test_a_hole_on_the_frontier_is_claimed(harness: Harness) -> None:
    """The live behaviour the guide contradicted: the witness is the work, so the hole is
    claimable (F03-T9, ``products.workable``), and the claim route reads the frontier's flag."""
    add_hole(harness)
    put_on_frontier(harness, HOLE)
    status, body = claim(harness, HOLE)
    assert status == 201, body
    assert [c.node_id for c in harness.store.list_claims()] == [HOLE]
