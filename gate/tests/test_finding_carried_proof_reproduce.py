"""F32-T7 (R6; D-5 v3.49; Q7): ``reproduce --node <hole>`` for a hole born proved.

A merge commits one attestation per node it settles (D-5 v3.49): the partial's, and one per hole
its carried proofs made proved. The hole has no directory at the merge commit (the post-merge job
writes it afterwards), so its record is reproduced by replaying the partial at that commit and
taking the hole's own run, exactly as the post-merge job took it. ``--compare`` then holds the
hole's record to the committed one with D-5's three fields masked and nothing else: the
back-pointer ``carried_by`` is facts of the tree and is compared like any other field.

The fast tier over the fake seam; the real sandbox is ``..._reproduce_docker.py``.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from harness import TARGET
from test_cli_sandboxed import Seam, json_documents
from test_finding_carried_proof_postmerge import H1, H2, merged, postmerge_run
from test_finding_partial_carries_proofs import Child
from test_finding_partial_carries_witnesses import NODE_WITNESS, holes_report
from test_partial import ROOT

from opn_gate import attestation, cli, schemas

TOOL = Path(__file__).resolve().parents[1] / "tools" / "check_reproduce.py"
AUTOMATION = {"method": "agent", "models": ["claude-opus-5-5"], "framework": "Claude Code 2.1"}


def merge_attested(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> tuple[Path, str, dict[str, Any], dict[str, Any]]:
    """The merge of AC6, attested by the post-merge job: (graph, merge commit, the partial's
    record, the hole's record), each as the key step would commit it (signing is masked)."""
    root = merged(tmp_path)
    merge = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    code, _out, err, out_dir = postmerge_run(tmp_path, seam, capsys, root)
    assert code == cli.EXIT_PASS, err
    partial = schemas.load_json(out_dir / "attestation.json")
    hole = schemas.load_json(out_dir / "hole-attestations" / f"{H1}.json")
    return root, merge, partial, hole


def reproduce(  # noqa: PLR0917 — the command's arguments, in the order they are typed
    capsys: pytest.CaptureFixture[str],
    seam: Seam,
    root: Path,
    merge: str,
    node: str,
    out: Path,
    *extra: str,
) -> tuple[int, list[dict[str, Any]], str]:
    """``reproduce --node <node>`` at the merge commit, on a fresh fake seam; every JSON
    document printed, in order, and stderr."""
    seam.fake = Child(witness=NODE_WITNESS, artifact=holes_report())
    argv = ["reproduce", "--graph", str(root), "--commit", merge, "--node", node,
            "--target", TARGET, "--out", str(out), *extra]  # fmt: skip
    code = cli.main(argv)
    captured = capsys.readouterr()
    return code, json_documents(captured.out), captured.err


def committed_file(tmp_path: Path, name: str, doc: dict[str, Any]) -> Path:
    path = tmp_path / "committed" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(schemas.canonical_json(doc))
    return path


# --- R6: the hole's record, reproduced ------------------------------------------------------------


def test_reproduce_a_born_proved_hole_writes_its_record_beside_the_partials(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """R6: given the hole and the merge commit, the partial is replayed at that commit; its
    record is ``attestation.json`` as ever, and the hole's own run's record is written beside it
    with every fact of the tree the post-merge job recorded."""
    root, merge, _partial, committed = merge_attested(tmp_path, seam, capsys)
    out = tmp_path / "r"
    code, docs, err = reproduce(capsys, seam, root, merge, H1, out)
    assert code == cli.EXIT_PASS, err
    assert schemas.load_json(out / "attestation.json")["node_id"] == ROOT
    path = out / "hole-attestations" / f"{H1}.json"
    assert docs[-1] == {"hole_attestation": str(path)}
    doc = schemas.load_json(path)
    assert schemas.violations(doc, "attestation/v8") == []
    for key in ("node_id", "statement_hash", "artifact_hash", "steps", "verdict", "footprint",
                "carried_by", "graph_commit", "trust_base"):  # fmt: skip
        assert doc[key] == committed[key], key
    assert doc["merge_commit"] is None  # D-5: the reproduction is not the merge's record


def test_reproduce_compare_on_the_hole_is_identical(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """R6, AC10's fast half: ``--compare`` against the committed hole record reports identical,
    exit 0, as the existing comparison reports it for any record."""
    root, merge, _partial, hole = merge_attested(tmp_path, seam, capsys)
    path = committed_file(tmp_path, f"000009.{H1}.json", hole)
    code, docs, err = reproduce(
        capsys, seam, root, merge, H1, tmp_path / "r", "--compare", str(path)
    )
    assert code == cli.EXIT_PASS, err
    assert docs[-1] == {"identical": True, "differing_fields": []}


def test_reproduce_compare_on_the_parent_is_identical(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """R6 "on either": the partial's own record, ``carried_by: null``, reproduces as before."""
    root, merge, partial, _hole = merge_attested(tmp_path, seam, capsys)
    path = committed_file(tmp_path, "000009.json", partial)
    code, docs, err = reproduce(
        capsys, seam, root, merge, ROOT, tmp_path / "r", "--compare", str(path)
    )
    assert code == cli.EXIT_PASS, err
    assert docs[-1] == {"identical": True, "differing_fields": []}
    assert not (tmp_path / "r" / "hole-attestations").exists()  # the parent route is unchanged


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("carried_by", "carried"),  # the back-pointer is facts of the tree: compared, not masked
        ("artifact_hash", "0" * 64),
        ("statement_hash", "1" * 64),
    ],
)
def test_a_hole_record_that_differs_is_not_reproduced(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str], field: str, value: str
) -> None:
    """D-5 v3.49: nothing new is masked. A committed hole record whose back-pointer, artifact
    or statement hash the tree does not give is named, exit 1."""
    root, merge, _partial, hole = merge_attested(tmp_path, seam, capsys)
    tampered = dict(hole)
    if field == "carried_by":
        tampered["carried_by"] = {
            **hole["carried_by"],
            "carried": {**hole["carried_by"]["carried"], "sha256": "2" * 64},
        }
    else:
        tampered[field] = value
    path = committed_file(tmp_path, f"000009.{H1}.json", tampered)
    code, docs, _err = reproduce(
        capsys, seam, root, merge, H1, tmp_path / "r", "--compare", str(path)
    )
    assert code == cli.EXIT_FAIL
    assert docs[-1] == {"identical": False, "differing_fields": [field]}


def test_masking_is_exactly_d5s_three_fields() -> None:
    """D-5 v3.49: the back-pointer is facts of the tree, so the mask is what it was."""
    assert attestation.MASKED_FIELDS == ("runner", "merge_commit", "signature")


@pytest.mark.parametrize("node", [ROOT, H1])
def test_a_declared_automation_block_is_copied_like_every_declared_field(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str], node: str
) -> None:
    """D-5, F07-T14: what a submission declares is not a function of the tree, so a
    reproduction copies it from the committed record. ``automation`` (D-23 v3.37) is declared
    like ``submitter`` and ``model_and_tooling``, and a hole's record carries the partial's
    (F32-R5), so a partial that declared one must still reproduce on either record."""
    root, merge, partial, hole = merge_attested(tmp_path, seam, capsys)
    doc = dict(partial if node == ROOT else hole, automation=AUTOMATION)
    assert schemas.violations(doc, "attestation/v8") == []
    path = committed_file(tmp_path, "declared.json", doc)
    code, docs, _err = reproduce(
        capsys, seam, root, merge, node, tmp_path / "r", "--compare", str(path)
    )
    assert docs[-1] == {"identical": True, "differing_fields": []}
    assert code == cli.EXIT_PASS


def test_a_hole_the_merge_carried_no_proof_for_is_refused(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--node`` naming a hole the merge made but carried no proof for (its record is the
    partial's alone) is an error that names the node, exit 2, with no hole record written."""
    root, merge, _partial, _hole = merge_attested(tmp_path, seam, capsys)
    out = tmp_path / "r"
    code, _docs, err = reproduce(capsys, seam, root, merge, H2, out)
    assert code == cli.EXIT_ERROR
    assert H2 in err and "carried no checked proof" in err, err
    assert not (out / "hole-attestations").exists()


# --- check_reproduce.py: the laptop tool takes the hole's file and the same comparison ------------


def load_tool() -> Any:
    spec = importlib.util.spec_from_file_location("check_reproduce", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("node", [ROOT, H1])
def test_check_reproduce_compares_the_record_it_was_given(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str], node: str
) -> None:
    """``check_reproduce.py <NNNNNN>.<hole>`` passes the record's node to ``reproduce.sh`` and
    must read back the hole's reproduction, not the partial's ``attestation.json``; on either
    record its verdict is the CLI's (declared fields and step 9 copied, D-5's mask)."""
    root, merge, partial, hole = merge_attested(tmp_path, seam, capsys)
    out = tmp_path / "r"
    code, _docs, err = reproduce(capsys, seam, root, merge, node, out)
    assert code == cli.EXIT_PASS, err
    committed = partial if node == ROOT else hole
    assert load_tool().differing_fields(committed, out) == []
