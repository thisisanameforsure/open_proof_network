"""Replay the tester's writes onto the graph clone and see what the record and the site make of
them.

For each push the fake host recorded: materialise it as a branch off main, run the pinned gate's
own ``classify`` over it, and — for the modes that build nothing (append, explainer) and, marked
as *unadmitted*, proposals — merge it onto a cumulative branch. Then regenerate the products and
re-render the site from that branch, and diff against the baseline render.
"""

from __future__ import annotations

import difflib
import html
import json
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path("/home/user/open_proof_network")
S = pathlib.Path(__file__).resolve().parent
GRAPH = S / "graph"
RECORDS = S / "records"
OUT = S / "check"
OUT.mkdir(exist_ok=True)

ENV = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
ENV["PYTHONPATH"] = str(ROOT / "gate")


def sh(
    *args: str, cwd: pathlib.Path | None = None, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(args), cwd=cwd, env=ENV, check=check, capture_output=True, text=True)


def git(wt: pathlib.Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return sh("git", "-C", str(wt), *args, check=check)


def gate(*args: str) -> subprocess.CompletedProcess[str]:
    return sh("uv", "run", "--frozen", "python", "-m", "opn_gate.cli", *args, cwd=ROOT, check=False)


def worktree(name: str) -> pathlib.Path:
    wt = S / name
    if wt.exists():
        git(GRAPH, "worktree", "remove", "--force", str(wt), check=False)
    git(GRAPH, "worktree", "add", "-q", "--detach", str(wt), "main")
    return wt


def write_files(wt: pathlib.Path, files: dict[str, str]) -> None:
    for path, text in files.items():
        p = wt / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


def commit(wt: pathlib.Path, message: str, author: dict | None) -> str:
    name = (author or {}).get("name") or "tester"
    email = (author or {}).get("email") or "tester@example.invalid"
    git(wt, "add", "-A")
    git(
        wt,
        "-c",
        f"user.name={name}",
        "-c",
        f"user.email={email}",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        message,
    )
    return git(wt, "rev-parse", "HEAD").stdout.strip()


def text_of(page: pathlib.Path) -> str:
    t = page.read_text(encoding="utf-8")
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return t.strip()


def main() -> int:  # noqa: PLR0912, PLR0915 — one replay, read top to bottom
    pushes = json.loads((RECORDS / "pushes.json").read_text())
    pulls = json.loads((RECORDS / "pulls.json").read_text())
    base_sha = git(GRAPH, "rev-parse", "main").stdout.strip()
    report: dict = {"base": base_sha, "pushes": [], "applied": [], "skipped": []}

    merged = worktree("wt-merged")
    jobs = [p for p in pushes if "job.json" in p["files"]]
    report["precheck_jobs"] = [
        {"repo": p["repo"], "branch": p["branch"], "job": json.loads(p["files"]["job.json"])}
        for p in jobs
    ]
    pushes = [p for p in pushes if "job.json" not in p["files"]]
    for i, push in enumerate(pushes, 1):
        pr = next((p for p in pulls if p["head"] == push["branch"]), None)
        wt = worktree(f"wt-push-{i}")
        write_files(wt, push["files"])
        head = commit(wt, push["message"], push.get("author"))
        diff = git(wt, "diff", "--name-status", f"{base_sha}..HEAD").stdout
        cls = gate("classify", "--graph", str(wt), "--base", base_sha, "--head", head)
        try:
            classification = json.loads(cls.stdout)
        except json.JSONDecodeError:
            classification = {"error": cls.stdout + cls.stderr}
        entry = {
            "n": i,
            "repo": push["repo"],
            "branch": push["branch"],
            "message": push["message"],
            "author": push.get("author"),
            "committer": push.get("committer"),
            "pr": pr,
            "files": sorted(push["files"]),
            "diff": diff,
            "classification": classification,
        }
        mode = classification.get("mode")
        excluded = {int(x) for x in os.environ.get("EXCLUDE", "").split(",") if x}
        if i in excluded:
            entry["applied"] = None
            report["skipped"].append(
                {"n": i, "mode": mode, "why": "excluded: admission would refuse it"}
            )
        elif classification.get("problems") == [] and mode in ("append", "explainer", "proposal"):
            write_files(merged, push["files"])
            title = pr["title"] if pr else push["message"]
            sha = commit(merged, f"Merge (replayed) #{i}: {title}", push.get("author"))
            entry["applied"] = sha
            entry["admitted"] = mode != "proposal"
            report["applied"].append(i)
        else:
            entry["applied"] = None
            report["skipped"].append(
                {
                    "n": i,
                    "mode": mode,
                    "why": "needs the gate/toolchain" if mode else "refused by classify",
                }
            )
        report["pushes"].append(entry)
        git(GRAPH, "worktree", "remove", "--force", str(wt), check=False)

    # Products and the site from the merged branch.
    prod = gate("products", "--graph", str(merged), "--commit", "HEAD", "--no-build")
    report["products"] = {
        "rc": prod.returncode,
        "stdout": prod.stdout[-3000:],
        "stderr": prod.stderr[-3000:],
    }
    merged_sha = git(merged, "rev-parse", "HEAD").stdout.strip()
    site_out = S / os.environ.get("SITE_OUT", "site-merged")
    ren = subprocess.run(
        [
            "uv",
            "run",
            "--frozen",
            "python",
            "-m",
            "opn_site.cli",
            "render",
            "--graph",
            str(merged),
            "--commit",
            merged_sha,
            "--out",
            str(site_out),
        ],
        cwd=ROOT,
        env={**ENV, "PYTHONPATH": f"{ROOT / 'site'}:{ROOT / 'gate'}"},
        capture_output=True,
        text=True,
        check=False,
    )
    report["site"] = {
        "rc": ren.returncode,
        "stdout": ren.stdout[-2000:],
        "stderr": ren.stderr[-2000:],
    }

    # Diff the two renders.
    base_site = S / "site-out"
    changes: dict[str, str] = {}
    if site_out.exists():
        base_pages = {p.relative_to(base_site).as_posix() for p in base_site.rglob("*.html")}
        new_pages = {p.relative_to(site_out).as_posix() for p in site_out.rglob("*.html")}
        for page in sorted(new_pages - base_pages):
            changes[page] = "ADDED"
        for page in sorted(base_pages - new_pages):
            changes[page] = "REMOVED"
        for page in sorted(base_pages & new_pages):
            a = text_of(base_site / page).splitlines()
            b = text_of(site_out / page).splitlines()
            a = [line for line in a if "Rendered from graph commit" not in line]
            b = [line for line in b if "Rendered from graph commit" not in line]
            if a != b:
                changes[page] = "\n".join(difflib.unified_diff(a, b, lineterm="", n=1))
    report["site_changes"] = changes

    # The products diff.
    prod_diff = git(merged, "diff", "--stat", f"{base_sha}..HEAD").stdout
    report["merged_diff_stat"] = prod_diff
    if (merged / "frontier.json").exists():
        before = {
            e["node_id"]: e for e in json.loads((GRAPH / "frontier.json").read_text())["entries"]
        }
        after = {
            e["node_id"]: e for e in json.loads((merged / "frontier.json").read_text())["entries"]
        }
        fdiff = {}
        for n in sorted(set(before) | set(after)):
            if n not in before:
                fdiff[n] = "ADDED"
            elif n not in after:
                fdiff[n] = "REMOVED"
            else:
                d = {
                    k: (before[n].get(k), after[n].get(k))
                    for k in set(before[n]) | set(after[n])
                    if before[n].get(k) != after[n].get(k)
                }
                if d:
                    fdiff[n] = d
        report["frontier_changes"] = fdiff

    (OUT / os.environ.get("REPORT", "report.json")).write_text(
        json.dumps(report, indent=2, default=str)
    )
    print(
        json.dumps(
            {
                k: report[k]
                for k in ("base", "applied", "skipped", "frontier_changes")
                if k in report
            },
            indent=2,
            default=str,
        )
    )
    print("site pages changed:", list(changes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
