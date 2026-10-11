"""F07-T61: the gate's pin step fails closed and takes the pin from the base (audit 2026-10-04).

The pin step decides, before any gate code exists in the job, which target a pull request touches
and which ``network`` commit gates it. As it stood:

- a pull request that touched no target (and not ``policy.json``) was reported "nothing to gate"
  and its required check went green, whoever opened it and whatever it changed — a workflow, the
  curator list, a key, a schema;
- the pin was read from the pull request's own tree, so a submission that rewrote its target's
  ``gate-spec.json`` chose the gate that judged it (D-4: a tooling change reaches a graph only as a
  visible diff made by the gate's named owner).

Now a pull request that changes anything outside ``targets/<id>/`` and ``policy.json`` fails the
check, "not a submission", unless its author is listed in ``curators.json`` *as the base has it*
(a pull request cannot list itself); a listed curator's such pull request is still review only. The
pin is read from the base commit: the target's own ``gate-spec.json`` there, or for a new target
any target's pin on the base. The author reaches the script through the environment.

The step runs here as the workflow writes it, in a repository whose ``HEAD`` is a merge commit
whose first parent is the base, as ``refs/pull/N/merge`` is.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from test_finding_merge_actor_wakes import load_gate_doc
from test_finding_postmerge_batch import PIN_A, PIN_B, git_env

CURATOR = "thisisanameforsure"
STRANGER = "mallory"


@pytest.fixture(scope="module")
def gate_doc() -> dict[Any, Any]:
    return load_gate_doc()


def pin_step(gate_doc: dict[Any, Any]) -> dict[str, Any]:
    (step,) = [s for s in gate_doc["jobs"]["gate"]["steps"] if s.get("id") == "pin"]
    found: dict[str, Any] = step
    return found


def git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True, env=git_env()
    )
    return proc.stdout.strip()


def write(root: Path, files: Mapping[str, str | None]) -> None:
    for rel, text in files.items():
        path = root / rel
        if text is None:
            path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def merge_ref(tmp_path: Path, files: Mapping[str, str | None]) -> Path:
    """A graph whose HEAD is the merge of a pull request changing ``files`` into main."""
    root = tmp_path / "graph"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    write(
        root,
        {
            "curators.json": json.dumps(
                {"identities": [{"pseudonym": CURATOR, "github_login": CURATOR}]}
            ),
            "targets/t1/gate-spec.json": json.dumps({"network_commit": PIN_A}),
            "targets/t1/nodes/n/Statement.lean": "theorem n : True := trivial\n",
            "targets/t2/gate-spec.json": json.dumps({"network_commit": PIN_A}),
            ".github/workflows/gate.yml": "name: gate\n",
        },
    )
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    git(root, "checkout", "-q", "-b", "pr")
    write(root, files)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "the pull request")
    git(root, "checkout", "-q", "--detach", "main")
    git(root, "merge", "--no-ff", "-q", "-m", "Merge pr into main", "pr")
    return root


def run_pin(
    gate_doc: dict[Any, Any], tmp_path: Path, files: Mapping[str, str | None], author: str
) -> tuple[int, dict[str, str], str]:
    root = merge_ref(tmp_path, files)
    step = pin_step(gate_doc)
    run = str(step["run"])
    assert "${{" not in run, "the step's script takes nothing by interpolation"
    output = tmp_path / "output"
    output.write_text("", encoding="utf-8")
    env = git_env()
    env.update(GITHUB_OUTPUT=str(output), OPN_PR_AUTHOR=author)
    proc = subprocess.run(
        ["bash", "-c", run], capture_output=True, text=True, check=False, cwd=root, env=env
    )  # fmt: skip
    outputs = dict(line.split("=", 1) for line in output.read_text().splitlines() if "=" in line)
    return proc.returncode, outputs, proc.stdout + proc.stderr


# --- fail closed ---------------------------------------------------------------------------------


def test_a_workflow_change_by_a_stranger_fails_the_check(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    code, out, said = run_pin(
        gate_doc, tmp_path, {".github/workflows/gate.yml": "name: gate\non: {}\n"}, STRANGER
    )
    assert code == 1, (code, out, said)
    assert "not a submission" in said, said
    assert out.get("run") != "true"


def test_a_workflow_change_by_a_listed_curator_is_still_review_only(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    code, out, said = run_pin(
        gate_doc, tmp_path, {".github/workflows/gate.yml": "name: gate\non: {}\n"}, CURATOR
    )
    assert code == 0 and out.get("run") == "false", (code, out, said)


def test_a_pull_request_cannot_list_its_own_author_as_a_curator(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    listed = {"identities": [{"pseudonym": STRANGER, "github_login": STRANGER}]}
    code, _out, said = run_pin(gate_doc, tmp_path, {"curators.json": json.dumps(listed)}, STRANGER)
    assert code == 1 and "not a submission" in said, said


@pytest.mark.parametrize(
    "files",
    [
        {"README.md": "hello\n", "targets/t1/nodes/n/attempts/a.yaml": "a\n"},  # a target and more
        {"targets/index.json": "{}\n"},  # a product, under targets/ but in no target
        {"keys/gate.pub": "ssh-ed25519 AAAA\n"},
        {"curators.json": None},  # a deletion is a change too
    ],
)
def test_anything_outside_a_target_fails_for_a_stranger(
    gate_doc: dict[Any, Any], tmp_path: Path, files: dict[str, str | None]
) -> None:
    code, _out, said = run_pin(gate_doc, tmp_path, files, STRANGER)
    assert code == 1 and "not a submission" in said, said


def test_a_submission_still_gates_as_before(gate_doc: dict[Any, Any], tmp_path: Path) -> None:
    code, out, said = run_pin(
        gate_doc, tmp_path, {"targets/t1/nodes/n/Proof.lean": "-- proof\n"}, STRANGER
    )
    assert code == 0, said
    assert (out["run"], out["target"], out["pin"]) == ("true", "t1", PIN_A), out


def test_policy_json_is_still_gated_and_left_to_the_classifier(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    """F15-R3: the steward switch is classified by the pinned gate, which checks the author."""
    code, out, said = run_pin(gate_doc, tmp_path, {"policy.json": "{}\n"}, STRANGER)
    assert code == 0, said
    assert (out["run"], out["pin"]) == ("true", PIN_A), out


# --- the pin comes from the base ---------------------------------------------------------------


def test_a_submission_cannot_choose_its_own_gate(gate_doc: dict[Any, Any], tmp_path: Path) -> None:
    files = {
        "targets/t1/gate-spec.json": json.dumps({"network_commit": PIN_B}),
        "targets/t1/nodes/n/Proof.lean": "-- proof\n",
    }
    code, out, said = run_pin(gate_doc, tmp_path, files, STRANGER)
    assert code == 0, said
    assert out["pin"] == PIN_A, (out, said)


def test_a_new_target_is_gated_by_the_pin_the_base_carries(
    gate_doc: dict[Any, Any], tmp_path: Path
) -> None:
    files = {
        "targets/t9/gate-spec.json": json.dumps({"network_commit": PIN_B}),
        "targets/t9/target.yaml": "id: t9\n",
    }
    code, out, said = run_pin(gate_doc, tmp_path, files, CURATOR)
    assert code == 0, said
    assert (out["target"], out["pin"]) == ("t9", PIN_A), (out, said)


def test_the_author_reaches_the_script_through_the_environment(gate_doc: dict[Any, Any]) -> None:
    step = pin_step(gate_doc)
    assert step["env"]["OPN_PR_AUTHOR"] == "${{ github.event.pull_request.user.login }}"
    assert "${{" not in str(step["run"])
