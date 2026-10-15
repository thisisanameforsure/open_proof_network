"""F28-T5 (R7, R8, R9; draft decisions v3.41, C8): the graph's closer, ``close.yml``.

Read from the graph on ``REFS`` (the F28 branch first while it is a graph branch; take it out once
it is on ``main``). Checked where each property is enforced:

* the YAML: it is woken by hand, by schedule and by the post-merge job, never by a pull request;
  the composing step holds no secret; exactly one step names the merge token;
* the push step's program, run as it stands: what it accepts from the composing step, what it
  opens and closes, the submission block it writes (the gate's own parser reads it), and a run
  against a bare remote with a scripted ``gh``, which pushes one ``close/<node>`` branch authored
  ``opn-gate``, opens one pull request, closes the one whose node a direct proof reached first,
  and opens nothing for a node that already has a closing pull request;
* ``merge.yml`` takes ``close/`` branches, and ``gate.yml``'s post-merge job wakes the closer.
"""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import textwrap
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml
from harness import GRAPH_CHECKOUT

from opn_gate import bounce, config, submission

REFS = ("f28-close", "origin/main")
SECRET = "OPN_GRAPH_MERGE_TOKEN"  # noqa: S105 — the secret's name, not a secret
OPEN_STEP = "Open the closing pull requests (the only step that sees the token)"
COMPOSE_STEP = "Compose and precheck the closing proofs"


def _env() -> dict[str, str]:
    identity = ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_AUTHOR_DATE",
                "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL", "GIT_COMMITTER_DATE")  # fmt: skip
    return config.child_environment(drop=(*config.GIT_REPO_VARIABLES, *identity))


def _show(path: str) -> str:
    if not GRAPH_CHECKOUT.is_dir():
        pytest.skip("the graph repo is not checked out beside this repo (set OPN_GRAPH_CHECKOUT)")
    for ref in REFS:
        proc = subprocess.run(
            ["git", "-C", str(GRAPH_CHECKOUT), "show", f"{ref}:{path}"],
            capture_output=True, text=True, check=False, env=_env(),
        )  # fmt: skip
        if proc.returncode == 0 and (path != ".github/workflows/close.yml" or proc.stdout):
            if path.endswith("gate.yml") and "Wake the closer" not in proc.stdout:
                continue
            if path.endswith("merge.yml") and '"close/"' not in proc.stdout:
                continue
            return proc.stdout
    pytest.fail(f"no ref of {REFS} carries the F28 version of {path}")


@pytest.fixture(scope="module")
def doc() -> dict[Any, Any]:
    loaded: dict[Any, Any] = yaml.safe_load(_show(".github/workflows/close.yml"))
    return loaded


def steps(doc: dict[Any, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = doc["jobs"]["close"]["steps"]
    return out


def step(doc: dict[Any, Any], prefix: str) -> dict[str, Any]:
    (found,) = [s for s in steps(doc) if str(s.get("name", "")).startswith(prefix)]
    return found


# --- the YAML ------------------------------------------------------------------------------------


def test_it_is_woken_by_hand_schedule_and_the_post_merge_job_never_a_pull_request(
    doc: dict[Any, Any],
) -> None:
    on = doc.get("on", doc.get(True))
    assert isinstance(on, dict)
    assert set(on) == {"workflow_dispatch", "schedule"}
    gate = yaml.safe_load(_show(".github/workflows/gate.yml"))
    names = [s.get("name") for s in gate["jobs"]["postmerge"]["steps"]]
    assert names.index("Wake the closer") == names.index("Wake the merge actor") + 1
    wake = gate["jobs"]["postmerge"]["steps"][names.index("Wake the closer")]
    assert wake["env"]["GH_TOKEN"] == "${{ github.token }}"  # noqa: S105 — an expression
    assert "gh workflow run close.yml" in wake["run"]


def test_one_step_sees_the_token_and_the_composing_step_holds_no_secret(
    doc: dict[Any, Any],
) -> None:
    text = _show(".github/workflows/close.yml")
    assert text.count("secrets.") == 1
    assert SECRET in str(step(doc, OPEN_STEP).get("env"))
    compose = step(doc, COMPOSE_STEP)
    assert "secrets." not in json.dumps(compose)
    for s in steps(doc):
        if str(s.get("uses", "")).startswith("actions/checkout@"):
            assert s["with"]["persist-credentials"] is False
    assert doc["permissions"] == {"contents": "read"}
    assert doc["jobs"]["close"]["permissions"] == {"contents": "read", "pull-requests": "read"}


def test_it_skips_what_is_open_and_is_inert_on_an_old_pin(doc: dict[Any, Any]) -> None:
    run = step(doc, COMPOSE_STEP)["run"]
    assert '--skip "$OPEN"' in run and "--no-build" in run
    assert "predates opn-gate close --target" in run
    # each proof is prechecked by the precheck job's own code, unsigned (D-4 kind none), and only
    # a pass is kept
    assert "python -m precheck.job" in run and "--key" not in run
    assert '[ "$verdict" = "pass" ]' in run and 'rm -f "$proof"' in run


def test_the_merge_actor_takes_close_branches() -> None:
    assert 'SERVICE_PREFIXES = ("propose/", "append/", "submit/", "close/")' in _show(
        ".github/workflows/merge.yml"
    )


# --- the push step's program ---------------------------------------------------------------------


@pytest.fixture(scope="module")
def helper(doc: dict[Any, Any], tmp_path_factory: pytest.TempPathFactory) -> ModuleType:
    run = step(doc, OPEN_STEP)["run"]
    body = run.split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
    path = tmp_path_factory.mktemp("close") / "close_open.py"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    spec = importlib.util.spec_from_file_location("close_open", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.__file__ = str(path)
    return module


def test_only_prechecked_target_node_files_are_proposals(
    helper: ModuleType, tmp_path: Path
) -> None:
    """A proof is proposed only beside its passing precheck attestation; a proof without one
    (its precheck failed and the step should have removed it) and any stray name are refused."""
    (tmp_path / "t").mkdir()
    (tmp_path / "t" / "n--h1.lean").write_text("x")
    (tmp_path / "t" / "n--h1.attestation.json").write_text("{}")
    (tmp_path / "t" / "unchecked.lean").write_text("x")
    (tmp_path / "t" / "deep").mkdir()
    (tmp_path / "t" / "deep" / "x.lean").write_text("x")
    (tmp_path / "stray.lean").write_text("x")
    found, bad = helper.proposals(tmp_path)
    assert [(t, n, a.name) for t, n, _, a in found] == [("t", "n--h1", "n--h1.attestation.json")]
    assert sorted(bad) == ["stray.lean", "t/deep/x.lean", "t/unchecked.lean"]


def test_the_plan_opens_new_closes_overtaken_and_never_repeats(helper: ModuleType) -> None:
    found = [
        (t, n, f"p{n}", f"a{n}") for t, n in (("t", "a"), ("t", "b"), ("t", "c"), ("t", "gone"))
    ]
    proved = {("t", "c"), ("t", "d")}
    exists = {("t", "a"), ("t", "b"), ("t", "c"), ("t", "d")}
    open_prs = {"b": (7, "t"), "d": (9, "t")}
    to_open, to_close = helper.plan(
        found, lambda t, n: (t, n) in exists, lambda t, n: (t, n) in proved, open_prs
    )
    assert [n for _, n, _, _ in to_open] == ["a"]  # b has a pull request, c is proved, gone is gone
    assert to_close == [("d", 9, "t")]  # proved directly while its closing pull request was open


def test_the_body_carries_both_blocks_the_gate_reads(helper: ModuleType) -> None:
    """The precheck block is the attestation as the precheck job wrote it, read back by the bounce
    rule's own parser; the submission block names the gate."""
    attestation = json.dumps({"schema": "attestation/v7", "signature": {"kind": "none"}})
    text = helper.body("erdos-1094", "erdos-1094--h2", "a" * 40, attestation)
    assert bounce.extract_block(text) == attestation
    block = submission.extract(text)
    assert block is not None, "the gate's parser rejected the block"
    assert block["identity"]["pseudonym"] == "opn-gate"
    assert block["artifact_type"] == "proof"
    assert submission.model_and_tooling(block) == "opn-gate close (F28)"


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True, env=_env()
    ).stdout.strip()


def test_a_run_pushes_one_branch_authored_by_the_gate_and_opens_one_pull_request(
    helper: ModuleType, tmp_path: Path
) -> None:
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True, env=_env())
    subprocess.run(["git", "init", "-q", "-b", "main", str(work)], check=True, env=_env())
    for node in ("p", "q", "r"):
        d = work / "targets" / "t" / "nodes" / node
        d.mkdir(parents=True)
        (d / "Statement.lean").write_text(f"theorem {node} : True := by\n  sorry\n")
    (work / "targets" / "t" / "nodes" / "r" / "Proof.lean").write_text(
        "theorem r : True := trivial\n"
    )
    _git(work, "add", ".")
    _git(work, "-c", "user.name=o", "-c", "user.email=o@x", "commit", "-q", "-m", "base")
    _git(work, "remote", "add", "origin", str(remote))
    _git(work, "push", "-q", "origin", "main")
    dest = tmp_path / "dest"
    (dest / "t").mkdir(parents=True)
    (dest / "t" / "p.lean").write_text("theorem p : True := (@_root_.p_h1)\n")
    (dest / "t" / "q.lean").write_text("theorem q : True := (@_root_.q_h1)\n")
    for n in ("p", "q"):
        (dest / "t" / f"{n}.attestation.json").write_text('{"verdict": "pass"}\n')
    log = tmp_path / "gh.log"
    fake = tmp_path / "bin" / "gh"
    fake.parent.mkdir()
    open_prs = [
        {
            "number": 5,
            "headRefName": "close/q",
            "files": [{"path": "targets/t/nodes/q/Proof.lean"}],
        },
        {
            "number": 6,
            "headRefName": "close/r",
            "files": [{"path": "targets/t/nodes/r/Proof.lean"}],
        },
        {"number": 8, "headRefName": "submit/x", "files": []},
    ]
    fake.write_text(
        "#!/bin/sh\n"
        f'echo "$@" >> "{log}"\n'
        'case "$1 $2" in\n'
        f"  'pr list') echo '{json.dumps(open_prs)}' ;;\n"
        "  'auth git-credential') exit 1 ;;\n"
        "esac\n"
    )
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    env = {
        **_env(),
        "PATH": f"{fake.parent}:{os.environ['PATH']}",
        "DEST": str(dest),
        "REPO": "owner/graph",
        "BASE": "b" * 40,
        "GH_TOKEN": "t",
        "REMOTE": str(remote),
        "RUNNER_TEMP": str(tmp_path),
    }
    proc = subprocess.run(
        ["python3", str(helper.__file__)],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    calls = log.read_text().splitlines()
    assert any(c.startswith("pr close 6 ") for c in calls)  # r was proved directly
    created = [c for c in calls if c.startswith("pr create")]
    assert len(created) == 1 and "--head close/p" in created[0]  # q already has #5
    body = (tmp_path / "close-p.md").read_text(encoding="utf-8")
    assert bounce.extract_block(body) == '{"verdict": "pass"}'
    assert _git(remote, "log", "-1", "--format=%an", "close/p") == "opn-gate"
    assert _git(remote, "show", "close/p:targets/t/nodes/p/Proof.lean") == (
        "theorem p : True := (@_root_.p_h1)"
    )
    changed = _git(remote, "diff", "--name-only", "main", "close/p")
    assert changed == "targets/t/nodes/p/Proof.lean"
    assert "close/q" not in _git(remote, "branch", "--list")


def test_without_the_token_it_only_says_what_it_would_open(
    helper: ModuleType, tmp_path: Path
) -> None:
    work = tmp_path / "work"
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True, env=_env())
    subprocess.run(["git", "init", "-q", "-b", "main", str(work)], check=True, env=_env())
    d = work / "targets" / "t" / "nodes" / "p"
    d.mkdir(parents=True)
    (d / "Statement.lean").write_text("theorem p : True := by\n  sorry\n")
    _git(work, "add", ".")
    _git(work, "-c", "user.name=o", "-c", "user.email=o@x", "commit", "-q", "-m", "base")
    _git(work, "remote", "add", "origin", str(remote))
    _git(work, "push", "-q", "origin", "main")
    dest = tmp_path / "dest"
    (dest / "t").mkdir(parents=True)
    (dest / "t" / "p.lean").write_text("x\n")
    (dest / "t" / "p.attestation.json").write_text("{}\n")
    env = {**_env(), "DEST": str(dest), "REPO": "owner/graph", "BASE": "b" * 40, "GH_TOKEN": ""}
    proc = subprocess.run(
        ["python3", str(helper.__file__)],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "dry run: would open a closing pull request for p" in proc.stdout
    assert "close/p" not in _git(remote, "branch", "--list")
