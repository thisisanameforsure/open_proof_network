"""F32-T4 (R7; AC9; Q7, Q12, Q14; D-12 v3.49, D-19): the ledger credits a born-proved hole.

A partial that carried a hole's proof merges with two records of one merge commit: the partial's
(``carried_by: null``) and the hole's (``carried_by`` naming the partial), the latter named
``attestations/<NNNNNN>.<hole id>.json`` by the key step. The ledger writes the partial's proof
line and one proof line per born-proved hole (its node, its ``Proof.lean``, the merge commit),
both credited to the partial's author (Q14). Every reader that takes "the merge's attestation" by
merge commit (``ledger.merge_record``, read by ``merge_tooling`` and ``merge_automation``)
reads the record whose ``carried_by`` is null, never the first by name: whether a hole's record
sorts before or after ``<NNNNNN>.json`` depends on its id's first letter (Q7, Q12).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import samples
from harness import TARGET
from test_cli_sandboxed import Seam, run
from test_finding_carried_proof_postmerge import H1, H2, merged, postmerge_run
from test_finding_partial_carries_witnesses import STAMP_FILE
from test_partial import ROOT

from opn_gate import cli, ledger, postmerge, schemas

MERGE = "c" * 40
PARTIAL_TOOLING = "claude-opus-5-5 via the partial"
HOLE_TOOLING = "something the hole's record says"
PARTIAL_AUTOMATION = {"method": "agent", "models": ["the-partials-model"], "framework": "f"}
HOLE_AUTOMATION = {"method": "manual", "models": ["the-holes-model"], "framework": "f"}


def carried_by(parent: str = ROOT) -> dict[str, Any]:
    return {
        "node_id": parent,
        "assembly": {"path": f"attempts/{STAMP_FILE}", "artifact_hash": "e" * 64},
        "carried": {"path": "attempts/x.1.proof", "sha256": "f" * 64},
    }


def write(root: Path, name: str, doc: dict[str, Any]) -> None:
    directory = root / "attestations"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_bytes(schemas.canonical_json(doc))


def records(root: Path, *, hole_name: str, merge: str = MERGE) -> None:
    """The partial's record as ``000009.json`` and a hole's under ``hole_name``, the hole's
    declared fields deliberately different, so a reader that picks the wrong one is seen."""
    write(
        root,
        "000009.json",
        samples.attestation(
            node_id=ROOT, merge_commit=merge, model_and_tooling=PARTIAL_TOOLING,
            automation=PARTIAL_AUTOMATION, carried_by=None,
        ),
    )  # fmt: skip
    write(
        root,
        hole_name,
        samples.attestation(
            node_id=H1, merge_commit=merge, model_and_tooling=HOLE_TOOLING,
            automation=HOLE_AUTOMATION, carried_by=carried_by(),
        ),
    )  # fmt: skip


# Q7: the real name of erdos-68--h1's record sorts before 000009.json, a variant-… one after.
NAMES = pytest.mark.parametrize(
    "hole_name", [f"000009.{H1}.json", "000009.variant-zz--h1.json"], ids=["first", "last"]
)


# --- the merge's record (Q12) ---------------------------------------------------------------------


@NAMES
def test_the_merges_record_is_the_one_with_carried_by_null(tmp_path: Path, hole_name: str) -> None:
    records(tmp_path, hole_name=hole_name)
    names = sorted(p.name for p in (tmp_path / "attestations").iterdir())
    assert (names.index(hole_name) == 0) is (hole_name.startswith(f"000009.{H1}"))
    doc = ledger.merge_record(tmp_path, MERGE)
    assert doc is not None and doc["node_id"] == ROOT and doc["carried_by"] is None
    assert ledger.merge_tooling(tmp_path, MERGE) == PARTIAL_TOOLING
    assert ledger.merge_automation(tmp_path, MERGE) == PARTIAL_AUTOMATION


def test_a_record_older_than_v8_is_the_merges_record(tmp_path: Path) -> None:
    """attestation/v1 to v7 carry no ``carried_by`` at all: absent reads as null, so every record
    already committed stays the merge's record."""
    old = samples.attestation(merge_commit=MERGE, model_and_tooling="v7 tooling", runner="hosted")
    old.pop("carried_by", None)
    old["schema"] = "attestation/v7"
    write(tmp_path, "000001.json", old)
    assert ledger.merge_tooling(tmp_path, MERGE) == "v7 tooling"


def test_a_merge_with_only_a_holes_record_has_no_record_of_its_own(tmp_path: Path) -> None:
    """A hole's record is never taken for the merge's, even when it is the only one there."""
    write(
        tmp_path,
        f"000009.{H1}.json",
        samples.attestation(
            node_id=H1, merge_commit=MERGE, model_and_tooling=HOLE_TOOLING,
            carried_by=carried_by(),
        ),
    )  # fmt: skip
    assert ledger.merge_record(tmp_path, MERGE) is None
    assert ledger.merge_tooling(tmp_path, MERGE) == ledger.UNDECLARED
    assert ledger.merge_automation(tmp_path, MERGE) is None


# --- which holes the merge proved -----------------------------------------------------------------


def test_born_proved_names_the_holes_of_this_parent_in_this_merge(tmp_path: Path) -> None:
    records(tmp_path, hole_name=f"000009.{H1}.json")
    # Not this merge's, not this parent's, not a pass, and the partial's own: none are holes here.
    write(
        tmp_path, f"000010.{H2}.json",
        samples.attestation(node_id=H2, merge_commit="d" * 40, carried_by=carried_by()),
    )  # fmt: skip
    write(
        tmp_path, "000009.other--h1.json",
        samples.attestation(
            node_id="other--h1", merge_commit=MERGE, carried_by=carried_by("other")
        ),
    )  # fmt: skip
    write(
        tmp_path, f"000009.{H2}.json",
        samples.attestation(
            node_id=H2, merge_commit=MERGE, carried_by=carried_by(), verdict="fail",
            first_failing_step=4,
        ),
    )  # fmt: skip
    found = ledger.born_proved(tmp_path, MERGE, ROOT)
    assert [hole for hole, _doc in found] == [H1]
    assert found[0][1]["carried_by"]["node_id"] == ROOT


def test_born_proved_is_empty_without_carried_records(tmp_path: Path) -> None:
    assert ledger.born_proved(tmp_path, MERGE, ROOT) == []
    write(tmp_path, "000009.json", samples.attestation(node_id=ROOT, merge_commit=MERGE))
    assert ledger.born_proved(tmp_path, MERGE, ROOT) == []


# --- AC9: opn-gate ledger over the merge of AC6 ---------------------------------------------------


def merged_and_attested(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str], *, hole_name: str | None = None
) -> tuple[Path, str]:
    """AC6's merge, with its records committed as the key step names them (``hole_name``
    overrides the hole record's name, to make it sort after the partial's). The hole's record
    declares a different tooling, so the ledger's choice of record is visible."""
    root = merged(tmp_path)
    code, _out, err, out_dir = postmerge_run(tmp_path, seam, capsys, root)
    assert code == cli.EXIT_PASS, err
    partial = schemas.load_json(out_dir / "attestation.json")
    commit = str(partial["merge_commit"])
    partial["model_and_tooling"] = PARTIAL_TOOLING
    path = postmerge.attestation_path(root, 9)
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(schemas.canonical_json(partial))
    hole = schemas.load_json(out_dir / "hole-attestations" / f"{H1}.json")
    hole["model_and_tooling"] = HOLE_TOOLING
    named = postmerge.hole_attestation_path(root, 9, H1)
    if hole_name is not None:
        named = named.with_name(hole_name)
    named.write_bytes(schemas.canonical_json(hole))
    return root, commit


@NAMES
def test_the_ledger_credits_the_partial_and_its_born_proved_hole(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str], hole_name: str
) -> None:
    """AC9: the partial's proof line and one for the hole, both the partial's author's, both at
    the merge commit, both with the partial's record's tooling whichever record sorts first."""
    root, commit = merged_and_attested(tmp_path, seam, capsys, hole_name=hole_name)
    code, out, err = run(capsys, "ledger", "--graph", str(root), "--commit", commit)
    assert code == cli.EXIT_PASS, err
    assert out["earned"] is True and out["identity"] == "t" and out["node"] == ROOT
    assert out["entries"] == [
        {"line": "proof", "node": ROOT, "artifact": f"attempts/{STAMP_FILE}"},
        {"line": "proof", "node": H1, "artifact": "Proof.lean"},
    ]
    doc = schemas.load_json(root / "ledger" / "t.json", ledger.SCHEMA)
    partial_line, hole_line = doc["entries"]
    assert hole_line == {
        **partial_line,
        "node": H1,
        "artifact": "Proof.lean",
    }
    assert hole_line["target"] == TARGET and hole_line["merge_commit"] == commit
    assert hole_line["tooling"] == PARTIAL_TOOLING
    # Q14: the two lines differ in the ledger key, so neither hides the other.
    key = ("line", "node", "artifact", "merge_commit")
    assert tuple(partial_line[k] for k in key) != tuple(hole_line[k] for k in key)


def test_a_partial_carrying_no_proof_earns_one_line(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """R7 adds lines only for born-proved holes: without one, the ledger is what it was."""
    root = merged(tmp_path, proof=False)
    code, _out, err, out_dir = postmerge_run(tmp_path, seam, capsys, root)
    assert code == cli.EXIT_PASS, err
    commit = str(schemas.load_json(out_dir / "attestation.json")["merge_commit"])
    path = postmerge.attestation_path(root, 9)
    path.parent.mkdir(exist_ok=True)
    path.write_bytes((out_dir / "attestation.json").read_bytes())
    code, out, err = run(capsys, "ledger", "--graph", str(root), "--commit", commit)
    assert code == cli.EXIT_PASS, err
    assert out["entries"] == [{"line": "proof", "node": ROOT, "artifact": f"attempts/{STAMP_FILE}"}]
