"""Finding C: a signature made against one statement keeps counting after a D-8 revision.

Reproduced end to end in the fast tier: a curated target is taken in, its root's QA pass is
recorded complete, a non-author signs it ``screened-and-signed`` through the F12-R9 grade gate,
it is posted and activated, and the curator revises the root (D-8: ``<root>-v2``, the old node
superseded). ``targets/index.json`` then still says ``claimable: true`` and
``fidelity: screened-and-signed`` with one signer, while the same row's QA state for the root is
``complete: false, stale: true``.

The cause is that ``fidelity/v1`` certificates pin no statement: ``fidelity.grade_of`` takes the
latest certificate for the *subject name* ``root``, and the subject name survives a revision
while the statement under it does not. D-9 grades a statement ("what stands on each rung is a
statement"); F12-R9 lets a signature be written only "for the current statement hash"; F12-R10
already refuses to carry an attempt across a revision ("an attempt counts only against the
statement content hash it actually ran on"). A certificate is the one record on that path with no
hash, so it is the one that crosses.

The tests marked as the defect's fail today. The others hold the behaviour a fix must keep.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from harness import copy_graph, take_in
from test_intake import LATER, index_row
from test_intake_root import revise_root
from test_qa import floor_rows
from test_qa import write as write_qa

from opn_gate import fidelity, intake, qa

NEW = "euclid-primes"
ROOT = "and-reassoc"
REVISED = f"{ROOT}-v2"
DEFS = {"Primes.lean": "def Opn.IsPrime (p : Nat) : Prop := 2 ≤ p\n"}
SIGNED = fidelity.CLAIMABLE_GRADE
GRADE_REASON = f"grade-below-{fidelity.CLAIMABLE_GRADE}"


def target_dir(root: Path) -> Path:
    return root / "targets" / NEW


def sign(root: Path, subject: str, by: str = "reviewer", date: str = "2026-09-11") -> Path:
    """A signature the way ``opn-gate fidelity`` writes one: through F12-R9's grade gate. The
    floor rows carry no exhibit files, so there is nothing to replay (F12-Q15)."""
    t = target_dir(root)
    return fidelity.attest(
        t,
        subject,
        SIGNED,
        attestor=by,
        date=date,
        evidence=f"read {subject} against the informal statement",
        gate=lambda s, _g: qa.grade_gate(t, s, replay=None),
    )


def active_signed_target(tmp_path: Path, *, defs: dict[str, str] | None = None) -> Path:
    """Listed, QA complete for every subject, signed by a non-author, posted, activated."""
    root = copy_graph(tmp_path)
    take_in(root, defs=defs)
    t = target_dir(root)
    for subject in fidelity.subjects_of(t):
        write_qa(t, floor_rows(subject), subject=subject)
        sign(root, subject)
    intake.post(root, NEW, venue="erdosproblems.com", url="https://example.org/posting", date=LATER)
    intake.activate(root, NEW, author="curator", date="2026-09-12T00:00:00Z")
    return root


def subject_row(row: dict[str, Any], subject: str) -> dict[str, Any]:
    return next(s for s in row["subjects"] if s["subject"] == subject)


# --- must keep passing ---------------------------------------------------------------------------


def test_an_unrevised_signed_target_stays_screened_and_signed(tmp_path: Path) -> None:
    """The control, and the state the reproduction starts from: a complete pass, one non-author
    signature, a posting and an activation make a claimable target at the signed rung."""
    root = active_signed_target(tmp_path)
    row = index_row(root, NEW)
    assert row["root"] == ROOT and row["status"] == "active"
    assert row["claimable"] is True and row["not_claimable"] == []
    assert row["fidelity"] == SIGNED
    root_row = subject_row(row, "root")
    assert root_row["signers"] == ["reviewer"] and root_row["signature_count"] == 1
    assert root_row["qa"]["complete"] is True and root_row["qa"]["stale"] is False


def test_an_unrevised_target_with_a_signed_definition_stays_signed(tmp_path: Path) -> None:
    """The control with a definition: root and ``Primes`` both signed; the minimum is signed."""
    root = active_signed_target(tmp_path, defs=DEFS)
    row = index_row(root, NEW)
    assert row["fidelity"] == SIGNED and row["claimable"] is True
    assert subject_row(row, "Primes")["signers"] == ["reviewer"]


def test_the_revision_really_changes_the_statement_the_pass_was_for(tmp_path: Path) -> None:
    """The precondition that makes this a defect rather than a no-op: the revision moves the
    root's statement hash, so F12 already calls the root's QA stale and refuses a new signature.
    Only the old certificate still speaks."""
    root = active_signed_target(tmp_path)
    t = target_dir(root)
    before = qa.subject_hash(t, "root")
    revise_root(root, ROOT, REVISED)
    assert qa.subject_hash(t, "root") != before
    state = qa.pass_state(t, "root")
    assert state.stale and not state.complete
    with pytest.raises(qa.QaError, match="stale"):
        qa.grade_gate(t, "root", replay=None)
    assert index_row(root, NEW)["root"] == REVISED


def test_the_superseded_signature_stays_on_disk(tmp_path: Path) -> None:
    """Whatever the fix, certificates are append-only (F11-R3, D-34): the signature on the old
    statement is history and is not removed by a revision."""
    root = active_signed_target(tmp_path)
    revise_root(root, ROOT, REVISED)
    certs = fidelity.load(target_dir(root))["root"]
    assert [c.grade for c in certs] == ["mechanical-only", SIGNED]
    assert all(c.path.is_file() for c in certs)


# --- the defect: FAIL today -----------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="finding C (D-9, F12-R9): a fidelity certificate records no statement hash, so a signature survives a revision of its statement; fix: fidelity/v2 pins the hash, v1 signatures count for nothing (Mike, 2026-09-13)",  # noqa: E501 — the xfail reason names the finding and its fix
)
def test_a_revised_root_drops_below_the_signed_rung(tmp_path: Path) -> None:
    """D-9: the rung belongs to the statement that was read. After D-8 makes ``<root>-v2`` nobody
    has signed the new statement, so the root's grade is the machine's own and the target's grade,
    the minimum over its subjects (F11-R3), falls with it.

    Today: ``fidelity`` stays ``screened-and-signed``."""
    root = active_signed_target(tmp_path)
    revise_root(root, ROOT, REVISED)
    row = index_row(root, NEW)
    assert subject_row(row, "root")["qa"]["stale"] is True  # F12 already sees it
    assert subject_row(row, "root")["grade"] == fidelity.DEFAULT_GRADE
    assert row["fidelity"] == fidelity.DEFAULT_GRADE
    assert fidelity.target_grade(target_dir(root)) == fidelity.DEFAULT_GRADE


@pytest.mark.xfail(
    strict=True,
    reason="finding C (D-9, F12-R9): a fidelity certificate records no statement hash, so a signature survives a revision of its statement; fix: fidelity/v2 pins the hash, v1 signatures count for nothing (Mike, 2026-09-13)",  # noqa: E501 — the xfail reason names the finding and its fix
)
def test_a_revised_root_is_not_claimable_and_says_why(tmp_path: Path) -> None:
    """F11-R4: claimable needs grade ≥ screened-and-signed, and D-9: "No proving compute is
    allocated below screened-and-signed". The reason is the existing grade code, so the Targets
    page explains it with the words it already has (``intake.explain``).

    Today: ``claimable: true`` and ``not_claimable: []``."""
    root = active_signed_target(tmp_path)
    revise_root(root, ROOT, REVISED)
    row = index_row(root, NEW)
    assert row["status"] == "active"  # the status record is not what changed
    assert row["claimable"] is False
    assert GRADE_REASON in row["not_claimable"]
    assert "D-9" in intake.explain(GRADE_REASON)


@pytest.mark.xfail(
    strict=True,
    reason="finding C (D-9, F12-R9): a fidelity certificate records no statement hash, so a signature survives a revision of its statement; fix: fidelity/v2 pins the hash, v1 signatures count for nothing (Mike, 2026-09-13)",  # noqa: E501 — the xfail reason names the finding and its fix
)
def test_the_old_signer_is_not_counted_for_the_new_statement(tmp_path: Path) -> None:
    """D-9 v3.12: signatures are counted and named, and the count is load-bearing
    (``expert-attested`` is ``author-attested`` plus one). A name that signed a different
    statement must not appear in the count for this one.

    Today: ``signers: ["reviewer"]``, ``signature_count: 1``."""
    root = active_signed_target(tmp_path)
    revise_root(root, ROOT, REVISED)
    root_row = subject_row(index_row(root, NEW), "root")
    assert root_row["signature_count"] == 0
    assert root_row["signers"] == []


@pytest.mark.xfail(
    strict=True,
    reason="finding C (D-9, F12-R9): a fidelity certificate records no statement hash, so a signature survives a revision of its statement; fix: fidelity/v2 pins the hash, v1 signatures count for nothing (Mike, 2026-09-13)",  # noqa: E501 — the xfail reason names the finding and its fix
)
def test_re_running_the_screens_does_not_resurrect_the_old_signature(tmp_path: Path) -> None:
    """The case that separates the two candidate fixes. If a certificate counted "while the QA
    pass is complete and fresh", re-running the screens on the revised statement would lift the
    target back to the signed rung with no person having read the new statement. D-9: non-author
    sign-off is "the only event that changes accepted state". So the pass alone is not enough;
    the signature itself has to be for this statement.

    Today: the grade is ``screened-and-signed`` throughout."""
    root = active_signed_target(tmp_path)
    t = target_dir(root)
    revise_root(root, ROOT, REVISED)
    write_qa(t, floor_rows("root"))
    assert qa.pass_state(t, "root").complete
    row = index_row(root, NEW)
    assert row["fidelity"] == fidelity.DEFAULT_GRADE
    assert row["claimable"] is False and GRADE_REASON in row["not_claimable"]


@pytest.mark.xfail(
    strict=True,
    reason="finding C (D-9, F12-R9): a fidelity certificate records no statement hash, so a signature survives a revision of its statement; fix: fidelity/v2 pins the hash, v1 signatures count for nothing (Mike, 2026-09-13)",  # noqa: E501 — the xfail reason names the finding and its fix
)
def test_a_fresh_signature_on_the_revised_root_restores_the_rung(tmp_path: Path) -> None:
    """What the curator does next: re-run the pass, a non-author signs the new statement, and the
    target is claimable again with that signer alone counted. Passes today only because the grade
    never fell; the assertion on the count is the defect's."""
    root = active_signed_target(tmp_path)
    t = target_dir(root)
    revise_root(root, ROOT, REVISED)
    write_qa(t, floor_rows("root"))
    sign(root, "root", by="auditor", date="2026-09-14")
    row = index_row(root, NEW)
    assert row["fidelity"] == SIGNED and row["claimable"] is True
    assert subject_row(row, "root")["signers"] == ["auditor"]


@pytest.mark.xfail(
    strict=True,
    reason="finding C (D-9, F12-R9): a fidelity certificate records no statement hash, so a signature survives a revision of its statement; fix: fidelity/v2 pins the hash, v1 signatures count for nothing (Mike, 2026-09-13)",  # noqa: E501 — the xfail reason names the finding and its fix
)
def test_a_signature_on_an_unchanged_definition_still_counts(tmp_path: Path) -> None:
    """D-9 grades each subject separately. Revising the root does not touch ``defs/Primes.lean``,
    so its signature is still for the file as it stands and keeps counting; only the root falls,
    and the target falls with it because the grade is the minimum (F11-R3).

    Today: the root does not fall either."""
    root = active_signed_target(tmp_path, defs=DEFS)
    revise_root(root, ROOT, REVISED)
    row = index_row(root, NEW)
    primes = subject_row(row, "Primes")
    assert primes["grade"] == SIGNED and primes["signers"] == ["reviewer"]
    assert primes["qa"]["stale"] is False
    assert subject_row(row, "root")["grade"] == fidelity.DEFAULT_GRADE
    assert row["fidelity"] == fidelity.DEFAULT_GRADE and row["claimable"] is False


@pytest.mark.xfail(
    strict=True,
    reason="finding C (D-9, F12-R9): a fidelity certificate records no statement hash, so a signature survives a revision of its statement; fix: fidelity/v2 pins the hash, v1 signatures count for nothing (Mike, 2026-09-13)",  # noqa: E501 — the xfail reason names the finding and its fix
)
def test_an_edited_definition_loses_its_signature_too(tmp_path: Path) -> None:
    """The same rule for the other kind of subject: a definition's hash is its file's (F12-R5,
    ``qa.subject_hash``), so a signature on the old file does not count for an edited one.

    Today: ``Primes`` stays ``screened-and-signed``."""
    root = active_signed_target(tmp_path, defs=DEFS)
    t = target_dir(root)
    (t / "defs" / "Primes.lean").write_text(
        "def Opn.IsPrime (p : Nat) : Prop := 3 ≤ p\n", encoding="utf-8"
    )
    row = index_row(root, NEW)
    assert subject_row(row, "Primes")["qa"]["stale"] is True
    assert subject_row(row, "Primes")["grade"] == fidelity.DEFAULT_GRADE
    assert row["claimable"] is False and GRADE_REASON in row["not_claimable"]
