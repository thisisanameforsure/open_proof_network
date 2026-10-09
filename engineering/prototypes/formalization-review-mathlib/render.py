"""Draw ``out/results.json`` as the review's evidence page: ``out/review.html``.

    python3 render.py
"""

from __future__ import annotations

import html
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
# one stylesheet for both prototypes, loaded by path: both files are called render.py
_spec = importlib.util.spec_from_file_location("round_render", HERE.parent / "formalization-round" / "render.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
CSS = _mod.CSS

R = json.loads((HERE / "out" / "results.json").read_text())
M = json.loads((HERE / "manifest.json").read_text())


def e(s: object) -> str:
    return html.escape(str(s))


def main_of(t: str) -> list[str]:
    return next(cl for cl in R[t]["clusters"] if "incumbent" in cl)


def outcome(t: str, cid: str, v: dict) -> str:
    if v["status"] == "live" and cid in main_of(t):
        return '<span class="pill ok">survives · main cluster</span>'
    if v["status"] == "live":
        return '<span class="pill warn">flagged for the signers</span>'
    if v["status"] == "returned":
        return '<span class="pill warn">returned · format</span>'
    return f'<span class="pill bad">discarded · {e(v["stage"])}</span>'


def as_expected(t: str, cid: str, v: dict) -> bool:
    exp = M[t]["candidates"][cid]["expect"]
    in_main = v["status"] == "live" and cid in main_of(t)
    return {"survive": in_main,
            "discard-compile": v["status"] == "discarded" and v.get("stage") == "compile",
            "discard-question": v["status"] == "discarded" and str(v.get("stage", "")).startswith("question")
            }.get(exp, not in_main)


def section(t: str) -> str:
    r, man = R[t], M[t]
    cands = r["candidates"]
    planted = [c for c in cands if man["candidates"][c]["author"] == "planted"]
    caught = [c for c in planted if as_expected(t, c, cands[c])]
    discarded = [c for c in planted if cands[c]["status"] == "discarded"]
    meaningful = [m for m in r["mutants"] if m["result"] in ("caught", "missed")]
    out = [f'<h2 id="{t}">{t}</h2><p class="words">“{e(man["words"])}”</p>',
           '<div class="grid">'
           f'<div class="stat"><b>{len(cands)}</b><span>candidate versions</span></div>'
           f'<div class="stat"><b>{len(caught)} / {len(planted)}</b><span>planted defects caught '
           f'({len(discarded)} discarded, {len(caught) - len(discarded)} flagged)</span></div>'
           f'<div class="stat"><b>{len(main_of(t))}</b><span>versions in the surviving cluster</span></div>'
           f'<div class="stat"><b>{len(r["questions"])}</b><span>questions to the proposer</span></div>'
           f'<div class="stat"><b>{sum(m["result"] == "caught" for m in meaningful)} / {len(meaningful)}</b>'
           '<span>mutants caught</span></div></div>']
    out.append("<h3>1 · Candidates</h3><div class='wrap'><table><tr><th>Version</th><th>Author</th>"
               "<th>Planted defect</th><th>Outcome</th><th>Why, with the Lean that decided it</th><th>As expected</th></tr>")
    for cid, v in cands.items():
        mm = man["candidates"][cid]
        who = mm.get("who") or (mm["author"] + (f" ({mm['model']})" if mm.get("model") else ""))
        why = e(v.get("reason") or v.get("flag") or "equivalent to the incumbent by proved pairs")
        ex = f"<pre>{e(v['exhibit'])}</pre>" if v.get("exhibit") else ""
        note = f"<div class='mut'>{e(mm['note'])}</div>" if mm.get("note") else ""
        changed = f"<div class='mut'>expectation revised: {e(mm['expect_changed'])}</div>" if mm.get("expect_changed") else ""
        ok = as_expected(t, cid, v)
        out.append(f"<tr><td><code>{e(cid)}</code></td><td>{e(who)}</td><td>{e(mm.get('defect', '—'))}</td>"
                   f"<td>{outcome(t, cid, v)}</td><td>{why}{ex}{note}{changed}</td>"
                   f"<td><span class='pill {'ok' if ok else 'bad'}'>{'yes' if ok else 'no'}</span></td></tr>")
    out.append("</table></div><h3>2 · Questions the proposer answered</h3>")
    if r["questions"]:
        out.append("<div class='wrap'><table><tr><th>Question</th><th>Raised by</th><th>Answer</th></tr>")
        for q in r["questions"]:
            ans = q["answer"] if not isinstance(q["answer"], bool) else ("yes" if q["answer"] else "no")
            out.append(f"<tr><td>{e(q['asked'])}</td><td class='mut'>{e(' vs '.join(q['between']))}</td>"
                       f"<td><b>{e(ans)}</b></td></tr>")
        out.append("</table></div>")
    else:
        out.append("<p class='mut'>None: every live candidate agreed on every sampled value.</p>")
    live = [c for c in cands if cands[c]["status"] == "live"]
    out.append("<h3>3 · Pairs among the survivors: does the row imply the column?</h3><p class='legend'>"
               "<span class='pill ok'>P</span> proved by a small tactic budget · <span class='pill ok'>P*</span> proved by "
               "an agent's exhibit · <span class='pill bad'>✕</span> the row contradicts the column (proved) · "
               "<span class='pill warn'>?</span> open, never recorded as a difference</p>")
    out.append("<div class='wrap'><table class='mx'><tr><th>⇒</th>" + "".join(f"<th>{e(c)}</th>" for c in live) + "</tr>")
    for a in live:
        cells = []
        for b in live:
            if a == b:
                cells.append("<td class='mut'>—</td>")
                continue
            p, x = r["pairs"][f"{a}→{b}:implies"], r["pairs"][f"{a}→{b}:contradicts"]
            cell = ("<span class='pill bad'>✕</span>" if x["state"] == "proved" else
                    "<span class='pill ok'>P*</span>" if p.get("by") == "agent exhibit" else
                    "<span class='pill ok'>P</span>" if p["state"] == "proved" else "<span class='pill warn'>?</span>")
            cells.append(f"<td>{cell}</td>")
        out.append(f"<tr><td><code>{e(a)}</code></td>{''.join(cells)}</tr>")
    out.append("</table></div>")
    out.append("<h3>4 · Mutants of the incumbent's named parts</h3><div class='wrap'><table><tr><th>Change</th>"
               "<th>Result</th><th>How</th></tr>")
    for m in r["mutants"]:
        cls = {"caught": "ok", "missed": "bad"}.get(m["result"], "warn")
        out.append(f"<tr><td><code>{e(m['mutation'])}</code></td><td><span class='pill {cls}'>{e(m['result'])}</span></td>"
                   f"<td class='mut'>{e(key_text(m.get('by', '')))}</td></tr>")
    out.append("</table></div>")
    return "".join(out)


def key_text(s: str) -> str:
    """'domain at (1,)' -> 'domain at 1'; 'iter at (2, 1)' -> 'iter at (2, 1)'."""
    import re
    return re.sub(r"\((\d+),\)", r"\1", s)


def page() -> str:
    ts = [t for t in M if not t.startswith("_")]
    planted = sum(1 for t in ts for x in M[t]["candidates"].values() if x["author"] == "planted")
    caught = sum(1 for t in ts for k, x in M[t]["candidates"].items()
                 if x["author"] == "planted" and as_expected(t, k, R[t]["candidates"][k]))
    nav = "".join(f"<a href='#{t}'>{t}</a>" for t in ts)
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>Formalization review, Mathlib</title><style>{CSS}</style></head><body><main>"
            "<h1>Formalization review — live Mathlib targets</h1>"
            "<p class='sub'>Decisions draft v3.36, second prototype. Three live targets of the graph, every check "
            f"through the network's own <code>POST /check</code> (AXLE, Lean 4.33.1, the target's Mathlib), "
            f"{len(R['_calls'])} calls. The incumbent is the live statement, ported by a wrapper proved equal by "
            "<code>Iff.rfl</code>. The proposer is simulated from the words and, where they are silent, the "
            f"cited source. <b>{caught} of {planted}</b> planted defects caught.</p>"
            f"<nav>{nav}</nav>" + "".join(section(t) for t in ts) + "</main></body></html>")


if __name__ == "__main__":
    (HERE / "out" / "review.html").write_text(page())
    print(HERE / "out" / "review.html")
