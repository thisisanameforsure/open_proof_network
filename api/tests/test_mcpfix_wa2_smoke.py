"""mcpfix WA2: the deploy smoke checks ``list_frontier``'s compact default against the full
document, over the in-process service (``smoke_mcp.compact_frontier``)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from api_fakes import Harness
from mcp_client import McpClient
from mcpfix_wa2_fixture import seed_large

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import smoke_mcp


class Shim:
    """``smoke_mcp.Client.call``'s shape over the in-process harness."""

    def __init__(self, harness: Harness) -> None:
        self.client = McpClient(harness)

    def call(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        result = self.client.call(name, arguments)
        doc = dict(result.structuredContent or {})
        doc["__is_error__"] = result.isError
        return doc


def test_the_smoke_finds_the_compact_frontier_consistent(harness: Harness) -> None:
    seed_large(harness)
    problems: list[str] = []
    entries = harness.client.get("/frontier.json").json()["entries"]
    smoke_mcp.compact_frontier(Shim(harness), entries, problems)  # type: ignore[arg-type]
    assert problems == []


def test_the_smoke_names_a_row_that_disagrees(harness: Harness) -> None:
    seed_large(harness)
    problems: list[str] = []
    entries = harness.client.get("/frontier.json").json()["entries"][1:]  # one entry short
    smoke_mcp.compact_frontier(Shim(harness), entries, problems)  # type: ignore[arg-type]
    assert any("disagrees" in p for p in problems), problems
