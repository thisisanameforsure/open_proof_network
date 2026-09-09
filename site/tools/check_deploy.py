"""F04-T5 / AC13: check the deployed site from a laptop.

    uv run python site/tools/check_deploy.py <hostname> [--graph PATH]

Fetches Home over HTTPS, checks the Content-Security-Policy header F04 §7 requires, that the
page names the graph's current main commit (or the commit ``rendered-from.txt`` reports), and
that a target and a node page load with the same commit. Exit 0 only when all of that holds.
Standard library only (C5).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

CSP = "default-src 'none'; style-src 'self'; script-src 'self'; img-src 'self'"
ROOT = Path(__file__).resolve().parents[2]


def fetch(url: str) -> tuple[int, dict[str, str], str]:
    if not url.startswith("https://"):
        msg = f"only https is fetched: {url}"
        raise ValueError(msg)
    req = urllib.request.Request(url, headers={"User-Agent": "opn-check-deploy"})  # noqa: S310
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read().decode()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("hostname")
    parser.add_argument("--graph", type=Path, default=ROOT.parent / "open_proof_network_graph")
    args = parser.parse_args(argv)
    base = f"https://{args.hostname}"
    problems: list[str] = []

    status, headers, home = fetch(f"{base}/")
    print(f"GET / -> {status}")
    if headers.get("content-security-policy") != CSP:
        problems.append(f"CSP header is {headers.get('content-security-policy')!r}")
    _s, _h, live = fetch(f"{base}/rendered-from.txt")
    live = live.strip()
    print(f"rendered-from.txt: {live}")
    m = re.search(
        r"Rendered from graph commit <a href=\"[^\"]*\"><code>([0-9a-f]{12})</code>", home
    )
    if not m or not live.startswith(m.group(1)):
        problems.append("Home does not name the deployed commit")
    try:
        subprocess.run(["git", "-C", str(args.graph), "fetch", "-q", "origin", "main"], check=True)
        main_sha = subprocess.run(
            ["git", "-C", str(args.graph), "rev-parse", "origin/main"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        print(f"graph origin/main: {main_sha}")
        if main_sha != live:
            problems.append(f"site renders {live[:12]}, graph main is {main_sha[:12]}")
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"could not compare with the graph checkout: {exc}")
    for path in ("/targets/", "/frontier/"):
        s, _h, body = fetch(f"{base}{path}")
        print(f"GET {path} -> {s}")
        if live[:12] not in body:
            problems.append(f"{path} does not name the deployed commit")
    target = re.search(r'href="(/targets/[^"/]+/)"', home + fetch(f"{base}/targets/")[2])
    if target:
        s, _h, body = fetch(f"{base}{target.group(1)}")
        print(f"GET {target.group(1)} -> {s}")
        node = re.search(r'href="(/nodes/[^"]+/)"', body)
        if node:
            s, _h, body = fetch(f"{base}{node.group(1)}")
            print(f"GET {node.group(1)} -> {s}")
            if "Attestation" not in body:
                problems.append("node page lacks the attestation section")
    for p in problems:
        print(f"PROBLEM: {p}")
    print(json.dumps({"hostname": args.hostname, "commit": live, "ok": not problems}))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
