"""The local runner (F05-T1)::

    set -a; . ./.env; set +a          # the local door of C8
    PYTHONPATH=api:gate uv run python -m opn_api.local [--port 8000]

Both packages must be on the path: ``opn_api`` for the service and ``opn_gate`` for the
protocol schemas it validates against (D-34), which is how the deployed package is laid out
too.

It is a minimal HTTP/1.1 server over asyncio bridging to the ASGI application — enough for a
laptop, the smoke script and a browser through the OAuth flow, without adding a server
package (C5). One request per connection, no keep-alive, no TLS. Configuration comes from the
environment (``.env`` sourced by the shell, C8 item 5), the store defaults to memory.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from collections.abc import Sequence
from typing import Any
from urllib.parse import unquote

from opn_api import app as appmod
from opn_api import config

MAX_HEADER_BYTES = 64 * 1024
REASONS = {
    200: "OK",
    201: "Created",
    302: "Found",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    409: "Conflict",
    429: "Too Many Requests",
    500: "Internal Server Error",
    503: "Service Unavailable",
}


async def serve_connection(
    asgi: Any, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    peer = writer.get_extra_info("peername") or ("127.0.0.1", 0)
    try:
        head = await reader.readuntil(b"\r\n\r\n")
    except (asyncio.IncompleteReadError, asyncio.LimitOverrunError):
        writer.close()
        return
    lines = head.decode("latin-1").split("\r\n")
    method, _, rest = lines[0].partition(" ")
    target, _, _version = rest.partition(" ")
    headers: list[tuple[bytes, bytes]] = []
    for line in lines[1:]:
        if ":" in line:
            name, _, value = line.partition(":")
            headers.append(
                (name.strip().lower().encode("latin-1"), value.strip().encode("latin-1"))
            )
    length = int(dict(headers).get(b"content-length", b"0") or 0)
    body = await reader.readexactly(length) if length else b""
    raw_path, _, query = target.partition("?")
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": "http",
        "path": unquote(raw_path),
        "raw_path": raw_path.encode("latin-1"),
        "query_string": query.encode("latin-1"),
        "root_path": "",
        "headers": headers,
        "client": (peer[0], peer[1]),
        "server": ("127.0.0.1", 0),
        "state": {},
    }
    sent_body = False

    async def receive() -> dict[str, Any]:
        nonlocal sent_body
        if sent_body:
            await asyncio.sleep(3600)  # nothing more; keep the app waiting, never lie
        sent_body = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        if message["type"] == "http.response.start":
            status = int(message["status"])
            reason = REASONS.get(status, "")
            out = [f"HTTP/1.1 {status} {reason}".encode()]
            out.extend(k + b": " + v for k, v in message.get("headers", []))
            out.append(b"connection: close")
            writer.write(b"\r\n".join(out) + b"\r\n\r\n")
        elif message["type"] == "http.response.body":
            writer.write(message.get("body", b""))
            if not message.get("more_body", False):
                await writer.drain()
                writer.close()

    try:
        await asgi(scope, receive, send)
    except Exception:
        logging.getLogger("opn_api.local").exception("request failed")
        if not writer.is_closing():
            writer.write(b"HTTP/1.1 500 Internal Server Error\r\nconnection: close\r\n\r\n")
            writer.close()


async def serve(asgi: Any, host: str, port: int) -> None:
    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await serve_connection(asgi, reader, writer)

    server = await asyncio.start_server(handle, host, port, limit=MAX_HEADER_BYTES)
    sys.stderr.write(
        f"opn-api: serving on http://{host}:{port}/ (memory store unless configured)\n"
    )
    async with server:
        await server.serve_forever()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="opn-api", description=__doc__.split("\n\n")[0])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    settings = config.load()
    logging.basicConfig(level=settings.log_level, format="%(levelname)s %(name)s: %(message)s")
    application = appmod.create_app(settings)
    try:
        asyncio.run(serve(application, args.host, args.port))
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
