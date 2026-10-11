"""F25-T9 / AC8 (F25-R12): the port of an exported wrapper to the registry's toolchain — pins
rewritten, the Challenge frozen, a failed build classified, the registry's preflight report
read — over a scripted runner. The real port (lake, Mathlib, Comparator) is T15's live run."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_export_palomar import ready, run

from opn_gate import palomar_port as pp

TC = "leanprover/lean4:v4.35.0-rc2"
REV = "v4.35.0-rc2"


def exported(tmp_path: Path) -> Path:
    project = tmp_path / "wrapper"
    run(ready(tmp_path)).write(project)
    return project


def test_rewrite_pins_and_remember_what_they_were(tmp_path: Path) -> None:
    project = exported(tmp_path)
    were = pp.rewrite_pins(project, toolchain=TC, mathlib_rev=REV)
    assert were == {"toolchain_was": "leanprover/lean4:v4.33.1", "mathlib_was": ""}
    assert (project / "lean-toolchain").read_text() == TC + "\n"
    lakefile = (project / "lakefile.toml").read_text()
    assert f'rev = "{REV}"' in lakefile and 'name = "mathlib"' in lakefile
    # a project that pinned Mathlib has its rev replaced, not a second require added
    pinned = lakefile.replace(f'rev = "{REV}"', f'rev = "{"a" * 40}"')
    (project / "lakefile.toml").write_text(pinned)
    were2 = pp.rewrite_pins(project, toolchain=TC, mathlib_rev="v4.36.0")
    assert were2["mathlib_was"] == "a" * 40
    after = (project / "lakefile.toml").read_text()
    assert after.count("[[require]]") == 1 and 'rev = "v4.36.0"' in after


def test_a_toolchain_below_the_minimum_is_refused(tmp_path: Path) -> None:
    project = exported(tmp_path)
    with pytest.raises(pp.PortError) as caught:
        pp.rewrite_pins(project, toolchain="leanprover/lean4:v4.34.0", mathlib_rev="v4.34.0")
    assert caught.value.diagnostic.code == "port-toolchain-below-minimum"
    assert pp._version_tuple("leanprover/lean4:v4.35.0-rc2") < pp._version_tuple(
        "leanprover/lean4:v4.35.0"
    )
    assert pp._version_tuple("leanprover/lean4:v4.35.0-rc3") > pp._version_tuple(
        "leanprover/lean4:v4.35.0-rc2"
    )


def test_the_challenge_is_frozen(tmp_path: Path) -> None:
    project = exported(tmp_path)
    pp.challenge_frozen(project)  # as exported: fine
    (project / "Challenge.lean").write_text(
        (project / "Challenge.lean").read_text() + "\n-- edited\n"
    )
    with pytest.raises(pp.PortError) as caught:
        pp.challenge_frozen(project)
    assert caught.value.diagnostic.code == "port-challenge-changed"
    (project / "opn-export.json").unlink()
    with pytest.raises(pp.PortError) as caught2:
        pp.challenge_frozen(project)
    assert caught2.value.diagnostic.code == "port-record-missing"


CANNED_BUILD = """✔ [2/7] Built OpnX.Nodes.a (284ms)
✖ [4/7] Building OpnX.Nodes.b (302ms)
error: OpnX/Nodes/b.lean:12:4: unknown identifier 'Nat.sub_le_iff_le_add'
error: OpnX/Nodes/b.lean:30:2: type mismatch
  h
has type
  a ≤ b : Prop
but is expected to have type
  a < b : Prop
warning: OpnX/Nodes/b.lean:40:6: `Finset.sum_const_nat` has been deprecated, use `sum_const`
warning: OpnX/Nodes/b.lean:41:6: unused variable `x`
error: OpnX/Nodes/b.lean:50:2: failed to reduce to true/false
error: Solution.lean:7:2: Tactic `rfl` failed: The left-hand side
Some required targets logged failures:
- OpnX.Nodes.b
"""


def test_build_failures_are_classified() -> None:
    failures = pp.classify(CANNED_BUILD)
    kinds = [(f.kind, f.line) for f in failures]
    assert kinds == [
        ("renamed-or-removed", 12),
        ("type-mismatch", 30),
        ("deprecated", 40),
        ("decide-failed", 50),
        ("tactic-failed", 7),
    ]
    assert failures[0].module == "OpnX.Nodes.b" and failures[0].file == "OpnX/Nodes/b.lean"
    assert all(f.kind != "other" for f in failures)
    assert pp.classify("Build completed successfully (8 jobs).\n") == []


def test_preflight_report_is_read_loosely() -> None:
    passed = pp.preflight_report({"status": "pass", "phase": "verification", "diagnostics": []})
    assert passed.passed and passed.findings == ()
    failed = pp.preflight_report(
        {
            "status": "fail",
            "phase": "preparation",
            "diagnostics": [
                {
                    "owner": "submitter",
                    "explanation": "Challenge.lean exceeds 1000 lines",
                    "next_action": "shorten it",
                    "retryable": False,
                    "location": {"path": "Challenge.lean"},
                },
                {
                    "owner": "palomar",
                    "explanation": "runner out of disk",
                    "retryability": "retryable",
                },
            ],
        }
    )
    assert not failed.passed and failed.status == "fail"
    assert (
        failed.findings[0].next_action == "shorten it"
        and failed.findings[0].location == '{"path": "Challenge.lean"}'
    )
    assert failed.findings[1].retryable is True and failed.findings[1].owner == "palomar"
    assert not pp.preflight_report({}).passed  # nothing is a pass but "pass"
    assert not pp.preflight_report({"status": "PASS"}).passed


def test_the_port_runs_the_steps_in_order_and_stops_at_the_first_failure(tmp_path: Path) -> None:
    project = exported(tmp_path)
    prefix = tmp_path / "toolchain"
    runner = pp.FakeRunner(answers={"lake build": [pp.Ran(("lake", "build"), 1, CANNED_BUILD)]})
    report = pp.port(project, toolchain=TC, mathlib_rev=REV, runner=runner, prefix=prefix)
    assert [c[0][:2] for c in runner.calls] == [
        ("lake", "update"),
        ("lake", "exe"),
        ("lake", "build"),
    ]
    assert all(cwd == project for _, cwd in runner.calls)
    assert not report.ok and [s["step"] for s in report.steps] == ["update", "cache", "build"]
    assert [f.kind for f in report.failures][:2] == ["renamed-or-removed", "type-mismatch"]
    written = json.loads((project / pp.PORT_REPORT).read_text())
    assert (
        written["ok"] is False
        and written["pins_were"]["toolchain_was"] == "leanprover/lean4:v4.33.1"
    )
    # the kernels configuration the comparator step would have used
    config = json.loads((project / ".opn-port" / "comparator.generated.json").read_text())
    assert set(config["external_kernels"]) == {"nanoda", "con-ron"}
    assert config["external_kernels"]["nanoda"] == [str(prefix / "bin" / "nanoda_bin")]
    assert "enable_nanoda" not in config and config["theorem_names"] == ["OpnProp.and_swap_reassoc"]


def test_a_clean_port_ends_with_comparator(tmp_path: Path) -> None:
    project = exported(tmp_path)
    runner = pp.FakeRunner()
    report = pp.port(
        project,
        toolchain=TC,
        mathlib_rev=REV,
        runner=runner,
        prefix=tmp_path / "tc",
        skip_update=True,
    )
    assert report.ok and [s["step"] for s in report.steps] == ["cache", "build", "comparator"]
    assert runner.calls[-1][0][:3] == ("lake", "comparator", "--config")


def test_a_port_refuses_a_moved_challenge_before_running_anything(tmp_path: Path) -> None:
    project = exported(tmp_path)
    (project / "Challenge.lean").write_text(
        "module\n\ntheorem OpnProp.and_swap_reassoc : True := trivial\n"
    )
    runner = pp.FakeRunner()
    with pytest.raises(pp.PortError):
        pp.port(project, toolchain=TC, mathlib_rev=REV, runner=runner, prefix=tmp_path)
    assert runner.calls == []
