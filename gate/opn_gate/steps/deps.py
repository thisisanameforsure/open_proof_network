"""D-4 step 8: declared dependencies (F01-R4 to R7; Q2, Q3, Q4).

Every constant the proof depends on is classified by the module it came from. Library and
``defs/`` constants are free; a constant from another node's module must be one of the node's
declared deps (R5). The repo's ``Context.lean`` must carry, for each declared dep, a signature
hash-equal to that dep's ``Statement.lean`` signature (R6) — the guarantee that makes the
gate-time Context substitution (Q4) sound. A declared dep the proof never touches is a warning,
never a failure (R7, Q3).
"""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

from opn_gate import layout, schemas
from opn_gate.steps.base import RunContext, StepResult
from opn_gate.steps.replay import PROOF_MODULE
from opn_gate.steps.witness import metaprogram_failure
from opn_gate.toolchain import ResolvedToolchain, UsedConstantsRequest

log = logging.getLogger(__name__)

_CONTEXT_DECL_RE = re.compile(
    r"^(?:theorem|lemma)\s+(?P<name>[^\s:({\[]+)(?P<sig>.*?):=", re.M | re.S
)
_WS = re.compile(r"\s+")


def normalize_signature(text: str) -> str:
    return _WS.sub(" ", text).strip()


def statement_signature(statement: layout.Statement) -> str:
    """The theorem's signature text from ``theorem`` up to (not including) ``:=``."""
    prefix = statement.prefix
    start = _CONTEXT_DECL_RE.search(prefix)
    if not start:
        return normalize_signature(prefix.rstrip(":= \n"))
    return normalize_signature(prefix[start.start() : len(prefix) - 2])


def context_signatures(text: str) -> dict[str, str]:
    """Every ``theorem NAME <sig> :=`` in a Context.lean, keyed by full declaration name."""
    out: dict[str, str] = {}
    for m in _CONTEXT_DECL_RE.finditer(text):
        name = m.group("name")
        out[name] = normalize_signature("theorem " + name + m.group("sig"))
    return out


def signature_hash(sig: str) -> str:
    return schemas.content_hash(sig.encode("utf-8"))


def classify(
    constants: list[dict[str, object]], *, own: str, declared: list[str]
) -> tuple[set[str], list[dict[str, str]]]:
    """R4/R5: the nodes a proof draws on, and every constant of undeclared or unknown origin."""
    used_nodes: set[str] = set()
    offences: list[dict[str, str]] = []
    for c in constants:
        name, module = str(c.get("name")), c.get("module")
        if module is None:
            continue  # declared in the submission itself (R4)
        kind, node_id = layout.module_origin(str(module))
        if kind in ("library", "defs") or (kind == "node" and node_id == own):
            continue
        if kind == "node" and node_id is not None:
            used_nodes.add(node_id)
            if node_id not in declared:
                offences.append({"constant": name, "module": str(module), "node": node_id})
            continue
        offences.append({"constant": name, "module": str(module), "node": "?"})
    return used_nodes, offences


class DepsStep:
    number = 8
    name = "deps"

    def run(self, ctx: RunContext) -> StepResult:  # noqa: PLR0911 — one return per rule
        node = ctx.node
        tc: ResolvedToolchain | None = ctx.data.get("toolchain")
        if node is None or tc is None:
            return StepResult.failed("step-order", "step 8 needs steps 1 and 2 to have passed")
        raw_deps = node.meta.get("deps")
        declared = [str(d) for d in raw_deps] if isinstance(raw_deps, list) else []

        context_problem = self._check_context(node, declared)
        if context_problem is not None:
            return context_problem

        staged = ctx.data.get("staged")
        proof = (
            staged.node_dir(node.node_id) / "Proof.lean" if staged is not None else node.proof_path
        )
        req = UsedConstantsRequest(
            file=proof,
            module=layout.node_module(node.node_id, PROOF_MODULE),
            decl=node.statement.decl_name,
        )
        try:
            result = ctx.toolchain.used_constants(
                tc, req, [ctx.build_dir], timeout_s=ctx.wallclock_s
            )
        except subprocess.TimeoutExpired:
            return StepResult.failed(
                "timeout", f"step 8 exceeded the {ctx.wallclock_s:g}s wall-clock cap"
            )
        if not result.ok and not result.doc:
            return metaprogram_failure(self.number, result)
        if not result.ok:
            return StepResult.failed(
                "deps-unreadable",
                result.error or "could not determine the proof's dependencies",
                messages=[m.as_dict() for m in result.messages],
            )

        used_nodes, offences = classify(
            result.doc.get("constants") or [], own=node.node_id, declared=declared
        )
        unused = [d for d in declared if d not in used_nodes]
        ctx.data["deps"] = {
            "declared": declared,
            "used": sorted(used_nodes),
            "unused": unused,
            "warnings": [
                f"declared dep {d!r} contributes no constant to the proof" for d in unused
            ],
        }
        if offences:
            first = offences[0]
            return StepResult.failed(
                "undeclared-dependency",
                f"the proof depends on {first['constant']} from {first['module']} "
                f"(node {first['node']}), which META.yaml does not declare",
                offences=offences,
                declared=declared,
            )
        for warning in ctx.data["deps"]["warnings"]:
            log.warning("step 8: %s", warning)
        return StepResult.passed()

    def _check_context(self, node: layout.Node, declared: list[str]) -> StepResult | None:
        """R6: Context.lean's signature for each dep hash-equals the dep's Statement.lean."""
        context_path = node.path / "Context.lean"
        present = context_signatures(context_path.read_text(encoding="utf-8"))
        for dep in declared:
            dep_dir: Path = node.path.parent / dep
            parsed = layout.parse_statement((dep_dir / "Statement.lean").read_text("utf-8"))
            if not isinstance(parsed, layout.Statement):
                return StepResult.failed("dep-statement", f"dep {dep!r}: {parsed.message}", dep=dep)
            expected = statement_signature(parsed)
            actual = present.get(parsed.decl_name)
            if actual is None:
                return StepResult.failed(
                    "context-missing-dep",
                    f"Context.lean has no signature for dep {dep!r} ({parsed.decl_name}); "
                    "Context.lean is not a submission path (D-3), so this is a graph defect",
                    dep=dep,
                    decl=parsed.decl_name,
                )
            if signature_hash(actual) != signature_hash(expected):
                return StepResult.failed(
                    "context-signature-mismatch",
                    f"Context.lean's signature for dep {dep!r} differs from its Statement.lean; "
                    "Context.lean is not a submission path (D-3), so this is a graph defect",
                    dep=dep,
                    context_hash=signature_hash(actual),
                    statement_hash=signature_hash(expected),
                )
        return None
