"""F00-T8: the post-merge job's pure parts (R14, Q4, Q8)."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from harness import make_context

from opn_gate import attestation, pipeline, postmerge, schemas
from opn_gate.signer import SshKeygenSigner

FIXED = datetime(2026, 9, 8, 6, 0, 0, tzinfo=UTC)


@pytest.fixture(scope="module")
def gate_key(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str]:
    d = tmp_path_factory.mktemp("gate-key")
    key = d / "gate"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", "opn-gate"],
        check=True,
    )
    return key, (d / "gate.pub").read_text()


def test_attestation_id_is_zero_padded() -> None:
    assert postmerge.attestation_id(7) == "000007"
    assert postmerge.attestation_id(123456) == "123456"
    assert postmerge.attestation_path(Path("/g"), 12) == Path("/g/attestations/000012.json")
    with pytest.raises(ValueError, match="positive"):
        postmerge.attestation_id(0)


def test_pr_number_from_message() -> None:
    assert postmerge.pr_number_from_message("Merge pull request #12 from x/y\n\nbody") == 12
    assert postmerge.pr_number_from_message("Prove tutorial-and-swap (#34)") == 34
    assert postmerge.pr_number_from_message("plain commit") is None
    assert postmerge.pr_number_from_message("") is None


def test_approving_reviewer_excludes_author_and_takes_latest() -> None:
    reviews = [
        {"state": "APPROVED", "user": {"login": "author"}, "submitted_at": "2026-09-08T01:00:00Z"},
        {"state": "COMMENTED", "user": {"login": "r1"}, "submitted_at": "2026-09-08T02:00:00Z"},
        {"state": "APPROVED", "user": {"login": "r1"}, "submitted_at": "2026-09-08T03:00:00Z"},
        {"state": "APPROVED", "user": {"login": "r2"}, "submitted_at": "2026-09-08T04:00:00Z"},
    ]
    assert postmerge.approving_reviewer(reviews, "author") == "r2"
    assert postmerge.approving_reviewer(reviews[:2], "author") is None
    assert postmerge.approving_reviewer([], "author") is None


def test_finalize_signs_with_gate_key(gate_key: tuple[Path, str], tmp_path: Path) -> None:
    key, pub = gate_key
    ctx = make_context(tmp_path)
    doc = attestation.build(
        ctx, pipeline.run_steps(ctx), graph_commit="3" * 40, clock=lambda: FIXED
    )
    review = postmerge.review_block("pr-approval", reviewer="reviewer")
    signed = postmerge.finalize(
        doc, merge_commit="4" * 40, review=review, key_path=key, signer=SshKeygenSigner()
    )
    assert schemas.violations(signed) == []
    assert signed["runner"] == "hosted"
    assert signed["merge_commit"] == "4" * 40
    assert signed["review"] == {"kind": "pr-approval", "reviewer": "reviewer", "reference": None}
    assert signed["signature"]["kind"] == "gate"
    assert signed["signature"]["timestamp"] == "2026-09-08T06:00:00Z"
    assert postmerge.verify(signed, pub, SshKeygenSigner())
    # D-5: beyond the masked fields, signing changed only the step-9 record (Q11).
    assert attestation.compare(doc, signed) == ["review"]
    assert attestation.compare(attestation.with_step9(doc, signed), signed) == []

    tampered = dict(signed, review=postmerge.review_block("tutorial"))
    assert not postmerge.verify(tampered, pub, SshKeygenSigner())
    assert not postmerge.verify(doc, pub, SshKeygenSigner())  # unsigned


def test_verify_rejects_wrong_key(gate_key: tuple[Path, str], tmp_path: Path) -> None:
    key, _pub = gate_key
    other = tmp_path / "other"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(other)], check=True)
    ctx = make_context(tmp_path)
    doc = attestation.build(ctx, pipeline.run_steps(ctx), graph_commit=None, clock=lambda: FIXED)
    signed = postmerge.finalize(
        doc,
        merge_commit="4" * 40,
        review=postmerge.review_block("tutorial"),
        key_path=key,
        signer=SshKeygenSigner(),
    )
    assert not postmerge.verify(signed, (tmp_path / "other.pub").read_text(), SshKeygenSigner())


def test_waiver_requires_named_approval(gate_key: tuple[Path, str], tmp_path: Path) -> None:
    """F02-AC9: a waived proof merges only with `waiver: native_decide` in the approval."""
    key, pub = gate_key
    ctx = make_context(tmp_path)
    doc = attestation.build(
        ctx, pipeline.run_steps(ctx), graph_commit="3" * 40, clock=lambda: FIXED
    )
    assert doc["trust_base"] == "kernel"
    assert postmerge.check_waiver(doc, []) is None  # nothing to approve

    waived = dict(doc, trust_base="compiler")
    refusal = postmerge.check_waiver(waived, ["LGTM", "approved, nice proof"])
    assert refusal is not None and refusal.code == "waiver-unapproved"
    assert "waiver: native_decide" in refusal.message
    assert postmerge.check_waiver(waived, []) is not None

    body = "Reviewed the justification.\n\nwaiver: native_decide\n"
    assert postmerge.check_waiver(waived, ["LGTM", body]) is None
    assert not postmerge.approval_names_waiver("waiver: native_decide is not something I grant")
    signed = postmerge.finalize(
        waived,
        merge_commit="4" * 40,
        review=postmerge.review_block("pr-approval", reviewer="reviewer"),
        key_path=key,
        signer=SshKeygenSigner(),
    )
    assert signed["trust_base"] == "compiler" and schemas.violations(signed) == []
    assert postmerge.verify(signed, pub, SshKeygenSigner())


def test_review_block_rules() -> None:
    assert postmerge.review_block("tutorial") == {
        "kind": "tutorial",
        "reviewer": None,
        "reference": None,
    }
    assert postmerge.review_block("certificate", reference="cert-1")["reference"] == "cert-1"
    with pytest.raises(ValueError, match="approving reviewer"):
        postmerge.review_block("pr-approval")
    with pytest.raises(ValueError, match="needs a reference"):
        postmerge.review_block("provenance")
