"""mcpfix WB1 item 2 (testers 2026-11-25, t883 item 4): the answer no longer echoes the program.

AXLE's body carries ``content``, the whole text it compiled: the caller's own text plus every
definition and Context the network inlined (61,728 characters on erdos-883), which overflowed the
MCP client's tool-result limit. ``result`` now leaves it out; ``echo: true`` asks for it back.
"""

from __future__ import annotations

from typing import Any

from api_fakes import AXLE_OKAY, AxleCall
from mcp_client import TARGET, McpClient
from test_checks import harness_with, post, refused, seed

from opn_api.mcp import writes

PROOF = "theorem OpnProp.and_reassoc : True := by\n  trivial\n"


def echoing(call: AxleCall) -> dict[str, Any]:
    """AXLE's answer: its own header in place of the sent one, and the text echoed."""
    return {**AXLE_OKAY, "content": "import Mathlib\n\n" + call.content + "\n"}


def test_the_echo_is_left_out_by_default() -> None:
    h = harness_with()
    seed(h)
    h.axle.replies = [echoing]
    r = post(h, {"target_id": TARGET, "content": PROOF})
    assert r.status_code == 200, r.text
    assert "content" not in r.json()["result"]
    assert r.json()["result"]["okay"] is True


def test_echo_true_asks_for_it() -> None:
    h = harness_with()
    seed(h)
    h.axle.replies = [echoing]
    r = post(h, {"target_id": TARGET, "content": PROOF, "echo": True})
    assert r.status_code == 200, r.text
    assert r.json()["result"]["content"] == "import Mathlib\n\n" + PROOF + "\n"


def test_echo_must_be_a_boolean() -> None:
    h = harness_with()
    seed(h)
    refused(post(h, {"target_id": TARGET, "content": PROOF, "echo": "yes"}), 400, "echo-invalid")
    assert h.axle.calls == []


def test_check_lean_declares_and_forwards_echo() -> None:
    (tool,) = [t for t in writes.TOOLS if t.name == "check_lean"]
    assert tool.input_schema["properties"]["echo"]["type"] == "boolean"
    h = harness_with()
    seed(h)
    h.axle.replies = [echoing, echoing]
    with h.client:
        client = McpClient(h)
        plain = client.ok("check_lean", {"target_id": TARGET, "content": PROOF})
        echoed = client.ok("check_lean", {"target_id": TARGET, "content": PROOF, "echo": True})
    assert "content" not in plain["body"]["result"]
    assert echoed["body"]["result"]["content"].endswith(PROOF + "\n")
