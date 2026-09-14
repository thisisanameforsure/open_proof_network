"""F07-T9..T11: a theorem keeps every proof (R3, R7, R15; AC9, AC22-AC24; D-25 v3.13, F07-Q20).

A later complete proof of a proved node is its own pull request adding
``attempts/<ts>-<pseudonym>-alternate.lean``. It is classified ``alternate``, checked like a proof,
never asked step 9, and merges with ``Proof.lean`` untouched. The machine never judges two proofs
alike: the only duplicate rule is exact bytes (Mike, 2026-09-13).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import samples
from fakes import FakeToolchain
from harness import copy_graph, make_context, node_dir

from opn_gate import attestation, layout, modes, paths, pipeline, products, schemas
from opn_gate import graph as graphmod
from opn_gate.paths import Change
from opn_gate.steps import artifact as art
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import AxiomResult

FIXTURES = Path(__file__).resolve().parent / "fixtures"
GRAPH = FIXTURES / "graphs" / "propositional"
T = "targets/propositional"
PROVED = "tutorial-and-swap"
#: A proved node that is not the tutorial: D-27 keeps the tutorial's proof file open to rehearsal.
OTHER_PROVED = "and-reassoc"
#: The fixture ships this node with a proof too; a test that needs it open removes the file.
UNPROVED = "and-swap-reassoc"


def alternate_path(node: str = PROVED, who: str = "bob", stamp: str = "20260913T120000Z") -> str:
    return f"{T}/nodes/{node}/attempts/{stamp}-{who}-alternate.lean"


@pytest.fixture
def graph(tmp_path: Path) -> Path:
    root = tmp_path / "graph"
    shutil.copytree(GRAPH, root)
    return root


def proof_of(graph: Path, node: str = PROVED) -> str:
    return (graph / T / "nodes" / node / "Proof.lean").read_text(encoding="utf-8")


def another_route(graph: Path, node: str = PROVED) -> str:
    """The node's proof by a different term: same header and signature (F00-R19), new body."""
    original = proof_of(graph, node)
    changed = original.replace("exact ⟨h.2, h.1⟩", "exact And.intro h.2 h.1")
    assert changed != original  # guard: the fixture's proof still has the body this rewrites
    return changed


def add(graph: Path, path: str, text: str) -> Change:
    dest = graph / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return Change("A", path)


def found(graph: Path, *changes: Change) -> list[str]:
    """Every refusal a pull request gets before a sandbox: classification, then ``check``."""
    classification = modes.classify(changes)
    codes = [d.code for d in classification.problems]
    if classification.ok:
        codes += [d.code for d in modes.check(graph, classification)]
    return codes


# --- F07-T9: classification (R3, R7; AC9) --------------------------------------------------------


def test_an_alternate_path_has_its_own_role() -> None:
    """R3: ``-alternate.lean`` under ``attempts/`` is an alternate; any other flat ``.lean`` there
    stays a partial, and nothing nested is either."""
    located = paths.locate(alternate_path())
    assert located is not None and located.role == "alternate"
    assert located.node_id == PROVED
    partial = paths.locate(f"{T}/nodes/{PROVED}/attempts/20260913T120000Z-bob-partial.lean")
    assert partial is not None and partial.role == "partial"
    nested = f"{T}/nodes/{PROVED}/attempts/sub/20260913T120000Z-bob-alternate.lean"
    assert paths.locate(nested) is None


def test_alternate_classification_and_refusals(graph: Path) -> None:
    """AC9: one alternate differing from the proof by a byte is mode ``alternate``, built and
    unreviewed, with nothing to refuse; each of the refusals fires on its own case."""
    one_byte = add(graph, alternate_path(), proof_of(graph) + "\n")
    classification = modes.classify([one_byte])
    assert classification.mode == "alternate"
    assert classification.node_id == PROVED
    assert classification.needs_gate is True
    assert classification.needs_review is False  # D-4 v3.13: step 9 is not asked of an alternate
    assert modes.check(graph, classification) == []

    # Byte-identical to the node's proof: the only duplicate rule there is (F07-Q20).
    same = add(graph, alternate_path(who="carol"), proof_of(graph))
    assert found(graph, same) == ["alternate-duplicate"]

    # More than one alternate in one pull request.
    second = add(graph, alternate_path(who="dave"), another_route(graph))
    assert found(graph, one_byte, second) == ["alternate-multiple"]

    # A merged Proof.lean is never modified; the refusal names where the proof belongs instead.
    replaced = modes.classify([Change("M", f"{T}/nodes/{OTHER_PROVED}/Proof.lean")])
    refusals = modes.check(graph, replaced)
    assert [d.code for d in refusals] == ["proof-replaces-merged"]
    assert f"{OTHER_PROVED}/attempts/<ts>-<pseudonym>-alternate.lean" in refusals[0].message


def test_an_alternate_on_an_unproved_node_is_refused(graph: Path) -> None:
    """R7: with no ``Proof.lean`` there is nothing to be an alternate to; it should be a proof."""
    (graph / T / "nodes" / UNPROVED / "Proof.lean").unlink()
    change = add(graph, alternate_path(node=UNPROVED), "theorem x : True := trivial\n")
    assert found(graph, change) == ["alternate-unproved"]


def test_a_copy_of_an_earlier_alternate_is_a_duplicate_and_a_changed_one_is_not(
    graph: Path,
) -> None:
    """R7: an alternate already recorded counts like the proof; its own new file never does."""
    earlier = another_route(graph)
    attempts = graph / T / "nodes" / PROVED / "attempts"
    (attempts / "20260912T090000Z-alice-alternate.lean").write_text(earlier, encoding="utf-8")
    copy = add(graph, alternate_path(), earlier)
    assert found(graph, copy) == ["alternate-duplicate"]

    (graph / copy.path).unlink()
    changed = add(graph, alternate_path(), earlier.replace("h.2 h.1", "h.right h.left"))
    assert found(graph, changed) == []


def test_an_alternate_rides_with_appends_but_not_with_a_proof_or_a_partial(graph: Path) -> None:
    """R3: appends may accompany an alternate; a Proof.lean or a partial alongside is mixed."""
    alt = alternate_path()
    postmortem = f"{T}/nodes/{PROVED}/attempts/20260913T120000Z-bob.yaml"
    assert modes.classify([Change("A", alt), Change("A", postmortem)]).mode == "alternate"
    for other in (
        f"{T}/nodes/{PROVED}/Proof.lean",
        f"{T}/nodes/{PROVED}/attempts/20260913T120000Z-bob-partial.lean",
    ):
        mixed = modes.classify([Change("A", alt), Change("A", other)])
        assert mixed.mode is None, other
        assert [d.code for d in mixed.problems] == ["mode-mixed"], other


def test_a_first_proof_is_still_a_proof(graph: Path) -> None:
    """Regression guard: adding Proof.lean to an unproved node is the ordinary proof mode."""
    (graph / T / "nodes" / UNPROVED / "Proof.lean").unlink()
    first = modes.classify([Change("A", f"{T}/nodes/{UNPROVED}/Proof.lean")])
    assert first.mode == "proof" and first.needs_review is True


def test_the_tutorial_nodes_proof_stays_open_to_rehearsal(graph: Path) -> None:
    """D-27: every operator proves the tutorial node again, on the git path by replacing its
    Proof.lean, and it earns nothing, so modifying it is still an ordinary proof. Found by the
    guide's own walkthrough, which does exactly that (gate/agents/AGENTS.md)."""
    rehearsal = modes.classify([Change("M", f"{T}/nodes/{PROVED}/Proof.lean")])
    assert rehearsal.mode == "proof"
    assert modes.check(graph, rehearsal) == []


def test_an_unreadable_meta_is_not_taken_for_a_tutorial(graph: Path) -> None:
    """C7: the exemption needs the flag read, so a META that will not parse is refused."""
    (graph / T / "nodes" / PROVED / "META.yaml").write_text("tutorial: [\n", encoding="utf-8")
    rehearsal = modes.classify([Change("M", f"{T}/nodes/{PROVED}/Proof.lean")])
    assert [d.code for d in modes.check(graph, rehearsal)] == ["proof-replaces-merged"]


# --- F07-T10: the pipeline checks the alternate, and the node's proof stays the first (R7, R15) --

NAME = "20260913T120000Z-bob-alternate.lean"
BODY = "exact ⟨h.2, h.1⟩"


def alternate_context(
    tmp_path: Path,
    rewrite: str | None,
    *,
    node: str = PROVED,
    toolchain: FakeToolchain | None = None,
) -> tuple[RunContext, str]:
    """A diff adding one alternate to ``node``, whose text is the node's proof with ``BODY``
    replaced by ``rewrite`` (or, for an unproved node, a stand-in proof)."""
    changes = [Change("A", f"{T}/nodes/{node}/attempts/{NAME}")]
    ctx = make_context(tmp_path, node_id=node, toolchain=toolchain, changes=changes)
    proof = node_dir(ctx) / "Proof.lean"
    original = proof.read_text(encoding="utf-8")
    text = original if rewrite is None else original.replace(BODY, rewrite)
    assert rewrite is None or text != original  # guard: the fixture's proof still has BODY
    (node_dir(ctx) / "attempts" / NAME).write_text(text, encoding="utf-8")
    return ctx, text


def test_the_pipeline_checks_the_alternate(tmp_path: Path) -> None:
    """AC22: the file under ``attempts/`` is what steps 2, 4 and 5 check, not ``Proof.lean``, and
    the attestation's ``artifact_hash`` is the alternate's."""
    ctx, text = alternate_context(tmp_path / "sound", "exact And.intro h.2 h.1")
    canonical = (node_dir(ctx) / "Proof.lean").read_bytes()
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step is None, verdict.as_dict()
    step2 = verdict.steps[1].diagnostic
    assert step2 is not None and step2.code == "alternate-submission"
    assert ctx.data[art.ALTERNATE_KEY]["path"] == f"attempts/{NAME}"
    staged = ctx.workdir / "src" / "Nodes" / PROVED / "Proof.lean"
    assert staged.read_text(encoding="utf-8") == text  # step 4 built the alternate
    assert (node_dir(ctx) / "Proof.lean").read_bytes() == canonical  # and left the proof alone
    doc = attestation.build(ctx, verdict, graph_commit=None)
    assert doc["artifact_hash"] == schemas.content_hash(text.encode("utf-8"))

    # Not the statement, while Proof.lean is: step 2 fails on the alternate (F00-R19).
    wrong, _ = alternate_context(tmp_path / "wrong", "exact h.1")
    statement = node_dir(wrong) / "attempts" / NAME
    statement.write_text(
        statement.read_text(encoding="utf-8").replace("q ∧ p :=", "q :="), encoding="utf-8"
    )
    failed = pipeline.run_steps(wrong)
    assert failed.first_failing_step == 2, failed.as_dict()
    assert failed.diagnostic is not None and failed.diagnostic.code == "proof-not-statement"

    # A sorry in it: step 5, with no partial's allowance for sorryAx.
    sorry_axioms = AxiomResult(ok=True, axioms=frozenset({"propext", "sorryAx"}))
    holey, _ = alternate_context(
        tmp_path / "holey", "exact ⟨h.2, sorry⟩", toolchain=FakeToolchain(axiom_result=sorry_axioms)
    )
    failed = pipeline.run_steps(holey)
    assert failed.first_failing_step == 5, failed.as_dict()

    # A counterexample of a proved statement is not an alternate proof of it.
    refuted, _ = alternate_context(tmp_path / "refuted", None)
    path = node_dir(refuted) / "attempts" / NAME
    path.write_text(
        "theorem OpnProp.and_swap_refuted : ¬ (∀ p q : Prop, p ∧ q → q ∧ p) := by\n  sorry\n",
        encoding="utf-8",
    )
    failed = pipeline.run_steps(refuted)
    assert failed.first_failing_step == 2, failed.as_dict()
    assert failed.diagnostic is not None and failed.diagnostic.code == "alternate-not-proof"


def test_an_alternate_on_an_unproved_node_fails_step_2_not_as_a_partial(tmp_path: Path) -> None:
    """R7: precheck never classifies, so step 2 refuses it too, and never takes it for a partial."""
    changes = [Change("A", f"{T}/nodes/{UNPROVED}/attempts/{NAME}")]
    ctx = make_context(tmp_path, node_id=UNPROVED, changes=changes)
    proof = node_dir(ctx) / "Proof.lean"
    (node_dir(ctx) / "attempts" / NAME).write_text(proof.read_text(encoding="utf-8"), "utf-8")
    proof.unlink()
    failed = pipeline.run_steps(ctx)
    assert failed.first_failing_step == 2, failed.as_dict()
    assert failed.diagnostic is not None and failed.diagnostic.code == "alternate-unproved"
    assert art.PARTIAL_KEY not in ctx.data


def attest(root: Path, n: int, *, merge: str, artifact_hash: str | None) -> None:
    node = layout.load_node(root / T / "nodes" / PROVED, "propositional")
    assert not isinstance(node, list)
    doc = samples.attestation(
        node_id=PROVED,
        statement_hash=node.statement.statement_hash,
        merge_commit=merge,
        graph_commit="1" * 40,
        runner="hosted",
        artifact_hash=artifact_hash,
    )
    (root / "attestations").mkdir(exist_ok=True)
    (root / "attestations" / f"{n:06d}.json").write_bytes(schemas.canonical_json(doc))


def test_canonical_proof_survives_a_lower_numbered_alternate(tmp_path: Path) -> None:
    """AC23: #40 opened first, #41 merged first, #40 then landed as an alternate — so
    ``000040.json`` sorts first. The node's proof is still #41's, the one whose hash is
    ``Proof.lean``'s; an earlier partial with no artifact hash does not take it either."""
    root = copy_graph(tmp_path)
    node = root / T / "nodes" / PROVED
    proof = (node / "Proof.lean").read_bytes()
    alternate = proof.replace(BODY.encode(), b"exact And.intro h.2 h.1")
    (node / "attempts" / NAME).write_bytes(alternate)
    attest(root, 19, merge="c" * 40, artifact_hash=None)
    attest(root, 40, merge="a" * 40, artifact_hash=schemas.content_hash(alternate))
    attest(root, 41, merge="b" * 40, artifact_hash=schemas.content_hash(proof))

    tg = graphmod.load_target(root, "propositional")
    facts = tg.nodes[PROVED]
    assert facts.proof is not None and facts.proof.merge_commit == "b" * 40
    assert facts.proof.attestation == "000041.json"
    assert tg.statuses[PROVED] == "proved"
    rows = {n["node_id"]: n for n in products.graph_doc(tg, "5" * 40)["nodes"]}
    assert rows[PROVED]["proof_commit"] == "b" * 40


def test_a_hand_made_attestation_still_proves_when_nothing_matches_the_proof(
    tmp_path: Path,
) -> None:
    """R15's fallback: an attestation whose hash matches no file (the fixtures' placeholder) is
    still the node's proof, as long as it is not an alternate's."""
    root = copy_graph(tmp_path)
    node = root / T / "nodes" / PROVED
    alternate = (
        (node / "Proof.lean").read_bytes().replace(BODY.encode(), b"exact And.intro h.2 h.1")
    )
    (node / "attempts" / NAME).write_bytes(alternate)
    attest(root, 5, merge="a" * 40, artifact_hash=schemas.content_hash(alternate))
    attest(root, 6, merge="d" * 40, artifact_hash="d" * 64)
    facts = graphmod.load_target(root, "propositional").nodes[PROVED]
    assert facts.proof is not None and facts.proof.merge_commit == "d" * 40
