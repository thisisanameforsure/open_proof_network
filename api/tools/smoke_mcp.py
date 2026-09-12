"""F09-T5 / AC11: a real MCP client against the deployed (or local) service.

    uv run python api/tools/smoke_mcp.py <api-url> [--read-only] [--token TOKEN]

Read-only (what CI runs after a deploy): the SDK's Streamable HTTP client initializes a
session at ``<api-url>/mcp``, the listed tools are exactly D-28's rows, ``server_info`` equals
``GET /info.json``, ``list_frontier`` equals ``GET /frontier.json`` and validates, ``get_node``
serves the tutorial node's bundle with its prose demarcated, every result validates against
its ``mcp/<tool>/v1`` schema, and a write without a token is the SDK's unauthorized result.

With a token (the evidence run) it also claims the first claimable frontier node through
``claim_node``, sees the claim in ``list_frontier``, and releases it through ``release_claim``
— the AC11 round trip. When the frontier has no claimable node (the live graph's only node is
proved, F05-Q6) it says so and exits 2, ``PENDING``, rather than manufacturing content.

The SDK is the client here on purpose: AC11 asks for a real MCP client, and the same SDK is
what Claude Code speaks. The plain-path comparisons use the standard library (C5).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import httpx
from mcp import types
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "gate"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from smoke import call  # the guarded caller the F05 smoke tool uses

from opn_api.mcp import demarcate, results
from opn_api.mcp.auth import UNAUTHORIZED, UNAUTHORIZED_STATUS
from opn_api.mcp.server import MCP_PATH, TOOLS
from opn_gate import schemas

TIMEOUT_S = 60
PENDING = 2


class Client:
    def __init__(self, base: str, token: str | None) -> None:
        self.url = f"{base}{MCP_PATH}"
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}
        self.transcript: list[str] = []

    async def _run(self, name: str, arguments: dict[str, Any]) -> types.CallToolResult:
        async with (
            httpx.AsyncClient(headers=self.headers, timeout=TIMEOUT_S) as http,
            streamable_http_client(self.url, http_client=http) as (r, w, _),
            ClientSession(r, w) as session,
        ):
            await session.initialize()
            return await session.call_tool(name, arguments)

    async def _tools(self) -> tuple[types.InitializeResult, list[types.Tool]]:
        async with (
            httpx.AsyncClient(headers=self.headers, timeout=TIMEOUT_S) as http,
            streamable_http_client(self.url, http_client=http) as (r, w, _),
            ClientSession(r, w) as session,
        ):
            init = await session.initialize()
            return init, (await session.list_tools()).tools

    def tools(self) -> tuple[types.InitializeResult, list[types.Tool]]:
        return asyncio.run(self._tools())

    def call(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """The structured content, after checking it validates; the transcript keeps a line."""
        result = asyncio.run(self._run(name, arguments or {}))
        doc = result.structuredContent
        if doc is None:
            msg = f"{name}: no structured content: {result.content}"
            raise AssertionError(msg)
        problems = results.violations(name, doc)
        if problems:
            msg = f"{name}: result violates mcp/{name}/v1: {problems}"
            raise AssertionError(msg)
        summary = json.dumps(doc)[:160]
        self.transcript.append(
            f"{name}({json.dumps(arguments or {})[:80]}) -> "
            f"{'error' if result.isError else 'ok'} {summary}"
        )
        doc["__is_error__"] = result.isError
        return doc


def read_only(  # noqa: PLR0912, PLR0915 — a checklist: one branch per thing the run asserts
    base: str, client: Client, problems: list[str]
) -> dict[str, Any]:
    init, tools = client.tools()
    print(f"initialize -> {init.serverInfo.name} {init.serverInfo.version}")
    names = sorted(t.name for t in tools)
    wanted = sorted(t.name for t in TOOLS)
    print(f"tools/list -> {len(names)} tools")
    if names != wanted:
        problems.append(f"the tool surface is {names}, not {wanted}")

    info = client.call("server_info")
    status, plain = call(f"{base}/info.json")
    print(f"server_info -> protocol {info.get('protocol_version')}; GET /info.json {status}")
    if info.pop("__is_error__") or info != plain:
        problems.append("server_info differs from GET /info.json")

    frontier = client.call("list_frontier")
    status, plain = call(f"{base}/frontier.json")
    frontier.pop("__is_error__")
    entries = frontier.get("entries", [])
    print(f"list_frontier -> {len(entries)} entries; GET /frontier.json {status}")
    if frontier != plain:
        problems.append("list_frontier differs from GET /frontier.json")
    if schemas.violations(frontier):  # against the version it declares (D-34)
        problems.append(f"list_frontier does not validate against {frontier.get('schema')}")

    targets = client.call("list_targets")
    targets.pop("__is_error__")
    ids = [t["target_id"] for t in targets.get("targets", [])]
    print(f"list_targets -> {ids}")
    tutorial = None
    for target_id in ids:
        graph = client.call("get_target", {"target_id": target_id})
        graph.pop("__is_error__")
        for node in graph.get("graph", {}).get("nodes", []):
            if node.get("tutorial"):
                tutorial = str(node["node_id"])
    if tutorial is None:
        problems.append("no target marks a tutorial node")
        return {"entries": entries}
    bundle = client.call("get_node", {"node_id": tutorial})
    if bundle.pop("__is_error__"):
        problems.append(f"get_node({tutorial}) is an error: {bundle}")
    else:
        bare = demarcate.bare_strings(
            {k: v for k, v in bundle.items() if k in ("context", "annexes", "explainers")}
        )
        # F09-AC6 over the F10-R3 bundle shape: contributor *prose* must be wrapped; the node's
        # Lean source (the statement's and witness's ``text``) is code the gate checked, served
        # bare on purpose (F10-Q6), and is the one ``.text`` the rule does not apply to.
        lean_source = {"$.context.statement.text", "$.context.witness.text"}
        prose = [
            p
            for p in bare
            if p.endswith((".detail", ".route", ".text", ".justification")) and p not in lean_source
        ]
        attempts = bundle["context"]["attempts"]
        print(
            f"get_node({tutorial}) -> context {bundle['context_source']}, "
            f"{attempts['count']} attempts ({len(attempts['records'])} records), "
            f"{len(bundle['annexes'])} annexes, {len(bundle['explainers'])} explainers, "
            f"note present: {bundle.get('untrusted_note') == demarcate.UNTRUSTED_NOTE}"
        )
        if prose:
            problems.append(f"bare prose in the bundle: {prose}")
    gate_spec = client.call("get_gate_spec", {"target_id": ids[0]})
    print(f"get_gate_spec({ids[0]}) -> network commit {gate_spec.get('network_commit')}")

    # The unauthorized result is checked from a client that holds no token, whatever this one has.
    anonymous = Client(base, None)
    unauthorized = anonymous.call("claim_node", {"node_id": tutorial})
    client.transcript.extend("(no token) " + line for line in anonymous.transcript)
    if not unauthorized.pop("__is_error__") or unauthorized != {
        "status": UNAUTHORIZED_STATUS,
        "body": UNAUTHORIZED,
    }:
        problems.append(
            f"claim_node without a token is not the unauthorized result: {unauthorized}"
        )
    else:
        print("claim_node (no token) -> 401, the SDK's unauthorized result")
    return {"entries": entries, "tutorial": tutorial}


def round_trip(
    base: str, client: Client, entries: list[dict[str, Any]], problems: list[str]
) -> int:
    claimable = [e for e in entries if e.get("claimable")]
    if not claimable:
        print("PENDING: the frontier has no claimable node (F05-Q6); the claim round trip waits")
        return PENDING
    node_id = str(claimable[0]["node_id"])
    receipt = client.call("claim_node", {"node_id": node_id, "ttl": 1})
    if receipt.pop("__is_error__") or receipt["status"] != 201:
        problems.append(f"claim_node({node_id}) failed: {receipt}")
        return 1
    claim_id = receipt["body"]["id"]
    print(f"claim_node({node_id}) -> 201 claim {claim_id} as {receipt['body']['pseudonym']}")
    seen = client.call("list_frontier", {"filters": {"node_id": node_id}})
    seen.pop("__is_error__")
    active = seen["entries"][0]["claims"]["active"] if seen["entries"] else []
    if not any(a["pseudonym"] == receipt["body"]["pseudonym"] for a in active):
        problems.append(f"the claim is not in the overlay: {active}")
    else:
        print("list_frontier(filters={node_id}) -> claim visible in the overlay")
    released = client.call("release_claim", {"claim_id": claim_id})
    if released.pop("__is_error__") or released["body"].get("released") is None:
        problems.append(f"release_claim failed: {released}")
    else:
        print(f"release_claim -> 200 released at {released['body']['released']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("url", help="the service's origin, e.g. https://api.openproofnetwork.org")
    parser.add_argument("--read-only", action="store_true", help="no token, no claim")
    parser.add_argument("--token", help="a write token from POST /tokens (the evidence run)")
    args = parser.parse_args(argv)
    base = args.url.rstrip("/")
    if not base.startswith("https://") and not base.startswith("http://127.0.0.1"):
        parser.error("only https (or a local runner) is smoked")
    problems: list[str] = []
    client = Client(base, None if args.read_only else args.token)
    facts = read_only(base, client, problems)
    code = 0
    if not args.read_only and args.token and not problems:
        code = round_trip(base, client, facts.get("entries", []), problems)
    elif not args.read_only and not args.token:
        print("no --token: the claim round trip was not attempted (pass one for AC11)")
    print("\ntranscript")
    for line in client.transcript:
        print("  " + line)
    for problem in problems:
        print(f"PROBLEM: {problem}", file=sys.stderr)
    print("smoke-mcp: ok" if not problems else f"smoke-mcp: {len(problems)} problem(s)")
    return 1 if problems else code


if __name__ == "__main__":
    sys.exit(main())
