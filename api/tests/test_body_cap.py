"""The request body cap (F05 §6, Q7; C6, C7): one limit, enforced once, ahead of every parser.

``BodyCap`` in ``app.py`` refuses a body larger than ``OPN_API_MAX_BODY_BYTES`` with a named
413 before authentication, rate limiting or parsing run. The cap is set small here so the
boundary can be walked byte by byte: exactly at the cap is parsed, one byte over is refused,
whatever the content type. The content type itself is deliberately not enforced (Q7): a JSON
body with no ``Content-Type`` at all is still parsed as JSON.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from api_fakes import Harness, make_harness
from starlette.requests import Request

from opn_api import bundles, config
from opn_api.app import ApiError, BodyCap, _content_length

CAP = 64


@pytest.fixture
def capped() -> Harness:
    return make_harness({"OPN_API_MAX_BODY_BYTES": str(CAP)})


def padded_json(size: int) -> bytes:
    """A JSON object of exactly ``size`` bytes with no usable fields."""
    frame = b'{"pad": ""}'
    body = b'{"pad": "' + b"x" * (size - len(frame)) + b'"}'
    assert len(body) == size
    return body


def test_a_body_exactly_at_the_cap_is_parsed(capped: Harness) -> None:
    r = capped.client.post(
        "/tokens", content=padded_json(CAP), headers={"Content-Type": "application/json"}
    )
    # The parser saw the fields and found no pseudonym: the body got through.
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "pseudonym-invalid"


def test_one_byte_over_the_cap_is_a_named_413_that_names_the_cap(capped: Harness) -> None:
    r = capped.client.post(
        "/tokens", content=padded_json(CAP + 1), headers={"Content-Type": "application/json"}
    )
    assert r.status_code == 413, r.text
    assert r.json()["error"] == "body-too-large"
    assert str(CAP) in r.json()["message"]


def test_a_form_body_over_the_cap_is_refused_too(capped: Harness) -> None:
    """The cap is on bytes, not on a content type: the browser form (Q4) is bounded the same
    way as an agent's JSON."""
    r = capped.client.post(
        "/tokens",
        content=b"pseudonym=" + b"x" * CAP,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 413, r.text
    assert r.json()["error"] == "body-too-large"


def test_an_over_cap_body_is_refused_before_authentication(capped: Harness) -> None:
    """An authenticated write route with no bearer and an oversized body answers 413, not 401:
    the cap runs ahead of the bearer gate, so nothing downstream ever sees the body."""
    r = capped.client.post(
        "/claims", content=padded_json(CAP + 1), headers={"Content-Type": "application/json"}
    )
    assert r.status_code == 413, r.text
    assert capped.store.claims == {}


def test_a_body_without_a_length_is_counted_as_it_streams() -> None:
    """A chunked body declares no Content-Length; the middleware counts the bytes it hands the
    handler and refuses the moment they pass the cap, inside the handler's ``request.body()``."""
    received: list[bytes] = []

    async def handler(scope: Any, receive: Any, send: Any) -> None:
        received.append(await Request(scope, receive).body())

    chunks = [b"x" * 40, b"x" * 40, b""]

    async def receive() -> dict[str, Any]:
        body = chunks.pop(0)
        return {"type": "http.request", "body": body, "more_body": bool(chunks)}

    async def send(message: Any) -> None:
        raise AssertionError("nothing is sent by the handler here")

    scope = {"type": "http", "method": "POST", "path": "/tokens", "headers": []}
    with pytest.raises(ApiError, match="exceeds the limit of 64 bytes") as raised:
        asyncio.run(BodyCap(handler, cap=CAP)(scope, receive, send))
    assert raised.value.status == 413
    assert raised.value.code == "body-too-large"
    assert received == []


def test_a_non_numeric_content_length_falls_back_to_counting() -> None:
    assert _content_length({"headers": [(b"content-length", b"lots")]}) is None
    assert _content_length({"headers": [(b"content-length", b"12")]}) == 12
    assert _content_length({"headers": []}) is None


def test_the_content_type_is_not_enforced(harness: Harness) -> None:
    """Q7: agents are sloppy with headers. A JSON body with no Content-Type is parsed as JSON,
    so the failure it earns is about its fields, not its framing."""
    r = harness.client.post("/tokens", content=b'{"pseudonym": "a b"}', headers={})
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "pseudonym-invalid"


# --- configuration (C6) ---------------------------------------------------------------------------


def test_the_default_cap_is_one_mebibyte_and_above_the_bundle_limit() -> None:
    assert config.load({}).max_body_bytes == 1024 * 1024
    assert config.DEFAULT_MAX_BODY_BYTES == 1024 * 1024
    # A 512 KiB bundle arrives inside a JSON envelope; the cap must leave it room (F06 §6).
    assert config.DEFAULT_MAX_BODY_BYTES > bundles.MAX_BUNDLE_BYTES * 1.5


def test_the_cap_is_configurable_and_must_be_positive() -> None:
    assert config.load({"OPN_API_MAX_BODY_BYTES": "2048"}).max_body_bytes == 2048
    with pytest.raises(config.ConfigError, match="positive"):
        config.load({"OPN_API_MAX_BODY_BYTES": "0"})
    with pytest.raises(config.ConfigError, match="integer"):
        config.load({"OPN_API_MAX_BODY_BYTES": "1M"})
