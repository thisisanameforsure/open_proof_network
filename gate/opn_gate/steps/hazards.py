"""D-4 step 6: hazard checkers over the statement (F02-R3 to R5, R10; Q1, Q3, Q4).

The checkers themselves are Lean (``opn-hazards``, F02-T1/T2); this step runs exactly the ones
the graph's ``gate-spec.json`` names, matches every finding against the node's
``acknowledged_hazards`` (``META.yaml``, ``meta/v2``) on ``checker`` and ``location``, fails
naming every unacknowledged finding, and on a pass records the acknowledgments it relied on in
the step's own record so a reviewer sees what was waved through (R5).

``check_config`` is the R3 guard the pipeline runs before step 1: an unknown checker id in the
spec is the gate owner's configuration error, not a submission's.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Any

from opn_gate import layout
from opn_gate.diagnostic import Diagnostic
from opn_gate.steps.base import RunContext, StepResult
from opn_gate.steps.replay import CONTEXT_MODULE
from opn_gate.steps.witness import metaprogram_failure
from opn_gate.toolchain import HazardsRequest, ResolvedToolchain

#: Every checker id this gate version ships (F02-R2), in id order. The lean tier checks this
#: against ``opn-hazards --list`` so the two registries cannot drift.
KNOWN_CHECKERS: tuple[str, ...] = (
    "div-zero",
    "int-trunc",
    "junk-value",
    "nat-sub",
    "off-by-one-range",
    "unused-binder",
)


def check_config(spec: dict[str, Any]) -> Diagnostic | None:
    """R3: the spec's ``hazard_checkers`` must all be known; else a configuration diagnostic."""
    listed = [str(c) for c in spec.get("hazard_checkers") or []]
    unknown = [c for c in listed if c not in KNOWN_CHECKERS]
    if not unknown:
        return None
    return Diagnostic(
        "config-unknown-checker",
        f"gate-spec.json names hazard checker(s) this gate does not ship: {', '.join(unknown)}",
        {"unknown": unknown, "known": list(KNOWN_CHECKERS)},
    )


@dataclass(frozen=True)
class Finding:
    checker: str
    location: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"checker": self.checker, "location": self.location, "message": self.message}


@dataclass(frozen=True)
class Acknowledgment:
    checker: str
    location: str
    justification: str

    def as_dict(self) -> dict[str, str]:
        return {
            "checker": self.checker,
            "location": self.location,
            "justification": self.justification,
        }


def findings_from(doc: dict[str, Any]) -> list[Finding]:
    out: list[Finding] = []
    for raw in doc.get("findings") or []:
        if isinstance(raw, dict):
            out.append(
                Finding(
                    str(raw.get("checker", "")),
                    str(raw.get("location", "")),
                    str(raw.get("message", "")),
                )
            )
    return out


def acknowledgments_from(meta: dict[str, object]) -> list[Acknowledgment]:
    """The node's ``acknowledged_hazards`` (``meta/v2``); ``meta/v1`` has none (R6)."""
    raw = meta.get("acknowledged_hazards")
    if not isinstance(raw, list):
        return []
    return [
        Acknowledgment(
            str(a.get("checker", "")), str(a.get("location", "")), str(a.get("justification", ""))
        )
        for a in raw
        if isinstance(a, dict)
    ]


@dataclass(frozen=True)
class Evaluation:
    unacknowledged: tuple[Finding, ...]
    used: tuple[Acknowledgment, ...]
    unused: tuple[Acknowledgment, ...]


def evaluate(findings: list[Finding], acks: list[Acknowledgment]) -> Evaluation:
    """R4: a finding is acknowledged by an entry matching checker and location whose
    justification is non-empty; anything else leaves the finding standing."""
    valid = [a for a in acks if a.justification.strip()]
    used: list[Acknowledgment] = []
    open_findings: list[Finding] = []
    for f in findings:
        match = next(
            (a for a in valid if a.checker == f.checker and a.location == f.location), None
        )
        if match is None:
            open_findings.append(f)
        elif match not in used:
            used.append(match)
    unused = [a for a in acks if a not in used]
    return Evaluation(tuple(open_findings), tuple(used), tuple(unused))


class StatementStep:
    """Step 2 of the standalone ``opn-gate hazards`` run (R7): load the node and compile its
    repo ``Context.lean`` — the sorry-bodied dep signatures, which need no merged proofs — so
    the statement elaborates. No diff, no Proof.lean: a proposed node has neither."""

    number = 2
    name = "statement"

    def run(self, ctx: RunContext) -> StepResult:
        tc: ResolvedToolchain | None = ctx.data.get("toolchain")
        if tc is None:
            return StepResult.failed("step-order", "the statement step needs step 1 to have passed")
        node_dir = layout.graph_nodes_dir(ctx.graph_root, ctx.claim.target_id) / ctx.claim.node_id
        loaded = layout.load_node(node_dir, ctx.claim.target_id)
        if isinstance(loaded, list):
            first = loaded[0]
            return StepResult.failed(
                first.code, first.message, **first.details, problems=[d.message for d in loaded]
            )
        ctx.node = loaded
        root = ctx.workdir / "src"
        dest = root / "Nodes" / loaded.node_id
        dest.mkdir(parents=True, exist_ok=True)
        for name in ("Statement.lean", CONTEXT_MODULE + ".lean"):
            shutil.copy(loaded.path / name, dest / name)
        ctx.build_dir.mkdir(parents=True, exist_ok=True)
        module = layout.node_module(loaded.node_id, CONTEXT_MODULE)
        try:
            elab = ctx.toolchain.elaborate(
                tc,
                dest / "Context.lean",
                module,
                ctx.build_dir,
                root=root,
                timeout_s=ctx.wallclock_s,
            )
        except subprocess.TimeoutExpired:
            return StepResult.failed(
                "timeout", f"compiling {module} exceeded the {ctx.wallclock_s:g}s wall-clock cap"
            )
        if not elab.ok:
            return StepResult.failed(
                "elaboration-failed",
                f"{module} does not elaborate",
                module=module,
                messages=[m.as_dict() for m in elab.errors or elab.messages],
            )
        return StepResult.passed()


class HazardsStep:
    number = 6
    name = "hazards"

    def run(self, ctx: RunContext) -> StepResult:  # noqa: PLR0911 — one return per rule
        node = ctx.node
        tc: ResolvedToolchain | None = ctx.data.get("toolchain")
        if node is None or tc is None:
            return StepResult.failed("step-order", "step 6 needs steps 1 and 2 to have passed")
        checkers = [str(c) for c in ctx.spec.get("hazard_checkers") or []]
        problem = check_config(ctx.spec)
        if problem is not None:
            return StepResult(ok=False, diagnostic=problem)
        acks = acknowledgments_from(node.meta)
        if not checkers:
            ctx.data["hazards"] = {"checkers": [], "findings": [], "acknowledged": []}
            return StepResult.passed()

        staged = ctx.data.get("staged")
        node_dir = staged.node_dir(node.node_id) if staged is not None else node.path
        req = HazardsRequest(
            statement=node_dir / "Statement.lean",
            module=layout.node_module(node.node_id, "Statement"),
            decl=node.statement.decl_name,
            checkers=tuple(checkers),
        )
        try:
            result = ctx.toolchain.hazards(tc, req, [ctx.build_dir], timeout_s=ctx.wallclock_s)
        except subprocess.TimeoutExpired:
            return StepResult.failed(
                "timeout", f"step 6 exceeded the {ctx.wallclock_s:g}s wall-clock cap"
            )
        if not result.ok and not result.doc:
            return metaprogram_failure(self.number, result)
        if not result.ok:
            return StepResult.failed(
                "hazards-unreadable",
                result.error or "the hazard checkers could not run over the statement",
                messages=[m.as_dict() for m in result.messages],
            )
        findings = findings_from(result.doc)
        ev = evaluate(findings, acks)
        ctx.data["hazards"] = {
            "checkers": checkers,
            "findings": [f.as_dict() for f in findings],
            "acknowledged": [a.as_dict() for a in ev.used],
            "capped": bool(result.doc.get("capped")),
        }
        if ev.unacknowledged:
            first = ev.unacknowledged[0]
            return StepResult.failed(
                "hazard-unacknowledged",
                f"{len(ev.unacknowledged)} unacknowledged hazard finding(s); first: "
                f"{first.checker} at {first.location}: {first.message}",
                findings=[f.as_dict() for f in ev.unacknowledged],
                acknowledged=[a.as_dict() for a in ev.used],
                checkers=checkers,
            )
        if ev.used:
            return StepResult.passed_with(
                "hazards-acknowledged",
                f"{len(ev.used)} hazard finding(s) acknowledged in META.yaml",
                acknowledged=[a.as_dict() for a in ev.used],
            )
        return StepResult.passed()
