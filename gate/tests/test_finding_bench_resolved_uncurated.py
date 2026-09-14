"""Bench finding: a resolved target with no target.yaml is still published claimable.

The live tutorial target has no ``target.yaml`` and a declaration from before its root was
proved that says ``claimable: true``. ``products.target_facts`` derives ``status: resolved``
from the proved root but, for an uncurated target, returns the declaration's ``claimable``
without consulting the status, so the index row reads ``resolved`` and ``claimable: true`` with
no reason. D-33 and F11-R4/AC15 (kept by F14-R1) say ``resolved`` closes claiming; F11-Q11's
compatibility rule keeps F03-Q4's rule for such targets, and Q4 derives claimability from the
status too. Nothing exempts the tutorial.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import samples
import yaml
from fixture import COMMIT, NOW, attest
from harness import TARGET, copy_graph

from opn_gate import products

ROOT_NODE = "and-swap-reassoc"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "F14 bench finding: "
        "products.target_facts returns early for a target without target.yaml and never applies "
        "the status rule"
    ),
)
def test_resolved_uncurated_target_is_not_claimable(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    target = root / "targets" / TARGET
    assert not (target / "target.yaml").exists(), "the fixture target must be uncurated"
    st = target / "status"
    st.mkdir()
    # The live tutorial's shape: a legacy declaration that still says claimable.
    (st / "2026-09-11-1.yaml").write_text(
        yaml.safe_dump(samples.target_status(status="active", claimable=True)),
        encoding="utf-8",
    )
    attest(root, "tutorial-and-swap", 1)
    attest(root, "and-reassoc", 2)
    attest(root, ROOT_NODE, 3)
    prod = products.generate(root, rendered_from=COMMIT, commit_time=NOW)
    rows = json.loads(prod.files[Path("targets/index.json")])["targets"]
    row = next(r for r in rows if r["target_id"] == TARGET)
    assert row["status"] == "resolved"
    assert row["claimable"] is False, "a resolved target is published claimable"
    assert "status-resolved" in row["not_claimable"]
