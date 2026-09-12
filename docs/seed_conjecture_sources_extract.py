#!/usr/bin/env python3
"""Extract the joined dataset from docs/seed_conjecture_sources.html into
docs/seed_conjecture_sources.json (F11-T5; Q23).

The report's §9 catalog *is* the fact pass's join — one row per Erdős problem with a Lean
statement in google-deepmind/formal-conjectures at the pinned commit, joined with
erdosproblems.com, the AI-contributions wiki, the benchmark selections, AlphaProof Nexus and the
registry's misformalization issues. The build script fetches those inputs into a work directory
and renders the HTML; this reads the rendered table back into records, so the dataset the five
listed targets were chosen from is a file in this repository rather than a table in a page.
Idempotent: rerunning over the same report gives the same JSON.

    uv run --no-project python3 docs/seed_conjecture_sources_extract.py
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORT = HERE / "seed_conjecture_sources.html"
OUT = HERE / "seed_conjecture_sources.json"
FC_BLOB = re.compile(r"formal-conjectures/blob/([0-9a-f]{40})/")
LEAN_FILE = re.compile(r"(\d+)\.lean")
DECL = re.compile(r"\b(erdos_\d+[A-Za-z0-9_.]*)")
AMS = re.compile(r"AMS (\d+)")
TRUST = re.compile(r"^([A-F]|n/a)\b")
ATTEMPTED = re.compile(r"attempted \((\d+)\)")


def text(cell: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", cell)).strip()


def cells(row: str) -> list[str]:
    return re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, re.S)


def extract(report: Path = REPORT) -> dict[str, object]:
    page = report.read_text(encoding="utf-8")
    pins = sorted(set(FC_BLOB.findall(page)))
    start = page.find("9. Catalog")
    table = re.search(r"<table.*?</table>", page[start:], re.S)
    assert table is not None, "no catalog table under §9"
    rows = re.findall(r"<tr.*?</tr>", table.group(0), re.S)
    header = [text(c) for c in cells(rows[0])]
    records = []
    for row in rows[1:]:
        raw = cells(row)
        if len(raw) != len(header):
            continue
        t = [text(c) for c in raw]
        number = re.match(r"#(\d+)", t[0])
        if not number:
            continue
        lean_col = raw[5]
        files = sorted(set(LEAN_FILE.findall(text(lean_col))))
        decls = sorted(set(DECL.findall(text(lean_col))))
        trust = TRUST.match(t[10])
        attempted = ATTEMPTED.search(t[7])
        records.append(
            {
                "number": int(number.group(1)),
                "bounty": "$" in t[0],
                "site_status": t[1].split("This")[0].strip() or t[1][:40],
                "informal": re.split(r"\s+\d+\.leanerdos_", t[2])[0].strip(),
                "areas": sorted(set(AMS.findall(t[3]))),
                "area_text": t[3],
                "standing_since": t[4][:4] if re.match(r"\d{4}", t[4]) else None,
                "lean_files": [f"FormalConjectures/ErdosProblems/{n}.lean" for n in files],
                "lean_declarations": decls,
                "lean_added": t[5],
                "proof_or_closed": t[6],
                "benchmarks": t[7],
                "attempted_external": int(attempted.group(1)) if attempted else 0,
                "misformalization": t[8],
                "ai_wiki": t[9],
                "trust": trust.group(1) if trust else None,
                "trust_text": t[10],
            }
        )
    return {
        "source": "docs/seed_conjecture_sources.html §9, extracted",
        "formal_conjectures_commits": pins,
        "columns": header,
        "count": len(records),
        "problems": records,
    }


if __name__ == "__main__":
    doc = extract()
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{doc['count']} problems -> {OUT.relative_to(HERE.parent)}; pins {doc['formal_conjectures_commits']}")
