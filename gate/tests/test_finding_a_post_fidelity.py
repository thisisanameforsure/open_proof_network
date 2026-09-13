"""Finding A: on a curated target, the acts that make it claimable must pass the classifier.

F11-R5 says ``intake post`` and ``intake activate`` are "each a curator PR"; F11-R3 keeps fidelity
certificates append-only under ``targets/<id>/fidelity/``; F11-R4 makes a target claimable only
with status active, grade >= screened-and-signed and a non-null posting; D-6 says "claims are
blocked until its fidelity grade reaches screened-and-signed (D-9) and the D-10 posting is made".
So each of the three acts has to reach the graph through a pull request the gate classifies.

Until F11-T8 two of them could not: ``intake post`` rewrites ``target.yaml`` and ``target-record``
was not modifiable (``path-forbidden``), and a lone certificate was routed to intake
(``intake-incomplete``). The rules decided by the owner on 2026-09-13, as ``modes`` now holds them:

- **Posting** is a curator PR modifying ``targets/<id>/target.yaml`` alone, where the base and
  head records differ only in ``posting``, null to a schema-valid posting
  (``modes.check_posting``).
- **A certificate is the signer's own PR**: new certificate files for one subject of a curated
  target and nothing else, opened by the attestor, non-author above mechanical-only, agreeing
  with the subject's author on record, and from screened-and-signed up only on a QA pass complete
  for the statement as it stands (``modes.check_certificate``; mode ``fidelity``).
- **Activation is re-checked at merge**: a status record declaring a curated target ``active``
  must leave it claimable (``modes.check_activation``).

Each act is written by the function the command calls (``intake.post``, ``fidelity.attest``,
``intake.activate``) on a git checkout of a freshly taken-in target, and ``opn-gate classify`` runs
over the commit, the way the graph's workflow does. ``fidelity.attest`` is called without F12-R9's
grade gate (the library default, F12-Q15); the classifier's own QA rule is what these tests hold.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import TARGET, copy_graph, take_in

from opn_gate import cli, fidelity, intake, modes, qa, records
from opn_gate.paths import Change

TARGET_ID = "euclid-primes"
ROOT = "and-reassoc"  # take_in reuses this fixture node as the new target's root
CURATOR = "curator"  # take_in's intake author, listed in curators.json below
SUBJECT_AUTHOR = "author"  # samples.target_record's provenance.author: the root's author
ATTESTOR = "reviewer"  # a non-author (D-9)
LATER = "2026-09-12T00:00:00Z"
RECORD = f"targets/{TARGET_ID}/target.yaml"
QA_TOOL = "opn-gate qa"


class Repo:
    """A git checkout of a graph holding one freshly listed curated target."""

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


def qa_row(check: qa.Check, verdict: qa.Verdict = "pass") -> qa.Row:
    """One row as ``qa.row`` writes it; a brief records the model that produced it (F12-R2)."""
    brief = qa.KIND_OF[check] == "brief"
    return qa.row(
        check,
        verdict,
        tool=QA_TOOL,
        tool_version="0.0.0",
        timestamp=LATER,
        model="fake-model" if brief else None,
        model_version="1" if brief else None,
    )


def complete_qa_pass(target: Path, subject: str = fidelity.ROOT_SUBJECT) -> Path:
    """F12-R9's floor, every check passed for the statement as it stands — what a signature above
    mechanical-only rests on. Written through ``qa.write``, so it is a record the reader counts."""
    rows = [qa_row(check) for check in qa.floor_for(subject)]
    return qa.write(target, subject, rows, date=LATER, produced_by=QA_TOOL)


def listed(tmp_path: Path, *, qa_pass: bool) -> Repo:
    root = copy_graph(tmp_path)
    take_in(root, TARGET_ID)
    # take_in reuses a fixture node as the root; a real root enters unproved (D-6, F11-R2).
    (root / "targets" / TARGET_ID / "nodes" / ROOT / "Proof.lean").unlink()
    (root / "curators.json").write_text(
        json.dumps({"identities": [{"pseudonym": CURATOR, "github_login": CURATOR}]})
    )
    if qa_pass:
        complete_qa_pass(root / "targets" / TARGET_ID)
    r = Repo(root)
    r.git("init", "-q")
    r.commit(f"intake: list {TARGET_ID}")
    return r


@pytest.fixture
def repo(tmp_path: Path) -> Repo:
    """A listed target whose root's QA pass is complete on the base, so a signature can merge."""
    return listed(tmp_path, qa_pass=True)


@pytest.fixture
def unscreened(tmp_path: Path) -> Repo:
    """A listed target with no QA record at all."""
    return listed(tmp_path, qa_pass=False)


def classify(
    repo: Repo, capsys: pytest.CaptureFixture[str], *, author: str = CURATOR
) -> tuple[int, dict[str, Any]]:
    """``opn-gate classify`` over the checkout's last commit, as the graph's workflow runs it."""
    capsys.readouterr()
    code = cli.main(["classify", "--graph", str(repo.root), "--base", "HEAD~1", "--author", author])
    return code, json.loads(capsys.readouterr().out)


def codes(out: dict[str, Any]) -> list[str]:
    return [p["code"] for p in out["problems"]]


def messages(out: dict[str, Any]) -> str:
    return " ".join(p["message"] for p in out["problems"])


def post(repo: Repo) -> None:
    intake.post(
        repo.root,
        TARGET_ID,
        venue="erdosproblems.com",
        url="https://example.org/posting",
        date=LATER,
    )


def sign(repo: Repo, *, attestor: str = ATTESTOR, grade: str = "screened-and-signed") -> Path:
    return fidelity.attest(
        repo.target,
        fidelity.ROOT_SUBJECT,
        grade,
        attestor=attestor,
        date="2026-09-12",
        evidence="read the Lean statement against the informal one; they agree",
    )


def activate(repo: Repo) -> None:
    intake.activate(repo.root, TARGET_ID, author=CURATOR, date="2026-09-13T00:00:00Z")


def declare(repo: Repo, status: str, *, date: str, target_id: str = TARGET_ID) -> Path:
    """A target-status record written by hand, as ``opn-gate status`` writes one — bypassing
    ``intake.activate``'s refusal, which is the point: the gate must hold the rule itself."""
    target = repo.root / "targets" / target_id
    doc = intake.status_doc(
        status,
        f"declared {status} by hand",
        author=CURATOR,
        date=date,
        root=records.declared_root(target),
    )
    stamp = date.replace("-", "").replace(":", "")
    path = target / "status" / f"{stamp}-{CURATOR}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return path


def certificate(repo: Repo, name: str, **fields: Any) -> Path:
    """A certificate written by hand, bypassing ``fidelity.attest``'s refusals: ``fidelity/v2``,
    pinned to the root's statement as it stands (F11-T9) unless a field says otherwise. A field
    given as ``None`` is left out of the file."""
    doc: dict[str, Any] = {
        "schema": fidelity.SCHEMA,
        "subject": fidelity.ROOT_SUBJECT,
        "statement_hash": fidelity.current_hash(repo.target, fidelity.ROOT_SUBJECT),
        "grade": "screened-and-signed",
        "subject_author": SUBJECT_AUTHOR,
        "attestor": ATTESTOR,
        "date": "2026-09-12",
        "evidence": "read it",
        **fields,
    }
    doc = {key: value for key, value in doc.items() if value is not None}
    path = repo.target / "fidelity" / name
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return path


CURATORS = modes.Curators(identities=((CURATOR, CURATOR),))


# --- 1. intake post (F11-R5, D-10) ----------------------------------------------------------------


def test_a_posting_pull_request_is_not_refused_as_a_path() -> None:
    """F11-R5, F11-R1: the D-10 posting is a field of target.yaml (``posting {venue, url, date} or
    null``) and recording it is "a curator PR", so a modified target record by a listed curator
    is a classifiable change: curator mode, reviewed by the other curators (none here)."""
    c = modes.classify([Change("M", RECORD)], author=CURATOR, curators=CURATORS)
    assert "path-forbidden" not in [d.code for d in c.problems], c.as_dict()
    assert c.ok and c.mode == "curator" and c.target_id == TARGET_ID, c.as_dict()


def test_a_curator_posts_a_listed_target_by_pull_request(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-R5: ``opn-gate intake post`` records the D-10 posting as a curator PR, and the gate
    classifies the commit it writes and passes its checks, building nothing."""
    post(repo)
    repo.commit(f"intake: {TARGET_ID} posted")
    code, out = classify(repo, capsys)
    assert codes(out) == [], out
    assert code == 0 and out["ok"] is True and out["target"] == TARGET_ID, out
    assert out["mode"] == "curator" and out["needs_gate"] is False, out


def test_a_non_curator_may_not_post(repo: Repo, capsys: pytest.CaptureFixture[str]) -> None:
    """F11-R5, F08-R8: posting is a curator's act; an unlisted author's identical commit is
    refused as ``curator-unlisted``, naming R5."""
    post(repo)
    repo.commit("posted by a stranger")
    code, out = classify(repo, capsys, author="stranger")
    assert code != 0 and out["ok"] is False and out["mode"] is None, out
    assert codes(out) == ["curator-unlisted"] and "F11-R5" in messages(out), out


def test_a_post_may_change_no_other_field_of_the_target_record(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-R5 names one act on the record, the posting; D-6's artifacts, the curator and the
    provenance are not re-opened by it (F11-Q10: a hand-edited record is how a record comes to
    disagree with itself). A commit that posts and also edits the title is refused, naming the
    field."""
    post(repo)
    doc = intake.load_doc(repo.target)
    assert doc is not None
    doc["title"] = "Euclid's theorem, retitled"
    intake.write_doc(repo.target, doc)
    repo.commit("posted, and retitled")
    code, out = classify(repo, capsys)
    assert code != 0 and out["ok"] is False, out
    assert codes(out) == ["posting-fields"] and "title" in messages(out), out


def test_a_posting_is_recorded_once(repo: Repo, capsys: pytest.CaptureFixture[str]) -> None:
    """``intake.post`` (R5, D-10): "a posting is recorded once" — a second commit that rewrites
    an existing posting, or removes it, is refused at the gate as it is at the command."""
    post(repo)
    repo.commit("posted")
    doc = intake.load_doc(repo.target)
    assert doc is not None
    doc["posting"] = {**doc["posting"], "url": "https://example.org/elsewhere"}
    intake.write_doc(repo.target, doc)
    repo.commit("posting rewritten")
    code, out = classify(repo, capsys)
    assert code != 0 and out["ok"] is False, out
    assert codes(out) == ["posting-recorded"], out

    doc["posting"] = None
    intake.write_doc(repo.target, doc)
    repo.commit("posting removed")
    code, out = classify(repo, capsys)
    assert code != 0 and out["ok"] is False, out
    assert codes(out) == ["posting-recorded"], out


def test_a_target_record_is_never_deleted(repo: Repo, capsys: pytest.CaptureFixture[str]) -> None:
    """F11-R4, Q11: the record is what makes a target curated; deleting it would silently put the
    target back under F03's pre-F11 rule. Refused."""
    (repo.target / "target.yaml").unlink()
    repo.commit("record deleted")
    code, out = classify(repo, capsys)
    assert code != 0 and out["ok"] is False and codes(out) == ["path-forbidden"], out


def test_a_post_carries_no_proof(repo: Repo, capsys: pytest.CaptureFixture[str]) -> None:
    """F11-R5 / F08-R8: a curator PR adds records; a proof on the root rides in no curator PR."""
    post(repo)
    (repo.target / "nodes" / ROOT / "Proof.lean").write_text("-- a proof\n", encoding="utf-8")
    repo.commit("posted, with a proof")
    code, out = classify(repo, capsys)
    assert code != 0 and out["ok"] is False, out
    assert codes(out) == ["mode-mixed"] and "F11-R3, R5" in messages(out), out


def test_a_modification_that_records_no_posting_is_refused(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-R5: the record is modified only to take its posting. A byte change that leaves the
    posting null (here, a comment) is not a posting and is refused as ``posting-absent``."""
    record = repo.target / "target.yaml"
    record.write_text(record.read_text(encoding="utf-8") + "# a note\n", encoding="utf-8")
    repo.commit("touched the record")
    code, out = classify(repo, capsys)
    assert code != 0 and codes(out) == ["posting-absent"], out


def test_a_posting_that_breaks_the_schema_is_refused(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-R1: the posting is ``{venue, url, date}``; a hand-written one missing its url does not
    validate against ``target/v1`` and is refused as ``record-invalid``."""
    doc = yaml.safe_load((repo.target / "target.yaml").read_text(encoding="utf-8"))
    doc["posting"] = {"venue": "erdosproblems.com", "date": "2026-09-12"}
    (repo.target / "target.yaml").write_text(yaml.safe_dump(doc, sort_keys=False), "utf-8")
    repo.commit("posted by hand, badly")
    code, out = classify(repo, capsys)
    assert code != 0 and set(codes(out)) == {"record-invalid"}, out


def test_a_posting_needs_the_base_to_be_checked() -> None:
    """C7: whether the posting was null before is a fact about the base commit; a check that was
    not given the base refuses rather than guessing (``posting-unverified``)."""
    c = modes.classify([Change("M", RECORD)], author=CURATOR, curators=CURATORS)
    problems = modes.check(Path("/nonexistent"), c, base=None)
    assert [d.code for d in problems] == ["posting-unverified"]


# --- 2. fidelity certificates (F11-R3, D-9, D-4 step 9) ------------------------------------------


def test_a_lone_certificate_is_not_an_incomplete_intake() -> None:
    """F11-R3: certificates are append-only records beside an existing target; D-9: the non-author
    sign-off is "the only event that changes accepted state". A certificate added after intake is
    therefore not an intake: it is the ``fidelity`` mode, which builds nothing and asks no
    second reviewer, because the signature is the review."""
    c = modes.classify(
        [Change("A", f"targets/{TARGET_ID}/fidelity/root-2.yaml")],
        author=CURATOR,
        curators=CURATORS,
    )
    assert "intake-incomplete" not in [d.code for d in c.problems], c.as_dict()
    assert c.ok and c.mode == "fidelity", c.as_dict()
    assert (c.needs_gate, c.needs_admission, c.needs_review) == (False, False, False)


def test_a_non_author_certificate_enters_by_pull_request(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-R3, D-9, D-4 step 9: the commit ``opn-gate fidelity <target> root screened-and-signed
    --by <non-author>`` leaves — one new ``fidelity/root-2.yaml`` — opened by that non-author,
    classifies and passes, and builds nothing."""
    path = sign(repo)
    assert path.name == "root-2.yaml"  # intake wrote root-1, mechanical-only
    repo.commit(f"fidelity: {TARGET_ID} root screened-and-signed")
    code, out = classify(repo, capsys, author=ATTESTOR)
    assert codes(out) == [], out
    assert code == 0 and out["ok"] is True and out["target"] == TARGET_ID, out
    assert out["mode"] == "fidelity" and out["needs_gate"] is False, out
    assert out["needs_review"] is False, out


def test_a_certificate_may_not_rewrite_an_earlier_one(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-R3: certificates are append-only — raising the intake certificate in place is refused
    naming the path."""
    first = repo.target / "fidelity" / "root-1.yaml"
    doc = yaml.safe_load(first.read_text(encoding="utf-8"))
    doc.update(grade="screened-and-signed", attestor=ATTESTOR)
    first.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    repo.commit("certificate rewritten")
    code, out = classify(repo, capsys, author=ATTESTOR)
    assert code != 0 and codes(out) == ["path-forbidden"], out


def test_a_certificate_may_not_be_deleted(repo: Repo, capsys: pytest.CaptureFixture[str]) -> None:
    """F11-R3: a downgrade shows its history rather than erasing it; deleting the intake
    certificate is refused naming the path."""
    (repo.target / "fidelity" / "root-1.yaml").unlink()
    repo.commit("certificate deleted")
    code, out = classify(repo, capsys, author=ATTESTOR)
    assert code != 0 and codes(out) == ["path-forbidden"], out


def test_an_authors_own_signature_is_refused_at_the_gate(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-R3, D-9: from screened-and-signed up the attestor is not the subject's author. A
    certificate written by hand (bypassing the command's refusal) and opened by that author is
    refused by the gate as ``certificate-self-signed`` — a content check on the certificate, with
    the attestor otherwise in order (it is the pull request's author)."""
    certificate(repo, "root-2.yaml", attestor=SUBJECT_AUTHOR, evidence="I wrote it; it is right")
    repo.commit("self-signed")
    code, out = classify(repo, capsys, author=SUBJECT_AUTHOR)
    assert code != 0 and out["ok"] is False, out
    assert codes(out) == ["certificate-self-signed"] and "D-9" in messages(out), out


def test_a_certificate_pull_request_carries_no_proof(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-R3 / D-3: a certificate is a record about the statement; a proof of the root never
    rides with it."""
    sign(repo)
    (repo.target / "nodes" / ROOT / "Proof.lean").write_text("-- a proof\n", encoding="utf-8")
    repo.commit("signed, with a proof")
    code, out = classify(repo, capsys, author=ATTESTOR)
    assert code != 0 and out["ok"] is False, out
    assert codes(out) == ["mode-mixed"] and "F11-R3, R5" in messages(out), out


def test_a_certificate_opened_by_someone_other_than_its_attestor_is_refused(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-R3, D-9 (owner's rule, 2026-09-13): a certificate is the signer's own pull request, so
    the login that opened it is the certificate's ``attestor``. Neither a stranger nor a listed
    curator may file a signature in someone else's name."""
    sign(repo)
    repo.commit("signed in reviewer's name")
    for author in ("stranger", CURATOR):
        code, out = classify(repo, capsys, author=author)
        assert code != 0 and out["ok"] is False, (author, out)
        assert codes(out) == ["certificate-attestor"], (author, out)
        assert ATTESTOR in messages(out) and author in messages(out), (author, out)


def test_a_certificate_with_no_qa_pass_is_refused(
    unscreened: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F12-R9, D-9 v3.12: screened-and-signed is the mechanizable pass "completed with its
    exhibits recorded", then a signature. With no QA record for the root at head the certificate
    is refused as ``certificate-qa-incomplete``, naming the checks not passed."""
    sign(unscreened)
    unscreened.commit("signed an unscreened statement")
    code, out = classify(unscreened, capsys, author=ATTESTOR)
    assert code != 0 and codes(out) == ["certificate-qa-incomplete"], out
    assert "compile" in messages(out) and "F12-R9" in messages(out), out


def test_a_certificate_with_an_incomplete_qa_pass_is_refused(
    unscreened: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F12-R9: a pass missing one floor check (an inconclusive screen) is not complete, so the
    signature it would rest on is refused naming that check."""
    rows = [
        qa_row(check, "inconclusive" if check == "screen-false" else "pass")
        for check in qa.FLOOR_ROOT
    ]
    qa.write(unscreened.target, "root", rows, date=LATER, produced_by=QA_TOOL)
    unscreened.commit("an incomplete pass, on the base")
    sign(unscreened)
    unscreened.commit("signed")
    code, out = classify(unscreened, capsys, author=ATTESTOR)
    assert code != 0 and codes(out) == ["certificate-qa-incomplete"], out
    assert "screen-false" in messages(out), out


def test_a_qa_pass_in_the_same_pull_request_is_not_a_certificate(
    unscreened: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-R3, F12-Q12: the QA record is a curator's act and the certificate the signer's; one
    pull request carrying both is a mixture, not a way to screen and sign at once."""
    complete_qa_pass(unscreened.target)
    sign(unscreened)
    unscreened.commit("screened and signed together")
    code, out = classify(unscreened, capsys, author=ATTESTOR)
    assert code != 0 and codes(out) == ["mode-mixed"], out


def test_a_mechanical_only_certificate_needs_no_signature_rules(
    unscreened: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """D-9, F11-R3: ``mechanical-only`` is the machine's own grade and signs for nobody, so the
    non-author rule and the QA pass (both "from screened-and-signed up") do not apply: the
    subject's author may file one, on a statement with no QA record."""
    sign(unscreened, attestor=SUBJECT_AUTHOR, grade="mechanical-only")
    unscreened.commit("re-admitted, mechanically")
    code, out = classify(unscreened, capsys, author=SUBJECT_AUTHOR)
    assert code == 0 and codes(out) == [] and out["mode"] == "fidelity", out


def test_a_certificate_must_agree_with_the_subjects_author_on_record(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-R3, D-9: a subject has one author; the first certificate established it. A certificate
    naming another author grades a different thing, and naming a third party as author is also
    how a subject's own author would sign around the non-author rule."""
    certificate(repo, "root-2.yaml", subject_author="someone-else")
    repo.commit("signed, with another author")
    code, out = classify(repo, capsys, author=ATTESTOR)
    assert code != 0 and codes(out) == ["certificate-author"], out
    assert SUBJECT_AUTHOR in messages(out) and "someone-else" in messages(out), out


def test_a_certificate_for_an_uncurated_target_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-R3, R2: certificates stand beside an existing curated target; a pre-F11 target has no
    ``target.yaml``, and a new target's certificates ride in its intake. Refused as
    ``certificate-uncurated``."""
    r = Repo(copy_graph(tmp_path))
    r.git("init", "-q")
    r.commit("base")
    (r.root / "targets" / TARGET / "fidelity").mkdir()
    (r.root / "targets" / TARGET / "fidelity" / "root-1.yaml").write_text(
        yaml.safe_dump(
            fidelity.certificate_doc(
                subject="root",
                statement_hash="0" * 64,
                grade="screened-and-signed",
                subject_author=SUBJECT_AUTHOR,
                attestor=ATTESTOR,
                date="2026-09-12",
                evidence="read it",
            )
        ),
        encoding="utf-8",
    )
    r.commit("a certificate for a pre-F11 target")
    code, out = classify(r, capsys, author=ATTESTOR)
    assert code != 0 and codes(out) == ["certificate-uncurated"], out


def test_a_certificate_for_no_subject_of_the_target_is_refused(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """D-9, F11-R3: the subjects are the root and each definition. A certificate for anything
    else grades nothing the target is stated over, and a low one would drag the published
    minimum down; refused as ``certificate-subject``."""
    certificate(repo, "Nothing-1.yaml", subject="Nothing", grade="mechanical-only")
    repo.commit("a certificate for nothing")
    code, out = classify(repo, capsys, author=ATTESTOR)
    assert code != 0 and codes(out) == ["certificate-subject"], out


def test_a_certificate_is_named_for_its_subject(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-R3: ``fidelity/<subject>-<n>.yaml``. The classifier reads the subject from the file
    name; a file whose content grades another subject is refused as ``certificate-name``."""
    certificate(repo, "root-2.yaml", subject="Other", grade="mechanical-only")
    repo.commit("misnamed")
    code, out = classify(repo, capsys, author=ATTESTOR)
    assert code != 0 and codes(out) == ["certificate-name"], out


@pytest.mark.parametrize(
    "fields",
    [{"grade": "very-sure"}, {"schema": "fidelity/v9"}, {"statement_hash": None}],
    ids=["invented-grade", "unknown-version", "v2-without-hash"],
)
def test_a_certificate_that_breaks_the_schema_is_refused(
    repo: Repo, capsys: pytest.CaptureFixture[str], fields: dict[str, Any]
) -> None:
    """F11-R3: a certificate is load-bearing for claimability, so one that does not validate
    against the version it declares — or declares a version the reader does not accept (D-34)
    — is refused as ``certificate-invalid``."""
    certificate(repo, "root-2.yaml", **fields)
    repo.commit("a broken certificate")
    code, out = classify(repo, capsys, author=ATTESTOR)
    assert code != 0 and set(codes(out)) == {"certificate-invalid"}, out


def test_a_v1_certificate_is_not_added(repo: Repo, capsys: pytest.CaptureFixture[str]) -> None:
    """F11-T9, D-9: a ``fidelity/v1`` certificate pins no statement and counts for nothing, so a
    new one would merge as a signature nobody can count. It validates, and is refused as
    ``certificate-unpinned``."""
    certificate(repo, "root-2.yaml", schema="fidelity/v1", statement_hash=None)
    repo.commit("signed at v1")
    code, out = classify(repo, capsys, author=ATTESTOR)
    assert code != 0 and codes(out) == ["certificate-unpinned"], out
    assert fidelity.SCHEMA in messages(out) and "D-9" in messages(out), out


def test_a_certificate_for_another_statement_is_refused(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-T9, D-9, F12-R9: a certificate counts only for the statement whose hash it pins. One
    pinned to anything but the subject's hash at head would merge and count for nothing; refused
    as ``certificate-stale``, naming both hashes."""
    certificate(repo, "root-2.yaml", statement_hash="0" * 64)
    repo.commit("signed against another statement")
    code, out = classify(repo, capsys, author=ATTESTOR)
    assert code != 0 and codes(out) == ["certificate-stale"], out
    current = fidelity.current_hash(repo.target, fidelity.ROOT_SUBJECT)
    assert current is not None and current in messages(out) and "0" * 64 in messages(out), out


def test_a_certificate_pull_request_signs_one_subject() -> None:
    """F11-R3 (owner's rule): one subject per certificate pull request, so each signature is read
    and merged against its own statement's QA pass; two subjects are ``certificate-subjects``."""
    c = modes.classify(
        [
            Change("A", f"targets/{TARGET_ID}/fidelity/root-2.yaml"),
            Change("A", f"targets/{TARGET_ID}/fidelity/IsPrime-2.yaml"),
        ],
        author=ATTESTOR,
    )
    assert c.mode is None and [d.code for d in c.problems] == ["certificate-subjects"], c.as_dict()


def test_a_certificate_pull_request_touches_nothing_else(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-R3, R5: a certificate carries no status record (or any other path) beside it."""
    sign(repo)
    declare(repo, "dormant", date="2026-09-13T00:00:00Z")
    repo.commit("signed, and declared dormant")
    code, out = classify(repo, capsys, author=ATTESTOR)
    assert code != 0 and codes(out) == ["mode-mixed"], out


# --- 3. the three acts together (F11-R4, R5) ------------------------------------------------------


def test_post_sign_and_activate_as_three_pull_requests_make_the_target_claimable(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-R4, R5, D-6: posting (by the curator), the non-author signature (by its signer) and
    activation (by the curator), each its own pull request in that order, are each classified and
    passed, and the target they leave is claimable."""
    results: dict[str, tuple[int, list[str]]] = {}
    post(repo)
    repo.commit("post")
    code, out = classify(repo, capsys)
    results["post"] = (code, codes(out))
    sign(repo)
    repo.commit("sign")
    code, out = classify(repo, capsys, author=ATTESTOR)
    results["sign"] = (code, codes(out))
    activate(repo)
    repo.commit("activate")
    code, out = classify(repo, capsys)
    results["activate"] = (code, codes(out))

    assert results == {"post": (0, []), "sign": (0, []), "activate": (0, [])}, results
    status = records.load_target_status(repo.target)
    assert status is not None
    claimable, reasons = intake.claimability(
        intake.load_doc(repo.target),
        status=str(status.doc["status"]),
        grade=fidelity.target_grade(repo.target),
    )
    assert claimable and reasons == (), reasons


def test_activation_alone_is_a_curator_pull_request(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-R5, F08-R8 (control): with the signature and the posting already on the base, the
    activation record ``intake activate`` writes is a curator PR and passes."""
    sign(repo)
    post(repo)
    repo.commit("signed and posted, on the base")
    activate(repo)
    repo.commit("activate")
    code, out = classify(repo, capsys)
    assert code == 0 and out["mode"] == "curator" and codes(out) == [], out


def test_post_sign_and_activate_bundled_are_refused(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-R5: post and activate are "each a curator PR", so one pull request carrying the
    posting, the signature and the activation is refused as a mixture naming R5 — each act
    classifies alone, and the owner kept the refusal (2026-09-13)."""
    sign(repo)
    post(repo)
    activate(repo)
    repo.commit("all three at once")
    code, out = classify(repo, capsys)
    assert code != 0 and out["ok"] is False, out
    assert codes(out) == ["mode-mixed"] and "F11-R3, R5" in messages(out), out


# --- 4. activation re-checked at merge (F11-R4, R5; D-33) -----------------------------------------


def test_an_active_declaration_on_an_unclaimable_curated_target_is_refused(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-R5: activation "shall refuse while claimable would remain false, naming the missing
    condition". A hand-written ``active`` record on a listed, unsigned, unposted target — what a
    record written outside ``intake activate`` could say — is refused at the gate as
    ``activation-refused``, naming the grade (D-9) and the posting (D-10)."""
    declare(repo, "active", date="2026-09-13T00:00:00Z")
    repo.commit("declared active by hand")
    code, out = classify(repo, capsys)
    assert code != 0 and out["ok"] is False, out
    assert codes(out) == ["activation-refused"], out
    assert "D-9" in messages(out) and "D-10" in messages(out), out


def test_an_active_declaration_names_only_the_condition_still_missing(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-R5: with the signature on the base and no posting, the refusal names the posting
    alone."""
    sign(repo)
    repo.commit("signed, on the base")
    declare(repo, "active", date="2026-09-13T00:00:00Z")
    repo.commit("declared active before posting")
    _code, out = classify(repo, capsys)
    assert codes(out) == ["activation-refused"], out
    assert "D-10" in messages(out) and "D-9" not in messages(out), out


def test_an_active_target_is_not_declared_active_again(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-T10's one activation rule, held at merge: a target is activated from listed or dormant
    only (D-33), so a second ``active`` record on a claimable active target is refused. The rule
    reads the status *before* this pull request — the head's latest is the record itself."""
    sign(repo)
    post(repo)
    activate(repo)
    repo.commit("signed, posted and activated, on the base")
    declare(repo, "active", date="2026-09-14T00:00:00Z")
    repo.commit("declared active again")
    code, out = classify(repo, capsys)
    assert code != 0 and codes(out) == ["activation-refused"], out
    assert "'active'" in messages(out) and "D-33" in messages(out), out


def test_a_dormant_claimable_target_may_be_declared_active_again(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """D-33: dormancy is reversible and "every node stays claimable"; on a curated target that was
    activated through R5 and then declared dormant, a curator's ``active`` record passes."""
    sign(repo)
    post(repo)
    activate(repo)
    declare(repo, "dormant", date="2026-09-13T01:00:00Z")
    repo.commit("signed, posted, activated, gone quiet")
    declare(repo, "active", date="2026-09-13T02:00:00Z")
    repo.commit("back to active")
    code, out = classify(repo, capsys)
    assert code == 0 and out["mode"] == "curator" and codes(out) == [], out


def test_a_dormant_declaration_is_not_held_to_claimability(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """The merge-time check is activation's (F11-R5); a ``dormant`` record on an unclaimable
    curated target is not an activation, so the curator PR passes. (Asserted as a clean pass, not
    as the absence of one code: an absence assertion kept passing after the code was renamed, and
    the ``activation_any_status`` mutant survived it.)"""
    declare(repo, "dormant", date="2026-09-13T00:00:00Z")
    repo.commit("declared dormant")
    code, out = classify(repo, capsys)
    assert code == 0 and out["mode"] == "curator" and codes(out) == [], out


def test_a_pre_f11_targets_active_declaration_is_unchanged(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """F08-R11, F11-Q4/Q5: a target with no ``target.yaml`` keeps F03's rule, so a curator's
    ``active`` record on it classifies and passes as before — claimability is not derived there."""
    r = Repo(copy_graph(tmp_path))
    (r.root / "curators.json").write_text(
        json.dumps({"identities": [{"pseudonym": CURATOR, "github_login": CURATOR}]})
    )
    r.git("init", "-q")
    r.commit("base")
    assert intake.load_doc(r.root / "targets" / TARGET) is None
    declare(r, "active", date="2026-09-13T00:00:00Z", target_id=TARGET)
    r.commit("declared active")
    code, out = classify(r, capsys)
    assert code == 0 and out["mode"] == "curator" and codes(out) == [], out
