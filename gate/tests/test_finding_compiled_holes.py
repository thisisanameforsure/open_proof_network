"""F02-T13: a partial proof's (and a reduction's) holes are read from compiled modules.

After F02-T12 one judging program still elaborated a contributor's file in the process that
prints the verdict: ``opn-artifact-type`` for a partial, which elaborated the assembly from the
work directory (``--artifact <Proof.lean>``, with the work directory's build on its search path)
to extract its holes. An ``#eval`` or ``initialize`` in the assembly then ran beside the hole
report, behind T11's nonce only, and could forge the holes: their names, closed types and the
offload rule's answers (``defeq_goal``, ``defeq_sibling``, ``defeq_ancestor``, the round trip).

Now the program is handed the assembly's olean, the one step 4 compiled and the kernel replayed,
from the judging directory's ``modules/``, and the statement's olean built there from the node's
own files: no contributor source, nothing under the work directory, nothing writable, and the
contributor modules' directory never on its ``LEAN_PATH`` (they are read by path as data and
added through the kernel). The sibling and ancestor probes, statement text of record, are staged
in the judging directory too.

The sandbox is the recording stand-in of ``test_finding_compiled_judges.py``; the lean tier
(``test_finding_compiled_holes_lean.py``) drives the real program.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import test_finding_compiled_judges as judges
from fakes import FakeToolchain, artifact_result
from test_finding_trusted_workspace import CAPS, Call, under
from test_partial import HOLES, ROOT, WITNESS, partial_context

from opn_gate import judging, layout, pipeline
from opn_gate.steps import RunContext, default_steps
from opn_gate.toolchain import VERDICT_TAG

#: What the recording sandbox answers for ``opn-artifact-type``: a partial with the two holes.
PARTIAL_DOC = artifact_result(holes=HOLES, decl="OpnProp.and_swap_reassoc").doc


class Recording(judges.Recording):
    """The recording sandbox, answering ``opn-artifact-type`` as well."""

    def _exec(
        self,
        cmd: Sequence[str],
        *,
        cwd: Path | None = None,
        extra_env: dict[str, str] | None = None,
        timeout_s: float | None = None,
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        if "opn-artifact-type" not in " ".join(cmd):
            return super()._exec(cmd, cwd=cwd, extra_env=extra_env, timeout_s=timeout_s, **kwargs)
        env = extra_env or {}
        lean_path = [Path(p) for p in env.get("LEAN_PATH", "").split(":") if p]
        mounted = [*self.read_only, *self.read_write]
        visible = sorted(p for root in mounted if root.is_dir() for p in root.rglob("*"))
        self.log.append(
            Call(list(cmd), list(self.read_only), list(self.read_write), lean_path, visible)
        )
        stdin = kwargs.get("stdin")
        out = f"{VERDICT_TAG} {str(stdin).strip()} {json.dumps(PARTIAL_DOC)}\n"
        return subprocess.CompletedProcess(list(cmd), 0, out, "")


def run_partial_to_step_4(tmp_path: Path) -> tuple[RunContext, Recording, Call]:
    ctx, _stamp = partial_context(
        tmp_path, toolchain=FakeToolchain(witness=WITNESS, artifact=artifact_result(holes=HOLES))
    )
    rec = Recording("opn-gate:test", CAPS, read_write=[ctx.workdir])
    rec.log = []
    ctx.toolchain = rec
    verdict = pipeline.run_steps(ctx, [s for s in default_steps() if s.number <= 4])
    assert verdict.ok, verdict.as_dict()
    asked = [c for c in rec.log if "opn-artifact-type" in c.joined]
    assert len(asked) == 1, [c.joined for c in rec.log]
    return ctx, rec, asked[0]


def test_the_hole_extraction_is_handed_no_source_and_nothing_writable(tmp_path: Path) -> None:
    """The partial's artifact-type call names no ``.lean`` file and nothing under the work
    directory, mounts only the judging directory and only read-only, and searches no directory
    the contributor's compile could write."""
    ctx, _rec, call = run_partial_to_step_4(tmp_path)
    work = ctx.workdir.resolve()
    judge_root = judging.root_for(ctx.workdir).resolve()
    assert not [a for a in call.cmd if a.endswith(".lean")], call.joined
    assert "--artifact" not in call.cmd and "--statement" not in call.cmd, call.joined
    assert not [a for a in call.cmd if under(Path(a), work)], call.joined
    assert call.read_write == [], call.joined
    assert call.read_only, call.joined
    for root in call.read_only:
        assert under(root, judge_root), (call.joined, root)
    for entry in call.lean_path:
        assert not under(entry, work), (call.joined, entry)


def test_the_assembly_is_read_from_the_module_step_4_replayed(tmp_path: Path) -> None:
    """The program receives the assembly's olean from the judging directory's ``modules/`` (what
    the kernel replay read), and that directory, from which the deps' modules are read by path,
    is never on its ``LEAN_PATH``: only the statement's own build, from the node's files, is."""
    ctx, _rec, call = run_partial_to_step_4(tmp_path)
    judge = judging.root_for(ctx.workdir).resolve()
    modules = judge / judging.MODULES_DIR
    olean = Path(call.cmd[call.cmd.index("--artifact-olean") + 1])
    assert olean == modules / "Nodes" / ROOT / "Proof.olean", call.joined
    assert olean.is_file()
    assert Path(call.cmd[call.cmd.index("--modules") + 1]) == modules, call.joined
    stmt = Path(call.cmd[call.cmd.index("--statement-olean") + 1])
    assert under(stmt, judge / judging.STATEMENT_DIR), call.joined
    assert stmt.is_file()
    assert call.cmd[call.cmd.index("--artifact-module") + 1] == layout.node_module(ROOT, "Proof")
    for entry in call.lean_path:
        assert not under(entry, modules), (call.joined, entry)
    assert any(under(modules, r) for r in call.read_only), call.joined


def test_the_probes_are_staged_in_the_judging_directory(tmp_path: Path) -> None:
    """The sibling probes (statement text of record) are written where the judgment reads them,
    beside the judging directory's other inputs, not in the work directory."""
    ctx, _rec, call = run_partial_to_step_4(tmp_path)
    judge_root = judging.root_for(ctx.workdir).resolve()
    assert "--siblings" in call.cmd, call.joined
    manifest = Path(call.cmd[call.cmd.index("--siblings") + 1])
    assert under(manifest, judge_root) and manifest.is_file(), call.joined
    assert any(under(manifest, r) for r in call.read_only), call.joined
