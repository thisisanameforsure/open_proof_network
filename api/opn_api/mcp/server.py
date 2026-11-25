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
import re
from collections.abc import AsyncIterator, Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

import httpx
import jsonschema
from mcp import types
from mcp.server.auth.middleware.auth_context import AuthContextMiddleware
from mcp.server.auth.middleware.bearer_auth import BearerAuthBackend
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Receive, Scope, Send

from opn_api.mcp import auth, bijection, demarcate, reads, results, surface, writes
from opn_api.mcp.calls import Call, Tool, ToolError, error
from opn_gate.products import PROTOCOL_VERSION

if TYPE_CHECKING:
    from opn_api.app import Context

log = logging.getLogger(__name__)

SERVER_NAME = "open-proof-network"
MCP_PATH = "/mcp"
TOOLS: tuple[Tool, ...] = (*reads.TOOLS, *writes.TOOLS)
BY_NAME: dict[str, Tool] = {t.name: t for t in TOOLS}


def instructions(tutorial: str, *, guide: str | None = None, errors: str | None = None) -> str:
    """The handshake's instructions, naming the tutorial node as ``tutorial`` words it
    (``auth.tutorial_phrase``: by name when the graph can be read), and the contributor guide
    and the error-code catalog by their full URLs when the service's configuration gives them
    (F09-T16: ``urls``); without one, the plain path stands in."""
    return (
        "The Open Proof Network's reference MCP server (D-28). Every tool is a lens over plain "
        "git and HTTP and holds no state: reads need no token, except list_my_claims, "
        "get_my_submissions and get_check, which read your own; writes need "
        "`Authorization: Bearer <token>` and pass their endpoint's "
        f"status and body through. Three writes need none: precheck_submission on {tutorial} "
        "(start there; list_frontier leaves it out, because it is proved); get_token, which "
        "turns that passing precheck into a token; and check_lean, the non-authoritative fast "
        "check (F13). "
        # F09-T16 (audit 2026-10-04): where the rest is written down, and the usual order.
        f"The contributor guide is {guide or 'AGENTS.md in the graph repository'}. A first "
        "contribution usually goes: list_frontier for an open node, get_node for its statement "
        "and context, claim_node, check_lean while you iterate, precheck_submission and "
        "get_precheck until it is done, submit_proof with the passing precheck, and "
        "get_submission to follow its pull request. "
        # F21-T8 (R10): the second entry task, words rather than a proof (D-3 v3.31).
        "A contribution that needs no proof: list_words_needed for a Lean file that has no words "
        "yet, get_node for its Lean, then submit_gloss with the words, opening with the "
        "statement in LaTeX, naming in drafted_with "
        "the model that helped draft them, if one did; one writer per file at a time, and a "
        "steward's or curator's signature on your words is what earns credit. "
        "Every refusal names its rule by a code "
        "(`error`, or a verdict's diagnostic `code`): list_error_codes, or "
        f"{errors or 'GET /errors.json'}, says what each means and what to do. "
        + demarcate.UNTRUSTED_NOTE
    )


def urls(ctx: Context) -> dict[str, str]:
    """The guide's and the error catalog's full URLs, from the service's configuration."""
    from opn_api import wayfinding  # noqa: PLC0415 — wayfinding imports this module

    return {
        "guide": wayfinding.guide_url(ctx.settings),
        "errors": ctx.settings.public_url.rstrip("/") + "/errors.json",
    }


#: The instructions in the words used when the tutorial node cannot be named.
INSTRUCTIONS = instructions(auth.TUTORIAL_UNNAMED)

#: F09-T78 (D-28 v3.50): what the three-tool surface adds in front of the instructions, whose
#: names below are then operations rather than tools.
SURFACE_LEAD = (
    "This server has three tools. search finds operations by what they do and returns each "
    "one's arguments; read runs one read operation and write one write operation, as "
    '{"operation": <name>, "arguments": {...}}. Every name below is an operation. The earlier '
    "surface, one tool per operation, is served at /mcp?surface=v1 for a transition window. "
)


class LazyInstructions:
    """Initialization options whose ``instructions`` are derived only when read. In stateless
    mode the SDK builds the options for every request, but its session reads ``instructions``
    only to answer ``initialize``; deriving them eagerly put every graph file in front of every
    tool call (the read-order tests in ``test_frontier_generation`` pin that it does not)."""

    def __init__(self, base: InitializationOptions, derive: Callable[[], str]) -> None:
        self._base = base
        self._derive = derive

    @property
    def instructions(self) -> str:
        return self._derive()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)


class LiveServer(Server[Any, Any]):
    """The SDK server with instructions derived when a client initialises, not at import: they
    name the tutorial node from the committed graphs (tester finding 2026-09-27), so moving the
    ``tutorial`` flag moves the name."""

    def __init__(self, ctx: Context, *, legacy: bool = False) -> None:
        super().__init__(SERVER_NAME, version=PROTOCOL_VERSION, instructions=INSTRUCTIONS)
        self._ctx = ctx
        self._legacy = legacy

    def create_initialization_options(
        self,
        notification_options: NotificationOptions | None = None,
        experimental_capabilities: dict[str, dict[str, Any]] | None = None,
    ) -> InitializationOptions:
        base = super().create_initialization_options(
            notification_options, experimental_capabilities
        )
        lead = "" if self._legacy else SURFACE_LEAD
        lazy = LazyInstructions(
            base,
            lambda: lead + instructions(auth.tutorial_phrase(self._ctx), **urls(self._ctx)),
        )
        return cast("InitializationOptions", lazy)


@dataclass(frozen=True)
class Outer:
    """What the tool needs from the HTTP request that carried the MCP call."""

    client_host: str  # the outer request's peer: the source the identity layer limits (F05-T19)


OUTER: contextvars.ContextVar[Outer | None] = contextvars.ContextVar("opn_mcp_outer", default=None)


#: F09-T23 (Q22): what a client shows a person for each tool, beside its name.
TITLES: dict[str, str] = {
    "server_info": "Server info",
    "list_targets": "List targets",
    "get_target": "Read a target",
    "list_frontier": "List open nodes",
    "get_node": "Read a node",
    "get_defs": "Read shared definitions",
    "get_gate_spec": "Read a gate spec",
    "get_submission": "Follow a submission",
    "list_submissions": "List open submissions",
    "get_schema": "Read a schema",
    "get_precheck": "Poll a precheck",
    "get_dco": "Read the DCO",
    "list_routes": "List HTTP routes",
    "get_hosted_checkers": "List hosted checkers",
    "list_my_claims": "List my claims",
    "get_my_submissions": "List my submissions",
    "get_check": "Read a fast check",
    "list_error_codes": "List error codes",
    "list_words_needed": "List files needing words",
    "claim_node": "Claim a node",
    "release_claim": "Release a claim",
    "precheck_submission": "Precheck a submission",
    "check_lean": "Fast-check Lean",
    "get_token": "Get a write token",
    "renew_token": "Renew a write token",
    "propose_witness": "Propose a hole witness",
    "submit_proof": "Submit a proof",
    "submit_postmortem": "Submit a postmortem",
    "submit_informal_annex": "Submit an informal annex",
    "submit_approach_record": "Submit an approach record",
    "file_defect_claim": "File a defect claim",
    "file_revision_request": "File a revision request",
    "propose_speculative_node": "Propose a crux statement",
    "propose_variant": "Propose a variant",
    "withdraw_submission": "Withdraw a submission",
    "submit_gloss": "Submit words for a file",
    "withdraw_gloss": "Withdraw words",
    "propose_literature": "Propose a literature status",
    "confirm_literature": "Confirm a literature status",
    "list_registrations": "List registry registrations",
    "set_display_name": "Set my display name",
    "register_target": "Record a registration",
    # F26-T10 (D-9, D-28 v3.39): the formalization review.
    "get_review": "Read a formalization review",
    "list_review_questions": "List review questions waiting",
    "submit_candidate": "Submit a candidate formalization",
    "list_open_pairs": "List open pair directions",
    # F27-T2 (D-25, D-28 v3.40)
    "list_sufficient_sets": "List routes and sufficient sets",
}


def declare(tool: Tool) -> types.Tool:
    row = bijection.BY_TOOL[tool.name]
    return types.Tool(
        name=tool.name,
        title=TITLES[tool.name],
        description=f"{tool.description} Plain path: {row.d28}.",
        inputSchema=tool.input_schema,
        outputSchema=results.declared(tool.name),
        annotations=types.ToolAnnotations(
            readOnlyHint=not tool.write, destructiveHint=False, idempotentHint=not tool.write
        ),
    )


def argument_hint(tool: Tool, arguments: dict[str, Any]) -> str:
    """F09-T75 (an agent, 2026-10-20): a refusal of the arguments as a whole also names what
    each missing argument is and which given ones the tool does not take, so an agent that
    passed a listing's ``id`` to ``get_submission`` learns ``submission_id`` is that value."""
    props: dict[str, Any] = tool.input_schema.get("properties", {})
    missing = [n for n in tool.input_schema.get("required", []) if n not in arguments]
    hint = "".join(
        f"; {n}: {props[n]['description']}" for n in missing if "description" in props.get(n, {})
    )
    unknown = sorted(k for k in arguments if k not in props)
    if unknown:
        hint += f"; not an argument of {tool.name}: {', '.join(unknown)}"
    return hint


#: mcpfix WA1 (qa-eb B2): an argument whose refusal the service names by a code of its own, per
#: operation: (code when it is missing, code when it is malformed). The adapter's schema check
#: runs first, so without this the service's documented codes never reached the caller.
FIELD_CODES: Mapping[str, Mapping[str, tuple[str, str]]] = {
    "precheck_submission": {"automation": ("automation-missing", "automation-invalid")},
    "submit_proof": {"automation": ("automation-missing", "automation-invalid")},
}
REQUIRED_RE = re.compile(r"^'(?P<name>[^']+)' is a required property")


def json_message(exc: jsonschema.ValidationError) -> str:
    """The validator's message with the values it quotes written as JSON (``null``, ``true``,
    ``"x"``), not as Python's repr (``None``, ``True``, ``'x'``). A ``type`` error's type names
    are words of the message, not values, and stay as they are."""
    message = exc.message
    values = [exc.instance] if exc.validator == "type" else [exc.instance, exc.validator_value]
    for value in values:
        python, plain = repr(value), json.dumps(value, ensure_ascii=False, default=str)
        if python != plain and python in message:
            message = message.replace(python, plain)
    return message


def where(exc: jsonschema.ValidationError) -> str:
    return "$" + "".join(f"[{p!r}]" for p in exc.absolute_path)


def schema_errors(schema: Mapping[str, Any], instance: Any) -> list[jsonschema.ValidationError]:
    """Every error the schema finds, sorted by the path of the value refused (qa-eb L3)."""
    validator = jsonschema.validators.validator_for(schema)(schema)
    return sorted(validator.iter_errors(instance), key=lambda e: [str(p) for p in e.absolute_path])


def described_errors(errors: list[jsonschema.ValidationError]) -> str:
    """Each error, located (F09-T10: the envelope is closed, so the path rides in the message)."""
    parts = [
        json_message(e) if where(e) == "$" else f"{where(e)}: {json_message(e)}" for e in errors
    ]
    return "; ".join(parts)


def field_of(exc: jsonschema.ValidationError) -> str | None:
    """The top-level argument an error is about: the head of its path, or the name a root
    ``required`` error says is missing."""
    if exc.absolute_path:
        return str(exc.absolute_path[0])
    m = REQUIRED_RE.match(exc.message) if exc.validator == "required" else None
    return m.group("name") if m else None


def is_missing(exc: jsonschema.ValidationError, name: str) -> bool:
    """Absent, null, or lacking a required field of its own: what the service calls missing."""
    path = list(exc.absolute_path)
    if exc.validator == "required" and path in ([], [name]):
        return True
    return path == [name] and exc.instance is None


def field_code(tool: Tool, errors: list[jsonschema.ValidationError]) -> str | None:
    """The service's own code when every error is about one argument it names a code for."""
    codes = FIELD_CODES.get(tool.name, {})
    fields = {field_of(e) for e in errors}
    if len(fields) != 1:
        return None
    [name] = fields
    if name is None or name not in codes:
        return None
    missing, invalid = codes[name]
    return missing if any(is_missing(e, name) for e in errors) else invalid


def arguments_refusal(tool: Tool, arguments: dict[str, Any]) -> ToolError | None:
    """The refusal of an operation's arguments, or ``None`` when its schema accepts them."""
    errors = schema_errors(tool.input_schema, arguments)
    if not errors:
        return None
    message = described_errors(errors)
    if any(where(e) == "$" for e in errors):
        message += argument_hint(tool, arguments)
    code = field_code(tool, errors)
    if code is not None:  # in the endpoint's words: the status the route would have answered
        return error(code, message, "adapter", status=400)
    return error("arguments-invalid", message, "adapter")


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
    return types.CallToolResult(content=text_block(doc), structuredContent=doc, isError=True)


def text_block(doc: dict[str, Any]) -> list[types.ContentBlock]:
    """The text a client without structured output reads: the structured content as compact
    JSON with its characters as they are (F09-T18, Q17). The SDK's own default is ``indent=2``
    with ASCII escapes, which cost about two fifths of a large result in whitespace and six
    characters for every Lean symbol."""
    return [
        types.TextContent(
            type="text", text=json.dumps(doc, separators=(",", ":"), ensure_ascii=False)
        )
    ]


def bare_error(doc: dict[str, Any]) -> types.CallToolResult:
    """An ``isError`` result of the three-tool surface (F09-T78) that names no operation."""
    return types.CallToolResult(content=text_block(doc), structuredContent=doc, isError=True)


async def run_operation(
    ctx: Context, host: Callable[[], ASGIApp], tool: Tool, arguments: dict[str, Any]
) -> tuple[list[types.ContentBlock], dict[str, Any]] | types.CallToolResult:
    """One operation, as a named tool runs it and as ``read`` and ``write`` run it (F09-T78):
    the arguments against its schema, the bearer gate (R2), the endpoint, the error envelope."""
    name = tool.name
    refusal = arguments_refusal(tool, arguments)
    if refusal is not None:
        return error_result(name, refusal.doc)
    token = auth.bearer() if tool.forwards_bearer else None
    if tool.needs_bearer and not token:  # R2: refused here, the endpoint never reached
        # A write answers in its envelope; a read of the caller's own records (F05-T14) in
        # the read tools' error shape, with the same code, message and status.
        body = auth.unauthorized(ctx)
        refusal = (
            writes.unauthorized(ctx)
            if tool.write
            else error(
                str(body["error"]),
                str(body["message"]),
                "adapter",
                status=auth.UNAUTHORIZED_STATUS,
            )
        )
        return error_result(name, refusal.doc)
    outer = OUTER.get()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(
            app=host(),
            raise_app_exceptions=False,
            client=(outer.client_host if outer else "127.0.0.1", 0),
        ),
        base_url=ctx.settings.public_url,
    ) as http:
        call = Call(ctx, http, token=token)
        try:
            doc = await tool.handler(call, arguments)
        except ToolError as failure:
            return error_result(name, failure.doc)
        except Exception as exc:  # C7: named, logged, never a partial answer
            log.error("%s failed: %s", name, type(exc).__name__, exc_info=exc)
            return error_result(
                name, error("internal", f"{name} failed: {type(exc).__name__}", "adapter").doc
            )
        # Both halves, so the SDK still validates the structured half against the output
        # schema and leaves the text as written (T18).
        return text_block(doc), doc


async def run_through(
    ctx: Context, host: Callable[[], ASGIApp], kind: str, arguments: dict[str, Any]
) -> types.CallToolResult:
    """``read`` or ``write`` (F09-T78): one operation of that kind, its result its own. No output
    schema is declared on the two tools, so the operation's is applied here, as the SDK applied
    it to the named tool (R9)."""
    name = arguments.get("operation")
    tool = BY_NAME.get(name) if isinstance(name, str) else None
    if tool is None:
        return bare_error(surface.unknown_operation(str(name), BY_NAME).doc)
    actual = "write" if tool.write else "read"
    if actual != kind:
        return bare_error(surface.kind_mismatch(tool.name, wanted=kind, actual=actual).doc)
    args = arguments.get("arguments") or {}
    if not isinstance(args, dict):
        return error_result(
            tool.name, error("arguments-invalid", "$['arguments']: not an object", "adapter").doc
        )
    answer = await run_operation(ctx, host, tool, args)
    if isinstance(answer, types.CallToolResult):
        return answer
    content, doc = answer
    problems = results.violations(tool.name, doc)
    if problems:  # a bug in the adapter, never hidden from the caller (C7)
        log.error("%s: result violates its schema: %s", tool.name, "; ".join(problems))
        return bare_error(
            error("internal", f"{tool.name} produced an unschematic result", "adapter").doc
        )
    return types.CallToolResult(content=content, structuredContent=doc)


def build_server(
    ctx: Context, host: Callable[[], ASGIApp], *, legacy: bool = False
) -> Server[Any, Any]:
    """The SDK server over ``ctx``; ``host`` yields the application the write tools call.
    ``legacy`` serves the named tools (``/mcp?surface=v1``, F09-T78); otherwise the three."""
    server: Server[Any, Any] = LiveServer(ctx, legacy=legacy)

    # The SDK's registration decorators are unannotated, hence the two ignores.
    @server.list_tools()  # type: ignore[untyped-decorator,no-untyped-call]
    async def list_tools() -> list[types.Tool]:
        return [declare(t) for t in TOOLS] if legacy else surface.declared()

    @server.call_tool(validate_input=False)  # type: ignore[untyped-decorator]
    async def call_tool(
        name: str, arguments: dict[str, Any]
    ) -> tuple[list[types.ContentBlock], dict[str, Any]] | types.CallToolResult:
        if legacy:
            tool = BY_NAME.get(name)
            if tool is None:
                message = (
                    f"no such tool {name}{surface.suggestion(name, BY_NAME)}; this surface has "
                    f"{len(TOOLS)} tools, named by tools/list"
                )
                return error_result("server_info", error("tool-unknown", message, "adapter").doc)
            return await run_operation(ctx, host, tool, arguments)
        return await run_surface(ctx, host, name, arguments)

    return server


async def run_surface(
    ctx: Context, host: Callable[[], ASGIApp], name: str, arguments: dict[str, Any]
) -> types.CallToolResult:
    """One call of the three-tool surface (F09-T78)."""
    schema = (
        surface.SEARCH_SCHEMA
        if name == surface.SEARCH
        else surface.call_schema(name)
        if name in (surface.READ, surface.WRITE)
        else None
    )
    if schema is None:
        message = f"no such tool {name}; the tools are search, read and write"
        return bare_error(error("tool-unknown", message, "adapter").doc)
    errors = schema_errors(schema, arguments)
    if errors:
        return bare_error(error("arguments-invalid", described_errors(errors), "adapter").doc)
    if name != surface.SEARCH:
        return await run_through(ctx, host, name, arguments)
    try:
        doc = surface.search(TOOLS, TITLES, arguments)
    except ToolError as failure:
        return bare_error(failure.doc)
    return types.CallToolResult(content=text_block(doc), structuredContent=doc)


def new_manager(server: Server[Any, Any]) -> StreamableHTTPSessionManager:
    return StreamableHTTPSessionManager(app=server, json_response=True, stateless=True)


def wants_legacy(scope: Scope) -> bool:
    """``?surface=v1`` selects the named tools (F09-T78, D-28 v3.50's transition window)."""
    query = scope.get("query_string", b"").decode("latin-1")
    return "surface=v1" in query.split("&")


class Mount:
    """The ASGI app at ``/mcp`` (R1): bearer verification, then the SDK's transport."""

    def __init__(self, ctx: Context, host: Callable[[], ASGIApp]) -> None:
        self.server = build_server(ctx, host)
        self.legacy = build_server(ctx, host, legacy=True)  # /mcp?surface=v1 (F09-T78)
        self._manager: StreamableHTTPSessionManager | None = None
        self._legacy_manager: StreamableHTTPSessionManager | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self.app: ASGIApp = AuthenticationMiddleware(
            AuthContextMiddleware(self._dispatch),
            backend=BearerAuthBackend(auth.StoreTokenVerifier(ctx)),
        )

    @contextlib.asynccontextmanager
    async def running(self) -> AsyncIterator[None]:
        """Enter the session manager for the host's lifetime — the host lifespan calls this."""
        manager, legacy = new_manager(self.server), new_manager(self.legacy)
        async with manager.run(), legacy.run():
            self._manager, self._legacy_manager = manager, legacy
            self._loop = asyncio.get_running_loop()
            try:
                yield
            finally:
                self._manager, self._legacy_manager, self._loop = None, None, None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.app(scope, receive, send)

    async def _dispatch(self, scope: Scope, receive: Receive, send: Send) -> None:
        conn = HTTPConnection(scope)
        outer = Outer(client_host=conn.client.host if conn.client else "unknown")
        token = OUTER.set(outer)
        legacy = wants_legacy(scope)
        try:
            manager = self._legacy_manager if legacy else self._manager
            if manager is not None and self._loop is asyncio.get_running_loop():
                await manager.handle_request(scope, receive, send)
                return
            # No lifespan runs on this loop (Mangum with lifespan off; a bare test client): a
            # manager for this request alone, which stateless mode makes the same thing (Q3).
            manager = new_manager(self.legacy if legacy else self.server)
            async with manager.run():
                await manager.handle_request(scope, receive, send)
        finally:
            OUTER.reset(token)
