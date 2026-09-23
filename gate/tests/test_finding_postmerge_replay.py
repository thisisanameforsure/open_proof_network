"""F07-T33: nothing moves ``main`` under a post-merge job, and a merge whose job was lost is
replayed rather than re-rendered by hand (testers 2026-09-23; #145).

Read from the record: five merges since 2026-09-20 have no ``gate: #N`` commit — #125, #130,
#132, #133 and #145 — and every one failed the same way: F07-T29's push loop found ``main`` moved
under it and touched the products' inputs, and said "re-render by hand". Nobody did for #145, a
proof, so ``variant-d865c9c6`` has had a merged ``Proof.lean`` and no attestation for two days,
published as open and claimable. A re-render cannot help: the attestation needs the gate key, which
only CI holds.

What moved ``main`` each time was the merge actor. T31 held a building pull request's *update*
while a post-merge job ran and exempted appends, and never held a *merge*: an append updated in the
window re-gates in fifteen seconds and was merged while the previous job was still rendering, and
every service pull request touches ``targets/``. #145's job was refused by #142, merged three
minutes after it.
"""

from __future__ import annotations

from typing import Any

import pytest
from test_finding_merge_actor_wakes import (
    BOT_S,
    World,
    load_gate_doc,
    the_afternoon_of_148,
    world,
)
from test_finding_merge_actor_workflow import RULES, _text, check, load_doc, load_pick, pull

GATE_JOB = "gate (steps 1, 2 and 4-8 in the sandbox)"
STEP9_JOB = "step 9 (a non-author approving review)"


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


# --- the actor ------------------------------------------------------------------------------------


@pytest.mark.parametrize("ref", ["append/annex", "propose/variant", "submit/proof"])
def test_nothing_is_merged_while_a_post_merge_job_runs(pick: dict[str, Any], ref: str) -> None:
    """An up-to-date green pull request of any kind waits for the running job to commit."""
    pulls = [pull(142, ref)]
    got = pick["decide"](
        pulls, RULES, lambda _s: green(), lambda _s: 0, postmerge_running=lambda: True
    )
    assert got == ("", "", "hold"), (ref, got)


def test_an_append_is_not_updated_into_the_window_either(pick: dict[str, Any]) -> None:
    """Updating it would only make it green and up to date inside the window, to be held there;
    the round is spent after the job commits instead."""
    pulls = [pull(142, "append/annex")]
    got = pick["decide"](
        pulls, RULES, lambda _s: green(), lambda _s: 1, postmerge_running=lambda: True
    )
    assert got == ("", "", "hold")


def moved_under_a_job(w: World) -> list[int]:
    """Every merge that landed while an earlier merge's post-merge job had not committed."""
    lost = []
    for number, at in w.merged_at.items():
        for other, other_at in w.merged_at.items():
            if other != number and other_at < at < other_at + BOT_S:
                lost.append(other)
    return sorted(set(lost))


def test_the_afternoon_loses_no_post_merge_commit(
    pick: dict[str, Any], gate_doc: dict[Any, Any]
) -> None:
    w = world(pick, gate_doc, the_afternoon_of_148())
    w.advance(4 * 3600)
    assert w.open == {}, sorted(w.open)
    assert moved_under_a_job(w) == [], "these merges' post-merge jobs had main moved under them"


def test_a_replayed_post_merge_job_is_one_the_actor_waits_for(text: str) -> None:
    """A replay is the gate workflow on main by dispatch, not by push; the actor must see it."""
    assert 'for event in ("push", "workflow_dispatch")' in text
    assert "&event={event}&" in text


@pytest.fixture(scope="module")
def text() -> str:
    return _text()


# --- the replay -----------------------------------------------------------------------------------


def job(gate_doc: dict[Any, Any]) -> dict[str, Any]:
    postmerge: dict[str, Any] = gate_doc["jobs"]["postmerge"]
    return postmerge


def test_the_gate_workflow_can_be_asked_to_replay_one_merged_pull_request(
    gate_doc: dict[Any, Any],
) -> None:
    dispatch = gate_doc[True]["workflow_dispatch"]  # YAML reads `on` as True
    assert "replay_pr" in dispatch["inputs"]
    assert dispatch["inputs"]["replay_pr"]["required"] is True
    assert "workflow_dispatch" in job(gate_doc)["if"]
    # the pull-request jobs never run on it
    assert gate_doc["jobs"]["gate"]["if"] == "github.event_name == 'pull_request'"


def find_step(gate_doc: dict[Any, Any]) -> str:
    (step,) = [s for s in job(gate_doc)["steps"] if s.get("id") == "pr"]
    return str(step["run"])


def test_a_replay_takes_the_merge_commit_from_the_pull_request(gate_doc: dict[Any, Any]) -> None:
    run = find_step(gate_doc)
    assert "merge_commit_sha" in run and "merged_at" in run
    assert "merge=" in run  # the merge commit every later step reads


def test_a_replay_of_a_merge_that_has_its_commit_does_nothing(gate_doc: dict[Any, Any]) -> None:
    """Idempotent: the ledger appends, so a second run would credit the merge twice."""
    run = find_step(gate_doc)
    assert 'grep -q "^gate: #$number "' in run or "gate: #$number " in run, run


def test_every_step_reads_the_merge_commit_not_the_event_commit(gate_doc: dict[Any, Any]) -> None:
    """On a replay GITHUB_SHA is main's head; the merge is elsewhere."""
    steps = job(gate_doc)["steps"]
    for step in steps:
        if step.get("id") == "pr":
            continue
        run = str(step.get("run", ""))
        for command in ("classify", "cli postmerge", "cli ledger", "cache publish"):
            if command in run:
                assert "GITHUB_SHA" not in run, (step.get("name"), command)


def test_a_moved_main_dispatches_the_replay_instead_of_asking_for_hands(
    gate_doc: dict[Any, Any],
) -> None:
    (commit,) = [s for s in job(gate_doc)["steps"] if "git push" in str(s.get("run", ""))]
    run = str(commit["run"])
    assert "re-render by hand" not in run
    assert "gh workflow run gate.yml" in run and "replay_pr" in run
    assert "github.token" in str(commit.get("env", {}))


def test_a_replay_says_so_in_its_commit(gate_doc: dict[Any, Any]) -> None:
    (commit,) = [s for s in job(gate_doc)["steps"] if "git push" in str(s.get("run", ""))]
    assert "(replayed)" in str(commit["run"])


def test_the_gate_that_attests_is_the_one_the_merge_pinned(gate_doc: dict[Any, Any]) -> None:
    """Found on the first replay (#145): the attestation names the pin in the merge commit's tree
    and runs that pin's image, while the Python that drove it came from main's newer pin. The
    attesting gate is now the merge's own; only the products, the ledger and the cache, which
    describe main as it is, are rendered by main's pin."""
    run = find_step(gate_doc)
    assert 'git show "$merge:targets/$target/gate-spec.json"' in run
    steps = {s.get("name", ""): str(s.get("run", "")) for s in job(gate_doc)["steps"]}
    for name, body in steps.items():
        if "cli postmerge" in body or "cli classify" in body or "cli sign" in body:
            assert "network-render" not in body, name
        if "cli products" in body or "cli ledger" in body or "cache publish" in body:
            assert "--project network-render" in body, name
