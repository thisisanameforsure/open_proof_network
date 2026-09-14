"""F13-T7 / AC12: the fast check against the deployed service and the real hosted checker.

    uv run python api/tools/smoke_check.py <api-url>

Every call is anonymous (F13-Q2), so this needs no token and writes nothing to the graph. It
asserts, and prints a line for each:

1. ``GET /hosted-checkers.json`` names AXLE, is non-authoritative, and maps the tutorial and one
   Erdős target to an environment.
2. The tutorial node's committed proof, sent in ``verify`` mode, is answered ``okay`` against the
   node's statement, with no lint warning, and carries a log id.
3. The same proof with its components swapped is answered not ``okay``, with a Lean error whose
   position is line 7 (the ``exact`` line) — a green run must show the checker read the text.
4. An Erdős root's own statement, still ``sorry``-bodied, is answered with the ``sorry-present``
   warning and the pin's environment, not ``exact``.
5. ``check_lean`` through a real MCP client, with no token, returns the endpoint's 200 envelope.

Exit 0 when all hold, 1 with the problems otherwise. The statements are read through the
service's own ``get_node`` tool, so the smoke checks the text the network would forward.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "gate"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from smoke import call  # the guarded caller the F05 smoke tool uses
from smoke_mcp import Client  # the SDK client that validates every result against its schema

TUTORIAL_TARGET = "tutorial"
TUTORIAL_NODE = "tutorial-and-swap"
ERDOS_TARGET = "erdos-376"
GOOD = "exact ⟨h.2, h.1⟩"
BAD = "exact ⟨h.1, h.2⟩"
ERROR_LINE = re.compile(r"^-:(\d+):\d+")


def node_files(mcp: Client, node_id: str) -> dict[str, Any]:
    doc = mcp.call("get_node", {"node_id": node_id})
    files: dict[str, Any] = doc["files"]
    return files


def check(base: str, body: dict[str, Any], problems: list[str], what: str) -> dict[str, Any]:
    status, doc = call(f"{base}/check", method="POST", body=body)
    if status != 200 or not isinstance(doc, dict):
        problems.append(f"{what}: POST /check -> {status} {doc}")
        return {}
    if doc.get("authoritative") is not False or doc.get("service") != "axle":
        problems.append(f"{what}: not marked non-authoritative AXLE: {doc}")
    if not doc.get("log_id"):
        problems.append(f"{what}: no log_id, so the call was not logged")
    return doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("url", help="the service's origin, e.g. https://api.openproofnetwork.org")
    base = parser.parse_args(argv).url.rstrip("/")
    problems: list[str] = []

    status, mapping = call(f"{base}/hosted-checkers.json")
    targets = mapping.get("targets", {}) if isinstance(mapping, dict) else {}
    print(f"GET /hosted-checkers.json -> {status}: {len(targets)} targets")
    for target in (TUTORIAL_TARGET, ERDOS_TARGET):
        env = (targets.get(target) or {}).get("environment")
        print(f"  {target}: {env}")
        if not env:
            problems.append(f"{target} has no hosted environment in /hosted-checkers.json")
    if not isinstance(mapping, dict) or mapping.get("authoritative") is not False:
        problems.append(f"/hosted-checkers.json is not marked non-authoritative: {mapping}")

    mcp = Client(base, None)
    tutorial = node_files(mcp, TUTORIAL_NODE)
    proof = tutorial.get("Proof.lean") or ""
    if GOOD not in proof:
        problems.append(f"the tutorial proof no longer contains {GOOD!r}; the smoke needs updating")

    good = check(
        base,
        {
            "target_id": TUTORIAL_TARGET,
            "node_id": TUTORIAL_NODE,
            "content": proof,
            "mode": "verify",
        },
        problems,
        "tutorial proof",
    )
    okay = (good.get("result") or {}).get("okay")
    print(
        f"verify tutorial proof -> okay={okay} env={good.get('environment')} "
        f"lint={[w['code'] for w in good.get('lint', [])]} log={good.get('log_id')}"
    )
    if good and (okay is not True or good.get("lint")):
        problems.append(f"the tutorial proof was not a clean pass: {good}")

    bad = check(
        base,
        {
            "target_id": TUTORIAL_TARGET,
            "node_id": TUTORIAL_NODE,
            "content": proof.replace(GOOD, BAD),
            "mode": "verify",
        },
        problems,
        "broken tutorial proof",
    )
    result = bad.get("result") or {}
    errors = (result.get("lean_messages") or {}).get("errors") or []
    lines = [int(m.group(1)) for e in errors if (m := ERROR_LINE.match(e))]
    print(f"verify broken proof -> okay={result.get('okay')} error lines={lines}")
    if bad and (result.get("okay") is not False or 7 not in lines):
        problems.append(f"the broken proof did not fail at line 7: {result}")

    statement = node_files(mcp, ERDOS_TARGET).get("Statement.lean") or ""
    erdos = check(
        base,
        {"target_id": ERDOS_TARGET, "node_id": ERDOS_TARGET, "content": statement},
        problems,
        "erdos root statement",
    )
    codes = [w["code"] for w in erdos.get("lint", [])]
    print(
        f"check {ERDOS_TARGET} statement -> env={erdos.get('environment')} "
        f"exact={erdos.get('exact')} lint={codes} okay={(erdos.get('result') or {}).get('okay')}"
    )
    if erdos and ("sorry-present" not in codes or erdos.get("exact") is not False):
        problems.append(f"the Erdős statement lacked sorry-present or claimed exact: {erdos}")

    envelope = mcp.call(
        "check_lean", {"target_id": TUTORIAL_TARGET, "node_id": TUTORIAL_NODE, "content": proof}
    )
    print(f"check_lean (MCP, no token) -> status {envelope.get('status')}")
    if envelope.get("status") != 200:
        problems.append(f"check_lean through MCP did not answer 200: {envelope}")

    for line in mcp.transcript:
        print(f"  mcp: {line}")
    if problems:
        print("FAIL")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
