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
        # F07-T75: the carried text less its `-- hole:` line, which the real toolchain admits.
        born = (nodes / child / "Witness.lean").read_text(encoding="utf-8")
        assert born == carried.as_witness(witnesses[name]) and "-- hole:" not in born
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


# --- the live shape: a target with ``defs/`` (F07-T53) -------------------------------------------

#: Every live target states its problem over its own ``defs/``; the propositional fixture has
#: none, so nothing above shows that a staged child whose statement imports ``Defs.*`` finds it.
#: The staged build is first on step 7's search path and has no ``Defs``; the node's build, second,
#: has (log, 2026-09-12: keep one fixture with the live shape).
DEFS_NODE = "uses-def"
DEFS_TEXT = (
    "/-! A definition of the target's own, as every live target has. -/\n\n"
    "def OpnProp.two : Nat := 2\n"
)
DEFS_STATEMENT = (
    "import Defs.Two\n"
    f"import Nodes.«{DEFS_NODE}».Context\n\n"
    "theorem OpnProp.uses_def : ∀ n : Nat, n = OpnProp.two → n + n = 4 := by\n  sorry\n"
)
DEFS_NODE_WITNESS = "import Defs.Two\n\ntheorem witness : ∃ n : Nat, n = OpnProp.two := ⟨2, rfl⟩\n"
DEFS_BODY = (
    "  intro n h\n"
    "  have dbl : n + n = 2 * n := sorry\n"
    "  have four : 2 * n = 4 := sorry\n"
    "  exact dbl.trans four\n"
)


def own_node(  # noqa: PLR0917 — the node's facts, each named
    tmp_path: Path,
    tc: Any,
    node_id: str,
    statement: str,
    node_witness: str,
    body: str,
    witnesses: dict[str, str],
    defs: dict[str, str] | None = None,
) -> tuple[RunContext, str]:
    """A node of its own on the fixture target (and ``defs`` beside it), with a skeleton of
    ``body`` and its carried witnesses as a pull request's diff: the context and the assembly."""
    files = {f"{STEM}.{n}{carried.SUFFIX}": text for n, text in enumerate(witnesses.values(), 1)}
    prefix = f"targets/{TARGET}/nodes/{node_id}/attempts/"
    ctx = make_context(
        tmp_path,
        node_id=node_id,
        toolchain=tc,
        changes=[Change("A", prefix + name) for name in (SKELETON, *files)],
    )
    target = ctx.graph_root / "targets" / TARGET
    for name, content in (defs or {}).items():
        (target / "defs").mkdir(exist_ok=True)
        (target / "defs" / name).write_text(content, encoding="utf-8")
    nodes = target / "nodes"
    node = nodes / node_id
    node.mkdir()
    for name in layout.REQUIRED_DIRS:
        (node / name).mkdir()
    (node / "Statement.lean").write_text(statement, encoding="utf-8")
    (node / "Context.lean").write_text("/-! Declared dependencies: none. -/\n", encoding="utf-8")
    (node / "Witness.lean").write_text(node_witness, encoding="utf-8")
    meta = yaml.safe_load((nodes / "and-reassoc" / "META.yaml").read_text(encoding="utf-8"))
    meta.update(
        {
            "id": node_id,
            "deps": [],
            "status": "ready",
            "statement-hash": schemas.content_hash(statement.encode("utf-8")),
        }
    )
    (node / "META.yaml").write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    head, _, _ = statement.partition(":= by\n  sorry")
    text = head + ":= by\n" + body
    (node / "attempts" / SKELETON).write_text(text, encoding="utf-8")
    for name, content in files.items():
        (node / "attempts" / name).write_text(content, encoding="utf-8")
    return ctx, text


def defs_context(tmp_path: Path, tc: Any, witnesses: dict[str, str]) -> tuple[RunContext, str]:
    """A node over the target's own definition, with the skeleton and its carried witnesses."""
    return own_node(
        tmp_path,
        tc,
        DEFS_NODE,
        DEFS_STATEMENT,
        DEFS_NODE_WITNESS,
        DEFS_BODY,
        witnesses,
        defs={"Two.lean": DEFS_TEXT},
    )


def test_a_carried_witness_on_a_target_with_defs_finds_them(
    tmp_path: Path, tc: LocalToolchain
) -> None:
    """The live shape. The hole's statement inherits ``import Defs.Two`` from its parent, the
    carried witness imports it too, and step 7 resolves it from the node's build although the
    staged children's build comes first; the child is born with the witness and admits as
    written. One hole carried, one not: the first is born with its slot, and blocked."""
    ctx, _ = defs_context(tmp_path / "bare", tc, {})
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "pass", verdict.as_dict()
    holes = {h["name"]: h for h in verdict.data["artifact"]["holes"]}
    wanted = holes["four"]["expected_witness"]
    assert wanted == "∃ (n : Nat), n = OpnProp.two", holes
    witnesses = {
        "four": f"-- hole: four\nimport Defs.Two\n\ntheorem witness : {wanted} := ⟨2, rfl⟩\n"
    }
    ctx, text = defs_context(tmp_path / "gate", tc, witnesses)
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "pass", verdict.as_dict()
    assert [w["hole"] for w in verdict.data[carried.DATA_KEY]] == ["four"]
    node = layout.graph_nodes_dir(ctx.graph_root, TARGET) / DEFS_NODE
    merged = postmerge.apply_partial(
        node,
        [Hole.of(h) for h in verdict.data["artifact"]["holes"]],
        partial_text=text,
        pseudonym="tester",
        stamp="20261001T000000Z",
        assembly_path=f"attempts/{SKELETON}",
        witnesses=cli.checked_witnesses(verdict, node),
    )
    slot, born = merged.children
    assert merged.witnessed == (born,)
    statement = (node.parent / born / "Statement.lean").read_text(encoding="utf-8")
    assert statement.startswith(f"import Defs.Two\nimport Nodes.«{born}».Context\n"), statement
    written = (node.parent / born / "Witness.lean").read_text(encoding="utf-8")
    assert written == carried.as_witness(witnesses["four"])  # F07-T75
    admitted = admit_as_written(tc, tmp_path / "admit", ctx.graph_root, born)
    assert witness_check(admitted) == ("pass", None), admitted.as_dict()
    # The derived statuses are the test above's; this fixture has two sinks and no declared root.
    assert not graph.witness_is_stub(node.parent / born)
    assert graph.witness_is_stub(node.parent / slot)


# --- the guide's worked file (F07-T52) -----------------------------------------------------------

GUIDE = Path(__file__).resolve().parents[2] / "gate" / "agents" / "AGENTS.md"
GUIDE_NODE = "divides-twelve"
GUIDE_STATEMENT = (
    f"import Nodes.«{GUIDE_NODE}».Context\n\n"
    "theorem OpnProp.divides_twelve : ∀ n : Nat, 0 < n → n \u2223 12 → n ≤ 12 := by\n  sorry\n"
)
#: ``\\u2223`` is Lean's divides bar, spelled out for the linter (RUF001).
GUIDE_BODY = (
    "  intro n hpos hdvd\n"
    "  have h₁ : n \u2223 24 := sorry\n"  # the one hole
    "  exact Nat.le_of_dvd (by decide) hdvd\n"
)


def test_the_guides_worked_file_is_a_carried_witness(tmp_path: Path, tc: LocalToolchain) -> None:
    """AC47 (log, 2026-09-19: check a worked example with the toolchain before it goes in a
    guide). The file the guide shows under "Carrying the holes' witnesses", byte for byte, is
    carried for a hole ``h₁`` whose statement has the two hypotheses it exhibits, and step 7
    passes it."""
    section = GUIDE.read_text(encoding="utf-8").split("### Carrying the holes' witnesses", 1)[1]
    block = section.split("```lean\n", 1)[1].split("```", 1)[0]
    assert carried.hole_named(block) == "h₁"
    node_witness = block.split("\n", 1)[1].lstrip("\n")  # the same declaration, for the node
    ctx, _ = own_node(
        tmp_path, tc, GUIDE_NODE, GUIDE_STATEMENT, node_witness, GUIDE_BODY, {"h₁": block}
    )
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "pass", verdict.as_dict()
    (checked,) = verdict.data[carried.DATA_KEY]
    assert checked["hole"] == "h₁" and checked["expected"] == "∃ n, 0 < n ∧ n \u2223 12"
    assert checked["witness"] == checked["expected"]


# --- a carried witness sees what its own node will see, and no more (F07-T53) --------------------


@pytest.mark.parametrize("module", ["Context", "Statement", "Witness", "Proof"])
def test_a_carried_witness_cannot_import_the_parents_modules(
    tmp_path: Path, tc: LocalToolchain, module: str
) -> None:
    """A witness proposed alone is checked in its own node's build, where no other node's module
    is. A carried one is checked beside the parent's build, which holds the parent's Statement,
    Context, Witness and the assembly itself as ``Proof``; if it could import one of them it
    would pass here and then fail to elaborate in the node it is written into, a hole born
    ``ready`` that nothing can be checked against. The copying mistake the guide warns of is
    exactly this (the parent's ``import Nodes.«…».Context`` line left in). The staged build is
    first on the search path and has the only ``Nodes`` root Lean will look in, so each is
    refused at step 7, naming the hole."""
    wanted = "∃ (n : Nat), n = OpnProp.two"
    text = (
        "-- hole: four\nimport Defs.Two\n"
        f"import Nodes.«{DEFS_NODE}».{module}\n\n"
        f"theorem witness : {wanted} := ⟨2, rfl⟩\n"
    )
    ctx, _ = defs_context(tmp_path, tc, {"four": text})
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "fail", verdict.as_dict()
    assert verdict.first_failing_step == 7 and verdict.diagnostic is not None, verdict.as_dict()
    assert verdict.diagnostic.code == "witness-elaboration", verdict.as_dict()
    assert verdict.diagnostic.details["hole"] == "four", verdict.as_dict()
    assert carried.DATA_KEY not in verdict.data
