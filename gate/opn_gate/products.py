"""The merge products (F03-T3; R4-R7, R9-R11; D-25, D-28, D-35).

``generate`` derives every target (``graph.py``), builds the four documents — each target's
``graph.json``, the graph-wide ``frontier.json``, ``targets/index.json`` and ``info.json`` —
validates each against its schema, and only then writes them all, canonically (sorted keys,
two-space indent, LF, trailing newline), so two runs over one commit are byte-identical (R11)
and a defective graph leaves the tree untouched (R3, C7). It also writes each node's derived
status into ``META.yaml`` (R2).

Library tags (R6) come from ``opn-used-constants`` over ``Statement.lean`` through the
``Toolchain`` seam and are cached per statement hash in ``targets/<id>/.tags-cache.json``. A
Mathlib-free graph (``mathlib_sha: null``) has no Mathlib namespaces to reference, so its tags
are ``[]`` without a scan.
"""

from __future__ import annotations

import json
import logging
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from opn_gate import graph as graphmod
from opn_gate import layout, records, schemas
from opn_gate.graph import GraphError, NodeFacts, TargetGraph
from opn_gate.toolchain import ResolvedToolchain, Toolchain, UsedConstantsRequest

log = logging.getLogger(__name__)

PROTOCOL_VERSION = "3.11"  # what the code implements; docs/architecture_decisions_v_3_12.html
# is the current protocol. v3.12 renamed D-9's second rung to screened-and-signed, which is a
# target-status/targets-index schema bump (D-34: versioned, never edited) budgeted into F11-T2.
# This value moves to "3.12" in that task, with the goldens regenerated in the same commit.
GRAPH_SCHEMA = "graph/v2"  # F07-R8: refuted, defective and the cause field
FRONTIER_SCHEMA = "frontier/v1"
INDEX_SCHEMA = "targets-index/v2"  # F07-R8: the two new statuses in node_counts
INFO_SCHEMA = "info/v1"
CLAIMS_SCHEMA = "claims/v1"
CLAIMS_FILE = "claims.json"
TAGS_CACHE = ".tags-cache.json"
MATHLIB_PREFIX = "Mathlib"
DEFAULT_FIDELITY = "mechanical-only"
KEEP_FILE = ".gitkeep"

Scanner = Callable[[NodeFacts], list[str]]


# --- library tags (R6) ---------------------------------------------------------------------------


def library_tags_from_modules(modules: list[str | None]) -> list[str]:
    """``Mathlib.Order.Basic`` -> ``Order``: the sorted set of top-level Mathlib namespaces."""
    tags: set[str] = set()
    for module in modules:
        if not module:
            continue
        parts = module.split(".")
        if parts[0] == MATHLIB_PREFIX and len(parts) > 1:
            tags.add(parts[1])
    return sorted(tags)


def scan_statement(
    toolchain: Toolchain, tc: ResolvedToolchain, node: NodeFacts, workdir: Path
) -> list[str]:
    """R6 through the seam: compile the node's repo Context, then read the statement's
    constants. Runs only where contributor Lean may run (C9): the caller picks the sandbox."""
    root = workdir / "src"
    build = workdir / "build"
    dest = root / "Nodes" / node.node_id
    dest.mkdir(parents=True, exist_ok=True)
    build.mkdir(parents=True, exist_ok=True)
    for name in ("Statement.lean", "Context.lean"):
        shutil.copy(node.path / name, dest / name)
    context = layout.node_module(node.node_id, "Context")
    elab = toolchain.elaborate(tc, dest / "Context.lean", context, build, root=root)
    if not elab.ok:
        msg = f"{context} does not elaborate; cannot tag {node.node_id}"
        raise GraphError(msg)
    statement = layout.load_node(node.path, node.target_id)
    if isinstance(statement, list):
        msg = f"node {node.node_id}: " + "; ".join(d.message for d in statement)
        raise GraphError(msg)
    result = toolchain.used_constants(
        tc,
        UsedConstantsRequest(
            dest / "Statement.lean",
            layout.node_module(node.node_id, "Statement"),
            statement.statement.decl_name,
        ),
        [build],
    )
    if not result.ok:
        msg = f"opn-used-constants failed on {node.node_id}: {result.error or result.output}"
        raise GraphError(msg)
    modules = [c.get("module") for c in result.doc.get("constants") or [] if isinstance(c, dict)]
    return library_tags_from_modules([str(m) if m is not None else None for m in modules])


class TagCache:
    """``targets/<id>/.tags-cache.json``: statement hash -> tags; bot-owned, sorted."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.entries: dict[str, list[str]] = {}
        if path.is_file():
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                self.entries = {str(k): [str(t) for t in v] for k, v in raw.items()}
        self.dirty = False

    def tags(self, node: NodeFacts, scanner: Scanner | None) -> list[str]:
        if node.statement_hash in self.entries:
            return list(self.entries[node.statement_hash])
        found = scanner(node) if scanner is not None else []
        self.entries[node.statement_hash] = sorted(found)
        self.dirty = True
        return list(self.entries[node.statement_hash])

    def rendered(self) -> bytes:
        return schemas.canonical_json(dict(sorted(self.entries.items())))


def load_claims(graph_root: Path) -> dict[str, dict[str, Any]]:
    """The committed ``claims.json`` snapshot the service produced (F05-R10, Q3).

    Absent or defective, the frontier's claim fields are empty: a claim registry is
    operational, never evidentiary, so it never blocks or corrupts a merge (C7, C9).
    """
    path = graph_root / CLAIMS_FILE
    if not path.is_file():
        return {}
    try:
        doc = schemas.load_json(path, CLAIMS_SCHEMA)
    except schemas.SchemaError as exc:
        log.warning("%s does not validate; the frontier carries no claims: %s", CLAIMS_FILE, exc)
        return {}
    nodes = doc.get("nodes") or {}
    return {str(k): dict(v) for k, v in nodes.items() if isinstance(v, dict)}


# --- documents ---------------------------------------------------------------------------------


def annex_present(node_dir: Path) -> bool:
    annex = node_dir / "annex"
    return annex.is_dir() and any(p.name != KEEP_FILE for p in annex.iterdir())


def target_facts(tg: TargetGraph) -> tuple[str, bool, str]:
    """(status, claimable, fidelity) for the index (R9; Q4, Q5)."""
    decl = tg.declaration.doc if tg.declaration is not None else {}
    root_tutorial = tg.nodes[tg.root].tutorial
    claimable = bool(decl.get("claimable", root_tutorial))
    fidelity = str(decl.get("fidelity", DEFAULT_FIDELITY))
    if tg.statuses[tg.root] == "proved":
        status = "resolved"
    elif "status" in decl:
        status = str(decl["status"])
    else:
        status = "active" if claimable else "listed"
    return status, claimable, fidelity


def graph_doc(tg: TargetGraph, rendered_from: str | None) -> dict[str, Any]:
    nodes = []
    causes = graphmod.derive_causes(tg.nodes, tg.statuses)
    for node_id in tg.order:
        n = tg.nodes[node_id]
        # A refuted or defective node has a merged artifact too, and the commit that carries it
        # is as much a fact as a proof's (D-12): record it for all three resolved statuses.
        resolved = tg.statuses[node_id] in graphmod.RESOLVED_STATUSES and n.proof is not None
        nodes.append(
            {
                "node_id": node_id,
                "status": tg.statuses[node_id],
                "cause": causes.get(node_id),
                "deps": list(n.deps),
                "origin": n.origin,
                "statement_hash": n.statement_hash,
                "relation": n.relation,
                "tutorial": n.tutorial,
                "trust_base": n.proof.trust_base if resolved and n.proof else None,
                "proof_commit": n.proof.merge_commit if resolved and n.proof else None,
            }
        )
    return {
        "schema": GRAPH_SCHEMA,
        "target_id": tg.target_id,
        "root": tg.root,
        "rendered_from": rendered_from,
        "nodes": nodes,
    }


def in_frontier(status: str, node: NodeFacts) -> bool:
    """R5: ready or speculative, plus every variant whose question is still open.

    A refuted or defective variant is as settled as a proved one (D-12), so it leaves the
    frontier too — the frontier is what is still worth attacking, not what still lacks a proof.
    """
    if status in graphmod.FRONTIER_STATUSES:
        return True
    return node.origin == "variant" and status not in graphmod.RESOLVED_STATUSES


def frontier_entry(
    tg: TargetGraph,
    node: NodeFacts,
    *,
    claimable: bool,
    ready_since: str | None,
    tags: list[str],
    claims: dict[str, Any] | None = None,
) -> dict[str, Any]:
    status = tg.statuses[node.node_id]
    attempts = records.load_attempts(node.path)
    for name in attempts.invalid_files:
        log.warning(
            "%s/%s: attempt %s does not validate (counted as invalid)",
            tg.target_id,
            node.node_id,
            name,
        )
    return {
        "node_id": node.node_id,
        "target_id": tg.target_id,
        "statement_hash": node.statement_hash,
        "relation": node.relation,
        "origin": node.origin,
        "tags": {"deps": sorted(node.deps), "library": tags},
        **attempts.as_dict(),
        "ready_since": ready_since if status == "ready" else None,
        "claims": claims if claims is not None else {"active": [], "history_count": 0},
        "annex_present": annex_present(node.path),
        "bounty": False,
        "claimable": claimable and in_frontier(status, node),
        "tutorial": node.tutorial,
    }


def index_doc(targets: list[TargetGraph], rendered_from: str | None) -> dict[str, Any]:
    out = []
    for tg in targets:
        status, claimable, fidelity = target_facts(tg)
        counts = dict.fromkeys(graphmod.ALL_STATUSES, 0)
        for s in tg.statuses.values():
            counts[s] += 1
        out.append(
            {
                "target_id": tg.target_id,
                "root": tg.root,
                "root_statement_hash": tg.nodes[tg.root].statement_hash,
                "fidelity": fidelity,
                "status": status,
                "mathlib_sha": tg.spec["mathlib_sha"],
                "node_counts": counts,
                "claimable": claimable,
            }
        )
    return {"schema": INDEX_SCHEMA, "rendered_from": rendered_from, "targets": out}


def info_doc(
    graph_root: Path, targets: list[TargetGraph], rendered_from: str | None
) -> dict[str, Any]:
    index: dict[str, list[int]] = {}
    for schema_id in schemas.known_schemas():
        name, _, version = schema_id.partition("/v")
        index.setdefault(name, []).append(int(version))
    return {
        "schema": INFO_SCHEMA,
        "protocol_version": PROTOCOL_VERSION,
        "schemas": {k: sorted(v) for k, v in sorted(index.items())},
        "targets": {
            tg.target_id: {
                "gate_spec_hash": schemas.content_hash(
                    layout.gate_spec_path(graph_root, tg.target_id).read_bytes()
                ),
                "network_commit": tg.spec["network_commit"],
            }
            for tg in targets
        },
        "rate_limit_policy": None,
        "rendered_from": rendered_from,
    }


# --- generation --------------------------------------------------------------------------------


@dataclass
class Products:
    """Every file the generator would write, validated, keyed by path relative to the root."""

    files: dict[Path, bytes] = field(default_factory=dict)
    meta_status: dict[Path, str] = field(default_factory=dict)  # node dir -> status
    targets: list[TargetGraph] = field(default_factory=list)

    def write(self, root: Path, *, write_meta: bool = True) -> list[Path]:
        written: list[Path] = []
        for rel, data in sorted(self.files.items()):
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.is_file() or path.read_bytes() != data:
                path.write_bytes(data)
                written.append(rel)
        if write_meta:
            for node_dir, status in sorted(self.meta_status.items()):
                if graphmod.write_meta_status(root / node_dir, status):
                    written.append(node_dir / "META.yaml")
        return written


def target_ids(graph_root: Path) -> list[str]:
    targets = graph_root / "targets"
    if not targets.is_dir():
        return []
    return sorted(p.name for p in targets.iterdir() if p.is_dir())


def generate(
    graph_root: Path,
    *,
    rendered_from: str | None,
    commit_time: str,
    scanner: Scanner | None = None,
    previous_frontier: dict[str, Any] | None = None,
    claims: dict[str, dict[str, Any]] | None = None,
) -> Products:
    """Build and validate every product without writing anything (R11; AC5)."""
    if previous_frontier is None:
        committed = graph_root / "frontier.json"
        if committed.is_file():
            previous_frontier = json.loads(committed.read_text(encoding="utf-8"))
    previous = graphmod.previous_ready_since(previous_frontier)
    registry = load_claims(graph_root) if claims is None else claims
    products = Products()
    entries: list[dict[str, Any]] = []
    for target_id in target_ids(graph_root):
        tg = graphmod.load_target(graph_root, target_id)
        products.targets.append(tg)
        products.files[Path("targets") / target_id / "graph.json"] = schemas.canonical_json(
            schemas.validate(graph_doc(tg, rendered_from), GRAPH_SCHEMA)
        )
        _status, claimable, _fidelity = target_facts(tg)
        ready_since = graphmod.ready_since_map(previous, tg.statuses, commit_time)
        # R6: only a Mathlib-pinned graph has library tags to scan for and a cache to keep.
        cache = TagCache(tg.path / TAGS_CACHE) if tg.spec["mathlib_sha"] is not None else None
        for node_id in tg.order:
            node = tg.nodes[node_id]
            products.meta_status[node.path.relative_to(graph_root)] = tg.statuses[node_id]
            if not in_frontier(tg.statuses[node_id], node):
                continue
            entries.append(
                frontier_entry(
                    tg,
                    node,
                    claimable=claimable,
                    ready_since=ready_since[node_id],
                    tags=cache.tags(node, scanner) if cache is not None else [],
                    claims=registry.get(node_id),
                )
            )
        if cache is not None and cache.dirty:
            products.files[Path("targets") / target_id / TAGS_CACHE] = cache.rendered()
    entries.sort(key=lambda e: (str(e["node_id"]), str(e["target_id"])))
    frontier = {"schema": FRONTIER_SCHEMA, "rendered_from": rendered_from, "entries": entries}
    products.files[Path("frontier.json")] = schemas.canonical_json(
        schemas.validate(frontier, FRONTIER_SCHEMA)
    )
    products.files[Path("targets") / "index.json"] = schemas.canonical_json(
        schemas.validate(index_doc(products.targets, rendered_from), INDEX_SCHEMA)
    )
    products.files[Path("info.json")] = schemas.canonical_json(
        schemas.validate(info_doc(graph_root, products.targets, rendered_from), INFO_SCHEMA)
    )
    return products
