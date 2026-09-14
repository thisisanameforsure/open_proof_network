"""Finding bench-guide-partial (a fresh agent, 2026-09-14): the guide never says where a partial
proof's bundle goes.

``gate/agents/AGENTS.md``'s skeleton section says a partial "merges into ``attempts/``" but shows
no path for the submission itself, and the only file path a contributor sees elsewhere is
``.../Proof.lean``. ``POST /submissions`` with ``artifact_type: partial`` at ``Proof.lean`` is a
400 ``artifact-path-mismatch`` (``api/opn_api/submissions.py``, ``check_artifact_path``), and the
right path, ``attempts/<ts>-<pseudonym>-partial.lean`` (``PARTIAL_PATTERN``), appears only in that
error message.

The example's ``import Nodes.«some-node».Context`` is not asserted on: the prose already says the
header is ``Statement.lean``'s byte for byte, and a live statement does import its Context
(``infinitude-of-primes``) while the Erdős ones import ``Mathlib``, so the example is a placeholder
rather than a wrong rule.
"""

from __future__ import annotations

import pytest
from test_finding_guide_pending_work import prose, says, section


@pytest.mark.xfail(
    strict=True,
    reason=(
        "F14 bench finding: "
        "the guide does not name attempts/<ts>-<pseudonym>-partial.lean; fix with the T15 guide "
        "copy"
    ),
)
def test_the_skeleton_section_names_the_partial_bundle_path() -> None:
    text = section("Skeletonization")
    assert says(text, r"attempts/<[^>]+>-<[^>]+>-partial\.lean", r"attempts/\S*-partial\.lean"), (
        "the skeleton section never names the path a partial is submitted at "
        "(attempts/<ts>-<pseudonym>-partial.lean)"
    )


@pytest.mark.xfail(
    strict=True,
    reason=("F14 bench finding: as above"),
)
def test_the_skeleton_section_says_a_partial_is_not_submitted_at_proof_lean() -> None:
    text = prose(section("Skeletonization"))
    assert says(
        text,
        r"\bartifact-path-mismatch\b",
        r"\bnot (at |as |to |in )?`?Proof\.lean`?[^.]*\bsubmi",
        r"\bsubmi[^.]*\bnot (at |as |to |in )?`?Proof\.lean",
        r"\bpath\b[^.]*-partial\.lean",
    ), (
        "the skeleton section does not say the submission's bundle path is the attempts file, "
        "not Proof.lean (the 400 artifact-path-mismatch)"
    )
