"""F26-T8 / R13: the post-merge job runs the review job after any merge that adds a review record.

R13: "The post-merge job shall run it after any merge that adds a review record." The job's
command (``opn-gate review run``, F26-T5) is another task's, so the post-merge side calls it
through one seam, ``postmerge.run_review_job(graph_root, target_id, runner)``, whose default runner
shells out to it and which these tests drive with a fake.

And the 2026-09-17 lesson: one node's defect never decides whether the graph has products. A
review job that fails — or a pinned gate with no ``review run`` subcommand at all, which is every
pin until T5 lands — is a warning in the post-merge log, and the products still render.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path

import pytest
import yaml
from harness import TARGET, copy_graph
from test_review_state import A, Review

from opn_gate import cli, postmerge
from opn_gate.paths import REVIEW_DIR, Change

OTHER = "euclid-primes"


class Graph:
    """A git checkout of the fixture graph, seeded as one commit."""

    def __init__(self, tmp_path: Path) -> None:
        self.root = copy_graph(tmp_path, publish=True)
        self.env = {
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@x",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@x",
            "GIT_COMMITTER_DATE": "2026-10-12T10:00:00+00:00",
            "PATH": "/usr/bin:/bin",
            "HOME": str(tmp_path),
        }
        self.git("init", "-q")
        self.commit("seed")

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=True,
            env=self.env,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def commit(self, message: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message)

    @property
    def target(self) -> Path:
        return self.root / "targets" / TARGET


class FakeRunner:
    """Records every call; answers ``code`` (or raises ``error``)."""

    def __init__(self, code: int = 0, error: Exception | None = None) -> None:
        self.calls: list[tuple[Path, str]] = []
        self.code = code
        self.error = error

    def __call__(self, graph_root: Path, target_id: str) -> int:
        self.calls.append((graph_root, target_id))
        if self.error is not None:
            raise self.error
        return self.code


def merge_a_candidate(g: Graph) -> None:
    """A merge that adds a review with one candidate: review.yaml, the candidate's YAML and its
    Lean — three review records on one target."""
    r = Review(g.target, role="curator", identity="curator")
    r.candidate(A, "model-runner")
    (g.target / REVIEW_DIR / "candidates" / f"{A}.lean").write_text("theorem t : True := trivial\n")
    g.commit("Merge pull request #500 from x/review-candidate")


# --- which merges call the job ---------------------------------------------------------------


def test_a_merge_adding_a_candidate_runs_the_job_once_for_its_target(tmp_path: Path) -> None:
    """Three review files on one target are one call, for that target, on the checkout."""
    g = Graph(tmp_path)
    merge_a_candidate(g)
    runner = FakeRunner()
    ran = postmerge.review_after_merge(g.root, "HEAD~1", "HEAD", runner=runner)
    assert runner.calls == [(g.root, TARGET)]
    assert ran == {TARGET: True}


def test_a_merge_with_no_review_path_does_not_run_the_job(tmp_path: Path) -> None:
    """A proof, an append or anything else outside ``review/`` asks nothing of the job."""
    g = Graph(tmp_path)
    note = g.target / "approaches" / "2026-10-12-note.yaml"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text("note: nothing to do with the review\n")
    g.commit("Merge pull request #501 from x/approach")
    runner = FakeRunner()
    assert postmerge.review_after_merge(g.root, "HEAD~1", "HEAD", runner=runner) == {}
    assert runner.calls == []


def test_review_targets_reads_the_review_roles_of_each_target_once() -> None:
    """Only paths ``paths.locate`` gives a review role count, each target once, deletions none."""
    changes = [
        Change("A", f"targets/{TARGET}/review/review.yaml"),
        Change("A", f"targets/{TARGET}/review/candidates/{A}.yaml"),
        Change("A", f"targets/{TARGET}/review/candidates/{A}.lean"),
        Change("A", f"targets/{OTHER}/review/signatures/independent-2026-10-12-1.yaml"),
        Change("A", f"targets/{OTHER}/nodes/infinitude-of-primes/Proof.lean"),
        Change("A", f"targets/{TARGET}/review/stray/notes.txt"),  # no role: not a review record
        Change("D", "targets/third/review/questions/q-11111111.yaml"),
    ]
    assert postmerge.review_targets(changes) == [OTHER, TARGET]


# --- failing soft: the products render whatever the job does ------------------------------------


@pytest.mark.parametrize(
    "runner",
    [
        pytest.param(FakeRunner(code=2), id="exit-2"),
        pytest.param(FakeRunner(error=FileNotFoundError("opn-gate")), id="not-found"),
    ],
)
def test_a_failing_job_warns_and_the_products_render(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    runner: FakeRunner,
) -> None:
    g = Graph(tmp_path)
    merge_a_candidate(g)
    with caplog.at_level(logging.WARNING, logger="opn_gate.postmerge"):
        ran = postmerge.review_after_merge(g.root, "HEAD~1", "HEAD", runner=runner)
    assert ran == {TARGET: False}
    assert any(
        TARGET in r.getMessage() and "products render" in r.getMessage() for r in caplog.records
    ), [r.getMessage() for r in caplog.records]
    capsys.readouterr()
    assert cli.main(["products", "--graph", str(g.root)]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True


def test_the_pinned_gate_without_review_run_fails_soft(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The default runner, for real, against a gate that has no such subcommand: written when
    this branch's gate lacked ``review run`` (T5 adds it); restated at the wave merge to name a
    command no gate has, which is what an older pinned gate looks like to the post-merge job. The
    command exits non-zero, the job is skipped with a warning, and the products render."""
    monkeypatch.setattr(postmerge, "REVIEW_JOB_COMMAND", ("review", "no-such-step"))
    g = Graph(tmp_path)
    merge_a_candidate(g)
    with caplog.at_level(logging.WARNING, logger="opn_gate.postmerge"):
        ran = postmerge.review_after_merge(g.root, "HEAD~1", "HEAD")
    assert ran == {TARGET: False}
    assert any("products render" in r.getMessage() for r in caplog.records)
    capsys.readouterr()
    assert cli.main(["products", "--graph", str(g.root)]) == 0


def test_the_entry_point_exits_zero_and_says_what_ran(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``python -m opn_gate.postmerge review-job`` is what the post-merge job calls: one JSON line
    naming each target and whether its job ran clean, exit 0 even when one did not."""
    g = Graph(tmp_path)
    merge_a_candidate(g)
    argv = ["review-job", "--graph", str(g.root), "--base", "HEAD~1", "--head", "HEAD"]
    assert postmerge.main(argv, runner=FakeRunner(code=1)) == 0
    assert json.loads(capsys.readouterr().out) == {"review_jobs": {TARGET: False}}
    assert postmerge.main(argv, runner=FakeRunner()) == 0
    assert json.loads(capsys.readouterr().out) == {"review_jobs": {TARGET: True}}


def test_a_bad_range_is_a_warning_not_a_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    """A diff that cannot be read (an unknown base) runs no job and still exits 0."""
    g = Graph(tmp_path)
    runner = FakeRunner()
    argv = ["review-job", "--graph", str(g.root), "--base", "0" * 40, "--head", "HEAD"]
    with caplog.at_level(logging.WARNING, logger="opn_gate.postmerge"):
        assert postmerge.main(argv, runner=runner) == 0
    assert runner.calls == []
    assert json.loads(capsys.readouterr().out) == {"review_jobs": {}}
    assert caplog.records


# --- review.yml: the graph's workflow, kept here as F26-T8's evidence (D-35) ---------------------

REPO = Path(__file__).resolve().parents[2]
REVIEW_YML = REPO / "engineering" / "evidence" / "F26" / "review.yml"
NETWORK_WORKFLOWS = REPO / ".github" / "workflows"
PINNED = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}\s+#\s*\S+$")
USES = re.compile(r"^\s*(?:-\s+)?uses:\s*(.+?)\s*$")


def uses_in(text: str) -> list[str]:
    return [m.group(1) for line in text.splitlines() if (m := USES.match(line))]


def test_review_yml_runs_only_on_dispatch_and_schedule() -> None:
    """R13: "on dispatch and nightly". No pull_request or push trigger: nothing a contributor
    sends starts a job holding the deploy key."""
    doc = yaml.safe_load(REVIEW_YML.read_text(encoding="utf-8"))
    triggers = doc.get("on", doc.get(True))  # YAML 1.1 reads a bare `on` as true
    assert set(triggers) == {"workflow_dispatch", "schedule"}, triggers
    assert len(triggers["schedule"]) == 1 and "cron" in triggers["schedule"][0]
    assert doc["permissions"] == {}


def test_review_yml_pins_every_action_as_the_network_does() -> None:
    """Every ``uses:`` is a full commit with its tag (the F04-T29 scan's rule), and each action is
    pinned to the commit the network's own workflows use for it."""
    used = uses_in(REVIEW_YML.read_text(encoding="utf-8"))
    assert used, "guard: the scan found no uses lines"
    assert all(PINNED.match(u) for u in used), used
    network: dict[str, set[str]] = {}
    for path in sorted(NETWORK_WORKFLOWS.glob("*.y*ml")):
        for u in uses_in(path.read_text(encoding="utf-8")):
            action, _, rest = u.partition("@")
            network.setdefault(action, set()).add(rest.split("#")[0].strip())
    for u in used:
        action, _, rest = u.partition("@")
        assert network.get(action) == {rest.split("#")[0].strip()}, (u, network.get(action))


def test_review_yml_names_the_deploy_key_in_the_push_step_only() -> None:
    """C8: no step before the push sees a secret, and the job it runs is ``review run``."""
    doc = yaml.safe_load(REVIEW_YML.read_text(encoding="utf-8"))
    steps = doc["jobs"]["review"]["steps"]
    with_secret = [s.get("name", s.get("uses")) for s in steps if "secrets." in str(s)]
    assert len(with_secret) == 1 and "push" in with_secret[0], with_secret
    assert steps[-1]["env"]["OPN_GRAPH_DEPLOY_KEY"] == "${{ secrets.OPN_GRAPH_DEPLOY_KEY }}"
    assert "review run" in str(steps)


# --- the job runs in the sandbox (F26-T14, 2026-10-14) ---------------------------------------
# The first live dispatch (graph run 38496615231) found the review open and failed at once:
# "opn-gate: elan not found on PATH". Neither caller passed --sandbox, and no runner installs
# Lean outside the step-3 image: contributor Lean runs only in the sandbox (C9).


def test_the_default_runner_runs_the_job_in_the_sandbox_and_names_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        seen.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setenv("GITHUB_RUN_ID", "38496615231")
    assert postmerge.default_review_runner(tmp_path, "tutorial") == 0
    (argv,) = seen
    assert "--sandbox" in argv
    assert argv[argv.index("--run") + 1] == "38496615231"


def test_the_default_runner_says_local_outside_a_workflow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        seen.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
    postmerge.default_review_runner(tmp_path, "tutorial")
    assert seen[0][seen[0].index("--run") + 1] == "local"


def test_review_yml_runs_the_job_in_the_sandbox_and_names_the_run() -> None:
    doc = yaml.safe_load(REVIEW_YML.read_text(encoding="utf-8"))
    runs = [
        str(step.get("run", ""))
        for job in doc["jobs"].values()
        for step in job["steps"]
        if "opn_gate.cli review run" in str(step.get("run", ""))
    ]
    assert len(runs) == 1
    command = " ".join(runs[0].replace("\\\n", " ").split())
    assert "--sandbox" in command
    assert '--run "$GITHUB_RUN_ID"' in command
