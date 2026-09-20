"""Finding graph-head-pin (agents D and E, 2026-09-19/20): a merged node stayed invisible to the
service for 6 to 13 minutes, and for two of those the service still refused a hole as
``witness-missing`` after the products on ``main`` said ``ready``.

The service read the graph's files from the raw host *by branch name*. That host is a CDN which
caches a branch path for minutes, on top of the service's own window, and nothing the service did
to its cache could see past it. A raw URL at a *commit sha* is immutable and so never stale: once
per window the service asks the API (no CDN) where ``main`` is, and reads every file at that
commit. Every product in one answer then comes from one commit, too (F05-T13).
"""

from __future__ import annotations

import json

from api_fakes import Harness

from opn_api import frontier

OLD, NEW = "a" * 40, "b" * 40


def age(h: Harness) -> None:
    """Move every cache entry, and the head check, past the window (relative to now)."""
    frontier.expire(h.context)


def test_files_are_read_at_the_commit_main_points_to(harness: Harness) -> None:
    harness.githost.head = OLD
    frontier.committed(harness.context, "frontier.json")
    assert harness.githost.refs[-1] == OLD
    assert set(harness.githost.refs) == {OLD}  # the marker and the file: one commit


def test_a_moved_head_is_seen_after_one_window_and_restales_everything(harness: Harness) -> None:
    harness.githost.head = OLD
    first = frontier.committed(harness.context, "frontier.json")
    doc = json.loads(first)
    doc["rendered_from"] = NEW
    harness.githost.files["frontier.json"] = json.dumps(doc).encode()
    harness.githost.head = NEW
    assert frontier.committed(harness.context, "frontier.json") == first  # inside the window
    age(harness)
    fresh = json.loads(frontier.committed(harness.context, "frontier.json"))
    assert fresh["rendered_from"] == NEW and harness.githost.refs[-1] == NEW


def test_an_unreachable_api_falls_back_to_the_branch(harness: Harness) -> None:
    """C7: the head is a freshness aid, never a reason to serve nothing."""
    harness.githost.head_failure = "boom"
    body = frontier.committed(harness.context, "frontier.json")
    assert body and harness.githost.refs[-1] == harness.settings.graph_branch


def test_the_last_known_head_is_kept_when_the_api_then_fails(harness: Harness) -> None:
    harness.githost.head = OLD
    frontier.committed(harness.context, "frontier.json")
    harness.githost.head_failure = "boom"
    age(harness)
    frontier.committed(harness.context, "frontier.json")
    assert harness.githost.refs[-1] == OLD


def test_the_head_is_asked_once_per_window_not_per_file(harness: Harness) -> None:
    harness.githost.head = OLD
    for path in ("frontier.json", "info.json", "targets/index.json", "frontier.json"):
        frontier.committed(harness.context, path)
    assert harness.githost.head_reads == 1
