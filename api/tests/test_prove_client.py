"""F17-T5 / AC6, AC7, AC9: ``opn-prove`` end to end against the real service on a loopback port.

The graph is the walkthrough's propositional clone, the host finishes every precheck at once with
a signed pass (``AutoRunGitHost``), and the prover is a stub command that answers the way the
common open-weight provers do: a proof plan, then a fenced ``lean4`` block. The chain is the one
the guide gives a contributor: export, run, import, check, submit. What the host recorded is the
assertion: one pull request whose ``Proof.lean`` is the node's real proof, declared as produced by
``opn-prove/command`` (D-23), which the gate never reads (F16-R12).
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from api_fakes import PrecheckKey, alice, make_harness, make_precheck_key
from test_prove_export import GRAPHS, prove
from test_walkthrough import AutoRunGitHost, build_graph_repo, serve_in_thread, tree_files

from opn_gate import schemas

TUTORIAL = "tutorial-and-swap"
TARGET = "propositional"
PROOF = (
    GRAPHS / "propositional" / "targets" / TARGET / "nodes" / TUTORIAL / "Proof.lean"
).read_text()

STUB = """
import pathlib, sys
problem, answer = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
text = problem.read_text(encoding="utf-8")
filled = text.replace("  sorry\\n", "  intro p q h\\n  exact ⟨h.2, h.1⟩\\n")
plan = "### Proof plan\\nSwap the pair.\\n\\n"
answer.write_text(plan + "```lean4\\n" + filled + "```\\n", encoding="utf-8")
"""


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


@pytest.fixture
def world(tmp_path: Path, key: PrecheckKey) -> Iterator[dict[str, Any]]:
    graph = build_graph_repo(tmp_path, key)
    host = AutoRunGitHost(tree_files(graph), key)
    host.users = {"code_alice": alice()}
    harness = make_harness(githost=host)
    token = harness.token_for("code_alice", "alice")
    base, loop = serve_in_thread(harness.app)
    yield {"graph": graph, "host": host, "api": base, "token": token, "harness": harness}
    loop.call_soon_threadsafe(loop.stop)


def cli(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, dict[str, Any]]:
    code = prove.main(list(argv))
    out = capsys.readouterr().out
    return code, json.loads(out) if out.strip().startswith("{") else {"text": out}


def test_round_trip(
    world: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    graph, api = str(world["graph"]), world["api"]
    problem, answer, proof = tmp_path / "problem.lean", tmp_path / "answer.txt", tmp_path / "P.lean"
    stub = tmp_path / "stub.py"
    stub.write_text(STUB, encoding="utf-8")
    node = ["--graph", graph, "--node", TUTORIAL, "--target", TARGET]

    code, out = cli(capsys, "export", *node, "--out", str(problem))
    assert code == 0 and out["ok"], out
    code, run = cli(
        capsys, "run", "--problem", str(problem), "--answer", str(answer),
        "--record", str(tmp_path / "run.json"), "--", sys.executable, str(stub),
        "{problem}", "{answer}",
    )  # fmt: skip
    assert code == 0 and run["answered"] and run["exit"] == 0, run
    code, imported = cli(capsys, "import", *node, str(answer), "--out", str(proof))
    assert code == 0 and imported["kind"] == "proof", imported
    assert proof.read_text(encoding="utf-8") == PROOF

    code, checked = cli(capsys, "check", "--api", api, *node, str(proof))
    assert checked["status"] == 200 and checked["authoritative"] is False, checked

    monkeypatch.setenv("OPN_TOKEN", world["token"])
    monkeypatch.setenv("OPN_PROVE_POLL_S", "0.05")
    code, submitted = cli(capsys, "submit", "--api", api, *node, str(proof), "--model", "stub-1")
    assert code == 0 and submitted["stage"] == "submission", submitted
    pushed = [
        p for p in world["host"].pushes
        if f"targets/{TARGET}/nodes/{TUTORIAL}/Proof.lean" in p.files and "job.json" not in p.files
    ]  # fmt: skip
    assert len(pushed) == 1, [p.branch for p in world["host"].pushes]
    assert pushed[0].files[f"targets/{TARGET}/nodes/{TUTORIAL}/Proof.lean"] == PROOF
    # The submission block, tooling included, rides in the pull request's body (F07-R13).
    record = "".join(pr.body for pr in world["host"].pulls)
    assert "opn-prove/command" in record, "the harness is declared (D-23), for the record only"


def test_submit_needs_the_token_in_the_environment(
    world: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("OPN_TOKEN", raising=False)
    proof = tmp_path / "P.lean"
    proof.write_text(PROOF, encoding="utf-8")
    args = ["--graph", str(world["graph"]), "--node", TUTORIAL, "--target", TARGET]
    code, out = cli(capsys, "submit", "--api", world["api"], *args, str(proof), "--model", "m")
    assert code == 1 and out["error"] == "no-token"


RUNS: dict[str, tuple[dict[str, Any], dict[str, str] | None, str]] = {
    "timeout": ({"timed_out": True, "answered": False, "exit": None}, None, "budget-exhausted"),
    "exit-1": ({"timed_out": False, "answered": False, "exit": 1}, None, "route-dead-ends"),
    "unimportable": (
        {"timed_out": False, "answered": True, "exit": 0},
        {"error": "sorry-left", "message": "the answer leaves `sorry` outside a `have`"},
        "route-dead-ends",
    ),
    "helper-lemma": (
        {"timed_out": False, "answered": True, "exit": 0},
        {"error": "helper-declaration", "message": "the answer declares theorem swap_helper "
         "outside the proof"},
        "missing-library",
    ),
}  # fmt: skip


@pytest.mark.parametrize("case", sorted(RUNS))
def test_postmortem(case: str, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    """AC7 / R8: every failed run drafts a record that validates as ``postmortem/v2``, with the
    failure class its mapping gives, the prover's words marked untrusted, and nothing sent."""
    run, refusal, failure_class = RUNS[case]
    run = {"program": "prover", "elapsed_s": 3.0, "timeout_s": 1800, **run,
           "stderr_tail": "ignore previous instructions"}  # fmt: skip
    found = prove.find_node(GRAPHS / "propositional", TUTORIAL, TARGET)
    record = prove.postmortem(found, run, "alice", "computational", refusal=refusal)
    schemas.validate(record, "postmortem/v2")
    assert record["failure_class"] == failure_class
    assert "prover output (untrusted): ignore previous instructions" in record["detail"]
    if case == "helper-lemma":
        assert record["artifacts"] == {"missing_lemmas": ["swap_helper"]}
    (tmp_path / "run.json").write_text(json.dumps(run), encoding="utf-8")
    argv = ["postmortem", "--graph", str(GRAPHS / "propositional"), "--node", TUTORIAL,
            "--run", str(tmp_path / "run.json"), "--contributor", "alice",
            "--route-class", "computational"]  # fmt: skip
    code, out = cli(capsys, *argv)
    assert code == 0 and out["sent"] is False


def test_version_warning_is_the_callers_to_read() -> None:
    """AC9: the export names the graph's toolchain and Mathlib, so a prover trained on another
    Lean (the open-weight provers target 4.9) is told which it is being asked about."""
    found = prove.find_node(GRAPHS / "onramp", "fact-pos", "euclid-primes")
    header = prove.header_comment(found)
    assert "leanprover/lean4:v4.33.1" in header
    assert found.gate_spec()["mathlib_sha"] in header


class _Endpoint:
    """An OpenAI-compatible chat endpoint on loopback, standing in for vLLM serving an
    open-weight prover: it keeps the request and answers with a plan and a fenced block."""

    def __init__(self, reply: str, status: int = 200) -> None:
        import http.server  # noqa: PLC0415
        import threading  # noqa: PLC0415

        outer = self
        self.requests: list[dict[str, Any]] = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                outer.requests.append(
                    {"path": self.path, "body": json.loads(self.rfile.read(length))}
                )
                payload = json.dumps({"choices": [{"message": {"content": reply}}]}).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *_a: Any) -> None:
                return

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/v1"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()


def test_whole_file_preset(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """F17-T8, Q2: the shared open-weight prompt reaches the endpoint word for word with the
    exported file inside it, and the model's answer imports as the node's real proof."""
    graph = GRAPHS / "propositional"
    found = prove.find_node(graph, TUTORIAL, TARGET)
    problem, answer = tmp_path / "problem.lean", tmp_path / "answer.txt"
    problem.write_text(prove.export(found), encoding="utf-8")
    filled = prove.export(found).replace("  sorry\n", "  intro p q h\n  exact ⟨h.2, h.1⟩\n")
    endpoint = _Endpoint("### Detailed Proof Plan\n\nSwap.\n\n```lean4\n" + filled + "```\n")
    try:
        code, run = cli(
            capsys, "run", "--preset", "whole-file", "--endpoint", endpoint.url,
            "--model", "Goedel-LM/Goedel-Prover-V2-8B", "--problem", str(problem),
            "--answer", str(answer), "--record", str(tmp_path / "run.json"),
        )  # fmt: skip
    finally:
        endpoint.close()
    assert code == 0 and run["answered"] and run["backend"] == "whole-file", run
    (request,) = endpoint.requests
    assert request["path"] == "/v1/chat/completions"
    sent = request["body"]["messages"][0]["content"]
    assert sent == prove.WHOLE_FILE_PROMPT.format(problem=prove.export(found))
    assert sent.startswith("Complete the following Lean 4 code:\n\n```lean4\n")
    imported = prove.import_answer(found, answer.read_text(encoding="utf-8"))
    assert imported.kind == "proof" and imported.text == PROOF


def test_whole_file_warns_about_the_lean_version(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC9 / R10: a preset trained on Lean 4.9 against a graph pinned at 4.33.1 is told so,
    naming both, and the run goes ahead."""
    found = prove.find_node(GRAPHS / "onramp", "fact-pos", "euclid-primes")
    warning = prove.version_warning(found, prove.WHOLE_FILE_LEAN)
    assert warning is not None and "v4.9" in warning and "v4.33.1" in warning
    problem, answer = tmp_path / "problem.lean", tmp_path / "answer.txt"
    problem.write_text(prove.export(found), encoding="utf-8")
    endpoint = _Endpoint("no proof today")
    try:
        code = prove.main([
            "run", "--preset", "whole-file", "--endpoint", endpoint.url, "--model", "m",
            "--graph", str(GRAPHS / "onramp"), "--node", "fact-pos", "--problem", str(problem),
            "--answer", str(answer), "--record", str(tmp_path / "run.json"),
        ])  # fmt: skip
    finally:
        endpoint.close()
    err = capsys.readouterr().err
    assert code == 0 and "warning: this prover targets Lean v4.9" in err and "v4.33.1" in err
    assert prove.version_warning(found, "v4.33.1") is None


def test_whole_file_unreachable_endpoint_is_a_failed_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A dead endpoint is a run with no answer, which drafts as a postmortem, never a crash."""
    problem, answer = tmp_path / "problem.lean", tmp_path / "answer.txt"
    problem.write_text("theorem t : True := by\n  sorry\n", encoding="utf-8")
    code, run = cli(
        capsys, "run", "--preset", "whole-file", "--endpoint", "http://127.0.0.1:9/v1",
        "--model", "m", "--problem", str(problem), "--answer", str(answer),
        "--record", str(tmp_path / "run.json"), "--timeout", "5",
    )  # fmt: skip
    assert code == 1 and run["answered"] is False and run["exit"] == 1, run
    found = prove.find_node(GRAPHS / "propositional", TUTORIAL, TARGET)
    record = prove.postmortem(found, run, "alice", "computational")
    schemas.validate(record, "postmortem/v2")
    assert record["outcome"] == "abandoned-early"


# --- the aristotle preset (F17-R11, AC11; Q6 ruled 2026-10-12) ---------------------------------


class _Version:
    """Aristotle's ``GET /version`` on loopback: ``{"lean_toolchain_version": ...}``, the one
    read the SDK makes before a submission (``local_file_utils.get_expected_toolchain``)."""

    def __init__(self, toolchain: str) -> None:
        import http.server  # noqa: PLC0415
        import threading  # noqa: PLC0415

        outer = self
        self.requests: list[dict[str, Any]] = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                outer.requests.append({"path": self.path, "key": self.headers.get("X-API-Key")})
                payload = json.dumps({"lean_toolchain_version": toolchain}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *_a: Any) -> None:
                return

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/api/v3"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()


def test_aristotle_preset_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC11, R11: the preset writes the Lake project, reads the service's toolchain, submits
    through the CLI with the project directory and a wait, and the archive's Problem.lean is the
    answer, which imports as the node's real proof."""
    graph = GRAPHS / "propositional"
    found = prove.find_node(graph, TUTORIAL, TARGET)
    filled = prove.export(found).replace("  sorry\n", "  intro p q h\n  exact ⟨h.2, h.1⟩\n")
    calls = fake_aristotle_service(
        tmp_path, monkeypatch, filled=filled, statuses=["IN_PROGRESS", "COMPLETE"]
    )
    version = _Version("leanprover/lean4:v4.28.0")
    monkeypatch.setenv("OPN_ARISTOTLE_API", version.url)
    answer = tmp_path / "answer.txt"
    try:
        code = prove.main([
            "run", "--preset", "aristotle", "--graph", str(graph), "--node", TUTORIAL,
            "--problem", str(tmp_path / "problem.lean"), "--answer", str(answer),
            "--record", str(tmp_path / "run.json"), "--timeout", "30",
        ])  # fmt: skip
    finally:
        version.close()
    captured = capsys.readouterr()
    run = json.loads(captured.out)
    assert code == 0 and run["answered"] and run["backend"] == "aristotle", run
    assert run["service_toolchain"] == "leanprover/lean4:v4.28.0"
    assert run["pinned_toolchain"] == "leanprover/lean4:v4.33.1"
    assert run["task_status"] == "COMPLETE"
    (req,) = version.requests
    assert req["path"] == "/api/v3/version" and req["key"] == "arstl_test"
    argv = aristotle_calls(calls)[0]
    # F17-T10: submitted without --wait, then polled and downloaded; no connection held open
    assert argv[0] == "submit" and "--wait" not in argv and "--project-dir" in argv
    assert [a[0] for a in aristotle_calls(calls)[1:]] == ["tasks", "tasks", "download"]
    assert "sorry" in argv[1] and "statement" in argv[1].lower()
    project = Path(argv[argv.index("--project-dir") + 1])
    assert (project / "lean-toolchain").read_text().strip() == "leanprover/lean4:v4.33.1"
    assert (project / "Problem.lean").read_text() == prove.header_comment(found) + prove.export(
        found
    )
    assert "v4.28.0" in captured.err and "v4.33.1" in captured.err  # R10, naming both
    imported = prove.import_answer(found, answer.read_text(encoding="utf-8"))
    assert imported.kind == "proof" and imported.text == PROOF


def test_complete_with_errors_is_partial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC11, R11: an archive from a COMPLETE_WITH_ERRORS task whose remaining sorry sits in a
    have is a candidate partial, not a failure."""
    graph = GRAPHS / "propositional"
    found = prove.find_node(graph, TUTORIAL, TARGET)
    filled = prove.export(found).replace(
        "  sorry\n", "  intro p q h\n  have hq : q := by\n    sorry\n  exact ⟨hq, h.1⟩\n"
    )
    fake_aristotle_service(tmp_path, monkeypatch, filled=filled, statuses=["COMPLETE_WITH_ERRORS"])
    version = _Version("leanprover/lean4:v4.28.0")
    monkeypatch.setenv("OPN_ARISTOTLE_API", version.url)
    answer = tmp_path / "answer.txt"
    try:
        code, run = cli(
            capsys, "run", "--preset", "aristotle", "--graph", str(graph), "--node", TUTORIAL,
            "--problem", str(tmp_path / "problem.lean"), "--answer", str(answer),
            "--record", str(tmp_path / "run.json"), "--timeout", "30",
        )  # fmt: skip
    finally:
        version.close()
    assert code == 0 and run["answered"] and run["task_status"] == "COMPLETE_WITH_ERRORS", run
    imported = prove.import_answer(found, answer.read_text(encoding="utf-8"))
    assert imported.kind == "partial" and "have hq : q := by" in imported.text


def test_aristotle_cli_missing_is_a_failed_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """No CLI on PATH, or no key: a run with no answer that drafts as a postmortem, never a
    crash; the service's version is still read when it can be."""
    graph = GRAPHS / "propositional"
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    monkeypatch.delenv("ARISTOTLE_API_KEY", raising=False)
    monkeypatch.setenv("OPN_ARISTOTLE_API", "http://127.0.0.1:9/api/v3")
    code, run = cli(
        capsys, "run", "--preset", "aristotle", "--graph", str(graph), "--node", TUTORIAL,
        "--problem", str(tmp_path / "problem.lean"), "--answer", str(tmp_path / "answer.txt"),
        "--record", str(tmp_path / "run.json"), "--timeout", "5",
    )  # fmt: skip
    assert code == 1 and run["answered"] is False and run["service_toolchain"] is None, run
    assert "ARISTOTLE_API_KEY" in run["stderr_tail"] or "aristotle" in run["stderr_tail"]
    found = prove.find_node(graph, TUTORIAL, TARGET)
    record = prove.postmortem(found, run, "alice", "computational")
    schemas.validate(record, "postmortem/v2")


# --- F17-T10: the aristotle preset survives what the live runs of 2026-10-15 met ------------------
#
# The real CLI was seen to: drop its connection a minute into ``submit --wait`` while the task ran
# on (and still exit 0, leaving an archive of the unchanged project); refuse a submission with
# "too many projects in progress", exit 0; and return the problem file unchanged from a task that
# ended COMPLETE_WITH_ERRORS. Its ``tasks`` table and ``download`` archive are as below.

FAKE_PROJECT = "150e6cec-a333-4d70-b94f-486f1c4b6dfa"
ANSI = "\x1b[2J\x1b[H"


def fake_aristotle_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    filled: str,
    statuses: list[str],
    summary: str = "I filled the sorry.",
    refuse: bool = False,
    wait_drops: bool = False,
) -> Path:
    """An ``aristotle`` on PATH with the subcommands the preset may call: ``submit`` (with or
    without ``--wait``), ``tasks <id>`` (one status per call, the last repeated) and
    ``download <id> --destination`` (the project as ``project_aristotle/`` with the summary).
    Every argv is appended to ``aristotle-calls.jsonl``."""
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    state = tmp_path / "aristotle-state.json"
    state.write_text(json.dumps({"statuses": statuses}), encoding="utf-8")
    calls = tmp_path / "aristotle-calls.jsonl"
    exe = bindir / "aristotle"
    exe.write_text(
        "#!/usr/bin/env python3\n"
        "import io, json, pathlib, sys, tarfile\n"
        f"STATE = pathlib.Path({str(state)!r}); CALLS = pathlib.Path({str(calls)!r})\n"
        f"PID = {FAKE_PROJECT!r}; ANSI = {ANSI!r}\n"
        f"FILLED = {filled!r}; SUMMARY = {summary!r}\n"
        f"REFUSE = {refuse!r}; WAIT_DROPS = {wait_drops!r}\n"
        "argv = sys.argv[1:]\n"
        "with CALLS.open('a') as f: f.write(json.dumps(argv) + '\\n')\n"
        "st = json.loads(STATE.read_text())\n"
        "def archive(dest, problem, summary):\n"
        "    with tarfile.open(dest, 'w:gz') as tar:\n"
        "        files = (('Problem.lean', problem), ('ARISTOTLE_SUMMARY.md', summary))\n"
        "        for name, text in files:\n"
        "            if text is None: continue\n"
        "            data = text.encode(); info = tarfile.TarInfo('project_aristotle/' + name)\n"
        "            info.size = len(data); tar.addfile(info, io.BytesIO(data))\n"
        "cmd = argv[0]\n"
        "if cmd == 'submit':\n"
        "    print('WARNING: Your Lean toolchain version does not match Aristotle\\'s.')\n"
        "    if REFUSE:\n"
        "        print('ERROR - You have too many projects in progress. Cancel a running '\n"
        "              'task or '\n"
        "              'wait for one to complete before starting another.'); sys.exit(0)\n"
        "    project = pathlib.Path(argv[argv.index('--project-dir') + 1])\n"
        "    st['problem'] = (project / 'Problem.lean').read_text()\n"
        "    STATE.write_text(json.dumps(st))\n"
        "    print(ANSI + 'QUEUED (started 0s ago)'); print('Project created: ' + PID)\n"
        "    if '--wait' in argv:\n"
        "        if WAIT_DROPS:\n"
        "            if '--destination' in argv:\n"
        "                archive(argv[argv.index('--destination') + 1], st['problem'], None)\n"
        "            print('ERROR - Connection to server was interrupted. Use \\'aristotle show '\n"
        "                  + PID + '\\' to try again.'); sys.exit(0)\n"
        "        archive(argv[argv.index('--destination') + 1], FILLED, SUMMARY)\n"
        "        print(ANSI + st['statuses'][-1]); print('Task complete!')\n"
        "    sys.exit(0)\n"
        "if cmd == 'tasks':\n"
        "    status = st['statuses'][0]\n"
        "    if len(st['statuses']) > 1: st['statuses'].pop(0); STATE.write_text(json.dumps(st))\n"
        "    print('ID                                   CREATED     NAME            STATUS')\n"
        "    print('-' * 80)\n"
        "    print('02772399-4ffd-4f4c-b58e-e0f1a790f258 1 min ago   Fill the sorry  ' + status)\n"
        "    sys.exit(0)\n"
        "if cmd == 'download':\n"
        "    archive(argv[argv.index('--destination') + 1], FILLED, SUMMARY); sys.exit(0)\n"
        "sys.exit(2)\n",
        encoding="utf-8",
    )
    exe.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bindir}:{__import__('os').environ['PATH']}")
    monkeypatch.setenv("ARISTOTLE_API_KEY", "arstl_test")
    monkeypatch.setenv("OPN_ARISTOTLE_API", "http://127.0.0.1:9/api/v3")  # no /version: a warning
    monkeypatch.setenv("OPN_ARISTOTLE_POLL_S", "0")
    return calls


def aristotle_calls(calls: Path) -> list[list[str]]:
    if not calls.exists():
        return []
    return [json.loads(line) for line in calls.read_text().splitlines()]


def run_preset(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, *extra: str
) -> tuple[int, dict[str, Any]]:
    return cli(
        capsys, "run", "--preset", "aristotle", "--graph", str(GRAPHS / "propositional"),
        "--node", TUTORIAL, "--problem", str(tmp_path / "problem.lean"),
        "--answer", str(tmp_path / "answer.txt"), "--record", str(tmp_path / "run.json"),
        "--timeout", "30", *extra,
    )  # fmt: skip


def test_aristotle_dropped_connection_still_gets_the_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """2026-10-15: the CLI lost its connection a minute into ``submit --wait`` and the task ran on
    for 25 minutes. The preset holds no connection open: it submits, keeps the project id, polls
    ``tasks`` until a terminal status and downloads the result, so a drop costs nothing."""
    found = prove.find_node(GRAPHS / "propositional", TUTORIAL, TARGET)
    filled = prove.export(found).replace("  sorry\n", "  intro p q h\n  exact ⟨h.2, h.1⟩\n")
    calls = fake_aristotle_service(
        tmp_path, monkeypatch, filled=filled,
        statuses=["QUEUED", "IN_PROGRESS", "IN_PROGRESS", "COMPLETE"], wait_drops=True,
    )  # fmt: skip
    code, run = run_preset(capsys, tmp_path)
    assert code == 0 and run["answered"] and run["task_status"] == "COMPLETE", run
    assert run["project_id"] == FAKE_PROJECT
    assert not any("--wait" in argv for argv in aristotle_calls(calls))
    imported = prove.import_answer(found, (tmp_path / "answer.txt").read_text(encoding="utf-8"))
    assert imported.kind == "proof" and imported.text == PROOF


def test_aristotle_project_limit_is_a_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """2026-10-15: "too many projects in progress", and the CLI still exits 0. That is not a run
    that found nothing: it is a refusal to retry later, and nothing is polled or downloaded."""
    calls = fake_aristotle_service(
        tmp_path, monkeypatch, filled="", statuses=["COMPLETE"], refuse=True
    )
    code, run = run_preset(capsys, tmp_path)
    assert code == 1 and run["answered"] is False, run
    assert run.get("refused") == "project-limit", run
    assert [argv[0] for argv in aristotle_calls(calls)] == ["submit"]


def test_aristotle_unchanged_file_is_not_an_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """2026-10-15: three tasks ended COMPLETE_WITH_ERRORS with Problem.lean exactly as sent. The
    file sent back unchanged is not an answer, whatever the status."""
    found = prove.find_node(GRAPHS / "propositional", TUTORIAL, TARGET)
    unchanged = prove.header_comment(found) + prove.export(found)
    fake_aristotle_service(
        tmp_path, monkeypatch, filled=unchanged, statuses=["COMPLETE_WITH_ERRORS"]
    )
    code, run = run_preset(capsys, tmp_path)
    assert code == 1 and run["answered"] is False, run
    assert run["task_status"] == "COMPLETE_WITH_ERRORS"


def test_aristotle_resume_polls_without_submitting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A run that was interrupted, or timed out on this side, is picked up by its project id:
    ``--resume`` polls and downloads and never submits a second task."""
    found = prove.find_node(GRAPHS / "propositional", TUTORIAL, TARGET)
    filled = prove.export(found).replace("  sorry\n", "  intro p q h\n  exact ⟨h.2, h.1⟩\n")
    calls = fake_aristotle_service(
        tmp_path, monkeypatch, filled=filled, statuses=["IN_PROGRESS", "COMPLETE"]
    )
    code, run = run_preset(capsys, tmp_path, "--resume", FAKE_PROJECT)
    assert "submit" not in [argv[0] for argv in aristotle_calls(calls)]
    assert code == 0 and run["answered"] and run.get("project_id") == FAKE_PROJECT, run
    assert aristotle_calls(calls)[-1][:2] == ["download", FAKE_PROJECT]


def test_aristotle_summary_reaches_the_postmortem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The archive's ARISTOTLE_SUMMARY.md is the prover's account of what it tried; the draft
    postmortem quotes it rather than the last 2000 characters of a progress display, and no
    terminal escape reaches the record."""
    found = prove.find_node(GRAPHS / "propositional", TUTORIAL, TARGET)
    unchanged = prove.header_comment(found) + prove.export(found)
    summary = "I could not fill the sorry. The case split only rules out p = 2 and p = 3."
    fake_aristotle_service(
        tmp_path, monkeypatch, filled=unchanged, statuses=["COMPLETE_WITH_ERRORS"],
        summary=summary,
    )  # fmt: skip
    _, run = run_preset(capsys, tmp_path)
    record = prove.postmortem(found, run, "alice", "case-split")
    schemas.validate(record, "postmortem/v2")
    assert summary in record["detail"] and "\x1b" not in record["detail"], record["detail"]
    assert Path(run["summary"]).read_text(encoding="utf-8") == summary, run


def test_import_partial_with_a_multiline_have(tmp_path: Path) -> None:
    """2026-10-15: Aristotle's partial on erdos-1094--h2--h2--h2--h3--h1--h1 states its one hole
    over fifteen lines, so the line above the sorry is the hole's type, not ``have``. The sorry
    is still the whole body of a have, which is what a partial is (D-12)."""
    found = prove.find_node(GRAPHS / "propositional", TUTORIAL, TARGET)
    body = (
        "  intro p q h\n"
        "  have hq :\n"
        "      q ∧\n"
        "        True := by\n"
        "    sorry\n"
        "  exact ⟨hq.1, h.1⟩\n"
    )
    answer = prove.export(found).replace("  sorry\n", body)
    imported = prove.import_answer(found, answer)
    assert imported.kind == "partial"
    assert "have hq :\n      q ∧\n        True := by" in imported.text
