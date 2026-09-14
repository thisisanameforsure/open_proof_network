"""The ``Axle`` seam (F13-T2; D-4 v3.14): every call to the hosted fast checker goes through here.

AXLE (Axiom Math's public Lean engine) elaborates Lean in its own sandbox against one Mathlib per
environment; the network elaborates none of it (C9 v2). Three calls, all verified against the
live service on 2026-09-14 (``engineering/evidence/F13/task-1.txt``):

- ``POST /api/v1/check`` with {content, environment, timeout_seconds}: compile and report.
- ``POST /api/v1/verify_proof`` with {formal_statement, content, environment, timeout_seconds}:
  compile, then compare against a sorry-bodied statement (name, type, axioms).
- ``GET /v1/environments``: the environments the service hosts.

The answer's body is returned verbatim and never interpreted beyond the request id: it is a third
party's untrusted output (F13 §7). Like ``GitHost``, a refusal or transport failure becomes an
``AxleError`` whose message names the call and the status, never a key, and every ``.json()`` is
guarded, so an edge proxy's HTML 502 can never escape as a ``JSONDecodeError`` (C7).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

CHECK_PATH = "/api/v1/check"
VERIFY_PATH = "/api/v1/verify_proof"
ENVIRONMENTS_PATH = "/v1/environments"
CONNECT_TIMEOUT_S = 10.0


class AxleError(Exception):
    """The checker refused or failed. ``status`` is its HTTP status, or ``None`` when no response
    arrived; the message is safe to log."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class AxleAnswer:
    """One answered call: the body verbatim, its request id, and how long the round trip took."""

    body: dict[str, Any]
    request_id: str | None
    latency_ms: int


class Axle(Protocol):
    def check(self, content: str, *, environment: str, timeout_s: float) -> AxleAnswer:
        """Compile ``content`` in ``environment`` and report its messages."""

    def verify_proof(
        self, content: str, *, formal_statement: str, environment: str, timeout_s: float
    ) -> AxleAnswer:
        """Compile ``content`` and compare it against ``formal_statement``."""

    def environments(self) -> list[str]:
        """The names of the environments the service hosts."""


class HttpxAxle:
    def __init__(self, *, base_url: str, api_key: str | None = None) -> None:
        self._base = base_url.rstrip("/")
        self._api_key = api_key  # none at Stage 0 (F13-Q5); never logged, never in a message

    def check(self, content: str, *, environment: str, timeout_s: float) -> AxleAnswer:
        body = {"content": content, "environment": environment, "timeout_seconds": timeout_s}
        return self._post(CHECK_PATH, body, "check", timeout_s)

    def verify_proof(
        self, content: str, *, formal_statement: str, environment: str, timeout_s: float
    ) -> AxleAnswer:
        body = {
            "formal_statement": formal_statement,
            "content": content,
            "environment": environment,
            "timeout_seconds": timeout_s,
        }
        return self._post(VERIFY_PATH, body, "verify_proof", timeout_s)

    def environments(self) -> list[str]:
        with self._client(CONNECT_TIMEOUT_S) as http:
            try:
                resp = http.get(self._base + ENVIRONMENTS_PATH)
            except httpx.HTTPError as exc:
                msg = f"AXLE environments failed: {type(exc).__name__}"
                raise AxleError(msg) from exc
        if resp.status_code != 200:
            msg = f"AXLE environments returned {resp.status_code}"
            raise AxleError(msg, status=resp.status_code)
        try:
            doc = resp.json()
        except ValueError as exc:
            msg = "AXLE returned a non-JSON body for environments"
            raise AxleError(msg, status=resp.status_code) from exc
        if not isinstance(doc, list):
            msg = f"AXLE returned {type(doc).__name__}, not an array, for environments"
            raise AxleError(msg, status=resp.status_code)
        return [str(e["name"]) for e in doc if isinstance(e, dict) and "name" in e]

    def _client(self, timeout_s: float) -> httpx.Client:
        headers = {"Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        # The read timeout is the checker's own budget plus the connect allowance, so a slow
        # elaboration is reported by AXLE rather than cut off by us mid-answer.
        return httpx.Client(
            timeout=httpx.Timeout(timeout_s + CONNECT_TIMEOUT_S, connect=CONNECT_TIMEOUT_S),
            headers=headers,
        )

    def _post(self, path: str, body: dict[str, Any], call: str, timeout_s: float) -> AxleAnswer:
        started = time.monotonic()
        with self._client(timeout_s) as http:
            try:
                resp = http.post(self._base + path, json=body)
            except httpx.HTTPError as exc:
                msg = f"AXLE {call} failed: {type(exc).__name__}"
                raise AxleError(msg) from exc
        latency_ms = int((time.monotonic() - started) * 1000)
        if resp.status_code != 200:
            msg = f"AXLE {call} returned {resp.status_code}"
            raise AxleError(msg, status=resp.status_code)
        try:
            doc = resp.json()
        except ValueError as exc:
            msg = f"AXLE returned a non-JSON body for {call}"
            raise AxleError(msg, status=resp.status_code) from exc
        if not isinstance(doc, dict):
            msg = f"AXLE returned {type(doc).__name__}, not an object, for {call}"
            raise AxleError(msg, status=resp.status_code)
        info = doc.get("info")
        request_id = info.get("request_id") if isinstance(info, dict) else None
        return AxleAnswer(
            body=doc,
            request_id=str(request_id) if request_id is not None else None,
            latency_ms=latency_ms,
        )


def build(settings: Any) -> Axle:
    return HttpxAxle(base_url=settings.axle_url)
