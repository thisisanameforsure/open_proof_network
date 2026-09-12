"""F12-T2 / AC12 with the real toolchain (lean tier): the screens on the on-ramp root under the
pinned Mathlib find nothing, and on the propositional fixture's root — a tautology — the
statement screen *proves it* and the finding is a kernel-checked exhibit the append gate
elaborates again.

The fast tier proves the runner's every branch through the fake seam; this proves the scratch
files the shapes produce are Lean the pinned toolchain accepts, that a proof found by the
tactic script survives ``leanchecker --fresh`` and the axiom check, and — printed for
``engineering/evidence/F12/budgets.txt`` (F12-Q4) — how long each attempt takes.

Needs the Mathlib checkout ``gate/scripts/install-mathlib.sh <sha>`` makes for the on-ramp
half; the propositional half needs only the toolchain.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

import pytest
from conftest import ONRAMP, ONRAMP_TARGET
from harness import GRAPH, TARGET, copy_graph

from opn_gate import config, exhibits, modes, qa, schemas
from opn_gate.paths import Change, Claim
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import LocalToolchain

pytestmark = pytest.mark.lean

ONRAMP_ROOT = "infinitude-of-primes"
PROPOSITIONAL_ROOT = "and-swap-reassoc"
WHEN = "2026-09-12T12:00:00Z"


def context(
    graph_root: Path, target_id: str, root: str, tc: LocalToolchain, work: Path
) -> RunContext:
    spec_path = graph_root / "targets" / target_id / "gate-spec.json"
    return RunContext(
        graph_root=graph_root,
        claim=Claim(target_id, root),
        spec=schemas.load_json(spec_path, "gate-spec/v1"),
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=None,
        workdir=work,
        toolchain=tc,
        settings=config.load({}),
    )


def report(capsys: pytest.CaptureFixture[str], line: str) -> None:
    """Print past pytest's capture, so a *passing* run's budget numbers reach the CI log (a
    captured print is shown only for failures; the numbers are wanted when the screens pass)."""
    with capsys.disabled():
        print(line)


def budget_lines(capsys: pytest.CaptureFixture[str], label: str, run: qa.ScreenRun) -> None:
    for row in run.rows:
        report(
            capsys,
            f"F12 §6 budget: {label} {row.check:<20} {row.verdict:<12} "
            f"{(row.elapsed_s or 0.0):7.1f}s of {row.budget_s or 0:g}s",
        )


def test_onramp_screens_clean(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    real_toolchain: LocalToolchain,
    lean_pkg: Path,
) -> None:
    """AC12: on the pinned toolchain and Mathlib, the statement, its negation and False all fail
    to prove within budget; the record shows the three clean passes (and the compile, and the
    vacuous consequence pass), no exhibit, no claim, exit as a clean pass."""
    real_toolchain.lean_pkg_bin = lean_pkg
    root = tmp_path / "graph"
    shutil.copytree(ONRAMP, root)
    ctx = context(root, ONRAMP_TARGET, ONRAMP_ROOT, real_toolchain, tmp_path / "work")
    started = time.monotonic()
    run = qa.screen(ctx, "root", date=WHEN, attempt_budget_s=120.0, subject_budget_s=600.0)
    elapsed = time.monotonic() - started
    budget_lines(capsys, "onramp", run)
    report(capsys, f"F12 §6 budget: onramp subject total {elapsed:.1f}s")
    assert {r.check: r.verdict for r in run.rows} == {
        "compile": "pass",
        "screen-consequence": "pass",
        "screen-statement": "pass",
        "screen-negation": "pass",
        "screen-false": "pass",
    }, [(r.check, r.verdict, r.note) for r in run.rows]
    assert run.clean and run.exhibits == [] and run.claims == []
    state = qa.pass_state(root / "targets" / ONRAMP_TARGET, "root")
    assert state.missing == ("brief", "backtranslation")


def test_a_tautology_is_found_and_its_exhibit_replays(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    real_toolchain: LocalToolchain,
    lean_pkg: Path,
) -> None:
    """R3, R4 on a real proof: the propositional root is provable by ``simp_all``, so the
    statement screen is a finding — the exhibit passed ``leanchecker --fresh`` and rests on no
    axiom outside the allowlist — and the claim's exhibit elaborates through the append gate."""
    real_toolchain.lean_pkg_bin = lean_pkg
    root = copy_graph(tmp_path, GRAPH)
    ctx = context(root, TARGET, PROPOSITIONAL_ROOT, real_toolchain, tmp_path / "work")
    run = qa.screen(ctx, "root", date=WHEN, attempt_budget_s=120.0, subject_budget_s=600.0)
    budget_lines(capsys, "propositional", run)
    by_check = {r.check: r for r in run.rows}
    assert by_check["compile"].verdict == "pass"
    assert by_check["screen-statement"].verdict == "fail", by_check["screen-statement"].note
    assert by_check["screen-negation"].verdict == "pass"
    assert by_check["screen-false"].verdict == "pass"
    assert not run.clean and len(run.exhibits) == 1 and len(run.claims) == 1
    note = by_check["screen-statement"].note or ""
    assert "proved with axioms" in note and "sorryAx" not in note

    # The claim is an append the gate accepts, and its exhibit elaborates against the node.
    classification = modes.classify([Change("A", run.claims[0])])
    assert classification.mode == "append" and modes.check(root, classification) == []
    ctx2 = context(root, TARGET, PROPOSITIONAL_ROOT, real_toolchain, tmp_path / "work2")
    assert exhibits.run(ctx2, modes.exhibits(root, classification)) == []
    # And the finding holds the grade until it is routed (R4, R9).
    state = qa.pass_state(
        root / "targets" / TARGET, "root", routed=qa.routed_by_claims(root / "targets" / TARGET)
    )
    assert [f.check for f in state.unrouted] == ["screen-statement"]


# --- AC24: a hand-committed exhibit is replayed before it counts (R15, R9) -----------------------

FORGED = (
    "theorem OpnQa.equiv_forward : (2 : Nat) + 2 = 4 := by native_decide\n"
    "theorem OpnQa.equiv_backward : (3 : Nat) + 3 = 6 := by native_decide\n"
)


def test_exhibit_is_replayed_before_it_counts(
    tmp_path: Path, real_toolchain: LocalToolchain, lean_pkg: Path
) -> None:
    """AC24: an exhibit that elaborates and has a matching hash and no sorry, but proves by
    native_decide, is refused by the replay through the real toolchain — the axiom check sees
    ``Lean.ofReduceBool`` — so the grade does not rise."""
    real_toolchain.lean_pkg_bin = lean_pkg
    root = copy_graph(tmp_path, GRAPH)
    target = root / "targets" / TARGET
    rel, digest = qa.store_exhibit(target, "root-equivalence-1.lean", FORGED)
    rows = [
        qa.row(
            check,
            "pass",
            tool="hand",
            tool_version="0",
            timestamp=WHEN,
            model="hand" if qa.KIND_OF[check] == "brief" else None,
        )
        for check in qa.FLOOR_ROOT
    ]
    rows.append(
        qa.row(
            "equivalence",
            "pass",
            tool="hand",
            tool_version="0",
            timestamp=WHEN,
            exhibit=rel,
            exhibit_sha256=digest,
        )
    )
    qa.write(target, "root", rows, date=WHEN, produced_by="hand")
    state = qa.pass_state(target, "root")
    assert state.complete and state.refused == (), "the fast checks let the forgery through"

    ctx = context(root, TARGET, PROPOSITIONAL_ROOT, real_toolchain, tmp_path / "work")
    with pytest.raises(qa.QaError, match="ofReduceBool") as refused:
        qa.grade_gate(
            target, "root", replay=lambda rs: qa.replay_exhibits(ctx, rs, timeout_s=120.0)
        )
    assert refused.value.code == qa.CODE_REPLAY
    assert (target / "fidelity").is_dir() is False or not any(
        "screened" in p.read_text() for p in (target / "fidelity").glob("root-*.yaml")
    )
