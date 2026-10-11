"""Elaborating the Lean exhibits an append carries (F08-R6, R7; D-8, D-16; C9).

A revision request or a defect claim may attach a Lean file as its evidence. The record itself
claims nothing a kernel could check, which is why it merges as an append (F07-R9) — but the
exhibit is contributor Lean, and contributor Lean runs only where the gate's sandbox runs it
(C9). So the append mode gets one build of its own, here: every exhibit elaborates, against the
node it is about, or the pull request fails naming the file.

Elaborating is all this asks. Whether the exhibit *shows* what the record says it shows is the
adjudicator's question (D-17), not the gate's; an exhibit that elaborates is admissible evidence,
and one that does not is noise.

The one exception is a circularity claim (F08-T17, F08-T21), whose exhibit must prove a stated
implication. Since F02-T14 that judgment reads compiled modules only (``check_circular``): the
exhibit is compiled apart and its constants are replayed through the kernel by
``opn-relation-type``, so nothing of the exhibit runs in the process that prints the verdict.
Every other exhibit's verdict is its own compile, which is the claim itself.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from opn_gate import defs, judging, layout, modes
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
#: The modules of a node an exhibit about it may import: what the staging compiles for it
#: (``stage_node``; for a circularity claim, ``compiled_exhibit``, for both nodes), beside the
#: target's definitions. A node's Statement is copied but never compiled for an exhibit, so an
#: import of it does not elaborate here; the service's pre-flight reads this tuple (F13-T31).
EXHIBIT_NODE_MODULES: tuple[str, ...] = ("Context",)
#: F08-T17, turned round by F08-T21: D-30's ``resolves`` is ``variant → root``; with the claimed
#: node (the hole) as the variant and the ancestor as the root it is the implication a circularity
#: claim asserts — the hole implies what it was cut from, so the route leads straight back.
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
    if located.role == "defect-claim" and doc.get("class") == CIRCULAR_CLASS:
        declared = layout.parse_declaration(text, f"{located.path}'s exhibit")
        if isinstance(declared, Diagnostic):
            return Diagnostic(
                "circular-exhibit",
                f"{declared.message}: a {CIRCULAR_CLASS} exhibit is the one theorem "
                "`<this node's statement> → <ancestor's statement>` (F08-T21)",
                {"path": located.path, **(declared.details or {})},
            )
        try:
            return check_circular(ctx, tc, located, doc, text=text, index=index, decl=declared)
        except subprocess.TimeoutExpired:
            return Diagnostic(
                "exhibit-timeout",
                f"{located.path}: the exhibit exceeded the {ctx.wallclock_s:g}s wall-clock cap",
                {"path": located.path},
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


def check_circular(  # noqa: PLR0913 — the run, the seam, the record and its exhibit
    ctx: RunContext,
    tc: ResolvedToolchain,
    located: Located,
    doc: dict[str, Any],
    *,
    text: str,
    index: int,
    decl: str,
) -> Diagnostic | None:
    """F08-T21 (D-16, D-12 v3.23): a circularity claim's exhibit proves ``node → ancestor``.

    No program decides "circular up to proof", so the claim carries the proof and the gate checks
    only that it is one: ``opn-relation-type`` with the label ``resolves`` (variant → root), this
    node as the variant and the ancestor as the root, compares the exhibit's one theorem to that
    implication by definitional equality and reads its axioms. Any proof of the node is then a
    proof of the ancestor: from the ancestor the decomposition led to this node, and this node
    leads straight back — the literal cycle. F08-T17 had asked for ``ancestor → node``, which says
    only that the node is no *harder* than the ancestor, a bar every provable hole and every hole
    whose hypothesis contradicts the ancestor clears (tester 69-C B3, 2026-09-29). That reverse
    implication, a theorem about anything else, and a proof resting on ``sorryAx`` (the ancestor's
    own half left as ``sorry`` is the obvious shortcut) are each refused by name.

    F02-T14 (decisions v3.27 §1): judged from compiled modules, as admission's relation check is
    (F02-T12). The two statements are built from their files of record in a judging area of
    their own; the exhibit is compiled in a call of its own, writable only in that area's scratch
    directory, under a header the gate writes; ``opn-relation-type`` is handed the oleans alone,
    read-only, and adds the exhibit's constants through the kernel, executing nothing of it. The
    exhibit's compile is also its "it elaborates" (F08-R6): one compile, not two.
    """
    assert located.node_id is not None  # the classifier refuses a circularity claim under defs/
    ancestor = str(doc.get("ancestor"))
    nodes_dir = layout.graph_nodes_dir(ctx.graph_root, located.target_id)
    decls: dict[str, str] = {}
    for node_id in (located.node_id, ancestor):
        for name in ("Statement.lean", "Context.lean"):
            if not (nodes_dir / node_id / name).is_file():
                return Diagnostic(
                    "exhibit-node",
                    f"{node_id} has no {name}; an exhibit is about a node that exists (D-3)",
                    {"node": node_id, "missing": name},
                )
        loaded = layout.load_node(nodes_dir / node_id, located.target_id)
        if isinstance(loaded, list):
            return Diagnostic(
                "exhibit-node",
                f"{node_id}: {loaded[0].message}; a circularity claim relates two nodes (D-3)",
                {"node": node_id},
            )
        decls[node_id] = loaded.statement.decl_name
    module = layout.node_module(located.node_id, f"{EXHIBIT_MODULE}{index}")
    prepared = compiled_exhibit(ctx, tc, located, ancestor, text=text, module=module)
    if isinstance(prepared, Diagnostic):
        return prepared
    build, olean, imports = prepared
    log.info("exhibit %s elaborates as %s", located.path, module)
    req = RelationRequest(
        variant=nodes_dir / located.node_id / "Statement.lean",
        variant_module=layout.node_module(located.node_id, STATEMENT_MODULE),
        variant_decl=decls[located.node_id],
        root=nodes_dir / ancestor / "Statement.lean",
        root_module=layout.node_module(ancestor, STATEMENT_MODULE),
        root_decl=decls[ancestor],
        label=CIRCULAR_LABEL,
        relation_module=module,
        relation_decl=decl,
        imports=imports,
        variant_olean=judging.statement_olean(build, located.node_id),
        root_olean=judging.statement_olean(build, ancestor),
        relation_olean=olean,
    )
    # F02-T14: the judging call reads compiled modules only, read-only, nothing writable
    reader = judging.confined(ctx.toolchain, read_only=[build, olean.parent])
    try:
        result = reader.relation_type(tc, req, [build], timeout_s=ctx.wallclock_s)
    except subprocess.TimeoutExpired:
        return Diagnostic(
            "exhibit-timeout",
            f"{located.path}: checking the exhibit's type exceeded the {ctx.wallclock_s:g}s cap",
            {"path": located.path},
        )
    return circular_verdict(ctx, located, ancestor, result)


def compiled_exhibit(  # noqa: PLR0913 — the run, the seam, the record, and what to compile
    ctx: RunContext,
    tc: ResolvedToolchain,
    located: Located,
    ancestor: str,
    *,
    text: str,
    module: str,
) -> tuple[Path, Path, tuple[str, ...]] | Diagnostic:
    """F02-T14: the node's and the ancestor's statements built from their files of record in the
    judging area ``exhibit<n>``, then the exhibit compiled apart under the union of the
    statements' imports and its own (``judging.with_header``), as ``opn-relation-type`` read all
    three headers when it elaborated them. Answers the statements' build, the exhibit's olean in
    ``contributed/`` and the imports, or the diagnostic.

    The graph modules the exhibit may add are what the staging compiled for it before T14: the
    target's definitions and the two nodes' Contexts. Any other (a Statement, another node's
    module) did not elaborate then, and is refused by name now, before anything is compiled.
    """
    assert located.node_id is not None
    nodes_dir = layout.graph_nodes_dir(ctx.graph_root, located.target_id)
    target_dir = layout.gate_spec_path(ctx.graph_root, located.target_id).parent
    where = judging.area(ctx.workdir, module.rsplit(".", 1)[-1].lower())
    trusted = where / judging.STATEMENT_DIR
    pair = (located.node_id, ancestor)
    problem = judging.build_statements(
        ctx.toolchain,
        tc,
        target_dir,
        [(n, nodes_dir / n / "Context.lean", nodes_dir / n / "Statement.lean") for n in pair],
        trusted,
        timeout_s=ctx.wallclock_s,
    )
    if problem is not None:
        return statement_problem(located, pair, problem)
    imports: list[str] = []
    for node_id in pair:
        source = (nodes_dir / node_id / "Statement.lean").read_text(encoding="utf-8")
        for imported in judging.header_imports(source):
            if imported not in imports:
                imports.append(imported)
    contexts = {layout.node_module(n, stem) for n in pair for stem in EXHIBIT_NODE_MODULES}
    for imported in judging.header_imports(text):
        if imported in imports:
            continue
        origin = layout.module_origin(imported)[0]
        if origin == "node" and imported not in contexts:
            return Diagnostic(
                "exhibit-elaboration",
                f"{located.path}: the exhibit imports {imported}; an exhibit about "
                f"{located.node_id} may import the target's definitions and the Contexts of "
                f"{located.node_id} and {ancestor}, and no other graph module (F08-R7)",
                {"path": located.path, "module": module, "messages": []},
            )
        imports.append(imported)
    elab, olean = judging.compile_contributed(
        ctx.toolchain,
        tc,
        text=judging.with_header(text, imports),
        module=module,
        trusted_build=trusted / "build",
        where=where,
        timeout_s=ctx.wallclock_s,
    )
    if olean is None:
        return Diagnostic(
            "exhibit-elaboration",
            f"{located.path}: the exhibit does not elaborate (F08-R6, R7)",
            {
                "path": located.path,
                "module": module,
                "messages": [m.as_dict() for m in elab.errors or elab.messages],
            },
        )
    return trusted / "build", olean, tuple(imports)


def statement_problem(located: Located, pair: tuple[str, str], problem: Diagnostic) -> Diagnostic:
    """A statement build's failure, in the words the staging used: a Context that does not
    elaborate is ``exhibit-node`` naming the node; a statement that does not is the relation
    program's old ``circular-elaboration``; the definitions' own failure stands as it is."""
    module = (problem.details or {}).get("module")
    messages = list((problem.details or {}).get("messages") or [])
    for node_id in pair:
        if module == layout.node_module(node_id, "Context"):
            return Diagnostic(
                "exhibit-node",
                f"{module} does not elaborate, so no exhibit about {node_id} can",
                {"node": node_id, "messages": messages},
            )
        if module == layout.node_module(node_id, STATEMENT_MODULE):
            return Diagnostic(
                "circular-elaboration",
                f"{located.path}: the exhibit could not be checked: {module} does not elaborate "
                "from the node's own files",
                {"path": located.path, "ancestor": pair[1], "messages": messages},
            )
    return problem


def circular_verdict(
    ctx: RunContext, located: Located, ancestor: str, result: MetaprogramResult
) -> Diagnostic | None:
    """What ``opn-relation-type``'s answer means for a circularity claim (F08-T17, F08-T21)."""
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
            f"{located.path}: the exhibit depends on sorryAx, so `{located.node_id} → {ancestor}` "
            "is claimed, not proved (F08-T21)",
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
            f"({located.node_id} → {ancestor}: the node implies the ancestor it was cut from), "
            f"but this one proves {out.get('declared')} (F08-T21)",
            details,
        )
    log.info("exhibit %s proves %s -> %s", located.path, located.node_id, ancestor)
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
