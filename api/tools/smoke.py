"""F05-T5 / AC19: check the deployed service.

    uv run python api/tools/smoke.py <api-url> [--read-only] [--token TOKEN]

Read-only (what CI runs after a deploy): health is 200, ``info.json`` carries the rate-limit
policy, ``frontier.json`` validates and every entry's claim fields are present, and
``claims.json`` validates. With a token (the evidence run), it also claims a node, sees the
claim in the overlay, releases it, and checks it left ``active`` — the round trip AC19 names.

Standard library only for the HTTP (C5); the protocol schemas come from ``opn_gate``.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "gate"))

from opn_gate import schemas

TIMEOUT_S = 30


def call(
    url: str, *, method: str = "GET", token: str | None = None, body: dict[str, Any] | None = None
) -> tuple[int, Any]:
    if not url.startswith("https://") and not url.startswith("http://127.0.0.1"):
        msg = f"only https (or a local runner) is called: {url}"
        raise ValueError(msg)
    data = json.dumps(body).encode() if body is not None else None
    headers = {"User-Agent": "opn-api-smoke", "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as resp:  # noqa: S310
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as exc:  # a refusal is an answer, not a crash
        raw = exc.read()
        try:
            return exc.code, json.loads(raw or b"null")
        except ValueError:
            return exc.code, raw.decode("utf-8", "replace")


def read_only(
    base: str, problems: list[str], *, allow_unconfigured: bool = False
) -> dict[str, Any]:
    status, health = call(f"{base}/health")
    print(f"GET /health -> {status} {health}")
    unconfigured = status == 503 and isinstance(health, dict) and health.get("missing")
    if unconfigured and allow_unconfigured:
        # R13: the function is running and says exactly which parameters it still lacks. That is
        # the correct state before the GitHub App exists, so the deploy is not called a failure.
        print("service reachable but not yet configured; missing:", ", ".join(health["missing"]))
        return {}
    if status != 200 or not (isinstance(health, dict) and health.get("ok")):
        problems.append(f"health is {status} {health}")
        return {}

    status, info = call(f"{base}/info.json")
    policy = info.get("rate_limit_policy") if isinstance(info, dict) else None
    print(f"GET /info.json -> {status}, protocol {info.get('protocol_version')}, policy {policy}")
    if status != 200:
        problems.append(f"info.json is {status}")
    elif schemas.violations(info, "info/v1"):
        problems.append(f"info.json does not validate: {schemas.violations(info, 'info/v1')}")
    elif not isinstance(policy, dict) or "writes_per_hour" not in policy:
        problems.append(f"info.json carries no rate-limit policy: {policy!r}")

    status, frontier = call(f"{base}/frontier.json")
    entries = frontier.get("entries", []) if isinstance(frontier, dict) else []
    print(f"GET /frontier.json -> {status}, {len(entries)} entries")
    if status != 200:
        problems.append(f"frontier.json is {status}")
    elif schemas.violations(frontier):  # against the version the graph published (D-34)
        problems.append(f"frontier.json does not validate: {schemas.violations(frontier)[:2]}")

    status, claims = call(f"{base}/claims.json")
    print(f"GET /claims.json -> {status}, {len(claims.get('nodes', {}))} nodes with claims")
    if status != 200 or schemas.violations(claims, "claims/v1"):
        problems.append(f"claims.json is {status} / does not validate")
    return frontier if isinstance(frontier, dict) else {}


ABSENT_NODE = "opn-smoke-no-such-node"


def token_authenticates(base: str, token: str, problems: list[str]) -> bool:
    """Prove the bearer is accepted without needing a claimable node: a write route answers
    about the node (404) rather than about the caller (401)."""
    status, body = call(f"{base}/claims", method="POST", token=token, body={"node_id": ABSENT_NODE})
    error = body.get("error") if isinstance(body, dict) else None
    if status == 401:
        problems.append(f"the token was not accepted: {status} {body}")
        return False
    if status != 404 or error != "node-not-in-frontier":
        problems.append(f"unexpected answer for an absent node: {status} {body}")
        return False
    print(f"POST /claims {ABSENT_NODE} -> 404 node-not-in-frontier (the token authenticates)")
    return True


def claim_round_trip(base: str, token: str, frontier: dict[str, Any], problems: list[str]) -> None:
    if not token_authenticates(base, token, problems):
        return
    claimable = [e for e in frontier.get("entries", []) if e.get("claimable")]
    if not claimable:
        problems.append(
            "no claimable node in the frontier, so the claim round trip could not run "
            "(the graph's nodes are all proved; F05-Q6)"
        )
        return
    node = str(claimable[0]["node_id"])
    status, receipt = call(
        f"{base}/claims", method="POST", token=token, body={"node_id": node, "ttl_hours": 1}
    )
    print(f"POST /claims {node} -> {status} {receipt}")
    if status != 201:
        problems.append(f"claiming {node} is {status} {receipt}")
        return
    claim_id = str(receipt["id"])
    pseudonym = str(receipt["pseudonym"])

    _, overlay = call(f"{base}/frontier.json")
    entry = next(e for e in overlay["entries"] if e["node_id"] == node)
    holders = [a["pseudonym"] for a in entry["claims"]["active"]]
    print(f"overlay shows {node} claimed by {holders}")
    if pseudonym not in holders:
        problems.append(f"the claim is not in the overlay: {entry['claims']}")

    status, released = call(f"{base}/claims/{claim_id}", method="DELETE", token=token)
    print(f"DELETE /claims/{claim_id} -> {status}, released {released.get('released')}")
    if status != 200 or not released.get("released"):
        problems.append(f"releasing is {status} {released}")
        return
    _, after = call(f"{base}/frontier.json")
    entry = next(e for e in after["entries"] if e["node_id"] == node)
    if pseudonym in [a["pseudonym"] for a in entry["claims"]["active"]]:
        problems.append("the released claim is still active in the overlay")
    if entry["claims"]["history_count"] < 1:
        problems.append("the released claim is missing from history_count")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("url", help="the service's origin, e.g. https://xyz.execute-api…")
    parser.add_argument("--token", help="a write token; without one only reads are checked")
    parser.add_argument("--read-only", action="store_true", help="skip the claim round trip")
    parser.add_argument(
        "--allow-unconfigured",
        action="store_true",
        help="a 503 naming missing parameters is reported, not failed (the post-deploy check)",
    )
    args = parser.parse_args(argv)
    base = args.url.rstrip("/")
    problems: list[str] = []
    frontier = read_only(base, problems, allow_unconfigured=args.allow_unconfigured)
    if args.token and not args.read_only:
        claim_round_trip(base, args.token, frontier, problems)
    elif not args.read_only:
        print("no --token: the claim round trip was not exercised")
    for problem in problems:
        print(f"PROBLEM: {problem}", file=sys.stderr)
    print("smoke: ok" if not problems else f"smoke: {len(problems)} problem(s)")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
