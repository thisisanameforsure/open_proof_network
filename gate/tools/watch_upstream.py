#!/usr/bin/env python3
"""F12-T5 / R11, R12, AC13: the watcher, run by hand or by the daily workflow.

    uv run python gate/tools/watch_upstream.py --graph <graph-checkout> [--dry-run]
        [--target ID ...] [--date 2026-09-12T00:00:00Z] [--branch NAME] [--out REPORT]

For every curated target whose provenance pins an upstream path and commit, compare the path
at the pin with the path at upstream head; a difference writes a ``drift/v1`` record that
flags the target (freezing proving compute in the products, F12-R11) and opens a D-8 revision
request carrying the diff. For every source page that publishes the problem's status, a flip
away from open writes a ``resolved-elsewhere`` record with the citation (R12); the target's
status is never changed here — dormancy is the curator's declaration (D-33).

``--dry-run`` reports what would be written and writes nothing (AC13). ``--branch`` commits
what was written on a new branch of the graph checkout; pushing it and opening the pull
request is whoever holds the credentials (C8; F12-Q16). Exit 0 when every upstream was read,
1 when one could not be — nothing is written for such a target and the run is not an all-clear
(AC20, C7), 2 on a usage error.

Upstream is read unauthenticated: the head commit through ``git ls-remote``, the file through
the raw content host, the page through the standard library (F12 §7).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # gate/ on the path for opn_gate

from opn_gate import config, watch

DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--graph", required=True, type=Path, help="the graph checkout")
    parser.add_argument("--dry-run", action="store_true", help="report; write nothing")
    parser.add_argument("--target", action="append", help="watch only these targets")
    parser.add_argument("--date", help="UTC timestamp of the run (default: now)")
    parser.add_argument("--branch", help="commit what was written on this new branch")
    parser.add_argument("--out", type=Path, help="also write the report here")
    args = parser.parse_args(argv)

    graph = args.graph.resolve()
    if not (graph / "targets").is_dir():
        sys.stderr.write(f"watch_upstream: {graph} has no targets/ directory\n")
        return 2
    date = args.date or datetime.now(tz=UTC).strftime(DATE_FORMAT)
    try:
        datetime.strptime(date, DATE_FORMAT).replace(tzinfo=UTC)
    except ValueError:
        sys.stderr.write(
            f"watch_upstream: --date must look like 2026-09-12T00:00:00Z, got {date!r}\n"
        )
        return 2

    report = watch.watch(
        graph, watch.GitUpstreamHost(), date=date, dry_run=args.dry_run, targets=args.target
    )
    text = report.render()
    sys.stdout.write(text)
    if args.out is not None:
        args.out.write_text(text, encoding="utf-8")
    written = [w for t in report.targets for w in t.written]
    if args.branch and written:
        env = config.child_environment(drop=config.GIT_REPO_VARIABLES)
        for step in (
            ["checkout", "-q", "-b", args.branch],
            ["add", "--", *written],
            ["commit", "-q", "-m", f"watcher: {date} — {len(written)} record(s) (F12-R11, R12)"],
        ):
            proc = subprocess.run(
                ["git", "-C", str(graph), *step],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            if proc.returncode != 0:
                sys.stderr.write(f"watch_upstream: git {step[0]} failed: {proc.stderr.strip()}\n")
                return 2
        sys.stdout.write(f"committed on {args.branch}; push it and open the pull request\n")
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
