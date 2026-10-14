"""The Lean the formalization review's job writes and checks (F26-R4, R6, R7, R8, R13; D-9 v3.39).

Rebuilt from the first prototype (``engineering/prototypes/formalization-round/round.py``, F26-Q2),
nothing imported from it. Every file the job elaborates is built here, as text, and goes through
the toolchain seam (``Toolchain.elaborate``), so the fast tier drives the same text through a fake
and the lean tier and the sandbox through the real toolchain. Nothing here reads a host path to
learn about the toolchain: what a check found comes back as ``lean --json`` messages (the
2026-09-12 lesson).

**The header line.** Every file starts with one comment, ``-- opn-review: <json>``, naming what
the file asks (``op``) and, for a case, the case. Lean reads it as a comment. The job reads it back
from an exhibit's or a test's Lean to know which case a question or a test is about (the records'
``case`` field is words, for the proposer); the fast tier's fake reads it to answer the check
without Lean. It is written only by this module.

**A candidate's shape** (``prepare``). The claim is what ``review_format.claim_of`` finds: a
Prop-valued ``def`` (the prototypes' ``def claim (n : Nat) : Prop``) or a sorry-bodied
``theorem``, which is rewritten to ``def opnClaim <binders> : Prop := <type>`` so it can be named
as a predicate. A claim with exactly one binder over the naturals is *indexed*: its small cases
are computable (``claim n``). A claim with no binders is *closed*. Anything else has no small
cases the job can compute, and the compile exhibit says so (F26-R6). A concept's predicate is the
declaration the format rule found for it; the probes replace it only when it is a predicate on
one natural number.

**The probes** (F26-R6; the amendment draft §2). ``holds``: the claim at ``n``. ``covers``: the
claim at ``n`` with every concept predicate made empty, so it fails exactly where the candidate
says something. ``witness``: the claim at ``n`` with one concept's predicate made the small set
``S``. ``concept``: the predicate's value at ``n``. Each is decided by the kernel
(``decide +kernel``); a table of values (``survey``) is a search for cases, compiled code and
never evidence.
"""

from __future__ import annotations

import concurrent.futures as cf
import hashlib
import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from opn_gate import layout, qa, review_format
from opn_gate.toolchain import ResolvedToolchain, Toolchain, module_output_path

#: The first line of every file the job writes or checks.
HEADER = "-- opn-review: "
#: The probes an intent test runs under (``intent-test/v1``'s ``probe``).
PROBES: tuple[str, ...] = ("holds", "covers", "witness", "concept")
#: The ``n`` of the holds, covers and concept tables a survey computes (the prototype's 0..40).
TABLE_N = 40
#: The ``n`` of the witness tables, and the values and sizes of the witness sets: every set of
#: one value below ``WITNESS_VALUES_1`` and of two values below ``WITNESS_VALUES_2``. The
#: prototype chose these per conjecture (13/37/21 values, sizes 1 and 2, n up to 24/5/4); the
#: job chooses them mechanically, the same for every review (F26-R6: case choice is mechanical).
WITNESS_N = 5
WITNESS_VALUES_1 = 13
WITNESS_VALUES_2 = 9
#: Lean's disjunction, spelled out for the linter.
OR = "\u2228"
#: The module every check is elaborated as.
MODULE = "OpnReview"

_IMPORT_RE = re.compile(r"^import\s+\S+[^\n]*$", re.M)
_NAT = "(?:Nat|\u2115)"  # Nat, or its double-struck name
_ONE_NAT_BINDER_RE = re.compile(rf"^\s*\(\s*([^\s():]+)\s*:\s*{_NAT}\s*\)\s*$")
_UNARY_PRED_HEADER_RE = re.compile(rf"^\s*\(\s*([^\s():]+)\s*:\s*{_NAT}\s*\)\s*:\s*Prop\s*$")
_SORRY_RE = re.compile(r"declaration uses ['`]sorry['`]")


# --- cases -------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Case:
    """One small case: a probe, the ``n`` (the value, for a ``concept`` probe), the witness set
    and the concept a ``witness`` or ``concept`` probe is about."""

    probe: str
    n: int
    set: tuple[int, ...] | None = None
    concept: str | None = None

    def key(self) -> dict[str, Any]:
        return {
            "probe": self.probe,
            "n": self.n,
            "set": list(self.set) if self.set is not None else None,
            "concept": self.concept,
        }

    def token(self) -> str:
        """The case as one canonical string (ids and de-duplication)."""
        return json.dumps(self.key(), sort_keys=True, ensure_ascii=False)

    @classmethod
    def from_key(cls, doc: object) -> Case | None:
        if not isinstance(doc, dict) or doc.get("probe") not in PROBES:
            return None
        n = doc.get("n")
        if not isinstance(n, int) or isinstance(n, bool) or n < 0:
            return None
        raw = doc.get("set")
        values: tuple[int, ...] | None = None
        if raw is not None:
            if not isinstance(raw, list) or not all(
                isinstance(v, int) and not isinstance(v, bool) for v in raw
            ):
                return None
            values = tuple(raw)
        concept = doc.get("concept")
        if concept is not None and not isinstance(concept, str):
            return None
        return cls(str(doc["probe"]), n, values, concept)

    def words(self) -> str:
        """The case in words, for a test record's ``case``."""
        if self.probe == "holds":
            return f"n = {self.n}: does the conjecture hold?"
        if self.probe == "covers":
            return f"n = {self.n}: does the conjecture say anything about it?"
        if self.probe == "concept":
            return f"is {self.n} {self.concept}, in the sense the conjecture means?"
        return f"n = {self.n}, {self._supposing()}"

    def _supposing(self) -> str:
        vals = sorted(self.set or ())
        concept = self.concept or "concept"
        if len(vals) == 1:
            return f"supposing {vals[0]} were the only {concept}"
        listed = ", ".join(map(str, vals[:-1])) + f" and {vals[-1]}" if vals else "nothing"
        return f"supposing {listed} were the only {concept}s"

    def question(self) -> str:
        """The question in mathematics, phrased as the hypothesis it tests (the amendment draft
        §9 point 5): what the probe asks, never "would a prime at 5 count?"."""
        if self.probe == "holds":
            return f"Does the conjecture hold at n = {self.n}?"
        if self.probe == "covers":
            return f"Does the conjecture say anything about n = {self.n}?"
        if self.probe == "concept":
            return f"Is {self.n} {self.concept}, in the sense the conjecture means?"
        s = self._supposing().replace("supposing", "Suppose", 1)
        return f"{s}. Would the conjecture be satisfied at n = {self.n}?"


def header_of(lean_text: str) -> dict[str, Any] | None:
    """The ``-- opn-review:`` header of a file the job wrote, or ``None``."""
    first = lean_text.split("\n", 1)[0]
    if not first.startswith(HEADER):
        return None
    try:
        doc = json.loads(first[len(HEADER) :])
    except ValueError:
        return None
    return doc if isinstance(doc, dict) else None


def case_of(lean_text: str) -> Case | None:
    """The case a file the job wrote is about, from its header."""
    doc = header_of(lean_text)
    return None if doc is None else Case.from_key(doc.get("case"))


# --- a candidate's shape -----------------------------------------------------------------------


@dataclass(frozen=True)
class Cand:
    """A candidate as the job checks it (``prepare``)."""

    id: str
    source: str  # as filed
    imports: tuple[str, ...]
    raw: str  # as filed, imports removed: what the compile check elaborates
    body: str  # the claim named as a predicate, imports removed: what every other check uses
    claim: str  # the claim's name in ``body``
    binder: str | None  # the indexed claim's variable
    claim_prop: str  # the claim's proposition (a def's body, a theorem's type)
    shape: str  # "indexed" | "closed" | "other"
    predicates: dict[str, str] = field(default_factory=dict)  # concept -> unary predicate name
    not_probed: tuple[str, ...] = ()  # concepts whose predicate is not on one natural number
    theorem_shape: bool = False

    @property
    def indexed(self) -> bool:
        return self.shape == "indexed"

    @property
    def why_no_cases(self) -> str | None:
        """Why small cases do not apply, or ``None`` when they do."""
        if self.shape == "closed":
            return (
                "small cases do not apply: the claim is a closed proposition, not a predicate on n"
            )
        if self.shape == "other":
            return (
                "small cases do not apply: the claim's binders are not exactly one natural number"
            )
        return None


def ns(cid: str, tag: str = "") -> str:
    """The namespace a candidate (or one of its probe copies) is elaborated in."""
    base = "C_" + re.sub(r"[^A-Za-z0-9]", "_", cid)
    return f"{base}_{tag}" if tag else base


def _split_binders(header: str) -> tuple[str, str]:
    """A theorem header as (binders, type) at its first top-level colon."""
    depth = 0
    for i, c in enumerate(header):
        if c in "([{⦃":
            depth += 1
        elif c in ")]}⦄":
            depth -= 1
        elif c == ":" and depth == 0:
            return header[:i].strip(), header[i + 1 :].strip()
    return "", header.strip()


def _strip_imports(text: str) -> tuple[tuple[str, ...], str]:
    imports = tuple(m.group(0).split()[1] for m in _IMPORT_RE.finditer(text))
    return imports, _IMPORT_RE.sub("", text)


_NEXT_COMMAND_RE = re.compile(r"\n(?=\S)")


def _top_level_assign(text: str) -> int | None:
    """The offset of the first top-level ``:=`` in ``text``."""
    depth = 0
    for i, c in enumerate(text):
        if c in "([{⦃⟨":
            depth += 1
        elif c in ")]}⦄⟩":
            depth -= 1
        elif depth == 0 and text.startswith(":=", i):
            return i
    return None


@dataclass(frozen=True)
class ClaimSpan:
    """Where a candidate's claim is in its source, every offset into the source."""

    name: str
    keyword: str
    start: int  # the declaration's keyword
    end: int  # where its command ends: the next line that starts in column 0
    prop_start: int  # the proposition: a def's body, a theorem's type
    prop_end: int
    binders: str


def claim_span(source: str, concepts: list[str]) -> ClaimSpan | None:
    """The claim ``review_format.claim_of`` finds, cut at the end of its own command (a following
    ``instance`` is not part of it: Lean commands start in column 0)."""
    decls = review_format.declarations(source)
    claim = review_format.claim_of(decls, concepts)
    if claim is None or isinstance(claim, int):
        return None
    masked = layout.code_mask(source)
    first_line = masked.find("\n", claim.start)
    nxt = _NEXT_COMMAND_RE.search(masked, first_line if first_line >= 0 else len(masked))
    end = min(claim.end, nxt.start() + 1) if nxt else claim.end
    after_name = masked.find(claim.name, claim.start) + len(claim.name)
    seg = masked[after_name:end]
    assign = _top_level_assign(seg)
    if assign is None:
        return None
    header = seg[:assign]
    if claim.keyword in review_format.THEOREM_KEYWORDS:
        binders, prop = _split_binders(header)
        colon = header.rfind(prop) if prop else len(header)
        p0 = after_name + colon
        p1 = after_name + assign
    else:
        binders = re.sub(r":\s*Prop\s*$", "", header.strip()).strip()
        p0 = after_name + assign + 2
        p1 = end
    while p1 > p0 and masked[p1 - 1].isspace():
        p1 -= 1
    while p0 < p1 and masked[p0].isspace():
        p0 += 1
    return ClaimSpan(claim.name, claim.keyword, claim.start, end, p0, p1, binders)


def prepare(cid: str, source: str, concepts: list[str]) -> Cand | str:
    """The candidate's shape, or why the job cannot read one (the format rule has run first, so
    this is rare: a claim the rule accepted that is neither a def nor a theorem)."""
    decls = review_format.declarations(source)
    span = claim_span(source, concepts)
    if span is None:
        return "no single claim to check"
    masked = layout.code_mask(source)
    prop = masked[span.prop_start : span.prop_end]
    binders = span.binders
    if span.keyword in review_format.THEOREM_KEYWORDS:
        name = "opnClaim"
        new = (
            f"def {name} {binders} : Prop :=\n  {prop}\n\n"
            if binders
            else (f"def {name} : Prop :=\n  {prop}\n\n")
        )
        rewritten = source[: span.start] + new + source[span.end :]
        theorem_shape = True
    else:
        name, rewritten = span.name, source
        theorem_shape = False
    m = _ONE_NAT_BINDER_RE.match(binders)
    shape = "indexed" if m else ("closed" if not binders.strip() else "other")
    predicates: dict[str, str] = {}
    not_probed: list[str] = []
    for concept in concepts:
        accepted = (concept.lower(), f"is{concept.lower()}")
        decl = next(
            (
                d
                for d in decls
                if d.keyword in review_format.PREDICATE_KEYWORDS and d.last.lower() in accepted
            ),
            None,
        )
        if decl is not None and _UNARY_PRED_HEADER_RE.match(decl.header):
            predicates[concept] = decl.name
        else:
            not_probed.append(concept)
    imports, raw = _strip_imports(source)
    _, body = _strip_imports(rewritten)
    return Cand(
        id=cid,
        source=source,
        imports=imports,
        raw=raw,
        body=body,
        claim=name,
        binder=m.group(1) if m else None,
        claim_prop=prop,
        shape=shape,
        predicates=predicates,
        not_probed=tuple(not_probed),
        theorem_shape=theorem_shape,
    )


# --- probes as source rewrites -----------------------------------------------------------------


@dataclass(frozen=True)
class Probe:
    """How the concept predicates are replaced: ``empty`` makes every one ``False``; ``set``
    makes ``concept``'s membership in ``values``."""

    kind: str  # "empty" | "set"
    values: tuple[int, ...] = ()
    concept: str | None = None


def probe_for(case: Case) -> Probe | None:
    if case.probe == "covers":
        return Probe("empty")
    if case.probe == "witness":
        return Probe("set", tuple(case.set or ()), case.concept)
    return None


def _replace_predicate(body: str, name: str, expr: str) -> str:
    decls = review_format.declarations(body)
    decl = next((d for d in decls if d.name == name), None)
    if decl is None:
        return body
    new_def = (
        f"def {name} (_x : Nat) : Prop := {expr}\n"
        f"instance : DecidablePred {name} := fun _x => by unfold {name}; infer_instance\n\n"
    )
    out = body[: decl.start] + new_def + body[decl.end :]
    # every instance the candidate gave for the old predicate goes: it may unfold the old body
    inst = re.compile(
        rf"^instance\b[^\n]*DecidablePred\s+{re.escape(name)}\b.*?(?=^\S|\Z)", re.M | re.S
    )
    first = out.find(new_def) + len(new_def)
    return out[:first] + inst.sub("", out[first:])


def probed_body(c: Cand, probe: Probe | None) -> str:
    """The candidate's body with its concept predicates replaced as ``probe`` says."""
    if probe is None:
        return c.body
    body = c.body
    for concept, name in c.predicates.items():
        if probe.kind == "empty":
            body = _replace_predicate(body, name, "False")
        elif concept == probe.concept:
            expr = f" {OR} ".join(f"_x = {v}" for v in probe.values) or "False"
            body = _replace_predicate(body, name, expr)
    return body


def _has_instance(body: str, name: str) -> bool:
    return re.search(rf"DecidablePred\s+{re.escape(name)}\b", body) is not None


def module(c: Cand, tag: str = "", probe: Probe | None = None, inside: str = "") -> str:
    """The candidate in its own namespace, its claim named and (when indexed) decidable, with
    ``inside`` appended before the namespace closes."""
    body = probed_body(c, probe).strip()
    extra = ""
    if c.indexed and not _has_instance(body, c.claim):
        extra = (
            f"\ninstance : DecidablePred {c.claim} := "
            f"fun {c.binder} => by unfold {c.claim}; infer_instance\n"
        )
    space = ns(c.id, tag)
    return f"namespace {space}\n{body}\n{extra}{inside}\nend {space}\n"


def claim_expr(c: Cand, tag: str, n: int | None) -> str:
    name = f"{ns(c.id, tag)}.{c.claim}"
    return name if n is None else f"{name} {n}"


def document(op: dict[str, Any], imports: set[str] | tuple[str, ...], *parts: str) -> str:
    """One file: the header, the imports, the parts."""
    lines = [HEADER + json.dumps(op, sort_keys=True, ensure_ascii=False)]
    lines += [f"import {m}" for m in sorted(set(imports))]
    lines.append("")
    return "\n".join(lines) + "\n" + "\n".join(p.rstrip() + "\n" for p in parts)


def _case_tag(case: Case) -> str:
    return {"holds": "h", "covers": "c", "concept": "k", "witness": "w"}[case.probe]


def case_prop(c: Cand, case: Case, value: bool, tag: str) -> str:
    """The proposition a case asserts of a candidate: the claim (or the predicate) at the case,
    negated when ``value`` is false."""
    if case.probe == "concept":
        pred = c.predicates.get(case.concept or "")
        expr = f"{ns(c.id, tag)}.{pred} {case.n}"
    else:
        expr = claim_expr(c, tag, case.n)
    return expr if value else f"¬ {expr}"


def decide_text(c: Cand, case: Case, value: bool, *, op: dict[str, Any] | None = None) -> str:
    """``example : <the case's proposition> := by decide +kernel`` for one candidate."""
    tag = _case_tag(case)
    prop = case_prop(c, case, value, tag)
    head = {"op": "decide", "cand": c.id, "case": case.key(), "value": value, **(op or {})}
    return document(
        head,
        c.imports,
        module(c, tag, probe_for(case)),
        f"example : {prop} := by decide +kernel",
    )


def instance_text(a: Cand, b: Cand, case: Case, *, op: dict[str, Any] | None = None) -> str:
    """The refutation of the direction ``a → b`` at a case: a kernel-checked instance where
    ``a``'s claim (or predicate) holds and ``b``'s fails (the amendment draft §3)."""
    tag = _case_tag(case)
    probe = probe_for(case)
    head = {"op": "instance", "a": a.id, "b": b.id, "case": case.key(), **(op or {})}
    return document(
        head,
        (*a.imports, *b.imports),
        module(a, tag, probe),
        module(b, tag, probe),
        f"example : {case_prop(a, case, True, tag)} ∧ {case_prop(b, case, False, tag)} := "
        "by decide +kernel",
    )


def test_text(test_id: str, case: Case, expected: bool, source: str, ref: str) -> str:
    """An intent test's own Lean: what the case is, as a definition core Lean elaborates. The
    test runs against a candidate as ``decide_text``; this file records the case for anyone
    reading the record and for the job (the header)."""
    words = case.words().replace("-/", "- /")
    return document(
        {"op": "test", "case": case.key(), "expected": expected},
        (),
        f"/-! Intent test {test_id} ({case.probe}): {words}\n"
        f"Expected: {'yes' if expected else 'no'}, from {source} ({ref}). The gate runs it "
        "against every candidate (F26-R6). -/",
        f"def opnCase : Nat := {case.n}",
    )


# --- surveys: tables of values, a search for cases ---------------------------------------------


def witness_sets() -> list[tuple[int, ...]]:
    ones: list[tuple[int, ...]] = [(v,) for v in range(WITNESS_VALUES_1)]
    twos: list[tuple[int, ...]] = [
        (a, b) for a in range(WITNESS_VALUES_2) for b in range(WITNESS_VALUES_2) if a < b
    ]
    return ones + twos


@dataclass(frozen=True)
class Row:
    """One table a survey prints: ``key`` names it, ``probe`` and ``concept`` say what it is."""

    key: str
    probe: str  # holds | covers | witness | concept
    n_max: int
    set: tuple[int, ...] | None = None
    concept: str | None = None

    def case(self, n: int) -> Case:
        return Case(self.probe, n, self.set, self.concept)

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "probe": self.probe,
            "n_max": self.n_max,
            "set": list(self.set) if self.set is not None else None,
            "concept": self.concept,
        }


def survey_rows(c: Cand, *, witness: bool = True) -> list[Row]:
    """What a survey of ``c`` computes: holds and covers to ``TABLE_N``, each probed concept's
    values to ``TABLE_N``, and (``witness``) each witness set to ``WITNESS_N``."""
    if not c.indexed:
        return []
    rows = [Row("holds", "holds", TABLE_N)]
    if c.predicates:
        rows.append(Row("covers", "covers", TABLE_N))
    for concept in sorted(c.predicates):
        rows.append(Row(f"concept:{concept}", "concept", TABLE_N, None, concept))
    if witness:
        for concept in sorted(c.predicates):
            for i, s in enumerate(witness_sets()):
                rows.append(Row(f"witness:{concept}:{i}", "witness", WITNESS_N, s, concept))
    return rows


def survey_text(c: Cand, rows: list[Row]) -> str:
    """One file printing every row as ``OPN|<key>|<0/1 per n>``: compiled code, a search for
    cases and never evidence (the prototype's ``table``)."""
    parts: list[str] = []
    tags: dict[tuple[str, tuple[int, ...] | None, str | None], str] = {}
    evals: list[str] = []
    for row in rows:
        probe = probe_for(row.case(0))
        pkey = (row.probe if probe else "base", row.set, row.concept if probe else None)
        if pkey not in tags:
            tag = f"s{len(tags)}"
            tags[pkey] = tag
            parts.append(module(c, tag, probe))
        tag = tags[pkey]
        if row.probe == "concept":
            expr = f"{ns(c.id, tag)}.{c.predicates[row.concept or '']} n"
        else:
            expr = f"{claim_expr(c, tag, None)} n"
        evals.append(
            f'#eval IO.println ("OPN|{row.key}|" ++ String.join ((List.range {row.n_max + 1}).map '
            f'(fun n => if decide ({expr}) then "1" else "0")))'
        )
    head = {"op": "survey", "cand": c.id, "rows": [r.as_dict() for r in rows]}
    return document(head, c.imports, *parts, *evals)


_TABLE_RE = re.compile(r"^OPN\|(?P<key>[^|]+)\|(?P<bits>[01]*)\s*$", re.M)


def parse_tables(messages: list[str]) -> dict[str, list[bool]]:
    out: dict[str, list[bool]] = {}
    for text in messages:
        for m in _TABLE_RE.finditer(text):
            out[m.group("key")] = [ch == "1" for ch in m.group("bits")]
    return out


# --- the runner: the toolchain seam ------------------------------------------------------------


@dataclass(frozen=True)
class Checked:
    """What one elaboration said: ``ok`` when it elaborated with no error (and no ``sorry``
    beyond ``allowed_sorry``), every message's text, and why it could not run if it could not."""

    ok: bool
    messages: tuple[str, ...] = ()
    error: str | None = None  # a timeout or a toolchain failure: decides nothing

    @property
    def first_error(self) -> str:
        return self.error or next((m for m in self.messages if m), "")


#: F26-Q21: the wall-clock cap for building one graph module a candidate imports; a Context that
#: imports Mathlib loads it, which the per-check budget was not sized for.
LOCAL_BUDGET_S = 600.0


def graph_sources(target_dir: Path, imports: list[str]) -> list[tuple[str, Path]] | str:
    """The graph's own modules among ``imports`` (``Defs.*`` from ``defs/``, ``Nodes.«id».Stem``
    from ``nodes/<id>/``) and the graph modules they import in turn, dependencies first; a reason
    when one names no file or the imports form a cycle (F26-Q21)."""
    order: list[tuple[str, Path]] = []
    state: dict[str, int] = {}

    def visit(module: str) -> str | None:
        kind, node = layout.module_origin(module)
        if kind not in ("defs", "node"):
            return None
        if state.get(module) == 2:
            return None
        if state.get(module) == 1:
            return f"the graph modules the candidates import form a cycle through {module}"
        if kind == "defs":
            path = target_dir / "defs" / f"{module.split('.', 1)[1]}.lean"
        else:
            path = target_dir / "nodes" / str(node) / f"{module.rsplit('.', 1)[1]}.lean"
        if not path.is_file():
            return f"{module} names no file in the target ({path.relative_to(target_dir)})"
        state[module] = 1
        for inner in layout.imports_of(path.read_text(encoding="utf-8")):
            problem = visit(inner)
            if problem is not None:
                return problem
        state[module] = 2
        order.append((module, path))
        return None

    for module in imports:
        problem = visit(module)
        if problem is not None:
            return problem
    return order


@dataclass
class Runner:
    """Elaborates the job's files through ``toolchain`` in ``workdir`` (which the sandbox
    mounts), each under ``budget_s``, ``jobs`` at a time; a text checked twice is checked once."""

    toolchain: Toolchain
    resolved: ResolvedToolchain
    workdir: Path
    budget_s: float
    jobs: int = 4
    _seen: dict[tuple[str, int], Checked] = field(default_factory=dict)
    count: int = 0
    #: the oleans of the graph modules the candidates import, laid beside every check (Q21)
    graph_build: Path | None = None

    def build_graph_modules(self, sources: list[tuple[str, Path]]) -> str | None:
        """Build ``sources`` (``graph_sources``'s order) once into ``<workdir>/graph/build``; a
        reason when one cannot be built. Each later check finds them on its search path."""
        if not sources:
            return None
        src = self.workdir / "graph" / "src"
        build = self.workdir / "graph" / "build"
        build.mkdir(parents=True, exist_ok=True)
        for module, path in sources:
            dest = src / module_output_path(module, ".lean")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(path, dest)
            try:
                elab = self.toolchain.elaborate(
                    self.resolved, dest, module, build, root=src, timeout_s=LOCAL_BUDGET_S
                )
            except subprocess.TimeoutExpired:
                return f"{module} did not build within {LOCAL_BUDGET_S:g} s"
            except (OSError, RuntimeError) as exc:
                return f"{module} could not be built: {exc}"
            if not elab.ok:
                first = next((m.text for m in elab.errors), "") or elab.stderr.strip()
                return f"{module} does not elaborate: {first[:300]}"
        self.graph_build = build
        return None

    def check(self, text: str, *, allowed_sorry: int = 0) -> Checked:
        key = (hashlib.sha256(text.encode()).hexdigest(), allowed_sorry)
        if key in self._seen:
            return self._seen[key]
        result = self._elaborate(text, key[0], allowed_sorry)
        self._seen[key] = result
        return result

    def many(self, texts: list[str]) -> list[Checked]:
        if self.jobs <= 1 or len(texts) <= 1:
            return [self.check(t) for t in texts]
        with cf.ThreadPoolExecutor(self.jobs) as pool:
            return list(pool.map(self.check, texts))

    def _elaborate(self, text: str, digest: str, allowed_sorry: int) -> Checked:
        self.count += 1
        here = self.workdir / "review" / digest[:20]
        here.mkdir(parents=True, exist_ok=True)
        src = here / f"{MODULE}.lean"
        src.write_text(text, encoding="utf-8")
        if self.graph_build is not None:
            shutil.copytree(self.graph_build, here / "out", dirs_exist_ok=True)
        try:
            elab = self.toolchain.elaborate(
                self.resolved, src, MODULE, here / "out", timeout_s=self.budget_s
            )
        except subprocess.TimeoutExpired:
            return Checked(False, (), f"timed out after {self.budget_s:g} s")
        except (OSError, RuntimeError) as exc:
            return Checked(False, (), f"the toolchain could not run: {exc}")
        texts = tuple(m.text for m in elab.messages)
        errors = [m.text for m in elab.errors]
        sorries = sum(1 for m in elab.messages if _SORRY_RE.search(m.text))
        ok = elab.ok and not errors and sorries <= allowed_sorry
        if not ok and not errors and not elab.ok:
            texts = (*texts, elab.stderr.strip() or "the elaboration failed with no message")
        return Checked(ok, texts)


# --- small helpers the stages share ------------------------------------------------------------


def screen_texts(c: Cand) -> dict[str, str | None]:
    """The statement and vacuity screens as files (the negation screen needs a case and is
    ``negation_text``); ``None`` where the shape gives the screen nothing to try."""
    tactics_core = qa.SCREEN_TACTICS_CORE[:3]
    if c.shape == "indexed":
        claim = c.claim
        b = c.binder
        stmt_tactics = [
            f"(intro {b}; unfold {claim}; omega)",
            f"(intro {b}; unfold {claim}; intros; omega)",
            f"(intro {b}; simp only [{claim}]; grind)",
        ]
        stmt = f"theorem opnScreen : ∀ ({b} : Nat), {claim} {b} := by\n  first\n" + "".join(
            f"    | {t}\n" for t in stmt_tactics
        )
        false_goal = f"∀ ({b} : Nat), {qa.conclusion_to_false(c.claim_prop)}"
    elif c.shape == "closed":
        stmt_tactics = [f"(unfold {c.claim}; {t})" for t in tactics_core]
        stmt = f"theorem opnScreen : {c.claim} := by\n  first\n" + "".join(
            f"    | {t}\n" for t in stmt_tactics
        )
        false_goal = qa.conclusion_to_false(c.claim_prop)
    else:
        return {"statement": None, "false": None}
    false_tactics = ["(intros; omega)", "(intros; simp_all)", "(intros; grind)"]
    false = f"theorem opnScreen : {false_goal} := by\n  first\n" + "".join(
        f"    | {t}\n" for t in false_tactics
    )
    out: dict[str, str | None] = {}
    for which, thm in (("statement", stmt), ("false", false)):
        out[which] = document(
            {"op": "screen", "cand": c.id, "screen": which},
            c.imports,
            module(c, "sc", None, inside=f"set_option maxHeartbeats 400000 in\n{thm}"),
        )
    return out


def negation_text(c: Cand, n: int | None) -> str | None:
    """The negation screen for an indexed claim: a counterexample ``n`` from the survey, checked
    by the kernel. A closed claim's negation is tried by tactics."""
    if c.shape == "indexed" and n is not None:
        b = c.binder
        thm = (
            f"theorem opnScreen : ¬ ∀ ({b} : Nat), {c.claim} {b} := "
            f"fun h => absurd (h {n}) (by decide +kernel)"
        )
        op: dict[str, Any] = {"op": "screen", "cand": c.id, "screen": "negation", "n": n}
    elif c.shape == "closed":
        tactics = [f"(unfold {c.claim}; {t})" for t in qa.SCREEN_TACTICS_CORE[:3]]
        thm = f"theorem opnScreen : ¬ {c.claim} := by\n  first\n" + "".join(
            f"    | {t}\n" for t in tactics
        )
        op = {"op": "screen", "cand": c.id, "screen": "negation", "n": None}
    else:
        return None
    return document(op, c.imports, module(c, "sc", None, inside=thm))


def compile_text(c: Cand) -> str:
    """The candidate as filed, in its own namespace."""
    space = ns(c.id)
    return document(
        {"op": "compile", "cand": c.id},
        c.imports,
        f"namespace {space}\n{c.raw.strip()}\nend {space}",
    )


def with_id(c: Cand, new_id: str, source: str, concepts: list[str]) -> Cand | str:
    """A variant of ``c`` (a mutant) under its own id."""
    got = prepare(new_id, source, concepts)
    return got if isinstance(got, str) else replace(got, id=new_id)
