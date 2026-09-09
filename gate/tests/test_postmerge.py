"""F00-T8: the post-merge job's pure parts (R14, Q4, Q8)."""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from harness import copy_graph, make_context

from opn_gate import attestation, pipeline, postmerge, products, schemas
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


def test_bot_commit_message_round_trips() -> None:
    """F03-R12: `gate: <pr> <verdict>`."""
    assert postmerge.bot_commit_message(2, "pass") == "gate: #2 pass"
    assert postmerge.bot_commit_message(120, "fail") == "gate: #120 fail"
    assert postmerge.parse_bot_commit_message("gate: #2 pass\n\nbody") == (2, "pass")
    assert postmerge.parse_bot_commit_message("attestation: PR #2 (tutorial-and-swap)") is None
    with pytest.raises(ValueError, match="pass or fail"):
        postmerge.bot_commit_message(2, "bounced")
    assert postmerge.pr_number_from_message("gate: #2 pass") is None  # not a merge commit


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


# --- F05-T3: the claims snapshot (R10; AC16) ----------------------------------------------------


def claims_doc(node: str = "and-reassoc", pseudonym: str = "alice-p") -> dict[str, Any]:
    return {
        "schema": "claims/v1",
        "snapshot_at": "2026-09-09T12:00:00Z",
        "nodes": {
            node: {
                "active": [{"pseudonym": pseudonym, "expires": "2026-09-09T18:00:00Z"}],
                "history_count": 3,
            }
        },
    }


def test_claims_snapshot_refreshes(tmp_path: Path) -> None:
    """R10: a reachable service replaces claims.json, canonically."""
    graph = tmp_path / "graph"
    graph.mkdir()
    body = json.dumps(claims_doc()).encode()
    note = postmerge.refresh_claims(
        graph, "https://api.example/claims.json", opener=lambda _u, _t: body
    )
    assert note is None
    written = json.loads((graph / "claims.json").read_text())
    assert written == claims_doc()
    assert (graph / "claims.json").read_bytes() == schemas.canonical_json(claims_doc())


def test_claims_snapshot_fallback(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """AC16: the service unreachable — the previous claims.json stands and the log names it,
    and products still generate, carrying the previous claims."""
    graph = tmp_path / "graph"
    graph.mkdir()
    previous = schemas.canonical_json(claims_doc(pseudonym="earlier-p"))
    (graph / "claims.json").write_bytes(previous)

    def down(_url: str, _timeout: int) -> bytes:
        msg = "connection refused"
        raise OSError(msg)

    with caplog.at_level(logging.WARNING):
        note = postmerge.refresh_claims(graph, "https://api.example/claims.json", opener=down)
    assert note is not None and "connection refused" in note
    assert "keeping the committed claims.json" in caplog.text
    assert (graph / "claims.json").read_bytes() == previous

    # A defective response is the same story: never a half-written snapshot (C7).
    bad = postmerge.refresh_claims(
        graph, "https://api.example/claims.json", opener=lambda _u, _t: b"{}"
    )
    assert bad is not None
    assert (graph / "claims.json").read_bytes() == previous

    # And the generator merges what stands into the frontier it renders.
    root = copy_graph(tmp_path / "gen")
    (root / "claims.json").write_bytes(previous)
    prod = products.generate(root, rendered_from="5" * 40, commit_time="2026-09-09T00:00:00Z")
    frontier = json.loads(prod.files[Path("frontier.json")])
    entry = next(e for e in frontier["entries"] if e["node_id"] == "and-reassoc")
    assert entry["claims"]["active"] == [
        {"pseudonym": "earlier-p", "expires": "2026-09-09T18:00:00Z"}
    ]
    assert entry["claims"]["history_count"] == 3
    others = [e for e in frontier["entries"] if e["node_id"] != "and-reassoc"]
    assert all(e["claims"] == {"active": [], "history_count": 0} for e in others)


def test_claims_snapshot_refuses_plain_http(tmp_path: Path) -> None:
    note = postmerge.refresh_claims(tmp_path, "http://api.example/claims.json")
    assert note is not None and "https" in note
    assert postmerge.refresh_claims(tmp_path, None) == "no claims endpoint configured"
    assert not (tmp_path / "claims.json").exists()


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
