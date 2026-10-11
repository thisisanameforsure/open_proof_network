"""F05-T18: the queue position the service reports is the merge actor's own order, not a guess.

``GET /submissions/<id>`` and ``GET /submissions.json`` say where a pull request stands in the
merge queue (the owner, 2026-10-01: "Yes, show queue positions"). The order is decided by one
function in one place, ``candidates`` in the graph's ``.github/workflows/merge.yml``: open,
non-draft pull requests whose head is in the repository, against ``main``, on a branch the service
opened, lowest number first. The service restates that rule over the host's open listing
(``opn_api.pending.queue_order``); this test runs the workflow's own function and the service's on
the same listing, in the host's own JSON shape, and requires the same answer. Like every test of
the actor it reads the workflow from the graph checkout beside this repository and is skipped
where there is none.
"""

from __future__ import annotations

import inspect
import itertools
import random
from typing import Any

import pytest
from test_finding_merge_actor_workflow import REPO, load_doc, load_pick

from opn_api import githost, pending


@pytest.fixture(scope="module")
def pick() -> dict[str, Any]:
    return load_pick(load_doc())


def host_entry(
    number: int,
    ref: str,
    *,
    draft: bool = False,
    base: str = "main",
    head_repo: str | None = REPO,
    sha: str | None = None,
) -> dict[str, Any]:
    """One entry of ``GET /repos/{repo}/pulls?state=open`` (shape read from the graph's own
    listing on 2026-10-01). ``head_repo`` ``None`` is a fork that has been deleted."""
    return {
        "number": number,
        "html_url": f"https://github.com/{REPO}/pull/{number}",
        "draft": draft,
        "head": {
            "ref": ref,
            "sha": sha or f"{number:040x}",
            "repo": {"full_name": head_repo} if head_repo is not None else None,
        },
        "base": {"ref": base, "repo": {"full_name": REPO}},
    }


def service_order(pulls: list[dict[str, Any]]) -> list[int]:
    listed = {pr["number"]: githost.open_pull_request_of(pr) for pr in pulls}
    return pending.queue_order(listed)


def actor_order(pick: dict[str, Any], pulls: list[dict[str, Any]]) -> list[int]:
    return [number for number, _sha in pick["candidates"](pulls)]


def test_the_prefixes_are_the_actors(pick: dict[str, Any]) -> None:
    assert tuple(pick["SERVICE_PREFIXES"]) == pending.SERVICE_PREFIXES
    assert pick["APPEND_PREFIX"] in pending.SERVICE_PREFIXES


def test_the_order_is_the_actors_on_a_mixed_listing(pick: dict[str, Any]) -> None:
    pulls = [
        host_entry(360, "submit/01M3W8YV"),
        host_entry(358, "append/01M3W7JH"),
        host_entry(359, "submit/01M3W8PN"),
        host_entry(361, "propose/01M3W9"),
        host_entry(340, "append/a-draft", draft=True),
        host_entry(341, "curator/erdos-69-defs"),
        host_entry(342, "submit/from-a-fork", head_repo="someone/fork"),
        host_entry(343, "submit/fork-deleted", head_repo=None),
        host_entry(344, "append/against-next", base="next"),
        host_entry(12, "submitted/not-the-prefix"),
    ]
    assert actor_order(pick, pulls) == [358, 359, 360, 361]
    assert service_order(pulls) == actor_order(pick, pulls)


def test_the_order_is_the_actors_whatever_the_listing_order(pick: dict[str, Any]) -> None:
    """The host lists newest first; nothing may depend on that. Every combination of the four
    things ``candidates`` reads, shuffled."""
    rng = random.Random(20261001)  # noqa: S311 — a fixed shuffle, not a secret
    refs = ("submit/a", "append/b", "propose/c", "feature/d", "")
    combos = list(itertools.product(refs, (False, True), ("main", "dev"), (REPO, "x/fork", None)))
    pulls = [
        host_entry(number, ref, draft=draft, base=base, head_repo=repo)
        for number, (ref, draft, base, repo) in enumerate(combos, start=1)
    ]
    for _ in range(20):
        rng.shuffle(pulls)
        assert service_order(pulls) == actor_order(pick, pulls)
    assert len(service_order(pulls)) == 3  # one per service prefix: non-draft, main, same repo


def test_decide_takes_the_first_green_in_that_order(pick: dict[str, Any]) -> None:
    """What ``order`` in the answer says: position is the order of consideration. The actor
    passes over a red one, so the second in line can merge first; that is why the answer calls a
    position an upper bound."""
    from test_finding_merge_actor_workflow import GREEN, RULES  # noqa: PLC0415

    pulls = [host_entry(5, "submit/red"), host_entry(6, "submit/green")]
    assert service_order(pulls) == [5, 6]
    red = [{**run, "conclusion": "failure"} for run in GREEN]
    decide = pick["decide"]
    # F07-T46 gave ``decide`` the branch tips; a checkout of the graph from before it has none
    tips = {pr["head"]["ref"]: pr["head"]["sha"] for pr in pulls}
    extra = {"tip_of": tips.__getitem__} if "tip_of" in inspect.signature(decide).parameters else {}
    number, _sha, action = decide(
        pulls,
        RULES,
        lambda sha: red if sha == pulls[0]["head"]["sha"] else GREEN,
        lambda _sha: 0,
        **extra,
    )[:3]
    assert (number, action) == (6, "merge")
    assert "passes over" in pending.QUEUE_ORDER and "upper bound" in pending.QUEUE_ORDER
