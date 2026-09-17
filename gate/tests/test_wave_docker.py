# ruff: noqa: RUF001, RUF003 — the registry fixtures are Lean source, with its double-struck
# letters, and the comments quote the statements they draft
"""F14-T11L: a drafted wave row is admitted inside the step-3 sandbox (R13; D-29, C9).

``make verify-lean`` (docker tier). The fast tier proves the driver drafts the clean rows and
refuses the rest by name, and that a draft imports and classifies as an intake
(``test_wave.py``) — but none of that runs Lean, while every draft the tool writes opens with
``import Mathlib``. The authoritative gate judges a drafted root inside the sandbox on the
Mathlib image, and this is the half that says so.

The two cases are the two shapes wave one met live (F14-T15): a clean row's root is admitted,
and a row whose witness is a stub is refused at step 7 by the container's own Lean — six of
wave one's twenty-two needed a real witness written by hand before admission would take them.

The image is the session ``mathlib_image``, built for ``gate/mathlib-pins.txt``'s one commit,
which is the ``mathlib_sha`` every live wave target pins: CI builds one image, not two.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import ONRAMP, ONRAMP_TARGET
from harness import copy_graph
from test_intake import import_fc
from test_wave import EXTRA, FILES, PIN, catalog_doc, load_tool

from opn_gate import schemas

pytestmark = pytest.mark.docker

#: The clean row the driver drafts: ``∀ n : ℕ, n ≤ n + 1``, which elaborates under Mathlib in
#: milliseconds, so the run costs the sandbox's start-up rather than a proof.
KEY = 7001
TARGET_ID = f"erdos-{KEY}"
REL_PATH = f"FormalConjectures/ErdosProblems/{KEY}.lean"

#: A witness that elaborates and depends on ``sorryAx`` — refused at step 7, `witness-sorry`.
STUB_WITNESS = "/-! A stub, not a witness. -/\n\ntheorem witness : True := by\n  sorry\n"


def draft_one(tmp_path: Path) -> Path:
    """Run the wave driver over the registry fixture, drafting only ``KEY``."""
    fc = tmp_path / "fc"
    for number, text in {**FILES, **EXTRA}.items():
        path = fc / "FormalConjectures" / "ErdosProblems" / f"{number}.lean"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    helpers = fc / "FormalConjecturesForMathlib" / "Combinatorics" / "AP.lean"
    helpers.parent.mkdir(parents=True)
    helpers.write_text(
        "namespace Set\ndef IsAPOfLength (s : Set ℕ) (k : ℕ) : Prop := True\nend Set\n",
        encoding="utf-8",
    )
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps(catalog_doc()), encoding="utf-8")
    out = tmp_path / "wave"
    tool = load_tool()
    code = tool.main(
        ["--catalog", str(catalog), "--fc", str(fc), "--out", str(out), "--key", f"erdos:{KEY}"]
    )
    assert code == 0
    assert (out / TARGET_ID / "Statement.lean").is_file(), sorted(p.name for p in out.iterdir())
    return out


def import_draft(tmp_path: Path, out: Path) -> tuple[Path, Path]:
    """Import the draft into a copy of the Mathlib-pinned on-ramp graph, as the wave did.

    The graph is the on-ramp fixture because it is the one fixture whose ``gate-spec.json``
    carries a ``mathlib_sha``; the imported target takes that spec (``intake.spec_for`` varies
    only the id and the pin, D-35), so the sandbox resolves the same Mathlib the image holds.
    """
    root = copy_graph(tmp_path / "graph-parent", ONRAMP, publish=True)
    directory = out / TARGET_ID
    import_fc(
        root,
        target_id=TARGET_ID,
        source=out / "upstream" / REL_PATH,
        rel_path=REL_PATH,
        commit=PIN,
        base=yaml.safe_load((directory / "record.yaml").read_text(encoding="utf-8")),
        witness=(directory / "Witness.lean").read_text(encoding="utf-8"),
        statement=(directory / "Statement.lean").read_text(encoding="utf-8"),
        spec_template=schemas.load_json(
            root / "targets" / ONRAMP_TARGET / "gate-spec.json", "gate-spec/v1"
        ),
    )
    node_dir = root / "targets" / TARGET_ID / "nodes" / TARGET_ID
    assert (node_dir / "Statement.lean").is_file()
    assert "import Mathlib" in (node_dir / "Statement.lean").read_text(encoding="utf-8")
    return root, node_dir


def admit(
    node_dir: Path, image: str, out: Path, capsys: pytest.CaptureFixture[str]
) -> dict[str, Any]:
    from opn_gate import cli  # noqa: PLC0415 — docker-tier only

    capsys.readouterr()  # the wave driver's own report is on stdout already; only admit's is read
    code = cli.main(["admit", str(node_dir), "--sandbox", "--image", image, "--out", str(out)])
    summary: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert (code == 0) is (summary["verdict"] == "pass"), summary
    assert summary["sandboxed"] is True, summary
    return summary


def test_a_drafted_row_is_admitted_in_the_sandbox(
    mathlib_image: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """R13: the root the driver drafted passes every admission check on the Mathlib image."""
    out = draft_one(tmp_path)
    _root, node_dir = import_draft(tmp_path, out)

    summary = admit(node_dir, mathlib_image, tmp_path / "clean", capsys)
    assert summary["verdict"] == "pass", summary
    assert [c["check"] for c in summary["checks"]] == [
        "toolchain",
        "layout",
        "declaration",
        "statement",
        "witness",
        "hazards",
        "context",
        "graph",
        "relation",
    ]
    assert {c["result"] for c in summary["checks"]} == {"pass"}, summary


def test_a_stub_witness_is_refused_by_the_containers_lean(
    mathlib_image: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Wave one's live shape: a witness that is a ``sorry`` is refused at step 7, and the checks
    after it are skipped rather than silently passed."""
    out = draft_one(tmp_path)
    _root, node_dir = import_draft(tmp_path, out)
    (node_dir / "Witness.lean").write_text(STUB_WITNESS, encoding="utf-8")

    summary = admit(node_dir, mathlib_image, tmp_path / "stub", capsys)
    assert summary["verdict"] == "fail", summary
    assert summary["first_failing_check"] == "witness", summary
    assert summary["diagnostic"]["code"] == "witness-sorry", summary
    results = {c["check"]: c["result"] for c in summary["checks"]}
    assert results["statement"] == "pass", summary
    assert results["hazards"] == "skipped", summary
