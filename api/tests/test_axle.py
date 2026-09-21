"""F13-T2: the real AXLE seam, ``HttpxAxle``, driven without a network.

As in ``test_githost_seam``, ``httpx.Client`` is replaced inside ``opn_api.axle`` only by one
bound to a scripted ``MockTransport``. The wire shapes asserted here are the ones the live
service accepted on 2026-09-14 (``engineering/evidence/F13/task-1.txt``); every failing case must
become an ``AxleError`` naming the call and the status, never a key.
"""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest

from opn_api import axle, config
from opn_api.axle import AxleError, HttpxAxle

BASE = "https://axle.example.test"
KEY = "axle_SENTINEL_KEY_NEVER_LOGGED"
ANSWER = {
    "okay": False,
    "failed_declarations": ["t"],
    "lean_messages": {"errors": ["-:5:17-5:22: error: omega could not prove the goal"]},
    "tool_messages": {"infos": ["-:5:17: info: unsolved goals at error"]},
    "info": {"request_id": "8d2d5549", "environment": "lean-4.33.0"},
}


@dataclass
class Script:
    replies: deque[httpx.Response | Exception] = field(default_factory=deque)
    requests: list[httpx.Request] = field(default_factory=list)

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        reply = self.replies.popleft()
        if isinstance(reply, Exception):
            raise reply
        return reply

    def answer(self, status: int = 200, **kwargs: Any) -> None:
        self.replies.append(httpx.Response(status, **kwargs))


class _Httpx:
    """``opn_api.axle.httpx`` for one test: the real module with ``Client`` bound to the script."""

    def __init__(self, client: type[httpx.Client]) -> None:
        self._client = client

    def __getattr__(self, name: str) -> Any:
        return self._client if name == "Client" else getattr(httpx, name)


@pytest.fixture
def script(monkeypatch: pytest.MonkeyPatch) -> Script:
    scripted = Script()

    class Scripted(httpx.Client):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(transport=httpx.MockTransport(scripted.handler), **kwargs)

    monkeypatch.setattr(axle, "httpx", _Httpx(Scripted))
    return scripted


def test_check_sends_the_verified_wire_shape_and_returns_the_body_verbatim(script: Script) -> None:
    script.answer(json=ANSWER)
    got = HttpxAxle(base_url=BASE + "/").check(
        "import Mathlib\n", environment="lean-4.33.0", timeout_s=60
    )
    (req,) = script.requests
    assert (req.method, str(req.url)) == ("POST", f"{BASE}/api/v1/check")
    assert json.loads(req.content) == {
        "content": "import Mathlib\n",
        "environment": "lean-4.33.0",
        "timeout_seconds": 60,
    }
    assert "authorization" not in req.headers  # keyless at Stage 0 (Q5)
    assert got.body == ANSWER and got.request_id == "8d2d5549" and got.latency_ms >= 0


def test_verify_proof_sends_the_formal_statement(script: Script) -> None:
    script.answer(json={"okay": True, "info": {}})
    got = HttpxAxle(base_url=BASE).verify_proof(
        "proof", formal_statement="stmt", environment="lean-4.33.0", timeout_s=30
    )
    (req,) = script.requests
    assert str(req.url) == f"{BASE}/api/v1/verify_proof"
    assert json.loads(req.content) == {
        "formal_statement": "stmt",
        "content": "proof",
        "environment": "lean-4.33.0",
        "timeout_seconds": 30,
    }
    assert got.request_id is None  # an info block without an id is not an error


def test_environments_lists_names(script: Script) -> None:
    script.answer(json=[{"name": "lean-4.33.0"}, {"name": "lean-4.32.2"}, {"nameless": 1}])
    assert HttpxAxle(base_url=BASE).environments() == ["lean-4.33.0", "lean-4.32.2"]
    assert str(script.requests[0].url) == f"{BASE}/v1/environments"


def test_a_key_is_sent_as_bearer_and_never_named_in_an_error(script: Script) -> None:
    script.answer(503, text="<html>bad gateway</html>")
    with pytest.raises(AxleError) as err:
        HttpxAxle(base_url=BASE, api_key=KEY).check("x", environment="e", timeout_s=1)
    assert script.requests[0].headers["authorization"] == f"Bearer {KEY}"
    assert err.value.status == 503 and KEY not in str(err.value)


@pytest.mark.parametrize(
    ("reply", "status", "words"),
    [
        (httpx.ConnectTimeout("slow"), None, "check failed: ConnectTimeout"),
        (httpx.Response(429, json={"detail": "busy"}), 429, "check returned 429"),
        (httpx.Response(502, text="<html>"), 502, "check returned 502"),
        (httpx.Response(200, text="<html>"), 200, "non-JSON body for check"),
        (httpx.Response(200, json=["not", "an", "object"]), 200, "list, not an object, for check"),
    ],
)
def test_each_failure_is_an_axle_error_naming_the_call(
    script: Script, reply: httpx.Response | Exception, status: int | None, words: str
) -> None:
    script.replies.append(reply)
    with pytest.raises(AxleError) as err:
        HttpxAxle(base_url=BASE).check("x", environment="e", timeout_s=1)
    assert err.value.status == status and words in str(err.value)


@pytest.mark.parametrize(
    ("reply", "words"),
    [
        (httpx.ReadTimeout("slow"), "environments failed: ReadTimeout"),
        (httpx.Response(500), "environments returned 500"),
        (httpx.Response(200, text="nope"), "non-JSON body for environments"),
        (httpx.Response(200, json={"name": "x"}), "dict, not an array, for environments"),
    ],
)
def test_environment_listing_failures_are_axle_errors(
    script: Script, reply: httpx.Response | Exception, words: str
) -> None:
    script.replies.append(reply)
    with pytest.raises(AxleError, match=words):
        HttpxAxle(base_url=BASE).environments()


def test_settings_name_the_service_and_the_budget() -> None:
    """R3, §6: the base URL and the per-call budget are config with documented defaults (C6)."""
    default = config.load({})
    assert default.axle_url == "https://axle.axiommath.ai" and default.check_timeout_s == 20  # T13
    custom = config.load({"OPN_API_AXLE_URL": BASE + "/", "OPN_API_CHECK_TIMEOUT_S": "5"})
    assert custom.axle_url == BASE and custom.check_timeout_s == 5
    with pytest.raises(config.ConfigError, match="OPN_API_CHECK_TIMEOUT_S"):
        config.load({"OPN_API_CHECK_TIMEOUT_S": "0"})
    built = axle.build(custom)
    assert isinstance(built, HttpxAxle)
