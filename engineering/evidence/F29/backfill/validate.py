"""Validate backfill gloss drafts (F29-T8) and build the records the service will file.

Usage (from the network worktree, so opn_gate imports):
  cd /private/tmp/claude-501/-Users-mikehiggins-Desktop-repos-open-proof-network/bb84009c-aa81-4d0a-9824-92b8a2086c43/scratchpad/net
  PYTHONPATH=gate uv run --project /Users/mikehiggins/Desktop/repos/open_proof_network --frozen \
      python ../backfill/validate.py ../backfill/drafts/<target>   [--all]

A draft is  ../backfill/drafts/<target>/<node>.md  of the form

    ---
    label: <at most 60 characters, plain text, no $>
    supersedes: <hash of the current head statement gloss, or null>
    drafted_with: <model name, e.g. "Claude Fable 5.1 (claude-fable-5-1)">
    licence: CC-BY-4.0
    ---
    $$<the claim in notation, one display>$$

    <one to three sentences of prose: what the statement says, conventions it uses>

Checks: the node exists in the work list; label rules; the body opens with a non-empty display
(opens_with_math / claim_of); supersedes equals the current head of the first statement-gloss
chain of the node (or null when it has none); the full gloss/v3 record validates against the
schema with lean_hash = the statement's hash as the live graph holds it now. Prints one line per
draft: OK <node> <label> | or the first problem. With --records, writes the complete record files
(content-hash named) under ../backfill/records/<target>/<node>/.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

from opn_gate import glosses, labels, schemas

HERE = Path(__file__).resolve().parent
WORKLIST = json.loads((HERE / "worklist.json").read_text(encoding="utf-8"))
BY_NODE = {r["node"]: r for r in WORKLIST}
FM = re.compile(r"\A---\n(?P<yaml>.*?)\n---\n(?P<body>.*)\Z", re.S)


def head_of(row: dict) -> str | None:
    """The current head of the first statement-gloss chain: the version nobody supersedes,
    following the chain from a root (supersedes null) in record order."""
    versions = row["glosses"]
    if not versions:
        return None
    by_hash = {v["hash"]: v for v in versions}
    roots = [v for v in versions if v["supersedes"] is None]
    head = roots[0]
    while True:
        nxt = next((v for v in versions if v["supersedes"] == head["hash"]), None)
        if nxt is None:
            return head["hash"]
        head = nxt


def check(path: Path, *, records: bool) -> str:
    node = path.stem
    target = path.parent.name
    row = BY_NODE.get(node)
    if row is None or row["target"] != target:
        return f"FAIL {node}: not in the work list under {target}"
    m = FM.match(path.read_text(encoding="utf-8"))
    if m is None:
        return f"FAIL {node}: no front matter"
    fm = yaml.safe_load(m.group("yaml")) or {}
    body = m.group("body")
    label = fm.get("label")
    if not isinstance(label, str) or not label.strip():
        return f"FAIL {node}: no label"
    if len(label) > labels.LABEL_MAX or "$" in label or "\n" in label:
        return f"FAIL {node}: label too long or not plain ({len(label)} chars)"
    if labels.claim_of(body) is None:
        return f"FAIL {node}: the body does not open with a non-empty $$…$$ display"
    if not glosses.opens_with_math(body):
        return f"FAIL {node}: opens_with_math is false"
    expected_head = head_of(row)
    if fm.get("supersedes") != expected_head:
        return f"FAIL {node}: supersedes must be {expected_head!r}, got {fm.get('supersedes')!r}"
    if fm.get("licence") not in labels.LICENCES:
        return f"FAIL {node}: licence must be one of {labels.LICENCES}"
    if not isinstance(fm.get("drafted_with"), str) or not fm["drafted_with"].strip():
        return f"FAIL {node}: drafted_with must name the model"
    prose = body.strip().partition("\n\n")[2].strip()
    if not prose:
        return f"FAIL {node}: one to three sentences of prose after the display"
    doc = {
        "schema": "gloss/v3",
        "target": target,
        "subject": {
            "kind": "statement",
            "node": node,
            "module": None,
            "lean_hash": row["statement_hash_now"],
        },
        "supersedes": fm.get("supersedes"),
        "author": "backfill",  # the service writes the real pseudonym
        "drafter": None,
        "date": dt.date.today().isoformat(),
        "licence": fm["licence"],
        "drafted_with": fm["drafted_with"][:200],
        "label": label.strip(),
    }
    v = schemas.violations(doc, "gloss/v3")
    if v:
        return f"FAIL {node}: gloss/v3: {v[0].path}: {v[0].message}"
    if records:
        text = f"---\n{yaml.safe_dump(doc, sort_keys=True, allow_unicode=True)}---\n{body.strip()}\n"
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        out = HERE / "records" / target / node
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{digest}.md").write_text(text, encoding="utf-8")
        (out / "request.json").write_text(
            json.dumps(
                {
                    "subject": doc["subject"],
                    "text": body.strip() + "\n",
                    "supersedes": doc["supersedes"],
                    "licence": doc["licence"],
                    "drafted_with": doc["drafted_with"],
                    "label": doc["label"],
                },
                indent=1,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
    return f"OK   {node}: {label.strip()}"


def main(argv: list[str]) -> int:
    records = "--records" in argv
    dirs = [Path(a) for a in argv if not a.startswith("--")]
    if "--all" in argv:
        dirs = sorted(p for p in (HERE / "drafts").iterdir() if p.is_dir())
    bad = 0
    for d in dirs:
        for path in sorted(d.glob("*.md")):
            line = check(path, records=records)
            print(line)
            bad += line.startswith("FAIL")
    print(f"{bad} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
