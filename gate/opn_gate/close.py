"""Closing by construction (F28-T7, T9; decisions v3.42).

``closing`` says which nodes are closable and by which link; this module closes them. For a route
it stages the node's merged assembly as its ``Proof`` module, has every module beneath it built
(a child proved by closure is joined in turn, ``steps.stage.join_module``), and runs ``opn-close``,
which replaces each hole of the assembly's elaborated term by the child's theorem, has the kernel
accept the node's theorem and writes its module. A ``resolves`` variant joins through a short
composed proof (its relation as a private helper applied to the variant's theorem), compiled like
any proof; the circularity claim is no link (D-12 v3.42, F28-Q11). Either way the result is
a ``closure`` record for the node.

``sweep`` closes a whole target in one run: it re-derives the target from the tree, joins every
node whose inputs are all proved, writes each record into the tree, and repeats, so a proof at the
bottom of a chain climbs to the top in one post-merge job. Every join runs in the step-3 sandbox;
nothing here writes to the graph but the records, which the post-merge job signs and commits.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from opn_gate import closing, closure, layout, outline, outline_graph, paths, products, schemas
from opn_gate import graph as graphmod
from opn_gate.toolchain import CloseRequest, ResolvedToolchain, Toolchain, module_output_path

#: Why no proof was composed. Each is a fact about the record or the run, never a guess.
LINK_REFUSED = "link-refused"
BUILD_FAILED = "build-failed"
JOIN_FAILED = "join-failed"

_DETAIL_CAP = 2000
#: Where a link's composed file is written in the (scratch) tree, to be staged as the node's proof.
LINK_FILE = ".opn-closing.lean"


@dataclass(frozen=True)
class Facts:
    """What every record of one run carries: the commit joined, and the pinned tooling."""

    graph_commit: str
    network_commit: str | None
    lean_toolchain: str
    mathlib_sha: str | None
    timestamp: str


@dataclass(frozen=True)
class Result:
    """One node's closure record, or the named reason there is none."""

    target: str
    node: str
    link: closing.Link | None
    record: dict[str, Any] | None = None
    reason: str | None = None
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.record is not None

    def as_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "node": self.node,
            "link": self.link.as_dict() if self.link else None,
            "ok": self.ok,
            "reason": self.reason,
            "detail": self.detail,
        }


def graph_doc(tree: Path, target_id: str) -> dict[str, Any]:
    """The target's published ``graph.json``: what ``closing`` reads."""
    path = tree / "targets" / target_id / "graph.json"
    doc: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return doc


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


# --- variants (F28-R5, T3; the claim link retired, F28-Q11) -----------------------------------

#: The helper a link's implication becomes in the closing proof: private, so it never reaches an
#: importer (F00-T11), and named so that no statement's theorem can collide with it.
LINK_HELPER = "opn_closing_link"
#: The implication's own name in the file it comes from: a variant's ``Relation.lean`` declares
#: ``relation`` (D-30). The circularity claim's ``circular`` went with the claim link (F28-Q11).
LINK_DECLS: Mapping[str, str] = {"variant": "relation"}
_HEADER_LINE_RE = re.compile(r"^(?:import\s+\S+|open\s.*|\s*)$")
_DECL_RE = re.compile(
    r"^(?P<mods>(?:@\[[^\]]*\]\s*)?(?:(?:private|protected|noncomputable)\s+)*)"
    r"(?P<kind>theorem|lemma|def|abbrev)\s+(?P<name>[^\s:({\[]+)",
    re.M,
)


class LinkError(ValueError):
    """The link's implication cannot become a helper of the closing proof; the message says why."""


def implication_source(tree: Path, target_id: str, link: closing.Link) -> str:
    """The Lean text of the implication a variant link proves: its ``Relation.lean``."""
    nodes_dir = layout.graph_nodes_dir(tree, target_id)
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


def _record(
    tree: Path, target_id: str, node_id: str, link: closing.Link, facts: Facts, **source: Any
) -> dict[str, Any]:
    node_dir = layout.graph_nodes_dir(tree, target_id) / node_id
    statement = (node_dir / "Statement.lean").read_bytes()
    return closure.build(
        target_id=target_id,
        node_id=node_id,
        statement_hash=schemas.content_hash(statement),
        link=closure.Link(link.kind, link.id, link.inputs),
        source_path=source.get("path"),
        source_text=source.get("text"),
        source_hash=str(source["hash"]),
        axioms=list(source.get("axioms") or []),
        graph_commit=facts.graph_commit,
        network_commit=facts.network_commit,
        lean_toolchain=facts.lean_toolchain,
        mathlib_sha=facts.mathlib_sha,
        timestamp=facts.timestamp,
    )


def join_link(  # noqa: PLR0913, PLR0917 — the run's seam, the record, the link, where it works, the facts
    toolchain: Toolchain,
    tc: ResolvedToolchain,
    tree: Path,
    target_id: str,
    found: closing.Closable,
    workdir: Path,
    *,
    facts: Facts,
    timeout_s: float,
) -> Result:
    """F28-R5: the closure through a ``resolves`` variant, staged and compiled as a proof whose text
    the record keeps. ``tree`` is a scratch export: the composed file is written into it."""
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
    except (LinkError, OSError) as exc:
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
    finally:
        (node_dir / LINK_FILE).unlink(missing_ok=True)
    elab = toolchain.elaborate(
        tc, job.file, job.module, job.search_path[0], root=job.file.parents[2],
        timeout_s=timeout_s,
    )  # fmt: skip
    if not elab.ok:
        first = elab.errors[0].as_dict() if elab.errors else elab.stderr
        detail = f"the composed proof does not elaborate: {first}"
        return Result(target_id, node_id, link, reason=JOIN_FAILED, detail=detail[:_DETAIL_CAP])
    record = _record(
        tree, target_id, node_id, link, facts,
        path=None, text=text, hash=schemas.content_hash(text.encode()),
    )  # fmt: skip
    return Result(target_id, node_id, link, record=record)


def join_route(  # noqa: PLR0913, PLR0917 — the run's seam, the record, the node, where it works, the facts
    toolchain: Toolchain,
    tc: ResolvedToolchain,
    tree: Path,
    target_id: str,
    found: closing.Closable,
    workdir: Path,
    *,
    gdoc: Mapping[str, Any],
    facts: Facts,
    timeout_s: float,
) -> Result:
    """F28-T7: the closure through a route: the assembly joined with its children by the kernel."""
    node_id, link = found.node, found.link
    partial = route_partial(gdoc, link)
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
        spec.write_text(json.dumps(children(tree, target_id, link.inputs)), encoding="utf-8")
    except outline_graph.BuildError as exc:
        return Result(target_id, node_id, link, reason=BUILD_FAILED, detail=str(exc)[:_DETAIL_CAP])
    out = job.search_path[0] / module_output_path(job.module, ".olean")
    result = toolchain.close(
        tc, CloseRequest(job.file, job.module, job.decl, spec, out), job.search_path,
        timeout_s=timeout_s,
    )  # fmt: skip
    doc = result.doc or {}
    if not result.ok or not doc.get("ok"):
        detail = str(doc.get("error") or result.output or "the join gave no module")
        return Result(target_id, node_id, link, reason=JOIN_FAILED, detail=detail[:_DETAIL_CAP])
    record = _record(
        tree, target_id, node_id, link, facts,
        path=partial, text=None, hash=digest, axioms=doc.get("axioms"),
    )  # fmt: skip
    return Result(target_id, node_id, link, record=record)


def sweep(  # noqa: PLR0913 — the run's seam, the tree, the target, where it works, the facts
    toolchain: Toolchain,
    tc: ResolvedToolchain,
    tree: Path,
    target_id: str,
    workdir: Path,
    *,
    facts: Facts,
    timeout_s: float,
) -> list[Result]:
    """Close every node of the target whose inputs are all proved, writing each record into
    ``tree`` (a scratch export) as it goes, and repeat until nothing more is ready: one run climbs
    the whole chain. A node with a record already, or whose join failed in this run, is not tried
    again; a failure is reported and changes nothing."""
    results: list[Result] = []
    tried: set[str] = set()
    nodes_dir = layout.graph_nodes_dir(tree, target_id)
    while True:
        tg = graphmod.load_target(tree, target_id)
        gdoc = products.graph_doc(tg, None)
        ready = [
            c
            for c in closing.closable(gdoc)
            if c.ready
            and c.node not in tried
            and not closure.path_for(nodes_dir / c.node).is_file()
        ]
        if not ready:
            return results
        for found in ready:
            tried.add(found.node)
            work = workdir / found.node
            if found.link.kind == "route":
                result = join_route(
                    toolchain, tc, tree, target_id, found, work,
                    gdoc=gdoc, facts=facts, timeout_s=timeout_s,
                )  # fmt: skip
            else:
                result = join_link(
                    toolchain, tc, tree, target_id, found, work, facts=facts, timeout_s=timeout_s
                )
            if result.record is not None:
                closure.write(nodes_dir / found.node, result.record)
            results.append(result)
