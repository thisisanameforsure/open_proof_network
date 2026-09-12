"""F12-T3: the Model seam (R6, R7, Q5, Q14; C5, C7, C8).

The seam is a thin one — one request shape, one answer — so what is tested is every way the
provider's answer is not a completion (a non-2xx, a refusal, a body with no text, not JSON, a
network error) and that each is a ``ModelError`` rather than text a brief would have recorded;
plus the two lookups R7's independence rule rests on.
"""

from __future__ import annotations

import json
import re

import httpx
import pytest

from opn_gate import models
from opn_gate.models import ModelError


def message(text: str = "Rendered.", **overrides: object) -> str:
    doc: dict[str, object] = {
        "type": "message",
        "model": "claude-opus-5-20260401",
        "stop_reason": "end_turn",
        "content": [{"type": "text", "text": text}],
        "usage": {"input_tokens": 12, "output_tokens": 3},
    }
    doc.update(overrides)
    return json.dumps(doc)


def test_a_completion_is_the_text_with_the_model_and_version() -> None:
    done = models.parse_completion(200, message("A thing."), model="claude-opus-5")
    assert done.text == "A thing." and done.model == "claude-opus-5"
    assert done.version == "claude-opus-5-20260401"
    assert (done.input_tokens, done.output_tokens) == (12, 3)


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (500, "{}", "answered 500"),
        (401, "{}", "answered 401"),
        (200, "not json", "not JSON"),
        (200, json.dumps({"type": "error"}), "not a message"),
        (200, message(stop_reason="refusal", stop_details={"category": "bio"}), "declined (bio)"),
        (200, message(stop_reason="refusal", stop_details=None), "declined (no category)"),
        (200, message(content=[{"type": "thinking", "thinking": ""}]), "no text"),
    ],
)
def test_anything_but_a_completion_is_a_model_error(status: int, body: str, expected: str) -> None:
    """AC19, C7: an error body is never recorded as a judgement."""
    with pytest.raises(ModelError, match=re.escape(expected)):
        models.parse_completion(status, body, model="claude-opus-5")


def test_the_real_client_sends_the_documented_shape() -> None:
    """The Messages API request: the model, one user turn, the system prompt, the key in the
    header and never in the body, no thinking configuration (Claude Opus 5 runs adaptive)."""
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["headers"] = dict(request.headers)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, text=message("English."))

    client = models.HttpxModelClient(
        "sk-test-key", "claude-opus-5", transport=httpx.MockTransport(handler)
    )
    done = client.complete(system="Be brief.", prompt="theorem t : True := trivial")
    assert done.text == "English." and client.model == "claude-opus-5"
    assert seen["url"] == models.MESSAGES_URL
    headers = seen["headers"]
    assert isinstance(headers, dict)
    assert headers["x-api-key"] == "sk-test-key"
    assert headers["anthropic-version"] == models.API_VERSION
    body = seen["body"]
    assert isinstance(body, dict)
    assert body["model"] == "claude-opus-5" and body["system"] == "Be brief."
    assert body["messages"] == [{"role": "user", "content": "theorem t : True := trivial"}]
    assert "thinking" not in body and "sk-test-key" not in json.dumps(body)


def test_a_network_failure_is_a_model_error_without_the_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    client = models.HttpxModelClient("sk-secret", transport=httpx.MockTransport(handler))
    with pytest.raises(ModelError) as failure:
        client.complete(system="s", prompt="p")
    assert "ConnectError" in str(failure.value) and "sk-secret" not in str(failure.value)


def test_family_and_formalizer_lookups() -> None:
    """R7: the family is a model id's leading letters; provenance names an AI formalizer by
    substring, or names none and is `unknown`."""
    assert models.family_of("claude-opus-5") == "claude"
    assert models.family_of("Gemini-3-pro") == "gemini"
    assert models.formalizer_family("Claude Opus 4.5 via the lean-genius pipeline") == "claude"
    assert models.formalizer_family("AlphaProof (Google DeepMind)") == "gemini"
    assert models.formalizer_family("Aristotle by Harmonic") == "aristotle"
    assert models.formalizer_family("T. Tao") == models.FORMALIZER_UNKNOWN
    assert models.formalizer_family(None) == models.FORMALIZER_UNKNOWN
    assert models.formalizer_family("") == models.FORMALIZER_UNKNOWN
