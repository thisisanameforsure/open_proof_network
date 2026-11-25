"""A graph the size of the live one, for the MCP's read operations (mcpfix WA2).

The live graph on 2026-11-25 had 443 targets and 601 frontier entries; one target (erdos-1094)
held 69 of them. ``seed_large`` puts a frontier and an index of that shape into the fake host,
built from one live ``frontier/v8`` entry and one ``targets-index/v11`` row
(``fixtures/mcpfix-wa2-templates.json``) with only the ids varied, so a size measured here is
the size of a live answer of the same shape.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from api_fakes import Harness

TEMPLATES = json.loads(
    (Path(__file__).parent / "fixtures" / "mcpfix-wa2-templates.json").read_text("utf-8")
)
TARGETS = 450
#: Entries per target: the three busiest live targets' counts, then one or two, and the last ten
#: targets with none (a target with no open work is not a row of the frontier's summary).
BUSY = {0: 69, 1: 47, 2: 25}
EMPTY_FROM = 440


def target_id(i: int) -> str:
    return f"t-{i:03d}"


def entries_for(i: int) -> int:
    if i in BUSY:
        return BUSY[i]
    if i >= EMPTY_FROM:
        return 0
    return 2 if i < 40 else 1


def index_doc() -> dict[str, Any]:
    rows = []
    for i in range(TARGETS):
        row = copy.deepcopy(TEMPLATES["index_row"])
        row["target_id"] = row["root"] = target_id(i)
        row["claimable"] = entries_for(i) > 0
        rows.append(row)
    return {
        "schema": TEMPLATES["index_schema"],
        "rendered_from": "5" * 40,
        "policy": {"steward_rule": False},
        "targets": rows,
    }


def frontier_doc() -> dict[str, Any]:
    entries = []
    for i in range(TARGETS):
        for k in range(entries_for(i)):
            entry = copy.deepcopy(TEMPLATES["frontier_entry"])
            entry["target_id"] = target_id(i)
            entry["node_id"] = f"{target_id(i)}--h{k + 1}"
            entry["claimable"] = k % 3 != 2
            entries.append(entry)
    return {"schema": TEMPLATES["frontier_schema"], "rendered_from": "5" * 40, "entries": entries}


def seed_large(harness: Harness) -> tuple[dict[str, Any], dict[str, Any]]:
    """Put the large index and frontier into the fake host; answer both documents."""
    index, frontier = index_doc(), frontier_doc()
    harness.githost.files["targets/index.json"] = json.dumps(index).encode()
    harness.githost.files["frontier.json"] = json.dumps(frontier).encode()
    harness.context.files.clear()
    harness.context.listings.clear()
    return index, frontier


def compact(doc: Any) -> str:
    return json.dumps(doc, separators=(",", ":"), ensure_ascii=False)
