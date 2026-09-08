"""F02-T1/T2: ``opn-hazards`` against the hazard fixtures (AC10, AC11, AC12). Lean tier."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from harness import GRAPH, TARGET

from opn_gate import layout
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

HAZARDS = Path(__file__).resolve().parent / "fixtures" / "hazards"
EXPECTED: dict[str, Any] = json.loads((HAZARDS / "expected.json").read_text())
NODES = layout.graph_nodes_dir(GRAPH, TARGET)
NODE_DECLS = {
    "tutorial-and-swap": "OpnProp.and_swap",
    "and-reassoc": "OpnProp.and_reassoc",
    "and-swap-reassoc": "OpnProp.and_swap_reassoc",
}


class Runner:
    """``opn-hazards`` under the pinned toolchain, with the fixture graph staged for AC11."""

    def __init__(self, root: Path, tc: LocalToolchain, pinned: ResolvedToolchain, bin_dir: Path):
        self.src = root / "src"
        self.build = root / "build"
        self.tc, self.pinned, self.bin = tc, pinned, bin_dir
        for node_id in NODE_DECLS:
            dest = self.src / "Nodes" / node_id
            dest.mkdir(parents=True)
            for f in (NODES / node_id).glob("*.lean"):
                shutil.copy(f, dest / f.name)
            (self.build / "Nodes" / node_id).mkdir(parents=True)

    def env(self) -> dict[str, str]:
        sysroot = self.pinned.libdir.parent.parent
        return {
            "LEAN_PATH": f"{self.build}:{self.pinned.libdir}",
            "LEAN_SYSROOT": str(sysroot),
            "ELAN_HOME": str(self.tc.elan.parent.parent),
            "PATH": f"{sysroot / 'bin'}:/usr/bin:/bin",
            "HOME": str(self.src.parent),
        }

    def run(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(self.tc.elan), "run", self.pinned.name, *args],
            cwd=cwd or self.src,
            env=self.env(),
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )

    def compile_context(self, node_id: str) -> None:
        rel = Path("Nodes") / node_id / "Context.lean"
        out = self.build / "Nodes" / node_id / "Context.olean"
        proc = self.run("lean", "-o", str(out), str(rel))
        assert proc.returncode == 0, proc.stdout + proc.stderr

    def hazards(self, *args: str, cwd: Path | None = None) -> tuple[int, dict[str, Any]]:
        proc = self.run(str(self.bin / "opn-hazards"), *args, cwd=cwd)
        assert proc.stdout.strip(), proc.stderr
        return proc.returncode, json.loads(proc.stdout.strip().splitlines()[-1])

    def all_checkers(self) -> list[str]:
        code, doc = self.hazards("--list")
        assert code == 0 and doc["ok"], doc
        return [c["id"] for c in doc["checkers"]]

    def on_fixture(self, stem: str, checkers: list[str]) -> tuple[int, dict[str, Any]]:
        return self.hazards(*fixture_args(stem, checkers), cwd=HAZARDS)


EXTRA_DECLS = {"Clean": "OpnHazard.clean", "NegLiteral": "OpnHazard.neg_literal"}


def fixture_args(stem: str, checkers: list[str]) -> tuple[str, ...]:
    decl = EXPECTED[stem]["decl"] if stem in EXPECTED else EXTRA_DECLS[stem]
    return (
        "--statement",
        f"{stem}.lean",
        "--module",
        f"Hazards.{stem}",
        "--decl",
        decl,
        "--checkers",
        ",".join(checkers),
    )


@pytest.fixture(scope="module")
def runner(
    tmp_path_factory: pytest.TempPathFactory,
    real_toolchain: LocalToolchain,
    pinned: ResolvedToolchain,
    lean_pkg: Path,
) -> Runner:
    r = Runner(tmp_path_factory.mktemp("hazards"), real_toolchain, pinned, lean_pkg)
    for node_id in NODE_DECLS:
        r.compile_context(node_id)
    return r


def test_registry_lists_shipped_checkers(runner: Runner) -> None:
    """R1: the executable names its checkers; the fixtures cover every one of them."""
    ids = runner.all_checkers()
    assert ids == sorted(ids) and len(ids) == len(set(ids))
    assert {EXPECTED[stem]["finding"]["checker"] for stem in EXPECTED} == set(ids)


def test_each_checker_fires_once(runner: Runner) -> None:
    """AC10: each fixture yields exactly its expected finding and no other, all checkers on."""
    checkers = runner.all_checkers()
    for stem, entry in EXPECTED.items():
        code, doc = runner.on_fixture(stem, checkers)
        assert code == 0 and doc["ok"], (stem, doc)
        assert doc["checkers"] == checkers and doc["capped"] is False
        got = [{"checker": f["checker"], "location": f["location"]} for f in doc["findings"]]
        assert got == [entry["finding"]], (stem, doc["findings"])
        assert all(f["message"] for f in doc["findings"])


def test_clean_statements_no_findings(runner: Runner) -> None:
    """AC11: the propositional fixture statements, and Clean.lean, produce no findings."""
    checkers = runner.all_checkers()
    for node_id, decl in NODE_DECLS.items():
        code, doc = runner.hazards(
            "--statement",
            f"Nodes/{node_id}/Statement.lean",
            "--module",
            layout.node_module(node_id, "Statement"),
            "--decl",
            decl,
            "--checkers",
            ",".join(checkers),
        )
        assert code == 0 and doc["ok"] and doc["findings"] == [], (node_id, doc)
    code, doc = runner.on_fixture("Clean", checkers)
    assert code == 0 and doc["ok"] and doc["findings"] == [], doc


def test_deterministic(runner: Runner) -> None:
    """AC12: two runs over any fixture print byte-identical output."""
    checkers = runner.all_checkers()
    for stem in (*EXPECTED, *EXTRA_DECLS):
        args = fixture_args(stem, checkers)
        first = runner.run(str(runner.bin / "opn-hazards"), *args, cwd=HAZARDS)
        second = runner.run(str(runner.bin / "opn-hazards"), *args, cwd=HAZARDS)
        assert first.returncode == 0 and first.stdout == second.stdout, (stem, first.stderr)


def test_unknown_checker_rejected(runner: Runner) -> None:
    """R3's Lean half: an unknown id is refused before the statement is elaborated."""
    code, doc = runner.on_fixture("NatSub", ["nat-sub", "bogus"])
    assert code == 1 and doc["ok"] is False
    assert "bogus" in doc["error"] and doc["known"] == runner.all_checkers()


def test_only_named_checkers_run(runner: Runner) -> None:
    """R3: exactly the listed checkers run — nat-sub alone sees nothing in DivZero.lean."""
    code, doc = runner.on_fixture("DivZero", ["nat-sub"])
    assert code == 0 and doc["checkers"] == ["nat-sub"] and doc["findings"] == [], doc
    code, doc = runner.on_fixture("DivZero", [])
    assert code == 0 and doc["checkers"] == [] and doc["findings"] == [], doc


def test_negative_literal_divisor(runner: Runner) -> None:
    """R2: `-3` is syntactically non-zero for div-zero; the same Int division is an int-trunc."""
    code, doc = runner.on_fixture("NegLiteral", ["div-zero"])
    assert code == 0 and doc["findings"] == [], doc
    code, doc = runner.on_fixture("NegLiteral", ["int-trunc"])
    assert code == 0 and [f["checker"] for f in doc["findings"]] == ["int-trunc"], doc
