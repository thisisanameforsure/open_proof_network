"""F08-T24, lean tier: a proof uses another node's merged proof, checked by the real toolchain
(R18; proposed decisions v3.25).

``test_uses_nodes.py`` pins the rules with the toolchain faked. Here the kernel says the rest:

* a proof that imports a proved node's module and names its theorem passes steps 1 to 8, the
  use read back out of the proof term by ``opn-used-constants``;
* the same header over a proof that does not name it is refused at step 8 (``use-unused``): the
  header is held to the term, not believed;
* a theorem that is merely *reachable* through the import (a dependency of the used node) and
  not declared is refused as an undeclared dependency;
* a used node's proof module that carries an instance cannot change what the statement says
  (``statement-meaning-changed``), and without the guard the same submission passes every step;
* a node whose dependency's merged proof has a use line still builds: the closure is staged.

Lean core only, on the propositional fixture.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from harness import TARGET, make_context
from test_uses_defs_lean import CARRIER, CARRIER_PROOF_TAIL, STATEMENTS, WITNESS, context
from test_uses_nodes import INTERIOR, ROOT, TUTORIAL, add_node, nodes, use_line

from opn_gate import layout, pipeline, scaffold, uses
from opn_gate.steps import RunContext, meaning
from opn_gate.toolchain import LocalToolchain

pytestmark = [pytest.mark.lean, pytest.mark.usefixtures("pinned", "lean_pkg")]

#: A proof of ``and-reassoc`` that goes through the tutorial node's theorem.
VIA_SWAP = (
    " by\n  intro p q r h\n  have h1 := OpnProp.and_swap _ _ h\n  exact ⟨h1.2.1, h1.2.2, h1.1⟩\n"
)
DIRECT = " by\n  intro p q r h\n  exact ⟨h.1.1, h.1.2, h.2⟩\n"


def write_proof(ctx: RunContext, node_id: str, body: str, *used: str) -> None:
    """The node's ``Proof.lean``: use lines where they go, the statement, and ``body``."""
    here = nodes(ctx) / node_id
    st = layout.parse_statement((here / "Statement.lean").read_text(encoding="utf-8"))
    assert isinstance(st, layout.Statement)
    lines = "".join(use_line(u) + "\n" for u in used)
    imports = [ln for ln in st.prefix.splitlines(keepends=True) if ln.startswith("import ")]
    head = st.prefix.replace(imports[-1], imports[-1] + lines) if imports else lines + st.prefix
    (here / "Proof.lean").write_text(head + body, encoding="utf-8")


def test_a_proof_uses_a_proved_node_by_importing_its_proof(
    tmp_path: Path, real_toolchain: LocalToolchain
) -> None:
    ctx = make_context(tmp_path, node_id=INTERIOR, toolchain=real_toolchain)
    write_proof(ctx, INTERIOR, VIA_SWAP, TUTORIAL)
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "pass", verdict.as_dict()
    assert [(s.step, s.result) for s in verdict.steps] == [
        (n, "pass") for n in (1, 2, 4, 5, 6, 7, 8)
    ]
    assert verdict.data[uses.USES_KEY]["nodes"] == [TUTORIAL]
    # step 8 read the use out of the kernel term; the node's recorded deps are still none
    assert verdict.data["deps"]["used"] == [TUTORIAL]
    assert verdict.data["deps"]["declared"] == []
    assert verdict.data[meaning.MEANING_KEY] == {"identical": True, "matches": True}


def test_a_use_line_over_a_proof_that_does_not_use_the_node_is_refused(
    tmp_path: Path, real_toolchain: LocalToolchain
) -> None:
    ctx = make_context(tmp_path, node_id=INTERIOR, toolchain=real_toolchain)
    write_proof(ctx, INTERIOR, DIRECT, TUTORIAL)
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "fail", verdict.as_dict()
    assert verdict.first_failing_step == 8
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "use-unused"
    assert verdict.diagnostic.details["unused"] == [TUTORIAL]


def test_a_theorem_reachable_through_a_use_but_not_declared_is_refused(
    tmp_path: Path, real_toolchain: LocalToolchain
) -> None:
    """``lemma`` depends on the tutorial node, so importing ``lemma``'s proof makes
    ``OpnProp.and_swap`` reachable by name. The proof names both and declares one."""
    ctx = make_context(tmp_path, node_id=INTERIOR, toolchain=real_toolchain)
    add_node(ctx, "lemma", deps=(TUTORIAL,))
    write_proof(ctx, "lemma", " fun p q h => OpnProp.and_swap p q h\n")
    write_proof(
        ctx,
        INTERIOR,
        " by\n  intro p q r h\n  have h1 := OpnProp.lemma _ _ h\n"
        "  have h2 := OpnProp.and_swap _ _ h1\n  exact ⟨h2.1.1, h2.1.2, h2.2⟩\n",
        "lemma",
    )
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "fail", verdict.as_dict()
    assert verdict.first_failing_step == 8
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "undeclared-dependency", verdict.diagnostic
    assert {o["node"] for o in verdict.diagnostic.details["offences"]} == {TUTORIAL}


def test_a_node_whose_dependency_has_a_use_line_still_builds(
    tmp_path: Path, real_toolchain: LocalToolchain
) -> None:
    """The root depends on the tutorial node and on ``and-reassoc``, in that order. Once the
    tutorial node's merged proof uses ``and-reassoc``, gating the root has to build
    ``and-reassoc`` first: the closure is staged by what each proof imports, not by the order
    a ``META.yaml`` happens to list."""
    ctx = make_context(tmp_path, node_id=ROOT, toolchain=real_toolchain)
    write_proof(
        ctx,
        TUTORIAL,
        " by\n  intro p q h\n  have h1 := OpnProp.and_reassoc p q True ⟨h, trivial⟩\n"
        "  exact ⟨h1.2.1, h1.1⟩\n",
        INTERIOR,
    )
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "pass", verdict.as_dict()
    assert uses.USES_KEY not in verdict.data


def carrier_context(tmp_path: Path, tc: LocalToolchain) -> RunContext:
    """The definitions fixture, a proved ``carrier`` whose proof module carries an instance,
    and the false ``size-is-zero`` claimed by a proof that uses ``carrier``."""
    ctx = context(tmp_path, "size-is-zero", tc)
    scaffold.write(
        nodes(ctx),
        scaffold.Proposal(
            node_id="carrier",
            target_id=TARGET,
            statement=CARRIER,
            witness="theorem witness : True := trivial\n",
            author="curator",
            date="2026-10-01T00:00:00Z",
        ),
    )
    st = layout.parse_statement(CARRIER)
    assert isinstance(st, layout.Statement)
    (nodes(ctx) / "carrier" / "Proof.lean").write_text(
        st.prefix + CARRIER_PROOF_TAIL, encoding="utf-8"
    )
    assert STATEMENTS["size-is-zero"] and WITNESS
    write_proof(
        ctx,
        "size-is-zero",
        " by\n  intro n\n  have _c : True := OpnProp.carrier\n  rfl\n",
        "carrier",
    )
    return ctx


def test_a_used_nodes_proof_module_cannot_change_what_the_statement_says(
    tmp_path: Path, real_toolchain: LocalToolchain
) -> None:
    ctx = carrier_context(tmp_path, real_toolchain)
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "fail", verdict.as_dict()
    assert verdict.first_failing_step == 4
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "statement-meaning-changed", verdict.diagnostic
    assert verdict.diagnostic.details["uses"] == [layout.node_module("carrier", "Proof")]


def test_without_the_guard_a_used_nodes_instance_proves_a_false_statement(
    tmp_path: Path, real_toolchain: LocalToolchain, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = carrier_context(tmp_path, real_toolchain)
    monkeypatch.setattr(meaning, "guard", lambda *_a, **_k: None)
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "pass", verdict.as_dict()
