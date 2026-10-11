"""F07-T59: the merges on a graph's main that no ``gate:`` commit credits.

    uv run python gate/tools/uncredited.py [--graph PATH] [--ref main]

Walks the graph's first-parent history. Every ``Merge pull request #N`` commit with two parents is
a merge the post-merge job owes a record; it is credited when any ``gate:`` commit subject on that
line names ``#N`` (a replay's included). The two subject grammars are copied, character for
character, from the post-merge helper in the graph's ``.github/workflows/gate.yml`` (``MERGE_RE``,
``CREDIT_RE``, ``credits()``); a test holds the copies equal to the graph's.

A merge that touched nothing under ``targets/`` is a maintenance merge: the workflow says "nothing
to gate" and writes no record, so it is reported apart and owes nothing. A merge that touched a
target and has no credit is *owed*: its attestation, ledger line and products never landed. The
tool exits 1 when any owed merge is not in ``ACKNOWLEDGED`` — the run goes red rather than reading
as an all-clear (C7).

Read-only: it runs ``git log`` and ``git diff`` on the checkout and writes nothing. The graph
checkout defaults to the sibling ``../open_proof_network_graph`` (D-35).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GRAPH = ROOT.parent / "open_proof_network_graph"

#: Copied from the graph's post-merge helper (gate.yml); test_credit_sweep holds them equal.
MERGE_RE = re.compile(r"^Merge pull request #([0-9]+) from [^/\s]+/(\S+)$")
CREDIT_RE = re.compile(r"^gate:((?: #[0-9]+)+)(?: |$)")
TARGET_RE = re.compile(r"^targets/([^/]+)/")

#: Merges known to be owed, each with the reason it does not fail the sweep. These four were found
#: by the 2026-10-04 audit, and the owner chose that day to acknowledge them for good rather than
#: replay them under pins weeks old (F07-T59, F07-T73): what is missing is a record line, never the
#: content, which later bot commits re-rendered.
ACKNOWLEDGED: dict[int, str] = {
    2: "#2 (2026-09-08), the graph's first proof, merged before the post-merge job wrote gate "
    "commits; its attestation landed by hand as 'attestation: PR #2 (tutorial-and-swap)'",
    8: "#8 (2026-09-11), the first merged variant: it gave the tutorial a second sink, root "
    "inference refused and the job wrote nothing (F08-Q19) until the root was declared (F08-T6)",
    72: "#72 (2026-09-17), the erdos-1050 intake, merged during the F15 re-pin: a gate-written "
    "hole that never elaborated failed the tag scan and the run lost its bot commit "
    "(log 2026-09-17)",
    73: "#73 (2026-09-17), the erdos-69 intake, lost its bot commit in the same run as #72; its "
    "pin was corrected by hand in bdcd64e10",
}


@dataclass(frozen=True)
class Merge:
    number: int
    sha: str
    branch: str
    targets: tuple[str, ...]


def credits(subject: str) -> list[int]:
    """The pull requests a gate commit credits: `gate: #2 #3 pass` is [2, 3], and a number
    inside a longer one is not credited (`gate: #23 pass` credits neither 2 nor 3)."""
    found = CREDIT_RE.match(subject)
    return [int(n) for n in found.group(1).split("#") if n.strip()] if found else []


def merge_of(subject: str, parents: int) -> tuple[int, str] | None:
    """(number, branch) for a pull request's merge commit, else None; two parents required."""
    found = MERGE_RE.match(subject) if parents == 2 else None
    return (int(found.group(1)), found.group(2)) if found else None


def parse_log(text: str) -> list[tuple[str, int, str]]:
    """(sha, parent count, subject) per line of ``git log --format=%H%x09%P%x09%s``."""
    entries = []
    for line in text.splitlines():
        if not line.strip():
            continue
        sha, parents, subject = line.split("\t", 2)
        entries.append((sha, len(parents.split()), subject))
    return entries


def sweep(
    log_entries: Iterable[tuple[str, int, str]], targets_of: Callable[[str], Sequence[str]]
) -> tuple[list[Merge], list[Merge]]:
    """(owed, no_target): the uncredited merges that touched a target, and those that touched
    none, oldest first. ``log_entries`` is (sha, parents, subject) along first-parent history,
    newest first as git log gives it; ``targets_of(sha)`` names the targets a merge commit
    changed against its first parent."""
    entries = list(log_entries)
    credited = {n for _sha, _parents, subject in entries for n in credits(subject)}
    owed: list[Merge] = []
    no_target: list[Merge] = []
    for sha, parents, subject in reversed(entries):
        found = merge_of(subject, parents)
        if found is None or found[0] in credited:
            continue
        merge = Merge(found[0], sha, found[1], tuple(targets_of(sha)))
        (owed if merge.targets else no_target).append(merge)
    return owed, no_target


def git(graph: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(graph), *args], check=True, capture_output=True, text=True
    ).stdout


def targets_in(graph: Path) -> Callable[[str], list[str]]:
    def targets_of(sha: str) -> list[str]:
        names = git(graph, "diff", "--name-only", f"{sha}^1", sha).split()
        return sorted({m.group(1) for n in names if (m := TARGET_RE.match(n))})

    return targets_of


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="uncredited", description=__doc__.split("\n\n")[0])
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--ref", default="main")
    args = parser.parse_args(argv)
    graph = args.graph.resolve()
    head = git(graph, "rev-parse", args.ref).strip()
    log = parse_log(git(graph, "log", "--first-parent", "--format=%H%x09%P%x09%s", head))
    merges = sum(1 for _sha, parents, subject in log if merge_of(subject, parents))
    owed, no_target = sweep(log, targets_in(graph))
    print(f"graph {graph} at {args.ref} = {head}: {merges} merges on the first-parent line")
    for merge in no_target:
        print(f"maintenance, owes nothing: #{merge.number} {merge.sha[:12]} {merge.branch}")
    failing = []
    for merge in owed:
        reason = ACKNOWLEDGED.get(merge.number)
        line = f"#{merge.number} {merge.sha[:12]} {merge.branch} {list(merge.targets)}"
        if reason is None:
            failing.append(merge)
            print(f"OWED: {line}")
        else:
            print(f"acknowledged: {line} ({reason})")
    stale = sorted(set(ACKNOWLEDGED) - {merge.number for merge in owed})
    if stale:
        print(f"note: acknowledged but now credited or absent: {stale}")
    print(f"owed {len(owed)}, acknowledged {len(owed) - len(failing)}, failing {len(failing)}")
    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main())
