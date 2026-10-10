"""F25-T2: the Comparator and module-system probes, run on a Linux runner at Palomar's toolchain.

Seven questions the export's shape depends on (F25-Q1, Q2 and the plan's probe list), each asked
of ``lake comparator`` itself on a throwaway core-only Lake project, so the answers come from the
tool Palomar runs and not from a reading of its README:

1. ``definition_names``: does Comparator compare a definition's *body* between Challenge and
   Solution, or only its type? (A Solution that redefines a Challenge definition and proves the
   theorem about its own version must be refused for the export's duplicated-definitions layout
   to be sound; if it is accepted, the export refuses targets with definitions, F25-R9.)
2. A structurally recursive definition duplicated in two modules (auxiliary declarations
   ``_unary``, ``match_1`` in both): does Comparator cope?
3. A theorem reached through ``public import`` of the development versus declared in
   ``Solution.lean`` itself.
4. A ``decide``-heavy theorem through nanoda and con-ron: time and verdict.
5. ``sorryAx`` in a development module the theorem does not use: refused or ignored?
6. (asked at 4.33.1 on the laptop: ``module`` + ``public section`` on a core-only file is
   accepted; the Mathlib half waits for the docker tier) — here: the same at 4.35.
7. ``@[expose] public section`` versus a bare ``public section`` for a definition a proof in
   another module unfolds by ``rfl``.

Usage: ``python3 gate/tools/palomar_probe.py --out <dir>`` with ``lean``, ``lake`` and ``bwrap``
on PATH and ``lean-toolchain`` ≥ v4.35.0-rc2 (``palomar.toolchain_minimum()``). Writes one
``<probe>.txt`` per probe plus ``summary.json``; never exits non-zero on a probe's answer, only on
a failure to ask (a missing tool), because every answer is evidence.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

TOOLCHAIN = "leanprover/lean4:v4.35.0-rc2"
AXIOMS = ["propext", "Quot.sound", "Classical.choice"]


@dataclass
class Outcome:
    probe: str
    variant: str
    build_ok: bool
    comparator_exit: int | None
    seconds: float
    note: str


def write(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


def lakefile(name: str) -> str:
    return (
        f'name = "{name}"\n'
        f'defaultTargets = ["{name}", "Challenge", "Solution"]\n\n'
        "[leanOptions]\nautoImplicit = false\n\n"
        f'[[lean_lib]]\nname = "{name}"\n\n'
        '[[lean_lib]]\nname = "Challenge"\nroots = ["Challenge"]\n\n'
        '[[lean_lib]]\nname = "Solution"\nroots = ["Solution"]\n'
    )


def comparator_config(prefix: Path, theorem_names: list[str], definition_names: list[str]) -> str:
    return json.dumps(
        {
            "challenge_module": "Challenge",
            "solution_module": "Solution",
            "theorem_names": theorem_names,
            "definition_names": definition_names,
            "permitted_axioms": AXIOMS,
            "external_kernels": [
                {"name": "nanoda", "argv": [str(prefix / "bin" / "nanoda_bin")]},
                {"name": "con-ron", "argv": [str(prefix / "bin" / "con-ron")]},
            ],
        },
        indent=2,
    )


def run(cmd: list[str], cwd: Path, log: list[str], timeout: int = 1800) -> int:
    log.append(f"$ {' '.join(cmd)}")
    try:
        proc = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired:
        log.append(f"(timed out after {timeout}s)")
        return 124
    log.append(proc.stdout[-6000:])
    log.append(proc.stderr[-6000:])
    log.append(f"(exit {proc.returncode})")
    return proc.returncode


def probe(  # noqa: PLR0913, PLR0917 — one argument per thing a probe varies
    out: Path,
    name: str,
    variant: str,
    files: dict[str, str],
    theorem_names: list[str],
    definition_names: list[str],
    note: str,
    prefix: Path,
) -> Outcome:
    root = out / "work" / f"{name}-{variant}"
    if root.exists():
        shutil.rmtree(root)
    write(root, {"lakefile.toml": lakefile("Probe"), "lean-toolchain": TOOLCHAIN + "\n", **files})
    log: list[str] = [f"# {name} / {variant}: {note}", ""]
    for rel, text in files.items():
        log.append(f"--- {rel}\n{text}")
    t0 = time.monotonic()
    build = run(["lake", "build"], root, log)
    comparator: int | None = None
    if build == 0:
        config = root / "comparator.generated.json"
        config.write_text(
            comparator_config(prefix, theorem_names, definition_names), encoding="utf-8"
        )
        comparator = run(["lake", "comparator", "--config", str(config)], root, log)
    seconds = round(time.monotonic() - t0, 1)
    (out / f"{name}-{variant}.txt").write_text("\n".join(log), encoding="utf-8")
    return Outcome(name, variant, build == 0, comparator, seconds, note)


HEAD = "module\n\n"
CHALLENGE_DEF = (
    HEAD + "@[expose] public section\n\n"
    "/-- a definition the statement needs -/\n"
    "def Probe.f (n : Nat) : Nat := n + 1\n\n"
    "/-- the advertised statement -/\n"
    "theorem Probe.t : Probe.f 1 = 2 := by\n  sorry\n"
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    missing = [t for t in ("lean", "lake", "bwrap") if shutil.which(t) is None]
    if missing:
        print(f"missing on PATH: {missing}", file=sys.stderr)
        return 2
    prefix = Path(
        subprocess.run(
            ["lean", "--print-prefix"], capture_output=True, text=True, check=True
        ).stdout.strip()
    )
    (out / "toolchain.txt").write_text(
        subprocess.run(["lean", "--version"], capture_output=True, text=True, check=False).stdout
        + "\n"
        + "\n".join(
            f"{b}: {'present' if (prefix / 'bin' / b).exists() else 'MISSING'}"
            for b in ("lake", "leanexport", "leanchecker", "nanoda_bin", "con-ron")
        )
        + "\n\n$ lake comparator --help\n"
        + subprocess.run(
            ["lake", "comparator", "--help"], capture_output=True, text=True, check=False
        ).stdout
        + subprocess.run(
            ["lake", "comparator", "--help"], capture_output=True, text=True, check=False
        ).stderr,
        encoding="utf-8",
    )
    outcomes: list[Outcome] = []

    # 1. definition bodies
    same_def = "module\n\n@[expose] public section\n\ndef Probe.f (n : Nat) : Nat := n + 1\n"
    other_def = "module\n\n@[expose] public section\n\ndef Probe.f (n : Nat) : Nat := 2\n"
    solution = (
        HEAD
        + "public import Probe.Defs\n\npublic section\n\n"
        + "theorem Probe.t : Probe.f 1 = 2 := by\n  rfl\n"
    )
    for variant, defs, names in (
        ("same-body", same_def, ["Probe.f"]),
        ("other-body-listed", other_def, ["Probe.f"]),
        ("other-body-unlisted", other_def, []),
    ):
        outcomes.append(
            probe(
                out,
                "p1-definition-bodies",
                variant,
                {
                    "Challenge.lean": CHALLENGE_DEF,
                    "Probe/Defs.lean": defs,
                    "Probe.lean": HEAD + "public import Probe.Defs\n",
                    "Solution.lean": solution,
                },
                ["Probe.t"],
                names,
                "does Comparator compare the definition's body (refuse other-body) or only its "
                "type (accept)?",
                prefix,
            )
        )

    # 2. structural recursion in two modules
    rec = "def Probe.fact : Nat → Nat\n  | 0 => 1\n  | n + 1 => (n + 1) * Probe.fact n\n"
    ch2 = (
        HEAD
        + "@[expose] public section\n\n"
        + rec
        + "\ntheorem Probe.t2 : Probe.fact 3 = 6 := by\n  sorry\n"
    )
    sol2 = (
        HEAD
        + "public import Probe.Defs\n\npublic section\n\n"
        + "theorem Probe.t2 : Probe.fact 3 = 6 := by\n  rfl\n"
    )
    outcomes.append(
        probe(
            out,
            "p2-structural-recursion",
            "duplicated",
            {
                "Challenge.lean": ch2,
                "Probe/Defs.lean": HEAD + "@[expose] public section\n\n" + rec,
                "Probe.lean": HEAD + "public import Probe.Defs\n",
                "Solution.lean": sol2,
            },
            ["Probe.t2"],
            ["Probe.fact"],
            "auxiliary declarations of a recursive definition exist in two modules",
            prefix,
        )
    )

    # 3. theorem via public import vs declared in Solution
    ch3 = HEAD + "public section\n\ntheorem Probe.t3 : 1 + 1 = 2 := by\n  sorry\n"
    outcomes.append(
        probe(
            out,
            "p3-theorem-location",
            "in-solution",
            {
                "Challenge.lean": ch3,
                "Probe.lean": HEAD + "public section\n\ntheorem Probe.unused : True := trivial\n",
                "Solution.lean": HEAD
                + "public import Probe\n\npublic section\n\n"
                + "theorem Probe.t3 : 1 + 1 = 2 := by\n  rfl\n",
            },
            ["Probe.t3"],
            [],
            "the theorem declared in Solution.lean itself",
            prefix,
        )
    )
    outcomes.append(
        probe(
            out,
            "p3-theorem-location",
            "via-import",
            {
                "Challenge.lean": ch3,
                "Probe.lean": HEAD
                + "public section\n\ntheorem Probe.t3 : 1 + 1 = 2 := by\n  rfl\n",
                "Solution.lean": HEAD + "public import Probe\n",
            },
            ["Probe.t3"],
            [],
            "the theorem reached only through public import",
            prefix,
        )
    )

    # 4. decide-heavy
    ch4 = (
        HEAD
        + "public section\n\ntheorem Probe.t4 : (List.range "
        + "2000).foldl (· + ·) 0 = 1999000 := by\n  sorry\n"
    )
    sol4 = (
        HEAD
        + "public section\n\ntheorem Probe.t4 : (List.range "
        + "2000).foldl (· + ·) 0 = 1999000 := by\n  decide\n"
    )
    outcomes.append(
        probe(
            out,
            "p4-decide",
            "range-2000",
            {"Challenge.lean": ch4, "Probe.lean": HEAD, "Solution.lean": sol4},
            ["Probe.t4"],
            [],
            "nanoda and con-ron on a decide term",
            prefix,
        )
    )

    # 5. sorryAx elsewhere
    ch5 = HEAD + "public section\n\ntheorem Probe.t5 : 2 + 2 = 4 := by\n  sorry\n"
    outcomes.append(
        probe(
            out,
            "p5-sorry-elsewhere",
            "unused-sorry",
            {
                "Challenge.lean": ch5,
                "Probe.lean": HEAD + "public import Probe.Junk\n",
                "Probe/Junk.lean": HEAD
                + "public section\n\ntheorem Probe.junk : True := by\n  sorry\n",
                "Solution.lean": HEAD
                + "public import Probe\n\npublic section\n\ntheorem Probe.t5 : "
                + "2 + 2 = 4 := by\n  rfl\n",
            },
            ["Probe.t5"],
            [],
            "a sorry in a development module the theorem never uses",
            prefix,
        )
    )

    # 7. expose
    sol7 = (
        HEAD
        + "public import Probe.Defs\n\npublic section\n\n"
        + "theorem Probe.t : Probe.f 1 = 2 := by\n  rfl\n"
    )
    outcomes.append(
        probe(
            out,
            "p7-expose",
            "exposed",
            {
                "Challenge.lean": CHALLENGE_DEF,
                "Probe/Defs.lean": same_def,
                "Probe.lean": HEAD + "public import Probe.Defs\n",
                "Solution.lean": sol7,
            },
            ["Probe.t"],
            ["Probe.f"],
            "@[expose] public section: rfl across modules",
            prefix,
        )
    )
    outcomes.append(
        probe(
            out,
            "p7-expose",
            "bare-public",
            {
                "Challenge.lean": CHALLENGE_DEF,
                "Probe/Defs.lean": "module\n\npublic section\n\ndef Probe.f "
                + "(n : Nat) : Nat := n + 1\n",
                "Probe.lean": HEAD + "public import Probe.Defs\n",
                "Solution.lean": sol7,
            },
            ["Probe.t"],
            ["Probe.f"],
            "bare public section: does rfl across modules still elaborate?",
            prefix,
        )
    )

    (out / "summary.json").write_text(
        json.dumps([asdict(o) for o in outcomes], indent=2), encoding="utf-8"
    )
    for o in outcomes:
        print(
            f"{o.probe:28} {o.variant:20} build={'ok' if o.build_ok else 'FAIL'} "
            f"comparator={o.comparator_exit} {o.seconds}s"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
