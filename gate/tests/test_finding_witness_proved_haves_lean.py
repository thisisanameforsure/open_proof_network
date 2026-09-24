# ruff: noqa: RUF001, RUF003 — the fixtures are Lean source, with its logical connectives
"""F07-T44 (D-29 v3.22), lean tier: a hole's witness exhibits only what the decomposition left
unproved.

A hole is closed over every binder in scope where it sits (F11-Q22), so step 7 used to hold its
witness to the conjunction of all of them — including facts the skeleton itself had proved, which a
contributor then had to prove again inside ``Witness.lean``. The owner's rule (decisions v3.22):
the witness exhibits the hypotheses the hole inherited from the statement and from other holes;
those the assembly proved are discharged by the gate from the merged assembly, which step 4 has
kernel-checked. The hole's *statement* does not change, and a hole written before the rule (no
record) keeps the expected type it was written with.

Which binders count as proved was read from the toolchain, not from memory (Lean 4.33.1, probe in
``engineering/evidence/F07/task-44.txt``): a proved ``have`` elaborates to a ``let`` that the
closed type drops when nothing uses it, so it was never a hypothesis at all; what *does* reach a
hole's statement is a binder the assembly introduced by destructuring a proved fact —
``obtain ⟨hp, hq⟩ := pq`` is ``And.casesOn pq (fun hp hq => …)`` — and those are what the
extractor now marks. The fixture has both, one hole after them, and one hole after that hole.

Lean core only, like the rest of the propositional fixture.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml
from harness import TARGET, copy_graph, make_context
from test_finding_hole_roundtrip_lean import ROOT, SKELETON

from opn_api import checks
from opn_gate import admit, config, layout, pipeline, postmerge, schemas
from opn_gate.paths import Change, Claim
from opn_gate.steps.artifact import Hole
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

#: One proved ``have`` (a let, absent from every closed type), one destructuring of it (two
#: binders the assembly proved), then a hole, then a hole after that hole.
BODY = (
    "  intro p q r h\n"
    "  have pq : p ∧ q := h.1\n"
    "  obtain ⟨hp, hq⟩ := pq\n"
    "  have first : q ∧ p := sorry\n"
    "  have second : r ∧ q := sorry\n"
    "  exact ⟨second.1, first⟩\n"
)
FIRST, SECOND = f"{ROOT}--h1", f"{ROOT}--h2"
#: The statements as the extractor printed them before the rule; the rule must not move them.
CLOSED_FIRST = "∀ (p q r : Prop), (p ∧ q) ∧ r → p → q → q ∧ p"
CLOSED_SECOND = "∀ (p q r : Prop), (p ∧ q) ∧ r → p → q → q ∧ p → r ∧ q"
#: ``hp`` and ``hq``: binders 4 and 5 of both closed types (p q r h hp hq …).
PROVED = [4, 5]
#: Today's expected types: every hypothesis, the proved ones included.
FULL_FIRST = "∃ (p : Prop), ∃ (q : Prop), ∃ (r : Prop), ((p ∧ q) ∧ r) ∧ p ∧ q"
FULL_SECOND = "∃ (p : Prop), ∃ (q : Prop), ∃ (r : Prop), ((p ∧ q) ∧ r) ∧ p ∧ q ∧ q ∧ p"
#: The rule's: the statement's own hypothesis, and ``first`` given what the assembly proved.
NARROW_FIRST = "∃ (p : Prop), ∃ (q : Prop), ∃ (r : Prop), (p ∧ q) ∧ r"
NARROW_SECOND = "∃ (p : Prop), ∃ (q : Prop), ∃ (r : Prop), ((p ∧ q) ∧ r) ∧ (p → q → q ∧ p)"
#: Witnesses, each of the type beside it.
PROOF_NARROW_FIRST = "⟨True, True, True, ⟨trivial, trivial⟩, trivial⟩"
PROOF_FULL_FIRST = "⟨True, True, True, ⟨⟨trivial, trivial⟩, trivial⟩, trivial, trivial⟩"
PROOF_NARROW_SECOND = (
    "⟨True, True, True, ⟨⟨trivial, trivial⟩, trivial⟩, fun _ _ => ⟨trivial, trivial⟩⟩"
)


def decompose(
    tmp_path: Path,
    tc: LocalToolchain,
    body: str = BODY,
    children: tuple[str, ...] = (FIRST, SECOND),
) -> tuple[Path, list[dict[str, object]], dict[str, object]]:
    """The skeleton through the real extractor, then the post-merge job's children in the tree:
    the graph root, the holes as step 4 reported them, and the verdict."""
    ctx = make_context(
        tmp_path / "skeleton",
        node_id=ROOT,
        toolchain=tc,
        changes=[Change("A", f"targets/{TARGET}/nodes/{ROOT}/attempts/{SKELETON}")],
    )
    node = layout.graph_nodes_dir(ctx.graph_root, TARGET) / ROOT
    (node / "Proof.lean").unlink(missing_ok=True)
    statement = (node / "Statement.lean").read_text(encoding="utf-8")
    head, _, _ = statement.partition(":= by\n  sorry")
    text = head + ":= by\n" + body
    (node / "attempts").mkdir(exist_ok=True)
    (node / "attempts" / SKELETON).write_text(text, encoding="utf-8")
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "pass", verdict.as_dict()
    holes = verdict.data["artifact"]["holes"]
    merged = postmerge.apply_partial(
        node,
        [Hole.of(h) for h in holes],
        partial_text=text,
        pseudonym="tester",
        stamp="20260924T000000Z",
        assembly_path=f"attempts/{SKELETON}",
    )
    assert merged.children == children
    return ctx.graph_root, holes, verdict.as_dict()


def with_witness(
    tc: LocalToolchain, tmp: Path, graph: Path, child: str, witness: tuple[str, str]
) -> admit.Admission:
    """The child with ``witness`` (a type and its proof) in its slot, through admission's step 7."""
    wtype, proof = witness
    root = copy_graph(tmp, graph)
    node = layout.graph_nodes_dir(root, TARGET) / child
    header = [
        line
        for line in (node / "Statement.lean").read_text(encoding="utf-8").splitlines()
        if line.startswith("import ")
    ]
    text = "\n".join(header) + f"\n\ntheorem witness : {wtype} := {proof}\n"
    (node / "Witness.lean").write_text(text, encoding="utf-8")
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


def witness_check(admission: admit.Admission) -> tuple[str, str | None]:
    (record,) = [c for c in admission.checks if c.name == "witness"]
    return record.result, record.diagnostic.code if record.diagnostic else None


Decomposed = tuple[Path, list[dict[str, object]], dict[str, object]]


@pytest.fixture(scope="module")
def decomposed(
    tmp_path_factory: pytest.TempPathFactory,
    real_toolchain: LocalToolchain,
    pinned: ResolvedToolchain,
    lean_pkg: Path,
) -> Decomposed:
    """One real decomposition for the module; every test copies the tree before it writes."""
    del pinned, lean_pkg  # resolved and built by the fixtures; the seam finds both itself
    return decompose(tmp_path_factory.mktemp("decomposed"), real_toolchain)


def test_a_hole_after_a_proved_have_asks_only_for_the_unproved_hypotheses(
    tmp_path: Path, real_toolchain: LocalToolchain, decomposed: Decomposed
) -> None:
    graph, holes, _ = decomposed
    first = holes[0]
    assert first["name"] == "first"
    assert first["proved_binders"] == PROVED, first
    assert first["expected_witness"] == NARROW_FIRST, first
    meta = yaml.safe_load(
        (layout.graph_nodes_dir(graph, TARGET) / FIRST / "META.yaml").read_text(encoding="utf-8")
    )
    assert meta["proved_binders"] == PROVED and meta["schema"] == "meta/v5", meta
    slot = (layout.graph_nodes_dir(graph, TARGET) / FIRST / "Witness.lean").read_text("utf-8")
    assert f"theorem witness : {NARROW_FIRST} := by" in slot
    # Step 7 on the child takes the narrowed witness: p and q are the assembly's to discharge.
    admitted = with_witness(
        real_toolchain, tmp_path / "narrow", graph, FIRST, (NARROW_FIRST, PROOF_NARROW_FIRST)
    )
    assert witness_check(admitted) == ("pass", None), admitted.as_dict()
    # A witness of the full type is still a witness (it exhibits more than it must).
    full = with_witness(
        real_toolchain, tmp_path / "full", graph, FIRST, (FULL_FIRST, PROOF_FULL_FIRST)
    )
    assert witness_check(full) == ("pass", None), full.as_dict()


def test_a_hole_after_a_hole_still_asks_for_that_hole(
    tmp_path: Path, real_toolchain: LocalToolchain, decomposed: Decomposed
) -> None:
    graph, holes, _ = decomposed
    second = holes[1]
    assert second["name"] == "second"
    assert second["proved_binders"] == PROVED, second
    # ``first`` is a hole, so it stays an obligation — given the facts the assembly proved.
    assert second["expected_witness"] == NARROW_SECOND, second
    admitted = with_witness(
        real_toolchain, tmp_path / "ok", graph, SECOND, (NARROW_SECOND, PROOF_NARROW_SECOND)
    )
    assert witness_check(admitted) == ("pass", None), admitted.as_dict()
    # Leaving the earlier hole out is refused: it is not the assembly's to discharge.
    short = with_witness(
        real_toolchain, tmp_path / "short", graph, SECOND, (NARROW_FIRST, PROOF_NARROW_FIRST)
    )
    assert witness_check(short) == ("fail", "witness-type-mismatch"), short.as_dict()


def test_the_statement_text_and_hash_are_unchanged(
    decomposed: Decomposed,
) -> None:
    graph, holes, _ = decomposed
    assert [h["closed_type"] for h in holes] == [CLOSED_FIRST, CLOSED_SECOND]
    assert all(h["closed_roundtrip"] is True for h in holes)
    nodes = layout.graph_nodes_dir(graph, TARGET)
    parent = (nodes / ROOT / "Statement.lean").read_text(encoding="utf-8")
    for child, hole in zip((FIRST, SECOND), holes, strict=True):
        text = (nodes / child / "Statement.lean").read_text(encoding="utf-8")
        # The same bytes the writer produces from the hole with no record at all.
        unmarked = Hole.of({**hole, "proved_binders": []})
        assert text == postmerge.child_statement(
            child,
            unmarked,
            imports=postmerge.parent_imports(parent),
            opens=postmerge.parent_opens(parent),
        )
        meta = yaml.safe_load((nodes / child / "META.yaml").read_text(encoding="utf-8"))
        assert meta["statement-hash"] == schemas.content_hash(text.encode("utf-8"))


def test_an_old_hole_with_no_record_keeps_todays_expected_type(
    tmp_path: Path, real_toolchain: LocalToolchain, decomposed: Decomposed
) -> None:
    graph = copy_graph(tmp_path / "old", decomposed[0])
    # The child as a pre-rule post-merge job wrote it: the same files, no record.
    meta_path = layout.graph_nodes_dir(graph, TARGET) / FIRST / "META.yaml"
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    meta.pop("proved_binders", None)
    meta["schema"] = "meta/v2"
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False, allow_unicode=True), "utf-8")
    narrow = with_witness(
        real_toolchain, tmp_path / "narrow", graph, FIRST, (NARROW_FIRST, PROOF_NARROW_FIRST)
    )
    assert witness_check(narrow) == ("fail", "witness-type-mismatch"), narrow.as_dict()
    full = with_witness(
        real_toolchain, tmp_path / "full", graph, FIRST, (FULL_FIRST, PROOF_FULL_FIRST)
    )
    assert witness_check(full) == ("pass", None), full.as_dict()


def test_the_fast_check_asks_the_same_narrowed_type(
    tmp_path: Path, pinned: ResolvedToolchain
) -> None:
    """The service's witness mode inlines the gate's own ``WitnessType.lean`` (F13-T14); given
    the record it asks the checker the question step 7 asks, and gets the same answer."""
    statement = f"theorem hole : {CLOSED_FIRST} := by\n  sorry\n"
    witness = f"theorem witness : {NARROW_FIRST} := {PROOF_NARROW_FIRST}\n"
    source = tmp_path / "Preview.lean"
    source.write_text(checks.witness_text(statement, witness, "hole", PROVED), encoding="utf-8")
    lean = pinned.libdir.parent.parent / "bin" / "lean"
    proc = subprocess.run(
        [str(lean), str(source)], capture_output=True, text=True, check=False, timeout=600
    )
    assert ": error:" not in proc.stdout, proc.stdout
    verdict = checks.witness_verdict({"lean_messages": {"infos": proc.stdout.splitlines()}})
    assert verdict == {"expected": NARROW_FIRST, "given": NARROW_FIRST, "matches": True}


# --- what is not a proved fact, and a proved binder that is data ---------------------------------

#: An ``obtain`` of an existential (data ``s`` and its equation, both the assembly's), then a case
#: split on ``q ∨ ¬q``: ``hq`` holds only in its branch, so it is not a fact the assembly proved,
#: and a witness must still show the branch can be reached.
BRANCH_BODY = (
    "  intro p q r h\n"
    "  obtain ⟨s, hs⟩ : ∃ s : Prop, s = p := ⟨p, rfl⟩\n"
    "  rcases Classical.em q with hq | hq\n"
    "  · have c : s ∨ q := sorry\n"
    "    exact ⟨h.2, h.1.2, h.1.1⟩\n"
    "  · exact ⟨h.2, h.1.2, h.1.1⟩\n"
)
BRANCH_CLOSED = "∀ (p q r : Prop), (p ∧ q) ∧ r → ∀ (s : Prop), s = p → q → s ∨ q"
#: ``s`` is the assembly's choice, so the witness does not pick it: it is given every ``s`` the
#: assembly could have chosen. ``hq`` is the branch's, so the witness exhibits it.
BRANCH_NARROW = "∃ (p : Prop), ∃ (q : Prop), ∃ (r : Prop), ((p ∧ q) ∧ r) ∧ ∀ (s : Prop), s = p → q"
PROOF_BRANCH_NARROW = "⟨True, True, True, ⟨⟨trivial, trivial⟩, trivial⟩, fun _ _ => trivial⟩"


@pytest.fixture(scope="module")
def branched(
    tmp_path_factory: pytest.TempPathFactory,
    real_toolchain: LocalToolchain,
    pinned: ResolvedToolchain,
    lean_pkg: Path,
) -> Decomposed:
    del pinned, lean_pkg
    return decompose(tmp_path_factory.mktemp("branched"), real_toolchain, BRANCH_BODY, (FIRST,))


def test_a_case_branch_is_an_obligation_and_an_obtained_value_is_given(
    tmp_path: Path, real_toolchain: LocalToolchain, branched: Decomposed
) -> None:
    graph, holes, _ = branched
    (hole,) = holes
    assert hole["closed_type"] == BRANCH_CLOSED, hole
    assert hole["proved_binders"] == [4, 5], hole  # s and hs; not hq (6)
    assert hole["expected_witness"] == BRANCH_NARROW, hole
    admitted = with_witness(
        real_toolchain, tmp_path / "ok", graph, FIRST, (BRANCH_NARROW, PROOF_BRANCH_NARROW)
    )
    assert witness_check(admitted) == ("pass", None), admitted.as_dict()
    # Dropping the branch's hypothesis is refused: nothing the assembly proved says q.
    no_branch = "∃ (p : Prop), ∃ (q : Prop), ∃ (r : Prop), (p ∧ q) ∧ r"
    short = with_witness(
        real_toolchain, tmp_path / "short", graph, FIRST, (no_branch, PROOF_NARROW_FIRST)
    )
    assert witness_check(short) == ("fail", "witness-type-mismatch"), short.as_dict()
