"""A node's closing proof, composed from its merged assembly and its proved holes (F28-T2;
draft decisions v3.41).

``closing`` says which nodes are closable and by which link; this module writes the proof for one
of them. For a route (F28-R4, R6) that is the route's merged assembly with each hole's ``sorry``
replaced by the hole node's theorem, composed by ``opn-close`` in the step-3 sandbox over the
same staging the outline job uses (``outline_graph.build``: the assembly staged as the node's
``Proof`` module, everything it imports compiled, the node's own ``Context`` with its children's
signatures among them). The composed text is a proposal: the gate judges it like any proof
(D-12 v3.41), so nothing here is trusted and nothing here writes to the graph.

Claims and variants (F28-R5) are F28-T3's; a link of either kind is answered
``link-unsupported`` until then.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from opn_gate import closing, layout, outline, outline_graph, schemas
from opn_gate.toolchain import CloseRequest, ResolvedToolchain, Toolchain

#: Why no proof was composed. Each is a fact about the record or the run, never a guess.
NOT_CLOSABLE = "not-closable"
NOT_READY = "not-ready"
LINK_UNSUPPORTED = "link-unsupported"
BUILD_FAILED = "build-failed"
COMPOSE_FAILED = "compose-failed"

_DETAIL_CAP = 2000


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
        return Result(target_id, node_id, found.link, reason=LINK_UNSUPPORTED)
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
