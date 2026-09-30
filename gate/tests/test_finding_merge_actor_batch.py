"""F07-T45: append-only pull requests skip the strict up-to-date rebuild, and merge in batches
(testers 2026-09-27; the owner's ruling 2026-09-29).

Read from the record: in the 2026-09-27 hour twenty graph pull requests were opened and seven
merged in about forty-five minutes. Every merge, a fifteen-second append included, cost a whole
round: the actor updated the branch, the gate re-ran, the actor merged, and then the post-merge
job (about three minutes) held everything, because since F07-T33 nothing moves ``main`` under a
running post-merge job. The rebuild is the part an append does not need: an append adds one new
file under a target (``append_pr`` in ``api/opn_api/appends.py``, the only caller of the
``append/`` branch prefix), earns no attestation, and its tree is not attested; the post-merge job
classifies what it actually merged against ``merge^1`` with the pinned gate either way.

So the actor now merges the oldest green append *behind* main, together with every following
green, non-conflicting append in queue order, up to ``MAX_BATCH``, in one run; and one post-merge
run covers every merge that has no ``gate:`` commit yet (the graph's ``gate.yml``, tested in
``test_finding_postmerge_batch.py``). Building pull requests keep T31's barrier, T32's wakes and
T33's hold exactly: a batch never includes one, never passes an up-to-date one whose gate runs,
and never starts while a post-merge job has not committed.

The replay drives the shipped decision program through the host as ``test_finding_merge_actor_
wakes.py`` models it (late reads, wakes only when the host would send one, no cron). It was seen
red against the actor as it stood (``engineering/evidence/F07/task-45-red.txt``).
"""

from __future__ import annotations

import os
import stat
import subprocess
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from test_finding_merge_actor_wakes import (
    BOT_S,
    FAST_S,
    SLOW_S,
    T0,
    load_gate_doc,
    world,
)
from test_finding_merge_actor_workflow import (
    GATE_JOB,
    RULES,
    STEP9_JOB,
    check,
    load_doc,
    load_pick,
    pull,
)

NOW = T0 + timedelta(hours=1)


@pytest.fixture(scope="module")
def doc() -> dict[Any, Any]:
    return load_doc()


@pytest.fixture(scope="module")
def pick(doc: dict[Any, Any]) -> dict[str, Any]:
    return load_pick(doc)


@pytest.fixture(scope="module")
def gate_doc() -> dict[Any, Any]:
    return load_gate_doc()


def cap(pick: dict[str, Any]) -> int:
    """The batch cap, read from the program; 8 for the actor as it stood (which had none)."""
    return int(pick.get("MAX_BATCH", 8))


def green() -> list[dict[str, Any]]:
    return [check(GATE_JOB, "success"), check(STEP9_JOB, "skipped", id_=2)]


def red() -> list[dict[str, Any]]:
    return [check(GATE_JOB, "failure"), check(STEP9_JOB, "skipped", id_=2)]


def gating(minutes_ago: int = 1) -> list[dict[str, Any]]:
    stamp = (NOW - timedelta(minutes=minutes_ago)).isoformat().replace("+00:00", "Z")
    return [{**check(GATE_JOB, None), "started_at": stamp}, check(STEP9_JOB, None, id_=2)]


def shas(pulls: list[dict[str, Any]]) -> dict[int, str]:
    return {p["number"]: p["head"]["sha"] for p in pulls}


def decide(
    pick: dict[str, Any],
    pulls: list[dict[str, Any]],
    checks: dict[int, list[dict[str, Any]]],
    behind: dict[int, int] | int = 1,
    conflicts: dict[int, bool | None] | None = None,
    *,
    running: bool = False,
) -> tuple[Any, Any, str]:
    by_sha = {p["head"]["sha"]: p["number"] for p in pulls}
    got: tuple[Any, Any, str] = pick["decide"](
        pulls,
        RULES,
        lambda sha: checks[by_sha[sha]],
        lambda sha: behind if isinstance(behind, int) else behind[by_sha[sha]],
        lambda number: (conflicts or {}).get(number, False),
        now=NOW,
        postmerge_running=lambda: running,
    )
    return got


def batch(pulls: list[dict[str, Any]], *numbers: int) -> tuple[str, str, str]:
    of = shas(pulls)
    return " ".join(map(str, numbers)), " ".join(of[n] for n in numbers), "merge-batch"


# --- the replay ---------------------------------------------------------------------------------


def after_a_proof() -> dict[int, tuple[int, str, int]]:
    """A proof at second 5; six appends in the minute after it; a second building pull request."""
    out: dict[int, tuple[int, str, int]] = {5: (300, "submit/proof", SLOW_S)}
    for i in range(6):
        out[20 + 10 * i] = (301 + i, f"append/a{i}", FAST_S)
    out[90] = (307, "propose/next", SLOW_S)
    return out


def test_the_appends_queued_behind_a_proof_merge_in_one_round(
    pick: dict[str, Any], gate_doc: dict[Any, Any]
) -> None:
    """The proof holds the line (T31) and its post-merge job holds everything (T33). The six
    appends are green and behind when it commits; as it stood the actor then spent a whole round
    on each (update, gate, merge, post-merge job), six rounds in all. Now they go in one."""
    w = world(pick, gate_doc, after_a_proof())
    w.advance(3 * 3600)
    assert w.open == {}, f"left open: {sorted(w.open)}; runs: {w.log}"
    appends = range(301, 307)
    rounds = sorted({w.merged_at[n] for n in appends})
    assert len(rounds) == 1, f"the appends merged in {len(rounds)} rounds: {rounds}; {w.log}"
    # one round: after the proof's bot commit lands, the next wake merges them all
    assert rounds[0] <= w.merged_at[300] + BOT_S + 60, (w.merged_at, w.log)
    # ...in queue order, and before the building pull request that came after them (FIFO)
    assert [a[2] for a in w.log if a[1] == "merge-batch"] == ["301 302 303 304 305 306"], w.log
    assert w.merged_at[307] > rounds[0]


def test_a_batch_never_moves_main_under_a_post_merge_job(
    pick: dict[str, Any], gate_doc: dict[Any, Any]
) -> None:
    """T33 still holds across the whole replay: every act found no committing job in flight
    (``World.act`` asserts it), and only the last merge of a batch has a job that commits."""
    w = world(pick, gate_doc, after_a_proof())
    w.advance(3 * 3600)
    committing = [r for r in w.push_runs if r.commits]
    batches = [a for a in w.log if a[1] in ("merge", "merge-batch")]
    assert len(committing) == len(batches), (committing, batches)


def test_a_steady_stream_of_appends_drains_faster_than_one_per_round(
    pick: dict[str, Any], gate_doc: dict[Any, Any]
) -> None:
    """The 2026-09-27 shape: twenty submissions in fifteen minutes, three in four appends. As it
    stood every one cost a post-merge job; now a round carries every append that is green."""
    arrivals = {}
    for i in range(20):
        building = i % 4 == 0
        ref = f"submit/p{i}" if building else f"append/a{i}"
        arrivals[5 + 45 * i] = (400 + i, ref, SLOW_S if building else FAST_S)
    w = world(pick, gate_doc, arrivals)
    w.advance(4 * 3600)
    assert w.open == {}, f"frozen with {sorted(w.open)} open; last runs: {w.log[-6:]}"
    committing = [r for r in w.push_runs if r.commits]
    assert len(committing) <= 12, f"{len(committing)} post-merge jobs for 20 merges: {w.log}"


# --- the rules one at a time --------------------------------------------------------------------


def test_a_batch_takes_every_green_append_up_to_the_first_green_building_one(
    pick: dict[str, Any],
) -> None:
    pulls = [pull(1, "append/a"), pull(2, "append/b"), pull(3, "submit/c"), pull(4, "append/d")]
    checks = {n: green() for n in (1, 2, 3, 4)}
    assert decide(pick, pulls, checks) == batch(pulls, 1, 2)


def test_a_batch_never_includes_a_building_pull_request(pick: dict[str, Any]) -> None:
    for ref in ("submit/p", "propose/v"):
        pulls = [pull(1, "append/a"), pull(2, ref), pull(3, "append/c")]
        got = decide(pick, pulls, {n: green() for n in (1, 2, 3)})
        assert got == batch(pulls, 1), (ref, got)
    # a building one at the head of the queue is acted on alone, exactly as before
    pulls = [pull(1, "submit/p"), pull(2, "append/b")]
    got = decide(pick, pulls, {1: green(), 2: green()})
    assert got == (1, pulls[0]["head"]["sha"], "update")
    got = decide(pick, pulls, {1: green(), 2: green()}, behind=0)
    assert got == (1, pulls[0]["head"]["sha"], "merge")


def test_a_batch_stops_at_the_cap(pick: dict[str, Any]) -> None:
    n = cap(pick) + 4
    pulls = [pull(10 + i, f"append/a{i}") for i in range(n)]
    got = decide(pick, pulls, {10 + i: green() for i in range(n)})
    assert got == batch(pulls, *range(10, 10 + cap(pick)))
    assert 2 <= cap(pick) <= 20, "a cap that keeps a post-merge job's work bounded"


def test_no_batch_while_a_post_merge_job_runs(pick: dict[str, Any]) -> None:
    pulls = [pull(1, "append/a"), pull(2, "append/b")]
    for behind in (0, 1):
        got = decide(pick, pulls, {1: green(), 2: green()}, behind, running=True)
        assert got == ("", "", "hold"), (behind, got)


def test_an_up_to_date_gating_pull_request_still_holds_the_line(pick: dict[str, Any]) -> None:
    """T31 at the head of the queue: nothing is merged past it, a batch included."""
    pulls = [pull(1, "submit/p"), pull(2, "append/a"), pull(3, "append/b")]
    got = decide(pick, pulls, {1: gating(), 2: green(), 3: green()}, {1: 0, 2: 1, 3: 1})
    assert got == ("", "", "hold")


def test_a_batch_ends_at_an_up_to_date_gating_pull_request(pick: dict[str, Any]) -> None:
    """T31 inside the queue: the appends ahead of it go, the ones behind it wait for it."""
    pulls = [pull(1, "append/a"), pull(2, "submit/p"), pull(3, "append/b")]
    got = decide(pick, pulls, {1: green(), 2: gating(), 3: green()}, {1: 1, 2: 0, 3: 1})
    assert got == batch(pulls, 1)
    # a pending append that is up to date is a barrier too, as it is at the head
    pulls = [pull(1, "append/a"), pull(2, "append/p"), pull(3, "append/b")]
    got = decide(pick, pulls, {1: green(), 2: gating(), 3: green()}, {1: 1, 2: 0, 3: 1})
    assert got == batch(pulls, 1)


def test_red_behind_pending_and_conflicting_appends_are_passed_over(pick: dict[str, Any]) -> None:
    pulls = [pull(1, "append/a"), pull(2, "append/r"), pull(3, "append/p"), pull(4, "append/c")]
    pulls.append(pull(5, "append/e"))
    checks = {1: green(), 2: red(), 3: gating(), 4: green(), 5: green()}
    got = decide(pick, pulls, checks, 1, {4: True})
    assert got == batch(pulls, 1, 5)


def test_a_batch_ends_where_the_host_is_still_computing_mergeability(pick: dict[str, Any]) -> None:
    """T32's rule inside the batch: an unknown answer is never acted on; what is before it goes."""
    pulls = [pull(1, "append/a"), pull(2, "append/b"), pull(3, "append/c")]
    got = decide(pick, pulls, {n: green() for n in (1, 2, 3)}, 1, {2: None})
    assert got == batch(pulls, 1)


def test_one_up_to_date_append_is_merged_as_before(pick: dict[str, Any]) -> None:
    pulls = [pull(1, "append/a")]
    got = decide(pick, pulls, {1: green()}, behind=0)
    assert got == (1, pulls[0]["head"]["sha"], "merge")


# --- the acting step, run as it stands with a fake host ----------------------------------------


FAKE_GH = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$GH_LOG"
if [ -n "${GH_FAIL:-}" ] && printf '%s' "$*" | grep -q -- "$GH_FAIL"; then exit 1; fi
exit 0
"""


def act_step(doc: dict[Any, Any]) -> str:
    (act,) = [s for s in doc["jobs"]["merge"]["steps"] if s.get("name", "").startswith("Act")]
    return str(act["run"])


def run_act(
    doc: dict[Any, Any], tmp_path: Path, number: str, sha: str, action: str, *, fail: str = ""
) -> tuple[int, list[str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    gh = bin_dir / "gh"
    gh.write_text(FAKE_GH, encoding="utf-8")
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    log = tmp_path / "gh.log"
    log.write_text("", encoding="utf-8")
    env = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "GH_LOG": str(log),
        "GH_FAIL": fail,
        "GH_TOKEN": "fake",  # a fake, so the act is not a dry run
        "REPO": "owner/graph",
        "NUMBER": number,
        "SHA": sha,
        "ACTION": action,
    }
    proc = subprocess.run(
        ["bash", "-c", act_step(doc)], capture_output=True, text=True, check=False, env=env
    )
    return proc.returncode, [line for line in log.read_text().splitlines() if line]


def test_the_act_merges_a_batch_in_order_each_at_the_head_it_saw(
    doc: dict[Any, Any], tmp_path: Path
) -> None:
    code, calls = run_act(doc, tmp_path, "5 6 7", "a5 a6 a7", "merge-batch")
    assert code == 0, calls
    assert calls == [
        f"api -X PUT repos/owner/graph/pulls/{n}/merge -f sha=a{n} -f merge_method=merge"
        for n in (5, 6, 7)
    ]


def test_a_failed_merge_in_a_batch_stops_there_and_the_rest_wait(
    doc: dict[Any, Any], tmp_path: Path
) -> None:
    """C7: a conflict that appeared since the decision refuses one merge; nothing after it is
    tried. The merges that landed each start a post-merge job, whose last step wakes the actor."""
    code, calls = run_act(doc, tmp_path, "5 6 7", "a5 a6 a7", "merge-batch", fail="pulls/6/merge")
    assert calls == [
        "api -X PUT repos/owner/graph/pulls/5/merge -f sha=a5 -f merge_method=merge",
        "api -X PUT repos/owner/graph/pulls/6/merge -f sha=a6 -f merge_method=merge",
    ]
    assert code == 0


def test_a_refused_first_merge_falls_back_to_the_update_it_had_before(
    doc: dict[Any, Any], tmp_path: Path
) -> None:
    """If the host ever refuses an append behind main (the token's bypass withdrawn), the actor
    must not fail the same way on every run: it updates the branch as it did before F07-T45, the
    gate re-runs and wakes it, and the append merges up to date next time."""
    code, calls = run_act(doc, tmp_path, "5 6", "a5 a6", "merge-batch", fail="pulls/5/merge")
    assert calls == [
        "api -X PUT repos/owner/graph/pulls/5/merge -f sha=a5 -f merge_method=merge",
        "api -X PUT repos/owner/graph/pulls/5/update-branch -f expected_head_sha=a5",
    ]
    assert code == 0
    # and if the update fails too, the run fails, and the rewake job starts another
    code, calls = run_act(doc, tmp_path, "5 6", "a5 a6", "merge-batch", fail="pulls/5/")
    assert code != 0 and len(calls) == 2


def test_single_actions_are_as_before(doc: dict[Any, Any], tmp_path: Path) -> None:
    code, calls = run_act(doc, tmp_path, "5", "a5", "merge")
    assert (code, calls) == (
        0,
        ["api -X PUT repos/owner/graph/pulls/5/merge -f sha=a5 -f merge_method=merge"],
    )
    code, calls = run_act(doc, tmp_path, "5", "a5", "update")
    assert (code, calls) == (
        0,
        ["api -X PUT repos/owner/graph/pulls/5/update-branch -f expected_head_sha=a5"],
    )


def test_the_pick_output_carries_a_batch_through_number_and_sha(doc: dict[Any, Any]) -> None:
    """``number`` and ``sha`` hold the batch's numbers and heads, space-separated and aligned;
    the acting step is still skipped when ``number`` is empty (a hold, or nothing to do)."""
    (step,) = [s for s in doc["jobs"]["merge"]["steps"] if s.get("id") == "pick"]
    assert 'out.write(f"number={number}\\nsha={sha}\\naction={action}\\n")' in step["run"]
    assert "merge-batch" in act_step(doc)
