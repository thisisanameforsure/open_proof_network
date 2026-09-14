"""Finding guide-mcp-renames (the 2026-09-13 Euclid tester): an MCP write tool's argument names
differ from the endpoint's body fields (``ttl`` is ``ttl_hours``, ``stmt`` is ``statement``,
``attestation`` becomes ``precheck_job_id``) and the guide says so nowhere, so an agent moving
between the two paths guesses.

F09-T7 makes ``opn_api.mcp.writes.RENAMES`` the one map the handlers use; F10-T7 gives the
guide's MCP appendix an "Argument → body field" column. This test holds the two equal as
``(tool, argument, field)`` triples. A cell of that column holds pairs of backticked names joined
by an arrow, ``ttl → ttl_hours`` each name in backticks (``->`` also accepted), separated freely;
in a row naming several tools, a pair applies to every tool of the row unless the cell names the
tool first, as a backticked name and a colon (``claim_node: ttl → ttl_hours``, backticked).
``RENAMES`` is looked up inside the test because it does not exist yet; either
``{tool: {argument: field}}`` or an iterable of triples is accepted.
"""

from __future__ import annotations

import importlib
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "gate" / "agents" / "AGENTS.md"
APPENDIX = "## Appendix: the MCP tools"

_TOKEN = re.compile(r"`([^`]+)`")
_PAIR = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)`\s*(?:→|->)\s*`([A-Za-z_][A-Za-z0-9_]*)`")
_TOOL_PREFIX = re.compile(r"`([a-z_][a-z0-9_]*)`\s*:")

Triple = tuple[str, str, str]


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def guide_triples() -> set[Triple]:
    markdown = GUIDE.read_text(encoding="utf-8")
    start = markdown.index(APPENDIX)
    end = markdown.find("\n## ", start + 1)
    lines = markdown[start : end if end >= 0 else len(markdown)].splitlines()
    table = [line for line in lines if line.lstrip().startswith("|")]
    assert table, "the MCP appendix has no table"
    header = _cells(table[0])
    column = next(
        (
            i
            for i, cell in enumerate(header)
            if re.search(r"argument", cell, re.IGNORECASE)
            and re.search(r"field|body", cell, re.IGNORECASE)
        ),
        None,
    )
    assert column is not None, f"the MCP appendix has no 'Argument → body field' column: {header}"
    triples: set[Triple] = set()
    for line in table[2:]:  # the header and the |---| rule
        cells = _cells(line)
        if column >= len(cells):
            continue
        tools = [t.split("(")[0].strip() for t in _TOKEN.findall(cells[0])]
        cell = cells[column]
        named = _TOOL_PREFIX.findall(cell)
        if named:
            for chunk in re.split(r"(?=`[a-z_][a-z0-9_]*`\s*:)", cell):
                owner = _TOOL_PREFIX.match(chunk.strip())
                if owner is None:
                    continue
                triples |= {(owner.group(1), a, f) for a, f in _PAIR.findall(chunk)}
        else:
            triples |= {(tool, a, f) for tool in tools for a, f in _PAIR.findall(cell)}
    return triples


def flattened(renames: Any) -> set[Triple]:
    if isinstance(renames, Mapping):
        return {
            (str(tool), str(arg), str(field))
            for tool, pairs in renames.items()
            for arg, field in dict(pairs).items()
        }
    assert isinstance(renames, Iterable), type(renames)
    return {(str(t), str(a), str(f)) for t, a, f in renames}


def test_the_appendix_renames_column_is_the_renames_map() -> None:
    documented = guide_triples()
    writes = importlib.import_module("opn_api.mcp.writes")
    renames = getattr(writes, "RENAMES", None)
    assert renames is not None, "opn_api.mcp.writes has no RENAMES map"
    expected = flattened(renames)
    assert expected, "RENAMES is empty"
    assert documented == expected, {
        "documented only": sorted(documented - expected),
        "RENAMES only": sorted(expected - documented),
    }
