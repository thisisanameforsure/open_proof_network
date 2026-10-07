"""F23-AC9 (R8; D-32 v3.33): the merge actor and the steward admission switch.

Under ``steward_admission: reviewed`` the service opens a steward record on a ``curate/`` branch,
which a curator merges and the record names (``admitted_by``). Under ``open`` it opens an
``append/`` branch, which merges unattended like any append. The actor reads no ``policy.json``:
the switch reaches it as the branch prefix the service chose, and the gate refuses a record whose
``admitted_by`` disagrees with the policy in the merge's parent tree (``test_steward_v2.py``), so an
``append/`` record under ``reviewed`` cannot merge either.

The decision program is the heredoc the graph's ``merge.yml`` writes to ``pick.py``, run as it
stands (``test_finding_merge_actor_workflow``); skipped where the graph is not checked out.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from test_finding_merge_actor_workflow import (
    GATE_JOB,
    RULES,
    STEP9_JOB,
    check,
    load_doc,
    load_pick,
    pull,
)

NOW = datetime(2026, 10, 7, 12, tzinfo=UTC)
STEWARD_FILE = "targets/erdos-69/stewards/1.yaml"


@pytest.fixture(scope="module")
def pick() -> dict[str, Any]:
    return load_pick(load_doc())


def green() -> list[dict[str, Any]]:
    return [check(GATE_JOB, "success"), check(STEP9_JOB, "skipped", id_=2)]


def decide(pick: dict[str, Any], pulls: list[dict[str, Any]]) -> list[tuple[int, str, str]]:
    decided: list[tuple[int, str, str]] = pick["decide_lanes"](
        pulls,
        RULES,
        lambda _sha: green(),
        lambda _sha: 0,
        lambda _number: False,
        now=NOW,
        lane_of=lambda _number: "erdos-69",
    )
    return [d for d in decided if d[2] != "wait"]


def test_a_curate_branch_is_never_a_candidate(pick: dict[str, Any]) -> None:
    """Reviewed: the service's ``curate/`` steward branch is left to a curator."""
    pulls = [pull(500, "curate/steward-erdos-69-alice"), pull(501, "curate/x")]
    assert pick["candidates"](pulls) == []
    assert not "curate/".startswith(tuple(pick["SERVICE_PREFIXES"]))


def test_a_green_curate_branch_is_never_merged(pick: dict[str, Any]) -> None:
    """Even green, up to date and alone in its lane, nothing is decided for it."""
    assert decide(pick, [pull(500, "curate/steward-erdos-69-alice")]) == []


def test_a_steward_append_merges_like_any_append(pick: dict[str, Any]) -> None:
    """Open: the record arrives on ``append/`` and is merged the way a postmortem is."""
    steward_pr = pull(502, "append/steward-erdos-69-alice")
    other_append = pull(503, "append/01M3W7JH")
    alone = decide(pick, [steward_pr])
    assert [(n, a) for n, _s, a in alone] == [(502, "merge")]
    with_curate = decide(pick, [pull(500, "curate/steward-erdos-69-bob"), steward_pr])
    assert [n for n, _s, _a in with_curate] == [502]
    beside = decide(pick, [steward_pr, other_append])
    assert {n for n, _s, _a in beside} == {502, 503}
    assert all(a.startswith("merge") for _n, _s, a in beside)


def test_the_lane_of_a_steward_record_is_its_target(pick: dict[str, Any]) -> None:
    assert pick["lane_of_paths"]([STEWARD_FILE]) == "erdos-69"
