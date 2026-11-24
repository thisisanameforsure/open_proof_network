"""Compare each newly imported graph statement with the registry declaration it came from.

Independent of the wave driver's extractor: finds `theorem <short>` in the upstream file by name,
takes its text up to the first top-level `:=`, and compares it (whitespace-normalised, name
removed) with the graph's `theorem Opn.<short>` text up to `:=`.
"""

import importlib.util
import json
import re
import sys
from pathlib import Path

NET = Path("/Users/mikehiggins/Desktop/repos/open_proof_network")
S = Path(sys.argv[1])
GRAPH, FC = S / "graph", S / "fc"

spec = importlib.util.spec_from_file_location("wave", NET / "gate/tools/wave.py")
wave = importlib.util.module_from_spec(spec)
sys.modules["wave"] = wave
spec.loader.exec_module(wave)

catalog = json.load(open(NET / "docs/lean_conjecture_catalog.json"))
by_target: dict[str, list[dict]] = {}
for row in catalog["rows"]:
    by_target.setdefault(wave.target_id_for(row), []).append(row)


def strip_comments(text: str) -> str:
    out, i, depth = [], 0, 0
    while i < len(text):
        if text.startswith("/-", i):
            depth += 1
            i += 2
        elif depth and text.startswith("-/", i):
            depth -= 1
            i += 2
        elif depth:
            i += 1
        elif text.startswith("--", i):
            j = text.find("\n", i)
            i = len(text) if j < 0 else j
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def signature(text: str, name_re: str) -> str | None:
    m = re.search(rf"(?m)^\s*(?:@\[[^\]]*\]\s*)?(?:protected\s+|private\s+)?(?:theorem|lemma)\s+{name_re}(?=[\s(\[{{:])", text)
    if not m:
        return None
    rest = text[m.end():]
    depth = 0
    for i, ch in enumerate(rest):
        if ch in "([{⟨":
            depth += 1
        elif ch in ")]}⟩":
            depth -= 1
        elif depth == 0 and rest.startswith(":=", i):
            return " ".join(rest[:i].split())
    return None


def short(decl: str) -> str:
    return decl.rsplit(".", 1)[-1]


results = {"same": [], "differs": [], "unmatched": []}
for t in Path(S / "new_targets.txt").read_text().split():
    rows = by_target.get(t, [])
    stmt_files = list((GRAPH / "targets" / t / "nodes").glob("*/Statement.lean"))
    root = GRAPH / "targets" / t / "nodes" / t / "Statement.lean"
    if not root.is_file():
        results["unmatched"].append((t, "no root Statement.lean named for the target"))
        continue
    gtext = strip_comments(root.read_text())
    gm = re.search(r"theorem\s+Opn\.(\S+)", gtext)
    if not gm:
        results["unmatched"].append((t, "no theorem Opn.*"))
        continue
    gsig = signature(gtext, re.escape("Opn." + gm.group(1)))
    found = None
    for row in rows:
        up = FC / row["file"]
        if not up.is_file():
            continue
        utext = strip_comments(up.read_text())
        decl = row.get("decl")
        names = [short(decl)] if decl else []
        names.append(gm.group(1))
        for nm in names:
            usig = signature(utext, r"(?:[\w.']+\.)?" + re.escape(nm))
            if usig is not None:
                found = (row["key"], row["file"], nm, usig)
                break
        if found:
            break
    if not found:
        results["unmatched"].append((t, f"rows={[r['key'] for r in rows]}"))
        continue
    key, file, nm, usig = found
    rec = {"target": t, "key": key, "file": file, "decl": nm, "graph": gsig, "upstream": usig}
    results["same" if gsig == usig else "differs"].append(rec)

print(json.dumps({k: len(v) for k, v in results.items()}))
json.dump(results, open(S / "compare_upstream.json", "w"), indent=1, ensure_ascii=False)
