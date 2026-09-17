"""Finding: a D-8 revision of an unwitnessed hole could never be admitted (F08-T9, R14, AC20; Q21).

Found live 2026-09-17, correcting the five mis-generated holes of the calibration run. The
post-merge writer creates a hole child with a placeholder ``Witness.lean``, the slot, and never
passes admission (D-29: a hole is admitted without a witness and stays blocked until one is
supplied). ``curator.revise`` copies the old node's witness into the revision (R9), so a revision
of a hole nobody had witnessed arrived carrying that slot, and admission ran step 7 on it and
refused ``witness-sorry``: four of five corrections were refused, and the two that landed needed
a hand-written witness. The asymmetry was the gate's: the writer may create such a node, a
curator may not correct one.

The carve-out is in admission only, under the stable check name ``witness``, and holds only when
the node's origin is a hole origin, its ``supersedes`` names a hole-origin node of the target, and
the witness is byte for byte the slot the writer writes. Anything a curator touched meets step 7 in
full, and the submission pipeline's step 7 is untouched. The pass is recorded (C7), and the
products derive ``blocked``/``witness-missing`` for the revision as for the hole (F03-T9).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from fakes import FakeToolchain, witness_result
from harness import TARGET, copy_graph, make_context
from test_curator import AUTHOR, DATE, nodes_dir, tree, write_request
from test_finding_hole_frontier import declare_root

from opn_gate import admit, cli, curator, postmerge, products, scaffold
from opn_gate import graph as graphmod
from opn_gate.paths import Claim
from opn_gate.steps.base import RunContext

ROOT_NODE = "and-swap-reassoc"
HOLE = "and-swap-reassoc--h1"
REVISION = HOLE + "-v2"
SLOT = postmerge.WITNESS_SLOT.format(expected="True")
REAL = "/-! A filled slot. -/\n\ntheorem witness : True := trivial\n"
STATEMENT = (
    "/-! Hole of a merged partial proof, as a node (D-12 #5, D-29). -/\n\n"
    "theorem OpnProp.and_swap_reassoc_h1 : True := by\n  sorry\n"
)
GOOD = witness_result(expected="True", witness="True")
STUBBED = witness_result(expected="True", witness="True", axioms=("sorryAx",))


def scaffold_hole(root: Path, *, origin: str = "skeleton-hole", witness: str = SLOT) -> Path:
    """The hole as the post-merge job creates it (``scaffold.write`` with the writer's slot)."""
    proposal = scaffold.Proposal(
        node_id=HOLE,
        target_id=TARGET,
        statement=STATEMENT,
        witness=witness,
        author=AUTHOR,
        origin=origin,  # type: ignore[arg-type]
        date=DATE,
    )
    return scaffold.write(nodes_dir(root), proposal)


def revise_hole(root: Path, **kw: Any) -> curator.Revision:
    request = write_request(root, HOLE)
    return curator.revise(root, TARGET, HOLE, STATEMENT, request, author=AUTHOR, date=DATE, **kw)


def admission_of(tmp_path: Path, node_id: str, toolchain: FakeToolchain) -> RunContext:
    ctx = make_context(tmp_path, node_id=ROOT_NODE, toolchain=toolchain)
    ctx.claim = Claim(TARGET, node_id)
    return ctx


def check(result: admit.Admission, name: str) -> tuple[str, str | None]:
    record = next(c for c in result.checks if c.name == name)
    return record.result, record.diagnostic.code if record.diagnostic else None


def witness_was_consulted(toolchain: FakeToolchain) -> bool:
    return any(str(c).startswith("witness_type:") for c in toolchain.calls)


# --- AC20: the carve-out, and its exact edges --------------------------------------------------


@pytest.mark.parametrize("origin", graphmod.HOLE_ORIGINS)
def test_a_revision_of_an_unwitnessed_hole_is_admitted_with_its_slot_open(
    tmp_path: Path, origin: str
) -> None:
    """The live defect: a hole revision carrying the writer's slot is admitted, blocked, with the
    pass recorded, and the witness metaprogram is not consulted (it never was for the hole)."""
    toolchain = FakeToolchain(witness=STUBBED)
    ctx = admission_of(tmp_path, REVISION, toolchain)
    scaffold_hole(ctx.graph_root, origin=origin)
    revise_hole(ctx.graph_root)

    result = admit.run(ctx)
    assert result.admitted, result.as_dict()
    assert check(result, "witness") == ("pass", "witness-slot-open")
    record = next(c for c in result.checks if c.name == "witness")
    assert record.diagnostic is not None
    assert record.diagnostic.details == {"origin": origin, "supersedes": HOLE}
    assert ctx.data["witness"]["slot"] == "open"
    assert result.as_dict()["checks"][4]["diagnostic"]["code"] == "witness-slot-open"
    assert not witness_was_consulted(toolchain)


def test_the_slot_carve_out_does_not_weaken_step_seven(tmp_path: Path) -> None:
    """Four nodes that carry a sorry witness and are not a hole's revision: each still meets D-4
    step 7 in full and fails it, with the metaprogram consulted."""
    # 1. A fresh hole, no supersedes: the writer's shape submitted as a proposal.
    toolchain = FakeToolchain(witness=STUBBED)
    ctx = admission_of(tmp_path / "fresh", HOLE, toolchain)
    scaffold_hole(ctx.graph_root)
    assert check(admit.run(ctx), "witness") == ("fail", "witness-sorry")
    assert witness_was_consulted(toolchain)

    # 2. An authored node revised with the slot as its witness.
    toolchain = FakeToolchain(witness=STUBBED)
    ctx = admission_of(tmp_path / "authored", REVISION, toolchain)
    scaffold_hole(ctx.graph_root, origin="authored")
    revise_hole(ctx.graph_root)
    assert check(admit.run(ctx), "witness") == ("fail", "witness-sorry")
    assert witness_was_consulted(toolchain)

    # 3. A hole revision whose slot a curator touched, by one character.
    toolchain = FakeToolchain(witness=STUBBED)
    ctx = admission_of(tmp_path / "touched", REVISION, toolchain)
    scaffold_hole(ctx.graph_root)
    revise_hole(ctx.graph_root)
    witness = nodes_dir(ctx.graph_root) / REVISION / "Witness.lean"
    witness.write_text(SLOT.replace(":= by\n  sorry\n", ":= sorry\n"), encoding="utf-8")
    assert check(admit.run(ctx), "witness") == ("fail", "witness-sorry")
    assert witness_was_consulted(toolchain)

    # 4. A revision whose META claims a hole origin, of a node that is not a hole.
    toolchain = FakeToolchain(witness=STUBBED)
    ctx = admission_of(tmp_path / "spoof", REVISION, toolchain)
    scaffold_hole(ctx.graph_root, origin="authored")
    revise_hole(ctx.graph_root)
    meta_path = nodes_dir(ctx.graph_root) / REVISION / "META.yaml"
    meta = yaml.safe_load(meta_path.read_text())
    meta["origin"] = "compiler-derived"
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    assert check(admit.run(ctx), "witness") == ("fail", "witness-sorry")
    assert witness_was_consulted(toolchain)


def test_a_hole_revision_with_a_real_witness_takes_step_seven_in_full(tmp_path: Path) -> None:
    """A curator who has a witness supplies it, and step 7 judges it as it judges any."""
    toolchain = FakeToolchain(witness=GOOD)
    ctx = admission_of(tmp_path / "good", REVISION, toolchain)
    scaffold_hole(ctx.graph_root)
    revise_hole(ctx.graph_root)
    (nodes_dir(ctx.graph_root) / REVISION / "Witness.lean").write_text(REAL, encoding="utf-8")
    result = admit.run(ctx)
    assert result.admitted, result.as_dict()
    assert check(result, "witness") == ("pass", None)
    assert witness_was_consulted(toolchain)

    toolchain = FakeToolchain(witness=witness_result(expected="True", witness="∃ p, p"))
    ctx = admission_of(tmp_path / "wrong", REVISION, toolchain)
    scaffold_hole(ctx.graph_root)
    revise_hole(ctx.graph_root)
    (nodes_dir(ctx.graph_root) / REVISION / "Witness.lean").write_text(REAL, encoding="utf-8")
    assert check(admit.run(ctx), "witness") == ("fail", "witness-type-mismatch")


# --- R14's second half: revise --witness ------------------------------------------------------


def test_revise_takes_a_witness_of_its_own(tmp_path: Path) -> None:
    """R9 widened: the copied witness is the default, a given one replaces it, and the old node's
    file is untouched either way."""
    root = copy_graph(tmp_path)
    scaffold_hole(root)
    revision = revise_hole(root, witness=REAL)
    assert (nodes_dir(root) / revision.new_id / "Witness.lean").read_text() == REAL
    assert (nodes_dir(root) / HOLE / "Witness.lean").read_text() == SLOT


def test_revise_refuses_an_empty_witness_and_writes_nothing(tmp_path: Path) -> None:
    """C7: the scaffold's own refusal, before a byte is written."""
    root = copy_graph(tmp_path)
    scaffold_hole(root)
    request = write_request(root, HOLE)
    before = tree(root)
    with pytest.raises((scaffold.ScaffoldError, curator.CuratorError)):
        curator.revise(
            root, TARGET, HOLE, STATEMENT, request, author=AUTHOR, date=DATE, witness="  \n"
        )
    assert tree(root) == before
    assert not (nodes_dir(root) / REVISION).exists()


def test_revising_a_hole_keeps_it_awaiting_its_witness(tmp_path: Path) -> None:
    """After the revision the products say what they say of any hole: blocked for its witness,
    on the frontier and claimable (F03-T9); the old hole is superseded."""
    root = copy_graph(tmp_path, publish=True)
    scaffold_hole(root)
    declare_root(root)
    revision = revise_hole(root)
    built = products.generate(root, rendered_from=None, commit_time="2026-09-17T12:00:00Z")
    tg = built.targets[0]
    assert tg.statuses[HOLE] == "superseded"
    assert tg.statuses[revision.new_id] == "blocked"
    causes = graphmod.derive_causes(tg.nodes, tg.statuses)
    assert causes[revision.new_id] == graphmod.CAUSE_WITNESS_MISSING
    entries = {e["node_id"]: e for e in json.loads(built.files[Path("frontier.json")])["entries"]}
    assert revision.new_id in entries and entries[revision.new_id]["claimable"] is True


def test_cli_revise_with_a_witness_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Through the entry point: ``--witness`` is read like ``--statement``, and a path that is
    not a file is a usage refusal with nothing written."""
    root = copy_graph(tmp_path, publish=True)
    scaffold_hole(root)
    request = write_request(root, HOLE)
    statement = tmp_path / "S.lean"
    statement.write_text(STATEMENT, encoding="utf-8")
    witness = tmp_path / "W.lean"
    witness.write_text(REAL, encoding="utf-8")
    common = [
        "revise",
        "--graph",
        str(root),
        "--author",
        AUTHOR,
        "--date",
        DATE,
        HOLE,
        "--statement",
        str(statement),
        "--request",
        str(request),
    ]

    code = cli.main([*common, "--witness", str(witness)])
    out = json.loads(capsys.readouterr().out)
    assert code == cli.EXIT_PASS and out["ok"] is True and out["revision"] == REVISION
    assert (nodes_dir(root) / REVISION / "Witness.lean").read_text() == REAL

    root2 = copy_graph(tmp_path / "again", publish=True)
    scaffold_hole(root2)
    request2 = write_request(root2, HOLE)
    try:
        code = cli.main(
            [
                "revise",
                "--graph",
                str(root2),
                "--author",
                AUTHOR,
                "--date",
                DATE,
                HOLE,
                "--statement",
                str(statement),
                "--request",
                str(request2),
                "--witness",
                str(tmp_path / "missing.lean"),
            ]
        )
    except cli.CliError:
        code = 1
    capsys.readouterr()
    assert code != cli.EXIT_PASS
    assert not (nodes_dir(root2) / REVISION).exists()
