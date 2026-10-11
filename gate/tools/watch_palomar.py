#!/usr/bin/env python3
"""F25-T13 / R14, AC13: the Palomar feed watcher, run by hand or by the weekly workflow.

    uv run python gate/tools/watch_palomar.py --graph <graph-checkout> [--snapshot recent.json]
        [--propose --contributor ID --out DIR] [--drift] [--out-report REPORT]

Reads the registry's ``recent.json`` (or a saved copy with ``--snapshot``, which is what the
workflow keeps as evidence), matches every entry to the network's targets by the problem's
number as a token, and prints the candidates with their evidence as one JSON document. A
candidate is information: with ``--propose`` an unsigned ``literature/v1`` proposal per candidate
is written under ``--out`` — never into the graph, never confirmed (F25-Q11). ``--drift`` compares
every registration record on the graph with the registry's entry and reports differences.

Exit 0 with or without candidates, 1 when the registry could not be read (a warning; nothing
written, and the run is not an all-clear — C7), 2 on a usage error. The same code as
``opn-gate palomar-feed``: this file exists so the workflow and a person run it by path.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # gate/ on the path for opn_gate

from opn_gate import palomar_feed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--graph", required=True, type=Path, help="the graph checkout")
    parser.add_argument("--snapshot", type=Path, help="a saved recent.json instead of the host")
    parser.add_argument("--propose", action="store_true", help="write a proposal per candidate")
    parser.add_argument("--contributor", help="the proposals' contributor (with --propose)")
    parser.add_argument("--out", type=Path, help="where proposals are written (with --propose)")
    parser.add_argument(
        "--drift", action="store_true", help="compare registrations with the registry"
    )
    parser.add_argument("--out-report", type=Path, help="also write the report here")
    args = parser.parse_args(argv)

    graph = args.graph.resolve()
    if not (graph / "targets").is_dir():
        sys.stderr.write(f"watch_palomar: {graph} has no targets/ directory\n")
        return 2
    if args.propose and (not args.contributor or args.out is None):
        sys.stderr.write("watch_palomar: --propose needs --contributor and --out\n")
        return 2
    if args.snapshot is not None and not args.snapshot.is_file():
        sys.stderr.write(f"watch_palomar: cannot read --snapshot {args.snapshot}\n")
        return 2
    host = None if args.snapshot is not None and not args.drift else palomar_feed.default_host()
    try:
        result = palomar_feed.run(
            graph,
            host,
            snapshot=args.snapshot,
            propose=args.propose,
            contributor=args.contributor,
            out=args.out,
            drift=args.drift,
        )
    except palomar_feed.FeedError as exc:
        sys.stderr.write(f"watch_palomar: {exc}\n")
        return 2
    text = result.render()
    sys.stdout.write(text)
    if args.out_report is not None:
        args.out_report.write_text(text, encoding="utf-8")
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
