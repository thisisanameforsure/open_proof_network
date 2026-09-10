"""The two entrypoints, ``opn_api.lambda_handler`` and ``opn_api.local`` (F05-R1, R2, T1; C7,
C8).

The Lambda module builds the application at import, so each test imports it fresh under a
patched parameter loader — no boto3 call is made. The local runner's HTTP bridge is driven
with an in-memory ``StreamReader`` and a recording writer: each case is a malformed or failing
connection the bridge must close or answer 500, never hang.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import os
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest
from api_fakes import TEST_ENV
from mangum import Mangum

from opn_api import config, local

MODULE = "opn_api.lambda_handler"


@pytest.fixture
def fresh(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[[], Any]]:
    """Import the Lambda module anew, and leave no copy behind for another test to reuse."""
    for name, value in TEST_ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("OPN_API_STORE", "memory")
    sys.modules.pop(MODULE, None)
    yield lambda: importlib.import_module(MODULE)
    sys.modules.pop(MODULE, None)


def test_lambda_build_falls_back_to_the_environment_when_parameter_store_is_unreadable(
    fresh: Callable[[], Any], monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """C7: the function still comes up (health will then name what is missing); C8: the log
    line carries the prefix and the exception's type, never its message."""

    def unreadable(prefix: str) -> dict[str, str]:
        msg = "AccessDeniedException: arn:aws:ssm:eu-west-1:123456789012:parameter/opn/secret"
        raise RuntimeError(msg)

    monkeypatch.setattr(config, "environment_with_parameters", unreadable)
    monkeypatch.setenv("OPN_API_PARAMETER_PREFIX", "/opn/test/")
    monkeypatch.setenv("OPN_API_PUBLIC_URL", "https://from-environ.example/")
    with caplog.at_level(logging.ERROR, logger="opn_api"):
        module = fresh()
    assert isinstance(module.handler, Mangum)
    (line,) = [r.getMessage() for r in caplog.records if "parameter store" in r.getMessage()]
    assert line == "parameter store unreadable under /opn/test/: RuntimeError"
    assert "arn:aws" not in caplog.text
    app: Any = module.handler.app  # the isinstance above narrows .app to the ASGI protocol
    settings = app.state.context.settings
    assert settings.public_url == "https://from-environ.example"


def test_lambda_build_applies_the_parameters_over_the_environment(
    fresh: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[str] = []

    def readable(prefix: str) -> dict[str, str]:
        seen.append(prefix)
        return {
            **dict(os.environ),
            "OPN_API_PUBLIC_URL": "https://from-parameters.example",
            "OPN_API_TOKEN_SECRET": "from-parameters",
        }

    monkeypatch.setattr(config, "environment_with_parameters", readable)
    monkeypatch.setenv("OPN_API_PARAMETER_PREFIX", "/opn/prod/")
    monkeypatch.setenv("OPN_API_PUBLIC_URL", "https://from-environ.example")
    module = fresh()
    assert seen == ["/opn/prod/"]
    settings = module.handler.app.state.context.settings
    assert settings.public_url == "https://from-parameters.example"
    assert settings.token_secret == "from-parameters"  # noqa: S105 — a sentinel, not a secret


def test_lambda_handler_serves_a_health_event(
    fresh: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config, "environment_with_parameters", lambda prefix: dict(os.environ))
    module = fresh()
    event = {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": "/health",
        "rawQueryString": "",
        "headers": {"host": "api.example"},
        "requestContext": {
            "http": {
                "method": "GET",
                "path": "/health",
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "test",
            },
            "stage": "$default",
        },
        "isBase64Encoded": False,
    }
    response = module.handler(event, None)
    assert response["statusCode"] == 200, response


# --- the local runner's HTTP bridge ------------------------------------------------------------


@dataclass
class Writer:
    written: bytes = b""
    closed: bool = False
    drains: int = 0

    def write(self, data: bytes) -> None:
        self.written += data

    async def drain(self) -> None:
        self.drains += 1

    def close(self) -> None:
        self.closed = True

    def is_closing(self) -> bool:
        return self.closed

    def get_extra_info(self, name: str) -> Any:
        return ("10.0.0.7", 4321) if name == "peername" else None


@dataclass
class Seen:
    scopes: list[dict[str, Any]] = field(default_factory=list)
    bodies: list[bytes] = field(default_factory=list)


def echo_app(seen: Seen, status: int = 200) -> Callable[..., Any]:
    async def app(scope: dict[str, Any], receive: Any, send: Any) -> None:
        seen.scopes.append(scope)
        message = await receive()
        seen.bodies.append(message["body"])
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [(b"content-type", b"text/plain")],
            }
        )
        await send({"type": "http.response.body", "body": b"ok", "more_body": False})

    return app


def raising_app() -> Callable[..., Any]:
    async def app(scope: dict[str, Any], receive: Any, send: Any) -> None:
        msg = "boom"
        raise RuntimeError(msg)

    return app


def serve(app: Callable[..., Any], raw: bytes) -> Writer:
    async def run() -> Writer:
        reader = asyncio.StreamReader(limit=local.MAX_HEADER_BYTES)
        reader.feed_data(raw)
        reader.feed_eof()
        writer = Writer()
        await local.serve_connection(app, reader, writer)  # type: ignore[arg-type]
        return writer

    return asyncio.run(run())


def test_local_closes_a_connection_whose_head_never_ends() -> None:
    seen = Seen()
    writer = serve(echo_app(seen), b"GET /health HTTP/1.1\r\nhost: x")
    assert writer.closed
    assert writer.written == b""
    assert seen.scopes == []


def test_local_closes_a_head_over_the_limit() -> None:
    seen = Seen()
    writer = serve(echo_app(seen), b"GET / HTTP/1.1\r\nx: " + b"a" * local.MAX_HEADER_BYTES)
    assert writer.closed
    assert seen.scopes == []


def test_local_answers_500_when_the_app_raises(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR, logger="opn_api.local"):
        writer = serve(raising_app(), b"GET /health HTTP/1.1\r\nhost: x\r\n\r\n")
    assert writer.written.startswith(b"HTTP/1.1 500 Internal Server Error\r\n")
    assert b"connection: close" in writer.written
    assert writer.closed
    assert "request failed" in caplog.text


def test_local_does_not_write_a_second_status_when_the_app_raises_after_starting() -> None:
    async def half(scope: dict[str, Any], receive: Any, send: Any) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"partial", "more_body": False})
        msg = "after the response"
        raise RuntimeError(msg)

    writer = serve(half, b"GET / HTTP/1.1\r\n\r\n")
    assert writer.written.count(b"HTTP/1.1 ") == 1
    assert writer.written.startswith(b"HTTP/1.1 200 OK\r\n")


def test_local_builds_the_scope_and_frames_the_response() -> None:
    seen = Seen()
    raw = (
        b"POST /claims%2Fx?ttl=2&x=y HTTP/1.1\r\n"
        b"Host: localhost\r\nContent-Type: application/json\r\nContent-Length: 7\r\n\r\n"
        b'{"a":1}'
    )
    writer = serve(echo_app(seen, status=418), raw)
    (scope,) = seen.scopes
    assert scope["method"] == "POST"
    assert scope["path"] == "/claims/x"
    assert scope["raw_path"] == b"/claims%2Fx"
    assert scope["query_string"] == b"ttl=2&x=y"
    assert scope["client"] == ("10.0.0.7", 4321)
    assert (b"content-length", b"7") in scope["headers"]
    assert (b"host", b"localhost") in scope["headers"]
    assert seen.bodies == [b'{"a":1}']
    assert writer.written == (
        b"HTTP/1.1 418 \r\ncontent-type: text/plain\r\nconnection: close\r\n\r\nok"
    )
    assert writer.closed


def test_local_request_without_a_body_hands_the_app_an_empty_body() -> None:
    seen = Seen()
    serve(echo_app(seen), b"GET /health HTTP/1.1\r\nhost: x\r\n\r\n")
    assert seen.bodies == [b""]


def test_local_main_refuses_a_bad_port() -> None:
    with pytest.raises(SystemExit) as raised:
        local.main(["--port", "not-a-number"])
    assert raised.value.code == 2
