"""Finding ledger-credits-merges (the Euclid tester, 2026-09-13; F07-R12, D-19, D-13, D-21, D-25,
D-27).

``opn_gate.ledger`` has had ``proof_entry`` and ``postmortem_entry`` since F07-T5, with the tutorial
and curator exclusions, but nothing calls them: ``cli.run_ledger`` is F08-R13's statement-line
writer and answers every other merge with ``not a merged node proposal``. So no merged proof,
partial assembly or first postmortem has ever reached a ledger, and the Contributors page is empty
of everything but statements. These tests drive ``opn-gate ledger`` over one merge of each kind
and assert what it should write.

Identity stays the commit author (``proposer_of``); tooling is the ``model_and_tooling`` of the
attestation the same post-merge job wrote for this merge commit, else ``undeclared``.

Held as strict expected failures from f80151b until F07-T15 (2026-09-14).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from harness import TARGET
from test_cli_sandboxed import NODES, Git, Seam, git_repo, run
from test_postmerge_apply import STAMP_FILE, merged_partial

from opn_gate import cli, ledger, schemas
from opn_gate import graph as graphmod

PROVED = "and-reassoc"  # non-tutorial, proved in the fixture
OTHER = "and-swap-reassoc"
DECLARED = "claude-opus-5 2026-09 claude-code"


def ledger_run(capsys: pytest.CaptureFixture[str], root: Path, commit: str) -> dict[str, Any]:
    code, out, err = run(capsys, "ledger", "--graph", str(root), "--commit", commit)
    assert code == cli.EXIT_PASS, err
    return out


def commit_proof(root: Path, git: Git, node: str, *, author: str) -> str:
    """Take ``node``'s proof out in a commit of its own, then merge it back as ``author``'s."""
    proof = root / NODES / node / "Proof.lean"
    text = proof.read_text(encoding="utf-8")
    proof.unlink()
    git("add", "--", f"{NODES}/{node}")
    git("commit", "-q", "-m", f"{node}, unproved")
    proof.write_text(text, encoding="utf-8")
    git("add", "--", f"{NODES}/{node}/Proof.lean")
    git("commit", "-q", "--author", f"{author} <{author}@x>", "-m", f"prove {node}")
    return git("rev-parse", "HEAD")


def commit_postmortems(
    root: Path, git: Git, node: str, route_classes: list[str], *, author: str, second: int = 0
) -> str:
    """One merged append carrying a postmortem per route class, by ``author``."""
    paths = []
    for i, route_class in enumerate(route_classes):
        name = f"20260913T12{second:02d}{i:02d}Z-{author}.yaml"
        rel = f"{NODES}/{node}/attempts/{name}"
        doc = samples.postmortem(node=node, contributor=author, route_class=route_class)
        (root / rel).write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
        paths.append(rel)
    git("add", "--", *paths)
    git("commit", "-q", "--author", f"{author} <{author}@x>", "-m", f"postmortems on {node}")
    return git("rev-parse", "HEAD")


def entries(root: Path, identity: str) -> list[dict[str, Any]]:
    doc = schemas.load_json(root / "ledger" / f"{identity}.json", ledger.SCHEMA)
    return ledger.entries_of(doc)


def test_a_merged_proof_earns_the_proof_line(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, git, _base = git_repo(tmp_path)
    head = commit_proof(root, git, PROVED, author="alice")
    out = ledger_run(capsys, root, head)
    assert out["earned"] is True, out
    assert out["commit"] == head and out["identity"] == "alice"
    assert out["written"] == "ledger/alice.json"
    assert [(e["line"], e["node"], e["artifact"]) for e in out["entries"]] == [
        ("proof", PROVED, "Proof.lean")
    ]
    (entry,) = entries(root, "alice")
    assert entry["line"] == "proof" and entry["target"] == TARGET and entry["node"] == PROVED
    assert entry["artifact"] == "Proof.lean"
    assert entry["merge_commit"] == head
    assert entry["date"] == graphmod.commit_timestamp(root, head)
    assert entry["tooling"] == ledger.UNDECLARED  # no attestation for this merge on disk


def test_the_tutorial_proof_earns_nothing_and_says_d27(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, git, _base = git_repo(tmp_path, author="alice")  # HEAD proves tutorial-and-swap
    out = ledger_run(capsys, root, git("rev-parse", "HEAD"))
    assert out["earned"] is False
    assert "D-27" in out["reason"], out["reason"]
    assert not (root / "ledger").exists()


def test_a_merged_partial_earns_the_proof_line_for_the_assembly(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, _assembly, _ = merged_partial(tmp_path)  # committed by author "t"
    head = cli._git(root, "rev-parse", "HEAD").stdout.strip()
    out = ledger_run(capsys, root, head)
    assert out["earned"] is True, out
    (entry,) = entries(root, "t")
    assert entry["line"] == "proof" and entry["node"] == OTHER
    assert entry["artifact"] == f"attempts/{STAMP_FILE}"
    assert entry["merge_commit"] == head


def test_a_merged_alternate_earns_nothing_until_write_up(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, git, _base = git_repo(tmp_path)
    rel = f"{NODES}/{PROVED}/attempts/20260913T120000Z-bob-alternate.lean"
    proof = (root / NODES / PROVED / "Proof.lean").read_text(encoding="utf-8")
    (root / rel).write_text(proof, encoding="utf-8")
    git("add", "--", rel)
    git("commit", "-q", "--author", "bob <bob@x>", "-m", "alternate")
    out = ledger_run(capsys, root, git("rev-parse", "HEAD"))
    assert out["earned"] is False
    assert "D-25" in out["reason"] and "write-up" in out["reason"], out["reason"]
    assert not (root / "ledger").exists()


def test_postmortems_earn_attempts_first_per_route_class(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, git, _base = git_repo(tmp_path)
    first = commit_postmortems(root, git, PROVED, ["induction", "case-split"], author="alice")
    out = ledger_run(capsys, root, first)
    assert out["earned"] is True, out
    found = entries(root, "alice")
    assert [(e["line"], e["route_class"]) for e in found] == [
        ("attempts", "induction"),
        ("attempts", "case-split"),
    ]
    assert {e["merge_commit"] for e in found} == {first}
    assert all(e["artifact"].startswith("attempts/") for e in found)
    before = (root / "ledger" / "alice.json").read_bytes()

    again = commit_postmortems(root, git, PROVED, ["induction"], author="alice", second=1)
    out = ledger_run(capsys, root, again)
    assert out["earned"] is False
    assert "D-13" in out["reason"], out["reason"]
    assert (root / "ledger" / "alice.json").read_bytes() == before


def test_the_curator_earns_no_proof_line_but_does_earn_attempts(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, git, _base = git_repo(tmp_path)
    record = root / "targets" / TARGET / "target.yaml"
    doc = samples.target_record(id=TARGET, curator="alice")
    record.write_text(yaml.safe_dump(schemas.validate(doc), sort_keys=False))
    git("add", "--", f"targets/{TARGET}/target.yaml")
    git("commit", "-q", "-m", "curated by alice")

    by_curator = commit_proof(root, git, PROVED, author="alice")
    out = ledger_run(capsys, root, by_curator)
    assert out["earned"] is False
    assert "D-21" in out["reason"], out["reason"]
    assert not (root / "ledger" / "alice.json").exists()

    by_bob = commit_proof(root, git, OTHER, author="bob")
    out = ledger_run(capsys, root, by_bob)
    assert out["earned"] is True, out
    assert [e["line"] for e in entries(root, "bob")] == ["proof"]

    postmortem = commit_postmortems(root, git, PROVED, ["induction"], author="alice")
    out = ledger_run(capsys, root, postmortem)
    assert out["earned"] is True, out
    assert [e["line"] for e in entries(root, "alice")] == ["attempts"]


def test_tooling_comes_from_the_attestation_of_this_merge(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, git, _base = git_repo(tmp_path)
    head = commit_proof(root, git, PROVED, author="alice")
    attestations = root / "attestations"
    attestations.mkdir()
    review = {"kind": "pr-approval", "reviewer": "rev", "reference": None}
    # Another merge's record declares something else: it must not be read for this one.
    other = samples.attestation(
        node_id=PROVED, merge_commit="e" * 40, runner="hosted", review=review,
        model_and_tooling="some-other-model", submitter="alice",
    )  # fmt: skip
    mine = samples.attestation(
        node_id=PROVED, merge_commit=head, runner="hosted", review=review,
        model_and_tooling=DECLARED, submitter="alice",
    )  # fmt: skip
    (attestations / "000006.json").write_bytes(schemas.canonical_json(schemas.validate(other)))
    (attestations / "000007.json").write_bytes(schemas.canonical_json(schemas.validate(mine)))
    out = ledger_run(capsys, root, head)
    assert out["earned"] is True, out
    (entry,) = entries(root, "alice")
    assert entry["tooling"] == DECLARED

    # With only another merge's record on disk, this merge's tooling is undeclared.
    (attestations / "000007.json").unlink()
    (root / "ledger" / "alice.json").unlink()
    out = ledger_run(capsys, root, head)
    assert out["earned"] is True, out
    (entry,) = entries(root, "alice")
    assert entry["tooling"] == ledger.UNDECLARED
