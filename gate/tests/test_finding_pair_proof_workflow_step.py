"""F26-T26 (Q27): the graph's gate job judges a pair-proof record's Lean before the pull request
can merge.

F26-T17 taught ``classify`` to ask for it (``needs_pair_proof``) and ``opn-gate pair-proofs`` to
do it, and its own comment names the hazard: "a pin that knows it and a workflow that does not
would merge the record unjudged, so the workflow's step lands first". F26-T20 put the step on graph
branch ``f26-t20-pair-proof-step`` (1d2c09a3b9), inert on the pin of the day, and the branch was
never pushed; the guide half reached ``main`` through a later re-pin's copy and the step did not.
Found 2026-11-01 while clearing worktrees: every target pins network cc2e782e, which emits the
flag, and graph ``main``'s gate job does not read it, so a pair-proof pull request would merge
with its Lean unjudged (the review job's settled rule, F26-T21, still makes it settle nothing).

Static reads of ``origin/main`` in the sibling graph repo, never a run of the workflow, skipped
where the graph is not checked out beside this repo. The flag is read with a default, so the step
stays inert on a pin that predates it (F08-Q8's shape).
"""

from __future__ import annotations

import subprocess
from typing import Any

import pytest
import yaml
from harness import GRAPH_CHECKOUT

from opn_gate import config

GATE_WORKFLOW = ".github/workflows/gate.yml"
FLAG = "steps.classify.outputs.needs_pair_proof"


def _live_gate_workflow() -> dict[Any, Any]:
    if not GRAPH_CHECKOUT.is_dir():
        pytest.skip("the graph repo is not checked out beside this repo")
    env = config.child_environment(drop=config.GIT_REPO_VARIABLES)  # the hook exports GIT_DIR
    proc = subprocess.run(
        ["git", "-C", str(GRAPH_CHECKOUT), "show", f"origin/main:{GATE_WORKFLOW}"],
        capture_output=True, text=True, check=False, env=env,
    )  # fmt: skip
    if proc.returncode != 0:
        pytest.skip("the graph repo has no readable origin/main")
    doc = yaml.safe_load(proc.stdout)
    assert isinstance(doc, dict), f"{GATE_WORKFLOW} is not a YAML mapping"
    return doc


def _steps() -> list[dict[str, Any]]:
    """The gate job's steps: the job that keeps the verdict. The post-merge job classifies too,
    under the same step id."""
    jobs = _live_gate_workflow()["jobs"].values()
    (gate,) = [
        job["steps"]
        for job in jobs
        if any(s.get("name") == "Keep the verdict and attestation" for s in job.get("steps", []))
    ]
    return list(gate)


def _classify_step() -> dict[str, Any]:
    (step,) = [s for s in _steps() if s.get("id") == "classify"]
    return step


def test_the_classify_step_reads_the_flag_with_a_default() -> None:
    assert '("needs_pair_proof", False)' in _classify_step()["run"]


def test_a_sandboxed_step_judges_the_pair_proof_when_asked() -> None:
    judged = [s for s in _steps() if s.get("if", "").strip() == f"{FLAG} == 'true'"]
    assert len(judged) == 1, "no step of the gate job runs on needs_pair_proof"
    (step,) = judged
    run = step["run"]
    assert "opn_gate.cli pair-proofs" in run
    assert "--sandbox" in run and '--base "$BASE"' in run and "--head HEAD" in run
    assert "secrets." not in yaml.safe_dump(step), "the judging step holds no secret (C8)"


def test_the_verdict_is_kept_when_a_pair_proof_was_judged() -> None:
    (keep,) = [s for s in _steps() if s.get("name") == "Keep the verdict and attestation"]
    assert FLAG in keep["if"]
    assert "pair-proofs/pair-proofs.json" in keep["with"]["path"]
