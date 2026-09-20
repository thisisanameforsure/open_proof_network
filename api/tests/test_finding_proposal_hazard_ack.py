"""Finding proposal-hazard-ack (the 2026-09-20 end-to-end run, agent E, graph PR #124): a
statement the gate's hazard checkers flag cannot be proposed through the service at all.

Step 6 lets a statement carry a finding its author *intends*, if ``META.yaml`` acknowledges it
(F02-R4): checker, location, justification. The proposal routes had no field for that, so
"infinitely many primes at least 100" was refused ``hazard-unacknowledged`` on ``100 ≤ p`` with no
way through — every other check on it had passed. The same gap the log records for holes the
post-merge job writes (F07-Q19), one route over.

F08-T14: ``acknowledged_hazards`` on both proposal routes and both MCP tools, validated against
the META schema before any pull request is opened, and written into the node's ``META.yaml``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from api_fakes import Harness
from test_proposals import NODES, STATEMENT, TARGET, WITNESS, materialise, post, pushed

from opn_api.mcp import writes
from opn_gate import layout, schemas

ACK = [
    {
        "checker": "off-by-one-range",
        "location": "100 ≤ p",
        "justification": "the bound is inclusive on purpose: primes at least 100",
    }
]


def body(**extra: Any) -> dict[str, Any]:
    return {"target_id": TARGET, "statement": STATEMENT, "witness": WITNESS, **extra}


@pytest.mark.parametrize("route", ["/proposals/variant", "/proposals/speculative"])
def test_an_acknowledged_hazard_lands_in_the_nodes_meta(
    harness: Harness, tmp_path: Path, route: str
) -> None:
    token = harness.token_for("code_alice", "alice")
    r = post(harness, route, token, body(acknowledged_hazards=ACK))
    assert r.status_code == 201, r.text
    node_id = r.json()["node_id"]
    root = materialise(pushed(harness), tmp_path / "graph")
    node_dir = root / NODES / node_id
    meta = yaml.safe_load((node_dir / "META.yaml").read_text())
    assert meta["acknowledged_hazards"] == ACK
    assert schemas.violations(meta) == [] and layout.validate_node(node_dir) == []


def test_without_the_field_meta_carries_none(harness: Harness, tmp_path: Path) -> None:
    token = harness.token_for("code_alice", "alice")
    r = post(harness, "/proposals/variant", token, body())
    assert r.status_code == 201, r.text
    root = materialise(pushed(harness), tmp_path / "graph")
    meta = yaml.safe_load((root / NODES / r.json()["node_id"] / "META.yaml").read_text())
    assert "acknowledged_hazards" not in meta


@pytest.mark.parametrize(
    "bad",
    [
        "off-by-one-range",
        [{"checker": "off-by-one-range", "location": "100 ≤ p"}],
        [{**ACK[0], "severity": "low"}],  # an unknown key
        [{**ACK[0], "checker": "Off By One"}],
        [{**ACK[0], "justification": "x" * 501}],
        [ACK[0], ACK[0]],  # the schema wants them unique
    ],
)
def test_a_malformed_acknowledgment_is_refused_before_any_pull_request(
    harness: Harness, bad: Any
) -> None:
    token = harness.token_for("code_alice", "alice")
    r = post(harness, "/proposals/variant", token, body(acknowledged_hazards=bad))
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "acknowledged-hazards-invalid"
    assert harness.githost.pushes == []


def test_both_mcp_tools_take_the_field() -> None:
    tools = {t.name: t for t in writes.TOOLS}
    for name in ("propose_variant", "propose_speculative_node"):
        props = tools[name].input_schema["properties"]
        assert "acknowledged_hazards" in props, name
        item = props["acknowledged_hazards"]["items"]
        assert set(item["required"]) == {"checker", "location", "justification"}
