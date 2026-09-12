#!/usr/bin/env python3
"""F11-T6 / R11, AC14: the invited-run readiness rehearsal.

    uv run python gate/tools/rehearsal.py <api-url> --node <on-ramp node> --proof FILE
        [--target ID] [--variant-statement FILE --variant-witness FILE]
        [--merge-timeout SECONDS] [--site https://host] [--out FILE] [--timeout SECONDS]

Both paths a contributor has — the plain HTTP routes and the MCP tools — driven end to end with
a test identity each, on an on-ramp node: claim, precheck, submit; a postmortem; a variant
proposal; then the wait for the root to close when its last hole merges, and the site reflecting
it. Every step is timed and written to the readiness record (default
``engineering/evidence/F11/invited-run-readiness.txt``).

What it cannot do itself is merge: nothing merges on green (F07-Q16), so the pull requests it
opens wait for a person, and the root-closing step reports *pending* until the merges land —
run it again with ``--merge-timeout`` once they have. Exit 0 when every step passed, 2 when
something is pending (a step skipped for want of an input, the merge, a site not yet
redeployed), 1 on a failure.

The identity is minted the account-free way (D-19: an anonymous precheck of the tutorial node),
so this needs no GitHub account. HTTP is the standard library through the smoke tools' guarded
caller (C5); the MCP path is the official SDK client, the same one Claude Code speaks.
"""

from __future__ import annotations

import argparse
import secrets
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "api" / "tools"))
sys.path.insert(0, str(ROOT / "api"))
sys.path.insert(0, str(ROOT / "gate"))

from smoke import call  # noqa: E402 — the guarded caller the smoke tools share
from smoke_mcp import Client  # noqa: E402
from smoke_precheck import exchange, wait_for  # noqa: E402

DEFAULT_OUT = ROOT / "engineering" / "evidence" / "F11" / "invited-run-readiness.txt"
EXIT_OK, EXIT_FAIL, EXIT_PENDING = 0, 1, 2
POLL_S = 15


@dataclass
class Step:
    name: str
    status: str  # ok | pending | skipped | failed
    seconds: float
    detail: str = ""


@dataclass
class Record:
    base: str
    steps: list[Step] = field(default_factory=list)

    def add(self, name: str, status: str, started: float, detail: str = "") -> Step:
        step = Step(name, status, time.monotonic() - started, detail)
        self.steps.append(step)
        print(f"{step.seconds:7.1f}s  {status:<8} {name}  {detail}", flush=True)
        return step

    @property
    def exit_code(self) -> int:
        if any(s.status == "failed" for s in self.steps):
            return EXIT_FAIL
        if any(s.status in ("pending", "skipped") for s in self.steps):
            return EXIT_PENDING  # R11 wants every step; a skipped one is not yet rehearsed
        return EXIT_OK

    def render(self) -> str:
        lines = [
            "F11-T6 — invited-run readiness rehearsal (R11; AC14)",
            f"service: {self.base}",
            f"run at: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
            "",
            f"{'seconds':>8}  {'status':<8} step",
        ]
        for s in self.steps:
            lines.append(
                f"{s.seconds:8.1f}  {s.status:<8} {s.name}"
                + (f"  — {s.detail}" if s.detail else "")
            )
        verdict = {EXIT_OK: "READY", EXIT_PENDING: "PENDING", EXIT_FAIL: "NOT READY"}[
            self.exit_code
        ]
        lines += ["", f"verdict: {verdict}"]
        return "\n".join(lines) + "\n"


# --- what the graph says -------------------------------------------------------------------------


def frontier(base: str) -> list[dict[str, Any]]:
    status, doc = call(f"{base}/frontier.json")
    if status != 200 or not isinstance(doc, dict):
        msg = f"GET /frontier.json -> {status}"
        raise RuntimeError(msg)
    return list(doc.get("entries", []))


def tutorial_node(mcp: Client) -> tuple[str, str, str]:
    """(target, node, Proof.lean) of the tutorial node, read through the service (D-27)."""
    targets = mcp.call("list_targets")
    targets.pop("__is_error__")
    for t in targets.get("targets", []):
        graph = mcp.call("get_target", {"target_id": t["target_id"]})
        graph.pop("__is_error__")
        for node in graph.get("graph", {}).get("nodes", []):
            if node.get("tutorial"):
                bundle = mcp.call("get_node", {"node_id": node["node_id"]})
                bundle.pop("__is_error__")
                proof = (bundle.get("files") or {}).get("Proof.lean")
                if not isinstance(proof, str):
                    msg = "the tutorial node's bundle carries no Proof.lean"
                    raise RuntimeError(msg)
                return str(t["target_id"]), str(node["node_id"]), proof
    msg = "no target marks a tutorial node; D-19's proof has nowhere to run"
    raise RuntimeError(msg)


def node_path(target_id: str, node_id: str, name: str) -> str:
    return f"targets/{target_id}/nodes/{node_id}/{name}"


# --- the two paths --------------------------------------------------------------------------------


def mint(base: str, tutorial: tuple[str, str, str], label: str, timeout: int) -> str:
    """D-19: an anonymous precheck of the tutorial node buys one write token."""
    target, node, proof = tutorial
    status, job = call(
        f"{base}/precheck",
        method="POST",
        body={"node_id": node, "bundle": {node_path(target, node, "Proof.lean"): proof}},
    )
    if status != 202 or not job.get("nonce"):
        msg = f"anonymous precheck -> {status} {job}"
        raise RuntimeError(msg)
    final, _ = wait_for(base, str(job["id"]), timeout)
    if (final.get("result") or {}).get("verdict") != "pass":
        msg = f"the identity-minting precheck did not pass: {final.get('state')}"
        raise RuntimeError(msg)
    _, dco = call(f"{base}/dco.json")
    pseudonym = f"rehearsal-{label}-{secrets.token_hex(3)}"
    version = dco.get("version") if isinstance(dco, dict) else None
    status, issued = exchange(base, str(job["id"]), str(job["nonce"]), pseudonym, version)
    if status != 201 or not isinstance(issued, dict) or not issued.get("token"):
        msg = f"POST /tokens -> {status} {issued}"
        raise RuntimeError(msg)
    return str(issued["token"])


class HttpPath:
    """The plain routes, as a script or a curl would use them (D-35)."""

    name = "http"

    def __init__(self, base: str, token: str, timeout: int) -> None:
        self.base, self.token, self.timeout = base, token, timeout

    def claim(self, node: str) -> str:
        status, body = call(
            f"{self.base}/claims", method="POST", token=self.token, body={"node_id": node}
        )
        if status == 201:
            return f"claim {body['id']}"
        if status == 409:
            return f"conflict: {body.get('error_description') or body.get('error')}"
        msg = f"POST /claims -> {status} {body}"
        raise RuntimeError(msg)

    def precheck_and_submit(self, target: str, node: str, proof: str) -> str:
        path = node_path(target, node, "Proof.lean")
        body = {"node_id": node, "bundle": {path: proof}}
        status, job = call(f"{self.base}/precheck", method="POST", token=self.token, body=body)
        if status != 202:
            msg = f"POST /precheck -> {status} {job}"
            raise RuntimeError(msg)
        final, _ = wait_for(self.base, str(job["id"]), self.timeout)
        verdict = (final.get("result") or {}).get("verdict")
        if verdict != "pass":
            msg = f"precheck {job['id']}: {final.get('state')} {verdict}"
            raise RuntimeError(msg)
        status, sub = call(
            f"{self.base}/submissions",
            method="POST",
            token=self.token,
            body={
                "node_id": node,
                "artifact_type": "proof",
                "bundle": {path: proof},
                "precheck_job_id": job["id"],
                "tooling": {"harness": "rehearsal.py"},
            },
        )
        if status != 201:
            msg = f"POST /submissions -> {status} {sub}"
            raise RuntimeError(msg)
        return f"precheck {job['id']} pass; PR {sub.get('pr_url') or sub.get('pr_number')}"

    def postmortem(self, node: str) -> str:
        doc = {
            "schema": "postmortem/v1",
            "node": node,
            "route": "rehearsal: the invited-run readiness run's attempt record",
            "route_class": "direct-estimate",
            "outcome": "abandoned-early",
            "detail": "Written by gate/tools/rehearsal.py (F11-T6) on the HTTP path.",
        }
        status, body = call(
            f"{self.base}/postmortems",
            method="POST",
            token=self.token,
            body={"node_id": node, "yaml": doc},
        )
        if status != 201:
            msg = f"POST /postmortems -> {status} {body}"
            raise RuntimeError(msg)
        return f"PR {body.get('pr_url') or body.get('pr_number')}"

    def variant(self, target: str, statement: str, witness: str) -> str:
        status, body = call(
            f"{self.base}/proposals/variant",
            method="POST",
            token=self.token,
            body={
                "target_id": target,
                "statement": statement,
                "witness": witness,
                "relation": "related",
            },
        )
        if status != 201:
            msg = f"POST /proposals/variant -> {status} {body}"
            raise RuntimeError(msg)
        return f"node {body.get('node_id')}; PR {body.get('pr_url') or body.get('pr_number')}"


class McpPath:
    """The same acts through D-28's tools, with the SDK client (F09)."""

    name = "mcp"

    def __init__(self, base: str, token: str, timeout: int) -> None:
        self.base, self.timeout = base, timeout
        self.client = Client(base, token)

    def _ok(self, name: str, args: dict[str, Any], wanted: int = 201) -> dict[str, Any]:
        result = self.client.call(name, args)
        if result.pop("__is_error__") or result.get("status") != wanted:
            msg = f"{name} -> {result}"
            raise RuntimeError(msg)
        body = result.get("body")
        return body if isinstance(body, dict) else {}

    def claim(self, node: str) -> str:
        result = self.client.call("claim_node", {"node_id": node})
        result.pop("__is_error__")
        if result.get("status") == 201:
            return f"claim {result['body']['id']}"
        if result.get("status") == 409:
            return f"conflict: {result.get('body', {}).get('error')}"
        msg = f"claim_node -> {result}"
        raise RuntimeError(msg)

    def precheck_and_submit(self, target: str, node: str, proof: str) -> str:
        path = node_path(target, node, "Proof.lean")
        job = self._ok("precheck_submission", {"node_id": node, "bundle": {path: proof}}, 202)
        final, _ = wait_for(self.base, str(job["id"]), self.timeout)
        if (final.get("result") or {}).get("verdict") != "pass":
            msg = f"precheck {job['id']}: {final.get('state')}"
            raise RuntimeError(msg)
        sub = self._ok(
            "submit_proof",
            {
                "node_id": node,
                "artifact_type": "proof",
                "bundle": {path: proof},
                "attestation": final,  # the get_precheck result; its id binds the submission
                "tooling": {"harness": "rehearsal.py"},
            },
        )
        return f"precheck {job['id']} pass; PR {sub.get('pr_url') or sub.get('pr_number')}"

    def postmortem(self, node: str) -> str:
        doc = {
            "schema": "postmortem/v1",
            "node": node,
            "route": "rehearsal: the invited-run readiness run's attempt record (MCP path)",
            "route_class": "direct-estimate",
            "outcome": "abandoned-early",
            "detail": "Written by gate/tools/rehearsal.py (F11-T6) through submit_postmortem.",
        }
        body = self._ok("submit_postmortem", {"node_id": node, "yaml": doc})
        return f"PR {body.get('pr_url') or body.get('pr_number')}"

    def variant(self, target: str, statement: str, witness: str) -> str:
        # A variant's id is a hash of its statement (F08-R3), so the MCP path's proposal is
        # marked, or it would name the node the HTTP path just proposed.
        statement = statement.rstrip("\n") + "\n-- proposed on the MCP path\n"
        body = self._ok(
            "propose_variant",
            {"target_id": target, "stmt": statement, "witness": witness, "relation": "related"},
        )
        return f"node {body.get('node_id')}; PR {body.get('pr_url') or body.get('pr_number')}"


# --- the run --------------------------------------------------------------------------------------


def choose_node(
    entries: list[dict[str, Any]], target: str | None, node: str | None
) -> tuple[str, str]:
    if node is not None:
        match = [e for e in entries if e.get("node_id") == node]
        if not match:
            msg = f"{node} is not on the frontier"
            raise RuntimeError(msg)
        return str(match[0]["target_id"]), node
    claimable = [
        e
        for e in entries
        if e.get("claimable") and (target is None or e.get("target_id") == target)
    ]
    if not claimable:
        msg = "the frontier has no claimable node" + (f" on {target}" if target else "")
        raise RuntimeError(msg)
    return str(claimable[0]["target_id"]), str(claimable[0]["node_id"])


def root_closed(mcp: Client, target: str) -> tuple[bool, str]:
    graph = mcp.call("get_target", {"target_id": target})
    graph.pop("__is_error__")
    doc = graph.get("graph", {})
    root = next((n for n in doc.get("nodes", []) if n.get("node_id") == doc.get("root")), None)
    if root is None:
        return False, f"no node is the root {doc.get('root')!r}"
    return root.get("status") == "proved", f"root {root['node_id']} is {root.get('status')}"


def check_site(site: str, target: str, node: str, base: str) -> tuple[str, str]:
    """The site names the same graph commit the service renders from, and both pages load."""
    _s, doc = call(f"{base}/frontier.json")
    rendered = str(doc.get("rendered_from", "")) if isinstance(doc, dict) else ""
    req = urllib.request.Request(  # noqa: S310
        f"{site}/rendered-from.txt", headers={"User-Agent": "opn-rehearsal"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        live = resp.read().decode().strip()
    for path in (f"/targets/{target}/", f"/nodes/{target}/{node}/"):
        req = urllib.request.Request(site + path, headers={"User-Agent": "opn-rehearsal"})  # noqa: S310
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            if resp.status != 200:
                return "failed", f"{path} -> {resp.status}"
    if rendered and live and not (live.startswith(rendered) or rendered.startswith(live)):
        return (
            "pending",
            f"site renders {live[:12]}, service renders {rendered[:12]}: a redeploy behind",
        )
    return "ok", f"site at {live[:12]}; target and node pages load"


def acts(
    path: HttpPath | McpPath,
    target: str,
    node: str,
    proof: str | None,
    variant: tuple[str, str] | None,
) -> list[tuple[str, Callable[[], str], str | None]]:
    """The four acts on one path, each with the reason it is skipped when an input is missing."""
    return [
        ("claim", lambda: path.claim(node), None),
        (
            "precheck+submit",
            lambda: path.precheck_and_submit(target, node, proof or ""),
            None if proof is not None else "no --proof given",
        ),
        ("postmortem", lambda: path.postmortem(node), None),
        (
            "variant",
            lambda: path.variant(target, *(variant or ("", ""))),
            None if variant is not None else "no --variant-statement/--variant-witness",
        ),
    ]


def run(args: argparse.Namespace) -> Record:
    base = args.url.rstrip("/")
    record = Record(base)
    anonymous = Client(base, None)
    t0 = time.monotonic()
    try:
        entries = frontier(base)
        tutorial = tutorial_node(anonymous)
        target, node = choose_node(entries, args.target, args.node)
        record.add(
            "frontier",
            "ok",
            t0,
            f"{len(entries)} entries; node {node} on {target}; tutorial {tutorial[1]}",
        )
    except RuntimeError as exc:
        record.add("frontier", "failed", t0, str(exc))
        return record
    proof = args.proof.read_text(encoding="utf-8") if args.proof else None
    variant = (
        (
            args.variant_statement.read_text(encoding="utf-8"),
            args.variant_witness.read_text(encoding="utf-8"),
        )
        if args.variant_statement and args.variant_witness
        else None
    )

    paths: list[HttpPath | McpPath] = []
    for label, factory in (("http", HttpPath), ("mcp", McpPath)):
        t = time.monotonic()
        try:
            token = mint(base, tutorial, label, args.timeout)
            paths.append(factory(base, token, args.timeout))
            record.add(f"identity:{label}", "ok", t, "tutorial precheck -> token (D-19)")
        except RuntimeError as exc:
            record.add(f"identity:{label}", "failed", t, str(exc))
    for path in paths:
        for step, act, skipped in acts(path, target, node, proof, variant):
            t = time.monotonic()
            if skipped is not None:
                record.add(f"{step}:{path.name}", "skipped", t, skipped)
                continue
            try:
                record.add(f"{step}:{path.name}", "ok", t, act())
            except (RuntimeError, AssertionError, KeyError, TypeError) as exc:
                record.add(f"{step}:{path.name}", "failed", t, str(exc)[:300])

    t = time.monotonic()
    deadline = t + args.merge_timeout
    closed, detail = root_closed(anonymous, target)
    while not closed and time.monotonic() < deadline:
        time.sleep(POLL_S)
        closed, detail = root_closed(anonymous, target)
    record.add(
        "root-closes",
        "ok" if closed else "pending",
        t,
        detail + ("" if closed else "; waits on the merges (nothing merges on green, F07-Q16)"),
    )

    t = time.monotonic()
    if args.site:
        try:
            status, detail = check_site(args.site.rstrip("/"), target, node, base)
        except (urllib.error.URLError, OSError) as exc:
            status, detail = "failed", str(exc)
        record.add("site", status, t, detail)
    else:
        record.add("site", "skipped", t, "no --site given")
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("url", help="the service's origin")
    parser.add_argument(
        "--target", help="the on-ramp target (default: the first with a claimable node)"
    )
    parser.add_argument(
        "--node", help="the on-ramp node to claim and submit on (default: the first claimable)"
    )
    parser.add_argument("--proof", type=Path, help="Proof.lean to precheck and submit on that node")
    parser.add_argument("--variant-statement", type=Path, help="a related variant's Statement.lean")
    parser.add_argument("--variant-witness", type=Path, help="its Witness.lean")
    parser.add_argument(
        "--merge-timeout", type=int, default=0, help="seconds to wait for the root to close"
    )
    parser.add_argument("--site", help="the site's origin, e.g. https://openproofnetwork.org")
    parser.add_argument("--timeout", type=int, default=900, help="seconds per precheck job")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="the readiness record")
    args = parser.parse_args(argv)
    base = args.url.rstrip("/")
    if not base.startswith("https://") and not base.startswith("http://127.0.0.1"):
        parser.error("only https (or a local runner) is rehearsed")
    record = run(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(record.render(), encoding="utf-8")
    print(f"\n{record.render()}wrote {args.out}")
    return record.exit_code


if __name__ == "__main__":
    sys.exit(main())
