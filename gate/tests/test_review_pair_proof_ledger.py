"""F26-T18 (R8; D-19): a merged pair-proof record earns its author the review line.

``ledger.MERGE_LINES["pair-proof"] == "review"`` is the contract (F26-T16); this drives the
post-merge ``opn-gate ledger`` step over a merge that added one record. The entry: line
``review``, the target's root as ``node`` (a pair direction is work on the review of the target's
statement, and ``ledger/v2`` needs a node), ``artifact`` the record's path under the target
(``review/pair-proofs/<name>``, the registration line's precedent for a record that lives outside
any node), the identity the record's ``author``, the tooling its ``models``. No other review
record earns one at merge, and a replay of the merge writes nothing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import TARGET
from test_cli_sandboxed import git_repo, run

from opn_gate import cli, graph, ledger, pair_proofs, schemas

AUTHOR = "t1027-j"
A, B = "c-aaaaaaaa", "c-bbbbbbbb"
NAME = pair_proofs.record_name(A, B, "forward", "20261027T010000Z", AUTHOR)
REL = f"targets/{TARGET}/review/{pair_proofs.DIR}/{NAME}"


def record(**kw: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": "pair-proof/v1",
        "target": TARGET,
        "a": A,
        "b": B,
        "direction": "forward",
        "kind": "proof",
        "case": None,
        "statement_hashes": {"a": "a" * 64, "b": "b" * 64},
        "lean": "-- opn-review: {}\n",
        "author": AUTHOR,
        "models": ["claude-opus-5-5"],
        "date": "2026-10-27T01:00:00Z",
    }
    doc.update(kw)
    return doc


def merge(tmp_path: Path, files: dict[str, Any], *, author: str = AUTHOR) -> tuple[Path, str]:
    """A merge adding ``files`` (path -> YAML document), committed by ``author``."""
    root, git, _base = git_repo(tmp_path)
    for rel, doc in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
        git("add", "--", rel)
    git("commit", "-q", "--author", f"{author} <a@x>", "-m", "pair proof")
    return root, git("rev-parse", "HEAD")


def test_a_merged_pair_proof_earns_its_author_the_review_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root, commit = merge(tmp_path, {REL: record()})
    code, out, err = run(capsys, "ledger", "--graph", str(root), "--commit", commit)
    assert code == cli.EXIT_PASS, err
    assert out["earned"] is True, out
    assert (out["identity"], out["line"]) == (AUTHOR, "review")
    the_root = graph.load_target(root, TARGET).root
    doc = schemas.load_json(root / "ledger" / f"{AUTHOR}.json", "ledger/v2")
    (entry,) = ledger.entries_of(doc)
    assert entry == {
        "line": "review",
        "target": TARGET,
        "node": the_root,
        "artifact": f"review/{pair_proofs.DIR}/{NAME}",
        "merge_commit": commit,
        "date": entry["date"],
        "tooling": "claude-opus-5-5",
        "status": "active",
        "automation": None,
    }
    assert out["written"] == [f"ledger/{AUTHOR}.json"]


def test_the_record_names_the_identity_not_the_commit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The service opens the pull request for the record's author (F18-Q7's precedent): the
    entry goes to ``author``, whoever's name the commit carries."""
    root, commit = merge(tmp_path, {REL: record()}, author="someone-else")
    code, out, err = run(capsys, "ledger", "--graph", str(root), "--commit", commit)
    assert code == cli.EXIT_PASS, err
    assert out["identity"] == AUTHOR
    assert not (root / "ledger" / "someone-else.json").exists()


def test_several_models_are_the_tooling_and_none_is_undeclared(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root, commit = merge(tmp_path, {REL: record(models=["m-one", "m-two"])})
    run(capsys, "ledger", "--graph", str(root), "--commit", commit)
    (entry,) = ledger.entries_of(ledger.load(root, AUTHOR))
    assert entry["tooling"] == "m-one, m-two"
    root2, commit2 = merge(tmp_path / "two", {REL: record(models=[])})
    run(capsys, "ledger", "--graph", str(root2), "--commit", commit2)
    (entry,) = ledger.entries_of(ledger.load(root2, AUTHOR))
    assert entry["tooling"] == ledger.UNDECLARED


def test_a_refutation_earns_the_same_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    case = {"probe": "holds", "n": 7, "set": None, "concept": None}
    root, commit = merge(tmp_path, {REL: record(kind="refutation", case=case)})
    code, out, err = run(capsys, "ledger", "--graph", str(root), "--commit", commit)
    assert code == cli.EXIT_PASS, err
    assert out["earned"] is True and out["line"] == "review"


def test_a_replay_of_the_merge_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """F07-T33: the post-merge job may replay a merge; credit is once per record."""
    root, commit = merge(tmp_path, {REL: record()})
    run(capsys, "ledger", "--graph", str(root), "--commit", commit)
    before = (root / "ledger" / f"{AUTHOR}.json").read_bytes()
    code, out, err = run(capsys, "ledger", "--graph", str(root), "--commit", commit)
    assert code == cli.EXIT_PASS, err
    assert out["earned"] is False and "already" in out["reason"], out
    assert (root / "ledger" / f"{AUTHOR}.json").read_bytes() == before


def test_an_unreadable_record_earns_nothing_and_says_why(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = record()
    del bad["author"]
    root, commit = merge(tmp_path, {REL: bad})
    code, out, err = run(capsys, "ledger", "--graph", str(root), "--commit", commit)
    assert code == cli.EXIT_PASS, err
    assert out["earned"] is False and NAME in out["reason"], out
    assert not (root / "ledger").exists()


@pytest.mark.parametrize(
    "rel",
    [
        f"targets/{TARGET}/review/candidates/c-aaaaaaaa.yaml",
        f"targets/{TARGET}/review/answers/a-1.yaml",
        f"targets/{TARGET}/review/signatures/s-1.yaml",
        f"targets/{TARGET}/review/review.yaml",
        f"targets/{TARGET}/review/pairs/{A}--{B}.yaml",
        f"targets/{TARGET}/review/questions/q-1.yaml",
    ],
)
def test_no_other_review_record_earns_a_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], rel: str
) -> None:
    root, commit = merge(tmp_path, {rel: {"schema": "whatever"}})
    code, out, err = run(capsys, "ledger", "--graph", str(root), "--commit", commit)
    assert code == cli.EXIT_PASS, err
    assert out["earned"] is False, out
    assert not (root / "ledger").exists()


def test_review_entry_is_pure_and_validates() -> None:
    entry = ledger.review_entry(
        target=TARGET,
        node="root-node",
        artifact=f"review/{pair_proofs.DIR}/{NAME}",
        merge_commit="1" * 40,
        date="2026-10-27T01:00:00Z",
        models=["claude-opus-5-5"],
    )
    doc = ledger.append({"schema": ledger.SCHEMA, "identity": AUTHOR, "entries": []}, entry)
    assert schemas.validate(doc, "ledger/v2")["entries"][0]["line"] == "review"
