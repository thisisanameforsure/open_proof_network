"""Elaborating the Lean exhibits an append carries (F08-R6, R7; D-8, D-16; C9).

A revision request or a defect claim may attach a Lean file as its evidence. The record itself
claims nothing a kernel could check, which is why it merges as an append (F07-R9) — but the
exhibit is contributor Lean, and contributor Lean runs only where the gate's sandbox runs it
(C9). So the append mode gets one build of its own, here: every exhibit elaborates, against the
node it is about, or the pull request fails naming the file.

Elaborating is all this asks. Whether the exhibit *shows* what the record says it shows is the
adjudicator's question (D-17), not the gate's; an exhibit that elaborates is admissible evidence,
and one that does not is noise.

F08-T42 (D-12, D-16 v3.43): the one exception there was, a circularity claim whose exhibit had
to prove a stated implication, is retired; a claim of that class is refused here as in the
classifier, and no implication is judged.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from collections.abc import Sequence

from opn_gate import defs, layout, modes
from opn_gate.diagnostic import Diagnostic
from opn_gate.paths import Located
from opn_gate.records import CIRCULAR_CLASS
from opn_gate.steps.base import RunContext
from opn_gate.steps.toolchain_step import ToolchainStep
from opn_gate.toolchain import ResolvedToolchain

log = logging.getLogger(__name__)

EXHIBIT_MODULE = "Exhibit"
STATEMENT_MODULE = "Statement"
#: The modules of a node an exhibit about it may import: what the staging compiles for it
#: (``stage_node``), beside the
#: target's definitions. A node's Statement is copied but never compiled for an exhibit, so an
#: import of it does not elaborate here; the service's pre-flight reads this tuple (F13-T31).
EXHIBIT_NODE_MODULES: tuple[str, ...] = ("Context",)


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


def elaborate_one(  # noqa: PLR0911 — one return per way an exhibit is not admissible
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
    if located.role == "defect-claim" and (
        doc.get("class") == CIRCULAR_CLASS or doc.get("ancestor") is not None
    ):
        return Diagnostic(
            "defect-class-retired",
            f"{located.path}: the {CIRCULAR_CLASS} class was retired in decisions v3.43 (D-12, "
            "D-16); its exhibit is not judged",
            {"path": located.path, "class": doc.get("class")},
        )
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
    compile the modules ``EXHIBIT_NODE_MODULES`` names (the Context), so an exhibit may import
    it — the sandbox holds nothing else (F00-R12; the lesson of F08-Q13). The Statement is
    copied, not compiled: an exhibit that imports it does not elaborate (F13-T31)."""
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
    # F11-R2, F01-Q2: the target's definitions first; the Context may import them.
    target_dir = layout.gate_spec_path(ctx.graph_root, target_id).parent
    problem = defs.compile_all(
        ctx.toolchain, tc, target_dir, ctx.workdir, timeout_s=ctx.wallclock_s
    )
    if problem is not None:
        return problem
    for stem in EXHIBIT_NODE_MODULES:
        module = layout.node_module(node_id, stem)
        try:
            elab = ctx.toolchain.elaborate(
                tc,
                dest / f"{stem}.lean",
                module,
                ctx.build_dir,
                root=src,
                timeout_s=ctx.wallclock_s,
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
