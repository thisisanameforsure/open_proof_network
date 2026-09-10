"""Graph derivation (F03-T2; R1, R2, R3, R8; Q1, Q2, Q3, Q5).

From a target's node directories, the graph's attestations and the status records, derive every
node's status, the target's root, and the ``ready_since`` timestamps — deterministically, from
committed facts and git alone (Q2). A dependency cycle, a dep that is not a node, or an
ambiguous root is a graph defect: ``GraphError`` names it and the caller writes nothing (R3, C7).
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from opn_gate import layout, records, schemas
from opn_gate.bounce import TIMESTAMP_FORMAT
from opn_gate.records import StatusRecord

DERIVED_STATUSES: tuple[str, ...] = ("ready", "blocked", "proved")
RECORD_STATUSES: tuple[str, ...] = ("speculative", "superseded", "stale", "disputed", "abandoned")
ALL_STATUSES: tuple[str, ...] = (*DERIVED_STATUSES, *RECORD_STATUSES)
FRONTIER_STATUSES: tuple[str, ...] = ("ready", "speculative")
TRUST_KERNEL = "kernel"
_RELATION_RE = re.compile(r"^\s*--\s*relation:\s*(?P<label>resolves|partial|related)\s*$", re.M)
_META_STATUS_RE = re.compile(r"^status:[ \t]*[^\n]*$", re.M)


class GraphError(ValueError):
    """The dependency relation or the target's records are defective (R3)."""


@dataclass(frozen=True)
class Proof:
    """What an attestation proves: the merge commit and the trust base (F02-R9)."""

    merge_commit: str
    trust_base: str
    attestation: str  # file name, for the record


@dataclass(frozen=True)
class NodeFacts:
    node_id: str
    target_id: str
    path: Path
    statement_hash: str
    deps: tuple[str, ...]
    origin: str
    tutorial: bool
    relation: str | None
    proof: Proof | None
    override: StatusRecord | None


@dataclass(frozen=True)
class TargetGraph:
    target_id: str
    path: Path
    spec: dict[str, Any]
    nodes: dict[str, NodeFacts]  # by node id, insertion order lexical
    statuses: dict[str, str]
    root: str
    declaration: StatusRecord | None

    @property
    def order(self) -> list[str]:
        return sorted(self.nodes)


# --- loading ----------------------------------------------------------------------------------


def load_attestations(graph_root: Path) -> list[tuple[str, dict[str, Any]]]:
    """Every committed attestation, by file name; a malformed one is a graph defect."""
    out: list[tuple[str, dict[str, Any]]] = []
    att_dir = graph_root / "attestations"
    if not att_dir.is_dir():
        return out
    for path in sorted(p for p in att_dir.iterdir() if p.suffix == ".json"):
        try:
            out.append((path.name, schemas.load_json(path)))
        except schemas.SchemaError as exc:
            msg = f"attestation {path} is malformed: {exc}"
            raise GraphError(msg) from exc
    return out


def proof_for(
    node_id: str, statement_hash: str, attestations: list[tuple[str, dict[str, Any]]]
) -> Proof | None:
    """R1: the first merged passing attestation for the node's current statement (AC3)."""
    for name, doc in attestations:
        if (
            doc.get("node_id") == node_id
            and doc.get("statement_hash") == statement_hash
            and doc.get("verdict") == "pass"
            and doc.get("merge_commit")
        ):
            return Proof(
                merge_commit=str(doc["merge_commit"]),
                trust_base=str(doc.get("trust_base") or TRUST_KERNEL),
                attestation=name,
            )
    return None


def relation_of(node_dir: Path, origin: str) -> str | None:
    """D-30 label: a variant's ``Relation.lean`` header names it; no header means ``related``."""
    if origin != "variant":
        return None
    relation = node_dir / "Relation.lean"
    if relation.is_file():
        m = _RELATION_RE.search(relation.read_text(encoding="utf-8"))
        if m:
            return m.group("label")
    return "related"


def load_nodes(
    graph_root: Path, target_id: str, attestations: list[tuple[str, dict[str, Any]]]
) -> dict[str, NodeFacts]:
    nodes_dir = layout.graph_nodes_dir(graph_root, target_id)
    facts: dict[str, NodeFacts] = {}
    for node_dir in sorted(p for p in nodes_dir.iterdir() if p.is_dir()):
        loaded = layout.load_node(node_dir, target_id)
        if isinstance(loaded, list):
            msg = f"node {node_dir.name}: " + "; ".join(d.message for d in loaded)
            raise GraphError(msg)
        raw_deps = loaded.meta.get("deps")
        deps = tuple(str(d) for d in raw_deps) if isinstance(raw_deps, list) else ()
        origin = str(loaded.meta.get("origin", "authored"))
        statement_hash = loaded.statement.statement_hash
        facts[loaded.node_id] = NodeFacts(
            node_id=loaded.node_id,
            target_id=target_id,
            path=node_dir,
            statement_hash=statement_hash,
            deps=deps,
            origin=origin,
            tutorial=bool(loaded.meta.get("tutorial", False)),
            relation=relation_of(node_dir, origin),
            proof=proof_for(loaded.node_id, statement_hash, attestations),
            override=records.load_node_status(node_dir),
        )
    return facts


# --- derivation --------------------------------------------------------------------------------


def missing_dep(edges: dict[str, tuple[str, ...]]) -> tuple[str, str] | None:
    """The first (node, dep) pair whose dep is not a node, or ``None``."""
    for node_id in sorted(edges):
        for dep in edges[node_id]:
            if dep not in edges:
                return node_id, dep
    return None


def find_cycle(edges: dict[str, tuple[str, ...]]) -> list[str] | None:
    """The first dependency cycle in ``edges``, as the path that closes it, or ``None``.

    Over ids alone, so admission (F08-R1) can ask the same question of a graph plus one proposed
    node without building the full node records F03 derives statuses from.
    """
    state: dict[str, int] = {}  # 1 = on the current path, 2 = done
    found: list[str] | None = None

    def visit(node_id: str, path: list[str]) -> None:
        nonlocal found
        if found is not None:
            return
        mark = state.get(node_id, 0)
        if mark == 2:
            return
        if mark == 1:
            found = [*path[path.index(node_id) :], node_id]
            return
        state[node_id] = 1
        for dep in edges.get(node_id, ()):
            visit(dep, [*path, node_id])
        state[node_id] = 2

    for node_id in sorted(edges):
        visit(node_id, [])
    return found


def check_dag(nodes: dict[str, NodeFacts]) -> None:
    """R3: every dep exists and the relation is acyclic; the first problem is named."""
    edges = {node_id: nodes[node_id].deps for node_id in nodes}
    absent = missing_dep(edges)
    if absent is not None:
        node_id, dep = absent
        msg = f"node {node_id!r} declares dep {dep!r}, which is not a node"
        raise GraphError(msg)
    cycle = find_cycle(edges)
    if cycle is not None:
        msg = "dependency cycle: " + " -> ".join(cycle)
        raise GraphError(msg)


def derive_statuses(nodes: dict[str, NodeFacts]) -> dict[str, str]:
    """R1: proved > blocked > ready from the facts; a status record overrides all three."""
    check_dag(nodes)
    statuses: dict[str, str] = {}

    def status_of(node_id: str) -> str:
        if node_id in statuses:
            return statuses[node_id]
        node = nodes[node_id]
        if node.override is not None:
            result = node.override.status
        elif node.proof is not None:
            result = "proved"
        elif any(status_of(dep) != "proved" for dep in node.deps):
            result = "blocked"
        else:
            result = "ready"
        statuses[node_id] = result
        return result

    for node_id in sorted(nodes):
        status_of(node_id)
    return dict(sorted(statuses.items()))


def find_root(nodes: dict[str, NodeFacts], declaration: StatusRecord | None) -> str:
    """Q5: the declared root, else the unique node nothing depends on."""
    if declaration is not None and declaration.doc.get("root"):
        root = str(declaration.doc["root"])
        if root not in nodes:
            msg = f"declared root {root!r} is not a node"
            raise GraphError(msg)
        return root
    depended_on = {dep for n in nodes.values() for dep in n.deps}
    sinks = sorted(n for n in nodes if n not in depended_on)
    if len(sinks) != 1:
        msg = (
            f"root is ambiguous: {len(sinks)} nodes have no dependents ({', '.join(sinks)}); "
            "declare one in targets/<id>/status/ (target-status/v1 root)"
        )
        raise GraphError(msg)
    return sinks[0]


def load_target(graph_root: Path, target_id: str) -> TargetGraph:
    """Everything the products need about one target, statuses derived."""
    target_dir = graph_root / "targets" / target_id
    spec = schemas.load_json(layout.gate_spec_path(graph_root, target_id), "gate-spec/v1")
    attestations = load_attestations(graph_root)
    nodes = load_nodes(graph_root, target_id, attestations)
    if not nodes:
        msg = f"target {target_id!r} has no nodes"
        raise GraphError(msg)
    declaration = records.load_target_status(target_dir)
    statuses = derive_statuses(nodes)
    return TargetGraph(
        target_id=target_id,
        path=target_dir,
        spec=spec,
        nodes=nodes,
        statuses=statuses,
        root=find_root(nodes, declaration),
        declaration=declaration,
    )


# --- ready_since and META status --------------------------------------------------------------


def ready_since_map(
    previous: Mapping[str, str | None], statuses: Mapping[str, str], commit_time: str
) -> dict[str, str | None]:
    """R8: keep the old timestamp for a node still ready; stamp a newly ready node with the
    merge commit's committer time; anything else carries no timestamp."""
    out: dict[str, str | None] = {}
    for node_id, status in statuses.items():
        if status != "ready":
            out[node_id] = None
            continue
        kept = previous.get(node_id)
        out[node_id] = kept if kept else commit_time
    return out


def previous_ready_since(frontier_doc: dict[str, Any] | None) -> dict[str, str | None]:
    if not frontier_doc:
        return {}
    return {
        str(e["node_id"]): e.get("ready_since")
        for e in frontier_doc.get("entries") or []
        if isinstance(e, dict) and "node_id" in e
    }


def commit_timestamp(graph_root: Path, commit: str) -> str:
    """The committer time of ``commit`` as the products' UTC timestamp (Q2: git, not the clock)."""
    proc = subprocess.run(
        ["git", "-C", str(graph_root), "log", "-1", "--format=%cI", commit],
        capture_output=True,
        text=True,
        check=True,
    )
    when = datetime.fromisoformat(proc.stdout.strip())
    return when.astimezone(UTC).strftime(TIMESTAMP_FORMAT)


def write_meta_status(node_dir: Path, status: str) -> bool:
    """R2, Q1: rewrite only the ``status:`` line of META.yaml; True when it changed."""
    if status not in ALL_STATUSES:
        msg = f"not a node status: {status!r}"
        raise ValueError(msg)
    path = node_dir / "META.yaml"
    text = path.read_text(encoding="utf-8")
    m = _META_STATUS_RE.search(text)
    if not m:
        msg = f"{path} has no status line to update"
        raise GraphError(msg)
    replacement = f"status: {status}"
    if m.group(0) == replacement:
        return False
    path.write_text(text[: m.start()] + replacement + text[m.end() :], encoding="utf-8")
    return True
