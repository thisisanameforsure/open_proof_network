"""F19-T4, T5: outline every merged proof artifact of a graph that has no outline yet (R5-R7, Q9).

``outline.py`` turns one artifact into an ``outline/v1`` document; this module finds the artifacts
and builds what each one imports, for ``opn-gate outline`` (the graph's ``outline`` job after each
building merge, and the backfill workflow).

* **What is outlined (R1, Q9)**: every merged proof artifact of a target — each node's
  ``Proof.lean`` and each alternate under ``attempts/`` (``graph.proofs_of``, which takes a file
  only with the merged passing attestation that names its bytes), and each merged partial assembly
  (``graph.partials_of``). A partial's ``sorry`` steps name their children from F18's
  decompositions (``products.decompositions_of``), never from anything derived here. One outline
  per artifact hash: two artifacts with the same bytes share it.
* **Only what is missing**: an artifact whose ``targets/<id>/outlines/<hash>.json`` is in the tree
  read or in the destination costs nothing, not even the image, so a job that runs after every
  building merge pays only for what that merge (or a lost earlier run) left without one.
* **How it is built (R6)**: as step 4 stages it (``steps.stage``): the artifact staged as the
  node's own ``Proof`` module over its dependency closure and its uses, the definitions compiled
  (``defs.compile_all``), every module it imports compiled through the toolchain it is handed —
  the step-3 sandbox in the CLI — and ``opn-outline`` run over the staged file with that build on
  its search path. Nothing is replayed and nothing is judged: the artifact was attested when it
  merged, and an outline decides nothing (§6). The node's own ``Proof`` module is never compiled:
  ``opn-outline`` elaborates the artifact itself. One work directory per node, so a node's
  alternate and its partial reuse the build its proof made.
* **Failure (R5, C7)**: an artifact whose file is missing, whose build fails, or whose extraction
  fails is named with its reason and writes nothing; a target that cannot be read is named and
  its artifacts are left for the next run; nothing stops another artifact or target.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from opn_gate import defs, graph, layout, outline, products, schemas
from opn_gate.sandbox import MemoryExceeded
from opn_gate.steps import stage as staging
from opn_gate.toolchain import ResolvedToolchain, Toolchain, module_output_path

#: Reasons this module adds to ``outline.REASONS`` (F19-R5): strings, as Q11 (10) has them.
MISSING = "artifact-missing"
BUILD_FAILED = "build-failed"
TARGET_UNREADABLE = "target-unreadable"

_DETAIL_CAP = 2000

#: Gives the toolchain for one work directory, given the target's gate-spec: the CLI's builds
#: a step-3 sandbox that mounts that directory and nothing else.
ToolchainFor = Callable[[Mapping[str, Any], Path], Toolchain]


class BuildError(RuntimeError):
    """What the artifact imports could not be built; the message names the module."""


@dataclass(frozen=True)
class Found:
    """One merged proof artifact of a node, and the children of its holes (a partial's only)."""

    target: str
    node: str
    artifact: outline.Artifact
    holes: Mapping[str, str | None] = field(default_factory=dict)


@dataclass(frozen=True)
class Entry:
    """One line of the report: an artifact (or, with ``node`` None, a target) and what became of
    it. ``outline`` is the written file's path relative to the destination."""

    target: str
    node: str | None
    path: str | None
    kind: str | None
    artifact_hash: str | None
    outline: str | None = None
    reason: str | None = None
    detail: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "target": self.target,
            "node": self.node,
            "path": self.path,
            "kind": self.kind,
            "artifact_hash": self.artifact_hash,
            "outline": self.outline,
            "reason": self.reason,
            "detail": self.detail,
        }

    @classmethod
    def of(cls, found: Found, **kw: Any) -> Entry:
        a = found.artifact
        return cls(found.target, found.node, a.path, a.kind, a.hash, **kw)


@dataclass
class Report:
    """What one run did: every artifact written, already present, or failed with its reason."""

    targets: list[str] = field(default_factory=list)
    written: list[Entry] = field(default_factory=list)
    present: list[Entry] = field(default_factory=list)
    failed: list[Entry] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "targets": list(self.targets),
            "written": [e.as_dict() for e in self.written],
            "present": [e.as_dict() for e in self.present],
            "failed": [e.as_dict() for e in self.failed],
        }


# --- finding the artifacts ---------------------------------------------------------------------


def target_ids(tree: Path) -> list[str]:
    """Every target of the tree: a directory under ``targets/`` with a ``gate-spec.json``
    (``targets/index.json`` sits beside them and is not one, 2026-09-18)."""
    return sorted(p.parent.name for p in (tree / "targets").glob("*/gate-spec.json"))


def merged_artifacts(tree: Path, target_id: str) -> list[Found]:
    """Every merged proof artifact of the target, node by node in id order: the proof, then its
    alternates, then its partials. Read with ``graph.load_nodes``, which derives no status and
    infers no root: an outline needs neither, and a target whose root is ambiguous still has
    proofs to outline. A ``GraphError`` (a node that does not load) is the caller's to report."""
    attestations = graph.load_attestations(tree)
    nodes = graph.load_nodes(tree, target_id, attestations)
    spec = schemas.load_json(layout.gate_spec_path(tree, target_id), "gate-spec/v1")
    tg = graph.TargetGraph(
        target_id=target_id,
        path=tree / "targets" / target_id,
        spec=spec,
        nodes=nodes,
        statuses={},
        root="",
        declaration=None,
    )
    out: list[Found] = []
    for node_id in sorted(nodes):
        facts = nodes[node_id]
        for p in facts.proofs:
            out.append(Found(target_id, node_id, outline.Artifact(p.path, p.artifact_hash, p.kind)))
        if not facts.partials:
            continue
        children = {
            d["partial"]: {h["name"]: h["node"] for h in d["holes"]}
            for d in products.decompositions_of(tg, node_id)
        }
        for partial in facts.partials:
            file = facts.path / partial.path
            digest = schemas.content_hash(file.read_bytes()) if file.is_file() else ""
            out.append(
                Found(
                    target_id,
                    node_id,
                    outline.Artifact(partial.path, digest, "partial"),
                    children.get(partial.path, {}),
                )
            )
    return out


# --- building what one artifact imports ------------------------------------------------------


def build(  # noqa: PLR0913 — one argument per fact the build needs
    toolchain: Toolchain,
    tc: ResolvedToolchain,
    tree: Path,
    found: Found,
    workdir: Path,
    *,
    timeout_s: float,
) -> outline.Job:
    """Stage the artifact as its node's ``Proof`` module and compile everything it imports,
    deps first, as step 4 does; ``BuildError`` names what failed. A module already built in
    ``workdir`` (by an earlier artifact of the same node) is not compiled again."""
    node_dir = layout.graph_nodes_dir(tree, found.target) / found.node
    loaded = layout.load_node(node_dir, found.target)
    if isinstance(loaded, list):
        raise BuildError("; ".join(d.message for d in loaded))
    staged = staging.stage(loaded, workdir, proof_override=node_dir / found.artifact.path)
    if staged.problems:
        raise BuildError("; ".join(p.message for p in staged.problems))
    target_dir = layout.gate_spec_path(tree, found.target).parent
    problem = defs.compile_all(toolchain, tc, target_dir, workdir, timeout_s=timeout_s)
    if problem is not None:
        raise BuildError(problem.message)
    for node_id in staged.order:
        for stem in ("Context", "Proof"):
            if node_id == found.node and stem == "Proof":
                continue  # the artifact itself: opn-outline elaborates it
            module = layout.node_module(node_id, stem)
            if (staged.build / module_output_path(module, ".olean")).is_file():
                continue
            elab = toolchain.elaborate(
                tc,
                staged.root / staged.rel(node_id, stem),
                module,
                staged.build,
                root=staged.root,
                timeout_s=timeout_s,
            )
            if not elab.ok:
                first = elab.errors[0].as_dict() if elab.errors else elab.stderr
                msg = f"{module} does not elaborate: {first}"
                raise BuildError(msg[:_DETAIL_CAP])
    return outline.Job(
        target=found.target,
        node=found.node,
        artifact=found.artifact,
        file=staged.root / staged.rel(found.node, "Proof"),
        module=layout.node_module(found.node, "Proof"),
        decl=loaded.statement.decl_name,
        holes=dict(found.holes),
        search_path=(staged.build,),
    )


# --- the run -------------------------------------------------------------------------------------


def _present(roots: Sequence[Path], target_id: str, digest: str) -> bool:
    return any(outline.outline_path(r / "targets" / target_id, digest).is_file() for r in roots)


def _detail(exc: BaseException) -> str:
    if isinstance(exc, BuildError):
        return str(exc)[:_DETAIL_CAP]
    return f"{type(exc).__name__}: {exc}"[:_DETAIL_CAP]


def _build_reason(exc: BaseException) -> str:
    """A build killed at the memory cap or the clock says so (F02-T6); anything else is a
    failed build."""
    if isinstance(exc, MemoryExceeded):
        return outline.MEMORY
    if isinstance(exc, subprocess.TimeoutExpired):
        return outline.TIMEOUT
    return BUILD_FAILED


def _pending(found: Sequence[Found], report: Report, *, roots: Sequence[Path]) -> list[Found]:
    """The artifacts still to outline, once each; the report gets every other one: a file the
    tree does not hold (failed), and an outline already in a tree read or written (present)."""
    pending: list[Found] = []
    seen: set[str] = set()
    for f in found:
        if not f.artifact.hash:
            report.failed.append(
                Entry.of(f, reason=MISSING, detail=f"{f.artifact.path} is not in the tree")
            )
        elif f.artifact.hash in seen or _present(roots, f.target, f.artifact.hash):
            report.present.append(Entry.of(f))
        else:
            seen.add(f.artifact.hash)
            pending.append(f)
    return pending


def run_target(  # noqa: PLR0913 — the tree, the target, where it writes, and the run's facts
    tree: Path,
    target_id: str,
    report: Report,
    *,
    dest: Path,
    work: Path,
    toolchain_for: ToolchainFor,
    gate: str,
    caps: outline.Caps,
) -> None:
    """Outline every artifact of one target that has no outline, into ``report``."""
    try:
        spec = schemas.load_json(layout.gate_spec_path(tree, target_id), "gate-spec/v1")
        found = merged_artifacts(tree, target_id)
    except Exception as exc:  # one target's defect never stops another (C7)
        report.failed.append(
            Entry(target_id, None, None, None, None, reason=TARGET_UNREADABLE, detail=_detail(exc))
        )
        return
    pending = _pending(found, report, roots=(tree, dest))
    if not pending:
        return  # nothing to extract: no image, no toolchain
    timeout_s = float(spec["step3_caps"]["wallclock_s"])
    try:
        tc = toolchain_for(spec, work / target_id).resolve(
            str(spec["lean_toolchain"]),
            mathlib_sha=str(spec["mathlib_sha"]) if spec.get("mathlib_sha") else None,
        )
    except Exception as exc:
        for f in pending:
            report.failed.append(Entry.of(f, reason=outline.TOOLCHAIN, detail=_detail(exc)))
        return
    target_dir = dest / "targets" / target_id
    for f in pending:
        workdir = work / target_id / f.node
        try:
            toolchain = toolchain_for(spec, workdir)
            job = build(toolchain, tc, tree, f, workdir, timeout_s=timeout_s)
        except Exception as exc:  # one artifact's failure stops no other (R5)
            report.failed.append(Entry.of(f, reason=_build_reason(exc), detail=_detail(exc)))
            continue
        outcome = outline.write(
            target_dir, outline.extract(toolchain, tc, job, gate=gate, caps=caps)
        )
        if outcome.written is None:
            report.failed.append(
                Entry.of(f, reason=outcome.reason, detail=outcome.detail[:_DETAIL_CAP])
            )
        else:
            report.written.append(Entry.of(f, outline=outcome.written.relative_to(dest).as_posix()))


def run(  # noqa: PLR0913 — the tree, the targets, where it writes, and the run's facts
    tree: Path,
    targets: Sequence[str],
    *,
    dest: Path,
    work: Path,
    toolchain_for: ToolchainFor,
    gate: str,
    caps: outline.Caps,
) -> Report:
    """Outline every target in ``targets``; the report names every artifact once."""
    report = Report(targets=list(targets))
    for target_id in targets:
        run_target(
            tree,
            target_id,
            report,
            dest=dest,
            work=work,
            toolchain_for=toolchain_for,
            gate=gate,
            caps=caps,
        )
    return report
