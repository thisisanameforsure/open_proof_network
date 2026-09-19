"""Graph derivation (F03-T2; R1, R2, R3, R8; Q1, Q2, Q3, Q5).

From a target's node directories, the graph's attestations and the status records, derive every
node's status, the target's root, and the ``ready_since`` timestamps — deterministically, from
committed facts and git alone (Q2). A dependency cycle, a dep that is not a node, or an
ambiguous root is a graph defect: ``GraphError`` names it and the caller writes nothing (R3, C7).
"""

from __future__ import annotations

import logging
import re
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from opn_gate import config, layout, paths, records, schemas
from opn_gate.bounce import TIMESTAMP_FORMAT
from opn_gate.diagnostic import Diagnostic
from opn_gate.records import StatusRecord

DERIVED_STATUSES: tuple[str, ...] = ("ready", "blocked", "proved", "refuted", "defective")
RECORD_STATUSES: tuple[str, ...] = ("speculative", "superseded", "stale", "disputed", "abandoned")
ALL_STATUSES: tuple[str, ...] = (*DERIVED_STATUSES, *RECORD_STATUSES)
FRONTIER_STATUSES: tuple[str, ...] = ("ready", "speculative")
#: A node whose question is settled either way: nothing depending on it can be proved (F07-R8).
RESOLVED_STATUSES: tuple[str, ...] = ("proved", "refuted", "defective")
#: What a merged artifact makes of the node it was submitted against (D-12 #1, #2, #3).
STATUS_FOR_ARTIFACT: dict[str, str] = {
    "proof": "proved",
    "counterexample": "refuted",
    "vacuity": "defective",
}
CAUSE_DEP_REFUTED = "dep-refuted"  # R8: a dependent of a refuted node, for curator attention
CAUSE_WITNESS_MISSING = "witness-missing"  # R6: a compiler-derived child with a stub witness
#: Origins whose nodes are created by the post-merge job with a witness slot, not a witness.
HOLE_ORIGINS: tuple[str, ...] = ("compiler-derived", "skeleton-hole")
TRUST_KERNEL = "kernel"
_RELATION_RE = re.compile(r"^\s*--\s*relation:\s*(?P<label>resolves|partial|related)\s*$", re.M)
_META_STATUS_RE = re.compile(r"^status:[ \t]*[^\n]*$", re.M)


log = logging.getLogger(__name__)


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
    artifact: str | None = None  # which of D-12's artifacts Proof.lean is (F07-R8)
    witness_stub: bool = False  # R6: the witness slot is unfilled, so the node cannot be ready
    supersedes: str | None = None  # F08-R9, D-8: the node this one revises
    #: F08-T10 (D-8 v3.18): ``deps`` is what the node depends on *now* — each recorded dep read
    #: through its revision chain — and this is the record itself, ``META.yaml``'s list, which
    #: nothing rewrites. Every derivation reads ``deps``; the record stays for the reader.
    declared_deps: tuple[str, ...] = ()
    #: A ``stale`` override the gate's own evidence has lifted (see ``stale_lifted``).
    stale_lifted: bool = False


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
    node_id: str,
    statement_hash: str,
    attestations: list[tuple[str, dict[str, Any]]],
    *,
    proof_hash: str | None = None,
    alternate_hashes: frozenset[str] = frozenset(),
) -> Proof | None:
    """R1, F07-R15: the node's proof — a merged passing attestation for its current statement.

    The one whose ``artifact_hash`` is the node's ``Proof.lean`` wins, whatever its number: in a
    race the pull request opened first can land second, as an alternate (D-25 v3.13), and its
    attestation sorts first by name. With no such match (a hand-made attestation), the first one
    that is not an alternate's is taken, which is what this function answered before alternates.
    """
    passing = [
        (name, doc)
        for name, doc in attestations
        if doc.get("node_id") == node_id
        and doc.get("statement_hash") == statement_hash
        and doc.get("verdict") == "pass"
        and doc.get("merge_commit")
    ]
    matching = [(n, d) for n, d in passing if proof_hash and d.get("artifact_hash") == proof_hash]
    others = [(n, d) for n, d in passing if d.get("artifact_hash") not in alternate_hashes]
    for name, doc in (*matching, *others):
        return Proof(
            merge_commit=str(doc["merge_commit"]),
            trust_base=str(doc.get("trust_base") or TRUST_KERNEL),
            attestation=name,
        )
    return None


def recorded_hashes(node_dir: Path) -> tuple[str | None, frozenset[str]]:
    """The content hash of the node's ``Proof.lean`` (``None`` without one) and of each alternate
    under ``attempts/`` (D-25 v3.13): what ``proof_for`` tells the node's proof from them by."""
    proof = node_dir / "Proof.lean"
    proof_hash = schemas.content_hash(proof.read_bytes()) if proof.is_file() else None
    attempts = node_dir / "attempts"
    alternates = frozenset(
        schemas.content_hash(p.read_bytes())
        for p in (attempts.glob(f"*{paths.ALTERNATE_SUFFIX}") if attempts.is_dir() else ())
        if p.is_file()
    )
    return proof_hash, alternates


def artifact_of(node_dir: Path, statement_decl: str) -> str | None:
    """Which of D-12's artifacts the node's ``Proof.lean`` is, from the name it declares.

    The same rule the gate applies when it checks the artifact (F07-R4, Q11): a proof keeps the
    statement's name, a counterexample adds ``_refuted``, a vacuity certificate ``_vacuous``. So
    the status a merged artifact produces is read off the tree, and no attestation field or
    submission block has to be trusted for it. ``None`` when the node has no proof file, or when
    it declares something the gate would not have accepted.
    """
    from opn_gate.steps import artifact  # noqa: PLC0415 — avoids a cycle through steps.base

    proof = node_dir / "Proof.lean"
    if not proof.is_file():
        return None
    declared = layout.parse_declaration(proof.read_text(encoding="utf-8"), "Proof.lean")
    if isinstance(declared, Diagnostic):
        return None
    return artifact.kind_of(statement_decl, declared)


def witness_is_stub(node_dir: Path) -> bool:
    """R6: a compiler-derived child is created with a witness slot, not a witness. Until someone
    fills it the node cannot pass step 7, so it is blocked and the reason is mechanical."""
    witness = node_dir / "Witness.lean"
    if not witness.is_file():
        return True
    # As a token in code, not as a word: the slot's own header comment says `sorry` (F08-Q18).
    return layout.mentions_sorry(witness.read_text(encoding="utf-8"))


def relation_label(relation_text: str | None, origin: str) -> str | None:
    """D-30 label from the text of ``Relation.lean``: the header names it; no header, or no
    file, means ``related``; a node that is not a variant has no label."""
    if origin != "variant":
        return None
    if relation_text is not None:
        m = _RELATION_RE.search(relation_text)
        if m:
            return m.group("label")
    return "related"


def relation_of(node_dir: Path, origin: str) -> str | None:
    """``relation_label`` over the node directory's ``Relation.lean``."""
    relation = node_dir / "Relation.lean"
    text = relation.read_text(encoding="utf-8") if relation.is_file() else None
    return relation_label(text, origin)


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
        declared = tuple(str(d) for d in raw_deps) if isinstance(raw_deps, list) else ()
        origin = str(loaded.meta.get("origin", "authored"))
        statement_hash = loaded.statement.statement_hash
        hashes = recorded_hashes(node_dir)
        override = records.load_node_status(node_dir)
        facts[loaded.node_id] = NodeFacts(
            node_id=loaded.node_id,
            target_id=target_id,
            path=node_dir,
            statement_hash=statement_hash,
            deps=effective_deps(nodes_dir, declared),
            declared_deps=declared,
            stale_lifted=(
                override is not None
                and override.status == "stale"
                and stale_lifted(
                    graph_root, override.path, loaded.node_id, statement_hash, attestations
                )
            ),
            origin=origin,
            tutorial=bool(loaded.meta.get("tutorial", False)),
            relation=relation_of(node_dir, origin),
            proof=proof_for(
                loaded.node_id,
                statement_hash,
                attestations,
                proof_hash=hashes[0],
                alternate_hashes=hashes[1],
            ),
            override=override,
            artifact=artifact_of(node_dir, loaded.statement.decl_name),
            witness_stub=witness_is_stub(node_dir),
            supersedes=_optional_str(loaded.meta.get("supersedes")),
        )
    return facts


# --- derivation --------------------------------------------------------------------------------


def _optional_str(value: object) -> str | None:
    return str(value) if isinstance(value, str) and value else None


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
    """R1, F07-R8: resolved > blocked > ready from the facts; a status record overrides all three.

    A merged artifact resolves its node, and *which* resolution it is comes from what the
    artifact declares: a proof proves it, a counterexample refutes it, a vacuity certificate
    marks it defective (D-12). All three are settled, and none of them lets a dependent proceed,
    because only a proof discharges the obligation a dependent inherited.
    """
    check_dag(nodes)
    statuses: dict[str, str] = {}

    def status_of(node_id: str) -> str:
        if node_id in statuses:
            return statuses[node_id]
        node = nodes[node_id]
        if node.override is not None and not stale_is_void(node):
            result = node.override.status
        elif node.proof is not None and node.artifact in STATUS_FOR_ARTIFACT:
            # F03-Q7 (2026-09-12): settled only by an artifact that is *in the tree* — a
            # Proof.lean the gate accepted, whose declared name says which artifact it is — with
            # a merged passing attestation for this statement. The attestation alone is not
            # enough: a merged partial earns one against its parent's statement hash too, and it
            # leaves no Proof.lean behind, so a parent with an attestation and no artifact is
            # blocked on its holes like any other node, not proved (D-12 #5, D-29, D-35).
            result = STATUS_FOR_ARTIFACT[node.artifact]
        else:
            blocked, _ = blocked_because(node, status_of)
            result = "blocked" if blocked else "ready"
        statuses[node_id] = result
        return result

    for node_id in sorted(nodes):
        status_of(node_id)
    return dict(sorted(statuses.items()))


def settled(node: NodeFacts) -> bool:
    """The node has a merged artifact in the tree with its attestation (F03-Q7)."""
    return node.proof is not None and node.artifact in STATUS_FOR_ARTIFACT


def stale_is_void(node: NodeFacts) -> bool:
    """F08-T10 (D-8, D-18 v3.18): when a ``stale`` record does not decide the status.

    ``stale`` says a merged proof must be re-derived against a revised dependency. A node with
    no merged artifact has nothing to re-derive, so the mark says nothing of it (and the seven
    live parents that carry one were frozen by it: a record outranks everything, and
    ``node-status/v1`` has no value that clears one). On a settled node it lifts when the gate's
    own evidence says the re-run happened (``stale_lifted``). Evidence lifts it; no record and
    no date does, because a record is an assertion by whoever holds a key."""
    if node.override is None or node.override.status != "stale":
        return False
    return not settled(node) or node.stale_lifted


def _git(graph_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(graph_root), *args],
        capture_output=True,
        text=True,
        check=False,
        env=config.child_environment(drop=config.GIT_REPO_VARIABLES),
    )


def stale_lifted(
    graph_root: Path,
    record: Path,
    node_id: str,
    statement_hash: str,
    attestations: list[tuple[str, dict[str, Any]]],
) -> bool:
    """Whether a passing attestation for this node's statement comes from a run that included
    the commit that marked it stale: its ``graph_commit`` descends from the commit that added
    ``record``. Commit ancestry, never dates — a status record's date is whatever its author
    typed, and an attestation carries none. With no history to ask (not a git tree, the record
    uncommitted, a commit this clone has never seen) the answer is no: the mark stays."""
    try:
        rel = record.relative_to(graph_root).as_posix()
    except ValueError:
        return False
    added = _git(graph_root, "log", "--diff-filter=A", "--format=%H", "-1", "--", rel)
    marked = added.stdout.strip() if added.returncode == 0 else ""
    if not marked:
        return False
    for _name, doc in attestations:
        if (
            doc.get("node_id") == node_id
            and doc.get("statement_hash") == statement_hash
            and doc.get("verdict") == "pass"
            and doc.get("graph_commit")
        ):
            ran_at = str(doc["graph_commit"])
            if _git(graph_root, "merge-base", "--is-ancestor", marked, ran_at).returncode == 0:
                return True
    return False


def blocked_because(node: NodeFacts, status_of: Callable[[str], str]) -> tuple[bool, str | None]:
    """Whether ``node`` is blocked, and the mechanical reason where there is one (R6, R8).

    Two things block a node that has no artifact of its own: a dependency that is not proved, and
    a witness slot nobody has filled. Only some of those have a *nameable* cause — a dep that is
    merely unproved is the ordinary case and says nothing worth publishing, while a dep that has
    been refuted is a dead end a curator has to look at (D-12, D-14).
    """
    unproved = [dep for dep in node.deps if status_of(dep) != "proved"]
    if unproved:
        refuted = any(status_of(dep) == "refuted" for dep in unproved)
        return True, CAUSE_DEP_REFUTED if refuted else None
    if node.witness_stub and node.origin in HOLE_ORIGINS:
        return True, CAUSE_WITNESS_MISSING
    return False, None


def awaiting_witness(node: NodeFacts, status_of: Callable[[str], str]) -> bool:
    """D-29, R6: a hole blocked *only* by its unfilled witness slot — the witness is the work.

    The decisions document says holes enter the frontier as children with no human promotion
    step, and D-25 publishes ``origin: skeleton-hole`` as a frontier field to filter on. Such a
    node is ``blocked``, so membership cannot key off status alone; it keys off the reason. A
    node waiting on a dependency nobody has proved is *not* this: nothing about it can be worked
    yet, so it stays off the frontier. That is the distinction :func:`blocked_because` already
    draws, and this reuses it rather than deriving it a second time (found live 2026-09-16, when
    the first hole on an open Erdős target took its target off the frontier entirely).
    """
    blocked, cause = blocked_because(node, status_of)
    return blocked and cause == CAUSE_WITNESS_MISSING


def derive_causes(nodes: dict[str, NodeFacts], statuses: dict[str, str]) -> dict[str, str | None]:
    """R8, R6: the machine-readable reason a blocked node is blocked, or ``None``.

    ``dep-refuted`` is the one the curator has to see: a node under a refuted one can never be
    proved as it stands, and nothing else in the products would say so.
    """
    causes: dict[str, str | None] = {}
    for node_id in sorted(nodes):
        _, cause = blocked_because(nodes[node_id], lambda n: statuses.get(n, "ready"))
        causes[node_id] = cause if statuses[node_id] == "blocked" else None
    return causes


def find_root(nodes: dict[str, NodeFacts], declaration: StatusRecord | None) -> str:
    """Q5: the declared root, else the unique node nothing depends on.

    A revision (F08-R9, D-8) leaves two sinks until the dependents are re-derived: the
    superseded node and the node that supersedes it. Neither is a new root — a superseded node
    is never the root, and a revision of an interior node is a sink only because its dependents
    still name the old id — so both are set aside before the sink is required to be unique. A
    revision of the root itself is then the one sink left. A declared root is followed the same
    way, to the node it has become (F11-Q29).
    """
    if declaration is not None and declaration.doc.get("root"):
        root = str(declaration.doc["root"])
        if root not in nodes:
            msg = f"declared root {root!r} is not a node"
            raise GraphError(msg)
        return _current_node(nodes, root)
    depended_on = {dep for n in nodes.values() for dep in n.deps}
    sinks = sorted(n for n in nodes if n not in depended_on)
    superseded = {n for n in sinks if is_superseded(nodes[n])}
    if len(sinks) > 1 and superseded:
        sinks = [n for n in sinks if n not in superseded]
    # A revision is set aside only when the node it revises is depended on: that revision is a
    # sink only because its dependents still name the old id. A revision of the root is the root's
    # successor and stays a candidate, so a variant beside it is ambiguity, never the root (C7).
    interior_revisions = {n for n in sinks if nodes[n].supersedes in depended_on}
    if len(sinks) > 1 and interior_revisions:
        sinks = [n for n in sinks if n not in interior_revisions]
    if len(sinks) != 1:
        msg = (
            f"root is ambiguous: {len(sinks)} nodes have no dependents ({', '.join(sinks)}); "
            f"declare one as `root:` in a targets/<id>/status/ record "
            f"({records.TARGET_STATUS_SCHEMAS[-1]})"
        )
        raise GraphError(msg)
    return sinks[0]


def _supersedes_of(node_dir: Path) -> str | None:
    try:
        meta = schemas.load_yaml(node_dir / "META.yaml")
    except (OSError, schemas.SchemaError):
        return None
    named = meta.get("supersedes") if isinstance(meta, dict) else None
    return str(named) if named else None


def current_id(nodes_dir: Path, node_id: str) -> str:
    """F08-T10 (D-8 v3.18): the node ``node_id`` has become — the end of its revision chain, read
    from the tree. A ``superseded`` status record's ``reference`` names the successor (``revise``
    and ``consolidate`` both write it), and the chain is followed while each step is sound:
    the successor is a node of this target, the chain does not loop, and a successor that says
    what it supersedes (a D-8 revision's ``META.yaml``) says *this* node. A consolidation's
    survivor says nothing and is followed as before. An unsound step is not followed and is
    logged by name; the walk stops at the last node soundly reached, because one bad record
    must never decide whether a target has products (2026-09-17)."""
    chain = [node_id]
    while True:
        here = nodes_dir / chain[-1]
        record = records.load_node_status(here) if here.is_dir() else None
        if record is None or record.status != "superseded":
            return chain[-1]
        successor = str(record.doc.get("reference") or "")
        if not successor:
            return chain[-1]
        if not (nodes_dir / successor).is_dir():
            problem = "which is not a node of this target"
        elif successor in chain:
            problem = "which loops"
        else:
            named = _supersedes_of(nodes_dir / successor)
            problem = (
                f"whose own record says it supersedes {named}"
                if named is not None and named != chain[-1]
                else ""
            )
        if problem:
            log.warning(
                "%s: its superseded record names %s, %s; the revision is not followed",
                chain[-1],
                successor,
                problem,
            )
            return chain[-1]
        chain.append(successor)


def effective_deps(nodes_dir: Path, declared: object) -> tuple[str, ...]:
    """The deps a node has *now*: each recorded dep read through its revision chain, in the
    record's order, a dep two records reach once kept once. ``declared`` is ``META.yaml``'s
    ``deps`` as loaded, so anything but a list is no deps."""
    out: list[str] = []
    for dep in declared if isinstance(declared, (list, tuple)) else ():
        current = current_id(nodes_dir, str(dep))
        if current not in out:
            out.append(current)
    return tuple(out)


def is_superseded(node: NodeFacts) -> bool:
    """D-8: a status record has replaced this node with the one its ``reference`` names. Never
    the root (``find_root``), never work (``products.in_frontier``, F03-R13)."""
    return node.override is not None and node.override.status == "superseded"


def _current_node(nodes: dict[str, NodeFacts], declared: str) -> str:
    """F11-Q29: the node a declared root has become.

    A declaration names the root as it was when written. A revision (D-8) or a consolidation
    (D-29) supersedes that node with a status record whose ``reference`` names the successor,
    and rewrites no target record — so the declaration is followed to the end of that chain.
    A successor that is not a node, or a chain that loops, is refused by name: publishing a
    superseded node as the root would be a silent wrong answer (C7).
    """
    chain = [declared]
    override = nodes[declared].override
    while override is not None and override.status == "superseded":
        successor = override.doc.get("reference")
        if not successor or str(successor) not in nodes:
            msg = (
                f"declared root {declared!r} is superseded and its successor {successor!r} is "
                "not a node; declare the root again in targets/<id>/status/"
            )
            raise GraphError(msg)
        if str(successor) in chain:
            path = " -> ".join([*chain, str(successor)])
            msg = f"declared root {declared!r} is superseded in a loop: {path}"
            raise GraphError(msg)
        chain.append(str(successor))
        override = nodes[chain[-1]].override
    return chain[-1]


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
