"""A local test bench: the real service over the fake git host, seeded with the live graph.

Serves the api on 127.0.0.1:8000 (memory store; every precheck 'passes' at once, signed by a
throwaway key committed to the in-memory copy of the graph). Dumps the fake host's pushes and
pull requests and the store's identities/claims to records/ every few seconds.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import pathlib
import sys
import threading
import time

ROOT = pathlib.Path("/home/user/open_proof_network")
SCRATCH = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [
    str(ROOT / "api"),
    str(ROOT / "gate"),
    str(ROOT / "api" / "tests"),
    str(ROOT / "gate" / "tests"),
]

from api_fakes import make_harness, make_precheck_key  # noqa: E402
from test_walkthrough import AutoRunGitHost, tree_files  # noqa: E402

from opn_api import local  # noqa: E402
from opn_api.clock import SystemClock  # noqa: E402

GRAPH = SCRATCH / "graph"
RECORDS = SCRATCH / "records"
RECORDS.mkdir(exist_ok=True)
PORT = 8000


def main() -> None:
    key = make_precheck_key(SCRATCH / "precheck-key")
    files = tree_files(GRAPH)
    files["keys/precheck.pub"] = (key.public + "\n").encode()
    host = AutoRunGitHost(files, key)
    harness = make_harness(
        githost=host, clock=SystemClock(), env={"OPN_API_PUBLIC_URL": f"http://127.0.0.1:{PORT}"}
    )
    store = harness.store

    def dump() -> None:
        while True:
            try:
                (RECORDS / "pushes.json").write_text(
                    json.dumps([dataclasses.asdict(p) for p in host.pushes], indent=2, default=str)
                )
                (RECORDS / "pulls.json").write_text(
                    json.dumps([dataclasses.asdict(p) for p in host.pulls], indent=2, default=str)
                )
                (RECORDS / "dispatches.json").write_text(
                    json.dumps([dataclasses.asdict(d) for d in host.dispatches], indent=2)
                )
                (RECORDS / "store.json").write_text(
                    json.dumps(
                        {
                            "identities": [
                                dataclasses.asdict(i) for i in store.identities.values()
                            ],
                            "claims": [dataclasses.asdict(c) for c in store.claims.values()],
                            "jobs": store.jobs,
                            "counters": {k: [v[0], str(v[1])] for k, v in store.counters.items()},
                        },
                        indent=2,
                        default=str,
                    )
                )
            except Exception as exc:
                (RECORDS / "dump-error.txt").write_text(repr(exc))
            time.sleep(3)

    threading.Thread(target=dump, daemon=True).start()
    asyncio.run(local.serve(harness.app, "127.0.0.1", PORT))


if __name__ == "__main__":
    main()
