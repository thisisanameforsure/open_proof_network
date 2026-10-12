"""F26-T8 / AC9: step 9 reads the formalization review (F26-R12; D-4 v3.39).

v3.39: "A proof that would settle a target's root merges only when that target's review is
complete — automated stages done, no open question, grade at least screened-and-signed — so
intermediate work never waits for the review and the claim that a conjecture is settled always
does. v3.15's second basis stands beside it: recorded catalog evidence about the statement scoring
at least five points still satisfies step 9 without a completed review."

AC9: given a proof that settles a root whose review is incomplete, when step 9 runs, then it does
not approve and the verdict names the review's state; given catalog evidence at five points, then
it approves as v3.15 says; given an intermediate node, then the review is not consulted. And
F26-Q7: a target with no review keeps today's rule exactly.

Every case runs ``opn-gate classify`` over a git checkout, as the graph's workflow does, with the
review's records written by T2's schema-checked builder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from test_finding_step9_certified import (
    TARGET_ID,
    Repo,
    certificate,
    classify,
    curated,
    evidence_record,
    fc_provenance,
    step9,
    submit_partial,
    submit_proof,
)
from test_review_state import A, B, Review

from opn_gate import fidelity, products
from opn_gate import graph as graphmod
from opn_gate.steps import review_step

INDEPENDENT = "reviewer"  # wrote no candidate: a non-author signature (D-9)
HELD = "review-incomplete"


def codes(out: dict[str, Any]) -> list[str]:
    return [p["code"] for p in out["problems"]]


def complete_review(repo: Repo, *, signed: bool = True) -> Review:
    """One model's candidate surviving alone, no question: the review is ``complete``; with
    ``signed``, an independent accept lifts it to screened-and-signed (the cap for a review with
    no person's candidate). Opened by a curator: the network's background review never decides
    step 9 (F26-Q16), so a review that satisfies it is one a person opened."""
    r = Review(repo.target, role="curator", identity="curator")
    r.candidate(A, "model-runner")
    if signed:
        r.signature("independent", "accept", INDEPENDENT)
    return r


def review_reference(repo: Repo, grade: str = "screened-and-signed") -> str:
    root_hash = fidelity.current_hash(repo.target, fidelity.ROOT_SUBJECT)
    return f"review:review/review.yaml@{root_hash}:{grade}"


# --- AC9 (a): an incomplete review holds a proof that would settle the root --------------------


def question_waiting(repo: Repo) -> None:
    r = Review(repo.target, role="curator", identity="curator")
    r.candidate(A, "model-runner")
    r.question("q-11111111")
    r.signature("independent", "accept", INDEPENDENT)


def two_readings(repo: Repo) -> None:
    r = Review(repo.target, role="curator", identity="curator")
    r.candidate(A, "model-runner")
    r.candidate(B, "other-runner")


def no_survivor(repo: Repo) -> None:
    r = Review(repo.target, role="curator", identity="curator")
    r.candidate(A, "model-runner")
    r.exhibit("compile", A, "fail")


def network_waiting(repo: Repo) -> None:
    r = Review(repo.target)  # opened by the network, nobody has answered or signed as intent
    r.candidate(A, "model-runner")
    r.question("q-11111111")
    r.question("q-22222222")


@pytest.mark.parametrize(
    ("build", "state", "words"),
    [
        pytest.param(question_waiting, "open", "review open: 1 question waiting", id="question"),
        pytest.param(two_readings, "open", "review open: 2 readings survive", id="two-readings"),
        pytest.param(no_survivor, "open", "review open: no candidate survives", id="no-survivor"),
        # The network's background review waiting for an intent signer held here until the owner's
        # ruling of 2026-10-12 (F26-Q16): a background review never holds step 9; see below.
    ],
)
def test_ac9_an_incomplete_review_holds_a_proof_of_the_root(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    build: Any,
    state: str,
    words: str,
) -> None:
    """AC9: step 9 does not approve, and the verdict names the review's state."""
    repo, proof = curated(tmp_path)
    build(repo)
    repo.commit("base: the review is under way")
    submit_proof(repo, proof)
    code, out = classify(repo, capsys)
    assert code != 0 and out["ok"] is False and out["mode"] == "proof", out
    assert codes(out) == [HELD], out
    held = out["problems"][0]
    assert words in held["message"], held
    assert held["details"]["review_state"] == state, held
    assert out["review_state"] == words, out


def test_ac9_a_root_certificate_does_not_stand_in_for_an_incomplete_review(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """v3.39: once a target has a review, the claim that its conjecture is settled waits for the
    review. A screened-and-signed certificate that approved alone before (F07-T17) does not stand in
    for a review with a question waiting."""
    repo, proof = curated(tmp_path)
    certificate(repo, "root-2.yaml")
    question_waiting(repo)
    repo.commit("base: certified, and a review with a question waiting")
    submit_proof(repo, proof)
    code, out = classify(repo, capsys)
    assert code != 0 and codes(out) == [HELD], out


def test_ac9_a_complete_review_below_screened_and_signed_holds(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Complete is not enough: the grade must be at least screened-and-signed, and a review nobody
    has signed earns only the floor."""
    repo, proof = curated(tmp_path)
    complete_review(repo, signed=False)
    repo.commit("base: complete, unsigned")
    submit_proof(repo, proof)
    code, out = classify(repo, capsys)
    assert code != 0 and codes(out) == [HELD], out
    assert out["review_state"] == "review complete at mechanical-only, below screened-and-signed"


# --- the review's own basis -----------------------------------------------------------------


def test_a_complete_signed_review_satisfies_step9(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The review complete at screened-and-signed approves with no person asked, recorded as the
    D-9 grade it earned (the attestation's ``certificate`` kind) naming the review, the root hash
    it was about and the grade."""
    repo, proof = curated(tmp_path)
    complete_review(repo)
    repo.commit("base: complete and signed")
    submit_proof(repo, proof)
    code, out = classify(repo, capsys)
    assert code == 0 and out["ok"] is True, out
    assert step9(out) == (False, "certificate", review_reference(repo)), out
    assert out["review_state"] == "review complete at screened-and-signed", out


def test_a_complete_review_keeps_a_held_grade(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``review.grade_of`` never lowers a held grade: a root certified screened-and-signed whose
    review is complete but unsigned stands at screened-and-signed, and step 9 approves."""
    repo, proof = curated(tmp_path)
    certificate(repo, "root-2.yaml")
    complete_review(repo, signed=False)
    repo.commit("base: certified, review complete")
    submit_proof(repo, proof)
    code, out = classify(repo, capsys)
    assert code == 0, out
    assert step9(out) == (False, "certificate", review_reference(repo)), out


# --- AC9 (b): v3.15's catalog evidence stands beside the review -------------------------------


@pytest.mark.parametrize("score", [5, 8])
def test_ac9_catalog_evidence_at_five_approves_with_an_incomplete_review(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], score: int
) -> None:
    """AC9: catalog evidence at five points approves as v3.15 says — recorded as ``provenance``
    with the evidence reference, exactly as F14-R6 — and the review's state is still named."""
    repo, proof = curated(tmp_path, provenance=fc_provenance())
    reference = evidence_record(repo, score=score)
    question_waiting(repo)
    repo.commit("base: evidence, and a review with a question waiting")
    submit_proof(repo, proof)
    code, out = classify(repo, capsys)
    assert code == 0 and out["ok"] is True, out
    assert step9(out) == (False, "provenance", reference), out
    assert out["review_state"] == "review open: 1 question waiting", out


def test_evidence_below_five_does_not_stand_in(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo, proof = curated(tmp_path, provenance=fc_provenance())
    evidence_record(repo, score=4)
    question_waiting(repo)
    repo.commit("base: weak evidence, review open")
    submit_proof(repo, proof)
    code, out = classify(repo, capsys)
    assert code != 0 and codes(out) == [HELD], out


# --- AC9 (c): intermediate work never consults the review -------------------------------------


def test_ac9_an_intermediate_artifact_does_not_consult_the_review(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A partial settles nothing (D-12 v3.19): step 9 is not asked and the review is not read —
    shown by a review reader that fails the test if it is called."""
    repo, _proof = curated(tmp_path)
    question_waiting(repo)
    repo.commit("base: a review with a question waiting")
    submit_partial(repo)

    def consulted(target_dir: Path) -> None:
        pytest.fail(f"the review of {target_dir.name} was read for intermediate work")

    monkeypatch.setattr(review_step, "standing", consulted)
    code, out = classify(repo, capsys)
    assert code == 0 and out["mode"] == "partial", out
    assert step9(out) == (False, "intermediate", None), out
    assert out["review_state"] is None, out


def test_a_calibration_target_does_not_consult_the_review(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-4 v3.20: a known result asks no step 9 even of its root, so no review is read."""
    repo, proof = curated(tmp_path, track="formalization", calibration=True)
    question_waiting(repo)
    repo.commit("base: a calibration target with a review")
    submit_proof(repo, proof)
    monkeypatch.setattr(review_step, "standing", lambda _d: pytest.fail("review read"))
    code, out = classify(repo, capsys)
    assert code == 0, out
    assert step9(out) == (False, "calibration", None), out


# --- F26-Q7: no review, today's rule exactly ----------------------------------------------------


def test_no_review_a_certificate_still_approves(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo, proof = curated(tmp_path)
    certificate(repo, "root-2.yaml")
    repo.commit("base: certified, no review")
    submit_proof(repo, proof)
    code, out = classify(repo, capsys)
    assert code == 0, out
    assert step9(out) == (False, "certificate", "fidelity/root-2.yaml"), out
    assert out["review_state"] is None, out


def test_no_review_evidence_still_approves(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo, proof = curated(tmp_path, provenance=fc_provenance())
    reference = evidence_record(repo, score=5)
    repo.commit("base: evidence, no review")
    submit_proof(repo, proof)
    code, out = classify(repo, capsys)
    assert code == 0, out
    assert step9(out) == (False, "provenance", reference), out


def test_no_review_a_person_is_still_asked(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With neither certificate nor evidence and no review, step 9 asks a non-author's approval,
    as before v3.39; the classification passes and the workflow's step-9 job waits for one."""
    repo, proof = curated(tmp_path)
    repo.commit("base: nothing stands in, no review")
    submit_proof(repo, proof)
    code, out = classify(repo, capsys)
    assert code == 0 and codes(out) == [], out
    assert step9(out) == (True, "pr-approval", None), out
    assert out["review_state"] is None, out


def test_a_review_directory_without_its_opening_is_no_review(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``review.state_of`` reads ``none`` until ``review.yaml`` exists, so a stray record beside no
    opening changes nothing (F26-Q7)."""
    repo, proof = curated(tmp_path)
    certificate(repo, "root-2.yaml")
    (repo.target / "review" / "questions").mkdir(parents=True)
    (repo.target / "review" / "questions" / "q-11111111.yaml").write_text("id: q-11111111\n")
    repo.commit("base: certified, a stray review record")
    submit_proof(repo, proof)
    code, out = classify(repo, capsys)
    assert code == 0, out
    assert step9(out) == (False, "certificate", "fidelity/root-2.yaml"), out


# --- the product says what the gate decides (targets-index ``step9``, F14-R9) ------------------


def certified(repo: Repo) -> None:
    certificate(repo, "root-2.yaml")


def certified_review_open(repo: Repo) -> None:
    certificate(repo, "root-2.yaml")
    question_waiting(repo)


def evidence_review_open(repo: Repo) -> None:
    evidence_record(repo, score=5)
    question_waiting(repo)


@pytest.mark.parametrize(
    ("build", "expected"),
    [
        pytest.param(certified, "certificate", id="no-review"),
        pytest.param(certified_review_open, "review", id="certified-review-open"),
        pytest.param(complete_review, "certificate", id="review-complete"),
        pytest.param(evidence_review_open, "evidence", id="evidence-review-open"),
    ],
)
def test_the_products_step9_field_follows_the_review(
    tmp_path: Path, build: Any, expected: str
) -> None:
    """``targets/index.json``'s ``step9`` is what a proof of the root needs at merge, as the gate
    decides it from the tree: published state is actual state, so it reads the review too."""
    repo, _proof = curated(tmp_path, provenance=fc_provenance())
    build(repo)
    tg = graphmod.load_target(repo.root, TARGET_ID)
    assert products.step9_basis(tg) == expected


# --- F26-Q16 (the owner's ruling, 2026-10-12): a background review never holds step 9 ----------


def test_a_background_review_waiting_does_not_hold_a_certified_root(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The network's review of an existing target informs and files defects; it never holds a
    proof that settles the root. A screened-and-signed certificate approves as before v3.39, though
    the review waits for an intent signer the target does not have."""
    repo, proof = curated(tmp_path)
    certificate(repo, "root-2.yaml")
    network_waiting(repo)
    repo.commit("base: certified, and the background review waiting for an intent signer")
    submit_proof(repo, proof)
    code, out = classify(repo, capsys)
    assert code == 0 and codes(out) == [], out
    assert step9(out) == (False, "certificate", "fidelity/root-2.yaml"), out


def test_a_background_review_leaves_a_person_asked_as_before(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With nothing standing in and only a background review, step 9 asks a person, as it did
    before v3.39; the review is not consulted in either direction."""
    repo, proof = curated(tmp_path)
    network_waiting(repo)
    repo.commit("base: a background review, nothing else")
    submit_proof(repo, proof)
    code, out = classify(repo, capsys)
    assert code == 0 and codes(out) == [], out
    assert step9(out) == (True, "pr-approval", None), out


def test_the_products_step9_field_ignores_a_background_review(tmp_path: Path) -> None:
    """Published state equals actual state: the targets-index ``step9`` field reads the same
    standing the gate does, so a background review leaves it as the certificate says."""
    repo, _proof = curated(tmp_path)
    certificate(repo, "root-2.yaml")
    network_waiting(repo)
    repo.commit("base")
    assert review_step.standing(repo.target) is None
    tg = graphmod.load_target(repo.root, repo.target.name)
    assert products.step9_basis(tg) == "certificate"


def test_a_review_a_person_opened_still_holds(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The carve-out is for the network's background review only: a review a curator opened on
    a certified target still holds the root's proof until it completes (D-9 v3.39)."""
    repo, proof = curated(tmp_path)
    certificate(repo, "root-2.yaml")
    question_waiting(repo)
    repo.commit("base")
    submit_proof(repo, proof)
    code, out = classify(repo, capsys)
    assert code != 0 and codes(out) == [HELD], out
