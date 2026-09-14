"""Edges of F07-T15's ledger writer that the finding tests do not reach (F07-R12; D-13, D-31).

``test_finding_ledger_credits_merges.py`` drives one merge of each kind. These cover what a merge
can carry beside the happy path: an append with no postmortem, two postmortems of one route class
in one merge, an author that cannot hold a ledger, and ``ledger.merge_tooling`` reading records it
cannot parse.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import samples
from harness import TARGET
from test_cli_sandboxed import NODES, Seam, git_repo
from test_finding_ledger_credits_merges import PROVED, commit_postmortems, entries, ledger_run

from opn_gate import ledger, schemas

MERGE = "c" * 40


# --- ledger.merge_tooling -----------------------------------------------------------------------


def test_merge_tooling_is_undeclared_without_attestations(tmp_path: Path) -> None:
    assert ledger.merge_tooling(tmp_path, MERGE) == ledger.UNDECLARED


def test_merge_tooling_skips_a_record_it_cannot_parse(tmp_path: Path) -> None:
    directory = tmp_path / "attestations"
    directory.mkdir()
    (directory / "000001.json").write_text("{not json", encoding="utf-8")
    good = samples.attestation(merge_commit=MERGE, model_and_tooling="m v h", runner="hosted")
    (directory / "000002.json").write_bytes(schemas.canonical_json(good))
    assert ledger.merge_tooling(tmp_path, MERGE) == "m v h"


@pytest.mark.parametrize("declared", ["", None, 7])
def test_merge_tooling_is_undeclared_when_the_record_declares_nothing_usable(
    tmp_path: Path, declared: object
) -> None:
    directory = tmp_path / "attestations"
    directory.mkdir()
    doc = dict(samples.attestation(merge_commit=MERGE, runner="hosted"))
    doc["model_and_tooling"] = declared
    (directory / "000001.json").write_bytes(schemas.canonical_json(doc))
    assert ledger.merge_tooling(tmp_path, MERGE) == ledger.UNDECLARED


def test_merge_tooling_reads_only_the_record_of_this_merge(tmp_path: Path) -> None:
    directory = tmp_path / "attestations"
    directory.mkdir()
    other = samples.attestation(merge_commit="d" * 40, model_and_tooling="other", runner="hosted")
    (directory / "000001.json").write_bytes(schemas.canonical_json(other))
    assert ledger.merge_tooling(tmp_path, MERGE) == ledger.UNDECLARED


# --- opn-gate ledger over what an append can carry -----------------------------------------------


def test_an_append_with_only_an_annex_earns_nothing_and_says_why(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, git, _base = git_repo(tmp_path)
    rel = f"{NODES}/{PROVED}/annex/{'a' * 64}.md"
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text("An informal argument.\n", encoding="utf-8")
    git("add", "--", rel)
    git("commit", "-q", "--author", "alice <alice@x>", "-m", "annex")
    out = ledger_run(capsys, root, git("rev-parse", "HEAD"))
    assert out["earned"] is False
    assert "D-13" in out["reason"] and "D-31" in out["reason"], out["reason"]
    assert not (root / "ledger").exists()


def test_two_postmortems_of_one_route_class_in_one_merge_earn_once(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, git, _base = git_repo(tmp_path)
    head = commit_postmortems(root, git, PROVED, ["induction", "induction"], author="alice")
    out = ledger_run(capsys, root, head)
    assert out["earned"] is True, out
    assert [(e["line"], e["route_class"]) for e in entries(root, "alice")] == [
        ("attempts", "induction")
    ]
    assert len(out["skipped"]) == 1 and "D-13" in out["skipped"][0], out["skipped"]


def test_an_author_that_cannot_hold_a_ledger_earns_nothing_on_a_postmortem(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, git, _base = git_repo(tmp_path)
    rel_dir = root / NODES / PROVED / "attempts"
    doc = samples.postmortem(node=PROVED, contributor="x", route_class="induction")
    import yaml  # noqa: PLC0415

    (rel_dir / "20260913T120000Z-x.yaml").write_text(yaml.safe_dump(doc), encoding="utf-8")
    git("add", "--", f"{NODES}/{PROVED}/attempts")
    git("commit", "-q", "--author", "Not A Pseudonym! <n@x>", "-m", "postmortem")
    out = ledger_run(capsys, root, git("rev-parse", "HEAD"))
    assert out["earned"] is False
    assert "'Not A Pseudonym!' cannot hold a ledger" in out["reason"], out["reason"]
    assert not (root / "ledger").exists()


def test_the_entry_names_the_target_it_was_earned_on(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, git, _base = git_repo(tmp_path)
    head = commit_postmortems(root, git, PROVED, ["case-split"], author="alice")
    ledger_run(capsys, root, head)
    (entry,) = entries(root, "alice")
    assert entry["target"] == TARGET and entry["node"] == PROVED
    assert entry["artifact"] == "attempts/20260913T120000Z-alice.yaml"
