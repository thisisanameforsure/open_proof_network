"""Findings: four places the contributor guide tells an agent something that is not true.

Three were re-found by the Erdős 412 live run (2026-09-16), one is the register's finding 2.
Docs are tests (F10-Q3), so each of these is an assertion over ``gate/agents/AGENTS.md`` and the
fix is the guide's own edit.

1. ``pregate.sh`` is invoked without ``--target``. On a graph with more than one target that
   exits 2 with "--target is required", and it is the first command on the git path. The
   document computes ``$TARGET`` fifty lines earlier and then does not pass it. (register #2)
2. The permitted-paths table gives ``attempts/<ts>-<you>-partial.lean`` to *the gate*, "filed by
   the post-merge job". Since F11-T4 the submission **is** that file: it is the path a partial is
   prechecked and submitted at, which the Skeletonization section says correctly two hundred
   lines later. A contributor who reads the table first learns the path is not theirs to write.
   (register #31; cost the 2026-09-13 tester two prechecks)
3. The Skeletonization section says a merged skeleton's holes arrive with origin
   ``skeleton-hole``. They arrive ``authored``: D-25's enum lost ``skeleton-hole`` and
   ``postmerge.ORIGIN_SKELETON`` is what the code writes. (register #65)
4. The appendix's tool table calls the argument ``get_submission(id)``; the tool's schema
   requires ``submission_id`` and refuses ``id`` with ``arguments-invalid``. The guide promises
   "every command in it runs as written", but the appendix is a table, not an ``sh`` block, so
   the walkthrough runner never executes it — which is exactly where the drift appeared.
   (found 2026-09-16, the agent's bug 1)

A fifth line is checked here but is *not* a guide bug on its own: the skeleton example's
``import`` line. The example's header must be ``Statement.lean``'s bytes, and the guide says so
in the next paragraph, so showing any import above the theorem invites the ``proof-not-statement``
refusal the 2026-09-13 tester hit. ``test_finding_guide_skeleton`` pins the *citation's*
placement; this pins that the example shows no header of its own to copy.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "gate" / "agents" / "AGENTS.md"
PARTIAL_ROW = "`attempts/<timestamp>-<you>-partial.lean`"


def guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


def section(title: str) -> str:
    text = guide()
    start = text.index(title)
    end = text.find("\n## ", start + 1)
    return text[start : end if end != -1 else len(text)]


def table_row(cell: str) -> str:
    """The one table row whose first cell is ``cell``."""
    found = [
        line
        for line in guide().splitlines()
        if line.startswith("|") and line.split("|")[1].strip() == cell.strip()
    ]
    assert len(found) == 1, f"{cell}: {len(found)} rows"
    return found[0]


def test_the_pregate_invocation_passes_the_target() -> None:
    """Without ``--target`` the command exits 2 on every real graph; ``$TARGET`` is in scope."""
    text = guide()
    calls = [line for line in text.splitlines() if "pregate.sh" in line and "--graph" in line]
    assert calls, "the guide no longer shows a pregate.sh invocation"
    target_at = text.index('TARGET="')
    for line in calls:
        assert "--target" in line, (
            f"finding guide-pregate-target (register #2): {line.strip()!r} omits --target, "
            'so it exits 2 on a multi-target graph; fix: pass --target "$TARGET"'
        )
        assert text.index(line) > target_at, "the invocation precedes the line that sets TARGET"


def test_the_permitted_paths_table_gives_the_partial_to_the_contributor() -> None:
    """The writer cell must name the contributor, not the gate: since F11-T4 the submission is
    that file (the Skeletonization section already says so)."""
    row = table_row(PARTIAL_ROW)
    writer = row.split("|")[2].strip()
    assert "gate" not in writer.lower(), (
        f"finding guide-partial-path (register #31): the table says {writer!r} writes "
        f"{PARTIAL_ROW}, but a partial is submitted at that path; fix: name the prover"
    )
    assert re.search(r"\byou\b|\bthe prover\b", writer), writer


def test_the_skeleton_section_names_the_origin_holes_actually_get() -> None:
    """``skeleton-hole`` is not a value any code can write (D-25's enum, F07); it is
    ``authored``."""
    body = section("## Skeletonization")
    assert "skeleton-hole" not in body, (
        "finding guide-hole-origin (register #65): the Skeletonization section still says holes "
        "arrive with origin `skeleton-hole`; they arrive `authored`"
    )
    assert "`authored`" in body, "the section should name the origin a hole really carries"


def test_the_appendix_names_the_submission_argument_the_tool_requires() -> None:
    """``get_submission`` requires ``submission_id``; the appendix said ``id``."""
    rows = [line for line in guide().splitlines() if "`get_submission(" in line]
    assert rows, "the appendix no longer lists get_submission"
    for row in rows:
        assert "get_submission(submission_id)" in row, (
            f"finding guide-get-submission-arg: {row.strip()!r} names an argument the tool "
            "refuses with arguments-invalid; fix: get_submission(submission_id)"
        )


def test_the_skeleton_example_shows_no_header_to_copy() -> None:
    """A partial's header is the statement's, byte for byte (F00-R19), so an example that opens
    with an import of its own is a shape the gate refuses."""
    body = section("## Skeletonization")
    fence = re.search(r"```lean\n(.*?)```", body, re.S)
    assert fence is not None, "the Skeletonization section shows no Lean block"
    imports = [ln for ln in fence.group(1).splitlines() if ln.startswith("import ")]
    assert not imports, (
        f"finding guide-skeleton-header: the example shows {imports!r} above the theorem; a "
        "partial's header must be Statement.lean's bytes, so the example must show only the body"
    )
