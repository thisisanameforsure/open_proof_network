"""F10-T1 / R2: run every command AGENTS.md shows, in order, and check what it says it prints.

    uv run python gate/tools/walkthrough.py [AGENTS.md] --graph PATH --network PATH --api URL
                                            [--skip lean] [--skip manual] [--timeout SECONDS]

Docs are tests (F10-Q3): an ``AGENTS.md`` whose commands rot is worse than none, so the fenced
command blocks of the document are the test. The grammar the runner understands:

- A fenced block whose info string starts with ``sh`` is a command block. Each runs in a fresh
  ``bash -euo pipefail`` with the environment the previous block left behind, so a variable set
  in one block is available in the next, exactly as when a person pastes them one by one.
- Words after ``sh`` are tags. ``lean`` marks a block that needs the pinned toolchain;
  ``manual`` marks one the runner cannot execute against a fixture (a push to a remote, a pull
  request). A caller skips a tag with ``--skip``; the skipped blocks are still counted and
  named, so a document that hides its commands behind tags is visible as such.
- A fenced ``output`` block immediately after a command block is what the command is documented
  to print: every non-blank line of it must appear, in order, somewhere in the command's output.
  A line that no longer appears is drift, and drift fails the run.

The runner sets nothing but ``OPN_WALKTHROUGH_ENV``; the caller supplies ``GRAPH``,
``NETWORK`` and ``OPN_API``, which is all the document assumes.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

FENCE = "```"
COMMAND_LANG = "sh"
OUTPUT_LANG = "output"
ENV_VARIABLE = "OPN_WALKTHROUGH_ENV"
DEFAULT_TIMEOUT_S = 900.0
_HEADING_RE = re.compile(r"^(?P<level>#{1,6})\s+(?P<text>.+?)\s*$")
_DECISION_RE = re.compile(r"\bD-(?P<n>[1-9][0-9]*)\b")
#: Variables a block's environment dump carries that are the shell's own, not the document's.
_SHELL_OWN: frozenset[str] = frozenset({"_", "SHLVL", "OLDPWD"})


@dataclass(frozen=True)
class Block:
    """One fenced block: its info string split into words, its text and the line it starts on."""

    info: tuple[str, ...]
    text: str
    line: int

    @property
    def lang(self) -> str:
        return self.info[0] if self.info else ""

    @property
    def tags(self) -> frozenset[str]:
        return frozenset(self.info[1:])


@dataclass(frozen=True)
class Step:
    command: Block
    expected: Block | None = None


Status = Literal["passed", "failed", "drifted", "skipped"]


@dataclass
class Outcome:
    step: Step
    status: Status
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    missing: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return self.status in ("passed", "skipped")


# --- reading the document ------------------------------------------------------------------------


def blocks(markdown: str) -> list[Block]:
    """Every fenced block, in document order. An unclosed fence runs to the end of the file."""
    out: list[Block] = []
    info: tuple[str, ...] | None = None
    start = 0
    body: list[str] = []
    for number, raw in enumerate(markdown.splitlines(), start=1):
        line = raw.rstrip()
        if info is None:
            if line.startswith(FENCE):
                info = tuple(line[len(FENCE) :].strip().split())
                start = number
                body = []
        elif line.strip() == FENCE:
            out.append(Block(info, "\n".join(body) + "\n", start))
            info = None
        else:
            body.append(raw)
    if info is not None:
        out.append(Block(info, "\n".join(body) + "\n", start))
    return out


def headings(markdown: str) -> list[str]:
    """The heading texts, in order, fenced blocks excluded (a ``#`` inside one is a comment)."""
    out: list[str] = []
    inside = False
    for raw in markdown.splitlines():
        line = raw.rstrip()
        if line.startswith(FENCE):
            inside = not inside
            continue
        if inside:
            continue
        m = _HEADING_RE.match(line)
        if m:
            out.append(m.group("text"))
    return out


def decisions(markdown: str) -> set[str]:
    """Every ``D-n`` the document cites."""
    return {f"D-{m.group('n')}" for m in _DECISION_RE.finditer(markdown)}


def steps(found: list[Block]) -> list[Step]:
    """Command blocks paired with the ``output`` block that immediately follows each, if any."""
    out: list[Step] = []
    for index, block in enumerate(found):
        if block.lang != COMMAND_LANG:
            continue
        following = found[index + 1] if index + 1 < len(found) else None
        expected = following if following is not None and following.lang == OUTPUT_LANG else None
        out.append(Step(block, expected))
    return out


# --- running ------------------------------------------------------------------------------------


def missing_lines(expected: str, actual: str) -> list[str]:
    """The documented lines that do not appear in ``actual``, in order: each non-blank line of
    ``expected`` must be a substring of ``actual`` at or after where the previous one matched."""
    position = 0
    missing: list[str] = []
    for raw in expected.splitlines():
        line = raw.strip()
        if not line:
            continue
        at = actual.find(line, position)
        if at < 0:
            missing.append(line)
        else:
            position = at + len(line)
    return missing


def _script(block: Block, env_file: Path) -> str:
    return (
        "set -euo pipefail\n"
        "set -a\n"  # every assignment is exported, so the next block sees it (a pasted shell would)
        f"{block.text}\n"
        f"env -0 > {str(env_file)!r}\n"  # reached only when every command above succeeded
    )


def _read_env(env_file: Path, previous: Mapping[str, str]) -> dict[str, str]:
    if not env_file.is_file():
        return dict(previous)
    out: dict[str, str] = {}
    for entry in env_file.read_bytes().split(b"\0"):
        if not entry:
            continue
        name, sep, value = entry.decode("utf-8", "replace").partition("=")
        if sep and name not in _SHELL_OWN:
            out[name] = value
    return out


def run_step(
    step: Step, env: Mapping[str, str], *, cwd: Path, timeout_s: float
) -> tuple[Outcome, dict[str, str]]:
    """Run one block; answer its outcome and the environment it left for the next."""
    with tempfile.TemporaryDirectory(prefix="opn-walkthrough-") as tmp:
        env_file = Path(tmp) / "env"
        child_env = {**env, ENV_VARIABLE: str(env_file)}
        try:
            proc = subprocess.run(
                ["bash"],
                input=_script(step.command, env_file),
                capture_output=True,
                text=True,
                cwd=cwd,
                env=child_env,
                timeout=timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            out = str(exc.stdout or "")
            err = str(exc.stderr or "") + f"\n[timed out after {timeout_s:g}s]"
            return Outcome(step, "failed", None, out, err), dict(env)
        next_env = _read_env(env_file, env)
    if proc.returncode != 0:
        return Outcome(step, "failed", proc.returncode, proc.stdout, proc.stderr), next_env
    missing: list[str] = []
    if step.expected is not None:
        missing = missing_lines(step.expected.text, proc.stdout + proc.stderr)
    status: Status = "drifted" if missing else "passed"
    return Outcome(step, status, 0, proc.stdout, proc.stderr, tuple(missing)), next_env


def run(  # noqa: PLR0913 — one argument per knob the command line exposes
    plan: list[Step],
    env: Mapping[str, str],
    *,
    cwd: Path,
    skip: frozenset[str] = frozenset(),
    timeout_s: float = DEFAULT_TIMEOUT_S,
    stop_on_failure: bool = True,
) -> list[Outcome]:
    """Run the plan in order. A failure stops the run — later blocks assume earlier ones — and
    the remaining steps are reported as skipped so the count is always the whole document."""
    outcomes: list[Outcome] = []
    current = dict(env)
    halted = False
    for step in plan:
        if halted or step.command.tags & skip:
            outcomes.append(Outcome(step, "skipped"))
            continue
        outcome, current = run_step(step, current, cwd=cwd, timeout_s=timeout_s)
        outcomes.append(outcome)
        if not outcome.ok and stop_on_failure:
            halted = True
    return outcomes


def summary(outcomes: list[Outcome]) -> str:
    lines = []
    for o in outcomes:
        first = o.step.command.text.strip().splitlines()[0] if o.step.command.text.strip() else ""
        tags = " ".join(sorted(o.step.command.tags))
        lines.append(
            f"line {o.step.command.line:>4} {o.status:<8} {first[:70]}"
            + (f"  [{tags}]" if tags else "")
        )
        if o.status == "failed":
            lines.append(f"      exit {o.exit_code}; stderr: {o.stderr.strip()[-1500:]}")
            if o.stdout.strip():
                lines.append(f"      stdout: {o.stdout.strip()[-1500:]}")
        elif o.status == "drifted":
            lines.append("      documented output not seen: " + " | ".join(o.missing))
            lines.append(f"      actual: {(o.stdout + o.stderr).strip()[-1500:]}")
    counts = {
        s: sum(1 for o in outcomes if o.status == s)
        for s in ("passed", "drifted", "failed", "skipped")
    }
    lines.append(", ".join(f"{n} {s}" for s, n in counts.items()))
    return "\n".join(lines)


# --- command line -------------------------------------------------------------------------------


DEFAULT_DOC = Path(__file__).resolve().parents[1] / "agents" / "AGENTS.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="walkthrough", description=__doc__.split("\n\n")[0])
    parser.add_argument("doc", nargs="?", type=Path, default=DEFAULT_DOC)
    parser.add_argument("--graph", required=True, type=Path, help="a graph checkout ($GRAPH)")
    parser.add_argument("--network", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--api", required=True, help="the service's base URL ($OPN_API)")
    parser.add_argument("--skip", action="append", default=[], help="skip blocks with this tag")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S)
    parser.add_argument("--keep-going", action="store_true", help="do not stop at a failure")
    args = parser.parse_args(argv)
    markdown = args.doc.read_text(encoding="utf-8")
    env = {
        **os.environ,
        "GRAPH": str(args.graph.resolve()),
        "NETWORK": str(args.network.resolve()),
        "OPN_API": args.api.rstrip("/"),
    }
    with tempfile.TemporaryDirectory(prefix="opn-walkthrough-cwd-") as cwd:
        outcomes = run(
            steps(blocks(markdown)),
            env,
            cwd=Path(cwd),
            skip=frozenset(args.skip),
            timeout_s=args.timeout,
            stop_on_failure=not args.keep_going,
        )
    print(summary(outcomes))
    return 0 if all(o.ok for o in outcomes) else 1


if __name__ == "__main__":
    sys.exit(main())
