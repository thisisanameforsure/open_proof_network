"""The formalization review's pairs (F26-R7, R8; D-9 v3.39; the amendment draft §3, §9 points 2-3).

Every pair of surviving candidates is compared in each direction, and each direction is recorded
as one of three states in ``pairs/<a>--<b>.yaml`` (``pair/v1``, ``a`` the lexically smaller id):

- **refuted**: a kernel-checked *instance* where the first claim holds and the second fails — at
  some ``n``, or under a probe (the concept made empty, or a small set). Never a proof that the
  two statements differ, which for an open conjecture would settle it. The instance is searched
  for in the candidates' tables (``review_lean.survey``) and only recorded once the kernel has
  checked it (``decide +kernel``), so **a failed attempt is never recorded as refuted** (D-9 v3.12:
  a failure is inconclusive). A holds-instance is looked for first (the implication then cannot be
  proved, so no proof is attempted); probe instances only after the proof attempt failed, since a
  probe exposes the formula and two formulas that differ under a probe can still be equivalent.
- **proved**: two-layer matching, the prototype's (§9 point 3). Layer one relates the two
  candidates' predicates for each concept the words use (``∀ x, B.IsPrime x ↔ A.Prime x``, else
  one implication), each by ``simp only`` and then ``grind``; layer two proves the direction with
  the concepts as atoms: ``simp only`` and ``exact``, then ``grind`` with the layer-one lemmas. The
  attempt is one bounded file (``first | …``).
- **open**: attempted without a result; the attempt is recorded (who: ``gate``, the tool, the
  budget). Open directions are claimable work (R8).

**The degenerate guard** (§3, on by default). A proved direction is re-elaborated with its
hypothesis cleared right after it is introduced (``intro n h; clear h; …``). If that still proves,
the proof never used its hypothesis — the conclusion holds outright within the budget — and the
direction is refused as a proof of equivalence: it stays **open**, the attempt naming the guard,
and the cleared proof is kept as a ``pair`` exhibit with result ``open`` (it shows what the guard
saw).

**A contributor's settlement** (R8, F26-T18). An open direction between two survivors is
claimable work, settled by a merged ``pair-proof/v1`` record under ``review/pair-proofs/``. The
job is still the only writer of pairs and exhibits: before attempting a direction itself it
re-checks such a record with its own runner (``contributed``, ``recheck``: the direction's
template, the region rules, the file elaborates, and for a proof the guarded copy does not), and
on a pass writes the ``pair`` exhibit (key ``contributed:<record>``) and the settled state. A
failed re-check leaves the direction open, the attempt naming the record and why.

A direction already ``proved`` or ``refuted`` on record (by this job's own attempt or from a
merged pair-proof record) is never re-attempted, and an ``open`` one whose recorded attempt is
this job's own at the same budget is not re-attempted either, so a second run writes nothing.
A pair record is written only when a direction changed; a later record for the same pair
supersedes (``review.in_order``: by date, then the generation in the name, F26-T18).
"""

from __future__ import annotations

from typing import Any

from opn_gate import pair_proofs, review_lean, schemas
from opn_gate.diagnostic import Diagnostic
from opn_gate.review_job import Job, _yaml_bytes, add_exhibit, find_exhibit, survey
from opn_gate.review_lean import Cand, Case, document, module, ns

#: What a recorded open attempt names as its tool.
TOOL = "gate: two-layer matching (simp only, exact, grind) under the degenerate guard"
GUARD_TOOL = (
    "gate: two-layer matching; the proof found never uses its hypothesis, so the degenerate "
    "guard refuses it as a proof of equivalence"
)


def _layer_one(job: Job, a: Cand, b: Cand) -> list[tuple[str, str]]:
    """Lemmas relating each concept's two predicates that the kernel accepted, as (name,
    statement-with-proof); used as atoms by layer two."""
    links: list[tuple[str, str]] = []
    for concept in sorted(set(a.predicates) & set(b.predicates)):
        pa = f"{ns(a.id, 'p')}.{a.predicates[concept]}"
        pb = f"{ns(b.id, 'p')}.{b.predicates[concept]}"
        for stmt in (f"∀ x, {pb} x ↔ {pa} x", f"∀ x, {pa} x → {pb} x", f"∀ x, {pb} x → {pa} x"):
            name = f"opnLink{len(links)}"
            body = (
                f"theorem {name} : {stmt} := by\n  first\n"
                f"    | (intro x; simp only [{pa}, {pb}])\n"
                f"    | (intro x; simp only [{pa}, {pb}]; grind)\n"
            )
            text = document(
                {"op": "link", "a": a.id, "b": b.id, "concept": concept, "stmt": stmt},
                (*a.imports, *b.imports),
                module(a, "p"),
                module(b, "p"),
                body,
            )
            if job.runner.check(text).ok:
                links.append((name, body))
                if "↔" in stmt:
                    break
    return links


def direction_text(a: Cand, b: Cand, links: list[tuple[str, str]], *, guard: bool) -> str:
    """``a → b`` (for every n, when indexed) under layer one's lemmas; ``guard`` clears the
    hypothesis right after it is introduced."""
    ca = f"{ns(a.id, 'p')}.{a.claim}"
    cb = f"{ns(b.id, 'p')}.{b.claim}"
    iffs = [n for n, s in links if "↔" in s.split(":=", 1)[0]]
    imps = [n for n, s in links if "↔" not in s.split(":=", 1)[0]]
    rw = ", ".join([ca, cb, *iffs])
    intro = "intro n h" if a.indexed else "intro h"
    if guard:
        intro += "; clear h"
    tactics = [
        f"({intro}; simp only [{ca}, {cb}] at *; exact h)",
        f"({intro}; simp only [{rw}] at *; grind)",
    ]
    if imps:
        tactics.append(f"({intro}; simp only [{rw}] at *; grind [{', '.join(imps)}])")
    goal = f"∀ n, {ca} n → {cb} n" if a.indexed else f"{ca} → {cb}"
    op = {"op": "direction", "a": a.id, "b": b.id, "guard": guard}
    return document(
        op,
        (*a.imports, *b.imports),
        module(a, "p"),
        module(b, "p"),
        *(body for _, body in links),
        "set_option maxHeartbeats 400000 in\n"
        f"theorem opnDirection : {goal} := by\n  first\n"
        + "".join(f"    | {t}\n" for t in tactics),
    )


def _instance_cases(job: Job, a: Cand, b: Cand, probes: tuple[str, ...]) -> list[Case]:
    """Cases where ``a``'s table holds and ``b``'s fails, in the order holds, covers, witness
    (smallest ``n`` first): candidates for a refuting instance, each still to be checked."""
    ta, tb = survey(job, a), survey(job, b)
    out: list[Case] = []
    if "holds" in probes:
        out += [
            Case("holds", n)
            for n, (x, y) in enumerate(zip(ta.get("holds", []), tb.get("holds", []), strict=False))
            if x and not y
        ][:1]
    if "covers" in probes and a.predicates and b.predicates:
        out += [
            Case("covers", n)
            for n, (x, y) in enumerate(
                zip(ta.get("covers", []), tb.get("covers", []), strict=False)
            )
            if x and not y
        ][:1]
    if "witness" in probes:
        for concept in sorted(set(a.predicates) & set(b.predicates)):
            for i, s in enumerate(review_lean.witness_sets()):
                key = f"witness:{concept}:{i}"
                for n, (x, y) in enumerate(zip(ta.get(key, []), tb.get(key, []), strict=False)):
                    if x and not y:
                        out.append(Case("witness", n, s, concept))
                        return out
    return out


def refute(job: Job, a: Cand, b: Cand, probes: tuple[str, ...]) -> dict[str, Any] | None:
    """The first instance the kernel accepts where ``a`` holds and ``b`` fails, as a ``pair``
    exhibit with result ``refuted``; ``None`` when no table offers one or the kernel accepts none.
    """
    for case in _instance_cases(job, a, b, probes):
        key = f"refute:{case.token()}"
        found = find_exhibit(job, "pair", a.id, b.id, key)
        if found is not None:
            if found.get("result") == "refuted":
                return found
            continue
        text = review_lean.instance_text(a, b, case)
        if job.runner.check(text).ok:
            return add_exhibit(
                job,
                "pair",
                a.id,
                b.id,
                key,
                "refuted",
                f"refuted at {case.words()}: {a.id} holds and {b.id} fails there",
                text,
            )
    return None


def attempt(job: Job, a: Cand, b: Cand) -> dict[str, Any]:  # noqa: PLR0911 — one per outcome
    """One direction ``a → b``: ``{"state", "exhibit", "attempt"}`` as ``pair/v1`` records it."""
    budget = max(1, int(job.runner.budget_s))
    if a.shape != b.shape or a.shape == "other":
        return _open(
            f"gate: not attempted, the claims' shapes differ ({a.shape}, {b.shape})", budget
        )
    refuted = refute(job, a, b, ("holds",))
    if refuted is not None:
        return {"state": "refuted", "exhibit": refuted["id"], "attempt": None}
    found = find_exhibit(job, "pair", a.id, b.id, "prove")
    if found is not None and found.get("result") == "proved":
        return {"state": "proved", "exhibit": found["id"], "attempt": None}
    if found is None:
        links = _layer_one(job, a, b)
        text = direction_text(a, b, links, guard=False)
        if job.runner.check(text).ok:
            guarded = direction_text(a, b, links, guard=True)
            if job.runner.check(guarded).ok:
                add_exhibit(
                    job,
                    "pair",
                    a.id,
                    b.id,
                    "guard",
                    "open",
                    f"degenerate: {b.id}'s claim follows with {a.id}'s hypothesis cleared, so "
                    "the proof never uses it and is refused as a proof of equivalence",
                    guarded,
                )
                return _open(GUARD_TOOL, budget)
            doc = add_exhibit(
                job,
                "pair",
                a.id,
                b.id,
                "prove",
                "proved",
                f"{a.id} implies {b.id}"
                + (" for every n" if a.indexed else "")
                + " (two-layer matching; the degenerate guard passed)",
                text,
            )
            return {"state": "proved", "exhibit": doc["id"], "attempt": None}
    elif find_exhibit(job, "pair", a.id, b.id, "guard") is not None:
        return _open(GUARD_TOOL, budget)
    refuted = refute(job, a, b, ("covers", "witness"))
    if refuted is not None:
        return {"state": "refuted", "exhibit": refuted["id"], "attempt": None}
    return _open(TOOL, budget)


def _open(tool: str, budget: int) -> dict[str, Any]:
    return {
        "state": "open",
        "exhibit": None,
        "attempt": {"who": "gate", "tool": tool, "budget_s": budget},
    }


def latest(job: Job, a: str, b: str) -> dict[str, Any] | None:
    held: dict[str, Any] | None = None
    for p in job.pairs:
        if (
            str(p.get("a")) == a
            and str(p.get("b")) == b
            and (held is None or str(p.get("date")) >= str(held.get("date")))
        ):
            held = p
    return held


def _keep(old: dict[str, Any] | None, budget: int) -> bool:
    """Whether a recorded direction stands without a new attempt: settled, or this job's own
    open attempt at the same budget."""
    if not isinstance(old, dict):
        return False
    if old.get("state") in ("proved", "refuted"):
        return True
    att = old.get("attempt")
    return (
        old.get("state") == "open"
        and isinstance(att, dict)
        and att.get("who") == "gate"
        and att.get("tool") in (TOOL, GUARD_TOOL)
        and att.get("budget_s") == budget
    )


def contributed(
    job: Job, a: Cand, b: Cand, direction: pair_proofs.Direction, budget: int
) -> dict[str, Any] | None:
    """The direction of the pair ``(a, b)`` (``pair/v1``'s order) as a merged pair-proof record
    settles it, or ``None`` when no record speaks to it (F26-T18).

    The records for the direction whose ``statement_hashes`` are the candidates' current ones
    are taken by record date, then by name; one with other hashes was checked against another
    text and is ignored with a note. The first whose re-check passes settles the direction: an
    exhibit (kind ``pair``, the direction's first candidate, the other as its test, the key
    naming the record, the record's Lean) and the state, ``exhibit`` set and ``attempt: null``;
    every later one is noted as not needed. When none passes the direction stays open, the
    attempt naming the first record and why; every failure is noted."""
    first, second = pair_proofs.ordered(a, b, direction)
    mine = sorted(
        (
            (stem, rec)
            for stem, rec in job.pair_proofs
            if (rec["a"], rec["b"], rec["direction"]) == (a.id, b.id, direction)
        ),
        key=lambda t: (str(t[1]["date"]), t[0]),
    )
    if not mine:
        return None
    job.pair_proofs_read.update(stem for stem, _ in mine)
    want = {
        "a": str(job.records.get(a.id, {}).get("statement_hash")),
        "b": str(job.records.get(b.id, {}).get("statement_hash")),
    }
    failures: list[tuple[str, dict[str, Any], str]] = []
    for i, (stem, rec) in enumerate(mine):
        if rec["statement_hashes"] != want:
            job.notes.append(
                f"pair-proof {stem}: its statement hashes are not the candidates' current ones "
                "(it was checked against another text); ignored"
            )
            continue
        why = recheck(job, rec, first, second)
        if why is not None:
            job.notes.append(f"pair-proof {stem}: the re-check failed: {why}")
            failures.append((stem, rec, why))
            continue
        for later, _ in mine[i + 1 :]:
            job.notes.append(f"pair-proof {later}: not needed, the direction is already settled")
        return _settled(job, stem, rec, first, second)
    if not failures:
        return None
    stem, rec, why = failures[0]
    tool = f"pair-proof {stem}: re-check failed: {why}"
    return {
        "state": "open",
        "exhibit": None,
        "attempt": {"who": str(rec["author"]), "tool": tool[:200], "budget_s": budget},
    }


def recheck(job: Job, rec: dict[str, Any], first: Cand, second: Cand) -> str | None:
    """Why the record's Lean does not settle the direction ``first → second``, or ``None``: the
    direction's template (``pair_proofs.template`` at the record's kind and case), the two
    regions' rules, the job's own elaboration, and for a proof the degenerate guard (the
    guarded copy must fail). Trusts nothing the gate said before the merge."""
    a, b = (first, second) if rec["direction"] == "forward" else (second, first)
    case = rec.get("case")
    n = case.get("n") if isinstance(case, dict) else None
    try:
        tmpl = pair_proofs.template(a, b, rec["direction"], rec["kind"], n)
    except ValueError as exc:
        return f"the direction takes no such {rec['kind']}: {exc}"
    lean = str(rec["lean"])
    filled = pair_proofs.split(lean, tmpl)
    if isinstance(filled, Diagnostic):
        return f"off its template: {filled.message}"
    bad = pair_proofs.problems(filled)
    if bad:
        return bad[0].message
    why = verdict(job, lean)
    if why is not None:
        return why
    if rec["kind"] == "proof" and job.runner.check(pair_proofs.guarded(lean, first)).ok:
        return (
            "the degenerate guard: it still proves with the hypothesis cleared, so it never used it"
        )
    return None


def verdict(job: Job, lean: str) -> str | None:
    """Why a filled template fails the job's own check, or ``None`` when it passes: it
    elaborates with no error and no ``sorry`` (``Runner.check``)."""
    checked = job.runner.check(lean)
    if checked.ok:
        return None
    return f"does not elaborate: {checked.first_error[:120]}"


def _settled(job: Job, stem: str, rec: dict[str, Any], first: Cand, second: Cand) -> dict[str, Any]:
    author, kind = str(rec["author"]), str(rec["kind"])
    if kind == "proof":
        result = "proved"
        what = f"{first.id} implies {second.id}" + (" for every n" if first.indexed else "")
        how = "re-checked by the review job; the degenerate guard passed"
    else:
        result = "refuted"
        n = rec["case"]["n"]
        what = f"refuted at n = {n}: {first.id} holds and {second.id} fails there"
        how = "re-checked by the review job"
    detail = f"contributed by {author} ({rec['direction']}): {what}; {how} (pair-proof {stem})"
    doc = add_exhibit(
        job, "pair", first.id, second.id, f"contributed:{stem}", result, detail, str(rec["lean"])
    )
    return {"state": result, "exhibit": doc["id"], "attempt": None}


def resolve(  # noqa: PLR0913 — one argument per fact the direction depends on
    job: Job,
    old: dict[str, Any] | None,
    a: Cand,
    b: Cand,
    *,
    direction: pair_proofs.Direction,
    budget: int,
) -> dict[str, Any]:
    """One direction of the pair ``(a, b)`` (``pair/v1``'s order) after this run: settled on
    record stands; else a merged pair-proof record for it; else this job's own open attempt at
    the same budget stands; else the job attempts it."""
    prev = old.get(direction) if old else None
    if isinstance(prev, dict) and prev.get("state") in ("proved", "refuted"):
        for stem, rec in job.pair_proofs:
            if (rec["a"], rec["b"], rec["direction"]) == (a.id, b.id, direction):
                job.pair_proofs_read.add(stem)
                job.notes.append(f"pair-proof {stem}: not needed, the direction is already settled")
        return prev
    got = contributed(job, a, b, direction, budget)
    if got is not None:
        return got
    if _keep(prev, budget):
        assert isinstance(prev, dict)
        return prev
    first, second = pair_proofs.ordered(a, b, direction)
    return attempt(job, first, second)


def run_pairs(job: Job, survivors: list[str]) -> list[dict[str, Any]]:
    """Every pair of survivors, each direction; returns the pair documents now in force (the
    record's latest, or this run's) and queues a record for each pair that changed."""
    budget = max(1, int(job.runner.budget_s))
    ids = [c for c in sorted(survivors) if c in job.cands]
    docs: list[dict[str, Any]] = []
    for i, a in enumerate(ids):
        for b in ids[i + 1 :]:
            old = latest(job, a, b)
            ca, cb = job.cands[a], job.cands[b]
            forward = resolve(job, old, ca, cb, direction="forward", budget=budget)
            backward = resolve(job, old, ca, cb, direction="backward", budget=budget)
            doc = {
                "schema": "pair/v1",
                "target": job.target,
                "a": a,
                "b": b,
                "forward": forward,
                "backward": backward,
                "date": job.date,
            }
            schemas.validate(doc, "pair/v1")
            if (
                old is not None
                and old.get("forward") == forward
                and old.get("backward") == backward
            ):
                docs.append(old)
                continue
            name = f"{a}--{b}.yaml"
            existing = {f"pairs/{n}" for n in _pair_files(job)}
            k = 1
            while f"pairs/{name}" in existing or f"pairs/{name}" in job.out:
                k += 1
                name = f"{a}--{b}--{job.date}-{k}.yaml"
            job.out[f"pairs/{name}"] = _yaml_bytes(doc)
            job.pairs.append(doc)
            docs.append(doc)
    for stem, _ in job.pair_proofs:
        if stem not in job.pair_proofs_read:
            job.notes.append(
                f"pair-proof {stem}: not a direction between two surviving candidates; not read"
            )
    return docs


def _pair_files(job: Job) -> list[str]:
    folder = job.base / "pairs"
    return sorted(p.name for p in folder.iterdir()) if folder.is_dir() else []


def concept_instance(job: Job, a: Cand, b: Cand, concept: str) -> dict[str, Any] | None:
    """Layer one refuted at a value: the first ``x`` where ``a``'s predicate for ``concept``
    holds and ``b``'s fails, checked by the kernel, as a ``pair`` exhibit (``refuted``); the
    claims' directions are not about it."""
    ta = survey(job, a).get(f"concept:{concept}", [])
    tb = survey(job, b).get(f"concept:{concept}", [])
    for x, (u, v) in enumerate(zip(ta, tb, strict=False)):
        if u and not v:
            case = Case("concept", x, None, concept)
            key = f"refute:{case.token()}"
            found = find_exhibit(job, "pair", a.id, b.id, key)
            if found is not None:
                return found if found.get("result") == "refuted" else None
            text = review_lean.instance_text(a, b, case)
            if job.runner.check(text).ok:
                return add_exhibit(
                    job,
                    "pair",
                    a.id,
                    b.id,
                    key,
                    "refuted",
                    f"the predicates for `{concept}` differ: at {x} {a.id}'s holds and "
                    f"{b.id}'s fails",
                    text,
                )
            return None
    return None
