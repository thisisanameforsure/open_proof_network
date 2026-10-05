"""F20-T10: the drafter workflow holds no authority, runs no Lean, and never passes keyless.

Asserted where it is enforced, in the YAML (engineering log, 2026-09-09): started by dispatch only
(F20-Q9), read-only permissions, the two secrets read by the one step that drafts and by no other
(C8), no contributor Lean anywhere (§6: drafting reads files), nothing pushed (D-35), the report
uploaded whatever happens; and the step's own decision driven as a script with a stand-in ``uv``,
so that a missing credential is a dry run whose job then fails by name (F20-Q7, the F12-Q16 shape)
while a dry run asked for passes. The action-pin scan (``test_finding_workflow_action_pins``)
covers its ``uses:`` lines with every other workflow's.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "gloss-draft.yml"
SECRETS = {"OPENROUTER_API_KEY", "OPN_DRAFTER_TOKEN"}


def doc() -> dict[Any, Any]:
    loaded = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def steps() -> list[dict[str, Any]]:
    jobs = doc()["jobs"]
    assert isinstance(jobs, dict) and set(jobs) == {"draft"}
    found = jobs["draft"]["steps"]
    assert isinstance(found, list)
    return found


def step(step_id: str) -> dict[str, Any]:
    [found] = [s for s in steps() if s.get("id") == step_id]
    return found


def runs() -> str:
    return "\n".join(str(s.get("run", "")) for s in steps())


def test_it_is_started_by_dispatch_only_with_its_inputs() -> None:
    triggers = doc()[True]  # PyYAML reads the key `on` as the boolean True
    assert isinstance(triggers, dict) and set(triggers) == {"workflow_dispatch"}
    inputs = triggers["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"graph_ref", "target", "subjects", "max_subjects", "dry_run"}
    assert inputs["subjects"]["options"] == ["new", "uncovered"]
    assert inputs["dry_run"]["type"] == "boolean" and inputs["dry_run"]["default"] is False


def test_it_has_no_write_permission_and_pushes_nothing() -> None:
    d = doc()
    assert d["permissions"] == {"contents": "read"}
    script = runs()
    assert "git push" not in script and "git commit" not in script
    for s in steps():
        if str(s.get("uses", "")).startswith("actions/checkout@"):
            assert s["with"]["persist-credentials"] is False


def test_the_secrets_reach_the_one_step_that_drafts() -> None:
    """C8: every secret has one home and one reader. The draft step holds both, as
    environment for ``opn_gate.config``; no other step names a secret at all."""
    for s in steps():
        text = yaml.safe_dump(s)
        if s.get("id") == "draft":
            env = s["env"]
            named = {k for k, v in env.items() if "secrets." in str(v)}
            assert named == SECRETS
            assert all(env[k] == f"${{{{ secrets.{k} }}}}" for k in SECRETS)
        else:
            assert "secrets." not in text, s.get("name")
    top = {k: v for k, v in doc().items() if k != "jobs"}
    assert "secrets." not in yaml.safe_dump(top)


def test_no_contributor_lean_runs_here() -> None:
    """Drafting reads the committed Lean text and outline products; nothing elaborates."""
    script = runs()
    for forbidden in ("docker", "lake ", "elan", "lean ", "--sandbox", "pregate", "reproduce"):
        assert forbidden not in script, forbidden
    assert "opn_gate.cli" in script and '"${args[@]}"' in script
    assert "gloss draft" in str(step("draft")["run"])


def test_the_report_is_kept_whatever_happens() -> None:
    [upload] = [s for s in steps() if str(s.get("uses", "")).startswith("actions/upload-artifact@")]
    assert upload["if"] == "always()"
    assert "gloss-draft-report.json" in upload["with"]["path"]
    summary = [s for s in steps() if s.get("name") == "Summarise the run"]
    assert summary and summary[0]["if"] == "always()"


def test_a_missing_credential_fails_the_job_by_name() -> None:
    [last] = [s for s in steps() if s.get("name") == "Fail when a credential was missing"]
    assert "steps.draft.outputs.missing != ''" in last["if"]
    assert "inputs.dry_run != true" in last["if"]
    assert "exit 1" in last["run"] and "::error::" in last["run"]
    assert steps()[-1] is not None and steps()[-1].get("name") == last["name"]


# --- the draft step's decision, run as a script -------------------------------------------------


def decide(tmp_path: Path, env: dict[str, str]) -> tuple[int, dict[str, str], list[str]]:
    """Run the draft step's script with a stand-in ``uv`` that records its arguments; answer the
    exit code, the step's outputs and the command the real ``uv`` would have run."""
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("no bash")
    work = tmp_path / "network"
    work.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    argv_file = tmp_path / "argv"
    fake_uv = bin_dir / "uv"
    fake_uv.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" > "{argv_file}"\necho "{{}}"\n')
    fake_uv.chmod(0o755)
    output = tmp_path / "github_output"
    output.write_text("")
    full = {
        "PATH": f"{bin_dir}{os.pathsep}/usr/bin:/bin",
        "GITHUB_OUTPUT": str(output),
        "SUBJECTS": "new",
        "TARGET": "",
        "MAX_SUBJECTS": "",
        "DRY_RUN": "false",
        "OPENROUTER_API_KEY": "",
        "OPN_DRAFTER_TOKEN": "",
        "SUBMIT_URL": "",
        **env,
    }
    script = str(step("draft")["run"])
    done = subprocess.run(
        [bash, "-c", script], cwd=work, env=full, capture_output=True, text=True, check=False
    )
    outputs = dict(line.split("=", 1) for line in output.read_text().splitlines() if "=" in line)
    argv = argv_file.read_text().splitlines() if argv_file.is_file() else []
    return done.returncode, outputs, argv


def test_without_the_credentials_it_dry_runs_and_names_what_is_missing(tmp_path: Path) -> None:
    code, outputs, argv = decide(tmp_path, {})
    assert code == 0
    assert outputs["missing"] == "OPENROUTER_API_KEY OPN_DRAFTER_TOKEN OPN_API_URL"
    assert outputs["mode"].startswith("dry-run (missing")
    assert "--dry-run" in argv and "--submit-url" not in argv
    assert argv[:4] == ["run", "--frozen", "python", "-m"]


def test_with_one_credential_missing_it_still_dry_runs(tmp_path: Path) -> None:
    code, outputs, argv = decide(
        tmp_path, {"OPENROUTER_API_KEY": "k", "SUBMIT_URL": "https://api.example"}
    )
    assert code == 0 and outputs["missing"] == "OPN_DRAFTER_TOKEN" and "--dry-run" in argv


def test_with_every_credential_it_runs_live(tmp_path: Path) -> None:
    code, outputs, argv = decide(
        tmp_path,
        {
            "OPENROUTER_API_KEY": "k",
            "OPN_DRAFTER_TOKEN": "t",
            "SUBMIT_URL": "https://api.example",
            "TARGET": "erdos-69",
            "SUBJECTS": "uncovered",
        },
    )
    assert code == 0 and outputs["mode"] == "live" and outputs["missing"] == ""
    assert "--dry-run" not in argv
    assert argv[argv.index("--submit-url") + 1] == "https://api.example"
    assert argv[argv.index("--target") + 1] == "erdos-69"
    assert argv[argv.index("--subjects") + 1] == "uncovered"
    assert "t" not in argv and "k" not in argv  # the secrets travel by environment only


def test_a_dry_run_asked_for_is_one_even_with_the_credentials(tmp_path: Path) -> None:
    code, outputs, argv = decide(
        tmp_path,
        {
            "OPENROUTER_API_KEY": "k",
            "OPN_DRAFTER_TOKEN": "t",
            "SUBMIT_URL": "https://api.example",
            "DRY_RUN": "true",
        },
    )
    assert code == 0 and outputs["mode"] == "dry-run (asked for)" and "--dry-run" in argv
