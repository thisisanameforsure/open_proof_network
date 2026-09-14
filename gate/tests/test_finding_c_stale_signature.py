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

The tests under "the defect" were strict xfails until F11-T9 (``fidelity/v2`` pins the statement
hash; a certificate counts only for the subject's current hash, and a v1 certificate counts for
nothing — Mike, 2026-09-13). The others hold the behaviour the fix had to keep.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from harness import copy_graph, take_in
from test_intake import LATER, index_row
from test_intake_root import revise_root
from test_qa import floor_rows
from test_qa import write as write_qa

from opn_gate import fidelity, intake, layout, qa, schemas

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
    root = copy_graph(tmp_path, publish=True)
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


# --- the defect: failed before F11-T9 -------------------------------------------------------------


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


# --- F11-T9: the counting rule and what it must not disturb ---------------------------------------


def write_certificate(root: Path, name: str, **fields: Any) -> Path:
    """A certificate written by hand, the way a pre-T9 gate or a curator's editor would."""
    path = fidelity.fidelity_dir(target_dir(root)) / name
    path.write_text(yaml.safe_dump(fields, sort_keys=False), encoding="utf-8")
    return path


def v1_signature(**overrides: Any) -> dict[str, Any]:
    doc = samples.fidelity_certificate(schema="fidelity/v1", subject_author="author", **overrides)
    doc.pop("statement_hash")
    return doc


def test_intake_writes_its_certificates_at_v2_pinned_to_each_subject(tmp_path: Path) -> None:
    """T9: intake's mechanical-only certificates are v2 and carry the hash of the subject they
    were written for — the value the QA record pins — so they count for that subject."""
    root = copy_graph(tmp_path, publish=True)
    take_in(root, defs=DEFS)
    t = target_dir(root)
    for subject in ("root", "Primes"):
        path = fidelity.fidelity_dir(t) / f"{subject}-1.yaml"
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert doc["schema"] == "fidelity/v2" == fidelity.SCHEMA
        assert doc["grade"] == fidelity.DEFAULT_GRADE
        assert doc["statement_hash"] == qa.subject_hash(t, subject)
        (cert,) = fidelity.load(t)[subject]
        assert cert.counts_for(fidelity.current_hash(t, subject))


def test_the_v2_schema_requires_a_statement_hash_and_v1_is_unchanged() -> None:
    """D-34: v2 is a new version, v1 is not edited — a v1 document still validates, a v2 one
    needs a 64-hex hash, and v1 does not accept the new field."""
    schemas.validate(samples.fidelity_certificate())
    schemas.validate(v1_signature())
    no_hash = samples.fidelity_certificate()
    no_hash.pop("statement_hash")
    assert schemas.violations(no_hash)
    assert schemas.violations(samples.fidelity_certificate(statement_hash="A" * 64))
    assert schemas.violations(samples.fidelity_certificate(statement_hash="a" * 63))
    assert schemas.violations({**v1_signature(), "statement_hash": "a" * 64})


def test_a_v1_signature_counts_for_nothing(tmp_path: Path) -> None:
    """Mike, 2026-09-13: a v1 certificate above mechanical-only pins no statement, so it counts
    for nothing until someone re-signs at v2 — even on a statement that has never changed."""
    root = copy_graph(tmp_path, publish=True)
    take_in(root)
    t = target_dir(root)
    write_qa(t, floor_rows("root"))
    write_certificate(root, "root-2.yaml", **v1_signature(grade="expert-attested"))
    (_, old) = fidelity.load(t)["root"]
    assert old.schema == "fidelity/v1" and old.statement_hash is None
    root_grade = next(r for r in fidelity.subject_grades(t) if r.subject == "root")
    assert root_grade.grade == fidelity.DEFAULT_GRADE and root_grade.signers == ()
    assert fidelity.target_grade(t) == fidelity.DEFAULT_GRADE
    intake.post(root, NEW, venue="erdosproblems.com", url="https://example.org/p", date=LATER)
    with pytest.raises(intake.IntakeError, match="below screened-and-signed"):
        intake.activate(root, NEW, author="curator", date="2026-09-12T00:00:00Z")


def test_a_v1_certificate_still_names_the_subjects_author(tmp_path: Path) -> None:
    """The live graph's nine certificates are v1. Authorship is not a grade: a v1 certificate
    still establishes who wrote the subject, so the non-author rule holds across the versions."""
    root = copy_graph(tmp_path, publish=True)
    take_in(root)
    t = target_dir(root)
    first = fidelity.fidelity_dir(t) / "root-1.yaml"
    doc = yaml.safe_load(first.read_text(encoding="utf-8"))
    doc.pop("statement_hash")
    first.write_text(yaml.safe_dump({**doc, "schema": "fidelity/v1"}), encoding="utf-8")
    assert fidelity.author_of(fidelity.load(t)["root"]) == "author"
    write_qa(t, floor_rows("root"))
    with pytest.raises(fidelity.FidelityError, match="cannot attest"):
        sign(root, "root", by="author")
    sign(root, "root", by="reviewer")
    assert fidelity.target_grade(t) == SIGNED


def test_a_stale_v2_signature_counts_for_nothing_and_a_fresh_one_counts(tmp_path: Path) -> None:
    """The rule itself: a v2 certificate counts only when its hash is the subject's current one.
    A signature pinned to another statement adds neither a grade nor a name; one pinned to this
    statement adds both, and only its own name."""
    root = copy_graph(tmp_path, publish=True)
    take_in(root)
    t = target_dir(root)
    write_qa(t, floor_rows("root"))
    write_certificate(
        root,
        "root-2.yaml",
        **samples.fidelity_certificate(subject_author="author", statement_hash="0" * 64),
    )
    row = next(r for r in fidelity.subject_grades(t) if r.subject == "root")
    assert row.grade == fidelity.DEFAULT_GRADE and row.signers == ()
    sign(root, "root", by="auditor", date="2026-09-12")
    row = next(r for r in fidelity.subject_grades(t) if r.subject == "root")
    assert row.grade == SIGNED and row.signers == ("auditor",)
    assert [c.path.name for c in fidelity.load(t)["root"]] == [
        "root-1.yaml",
        "root-2.yaml",
        "root-3.yaml",
    ]


def test_a_later_stale_certificate_does_not_mask_a_counting_one(tmp_path: Path) -> None:
    """The latest *counting* certificate decides: a stale one dated after a fresh signature
    neither lowers nor raises the grade."""
    root = copy_graph(tmp_path, publish=True)
    take_in(root)
    t = target_dir(root)
    write_qa(t, floor_rows("root"))
    sign(root, "root", by="reviewer", date="2026-09-12")
    write_certificate(
        root,
        "root-3.yaml",
        **samples.fidelity_certificate(
            subject_author="author",
            attestor="other",
            grade="published-and-uncontested",
            statement_hash="0" * 64,
            date="2026-09-20",
        ),
    )
    row = next(r for r in fidelity.subject_grades(t) if r.subject == "root")
    assert row.grade == SIGNED and row.signers == ("reviewer",)


def test_a_mathlib_pin_move_keeps_the_grade(tmp_path: Path) -> None:
    """Mike, 2026-09-13: only the statement hash drops a grade. A pin move makes the QA pass
    stale (D-9: screens re-run when the pin moves) but the statement the signer read is the
    same, so the signature, the rung and claimability stand."""
    root = active_signed_target(tmp_path)
    spec_path = layout.gate_spec_path(root, NEW)
    spec = schemas.load_json(spec_path, "gate-spec/v1")
    assert spec["mathlib_sha"] != "b" * 40
    spec_path.write_bytes(schemas.canonical_json({**spec, "mathlib_sha": "b" * 40}))
    row = index_row(root, NEW)
    root_row = subject_row(row, "root")
    assert root_row["qa"]["stale"] is True  # the pin really moved under the pass
    assert root_row["grade"] == SIGNED and root_row["signers"] == ["reviewer"]
    assert row["fidelity"] == SIGNED and row["claimable"] is True


def test_a_revised_root_keeps_its_posting(tmp_path: Path) -> None:
    """Mike, 2026-09-13: the D-10 posting is a fact about the world and survives the revision;
    only the grade reason stands between the revised target and claimable."""
    root = active_signed_target(tmp_path)
    posting = index_row(root, NEW)["posting"]
    revise_root(root, ROOT, REVISED)
    row = index_row(root, NEW)
    assert row["posting"] == posting and posting is not None
    assert row["not_claimable"] == [GRADE_REASON]


def test_a_certificate_for_a_removed_definition_counts_for_nothing(tmp_path: Path) -> None:
    """A definition that no longer exists has no current hash, so its signature counts for
    nothing — and the products still render. Its row leaves the grade (Mike, 2026-09-13;
    F11-Q33), so the target is graded by the root and the definitions that exist now, and the
    certificates stay on disk."""
    root = active_signed_target(tmp_path, defs=DEFS)
    t = target_dir(root)
    (t / "defs" / "Primes.lean").unlink()
    assert fidelity.current_hash(t, "Primes") is None
    row = index_row(root, NEW)
    assert [s["subject"] for s in row["subjects"]] == ["root"]
    assert subject_row(row, "root")["grade"] == SIGNED
    assert row["fidelity"] == SIGNED
    assert [c.grade for c in fidelity.load(t)["Primes"]] == ["mechanical-only", SIGNED]


def test_a_certificate_of_an_unreadable_version_stops_the_grade(tmp_path: Path) -> None:
    """C7: a file under fidelity/ that is not a fidelity certificate of a readable version is a
    graph defect, not a certificate that quietly counts for nothing."""
    root = copy_graph(tmp_path, publish=True)
    take_in(root)
    write_certificate(root, "root-2.yaml", **samples.target_status())
    with pytest.raises(schemas.SchemaError, match="not a fidelity certificate"):
        fidelity.subject_grades(target_dir(root))
