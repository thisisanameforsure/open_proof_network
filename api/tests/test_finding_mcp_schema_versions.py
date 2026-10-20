"""F09-T13: the MCP tool descriptions name the schema versions the tools actually write
(tester 2026-09-24).

The 69-MCP agent, about to file a circularity claim, asked ``get_schema`` for the record it was
writing. The tool's description offered ``defect-claim/v1`` as its example, and v1 has no
``circular-decomposition`` class and no ``ancestor``: ``file_defect_claim`` writes v1 for D-16's
taxonomy and ``defect-claim/v3`` when an ``ancestor`` is given (``requests.CIRCULAR_SCHEMA``,
F08-T17), and neither description said so. An agent that reads the schema it was pointed at
learns a record the tool does not write.

The rule: every schema id a tool description names exists under ``gate/schemas``, and
``file_defect_claim``'s description names every version ``requests.py`` writes, read from the
constants rather than written here, so a later bump cannot leave the description behind.
F08-T42 (D-16 v3.43) retired the circularity class and ``defect-claim/v3`` with it, so that is
one version, ``defect-claim/v1``.

Red run: ``engineering/evidence/F09/task-13.txt``.
"""

from __future__ import annotations

import re
from pathlib import Path

from opn_api import requests
from opn_api.mcp.server import BY_NAME, TOOLS

SCHEMAS = Path(__file__).resolve().parents[2] / "gate" / "schemas"
#: A protocol schema id as prose names one: ``name/vN``, not preceded by a path segment or a
#: placeholder (``mcp/<tool>/v1`` is the adapter's own family, which lives beside the adapter).
SCHEMA_ID = re.compile(r"(?<![\w/<>.-])([a-z][a-z0-9-]*)/v(\d+)\b")


def named_ids(text: str) -> set[str]:
    return {f"{m.group(1)}/v{m.group(2)}" for m in SCHEMA_ID.finditer(text)}


def test_every_schema_id_named_in_a_tool_description_exists_in_gate_schemas() -> None:
    named = {(tool.name, sid) for tool in TOOLS for sid in named_ids(tool.description)}
    assert named, "the scan found no schema id at all: the pattern is wrong, not the tools"
    missing = sorted(
        (name, sid)
        for name, sid in named
        if not (SCHEMAS / sid.split("/")[0] / f"{sid.split('/')[1]}.json").is_file()
    )
    assert not missing, missing


def test_file_defect_claim_names_every_version_requests_writes() -> None:
    """F08-T42 (D-16 v3.43): with the circularity class retired, every claim is written at
    ``requests.DEFECT_SCHEMA``, and the description names that version and no other."""
    described = named_ids(BY_NAME["file_defect_claim"].description)
    assert {requests.DEFECT_SCHEMA} == {s for s in described if s.startswith("defect-claim/")}, (
        sorted(described)
    )


def test_get_schema_points_a_defect_claim_at_the_version_it_is_written_at() -> None:
    """The description's example names the defect-claim record at the version the tool writes;
    since F08-T42 that is the only one, and the retired class is not offered."""
    description = BY_NAME["get_schema"].description
    assert requests.DEFECT_SCHEMA in named_ids(description), description
    assert requests.RETIRED_CLASS not in description, description
