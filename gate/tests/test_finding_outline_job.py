"""F19-T4 (R6; Q2): the graph's ``outline`` job — after the post-merge push, in the sandbox, with no
secret during extraction, pushed with F07-T29's catch-up, and inert on an old pin.

Read from the graph's ``gate.yml`` on ``REFS`` (the F19-T4 branch first while it is a graph branch;
take it out once it is on ``main``). Three kinds of check, each where the property is enforced:

* the YAML itself (the job's place, permissions and which step sees which secret);
* the extraction step's own script, run with a ``uv`` that answers as a pinned gate would — one
  that predates ``opn-gate outline`` ends the job with a notice and extracts nothing (the
  2026-09-09 rule: a workflow may only use a command the pinned commit understands), and this
  repository's own help is the shape the step's test reads;
* the push step's helper program, run as it stands against a bare remote while ``main`` moves:
  an unrelated commit is caught up on, an outline another run already pushed is left to theirs,
  an artifact whose bytes changed has its outline dropped, a re-pin pushes nothing, and the
  extraction may add outline files and nothing else.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml
from harness import GRAPH_CHECKOUT

from opn_gate import config

GATE_DIR = Path(__file__).resolve().parents[1]
REFS = ("f19-t4-outline-job", "origin/main")
JOB = "outline"
JOB_NAME = "proof outlines for a merge that built (F19-R6), after its record is pushed"
EXTRACT = "Extract the missing outlines"
COMMIT = "Commit the outlines and push them"
PIN_A, PIN_B = "a" * 40, "b" * 40
SHA_PINNED = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")


def _env() -> dict[str, str]:
    return config.child_environment(drop=config.GIT_REPO_VARIABLES)


@pytest.fixture(scope="module")
def gate_doc() -> dict[Any, Any]:
    """The graph's gate workflow from the first ref that has an ``outline`` job. Skipped where no
    graph is checked out (CI, as every graph-reading test is); a checkout whose refs lack the job
    fails."""
    if not GRAPH_CHECKOUT.is_dir():
        pytest.skip("the graph repo is not checked out beside this repo (set OPN_GRAPH_CHECKOUT)")
    for ref in REFS:
        proc = subprocess.run(
            ["git", "-C", str(GRAPH_CHECKOUT), "show", f"{ref}:.github/workflows/gate.yml"],
            capture_output=True, text=True, check=False, env=_env(),
        )  # fmt: skip
        if proc.returncode == 0:
            loaded: dict[Any, Any] = yaml.safe_load(proc.stdout)
            if JOB in loaded.get("jobs", {}):
                return loaded
    pytest.fail(f"no outline job in gate.yml on {' or '.join(REFS)} of {GRAPH_CHECKOUT}")


def job(gate_doc: dict[Any, Any]) -> dict[str, Any]:
    found: dict[str, Any] = gate_doc["jobs"][JOB]
    return found


def named(gate_doc: dict[Any, Any], prefix: str) -> dict[str, Any]:
    steps: list[dict[str, Any]] = job(gate_doc)["steps"]
    (step,) = [s for s in steps if str(s.get("name", "")).startswith(prefix)]
    return step


# --- the YAML ------------------------------------------------------------------------------------


def test_a_job_of_its_own_after_the_record_for_a_merge_that_built(
    gate_doc: dict[Any, Any],
) -> None:
    """Q2: after the post-merge push, for the merges that add a proof artifact; nothing in the
    post-merge job waits for it or extracts anything."""
    j = job(gate_doc)
    assert j["name"] == JOB_NAME
    assert j["needs"] == "postmerge"
    assert j["if"] == "needs.postmerge.outputs.cache == 'true'"
    assert "opn_gate.cli outline" not in str(gate_doc["jobs"]["postmerge"])
    assert "outline" not in gate_doc["jobs"]["postmerge"].get("outputs", {})


def test_no_secret_until_the_push_and_no_credential_in_the_checkouts(
    gate_doc: dict[Any, Any],
) -> None:
    """C8, C9: the job is granted read only; contributor Lean runs in the extraction step, which
    sees no secret, and neither checkout keeps a token; the deploy key is the push step's alone.
    After the push only the drafter's dispatch (F20-T10) follows, holding the site dispatch token
    and nothing else; no step after the push runs contributor Lean."""
    j = job(gate_doc)
    assert j["permissions"] == {"contents": "read"}
    steps = j["steps"]
    commit_index = next(i for i, s in enumerate(steps) if str(s.get("name", "")).startswith(COMMIT))
    after = steps[commit_index + 1 :]
    assert [s.get("name") for s in after] == ["Ask the network's drafter for this merge's words"]
    assert [v for v in after[0]["env"].values() if "secrets." in v] == [
        "${{ secrets.OPN_SITE_DEPLOY_TOKEN }}"
    ]
    assert "secrets.OPN_GRAPH_DEPLOY_KEY" not in str(after[0])
    assert "opn-gate" not in after[0]["run"] and "uv run" not in after[0]["run"]
    for s in steps[:commit_index]:
        assert "secrets." not in str(s), s.get("name", s.get("uses"))
        assert "github.token" not in str(s)
    commit_env = steps[commit_index]["env"]
    assert commit_env["OPN_GRAPH_DEPLOY_KEY"] == "${{ secrets.OPN_GRAPH_DEPLOY_KEY }}"
    assert [k for k, v in commit_env.items() if "secrets." in str(v)] == ["OPN_GRAPH_DEPLOY_KEY"]
    for s in steps:
        if str(s.get("uses", "")).startswith("actions/checkout@"):
            assert s["with"]["persist-credentials"] is False, s
    assert "trap 'rm -f \"$RUNNER_TEMP/deploy_key\"' EXIT" in steps[commit_index]["run"]


def test_main_as_it_is_and_the_gate_main_pins_for_the_target(gate_doc: dict[Any, Any]) -> None:
    j = job(gate_doc)
    graph_checkout, network_checkout = (
        s for s in j["steps"] if str(s.get("uses", "")).startswith("actions/checkout@")
    )
    assert graph_checkout["with"]["ref"] == "main"
    assert network_checkout["with"]["ref"] == "${{ steps.pin.outputs.pin }}"
    assert network_checkout["with"]["path"] == "network-render"
    pin = next(s for s in j["steps"] if s.get("id") == "pin")
    assert "network_commit" in pin["run"] and "targets/$target/gate-spec.json" in pin["run"]
    run = named(gate_doc, EXTRACT)["run"]
    assert "--project network-render python -m opn_gate.cli outline" in run
    assert "--commit HEAD" in run and "--no-build" in run


def test_every_action_is_pinned_to_a_commit(gate_doc: dict[Any, Any]) -> None:
    uses = [str(s["uses"]) for s in job(gate_doc)["steps"] if "uses" in s]
    assert uses and all(SHA_PINNED.match(u) for u in uses), uses


# --- the extraction step on an old pin and a new one -------------------------------------------

FAKE_UV = r"""#!/usr/bin/env python3
import os, sys
args = sys.argv[1:]
with open(os.environ["UV_LOG"], "a", encoding="utf-8") as log:
    log.write(" ".join(args) + "\n")
if args[:1] == ["sync"]:
    sys.exit(0)
if args[-1:] == ["--help"]:
    print(open(os.environ["FAKE_HELP"], encoding="utf-8").read())
    sys.exit(0)
if "outline" in args:
    print('{"failed": [{"reason": "build-failed"}]}')
    sys.exit(int(os.environ.get("OUTLINE_EXIT", "0")))
sys.exit(2)
"""


def run_extract(
    gate_doc: dict[Any, Any], tmp_path: Path, help_text: str, outline_exit: int = 0
) -> tuple[subprocess.CompletedProcess[str], dict[str, str], list[str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    uv = bin_dir / "uv"
    uv.write_text(FAKE_UV, encoding="utf-8")
    uv.chmod(uv.stat().st_mode | stat.S_IEXEC)
    (tmp_path / "help.txt").write_text(help_text, encoding="utf-8")
    out = tmp_path / "github_output"
    out.touch()
    runner = tmp_path / "runner"
    runner.mkdir()
    env = {
        **_env(),
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "UV_LOG": str(tmp_path / "uv.log"),
        "FAKE_HELP": str(tmp_path / "help.txt"),
        "OUTLINE_EXIT": str(outline_exit),
        "GITHUB_OUTPUT": str(out),
        "RUNNER_TEMP": str(runner),
        "TARGETS": "erdos-1050",
        "PIN": PIN_A,
    }
    proc = subprocess.run(
        ["bash", "-c", named(gate_doc, EXTRACT)["run"]],
        cwd=tmp_path, env=env, capture_output=True, text=True, check=False,
    )  # fmt: skip
    outputs = dict(line.split("=", 1) for line in out.read_text().splitlines() if "=" in line)
    log = (tmp_path / "uv.log").read_text().splitlines() if (tmp_path / "uv.log").is_file() else []
    return proc, outputs, log


def own_help() -> str:
    """This repository's own top-level help: the shape the step's grep reads."""
    proc = subprocess.run(
        [sys.executable, "-m", "opn_gate.cli", "--help"],
        capture_output=True, text=True, check=True, cwd=GATE_DIR,
        env={**_env(), "PYTHONPATH": str(GATE_DIR)},
    )  # fmt: skip
    return proc.stdout


def test_a_pin_that_predates_the_command_extracts_nothing(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    old_help = own_help().replace(",outline,", ",")
    assert "outline" not in old_help.split("\n\n")[0], "guard: the old help names no outline"
    proc, outputs, log = run_extract(gate_doc, tmp_path, old_help)
    assert proc.returncode == 0, proc.stderr
    assert outputs["run"] == "false"
    assert "predates opn-gate outline" in proc.stdout
    assert not any(" outline " in f" {line} " for line in log), log


def test_a_pin_that_has_it_extracts_and_a_failure_is_a_warning(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    proc, outputs, log = run_extract(gate_doc, tmp_path, own_help(), outline_exit=1)
    assert proc.returncode == 0, proc.stderr
    assert outputs["run"] == "true"
    assert "::warning::outline: erdos-1050 has an artifact left without an outline" in proc.stdout
    [call] = [line for line in log if " outline " in f" {line} "]
    assert "--target erdos-1050" in call and "--no-build" in call


# --- the push step's helper, against a bare remote while main moves -----------------------------


def helper_source(gate_doc: dict[Any, Any]) -> str:
    run = named(gate_doc, COMMIT)["run"]
    found = re.search(r"<<'PY'\n(.*?)\nPY\n", run, re.S)
    assert found, "the push step writes its helper from a heredoc"
    return found.group(1) + "\n"


@pytest.fixture(scope="module")
def helper(gate_doc: dict[Any, Any], tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("helper") / "outline_publish.py"
    path.write_text(helper_source(gate_doc), encoding="utf-8")
    return path


def load(helper: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("outline_publish", helper)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sh(cwd: Path, *args: str) -> str:
    env = {
        **_env(),
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
    }
    return subprocess.run(
        ["git", *args], cwd=cwd, env=env, capture_output=True, text=True, check=True
    ).stdout.strip()


PROOF = b"theorem t : True := trivial\n"


def proof_hash(data: bytes = PROOF) -> str:
    import hashlib  # noqa: PLC0415

    return hashlib.sha256(data).hexdigest()


def outline_doc(target: str = "t1", data: bytes = PROOF) -> bytes:
    doc = {
        "schema": "outline/v1",
        "target": target,
        "node": "n",
        "artifact": {"path": "Proof.lean", "hash": proof_hash(data), "kind": "proof"},
        "gate": PIN_A,
        "steps": [],
    }
    return (json.dumps(doc, sort_keys=True) + "\n").encode()


def outline_path(target: str = "t1", data: bytes = PROOF) -> str:
    return f"targets/{target}/outlines/{proof_hash(data)}.json"


class Graph:
    """A bare ``main`` with one target pinned to PIN_A and one merged proof, and a clone of it as
    the job's checkout. ``advance`` writes to main as another actor would."""

    def __init__(self, tmp_path: Path) -> None:
        self.remote = tmp_path / "remote.git"
        sh(tmp_path, "init", "-q", "--bare", "-b", "main", str(self.remote))
        seed = tmp_path / "seed"
        sh(tmp_path, "clone", "-q", str(self.remote), str(seed))
        self.write(seed, "targets/t1/gate-spec.json", json.dumps({"network_commit": PIN_A}))
        self.write(seed, "targets/t1/nodes/n/Proof.lean", PROOF)
        sh(seed, "add", "-A")
        sh(seed, "commit", "-q", "-m", "gate: #1 pass")
        sh(seed, "push", "-q", "origin", "HEAD:main")
        self.other = seed
        self.work = tmp_path / "work"
        sh(tmp_path, "clone", "-q", str(self.remote), str(self.work))
        sh(self.work, "config", "user.name", "opn-gate")
        sh(self.work, "config", "user.email", "gate@openproof.network")

    @staticmethod
    def write(root: Path, rel: str, data: str | bytes) -> None:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data.encode() if isinstance(data, str) else data)

    def advance(self, rel: str, data: str | bytes, message: str = "gate: #2 pass") -> str:
        sh(self.other, "pull", "-q", "--ff-only", "origin", "main")
        self.write(self.other, rel, data)
        sh(self.other, "add", "-A")
        sh(self.other, "commit", "-q", "-m", message)
        sh(self.other, "push", "-q", "origin", "HEAD:main")
        return sh(self.other, "rev-parse", "HEAD")

    def main(self) -> str:
        return sh(self.work, "ls-remote", str(self.remote), "refs/heads/main").split()[0]

    def show(self, rev: str, rel: str) -> str:
        return sh(self.work, "--git-dir", str(self.remote), "show", f"{rev}:{rel}")

    def publish(self, helper: Path, files: list[str]) -> subprocess.CompletedProcess[str]:
        listed = self.work.parent / "outlines.txt"
        listed.write_text("\n".join(files) + "\n", encoding="utf-8")
        env = {
            **_env(),
            "REMOTE": str(self.remote),
            "LIST": str(listed),
            "PIN": PIN_A,
            "TARGETS": "t1",
        }
        return subprocess.run(
            [sys.executable, str(helper), "publish"],
            cwd=self.work, env=env, capture_output=True, text=True, check=False,
        )  # fmt: skip


def test_main_moved_by_another_commit_is_caught_up_on(helper: Path, tmp_path: Path) -> None:
    g = Graph(tmp_path)
    g.write(g.work, outline_path(), outline_doc())
    moved = g.advance("targets/t1/graph.json", "{}\n")  # the post-merge job of the next merge
    proc = g.publish(helper, [outline_path()])
    assert proc.returncode == 0, proc.stderr
    assert "outline: publish pushed" in proc.stdout and "caught up on" in proc.stdout
    tip = g.main()
    assert sh(g.work, "--git-dir", str(g.remote), "rev-parse", f"{tip}^") == moved
    assert g.show(tip, outline_path()).encode() + b"\n" == outline_doc()
    subject = sh(g.work, "--git-dir", str(g.remote), "log", "-1", "--format=%s %an", tip)
    assert subject == "outline: 1 for t1 opn-gate"
    assert not subject.startswith("gate:"), "the post-merge job credits only gate commits"


def test_an_outline_another_run_pushed_first_is_left_to_theirs(
    helper: Path, tmp_path: Path
) -> None:
    g = Graph(tmp_path)
    g.write(g.work, outline_path(), outline_doc())
    theirs = g.advance(outline_path(), outline_doc(), "outline: 1 for t1")
    proc = g.publish(helper, [outline_path()])
    assert proc.returncode == 0, proc.stderr
    assert "outline: publish nothing-left" in proc.stdout
    assert g.main() == theirs


def test_an_artifact_whose_bytes_changed_loses_its_outline(helper: Path, tmp_path: Path) -> None:
    """The record moved in a way that matters for this outline: the bytes it outlines are no
    longer the artifact at that path, so it is not laid on main."""
    g = Graph(tmp_path)
    g.write(g.work, outline_path(), outline_doc())
    moved = g.advance("targets/t1/nodes/n/Proof.lean", PROOF + b"-- revised\n")
    proc = g.publish(helper, [outline_path()])
    assert proc.returncode == 0, proc.stderr
    assert "outline: publish nothing-left" in proc.stdout
    assert g.main() == moved


def test_a_re_pin_since_extraction_pushes_nothing(helper: Path, tmp_path: Path) -> None:
    g = Graph(tmp_path)
    g.write(g.work, outline_path(), outline_doc())
    moved = g.advance("targets/t1/gate-spec.json", json.dumps({"network_commit": PIN_B}))
    proc = g.publish(helper, [outline_path()])
    assert proc.returncode == 0, proc.stderr
    assert "outline: publish pin-moved" in proc.stdout
    assert "main re-pinned t1" in proc.stdout
    assert g.main() == moved


def test_a_push_onto_main_unmoved_lands_first_time(helper: Path, tmp_path: Path) -> None:
    g = Graph(tmp_path)
    g.write(g.work, outline_path(), outline_doc())
    proc = g.publish(helper, [outline_path()])
    assert proc.returncode == 0, proc.stderr
    assert "outline: publish pushed" in proc.stdout and "caught up" not in proc.stdout


def test_the_extraction_may_add_outlines_and_nothing_else(helper: Path) -> None:
    m = load(helper)
    good = f"?? {outline_path()}"
    files, bad = m.collect({"t1"}, good + "\n", "")
    assert files == [outline_path()] and bad == []
    for line, tracked in (
        ("?? targets/t1/nodes/n/Evil.lean", ""),  # a file that is not an outline
        (f"?? {outline_path('t2')}", ""),  # an outline of a target this job did not outline
        ("?? targets/t1/outlines/notahash.json", ""),
        ("", " M targets/t1/nodes/n/Proof.lean"),  # a change to a tracked file
    ):
        files, bad = m.collect({"t1"}, f"{good}\n{line}\n", tracked)
        assert bad, (line, tracked)


def test_describes_checks_the_artifact_bytes_and_the_name(helper: Path) -> None:
    m = load(helper)
    tree = {"targets/t1/nodes/n/Proof.lean": PROOF}

    def blob(p: str) -> bytes | None:
        return tree.get(p)

    def absent(_p: str) -> bool:
        return False

    assert m.describes(outline_path(), outline_doc(), exists=absent, blob=blob)
    assert not m.describes(outline_path(), outline_doc(), exists=lambda _p: True, blob=blob)
    assert not m.describes(outline_path(), outline_doc(data=b"other"), exists=absent, blob=blob)
    assert not m.describes(outline_path(), b"not json", exists=absent, blob=blob)
    renamed = outline_path().replace("/t1/", "/t2/")
    assert not m.describes(renamed, outline_doc(), exists=absent, blob=blob)
    escaping = json.loads(outline_doc())
    escaping["artifact"]["path"] = "../../t2/nodes/n/Proof.lean"
    assert not m.describes(outline_path(), json.dumps(escaping).encode(), exists=absent, blob=blob)
