"""F32-T8 (R10, AC13; D-29 v3.49): the guide says how a skeleton carries its holes' proofs.

An agent reads the guide and not the code (log, 2026-09-11: docs are tests). Where a sentence
states a suffix, a marker or a code the gate defines, the test reads the gate's value, so the two
cannot drift; and the worked example — the hole, its witness and its proof, read out of the guide
itself — is run through the gate's grammar here and through the real toolchain in the lean tier.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from harness import TARGET, declared, make_context

from opn_gate import carried, codes, layout, pipeline, scaffold
from opn_gate.paths import Change

ROOT = Path(__file__).resolve().parents[2]
GUIDE = (ROOT / "gate" / "agents" / "AGENTS.md").read_text(encoding="utf-8")
FLAT = re.sub(r"\s+", " ", GUIDE)
HEAD = "### Carrying the holes' proofs in the skeleton"
SECTION = GUIDE.split(HEAD, 1)[-1].split("### After the skeleton merges", 1)[0]
WITNESSES = GUIDE.split("### Carrying the holes' witnesses in the skeleton", 1)[-1]
WITNESSES = WITNESSES.split(HEAD, 1)[0]

PRESENT = {
    "the file name, built from the assembly's": f"-partial.1{carried.PROOF_SUFFIX}",
    "the marker that names the hole": "-- hole: h₁",
    "the separator line": "`-- proof:`",
    "what the body is": "what follows the hole statement's `:=`, starting at `by`",
    "where the type comes from": "`closed_type`",
    "the body introduces the binders": "the body introduces them (`intro`)",
    "the witness requirement": "`hole-proof-without-witness`",
    "what it may not use": "a sibling hole's theorem, the parent's, or a `Defs` module",
    "no import or use line": "no import or use line (`hole-proof-uses`)",
    "a hole that is an existing node": "`hole-proof-restates`",
    "a failure refuses the whole partial": "A carried proof that fails refuses the whole partial",
    "the unknown-hole code": "`hole-proof-unknown`",
    "the shared-name code": "`hole-proof-ambiguous`",
    "what the precheck says": "`holes[].proof`",
    "the old pin": "`400 hole-proof-unchecked`",
    "what the old pin's precheck says": "carries `carried_proofs`, whose `unchecked` lists them",
    "the hole is born proved": "is born `proved`",
    "credit": "credited to you, the partial's author",
    "the parent closes later": "closure sweep on the next merge",
    "the permitted-paths row": "`attempts/<timestamp>-<you>-partial.<n>.proof`",
    "the after-merge list knows": "Skip this for a hole whose proof the skeleton carried",
}


@pytest.mark.parametrize("what", sorted(PRESENT))
def test_the_guide_says(what: str) -> None:
    assert PRESENT[what] in FLAT, f"the guide does not say: {what}"


def test_the_section_sits_beside_the_witnesses_one() -> None:
    assert SECTION != GUIDE and "D-29 v3.49" in SECTION.splitlines()[0]
    assert (
        GUIDE.index("### Carrying the holes' witnesses")
        < GUIDE.index(HEAD)
        < GUIDE.index("### After the skeleton merges")
    )


def test_every_refusal_the_guide_names_is_one_the_gate_gives() -> None:
    """Each code the section names is in the catalog; the step-2 list is the grammar's own."""
    named = set(re.findall(r"`(hole-proof-[a-z-]+|helper-forbidden)`", SECTION))
    named |= {"hole-proof" + s for s in re.findall(r"`(-[a-z-]+)`", SECTION)}
    assert named, "the section names no code"
    assert named <= set(codes.CATALOG), sorted(named - set(codes.CATALOG))
    source = (ROOT / "gate" / "opn_gate" / "carried.py").read_text(encoding="utf-8")
    for code in ("unnamed", "duplicate", "malformed", "sorry", "uses", "unattached"):
        assert f'"hole-proof-{code}"' in source, code
    assert '"hole-proof-without-partial"' in source


# --- the worked example, out of the guide ---------------------------------------------------------


def example() -> tuple[str, str, str]:
    """The hole's ``have`` line, its witness file (the witnesses section's worked file) and its
    proof file, as the guide prints them."""
    have = re.search(r"For the hole `(have h₁ : .+? := sorry)`", FLAT)
    assert have is not None, "the section names no hole for its example"
    witness = WITNESSES.split("```lean\n", 1)[1].split("```", 1)[0]
    proof = SECTION.split("```lean\n", 1)[1].split("```", 1)[0]
    return have.group(1), witness, proof


def test_the_example_proof_is_one_the_grammar_reads() -> None:
    """R1, R2: the example names its hole, its witness names the same hole, the file names in the
    section attach to the assembly beside them, and it composes into a proof of the hole."""
    have, witness, proof = example()
    names = re.findall(r"attempts/(\S+)", SECTION.split("```text\n", 1)[1].split("```", 1)[0])
    assembly, witness_name, proof_name = names
    assert carried.number_of(assembly, witness_name) == 1
    assert carried.proof_number_of(assembly, proof_name) == 1
    witnesses, problem = carried.read(f"attempts/{assembly}", {f"attempts/{witness_name}": witness})
    assert problem is None
    proofs, problem = carried.read_proofs(
        f"attempts/{assembly}", {f"attempts/{proof_name}": proof}, [w.hole for w in witnesses]
    )
    assert problem is None and [p.hole for p in proofs] == ["h₁"]
    (read,) = proofs
    assert read.helpers is None and read.body.startswith("by\n")
    claimed = have.removeprefix("have h₁ : ").removesuffix(" := sorry")
    statement = f"theorem t : {claimed} := by\n  sorry\n"
    composed = carried.compose_proof(statement, read)
    assert composed == f"theorem t : {claimed} := {read.body}\n"
    assert "-- hole:" not in composed and "-- proof:" not in composed


# --- lean tier: the worked example through the real gate ------------------------------------------

NODE = "twelve-bound"
STEM = "attempts/20261030T000000Z-prover-partial"


def lean_context(tmp_path: Path, tc: Any, claimed: str) -> Any:
    """The propositional fixture with a node whose statement the example's hole serves: the
    hole's claim, with `∧ True` so the hole is not the statement itself."""
    ctx = make_context(tmp_path, node_id=NODE, toolchain=tc, changes=[])
    target_dir = layout.gate_spec_path(ctx.graph_root, TARGET).parent
    hypotheses, conclusion = claimed.rsplit(" → ", 1)
    statement = (
        f"import {layout.node_module(NODE, 'Context')}\n\n"
        f"theorem OpnProp.twelve_bound : {hypotheses} → {conclusion} ∧ True := by\n  sorry\n"
    )
    scaffold.write(
        target_dir / "nodes",
        scaffold.Proposal(
            node_id=NODE,
            target_id=TARGET,
            statement=statement,
            witness="theorem witness : ∃ n : Nat, 0 < n ∧ n ∣ 12 := ⟨1, by decide, by decide⟩\n",  # noqa: RUF001
            author="curator",
            date="2026-10-30T00:00:00Z",
        ),
    )
    return ctx


@pytest.mark.lean
@pytest.mark.usefixtures("pinned", "lean_pkg")
def test_the_example_passes_the_real_gate(tmp_path: Path, real_toolchain: Any) -> None:
    """AC13: a skeleton whose one hole is the guide's, carrying the guide's witness and proof,
    passes every step through the real toolchain, and step 4 records the proof as checked."""
    have, witness, proof = example()
    claimed = have.removeprefix("have h₁ : ").removesuffix(" := sorry")
    ctx = lean_context(tmp_path, real_toolchain, claimed)
    node = layout.graph_nodes_dir(ctx.graph_root, TARGET) / NODE
    st = layout.parse_statement((node / "Statement.lean").read_text(encoding="utf-8"))
    assert isinstance(st, layout.Statement)
    body = declared(f" by\n  {have}\n  intro n h1 h2\n  exact ⟨h₁ n h1 h2, trivial⟩\n")
    files = {
        f"{STEM}.lean": st.prefix + body,
        f"{STEM}.1{carried.SUFFIX}": witness,
        f"{STEM}.1{carried.PROOF_SUFFIX}": proof,
    }
    prefix = f"targets/{TARGET}/nodes/{NODE}/"
    ctx.changes = []
    for name, text in files.items():
        (node / name).write_text(text, encoding="utf-8")
        ctx.changes.append(Change("A", prefix + name))
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "pass", verdict.as_dict()
    step4 = next(s for s in verdict.steps if s.step == 4)
    assert step4.diagnostic is not None and step4.diagnostic.code == "hole-proofs"
    (entry,) = step4.diagnostic.details["proofs"]
    assert entry["hole"] == "h₁" and entry["node"] == f"{NODE}--h1"
