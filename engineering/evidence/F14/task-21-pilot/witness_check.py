"""Check a witness for a drafted (or refused) statement on the hosted checker, mode `witness`.

    .venv/bin/python witness_check.py <draft dir> <Witness.lean> [--target-id goldbach]

The statement is sent with its ported defs inlined (each module in its own section, its theorems
removed, since the witness route takes a statement with exactly one theorem and the checker reads
no committed defs/ for a statement that is not a node). Prints the checker's `expected` witness
type, `okay`, and the first errors. Exit 0 when okay, 1 when not, 2 on a transport or input error.
"""

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

WAVE = "/Users/mikehiggins/Desktop/repos/open_proof_network/gate/tools/wave.py"
_spec = importlib.util.spec_from_file_location("wave", WAVE)
_wave = importlib.util.module_from_spec(_spec)
sys.modules["wave"] = _wave
_spec.loader.exec_module(_wave)

draft, witness_path = Path(sys.argv[1]), Path(sys.argv[2])
target = sys.argv[sys.argv.index("--target-id") + 1] if "--target-id" in sys.argv else "goldbach"
HEADER_RE = re.compile(r"\A/-\n.*?-/\n", re.S)
IMPORT_RE = re.compile(r"^import\s+(\S+)\s*$", re.M)


def order(defs):
    done, out_ = set(), []

    def visit(stem):
        if stem in done:
            return
        done.add(stem)
        for m in IMPORT_RE.findall(defs[stem]):
            if m.startswith("Defs.") and m[5:] in defs:
                visit(m[5:])
        out_.append(stem)

    for s in sorted(defs):
        visit(s)
    return out_


defs = (
    {p.stem: p.read_text() for p in (draft / "defs").glob("*.lean")}
    if (draft / "defs").is_dir()
    else {}
)
kept, parts = [], []
for stem in order(defs):
    # Header, imports and theorems gone: the witness route takes a statement with exactly one
    # theorem (`lemma` counts too), so a ported definition whose proof fields cite the module's own
    # lemmas cannot be pre-flighted here; the gate's admission (wave-admit) is its judge.
    body, imps = _wave.port_body(defs[stem])
    kept += [m for m in imps if not m.startswith("Defs.") and m != "Mathlib"]
    parts.append(f"section\n{body}\nend\n")
statement = draft.joinpath("Statement.lean").read_text()
m = HEADER_RE.match(statement)
header = m.group(0) if m else ""
sbody = IMPORT_RE.sub("", HEADER_RE.sub("", statement)).strip("\n") + "\n"
composed = (
    header
    + "import Mathlib\n"
    + "".join(f"import {mod}\n" for mod in dict.fromkeys(kept))
    + "\n"
    + "\n".join(parts)
    + ("\n" if parts else "")
    + sbody
)
req = {
    "target_id": target,
    "mode": "witness",
    "statement": composed,
    "content": witness_path.read_text(),
}
with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
    json.dump(req, fh)
    reqp = fh.name
r = subprocess.run(
    [
        "curl", "-s", "--max-time", "300", "-X", "POST",
        "https://api.openproofnetwork.org/check",
        "-H", "Content-Type: application/json", "--data-binary", f"@{reqp}",
    ],
    capture_output=True,
    text=True,
)
try:
    res = json.loads(r.stdout)
except Exception:
    print("no JSON:", r.stdout[:400])
    sys.exit(2)
if "error" in res:
    print(json.dumps({"error": res["error"], "message": str(res.get("message", ""))[:300]}))
    sys.exit(2)
result = res.get("result") or {}
out = {
    "okay": res.get("okay"),
    "expected": res.get("expected") or result.get("expected"),
    "witness": res.get("witness") or result.get("witness"),
    "matched": res.get("matched", result.get("matched")),
    "errors": ((result.get("lean_messages") or {}).get("errors") or [])[:3],
    "tool": ((result.get("tool_messages") or {}).get("errors") or [])[:3],
    "lint": [lint.get("code") for lint in (res.get("lint") or [])],
    "keys": sorted(res.keys()),
}
print(json.dumps(out, ensure_ascii=False, indent=1)[:3000])
matches = bool((res.get("witness") or {}).get("matches"))
print("VERDICT", "ACCEPTED" if res.get("okay") and matches else "NOT ACCEPTED")
sys.exit(0 if res.get("okay") and matches else 1)
