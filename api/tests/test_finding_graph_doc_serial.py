"""Finding graph-doc-serial (2026-11-24, after the bulk load): every ``POST /check`` timed out.

The bulk load took the graph from 32 targets to 443. ``precheck.graph_doc`` reads every target's
``graph.json`` through the committed-file cache one file at a time, and the real host opens a new
HTTPS connection per file, so a cold read (a fresh container, or any request after the graph
moves and the generation ages every entry) cost 443 round trips in series: the live log of a
timed-out ``/check`` shows 372 ``graph.json`` fetches in 24 s before the 29 s limit ended it.
Check, precheck, proposals and claims all reach ``graph_doc``; no ``POST`` had answered in the 30
hours before this was found.

The reads are independent, so they are made concurrently: what the test holds is that they
overlap, counted at the host, never a wall-clock budget, which flakes on a loaded machine. What
must not change: every target's nodes come back, and a ``graph.json`` that cannot be read is
still the cache's ``503 graph-unreachable``.
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any

import pytest
from api_fakes import Harness

from opn_api import precheck
from opn_api.app import ApiError

TARGETS = 40


class Overlap:
    """Wraps the fake host's ``fetch_raw`` to count how many ``graph.json`` reads are in flight
    at once; a short sleep stands in for the network so overlapping calls can be seen."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.lock = threading.Lock()
        self.in_flight = 0
        self.most = 0

    def __call__(self, repo: str, ref: str, path: str, *, etag: str | None) -> Any:
        graph = path.endswith("/graph.json")
        if graph:
            with self.lock:
                self.in_flight += 1
                self.most = max(self.most, self.in_flight)
        try:
            if graph:
                time.sleep(0.01)
            return self.inner(repo, ref, path, etag=etag)
        finally:
            if graph:
                with self.lock:
                    self.in_flight -= 1


def many_targets(h: Harness, n: int = TARGETS) -> list[str]:
    index = json.loads(h.githost.files["targets/index.json"])
    template = index["targets"][0]
    ids = [f"bulk-{i:03d}" for i in range(n)]
    index["targets"] = [{**template, "target_id": t} for t in ids]
    h.githost.files["targets/index.json"] = json.dumps(index).encode()
    for t in ids:
        h.githost.files[f"targets/{t}/graph.json"] = json.dumps(
            {"nodes": [{"node_id": t, "status": "ready"}]}
        ).encode()
    return ids


def test_graph_doc_reads_the_targets_concurrently(harness: Harness) -> None:
    many_targets(harness)
    overlap = Overlap(harness.githost.fetch_raw)
    harness.githost.fetch_raw = overlap  # type: ignore[method-assign]
    precheck.graph_doc(harness.app.state.context)
    assert overlap.most >= 4, f"at most {overlap.most} graph.json read(s) in flight at once"


def test_graph_doc_still_returns_every_targets_nodes(harness: Harness) -> None:
    ids = many_targets(harness)
    doc = precheck.graph_doc(harness.app.state.context)
    assert sorted(doc) == ids
    assert all(doc[t] == [{"node_id": t, "status": "ready"}] for t in ids)


def test_an_unreadable_graph_is_still_graph_unreachable(harness: Harness) -> None:
    ids = many_targets(harness)
    del harness.githost.files[f"targets/{ids[17]}/graph.json"]
    with pytest.raises(ApiError) as caught:
        precheck.graph_doc(harness.app.state.context)
    assert caught.value.status == 503
    assert caught.value.code == "graph-unreachable"
