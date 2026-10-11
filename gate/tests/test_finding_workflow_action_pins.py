"""F04-T29: every action the network's workflows run is pinned to a commit (audit 2026-10-04).

The audit found every ``uses:`` in ``.github/workflows`` named a tag (``actions/checkout@v7``,
``aws-actions/configure-aws-credentials@v4``). A tag is a pointer its owner can move, so whoever
controls an action's repository could change the code that runs in the api and site deploy jobs,
which hold the OIDC token for the deploy roles (C8). A full commit SHA cannot move; the trailing
``# <tag>`` comment keeps the version readable for whoever bumps it.

A static scan of every workflow file, so a new step that names a tag turns this red.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"

#: ``uses: owner/repo[/path]@<40 hex>  # <tag>``
PINNED = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}\s+#\s*\S+$")
USES = re.compile(r"^\s*(?:-\s+)?uses:\s*(.+?)\s*$")


def uses_lines() -> list[tuple[str, int, str]]:
    found = []
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            m = USES.match(line)
            if m:
                found.append((path.name, number, m.group(1)))
    return found


def test_the_scan_sees_the_workflows() -> None:
    assert len(uses_lines()) >= 20, "guard: the scan found too few uses lines to mean anything"


def test_every_action_is_pinned_to_a_full_commit_with_its_tag() -> None:
    unpinned = [
        f"{name}:{number}: {value}"
        for name, number, value in uses_lines()
        if not value.startswith("./") and not PINNED.match(value)
    ]
    assert not unpinned, "\n".join(unpinned)


def test_one_action_is_pinned_to_one_commit_everywhere() -> None:
    """Two SHAs for one action and tag would mean one of them was resolved wrongly."""
    seen: dict[str, set[str]] = {}
    for _name, _number, value in uses_lines():
        action, _, rest = value.partition("@")
        seen.setdefault(action, set()).add(rest)
    assert all(len(v) == 1 for v in seen.values()), seen
