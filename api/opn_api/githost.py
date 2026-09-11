"""The ``GitHost`` seam (conventions §1): every call to GitHub goes through here.

F05 needs two calls: exchanging an OAuth code for the user's login and account age (R3), and
reading a committed file at the graph's ``main`` with ETag caching (R7, R9). The OAuth access
token GitHub returns lives inside ``exchange_code`` for one request and is dropped on return —
it is never stored, never returned, never logged (D-23; AC5).

F06 adds the four calls a precheck job needs (F06-R3, R5), all as the GitHub App: push the job
branch, dispatch the scratch repository's workflow, find the run that branch produced, and
download its result artifact. Authenticating as the App means an RS256 JWT traded for an
installation access token, which is cached in memory until shortly before it expires and, like
the OAuth token, is never stored, returned or logged (C8).
"""

from __future__ import annotations

import base64
import json
import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

log = logging.getLogger(__name__)

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"  # noqa: S105 — a URL
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_API = "https://api.github.com"
RAW_URL = "https://raw.githubusercontent.com/{repo}/{ref}/{path}"
API_ACCEPT = "application/vnd.github+json"
API_VERSION = "2022-11-28"
TIMEOUT_S = 10.0
ARTIFACT_TIMEOUT_S = 30.0  # a result artifact is a zip from blob storage, not an API call
JWT_LIFETIME_S = 540  # GitHub caps an App JWT at ten minutes; stay inside it
JWT_BACKDATE_S = 60  # tolerate clock skew on GitHub's side
TOKEN_REFRESH_MARGIN_S = 300  # renew an installation token five minutes before it expires
BLOB_MODE = "100644"


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


@dataclass(frozen=True)
class Author:
    """One side of a commit's attribution: the author who wrote it, or the committer who
    carried it (F07-R2). Both are sent explicitly — GitHub copies the author into the committer
    when only one is given, which would make the contributor both."""

    name: str
    email: str
    date: str  # ISO 8601 with a Z suffix, as the api renders timestamps

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "email": self.email, "date": self.date}


@dataclass(frozen=True)
class PullRequest:
    number: int
    url: str


@dataclass(frozen=True)
class WorkflowRun:
    """One Actions run, as much of it as the polling state machine needs (F06-R5)."""

    id: int
    status: str  # queued | in_progress | completed (GitHub's vocabulary, not ours)
    conclusion: str | None  # success | failure | cancelled | … , only once completed
    url: str

    @property
    def completed(self) -> bool:
        return self.status == "completed"

    @property
    def succeeded(self) -> bool:
        return self.completed and self.conclusion == "success"


class GitHost(Protocol):
    def exchange_code(self, code: str, *, redirect_uri: str) -> GitHubUser:
        """Trade the OAuth ``code`` for the user's login and creation date; the access token
        is discarded before this returns (R3)."""
        ...

    def fetch_raw(self, repo: str, ref: str, path: str, *, etag: str | None) -> Fetched:
        """Read a committed file, honoring ``If-None-Match`` (R9)."""
        ...

    def push_branch(  # noqa: PLR0913 — one argument per part of the commit being made
        self,
        repo: str,
        branch: str,
        files: Mapping[str, str],
        *,
        base: str,
        message: str,
        author: Author | None = None,
        committer: Author | None = None,
    ) -> str:
        """Create ``branch`` from ``base`` with ``files`` added, returning the commit sha.

        The tree is the base branch's tree plus these paths, so the branch carries the scratch
        repository's own workflow as ``base`` has it — the api never pushes runnable code
        (F06-R3, §7). ``author`` is who wrote it and ``committer`` is who carried it; both must
        be given, because GitHub copies the author into the committer otherwise (F07-R2).
        """
        ...

    def open_pull_request(
        self, repo: str, *, head: str, base: str, title: str, body: str
    ) -> PullRequest:
        """Open a pull request from ``head`` into ``base`` (F07-R2). The App never merges it."""
        ...

    def dispatch_workflow(
        self, repo: str, workflow: str, *, ref: str, inputs: Mapping[str, str]
    ) -> None:
        """``workflow_dispatch`` the named workflow file at ``ref`` (F06-R3)."""
        ...

    def find_run(self, repo: str, workflow: str, *, branch: str) -> WorkflowRun | None:
        """The most recent run of ``workflow`` on ``branch``; ``None`` while there is none."""
        ...

    def download_artifact(self, repo: str, run_id: int, name: str) -> bytes | None:
        """The named artifact's zip, or ``None`` when the run produced no such artifact."""
        ...


class HttpxGitHost:
    def __init__(
        self, *, client_id: str, client_secret: str, app_id: str = "", private_key: str = ""
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._app_id = app_id
        self._private_key = private_key
        # repo -> (installation access token, unix expiry). Memory only: never stored (C8).
        self._installation_tokens: dict[str, tuple[str, float]] = {}

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
            # Status first, then the body, and the body only through a guard: an edge proxy's
            # HTML 502 must become a GitHostError naming the call, never a JSONDecodeError
            # escaping to the boundary as a 500 (C7; F05-Q7).
            if exchange.status_code != 200:
                msg = f"GitHub refused the code: {_error_field(exchange, exchange.status_code)}"
                raise GitHostError(msg)
            payload = _json(exchange, "the token exchange") if exchange.content else {}
            access_token = payload.get("access_token")
            if not access_token:
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
        doc = _json(user, "the user lookup")
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

    # --- as the GitHub App (F06-R3, R5) ---------------------------------------------------------

    def _app_jwt(self) -> str:
        """An RS256 JWT signed with the App's private key (C8 item 3; F06-Q5)."""
        if not self._app_id or not self._private_key:
            msg = "the GitHub App id and private key are not configured"
            raise GitHostError(msg)
        try:
            key = serialization.load_pem_private_key(
                self._private_key.encode("utf-8"), password=None
            )
        except (ValueError, TypeError) as exc:
            # The message is the exception's type alone: a key-parsing error must not echo key
            # material into a log (C8).
            msg = f"the GitHub App private key cannot be read: {type(exc).__name__}"
            raise GitHostError(msg) from exc
        if not isinstance(key, rsa.RSAPrivateKey):
            msg = "the GitHub App private key is not an RSA key"
            raise GitHostError(msg)
        now = int(time.time())
        header = {"alg": "RS256", "typ": "JWT"}
        claims = {
            "iat": now - JWT_BACKDATE_S,
            "exp": now + JWT_LIFETIME_S,
            "iss": self._app_id,
        }
        signing_input = b".".join(
            _b64url(json.dumps(part, separators=(",", ":")).encode()) for part in (header, claims)
        )
        signature = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        return (signing_input + b"." + _b64url(signature)).decode("ascii")

    def _installation_token(self, repo: str) -> str:
        """The App's installation access token for ``repo``, cached until it nearly expires."""
        cached = self._installation_tokens.get(repo)
        if cached is not None and cached[1] - TOKEN_REFRESH_MARGIN_S > time.time():
            return cached[0]
        jwt = self._app_jwt()
        headers = {
            "Authorization": f"Bearer {jwt}",
            "Accept": API_ACCEPT,
            "X-GitHub-Api-Version": API_VERSION,
        }
        with httpx.Client(timeout=TIMEOUT_S, headers=headers) as http:
            installation = _json(_send(http, "GET", f"{GITHUB_API}/repos/{repo}/installation"))
            installation_id = installation.get("id")
            if not installation_id:
                msg = f"the GitHub App is not installed on {repo}"
                raise GitHostError(msg)
            issued = _json(
                _send(
                    http, "POST", f"{GITHUB_API}/app/installations/{installation_id}/access_tokens"
                )
            )
        token = str(issued.get("token") or "")
        if not token:
            msg = f"GitHub issued no installation token for {repo}"
            raise GitHostError(msg)
        # An installation token lives an hour; trust the margin rather than parsing expires_at.
        self._installation_tokens[repo] = (token, time.time() + 3600)
        return token

    def _api(self, repo: str) -> httpx.Client:
        """A client carrying the installation token for ``repo``. The token is in memory and in
        this header only — never in a store, a response or a log (C8)."""
        return httpx.Client(
            timeout=TIMEOUT_S,
            headers={
                "Authorization": f"Bearer {self._installation_token(repo)}",
                "Accept": API_ACCEPT,
                "X-GitHub-Api-Version": API_VERSION,
            },
        )

    def push_branch(  # noqa: PLR0913 — one argument per part of the commit being made
        self,
        repo: str,
        branch: str,
        files: Mapping[str, str],
        *,
        base: str,
        message: str,
        author: Author | None = None,
        committer: Author | None = None,
    ) -> str:
        with self._api(repo) as http:
            ref = _json(_send(http, "GET", f"{GITHUB_API}/repos/{repo}/git/ref/heads/{base}"))
            base_sha = str(ref.get("object", {}).get("sha") or "")
            if not base_sha:
                msg = f"{repo} has no {base} branch to base a job on"
                raise GitHostError(msg)
            base_commit = _json(
                _send(http, "GET", f"{GITHUB_API}/repos/{repo}/git/commits/{base_sha}")
            )
            tree = _json(
                _send(
                    http,
                    "POST",
                    f"{GITHUB_API}/repos/{repo}/git/trees",
                    json={
                        "base_tree": base_commit["tree"]["sha"],
                        "tree": [
                            {"path": path, "mode": BLOB_MODE, "type": "blob", "content": content}
                            for path, content in sorted(files.items())
                        ],
                    },
                )
            )
            payload: dict[str, Any] = {
                "message": message,
                "tree": tree["sha"],
                "parents": [base_sha],
            }
            if author is not None:
                payload["author"] = author.as_dict()
            if committer is not None:
                # Named, not omitted: the Git Data API copies the author into the committer when
                # none is given, so leaving it out made the contributor the committer too — the
                # opposite of R2. Checked against the live host, not assumed (F07-T6).
                payload["committer"] = committer.as_dict()
            commit = _json(
                _send(http, "POST", f"{GITHUB_API}/repos/{repo}/git/commits", json=payload)
            )
            _send(
                http,
                "POST",
                f"{GITHUB_API}/repos/{repo}/git/refs",
                json={"ref": f"refs/heads/{branch}", "sha": commit["sha"]},
            )
        return str(commit["sha"])

    def open_pull_request(
        self, repo: str, *, head: str, base: str, title: str, body: str
    ) -> PullRequest:
        with self._api(repo) as http:
            doc = _json(
                _send(
                    http,
                    "POST",
                    f"{GITHUB_API}/repos/{repo}/pulls",
                    json={"head": head, "base": base, "title": title, "body": body},
                )
            )
        return PullRequest(number=int(doc["number"]), url=str(doc.get("html_url") or ""))

    def dispatch_workflow(
        self, repo: str, workflow: str, *, ref: str, inputs: Mapping[str, str]
    ) -> None:
        with self._api(repo) as http:
            _send(
                http,
                "POST",
                f"{GITHUB_API}/repos/{repo}/actions/workflows/{workflow}/dispatches",
                json={"ref": ref, "inputs": dict(inputs)},
            )

    def find_run(self, repo: str, workflow: str, *, branch: str) -> WorkflowRun | None:
        with self._api(repo) as http:
            page = _json(
                _send(
                    http,
                    "GET",
                    f"{GITHUB_API}/repos/{repo}/actions/workflows/{workflow}/runs",
                    params={"branch": branch, "per_page": 1},
                )
            )
        runs = page.get("workflow_runs") or []
        if not runs:
            return None
        run = runs[0]
        return WorkflowRun(
            id=int(run["id"]),
            status=str(run.get("status") or ""),
            conclusion=str(run["conclusion"]) if run.get("conclusion") else None,
            url=str(run.get("html_url") or ""),
        )

    def download_artifact(self, repo: str, run_id: int, name: str) -> bytes | None:
        with self._api(repo) as http:
            listing = _json(
                _send(http, "GET", f"{GITHUB_API}/repos/{repo}/actions/runs/{run_id}/artifacts")
            )
            found = next(
                (a for a in listing.get("artifacts") or [] if str(a.get("name")) == name), None
            )
            if found is None:
                return None
            http.timeout = httpx.Timeout(ARTIFACT_TIMEOUT_S)
            # This redirects to blob storage with a signed URL. Following it is safe because
            # httpx strips Authorization on a cross-origin redirect, so the installation token
            # is not handed to a storage host that has no business seeing it (C8).
            zipped = _send(
                http,
                "GET",
                f"{GITHUB_API}/repos/{repo}/actions/artifacts/{found['id']}/zip",
                follow_redirects=True,
            )
        return zipped.content


def _b64url(raw: bytes) -> bytes:
    return base64.urlsafe_b64encode(raw).rstrip(b"=")


def _send(http: httpx.Client, method: str, url: str, **kwargs: Any) -> httpx.Response:
    """One GitHub API call. Every failure becomes a ``GitHostError`` naming the call, never the
    credential that made it (C8)."""
    try:
        resp = http.request(method, url, **kwargs)
    except httpx.HTTPError as exc:
        msg = f"{method} {_path(url)} failed: {type(exc).__name__}"
        raise GitHostError(msg) from exc
    if resp.status_code >= 400:
        detail = _error_field(resp, "", field="message")
        msg = f"{method} {_path(url)} returned {resp.status_code}{': ' + detail if detail else ''}"
        raise GitHostError(msg)
    return resp


def _json(resp: httpx.Response, call: str | None = None) -> dict[str, Any]:
    """The response body as an object, or a ``GitHostError`` naming the call (never the
    credential that made it). Every ``.json()`` in this module goes through here or through
    ``_error_field``: a body is untrusted input (conventions §4) and parsing it is guarded."""
    what = call or _path(str(resp.url))
    try:
        doc = resp.json()
    except ValueError as exc:
        msg = f"GitHub returned a non-JSON body for {what}"
        raise GitHostError(msg) from exc
    if not isinstance(doc, dict):
        msg = f"GitHub returned {type(doc).__name__}, not an object, for {what}"
        raise GitHostError(msg)
    return doc


def _error_field(resp: httpx.Response, default: Any, *, field: str = "error") -> str:
    """The named field of an error body, for a message; ``default`` when the body is empty,
    not JSON, not an object or has no such field. Reading a diagnostic must never itself
    raise, so this guard swallows on purpose — the status is already the fact reported."""
    if not resp.content:
        return str(default)
    try:
        doc = resp.json()
    except ValueError:
        return str(default)
    if not isinstance(doc, dict) or not doc.get(field):
        return str(default)
    return str(doc[field])


def _path(url: str) -> str:
    return url.removeprefix(GITHUB_API)


def authorize_url(*, client_id: str, redirect_uri: str, state: str) -> str:
    """Where ``GET /auth/github/start`` sends the browser (R3)."""
    params = httpx.QueryParams(
        {"client_id": client_id, "redirect_uri": redirect_uri, "state": state}
    )
    return f"{GITHUB_AUTHORIZE_URL}?{params}"


def build(settings: Any) -> GitHost:
    return HttpxGitHost(
        client_id=settings.github_client_id or "",
        client_secret=settings.github_client_secret or "",
        app_id=settings.github_app_id or "",
        private_key=settings.github_private_key or "",
    )
