"""F02-T10, lean and docker tiers: a build output the contributor's compile left behind decides
nothing.

The fast tier (``test_finding_trusted_workspace.py``) pins the mounts: no judging call is handed
the work directory. This drives the real toolchain in the real sandbox and tampers with the work
directory between the contributor's compile and the judging calls, the way code running in that
compile could (an ``#eval`` that writes files), but from the test, so the fixture does not depend
on how a given Lean version lets elaboration reach the file system.

* The node's own compiled module is replaced by one declaring the statement's theorem with
  another type (``True``). It is the one input the judging calls take from the work directory,
  so it is caught by what they do with it: the meaning comparison (F08-T28) refuses it at step 4.
* A definition's olean is planted where the statement's own build lived before T10
  (``work/meaning/build/Defs/Base.olean``, which ``defs.compile_all`` would have taken as
  built), carrying the instance that makes a false statement read true, and a shadow of it
  beside the artifact's modules. The statement is built in the judging directory now, so the
  trap is refused exactly as when nothing was planted.

Both need the step-3 image and the pinned toolchain; they run in CI (``make verify-lean`` with
docker), not on a laptop without either.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from harness import make_context
from test_uses_defs_lean import BASE, context, submit

from opn_gate import layout, pipeline, sandbox
from opn_gate.sandbox import SandboxToolchain
from opn_gate.steps import RunContext
from opn_gate.toolchain import ElabResult, ResolvedToolchain

pytestmark = [pytest.mark.lean, pytest.mark.docker]

PIN = "leanprover/lean4:v4.33.1"
#: Only to construct the fixture; ``sandboxed`` replaces the seam with one at the spec's caps.
CAPS_UNUSED = sandbox.Caps(cpu=1.0, memory_mib=1024, wallclock_s=60)


class Tampering(SandboxToolchain):
    """The sandbox, with ``tamper`` run on the host after the node's own ``Proof`` compiles:
    whatever it writes is in the work directory when the judging calls run."""

    target_module: str = ""
    tamper: Callable[[Path], None] | None = None

    def elaborate(
        self,
        tc: ResolvedToolchain,
        source: Path,
        module: str,
        out_dir: Path,
        *,
        root: Path | None = None,
        timeout_s: float | None = None,
    ) -> ElabResult:
        result = super().elaborate(tc, source, module, out_dir, root=root, timeout_s=timeout_s)
        if result.ok and module == self.target_module and self.tamper is not None:
            self.tamper(out_dir)
        return result


def sandboxed(ctx: RunContext, image: str, node_id: str) -> Tampering:
    sbx = Tampering(image, sandbox.Caps.from_spec(ctx.spec), read_write=[ctx.workdir])
    sbx.target_module = layout.node_module(node_id, "Proof")
    ctx.toolchain = sbx
    return sbx


def compiled(sbx: Tampering, scratch: Path, module_rel: Path, module: str, text: str) -> Path:
    """``text`` compiled as ``module`` in the sandbox, in a directory of its own; its olean."""
    tc = sbx.resolve(PIN)
    src = scratch / "src"
    source = src / module_rel
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(text, encoding="utf-8")
    seam = sbx.scoped(read_write=[scratch])
    elab = seam.elaborate(tc, source, module, scratch / "build", root=src)
    assert elab.ok, ([m.as_dict() for m in elab.messages], elab.stderr)
    return scratch / "build" / module_rel.with_suffix(".olean")


def test_a_compiled_module_with_another_type_is_refused_at_step_4(
    tmp_path: Path, sandbox_image: str
) -> None:
    node_id = "and-swap-reassoc"
    ctx = make_context(tmp_path, node_id=node_id)
    sbx = sandboxed(ctx, sandbox_image, node_id)
    rel = Path("Nodes") / node_id / "Proof.lean"
    forged = compiled(
        sbx,
        tmp_path / "forged",
        rel,
        sbx.target_module,
        "theorem OpnProp.and_swap_reassoc : True := trivial\n",
    )

    def tamper(build: Path) -> None:
        (build / rel.with_suffix(".olean")).write_bytes(forged.read_bytes())

    sbx.tamper = tamper
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "fail", verdict.as_dict()
    assert verdict.first_failing_step == 4
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "statement-meaning-changed", verdict.diagnostic


#: ``Defs.Base`` with the trap's instance in it, named as ``Defs.Trap`` names its own.
PLANTED_BASE = BASE + "\ninstance (priority := high) : Opn.Size Nat := ⟨fun _ => 0⟩\n"


def test_a_definition_planted_in_the_work_directory_does_not_reach_the_statements_build(
    tmp_path: Path, sandbox_image: str
) -> None:
    ctx = context(tmp_path, "size-is-zero", sandbox.SandboxToolchain(sandbox_image, CAPS_UNUSED))
    sbx = sandboxed(ctx, sandbox_image, "size-is-zero")
    submit(ctx, "Defs.Trap", " by\n  intro n\n  rfl\n")
    planted = compiled(
        sbx, tmp_path / "planted", Path("Defs") / "Base.lean", "Defs.Base", PLANTED_BASE
    )

    def tamper(build: Path) -> None:
        work = build.parent
        for where in (work / "meaning" / "build", build):
            dest = where / "Defs" / "Base.olean"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(planted.read_bytes())

    sbx.tamper = tamper
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "fail", verdict.as_dict()
    assert verdict.first_failing_step == 4
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "statement-meaning-changed", verdict.diagnostic
