"""F09-T12: an MCP record may be sent as the text the HTTP route takes (testers 2026-09-23).

The guide's postmortem example sends ``yaml`` as the file's text, and ``POST /postmortems`` takes
text or an object (``appends.as_mapping``). The MCP tool declared ``{"type": "object"}``, so an
agent following the guide through the MCP got ``arguments-invalid: $['yaml']: '<the whole yaml>'
is not of type 'object'`` — the whole record echoed back before the useful words. The tool and
the route now take the same two shapes (D-28's bijection), for postmortems and approach records.
"""

from __future__ import annotations

import yaml
from api_fakes import TUTORIAL_NODE, Harness
from mcp_client import TARGET, McpClient
from test_mcp_equivalence import postmortem


def test_a_postmortem_sent_as_text_is_taken(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    text = yaml.safe_dump(postmortem(), sort_keys=True)
    result = McpClient(harness).call(
        "submit_postmortem", {"node_id": TUTORIAL_NODE, "yaml": text}, token=token
    )
    assert not result.isError, result.content
    assert len(harness.githost.pulls) == 1


def test_an_approach_record_sent_as_text_is_taken(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    text = yaml.safe_dump({"route": "normalise", "outcome": "exhausted"})
    result = McpClient(harness).call(
        "submit_approach_record", {"target_id": TARGET, "record": text}, token=token
    )
    assert not result.isError, result.content


def test_an_object_is_still_taken(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    result = McpClient(harness).call(
        "submit_postmortem", {"node_id": TUTORIAL_NODE, "yaml": postmortem()}, token=token
    )
    assert not result.isError, result.content
