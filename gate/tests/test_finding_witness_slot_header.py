"""F07-T37: a hole's witness slot carries its statement's header (testers 2026-09-23).

The guide says ``Witness.lean`` "holds the statement's header (its ``import`` and ``open`` lines,
unchanged) and one declaration named ``witness``". The slot the post-merge job wrote for
``erdos-1050--h1-v2--h1`` had no header at all, so two agents on 2026-09-23 each added one by hand
(#146 and #150 both did, and #146 merged): the file a contributor is told to fill did not have the
shape the guide describes. The writer now copies the child statement's ``import`` and ``open``
lines into the slot, exactly as the statement has them.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fakes import FakeToolchain, artifact_result
from test_cli_sandboxed import NODES, Seam, run
from test_finding_witness_slot import EXPECTED
from test_postmerge_apply import HOLES, WITNESS, argv, merged_partial

from opn_gate import cli, graph


def header(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith(("import ", "open "))]


def test_a_holes_slot_opens_with_its_statements_header(
    tmp_path: Path, seam: Seam, capsys: pytest.CaptureFixture[str]
) -> None:
    root, _assembly, _ = merged_partial(tmp_path)
    report = artifact_result(holes=HOLES)
    report.doc["holes"][0]["expected_witness"] = EXPECTED
    seam.fake = FakeToolchain(witness=WITNESS, artifact=report)
    code, out, err = run(capsys, *argv(root, tmp_path / "o", "--apply-partial", "--author", "c"))
    assert code == cli.EXIT_PASS, err
    for child in out["partial"]["children"]:
        node = root / NODES / child
        statement = (node / "Statement.lean").read_text(encoding="utf-8")
        slot = (node / "Witness.lean").read_text(encoding="utf-8")
        assert header(statement), "guard: a child statement has a header to copy"
        assert header(slot) == header(statement), (child, slot)
        assert slot.startswith(header(statement)[0]), "Lean takes imports first"
        assert graph.witness_is_stub(node), "still a slot: the node stays blocked (F07-R6)"
