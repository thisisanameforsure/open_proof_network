"""The formalization review's mutation stage (F26-R8; D-9 v3.39, D-11; the amendment draft §1
stage 6, §9).

The surviving cluster's representative is perturbed by single-site changes to its claim — never
to a concept's predicate, which the concept questions test — in D-11's defect classes, each mutant
one change (``mutants``), capped at ``CAP`` (200, F26 §6; the run's summary says when the cap was
hit). Each mutant is then asked, in order:

1. does it elaborate? If not: an ``error`` exhibit (no Lean), and it says nothing about the tests;
2. does an intent test on record fail on it? The first that does **caught** it: a ``fail``
   exhibit whose Lean is the kernel's proof that the mutant says the opposite of the expected
   answer;
3. otherwise it **survived** the tests (a ``pass`` exhibit). Where its tables differ from the
   representative's at a case (the prototype's "would raise a question"), the Lean is the kernel's
   instance of the difference and the case becomes a question of kind ``mutant``; where nothing
   differs, the pair attempt is run both ways: proved equivalent is a ``proved`` exhibit (the
   change did not change the meaning, and nothing is asked), else the question is asked with no
   case ("a variant agrees on every case checked").

So the count of ``fail`` among the mutants that elaborate and are not proved equivalent is what
R8's page reports: how many meaning-changing mutants the tests catch, a measure of the tests and
never of the statement. The meaning of each result for ``kind: mutant`` is this module's and
``review_job``'s docstring's (``exhibit/v1`` is pinned; proposed as an F26 Q entry).

**The classes.** The first prototype's operators, rebuilt generically (F26-Q2): ``relation``
(``<`` and ``≤`` swapped, and ``>`` and ``≥``), ``connective`` (and, or), ``offset`` (an
offset dropped: ``(n+1)`` becomes ``n``), ``exponent`` (``(n+1)^2`` becomes ``n^2 + 1``),
``product`` (``n*(n-1)`` becomes ``n*n - 1``) and ``constant`` (each numeral one up and one down).
Two of D-11's classes the prototype did not run are added: ``hypothesis`` (a top-level hypothesis
of the claim dropped) and ``quantifier`` (``∀`` and ``∃`` swapped). Each mutant carries its class,
so the prototype's counts can be read off the classes it ran.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from opn_gate import layout, review_lean
from opn_gate.review_job import (
    Job,
    TestRec,
    add_exhibit,
    find_exhibit,
    probe_value,
    survey,
    table_value,
)
from opn_gate.review_lean import OR, Cand, Case, document, module, ns

#: The most mutants one representative is perturbed into (F26 §6).
CAP = 200
_SWAPS: tuple[tuple[str, str, str], ...] = (
    ("relation", "<", "≤"),
    ("relation", "≤", "<"),
    ("relation", ">", "≥"),
    ("relation", "≥", ">"),
    ("connective", "∧", OR),
    ("connective", OR, "∧"),
    ("quantifier", "∀", "∃"),
    ("quantifier", "∃", "∀"),
)
_ID = r"[A-Za-z_][A-Za-z0-9_']*"
_OFFSET_RE = re.compile(rf"\(\s*({_ID})\s*([+-])\s*(\d+)\s*\)")
_EXPONENT_RE = re.compile(rf"\(\s*({_ID})\s*\+\s*(\d+)\s*\)\s*\^\s*(\d+)")
_PRODUCT_RE = re.compile(rf"({_ID})\s*\*\s*\(\s*({_ID})\s*-\s*(\d+)\s*\)")
_NUMERAL_RE = re.compile(r"(?<![\w.'])(\d+)(?![\w.])")


@dataclass(frozen=True)
class Mutant:
    label: str  # what changed and where, in the claim's text
    cls: str  # the defect class
    source: str  # the representative's Lean with the one change


def _claim_region(source: str, concepts: list[str]) -> tuple[int, int] | None:
    """Where the claim's proposition is in the source: a def's body, a theorem's type."""
    span = review_lean.claim_span(source, concepts)
    return None if span is None else (span.prop_start, span.prop_end)


def _hypotheses(text: str) -> list[tuple[int, int]]:
    """The spans of the claim's top-level hypotheses (``H →``), after any leading ``∀ x,``."""
    spans: list[tuple[int, int]] = []
    depth = 0
    i = 0
    # skip leading binders
    stripped = text.lstrip()
    start = len(text) - len(stripped)
    while text.startswith("∀", start):
        comma = _top_level(text, ",", start)
        if comma is None:
            break
        start = comma + 1
    seg_start = start
    i = start
    while i < len(text):
        ch = text[i]
        if ch in "([{⦃⟨":
            depth += 1
        elif ch in ")]}⦄⟩":
            depth -= 1
        elif depth == 0 and text.startswith("→", i):
            spans.append((seg_start, i + 1))
            seg_start = i + 1
        elif depth == 0 and ch in "∃∀,":
            break
        i += 1
    return spans


def _top_level(text: str, token: str, start: int) -> int | None:
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch in "([{⦃⟨":
            depth += 1
        elif ch in ")]}⦄⟩":
            depth -= 1
        elif depth == 0 and text.startswith(token, i):
            return i
    return None


def mutants(c: Cand, concepts: list[str], cap: int = CAP) -> tuple[list[Mutant], bool]:
    """Every single-site change of the representative's claim, in the classes' order; and
    whether the cap cut the list."""
    region = _claim_region(c.source, concepts)
    if region is None:
        return [], False
    lo, hi = region
    src = c.source
    masked = layout.code_mask(src)
    body = src[lo:hi]
    code = masked[lo:hi]
    out: list[Mutant] = []

    def add(cls: str, start: int, end: int, new: str, what: str) -> None:
        if code[start:end] != body[start:end]:  # inside a comment or a string
            return
        out.append(Mutant(f"{what} at {start}", cls, src[: lo + start] + new + src[lo + end :]))

    for cls, old, new in _SWAPS:
        for m in re.finditer(re.escape(old), code):
            add(cls, m.start(), m.end(), new, f"{old} → {new}")
    for m in _OFFSET_RE.finditer(code):
        add("offset", m.start(), m.end(), m.group(1), f"{m.group(0)} → {m.group(1)}")
    for m in _EXPONENT_RE.finditer(code):
        new = f"{m.group(1)}^{m.group(3)} + {m.group(2)}"
        add("exponent", m.start(), m.end(), new, f"{m.group(0)} → {new}")
    for m in _PRODUCT_RE.finditer(code):
        new = f"{m.group(1)}*{m.group(2)} - {m.group(3)}"
        add("product", m.start(), m.end(), new, f"{m.group(0)} → {new}")
    for m in _NUMERAL_RE.finditer(code):
        k = int(m.group(1))
        for nk in (k - 1, k + 1):
            if nk >= 0:
                add("constant", m.start(), m.end(), str(nk), f"{k} → {nk}")
    for s, e in _hypotheses(code):
        add("hypothesis", s, e, "", f"`{' '.join(body[s:e].split())}` dropped")
    capped = len(out) > cap
    return out[:cap], capped


def _compiles(job: Job, m: Cand) -> bool:
    text = document({"op": "compile-mutant", "cand": m.id}, m.imports, module(m))
    return job.runner.check(text).ok


def _caught(job: Job, m: Cand, rep: Cand) -> tuple[TestRec, str] | None:
    """The first test on record the mutant fails, with the kernel's proof of it."""
    for tid in sorted(job.tests):
        t = job.tests[tid]
        if t.case is None or t.expected is None:
            continue
        if t.case.probe in ("concept",):  # a mutant changes the claim, never a predicate
            continue
        if t.case.probe in ("covers", "witness") and not m.predicates:
            continue
        value = probe_value(t.case, t.expected)
        if job.runner.check(review_lean.decide_text(m, t.case, value, op={"of": rep.id})).ok:
            continue
        opposite = review_lean.decide_text(m, t.case, not value, op={"of": rep.id})
        if job.runner.check(opposite).ok:
            return t, opposite
    return None


def _difference(job: Job, m: Cand, rep: Cand) -> tuple[Case, str] | None:
    """The first case where the mutant's tables and the representative's differ, with the
    kernel's instance of it (whichever of the two holds there)."""
    tm, tr = survey(job, m), survey(job, rep)
    cases: list[Case] = []
    for probe in ("holds", "covers"):
        rm, rr = tm.get(probe, []), tr.get(probe, [])
        cases += [Case(probe, n) for n, (x, y) in enumerate(zip(rm, rr, strict=False)) if x != y][
            :1
        ]
    for concept in sorted(rep.predicates):
        for i, s in enumerate(review_lean.witness_sets()):
            key = f"witness:{concept}:{i}"
            rm, rr = tm.get(key, []), tr.get(key, [])
            diff = [n for n, (x, y) in enumerate(zip(rm, rr, strict=False)) if x != y]
            if diff:
                cases.append(Case("witness", diff[0], s, concept))
                break
        if len(cases) > 2:
            break
    for case in cases:
        vm = table_value(tm, case)
        if vm is None:
            continue
        first, second = (m, rep) if probe_value(case, vm) else (rep, m)
        text = review_lean.instance_text(first, second, case, op={"of": rep.id})
        if job.runner.check(text).ok:
            return case, text
    return None


def _equivalent(job: Job, m: Cand, rep: Cand) -> str | None:
    """Both directions between the mutant and the representative proved (the pairs' tactics,
    guard included), as one file the kernel accepted; ``None`` otherwise."""
    from opn_gate import review_pairs  # noqa: PLC0415

    links = review_pairs._layer_one(job, m, rep)
    fwd = review_pairs.direction_text(m, rep, links, guard=False)
    back = review_pairs.direction_text(rep, m, links, guard=False)
    if not (job.runner.check(fwd).ok and job.runner.check(back).ok):
        return None
    for a, b in ((m, rep), (rep, m)):
        if job.runner.check(review_pairs.direction_text(a, b, links, guard=True)).ok:
            return None
    body_f = fwd.split("theorem opnDirection", 1)[1]
    body_b = back.split("theorem opnDirection", 1)[1]
    text = document(
        {"op": "equivalent", "a": m.id, "b": rep.id},
        (*m.imports, *rep.imports),
        module(m, "p"),
        module(rep, "p"),
        *(body for _, body in links),
        f"set_option maxHeartbeats 400000 in\ntheorem opnForward{body_f}",
        f"set_option maxHeartbeats 400000 in\ntheorem opnBackward{body_b}",
    )
    return text if job.runner.check(text).ok else None


def mutate(job: Job, rep: Cand, *, cap: int = CAP) -> dict[str, Any]:  # noqa: PLR0912 — one branch per result
    """Stage 6 on ``rep``: an exhibit per mutant, a question per surviving one; the summary."""
    from opn_gate import review_questions  # noqa: PLC0415

    found, capped = mutants(rep, job.concepts, cap)
    results: list[dict[str, Any]] = []
    for i, mu in enumerate(found):
        key = f"mutant:{mu.label}"
        held = find_exhibit(job, "mutant", rep.id, None, key)
        result: str
        if held is not None:
            result = str(held["result"])
            doc = held
        else:
            prepared = review_lean.prepare(f"{rep.id}-m{i}", mu.source, job.concepts)
            if isinstance(prepared, str) or not _compiles(job, prepared):
                doc = add_exhibit(
                    job,
                    "mutant",
                    rep.id,
                    None,
                    key,
                    "error",
                    f"{mu.label}: does not elaborate",
                    None,
                )
            else:
                m = prepared
                caught = _caught(job, m, rep)
                if caught is not None:
                    test, text = caught
                    doc = add_exhibit(
                        job,
                        "mutant",
                        rep.id,
                        None,
                        key,
                        "fail",
                        f"{mu.label} ({mu.cls}): caught by test {test.id} at "
                        f"{test.case.words() if test.case else '?'}",
                        text,
                    )
                else:
                    diff = _difference(job, m, rep)
                    if diff is not None:
                        case, text = diff
                        doc = add_exhibit(
                            job,
                            "mutant",
                            rep.id,
                            None,
                            key,
                            "pass",
                            f"{mu.label} ({mu.cls}): every test passes; it differs from the "
                            f"representative at {case.words()}",
                            text,
                        )
                    else:
                        eq = _equivalent(job, m, rep)
                        if eq is not None:
                            doc = add_exhibit(
                                job,
                                "mutant",
                                rep.id,
                                None,
                                key,
                                "proved",
                                f"{mu.label} ({mu.cls}): proved equivalent to the "
                                "representative both ways; not a change of meaning",
                                eq,
                            )
                        else:
                            doc = add_exhibit(
                                job,
                                "mutant",
                                rep.id,
                                None,
                                key,
                                "pass",
                                f"{mu.label} ({mu.cls}): every test passes and no case "
                                "checked tells it from the representative",
                                None,
                            )
            result = str(doc["result"])
        if result == "pass":
            lean = job.exhibit_lean.get(str(doc["id"]))
            asked = review_lean.case_of(lean) if lean else None
            text = (
                asked.question()
                if asked is not None
                else "A variant of the statement agrees with it on every small case checked. "
                "Is there a case on which the conjecture and this variant should differ?"
            )
            review_questions.add_question(job, text, "mutant", str(doc["id"]), asked)
        claim = _claim_line(mu.source, job.concepts)
        results.append(
            {
                "label": mu.label,
                "class": mu.cls,
                "result": result,
                "claim": claim,
                "exhibit": doc["id"],
            }
        )
    counts: dict[str, int] = {}
    for r in results:
        counts[r["result"]] = counts.get(r["result"], 0) + 1
    return {
        "representative": rep.id,
        "total": len(results),
        "caught": counts.get("fail", 0),
        "survived": counts.get("pass", 0),
        "equivalent": counts.get("proved", 0),
        "not_elaborating": counts.get("error", 0),
        "capped": capped,
        "cap": cap,
        "results": results,
    }


def _claim_line(source: str, concepts: list[str]) -> str:
    region = _claim_region(source, concepts)
    if region is None:
        return ""
    return " ".join(source[region[0] : region[1]].split())


def namespace_of(c: Cand) -> str:
    return ns(c.id)
