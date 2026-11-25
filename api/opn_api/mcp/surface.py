"""F09-T78 (D-28 v3.50): the MCP surface as three tools over the catalog of operations.

``search`` finds operations; ``read`` runs one read operation; ``write`` runs one write
operation. An operation is one of the named tools of ``reads`` and ``writes``, unchanged, so the
bijection (D-28) holds per operation: each call of ``read`` or ``write`` is still exactly one
endpoint or one graph path. Splitting reads from writes keeps the kind on the tool, where a
harness's permission rule can see it: allow ``read``, ask on ``write``. The bearer is read from
the request header only, as before (``auth.bearer``); no token ever travels as an argument.
"""

from __future__ import annotations

import difflib
import re
from collections.abc import Iterable, Mapping
from typing import Any

from mcp import types

from opn_api.mcp import bijection, results
from opn_api.mcp.calls import Tool, ToolError, error

SEARCH, READ, WRITE = "search", "read", "write"
NAMES = (SEARCH, READ, WRITE)
DEFAULT_LIMIT = 8
MAX_LIMIT = 50

STOPWORDS = frozenset(
    {"a", "an", "the", "of", "to", "for", "my", "is", "on", "in", "and", "or", "this", "that"}
    | {"what", "which", "who", "how", "would", "do", "does", "can", "i", "it", "with", "be"}
)
WORD_RE = re.compile(r"[a-z0-9]+")


def words(text: str) -> set[str]:
    """Lower-case words, with a plural's trailing ``s`` taken off, stopwords dropped."""
    out: set[str] = set()
    for w in WORD_RE.findall(text.lower().replace("_", " ")):
        if w in STOPWORDS:
            continue
        # A plural's ``s`` only: never after another ``s`` (gloss, class) or a ``u`` (status).
        out.add(w[:-1] if len(w) > 3 and w.endswith("s") and w[-2] not in "su" else w)
    return out


def score(tool: Tool, title: str, query: str) -> int:
    """Name words count three, title words and keywords two, description words and parameter
    names one; an exact name wins."""
    if query.strip() == tool.name:
        return 1_000_000
    q = words(query)
    name, head, body = words(tool.name), words(title), words(tool.description)
    keys = words(" ".join(tool.keywords))
    args = words(" ".join(tool.input_schema.get("properties", {})))
    return sum(
        3 * (w in name) + 2 * (w in head) + 2 * (w in keys) + (w in body) + (w in args) for w in q
    )


def arguments_of(tool: Tool) -> dict[str, list[str]]:
    """The operation's argument names from its input schema, required first."""
    required = list(tool.input_schema.get("required", []))
    props = tool.input_schema.get("properties", {})
    return {"required": required, "optional": [p for p in props if p not in required]}


def entry(tool: Tool, title: str, *, full: bool, output: bool) -> dict[str, Any]:
    row = bijection.BY_TOOL[tool.name]
    doc: dict[str, Any] = {
        "name": tool.name,
        "kind": row.kind,
        "title": title,
        "auth": tool.access,
        "plain": list(row.plain),
    }
    if not full:
        doc["args"] = arguments_of(tool)
    if full:
        doc["description"] = tool.description
        doc["input_schema"] = tool.input_schema
    if output:
        doc["output_schema"] = results.declared(tool.name)
    return doc


def search(
    catalog: Iterable[Tool], titles: Mapping[str, str], arguments: Mapping[str, Any]
) -> dict[str, Any]:
    """The search tool's answer. ``operations`` names operations to return in full; ``query``
    ranks the catalog and returns the best ``limit`` in full; neither lists every operation
    briefly — the index an agent reads once."""
    tools = list(catalog)
    by_name = {t.name: t for t in tools}
    output = bool(arguments.get("include_output_schema", False))
    named = arguments.get("operations")
    if named:
        unknown = [n for n in named if n not in by_name]
        if unknown:
            raise unknown_operation(unknown[0], by_name)
        return {
            "operations": [entry(by_name[n], titles[n], full=True, output=output) for n in named]
        }
    query = str(arguments.get("query") or "").strip()
    if not query:
        return {
            "count": len(tools),
            "operations": [entry(t, titles[t.name], full=False, output=False) for t in tools],
            "next": "search with a query, or with operations naming the ones you need, for "
            "their arguments; then read or write.",
        }
    limit = min(int(arguments.get("limit") or DEFAULT_LIMIT), MAX_LIMIT)
    ranked = sorted(
        ((score(t, titles[t.name], query), i, t) for i, t in enumerate(tools)),
        key=lambda s: (-s[0], s[1]),
    )
    hits = [t for s, _, t in ranked if s > 0][:limit]
    return {"operations": [entry(t, titles[t.name], full=True, output=output) for t in hits]}


def suggestion(name: str, names: Iterable[str]) -> str:
    """``; did you mean X?`` for the closest known name, or nothing."""
    close = difflib.get_close_matches(name, list(names), n=1, cutoff=0.75)
    return f"; did you mean {close[0]}?" if close else ""


def unknown_operation(name: str, names: Iterable[str] = ()) -> ToolError:
    return error(
        "operation-unknown",
        f"no operation named {name}{suggestion(name, names)}; call search to find operations "
        "by what they do",
        "adapter",
    )


def kind_mismatch(name: str, *, wanted: str, actual: str) -> ToolError:
    return error(
        "operation-kind-mismatch",
        f"{name} is a {actual} operation; call it through the {actual} tool, not {wanted}",
        "adapter",
    )


SEARCH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "What you want to do, in words (e.g. 'claim a node', 'submit a "
            "proof'), or an operation's exact name.",
        },
        "operations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Operation names to return in full, with their argument schemas.",
        },
        "limit": {"type": "integer", "minimum": 1, "maximum": MAX_LIMIT},
        "include_output_schema": {
            "type": "boolean",
            "description": "Also return each operation's result schema.",
        },
    },
    "additionalProperties": False,
}


def call_schema(kind: str) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": f"A {kind} operation's name, as search returns it.",
            },
            "arguments": {
                "type": "object",
                "description": "The operation's arguments, per its input_schema from search.",
            },
        },
        "required": ["operation"],
        "additionalProperties": False,
    }


def declared() -> list[types.Tool]:
    return [
        types.Tool(
            name=SEARCH,
            title="Find operations",
            description="Find the network's operations by what they do. No query lists every "
            "operation with its kind (read or write) and plain git/HTTP path; a query or "
            "named operations return their descriptions and argument schemas. Then call one "
            "with read or write.",
            inputSchema=SEARCH_SCHEMA,
            annotations=types.ToolAnnotations(
                readOnlyHint=True, destructiveHint=False, idempotentHint=True
            ),
        ),
        types.Tool(
            name=READ,
            title="Run a read operation",
            description="Run one read operation by name with its arguments. Reads need no "
            "token, except the ones that read your own records (auth 'bearer' in search). "
            "The result is the operation's own.",
            inputSchema=call_schema("read"),
            annotations=types.ToolAnnotations(
                readOnlyHint=True, destructiveHint=False, idempotentHint=True
            ),
        ),
        types.Tool(
            name=WRITE,
            title="Run a write operation",
            description="Run one write operation by name with its arguments. Writes need "
            "`Authorization: Bearer <token>` on the connection, except get_token, "
            "precheck_submission and check_lean, whose endpoints decide. The result is the "
            "endpoint's status and body.",
            inputSchema=call_schema("write"),
            annotations=types.ToolAnnotations(
                readOnlyHint=False, destructiveHint=False, idempotentHint=False
            ),
        ),
    ]
