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


# --- AC10: the skeleton, in partial mode (F11-R8; F07-R5 dispatched in T4) ----------------------

ROOT_NODE = "infinitude-of-primes"
SKELETON = "20260912T000000Z-thisisanameforsure-partial.lean"


def skeleton_run(graph: Path, out: Path, capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    """pregate on the root with its skeleton as the one added assembly."""
    changes = out.parent / "changes.txt"
    code = cli.main(
        ["pregate", "--graph", str(graph), "--node", ROOT_NODE, "--no-diff", "--out", str(out)]
    )
    captured = capsys.readouterr()
    assert code == cli.EXIT_PASS, captured.err[-3000:] + captured.out[-4000:]
    del changes
    doc: dict[str, object] = json.loads(captured.out)
    return doc


def assert_skeleton_verdict(verdict: dict[str, object]) -> None:
    steps = verdict["steps"]
    assert isinstance(steps, list)
    assert [(s["step"], s["result"]) for s in steps] == [
        (1, "pass"),
        (2, "pass"),
        (4, "pass"),
        (5, "pass"),
        (6, "pass"),
        (7, "pass"),
        (8, "pass"),
    ]
    assert steps[1]["diagnostic"]["code"] == "partial-submission"
    assert steps[1]["diagnostic"]["details"]["path"] == f"attempts/{SKELETON}"
    step4 = steps[2]["diagnostic"]
    assert step4["code"] == "artifact-partial", step4
    assert step4["details"]["holes"] == ["dvd_fact", "prime_divisor", "dvd_consecutive"]
    artifact = verdict.get("artifact") or {}
    holes = artifact.get("holes") if isinstance(artifact, dict) else None
    if holes:  # the printed summary carries them when the run does
        assert all(not h["defeq_goal"] for h in holes)


def test_skeleton_admits(
    tmp_path: Path,
    lean_pkg: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC10: on the pinned Mathlib, pregate in partial mode on the root passes — the assembly
    typechecks modulo its three named holes, each extracted, none definitionally the root — with
    the annex citation making them skeleton holes when merged (F07-R6)."""
    monkeypatch.setenv("OPN_LEAN_PKG_BIN", str(lean_pkg))
    verdict = skeleton_run(ONRAMP, tmp_path / "out", capsys)
    assert_skeleton_verdict(verdict)
    step1 = verdict["steps"][0]["diagnostic"]  # type: ignore[index]
    assert step1["code"] == "mathlib-pinned" and step1["details"]["mathlib_sha"] == ONRAMP_MATHLIB


def test_skeleton_mechanics_without_mathlib(
    tmp_path: Path,
    lean_pkg: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The same skeleton on a Mathlib-free copy of the fixture: the root's statement and the
    assembly use Lean core only, so the partial dispatch — staging, replay through the holes,
    extraction, the offload rule — is proved on a laptop that holds no Mathlib checkout, and
    the pinned run above adds only the pin. The proved lemma's Mathlib import and tactic are
    swapped for Lean core in the copy, so the root's dependency is still proved."""
    import shutil  # noqa: PLC0415

    monkeypatch.setenv("OPN_LEAN_PKG_BIN", str(lean_pkg))
    graph = tmp_path / "graph"
    shutil.copytree(ONRAMP, graph)
    spec_path = graph / "targets" / ONRAMP_TARGET / "gate-spec.json"
    spec = schemas.load_json(spec_path, "gate-spec/v1")
    spec["mathlib_sha"] = None
    spec_path.write_bytes(schemas.canonical_json(spec))
    proved = graph / "targets" / ONRAMP_TARGET / "nodes" / "fact-pos"
    statement = (proved / "Statement.lean").read_text(encoding="utf-8")
    statement = statement.replace("import Mathlib.Tactic.Linarith\n", "")
    (proved / "Statement.lean").write_text(statement, encoding="utf-8")
    head, _, _ = statement.partition(":= by\n  sorry")
    (proved / "Proof.lean").write_text(
        head + ":= by\n  intro n\n  induction n with\n  | zero => simp [Opn.fact]\n"
        "  | succ n ih =>\n    simp only [Opn.fact]\n    exact Nat.mul_pos (Nat.succ_pos n) ih\n",
        encoding="utf-8",
    )
    import hashlib  # noqa: PLC0415
    import re  # noqa: PLC0415

    meta = proved / "META.yaml"
    digest = hashlib.sha256((proved / "Statement.lean").read_bytes()).hexdigest()
    meta.write_text(
        re.sub(r"statement-hash: [0-9a-f]+", f"statement-hash: {digest}", meta.read_text())
    )
    verdict = skeleton_run(graph, tmp_path / "out", capsys)
    assert_skeleton_verdict(verdict)
    assert verdict["steps"][0]["diagnostic"] is None  # type: ignore[index]
