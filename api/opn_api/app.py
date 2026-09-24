"""The api application (F05-R1, R5, R11, R13).

``create_app`` wires the routes table (``routes.py``) to handlers over one ``Context`` holding
the seams — ``Store``, ``GitHost``, ``Clock`` — and the configuration. Every handler has the
signature ``async (ctx, request) -> Response``; the binding applies, in order: the R13 gate
(503 while a table or parameter is missing), bearer authentication for authenticated routes
(R5), the per-identity write limit (R6), then the handler. Errors are ``ApiError`` and render
as ``{"error": code, "message": ...}``, plus ``details`` when the refusal carries them (F05-T9);
anything else is logged and becomes a 500 (C7).

Before any of that, ``BodyCap`` refuses a request body larger than ``settings.max_body_bytes``
with a 413 ``body-too-large`` (§6): the one place the cap is enforced, ahead of every parser.
The content type is deliberately not enforced (Q7).

Request logging (R11): method, route template, identity id (never the token), status and
duration, at INFO; no request or response body is logged above DEBUG.

The MCP server (F09) is mounted at ``/mcp`` beside the routes table, not in it: it is a lens
over those routes (D-28), and its session manager runs from this application's lifespan.
"""

from __future__ import annotations

import contextlib
import importlib
import logging
import threading
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from opn_api import auth, config, ratelimit
from opn_api import axle as axlemod
from opn_api import clock as clockmod
from opn_api import githost as githostmod
from opn_api import store as storemod
from opn_api.axle import Axle
from opn_api.clock import Clock
from opn_api.githost import GitHost, PullRequestState
from opn_api.routes import ROUTES, RouteSpec
from opn_api.store import Store

log = logging.getLogger("opn_api")
access_log = logging.getLogger("opn_api.access")


class ApiError(Exception):
    """A response the handler chose: status, machine-readable code, human message, and — for a
    refusal whose reason is data as well as prose — ``details``, rendered only when given
    (F05-T9: a blocked node's cause and unproved dependencies, a listed node's reasons)."""

    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        *,
        headers: Mapping[str, str] | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.headers = dict(headers or {})
        self.details = dict(details) if details is not None else None

    def response(self) -> JSONResponse:
        body: dict[str, Any] = {"error": self.code, "message": self.message}
        if self.details is not None:
            body["details"] = self.details
        return JSONResponse(body, self.status, headers=self.headers)


@dataclass
class CachedFile:
    """A committed file fetched from the graph, reused until ``max_stale_s`` then revalidated."""

    path: str
    body: bytes | None = None
    etag: str | None = None
    fetched_at: float = 0.0


@dataclass
class CachedPull:
    """A pull request's live state read through the App (F07-T16), reused for
    ``frontier_max_stale_s``; ``state`` is ``None`` when the host had no such pull request."""

    number: int
    state: PullRequestState | None = None
    fetched_at: float = 0.0


@dataclass
class Context:
    settings: config.Settings
    store: Store
    githost: GitHost
    clock: Clock
    axle: Axle  # F13: the hosted fast checker (D-4 v3.14)
    missing: list[str] = field(default_factory=list)
    files: dict[str, CachedFile] = field(default_factory=dict)
    pulls: dict[int, CachedPull] = field(default_factory=dict)
    # F07-T26: a failed gate run's verdict, by the head commit it ran on. A verdict is a fact
    # about a commit, so it is read once; ``None`` is kept too (the run kept no artifact).
    verdicts: dict[str, dict[str, Any] | None] = field(default_factory=dict)
    # F05-T13: the commit ``main`` pointed to when last asked, and when that was. Every committed
    # file is read at it; ``None`` until the API has answered once.
    head: str | None = None
    head_checked_at: float | None = None
    # F13-R8, Q8: this application's in-flight cap on the hosted checker, made on first use. It
    # lives here rather than in a table keyed by id(ctx), because a collected Context's address
    # is reused by the next one (checks.slots).
    check_slots: threading.BoundedSemaphore | None = None
    # F07-T39, Q47: one lock per pull request, held while a record is reconciled (its live read,
    # a racer's conversion, its closing), so two threads never do that work twice for one pull
    # request; ``pr_locks_guard`` makes the table itself safe to grow from several threads.
    pr_locks: dict[int, threading.RLock] = field(default_factory=dict)
    pr_locks_guard: threading.Lock = field(default_factory=threading.Lock)


Handler = Callable[[Context, Request], Awaitable[Response]]


def resolve(handler: str) -> Handler:
    module_name, _, function = handler.partition(":")
    module = importlib.import_module(f"opn_api.{module_name}")
    fn: Handler = getattr(module, function)
    return fn


def bind(ctx: Context, spec: RouteSpec) -> Callable[[Request], Awaitable[Response]]:
    fn = resolve(spec.handler)

    async def endpoint(request: Request) -> Response:
        request.state.route = spec.label
        if ctx.missing and spec.path != "/health":
            raise ApiError(503, "not-configured", "missing: " + ", ".join(ctx.missing))
        if spec.authenticated:
            identity = auth.authenticate(ctx, request)
            request.state.identity_id = identity.id
            request.state.identity = identity
            ratelimit.check_write(ctx, identity.id)
        return await fn(ctx, request)

    return endpoint


async def health(ctx: Context, request: Request) -> Response:
    """R13: 200 with the store kind, or 503 naming every missing table or parameter."""
    if ctx.missing:
        return JSONResponse({"ok": False, "missing": list(ctx.missing)}, 503)
    return JSONResponse({"ok": True, "store": ctx.settings.store})


class AccessLog:
    """Pure-ASGI middleware: one INFO line per request (R11)."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        scope.setdefault("state", {})
        started = time.perf_counter()
        status = 0

        async def send_wrapper(message: Any) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = int(message["status"])
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            state = scope.get("state") or {}
            access_log.info(
                "%s %s identity=%s status=%d ms=%d",
                scope.get("method"),
                state.get("route", scope.get("path")),
                state.get("identity_id", "-"),
                status,
                int((time.perf_counter() - started) * 1000),
            )


class BodyCap:
    """Pure-ASGI middleware: refuse a request body over ``cap`` bytes with a 413 (F05 §6).

    A declared ``Content-Length`` over the cap is refused before the handler runs at all — no
    authentication, no rate-limit charge, no parsing. A body sent without a length (chunked)
    is counted as it streams and refused the moment it passes the cap; the error is raised
    inside the handler's ``request.body()`` and rendered by the ``ApiError`` handler like any
    other named refusal. Nothing else in the api needs to know the cap exists.
    """

    def __init__(self, app: Any, *, cap: int) -> None:
        self.app = app
        self.cap = cap

    def error(self) -> ApiError:
        return ApiError(
            413, "body-too-large", f"the request body exceeds the limit of {self.cap} bytes"
        )

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = _content_length(scope)
        if declared is not None and declared > self.cap:
            await self.error().response()(scope, receive, send)
            return
        seen = 0

        async def counting_receive() -> Any:
            nonlocal seen
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > self.cap:
                    raise self.error()
            return message

        await self.app(scope, counting_receive, send)


def _content_length(scope: Any) -> int | None:
    """The declared body length, or ``None`` when absent or not a number (then the body is
    counted as it arrives instead)."""
    for name, value in scope.get("headers", ()):
        if name == b"content-length":
            try:
                return int(value)
            except ValueError:
                return None
    return None


async def _api_error(request: Request, exc: Exception) -> Response:
    assert isinstance(exc, ApiError)
    return exc.response()


async def _unexpected(request: Request, exc: Exception) -> Response:
    log.error("unhandled %s on %s", type(exc).__name__, request.url.path, exc_info=exc)
    return JSONResponse({"error": "internal", "message": "internal error"}, 500)


async def _not_found(request: Request, exc: Exception) -> Response:
    return JSONResponse({"error": "not-found", "message": "no such route"}, 404)


def create_app(
    settings: config.Settings,
    *,
    store: Store | None = None,
    githost: GitHost | None = None,
    clock: Clock | None = None,
    axle: Axle | None = None,
) -> Starlette:
    """Build the application. Seams default to the real implementations the settings name."""
    missing = settings.missing()
    if store is None:
        try:
            store = storemod.build(settings)
        except Exception as exc:
            log.error("store unavailable: %s", type(exc).__name__)
            missing.append(f"store ({type(exc).__name__})")
            store = storemod.MemoryStore()
    if not missing:
        missing.extend(store.check())
    ctx = Context(
        settings=settings,
        store=store,
        githost=githost if githost is not None else githostmod.build(settings),
        clock=clock if clock is not None else clockmod.SystemClock(),
        axle=axle if axle is not None else axlemod.build(settings),
        missing=missing,
    )
    if missing:
        log.error("serving 503 until configured; missing: %s", ", ".join(missing))
    from opn_api.mcp import server as mcpmod  # noqa: PLC0415 — the adapter imports this module

    mcp = mcpmod.Mount(ctx, lambda: app)
    routes = [Route(r.path, bind(ctx, r), methods=[r.method], name=r.label) for r in ROUTES]
    routes.append(Route(mcpmod.MCP_PATH, mcp, methods=["GET", "POST", "DELETE"], name="mcp"))

    @contextlib.asynccontextmanager
    async def lifespan(_: Starlette) -> AsyncIterator[None]:
        async with mcp.running():
            yield

    app = Starlette(
        routes=routes,
        middleware=[
            Middleware(AccessLog),
            Middleware(BodyCap, cap=settings.max_body_bytes),  # inside the log, so a 413 is logged
        ],
        exception_handlers={ApiError: _api_error, 404: _not_found, Exception: _unexpected},
        lifespan=lifespan,
    )
    app.state.context = ctx
    app.state.mcp = mcp
    return app
