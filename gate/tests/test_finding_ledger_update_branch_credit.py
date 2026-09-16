"""Finding: updating a pull request's branch reassigns the ledger credit to whoever pressed it.

Found 2026-09-16 on the live graph, on the first merged partial by an outside pseudonym.

``proposer_of`` takes the author of the merge's **second parent** as the contributor. That is the
submission's own commit only while the branch was never brought up to date. The graph's ruleset
requires a branch to be up to date before merging, so any pull request that is not first in the
queue gets an "update branch" merge — authored by whoever pressed it — and *that* commit becomes
the second parent. The contributor's commit is then one step further in.

Live proof (graph PR #71, the Erdos 412 partial):

- the submission commit ``0802ef5`` is authored ``agent-sigma-4f1d <...@anon.opn.invalid>`` (D-23
  puts the pseudonym in the author and the App in the committer);
- the merge ``42f94ef`` has parents ``[10f4b93, eb21025c]``, and ``eb21025c`` is
  "Merge branch 'main' into submit/..." authored ``thisisanameforsure`` — the update;
- so the ledger resolved the earner as ``thisisanameforsure``, and D-21 then barred the line
  because that identity curates ``erdos-412``. The contributor earned nothing and
  ``ledger/agent-sigma-4f1d.json`` was never written.

Where the merger is not a curator this is worse than a missing line: the contributor's proof line
would be written to the **merger's** ledger. PR #38 (Euclid) escaped only because its branch was
never updated, so its second parent was the contributor's commit.

Every existing ledger test commits linearly, so ``proposer_of``'s merge branch was never
exercised at all. These tests build the real shape. The fix reads the commits the merge actually
brought in — those on the second parent's side that the first parent does not already have —
rather than the second parent itself.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_cli_sandboxed import NODES, Git, Seam, git_repo, run
from test_finding_ledger_credits_merges import commit_proof, entries

from opn_gate import cli

PROVED = "and-reassoc"  # non-tutorial, proved in the fixture
AGENT = "agent-sigma-4f1d"  # the live pseudonym, D-23 shape
OWNER = "thisisanameforsure"  # who presses "update branch" and "merge"
FINDING = (
    "finding ledger-update-branch-credit (F07-R12, D-21, D-23): {}; "
    "fix: proposer_of reads the commits the merge brought in (2026-09-16)"
)


def as_author(git: Git, who: str) -> None:
    """Re-author HEAD, so a merge commit git made with the repo's identity is ``who``'s."""
    git("commit", "--amend", "--no-edit", "--author", f"{who} <{who}@x>")


def contributor_branch(root: Path, git: Git, *, branch: str = "submit/x") -> str:
    """The node left unproved on main, then proved on a branch of its own by the pseudonym.

    The unproving belongs on main: doing both halves on the branch nets to no change at all, so
    the merge's diff would be empty and classify as nothing (which is what the first cut of this
    fixture did — ``a merged None pull request earns no ledger line``). This way the merge's diff
    against main is exactly "adds ``Proof.lean``", which is what a real submission looks like.
    """
    main = git("rev-parse", "--abbrev-ref", "HEAD")
    proof = root / NODES / PROVED / "Proof.lean"
    text = proof.read_text(encoding="utf-8")
    proof.unlink()
    git("add", "--", f"{NODES}/{PROVED}")
    git("commit", "-q", "-m", f"{PROVED}, unproved")

    git("checkout", "-q", "-b", branch)
    proof.write_text(text, encoding="utf-8")
    git("add", "--", f"{NODES}/{PROVED}/Proof.lean")
    git("commit", "-q", "--author", f"{AGENT} <{AGENT}@x>", "-m", f"prove {PROVED}")
    git("checkout", "-q", main)
    return main


def move_main(root: Path, git: Git, *, who: str = OWNER) -> None:
    """Something else merges first, so the branch falls behind (the strict ruleset's world)."""
    note = root / "NOTE.md"
    # Distinct content per call: two identical writes leave nothing to commit, and the queue
    # this stands for moves main once per merge.
    before = note.read_text(encoding="utf-8") if note.is_file() else ""
    note.write_text(f"{before}another merge landed first\n", encoding="utf-8")
    git("add", "--", "NOTE.md")
    git("commit", "-q", "--author", f"{who} <{who}@x>", "-m", "something else merged")


def merge_no_ff(git: Git, ref: str, *, who: str) -> str:
    git("merge", "-q", "--no-ff", "--no-edit", ref)
    as_author(git, who)
    return git("rev-parse", "HEAD")


def test_proposer_of_is_the_contributor_after_an_update_branch(tmp_path: Path, seam: Seam) -> None:
    """The shape the live record produced: update the branch, then merge."""
    root, git, _base = git_repo(tmp_path)
    main = contributor_branch(root, git)
    move_main(root, git)

    git("checkout", "-q", "submit/x")
    merge_no_ff(git, main, who=OWNER)  # "Update branch" — authored by whoever pressed it
    git("checkout", "-q", main)
    head = merge_no_ff(git, "submit/x", who=OWNER)

    second = git("log", "-1", "--format=%an", f"{head}^2")
    assert second == OWNER, "the fixture must reproduce the update-branch shape"
    assert cli.proposer_of(root, head) == AGENT, FINDING.format(
        f"proposer_of answered {cli.proposer_of(root, head)!r}, the author of the update merge, "
        f"not {AGENT!r} who wrote the submission"
    )


def test_the_contributor_earns_the_line_not_the_merger(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """End to end through ``opn-gate ledger``: the proof line lands in the contributor's file.

    With the bug, the earner resolves to the merger; on the live graph that identity curated the
    target, so D-21 barred the line and nothing was written at all.
    """
    root, git, _base = git_repo(tmp_path)
    main = contributor_branch(root, git)
    move_main(root, git)
    git("checkout", "-q", "submit/x")
    merge_no_ff(git, main, who=OWNER)
    git("checkout", "-q", main)
    head = merge_no_ff(git, "submit/x", who=OWNER)

    code, out, err = run(capsys, "ledger", "--graph", str(root), "--commit", head)
    assert code == cli.EXIT_PASS, err
    assert out["earned"] is True, FINDING.format(f"the merge earned nothing: {out.get('reason')}")
    assert out["identity"] == AGENT, FINDING.format(
        f"the ledger credited {out['identity']!r} rather than the contributor"
    )
    assert out["written"] == f"ledger/{AGENT}.json"
    assert [e["line"] for e in entries(root, AGENT)] == ["proof"]
    assert not (root / "ledger" / f"{OWNER}.json").exists(), FINDING.format(
        "the merger got a ledger file"
    )


def test_a_branch_that_was_never_updated_still_resolves(tmp_path: Path, seam: Seam) -> None:
    """The PR #38 shape, pinned: no update merge, so the second parent is the contributor's own
    commit and the answer was always right. The fix must not change this."""
    root, git, _base = git_repo(tmp_path)
    contributor_branch(root, git)  # no update merge: nothing moves main
    head = merge_no_ff(git, "submit/x", who=OWNER)

    assert git("log", "-1", "--format=%an", f"{head}^2") == AGENT
    assert cli.proposer_of(root, head) == AGENT


def test_a_linear_commit_still_resolves(tmp_path: Path, seam: Seam) -> None:
    """No merge commit at all — the shape every existing ledger test uses. Unchanged."""
    root, git, _base = git_repo(tmp_path)
    head = commit_proof(root, git, PROVED, author="alice")
    assert cli.proposer_of(root, head) == "alice"


def test_an_octopus_of_updates_still_finds_the_contributor(tmp_path: Path, seam: Seam) -> None:
    """Two rounds of falling behind: the queue made the branch update twice, as it does whenever
    several pull requests are open. The contributor is still the one who wrote the submission."""
    root, git, _base = git_repo(tmp_path)
    main = contributor_branch(root, git)
    for _ in range(2):
        move_main(root, git)
        git("checkout", "-q", "submit/x")
        merge_no_ff(git, main, who=OWNER)
        git("checkout", "-q", main)
    head = merge_no_ff(git, "submit/x", who=OWNER)

    assert cli.proposer_of(root, head) == AGENT, FINDING.format(
        "two update merges hid the contributor completely"
    )
