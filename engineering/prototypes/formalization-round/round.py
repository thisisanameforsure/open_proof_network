"""A formalization round (decisions draft v3.36), run end to end on core Lean.

Prototype, not network code. For each conjecture in ``manifest.json`` it takes every candidate in
``candidates/<conjecture>/`` (human, agent and planted) and runs the round's automated stages:

  compile      each candidate, wrapped in its own namespace, must elaborate;
  table        ``claim n`` evaluated for n = 0..N (compiled code: a search, not evidence);
  screen       try to prove ``∀ n, claim n`` (generic tactics, then any agent exhibit in
               ``exhibits/``); a proof of an open conjecture by a small budget discards it;
  seeds        the proposer's cases, each a kernel-checked intent test;
  pairs        each direction ``∀ n, A.claim n → B.claim n`` is proved (tactics), refuted (a
               kernel-checked instance where A holds and B fails) or open;
  ask          every refuted direction becomes a question at that n; the proposer answers
               (simulated by ``oracle``, written from the words, independent of every candidate);
               each answer is a kernel-checked intent test, and failing candidates are discarded;
  mutate       the surviving reference is perturbed site by site; a mutant is caught if an intent
               test or a screen discards it, equivalent if both directions prove, missed otherwise.

Every discard carries the Lean that discarded it, re-checked by the kernel (``decide +kernel``, or
the screen's proof with its axioms printed). Writes ``out/results.json``; ``render.py`` draws it.

    python3 round.py [--only goldbach] [--n 40] [--jobs 6]
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEAN = Path.home() / ".elan/toolchains/leanprover--lean4---v4.33.1/bin/lean"
WORK = Path(tempfile.gettempdir()) / "opn-round"
TIMEOUT_S = 90


# --- the proposer, simulated: the words, read faithfully, in Python ------------------------------


def _prime(p: int) -> bool:
    return p >= 2 and all(p % d for d in range(2, int(p**0.5) + 1))


def _between(lo: int, hi: int, P) -> bool:
    """Some x with P(x) strictly between lo and hi."""
    return any(P(x) for x in range(lo + 1, hi))


#: The words, read faithfully, with the concept "prime" left as a parameter P. With P the real
#: primes this is the proposer's answer to "does it hold at n?"; with P empty it answers "does it
#: say anything at n?"; with P = {c} it answers "would a prime at c count for n?".
READING = {
    "goldbach": lambda n, P: not (n > 2 and n % 2 == 0) or any(P(p) and P(n - p) for p in range(n + 1)),
    "legendre": lambda n, P: n < 1 or _between(n * n, (n + 1) ** 2, P),
    "oppermann": lambda n, P: n < 2 or (_between(n * (n - 1), n * n, P) and _between(n * n, n * (n + 1), P)),
}
ORACLE = {c: (lambda r: lambda n: r(n, _prime))(r) for c, r in READING.items()}
COVERED = {c: (lambda r: lambda n: not r(n, lambda _x: False))(r) for c, r in READING.items()}

#: The concepts the words use, as the proposer would answer a question about one value.
CONCEPTS = {"prime": _prime}


# --- Lean -----------------------------------------------------------------------------------------


def ns(cid: str) -> str:
    return "C_" + re.sub(r"[^A-Za-z0-9]", "_", cid)


def wrap(cid: str, src: str) -> str:
    return f"namespace {ns(cid)}\n{src.strip()}\nend {ns(cid)}\n"


def lean(text: str) -> tuple[bool, str]:
    """Elaborate one file; ok means no error and no sorry."""
    WORK.mkdir(parents=True, exist_ok=True)
    f = WORK / (hashlib.sha256(text.encode()).hexdigest()[:16] + ".lean")
    f.write_text(text)
    try:
        r = subprocess.run([str(LEAN), str(f)], capture_output=True, text=True, timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    out = r.stdout + r.stderr
    ok = r.returncode == 0 and ": error" not in out and "sorry" not in out
    return ok, out


def defs_of(src: str) -> list[str]:
    return re.findall(r"^def\s+(\w+)", src, flags=re.M)


SCREEN_TACTICS = [
    "intro n; unfold {c}; omega",
    "intro n; unfold {c}; intros; omega",
    "intro n; simp only [{c}]; grind",
]


def screen(cid: str, src: str, exhibit: str | None) -> dict:
    c = f"{ns(cid)}.claim"
    for tac in SCREEN_TACTICS:
        t = tac.format(c=c)
        ok, _ = lean(wrap(cid, src) + f"theorem screen : ∀ n, {c} n := by\n  {t}\n")
        if ok:
            return {"proved": True, "by": f"tactic: {t}", "lean": f"theorem screen : ∀ n, {c} n := by {t}"}
    if exhibit:
        body = wrap(cid, src + "\n" + exhibit) + f"#print axioms {ns(cid)}.screen\n"
        ok, out = lean(body)
        if ok:
            return {"proved": True, "by": "agent exhibit", "lean": exhibit.strip(),
                    "axioms": out.strip().splitlines()[-1]}
    return {"proved": False}


def table(cid: str, src: str, n_max: int) -> list[bool] | None:
    c = f"{ns(cid)}.claim"
    ok, out = lean(wrap(cid, src) + (
        f'#eval IO.println ("TABLE:" ++ String.intercalate "," '
        f'((List.range {n_max + 1}).map (fun n => if decide ({c} n) then "1" else "0")))\n'))
    m = re.search(r"TABLE:([01,]+)", out)
    return [x == "1" for x in m.group(1).split(",")] if ok and m else None


def unary_helpers(src: str) -> list[str]:
    return [d for d in re.findall(r"^def\s+(\w+)\s*\(\s*\w+\s*:\s*Nat\s*\)\s*:\s*Prop", src, flags=re.M)
            if d != "claim"]


def counterfactual(src: str) -> str:
    """The candidate with every unary helper predicate made empty (``:= False``) and its instance
    replaced. Under it the claim fails exactly where it asks for something, so its truth table is
    the candidate's *coverage*: a probe that tells "holds" from "says nothing here"."""
    out = src
    for h in unary_helpers(src):
        out = re.sub(rf"^def {h}\b.*?(?=^\S|\Z)", f"def {h} (_x : Nat) : Prop := False\n", out,
                     flags=re.M | re.S)
        out = re.sub(rf"^instance\s*:\s*DecidablePred {h}\b.*?(?=^\S|\Z)",
                     f"instance : DecidablePred {h} := fun _ => instDecidableFalse\n", out,
                     flags=re.M | re.S)
    return out


def probe_source(src: str, S: tuple[int, ...]) -> str:
    """The candidate with every unary helper predicate replaced by membership in S."""
    body = " ∨ ".join(f"_x = {c}" for c in S) or "False"
    out = src
    for h in unary_helpers(src):
        out = re.sub(rf"^def {h}\b.*?(?=^\S|\Z)", f"def {h} (_x : Nat) : Prop := {body}\n", out,
                     flags=re.M | re.S)
        out = re.sub(rf"^instance\s*:\s*DecidablePred {h}\b.*?(?=^\S|\Z)",
                     f"instance : DecidablePred {h} := fun _x => by unfold {h}; infer_instance\n", out,
                     flags=re.M | re.S)
    return out


def probe_sets(spec: dict) -> list[tuple[int, ...]]:
    import itertools
    pr = spec["probe"]
    vals = range(pr["values"])
    return [S for k in range(1, pr["arity"] + 1) for S in itertools.combinations(vals, k)]


def probe_tables(cid: str, src: str, sets: list[tuple[int, ...]], n_probe: int) -> list[list[bool]] | None:
    """claim n under each witness probe, for n = 0..n_probe: one file, one namespace per probe."""
    parts, evals = [], []
    for i, S in enumerate(sets):
        pid = f"{cid}-p{i}"
        parts.append(wrap(pid, probe_source(src, S)))
        evals.append(f'(String.intercalate "" ((List.range {n_probe + 1}).map '
                     f'(fun n => if decide ({ns(pid)}.claim n) then "1" else "0")))')
    text = "".join(parts) + "#eval do\n" + "".join(
        f'  IO.println ("P{i}:" ++ {e})\n' for i, e in enumerate(evals))
    ok, out = lean(text)
    rows = dict(re.findall(r"^P(\d+):([01]+)$", out, flags=re.M))
    if not ok or len(rows) != len(sets):
        return None
    return [[ch == "1" for ch in rows[str(i)]] for i in range(len(sets))]


def probe_check(cid: str, src: str, S: tuple[int, ...], k: int, expected: bool) -> tuple[bool, str]:
    pid = f"{cid}-probe"
    prop = f"{ns(pid)}.claim {k}" if expected else f"¬ {ns(pid)}.claim {k}"
    ok, _ = lean(wrap(pid, probe_source(src, S)) + f"example : {prop} := by decide +kernel\n")
    return ok, f"-- with the helper predicate replaced by membership in {set(S)}\nexample : {prop} := by decide +kernel"


def helper_table(cid: str, src: str, h: str, n_max: int) -> list[bool] | None:
    ok, out = lean(wrap(cid, src) + (
        f'#eval IO.println ("TABLE:" ++ String.intercalate "," '
        f'((List.range {n_max + 1}).map (fun n => if decide ({ns(cid)}.{h} n) then "1" else "0")))\n'))
    m = re.search(r"TABLE:([01,]+)", out)
    return [x == "1" for x in m.group(1).split(",")] if ok and m else None


def concept_check(cid: str, src: str, h: str, x: int, expected: bool) -> tuple[bool, str]:
    prop = f"{ns(cid)}.{h} {x}" if expected else f"¬ {ns(cid)}.{h} {x}"
    ok, _ = lean(wrap(cid, src) + f"example : {prop} := by decide +kernel\n")
    return ok, f"example : {prop} := by decide +kernel"


def kernel_check(cid: str, src: str, k: int, expected: bool) -> tuple[bool, str]:
    """The intent test at k, decided by the kernel."""
    c = f"{ns(cid)}.claim"
    prop = f"{c} {k}" if expected else f"¬ {c} {k}"
    ok, _ = lean(wrap(cid, src) + f"example : {prop} := by decide +kernel\n")
    return ok, f"example : {prop} := by decide +kernel"


_LINKS: dict[tuple[str, str], list[tuple[str, str]]] = {}


def helper_links(a: str, sa: str, b: str, sb: str) -> list[tuple[str, str]]:
    """Layer one of the matching: relate each helper of B to each helper of A, one predicate at a
    time (``B.IsPrime x ↔ A.Prime x``, else one implication). Returns (name, statement) for the
    lemmas the kernel accepted, so layer two can treat the helpers as atoms."""
    key = (sa, sb)
    if key in _LINKS:
        return _LINKS[key]
    links: list[tuple[str, str]] = []
    ha = [d for d in defs_of(sa) if d != "claim"]
    hb = [d for d in defs_of(sb) if d != "claim"]
    i = 0
    for x in ha:
        for y in hb:
            A, B = f"{ns(a)}.{x}", f"{ns(b)}.{y}"
            for stmt in (f"∀ x, {B} x ↔ {A} x", f"∀ x, {A} x → {B} x", f"∀ x, {B} x → {A} x"):
                for tac in (f"intro x; simp only [{A}, {B}]", f"intro x; simp only [{A}, {B}]; grind"):
                    ok, _ = lean(wrap(a, sa) + wrap(b, sb) + f"theorem L : {stmt} := by {tac}\n")
                    if ok:
                        links.append((f"link{i}", f"theorem link{i} : {stmt} := by {tac}"))
                        i += 1
                        break
                if links and links[-1][1].startswith(f"theorem link{i - 1} : {stmt}"):
                    if "↔" in stmt:
                        break
    _LINKS[key] = links
    return links


def direction(a: str, sa: str, b: str, sb: str, exhibit: str | None = None) -> dict:
    """Try ∀ n, A.claim n → B.claim n with a small, fixed tactic budget: helpers matched first
    (``helper_links``), then the claims compared with the helpers as atoms."""
    ca, cb = f"{ns(a)}.claim", f"{ns(b)}.claim"
    links = helper_links(a, sa, b, sb)
    iffs = [n for n, s in links if "↔" in s]
    imps = [n for n, s in links if "↔" not in s]
    rw = ", ".join([ca, cb, *iffs])
    tactics = [
        f"intro n h; simp only [{ca}, {cb}] at *; exact h",
        f"intro n h; simp only [{rw}] at *; grind",
        f"intro n h; simp only [{rw}] at *; grind [{', '.join(imps)}]" if imps else None,
    ]
    head = wrap(a, sa) + wrap(b, sb) + "set_option maxHeartbeats 400000\n" + "".join(
        s + "\n" for _, s in links)
    for t in filter(None, tactics):
        ok, _ = lean(head + f"theorem dir : ∀ n, {ca} n → {cb} n := by\n  {t}\n")
        if ok:
            return {"state": "proved", "by": "tactic", "lean": t, "links": [s for _, s in links]}
    if exhibit:  # an open direction is claimable work; an agent's proof is checked like any other
        ok, _ = lean(head + exhibit)
        if ok:
            return {"state": "proved", "by": "agent exhibit", "lean": exhibit.strip(),
                    "links": [s for _, s in links]}
    return {"state": "open", "links": [s for _, s in links]}


# --- mutation -------------------------------------------------------------------------------------

SWAPS = [("<", "≤"), ("≤", "<"), ("∧", "∨"), ("∨", "∧"), ("(n+1)", "n"), ("(n-1)", "n"),
         ("(n+1)^2", "n^2 + 1"), ("n*(n-1)", "n*n - 1")]


def mutants(src: str) -> list[tuple[str, str]]:
    """One change per mutant, inside the claim's body only (helper definitions untouched)."""
    line = claim_text(src)
    head, body = line.split(":=", 1)
    out: list[tuple[str, str]] = []
    for old, new in SWAPS:
        for m in re.finditer(re.escape(old), body):
            nb = body[: m.start()] + new + body[m.end():]
            out.append((f"{old} → {new} at {m.start()}", src.replace(line, head + ":=" + nb)))
    for m in re.finditer(r"\b(\d+)\b", body):
        k = int(m.group(1))
        for nk in (k - 1, k + 1):
            if nk >= 0:
                nb = body[: m.start()] + str(nk) + body[m.end():]
                out.append((f"{k} → {nk} at {m.start()}", src.replace(line, head + ":=" + nb)))
    return out


def claim_text(src: str) -> str:
    """The whole ``def claim`` definition, however many lines it spans."""
    m = re.search(r"^def claim\b.*?(?=^\S|\Z)", src, flags=re.M | re.S)
    if not m:
        raise ValueError("no def claim")
    return m.group(0).rstrip()


# --- the round ------------------------------------------------------------------------------------


def ask_text(kind: str, k: int, concept) -> str:
    """The question as the proposer reads it: mathematics, never Lean."""
    if kind == "holds":
        return f"Does the conjecture hold at n = {k}?"
    if kind == "covers":
        return f"Does the conjecture say anything about n = {k}?"
    if kind == "concept":
        return f"Is {k} {concept}, in the sense the conjecture means?"
    # the probe asks about the whole claim under a hypothetical set of primes, so the question
    # must too: "would a prime at 5 count?" reads as "is 5 in an interval", a different question
    # whose answer differs when the claim needs two witnesses (Oppermann at n = 2: 5 is in the
    # second interval, yet with 5 the only prime the first interval is empty)
    if len(concept) == 1:
        return f"Suppose {concept[0]} were the only prime. Would the conjecture be satisfied at n = {k}?"
    return (f"Suppose {' and '.join(map(str, sorted(concept)))} were the only primes. "
            f"Would the conjecture be satisfied at n = {k}?")


def run(conj: str, spec: dict, n_max: int, jobs: int) -> dict:
    oracle = ORACLE[conj]
    cdir = HERE / "candidates" / conj
    src = {p.stem: p.read_text() for p in sorted(cdir.glob("*.lean"))}
    meta = spec["candidates"]
    missing = sorted(set(src) - set(meta))
    if missing:
        raise SystemExit(f"{conj}: candidates not in the manifest: {missing}")
    cands: dict[str, dict] = {c: {**meta[c], "id": c, "source": src[c], "status": "live"} for c in src}
    ex = {p.stem: p.read_text() for p in (HERE / "exhibits" / conj).glob("*.lean")} if (
        HERE / "exhibits" / conj).exists() else {}
    pool = cf.ThreadPoolExecutor(jobs)

    def discard(c: str, stage: str, reason: str, lean_text: str) -> None:
        if cands[c]["status"] == "live":
            cands[c].update(status="discarded", stage=stage, reason=reason, exhibit=lean_text)

    # compile + table
    tabs = dict(zip(src, pool.map(lambda c: table(c, src[c], n_max), src)))
    for c, t in tabs.items():
        cands[c]["table"] = t
        if t is None:
            discard(c, "compile", "does not elaborate, or claim is not decidable", "")

    # screen
    live = [c for c in cands if cands[c]["status"] == "live"]
    for c, s in zip(live, pool.map(lambda c: screen(c, src[c], ex.get(c)), live)):
        cands[c]["screen"] = s
        if s["proved"]:
            discard(c, "screen", f"∀ n, claim n proved by {s['by']}: a small budget proves it, "
                                 "so it is not the open conjecture", s["lean"])

    # coverage (the counterfactual probe) and helper tables, for every candidate that compiled
    cfs = {c: counterfactual(src[c]) for c in src}
    compiled = [c for c in cands if cands[c].get("table") is not None]
    for c, t in zip(compiled, pool.map(lambda c: table(c, cfs[c], n_max), compiled)):
        cands[c]["coverage"] = t
    helpers: dict[str, dict[str, list[bool] | None]] = {}
    for c in compiled:
        hs = unary_helpers(src[c])
        helpers[c] = dict(zip(hs, pool.map(lambda h: helper_table(c, src[c], h, n_max), hs)))
    # which concept each helper stands for: the one it agrees with on at least 85% of 0..N
    concept_of: dict[tuple[str, str], str] = {}
    for c, hs in helpers.items():
        for h, tab in hs.items():
            for name, fn in CONCEPTS.items():
                if tab and sum(v == fn(i) for i, v in enumerate(tab)) >= 0.85 * len(tab):
                    concept_of[(c, h)] = name
    cands_concepts = {c: {h: concept_of.get((c, h)) for h in hs} for c, hs in helpers.items()}
    for c in compiled:
        cands[c]["helpers"] = cands_concepts[c]
        # format rule: the probes replace the predicate that stands for each concept the words use,
        # so a candidate that writes the concept inline cannot be probed, and probing its real claim
        # would discard a correct version (found by alt-inline, 2026-10-09). It goes back to its
        # author with the reason; it is not judged.
        if cands[c]["status"] == "live" and not any(cands_concepts[c].values()):
            cands[c].update(status="returned", stage="format", exhibit="",
                            reason="no named predicate for the concept the words use ("
                                   + ", ".join(CONCEPTS) + "); returned to its author to name it, "
                                   "so the coverage and witness probes can replace it")
    sets = probe_sets(spec)
    n_probe = spec["probe"]["n"]
    reading = READING[conj]
    for c, pt in zip(compiled, pool.map(lambda c: probe_tables(c, src[c], sets, n_probe), compiled)):
        cands[c]["probes"] = pt

    # intent tests: the proposer's seeds first, then a question for every disagreement among live
    # candidates (on truth, on coverage, on a shared concept), until nothing new is found.
    # Three kinds, each decided by the kernel per candidate:
    #   holds   claim k ↔ the proposer's answer
    #   covers  under the counterfactual, claim k fails ↔ the conjecture says something at k
    #   concept helper x ↔ the proposer's answer about the concept (e.g. "is 1 prime?")
    tests: list[dict] = []
    covered = COVERED[conj]

    def have(kind: str, k: int, concept: str | None = None) -> bool:
        return any(t["kind"] == kind and t["n"] == k and t.get("concept") == concept for t in tests)

    def apply_test(kind: str, k: int, origin: str, note: str, concept: str | None = None) -> None:
        if have(kind, k, concept):
            return
        exp = {"holds": lambda: oracle(k), "covers": lambda: covered(k),
               "concept": lambda: CONCEPTS[concept](k),
               "witness": lambda: reading(k, lambda x: x in concept)}[kind]()
        t = {"kind": kind, "n": k, "expected": exp, "origin": origin, "note": note,
             "concept": concept, "results": {}}
        tests.append(t)
        live = [c for c in cands if cands[c]["status"] == "live"]

        def check(c: str) -> tuple[bool, str, str]:
            if kind == "holds":
                ok, txt = kernel_check(c, src[c], k, exp)
                return ok, txt, f"at n = {k} the proposer says the claim {'holds' if exp else 'fails'}"
            if kind == "covers":
                ok, txt = kernel_check(c, cfs[c], k, not exp)
                return ok, "-- with every helper predicate made empty (the counterfactual)\n" + txt, (
                    f"the proposer says the conjecture {'says something' if exp else 'says nothing'}"
                    f" at n = {k}; this candidate's coverage disagrees")
            if kind == "witness":
                ok, txt = probe_check(c, src[c], concept, k, exp)
                return ok, txt, (f"the proposer says that with only {set(concept)} prime the claim at "
                                 f"n = {k} is {'met' if exp else 'not met'}; this candidate disagrees")
            hs = [h for h, cn in cands_concepts.get(c, {}).items() if cn == concept]
            for h in hs:
                ok, txt = concept_check(c, src[c], h, k, exp)
                if not ok:
                    return False, txt, (f"the proposer says {k} is {'' if exp else 'not '}{concept}; "
                                        f"this candidate's {h} says otherwise")
            return True, "", ""

        def opposite(c: str) -> str:
            """The Lean the kernel accepts for this candidate: the negation of the failed test."""
            if kind == "holds":
                ok, txt = kernel_check(c, src[c], k, not exp)
            elif kind == "covers":
                ok, txt = kernel_check(c, cfs[c], k, exp)
                txt = "-- with every helper predicate made empty (the counterfactual)\n" + txt
            elif kind == "witness":
                ok, txt = probe_check(c, src[c], concept, k, not exp)
            else:
                hs = [h for h, cn in cands_concepts.get(c, {}).items() if cn == concept]
                ok, txt = next((r for r in (concept_check(c, src[c], h, k, not exp) for h in hs) if r[0]),
                               (False, ""))
            return txt if ok else "-- (the kernel could not decide either way)"

        for c, (ok, _txt, why) in zip(live, pool.map(check, live)):
            t["results"][c] = ok
            if not ok:
                discard(c, f"intent-test ({kind})", why, opposite(c))

    for k, note in spec.get("seeds", []):
        apply_test("holds", k, "proposer's seed", note)
        apply_test("covers", k, "proposer's seed", note)

    questions: list[dict] = []

    def next_disagreement() -> tuple[str, int, str, str, str | None] | None:
        live = [c for c in cands if cands[c]["status"] == "live"]
        for kind, key in (("holds", "table"), ("covers", "coverage")):
            for a in live:
                for b in live:
                    ta, tb = cands[a].get(key), cands[b].get(key)
                    if a == b or ta is None or tb is None:
                        continue
                    for k, (x, y) in enumerate(zip(ta, tb)):
                        if x != y and not have(kind, k):
                            return kind, k, a, b, None
        for a in live:
            for b in live:
                for ha, ca in cands_concepts.get(a, {}).items():
                    for hb, cb in cands_concepts.get(b, {}).items():
                        if a == b or ca is None or ca != cb:
                            continue
                        for k, (x, y) in enumerate(zip(helpers[a][ha], helpers[b][hb])):
                            if x != y and not have("concept", k, ca):
                                return "concept", k, a, b, ca
        for a in live:
            for b in live:
                pa, pb = cands[a].get("probes"), cands[b].get("probes")
                if a == b or pa is None or pb is None:
                    continue
                for i, S in enumerate(sets):
                    for k, (x, y) in enumerate(zip(pa[i], pb[i])):
                        if x != y and not have("witness", k, S):
                            return "witness", k, a, b, S
        return None

    while (d := next_disagreement()) is not None:
        kind, k, a, b, concept = d
        asked = ask_text(kind, k, concept)
        answer = {"holds": lambda: oracle(k), "covers": lambda: covered(k),
                  "concept": lambda: CONCEPTS[concept](k),
                  "witness": lambda: reading(k, lambda x: x in concept)}[kind]()
        questions.append({"kind": kind, "n": k, "between": [a, b], "asked": asked, "answer": answer,
                          "concept": list(concept) if isinstance(concept, tuple) else concept})
        apply_test(kind, k, "question", f"{a} and {b} disagree", concept)

    # pairs over every candidate that compiled and was not screened out (the page shows them all)
    pairable = [c for c in cands if cands[c].get("table") is not None and not cands[c].get("screen", {}).get("proved")]
    jobs_list = [(a, b) for a in pairable for b in pairable if a != b]
    pairs: dict[str, dict] = {}

    def do_pair(ab: tuple[str, str]) -> tuple[str, dict]:
        a, b = ab
        ta, tb = cands[a]["table"], cands[b]["table"]
        for k, (x, y) in enumerate(zip(ta, tb)):
            if x and not y:
                ok, _ = lean(wrap(a, src[a]) + wrap(b, src[b]) +
                             f"example : {ns(a)}.claim {k} ∧ ¬ {ns(b)}.claim {k} := by decide +kernel\n")
                if ok:
                    return f"{a}→{b}", {"state": "refuted", "n": k,
                                        "lean": f"example : A.claim {k} ∧ ¬ B.claim {k} := by decide +kernel"}
        return f"{a}→{b}", direction(a, src[a], b, src[b], ex.get(f"dir--{a}--{b}"))

    for key, val in pool.map(do_pair, jobs_list):
        pairs[key] = val

    def cluster() -> tuple[list[list[str]], list[str]]:
        """Clusters among survivors (both directions proved); flags on the ones outside the main."""
        live = [c for c in cands if cands[c]["status"] == "live"]
        # connected components of "both directions proved": equivalence is transitive, so a chain
        # of proved pairs puts its ends in one cluster even where their own pair is open
        parent = {c: c for c in live}

        def root(c: str) -> str:
            while parent[c] != c:
                c = parent[c]
            return c

        for a in live:
            for b in live:
                if a < b and pairs[f"{a}→{b}"]["state"] == "proved" and pairs[f"{b}→{a}"]["state"] == "proved":
                    parent[root(a)] = root(b)
        groups: dict[str, list[str]] = {}
        for c in live:
            groups.setdefault(root(c), []).append(c)
        clusters = sorted(groups.values(), key=len, reverse=True)
        main = next((cl for cl in clusters if "human-ref" in cl), clusters[0])
        for c in cands:
            cands[c].pop("flag", None)
            cands[c].pop("cluster", None)
        for c in live:
            cands[c]["cluster"] = clusters.index(main) if c in main else next(
                i for i, cl in enumerate(clusters) if c in cl)
            if c in main:
                continue
            r = "human-ref" if "human-ref" in main else main[0]
            fwd, back = pairs[f"{r}→{c}"]["state"], pairs[f"{c}→{r}"]["state"]
            rel = ("weaker" if fwd == "proved" and back != "proved" else
                   "stronger" if back == "proved" and fwd != "proved" else None)
            cands[c]["flag"] = (f"not shown equivalent to the main cluster: {rel} than {r} by proof, "
                                "the other direction open" if rel else
                                f"not shown equivalent to the main cluster ({r}): no direction proved")
        return clusters, main

    clusters, main = cluster()

    # mutation of the main cluster's human reference (or its first member)
    base = "human-ref" if "human-ref" in main else main[0]
    muts = mutants(src[base])

    def do_mut(item: tuple[str, str]) -> dict:
        label, msrc = item
        mid = "mutant"
        t = table(mid, msrc, n_max)
        if t is None:
            return {"mutation": label, "result": "does not elaborate"}
        for tt in tests:
            if tt["kind"] == "holds":
                ok, _ = kernel_check(mid, msrc, tt["n"], tt["expected"])
            elif tt["kind"] == "covers":
                ok, _ = kernel_check(mid, counterfactual(msrc), tt["n"], not tt["expected"])
            elif tt["kind"] == "witness":
                ok, _ = probe_check(mid, msrc, tuple(tt["concept"]), tt["n"], tt["expected"])
            else:
                continue  # mutants change the claim only, never a helper
            if not ok:
                return {"mutation": label, "result": "caught",
                        "by": f"intent test ({tt['kind']}) n = {tt['n']}"}
        s = screen(mid, msrc, None)
        if s["proved"]:
            return {"mutation": label, "result": "caught", "by": "screen"}
        cov = table(mid, counterfactual(msrc), n_max)
        for kind, mine, theirs in (("holds", t, cands[base]["table"]),
                                   ("covers", cov, cands[base]["coverage"])):
            for k, (x, y) in enumerate(zip(mine or [], theirs or [])):
                if x != y:
                    return {"mutation": label, "result": "caught",
                            "by": f"would raise a question ({kind}) at n = {k}", "new_question": [kind, k, None]}
        mp = probe_tables(mid, msrc, sets, n_probe)
        for i, S in enumerate(sets):
            for k, (x, y) in enumerate(zip((mp or [[]] * len(sets))[i], cands[base]["probes"][i])):
                if x != y:
                    return {"mutation": label, "result": "caught",
                            "by": f"would raise a question (witness {set(S)}) at n = {k}",
                            "new_question": ["witness", k, list(S)]}
        f = direction(mid, msrc, base, src[base])["state"]
        b = direction(base, src[base], mid, msrc)["state"]
        if f == "proved" and b == "proved":
            return {"mutation": label, "result": "equivalent"}
        return {"mutation": label, "result": "missed",
                "by": f"same truth values for n ≤ {n_max}; mutant→ref {f}, ref→mutant {b}"}

    mut_results = list(pool.map(do_mut, muts))
    for m, (_, msrc) in zip(mut_results, muts):
        m["claim"] = claim_text(msrc)
    # a mutant the tests could not tell from the reference raises its question: ask it, and let the
    # answer re-check every live candidate (stage 6 feeds stage 5)
    for m in mut_results:
        if "new_question" in m:
            kind, k, S = m["new_question"]
            key = tuple(S) if S is not None else None
            if not have(kind, k, key):
                answer = {"holds": lambda: oracle(k), "covers": lambda: covered(k),
                          "witness": lambda: reading(k, lambda x: x in key)}[kind]()
                questions.append({"kind": kind, "n": k, "between": [base, "mutant"], "answer": answer,
                                  "asked": ask_text(kind, k, key),
                                  "concept": S, "from_mutant": m["mutation"]})
                apply_test(kind, k, "question", f"mutant {m['mutation']}", key)
    clusters, main = cluster()
    pool.shutdown()

    return {"words": spec["words"], "n_max": n_max, "candidates": cands, "tests": tests,
            "questions": questions, "pairs": pairs, "clusters": clusters,
            "mutation_base": base, "mutants": mut_results}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--jobs", type=int, default=6)
    args = ap.parse_args()
    manifest = json.loads((HERE / "manifest.json").read_text())
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    path = out / "results.json"
    results = json.loads(path.read_text()) if path.exists() else {}
    for conj, spec in manifest.items():
        if conj.startswith("_") or (args.only and conj != args.only):
            continue
        print(f"== {conj}", file=sys.stderr, flush=True)
        results[conj] = run(conj, spec, args.n, args.jobs)
        path.write_text(json.dumps(results, indent=1, ensure_ascii=False))
    print(json.dumps({c: {k: v["status"] + (" @" + v.get("stage", "") if v["status"] != "live" else "")
                          for k, v in r["candidates"].items()} for c, r in results.items()},
                     indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
