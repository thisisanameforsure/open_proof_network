"""F07-T32: the merge actor never stops with work waiting (testers 2026-09-23, finding 1).

On 2026-09-23 the queue froze twice with green pull requests waiting, and nothing a person could
see was red. Read from the record (``engineering/evidence/F07/task-32.txt``):

1. #148's gate check completed at 15:07:07 and its run at 15:07:18; the actor woken by that run
   read the check runs at 15:07:26, saw them pending, and held. Its own program run by hand at
   15:13 answered ``merge #148``. The host's check-run view lags the check.
2. A hold ends the run, and only the completion of *another* run wakes the actor again; the one
   it held for had already completed, so nothing did. The workflow's comment said "a hold here is
   always woken".
3. The post-merge run of #147 finished its jobs at 14:56:10 and was reported ``in_progress`` until
   15:04:19, so ``postmerge_running`` (which read the run's status) held eight times.
4. ``concurrency: merge`` keeps one pending run and cancels the rest: 5 of 183 wakes were dropped.
5. The hourly backstop fired at 00:43, 06:06, 11:51 and 17:15: a hope, as its comment says.
6. At 17:48 and 17:51 the actor chose #150 for an update while the host was still computing its
   mergeability (``mergeable: null``) although it conflicted with main; the update failed, the
   run failed, and a failed run wakes nothing. Frozen from 17:51.

The existing replay (``test_finding_merge_actor_queue.py``) ran the actor every fifteen seconds
and read every status exactly, which is why none of this showed. The world below wakes the actor
only when the host would, reads statuses as late as the host reports them, keeps one pending run
as the concurrency group does, and has no cron at all.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import yaml
from test_finding_merge_actor_workflow import (
    GATE_JOB,
    GRAPH_REPO,
    REFS,
    RULES,
    STEP9_JOB,
    check,
    load_doc,
    load_pick,
    pull,
)

from opn_gate import config

T0 = datetime(2026, 9, 23, 14, 44, tzinfo=UTC)
#: Seconds, from the record: a Mathlib gate round, an append's, the post-merge job, the lag of the
#: check-run view behind the check (>= 19 s on #148), and of a push run's status behind its jobs
#: (8 min 9 s on #147's post-merge run).
SLOW_S, FAST_S, BOT_S, CHECK_LAG_S, RUN_LAG_S = 180, 20, 150, 30, 489
WAKE_S, TICK_S = 5, 5


def load_gate_doc() -> dict[Any, Any]:
    """The graph's gate workflow, from the same refs as the actor's."""
    env = config.child_environment(drop=config.GIT_REPO_VARIABLES)
    for ref in REFS:
        proc = subprocess.run(
            ["git", "-C", str(GRAPH_REPO), "show", f"{ref}:.github/workflows/gate.yml"],
            capture_output=True, text=True, check=False, env=env,
        )  # fmt: skip
        if proc.returncode == 0:
            loaded: dict[Any, Any] = yaml.safe_load(proc.stdout)
            return loaded
    pytest.skip("no gate.yml on the graph refs")


@pytest.fixture(scope="module")
def doc() -> dict[Any, Any]:
    return load_doc()


@pytest.fixture(scope="module")
def pick(doc: dict[Any, Any]) -> dict[str, Any]:
    return load_pick(doc)


@pytest.fixture(scope="module")
def gate_doc() -> dict[Any, Any]:
    return load_gate_doc()


def postmerge_wakes_the_actor(gate_doc: dict[Any, Any]) -> bool:
    steps = gate_doc["jobs"]["postmerge"]["steps"]
    return any("gh workflow run merge.yml" in str(step.get("run", "")) for step in steps)


@dataclass
class Pr:
    number: int
    ref: str
    gate_s: int
    based_on: int
    gate_done: int


@dataclass
class PushRun:
    id: int
    jobs_done: int  # the bot commit lands and the job ends
    reported_done: int  # the host says the run completed


@dataclass
class World:
    """The host as the actor sees it: late, and only when it is woken."""

    pick: dict[str, Any]
    dispatch_after_postmerge: bool
    now: int = 0
    main: int = 0
    open: dict[int, Pr] = field(default_factory=dict)
    arrivals: dict[int, tuple[int, str, int]] = field(default_factory=dict)
    push_runs: list[PushRun] = field(default_factory=list)
    wakes: list[int] = field(default_factory=list)
    running: bool = False
    pending: bool = False
    merged_at: dict[int, int] = field(default_factory=dict)
    log: list[tuple[int, str, str]] = field(default_factory=list)

    # --- what the host reports -------------------------------------------------------------------

    def sha(self, pr: Pr) -> str:
        return f"{pr.number:036d}{pr.based_on:04d}"

    def checks_of(self, sha: str) -> list[dict[str, Any]]:
        pr = next(p for p in self.open.values() if self.sha(p) == sha)
        seen_done = self.now >= pr.gate_done + CHECK_LAG_S
        started = T0 + timedelta(seconds=pr.gate_done - pr.gate_s)
        stamp = started.isoformat().replace("+00:00", "Z")
        gate = {**check(GATE_JOB, "success" if seen_done else None), "started_at": stamp}
        return [gate, check(STEP9_JOB, "skipped" if seen_done else None, id_=2)]

    def pulls(self) -> list[dict[str, Any]]:
        out = []
        for pr in self.open.values():
            entry = pull(pr.number, pr.ref)
            entry["head"]["sha"] = self.sha(pr)
            out.append(entry)
        return out

    def runs(self) -> list[dict[str, Any]]:
        return [
            {"id": run.id, "name": "gate", "event": "push", "head_branch": "main",
             "status": "completed" if self.now >= run.reported_done else "in_progress"}
            for run in self.push_runs
        ]  # fmt: skip

    def jobs_of(self, run_id: int) -> list[dict[str, Any]]:
        run = next(r for r in self.push_runs if r.id == run_id)
        done = self.now >= run.jobs_done
        return [{"name": "postmerge", "status": "completed" if done else "in_progress"}]

    def postmerge_running(self) -> bool:
        live = [r for r in self.runs() if r["status"] != "completed"]
        if "postmerge_running_from" in self.pick:
            return bool(self.pick["postmerge_running_from"](live, self.jobs_of))
        return bool(live)  # the actor as it stood: the run's own status

    # --- the actor ----------------------------------------------------------------------------

    def decide(self) -> tuple[Any, Any, str]:
        result: tuple[Any, Any, str] = self.pick["decide"](
            self.pulls(),
            RULES,
            self.checks_of,
            lambda sha: self.main - int(sha[-4:]),
            now=T0 + timedelta(seconds=self.now),
            postmerge_running=self.postmerge_running,
        )
        return result

    def sleep(self, seconds: float) -> None:
        self.advance(self.now + int(seconds))

    def run_actor(self) -> None:
        self.running = True
        if "settle" in self.pick:
            number, _sha, action = self.pick["settle"](
                self.decide, self.sleep, clock=lambda: self.now
            )
        else:
            number, _sha, action = self.decide()
        self.log.append((self.now, action or "nothing", str(number)))
        if number:
            self.act(int(number), action)
        self.running = False

    def act(self, number: int, action: str) -> None:
        pr = self.open[number]
        if action == "update":
            pr.based_on, pr.gate_done = self.main, self.now + pr.gate_s
            self.wakes.append(pr.gate_done + WAKE_S)
            return
        assert action == "merge" and pr.based_on == self.main, "the host refuses a stale merge"
        del self.open[number]
        self.merged_at[number] = self.now
        self.main += 1
        land = self.now + BOT_S
        self.push_runs.append(PushRun(len(self.push_runs) + 1, land, land + RUN_LAG_S))
        self.wakes.append(land + RUN_LAG_S + WAKE_S)  # workflow_run: the push run completed
        if self.dispatch_after_postmerge:
            self.wakes.append(land + WAKE_S)  # the post-merge job's last step dispatches

    def wake(self) -> None:
        if self.running:
            self.pending = True  # one pending run; an older pending one is cancelled
            return
        self.run_actor()
        while self.pending:
            self.pending = False
            self.run_actor()

    # --- time ---------------------------------------------------------------------------------

    def advance(self, until: int) -> None:
        while self.now < until:
            self.now += TICK_S
            for run in self.push_runs:
                if run.jobs_done == self.now:
                    self.main += 1  # the bot's products commit
            for when in sorted(t for t in self.arrivals if t <= self.now):
                number, ref, gate_s = self.arrivals.pop(when)
                self.open[number] = Pr(number, ref, gate_s, self.main, self.now + gate_s)
                self.wakes.append(self.now + gate_s + WAKE_S)
            due = [t for t in self.wakes if t <= self.now]
            for t in due:
                self.wakes.remove(t)
            if due:
                self.wake()


def world(pick: dict[str, Any], gate_doc: dict[Any, Any], arrivals: dict[int, Any]) -> World:
    return World(pick, postmerge_wakes_the_actor(gate_doc), arrivals=dict(arrivals))


def the_afternoon_of_148() -> dict[int, tuple[int, str, int]]:
    """Twenty-five submissions in fifteen minutes, one in three building, as on 2026-09-23."""
    out = {}
    for i in range(25):
        building = i % 3 == 0
        ref = f"submit/p{i}" if building else f"append/a{i}"
        out[5 + 35 * i] = (148 + i, ref, SLOW_S if building else FAST_S)
    return out


# --- the replays ----------------------------------------------------------------------------------


def test_a_stale_read_after_the_wake_does_not_strand_the_pull_request(
    pick: dict[str, Any], gate_doc: dict[Any, Any]
) -> None:
    """Finding 1 and 2: the only wake arrives before the host reports the gate done."""
    w = world(pick, gate_doc, {5: (148, "propose/variant", SLOW_S)})
    w.advance(3 * 3600)
    assert 148 in w.merged_at, f"#148 never merged; the actor's runs: {w.log}"
    assert w.merged_at[148] <= 5 + SLOW_S + CHECK_LAG_S + 60, w.merged_at


def test_a_finished_post_merge_job_does_not_hold_the_next_update(
    pick: dict[str, Any], gate_doc: dict[Any, Any]
) -> None:
    """Finding 3: after #1 merges, #2 is behind; it must be updated once the bot commit lands,
    not once the host gets round to calling the run complete eight minutes later."""
    w = world(pick, gate_doc, {5: (1, "submit/a", SLOW_S), 10: (2, "submit/b", SLOW_S)})
    w.advance(3 * 3600)
    assert set(w.merged_at) == {1, 2}, f"left open: {sorted(w.open)}; runs: {w.log}"
    land = w.merged_at[1] + BOT_S
    # one gate round after the bot commit lands, plus the lag and the polling slack
    assert w.merged_at[2] <= land + SLOW_S + CHECK_LAG_S + 120, (w.merged_at, w.log)


def test_the_afternoon_of_148_drains_with_no_cron(
    pick: dict[str, Any], gate_doc: dict[Any, Any]
) -> None:
    """The whole afternoon, with no backstop at all: every submission merges. Not strictly in
    order: a pull request that is behind while its first gate still runs holds nothing (F07-T31's
    rule), so a green append opened after it may go first."""
    w = world(pick, gate_doc, the_afternoon_of_148())
    w.advance(4 * 3600)
    assert w.open == {}, f"frozen with {sorted(w.open)} open; last runs: {w.log[-6:]}"
    assert max(w.merged_at.values()) <= 3 * 3600, w.merged_at


# --- the rules one at a time ----------------------------------------------------------------------

NOW = T0 + timedelta(hours=1)


def green() -> list[dict[str, Any]]:
    return [check(GATE_JOB, "success"), check(STEP9_JOB, "skipped", id_=2)]


def test_a_run_whose_jobs_have_all_finished_is_not_running(pick: dict[str, Any]) -> None:
    runs = [{"id": 7, "name": "gate", "status": "in_progress"}]
    finished = [
        {"name": "postmerge", "status": "completed"},
        {"name": "gate", "status": "completed"},
    ]
    working = [{"name": "postmerge", "status": "in_progress"}]
    assert pick["postmerge_running_from"](runs, lambda _id: finished) is False
    assert pick["postmerge_running_from"](runs, lambda _id: working) is True
    # queued, no job started yet: the commit is still to come
    assert pick["postmerge_running_from"](runs, lambda _id: []) is True
    assert pick["postmerge_running_from"]([], lambda _id: working) is False


def test_a_hold_is_decided_again_until_it_resolves(pick: dict[str, Any]) -> None:
    answers = iter([("", "", "hold"), ("", "", "hold"), (6, "abc", "merge")])
    slept: list[float] = []
    clock = [0.0]

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        clock[0] += seconds

    got = pick["settle"](lambda: next(answers), sleep, clock=lambda: clock[0])
    assert got == (6, "abc", "merge") and len(slept) == 2


def test_a_hold_that_never_resolves_ends_the_run_at_the_cap(pick: dict[str, Any]) -> None:
    clock = [0.0]

    def sleep(seconds: float) -> None:
        clock[0] += seconds

    got = pick["settle"](lambda: ("", "", "hold"), sleep, clock=lambda: clock[0])
    assert got == ("", "", "hold")
    assert pick["SETTLE_CAP_S"] <= clock[0] <= pick["SETTLE_CAP_S"] + pick["SETTLE_EVERY_S"]


def test_nothing_to_do_is_not_waited_on(pick: dict[str, Any]) -> None:
    calls: list[int] = []

    def step() -> tuple[str, str, str]:
        calls.append(1)
        return "", "", ""

    got = pick["settle"](step, lambda _s: None, clock=lambda: 0)
    assert got == ("", "", "") and calls == [1]


def test_a_pull_request_whose_mergeability_is_unknown_is_not_updated(pick: dict[str, Any]) -> None:
    """Finding 6: ``mergeable`` is null while the host computes it. #150 was updated twice in
    that state, the update failed, and the failed run woke nothing."""
    pulls = [pull(150, "propose/witness")]
    got = pick["decide"](pulls, RULES, lambda _s: green(), lambda _s: 1, lambda _n: None, now=NOW)
    assert got == ("", "", "hold"), got
    # and a known conflict is still passed over, a known clean one still acted on
    got = pick["decide"](pulls, RULES, lambda _s: green(), lambda _s: 1, lambda _n: True, now=NOW)
    assert got == ("", "", "")
    got = pick["decide"](pulls, RULES, lambda _s: green(), lambda _s: 1, lambda _n: False, now=NOW)
    assert got == (150, pulls[0]["head"]["sha"], "update")


# --- static: every way the actor can stop has a wake after it ------------------------------------


def test_the_post_merge_job_wakes_the_actor_whatever_happened(gate_doc: dict[Any, Any]) -> None:
    job = gate_doc["jobs"]["postmerge"]
    (step,) = [s for s in job["steps"] if "gh workflow run merge.yml" in str(s.get("run", ""))]
    assert step.get("if") == "always()", step.get("if")
    assert "github.token" in str(step.get("env", {})), "its own token: dispatch starts a run"
    assert job["permissions"].get("actions") == "write"


def test_a_failed_act_wakes_the_actor_again(doc: dict[Any, Any]) -> None:
    rewake = doc["jobs"]["rewake"]
    assert rewake["needs"] == "merge" and rewake["if"] == "failure()"
    assert rewake["permissions"] == {"actions": "write"}
    assert "gh workflow run merge.yml" in str(rewake["steps"])
    # the acting job itself still only reads
    assert set(doc["jobs"]["merge"]["permissions"].values()) == {"read"}


def test_the_job_is_capped_above_the_settle_loop(doc: dict[Any, Any], pick: dict[str, Any]) -> None:
    assert doc["jobs"]["merge"]["timeout-minutes"] * 60 > pick["SETTLE_CAP_S"] + 120
