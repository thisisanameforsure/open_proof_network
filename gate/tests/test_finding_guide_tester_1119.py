"""F07-T87, F07-T88 (B2, B12, B14, B16, B17a; 2026-11-19 run): the guide's sentences the run
found wrong or missing.

B2: the post-merge timing said "about a minute ... three to five" where the record measured a
median of about nine minutes to the record and fourteen to the products, for appends and proofs
alike. B12: `open scoped Nat` makes `φ` notation. B14: a large computational proof outlasts the
fast check's 20 seconds. B16: a witness's import lines are optional (pinned by behaviour in
``test_finding_witness_header_optional.py``). B17a: the walkthrough wrote its proof into the
clone, so a later ``git pull`` aborted; it writes into ``$WORK`` (the walkthrough itself runs in
``test_walkthrough.py``).
"""

from __future__ import annotations

import re
from pathlib import Path

GUIDE = Path(__file__).resolve().parents[1] / "agents" / "AGENTS.md"
TEXT = GUIDE.read_text(encoding="utf-8")
FLAT = " ".join(TEXT.split())


def test_b2_the_post_merge_wait_is_the_measured_one() -> None:
    assert "three to five for a proof or a partial" not in FLAT
    assert "about a minute for a merge that builds nothing" not in FLAT
    assert "the record lands about nine minutes after the merge" in FLAT
    assert "the products about fourteen" in FLAT


def test_b12_scoped_greek_letters_are_named() -> None:
    assert "open scoped Nat" in FLAT
    sigma = "\u03c3"  # spelled out: ruff reads the letter as a confusable
    assert f"do not name anything `φ`, `π` or `{sigma}`" in FLAT


def test_b14_large_computational_proofs_go_straight_to_precheck() -> None:
    assert "go straight to `POST /precheck`" in FLAT


def test_b16_witness_imports_are_optional() -> None:
    assert "The `import` lines are optional" in FLAT
    assert "its `import Nodes.«…».Context` among them" in FLAT


def test_b17a_the_walkthrough_never_writes_its_proof_into_the_clone() -> None:
    blocks = re.findall(r"```sh[^\n]*\n(.*?)```", TEXT, re.S)
    walk = "\n".join(blocks)
    assert '(node / "Proof.lean").write_text' not in walk
    # Every copy into the clone is on a branch, or is put back after pregate.sh.
    copies = [b for b in blocks if 'cp "$WORK/Proof.lean" "$NODE_DIR/Proof.lean"' in b]
    assert len(copies) == 2
    assert any('checkout -q -b "$BRANCH"' in b for b in copies)
    assert any('checkout -q -- "targets/$TARGET/nodes/$NODE/Proof.lean"' in b for b in copies)
