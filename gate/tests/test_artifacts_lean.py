"""F07-T2 / AC20: ``opn-artifact-type`` against the real toolchain, pinned to a golden.

The fast tier decides what the gate does with the metaprogram's answer; only this tier proves the
answer is right. Every fixture under ``fixtures/artifacts/`` is run against the tutorial node's
statement and compared with ``golden/artifact-types.json`` — so a change in Lean's elaboration,
or in the extractor, shows up as a diff rather than as a silently different verdict.

Regenerate the golden after an intended change with (elan and a built Lake package needed)

    PYTHONPATH=gate uv run python -c "import sys; sys.path.insert(0, 'gate/tests'); \
        import test_artifacts_lean as t; t.write_golden()"

and review the diff before committing it with the task that caused it.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from harness import GRAPH, TARGET

from opn_gate import layout
from opn_gate.steps import artifact as art
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "artifacts"
GOLDEN = Path(__file__).resolve().parent / "golden" / "artifact-types.json"
NODE = "tutorial-and-swap"
STATEMENT_DECL = "OpnProp.and_swap"

#: fixture stem -> the artifact kind it is submitted as.
CASES: dict[str, art.Kind] = {
    "Proof": "proof",
    "Refuted": "counterexample",
    "RefutedWrong": "counterexample",
    "Vacuous": "vacuity",
    "VacuousWrong": "vacuity",
    "Partial": "partial",
    "Reduction": "reduction",
    "Offload": "partial",
    "RestateConclusion": "partial",
    "BareHole": "partial",
}


class Bench:
    """The statement and the artifacts side by side, in a directory the metaprogram can read."""

    def __init__(self, root: Path, tc: LocalToolchain, pinned: ResolvedToolchain, bin_dir: Path):
        self.root = root
        self.tc, self.pinned, self.bin = tc, pinned, bin_dir
        node = layout.graph_nodes_dir(GRAPH, TARGET) / NODE
        shutil.copy(node / "Statement.lean", root / "Statement.lean")
        for lean in FIXTURES.glob("*.lean"):
            shutil.copy(lean, root / lean.name)

    def run(self, stem: str, kind: art.Kind) -> dict[str, Any]:
        sysroot = self.pinned.libdir.parent.parent
        req = [
            "--statement",
            str(self.root / "Statement.lean"),
            "--module",
            layout.node_module(NODE, "Statement"),
            "--decl",
            STATEMENT_DECL,
            "--artifact",
            str(self.root / f"{stem}.lean"),
            "--artifact-module",
            f"Artifacts.{stem}",
            "--artifact-decl",
            art.expected_decl(kind, STATEMENT_DECL),
            "--kind",
            kind,
        ]
        proc = subprocess.run(
            [str(self.tc.elan), "run", self.pinned.name, str(self.bin / "opn-artifact-type"), *req],
            cwd=self.root,
            env={
                "LEAN_PATH": str(self.pinned.libdir),
                "LEAN_SYSROOT": str(sysroot),
                "ELAN_HOME": str(self.tc.elan.parent.parent),
                "PATH": f"{sysroot / 'bin'}:/usr/bin:/bin",
                "HOME": str(self.root),
            },
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )
        assert proc.stdout.strip(), proc.stderr
        doc: dict[str, Any] = json.loads(proc.stdout.strip().splitlines()[-1])
        assert doc["ok"], doc
        return doc


@pytest.fixture(scope="module")
def bench(
    tmp_path_factory: pytest.TempPathFactory,
    real_toolchain: LocalToolchain,
    pinned: ResolvedToolchain,
    lean_pkg: Path,
) -> Bench:
    return Bench(tmp_path_factory.mktemp("artifacts"), real_toolchain, pinned, lean_pkg)


def observed(bench: Bench) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for stem, kind in CASES.items():
        doc = bench.run(stem, kind)
        parsed = art.Artifact.of(kind, doc)
        out[stem] = {
            **parsed.as_dict(),
            "problems": [d.code for d in art.check(parsed)],
        }
    return out


def test_artifact_types_golden(bench: Bench) -> None:
    """AC20: every fixture's type, holes and verdict, byte for byte against the golden."""
    assert observed(bench) == json.loads(GOLDEN.read_text(encoding="utf-8"))


def write_golden() -> None:
    """Regenerate ``golden/artifact-types.json`` (see the module docstring)."""
    import tempfile  # noqa: PLC0415 — only the regeneration path needs it

    from opn_gate import config  # noqa: PLC0415

    settings = config.load()
    tc = LocalToolchain.from_settings(settings)
    root = Path(__file__).resolve().parents[2]
    pinned = tc.resolve((root / "lean-toolchain").read_text().strip(), install=False)
    with tempfile.TemporaryDirectory(prefix="opn-artifacts-") as tmp:
        bench = Bench(Path(tmp), tc, pinned, settings.lean_pkg_bin)
        got = observed(bench)
    GOLDEN.write_text(json.dumps(got, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def test_the_golden_says_what_the_rules_say(bench: Bench) -> None:
    """The golden is only worth having if it encodes the rules: read them back out of it.

    AC4, AC5 and AC6 are asserted in the fast tier against the fake; this is the same set of
    claims against the real elaborator, which is the point of the tier (conventions §2).
    """
    got = observed(bench)
    assert got["Proof"]["matches"] and got["Proof"]["problems"] == []
    assert got["Refuted"]["matches"] and got["Refuted"]["problems"] == []
    assert not got["RefutedWrong"]["matches"]
    assert got["RefutedWrong"]["problems"] == ["artifact-type-mismatch"]
    assert got["Vacuous"]["matches"] and got["Vacuous"]["problems"] == []
    assert not got["VacuousWrong"]["matches"]

    partial = got["Partial"]
    assert partial["matches"] and partial["problems"] == []
    assert [(h["name"], h["type"]) for h in partial["holes"]] == [("right", "q"), ("left", "p")]
    assert not any(h["defeq_goal"] for h in partial["holes"])

    assert got["Reduction"]["reduction"] and got["Reduction"]["problems"] == []
    assert "offload-restated-goal" in got["Offload"]["problems"]
    assert "offload-restated-goal" in got["RestateConclusion"]["problems"]
    assert "offload-whole-goal" in got["BareHole"]["problems"]
