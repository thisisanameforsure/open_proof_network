"""A node's closing proof, composed from its merged assembly and its proved holes (F28-T2;
draft decisions v3.41).

``closing`` says which nodes are closable and by which link; this module writes the proof for one
of them. For a route (F28-R4, R6) that is the route's merged assembly with each hole's ``sorry``
replaced by the hole node's theorem, composed by ``opn-close`` in the step-3 sandbox over the
same staging the outline job uses (``outline_graph.build``: the assembly staged as the node's
``Proof`` module, everything it imports compiled, the node's own ``Context`` with its children's
signatures among them). The composed text is a proposal: the gate judges it like any proof
(D-12 v3.41), so nothing here is trusted and nothing here writes to the graph.

For a circularity claim or a ``resolves`` variant (F28-R5, T3) the closing proof is the node's
statement with its ``sorry`` replaced by the link's implication applied to the input's theorem:
the implication (the claim's exhibit, the variant's ``Relation.lean``) goes in as a private helper
lemma directly before the theorem (F00-T11), and the input's merged proof comes in through a use
line (v3.25) unless the input is already a dependency, whose theorem ``Context`` carries. That
file is staged and elaborated whole before it is returned.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from opn_gate import closing, layout, outline, outline_graph, paths, schemas
from opn_gate import graph as graphmod
from opn_gate.toolchain import CloseRequest, ResolvedToolchain, Toolchain

#: Why no proof was composed. Each is a fact about the record or the run, never a guess.
NOT_CLOSABLE = "not-closable"
NOT_READY = "not-ready"
LINK_REFUSED = "link-refused"
BUILD_FAILED = "build-failed"
COMPOSE_FAILED = "compose-failed"

_DETAIL_CAP = 2000
#: Where a link's composed file is written in the (scratch) tree, to be staged as the node's proof.
LINK_FILE = ".opn-closing.lean"


@dataclass(frozen=True)
class Result:
    """One node's closing proof, or the named reason there is none. ``sites`` are the
    composer's, one per hole of the assembly."""

    target: str
    node: str
    link: closing.Link | None
    proof: str | None = None
    reason: str | None = None
    detail: str = ""
    sites: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return self.proof is not None

    def as_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "node": self.node,
            "link": self.link.as_dict() if self.link else None,
            "ok": self.ok,
            "proof": self.proof,
            "reason": self.reason,
            "detail": self.detail,
            "sites": [dict(s) for s in self.sites],
        }


def graph_doc(tree: Path, target_id: str) -> dict[str, Any]:
    """The target's published ``graph.json``: what ``closing`` reads."""
    path = tree / "targets" / target_id / "graph.json"
    doc: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return doc


def find(graph: Mapping[str, Any], node_id: str) -> closing.Closable | None:
    """The node's closable entry, or ``None`` when it is not closable."""
    return next((c for c in closing.closable(graph) if c.node == node_id), None)


def route_partial(graph: Mapping[str, Any], link: closing.Link) -> str:
    """The assembly a route link names: ``<node>@<k>`` is the node's ``k``-th decomposition in
    the record's order (F27), whose ``partial`` is its path under the node."""
    node_id, _, k = link.id.rpartition("@")
    row = next(n for n in graph["nodes"] if n["node_id"] == node_id)
    return str(row["decompositions"][int(k) - 1]["partial"])


def children(tree: Path, target_id: str, inputs: tuple[str, ...]) -> list[dict[str, str]]:
    """Each input node with the theorem its statement declares, in the link's order."""
    out: list[dict[str, str]] = []
    nodes_dir = layout.graph_nodes_dir(tree, target_id)
    for node_id in inputs:
        loaded = layout.load_node(nodes_dir / node_id, target_id)
        if isinstance(loaded, list):
            msg = "; ".join(d.message for d in loaded)
            raise outline_graph.BuildError(f"{node_id}: {msg}")
        out.append({"node": node_id, "decl": loaded.statement.decl_name})
    return out


# --- claims and variants (F28-R5, T3) -------------------------------------------------------------

#: The helper a link's implication becomes in the closing proof: private, so it never reaches an
#: importer (F00-T11), and named so that no statement's theorem can collide with it.
LINK_HELPER = "opn_closing_link"
#: The implication's own name in the file it comes from: a circularity exhibit declares
#: ``circular`` (D-16 v3.23), a variant's ``Relation.lean`` declares ``relation`` (D-30).
LINK_DECLS: Mapping[str, str] = {"claim": "circular", "variant": "relation"}
_HEADER_LINE_RE = re.compile(r"^(?:import\s+\S+|open\s.*|\s*)$")
_DECL_RE = re.compile(
    r"^(?P<mods>(?:@\[[^\]]*\]\s*)?(?:(?:private|protected|noncomputable)\s+)*)"
    r"(?P<kind>theorem|lemma|def|abbrev)\s+(?P<name>[^\s:({\[]+)",
    re.M,
)


class LinkError(ValueError):
    """The link's implication cannot become a helper of the closing proof; the message says why."""


def implication_source(tree: Path, target_id: str, link: closing.Link) -> str:
    """The Lean text of the implication a claim or a variant link proves: a claim's exhibit
    (``defect-claim``'s ``exhibit``, under the claiming node) or a variant's ``Relation.lean``."""
    nodes_dir = layout.graph_nodes_dir(tree, target_id)
    if link.kind == "claim":
        doc = yaml.safe_load((nodes_dir / link.id).read_text(encoding="utf-8"))
        exhibit = doc.get("exhibit") if isinstance(doc, Mapping) else None
        if not isinstance(exhibit, str):
            msg = f"{link.id} carries no exhibit"
            raise LinkError(msg)
        return exhibit
    return (nodes_dir / link.id / "Relation.lean").read_text(encoding="utf-8")


def as_helper(source: str, kind: str, statement_prefix: str) -> str:
    """``source`` made a helper block: its header (imports, ``open`` lines, blanks) dropped, the
    implication renamed ``LINK_HELPER``, every declaration private. An ``open`` the statement does
    not itself carry cannot go into a helper block (``helper-forbidden``), so it is refused."""
    lines = source.splitlines()
    i = 0
    while i < len(lines) and _HEADER_LINE_RE.fullmatch(lines[i]):
        line = lines[i].strip()
        if line.startswith("open ") and line not in {
            s.strip() for s in statement_prefix.splitlines()
        }:
            msg = f"the implication needs `{line}`, which the statement does not open"
            raise LinkError(msg)
        i += 1
    body = "\n".join(lines[i:]).strip("\n")
    name = LINK_DECLS[kind]
    found = False

    def fix(m: re.Match[str]) -> str:
        nonlocal found
        mods = m.group("mods")
        if "private" not in mods:
            mods = mods + "private "
        new = m.group("name")
        if new == name:
            found = True
            new = LINK_HELPER
        return f"{mods}{m.group('kind')} {new}"

    body = _DECL_RE.sub(fix, body)
    if not found:
        msg = f"the implication declares no `{name}`"
        raise LinkError(msg)
    return body + "\n\n"


def link_text(st: layout.Statement, helper: str, input_decl: str, use: str | None) -> str:
    """The node's statement with ``helper`` as its helper block, ``use`` (a module) as its one
    use line, and its ``sorry`` replaced by the helper applied to the input's theorem. With the
    use line and the helper block taken out it is the statement with its ``sorry`` replaced, which
    is what step 2 compares (``layout.split_uses``, ``paths._without_helpers``)."""
    prefix = st.prefix
    at = layout._imports_end(prefix)
    start = layout.declaration_start(prefix)
    line = f"import {use}\n" if use else ""
    body = f" ({LINK_HELPER} @_root_.{input_decl})"
    return prefix[:at] + line + prefix[at:start] + helper + prefix[start:] + body + st.suffix


def compose_link(  # noqa: PLR0913, PLR0917 — the run's seam, the record, the link, where it works
    toolchain: Toolchain,
    tc: ResolvedToolchain,
    tree: Path,
    target_id: str,
    found: closing.Closable,
    workdir: Path,
    *,
    timeout_s: float,
) -> Result:
    """F28-R5: the closing proof through a claim or a variant, staged and elaborated whole.
    ``tree`` is a scratch export: the composed file is written into it to be staged."""
    link = found.link
    node_id = found.node
    nodes_dir = layout.graph_nodes_dir(tree, target_id)
    node_dir = nodes_dir / node_id
    loaded = layout.load_node(node_dir, target_id)
    if isinstance(loaded, list):
        detail = "; ".join(d.message for d in loaded)
        return Result(target_id, node_id, link, reason=BUILD_FAILED, detail=detail[:_DETAIL_CAP])
    st = loaded.statement
    (source_node,) = link.inputs
    try:
        [child] = children(tree, target_id, link.inputs)
        helper = as_helper(implication_source(tree, target_id, link), link.kind, st.prefix)
        problem = paths.helper_problem(helper, first_line=1)
        if problem is not None:
            raise LinkError(problem.message)
    except (LinkError, OSError, yaml.YAMLError) as exc:
        return Result(target_id, node_id, link, reason=LINK_REFUSED, detail=str(exc)[:_DETAIL_CAP])
    deps = graphmod.effective_deps(nodes_dir, loaded.meta.get("deps"))
    use = None if source_node in deps else layout.node_module(source_node, "Proof")
    text = link_text(st, helper, child["decl"], use)
    (node_dir / LINK_FILE).write_text(text, encoding="utf-8")
    try:
        job = outline_graph.build(
            toolchain,
            tc,
            tree,
            outline_graph.Found(
                target_id,
                node_id,
                outline.Artifact(LINK_FILE, schemas.content_hash(text.encode()), "proof"),
            ),
            workdir,
            timeout_s=timeout_s,
        )
    except outline_graph.BuildError as exc:
        return Result(target_id, node_id, link, reason=BUILD_FAILED, detail=str(exc)[:_DETAIL_CAP])
    elab = toolchain.elaborate(
        tc, job.file, job.module, job.search_path[0], root=job.file.parents[2],
        timeout_s=timeout_s,
    )  # fmt: skip
    if not elab.ok:
        first = elab.errors[0].as_dict() if elab.errors else elab.stderr
        detail = f"the composed proof does not elaborate: {first}"
        return Result(target_id, node_id, link, reason=COMPOSE_FAILED, detail=detail[:_DETAIL_CAP])
    return Result(target_id, node_id, link, proof=text)


def compose(  # noqa: PLR0913, PLR0917 — the run's seam, the record, the node, where it works
    toolchain: Toolchain,
    tc: ResolvedToolchain,
    tree: Path,
    target_id: str,
    node_id: str,
    workdir: Path,
    *,
    timeout_s: float,
) -> Result:
    """The closing proof of ``node_id`` at ``tree``, or why there is none."""
    graph = graph_doc(tree, target_id)
    found = find(graph, node_id)
    if found is None:
        return Result(target_id, node_id, None, reason=NOT_CLOSABLE)
    if not found.ready:
        detail = "waits on " + ", ".join(found.link.inputs)
        return Result(target_id, node_id, found.link, reason=NOT_READY, detail=detail)
    if found.link.kind != "route":
        return compose_link(toolchain, tc, tree, target_id, found, workdir, timeout_s=timeout_s)
    partial = route_partial(graph, found.link)
    node_dir = layout.graph_nodes_dir(tree, target_id) / node_id
    file = node_dir / partial
    digest = schemas.content_hash(file.read_bytes()) if file.is_file() else ""
    try:
        job = outline_graph.build(
            toolchain,
            tc,
            tree,
            outline_graph.Found(target_id, node_id, outline.Artifact(partial, digest, "partial")),
            workdir,
            timeout_s=timeout_s,
        )
        workdir.mkdir(parents=True, exist_ok=True)
        spec = workdir / "children.json"
        spec.write_text(json.dumps(children(tree, target_id, found.link.inputs)), encoding="utf-8")
    except outline_graph.BuildError as exc:
        return Result(
            target_id, node_id, found.link, reason=BUILD_FAILED, detail=str(exc)[:_DETAIL_CAP]
        )
    result = toolchain.close(
        tc, CloseRequest(job.file, job.module, job.decl, spec), job.search_path,
        timeout_s=timeout_s,
    )  # fmt: skip
    doc = result.doc or {}
    sites = tuple(doc.get("sites") or ())
    if not result.ok or not doc.get("ok") or not isinstance(doc.get("composed"), str):
        detail = str(doc.get("error") or result.output or "the composer gave no proof")
        return Result(
            target_id,
            node_id,
            found.link,
            reason=COMPOSE_FAILED,
            detail=detail[:_DETAIL_CAP],
            sites=sites,
        )
    return Result(target_id, node_id, found.link, proof=str(doc["composed"]), sites=sites)
