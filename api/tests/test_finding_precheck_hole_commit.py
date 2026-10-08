"""F06-T14: a hole written by a merged partial could not be prechecked until a later merge.

Seen on the live record 2026-10-08. Graph bot commit ``28f5a569c`` ("gate: #441 pass") writes the
holes ``erdos-1094--h1/2/3`` and, in the same commit, the products that list them; every one of
those products says ``rendered_from: d1833c0ed``, the merge commit, whose tree carries only
``erdos-1094``. The post-merge job writes holes after it renders, so the commit the products were
rendered from never holds the nodes they create. A job is pinned to ``rendered_from`` (F06-Q10,
Q12), checked out a commit without the node, and failed step 2 ``layout-missing`` after six and a
half minutes, blaming the contributor's bundle; on a quiet network the hole stayed unprecheckable
until any other merge re-rendered the products.

Asserted here: a job is pinned to a commit that carries the node's ``Statement.lean`` — the
``rendered_from`` when it does (Q12's freshly merged variant, unchanged), otherwise the commit the
service read the products at (F05-T13), which is the bot commit or a descendant of it — and when
neither carries it the precheck is refused at once with ``409 products-pending`` saying what it
waits for, before any job exists (C7). The MCP tool forwards to the route, so it answers the same.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from api_fakes import Harness
from mcp_client import McpClient
from test_precheck import NODE, TARGET, bundle_for

from opn_api import frontier, precheck
from opn_api.githost import Fetched, GitHostError

#: The merge commit of a partial: what the bot commit's products say they were rendered from.
MERGE = "d" * 40
#: The post-merge job's bot commit: the products, the network pin and the holes, in one commit.
BOT = "e" * 40
HOLE = f"{NODE}--h1"
GRAPH_PATH = f"targets/{TARGET}/graph.json"


def node_files(node_id: str) -> dict[str, bytes]:
    node_dir = f"targets/{TARGET}/nodes/{node_id}/"
    return {
        node_dir + "META.yaml": b"deps: []\n",
        node_dir + "Statement.lean": b"theorem x : True := sorry\n",
        node_dir + "Witness.lean": b"",
    }


def rendered_from_everywhere(h: Harness, commit: str) -> None:
    for path in ("frontier.json", GRAPH_PATH):
        doc = json.loads(h.githost.files[path])
        doc["rendered_from"] = commit
        h.githost.files[path] = json.dumps(doc).encode()


def bot_commit_writes_hole(h: Harness, *, head: str = BOT) -> None:
    """The state the post-merge job leaves: the products (read at ``head``) list a ready hole and
    say they were rendered from the merge, and the hole's files are absent at the merge."""
    doc = json.loads(h.githost.files[GRAPH_PATH])
    doc["nodes"].append(
        {
            "node_id": HOLE,
            "status": "ready",
            "cause": None,
            "deps": [],
            "origin": "compiler-derived",
            "statement_hash": "1" * 64,
            "relation": None,
            "tutorial": False,
            "trust_base": None,
            "proof_commit": None,
        }
    )
    h.githost.files[GRAPH_PATH] = json.dumps(doc).encode()
    rendered_from_everywhere(h, MERGE)
    hole = node_files(HOLE)
    h.githost.files.update(hole)
    h.githost.absent_at[MERGE] = set(hole)
    h.githost.head = head
    h.context.files.clear()
    frontier.expire(h.context)


def precheck_post(h: Harness, token: str, node_id: str) -> httpx.Response:
    r: httpx.Response = h.client.post(
        "/precheck", json={"node_id": node_id, "bundle": bundle_for(node_id)}, headers=h.auth(token)
    )
    return r


def no_job(h: Harness) -> None:
    assert h.githost.dispatches == [], "a hosted run was spent on a precheck that could not pass"
    assert h.githost.pushes == [], "a job branch was pushed for a precheck that could not pass"
    assert h.store.jobs == {}


def test_a_hole_written_by_the_bot_commit_is_pinned_where_it_exists(harness: Harness) -> None:
    """The live case: the job runs at the commit the products were read at, which carries the
    hole, not at the merge the products name, which does not."""
    token = harness.token_for("code_alice", "alice-p")
    bot_commit_writes_hole(harness)
    r = precheck_post(harness, token, HOLE)
    assert r.status_code == 202, r.text
    assert r.json()["graph_commit"] == BOT, "pinned to a commit without the node"
    job = precheck.load(harness.context, r.json()["id"])
    assert job is not None and job.graph_commit == BOT
    assert len(harness.githost.dispatches) == 1


def test_a_node_no_commit_carries_is_refused_at_once(harness: Harness) -> None:
    """The service cannot say where ``main`` is (C7: it reads by branch name), so the only commit
    it could pin is the merge, which lacks the hole: refused before any job, saying it waits for
    the products to reach a commit that carries the node, with a ``Retry-After``."""
    token = harness.token_for("code_alice", "alice-p")
    bot_commit_writes_hole(harness, head="")
    r = precheck_post(harness, token, HOLE)
    doc: dict[str, Any] = r.json()
    assert (r.status_code, doc.get("error")) == (409, "products-pending"), r.text
    assert HOLE in doc["message"] and MERGE[:12] in doc["message"], doc["message"]
    assert doc["details"]["node_id"] == HOLE
    assert doc["details"]["graph_commit"] == MERGE
    assert r.headers.get("Retry-After"), "a refusal that waits says when to come back"
    no_job(harness)


def test_a_node_absent_at_the_read_commit_too_is_refused(harness: Harness) -> None:
    """Defensive: neither the rendered commit nor the read commit carries the node's statement
    (a tree that disagrees with its own products). No job can pass there, so none is made."""
    token = harness.token_for("code_alice", "alice-p")
    bot_commit_writes_hole(harness)
    harness.githost.absent_at[BOT] = set(node_files(HOLE))
    r = precheck_post(harness, token, HOLE)
    assert (r.status_code, r.json().get("error")) == (409, "products-pending"), r.text
    no_job(harness)


def test_a_node_present_at_rendered_from_keeps_that_commit(harness: Harness) -> None:
    """Q12's case, unchanged: a freshly merged variant is in its merge commit, which the products
    name, so the job stays pinned there even though the products were read at a later commit."""
    token = harness.token_for("code_alice", "alice-p")
    bot_commit_writes_hole(harness)
    harness.githost.files.update(node_files(NODE))
    r = precheck_post(harness, token, NODE)
    assert r.status_code == 202, r.text
    assert r.json()["graph_commit"] == MERGE


def test_an_unreadable_probe_keeps_rendered_from(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C7: when the host cannot say whether the node is at the rendered commit, the job is pinned
    there as before; an unreadable host refuses nothing."""
    token = harness.token_for("code_alice", "alice-p")
    bot_commit_writes_hole(harness)
    real = harness.githost.fetch_raw

    def flaky(repo: str, ref: str, path: str, *, etag: str | None) -> Fetched:
        if path.startswith(f"targets/{TARGET}/nodes/{HOLE}/"):
            msg = f"fetching {path} failed: ConnectError"
            raise GitHostError(msg)
        return real(repo, ref, path, etag=etag)

    monkeypatch.setattr(harness.githost, "fetch_raw", flaky)
    r = precheck_post(harness, token, HOLE)
    assert r.status_code == 202, r.text
    assert r.json()["graph_commit"] == MERGE


def test_the_mcp_tool_gives_the_same_answer(harness: Harness) -> None:
    """``precheck_submission`` forwards to ``POST /precheck``: the same pin, the same refusal."""
    token = harness.token_for("code_alice", "alice-p")
    bot_commit_writes_hole(harness, head="")
    client = McpClient(harness)
    refused = client.failed(
        "precheck_submission", {"node_id": HOLE, "bundle": bundle_for(HOLE)}, token=token
    )
    assert refused["status"] == 409, refused
    assert refused["body"]["error"] == "products-pending", refused
    no_job(harness)

    harness.githost.head = BOT
    frontier.expire(harness.context)
    done = client.ok(
        "precheck_submission", {"node_id": HOLE, "bundle": bundle_for(HOLE)}, token=token
    )
    assert done["body"]["graph_commit"] == BOT, done
