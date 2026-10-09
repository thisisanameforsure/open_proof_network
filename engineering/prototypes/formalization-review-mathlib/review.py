"""A formalization review (decisions draft v3.36) on three live Mathlib targets, through the
network's own fast check (``POST /check``: AXLE, Lean 4.33.1, the target's Mathlib).

Second prototype: the first (``../formalization-round``) ran core Lean on statements of the form
"for every n, claim(n)". The live targets are shaped otherwise ("infinitely many n with P(n)",
"for every k ≥ 2 infinitely many n", a limit), so the format names their parts instead:
``member`` (the predicate the set is built from), ``domain`` (which parameters the conjecture is
about), ``iter`` (σ_k(n) for erdos-410), and ``conj`` (the conjecture as a Prop).

Stages, each through ``POST /check`` and batched to fit its 20 s budget and the anonymous limit:
  compile + tables  each candidate alone, with ``#eval`` printing its member/domain/iter tables
  format            a candidate missing a required name is returned to its author
  screens           agent exhibits proving ``conj`` or ``¬ conj`` (``exhibits/``)
  questions         every disagreement among live candidates' tables is a question; the proposer
                    (simulated from the words and the cited source, in Python) answers; the answer
                    is a ``decide`` test per candidate, and a failing candidate is discarded
  pairs             each direction ``A.conj → B.conj`` (and the contradiction ``A.conj → ¬ B.conj``)
                    tried with a small budget after matching the named parts
  mutation          single-site changes to the incumbent's member/domain/iter, caught if their
                    tables differ from the proposer's answers

    python3 review.py [--only erdos-1003]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from math import factorial
from pathlib import Path

import axle

HERE = Path(__file__).resolve().parent
MAX_CALLS = 160


# --- the proposer, simulated: the words (and, where they are silent, the cited source) ------------


def phi(n: int) -> int:
    if n == 0:
        return 0
    from math import gcd
    return sum(1 for i in range(1, n + 1) if gcd(i, n) == 1)


def sigma(n: int) -> int:
    return 0 if n == 0 else sum(d for d in range(1, n + 1) if n % d == 0)


def sigma_k(n: int, k: int) -> int:
    for _ in range(k):
        n = sigma(n)
    return n


#: Each table: its Lean expression per key, the keys sampled, and the proposer's answer per key.
TABLES = {
    "erdos-1003": {
        "member": {"keys": [(n,) for n in range(31)], "lean": "member {0}",
                   "answer": lambda n: phi(n) == phi(n + 1),
                   "ask": "Is n = {0} a solution, that is, φ({0}) = φ({0}+1)?"},
    },
    "erdos-727": {
        "domain": {"keys": [(k,) for k in range(6)], "lean": "domain {0}",
                   "answer": lambda k: k >= 2,
                   "ask": "Is k = {0} one of the k the conjecture is about?"},
        "member": {"keys": [(k, n) for k in (1, 2, 3) for n in range(21)], "lean": "member {0} {1}",
                   "answer": lambda k, n: factorial(2 * n) % (factorial(n + k) ** 2) == 0,
                   "ask": "For k = {0}, n = {1}: does ((n+k)!)² divide (2n)!?"},
    },
    "erdos-410": {
        "domain": {"keys": [(n,) for n in range(6)], "lean": "domain {0}",
                   "answer": lambda n: n >= 2,
                   "ask": "Is n = {0} one of the n the conjecture is about? (The words are silent; "
                          "the source, Erdős–Granville–Pomerance–Spiro 1990, takes n ≥ 2, and at "
                          "n = 1 every σ_k(1) is 1.)"},
        "iter": {"keys": [(n, k) for n in range(1, 7) for k in (1, 2, 3)], "lean": "iter {0} {1}",
                 "answer": lambda n, k: sigma_k(n, k),
                 "ask": "What is σ_{1}({0}) in the problem's indexing (σ_1 = σ)?"},
    },
}
REQUIRED = {"erdos-1003": ["member", "conj"], "erdos-727": ["domain", "member", "conj"],
            "erdos-410": ["domain", "iter", "conj"]}


# --- Lean text ------------------------------------------------------------------------------------


def ns(cid: str) -> str:
    return "C_" + re.sub(r"[^A-Za-z0-9]", "_", cid)


def wrap(cid: str, src: str) -> str:
    """The candidate in its own namespace; ``open`` lines move out of it, as Lean wants them first."""
    opens = [ln for ln in src.splitlines() if ln.startswith("open ")]
    body = "\n".join(ln for ln in src.splitlines() if not ln.startswith("open "))
    return "\n".join(opens) + f"\nnamespace {ns(cid)}\n{body.strip()}\nend {ns(cid)}\n"


def defs_of(src: str) -> list[str]:
    return re.findall(r"^def\s+(\w+)", src, flags=re.M)


def call(target: str, text: str) -> dict:
    if len(axle.CALLS) >= MAX_CALLS:
        raise SystemExit(f"call budget of {MAX_CALLS} spent")
    out = axle.check(target, text)
    if "http_error" in out:
        print(f"  ! HTTP {out['http_error']}: {out['body'][:300]}", file=sys.stderr)
    return out


def failed(out: dict) -> set[str]:
    return set((out.get("result") or {}).get("failed_declarations") or [])


def lit(v: object) -> str:
    return "true" if v is True else "false" if v is False else str(v)


# --- stages ---------------------------------------------------------------------------------------


def compile_and_tables(target: str, cid: str, src: str) -> dict:
    tabs = TABLES[target]
    lines = [wrap(cid, src)]
    for name, t in tabs.items():
        exprs = ", ".join(
            (f"toString (decide ({ns(cid)}.{t['lean'].format(*key)}))" if name != "iter"
             else f"toString ({ns(cid)}.{t['lean'].format(*key)})")
            for key in t["keys"])
        lines.append(f'#eval IO.println ("TABLE:{name}:" ++ String.intercalate "," [{exprs}])')
    out = call(target, "\n".join(lines) + "\n")
    m = axle.messages(out)
    got: dict[str, list[str]] = {}
    for info in m["infos"]:
        mm = re.search(r"TABLE:(\w+):([^\n]*)", info)
        if mm:
            got[mm.group(1)] = mm.group(2).split(",")
    return {"ok": bool(out.get("okay")) and not m["errors"], "errors": m["errors"][:3],
            "tables": {k: [v.strip() for v in vs] for k, vs in got.items()}}


def tables_many(target: str, items: list[tuple[str, str]]) -> list[dict]:
    """Several candidates' tables in one call; a candidate whose tables do not all print failed."""
    tabs = TABLES[target]
    lines = []
    for cid, src in items:
        lines.append(wrap(cid, src))
        for name, t in tabs.items():
            exprs = ", ".join(
                (f"toString (decide ({ns(cid)}.{t['lean'].format(*key)}))" if name != "iter"
                 else f"toString ({ns(cid)}.{t['lean'].format(*key)})")
                for key in t["keys"])
            lines.append(f'#eval IO.println ("TABLE:{cid}:{name}:" ++ String.intercalate "," [{exprs}])')
    out = call(target, "\n".join(lines) + "\n")
    got: dict[str, dict[str, list[str]]] = {}
    for info in axle.messages(out)["infos"]:
        mm = re.search(r"TABLE:([\w-]+):(\w+):([^\n]*)", info)
        if mm:
            got.setdefault(mm.group(1), {})[mm.group(2)] = [v.strip() for v in mm.group(3).split(",")]
    return [{"ok": set(got.get(cid, {})) == set(tabs), "tables": got.get(cid, {})} for cid, _ in items]


def run(target: str, man: dict) -> dict:
    cdir = HERE / "candidates" / target
    src = {p.stem: p.read_text() for p in sorted(cdir.glob("*.lean"))}
    meta = man["candidates"]
    cands = {c: {**meta.get(c, {"author": "unknown"}), "id": c, "status": "live"} for c in src}
    exhibits = {p.stem: p.read_text() for p in (HERE / "exhibits" / target).glob("*.lean")} if (
        HERE / "exhibits" / target).exists() else {}

    def discard(c: str, stage: str, reason: str, lean: str = "") -> None:
        if cands[c]["status"] == "live":
            cands[c].update(status="discarded", stage=stage, reason=reason, exhibit=lean)

    # format, compile, tables
    for c in src:
        missing = [n for n in REQUIRED[target] if n not in defs_of(src[c])]
        if missing:
            cands[c].update(status="returned", stage="format",
                            reason=f"missing the format's names {missing}; returned to its author")
            continue
        r = compile_and_tables(target, c, src[c])
        cands[c]["tables"] = r["tables"]
        if not r["ok"] or set(r["tables"]) != set(TABLES[target]):
            discard(c, "compile", "does not elaborate, or a table could not be evaluated",
                    "\n".join(r["errors"]))
        print(f"  {c}: {cands[c]['status']}", file=sys.stderr, flush=True)

    # screens: agent exhibits proving the conjecture (too easy to be the open problem) or its
    # negation (false as stated: routed to a person in the real review; here, the proposer's
    # source says the conjecture is open, so a refutation of a candidate is a misformalization)
    for c, ex in exhibits.items():
        if c not in cands or cands[c]["status"] != "live":
            continue
        out = call(target, wrap(c, src[c] + "\n" + ex))
        ok = bool(out.get("okay")) and not axle.messages(out)["errors"]
        cands[c]["screen"] = {"exhibit": ex.strip(), "accepted": ok}
        if ok:
            what = "its negation" if "¬" in ex.split(":=")[0] else "the statement itself"
            discard(c, "screen", f"an agent proved {what} in a few lines: as written it is not the "
                                 "open conjecture", ex.strip())

    # questions from table disagreements, answered by the proposer, tested per candidate
    tests: list[dict] = []
    questions: list[dict] = []
    tabs = TABLES[target]

    def have(name: str, key: tuple) -> bool:
        return any(t["table"] == name and tuple(t["key"]) == key for t in tests)

    while True:
        live = [c for c in cands if cands[c]["status"] == "live"]
        new = None
        for name, t in tabs.items():
            for i, key in enumerate(t["keys"]):
                vals = {cands[c]["tables"][name][i] for c in live}
                if len(vals) > 1 and not have(name, key):
                    new = (name, i, key)
                    break
            if new:
                break
        if not new:
            break
        name, i, key = new
        t = tabs[name]
        ans = t["answer"](*key)
        between = sorted({cands[c]["tables"][name][i]: c for c in live}.values())
        questions.append({"table": name, "key": list(key), "asked": t["ask"].format(*key),
                          "answer": ans, "between": between})
        expr = t["lean"].format(*key)
        prop = (lambda c: f"{ns(c)}.{expr} = {ans}") if name == "iter" else (
            lambda c: f"{ns(c)}.{expr}" if ans else f"¬ {ns(c)}.{expr}")
        text = "".join(wrap(c, src[c]) for c in live) + "".join(
            f"theorem test_{ns(c)} : {prop(c)} := by decide\n" for c in live)
        out = call(target, text)
        fails = failed(out)
        res = {c: f"test_{ns(c)}" not in fails for c in live}
        tests.append({"table": name, "key": list(key), "expected": ans, "results": res})
        for c, ok in res.items():
            if not ok:
                mine = cands[c]["tables"][name][i]
                discard(c, f"question ({name})",
                        f"asked “{t['ask'].format(*key)}” the proposer answers {lit(ans)}; this "
                        f"candidate's {name} gives {mine}",
                        f"-- the kernel's decision (decide) on this candidate:\n-- {expr} = {mine}")

    # pairs among the survivors: match the named parts, then compare the conjectures
    live = [c for c in cands if cands[c]["status"] == "live"]
    pairs: dict[str, dict] = {}
    directions = [(a, b, kind) for a in live for b in live if a != b for kind in ("implies", "contradicts")]
    names = [n for n in REQUIRED[target] if n != "conj"]

    def links(a: str, b: str, tag: str) -> tuple[str, list[str]]:
        """Lemmas rewriting B's named parts into A's, each tried with a few tactics."""
        text, names_ok = "", []
        for n in names:
            arity = len(next(iter(tabs[n]["keys"])) if n in tabs else (1,))
            xs = " ".join(f"x{i}" for i in range(arity))
            stmt = (f"∀ {xs}, {ns(b)}.{n} {xs} = {ns(a)}.{n} {xs}" if n == "iter"
                    else f"∀ {xs}, {ns(b)}.{n} {xs} ↔ {ns(a)}.{n} {xs}")
            text += (f"theorem link_{tag}_{n} : {stmt} := by\n  intro {xs}\n  first\n"
                     f"  | rfl\n  | simp only [{ns(a)}.{n}, {ns(b)}.{n}]\n"
                     f"  | (simp only [{ns(a)}.{n}, {ns(b)}.{n}]; omega)\n"
                     f"  | (simp [{ns(a)}.{n}, {ns(b)}.{n}]; done)\n"
                     f"  | (induction x1 <;> simp_all [{ns(a)}.{n}, {ns(b)}.{n}, Function.iterate_succ_apply'])\n"
                     f"  | (simp [{ns(a)}.{n}, {ns(b)}.{n}, Nat.factorial, sq, two_mul])\n")
            names_ok.append(f"link_{tag}_{n}")
        return text, names_ok

    def body(a: str, b: str, kind: str, tag: str) -> str:
        lk, ln = links(a, b, tag)
        rw = ", ".join([f"{ns(a)}.conj", f"{ns(b)}.conj", *ln])
        goal = f"{ns(a)}.conj → {ns(b)}.conj" if kind == "implies" else f"{ns(a)}.conj → ¬ {ns(b)}.conj"
        tac = ("intro h\n  simp only [" + rw + "] at *\n  first\n  | exact h\n  | (simpa using h)\n"
               "  | aesop\n  | (intro hb; exact h hb)\n  | (intro hb; exact absurd hb h)\n"
               "  | (rw [Filter.tendsto_atTop_atTop] at *; exact h)\n"
               "  | (simp only [Filter.tendsto_atTop_atTop] at *; exact h)\n"
               "  | (simp only [Set.infinite_iff_exists_gt] at *; exact h)\n"
               "  | (simp only [← Set.infinite_iff_exists_gt] at *; exact h)\n"
               "  | (exact fun n hn => h n hn |>.nonempty |>.elim fun x hx => ⟨n, hn, h n hn⟩)")
        return f"section\n{lk}theorem dir_{tag} : {goal} := by\n  {tac}\nend\n"

    pair_ex = {k: v for k, v in exhibits.items() if k.startswith("dir--")}
    head = "".join(wrap(c, src[c]) for c in live)
    for chunk in [directions[i:i + 6] for i in range(0, len(directions), 6)]:
        tags = {d: f"d{directions.index(d)}" for d in chunk}
        out = call(target, head + "".join(body(a, b, kind, tags[(a, b, kind)]) for a, b, kind in chunk))
        fails = failed(out)
        for d in chunk:
            a, b, kind = d
            ok = f"dir_{tags[d]}" not in fails and (out.get("result") is not None)
            pairs[f"{a}→{b}:{kind}"] = {"state": "proved" if ok else "open", "by": "tactic" if ok else None}
    for key, ex in pair_ex.items():  # an open direction is claimable work: agents' proofs, checked
        _, a, b = key.split("--")
        if a in live and b in live and pairs[f"{a}→{b}:implies"]["state"] == "open":
            out = call(target, "".join(wrap(c, src[c]) for c in (a, b)) + ex)
            if bool(out.get("okay")) and not axle.messages(out)["errors"]:
                pairs[f"{a}→{b}:implies"] = {"state": "proved", "by": "agent exhibit", "lean": ex.strip()}
    for k, v in pairs.items():
        print(f"  pair {k}: {v['state']}", file=sys.stderr, flush=True)

    # clusters: connected components of "implies both ways"
    parent = {c: c for c in live}

    def root(c: str) -> str:
        while parent[c] != c:
            c = parent[c]
        return c

    for a in live:
        for b in live:
            if a < b and pairs[f"{a}→{b}:implies"]["state"] == pairs[f"{b}→{a}:implies"]["state"] == "proved":
                parent[root(a)] = root(b)
    groups: dict[str, list[str]] = {}
    for c in live:
        groups.setdefault(root(c), []).append(c)
    clusters = sorted(groups.values(), key=lambda g: ("incumbent" not in g, -len(g)))
    main = clusters[0] if clusters else []
    for c in live:
        if c in main:
            continue
        r = "incumbent" if "incumbent" in main else main[0]
        fwd, back = pairs[f"{r}→{c}:implies"]["state"], pairs[f"{c}→{r}:implies"]["state"]
        contra = pairs[f"{r}→{c}:contradicts"]["state"] == "proved" or pairs[f"{c}→{r}:contradicts"]["state"] == "proved"
        cands[c]["flag"] = ("contradicts the main cluster, by proof: a structural question for the signers"
                            if contra else
                            f"weaker than {r} by proof; the other direction open" if fwd == "proved" else
                            f"stronger than {r} by proof; the other direction open" if back == "proved" else
                            f"no direction proved against {r}")

    # mutation of the incumbent's named parts
    mutants = mutate(target, src["incumbent"]) if "incumbent" in src else []
    mres = []
    for chunk in [mutants[i:i + 6] for i in range(0, len(mutants), 6)]:
        rs = tables_many(target, [(f"mutant{j}", msrc) for j, (_, msrc) in enumerate(chunk)])
        for (label, msrc), r in zip(chunk, rs):
            if not r["ok"]:
                mres.append({"mutation": label, "result": "does not elaborate"})
                continue
            diff = next(((n, tabs[n]["keys"][i]) for n in tabs for i, v in enumerate(r["tables"][n])
                         if v != lit(tabs[n]["answer"](*tabs[n]["keys"][i]))), None)
            mres.append({"mutation": label, "result": "caught" if diff else "missed",
                         "by": f"{diff[0]} at {diff[1]} disagrees with the proposer" if diff else
                               "every table agrees with the proposer"})

    return {"words": man["words"], "candidates": cands, "tests": tests, "questions": questions,
            "pairs": pairs, "clusters": clusters, "mutants": mres}


SWAPS = [("≥", ">"), (">", "≥"), ("+ k", "+ 1"), ("^ 2", ""), ("2 *", "3 *"), ("n + 1", "n + 2"),
         ("sigma 1", "sigma 0"), ("^[k]", "^[k + 1]")]


def mutate(target: str, src: str) -> list[tuple[str, str]]:
    out = []
    for name in [n for n in REQUIRED[target] if n != "conj"]:
        m = re.search(rf"^def {name}\b.*$", src, flags=re.M)
        if not m:
            continue
        line = m.group(0)
        head, bodyt = line.split(":=", 1)
        for old, new in SWAPS:
            for mm in re.finditer(re.escape(old), bodyt):
                nb = bodyt[:mm.start()] + new + bodyt[mm.end():]
                out.append((f"{name}: {old} → {new or '∅'}", src.replace(line, head + ":=" + nb)))
        for mm in re.finditer(r"\b(\d+)\b", bodyt):
            k = int(mm.group(1))
            for nk in (k - 1, k + 1):
                if nk >= 0:
                    nb = bodyt[:mm.start()] + str(nk) + bodyt[mm.end():]
                    out.append((f"{name}: {k} → {nk}", src.replace(line, head + ":=" + nb)))
    # the port theorem would fail on every mutant (it is about the original); drop it
    return [(lab, re.sub(r"^theorem port.*$", "", s, flags=re.M)) for lab, s in out]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    a = ap.parse_args()
    manifest = json.loads((HERE / "manifest.json").read_text())
    path = HERE / "out" / "results.json"
    path.parent.mkdir(exist_ok=True)
    results = json.loads(path.read_text()) if path.exists() else {}
    for target, man in manifest.items():
        if target.startswith("_") or (a.only and target != a.only):
            continue
        print(f"== {target}", file=sys.stderr, flush=True)
        results[target] = run(target, man)
        results.setdefault("_calls", []).extend(axle.CALLS)
        axle.CALLS.clear()
        path.write_text(json.dumps(results, indent=1, ensure_ascii=False))
    print(json.dumps({t: {c: v["status"] + ("@" + v["stage"] if v.get("stage") else "")
                          for c, v in r["candidates"].items()}
                      for t, r in results.items() if not t.startswith("_")}, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
