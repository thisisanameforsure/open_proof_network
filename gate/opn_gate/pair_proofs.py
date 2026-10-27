"""A contributor's settlement of one open pair direction (F26-R8, F26-T16; D-9 v3.39).

The review job compares every two surviving candidates in each direction and leaves open what its
own tactics could not settle (``review_pairs``). R8 makes an open direction claimable work: anyone
may prove it, or refute it at an instance, and the work is checked and credited. This module is the
one place the *text* of such a settlement is defined, so the service's pre-flight, the gate's
pre-merge check and the job's post-merge re-check all judge the same file the same way.

**The template** (``template``). The gate writes the whole file except two regions: the two
candidates in their namespaces exactly as the job elaborates them (``review_lean.module``), then a
helper region, then the theorem the direction asks, whose statement the contributor never writes:

- a proof: ``theorem opnDirection : <first> → <second>`` (``∀ n, …`` when the claims are
  indexed), opened by the gate's own ``intro``; the contributor's tactics follow it;
- a refutation (indexed claims only): ``theorem opnInstance : <first> n ∧ ¬ <second> n`` at the
  contributor's ``n``, the job's own refuting instance (``review_lean.instance_text``) with any
  proof in place of ``decide +kernel``. A closed claim has no instance, and a proof that the two
  statements differ would settle the conjecture, so a closed direction cannot be refuted here.

The file starts with the job's ``-- opn-review:`` header, so an exhibit made from it names its case
(``review_lean.case_of``) and a refutation raises its question like the job's own.

**Filling it** (``split``). The filled file must equal the template byte for byte outside the
helper region (between the two ``-- opn-pair-proof: helpers`` lines) and the proof region
(everything after the ``-- opn-pair-proof: proof begins`` line). ``problems`` then holds the
helpers to F00-T11's helper rule (``paths.helper_problem``: private theorem, lemma, def or abbrev,
nothing that sets an option or adds to the environment) and the proof to an indented tactic block
with no ``sorry``, ``admit``, ``set_option`` or ``native_decide``; a line at column 0 would start a
new command after the theorem, so none is allowed.

**The degenerate guard** (``guarded``). As the job does (``review_pairs.attempt``), a proof is
elaborated a second time with its hypothesis cleared right after the gate's ``intro``. If that still
proves, the proof never used the hypothesis and is refused as a proof of the direction. A
refutation has no hypothesis and no guard.

What this module does not do: elaborate anything, or judge axioms. Those belong to whoever holds a
toolchain (the hosted check before the pull request, the sandbox before the merge, the job after).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from opn_gate import layout, paths
from opn_gate.diagnostic import Diagnostic
from opn_gate.review_lean import HEADER, Cand, Case, claim_expr, module, ns

Direction = Literal["forward", "backward"]
Kind = Literal["proof", "refutation"]

DIRECTIONS: tuple[Direction, ...] = ("forward", "backward")
KINDS: tuple[Kind, ...] = ("proof", "refutation")
#: The directory under ``targets/<id>/review/`` the records live in (``paths.REVIEW_ROLES_BY_DIR``).
DIR = "pair-proofs"
#: The heartbeat cap the theorem is elaborated under: the gate's own (F00-T11), written by the
#: template so a contributor never sets an option.
MAX_HEARTBEATS = 1_000_000

HELPERS_BEGIN = (
    "-- opn-pair-proof: helpers begin (private theorem, lemma, def or abbrev declarations only)"
)
HELPERS_END = "-- opn-pair-proof: helpers end"
PROOF_BEGINS = "-- opn-pair-proof: proof begins (an indented tactic block, to the end of the file)"
#: What the template's proof region holds before it is filled: it elaborates, with a warning.
PLACEHOLDER = "  sorry\n"
#: The axioms a settled direction may rest on, and nothing else: Lean's standard three (D-4 step
#: 5's allowlist). An allowlist, never a blocklist: at Lean 4.33.1 ``native_decide`` adds an
#: auxiliary axiom of its own per use (``<decl>._native.native_decide.ax_1_1``), not
#: ``Lean.ofReduceBool``. One definition for the service, the gate and the job (F26-T17, T19).
STANDARD_AXIOMS: tuple[str, ...] = ("Classical.choice", "Quot.sound", "propext")
#: Words the proof region may not hold (comments and strings masked first).
PROOF_FORBIDDEN = ("sorry", "admit", "set_option", "native_decide")


@dataclass(frozen=True)
class Filled:
    """A filled template, cut into its two contributor regions."""

    helpers: str
    proof: str
    #: 1-based line of the helper region's first line in the filled file.
    helpers_line: int
    #: 1-based line of the proof region's first line in the filled file.
    proof_line: int


def ordered(a: Cand, b: Cand, direction: Direction) -> tuple[Cand, Cand]:
    """The direction's first and second claim: ``forward`` is ``a → b`` with ``a`` the pair's
    lexically smaller id, as ``pair/v1`` names them."""
    return (a, b) if direction == "forward" else (b, a)


def refutable(first: Cand, second: Cand) -> str | None:
    """Why the direction cannot be refuted at an instance, or ``None`` when it can."""
    if not (first.indexed and second.indexed):
        return (
            "a refutation is an instance at a natural number n, and only indexed claims have one; "
            "a proof that two closed claims differ would settle the conjecture"
        )
    return None


def provable(first: Cand, second: Cand) -> str | None:
    """Why the job's own comparison does not apply to the direction, or ``None`` when it does."""
    if first.shape != second.shape or first.shape == "other":
        return (
            f"the claims' shapes differ or are not ones the review compares ({first.shape}, "
            f"{second.shape})"
        )
    return None


def header(a_id: str, b_id: str, direction: Direction, kind: Kind, case: Case | None) -> str:
    """The file's ``-- opn-review:`` line."""
    op: dict[str, Any] = {
        "op": "pair-proof",
        "a": a_id,
        "b": b_id,
        "direction": direction,
        "kind": kind,
        "case": None if case is None else case.key(),
    }
    return HEADER + json.dumps(op, sort_keys=True, ensure_ascii=False)


def _intro(first: Cand) -> str:
    return "intro n h" if first.indexed else "intro h"


def template(
    a: Cand, b: Cand, direction: Direction, kind: Kind = "proof", n: int | None = None
) -> str:
    """The file a contributor fills for one direction of the pair ``(a, b)``: ``a`` and ``b`` in
    ``pair/v1``'s order, ``n`` the refuting instance when ``kind`` is ``refutation``.

    Raises ``ValueError`` when the direction cannot take that kind (``provable``, ``refutable``),
    or when ``n`` is given for a proof or missing for a refutation."""
    if direction not in DIRECTIONS or kind not in KINDS:
        raise ValueError(f"direction {direction!r} or kind {kind!r} unknown")
    first, second = ordered(a, b, direction)
    case: Case | None = None
    if kind == "proof":
        if n is not None:
            raise ValueError("a proof takes no instance")
        why = provable(first, second)
        if why is not None:
            raise ValueError(why)
        ca, cb = f"{ns(first.id, 'p')}.{first.claim}", f"{ns(second.id, 'p')}.{second.claim}"
        goal = f"∀ n, {ca} n → {cb} n" if first.indexed else f"{ca} → {cb}"
        theorem = f"theorem opnDirection : {goal} := by\n  {_intro(first)}\n"
    else:
        if n is None or isinstance(n, bool) or not isinstance(n, int) or n < 0:
            raise ValueError("a refutation names its instance, a natural number n")
        why = refutable(first, second)
        if why is not None:
            raise ValueError(why)
        case = Case("holds", n)
        theorem = (
            f"theorem opnInstance : {claim_expr(first, 'p', n)} ∧ "
            f"¬ {claim_expr(second, 'p', n)} := by\n"
        )
    lines = [header(a.id, b.id, direction, kind, case)]
    lines += [f"import {m}" for m in sorted({*first.imports, *second.imports})]
    head = "\n".join(lines) + "\n\n"
    body = module(first, "p").rstrip() + "\n\n" + module(second, "p").rstrip() + "\n\n"
    return (
        head
        + body
        + HELPERS_BEGIN
        + "\n"
        + HELPERS_END
        + "\n"
        + f"set_option maxHeartbeats {MAX_HEARTBEATS} in\n"
        + theorem
        + "  "
        + PROOF_BEGINS
        + "\n"
        + PLACEHOLDER
    )


def _parts(tmpl: str) -> tuple[str, str]:
    """The template's fixed text before the helper region and between the two regions."""
    begin = tmpl.index(HELPERS_BEGIN + "\n") + len(HELPERS_BEGIN) + 1
    end = tmpl.index("  " + PROOF_BEGINS + "\n") + len(PROOF_BEGINS) + 3
    return tmpl[:begin], tmpl[begin:end]


def split(text: str, tmpl: str) -> Filled | Diagnostic:
    """``text`` cut into its helper and proof regions, or ``pair-proof-template-mismatch`` naming
    the first line where a byte the gate wrote differs from the template."""
    before, between = _parts(tmpl)
    if not text.startswith(before):
        return _mismatch(text, before, 0)
    rest = text[len(before) :]
    # The helper region ends at the first helpers-end line; from there every byte up to the
    # proof region is the gate's.
    end = 0 if rest.startswith(HELPERS_END + "\n") else rest.find("\n" + HELPERS_END + "\n") + 1
    if end == 0 and not rest.startswith(HELPERS_END + "\n"):
        return _mismatch(text, text[: len(before)] + between, len(before))
    helpers = rest[:end]
    start = len(before) + end
    if not text.startswith(between, start):
        return _mismatch(text, text[:start] + between, start)
    after = text[start + len(between) :]
    helpers_line = before.count("\n") + 1
    proof_line = helpers_line + helpers.count("\n") + between.count("\n")
    return Filled(helpers, after, helpers_line, proof_line)


def _mismatch(text: str, expected: str, start: int) -> Diagnostic:
    i = start
    while i < len(expected) and i < len(text) and text[i] == expected[i]:
        i += 1
    line = text.count("\n", 0, i) + 1
    exp_line = expected[expected.rfind("\n", 0, i) + 1 :].split("\n", 1)[0]
    got_line = text[text.rfind("\n", 0, i) + 1 :].split("\n", 1)[0]
    return Diagnostic(
        "pair-proof-template-mismatch",
        f"line {line} differs from the direction's template: only the helper region and the proof "
        "region are the contributor's, every other byte is the gate's",
        {"line": line, "expected": exp_line, "got": got_line},
    )


def problems(filled: Filled) -> list[Diagnostic]:
    """What the two regions may not hold: F00-T11's helper rule, and for the proof an indented
    tactic block with none of ``PROOF_FORBIDDEN``."""
    out: list[Diagnostic] = []
    if filled.helpers.strip():
        bad = paths.helper_problem(filled.helpers, first_line=filled.helpers_line)
        if bad is not None:
            out.append(
                Diagnostic(
                    "pair-proof-forbidden",
                    bad.message.replace("Proof.lean's helper block", "the helper region"),
                    bad.details,
                )
            )
    if not filled.proof.strip():
        out.append(Diagnostic("pair-proof-forbidden", "the proof region is empty", {}))
        return out
    masked = layout.code_mask(filled.proof)
    for i, (raw, code) in enumerate(zip(filled.proof.split("\n"), masked.split("\n"), strict=True)):
        line = filled.proof_line + i
        if raw.strip() and not raw[:1].isspace():
            out.append(
                Diagnostic(
                    "pair-proof-forbidden",
                    f"line {line} starts at column 0: the proof region is an indented tactic "
                    "block, and a line at column 0 would start a new command",
                    {"line": line, "got": raw},
                )
            )
            break
        for word in PROOF_FORBIDDEN:
            if _word_in(code, word):
                out.append(
                    Diagnostic(
                        "pair-proof-forbidden",
                        f"the proof region may not hold `{word}` (line {line})",
                        {"line": line, "token": word, "got": raw},
                    )
                )
                return out
    return out


def _word_in(code: str, word: str) -> bool:
    start = 0
    while (i := code.find(word, start)) >= 0:
        before = code[i - 1] if i else " "
        after = code[i + len(word)] if i + len(word) < len(code) else " "
        if not (before.isalnum() or before in "_.'") and not (after.isalnum() or after in "_'!?"):
            return True
        start = i + 1
    return False


def guarded(text: str, first: Cand) -> str:
    """The filled proof with its hypothesis cleared right after the gate's ``intro`` (the
    degenerate guard). Only for a proof; the intro line is the template's, so it is found
    exactly once."""
    line = f"\n  {_intro(first)}\n  {PROOF_BEGINS}\n"
    if text.count(line) != 1:
        raise ValueError("not a filled proof template")
    return text.replace(line, f"\n  {_intro(first)}; clear h\n  {PROOF_BEGINS}\n")


def record_name(a_id: str, b_id: str, direction: Direction, stamp: str, author: str) -> str:
    """``<a>--<b>--<direction>--<stamp>-<author>.yaml``; ``stamp`` is ``YYYYMMDDTHHMMSSZ``."""
    return f"{a_id}--{b_id}--{direction}--{stamp}-{author}.yaml"
