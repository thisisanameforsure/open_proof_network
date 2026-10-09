"""Testers 2026-10-09b (C2): the handshake named the tutorial node as
``tutorial/tutorial-and-swap``, a form no tool's ``node_id`` accepts (``^[a-z0-9][a-z0-9-]*$``),
so the first ``get_node`` an MCP-only client makes from the instructions is ``arguments-invalid``.

The instructions now name the node id as the tools take it, with its target beside it, and every
id the instructions quote is one ``get_node`` answers.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

import pytest
from api_fakes import TUTORIAL_NODE, Harness, make_harness
from mcp_client import McpClient

from opn_api.mcp import auth
from opn_api.mcp.calls import ID_PARAM

ID_PATTERN = str(ID_PARAM["pattern"])


@pytest.fixture
def h() -> Iterator[Harness]:
    harness = make_harness()
    with harness.client:
        yield harness


#: A node named as the tools take it, with its target beside it.
NAMED = re.compile(r"`([^`/]+)` \(target `([^`/]+)`\)")


def named(text: str) -> list[tuple[str, str]]:
    return NAMED.findall(text)


def test_the_phrase_names_the_node_id_the_tools_take(h: Harness) -> None:
    phrase = auth.tutorial_phrase(h.context)
    assert "/" not in phrase  # never <target>/<node>: no tool takes that
    nodes = dict(named(phrase))
    assert TUTORIAL_NODE in nodes  # the target is named beside it, not joined to it
    assert all(re.fullmatch(ID_PATTERN, t) for t in nodes.values())


def test_every_id_the_instructions_quote_is_one_get_node_answers(h: Harness) -> None:
    client = McpClient(h)
    init = client.initialize()
    assert init.instructions is not None
    ids = [node for node, _target in named(init.instructions)]
    assert TUTORIAL_NODE in ids
    for node_id in ids:
        assert re.fullmatch(ID_PATTERN, node_id), node_id
        # the id passes the tools' input schema: a refusal, if any, is about the fixture's files
        # (one tutorial node of the fixture graph has no META.yaml), never arguments-invalid
        result = client.call("get_node", {"node_id": node_id, "include": []})
        if result.isError:
            assert "arguments-invalid" not in str(result.content), result.content
        else:
            assert result.structuredContent is not None
            assert result.structuredContent["node_id"] == node_id
