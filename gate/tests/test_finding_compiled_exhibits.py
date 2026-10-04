"""F02-T14: a defect claim's exhibit is judged from compiled modules (decisions v3.27 §1).

F02-T12 converted admission's relation check and left one program elaborating contributor Lean in
the process that prints the verdict: ``opn-gate exhibits`` checks a circularity claim's exhibit
(F08-T17, F08-T21) with ``opn-relation-type --relation <exhibit.lean>``, which elaborates the
exhibit there with initializers on (``#eval``, ``run_cmd``, a macro run after the nonce is read,
in the verdict's address space), and reads the nodes' staged copies and the build under the work
directory, which the exhibit's own compile could write. Now, as admission does:

* the two statements are built from their files of record in a judging area of their own;
* the exhibit is compiled in a call of its own, writable only in that area's scratch directory,
  under a header the gate writes (the statements' imports, with the target's definitions and the
  two nodes' Contexts the only graph modules it may add, as the staging allowed before);
* ``opn-relation-type`` is handed the oleans only, mounts them read-only and nothing writable,
  and adds the exhibit's constants through the kernel (``replayInto``), executing nothing of it.

Every other exhibit (a revision request's, a defect claim of another class) is judged by its own
compile and nothing else: "it elaborates" is the whole claim (F08-R6), so there is no verdict
process to convert. That path is pinned unchanged here.

The sandbox is the recording stand-in of ``test_finding_compiled_judges.py``; the lean tier
(``test_finding_compiled_exhibits_lean.py``) drives the real program.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from harness import TARGET, copy_graph
from test_finding_circular_decomposition import ANCESTOR, EXHIBIT, HOLE, file_claim
from test_finding_compiled_judges import Recording as JudgesRecording
from test_finding_compiled_judges import Requests
from test_finding_trusted_workspace import CAPS, Call, under

from opn_gate import config, exhibits, judging, layout, modes, schemas
from opn_gate.diagnostic import Diagnostic
from opn_gate.paths import Change, Claim
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import VERDICT_TAG, Toolchain

RELATION = "opn-relation-type"


class Recording(JudgesRecording):
    """``test_finding_compiled_judges``' stand-in, answering ``opn-relation-type`` too."""

    def _exec(
        self,
        cmd: Sequence[str],
        *,
        cwd: Path | None = None,
        extra_env: dict[str, str] | None = None,
        timeout_s: float | None = None,
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        if RELATION not in " ".join(cmd):
            return super()._exec(cmd, cwd=cwd, extra_env=extra_env, timeout_s=timeout_s, **kwargs)
        proc = super()._exec(cmd, cwd=cwd, extra_env=extra_env, timeout_s=timeout_s, **kwargs)
        doc = {
            "ok": True,
            "label": "resolves",
            "decl": "circular",
            "expected": "H → A",
            "declared": "H → A",
            "matches": True,
            "axioms": [],
        }
        stdin = kwargs.get("stdin")
        nonce = stdin.strip() if isinstance(stdin, str) else ""
        return subprocess.CompletedProcess(
            proc.args, 0, f"{VERDICT_TAG} {nonce} {json.dumps(doc)}\n", ""
        )


def context(root: Path, workdir: Path, toolchain: Toolchain, rel: str) -> RunContext:
    classification = modes.classify([Change("A", rel)])
    spec_path = layout.gate_spec_path(root, TARGET)
    return RunContext(
        graph_root=root,
        claim=Claim(TARGET, classification.node_id or ""),
        spec=schemas.load_json(spec_path, "gate-spec/v1"),
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=None,
        workdir=workdir,
        toolchain=toolchain,
        settings=config.load({}),
    )


def run(ctx: RunContext, rel: str) -> list[Diagnostic]:
    classification = modes.classify([Change("A", rel)])
    return exhibits.run(ctx, modes.exhibits(ctx.graph_root, classification))


def recorded(tmp_path: Path, **claim: Any) -> tuple[RunContext, Recording, list[Diagnostic]]:
    root = copy_graph(tmp_path)
    rel = file_claim(root, **claim)
    workdir = tmp_path / "work"
    rec = Recording("opn-gate:test", CAPS, read_write=[workdir])
    rec.log = []
    ctx = context(root, workdir, rec, rel)
    return ctx, rec, run(ctx, rel)


def test_the_exhibit_judgment_is_handed_no_contributor_source_or_writable_mount(
    tmp_path: Path,
) -> None:
    """The defect: ``opn-relation-type`` was given ``--relation <exhibit.lean>`` and the two
    staged statements under the work directory, with the work directory mounted writable, so the
    exhibit's code ran in the call that prints the verdict."""
    ctx, rec, found = recorded(tmp_path)
    assert found == [], found
    work = ctx.workdir.resolve()
    judge_root = judging.root_for(ctx.workdir).resolve()
    asked = [c for c in rec.log if RELATION in c.joined]
    assert len(asked) == 1, [c.joined for c in rec.log]
    (call,) = asked
    sources = [a for a in call.cmd if a.endswith(".lean")]
    assert not sources, (call.joined, sources)
    assert "--relation" not in call.cmd and "--variant" not in call.cmd, call.joined
    assert not [a for a in call.cmd if under(Path(a), work)], call.joined
    assert call.read_write == [], call.joined
    assert call.read_only, call.joined
    for root in call.read_only:
        assert under(root, judge_root), (call.joined, root)
    for entry in call.lean_path:
        assert not under(entry, work), (call.joined, entry)


def test_the_exhibit_is_compiled_apart_and_read_as_data(tmp_path: Path) -> None:
    """The exhibit's one compile can write only its own scratch area; the program reads the olean
    taken from it in ``contributed/``, mounted read-only and not on its ``LEAN_PATH``, and nothing
    that compile could write is mounted for the judgment."""
    ctx, rec, found = recorded(tmp_path)
    assert found == [], found
    work = ctx.workdir.resolve()
    judge_root = judging.root_for(ctx.workdir).resolve()
    stem = f"{exhibits.EXHIBIT_MODULE}0.olean"
    compiles: list[Call] = [
        c for c in rec.log if "-o" in c.cmd and c.cmd[c.cmd.index("-o") + 1].endswith(stem)
    ]
    assert len(compiles) == 1, [c.joined for c in rec.log]
    (compile_,) = compiles
    assert compile_.read_only == []
    assert compile_.read_write
    assert all(under(r, judge_root) and not under(r, work) for r in compile_.read_write)
    (call,) = [c for c in rec.log if RELATION in c.joined]
    olean = Path(call.cmd[call.cmd.index("--relation-olean") + 1])
    assert judging.CONTRIBUTED_DIR in olean.parts and under(olean, judge_root)
    assert olean.is_file()
    assert not [p for p in call.lean_path if under(olean, p)], call.lean_path
    for root in compile_.read_write:
        assert not [r for r in call.read_only if under(r, root) or under(root, r)]


def test_the_statements_are_built_from_the_record_not_the_work_directory(tmp_path: Path) -> None:
    """Both statements' oleans come from the judging area's own build of the graph's files, and
    the request names the hole as the variant and the ancestor as the root (F08-T21)."""
    root = copy_graph(tmp_path)
    rel = file_claim(root)
    fake = Requests()
    ctx = context(root, tmp_path / "work", fake, rel)
    assert run(ctx, rel) == []
    (req,) = fake.relation_requests
    judge_root = judging.root_for(ctx.workdir).resolve()
    for olean in (req.relation_olean, req.variant_olean, req.root_olean):
        assert olean is not None, req
        assert under(olean.resolve(), judge_root), req
    assert req.variant_olean is not None and req.root_olean is not None
    assert (req.variant_olean.parent.name, req.variant_olean.name) == (
        HOLE,
        "Statement.olean",
    )
    assert (req.root_olean.parent.name, req.root_olean.name) == (
        ANCESTOR,
        "Statement.olean",
    )
    assert req.label == exhibits.CIRCULAR_LABEL
    assert not [a for a in req.args() if a.endswith(".lean")], req.args()


@pytest.mark.parametrize(
    ("module", "allowed"),
    [
        (f"Nodes.«{HOLE}».Context", True),
        (f"Nodes.«{ANCESTOR}».Context", True),
        (f"Nodes.«{HOLE}».Statement", False),
        ("Nodes.«tutorial-and-swap».Context", False),
    ],
)
def test_the_graph_modules_an_exhibit_may_import_are_what_staging_gave_it(
    tmp_path: Path, module: str, *, allowed: bool
) -> None:
    """Verdicts unchanged: the staging compiled the target's definitions and the two nodes'
    Contexts and nothing else, so an exhibit importing any other graph module did not elaborate.
    The compiled header admits exactly those, and refuses the rest by name before compiling."""
    root = copy_graph(tmp_path)
    rel = file_claim(root, exhibit=f"import {module}\n\n{EXHIBIT}")
    fake = Requests()
    ctx = context(root, tmp_path / "work", fake, rel)
    found = run(ctx, rel)
    if allowed:
        assert found == [], found
        (req,) = fake.relation_requests
        assert module in req.imports
    else:
        assert [d.code for d in found] == ["exhibit-elaboration"], found
        assert module in found[0].message
        assert not fake.relation_requests


def test_a_hole_context_that_does_not_elaborate_is_still_named(tmp_path: Path) -> None:
    """``exhibit-node`` as before: the claim names the node whose Context fails."""
    root = copy_graph(tmp_path)
    rel = file_claim(root)
    from scripted import ScriptedToolchain  # noqa: PLC0415 — one test's seam

    fake = ScriptedToolchain(failing_modules={f"Nodes.«{HOLE}».Context"})
    found = run(context(root, tmp_path / "work", fake, rel), rel)
    assert [d.code for d in found] == ["exhibit-node"], found
    assert found[0].details["node"] == HOLE
    assert not any(c.startswith("relation_type") for c in fake.calls)


def test_the_exhibit_timeout_is_named(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    rel = file_claim(root)
    from scripted import ScriptedToolchain  # noqa: PLC0415 — one test's seam

    module = layout.node_module(HOLE, f"{exhibits.EXHIBIT_MODULE}0")
    fake = ScriptedToolchain(timeout_modules={module})
    found = run(context(root, tmp_path / "work", fake, rel), rel)
    assert [d.code for d in found] == ["exhibit-timeout"], found
    assert found[0].details == {"path": rel}
