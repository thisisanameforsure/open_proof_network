"""F07-T6 / AC21: a submission opens a real pull request on the graph, and the gate runs on it.

    uv run python api/tools/smoke_submit.py <api-url> [--timeout 900] [--keep-branch]

The plain path is a pull request (D-35), and ``POST /submissions`` is meant to open one that is
indistinguishable from a hand-opened one. This drives the whole thing against the deployed
service and then reads the result back from GitHub, unauthenticated, exactly as a bystander
would: the branch, the commit's author and sign-off, the two blocks in the body, and the gate
check running on it.

It does not merge anything. The tutorial node is already proved, so a merge would be an
alternate proof (F07-R7) rather than a new result, and the criterion asks only that the pull
request exists and the gate runs. The branch and the pull request are cleaned up on the way out
unless ``--keep-branch`` is passed.

Standard library only for the HTTP (C5). The identity is minted the account-free way (D-19), so
this needs no GitHub account and no pre-existing token.
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

from smoke import call  # the same guarded caller the other smoke tools use
from smoke_precheck import DEFAULT_GRAPH_REPO, exchange, find_tutorial_node, wait_for

GITHUB_API = "https://api.github.com"
POLL_INTERVAL_S = 10


def github(
    path: str, *, method: str = "GET", token: str | None = None, body: dict[str, Any] | None = None
) -> tuple[int, Any]:
    """An unauthenticated GitHub read, unless a token is given for the cleanup."""
    request = urllib.request.Request(  # noqa: S310 — a fixed https host
        GITHUB_API + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "opn-submit-smoke",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:  # noqa: S310
            text = resp.read().decode("utf-8")
            return resp.status, json.loads(text) if text else None
    except urllib.error.HTTPError as exc:  # a refusal is an answer, not a crash
        text = exc.read().decode("utf-8")
        return exc.code, json.loads(text) if text else None


def mint_identity(base: str, node_id: str, path: str, proof: str, timeout: int) -> str | None:
    """D-19's account-free path: an anonymous precheck of the tutorial node buys a write token."""
    status, job = call(
        f"{base}/precheck", method="POST", body={"node_id": node_id, "bundle": {path: proof}}
    )
    print(f"POST /precheck (no token) -> {status} id={job.get('id')}")
    if status != 202 or not job.get("nonce"):
        print(f"PROBLEM: anonymous precheck is {status} {job}", file=sys.stderr)
        return None
    final, _ = wait_for(base, str(job["id"]), timeout)
    if (final.get("result") or {}).get("verdict") != "pass":
        print(f"PROBLEM: the identity-minting precheck did not pass: {final}", file=sys.stderr)
        return None
    _, dco = call(f"{base}/dco.json")
    pseudonym = "smoke-" + secrets.token_hex(4)
    status, issued = exchange(
        base,
        str(job["id"]),
        str(job["nonce"]),
        pseudonym,
        dco.get("version") if isinstance(dco, dict) else None,
    )
    print(f"POST /tokens -> {status} pseudonym={pseudonym}")
    if status != 201 or not isinstance(issued, dict) or not issued.get("token"):
        print(f"PROBLEM: no token: {status} {issued}", file=sys.stderr)
        return None
    return str(issued["token"])


def owned_precheck(  # noqa: PLR0913, PLR0917 — one argument per thing the job needs
    base: str,
    token: str,
    node_id: str,
    path: str,
    proof: str,
    timeout: int,
) -> str | None:
    """R1: a submission binds to a precheck *this identity* ran, so run one with the token."""
    status, job = call(
        f"{base}/precheck",
        method="POST",
        token=token,
        body={"node_id": node_id, "bundle": {path: proof}},
    )
    print(f"POST /precheck (as the identity) -> {status} id={job.get('id')}")
    if status != 202:
        print(f"PROBLEM: authenticated precheck is {status} {job}", file=sys.stderr)
        return None
    if job.get("authenticated") is not True or job.get("nonce"):
        print(f"PROBLEM: an authenticated job should carry no nonce: {job}", file=sys.stderr)
    final, _ = wait_for(base, str(job["id"]), timeout)
    if (final.get("result") or {}).get("verdict") != "pass":
        print(f"PROBLEM: the submission's precheck did not pass: {final}", file=sys.stderr)
        return None
    return str(job["id"])


def check_pull_request(repo: str, number: int, problems: list[str]) -> dict[str, Any]:
    """AC21: the pull request exists, is authored as the ledger identity, and carries the blocks."""
    status, pr = github(f"/repos/{repo}/pulls/{number}")
    if status != 200 or not isinstance(pr, dict):
        problems.append(f"the pull request is not readable: {status}")
        return {}
    body = str(pr.get("body") or "")
    print(f"PR #{number}: {pr.get('title')!r} [{pr.get('state')}] {pr.get('html_url')}")
    for marker in ("opn-precheck-attestation", "opn-submission"):
        if marker not in body:
            problems.append(f"the pull-request body carries no {marker} block (R2)")
    status, commits = github(f"/repos/{repo}/pulls/{number}/commits")
    if status != 200 or not commits:
        problems.append(f"the pull request has no readable commits: {status}")
        return pr
    commit = commits[-1]["commit"]
    author, committer = commit.get("author") or {}, commit.get("committer") or {}
    print(f"  author   : {author.get('name')} <{author.get('email')}>")
    print(f"  committer: {committer.get('name')} <{committer.get('email')}>")
    print(f"  sign-off : {'yes' if 'Signed-off-by:' in (commit.get('message') or '') else 'NO'}")
    if not str(author.get("email", "")).endswith("@anon.opn.invalid"):
        problems.append(f"the commit author is {author.get('email')!r}, not the ledger identity")
    if "Signed-off-by:" not in (commit.get("message") or ""):
        problems.append("the commit message carries no Signed-off-by line (R2, D-23)")
    if committer.get("name") == author.get("name"):
        problems.append("the committer is the author; the App should have committed it (R2)")
    return pr


def wait_for_gate(repo: str, sha: str, timeout_s: int, problems: list[str]) -> None:
    """AC21: the gate runs on the pull request. Not that it passes — that is the gate's business."""
    started = time.monotonic()
    while time.monotonic() - started < timeout_s:
        _, runs = github(f"/repos/{repo}/actions/runs?head_sha={sha}")
        found = (runs or {}).get("workflow_runs") or [] if isinstance(runs, dict) else []
        gate = [r for r in found if r.get("name") == "gate"]
        if gate:
            run = gate[0]
            print(f"  gate     : {run['status']} {run.get('conclusion') or ''} {run['html_url']}")
            if run["status"] == "completed":
                return
        time.sleep(POLL_INTERVAL_S)
    problems.append(f"no completed gate run on {sha[:8]} within {timeout_s}s")


def cleanup(repo: str, number: int, branch: str, token: str | None) -> None:
    """Close the pull request and delete its branch: this submission is a test, not a result."""
    if token is None:
        print(f"NOTE: no GITHUB_TOKEN, so PR #{number} and branch {branch} are left open")
        return
    status, _ = github(
        f"/repos/{repo}/pulls/{number}", method="PATCH", token=token, body={"state": "closed"}
    )
    print(f"cleanup: close PR #{number} -> {status}")
    status, _ = github(f"/repos/{repo}/git/refs/heads/{branch}", method="DELETE", token=token)
    print(f"cleanup: delete {branch} -> {status}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("url", help="the service's origin, e.g. https://api.openproofnetwork.org")
    parser.add_argument("--graph-repo", default=DEFAULT_GRAPH_REPO)
    parser.add_argument("--graph-branch", default="main")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--keep-branch", action="store_true", help="leave the PR and branch")
    parser.add_argument("--github-token", default=None, help="token used only for the cleanup")
    args = parser.parse_args(argv)
    base = args.url.rstrip("/")
    problems: list[str] = []

    status, health = call(f"{base}/health")
    print(f"GET /health -> {status} {health}")
    if status != 200:
        print("PROBLEM: the service is not healthy", file=sys.stderr)
        return 1

    target_id, node_id, proof = find_tutorial_node(args.graph_repo, args.graph_branch)
    path = f"targets/{target_id}/nodes/{node_id}/Proof.lean"
    print(f"tutorial node: {node_id} in target {target_id}, proof {len(proof)} bytes")

    token = mint_identity(base, node_id, path, proof, args.timeout)
    if token is None:
        return 1
    job_id = owned_precheck(base, token, node_id, path, proof, args.timeout)
    if job_id is None:
        return 1

    status, submitted = call(
        f"{base}/submissions",
        method="POST",
        token=token,
        body={
            "node_id": node_id,
            "artifact_type": "proof",
            "bundle": {path: proof},
            "precheck_job_id": job_id,
            "tooling": {"model": "smoke", "version": None, "harness": "smoke_submit.py"},
        },
    )
    where = submitted.get("pr_url") if isinstance(submitted, dict) else submitted
    print(f"POST /submissions -> {status} {where}")
    if status != 201 or not isinstance(submitted, dict):
        print(f"PROBLEM: the submission was refused: {status} {submitted}", file=sys.stderr)
        return 1

    number = int(submitted["pr_number"])
    branch = f"submit/{submitted['submission_id']}"
    pr = check_pull_request(args.graph_repo, number, problems)
    if pr:
        wait_for_gate(args.graph_repo, str(pr["head"]["sha"]), args.timeout, problems)
    if not args.keep_branch:
        cleanup(args.graph_repo, number, branch, args.github_token)

    for problem in problems:
        print(f"PROBLEM: {problem}", file=sys.stderr)
    print("smoke-submit: ok" if not problems else f"smoke-submit: {len(problems)} problem(s)")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
