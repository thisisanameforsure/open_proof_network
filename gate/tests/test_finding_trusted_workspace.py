"""F02-T10: the judging calls run in a workspace the contributor's compile never wrote to.

The step-3 sandbox runs every process in a fresh container, but until T10 every call was handed
the same writable work directory, copied in before and copied back after. So the call that
compiles a contributor's ``Proof.lean`` (whose elaboration may run arbitrary code: ``#eval``,
``run_cmd``, a macro) could write anything anywhere under it, and the calls that judge the
artifact read from it afterwards: the statement's own build (``work/meaning``, whose definitions
``defs.compile_all`` skips when an olean is already there), the meaning comparison, the axioms
probe and the kernel replay, each with ``work/build`` first on ``LEAN_PATH``, where an olean
named ``Init.*`` or ``Mathlib.*`` shadows the real one and, on a Mathlib pin, is never replayed.

The guarantee T10 establishes: the verdict that an artifact proves its statement is derived only
from the kernel replay of the compiled modules and the comparison of the compiled declaration's
type with the statement's, built from the admitted files, in processes and a directory the
contributor's code never ran in or wrote to. The contributor's compiled graph modules are the one
input taken from the work directory, copied by name into a fresh judging directory and handed
to the judging calls read-only.

The sandbox is a recording stand-in: ``SandboxToolchain`` with ``_exec`` answering as the real
binaries would and logging the mounts each call was given, so the container assembly is what is
asserted while nothing runs in a container. The docker and lean tiers drive the real thing
(``test_finding_trusted_workspace_lean.py``).
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from harness import make_context

from opn_gate import layout, pipeline
from opn_gate.sandbox import Caps, SandboxToolchain
from opn_gate.steps import RunContext, default_steps

CAPS = Caps(cpu=1.0, memory_mib=1024, wallclock_s=60)
PIN = "leanprover/lean4:v4.33.1"
NODE = "and-swap-reassoc"  # two proved dependencies
LIBDIR = Path("/opt/elan/toolchains/x/lib/lean")
#: What a contributor's elaboration leaves behind when it writes outside its own olean.
SHADOW = Path("Init") / "Prelude.olean"
PLANTED_DEF = Path("Defs") / "Planted.olean"


@dataclass
class Call:
    cmd: list[str]
    read_only: list[Path]
    read_write: list[Path]
    lean_path: list[Path]
    #: the files under every mounted directory, as the container would see them
    visible: list[Path] = field(default_factory=list)

    @property
    def joined(self) -> str:
        return " ".join(self.cmd)


class Recording(SandboxToolchain):
    """Every process answered as the real one would, and logged with its mounts."""

    log: list[Call]
    workdir: Path

    def _exec(
        self,
        cmd: Sequence[str],
        *,
        cwd: Path | None = None,
        extra_env: dict[str, str] | None = None,
        timeout_s: float | None = None,
        **_kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        cmd = list(cmd)
        env = extra_env or {}
        lean_path = [Path(p) for p in env.get("LEAN_PATH", "").split(":") if p]
        mounted = [*self.read_only, *self.read_write]
        visible = sorted(p for root in mounted if root.is_dir() for p in root.rglob("*"))
        self.log.append(Call(cmd, list(self.read_only), list(self.read_write), lean_path, visible))
        joined = " ".join(cmd)
        out = ""
        if "toolchain list" in joined:
            out = f"{PIN}\n"
        elif "lean --version" in joined:
            out = "Lean (version 4.33.1, x86_64-unknown-linux-gnu, commit 819816b2e0a3, Release)\n"
        elif "lean --githash" in joined:
            out = "819816b2e0a3bf405af45ae5c7af2491d8f5bee6\n"
        elif "lean --print-libdir" in joined:
            out = f"{LIBDIR}\n"
        elif "-o" in cmd:  # `lean --json -o <olean> -i <ilean> <file>`
            olean = Path(cmd[cmd.index("-o") + 1])
            olean.parent.mkdir(parents=True, exist_ok=True)
            olean.write_bytes(b"olean")
            if olean.name == "Proof.olean" and f"/{NODE}/" in olean.as_posix():
                # the contributor's elaboration writes beside its own module
                build = self.workdir / "build"
                for planted in (SHADOW, PLANTED_DEF):
                    (build / planted).parent.mkdir(parents=True, exist_ok=True)
                    (build / planted).write_bytes(b"planted")
        elif "OpnAxioms.lean" in joined:
            out = "'OpnProp.and_swap_reassoc' does not depend on any axioms\n"
        elif "opn-statement-meaning" in joined:
            out = json.dumps({"ok": True, "identical": True, "matches": True}) + "\n"
        elif "opn-axioms" in joined:
            out = json.dumps({"ok": True, "decl": "OpnProp.and_swap_reassoc", "axioms": []})
        return subprocess.CompletedProcess(cmd, 0, out, "")


def recording(ctx: RunContext) -> Recording:
    rec = Recording("opn-gate:test", CAPS, read_write=[ctx.workdir])
    rec.log = []
    rec.workdir = ctx.workdir.resolve()
    return rec


def under(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def run_to_step_5(tmp_path: Path) -> tuple[RunContext, Recording]:
    ctx = make_context(tmp_path, node_id=NODE)
    rec = recording(ctx)
    ctx.toolchain = rec
    verdict = pipeline.run_steps(ctx, [s for s in default_steps() if s.number <= 5])
    assert verdict.ok, verdict.as_dict()
    return ctx, rec


def test_no_judging_call_can_write_to_or_read_from_the_contributors_work_directory(
    tmp_path: Path,
) -> None:
    ctx, rec = run_to_step_5(tmp_path)
    work = ctx.workdir.resolve()
    build = work / "build"
    contributor = [
        c for c in rec.log if "-o" in c.cmd and under(Path(c.cmd[c.cmd.index("-o") + 1]), build)
    ]
    assert contributor, "the artifact's own build ran"
    asked = [
        c
        for c in rec.log
        if any(k in c.joined for k in ("leanchecker", "opn-statement-meaning", "OpnAxioms"))
        or "opn-axioms" in c.joined
        or ("-o" in c.cmd and not under(Path(c.cmd[c.cmd.index("-o") + 1]), build))
    ]
    names = [c.joined for c in asked]
    assert any("leanchecker" in n for n in names)
    assert any("opn-statement-meaning" in n for n in names)
    assert any("OpnAxioms" in n or "opn-axioms" in n for n in names)
    assert any("Statement.olean" in n for n in names)
    for call in asked:
        # nothing it may write is the contributor's, and the contributor's is not writable
        for root in call.read_write:
            assert not under(root, work) and not under(work, root), (call.joined, root)
        # what it reads is mounted outside the work directory
        for root in call.read_only:
            assert not under(root, work) and not under(work, root), (call.joined, root)
        for entry in call.lean_path:
            assert not under(entry, work), (call.joined, entry)


def test_the_judging_directory_holds_only_the_graphs_compiled_modules_and_is_fresh(
    tmp_path: Path,
) -> None:
    """A file left in the judging directory by an earlier run, and a module the contributor's
    elaboration planted beside its own (a shadow of ``Init.Prelude``, a ``Defs`` module no
    definition file declares), are never seen by a judging call."""
    ctx = make_context(tmp_path, node_id=NODE)
    stale = ctx.workdir.parent / f"{ctx.workdir.name}.judge" / "modules" / "Init" / "Stale.olean"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"stale")
    rec = recording(ctx)
    ctx.toolchain = rec
    verdict = pipeline.run_steps(ctx, [s for s in default_steps() if s.number <= 5])
    assert verdict.ok, verdict.as_dict()
    replay = [c for c in rec.log if "leanchecker" in c.joined]
    assert replay
    for call in replay:
        oleans = [p for p in call.visible if p.suffix == ".olean"]
        assert oleans
        assert not [p for p in oleans if p.name in ("Stale.olean", "Prelude.olean")]
        assert not [p for p in oleans if p.name == "Planted.olean"]
        for olean in oleans:
            rel = next(olean.relative_to(r) for r in call.read_only if under(olean, r))
            assert rel.parts[0] in (layout.NODES_PREFIX, layout.DEFS_PREFIX), olean
