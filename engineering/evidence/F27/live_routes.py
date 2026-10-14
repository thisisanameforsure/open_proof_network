"""F27-T5: every live target's routes and sufficient sets, from the committed products.

Reads each ``targets/<id>/graph.json`` and ``frontier.json`` at the graph's ``origin/main`` with
``git show`` (never the shared checkout's working tree, which moves under a session), runs
``opn_gate.routes.read`` with both cuts, and checks each set independently: forward-chaining from
the set's statements and every proved node through routes and resolves variants must close the
root. Prints one line per target and a total.

    PYTHONPATH=gate uv run --frozen python engineering/evidence/F27/live_routes.py \
        [--graph ../open_proof_network_graph] [--ref origin/main]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any

from opn_gate import routes


def show(graph: Path, ref: str, path: str) -> Any:
    out = subprocess.run(
        ["git", "-C", str(graph), "show", f"{ref}:{path}"], capture_output=True, check=True
    )
    return json.loads(out.stdout)


def closes_root(doc: dict[str, Any], result: routes.Routes, members: set[str]) -> bool:
    """Forward-chain over the routes as the library resolved them (so an older product's unnamed
    holes count as assigned), a direct proof needing its non-hole deps, and resolves variants."""
    rows = {str(n["node_id"]): n for n in doc["nodes"]}
    closed = {k for k, n in rows.items() if n["status"] == "proved"} | members
    by_node: dict[str, list[list[str]]] = {}
    for r in result.routes:
        if r.resolved:
            by_node.setdefault(r.node, []).append([str(h.node) for h in r.holes])
    changed = True
    while changed:
        changed = False
        for k in rows:
            if k in closed:
                continue
            if any(all(h in closed for h in hs) for hs in by_node.get(k, [])):
                closed.add(k)
                changed = True
    root = str(doc["root"])
    return root in closed or any(
        n.get("relation") == "resolves" and k in closed for k, n in rows.items() if k != root
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--graph", default="../open_proof_network_graph")
    ap.add_argument("--ref", default="origin/main")
    args = ap.parse_args()
    graph = Path(args.graph)
    sha = subprocess.run(
        ["git", "-C", str(graph), "rev-parse", args.ref], capture_output=True, text=True, check=True
    ).stdout.strip()
    frontier = show(graph, args.ref, "frontier.json")
    index = show(graph, args.ref, "targets/index.json")
    print(f"graph {sha} ({args.ref}); frontier rendered_from {frontier.get('rendered_from')}")
    print(f"{'target':<20} {'nodes':>5} {'routes':>6} {'unres':>5} {'finest':>6} {'any':>5} "
          f"{'trunc':>5} {'close':>5} {'ms':>6}")
    bad = 0
    for row in index["targets"]:
        tid = str(row["target_id"])
        doc = show(graph, args.ref, f"targets/{tid}/graph.json")
        started = time.perf_counter()
        finest = routes.read(doc, frontier["entries"])
        coarse = routes.read(doc, frontier["entries"], cut="any")
        ms = (time.perf_counter() - started) * 1000
        ok = all(closes_root(doc, finest, set(s.statements)) for s in finest.sets) and all(
            closes_root(doc, coarse, set(s.statements)) for s in coarse.sets
        )
        bad += 0 if ok and finest.sets else 1
        unresolved = sum(1 for r in finest.routes if not r.resolved)
        print(f"{tid:<20} {len(doc['nodes']):>5} {len(finest.routes):>6} {unresolved:>5} "
              f"{len(finest.sets):>6} {len(coarse.sets):>5} {str(coarse.truncated):>5} "
              f"{str(ok):>5} {ms:>6.1f}")
    print(f"targets whose sets do not all close the root, or that have no set: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
