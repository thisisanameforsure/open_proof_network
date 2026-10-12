"""Deploy 38223446603 (2026-10-12) went red at its smoke: ``claim_node`` without a token answered
the right 401 and error, and the smoke still called it "not the unauthorized result", because it
looked for ``/<node>``` in the message while F09-T71 (testers 2026-10-09b, C2) had changed the
phrase to name the node as the tools take it (``\\`<node>\\` (target \\`<target>\\`)``). The smoke's
predicate is now a function held to the phrase the service actually builds, so a reworded
refusal fails a fast test here and not a deploy.
"""

from __future__ import annotations

import sys
from pathlib import Path

from api_fakes import Harness

from opn_api.mcp import auth

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import smoke_mcp


def test_the_smoke_accepts_the_refusal_the_service_builds(harness: Harness) -> None:
    ctx = harness.context
    body = auth.unauthorized(ctx)  # the live phrase, built the way the tool builds it
    result = {"__is_error__": True, "status": auth.UNAUTHORIZED_STATUS, "body": body}
    assert smoke_mcp.is_unauthorized(dict(result), "tutorial-and-swap")
    # the generic words (no graph readable) are accepted too: they name no node
    generic = {"__is_error__": True, "status": 401, "body": auth.UNAUTHORIZED}
    assert smoke_mcp.is_unauthorized(dict(generic), "tutorial-and-swap")


def test_the_smoke_still_refuses_the_wrong_shapes() -> None:
    body = auth.unauthorized_body("the tutorial node `tutorial-and-swap` (target `tutorial`)")
    ok = {"__is_error__": True, "status": 401, "body": body}
    assert not smoke_mcp.is_unauthorized({**ok, "__is_error__": False}, "tutorial-and-swap")
    assert not smoke_mcp.is_unauthorized({**ok, "status": 403}, "tutorial-and-swap")
    assert not smoke_mcp.is_unauthorized(
        {**ok, "body": {**body, "error": "forbidden"}}, "tutorial-and-swap"
    )
    assert not smoke_mcp.is_unauthorized(
        {**ok, "body": {**body, "message": "no way to a token here"}}, "tutorial-and-swap"
    )
