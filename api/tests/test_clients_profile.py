"""F16-T4 / AC4, AC7, AC14, AC15: the MCP tool surface held to every connector's profile.

Each harness is known to refuse, drop or cut something (docs/research_harnesses_2026-09.html,
part 1; each limit's source is in its registry entry): Gemini renames tools ``mcp_<server>_<tool>``
and truncates past 63 characters, Codex allows 128, Cursor is reported to load 40 tools across
all servers, Claude Code cuts a result past 25,000 tokens, and ``codex exec`` denies any tool
that is not annotated read-only. These tests read the live ``TOOLS`` and the served
``tools/list``, so a tool added tomorrow that breaks a harness fails here, before a deploy
publishes it.
"""

from __future__ import annotations

import dataclasses
import re
from typing import Any

import pytest
from api_fakes import Harness
from mcp_client import McpClient
from test_mcp_frontier import commit_frontier, entry

from opn_api import auth
from opn_api.mcp.server import SERVER_NAME, TOOLS, declare
from opn_gate import clients

REGISTRY = clients.load()
ENTRIES = [e.id for e in REGISTRY.entries]

#: The live frontier on 2026-09-25: 38 entries (engineering/evidence/F16/task-4.txt). A result
#: that fits at twice that is the bar; the test prints the count at which it would not.
LIVE_FRONTIER_ENTRIES = 38
HEADROOM = 2


def views() -> list[clients.ToolView]:
    out = []
    for tool in TOOLS:
        declared = declare(tool)
        hint = declared.annotations.readOnlyHint if declared.annotations else None
        out.append(clients.ToolView(tool.name, tool.input_schema, hint))
    return out


def test_registry_server_is_the_servers_name() -> None:
    """The name every snippet registers is the name the server reports."""
    assert REGISTRY.server == SERVER_NAME


@pytest.mark.parametrize("entry_id", ENTRIES)
def test_surface_fits(entry_id: str) -> None:
    """AC4 / R5: no tool breaks the harness's known limits."""
    found = clients.check_profile(REGISTRY, REGISTRY.by_id(entry_id), views())
    assert found == [], [str(v) for v in found]


def _profile(**limits: Any) -> clients.Entry:
    base = REGISTRY.by_id("gemini-cli")
    profile = clients.Profile(sources=base.profile.sources, **limits)
    return dataclasses.replace(base, id="synthetic", profile=profile)


VIOLATIONS: dict[str, tuple[dict[str, Any], list[clients.ToolView], str]] = {
    "max_tools": (
        {"max_tools": 2},
        [clients.ToolView(f"t{i}", {}, True) for i in range(3)],
        "synthetic: (surface): max_tools: 3 > 2",
    ),
    "max_name_length": (
        {"name_format": "mcp_{server}_{tool}", "max_name_length": 63},
        [clients.ToolView("x" * 60, {}, True)],
        "max_name_length",
    ),
    "name_pattern": (
        {"name_pattern": "^[A-Za-z0-9_-]+$"},
        [clients.ToolView("get.node", {}, True)],
        "synthetic: get.node: name_pattern",
    ),
    "forbidden_keywords": (
        {"forbidden_keywords": ("$ref",)},
        [clients.ToolView("t", {"properties": {"a": {"$ref": "#/$defs/a"}}}, True)],
        "synthetic: t: forbidden_keywords: $ref",
    ),
    "requires_readonly_hint": (
        {"requires_readonly_hint": True},
        [clients.ToolView("t", {}, None)],
        "synthetic: t: requires_readonly_hint",
    ),
}


@pytest.mark.parametrize("rule", sorted(VIOLATIONS))
def test_violation_named(rule: str) -> None:
    """AC4: each rule, broken on its own, is reported naming the harness, the tool and the rule."""
    limits, tools, expected = VIOLATIONS[rule]
    found = [str(v) for v in clients.check_profile(REGISTRY, _profile(**limits), tools)]
    assert any(expected in f for f in found), found


def test_property_named_like_a_keyword_is_not_one() -> None:
    """A property called ``pattern`` or ``type`` is a field, not a JSON Schema keyword."""
    tools = [clients.ToolView("t", {"properties": {"$ref": {"type": "string"}}}, True)]
    assert clients.check_profile(REGISTRY, _profile(forbidden_keywords=("$ref",)), tools) == []


def test_read_tools_annotated(harness: Harness) -> None:
    """AC15 / R17: what ``tools/list`` serves says read-only for every read and not for any
    write; ``codex exec`` runs a tool without asking only on ``readOnlyHint: true``."""
    served = {t.name: t for t in McpClient(harness).list_tools()}
    assert set(served) == {t.name for t in TOOLS}
    for tool in TOOLS:
        hint = served[tool.name].annotations
        assert hint is not None, f"{tool.name}: no annotations; codex exec would deny it"
        assert hint.readOnlyHint is (not tool.write), tool.name


def test_stripped_keywords_are_enforced_by_the_server(harness: Harness) -> None:
    """Gemini strips ``additionalProperties`` before its model sees a schema, so its model can
    send a field the schema closes; the server validates every call itself and refuses by name,
    so the refusal does not depend on the client keeping the keyword."""
    doc = McpClient(harness).failed("get_node", {"node_id": "x", "colour": "blue"})
    assert doc["error"] == "arguments-invalid"
    assert "colour" in doc["message"]


def frontier_text(harness: Harness, count: int) -> str:
    commit_frontier(harness, [entry(f"node-{i:03d}") for i in range(count)])
    result = McpClient(harness).call("list_frontier")
    assert not result.isError
    return "".join(getattr(c, "text", "") for c in result.content)


def test_results_fit(harness: Harness) -> None:
    """AC14 / R16: ``list_frontier`` over a frontier twice the live one's size fits every
    connector's result cap, estimated at four characters a token; the count at which the
    smallest cap would cut it is printed for the evidence."""
    count = LIVE_FRONTIER_ENTRIES * HEADROOM
    text = frontier_text(harness, count)
    smallest = clients.smallest_result_cap(REGISTRY.entries)
    assert smallest is not None
    harness_id, cap = smallest
    breaks_at = int(cap * 4 / (len(text) / count))
    print(
        f"list_frontier: {count} entries, ~{clients.estimated_tokens(text)} tokens; "
        f"{harness_id} would cut it at ~{breaks_at} entries"
    )
    found = clients.check_result(REGISTRY.entries, "list_frontier", text)
    assert found == [], [str(v) for v in found]


def test_results_cap_named(harness: Harness) -> None:
    """AC14: a cap set 1% below the result's size fails, naming the harness and the tool."""
    text = frontier_text(harness, LIVE_FRONTIER_ENTRIES)
    tight = _profile(result_cap_tokens=int(clients.estimated_tokens(text) * 0.99))
    found = [str(v) for v in clients.check_result([tight], "list_frontier", text)]
    assert found and found[0].startswith("synthetic: list_frontier: result_cap_tokens"), found


def test_token_rule_catches_a_real_token() -> None:
    """R6 is held to the token the service actually mints, not to a guessed shape."""
    token = auth.new_token()
    assert clients.TOKEN_RE.search(f'"Authorization": "Bearer {token}"')
    assert clients.TOKEN_RE.search(f"--header x:{token}")


TOOL_NAME_RE = re.compile(r"`([a-z]+(?:_[a-z]+)+)`")


def test_no_new_capability() -> None:
    """AC7 / R13: every tool name a connector's text mentions is a tool the server has, and
    every template uses only the placeholders R13 allows (``clients.problems`` enforces the
    second; this proves the registry on disk passes it)."""
    names = {t.name for t in TOOLS}
    texts = [clients.guide_section(REGISTRY)]
    for e in REGISTRY.entries:
        texts += [e.instructions, e.approve, *(s.title for s in e.snippets)]
    mentioned = {m for text in texts for m in TOOL_NAME_RE.findall(text)}
    config_words = {"default_tools_approval_mode", "bearer_token_env_var"}
    assert mentioned - config_words <= names, sorted(mentioned - config_words - names)
    assert "get_token" in mentioned  # the guide section names the one tool a restart follows
