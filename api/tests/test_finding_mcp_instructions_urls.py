"""F09-T16: the MCP handshake names the guide, the error codes and the usual order of calls
(audit 2026-10-04; owner-approved).

The instructions said how tokens work and which writes need none, but not where the guide is,
where a refusal's code is explained, or what an agent normally does first. An MCP-only client has
nothing else to go on. They now name the contributor guide and ``GET /errors.json`` as full URLs
from configuration (the same guide URL ``GET /`` names), and the calls in the order a first
contribution makes them.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from api_fakes import Harness, make_harness
from mcp_client import McpClient

from opn_api.mcp.server import TOOLS

PUBLIC = "https://api.example.test"
#: The order a first contribution makes its calls in, as the instructions must give it.
ORDER = (
    "list_frontier",
    "get_node",
    "claim_node",
    "check_lean",
    "precheck_submission",
    "get_precheck",
    "submit_proof",
    "get_submission",
)


@pytest.fixture
def configured() -> Iterator[Harness]:
    h = make_harness({"OPN_API_PUBLIC_URL": PUBLIC})
    with h.client:
        yield h


def instructions_of(harness: Harness) -> str:
    init = McpClient(harness).initialize()
    assert init.instructions is not None
    return init.instructions


def test_the_instructions_name_the_guide_and_the_error_codes(configured: Harness) -> None:
    text = instructions_of(configured)
    guide = configured.client.get("/").json()["guide"]
    assert guide in text
    assert f"{PUBLIC}/errors.json" in text
    assert "list_error_codes" in text


def test_the_instructions_give_the_usual_order_of_calls(configured: Harness) -> None:
    text = instructions_of(configured)
    names = {t.name for t in TOOLS}
    assert set(ORDER) <= names  # the order names real tools only
    # A subsequence: each tool is named after the one before it (an earlier mention elsewhere
    # in the text, such as precheck_submission on the tutorial node, does not count against it).
    at = 0
    for tool in ORDER:
        found = text.find(tool, at)
        assert found >= 0, f"{tool} is not named after {text[:at][-60:]!r}"
        at = found + len(tool)
