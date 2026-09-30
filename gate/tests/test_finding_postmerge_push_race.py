"""F07-T29: the post-merge job's products commit survives ``main`` moving under it.

Found live 2026-09-20 on graph PR #130: the job pushed with a plain ``git push HEAD:main`` several
minutes after the merge it renders. An owner push (a guide copy) landed in between, the push was
rejected as a non-fast-forward, the run went red, and the merge's products were never committed;
the label it carried reached neither the frontier nor the site until a curator re-rendered by
hand. With the merge actor live, and re-pins and guide copies pushed directly, that window is
open several times a day.

A static read of the graph's workflow, like its siblings: ``origin/main``, or the local branch
the task was built on until that is pushed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from opn_gate import config

ROOT = Path(__file__).resolve().parents[2]
GRAPH_REPO = ROOT.parent / "open_proof_network_graph"
REFS = ("origin/main", "f07-t29-postmerge-push")
STEP = "Commit the attestation and the products"


@pytest.fixture(scope="module")
def step() -> str:
    if not GRAPH_REPO.is_dir():
        pytest.skip("the graph repo is not checked out beside this repo")
    env = config.child_environment(drop=config.GIT_REPO_VARIABLES)
    for ref in REFS:
        proc = subprocess.run(
            ["git", "-C", str(GRAPH_REPO), "show", f"{ref}:.github/workflows/gate.yml"],
            capture_output=True, text=True, check=False, env=env,
        )  # fmt: skip
        if proc.returncode != 0:
            continue
        steps = yaml.safe_load(proc.stdout)["jobs"]["postmerge"]["steps"]
        (found,) = [s for s in steps if str(s.get("name", "")).startswith(STEP)]
        if "rebase" in found["run"]:
            return str(found["run"])
    pytest.skip("no gate.yml with the hardened push on " + " or ".join(REFS))


def test_a_rejected_push_is_rebased_and_retried(step: str) -> None:
    assert "git rebase" in step and "for attempt in" in step
    assert step.count("HEAD:main") == 1  # one push command, inside the loop


def test_it_refuses_to_rebase_over_anything_the_products_derive_from(step: str) -> None:
    """The products were rendered from the merge commit. If what landed meanwhile touched a target,
    an attestation or a product, a rebased commit would publish a render of a tree that no longer
    exists: that is a failure, said loudly, never a retry."""
    assert "git diff --name-only" in step
    for derived in ("targets", "attestations", "frontier.json"):
        assert derived in step.split("git diff --name-only", 1)[1].split("\n", 1)[0], derived
    assert "::error::" in step and "exit 1" in step


def test_the_deploy_key_never_outlives_the_step(step: str) -> None:
    """C8: every exit path removes the key file."""
    assert "trap" in step and "deploy_key" in step.split("trap", 1)[1].split("\n", 1)[0]
