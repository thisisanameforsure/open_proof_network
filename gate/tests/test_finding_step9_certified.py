"""F07-T17: step 9 is satisfied by the root's certificate or its registry provenance (D-4 v3.11).

D-4 step 9: "satisfied by the root's fidelity certificate (D-9, at least screened-and-signed) or
its D-10 registry provenance, checked at merge; a per-pull-request approving review by a
non-author only where the root has neither", and "the attestation records the certificate or
provenance it relied on in place of a reviewer". The owner restated it on 2026-09-14: a verified
Lean statement, or one from a trustworthy source, skips the human judgment.

Until T17 the classifier never consulted either, so every proof and partial waited for a person.
The rule as ``opn-gate classify`` now publishes it, for a building mode (``proof``, ``partial``):

- **certificate** — the root's counting certificates (``fidelity/v2``, pinned to the root as it
  stands, F11-T9) grade it at least ``screened-and-signed``; the reference is the newest counting
  signing certificate's path relative to the target directory.
- **provenance** — otherwise, ``target.yaml``'s provenance is a D-10 registry
  (``formal-conjectures``) with a non-empty ``upstream_commit`` and ``upstream_path``; the
  reference is ``formal-conjectures:<path>@<commit>``.
- **pr-approval** — otherwise a non-author approving review, as before.

Two fields carry it: ``review_kind`` (``certificate`` | ``provenance`` | ``pr-approval`` | null
where step 9 is not asked) and ``review_reference`` (string or null). ``needs_review`` is false
under a certificate or provenance. Alternates, curator records and intakes are unchanged.

Every case runs ``opn-gate classify`` over a git checkout, the way the graph's workflow does.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from harness import TARGET, TUTORIAL, copy_graph, take_in
from test_cli_sandboxed import Seam, git_repo, postmerge_argv, run

from opn_gate import cli, evidence, fidelity, schemas

TARGET_ID = "euclid-primes"
ROOT = "and-reassoc"  # take_in reuses this fixture node as the new target's root
CURATOR = "curator"  # take_in's intake author
OTHER_CURATOR = "second-curator"
SUBJECT_AUTHOR = "author"  # samples.target_record's provenance.author
ATTESTOR = "reviewer"
PROVER = "prover"
FC_COMMIT = "c7f31d5fd3d2ca3d69979f2d213eb9b58fe956ae"
FC_PATH = "FormalConjectures/ErdosProblems/52.lean"
FC_REFERENCE = f"formal-conjectures:{FC_PATH}@{FC_COMMIT}"


def fc_provenance(**fields: Any) -> dict[str, Any]:
    """The provenance ``intake import-fc`` writes (``intake.fc_record``)."""
    doc: dict[str, Any] = {
        "statement_source": "formal-conjectures",
        "author": SUBJECT_AUTHOR,
        "adversarially_reviewed": False,
        "upstream_commit": FC_COMMIT,
        "upstream_path": FC_PATH,
    }
    doc.update(fields)
    return doc


class Repo:
    """A git checkout of a graph holding one curated target whose root is unproved."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.env = {
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@x",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@x",
            "PATH": "/usr/bin:/bin",
            "HOME": str(root.parent),
        }

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=True,
            env=self.env,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def commit(self, message: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message)

    @property
    def target(self) -> Path:
        return self.root / "targets" / TARGET_ID

    @property
    def node(self) -> Path:
        return self.target / "nodes" / ROOT


def write_curators(root: Path, *logins: str) -> None:
    identities = [{"pseudonym": login, "github_login": login} for login in logins]
    (root / "curators.json").write_text(json.dumps({"identities": identities}))


def curated(tmp_path: Path, *, keep_proof: bool = False, **record: Any) -> tuple[Repo, str]:
    """A taken-in target, not yet committed; returns the repo and the root's proof text, which
    was removed from the tree unless ``keep_proof`` (a real root enters unproved, D-6)."""
    root = copy_graph(tmp_path)
    take_in(root, TARGET_ID, **record)
    proof = root / "targets" / TARGET_ID / "nodes" / ROOT / "Proof.lean"
    text = proof.read_text(encoding="utf-8")
    if not keep_proof:
        proof.unlink()
    write_curators(root, CURATOR)
    repo = Repo(root)
    repo.git("init", "-q")
    return repo, text


def certificate(repo: Repo, name: str, **fields: Any) -> Path:
    """A certificate written by hand: ``fidelity/v2`` for the root, pinned to the root as it
    stands, screened-and-signed by a non-author, unless a field says otherwise."""
    doc: dict[str, Any] = {
        "schema": fidelity.SCHEMA,
        "subject": fidelity.ROOT_SUBJECT,
        "statement_hash": fidelity.current_hash(repo.target, fidelity.ROOT_SUBJECT),
        "grade": "screened-and-signed",
        "subject_author": SUBJECT_AUTHOR,
        "attestor": ATTESTOR,
        "date": "2026-09-12",
        "evidence": "read the Lean statement against the informal one; they agree",
        **fields,
    }
    doc = {key: value for key, value in doc.items() if value is not None}
    path = repo.target / "fidelity" / name
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return path


def submit_proof(repo: Repo, text: str) -> None:
    (repo.node / "Proof.lean").write_text(text, encoding="utf-8")
    repo.commit("a proof of the root")


def submit_partial(repo: Repo) -> None:
    assembly = repo.node / "attempts" / "20260914T000000Z-prover-partial.lean"
    assembly.parent.mkdir(parents=True, exist_ok=True)
    assembly.write_text("-- an assembly with holes\n", encoding="utf-8")
    repo.commit("a partial of the root")


def classify(
    repo: Repo, capsys: pytest.CaptureFixture[str], *, author: str = PROVER
) -> tuple[int, dict[str, Any]]:
    """``opn-gate classify`` over the checkout's last commit, as the graph's workflow runs it."""
    capsys.readouterr()
    code = cli.main(["classify", "--graph", str(repo.root), "--base", "HEAD~1", "--author", author])
    return code, json.loads(capsys.readouterr().out)


def step9(out: dict[str, Any]) -> tuple[Any, Any, Any]:
    return out.get("needs_review"), out.get("review_kind"), out.get("review_reference")


# --- (a)-(c) the root's certificate ---------------------------------------------------------------


def test_a_a_signed_root_certificate_satisfies_step9(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """(a) D-4 v3.11: a screened-and-signed certificate for the root as it stands satisfies step 9;
    nobody is asked to approve, and the reference names the certificate file."""
    repo, proof = curated(tmp_path)
    certificate(repo, "root-2.yaml")
    repo.commit("base: the root is screened and signed")
    submit_proof(repo, proof)
    code, out = classify(repo, capsys)
    assert code == 0 and out["mode"] == "proof" and out["needs_gate"] is True, out
    assert step9(out) == (False, "certificate", "fidelity/root-2.yaml"), out


def test_a_the_reference_is_the_newest_signing_certificate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """(a) With two counting signatures the reference is the newer one — by the order
    ``fidelity.load`` keeps, ``(date, file name)`` — at a higher rung here."""
    repo, proof = curated(tmp_path)
    certificate(repo, "root-2.yaml")
    certificate(repo, "root-3.yaml", grade="author-attested", attestor="poser", date="2026-09-13")
    repo.commit("base: signed twice")
    submit_proof(repo, proof)
    _code, out = classify(repo, capsys)
    assert step9(out) == (False, "certificate", "fidelity/root-3.yaml"), out


def test_b_a_mechanical_only_certificate_needs_a_review(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """(b) D-9: mechanical-only is the machine's own rung, not a signature. Intake wrote one
    (root-1); another written by hand changes nothing: a non-author approving review is needed."""
    repo, proof = curated(tmp_path)
    assert (repo.target / "fidelity" / "root-1.yaml").is_file()
    certificate(repo, "root-2.yaml", grade="mechanical-only", attestor=SUBJECT_AUTHOR)
    repo.commit("base: mechanical-only")
    submit_proof(repo, proof)
    code, out = classify(repo, capsys)
    assert code == 0 and out["mode"] == "proof", out
    assert step9(out) == (True, "pr-approval", None), out


def test_b_a_later_downgrade_takes_the_certificate_away(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """(b) F11-R3: a subject's grade is its *latest* counting certificate's. A signature followed
    by a mechanical-only certificate leaves the root at mechanical-only, so step 9 is a review."""
    repo, proof = curated(tmp_path)
    certificate(repo, "root-2.yaml", date="2026-09-12")
    certificate(
        repo, "root-3.yaml", grade="mechanical-only", attestor=SUBJECT_AUTHOR, date="2026-09-13"
    )
    repo.commit("base: signed, then downgraded")
    submit_proof(repo, proof)
    _code, out = classify(repo, capsys)
    assert step9(out) == (True, "pr-approval", None), out


@pytest.mark.parametrize(
    "fields",
    [
        pytest.param({"statement_hash": "a" * 64}, id="pinned-to-an-old-root"),
        pytest.param({"schema": "fidelity/v1", "statement_hash": None}, id="v1-pins-nothing"),
    ],
)
def test_c_a_certificate_for_another_statement_does_not_count(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], fields: dict[str, Any]
) -> None:
    """(c) F11-T9: a certificate counts only for the statement it pins. One signed against an old
    root hash — or a v1 certificate, which pins none — satisfies nothing."""
    repo, proof = curated(tmp_path)
    certificate(repo, "root-2.yaml", **fields)
    repo.commit("base: a signature for a different statement")
    submit_proof(repo, proof)
    code, out = classify(repo, capsys)
    assert code == 0 and out["mode"] == "proof", out
    assert step9(out) == (True, "pr-approval", None), out


def test_c_a_proof_cannot_bring_its_own_certificate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """(c) The classifier reads certificates from the merge checkout, so what stands in for step 9
    must already be on the base: a pull request that adds a signature beside the proof it would
    excuse is not a proof at all (``mode-mixed``, F11-R3's own pull request)."""
    repo, proof = curated(tmp_path)
    repo.commit("base: mechanical-only")
    certificate(repo, "root-2.yaml")
    (repo.node / "Proof.lean").write_text(proof, encoding="utf-8")
    repo.commit("a proof, and a signature for its statement")
    code, out = classify(repo, capsys)
    assert code != 0 and out["mode"] is None, out
    assert [p["code"] for p in out["problems"]] == ["mode-mixed"], out
    assert step9(out) == (False, None, None), out


def test_c_a_proof_cannot_bring_its_own_evidence(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """F14-AC5: an evidence record is a curator's record, so one added beside the proof it would
    excuse makes the pull request ``mode-mixed``, exactly as a certificate does."""
    repo, proof = curated(tmp_path, provenance=fc_provenance())
    repo.commit("base: an imported statement, no evidence")
    evidence_record(repo, score=8)
    (repo.node / "Proof.lean").write_text(proof, encoding="utf-8")
    repo.commit("a proof, and evidence for its statement")
    code, out = classify(repo, capsys)
    assert code != 0 and out["mode"] is None, out
    assert "mode-mixed" in [p["code"] for p in out["problems"]], out
    assert step9(out) == (False, None, None), out


# --- (d)-(f) F14-R5: recorded catalog evidence, never provenance alone --------------------------


LETTERS = {4: "B", 5: "B+", 6: "A", 8: "A"}


def evidence_record(repo: Repo, *, score: int = 6, statement_hash: str | None = None) -> str:
    """A statement-evidence record for the root at ``score``, pinned to the root as it stands
    unless a hash is given; returns the reference the attestation would cite (F14-R6)."""
    root_hash = statement_hash or fidelity.current_hash(repo.target, fidelity.ROOT_SUBJECT)
    doc = samples.statement_evidence(statement_hash=root_hash)
    doc["catalog"] = {**doc["catalog"], "score": score, "letter": LETTERS[score]}
    path = evidence.write(repo.target, doc)
    return f"evidence:evidence/{path.name}@{root_hash}:{score}"


def test_d_formal_conjectures_provenance_alone_needs_a_review(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """(d) F14-R5 (Mike, 2026-09-14): where a statement came from is not evidence that it says
    what the conjecture says. A root inherited from Formal Conjectures at a pinned commit and
    path, with no evidence record, asks a non-author's review."""
    repo, proof = curated(tmp_path, provenance=fc_provenance())
    repo.commit("base: an imported statement, no evidence recorded")
    submit_proof(repo, proof)
    code, out = classify(repo, capsys)
    assert code == 0 and out["mode"] == "proof", out
    assert step9(out) == (True, "pr-approval", None), out


@pytest.mark.parametrize("score", [5, 6, 8])
def test_d_catalog_evidence_at_the_minimum_satisfies_step9(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], score: int
) -> None:
    """(d) F14-R5, R6: a current evidence record scoring at least five stands in for the review,
    recorded as ``provenance`` with the reference naming the record, the hash and the score."""
    repo, proof = curated(tmp_path, provenance=fc_provenance())
    reference = evidence_record(repo, score=score)
    repo.commit("base: an imported statement with its catalog evidence")
    submit_proof(repo, proof)
    code, out = classify(repo, capsys)
    assert code == 0 and out["mode"] == "proof", out
    assert step9(out) == (False, "provenance", reference), out


def test_e_evidence_below_the_minimum_needs_a_review(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """(e) F14-R5: four points is B, below the high grade — a person reviews the proof."""
    repo, proof = curated(tmp_path, provenance=fc_provenance())
    evidence_record(repo, score=4)
    repo.commit("base: evidence at four")
    submit_proof(repo, proof)
    _code, out = classify(repo, capsys)
    assert step9(out) == (True, "pr-approval", None), out


def test_e_evidence_for_another_statement_needs_a_review(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """(e) F14-R3: a record pinned to another hash counts for nothing, however high it scored."""
    repo, proof = curated(tmp_path, provenance=fc_provenance())
    evidence_record(repo, score=8, statement_hash="a" * 64)
    repo.commit("base: evidence recorded against an earlier root")
    submit_proof(repo, proof)
    _code, out = classify(repo, capsys)
    assert step9(out) == (True, "pr-approval", None), out


def test_e_the_minimum_is_configuration(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """(e) C6, F14-Q4: the minimum is read from OPN_STEP9_MIN_SCORE; raised to seven, a record at
    six asks a review."""
    monkeypatch.setenv("OPN_STEP9_MIN_SCORE", "7")
    repo, proof = curated(tmp_path, provenance=fc_provenance())
    evidence_record(repo, score=6)
    repo.commit("base: evidence at six")
    submit_proof(repo, proof)
    _code, out = classify(repo, capsys)
    assert step9(out) == (True, "pr-approval", None), out


@pytest.mark.parametrize(
    "provenance",
    [
        pytest.param(fc_provenance(upstream_commit=None), id="no-upstream-commit"),
        pytest.param(fc_provenance(upstream_path=""), id="empty-upstream-path"),
        pytest.param(fc_provenance(upstream_path=None), id="no-upstream-path"),
        pytest.param(fc_provenance(statement_source="network"), id="not-a-registry"),
    ],
)
def test_e_incomplete_or_non_registry_provenance_needs_a_review(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], provenance: dict[str, Any]
) -> None:
    """(e) D-10: inheritance is at an immutable commit, which is part of provenance. A
    formal-conjectures record missing the commit or the path, or a statement the network wrote
    itself, is not registry provenance: a review is needed."""
    repo, proof = curated(tmp_path, provenance=provenance)
    repo.commit("base: provenance that is not a pinned registry import")
    submit_proof(repo, proof)
    code, out = classify(repo, capsys)
    assert code == 0 and out["mode"] == "proof", out
    assert step9(out) == (True, "pr-approval", None), out


def test_f_a_certificate_is_preferred_over_evidence(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """(f) When both hold, the certificate is what the attestation relies on: a person's signature
    on the statement as it stands says more than a catalog score."""
    repo, proof = curated(tmp_path, provenance=fc_provenance())
    certificate(repo, "root-2.yaml")
    evidence_record(repo, score=8)
    repo.commit("base: imported, evidenced and signed")
    submit_proof(repo, proof)
    _code, out = classify(repo, capsys)
    assert step9(out) == (False, "certificate", "fidelity/root-2.yaml"), out


def test_f_a_stale_certificate_falls_back_to_evidence(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """(f) A certificate that does not count is no certificate: current evidence still stands."""
    repo, proof = curated(tmp_path, provenance=fc_provenance())
    certificate(repo, "root-2.yaml", statement_hash="a" * 64)
    reference = evidence_record(repo, score=6)
    repo.commit("base: evidenced, signed against an old root")
    submit_proof(repo, proof)
    _code, out = classify(repo, capsys)
    assert step9(out) == (False, "provenance", reference), out


# --- (g) partial mode -----------------------------------------------------------------------------


@pytest.mark.parametrize("basis", ["certificate", "evidence", "neither"])
def test_g_a_partial_is_treated_like_a_proof(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], basis: str
) -> None:
    """(g) D-4 v3.20 (F07-T24): a skeleton settles nothing, so step 9 is not asked of it whatever
    stands behind the root; whoever later closes the root is the one the rule speaks to. Until
    v3.20 a partial was treated like a proof ("every kernel-checked artifact of D-12 alike"),
    which still holds among the artifacts that *close* a node."""
    repo, _proof = curated(tmp_path, provenance=fc_provenance())
    expected: tuple[Any, Any, Any] = (False, "intermediate", None)
    if basis == "certificate":
        certificate(repo, "root-2.yaml")
    elif basis == "evidence":
        evidence_record(repo, score=5)
    repo.commit("base")
    submit_partial(repo)
    code, out = classify(repo, capsys)
    assert code == 0 and out["mode"] == "partial", out
    assert step9(out) == expected, out


# --- (h), (i) the modes that do not change ------------------------------------------------------


def test_h_an_alternate_still_asks_no_review(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """(h) D-4 v3.13: step 9 is not asked of an alternate, certified root or not; its review_kind
    is null, not the certificate, because the alternate's record names no step-9 basis."""
    repo, _proof = curated(tmp_path, keep_proof=True, provenance=fc_provenance())
    certificate(repo, "root-2.yaml")
    repo.commit("base: a proved, certified root")
    alternate = repo.node / "attempts" / "20260914T000000Z-prover-alternate.lean"
    alternate.parent.mkdir(parents=True, exist_ok=True)
    alternate.write_text("-- a different proof\n", encoding="utf-8")
    repo.commit("an alternate proof")
    code, out = classify(repo, capsys)
    assert code == 0 and out["mode"] == "alternate", out
    assert step9(out) == (False, None, None), out


@pytest.mark.parametrize(
    ("curators", "expected"),
    [
        pytest.param((CURATOR,), (False, None, None, [], "single-curator"), id="waived"),
        pytest.param(
            (CURATOR, OTHER_CURATOR),
            (True, "pr-approval", None, [OTHER_CURATOR], None),
            id="second-curator",
        ),
    ],
)
def test_i_a_curator_record_is_unchanged_under_a_certified_root(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    curators: tuple[str, ...],
    expected: tuple[Any, ...],
) -> None:
    """(i) F08-R8: a certificate or provenance on the root does not stand in for a second curator;
    a curator record is reviewed by another listed identity, or waived, exactly as before."""
    repo, _proof = curated(tmp_path, provenance=fc_provenance())
    certificate(repo, "root-2.yaml")
    write_curators(repo.root, *curators)
    repo.commit("base: certified and imported")
    record = repo.node / "status" / "20260914T000000Z-curator.yaml"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(yaml.safe_dump(samples.node_status(author=CURATOR), sort_keys=True))
    repo.commit("a status record")
    code, out = classify(repo, capsys, author=CURATOR)
    assert code == 0 and out["mode"] == "curator", out
    got = (*step9(out), out.get("reviewers"), out.get("review_waived"))
    assert got == expected, out


def test_i_an_intake_is_unchanged_by_its_own_provenance(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """(i) F11-R2: an intake is reviewed by a second listed curator whatever its record says —
    the provenance an intake carries is what the review looks at, not a way around it."""
    root = copy_graph(tmp_path)
    write_curators(root, CURATOR, OTHER_CURATOR)
    repo = Repo(root)
    repo.git("init", "-q")
    repo.commit("before the intake")
    take_in(root, TARGET_ID, provenance=fc_provenance())
    (repo.node / "Proof.lean").unlink()
    repo.commit(f"intake: {TARGET_ID}")
    code, out = classify(repo, capsys, author=CURATOR)
    assert code == 0 and out["mode"] == "intake", out
    assert (*step9(out), out.get("reviewers")) == (True, "pr-approval", None, [OTHER_CURATOR]), out


# --- (j) the classification document the workflow reads -------------------------------------------


def test_j_the_fields_are_published_on_a_target_that_predates_f11(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """(j) The workflow reads ``review_kind`` and ``review_reference`` from the classify JSON.
    On a target with no target.yaml and no certificates — the tutorial's shape — the fields are
    still published. The fixture's tutorial node is not its target's root, so since v3.20
    (F07-T24) a proof of it is ``intermediate``; the tutorial exemption stays the workflow's
    flag either way."""
    root, _git, _base = git_repo(tmp_path)
    capsys.readouterr()
    code = cli.main(["classify", "--graph", str(root), "--base", "HEAD~1", "--author", PROVER])
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["mode"] == "proof" and out["target"] == TARGET, out
    assert out["node"] == TUTORIAL, out
    assert {"review_kind", "review_reference"} <= set(out), sorted(out)
    assert step9(out) == (False, "intermediate", None), out


def test_j_an_unreadable_certificate_asks_for_a_review_rather_than_failing_open(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """(j) C7: when the root's certificates cannot be read, nothing stands in for the review, and
    the classification is still published — a person is asked, never skipped."""
    repo, proof = curated(tmp_path, provenance=fc_provenance(upstream_commit=None))
    (repo.target / "fidelity" / "root-2.yaml").write_text("schema: vibes/v1\n", encoding="utf-8")
    repo.commit("base: a broken certificate")
    submit_proof(repo, proof)
    code, out = classify(repo, capsys)
    assert code == 0 and out["mode"] == "proof", out
    assert step9(out) == (True, "pr-approval", None), out


# --- (k) the post-merge record -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "reference"),
    [("certificate", "fidelity/root-2.yaml"), ("provenance", FC_REFERENCE)],
)
def test_k_postmerge_records_what_stood_in_for_the_reviewer(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str], kind: str, reference: str
) -> None:
    """(k) D-4 v3.11: "the attestation records the certificate or provenance it relied on in place
    of a reviewer" — ``postmerge --review-kind <kind> --review-reference <ref>`` writes
    ``review {kind, reference, reviewer: null}`` into a schema-valid attestation."""
    root, _git, _base = git_repo(tmp_path)
    out_dir = tmp_path / kind
    code, out, err = run(
        capsys,
        *postmerge_argv(root, out_dir, "--review-kind", kind, "--review-reference", reference),
    )
    assert code == cli.EXIT_PASS and out["verdict"] == "pass", (out, err)
    doc = schemas.load_json(out_dir / "attestation.json")
    assert doc["review"] == {"kind": kind, "reviewer": None, "reference": reference}, doc
    assert schemas.violations(doc) == []
