"""Step 4's replay mode (D-4 step 4): ``--fresh`` on a Mathlib-free target; on a Mathlib-pinned one,
``leanchecker`` over the graph's own prefixes without ``--fresh``, because fresh-replaying all of
Mathlib exceeds the wall-clock cap (found live 2026-09-14 on an erdos-376 partial)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from fakes import FakeToolchain
from harness import TUTORIAL, make_context

from opn_gate import pipeline
from opn_gate.steps.replay import (
    MODE_FRESH,
    MODE_PREFIX,
    REPLAY_MODE_KEY,
    graph_prefixes,
    replay_plan,
)
from opn_gate.toolchain import LocalToolchain, ReplayResult, ResolvedToolchain, replay_command

MATHLIB = {"mathlib_sha": "0df444a360eaa60ab8c11dca51a86af692955474"}
PROOF = f"Nodes.«{TUTORIAL}».Proof"


class TimingOut(FakeToolchain):
    def kernel_replay(self, *args: object, **kwargs: object) -> ReplayResult:
        raise subprocess.TimeoutExpired(["leanchecker"], 600)


def _step4(verdict: pipeline.Verdict) -> pipeline.StepRecord:
    return next(s for s in verdict.steps if s.step == 4)


def _olean(build: Path, rel: str) -> None:
    path = build / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"olean")


# -- the command ----------------------------------------------------------------------------------


def test_command_fresh_is_one_module() -> None:
    assert replay_command([PROOF], fresh=True) == ["leanchecker", "--fresh", PROOF]
    with pytest.raises(ValueError, match="exactly one"):
        replay_command(["Nodes", "Defs"], fresh=True)


def test_command_prefix_form_takes_many() -> None:
    assert replay_command(["Nodes", "Defs"], fresh=False) == ["leanchecker", "Nodes", "Defs"]


def test_command_refuses_a_bare_string_and_nothing() -> None:
    with pytest.raises(TypeError):
        replay_command("Nodes", fresh=False)
    with pytest.raises(ValueError, match="at least one"):
        replay_command([], fresh=False)


# -- the plan -------------------------------------------------------------------------------------


def test_plan_without_mathlib_is_fresh(tmp_path: Path) -> None:
    _olean(tmp_path, "Defs/Fact.olean")
    assert replay_plan({"mathlib_sha": None}, PROOF, tmp_path) == (MODE_FRESH, [PROOF])


def test_plan_with_mathlib_names_defs_only_when_built(tmp_path: Path) -> None:
    _olean(tmp_path, f"Nodes/{TUTORIAL}/Proof.olean")
    assert replay_plan(MATHLIB, PROOF, tmp_path) == (MODE_PREFIX, ["Nodes"])
    (tmp_path / "Defs").mkdir()  # a Defs directory with no olean does not count
    assert graph_prefixes(tmp_path) == ["Nodes"]
    _olean(tmp_path, "Defs/IsPrime.olean")
    assert replay_plan(MATHLIB, PROOF, tmp_path) == (MODE_PREFIX, ["Nodes", "Defs"])


def test_plan_with_mathlib_adds_a_module_outside_the_prefixes(tmp_path: Path) -> None:
    """QA's scratch exhibits (``OpnQa.*``) are not graph modules; they are replayed by name."""
    _olean(tmp_path, "Defs/IsPrime.olean")
    assert replay_plan(MATHLIB, "OpnQa.Replay0", tmp_path) == (
        MODE_PREFIX,
        ["Defs", "OpnQa.Replay0"],
    )


# -- step 4 through the pipeline ------------------------------------------------------------------


def test_mathlib_free_spec_replays_the_proof_fresh(tmp_path: Path) -> None:
    fake = FakeToolchain()
    ctx = make_context(tmp_path, toolchain=fake)
    assert ctx.spec["mathlib_sha"] is None
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict.as_dict()
    assert fake.replays == [((PROOF,), True)]
    assert ctx.data[REPLAY_MODE_KEY] == MODE_FRESH


def test_mathlib_spec_replays_the_graph_prefixes(tmp_path: Path) -> None:
    fake = FakeToolchain()
    ctx = make_context(tmp_path, toolchain=fake, spec_overrides=MATHLIB)
    pipeline.run_steps(ctx)
    assert fake.replays == [(("Nodes",), False)]  # the propositional fixture has no defs/
    assert ctx.data[REPLAY_MODE_KEY] == MODE_PREFIX


def test_mathlib_spec_with_defs_replays_defs_too(tmp_path: Path) -> None:
    fake = FakeToolchain()
    ctx = make_context(tmp_path, toolchain=fake, spec_overrides=MATHLIB)
    defs = ctx.graph_root / "targets" / ctx.claim.target_id / "defs"
    defs.mkdir(exist_ok=True)  # the fixture keeps an empty defs/ (a .gitkeep)
    (defs / "Fact.lean").write_text("def Opn.fact : Nat → Nat\n  | _ => 1\n", encoding="utf-8")
    pipeline.run_steps(ctx)
    assert fake.replays == [(("Nodes", "Defs"), False)]


@pytest.mark.parametrize(("overrides", "mode"), [({}, MODE_FRESH), (MATHLIB, MODE_PREFIX)])
def test_failure_is_mode_neutral_and_names_the_mode(
    tmp_path: Path, overrides: dict[str, str], mode: str
) -> None:
    fake = FakeToolchain(replay=ReplayResult(ok=False, output="kernel: bad"))
    verdict = pipeline.run_steps(make_context(tmp_path, toolchain=fake, spec_overrides=overrides))
    step = _step4(verdict)
    assert step.diagnostic is not None
    assert step.diagnostic.code == "kernel-replay-failed"
    assert "--fresh" not in step.diagnostic.message
    assert step.diagnostic.details["replay_mode"] == mode
    assert step.diagnostic.details["output"] == "kernel: bad"


@pytest.mark.parametrize(("overrides", "mode"), [({}, MODE_FRESH), (MATHLIB, MODE_PREFIX)])
def test_timeout_is_still_timeout(tmp_path: Path, overrides: dict[str, str], mode: str) -> None:
    verdict = pipeline.run_steps(
        make_context(tmp_path, toolchain=TimingOut(), spec_overrides=overrides)
    )
    assert verdict.first_failing_step == 4
    step = _step4(verdict)
    assert step.diagnostic is not None and step.diagnostic.code == "timeout"
    assert step.diagnostic.details["replay_mode"] == mode


# -- the real toolchain (lean tier) ---------------------------------------------------------------

DEF_FACT = "def Opn.fact : Nat → Nat\n  | 0 => 1\n  | n + 1 => (n + 1) * Opn.fact n\n"
NODE_PROOF = (
    "import Defs.Fact\n\n"
    "theorem Opn.fact_pos_one : 0 < Opn.fact 1 := by decide\n\n"
    "theorem Opn.and_swap : ∀ p q : Prop, p ∧ q → q ∧ p :=\n  fun _ _ h => ⟨h.2, h.1⟩\n"
)


@pytest.mark.lean
def test_prefix_replay_runs_on_the_real_toolchain(
    real_toolchain: LocalToolchain, pinned: ResolvedToolchain, tmp_path: Path
) -> None:
    """The non-fresh form over ``Nodes`` and ``Defs`` replays a graph-shaped build and passes;
    a prefix with no oleans is refused, which is why ``Defs`` is passed only when built."""
    real, tc = real_toolchain, pinned
    src, build = tmp_path / "src", tmp_path / "build"
    fact = src / "Defs" / "Fact.lean"
    proof = src / "Nodes" / TUTORIAL / "Proof.lean"
    for path, text in ((fact, DEF_FACT), (proof, NODE_PROOF)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    only_defs = real.elaborate(tc, fact, "Defs.Fact", build, root=src, timeout_s=120)
    assert only_defs.ok, only_defs
    no_nodes = real.kernel_replay(tc, ["Nodes"], [build], fresh=False, timeout_s=300)
    assert not no_nodes.ok  # leanchecker refuses a prefix with no oleans

    elab = real.elaborate(tc, proof, PROOF, build, root=src, timeout_s=120)
    assert elab.ok, elab
    mode, modules = replay_plan(MATHLIB, PROOF, build)
    assert (mode, modules) == (MODE_PREFIX, ["Nodes", "Defs"])
    result = real.kernel_replay(tc, modules, [build], fresh=False, timeout_s=300)
    assert result.ok, result.output

    fresh = real.kernel_replay(tc, [PROOF], [build], fresh=True, timeout_s=300)
    assert fresh.ok, fresh.output
