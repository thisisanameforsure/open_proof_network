"""F07-T60: the products are re-rendered after a re-pin, which merges no pull request (audit
2026-10-04).

The post-merge job renders the products only for a merged pull request. A re-pin is the owner's
direct push of ``gate-spec.json``: the job said "did not merge a pull request; nothing to record"
and stopped, so the gate changes the re-pin carried went live while every product went on
publishing the *old* gate's statuses until the next merge (the 2026-09-19 re-pin needed a second,
hand-made curator commit for exactly this; Log 2026-09-19).

Now the job dispatches the graph's ``render.yml`` when a push that merged nothing touched a
``gate-spec.json``. That workflow takes the pin main carries, renders the products with that gate,
and pushes them through the post-merge job's own publish loop (``postmerge_batch.py``, read out of
``gate.yml``), crediting nothing: ``gate: render <pin12>``. Both halves run here as the workflows
write them: the find step on a push with a fake host, and the render job's scripts against a bare
remote with the stand-in ``uv`` the catch-up tests use.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from test_finding_merge_actor_wakes import load_gate_doc
from test_finding_merge_actor_workflow import GRAPH_REPO, REFS
from test_finding_postmerge_batch import (
    PIN_A,
    PIN_B,
    REPO,
    Graph,
    git_env,
    helper_source,
    run_find_step,
)
from test_finding_postmerge_catch_up import Origin, env_for, fresh_render_agrees, git

from opn_gate import config

RENDER = ".github/workflows/render.yml"
GATE = ".github/workflows/gate.yml"


def graph_text(path: str) -> str:
    """A graph workflow's text from the first of REFS that has it. A missing render.yml fails:
    a skipped test is evidence of nothing."""
    if not GRAPH_REPO.is_dir():
        pytest.skip("the graph repo is not checked out beside this repo")
    env = config.child_environment(drop=config.GIT_REPO_VARIABLES)
    for ref in REFS:
        proc = subprocess.run(
            ["git", "-C", str(GRAPH_REPO), "show", f"{ref}:{path}"],
            capture_output=True, text=True, check=False, env=env,
        )  # fmt: skip
        if proc.returncode == 0:
            return proc.stdout
    pytest.fail(f"no {path} on {' or '.join(REFS)} of the graph")


@pytest.fixture(scope="module")
def gate_doc() -> dict[Any, Any]:
    return load_gate_doc()


@pytest.fixture(scope="module")
def render_doc() -> dict[Any, Any]:
    loaded: dict[Any, Any] = yaml.safe_load(graph_text(RENDER))
    return loaded


# --- the post-merge job dispatches a render --------------------------------------------------


def renders(calls: list[str]) -> list[str]:
    return [call for call in calls if call.startswith("workflow run render.yml")]


def test_a_direct_re_pin_dispatches_a_render(gate_doc: dict[Any, Any], tmp_path: Path) -> None:
    graph = Graph(tmp_path / "g")
    repin = json.dumps({"network_commit": PIN_B})
    graph.write("targets/t1/gate-spec.json", repin)
    graph.write("targets/t2/gate-spec.json", repin)
    sha = graph.commit("re-pin every target to the next network commit")
    code, out, said, calls = run_find_step(gate_doc, graph, tmp_path, sha, {})
    assert code == 0 and out.get("run") == "false", (out, said)
    assert renders(calls) == [f"workflow run render.yml --repo {REPO} --ref main"], (calls, said)


def test_a_direct_push_that_touches_no_pin_dispatches_nothing(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    graph = Graph(tmp_path / "g")
    graph.write("AGENTS.md", "the guide\n")
    sha = graph.commit("an owner's push of the guide")
    code, out, said, calls = run_find_step(gate_doc, graph, tmp_path, sha, {})
    assert code == 0 and out.get("run") == "false", (out, said)
    assert renders(calls) == [], calls


def test_a_merge_dispatches_no_render(gate_doc: dict[Any, Any], tmp_path: Path) -> None:
    """A merged pull request's own run renders; a re-pin merged as a pull request is recorded
    by that run, not by a second render."""
    graph = Graph(tmp_path / "g")
    sha = graph.append(2)
    code, out, said, calls = run_find_step(gate_doc, graph, tmp_path, sha, {sha: 2})
    assert code == 0 and out.get("run") == "true", (out, said)
    assert renders(calls) == [], calls


# --- the render job ------------------------------------------------------------------------------


class RenderJob:
    """One run of render.yml, from a clone of the host's main, through its scripts as written."""

    def __init__(self, render_doc: dict[Any, Any], origin: Origin, name: str) -> None:
        self.doc, self.origin = render_doc, origin
        self.work = origin.tmp / f"render-{name}"
        self.temp = origin.tmp / f"render-temp-{name}"
        self.temp.mkdir()
        (self.temp / "output").write_text("", encoding="utf-8")
        subprocess.run(
            ["git", "clone", "-q", str(origin.bare), str(self.work)], check=True, env=git_env()
        )
        self.head = git(self.work, "rev-parse", "HEAD")
        self.outputs: dict[str, str] = {}

    def step(self, name: str, **extra: str) -> subprocess.CompletedProcess[str]:
        (found,) = [
            s for s in self.doc["jobs"]["render"]["steps"]
            if str(s.get("name", "")).startswith(name)
        ]  # fmt: skip
        run = str(found["run"]).replace(
            "git@github.com:${GITHUB_REPOSITORY}.git", str(self.origin.bare)
        )
        assert "${{" not in run, f"{name}: an expression this rehearsal does not supply"
        literal = {
            key: str(value)
            for key, value in (found.get("env") or {}).items()
            if "${{" not in str(value)
        }
        (self.temp / "output").write_text("", encoding="utf-8")
        env = env_for(
            self.origin.tmp, self.temp,
            GITHUB_EVENT_NAME="workflow_dispatch", OPN_GRAPH_DEPLOY_KEY="not a key",
            OPN_API_CLAIMS_URL="", RENDER_PIN=self.outputs.get("pin", ""),
            TARGETS=self.outputs.get("targets", ""), **extra,
        )  # fmt: skip
        proc = subprocess.run(
            ["bash", "-c", run],
            capture_output=True, text=True, check=False, cwd=self.work, env={**env, **literal},
        )  # fmt: skip
        for line in (self.temp / "output").read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                self.outputs[key] = value
        return proc

    def prepare(self) -> None:
        """The steps before the push: the pin and the publish loop, then the render."""
        for name in ("Find the network commit", "Render the products"):
            proc = self.step(name)
            assert proc.returncode == 0, (name, proc.stdout, proc.stderr)

    def push(self) -> tuple[int, str]:
        proc = self.step("Commit the products")
        return proc.returncode, proc.stdout + proc.stderr


def origin_with_workflow(tmp_path: Path) -> Origin:
    """The host, whose main carries the gate workflow the render job reads its loop from."""
    origin = Origin(tmp_path)
    origin.owner({GATE: graph_text(GATE)}, "the gate workflow")
    return origin


def rendered_from(origin: Origin) -> str:
    return str(json.loads(origin.show("frontier.json"))["rendered_from"])


def credits_of(gate_doc: dict[Any, Any], subject: str) -> list[int]:
    helper: dict[str, Any] = {"__name__": "postmerge_batch"}
    exec(compile(helper_source(gate_doc), "postmerge_batch.py", "exec"), helper)  # noqa: S102
    found: list[int] = helper["credits"](subject)
    return found


def test_the_render_job_publishes_the_products_of_main_crediting_nothing(
    render_doc: dict[Any, Any], gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    origin = origin_with_workflow(tmp_path)
    job = RenderJob(render_doc, origin, "one")
    job.prepare()
    assert job.outputs["pin"] == PIN_A and job.outputs["targets"] == "t1 t2", job.outputs
    code, said = job.push()
    assert code == 0, said
    subject = origin.subjects(1)[0]
    assert subject == f"gate: render {PIN_A[:12]}", origin.subjects()
    assert credits_of(gate_doc, subject) == []
    assert git(origin.bare, "rev-parse", "main^") == job.head
    assert rendered_from(origin) == job.head
    fresh_render_agrees(origin)


def test_the_render_job_renders_again_when_main_moves_under_it(
    render_doc: dict[Any, Any], gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    """A merge and its gate commit land while the render runs: the push is refused, and the job
    renders again on main as it is rather than giving up (its loop has nothing to credit, so
    "main already credits everything" is not an answer for it)."""
    origin = origin_with_workflow(tmp_path)
    job = RenderJob(render_doc, origin, "moved")
    job.prepare()
    three = origin.append(3, "t2")
    moved = origin.bot(3, ledger=(three,))
    code, said = job.push()
    assert code == 0, said
    assert origin.subjects(2) == [f"gate: render {PIN_A[:12]}", "gate: #3 pass"], said
    assert git(origin.bare, "rev-parse", "main^") == moved
    assert rendered_from(origin) == moved, said
    fresh_render_agrees(origin)


def test_a_re_pin_under_the_render_ends_it(render_doc: dict[Any, Any], tmp_path: Path) -> None:
    """The products describe main under the gate main pins: a render made with the old pin is
    not pushed, and the re-pin's own push dispatches a render of its own."""
    origin = origin_with_workflow(tmp_path)
    job = RenderJob(render_doc, origin, "repinned")
    job.prepare()
    repin = json.dumps({"network_commit": PIN_B})
    before = origin.owner({"targets/t1/gate-spec.json": repin, "targets/t2/gate-spec.json": repin})
    code, said = job.push()
    assert code == 0, said
    assert origin.main() == before, said


def test_targets_that_disagree_on_a_pin_render_nothing(
    render_doc: dict[Any, Any], tmp_path: Path
) -> None:
    origin = origin_with_workflow(tmp_path)
    origin.owner({"targets/t2/gate-spec.json": json.dumps({"network_commit": PIN_B})})
    job = RenderJob(render_doc, origin, "split")
    proc = job.step("Find the network commit")
    assert proc.returncode != 0 and "do not agree" in proc.stdout + proc.stderr


def test_the_render_job_holds_its_secrets_in_one_step_each(render_doc: dict[Any, Any]) -> None:
    """C8, as in the post-merge job: the deploy key only where it pushes, nothing before it."""
    assert render_doc["permissions"] == {}
    job = render_doc["jobs"]["render"]
    assert job["permissions"] == {"contents": "write"}
    triggers = render_doc[True]  # YAML reads the key `on` as a boolean
    assert set(triggers) == {"workflow_dispatch"}
    named: dict[str, list[str]] = {}
    for step in job["steps"]:
        for secret in re.findall(r"secrets\.([A-Z_]+)", str(step)):
            named.setdefault(secret, []).append(str(step.get("name")))
    assert named == {
        "OPN_GRAPH_DEPLOY_KEY": [
            "Commit the products, crediting nothing, and push them (the deploy key's only step)"
        ],
        "OPN_SITE_DEPLOY_TOKEN": ["Ask the site to deploy what main now holds"],
    }
