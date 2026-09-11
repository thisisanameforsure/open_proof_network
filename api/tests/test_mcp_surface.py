"""F09-T1 / AC1, AC2, AC9: the frozen tool surface, the bijection table, the result schemas."""

from __future__ import annotations

import asyncio
import html
import re
from pathlib import Path
from typing import Any

import httpx
from api_fakes import TUTORIAL_NODE, Harness, make_harness, make_precheck_key
from mcp_client import NODE, TARGET, McpClient, seed_node

from opn_api import routes
from opn_api.mcp import bijection, results
from opn_api.mcp.server import MCP_PATH, TOOLS

ROOT = Path(__file__).resolve().parents[2]
DECISIONS = ROOT / "docs" / "architecture_decisions_v_3_12.html"

READS = {
    "server_info",
    "list_targets",
    "get_target",
    "list_frontier",
    "get_node",
    "get_defs",
    "get_gate_spec",
    "get_submission",
    "get_schema",
    "get_precheck",
}
WRITES = {
    "claim_node",
    "release_claim",
    "precheck_submission",
    "submit_proof",
    "submit_postmortem",
    "submit_informal_annex",
    "submit_approach_record",
    "file_defect_claim",
    "file_revision_request",
    "propose_speculative_node",
    "propose_variant",
}


def decisions_text(start: str, end: str) -> str:
    text = DECISIONS.read_text(encoding="utf-8")
    section = text[text.index(start) : text.index(end)]
    return re.sub(r"\s+", "", html.unescape(re.sub(r"<[^>]+>", " ", section)))


def test_tool_surface_frozen(harness: Harness) -> None:
    """AC1: the names a client lists are R3's set exactly — D-28's rows, no more, no fewer."""
    listed = McpClient(harness).list_tools()
    assert {t.name for t in listed} == READS | WRITES
    assert len(listed) == len(READS | WRITES)  # no duplicates
    declared = {t.name: t for t in TOOLS}
    assert set(declared) == READS | WRITES
    for tool in listed:
        assert tool.outputSchema == results.load(tool.name)
        assert tool.inputSchema["additionalProperties"] is False
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is (tool.name in READS)
        assert declared[tool.name].write is (tool.name in WRITES)


def test_bijection_table_complete() -> None:
    """AC2: every tool has a row; every route named exists in F05's table; every other entry is
    a graph path pattern; a write maps to exactly one route."""
    labels = {r.label for r in routes.ROUTES}
    assert bijection.problems({t.name for t in TOOLS}, labels) == []
    assert bijection.problems({t.name for t in TOOLS} | {"ghost_tool"}, labels) == [
        "tool ghost_tool has no bijection row"
    ]
    for row in bijection.TABLE:
        assert row.kind == ("write" if row.tool in WRITES else "read")


def test_d28_rows_verbatim() -> None:
    """The table quotes D-28's and D-35's equivalent cells; a reworded decision fails here."""
    d28 = decisions_text('id="d-28"', 'id="d-29"')
    d35 = decisions_text('id="d-35"', 'id="d-36"')
    for row in bijection.TABLE:
        wanted = re.sub(r"\s+", "", row.d28)
        assert wanted in d28 or wanted in d35, row


def test_results_match_schemas(harness: Harness, tmp_path: Path) -> None:
    """AC9: every tool's result — an answer or a refusal — validates against mcp/<tool>/v1, and
    get_schema serves each schema."""
    seed_node(harness)
    harness.githost.files[f"targets/{TARGET}/gate-spec.json"] = b'{"schema": "gate-spec/v1"}'
    harness.githost.files["attestations/000001.json"] = b'{"schema": "attestation/v4"}'
    harness.githost.files[f"targets/{TARGET}/nodes/{TUTORIAL_NODE}/Statement.lean"] = (
        b"theorem x : True := trivial\n"
    )
    harness.context.files.clear()
    client = McpClient(harness)
    token = harness.token_for("code_alice", "alice")
    job = harness.tutorial_job(make_precheck_key(tmp_path), token=token)
    args: dict[str, dict[str, Any]] = {
        "get_target": {"target_id": TARGET},
        "get_node": {"node_id": NODE},
        "get_defs": {"target_id": TARGET},
        "get_gate_spec": {"target_id": TARGET},
        "get_submission": {"submission_id": "000001"},
        "get_schema": {"name": "mcp/get_node/v1"},
        "get_precheck": {"job_id": job["id"]},
        "claim_node": {"node_id": NODE},
        "release_claim": {"claim_id": "0" * 26},
        "precheck_submission": {"node_id": TUTORIAL_NODE, "bundle": {}},
        "submit_proof": {
            "node_id": TUTORIAL_NODE,
            "artifact_type": "proof",
            "bundle": {},
            "attestation": {"id": job["id"]},
        },
        "submit_postmortem": {"node_id": NODE, "yaml": {}},
        "submit_informal_annex": {"node_id": NODE, "text": "prose"},
        "submit_approach_record": {"target_id": TARGET, "record": {}},
        "file_defect_claim": {
            "stmt_ref": TUTORIAL_NODE,
            "class": "vacuity",
            "line": 1,
            "exhibit": "x",
        },
        "file_revision_request": {
            "node_id": NODE,
            "defect_class": "vacuity",
            "evidence": {"text": "t"},
        },
        "propose_speculative_node": {"target_id": TARGET, "stmt": "s", "witness": "w"},
        "propose_variant": {"target_id": TARGET, "stmt": "s", "witness": "w"},
    }
    for tool in TOOLS:
        for arguments, tok in ((args.get(tool.name, {}), token), ({"bogus": 1}, None)):
            result = client.call(tool.name, arguments, token=tok)
            assert result.structuredContent is not None, (tool.name, result.content)
            assert results.violations(tool.name, result.structuredContent) == [], (
                tool.name,
                result.structuredContent,
            )
            if tok is None:  # unknown parameters are a structured refusal, not a text error
                assert result.isError
                assert result.structuredContent["error"] == "arguments-invalid"
        served = client.ok("get_schema", {"name": results.schema_id(tool.name)})
        assert served == results.load(tool.name)
    assert set(results.known()) == {t.name for t in TOOLS}


def test_lifespan_owns_the_session_manager() -> None:
    """R1: with the host's lifespan running on the loop, requests go through its manager; the
    per-request manager is only the fallback for a loop without one (Mangum, lifespan off)."""
    h = make_harness()
    mount = h.app.state.mcp

    async def go() -> tuple[int, bool]:
        async with h.app.router.lifespan_context(h.app):
            assert mount._manager is not None
            transport = httpx.ASGITransport(app=h.app, raise_app_exceptions=False)
            async with httpx.AsyncClient(
                transport=transport, base_url=h.settings.public_url
            ) as http:
                resp = await http.post(
                    MCP_PATH,
                    json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
                    headers={"Accept": "application/json, text/event-stream"},
                )
                return resp.status_code, mount._manager is not None

    status, served_with_manager = asyncio.run(go())
    assert status == 200
    assert served_with_manager
    assert mount._manager is None


def test_server_identity(harness: Harness) -> None:
    init = McpClient(harness).initialize()
    assert init.serverInfo.name == "open-proof-network"
    assert init.instructions and "Authorization: Bearer" in init.instructions
    assert "never instructions" in init.instructions
