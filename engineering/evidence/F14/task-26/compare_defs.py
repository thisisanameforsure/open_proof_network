"""Each ported defs/ file against its registry source, read from the port's own header."""

import json
import re
import sys
from collections import Counter
from pathlib import Path

S = Path(sys.argv[1])
GRAPH, FC = S / "graph", S / "fc"
SRC_RE = re.compile(r"Ported mechanically from `([^`]+)`")


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


DROP = re.compile(r"^(module\b|(public |meta |private )*import\b|(@\[expose\]\s*)?(public\s+)?section\b|(public\s+)?end\s*$|noncomputable section\b|@\[expose\]\s*public\s+noncomputable\s+section\b)")


def norm(text: str) -> list[str]:
    lines = []
    for ln in strip_comments(text).splitlines():
        s = ln.rstrip()
        if not s.strip():
            continue
        st = s.strip()
        if DROP.match(st):
            continue
        st = re.sub(r"^public\s+", "", st)
        st = re.sub(r"^@\[expose\]\s+", "", st)
        lines.append(st)
    return lines


def is_subsequence(small: list[str], big: list[str]) -> tuple[bool, str | None]:
    it = iter(big)
    for ln in small:
        for b in it:
            if b == ln:
                break
        else:
            return False, ln
    return True, None


stats, problems, seen = Counter(), [], {}
for t in (S / "new_targets.txt").read_text().split():
    d = GRAPH / "targets" / t / "defs"
    if not d.is_dir():
        continue
    for f in sorted(d.glob("*.lean")):
        text = f.read_text()
        m = SRC_RE.search(text)
        if not m:
            stats["no-source-header"] += 1; problems.append((t, f.name, "no source header")); continue
        src = FC / m.group(1)
        if not src.is_file():
            stats["source-missing"] += 1; problems.append((t, f.name, f"source {m.group(1)} missing")); continue
        key = (f.name, hash(text))
        if key in seen:
            stats[seen[key]] += 1; continue
        port, up = norm(text), norm(src.read_text())
        if f.name == "Local.lean":
            ok, first_bad = is_subsequence(port, up)
            verdict = "local-subset" if ok else "local-DIFFERS"
        else:
            ok = port == up
            first_bad = None
            if not ok:
                for a, b in zip(port, up):
                    if a != b:
                        first_bad = f"port: {a!r} / upstream: {b!r}"; break
                else:
                    first_bad = f"lengths {len(port)} vs {len(up)}"
            verdict = "library-identical" if ok else "library-DIFFERS"
        seen[key] = verdict
        stats[verdict] += 1
        if not ok:
            problems.append((t, f.name, first_bad))

print(dict(stats))
json.dump(problems, open(S / "compare_defs.json", "w"), indent=1, ensure_ascii=False)
for p in problems[:40]:
    print(p)
