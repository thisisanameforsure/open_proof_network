"""Finding mcp-context-budget (the owner's review of 2026-10-06): what the MCP costs a model's
context. Measured on the live server that morning: ``tools/list`` was 104 KB, about 29k tokens,
of which 17k were output schemas and 7k descriptions; one ``get_node`` on erdos-1050 answered
121 KB, about 33k tokens. Six fixes, one per task (F09-T18 to T23):

- T18: a result's text block is its structured content as compact JSON, not ``indent=2``;
- T19: ``get_node`` takes ``include`` to leave the node's prose sections out (full by default,
  the owner's ruling; D-28 notation note of 2026-10-06);
- T20: ``tools/list`` declares each output schema without its annotation prose, which stays in
  the file and in ``get_schema``;
- T21: every input parameter says what it is, and ``list_frontier``'s filters name their fields;
- T22: no tool description is longer than ``DESCRIPTION_BUDGET`` characters; the guide holds
  the rest;
- T23: every tool has a title; a tool that needs a token still refuses inside the tool result,
  never with an HTTP 401 (F09-Q22: the token is not OAuth).
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from api_fakes import Harness
from mcp_client import INJECTION, NODE, McpClient, seed_node

from opn_api.mcp import reads, results
from opn_api.mcp.server import MCP_PATH, TOOLS

#: The prose sections of a node's bundle a caller may leave out (T19).
PROSE = ("annexes", "explainers", "outlines", "gloss_chains", "explainer_chains")
#: What get_node always answers, whatever ``include`` says (T19).
ALWAYS = {
    "node_id",
    "target_id",
    "context",
    "context_source",
    "closing",
    "files",
    "claims",
    "submissions",
    "untrusted_note",
}
#: The longest a declared description may be, plain path included (T22).
DESCRIPTION_BUDGET = 1000
#: JSON Schema keywords that annotate and never constrain (2020-12, meta-data vocabulary).
PROSE_KEYWORDS = {"description", "title", "$comment", "examples"}
#: Schema keywords whose value is a map from names to subschemas, not a subschema itself.
SCHEMA_MAPS = {"properties", "patternProperties", "$defs", "definitions", "dependentSchemas"}


def compact(doc: Any) -> str:
    return json.dumps(doc, separators=(",", ":"), ensure_ascii=False)


def prose_at(schema: Any, where: str = "$") -> list[str]:
    """Every place a prose keyword sits in schema position, walking maps of names as maps (a
    property called ``description`` is a name, not a keyword)."""
    found: list[str] = []
    if isinstance(schema, dict):
        for key, value in schema.items():
            if key in PROSE_KEYWORDS:
                found.append(f"{where}.{key}")
            elif key in SCHEMA_MAPS and isinstance(value, dict):
                for name, sub in value.items():
                    found += prose_at(sub, f"{where}.{key}.{name}")
            else:
                found += prose_at(value, f"{where}.{key}")
    elif isinstance(schema, list):
        for i, item in enumerate(schema):
            found += prose_at(item, f"{where}[{i}]")
    return found


def without_prose(schema: Any) -> Any:
    if isinstance(schema, dict):
        out: dict[str, Any] = {}
        for key, value in schema.items():
            if key in PROSE_KEYWORDS:
                continue
            if key in SCHEMA_MAPS and isinstance(value, dict):
                out[key] = {name: without_prose(sub) for name, sub in value.items()}
            else:
                out[key] = without_prose(value)
        return out
    if isinstance(schema, list):
        return [without_prose(item) for item in schema]
    return schema


# --- T18: compact text ----------------------------------------------------------------------------


def test_a_result_text_is_its_structured_content_as_compact_json(harness: Harness) -> None:
    seed_node(harness)
    client = McpClient(harness)
    calls: list[tuple[str, dict[str, Any]]] = [
        ("server_info", {}),
        ("list_frontier", {}),
        ("get_node", {"node_id": NODE}),
        ("get_node", {"node_id": NODE, "bogus": 1}),  # the adapter's refusal
        ("claim_node", {"node_id": NODE}),  # a write without a token
    ]
    for name, arguments in calls:
        result = client.call(name, arguments)
        assert result.structuredContent is not None, (name, result.content)
        [block] = result.content
        assert block.type == "text"
        assert block.text == compact(result.structuredContent), name


def test_the_text_keeps_lean_symbols_as_they_are(harness: Harness) -> None:
    """``ensure_ascii`` would spell ``∀`` as six characters; the text carries the character."""
    seed_node(harness)
    harness.githost.files[f"targets/propositional/nodes/{NODE}/Statement.lean"] = (
        "theorem OpnProp.and_reassoc : ∀ p : Prop, p → p := by\n  sorry\n".encode()
    )
    harness.context.files.clear()
    [block] = McpClient(harness).call("get_node", {"node_id": NODE}).content
    assert block.type == "text"
    assert "∀ p : Prop" in block.text and "\\u2200" not in block.text


# --- T19: get_node's include ----------------------------------------------------------------------


def test_get_node_declares_include() -> None:
    [tool] = [t for t in TOOLS if t.name == "get_node"]
    include = tool.input_schema["properties"].get("include")
    assert include is not None, "get_node takes no include"
    assert include["type"] == "array"
    assert sorted(include["items"]["enum"]) == sorted(PROSE)
    assert tool.input_schema["required"] == ["node_id"]


def test_without_include_get_node_is_the_full_bundle(harness: Harness) -> None:
    """The owner's ruling of 2026-10-06: full by default, so no client changes."""
    seed_node(harness)
    client = McpClient(harness)
    full = client.ok("get_node", {"node_id": NODE})
    assert set(PROSE) <= set(full)
    assert client.ok("get_node", {"node_id": NODE, "include": list(PROSE)}) == full


def test_include_nothing_leaves_every_prose_section_out(harness: Harness) -> None:
    seed_node(harness)
    client = McpClient(harness)
    full = client.ok("get_node", {"node_id": NODE})
    lean = client.ok("get_node", {"node_id": NODE, "include": []})
    assert set(lean) == ALWAYS
    assert {k: lean[k] for k in ALWAYS} == {k: full[k] for k in ALWAYS}
    assert results.violations("get_node", lean) == []
    # the fixture's annex and explainer carry the injection string; neither reaches the answer
    assert "An informal argument" not in compact(lean)
    assert "What the proof does" not in compact(lean)
    assert INJECTION in compact(full)


def test_include_names_the_sections_it_answers(harness: Harness) -> None:
    seed_node(harness)
    client = McpClient(harness)
    full = client.ok("get_node", {"node_id": NODE})
    some = client.ok("get_node", {"node_id": NODE, "include": ["annexes", "gloss_chains"]})
    assert set(some) == ALWAYS | {"annexes", "gloss_chains", "chains_source"}
    assert some["annexes"] == full["annexes"]
    assert some["gloss_chains"] == full["gloss_chains"]
    assert results.violations("get_node", some) == []


def test_an_unknown_section_is_refused_by_name(harness: Harness) -> None:
    seed_node(harness)
    out = McpClient(harness).failed("get_node", {"node_id": NODE, "include": ["attempts"]})
    assert out["error"] == "arguments-invalid"
    assert "include" in out["message"]


# --- T20: output schemas declared without prose ---------------------------------------------------


def test_a_declared_output_schema_carries_no_prose(harness: Harness) -> None:
    for tool in McpClient(harness).list_tools():
        assert tool.outputSchema is not None, tool.name
        assert prose_at(tool.outputSchema) == [], tool.name


def test_a_declared_output_schema_is_its_file_without_the_prose(harness: Harness) -> None:
    """Annotations never constrain (JSON Schema 2020-12), so the declared schema accepts what
    the file accepts; and a property named ``description`` is a name, kept."""
    listed = {t.name: t for t in McpClient(harness).list_tools()}
    for name, tool in listed.items():
        assert tool.outputSchema == without_prose(results.load(name)), name
    items = listed["list_submissions"].outputSchema
    assert items is not None
    assert '"description":{' in compact(items), "a property called description was stripped"


def test_get_schema_still_serves_the_file(harness: Harness) -> None:
    served = McpClient(harness).ok("get_schema", {"name": results.schema_id("get_node")})
    assert served == results.load("get_node")
    assert prose_at(served) != []


# --- T21: every parameter says what it is ---------------------------------------------------------


def test_every_input_parameter_is_described() -> None:
    missing = [
        f"{tool.name}.{name}"
        for tool in TOOLS
        for name, prop in tool.input_schema["properties"].items()
        if not str(prop.get("description", "")).strip()
    ]
    assert missing == []


def test_the_frontier_filters_name_their_fields() -> None:
    [tool] = [t for t in TOOLS if t.name == "list_frontier"]
    text = tool.input_schema["properties"]["filters"].get("description", "")
    absent = sorted(f for f in reads._entry_fields() if f"`{f}`" not in text)
    assert absent == []


# --- T22: descriptions fit a budget ---------------------------------------------------------------


def test_every_description_fits_the_budget(harness: Harness) -> None:
    over = {
        t.name: len(t.description or "")
        for t in McpClient(harness).list_tools()
        if len(t.description or "") > DESCRIPTION_BUDGET
    }
    assert over == {}


# --- T23: titles; the refusal stays in the tool result --------------------------------------------


def test_every_tool_has_a_title(harness: Harness) -> None:
    listed = McpClient(harness).list_tools()
    titles = [t.title for t in listed]
    assert all(isinstance(t, str) and t.strip() for t in titles), titles
    assert len(set(titles)) == len(titles)


@pytest.mark.parametrize("tool", ["claim_node", "list_my_claims"])
def test_pin_a_tool_that_needs_a_token_refuses_inside_the_result(
    harness: Harness, tool: str
) -> None:
    """**PIN** (F09-Q22). An HTTP 401 on ``/mcp`` would send a standard MCP client into an OAuth
    discovery this server cannot answer, because its tokens come from ``get_token``; the
    refusal is a tool result that says how to get one, and the HTTP status is 200."""
    seed_node(harness)
    arguments = {"node_id": NODE} if tool == "claim_node" else {}
    r = harness.client.post(
        MCP_PATH,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
        },
        headers={"Accept": "application/json, text/event-stream"},
    )
    assert r.status_code == 200, r.text
    assert "www-authenticate" not in {k.lower() for k in r.headers}
    result = r.json()["result"]
    assert result["isError"] is True
    assert "get_token" in compact(result["structuredContent"])
