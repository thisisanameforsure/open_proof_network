"""F00-T2: the Toolchain seam, fast tier (R16, AC20)."""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Sequence
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


def test_require_entrypoint_usage() -> None:
    assert toolchain.main(["--bogus"]) == 2
    assert toolchain.main([]) == 2


@pytest.mark.parametrize(
    "stdout",
    ['{"expected": "True"}\n', "[1, 2]\n", "", "null\n", '"ok"\n', '{"ok": true}\nnot json\n'],
)
def test_metaprogram_output_without_a_verdict_is_a_failure(stdout: str) -> None:
    """F01-R9: a JSON document without `ok`, a non-object, an empty stdout, or a trailing
    non-JSON line all break the contract, whatever the exit code says."""
    result = toolchain.parse_metaprogram_output(0, stdout, "stderr text")
    assert not result.ok and result.doc == {} and result.exit_code == 0
    assert result.output == (stdout + "stderr text")[: toolchain.METAPROGRAM_OUTPUT_CAP]
    assert result.error is None and result.messages == ()


def test_metaprogram_messages_are_read_defensively() -> None:
    doc = {"ok": False, "error": 7, "messages": ["junk", {"text": "t"}, {"line": "3"}]}
    result = toolchain.MetaprogramResult(ok=False, doc=doc, exit_code=1)
    assert result.error == "7"
    assert [(m.line, m.severity, m.text) for m in result.messages] == [
        (0, "error", "t"),
        (3, "error", ""),
    ]


def test_parse_json_messages_skips_broken_json() -> None:
    raw = '{"fileName": "S.lean", "pos": {"line": 1}, "severity": "error", "data": "x"\n{"ok"\n'
    assert toolchain.parse_json_messages(raw) == ()
    raw = '{"severity": "error", "data": "no pos"}\n'
    msgs = toolchain.parse_json_messages(raw)
    assert msgs[0].line == 0 and msgs[0].file == ""


def test_parse_axioms_empty_list_and_module_paths() -> None:
    assert toolchain.parse_axioms("'T.x' depends on axioms: []\n", "T.x") == frozenset()
    assert toolchain.parse_axioms("", "T.x") is None
    assert toolchain.module_output_path("Nodes.«a-b».Proof", ".olean") == Path(
        "Nodes/a-b/Proof.olean"
    )
    assert toolchain.module_output_path("Nodes.«a.b».Proof", ".ilean") == Path(
        "Nodes/a.b/Proof.ilean"
    )
    assert toolchain.module_output_path("Proof", ".olean") == Path("Proof.olean")


# --- the real seam over a scripted process (F00-R4, R5, R16; C7) ---------------------------------


Answer = tuple[int, str, str]


class ScriptedToolchain(toolchain.LocalToolchain):
    """`LocalToolchain` with `_exec` replaced: each command is answered by the first script
    entry whose key appears in it. Nothing is executed."""

    def __init__(self, script: list[tuple[str, Answer]], lean_pkg_bin: Path) -> None:
        super().__init__(Path("/fake/elan"), lean_pkg_bin=lean_pkg_bin)
        self.script = script
        self.calls: list[tuple[list[str], Path | None, dict[str, str] | None, float | None]] = []

    def _exec(
        self,
        cmd: Sequence[str],
        *,
        cwd: Path | None = None,
        extra_env: dict[str, str] | None = None,
        timeout_s: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append((list(cmd), cwd, extra_env, timeout_s))
        joined = " ".join(cmd)
        for key, (code, out, err) in self.script:
            if key in joined:
                return subprocess.CompletedProcess(list(cmd), code, out, err)
        return subprocess.CompletedProcess(list(cmd), 0, "", "")


PIN = "leanprover/lean4:v4.33.1"
HEALTHY: list[tuple[str, Answer]] = [
    ("toolchain list", (0, f"{PIN} (default)\n", "")),
    (
        "lean --version",
        (0, "Lean (version 4.33.1, x86_64-unknown-linux-gnu, commit 819816b2e0a3, Release)\n", ""),
    ),
    ("lean --githash", (0, "819816b2e0a3bf405af45ae5c7af2491d8f5bee6\n", "")),
    ("lean --print-libdir", (0, "/fake/elan/toolchains/x/lib/lean\n", "")),
]


def scripted(tmp_path: Path, *overrides: tuple[str, Answer]) -> ScriptedToolchain:
    return ScriptedToolchain([*overrides, *HEALTHY], lean_pkg_bin=tmp_path / "bin")


def test_resolve_reports_the_pin(tmp_path: Path) -> None:
    tc = scripted(tmp_path).resolve(PIN)
    assert tc == ResolvedToolchain(
        PIN,
        "4.33.1",
        "819816b2e0a3bf405af45ae5c7af2491d8f5bee6",
        Path("/fake/elan/toolchains/x/lib/lean"),
    )


def test_resolve_refuses_an_uninstalled_toolchain_by_default(tmp_path: Path) -> None:
    """R16: without `install`, an absent pin is reported with the install script, and elan is
    never asked to fetch anything (the sandbox has no network to fetch over)."""
    lt = scripted(tmp_path, ("toolchain list", (0, "leanprover/lean4:v4.0.0\n", "")))
    with pytest.raises(ToolchainMissingError) as info:
        lt.resolve(PIN)
    assert PIN in str(info.value) and toolchain.INSTALL_SCRIPT in str(info.value)
    assert not any("install" in c[0] for c in lt.calls)


def test_resolve_install_failure_is_missing_toolchain(tmp_path: Path) -> None:
    lt = scripted(
        tmp_path,
        ("toolchain list", (0, "", "")),
        ("toolchain install", (1, "", "error: could not download")),
    )
    with pytest.raises(
        ToolchainMissingError, match=r"install .* failed: error: could not download"
    ):
        lt.resolve(PIN, install=True)


@pytest.mark.parametrize(
    ("override", "match"),
    [
        (("lean --version", (1, "", "lean: not found")), "lean under .* failed: lean: not found"),
        (("lean --githash", (127, "", "boom")), "failed: boom"),
        (("lean --version", (0, "Lean 4.33.1\n", "")), "could not parse lean --version"),
    ],
)
def test_resolve_refuses_a_toolchain_that_does_not_answer(
    tmp_path: Path, override: tuple[str, Answer], match: str
) -> None:
    """A toolchain that is listed but cannot report what it is fails step 1 as a ToolchainError,
    never a resolved pin with guessed fields."""
    with pytest.raises(toolchain.ToolchainError, match=match):
        scripted(tmp_path, override).resolve(PIN)


def test_elaborate_needs_a_zero_exit_and_an_olean(tmp_path: Path) -> None:
    """R5: `lean` exiting 0 without writing the olean is a failure (as is a non-zero exit with
    its messages); the search path handed to lean is the build dir plus the toolchain's lib."""
    lt = scripted(tmp_path)
    tc = lt.resolve(PIN)
    src = tmp_path / "src" / "Nodes" / "n" / "Proof.lean"
    src.parent.mkdir(parents=True)
    src.write_text("theorem t : True := trivial\n")
    out = tmp_path / "build"
    result = lt.elaborate(tc, src, "Nodes.«n».Proof", out, root=tmp_path / "src", timeout_s=9)
    assert result.ok is False and result.messages == ()
    cmd, cwd, env, timeout = lt.calls[-1]
    assert cmd[:3] == ["/fake/elan", "run", PIN] and cmd[3:5] == ["lean", "--json"]
    assert cmd[-1] == "Nodes/n/Proof.lean" and cwd == (tmp_path / "src").resolve()
    assert timeout == 9
    assert env == {"LEAN_PATH": f"{out.resolve()}:{tc.libdir.resolve()}"}

    failing = scripted(
        tmp_path,
        (
            "lean --json",
            (
                1,
                '{"fileName":"Proof.lean","pos":{"line":1,"column":8},'
                '"severity":"error","data":"type mismatch"}\n',
                "",
            ),
        ),
    )
    result = failing.elaborate(tc, src, "Nodes.«n».Proof", out)
    assert result.ok is False and result.errors[0].text == "type mismatch"

    # Only when the process succeeds *and* the olean exists is the result a pass.
    (out / "Nodes" / "n").mkdir(parents=True, exist_ok=True)
    (out / "Nodes" / "n" / "Proof.olean").write_bytes(b"olean")
    assert lt.elaborate(tc, src, "Nodes.«n».Proof", out).ok is True


def test_kernel_replay_failure_carries_both_streams(tmp_path: Path) -> None:
    lt = scripted(
        tmp_path,
        ("leanchecker --fresh", (1, "replaying...\n", "kernel: declaration has metavars\n")),
    )
    tc = lt.resolve(PIN)
    result = lt.kernel_replay(tc, "Nodes.«n».Proof", [tmp_path / "build"], timeout_s=5)
    assert result.ok is False
    assert result.output == "replaying...\nkernel: declaration has metavars\n"
    cmd, _cwd, env, timeout = lt.calls[-1]
    assert cmd[3:] == ["leanchecker", "--fresh", "Nodes.«n».Proof"] and timeout == 5
    assert env is not None and env["LEAN_PATH"].endswith(str(tc.libdir.resolve()))


def test_axioms_fail_closed_when_the_probe_says_nothing_about_the_declaration(
    tmp_path: Path,
) -> None:
    """R6: a probe that runs but never prints the declaration's axioms — or exits non-zero even
    though it printed them — is unreadable, never an empty set."""
    lt = scripted(tmp_path, ("OpnAxioms.lean", (0, "'Other' depends on axioms: [propext]\n", "")))
    tc = lt.resolve(PIN)
    result = lt.axioms(tc, "Nodes.«n».Proof", "T.x", [tmp_path / "build"], tmp_path / "scratch")
    assert result.ok is False and result.axioms == frozenset() and "Other" in result.output
    probe = (tmp_path / "scratch" / "OpnAxioms.lean").read_text()
    assert probe == "import Nodes.«n».Proof\n#print axioms T.x\n"

    nonzero = scripted(
        tmp_path, ("OpnAxioms.lean", (1, "'T.x' depends on axioms: [propext]\n", "error\n"))
    )
    result = nonzero.axioms(
        tc, "Nodes.«n».Proof", "T.x", [tmp_path / "build"], tmp_path / "scratch"
    )
    assert result.ok is False and result.axioms == frozenset()

    fine = scripted(
        tmp_path, ("OpnAxioms.lean", (0, "'T.x' depends on axioms: [propext, sorryAx]\n", ""))
    )
    result = fine.axioms(tc, "Nodes.«n».Proof", "T.x", [tmp_path / "build"], tmp_path / "scratch")
    assert result.ok is True and result.axioms == frozenset({"propext", "sorryAx"})


def test_metaprograms_need_a_built_package(tmp_path: Path) -> None:
    """F01-R1, R10: an unbuilt package is a missing-toolchain error naming `lake build`; a
    package whose build fails is a ToolchainError with the build's tail; nothing is guessed."""
    req = toolchain.HazardsRequest(tmp_path / "S.lean", "Nodes.«n».Statement", "T.x", ("nat-sub",))
    unbuilt = scripted(tmp_path)  # lean_pkg_bin under tmp_path/bin: no lakefile above it
    tc = unbuilt.resolve(PIN)
    with pytest.raises(ToolchainMissingError, match="opn-hazards not found"):
        unbuilt.hazards(tc, req, [tmp_path / "build"])
    assert not any("lake" in c[0] for c in unbuilt.calls)

    pkg = tmp_path / "pkg"
    bin_dir = pkg / ".lake" / "build" / "bin"
    bin_dir.mkdir(parents=True)
    (pkg / "lakefile.lean").write_text("")
    broken = ScriptedToolchain(
        [("lake build", (1, "", "error: build failed\n")), *HEALTHY], bin_dir
    )
    with pytest.raises(
        toolchain.ToolchainError, match=r"lake build of .* failed: error: build failed"
    ):
        broken.hazards(tc, req, [tmp_path / "build"])
    assert broken.calls[-1][0] == ["/fake/elan", "run", PIN, "lake", "build"]
    assert broken.calls[-1][1] == pkg

    # A build that "succeeds" but produces no binary is still missing.
    quiet = ScriptedToolchain([("lake build", (0, "", "")), *HEALTHY], bin_dir)
    with pytest.raises(ToolchainMissingError, match="opn-hazards not found"):
        quiet.hazards(tc, req, [tmp_path / "build"])


def test_metaprogram_run_sets_the_lean_environment(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    bin_dir = pkg / ".lake" / "build" / "bin"
    bin_dir.mkdir(parents=True)
    for name in toolchain.METAPROGRAMS:
        (bin_dir / name).write_text("")
    lt = ScriptedToolchain(
        [
            ("opn-witness-type", (0, '{"ok": true, "expected": "True", "defeq": true}\n', "")),
            *HEALTHY,
        ],
        bin_dir,
    )
    tc = lt.resolve(PIN)
    req = toolchain.WitnessRequest(tmp_path / "S.lean", "Nodes.«n».Statement", "T.x")
    result = lt.witness_type(tc, req, [tmp_path / "build"], timeout_s=3)
    assert result.ok and result.doc["expected"] == "True"
    cmd, _cwd, env, timeout = lt.calls[-1]
    assert cmd[3] == str(bin_dir / "opn-witness-type") and "--witness" not in cmd
    assert env == {
        "LEAN_PATH": f"{(tmp_path / 'build').resolve()}:{tc.libdir.resolve()}",
        "LEAN_SYSROOT": str(tc.libdir.parent.parent),
    }
    assert timeout == 3
    assert not any("lake" in c[0] for c in lt.calls)  # already built: no rebuild


# --- F11-R6: the Mathlib pin — a checkout found by sha, its oleans on every search path ---------


def mathlib_checkout(home: Path, sha: str, *, toolchain_pin: str = PIN, packages: int = 2) -> Path:
    """What install-mathlib.sh leaves: the stamp, the lean-toolchain, Mathlib's lib and its
    packages' libs."""
    checkout = home / sha
    lib = Path(".lake") / "build" / "lib" / "lean"
    (checkout / lib).mkdir(parents=True)
    (checkout / "MATHLIB_SHA").write_text(sha + "\n")
    (checkout / "lean-toolchain").write_text(toolchain_pin + "\n")
    for name in [f"pkg{i}" for i in range(packages)]:
        (checkout / ".lake" / "packages" / name / lib).mkdir(parents=True)
    return checkout


MATHLIB = "0df444a360eaa60ab8c11dca51a86af692955474"


def test_mathlib_library_path_is_mathlib_then_its_packages(tmp_path: Path) -> None:
    checkout = mathlib_checkout(tmp_path, MATHLIB)
    lib = Path(".lake") / "build" / "lib" / "lean"
    assert toolchain.mathlib_library_path(tmp_path, MATHLIB, PIN) == (
        checkout / lib,
        checkout / ".lake" / "packages" / "pkg0" / lib,
        checkout / ".lake" / "packages" / "pkg1" / lib,
    )


def test_mathlib_pin_refusals_name_the_install_script(tmp_path: Path) -> None:
    """No checkout, a checkout stamped with another commit, one built by another toolchain, one
    without oleans, a sha that is not one: each is step 1's failure with the remedy in it."""
    with pytest.raises(ToolchainMissingError, match="no Mathlib checkout") as info:
        toolchain.mathlib_library_path(tmp_path, MATHLIB, PIN)
    assert toolchain.INSTALL_MATHLIB_SCRIPT in str(info.value) and MATHLIB in str(info.value)

    other = "e" * 40
    checkout = mathlib_checkout(tmp_path / "a", other)
    (checkout / "MATHLIB_SHA").write_text(MATHLIB + "\n")  # stamp says one thing, path another
    with pytest.raises(ToolchainMissingError, match="stamped"):
        toolchain.mathlib_library_path(tmp_path / "a", other, PIN)

    mathlib_checkout(tmp_path / "b", MATHLIB, toolchain_pin="leanprover/lean4:v4.32.0")
    with pytest.raises(
        ToolchainMissingError, match=re.escape("pins leanprover/lean4:v4.32.0")
    ) as info:
        toolchain.mathlib_library_path(tmp_path / "b", MATHLIB, PIN)
    assert "D-7" in str(info.value)

    checkout = mathlib_checkout(tmp_path / "c", MATHLIB, packages=1)
    (checkout / ".lake" / "build" / "lib" / "lean").rmdir()
    with pytest.raises(ToolchainMissingError, match="no built oleans"):
        toolchain.mathlib_library_path(tmp_path / "c", MATHLIB, PIN)
    # A package with no oleans (Mathlib's `Cli`, a build-time dependency of its cache tool) is
    # simply not on the path: nothing imports it, and requiring it refused a real checkout.
    checkout = mathlib_checkout(tmp_path / "d", MATHLIB, packages=2)
    (checkout / ".lake" / "packages" / "pkg0" / ".lake" / "build" / "lib" / "lean").rmdir()
    lib = Path(".lake") / "build" / "lib" / "lean"
    assert toolchain.mathlib_library_path(tmp_path / "d", MATHLIB, PIN) == (
        checkout / lib,
        checkout / ".lake" / "packages" / "pkg1" / lib,
    )

    with pytest.raises(ToolchainMissingError, match="not a 40-hex commit"):
        toolchain.mathlib_library_path(tmp_path, "v4.33.1", PIN)


def test_resolve_with_a_mathlib_pin_puts_its_oleans_on_every_search_path(tmp_path: Path) -> None:
    """R6: the pin resolves once, and the order everywhere is build dir, Mathlib and its
    packages, then the toolchain's lib — for `lean`, `leanchecker`, the axiom probe and the
    metaprograms alike. Without a pin nothing changes."""
    checkout = mathlib_checkout(tmp_path / "mathlib", MATHLIB, packages=1)
    lib = Path(".lake") / "build" / "lib" / "lean"
    pkg = tmp_path / "pkg"
    bin_dir = pkg / ".lake" / "build" / "bin"
    bin_dir.mkdir(parents=True)
    for name in toolchain.METAPROGRAMS:
        (bin_dir / name).write_text("")
    lt = ScriptedToolchain(
        [
            ("opn-witness-type", (0, '{"ok": true, "expected": "True", "defeq": true}\n', "")),
            *HEALTHY,
        ],
        bin_dir,
    )
    lt.mathlib_home = tmp_path / "mathlib"
    tc = lt.resolve(PIN, mathlib_sha=MATHLIB)
    assert tc.mathlib_sha == MATHLIB
    assert tc.library_path == (checkout / lib, checkout / ".lake" / "packages" / "pkg0" / lib)
    assert tc.toolchain_hash == lt.resolve(PIN).toolchain_hash  # the pin is not in the hash
    build = tmp_path / "build"
    expected = ":".join(str(p) for p in (build.resolve(), *tc.library_path, tc.libdir.resolve()))

    src = tmp_path / "src" / "Nodes" / "n" / "Proof.lean"
    src.parent.mkdir(parents=True)
    src.write_text("theorem t : True := trivial\n")
    lt.elaborate(tc, src, "Nodes.«n».Proof", build, root=tmp_path / "src")
    assert lt.calls[-1][2] == {"LEAN_PATH": expected}
    lt.kernel_replay(tc, "Nodes.«n».Proof", [build])
    assert lt.calls[-1][2] == {"LEAN_PATH": expected}
    lt.axioms(tc, "Nodes.«n».Proof", "t", [build], tmp_path / "scratch")
    assert lt.calls[-1][2] == {"LEAN_PATH": expected}
    req = toolchain.WitnessRequest(tmp_path / "S.lean", "Nodes.«n».Statement", "T.x")
    lt.witness_type(tc, req, [build])
    env = lt.calls[-1][2]
    assert env is not None and env["LEAN_PATH"] == expected

    plain = lt.resolve(PIN)
    assert plain.library_path == () and plain.mathlib_sha is None
    lt.elaborate(plain, src, "Nodes.«n».Proof", build, root=tmp_path / "src")
    assert lt.calls[-1][2] == {"LEAN_PATH": f"{build.resolve()}:{plain.libdir.resolve()}"}

    lt.mathlib_home = tmp_path / "nowhere"
    with pytest.raises(ToolchainMissingError, match="no Mathlib checkout"):
        lt.resolve(PIN, mathlib_sha=MATHLIB)
