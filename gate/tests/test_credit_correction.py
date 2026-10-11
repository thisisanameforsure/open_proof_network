"""F07-T66 (D-18, D-19 v3.27): a curator's credit correction, classified, checked and applied.

The ledger's own rules are in ``test_ledger.py``; these drive the record through the classifier
(a curator record, F08-R8), the checks before any merge, and the post-merge ``opn-gate ledger``
step that applies it. The record lives at ``targets/<t>/credit-corrections/<stamp>-<curator>.yaml``:
a submission can only reach ``targets/**`` and ``policy.json``, and a ledger line names the target
its merge touched, so the correction is filed under that target and the one-target rule holds.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import TARGET, copy_graph
from test_cli_sandboxed import git_repo, run

from opn_gate import cli, ledger, modes, paths, schemas
from opn_gate.modes import Curators
from opn_gate.paths import Change

NODE = "and-reassoc"
MERGE = "1" * 40
DATE = "2026-09-16T12:00:00Z"
CORRECTION = f"targets/{TARGET}/credit-corrections/20261004T120000Z-founder.yaml"
CURATORS = Curators((("founder", "founder-login"), ("second", "second-login")))


def correction(**kw: object) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": "credit-correction/v1",
        "merge_commit": MERGE,
        "line": "proof",
        "node": NODE,
        "artifact": "Proof.lean",
        "from": "alice",
        "to": "bob",
        "reason": "the ledger credited the merger; bob's commit is the submission",
        "author": "founder",
        "date": "2026-10-04",
    }
    doc.update(kw)
    return doc


def alice_holds_the_line(root: Path) -> dict[str, Any]:
    entry = ledger.proof_entry(
        identity="alice",
        target=TARGET,
        node=NODE,
        artifact_type="proof",
        artifact="Proof.lean",
        merge_commit=MERGE,
        date=DATE,
    )
    assert entry is not None
    ledger.record(root, "alice", entry)
    return entry.as_dict()


def write(root: Path, rel: str, doc: dict[str, Any]) -> str:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return rel


# --- the record is a curator's ------------------------------------------------------------------


def test_a_credit_correction_is_a_curator_record() -> None:
    """Today the path is no role, so the pull request is ``path-forbidden``."""
    located = paths.locate(CORRECTION)
    assert located is not None and located.role == "credit-correction"
    classification = modes.classify(
        [Change("A", CORRECTION)], author="founder-login", curators=CURATORS
    )
    assert classification.mode == "curator", classification.problems
    assert classification.reviewers == ("second-login",)


def test_a_credit_correction_by_a_non_curator_is_refused() -> None:
    classification = modes.classify([Change("A", CORRECTION)], author="alice", curators=CURATORS)
    assert [d.code for d in classification.problems] == ["curator-unlisted"]


def test_the_ledger_itself_is_still_no_submission() -> None:
    """The correction is the curator's route; the bot-owned ledger stays untouchable (D-35)."""
    classification = modes.classify(
        [Change("M", "ledger/alice.json")], author="founder-login", curators=CURATORS
    )
    assert [d.code for d in classification.problems] == ["path-forbidden"]


def check_codes(root: Path, rel: str) -> list[str]:
    classification = modes.classify([Change("A", rel)], author="founder-login", curators=CURATORS)
    assert classification.mode == "curator", classification.problems
    return [d.code for d in modes.check(root, classification)]


def test_a_correction_of_a_line_on_the_ledger_passes_the_checks(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    alice_holds_the_line(root)
    assert schemas.violations(correction(), "credit-correction/v1") == []
    assert check_codes(root, write(root, CORRECTION, correction())) == []


@pytest.mark.parametrize(
    "overrides",
    [{"node": "and-swap-reassoc"}, {"merge_commit": "2" * 40}, {"from": "carol"}],
    ids=["another-node", "another-merge", "another-identity"],
)
def test_a_correction_naming_no_active_line_is_refused(
    tmp_path: Path, overrides: dict[str, Any]
) -> None:
    root = copy_graph(tmp_path)
    alice_holds_the_line(root)
    rel = write(root, CORRECTION, correction(**overrides))
    assert check_codes(root, rel) == ["credit-correction-unknown-entry"]


def test_a_correction_to_the_same_identity_is_refused(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    alice_holds_the_line(root)
    rel = write(root, CORRECTION, correction(to="alice"))
    assert check_codes(root, rel) == ["credit-correction-same-identity"]


def test_a_malformed_correction_is_refused(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    alice_holds_the_line(root)
    rel = write(root, CORRECTION, {k: v for k, v in correction().items() if k != "reason"})
    assert check_codes(root, rel) == ["record-invalid"]


# --- the post-merge ledger step applies it ------------------------------------------------------


def test_the_post_merge_ledger_step_applies_a_merged_correction(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root, git, _base = git_repo(tmp_path)
    original = alice_holds_the_line(root)
    git("add", "--", "ledger")
    git("commit", "-q", "-m", "gate: #1 pass")
    write(root, CORRECTION, correction())
    git("add", "--", CORRECTION)
    git("commit", "-q", "--author", "founder <f@x>", "-m", "correct the credit of #1")
    commit = git("rev-parse", "HEAD")

    code, out, err = run(capsys, "ledger", "--graph", str(root), "--commit", commit)
    assert code == cli.EXIT_PASS, err
    assert out["corrected"] == [CORRECTION], out
    alice = ledger.entries_of(ledger.load(root, "alice"))
    bob = ledger.entries_of(ledger.load(root, "bob"))
    assert alice == [{**original, "status": "revoked"}]
    assert bob == [{**original, "status": "active"}]

    # a replay of the same merge (F07-T33) changes nothing
    before = {p.name: p.read_bytes() for p in (root / "ledger").iterdir()}
    code, out, err = run(capsys, "ledger", "--graph", str(root), "--commit", commit)
    assert code == cli.EXIT_PASS, err
    assert {p.name: p.read_bytes() for p in (root / "ledger").iterdir()} == before
