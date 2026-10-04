"""F06-T12 (audit 2026-10-04): an installation token carries only what its call needs.

``HttpxGitHost._installation_token_locked`` POSTed ``/app/installations/{id}/access_tokens`` with
no body, and GitHub then issues a token with *every* permission granted to the App on *every*
repository the installation covers. So the token that read a directory listing for an anonymous
caller could also have pushed to the graph, dispatched workflows on the scratch repository or
closed pull requests: one leaked header (a log line, a redirect, a dependency bug) was the App's
whole grant.

The rule. Each seam method names the permissions its own calls need, and the token request asks
for exactly those, on the one repository the call is for (``repositories: [<name>]``, the name
without its owner, as the API takes it). A token is cached per (repository, permission set), so a
read never reuses a write's token and a write never borrows a read's. The table below is the
audit of every call the seam makes (``engineering/evidence/F06/task-12-audit-2026-10-04.txt``
lists the live probe for each permission).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from test_githost_seam import (  # the seam's fixtures, reused as they stand
    BASE_SHA,
    BASE_TREE,
    COMMIT_SHA,
    INSTALLATION_TOKEN,
    NEW_TREE,
    REPO,
    Script,
    clock,
    host,
    install_app,
    pem,
    rsa_key,
    script,
)

from opn_api.githost import HttpxGitHost

__all__ = ["clock", "host", "pem", "rsa_key", "script"]  # pytest fixtures

NAME = REPO.split("/", 1)[1]
TOKENS = "/app/installations/99/access_tokens"
API = f"/repos/{REPO}"


def body_of(request: Any) -> Any:
    return json.loads(request.content) if request.content else None


def pull_closed() -> dict[str, Any]:
    return {"number": 33, "state": "closed", "merged": True, "head": {"sha": "e" * 40}}


#: (method, the calls it makes as scripted answers, how to call it, the permissions it needs)
Case = tuple[str, Callable[[Script], Script], Callable[[HttpxGitHost], Any], dict[str, str]]

CASES: list[Case] = [
    (
        "head_sha",
        lambda s: s.on("GET", f"{API}/git/ref/heads/main", json={"object": {"sha": BASE_SHA}}),
        lambda h: h.head_sha(REPO, "main"),
        {"contents": "read"},
    ),
    (
        "list_dir",
        lambda s: s.on("GET", f"{API}/contents/targets", json=[]),
        lambda h: h.list_dir(REPO, "main", "targets"),
        {"contents": "read"},
    ),
    (
        "is_ancestor",
        lambda s: s.on("GET", f"{API}/compare/{BASE_SHA}...{COMMIT_SHA}", json={"status": "ahead"}),
        lambda h: h.is_ancestor(REPO, BASE_SHA, COMMIT_SHA),
        {"contents": "read"},
    ),
    (
        "push_branch",
        lambda s: (
            s.on("GET", f"{API}/git/ref/heads/main", json={"object": {"sha": BASE_SHA}})
            .on("GET", f"{API}/git/commits/{BASE_SHA}", json={"tree": {"sha": BASE_TREE}})
            .on("POST", f"{API}/git/trees", 201, json={"sha": NEW_TREE})
            .on("POST", f"{API}/git/commits", 201, json={"sha": COMMIT_SHA})
            .on("POST", f"{API}/git/refs", 201, json={})
        ),
        lambda h: h.push_branch(REPO, "job/x", {"a.txt": "a"}, base="main", message="m"),
        {"contents": "write"},
    ),
    (
        "delete_branch",
        lambda s: s.on("DELETE", f"{API}/git/refs/heads/job/x", 204),
        lambda h: h.delete_branch(REPO, "job/x"),
        {"contents": "write"},
    ),
    (
        "open_pull_request",
        lambda s: s.on("POST", f"{API}/pulls", 201, json={"number": 7, "html_url": "u"}),
        lambda h: h.open_pull_request(REPO, head="job/x", base="main", title="t", body="b"),
        {"pull_requests": "write"},
    ),
    (
        "close_pull_request",
        lambda s: s.on("PATCH", f"{API}/pulls/7", json={"number": 7}),
        lambda h: h.close_pull_request(REPO, 7),
        {"pull_requests": "write"},
    ),
    (
        "list_open_pull_requests",
        lambda s: s.on("GET", f"{API}/pulls", json=[]),
        lambda h: h.list_open_pull_requests(REPO),
        {"pull_requests": "read"},
    ),
    (
        "get_pull_request",
        lambda s: (
            s.on("GET", f"{API}/pulls/33", json=pull_closed())
            .on("GET", f"{API}/pulls/33/reviews", json=[])
            .on("GET", f"{API}/actions/runs", json={"workflow_runs": []})
        ),
        lambda h: h.get_pull_request(REPO, 33),
        {"pull_requests": "read", "actions": "read"},
    ),
    (
        "dispatch_workflow",
        lambda s: s.on("POST", f"{API}/actions/workflows/precheck.yml/dispatches", 204),
        lambda h: h.dispatch_workflow(REPO, "precheck.yml", ref="job/x", inputs={"job_id": "j"}),
        {"actions": "write"},
    ),
    (
        "find_run",
        lambda s: s.on(
            "GET", f"{API}/actions/workflows/precheck.yml/runs", json={"workflow_runs": []}
        ),
        lambda h: h.find_run(REPO, "precheck.yml", branch="job/x"),
        {"actions": "read"},
    ),
    (
        "download_artifact",
        lambda s: s.on("GET", f"{API}/actions/runs/5/artifacts", json={"artifacts": []}),
        lambda h: h.download_artifact(REPO, 5, "result-j"),
        {"actions": "read"},
    ),
    (
        "latest_artifact",
        lambda s: s.on("GET", f"{API}/actions/runs/5/artifacts", json={"artifacts": []}),
        lambda h: h.latest_artifact(REPO, 5, "gate-7-"),
        {"actions": "read"},
    ),
]


@pytest.mark.parametrize(("method", "answers", "call", "needs"), CASES, ids=[c[0] for c in CASES])
def test_each_call_asks_for_its_own_permissions_on_its_own_repository(  # noqa: PLR0917 — the case's fields and two fixtures
    script: Script,
    host: HttpxGitHost,
    method: str,
    answers: Callable[[Script], Script],
    call: Callable[[HttpxGitHost], Any],
    needs: dict[str, str],
) -> None:
    answers(install_app(script))
    call(host)
    (minted,) = script.to("POST", TOKENS)
    assert body_of(minted) == {"repositories": [NAME], "permissions": needs}, method


def test_a_token_is_kept_per_permission_set(script: Script, host: HttpxGitHost) -> None:
    """Two reads with one set mint once; a write after them mints its own token, and the reads
    never carry it."""
    install_app(script).on(
        "GET", f"{API}/actions/workflows/precheck.yml/runs", json={"workflow_runs": []}
    ).on("POST", f"{API}/actions/workflows/precheck.yml/dispatches", 204)
    script.routes[("POST", TOKENS)].append(httpx.Response(201, json={"token": "ghs_WRITE"}))
    host.find_run(REPO, "precheck.yml", branch="job/x")
    host.find_run(REPO, "precheck.yml", branch="job/y")
    host.dispatch_workflow(REPO, "precheck.yml", ref="job/x", inputs={})
    host.find_run(REPO, "precheck.yml", branch="job/z")
    minted = script.to("POST", TOKENS)
    assert [body_of(m)["permissions"] for m in minted] == [
        {"actions": "read"},
        {"actions": "write"},
    ]
    reads = script.to("GET", f"{API}/actions/workflows/precheck.yml/runs")
    assert {r.headers["Authorization"] for r in reads} == {f"Bearer {INSTALLATION_TOKEN}"}
    (write,) = script.to("POST", f"{API}/actions/workflows/precheck.yml/dispatches")
    assert write.headers["Authorization"] == "Bearer ghs_WRITE"
