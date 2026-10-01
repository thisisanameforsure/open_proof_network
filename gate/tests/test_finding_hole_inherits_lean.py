"""F07-T48, lean tier: a hole is closed over the earlier holes it mentions, not every one in scope.

The extractor closed each ``have``-bound hole over every binder in scope (F11-Q22), an earlier
hole included, so a later hole inherited a predecessor it had nothing to do with. Live on
``erdos-1050--h1-v2--h4`` (three testers, 2026-09-27): the skeleton wrote ``have hrem : … := by
clear hden; sorry`` and the child still carried ``hden`` as a hypothesis, its witness had to carry
the whole proof of ``hden`` (845 lines), and the same proof went through the merge queue twice.
``clear`` leaves no trace in the proof term, checked at Lean 4.33.1 rather than assumed: the
hole's value is ``sorryAx T`` either way, and the assembly went on using ``hden`` after the hole.
Nothing but the hole's own type can say what it needs.

The rule: every local that is not an earlier hole is kept as before (the statement's own binders,
in their order, ``intro``s, case fields, proved ``have``s); an earlier hole is kept only when
something kept mentions it, transitively, through the hole's type or the type of a kept binder.
A hole that wants a predecessor's fact and cannot mention it states it as a premise
(``have h4 : P → Q := sorry``), which is what ``test_finding_witness_proved_haves_lean`` now does.

Lean core only, like the rest of the propositional fixture (``Nat``, not the double-struck
notation, for the reason ``test_finding_hole_roundtrip_lean`` gives).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from harness import TARGET, make_context
from test_finding_hole_roundtrip_lean import ROOT, SKELETON

from opn_gate import layout, pipeline
from opn_gate.paths import Change
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

#: Four holes. ``h4`` does not mention ``h3``; ``h5`` mentions ``h3`` in its type and not ``h4``;
#: ``h6`` mentions only ``c``, whose sibling field ``hc`` is typed over ``h3`` — so ``h6`` keeps
#: ``h3`` through ``hc``'s type and nothing else.
BODY = (
    "  intro p q r h\n"
    "  have h3 : ∃ x : Nat, 0 < x := sorry\n"
    "  have h4 : q ∧ p := sorry\n"
    "  have h5 : 0 < Classical.choose h3 := sorry\n"
    "  obtain ⟨c, hc⟩ : ∃ c : Nat, c = Classical.choose h3 := ⟨_, rfl⟩\n"
    "  have h6 : 0 < c := sorry\n"
    "  exact ⟨h.2, h4⟩\n"
)
STMT = "∀ (p q r : Prop), (p ∧ q) ∧ r →"
H3 = "∃ (x : Nat), (0 : Nat) < x"
CLOSED = {
    "h3": f"{STMT} {H3}",
    # h3 dropped: h4's type does not mention it.
    "h4": f"{STMT} q ∧ p",
    # h3 kept, by name, because the type mentions it; h4 dropped.
    "h5": f"{STMT} ∀ (h3 : {H3}), (0 : Nat) < Classical.choose h3",
    # h3 kept through hc's type; h4 and h5 dropped; c and hc are the assembly's (proved).
    "h6": f"{STMT} ∀ (h3 : {H3}) (c : Nat), c = Classical.choose h3 → (0 : Nat) < c",
}
#: Step 7's expected witness (F07-R21) over each closed type. ``h5`` keeps ``h3`` by name, so its
#: witness must show ``h3`` can hold — the F11-Q22 cost, now paid only where a hole names its
#: predecessor (a hypothesis no later binder mentions is exhibited as a conjunct, read from the
#: run rather than guessed); ``h6``'s ``h3`` is a variable because ``hc``'s type mentions it.
WITNESS = {
    "h3": "∃ (p : Prop), ∃ (q : Prop), ∃ (r : Prop), (p ∧ q) ∧ r",
    "h4": "∃ (p : Prop), ∃ (q : Prop), ∃ (r : Prop), (p ∧ q) ∧ r",
    "h5": f"∃ (p : Prop), ∃ (q : Prop), ∃ (r : Prop), ((p ∧ q) ∧ r) ∧ {H3}",
    "h6": f"∃ (p : Prop), ∃ (q : Prop), ∃ (r : Prop), ∃ (h3 : {H3}), (p ∧ q) ∧ r",
}
#: ``c`` and ``hc`` sit after p q r h h3 in ``h6``'s closed type: binders 5 and 6.
PROVED = {"h3": [], "h4": [], "h5": [], "h6": [5, 6]}


def one_line(text: str) -> str:
    """The pretty-printer wraps at its width; the comparison is on the tokens."""
    return " ".join(text.split())


@pytest.fixture(scope="module")
def holes(
    tmp_path_factory: pytest.TempPathFactory,
    real_toolchain: LocalToolchain,
    pinned: ResolvedToolchain,
    lean_pkg: Path,
) -> dict[str, dict[str, object]]:
    """The skeleton through the real extractor, once for the module."""
    del pinned, lean_pkg  # resolved and built by the fixtures; the seam finds both itself
    tmp = tmp_path_factory.mktemp("inherits")
    ctx = make_context(
        tmp,
        node_id=ROOT,
        toolchain=real_toolchain,
        changes=[Change("A", f"targets/{TARGET}/nodes/{ROOT}/attempts/{SKELETON}")],
    )
    node = layout.graph_nodes_dir(ctx.graph_root, TARGET) / ROOT
    (node / "Proof.lean").unlink(missing_ok=True)
    statement = (node / "Statement.lean").read_text(encoding="utf-8")
    head, _, _ = statement.partition(":= by\n  sorry")
    (node / "attempts").mkdir(exist_ok=True)
    (node / "attempts" / SKELETON).write_text(head + ":= by\n" + BODY, encoding="utf-8")
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "pass", verdict.as_dict()
    reported = verdict.data["artifact"]["holes"]
    assert [h["name"] for h in reported] == ["h3", "h4", "h5", "h6"]
    return {str(h["name"]): h for h in reported}


@pytest.mark.parametrize("name", ["h3", "h4", "h5", "h6"])
def test_a_hole_is_closed_over_the_holes_it_mentions(
    holes: dict[str, dict[str, object]], name: str
) -> None:
    """The closed type carries an earlier hole only when the hole's type reaches it."""
    hole = holes[name]
    assert one_line(str(hole["closed_type"])) == CLOSED[name], hole
    assert hole["closed_roundtrip"] is True, hole


@pytest.mark.parametrize("name", ["h3", "h4", "h5", "h6"])
def test_the_witness_and_the_proved_indices_follow_the_closed_type(
    holes: dict[str, dict[str, object]], name: str
) -> None:
    """Step 7's expected type and ``proved_binders`` (F07-T44) index the closed type as reported,
    so dropping a hole moves the indices of the binders after it."""
    hole = holes[name]
    assert one_line(str(hole["expected_witness"])) == WITNESS[name], hole
    assert hole["proved_binders"] == PROVED[name], hole


def test_the_statement_binders_are_always_kept(holes: dict[str, dict[str, object]]) -> None:
    """The statement's own binders stay, in their order, whether or not a hole mentions them:
    ``h4`` mentions neither ``r`` nor ``h`` and is still closed over both."""
    assert one_line(str(holes["h4"]["closed_type"])).startswith(STMT)
