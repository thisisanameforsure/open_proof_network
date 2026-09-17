"""F07-R19, T18: a hole whose printed type does not read back is never made into a child.

The calibration run of 2026-09-17 published two holes of `erdos-69` over the naturals while the
assembly had discharged them over the reals: the extractor printed a real-valued division with its
coercion ascriptions dropped, and the text elaborates again as natural-number division, which
truncates. The nodes looked well formed, the gate refused the real proof against them (step 7
`witness-elaboration`), and nothing said why. The extractor now
reports whether each hole's printed closed type elaborates back to the same obligation, and this
is the writer's half. Step 4 refuses such a partial before it merges (F07-T19, as
`hole-not-roundtrip`); this refusal is the backstop for a partial merged under a pin that
predates that check.

The lean tier proves the extractor's half, because whether a printed type reads back is a question
for Lean (`test_finding_hole_roundtrip_lean.py`).
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest
from test_postmerge import ASSEMBLY, HOLES, PARENT, PSEUDONYM, STAMP, parent_dir

from opn_gate import postmerge
from opn_gate.steps import artifact as art


def test_a_hole_that_does_not_read_back_is_refused_and_writes_nothing(tmp_path: Path) -> None:
    """AC40: the refusal names the hole, and no child directory is left behind (C7)."""
    node_dir = parent_dir(tmp_path)
    holes = (HOLES[0], dataclasses.replace(HOLES[1], closed_roundtrip=False))

    with pytest.raises(postmerge.GraphWriteError) as excinfo:
        postmerge.apply_partial(
            node_dir, holes, partial_text=ASSEMBLY, pseudonym=PSEUDONYM, stamp=STAMP
        )

    message = str(excinfo.value)
    assert "left" in message and "F07-R19" in message
    # The failing hole is the second, so the first would already have been written by a check
    # inside the loop: neither child exists.
    for index in (1, 2):
        assert not (node_dir.parent / f"{PARENT}--h{index}").exists()


def test_a_hole_that_reads_back_is_written_as_before(tmp_path: Path) -> None:
    """The guard is a refusal, not a new condition on the ordinary path."""
    node_dir = parent_dir(tmp_path)
    result = postmerge.apply_partial(
        node_dir, HOLES, partial_text=ASSEMBLY, pseudonym=PSEUDONYM, stamp=STAMP
    )
    assert result.children == (f"{PARENT}--h1", f"{PARENT}--h2")
    assert all(h.closed_roundtrip for h in HOLES)


def test_an_extractor_that_reports_no_field_is_taken_as_a_round_trip() -> None:
    """D-35: the rule arrives with the re-pin that carries it. A graph pinned to a commit whose
    extractor predates the check reports no field, and its holes must keep being written."""
    old = art.Hole.of(
        {
            "name": "right",
            "type": "r",
            "closed_type": "∀ (p q r : Prop), (p ∧ q) ∧ r → r",
            "defeq_goal": False,
        }
    )
    assert old.closed_roundtrip is True
    assert old.as_dict()["closed_roundtrip"] is True


@pytest.mark.parametrize("reported", [True, False])
def test_the_field_round_trips_through_the_report(reported: bool) -> None:
    """What the extractor says is what the writer reads, both ways."""
    hole = art.Hole.of(
        {
            "name": "h",
            "type": "T",
            "closed_type": "T",
            "defeq_goal": False,
            "closed_roundtrip": reported,
        }
    )
    assert hole.closed_roundtrip is reported
    assert art.Hole.of(hole.as_dict()).closed_roundtrip is reported
