"""F00-R4, R16, F01-R1: the real Toolchain seam's remaining branches in the fast tier — an
install that elan accepts but that leaves a toolchain unable to answer, a `lake` that is not
there, an output directory that cannot be written, the request records' optional arguments,
the child environment, and the `--require` entry point in process. Nothing here runs Lean:
every process is scripted (``test_toolchain.ScriptedToolchain``), or is this interpreter."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fakes import FakeToolchain
from harness import TUTORIAL, make_context
from test_toolchain import HEALTHY, PIN, Answer, ScriptedToolchain, scripted

from opn_gate import config, pipeline, toolchain
from opn_gate.toolchain import LocalToolchain, ToolchainError, ToolchainMissingError

# --- the request records: every optional argument reaches the metaprogram ------------------------


def test_request_records_carry_their_optional_arguments(tmp_path: Path) -> None:
    """F01-R3, R4, F07-R4, F08-R4: a witness, an artifact and a relation proof are passed only
    when given, each with its module, and paths are absolute."""
    st = tmp_path / "S.lean"
    with_witness = toolchain.WitnessRequest(st, "M.S", "T.x", tmp_path / "W.lean", "M.W")
    assert with_witness.args()[-4:] == [
        "--witness",
        str(tmp_path / "W.lean"),
        "--witness-module",
        "M.W",
    ]
    assert "--witness" not in toolchain.WitnessRequest(st, "M.S", "T.x").args()
    assert toolchain.UsedConstantsRequest(st, "M.S", "T.x").args() == [
        "--file", str(st), "--module", "M.S", "--decl", "T.x",
    ]  # fmt: skip
    art = toolchain.ArtifactRequest(
        st, "M.S", "T.x", tmp_path / "P.lean", "M.P", "T.x_refuted", "counterexample"
    )
    assert art.args()[6:] == [
        "--artifact", str(tmp_path / "P.lean"), "--artifact-module", "M.P",
        "--artifact-decl", "T.x_refuted", "--kind", "counterexample",
    ]  # fmt: skip
    bare = toolchain.RelationRequest(st, "M.V", "V.t", tmp_path / "R.lean", "M.R", "R.t", "related")
    assert bare.args()[-2:] == ["--label", "related"] and "--relation" not in bare.args()
    proved = toolchain.RelationRequest(
        st, "M.V", "V.t", tmp_path / "R.lean", "M.R", "R.t", "resolves",
        relation=tmp_path / "Relation.lean", relation_module="M.Relation",
    )  # fmt: skip
    assert proved.args()[-6:] == [
        "--relation", str(tmp_path / "Relation.lean"), "--relation-module", "M.Relation",
        "--relation-decl", "relation",
    ]  # fmt: skip
    half = toolchain.RelationRequest(
        st,
        "M.V",
        "V.t",
        tmp_path / "R.lean",
        "M.R",
        "R.t",
        "resolves",
        relation=tmp_path / "Relation.lean",
    )
    assert "--relation" not in half.args()  # a file without its module is not a relation proof


def test_parse_axioms_reads_only_the_named_declaration(tmp_path: Path) -> None:
    """Another declaration's 'no axioms' line is skipped; the named one's is an empty set."""
    out = "'Other' does not depend on any axioms\n'T.x' does not depend on any axioms\n"
    assert toolchain.parse_axioms(out, "T.x") == frozenset()
    assert toolchain.parse_axioms("'Other' does not depend on any axioms\n", "T.x") is None


# --- finding elan --------------------------------------------------------------------------------


def test_find_elan_takes_the_path_before_elan_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    on_path = tmp_path / "p" / "elan"
    on_path.parent.mkdir()
    on_path.write_text("#!/bin/sh\n")
    on_path.chmod(0o755)
    under_home = tmp_path / "home" / "bin" / "elan"
    under_home.parent.mkdir(parents=True)
    under_home.write_text("#!/bin/sh\n")
    monkeypatch.setenv("PATH", str(on_path.parent))
    assert toolchain.find_elan(path_env=None, elan_home=tmp_path / "home") == on_path
    assert (
        toolchain.find_elan(path_env=str(tmp_path / "nowhere"), elan_home=tmp_path / "home")
        == under_home
    )


def test_from_settings_reads_elan_home_and_the_package_bin_from_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R17: the seam is built from Settings alone — no PATH elan, so OPN_ELAN_HOME decides."""
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    home = tmp_path / "elan-home"
    (home / "bin").mkdir(parents=True)
    (home / "bin" / "elan").write_text("#!/bin/sh\n")
    settings = config.load({"OPN_ELAN_HOME": str(home), "OPN_LEAN_PKG_BIN": str(tmp_path / "bin")})
    lt = LocalToolchain.from_settings(settings)
    assert lt.elan == home / "bin" / "elan" and lt.lean_pkg_bin == tmp_path / "bin"
    with pytest.raises(ToolchainMissingError, match="OPN_ELAN_HOME"):
        LocalToolchain.from_settings(config.load({"OPN_ELAN_HOME": str(tmp_path / "nope")}))


def test_require_entrypoint_in_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """R16: `--require` is exit 1 naming the install script without elan, exit 0 naming the
    binary with it — the check `make verify-lean` runs first."""
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    monkeypatch.setenv("OPN_ELAN_HOME", str(tmp_path / "home"))
    assert toolchain.main(["--require"]) == 1
    assert toolchain.INSTALL_SCRIPT in capsys.readouterr().err
    elan = tmp_path / "home" / "bin" / "elan"
    elan.parent.mkdir(parents=True)
    elan.write_text("#!/bin/sh\n")
    assert toolchain.main(["--require"]) == 0
    assert capsys.readouterr().out == f"verify-lean: elan at {elan}\n"


# --- the process plumbing ------------------------------------------------------------------------


def test_exec_hands_the_child_the_inherited_environment_plus_extra(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R17: the one place a process starts — `extra_env` is layered over the process
    environment (through config, the only reader of os.environ), and without it the child sees
    exactly what the gate inherited."""
    monkeypatch.setenv("OPN_MARKER", "inherited")
    monkeypatch.delenv("LEAN_PATH", raising=False)
    lt = LocalToolchain(Path("/nonexistent/elan"), lean_pkg_bin=tmp_path / "bin")
    probe = [
        sys.executable,
        "-c",
        "import os; print(os.environ.get('LEAN_PATH', '<unset>') + '|' + os.environ['OPN_MARKER'])",
    ]
    proc = lt._exec(probe, cwd=tmp_path, extra_env={"LEAN_PATH": "/x:/y"}, timeout_s=30)
    assert proc.returncode == 0 and proc.stdout.strip() == "/x:/y|inherited"
    proc = lt._exec(probe, timeout_s=30)
    assert proc.stdout.strip() == "<unset>|inherited"
    assert toolchain._env_with(None) is None and toolchain._env_with({}) is None


def test_exec_propagates_the_wall_clock_timeout(tmp_path: Path) -> None:
    lt = LocalToolchain(Path("/nonexistent/elan"), lean_pkg_bin=tmp_path / "bin")
    with pytest.raises(subprocess.TimeoutExpired):
        lt._exec([sys.executable, "-c", "import time; time.sleep(5)"], timeout_s=0.2)


# --- step 1's install path, when elan says yes ---------------------------------------------------


def test_an_install_elan_accepts_but_that_cannot_answer_is_a_toolchain_error(
    tmp_path: Path,
) -> None:
    """`--install`: elan reports success, yet `lean --version` under the new toolchain fails —
    a half-installed toolchain is a ToolchainError with lean's stderr, never a resolved pin."""
    lt = scripted(
        tmp_path,
        ("toolchain list", (0, "", "")),
        ("toolchain install", (0, "info: downloading\n", "")),
        ("lean --version", (1, "", "error: toolchain is incomplete")),
    )
    with pytest.raises(
        ToolchainError, match=r"lean under .* failed: error: toolchain is incomplete"
    ):
        lt.resolve(PIN, install=True)
    assert [c[0][1:] for c in lt.calls[:2]] == [
        ["toolchain", "list"],
        ["toolchain", "install", PIN],
    ]


def test_an_install_that_completes_resolves_the_pin(tmp_path: Path) -> None:
    lt = scripted(tmp_path, ("toolchain list", (0, "", "")), ("toolchain install", (0, "", "")))
    resolved = lt.resolve(PIN, install=True)
    assert resolved.name == PIN and resolved.version == "4.33.1"
    assert any(c[0][-3:] == ["toolchain", "install", PIN] for c in lt.calls)


def test_a_missing_lake_is_a_toolchain_error_and_an_orphan_bin_dir_never_builds(
    tmp_path: Path,
) -> None:
    """F01-R10: `lake` absent (exit 127) fails the build with the shell's message; a package
    bin directory with no Lake package above it is reported as unbuilt without running lake."""
    pkg = tmp_path / "pkg"
    bin_dir = pkg / ".lake" / "build" / "bin"
    bin_dir.mkdir(parents=True)
    (pkg / "lakefile.lean").write_text("")
    no_lake: list[tuple[str, Answer]] = [("lake build", (127, "", "sh: lake: command not found\n"))]
    lt = ScriptedToolchain([*no_lake, *HEALTHY], bin_dir)
    tc = lt.resolve(PIN)
    req = toolchain.UsedConstantsRequest(tmp_path / "S.lean", "M.S", "T.x")
    with pytest.raises(
        ToolchainError, match=r"lake build of .* failed: sh: lake: command not found"
    ):
        lt.used_constants(tc, req, [tmp_path / "build"])

    orphan = ScriptedToolchain(list(HEALTHY), Path("bin"))  # no parents to hold a lakefile
    with pytest.raises(ToolchainMissingError, match="opn-used-constants not found"):
        orphan.used_constants(tc, req, [tmp_path / "build"])
    assert not any("lake" in c[0] for c in orphan.calls)


def test_the_real_seam_routes_every_metaprogram_through_one_runner(tmp_path: Path) -> None:
    """F01-R1, F07-R4, F08-R4: used-constants, artifact-type and relation-type each invoke their
    built binary with the request's arguments under LEAN_PATH/LEAN_SYSROOT, and a binary that
    breaks the JSON contract is a failure carrying its output (R9)."""
    pkg = tmp_path / "pkg"
    bin_dir = pkg / ".lake" / "build" / "bin"
    bin_dir.mkdir(parents=True)
    for name in toolchain.METAPROGRAMS:
        (bin_dir / name).write_text("")
    lt = ScriptedToolchain(
        [
            ("opn-used-constants", (0, '{"ok": true, "constants": [], "axioms": []}\n', "")),
            ("opn-artifact-type", (0, '{"ok": true, "kind": "proof", "holes": []}\n', "")),
            ("opn-relation-type", (1, "Segmentation fault\n", "core dumped\n")),
            *HEALTHY,
        ],
        bin_dir,
    )
    tc = lt.resolve(PIN)
    st = tmp_path / "S.lean"
    used = lt.used_constants(
        tc, toolchain.UsedConstantsRequest(st, "M.S", "T.x"), [tmp_path / "b"], timeout_s=4
    )
    assert used.ok and used.doc["constants"] == []
    cmd, _cwd, env, timeout = lt.calls[-1]
    assert cmd[3] == str(bin_dir / "opn-used-constants") and cmd[4:] == [
        "--file",
        str(st),
        "--module",
        "M.S",
        "--decl",
        "T.x",
    ]
    assert env is not None and set(env) == {"LEAN_PATH", "LEAN_SYSROOT"} and timeout == 4

    art = lt.artifact_type(
        tc,
        toolchain.ArtifactRequest(st, "M.S", "T.x", tmp_path / "P.lean", "M.P", "T.x", "proof"),
        [tmp_path / "b"],
    )
    assert art.ok and art.doc["kind"] == "proof"
    assert lt.calls[-1][0][3] == str(bin_dir / "opn-artifact-type") and "--kind" in lt.calls[-1][0]

    rel = lt.relation_type(
        tc,
        toolchain.RelationRequest(st, "M.V", "V.t", tmp_path / "R.lean", "M.R", "R.t", "related"),
        [tmp_path / "b"],
    )
    assert not rel.ok and rel.doc == {} and rel.exit_code == 1
    assert "Segmentation fault" in rel.output and "core dumped" in rel.output
    assert lt.calls[-1][0][3] == str(bin_dir / "opn-relation-type")


# --- an output directory that cannot be written ---------------------------------------------------


def test_elaborate_into_an_unwritable_output_directory_raises_and_the_pipeline_records_it(
    tmp_path: Path,
) -> None:
    """The seam does not hide an OSError from the host (it is not a Lean verdict); the pipeline
    turns it into the step's `unexpected-error` failure with the exception named (R18, C7)."""
    lt = scripted(tmp_path)
    tc = lt.resolve(PIN)
    src = tmp_path / "src" / "Proof.lean"
    src.parent.mkdir()
    src.write_text("theorem t : True := trivial\n")
    blocked = tmp_path / "build"
    blocked.write_text("a file where the build directory should be")
    with pytest.raises(OSError, match="build"):
        lt.elaborate(tc, src, "Nodes.«n».Proof", blocked)
    assert not any("lean --json" in " ".join(c[0]) for c in lt.calls)  # nothing was run

    ctx = make_context(tmp_path / "g", toolchain=FakeToolchain())
    ctx.workdir.write_text("a file where the work directory should be")
    verdict = pipeline.run_steps(ctx)
    # Steps 1 and 2 read nothing from the work directory; step 4 stages into it and hits the file.
    assert verdict.verdict == "fail" and verdict.first_failing_step == 4
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "unexpected-error"
    assert verdict.diagnostic.details["exception"] in ("FileExistsError", "NotADirectoryError")
    assert TUTORIAL in str(ctx.claim.node_id)
    shutil.rmtree(tmp_path / "g", ignore_errors=True)
