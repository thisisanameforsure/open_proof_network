"""F07-T47 (bugs.md item 1, 2026-09-30): unauthenticated reads spend the App's host budget, and
when it is gone nothing works and nothing goes red.

The story. ``GET /submissions/<id>`` read the host per call and ``GET /submissions.json``
reconciled every open record against it, three or four API calls each; eighteen pollers
exhausted GitHub's hourly limit for the App installation at 19:35Z. Then ``POST /precheck``
answered ``502 dispatch-failed``, every write that opens or closes a pull request answered
``502 pull-request-failed`` with GitHub's raw text and no ``Retry-After``, ``/health`` still said
``ok: true``, and the by-id route served a stale ``pull_request`` block with a live-looking
``waiting_on`` beside a ``pull_request_error``.

The rules. (a) The host seam records the budget the host last reported on any API answer and
knows a rate-limit refusal (403/429 with ``X-RateLimit-Remaining: 0``) as its own error kind.
(b) Such a refusal is a ``503 host-budget-exhausted`` with ``Retry-After`` computed from the
reset, on every route that needs the host to act. (c) The by-id route and the listing serve
their cached state with ``read_at`` and ``stale: true`` when the host could not be read, with
``Retry-After`` when the budget is why — never a live-looking block beside an error. (d) The
listing reconciles the whole queue against one open-pull-request listing per window, not one
read per record; and no unauthenticated read spends the host once the budget is at or below a
reserve kept for writes. (e) ``/health`` reports the budget and goes red while it is spent.
Windows and the reserve are settings (C6).
"""

from __future__ import annotations

import time
from datetime import timedelta
from typing import Any

import pytest
from api_fakes import TUTORIAL_NODE, Harness, make_harness
from test_githost_seam import (  # the seam's fixtures, reused as they stand
    PULL,
    REPO,
    REVIEWS,
    Script,
    assert_clean,
    clock,
    host,
    install_app,
    logs,
    pem,
    rsa_key,
    script,
    secrets,
)
from test_pending_submissions import record

from opn_api import clock as clockmod
from opn_api import config
from opn_api.githost import GitHostError, HostBudget, HttpxGitHost, OpenPullRequest, RateLimitError
from opn_api.mcp import results

__all__ = ["clock", "host", "logs", "pem", "rsa_key", "script", "secrets"]  # pytest fixtures

NOW = 1_800_000_000  # test_githost_seam.Clock's frozen now
RESET_IN_S = 1800
PULLS = f"/repos/{REPO}/pulls"
HEADERS_SPENT = {
    "X-RateLimit-Limit": "5000",
    "X-RateLimit-Remaining": "0",
    "X-RateLimit-Reset": str(NOW + RESET_IN_S),
}


def runs_body() -> dict[str, Any]:
    return {"workflow_runs": []}


def pull_body() -> dict[str, Any]:
    return {
        "number": 33,
        "html_url": "https://github.com/owner/scratch/pull/33",
        "state": "open",
        "merged": False,
        "mergeable_state": "clean",
        "head": {"sha": "e" * 40},
        "merge_commit_sha": None,
    }


# --- (a) the seam: the budget it saw, the refusal it knows ----------------------------------------


def test_the_seam_records_the_budget_the_host_last_reported(
    script: Script, host: HttpxGitHost, clock: Any
) -> None:
    """The last ``X-RateLimit-*`` seen on any answer, with when it was read; an answer without
    the headers (the runs listing here) leaves the last reading standing."""
    install_app(script).on(
        "GET",
        PULL,
        json=pull_body(),
        headers={
            "X-RateLimit-Limit": "5000",
            "X-RateLimit-Remaining": "4321",
            "X-RateLimit-Reset": str(NOW + RESET_IN_S),
        },
    ).on(
        "GET",
        REVIEWS,
        json=[],
        headers={"X-RateLimit-Limit": "5000", "X-RateLimit-Remaining": "4320"},
    ).on("GET", f"/repos/{REPO}/actions/runs", json=runs_body())
    assert host.budget() is None
    host.get_pull_request(REPO, 33)
    assert host.budget() == HostBudget(
        remaining=4320, limit=5000, reset_at=None, read_at=float(NOW)
    )


@pytest.mark.parametrize("status", [403, 429])
def test_a_refusal_with_remaining_zero_is_a_rate_limit_error(  # noqa: PLR0917 — fixtures
    script: Script, host: HttpxGitHost, clock: Any, secrets: list[str], logs: Any, status: int
) -> None:
    """GitHub's primary rate limit: 403 (or 429) with ``X-RateLimit-Remaining: 0`` and the reset
    epoch. The seam raises its own kind, carrying the budget, naming the reset and never the
    credential; and the budget it reports afterwards is the spent one."""
    install_app(script).on(
        "GET", PULL, status, json={"message": "API rate limit exceeded"}, headers=HEADERS_SPENT
    )
    with pytest.raises(RateLimitError) as raised:
        host.get_pull_request(REPO, 33)
    assert raised.value.budget == HostBudget(0, 5000, float(NOW + RESET_IN_S), float(NOW))
    assert str(raised.value.budget.reset_iso) in str(raised.value)
    assert_clean(str(raised.value) + logs.text, secrets)
    assert host.budget() == raised.value.budget


def test_a_403_with_budget_left_is_an_ordinary_refusal(script: Script, host: HttpxGitHost) -> None:
    """A permission refusal carries a remaining count above zero: not a rate limit."""
    install_app(script).on(
        "GET",
        PULL,
        403,
        json={"message": "Resource not accessible by integration"},
        headers={"X-RateLimit-Limit": "5000", "X-RateLimit-Remaining": "4000"},
    )
    with pytest.raises(GitHostError) as raised:
        host.get_pull_request(REPO, 33)
    assert not isinstance(raised.value, RateLimitError)
    assert "403" in str(raised.value)


def test_a_write_refused_for_budget_is_the_same_kind(
    script: Script, host: HttpxGitHost, clock: Any
) -> None:
    """``_send`` (the path every write takes) raises the kind too, not a bare status."""
    install_app(script).on("POST", PULLS, 403, json={"message": "rate"}, headers=HEADERS_SPENT)
    with pytest.raises(RateLimitError):
        host.open_pull_request(REPO, head="b", base="main", title="t", body="")


def test_the_open_listing_is_one_call_as_the_app(script: Script, host: HttpxGitHost) -> None:
    """``GET /repos/{repo}/pulls?state=open&per_page=100``: the queue's open set in one call,
    shaped to number, url and head (a guard on the new seam method; green from the start)."""

    def entry(number: int, ref: str, *, draft: bool = False, fork: bool = False) -> dict[str, Any]:
        """One entry in the host's own shape (read from the graph's listing, 2026-10-01)."""
        return {
            "number": number,
            "html_url": f"https://github.com/o/r/pull/{number}",
            "draft": draft,
            "head": {
                "sha": str(number) * 40,
                "ref": ref,
                "repo": {"full_name": "someone/fork" if fork else REPO},
            },
            "base": {"ref": "main", "repo": {"full_name": REPO}},
        }

    install_app(script).on(
        "GET",
        PULLS,
        json=[entry(7, "submit/01A"), entry(9, "append/01B", draft=True, fork=True), "junk"],
    )
    # F05-T18: with what the merge actor's ``candidates`` reads of each, from the same call.
    assert host.list_open_pull_requests(REPO) == [
        OpenPullRequest(7, "https://github.com/o/r/pull/7", "7" * 40, "submit/01A", "main"),
        OpenPullRequest(
            9, "https://github.com/o/r/pull/9", "9" * 40, "append/01B", "main", True, False
        ),
    ]
    (call,) = script.to("GET", PULLS)
    assert dict(call.url.params) == {"state": "open", "per_page": "100", "page": "1"}


# --- the routes, over the fake host ---------------------------------------------------------------


def spent(h: Harness, remaining: int = 0, *, ahead_s: int = RESET_IN_S) -> HostBudget:
    """A budget as the host would report it now, resetting ``ahead_s`` from the fake clock."""
    now = h.clock.now().timestamp()
    return HostBudget(remaining=remaining, limit=5000, reset_at=now + ahead_s, read_at=now)


def annex(h: Harness, token: str, n: int = 0) -> dict[str, Any]:
    r = h.client.post(
        "/annexes",
        json={
            "node_id": TUTORIAL_NODE,
            "text": f"An informal argument, number {n}.\n",
            "licence": "CC-BY-4.0",
        },
        headers=h.auth(token),
    )
    assert r.status_code == 201, r.text
    doc: dict[str, Any] = r.json()
    return doc


def get(h: Harness, submission_id: str) -> Any:
    r = h.client.get(f"/submissions/{submission_id}")
    assert r.status_code == 200, (submission_id, r.status_code, r.text)
    return r


def age_pulls(h: Harness) -> None:
    window = h.settings.pull_max_stale_s
    for entry in h.context.pulls.values():
        entry.fetched_at = time.monotonic() - (window + 1)


def age_listing(h: Harness) -> None:
    listing = getattr(h.context, "open_pulls", None)
    assert listing is not None, "Context.open_pulls holds no cached listing"
    listing.fetched_at = time.monotonic() - (h.settings.pull_listing_max_stale_s + 1)


def fill(h: Harness, count: int, *, merged: frozenset[int] = frozenset()) -> None:
    for number in range(1, count + 1):
        h.store.put_submission(record(number, kind="annex"))
        if number in merged:
            h.githost.set_pull_request_state(number, state="closed", merged=True)
        else:
            h.githost.set_pull_request_state(number, mergeable_state="behind")


def snapshot(h: Harness) -> Any:
    r = h.client.get("/submissions.json")
    assert r.status_code == 200, r.text
    return r


# --- (b) a refusal for budget is a 503 with Retry-After, on every route that acts ----------------


def assert_budget_refusal(r: Any) -> None:
    assert r.status_code == 503, (r.status_code, r.text)
    assert r.json()["error"] == "host-budget-exhausted"
    assert r.headers.get("Retry-After") == str(RESET_IN_S), dict(r.headers)
    message = r.json()["message"]
    assert "budget" in message and "refills at" in message, message


def test_a_precheck_dispatch_refused_for_budget_is_a_503_naming_the_reset(
    harness: Harness,
) -> None:
    harness.githost.rate_limited = spent(harness)
    r = harness.client.post(
        "/precheck",
        json={
            "node_id": TUTORIAL_NODE,
            "bundle": {
                f"targets/propositional/nodes/{TUTORIAL_NODE}/Proof.lean": (
                    "import Nodes.X.Context\n\ntheorem x : True := trivial\n"
                )
            },
        },
    )
    assert_budget_refusal(r)


def test_opening_a_pull_request_refused_for_budget_is_a_503(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    harness.githost.rate_limited = spent(harness)
    r = harness.client.post(
        "/annexes",
        json={"node_id": TUTORIAL_NODE, "text": "An informal argument.\n", "licence": "CC-BY-4.0"},
        headers=harness.auth(token),
    )
    assert_budget_refusal(r)


def test_withdrawing_refused_for_budget_is_a_503(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    opened = annex(harness, token)
    harness.githost.rate_limited = spent(harness)
    r = harness.client.delete(f"/submissions/{opened['id']}", headers=harness.auth(token))
    assert_budget_refusal(r)
    assert harness.store.get_submission(opened["id"]).closed is None  # type: ignore[union-attr]


# --- (c) the by-id route: a cached block says when it was read and that it is stale --------------


def test_the_by_id_read_serves_its_cached_block_as_stale_with_read_at(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    annex(harness, token)
    harness.githost.set_pull_request_state(1, mergeable_state="clean")
    read_at = clockmod.render(harness.clock.now())
    fresh = get(harness, "1").json()
    assert fresh["pull_request"]["read_at"] == read_at
    assert fresh["pull_request"]["stale"] is False
    assert fresh["pull_request"]["waiting_on"] == "gate"  # no gate run on the fake yet
    assert results.violations("get_submission", fresh) == []

    harness.clock.advance(minutes=5)
    age_pulls(harness)
    harness.githost.rate_limited = spent(harness)
    r = get(harness, "1")
    served = r.json()
    assert served["pull_request"] == {**fresh["pull_request"], "stale": True}, served
    assert served["pull_request"]["read_at"] == read_at  # when it was last true, not now
    assert str(served["pull_request_error"]).startswith("host-budget-exhausted")
    assert r.headers.get("Retry-After") == str(RESET_IN_S), dict(r.headers)
    assert results.violations("get_submission", served) == []


def test_any_host_failure_marks_the_cached_block_stale(harness: Harness) -> None:
    """Not only the budget: a 502 from the host leaves the last block served as stale, and no
    Retry-After, because nothing says when the host will answer."""
    token = harness.token_for("code_alice", "alice")
    annex(harness, token)
    get(harness, "1")
    age_pulls(harness)
    harness.githost.pr_lookup_failure = "GET /repos/o/g/pulls/1 returned 502"
    r = get(harness, "1")
    assert r.json()["pull_request"]["stale"] is True
    assert "502" in r.json()["pull_request_error"]
    assert "Retry-After" not in r.headers


def test_a_first_read_with_the_budget_spent_is_a_null_block_with_retry_after(
    harness: Harness,
) -> None:
    harness.store.put_submission(record(7, kind="annex"))
    harness.githost.rate_limited = spent(harness)
    r = get(harness, "7")
    assert r.json()["pull_request"] is None
    assert str(r.json()["pull_request_error"]).startswith("host-budget-exhausted")
    assert r.headers.get("Retry-After") == str(RESET_IN_S)


def test_a_closed_record_block_says_when_it_was_read(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    annex(harness, token)
    harness.githost.set_pull_request_state(1, state="closed", merged=True)
    doc = get(harness, "1").json()
    assert doc["submission"]["closed"] == clockmod.render(harness.clock.now())
    assert doc["pull_request"]["read_at"] == clockmod.render(harness.clock.now())
    assert doc["pull_request"]["stale"] is False
    assert results.violations("get_submission", doc) == []


# --- (d) the listing: one host call per window for the whole queue -------------------------------


def test_the_listing_costs_one_host_call_for_the_whole_queue(harness: Harness) -> None:
    fill(harness, 25)
    r = snapshot(harness)
    doc = r.json()
    assert len(doc["open"]) == 25
    assert harness.githost.listing_calls == 1
    assert harness.githost.pull_lookups == [], "the listing read a record on its own"
    assert doc["host"] == {
        "read_at": clockmod.render(harness.clock.now()),
        "stale": False,
        "error": None,
    }
    assert results.violations("list_submissions", doc) == []

    snapshot(harness)
    assert harness.githost.listing_calls == 1  # inside the window: no call at all
    age_listing(harness)
    snapshot(harness)
    assert harness.githost.listing_calls == 2


def test_a_record_the_listing_lacks_is_read_once_and_closed(harness: Harness) -> None:
    fill(harness, 5, merged=frozenset({3}))
    doc = snapshot(harness).json()
    assert [e["pr_number"] for e in doc["open"]] == [1, 2, 4, 5]
    assert harness.githost.listing_calls == 1
    assert harness.githost.pull_lookups == [3]
    closed = harness.store.get_submission_by_pr(3)
    assert closed is not None and closed.closed is not None
    assert (closed.final_state or {}).get("merged") is True
    snapshot(harness)
    assert harness.githost.pull_lookups == [3]  # closed: never read again


def test_the_listing_is_served_stale_when_the_budget_is_spent(harness: Harness) -> None:
    fill(harness, 3)
    first_at = clockmod.render(harness.clock.now())
    snapshot(harness)
    harness.clock.advance(minutes=2)
    age_listing(harness)
    harness.githost.rate_limited = spent(harness)
    r = snapshot(harness)
    doc = r.json()
    assert [e["pr_number"] for e in doc["open"]] == [1, 2, 3]
    assert doc["host"]["stale"] is True
    assert doc["host"]["read_at"] == first_at
    assert str(doc["host"]["error"]).startswith("host-budget-exhausted")
    assert r.headers.get("Retry-After") == str(RESET_IN_S)
    assert harness.githost.pull_lookups == []
    assert results.violations("list_submissions", doc) == []


def test_reads_do_not_spend_the_host_at_or_below_the_reserve(harness: Harness) -> None:
    """The budget is at 150 of 5000 with the reset twenty minutes ahead and the reserve is 200:
    the by-id read and the listing serve what they have as stale, with Retry-After, and make no
    call; once the reset has passed they read again."""
    token = harness.token_for("code_alice", "alice")
    annex(harness, token)
    get(harness, "1")
    snapshot(harness)
    assert (len(harness.githost.pull_lookups), harness.githost.listing_calls) == (1, 1)

    harness.githost.budget_seen = spent(harness, remaining=150, ahead_s=1200)
    age_pulls(harness)
    age_listing(harness)
    r = get(harness, "1")
    assert r.json()["pull_request"]["stale"] is True
    assert "reserve" in r.json()["pull_request_error"]
    assert r.headers.get("Retry-After") == "1200"
    listed = snapshot(harness)
    assert listed.json()["host"]["stale"] is True
    assert listed.headers.get("Retry-After") == "1200"
    assert (len(harness.githost.pull_lookups), harness.githost.listing_calls) == (1, 1)

    harness.clock.advance(minutes=21)
    age_pulls(harness)
    age_listing(harness)
    assert get(harness, "1").json()["pull_request"]["stale"] is False
    snapshot(harness)
    assert (len(harness.githost.pull_lookups), harness.githost.listing_calls) == (2, 2)


# --- (e) health -----------------------------------------------------------------------------------


def test_health_reports_the_budget_and_goes_red_while_it_is_spent(harness: Harness) -> None:
    r = harness.client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "store": "memory", "host_budget": None}

    harness.githost.budget_seen = spent(harness, remaining=4000)
    now = clockmod.render(harness.clock.now())
    reset = clockmod.render(harness.clock.now() + timedelta(seconds=RESET_IN_S))
    r = harness.client.get("/health")
    assert r.status_code == 200
    assert r.json()["host_budget"] == {
        "remaining": 4000,
        "limit": 5000,
        "reset_at": reset,
        "read_at": now,
    }

    harness.githost.budget_seen = spent(harness)
    r = harness.client.get("/health")
    assert r.status_code == 503, r.text
    assert r.json()["ok"] is False
    assert r.json()["host_budget"]["remaining"] == 0
    assert r.headers.get("Retry-After") == str(RESET_IN_S)

    harness.clock.advance(seconds=RESET_IN_S + 1)
    r = harness.client.get("/health")
    assert r.status_code == 200 and r.json()["ok"] is True  # the reset has passed


# --- C6: the windows and the reserve are settings -------------------------------------------------


def test_the_windows_and_the_reserve_are_settings() -> None:
    s = config.load({})
    assert (s.pull_max_stale_s, s.pull_listing_max_stale_s, s.host_budget_reserve) == (
        180,
        60,
        200,
    )
    s = config.load(
        {
            "OPN_API_PULL_MAX_STALE_S": "30",
            "OPN_API_PULL_LISTING_MAX_STALE_S": "15",
            "OPN_API_HOST_BUDGET_RESERVE": "0",
        }
    )
    assert (s.pull_max_stale_s, s.pull_listing_max_stale_s, s.host_budget_reserve) == (30, 15, 0)
    with pytest.raises(config.ConfigError, match="negative"):
        config.load({"OPN_API_HOST_BUDGET_RESERVE": "-1"})
    h = make_harness({"OPN_API_HOST_BUDGET_RESERVE": "0"})
    with h.client:
        token = h.token_for("code_alice", "alice")
        annex(h, token)
        get(h, "1")
        h.githost.budget_seen = spent(h, remaining=1, ahead_s=600)  # above a reserve of none
        age_pulls(h)
        assert get(h, "1").json()["pull_request"]["stale"] is False
        assert len(h.githost.pull_lookups) == 2
