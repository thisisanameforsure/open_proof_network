"""F07-T81, T82: words and reports do not churn a target's proofs (the 2026-11-19 run, finding B1).

On 2026-11-19 nine agents worked three targets for two hours. Within one target's lane every merge
put every queued building pull request (a proof, a partial, an alternate, a proposal, a witness)
behind, so it was updated and paid another three-to-five-minute gate round: #1552 went green at
least six times and #1557 three times before either merged. Appends (postmortems, explainers,
glosses, literature) that were green within a minute waited 20 to 50 minutes behind them, because
a lane takes one step at a time and closes on any building pull request's update or hold.

T81: a path in the pull request's own target whose D-3 role is a words or report append no
building verdict reads (``inert_role``) no longer counts against the lane, so a postmortem merged
ahead of a proof leaves the proof up to date. T82: such appends have a sub-lane of their own in
each target, so a building pull request holding, updating or merging closes only the building
sub-lane, and a batch of appends closes only theirs.

The decision program is the heredoc ``merge.yml`` writes to ``pick.py``, run as it stands; the
replays are ``test_finding_merge_actor_wakes.py``'s host, with every commit on main carrying the
paths it changed, so staleness is the actor's own ``stale_count`` over real paths.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

import pytest
from test_finding_merge_actor_wakes import (
    ANY,
    CHECK_LAG_S,
    FAST_S,
    PRODUCTS,
    SLOW_S,
    T0,
    World,
    load_gate_doc,
    postmerge_wakes_the_actor,
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

from opn_gate import paths

NOW = T0 + timedelta(hours=1)
HASH = "a" * 64


@pytest.fixture(scope="module")
def doc() -> dict[Any, Any]:
    return load_doc()


@pytest.fixture(scope="module")
def pick(doc: dict[Any, Any]) -> dict[str, Any]:
    return load_pick(doc)


@pytest.fixture(scope="module")
def gate_doc() -> dict[Any, Any]:
    return load_gate_doc()


# --- the paths: the actor's grammar against the gate's ------------------------------------------

#: The roles T81 accepts as inert, each checked against the gate before it was accepted
#: (``engineering/evidence/F07/task-81.txt``): no step, no building mode's check, ``closure``,
#: ``graph.load_target`` (and ``shelved_refusal`` through it) or the post-merge re-check opens one.
INERT = frozenset(
    {
        "postmortem",
        "precheck-record",
        "explainer",
        "explainer-signature",
        "gloss",
        "gloss-signature",
        "approach-record",
        "literature",
    }
)

SAMPLES = [
    # inert, each role
    "targets/t1/nodes/n/attempts/20261119T133543Z-agent.yaml",
    "targets/t1/nodes/n/attempts/20261119T133543Z-agent.yml",
    "targets/t1/nodes/n/attempts/precheck/abc.json",
    f"targets/t1/nodes/n/explainer/{HASH}.md",
    f"targets/t1/nodes/n/explainer/signed/{HASH}-1.yaml",
    f"targets/t1/nodes/n/gloss/{HASH}.md",
    f"targets/t1/nodes/n/gloss/signed/{HASH}-1.yaml",
    f"targets/t1/gloss/{HASH}.md",
    f"targets/t1/gloss/signed/{HASH}-2.yml",
    "targets/t1/approaches/route-a.yaml",
    "targets/t1/nodes/n/literature/20261119T140000Z-agent.yaml",
    "targets/erdos-1094/nodes/erdos-1094--h2--h1/attempts/20261119T1-x.yaml",
    # near misses: building artifacts that sit beside them
    "targets/t1/nodes/n/attempts/20261119T133543Z-agent.lean",  # a partial
    "targets/t1/nodes/n/attempts/20261119T133543Z-agent-alternate.lean",  # an alternate
    "targets/t1/nodes/n/attempts/20261119T133543Z-agent.1.witness",  # a carried witness
    "targets/t1/nodes/n/attempts/20261119T133543Z-agent.1.proof",  # a carried proof
    "targets/t1/nodes/n/attempts/precheck/abc.yaml",  # a precheck record is JSON
    "targets/t1/nodes/n/attempts/precheck/sub/abc.json",
    "targets/t1/nodes/n/attempts/sub/x.yaml",  # nested
    "targets/t1/nodes/n/attempts/.yaml",  # a hidden file, no suffix
    "targets/t1/nodes/n/attempts/.gitkeep",
    "targets/t1/nodes/n/explainer/.gitkeep",
    f"targets/t1/nodes/n/explainer/{HASH}.yaml",
    f"targets/t1/nodes/n/explainer/signed/{HASH}.md",
    f"targets/t1/nodes/n/explainer/signed/x/{HASH}-1.yaml",
    f"targets/t1/nodes/n/gloss/x/{HASH}.md",
    "targets/t1/nodes/n/literature/x.md",
    "targets/t1/nodes/n/literature/sub/x.yaml",
    "targets/t1/approaches/route-a.md",
    "targets/t1/approaches/sub/route-a.yaml",
    f"targets/t1/defs/gloss/{HASH}.md",
    f"targets/t1/defs/{HASH}.md",
    # what keeps counting: the annex a skeleton cites, records, the node, the target's own files
    f"targets/t1/nodes/n/annex/{HASH}.md",
    "targets/t1/nodes/n/Proof.lean",
    "targets/t1/nodes/n/Statement.lean",
    "targets/t1/nodes/n/Context.lean",
    "targets/t1/nodes/n/META.yaml",
    "targets/t1/nodes/n/Witness.lean",
    "targets/t1/nodes/n/Relation.lean",
    "targets/t1/nodes/n/waivers/native_decide.yaml",
    "targets/t1/nodes/n/status/x.yaml",
    "targets/t1/nodes/n/revisions/x.yaml",
    "targets/t1/nodes/n/defects/x.yaml",
    "targets/t1/nodes/n/withdrawals/x.yaml",
    "targets/t1/nodes/n/proposed-for/x.yaml",
    "targets/t1/nodes/n/shelving/x.yaml",
    "targets/t1/nodes/n/relevance.yaml",
    "targets/t1/review/review.yaml",
    "targets/t1/review/pair-proofs/a--b--forward--x.yaml",
    "targets/t1/review/signatures/intent-2026-11-19-1.yaml",
    "targets/t1/stewards/1.yaml",
    "targets/t1/status/root.yaml",
    "targets/t1/withdrawals/x.yaml",
    "targets/t1/target.yaml",
    "targets/t1/gate-spec.json",
    "targets/t1/defs/Fact.lean",
    "targets/t1/fidelity/root-1.yaml",
    "targets/t1/motions/1.yaml",
    "targets/t1/registrations/2026-11-19-1.yaml",
    # ids the grammar refuses
    "targets/T1/nodes/n/attempts/x.yaml",
    "targets/t1/nodes/N/attempts/x.yaml",
    "targets/-t/approaches/a.yaml",
    "targets/t1/nodes//attempts/x.yaml",
    # outside any target
    "policy.json",
    "names/agent.yaml",
    "attempts/x.yaml",
    "targets/approaches/a.yaml",
]


def gate_inert(path: str) -> str | None:
    located = paths.locate(path)
    return located.role if located is not None and located.role in INERT else None


@pytest.mark.parametrize("path", SAMPLES)
def test_the_actors_words_grammar_agrees_with_the_gates(pick: dict[str, Any], path: str) -> None:
    """``pick.py`` cannot import the gate, so it carries its own grammar; this holds it to
    ``opn_gate.paths.locate`` on every sample, inert or not, near misses included."""
    assert pick["inert_role"](path) == gate_inert(path)


def test_every_inert_role_is_an_append_role(pick: dict[str, Any]) -> None:
    """Every role T81 accepts claims nothing (``APPEND_ROLES``) or is words (D-3's explainers and
    glosses); and every one of them occurs in the samples, so the parity test reaches it."""
    words = {"explainer", "explainer-signature", "gloss", "gloss-signature"}
    assert set(paths.APPEND_ROLES) | words >= INERT
    assert {gate_inert(p) for p in SAMPLES} - {None} == INERT
    assert "annex" not in INERT and "shelving" not in INERT  # read by building verdicts


@pytest.mark.parametrize(
    ("path", "lane", "counts"),
    [
        ("targets/t1/nodes/n/attempts/x.yaml", "t1", False),  # a postmortem
        ("targets/t1/nodes/n/attempts/precheck/x.json", "t1", False),
        (f"targets/t1/nodes/n/explainer/{HASH}.md", "t1", False),
        (f"targets/t1/nodes/n/gloss/signed/{HASH}-1.yaml", "t1", False),
        (f"targets/t1/gloss/{HASH}.md", "t1", False),
        ("targets/t1/approaches/a.yaml", "t1", False),
        ("targets/t1/nodes/n/literature/x.yaml", "t1", False),
        ("targets/t1/nodes/n/attempts/x.lean", "t1", True),  # a partial still counts
        (f"targets/t1/nodes/n/annex/{HASH}.md", "t1", True),  # a skeleton may cite it
        ("targets/t1/nodes/n/shelving/x.yaml", "t1", True),  # shelved_refusal reads it
        ("targets/t1/nodes/n/attempts/x.yaml", None, True),  # no lane: as before
    ],
)
def test_words_and_reports_do_not_count_against_their_lane(
    pick: dict[str, Any], path: str, lane: str | None, counts: bool
) -> None:
    assert pick["gates_on"](path, lane) is counts


# --- the replay, with paths ----------------------------------------------------------------------

POSTMORTEM = "targets/{t}/nodes/n{k}/attempts/20261119T1{k:05d}Z-agent.yaml"
EXPLAINER = "targets/{t}/nodes/n{k}/explainer/{k:064d}.md"
ANNEX = "targets/{t}/nodes/n{k}/annex/{k:064d}.md"
PROOF = "targets/{t}/nodes/n{k}/Proof.lean"


@dataclass
class PathWorld(World):
    """``World`` with every commit on main carrying the paths it changed, so a pull request's
    staleness is the actor's own ``stale_count`` over them, and every pull request its files."""

    files: dict[int, list[str]] = field(default_factory=dict)
    commit_paths: dict[int, list[str]] = field(default_factory=dict)  # main's index: its paths
    sublanes: bool = True  # F07-T82: tell the actor which appends are words alone
    gate_runs: dict[int, int] = field(default_factory=dict)  # gate rounds per pull request

    def behind_of(self, sha: str) -> int:
        pr = self.by_sha(sha)
        walk = []
        for i in range(pr.based_on, self.main):
            touched = self.touched[i]
            if i in self.commit_paths:
                walk.append(self.commit_paths[i])
            elif touched == ANY:
                walk.append(["curators.json"])
            elif touched == PRODUCTS:
                walk.append(["frontier.json", f"targets/{pr.target}/graph.json"])
            else:  # a building merge's bot commit: the node's status, beside the products
                walk.append([f"targets/{touched}/nodes/n0/META.yaml", "frontier.json"])
        count: int = self.pick["stale_count"](walk, pr.target)
        return count

    def decide(self) -> list[tuple[int, str, str]]:
        kw: dict[str, Any] = {}
        if self.sublanes and "inert_of" in inspect.signature(self.pick["decide_lanes"]).parameters:
            kw["inert_of"] = self.inert_of
        decided: list[tuple[int, str, str]] = self.pick["decide_lanes"](
            self.pulls(),
            RULES,
            self.checks_of,
            self.behind_of,
            now=T0 + timedelta(seconds=self.now),
            lane_of=lambda number: self.open[number].target,
            **kw,
        )
        return decided

    def inert_of(self, number: int) -> bool:
        return all(self.pick["inert_role"](p) for p in self.files[number])

    def act(self, acted: list[tuple[int, str, str]]) -> None:
        merged = [n for n, _s, a in acted if a == "merge"]
        for number, _sha, action in acted:
            if action == "update":
                self.gate_runs[number] = self.gate_runs.get(number, 1) + 1
        before = self.main
        super().act(acted)
        for i, number in enumerate(merged):
            self.commit_paths[before + i] = self.files[number]


def path_world(
    pick: dict[str, Any],
    gate_doc: dict[Any, Any],
    arrivals: dict[int, tuple[int, str, int, str, list[str]]],
    *,
    sublanes: bool = True,
) -> PathWorld:
    w = PathWorld(pick, postmerge_wakes_the_actor(gate_doc), sublanes=sublanes)
    for when, (number, ref, gate_s, target, files) in arrivals.items():
        w.arrivals[when] = (number, ref, gate_s, target)
        w.files[number] = files
    return w


def test_a_postmortem_merged_ahead_of_a_proof_does_not_re_gate_it(
    pick: dict[str, Any], gate_doc: dict[Any, Any]
) -> None:
    """B1's acceptance: on a fixture target, with proof P queued behind append A, merging A does
    not change P's head or trigger a new gate run on P."""
    arrivals = {
        5: (1, "append/a", FAST_S, "t1", [POSTMORTEM.format(t="t1", k=1)]),
        10: (2, "submit/p", SLOW_S, "t1", [PROOF.format(t="t1", k=2)]),
    }
    w = path_world(pick, gate_doc, arrivals)
    w.advance(3600)
    assert set(w.merged_at) == {1, 2}, (w.open, w.log)
    assert w.merged_at[1] < w.merged_at[2], "the append merged first, ahead of the proof"
    assert 2 not in w.updates, f"the proof was updated after the postmortem merged: {w.log}"
    assert w.merged_at[2] <= 10 + SLOW_S + CHECK_LAG_S + 60, (w.merged_at, w.log)


def test_an_annex_merged_ahead_of_a_proof_still_re_gates_it(
    pick: dict[str, Any], gate_doc: dict[Any, Any]
) -> None:
    """What keeps counting keeps counting: an annex is read by a skeleton's step 2 (F07-T27), so
    a building pull request behind one is updated before it merges."""
    arrivals = {
        5: (1, "append/a", FAST_S, "t1", [ANNEX.format(t="t1", k=1)]),
        10: (2, "submit/p", SLOW_S, "t1", [PROOF.format(t="t1", k=2)]),
    }
    w = path_world(pick, gate_doc, arrivals)
    w.advance(3600)
    assert set(w.merged_at) == {1, 2}, (w.open, w.log)
    assert 2 in w.updates, w.log


def test_a_decision_leaves_a_proof_up_to_date_behind_a_postmortem(pick: dict[str, Any]) -> None:
    """The rule alone: main moved by a postmortem and a bot commit on the proof's target."""
    walk = [["frontier.json", "targets/t1/graph.json"], [POSTMORTEM.format(t="t1", k=1)]]
    assert pick["stale_count"](walk, "t1") == 0
    walk.append([PROOF.format(t="t1", k=3)])
    assert pick["stale_count"](walk, "t1") == 1
    green = [check(GATE_JOB, "success"), check(STEP9_JOB, "skipped", id_=2)]
    pulls = [pull(2, "submit/p")]
    got = pick["decide_lanes"](
        pulls,
        RULES,
        lambda _s: green,
        lambda _s: pick["stale_count"](walk[:2], "t1"),
        now=NOW,
        lane_of=lambda _n: "t1",
    )
    assert got == [(2, pulls[0]["head"]["sha"], "merge")]


# --- F07-T82: an append sub-lane in each target --------------------------------------------------


def green() -> list[dict[str, Any]]:
    return [check(GATE_JOB, "success"), check(STEP9_JOB, "skipped", id_=2)]


def gating() -> list[dict[str, Any]]:
    stamp = (NOW - timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
    return [{**check(GATE_JOB, None), "started_at": stamp}, check(STEP9_JOB, None, id_=2)]


def sublanes(
    pick: dict[str, Any],
    pulls: list[dict[str, Any]],
    checks: dict[int, list[dict[str, Any]]],
    targets: dict[int, str | None],
    inert: set[int],
    *,
    stale: dict[int, int] | None = None,
    words_moved: set[int] | None = None,
) -> list[tuple[int, str, str]]:
    by_sha = {p["head"]["sha"]: p["number"] for p in pulls}
    decided: list[tuple[int, str, str]] = pick["decide_lanes"](
        pulls,
        RULES,
        lambda sha: checks[by_sha[sha]],
        lambda sha: (stale or {}).get(by_sha[sha], 0),
        lambda _number: False,
        now=NOW,
        lane_of=targets.__getitem__,
        inert_of=lambda number: number in inert,
        words_moved=lambda number: number in (words_moved or set()),
    )
    return decided


def sha(pulls: list[dict[str, Any]], number: int) -> str:
    return str(next(p["head"]["sha"] for p in pulls if p["number"] == number))


def the_afternoon_of_1552(appends: int = 14) -> dict[int, tuple[int, str, int, str, list[str]]]:
    """2026-11-19's shape on one target: three proofs churning (each merge makes the others stale,
    so each is updated and gated again), a fourth arriving later, and words and reports arriving
    every ninety seconds from the agents working beside them."""
    out: dict[int, tuple[int, str, int, str, list[str]]] = {}
    for i, when in enumerate((5, 15, 25, 400)):
        out[when] = (1 + i, f"submit/p{i}", SLOW_S, "t1", [PROOF.format(t="t1", k=1 + i)])
    for i in range(appends):
        number = 20 + i
        shape = (POSTMORTEM, EXPLAINER)[i % 2]
        out[60 + 90 * i] = (number, f"append/a{i}", FAST_S, "t1", [shape.format(t="t1", k=number)])
    return out


def append_latency(w: PathWorld, arrivals: dict[int, Any]) -> dict[int, int]:
    """Seconds from the host first reporting each append green to its merge."""
    return {
        number: w.merged_at[number] - (when + gate_s + CHECK_LAG_S)
        for when, (number, ref, gate_s, *_rest) in arrivals.items()
        if ref.startswith("append/") and number in w.merged_at
    }


def test_a_green_append_merges_while_a_building_pull_request_gates(pick: dict[str, Any]) -> None:
    """A building pull request holding its target (T31) closes the building sub-lane only."""
    pulls = [pull(1, "submit/p"), pull(2, "append/a")]
    got = sublanes(pick, pulls, {1: gating(), 2: green()}, {1: "t1", 2: "t1"}, {2})
    assert got == [(1, sha(pulls, 1), "hold"), (2, sha(pulls, 2), "merge")]


def test_a_green_append_merges_while_a_building_pull_request_is_updated(
    pick: dict[str, Any],
) -> None:
    pulls = [pull(1, "submit/p"), pull(2, "append/a")]
    got = sublanes(pick, pulls, {1: green(), 2: green()}, {1: "t1", 2: "t1"}, {2}, stale={1: 1})
    assert got == [(1, sha(pulls, 1), "update"), (2, sha(pulls, 2), "merge")]


def test_a_batch_walks_its_own_sub_lane_past_a_green_building_pull_request(
    pick: dict[str, Any],
) -> None:
    """T45's batch ended at the first green building pull request; it is in the other sub-lane
    now, so the batch takes every green words append behind it, and it merges too."""
    pulls = [pull(1, "append/a"), pull(2, "submit/p"), pull(3, "append/b"), pull(4, "submit/q")]
    targets: dict[int, str | None] = {1: "t1", 2: "t1", 3: "t1", 4: "t1"}
    got = sublanes(pick, pulls, {n: green() for n in (1, 2, 3, 4)}, targets, {1, 3})
    assert got == [
        (1, sha(pulls, 1), "merge"),
        (3, sha(pulls, 3), "merge"),
        (2, sha(pulls, 2), "merge"),
    ], "one building step, and the batch beside it"


def test_an_append_a_building_verdict_can_read_stays_in_the_building_sub_lane(
    pick: dict[str, Any],
) -> None:
    """An annex, a review record or a shelving is an append the gate's building checks read: it
    still waits behind a building pull request's hold, and a building merge ends its batch."""
    pulls = [pull(1, "submit/p"), pull(2, "append/annex"), pull(3, "append/words")]
    got = sublanes(
        pick, pulls, {1: gating(), 2: green(), 3: green()}, dict.fromkeys((1, 2, 3), "t1"), {3}
    )
    assert got == [(1, sha(pulls, 1), "hold"), (3, sha(pulls, 3), "merge")]
    # and a words append's batch does not take it
    pulls = [pull(5, "append/words"), pull(6, "append/annex"), pull(7, "append/more")]
    checks = {n: green() for n in (5, 6, 7)}
    got = sublanes(pick, pulls, checks, dict.fromkeys((5, 6, 7), "t1"), {5, 7})
    assert got == [
        (5, sha(pulls, 5), "merge"),
        (7, sha(pulls, 7), "merge"),
        (6, sha(pulls, 6), "merge"),
    ]


def test_a_submit_branch_of_words_alone_is_still_a_building_one(pick: dict[str, Any]) -> None:
    """The sub-lane is the service's append branches: a building branch is never batched."""
    pulls = [pull(1, "submit/p"), pull(2, "submit/words")]
    got = sublanes(pick, pulls, {1: gating(), 2: green()}, {1: "t1", 2: "t1"}, {2})
    assert got == [(1, sha(pulls, 1), "hold")]


def test_a_pull_request_in_no_lane_still_closes_both_sub_lanes(pick: dict[str, Any]) -> None:
    pulls = [pull(1, "propose/policy"), pull(2, "append/a"), pull(3, "submit/p")]
    targets: dict[int, str | None] = {1: None, 2: "t1", 3: "t1"}
    got = sublanes(pick, pulls, {n: green() for n in (1, 2, 3)}, targets, {2})
    assert got == [(1, sha(pulls, 1), "merge")]
    # and it waits until it is first: an append ahead of it goes, and it does not
    pulls = [pull(2, "append/a"), pull(4, "propose/policy")]
    got = sublanes(pick, pulls, {2: green(), 4: green()}, {2: "t1", 4: None}, {2})
    assert got == [(2, sha(pulls, 2), "merge")]


def test_a_words_update_closes_only_the_append_sub_lane(pick: dict[str, Any]) -> None:
    """F22-T22's update of an append whose words moved holds its sub-lane, not the proof's."""
    pulls = [pull(1, "append/a"), pull(2, "append/b"), pull(3, "submit/p")]
    targets: dict[int, str | None] = dict.fromkeys((1, 2, 3), "t1")
    got = sublanes(pick, pulls, {n: green() for n in (1, 2, 3)}, targets, {1, 2}, words_moved={1})
    assert got == [(1, sha(pulls, 1), "update"), (3, sha(pulls, 3), "merge")]


def test_the_batch_cap_still_spans_the_run(pick: dict[str, Any]) -> None:
    cap = int(pick["MAX_BATCH"])
    words = [pull(10 + i, f"append/a{i}") for i in range(cap + 2)]
    pulls = [pull(1, "submit/p"), *words]
    checks = {p["number"]: green() for p in pulls}
    targets: dict[int, str | None] = {p["number"]: "t1" for p in pulls}
    got = sublanes(pick, pulls, checks, targets, {p["number"] for p in words})
    merged = [n for n, _s, a in got if a == "merge"]
    assert merged[0] == 1 and merged[1:] == [p["number"] for p in words[:cap]]


def test_the_run_tells_the_decision_which_appends_are_words_alone(doc: dict[Any, Any]) -> None:
    (step,) = [s for s in doc["jobs"]["merge"]["steps"] if s.get("id") == "pick"]
    script = str(step["run"])
    assert "inert_of=inert_of" in script
    assert "all(inert_role(path) for path in files)" in script and "bool(files)" in script


def test_a_green_append_merges_within_one_queue_tick(
    pick: dict[str, Any], gate_doc: dict[Any, Any]
) -> None:
    """B1's second acceptance criterion, on 2026-11-19's shape: one target, three proofs churning
    and a fourth later, words and reports arriving every ninety seconds. Every append merges
    within one tick of the host reporting it green, while the proofs are updated and gated
    beside it; the proofs still go one at a time, each up to date when it merges (``World.act``
    asserts that on every merge), and none is gated more often than before."""
    arrivals = the_afternoon_of_1552()
    w = path_world(pick, gate_doc, arrivals)
    w.advance(4 * 3600)
    assert w.open == {}, w.log
    latency = append_latency(w, arrivals)
    assert len(latency) == 14
    tick = int(pick["SETTLE_EVERY_S"]) + 2 * 5  # one decision again, and the wake and the tick
    assert max(latency.values()) <= tick, sorted(latency.items())
    assert w.updates, "the proofs still churned: the replay has building work beside the appends"
    one_lane = path_world(pick, gate_doc, arrivals, sublanes=False)
    one_lane.advance(4 * 3600)
    assert one_lane.open == {}
    assert w.gate_runs == one_lane.gate_runs, "no proof was gated more often"
