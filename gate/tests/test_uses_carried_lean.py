"""F08-T25, lean tier: a definition a dependency's proof declared cannot change what a dependent's
statement says (R22, Q40).

The trap, on the real toolchain. ``Defs.Trap`` is a definition module a curator admitted; it
carries a higher-priority instance. ``carrier`` is a true statement, proved honestly by a proof
that declares ``import Defs.Trap``: its own statement does not mention the class, so its meaning
guard passes, and an idle definition is a warning, never a refusal. ``size-is-zero-dep`` depends
on ``carrier`` and is false as its own header reads it. Its "proof" declares no use at all — its
header is the statement's, the rule F00-R19 has always held — and Lean accepts it, because the
generated Context imports ``carrier``'s proof module and with it ``Defs.Trap``.

* with the guard reaching the closure, step 4 refuses it ``statement-meaning-changed`` and names
  the carrier;
* with the guard switched off, the same submission passes every step, which is what T23 and T24
  alone would have merged.

Lean core only, on the propositional fixture with ``test_uses_defs_lean``'s definitions.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from harness import TARGET
from test_uses_defs_lean import CARRIER, DEPENDENT, WITNESS, context

from opn_gate import layout, pipeline, scaffold, uses
from opn_gate.steps import RunContext, meaning
from opn_gate.toolchain import LocalToolchain

pytestmark = [pytest.mark.lean, pytest.mark.usefixtures("pinned", "lean_pkg")]


def trap_context(tmp_path: Path, tc: LocalToolchain) -> RunContext:
    """``carrier`` proved by an honest proof that declares ``Defs.Trap``; the false
    ``size-is-zero-dep`` depending on it, claimed by a proof whose header is its statement's."""
    ctx = context(tmp_path, "size-is-zero-dep", tc)
    nodes = layout.graph_nodes_dir(ctx.graph_root, TARGET)
    scaffold.write(
        nodes,
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
    own = f"import {layout.node_module('carrier', 'Context')}\n"
    assert st.prefix.count(own) == 1
    carrier_proof = st.prefix.replace(own, f"{own}import Defs.Trap\n") + " by\n  trivial\n"
    (nodes / "carrier" / "Proof.lean").write_text(carrier_proof, encoding="utf-8")
    # the carrier's proof is a merged proof like any other: the statement, one use line, a body
    assert uses.declared(st, carrier_proof, "carrier").modules == ("Defs.Trap",)
    assert layout.validate_node(nodes / "carrier") == []
    scaffold.write(
        nodes,
        scaffold.Proposal(
            node_id="size-is-zero-dep",
            target_id=TARGET,
            statement=DEPENDENT,
            witness=WITNESS,
            author="curator",
            deps=("carrier",),
            date="2026-10-01T00:00:00Z",
        ),
    )
    dep = layout.parse_statement(DEPENDENT)
    assert isinstance(dep, layout.Statement)
    (nodes / "size-is-zero-dep" / "Proof.lean").write_text(
        dep.prefix + " by\n  intro n\n  rfl\n", encoding="utf-8"
    )
    return ctx


def test_the_carriers_own_proof_is_an_honest_merge(
    tmp_path: Path, real_toolchain: LocalToolchain
) -> None:
    """Nothing about the carrier is refusable: its statement means what it meant, so the trap
    cannot be stopped where the use is declared."""
    ctx = trap_context(tmp_path, real_toolchain)
    ctx.claim = type(ctx.claim)(target_id=TARGET, node_id="carrier")
    ctx.changes = None
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "pass", verdict.as_dict()
    assert verdict.data[uses.USES_KEY]["defs"] == ["Defs.Trap"]


def test_a_dependencys_declared_definition_cannot_change_a_dependents_statement(
    tmp_path: Path, real_toolchain: LocalToolchain
) -> None:
    ctx = trap_context(tmp_path, real_toolchain)
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "fail", verdict.as_dict()
    assert verdict.first_failing_step == 4
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "statement-meaning-changed", verdict.diagnostic
    assert verdict.diagnostic.details["uses"] == []
    assert verdict.diagnostic.details["carried"] == {"carrier": ["Defs.Trap"]}
    assert verdict.diagnostic.details["expected"] != verdict.diagnostic.details["declared"]


def test_without_the_guard_the_dependent_proves_a_false_statement(
    tmp_path: Path, real_toolchain: LocalToolchain, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = trap_context(tmp_path, real_toolchain)
    monkeypatch.setattr(meaning, "guard", lambda *_a, **_k: None)
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "pass", verdict.as_dict()
