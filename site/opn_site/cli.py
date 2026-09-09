"""``python -m opn_site.cli render --graph <checkout> --commit <sha> --out <dir>`` (F04).

Loads the checkout and its products, renders every page in memory, and writes them only when
all of them rendered (R13). Exit 0 on success, 1 when the graph cannot be rendered faithfully.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from opn_site import config, model, render


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="opn-site", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    r = sub.add_parser("render", help="render the site from a graph checkout and its products")
    r.add_argument("--graph", required=True, type=Path, help="path to the graph checkout")
    r.add_argument("--commit", required=True, help="the graph commit the checkout is at")
    r.add_argument("--out", required=True, type=Path, help="output directory")
    args = parser.parse_args(argv)
    settings = config.load()
    try:
        site = model.load_site(args.graph, args.commit)
        files = render.render_site(site, repo_url=settings.graph_repo_url)
    except (model.SiteError, ValueError) as exc:
        sys.stdout.write(json.dumps({"ok": False, "error": str(exc)}) + "\n")
        sys.stderr.write(f"opn-site: nothing written: {exc}\n")
        return 1
    written = render.write(files, args.out.resolve())
    sys.stdout.write(json.dumps({"ok": True, "pages": len(written), "out": str(args.out)}) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
