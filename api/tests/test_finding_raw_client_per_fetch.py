"""Finding raw-client-per-fetch (2026-11-24, F14-T27 deployed): concurrency alone did not save
``POST /check``.

With ``frontier.prefetch`` live, the Lambda read all 443 ``graph.json`` files in a timed-out
request (13:32:03Z to 13:32:28Z) instead of 372, at about 17 a second across 16 threads, which is
slower per read than the 65 ms it had managed in series. The reads were CPU-bound, not waiting:
``HttpxGitHost.fetch_raw`` built a new ``httpx.Client`` for every file, so every read paid a fresh
SSL context (the CA bundle loaded again) and a TLS handshake, and a 512 MB Lambda has a fraction of
one vCPU to share among the threads. The raw host is one origin; one client, kept for the
process, makes every read after the first a request on an open connection.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx
import pytest

from opn_api import githost

REPO = "owner/graph"
REF = "a" * 40


class Counting:
    """Stands in for ``httpx.Client`` inside ``githost``: counts constructions and answers every
    request from a mock transport, so nothing reaches the network."""

    def __init__(self) -> None:
        self.made = 0
        self.lock = threading.Lock()
        real = httpx.Client

        def answer(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, headers={"ETag": '"e"'}, content=request.url.path.encode())

        def make(*args: Any, **kwargs: Any) -> httpx.Client:
            with self.lock:
                self.made += 1
            kwargs["transport"] = httpx.MockTransport(answer)
            return real(*args, **kwargs)

        self.make = make


@pytest.fixture
def counting(monkeypatch: pytest.MonkeyPatch) -> Counting:
    c = Counting()
    monkeypatch.setattr("httpx.Client", c.make)
    return c


def host() -> githost.HttpxGitHost:
    return githost.HttpxGitHost(client_id="id", client_secret="not-a-secret")  # noqa: S106


def test_raw_reads_share_one_client(counting: Counting) -> None:
    h = host()
    for i in range(20):
        got = h.fetch_raw(REPO, REF, f"targets/t{i}/graph.json", etag=None)
        assert got.status == 200
    assert counting.made == 1, f"{counting.made} clients for 20 raw reads"


def test_raw_reads_from_many_threads_share_one_client(counting: Counting) -> None:
    h = host()
    with ThreadPoolExecutor(max_workers=16) as pool:
        got = list(
            pool.map(
                lambda i: h.fetch_raw(REPO, REF, f"targets/t{i}/graph.json", etag=None),
                range(64),
            )
        )
    assert [g.status for g in got] == [200] * 64
    assert got[5].body == f"/{REPO}/{REF}/targets/t5/graph.json".encode()
    assert counting.made == 1, f"{counting.made} clients for 64 concurrent raw reads"


def test_a_304_and_a_failure_still_answer_as_before(monkeypatch: pytest.MonkeyPatch) -> None:
    real = httpx.Client

    def answer(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("gone.json"):
            raise httpx.ConnectError("down", request=request)
        if request.headers.get("If-None-Match") == '"e"':
            return httpx.Response(304)
        return httpx.Response(404)

    monkeypatch.setattr(
        "httpx.Client",
        lambda *a, **k: real(*a, **{**k, "transport": httpx.MockTransport(answer)}),
    )
    h = host()
    assert h.fetch_raw(REPO, REF, "a.json", etag='"e"').status == 304
    assert h.fetch_raw(REPO, REF, "b.json", etag=None).status == 404
    with pytest.raises(githost.GitHostError, match=r"gone\.json"):
        h.fetch_raw(REPO, REF, "gone.json", etag=None)
