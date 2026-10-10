"""F08-T41 (D-12 v3.36): the lemmas backfill workflow holds no authority and runs Lean only in
the sandbox — the footprint backfill's shape (F18-T7).

Asserted where it is enforced, in the YAML (engineering/CLAUDE.md, 2026-09-09): read-only
permissions and no secret anywhere (C8), started by hand only, every partial re-extracted with a
pulled image and never a built one (C9, D-4 step 3), and the edges leaving as an artifact rather
than as a push (D-35): META.yaml is path-forbidden to every submission, so the commit is the
curator's.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from opn_gate.lemma_backfill import Report

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "lemmas-backfill.yml"


def doc() -> dict[Any, Any]:
    loaded = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def runs(d: dict[Any, Any]) -> str:
    jobs = d["jobs"]
    assert isinstance(jobs, dict)
    return "\n".join(str(step.get("run", "")) for job in jobs.values() for step in job["steps"])


def test_it_is_started_by_hand_only() -> None:
    triggers = doc()[True]  # PyYAML reads the key `on` as the boolean True
    assert isinstance(triggers, dict) and set(triggers) == {"workflow_dispatch"}


def test_it_reads_and_names_no_secret() -> None:
    d = doc()
    assert d["permissions"] == {"contents": "read"}
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "secrets." not in text and "GITHUB_TOKEN" not in text


def test_lean_runs_only_in_a_pulled_image() -> None:
    script = runs(doc())
    assert "opn_gate.cli lemmas-backfill" in script
    assert "--image" in script and "--no-build" in script
    assert "docker build" not in script
    assert "docker pull" in script


def test_nothing_is_pushed_the_edges_are_an_artifact() -> None:
    d = doc()
    script = runs(d)
    assert "git push" not in script and "git commit" not in script
    jobs = d["jobs"]
    assert isinstance(jobs, dict)
    uses = [str(s.get("uses", "")) for job in jobs.values() for s in job["steps"]]
    assert any(u.startswith("actions/upload-artifact@") for u in uses)


def test_the_summary_reads_the_commands_own_report_keys() -> None:
    """The row is built from ``Report.as_dict``'s keys, never guessed (2026-09-16)."""
    keys = set(Report().as_dict())
    script = runs(doc())
    assert {"written", "unchanged", "failed"} <= keys
    for key in ("written", "unchanged", "failed"):
        assert f'd.get("{key}")' in script
