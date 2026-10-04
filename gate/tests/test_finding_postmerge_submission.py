"""F07-T63: the submitter the attestation records is the one the gate saw (audit 2026-10-04).

The post-merge job read the merged pull request's body from the host *after* the merge
(``gh api pulls/N --jq .body``) and handed it to the pinned gate as the submission block: the
submitter, the declared model and tooling, the precheck consumed (F07-T14). A body edited after the
gate went green — by anyone who may edit the pull request — was what the attestation and the ledger
recorded, though the gate never saw it.

Now the gate job keeps the body from its own event payload (through the environment, never
interpolated into a script) and uploads it as the artifact ``submission-<pr>-<head sha>``; the
post-merge job downloads the newest such artifact for the merged pull request's head and falls back
to the live body, with a warning, only when there is none (a run from before this change, or an
expired artifact). The post-merge step runs here as the workflow writes it, against a fake host.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path
from typing import Any

import pytest
from test_finding_merge_actor_wakes import load_gate_doc
from test_finding_postmerge_batch import FAKE, REPO, git_env

HEAD = "c" * 40
NUMBER = "7"
GATED = "<!-- opn-submission -->\nsubmitter: honest-prover\n"
EDITED = "<!-- opn-submission -->\nsubmitter: someone-else\n"
BODY_STEP = "Fetch the merged pull request's body"

#: The host: the pull request as it reads now, the artifacts the gate kept, and a download.
FAKE_GH = r"""#!/usr/bin/env python3
import json, os, pathlib, sys
args = sys.argv[1:]
with open(os.environ["GH_LOG"], "a", encoding="utf-8") as log:
    log.write(" ".join(args) + "\n")
host = json.loads(os.environ["GH_HOST"])
if args[:1] == ["api"]:
    path = args[1]
    if path.endswith("/pulls/" + host["number"]):
        pr = {"number": int(host["number"]), "body": host["live"], "head": {"sha": host["head"]}}
        if "--jq" in args:
            print(pr["body"])
        else:
            print(json.dumps(pr))
        sys.exit(0)
    if "/actions/artifacts" in path:
        name = path.split("name=", 1)[1].split("&", 1)[0]
        kept = [a for a in host["artifacts"] if a["name"] == name]
        print(json.dumps({"total_count": len(kept), "artifacts": kept}))
        sys.exit(0)
if args[:2] == ["run", "download"]:
    run_id = args[2]
    out = pathlib.Path(args[args.index("--dir") + 1])
    name = args[args.index("--name") + 1]
    body = host["bodies"].get(f"{run_id}/{name}")
    if body is None:
        print(f"no artifact {name} in run {run_id}", file=sys.stderr)
        sys.exit(1)
    out.mkdir(parents=True, exist_ok=True)
    (out / "pr-body.md").write_text(body, encoding="utf-8")
    sys.exit(0)
print("unexpected: " + " ".join(args), file=sys.stderr)
sys.exit(1)
"""


@pytest.fixture(scope="module")
def gate_doc() -> dict[Any, Any]:
    return load_gate_doc()


def artifact(run_id: int, created: str, *, expired: bool = False) -> dict[str, Any]:
    return {
        "id": run_id * 10,
        "name": f"submission-{NUMBER}-{HEAD}",
        "expired": expired,
        "created_at": created,
        "workflow_run": {"id": run_id, "head_sha": HEAD},
    }


def body_step(
    gate_doc: dict[Any, Any], tmp_path: Path, host: dict[str, Any]
) -> tuple[int, str, str]:
    (step,) = [
        s for s in gate_doc["jobs"]["postmerge"]["steps"]
        if str(s.get("name", "")).startswith(BODY_STEP)
    ]  # fmt: skip
    run = str(step["run"]).replace("${{ steps.pr.outputs.number }}", NUMBER)
    assert "${{" not in run, "an expression this rehearsal does not supply"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(FAKE_GH, encoding="utf-8")
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    runner_temp = tmp_path / "temp"
    runner_temp.mkdir()
    env = git_env()
    env.update(
        PATH=f"{bin_dir}{os.pathsep}{env['PATH']}", GH_LOG=str(runner_temp / "gh.log"),
        GH_HOST=json.dumps({"number": NUMBER, "head": HEAD, **host}), GH_TOKEN=FAKE,
        GITHUB_REPOSITORY=REPO, RUNNER_TEMP=str(runner_temp), NUMBER=NUMBER,
    )  # fmt: skip
    proc = subprocess.run(
        ["bash", "-c", run], capture_output=True, text=True, check=False, cwd=tmp_path, env=env
    )  # fmt: skip
    body = runner_temp / "pr-body.md"
    return (
        proc.returncode,
        body.read_text(encoding="utf-8") if body.exists() else "",
        (proc.stdout + proc.stderr),
    )


def test_the_recorded_body_is_the_one_the_gate_saw(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    host = {
        "live": EDITED,
        "artifacts": [artifact(41, "2026-10-04T10:00:00Z")],
        "bodies": {f"41/submission-{NUMBER}-{HEAD}": GATED},
    }
    code, body, said = body_step(gate_doc, tmp_path, host)
    assert code == 0, said
    assert body == GATED, (body, said)


def test_the_newest_gate_run_on_that_head_is_the_one_read(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    """A head gated twice (a re-opened pull request) kept two bodies; the merge followed the
    newest run's green check. An expired artifact is never chosen."""
    name = f"submission-{NUMBER}-{HEAD}"
    host = {
        "live": EDITED,
        "artifacts": [
            artifact(41, "2026-10-04T10:00:00Z"),
            artifact(43, "2026-10-04T11:00:00Z"),
            artifact(45, "2026-10-04T12:00:00Z", expired=True),
        ],
        "bodies": {f"41/{name}": "old\n", f"43/{name}": GATED, f"45/{name}": "expired\n"},
    }
    code, body, said = body_step(gate_doc, tmp_path, host)
    assert code == 0 and body == GATED, (body, said)


def test_with_no_body_kept_the_live_one_is_recorded_with_a_warning(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    """A merge gated before this change, or one whose artifact expired: the record goes on with
    what the host says now, and says so."""
    code, body, said = body_step(
        gate_doc, tmp_path, {"live": EDITED, "artifacts": [], "bodies": {}}
    )
    assert code == 0, said
    assert body.rstrip("\n") == EDITED.rstrip("\n")
    assert "::warning::" in said, said


def test_the_gate_job_keeps_the_body_from_its_event_named_for_its_head(
    gate_doc: dict[Any, Any],
) -> None:
    steps = gate_doc["jobs"]["gate"]["steps"]
    (keep,) = [s for s in steps if "PR_BODY" in (s.get("env") or {}) and "submission" in str(s)]
    assert keep["env"]["PR_BODY"] == "${{ github.event.pull_request.body }}"
    assert "${{" not in str(keep["run"]), "the body reaches the script through the environment"
    assert keep["if"] == "steps.pin.outputs.run == 'true'"
    (upload,) = [
        s for s in steps if str(s.get("uses", "")).startswith("actions/upload-artifact@")
        and "submission-" in str((s.get("with") or {}).get("name"))
    ]  # fmt: skip
    assert upload["with"]["name"] == (
        "submission-${{ github.event.pull_request.number }}-"
        "${{ github.event.pull_request.head.sha }}"
    )
    assert upload["if"] == "steps.pin.outputs.run == 'true'"
    assert steps.index(keep) < steps.index(upload)
