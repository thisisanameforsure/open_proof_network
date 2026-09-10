"""The real GitHub seam, ``HttpxGitHost``, driven without a network (F05-R3, R9; F06-R3, R5;
F07-R2; C8).

The fake host in ``api_fakes`` proves the routes; nothing proved the seam itself until now. Here
``httpx.Client`` is replaced, inside ``opn_api.githost`` only, by one bound to a scripted
``MockTransport``: each test scripts the status codes and bodies GitHub would answer with and
reads back every request the seam made. Every test is a failing case the seam must map to a
``GitHostError`` naming the call and the status — never the credential that made it (C8) — or a
wire shape the seam must send exactly (the author/committer split, the JWT claims).
"""

from __future__ import annotations

import base64
import json
import logging
from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa

from opn_api import githost
from opn_api.githost import Author, GitHostError, HttpxGitHost

REPO = "owner/scratch"
APP_ID = "12345"
CLIENT_SECRET = "cs_CLIENT_SECRET_NEVER_LOGGED"  # noqa: S105 — a sentinel, not a secret
ACCESS_TOKEN = "gho_ACCESS_TOKEN_NEVER_LOGGED"  # noqa: S105
INSTALLATION_TOKEN = "ghs_INSTALLATION_TOKEN_NEVER_LOGGED"  # noqa: S105
NOW = 1_800_000_000.0
BASE_SHA = "a" * 40
BASE_TREE = "b" * 40
NEW_TREE = "c" * 40
COMMIT_SHA = "d" * 40


# --- the scripted transport ------------------------------------------------------------------


@dataclass
class Script:
    """What GitHub will answer, by ``(method, path)``, and every request the seam made.

    A path scripted once answers every call to it; scripted several times the answers are
    consumed in order and the last one repeats. An unscripted call is a test error, not a
    response the seam could mistake for GitHub's.
    """

    calls: list[httpx.Request] = field(default_factory=list)
    routes: dict[tuple[str, str], deque[httpx.Response | Exception]] = field(default_factory=dict)

    def on(
        self,
        method: str,
        path: str,
        status: int = 200,
        *,
        json: Any = None,
        content: bytes | None = None,
        text: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> Script:
        response = httpx.Response(
            status, json=json, content=content, text=text, headers=headers or {}
        )
        self.routes.setdefault((method, path), deque()).append(response)
        return self

    def fail(self, method: str, path: str, exc: Exception) -> Script:
        self.routes.setdefault((method, path), deque()).append(exc)
        return self

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        queue = self.routes.get((request.method, request.url.path))
        if not queue:
            msg = f"unscripted {request.method} {request.url}"
            raise AssertionError(msg)
        item = queue.popleft() if len(queue) > 1 else queue[0]
        if isinstance(item, Exception):
            raise item
        return item

    def to(self, method: str, path: str) -> list[httpx.Request]:
        return [c for c in self.calls if c.method == method and c.url.path == path]

    def sent(self, method: str, path: str) -> Any:
        """The JSON body of the one call to ``path``."""
        (call,) = self.to(method, path)
        return json.loads(call.content)


class _Httpx:
    """``opn_api.githost.httpx`` for the duration of a test: the real module, except that
    ``Client`` is bound to the script. The real ``httpx`` module is never touched."""

    def __init__(self, client: type[httpx.Client]) -> None:
        self._client = client

    def __getattr__(self, name: str) -> Any:
        return self._client if name == "Client" else getattr(httpx, name)


@pytest.fixture
def script(monkeypatch: pytest.MonkeyPatch) -> Script:
    scripted = Script()

    class Scripted(httpx.Client):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(transport=httpx.MockTransport(scripted.handler), **kwargs)

    monkeypatch.setattr(githost, "httpx", _Httpx(Scripted))
    return scripted


@dataclass
class Clock:
    now: float = NOW

    def time(self) -> float:
        return self.now


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    frozen = Clock()
    monkeypatch.setattr(githost, "time", SimpleNamespace(time=frozen.time))
    return frozen


@pytest.fixture(scope="module")
def rsa_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="module")
def pem(rsa_key: rsa.RSAPrivateKey) -> str:
    return rsa_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()


@pytest.fixture
def host(pem: str) -> HttpxGitHost:
    return HttpxGitHost(
        client_id="Iv1.test", client_secret=CLIENT_SECRET, app_id=APP_ID, private_key=pem
    )


@pytest.fixture
def secrets(pem: str) -> list[str]:
    """Every credential a message or log line must never carry (C8)."""
    body = [line for line in pem.splitlines() if not line.startswith("-----")]
    return [CLIENT_SECRET, ACCESS_TOKEN, INSTALLATION_TOKEN, *body[:3]]


@pytest.fixture
def logs(caplog: pytest.LogCaptureFixture) -> Iterator[pytest.LogCaptureFixture]:
    with caplog.at_level(logging.DEBUG):
        yield caplog


def assert_clean(text: str, secrets: list[str]) -> None:
    for secret in secrets:
        assert secret not in text, f"credential material leaked: {secret[:12]}…"


def install_app(script: Script) -> Script:
    """The two calls behind every App-authenticated request (F06-R3)."""
    return script.on("GET", f"/repos/{REPO}/installation", json={"id": 99}).on(
        "POST", "/app/installations/99/access_tokens", 201, json={"token": INSTALLATION_TOKEN}
    )


def b64url_decode(part: str) -> bytes:
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


def jwt_sent(script: Script) -> str:
    (call,) = script.to("GET", f"/repos/{REPO}/installation")
    return call.headers["Authorization"].removeprefix("Bearer ")


# --- exchange_code (F05-R3, AC5) ---------------------------------------------------------------


def exchange_ok(script: Script) -> Script:
    return script.on("POST", "/login/oauth/access_token", json={"access_token": ACCESS_TOKEN})


def test_exchange_transport_failure_names_the_exception_type_not_the_secret(
    script: Script, host: HttpxGitHost, secrets: list[str], logs: pytest.LogCaptureFixture
) -> None:
    script.fail("POST", "/login/oauth/access_token", httpx.ConnectError("dns"))
    with pytest.raises(GitHostError, match=r"token exchange failed: ConnectError$") as raised:
        host.exchange_code("code-1", redirect_uri="https://api/cb")
    assert_clean(str(raised.value) + logs.text, secrets)


def test_exchange_error_body_with_200_is_a_refusal(script: Script, host: HttpxGitHost) -> None:
    """GitHub answers OAuth errors with 200 and an ``error`` field; the seam must not read the
    absent token as anything but a refusal."""
    script.on("POST", "/login/oauth/access_token", json={"error": "bad_verification_code"})
    with pytest.raises(GitHostError, match="refused the code: bad_verification_code"):
        host.exchange_code("code-1", redirect_uri="https://api/cb")
    assert script.to("GET", "/user") == []


def test_exchange_non_200_with_empty_body_names_the_status(
    script: Script, host: HttpxGitHost
) -> None:
    script.on("POST", "/login/oauth/access_token", 503, content=b"")
    with pytest.raises(GitHostError, match="refused the code: 503"):
        host.exchange_code("code-1", redirect_uri="https://api/cb")


@pytest.mark.xfail(
    strict=True,
    raises=json.JSONDecodeError,
    reason="githost.py:179 calls exchange.json() before checking the status, unguarded: a "
    "non-JSON body (an edge proxy's HTML 502) escapes as JSONDecodeError, so the callback "
    "answers 500 instead of the mapped 502 github-exchange-failed (C7)",
)
def test_exchange_non_json_body_is_a_githost_error(script: Script, host: HttpxGitHost) -> None:
    script.on("POST", "/login/oauth/access_token", 502, text="<html>Bad Gateway</html>")
    with pytest.raises(GitHostError):
        host.exchange_code("code-1", redirect_uri="https://api/cb")


def test_exchange_sends_the_secret_to_github_only_as_form_data(
    script: Script, host: HttpxGitHost
) -> None:
    exchange_ok(script).on(
        "GET", "/user", json={"login": "alice", "id": 1001, "created_at": "2015-03-01T00:00:00Z"}
    )
    user = host.exchange_code("code-1", redirect_uri="https://api/cb")
    assert user.login == "alice"
    (call,) = script.to("POST", "/login/oauth/access_token")
    assert call.headers["Accept"] == "application/json"
    form = dict(httpx.QueryParams(call.content.decode()))
    assert form == {
        "client_id": "Iv1.test",
        "client_secret": CLIENT_SECRET,
        "code": "code-1",
        "redirect_uri": "https://api/cb",
    }
    (lookup,) = script.to("GET", "/user")
    assert lookup.headers["Authorization"] == f"Bearer {ACCESS_TOKEN}"


def test_user_lookup_transport_failure_drops_the_access_token(
    script: Script, host: HttpxGitHost, secrets: list[str], logs: pytest.LogCaptureFixture
) -> None:
    exchange_ok(script).fail("GET", "/user", httpx.ReadTimeout("slow"))
    with pytest.raises(GitHostError, match=r"user lookup failed: ReadTimeout$") as raised:
        host.exchange_code("code-1", redirect_uri="https://api/cb")
    assert_clean(str(raised.value) + logs.text, secrets)


def test_user_lookup_401_names_the_status_only(
    script: Script, host: HttpxGitHost, secrets: list[str]
) -> None:
    exchange_ok(script).on("GET", "/user", 401, json={"message": "Bad credentials"})
    with pytest.raises(GitHostError, match=r"user lookup returned 401$") as raised:
        host.exchange_code("code-1", redirect_uri="https://api/cb")
    assert_clean(str(raised.value), secrets)


@pytest.mark.parametrize(
    "doc",
    [
        {"id": 1, "created_at": "2015-03-01T00:00:00Z"},
        {"login": "alice", "created_at": "2015-03-01T00:00:00Z"},
        {"login": "alice", "id": "not-a-number", "created_at": "2015-03-01T00:00:00Z"},
        {"login": "alice", "id": None, "created_at": "2015-03-01T00:00:00Z"},
    ],
    ids=["no-login", "no-id", "id-not-int", "id-null"],
)
def test_user_document_missing_a_field_is_refused(
    script: Script, host: HttpxGitHost, doc: dict[str, Any]
) -> None:
    exchange_ok(script).on("GET", "/user", json=doc)
    with pytest.raises(GitHostError, match="missing login, id or created_at"):
        host.exchange_code("code-1", redirect_uri="https://api/cb")


@pytest.mark.xfail(
    strict=True,
    raises=json.JSONDecodeError,
    reason="githost.py:196 user.json() is unguarded: a non-JSON 200 body escapes as "
    "JSONDecodeError instead of a GitHostError the callback maps to 502 (C7)",
)
def test_user_document_not_json_is_a_githost_error(script: Script, host: HttpxGitHost) -> None:
    exchange_ok(script).on("GET", "/user", text="not json")
    with pytest.raises(GitHostError):
        host.exchange_code("code-1", redirect_uri="https://api/cb")


# --- fetch_raw (F05-R9) ------------------------------------------------------------------------


def test_fetch_transport_failure_names_path_repo_and_exception_type(
    script: Script, host: HttpxGitHost
) -> None:
    script.fail("GET", "/owner/graph/main/frontier.json", httpx.ConnectError("down"))
    with pytest.raises(
        GitHostError, match=r"fetching frontier.json from owner/graph@main failed: ConnectError$"
    ):
        host.fetch_raw("owner/graph", "main", "frontier.json", etag=None)


@pytest.mark.parametrize("status", [404, 500, 429])
def test_fetch_error_status_is_returned_not_raised(
    script: Script, host: HttpxGitHost, status: int
) -> None:
    """R9's caller decides what a missing or unavailable file means; the seam reports the
    status with no body and no etag, so a stale cache is never refreshed from an error page."""
    script.on("GET", "/owner/graph/main/frontier.json", status, text="<html>error</html>")
    fetched = host.fetch_raw("owner/graph", "main", "frontier.json", etag='"old"')
    assert fetched == githost.Fetched(status, None, None)


def test_fetch_sends_if_none_match_and_returns_304_with_the_same_etag(
    script: Script, host: HttpxGitHost
) -> None:
    script.on("GET", "/owner/graph/main/frontier.json", 304)
    fetched = host.fetch_raw("owner/graph", "main", "frontier.json", etag='"v1"')
    assert fetched == githost.Fetched(304, '"v1"', None)
    (call,) = script.to("GET", "/owner/graph/main/frontier.json")
    assert call.headers["If-None-Match"] == '"v1"'


def test_fetch_without_etag_sends_no_conditional_header(script: Script, host: HttpxGitHost) -> None:
    script.on(
        "GET", "/owner/graph/main/frontier.json", 200, content=b"{}", headers={"ETag": '"v2"'}
    )
    fetched = host.fetch_raw("owner/graph", "main", "frontier.json", etag=None)
    assert fetched == githost.Fetched(200, '"v2"', b"{}")
    (call,) = script.to("GET", "/owner/graph/main/frontier.json")
    assert "If-None-Match" not in call.headers


# --- the App JWT (F06-R3; C8 item 3; F06-Q5) ---------------------------------------------------


def test_jwt_refused_when_the_app_is_not_configured(script: Script) -> None:
    host = HttpxGitHost(client_id="Iv1.test", client_secret=CLIENT_SECRET)
    with pytest.raises(GitHostError, match="App id and private key are not configured"):
        host.dispatch_workflow(REPO, "precheck.yml", ref="main", inputs={})
    assert script.calls == []


def test_build_without_app_settings_yields_a_host_that_refuses_app_calls(
    script: Script,
) -> None:
    settings = SimpleNamespace(
        github_client_id=None,
        github_client_secret=None,
        github_app_id=None,
        github_private_key=None,
    )
    built = githost.build(settings)
    with pytest.raises(GitHostError, match="not configured"):
        built.find_run(REPO, "precheck.yml", branch="job/x")


def test_unreadable_private_key_names_the_exception_type_not_the_key(script: Script) -> None:
    garbage = (
        "-----BEGIN RSA PRIVATE KEY-----\nTHIS_IS_NOT_A_KEY_zzzz\n-----END RSA PRIVATE KEY-----"
    )
    host = HttpxGitHost(
        client_id="Iv1.test", client_secret=CLIENT_SECRET, app_id=APP_ID, private_key=garbage
    )
    with pytest.raises(GitHostError, match=r"private key cannot be read: ValueError$") as raised:
        host.find_run(REPO, "precheck.yml", branch="job/x")
    assert "THIS_IS_NOT_A_KEY" not in str(raised.value)
    assert script.calls == []


def test_non_rsa_private_key_is_refused(script: Script) -> None:
    ed_pem = (
        ed25519.Ed25519PrivateKey.generate()
        .private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        .decode()
    )
    host = HttpxGitHost(
        client_id="Iv1.test", client_secret=CLIENT_SECRET, app_id=APP_ID, private_key=ed_pem
    )
    with pytest.raises(GitHostError, match="not an RSA key"):
        host.find_run(REPO, "precheck.yml", branch="job/x")
    assert script.calls == []


def test_jwt_claims_expiry_window_and_signature(
    script: Script, host: HttpxGitHost, clock: Clock, rsa_key: rsa.RSAPrivateKey
) -> None:
    """The JWT is backdated a minute for skew and lives nine minutes, inside GitHub's ten-minute
    cap; ``iss`` is the App id; the signature verifies with the App's public key."""
    install_app(script).on(
        "GET", f"/repos/{REPO}/actions/workflows/precheck.yml/runs", json={"workflow_runs": []}
    )
    host.find_run(REPO, "precheck.yml", branch="job/x")
    token = jwt_sent(script)
    header_b64, claims_b64, signature_b64 = token.split(".")
    assert json.loads(b64url_decode(header_b64)) == {"alg": "RS256", "typ": "JWT"}
    claims = json.loads(b64url_decode(claims_b64))
    assert claims == {"iat": int(NOW) - 60, "exp": int(NOW) + 540, "iss": APP_ID}
    assert claims["exp"] - claims["iat"] <= 600
    rsa_key.public_key().verify(
        b64url_decode(signature_b64),
        f"{header_b64}.{claims_b64}".encode(),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )


# --- the installation token (F06-R3; C8) -------------------------------------------------------


def test_app_not_installed_404_names_the_call_and_status_not_the_jwt(
    script: Script, host: HttpxGitHost, secrets: list[str], logs: pytest.LogCaptureFixture
) -> None:
    script.on("GET", f"/repos/{REPO}/installation", 404, json={"message": "Not Found"})
    with pytest.raises(
        GitHostError, match=rf"GET /repos/{REPO}/installation returned 404: Not Found$"
    ) as raised:
        host.find_run(REPO, "precheck.yml", branch="job/x")
    assert jwt_sent(script) not in str(raised.value)
    assert_clean(str(raised.value) + logs.text, [*secrets, jwt_sent(script)])


def test_installation_document_without_an_id_is_not_installed(
    script: Script, host: HttpxGitHost
) -> None:
    script.on("GET", f"/repos/{REPO}/installation", json={})
    with pytest.raises(GitHostError, match=f"not installed on {REPO}"):
        host.find_run(REPO, "precheck.yml", branch="job/x")
    assert script.to("POST", "/app/installations/99/access_tokens") == []


def test_installation_token_401_names_the_status_not_the_jwt(
    script: Script, host: HttpxGitHost, secrets: list[str]
) -> None:
    script.on("GET", f"/repos/{REPO}/installation", json={"id": 99}).on(
        "POST", "/app/installations/99/access_tokens", 401, json={"message": "Bad credentials"}
    )
    with pytest.raises(
        GitHostError,
        match=r"POST /app/installations/99/access_tokens returned 401: Bad credentials$",
    ) as raised:
        host.find_run(REPO, "precheck.yml", branch="job/x")
    assert_clean(str(raised.value), [*secrets, jwt_sent(script)])


def test_installation_token_issued_empty_is_refused(script: Script, host: HttpxGitHost) -> None:
    script.on("GET", f"/repos/{REPO}/installation", json={"id": 99}).on(
        "POST", "/app/installations/99/access_tokens", 201, json={"expires_at": "soon"}
    )
    with pytest.raises(GitHostError, match=f"issued no installation token for {REPO}"):
        host.find_run(REPO, "precheck.yml", branch="job/x")


def test_installation_document_not_json_is_refused(script: Script, host: HttpxGitHost) -> None:
    script.on("GET", f"/repos/{REPO}/installation", text="<html>maintenance</html>")
    with pytest.raises(GitHostError, match=f"non-JSON body for /repos/{REPO}/installation"):
        host.find_run(REPO, "precheck.yml", branch="job/x")


def test_installation_document_not_an_object_is_refused(script: Script, host: HttpxGitHost) -> None:
    script.on("GET", f"/repos/{REPO}/installation", json=[{"id": 99}])
    with pytest.raises(GitHostError, match="returned list, not an object"):
        host.find_run(REPO, "precheck.yml", branch="job/x")


def test_installation_token_is_cached_per_repo_and_renewed_before_expiry(
    script: Script, host: HttpxGitHost, clock: Clock
) -> None:
    install_app(script).on(
        "GET", f"/repos/{REPO}/actions/workflows/precheck.yml/runs", json={"workflow_runs": []}
    )
    other = "owner/graph"
    script.on("GET", f"/repos/{other}/installation", json={"id": 77}).on(
        "POST", "/app/installations/77/access_tokens", 201, json={"token": "ghs_OTHER"}
    ).on("GET", f"/repos/{other}/actions/workflows/gate.yml/runs", json={"workflow_runs": []})

    host.find_run(REPO, "precheck.yml", branch="job/x")
    host.find_run(REPO, "precheck.yml", branch="job/y")
    assert len(script.to("POST", "/app/installations/99/access_tokens")) == 1
    runs = script.to("GET", f"/repos/{REPO}/actions/workflows/precheck.yml/runs")
    assert [r.headers["Authorization"] for r in runs] == [f"Bearer {INSTALLATION_TOKEN}"] * 2

    host.find_run(other, "gate.yml", branch="job/z")
    assert len(script.to("POST", "/app/installations/77/access_tokens")) == 1
    (run,) = script.to("GET", f"/repos/{other}/actions/workflows/gate.yml/runs")
    assert run.headers["Authorization"] == "Bearer ghs_OTHER"

    clock.now = NOW + 3600 - 300  # exactly the refresh margin before the hour: renew
    host.find_run(REPO, "precheck.yml", branch="job/x")
    assert len(script.to("POST", "/app/installations/99/access_tokens")) == 2


def test_installation_token_within_the_margin_is_reused(
    script: Script, host: HttpxGitHost, clock: Clock
) -> None:
    install_app(script).on(
        "GET", f"/repos/{REPO}/actions/workflows/precheck.yml/runs", json={"workflow_runs": []}
    )
    host.find_run(REPO, "precheck.yml", branch="job/x")
    clock.now = NOW + 3600 - 301
    host.find_run(REPO, "precheck.yml", branch="job/x")
    assert len(script.to("POST", "/app/installations/99/access_tokens")) == 1


def test_installation_token_failure_is_not_cached(script: Script, host: HttpxGitHost) -> None:
    script.on("GET", f"/repos/{REPO}/installation", json={"id": 99}).on(
        "POST", "/app/installations/99/access_tokens", 500, json={"message": "boom"}
    ).on("POST", "/app/installations/99/access_tokens", 201, json={"token": INSTALLATION_TOKEN}).on(
        "GET", f"/repos/{REPO}/actions/workflows/precheck.yml/runs", json={"workflow_runs": []}
    )
    with pytest.raises(GitHostError, match="returned 500"):
        host.find_run(REPO, "precheck.yml", branch="job/x")
    assert host.find_run(REPO, "precheck.yml", branch="job/x") is None
    assert len(script.to("POST", "/app/installations/99/access_tokens")) == 2


# --- error mapping in _send (C8) ---------------------------------------------------------------


def test_4xx_with_non_json_body_names_the_status_alone(script: Script, host: HttpxGitHost) -> None:
    install_app(script).on(
        "GET", f"/repos/{REPO}/actions/workflows/precheck.yml/runs", 502, text="<html>"
    )
    with pytest.raises(
        GitHostError, match=rf"GET /repos/{REPO}/actions/workflows/precheck.yml/runs returned 502$"
    ):
        host.find_run(REPO, "precheck.yml", branch="job/x")


def test_4xx_json_without_a_message_names_the_status_alone(
    script: Script, host: HttpxGitHost
) -> None:
    install_app(script).on(
        "GET", f"/repos/{REPO}/actions/workflows/precheck.yml/runs", 403, json={"errors": ["x"]}
    )
    with pytest.raises(GitHostError, match=r"returned 403$"):
        host.find_run(REPO, "precheck.yml", branch="job/x")


def test_a_5xx_is_not_retried(script: Script, host: HttpxGitHost) -> None:
    """There is no retry in the seam; the polling state machine is the retry (F06-R5)."""
    install_app(script).on(
        "GET", f"/repos/{REPO}/actions/workflows/precheck.yml/runs", 503, json={"message": "x"}
    ).on("GET", f"/repos/{REPO}/actions/workflows/precheck.yml/runs", json={"workflow_runs": []})
    with pytest.raises(GitHostError, match="returned 503"):
        host.find_run(REPO, "precheck.yml", branch="job/x")
    assert len(script.to("GET", f"/repos/{REPO}/actions/workflows/precheck.yml/runs")) == 1


def test_app_calls_carry_the_api_version_and_accept_headers(
    script: Script, host: HttpxGitHost
) -> None:
    install_app(script).on(
        "GET", f"/repos/{REPO}/actions/workflows/precheck.yml/runs", json={"workflow_runs": []}
    )
    host.find_run(REPO, "precheck.yml", branch="job/x")
    for call in script.calls:
        assert call.headers["Accept"] == githost.API_ACCEPT
        assert call.headers["X-GitHub-Api-Version"] == githost.API_VERSION


# --- push_branch (F06-R3; F07-R2 / D-23) -------------------------------------------------------


def push_ok(script: Script) -> Script:
    return (
        install_app(script)
        .on("GET", f"/repos/{REPO}/git/ref/heads/main", json={"object": {"sha": BASE_SHA}})
        .on("GET", f"/repos/{REPO}/git/commits/{BASE_SHA}", json={"tree": {"sha": BASE_TREE}})
        .on("POST", f"/repos/{REPO}/git/trees", 201, json={"sha": NEW_TREE})
        .on("POST", f"/repos/{REPO}/git/commits", 201, json={"sha": COMMIT_SHA})
        .on("POST", f"/repos/{REPO}/git/refs", 201, json={"ref": "refs/heads/job/1"})
    )


def test_push_to_a_missing_base_branch_names_the_ref_call(
    script: Script, host: HttpxGitHost, secrets: list[str]
) -> None:
    install_app(script).on(
        "GET", f"/repos/{REPO}/git/ref/heads/main", 404, json={"message": "Not Found"}
    )
    with pytest.raises(GitHostError, match=r"GET /repos/.*/git/ref/heads/main returned 404") as r:
        host.push_branch(REPO, "job/1", {"a.txt": "x"}, base="main", message="m")
    assert_clean(str(r.value), secrets)
    assert script.to("POST", f"/repos/{REPO}/git/trees") == []


def test_push_with_a_ref_document_lacking_a_sha_is_refused(
    script: Script, host: HttpxGitHost
) -> None:
    install_app(script).on("GET", f"/repos/{REPO}/git/ref/heads/main", json={"object": {}})
    with pytest.raises(GitHostError, match=f"{REPO} has no main branch to base a job on"):
        host.push_branch(REPO, "job/1", {"a.txt": "x"}, base="main", message="m")


def test_push_tree_422_carries_githubs_message(
    script: Script, host: HttpxGitHost, secrets: list[str]
) -> None:
    install_app(script).on(
        "GET", f"/repos/{REPO}/git/ref/heads/main", json={"object": {"sha": BASE_SHA}}
    ).on("GET", f"/repos/{REPO}/git/commits/{BASE_SHA}", json={"tree": {"sha": BASE_TREE}}).on(
        "POST",
        f"/repos/{REPO}/git/trees",
        422,
        json={
            "message": 'Invalid request.\n\n"tree" wasn\'t supplied.',
            "documentation_url": "https://docs.github.com/rest/git/trees",
        },
    )
    with pytest.raises(GitHostError, match=r"git/trees returned 422: Invalid request") as raised:
        host.push_branch(REPO, "job/1", {"a.txt": "x"}, base="main", message="m")
    assert_clean(str(raised.value), secrets)
    assert script.to("POST", f"/repos/{REPO}/git/commits") == []


def test_push_to_an_existing_branch_is_a_422_from_the_refs_call(
    script: Script, host: HttpxGitHost
) -> None:
    push_ok(script).routes[("POST", f"/repos/{REPO}/git/refs")] = deque(
        [httpx.Response(422, json={"message": "Reference already exists"})]
    )
    with pytest.raises(GitHostError, match="git/refs returned 422: Reference already exists"):
        host.push_branch(REPO, "job/1", {"a.txt": "x"}, base="main", message="m")


def test_push_sends_author_and_committer_both_named_explicitly(
    script: Script, host: HttpxGitHost
) -> None:
    """F07-R2, D-23: the contributor authors and the App commits — both fields sent, because
    the Git Data API copies the author into an absent committer (the live-found defect)."""
    push_ok(script)
    author = Author("alice-p", "alice-p@users.noreply.example", "2026-09-10T12:00:00Z")
    committer = Author("opn-app[bot]", "opn-app[bot]@users.noreply.example", "2026-09-10T12:00:01Z")
    sha = host.push_branch(
        REPO,
        "job/1",
        {"z.lean": "z", "a.lean": "a"},
        base="main",
        message="F07 submission",
        author=author,
        committer=committer,
    )
    assert sha == COMMIT_SHA
    commit = script.sent("POST", f"/repos/{REPO}/git/commits")
    assert commit == {
        "message": "F07 submission",
        "tree": NEW_TREE,
        "parents": [BASE_SHA],
        "author": {
            "name": "alice-p",
            "email": "alice-p@users.noreply.example",
            "date": "2026-09-10T12:00:00Z",
        },
        "committer": {
            "name": "opn-app[bot]",
            "email": "opn-app[bot]@users.noreply.example",
            "date": "2026-09-10T12:00:01Z",
        },
    }
    assert commit["author"] != commit["committer"]


def test_push_without_attribution_sends_neither_field(script: Script, host: HttpxGitHost) -> None:
    """The scratch push (F06-R3) names nobody: the App is then author and committer alike."""
    push_ok(script)
    host.push_branch(REPO, "job/1", {"a.txt": "x"}, base="main", message="m")
    commit = script.sent("POST", f"/repos/{REPO}/git/commits")
    assert "author" not in commit
    assert "committer" not in commit


def test_push_tree_is_the_base_tree_plus_sorted_blobs_and_the_ref_is_created_last(
    script: Script, host: HttpxGitHost
) -> None:
    push_ok(script)
    host.push_branch(REPO, "job/1", {"z.lean": "z", "a.lean": "a"}, base="main", message="m")
    tree = script.sent("POST", f"/repos/{REPO}/git/trees")
    assert tree == {
        "base_tree": BASE_TREE,
        "tree": [
            {"path": "a.lean", "mode": githost.BLOB_MODE, "type": "blob", "content": "a"},
            {"path": "z.lean", "mode": githost.BLOB_MODE, "type": "blob", "content": "z"},
        ],
    }
    assert script.sent("POST", f"/repos/{REPO}/git/refs") == {
        "ref": "refs/heads/job/1",
        "sha": COMMIT_SHA,
    }
    order = [c.url.path for c in script.calls[2:]]
    assert order[-1] == f"/repos/{REPO}/git/refs"
    for call in script.calls[2:]:
        assert call.headers["Authorization"] == f"Bearer {INSTALLATION_TOKEN}"


# --- open_pull_request (F07-R2) ----------------------------------------------------------------


def test_pull_request_422_carries_githubs_validation_message(
    script: Script, host: HttpxGitHost, secrets: list[str]
) -> None:
    install_app(script).on(
        "POST",
        f"/repos/{REPO}/pulls",
        422,
        json={
            "message": "Validation Failed",
            "errors": [{"message": "No commits between main and job/1"}],
        },
    )
    with pytest.raises(GitHostError, match=r"pulls returned 422: Validation Failed$") as raised:
        host.open_pull_request(REPO, head="job/1", base="main", title="t", body="b")
    assert_clean(str(raised.value), secrets)


def test_pull_request_403_when_the_app_lacks_the_permission(
    script: Script, host: HttpxGitHost
) -> None:
    install_app(script).on(
        "POST",
        f"/repos/{REPO}/pulls",
        403,
        json={"message": "Resource not accessible by integration"},
    )
    with pytest.raises(GitHostError, match="returned 403: Resource not accessible by integration"):
        host.open_pull_request(REPO, head="job/1", base="main", title="t", body="b")


def test_pull_request_without_html_url_still_returns_its_number(
    script: Script, host: HttpxGitHost
) -> None:
    install_app(script).on("POST", f"/repos/{REPO}/pulls", 201, json={"number": 7})
    pr = host.open_pull_request(REPO, head="job/1", base="main", title="t", body="b")
    assert pr == githost.PullRequest(7, "")
    assert script.sent("POST", f"/repos/{REPO}/pulls") == {
        "head": "job/1",
        "base": "main",
        "title": "t",
        "body": "b",
    }


# --- dispatch_workflow (F06-R3, R10) -----------------------------------------------------------


DISPATCH = f"/repos/{REPO}/actions/workflows/precheck.yml/dispatches"


def test_dispatch_403_is_the_permission_probe(
    script: Script, host: HttpxGitHost, secrets: list[str]
) -> None:
    """The log's probe: 403 means the App lacks ``Actions: write``, whatever the ref."""
    install_app(script).on(
        "POST", DISPATCH, 403, json={"message": "Resource not accessible by integration"}
    )
    with pytest.raises(
        GitHostError,
        match=rf"POST {DISPATCH} returned 403: Resource not accessible by integration$",
    ) as raised:
        host.dispatch_workflow(REPO, "precheck.yml", ref="job/1", inputs={"job_id": "1"})
    assert_clean(str(raised.value), secrets)


def test_dispatch_422_no_ref_found_is_distinguishable_from_403(
    script: Script, host: HttpxGitHost
) -> None:
    install_app(script).on("POST", DISPATCH, 422, json={"message": "No ref found"})
    with pytest.raises(GitHostError, match=rf"POST {DISPATCH} returned 422: No ref found$"):
        host.dispatch_workflow(REPO, "precheck.yml", ref="job/none", inputs={})


def test_dispatch_404_when_the_workflow_file_is_missing(script: Script, host: HttpxGitHost) -> None:
    install_app(script).on("POST", DISPATCH, 404, json={"message": "Not Found"})
    with pytest.raises(GitHostError, match="returned 404: Not Found"):
        host.dispatch_workflow(REPO, "precheck.yml", ref="job/1", inputs={})


def test_dispatch_sends_ref_and_inputs_and_accepts_204(script: Script, host: HttpxGitHost) -> None:
    install_app(script).on("POST", DISPATCH, 204)
    host.dispatch_workflow(REPO, "precheck.yml", ref="job/1", inputs={"job_id": "1"})
    assert script.sent("POST", DISPATCH) == {"ref": "job/1", "inputs": {"job_id": "1"}}


# --- find_run (F06-R5) -------------------------------------------------------------------------


RUNS = f"/repos/{REPO}/actions/workflows/precheck.yml/runs"


@pytest.mark.parametrize("page", [{}, {"workflow_runs": []}, {"workflow_runs": None}])
def test_find_run_with_no_runs_is_none(
    script: Script, host: HttpxGitHost, page: dict[str, Any]
) -> None:
    install_app(script).on("GET", RUNS, json=page)
    assert host.find_run(REPO, "precheck.yml", branch="job/1") is None
    (call,) = script.to("GET", RUNS)
    assert dict(call.url.params) == {"branch": "job/1", "per_page": "1"}


def test_find_run_in_progress_has_no_conclusion(script: Script, host: HttpxGitHost) -> None:
    install_app(script).on(
        "GET",
        RUNS,
        json={
            "workflow_runs": [
                {"id": 4242, "status": "in_progress", "conclusion": None, "html_url": "u"}
            ]
        },
    )
    run = host.find_run(REPO, "precheck.yml", branch="job/1")
    assert run == githost.WorkflowRun(4242, "in_progress", None, "u")
    assert not run.completed
    assert not run.succeeded


def test_find_run_completed_failure_is_not_succeeded(script: Script, host: HttpxGitHost) -> None:
    install_app(script).on(
        "GET",
        RUNS,
        json={"workflow_runs": [{"id": 1, "status": "completed", "conclusion": "failure"}]},
    )
    run = host.find_run(REPO, "precheck.yml", branch="job/1")
    assert run == githost.WorkflowRun(1, "completed", "failure", "")
    assert run.completed
    assert not run.succeeded


def test_find_run_non_json_page_is_refused(script: Script, host: HttpxGitHost) -> None:
    install_app(script).on("GET", RUNS, text="<html>")
    with pytest.raises(GitHostError, match=f"non-JSON body for {RUNS}"):
        host.find_run(REPO, "precheck.yml", branch="job/1")


# --- download_artifact (F06-R5; C8) ------------------------------------------------------------


LISTING = f"/repos/{REPO}/actions/runs/4242/artifacts"
ZIP = f"/repos/{REPO}/actions/artifacts/77/zip"


@pytest.mark.parametrize(
    "listing",
    [
        {},
        {"artifacts": []},
        {"artifacts": [{"id": 1, "name": "result-other"}]},
        {"artifacts": [{"id": 1}]},
    ],
    ids=["no-key", "empty", "other-name", "nameless"],
)
def test_download_with_no_matching_artifact_is_none(
    script: Script, host: HttpxGitHost, listing: dict[str, Any]
) -> None:
    install_app(script).on("GET", LISTING, json=listing)
    assert host.download_artifact(REPO, 4242, "result-1") is None
    assert [c.url.path for c in script.calls[2:]] == [LISTING]


def test_download_of_an_expired_artifact_is_a_410(script: Script, host: HttpxGitHost) -> None:
    install_app(script).on("GET", LISTING, json={"artifacts": [{"id": 77, "name": "result-1"}]})
    script.on("GET", ZIP, 410, json={"message": "Artifact has expired"})
    with pytest.raises(GitHostError, match=rf"GET {ZIP} returned 410: Artifact has expired$"):
        host.download_artifact(REPO, 4242, "result-1")


def test_download_truncated_mid_body_is_a_read_error(
    script: Script, host: HttpxGitHost, secrets: list[str]
) -> None:
    install_app(script).on("GET", LISTING, json={"artifacts": [{"id": 77, "name": "result-1"}]})
    script.fail("GET", ZIP, httpx.ReadError("connection closed"))
    with pytest.raises(GitHostError, match=rf"GET {ZIP} failed: ReadError$") as raised:
        host.download_artifact(REPO, 4242, "result-1")
    assert_clean(str(raised.value), secrets)


def test_download_follows_the_blob_redirect_without_the_installation_token(
    script: Script, host: HttpxGitHost
) -> None:
    """The zip endpoint redirects to blob storage with a signed URL; the seam relies on httpx
    stripping ``Authorization`` on a cross-origin redirect (C8). Proved, not assumed."""
    install_app(script).on("GET", LISTING, json={"artifacts": [{"id": 77, "name": "result-1"}]})
    script.on("GET", ZIP, 302, headers={"Location": "https://blob.example/signed?sig=abc"})
    script.on("GET", "/signed", 200, content=b"PK\x03\x04zip-bytes")
    assert host.download_artifact(REPO, 4242, "result-1") == b"PK\x03\x04zip-bytes"
    (blob,) = script.to("GET", "/signed")
    assert blob.url.host == "blob.example"
    assert "Authorization" not in blob.headers
    (zipped,) = script.to("GET", ZIP)
    assert zipped.headers["Authorization"] == f"Bearer {INSTALLATION_TOKEN}"
    assert zipped.extensions["timeout"]["read"] == githost.ARTIFACT_TIMEOUT_S
    (listing,) = script.to("GET", LISTING)
    assert listing.extensions["timeout"]["read"] == githost.TIMEOUT_S


def test_download_returns_an_oversized_body_whole(script: Script, host: HttpxGitHost) -> None:
    """The seam does not cap the body; ``precheck.MAX_RESULT_BYTES`` applies after the whole
    artifact is in memory (F06 §6). Recorded here so the split is a named fact, not a surprise."""
    from opn_api import precheck  # noqa: PLC0415 — the cap's owner, named where it is tested

    install_app(script).on("GET", LISTING, json={"artifacts": [{"id": 77, "name": "result-1"}]})
    big = b"x" * (precheck.MAX_RESULT_BYTES + 1)
    script.on("GET", ZIP, 200, content=big)
    assert host.download_artifact(REPO, 4242, "result-1") == big


# --- authorize_url (F05-R3) --------------------------------------------------------------------


def test_authorize_url_encodes_a_state_that_would_otherwise_split_the_query() -> None:
    url = githost.authorize_url(
        client_id="Iv1.test", redirect_uri="https://api/cb?x=1", state="a&b=c"
    )
    params = httpx.URL(url).params
    assert params["state"] == "a&b=c"
    assert params["redirect_uri"] == "https://api/cb?x=1"
    assert url.startswith(githost.GITHUB_AUTHORIZE_URL + "?")
