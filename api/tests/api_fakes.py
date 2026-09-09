"""Fakes for the api's seams (conventions §1, §2): ``FakeGitHost`` and ``FakeClock``.

The store's fake is ``opn_api.store.MemoryStore`` itself — the local runner uses it too. The
fake host returns the structured records the seam defines; it never imitates GitHub's wire
format. It holds a fake access token only so a test can assert the string never reaches a
store or a log (AC5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from starlette.testclient import TestClient

from opn_api import config, identity
from opn_api.app import create_app
from opn_api.githost import Fetched, GitHostError, GitHubUser
from opn_api.store import MemoryStore

FIXTURES = Path(__file__).resolve().parent / "fixtures"
FAKE_ACCESS_TOKEN = "gho_FAKE_ACCESS_TOKEN_NEVER_STORED"  # noqa: S105 — a sentinel, not a secret


@dataclass
class FakeClock:
    current: datetime = field(default_factory=lambda: datetime(2026, 9, 9, 12, 0, 0, tzinfo=UTC))

    def now(self) -> datetime:
        return self.current

    def advance(self, **kwargs: int) -> None:
        self.current += timedelta(**kwargs)


@dataclass
class FakeGitHost:
    users: dict[str, GitHubUser] = field(default_factory=dict)
    files: dict[str, bytes] = field(default_factory=dict)
    exchanges: list[str] = field(default_factory=list)
    fetches: list[tuple[str, str | None]] = field(default_factory=list)
    unreachable: bool = False
    access_token: str = FAKE_ACCESS_TOKEN

    @classmethod
    def with_fixtures(cls, **users: GitHubUser) -> FakeGitHost:
        return cls(
            users=dict(users),
            files={
                "frontier.json": (FIXTURES / "frontier.json").read_bytes(),
                "info.json": (FIXTURES / "info.json").read_bytes(),
            },
        )

    def exchange_code(self, code: str, *, redirect_uri: str) -> GitHubUser:
        self.exchanges.append(code)
        user = self.users.get(code)
        if user is None:
            msg = "GitHub refused the code: bad_verification_code"
            raise GitHostError(msg)
        return user

    def fetch_raw(self, repo: str, ref: str, path: str, *, etag: str | None) -> Fetched:
        self.fetches.append((path, etag))
        if self.unreachable:
            msg = f"fetching {path} failed: ConnectError"
            raise GitHostError(msg)
        body = self.files.get(path)
        if body is None:
            return Fetched(404, None, None)
        current = f'"{len(body)}-{hash(body) & 0xFFFF:x}"'
        if etag == current:
            return Fetched(304, etag, None)
        return Fetched(200, current, body)


def alice() -> GitHubUser:
    return GitHubUser(login="alice", id=1001, created_at="2015-03-01T00:00:00Z")


def bob() -> GitHubUser:
    return GitHubUser(login="bob", id=1002, created_at="2018-06-01T00:00:00Z")


TEST_ENV: dict[str, str] = {
    "OPN_API_GITHUB_APP_ID": "1",
    "OPN_API_GITHUB_CLIENT_ID": "Iv1.test",
    "OPN_API_GITHUB_CLIENT_SECRET": "client-secret-for-tests",
    "OPN_API_GITHUB_PRIVATE_KEY": "-----BEGIN TEST KEY-----",
    "OPN_API_TOKEN_SECRET": "token-secret-for-tests",
}


@dataclass
class Harness:
    settings: config.Settings
    store: MemoryStore
    githost: FakeGitHost
    clock: FakeClock
    client: TestClient
    app: Any

    def token_for(self, code: str, pseudonym: str) -> str:
        """Drive the three-step GitHub flow and return the raw token."""
        start = self.client.get("/auth/github/start", follow_redirects=False)
        assert start.status_code == 302, start.text
        state = start.headers["location"].split("state=")[1].split("&")[0]
        cb = self.client.get(
            "/auth/github/callback",
            params={"code": code, "state": state},
            headers={"Accept": "application/json"},
        )
        assert cb.status_code == 200, cb.text
        issued = self.client.post(
            "/tokens",
            json={
                "proof": cb.json()["proof"],
                "pseudonym": pseudonym,
                "dco": {"version": identity.DCO_VERSION, "accepted": True},
            },
        )
        assert issued.status_code == 201, issued.text
        return str(issued.json()["token"])

    @property
    def context(self) -> Any:
        """The app's ``Context`` — the seams and the committed-file cache (R9)."""
        return self.app.state.context

    def auth(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}


def make_harness(env: dict[str, str] | None = None, **seams: Any) -> Harness:
    settings = config.load({**TEST_ENV, **(env or {})})
    store = seams.get("store") or MemoryStore()
    githost = seams.get("githost") or FakeGitHost.with_fixtures(code_alice=alice(), code_bob=bob())
    clock = seams.get("clock") or FakeClock()
    app = create_app(settings, store=store, githost=githost, clock=clock)
    client = TestClient(app, raise_server_exceptions=False)
    return Harness(settings, store, githost, clock, client, app)
