"""Elaborating the Lean exhibits an append carries (F08-R6, R7; D-8, D-16; C9).

A revision request or a defect claim may attach a Lean file as its evidence. The record itself
claims nothing a kernel could check, which is why it merges as an append (F07-R9) — but the
exhibit is contributor Lean, and contributor Lean runs only where the gate's sandbox runs it
(C9). So the append mode gets one build of its own, here: every exhibit elaborates, against the
node it is about, or the pull request fails naming the file.

Elaborating is all this asks. Whether the exhibit *shows* what the record says it shows is the
adjudicator's question (D-17), not the gate's; an exhibit that elaborates is admissible evidence,
and one that does not is noise.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from collections.abc import Sequence

from opn_gate import layout, modes
from opn_gate.diagnostic import Diagnostic
from opn_gate.paths import Located
from opn_gate.steps.base import RunContext
from opn_gate.steps.toolchain_step import ToolchainStep
from opn_gate.toolchain import ResolvedToolchain

log = logging.getLogger(__name__)

EXHIBIT_MODULE = "Exhibit"


def run(ctx: RunContext, records: Sequence[Located]) -> list[Diagnostic]:
    """Elaborate each record's exhibit; every failure is named, none is silent (C7)."""
    if not records:
        return []
    resolved = ToolchainStep().run(ctx)
    if not resolved.ok:
        assert resolved.diagnostic is not None
        return [resolved.diagnostic]
    tc: ResolvedToolchain = ctx.data["toolchain"]
    problems: list[Diagnostic] = []
    for index, located in enumerate(records):
        problem = elaborate_one(ctx, tc, located, index)
        if problem is not None:
            problems.append(problem)
    return problems


def elaborate_one(
    ctx: RunContext, tc: ResolvedToolchain, located: Located, index: int
) -> Diagnostic | None:
    """One exhibit, as the module ``Nodes.«<id>».Exhibit<n>`` when it is about a node — so it may
    import that node's Context and Statement — or as a bare module otherwise."""
    data = (ctx.graph_root / located.path).read_bytes()
    doc = modes._document(located, data)
    if isinstance(doc, Diagnostic):
        return doc
    text = modes.exhibit_of(located.role, doc)
    if text is None:
        return None
    src = ctx.workdir / "src"
    ctx.build_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{EXHIBIT_MODULE}{index}"
    if located.node_id is not None:
        staged = stage_node(ctx, tc, located.target_id, located.node_id)
        if staged is not None:
            return staged
        dest = src / "Nodes" / located.node_id / f"{stem}.lean"
        module = layout.node_module(located.node_id, stem)
    else:
        dest = src / f"{stem}.lean"
        module = stem
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    try:
        elab = ctx.toolchain.elaborate(
            tc, dest, module, ctx.build_dir, root=src, timeout_s=ctx.wallclock_s
        )
    except subprocess.TimeoutExpired:
        return Diagnostic(
            "exhibit-timeout",
            f"{located.path}: the exhibit exceeded the {ctx.wallclock_s:g}s wall-clock cap",
            {"path": located.path},
        )
    if not elab.ok:
        return Diagnostic(
            "exhibit-elaboration",
            f"{located.path}: the exhibit does not elaborate (F08-R6, R7)",
            {
                "path": located.path,
                "module": module,
                "messages": [m.as_dict() for m in elab.errors or elab.messages],
            },
        )
    log.info("exhibit %s elaborates as %s", located.path, module)
    return None


def stage_node(
    ctx: RunContext, tc: ResolvedToolchain, target_id: str, node_id: str
) -> Diagnostic | None:
    """Copy the node's ``Statement.lean`` and ``Context.lean`` under the work directory and
    compile the Context, so an exhibit may import either — the sandbox holds nothing else
    (F00-R12; the lesson of F08-Q13)."""
    node_dir = layout.graph_nodes_dir(ctx.graph_root, target_id) / node_id
    src = ctx.workdir / "src"
    dest = src / "Nodes" / node_id
    if (dest / "Context.lean").is_file():
        return None  # staged for an earlier exhibit of the same node
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("Statement.lean", "Context.lean"):
        source = node_dir / name
        if not source.is_file():
            return Diagnostic(
                "exhibit-node",
                f"{node_id} has no {name}; an exhibit is about a node that exists (D-3)",
                {"node": node_id, "missing": name},
            )
        shutil.copy(source, dest / name)
    module = layout.node_module(node_id, "Context")
    try:
        elab = ctx.toolchain.elaborate(
            tc, dest / "Context.lean", module, ctx.build_dir, root=src, timeout_s=ctx.wallclock_s
        )
    except subprocess.TimeoutExpired:
        return Diagnostic("exhibit-timeout", f"compiling {module} exceeded the wall-clock cap")
    if not elab.ok:
        return Diagnostic(
            "exhibit-node",
            f"{module} does not elaborate, so no exhibit about {node_id} can",
            {"node": node_id, "messages": [m.as_dict() for m in elab.errors or elab.messages]},
        )
    return None
