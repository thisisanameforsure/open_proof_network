"""F02-T12: the judging programs that used to elaborate contributor files read compiled modules.

F02-T11 left four programs elaborating a contributor's file in the process that prints the
verdict, with initializers on: ``opn-witness-type`` (step 7), ``opn-used-constants`` (step 8),
``opn-artifact-type`` (a counterexample's or vacuity certificate's type, step 4's last word) and
``opn-relation-type`` (admission). Code in the file (``#eval``, ``initialize``, a macro) ran
there, after the nonce was read but in the same address space. Now:

* the contributor's file is compiled in a call of its own, whose only writable directory is a
  scratch area beside the judging directory (``judging.compile_contributed``); or, for step 8 and
  the artifact's type, it is the ``Proof`` module step 4 already compiled and replayed;
* the judging call is handed no source of the contributor's, mounts the judging directory
  read-only and nothing writable, and reads the compiled module from there: imported with nothing
  of it executed, or added constant by constant through the kernel.

The sandbox is the recording stand-in of ``test_finding_trusted_workspace.py``, answering each
binary as the real one would and logging the mounts each call was given; the lean tier
(``test_finding_compiled_judges_lean.py``) drives the real programs.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from fakes import FakeToolchain, artifact_result, relation_result, witness_result
from harness import make_context, node_dir
from test_admit import VARIANT_WITNESS, context_for
from test_finding_trusted_workspace import CAPS, LIBDIR, NODE, PIN, Call, under

from opn_gate import admit, judging, pipeline
from opn_gate.sandbox import SandboxToolchain
from opn_gate.steps import RunContext, default_steps
from opn_gate.toolchain import (
    VERDICT_TAG,
    ArtifactRequest,
    MetaprogramResult,
    RelationRequest,
    ResolvedToolchain,
)

JUDGES = ("opn-witness-type", "opn-used-constants")


class Recording(SandboxToolchain):
    """Every process answered as the real one would, and logged with its mounts."""

    log: list[Call]

    def _exec(
        self,
        cmd: Sequence[str],
        *,
        cwd: Path | None = None,
        extra_env: dict[str, str] | None = None,
        timeout_s: float | None = None,
        **kwargs: Any,
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
        elif "-o" in cmd:
            olean = Path(cmd[cmd.index("-o") + 1])
            olean.parent.mkdir(parents=True, exist_ok=True)
            olean.write_bytes(b"olean")
        elif "opn-statement-meaning" in joined:
            out = json.dumps({"ok": True, "identical": True, "matches": True})
        elif "opn-axioms" in joined:
            out = json.dumps({"ok": True, "decl": "OpnProp.and_swap_reassoc", "axioms": []})
        elif "opn-hazards" in joined:
            out = json.dumps({"ok": True, "checkers": [], "findings": [], "capped": False})
        elif "opn-witness-type" in joined:
            doc = {"ok": True, "expected": "∃ p q r, (p ∧ q) ∧ r", "defeq": True}
            out = json.dumps({**doc, "witness": doc["expected"], "witness_axioms": []})
        elif "opn-used-constants" in joined:
            out = json.dumps({"ok": True, "decl": "x", "constants": [], "axioms": []})
        stdin = kwargs.get("stdin")
        if isinstance(stdin, str) and out.startswith("{"):
            out = f"{VERDICT_TAG} {stdin.strip()} {out}\n"
        return subprocess.CompletedProcess(cmd, 0, out, "")


def run_to_step_8(tmp_path: Path) -> tuple[RunContext, Recording]:
    ctx = make_context(tmp_path, node_id=NODE)
    rec = Recording("opn-gate:test", CAPS, read_write=[ctx.workdir])
    rec.log = []
    ctx.toolchain = rec
    verdict = pipeline.run_steps(ctx, [s for s in default_steps() if s.number <= 8])
    assert verdict.ok, verdict.as_dict()
    return ctx, rec


def test_no_judging_program_is_handed_a_contributor_source_or_a_writable_mount(
    tmp_path: Path,
) -> None:
    """Step 7's and step 8's programs read compiled modules, read-only, from the judging
    directory; neither is given a ``.lean`` file or anything under the work directory."""
    ctx, rec = run_to_step_8(tmp_path)
    work = ctx.workdir.resolve()
    judge_root = judging.root_for(ctx.workdir).resolve()
    asked = [c for c in rec.log if any(j in c.joined for j in JUDGES)]
    assert {j for j in JUDGES if any(j in c.joined for c in asked)} == set(JUDGES), [
        c.joined for c in rec.log
    ]
    for call in asked:
        sources = [a for a in call.cmd if a.endswith(".lean")]
        assert not sources, (call.joined, sources)
        assert "--file" not in call.cmd and "--witness" not in call.cmd, call.joined
        assert not [a for a in call.cmd if under(Path(a), work)], call.joined
        assert call.read_write == [], call.joined
        assert call.read_only, call.joined
        for root in call.read_only:
            assert under(root, judge_root), (call.joined, root)
        for entry in call.lean_path:
            assert not under(entry, work), (call.joined, entry)


def test_the_witness_is_compiled_apart_and_read_as_data(tmp_path: Path) -> None:
    """The witness is compiled by a call that can write only its own scratch area, and the
    program reads the olean taken from it at its path in ``contributed/``, which is mounted
    read-only and is not on the program's ``LEAN_PATH``."""
    ctx, rec = run_to_step_8(tmp_path)
    work = ctx.workdir.resolve()
    judge_root = judging.root_for(ctx.workdir).resolve()
    compiles = [
        c
        for c in rec.log
        if "-o" in c.cmd and c.cmd[c.cmd.index("-o") + 1].endswith("Witness.olean")
    ]
    assert len(compiles) == 1, [c.joined for c in rec.log]
    compile_ = compiles[0]
    assert compile_.read_only == []
    assert compile_.read_write and all(
        under(r, judge_root) and not under(r, work) for r in compile_.read_write
    )
    (call,) = [c for c in rec.log if "opn-witness-type" in c.joined]
    olean = Path(call.cmd[call.cmd.index("--witness-olean") + 1])
    assert judging.CONTRIBUTED_DIR in olean.parts and under(olean, judge_root)
    assert olean.is_file()
    assert not [p for p in call.lean_path if under(olean, p)], call.lean_path
    assert any(under(olean, r) for r in call.read_only)
    # nothing the witness's compile could write is mounted for the judgment
    for root in compile_.read_write:
        assert not [r for r in call.read_only if under(r, root) or under(root, r)]


class Requests(FakeToolchain):
    """The fake seam, keeping every artifact and relation request."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.artifact_requests: list[ArtifactRequest] = []
        self.relation_requests: list[RelationRequest] = []

    def artifact_type(
        self,
        tc: ResolvedToolchain,
        req: ArtifactRequest,
        search_path: Sequence[Path],
        *,
        timeout_s: float | None = None,
    ) -> MetaprogramResult:
        self.artifact_requests.append(req)
        return super().artifact_type(tc, req, search_path, timeout_s=timeout_s)

    def relation_type(
        self,
        tc: ResolvedToolchain,
        req: RelationRequest,
        search_path: Sequence[Path],
        *,
        timeout_s: float | None = None,
    ) -> MetaprogramResult:
        self.relation_requests.append(req)
        return super().relation_type(tc, req, search_path, timeout_s=timeout_s)


def test_a_counterexample_is_judged_from_compiled_modules(tmp_path: Path) -> None:
    """F08-T29b: a counterexample's ``¬ S`` is compared from the statement's olean in the
    judging directory and the artifact's compiled module; its source is not an argument."""
    decl = "OpnProp.and_swap_reassoc_refuted"
    fake = Requests(
        artifact=artifact_result(kind="counterexample", decl=decl, expected="¬S", declared="¬S")
    )
    ctx = make_context(tmp_path, node_id=NODE, toolchain=fake)
    proof = node_dir(ctx) / "Proof.lean"
    statement = (node_dir(ctx) / "Statement.lean").read_text(encoding="utf-8")
    proof.write_text(
        statement.replace("theorem OpnProp.and_swap_reassoc :", f"theorem {decl} : ¬").replace(
            "sorry", "by\n  sorry"
        ),
        encoding="utf-8",
    )
    pipeline.run_steps(ctx, [s for s in default_steps() if s.number <= 4])
    assert fake.artifact_requests, fake.calls
    (req,) = fake.artifact_requests
    judge_root = judging.root_for(ctx.workdir).resolve()
    assert req.statement_olean is not None and under(req.statement_olean.resolve(), judge_root)
    assert not [a for a in req.args() if a.endswith(".lean")], req.args()


def test_the_relation_proof_is_compiled_apart(tmp_path: Path) -> None:
    """Admission hands ``opn-relation-type`` the relation proof's olean from ``contributed/``
    and the statements' oleans from the judging directory, never a source."""
    fake = Requests(
        relation=relation_result(),
        witness=witness_result(expected=VARIANT_WITNESS, witness=VARIANT_WITNESS),
    )
    ctx = context_for(tmp_path, "variant-resolves", toolchain=fake)
    admission = admit.run(ctx)
    assert admission.admitted, admission.as_dict()
    assert fake.relation_requests, fake.calls
    (req,) = fake.relation_requests
    judge_root = judging.root_for(ctx.workdir).resolve()
    for olean in (req.relation_olean, req.variant_olean, req.root_olean):
        assert olean is not None and under(olean.resolve(), judge_root), req
    assert judging.CONTRIBUTED_DIR in req.relation_olean.parts  # type: ignore[union-attr]
    assert not [a for a in req.args() if a.endswith(".lean")], req.args()
