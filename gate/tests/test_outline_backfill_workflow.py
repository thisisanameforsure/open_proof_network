"""F19-T5 (R7): the outline backfill holds no authority and runs Lean only in the pinned sandbox.

Asserted where it is enforced, in the YAML (engineering/CLAUDE.md, 2026-09-09), in the shape of
F18-T7's footprint backfill: started by hand at a named graph commit; read-only permissions and no
secret anywhere (C8), so nothing it runs — contributor Lean included — is handed a credential;
every outline extracted by the network commit the graph pins (D-35: the gate whose output a
curator commits is the gate the graph trusts), in a pulled image and never a built one (C9, D-4
step 3); a pin that predates ``opn-gate outline`` refused by name rather than run; and the
outlines leaving as an artifact for a curator to commit, never as a push. The command itself is
``test_outline_cli.py``'s.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "outline-backfill.yml"
JOB = "extract"
JOB_NAME = "outlines of the merges before outline/v1 (F19-R7), in the pinned sandbox"


def doc() -> dict[Any, Any]:
    loaded = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def steps(d: dict[Any, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = d["jobs"][JOB]["steps"]
    return found


def runs(d: dict[Any, Any]) -> str:
    return "\n".join(str(s.get("run", "")) for s in steps(d))


def test_it_is_started_by_hand_at_a_named_graph_commit() -> None:
    triggers = doc()[True]  # PyYAML reads the key `on` as the boolean True
    assert isinstance(triggers, dict) and set(triggers) == {"workflow_dispatch"}
    inputs = triggers["workflow_dispatch"]["inputs"]
    assert inputs["graph_sha"]["required"] is True
    assert inputs["target"]["required"] is False


def test_one_job_by_its_name() -> None:
    jobs = doc()["jobs"]
    assert list(jobs) == [JOB]
    assert jobs[JOB]["name"] == JOB_NAME


def test_it_reads_and_names_no_secret() -> None:
    d = doc()
    assert d["permissions"] == {"contents": "read"}
    assert "permissions" not in d["jobs"][JOB], "the job may not widen the workflow's grant"
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "secrets." not in text and "GITHUB_TOKEN" not in text and "github.token" not in text
    for s in steps(d):
        if str(s.get("uses", "")).startswith("actions/checkout@"):
            assert s["with"]["persist-credentials"] is False, s


def test_the_outlines_are_extracted_by_the_gate_the_graph_pins() -> None:
    """D-35: the network commit that extracts is read from the graph at the named commit, checked
    out on its own, and is the project every outline command runs; targets that pin different
    gates are refused rather than outlined by one of them."""
    d = doc()
    (pin,) = [s for s in steps(d) if s.get("id") == "pin"]
    assert "network_commit" in pin["run"] and "gate-spec.json" in pin["run"]
    assert "more than one network commit" in pin["run"]
    (checkout,) = [
        s
        for s in steps(d)
        if str(s.get("uses", "")).startswith("actions/checkout@")
        and (s.get("with") or {}).get("path") == "network-pin"
    ]
    assert checkout["with"]["ref"] == "${{ steps.pin.outputs.pin }}"
    assert checkout["with"]["repository"] == "thisisanameforsure/open_proof_network"
    script = runs(d)
    assert "--project network-pin" in script and "opn_gate.cli outline" in script
    assert "--project network " not in script


def test_a_pin_that_predates_the_command_is_refused_by_name() -> None:
    script = runs(doc())
    assert "[{,]outline[,}]" in script, "the pinned gate's own command list is what is asked"
    assert "::error::" in script and "predates opn-gate outline" in script


def test_lean_runs_only_in_a_pulled_image() -> None:
    script = runs(doc())
    assert "--image" in script and "--no-build" in script
    assert "docker build" not in script
    assert "docker pull" in script
    assert "devcontainer_ref" in script


def test_nothing_is_pushed_the_outlines_are_an_artifact() -> None:
    d = doc()
    script = runs(d)
    assert "git push" not in script and "git commit" not in script
    assert "--dest outlines" in script, "written beside the clone, so the artifact holds only new"
    (upload,) = [
        s for s in steps(d) if str(s.get("uses", "")).startswith("actions/upload-artifact@")
    ]
    assert upload["if"] == "always()"
    assert "outlines/" in upload["with"]["path"]
