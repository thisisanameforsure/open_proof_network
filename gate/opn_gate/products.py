"""The merge products (F03-T3; R4-R7, R9-R11; D-25, D-28, D-35).

``generate`` derives every target (``graph.py``), builds the four documents — each target's
``graph.json``, the graph-wide ``frontier.json``, ``targets/index.json`` and ``info.json`` —
plus every node's ``CONTEXT.json`` (F10-R3, ``context.py``),
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

from opn_gate import context, defs, intake, layout, qa, records, schemas, watch
from opn_gate import fidelity as fidelitymod
from opn_gate import graph as graphmod
from opn_gate.graph import GraphError, NodeFacts, TargetGraph
from opn_gate.toolchain import ResolvedToolchain, Toolchain, UsedConstantsRequest

log = logging.getLogger(__name__)

PROTOCOL_VERSION = "3.12"  # docs/architecture_decisions_v_3_12.html, implemented by F11-T2
GRAPH_SCHEMA = "graph/v3"  # F12-R13: a related variant's relevance signature (v2: F07-R8)
FRONTIER_SCHEMA = "frontier/v2"  # F11-R4: the target's D-33 dormancy, as a fact on each entry
#: F11-R12 renames D-9's second rung and F11-R3/R4 add the derived fields. v2 was already spent
#: on F07-R8's node counts and D-34 forbids editing it, so the rename lands at v3 (F11-Q9).
#: F12-R14 adds the QA pass state per subject, the counted attempts and the drift flag: v4.
INDEX_SCHEMA = "targets-index/v4"
INFO_SCHEMA = "info/v1"
CLAIMS_SCHEMA = "claims/v1"
CLAIMS_FILE = "claims.json"
TAGS_CACHE = ".tags-cache.json"
MATHLIB_PREFIX = "Mathlib"
DEFAULT_FIDELITY = fidelitymod.DEFAULT_GRADE
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
    # F11-R2, F01-Q2: the target's definitions first; the Context may import them.
    problem = defs.compile_all(toolchain, tc, node.path.parents[1], workdir)
    if problem is not None:
        msg = f"{node.target_id}: {problem.message}; cannot tag {node.node_id}"
        raise GraphError(msg)
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


@dataclass(frozen=True)
class TargetFacts:
    """What the index publishes about a target, all of it derived (F03-R9; F11-R3, R4)."""

    status: str
    claimable: bool
    fidelity: str
    reasons: tuple[str, ...] = ()
    subjects: tuple[fidelitymod.SubjectGrade, ...] = ()
    posting: dict[str, Any] | None = None
    track: str | None = None
    qa: dict[str, dict[str, Any]] = field(default_factory=dict)  # subject -> pass state (F12)
    attempts: dict[str, int] = field(default_factory=lambda: {"counted": 0, "recorded": 0})
    drift: dict[str, Any] | None = None

    @property
    def dormant(self) -> bool:
        return self.status == intake.DORMANT


def target_facts(tg: TargetGraph) -> TargetFacts:
    """(status, claimable, fidelity) and the rest, for the index (R9; Q4, Q5; F11-R3, R4).

    Two eras meet here. A target with no ``target.yaml`` predates F11: its declaration says
    whether it is claimable and at what grade, which is F03-Q4/Q5 and is what the tutorial graph
    still runs on. A curated target derives all three — the grade from its fidelity certificates
    (F11-R3), claimability from status, grade and posting (F11-R4) — and the declaration's own
    ``claimable`` and ``fidelity`` fields are ignored, because a derived value with a second
    writable home is a value that will disagree with itself.
    """
    decl = tg.declaration.doc if tg.declaration is not None else {}
    doc = intake.load_doc(tg.path)
    subjects = tuple(fidelitymod.subject_grades(tg.path))
    derived_grade = fidelitymod.target_grade(tg.path)
    fallback = str(decl.get("fidelity", DEFAULT_FIDELITY))
    grade = derived_grade if derived_grade is not None else fallback
    legacy_claimable = bool(decl.get("claimable", tg.nodes[tg.root].tutorial))
    if tg.statuses[tg.root] == "proved":
        status = "resolved"
    elif "status" in decl:
        status = str(decl["status"])
    elif doc is not None:
        status = intake.LISTED
    else:
        status = "active" if legacy_claimable else "listed"
    if doc is None:
        return TargetFacts(status=status, claimable=legacy_claimable, fidelity=grade)
    # F12-R11: an upstream edit that stands on the root as it is freezes proving compute.
    root_hash = tg.nodes[tg.root].statement_hash
    drift = watch.drift_state(tg.path, root_hash)
    claimable, reasons = intake.claimability(doc, status=status, grade=grade, drifted=drift.frozen)
    # F12-R14: the pass state per subject, the counted attempts and the flag, all derived.
    routed = qa.routed_by_claims(tg.path, tg.root)
    pass_states = {
        row.subject: qa.pass_state(tg.path, row.subject, spec=tg.spec, routed=routed).as_dict()
        for row in subjects
        if row.subject in fidelitymod.subjects_of(tg.path)
    }
    attempts = qa.attempts_state(tg.path, root_hash)
    return TargetFacts(
        status=status,
        claimable=claimable,
        fidelity=grade,
        reasons=reasons,
        subjects=subjects,
        posting=doc.get("posting"),
        track=str(doc["track"]),
        qa=pass_states,
        attempts={"counted": attempts.m, "recorded": attempts.m + len(attempts.stale)},
        drift=drift.as_dict(),
    )


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
                # F12-R13: a related variant is pertinent only with its one signature.
                "relevance": qa.relevance_of(n.path, n.relation),
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
    dormant: bool,
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
        # D-33: a dormancy declaration refuses no claim, so this is a fact and not a gate. It
        # rides on the entry rather than only on the index so an agent choosing work sees it
        # without a second fetch (F11-R4).
        "dormant": dormant,
    }


def qa_summary(state: dict[str, Any] | None) -> dict[str, Any]:
    """F12-R14: the pass state as the index carries it — a subject with no record, or one that
    predates F11, shows every check unrun and the pass incomplete."""
    if state is None:
        return {
            "complete": False,
            "stale": False,
            "checks": dict.fromkeys(qa.CHECKS),
            "unrouted_findings": 0,
            "fresh_records": 0,
        }
    return {
        "complete": bool(state["complete"]),
        "stale": bool(state["stale"]),
        "checks": {c: state["checks"].get(c) for c in qa.CHECKS},
        "unrouted_findings": int(state["unrouted_findings"]),
        "fresh_records": int(state["fresh_records"]),
    }


def index_doc(targets: list[TargetGraph], rendered_from: str | None) -> dict[str, Any]:
    out = []
    for tg in targets:
        facts = target_facts(tg)
        counts = dict.fromkeys(graphmod.ALL_STATUSES, 0)
        for status in tg.statuses.values():
            counts[status] += 1
        out.append(
            {
                "target_id": tg.target_id,
                "root": tg.root,
                "root_statement_hash": tg.nodes[tg.root].statement_hash,
                "fidelity": facts.fidelity,
                "status": facts.status,
                "mathlib_sha": tg.spec["mathlib_sha"],
                "node_counts": counts,
                "claimable": facts.claimable,
                "track": facts.track,
                "subjects": [
                    {**row.as_dict(), "qa": qa_summary(facts.qa.get(row.subject))}
                    for row in facts.subjects
                ],
                "posting": facts.posting,
                "not_claimable": list(facts.reasons),
                "attempts": facts.attempts,
                "drift": facts.drift,
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
    reader = context.DiskReader(graph_root)
    for target_id in target_ids(graph_root):
        tg = graphmod.load_target(graph_root, target_id)
        products.targets.append(tg)
        gdoc = schemas.validate(graph_doc(tg, rendered_from), GRAPH_SCHEMA)
        products.files[Path("targets") / target_id / "graph.json"] = schemas.canonical_json(gdoc)
        # F10-R3: one context bundle per node, a rendering of the same facts, bot-owned (Q2).
        states = context.graph_states(gdoc)
        for node_id in tg.order:
            products.files[Path(context.context_path(target_id, node_id))] = context.render(
                reader, target_id, node_id, states=states, rendered_from=rendered_from
            )
        facts = target_facts(tg)
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
                    claimable=facts.claimable,
                    dormant=facts.dormant,
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
