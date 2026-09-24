"""F07-T43 (Q50; ruling D5, 2026-09-24): ``DELETE /submissions/<id>``, withdrawing one's own PR.

The story. Six agents on the calibration targets, 2026-09-24 12:24-13:25Z
(``engineering/session-notes/2026-09-24-calibration-testers.md``). Three asked for the same thing:
erdos-1050-http re-filed a speculative proposal with its hazards acknowledged (#203) and could not
close the red first try (#202, the same node id), "I found no route to withdraw/close my own failed
proposal"; erdos-402-mcp opened #181 as a duplicate of #177 and #195 with a wrong witness, and had
"no withdraw tool on the MCP"; erdos-69-http filed a duplicate circularity claim (#194) that "will
merge as a duplicate unless a curator closes it". ``GET /`` listed no such route, so each of those
pull requests stayed in the merge queue until a person closed it.

The mechanism. The service opens pull requests on a contributor's behalf and records who (the
record's ``pseudonym``, F07-T16), but offered no way back: the only close was a person's on the
host.

The owner's ruling D5: add ``DELETE /submissions/<id>``. Holder only: the identity that opened it
(the record's pseudonym, which the store keeps unique), else ``403 not-holder``; it closes the pull
request and deletes its branch through the App (GitHost seam), ``409 submission-merged`` if it has
merged, harmless on one already closed, ``404`` for an id the service never recorded. The record is
closed in the store, so ``GET /submissions.json`` drops it at once and the duplicate rule stops
counting it. The graph's merge workflow cannot be read here (the graph repository is not in this
checkout); a closed pull request is outside what it merges by construction, and the service's side
of that — the record closed, the host told to close — is what these tests assert. The MCP tool is
``withdraw_submission``.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from api_fakes import TUTORIAL_NODE, Harness, make_harness
from mcp_client import McpClient
from test_githost_seam import (  # noqa: F401 — fixtures: the scripted transport and the App
    REPO,
    Script,
    host,
    install_app,
    pem,
    rsa_key,
    script,
)
from test_store_seam import dynamo

from opn_api.githost import GitHostError, HttpxGitHost
from opn_api.store import MemoryStore

_N = iter(range(1, 10_000))


@pytest.fixture(params=["memory", "dynamodb"])
def h(request: pytest.FixtureRequest) -> Iterator[Harness]:
    store = MemoryStore() if request.param == "memory" else dynamo()
    harness = make_harness(store=store)
    with harness.client:
        yield harness


def annex(h: Harness, token: str) -> dict[str, Any]:
    text = f"An informal argument, number {next(_N)}.\n"
    r = h.client.post(
        "/annexes", json={"node_id": TUTORIAL_NODE, "text": text}, headers=h.auth(token)
    )
    assert r.status_code == 201, r.text
    doc: dict[str, Any] = r.json()
    return doc


def withdraw(h: Harness, token: str | None, submission_id: str) -> Any:
    headers = h.auth(token) if token else {}
    return h.client.delete(f"/submissions/{submission_id}", headers=headers)


def closed_on_host(h: Harness) -> list[int]:
    return list(getattr(h.githost, "closed_pulls", []))


def deleted_on_host(h: Harness) -> list[str]:
    return list(getattr(h.githost, "deleted_branches", []))


def open_ids(h: Harness) -> list[str]:
    return [s["id"] for s in h.client.get("/submissions.json").json()["open"]]


def test_the_holder_closes_their_open_pull_request(h: Harness) -> None:
    alice = h.token_for("code_alice", "alice")
    opened = annex(h, alice)
    r = withdraw(h, alice, opened["id"])
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["withdrawn"] is True
    assert doc["submission"]["id"] == opened["id"]
    assert doc["submission"]["closed"] is not None
    assert doc["pull_request"]["state"] == "closed" and doc["pull_request"]["merged"] is False
    assert doc["branch_deleted"] is True
    assert closed_on_host(h) == [opened["pr_number"]]
    assert deleted_on_host(h) == [h.githost.pulls[0].head]
    # the store has closed the record, in both stores
    record = h.store.get_submission(opened["id"])
    assert record is not None and record.closed is not None
    assert opened["id"] not in [s.id for s in h.store.list_open_submissions()]
    # and the route that reads it says so
    got = h.client.get(f"/submissions/{opened['id']}").json()
    assert got["submission"]["closed"] is not None
    assert got["pull_request"]["state"] == "closed"


def test_the_pull_request_number_names_it_too(h: Harness) -> None:
    alice = h.token_for("code_alice", "alice")
    opened = annex(h, alice)
    r = withdraw(h, alice, f"{opened['pr_number']:06d}")
    assert r.status_code == 200, r.text
    assert r.json()["submission"]["id"] == opened["id"]


def test_another_identity_gets_403(h: Harness) -> None:
    alice = h.token_for("code_alice", "alice")
    bob = h.token_for("code_bob", "bob")
    opened = annex(h, alice)
    r = withdraw(h, bob, opened["id"])
    assert r.status_code == 403, r.text
    assert r.json()["error"] == "not-holder"
    assert closed_on_host(h) == [] and deleted_on_host(h) == []
    assert open_ids(h) == [opened["id"]]


def test_a_merged_submission_gets_409(h: Harness) -> None:
    alice = h.token_for("code_alice", "alice")
    opened = annex(h, alice)
    h.githost.set_pull_request_state(opened["pr_number"], state="closed", merged=True)
    r = withdraw(h, alice, opened["id"])
    assert r.status_code == 409, r.text
    assert r.json()["error"] == "submission-merged"
    assert closed_on_host(h) == [] and deleted_on_host(h) == []


def test_merged_is_read_from_the_host_not_the_cache(h: Harness) -> None:
    """A read a moment ago cached the pull request as open; it has merged since. Withdrawing it
    must not answer "withdrawn" from the cache (added with the fix, as the guard for its
    fresh read)."""
    alice = h.token_for("code_alice", "alice")
    opened = annex(h, alice)
    assert h.client.get(f"/submissions/{opened['id']}").json()["pull_request"]["state"] == "open"
    h.githost.set_pull_request_state(opened["pr_number"], state="closed", merged=True)
    r = withdraw(h, alice, opened["id"])
    assert r.status_code == 409, r.text
    assert closed_on_host(h) == []


def test_twice_is_harmless(h: Harness) -> None:
    alice = h.token_for("code_alice", "alice")
    opened = annex(h, alice)
    first = withdraw(h, alice, opened["id"])
    second = withdraw(h, alice, opened["id"])
    assert (first.status_code, second.status_code) == (200, 200), second.text
    assert second.json()["withdrawn"] is True
    assert second.json()["submission"]["closed"] == first.json()["submission"]["closed"]
    assert closed_on_host(h) == [opened["pr_number"]]  # the host was asked once


def test_one_closed_on_the_host_already_is_harmless(h: Harness) -> None:
    alice = h.token_for("code_alice", "alice")
    opened = annex(h, alice)
    h.githost.set_pull_request_state(opened["pr_number"], state="closed", merged=False)
    r = withdraw(h, alice, opened["id"])
    assert r.status_code == 200, r.text
    assert r.json()["submission"]["closed"] is not None
    assert closed_on_host(h) == []  # nothing to close


def test_the_snapshot_drops_it(h: Harness) -> None:
    alice = h.token_for("code_alice", "alice")
    kept, gone = annex(h, alice), annex(h, alice)
    assert sorted(open_ids(h)) == sorted([kept["id"], gone["id"]])
    assert withdraw(h, alice, gone["id"]).status_code == 200
    # at once: no cache window to wait out, the record is closed
    assert open_ids(h) == [kept["id"]]


def test_unknown_ids_are_404(h: Harness) -> None:
    alice = h.token_for("code_alice", "alice")
    for raw in ("01ARZ3NDEKTSV4RRFFQ69G5FAV", "000042"):
        r = withdraw(h, alice, raw)
        assert r.status_code == 404, (raw, r.text)
        assert r.json()["error"] == "submission-unknown"
    assert withdraw(h, alice, "not an id!").status_code == 400


def test_without_a_bearer_is_401() -> None:
    h = make_harness()
    alice = h.token_for("code_alice", "alice")
    opened = annex(h, alice)
    r = withdraw(h, None, opened["id"])
    assert r.status_code == 401, r.text
    assert open_ids(h) == [opened["id"]]


def test_a_host_failure_is_502_and_the_record_stays_open() -> None:
    h = make_harness()
    alice = h.token_for("code_alice", "alice")
    opened = annex(h, alice)
    h.githost.app_failure = "PATCH /repos/o/g/pulls/1 returned 502"
    r = withdraw(h, alice, opened["id"])
    assert r.status_code == 502, r.text
    assert r.json()["error"] == "withdraw-failed"
    h.githost.app_failure = None
    record = h.store.get_submission(opened["id"])
    assert record is not None and record.closed is None


def test_a_branch_the_service_did_not_name_is_never_deleted() -> None:
    """Only a branch the service itself opened (its ``submit/``, ``append/`` or ``propose/``
    prefixes) is deleted; the pull request is still closed."""
    h = make_harness()
    alice = h.token_for("code_alice", "alice")
    opened = annex(h, alice)
    h.githost.pulls[0].head = "someone/elses-branch"
    r = withdraw(h, alice, opened["id"])
    assert r.status_code == 200, r.text
    assert r.json()["branch_deleted"] is False
    assert closed_on_host(h) == [opened["pr_number"]] and deleted_on_host(h) == []


def test_the_route_is_an_authenticated_write_with_a_d35_row() -> None:
    from opn_api import routes  # noqa: PLC0415

    label = "DELETE /submissions/{submission_id}"
    spec = next((r for r in routes.ROUTES if r.label == label), None)
    assert spec is not None, "DELETE /submissions/{submission_id} is not in the routes table"
    assert spec.write and spec.authenticated and spec.feature == "F07"
    assert spec.d35 == "DELETE /submissions/<id>"


def test_withdraw_submission_over_mcp_is_the_route() -> None:
    h = make_harness()
    alice = h.token_for("code_alice", "alice")
    opened = annex(h, alice)
    result = McpClient(h).call("withdraw_submission", {"submission_id": opened["id"]}, token=alice)
    assert not result.isError, result.structuredContent
    doc = result.structuredContent or {}
    assert doc.get("status") == 200 and doc["body"]["withdrawn"] is True
    assert closed_on_host(h) == [opened["pr_number"]]


# --- the seam: HttpxGitHost against a scripted GitHub ---------------------------------------------


def test_the_seam_closes_the_pull_request_and_names_its_branch(
    script: Script,  # noqa: F811 — the fixture imported above
    host: HttpxGitHost,  # noqa: F811
) -> None:
    install_app(script).on(
        "PATCH",
        f"/repos/{REPO}/pulls/7",
        json={
            "number": 7,
            "state": "closed",
            "merged": False,
            "head": {"ref": "append/01ABC", "repo": {"full_name": REPO}},
        },
    )
    close = getattr(host, "close_pull_request", None)
    assert close is not None, "HttpxGitHost has no close_pull_request"
    assert close(REPO, 7) == "append/01ABC"
    assert script.sent("PATCH", f"/repos/{REPO}/pulls/7") == {"state": "closed"}


def test_the_seam_names_no_branch_for_a_fork(
    script: Script,  # noqa: F811
    host: HttpxGitHost,  # noqa: F811
) -> None:
    install_app(script).on(
        "PATCH",
        f"/repos/{REPO}/pulls/7",
        json={"number": 7, "head": {"ref": "main", "repo": {"full_name": "someone/fork"}}},
    )
    close = getattr(host, "close_pull_request", None)
    assert close is not None, "HttpxGitHost has no close_pull_request"
    assert close(REPO, 7) is None


def test_the_seam_deletes_a_branch_and_a_missing_one_is_not_an_error(
    script: Script,  # noqa: F811
    host: HttpxGitHost,  # noqa: F811
) -> None:
    ref = f"/repos/{REPO}/git/refs/heads/append/01ABC"
    install_app(script).on("DELETE", ref, 204).on("DELETE", ref, 422, json={"message": "x"})
    delete = getattr(host, "delete_branch", None)
    assert delete is not None, "HttpxGitHost has no delete_branch"
    assert delete(REPO, "append/01ABC") is True
    assert delete(REPO, "append/01ABC") is False  # "Reference does not exist": already gone


def test_the_seam_refusal_names_the_call(
    script: Script,  # noqa: F811
    host: HttpxGitHost,  # noqa: F811
) -> None:
    install_app(script).on(
        "PATCH",
        f"/repos/{REPO}/pulls/7",
        403,
        json={"message": "Resource not accessible by integration"},
    )
    close = getattr(host, "close_pull_request", None)
    assert close is not None, "HttpxGitHost has no close_pull_request"
    with pytest.raises(GitHostError, match="pulls/7 returned 403"):
        close(REPO, 7)
