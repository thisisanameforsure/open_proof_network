"""Draw ``out/results.json`` as the round's evidence page (draft v3.36 §7): ``out/round.html``.

    python3 render.py
"""

from __future__ import annotations

import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = json.loads((HERE / "out" / "results.json").read_text())
M = json.loads((HERE / "manifest.json").read_text())

CSS = """
:root{--bg:#fbfaf7;--fg:#1d1c1a;--mut:#6b675f;--line:#e2ded5;--card:#fff;--ok:#1f7a4d;--okbg:#e5f3ea;
--bad:#a3342b;--badbg:#f8e6e3;--warn:#8a6100;--warnbg:#fbf0d6;--acc:#2f5d9a;--code:#f3f1ec}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#16161a;--fg:#e9e6df;--mut:#a29e95;
--line:#2e2d33;--card:#1d1d22;--ok:#6fcf97;--okbg:#17301f;--bad:#f08a80;--badbg:#3a1d1a;--warn:#e7c165;
--warnbg:#33290f;--acc:#8fb4ea;--code:#26252b}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,sans-serif}
main{max-width:1180px;margin:0 auto;padding:28px 16px 64px}h1{font-size:26px;margin:0 0 4px}
h2{font-size:21px;margin:40px 0 4px;padding-top:12px;border-top:2px solid var(--line)}h3{font-size:15px;margin:22px 0 8px;color:var(--mut);text-transform:uppercase;letter-spacing:.04em}
.sub{color:var(--mut);margin:0 0 18px}.words{font-size:17px;font-style:italic;margin:6px 0 14px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:14px 0}
.stat{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px}
.stat b{display:block;font-size:24px}.stat span{color:var(--mut);font-size:13px}
.wrap{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:var(--card)}
table{border-collapse:collapse;width:100%;font-size:13.5px}th,td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--mut);font-weight:600;white-space:nowrap}tr:last-child td{border-bottom:0}
code,pre{font:12.5px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--code);border-radius:4px}
code{padding:1px 4px}td:first-child code{white-space:nowrap}pre{margin:4px 0 0;padding:6px 8px;white-space:pre-wrap;word-break:break-word}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;font-weight:600;white-space:nowrap}
.ok{background:var(--okbg);color:var(--ok)}.bad{background:var(--badbg);color:var(--bad)}.warn{background:var(--warnbg);color:var(--warn)}
.mut{color:var(--mut)}.mx td{text-align:center;padding:5px 4px;font-size:12px}.mx th{font-size:11.5px;padding:5px 4px}
.mx td:first-child,.mx th:first-child{text-align:left}.legend{color:var(--mut);font-size:13px;margin:6px 0}
.sign{display:grid;grid-template-columns:1fr 1fr;gap:12px}.slot{border:1px dashed var(--line);border-radius:8px;padding:14px;background:var(--card)}
@media (max-width:640px){.sign{grid-template-columns:1fr}}
nav a{color:var(--acc);margin-right:14px}
"""


def e(s: object) -> str:
    return html.escape(str(s))


def outcome(cj: str, cid: str, v: dict) -> str:
    main = next(cl for cl in R[cj]["clusters"] if "human-ref" in cl)
    if v["status"] == "live" and cid in main:
        return '<span class="pill ok">survives · main cluster</span>'
    if v["status"] == "live":
        return '<span class="pill warn">flagged</span>'
    if v["status"] == "returned":
        return '<span class="pill warn">returned to author · format</span>'
    return f'<span class="pill bad">discarded · {e(v["stage"])}</span>'


def expected_ok(cj: str, cid: str, v: dict) -> bool:
    exp = M[cj]["candidates"][cid]["expect"]
    main = next(cl for cl in R[cj]["clusters"] if "human-ref" in cl)
    in_main = v["status"] == "live" and cid in main
    if exp == "survive":
        return in_main
    if exp == "discard-compile":
        return v["status"] == "discarded" and v["stage"] == "compile"
    if exp == "returned":
        return v["status"] == "returned"
    return not in_main


def section(cj: str) -> str:
    r, man = R[cj], M[cj]
    cands = r["candidates"]
    planted = [c for c in cands if man["candidates"][c]["author"] == "planted"]
    caught = [c for c in planted if expected_ok(cj, c, cands[c])]
    muts = r["mutants"]
    meaningful = [m for m in muts if m["result"] in ("caught", "missed")]
    out = [f'<h2 id="{cj}">{cj.capitalize()}</h2><p class="words">“{e(man["words"])}”</p>']
    out.append('<div class="grid">'
               f'<div class="stat"><b>{len(cands)}</b><span>candidate versions</span></div>'
               f'<div class="stat"><b>{len(caught)} / {len(planted)}</b><span>planted defects caught</span></div>'
               f'<div class="stat"><b>{len(r["clusters"][0]) if r["clusters"] else 0}</b><span>versions in the surviving cluster</span></div>'
               f'<div class="stat"><b>{len(r["questions"])}</b><span>questions to the proposer</span></div>'
               f'<div class="stat"><b>{sum(m["result"]=="caught" for m in meaningful)} / {len(meaningful)}</b><span>meaning-changing mutants caught</span></div>'
               '</div>')

    out.append("<h3>1 · Candidates</h3><div class='wrap'><table><tr><th>Version</th><th>Author</th>"
               "<th>Planted defect</th><th>Outcome</th><th>Why, with the Lean that decided it</th><th>As expected</th></tr>")
    for cid, v in cands.items():
        mm = man["candidates"][cid]
        who = mm["author"] + (f" ({mm['model']})" if mm.get("model") else "")
        why = e(v.get("reason") or v.get("flag") or ("equivalent to the reference by proved pairs" if v["status"] == "live" else ""))
        ex = f"<pre>{e(v['exhibit'])}</pre>" if v.get("exhibit") else ""
        okp = expected_ok(cj, cid, v)
        changed = f"<div class='mut'>expectation revised: {e(mm['expect_changed'])}</div>" if mm.get("expect_changed") else ""
        out.append(f"<tr><td><code>{e(cid)}</code></td><td>{e(who)}</td><td>{e(mm.get('defect', '—'))}</td>"
                   f"<td>{outcome(cj, cid, v)}</td><td>{why}{ex}{changed}</td>"
                   f"<td>{'<span class=\"pill ok\">yes</span>' if okp else '<span class=\"pill bad\">no</span>'}</td></tr>")
    out.append("</table></div>")

    out.append("<h3>2 · Questions the proposer answered</h3>")
    if r["questions"]:
        out.append("<div class='wrap'><table><tr><th>Kind</th><th>Question</th><th>Raised by</th><th>Answer</th></tr>")
        for q in r["questions"]:
            out.append(f"<tr><td>{e(q['kind'])}</td><td>{e(q['asked'])}</td><td class='mut'>{e(' vs '.join(q['between']))}"
                       f"{(' · ' + e(q['from_mutant'])) if q.get('from_mutant') else ''}</td>"
                       f"<td>{'<b>yes</b>' if q['answer'] else '<b>no</b>'}</td></tr>")
        out.append("</table></div>")
    else:
        out.append("<p class='mut'>None needed beyond the seeds.</p>")

    tests = r["tests"]
    live_all = list(cands)
    out.append("<h3>3 · Intent tests × versions</h3><p class='legend'>Each cell is a kernel decision "
               "(<code>decide +kernel</code>). ✓ agrees with the proposer, ✗ disagrees (the version is discarded there), · not run (already discarded).</p>")
    out.append("<div class='wrap'><table class='mx'><tr><th>test</th>" + "".join(
        f"<th>{e(c)}</th>" for c in live_all) + "</tr>")
    for t in tests:
        lab = f"{t['kind']} n={t['n']}" + (f" {set(t['concept'])}" if t["kind"] == "witness" else
                                           f" ({t['concept']})" if t["kind"] == "concept" else "")
        cells = "".join(
            "<td>" + ("<span class='pill ok'>✓</span>" if t["results"].get(c) is True else
                      "<span class='pill bad'>✗</span>" if t["results"].get(c) is False else "·") + "</td>"
            for c in live_all)
        out.append(f"<tr><td><code>{e(lab)}</code> <span class='mut'>{e(t['origin'])}</span></td>{cells}</tr>")
    out.append("</table></div>")

    pv = [c for c in cands if cands[c].get("table") is not None and not cands[c].get("screen", {}).get("proved")]
    out.append("<h3>4 · Pairs: does the row imply the column?</h3><p class='legend'>"
               "<span class='pill ok'>P</span> proved (tactic) · <span class='pill ok'>P*</span> proved by an agent's exhibit · "
               "<span class='pill bad'>R</span> refuted by a kernel-checked instance · <span class='pill warn'>?</span> open (never recorded as a refutation)</p>")
    out.append("<div class='wrap'><table class='mx'><tr><th>⇒</th>" + "".join(f"<th>{e(c)}</th>" for c in pv) + "</tr>")
    for a in pv:
        row = []
        for b in pv:
            if a == b:
                row.append("<td class='mut'>—</td>")
                continue
            p = r["pairs"][f"{a}→{b}"]
            row.append("<td>" + {"proved": "<span class='pill ok'>P*</span>" if p.get("by") == "agent exhibit" else "<span class='pill ok'>P</span>",
                                 "refuted": f"<span class='pill bad' title='n = {p.get('n')}'>R{p.get('n')}</span>",
                                 "open": "<span class='pill warn'>?</span>"}[p["state"]] + "</td>")
        out.append(f"<tr><td><code>{e(a)}</code></td>{''.join(row)}</tr>")
    out.append("</table></div>")

    out.append(f"<h3>5 · Mutants of <code>{e(r['mutation_base'])}</code></h3><div class='wrap'><table>"
               "<tr><th>Change</th><th>Result</th><th>How</th></tr>")
    for m in muts:
        cls = {"caught": "ok", "equivalent": "ok", "missed": "bad"}.get(m["result"], "warn")
        out.append(f"<tr><td><code>{e(m['mutation'])}</code></td><td><span class='pill {cls}'>{e(m['result'])}</span></td>"
                   f"<td class='mut'>{e(m.get('by', ''))}</td></tr>")
    out.append("</table></div>")

    out.append("<h3>6 · Signatures</h3><div class='sign'><div class='slot'><b>Intent signer</b><p class='mut'>"
               "The proposer: answered the questions above. Not signed (prototype).</p></div><div class='slot'><b>Independent signer</b>"
               "<p class='mut'>Reads Lean, wrote nothing in the surviving cluster. Not signed (prototype).</p></div></div>")
    return "".join(out)


def page() -> str:
    conjs = [c for c in M if not c.startswith("_")]
    planted = sum(1 for c in conjs for x in M[c]["candidates"].values() if x["author"] == "planted")
    caught = sum(1 for c in conjs for k, x in M[c]["candidates"].items()
                 if x["author"] == "planted" and expected_ok(c, k, R[c]["candidates"][k]))
    nav = "".join(f"<a href='#{c}'>{c.capitalize()}</a>" for c in conjs)
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>Formalization round</title><style>{CSS}</style></head><body><main>"
            "<h1>Formalization round — prototype evidence</h1>"
            "<p class='sub'>Decisions draft v3.36. Core Lean 4.33.1, no Mathlib. Candidates written by people, by three blind agents "
            "(Sonnet, Haiku, Opus) and planted with one known defect each. The proposer is simulated by a Python reading of the "
            f"words, independent of every candidate. <b>{caught} of {planted}</b> planted defects caught.</p>"
            f"<nav>{nav}</nav>" + "".join(section(c) for c in conjs) + "</main></body></html>")


if __name__ == "__main__":
    (HERE / "out" / "round.html").write_text(page())
    print(HERE / "out" / "round.html")
