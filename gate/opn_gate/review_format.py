"""The formalization review's format rule (F26-R5; D-9 v3.39).

A candidate names each concept the words use as its own predicate, because the intent tests'
``covers`` and ``witness`` probes work by *replacing* that predicate (the concept made empty, the
concept made a small set); a candidate that writes the concept inline gives the probe nothing to
replace, and probing its real claim would discard a correct version — which is what the first
prototype's ``alt-inline`` did (session note 2026-10-09, §9 point 4). So such a candidate is
**returned** to its author with the reason, never discarded (R4): a return is a format verdict, not
a mathematical one, and it is recorded as an ``exhibit/v1`` of kind ``format``.

What the rule reads, and the three decisions it rests on:

1. **The claim.** A candidate's conjecture is its one sorry-bodied ``theorem``/``lemma`` (a
   node's ``Statement.lean`` shape, F00-R19; the type is the claim; a theorem with a proof, such
   as the wrapper's own ``port``, is auxiliary) or, the prototypes' shape, its last
   ``Prop``-valued ``def`` not named for a concept (``def claim (n : Nat) : Prop := …``,
   ``def conj : Prop := …``; the body is the claim). Neither, or two theorems, is returned: there
   is nothing to probe. The spec fixes no shape for a candidate's Lean (R3 says "one Lean
   formalization"), so both are read.
2. **Named.** A concept ``prime`` is named when the candidate declares a ``def``, ``abbrev``,
   ``structure``, ``inductive`` or ``class`` whose last name component is ``prime``, ``isprime``
   (case-insensitive: ``Prime``, ``IsPrime``, ``isPrime`` all count) — the manifest's concepts are
   words and candidates spell them as Lean names — *and* the claim uses that name as a bare token.
   ``Nat.Prime p`` in the claim is Mathlib's notion, not the candidate's own, and the reason says
   so; a declared predicate the claim never uses leaves the probe nothing to replace and is
   returned too. Comments and strings are blanked first (``layout.code_mask``).
3. **The wrapper** (a ported statement). The live or registry statement is the review's first
   candidate and may not meet the rule; the review adds a *second* candidate (``origin: wrapper``)
   that carries the original verbatim as ``def original : Prop``, declares one predicate per
   concept **delegating** to the notion the original used (``def IsPrime := Nat.Prime``: a plain
   ``def`` of the constant, so its type is inferred and the delegation is definitional), restates
   the claim through the predicates as ``def conj``, and proves ``theorem port : conj ↔ original :=
   Iff.rfl`` — the second prototype's hand-written incumbents, generalized. The original's text and
   hash are untouched (§10 point 4). The notion is found in the claim's text: an identifier whose
   last component is the concept (``Nat.Prime``, ``totient`` under ``open Nat``), or one of the
   term-level scoped notations Mathlib gives a single constant (``φ`` for ``Nat.totient``), which
   is an application like any other, so swapping the token is exact. An infix notation (``∧`` for
   ``And``, the divides bar for ``Dvd.dvd``) has no textual rewrite that keeps precedence; rather
   than emit a restatement that may not be the original, the wrapper refuses, naming the concept,
   and the review's opener names the concept another way or writes the wrapper by hand. The port
   line is the detector: a wrong restatement fails there under the toolchain
   (``test_review_format_lean.py``), and T5 compiles every wrapper before it is filed.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from opn_gate import layout, schemas

#: The declarations that can be a concept's predicate.
PREDICATE_KEYWORDS = ("def", "abbrev", "structure", "inductive", "class")
#: The declarations that can be a claim (theorem shape).
THEOREM_KEYWORDS = ("theorem", "lemma")
#: Mathlib's term-level scoped notations for one constant, as the live targets use them: an
#: application ``φ n`` is ``Nat.totient n``, so the token swap keeps the statement. Only
#: notations that stand for a single constant with no argument syntax belong here.
NOTATIONS: dict[str, str] = {
    "φ": "Nat.totient",
    "\u03c3": "ArithmeticFunction.sigma",  # the Greek small sigma, spelled out for the linter
    "μ": "ArithmeticFunction.moebius",
    "Λ": "ArithmeticFunction.vonMangoldt",
    "Ω": "ArithmeticFunction.cardFactors",
    "ω": "ArithmeticFunction.cardDistinctFactors",
}
#: The names the wrapper declares; an original that already declares one cannot be wrapped.
WRAPPER_NAMES = ("original", "conj", "port")

_MODIFIERS = r"(?:@\[[^\]]*\]\s*)?(?:(?:private|protected|noncomputable|unsafe|partial)\s+)*"
_DECL_RE = re.compile(
    rf"^[ \t]*{_MODIFIERS}(?P<kw>def|abbrev|structure|inductive|class|theorem|lemma)"
    r"\s+(?P<name>[^\s:({\[]+)",
    re.M,
)
_IDENT_START = r"(?:[^\W\d]|«)"
_IDENT_RE = re.compile(
    rf"(?<![\w'!?.»]){_IDENT_START}[\w'!?»]*(?:\.{_IDENT_START}[\w'!?»]*)*", re.UNICODE
)
_OPEN, _CLOSE = "([{⦃", ")]}⦄"
_SORRY_BODY_RE = re.compile(r"\s*(?:by\s+)?sorry(?![\w'!?])")


@dataclass(frozen=True)
class Declaration:
    keyword: str
    name: str
    start: int  # offset of the keyword in the text
    end: int  # offset where the next declaration starts (or the text ends)
    header: str  # from after the name to the first top-level ``:=`` or ``where``
    body: str  # after that ``:=``/``where`` to ``end``

    @property
    def last(self) -> str:
        return self.name.rsplit(".", 1)[-1]

    @property
    def is_statement(self) -> bool:
        """A sorry-bodied theorem: a statement, not a proof (``theorem port`` is auxiliary)."""
        return self.keyword in THEOREM_KEYWORDS and _SORRY_BODY_RE.match(self.body) is not None

    @property
    def is_prop_def(self) -> bool:
        return (
            self.keyword in ("def", "abbrev")
            and re.search(r":\s*Prop\s*$", self.header) is not None
        )


def _split_header(text: str) -> tuple[str, str]:
    """``text`` as (header, body) at the first top-level ``:=`` (or ``where``)."""
    depth = 0
    i = 0
    while i < len(text):
        c = text[i]
        if c in _OPEN:
            depth += 1
        elif c in _CLOSE:
            depth -= 1
        elif depth == 0:
            if text.startswith(":=", i):
                return text[:i], text[i + 2 :]
            if re.match(r"\bwhere\b", text[i:]) and (i == 0 or not text[i - 1].isalnum()):
                return text[:i], text[i + 5 :]
        i += 1
    return text, ""


def declarations(lean_text: str) -> list[Declaration]:
    """Every declaration of ``lean_text``, comments and strings blanked, in order. The mask
    keeps every offset (``code_mask``; ``strip_comments`` drops the comment delimiters), so a
    declaration's ``start`` indexes the source text too."""
    masked = layout.code_mask(lean_text)
    found = list(_DECL_RE.finditer(masked))
    out: list[Declaration] = []
    for i, m in enumerate(found):
        end = found[i + 1].start() if i + 1 < len(found) else len(masked)
        header, body = _split_header(masked[m.end() : end])
        out.append(Declaration(m.group("kw"), m.group("name"), m.start(), end, header, body))
    return out


def _concept_names(concept: str) -> tuple[str, str]:
    c = concept.lower()
    return c, f"is{c}"


def _declares(decls: list[Declaration], concept: str) -> Declaration | None:
    accepted = _concept_names(concept)
    for d in decls:
        if d.keyword in PREDICATE_KEYWORDS and d.last.lower() in accepted:
            return d
    return None


def _tokens(text: str) -> list[str]:
    return [m.group() for m in _IDENT_RE.finditer(text)]


def concepts_named(lean_text: str, concepts: list[str]) -> dict[str, bool]:
    """For each concept, whether the candidate declares a predicate for it (decision 2's naming;
    whether the claim uses it is ``returned_reason``'s)."""
    decls = declarations(lean_text)
    return {c: _declares(decls, c) is not None for c in concepts}


def claim_of(decls: list[Declaration], concepts: list[str]) -> Declaration | int | None:
    """The candidate's claim (decision 1): its one sorry-bodied theorem, else its last
    Prop-valued def not named for a concept; ``None`` for none, the count for more than one
    statement."""
    theorems = [d for d in decls if d.keyword in THEOREM_KEYWORDS and d.is_statement]
    if len(theorems) == 1:
        return theorems[0]
    if theorems:
        return len(theorems)
    predicates = {n for c in concepts for n in _concept_names(c)}
    props = [d for d in decls if d.is_prop_def and d.last.lower() not in predicates]
    return props[-1] if props else None


def _claim_text(claim: Declaration) -> str:
    """What the claim says: a theorem's header (binders and type), a def's body."""
    return claim.header if claim.keyword in THEOREM_KEYWORDS else claim.body


def _inline_as(claim_text: str, concept: str) -> str | None:
    """A library constant the claim writes the concept as (``Nat.Prime``), if one is visible."""
    accepted = _concept_names(concept)
    for tok in _tokens(claim_text):
        if "." in tok and tok.rsplit(".", 1)[-1].lower() in accepted:
            return tok
        if tok in NOTATIONS and NOTATIONS[tok].rsplit(".", 1)[-1].lower() in accepted:
            return f"{tok} ({NOTATIONS[tok]})"
    return None


def returned_reason(lean_text: str, concepts: list[str]) -> str | None:
    """Why the candidate is returned to its author, or ``None`` when the rule is met."""
    decls = declarations(lean_text)
    claim = claim_of(decls, concepts)
    if claim is None:
        return (
            "returned: no conjecture declaration (a theorem, or a Prop-valued def such as "
            "`conj` or `claim`); nothing to probe"
        )
    if isinstance(claim, int):
        return f"returned: {claim} theorems declared; a candidate states one conjecture"
    text = _claim_text(claim)
    used = set(_tokens(text))
    for concept in concepts:
        decl = _declares(decls, concept)
        if decl is None:
            inline = _inline_as(text, concept)
            how = (
                f"written inline as `{inline}`"
                if inline
                else f"no predicate named `{concept}` or `Is{concept[:1].upper()}{concept[1:]}`"
                " is declared"
            )
            return (
                f"returned: the concept `{concept}` is not named as the candidate's own predicate "
                f"({how}); the probes replace a named predicate, so declare one and state the "
                "claim through it"
            )
        if decl.name not in used and decl.last not in used:
            return (
                f"returned: `{decl.name}` is declared for the concept `{concept}` but the claim "
                "does not use it; the probes replace the predicate the claim is stated through"
            )
    return None


def predicate_name(concept: str) -> str:
    """The wrapper's name for a concept's predicate: ``IsPrime`` for ``prime``/``Prime``."""
    if concept.lower().startswith("is") and len(concept) > 2:
        return concept[:1].upper() + concept[1:]
    return f"Is{concept[:1].upper()}{concept[1:]}"


def _notion(claim_text: str, concept: str) -> tuple[str, list[str]] | None:
    """The constant the original writes the concept as, and every token form it uses for it."""
    accepted = _concept_names(concept)
    notion: str | None = None
    forms: list[str] = []
    for tok in _tokens(claim_text):
        target = NOTATIONS.get(tok, tok)
        if target.rsplit(".", 1)[-1].lower() in accepted:
            if notion is None:
                notion = target
            if target == notion and tok not in forms:
                forms.append(tok)
    return None if notion is None else (notion, forms)


def _swap(text: str, forms: list[str], name: str) -> str:
    def sub(m: re.Match[str]) -> str:
        return name if m.group() in forms else m.group()

    return _IDENT_RE.sub(sub, text)


def _original_prop(claim: Declaration) -> str:
    """The claim as a Prop: a theorem's type under its binders, a def's body."""
    if claim.keyword not in THEOREM_KEYWORDS:
        return claim.body.strip()
    binders, _, typ = _split_binders(claim.header)
    typ = typ.strip()
    return f"∀ {binders.strip()}, {typ}" if binders.strip() else typ


def _split_binders(header: str) -> tuple[str, str, str]:
    """A theorem header as (binders, ':', type) at its first top-level colon."""
    depth = 0
    for i, c in enumerate(header):
        if c in _OPEN:
            depth += 1
        elif c in _CLOSE:
            depth -= 1
        elif c == ":" and depth == 0:
            return header[:i], ":", header[i + 1 :]
    return "", "", header


def wrapper_for(original_lean: str, concepts: list[str]) -> str:
    """The wrapper candidate for a ported statement that does not meet the rule (decision 3).

    Raises ``ValueError`` when the original already meets the rule, declares a name the wrapper
    needs, has no claim, or writes a concept in a way the wrapper cannot delegate (not used, or
    infix notation)."""
    if returned_reason(original_lean, concepts) is None:
        msg = "the statement already meets the format rule; no wrapper is needed"
        raise ValueError(msg)
    decls = declarations(original_lean)
    claim = claim_of(decls, concepts)
    if claim is None or isinstance(claim, int):
        msg = "the statement has no single conjecture declaration to wrap"
        raise ValueError(msg)
    taken = [d.name for d in decls if d is not claim and d.last in WRAPPER_NAMES]
    if taken:
        msg = f"the statement declares {taken}, which the wrapper needs"
        raise ValueError(msg)
    original = _original_prop(claim)
    restated = original
    predicates: list[tuple[str, str, str]] = []
    for concept in concepts:
        found = _notion(_claim_text(claim), concept)
        if found is None:
            msg = (
                f"the concept `{concept}` is not written in the statement as a constant the "
                "wrapper can delegate to (an identifier, or a scoped notation for one); an infix "
                "notation has no textual rewrite, so name it another way or write the wrapper by "
                "hand"
            )
            raise ValueError(msg)
        notion, forms = found
        name = predicate_name(concept)
        predicates.append((concept, name, notion))
        restated = _swap(restated, forms, name)
    prefix = original_lean[: claim.start].rstrip("\n")
    what = (
        f"the type of `{claim.name}`"
        if claim.keyword in THEOREM_KEYWORDS
        else f"the body of `{claim.name}`"
    )
    lines = [prefix, ""] if prefix.strip() else []
    lines += [
        f"/-- The original, verbatim: {what} (F26-R5: its text and hash are untouched). -/",
        f"def original : Prop := {original}",
        "",
    ]
    for concept, name, notion in predicates:
        lines += [
            f"/-- `{concept}`, as the original writes it: `{notion}`. -/",
            f"def {name} := {notion}",
            "",
        ]
    lines += [
        "/-- The original restated through the named predicates. -/",
        f"def conj : Prop := {restated}",
        "",
        "/-- The restatement is the original: each predicate unfolds to what it wrote. -/",
        "theorem port : conj ↔ original := Iff.rfl",
        "",
    ]
    return "\n".join(lines)


def format_exhibit(  # noqa: PLR0913 — one argument per fact the record carries
    candidate_id: str,
    reason: str,
    *,
    target: str,
    toolchain: str,
    mathlib_sha: str | None,
    run: str,
    date: str,
) -> dict[str, object]:
    """The ``exhibit/v1`` record the review job writes for a returned candidate: kind ``format``,
    result ``returned``, no Lean file (nothing was checked). Its id is a function of the candidate
    and the reason, so a second run writes the same record (R13)."""
    digest = hashlib.sha256(f"format\n{candidate_id}\n{reason}".encode()).hexdigest()[:8]
    doc: dict[str, object] = {
        "schema": "exhibit/v1",
        "target": target,
        "id": f"e-{digest}",
        "kind": "format",
        "candidate": candidate_id,
        "test": None,
        "result": "returned",
        "detail": reason[:2000],
        "lean_file": None,
        "toolchain": toolchain,
        "mathlib_sha": mathlib_sha,
        "run": run,
        "date": date,
    }
    schemas.validate(doc, "exhibit/v1")
    return doc
