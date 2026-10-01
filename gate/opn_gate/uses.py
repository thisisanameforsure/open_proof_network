"""Declared uses: what a proof may draw on beyond its statement's own header (F08-R16 to R18;
D-3, D-4, proposed v3.25).

A node's statement is immutable, and until this module a proof's header had to be the
statement's exactly (F00-R19, with F00-T10's one line). So nothing beneath a root stated over
Mathlib alone could name a definition admitted to the target later (F11-T13), and no node could
name a proved node it did not already depend on: a gate-written hole has ``deps: []`` and its
parent's header, and an authored node's deps are fixed when it is created.

**The declaration is the artifact's own header.** A proof, a partial's assembly or an alternate
may carry *use lines*: ``import`` lines placed directly after the statement's last import (after
the node's own ``Context`` line, where F00-T10 added one), each naming

* ``Defs.<Name>``: a definition module of the same target, on the tree; or
* ``Nodes.«<id>».Proof``: the merged proof of another node of the same target (F08-T24).

Nothing else changes in the file: with its use lines removed it is the statement with the
``sorry`` replaced, as before, so ``Statement.lean``, its hash and ``META.yaml`` are untouched.
The declaration lands in the tree inside the artifact, under the artifact's hash, with no
sidecar and no new path, and Lean itself enforces half of it: a name whose module is not
imported is not there to be used.

What makes it sound is split across the steps that already own each question:

* step 2 (``check``): each line names something that exists and may be used;
* step 4 (``steps.meaning``): the larger environment did not change what the statement says;
* step 8 (``steps.deps``): the lines agree with what the kernel term uses.

A gate that predates this module refuses every such header as ``proof-not-statement``, so
nothing here is live on a graph before its re-pin (D-35).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from opn_gate import graph as graphmod
from opn_gate import layout, records, schemas
from opn_gate.diagnostic import Diagnostic

#: ``ctx.data`` key: the uses step 2 read off the artifact, as ``Uses.as_dict`` gives them.
USES_KEY = "uses"

#: One use line, without its newline: the module it names (``layout.split_uses`` reads them).
USE_LINE_RE = layout.USE_LINE_RE


@dataclass(frozen=True)
class Uses:
    """The use lines of one artifact, in the order written."""

    modules: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.modules)

    @property
    def defs(self) -> tuple[str, ...]:
        """The ``Defs.<Name>`` modules declared."""
        return tuple(m for m in self.modules if layout.module_origin(m)[0] == "defs")

    @property
    def nodes(self) -> tuple[str, ...]:
        """The nodes whose merged proof is declared as a use (F08-R18)."""
        return tuple(n for n in (node_of(m) for m in self.modules) if n is not None)

    def as_dict(self) -> dict[str, Any]:
        return {"modules": list(self.modules), "defs": list(self.defs), "nodes": list(self.nodes)}


def node_of(module: str) -> str | None:
    """The node ``Nodes.«<id>».Proof`` names; ``None`` for any other module."""
    return layout.used_node(module)


def split(prefix: str, text: str, node_id: str | None) -> tuple[str, Uses]:
    """``text`` with its use lines removed, and the uses they declare (``layout.split_uses``,
    the one reading of a use line: the same for a submission and for a merged proof)."""
    rest, modules = layout.split_uses(prefix, text, node_id)
    return rest, Uses(modules)


def declared(statement: layout.Statement, text: str, node_id: str | None) -> Uses:
    """The uses an artifact of ``statement`` declares (``split``'s second half)."""
    return split(statement.prefix, text, node_id)[1]


def defs_file(target_dir: Path, module: str) -> Path:
    """Where ``Defs.<Name>`` lives in a target: ``defs/<Name>.lean``."""
    return target_dir / "defs" / f"{module.partition('.')[2]}.lean"


def merged_uses(node_dir: Path) -> tuple[str, ...]:
    """The nodes a node's merged ``Proof.lean`` uses; none for a node without one. This is the
    graph's record of a use: nothing else is written for it (R19)."""
    return layout.merged_uses(node_dir)


def edges(nodes_dir: Path) -> dict[str, tuple[str, ...]]:
    """What every node of the target rests on: its recorded dependencies, both as ``META.yaml``
    wrote them and as they are now (``graph.effective_deps``: each read through its revision
    chain; its own holes are among them), and the nodes its merged proof uses. Both readings,
    because this relation exists to refuse: a node that was replaced is still a node a parent
    was written over, and a proof of it that cited the parent would be the same circle. A
    ``META.yaml`` that does not read contributes its uses alone."""
    out: dict[str, tuple[str, ...]] = {}
    for node_dir in sorted(p for p in nodes_dir.iterdir() if p.is_dir()):
        try:
            meta = schemas.load_yaml(node_dir / "META.yaml")
        except (OSError, schemas.SchemaError):
            meta = {}
        raw = meta.get("deps") if isinstance(meta, dict) else None
        recorded = tuple(str(d) for d in raw) if isinstance(raw, (list, tuple)) else ()
        deps = graphmod.effective_deps(nodes_dir, raw)
        out[node_dir.name] = tuple(dict.fromkeys((*recorded, *deps, *merged_uses(node_dir))))
    return out


def above(nodes_dir: Path, node_id: str) -> set[str]:
    """Every node that rests on ``node_id``, however indirectly, over ``edges``; never the node
    itself. A proof of ``node_id`` may use none of them (R18): the node it used would rest on
    the node it proves, which is the cycle D-12 refuses of a hole, by another road."""
    rests_on = edges(nodes_dir)
    found: set[str] = set()
    frontier = [node_id]
    while frontier:
        below = frontier.pop()
        for candidate, on in rests_on.items():
            if below in on and candidate not in found and candidate != node_id:
                found.add(candidate)
                frontier.append(candidate)
    return found


def _superseded_by(nodes_dir: Path, node_id: str) -> str | None:
    """The node that replaced ``node_id``, when a status record says it is superseded: the end of
    its revision chain, or the node itself when the record names no sound successor."""
    try:
        record = records.load_node_status(nodes_dir / node_id)
    except (OSError, schemas.SchemaError):
        return None
    if record is None or record.status != "superseded":
        return None
    return graphmod.current_id(nodes_dir, node_id)


def _node_problem(node: layout.Node, used: str) -> Diagnostic | None:  # noqa: PLR0911 — one per rule
    """Why ``node``'s artifact may not use the merged proof of ``used``, or ``None`` (R18)."""
    from opn_gate.steps import artifact  # noqa: PLC0415 — the steps import this module

    nodes_dir = node.path.parent
    module = layout.node_module(used, layout.USED_STEM)
    details = {"module": module, "node": used}
    if used == node.node_id:
        return Diagnostic("use-self", f"{module} is this node's own proof", details)
    used_dir = nodes_dir / used
    if not used_dir.is_dir():
        return Diagnostic("use-unknown-node", f"{used} is not a node of {node.target_id}", details)
    successor = _superseded_by(nodes_dir, used)
    if successor is not None:
        return Diagnostic(
            "use-superseded",
            f"{used} has been superseded"
            + (f" by {successor}: use that node's proof" if successor != used else "")
            + " (D-8); a proof may not rest on a statement the graph has replaced",
            {**details, "successor": successor if successor != used else None},
        )
    proof = used_dir / "Proof.lean"
    statement = layout.parse_statement((used_dir / "Statement.lean").read_text(encoding="utf-8"))
    kind = (
        artifact.declared_kind(statement.decl_name, proof.read_text(encoding="utf-8"))[0]
        if proof.is_file() and isinstance(statement, layout.Statement)
        else None
    )
    if kind != "proof":
        return Diagnostic(
            "use-unproved",
            f"{used} has no merged proof to use"
            + (f" (its merged artifact is a {kind})" if kind else "")
            + ": a proof may use a node of its target only once that node's Proof.lean has "
            "merged (D-3)",
            {**details, "artifact": kind},
        )
    if used in graphmod.effective_deps(nodes_dir, node.meta.get("deps")):
        return Diagnostic(
            "use-redundant",
            f"{used} is already a dependency of {node.node_id}: its theorem reaches the proof "
            f"through {layout.node_module(node.node_id, 'Context')}, and a node is named one way",
            details,
        )
    if used in above(nodes_dir, node.node_id):
        return Diagnostic(
            "use-ancestor",
            f"{used} rests on {node.node_id} (through recorded dependencies and merged uses), "
            f"so a proof of {node.node_id} that uses it would make the statement graph wait on "
            "itself; a node is proved from what lies beside or below it, never from a node it "
            "was written to help prove (D-12: no cycles)",
            details,
        )
    return None


def check(node: layout.Node, uses: Uses) -> Diagnostic | None:
    """Step 2's rules for a declared use, read from the tree (R16, R18): the first one broken.

    * ``use-duplicate``: a line repeats another, or a module the statement already imports;
    * ``use-unknown-defs``: ``Defs.<Name>`` is not a definition of this target on the tree. A
      submission cannot add one (``defs/`` is no submission path, D-3), so what is on the tree is
      what a curator's pull request admitted (F11-R15);
    * a node use: ``_node_problem``. A submission cannot add another node's ``Proof.lean``
      either (a diff outside the claimed node is refused first), so a used node's proof is one
      a merge put there.
    """
    target_dir = node.path.parent.parent
    seen = set(layout.imports_of(node.statement.text))
    for module in uses.modules:
        if module in seen:
            return Diagnostic(
                "use-duplicate",
                f"the header imports {module} twice: a use line names a module once, and never "
                "one the statement already imports",
                {"module": module},
            )
        seen.add(module)
    for module in uses.defs:
        if not defs_file(target_dir, module).is_file():
            return Diagnostic(
                "use-unknown-defs",
                f"{module} is not a definition of {node.target_id}: a proof may use a module "
                f"under targets/{node.target_id}/defs/ that is already on the graph (D-3), and "
                "a definition is added by a curator's pull request (F11-R15)",
                {"module": module},
            )
    for used in uses.nodes:
        problem = _node_problem(node, used)
        if problem is not None:
            return problem
    return None
