"""F22-T24 (feature request A): a writer could learn the gate's warnings on a words pull
request only from the Actions log. The gate job keeps ``gate-<pr>-<attempt>`` only for a pull
request that builds, is admitted, has exhibits or a QA re-run, so a gloss or an explainer left no
artifact at all, and ``GET /submissions/<id>`` had nothing to read. The classification, which
carries the warnings, is now kept for every pull request the job classified, under its own name,
so the service can show a green pull request's warnings as well as a red one's reasons."""

from __future__ import annotations

from typing import Any

import pytest
from test_finding_merge_actor_wakes import load_gate_doc


@pytest.fixture(scope="module")
def gate_doc() -> dict[Any, Any]:
    return load_gate_doc()


def test_the_classification_is_kept_for_every_classified_pull_request(
    gate_doc: dict[Any, Any],
) -> None:
    steps = gate_doc["jobs"]["gate"]["steps"]
    kept = [
        s
        for s in steps
        if str(s.get("uses", "")).startswith("actions/upload-artifact@")
        and "classification.json" in str(s.get("with", {}).get("path", ""))
    ]
    assert len(kept) == 1, [s.get("name") for s in steps]
    (step,) = kept
    assert step["with"]["name"] == (
        "classify-${{ github.event.pull_request.number }}-${{ github.run_attempt }}"
    )
    condition = str(step["if"])
    assert condition.startswith("always()") and "steps.classify.outcome != 'skipped'" in condition
    assert "needs_gate" not in condition  # a words pull request builds nothing and still has one
    names = [s.get("id") or s.get("name") for s in steps]
    assert names.index("classify") < steps.index(step)
