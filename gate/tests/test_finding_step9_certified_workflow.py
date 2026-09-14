"""Finding step9-certified-workflow (Mike, 2026-09-14; D-4 v3.11; F07-T17): the graph's
post-merge job records step 9 by certificate or provenance when the pinned gate says so.

F07-T17 teaches ``classify`` that a root certified at ``screened-and-signed`` or above, or inherited
from a D-10 registry with provenance recorded, satisfies step 9 without a person: ``needs_review``
is false and the classification document carries ``review_kind`` (``certificate`` | ``provenance``
| ``pr-approval`` | null) and ``review_reference``. The gate job needs nothing new for that: its
step-9 job already runs only when ``needs_review`` is true. The post-merge job does. Its "Record
what satisfied step 9" step ran only when ``needs_review`` was true, so a certified merge would
reach ``postmerge`` with an empty ``--review-kind`` and no reference, and the attestation could not
say what it relied on.

These are static reads of ``origin/main`` in the sibling graph repo (never a run of the workflow),
skipped where the graph is not checked out beside this repo: three strict xfails until the graph
carries the change, and one guard that passes today. Every new field is read with a default, so
the workflow stays inert on a pin that predates F07-T17 (F08-Q8's shape).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from opn_gate import config

ROOT = Path(__file__).resolve().parents[2]
GRAPH_REPO = ROOT.parent / "open_proof_network_graph"
GATE_WORKFLOW = ".github/workflows/gate.yml"
REASON = (
    "finding step9-certified-workflow (D-4 v3.11, F07-R16, F07-T17): the post-merge job records "
    "step 9 only when a review was asked, so a certified or registry-provenanced merge would "
    "reach postmerge with no review kind and no reference; fix: F07-T17 (Mike, 2026-09-14)"
)


def _live_workflow(path: str) -> dict[Any, Any] | None:
    if not GRAPH_REPO.is_dir():
        pytest.skip("the graph repo is not checked out beside this repo")
    env = config.child_environment(drop=config.GIT_REPO_VARIABLES)  # the hook exports GIT_DIR
    ref = subprocess.run(
        ["git", "-C", str(GRAPH_REPO), "rev-parse", "--verify", "--quiet", "origin/main"],
        capture_output=True, text=True, check=False, env=env,
    )  # fmt: skip
    if ref.returncode != 0:
        pytest.skip("the graph repo has no readable origin/main")
    proc = subprocess.run(
        ["git", "-C", str(GRAPH_REPO), "show", f"origin/main:{path}"],
        capture_output=True, text=True, check=False, env=env,
    )  # fmt: skip
    if proc.returncode != 0:
        return None
    doc = yaml.safe_load(proc.stdout)
    assert isinstance(doc, dict), f"{path} is not a YAML mapping"
    return doc


def _postmerge() -> dict[str, Any]:
    doc = _live_workflow(GATE_WORKFLOW)
    assert doc is not None and isinstance(doc.get("jobs"), dict), "gate.yml has no jobs"
    job = doc["jobs"].get("postmerge")
    assert isinstance(job, dict), "gate.yml has no postmerge job"
    return job


def _step(
    job: dict[str, Any], *, name: str | None = None, runs: str | None = None
) -> dict[str, Any]:
    for step in job.get("steps") or []:
        if not isinstance(step, dict):
            continue
        if name is not None and str(step.get("name", "")).startswith(name):
            return step
        if runs is not None and runs in str(step.get("run", "")):
            return step
    raise AssertionError(f"no step named {name!r} / running {runs!r}")


def test_postmerge_classify_exports_the_review_kind_and_reference_with_defaults() -> None:
    """The classify step's output loop names both new fields with a default, so an old pin that
    publishes neither leaves them empty and changes nothing."""
    classify = _step(_postmerge(), runs="opn_gate.cli classify")
    run = str(classify.get("run", ""))
    assert '("review_kind", None)' in run, run
    assert '("review_reference", None)' in run, run


def test_the_step_9_record_runs_for_every_building_merge() -> None:
    """A certified merge asks no review, so the record step cannot be guarded by ``needs_review``:
    it runs whenever the merge builds, and a certificate or provenance kind needs no approval."""
    review = _step(_postmerge(), name="Record what satisfied step 9")
    guard = str(review.get("if", ""))
    assert "needs_gate == 'true'" in guard, guard
    # A merge that asked a review (a curator record) still runs it, so a bypass fails here (C7);
    # what must not be true is that ``needs_review`` alone guards it.
    assert guard.strip() != "steps.classify.outputs.needs_review == 'true'", guard
    env = review.get("env") or {}
    assert "steps.classify.outputs.review_kind" in str(env.get("REVIEW_KIND", "")), sorted(env)
    assert "steps.classify.outputs.review_reference" in str(env.get("REVIEW_REFERENCE", "")), (
        sorted(env)
    )
    run = str(review.get("run", ""))
    for kind in ("certificate", "provenance"):
        assert kind in run, f"the record step never selects {kind}"
    assert "reference=" in run and "GITHUB_OUTPUT" in run, "the step publishes no reference"


def test_the_re_derive_step_hands_the_reference_to_postmerge() -> None:
    """The attestation names the certificate or provenance it relied on (D-4): ``postmerge`` gets
    ``--review-reference`` whenever the record step published one."""
    derive = _step(_postmerge(), name="Re-derive the verdict")
    text = json.dumps(derive)
    assert "--review-reference" in text, text[:400]
    assert "steps.review.outputs.reference" in text, text[:400]


def test_approval_bodies_are_still_read_when_no_review_is_asked() -> None:
    """A guard, not a finding: it passes today and must keep passing through F07-T17. F02-R9: a
    waived proof is attested only if an approving review names the waiver. A certified root asks no
    review, so the record step still reads the reviews and writes their bodies — a reviewer can
    approve with ``waiver: native_decide`` even where nobody had to."""
    review = _step(_postmerge(), name="Record what satisfied step 9")
    run = str(review.get("run", ""))
    assert "pulls/${NUMBER}/reviews" in run, "the record step no longer reads the reviews"
    assert "approvals" in run, "the approval bodies are no longer written"
