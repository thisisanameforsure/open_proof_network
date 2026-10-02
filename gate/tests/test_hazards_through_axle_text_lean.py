"""F13-T20, lean tier: the text the service composes for the hazard pre-flight and ``mode:
"hazards"`` finds exactly what step 6's ``opn-hazards`` finds, finding for finding.

The fast tier (``api/tests/test_finding_hazards_preflight.py``) pins what is sent and how the
answer is read. Whether what is sent *is* the gate's checker is Lean's to say: the checker files
pasted after a statement, the registry, a ``run_meta`` block, a JSON line. The locations must be
byte-identical, because an acknowledgment is matched to a finding on its printed location (F02-Q4),
so a pre-flight that printed ``a / b`` where the gate prints ``a / b`` differently would refuse a
proposal the gate would pass. Run on every statement ``test_hazards_lean.py`` gives ``opn-hazards``:
each fixture, the clean ones, and the fixture graph's nodes with their Context inlined as the
service inlines it.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
from test_hazards_lean import (
    EXPECTED,
    EXTRA_DECLS,
    HAZARDS,
    NODE_DECLS,
    NODES,
    Runner,
    fixture_args,
    runner,  # noqa: F401 — the module-scoped fixture, shared with the opn-hazards tests
)

from opn_api import checks
from opn_gate import layout
from opn_gate.toolchain import ResolvedToolchain

pytestmark = pytest.mark.lean

ROOT = Path(__file__).resolve().parents[2]


#: F13-T26: the toolchain modules the hosted checker's environment holds, one measured list per
#: environment (``gate/hosted-checker-modules/``). AXLE replaces a text's header with its own,
#: ``import Mathlib``, which reaches these and no other module of ``Lean``.
HOSTED_MODULES = ROOT / "gate" / "hosted-checker-modules" / "lean-4.33.1.txt"


def hosted_header() -> str:
    """The hosted environment's share of the toolchain, as an import block: what stands in for
    ``import Mathlib`` on a machine with no Mathlib."""
    modules = [
        line.strip()
        for line in HOSTED_MODULES.read_text("utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    assert "Lean.Elab.Command" in modules and "Lean.Elab.Frontend" not in modules
    return "".join(f"import {m}\n" for m in modules)


def as_the_hosted_checker_reads_it(text: str) -> str:
    """``text`` with its ``import Lean`` replaced by the hosted environment's modules. The
    composer writes ``import Lean`` and the hosted checker never honours it (2026-10-01: the
    program named ``Lean.Elab.IO.processCommands``, green here under ``import Lean`` and an
    unknown identifier on every live call)."""
    assert text.count("import Lean\n") == 1, "the composed text carries one `import Lean` line"
    return text.replace("import Lean\n", hosted_header(), 1)


def through_the_service(pinned: ResolvedToolchain, tmp_path: Path, text: str) -> dict[str, Any]:
    """Elaborate the composed text as the hosted checker would — under the modules its
    environment holds, not under ``import Lean`` (F13-T26) — and read its line back the way the
    service reads the checker's info messages."""
    source = tmp_path / "Hazards.lean"
    source.write_text(as_the_hosted_checker_reads_it(text), encoding="utf-8")
    lean = pinned.libdir.parent.parent / "bin" / "lean"
    proc = subprocess.run(
        [str(lean), str(source)], capture_output=True, text=True, check=False, timeout=600
    )
    # Lean prints an error as ``error:`` or ``error(<kind>):``; the old ``": error:"`` saw
    # only the first, and an unknown identifier is the second (F13-T26).
    assert not re.search(r": error(\([^)]*\))?:", proc.stdout), proc.stdout
    verdict = checks.hazards_verdict({"lean_messages": {"infos": proc.stdout.splitlines()}})
    assert verdict is not None, proc.stdout
    return verdict


def node_text(node_id: str) -> str:
    """A fixture node's statement with its own Context inlined, as ``checks.inline_defs`` and
    ``forwarded_text`` do for a node on the graph."""
    statement = (NODES / node_id / "Statement.lean").read_text("utf-8")
    context = (NODES / node_id / "Context.lean").read_text("utf-8")
    own = layout.node_module(node_id, "Context")
    defs = [(own, checks.IMPORT_LINE_RE.sub("", context).strip("\n"))]
    return checks.forwarded_text(statement, defs)


def test_the_composed_text_finds_what_opn_hazards_finds(
    runner: Runner,  # noqa: F811 — the imported fixture
    pinned: ResolvedToolchain,
    tmp_path: Path,
) -> None:
    checkers = runner.all_checkers()
    for stem in (*EXPECTED, *EXTRA_DECLS):
        code, gate = runner.on_fixture(stem, checkers)
        assert code == 0 and gate["ok"], (stem, gate)
        decl = fixture_args(stem, checkers)[5]
        text = checks.hazards_text((HAZARDS / f"{stem}.lean").read_text("utf-8"), decl, checkers)
        service = through_the_service(pinned, tmp_path, text)
        assert service == {
            "checkers": gate["checkers"],
            "findings": gate["findings"],
            "capped": gate["capped"],
        }, stem


def test_the_nodes_with_their_context_inlined_agree(
    runner: Runner,  # noqa: F811 — the imported fixture
    pinned: ResolvedToolchain,
    tmp_path: Path,
) -> None:
    checkers = runner.all_checkers()
    for node_id, decl in NODE_DECLS.items():
        code, gate = runner.hazards(
            "--statement",
            f"Nodes/{node_id}/Statement.lean",
            "--module",
            layout.node_module(node_id, "Statement"),
            "--decl",
            decl,
            "--checkers",
            ",".join(checkers),
        )
        assert code == 0 and gate["ok"], (node_id, gate)
        statement = (NODES / node_id / "Statement.lean").read_text("utf-8")
        service = through_the_service(
            pinned,
            tmp_path,
            checks.hazards_text(node_text(node_id), decl, checkers, statement=statement),
        )
        assert service["findings"] == gate["findings"], node_id


def test_only_the_named_checkers_run(pinned: ResolvedToolchain, tmp_path: Path) -> None:
    """As ``test_hazards_lean.test_only_named_checkers_run``: nat-sub alone sees nothing in
    DivZero.lean, and no checker at all is an empty answer, not an error."""
    source = (HAZARDS / "DivZero.lean").read_text("utf-8")
    decl = EXPECTED["DivZero"]["decl"]
    alone = through_the_service(pinned, tmp_path, checks.hazards_text(source, decl, ["nat-sub"]))
    assert alone == {"checkers": ["nat-sub"], "findings": [], "capped": False}
    none = through_the_service(pinned, tmp_path, checks.hazards_text(source, decl, []))
    assert none == {"checkers": [], "findings": [], "capped": False}
