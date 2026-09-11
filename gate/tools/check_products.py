"""F03-T5 / AC13: check a bot commit's merge products from a laptop.

    uv run python gate/tools/check_products.py <commit> [--graph PATH]

Given a commit in the graph repo, this tool checks that it is the one bot commit F03-R12
describes: its message is ``gate: #<pr> <verdict>``; it adds an attestation and touches
``frontier.json``, ``info.json``, ``targets/index.json`` and every target's ``graph.json``;
``frontier.json`` validates against the version it declares; and regenerating from the tree
at that commit reproduces every committed product byte for byte (R11). Exit 0 only when all of
that holds.

The graph checkout defaults to the sibling ``../open_proof_network_graph`` (D-35); pass
``--graph`` for any other clone. Nothing here trusts the CI: the inputs are the graph history and
the pinned tooling.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # gate/ on the path for opn_gate

from opn_gate import graph, postmerge, products, schemas
from opn_gate.cli import export_tree

ROOT = Path(__file__).resolve().parents[2]


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout


def check_shape(repo: Path, commit: str) -> tuple[list[str], set[str]]:
    """R12: the message, and an attestation for the pull request it names."""
    problems: list[str] = []
    message = git(repo, "log", "-1", "--format=%B", commit)
    first = message.splitlines()[0] if message else ""
    print(f"commit {commit[:12]}: {first}")
    parsed = postmerge.parse_bot_commit_message(message)
    if parsed is None:
        problems.append(f"commit message is not `gate: #<pr> <verdict>`: {first!r}")
    changed = set(git(repo, "show", "--name-only", "--format=", commit).split())
    attestations = sorted(p for p in changed if p.startswith("attestations/"))
    if not attestations:
        problems.append("no attestation in the commit")
    elif parsed is not None:
        expected = f"attestations/{postmerge.attestation_id(parsed[0])}.json"
        if expected not in attestations:
            problems.append(f"attestation {expected} not in the commit (found {attestations})")
    return problems, changed


def check_products_present(tree: Path, changed: set[str]) -> tuple[list[str], str | None]:
    """Every product is in the tree and in the commit; frontier.json validates (AC13)."""
    problems: list[str] = []
    expected = [*postmerge.PRODUCT_FILES] + [
        f"targets/{t}/graph.json" for t in products.target_ids(tree)
    ]
    for rel in expected:
        if rel not in changed:
            problems.append(f"{rel} not touched by the commit")
        if not (tree / rel).is_file():
            problems.append(f"{rel} missing from the tree")
    frontier_path = tree / "frontier.json"
    if not frontier_path.is_file():
        return problems, None
    frontier = json.loads(frontier_path.read_text(encoding="utf-8"))
    # Against the version the products declare: several are live at once (D-34), and the
    # gate that wrote them is the one that decides which (F11-R4).
    violations = schemas.violations(frontier)
    if violations:
        problems.append(f"frontier.json does not validate: {violations[0].message}")
    rendered_from = frontier.get("rendered_from")
    entries = len(frontier.get("entries") or [])
    print(f"frontier.json: {entries} entries, rendered from {rendered_from}")
    return problems, str(rendered_from) if rendered_from else None


def check_regeneration(repo: Path, tree: Path, rendered_from: str) -> list[str]:
    """R11: a fresh generation over the committed tree reproduces every product and status."""
    try:
        regenerated = products.generate(
            tree,
            rendered_from=rendered_from,
            commit_time=graph.commit_timestamp(repo, rendered_from),
        )
    except (graph.GraphError, schemas.SchemaError) as exc:
        return [f"regeneration failed: {exc}"]
    problems: list[str] = []
    for rel, data in regenerated.files.items():
        committed = tree / rel
        if not committed.is_file() or committed.read_bytes() != data:
            problems.append(f"{rel.as_posix()} differs from a fresh generation")
    for node_dir, status in regenerated.meta_status.items():
        meta = (tree / node_dir / "META.yaml").read_text(encoding="utf-8")
        if f"status: {status}\n" not in meta:
            problems.append(f"{node_dir.as_posix()}/META.yaml status is not {status}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("commit", help="the bot commit to check")
    parser.add_argument("--graph", type=Path, default=ROOT.parent / "open_proof_network_graph")
    args = parser.parse_args(argv)
    repo = args.graph.resolve()
    commit = git(repo, "rev-parse", "--verify", f"{args.commit}^{{commit}}").strip()
    problems, changed = check_shape(repo, commit)
    with tempfile.TemporaryDirectory(prefix="opn-check-products-") as tmp:
        tree = export_tree(repo, commit, Path(tmp) / "tree")
        more, rendered_from = check_products_present(tree, changed)
        problems += more
        if rendered_from:
            problems += check_regeneration(repo, tree, rendered_from)
    for p in problems:
        print(f"PROBLEM: {p}")
    print(json.dumps({"commit": commit, "ok": not problems, "problems": problems}))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
