"""F09-T10: the MCP accepts the ``tooling`` the endpoint accepts, and a refusal names its field
(tester 2026-09-21).

The erdos-402 agent, working through the MCP alone, sent the guide's own example,
``"tooling": {"model": "...", "version": None, "harness": "..."}``, and was refused
``arguments-invalid``: "None is not of type 'string'", with no field named. ``POST /submissions``
takes that value: ``submissions.check_tooling`` reads ``null`` and ``""`` as undeclared.

Each test was seen red first (``engineering/evidence/F09/task-10.txt``).
"""

from __future__ import annotations

from typing import Any

import jsonschema
import pytest
from api_fakes import Harness
from mcp_client import NODE, McpClient, seed_node

from opn_api import submissions
from opn_api.app import ApiError
from opn_api.mcp.server import BY_NAME

GUIDE_TOOLING = {"model": "the model you used", "version": None, "harness": "AGENTS.md walkthrough"}


def submit_args(tooling: Any) -> dict[str, Any]:
    return {"node_id": NODE, "artifact_type": "proof", "bundle": {}, "tooling": tooling}


def test_the_guides_own_tooling_reaches_the_endpoint(harness: Harness) -> None:
    """The agent's exact call. Whatever the endpoint then says (there is no token here), it is the
    endpoint that says it: the adapter did not refuse the arguments."""
    seed_node(harness)
    result = McpClient(harness).call("submit_proof", submit_args(GUIDE_TOOLING))
    doc = result.structuredContent
    assert doc is not None
    assert doc.get("error") != "arguments-invalid", doc


def test_a_refused_argument_names_its_field(harness: Harness) -> None:
    seed_node(harness)
    doc = McpClient(harness).failed("submit_proof", submit_args({"version": 5}))
    assert doc["error"] == "arguments-invalid" and doc["source"] == "adapter"
    assert "tooling" in doc["message"] and "version" in doc["message"], doc["message"]


VALUES: list[Any] = [None, "", "x", "y" * 200, "z" * 201, 5, ["a"]]


@pytest.mark.parametrize("field", submissions.TOOLING_FIELDS)
@pytest.mark.parametrize("value", VALUES, ids=lambda v: repr(v)[:12])
def test_the_adapter_and_the_endpoint_agree_on_every_tooling_value(field: str, value: Any) -> None:
    """Parity at the seam: what ``check_tooling`` takes the tool's schema takes, and what it
    refuses the schema refuses, so the two cannot drift apart again."""
    tooling = {field: value}
    try:
        submissions.check_tooling(tooling)
        endpoint_takes = True
    except ApiError:
        endpoint_takes = False
    schema = BY_NAME["submit_proof"].input_schema["properties"]["tooling"]
    adapter_takes = not list(jsonschema.Draft202012Validator(schema).iter_errors(tooling))
    assert adapter_takes == endpoint_takes, (field, value)
