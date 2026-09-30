"""F07-T46: a pull request whose branch has moved away from its own head does not hold the queue
(the 2026-09-30 freeze and storm).

Read from the record. At 04:09:36Z the actor ran ``PUT pulls/306/update-branch`` with the pull
request's head as ``expected_head_sha``. GitHub created the merge commit and moved the branch
``submit/01M3QNGQ...`` to ``d74ba77c``, but the pull request object kept its old head ``641260d5``
(``refs/pull/306/head`` too), fired no ``synchronize``, so no gate ran and nothing woke the actor;
the ``*/15`` cron did not fire. Six hours later an unrelated merge woke it: ``decide()`` read the
stale head, chose ``update #306`` at ``641260d5``, the host refused it (``422 expected head sha
didn't match current head ref``), the Act step exited 1, ``rewake`` dispatched again, and that
repeated every ~50 s: 89 failed runs in 35 minutes, 15 pull requests stuck behind #306. Even an
update with no expected sha was refused. What unstuck it was a real push of a merge commit (main
merged into the branch): the host then re-synced the pull request's head and ran the gate.

Three rules follow, each tested below against the workflow as it ships. ``decide()`` asks the host
for the branch's own head (``branch_head_of``) and passes over a candidate whose branch head is
not its pull request head, recording it as stuck; the queue moves on. The Act step nudges each
stuck one with the server-side merge of main into its branch (``POST repos/{repo}/merges``), the
push that re-syncs the pull request; a nudge never fails the run. And a refused update or single
merge is a warning and exit 0, not a failed job, so ``rewake`` fires only on a genuine crash.

The replay uses ``test_finding_merge_actor_wakes.py``'s world (wakes only when the host would send
one, no cron) with one addition: the host's update of one pull request moves its branch and not
its pull request. It was seen red against the actor as it stood
(``engineering/evidence/F07/task-46-red.txt``): the same ``update 306`` every round, nothing
merging.
"""

from __future__ import annotations

import inspect
import os
import stat
import subprocess
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from test_finding_merge_actor_batch import NOW, gating, green
from test_finding_merge_actor_wakes import (
    FAST_S,
    SLOW_S,
    T0,
    WAKE_S,
    World,
    load_gate_doc,
    postmerge_wakes_the_actor,
)
from test_finding_merge_actor_workflow import RULES, load_doc, load_pick, pull

#: The rewake job sleeps 30 s and dispatches; a runner picks the dispatch up a few seconds later.
REWAKE_S = 30 + WAKE_S


@pytest.fixture(scope="module")
def doc() -> dict[Any, Any]:
    return load_doc()


@pytest.fixture(scope="module")
def pick(doc: dict[Any, Any]) -> dict[str, Any]:
    return load_pick(doc)


@pytest.fixture(scope="module")
def gate_doc() -> dict[Any, Any]:
    return load_gate_doc()


def decide(
    pick: dict[str, Any],
    pulls: list[dict[str, Any]],
    checks: dict[int, list[dict[str, Any]]],
    behind: dict[int, int] | int = 1,
    *,
    branch_heads: dict[str, str] | None,
    stuck: list[Any] | None = None,
) -> tuple[Any, Any, str]:
    """``branch_heads`` maps a branch ref to the sha the host reports for it; None means the
    caller does not ask (``branch_head_of`` answers None for everything)."""
    by_sha = {p["head"]["sha"]: p["number"] for p in pulls}
    heads = branch_heads or {}
    kwargs: dict[str, Any] = {"branch_head_of": heads.get}
    if stuck is not None:
        kwargs["stuck"] = stuck
    got: tuple[Any, Any, str] = pick["decide"](
        pulls,
        RULES,
        lambda sha: checks[by_sha[sha]],
        lambda sha: behind if isinstance(behind, int) else behind[by_sha[sha]],
        lambda number: False,
        now=NOW,
        postmerge_running=lambda: False,
        **kwargs,
    )
    return got


def sha_of(pulls: list[dict[str, Any]], number: int) -> str:
    return next(str(p["head"]["sha"]) for p in pulls if p["number"] == number)


# --- decide: a desynced candidate is passed over and recorded ----------------------------------


def test_a_candidate_whose_branch_head_is_not_its_pull_request_head_is_passed_over(
    pick: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    """(a) #306 at the head of the queue, its branch moved on without it; #307 green behind it.
    The actor acts on #307 and records #306 as stuck, naming both shas."""
    pulls = [pull(306, "submit/stuck"), pull(307, "submit/next")]
    heads = {"submit/stuck": "d74ba77c" + "0" * 32, "submit/next": sha_of(pulls, 307)}
    stuck: list[Any] = []
    got = decide(pick, pulls, {306: green(), 307: green()}, branch_heads=heads, stuck=stuck)
    assert got == (307, sha_of(pulls, 307), "update"), got
    assert stuck == [(306, "submit/stuck")], stuck
    out = capsys.readouterr().out
    assert "306" in out and sha_of(pulls, 306) in out and heads["submit/stuck"] in out, out


def test_a_stuck_pull_request_never_holds_the_queue(pick: dict[str, Any]) -> None:
    """Even when its stale head is up to date and its stale checks are running (a shape the host
    could report), the checks belong to a commit that is not the branch: pass it over."""
    pulls = [pull(306, "submit/stuck"), pull(307, "append/next")]
    heads = {"submit/stuck": "d74ba77c" + "0" * 32, "submit/next": sha_of(pulls, 307)}
    stuck: list[Any] = []
    got = decide(
        pick, pulls, {306: gating(), 307: green()}, {306: 0, 307: 1}, branch_heads=heads,
        stuck=stuck,
    )  # fmt: skip
    assert got == ("307", sha_of(pulls, 307), "merge-batch"), got
    assert len(stuck) == 1
    # and with nothing else in the queue the answer is nothing to do, with #306 still recorded
    stuck = []
    got = decide(pick, pulls[:1], {306: green()}, branch_heads=heads, stuck=stuck)
    assert got == ("", "", "") and len(stuck) == 1, (got, stuck)


def test_an_unknown_branch_head_changes_nothing(pick: dict[str, Any]) -> None:
    """(b) ``branch_head_of`` answering None is "not asked": the actor decides as before."""
    pulls = [pull(306, "submit/stuck"), pull(307, "submit/next")]
    stuck: list[Any] = []
    got = decide(pick, pulls, {306: green(), 307: green()}, branch_heads=None, stuck=stuck)
    assert got == (306, sha_of(pulls, 306), "update") and stuck == [], (got, stuck)
    # a branch head that equals the pull request head is not stuck either
    heads = {p["head"]["ref"]: str(p["head"]["sha"]) for p in pulls}
    got = decide(pick, pulls, {306: green(), 307: green()}, branch_heads=heads, stuck=stuck)
    assert got == (306, sha_of(pulls, 306), "update") and stuck == [], (got, stuck)


def test_the_default_asks_nothing_and_the_batch_skips_a_desynced_append(
    pick: dict[str, Any],
) -> None:
    """Callers that pass no ``branch_head_of`` (every earlier test) get today's behaviour; inside
    a batch a desynced append is passed over too, since its merge names a head the branch has
    left, and the appends after it still go."""
    sig = inspect.signature(pick["decide"])
    assert sig.parameters["branch_head_of"].default("any/ref") is None
    pulls = [pull(1, "append/a"), pull(2, "append/b"), pull(3, "append/c")]
    heads = {p["head"]["ref"]: str(p["head"]["sha"]) for p in pulls}
    heads["append/b"] = "f" * 40
    stuck: list[Any] = []
    got = decide(pick, pulls, {n: green() for n in (1, 2, 3)}, branch_heads=heads, stuck=stuck)
    assert got == ("1 3", f"{sha_of(pulls, 1)} {sha_of(pulls, 3)}", "merge-batch"), got
    assert len(stuck) == 1


# --- the replay of 2026-09-30 --------------------------------------------------------------------


@dataclass
class StuckWorld(World):
    """The wakes world plus the host's defect: the first update of ``desync_on_update`` moves its
    branch and not its pull request. ``branch_based_on`` is the branch's own line; the pull
    request's is ``Pr.based_on``. An update of a desynced pull request is refused (422), the
    run fails and ``rewake`` fires; a nudge (main merged into the branch) re-syncs it."""

    desync_on_update: set[int] = field(default_factory=set)
    branch_based_on: dict[int, int] = field(default_factory=dict)
    desynced: set[int] = field(default_factory=set)
    failed_runs: int = 0
    nudged: list[tuple[int, int]] = field(default_factory=list)
    stuck_seen: list[Any] = field(default_factory=list)

    def branch_head_of(self, ref: str) -> str | None:
        pr = next((p for p in self.open.values() if p.ref == ref), None)
        if pr is None:
            return None
        based_on = self.branch_based_on.get(pr.number, pr.based_on)
        return f"{pr.number:036d}{based_on:04d}"

    def decide(self) -> tuple[Any, Any, str]:
        kwargs: dict[str, Any] = {}
        params = inspect.signature(self.pick["decide"]).parameters
        if "branch_head_of" in params:
            kwargs["branch_head_of"] = self.branch_head_of
        if "stuck" in params:
            self.stuck_seen = []
            kwargs["stuck"] = self.stuck_seen
        result: tuple[Any, Any, str] = self.pick["decide"](
            self.pulls(),
            RULES,
            self.checks_of,
            lambda sha: self.main - int(sha[-4:]),
            now=self.now_stamp(),
            postmerge_running=self.postmerge_running,
            **kwargs,
        )
        return result

    def now_stamp(self) -> Any:
        return T0 + timedelta(seconds=self.now)

    def run_actor(self) -> None:
        self.running = True
        number, _sha, action = self.pick["settle"](self.decide, self.sleep, clock=lambda: self.now)
        self.log.append((self.now, action or "nothing", str(number)))
        for n, _ref in list(self.stuck_seen):
            self.nudge(int(n))  # the Act step nudges first, then acts
        if number:
            self.act(str(number), action)
        self.running = False

    def act(self, number: str, action: str) -> None:
        if action == "update":
            n = int(number)
            if n in self.desynced:
                # 422 expected head sha didn't match current head ref: the run fails
                self.failed_runs += 1
                if self.rewake_after_failure:
                    self.wakes.append(self.now + REWAKE_S)
                return
            if n in self.desync_on_update:
                # the host's defect: the branch moves, the pull request does not, no gate runs
                self.desync_on_update.discard(n)
                self.desynced.add(n)
                self.branch_based_on[n] = self.main
                return
        super().act(number, action)

    def nudge(self, number: int) -> None:
        pr = self.open.get(number)
        if pr is None:
            return
        if self.branch_based_on.get(number, pr.based_on) == self.main:
            return  # 204: the branch already contains main; the nudge did nothing
        self.nudged.append((self.now, number))
        pr.based_on = self.main
        self.branch_based_on[number] = self.main
        self.desynced.discard(number)
        pr.gate_done = self.now + pr.gate_s  # the host re-syncs the head and the gate runs
        self.wakes.append(pr.gate_done + WAKE_S)

    rewake_after_failure: bool = True


def the_morning_of_306() -> dict[int, tuple[int, str, int]]:
    """An append that merges at once, so the building pull request after it is behind when it
    is green and its first act is the update; then fifteen behind it in the next quarter hour,
    one in three building, as on 2026-09-30."""
    out: dict[int, tuple[int, str, int]] = {
        5: (305, "append/first", FAST_S),
        10: (306, "submit/stuck", SLOW_S),
    }
    for i in range(15):
        building = i % 3 == 0
        ref = f"submit/p{i}" if building else f"append/a{i}"
        out[60 + 55 * i] = (307 + i, ref, SLOW_S if building else FAST_S)
    return out


def test_the_morning_of_306_drains_and_306_is_nudged(
    pick: dict[str, Any], gate_doc: dict[Any, Any]
) -> None:
    """(c) The actor's first update of #306 moves its branch and not its pull request. As the
    actor stood, every later wake chose ``update 306`` again, the host refused it, the failed run
    dispatched another, and the fifteen behind it never merged. Now they merge, #306 is nudged
    with a merge of main, the host re-syncs it, and it merges too."""
    w = StuckWorld(
        pick, postmerge_wakes_the_actor(gate_doc), arrivals=the_morning_of_306(),
        desync_on_update={306},
    )  # fmt: skip
    w.advance(3 * 3600)
    chosen = [a for a in w.log if a[2] == "306"]
    others = set(range(307, 322))
    assert others <= set(w.merged_at), (
        f"left open: {sorted(w.open)}; #306 chosen {len(chosen)} times, {w.failed_runs} failed "
        f"runs; last runs: {w.log[-8:]}"
    )
    assert w.failed_runs == 0, f"{w.failed_runs} failed runs (a rewake storm): {w.log[-8:]}"
    assert [n for _, n in w.nudged] == [306], w.nudged
    assert 306 in w.merged_at, f"#306 never merged after its nudge: {w.log[-8:]}"


def test_a_stuck_pull_request_alone_is_nudged_once_main_moves(
    pick: dict[str, Any], gate_doc: dict[Any, Any]
) -> None:
    """The 204 case: while main has not moved since the branch was moved, the nudge has nothing
    to merge and #306 stays stuck (a person has to push to it); the moment one other merge
    lands, the next nudge is a real push and #306 recovers."""
    arrivals = {
        5: (305, "append/first", FAST_S),
        10: (306, "submit/stuck", SLOW_S),
        2000: (400, "append/later", FAST_S),
    }
    w = StuckWorld(
        pick, postmerge_wakes_the_actor(gate_doc), arrivals=arrivals, desync_on_update={306}
    )
    # #400's gate wakes the actor at about 2025: #306 is passed over and its nudge finds main
    # exactly where its branch already is (204); #400 merges in that run
    w.advance(2040)
    assert 306 in w.desynced and 306 in w.open, (w.log, w.nudged)
    assert w.stuck_seen == [(306, "submit/stuck")] and w.nudged == [], (w.stuck_seen, w.nudged)
    assert 400 in w.merged_at, w.log
    w.advance(3 * 3600)
    assert set(w.merged_at) == {305, 306, 400}, (w.merged_at, w.log[-8:])
    assert w.failed_runs == 0 and [n for _, n in w.nudged] == [306], (w.failed_runs, w.nudged)


# --- the Act step, run as it stands with a fake host ---------------------------------------------


FAKE_GH = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$GH_LOG"
if [ -n "${GH_FAIL:-}" ] && printf '%s' "$*" | grep -q -- "$GH_FAIL"; then
  echo "HTTP 422: expected head sha didn't match current head ref" >&2; exit 1
fi
if [ -n "${GH_BODY:-}" ] && printf '%s' "$*" | grep -q -- "/merges"; then printf '%s' "$GH_BODY"; fi
exit 0
"""


def act_step(doc: dict[Any, Any]) -> dict[str, Any]:
    (act,) = [s for s in doc["jobs"]["merge"]["steps"] if s.get("name", "").startswith("Act")]
    return dict(act)


def run_act(
    doc: dict[Any, Any],
    tmp_path: Path,
    number: str,
    sha: str,
    action: str,
    *,
    stuck: str = "",
    fail: str = "",
    body: str = "",
    dry_run: bool = False,
) -> tuple[int, list[str], str]:
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
        "GH_BODY": body,
        "GH_TOKEN": "" if dry_run else "fake",  # a fake, so the act is not a dry run
        "REPO": "owner/graph",
        "NUMBER": number,
        "SHA": sha,
        "ACTION": action,
        "STUCK": stuck,
    }
    proc = subprocess.run(
        ["bash", "-c", str(act_step(doc)["run"])],
        capture_output=True, text=True, check=False, env=env,
    )  # fmt: skip
    calls = [line for line in log.read_text().splitlines() if line]
    return proc.returncode, calls, proc.stdout + proc.stderr


def test_a_refused_update_is_a_warning_and_not_a_failed_run(
    doc: dict[Any, Any], tmp_path: Path
) -> None:
    """(d) The 422 of 2026-09-30: the step says so and exits 0, so ``rewake`` does not fire; the
    next wake is the next gate completion, post-merge job or cron, and decide() passes the stuck
    pull request over meanwhile."""
    code, calls, out = run_act(doc, tmp_path, "306", "641260d5", "update", fail="update-branch")
    assert calls == [
        "api -X PUT repos/owner/graph/pulls/306/update-branch -f expected_head_sha=641260d5"
    ]
    assert code == 0, out
    assert "::warning::" in out and "306" in out, out


def test_a_refused_single_merge_is_a_warning_and_not_a_failed_run(
    doc: dict[Any, Any], tmp_path: Path
) -> None:
    code, calls, out = run_act(doc, tmp_path, "5", "a5", "merge", fail="pulls/5/merge")
    assert calls == ["api -X PUT repos/owner/graph/pulls/5/merge -f sha=a5 -f merge_method=merge"]
    assert code == 0, out
    assert "::warning::" in out, out


def test_each_stuck_pull_request_is_nudged_with_a_merge_of_main_into_its_branch(
    doc: dict[Any, Any], tmp_path: Path
) -> None:
    """(d) The nudge is the server-side merge of main into the branch: the push that re-synced
    #306 when the lead made it by hand. It uses the token the step already holds (C8)."""
    stuck = "306:submit/01M3QNGQ 310:submit/other"
    code, calls, out = run_act(
        doc, tmp_path, "307", "a307", "update", stuck=stuck, body='{"sha": "abc"}'
    )
    assert code == 0, out
    nudges = [c for c in calls if "/merges" in c]
    assert len(nudges) == 2, calls
    for call, ref in zip(nudges, ("submit/01M3QNGQ", "submit/other"), strict=True):
        assert call.startswith("api -X POST repos/owner/graph/merges"), call
        assert f"-f base={ref}" in call and "-f head=main" in call, call
    assert "api -X PUT repos/owner/graph/pulls/307/update-branch -f expected_head_sha=a307" in calls
    assert "306" in out and "310" in out, out


def test_a_refused_nudge_never_fails_the_run(doc: dict[Any, Any], tmp_path: Path) -> None:
    code, calls, out = run_act(
        doc, tmp_path, "307", "a307", "update", stuck="306:submit/x", fail="/merges"
    )
    assert code == 0, out
    assert any("/merges" in c for c in calls), calls
    assert "::warning::" in out and "306" in out, out
    # the update was still made after the refused nudge
    assert "api -X PUT repos/owner/graph/pulls/307/update-branch -f expected_head_sha=a307" in calls


def test_a_nudge_that_finds_main_already_in_the_branch_says_it_is_still_stuck(
    doc: dict[Any, Any], tmp_path: Path
) -> None:
    """The merges endpoint answers 204 with no body when the branch already contains main: no
    push, no re-sync, and the pull request is still stuck. The step must say so, not claim a
    nudge."""
    code, _calls, out = run_act(doc, tmp_path, "", "", "", stuck="306:submit/x", body="")
    assert code == 0, out
    assert "::warning::" in out and "still stuck" in out, out


def test_stuck_alone_acts_and_dry_runs_without_the_token(
    doc: dict[Any, Any], tmp_path: Path
) -> None:
    """The Act step runs for a stuck list with nothing to merge or update, and without the
    secret it says what it would nudge and changes nothing (C7)."""
    step = act_step(doc)
    assert "stuck" in str(step.get("if", "")), step.get("if")
    code, calls, out = run_act(doc, tmp_path, "", "", "", stuck="306:submit/x", body="{}")
    assert code == 0, out
    assert len(calls) == 1 and "merges -f base=submit/x -f head=main" in calls[0], calls
    code, calls, out = run_act(doc, tmp_path, "", "", "", stuck="306:submit/x", dry_run=True)
    assert code == 0 and calls == [] and "dry run" in out and "306" in out, (code, calls, out)


def test_the_pick_writes_the_stuck_list_to_the_output(doc: dict[Any, Any]) -> None:
    (step,) = [s for s in doc["jobs"]["merge"]["steps"] if s.get("id") == "pick"]
    assert "stuck=" in step["run"], "the stuck pull requests reach the Act step as an output"
    assert "git/ref/heads/" in step["run"], "the branch's own head, from the host"
    assert act_step(doc)["env"].get("STUCK") == "${{ steps.pick.outputs.stuck }}"
