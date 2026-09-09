"""The ``GitHost`` seam (conventions §1): every call to GitHub goes through here.

F05 needs two calls: exchanging an OAuth code for the user's login and account age (R3), and
reading a committed file at the graph's ``main`` with ETag caching (R7, R9). The OAuth access
token GitHub returns lives inside ``exchange_code`` for one request and is dropped on return —
it is never stored, never returned, never logged (D-23; AC5).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

log = logging.getLogger(__name__)

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"  # noqa: S105 — a URL
GITHUB_USER_URL = "https://api.github.com/user"
RAW_URL = "https://raw.githubusercontent.com/{repo}/{ref}/{path}"
TIMEOUT_S = 10.0


class GitHostError(Exception):
    """The host refused or failed; the message is safe to log (no credential in it)."""


@dataclass(frozen=True)
class GitHubUser:
    login: str
    id: int
    created_at: str


@dataclass(frozen=True)
class Fetched:
    status: int  # 200, 304 or the host's error status
    etag: str | None
    body: bytes | None


class GitHost(Protocol):
    def exchange_code(self, code: str, *, redirect_uri: str) -> GitHubUser:
        """Trade the OAuth ``code`` for the user's login and creation date; the access token
        is discarded before this returns (R3)."""
        ...

    def fetch_raw(self, repo: str, ref: str, path: str, *, etag: str | None) -> Fetched:
        """Read a committed file, honoring ``If-None-Match`` (R9)."""
        ...


class HttpxGitHost:
    def __init__(self, *, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret

    def exchange_code(self, code: str, *, redirect_uri: str) -> GitHubUser:
        with httpx.Client(timeout=TIMEOUT_S, headers={"Accept": "application/json"}) as http:
            try:
                exchange = http.post(
                    GITHUB_TOKEN_URL,
                    data={
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "code": code,
                        "redirect_uri": redirect_uri,
                    },
                )
            except httpx.HTTPError as exc:
                msg = f"GitHub token exchange failed: {type(exc).__name__}"
                raise GitHostError(msg) from exc
            payload: dict[str, Any] = exchange.json() if exchange.content else {}
            access_token = payload.get("access_token")
            if exchange.status_code != 200 or not access_token:
                msg = f"GitHub refused the code: {payload.get('error', exchange.status_code)}"
                raise GitHostError(msg)
            try:
                user = http.get(
                    GITHUB_USER_URL, headers={"Authorization": f"Bearer {access_token}"}
                )
            except httpx.HTTPError as exc:
                msg = f"GitHub user lookup failed: {type(exc).__name__}"
                raise GitHostError(msg) from exc
            finally:
                del access_token  # one request, then gone (D-23)
        if user.status_code != 200:
            msg = f"GitHub user lookup returned {user.status_code}"
            raise GitHostError(msg)
        doc = user.json()
        try:
            return GitHubUser(
                login=str(doc["login"]), id=int(doc["id"]), created_at=str(doc["created_at"])
            )
        except (KeyError, TypeError, ValueError) as exc:
            msg = "GitHub user document is missing login, id or created_at"
            raise GitHostError(msg) from exc

    def fetch_raw(self, repo: str, ref: str, path: str, *, etag: str | None) -> Fetched:
        url = RAW_URL.format(repo=repo, ref=ref, path=path)
        headers = {"If-None-Match": etag} if etag else {}
        try:
            with httpx.Client(timeout=TIMEOUT_S) as http:
                resp = http.get(url, headers=headers)
        except httpx.HTTPError as exc:
            msg = f"fetching {path} from {repo}@{ref} failed: {type(exc).__name__}"
            raise GitHostError(msg) from exc
        if resp.status_code == 304:
            return Fetched(304, etag, None)
        if resp.status_code != 200:
            return Fetched(resp.status_code, None, None)
        return Fetched(200, resp.headers.get("ETag"), resp.content)


def authorize_url(*, client_id: str, redirect_uri: str, state: str) -> str:
    """Where ``GET /auth/github/start`` sends the browser (R3)."""
    params = httpx.QueryParams(
        {"client_id": client_id, "redirect_uri": redirect_uri, "state": state}
    )
    return f"{GITHUB_AUTHORIZE_URL}?{params}"


def build(settings: Any) -> GitHost:
    return HttpxGitHost(
        client_id=settings.github_client_id or "", client_secret=settings.github_client_secret or ""
    )
