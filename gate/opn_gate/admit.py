"""Mechanical admission: may this node directory enter the graph? (F08-R1, R4; D-29, D-30)

D-29's rule is that structure needs no human approval — a proposed node is admitted if it passes
the same checks the gate already applies to statements, and refused otherwise. No curator signs
off on a well-formed node, and no reviewer can wave a malformed one through. So admission is not
a new kind of check: it is F00's layout rule, F01's witness and context rules, F02's hazard
checkers and F03's acyclicity, run in one order over a node that has no proof yet.

The order is R1's, and it is chosen so the first failure is the most useful one: a statement that
does not elaborate makes every later question meaningless, a witness that does not typecheck
makes the hazards moot. Each check runs only if the ones before it passed, and the verdict names
the first failure, in the shape a gate verdict has (F00-R7).

What is *not* here: any judgment about whether the statement is worth having. That is the
frontier's business and the curator's (D-25, D-14), and admission has no opinion.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import traceback
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from opn_gate import graph as graphmod
from opn_gate import layout, records, schemas
from opn_gate.diagnostic import Diagnostic
from opn_gate.scaffold import LABELS_NEEDING_PROOF, RELATION_DECL, RELATION_FILE
from opn_gate.steps.base import RunContext, Step, StepResult
from opn_gate.steps.deps import check_context
from opn_gate.steps.hazards import HazardsStep, StatementStep
from opn_gate.steps.toolchain_step import ToolchainStep
from opn_gate.steps.witness import WitnessStep
from opn_gate.toolchain import MetaprogramResult, RelationRequest, ResolvedToolchain

log = logging.getLogger(__name__)

STATEMENT_MODULE = "Statement"
#: The one axiom a statement is expected to rest on: its own ``sorry`` body (D-3).
SORRY_AXIOM = "sorryAx"


@dataclass(frozen=True)
class CheckRecord:
    name: str
    result: str  # pass | fail | skipped
    diagnostic: Diagnostic | None = None

    def as_dict(self, max_bytes: int | None = None) -> dict[str, Any]:
        return {
            "check": self.name,
            "result": self.result,
            "diagnostic": None if self.diagnostic is None else self.diagnostic.as_dict(max_bytes),
        }


@dataclass(frozen=True)
class Admission:
    """The verdict, in the gate's shape but keyed by check name rather than D-4 step number."""

    admitted: bool
    checks: tuple[CheckRecord, ...]
    first_failing_check: str | None = None
    diagnostic: Diagnostic | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def as_dict(self, max_bytes: int | None = None) -> dict[str, Any]:
        return {
            "verdict": "pass" if self.admitted else "fail",
            "first_failing_check": self.first_failing_check,
            "diagnostic": None if self.diagnostic is None else self.diagnostic.as_dict(max_bytes),
            "checks": [c.as_dict(max_bytes) for c in self.checks],
        }


# --- the checks admission adds to the ones the steps already are --------------------------------


class StatementAxiomsCheck:
    """R1: ``Statement.lean`` elaborates, and rests on nothing but its own ``sorry``.

    A statement that quietly leans on an axiom outside the graph's allowlist is a statement about
    a different mathematics than the one the target claims, and it would be inherited by every
    proof of it — so it is refused at admission, where it costs one person a rewrite, rather than
    at the first submission, where it costs everyone who tried.
    """

    number = 5
    name = "statement-axioms"

    def run(self, ctx: RunContext) -> StepResult:  # noqa: PLR0911 — one return per rule
        node = ctx.node
        tc: ResolvedToolchain | None = ctx.data.get("toolchain")
        if node is None or tc is None:
            return StepResult.failed("check-order", "the axiom check needs the earlier checks")
        module = layout.node_module(node.node_id, STATEMENT_MODULE)
        src = ctx.workdir / "src"
        try:
            elab = ctx.toolchain.elaborate(
                tc,
                src / "Nodes" / node.node_id / "Statement.lean",
                module,
                ctx.build_dir,
                root=src,
                timeout_s=ctx.wallclock_s,
            )
        except subprocess.TimeoutExpired:
            return StepResult.failed(
                "timeout", f"the statement exceeded the {ctx.wallclock_s:g}s wall-clock cap"
            )
        if not elab.ok:
            return StepResult.failed(
                "statement-elaboration",
                "Statement.lean does not elaborate",
                module=module,
                messages=[m.as_dict() for m in elab.errors or elab.messages],
            )
        try:
            found = ctx.toolchain.axioms(
                tc,
                module,
                node.statement.decl_name,
                [ctx.build_dir],
                ctx.workdir / "axioms",
                timeout_s=ctx.wallclock_s,
            )
        except subprocess.TimeoutExpired:
            return StepResult.failed("timeout", "the axiom check exceeded the wall-clock cap")
        if not found.ok:
            return StepResult.failed(
                "statement-axioms-unreadable",
                "could not read the statement's axioms",
                output=found.output[-2000:],
            )
        allowed = {*ctx.spec["axiom_allowlist"], SORRY_AXIOM}
        outside = sorted(a for a in found.axioms if a not in allowed)
        ctx.data["statement_axioms"] = sorted(found.axioms)
        if outside:
            return StepResult.failed(
                "statement-axiom",
                f"Statement.lean rests on axioms outside the allowlist: {', '.join(outside)}",
                axioms=outside,
            )
        return StepResult.passed()


class ContextCheck:
    """R1: ``Context.lean`` carries each declared dep's signature (F01-R6), for a node with no
    proof — so this is step 8's first half and nothing else."""

    number = 8
    name = "context"

    def run(self, ctx: RunContext) -> StepResult:
        node = ctx.node
        if node is None:
            return StepResult.failed("check-order", "the context check needs the layout check")
        raw = node.meta.get("deps")
        declared = [str(d) for d in raw] if isinstance(raw, list) else []
        problem = check_context(node, declared)
        return problem if problem is not None else StepResult.passed()


class GraphCheck:
    """R1: every declared dep is a node of this target, and the graph with this node stays a DAG
    (F03-R3). Read from META alone, because a proposal's siblings need not be loadable for the
    question 'does this create a cycle?' to have an answer."""

    number = 8
    name = "graph"

    def run(self, ctx: RunContext) -> StepResult:
        node = ctx.node
        if node is None:
            return StepResult.failed("check-order", "the graph check needs the layout check")
        nodes_dir = layout.graph_nodes_dir(ctx.graph_root, ctx.claim.target_id)
        try:
            edges = dep_edges(nodes_dir)
        except schemas.SchemaError as exc:
            return StepResult.failed("graph-unreadable", str(exc))
        absent = graphmod.missing_dep(edges)
        if absent is not None:
            owner, dep = absent
            return StepResult.failed(
                "dep-unknown",
                f"node {owner!r} declares dep {dep!r}, which is not a node of this target",
                node=owner,
                dep=dep,
            )
        cycle = graphmod.find_cycle(edges)
        if cycle is not None:
            return StepResult.failed(
                "dependency-cycle",
                "dependency cycle: " + " -> ".join(cycle),
                cycle=cycle,
            )
        ctx.data["graph"] = {"nodes": sorted(edges), "deps": edges.get(node.node_id, ())}
        return StepResult.passed()


class RelationCheck:
    """R4, D-30: a variant's label above ``related`` is a claim, and the claim is kernel-checkable.

    ``resolves`` means the variant implies the root, ``partial`` means the root implies the
    variant. Getting the direction backwards is the failure the label exists to price, so the
    gate derives the expected implication from the label and compares, rather than reading the
    label and believing it.

    The label is the ``-- relation:`` line in ``Relation.lean`` (F03's convention), so a claim
    and its proof are the same file: there is no way to assert ``resolves`` and supply nothing.
    """

    number = 9
    name = "relation"

    def run(self, ctx: RunContext) -> StepResult:  # noqa: PLR0911 — one return per rule
        node = ctx.node
        tc: ResolvedToolchain | None = ctx.data.get("toolchain")
        if node is None or tc is None:
            return StepResult.failed("check-order", "the relation check needs the earlier checks")
        origin = str(node.meta.get("origin"))
        relation_path = node.path / RELATION_FILE
        if origin != "variant":
            if relation_path.is_file():
                return StepResult.failed(
                    "relation-not-a-variant",
                    f"{RELATION_FILE} belongs to variants only (D-3); this node's origin is "
                    f"{origin!r}",
                    origin=origin,
                )
            return StepResult.passed()
        label = graphmod.relation_of(node.path, origin) or "related"
        ctx.data["relation_label"] = label
        if label not in LABELS_NEEDING_PROOF:
            if relation_path.is_file():
                return StepResult.failed(
                    "relation-unlabelled",
                    f"{RELATION_FILE} is present but claims nothing: add a `-- relation: partial` "
                    "or `-- relation: resolves` line, or drop the file (D-30)",
                    label=label,
                )
            return StepResult.passed()
        root_id = root_of(ctx.graph_root, ctx.claim.target_id, exclude=node.node_id)
        if root_id is None or root_id == node.node_id:
            return StepResult.failed(
                "relation-root-unknown",
                "the target's root is not known, so there is nothing to relate the variant to",
            )
        root_dir = node.path.parent / root_id
        root = layout.load_node(root_dir, ctx.claim.target_id)
        if isinstance(root, list):
            return StepResult.failed(
                "relation-root-invalid", f"the root {root_id}: {root[0].message}"
            )
        staged = stage_context(ctx, tc, root_id, root_dir)
        if staged is not None:
            return staged
        declared = layout.parse_declaration(
            relation_path.read_text(encoding="utf-8"), RELATION_FILE
        )
        if isinstance(declared, Diagnostic):
            return StepResult(ok=False, diagnostic=declared)
        if declared != RELATION_DECL:
            return StepResult.failed(
                "relation-decl",
                f"{RELATION_FILE} declares {declared}; D-30's relation proof is "
                f"`theorem {RELATION_DECL}`",
                declared=declared,
            )
        req = RelationRequest(
            variant=node.path / "Statement.lean",
            variant_module=layout.node_module(node.node_id, STATEMENT_MODULE),
            variant_decl=node.statement.decl_name,
            root=root_dir / "Statement.lean",
            root_module=layout.node_module(root_id, STATEMENT_MODULE),
            root_decl=root.statement.decl_name,
            label=label,
            relation=relation_path,
            relation_module=layout.node_module(node.node_id, "Relation"),
            relation_decl=RELATION_DECL,
        )
        try:
            result = ctx.toolchain.relation_type(
                tc, req, [ctx.build_dir], timeout_s=ctx.wallclock_s
            )
        except subprocess.TimeoutExpired:
            return StepResult.failed("timeout", "the relation check exceeded the wall-clock cap")
        return relation_verdict(ctx, label, result)


def stage_context(
    ctx: RunContext, tc: ResolvedToolchain, node_id: str, node_dir: Path
) -> StepResult | None:
    """Compile ``node_id``'s ``Context.lean`` into the build directory, or say why not.

    The relation proof and the root's statement import the root's Context, and only the node
    under admission has had its own compiled (by the layout check). Without this the metaprogram
    cannot import what the files it is handed say they need.
    """
    src = ctx.workdir / "src"
    dest = src / "Nodes" / node_id
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("Statement.lean", "Context.lean"):
        source = node_dir / name
        if source.is_file():
            shutil.copy(source, dest / name)
    ctx.build_dir.mkdir(parents=True, exist_ok=True)
    module = layout.node_module(node_id, "Context")
    try:
        elab = ctx.toolchain.elaborate(
            tc, dest / "Context.lean", module, ctx.build_dir, root=src, timeout_s=ctx.wallclock_s
        )
    except subprocess.TimeoutExpired:
        return StepResult.failed("timeout", f"compiling {module} exceeded the wall-clock cap")
    if not elab.ok:
        return StepResult.failed(
            "relation-root-context",
            f"{module} does not elaborate, so the root's statement cannot be read",
            module=module,
            messages=[m.as_dict() for m in elab.errors or elab.messages],
        )
    return None


def root_of(graph_root: Path, target_id: str, *, exclude: str | None = None) -> str | None:
    """The target's root: what the products say, else what the declaration says, else the one
    node nothing depends on (F03-Q5's rule, asked without loading every node).

    ``exclude`` drops the node being admitted from the last of those, because a proposal is
    un-depended-on by construction and would otherwise look like a second root.
    """
    target_dir = graph_root / "targets" / target_id
    rendered = target_dir / "graph.json"
    if rendered.is_file():
        try:
            root = schemas.load_json(rendered).get("root")
        except schemas.SchemaError:
            root = None
        if isinstance(root, str) and root:
            return root
    declaration = records.load_target_status(target_dir)
    if declaration is not None and declaration.doc.get("root"):
        return str(declaration.doc["root"])
    try:
        edges = dep_edges(layout.graph_nodes_dir(graph_root, target_id))
    except (schemas.SchemaError, OSError):
        return None
    depended_on = {dep for deps in edges.values() for dep in deps}
    roots = sorted(set(edges) - depended_on - ({exclude} if exclude else set()))
    return roots[0] if len(roots) == 1 else None


def relation_verdict(ctx: RunContext, label: str, result: MetaprogramResult) -> StepResult:
    """R4: what the relation metaprogram's answer means."""
    ok, doc = result.ok, result.doc
    if not ok and not doc:
        return StepResult.failed(
            "metaprogram-failed",
            f"opn-relation-type exited {result.exit_code} without a JSON verdict",
            exit_code=result.exit_code,
            output=result.output,
        )
    if not ok:
        return StepResult.failed(
            "relation-elaboration",
            str(doc.get("error") or "the relation proof does not elaborate"),
            messages=[m.as_dict() for m in result.messages],
        )
    ctx.data["relation"] = {
        "label": label,
        "expected": doc.get("expected"),
        "declared": doc.get("declared"),
        "axioms": sorted(str(a) for a in doc.get("axioms") or []),
    }
    axioms = ctx.data["relation"]["axioms"]
    if SORRY_AXIOM in axioms:
        return StepResult.failed(
            "relation-sorry",
            f"{RELATION_FILE} depends on sorryAx: the implication is claimed, not proved (D-30)",
            axioms=axioms,
        )
    allowed = set(ctx.spec["axiom_allowlist"])
    outside = [a for a in axioms if a not in allowed]
    if outside:
        return StepResult.failed(
            "relation-axiom",
            f"{RELATION_FILE} depends on axioms outside the allowlist: {', '.join(outside)}",
            axioms=outside,
        )
    if doc.get("matches") is not True:
        return StepResult.failed(
            "relation-direction",
            f"a variant labeled {label!r} must prove {doc.get('expected')}, but "
            f"{RELATION_FILE} proves {doc.get('declared')} (D-30)",
            label=label,
            expected=doc.get("expected"),
            declared=doc.get("declared"),
        )
    return StepResult.passed()


def dep_edges(nodes_dir: Path) -> dict[str, tuple[str, ...]]:
    """Every node of the target and the deps its META declares — ids only (F03-R3's question)."""
    edges: dict[str, tuple[str, ...]] = {}
    for node_dir in sorted(p for p in nodes_dir.iterdir() if p.is_dir()):
        meta_path = node_dir / "META.yaml"
        if not meta_path.is_file():
            msg = f"{node_dir.name} has no META.yaml"
            raise schemas.SchemaError(msg)
        meta = schemas.load_yaml(meta_path)
        raw = meta.get("deps")
        edges[node_dir.name] = tuple(str(d) for d in raw) if isinstance(raw, list) else ()
    return edges


# --- the order, and running it -------------------------------------------------------------------


def default_checks() -> list[tuple[str, Step]]:
    """R1's order. The names are the verdict's vocabulary, so they are stable."""
    return [
        ("toolchain", ToolchainStep()),
        ("layout", StatementStep()),
        ("statement", StatementAxiomsCheck()),
        ("witness", WitnessStep()),
        ("hazards", HazardsStep()),
        ("context", ContextCheck()),
        ("graph", GraphCheck()),
        ("relation", RelationCheck()),
    ]


def run(ctx: RunContext, checks: Sequence[tuple[str, Step]] | None = None) -> Admission:
    """Run the checks in order, stopping at the first failure (F00-R7, R18).

    An unexpected exception inside a check is that check's failure, never a crash: admission runs
    on contributor files, and a malformed one must produce a verdict like any other (C7).
    """
    ordered = list(default_checks() if checks is None else checks)
    records: list[CheckRecord] = []
    failed_at: str | None = None
    diagnostic: Diagnostic | None = None
    for name, step in ordered:
        if failed_at is not None:
            records.append(CheckRecord(name, "skipped"))
            continue
        try:
            result = step.run(ctx)
        except Exception as exc:  # R18: any exception is this check's failure
            log.exception("admission check %s raised", name)
            result = StepResult.failed(
                "unexpected-error",
                f"{type(exc).__name__}: {exc}",
                exception=type(exc).__name__,
                traceback=traceback.format_exc(limit=5),
            )
        if result.ok:
            records.append(CheckRecord(name, "pass", result.diagnostic))
        else:
            failed_at = name
            diagnostic = result.diagnostic or Diagnostic("failed", "check failed without detail")
            records.append(CheckRecord(name, "fail", diagnostic))
            log.info("admission check %s failed: %s", name, diagnostic.code)
    return Admission(
        admitted=failed_at is None,
        checks=tuple(records),
        first_failing_check=failed_at,
        diagnostic=diagnostic,
        data=dict(ctx.data),
    )
