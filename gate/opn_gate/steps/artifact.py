"""D-12's five resolution artifacts, and what the gate demands of each (F07-R4, R5).

Until F07 a submission was a proof: ``Proof.lean`` is ``Statement.lean`` with the ``sorry``
replaced (F00-R19), and step 2's textual check is the whole shape rule. D-12's other four
artifacts declare something else, so step 2 needs a second shape rule, and it is a *type* rule
rather than a textual one:

===============  ===========================  ============================================
artifact         declares                     the gate checks
===============  ===========================  ============================================
proof            ``<decl> : S``               F00-R19, textually
counterexample   ``<decl>_refuted : ¬ S``     the declared type against ``¬ S``
vacuity          ``<decl>_vacuous : ¬ W``     against the negation of F01's witness type
partial          ``<decl> : S``, holes open   the type, and the holes, against D-12's offload rule
reduction        as a partial with one hole   the same; the count is what makes it a reduction
===============  ===========================  ============================================

**Which artifact this is comes from the file, not from the submitter.** The declared name says
it: a proof keeps the statement's name, a counterexample adds ``_refuted``, a vacuity certificate
adds ``_vacuous``. The ``opn-submission`` block declares the same thing, but the block is not
evidentiary (F07-Q9) and a submitter who mislabels would otherwise choose which checks run.

The type work itself is the Lake package's ``opn-artifact-type``; everything here is the decision
taken on what it reports.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from opn_gate import layout
from opn_gate.diagnostic import Diagnostic
from opn_gate.steps.base import RunContext, StepResult
from opn_gate.toolchain import ArtifactRequest, MetaprogramResult, ResolvedToolchain

Kind = Literal["proof", "counterexample", "vacuity", "partial", "reduction"]

#: The suffix each non-proof artifact adds to the statement's declaration name (R4).
REFUTED_SUFFIX = "_refuted"
VACUOUS_SUFFIX = "_vacuous"

#: F07 §6: beyond this a partial is a decomposition dump, not a decomposition.
MAX_HOLES = 20

#: Kinds whose file is the node's ``Proof.lean``; ``partial`` lives under ``attempts/`` (D-12 #5).
PROOF_FILE_KINDS: tuple[Kind, ...] = ("proof", "counterexample", "vacuity")


@dataclass(frozen=True)
class Hole:
    """One ``have``-bound hole in a partial proof — a candidate child node (D-29, F07-R6)."""

    name: str
    type: str
    #: The same obligation closed over the binders it sat under — what a child node's
    #: ``Statement.lean`` declares, because a hole's own type is rarely a closed proposition.
    closed_type: str
    defeq_goal: bool

    @classmethod
    def of(cls, doc: dict[str, Any]) -> Hole:
        local = str(doc.get("type", ""))
        return cls(
            name=str(doc.get("name", "")),
            type=local,
            closed_type=str(doc.get("closed_type") or local),
            defeq_goal=bool(doc.get("defeq_goal")),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "closed_type": self.closed_type,
            "defeq_goal": self.defeq_goal,
        }


@dataclass(frozen=True)
class Artifact:
    """What ``opn-artifact-type`` reported, as data the rest of the gate reads."""

    kind: Kind
    decl: str
    expected: str
    declared: str
    matches: bool
    holes: tuple[Hole, ...] = ()
    unnamed: int = 0
    body_is_hole: bool = False
    axioms: tuple[str, ...] = ()

    @classmethod
    def of(cls, kind: Kind, doc: dict[str, Any]) -> Artifact:
        return cls(
            kind=kind,
            decl=str(doc.get("decl", "")),
            expected=str(doc.get("expected", "")),
            declared=str(doc.get("declared", "")),
            matches=bool(doc.get("matches")),
            holes=tuple(Hole.of(h) for h in doc.get("holes") or [] if isinstance(h, dict)),
            unnamed=int(doc.get("unnamed") or 0),
            body_is_hole=bool(doc.get("body_is_hole")),
            axioms=tuple(str(a) for a in doc.get("axioms") or []),
        )

    @property
    def is_reduction(self) -> bool:
        """Q1: a reduction is a partial with exactly one hole; one code path serves both."""
        return self.kind in ("partial", "reduction") and len(self.holes) == 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "decl": self.decl,
            "expected": self.expected,
            "declared": self.declared,
            "matches": self.matches,
            "holes": [h.as_dict() for h in self.holes],
            "unnamed": self.unnamed,
            "body_is_hole": self.body_is_hole,
            "reduction": self.is_reduction,
        }


# --- which artifact is this? --------------------------------------------------------------------


def expected_decl(kind: Kind, statement_decl: str) -> str:
    """R4: the name each artifact must declare, derived from the statement's."""
    if kind == "counterexample":
        return statement_decl + REFUTED_SUFFIX
    if kind == "vacuity":
        return statement_decl + VACUOUS_SUFFIX
    return statement_decl


def kind_of(statement_decl: str, declared: str) -> Kind | None:
    """The artifact a ``Proof.lean`` declaring ``declared`` is, or ``None`` if it is none of them.

    Only the three proof-file kinds are reachable here: a partial never touches ``Proof.lean``
    (D-12 #5), so its mode is decided by the path instead (``opn_gate.modes``).
    """
    for kind in PROOF_FILE_KINDS:
        if declared == expected_decl(kind, statement_decl):
            return kind
    return None


def declared_kind(statement_decl: str, proof_text: str) -> tuple[Kind | None, Diagnostic | None]:
    """Read ``Proof.lean``'s own declaration and say which artifact it is (R4)."""
    parsed = layout.parse_declaration(proof_text, "Proof.lean")
    if isinstance(parsed, Diagnostic):
        return None, parsed
    kind = kind_of(statement_decl, parsed)
    if kind is None:
        permitted = ", ".join(expected_decl(k, statement_decl) for k in PROOF_FILE_KINDS)
        return None, Diagnostic(
            "artifact-decl-unknown",
            f"Proof.lean declares {parsed}; a submission declares one of: {permitted} "
            "(D-12: a proof, a counterexample, or a vacuity certificate)",
            {"declared": parsed, "permitted": permitted},
        )
    return kind, None


# --- what the report has to say -------------------------------------------------------------------


def check(artifact: Artifact, *, max_holes: int = MAX_HOLES) -> list[Diagnostic]:
    """R4, R5: every reason this artifact is not what it claims to be."""
    problems: list[Diagnostic] = []
    if not artifact.matches:
        problems.append(
            Diagnostic(
                "artifact-type-mismatch",
                f"{artifact.decl} has type {artifact.declared}, but a {artifact.kind} of this "
                f"node must have type {artifact.expected}",
                {
                    "kind": artifact.kind,
                    "expected": artifact.expected,
                    "declared": artifact.declared,
                },
            )
        )
    if artifact.kind in PROOF_FILE_KINDS:
        return problems
    problems.extend(_partial_problems(artifact, max_holes))
    return problems


def _partial_problems(artifact: Artifact, max_holes: int) -> list[Diagnostic]:
    """D-12's offload rule and the rest of what a partial has to be (R5)."""
    problems: list[Diagnostic] = []
    if artifact.body_is_hole:
        problems.append(
            Diagnostic(
                "offload-whole-goal",
                "the assembly is a single hole: nothing has been decomposed (D-12 offload rule)",
                {},
            )
        )
    restated = [h for h in artifact.holes if h.defeq_goal]
    if restated:
        problems.append(
            Diagnostic(
                "offload-restated-goal",
                "a hole is the node's own goal under a new name: "
                + ", ".join(f"{h.name} : {h.type}" for h in restated)
                + " (D-12 offload rule)",
                {"holes": [h.name for h in restated]},
            )
        )
    if artifact.unnamed:
        problems.append(
            Diagnostic(
                "hole-unnamed",
                f"{artifact.unnamed} sorry(s) are not bound by a `have`, so they name no child "
                "node; every hole in a partial is `have <name> : <type> := sorry`",
                {"unnamed": artifact.unnamed},
            )
        )
    if not artifact.holes and not artifact.body_is_hole:
        problems.append(
            Diagnostic(
                "partial-without-holes",
                "a partial proof has at least one hole; a proof with none is a proof (D-12)",
                {},
            )
        )
    if len(artifact.holes) > max_holes:
        problems.append(
            Diagnostic(
                "too-many-holes",
                f"{len(artifact.holes)} holes; a partial carries at most {max_holes} before it "
                "is a decomposition dump rather than a decomposition",
                {"holes": len(artifact.holes), "cap": max_holes},
            )
        )
    return problems


# --- running it ----------------------------------------------------------------------------------


def request(
    ctx: RunContext, kind: Kind, *, node_dir: Path, artifact: Path, artifact_module: str
) -> ArtifactRequest:
    node = ctx.node
    assert node is not None
    return ArtifactRequest(
        statement=node_dir / "Statement.lean",
        statement_module=layout.node_module(node.node_id, "Statement"),
        decl=node.statement.decl_name,
        artifact=artifact,
        artifact_module=artifact_module,
        artifact_decl=expected_decl(kind, node.statement.decl_name),
        kind=kind,
    )


def run(
    ctx: RunContext, tc: ResolvedToolchain, req: ArtifactRequest, kind: Kind
) -> tuple[Artifact | None, StepResult | None]:
    """Call the metaprogram and turn its answer into an ``Artifact`` or a step failure."""
    try:
        result = ctx.toolchain.artifact_type(tc, req, [ctx.build_dir], timeout_s=ctx.wallclock_s)
    except subprocess.TimeoutExpired:
        return None, StepResult.failed(
            "timeout", f"the artifact-type check exceeded the {ctx.wallclock_s:g}s cap"
        )
    failure = _metaprogram_failure(result)
    if failure is not None:
        return None, failure
    artifact = Artifact.of(kind, result.doc)
    problems = check(artifact)
    ctx.data["artifact"] = artifact.as_dict()
    if problems:
        first = problems[0]
        return artifact, StepResult.failed(
            first.code,
            first.message,
            **first.details,
            problems=[d.message for d in problems],
        )
    return artifact, None


def _metaprogram_failure(result: MetaprogramResult) -> StepResult | None:
    if result.ok:
        return None
    if not result.doc:
        return StepResult.failed(
            "metaprogram-failed",
            f"opn-artifact-type exited {result.exit_code} without a JSON verdict",
            exit_code=result.exit_code,
            output=result.output,
        )
    return StepResult.failed(
        "artifact-elaboration",
        result.error or "the artifact does not elaborate",
        messages=[m.as_dict() for m in result.messages],
    )
