"""The ``Model`` seam (conventions §1; F12-R6, R7, Q5, Q14): the one module that talks to a
language-model provider.

Two of D-9 v3.12's layers ask a model a question — the definition-grounded review brief and the
back-translation — and both are *judgements*: they belong to the review brief attached to a
certificate, never to the trust base (F12-R2). So this seam does one thing, ``complete``, and
returns the text with the model and version that produced it, which the QA record carries on
every ``brief`` row (R6, R7: the model and version are recorded; R7's independence rule is
decided by family, ``family_of``).

The provider is OpenRouter's chat completions API (the owner's choice, 2026-10-05, replacing
Anthropic's Messages API), over the repository's already-locked ``httpx`` (F12-Q14): a second
HTTP stack for one endpoint is the supply-chain cost C5 exists to refuse. The request shape is
the documented one (openrouter.ai/docs/api-reference/chat-completion) — ``POST
/api/v1/chat/completions`` with the model, a system turn, one user turn and ``max_tokens``, the
key as a bearer token. A non-2xx status (402 is a spent credit balance, 429 a rate limit), an
error object in a 200 body, a ``content_filter`` finish, a network error or a malformed body is a
``ModelError`` the caller records as ``inconclusive`` (AC19, C7).

The key is a C8 secret read by ``opn_gate.config`` (``OPENROUTER_API_KEY``) and never logged.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

log = logging.getLogger(__name__)

COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"
#: Claude Opus 5.5 as OpenRouter lists it (GET /api/v1/models, 2026-10-05): the owner's choice.
DEFAULT_MODEL = "anthropic/claude-opus-5.5"
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


class ModelTruncatedError(ModelError):
    """The answer stopped at the output limit (``finish_reason: length``): text was returned,
    but not a whole answer, so it is never taken for one. It carries the tokens it spent, which
    were billed (found 2026-10-05: an explainer cut off mid-formula at 16000 tokens merged)."""

    def __init__(self, message: str, *, input_tokens: int = 0, output_tokens: int = 0) -> None:
        super().__init__(message)
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


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
    """``claude-opus-5`` -> ``claude``: the leading letters of a model id name its family, after
    any provider prefix — OpenRouter's ``anthropic/claude-opus-5.5`` is a claude, not an
    anthropic, or R7's independence rule would compare a provider with a family."""
    name = model.strip().lower().rsplit("/", 1)[-1]
    m = _FAMILY_RE.match(name)
    return m.group(0) if m else name


def formalizer_family(author: str | None) -> str:
    """R7: which AI family a provenance author names, or ``unknown`` when it names none — a
    human name, an upstream repository, an empty field. Recorded on the row either way."""
    text = (author or "").casefold()
    for family, markers in AI_FAMILIES.items():
        if any(marker in text for marker in markers):
            return family
    return FORMALIZER_UNKNOWN


class HttpxModelClient:
    """The real seam: OpenRouter's chat completions over the locked ``httpx``."""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        *,
        url: str = COMPLETIONS_URL,
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
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        headers = {
            "authorization": f"Bearer {self._api_key}",
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
    """The completion in a chat completions response, or why there is none — every refusal
    named, because a brief that quietly recorded an error body as its judgement would be the C7
    failure this seam exists to prevent."""
    if status < 200 or status >= 300:
        msg = f"the model provider answered {status}"
        raise ModelError(msg)
    try:
        doc: Any = httpx.Response(200, text=text).json()
    except ValueError as exc:
        msg = "the model provider's answer is not JSON"
        raise ModelError(msg) from exc
    if isinstance(doc, dict) and isinstance(doc.get("error"), dict):
        # OpenRouter can answer 200 and carry an upstream failure in the body.
        msg = f"the model provider answered an error ({doc['error'].get('code', 'no code')})"
        raise ModelError(msg)
    choices = doc.get("choices") if isinstance(doc, dict) else None
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        msg = "the model provider's answer is not a completion"
        raise ModelError(msg)
    choice = choices[0]
    raw_usage = doc.get("usage")
    usage: dict[str, Any] = raw_usage if isinstance(raw_usage, dict) else {}
    spent_in = int(usage.get("prompt_tokens") or 0)
    spent_out = int(usage.get("completion_tokens") or 0)
    if choice.get("finish_reason") == "length":
        msg = f"the answer was cut off at the output limit ({spent_out} tokens)"
        raise ModelTruncatedError(msg, input_tokens=spent_in, output_tokens=spent_out)
    if choice.get("finish_reason") == "content_filter":
        msg = "the model declined (content_filter)"
        raise ModelError(msg)
    message = choice.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    answer = content.strip() if isinstance(content, str) else ""
    if not answer:
        msg = "the model answered with no text"
        raise ModelError(msg)
    return Completion(
        text=answer,
        model=model,
        version=str(doc.get("model") or model),
        input_tokens=spent_in,
        output_tokens=spent_out,
    )
