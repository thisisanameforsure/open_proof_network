#!/usr/bin/env python3
"""F16-T7 / R8, R10: the connectors' real-client check, run by hand or by ``make verify-harness``.

    uv run python gate/tools/harness_check.py [--bin-dir DIR] [--entry ID ...]
        [--auth none|bearer|both] [--out REPORT.json]

For each registry entry, the real api is served on a loopback port over the test suite's fake git
host, the entry's rendered snippet registers it in a throwaway home and project, and the entry's
connection check runs the harness binary against it. What decides the check is the server's own
record of the MCP calls that run made (``initialize``, ``tools/list``), never the harness's exit
code or its words: Claude Code skips a malformed entry and still exits 0, and ``codex mcp list``
prints a table without connecting. With ``--auth bearer`` the entry's token form is registered
with a fresh random token in ``OPN_TOKEN``, and the record says whether a request carried exactly
that token, carried the variable unexpanded, or carried nothing; the token itself is never kept.

Each entry ends ``pass``, ``fail`` or ``not-attempted`` (a missing binary, a credential the check
needs, a token form no binary can exercise), always with the reason. ``not-attempted`` counts
against the verdict (R10): exit 0 only when every check passed, 1 otherwise, 2 on a usage error.

Nothing here reaches a live host: the service is the real code over an in-memory store.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Awaitable, Callable, MutableMapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
for sub in ("gate", "api", "gate/tests", "api/tests"):
    if str(ROOT / sub) not in sys.path:
        sys.path.insert(0, str(ROOT / sub))

import uvicorn  # noqa: E402 — locked as the MCP SDK's own dependency; no new package (C5)
from api_fakes import make_harness  # noqa: E402

from opn_api.clock import SystemClock  # noqa: E402
from opn_gate import clients  # noqa: E402

PASS, FAIL, NOT_ATTEMPTED = "pass", "fail", "not-attempted"
LOOPBACK = "127.0.0.1,localhost"
OUTPUT_TAIL = 1200

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGI = Callable[[Scope, Receive, Send], Awaitable[None]]


@dataclass
class Seen:
    """One HTTP request the service received: its MCP methods and what its bearer was."""

    method: str
    path: str
    status: int | None
    user_agent: str | None
    rpc: list[str]
    bearer: str  # none | expected | unexpanded | other


@dataclass
class Result:
    entry: str
    auth: str
    state: str
    reason: str
    version: str | None = None
    rpc_seen: list[str] = field(default_factory=list)
    bearer: str | None = None
    output_tail: str = ""


class Recorder:
    """ASGI middleware that keeps, per request, the JSON-RPC methods and how the bearer compared
    with the token the current check expects. It never keeps a header value (C9)."""

    def __init__(self, app: ASGI) -> None:
        self.app = app
        self.seen: list[Seen] = []
        self.expected_token: str | None = None
        self.token_env: str = "OPN_TOKEN"  # noqa: S105 — a variable's name, not a secret

    def classify(self, header: str | None) -> str:
        if not header:
            return "none"
        value = header.removeprefix("Bearer ").strip()
        if self.expected_token is not None and value == self.expected_token:
            return "expected"
        if self.token_env in value:
            return "unexpanded"
        return "other"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        body = bytearray()
        status: dict[str, int] = {}

        async def rec() -> Message:
            msg = await receive()
            if msg["type"] == "http.request":
                body.extend(msg.get("body", b""))
            return msg

        async def snd(msg: Message) -> None:
            if msg["type"] == "http.response.start":
                status["code"] = int(msg["status"])
            await send(msg)

        await self.app(scope, rec, snd)
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        try:
            doc = json.loads(bytes(body)) if body else None
        except ValueError:
            doc = None
        messages = doc if isinstance(doc, list) else [doc] if isinstance(doc, dict) else []
        self.seen.append(
            Seen(
                method=scope["method"],
                path=scope["path"],
                status=status.get("code"),
                user_agent=headers.get("user-agent"),
                rpc=[str(m.get("method")) for m in messages if isinstance(m, dict)],
                bearer=self.classify(headers.get("authorization")),
            )
        )


@dataclass
class Served:
    url: str
    recorder: Recorder
    server: uvicorn.Server

    def stop(self) -> None:
        self.server.should_exit = True


def serve() -> Served:
    """The real api over the fake host and a memory store, on a free loopback port."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    harness = make_harness(clock=SystemClock(), env={"OPN_API_PUBLIC_URL": url})
    recorder = Recorder(harness.app)
    config = uvicorn.Config(recorder, host="127.0.0.1", port=port, log_level="warning")
    config.lifespan = "off"  # the MCP mount serves a request with no lifespan running (F09-Q3)
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True, name="opn-harness-api").start()
    deadline = time.monotonic() + 30
    while not server.started:
        if time.monotonic() > deadline:
            msg = "the local api did not start within 30 s"
            raise RuntimeError(msg)
        time.sleep(0.05)
    return Served(url, recorder, server)


def program(command: str) -> str | None:
    """The executable a shell command runs: its first word after any ``NAME=value`` prefix."""
    for word in shlex.split(command):
        if "=" not in word.split("/")[0]:
            return word
    return None


def _environment(
    home: Path, bin_dir: Path | None, entry: clients.Entry, token: str | None
) -> dict[str, str]:
    path = os.pathsep.join(p for p in (str(bin_dir) if bin_dir else "", os.environ["PATH"]) if p)
    env = {
        "HOME": str(home),
        "PATH": path,
        "NO_PROXY": LOOPBACK,
        "no_proxy": LOOPBACK,
        "LANG": "C.UTF-8",
        **{
            k: os.environ[k]
            for k in ("HTTPS_PROXY", "HTTP_PROXY", "SSL_CERT_FILE")
            if k in os.environ
        },
        **{k: os.environ[k] for k in entry.list_requires_env if k in os.environ},
        **entry.list_env,
    }
    if token is not None:
        env["OPN_TOKEN"] = token
    return env


def _register(snippet: clients.Rendered, home: Path, project: Path, env: dict[str, str]) -> str:
    """Put one rendered snippet where its harness looks, as a contributor would; the command's
    output is returned for the report."""
    if snippet.kind == "command":
        # S602: a snippet is a shell command a contributor pastes; running it through a shell is
        # the thing under test, and its text comes from the validated registry, never the network.
        done = subprocess.run(  # noqa: S602
            snippet.text,
            shell=True,
            cwd=project,
            env=env,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=60,
            check=False,
        )
        if done.returncode != 0:
            msg = f"registration exited {done.returncode}: {(done.stdout + done.stderr)[-400:]}"
            raise RuntimeError(msg)
        return done.stdout + done.stderr
    assert snippet.path is not None
    target = home / snippet.path[2:] if snippet.path.startswith("~/") else project / snippet.path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(snippet.text, encoding="utf-8")
    return f"wrote {snippet.path}"


def _version(binary: str, env: dict[str, str]) -> str | None:
    try:
        done = subprocess.run(
            [binary, "--version"],
            env=env,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    lines = [line for line in (done.stdout + done.stderr).splitlines() if line.strip()]
    return lines[0].strip() if lines else None


def check(  # noqa: PLR0911 — one return per outcome, each with its reason
    served: Served,
    registry: clients.Registry,
    entry: clients.Entry,
    *,
    auth: str = "none",
    bin_dir: Path | None = None,
) -> Result:
    """One entry, one token form: the level-2 check (R8)."""
    mcp_url = f"{served.url}/mcp"
    command, expect = clients.render_list_check(registry, entry, mcp_url)
    binary = program(command)
    search = os.pathsep.join(p for p in (str(bin_dir) if bin_dir else "", os.environ["PATH"]) if p)
    if binary is None or shutil.which(binary, path=search) is None:
        return Result(entry.id, auth, NOT_ATTEMPTED, f"{binary} is not installed")
    missing = [k for k in entry.list_requires_env if not os.environ.get(k)]
    if missing:
        return Result(
            entry.id, auth, NOT_ATTEMPTED, f"needs {', '.join(missing)} in the environment"
        )
    rendered = [r for r in clients.render(registry, entry, mcp_url) if r.auth == auth]
    registration = next((r for r in rendered if r.kind == "command"), None) or next(
        (r for r in rendered if r.kind == "file"), None
    )
    if registration is None:
        return Result(entry.id, auth, NOT_ATTEMPTED, f"no {auth} snippet")
    if auth == "bearer" and "${input:" in registration.text:
        return Result(entry.id, auth, NOT_ATTEMPTED, "the token form prompts in an editor")
    token = secrets.token_urlsafe(32) if auth == "bearer" else None
    with tempfile.TemporaryDirectory(prefix=f"opn-harness-{entry.id}-") as tmp:
        home = Path(tmp)
        project = home / "project"
        project.mkdir()
        env = _environment(home, bin_dir, entry, token)
        version = _version(shutil.which(binary, path=search) or binary, env)
        try:
            _register(registration, home, project, env)
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            return Result(entry.id, auth, FAIL, str(exc), version)
        served.recorder.expected_token = token
        served.recorder.token_env = registry.token_env
        start = len(served.recorder.seen)
        try:
            done = subprocess.run(  # noqa: S602 — the registry's own command, as above
                command,
                shell=True,
                cwd=project,
                env=env,
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=entry.list_timeout_s,
                check=False,
            )
            output = done.stdout + done.stderr
        except subprocess.TimeoutExpired as exc:
            output = _text(exc.stdout) + _text(exc.stderr) + "\n[timed out: the check ignores it]"
        time.sleep(0.2)  # the last request's record lands after its response
        seen = served.recorder.seen[start:]
        served.recorder.expected_token = None
    mcp_calls = [m for s in seen if s.path.rstrip("/").endswith("/mcp") for m in s.rpc]
    tail = output[-OUTPUT_TAIL:]
    missing_rpc = [m for m in entry.list_rpc if m not in mcp_calls]
    if missing_rpc:
        reason = f"the server saw no {', '.join(missing_rpc)} from this run"
        return Result(entry.id, auth, FAIL, reason, version, mcp_calls, None, tail)
    if expect is not None and expect not in output:
        reason = f"the output does not contain {expect!r}"
        return Result(entry.id, auth, FAIL, reason, version, mcp_calls, None, tail)
    bearer = None
    if auth == "bearer":
        kinds = {s.bearer for s in seen if s.path.rstrip("/").endswith("/mcp")}
        bearer = (
            "expected"
            if "expected" in kinds
            else "unexpanded"
            if "unexpanded" in kinds
            else ("other" if "other" in kinds else "none")
        )
        if bearer != "expected":
            reason = f"the MCP requests carried {bearer} bearer, not the token in OPN_TOKEN"
            return Result(entry.id, auth, FAIL, reason, version, mcp_calls, bearer, tail)
    return Result(entry.id, auth, PASS, "the server saw " + ", ".join(entry.list_rpc), version,
                  mcp_calls, bearer, tail)  # fmt: skip


def _text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return value.decode("utf-8", "replace") if isinstance(value, bytes) else value


def verdict(results: Sequence[Result]) -> bool:
    """R10: every check passed; a not-attempted check is not a pass."""
    return bool(results) and all(r.state == PASS for r in results)


def regressions(pinned: Sequence[dict[str, Any]], latest: Sequence[dict[str, Any]]) -> list[str]:
    """R11: every check the pinned harness passes and the latest release does not, naming the
    entry, the token form and both versions. Nothing is written; the caller only reports."""
    before = {(r["entry"], r["auth"]): r for r in pinned}
    out = []
    for r in latest:
        old = before.get((r["entry"], r["auth"]))
        if old is not None and old["state"] == PASS and r["state"] != PASS:
            out.append(
                f"{r['entry']} ({r['auth']}): passes at {old['version']}, {r['state']} at "
                f"{r['version'] or 'an unknown version'}: {r['reason']}"
            )
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="harness_check")
    parser.add_argument("--bin-dir", type=Path, help="where the harness binaries are, first")
    parser.add_argument("--entry", action="append", default=[], help="an entry id (repeatable)")
    parser.add_argument("--auth", choices=("none", "bearer", "both"), default="both")
    parser.add_argument("--out", type=Path, help="write the JSON report here")
    parser.add_argument(
        "--compare",
        nargs=2,
        type=Path,
        metavar=("PINNED", "LATEST"),
        help="R11: compare two reports and exit 1 on any regression; runs nothing",
    )
    args = parser.parse_args(argv)
    if args.compare:
        pinned, latest = (
            json.loads(p.read_text(encoding="utf-8"))["results"] for p in args.compare
        )
        found = regressions(pinned, latest)
        for line in found:
            print(f"regression: {line}")
        print(f"{len(found)} regression(s)")
        return 1 if found else 0
    registry = clients.load()
    known = {e.id for e in registry.entries}
    unknown = [e for e in args.entry if e not in known]
    if unknown:
        print(f"unknown entries: {unknown}; known: {sorted(known)}", file=sys.stderr)
        return 2
    forms = ("none", "bearer") if args.auth == "both" else (args.auth,)
    bin_dir = args.bin_dir.resolve() if args.bin_dir else None  # each check runs elsewhere
    served = serve()
    results: list[Result] = []
    try:
        for entry in registry.entries:
            if args.entry and entry.id not in args.entry:
                continue
            for form in forms:
                result = check(served, registry, entry, auth=form, bin_dir=bin_dir)
                results.append(result)
                print(f"{result.state:14} {entry.id:12} {form:6} {result.version or '-':30} "
                      f"{result.reason}")  # fmt: skip
    finally:
        served.stop()
    ok = verdict(results)
    print(f"verdict: {'pass' if ok else 'not pass'} ({sum(r.state == PASS for r in results)} of "
          f"{len(results)} checks passed)")  # fmt: skip
    if args.out:
        doc = {"schema": "harness-check/v1", "results": [asdict(r) for r in results], "pass": ok}
        args.out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
