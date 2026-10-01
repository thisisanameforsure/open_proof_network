"""F08-T22: ``context/v2`` reaches the service, and a graph still on ``context/v1`` is served.

A schema bump has a deploy window (the lesson of 2026-09-11): the service deploys on a network
push, the graph's committed ``CONTEXT.json`` files move only at the re-pin that re-renders the
products, and between the two every ``get_node`` would have answered ``context-invalid`` had the
route validated a committed ``context/v1`` file against the new version. The route validates a
committed bundle against the version it names, within the versions the bundle's module accepts;
a bundle it derives itself is the current version, with ``circular_below`` present.
"""

from __future__ import annotations

import json
from pathlib import Path

from api_fakes import Harness
from mcp_client import NODE, NODE_DIR, McpClient
from test_mcp_equivalence import derived_bundle, seed_graph

from opn_gate import context, schemas


def test_a_committed_v1_bundle_is_served_through_the_window(
    harness: Harness, tmp_path: Path
) -> None:
    seed_graph(harness)
    client = McpClient(harness)
    derived = derived_bundle(harness, tmp_path / "tree")
    assert derived["schema"] == "context/v2" and derived["circular_below"] == []
    assert context.SCHEMA == "context/v2" and "context/v1" in context.ACCEPTED
    v1 = {k: v for k, v in derived.items() if k != "circular_below"}
    v1["schema"] = "context/v1"
    assert schemas.violations(v1, "context/v1") == []
    harness.githost.files[NODE_DIR + "CONTEXT.json"] = schemas.canonical_json(v1)
    harness.context.files.clear()
    served = client.ok("get_node", {"node_id": NODE})
    assert served["context_source"] == "file"
    assert {**v1, "claims": served["context"]["claims"]} == served["context"]
    # A version the module does not accept is still a named error, not a partial answer.
    harness.githost.files[NODE_DIR + "CONTEXT.json"] = json.dumps(
        {**v1, "schema": "context/v9"}
    ).encode()
    harness.context.files.clear()
    failed = client.failed("get_node", {"node_id": NODE})
    assert failed["error"] == "context-invalid" and failed["source"] == "graph"
