"""Finding graph-readme (the 2026-09-13 Euclid tester): the graph's README sends a reader to a
decisions document that does not exist.

``README.md`` at the graph's ``origin/main`` names ``docs/architecture_decisions_v_3_10.html``
in the ``network`` repository, which carries only the current version. A static read of the
fetched remote, skipped where the graph is not checked out beside this repo.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from opn_gate import config

ROOT = Path(__file__).resolve().parents[2]
GRAPH_REPO = ROOT.parent / "open_proof_network_graph"
CITATION = re.compile(r"docs/architecture_decisions_v_\d+_\d+\.html")

REASON = (
    "finding graph-readme (D-35, F10-R2): the graph's README cites "
    "docs/architecture_decisions_v_3_10.html, which this repo does not carry; "
    "fix: F10-T7 (Mike, 2026-09-14)"
)


def _live_readme() -> str:
    if not GRAPH_REPO.is_dir():
        pytest.skip("the graph repo is not checked out beside this repo")
    proc = subprocess.run(
        ["git", "-C", str(GRAPH_REPO), "show", "origin/main:README.md"],
        capture_output=True,
        text=True,
        check=False,
        env=config.child_environment(drop=config.GIT_REPO_VARIABLES),  # the hook exports GIT_DIR
    )
    if proc.returncode != 0:
        pytest.skip(f"origin/main:README.md is not readable: {proc.stderr[:200]}")
    return proc.stdout


@pytest.mark.xfail(strict=True, reason=REASON)
def test_the_graph_readme_cites_a_decisions_document_that_exists() -> None:
    cited = sorted(set(CITATION.findall(_live_readme())))
    assert cited, "the graph's README cites no docs/architecture_decisions_v_<n>_<m>.html"
    missing = [path for path in cited if not (ROOT / path).is_file()]
    present = sorted(p.name for p in (ROOT / "docs").glob("architecture_decisions_v_*.html"))
    assert missing == [], f"cited but absent: {missing}; this repo has {present}"
