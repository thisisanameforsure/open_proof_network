"""What a tool call is made of (F09-R7, R10): the api ``Context``, the caller's bearer, an
in-process HTTP client over the host application, and the two ways a call ends.

``Call.endpoint`` is how every route-backed tool reaches its plain path: a real HTTP request
through the same ASGI application, middleware and handlers a curl would hit, carrying the
caller's bearer and source address — so the tool result is the endpoint's response and nothing
else (R7), and the equivalence suite compares like with like (AC3, AC4).

A tool ends by returning its structured result, or by raising ``ToolError`` with the
structured error the schema's error branch describes: ``{error, message, source}`` for a plain
path that did not answer (R10) or arguments the adapter refused, and the response envelope
``{status, body}`` for an endpoint that refused (R7, R8).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

import httpx

if TYPE_CHECKING:
    from opn_api.app import Context

Source = Literal["graph", "service", "adapter"]
RETRY_AFTER = "retry-after"


class ToolError(Exception):
    """A tool result with ``isError`` set; ``doc`` is its structured content."""

    def __init__(self, doc: dict[str, Any]) -> None:
        super().__init__(str(doc.get("message") or doc.get("error") or doc.get("status")))
        self.doc = doc


def error(code: str, message: str, source: Source, *, status: int | None = None) -> ToolError:
    doc: dict[str, Any] = {"error": code, "message": message, "source": source}
    if status is not None:
        doc["status"] = status
    return ToolError(doc)


@dataclass(frozen=True)
class Answer:
    """An endpoint's response, as the tool passes it through (R7)."""

    status: int
    body: Any
    retry_after: str | None = None

    def envelope(self) -> dict[str, Any]:
        out: dict[str, Any] = {"status": self.status, "body": self.body}
        if self.retry_after is not None:
            out["retry_after"] = self.retry_after
        return out

    @property
    def refused(self) -> bool:
        return self.status >= 400


@dataclass
class Call:
    ctx: Context
    http: httpx.AsyncClient  # in-process, against the host application
    token: str | None = None  # the caller's verified bearer, forwarded and never logged (C8)
    forwarded_for: str | None = None  # the caller's source address, for the identity layer's limits
    calls: list[tuple[str, str]] = field(default_factory=list)  # (method, path) made, for tests

    async def endpoint(
        self, method: str, path: str, *, json: Mapping[str, Any] | None = None
    ) -> Answer:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self.forwarded_for:
            headers["X-Forwarded-For"] = self.forwarded_for
        self.calls.append((method, path))
        resp = await self.http.request(
            method, path, json=dict(json) if json else None, headers=headers
        )
        body: Any
        try:
            body = resp.json() if resp.content else None
        except ValueError:
            body = resp.text
        return Answer(resp.status_code, body, resp.headers.get(RETRY_AFTER))


Handler = Callable[[Call, dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class Tool:
    """One D-28 row as the server declares it: name, D-28's parameters as a JSON Schema, the
    handler, and whether it needs a bearer (R2)."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Handler
    write: bool = False


def params(
    properties: Mapping[str, Mapping[str, Any]], required: tuple[str, ...] = ()
) -> dict[str, Any]:
    """An input schema: named parameters, nothing else accepted."""
    return {
        "type": "object",
        "properties": {k: dict(v) for k, v in properties.items()},
        "required": list(required),
        "additionalProperties": False,
    }


ID_PARAM: dict[str, Any] = {"type": "string", "pattern": "^[a-z0-9][a-z0-9-]*$"}
