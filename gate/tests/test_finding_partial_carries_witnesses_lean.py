"""F07-T50 (R23, AC45; D-29 v3.24), lean tier: a partial's carried witnesses through the real
extractor and the real step 7.

The fast tier (``test_finding_partial_carries_witnesses.py``) shows the plumbing over the fake
seam, which cannot see what Lean sees: whether the statement the gate stages for a hole before
the merge elaborates, whether step 7's expected type for it is the one the extractor printed in
the precheck, and whether a file checked there is still a witness of the node the post-merge
job then writes. So the flow a contributor follows is driven here end to end: precheck the
skeleton, copy each hole's ``expected_witness``, carry a witness of that type, and let the
post-merge writer make the children.

Two skeletons. The first has a hole that states an earlier hole as its premise (how a hole
inherits one since F07-T48) and two holes each in its own bullet of a ``refine`` (scoped holes,
closed over the statement's binders alone). The second is F07-T44's: an ``obtain`` whose fields
the assembly proved, so the expected types are narrowed (``meta/v5``).

Lean core only, like the rest of the propositional fixture.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from harness import TARGET, copy_graph, make_context
from test_finding_hole_roundtrip_lean import ROOT, SKELETON
from test_finding_witness_proved_haves_lean import BODY as NARROWED_BODY
from test_finding_witness_proved_haves_lean import (
    NARROW_FIRST,
    NARROW_SECOND,
    PROOF_NARROW_FIRST,
    PROOF_NARROW_SECOND,
    PROVED,
    witness_check,
)

from opn_gate import admit, carried, cli, config, graph, layout, pipeline, postmerge, schemas
from opn_gate.paths import Change, Claim
from opn_gate.steps.artifact import Hole
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

STEM = SKELETON[: -len(".lean")]
#: ``second`` states ``first`` as its premise; ``third`` and ``fourth`` each sit in their own
#: bullet, after both, and name neither.
BODY = (
    "  intro p q r h\n"
    "  have first : q ∧ p := sorry\n"
    "  have second : q ∧ p → r ∧ q := sorry\n"
    "  refine ⟨?_, ?_⟩\n"
    "  · have third : r := sorry\n"
    "    exact third\n"
    "  · have fourth : p ∧ q := sorry\n"
    "    exact ⟨fourth.2, fourth.1⟩\n"
)
NAMES = ("first", "second", "third", "fourth")
#: The statement's own hypothesis, over its three variables: what a hole that inherits nothing
#: asks a witness for.
OWN = "∃ (p : Prop), ∃ (q : Prop), ∃ (r : Prop), (p ∧ q) ∧ r"
#: ``second`` also asks for its premise, the earlier hole's conclusion.
INHERITS = "∃ (p : Prop), ∃ (q : Prop), ∃ (r : Prop), ((p ∧ q) ∧ r) ∧ q ∧ p"
#: The same two types as step 7 prints them (``ppExpr``'s defaults; the extractor prints the
#: form above so that it reads back, F07-R19). Read from the first run, not assumed.
OWN_AT_STEP_7 = "∃ p q r, (p ∧ q) ∧ r"
INHERITS_AT_STEP_7 = "∃ p q r, ((p ∧ q) ∧ r) ∧ q ∧ p"
AT_STEP_7 = {OWN: OWN_AT_STEP_7, INHERITS: INHERITS_AT_STEP_7}
PROOF_OWN = "⟨True, True, True, ⟨trivial, trivial⟩, trivial⟩"
PROOF_INHERITS = "⟨True, True, True, ⟨⟨trivial, trivial⟩, trivial⟩, trivial, trivial⟩"
PROOFS = {"first": PROOF_OWN, "second": PROOF_INHERITS, "third": PROOF_OWN, "fourth": PROOF_OWN}


def witness_file(hole: str, wtype: str, proof: str, preamble: str = "") -> str:
    return f"-- hole: {hole}\n\n{preamble}theorem witness : {wtype} :=\n  {proof}\n"


def prepare(
    tmp_path: Path, tc: Any, body: str, witnesses: dict[str, str]
) -> tuple[RunContext, str]:
    """The skeleton and its carried witnesses (hole name -> file text) on the unproved root, as
    a pull request's diff would present them: the context, and the assembly's text."""
    files = {f"{STEM}.{n}{carried.SUFFIX}": text for n, text in enumerate(witnesses.values(), 1)}
    prefix = f"targets/{TARGET}/nodes/{ROOT}/attempts/"
    ctx = make_context(
        tmp_path,
        node_id=ROOT,
        toolchain=tc,
        changes=[Change("A", prefix + name) for name in (SKELETON, *files)],
    )
    node = layout.graph_nodes_dir(ctx.graph_root, TARGET) / ROOT
    (node / "Proof.lean").unlink(missing_ok=True)
    statement = (node / "Statement.lean").read_text(encoding="utf-8")
    head, _, _ = statement.partition(":= by\n  sorry")
    text = head + ":= by\n" + body
    (node / "attempts").mkdir(exist_ok=True)
    (node / "attempts" / SKELETON).write_text(text, encoding="utf-8")
    for name, content in files.items():
        (node / "attempts" / name).write_text(content, encoding="utf-8")
    return ctx, text


def submit(
    tmp_path: Path, tc: LocalToolchain, body: str, witnesses: dict[str, str]
) -> tuple[RunContext, pipeline.Verdict, str]:
    """``prepare``, then the pipeline."""
    ctx, text = prepare(tmp_path, tc, body, witnesses)
    return ctx, pipeline.run_submission(ctx), text


def expected_types(tmp_path: Path, tc: LocalToolchain, body: str) -> dict[str, dict[str, Any]]:
    """What a precheck of the bare skeleton tells its author: each hole's report, by name."""
    _ctx, verdict, _ = submit(tmp_path, tc, body, {})
    assert verdict.verdict == "pass", verdict.as_dict()
    return {h["name"]: h for h in verdict.data["artifact"]["holes"]}


def admit_as_written(
    tc: LocalToolchain, tmp: Path, graph_root: Path, child: str
) -> admit.Admission:
    """Admission over the child exactly as the post-merge job left it: nothing rewritten."""
    root = copy_graph(tmp, graph_root)
    spec_path = layout.gate_spec_path(root, TARGET)
    ctx = RunContext(
        graph_root=root,
        claim=Claim(TARGET, child),
        spec=schemas.load_json(spec_path, "gate-spec/v1"),
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=None,
        workdir=tmp / "work",
        toolchain=tc,
        settings=config.load({}),
    )
    return admit.run(ctx)


@pytest.fixture(scope="module")
def tc(real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path) -> LocalToolchain:
    del pinned, lean_pkg  # resolved and built by the fixtures; the seam finds both itself
    return real_toolchain


@pytest.fixture(scope="module")
def reported(
    tmp_path_factory: pytest.TempPathFactory, tc: LocalToolchain
) -> dict[str, dict[str, Any]]:
    return expected_types(tmp_path_factory.mktemp("precheck"), tc, BODY)


def test_the_precheck_states_each_holes_witness_type(reported: dict[str, dict[str, Any]]) -> None:
    """The premise of the whole flow, read from the toolchain: the hole that states an earlier
    hole as its premise asks for it; the scoped holes, after both, inherit neither."""
    assert tuple(reported) == NAMES
    assert reported["first"]["expected_witness"] == OWN
    assert reported["second"]["expected_witness"] == INHERITS
    assert reported["third"]["expected_witness"] == OWN
    assert reported["fourth"]["expected_witness"] == OWN
    assert reported["third"]["closed_type"] == "∀ (p q r : Prop), (p ∧ q) ∧ r → r"
    assert all(h["proved_binders"] == [] for h in reported.values())


def test_a_skeleton_carrying_every_witness_leaves_every_hole_ready(
    tmp_path: Path, tc: LocalToolchain, reported: dict[str, dict[str, Any]]
) -> None:
    """AC45: witnesses of the types the precheck printed pass step 7 before the merge, against
    the statements the writer then writes; the children are born with them, are not stubs, pass
    admission's own step 7 as written and derive ``ready``."""
    witnesses = {
        name: witness_file(name, reported[name]["expected_witness"], PROOFS[name]) for name in NAMES
    }
    ctx, verdict, text = submit(tmp_path / "gate", tc, BODY, witnesses)
    assert verdict.verdict == "pass", verdict.as_dict()
    step7 = next(s for s in verdict.steps if s.step == 7)
    assert step7.diagnostic is not None and step7.diagnostic.code == "hole-witnesses"
    checked = verdict.data[carried.DATA_KEY]
    assert [w["hole"] for w in checked] == list(NAMES)
    # Step 7 computed, for the staged child, the type the extractor had printed for the hole
    # (each in its own printing), and found the carried witness to be of it.
    for w in checked:
        assert w["expected"] == AT_STEP_7[reported[w["hole"]]["expected_witness"]] == w["witness"]
        assert w["axioms"] == []

    node = layout.graph_nodes_dir(ctx.graph_root, TARGET) / ROOT
    merged = postmerge.apply_partial(
        node,
        [Hole.of(h) for h in verdict.data["artifact"]["holes"]],
        partial_text=text,
        pseudonym="tester",
        stamp="20261001T000000Z",
        assembly_path=f"attempts/{SKELETON}",
        witnesses=cli.checked_witnesses(verdict, node),
    )
    children = tuple(f"{ROOT}--h{i}" for i in range(1, 5))
    assert merged.children == children == merged.witnessed
    nodes = node.parent
    staged = ctx.workdir / "holes" / "src" / "Nodes"
    for child, name in zip(children, NAMES, strict=True):
        # What was checked is what was written, statement and witness, byte for byte.
        for file in ("Statement.lean", "Witness.lean", "Context.lean"):
            assert (nodes / child / file).read_bytes() == (staged / child / file).read_bytes()
        assert (nodes / child / "Witness.lean").read_text(encoding="utf-8") == witnesses[name]
        assert not graph.witness_is_stub(nodes / child)
        admitted = admit_as_written(tc, tmp_path / f"admit-{name}", ctx.graph_root, child)
        assert witness_check(admitted) == ("pass", None), admitted.as_dict()
    tg = graph.load_target(ctx.graph_root, TARGET)
    assert [tg.statuses[c] for c in children] == ["ready"] * 4


def test_a_carried_witness_of_the_wrong_type_refuses_the_partial(
    tmp_path: Path, tc: LocalToolchain, reported: dict[str, dict[str, Any]]
) -> None:
    """AC45: ``second`` carried with the type of a hole that inherits nothing — its premise left
    out — is step 7's ``witness-type-mismatch``, naming the hole and both types."""
    witnesses = {
        "first": witness_file("first", OWN, PROOF_OWN),
        "second": witness_file("second", OWN, PROOF_OWN),
    }
    ctx, verdict, _ = submit(tmp_path, tc, BODY, witnesses)
    assert verdict.verdict == "fail" and verdict.first_failing_step == 7, verdict.as_dict()
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "witness-type-mismatch"
    assert verdict.diagnostic.details["hole"] == "second"
    assert verdict.diagnostic.details["path"] == f"attempts/{STEM}.2{carried.SUFFIX}"
    assert reported["second"]["expected_witness"] == INHERITS
    assert verdict.diagnostic.details["expected"] == INHERITS_AT_STEP_7
    assert verdict.diagnostic.details["witness"] == OWN_AT_STEP_7
    assert carried.DATA_KEY not in ctx.data


def test_a_carried_witness_resting_on_an_axiom_refuses_the_partial(
    tmp_path: Path, tc: LocalToolchain
) -> None:
    """AC45: the allowlist is step 7's for a carried witness as for a node's own."""
    cheat = witness_file("third", OWN, "Cheat.it", preamble=f"axiom Cheat.it : {OWN}\n\n")
    _ctx, verdict, _ = submit(tmp_path, tc, BODY, {"third": cheat})
    assert verdict.first_failing_step == 7, verdict.as_dict()
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "witness-axiom"
    assert verdict.diagnostic.details["hole"] == "third"
    assert verdict.diagnostic.details["axioms"] == ["Cheat.it"]


def test_a_carried_witness_that_does_not_elaborate_refuses_the_partial(
    tmp_path: Path, tc: LocalToolchain
) -> None:
    broken = witness_file("fourth", OWN, "⟨True, True, trivial⟩")
    _ctx, verdict, _ = submit(tmp_path, tc, BODY, {"fourth": broken})
    assert verdict.first_failing_step == 7, verdict.as_dict()
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "witness-elaboration"
    assert verdict.diagnostic.details["hole"] == "fourth"


def test_a_narrowed_witness_is_carried_as_it_would_be_proposed(
    tmp_path: Path, tc: LocalToolchain
) -> None:
    """F07-T44 with R23: where the assembly proved some of a hole's binders, the carried witness
    is held to the narrowed type before the merge, and the child is born ``meta/v5`` with the
    record that makes admission ask the same of it afterwards."""
    witnesses = {
        "first": witness_file("first", NARROW_FIRST, PROOF_NARROW_FIRST),
        "second": witness_file("second", NARROW_SECOND, PROOF_NARROW_SECOND),
    }
    ctx, verdict, text = submit(tmp_path / "gate", tc, NARROWED_BODY, witnesses)
    assert verdict.verdict == "pass", verdict.as_dict()
    checked = {w["hole"]: w for w in verdict.data[carried.DATA_KEY]}
    # NARROW_FIRST and NARROW_SECOND, as step 7 prints them: asked with the hole's
    # ``proved_binders``, so ``p`` and ``q`` are given under the arrow and not exhibited.
    assert checked["first"]["expected"] == "∃ p q r, (p ∧ q) ∧ r" == checked["first"]["witness"]
    assert checked["second"]["expected"] == "∃ p q r, ((p ∧ q) ∧ r) ∧ (p → q → q ∧ p)"
    assert checked["second"]["witness"] == checked["second"]["expected"]
    holes = {h["name"]: h for h in verdict.data["artifact"]["holes"]}
    assert holes["first"]["expected_witness"] == NARROW_FIRST
    assert holes["second"]["expected_witness"] == NARROW_SECOND
    node = layout.graph_nodes_dir(ctx.graph_root, TARGET) / ROOT
    merged = postmerge.apply_partial(
        node,
        [Hole.of(h) for h in verdict.data["artifact"]["holes"]],
        partial_text=text,
        pseudonym="tester",
        stamp="20261001T000000Z",
        assembly_path=f"attempts/{SKELETON}",
        witnesses=cli.checked_witnesses(verdict, node),
    )
    assert merged.witnessed == (f"{ROOT}--h1", f"{ROOT}--h2")
    for child in merged.children:
        meta = yaml.safe_load((node.parent / child / "META.yaml").read_text(encoding="utf-8"))
        assert meta["schema"] == "meta/v5" and meta["proved_binders"] == PROVED, meta
        admitted = admit_as_written(tc, tmp_path / f"admit-{child}", ctx.graph_root, child)
        assert witness_check(admitted) == ("pass", None), admitted.as_dict()
