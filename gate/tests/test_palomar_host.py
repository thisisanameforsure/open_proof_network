"""F25-T6 / AC12: the Palomar client seam — the fake and the real host share one protocol, a
Retry-After is honoured, refusals are typed, and nothing registers without a person's word."""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from typing import Any

import pytest

from opn_gate import palomar_host as ph


def test_the_fake_satisfies_the_protocol() -> None:
    host: ph.PalomarHost = ph.FakePalomarHost()
    real: ph.PalomarHost = ph.HttpPalomarHost()
    for name in (
        "recent", "versions", "entry", "repository", "identity",
        "submit", "verify", "submission", "review", "register", "withdraw",
    ):  # fmt: skip
        assert callable(getattr(host, name)) and callable(getattr(real, name))


def test_data_reads_on_the_fake() -> None:
    entry = {"id": "PALOMAR-2026-10-09-000016", "version": 1, "status": "registered", "title": "t"}
    host = ph.FakePalomarHost(entries={("PALOMAR-2026-10-09-000016", 1): entry}, feed=[entry])
    assert host.recent() == {"entries": [entry]}
    assert host.entry("PALOMAR-2026-10-09-000016", 1) == entry
    assert host.entry("PALOMAR-2026-10-09-000016", 2) is None
    versions = host.versions("PALOMAR-2026-10-09-000016")
    assert (
        versions is not None
        and versions["entries"][0]["path"] == "entries/PALOMAR-2026-10-09-000016-v1.json"
    )
    assert host.versions("PALOMAR-2026-10-09-000017") is None
    with pytest.raises(ph.PalomarError):
        host.entry("not-an-id", 1)


def test_the_identity_digest_is_palomars() -> None:
    """lowercase repository, NUL, project path or empty, NUL, comparator path."""
    import hashlib  # noqa: PLC0415

    want = hashlib.sha256(b"plasma-ai/erdos-809\x00\x00comparator.json").hexdigest()
    assert ph.identity_digest("Plasma-AI/erdos-809", None, "comparator.json") == want
    assert ph.identity_digest("o/r", "lean", "lean/comparator/config.json") != want


def test_register_refuses_without_a_person() -> None:
    host = ph.FakePalomarHost()
    with pytest.raises(ph.HumanConfirmationRequiredError):
        host.register("token", "a" * 64, human_confirmed=False)
    assert host.calls == [], "the refusal happens before the host is reached"
    real = ph.HttpPalomarHost(intake_host="https://127.0.0.1:1")
    with pytest.raises(ph.HumanConfirmationRequiredError):
        real.register("token", "a" * 64, human_confirmed=False)


def test_the_intake_flow_on_the_fake() -> None:
    host = ph.FakePalomarHost()
    out = host.submit(
        {
            "repository": "o/r",
            "commit": "a" * 40,
            "comparator_config_path": "comparator.json",
            "authorization_relationship": "maintainer",
        }
    )
    assert set(out) == {"pending_secret", "challenge", "instructions"}
    token = host.verify(out["pending_secret"], "gist-1")["access_token"]
    assert host.submission(token)["status"] == "verifying"
    assert host.review(token) is None
    host.reviews[token] = {"sha256": "b" * 64, "outcome": "neutral"}
    with pytest.raises(ph.PalomarRefusedError) as refused:
        host.register(token, "c" * 64, human_confirmed=True)
    assert refused.value.status == 409
    assert host.register(token, "b" * 64, human_confirmed=True) == {"status": "registered"}
    with pytest.raises(ph.PalomarRefusedError):
        host.verify(out["pending_secret"], "gist-1")  # spent


def test_busy_is_surfaced_with_the_wait() -> None:
    host = ph.FakePalomarHost(busy=45)
    with pytest.raises(ph.PalomarBusyError) as busy:
        host.recent()
    assert busy.value.retry_after_s == 45 and busy.value.status == 429
    assert host.recent() == {"entries": []}  # once


# --- the real host over a stubbed urlopen ----------------------------------------------------


class _Resp(io.BytesIO):
    def __enter__(self) -> _Resp:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


def _http_error(
    url: str, code: int, body: dict[str, Any], headers: dict[str, str] | None = None
) -> urllib.error.HTTPError:
    from email.message import Message  # noqa: PLC0415

    msg = Message()
    for k, v in (headers or {}).items():
        msg[k] = v
    return urllib.error.HTTPError(url, code, "x", msg, io.BytesIO(json.dumps(body).encode()))


def test_http_host_decodes_404_busy_and_refusals(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[str, str, str | None]] = []

    def fake_urlopen(request: Any, timeout: float) -> Any:
        url = request.full_url
        seen.append((request.get_method(), url, request.get_header("Authorization")))
        if url.endswith("/entries/PALOMAR-2026-10-09-000016-v1.json"):
            return _Resp(json.dumps({"id": "PALOMAR-2026-10-09-000016", "version": 1}).encode())
        if url.endswith("/entries/PALOMAR-2026-10-09-000016-v2.json"):
            raise _http_error(url, 404, {"error": "not found"})
        if url.endswith("/api/submit"):
            raise _http_error(url, 429, {"error": "spacing"}, {"Retry-After": "90"})
        if url.endswith("/api/verify"):
            raise _http_error(url, 403, {"error": "tag not found", "attempts_remaining": 9})
        if url.endswith("/api/review"):
            raise _http_error(url, 404, {"error": "not yet"})
        raise AssertionError(url)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    host = ph.HttpPalomarHost()
    assert host.entry("PALOMAR-2026-10-09-000016", 1) == {
        "id": "PALOMAR-2026-10-09-000016",
        "version": 1,
    }
    assert host.entry("PALOMAR-2026-10-09-000016", 2) is None
    with pytest.raises(ph.PalomarBusyError) as busy:
        host.submit({"repository": "o/r"})
    assert busy.value.retry_after_s == 90 and busy.value.status == 429
    with pytest.raises(ph.PalomarRefusedError) as refused:
        host.verify("s", "g")
    assert refused.value.status == 403 and refused.value.body["attempts_remaining"] == 9
    assert host.review("tok") is None
    assert seen[-1] == ("GET", "https://submit.palomar-registry.org/api/review", "Bearer tok")
    assert all(m == "GET" for m, u, _ in seen if "data.palomar-registry.org" in u)


def test_http_host_network_failure_is_a_palomar_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def down(request: Any, timeout: float) -> Any:
        raise urllib.error.URLError("no route")

    monkeypatch.setattr(urllib.request, "urlopen", down)
    with pytest.raises(ph.PalomarError):
        ph.HttpPalomarHost().recent()
    with pytest.raises(ph.PalomarError):
        ph.HttpPalomarHost().identity("not-a-digest")
