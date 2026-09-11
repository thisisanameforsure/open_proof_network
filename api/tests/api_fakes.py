"""Fakes for the api's seams (conventions §1, §2): ``FakeGitHost`` and ``FakeClock``.

The store's fake is ``opn_api.store.MemoryStore`` itself — the local runner uses it too. The
fake host returns the structured records the seam defines; it never imitates GitHub's wire
format. It holds a fake access token only so a test can assert the string never reaches a
store or a log (AC5).

F06 adds the App-authenticated half of the seam: the fake records every branch push and
dispatch, and a test drives the polling state machine by putting a run — and, when the run
completes, an artifact — where the fake will find it.
"""

from __future__ import annotations

import io
import subprocess
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import samples  # gate/tests is on the path (pyproject [tool.pytest.ini_options])
from precheck.job import sign_service  # the signing the scratch workflow itself calls
from starlette.testclient import TestClient

from opn_api import config, identity
from opn_api.app import create_app
from opn_api.githost import Author, Fetched, GitHostError, GitHubUser, PullRequest, WorkflowRun
from opn_api.store import MemoryStore
from opn_gate import schemas

FIXTURES = Path(__file__).resolve().parent / "fixtures"
FAKE_ACCESS_TOKEN = "gho_FAKE_ACCESS_TOKEN_NEVER_STORED"  # noqa: S105 — a sentinel, not a secret
PRECHECK_KEY_PATH = "keys/precheck.pub"
# The fixture graph's tutorial node, and a proof shaped the way the gate's path check wants one.
TUTORIAL_NODE = "tutorial-and-swap"
PROOF_PREFIX = "targets/propositional/nodes/"
TUTORIAL_PROOF = "import Nodes.X.Context\n\ntheorem x : True := trivial\n"


@dataclass
class FakeClock:
    current: datetime = field(default_factory=lambda: datetime(2026, 9, 9, 12, 0, 0, tzinfo=UTC))

    def now(self) -> datetime:
        return self.current

    def advance(self, **kwargs: int) -> None:
        self.current += timedelta(**kwargs)


@dataclass
class Push:
    repo: str
    branch: str
    files: dict[str, str]
    base: str
    message: str
    author: Author | None = None
    committer: Author | None = None


@dataclass
class OpenedPr:
    repo: str
    head: str
    base: str
    title: str
    body: str


@dataclass
class Dispatch:
    repo: str
    workflow: str
    ref: str
    inputs: dict[str, str]


@dataclass
class FakeGitHost:
    users: dict[str, GitHubUser] = field(default_factory=dict)
    files: dict[str, bytes] = field(default_factory=dict)
    exchanges: list[str] = field(default_factory=list)
    fetches: list[tuple[str, str | None]] = field(default_factory=list)
    unreachable: bool = False
    access_token: str = FAKE_ACCESS_TOKEN
    # The App-authenticated half (F06-R3, R5).
    pushes: list[Push] = field(default_factory=list)
    pulls: list[OpenedPr] = field(default_factory=list)
    dispatches: list[Dispatch] = field(default_factory=list)
    runs: dict[str, WorkflowRun] = field(default_factory=dict)  # branch -> run
    artifacts: dict[tuple[int, str], bytes] = field(default_factory=dict)  # (run, name) -> zip
    app_failure: str | None = None  # when set, every App call raises it (R10, AC12)
    lookup_failure: str | None = None  # when set, only find_run raises (C7: a transient outage)
    pr_failure: str | None = None  # when set, the branch pushes and the pull request does not

    @classmethod
    def with_fixtures(cls, **users: GitHubUser) -> FakeGitHost:
        return cls(
            users=dict(users),
            files={
                "frontier.json": (FIXTURES / "frontier.json").read_bytes(),
                "info.json": (FIXTURES / "info.json").read_bytes(),
                "targets/index.json": (FIXTURES / "targets-index.json").read_bytes(),
                "targets/propositional/graph.json": (FIXTURES / "graph.json").read_bytes(),
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

    def list_dir(self, repo: str, ref: str, path: str) -> list[str] | None:
        """The files directly under ``path`` (F09-R6); ``None`` when nothing lives there.
        A ``.gitkeep`` marks an empty directory the way the graph's layout does."""
        self.fetches.append((path + "/", None))
        if self.unreachable:
            msg = f"listing {path} failed: ConnectError"
            raise GitHostError(msg)
        prefix = path.rstrip("/") + "/"
        names = sorted(
            {
                name.partition("/")[0]
                for name in (k.removeprefix(prefix) for k in self.files if k.startswith(prefix))
            }
        )
        if not names:
            return None
        return [n for n in names if prefix + n in self.files]

    def _app_call(self) -> None:
        if self.app_failure:
            raise GitHostError(self.app_failure)

    def push_branch(
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
        self._app_call()
        self.pushes.append(Push(repo, branch, dict(files), base, message, author, committer))
        return f"{len(self.pushes):040d}"

    def open_pull_request(
        self, repo: str, *, head: str, base: str, title: str, body: str
    ) -> PullRequest:
        self._app_call()
        if self.pr_failure:
            raise GitHostError(self.pr_failure)
        self.pulls.append(OpenedPr(repo, head, base, title, body))
        number = len(self.pulls)
        return PullRequest(number, f"https://github.com/{repo}/pull/{number}")

    def dispatch_workflow(
        self, repo: str, workflow: str, *, ref: str, inputs: Mapping[str, str]
    ) -> None:
        self._app_call()
        self.dispatches.append(Dispatch(repo, workflow, ref, dict(inputs)))

    def find_run(self, repo: str, workflow: str, *, branch: str) -> WorkflowRun | None:
        self._app_call()
        if self.lookup_failure:
            raise GitHostError(self.lookup_failure)
        return self.runs.get(branch)

    def download_artifact(self, repo: str, run_id: int, name: str) -> bytes | None:
        self._app_call()
        return self.artifacts.get((run_id, name))

    # --- what a test sets up ---------------------------------------------------------------------

    def start_run(self, branch: str, run_id: int = 4242) -> WorkflowRun:
        run = WorkflowRun(run_id, "in_progress", None, f"https://github.com/runs/{run_id}")
        self.runs[branch] = run
        return run

    def finish_run(
        self, branch: str, *, conclusion: str = "success", artifact: tuple[str, bytes] | None = None
    ) -> WorkflowRun:
        started = self.runs.get(branch) or self.start_run(branch)
        run = WorkflowRun(started.id, "completed", conclusion, started.url)
        self.runs[branch] = run
        if artifact is not None:
            self.artifacts[(run.id, artifact[0])] = artifact[1]
        return run


# --- a signed precheck result, as the scratch workflow would upload one --------------------------


@dataclass(frozen=True)
class PrecheckKey:
    """An ed25519 keypair standing in for C8 item 2, made the way the real one was."""

    private: Path
    public: str


def make_precheck_key(directory: Path, name: str = "precheck") -> PrecheckKey:
    key = directory / name
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", "opn-precheck-test"],
        check=True,
    )
    return PrecheckKey(key, (directory / f"{name}.pub").read_text().strip())


def result_zip(
    *,
    job_id: str,
    node_id: str,
    graph_commit: str,
    bundle_digest: str,
    key: PrecheckKey | None,
    verdict: str = "pass",
    runner: str = "hosted",
    tamper: bool = False,
) -> bytes:
    """The artifact zip the workflow uploads: one ``result.json`` whose attestation is signed by
    ``key`` as kind ``service``, through the very function the workflow calls (``precheck.sign``).

    ``key=None`` leaves it unsigned and ``tamper`` alters a field after signing, which is how the
    two refusal paths (AC7) are exercised.
    """
    doc = samples.attestation(
        node_id=node_id, graph_commit=graph_commit, runner=runner, verdict=verdict
    )
    if key is not None:
        doc = sign_service(doc, key.private)
    if tamper:
        doc = {**doc, "verdict": "fail" if verdict == "pass" else "pass"}
    result = {
        "job_id": job_id,
        "node_id": node_id,
        "bundle_digest": bundle_digest,
        "verdict": verdict,
        "first_failing_step": None,
        "steps": doc["steps"],
        "attestation": doc,
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("result.json", schemas.canonical_json(result))
    return buffer.getvalue()


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

    def commit_precheck_key(self, public_key: str) -> None:
        """Put the precheck public key where the graph commits it (C8 item 2; F06-R5)."""
        self.githost.files[PRECHECK_KEY_PATH] = public_key.encode() + b"\n"
        self.context.files.pop(PRECHECK_KEY_PATH, None)

    def tutorial_job(
        self,
        key: PrecheckKey,
        *,
        node: str = TUTORIAL_NODE,
        token: str | None = None,
        verdict: str = "pass",
    ) -> dict[str, Any]:
        """Drive a precheck of the tutorial node all the way to ``done``, and answer the created
        job document — the ``{id, nonce}`` an agent turns into a token (F06-R7).

        ``token`` makes it an authenticated job (which then has no nonce, AC11) and ``verdict``
        makes it a failing one.
        """
        self.commit_precheck_key(key.public)
        headers = self.auth(token) if token else {}
        proof = f"{PROOF_PREFIX}{node}/Proof.lean"
        created = self.client.post(
            "/precheck",
            json={"node_id": node, "bundle": {proof: TUTORIAL_PROOF}},
            headers=headers,
        )
        assert created.status_code == 202, created.text
        doc: dict[str, Any] = created.json()
        artifact = result_zip(
            job_id=doc["id"],
            node_id=node,
            graph_commit=doc["graph_commit"],
            bundle_digest=doc["bundle_digest"],
            key=key,
            verdict=verdict,
        )
        self.githost.finish_run(f"job/{doc['id']}", artifact=(f"result-{doc['id']}", artifact))
        return doc


def make_harness(env: dict[str, str] | None = None, **seams: Any) -> Harness:
    settings = config.load({**TEST_ENV, **(env or {})})
    store = seams.get("store") or MemoryStore()
    githost = seams.get("githost") or FakeGitHost.with_fixtures(code_alice=alice(), code_bob=bob())
    clock = seams.get("clock") or FakeClock()
    app = create_app(settings, store=store, githost=githost, clock=clock)
    client = TestClient(app, raise_server_exceptions=False)
    return Harness(settings, store, githost, clock, client, app)
