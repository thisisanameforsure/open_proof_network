"""The MCP server and its mount (F09-R1, R2, R3, R9; D-28).

A low-level SDK ``Server`` declares exactly the tools of ``reads`` and ``writes`` — D-28's
rows, no more — each with D-28's parameters as its input schema and ``mcp/<tool>/v1`` as its
output schema, so a client can rely on the shape and the SDK validates every successful
result against it (R9). Arguments are validated here too, so a refusal is as structured as an
answer. A tool call runs against the api ``Context`` and an in-process HTTP client over the host
application, with the caller's bearer from the SDK's auth context (``auth``).

``Mount`` is the ASGI app at ``/mcp``: Streamable HTTP, stateless, JSON responses, behind the
SDK's bearer backend and auth-context middleware. The SDK's session manager must run inside a
task group the host owns: the host application's lifespan enters ``Mount.running`` (R1), and
a request that arrives with no lifespan running — every Lambda invocation, because Mangum runs
with lifespan off — is served by a manager that lives for that one request, which stateless
mode makes equivalent (Q3). The server holds no state either way.
"""

from __future__ import annotations

import asyncio
import contextlib
import contextvars
import json
import logging
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx
import jsonschema
from mcp import types
from mcp.server.auth.middleware.auth_context import AuthContextMiddleware
from mcp.server.auth.middleware.bearer_auth import BearerAuthBackend
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Receive, Scope, Send

from opn_api.mcp import auth, bijection, demarcate, reads, results, writes
from opn_api.mcp.calls import Call, Tool, ToolError, error
from opn_gate.products import PROTOCOL_VERSION

if TYPE_CHECKING:
    from opn_api.app import Context

log = logging.getLogger(__name__)

SERVER_NAME = "open-proof-network"
MCP_PATH = "/mcp"
TOOLS: tuple[Tool, ...] = (*reads.TOOLS, *writes.TOOLS)
BY_NAME: dict[str, Tool] = {t.name: t for t in TOOLS}
INSTRUCTIONS = (
    "The Open Proof Network's reference MCP server (D-28). Every tool is a lens over plain git "
    "and HTTP and holds no state: reads need no token; writes need `Authorization: Bearer "
    "<token>` from POST /tokens, and pass their endpoint's status and body through. "
    + demarcate.UNTRUSTED_NOTE
)


@dataclass(frozen=True)
class Outer:
    """What the tool needs from the HTTP request that carried the MCP call."""

    forwarded_for: str | None
    client_host: str


OUTER: contextvars.ContextVar[Outer | None] = contextvars.ContextVar("opn_mcp_outer", default=None)


def declare(tool: Tool) -> types.Tool:
    row = bijection.BY_TOOL[tool.name]
    return types.Tool(
        name=tool.name,
        description=f"{tool.description} Plain path: {row.d28}.",
        inputSchema=tool.input_schema,
        outputSchema=results.load(tool.name),
        annotations=types.ToolAnnotations(
            readOnlyHint=not tool.write, destructiveHint=False, idempotentHint=not tool.write
        ),
    )


def error_result(tool: str, doc: dict[str, Any]) -> types.CallToolResult:
    """An ``isError`` result whose structured content still satisfies the tool's schema (R9)."""
    problems = results.violations(tool, doc)
    if problems:  # a bug in the adapter, never hidden from the caller (C7)
        log.error("%s: error result violates its schema: %s", tool, "; ".join(problems))
        doc = {
            "error": "internal",
            "message": "the adapter produced an unschematic error result",
            "source": "adapter",
        }
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json.dumps(doc, indent=2))],
        structuredContent=doc,
        isError=True,
    )


def build_server(ctx: Context, host: Callable[[], ASGIApp]) -> Server[Any, Any]:
    """The SDK server over ``ctx``; ``host`` yields the application the write tools call."""
    server: Server[Any, Any] = Server(
        SERVER_NAME, version=PROTOCOL_VERSION, instructions=INSTRUCTIONS
    )

    # The SDK's registration decorators are unannotated, hence the two ignores.
    @server.list_tools()  # type: ignore[untyped-decorator,no-untyped-call]
    async def list_tools() -> list[types.Tool]:
        return [declare(t) for t in TOOLS]

    @server.call_tool(validate_input=False)  # type: ignore[untyped-decorator]
    async def call_tool(
        name: str, arguments: dict[str, Any]
    ) -> dict[str, Any] | types.CallToolResult:
        tool = BY_NAME.get(name)
        if tool is None:
            return error_result(
                "server_info", error("tool-unknown", f"no such tool {name}", "adapter").doc
            )
        try:
            jsonschema.validate(instance=arguments, schema=tool.input_schema)
        except jsonschema.ValidationError as exc:
            return error_result(name, error("arguments-invalid", exc.message, "adapter").doc)
        outer = OUTER.get()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(
                app=host(),
                raise_app_exceptions=False,
                client=(outer.client_host if outer else "127.0.0.1", 0),
            ),
            base_url=ctx.settings.public_url,
        ) as http:
            call = Call(
                ctx,
                http,
                token=auth.bearer() if tool.write else None,
                forwarded_for=outer.forwarded_for if outer else None,
            )
            try:
                return await tool.handler(call, arguments)
            except ToolError as failure:
                return error_result(name, failure.doc)
            except Exception as exc:  # C7: named, logged, never a partial answer
                log.error("%s failed: %s", name, type(exc).__name__, exc_info=exc)
                return error_result(
                    name, error("internal", f"{name} failed: {type(exc).__name__}", "adapter").doc
                )

    return server


def new_manager(server: Server[Any, Any]) -> StreamableHTTPSessionManager:
    return StreamableHTTPSessionManager(app=server, json_response=True, stateless=True)


class Mount:
    """The ASGI app at ``/mcp`` (R1): bearer verification, then the SDK's transport."""

    def __init__(self, ctx: Context, host: Callable[[], ASGIApp]) -> None:
        self.server = build_server(ctx, host)
        self._manager: StreamableHTTPSessionManager | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self.app: ASGIApp = AuthenticationMiddleware(
            AuthContextMiddleware(self._dispatch),
            backend=BearerAuthBackend(auth.StoreTokenVerifier(ctx)),
        )

    @contextlib.asynccontextmanager
    async def running(self) -> AsyncIterator[None]:
        """Enter the session manager for the host's lifetime — the host lifespan calls this."""
        manager = new_manager(self.server)
        async with manager.run():
            self._manager, self._loop = manager, asyncio.get_running_loop()
            try:
                yield
            finally:
                self._manager, self._loop = None, None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.app(scope, receive, send)

    async def _dispatch(self, scope: Scope, receive: Receive, send: Send) -> None:
        conn = HTTPConnection(scope)
        outer = Outer(
            forwarded_for=conn.headers.get("x-forwarded-for") or None,
            client_host=conn.client.host if conn.client else "unknown",
        )
        token = OUTER.set(outer)
        try:
            manager = self._manager
            if manager is not None and self._loop is asyncio.get_running_loop():
                await manager.handle_request(scope, receive, send)
                return
            # No lifespan runs on this loop (Mangum with lifespan off; a bare test client): a
            # manager for this request alone, which stateless mode makes the same thing (Q3).
            manager = new_manager(self.server)
            async with manager.run():
                await manager.handle_request(scope, receive, send)
        finally:
            OUTER.reset(token)
