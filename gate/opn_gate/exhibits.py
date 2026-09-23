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
from pathlib import Path
from typing import Any

from opn_gate import defs, layout, modes
from opn_gate.diagnostic import Diagnostic
from opn_gate.paths import Located
from opn_gate.records import CIRCULAR_CLASS
from opn_gate.steps.axioms import SORRY_AXIOM
from opn_gate.steps.base import RunContext
from opn_gate.steps.toolchain_step import ToolchainStep
from opn_gate.toolchain import MetaprogramResult, RelationRequest, ResolvedToolchain

log = logging.getLogger(__name__)

EXHIBIT_MODULE = "Exhibit"
STATEMENT_MODULE = "Statement"
#: F08-T17: D-30's ``resolves`` is ``variant → root``; with the ancestor as the variant and the
#: claimed node as the root it is the implication a circularity claim asserts.
CIRCULAR_LABEL = "resolves"


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
    circular = located.role == "defect-claim" and doc.get("class") == CIRCULAR_CLASS
    decl: str | None = None
    if circular:
        declared = layout.parse_declaration(text, f"{located.path}'s exhibit")
        if isinstance(declared, Diagnostic):
            return Diagnostic(
                "circular-exhibit",
                f"{declared.message}: a {CIRCULAR_CLASS} exhibit is the one theorem "
                "`<ancestor's statement> → <this node's statement>` (F08-T17)",
                {"path": located.path, **(declared.details or {})},
            )
        decl = declared
    src = ctx.workdir / "src"
    ctx.build_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{EXHIBIT_MODULE}{index}"
    if located.node_id is not None:
        staged = stage_node(ctx, tc, located.target_id, located.node_id)
        if staged is None and circular:
            # F08-T17: the ancestor too, before the exhibit elaborates — it may import the
            # ancestor's Context, and the relation check reads the ancestor's staged statement.
            staged = stage_node(ctx, tc, located.target_id, str(doc.get("ancestor")))
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
    if decl is not None:
        return check_circular(ctx, tc, located, doc, exhibit=dest, module=module, decl=decl)
    return None


def check_circular(  # noqa: PLR0913 — the run, the seam, the record and the staged exhibit
    ctx: RunContext,
    tc: ResolvedToolchain,
    located: Located,
    doc: dict[str, Any],
    *,
    exhibit: Path,
    module: str,
    decl: str,
) -> Diagnostic | None:
    """F08-T17 (D-16): a circularity claim's exhibit proves ``ancestor → node``, exactly.

    No program decides "no easier up to proof", so the claim carries the proof and the gate checks
    only that it is one: ``opn-relation-type`` with the label ``resolves`` (variant → root), the
    ancestor as the variant and this node as the root, compares the exhibit's one theorem to that
    implication by definitional equality and reads its axioms. The reverse implication, a theorem
    about anything else, and a proof resting on ``sorryAx`` (the ancestor's Context restates this
    node's theorem with a ``sorry`` body, which is the obvious shortcut) are each refused by name.
    Both statements are read from their staged copies: the sandbox holds the work directory and
    nothing else of the graph (F00-R12, the lesson of F08-Q13).
    """
    assert located.node_id is not None  # the classifier refuses a circularity claim under defs/
    ancestor = str(doc.get("ancestor"))  # staged by ``elaborate_one`` with the node itself
    nodes_dir = layout.graph_nodes_dir(ctx.graph_root, located.target_id)
    decls: dict[str, str] = {}
    for node_id in (ancestor, located.node_id):
        loaded = layout.load_node(nodes_dir / node_id, located.target_id)
        if isinstance(loaded, list):
            return Diagnostic(
                "exhibit-node",
                f"{node_id}: {loaded[0].message}; a circularity claim relates two nodes (D-3)",
                {"node": node_id},
            )
        decls[node_id] = loaded.statement.decl_name
    src = ctx.workdir / "src"
    req = RelationRequest(
        variant=src / "Nodes" / ancestor / "Statement.lean",
        variant_module=layout.node_module(ancestor, STATEMENT_MODULE),
        variant_decl=decls[ancestor],
        root=src / "Nodes" / located.node_id / "Statement.lean",
        root_module=layout.node_module(located.node_id, STATEMENT_MODULE),
        root_decl=decls[located.node_id],
        label=CIRCULAR_LABEL,
        relation=exhibit,
        relation_module=module,
        relation_decl=decl,
    )
    try:
        result = ctx.toolchain.relation_type(tc, req, [ctx.build_dir], timeout_s=ctx.wallclock_s)
    except subprocess.TimeoutExpired:
        return Diagnostic(
            "exhibit-timeout",
            f"{located.path}: checking the exhibit's type exceeded the {ctx.wallclock_s:g}s cap",
            {"path": located.path},
        )
    return circular_verdict(ctx, located, ancestor, result)


def circular_verdict(
    ctx: RunContext, located: Located, ancestor: str, result: MetaprogramResult
) -> Diagnostic | None:
    """What ``opn-relation-type``'s answer means for a circularity claim (F08-T17)."""
    ok, out = result.ok, result.doc
    details: dict[str, Any] = {"path": located.path, "ancestor": ancestor}
    if not ok:
        return Diagnostic(
            "circular-elaboration",
            f"{located.path}: the exhibit could not be checked against {ancestor} and "
            f"{located.node_id}: {out.get('error') or f'exit {result.exit_code}, no verdict'}",
            {
                **details,
                "messages": [m.as_dict() for m in result.messages],
                "output": result.output,
            },
        )
    axioms = sorted(str(a) for a in out.get("axioms") or [])
    details.update(expected=out.get("expected"), declared=out.get("declared"), axioms=axioms)
    if SORRY_AXIOM in axioms:
        return Diagnostic(
            "circular-sorry",
            f"{located.path}: the exhibit depends on sorryAx, so the implication is claimed, not "
            "proved (F08-T17)",
            details,
        )
    outside = [a for a in axioms if a not in set(ctx.spec["axiom_allowlist"])]
    if outside:
        return Diagnostic(
            "circular-axiom",
            f"{located.path}: the exhibit depends on axioms outside the allowlist: "
            f"{', '.join(outside)}",
            details,
        )
    if out.get("matches") is not True:
        return Diagnostic(
            "circular-direction",
            f"{located.path}: a {CIRCULAR_CLASS} exhibit proves {out.get('expected')} "
            f"({ancestor} → {located.node_id}), but this one proves {out.get('declared')} "
            "(F08-T17)",
            details,
        )
    log.info("exhibit %s proves %s -> %s", located.path, ancestor, located.node_id)
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
    # F11-R2, F01-Q2: the target's definitions first; the Context may import them.
    target_dir = layout.gate_spec_path(ctx.graph_root, target_id).parent
    problem = defs.compile_all(
        ctx.toolchain, tc, target_dir, ctx.workdir, timeout_s=ctx.wallclock_s
    )
    if problem is not None:
        return problem
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
