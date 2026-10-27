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

A direction already ``proved`` or ``refuted`` on record (by this job or by a merged pair-proof
artifact) is never re-attempted, and an ``open`` one whose recorded attempt is this job's own at
the same budget is not re-attempted either, so a second run writes nothing. A pair record is
written only when a direction changed; a later record for the same pair supersedes
(``review.in_order``: by date, then the generation in the name, F26-T18).
"""

from __future__ import annotations

from typing import Any

from opn_gate import review_lean, schemas
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
            forward = old["forward"] if old and _keep(old.get("forward"), budget) else None
            backward = old["backward"] if old and _keep(old.get("backward"), budget) else None
            if forward is None:
                forward = attempt(job, ca, cb)
            if backward is None:
                backward = attempt(job, cb, ca)
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
