"""F07-T36: a losing racer's proof is recorded as an alternate, as D-25 says (testers 2026-09-23).

D-25 (v3.13): "first merged fills ``Proof.lean``; a losing racer's complete proof is recorded in
``attempts/`` as an alternate proof". Nothing did it. On 2026-09-23 three agents proved the same
three erdos-69 holes within minutes (#159-#164, #167, #172, every text different): each pull
request writes the node's ``Proof.lean``, so once the first merges the rest conflict with
``main`` for ever, and each sits open reading ``waiting_on: merge`` until a person closes it —
the different proofs the owner wants kept ("there can be multiple proofs per node") thrown away.

The service opened each of those branches, so it moves the loser's proof, unchanged, to
``attempts/<its submission time>-<pseudonym>-alternate.lean`` on a fresh commit from ``main``,
the path an alternate takes (F07-T12), and the gate then checks it as one. It does this when a
live read finds the pull request conflicting and the node proved; once per submission. A loser
that is a copy of the winner is left alone: an alternate identical to the proof is refused.
"""

from __future__ import annotations

from typing import Any

from api_fakes import PROOF_PREFIX, Harness
from test_githost_seam import COMMIT_SHA, REPO, Script, host, pem, push_ok, rsa_key, script
from test_pending_submissions import record
from test_submissions_alternate import mark_proved

WINNER = "import Mathlib\n\ntheorem x : True := trivial\n"
RACER = "import Mathlib\n\ntheorem x : True := True.intro\n"
HEAD = "c" * 40
__all__ = ["host", "pem", "rsa_key", "script"]  # the seam's fixtures, for pytest to find


def racing(h: Harness, text: str = RACER) -> tuple[str, Any]:
    """A proved node whose proof merged from another pull request, and an open proof of it that
    now conflicts with main; answers the node and the loser's record."""
    proved, _other = mark_proved(h)
    h.githost.files[f"{PROOF_PREFIX}{proved}/Proof.lean"] = WINNER.encode()
    loser = record(12, kind="proof", node_id=proved, pseudonym="bob")
    h.store.put_submission(loser)
    h.githost.set_pull_request_state(12, mergeable_state="dirty", head_sha=HEAD)
    h.githost.files_at[HEAD] = {f"{PROOF_PREFIX}{proved}/Proof.lean": text.encode()}
    return proved, loser


def replaced(h: Harness) -> list[Any]:
    return [p for p in h.githost.pushes if p.replace]


def test_a_losing_racer_is_moved_to_an_alternate(harness: Harness) -> None:
    node, loser = racing(harness)
    got = harness.client.get(f"/submissions/{loser.id}")
    assert got.status_code == 200, got.text
    (push,) = replaced(harness)
    assert push.branch == f"submit/{loser.id}"
    (path,) = push.files
    assert path.startswith(f"{PROOF_PREFIX}{node}/attempts/") and path.endswith(
        "-bob-alternate.lean"
    )
    assert push.files[path] == RACER
    assert push.base == harness.settings.graph_branch  # a fresh commit from main
    assert push.author is not None and push.author.name == "bob"
    assert "Signed-off-by: bob" in push.message


def test_it_is_done_once(harness: Harness) -> None:
    _node, loser = racing(harness)
    for _ in range(3):
        harness.client.get(f"/submissions/{loser.id}")
    assert len(replaced(harness)) == 1


def test_a_racer_that_copies_the_winner_is_left_alone(harness: Harness) -> None:
    _node, loser = racing(harness, text="-- same\n" + WINNER)
    harness.client.get(f"/submissions/{loser.id}")
    assert replaced(harness) == []


def test_a_conflict_on_an_unproved_node_is_not_a_race(harness: Harness) -> None:
    _proved, unproved = mark_proved(harness)
    loser = record(12, kind="proof", node_id=unproved, pseudonym="bob")
    harness.store.put_submission(loser)
    harness.githost.set_pull_request_state(12, mergeable_state="dirty", head_sha=HEAD)
    harness.client.get(f"/submissions/{loser.id}")
    assert replaced(harness) == []


def test_the_snapshot_converts_too(harness: Harness) -> None:
    """``GET /submissions.json`` reconciles every open record; a racer nobody polls is moved."""
    _node, _loser = racing(harness)
    assert harness.client.get("/submissions.json").status_code == 200
    assert len(replaced(harness)) == 1


def test_the_host_moves_an_existing_branch_and_creates_no_ref(script: Script, host: Any) -> None:
    """The seam: ``replace`` rebuilds the branch from ``base`` and force-moves its ref with one
    PATCH; no ``POST /git/refs``, which would answer 422 for a branch that exists."""
    push_ok(script).on("PATCH", f"/repos/{REPO}/git/refs/heads/submit/01X", 200, json={})
    sha = host.push_branch(
        REPO, "submit/01X", {"a.lean": "x"}, base="main", message="m", replace=True
    )
    assert sha == COMMIT_SHA
    assert script.sent("PATCH", f"/repos/{REPO}/git/refs/heads/submit/01X") == {
        "sha": COMMIT_SHA,
        "force": True,
    }
    assert script.to("POST", f"/repos/{REPO}/git/refs") == []
