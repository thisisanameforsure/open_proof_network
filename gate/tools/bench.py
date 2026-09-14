"""F14-T13: a local bench a fresh agent can work against, and the replay that grades what it did.

    uv run python gate/tools/bench.py seed   --graph <graph checkout> --bench <dir>
    uv run python gate/tools/bench.py serve  --bench <dir>            # prints the two URLs
    uv run python gate/tools/bench.py replay --bench <dir> [--assert]

Promoted from the 2026-09-12 tester's ``bench.py`` and ``check.py``
(``engineering/session-notes/2026-09-12-erdos-376-tester/``).

``seed`` clones the graph into ``<dir>/graph``, makes a throwaway precheck key and renders the
baseline site into ``<dir>/site-base``.

``serve`` runs the real api over the test suite's fake git host, seeded with that clone, on an
ephemeral loopback port, and serves the baseline site on another. It writes both URLs to
``<dir>/urls.json`` and dumps the host's pushes, pull requests and dispatches, and the store's
identities and claims, to ``<dir>/records/`` every few seconds. Every precheck passes at once, so a
pass on the bench says nothing about the Lean.

``replay`` materialises each recorded push as a branch off ``main`` and runs the gate's own
``classify`` over it. Pushes that build nothing (append, explainer) are merged onto one branch, and
proposals are merged marked unadmitted. Then it regenerates the products and re-renders the site
from that branch, and writes ``<dir>/check/report.json`` with the frontier and page changes.
Products and pages are rendered in process, so the replay needs no Lean toolchain and no Docker.
With ``--assert`` it exits 1 when a push is refused by ``classify`` or when the products or the
site do not render.

Nothing here touches a live host: the graph is a local clone, and the service's writes go to the
fake host's memory.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import dataclasses
import difflib
import functools
import html
import http.server
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
for sub in ("gate", "api", "site", "gate/tests", "api/tests"):
    if str(ROOT / sub) not in sys.path:
        sys.path.insert(0, str(ROOT / sub))

from api_fakes import make_harness, make_precheck_key  # noqa: E402
from test_walkthrough import AutoRunGitHost, tree_files  # noqa: E402

from opn_api import local  # noqa: E402
from opn_api.clock import SystemClock  # noqa: E402
from opn_gate import products  # noqa: E402
from opn_site import model, render  # noqa: E402

BUILDS_NOTHING = ("append", "explainer", "proposal")
REPO_URL = "https://github.com/bench/graph"
GIT_ENV = {**{k: v for k, v in os.environ.items() if not k.startswith("GIT_")}, "TZ": "UTC"}


def _run(
    *args: str, cwd: Path | None = None, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args), cwd=cwd, env=GIT_ENV, check=check, capture_output=True, text=True
    )


def git(repo: Path, *args: str, check: bool = True) -> str:
    return _run("git", "-C", str(repo), *args, check=check).stdout.strip()


def render_site(graph: Path, commit: str, out: Path) -> int:
    """Write every page the site generator renders for ``graph`` at ``commit``; the page count."""
    pages = render.render_site(model.load_site(graph, commit), repo_url=REPO_URL)
    for rel, text in pages.items():
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return len(pages)


# --- seed --------------------------------------------------------------------------------------


def seed(graph: Path, bench: Path) -> dict[str, Any]:
    bench.mkdir(parents=True, exist_ok=True)
    clone = bench / "graph"
    if clone.exists():
        raise SystemExit(f"{clone} exists; seed a fresh bench directory")
    _run("git", "clone", "-q", "--no-hardlinks", str(graph), str(clone))
    git(clone, "checkout", "-q", "-B", "main")
    make_precheck_key(bench, "precheck-key")
    base = git(clone, "rev-parse", "HEAD")
    pages = render_site(clone, base, bench / "site-base")
    doc = {"graph": str(clone), "base": base, "pages": pages}
    (bench / "bench.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return doc


# --- serve -------------------------------------------------------------------------------------


@dataclasses.dataclass
class Served:
    api_url: str
    site_url: str
    host: Any
    store: Any
    records: Path
    _loop: asyncio.AbstractEventLoop
    _site: http.server.ThreadingHTTPServer

    def dump(self) -> None:
        self.records.mkdir(parents=True, exist_ok=True)

        def write(name: str, doc: Any) -> None:
            (self.records / name).write_text(json.dumps(doc, indent=2, default=str) + "\n")

        write("pushes.json", [dataclasses.asdict(p) for p in self.host.pushes])
        write("pulls.json", [dataclasses.asdict(p) for p in self.host.pulls])
        write("dispatches.json", [dataclasses.asdict(d) for d in self.host.dispatches])
        write(
            "store.json",
            {
                "identities": [dataclasses.asdict(i) for i in self.store.identities.values()],
                "claims": [dataclasses.asdict(c) for c in self.store.claims.values()],
            },
        )

    def stop(self) -> None:
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._site.shutdown()


def start(bench: Path) -> Served:
    """The api and the baseline site on two ephemeral loopback ports, in daemon threads."""
    clone = bench / "graph"
    key = make_precheck_key(bench, f"serve-key-{os.getpid()}-{time.monotonic_ns()}")
    files = tree_files(clone)
    files["keys/precheck.pub"] = (key.public + "\n").encode()
    host = AutoRunGitHost(files, key)

    ready: queue.Queue[int] = queue.Queue()
    loop = asyncio.new_event_loop()
    holder: dict[str, Any] = {}

    async def main() -> None:
        async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            await local.serve_connection(holder["app"], reader, writer)

        server = await asyncio.start_server(handle, "127.0.0.1", 0, limit=local.MAX_HEADER_BYTES)
        ready.put(server.sockets[0].getsockname()[1])
        async with server:
            await server.serve_forever()

    def run() -> None:
        with contextlib.suppress(RuntimeError):  # loop.stop()
            loop.run_until_complete(main())

    # The api needs its public URL at construction, so the port is bound first and the app is
    # built before the first connection can arrive.
    thread = threading.Thread(target=run, daemon=True, name="opn-bench-api")
    thread.start()
    port = ready.get(timeout=30)
    api_url = f"http://127.0.0.1:{port}"
    harness = make_harness(githost=host, clock=SystemClock(), env={"OPN_API_PUBLIC_URL": api_url})
    holder["app"] = harness.app

    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(bench / "site-base")
    )
    handler.log_message = lambda *_a, **_k: None  # type: ignore[attr-defined]
    site = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=site.serve_forever, daemon=True, name="opn-bench-site").start()
    site_url = f"http://127.0.0.1:{site.server_address[1]}/"

    served = Served(api_url, site_url, host, harness.store, bench / "records", loop, site)
    (bench / "urls.json").write_text(
        json.dumps({"api": api_url, "mcp": f"{api_url}/mcp", "site": site_url}, indent=2) + "\n"
    )
    served.dump()
    return served


def serve(bench: Path, every: float) -> None:
    served = start(bench)
    print(json.dumps({"api": served.api_url, "site": served.site_url}), flush=True)
    try:
        while True:
            time.sleep(every)
            served.dump()
    except KeyboardInterrupt:
        served.dump()
        served.stop()


# --- replay ------------------------------------------------------------------------------------


def _worktree(clone: Path, path: Path) -> Path:
    if path.exists():
        git(clone, "worktree", "remove", "--force", str(path), check=False)
    git(clone, "worktree", "add", "-q", "--detach", str(path), "main")
    return path


def _write(tree: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        target = tree / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def _commit(tree: Path, message: str, author: dict[str, Any] | None) -> str:
    name = (author or {}).get("name") or "bench"
    email = (author or {}).get("email") or "bench@example.invalid"
    git(tree, "add", "-A")
    git(tree, "-c", f"user.name={name}", "-c", f"user.email={email}",
        "commit", "-q", "--allow-empty", "-m", message)  # fmt: skip
    return git(tree, "rev-parse", "HEAD")


def _classify(tree: Path, base: str, head: str) -> dict[str, Any]:
    env = {**GIT_ENV, "PYTHONPATH": str(ROOT / "gate")}
    done = subprocess.run(
        [sys.executable, "-m", "opn_gate.cli", "classify", "--graph", str(tree),
         "--base", base, "--head", head],
        env=env, capture_output=True, text=True, check=False,
    )  # fmt: skip
    try:
        doc: dict[str, Any] = json.loads(done.stdout)
    except json.JSONDecodeError:
        return {"error": (done.stdout + done.stderr)[-2000:]}
    return doc


def _page_text(page: Path) -> list[str]:
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", page.read_text("utf-8"), flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return [line for line in lines if line and "Rendered from graph commit" not in line]


def _frontier_changes(before: Path, after: Path) -> dict[str, Any]:
    def entries(path: Path) -> dict[str, Any]:
        if not path.is_file():
            return {}
        return {e["node_id"]: e for e in json.loads(path.read_text("utf-8"))["entries"]}

    old, new = entries(before), entries(after)
    changes: dict[str, Any] = {}
    for node in sorted(set(old) | set(new)):
        if node not in old:
            changes[node] = "ADDED"
        elif node not in new:
            changes[node] = "REMOVED"
        else:
            diff = {k: [old[node].get(k), new[node].get(k)]
                    for k in sorted(set(old[node]) | set(new[node]))
                    if old[node].get(k) != new[node].get(k)}  # fmt: skip
            if diff:
                changes[node] = diff
    return changes


def replay(bench: Path) -> dict[str, Any]:  # noqa: PLR0915 — one replay, read top to bottom
    clone = bench / "graph"
    records = bench / "records"
    pushes = json.loads((records / "pushes.json").read_text("utf-8"))
    pulls = json.loads((records / "pulls.json").read_text("utf-8"))
    base = git(clone, "rev-parse", "main")
    work = bench / "check"
    work.mkdir(exist_ok=True)
    merged = _worktree(clone, work / "wt-merged")
    report: dict[str, Any] = {"base": base, "pushes": [], "applied": [], "skipped": [],
                              "refused": []}  # fmt: skip

    jobs = [p for p in pushes if "job.json" in p["files"]]
    report["precheck_jobs"] = len(jobs)
    for n, push in enumerate((p for p in pushes if "job.json" not in p["files"]), 1):
        pr = next((p for p in pulls if p["head"] == push["branch"]), None)
        tree = _worktree(clone, work / f"wt-push-{n}")
        _write(tree, push["files"])
        head = _commit(tree, push["message"], push.get("author"))
        classification = _classify(tree, base, head)
        mode = classification.get("mode")
        entry = {"n": n, "branch": push["branch"], "message": push["message"], "pr": pr,
                 "files": sorted(push["files"]), "classification": classification}  # fmt: skip
        problems = classification.get("problems")
        if problems == [] and mode in BUILDS_NOTHING:
            _write(merged, push["files"])
            title = pr["title"] if pr else push["message"]
            message = f"Merge (replayed) #{n}: {title}"
            entry["applied"] = _commit(merged, message, push.get("author"))
            entry["admitted"] = mode != "proposal"
            report["applied"].append(n)
        elif problems == []:
            report["skipped"].append({"n": n, "mode": mode, "why": "needs the gate's toolchain"})
        else:
            # A push in a mode can still carry problems; that is a refusal, never a skip.
            codes = [p.get("code") for p in problems or []]
            report["refused"].append({"n": n, "mode": mode, "problems": codes or classification})
        report["pushes"].append(entry)
        git(clone, "worktree", "remove", "--force", str(tree), check=False)

    head = git(merged, "rev-parse", "HEAD")
    stamp = "--date=format-local:%Y-%m-%dT%H:%M:%SZ"  # TZ=UTC in GIT_ENV makes the Z true
    commit_time = git(merged, "show", "-s", "--format=%cd", stamp, "HEAD")
    try:
        products.generate(merged, rendered_from=head, commit_time=commit_time).write(merged)
        report["products"] = {"ok": True}
    except Exception as exc:  # the report names whatever stopped the products
        report["products"] = {"ok": False, "error": repr(exc)}
    site_out = work / "site-merged"
    try:
        report["site"] = {"ok": True, "pages": render_site(merged, head, site_out)}
    except Exception as exc:  # as above
        report["site"] = {"ok": False, "error": repr(exc)}

    base_site = bench / "site-base"
    pages: dict[str, str] = {}
    if site_out.exists():
        old = {p.relative_to(base_site).as_posix() for p in base_site.rglob("*.html")}
        new = {p.relative_to(site_out).as_posix() for p in site_out.rglob("*.html")}
        pages.update(dict.fromkeys(sorted(new - old), "ADDED"))
        pages.update(dict.fromkeys(sorted(old - new), "REMOVED"))
        for page in sorted(old & new):
            a, b = _page_text(base_site / page), _page_text(site_out / page)
            if a != b:
                pages[page] = "\n".join(difflib.unified_diff(a, b, lineterm="", n=1))
    report["site_changes"] = pages
    report["frontier_changes"] = _frontier_changes(
        clone / "frontier.json", merged / "frontier.json"
    )
    (work / "report.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    return report


def failures(report: dict[str, Any]) -> list[str]:
    """What ``--assert`` refuses: a push ``classify`` refused, products or pages that did not
    render."""
    found = [f"push {r['n']} refused: {r['problems']}" for r in report["refused"]]
    for part in ("products", "site"):
        if not report[part]["ok"]:
            found.append(f"{part} did not render: {report[part]['error']}")
    return found


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("seed", help="clone a graph and render the baseline site")
    s.add_argument("--graph", required=True, type=Path)
    s.add_argument("--bench", required=True, type=Path)
    v = sub.add_parser("serve", help="serve the api and the site until interrupted")
    v.add_argument("--bench", required=True, type=Path)
    v.add_argument("--every", type=float, default=3.0, help="seconds between record dumps")
    r = sub.add_parser("replay", help="classify and merge the recorded pushes, then re-render")
    r.add_argument("--bench", required=True, type=Path)
    r.add_argument("--assert", dest="check", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "seed":
        print(json.dumps(seed(args.graph.resolve(), args.bench.resolve())))
        return 0
    if args.command == "serve":
        serve(args.bench.resolve(), args.every)
        return 0
    report = replay(args.bench.resolve())
    summary = {k: report[k] for k in ("base", "applied", "skipped", "refused", "frontier_changes")}
    print(json.dumps(summary, indent=2, default=str))
    print("site pages changed:", sorted(report["site_changes"]))
    problems = failures(report)
    for problem in problems:
        print(f"FAIL {problem}", file=sys.stderr)
    return 1 if args.check and problems else 0


if __name__ == "__main__":
    sys.exit(main())
