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

import functools
import json
import logging
import shutil
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from opn_gate import (
    context,
    defs,
    evidence,
    explainers,
    formalizations,
    intake,
    layout,
    postmerge,
    qa,
    records,
    schemas,
    signed,
    steward,
    watch,
    writeup,
)
from opn_gate import fidelity as fidelitymod
from opn_gate import graph as graphmod
from opn_gate import policy as policymod
from opn_gate.graph import GraphError, NodeFacts, TargetGraph
from opn_gate.signer import Signer
from opn_gate.toolchain import ResolvedToolchain, Toolchain, UsedConstantsRequest

log = logging.getLogger(__name__)

PROTOCOL_VERSION = "3.18"  # docs/architecture_decisions.html (v3.18, F08-R15)
GRAPH_SCHEMA = "graph/v3"  # F12-R13: a related variant's relevance signature (v2: F07-R8)
FRONTIER_SCHEMA = "frontier/v3"  # T7: attempts counts partials (v2, F11-R4: D-33 dormancy)
#: F11-R12 renames D-9's second rung and F11-R3/R4 add the derived fields. v2 was already spent
#: on F07-R8's node counts and D-34 forbids editing it, so the rename lands at v3 (F11-Q9).
#: F12-R14 adds the QA pass state per subject, the counted attempts and the drift flag: v4.
#: F14-R1, R9: claimable while listed; the statement evidence, the step-9 basis and the
#: formalizations: v5.
#: F15-R9: the policy state at the top; per target the active stewards, the digestion state with
#: its counts, the calibration flag, and `no-steward` among the reasons: v6.
INDEX_SCHEMA = "targets-index/v6"
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
        #: R13: node ids whose scan raised this run. No tags, no entry, not on the frontier, and
        #: never written: a cached failure would hide a transient toolchain fault forever (C7).
        self.failed: set[str] = set()

    def tags(self, node: NodeFacts, scanner: Scanner | None) -> list[str]:
        if node.statement_hash in self.entries:
            return list(self.entries[node.statement_hash])
        if scanner is None:
            found: list[str] = []
        else:
            try:
                found = scanner(node)
            except GraphError as exc:
                # One node's statement failing to elaborate is that node's defect, not a reason
                # to publish no products for the whole graph: the post-merge job stopped on the
                # first hole on erdos-412 (its statement lacked its parent's ``open`` line,
                # 2026-09-17) and every merge after it would have lost its bot commit. The node
                # gets no tags, the cache keeps no entry, and the log names it; ``failed`` names
                # it too, so the frontier leaves it out (R13).
                log.warning("library tags skipped for %s: %s", node.node_id, exc)
                self.failed.add(node.node_id)
                return []
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
    #: F15-R1, R7, R13: the active stewards, the digestion state with its counts, and whether
    #: the target is a calibration target — derived for every target, curated or not.
    stewards: tuple[steward.Steward, ...] = ()
    digestion: dict[str, Any] = field(default_factory=lambda: dict(NO_DIGESTION))
    calibration: bool = False

    @property
    def dormant(self) -> bool:
        return self.status == intake.DORMANT


#: F15-R7: what a target in any status but ``resolved`` carries — no state, and the counts.
NO_DIGESTION: dict[str, Any] = {
    "state": None,
    "closure": 0,
    "closure_explained": 0,
    "proved": 0,
    "proved_explained": 0,
}
UNDIGESTED = "undigested"
EXPLAINED = "explained"
WRITTEN_UP = "written-up"


def closing_node(tg: TargetGraph) -> str | None:
    """F15-Q11: the node whose proof closed the target — the root, or the ``resolves`` variant
    where the target resolved by variant (D-30); ``None`` while nothing has. A ``partial``
    variant closes nothing and starts no digestion state."""
    if tg.statuses[tg.root] == "proved":
        return tg.root
    for node_id in tg.order:
        n = tg.nodes[node_id]
        if n.relation == "resolves" and tg.statuses[node_id] == "proved":
            return node_id
    return None


def dependency_closure(tg: TargetGraph, node_id: str) -> list[str]:
    """``node_id`` and every node it depends on, transitively, in id order."""
    seen: set[str] = set()
    stack = [node_id]
    while stack:
        current = stack.pop()
        if current in seen or current not in tg.nodes:
            continue
        seen.add(current)
        stack.extend(tg.nodes[current].deps)
    return sorted(seen)


def digestion(tg: TargetGraph, *, status: str, signer: Signer) -> dict[str, Any]:
    """F15-R7 (D-33 v3.17): the digestion state of a resolved target and the counts behind it.

    ``written-up`` when a valid ``paper`` write-up record exists; else ``explained`` when every
    proved node in the closing artifact's dependency closure carries at least one valid signed
    explainer; else ``undigested``. A target in any other status carries ``null``, with the
    proved-node counts still filled in, because the home page's coverage count ("explained: n of
    m proved nodes") sums over every target, resolved or not (F15-R10, Q10).
    """
    proved = [n for n in tg.order if tg.statuses[n] == "proved"]
    explained = {n for n in proved if explainers.valid(tg.nodes[n].path, signer)}
    out: dict[str, Any] = {
        **NO_DIGESTION,
        "proved": len(proved),
        "proved_explained": len(explained),
    }
    if status != "resolved":
        return out
    closing = closing_node(tg)
    closure = dependency_closure(tg, closing) if closing is not None else []
    closure_proved = [n for n in closure if tg.statuses[n] == "proved"]
    closure_explained = [n for n in closure_proved if n in explained]
    out["closure"] = len(closure_proved)
    out["closure_explained"] = len(closure_explained)
    if writeup.has_paper(tg.path, signer):
        out["state"] = WRITTEN_UP
    elif closure_proved and len(closure_explained) == len(closure_proved):
        out["state"] = EXPLAINED
    else:
        out["state"] = UNDIGESTED
    return out


def target_facts(
    tg: TargetGraph, *, signer: Signer | None = None, policy: policymod.Policy | None = None
) -> TargetFacts:
    """(status, claimable, fidelity) and the rest, for the index (R9; Q4, Q5; F11-R3, R4).

    Two eras meet here. A target with no ``target.yaml`` predates F11: its declaration says
    whether it is claimable and at what grade, which is F03-Q4/Q5 and is what the tutorial graph
    still runs on. A curated target derives all three — the grade from its fidelity certificates
    (F11-R3), claimability from status, grade and posting (F11-R4) — and the declaration's own
    ``claimable`` and ``fidelity`` fields are ignored, because a derived value with a second
    writable home is a value that will disagree with itself.

    ``signer`` verifies the F15 records (stewards, explainer signatures, write-ups); the default
    is the platform's ssh-keygen, which is where the products are generated (F15 §7). ``policy``
    is the graph's ``policy.json`` (F15-R3), read from the target's graph root when not given.
    """
    verifier = signer if signer is not None else signed.default_signer()
    rule = policy if policy is not None else policymod.load(tg.path.parents[1])
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
    stewards = tuple(steward.active(tg.path, verifier))
    digested = digestion(tg, status=status, signer=verifier)
    if doc is None:
        return TargetFacts(
            status=status,
            claimable=legacy_claimable,
            fidelity=grade,
            stewards=stewards,
            digestion=digested,
        )
    # F12-R11: an upstream edit that stands on the root as it is freezes proving compute.
    root_hash = tg.nodes[tg.root].statement_hash
    drift = watch.drift_state(tg.path, root_hash)
    claimable, reasons = intake.claimability(
        doc,
        status=status,
        grade=grade,
        drifted=drift.frozen,
        steward_rule=rule.enforced,  # F15-R4: only while the switch is on
        stewards=tuple(s.login for s in stewards),
    )
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
        stewards=stewards,
        digestion=digested,
        calibration=intake.is_calibration(doc),
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


def status_or_ready(statuses: Mapping[str, str], node_id: str) -> str:
    """A node's derived status, defaulting to ``ready`` for an id the map does not carry — the
    reading :func:`graph.derive_causes` already takes."""
    return statuses.get(node_id, "ready")


def workable(status: str, node: NodeFacts, status_of: Callable[[str], str]) -> bool:
    """R13: what a claim could be worked on. A ready or speculative node, or a hole waiting only
    for its witness while ``blocked`` is still its status. A record status is the curator's word
    over the mechanical reason, the reading ``graph.derive_causes`` takes for ``cause`` and the
    api's witness route keys off; and a superseded node is refused on the fact itself (D-8),
    whatever its slot says. Found live 2026-09-17: ``erdos-69--h2``, replaced by a D-8 revision,
    was still ``claimable: true`` because the hole clause asked only about the slot. One predicate
    for membership and for ``claimable``, so the two cannot drift (the 2026-09-14 lesson)."""
    if graphmod.is_superseded(node):
        return False
    if status in graphmod.FRONTIER_STATUSES:
        return True
    return status == "blocked" and graphmod.awaiting_witness(node, status_of)


def in_frontier(status: str, node: NodeFacts, status_of: Callable[[str], str]) -> bool:
    """R5: ready or speculative, every variant whose question is still open, and every hole
    waiting only for its witness.

    A refuted or defective variant is as settled as a proved one (D-12), so it leaves the
    frontier too — the frontier is what is still worth attacking, not what still lacks a proof.

    A hole is ``blocked`` from the moment the post-merge job creates it, because its witness slot
    is a stub; D-29 nevertheless says holes enter the frontier as children with no human
    promotion step, and D-25 publishes ``origin: skeleton-hole`` as a field to filter on. Keying
    membership off status alone hid every hole ever created (found live 2026-09-16, when the
    first hole on an open Erdős target took its whole target off the frontier). The witness is
    work anyone can do — ``POST /proposals/witness`` takes exactly this node — so it belongs
    here, while a node waiting on an unproved dependency does not.
    """
    if graphmod.is_superseded(node):
        return False  # R13: its successor carries the question, variant or not
    if workable(status, node, status_of):
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
        # Q4 (T6): the target's claimability and the node's status. An open variant is listed
        # while it waits on its holes (R5), but a claim on it could not be worked. A hole waiting
        # only for its witness is the exception that premise does not cover: the witness *is* the
        # work, and ``POST /proposals/witness`` accepts it today, so a claim on it is workable
        # (owner's call, 2026-09-16).
        "claimable": claimable
        and workable(status, node, functools.partial(status_or_ready, tg.statuses)),
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


def step9_basis(tg: TargetGraph) -> str:
    """F14-R9: what a proof or partial on the root needs at merge, as the gate decides it from this
    tree (``modes.with_statement_review``): a counting certificate, recorded evidence, or a
    non-author's review. Rendered with the default minimum, since the products are what the gate
    at this pin decides without configuration (F14-R5)."""
    from opn_gate import modes  # noqa: PLC0415 — modes owns the rule; products only reports it

    if modes.root_certificate(tg.path) is not None:
        return "certificate"
    if modes.step9_evidence(tg.path) is not None:
        return "evidence"
    return "review"


def index_doc(
    targets: list[TargetGraph],
    rendered_from: str | None,
    *,
    policy: policymod.Policy | None = None,
    signer: Signer | None = None,
) -> dict[str, Any]:
    out = []
    for tg in targets:
        facts = target_facts(tg, signer=signer, policy=policy)
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
                # F14-R9: the root's catalog evidence (T4); the formalizations arrive with T6.
                "statement_evidence": evidence.summary(tg.path, tg.nodes[tg.root].statement_hash),
                "step9": step9_basis(tg),
                "formalizations": formalizations.summary(tg.path),
                # F15-R9: the active stewards, the digestion state and the calibration flag.
                "stewards": [s.as_dict() for s in facts.stewards],
                "digestion": dict(facts.digestion),
                "calibration": facts.calibration,
            }
        )
    return {
        "schema": INDEX_SCHEMA,
        "rendered_from": rendered_from,
        "policy": (policy if policy is not None else policymod.Policy()).as_dict(),
        "targets": out,
    }


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
            # F08-T10 (D-8 v3.18): the other bot-owned file. A revision puts its dependents'
            # generated contexts out of date and no submission may mend one, so the job that
            # renders the products after every merge regenerates them, in both directions.
            for target_id in target_ids(root):
                nodes_dir = layout.graph_nodes_dir(root, target_id)
                written.extend(p.relative_to(root) for p in postmerge.refresh_contexts(nodes_dir))
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
    signer: Signer | None = None,
) -> Products:
    """Build and validate every product without writing anything (R11; AC5).

    ``signer`` verifies the signed F15 records the index derives from (stewards, explainer
    signatures, write-ups); the default is the platform's ssh-keygen (F15 §7).
    """
    verifier = signer if signer is not None else signed.default_signer()
    policy = policymod.load(graph_root)  # F15-R3: absent means not enforced
    # F03-T8 (R10, D-34): info.json advertises the registry, so the graph must serve every
    # family it lists. Checked first: a cheap refusal before any scan (C7).
    lacking = schemas.unpublished(graph_root)
    if lacking:
        msg = (
            f"schema-unpublished: info.json would advertise {len(lacking)} schema(s) the graph's "
            f"schemas/ does not hold: {', '.join(lacking)}; seed it with opn_gate.schemas.publish"
        )
        raise GraphError(msg)
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
        facts = target_facts(tg, signer=verifier, policy=policy)
        ready_since = graphmod.ready_since_map(previous, tg.statuses, commit_time)
        # R6: only a Mathlib-pinned graph has library tags to scan for and a cache to keep.
        cache = TagCache(tg.path / TAGS_CACHE) if tg.spec["mathlib_sha"] is not None else None
        # Bound per target, not per node: a lambda defined in the node loop would close over the
        # loop's ``tg`` and read the last target's statuses (ruff B023).
        statuses = tg.statuses
        status_of = functools.partial(status_or_ready, statuses)
        for node_id in tg.order:
            node = tg.nodes[node_id]
            products.meta_status[node.path.relative_to(graph_root)] = tg.statuses[node_id]
            if not in_frontier(tg.statuses[node_id], node, status_of):
                continue
            # R6 before R13: the scan is the one place the products elaborate a statement, so a
            # statement the pinned toolchain refuses is learned here, and such a node is not
            # work anyone can take (found live 2026-09-17: a hole the pinned extractor wrote
            # without its ascriptions was published claimable). Loud, never silent (C7): the
            # log names it, and graph.json and META.yaml still carry the derived status.
            tags = cache.tags(node, scanner) if cache is not None else []
            if cache is not None and node_id in cache.failed:
                log.warning(
                    "%s/%s: its statement does not elaborate under the pinned toolchain, so it "
                    "is not on the frontier (F03-R13)",
                    target_id,
                    node_id,
                )
                continue
            entries.append(
                frontier_entry(
                    tg,
                    node,
                    claimable=facts.claimable,
                    dormant=facts.dormant,
                    ready_since=ready_since[node_id],
                    tags=tags,
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
        schemas.validate(
            index_doc(products.targets, rendered_from, policy=policy, signer=verifier),
            INDEX_SCHEMA,
        )
    )
    products.files[Path("info.json")] = schemas.canonical_json(
        schemas.validate(info_doc(graph_root, products.targets, rendered_from), INFO_SCHEMA)
    )
    notices = notices_text(products.targets)
    if notices is not None:
        products.files[Path(intake.NOTICES_FILE)] = notices
    return products


def notices_text(targets: list[TargetGraph]) -> bytes | None:
    """F14-R12: ``THIRD_PARTY_NOTICES.md`` rendered from every target record's licensed sources,
    sorted by target id — rebuildable from the graph (D-35) instead of appended by an import whose
    branch could never merge it (F11-Q26). ``None`` when no statement was copied in, so a graph
    with no imports gains no file."""
    entries: list[str] = []
    for tg in sorted(targets, key=lambda t: t.target_id):
        doc = intake.load_doc(tg.path)
        if doc is not None:
            entries.extend(intake.notices_entries(tg.target_id, doc))
    if not entries:
        return None
    return intake.render_notices(entries).encode("utf-8")
