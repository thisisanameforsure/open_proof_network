"""F01-T1: the Lake package's metaprograms against the golden files (AC11, AC12). Lean tier."""

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

GOLDEN = Path(__file__).resolve().parent / "golden"
NODES = layout.graph_nodes_dir(GRAPH, TARGET)
NODE_IDS = ("tutorial-and-swap", "and-reassoc", "and-swap-reassoc")


class Staged:
    """The fixture in the gate's build layout: ``src/Nodes/<id>/*.lean``, oleans in ``build/``."""

    def __init__(self, root: Path, tc: LocalToolchain, pinned: ResolvedToolchain, bin_dir: Path):
        self.src = root / "src"
        self.build = root / "build"
        self.tc, self.pinned, self.bin = tc, pinned, bin_dir
        for node_id in NODE_IDS:
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

    def run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(self.tc.elan), "run", self.pinned.name, *args],
            cwd=self.src,
            env=self.env(),
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )

    def compile(self, node_id: str, stem: str) -> None:
        rel = Path("Nodes") / node_id / f"{stem}.lean"
        out = self.build / "Nodes" / node_id / f"{stem}.olean"
        proc = self.run("lean", "-o", str(out), str(rel))
        assert proc.returncode == 0, proc.stdout + proc.stderr

    def exe(self, name: str, *args: str) -> tuple[int, dict[str, Any]]:
        proc = self.run(str(self.bin / name), *args)
        assert proc.stdout.strip(), proc.stderr
        return proc.returncode, json.loads(proc.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="module")
def staged(
    tmp_path_factory: pytest.TempPathFactory,
    real_toolchain: LocalToolchain,
    pinned: ResolvedToolchain,
    lean_pkg: Path,
) -> Staged:
    s = Staged(tmp_path_factory.mktemp("staged"), real_toolchain, pinned, lean_pkg)
    # Interior nodes: their own (sorry-free) proofs. Root: Context generated from the dep proofs
    # (F01-Q4 substitution), then the proof.
    for node_id in ("tutorial-and-swap", "and-reassoc"):
        s.compile(node_id, "Context")
        s.compile(node_id, "Proof")
    ctx = s.src / "Nodes" / "and-swap-reassoc" / "Context.lean"
    ctx.write_text(
        "import Nodes.«tutorial-and-swap».Proof\nimport Nodes.«and-reassoc».Proof\n",
        encoding="utf-8",
    )
    s.compile("and-swap-reassoc", "Context")
    return s


def test_witness_type_golden(staged: Staged) -> None:
    """AC11."""
    golden = json.loads((GOLDEN / "witness-types.json").read_text())
    got: dict[str, Any] = {}
    for node_id, entry in golden.items():
        code, doc = staged.exe(
            "opn-witness-type",
            "--statement",
            f"Nodes/{node_id}/Statement.lean",
            "--module",
            layout.node_module(node_id, "Statement"),
            "--decl",
            entry["decl"],
        )
        assert code == 0 and doc["ok"], doc
        got[node_id] = {"decl": entry["decl"], "expected": doc["expected"]}
    assert got == golden


def test_witness_defeq_and_axioms(staged: Staged) -> None:
    code, doc = staged.exe(
        "opn-witness-type",
        "--statement",
        "Nodes/tutorial-and-swap/Statement.lean",
        "--module",
        layout.node_module("tutorial-and-swap", "Statement"),
        "--decl",
        "OpnProp.and_swap",
        "--witness",
        "Nodes/tutorial-and-swap/Witness.lean",
        "--witness-module",
        layout.node_module("tutorial-and-swap", "Witness"),
    )
    assert code == 0 and doc["defeq"] is True and doc["witness_axioms"] == [], doc

    wrong = staged.src / "WrongWitness.lean"
    wrong.write_text("theorem witness : ∃ p : Prop, p := ⟨True, trivial⟩\n", encoding="utf-8")
    code, doc = staged.exe(
        "opn-witness-type",
        "--statement",
        "Nodes/tutorial-and-swap/Statement.lean",
        "--module",
        layout.node_module("tutorial-and-swap", "Statement"),
        "--decl",
        "OpnProp.and_swap",
        "--witness",
        "WrongWitness.lean",
        "--witness-module",
        "Nodes.«tutorial-and-swap».Witness",
    )
    assert code == 0 and doc["defeq"] is False
    assert doc["expected"] == "∃ p q, p ∧ q" and doc["witness"] == "∃ p, p"


def test_used_constants_golden(staged: Staged) -> None:
    """AC12."""
    golden = json.loads((GOLDEN / "used-constants-root.json").read_text())
    code, doc = staged.exe(
        "opn-used-constants",
        "--file",
        "Nodes/and-swap-reassoc/Proof.lean",
        "--module",
        layout.node_module("and-swap-reassoc", "Proof"),
        "--decl",
        "OpnProp.and_swap_reassoc",
    )
    assert code == 0 and doc["ok"], doc
    assert {k: doc[k] for k in ("decl", "axioms", "constants")} == golden
    modules = {c["module"] for c in doc["constants"]}
    assert all(layout.module_origin(m)[0] in ("library", "node") for m in modules)


def test_metaprogram_error_contract(staged: Staged) -> None:
    """R1, R9: non-zero exit and a JSON error document on any failure."""
    broken = staged.src / "Broken.lean"
    broken.write_text("theorem broken : True := (1 : Nat)\n", encoding="utf-8")
    code, doc = staged.exe(
        "opn-used-constants", "--file", "Broken.lean", "--module", "Broken", "--decl", "broken"
    )
    assert code == 1 and doc["ok"] is False
    assert doc["messages"][0]["severity"] == "error"
    code, doc = staged.exe(
        "opn-used-constants", "--file", "nope.lean", "--module", "X", "--decl", "y"
    )
    assert code == 1 and "nope.lean" in doc["error"]
