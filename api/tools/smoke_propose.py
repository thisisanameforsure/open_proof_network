"""F08-T6 / AC19: a proposal opens a real pull request, admission runs on it, and the merged
node enters the frontier.

    uv run python api/tools/smoke_propose.py <api-url> [--github-token T] [--timeout 1800]

Drives ``POST /proposals/variant`` against the deployed service with a ``related`` variant of
the tutorial node, then reads everything back from GitHub, unauthenticated, as a bystander
would: the branch, the commit's author and sign-off, the one new node directory, the gate run
on the pull request and — once the pull request is merged — the post-merge run, the node's entry
in ``frontier.json`` and the proposer's statement line in the ledger (F08-R13).

Nothing merges on green yet (F07-Q16, F08-R2): the merge is a person's act. With
``--github-token`` the tool presses the button as that account, as a merge commit so the
pseudonymous commit stays the pull request's own; without one it waits for a human to press it,
up to the timeout, and says so. Either way the pull request and the branch are left alone
afterwards: a merged proposal is content on the record (D-35), not a test artifact, and an
unmerged one is evidence of where the run stopped.

Standard library only for the HTTP (C5). The identity is minted the account-free way (D-19).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from smoke import call  # the same guarded caller the other smoke tools use
from smoke_precheck import DEFAULT_GRAPH_REPO, find_tutorial_node, raw
from smoke_submit import github, mint_identity

POLL_INTERVAL_S = 15
EXIT_PENDING = 2  # green, and waiting for a person to merge

#: A weaker statement than the tutorial's, related and honestly labelled so (D-30): from p ∧ q,
#: p alone. No import line: the id is derived from the statement's hash (F08-R3), so the
#: statement cannot name its own Context module, and a core-only statement needs none.
VARIANT_STATEMENT = (
    "/-! A related variant of the tutorial node (D-30), proposed by the F08 smoke. -/\n\n"
    "theorem OpnProp.and_left_of_and_swap : ∀ p q : Prop, p ∧ q → p := by\n  sorry\n"
)
VARIANT_WITNESS = (
    "/-! Non-vacuity witness (D-4 step 7): the hypothesis `p ∧ q` is satisfiable. -/\n\n"
    "theorem witness : ∃ p q : Prop, p ∧ q := ⟨True, True, trivial, trivial⟩\n"
)


def check_pull_request(repo: str, number: int, node_id: str, problems: list[str]) -> str:
    """AC19: the pull request adds one new node directory, authored as the ledger identity with
    the App as committer. Returns the head sha."""
    status, pr = github(f"/repos/{repo}/pulls/{number}")
    if status != 200 or not isinstance(pr, dict):
        problems.append(f"the pull request is not readable: {status}")
        return ""
    print(f"PR #{number}: {pr.get('title')!r} [{pr.get('state')}] {pr.get('html_url')}")
    status, files = github(f"/repos/{repo}/pulls/{number}/files")
    changed = [f.get("filename", "") for f in files] if isinstance(files, list) else []
    prefix = f"nodes/{node_id}/"
    print(f"  files    : {len(changed)} added under {prefix}")
    if not changed or not all(prefix in f for f in changed):
        problems.append(f"the pull request should add {prefix} and nothing else: {changed}")
    for required in ("META.yaml", "Statement.lean", "Witness.lean", "Context.lean"):
        if not any(f.endswith(prefix + required) for f in changed):
            problems.append(f"the proposal lacks {required} (D-3)")
    status, commits = github(f"/repos/{repo}/pulls/{number}/commits")
    if status != 200 or not commits:
        problems.append(f"the pull request has no readable commits: {status}")
        return str(pr.get("head", {}).get("sha", ""))
    commit = commits[-1]["commit"]
    author, committer = commit.get("author") or {}, commit.get("committer") or {}
    print(f"  author   : {author.get('name')} <{author.get('email')}>")
    print(f"  committer: {committer.get('name')} <{committer.get('email')}>")
    if not str(author.get("email", "")).endswith("@anon.opn.invalid"):
        problems.append(f"the commit author is {author.get('email')!r}, not the ledger identity")
    if "Signed-off-by:" not in (commit.get("message") or ""):
        problems.append("the commit message carries no Signed-off-by line (F07-R2, D-23)")
    if committer.get("name") == author.get("name"):
        problems.append("the committer is the author; the App should have committed it")
    return str(commits[-1]["sha"])


def wait_for_run(
    repo: str, *, head_sha: str | None, event: str, timeout_s: int, problems: list[str]
) -> dict[str, Any]:
    """The gate workflow's run on ``head_sha`` (or the latest for ``event``), completed."""
    started = time.monotonic()
    while time.monotonic() - started < timeout_s:
        query = f"head_sha={head_sha}" if head_sha else f"event={event}&per_page=5"
        _, runs = github(f"/repos/{repo}/actions/runs?{query}")
        found = (runs or {}).get("workflow_runs") or [] if isinstance(runs, dict) else []
        gate = [r for r in found if r.get("name") == "gate" and r.get("event") == event]
        if gate:
            run = gate[0]
            print(f"  {event:<13}: {run['status']} {run.get('conclusion') or ''} {run['html_url']}")
            if run["status"] == "completed":
                return dict(run)
        time.sleep(POLL_INTERVAL_S)
    problems.append(f"no completed {event} gate run within {timeout_s}s")
    return {}


def merge_or_wait(
    repo: str, number: int, token: str | None, timeout_s: int, problems: list[str]
) -> str | None:
    """The merge commit's sha: pressed here with a token, or awaited from a person without."""
    if token is not None:
        status, result = github(
            f"/repos/{repo}/pulls/{number}/merge",
            method="PUT",
            token=token,
            body={"merge_method": "merge"},
        )
        print(f"PUT /pulls/{number}/merge -> {status} {result if status != 200 else ''}")
        if status != 200 or not isinstance(result, dict):
            problems.append(f"the merge was refused: {status} {result}")
            return None
        return str(result.get("sha"))
    print(f"waiting for a person to merge PR #{number} (F07-Q16: nothing merges on green) ...")
    started = time.monotonic()
    while time.monotonic() - started < timeout_s:
        status, pr = github(f"/repos/{repo}/pulls/{number}")
        if status == 200 and isinstance(pr, dict) and pr.get("merged_at"):
            print(f"  merged at {pr['merged_at']} as {pr.get('merge_commit_sha')}")
            return str(pr.get("merge_commit_sha"))
        if status == 200 and isinstance(pr, dict) and pr.get("state") == "closed":
            problems.append("the pull request was closed without merging")
            return None
        time.sleep(POLL_INTERVAL_S)
    return None


def check_products(
    repo: str, branch: str, node_id: str, pseudonym: str, problems: list[str]
) -> None:
    """AC19: the node is in frontier.json; R13: the proposer has a statement line."""
    frontier = json.loads(raw(repo, branch, "frontier.json"))
    entries = {e["node_id"]: e for e in frontier.get("entries", [])}
    entry = entries.get(node_id)
    print(f"frontier.json: {len(entries)} entries; {node_id}: {'present' if entry else 'ABSENT'}")
    if entry is None:
        problems.append(f"{node_id} is not in frontier.json after the merge")
    else:
        print(f"  origin {entry.get('origin')} relation {entry.get('relation')}")
        if entry.get("origin") != "variant" or entry.get("relation") != "related":
            problems.append(f"the frontier entry is not a related variant: {entry}")
    try:
        ledger = json.loads(raw(repo, branch, f"ledger/{pseudonym}.json"))
    except Exception as exc:  # a missing ledger is a finding, not a crash
        problems.append(f"no ledger for {pseudonym} after the merge (F08-R13): {exc}")
        return
    lines = [e.get("line") for e in ledger.get("entries", [])]
    print(f"ledger/{pseudonym}.json: lines {lines}")
    if "statement" not in lines:
        problems.append("the proposer earned no statement line (F08-R13)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("url", help="the service's origin, e.g. https://api.openproofnetwork.org")
    parser.add_argument("--graph-repo", default=DEFAULT_GRAPH_REPO)
    parser.add_argument("--graph-branch", default="main")
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--github-token", default=None, help="merge the PR as this account")
    args = parser.parse_args(argv)
    base = args.url.rstrip("/")
    problems: list[str] = []

    status, health = call(f"{base}/health")
    print(f"GET /health -> {status} {health}")
    if status != 200:
        print("PROBLEM: the service is not healthy", file=sys.stderr)
        return 1

    target_id, tutorial, proof = find_tutorial_node(args.graph_repo, args.graph_branch)
    path = f"targets/{target_id}/nodes/{tutorial}/Proof.lean"
    print(f"tutorial node: {tutorial} in target {target_id}")
    token = mint_identity(base, tutorial, path, proof, args.timeout)
    if token is None:
        return 1
    status, proposed = call(
        f"{base}/proposals/variant",
        method="POST",
        token=token,
        body={
            "target_id": target_id,
            "statement": VARIANT_STATEMENT,
            "witness": VARIANT_WITNESS,
            "relation": "related",
        },
    )
    print(f"POST /proposals/variant -> {status} {proposed if status != 201 else ''}")
    if status != 201 or not isinstance(proposed, dict):
        print("PROBLEM: the proposal was not accepted", file=sys.stderr)
        return 1
    node_id, number = str(proposed["node_id"]), int(proposed["pr_number"])
    print(f"proposed {node_id}: {proposed['pr_url']}")

    head = check_pull_request(args.graph_repo, number, node_id, problems)
    pseudonym = ""
    status, commits = github(f"/repos/{args.graph_repo}/pulls/{number}/commits")
    if status == 200 and commits:
        pseudonym = str((commits[-1]["commit"].get("author") or {}).get("name") or "")
    run = wait_for_run(
        args.graph_repo,
        head_sha=head,
        event="pull_request",
        timeout_s=args.timeout,
        problems=problems,
    )
    if run.get("conclusion") != "success":
        problems.append(f"the gate did not pass the proposal: {run.get('conclusion')}")
    if problems:
        for p in problems:
            print(f"PROBLEM: {p}", file=sys.stderr)
        return 1

    merged = merge_or_wait(args.graph_repo, number, args.github_token, args.timeout, problems)
    if merged is not None:
        post = wait_for_run(
            args.graph_repo, head_sha=None, event="push", timeout_s=args.timeout, problems=problems
        )
        if post.get("conclusion") != "success":
            problems.append(f"the post-merge run did not succeed: {post.get('conclusion')}")
        time.sleep(POLL_INTERVAL_S)  # the bot commit lands after the run; raw reads lag a little
        check_products(args.graph_repo, args.graph_branch, node_id, pseudonym, problems)
    for p in problems:
        print(f"PROBLEM: {p}", file=sys.stderr)
    if merged is None and not problems:
        print(
            f"PENDING: PR #{number} is green and awaits a merge; the products are checked after it"
        )
        return EXIT_PENDING
    print("PASS" if not problems else "FAIL")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
