"""A stand-in harness binary for the fast tier of F16's connection check (``test_harness_check``).

    python fake_harness.py <mode> <config.json>

The config is what the synthetic registry entry writes: ``{"url": ..., "headers": {...}}``.
Modes:
    connect     initialize and list tools with the official MCP client, headers expanded from
                the environment, as a harness that works does
    raw-header  the same, but the header is sent exactly as written, variable unexpanded
    lie         print "Connected" and connect to nothing, as a harness that skips an entry and
                still exits 0 does
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def connect(url: str, headers: dict[str, str]) -> int:
    async with (
        httpx.AsyncClient(headers=headers, trust_env=False) as http,
        streamable_http_client(url, http_client=http) as (read, write, _),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        tools = (await session.list_tools()).tools
    print(f"Connected: {len(tools)} tools")
    return 0


def main() -> int:
    mode, config = sys.argv[1], json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    if mode == "lie":
        print("Connected")
        return 0
    headers = dict(config.get("headers", {}))
    if mode == "connect":
        headers = {k: os.path.expandvars(v) for k, v in headers.items()}
    return asyncio.run(connect(config["url"], headers))


if __name__ == "__main__":
    sys.exit(main())
