"""F06-T5 / AC15: the account-free loop against the deployed service and the real scratch repo.

    uv run python api/tools/smoke_precheck.py <api-url> [--timeout 600] [--keep-token]

No account, no token, no local graph checkout. The tool reads the graph the service reads,
finds the node its ``META`` marks as the tutorial one, sends that node's own committed proof as
an anonymous precheck, waits for the scratch repository's run to finish, and exchanges the
resulting nonce for a write token — then proves the token is a write token by using it.

What it asserts (F06-AC15): the job reaches ``done`` with verdict ``pass`` inside the timeout,
and a token is issued from it. It also prints the wall-clock time each state took, which is the
Stage 0 latency series §6 asks to be recorded in the evidence.

Standard library only for the HTTP (C5); the schemas and the URL guard come from the repo.
"""

from __future__ import annotations

import argparse
import json
import secrets
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from smoke import call  # the same guarded caller the F05 smoke tool uses

RAW = "https://raw.githubusercontent.com/{repo}/{branch}/{path}"
DEFAULT_GRAPH_REPO = "thisisanameforsure/open_proof_network_graph"
POLL_INTERVAL_S = 10
ABSENT_NODE = "opn-smoke-no-such-node"


def raw(repo: str, branch: str, path: str, *, timeout: int = 30) -> Any:
    url = RAW.format(repo=repo, branch=branch, path=path)
    request = urllib.request.Request(url, headers={"User-Agent": "opn-precheck-smoke"})  # noqa: S310
    with urllib.request.urlopen(request, timeout=timeout) as resp:  # noqa: S310
        return resp.read().decode("utf-8")


def find_tutorial_node(repo: str, branch: str) -> tuple[str, str, str]:
    """(target_id, node_id, the node's committed Proof.lean) — read from the graph, never
    hardcoded, so the tool keeps working when the tutorial node moves or is renamed (D-27)."""
    index = json.loads(raw(repo, branch, "targets/index.json"))
    for target in index.get("targets", []):
        target_id = str(target["target_id"])
        graph = json.loads(raw(repo, branch, f"targets/{target_id}/graph.json"))
        for node in graph.get("nodes", []):
            if node.get("tutorial"):
                node_id = str(node["node_id"])
                path = f"targets/{target_id}/nodes/{node_id}/Proof.lean"
                return target_id, node_id, raw(repo, branch, path)
    msg = f"{repo}@{branch} has no node marked tutorial; D-19's proof has nowhere to run"
    raise SystemExit(msg)


def wait_for(base: str, job_id: str, timeout_s: int) -> tuple[dict[str, Any], list[str]]:
    """Poll until terminal or the timeout, printing each state change with its elapsed time."""
    started = time.monotonic()
    timeline: list[str] = []
    state = ""
    doc: dict[str, Any] = {}
    while True:
        status, doc = call(f"{base}/precheck/{job_id}")
        if status != 200:
            timeline.append(f"GET /precheck/<id> -> {status}")
            return {}, timeline
        elapsed = time.monotonic() - started
        if doc.get("state") != state:
            state = str(doc.get("state"))
            line = f"{elapsed:7.1f}s  {state}"
            timeline.append(line)
            print(line, flush=True)
        if state in ("done", "error", "expired"):
            return doc, timeline
        if elapsed > timeout_s:
            line = f"{elapsed:7.1f}s  still {state}; giving up at the {timeout_s}s budget"
            timeline.append(line)
            print(line, flush=True)
            return doc, timeline
        time.sleep(POLL_INTERVAL_S)


def exchange(base: str, job_id: str, nonce: str, pseudonym: str, dco_version: Any) -> Any:
    return call(
        f"{base}/tokens",
        method="POST",
        body={
            "proof": {"kind": "tutorial", "job_id": job_id, "nonce": nonce},
            "pseudonym": pseudonym,
            "dco": {"version": dco_version, "accepted": True},
        },
    )


def exchange_nonce(
    base: str, job_id: str, nonce: str, problems: list[str], *, show_token: bool
) -> bool:
    """R7: the nonce mints one write token, it authenticates, and it mints no second one."""
    _, dco = call(f"{base}/dco.json")
    version = dco.get("version") if isinstance(dco, dict) else None
    pseudonym = "smoke-" + secrets.token_hex(4)

    status, issued = exchange(base, job_id, nonce, pseudonym, version)
    identity = issued.get("identity") or {} if isinstance(issued, dict) else {}
    print(f"POST /tokens (tutorial proof) -> {status} identity={identity}")
    if status != 201 or not isinstance(issued, dict) or not issued.get("token"):
        print(f"PROBLEM: the tutorial proof minted no token: {status} {issued}", file=sys.stderr)
        return False
    token = str(issued["token"])
    if identity.get("proof_kind") != "tutorial":
        problems.append(f"the identity's proof kind is {identity.get('proof_kind')!r} (R7)")
    print(f"token: {len(token)} characters" + (f" — {token}" if show_token else ""))

    # It is a *write* token: a write route answers about the node, not about the caller.
    status, body = call(f"{base}/claims", method="POST", token=token, body={"node_id": ABSENT_NODE})
    error = body.get("error") if isinstance(body, dict) else None
    print(f"POST /claims {ABSENT_NODE} -> {status} {error}")
    if status == 401:
        problems.append(f"the issued token was not accepted: {body}")
    elif status != 404 or error != "node-not-in-frontier":
        problems.append(f"unexpected answer for an absent node: {status} {body}")

    # Single use (AC10): the same nonce a second time is refused.
    status, second = exchange(base, job_id, nonce, pseudonym + "-again", version)
    print(f"POST /tokens (same nonce again) -> {status} {second}")
    if status != 400:
        problems.append(f"the nonce was not single use: {status} {second}")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("url", help="the service's origin, e.g. https://api.openproofnetwork.org")
    parser.add_argument("--graph-repo", default=DEFAULT_GRAPH_REPO)
    parser.add_argument("--graph-branch", default="main")
    parser.add_argument(
        "--timeout", type=int, default=600, help="seconds to wait for the run (§6 budget: 300)"
    )
    parser.add_argument(
        "--keep-token", action="store_true", help="print the issued token (default: only its shape)"
    )
    args = parser.parse_args(argv)
    base = args.url.rstrip("/")
    problems: list[str] = []

    status, health = call(f"{base}/health")
    print(f"GET /health -> {status} {health}")
    if status != 200:
        print("PROBLEM: the service is not healthy; nothing else was attempted", file=sys.stderr)
        return 1

    target_id, node_id, proof = find_tutorial_node(args.graph_repo, args.graph_branch)
    path = f"targets/{target_id}/nodes/{node_id}/Proof.lean"
    print(f"tutorial node: {node_id} in target {target_id}, proof {len(proof)} bytes")

    # 1. The one unauthenticated write-shaped route (R2, Q2): no Authorization header at all.
    status, job = call(
        f"{base}/precheck", method="POST", body={"node_id": node_id, "bundle": {path: proof}}
    )
    print(f"POST /precheck (no token) -> {status} state={job.get('state')} id={job.get('id')}")
    if status != 202 or not job.get("nonce"):
        print(f"PROBLEM: anonymous precheck is {status} {job}", file=sys.stderr)
        return 1
    job_id, nonce = str(job["id"]), str(job["nonce"])
    if job.get("authenticated") is not False or job.get("public") is not True:
        problems.append(f"the response does not say anonymous-and-public: {job}")

    # 2. The scratch repository's run, polled on read (Q3).
    final, timeline = wait_for(base, job_id, args.timeout)
    verdict = (final.get("result") or {}).get("verdict")
    if final.get("state") != "done" or verdict != "pass":
        detail = final.get("error") or final.get("run_url") or verdict
        print(f"PROBLEM: the job is {final.get('state')} ({detail})", file=sys.stderr)
        return 1
    attestation = (final.get("result") or {}).get("attestation") or {}
    print(
        f"verdict {verdict}; attestation {attestation.get('schema')} "
        f"signed as {attestation.get('signature', {}).get('kind')} "
        f"by {attestation.get('signature', {}).get('key_id')}, runner {attestation.get('runner')}"
    )
    if attestation.get("signature", {}).get("kind") != "service":
        problems.append("the served attestation is not signed as kind service (R6)")

    # 3-5. The nonce becomes a write token, once (R7, AC10).
    if not exchange_nonce(base, job_id, nonce, problems, show_token=args.keep_token):
        return 1

    print("\nlatency (§6: the tutorial node under 5 min on a cold hosted runner)")
    for line in timeline:
        print("  " + line)
    for problem in problems:
        print(f"PROBLEM: {problem}", file=sys.stderr)
    print("smoke-precheck: ok" if not problems else f"smoke-precheck: {len(problems)} problem(s)")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
