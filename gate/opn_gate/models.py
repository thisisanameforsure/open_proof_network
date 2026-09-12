"""The ``Model`` seam (conventions §1; F12-R6, R7, Q5, Q14): the one module that talks to a
language-model provider.

Two of D-9 v3.12's layers ask a model a question — the definition-grounded review brief and the
back-translation — and both are *judgements*: they belong to the review brief attached to a
certificate, never to the trust base (F12-R2). So this seam does one thing, ``complete``, and
returns the text with the model and version that produced it, which the QA record carries on
every ``brief`` row (R6, R7: the model and version are recorded; R7's independence rule is
decided by family, ``family_of``).

The provider is the Anthropic Messages API over the repository's already-locked ``httpx``
(F12-Q14): the official SDK's current line is built on ``httpx2`` while ``mcp`` 1.x pins
``httpx`` 0.28, and a second HTTP stack for one endpoint is the supply-chain cost C5 exists to
refuse. The request shape is the documented one — ``POST /v1/messages`` with the model, a
system prompt, one user turn and ``max_tokens``; Claude Opus 5 runs adaptive thinking by
default, so the request names no thinking configuration. A ``refusal`` stop reason, a non-2xx
status, a network error or a malformed body is a ``ModelError`` the caller records as
``inconclusive`` (AC19, C7).

The key is a C8 secret read by ``opn_gate.config`` (``OPN_MODEL_API_KEY``) and never logged.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

log = logging.getLogger(__name__)

MESSAGES_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-opus-5"
DEFAULT_MAX_TOKENS = 16000
TIMEOUT_S = 600.0  # a brief over a long statement can take minutes; the SDK's own default

#: R7: an AI formalizer named in a target's provenance, by the substrings that name it, and the
#: family each belongs to. A back-translating model of the same family is refused (Q5): the
#: model that wrote the Lean must not be the one that reads it back.
AI_FAMILIES: dict[str, tuple[str, ...]] = {
    "claude": ("claude", "anthropic"),
    "gemini": ("gemini", "alphaproof", "deepmind"),
    "gpt": ("gpt", "openai", "codex", "o3", "o4"),
    "aristotle": ("aristotle", "harmonic"),
    "aletheia": ("aletheia",),
    "deepseek": ("deepseek",),
    "kimi": ("kimi", "kimina"),
}
FORMALIZER_UNKNOWN = "unknown"
_FAMILY_RE = re.compile(r"^[a-z]+")


class ModelError(RuntimeError):
    """The provider did not answer with a completion; the message carries no credential."""


@dataclass(frozen=True)
class Completion:
    text: str
    model: str  # what was asked for (the family's name rides on it)
    version: str  # what the provider reports it ran
    input_tokens: int = 0
    output_tokens: int = 0


class ModelClient(Protocol):
    """Everything the QA layers need from a model."""

    @property
    def model(self) -> str: ...

    def complete(
        self, *, system: str, prompt: str, max_tokens: int = DEFAULT_MAX_TOKENS
    ) -> Completion:
        """One question, one answer. Raises ``ModelError`` on anything but a completion."""


def family_of(model: str) -> str:
    """``claude-opus-5`` -> ``claude``: the leading letters of a model id name its family."""
    m = _FAMILY_RE.match(model.strip().lower())
    return m.group(0) if m else model.strip().lower()


def formalizer_family(author: str | None) -> str:
    """R7: which AI family a provenance author names, or ``unknown`` when it names none — a
    human name, an upstream repository, an empty field. Recorded on the row either way."""
    text = (author or "").casefold()
    for family, markers in AI_FAMILIES.items():
        if any(marker in text for marker in markers):
            return family
    return FORMALIZER_UNKNOWN


class HttpxModelClient:
    """The real seam: the Messages API over the locked ``httpx``."""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        *,
        url: str = MESSAGES_URL,
        timeout_s: float = TIMEOUT_S,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._url = url
        self._timeout_s = timeout_s
        self._transport = transport

    @property
    def model(self) -> str:
        return self._model

    def complete(
        self, *, system: str, prompt: str, max_tokens: int = DEFAULT_MAX_TOKENS
    ) -> Completion:
        body = {
            "model": self._model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
        }
        try:
            with httpx.Client(timeout=self._timeout_s, transport=self._transport) as http:
                response = http.post(self._url, json=body, headers=headers)
        except httpx.HTTPError as exc:
            msg = f"the model provider could not be reached: {exc.__class__.__name__}"
            raise ModelError(msg) from exc
        return parse_completion(response.status_code, response.text, model=self._model)


def parse_completion(status: int, text: str, *, model: str) -> Completion:
    """The completion in a Messages API response, or why there is none — every refusal named,
    because a brief that quietly recorded an error body as its judgement would be the C7
    failure this seam exists to prevent."""
    if status < 200 or status >= 300:
        msg = f"the model provider answered {status}"
        raise ModelError(msg)
    try:
        doc: Any = httpx.Response(200, text=text).json()
    except ValueError as exc:
        msg = "the model provider's answer is not JSON"
        raise ModelError(msg) from exc
    if not isinstance(doc, dict) or doc.get("type") != "message":
        msg = "the model provider's answer is not a message"
        raise ModelError(msg)
    if doc.get("stop_reason") == "refusal":
        details = doc.get("stop_details") or {}
        category = details.get("category") if isinstance(details, dict) else None
        msg = f"the model declined ({category or 'no category'})"
        raise ModelError(msg)
    parts = [
        str(block.get("text", ""))
        for block in doc.get("content") or []
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    answer = "".join(parts).strip()
    if not answer:
        msg = "the model answered with no text"
        raise ModelError(msg)
    raw_usage = doc.get("usage")
    usage: dict[str, Any] = raw_usage if isinstance(raw_usage, dict) else {}
    return Completion(
        text=answer,
        model=model,
        version=str(doc.get("model") or model),
        input_tokens=int(usage.get("input_tokens") or 0),
        output_tokens=int(usage.get("output_tokens") or 0),
    )
