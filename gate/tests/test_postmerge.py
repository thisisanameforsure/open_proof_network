"""F00-T8: the post-merge job's pure parts (R14, Q4, Q8)."""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import copy_graph, make_context

from opn_gate import attestation, pipeline, postmerge, products, schemas
from opn_gate import graph as graphmod
from opn_gate.signer import SshKeygenSigner
from opn_gate.steps import artifact as art

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


# --- F07-T4: what a merged partial and a merged alternate leave behind (R6, R7; AC7, AC8, AC9) ---

TARGET = "propositional"
PARENT = "and-swap-reassoc"
STAMP = "20260910T121314Z"
PSEUDONYM = "alice"

ASSEMBLY = """/-! A partial proof of the root (D-12 #5). -/

theorem OpnProp.and_swap_reassoc : ∀ p q r : Prop, (p ∧ q) ∧ r → r ∧ (q ∧ p) := by
  intro p q r h
  have right : r := sorry
  have left : q ∧ p := sorry
  exact ⟨right, left⟩
"""


def hole(name: str, closed: str, *, local: str | None = None) -> art.Hole:
    return art.Hole(name=name, type=local or closed, closed_type=closed, defeq_goal=False)


HOLES = (
    hole("right", "∀ (p q r : Prop), (p ∧ q) ∧ r → r", local="r"),
    hole("left", "∀ (p q r : Prop), (p ∧ q) ∧ r → r → q ∧ p", local="q ∧ p"),
)


def parent_dir(tmp_path: Path) -> Path:
    root = copy_graph(tmp_path)
    return root / "targets" / TARGET / "nodes" / PARENT


def test_partial_creates_children(tmp_path: Path) -> None:
    """AC7: two node dirs with origin compiler-derived, the parent's deps and Context updated,
    and the assembly filed under attempts/."""
    node_dir = parent_dir(tmp_path)
    before = yaml.safe_load((node_dir / "META.yaml").read_text())["deps"]

    result = postmerge.apply_partial(
        node_dir, HOLES, partial_text=ASSEMBLY, pseudonym=PSEUDONYM, stamp=STAMP
    )
    assert result.children == (f"{PARENT}--h1", f"{PARENT}--h2")
    assert result.origin == "compiler-derived"
    assert result.annex is None

    for child_id, h in zip(result.children, HOLES, strict=True):
        child = node_dir.parent / child_id
        meta = yaml.safe_load((child / "META.yaml").read_text())
        assert meta["origin"] == "compiler-derived"
        assert meta["id"] == child_id
        # The statement is the hole closed over its binders — a proposition on its own (D-29).
        statement = (child / "Statement.lean").read_text()
        assert h.closed_type in statement
        assert h.name in statement
        assert "sorry" in (child / "Witness.lean").read_text()  # R6: a slot, not a witness
        assert schemas.violations(meta) == []

    deps = yaml.safe_load((node_dir / "META.yaml").read_text())["deps"]
    assert deps == [*before, *result.children]
    context = (node_dir / "Context.lean").read_text()
    for child_id in result.children:
        signature = (node_dir.parent / child_id / "Statement.lean").read_text()
        decl = signature.split("theorem ")[1].split(" :")[0]
        assert decl in context
    assert (node_dir / result.attempt_path).is_file()
    assert (node_dir / result.attempt_path).read_text() == ASSEMBLY


def test_children_are_blocked_until_their_witness_is_filled(tmp_path: Path) -> None:
    """R6, F07-Q3: a child is created with a witness slot, so it is blocked with a cause until
    someone fills it — and F03 derives that from the tree, not from a record."""
    node_dir = parent_dir(tmp_path)
    result = postmerge.apply_partial(
        node_dir, HOLES, partial_text=ASSEMBLY, pseudonym=PSEUDONYM, stamp=STAMP
    )
    child = node_dir.parent / result.children[0]
    assert graphmod.witness_is_stub(child)
    facts = graphmod.NodeFacts(
        node_id=child.name,
        target_id=TARGET,
        path=child,
        statement_hash="a" * 64,
        deps=(),
        origin="compiler-derived",
        tutorial=False,
        relation=None,
        proof=None,
        override=None,
        witness_stub=True,
    )
    statuses = graphmod.derive_statuses({child.name: facts})
    assert statuses[child.name] == "blocked"
    causes = graphmod.derive_causes({child.name: facts}, statuses)
    assert causes[child.name] == graphmod.CAUSE_WITNESS_MISSING


def test_skeleton_annex_citation(tmp_path: Path) -> None:
    """AC8: a cited annex present on the node makes the children skeleton-hole; no citation
    leaves them compiler-derived; a citation pointing at nothing is a rejection."""
    node_dir = parent_dir(tmp_path)
    text = "-- annex: " + ("a" * 64) + "\n" + ASSEMBLY

    with pytest.raises(postmerge.GraphWriteError, match="not on this node"):
        postmerge.apply_partial(
            node_dir, HOLES, partial_text=text, pseudonym=PSEUDONYM, stamp=STAMP
        )
    assert not (node_dir.parent / f"{PARENT}--h1").exists()  # nothing half-written (C7)

    (node_dir / "annex").mkdir(exist_ok=True)
    (node_dir / "annex" / f"{'a' * 64}.md").write_text("the informal argument\n")
    result = postmerge.apply_partial(
        node_dir, HOLES, partial_text=text, pseudonym=PSEUDONYM, stamp=STAMP
    )
    assert result.origin == "skeleton-hole"
    assert result.annex == "a" * 64
    meta = yaml.safe_load((node_dir.parent / result.children[0] / "META.yaml").read_text())
    assert meta["origin"] == "skeleton-hole"
    assert meta["schema"] == "meta/v3"  # the only version that can carry the value (D-3 v3.12)
    assert schemas.violations(meta) == []
    # D-31 v3.12: the citation stays in the file, which is committed under attempts/.
    assert postmerge.annex_citation((node_dir / result.attempt_path).read_text()) == "a" * 64


def test_alternate_proof(tmp_path: Path) -> None:
    """AC9: a second proof of a proved node lands under attempts/ and Proof.lean is unchanged."""
    node_dir = parent_dir(tmp_path)
    original = (node_dir / "Proof.lean").read_text()
    alternate = original.replace("⟨", "⟨ ")  # a different route to the same theorem

    path = postmerge.record_alternate(node_dir, alternate, pseudonym="bob", stamp=STAMP)
    assert path == f"attempts/{STAMP}-bob-alternate.lean"
    assert (node_dir / path).read_text() == alternate
    assert (node_dir / "Proof.lean").read_text() == original

    with pytest.raises(postmerge.GraphWriteError, match="append-only"):
        postmerge.record_alternate(node_dir, alternate, pseudonym="bob", stamp=STAMP)


# --- the post-merge job's refusals: each named, none half-written (R6, R7; C7) -------------------

from opn_gate import scaffold  # noqa: E402
from opn_gate.signer import Signature  # noqa: E402


def snapshot(node_dir: Path) -> dict[str, bytes]:
    return {
        p.relative_to(node_dir.parent).as_posix(): p.read_bytes()
        for p in node_dir.parent.rglob("*")
        if p.is_file()
    }


def test_a_partial_with_no_holes_creates_nothing(tmp_path: Path) -> None:
    """D-12 #5: a hole-less partial is a proof, and the job refuses to make children of it."""
    node_dir = parent_dir(tmp_path)
    before = snapshot(node_dir)
    with pytest.raises(postmerge.GraphWriteError, match="no holes"):
        postmerge.apply_partial(
            node_dir, (), partial_text=ASSEMBLY, pseudonym=PSEUDONYM, stamp=STAMP
        )
    assert snapshot(node_dir) == before


def test_a_partial_applied_twice_is_refused_and_the_parent_is_untouched(tmp_path: Path) -> None:
    """The child ids are a function of the parent, so re-applying a merge lands on existing
    directories, which the scaffold never writes into (D-3); the parent stays as the first
    application left it."""
    node_dir = parent_dir(tmp_path)
    postmerge.apply_partial(
        node_dir, HOLES, partial_text=ASSEMBLY, pseudonym=PSEUDONYM, stamp=STAMP
    )
    after_first = snapshot(node_dir)
    with pytest.raises(scaffold.ScaffoldError, match="already exists"):
        postmerge.apply_partial(
            node_dir, HOLES, partial_text=ASSEMBLY, pseudonym="carol", stamp="20260911T000000Z"
        )
    assert snapshot(node_dir) == after_first


@pytest.mark.xfail(
    strict=True,
    reason="postmerge.apply_partial files the assembly last: when attempts/<ts>-<pseudonym>"
    "-partial.lean already exists (F07-Q15: the submitter may name the file anything under "
    "attempts/), the refusal comes after the children, the parent's deps and Context.lean were "
    "written, contradicting the docstring's 'a failure leaves nothing behind' (C7)",
)
def test_a_refusal_at_the_attempt_file_leaves_nothing_behind(tmp_path: Path) -> None:
    node_dir = parent_dir(tmp_path)
    submitted = node_dir / "attempts" / postmerge.attempt_name(STAMP, PSEUDONYM, "-partial.lean")
    submitted.write_text(ASSEMBLY, encoding="utf-8")
    before = snapshot(node_dir)
    with pytest.raises(postmerge.GraphWriteError, match="append-only"):
        postmerge.apply_partial(
            node_dir, HOLES, partial_text=ASSEMBLY, pseudonym=PSEUDONYM, stamp=STAMP
        )
    assert snapshot(node_dir) == before


@pytest.mark.xfail(
    strict=True,
    reason="postmerge.annex_citation matches only a 64-char lowercase hex hash, so a truncated "
    "or upper-cased `-- annex:` line is read as no citation at all: the children silently become "
    "compiler-derived instead of the citation being rejected as absent (F07-R6, D-31; C7)",
)
@pytest.mark.parametrize("digest", ["a" * 63, "A" * 64, "a" * 64 + "0"])
def test_a_malformed_annex_citation_is_rejected_not_ignored(tmp_path: Path, digest: str) -> None:
    node_dir = parent_dir(tmp_path)
    text = f"-- annex: {digest}\n" + ASSEMBLY
    with pytest.raises(postmerge.GraphWriteError):
        postmerge.apply_partial(
            node_dir, HOLES, partial_text=text, pseudonym=PSEUDONYM, stamp=STAMP
        )


def test_a_citation_needs_its_own_line(tmp_path: Path) -> None:
    """The citation is a comment line of the form `-- annex: <hash>` and nothing else: a hash
    mentioned in prose, or after other text, is not a citation."""
    assert postmerge.annex_citation(f"-- see annex {'a' * 64}\n") is None
    assert postmerge.annex_citation(f"-- annex: {'a' * 64} (my sketch)\n") is None
    assert postmerge.annex_citation(f"  -- annex:\t{'b' * 64}  \n") == "b" * 64
    assert postmerge.child_origin("theorem t : True := trivial\n") == "compiler-derived"


def test_regenerating_context_for_a_ghost_dep_is_refused(tmp_path: Path) -> None:
    """The bot-owned Context is generated from the deps' own files (F01-R6); a dep with no
    Statement.lean to copy is a refusal, and the old Context stands."""
    node_dir = parent_dir(tmp_path)
    before = (node_dir / "Context.lean").read_text()
    postmerge.add_deps(node_dir, ["ghost"])
    with pytest.raises(scaffold.ScaffoldError, match="'ghost' is not a node"):
        postmerge.regenerate_context(node_dir, node_dir.parent)
    assert (node_dir / "Context.lean").read_text() == before


def test_add_deps_is_additive_and_idempotent(tmp_path: Path) -> None:
    node_dir = parent_dir(tmp_path)
    before = yaml.safe_load((node_dir / "META.yaml").read_text())["deps"]
    assert postmerge.add_deps(node_dir, [before[0], "x"]) == [*before, "x"]
    assert postmerge.add_deps(node_dir, ["x"]) == [*before, "x"]


@pytest.mark.xfail(
    strict=True,
    reason="graph.witness_is_stub is `'sorry' in text`: a hole's witness filled by replacing the "
    "body but keeping the slot's own doc comment (which says `sorry`) still reads as a stub, so "
    "the node stays blocked with cause witness-missing after its witness is real (F07-R6, "
    "F08-R5, F07-Q3)",
)
def test_a_filled_witness_that_keeps_the_slot_comment_is_not_a_stub(tmp_path: Path) -> None:
    node_dir = parent_dir(tmp_path)
    result = postmerge.apply_partial(
        node_dir, HOLES, partial_text=ASSEMBLY, pseudonym=PSEUDONYM, stamp=STAMP
    )
    child = node_dir.parent / result.children[0]
    slot = (child / "Witness.lean").read_text()
    filled = slot.replace(":= by\n  sorry\n", ":= trivial\n")
    assert "sorry" not in filled.split("theorem", 1)[1]  # the proof body is real
    (child / "Witness.lean").write_text(filled, encoding="utf-8")
    assert not graphmod.witness_is_stub(child)


def test_stamp_to_date_needs_a_whole_day() -> None:
    assert postmerge.stamp_to_date("20260910T121314Z") == "2026-09-10"
    assert postmerge.stamp_to_date("2026") == "2026"  # too short to be a day: passed through


# --- the step-9 record and the gate signature: what is refused ------------------------------------


class RecordingSigner:
    """A signer that never signs: every call is recorded so a test can prove none was made."""

    def __init__(self, key_id: str = "SHA256:fake") -> None:
        self.key_id = key_id
        self.calls: list[str] = []

    def sign(self, payload: bytes, key_path: Path, kind: str) -> Signature:
        self.calls.append(f"sign:{kind}")
        return Signature(kind, self.key_id, "sig")  # type: ignore[arg-type]

    def verify(self, payload: bytes, signature: str, public_key: str) -> bool:
        self.calls.append("verify")
        return True

    def fingerprint(self, public_key: str) -> str:
        self.calls.append("fingerprint")
        return self.key_id


def test_verify_refuses_before_consulting_the_signer(tmp_path: Path) -> None:
    """An unknown signature kind, an empty value, or a key id that is not the committed key's
    is refused without a cryptographic check — a signer is never asked about garbage."""
    ctx = make_context(tmp_path)
    doc = attestation.build(ctx, pipeline.run_steps(ctx), graph_commit=None, clock=lambda: FIXED)
    signer = RecordingSigner()

    bogus = dict(doc, signature=dict(doc["signature"], kind="bogus", value="sig"))
    assert not postmerge.verify(bogus, "ssh-ed25519 AAAA", signer)
    empty = dict(doc, signature=dict(doc["signature"], kind="gate", value=""))
    assert not postmerge.verify(empty, "ssh-ed25519 AAAA", signer)
    assert signer.calls == []

    other_key = dict(doc, signature=dict(doc["signature"], kind="gate", value="sig", key_id="x"))
    assert not postmerge.verify(other_key, "ssh-ed25519 AAAA", signer)
    assert signer.calls == ["fingerprint"]  # compared, but never verified


def test_record_step9_refuses_a_malformed_review_or_commit(tmp_path: Path) -> None:
    """The post-merge fields are validated on the way in: a review kind D-4 does not have, or a
    merge commit that is not a SHA, never reaches a signature."""
    ctx = make_context(tmp_path)
    doc = attestation.build(ctx, pipeline.run_steps(ctx), graph_commit=None, clock=lambda: FIXED)
    with pytest.raises(schemas.SchemaError):
        postmerge.record_step9(doc, merge_commit="4" * 40, review={"kind": "rubber-stamp"})
    with pytest.raises(schemas.SchemaError):
        postmerge.record_step9(
            doc, merge_commit="not-a-sha", review=postmerge.review_block("tutorial")
        )
    signer = RecordingSigner()
    with pytest.raises(schemas.SchemaError):
        postmerge.finalize(
            doc,
            merge_commit="4" * 40,
            review={"kind": "rubber-stamp"},
            key_path=tmp_path / "k",
            signer=signer,
        )
    assert signer.calls == []


def test_a_bot_commit_needs_a_real_pull_request_number() -> None:
    with pytest.raises(ValueError, match="positive"):
        postmerge.bot_commit_message(0, "pass")
    with pytest.raises(ValueError, match="positive"):
        postmerge.attestation_path(Path("/g"), -3)
    assert postmerge.parse_bot_commit_message("") is None
    assert postmerge.parse_bot_commit_message("gate: #2 bounced") is None
    assert postmerge.parse_bot_commit_message("gate: #02 pass") == (2, "pass")


def test_approving_reviewer_ignores_reviews_without_a_user() -> None:
    reviews: list[dict[str, Any]] = [
        {"state": "APPROVED", "submitted_at": "2026-09-08T01:00:00Z"},
        {"state": "APPROVED", "user": None, "submitted_at": "2026-09-08T02:00:00Z"},
        {"state": "APPROVED", "user": {}, "submitted_at": "2026-09-08T03:00:00Z"},
    ]
    assert postmerge.approving_reviewer(reviews, "author") is None


def test_claims_snapshot_that_is_not_json_is_kept_out(tmp_path: Path) -> None:
    """A response that does not parse is the same story as an unreachable service (C7)."""
    graph = tmp_path / "graph"
    graph.mkdir()
    note = postmerge.refresh_claims(
        graph, "https://api.example/claims.json", opener=lambda _u, _t: b"<html>oops</html>"
    )
    assert note is not None and "JSONDecodeError" in note
    assert not (graph / "claims.json").exists()
    with pytest.raises(ValueError, match="https"):
        postmerge.fetch_claims_snapshot("ftp://api.example/claims.json")
    assert (
        postmerge.fetch_claims_snapshot("http://127.0.0.1:8000/c.json", opener=lambda _u, _t: b"{}")
        == b"{}"
    )
