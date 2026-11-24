"""Build Strict.lean's manifest from the graph worktree: every new target's defs/ in import order,
its root Statement.lean, and the union of non-Defs imports. Usage: manifest.py <scratchpad> [ids...]"""

import hashlib
import json
import re
import sys
from pathlib import Path

S = Path(sys.argv[1])
GRAPH = S / "graph"
IMPORT_RE = re.compile(r"^import\s+(\S+)", re.M)
ids = sys.argv[2:] or (S / "new_targets.txt").read_text().split()

union: list[str] = []
targets = []
for t in ids:
    tdir = GRAPH / "targets" / t
    stems = {p.stem: p for p in (tdir / "defs").glob("*.lean")} if (tdir / "defs").is_dir() else {}
    deps = {}
    for s, p in stems.items():
        imps = IMPORT_RE.findall(p.read_text())
        deps[s] = [m.split(".", 1)[1] for m in imps if m.startswith("Defs.")]
        union += [m for m in imps if not m.startswith("Defs.")]
    order, seen = [], set()

    def visit(s):
        if s in seen:
            return
        seen.add(s)
        for d in deps[s]:
            visit(d)
        order.append(s)

    for s in sorted(stems):
        visit(s)
    stmt = tdir / "nodes" / t / "Statement.lean"
    union += [m for m in IMPORT_RE.findall(stmt.read_text()) if not m.startswith(("Defs.", "Nodes."))]
    targets.append({
        "id": t,
        "modules": [{"name": s, "path": str(stems[s]),
                     "hash": hashlib.sha256(stems[s].read_bytes()).hexdigest()[:16]} for s in order],
        "statement": str(stmt),
    })

imports = list(dict.fromkeys(union))
json.dump({"imports": imports, "targets": targets}, open(S / "strict" / "manifest.json", "w"))
print(len(targets), "targets;", "imports:", imports)
