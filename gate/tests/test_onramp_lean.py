"""F11-T3 / R6 with the real toolchain and the pinned Mathlib checkout (lean tier): the on-ramp
fixture's proved node passes the whole pipeline with Mathlib resolved from OPN_MATHLIB_HOME —
step 1 reports the pin, the definitions build before the node, the proof's `nlinarith` runs on
Mathlib's oleans — and the attestation records the sha and nothing about where it was.

Needs the checkout ``gate/scripts/install-mathlib.sh <sha>`` makes (the commit is the first line
of gate/mathlib-pins.txt); without it step 1 fails naming that script, which is the failure this
test then reports. F11-T4's skeleton criterion (AC10) is added here when the skeleton exists.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from conftest import ONRAMP, ONRAMP_MATHLIB, ONRAMP_TARGET

from opn_gate import cli, schemas

pytestmark = pytest.mark.lean

PROVED = "fact-pos"


def test_the_on_ramp_node_passes_on_the_pinned_mathlib(
    tmp_path: Path,
    lean_pkg: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("OPN_LEAN_PKG_BIN", str(lean_pkg))
    out = tmp_path / "out"
    started = time.monotonic()
    code = cli.main(
        ["pregate", "--graph", str(ONRAMP), "--node", PROVED, "--no-diff", "--out", str(out)]
    )
    elapsed = time.monotonic() - started
    captured = capsys.readouterr()
    assert code == cli.EXIT_PASS, captured.err[-3000:] + captured.out[-3000:]
    verdict = json.loads(captured.out)
    assert verdict["verdict"] == "pass"
    assert [(s["step"], s["result"]) for s in verdict["steps"]] == [
        (1, "pass"),
        (2, "pass"),
        (4, "pass"),
        (5, "pass"),
        (6, "pass"),
        (7, "pass"),
        (8, "pass"),
    ]
    step1 = verdict["steps"][0]["diagnostic"]
    assert step1["code"] == "mathlib-pinned"
    assert step1["details"]["mathlib_sha"] == ONRAMP_MATHLIB
    assert step1["details"]["packages"] >= 2  # Mathlib and at least one of its packages
    assert "/" not in json.dumps(step1)  # the record names the pin, never this host's path

    attestation = schemas.load_json(out / "attestation.json")
    assert attestation["mathlib_sha"] == ONRAMP_MATHLIB
    assert attestation["graph_id"] == ONRAMP_TARGET and attestation["verdict"] == "pass"
    assert schemas.violations(attestation) == []
    # The definitions were built first, under Defs/, and the proof's Mathlib import resolved.
    build = out / "work" / "build"
    assert (build / "Defs" / "Fact.olean").is_file()
    assert (build / "Nodes" / PROVED / "Proof.olean").is_file()
    print(f"F11 §6: pregate on {PROVED} with the pinned Mathlib in {elapsed:.1f}s")
    assert elapsed < 600  # §6: under ten minutes; the docker tier measures the image
