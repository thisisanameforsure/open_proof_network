"""F28-T9 (D-12 v3.42, C8): closing by construction in the graph's post-merge job.

Read from ``gate.yml`` on the refs the merge actor's tests read (the F28 branch first while it is
a graph branch). Checked where each property is enforced: the join step runs for every merge,
after the merge's own verdict and before the record is kept, with the render pin's gate and no
secret, and is inert on a pin that predates the sweep; the one step that reads the gate key also
signs each closure record; and the closer's pull-request machinery is gone.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from test_finding_merge_actor_wakes import load_gate_doc

POSTMERGE = "postmerge"
JOIN = "Join what this merge made provable"
SIGN = "Sign with the gate key (the only step that sees it)"


@pytest.fixture(scope="module")
def gate_doc() -> dict[Any, Any]:
    doc: dict[Any, Any] = load_gate_doc()
    return doc


def names(doc: dict[Any, Any]) -> list[str]:
    return [str(s.get("name", "")) for s in doc["jobs"][POSTMERGE]["steps"]]


def step(doc: dict[Any, Any], prefix: str) -> dict[str, Any]:
    found: list[dict[str, Any]] = [
        s for s in doc["jobs"][POSTMERGE]["steps"] if str(s.get("name", "")).startswith(prefix)
    ]
    assert len(found) == 1, prefix
    return found[0]


def test_the_join_runs_after_the_verdict_and_before_the_record(gate_doc: dict[Any, Any]) -> None:
    order = names(gate_doc)
    at = next(i for i, n in enumerate(order) if n.startswith(JOIN))
    assert order[at - 1].startswith("Re-derive the verdict on the merge commit")
    assert order[at + 1] == SIGN
    keep = next(i for i, n in enumerate(order) if n.startswith("Keep this merge's own record"))
    assert at < keep


def test_the_join_holds_no_secret_and_is_inert_on_an_old_pin(gate_doc: dict[Any, Any]) -> None:
    join = step(gate_doc, JOIN)
    assert join["if"] == "steps.pr.outputs.run == 'true'"
    assert "secrets." not in json.dumps(join)
    assert join["env"]["PYTHONPATH"] == "network-render/gate"
    run = join["run"]
    assert "opn_gate.cli close" in run and "--all" in run and "--no-build" in run
    assert "predates the closure sweep" in run


def test_the_one_key_step_signs_the_attestation_and_each_closure_record(
    gate_doc: dict[Any, Any],
) -> None:
    sign = step(gate_doc, SIGN)
    assert "steps.join.outputs.closed == 'true'" in sign["if"]
    assert "closure.json" in sign["run"] and "opn_gate.cli sign" in sign["run"]
    readers = [
        s for s in gate_doc["jobs"][POSTMERGE]["steps"] if "OPN_GATE_SIGNING_KEY" in json.dumps(s)
    ]
    assert [s["name"] for s in readers] == [SIGN]


def test_no_closing_pull_requests_remain(gate_doc: dict[Any, Any]) -> None:
    assert not any("closer" in n for n in names(gate_doc))
