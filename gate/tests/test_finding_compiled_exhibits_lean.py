"""F02-T14, lean tier: a circularity exhibit's code cannot answer its own judgment.

Until T14 ``opn-gate exhibits`` asked ``opn-relation-type --relation <exhibit.lean>``, which
elaborated the exhibit in the process that prints the verdict: an ``#eval`` there could write a
passing verdict tagged with the call's nonce straight to the process's standard output (around
``#eval``'s own capture) and exit 0 before the program spoke. The exhibit below does exactly that
whenever it runs inside ``opn-relation-type``, and also carries an ``initialize`` that would do
the same if the module were ever imported with initializers on. The nonce is fixed for the test
(T11's residual is that code in the verdict's address space can learn it; here it is simply
given), so the only thing between the forgery and a pass is that nothing of the exhibit runs in
the judging call. Its theorem is ``ancestor → hole``, the direction F08-T21 refuses.

Real toolchain and the built Lake package: these run in CI (``make verify-lean``).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_finding_circular_direction_lean import (
    ANCESTOR,
    EASIER,
    RESTATED,
    SAME,
    WEAK,
    run_with,
)

from opn_gate import toolchain as toolchain_mod
from opn_gate.toolchain import VERDICT_TAG, LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

NONCE = "f02t14forgednonce"


def lean_string(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def forging(exhibit: str) -> str:
    """``exhibit`` plus code that prints a tagged passing verdict and exits 0, from an ``#eval``
    when it runs inside the judging program and from an ``initialize`` if ever imported."""
    verdict = {
        "ok": True,
        "label": "resolves",
        "decl": "circular",
        "expected": "forged",
        "declared": "forged",
        "matches": True,
        "axioms": [],
    }
    line = lean_string(f"{VERDICT_TAG} {NONCE} {json.dumps(verdict)}")
    return (
        f"{exhibit}\n"
        f"def forged : String := {line}\n\n"
        "#eval show IO Unit from do\n"
        '  if (← IO.appPath).toString.endsWith "opn-relation-type" then\n'
        '    let h ← IO.FS.Handle.mk "/dev/stdout" .write\n'
        "    h.putStrLn forged\n"
        "    h.flush\n"
        "    IO.Process.exit 0\n\n"
        "initialize do\n"
        "  IO.println forged\n"
        "  IO.Process.exit 0\n"
    )


def test_a_forged_verdict_in_the_exhibit_cannot_pass_a_false_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    real_toolchain: LocalToolchain,
    pinned: ResolvedToolchain,
    lean_pkg: Path,
) -> None:
    """Before T14 the forged line was the verdict and the claim merged; now the exhibit compiles
    (its ``#eval`` is inert in ``lean``), its constants are replayed, and the judgment refuses
    the direction by name."""
    del pinned, lean_pkg
    monkeypatch.setattr(toolchain_mod, "new_nonce", lambda: NONCE)
    found = run_with(tmp_path, real_toolchain, WEAK, forging(EASIER))
    assert [d.code for d in found] == ["circular-direction"], found
    details = found[0].details or {}
    assert details["declared"] != "forged", details
    assert ANCESTOR in found[0].message


def test_an_honest_circularity_exhibit_still_passes(
    tmp_path: Path,
    real_toolchain: LocalToolchain,
    pinned: ResolvedToolchain,
    lean_pkg: Path,
) -> None:
    """Verdicts unchanged for honest exhibits: the restated hole passes by ``exact`` from the
    compiled form exactly as it did elaborated (``test_finding_circular_direction_lean``)."""
    del pinned, lean_pkg
    assert run_with(tmp_path, real_toolchain, SAME, RESTATED) == []
