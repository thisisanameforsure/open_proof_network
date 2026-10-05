"""F12-T3: the Model seam (R6, R7, Q5, Q14; C5, C7, C8), through OpenRouter since 2026-10-05.

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

MODEL = "anthropic/claude-opus-5.5"


def message(
    text: str | None = "Rendered.", finish_reason: str = "stop", **overrides: object
) -> str:
    """A chat completion as OpenRouter documents it (openrouter.ai/docs/api-reference)."""
    doc: dict[str, object] = {
        "id": "gen-1",
        "object": "chat.completion",
        "model": "anthropic/claude-opus-5.5-20260901",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": finish_reason,
            }
        ],
        "usage": {"prompt_tokens": 12, "completion_tokens": 3, "total_tokens": 15},
    }
    doc.update(overrides)
    return json.dumps(doc)


def test_a_completion_is_the_text_with_the_model_and_version() -> None:
    done = models.parse_completion(200, message("A thing."), model=MODEL)
    assert done.text == "A thing." and done.model == MODEL
    assert done.version == "anthropic/claude-opus-5.5-20260901"
    assert (done.input_tokens, done.output_tokens) == (12, 3)


def test_the_default_model_is_opus_5_5_through_openrouter() -> None:
    """The owner's choice, 2026-10-05: Claude Opus 5.5, named as OpenRouter lists it."""
    assert models.DEFAULT_MODEL == MODEL
    assert models.COMPLETIONS_URL == "https://openrouter.ai/api/v1/chat/completions"


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (500, "{}", "answered 500"),
        (401, "{}", "answered 401"),
        (
            402,
            json.dumps({"error": {"code": 402, "message": "Insufficient credits"}}),
            "answered 402",
        ),
        (429, "{}", "answered 429"),
        (200, "not json", "not JSON"),
        (
            200,
            json.dumps({"error": {"code": 502, "message": "upstream"}}),
            "answered an error (502)",
        ),
        (200, json.dumps({"object": "chat.completion", "choices": []}), "not a completion"),
        (200, message(finish_reason="content_filter"), "declined (content_filter)"),
        (200, message(None), "no text"),
        (200, message("   "), "no text"),
    ],
)
def test_anything_but_a_completion_is_a_model_error(status: int, body: str, expected: str) -> None:
    """AC19, C7: an error body is never recorded as a judgement."""
    with pytest.raises(ModelError, match=re.escape(expected)):
        models.parse_completion(status, body, model=MODEL)


def test_the_real_client_sends_the_documented_shape() -> None:
    """OpenRouter's chat completions request: the model, a system turn then one user turn, the
    key as a bearer header and never in the body."""
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["headers"] = dict(request.headers)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, text=message("English."))

    client = models.HttpxModelClient("sk-or-test", MODEL, transport=httpx.MockTransport(handler))
    done = client.complete(system="Be brief.", prompt="theorem t : True := trivial", max_tokens=99)
    assert done.text == "English." and client.model == MODEL
    assert seen["url"] == models.COMPLETIONS_URL
    headers = seen["headers"]
    assert isinstance(headers, dict)
    assert headers["authorization"] == "Bearer sk-or-test"
    body = seen["body"]
    assert isinstance(body, dict)
    assert body["model"] == MODEL and body["max_tokens"] == 99
    assert body["messages"] == [
        {"role": "system", "content": "Be brief."},
        {"role": "user", "content": "theorem t : True := trivial"},
    ]
    assert "sk-or-test" not in json.dumps(body)


def test_a_network_failure_is_a_model_error_without_the_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    client = models.HttpxModelClient("sk-secret", transport=httpx.MockTransport(handler))
    with pytest.raises(ModelError) as failure:
        client.complete(system="s", prompt="p")
    assert "ConnectError" in str(failure.value) and "sk-secret" not in str(failure.value)


def test_family_and_formalizer_lookups() -> None:
    """R7: the family is a model id's leading letters, after any provider prefix (OpenRouter
    names ``anthropic/claude-opus-5.5``, whose family is claude, not anthropic); provenance names
    an AI formalizer by substring, or names none and is `unknown`."""
    assert models.family_of("claude-opus-5") == "claude"
    assert models.family_of("anthropic/claude-opus-5.5") == "claude"
    assert models.family_of("google/gemini-3-pro") == "gemini"
    assert models.family_of("Gemini-3-pro") == "gemini"
    assert models.formalizer_family("Claude Opus 4.5 via the lean-genius pipeline") == "claude"
    assert models.formalizer_family("AlphaProof (Google DeepMind)") == "gemini"
    assert models.formalizer_family("Aristotle by Harmonic") == "aristotle"
    assert models.formalizer_family("T. Tao") == models.FORMALIZER_UNKNOWN
    assert models.formalizer_family(None) == models.FORMALIZER_UNKNOWN
    assert models.formalizer_family("") == models.FORMALIZER_UNKNOWN
