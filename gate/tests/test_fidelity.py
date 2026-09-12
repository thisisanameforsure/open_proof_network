"""F11-T2: fidelity certificates and the grade a target derives from them (R3; AC4; D-9 v3.12).

D-9's ladder only means anything if two rules hold: the grade of a target is its *weakest*
subject, and above the first rung the signature is someone other than the author's. Both are
tested here against a real certificate set on disk, because both are rules about a *set* of
files and neither survives being asserted about one document.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml
from harness import copy_graph, take_in

from opn_gate import fidelity
from opn_gate.fidelity import FidelityError

DEFS = {"Primes.lean": "def Opn.IsPrime (p : Nat) : Prop := 2 ≤ p\n"}
AUTHOR = "author"  # samples.target_record's provenance.author, so the root's author on record


@pytest.fixture
def target(tmp_path: Path) -> Path:
    root = copy_graph(tmp_path)
    take_in(root, defs=DEFS)
    return root / "targets" / "euclid-primes"


def sign(target: Path, subject: str, grade: str, by: str, date: str = "2026-09-12") -> Path:
    return fidelity.attest(
        target, subject, grade, attestor=by, date=date, evidence=f"checked {subject}"
    )


def grades(target: Path) -> dict[str, fidelity.SubjectGrade]:
    return {row.subject: row for row in fidelity.subject_grades(target)}


def test_grade_rules(target: Path) -> None:
    """AC4: the author cannot sign their own statement above the first rung; a non-author can;
    and a definition still at mechanical-only holds the whole target there."""
    with pytest.raises(FidelityError) as refusal:
        sign(target, "root", "screened-and-signed", AUTHOR)
    assert "cannot attest" in str(refusal.value) and "D-9" in str(refusal.value)
    assert grades(target)["root"].grade == "mechanical-only", "a refusal wrote a certificate"

    sign(target, "root", "screened-and-signed", "reviewer")
    assert grades(target)["root"].grade == "screened-and-signed"
    # R3: the minimum over the root and every definition — Primes is still the machine's word.
    assert grades(target)["Primes"].grade == "mechanical-only"
    assert fidelity.target_grade(target) == "mechanical-only"

    sign(target, "Primes", "screened-and-signed", "reviewer")
    assert fidelity.target_grade(target) == "screened-and-signed"


def test_the_author_may_still_hold_the_machines_own_grade(target: Path) -> None:
    """R3: `mechanical-only` is what the toolchain says, so it signs for nobody and the
    non-author rule does not apply — which is why intake can write it in the author's name."""
    sign(target, "root", "mechanical-only", AUTHOR)
    assert grades(target)["root"].grade == "mechanical-only"
    assert grades(target)["root"].signers == ()


def test_certificates_are_append_only_and_the_latest_wins(target: Path) -> None:
    """R3: a downgrade shows its history rather than erasing it."""
    first = sign(target, "root", "expert-attested", "reviewer", date="2026-09-12")
    second = sign(target, "root", "screened-and-signed", "auditor", date="2026-09-13")
    # root-1 is intake's own mechanical-only certificate, so these are 2 and 3.
    assert first.name == "root-2.yaml" and second.name == "root-3.yaml"
    assert first.is_file(), "the earlier certificate was overwritten"
    assert grades(target)["root"].grade == "screened-and-signed"


def test_signatures_are_counted_and_named(target: Path) -> None:
    """R3, D-9 v3.12: distinct attestors at screened-and-signed or above, counted once each."""
    sign(target, "root", "screened-and-signed", "reviewer", date="2026-09-12")
    sign(target, "root", "expert-attested", "auditor", date="2026-09-13")
    sign(target, "root", "expert-attested", "auditor", date="2026-09-14")
    row = grades(target)["root"]
    assert row.signers == ("reviewer", "auditor")
    assert row.as_dict()["signature_count"] == 2


def test_a_subject_has_one_author(target: Path) -> None:
    """R3: the first certificate establishes who wrote the subject; a later one that disagrees
    is grading a different thing, so it is refused rather than recorded."""
    with pytest.raises(FidelityError, match="one author"):
        fidelity.attest(
            target,
            "root",
            "screened-and-signed",
            attestor="reviewer",
            subject_author="someone-else",
            date="2026-09-12",
            evidence="x",
        )


def test_an_unknown_subject_is_refused(target: Path) -> None:
    """D-9's subjects are the root and the definitions; anything else has no informal statement
    to be faithful to."""
    with pytest.raises(FidelityError, match="not a fidelity subject"):
        sign(target, "Nonexistent", "screened-and-signed", "reviewer")


def test_a_broken_certificate_stops_the_grade_rather_than_being_skipped(target: Path) -> None:
    """R3, C7: an attempt record that does not validate is counted as invalid (F03-R7), but a
    fidelity grade gates claiming — so a broken one raises instead of quietly lowering nobody."""
    (fidelity.fidelity_dir(target) / "root-9.yaml").write_text("grade: [oops\n", encoding="utf-8")
    with pytest.raises(Exception, match=re.escape("root-9.yaml")):
        fidelity.subject_grades(target)


def test_a_certificate_for_a_removed_definition_still_counts(target: Path) -> None:
    """R3: deleting a definition file must not silently raise the target's grade."""
    sign(target, "Primes", "mechanical-only", AUTHOR)
    (target / "defs" / "Primes.lean").unlink()
    rows = grades(target)
    assert "Primes" in rows, "a certificate vanished with its subject file"
    assert fidelity.target_grade(target) == "mechanical-only"


def test_the_ladder_is_ordered_and_unknown_grades_are_refused() -> None:
    assert [fidelity.rank(g) for g in fidelity.GRADES] == list(range(len(fidelity.GRADES)))
    assert fidelity.meets("expert-attested") and not fidelity.meets("mechanical-only")
    assert not fidelity.meets(None)
    with pytest.raises(FidelityError, match="unknown fidelity grade"):
        fidelity.rank("back-translated")  # the rung D-9 v3.12 renamed away


def test_a_certificate_records_its_exhibits_and_evidence_files(target: Path) -> None:
    """R3: the grade names what it rests on, so a later reader can check the same things."""
    path = fidelity.attest(
        target,
        "root",
        "screened-and-signed",
        attestor="reviewer",
        date="2026-09-12",
        evidence="back-translation agreed; the two edge cases were checked by hand",
        evidence_files=("targets/euclid-primes/qa/root.md",),
        exhibits=({"kind": "back-translation", "path": "qa/root-bt.txt", "note": None},),
    )
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert doc["evidence_files"] == ["targets/euclid-primes/qa/root.md"]
    assert doc["exhibits"][0]["kind"] == "back-translation"
