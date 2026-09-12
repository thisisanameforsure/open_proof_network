#!/usr/bin/env python3
"""Build docs/seed_conjecture_sources.html: the seed-conjecture research report plus a
per-problem catalog of every Erdős problem that has a Lean statement in
google-deepmind/formal-conjectures, joined with erdosproblems.com, the Erdős-problems AI
wiki, Epoch's FrontierMath Erdős selection, AlphaProof Nexus attempts, the registry's
misformalization issues and its git history.

Inputs (all public; fetched into a work directory, see `--work`):
  fc/                      shallow clone of google-deepmind/formal-conjectures (HEAD = pin)
  fc_file_history.txt      `git log --format='COMMIT %H %cI' --name-status --diff-filter=AMR -- FormalConjectures`
  fc_misform_issues.json   `gh api --paginate 'repos/google-deepmind/formal-conjectures/issues?labels=misformalization&state=all&per_page=100'`
  ep/data/problems.yaml    teorth/erdosproblems
  epwiki/AI-contributions-to-Erdős-problems.md   teorth/erdosproblems.wiki
  epoch/apn/data/erdos/{ERDOS_PROBLEM_STATEMENT_SELECTION.md,subsets/bloom_selection.json,metadata/snapshots/bloom_top10.json}
  epoch/apn/data/erdos_autoformalized/subsets/bloom_selection.json
  nexus/erdos_problems_attempted.txt, nexus/APNOutputs/ErdosProblems/   google-deepmind/alphaproof-nexus-results
  ep_pages/N.html          erdosproblems.com/N, one per FC Erdős file
  report_body.html         the prose sections of the report (hand-written)

Run:  uv run --no-project --with pyyaml python3 docs/seed_conjecture_sources_build.py --work <dir>
"""
import argparse
import importlib.util
import datetime as dt
import glob
import html
import json
import os
import pathlib
import re
import subprocess
import sys

import yaml

TODAY = dt.date(2026, 9, 8)
AMS_NAMES = {
    "3": "logic and foundations", "5": "combinatorics", "11": "number theory", "12": "field theory",
    "14": "algebraic geometry", "20": "group theory", "26": "real functions", "28": "measure theory",
    "30": "complex functions", "40": "sequences and series", "42": "harmonic analysis",
    "51": "geometry", "52": "convex and discrete geometry", "54": "general topology",
    "60": "probability", "68": "computer science",
}
HAZARDS = [
    ("density", re.compile(r"densit", re.I)),
    ("sufficiently large", re.compile(r"sufficiently large|for all large|large enough", re.I)),
    ("asymptotic notation", re.compile(r"\\gg|\\ll|≫|≪|\bO\(|\bo\(|\\Omega\(|\\Theta\(")),
    ("cardinal / set-theoretic", re.compile(r"\\aleph|ℵ|cardinal|\\omega_1|ordinal", re.I)),
    ("almost all", re.compile(r"almost all|almost every", re.I)),
]


# ----------------------------------------------------------------------------- Lean parsing
DOC_RE = re.compile(r"/--(?P<doc>.*?)-/", re.S)
ATTR_RE = re.compile(r"@\[(?P<attrs>[^\]]*)\]", re.S)
DECL_RE = re.compile(r"^(?:noncomputable\s+)?(?P<kind>theorem|lemma|def|abbrev|structure|instance)\s+(?P<name>[^\s:({\[]+)", re.M)
MODDOC_RE = re.compile(r"/-!(?P<doc>.*?)-/", re.S)
NS_RE = re.compile(r"^namespace\s+(\S+)", re.M)
URL_RE = re.compile(r"https?://[^\s)\]>\"']+")


def parse_attrs(text):
    out = {"category": None, "ams": [], "formal_proof": None}
    if not text:
        return out
    m = re.search(r"category\s+(research open|research solved|textbook|API|test)", text)
    if m:
        out["category"] = m.group(1)
    m = re.search(r"AMS\s+([0-9 ]+)", text)
    if m:
        out["ams"] = m.group(1).split()
    m = re.search(r"formal_proof\s+using\s+(\w+)(?:\s+at\s+\"([^\"]+)\")?", text)
    if m:
        out["formal_proof"] = {"using": m.group(1), "url": m.group(2)}
    return out


def parse_lean(path):
    src = open(path, encoding="utf-8").read()
    mod = MODDOC_RE.search(src)
    moddoc = mod.group("doc").strip() if mod else ""
    title = ""
    for line in moddoc.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    refs = URL_RE.findall(moddoc)
    ns = NS_RE.search(src)
    namespace = ns.group(1) if ns else ""
    decls = []
    positions = [(m.start(), m) for m in DECL_RE.finditer(src)]
    for idx, (pos, m) in enumerate(positions):
        end = positions[idx + 1][0] if idx + 1 < len(positions) else len(src)
        body = src[m.end():end]
        # attributes and docstring immediately preceding the declaration
        pre = src[max(0, pos - 6000):pos]
        attrs_text = ""
        doc = ""
        tail = pre.rstrip()
        # collect trailing attribute blocks
        while tail.endswith("]"):
            a = tail.rfind("@[")
            if a < 0:
                break
            attrs_text = tail[a + 2:-1] + " " + attrs_text
            tail = tail[:a].rstrip()
        if tail.endswith("-/"):
            d = tail.rfind("/--")
            if d >= 0 and "/-!" not in tail[d:]:
                doc = tail[d + 3:-2].strip()
        at = parse_attrs(attrs_text)
        decls.append({
            "kind": m.group("kind"), "name": m.group("name"), "doc": doc,
            "category": at["category"], "ams": at["ams"], "formal_proof": at["formal_proof"],
            # value-typed: `answer(sorry)` used as a value (`f n = answer(sorry)`), as opposed to the
            # prove-or-disprove form `answer(sorry) ↔ P`, which is a conjecture with unknown truth value
            "value_typed": "answer(sorry)" in body and not re.search(r"answer\(sorry\)\s*↔|↔\s*answer\(sorry\)", body),
        })
    local_defs = [d for d in decls if d["kind"] in ("def", "abbrev", "structure") and d["category"] is None]
    return {"title": title, "refs": refs, "namespace": namespace, "decls": decls,
            "local_defs": [d["name"] for d in local_defs], "src_len": len(src)}


# ----------------------------------------------------------------------------- site pages
def parse_site(path):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return None
    s = open(path, encoding="utf-8", errors="replace").read()
    out = {}
    m = re.search(r'<span class="tooltip">\s*(.*?)\s*<span class="tooltiptext">\s*(.*?)\s*</span>\s*</span>\s*(?:-\s*(\$[\d,]+))?', s, re.S)
    if m:
        out["status"] = html.unescape(m.group(1)).strip()
        out["status_line"] = html.unescape(m.group(2)).strip()
        out["prize"] = m.group(3)
    m = re.search(r'<div id="content">(.*?)</div>', s, re.S)
    out["statement"] = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""
    out["refs"] = re.findall(r"addNewBox\('([^']+)'", s)
    years = []
    for r in out["refs"]:
        y = re.search(r"[A-Za-z]+(\d{2})(?:[a-z])?$", r)
        if y:
            yy = int(y.group(1))
            years.append(1900 + yy if yy >= 30 else 2000 + yy)
    out["first_year"] = min(years) if years else None
    m = re.search(r'<div id="tags">(.*?)</div>', s, re.S)
    out["tags"] = [html.unescape(t) for t in re.findall(r'<a href="/tags/[^"]*">([^<]+)</a>', m.group(1))] if m else []
    m = re.search(r"last edited (\d+ \w+ \d{4})", s)
    out["last_edited"] = m.group(1) if m else ""
    m = re.search(r"Comments \((\d+)\)", s)
    out["comments"] = int(m.group(1)) if m else 0
    m = re.search(r"Proof claims \((\d+)\)", s)
    out["proof_claims"] = int(m.group(1)) if m else 0
    m = re.search(r"Proof expositions \((\d+)\)", s)
    out["expositions"] = int(m.group(1)) if m else 0
    out["oeis"] = sorted(set(re.findall(r"oeis\.org/(A\d+)", s)))
    return out


# ----------------------------------------------------------------------------- other inputs
def load_history(path):
    hist = {}
    date = None
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("COMMIT "):
            date = line.split()[2][:10]
            continue
        if not line.strip():
            continue
        parts = line.split("\t")
        p = parts[-1]
        h = hist.setdefault(p, {"first": date, "last": date, "n": 0})
        h["first"] = min(h["first"], date)
        h["last"] = max(h["last"], date)
        h["n"] += 1
    return hist


def load_issues(path):
    data = json.load(open(path))
    by_num, by_file = {}, {}
    pats = [re.compile(r"Erd[őo]s(?:\s+Problem)?\s*#?\s*(\d+)", re.I), re.compile(r"erdos_?(\d+)", re.I),
            re.compile(r"ErdosProblems/(\d+)\.lean")]
    for it in data:
        title = it.get("title") or ""
        body = it.get("body") or ""
        rec = {"number": it["number"], "state": it["state"], "created": it["created_at"][:10],
               "closed": (it.get("closed_at") or "")[:10], "title": title, "url": it["html_url"],
               "pr": "pull_request" in it}
        # Problem numbers named in the title are authoritative; fall back to the opening of the
        # body only when the title names none, so a passing "see also Erdős 3" does not attach.
        nums = set()
        for p in pats:
            nums.update(p.findall(title))
        if not nums:
            for p in pats:
                nums.update(p.findall(body[:500]))
        for n in nums:
            by_num.setdefault(int(n), []).append(rec)
        for f in set(re.findall(r"FormalConjectures/[\w/]+\.lean", title + "\n" + body[:1500])):
            by_file.setdefault(f, []).append(rec)
    return by_num, by_file


def load_wiki(path):
    entries = {}
    section = ""
    for line in open(path, encoding="utf-8"):
        if line.startswith("### "):
            section = line[4:].strip()
            continue
        m = re.match(r"\|\s*\[\[(\d+)\]\]\([^)]*\)\s*\|(.*)$", line)
        if m and section and section[0] in "12":
            cells = [c.strip() for c in m.group(2).strip().strip("|").split("|")]
            entries.setdefault(int(m.group(1)), []).append({"section": section, "cells": cells})
    return entries


def load_epoch(work):
    base = os.path.join(work, "epoch/apn/data")
    sel = open(os.path.join(base, "erdos/ERDOS_PROBLEM_STATEMENT_SELECTION.md")).read()
    m = re.search(r"selected 70 Erdős problem numbers[^\n]*\n\n((?:>[^\n]*\n)+)", sel)
    bloom70 = set(int(x) for x in re.findall(r"\d+", m.group(1))) if m else set()
    fc48 = json.load(open(os.path.join(base, "erdos/subsets/bloom_selection.json")))["ids"]
    auto18 = json.load(open(os.path.join(base, "erdos_autoformalized/subsets/bloom_selection.json")))["ids"]
    top10 = json.load(open(os.path.join(base, "erdos/metadata/snapshots/bloom_top10.json")))
    top = set()
    for e in top10["entries"]:
        top.update(e["problems"])
    def nums(ids):
        d = {}
        for i in ids:
            n = int(re.match(r"Erdos(\d+)", i).group(1))
            d.setdefault(n, []).append(i.split(".", 1)[1])
        return d
    return bloom70, nums(fc48), nums(auto18), top


def load_nexus(work):
    attempted = {}
    for line in open(os.path.join(work, "nexus/erdos_problems_attempted.txt")):
        line = line.strip()
        m = re.match(r"erdos_(\d+)", line)
        if m:
            attempted.setdefault(int(m.group(1)), []).append(line)
    solved = {}
    for f in glob.glob(os.path.join(work, "nexus/APNOutputs/ErdosProblems/*.lean")):
        b = os.path.basename(f)[:-5]
        m = re.match(r"erdos_(\d+)", b)
        if m:
            solved.setdefault(int(m.group(1)), []).append(b)
    return attempted, solved


# ----------------------------------------------------------------------------- scoring
def score_row(r):
    """Heuristic trust score for seeding, from the report's filter. Returns (points, letter, reasons)."""
    if r["site"] and r["site"].get("status", "").upper() not in ("OPEN",):
        return None, "n/a", ["site status is " + r["site"].get("status", "?") + ", not a seed candidate"]
    if not r["open_stmts"]:
        return None, "n/a", ["no `research open` statement in the Lean file"]
    pts, why = 0, []
    if r["num"] in r["_bloom70"]:
        pts += 2; why.append("+2 Bloom selected it for FrontierMath Erdős")
        if r["num"] in r["_fc48"]:
            pts += 1; why.append("+1 FC statement vendored and asserted `research open` at Epoch's pin")
        elif r["num"] in r["_auto18"]:
            why.append("+0 autoformalized 2026-08, Bloom reviewed; too new to have survived a prover sweep")
    if r["num"] in r["_nexus_att"] and r["num"] not in r["_nexus_solved"]:
        pts += 2; why.append("+2 attempted by AlphaProof Nexus (Feb 2026), not solved")
    iss = r["issues"]
    if not iss:
        pts += 1; why.append("+1 no misformalization issue ever filed")
    elif any(i["state"] == "open" for i in iss):
        pts -= 2; why.append("-2 open misformalization issue")
    else:
        why.append("+0 misformalization issue(s) filed and closed")
    h = r["hist"]
    if h and h["first"] and (TODAY - dt.date.fromisoformat(h["first"])).days >= 180:
        pts += 1; why.append("+1 Lean statement public for 180+ days")
    if h and h["last"] and (TODAY - dt.date.fromisoformat(h["last"])).days < 30:
        pts -= 1; why.append("-1 file modified in the last 30 days")
    if not r["lean"]["local_defs"]:
        pts += 1; why.append("+1 no file-local definitions (Mathlib vocabulary only)")
    else:
        why.append("+0 file-local definitions: " + ", ".join(r["lean"]["local_defs"][:4]))
    if r["hazards"]:
        d = min(2, len(r["hazards"]))
        pts -= d; why.append(f"-{d} wording hazard: " + ", ".join(r["hazards"]))
    if r["main_open"] and r["main_open"]["value_typed"]:
        pts -= 1; why.append("-1 main open statement is value-typed (`answer(sorry)`)")
    if any("🟢" in " ".join(e["cells"]) and e["section"][0] == "1" for e in r["wiki"]):
        pts -= 2; why.append("-2 wiki records a full AI solution while the site still says open")
    letter = "A" if pts >= 6 else "B" if pts >= 4 else "C" if pts >= 2 else "D"
    return pts, letter, why


# ----------------------------------------------------------------------------- html helpers
def esc(x):
    return html.escape(str(x), quote=True)


def short(text, n=420):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def fc_url(commit, rel):
    return f"https://github.com/google-deepmind/formal-conjectures/blob/{commit}/{rel}"


def render_stmt_list(decls, commit, rel):
    items = []
    for d in decls:
        if not d["category"]:
            continue
        fp = ""
        if d["formal_proof"]:
            if d["formal_proof"]["url"]:
                fp = f' · <a href="{esc(d["formal_proof"]["url"])}">Lean proof</a>'
            else:
                fp = f' · Lean proof in the registry ({esc(d["formal_proof"]["using"])})'
        vt = " · value-typed" if d["value_typed"] else ""
        ams = " ".join("AMS " + a for a in d["ams"])
        items.append(f'<li><code>{esc(d["name"])}</code> <span class="cat {esc(d["category"].replace(" ", "-"))}">{esc(d["category"])}</span> '
                     f'<span class="mut">{esc(ams)}{vt}</span>{fp}<div class="doc">{esc(short(d["doc"], 700))}</div></li>')
    return "<ul class=\"stmts\">" + "".join(items) + "</ul>"


def render_wiki(entries):
    if not entries:
        return ""
    out = []
    for e in entries:
        out.append(f'<li><span class="mut">{esc(e["section"])}</span> · ' + " · ".join(esc(c) for c in e["cells"]) + "</li>")
    return "<ul class=\"wiki\">" + "".join(out) + "</ul>"


def render_issues(iss):
    if not iss:
        return "none"
    return "<br>".join(f'<a href="{esc(i["url"])}">#{i["number"]}</a> {"PR" if i["pr"] else "issue"}, {esc(i["state"])}, {esc(i["created"])}' + (f' → {esc(i["closed"])}' if i["closed"] else "") for i in iss)


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "seed_conjecture_sources.html"))
    ap.add_argument("--json", default=os.path.join(os.path.dirname(__file__), "seed_conjecture_sources.json"),
                    help="also write the joined dataset here (F11-T5): the same rows the report's "
                    "catalog renders, extracted by seed_conjecture_sources_extract.py")
    args = ap.parse_args()
    W = args.work
    fc = os.path.join(W, "fc")
    commit = subprocess.check_output(["git", "-C", fc, "rev-parse", "HEAD"], text=True).strip()
    commit_date = subprocess.check_output(["git", "-C", fc, "log", "-1", "--format=%cI"], text=True).strip()[:10]
    toolchain = open(os.path.join(fc, "lean-toolchain")).read().strip()
    manifest = json.load(open(os.path.join(fc, "lake-manifest.json")))
    mathlib = next(p for p in manifest["packages"] if p["name"] == "mathlib")
    mathlib_rev, mathlib_tag = mathlib["rev"], mathlib.get("inputRev")

    problems = {str(p["number"]): p for p in yaml.safe_load(open(os.path.join(W, "ep/data/problems.yaml")))}
    hist = load_history(os.path.join(W, "fc_file_history.txt"))
    issues_by_num, issues_by_file = load_issues(os.path.join(W, "fc_misform_issues.json"))
    wiki = load_wiki(os.path.join(W, "epwiki/AI-contributions-to-Erdős-problems.md"))
    bloom70, fc48, auto18, top10 = load_epoch(W)
    nexus_att, nexus_solved = load_nexus(W)

    rows = []
    missing_pages = []
    for path in sorted(glob.glob(os.path.join(fc, "FormalConjectures/ErdosProblems/*.lean"))):
        base = os.path.basename(path)[:-5]
        if not base.isdigit():
            continue
        num = int(base)
        rel = f"FormalConjectures/ErdosProblems/{base}.lean"
        lean = parse_lean(path)
        site = parse_site(os.path.join(W, "ep_pages", f"{base}.html"))
        if site is None:
            missing_pages.append(num)
        db = problems.get(base, {})
        open_stmts = [d for d in lean["decls"] if d["category"] == "research open"]
        solved_stmts = [d for d in lean["decls"] if d["category"] == "research solved"]
        main_open = next((d for d in open_stmts if ".variants." not in d["name"] and ".parts." not in d["name"]), open_stmts[0] if open_stmts else None)
        haz_text = (site or {}).get("statement", "") + " " + " ".join(d["doc"] for d in open_stmts)
        hazards = [name for name, rx in HAZARDS if rx.search(haz_text)]
        r = {
            "num": num, "rel": rel, "lean": lean, "site": site, "db": db, "open_stmts": open_stmts,
            "solved_stmts": solved_stmts, "main_open": main_open, "hazards": hazards,
            "issues": sorted(issues_by_num.get(num, []) + [i for i in issues_by_file.get(rel, []) if i not in issues_by_num.get(num, [])], key=lambda i: i["created"]),
            "hist": hist.get(rel), "wiki": wiki.get(num, []),
            "_bloom70": bloom70, "_fc48": fc48, "_auto18": auto18, "_nexus_att": nexus_att, "_nexus_solved": nexus_solved,
        }
        r["score"], r["letter"], r["why"] = score_row(r)
        rows.append(r)

    # ------------------------------------------------------------------ Erdős catalog table
    trs = []
    for r in rows:
        s = r["site"] or {}
        db = r["db"]
        status = s.get("status") or db.get("status", {}).get("state", "?")
        status_cls = "open" if status.upper() == "OPEN" else "closed"
        cats = {}
        for d in r["lean"]["decls"]:
            if d["category"]:
                cats[d["category"]] = cats.get(d["category"], 0) + 1
        cat_txt = ", ".join(f"{v} {k}" for k, v in sorted(cats.items()))
        ams = sorted({a for d in r["lean"]["decls"] for a in d["ams"]}, key=int)
        area = "; ".join(f"AMS {a} {AMS_NAMES.get(a, '')}".strip() for a in ams)
        tags = ", ".join(s.get("tags", []) or db.get("tags", []))
        year = s.get("first_year")
        standing = f"{year} ({TODAY.year - year} yr)" if year else ""
        h = r["hist"] or {}
        days = (TODAY - dt.date.fromisoformat(h["first"])).days if h.get("first") else None
        fme = ""
        if r["num"] in r["_fc48"]:
            fme = "FME, FC-reviewed"
        elif r["num"] in r["_auto18"]:
            fme = "FME, autoformalized"
        elif r["num"] in bloom70:
            fme = "Bloom-selected, excluded (estimate-type)"
        if r["num"] in top10:
            fme += ("; " if fme else "") + "Bloom top 10"
        nx = ""
        if r["num"] in nexus_solved:
            nx = "solved: " + ", ".join(nexus_solved[r["num"]])
        elif r["num"] in nexus_att:
            nx = f"attempted ({len(nexus_att[r['num']])}), unsolved"
        lean_proofs = []
        for d in r["lean"]["decls"]:
            if d["formal_proof"] and d["category"] == "research solved":
                if d["formal_proof"]["url"]:
                    lean_proofs.append(f'<a href="{esc(d["formal_proof"]["url"])}">{esc(d["name"])}</a>')
                else:
                    lean_proofs.append(f'<a href="{esc(fc_url(commit, r["rel"]))}">{esc(d["name"])}</a> (in registry)')
        informal_proof = ""
        if r["solved_stmts"]:
            informal_proof = short(r["solved_stmts"][0]["doc"], 300)
        score_txt = "n/a" if r["score"] is None else f'{r["letter"]} ({r["score"]:+d})'
        why = "<br>".join(esc(w) for w in r["why"])
        trs.append(f"""<tr class="row {status_cls}" data-num="{r['num']}" data-status="{esc(status)}" data-score="{r['score'] if r['score'] is not None else -99}"
 data-letter="{esc(r['letter'])}" data-open="{len(r['open_stmts'])}" data-fme="{1 if r['num'] in bloom70 else 0}" data-nexus="{1 if r['num'] in nexus_att else 0}"
 data-issues="{len(r['issues'])}" data-year="{year or 0}" data-days="{days if days is not None else -1}" data-ams="{esc(' '.join(ams))}"
 data-text="{esc((s.get('statement','') + ' ' + tags + ' ' + (r['lean']['title'] or '')).lower())}">
<td class="num"><a href="https://www.erdosproblems.com/{r['num']}">#{r['num']}</a><div class="mut">{esc(s.get('prize') or (db.get('prize') if str(db.get('prize', '')).startswith('$') else '') or '')}</div></td>
<td><span class="st {status_cls}">{esc(status)}</span><div class="mut">{esc(s.get('status_line',''))}</div><div class="mut">site updated {esc(db.get('status',{}).get('last_update',''))}; page edited {esc(s.get('last_edited',''))}</div></td>
<td class="stmt">{esc(s.get('statement') or short((r['main_open'] or (r['lean']['decls'] or [{}])[0]).get('doc',''), 500))}
<details><summary>{len([d for d in r['lean']['decls'] if d['category']])} Lean statements: {esc(cat_txt)}</summary>{render_stmt_list(r['lean']['decls'], commit, r['rel'])}</details></td>
<td>{esc(area)}<div class="mut">{esc(tags)}</div></td>
<td class="tn">{esc(standing)}<div class="mut">{esc(' '.join('[' + x + ']' for x in s.get('refs', [])[:4]))}</div></td>
<td><a href="{esc(fc_url(commit, r['rel']))}">{esc(os.path.basename(r['rel']))}</a><div class="mut">{esc(r['main_open']['name'] if r['main_open'] else (r['solved_stmts'][0]['name'] if r['solved_stmts'] else ''))}</div>
<div class="mut">added {esc(h.get('first',''))}, last change {esc(h.get('last',''))}, {h.get('n',0)} commits{'; local defs: ' + esc(', '.join(r['lean']['local_defs'][:3])) if r['lean']['local_defs'] else ''}</div></td>
<td>{'<br>'.join(lean_proofs) if lean_proofs else ''}<div class="mut">{esc(informal_proof)}</div></td>
<td>{esc(fme)}<div class="mut">{esc(nx)}</div></td>
<td>{render_issues(r['issues'])}</td>
<td>{render_wiki(r['wiki'])}</td>
<td class="score"><span class="lt {esc(r['letter'])}">{esc(score_txt)}</span><details><summary>why</summary><div class="why">{why}</div></details></td>
</tr>""")

    # ------------------------------------------------------------------ non-Erdős open statements
    other = []
    for path in sorted(glob.glob(os.path.join(fc, "FormalConjectures/*/**/*.lean"), recursive=True)):
        rel = os.path.relpath(path, fc)
        if "/ErdosProblems/" in rel:
            continue
        lean = parse_lean(path)
        opens = [d for d in lean["decls"] if d["category"] == "research open"]
        if not opens:
            continue
        cats = {}
        for d in lean["decls"]:
            if d["category"]:
                cats[d["category"]] = cats.get(d["category"], 0) + 1
        ams = sorted({a for d in opens for a in d["ams"]}, key=int)
        h = hist.get(rel, {})
        iss = issues_by_file.get(rel, [])
        srcdir = rel.split("/")[1]
        refs = lean["refs"][:2]
        other.append(f"""<tr data-dir="{esc(srcdir)}" data-text="{esc((lean['title'] + ' ' + rel).lower())}">
<td>{esc(srcdir)}</td><td><a href="{esc(fc_url(commit, rel))}">{esc(rel.split('/', 2)[-1])}</a><div class="mut">{esc(lean['title'])}</div></td>
<td>{' '.join(f'<a href="{esc(u)}">{esc(u[:60])}</a>' for u in refs)}</td>
<td class="tn">{len(opens)} open / {cats.get('research solved', 0)} solved</td>
<td>{esc('; '.join('AMS ' + a + ' ' + AMS_NAMES.get(a, '') for a in ams))}</td>
<td class="tn">{esc(h.get('first', ''))}</td>
<td>{render_issues(iss)}</td>
<td><details><summary>{len(opens)} statements</summary>{render_stmt_list(opens, commit, rel)}</details></td></tr>""")

    n_open_site = sum(1 for r in rows if (r["site"] or {}).get("status", "").upper() == "OPEN")
    n_cand = sum(1 for r in rows if r["score"] is not None)
    n_A = sum(1 for r in rows if r["letter"] == "A")
    n_B = sum(1 for r in rows if r["letter"] == "B")
    body = open(os.path.join(W, "report_body.html"), encoding="utf-8").read()
    body = (body.replace("{{COMMIT}}", commit).replace("{{COMMIT_SHORT}}", commit[:7]).replace("{{COMMIT_DATE}}", commit_date)
                .replace("{{TOOLCHAIN}}", toolchain).replace("{{MATHLIB_REV}}", mathlib_rev).replace("{{MATHLIB_TAG}}", mathlib_tag or "")
                .replace("{{N_ROWS}}", str(len(rows))).replace("{{N_OPEN_SITE}}", str(n_open_site)).replace("{{N_CAND}}", str(n_cand))
                .replace("{{N_A}}", str(n_A)).replace("{{N_B}}", str(n_B)).replace("{{N_OTHER}}", str(len(other)))
                .replace("{{MISSING_PAGES}}", ", ".join(str(m) for m in missing_pages) or "none"))
    page = body.replace("{{ERDOS_TABLE_ROWS}}", "\n".join(trs)).replace("{{OTHER_TABLE_ROWS}}", "\n".join(other))
    open(args.out, "w", encoding="utf-8").write(page)
    print(f"wrote {args.out}: {len(rows)} Erdős rows ({n_open_site} open on site, {n_cand} scoreable, {n_A} A, {n_B} B), {len(other)} non-Erdős files with open statements; missing pages: {missing_pages}")
    # F11-T5: the joined dataset, from the report just written (one join, two renderings).
    if args.json:
        spec = importlib.util.spec_from_file_location(
            "seed_extract", os.path.join(os.path.dirname(__file__), "seed_conjecture_sources_extract.py")
        )
        extract_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(extract_mod)
        dataset = extract_mod.extract(pathlib.Path(args.out))
        with open(args.json, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(dataset, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
        print(f"wrote {dataset['count']} problems to {args.json}")


if __name__ == "__main__":

    main()
