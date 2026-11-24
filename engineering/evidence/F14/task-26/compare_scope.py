"""For each new target: the namespaces in scope at the registry's theorem (enclosing `namespace`s
and top-level `open`s before it, with `open ... in` excluded) against the graph statement's `open`
lines. Reports any registry scope the graph lacks, and any `variable` in scope upstream."""

import json
import re
import sys
from pathlib import Path

import yaml

S = Path(sys.argv[1])
GRAPH, FC = S / "graph", S / "fc"


def strip_comments(text: str) -> str:
    out, i, depth = [], 0, 0
    while i < len(text):
        if text.startswith("/-", i):
            depth += 1; i += 2
        elif depth and text.startswith("-/", i):
            depth -= 1; i += 2
        elif depth:
            i += 1
        elif text.startswith("--", i):
            j = text.find("\n", i); i = len(text) if j < 0 else j
        else:
            out.append(text[i]); i += 1
    return "".join(out)


def opens_of(line: str) -> list[str]:
    body = line.split(None, 1)[1] if len(line.split(None, 1)) > 1 else ""
    body = re.sub(r"\b(scoped|Classical)\b", lambda m: m.group(0), body)
    body = re.sub(r"\(.*?\)|hiding.*|renaming.*", "", body)
    return [w for w in body.split() if w not in ("scoped", "in")]


report = []
for t in (S / "new_targets.txt").read_text().split():
    y = yaml.safe_load(open(GRAPH / "targets" / t / "target.yaml"))
    up = strip_comments((FC / y["provenance"]["upstream_path"]).read_text())
    g = strip_comments((GRAPH / "targets" / t / "nodes" / t / "Statement.lean").read_text())
    name = re.search(r"theorem\s+Opn\.(\S+)", g).group(1)
    m = re.search(rf"(?m)^\s*(?:@\[[^\]]*\]\s*)?(?:theorem|lemma)\s+(?:[\w.']+\.)?{re.escape(name)}(?=[\s(\[{{:])", up)
    if not m:
        report.append({"target": t, "problem": "theorem not found upstream"}); continue
    before = up[: m.start()]
    scopes: list[list[str]] = [[]]  # stack of (namespace/section) frames, each holding opens
    ns: list[str] = []
    frames: list[str] = []
    variables: list[str] = []
    for line in before.splitlines():
        s = line.strip()
        if s.startswith("namespace "):
            n = s.split()[1]; ns.append(n); frames.append("ns"); scopes.append([])
        elif s.startswith("section"):
            frames.append("sec"); scopes.append([])
        elif s.startswith("end") and (s == "end" or s.split()[0] == "end"):
            if frames:
                f = frames.pop(); scopes.pop()
                if f == "ns": ns.pop()
        elif re.match(r"^open\b", s) and not re.search(r"\bin\s*$", s) and " in " not in s:
            scopes[-1].extend(opens_of(s))
        elif re.match(r"^variable\b", s):
            variables.append(s)
    up_opens = {o for fr in scopes for o in fr}
    full_ns = [".".join(ns[: i + 1]) for i in range(len(ns))]
    g_opens = set()
    for line in g.splitlines():
        s = line.strip()
        if re.match(r"^open\b", s):
            g_opens.update(opens_of(s))
    # an upstream `open X` inside namespace N may mean N.X; accept either spelling
    def covered(o: str) -> bool:
        cands = {o} | {f"{n}.{o}" for n in full_ns}
        return bool(cands & g_opens)
    missing_opens = sorted(o for o in up_opens if not covered(o))
    missing_ns = [n for n in full_ns if n not in g_opens and not any(x.endswith("." + n.split(".")[-1]) and x == n for x in g_opens)]
    if missing_opens or missing_ns or variables:
        report.append({"target": t, "decl": name, "missing_opens": missing_opens,
                       "missing_namespaces": missing_ns, "variables": variables,
                       "graph_opens": sorted(g_opens)})

print(len(report), "targets with a scope difference to read")
json.dump(report, open(S / "compare_scope.json", "w"), indent=1, ensure_ascii=False)
