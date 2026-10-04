"""F07-T68 (audit 2026-10-04): every anonymous read that spends the App's installation budget is
held at the reserve and cached.

F07-T47 held two reads, a pull request's live state and the open listing, once the budget the
host last reported is at or below ``host_budget_reserve``. Four more reads spent the same budget
with no hold and, in three cases, no cache, so a poller of an anonymous route could still drain
what the writes are kept for:

- the MCP adapter's directory listing (``reads.listing``, the Contents API), on every
  ``get_target`` and every derived node bundle;
- ``GET /precheck/<id>`` advancing a running job (``find_run``) on every poll;
- ``gate_verdict``'s artifact read, whose failures were not cached, so every read of a refused
  pull request asked again;
- ``_annex_unrendered``'s two listings, at commits that never change.

The rules. With the budget held each makes no host call and answers as the held paths do: the
last thing it read, or the read's own "could not say" shape (an MCP ``host-budget-exhausted``
error, an unadvanced job with ``Retry-After``, no verdict, the pull request unchanged). With the
budget fine, each is cached: a listing per (path, head), a job's poll at most once per
``precheck_poll_min_s``, a verdict failure for ``verdict_retry_s``, an annex comparison for good.
"""

from __future__ import annotations

import time
from typing import Any

import pytest
from api_fakes import PROOF_PREFIX, TUTORIAL_NODE, TUTORIAL_PROOF, Harness
from test_finding_host_budget import spent
from test_pending_submissions import record

from opn_api import pending
from opn_api.githost import GATE_WORKFLOW
from opn_api.mcp import reads
from opn_api.mcp.calls import ToolError

APPROACHES = "targets/propositional/approaches"
HEAD = "f" * 40
MERGE = "e" * 40
RUN_ID = 77


def hold(h: Harness) -> None:
    """The budget at 150 of 5000 against the default reserve of 200, reset twenty minutes on."""
    h.githost.budget_seen = spent(h, remaining=150, ahead_s=1200)


def listings(h: Harness) -> list[str]:
    """Every Contents-API listing the fake host answered (``list_dir`` records ``path/``)."""
    return [p for p, _ in h.githost.fetches if p.endswith("/")]


# --- the MCP adapter's listing -------------------------------------------------------------------


def test_a_held_listing_with_nothing_cached_spends_nothing_and_says_why(harness: Harness) -> None:
    hold(harness)
    with pytest.raises(ToolError) as raised:
        reads.listing(harness.context, APPROACHES)
    assert listings(harness) == []
    assert raised.value.doc["error"] == "host-budget-exhausted"
    assert raised.value.doc["source"] == "graph"
    assert "reserve" in raised.value.doc["message"]


def test_a_listing_is_read_once_per_head_and_served_from_cache_when_held(
    harness: Harness,
) -> None:
    harness.githost.head = HEAD
    harness.githost.files[f"{APPROACHES}/a.yaml"] = b"x: 1\n"
    first = reads.listing(harness.context, APPROACHES)
    again = reads.listing(harness.context, APPROACHES)
    assert first == again == ["a.yaml"]
    assert len(listings(harness)) == 1

    hold(harness)
    assert reads.listing(harness.context, APPROACHES) == ["a.yaml"]
    assert len(listings(harness)) == 1

    harness.githost.budget_seen = None
    harness.githost.head = "1" * 40  # main moved: the listing is read again at the new head
    harness.context.head_checked_at = time.monotonic() - (harness.settings.frontier_max_stale_s + 1)
    reads.listing(harness.context, APPROACHES)
    assert len(listings(harness)) == 2


# --- GET /precheck/<id> --------------------------------------------------------------------------


def running_job(h: Harness) -> tuple[str, list[str]]:
    """A tutorial precheck whose run has started and not finished; and the branches every
    ``find_run`` was asked about from now on."""
    created = h.client.post(
        "/precheck",
        json={
            "node_id": TUTORIAL_NODE,
            "bundle": {f"{PROOF_PREFIX}{TUTORIAL_NODE}/Proof.lean": TUTORIAL_PROOF},
        },
    )
    assert created.status_code == 202, created.text
    job_id = str(created.json()["id"])
    h.githost.start_run(f"job/{job_id}")
    asked: list[str] = []
    real = h.githost.find_run

    def counting(repo: str, workflow: str, *, branch: str) -> Any:
        asked.append(branch)
        return real(repo, workflow, branch=branch)

    h.githost.find_run = counting  # type: ignore[method-assign]
    return job_id, asked


def test_a_held_precheck_poll_spends_nothing_and_carries_retry_after(harness: Harness) -> None:
    job_id, asked = running_job(harness)
    hold(harness)
    r = harness.client.get(f"/precheck/{job_id}")
    assert r.status_code == 200, r.text
    assert r.json()["state"] == "queued"  # unadvanced: what the record says
    assert r.headers.get("Retry-After") == "1200"
    assert asked == []


def test_a_precheck_is_polled_at_most_once_per_interval(harness: Harness) -> None:
    job_id, asked = running_job(harness)
    for _ in range(5):
        r = harness.client.get(f"/precheck/{job_id}")
        assert r.status_code == 200, r.text
    assert r.json()["state"] == "running"
    assert len(asked) == 1

    polls = harness.context.precheck_polls
    polls[job_id] -= harness.settings.precheck_poll_min_s + 1  # the interval has passed
    harness.client.get(f"/precheck/{job_id}")
    assert len(asked) == 2


# --- gate_verdict -------------------------------------------------------------------------------


def failed_pull() -> dict[str, Any]:
    return {
        "waiting_on": "gate-failed",
        "head_sha": HEAD,
        "runs": [{"name": GATE_WORKFLOW, "url": f"https://github.com/o/g/actions/runs/{RUN_ID}"}],
    }


def test_a_verdict_read_that_failed_is_not_retried_inside_the_window(harness: Harness) -> None:
    harness.githost.artifact_failure = "GET /repos/o/g/actions/runs/77/artifacts returned 502"
    for _ in range(4):
        assert pending.gate_verdict(harness.context, 5, failed_pull()) is None
    assert harness.githost.artifact_reads == 1

    harness.githost.artifact_failure = ""
    failures = harness.context.verdict_failures
    failures[HEAD] -= harness.settings.verdict_retry_s + 1
    pending.gate_verdict(harness.context, 5, failed_pull())
    assert harness.githost.artifact_reads == 2


def test_a_held_verdict_read_spends_nothing(harness: Harness) -> None:
    hold(harness)
    assert pending.gate_verdict(harness.context, 5, failed_pull()) is None
    assert harness.githost.artifact_reads == 0


# --- _annex_unrendered ---------------------------------------------------------------------------


def merged_annex() -> tuple[Any, dict[str, Any]]:
    found = record(4, kind="annex", node_id=TUTORIAL_NODE)
    return found, {"merged": True, "merge_commit_sha": MERGE, "waiting_on": None}


def test_the_annex_comparison_is_made_once_per_commit_pair(harness: Harness) -> None:
    found, pull = merged_annex()
    for _ in range(3):
        assert pending.waiting_on_products(harness.context, found, pull) == pull
    assert len(listings(harness)) == 2  # the merge commit's listing and the rendered one's


def test_a_held_annex_comparison_spends_nothing_and_changes_nothing(harness: Harness) -> None:
    found, pull = merged_annex()
    hold(harness)
    assert pending.waiting_on_products(harness.context, found, pull) == pull
    assert listings(harness) == []
