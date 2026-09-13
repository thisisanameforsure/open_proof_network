"""Finding A: on a curated target, the acts that make it claimable cannot pass the classifier.

F11-R5 says ``intake post`` and ``intake activate`` are "each a curator PR"; F11-R3 keeps fidelity
certificates append-only under ``targets/<id>/fidelity/``; F11-R4 makes a target claimable only
with status active, grade >= screened-and-signed and a non-null posting; D-6 says "claims are
blocked until its fidelity grade reaches screened-and-signed (D-9) and the D-10 posting is made".
So each of the three acts has to reach the graph through a pull request the gate classifies.

As built, two of them cannot:

- ``intake post`` rewrites ``target.yaml`` (``posting: null`` -> a posting), and ``target-record``
  is not in ``paths.MODIFIABLE_ROLES``, so ``_locate_change`` refuses it before any mode is asked:
  ``path-forbidden: targets/<id>/target.yaml: a target-record may not be modified``.
- a certificate is ``paths.INTAKE_ROLES``, so a lone certificate is routed to
  ``_classify_intake`` and refused as ``intake-incomplete`` (F11-R2), although the target exists.

The tests below that assert the acts classify fail today for exactly those two reasons. The
others pin refusals that must survive the fix. Each act is written by the function the command
calls (``intake.post``, ``fidelity.attest``, ``intake.activate``) on a git checkout of a freshly
taken-in target, and ``opn-gate classify`` runs over the commit, the way the graph's workflow does.

``fidelity.attest`` is called without F12-R9's grade gate (the library default, F12-Q15): the
QA pass is the command's refusal, run where the attestor runs it, and the classifier sees only
the file the command leaves. Who may *open* a certificate pull request (a listed curator, or the
attestor) is an open decision; these tests use a listed curator as the author, the one reading
that needs no new role.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import copy_graph, take_in

from opn_gate import cli, fidelity, intake, modes, records
from opn_gate.paths import Change

TARGET_ID = "euclid-primes"
ROOT = "and-reassoc"  # take_in reuses this fixture node as the new target's root
CURATOR = "curator"  # take_in's intake author, listed in curators.json below
SUBJECT_AUTHOR = "author"  # samples.target_record's provenance.author: the root's author
ATTESTOR = "reviewer"  # a non-author (D-9)
LATER = "2026-09-12T00:00:00Z"
RECORD = f"targets/{TARGET_ID}/target.yaml"


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


@pytest.fixture
def repo(tmp_path: Path) -> Repo:
    root = copy_graph(tmp_path)
    take_in(root, TARGET_ID)
    # take_in reuses a fixture node as the root; a real root enters unproved (D-6, F11-R2).
    (root / "targets" / TARGET_ID / "nodes" / ROOT / "Proof.lean").unlink()
    (root / "curators.json").write_text(
        json.dumps({"identities": [{"pseudonym": CURATOR, "github_login": CURATOR}]})
    )
    r = Repo(root)
    r.git("init", "-q")
    r.commit(f"intake: list {TARGET_ID}")
    return r


def classify(
    repo: Repo, capsys: pytest.CaptureFixture[str], *, author: str = CURATOR
) -> tuple[int, dict[str, Any]]:
    """``opn-gate classify`` over the checkout's last commit, as the graph's workflow runs it."""
    capsys.readouterr()
    code = cli.main(["classify", "--graph", str(repo.root), "--base", "HEAD~1", "--author", author])
    return code, json.loads(capsys.readouterr().out)


def codes(out: dict[str, Any]) -> list[str]:
    return [p["code"] for p in out["problems"]]


def post(repo: Repo) -> None:
    intake.post(
        repo.root,
        TARGET_ID,
        venue="erdosproblems.com",
        url="https://example.org/posting",
        date=LATER,
    )


def sign(repo: Repo, *, attestor: str = ATTESTOR) -> Path:
    return fidelity.attest(
        repo.target,
        fidelity.ROOT_SUBJECT,
        "screened-and-signed",
        attestor=attestor,
        date="2026-09-12",
        evidence="read the Lean statement against the informal one; they agree",
    )


def activate(repo: Repo) -> None:
    intake.activate(repo.root, TARGET_ID, author=CURATOR, date="2026-09-13T00:00:00Z")


CURATORS = modes.Curators(identities=((CURATOR, CURATOR),))


# --- 1. intake post (F11-R5, D-10) ----------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="finding A (F11-R3, R5): a posting and a lone fidelity certificate cannot pass classify (path-forbidden / intake-incomplete); fix: posting is a curator PR, a certificate the signer's own PR (Mike, 2026-09-13)",  # noqa: E501 — the xfail reason names the finding and its fix
)
def test_a_posting_pull_request_is_not_refused_as_a_path() -> None:
    """F11-R5, F11-R1: the D-10 posting is a field of target.yaml (``posting {venue, url, date} or
    null``) and recording it is "a curator PR", so a modified target record by a listed curator
    is a classifiable change. Fails today: ``path-forbidden: ... a target-record may not be
    modified``."""
    c = modes.classify([Change("M", RECORD)], author=CURATOR, curators=CURATORS)
    assert "path-forbidden" not in [d.code for d in c.problems], c.as_dict()
    assert c.ok and c.mode is not None and c.target_id == TARGET_ID, c.as_dict()


@pytest.mark.xfail(
    strict=True,
    reason="finding A (F11-R3, R5): a posting and a lone fidelity certificate cannot pass classify (path-forbidden / intake-incomplete); fix: posting is a curator PR, a certificate the signer's own PR (Mike, 2026-09-13)",  # noqa: E501 — the xfail reason names the finding and its fix
)
def test_a_curator_posts_a_listed_target_by_pull_request(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-R5: ``opn-gate intake post`` records the D-10 posting as a curator PR, and the gate
    classifies the commit it writes and passes its checks, building nothing. Fails today with
    ``path-forbidden`` on target.yaml."""
    post(repo)
    repo.commit(f"intake: {TARGET_ID} posted")
    code, out = classify(repo, capsys)
    assert codes(out) == [], out
    assert code == 0 and out["ok"] is True and out["target"] == TARGET_ID, out
    assert out["needs_gate"] is False, out


def test_a_non_curator_may_not_post(repo: Repo, capsys: pytest.CaptureFixture[str]) -> None:
    """F11-R5, F08-R8: posting is a curator's act; an unlisted author's identical commit is
    refused. (Refused today by ``path-forbidden``; after the fix the reason should be
    ``curator-unlisted``.)"""
    post(repo)
    repo.commit("posted by a stranger")
    code, out = classify(repo, capsys, author="stranger")
    assert code != 0 and out["ok"] is False and out["mode"] is None, out


def test_a_post_may_change_no_other_field_of_the_target_record(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-R5 names one act on the record, the posting; D-6's artifacts, the curator and the
    provenance are not re-opened by it (F11-Q10: a hand-edited record is how a record comes to
    disagree with itself). A commit that posts and also edits the title is refused."""
    post(repo)
    doc = intake.load_doc(repo.target)
    assert doc is not None
    doc["title"] = "Euclid's theorem, retitled"
    intake.write_doc(repo.target, doc)
    repo.commit("posted, and retitled")
    code, out = classify(repo, capsys)
    assert code != 0 and out["ok"] is False, out


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

    doc["posting"] = None
    intake.write_doc(repo.target, doc)
    repo.commit("posting removed")
    code, out = classify(repo, capsys)
    assert code != 0 and out["ok"] is False, out


def test_a_target_record_is_never_deleted(repo: Repo, capsys: pytest.CaptureFixture[str]) -> None:
    """F11-R4, Q11: the record is what makes a target curated; deleting it would silently put the
    target back under F03's pre-F11 rule. Refused."""
    (repo.target / "target.yaml").unlink()
    repo.commit("record deleted")
    code, out = classify(repo, capsys)
    assert code != 0 and out["ok"] is False and "path-forbidden" in codes(out), out


def test_a_post_carries_no_proof(repo: Repo, capsys: pytest.CaptureFixture[str]) -> None:
    """F11-R5 / F08-R8: a curator PR adds records; a proof on the root rides in no curator PR."""
    post(repo)
    (repo.target / "nodes" / ROOT / "Proof.lean").write_text("-- a proof\n", encoding="utf-8")
    repo.commit("posted, with a proof")
    code, out = classify(repo, capsys)
    assert code != 0 and out["ok"] is False, out


# --- 2. fidelity certificates (F11-R3, D-9, D-4 step 9) ------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="finding A (F11-R3, R5): a posting and a lone fidelity certificate cannot pass classify (path-forbidden / intake-incomplete); fix: posting is a curator PR, a certificate the signer's own PR (Mike, 2026-09-13)",  # noqa: E501 — the xfail reason names the finding and its fix
)
def test_a_lone_certificate_is_not_an_incomplete_intake() -> None:
    """F11-R3: certificates are append-only records beside an existing target; D-9: the non-author
    sign-off is "the only event that changes accepted state". A certificate added after intake is
    therefore not an intake. Fails today: ``intake-incomplete: an intake adds
    targets/<id>/target.yaml; this one does not (F11-R2)``."""
    c = modes.classify(
        [Change("A", f"targets/{TARGET_ID}/fidelity/root-2.yaml")],
        author=CURATOR,
        curators=CURATORS,
    )
    assert "intake-incomplete" not in [d.code for d in c.problems], c.as_dict()
    assert c.ok and c.mode is not None, c.as_dict()


@pytest.mark.xfail(
    strict=True,
    reason="finding A (F11-R3, R5): a posting and a lone fidelity certificate cannot pass classify (path-forbidden / intake-incomplete); fix: posting is a curator PR, a certificate the signer's own PR (Mike, 2026-09-13)",  # noqa: E501 — the xfail reason names the finding and its fix
)
def test_a_non_author_certificate_enters_by_pull_request(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-R3, D-9, D-4 step 9: the commit ``opn-gate fidelity <target> root screened-and-signed
    --by <non-author>`` leaves — one new ``fidelity/root-2.yaml`` — classifies and passes, and
    builds nothing. Fails today with ``intake-incomplete``."""
    path = sign(repo)
    assert path.name == "root-2.yaml"  # intake wrote root-1, mechanical-only
    repo.commit(f"fidelity: {TARGET_ID} root screened-and-signed")
    code, out = classify(repo, capsys)
    assert codes(out) == [], out
    assert code == 0 and out["ok"] is True and out["target"] == TARGET_ID, out
    assert out["needs_gate"] is False, out


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
    code, out = classify(repo, capsys)
    assert code != 0 and "path-forbidden" in codes(out), out


def test_an_authors_own_signature_is_refused_at_the_gate(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-R3, D-9: from screened-and-signed up the attestor is not the subject's author. A
    certificate written by hand (bypassing the command's refusal) is refused by the gate. Refused
    today only because every lone certificate is; the fix must keep this refusal as a content
    check on the certificate, not lose it with the ``intake-incomplete`` routing."""
    cert = {
        "schema": fidelity.SCHEMA,
        "subject": fidelity.ROOT_SUBJECT,
        "grade": "screened-and-signed",
        "subject_author": SUBJECT_AUTHOR,
        "attestor": SUBJECT_AUTHOR,
        "date": "2026-09-12",
        "evidence": "I wrote it and I say it is right",
    }
    (repo.target / "fidelity" / "root-2.yaml").write_text(
        yaml.safe_dump(cert, sort_keys=False), encoding="utf-8"
    )
    repo.commit("self-signed")
    code, out = classify(repo, capsys)
    assert code != 0 and out["ok"] is False, out


def test_a_certificate_pull_request_carries_no_proof(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-R3 / D-3: a certificate is a record about the statement; a proof of the root never
    rides with it."""
    sign(repo)
    (repo.target / "nodes" / ROOT / "Proof.lean").write_text("-- a proof\n", encoding="utf-8")
    repo.commit("signed, with a proof")
    code, out = classify(repo, capsys)
    assert code != 0 and out["ok"] is False, out


# --- 3. the three acts together (F11-R4, R5) ------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="finding A (F11-R3, R5): a posting and a lone fidelity certificate cannot pass classify (path-forbidden / intake-incomplete); fix: posting is a curator PR, a certificate the signer's own PR (Mike, 2026-09-13)",  # noqa: E501 — the xfail reason names the finding and its fix
)
def test_post_sign_and_activate_as_three_pull_requests_make_the_target_claimable(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """F11-R4, R5, D-6: posting, the non-author signature and activation, each its own pull request
    in that order, are each classified and passed, and the target they leave is claimable. Fails
    today at the first two (``path-forbidden``, ``intake-incomplete``); only activation passes."""
    results: dict[str, tuple[int, list[str]]] = {}
    post(repo)
    repo.commit("post")
    code, out = classify(repo, capsys)
    results["post"] = (code, codes(out))
    sign(repo)
    repo.commit("sign")
    code, out = classify(repo, capsys)
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
    activation record ``intake activate`` writes is a curator PR and passes. Passes today."""
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
    posting, the signature and the activation is refused. Refused today (by ``path-forbidden``
    on target.yaml); whether the refusal stays once each act classifies alone is the owner's
    call — this test pins R5 as written."""
    sign(repo)
    post(repo)
    activate(repo)
    repo.commit("all three at once")
    code, out = classify(repo, capsys)
    assert code != 0 and out["ok"] is False, out
