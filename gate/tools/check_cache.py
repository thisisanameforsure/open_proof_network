"""F10-T4 / AC11: check the live olean cache for a graph commit, from a laptop.

    uv run python gate/tools/check_cache.py <commit> [--graph PATH] [--target ID] [--url URL]

Reads the target's ``olean_cache_url`` from the graph checkout's gate-spec.json (or takes
``--url``, for a graph whose spec does not name the cache yet), fetches the
cache for exactly ``<commit>`` over https (the consumer's own view), verifies the archive against
its manifest and every member against the manifest's hashes (R8), lists what it holds, and
times the fetch. Then it asks the same question ``pregate.sh`` asks — the newest cache at or
before ``<commit>`` on the checkout's history — and reports which commit that resolves to.
Exit 0 only when the exact cache exists and verifies.

The graph checkout defaults to the sibling ``../open_proof_network_graph`` (D-35). Nothing here
trusts the CI: the inputs are the store's bytes and the manifest's hashes.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # gate/ on the path for opn_gate

from opn_gate import cache, layout, schemas
from opn_gate.objectstore import HttpStore, ObjectStoreError

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GRAPH = ROOT.parent / "open_proof_network_graph"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="check_cache", description=__doc__.split("\n\n")[0])
    parser.add_argument("commit", help="the graph commit the cache should be keyed by")
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--target", default="tutorial")
    parser.add_argument("--url", help="the cache URL, when the spec does not name one yet")
    args = parser.parse_args(argv)
    graph = args.graph.resolve()
    spec = schemas.load_json(layout.gate_spec_path(graph, args.target), "gate-spec/v1")
    url = args.url or spec.get("olean_cache_url")
    if not isinstance(url, str) or not url:
        print(f"PROBLEM: {args.target}'s gate-spec.json names no olean_cache_url", file=sys.stderr)
        return 1
    print(f"cache: {url} (target {args.target})")
    problems: list[str] = []
    try:
        store = HttpStore(url)
        started = time.monotonic()
        commits = cache.candidates(store, args.target)
        print(f"index: {len(commits)} cache(s): {[c[:12] for c in commits]}")
        manifest_raw = store.get(cache.manifest_key(args.target, args.commit))
        archive = store.get(cache.archive_key(args.target, args.commit))
        fetched_in = time.monotonic() - started
    except ObjectStoreError as exc:
        print(f"PROBLEM: the store did not answer: {exc}", file=sys.stderr)
        return 1
    if manifest_raw is None or archive is None:
        have = f"manifest {manifest_raw is not None}, archive {archive is not None}"
        print(f"PROBLEM: no cache for {args.commit} ({have})", file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory(prefix="opn-check-cache-") as tmp:
        started = time.monotonic()
        try:
            manifest = cache.verify_and_extract(manifest_raw, archive, Path(tmp) / "oleans")
        except cache.CacheError as exc:
            print(f"PROBLEM: the cache does not verify: {exc}", file=sys.stderr)
            return 1
        verified_in = time.monotonic() - started
    modules = manifest.get("modules") or {}
    print(
        f"verified: {len(archive)} bytes, {len(modules)} module(s), toolchain "
        f"{manifest.get('lean_toolchain')}, network {str(manifest.get('network_commit'))[:12]}"
    )
    for module, entry in sorted(modules.items()):
        print(f"  {module}: {', '.join(sorted(entry.get('files') or {}))}")
    print(f"timings: fetch {fetched_in:.2f}s, verify+extract {verified_in:.2f}s")
    chosen = cache.choose(commits, args.commit, cache.git_distance(graph))
    print(f"newest at or before {args.commit[:12]} on this checkout's history: {chosen}")
    if chosen != args.commit:
        problems.append(f"pregate.sh would pick {chosen}, not {args.commit}")
    if len(archive) > cache.MAX_ARCHIVE_BYTES:
        problems.append(
            f"the archive is {len(archive)} bytes; the cap is {cache.MAX_ARCHIVE_BYTES}"
        )
    print(json.dumps({"ok": not problems, "problems": problems}))
    for p in problems:
        print(f"PROBLEM: {p}", file=sys.stderr)
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
