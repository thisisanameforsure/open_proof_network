"""F25-T10 / AC14's fast half (F25-R13): the conformance verifier's plan over a scripted runner —
the clone at the exact commit, the hashes held to the registry's record, build and Comparator
with the toolchain's kernels, then the network's checkers per theorem; a disagreement anywhere
fails the entry. The real run (Lake, Mathlib, Comparator, the metaprograms at 4.35) is the
corpus workflow."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from opn_gate import palomar
from opn_gate import palomar_verify as pv
from opn_gate.palomar_port import FakeRunner, Ran

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "palomar"
ENTRY = "PALOMAR-2026-10-03-000008"  # Falmagne, Block and Marschak: one theorem, the smallest


class ClonedRunner(FakeRunner):
    """A fake whose ``git checkout`` materialises the fixture's files, as a clone would."""

    def __init__(self, files: dict[str, bytes], **answers: list[Ran]) -> None:
        super().__init__(answers={k.replace("_", " "): v for k, v in answers.items()})
        self.files = files

    def run(self, argv: list[str], *, cwd: Path, timeout_s: float) -> Ran:
        if argv[:2] == ["git", "checkout"]:
            for rel, data in self.files.items():
                (cwd / rel).parent.mkdir(parents=True, exist_ok=True)
                (cwd / rel).write_bytes(data)
        return super().run(argv, cwd=cwd, timeout_s=timeout_s)


def pin_and_files() -> tuple[dict[str, Any], dict[str, bytes]]:
    [pin] = [c for c in palomar.corpus() if c["id"] == ENTRY]
    files = {
        "Challenge.lean": (FIXTURES / ENTRY / "Challenge.lean").read_bytes(),
        "Solution.lean": b"module\n\ntheorem x : True := trivial\n",  # not vendored; hashed below
        "comparator.json": (FIXTURES / ENTRY / "comparator.json").read_bytes(),
        "lakefile.toml": (FIXTURES / ENTRY / "lakefile.toml").read_bytes(),
        "lean-toolchain": (FIXTURES / ENTRY / "lean-toolchain").read_bytes(),
    }
    pin = dict(pin, solution_sha256=hashlib.sha256(files["Solution.lean"]).hexdigest())
    return pin, files


def checkers_ok(
    project: Path, tc: str, module: str, decl: str, olean: str
) -> tuple[list[str] | None, bool | None, str]:
    return (["propext", "Quot.sound", "Classical.choice"], True, f"{module}.{decl} vs {olean}")


def test_layout_helpers() -> None:
    assert pv.module_olean(Path("/p"), "Challenge") == Path(
        "/p/.lake/build/lib/lean/Challenge.olean"
    )
    assert pv.module_olean(Path("/p"), "Lean.Comparator.ClassicalChallenge") == Path(
        "/p/.lake/build/lib/lean/Lean/Comparator/ClassicalChallenge.olean"
    )
    assert pv.project_dir(Path("/r"), {"project_path": "lean"}) == Path("/r/lean")
    assert pv.project_dir(Path("/r"), {"project_path": None}) == Path("/r")


def test_search_path_lists_the_project_then_every_package(tmp_path: Path) -> None:
    for pkg in ("mathlib", "batteries"):
        (tmp_path / ".lake" / "packages" / pkg / ".lake" / "build" / "lib" / "lean").mkdir(
            parents=True
        )
    sp = pv.search_path(tmp_path)
    assert sp[0] == tmp_path / ".lake" / "build" / "lib" / "lean"
    assert [p.parts[-5] for p in sp[1:]] == ["batteries", "mathlib"]


def test_a_registered_entry_passes_every_check_on_the_plan(tmp_path: Path) -> None:
    pin, files = pin_and_files()
    runner = ClonedRunner(files)
    result = pv.verify(
        pin,
        work=tmp_path,
        runner=runner,
        prefix_for=lambda tc: tmp_path / "prefix",
        checkers=checkers_ok,
    )
    assert result.ok, result.as_dict()
    names = [c.name for c in result.checks]
    assert names == [
        "clone", "hash challenge_path", "hash solution_path", "toolchain", "cache", "build",
        "comparator", "opn-axioms Falmagne.falmagne_blockMarschak",
        "opn-statement-meaning Falmagne.falmagne_blockMarschak",
    ]  # fmt: skip
    argvs = [c[0] for c in runner.calls]
    assert argvs[2][:5] == ("git", "fetch", "-q", "--depth", "1") and argvs[2][-1] == pin["commit"]
    assert ("lake", "exe", "cache", "get") in argvs and ("lake", "build") in argvs
    comparator = next(a for a in argvs if a[:2] == ("lake", "comparator"))
    assert Path(comparator[3]).is_absolute(), (
        "lake reads the config path from the project, not from the tool's cwd"
    )
    config = json.loads(Path(comparator[3]).read_text())
    assert config["external_kernels"]["nanoda"] == [str(tmp_path / "prefix" / "bin" / "nanoda_bin")]
    assert "enable_nanoda" not in config and config["theorem_names"] == pin["theorem_names"]
    assert result.our_axioms == {
        "Falmagne.falmagne_blockMarschak": ["Classical.choice", "Quot.sound", "propext"]
    }
    assert result.toolchain == pin["lean_toolchain"]


def test_a_hash_the_record_does_not_know_fails_before_any_build(tmp_path: Path) -> None:
    pin, files = pin_and_files()
    files["Challenge.lean"] = files["Challenge.lean"] + b"\n-- edited\n"
    runner = ClonedRunner(files)
    result = pv.verify(
        pin, work=tmp_path, runner=runner, prefix_for=lambda tc: tmp_path, checkers=checkers_ok
    )
    assert not result.ok
    assert [c.name for c in result.checks if not c.ok] == ["hash challenge_path"]
    assert all(a[0] == "git" for a, _ in runner.calls)  # nothing built


def test_comparator_and_the_networks_checkers_can_each_fail_the_entry(tmp_path: Path) -> None:
    pin, files = pin_and_files()
    runner = ClonedRunner(
        files, lake_comparator=[Ran(("lake", "comparator"), 1, "error: Const does not match")]
    )
    result = pv.verify(
        pin, work=tmp_path, runner=runner, prefix_for=lambda tc: tmp_path, checkers=checkers_ok
    )
    assert not result.ok and result.comparator_exit == 1
    assert [c.name for c in result.checks if not c.ok] == ["comparator"]

    def disagreeing(
        project: Path, tc: str, module: str, decl: str, olean: str
    ) -> tuple[list[str] | None, bool | None, str]:
        return (["propext", "sorryAx"], False, "the network's checker disagrees")

    runner2 = ClonedRunner(files)
    result2 = pv.verify(
        pin,
        work=tmp_path / "b",
        runner=runner2,
        prefix_for=lambda tc: tmp_path,
        checkers=disagreeing,
    )
    assert not result2.ok
    failed = [c.name for c in result2.checks if not c.ok]
    assert failed == [
        "opn-axioms Falmagne.falmagne_blockMarschak",
        "opn-statement-meaning Falmagne.falmagne_blockMarschak",
    ]


def test_checkers_that_could_not_be_built_count_against_the_verdict(tmp_path: Path) -> None:
    """The 2026-09-12 rule: a tool that reports pass with steps skipped is lying by omission."""
    pin, files = pin_and_files()
    result = pv.verify(
        pin,
        work=tmp_path,
        runner=ClonedRunner(files),
        prefix_for=lambda tc: tmp_path,
        checkers=None,
    )
    assert not result.ok
    assert (
        result.checks[-1].name == "network-checkers" and "not attempted" in result.checks[-1].detail
    )


def test_a_nested_project_resolves_its_paths(tmp_path: Path) -> None:
    pin, files = pin_and_files()
    nested = {f"lean/{k}": v for k, v in files.items()}
    pin = dict(
        pin,
        project_path="lean",
        challenge_path="lean/Challenge.lean",
        solution_path="lean/Solution.lean",
        comparator_config_path="lean/comparator.json",
        lakefile_path="lean/lakefile.toml",
    )
    runner = ClonedRunner(nested)
    result = pv.verify(
        pin, work=tmp_path, runner=runner, prefix_for=lambda tc: tmp_path, checkers=checkers_ok
    )
    assert result.ok, result.as_dict()
    assert all(cwd == tmp_path / "repo" / "lean" for a, cwd in runner.calls if a[0] == "lake")


def test_pins_drift_names_what_moved() -> None:
    pins = palomar.pins()
    same = {
        pins["toolchains"]["source"]: palomar.TOOLCHAINS_FILE.read_bytes(),
        pins["formalization_schema"]["source"]: palomar.FORMALIZATION_SCHEMA_FILE.read_bytes(),
    }
    assert pv.pins_drift(lambda url: same[url], pins) == []
    moved = dict(same)
    moved[pins["toolchains"]["source"]] = b'{"schema_version": 2, "minimum": "v4.36.0"}\n'
    [row] = pv.pins_drift(lambda url: moved[url], pins)
    assert row["pin"] == "toolchains" and row["detail"] == "minimum now v4.36.0"


def test_build_checkers_copies_the_package_without_its_build(tmp_path: Path) -> None:
    src = tmp_path / "lean"
    (src / ".lake" / "build").mkdir(parents=True)
    (src / "lakefile.lean").write_text("package x\n")
    (src / "lean-toolchain").write_text("leanprover/lean4:v4.33.1\n")
    runner = FakeRunner()
    bin_dir = pv.build_checkers(src, tmp_path / "work", "leanprover/lean4:v4.35.0-rc2", runner)
    dest = tmp_path / "work" / pv.LEAN_PKG_NAME
    assert bin_dir == dest / ".lake" / "build" / "bin"
    assert not (dest / ".lake" / "build").exists() or not any((dest / ".lake" / "build").iterdir())
    assert (dest / "lean-toolchain").read_text() == "leanprover/lean4:v4.35.0-rc2\n"
    assert runner.calls[0][0] == ("lake", "build") and runner.calls[0][1] == dest
    failing = FakeRunner(answers={"lake build": [Ran(("lake", "build"), 1, "error: no")]})
    assert (
        pv.build_checkers(src, tmp_path / "work2", "leanprover/lean4:v4.35.0-rc2", failing) is None
    )
    assert "error: no" in (tmp_path / "work2" / f"{pv.LEAN_PKG_NAME}-build.txt").read_text()
