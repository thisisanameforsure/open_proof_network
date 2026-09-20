"""Finding precheck-stale-commit (the 2026-09-19 primes run, agent A): a precheck accepted for a
freshly merged node ran at a commit from before the merge and failed step 2 ``layout-missing``,
naming the contributor's bundle as the thing at fault.

The service keeps each committed product in its own cache entry. A target's ``graph.json`` this
container had never read is fetched new, while ``frontier.json`` is still inside its window: the
node is found in the new products and the job is pinned to the old ``rendered_from``. Every
product carries the commit it was rendered from, so the job is pinned to the commit of the very
document the node was found in (F06-T7).
"""

from __future__ import annotations

import json

from api_fakes import Harness
from test_precheck import NODE, TARGET, bundle_for, post

from opn_api import precheck

OLD = "a" * 40
NEW = "b" * 40


def set_rendered_from(h: Harness, path: str, commit: str) -> None:
    doc = json.loads(h.githost.files[path])
    doc["rendered_from"] = commit
    h.githost.files[path] = json.dumps(doc).encode()


def test_a_job_is_pinned_to_the_commit_its_node_was_found_at(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice-p")
    set_rendered_from(harness, "frontier.json", OLD)
    set_rendered_from(harness, f"targets/{TARGET}/graph.json", NEW)
    harness.context.files.clear()
    r = post(harness, {"node_id": NODE, "bundle": bundle_for(NODE)}, token)
    assert r.status_code == 202, r.text
    assert r.json()["graph_commit"] == NEW
    job = precheck.load(harness.context, r.json()["id"])
    assert job is not None and job.graph_commit == NEW


def test_a_graph_document_without_the_commit_falls_back_to_the_frontier(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice-p")
    path = f"targets/{TARGET}/graph.json"
    doc = json.loads(harness.githost.files[path])
    doc.pop("rendered_from", None)
    harness.githost.files[path] = json.dumps(doc).encode()
    set_rendered_from(harness, "frontier.json", OLD)
    harness.context.files.clear()
    r = post(harness, {"node_id": NODE, "bundle": bundle_for(NODE)}, token)
    assert r.status_code == 202, r.text
    assert r.json()["graph_commit"] == OLD
