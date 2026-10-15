"""F06-T18: a skeleton's precheck planned its holes against a tree without the newest holes.

Seen on the live record 2026-10-14 (erdos-1094, graph #508 and #510). The post-merge job of the
first skeleton wrote its holes in its bot commit, beside the products that list them, and those
products say they were rendered from the merge, whose tree lacks the holes. A job is pinned to
``rendered_from`` whenever its own node is there (F06-Q10, Q12, Q19), and the second skeleton's
node was, so its job ran without the first skeleton's holes: its two literature holes were
planned as new nodes, duplicates of nodes one commit away, with no warning. A hand dispatch of
``render.yml`` moved ``rendered_from`` past the bot commit, and they planned as lemmas. The
merge itself was not at risk (the gate runs on an up-to-date branch and the post-merge job plans
on the merged tree); the precheck's answer, which is what a contributor acts on, was wrong.

The second shape was on the live graph the next morning: #534 merged (``56c054dd0``) after the
products commit ``49686f793``, its post-merge run still in flight, so a skeleton prechecked then
would plan against a tree without #534's work, and the products saying so were minutes away.

Asserted here (Q23): a job runs at the commit that *wrote* its target's products, which carries
every node they list, when no later commit has touched the target's nodes; when one has, a
render is in flight, and a bundle that makes holes (a partial or reduction, the gate's path role
``partial``) is refused at once with ``409 products-pending``, while any other bundle, whose
verdict reads only immutable statements, runs at the products commit. When the host cannot say,
today's rule stands (C7).
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from api_fakes import Harness
from test_finding_precheck_hole_commit import BOT, HOLE, MERGE, bot_commit_writes_hole
from test_githost_seam import (  # the seam's fixtures, reused as they stand
    BASE_SHA,
    COMMIT_SHA,
    REPO,
    Script,
    clock,
    host,
    install_app,
    pem,
    rsa_key,
    script,
)
from test_precheck import NODE, TARGET, bundle_for

from opn_api import frontier
from opn_api.githost import GitHostError, HttpxGitHost

__all__ = ["clock", "host", "pem", "rsa_key", "script"]  # pytest fixtures

GRAPH_PATH = f"targets/{TARGET}/graph.json"
NODES_PATH = f"targets/{TARGET}/nodes"
#: A merge on the target after the products commit, whose own render has not landed.
LATER = "f" * 40
#: A products-only commit after the bot commit: a hand dispatch of ``render.yml``.
RENDER = "a" * 40
PARTIAL_PATH = f"targets/{TARGET}/nodes/{NODE}/attempts/20261014T081500Z-alice-partial.lean"
#: F29-R5 (D-12 v3.44, which landed while this task waited unpushed): a partial declares its
#: approach, its licence and each hole's label and claim, or the service refuses it before it
#: reaches the pin this file is about.
PARTIAL = (
    "theorem OpnProp.and_reassoc : True := by\n"
    "  -- approach: one hole\n  -- licence: CC-BY-4.0\n"
    "  -- label: the hole\n  -- claim: $\\top$\n  have h : True := sorry\n  exact h\n"
)


def skeleton() -> dict[str, str]:
    return {PARTIAL_PATH: PARTIAL}


def history(h: Harness, *, head: str, products: str | None, nodes: str | None) -> None:
    """Where ``main`` is, and the newest commits there that touched the target's products and
    its nodes."""
    h.githost.head = head
    h.githost.history[(head, GRAPH_PATH)] = products
    h.githost.history[(head, NODES_PATH)] = nodes
    h.context.files.clear()
    frontier.expire(h.context)


def precheck(h: Harness, token: str, bundle: dict[str, str]) -> httpx.Response:
    r: httpx.Response = h.client.post(
        "/precheck", json={"node_id": NODE, "bundle": bundle}, headers=h.auth(token)
    )
    return r


def no_job(h: Harness) -> None:
    assert h.githost.dispatches == [], "a hosted run was spent on a precheck that could not pass"
    assert h.store.jobs == {}


def test_a_skeleton_runs_where_the_newest_holes_are(harness: Harness) -> None:
    """The live case: the node is at ``rendered_from``, a sibling hole is only in the bot
    commit, and the bot commit is the newest to touch the target. The job runs there."""
    token = harness.token_for("code_alice", "alice-p")
    bot_commit_writes_hole(harness)
    history(harness, head=BOT, products=BOT, nodes=BOT)
    r = precheck(harness, token, skeleton())
    assert r.status_code == 202, r.text
    assert r.json()["graph_commit"] == BOT, "planned against a tree without the newest hole"


def test_a_products_only_render_is_pinned_too(harness: Harness) -> None:
    """A later products-only commit (a hand render) wrote the products; the nodes' newest change
    is its ancestor, so the tree there is the tree the products describe."""
    token = harness.token_for("code_alice", "alice-p")
    bot_commit_writes_hole(harness, head=RENDER)
    history(harness, head=RENDER, products=RENDER, nodes=BOT)
    harness.githost.ancestry[(BOT, RENDER)] = True
    r = precheck(harness, token, skeleton())
    assert r.status_code == 202, r.text
    assert r.json()["graph_commit"] == RENDER


def test_a_skeleton_waits_for_a_render_in_flight(harness: Harness) -> None:
    """The morning's case: a merge touched the target's nodes after its products were written.
    Its holes are coming in the next bot commit, so planning now would be planning blind."""
    token = harness.token_for("code_alice", "alice-p")
    bot_commit_writes_hole(harness, head=LATER)
    history(harness, head=LATER, products=BOT, nodes=LATER)
    harness.githost.ancestry[(LATER, BOT)] = False
    r = precheck(harness, token, skeleton())
    doc: dict[str, Any] = r.json()
    assert (r.status_code, doc.get("error")) == (409, "products-pending"), r.text
    assert BOT[:12] in doc["message"] and LATER[:12] in doc["message"], doc["message"]
    assert doc["details"]["node_id"] == NODE
    assert doc["details"]["graph_commit"] == BOT
    assert doc["details"]["nodes_commit"] == LATER
    assert r.headers.get("Retry-After"), "a refusal that waits says when to come back"
    no_job(harness)


def test_a_proof_in_the_same_window_runs_at_the_products_commit(harness: Harness) -> None:
    """A proof's verdict reads only statements, which never change, so the window does not
    hold it up; it runs at the commit whose tree the products describe."""
    token = harness.token_for("code_alice", "alice-p")
    bot_commit_writes_hole(harness, head=LATER)
    history(harness, head=LATER, products=BOT, nodes=LATER)
    harness.githost.ancestry[(LATER, BOT)] = False
    r = precheck(harness, token, bundle_for(NODE))
    assert r.status_code == 202, r.text
    assert r.json()["graph_commit"] == BOT


def test_a_hole_is_pinned_to_the_products_commit(harness: Harness) -> None:
    """Q19's case under the new rule: the hole is in the products commit, so the job runs
    there, as it did through the read commit before."""
    token = harness.token_for("code_alice", "alice-p")
    bot_commit_writes_hole(harness)
    history(harness, head=BOT, products=BOT, nodes=BOT)
    r = harness.client.post(
        "/precheck", json={"node_id": HOLE, "bundle": bundle_for(HOLE)}, headers=harness.auth(token)
    )
    assert r.status_code == 202, r.text
    assert r.json()["graph_commit"] == BOT


def test_an_unanswerable_ancestry_keeps_todays_rule(harness: Harness) -> None:
    """C7: when the host cannot say whether the nodes' newest change precedes the products,
    nothing is refused on that account, and the job is pinned as before Q23."""
    token = harness.token_for("code_alice", "alice-p")
    bot_commit_writes_hole(harness, head=LATER)
    history(harness, head=LATER, products=BOT, nodes=LATER)  # no ancestry seeded: a failure
    r = precheck(harness, token, skeleton())
    assert r.status_code == 202, r.text
    assert r.json()["graph_commit"] == MERGE


def test_no_history_keeps_todays_rule(harness: Harness) -> None:
    """C7: a host that cannot list commits leaves the pin where Q19 put it."""
    token = harness.token_for("code_alice", "alice-p")
    bot_commit_writes_hole(harness)
    r = precheck(harness, token, skeleton())
    assert r.status_code == 202, r.text
    assert r.json()["graph_commit"] == MERGE


# --- the seam: the list-commits API, filtered by path -------------------------------------------

COMMITS = f"/repos/{REPO}/commits"


def test_the_host_asks_for_the_newest_commit_on_a_path(script: Script, host: HttpxGitHost) -> None:
    """One commit, newest first, reachable from the ref, touching the path: GitHub's
    ``sha``, ``path`` and ``per_page`` parameters (probed on the live graph 2026-10-15)."""
    install_app(script).on("GET", COMMITS, json=[{"sha": COMMIT_SHA, "parents": []}])
    assert host.last_commit(REPO, BASE_SHA, "targets/t/nodes") == COMMIT_SHA
    (call,) = script.to("GET", COMMITS)
    assert dict(call.url.params) == {"sha": BASE_SHA, "path": "targets/t/nodes", "per_page": "1"}


def test_a_path_nothing_touched_has_no_commit(script: Script, host: HttpxGitHost) -> None:
    """The live answer for a path no commit touched is an empty list, not an error."""
    install_app(script).on("GET", COMMITS, json=[])
    assert host.last_commit(REPO, BASE_SHA, "targets/none/nodes") is None


@pytest.mark.parametrize("body", [{"message": "x"}, [{"parents": []}], [{"sha": ""}]])
def test_a_malformed_answer_is_a_host_error(script: Script, host: HttpxGitHost, body: Any) -> None:
    """A body is untrusted input (conventions §4): anything but a list of commits with a sha
    is a ``GitHostError``, which the precheck reads as "the host cannot say" (C7)."""
    install_app(script).on("GET", COMMITS, json=body)
    with pytest.raises(GitHostError):
        host.last_commit(REPO, BASE_SHA, "targets/t/nodes")
