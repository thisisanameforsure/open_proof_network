"""F33-T0 measurement 1: the gate tier's fixed battery, one variant at a time, checked on AXLE.

For each surviving mutant (mutants.json from enumerate.py) two Lean files are written:

- ``core``: the variant proved, refuted, and proved equivalent to the candidate's claim, each by
  every tactic of the battery (one theorem per attempt, so AXLE's ``failed_declarations`` says
  which attempts the kernel accepted);
- ``inst``: when the claim opens with a ``∀``, the variant refuted at fixed instances of the first
  binder, and the variant separated from the candidate at each instance (``¬ (PV v ↔ PO v)``).

Files go to ../lean/<n>-<kind>.lean, AXLE's answers to ../raw/<n>-<kind>.json, a summary line per
variant to ../battery.jsonl. Usage: battery.py [first] [last] [workers].
"""

from __future__ import annotations

import concurrent.futures as cf
import json
import re
import sys
import time
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
EVID = HERE.parent
LEAN = EVID / "lean"
RAW = EVID / "raw"
AXLE = "https://axle.axiommath.ai/api/v1/check"
ENV = "lean-4.33.1"
TIMEOUT_S = 300  # the grill's gate-tier cap per check
TACTICS = ["decide", "norm_num", "simp", "simp_all", "omega", "positivity", "aesop", "grind"]
INST_TACTICS = ["decide", "norm_num", "simp", "simp_all", "aesop", "grind"]
HB = "set_option maxHeartbeats 200000 in\n"

EUCLID_DEFS = (
    "def Opn.Divides (a b : Nat) : Prop := ∃ c : Nat, b = a * c\n"
    "def Opn.IsPrime (p : Nat) : Prop := 2 ≤ p ∧ ∀ d : Nat, Opn.Divides d p → d = 1 ∨ d = p\n"
)

VALUES = {
    "ℕ": ["0", "1", "2", "3"],
    "Nat": ["0", "1", "2", "3"],
    "ℤ": ["0", "1", "-1", "2"],
    "ℝ": ["0", "1", "2", "1/2"],
    "Set ℕ": ["∅", "Set.univ", "{0}", "{1}"],
    "Finset ℕ": ["∅", "{0}", "{1}", "{1, 2}"],
    "Finset ℤ": ["∅", "{0}", "{1}", "{1, 2}"],
    "Prop": ["True", "False"],
}


def _close(text: str, i: int) -> int:
    """Index of the bracket closing the one at ``i``."""
    depth = 0
    for j in range(i, len(text)):
        if text[j] in "([{":
            depth += 1
        elif text[j] in ")]}":
            depth -= 1
            if depth == 0:
                return j
    return -1


def leading(prop: str) -> tuple[str, str, str | None, str] | None:
    """The claim's first universally bound variable: (name, type, guard, the rest as a Prop)."""
    m = re.match(r"∀(ᵉ?)\s*", prop)
    if not m:
        return None
    e = m.group(1)
    i = m.end()
    if prop[i] == "(":
        j = _close(prop, i)
        inner = prop[i + 1 : j].strip()
        after = prop[j + 1 :].lstrip()
        g = re.match(r"^(\S+)\s*(>|≥|<|≤)\s*(.+)$", inner)
        if g:
            name, guard, typ = g.group(1), f"{g.group(1)} {g.group(2)} {g.group(3)}", "ℕ"
        else:
            names, _, typ = inner.partition(":")
            names_l = names.split()
            typ = typ.strip()
            name = names_l[0]
            guard = None
            if len(names_l) > 1:
                after = f"({' '.join(names_l[1:])} : {typ}) " + after
                return name, typ, guard, f"∀{e} {after}"
        if after.startswith(","):
            rest = after[1:].strip()
        else:
            rest = f"∀{e} {after}"
        return name, typ, guard, rest
    head, _, rest = prop[i:].partition(",")
    rest = rest.strip()
    g = re.match(r"^(\S+)\s*(>|≥|<|≤)\s*(.+)$", head.strip())
    if g:
        return g.group(1), "ℕ", f"{g.group(1)} {g.group(2)} {g.group(3)}", rest
    names, _, typ = head.partition(":")
    names_l = names.split()
    typ = typ.strip() or "ℕ"
    if len(names_l) > 1:
        return names_l[0], typ, None, f"∀ {' '.join(names_l[1:])} : {typ}, {rest}"
    return names_l[0], typ, None, rest


def pred(lead: tuple[str, str, str | None, str]) -> str:
    name, typ, guard, rest = lead
    body = f"{guard} → {rest}" if guard else rest
    return f"(fun ({name} : {typ}) => {body})"


def _opens(body: str) -> str:
    return "\n".join(line for line in body.splitlines() if line.startswith("open "))


def _space(tag: str, body: str) -> str:
    return f"namespace {tag}\n{body.strip()}\nend {tag}\n"


def header(r: dict) -> str:
    imports = [i for i in r["imports"] if not i.startswith(("Defs.", "Nodes."))]
    if r["target"] == "euclid-primes" or not imports:
        imports = ["Mathlib"]  # AXLE substitutes import Mathlib for every environment
    lines = [f"import {i}" for i in sorted(set(imports))]
    pre = EUCLID_DEFS if r["target"] == "euclid-primes" else ""
    return "\n".join(lines) + "\n\n" + pre + "\n" + _space("V", r["var_body"]) + "\n" + _space(
        "O", r["orig_body"]
    )


def core_file(r: dict) -> tuple[str, list[str]]:
    parts = [header(r)]
    names = []
    for t in TACTICS:
        for kind, goal, unf in (
            ("prove", "V.opnClaim", "V.opnClaim"),
            ("refute", "¬ V.opnClaim", "V.opnClaim"),
            ("equiv", "V.opnClaim ↔ O.opnClaim", "V.opnClaim O.opnClaim"),
        ):
            n = f"t_{kind}_{t}"
            names.append(n)
            parts.append(f"{HB}theorem {n} : {goal} := by\n  unfold {unf}\n  {t}\n")
    return "\n".join(parts), names


def inst_file(r: dict) -> tuple[str, list[str]] | None:
    lv = leading(r["var_prop"])
    if lv is None or lv[1] not in VALUES:
        return None
    lo = leading(r["orig_prop"])
    sep = lo is not None and lo[0] == lv[0] and lo[1] == lv[1]
    opens = _opens(r["var_body"])
    parts = [header(r), "namespace S", opens, ""]
    names = []
    for k, v in enumerate(VALUES[lv[1]]):
        for t in INST_TACTICS:
            n = f"i_refute_{k}_{t}"
            names.append(n)
            parts.append(
                f"{HB}theorem {n} : ¬ V.opnClaim := by\n  unfold V.opnClaim\n  intro h\n"
                f"  have hv := h ({v} : {lv[1]})\n  {t}\n"
            )
            if sep:
                n = f"i_sep_{k}_{t}"
                names.append(n)
                parts.append(
                    f"{HB}theorem {n} : ¬ ({pred(lv)} ({v} : {lv[1]}) ↔ "
                    f"{pred(lo)} ({v} : {lo[1]})) := by\n  {t}\n"
                )
    parts.append("end S\n")
    return "\n".join(parts), names


def check(text: str) -> tuple[dict, float]:
    started = time.monotonic()
    for attempt in range(4):
        try:
            resp = httpx.post(
                AXLE,
                json={"content": text, "environment": ENV, "timeout_seconds": TIMEOUT_S},
                timeout=TIMEOUT_S + 60,
            )
            if resp.status_code == 429 or resp.status_code >= 500:
                time.sleep(10 * (attempt + 1))
                continue
            return resp.json(), time.monotonic() - started
        except (httpx.HTTPError, ValueError) as exc:
            last = repr(exc)
            time.sleep(10 * (attempt + 1))
    return {"transport_error": locals().get("last", "status")}, time.monotonic() - started


def accepted(doc: dict, names: list[str]) -> tuple[list[str], bool]:
    """The attempts the kernel accepted, and whether the file as a whole elaborated."""
    if "failed_declarations" not in doc:
        return [], False
    failed = set(doc.get("failed_declarations") or [])
    errs = (doc.get("lean_messages") or {}).get("errors") or []
    # A header error (variant or candidate does not elaborate) fails every theorem with it.
    ok = [n for n in names if n not in failed and not any(f"S.{n}" == x for x in failed)]
    header_ok = not any(x in failed for x in ("V.opnClaim", "O.opnClaim"))
    return ok, header_ok and not (errs and len(ok) == len(names))


def run_one(idx: int, r: dict) -> dict:
    out = {"n": idx, "target": r["target"], "question": r["question"], "cls": r["cls"],
           "label": r["label"], "var_prop": r["var_prop"], "orig_prop": r["orig_prop"]}
    for kind, built in (("core", core_file(r)), ("inst", inst_file(r))):
        if built is None:
            out[kind] = None
            continue
        text, names = built
        (LEAN / f"{idx:03d}-{kind}.lean").write_text(text)
        doc, secs = check(text)
        (RAW / f"{idx:03d}-{kind}.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False))
        ok, header_ok = accepted(doc, names)
        info = doc.get("info") or {}
        out[kind] = {
            "wall_s": round(secs, 1),
            "exec_ms": info.get("execution_time_ms"),
            "accepted": ok,
            "header_ok": header_ok,
            "timeout": "timeout" in json.dumps(doc.get("lean_messages", {})).lower()
            or "LeanTimeout" in json.dumps(doc),
            "attempts": len(names),
            "transport_error": doc.get("transport_error"),
        }
    return out


def main() -> None:
    LEAN.mkdir(exist_ok=True)
    RAW.mkdir(exist_ok=True)
    rows = json.loads((HERE / "mutants.json").read_text())
    first = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    last = int(sys.argv[2]) if len(sys.argv) > 2 else len(rows)
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    done = set()
    out_path = EVID / "battery.jsonl"
    if out_path.exists():
        done = {json.loads(line)["n"] for line in out_path.read_text().splitlines() if line}
    todo = [(i, rows[i]) for i in range(first, min(last, len(rows))) if i not in done]
    with cf.ThreadPoolExecutor(workers) as pool, out_path.open("a") as fh:
        for res in pool.map(lambda a: run_one(*a), todo):
            fh.write(json.dumps(res, ensure_ascii=False) + "\n")
            fh.flush()
            c = res["core"] or {}
            i = res["inst"] or {}
            print(res["n"], res["target"], res["cls"], c.get("wall_s"), c.get("accepted"),
                  i.get("wall_s") if i else "-", i.get("accepted") if i else "-", flush=True)


if __name__ == "__main__":
    main()
