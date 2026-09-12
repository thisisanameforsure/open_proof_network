"""The curator's four commands (F08-R9 to R12; D-8, D-13, D-18, D-29, D-33).

D-29 leaves the curator one thin, mechanical authority over a target's statements: versioning a
defective one (D-8), consolidating syntactic duplicates, and declaring a target dormant (D-33).
Each is a command that writes files a curator pull request carries — a node directory, status
records — and nothing here merges anything or edits a statement in place. The records are what
F03 derives statuses from; the commands only put them there, with the cause on the record.

``missing-library`` is the odd one out: it writes nothing at all. D-13 has the aggregate
surfaced to the curator, who proposes the prerequisite node like any contributor (F08-Q3).
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from opn_gate import defs, layout, records, scaffold, schemas
from opn_gate import graph as graphmod
from opn_gate.paths import VERSION_RE
from opn_gate.steps.base import RunContext
from opn_gate.steps.toolchain_step import ToolchainStep
from opn_gate.toolchain import ResolvedToolchain

log = logging.getLogger(__name__)

NODE_STATUS_SCHEMA = "node-status/v1"
#: F11-R12: new declarations are written at v2, whose fidelity enum carries D-9
#: v3.12's renamed rung. v1 records already in a graph stay valid (D-34).
TARGET_STATUS_SCHEMA = "target-status/v2"
REVISION_SCHEMA = "revision-request/v1"
POSTMORTEM_SCHEMA = "postmortem/v1"
MISSING_LIBRARY = "missing-library"
#: D-33's pilot defaults, tunable per graph: every ready node carries at least K attempts, or no
#: progress artifact has landed in N days.
DEFAULT_K = 3
DEFAULT_N_DAYS = 90
DEFAULT_THRESHOLD = 3  # D-13: the missing-library aggregate surfaced at or above this
NODE_STATUSES: tuple[str, ...] = ("abandoned",)  # what `status` may say of a node (D-14)
TARGET_STATUSES: tuple[str, ...] = ("dormant", "active")  # ... and of a target (D-33)
_WS = re.compile(r"\s+")
PROBE_NAME = "OpnConsolidate.probe"
_THEOREM_NAME_RE = re.compile(r"^(?P<kw>theorem|lemma)\s+[^\s:({\[]+", re.M)


class CuratorError(ValueError):
    """The command refuses; nothing has been written."""


# --- versions (D-8, F08-Q16) ----------------------------------------------------------------


def base_id(node_id: str) -> str:
    m = VERSION_RE.match(node_id)
    return m.group("base") if m else node_id


def version_of(node_id: str) -> int:
    m = VERSION_RE.match(node_id)
    return int(m.group("n")) if m else 1


def next_version_id(nodes_dir: Path, node_id: str) -> str:
    """``<base>-v<n>`` for the next free ``n``: the unversioned node is v1 (D-19)."""
    base = base_id(node_id)
    taken = [
        version_of(p.name) for p in nodes_dir.iterdir() if p.is_dir() and base_id(p.name) == base
    ]
    return f"{base}-v{max(taken, default=1) + 1}"


# --- records ---------------------------------------------------------------------------------


def stamp(date: str) -> str:
    """``2026-09-10T12:13:14Z`` -> ``20260910T121314Z``: sorts lexically, a legal file name."""
    return date.replace("-", "").replace(":", "")


def node_status_doc(
    status: str, cause: str, *, author: str, date: str, reference: str | None = None
) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": NODE_STATUS_SCHEMA,
        "status": status,
        "cause": cause,
        "author": author,
        "date": scaffold.day(date),
    }
    if reference is not None:
        doc["reference"] = reference
    return schemas.validate(doc, NODE_STATUS_SCHEMA)


def record_path(directory: Path, *, author: str, date: str) -> Path:
    """Where a status record by ``author`` at ``date`` goes: ``<dir>/status/<stamp>-<author>.yaml``.
    Append-only, so a name already taken is a refusal rather than an overwrite (C7)."""
    path = directory / "status" / f"{stamp(date)}-{author}.yaml"
    if path.exists():
        msg = f"{path} already exists; status records are append-only"
        raise CuratorError(msg)
    return path


def write_record(directory: Path, doc: dict[str, Any], *, author: str, date: str) -> Path:
    """Write ``doc`` at its ``record_path``; the refusal comes before the directory is made."""
    return _write_yaml(record_path(directory, author=author, date=date), doc)


def _write_yaml(path: Path, doc: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def dependents_of(nodes_dir: Path, node_id: str) -> list[str]:
    """Every node of the target whose META declares ``node_id`` as a dep (D-18's stale set)."""
    out: list[str] = []
    for node_dir in sorted(p for p in nodes_dir.iterdir() if p.is_dir()):
        meta_path = node_dir / "META.yaml"
        if not meta_path.is_file():
            continue
        meta = schemas.load_yaml(meta_path)
        deps = meta.get("deps")
        if isinstance(deps, list) and node_id in deps:
            out.append(node_dir.name)
    return out


def load_node(nodes_dir: Path, target_id: str, node_id: str) -> layout.Node:
    node_dir = nodes_dir / node_id
    if not node_dir.is_dir():
        msg = f"{node_id} is not a node of {target_id}"
        raise CuratorError(msg)
    loaded = layout.load_node(node_dir, target_id)
    if isinstance(loaded, list):
        msg = f"{node_id} is not a valid node: {loaded[0].message}"
        raise CuratorError(msg)
    return loaded


# --- revise (R9; D-8, D-18) -------------------------------------------------------------------


@dataclass(frozen=True)
class Revision:
    node_id: str
    new_id: str
    request: str  # the revision request's path, relative to the graph root
    dependents: tuple[str, ...]
    written: tuple[str, ...] = field(default_factory=tuple)  # every path this created

    def as_dict(self) -> dict[str, Any]:
        return {
            "node": self.node_id,
            "revision": self.new_id,
            "request": self.request,
            "dependents": list(self.dependents),
            "written": list(self.written),
        }


def revise(  # noqa: PLR0913 — one argument per fact of the revision
    graph_root: Path,
    target_id: str,
    node_id: str,
    statement: str,
    request: Path,
    *,
    author: str,
    date: str,
) -> Revision:
    """R9: scaffold ``<node>-v<n>`` from the new statement, carrying the old witness, deps and
    relation for the curator to adjust; mark the old node superseded and each dependent stale.

    The old node is never touched beyond its status record (D-3, D-8): its history and its
    credit stay where they are (D-19), and the products derive the rest. Every record is built
    and its path checked free before the directory is scaffolded, so a refusal at any of them
    leaves nothing on disk (C7; F08-Q18).
    """
    nodes_dir = layout.graph_nodes_dir(graph_root, target_id)
    old = load_node(nodes_dir, target_id, node_id)
    request_doc = schemas.load_yaml(request, REVISION_SCHEMA)
    if str(request_doc["node"]) != node_id:
        msg = f"{request} is a revision request for {request_doc['node']!r}, not {node_id!r}"
        raise CuratorError(msg)
    request_rel = _relative(graph_root, request)
    new_id = next_version_id(nodes_dir, node_id)
    defect = request_doc["defect_class"]
    records: list[tuple[Path, dict[str, Any]]] = [
        (
            record_path(old.path, author=author, date=date),
            node_status_doc(
                "superseded",
                f"superseded by {new_id} on revision request {request_rel} ({defect}; D-8)",
                author=author,
                date=date,
                reference=new_id,
            ),
        )
    ]
    dependents = tuple(dependents_of(nodes_dir, node_id))
    records.extend(
        (
            record_path(nodes_dir / dependent, author=author, date=date),
            node_status_doc(
                "stale",
                f"depends on {node_id}, superseded by {new_id} on revision request "
                f"{request_rel}; to be re-derived against the revision (D-18)",
                author=author,
                date=date,
                reference=node_id,
            ),
        )
        for dependent in dependents
    )
    origin = str(old.meta.get("origin", "authored"))
    raw_deps = old.meta.get("deps")
    deps = tuple(str(d) for d in raw_deps) if isinstance(raw_deps, list) else ()
    relation_path = old.path / scaffold.RELATION_FILE
    relation = graphmod.relation_of(old.path, origin) if origin == "variant" else None
    proposal = scaffold.Proposal(
        node_id=new_id,
        target_id=target_id,
        statement=statement,
        witness=(old.path / "Witness.lean").read_text(encoding="utf-8"),
        author=author,
        deps=deps,
        origin=origin,  # type: ignore[arg-type]
        relation=relation,
        relation_proof=relation_path.read_text(encoding="utf-8")
        if relation_path.is_file()
        else None,
        date=date,
        extra_meta={"supersedes": node_id},
    )
    scaffold.validate(proposal)  # every refusal the scaffold has, before a byte is written
    written: list[str] = []
    new_dir = scaffold.write(nodes_dir, proposal)
    written.extend(_relative(graph_root, p) for p in sorted(new_dir.rglob("*")) if p.is_file())
    written.extend(_relative(graph_root, _write_yaml(path, doc)) for path, doc in records)
    log.info("revised %s as %s; %d dependents stale", node_id, new_id, len(dependents))
    return Revision(node_id, new_id, request_rel, dependents, tuple(written))


def _relative(graph_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(graph_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


# --- consolidate (R10; D-29) --------------------------------------------------------------------

Defeq = Callable[[layout.Node, layout.Node], bool]


def consolidate(  # noqa: PLR0913 — the two nodes and the record's facts
    graph_root: Path,
    target_id: str,
    keep: str,
    drop: str,
    *,
    author: str,
    date: str,
    defeq: Defeq | None = None,
) -> Path:
    """R10: mark ``drop`` superseded by ``keep`` — only when the two statements are the same
    statement, byte for byte or definitionally. Anything less is not a duplicate, and D-29's
    consolidation is for syntactic duplicates, never for judgment."""
    if keep == drop:
        msg = "consolidate needs two different nodes"
        raise CuratorError(msg)
    nodes_dir = layout.graph_nodes_dir(graph_root, target_id)
    kept = load_node(nodes_dir, target_id, keep)
    dropped = load_node(nodes_dir, target_id, drop)
    if kept.statement.statement_hash == dropped.statement.statement_hash:
        how = "identical statement"
    elif defeq is not None and defeq(kept, dropped):
        how = "definitionally equal statements"
    else:
        detail = (
            "no toolchain was given to check definitional equality"
            if defeq is None
            else "the statements do not elaborate to definitionally equal types"
        )
        msg = (
            f"{keep} and {drop} are not the same statement: hashes "
            f"{kept.statement.statement_hash[:12]}… and {dropped.statement.statement_hash[:12]}… "
            f"differ and {detail} (D-29: consolidation is for duplicates)"
        )
        raise CuratorError(msg)
    record = node_status_doc(
        "superseded",
        f"consolidated into {keep}: {how} (D-29)",
        author=author,
        date=date,
        reference=keep,
    )
    return write_record(dropped.path, record, author=author, date=date)


def statements_defeq(ctx: RunContext, kept: layout.Node, dropped: layout.Node) -> bool:
    """Whether the two statements elaborate to definitionally equal types, asked of Lean the
    only way that needs no new metaprogram: ``dropped``'s statement with its ``sorry`` replaced
    by ``kept``'s theorem. It elaborates exactly when the elaborator's ``isDefEq`` unifies the
    two types. Runs wherever the caller's toolchain runs — the sandbox on the gate (C9)."""
    resolved = ToolchainStep().run(ctx)
    if not resolved.ok:
        return False
    tc: ResolvedToolchain = ctx.data["toolchain"]
    src = ctx.workdir / "src"
    ctx.build_dir.mkdir(parents=True, exist_ok=True)
    # F11-R2, F01-Q2: the target's definitions first; either Context may import them.
    target_dir = layout.gate_spec_path(ctx.graph_root, ctx.claim.target_id).parent
    if defs.compile_all(ctx.toolchain, tc, target_dir, ctx.workdir, timeout_s=ctx.wallclock_s):
        return False
    for node in (kept, dropped):
        dest = src / "Nodes" / node.node_id
        dest.mkdir(parents=True, exist_ok=True)
        for name in ("Statement.lean", "Context.lean"):
            shutil.copy(node.path / name, dest / name)
        context = layout.node_module(node.node_id, "Context")
        if not _elaborate(ctx, tc, dest / "Context.lean", context, src):
            return False
    keep_module = layout.node_module(kept.node_id, "Statement")
    if not _elaborate(ctx, tc, src / "Nodes" / kept.node_id / "Statement.lean", keep_module, src):
        return False
    probe = src / "Nodes" / dropped.node_id / "Consolidate.lean"
    # Duplicates usually share a theorem name, and the probe imports the kept one — so the
    # probe's own declaration is renamed, or it would redeclare what it imports.
    prefix = _THEOREM_NAME_RE.sub(rf"\g<kw> {PROBE_NAME}", dropped.statement.prefix, count=1)
    text = (
        f"import {keep_module}\n"
        + prefix
        + f" {kept.statement.decl_name}"
        + dropped.statement.suffix
    )
    probe.write_text(text, encoding="utf-8")
    return _elaborate(ctx, tc, probe, layout.node_module(dropped.node_id, "Consolidate"), src)


def _elaborate(
    ctx: RunContext, tc: ResolvedToolchain, source: Path, module: str, root: Path
) -> bool:
    try:
        return ctx.toolchain.elaborate(
            tc, source, module, ctx.build_dir, root=root, timeout_s=ctx.wallclock_s
        ).ok
    except subprocess.TimeoutExpired:
        return False


# --- status (R11; D-14, D-33) ---------------------------------------------------------------


@dataclass(frozen=True)
class Series:
    """D-25's starvation series, as observed at declaration time."""

    ready: int
    attempts: dict[str, int]  # ready node -> attempt count
    k: int
    n_days: int
    last_merge: str | None

    @property
    def zero_attempts(self) -> int:
        return sum(1 for c in self.attempts.values() if c == 0)

    @property
    def fraction_zero(self) -> float:
        return self.zero_attempts / self.ready if self.ready else 0.0

    @property
    def min_attempts(self) -> int:
        return min(self.attempts.values(), default=0)

    def render(self) -> str:
        counts = ", ".join(f"{n}={c}" for n, c in sorted(self.attempts.items())) or "none"
        return (
            f"D-25 series at declaration: ready nodes {self.ready}; attempts per ready node "
            f"{counts}; zero-attempt fraction {self.fraction_zero:.2f}; K={self.k}, "
            f"N={self.n_days} days; last progress artifact merged "
            f"{self.last_merge or 'never'}"
        )


def starvation_series(
    graph_root: Path, target_id: str, *, k: int, n_days: int, last_merge: datetime | None
) -> Series:
    tg = graphmod.load_target(graph_root, target_id)
    attempts = {
        node_id: records.load_attempts(tg.nodes[node_id].path).count
        for node_id, status in tg.statuses.items()
        if status == "ready"
    }
    return Series(
        ready=len(attempts),
        attempts=attempts,
        k=k,
        n_days=n_days,
        last_merge=None if last_merge is None else last_merge.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def declare_status(  # noqa: PLR0913 — the declaration's facts, each named
    graph_root: Path,
    target_id: str,
    ref: str,
    status: str,
    cause: str,
    *,
    author: str,
    date: str,
    now: datetime,
    last_merge: datetime | None = None,
    k: int = DEFAULT_K,
    n_days: int = DEFAULT_N_DAYS,
) -> Path:
    """R11: an abandonment record on a node (D-14), or a dormancy / active declaration on the
    target (D-33). Dormancy is evidence-gated: the record names the D-25 series and the K and N
    in force, and is refused when the target has had a progress artifact within N days while a
    ready node still has fewer than K attempts (D-33 condition a)."""
    if not cause.strip():
        msg = "a status record publishes its reasoning: --cause is required (D-33 b)"
        raise CuratorError(msg)
    nodes_dir = layout.graph_nodes_dir(graph_root, target_id)
    if ref != target_id:
        if status not in NODE_STATUSES:
            msg = f"a node may be marked {', '.join(NODE_STATUSES)}; {status!r} is a target status"
            raise CuratorError(msg)
        node = load_node(nodes_dir, target_id, ref)
        record = node_status_doc(status, cause, author=author, date=date)
        return write_record(node.path, record, author=author, date=date)
    if status not in TARGET_STATUSES:
        msg = f"a target may be declared {', '.join(TARGET_STATUSES)}; {status!r} is a node status"
        raise CuratorError(msg)
    full_cause = cause
    if status == "dormant":
        series = starvation_series(graph_root, target_id, k=k, n_days=n_days, last_merge=last_merge)
        attempted = series.ready > 0 and series.min_attempts >= k
        quiet = last_merge is None or now - last_merge > timedelta(days=n_days)
        if not (attempted or quiet):
            since = (now - last_merge).days if last_merge is not None else None
            msg = (
                f"D-33 (a) does not hold: a progress artifact merged {since} days ago (N={n_days}) "
                f"and a ready node has {series.min_attempts} attempts (K={k}); "
                f"{series.render()}"
            )
            raise CuratorError(msg)
        full_cause = f"{cause}\n{series.render()}"
    doc: dict[str, Any] = {
        "schema": TARGET_STATUS_SCHEMA,
        "status": status,
        "cause": full_cause,
        "author": author,
        "date": scaffold.day(date),
    }
    schemas.validate(doc, TARGET_STATUS_SCHEMA)
    return write_record(graph_root / "targets" / target_id, doc, author=author, date=date)


# --- missing-library (R12; D-13) ------------------------------------------------------------------


def normalise(lemma: str) -> str:
    return _WS.sub(" ", lemma).strip().casefold()


@dataclass(frozen=True)
class MissingLemma:
    key: str
    count: int
    examples: tuple[str, ...]
    nodes: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "lemma": self.key,
            "count": self.count,
            "as_written": list(self.examples),
            "nodes": list(self.nodes),
        }


def missing_library_report(
    graph_root: Path, target_id: str, *, threshold: int = DEFAULT_THRESHOLD
) -> list[MissingLemma]:
    """R12, D-13: ``missing-library`` postmortems aggregated by their normalised lemma strings;
    those named at least ``threshold`` times, for the curator. Creates nothing (F08-Q3)."""
    nodes_dir = layout.graph_nodes_dir(graph_root, target_id)
    counts: dict[str, int] = defaultdict(int)
    examples: dict[str, list[str]] = defaultdict(list)
    where: dict[str, list[str]] = defaultdict(list)
    for node_dir in sorted(p for p in nodes_dir.iterdir() if p.is_dir()):
        attempts = node_dir / "attempts"
        if not attempts.is_dir():
            continue
        for path in sorted(p for p in attempts.iterdir() if p.suffix in records.ATTEMPT_SUFFIXES):
            try:
                doc = schemas.load_yaml(path, POSTMORTEM_SCHEMA)
            except schemas.SchemaError:
                continue  # F03-R7 already counts it as invalid; it names no lemma
            if doc.get("failure_class") != MISSING_LIBRARY:
                continue
            artifacts = doc.get("artifacts") or {}
            lemmas = artifacts.get("missing_lemmas") if isinstance(artifacts, dict) else None
            for lemma in lemmas or []:
                key = normalise(str(lemma))
                if not key:
                    continue
                counts[key] += 1
                if str(lemma) not in examples[key]:
                    examples[key].append(str(lemma))
                if node_dir.name not in where[key]:
                    where[key].append(node_dir.name)
    report = [
        MissingLemma(key, count, tuple(examples[key]), tuple(where[key]))
        for key, count in counts.items()
        if count >= threshold
    ]
    report.sort(key=lambda m: (-m.count, m.key))
    return report
