"""F02-T13, lean tier: a partial's assembly cannot answer its own hole extraction.

Until T13 ``opn-artifact-type`` elaborated a partial's assembly in the process that printed the
hole report, and every command in the file took effect there. One that needs no nonce at all is
an ``@[app_unexpander]``: it is a function the contributor wrote, registered by an attribute in
the assembly's environment, and the judge's pretty-printer runs it on every hole's type, so the
assembly chose how its holes were printed (and so which child statements the post-merge job would
write). Now the assembly's olean is added through the kernel into an environment imported only
from modules of record; its constants are there, its attributes and initializers are not, and the
holes are printed by the program alone.

Two kinds of evidence:

* the forging assembly, through steps 1 to 4 on the real toolchain: the holes are the true ones,
  printed with the statement's own notation;
* the compiled form against ``golden/artifact-types.json``, which the elaborating form produced:
  every partial fixture's report is the same, field for field (the "before and after").

They need the real toolchain and the built Lake package; they run in CI.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from harness import GRAPH, TARGET
from test_finding_compiled_judges_lean import forging
from test_partial import ROOT, partial_context

from opn_gate import layout, pipeline
from opn_gate.steps import artifact as art
from opn_gate.steps import default_steps
from opn_gate.toolchain import ArtifactRequest, LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "artifacts"
GOLDEN = Path(__file__).resolve().parent / "golden" / "artifact-types.json"

#: Trailing commands of a forging assembly: an unexpander that prints every conjunction as
#: ``True`` (so a hole ``q ∧ p`` would be reported as ``True``), an ``#eval`` and an ``initialize``
#: that print a forged report naming one hole nobody wrote.
FORGED_REPORT = {
    "ok": True,
    "kind": "partial",
    "decl": "OpnProp.and_swap_reassoc",
    "matches": True,
    "axioms": [],
    "holes": [{"name": "forged", "type": "True", "closed_type": "True", "defeq_goal": False}],
    "unnamed": 0,
    "body_is_hole": False,
}
UNEXPANDER = """

@[app_unexpander And] def forgeAnd : Lean.PrettyPrinter.Unexpander
  | `($_ $_ $_) => `(True)
  | _ => throw ()
"""


def test_a_partial_cannot_answer_its_own_hole_extraction(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    del pinned, lean_pkg
    ctx, stamp = partial_context(tmp_path, toolchain=real_toolchain)  # type: ignore[arg-type]
    assembly = layout.graph_nodes_dir(ctx.graph_root, TARGET) / ROOT / "attempts" / stamp
    assembly.write_text(
        assembly.read_text(encoding="utf-8") + UNEXPANDER + forging(FORGED_REPORT),
        encoding="utf-8",
    )
    verdict = pipeline.run_steps(ctx, [s for s in default_steps() if s.number <= 4])
    assert verdict.first_failing_step is None, verdict.as_dict()
    holes = {h["name"]: h for h in verdict.data["artifact"]["holes"]}
    assert list(holes) == ["right", "left"], holes
    assert holes["right"]["closed_type"] == "∀ (p q r : Prop), (p ∧ q) ∧ r → r"
    assert holes["left"]["type"] == "q ∧ p"
    assert holes["left"]["closed_type"] == "∀ (p q r : Prop), (p ∧ q) ∧ r → q ∧ p"
    assert all(h["closed_roundtrip"] for h in holes.values())
    assert verdict.data["artifact"]["declared"] == "∀ (p q r : Prop), (p ∧ q) ∧ r → r ∧ q ∧ p"


MATCH_BODY = """  intro p q r h
  have m : match (2 : Nat) with | 0 => False | _ + 1 => True := sorry
  exact ⟨h.2, ⟨h.1.2, h.1.1⟩⟩
"""


def test_a_hole_naming_the_assemblys_own_constant_is_no_round_trip(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    """What the replay does not carry: a ``match`` in a hole's type is the assembly's own matcher,
    whose matcher info is an extension entry. Read from the compiled module it prints as the
    constant (``OpnProp.and_swap_reassoc.match_1_1 …``), which reads back in the judge, where the
    constant is, and in no child's environment. The compiled form says so (the hole names one of
    the assembly's own constants), and the partial is refused as before T13, when the hole printed
    as ``match`` and did not read back: ``hole-not-roundtrip``, never a child that cannot
    elaborate. Shown at 4.33.1 in ``engineering/evidence/F02/task-13-audit-2026-10-04.txt``."""
    del pinned, lean_pkg
    ctx, stamp = partial_context(tmp_path, toolchain=real_toolchain)  # type: ignore[arg-type]
    assembly = layout.graph_nodes_dir(ctx.graph_root, TARGET) / ROOT / "attempts" / stamp
    head, _, _ = assembly.read_text(encoding="utf-8").partition(":= by\n")
    assembly.write_text(head + ":= by\n" + MATCH_BODY, encoding="utf-8")
    verdict = pipeline.run_steps(ctx, [s for s in default_steps() if s.number <= 4])
    assert verdict.first_failing_step == 4, verdict.as_dict()
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "hole-not-roundtrip", verdict.diagnostic
    [hole] = ctx.data[art.ARTIFACT_KEY]["holes"]
    assert hole["name"] == "m" and hole["closed_roundtrip"] is False


#: The fixtures with holes, and the kind each is submitted as (``test_artifacts_lean.CASES``).
HOLE_CASES: dict[str, art.Kind] = {
    "Partial": "partial",
    "Reduction": "reduction",
    "Offload": "partial",
    "RestateConclusion": "partial",
    "BareHole": "partial",
}
NODE = "tutorial-and-swap"
STATEMENT_DECL = "OpnProp.and_swap"


def compiled_report(
    root: Path, tc: LocalToolchain, pinned: ResolvedToolchain, stem: str, kind: art.Kind
) -> dict[str, Any]:
    """The fixture compiled as the node's ``Proof`` module and judged by the compiled form, the
    statement compiled from the graph's file into a build of its own (the search path)."""
    here = root / stem
    stmt_src, stmt_build = here / "stmt" / "src", here / "stmt" / "build"
    mod_src, mod_build = here / "modules" / "src", here / "modules" / "build"
    node = layout.graph_nodes_dir(GRAPH, TARGET) / NODE
    for src, name, text in (
        (stmt_src, "Statement.lean", (node / "Statement.lean").read_text(encoding="utf-8")),
        (mod_src, "Proof.lean", (FIXTURES / f"{stem}.lean").read_text(encoding="utf-8")),
    ):
        (src / "Nodes" / NODE).mkdir(parents=True, exist_ok=True)
        (src / "Nodes" / NODE / name).write_text(text, encoding="utf-8")
    statement_module = layout.node_module(NODE, "Statement")
    proof_module = layout.node_module(NODE, "Proof")
    for src, build, module, name in (
        (stmt_src, stmt_build, statement_module, "Statement.lean"),
        (mod_src, mod_build, proof_module, "Proof.lean"),
    ):
        elab = tc.elaborate(pinned, src / "Nodes" / NODE / name, module, build, root=src)
        assert elab.ok, (stem, elab)
    req = ArtifactRequest(
        statement=stmt_src / "Nodes" / NODE / "Statement.lean",
        statement_module=statement_module,
        decl=STATEMENT_DECL,
        artifact=mod_src / "Nodes" / NODE / "Proof.lean",
        artifact_module=proof_module,
        artifact_decl=art.expected_decl(kind, STATEMENT_DECL),
        kind=kind,
        statement_olean=stmt_build / "Nodes" / NODE / "Statement.olean",
        artifact_olean=mod_build / "Nodes" / NODE / "Proof.olean",
        modules=mod_build,
    )
    assert not [a for a in req.args() if a.endswith(".lean")], req.args()
    result = tc.artifact_type(pinned, req, [stmt_build])
    assert result.ok, (stem, result)
    parsed = art.Artifact.of(kind, result.doc)
    return {**parsed.as_dict(), "problems": [d.code for d in art.check(parsed)]}


def test_the_compiled_form_reports_what_the_elaborating_form_did(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    """Every fixture with holes: names, types, closed types, the offload rule's answers, the round
    trip, the expected witness and the verdict, equal to the golden the elaborating form made."""
    del lean_pkg
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    got = {
        stem: compiled_report(tmp_path, real_toolchain, pinned, stem, kind)
        for stem, kind in HOLE_CASES.items()
    }
    assert got == {stem: golden[stem] for stem in HOLE_CASES}
    shutil.rmtree(tmp_path, ignore_errors=True)
