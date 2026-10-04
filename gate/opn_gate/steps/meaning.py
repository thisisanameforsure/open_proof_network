"""Step 4's meaning guard: an artifact that claims the statement proved it as the statement's own
files read it (F08-R17; D-4, v3.25; F08-T28).

An artifact's file repeats the statement's text, and it is elaborated in the environment the
build gives it, which is larger than the statement's: its use lines, and the merged proofs of
the nodes it rests on, which the build stages as their ``Proof`` modules (F01-Q4). The same text
can elaborate to a different term there: an imported module may add an instance that wins
resolution, a notation or macro that rewrites an operator, or a name an ``open`` now resolves to.
Lean would then accept a proof of *that* term under the statement's name, and every later step
would agree with it.

So the gate builds the statement the way admission did (``steps.hazards.StatementStep``): the
target's definitions, the node's own ``Context.lean`` — the signatures D-3 gives it, not the
merged proofs the build stages in its place — and ``Statement.lean`` under its own header, all in
a build of their own beside the artifact's. It then asks ``opn-statement-meaning`` whether the
declaration the artifact's module holds has the statement module's type, in the artifact's
environment, by the kernel's definitional equality. Nothing is elaborated a second time in that
program: both types are read from compiled modules, so the comparison cannot itself be bent by
what the extra imports do to elaboration.

The statement's build lives in its own directory (``MEANING_DIR``), so the kernel replay sees
exactly the modules it did before.

**Which artifacts are guarded (F08-T28, Q36).** Every artifact that declares the statement's own
theorem: a proof, an alternate (D-25) and a partial's assembly (D-12 #5). T23 asked only when the
artifact declared a use and T25 (R22) when a use stood anywhere in the staged closure, which left
the oldest road open: step 2 accepts a ``Proof.lean`` with a further command after its body, so a
dependency's merged proof can carry an instance or a macro into every proof built on it with no
use line anywhere. For a plain proof nothing else compares types (``artifact.judge`` passes it on
its text), so without this the verdict that it proves the statement rested on its text alone.
A counterexample or a vacuity certificate declares another theorem, whose type
``opn-artifact-type`` checks; it is asked only when a use stands in its closure, as before (and
is then refused, since its module does not declare the statement's theorem).

**What it costs.** One more build of the target's definitions, the node's ``Context`` and its
``Statement`` per gate run, and one metaprogram that imports the artifact's module: on a Mathlib
target, three more imports of Mathlib's environment.

``carried`` still names the use lines beneath the artifact, for the reader of a refusal.
"""

from __future__ import annotations

import shutil

from opn_gate import defs, layout, uses
from opn_gate.steps import artifact
from opn_gate.steps import stage as staging
from opn_gate.steps.base import RunContext, StepResult
from opn_gate.toolchain import MeaningRequest, ResolvedToolchain, module_output_path

STATEMENT_MODULE = "Statement"
CONTEXT_MODULE = "Context"
#: Under the work directory: the statement's own build, apart from the artifact's.
MEANING_DIR = "meaning"
#: ``ctx.data`` key: what the guard found, for the verdict's reader.
MEANING_KEY = "statement_meaning"


def carried(own: str, staged: staging.Staged) -> dict[str, list[str]]:
    """The use lines of every *other* proof staged for this build: node id -> the modules its
    merged ``Proof.lean`` declares (R22). Each is an import of a module the artifact's Context,
    or one of its own uses, brings in, so each is in the artifact's environment. Read from the
    staged copies, which are the files the build compiles."""
    found: dict[str, list[str]] = {}
    for node_id in staged.order:
        if node_id == own:
            continue
        statement = staged.node_dir(node_id) / "Statement.lean"
        proof = staged.node_dir(node_id) / "Proof.lean"
        if not statement.is_file() or not proof.is_file():
            continue
        parsed = layout.parse_statement(statement.read_text(encoding="utf-8"))
        if not isinstance(parsed, layout.Statement):
            continue
        modules = uses.declared(parsed, proof.read_text(encoding="utf-8"), node_id).modules
        if modules:
            found[node_id] = list(modules)
    return dict(sorted(found.items()))


def claims_statement(node_id: str, decl: str, staged: staging.Staged) -> bool:
    """Whether the artifact staged as the node's ``Proof`` module declares the statement's own
    theorem (T28): a proof, an alternate, or a partial's assembly, which is staged in the proof's
    place. Read from the staged file, the one the build compiled."""
    proof = staged.node_dir(node_id) / "Proof.lean"
    if not proof.is_file():
        return False
    kind, _problem = artifact.declared_kind(decl, proof.read_text(encoding="utf-8"))
    return kind == "proof"


def guard(  # noqa: PLR0911 — one return per way the comparison can end
    ctx: RunContext, tc: ResolvedToolchain, staged: staging.Staged
) -> StepResult | None:
    """The refusal, or ``None`` when the artifact proved the statement as stated, or when it is
    a counterexample or a vacuity certificate with no use in its closure (T28). Called once the
    node's own modules are built and before they are replayed."""
    declared = ctx.data.get(uses.USES_KEY)
    node = ctx.node
    if node is None:
        return None
    below = carried(node.node_id, staged)
    claims = claims_statement(node.node_id, node.statement.decl_name, staged)
    if not claims and not declared and not below:
        return None
    work = ctx.workdir / MEANING_DIR
    src, build = work / "src", work / "build"
    dest = src / layout.NODES_PREFIX / node.node_id
    dest.mkdir(parents=True, exist_ok=True)
    for stem in (CONTEXT_MODULE, STATEMENT_MODULE):
        shutil.copy(node.path / f"{stem}.lean", dest / f"{stem}.lean")
    target_dir = layout.gate_spec_path(ctx.graph_root, ctx.claim.target_id).parent
    problem = defs.compile_all(ctx.toolchain, tc, target_dir, work, timeout_s=ctx.wallclock_s)
    if problem is not None:
        return StepResult(ok=False, diagnostic=problem)
    for stem in (CONTEXT_MODULE, STATEMENT_MODULE):
        module = layout.node_module(node.node_id, stem)
        elab = ctx.toolchain.elaborate(
            tc, dest / f"{stem}.lean", module, build, root=src, timeout_s=ctx.wallclock_s
        )
        if not elab.ok:
            return StepResult.failed(
                "elaboration-failed",
                f"{module} does not elaborate from the node's own files, so the statement's "
                "meaning cannot be compared with what the artifact proved (F08-R17)",
                module=module,
                node=node.node_id,
                messages=[m.as_dict() for m in elab.errors or elab.messages],
                stderr=elab.stderr,
            )
    req = MeaningRequest(
        statement_olean=build
        / module_output_path(layout.node_module(node.node_id, STATEMENT_MODULE), ".olean"),
        decl=node.statement.decl_name,
        artifact_module=layout.node_module(node.node_id, "Proof"),
        artifact_decl=node.statement.decl_name,
    )
    result = ctx.toolchain.statement_meaning(tc, req, [staged.build], timeout_s=ctx.wallclock_s)
    if not result.ok and not result.doc:
        return StepResult.failed(
            "metaprogram-failed",
            f"opn-statement-meaning exited {result.exit_code} without a JSON verdict",
            exit_code=result.exit_code,
            output=result.output,
        )
    if not result.ok:
        return StepResult.failed(
            "statement-meaning-unreadable",
            result.error or "the statement's type could not be compared with the artifact's",
            messages=[m.as_dict() for m in result.messages],
        )
    doc = result.doc
    ctx.data[MEANING_KEY] = {
        "identical": bool(doc.get("identical")),
        "matches": bool(doc.get("matches")),
    }
    if below:
        ctx.data[MEANING_KEY]["carried"] = below
    if doc.get("matches"):
        return None
    mismatch = [str(n) for n in doc.get("local_mismatch") or []]
    return StepResult.failed(
        "statement-meaning-changed",
        "in the environment its use lines and the proofs it is built on give it, the artifact's "
        "text states a different proposition from the one the node's own files state"
        + (
            f" (a declaration of the statement's own file differs there: {', '.join(mismatch)})"
            if mismatch
            else ""
        )
        + ". A use may add names to prove with; it may not add an instance, a notation or a "
        "name that changes what the statement's text elaborates to (F08-R17)"
        + (
            ". Uses declared by proofs this one is built on are in its environment too: "
            + "; ".join(f"{dep} declares {', '.join(mods)}" for dep, mods in below.items())
            + " (F08-R22)"
            if below
            else ""
        ),
        expected=str(doc.get("expected", "")),
        declared=str(doc.get("declared", "")),
        local_mismatch=mismatch,
        uses=list(declared.get("modules") or []) if isinstance(declared, dict) else [],
        carried=below,
    )
