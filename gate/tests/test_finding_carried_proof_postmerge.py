"""F32-T3 (R4, R5; AC6, AC7; Q7, Q10; D-3, D-5 v3.49): a hole whose proof was carried is born
proved in the merge that creates it, with an attestation of its own.

After the merge the post-merge job re-derives the verdict on the merge commit, which runs F32-R3
again (each carried proof against the node its hole becomes, on that tree), and only on a pass
does ``apply_partial`` write, beside the statement, witness and context it writes today, the
composed ``Proof.lean`` its own run checked, byte for byte. Beside the partial's attestation
(``carried_by: null``) the job leaves one ``attestation/v8`` per born-proved hole, keyed to the
hole's node and statement hash, its steps the hole's run's, its declared fields the partial's,
and ``carried_by`` pointing back to the partial by facts of the tree; the key step signs each as
``attestations/<NNNNNN>.<hole id>.json`` (Q7, T5).

Q10: the writer fails closed. If the tree it writes into would give the hole another id than the
one its proof was checked under (another decomposition of the parent merged first, or the job
caught up on a newer main), or the hole now restates an existing node, nothing is written and
nothing is attested.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from harness import TARGET, copy_graph
from test_cli_sandboxed import NODES, Seam, run
from test_finding_partial_carries_proofs import Child, proof_text
from test_finding_partial_carries_witnesses import (
    BOTH,
    NODE_WITNESS,
    STEM,
    holes_report,
    merged_with_witnesses,
    postmerge_argv,
)
from test_partial import ROOT
from test_postmerge import snapshot

from opn_gate import attestation, carried, cli, graph, postmerge, products, schemas

PROOF = f"{STEM}.1.proof"
H1, H2 = f"{ROOT}--h1", f"{ROOT}--h2"


def merged(tmp_path: Path, *, proof: bool = True) -> Path:
    """A repo whose HEAD merges one assembly carrying both witnesses and (by default) a proof
    of ``right``, the hole that becomes ``--h1``."""
    files = {**BOTH, **({PROOF: proof_text()} if proof else {})}
    return merged_with_witnesses(tmp_path, files)


def postmerge_run(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str], root: Path, **kw: Any
) -> tuple[int, dict[str, Any], str, Path]:
    seam.fake = kw.pop("fake", None) or Child(witness=NODE_WITNESS, artifact=holes_report())
    out = tmp_path / "o"
    argv = postmerge_argv(root, out)
    if "commit" in kw:
        argv[argv.index("--commit") + 1] = kw.pop("commit")
    code, doc, err = run(capsys, *argv)
    return code, doc, err, out


#: When the fixture's bot commit renders its products (F32-T6).
RECORDED_AT = "2026-09-10T12:20:00Z"


def _commit(root: Path, message: str) -> str:
    env = {
        "GIT_AUTHOR_NAME": "opn-gate",
        "GIT_AUTHOR_EMAIL": "gate@x",
        "GIT_COMMITTER_NAME": "opn-gate",
        "GIT_COMMITTER_EMAIL": "gate@x",
        "PATH": "/usr/bin:/bin",
        "HOME": str(root.parent),
    }
    for args in (("add", "-A"), ("commit", "-q", "-m", message)):
        subprocess.run(["git", "-C", str(root), *args], check=True, env=env, capture_output=True)
    return rev(root, "HEAD")


def rev(root: Path, ref: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", ref], check=True, capture_output=True, text=True
    ).stdout.strip()


def recorded(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> tuple[Path, str, str]:
    """F32-T6: AC6's merge as the record holds it once the graph workflow is done — the merge
    commit (the assembly and the carried files, no hole yet), then the bot commit: the job's
    tree (both holes, ``--h1`` with its ``Proof.lean``), both records under the names the key
    step gives them, and the products rendered from the merge. Returns (root, merge, bot)."""
    root = merged(tmp_path)
    merge = rev(root, "HEAD")
    code, _out, err, out_dir = postmerge_run(tmp_path, seam, capsys, root)
    assert code == cli.EXIT_PASS, err
    partial = postmerge.attestation_path(root, 9)
    partial.parent.mkdir(exist_ok=True)
    partial.write_bytes((out_dir / "attestation.json").read_bytes())
    postmerge.hole_attestation_path(root, 9, H1).write_bytes(
        (out_dir / "hole-attestations" / f"{H1}.json").read_bytes()
    )
    schemas.publish(root)  # the fixture serves no schemas/; a live graph does (F03-T8)
    products.generate(root, rendered_from=merge, commit_time=RECORDED_AT).write(root)
    return root, merge, _commit(root, "gate: #9 pass")


# --- AC6 ------------------------------------------------------------------------------------------


def test_the_hole_is_born_with_the_proof_its_run_checked(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC6: the proved hole's node holds the composed Proof.lean the run checked; the other hole
    is created as before; two attestations validate as attestation/v8 with R5's fields."""
    root = merged(tmp_path)
    code, out, err, out_dir = postmerge_run(tmp_path, seam, capsys, root)
    assert code == cli.EXIT_PASS, err
    assert out == {"hole_attestations": [str(out_dir / "hole-attestations" / f"{H1}.json")]}
    nodes = root / NODES
    born = (nodes / H1 / "Proof.lean").read_text(encoding="utf-8")
    statement = (nodes / H1 / "Statement.lean").read_text(encoding="utf-8")
    (read,), _ = carried.read_proofs(
        f"attempts/{STEM}.lean", {f"attempts/{PROOF}": proof_text()}, ["right"]
    )
    assert born == carried.compose_proof(statement, read)
    assert not (nodes / H2 / "Proof.lean").exists()
    assert graph.witness_is_stub(nodes / H2) is False  # both witnesses were carried
    # The carried file stays where it was submitted, as the record of what was carried (D-3).
    assert (nodes / ROOT / "attempts" / PROOF).read_text(encoding="utf-8") == proof_text()

    partial = schemas.load_json(out_dir / "attestation.json")
    hole = schemas.load_json(out_dir / "hole-attestations" / f"{H1}.json")
    for doc in (partial, hole):
        assert schemas.violations(doc, "attestation/v8") == []
    assert partial["carried_by"] is None and partial["node_id"] == ROOT
    assert hole["node_id"] == H1
    assert hole["statement_hash"] == schemas.content_hash(statement.encode("utf-8"))
    assert hole["merge_commit"] == partial["merge_commit"]
    assert hole["artifact_hash"] == schemas.content_hash(born.encode("utf-8"))
    assert hole["verdict"] == "pass" and hole["first_failing_step"] is None
    assert [(s["step"], s["result"]) for s in hole["steps"]] == [
        (n, "pass") for n in (1, 2, 4, 5, 6, 7, 8)
    ]
    assert hole["footprint"] == {"nodes": []}
    assert hole["review"] == {"kind": "intermediate", "reviewer": None, "reference": None}
    for key in ("submitter", "model_and_tooling", "automation", "precheck_attestation", "tooling"):
        assert hole[key] == partial[key], key
    assembly = root / NODES / ROOT / "attempts" / f"{STEM}.lean"
    assert hole["carried_by"] == {
        "node_id": ROOT,
        "assembly": {
            "path": f"attempts/{STEM}.lean",
            "artifact_hash": schemas.content_hash(assembly.read_bytes()),
        },
        "carried": {
            "path": f"attempts/{PROOF}",
            "sha256": schemas.content_hash(proof_text().encode("utf-8")),
        },
    }
    # D-5: every difference from the partial's record is a fact of the hole's node, never of
    # the run; the three masked fields aside, nothing else.
    differing = set(attestation.compare(partial, hole))
    assert differing <= {
        "node_id",
        "statement_hash",
        "artifact_hash",
        "steps",
        "footprint",
        "carried_by",
        "review",
        "diagnostic",
    }


def test_the_graph_derives_the_hole_proved_and_off_the_frontier(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC6: with the two records committed as the key step names them, the hole is proved
    through its own attestation, off the frontier; its sibling is ready."""
    root = merged(tmp_path)
    code, _out, err, out_dir = postmerge_run(tmp_path, seam, capsys, root)
    assert code == cli.EXIT_PASS, err
    partial = postmerge.attestation_path(root, 9)
    partial.parent.mkdir(exist_ok=True)
    partial.write_bytes((out_dir / "attestation.json").read_bytes())
    hole = postmerge.hole_attestation_path(root, 9, H1)
    assert hole.name == f"000009.{H1}.json"
    hole.write_bytes((out_dir / "hole-attestations" / f"{H1}.json").read_bytes())
    tg = graph.load_target(root, TARGET)
    assert tg.statuses[H1] == "proved" and tg.statuses[H2] == "ready"
    assert not products.in_frontier("proved", tg.nodes[H1], lambda n: tg.statuses[n])


def test_a_partial_carrying_no_proof_is_what_it_was(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC6, R4's last sentence: no Proof.lean, no hole record, the tree the witness-only writer
    makes, and an attestation that is v7's but for its schema and ``carried_by: null``."""
    root = merged(tmp_path, proof=False)
    code, _out, err, out_dir = postmerge_run(tmp_path, seam, capsys, root)
    assert code == cli.EXIT_PASS, err
    assert not (out_dir / "hole-attestations").exists()
    nodes = root / NODES
    assert not (nodes / H1 / "Proof.lean").exists() and not (nodes / H2 / "Proof.lean").exists()
    doc = schemas.load_json(out_dir / "attestation.json")
    assert doc["schema"] == "attestation/v8" and doc["carried_by"] is None
    as_v7 = {k: v for k, v in doc.items() if k != "carried_by"} | {"schema": "attestation/v7"}
    assert schemas.violations(as_v7, "attestation/v7") == []


def test_the_writer_without_proofs_writes_what_it_wrote(tmp_path: Path) -> None:
    """R4: ``proofs={}`` and no ``proofs`` at all write the same tree, byte for byte."""
    from test_postmerge import ASSEMBLY, HOLES, PARENT, PSEUDONYM, STAMP  # noqa: PLC0415

    a = copy_graph(tmp_path / "a") / "targets" / TARGET / "nodes" / PARENT
    b = copy_graph(tmp_path / "b") / "targets" / TARGET / "nodes" / PARENT
    one = postmerge.apply_partial(a, HOLES, partial_text=ASSEMBLY, pseudonym=PSEUDONYM, stamp=STAMP)
    two = postmerge.apply_partial(
        b, HOLES, partial_text=ASSEMBLY, pseudonym=PSEUDONYM, stamp=STAMP, proofs={}
    )
    assert snapshot(a) == snapshot(b) and one.as_dict() == two.as_dict()
    assert "proved" not in one.as_dict()


def test_a_rerun_of_the_writer_writes_nothing(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """The job re-run on the same merge (a replay): the hole is already the node its proof was
    written into, with that very text, so nothing is refused and nothing is written again."""
    root = merged(tmp_path)
    code, _out, err, _ = postmerge_run(tmp_path, seam, capsys, root)
    assert code == cli.EXIT_PASS, err
    before = snapshot(root / NODES / ROOT)
    code, _out, err, _ = postmerge_run(tmp_path / "again", seam, capsys, root)
    assert code == cli.EXIT_PASS, err
    assert snapshot(root / NODES / ROOT) == before


# --- AC7: fail closed -----------------------------------------------------------------------------


def later_child(root: Path, name: str, closed: str) -> None:
    """Another decomposition of the parent merged on main after the merge being recorded: a
    hole child written by the gate, committed on top."""
    from test_postmerge import hole  # noqa: PLC0415

    parent = root / NODES / ROOT
    postmerge.apply_partial(
        parent,
        [hole(name, closed)],
        partial_text="",
        pseudonym="carol",
        stamp="20260913T000000Z",
    )
    _commit(root, "another partial of the root")


@pytest.mark.parametrize(
    ("closed", "says"),
    [
        ("∀ (p q r : Prop), (p ∧ q) ∧ r → p", "becomes"),  # a new hole: --h1 is taken
        ("∀ (p q r : Prop), (p ∧ q) ∧ r → r", "restates"),  # ``right`` itself, now on record
    ],
)
def test_renumbered_fails_closed(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str], closed: str, says: str
) -> None:
    """AC7: the merge re-derived on its own commit (and passing), written into a main that has
    moved: the hole would be another node than the one its proof was checked as. The job fails
    visibly and writes no attestation, no Proof.lean and no child."""
    root = merged(tmp_path)
    merge = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    later_child(root, "other", closed)
    before = snapshot(root / NODES / ROOT)
    code, _out, err, out_dir = postmerge_run(tmp_path, seam, capsys, root, commit=merge)
    assert code not in (cli.EXIT_PASS, cli.EXIT_FAIL), err  # an error, not a verdict
    assert "not attesting this merge" in err and says in err, err
    assert not (out_dir / "attestation.json").exists()
    assert not (out_dir / "hole-attestations").exists()
    assert snapshot(root / NODES / ROOT) == before


def test_the_writer_refuses_a_renumbered_proof_before_writing(tmp_path: Path) -> None:
    """Q10 at the writer itself (the backstop the command's preflight runs): handed a proof
    checked as ``--h1`` on a tree where the hole becomes ``--h2``, it raises and writes nothing."""
    from test_postmerge import ASSEMBLY, HOLES, PARENT  # noqa: PLC0415

    parent = copy_graph(tmp_path) / "targets" / TARGET / "nodes" / PARENT
    (parent.parent / f"{PARENT}--h1").mkdir()  # an earlier decomposition's hole, by its id
    before = snapshot(parent)
    with pytest.raises(postmerge.GraphWriteError, match="was checked as"):
        postmerge.apply_partial(
            parent,
            HOLES,
            partial_text=ASSEMBLY,
            pseudonym="alice",
            stamp="20260910T121314Z",
            witnesses={"right": "theorem witness : True := trivial\n"},
            proofs={"right": postmerge.CheckedProof(f"{PARENT}--h1", "anything")},
        )
    assert snapshot(parent) == before


def test_the_command_writes_nothing_when_a_carried_proof_fails(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    """R5's last sentence: the re-derivation fails on a carried proof; no record of the merge is
    attested (the verdict is the visible failure, C7) and no child is written."""
    root = merged(tmp_path)
    fake = Child(witness=NODE_WITNESS, artifact=holes_report(), fail_replay_of=H1)
    code, out, _err, out_dir = postmerge_run(tmp_path, seam, capsys, root, fake=fake)
    assert code == cli.EXIT_FAIL
    assert out["first_failing_step"] == 4 and out["diagnostic"]["details"]["hole"] == "right"
    assert not (out_dir / "hole-attestations").exists()
    assert not (root / NODES / H1).exists() and not (root / NODES / H2).exists()
    assert json.loads((out_dir / "attestation.json").read_text())["verdict"] == "fail"
