"""Per-tool result schemas (F09-R9): ``mcp/<tool>/v1``, one JSON Schema file per tool.

They live beside the adapter, under ``schemas/<tool>/v1.json`` in this package, rather than in
the protocol registry (``gate/schemas``): they describe the adapter's results, not records of
the graph, and the registry's ids are one level deep (``<name>/v<n>``) and pinned into every
product golden (D-34; F09-Q5). ``get_schema`` serves both namespaces.

Every tool result — success or error — is validated against its schema before it leaves the
server: successes by the SDK, which carries the schema as the tool's ``outputSchema``, and
error results here, because the SDK does not validate a ``CallToolResult`` a tool builds itself.
"""

from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path
from typing import Any

import jsonschema

SCHEMAS_DIR = Path(__file__).resolve().parent / "schemas"
PREFIX = "mcp/"
VERSION = "v1"
NAME_RE = re.compile(r"^mcp/(?P<tool>[a-z][a-z_]*)/v1$")

#: The error branch every tool schema carries: what a caller gets when the plain path did not
#: answer (R10) or the arguments were refused. ``source`` names who did not answer.
ERROR_SOURCES: tuple[str, ...] = ("graph", "service", "adapter")


def schema_id(tool: str) -> str:
    return f"{PREFIX}{tool}/{VERSION}"


def tool_of(name: str) -> str | None:
    """The tool a schema name refers to, or ``None`` when the name is not an adapter schema."""
    m = NAME_RE.match(name)
    return m.group("tool") if m else None


def known() -> tuple[str, ...]:
    return tuple(sorted(f"{p.parent.name}" for p in SCHEMAS_DIR.glob("*/v1.json")))


@cache
def load(tool: str) -> dict[str, Any]:
    path = SCHEMAS_DIR / tool / f"{VERSION}.json"
    if not path.is_file():
        msg = f"no result schema for tool {tool!r}"
        raise KeyError(msg)
    doc: dict[str, Any] = json.loads(path.read_bytes())
    return doc


@cache
def _validator(tool: str) -> jsonschema.Draft202012Validator:
    return jsonschema.Draft202012Validator(load(tool))


def violations(tool: str, doc: object) -> list[str]:
    found = sorted(_validator(tool).iter_errors(doc), key=lambda e: list(e.absolute_path))
    return ["$" + "".join(f"[{p!r}]" for p in e.absolute_path) + ": " + e.message for e in found]
