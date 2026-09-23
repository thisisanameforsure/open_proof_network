"""F07-T31: the merge actor holds the line, so a green pull request is not starved (testers
2026-09-21, finding 1; all three agents).

Read from the record: graph pull request #131 (a witness on a Mathlib target, a three-minute
gate) went green four times and merged after thirteen minutes; #136 took 19, #139 took 20, #140
took 31, #137 took 33 and at least eight green runs. Annexes and postmortems opened in the same
minutes merged in under one. The actor took the oldest *green* pull request: the one it had just
updated was *pending* while its gate re-ran, so it was passed over, the next green one (always a
fifteen-second append) was merged, ``main`` moved, and the waiting one was behind again. A pull
request merged only when nobody else submitted for a whole round.

The replay below drives the shipped decision program through that morning as a small simulation.
It was seen red against the actor as it stood (``engineering/evidence/F07/task-31.txt``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
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


@pytest.fixture(scope="module")
def doc() -> dict[Any, Any]:
    return load_doc()


@pytest.fixture(scope="module")
def pick(doc: dict[Any, Any]) -> dict[str, Any]:
    return load_pick(doc)


T0 = datetime(2026, 9, 21, 6, 28, tzinfo=UTC)
SLOW_S, FAST_S, BOT_S, TICK_S = 180, 15, 120, 15


@dataclass
class Open:
    number: int
    ref: str
    gate_s: int
    based_on: int  # the version of main its head contains
    gate_done: int  # the second its current gate run finishes
    started: int  # the second its current gate run started


@dataclass
class World:
    """Main, the open pull requests and the post-merge jobs still to commit, second by second."""

    decide: Any
    main: int = 0
    now: int = 0
    open: dict[int, Open] = field(default_factory=dict)
    bot_commits: list[int] = field(default_factory=list)  # the seconds they land
    merged_at: dict[int, int] = field(default_factory=dict)
    log: list[tuple[int, str, int]] = field(default_factory=list)

    def submit(self, number: int, ref: str, gate_s: int) -> None:
        self.open[number] = Open(number, ref, gate_s, self.main, self.now + gate_s, self.now)

    def sha(self, pr: Open) -> str:
        return f"{pr.number:036d}{pr.based_on:04d}"

    def checks_of(self, sha: str) -> list[dict[str, Any]]:
        pr = next(p for p in self.open.values() if self.sha(p) == sha)
        done = self.now >= pr.gate_done
        started = (T0 + timedelta(seconds=pr.started)).isoformat().replace("+00:00", "Z")
        gate = {**check(GATE_JOB, "success" if done else None), "started_at": started}
        return [gate, check(STEP9_JOB, "skipped" if done else None, id_=2)]

    def act(self) -> None:
        pulls = []
        for pr in self.open.values():
            entry = pull(pr.number, pr.ref)
            entry["head"]["sha"] = self.sha(pr)
            pulls.append(entry)
        args = (pulls, RULES, self.checks_of, lambda sha: self.main - int(sha[-4:]))
        try:
            number, _sha, action = self.decide(
                *args,
                now=T0 + timedelta(seconds=self.now),
                postmerge_running=lambda: bool(self.bot_commits),
            )
        except TypeError:  # the actor as it stood before T31 took no clock and no post-merge view
            number, _sha, action = self.decide(*args)
        if not number:
            return
        pr = self.open[int(number)]
        self.log.append((self.now, action, pr.number))
        if action == "update":
            pr.based_on, pr.started, pr.gate_done = self.main, self.now, self.now + pr.gate_s
        else:
            assert action == "merge" and pr.based_on == self.main, "the host refuses a stale merge"
            del self.open[pr.number]
            self.merged_at[pr.number] = self.now
            self.main += 1
            self.bot_commits.append(self.now + BOT_S)

    def run(self, until: int, arrivals: dict[int, tuple[int, str, int]]) -> None:
        for second in range(0, until, TICK_S):
            self.now = second
            for landed in [t for t in self.bot_commits if t <= second]:
                self.bot_commits.remove(landed)
                self.main += 1  # the products commit moves main a second time
            for when, (number, ref, gate_s) in list(arrivals.items()):
                if when <= second:
                    self.submit(number, ref, gate_s)
                    del arrivals[when]
            self.act()


def the_morning_of_131(decide: Any) -> World:
    """A witness on a Mathlib target at second 0; an append every minute for ten minutes."""
    world = World(decide)
    arrivals: dict[int, tuple[int, str, int]] = {0: (131, "propose/witness-131", SLOW_S)}
    for i in range(10):
        arrivals[60 * (i + 1)] = (132 + i, f"append/a{i}", FAST_S)
    world.run(3600, arrivals)
    return world


def test_a_green_mathlib_pull_request_is_not_starved_by_appends(pick: dict[str, Any]) -> None:
    world = the_morning_of_131(pick["decide"])
    assert 131 in world.merged_at, f"#131 never merged; the actor's acts: {world.log[:12]}"
    # Opened on an up-to-date main, so one gate round is all it owes; one more for slack.
    assert world.merged_at[131] <= 2 * SLOW_S + TICK_S, world.merged_at


def test_the_queue_is_first_in_first_out_and_everything_merges(pick: dict[str, Any]) -> None:
    world = the_morning_of_131(pick["decide"])
    assert world.open == {}, f"left open: {sorted(world.open)}"
    order = sorted(world.merged_at, key=lambda n: world.merged_at[n])
    assert order == sorted(world.merged_at), order


def test_no_gate_round_is_wasted_on_a_bot_commit_about_to_land(pick: dict[str, Any]) -> None:
    """Two Mathlib pull requests, the second behind once the first merges. Updated at once it
    would be behind again when the first one's products commit landed, and owe a third round."""
    world = World(pick["decide"])
    world.run(3600, {0: (201, "propose/a", SLOW_S), 15: (202, "submit/b", SLOW_S)})
    updates_of_202 = [entry for entry in world.log if entry[1:] == ("update", 202)]
    assert len(updates_of_202) == 1, world.log
    assert world.open == {}


# --- the rules one at a time ----------------------------------------------------------------------

NOW = T0 + timedelta(hours=1)


def gating(started: datetime) -> list[dict[str, Any]]:
    stamp = started.isoformat().replace("+00:00", "Z")
    return [{**check(GATE_JOB, None), "started_at": stamp}, check(STEP9_JOB, None, id_=2)]


def green() -> list[dict[str, Any]]:
    return [check(GATE_JOB, "success"), check(STEP9_JOB, "skipped", id_=2)]


def test_an_up_to_date_gating_pull_request_holds_everything_behind_it(pick: dict[str, Any]) -> None:
    """The starvation itself, in one call: the actor used to merge #7 here."""
    pulls = [pull(6, "propose/slow"), pull(7, "append/fast")]
    checks = {
        pulls[0]["head"]["sha"]: gating(NOW - timedelta(minutes=2)),
        pulls[1]["head"]["sha"]: green(),
    }
    got = pick["decide"](pulls, RULES, checks.__getitem__, lambda _sha: 0, now=NOW)
    assert got == ("", "", "hold")


def test_a_run_that_never_reports_holds_nothing(pick: dict[str, Any]) -> None:
    pulls = [pull(6, "propose/stuck"), pull(7, "append/fast")]
    stale = NOW - timedelta(seconds=pick["HOLD_S"] + 1)
    checks = {pulls[0]["head"]["sha"]: gating(stale), pulls[1]["head"]["sha"]: green()}
    got = pick["decide"](pulls, RULES, checks.__getitem__, lambda _sha: 0, now=NOW)
    assert got == (7, pulls[1]["head"]["sha"], "merge")


def test_a_pending_pull_request_that_is_behind_holds_nothing(pick: dict[str, Any]) -> None:
    """Its run will have to be repeated anyway, so nothing is gained by waiting for it."""
    pulls = [pull(6, "propose/slow"), pull(7, "append/fast")]
    behind = {pulls[0]["head"]["sha"]: 2, pulls[1]["head"]["sha"]: 0}
    checks = {
        pulls[0]["head"]["sha"]: gating(NOW - timedelta(minutes=1)),
        pulls[1]["head"]["sha"]: green(),
    }
    got = pick["decide"](pulls, RULES, checks.__getitem__, behind.__getitem__, now=NOW)
    assert got == (7, pulls[1]["head"]["sha"], "merge")


def test_the_oldest_green_one_goes_first_even_past_a_newer_gating_one(pick: dict[str, Any]) -> None:
    pulls = [pull(6, "propose/old-green"), pull(7, "propose/new-gating")]
    checks = {pulls[0]["head"]["sha"]: green(), pulls[1]["head"]["sha"]: gating(NOW)}
    behind = {pulls[0]["head"]["sha"]: 1, pulls[1]["head"]["sha"]: 0}
    got = pick["decide"](pulls, RULES, checks.__getitem__, behind.__getitem__, now=NOW)
    assert got == (6, pulls[0]["head"]["sha"], "update")


def test_nothing_is_updated_or_merged_while_a_post_merge_job_runs(pick: dict[str, Any]) -> None:
    """Restated by F07-T33 (Q41). T31 held only a building pull request's update here and let an
    append through, and never held a merge ("the branch is up to date, so main has not moved");
    an append updated in the window re-gated in fifteen seconds and was merged while the job was
    still rendering, so the job's push was refused and its record lost (#125, #132, #133, #145).
    The rule this test was about stands: no round is wasted on a commit about to land. It now
    covers every kind, and the merge as well as the update."""
    for ref in ("propose/slow", "submit/slow", "append/fast"):
        for behind in (1, 0):  # the update, and the merge
            got = pick["decide"](
                [pull(6, ref)],
                RULES,
                lambda _s: green(),
                lambda _s, b=behind: b,
                now=NOW,
                postmerge_running=lambda: True,
            )
            assert got == ("", "", "hold"), (ref, behind, got)
    # and once the job has committed, the same pull request is acted on
    pulls = [pull(6, "append/fast")]
    got = pick["decide"](
        pulls, RULES, lambda _s: green(), lambda _s: 1, now=NOW, postmerge_running=lambda: False
    )
    assert got == (6, pulls[0]["head"]["sha"], "update")


def test_a_hold_names_no_pull_request_so_the_acting_step_is_skipped(doc: dict[Any, Any]) -> None:
    """``hold`` rides in ``action`` with an empty ``number``; the one step that holds the token
    runs only when ``number`` is set, and would merge on any action that is not ``update``."""
    (act,) = [s for s in doc["jobs"]["merge"]["steps"] if s.get("name", "").startswith("Act")]
    assert act["if"] == "steps.pick.outputs.number != ''"


def test_the_job_may_read_the_runs_it_asks_about_and_nothing_more(doc: dict[Any, Any]) -> None:
    grants = doc["jobs"]["merge"]["permissions"]
    assert grants["actions"] == "read" and set(grants.values()) == {"read"}
