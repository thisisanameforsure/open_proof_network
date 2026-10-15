"""Submit the erdos-1094 drafts through the live service, as the token's pseudonym.

Usage: OPN_TOKEN=... python3 submit_1094.py <drafts-dir> <graph-checkout> [--real]
Without --real every request is a dry run (the service runs the gate's own checks, opens nothing).
Heads are read from the graph checkout's origin/main glosses.json at run time.
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

API = "https://api.openproofnetwork.org"
DRAFTED = "Claude Opus 5.5 (claude-opus-5-5), read by thisisanameforsure before submission"
TARGET = "erdos-1094"

drafts, graph = sys.argv[1], sys.argv[2]
real = "--real" in sys.argv
token = os.environ["OPN_TOKEN"]


def show(path):
    return subprocess.run(
        ["git", "-C", graph, "show", f"origin/main:{path}"], check=True, capture_output=True, text=True
    ).stdout


glosses = json.loads(show(f"targets/{TARGET}/glosses.json"))
heads = {}
for s in glosses["subjects"]:
    for c in s["chains"]:
        heads[(s["node"], s["kind"])] = c["current"]


def post(route, body):
    body = dict(body, dry_run=not real) if route == "/glosses" else body
    req = urllib.request.Request(
        API + route,
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json", "authorization": f"Bearer {token}"},
        method="POST",
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")
        except (urllib.error.URLError, TimeoutError) as e:
            # A write may have landed before the connection dropped: never retry a real write blind.
            if real and route != "/glosses" or (real and route == "/glosses"):
                return 0, {"message": f"connection failed ({e}); check before resending"}
            time.sleep(10)
    return 0, {"message": "connection failed four times"}


jobs = []
for node in [
    "erdos-1094", "erdos-1094--h1", "erdos-1094--h2", "erdos-1094--h2--h1", "erdos-1094--h2--h1--h1",
    "erdos-1094--h2--h2", "erdos-1094--h3", "erdos-1094--h3--h1", "erdos-1094--h3--h1--h1",
    "erdos-1094--h3--h1--h2",
]:
    jobs.append(("/glosses", f"gloss {node}", {
        "subject": {"kind": "statement", "node_id": node},
        "text": open(f"{drafts}/glosses/{node}.md").read(),
        "supersedes": heads[(node, "statement")], "licence": "CC-BY-4.0", "drafted_with": DRAFTED}))
jobs.append(("/glosses", "witness gloss erdos-1094", {
    "subject": {"kind": "witness", "node_id": "erdos-1094"},
    "text": open(f"{drafts}/glosses/erdos-1094.witness.md").read(),
    "supersedes": heads[("erdos-1094", "witness")], "licence": "CC-BY-4.0", "drafted_with": DRAFTED}))
jobs.append(("/glosses", "explainer erdos-1094--h1", {
    "subject": {"kind": "proof", "node_id": "erdos-1094--h1",
                "proof": "a5d0f2882f4949b0fd5894dd5cf59e1e10cee1215dc174db6635d2bda53307a1"},
    "text": open(f"{drafts}/explainer/erdos-1094--h1.md").read(),
    "supersedes": heads[("erdos-1094--h1", "proof")], "licence": "CC-BY-4.0", "drafted_with": DRAFTED}))
# Annexes have no dry run: they go only with --real.
annexes = [("erdos-1094", f"{drafts}/annexes/erdos-1094--state-of-the-problem.md"),
           ("erdos-1094", f"{drafts}/annexes/erdos-1094--numerics.md")]
for f in sorted(os.listdir(f"{drafts}/annexes/per-node")):
    annexes.append((f[:-3], f"{drafts}/annexes/per-node/{f}"))
if real:
    for node, path in annexes:
        jobs.append(("/annexes", f"annex {node} {os.path.basename(path)}", {
            "node_id": node, "text": open(path).read(), "licence": "CC-BY-4.0",
            "model_and_tooling": DRAFTED}))

bad = 0
for route, label, body in jobs:
    status, out = post(route, body)
    ok = 200 <= status < 300
    bad += not ok
    print(f"{status} {label}: " + json.dumps({k: out.get(k) for k in ("pull_request", "url", "code", "message", "warnings", "dry_run") if k in out})[:400])
    time.sleep(2)
print("annexes queued:", len(annexes) if real else f"{len(annexes)} (sent only with --real)")
sys.exit(1 if bad else 0)
