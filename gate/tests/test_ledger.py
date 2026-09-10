"""F07-T5: the ledger's two lines and its exclusions (R12; AC16, AC17).

D-19's ledger is a record of artifacts with no weights, so the only judgment in it is *which*
merges earn an entry. That is what these tests pin.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from opn_gate import ledger, schemas

TARGET = "propositional"
NODE = "and-reassoc"
MERGE = "1" * 40
DATE = "2026-09-10T12:00:00Z"


def proof(**kw: object) -> ledger.Entry | None:
    args: dict[str, object] = {
        "identity": "alice",
        "target": TARGET,
        "node": NODE,
        "artifact_type": "proof",
        "artifact": "Proof.lean",
        "merge_commit": MERGE,
        "date": DATE,
    }
    args.update(kw)
    return ledger.proof_entry(**args)  # type: ignore[arg-type]


def postmortem(doc: dict[str, object], **kw: object) -> ledger.Entry | None:
    args: dict[str, object] = {
        "identity": "alice",
        "target": TARGET,
        "node": NODE,
        "route_class": "induction",
        "artifact": "attempts/2026-09-10-alice.yaml",
        "merge_commit": MERGE,
        "date": DATE,
    }
    args.update(kw)
    return ledger.postmortem_entry(doc, **args)  # type: ignore[arg-type]


def empty() -> dict[str, object]:
    return {"schema": ledger.SCHEMA, "identity": "alice", "entries": []}


# --- the proof line (R12; D-12, D-19) ------------------------------------------------------------


@pytest.mark.parametrize("artifact_type", ledger.PROOF_ARTIFACTS)
def test_every_kernel_checked_artifact_earns_the_proof_line(artifact_type: str) -> None:
    """R12: proofs, counterexamples, vacuity certificates and partial assemblies all count.

    D-12 calls a root-level counterexample a research result, so paying only for proofs would
    price the record dishonestly.
    """
    entry = proof(artifact_type=artifact_type)
    assert entry is not None
    assert entry.line == "proof"
    assert entry.status == "active"
    assert schemas.violations(ledger.append(empty(), entry), ledger.SCHEMA) == []


def test_an_annex_or_approach_record_earns_nothing() -> None:
    """D-31, D-14: an annex is input and earns nothing ever; an approach record is paid
    retroactively on demonstrated reuse, which is not a thing a merge can see."""
    assert proof(artifact_type="annex") is None
    assert proof(artifact_type="approach-record") is None
    assert proof(artifact_type="explainer") is None


def test_tutorial_off_ledger() -> None:
    """AC17, D-27: the tutorial node mints identities, so paying for it would make minting one
    a way to be paid."""
    assert proof(tutorial=True) is None
    assert postmortem(empty(), tutorial=True) is None


# --- the attempts line (R12; D-13) ---------------------------------------------------------------


def test_first_per_route_class(tmp_path: Path) -> None:
    """AC16: the first postmortem of a route class on a node earns; the second does not."""
    doc = empty()
    first = postmortem(doc)
    assert first is not None and first.line == "attempts" and first.route_class == "induction"
    doc = ledger.append(doc, first)

    assert postmortem(doc) is None  # same node, same class

    # A different class on the same node earns, and so does the same class on another node.
    other_class = postmortem(doc, route_class="case-split")
    assert other_class is not None
    doc = ledger.append(doc, other_class)
    other_node = postmortem(doc, node="tutorial-and-swap")
    assert other_node is not None

    assert [e["line"] for e in ledger.entries_of(doc)] == ["attempts", "attempts"]
    assert schemas.violations(doc, ledger.SCHEMA) == []


def test_first_is_per_identity_not_per_graph() -> None:
    """D-13: two contributors may each be first to a class they were first to; the ledger a
    question is asked of is the one being written."""
    alice = ledger.append(empty(), postmortem(empty()))  # type: ignore[arg-type]
    bob: dict[str, object] = {"schema": ledger.SCHEMA, "identity": "bob", "entries": []}
    assert postmortem(alice) is None
    assert postmortem(bob) is not None


# --- reading and writing (R12: append-only, bot-owned) -------------------------------------------


def test_record_appends_and_never_rewrites(tmp_path: Path) -> None:
    entry = proof()
    assert entry is not None
    path = ledger.record(tmp_path, "alice", entry)
    assert path == tmp_path / "ledger" / "alice.json"
    assert path is not None

    again = ledger.record(tmp_path, "alice", proof(artifact_type="counterexample"))
    assert again is not None
    doc = ledger.load(tmp_path, "alice")
    assert [e["artifact"] for e in ledger.entries_of(doc)] == ["Proof.lean", "Proof.lean"]
    assert [e["line"] for e in ledger.entries_of(doc)] == ["proof", "proof"]
    assert schemas.violations(doc, ledger.SCHEMA) == []


def test_earning_nothing_writes_nothing(tmp_path: Path) -> None:
    """C7: a merge that pays for nothing leaves no file behind, so an empty ledger never appears."""
    assert ledger.record(tmp_path, "alice", proof(tutorial=True)) is None
    assert not (tmp_path / "ledger").exists()


def test_contributions_reads_active_entries(tmp_path: Path) -> None:
    """What the site consumes (D-36): every entry per identity, revoked ones included (D-18)."""
    ledger.record(tmp_path, "alice", proof())
    revoked = ledger.Entry(
        line="proof",
        target=TARGET,
        node=NODE,
        artifact="Proof.lean",
        merge_commit=MERGE,
        date=DATE,
        status="revoked",
    )
    ledger.write(tmp_path, ledger.append(ledger.load(tmp_path, "alice"), revoked))
    ledger.record(tmp_path, "bob", proof(identity="bob"))

    found = ledger.contributions(tmp_path)
    assert sorted(found) == ["alice", "bob"]
    # D-18 revokes by marking, not by deleting: the entry is still there, labelled.
    assert [e["status"] for e in found["alice"]] == ["active", "revoked"]
    assert ledger.contributions(tmp_path / "nowhere") == {}


def test_tooling_defaults_to_undeclared() -> None:
    """R13: a hand-opened pull request declares nothing, and the record says so rather than
    pretending it knows."""
    entry = proof()
    assert entry is not None and entry.tooling == ledger.UNDECLARED
    declared = proof(tooling="claude-opus-5 claude-code")
    assert declared is not None and declared.as_dict()["tooling"] == "claude-opus-5 claude-code"
