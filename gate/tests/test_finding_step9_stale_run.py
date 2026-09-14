"""Finding step9-stale-run (the 2026-09-13 Euclid tester): step 9 is evaluated before the build,
and a review submitted later cannot turn the red check green.

The graph's ``gate.yml`` runs on ``pull_request_review`` as well as ``pull_request``, so an
approving review starts a *new* run of the whole gate job; the red run for the same head stays
on the pull request, and the ruleset reads the stale one. F07-T8 splits step 9 into a job of its
own (``test_pins.py::test_step_9_is_its_own_job_after_the_sandbox_build`` pins that half, and is
not repeated here) and adds ``step9-refresh.yml``, a workflow holding only ``actions: write``
that re-runs the step-9 job of the existing run in place — no checkout, no gate code, so it is
inert on any pin. The same commit makes the post-merge job hand every merge its body and author
(so the attestation can record the submission, F07-T14) and write the ledger for every merge
(F07-T15), and the ruleset requires both job names.

Static reads of ``origin/main`` in the sibling graph repo (never a run of the workflows), skipped
where the graph is not checked out beside this repo; a missing ``step9-refresh.yml`` is a
failure, not a skip. One ``network`` test reads the ruleset through ``gh``, read-only.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from opn_gate import config

ROOT = Path(__file__).resolve().parents[2]
GRAPH_REPO = ROOT.parent / "open_proof_network_graph"
GRAPH_SLUG = "thisisanameforsure/open_proof_network_graph"
GATE_WORKFLOW = ".github/workflows/gate.yml"
REFRESH_WORKFLOW = ".github/workflows/step9-refresh.yml"
#: The name F07-T8 gives the step-9 job; the ruleset matches a check by this exact string.
STEP9_JOB_NAME = "step 9 (a non-author approving review)"
ACTIONS_APP_ID = 15368  # GitHub Actions' integration id, the source every required check names

REASON = (
    "finding step9-stale-run (D-4 step order, F07-R16, C8, F07-Q16): step 9 runs inside the gate "
    "job and an approving review starts a new run instead of refreshing the red one, so a "
    "reviewed submission stays blocked; fix: F07-T8 (Mike, 2026-09-14)"
)


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(GRAPH_REPO), *args],
        capture_output=True,
        text=True,
        check=False,
        env=config.child_environment(drop=config.GIT_REPO_VARIABLES),  # the hook exports GIT_DIR
    )


def _live_workflow(path: str) -> dict[Any, Any] | None:
    """The workflow at ``origin/main:<path>`` in the graph repo, or ``None`` when that ref has no
    such file. Skips only when the graph repo or its ``origin/main`` is not there to read."""
    if not GRAPH_REPO.is_dir():
        pytest.skip("the graph repo is not checked out beside this repo")
    if _git("rev-parse", "--verify", "--quiet", "origin/main").returncode != 0:
        pytest.skip("the graph repo has no readable origin/main")
    proc = _git("show", f"origin/main:{path}")
    if proc.returncode != 0:
        return None
    doc = yaml.safe_load(proc.stdout)
    assert isinstance(doc, dict), f"{path} is not a YAML mapping"
    return doc


def _gate_workflow() -> dict[Any, Any]:
    doc = _live_workflow(GATE_WORKFLOW)
    assert doc is not None, f"origin/main:{GATE_WORKFLOW} does not exist"
    assert isinstance(doc.get("jobs"), dict), "gate.yml has no jobs"
    return doc


def _refresh_workflow() -> dict[Any, Any]:
    doc = _live_workflow(REFRESH_WORKFLOW)
    assert doc is not None, (
        f"origin/main:{REFRESH_WORKFLOW} does not exist: nothing re-runs step 9 when a review "
        "is submitted or dismissed"
    )
    return doc


def _triggers(doc: dict[Any, Any]) -> Any:
    """``on:`` — which ``yaml.safe_load`` reads as the boolean key ``True``."""
    return doc.get("on", doc.get(True))


def _steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    steps = job.get("steps") or []
    assert isinstance(steps, list)
    return [s for s in steps if isinstance(s, dict)]


def _step_named(job: dict[str, Any], prefix: str) -> tuple[int, dict[str, Any]]:
    for index, step in enumerate(_steps(job)):
        if str(step.get("name", "")).lower().startswith(prefix.lower()):
            return index, step
    names = [s.get("name") for s in _steps(job)]
    raise AssertionError(f"no step named {prefix!r}…: {names}")


def _step_running(job: dict[str, Any], needle: str) -> tuple[int, dict[str, Any]]:
    for index, step in enumerate(_steps(job)):
        if needle in str(step.get("run", "")):
            return index, step
    raise AssertionError(f"no step runs {needle!r}")


def _step9_job(jobs: dict[str, Any]) -> dict[str, Any] | None:
    for job in jobs.values():
        if isinstance(job, dict) and str(job.get("name", "")).lower().startswith("step 9"):
            return job
    return None


# --- gate.yml -----------------------------------------------------------------------------------


@pytest.mark.xfail(strict=True, reason=REASON)
def test_the_gate_workflow_is_not_started_by_a_review() -> None:
    """A review re-runs step 9 in place (step9-refresh.yml); it never starts the gate again, so
    the workflow triggers on ``pull_request`` and ``push`` only and the gate job runs for a pull
    request event alone."""
    doc = _gate_workflow()
    on = _triggers(doc)
    assert isinstance(on, dict), on
    assert set(on) == {"pull_request", "push"}, sorted(on)
    gate_if = str(doc["jobs"]["gate"].get("if", ""))
    assert "pull_request_review" not in gate_if, gate_if


@pytest.mark.xfail(strict=True, reason=REASON)
def test_the_step_9_job_reads_eligible_reviewers_from_the_gate_jobs_output() -> None:
    """The step-9 job has no checkout, so ``classification.json`` is not there to read: the gate
    job exports ``reviewers`` (with ``needs_review`` and ``tutorial``) and step 9 reads it from
    ``needs.gate.outputs``."""
    jobs = _gate_workflow()["jobs"]
    outputs = jobs["gate"].get("outputs") or {}
    assert {"needs_review", "tutorial", "reviewers"} <= set(outputs), sorted(outputs)
    review = _step9_job(jobs)
    assert review is not None, "no job named 'step 9 …' in the graph's gate.yml"
    text = json.dumps(review)
    assert "needs.gate.outputs.reviewers" in text, "step 9 does not read the gate's reviewers"
    assert "classification.json" not in text, "step 9 reads a file its job never checked out"


@pytest.mark.xfail(strict=True, reason=REASON)
def test_the_gate_step_hands_the_author_to_the_pinned_gate() -> None:
    """F07-T14 records the submitter; a hand-opened pull request has no body block, so ``Run the
    gate`` passes the author the way classify already does (``OPN_PR_AUTHOR``, no new flag)."""
    jobs = _gate_workflow()["jobs"]
    _, build = _step_named(jobs["gate"], "Run the gate")
    env = build.get("env") or {}
    assert "OPN_PR_AUTHOR" in env, sorted(env)
    assert "pull_request.user.login" in str(env["OPN_PR_AUTHOR"]), env["OPN_PR_AUTHOR"]


# --- the post-merge job -------------------------------------------------------------------------


@pytest.mark.xfail(strict=True, reason=REASON)
def test_postmerge_fetches_the_body_for_every_mode() -> None:
    """Every attested merge records its submission block (F07-T14), so the body is fetched
    whatever the mode — not only for a partial."""
    postmerge = _gate_workflow()["jobs"]["postmerge"]
    _, fetch = _step_running(postmerge, "pr-body.md")
    assert "gh api" in str(fetch.get("run", "")), fetch.get("name")
    guard = str(fetch.get("if", ""))
    assert "mode" not in guard and "partial" not in guard, guard


@pytest.mark.xfail(strict=True, reason=REASON)
def test_postmerge_passes_the_body_and_the_author_unconditionally() -> None:
    """The re-derive step's ``postmerge`` command carries ``--pr-body-file`` and ``--author`` on
    its own command line, not inside the partial-only array (the pinned commit already accepts
    both flags on ``postmerge``)."""
    postmerge = _gate_workflow()["jobs"]["postmerge"]
    _, derive = _step_named(postmerge, "Re-derive the verdict")
    run = str(derive.get("run", ""))
    at = run.find("opn_gate.cli postmerge")
    assert at >= 0, "the re-derive step does not run postmerge"
    command: list[str] = []
    for line in run[at:].splitlines():
        command.append(line)
        if not line.rstrip().endswith("\\"):
            break
    invocation = "\n".join(command)
    assert "--pr-body-file" in invocation, invocation
    assert re.search(r"--author\b", invocation), invocation


@pytest.mark.xfail(strict=True, reason=REASON)
def test_postmerge_writes_the_ledger_for_every_merge_after_signing() -> None:
    """F07-T15: the ledger credits every merge it should, so its step runs whenever the merge
    touched a target — not only for a proposal — and after the attestation is signed (it reads
    the attestation's tooling), before the bot commit."""
    postmerge = _gate_workflow()["jobs"]["postmerge"]
    ledger_at, ledger = _step_running(postmerge, "opn_gate.cli ledger")
    guard = str(ledger.get("if", ""))
    assert "run == 'true'" in guard, guard
    assert "proposal" not in guard and "mode" not in guard, guard
    sign_at, _ = _step_named(postmerge, "Sign")
    commit_at, _ = _step_named(postmerge, "Commit")
    assert sign_at < ledger_at < commit_at, (sign_at, ledger_at, commit_at)


# --- step9-refresh.yml --------------------------------------------------------------------------


@pytest.mark.xfail(strict=True, reason=REASON)
def test_the_refresh_workflow_runs_on_a_review_and_holds_one_job() -> None:
    doc = _refresh_workflow()
    on = _triggers(doc)
    assert isinstance(on, dict) and set(on) == {"pull_request_review"}, on
    types = (on["pull_request_review"] or {}).get("types")
    assert isinstance(types, list) and set(types) == {"submitted", "dismissed"}, types
    assert doc.get("permissions") == {}, doc.get("permissions")
    jobs = doc.get("jobs")
    assert isinstance(jobs, dict) and len(jobs) == 1, jobs


@pytest.mark.xfail(strict=True, reason=REASON)
def test_the_refresh_workflow_holds_nothing_but_the_rerun_permission() -> None:
    """C8: the one new door is ``actions: write``; no action is used (no checkout), no secret is
    named, so nothing a contributor wrote is ever on the runner."""
    doc = _refresh_workflow()
    (job,) = doc["jobs"].values()
    assert job.get("permissions") == {"actions": "write", "pull-requests": "read"}, job.get(
        "permissions"
    )
    assert all("uses" not in step for step in _steps(job)), [s.get("uses") for s in _steps(job)]
    assert "secrets." not in json.dumps(doc)


@pytest.mark.xfail(strict=True, reason=REASON)
def test_the_refresh_workflow_reruns_the_step_9_job_of_the_existing_gate_run() -> None:
    """It finds the pull request's gate run and re-runs that run's step-9 job in place, and runs
    no gate code at all — so it works the same on any pinned network commit."""
    doc = _refresh_workflow()
    (job,) = doc["jobs"].values()
    text = "\n".join(str(step.get("run", "")) for step in _steps(job))
    assert "gh run list" in text, text
    assert re.search(r"(--workflow[= ]|-w )['\"]?gate\.yml", text), text
    assert re.search(r"(--event[= ]|-e )['\"]?pull_request\b", text), text
    assert re.search(r"gh run rerun\b[^\n]*--job", text), text
    assert "uv run" not in text and "opn_gate" not in text, text


# --- the ruleset (network) ----------------------------------------------------------------------


def _gh(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=False, timeout=60)


@pytest.mark.network
@pytest.mark.xfail(strict=True, reason=REASON)
def test_the_ruleset_requires_the_gate_and_the_step_9_job() -> None:
    """The main ruleset requires both job names, exactly, from GitHub Actions, up to date — a
    check matched by a stale name never reports and blocks every merge (the log, 2026-09-10).
    Read-only: ``gh api`` GETs only."""
    if shutil.which("gh") is None:
        pytest.skip("gh is not installed")
    if _gh("auth", "status").returncode != 0:
        pytest.skip("gh is not authenticated")
    jobs = _gate_workflow()["jobs"]
    review = _step9_job(jobs)
    expected = {
        str(jobs["gate"]["name"]),
        str(review["name"]) if review is not None else STEP9_JOB_NAME,
    }
    listed = _gh("api", f"repos/{GRAPH_SLUG}/rulesets")
    assert listed.returncode == 0, listed.stderr[:300]
    found: list[dict[str, Any]] = []
    for summary in json.loads(listed.stdout):
        detail = _gh("api", f"repos/{GRAPH_SLUG}/rulesets/{summary['id']}")
        assert detail.returncode == 0, detail.stderr[:300]
        ruleset = json.loads(detail.stdout)
        includes = ((ruleset.get("conditions") or {}).get("ref_name") or {}).get("include") or []
        if ruleset.get("target") != "branch" or "refs/heads/main" not in includes:
            continue
        found += [
            rule["parameters"]
            for rule in ruleset.get("rules", [])
            if rule.get("type") == "required_status_checks"
        ]
    assert len(found) == 1, f"expected one required-status-checks rule on main, found {found}"
    (parameters,) = found
    checks = parameters.get("required_status_checks") or []
    assert {c["context"] for c in checks} == expected, checks
    assert len(checks) == len(expected), checks
    assert all(c.get("integration_id") == ACTIONS_APP_ID for c in checks), checks
    assert parameters.get("strict_required_status_checks_policy") is True, parameters
