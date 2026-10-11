"""F07-T29: the post-merge job's products commit survives ``main`` moving under it.

Found live 2026-09-20 on graph PR #130: the job pushed with a plain ``git push HEAD:main`` several
minutes after the merge it renders. An owner push (a guide copy) landed in between, the push was
rejected as a non-fast-forward, the run went red, and the merge's products were never committed;
the label it carried reached neither the frontier nor the site until a curator re-rendered by
hand. With the merge actor live, and re-pins and guide copies pushed directly, that window is
open several times a day.

A static read of the graph's workflow, like its siblings, from the refs they share.

Restated by F07-T55: the rebase over a main that moved without touching the products' inputs is
gone with the rule it served. A refused push now catches up on main as it is — the record laid on
it, the products rendered afresh (``test_finding_postmerge_catch_up.py``) — so no render of a tree
that no longer exists is ever pushed, which is what this test was about.
"""

from __future__ import annotations

import subprocess

import pytest
import yaml
from test_finding_merge_actor_workflow import GRAPH_REPO, REFS

from opn_gate import config

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
        return str(found["run"])
    pytest.skip("no gate.yml on " + " or ".join(REFS))


def test_a_rejected_push_is_caught_up_not_rebased(step: str) -> None:
    assert 'python3 "$helper" publish' in step
    assert "git rebase" not in step and "git push" not in step  # the one push is in publish


def test_a_render_of_a_tree_that_no_longer_exists_is_never_pushed(step: str) -> None:
    """The catch-up renders the products again on main as it is; the commit it pushes carries
    the products of that tree, never of the one this run checked out."""
    assert "PRODUCTS_CMD" not in step  # the command comes from the step's env, not a rebase
    assert "status=$?" in step and 'exit "$status"' in step  # giving up fails the step (C7)


def test_the_deploy_key_never_outlives_the_step(step: str) -> None:
    """C8: every exit path removes the key file."""
    assert "trap" in step and "deploy_key" in step.split("trap", 1)[1].split("\n", 1)[0]
