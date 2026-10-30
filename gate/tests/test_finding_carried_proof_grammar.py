"""F32-T1 (R1, R2; AC1, AC2; Q2, Q3, Q4; D-29 v3.49): a carried proof's file and its composition.

On erdos-68 (2026-10-28) two hole proofs were checked against the exact hole types 36 minutes
before the holes existed and became proved 64 minutes later, after a second round through the
queue. So a partial may carry, beside its assembly ``attempts/<name>.lean`` and its carried
witnesses ``attempts/<name>.<n>.witness``, files ``attempts/<name>.<n>.proof``:

    -- hole: <name>
    <optional private helpers, F00-T11>
    -- proof:
    <the body: what follows the hole statement's ``:=``>

Step 2 reads each as bytes and refuses a malformed one by name before any Lean is built. The
gate then composes the hole's ``Proof.lean`` from the ``Statement.lean`` the post-merge job will
write (``postmerge.child_statement``): the statement through its ``:=``, then the body, with the
helpers placed where F00-T11 puts them; the author never names the future node. The composed
file is a proof step 2 accepts for that node, unchanged.

Over the fake seam; the pre-merge check of the composed proof is T2's.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from harness import TARGET, make_context, node_dir
from test_finding_partial_carries_witnesses import BOTH, STEM, carrying, witness_text
from test_partial import ROOT
from test_postmerge import HOLES

from opn_gate import carried, layout, modes, paths, pipeline, postmerge, schemas
from opn_gate.paths import Change
from opn_gate.steps.artifact import PARTIAL_KEY

PROOF = f"{STEM}.1.proof"
HELPERS = "private theorem and_comm' (p q : Prop) (h : p ∧ q) : q ∧ p :=\n  ⟨h.2, h.1⟩\n"


def proof_text(
    hole: str = "right", body: str = "by\n  intro p q r h\n  exact h.2\n", helpers: str = ""
) -> str:
    return f"-- hole: {hole}\n" + helpers + "-- proof:\n" + body


def with_witnesses(**proofs: str) -> dict[str, str]:
    """``BOTH``'s carried witnesses plus the proof files named ``<n>`` -> text."""
    return {**BOTH, **{f"{STEM}.{n}.proof": text for n, text in proofs.items()}}


# --- step 2 ---------------------------------------------------------------------------------------


def test_a_well_formed_carried_proof_is_read_at_step_2(tmp_path: Path) -> None:
    """AC1: step 2 passes and records the file for step 4, as it records a carried witness."""
    ctx, _ = carrying(tmp_path, with_witnesses(**{"1": proof_text(helpers=HELPERS)}))
    verdict = pipeline.run_steps(ctx)
    step2 = next(s for s in verdict.steps if s.step == 2)
    assert step2.result == "pass", verdict.as_dict()
    recorded = ctx.data[PARTIAL_KEY][carried.PARTIAL_PROOFS_KEY]
    file = str(node_dir(ctx) / "attempts" / PROOF)
    assert recorded == [{"hole": "right", "path": f"attempts/{PROOF}", "file": file}]


@pytest.mark.parametrize(
    ("files", "code"),
    [
        ({"other-partial.1.proof": proof_text()}, "hole-proof-unattached"),
        ({f"{STEM}.01.proof": proof_text()}, "hole-proof-unattached"),
        ({f"{STEM}.proof": proof_text()}, "hole-proof-unattached"),
        ({PROOF: "-- proof:\nby\n  simp\n"}, "hole-proof-unnamed"),
        ({PROOF: proof_text(), f"{STEM}.2.proof": proof_text()}, "hole-proof-duplicate"),
        ({PROOF: "-- hole: right\nby\n  simp\n"}, "hole-proof-malformed"),
        ({PROOF: proof_text(body="")}, "hole-proof-malformed"),
        ({PROOF: proof_text(body="\n   \n")}, "hole-proof-malformed"),
        ({PROOF: proof_text(body="by\n  sorry\n")}, "hole-proof-sorry"),
        ({PROOF: proof_text(body="by\n  admit\n")}, "hole-proof-sorry"),
        ({PROOF: proof_text(helpers="import Mathlib.Tactic\n")}, "hole-proof-uses"),
        ({PROOF: proof_text(helpers="import Defs.Fact\n")}, "hole-proof-uses"),
        ({PROOF: proof_text(helpers="import Nodes.«and-reassoc».Proof\n")}, "hole-proof-uses"),
        ({PROOF: proof_text(helpers="theorem leak : True := trivial\n")}, "helper-forbidden"),
        ({PROOF: proof_text(helpers="set_option maxHeartbeats 0 in\n")}, "helper-forbidden"),
    ],
)
def test_a_malformed_carried_proof_is_refused_at_step_2(
    tmp_path: Path, files: dict[str, str], code: str
) -> None:
    """AC1: each by its code, naming the file, and before any Lean is built."""
    ctx, fake = carrying(tmp_path, {**BOTH, **files})
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 2, verdict.as_dict()
    assert verdict.diagnostic is not None and verdict.diagnostic.code == code
    assert verdict.diagnostic.details["path"].startswith("attempts/")
    assert verdict.diagnostic.details["path"].endswith(".proof")
    assert not any(c.startswith(("elaborate", "witness_type")) for c in fake.calls)


def test_a_comment_naming_sorry_is_not_a_sorry(tmp_path: Path) -> None:
    text = proof_text(body="by\n  -- no sorry here\n  intro p q r h\n  exact h.2\n")
    ctx, _ = carrying(tmp_path, with_witnesses(**{"1": text}))
    assert pipeline.run_steps(ctx).first_failing_step is None


def test_a_carried_proof_without_its_witness_is_refused(tmp_path: Path) -> None:
    """Q3: a proved node has a real witness, so a hole whose proof is carried carries its
    witness too; refused by its own name at step 2, before any Lean."""
    left_only = {f"{STEM}.2.witness": BOTH[f"{STEM}.2.witness"]}
    ctx, fake = carrying(tmp_path, {**left_only, PROOF: proof_text("right")})
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 2
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "hole-proof-without-witness"
    assert verdict.diagnostic.details == {"path": f"attempts/{PROOF}", "hole": "right"}
    assert not fake.calls or not any(c.startswith("elaborate") for c in fake.calls)


def test_a_proof_file_beside_a_proof_is_refused(tmp_path: Path) -> None:
    """R1: a ``.proof`` file belongs to a partial; on a proof submission it is refused by name
    at step 2 (a precheck never classifies)."""
    ctx = make_context(tmp_path)
    attempts = node_dir(ctx) / "attempts"
    attempts.mkdir(exist_ok=True)
    (attempts / PROOF).write_text(proof_text(), encoding="utf-8")
    assert ctx.changes is not None
    ctx.changes.append(Change("A", ctx.claim.node_prefix + f"attempts/{PROOF}"))
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 2
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "hole-proof-without-partial"
    assert verdict.diagnostic.details["paths"] == [f"attempts/{PROOF}"]


def test_a_carried_proof_is_read_as_its_bytes(tmp_path: Path) -> None:
    """AC1, F07-Q58 (3): ``\\r\\n`` line ends reach the record as they were sent."""
    text = proof_text().replace("\n", "\r\n")
    ctx, _ = carrying(tmp_path, BOTH)
    (node_dir(ctx) / "attempts" / PROOF).write_bytes(text.encode("utf-8"))
    assert ctx.changes is not None
    ctx.changes.append(Change("A", f"targets/{TARGET}/nodes/{ROOT}/attempts/{PROOF}"))
    verdict = pipeline.run_steps(ctx)
    assert next(s for s in verdict.steps if s.step == 2).result == "pass", verdict.as_dict()
    files = {f"attempts/{PROOF}": carried.read_file(node_dir(ctx) / "attempts" / PROOF)}
    (read,), problem = carried.read_proofs(f"attempts/{STEM}.lean", files, ["right"])
    assert problem is None
    assert read.sha256 == schemas.content_hash(text.encode("utf-8"))
    assert read.body == "by\r\n  intro p q r h\r\n  exact h.2"


def test_partial_mode_takes_a_carried_proof() -> None:
    """R1: the classifier's partial mode takes ``hole-proof`` beside the assembly (and beside
    its witnesses), and nothing else does — restated from T0's reservation."""
    prefix = f"targets/{TARGET}/nodes/{ROOT}/attempts/"
    assembly = Change("A", prefix + f"{STEM}.lean")
    proof = Change("A", prefix + PROOF)
    witness = Change("A", prefix + f"{STEM}.1.witness")
    assert modes.classify([assembly, witness, proof]).mode == "partial"
    assert modes.classify([proof]).mode is None
    beside_a_proof = [Change("A", f"targets/{TARGET}/nodes/{ROOT}/Proof.lean"), proof]
    assert modes.classify(beside_a_proof).mode is None
    assert modes.classify([assembly, Change("M", proof.path)]).mode is None
    located = paths.locate(proof.path)
    assert located is not None and located.role == "hole-proof"


# --- composition (R2, AC2) -----------------------------------------------------------------------


def child_text(tmp_path: Path, index: int = 0) -> tuple[str, str]:
    """A hole statement exactly as the post-merge job writes it, and the child's id."""
    from harness import copy_graph  # noqa: PLC0415

    root = copy_graph(tmp_path)
    parent = root / "targets" / TARGET / "nodes" / ROOT
    child = postmerge.child_id(ROOT, index + 1)
    proposal = postmerge.child_proposal(parent, child, HOLES[index], author="x", origin="x")
    return proposal.statement, child


def read_one(text: str, hole: str = "right") -> carried.CarriedProof:
    (proof,), problem = carried.read_proofs(
        f"attempts/{STEM}.lean", {f"attempts/{PROOF}": text}, [hole]
    )
    assert problem is None
    return proof


@pytest.mark.parametrize("helpers", ["", HELPERS, "\n" + HELPERS + "\n\n"])
def test_composed_proof_is_the_statement(tmp_path: Path, helpers: str) -> None:
    """AC2: the statement through ``:=``, then the body; helpers before the declaration; no
    marker line; and step 2's proof-is-statement check passes it for that node."""
    statement, child = child_text(tmp_path)
    parsed = layout.parse_statement(statement)
    assert isinstance(parsed, layout.Statement)
    body = "by\n  intro p q r h\n  exact h.2\n"
    composed = carried.compose_proof(statement, read_one(proof_text(body=body, helpers=helpers)))
    assert "-- hole:" not in composed and "-- proof:" not in composed
    assert paths.check_proof_is_statement(parsed, composed, node_id=child) is None
    assert layout.imports_of(composed) == layout.imports_of(statement)  # nothing added
    if not helpers:
        assert composed == parsed.prefix + " " + body.rstrip() + parsed.suffix
    else:
        at = layout.declaration_start(parsed.prefix)
        assert composed == (
            parsed.prefix[:at]
            + HELPERS
            + "\n"
            + parsed.prefix[at:]
            + " "
            + body.rstrip()
            + parsed.suffix
        )
    # The composed file is a statement-shaped proof: one theorem of the statement's name, and
    # the helper's private theorem before it.
    assert composed.count(f"theorem {child.replace('-', '_')} :") == 1


def test_composition_is_a_pure_function_of_its_inputs(tmp_path: Path) -> None:
    statement, _child = child_text(tmp_path)
    proof = read_one(proof_text(helpers=HELPERS))
    assert carried.compose_proof(statement, proof) == carried.compose_proof(statement, proof)
    other, _ = child_text(tmp_path / "b", index=1)
    assert carried.compose_proof(other, read_one(proof_text("left"), "left")).startswith(
        layout.parse_statement(other).prefix  # type: ignore[union-attr]
    )


def test_a_body_that_is_not_by_is_composed_as_it_is(tmp_path: Path) -> None:
    """Q2: the body is what follows ``:=``, a term as much as a tactic block."""
    statement, child = child_text(tmp_path)
    parsed = layout.parse_statement(statement)
    assert isinstance(parsed, layout.Statement)
    proof = read_one(proof_text(body="fun _ _ _ h => h.2\n"))
    composed = carried.compose_proof(statement, proof)
    assert composed == parsed.prefix + " fun _ _ _ h => h.2" + parsed.suffix
    assert paths.check_proof_is_statement(parsed, composed, node_id=child) is None


def test_witness_tests_still_hold_beside_proofs(tmp_path: Path) -> None:
    """Q57's grammar is untouched: the witnesses beside a proof are read as before."""
    ctx, _ = carrying(tmp_path, with_witnesses(**{"1": proof_text()}))
    pipeline.run_steps(ctx)
    assert [w["hole"] for w in ctx.data[PARTIAL_KEY][carried.PARTIAL_WITNESSES_KEY]] == [
        "right",
        "left",
    ]
    assert witness_text("right") == BOTH[f"{STEM}.1.witness"]
