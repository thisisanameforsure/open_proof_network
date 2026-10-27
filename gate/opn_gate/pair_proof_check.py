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
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml

from opn_gate import judging, pair_proofs, review, review_lean
from opn_gate.diagnostic import Diagnostic
from opn_gate.pair_proofs import Direction, Kind
from opn_gate.paths import REVIEW_DIR
from opn_gate.review_lean import Cand
from opn_gate.review_pairs import GUARD_TOOL
from opn_gate.toolchain import (
    ElabResult,
    MeaningRequest,
    ResolvedToolchain,
    Toolchain,
    is_native_decide_axiom,
)

#: The axioms a settled direction may rest on (``pair_proofs.STANDARD_AXIOMS``); kept under this
#: name too for the verdict's callers.
ALLOWED_AXIOMS: tuple[str, ...] = pair_proofs.STANDARD_AXIOMS
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
    outside = sorted(a for a in axioms if a not in pair_proofs.STANDARD_AXIOMS)
    if outside:
        native = any(is_native_decide_axiom(a) for a in outside)
        return Diagnostic(
            "pair-proof-axiom",
            f"{decl} depends on axioms outside propext, Classical.choice and Quot.sound: "
            + ", ".join(outside)
            + (" (native_decide trusts the compiler, not the kernel)" if native else ""),
            {"axioms": outside, "allowlist": sorted(pair_proofs.STANDARD_AXIOMS)},
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


# --- the record against the tree it is checked on (F26-T17) --------------------------------------


@dataclass(frozen=True)
class Inputs:
    """What a pair-proof record is judged against, read from the tree: the pair's candidates as
    the job prepares them, the direction's first claim, the kind, the template and the text."""

    a: Cand
    b: Cand
    direction: Direction
    kind: Kind
    n: int | None
    tmpl: str
    text: str
    #: the modules the candidates import, for the caller that builds the graph's own (Q21)
    imports: tuple[str, ...]

    @property
    def first(self) -> Cand:
        return pair_proofs.ordered(self.a, self.b, self.direction)[0]


def stamp(date: str) -> str:
    """``YYYY-MM-DDTHH:MM:SSZ`` as the record's file name carries it: ``YYYYMMDDTHHMMSSZ``."""
    return date.replace("-", "").replace(":", "")


def expected_name(doc: Mapping[str, Any]) -> str:
    """The file name the record must have (``pair_proofs.record_name``)."""
    return pair_proofs.record_name(
        str(doc.get("a")),
        str(doc.get("b")),
        doc.get("direction"),  # type: ignore[arg-type]  # validated by the schema first
        stamp(str(doc.get("date"))),
        str(doc.get("author")),
    )


def name_problem(doc: Mapping[str, Any], name: str) -> Diagnostic | None:
    """The record's file name is its own, and its pair is in ``pair/v1``'s order."""
    a, b = str(doc.get("a")), str(doc.get("b"))
    if not a < b:
        return Diagnostic(
            "pair-proof-name",
            f"a names {a!r} and b names {b!r}; a pair names its candidates with the lexically "
            "smaller id first, as pair/v1 does, and `direction` says which way",
            {"a": a, "b": b},
        )
    want = expected_name(doc)
    if name != want:
        return Diagnostic(
            "pair-proof-name",
            f"the record is named {name!r}; a pair-proof record is named for its pair, its "
            f"direction, its date and its author: {want!r}",
            {"name": name, "expected": want},
        )
    return None


def _candidate_records(base: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    out: dict[str, tuple[Path, dict[str, Any]]] = {}
    folder = base / "candidates"
    if not folder.is_dir():
        return out
    for path in sorted(folder.iterdir()):
        if path.suffix not in (".yaml", ".yml"):
            continue
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            continue
        if isinstance(doc, dict) and isinstance(doc.get("id"), str):
            out[doc["id"]] = (path, doc)
    return out


def _latest_pair(base: Path, a: str, b: str) -> dict[str, Any] | None:
    """The pair record in force for ``(a, b)``: the latest, as ``review._pairs`` reads it."""
    return next(
        (p for p in review._pairs(base) if (str(p.get("a")), str(p.get("b"))) == (a, b)),
        None,
    )


def _settled_by(base: Path, doc: Mapping[str, Any], own: str | None) -> str | None:
    """An earlier pair-proof record on the tree for the same direction at the same statement
    hashes, by file name; ``own`` (the record under check, when it is on the tree) is not one,
    and nor is a record the review job's re-check refused (``review.pair_proof_judgments``): it
    settled nothing, and counting it would lock the direction for ever. A record the job has not
    judged yet still counts, since the job may yet accept it."""
    folder = base / pair_proofs.DIR
    if not folder.is_dir():
        return None
    judged = review.pair_proof_judgments(base)
    for path in sorted(folder.iterdir()):
        if path.name == own or path.suffix not in (".yaml", ".yml"):
            continue
        verdict_on = judged.get(path.stem)
        if verdict_on is not None and not verdict_on["accepted"]:
            continue
        try:
            other = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            continue
        if isinstance(other, dict) and all(
            other.get(k) == doc.get(k) for k in ("a", "b", "direction", "statement_hashes")
        ):
            return path.name
    return None


def admissible(  # noqa: PLR0911 — one return per rule
    target_dir: Path, doc: Mapping[str, Any], *, own: str | None = None
) -> Inputs | Diagnostic:
    """F26-T17: whether the tree takes this record, and what it is judged against.

    The review exists; both candidates are on it, their ``candidate/v1`` ``statement_hash`` is
    the record's, and both survive (``review.derive``); the direction is open on the pair record
    in force (``review._pairs``: a later record supersedes); no earlier pair-proof record settles
    the same direction at the same hashes; the kind fits the direction (``pair_proofs.template``,
    which raises when it does not); and the record's Lean is the template with its two regions
    filled (``static``). ``doc`` has validated against ``pair-proof/v1``. The record's own name
    and who it acts for are the caller's (``name_problem``, the gate's ``acting_names``)."""
    head = review.opening(target_dir)
    if head is None:
        return Diagnostic(
            "pair-proof-no-review",
            f"{target_dir.name} has no formalization review (review/review.yaml), so it has no "
            "pair to settle",
            {"target": target_dir.name},
        )
    base = target_dir / REVIEW_DIR
    a_id, b_id = str(doc.get("a")), str(doc.get("b"))
    hashes = doc.get("statement_hashes")
    hashes = hashes if isinstance(hashes, Mapping) else {}
    records = _candidate_records(base)
    sources: dict[str, str] = {}
    for side, cid in (("a", a_id), ("b", b_id)):
        found = records.get(cid)
        lean = (
            found[0].with_name(str(found[1].get("lean_file") or f"{cid}.lean"))
            if found is not None
            else None
        )
        if found is None or lean is None or not lean.is_file():
            return Diagnostic(
                "pair-candidate-unknown",
                f"{side} names {cid!r}, which is not a candidate of {target_dir.name}'s review",
                {"candidate": cid},
            )
        if found[1].get("statement_hash") != hashes.get(side):
            return Diagnostic(
                "pair-candidate-mismatch",
                f"statement_hashes.{side} is not {cid}'s statement_hash: the record must be bound "
                "to the candidate texts on record (read them from list_open_pairs)",
                {
                    "candidate": cid,
                    "expected": found[1].get("statement_hash"),
                    "got": hashes.get(side),
                },
            )
        sources[cid] = lean.read_text(encoding="utf-8")
    fates = {c["id"]: c["status"] for c in review.derive(target_dir)["candidates"]}
    for cid in (a_id, b_id):
        if fates.get(cid) != review.SURVIVING:
            return Diagnostic(
                "pair-candidate-not-surviving",
                f"{cid} is {fates.get(cid, 'unknown')}, and only a pair of surviving candidates "
                "has directions to settle",
                {"candidate": cid, "status": fates.get(cid)},
            )
    direction = doc.get("direction")
    pair = _latest_pair(base, a_id, b_id)
    way = pair.get(str(direction)) if pair is not None else None
    state = way.get("state") if isinstance(way, Mapping) else None
    if state != "open":
        return Diagnostic(
            "pair-not-open",
            (
                f"the review job has not compared {a_id} and {b_id} yet"
                if pair is None
                else f"the {direction} direction of {a_id} and {b_id} is {state}, not open"
            )
            + "; only an open direction takes a pair proof (F26-R8)",
            {"a": a_id, "b": b_id, "direction": direction, "state": state},
        )
    earlier = _settled_by(base, doc, own)
    if earlier is not None:
        return Diagnostic(
            "pair-proof-settled",
            f"{earlier} already settles the {direction} direction of {a_id} and {b_id} at these "
            "statement hashes; the review job writes the pair from it",
            {"earlier": f"{REVIEW_DIR}/{pair_proofs.DIR}/{earlier}"},
        )
    concepts = [str(x) for x in head.get("concepts") or []]
    cands: dict[str, Cand] = {}
    for cid in (a_id, b_id):
        got = review_lean.prepare(cid, sources[cid], concepts)
        if isinstance(got, str):
            return Diagnostic(
                "pair-proof-kind",
                f"{cid} has no claim the review compares ({got}), so no direction of it can be "
                "settled here",
                {"candidate": cid},
            )
        cands[cid] = got
    kind = doc.get("kind")
    case = doc.get("case")
    n = case.get("n") if isinstance(case, Mapping) else None
    try:
        tmpl = pair_proofs.template(cands[a_id], cands[b_id], direction, kind, n)  # type: ignore[arg-type]
    except ValueError as exc:
        return Diagnostic(
            "pair-proof-kind",
            f"the {direction} direction cannot take a {kind} here: {exc}",
            {"direction": direction, "kind": kind, "case": case},
        )
    text = str(doc.get("lean"))
    problem = static(text, tmpl)
    if problem is not None:
        return problem
    imports = tuple(sorted({*cands[a_id].imports, *cands[b_id].imports}))
    # ``template`` accepted both, so each is one of its literals
    return Inputs(
        cands[a_id],
        cands[b_id],
        cast(Direction, direction),
        cast(Kind, kind),
        n,
        tmpl,
        text,
        imports,
    )
