"""The Palomar registry as the network talks to it (F25-T6; D-10 v3.37).

Everything the export, the feed and the conformance tools ask of Palomar sits behind one
protocol, :class:`PalomarHost`, with a fake for every test and one real implementation over the
standard library — the shape ``opn_gate.watch.UpstreamHost`` gave the upstream watcher. Two
hosts: the read-only data host (``recent.json``, ``versions/<id>.json``,
``entries/<id>-v<n>.json``, ``repositories/<owner>/<repo>.json``,
``registration-identities/<sha256>.json``) and the intake host (``/api/submit``, ``/api/verify``,
``/api/submission``, ``/api/review``, ``/register``, ``/withdraw``), as Palomar's own protocol
summary (``submit.palomar-registry.org/llms.txt``) describes them.

Two rules Palomar states and the network keeps here, not in a caller: **an agent never
registers** — :meth:`PalomarHost.register` refuses unless the caller passes
``human_confirmed=True``, which only the CLI sets when a person says they have read the review —
and a ``Retry-After`` the host sends is honoured, never retried through.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol

DATA_HOST = "https://data.palomar-registry.org"
INTAKE_HOST = "https://submit.palomar-registry.org"
REGISTRY_HOST = "https://palomar-registry.org"
USER_AGENT = "opn-palomar (openproofnetwork.org)"
FETCH_TIMEOUT_S = 30
ID_RE = re.compile(r"^PALOMAR-[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{6}$")
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
#: Palomar's settled submission statuses (its protocol summary).
SETTLED_STATUSES: frozenset[str] = frozenset(
    {
        "registered",
        "withdrawn",
        "verification-failed",
        "verification-error",
        "review-failed",
        "dispatch-lost",
    }
)


class PalomarError(Exception):
    """The host did not answer, or answered with an error the caller must see."""


class PalomarRefusedError(PalomarError):
    """A 4xx the caller can act on: ``status``, the body's ``error`` and the body."""

    def __init__(self, status: int, error: str, body: dict[str, Any] | None = None) -> None:
        super().__init__(f"palomar answered {status}: {error}")
        self.status = status
        self.error = error
        self.body = body or {}


class PalomarBusyError(PalomarError):
    """A 429 or 503 with the seconds to wait; the caller waits, never retries through it."""

    def __init__(self, status: int, retry_after_s: int, message: str) -> None:
        super().__init__(f"palomar answered {status}: {message} (retry after {retry_after_s}s)")
        self.status = status
        self.retry_after_s = retry_after_s


class HumanConfirmationRequiredError(PalomarError):
    """``register`` was called without a person's word (D-10 v3.37; Palomar's own rule)."""


def entry_url(registry_id: str, version: int) -> str:
    return f"{REGISTRY_HOST}/entries/{registry_id}-v{version}"


def identity_digest(repository: str, project_path: str | None, comparator_config_path: str) -> str:
    """Palomar's registration-identity key: sha256 over ``lowercase_repository NUL
    project_path_or_empty NUL comparator_config_path``."""
    raw = b"\0".join(
        [
            repository.lower().encode(),
            (project_path or "").encode(),
            comparator_config_path.encode(),
        ]
    )
    return hashlib.sha256(raw).hexdigest()


class PalomarHost(Protocol):
    """Everything the network asks of Palomar."""

    # --- the data host (public, CC0) ---
    def recent(self) -> dict[str, Any]:
        """``recent.json``: ``{"entries": [...]}``."""

    def versions(self, registry_id: str) -> dict[str, Any] | None:
        """``versions/<id>.json``, or ``None`` when the id is unknown."""

    def entry(self, registry_id: str, version: int) -> dict[str, Any] | None:
        """``entries/<id>-v<n>.json``, or ``None``."""

    def repository(self, owner: str, repo: str) -> dict[str, Any] | None:
        """``repositories/<owner>/<repo>.json``, or ``None``."""

    def identity(self, digest: str) -> dict[str, Any] | None:
        """``registration-identities/<sha256>.json``, or ``None``."""

    # --- the intake host (the curator's act; a token the network never stores) ---
    def submit(self, body: dict[str, Any]) -> dict[str, Any]:
        """``POST /api/submit`` → ``{pending_secret, challenge, instructions}``."""

    def verify(self, pending_secret: str, gist_id: str) -> dict[str, Any]:
        """``POST /api/verify`` → ``{submission_id, access_token}``."""

    def submission(self, access_token: str) -> dict[str, Any]:
        """``GET /api/submission``."""

    def review(self, access_token: str) -> dict[str, Any] | None:
        """``GET /api/review``, or ``None`` while it 404s."""

    def register(
        self, access_token: str, review_sha256: str, *, human_confirmed: bool
    ) -> dict[str, Any]:
        """``POST /register``; refused without a person's confirmation."""

    def withdraw(self, access_token: str) -> dict[str, Any]:
        """``POST /withdraw``."""


# --- the real one ----------------------------------------------------------------------------


def _retry_after(headers: Any, default: int = 60) -> int:
    raw = headers.get("Retry-After") if headers is not None else None
    try:
        return max(1, int(str(raw).strip())) if raw else default
    except ValueError:
        return default


class HttpPalomarHost:
    """Palomar over ``urllib``: one request per call, a timeout on each, ``Retry-After``
    surfaced as :class:`PalomarBusyError`, a 404 on the data host as ``None``."""

    def __init__(
        self,
        *,
        data_host: str = DATA_HOST,
        intake_host: str = INTAKE_HOST,
        timeout_s: int = FETCH_TIMEOUT_S,
    ) -> None:
        self.data_host = data_host.rstrip("/")
        self.intake_host = intake_host.rstrip("/")
        self.timeout_s = timeout_s

    def _call(
        self,
        method: str,
        url: str,
        *,
        body: dict[str, Any] | None = None,
        token: str | None = None,
        none_on_404: bool = False,
    ) -> dict[str, Any] | None:
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(url, data=data, method=method, headers=headers)  # noqa: S310
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as resp:  # noqa: S310
                return _decode(resp.read())
        except urllib.error.HTTPError as exc:
            if exc.code == 404 and none_on_404:
                return None
            payload = _decode(exc.read() or b"{}")
            if exc.code in (429, 503):
                raise PalomarBusyError(
                    exc.code, _retry_after(exc.headers), str(payload.get("error", ""))
                ) from exc
            raise PalomarRefusedError(
                exc.code, str(payload.get("error") or exc.reason), payload
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            msg = f"{method} {url} failed: {exc.__class__.__name__}"
            raise PalomarError(msg) from exc

    # data host
    def recent(self) -> dict[str, Any]:
        doc = self._call("GET", f"{self.data_host}/recent.json")
        return doc or {"entries": []}

    def versions(self, registry_id: str) -> dict[str, Any] | None:
        _check_id(registry_id)
        return self._call("GET", f"{self.data_host}/versions/{registry_id}.json", none_on_404=True)

    def entry(self, registry_id: str, version: int) -> dict[str, Any] | None:
        _check_id(registry_id)
        return self._call(
            "GET", f"{self.data_host}/entries/{registry_id}-v{int(version)}.json", none_on_404=True
        )

    def repository(self, owner: str, repo: str) -> dict[str, Any] | None:
        return self._call(
            "GET",
            f"{self.data_host}/repositories/{owner.lower()}/{repo.lower()}.json",
            none_on_404=True,
        )

    def identity(self, digest: str) -> dict[str, Any] | None:
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            msg = f"not a registration-identity digest: {digest!r}"
            raise PalomarError(msg)
        return self._call(
            "GET", f"{self.data_host}/registration-identities/{digest}.json", none_on_404=True
        )

    # intake host
    def submit(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._call("POST", f"{self.intake_host}/api/submit", body=body) or {}

    def verify(self, pending_secret: str, gist_id: str) -> dict[str, Any]:
        body = {"pending_secret": pending_secret, "gist_id": gist_id}
        return self._call("POST", f"{self.intake_host}/api/verify", body=body) or {}

    def submission(self, access_token: str) -> dict[str, Any]:
        return self._call("GET", f"{self.intake_host}/api/submission", token=access_token) or {}

    def review(self, access_token: str) -> dict[str, Any] | None:
        return self._call(
            "GET", f"{self.intake_host}/api/review", token=access_token, none_on_404=True
        )

    def register(
        self, access_token: str, review_sha256: str, *, human_confirmed: bool
    ) -> dict[str, Any]:
        _require_human(human_confirmed)
        body = {"review_sha256": review_sha256}
        return (
            self._call("POST", f"{self.intake_host}/register", body=body, token=access_token) or {}
        )

    def withdraw(self, access_token: str) -> dict[str, Any]:
        return self._call("POST", f"{self.intake_host}/withdraw", body={}, token=access_token) or {}


def _decode(raw: bytes) -> dict[str, Any]:
    try:
        doc = json.loads(raw.decode("utf-8")) if raw else {}
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        msg = "palomar answered something that is not JSON"
        raise PalomarError(msg) from exc
    return doc if isinstance(doc, dict) else {"value": doc}


def _check_id(registry_id: str) -> None:
    if not ID_RE.match(registry_id):
        msg = f"not a Palomar id: {registry_id!r}"
        raise PalomarError(msg)


def _require_human(human_confirmed: bool) -> None:
    if human_confirmed is not True:
        msg = (
            "registering is the person's act who has read the review (D-10 v3.37; Palomar's "
            "protocol says the same): pass human_confirmed=True from the CLI's flag, never from "
            "code"
        )
        raise HumanConfirmationRequiredError(msg)


# --- the fake ---------------------------------------------------------------------------------


@dataclass
class FakePalomarHost:
    """A Palomar in memory for tests: seeded data documents, a scripted intake, a log of every
    call. ``busy`` makes the next call answer 429 with ``retry_after_s``."""

    entries: dict[tuple[str, int], dict[str, Any]] = field(default_factory=dict)
    feed: list[dict[str, Any]] = field(default_factory=list)
    repositories: dict[str, dict[str, Any]] = field(default_factory=dict)
    identities: dict[str, dict[str, Any]] = field(default_factory=dict)
    submissions: dict[str, dict[str, Any]] = field(default_factory=dict)  # token -> state
    reviews: dict[str, dict[str, Any]] = field(default_factory=dict)  # token -> review
    calls: list[tuple[str, tuple[Any, ...]]] = field(default_factory=list)
    busy: int | None = None
    refuse_next: PalomarRefusedError | None = None
    counter: int = 0

    def _log(self, name: str, *args: Any) -> None:
        self.calls.append((name, args))
        if self.busy is not None:
            wait, self.busy = self.busy, None
            raise PalomarBusyError(429, wait, "spacing")
        if self.refuse_next is not None:
            exc, self.refuse_next = self.refuse_next, None
            raise exc

    def recent(self) -> dict[str, Any]:
        self._log("recent")
        return {"entries": list(self.feed)}

    def versions(self, registry_id: str) -> dict[str, Any] | None:
        self._log("versions", registry_id)
        _check_id(registry_id)
        found = sorted(v for (i, v) in self.entries if i == registry_id)
        if not found:
            return None
        return {
            "id": registry_id,
            "schema_version": 2,
            "entries": [
                {
                    "id": registry_id,
                    "version": v,
                    "path": f"entries/{registry_id}-v{v}.json",
                    "status": self.entries[(registry_id, v)].get("status", "registered"),
                    "title": self.entries[(registry_id, v)].get("title", ""),
                }
                for v in found
            ],
        }

    def entry(self, registry_id: str, version: int) -> dict[str, Any] | None:
        self._log("entry", registry_id, version)
        _check_id(registry_id)
        return self.entries.get((registry_id, int(version)))

    def repository(self, owner: str, repo: str) -> dict[str, Any] | None:
        self._log("repository", owner, repo)
        return self.repositories.get(f"{owner}/{repo}".lower())

    def identity(self, digest: str) -> dict[str, Any] | None:
        self._log("identity", digest)
        return self.identities.get(digest)

    def submit(self, body: dict[str, Any]) -> dict[str, Any]:
        self._log("submit", body)
        self.counter += 1
        secret = f"secret-{self.counter}"
        self.submissions[secret] = {"body": dict(body), "status": "pending-verification"}
        return {
            "pending_secret": secret,
            "challenge": f"challenge-{self.counter}",
            "instructions": "tag + gist",
        }

    def verify(self, pending_secret: str, gist_id: str) -> dict[str, Any]:
        self._log("verify", pending_secret, gist_id)
        state = self.submissions.pop(pending_secret, None)
        if state is None:
            raise PalomarRefusedError(404, "that submission has already been verified")
        token = f"token-{self.counter}"
        self.submissions[token] = {
            **state,
            "status": "verifying",
            "submission_id": f"sub-{self.counter}",
        }
        return {"submission_id": f"sub-{self.counter}", "access_token": token}

    def submission(self, access_token: str) -> dict[str, Any]:
        self._log("submission", access_token)
        state = self.submissions.get(access_token)
        if state is None:
            raise PalomarRefusedError(401, "unknown token")
        return {"status": state["status"], "submission_id": state["submission_id"]}

    def review(self, access_token: str) -> dict[str, Any] | None:
        self._log("review", access_token)
        return self.reviews.get(access_token)

    def register(
        self, access_token: str, review_sha256: str, *, human_confirmed: bool
    ) -> dict[str, Any]:
        _require_human(human_confirmed)
        self._log("register", access_token, review_sha256)
        review = self.reviews.get(access_token)
        if review is None or review.get("sha256") != review_sha256:
            raise PalomarRefusedError(409, "review digest mismatch")
        self.submissions[access_token]["status"] = "registered"
        return {"status": "registered"}

    def withdraw(self, access_token: str) -> dict[str, Any]:
        self._log("withdraw", access_token)
        if access_token in self.submissions:
            self.submissions[access_token]["status"] = "withdrawn"
        return {"status": "withdrawn"}
