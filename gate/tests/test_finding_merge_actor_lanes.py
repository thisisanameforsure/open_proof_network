"""F07-T56: the queue is strict per target, not across the whole graph (the owner, 2026-10-02).

A submission touches exactly one target (D-2, D-3), so a merge on erdos-402 cannot change the
verdict on erdos-69. The ruleset's up-to-date rule was applied to the whole of ``main``: every merge
put every other pull request behind, and every building one paid a full gate round to catch up with
commits that could not change its verdict — on top of waiting for the post-merge job (F07-T33),
which F07-T55 made unnecessary.

Now each target is a lane. A pull request is stale only if main's commits since its merge base
touched its own target or a shared input (``curators.json``, ``policy.json``, ``keys/``,
``schemas/``, the workflows); the products the post-merge job renders and the guides never count. A
stale one is updated, any other merges behind main, and one run acts in every lane. Within a lane it
is one at a time, as the whole queue was, which stays the safe choice now that a proof may import
another node's proved lemma. The post-merge re-check on the merge commit stays the backstop.

The decision program is the heredoc ``merge.yml`` writes to ``pick.py``, run as it stands; the
replay below is ``test_finding_merge_actor_wakes.py``'s host with targets. It was seen red against
the actor as it stood (``engineering/evidence/F07/task-56-red.txt``).
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
    CHECK_LAG_S,
    FAST_S,
    SLOW_S,
    T0,
    World,
    load_gate_doc,
    the_afternoon_of_148,
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


def green() -> list[dict[str, Any]]:
    return [check(GATE_JOB, "success"), check(STEP9_JOB, "skipped", id_=2)]


def gating() -> list[dict[str, Any]]:
    stamp = (NOW - timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
    return [{**check(GATE_JOB, None), "started_at": stamp}, check(STEP9_JOB, None, id_=2)]


def lanes(
    pick: dict[str, Any],
    pulls: list[dict[str, Any]],
    checks: dict[int, list[dict[str, Any]]],
    targets: dict[int, str | None],
    *,
    stale: dict[int, int] | None = None,
    conflicts: dict[int, bool | None] | None = None,
) -> list[tuple[int, str, str]]:
    by_sha = {p["head"]["sha"]: p["number"] for p in pulls}
    decided: list[tuple[int, str, str]] = pick["decide_lanes"](
        pulls,
        RULES,
        lambda sha: checks[by_sha[sha]],
        lambda sha: (stale or {}).get(by_sha[sha], 0),
        lambda number: (conflicts or {}).get(number, False),
        now=NOW,
        lane_of=targets.__getitem__,
    )
    return decided


def sha(pulls: list[dict[str, Any]], number: int) -> str:
    return str(next(p["head"]["sha"] for p in pulls if p["number"] == number))


# --- what counts as stale ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("path", "lane", "counts"),
    [
        ("targets/t1/nodes/n/Proof.lean", "t1", True),  # its own target's sources
        ("targets/t1/nodes/n/META.yaml", "t1", True),  # a status the bot wrote is still an input
        ("targets/t1/nodes/n/Context.lean", "t1", True),  # imported by every proof of the node
        ("targets/t1/nodes/n/attempts/x.yaml", "t1", True),  # an annex a skeleton may cite
        ("targets/t1/gate-spec.json", "t1", True),  # its pin
        ("targets/t2/nodes/n/Proof.lean", "t1", False),  # another target cannot change its verdict
        ("targets/t2/gate-spec.json", "t1", False),
        ("targets/t1/graph.json", "t1", False),  # rendered by the post-merge job
        ("targets/t1/.tags-cache.json", "t1", False),
        ("targets/t1/.footprint-cache.json", "t1", False),  # F18's backfill and products
        ("targets/t1/glosses.json", "t1", False),  # F20's product
        ("targets/t1/outlines/" + "a" * 64 + ".json", "t1", False),  # F19-T4's outline job
        ("targets/t1/outlines", "t1", True),  # a file named outlines is not the directory
        ("targets/t1/nodes/n/CONTEXT.json", "t1", False),
        ("targets/index.json", "t1", False),
        ("frontier.json", "t1", False),
        ("info.json", "t1", False),
        ("claims.json", "t1", False),
        ("THIRD_PARTY_NOTICES.md", "t1", False),
        ("attestations/000123.json", "t1", False),
        ("ledger/agent.json", "t1", False),
        ("AGENTS.md", "t1", False),  # the guide: no gate reads it
        ("README.md", "t1", False),
        ("curators.json", "t1", True),  # shared inputs reach every lane
        ("policy.json", "t1", True),
        ("keys/gate.pub", "t1", True),
        ("schemas/meta/v5.json", "t1", True),
        (".github/workflows/gate.yml", "t1", True),
        ("targets/t2/nodes/n/Proof.lean", None, True),  # no lane: every input counts
        ("targets/t2/graph.json", None, False),  # but never a product
    ],
)
def test_a_change_counts_against_a_lane_only_if_it_can_change_its_verdict(
    pick: dict[str, Any], path: str, lane: str | None, counts: bool
) -> None:
    assert pick["gates_on"](path, lane) is counts


def test_a_pull_requests_lane_is_the_one_target_it_touches(pick: dict[str, Any]) -> None:
    lane_of = pick["lane_of_paths"]
    assert lane_of(["targets/t1/nodes/n/Proof.lean"]) == "t1"
    assert lane_of(["targets/t1/nodes/n/Proof.lean", "targets/t1/nodes/n/attempts/a.yaml"]) == "t1"
    assert lane_of(["targets/t1/a", "targets/t2/b"]) is None  # refused by the gate anyway
    assert lane_of(["policy.json"]) is None  # a curator's switch: every lane
    assert lane_of(["targets/t1/a", "curators.json"]) is None
    # restated by F07-T62: an empty diff was None, a pull request in no lane, which closes every
    # lane when it is first; it changes nothing another lane is gated against, so it has its own
    assert lane_of([]) == pick["EMPTY_LANE"] and lane_of([]) is not None


def test_stale_counts_only_the_commits_that_reach_the_lane(pick: dict[str, Any]) -> None:
    count = pick["stale_count"]
    bot = ["frontier.json", "targets/t1/graph.json", "targets/t2/graph.json", "ledger/a.json"]
    other = ["targets/t2/nodes/m/Proof.lean"]
    own = ["targets/t1/nodes/n/attempts/x.yaml"]
    assert count([bot, other, bot], "t1") == 0
    assert count([bot, own, other, own], "t1") == 2
    assert count([["curators.json"], other], "t1") == 1
    assert count([], "t1") == 0
    assert count(None, "t1") > 0, "a history the actor could not read updates the branch"
    assert count([other], None) == 1  # no lane: any input counts


def test_main_is_read_back_along_its_first_parent_line_to_the_merge_base(
    pick: dict[str, Any],
) -> None:
    history = {
        "m3": (["frontier.json"], ["m2", "x"]),
        "m2": (["targets/t2/a"], ["m1", "y"]),
        "m1": (["targets/t1/b"], ["base"]),
    }
    since = pick["main_since"]
    assert since("base", "m3", history.__getitem__) == [
        ["frontier.json"],
        ["targets/t2/a"],
        ["targets/t1/b"],
    ]
    assert since("m3", "m3", history.__getitem__) == []
    assert since("base", "m3", history.__getitem__, limit=2) is None
    unreadable = {**history, "m2": (None, ["m1"])}
    assert since("base", "m3", unreadable.__getitem__) is None


def test_a_commits_files_are_read_page_by_page_and_a_rename_counts_twice(
    pick: dict[str, Any],
) -> None:
    pages = {
        1: {"parents": [{"sha": "p"}], "files": [{"filename": f"f{i}"} for i in range(100)]},
        2: {"files": [{"filename": "new", "previous_filename": "old"}]},
    }

    def read(path: str) -> dict[str, Any]:
        return pages[int(path.rsplit("page=", 1)[1])]

    paths, first = pick["paged_files"]("repos/o/g/commits/c", read)
    assert len(paths) == 102 and paths[-2:] == ["new", "old"]
    assert first["parents"] == [{"sha": "p"}]
    full = {"files": [{"filename": "x"}] * 100}
    paths, _first = pick["paged_files"]("repos/o/g/commits/c", lambda _p: full)
    assert paths is None, "past the host's cap the list is unreadable, not complete"


# --- one step in every lane ----------------------------------------------------------------------


def test_two_targets_merge_in_one_run_behind_main(pick: dict[str, Any]) -> None:
    """Both green, both behind main by the other's commits only: both merge, neither updated."""
    pulls = [pull(1, "submit/a"), pull(2, "submit/b")]
    got = lanes(pick, pulls, {1: green(), 2: green()}, {1: "t1", 2: "t2"})
    assert got == [(1, sha(pulls, 1), "merge"), (2, sha(pulls, 2), "merge")]


def test_within_a_target_it_is_one_at_a_time(pick: dict[str, Any]) -> None:
    pulls = [pull(1, "submit/a"), pull(2, "propose/b"), pull(3, "submit/c")]
    got = lanes(pick, pulls, {1: green(), 2: green(), 3: green()}, {1: "t1", 2: "t1", 3: "t2"})
    assert got == [(1, sha(pulls, 1), "merge"), (3, sha(pulls, 3), "merge")]


def test_a_pull_request_stale_on_its_own_target_is_updated_and_others_go_on(
    pick: dict[str, Any],
) -> None:
    pulls = [pull(1, "submit/a"), pull(2, "submit/b")]
    got = lanes(pick, pulls, {1: green(), 2: green()}, {1: "t1", 2: "t2"}, stale={1: 1})
    assert got == [(1, sha(pulls, 1), "update"), (2, sha(pulls, 2), "merge")]


def test_a_gating_pull_request_holds_its_own_lane_only(pick: dict[str, Any]) -> None:
    """T31 per target: nothing on t1 is merged past #1 while its gate runs; t2 goes on."""
    pulls = [pull(1, "submit/a"), pull(2, "append/b"), pull(3, "submit/c")]
    got = lanes(pick, pulls, {1: gating(), 2: green(), 3: green()}, {1: "t1", 2: "t1", 3: "t2"})
    assert got == [(1, sha(pulls, 1), "hold"), (3, sha(pulls, 3), "merge")]


def test_an_unknown_mergeability_holds_its_own_lane_only(pick: dict[str, Any]) -> None:
    pulls = [pull(1, "submit/a"), pull(2, "submit/b")]
    got = lanes(pick, pulls, {1: green(), 2: green()}, {1: "t1", 2: "t2"}, conflicts={1: None})
    assert got == [(1, sha(pulls, 1), "hold"), (2, sha(pulls, 2), "merge")]


def test_a_conflict_passes_over_and_the_next_in_its_lane_is_taken(pick: dict[str, Any]) -> None:
    pulls = [pull(1, "submit/a"), pull(2, "submit/b")]
    got = lanes(pick, pulls, {1: green(), 2: green()}, {1: "t1", 2: "t1"}, conflicts={1: True})
    assert got == [(2, sha(pulls, 2), "merge")]


def test_appends_batch_within_their_lane_and_the_cap_spans_the_run(pick: dict[str, Any]) -> None:
    cap = int(pick["MAX_BATCH"])
    t1 = [pull(10 + i, f"append/a{i}") for i in range(cap - 2)]
    t2 = [pull(50 + i, f"append/b{i}") for i in range(4)]
    pulls = t1 + t2
    checks = {p["number"]: green() for p in pulls}
    targets: dict[int, str | None] = {p["number"]: "t1" for p in t1}
    targets.update({p["number"]: "t2" for p in t2})
    got = lanes(pick, pulls, checks, targets)
    assert [n for n, _s, a in got if a == "merge"] == [p["number"] for p in t1] + [50, 51]
    assert len(got) == cap


def test_first_in_first_out_holds_within_a_lane_not_across(pick: dict[str, Any]) -> None:
    """T45's batch still ends at a green building pull request of its own lane; another lane's
    building pull request neither ends it nor waits for it."""
    pulls = [pull(1, "append/a"), pull(2, "submit/p"), pull(3, "append/c"), pull(4, "submit/q")]
    targets: dict[int, str | None] = {1: "t1", 2: "t1", 3: "t1", 4: "t2"}
    got = lanes(pick, pulls, {n: green() for n in (1, 2, 3, 4)}, targets)
    assert got == [(1, sha(pulls, 1), "merge"), (4, sha(pulls, 4), "merge")]


def test_a_pull_request_in_no_lane_waits_until_it_is_first_and_then_holds_every_lane(
    pick: dict[str, Any],
) -> None:
    pulls = [pull(1, "submit/a"), pull(2, "propose/policy"), pull(3, "submit/c")]
    checks = {n: green() for n in (1, 2, 3)}
    got = lanes(pick, pulls, checks, {1: "t1", 2: None, 3: "t2"})
    assert got == [(1, sha(pulls, 1), "merge"), (3, sha(pulls, 3), "merge")]
    got = lanes(pick, pulls[1:], checks, {2: None, 3: "t2"})
    assert got == [(2, sha(pulls, 2), "merge")]


def test_without_lanes_the_queue_is_the_single_line_it_was(pick: dict[str, Any]) -> None:
    pulls = [pull(1, "submit/a"), pull(2, "submit/b")]
    by_sha = {p["head"]["sha"]: p["number"] for p in pulls}
    got = pick["decide_lanes"](
        pulls, RULES, lambda s: green(), lambda s: 0, lambda n: False, now=NOW
    )  # fmt: skip
    assert got == [(1, sha(pulls, 1), "merge")], by_sha


def test_a_pull_request_behind_on_its_lane_while_it_gates_is_waited_on_and_holds_nothing(
    pick: dict[str, Any],
) -> None:
    """Found by the replay: a merge's own bot commit can put the next pull request in its lane
    behind while that one re-gates. T31 says it holds nothing, and the one after it may go; but
    the run must read its gate again, or a wake that arrives before the host reports the check
    (T32) decides "nothing" and strands it until some other wake."""
    pulls = [pull(1, "submit/a"), pull(2, "append/b")]
    got = lanes(pick, pulls, {1: gating(), 2: green()}, {1: "t1", 2: "t1"}, stale={1: 1})
    assert got == [(1, sha(pulls, 1), "wait"), (2, sha(pulls, 2), "merge")]
    assert pick["acts"](got) == [(2, sha(pulls, 2), "merge")]
    got = lanes(pick, pulls[:1], {1: gating()}, {1: "t1"}, stale={1: 1})
    assert got == [(1, sha(pulls, 1), "wait")]
    answers = iter([got, got, [(1, sha(pulls, 1), "update")]])
    slept: list[float] = []
    settled = pick["settle"](lambda: next(answers), slept.append, clock=lambda: 0)
    assert settled == [(1, sha(pulls, 1), "update")] and len(slept) == 2


def test_a_run_settles_only_while_every_lane_holds(pick: dict[str, Any]) -> None:
    answers = iter(
        [
            [(1, "a", "hold")],
            [(1, "a", "hold"), (2, "b", "merge")],
        ]
    )
    slept: list[float] = []
    got = pick["settle"](lambda: next(answers), slept.append, clock=lambda: 0)
    assert got == [(1, "a", "hold"), (2, "b", "merge")] and len(slept) == 1
    assert pick["acts"](got) == [(2, "b", "merge")]


# --- the replay ---------------------------------------------------------------------------------


def targeted(arrivals: dict[int, tuple[Any, ...]], every: int) -> dict[int, tuple[Any, ...]]:
    """The same arrivals, spread over `every` targets in turn."""
    out = {}
    for i, (when, (number, ref, gate_s)) in enumerate(sorted(arrivals.items())):
        out[when] = (number, ref, gate_s, f"t{i % every}")
    return out


def test_two_mathlib_proofs_on_two_targets_merge_in_one_round(
    pick: dict[str, Any], gate_doc: dict[Any, Any]
) -> None:
    """As it stood the second was behind the moment the first merged, waited for the first's
    post-merge job, and then paid a second three-minute gate round."""
    w = world(pick, gate_doc, {5: (1, "submit/a", SLOW_S, "t1"), 10: (2, "submit/b", SLOW_S, "t2")})
    w.advance(3600)
    assert set(w.merged_at) == {1, 2}, (w.open, w.log)
    assert max(w.merged_at.values()) <= 10 + SLOW_S + CHECK_LAG_S + 60, (w.merged_at, w.log)
    assert w.updates == [], "nothing was updated: neither moved the other's target"


def test_two_proofs_on_one_target_are_still_one_at_a_time(
    pick: dict[str, Any], gate_doc: dict[Any, Any]
) -> None:
    """The second is gated again on a tree that holds the first before it merges: the safe
    choice now that a proof may import another node's proved lemma."""
    w = world(pick, gate_doc, {5: (1, "submit/a", SLOW_S, "t1"), 10: (2, "submit/b", SLOW_S, "t1")})
    w.advance(3600)
    assert set(w.merged_at) == {1, 2}, (w.open, w.log)
    assert 2 in w.updates, w.log
    assert w.merged_at[2] > w.merged_at[1] + SLOW_S, (w.merged_at, w.log)


def test_no_merge_waits_for_a_post_merge_job(
    pick: dict[str, Any], gate_doc: dict[Any, Any]
) -> None:
    """F07-T55 keeps the record when main moves under a post-merge job, so the queue no longer
    waits for one: here merges land while earlier merges' jobs are still committing."""
    arrivals = {5 + 20 * i: (40 + i, f"append/a{i}", FAST_S, f"t{i}") for i in range(4)}
    arrivals[3] = (39, "submit/p", SLOW_S, "t9")
    w = world(pick, gate_doc, arrivals)
    w.advance(3600)
    assert w.open == {}, w.log
    under = [
        n
        for n, at in w.merged_at.items()
        if any(m != n and w.merged_at[m] < at < w.merged_at[m] + BOT_S for m in w.merged_at)
    ]
    assert under, f"every merge waited for the one before it: {w.merged_at}"


def test_the_afternoon_of_148_drains_faster_over_targets_than_in_one_line(
    pick: dict[str, Any], gate_doc: dict[Any, Any]
) -> None:
    one_line = world(pick, gate_doc, the_afternoon_of_148())
    one_line.advance(4 * 3600)
    over_targets = world(pick, gate_doc, targeted(the_afternoon_of_148(), 5))
    over_targets.advance(4 * 3600)
    assert one_line.open == {} and over_targets.open == {}, (one_line.log, over_targets.log)
    assert max(over_targets.merged_at.values()) < max(one_line.merged_at.values()), (
        over_targets.merged_at,
        one_line.merged_at,
    )
    building = [n for n, (_n, ref, *_r) in the_afternoon_of_148().items() if ref.startswith("s")]
    assert building  # the afternoon has building pull requests for the lanes to overlap


def test_every_building_merge_was_up_to_date_on_its_own_target(
    pick: dict[str, Any], gate_doc: dict[Any, Any]
) -> None:
    """``World.act`` asserts it on every merge; this drives enough of them to matter."""
    w: World = world(pick, gate_doc, targeted(the_afternoon_of_148(), 3))
    w.advance(4 * 3600)
    assert w.open == {}, w.log
    assert w.behind_merges, "some building pull requests merged behind main"


# --- the acting step, run as it stands with a fake host ----------------------------------------


FAKE_GH = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$GH_LOG"
if [ -n "${GH_FAIL:-}" ] && printf '%s' "$*" | grep -q -- "$GH_FAIL"; then exit 1; fi
exit 0
"""


def run_act(
    doc: dict[Any, Any], tmp_path: Path, number: str, sha_: str, action: str, *, fail: str = ""
) -> tuple[int, list[str], str]:
    (act,) = [s for s in doc["jobs"]["merge"]["steps"] if s.get("name", "").startswith("Act")]
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    gh = bin_dir / "gh"
    gh.write_text(FAKE_GH, encoding="utf-8")
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    log = tmp_path / "gh.log"
    log.write_text("", encoding="utf-8")
    output = tmp_path / "output"
    output.write_text("", encoding="utf-8")
    env = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "GH_LOG": str(log),
        "GH_FAIL": fail,
        "GH_TOKEN": "fake",
        "REPO": "owner/graph",
        "NUMBER": number,
        "SHA": sha_,
        "ACTION": action,
        "GITHUB_OUTPUT": str(output),
    }
    proc = subprocess.run(
        ["bash", "-c", str(act["run"])], capture_output=True, text=True, check=False, env=env
    )
    calls = [line for line in log.read_text().splitlines() if line]
    return proc.returncode, calls, output.read_text()


def merge_call(n: int) -> str:
    return f"api -X PUT repos/owner/graph/pulls/{n}/merge -f sha=a{n} -f merge_method=merge"


def update_call(n: int) -> str:
    return f"api -X PUT repos/owner/graph/pulls/{n}/update-branch -f expected_head_sha=a{n}"


def test_one_run_merges_and_updates_across_lanes(doc: dict[Any, Any], tmp_path: Path) -> None:
    code, calls, output = run_act(doc, tmp_path, "5 6 7", "a5 a6 a7", "merge update merge")
    assert code == 0, calls
    assert calls == [merge_call(5), update_call(6), merge_call(7)]
    assert "merged=2" in output


def test_a_refused_merge_is_updated_and_the_other_lanes_go_on(
    doc: dict[Any, Any], tmp_path: Path
) -> None:
    code, calls, output = run_act(
        doc, tmp_path, "5 6 7", "a5 a6 a7", "merge merge merge", fail="pulls/6/merge"
    )
    assert code == 0
    assert calls == [merge_call(5), merge_call(6), update_call(6), merge_call(7)]
    assert "merged=2" in output
    code, calls, _ = run_act(doc, tmp_path, "5 6", "a5 a6", "merge merge", fail="pulls/5/")
    assert code != 0 and calls == [merge_call(5), update_call(5), merge_call(6)]


def test_misaligned_outputs_act_on_nothing(doc: dict[Any, Any], tmp_path: Path) -> None:
    code, calls, _ = run_act(doc, tmp_path, "5 6", "a5", "merge merge")
    assert code != 0 and calls == []


def test_a_run_that_merged_wakes_the_actor_again(doc: dict[Any, Any]) -> None:
    """The next pull request in a lane whose head merged is updated at once, not when the
    post-merge job's wake arrives minutes later."""
    rewake = doc["jobs"]["rewake"]
    assert "failure()" in rewake["if"] and "needs.merge.outputs.merged" in rewake["if"]
    assert doc["jobs"]["merge"]["outputs"]["merged"] == "${{ steps.act.outputs.merged }}"
    assert rewake["permissions"] == {"actions": "write"}


def test_the_actor_reads_no_post_merge_run_and_no_contributor_file(
    doc: dict[Any, Any],
) -> None:
    (step,) = [s for s in doc["jobs"]["merge"]["steps"] if s.get("id") == "pick"]
    script = str(step["run"])
    assert "postmerge_running" not in script and "actions/runs" not in script
    assert "actions" not in doc["jobs"]["merge"]["permissions"]
    # the lane is read from the host's list of a pull request's paths, never from its content
    assert "pulls/{number}/files" in script and "compare/{sha}...{main}" in script
    assert "contents/" not in script and "raw.githubusercontent" not in script
    assert "lane_of=lane_of" in script and "tip_of=tip" in script


def test_a_decision_reads_each_pull_requests_staleness_once(doc: dict[Any, Any]) -> None:
    """``decide`` asks ``behind_of`` up to three times for one pull request, every SETTLE_EVERY_S
    for up to SETTLE_CAP_S, and each ask is a compare call against an hourly token budget."""
    (step,) = [s for s in doc["jobs"]["merge"]["steps"] if s.get("id") == "pick"]
    script = str(step["run"])
    assert "stale = {}" in script and "if sha not in stale:" in script
    assert script.count("compare/{sha}...{main}") == 1
