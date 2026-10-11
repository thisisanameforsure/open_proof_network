"""F05-T19 (audit 2026-10-04): the per-source limits key on the real source address.

``ratelimit.client_address`` took the first ``X-Forwarded-For`` hop. API Gateway's HTTP API
*appends* the caller's address to whatever ``X-Forwarded-For`` the caller sent, so the first hop
is the caller's to write: a fresh made-up hop per request made every per-source limit (token
starts, anonymous prechecks, anonymous checks) unlimited. Mangum (payload 2.0) puts
``requestContext.http.sourceIp`` — which the caller cannot set — into the ASGI ``client``, so
that is the address, and the header is ignored.
"""

from __future__ import annotations

import importlib
import os
import sys
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from api_fakes import TEST_ENV, make_harness
from starlette.testclient import TestClient

from opn_api import config

MODULE = "opn_api.lambda_handler"


@pytest.fixture
def fresh(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[[], Any]]:
    for name, value in TEST_ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("OPN_API_STORE", "memory")
    monkeypatch.setenv("OPN_API_TOKEN_STARTS_PER_DAY", "3")
    monkeypatch.setattr(config, "environment_with_parameters", lambda prefix: dict(os.environ))
    sys.modules.pop(MODULE, None)
    yield lambda: importlib.import_module(MODULE)
    sys.modules.pop(MODULE, None)


def start_event(source_ip: str, forwarded_for: str) -> dict[str, Any]:
    """``GET /auth/github/start`` as API Gateway's HTTP API hands it to the function: the caller's
    own ``X-Forwarded-For`` with the real address appended, and the real one in ``sourceIp``."""
    return {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": "/auth/github/start",
        "rawQueryString": "",
        "headers": {"host": "api.example", "x-forwarded-for": f"{forwarded_for}, {source_ip}"},
        "requestContext": {
            "http": {
                "method": "GET",
                "path": "/auth/github/start",
                "protocol": "HTTP/1.1",
                "sourceIp": source_ip,
                "userAgent": "test",
            },
            "stage": "$default",
        },
        "isBase64Encoded": False,
    }


def test_a_forged_forwarded_hop_per_request_does_not_escape_the_start_limit(
    fresh: Callable[[], Any],
) -> None:
    module = fresh()
    statuses = [
        module.handler(start_event("192.0.2.50", f"10.9.8.{n}"), None)["statusCode"]
        for n in range(4)
    ]
    assert statuses == [302, 302, 302, 429]


def test_the_peer_address_is_the_source_whatever_the_header_says() -> None:
    """Two sources sending the same ``X-Forwarded-For`` are limited separately, and one source
    cannot spend another's allowance by naming it."""
    h = make_harness({"OPN_API_TOKEN_STARTS_PER_DAY": "1"})
    one = TestClient(h.app, client=("203.0.113.7", 40000))
    two = TestClient(h.app, client=("198.51.100.2", 40000))
    same = {"X-Forwarded-For": "198.51.100.2"}

    def start(client: TestClient) -> int:
        r = client.get("/auth/github/start", headers=same, follow_redirects=False)
        return int(r.status_code)

    assert start(one) == 302
    assert start(one) == 429
    assert start(two) == 302  # untouched by the first source naming it
    assert start(two) == 429
