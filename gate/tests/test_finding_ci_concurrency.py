"""The network's CI cancels a superseded run on a pull request branch (testers 2026-09-29, item 2).

Every push to a network branch runs the hour-long Lean tier, and 27 pushes from one pull request
held the account's whole hosted-runner pool: the graph's gate sat ``queued`` for 16 to 24 minutes
at the head of the merge queue, prechecks likewise, and no merge happened for 42 minutes. A run on
a commit that a later push has already replaced checks nothing anyone will merge, so the workflow
carries a concurrency group per ref that cancels the older run on a pull request; a push to
``main`` is never cancelled, because every commit on main is one the record pins.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def load() -> dict[Any, Any]:
    loaded: dict[Any, Any] = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return loaded


def test_runs_on_one_ref_share_a_concurrency_group() -> None:
    doc = load()
    group = str(doc["concurrency"]["group"])
    assert "github.ref" in group, group
    assert "github.workflow" in group or group.startswith("ci"), group


def test_a_superseded_pull_request_run_is_cancelled_and_a_main_run_is_not() -> None:
    cancel = str(load()["concurrency"]["cancel-in-progress"])
    assert "pull_request" in cancel and "github.event_name" in cancel, cancel
