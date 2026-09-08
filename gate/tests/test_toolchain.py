"""F00-T2: the Toolchain seam, fast tier (R16, AC20)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from fakes import FakeToolchain

from opn_gate import toolchain
from opn_gate.toolchain import ResolvedToolchain, ToolchainMissingError

ROOT = Path(__file__).resolve().parents[2]


def test_missing_toolchain_diagnostic(tmp_path: Path) -> None:
    """AC20: with no elan on PATH the diagnostic names the install script."""
    with pytest.raises(ToolchainMissingError) as info:
        toolchain.find_elan(path_env=str(tmp_path), elan_home=tmp_path / "no-elan")
    assert "gate/scripts/install-toolchain.sh" in str(info.value)
    assert (ROOT / "gate/scripts/install-toolchain.sh").is_file()


def test_require_entrypoint_fails_without_elan(tmp_path: Path) -> None:
    """`make verify-lean` calls this first; it must exit 1 naming the script (R16)."""
    proc = subprocess.run(
        [sys.executable, "-m", "opn_gate.toolchain", "--require"],
        env={"PATH": str(tmp_path), "OPN_ELAN_HOME": str(tmp_path / "nope"), "HOME": str(tmp_path)},
        cwd=ROOT / "gate",
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "gate/scripts/install-toolchain.sh" in proc.stderr


def test_find_elan_under_elan_home(tmp_path: Path) -> None:
    fake = tmp_path / "bin" / "elan"
    fake.parent.mkdir()
    fake.write_text("#!/bin/sh\n")
    assert toolchain.find_elan(path_env=str(tmp_path), elan_home=tmp_path) == fake


def test_toolchain_hash_is_platform_independent() -> None:
    a = ResolvedToolchain("leanprover/lean4:v4.33.1", "4.33.1", "abc", Path("/mac/lib"))
    b = ResolvedToolchain("leanprover/lean4:v4.33.1", "4.33.1", "abc", Path("/linux/lib"))
    assert a.toolchain_hash == b.toolchain_hash
    c = ResolvedToolchain("leanprover/lean4:v4.33.1", "4.33.1", "abd", Path("/mac/lib"))
    assert a.toolchain_hash != c.toolchain_hash


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        ("'T.x' depends on axioms: [propext, Classical.choice]\n", {"propext", "Classical.choice"}),
        ("'T.x' does not depend on any axioms\n", set()),
        ("warning: foo\n'T.x' depends on axioms: [sorryAx]\n", {"sorryAx"}),
        ("'Other' depends on axioms: [sorryAx]\n", None),
    ],
)
def test_parse_axioms(output: str, expected: set[str] | None) -> None:
    got = toolchain.parse_axioms(output, "T.x")
    assert (got if got is None else set(got)) == expected


def test_native_decide_axiom_detected() -> None:
    assert toolchain.is_native_decide_axiom("t._native.native_decide.ax_1_1")
    assert toolchain.is_native_decide_axiom("Lean.ofReduceBool")
    assert not toolchain.is_native_decide_axiom("propext")


def test_parse_json_messages_skips_noise() -> None:
    raw = (
        "not json\n"
        '{"fileName":"S.lean","pos":{"line":1,"column":8},"severity":"warning",'
        '"data":"declaration uses `sorry`"}\n'
    )
    msgs = toolchain.parse_json_messages(raw)
    assert len(msgs) == 1
    assert msgs[0].line == 1 and msgs[0].severity == "warning"
    assert "sorry" in msgs[0].text


def test_fake_toolchain_records_calls(tmp_path: Path) -> None:
    fake = FakeToolchain()
    tc = fake.resolve("leanprover/lean4:v4.33.1")
    assert fake.elaborate(tc, tmp_path / "Proof.lean", "Proof", tmp_path / "out").ok
    assert (tmp_path / "out" / "Proof.olean").exists()
    assert fake.calls == ["resolve:leanprover/lean4:v4.33.1:install=False", "elaborate:Proof"]


def test_parse_metaprogram_output_contract() -> None:
    """F01-R1/R9: the last stdout line is the JSON verdict; anything else is a failure."""
    ok = toolchain.parse_metaprogram_output(0, 'noise\n{"ok": true, "expected": "True"}\n', "")
    assert ok.ok and ok.doc["expected"] == "True" and ok.error is None
    failed = toolchain.parse_metaprogram_output(1, '{"ok": false, "error": "boom"}\n', "")
    assert not failed.ok and failed.error == "boom" and failed.doc
    garbage = toolchain.parse_metaprogram_output(1, "Segmentation fault", "core dumped")
    assert not garbage.ok and garbage.doc == {} and garbage.exit_code == 1
    assert "Segmentation fault" in garbage.output and "core dumped" in garbage.output
    huge = toolchain.parse_metaprogram_output(2, "x" * 100_000, "")
    assert len(huge.output) == toolchain.METAPROGRAM_OUTPUT_CAP
    lying = toolchain.parse_metaprogram_output(3, '{"ok": true}', "")
    assert not lying.ok  # a non-zero exit is never a pass


def test_metaprogram_path_requires_built_package(tmp_path: Path) -> None:
    lt = toolchain.LocalToolchain(tmp_path / "elan", lean_pkg_bin=tmp_path / "bin")
    with pytest.raises(ToolchainMissingError, match="lake build"):
        lt.metaprogram("opn-witness-type")
