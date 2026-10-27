"""The verdict on a pair proof (F26-R8, F26-T17; D-9 v3.39): one function the three layers share.

A pair-proof record (``pair-proof/v1``) carries a whole Lean file, the gate's template for one open
direction of a review pair (``pair_proofs.template``) with its two regions filled. Three layers
judge that file the same way: the service's pre-flight before any pull request opens, the gate in
the step-3 sandbox before the merge (``opn-gate pair-proofs``), and the review job after the merge.
``verdict`` is the judgment; each layer brings the toolchain it holds.

**What it asks, in order** (the first refusal is the answer):

1. ``static``: the file equals the template byte for byte outside the two regions
   (``pair-proof-template-mismatch``) and the regions keep their rules (``pair-proof-forbidden``).
   No toolchain runs for a file that fails here.
2. The gate's own unfilled template is compiled (the *reference*): the candidates and the
   theorem the direction asks, with the placeholder proof. It is the gate's text, so a failure is
   the gate's, never the contributor's (``pair-proof-unchecked``).
3. The filled file is compiled in a call whose only writable directory is its own compile area
   (``judging.compile_contributed``): an error is ``pair-proof-elaboration``, a ``sorry`` warning
   ``pair-proof-sorry``.
4. The module's olean, copied by name out of that area into one the compile never wrote, is
   replayed through the kernel (``pair-proof-replay``): ``--fresh`` on a core-Lean pin, against its
   imports on a Mathlib pin, as step 4 replays a proof (``steps.replay``).
5. Its theorem and every candidate declaration the theorem's type reaches are compared with the
   reference's by ``opn-statement-meaning`` (F08-T28), so code in a region cannot change what the
   gate-written text compiled to (``pair-proof-meaning``).
6. Its axioms are read by ``opn-axioms`` (F02-T11: the module read with initializers off, the
   verdict one nonce-tagged line), and must be among ``propext``, ``Classical.choice`` and
   ``Quot.sound``: ``sorryAx`` is ``pair-proof-sorry``, anything else (``native_decide``'s
   ``Lean.ofReduceBool`` included) ``pair-proof-axiom``.
7. For a proof, the guarded copy (``pair_proofs.guarded``: the hypothesis cleared right after the
   gate's ``intro``) is compiled the same way. If it elaborates with no error and no ``sorry``, the
   proof never used its hypothesis and the verdict is ``pair-proof-degenerate``, in the job's own
   words (``review_pairs.GUARD_TOOL``). A guarded copy that fails, times out or needs ``sorry`` did
   not prove, so the proof stands, as the job reads its own guard. A refutation has no guard.

Steps 4 to 6 are F02-T10's judging workspace reused, not a second one: the replay, the comparison
and the axioms query each mount the module's directory, the reference's and the graph modules'
read-only and nothing writable. A timeout, a memory kill or a toolchain failure anywhere decides
nothing and is ``pair-proof-unchecked`` (C7: a check that could not run refuses).

``graph_build`` is a directory of the graph modules the candidates import (``Defs.*``), built
from the graph by the caller (``review_lean.graph_sources``, F26-Q21); it is on every call's search
path and is copied, never written.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from opn_gate import judging, pair_proofs
from opn_gate.diagnostic import Diagnostic
from opn_gate.pair_proofs import Kind
from opn_gate.review_lean import Cand
from opn_gate.review_pairs import GUARD_TOOL
from opn_gate.toolchain import (
    ElabResult,
    MeaningRequest,
    ResolvedToolchain,
    Toolchain,
    is_native_decide_axiom,
)

#: The axioms a settled direction may rest on: Lean's standard three (D-4 step 5's allowlist).
ALLOWED_AXIOMS: tuple[str, ...] = ("Classical.choice", "Quot.sound", "propext")
SORRY_AXIOM = "sorryAx"
#: The module every text is compiled as: one name for the reference and the filled file, so a
#: private declaration of a candidate is the same constant on both sides of the comparison.
MODULE = "OpnPairProof"
#: The theorem the template declares, by kind.
DECLS: dict[str, str] = {"proof": "opnDirection", "refutation": "opnInstance"}
#: The areas under ``workdir``, one per compile, each with its own judging directory.
REFERENCE, FILLED, GUARD = "reference", "filled", "guard"


@dataclass(frozen=True)
class Verdict:
    """The answer: ``ok``, or the refusal's ``code``, ``reason`` and ``details``. ``axioms`` are
    the theorem's axioms when they were read."""

    ok: bool
    code: str | None = None
    reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    axioms: tuple[str, ...] = ()

    @property
    def diagnostic(self) -> Diagnostic | None:
        """The refusal as a ``Diagnostic``; ``None`` for a pass."""
        if self.ok or self.code is None:
            return None
        return Diagnostic(self.code, self.reason, dict(self.details))

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "code": self.code,
            "reason": self.reason,
            "details": self.details,
            "axioms": list(self.axioms),
        }


def _refused(diagnostic: Diagnostic, axioms: tuple[str, ...] = ()) -> Verdict:
    return Verdict(False, diagnostic.code, diagnostic.message, dict(diagnostic.details), axioms)


# --- the rules, each one function so every layer can apply it to what it holds ------------------


def static(text: str, tmpl: str) -> Diagnostic | None:
    """Step 1: the template match and the region rules; the first refusal, or ``None``."""
    filled = pair_proofs.split(text, tmpl)
    if isinstance(filled, Diagnostic):
        return filled
    found = pair_proofs.problems(filled)
    return found[0] if found else None


def uses_sorry(elab: ElabResult) -> bool:
    """Whether Lean reported a ``sorry`` (``declaration uses 'sorry'``) while elaborating."""
    return any(
        "declaration uses 'sorry'" in m.text or "declaration uses `sorry`" in m.text
        for m in elab.messages
    )


def clean(elab: ElabResult) -> bool:
    """Elaborated with no error and no ``sorry``: what "the file elaborates" means here."""
    return elab.ok and not elab.errors and not uses_sorry(elab)


def elaboration_problem(elab: ElabResult) -> Diagnostic | None:
    """Step 3's refusal for a compile result, or ``None``."""
    if not elab.ok or elab.errors:
        shown = [m.as_dict() for m in (elab.errors or elab.messages)][:10]
        return Diagnostic(
            "pair-proof-elaboration",
            "the filled file does not elaborate"
            + (f": {elab.errors[0].text[:300]}" if elab.errors else ""),
            {"messages": shown, "stderr": elab.stderr[-2000:]},
        )
    if uses_sorry(elab):
        return Diagnostic(
            "pair-proof-sorry",
            "the filled file elaborates only with `sorry`; a settled direction is a whole proof",
            {"messages": [m.as_dict() for m in elab.messages][:10]},
        )
    return None


def axiom_problem(axioms: frozenset[str] | set[str], decl: str) -> Diagnostic | None:
    """Step 6's refusal for the axioms ``decl`` depends on, or ``None``."""
    if SORRY_AXIOM in axioms:
        return Diagnostic(
            "pair-proof-sorry",
            f"{decl} depends on sorryAx; a settled direction is a whole proof",
            {"axioms": sorted(axioms)},
        )
    outside = sorted(a for a in axioms if a not in ALLOWED_AXIOMS)
    if outside:
        native = any(is_native_decide_axiom(a) for a in outside)
        return Diagnostic(
            "pair-proof-axiom",
            f"{decl} depends on axioms outside propext, Classical.choice and Quot.sound: "
            + ", ".join(outside)
            + (" (native_decide trusts the compiler, not the kernel)" if native else ""),
            {"axioms": outside, "allowlist": sorted(ALLOWED_AXIOMS)},
        )
    return None


def degenerate(first: Cand) -> Diagnostic:
    """Step 7's refusal: the job's own words, and what the guard saw."""
    return Diagnostic(
        "pair-proof-degenerate",
        f"{GUARD_TOOL}: the proof still proves with {first.id}'s hypothesis cleared after the "
        "gate's intro, so it never uses it",
        {"guard": "the hypothesis cleared right after the gate's intro (pair_proofs.guarded)"},
    )


def _unchecked(reason: str, **details: Any) -> Diagnostic:
    return Diagnostic(
        "pair-proof-unchecked",
        f"the pair proof could not be checked, so it is not accepted: {reason}",
        details,
    )


# --- the judgment ------------------------------------------------------------------------------


def verdict(  # noqa: PLR0913 — one argument per fact the judgment needs
    toolchain: Toolchain,
    resolved: ResolvedToolchain,
    text: str,
    tmpl: str,
    *,
    first: Cand,
    kind: Kind,
    workdir: Path,
    graph_build: Path | None = None,
    timeout_s: float | None = None,
) -> Verdict:
    """The verdict on ``text``, the filled file, against ``tmpl``, the direction's template
    (``pair_proofs.template`` from the base tree's candidates); ``first`` is the direction's
    first candidate (its intro is the guard's anchor), ``kind`` the record's. ``workdir`` is a
    directory this call may fill, and ``<workdir>.judge`` beside it holds the judging areas
    (``judging.area``); nothing else is written."""
    problem = static(text, tmpl)
    if problem is not None:
        return _refused(problem)
    decl = DECLS[kind]
    trusted = graph_build if graph_build is not None else workdir / "no-graph-modules"
    trusted.mkdir(parents=True, exist_ok=True)
    try:
        return _judge(
            toolchain, resolved, text, tmpl, first, kind, decl, workdir, trusted, timeout_s
        )
    except subprocess.TimeoutExpired as exc:  # sandbox.MemoryExceeded is one
        return _refused(_unchecked(f"a call did not finish ({exc.cmd})", cmd=str(exc.cmd)))
    except (OSError, RuntimeError) as exc:  # the toolchain or docker could not run
        return _refused(_unchecked(str(exc)[:500]))


def _judge(  # noqa: PLR0911, PLR0913, PLR0917 — one return per step; the verdict's inputs
    toolchain: Toolchain,
    resolved: ResolvedToolchain,
    text: str,
    tmpl: str,
    first: Cand,
    kind: Kind,
    decl: str,
    workdir: Path,
    trusted: Path,
    timeout_s: float | None,
) -> Verdict:
    reference_area = judging.area(workdir, REFERENCE)
    ref_elab, ref_olean = judging.compile_contributed(
        toolchain,
        resolved,
        text=tmpl,
        module=MODULE,
        trusted_build=trusted,
        where=reference_area,
        timeout_s=timeout_s,
    )
    if ref_olean is None or ref_elab.errors:
        first_error = next((m.text for m in ref_elab.errors), "") or ref_elab.stderr[-300:]
        return _refused(_unchecked(f"the direction's own template does not build: {first_error}"))

    filled_area = judging.area(workdir, FILLED)
    elab, olean = judging.compile_contributed(
        toolchain,
        resolved,
        text=text,
        module=MODULE,
        trusted_build=trusted,
        where=filled_area,
        timeout_s=timeout_s,
    )
    problem = elaboration_problem(elab)
    if problem is not None:
        return _refused(problem)
    if olean is None:
        return _refused(
            Diagnostic(
                "pair-proof-elaboration",
                "the filled file left no compiled module",
                {"stderr": elab.stderr[-2000:]},
            )
        )
    modules = filled_area / judging.CONTRIBUTED_DIR
    search = [modules, trusted]
    reader = judging.confined(toolchain, read_only=[modules, trusted])

    replayed = reader.kernel_replay(
        resolved, [MODULE], search, fresh=resolved.mathlib_sha is None, timeout_s=timeout_s
    )
    if not replayed.ok:
        return _refused(
            Diagnostic(
                "pair-proof-replay",
                "the kernel replay rejected the filled file's build",
                {"output": replayed.output[-4000:]},
            )
        )

    comparer = judging.confined(toolchain, read_only=[modules, trusted, ref_olean.parent])
    req = MeaningRequest(
        statement_olean=ref_olean, decl=decl, artifact_module=MODULE, artifact_decl=decl
    )
    meant = comparer.statement_meaning(resolved, req, search, timeout_s=timeout_s)
    if not meant.ok or "matches" not in meant.doc:
        return _refused(
            _unchecked(
                meant.error
                or f"opn-statement-meaning answered no verdict (exit {meant.exit_code})",
                output=meant.output[-2000:],
            )
        )
    if not meant.doc.get("matches"):
        mismatch = [str(n) for n in meant.doc.get("local_mismatch") or []]
        return _refused(
            Diagnostic(
                "pair-proof-meaning",
                f"the filled file's {decl} is not the template's: code in a region changed what "
                "the gate-written text compiled to"
                + (f" (a declaration differs: {', '.join(mismatch)})" if mismatch else ""),
                {
                    "expected": str(meant.doc.get("expected", "")),
                    "declared": str(meant.doc.get("declared", "")),
                    "local_mismatch": mismatch,
                },
            )
        )

    read = reader.axioms(
        resolved, MODULE, decl, search, filled_area / "axioms", timeout_s=timeout_s
    )
    if not read.ok:
        return _refused(
            _unchecked(f"the axioms of {decl} could not be read", output=read.output[-2000:])
        )
    axioms = tuple(sorted(read.axioms))
    problem = axiom_problem(read.axioms, decl)
    if problem is not None:
        return _refused(problem, axioms)

    if kind == "proof":
        guard_area = judging.area(workdir, GUARD)
        try:
            g_elab, _ = judging.compile_contributed(
                toolchain,
                resolved,
                text=pair_proofs.guarded(text, first),
                module=MODULE,
                trusted_build=trusted,
                where=guard_area,
                timeout_s=timeout_s,
            )
        except subprocess.TimeoutExpired:
            g_elab = ElabResult(ok=False)  # as the job reads its guard: it did not prove
        if clean(g_elab):
            return _refused(degenerate(first), axioms)
    return Verdict(True, axioms=axioms)
