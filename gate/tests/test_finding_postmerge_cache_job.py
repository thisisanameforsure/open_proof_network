"""F07-T57: the post-merge job ends at its push; the olean cache is a job of its own (the owner,
2026-10-02).

Read from the record (``engineering/evidence/F07/task-55.txt``): of a post-merge job's five to
eight and a half minutes, the olean cache upload took three and a half to seven, and it ran
*before* the commit, on every merge. A merge that builds nothing (an annex, a postmortem, a
proposal) waited four to seven minutes for an upload of oleans it had not changed; its record
landed about a minute after its merge only once the upload was out of the way.

Now the job that records a merge ends at its push (and its two dispatches); the upload is a job of
its own that needs it, runs only for a merge that built something and passed (``needs_gate``: a
proof or a partial), checks out exactly that merge commit, and alone holds the OIDC grant the
upload role needs (C8, least privilege). A merge that builds nothing publishes no cache: the next
fetch takes the newest cache at or before its commit (F10-R7), which holds every proved node. The
verdict is already re-derived only for the modes that build (F07-R9); that is pinned here too.
"""

from __future__ import annotations

from typing import Any

import pytest
from test_finding_merge_actor_wakes import load_gate_doc

POSTMERGE, CACHE = "postmerge", "cache"


@pytest.fixture(scope="module")
def gate_doc() -> dict[Any, Any]:
    return load_gate_doc()


def steps(gate_doc: dict[Any, Any], job: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = gate_doc["jobs"][job]["steps"]
    return found


def named(gate_doc: dict[Any, Any], job: str, prefix: str) -> dict[str, Any]:
    (step,) = [s for s in steps(gate_doc, job) if str(s.get("name", "")).startswith(prefix)]
    return step


def test_the_record_no_longer_waits_for_the_cache(gate_doc: dict[Any, Any]) -> None:
    text = str(steps(gate_doc, POSTMERGE))
    assert "cache publish" not in text and "configure-aws-credentials" not in text
    assert "id-token" not in gate_doc["jobs"][POSTMERGE]["permissions"]


def test_after_the_push_the_job_only_dispatches(gate_doc: dict[Any, Any]) -> None:
    """The site and the merge actor hear of the merge as soon as its record lands."""
    names = [str(s.get("name", "")) for s in steps(gate_doc, POSTMERGE)]
    commit = next(i for i, n in enumerate(names) if n.startswith("Commit the attestation"))
    assert [n.split(" ", 3)[:3] for n in names[commit + 1 :]] == [
        ["Ask", "the", "site"],
        ["Wake", "the", "merge"],
    ], names[commit:]


def test_the_cache_is_a_job_of_its_own_after_the_record(gate_doc: dict[Any, Any]) -> None:
    job = gate_doc["jobs"][CACHE]
    assert job["needs"] == POSTMERGE
    assert "needs.postmerge.outputs.cache == 'true'" in job["if"]
    assert "vars.OPN_CACHE_UPLOAD_ROLE_ARN != ''" in job["if"]
    assert job["permissions"] == {"contents": "read", "id-token": "write"}
    assert "secrets." not in str(job), "the upload needs no stored secret, only the role (C8)"


def test_only_a_merge_that_built_and_passed_publishes_a_cache(gate_doc: dict[Any, Any]) -> None:
    out = gate_doc["jobs"][POSTMERGE]["outputs"]["cache"]
    assert "steps.classify.outputs.needs_gate == 'true'" in out
    assert "steps.products.outputs.verdict == 'pass'" in out


def test_the_cache_job_builds_exactly_the_merge_commit_with_the_rendering_gate(
    gate_doc: dict[Any, Any],
) -> None:
    """F07-T33's split: the cache describes main, so main's pin builds it; the commit is the
    merge's, never the event's (a replay's event commit is main's head)."""
    (checkout,) = [
        s
        for s in steps(gate_doc, CACHE)
        if s.get("uses", "").startswith("actions/checkout") and "path" not in (s.get("with") or {})
    ]
    assert checkout["with"]["ref"] == "${{ needs.postmerge.outputs.merge }}"
    (render,) = [s for s in steps(gate_doc, CACHE) if (s.get("with") or {}).get("path")]
    assert render["with"]["path"] == "network-render"
    assert render["with"]["ref"] == "${{ needs.postmerge.outputs.render_pin }}"
    publish = named(gate_doc, CACHE, "Publish the olean cache")
    run = str(publish["run"])
    assert "--project network-render" in run and '--commit "$MERGE"' in run
    assert "GITHUB_SHA" not in run
    assert publish["env"]["MERGE"] == "${{ needs.postmerge.outputs.merge }}"
    assert "::warning::" in run, "a failed upload is a warning: the next run builds (C7)"
    for key in ("merge", "targets", "render_pin"):
        assert key in gate_doc["jobs"][POSTMERGE]["outputs"], key


def test_the_verdict_is_re_derived_only_for_a_merge_that_builds(gate_doc: dict[Any, Any]) -> None:
    for prefix in ("Re-derive the verdict", "Sign with the gate key"):
        assert named(gate_doc, POSTMERGE, prefix)["if"] == (
            "steps.classify.outputs.needs_gate == 'true'"
        ), prefix
