"""F28-T11 (bug B5, the 2026-11-19 agent run; D-12 v3.42, D-25 v3.13): a node proved by closure
takes alternates.

Live: the last hole merged (graph #1508), the closure sweep proved the parent by
``nodes/<id>/closure.json`` with no ``Proof.lean``, and the parent's assembly, submitted as its
``Proof.lean`` (#1519), was moved by the service to ``attempts/<ts>-<pseudonym>-alternate.lean``.
The gate then refused it ``alternate-unproved`` ("has no merged Proof.lean, so there is nothing
for this to be an alternate to"), because both its checks looked for the file alone.

The owner's ruling: a node proved by closure counts as proved, and a direct proof of it merges as
that node's alternate. A closure that refutes the node, or no record at all, is still refused.
"""

from __future__ import annotations

from pathlib import Path

import samples
from harness import TARGET, copy_graph, make_context, node_dir

from opn_gate import closure, layout, modes, pipeline, products, schemas
from opn_gate import graph as graphmod
from opn_gate.diagnostic import Diagnostic
from opn_gate.paths import Change
from opn_gate.steps import artifact as art

T = f"targets/{TARGET}"
NODE = "and-reassoc"  # not the tutorial, not the root; its only input below is proved
NAME = "20261119T120000Z-bob-alternate.lean"
ASSEMBLY = (
    f"import Nodes.«{NODE}».Context\n\n"
    "theorem OpnProp.and_reassoc : ∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ (q ∧ r) := by\n"
    "  intro p q r h\n  have hole : p ∧ (q ∧ r) := sorry\n  exact hole\n"
)


def close(node: Path, *, verdict: str = closure.VERDICT_PROVED) -> None:
    """Replace the node's ``Proof.lean`` by a closure record over a merged assembly, as the
    post-merge sweep leaves a node it closed (F28-T8)."""
    statement = layout.parse_statement((node / "Statement.lean").read_text(encoding="utf-8"))
    assert not isinstance(statement, Diagnostic)
    (node / "Proof.lean").unlink()
    (node / "attempts").mkdir(exist_ok=True)
    (node / "attempts" / "20261118T120000Z-alice-partial.lean").write_text(ASSEMBLY, "utf-8")
    record = closure.build(
        target_id=TARGET, node_id=NODE, statement_hash=statement.statement_hash,
        link=closure.Link("route", f"{NODE}@1", ("tutorial-and-swap",)),
        source_path="attempts/20261118T120000Z-alice-partial.lean", source_text=None,
        source_hash="b" * 64, axioms=[], graph_commit="c" * 40, network_commit=None,
        lean_toolchain="leanprover/lean4:v4.33.1", mathlib_sha=None,
        timestamp="2026-11-19T12:00:00Z", verdict=verdict,
    )  # fmt: skip
    closure.write(node, record)


def direct_proof() -> str:
    return (
        "theorem OpnProp.and_reassoc : ∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ (q ∧ r) := by\n"
        "  intro p q r h\n  exact ⟨h.1.1, h.1.2, h.2⟩\n"
    )


def refusals(root: Path, path: str) -> list[str]:
    classification = modes.classify([Change("A", path)])
    assert classification.ok, classification.problems
    return [d.code for d in modes.check(root, classification)]


# --- 1. the gate's mode check and step 2 --------------------------------------------------------


def test_an_alternate_on_a_node_proved_by_closure_is_accepted(tmp_path: Path) -> None:
    """The live refusal of #1519: no ``Proof.lean``, a proving closure record. Accepted, and the
    duplicate check does not trip over the missing file."""
    root = copy_graph(tmp_path)
    node = layout.graph_nodes_dir(root, TARGET) / NODE
    close(node)
    path = f"{T}/nodes/{NODE}/attempts/{NAME}"
    (root / path).write_text(direct_proof(), encoding="utf-8")
    assert refusals(root, path) == []


def test_a_copy_of_an_alternate_already_on_a_closure_node_is_a_duplicate(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    node = layout.graph_nodes_dir(root, TARGET) / NODE
    close(node)
    (node / "attempts" / "20261119T110000Z-carol-alternate.lean").write_text(
        direct_proof(), "utf-8"
    )
    path = f"{T}/nodes/{NODE}/attempts/{NAME}"
    (root / path).write_text(direct_proof(), encoding="utf-8")
    assert refusals(root, path) == ["alternate-duplicate"]


def test_a_refuting_closure_or_none_is_still_nothing_to_be_an_alternate_to(
    tmp_path: Path,
) -> None:
    """A refuted node has no proof to stand beside (D-12 v3.46): the refusal stands, as it does
    with neither file."""
    refuted = copy_graph(tmp_path / "refuted")
    close(layout.graph_nodes_dir(refuted, TARGET) / NODE, verdict=closure.VERDICT_REFUTED)
    path = f"{T}/nodes/{NODE}/attempts/{NAME}"
    (refuted / path).write_text(direct_proof(), encoding="utf-8")
    assert refusals(refuted, path) == ["alternate-unproved"]

    bare = copy_graph(tmp_path / "bare")
    (layout.graph_nodes_dir(bare, TARGET) / NODE / "Proof.lean").unlink()
    (bare / path).parent.mkdir(exist_ok=True)
    (bare / path).write_text(direct_proof(), encoding="utf-8")
    assert refusals(bare, path) == ["alternate-unproved"]


def test_step_2_takes_an_alternate_on_a_node_proved_by_closure(tmp_path: Path) -> None:
    """Precheck never classifies, so step 2 asks the same question; it is the pipeline's
    ``alternate-submission``, with the file recorded for step 4 to stage."""
    ctx = make_context(
        tmp_path, node_id=NODE, changes=[Change("A", f"{T}/nodes/{NODE}/attempts/{NAME}")]
    )
    close(node_dir(ctx))
    (node_dir(ctx) / "attempts" / NAME).write_text(direct_proof(), encoding="utf-8")
    verdict = pipeline.run_steps(ctx)
    step2 = verdict.steps[1].diagnostic
    assert step2 is not None and step2.code == "alternate-submission", verdict.as_dict()
    assert ctx.data[art.ALTERNATE_KEY]["path"] == f"attempts/{NAME}"


# --- 2. the products: the alternate is one of the node's proofs ---------------------------------


def attest(
    root: Path,
    n: int,
    *,
    statement_hash: str,
    artifact_hash: str | None,
    node_id: str = NODE,
    footprint: list[str] | None = None,
) -> None:
    doc = samples.attestation(
        footprint=None if footprint is None else {"nodes": footprint},
        node_id=node_id,
        statement_hash=statement_hash,
        merge_commit=f"{n:040d}",
        graph_commit="1" * 40,
        runner="hosted",
        artifact_hash=artifact_hash,
    )
    (root / "attestations").mkdir(exist_ok=True)
    (root / "attestations" / f"{n:06d}.json").write_bytes(schemas.canonical_json(doc))


def test_a_merged_alternate_on_a_closure_node_is_listed_in_its_proofs(tmp_path: Path) -> None:
    """``graph.json``'s ``proofs[]`` lists every merged proof of a node, its alternates with
    them (D-25 v3.13); a closure node's alternate is one. What the closure rests on is the
    closure's, not the alternate's: ``rests_on`` is unchanged by its arrival."""
    root = copy_graph(tmp_path)
    node = layout.graph_nodes_dir(root, TARGET) / NODE
    close(node)
    loaded = layout.load_node(node, TARGET)
    assert not isinstance(loaded, list)
    sh = loaded.statement.statement_hash
    tutorial = layout.load_node(layout.graph_nodes_dir(root, TARGET) / "tutorial-and-swap", TARGET)
    assert not isinstance(tutorial, list)
    attest(  # the closure's one input, proved
        root, 9, statement_hash=tutorial.statement.statement_hash, artifact_hash=None,
        node_id="tutorial-and-swap",
    )  # fmt: skip
    attest(root, 10, statement_hash=sh, artifact_hash=None)  # the partial's merge
    before = graphmod.load_target(root, TARGET)
    assert before.statuses[NODE] == "proved"
    assert before.nodes[NODE].proofs == ()

    text = direct_proof().encode("utf-8")
    (node / "attempts" / NAME).write_bytes(text)
    # the alternate's term was measured, and uses a node the closure does not rest on
    attest(
        root, 11, statement_hash=sh, artifact_hash=schemas.content_hash(text),
        footprint=["tutorial-and-swap"],
    )  # fmt: skip
    after = graphmod.load_target(root, TARGET)
    assert after.statuses[NODE] == "proved"
    proofs = after.nodes[NODE].proofs
    assert [(p.kind, p.path, p.attestation) for p in proofs] == [
        ("alternate", f"attempts/{NAME}", "000011.json")
    ]
    assert proofs[0].used == ("tutorial-and-swap",)
    assert after.nodes[NODE].rests_on == before.nodes[NODE].rests_on
    # What the service reads off the row (F28-T11's api half): the row is proved, carries its
    # closure, a proof commit (the partial's merge), and the alternate as its only proof.
    row = next(n for n in products.graph_doc(after, "5" * 40)["nodes"] if n["node_id"] == NODE)
    assert row["status"] == "proved" and row["closure"] is not None
    assert row["proof_commit"] == f"{10:040d}"
    assert [p["kind"] for p in row["proofs"]] == ["alternate"]
