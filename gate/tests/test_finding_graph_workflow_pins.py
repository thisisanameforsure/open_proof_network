"""F07-T62 (with F04-T29's intent): every action the graph's workflows use is pinned to a commit
(audit 2026-10-04).

A tag is a moving name: whoever controls an action's repository can point ``@v4`` at new code, and
the graph's workflows hold the gate's signing key and a write deploy key in some of their jobs.
Every ``uses:`` therefore names a full forty-hex commit, with the tag it was read from as a trailing
``# vX`` comment so a person can see what it is and bump it on purpose. Read from the first of the
graph refs the workflow tests read (``REFS``), every workflow file there.
"""

from __future__ import annotations

import re
import subprocess
from typing import Any

import pytest
import yaml
from test_finding_merge_actor_workflow import GRAPH_REPO, REFS

from opn_gate import config

PINNED = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40}$")
COMMENT = re.compile(r"uses:\s*(\S+)\s+#\s*v[0-9][0-9A-Za-z.\-]*\s*$")


def git(*args: str) -> subprocess.CompletedProcess[str]:
    env = config.child_environment(drop=config.GIT_REPO_VARIABLES)
    return subprocess.run(
        ["git", "-C", str(GRAPH_REPO), *args], capture_output=True, text=True, check=False, env=env
    )


def workflows() -> dict[str, str]:
    if not GRAPH_REPO.is_dir():
        pytest.skip("the graph repo is not checked out beside this repo")
    for ref in REFS:
        listed = git("ls-tree", "--name-only", f"{ref}:.github/workflows")
        if listed.returncode != 0:
            continue
        names = [n for n in listed.stdout.split() if n.endswith((".yml", ".yaml"))]
        return {n: git("show", f"{ref}:.github/workflows/{n}").stdout for n in names}
    pytest.fail(f"no .github/workflows on {' or '.join(REFS)} of the graph")


def uses_of(doc: dict[Any, Any]) -> list[str]:
    found = []
    for job in (doc.get("jobs") or {}).values():
        if "uses" in job:  # a reusable workflow
            found.append(str(job["uses"]))
        for step in job.get("steps") or []:
            if "uses" in step:
                found.append(str(step["uses"]))
    return found


def test_every_action_is_pinned_to_a_commit_with_its_tag_beside_it() -> None:
    texts = workflows()
    assert texts, "no workflow files read"
    unpinned, uncommented, seen = [], [], 0
    for name, text in texts.items():
        doc = yaml.safe_load(text)
        commented = {m.group(1) for m in map(COMMENT.search, text.splitlines()) if m}
        for uses in uses_of(doc):
            seen += 1
            if uses.startswith("./"):
                continue  # a local action is this repository's own, at this commit
            if not PINNED.match(uses):
                unpinned.append(f"{name}: {uses}")
            elif uses not in commented:
                uncommented.append(f"{name}: {uses}")
    assert seen, "no `uses:` found: the accessor, not the workflows, is wrong"
    assert unpinned == [], unpinned
    assert uncommented == [], uncommented
