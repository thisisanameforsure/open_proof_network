"""F07-T46: a pull request whose branch moved under the host's record is passed over, not held for.

The 2026-09-29 tester run's queue froze at 04:04Z on 2026-09-30 with fifteen green pull requests
open, and stayed frozen through nine actor runs (``engineering/evidence/F07/task-46.txt``). Read
from the record:

1. Run 1094 picked #306 (a ``submit/`` proof, green, behind main) and updated its branch at
   04:09:38Z; the push landed (``submit/01M3QNGQ...`` moved to ``d74ba77c``, a merge of main into
   the proof commit ``641260d5``).
2. The host never synchronised the pull request: at 10:12Z it still reported head ``641260d5``,
   ``updated_at`` 22:45:44Z, no gate run on ``d74ba77c`` and ``mergeable: null``; an update of
   the branch through the API was refused with "expected head sha didn't match current head ref"
   for either commit.
3. Every run since (1095 to 1101) read the old head's checks as green and its mergeability as
   unknown, printed "#306 is green; the host is still computing whether it conflicts: holding"
   for the whole settle cap, and ended with ``hold``. Fourteen green pull requests waited behind
   it for six hours and nothing was red.

T32's hold on an unknown mergeability is right while the host is computing; it is wrong when the
host's record of the pull request is stale. The fact that tells the two apart is on the host: the
branch's tip. A pull request whose recorded head is not its branch's tip cannot be merged at that
head (the merge names the head it saw) and its checks are not the branch's; it is passed over with
a notice, as a conflict is, and the queue moves. A branch that no longer exists is the same case.
"""

from __future__ import annotations

from typing import Any

import pytest
from test_finding_merge_actor_wakes import NOW
from test_finding_merge_actor_workflow import (
    GREEN,
    RULES,
    load_doc,
    load_pick,
    pull,
)

MOVED = "d74ba77c022fe6603d29118d393407cab4db8595"


@pytest.fixture(scope="module")
def doc() -> dict[Any, Any]:
    return load_doc()


@pytest.fixture(scope="module")
def pick(doc: dict[Any, Any]) -> dict[str, Any]:
    return load_pick(doc)


def sha(pr: dict[str, Any]) -> str:
    return str(pr["head"]["sha"])


def tips(pulls: list[dict[str, Any]], **moved: str) -> Any:
    """The branch tips the host would report: each pull request's own head, except the ones named
    (``submit_x=<tip>``; an empty tip is a branch that no longer exists)."""
    by_ref = {pr["head"]["ref"]: sha(pr) for pr in pulls}
    by_ref.update({k.replace("_", "/", 1): v for k, v in moved.items()})
    return lambda ref: by_ref[ref]


def decide(
    pick: dict[str, Any],
    pulls: list[dict[str, Any]],
    *,
    conflicts: dict[int, bool | None],
    tip_of: Any,
    behind: int = 1,
) -> tuple[Any, Any, str]:
    got: tuple[Any, Any, str] = pick["decide"](
        pulls,
        RULES,
        lambda _sha: GREEN,
        lambda _sha: behind,
        lambda number: conflicts.get(number, False),
        now=NOW,
        tip_of=tip_of,
    )
    return got


def the_morning_of_306() -> list[dict[str, Any]]:
    """#306 to #320 as the host listed them at 10:00Z: all green, #306 first, its mergeability
    unknown and its branch one commit past the head the host records."""
    return [pull(306, "submit/01M3QNGQ")] + [pull(n, f"submit/{n:08d}") for n in range(307, 321)]


def test_the_morning_of_306_moves_past_the_stale_head(pick: dict[str, Any]) -> None:
    pulls = the_morning_of_306()
    got = decide(pick, pulls, conflicts={306: None}, tip_of=tips(pulls, submit_01M3QNGQ=MOVED))
    assert got == (307, sha(pulls[1]), "update"), got


def test_a_stale_head_is_passed_over_even_if_the_host_calls_it_clean(pick: dict[str, Any]) -> None:
    """The merge names the head it saw, so acting at a stale head is refused by the host every
    time (C7); the rule keys on the branch, not on the mergeability flag."""
    pulls = [pull(306, "submit/a"), pull(307, "submit/b")]
    got = decide(pick, pulls, conflicts={306: False}, tip_of=tips(pulls, submit_a=MOVED))
    assert got == (307, sha(pulls[1]), "update"), got


def test_a_branch_that_no_longer_exists_is_passed_over(pick: dict[str, Any]) -> None:
    pulls = [pull(306, "submit/a"), pull(307, "submit/b")]
    got = decide(pick, pulls, conflicts={306: None}, tip_of=tips(pulls, submit_a=""))
    assert got == (307, sha(pulls[1]), "update"), got


def test_a_head_the_host_still_computes_is_held_for_as_before(pick: dict[str, Any]) -> None:
    """T32 stands: the branch is where the record says, so the host is computing, not stale."""
    pulls = [pull(306, "submit/a"), pull(307, "submit/b")]
    got = decide(pick, pulls, conflicts={306: None}, tip_of=tips(pulls))
    assert got == ("", "", "hold"), got


def test_a_stale_append_never_ends_a_batch(pick: dict[str, Any]) -> None:
    """In a batch a stale append is passed over like a conflicting one, and the appends after it
    still go (F07-T45)."""
    pulls = [pull(1, "append/a"), pull(2, "append/b"), pull(3, "append/c")]
    got = decide(pick, pulls, conflicts={2: None}, tip_of=tips(pulls, append_b=MOVED))
    assert got == ("1 3", f"{sha(pulls[0])} {sha(pulls[2])}", "merge-batch"), got


def test_without_a_tip_reader_nothing_changes(pick: dict[str, Any]) -> None:
    """Every older test calls ``decide`` without ``tip_of``; the rule is off, and an unknown
    mergeability is still a hold."""
    pulls = [pull(306, "submit/a")]
    got = pick["decide"](pulls, RULES, lambda _s: GREEN, lambda _s: 1, lambda _n: None, now=NOW)
    assert got == ("", "", "hold"), got


def test_the_workflow_reads_each_branch_tip_and_survives_a_missing_one(doc: dict[Any, Any]) -> None:
    (step,) = [s for s in doc["jobs"]["merge"]["steps"] if s.get("id") == "pick"]
    script = str(step["run"])
    assert "git/ref/heads/" in script, "the tip of a branch is read from the host's refs"
    assert "tip_of=" in script, "and handed to the decision"
    # a branch that is gone is a 404: the run must not fail on it, since a failed run wakes nothing
    assert "CalledProcessError" in script
