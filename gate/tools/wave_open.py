"""F14-T24: open the admitted drafts as intake pull requests, one per target.

    uv run python gate/tools/wave_open.py --report <merged admission dir> \\
        --drafts <wave.py --out> --graph <a clone with push access> [--repo owner/graph] \\
        [--limit N] [--dry-run]

For each target the merged admission report (T20) admitted, in id order: a fresh detached checkout
of the clone at ``origin/main``, ``intake import-fc … --branch intake/<id> --no-toolchain`` (the
gate judges the pull request; the sandbox already did), ``git push``, ``gh pr create``. The merge
actor takes ``intake/`` branches (T22). Every opened target is written to ``<report>/opened.json``
as it happens, so a stopped run resumes and no target is opened twice; the first failure stops the
run, with the target named. Reads the admitted list only: nothing here decides what is admitted.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # gate/ on the path for opn_gate


def _load_sibling(name: str) -> Any:
    """A tool beside this file (gate/tools is not a package)."""
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, module)
    spec.loader.exec_module(module)
    return module


wave_admit = _load_sibling("wave_admit")

ROOT = Path(__file__).resolve().parents[2]
GRAPH_REPO = "thisisanameforsure/open_proof_network_graph"
Runner = Callable[[list[str], Path], tuple[int, str]]


class OpenError(Exception):
    """A step failed for one target; the run stops there, nothing opened for it."""


def run_process(argv: list[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)
    return proc.returncode, proc.stdout + ("\n" + proc.stderr if proc.returncode else "")


def _load_opened(report: Path) -> list[dict[str, Any]]:
    path = report / "opened.json"
    if not path.is_file():
        return []
    loaded: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def _save_opened(report: Path, opened: list[dict[str, Any]]) -> None:
    (report / "opened.json").write_text(
        json.dumps(opened, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def open_all(  # noqa: PLR0913 — one input per fact about the run
    report: Path,
    drafts: Path,
    *,
    graph: Path,
    repo: str,
    pin: str,
    network: str,
    catalog: Path,
    author: str,
    runner: Runner | None = None,
    limit: int | None = None,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    """Open every admitted target not yet opened; returns what this run opened."""
    runner = runner or run_process
    summary = json.loads((report / "summary.json").read_text(encoding="utf-8"))
    manifests = wave_admit.manifests(drafts)
    opened = _load_opened(report)
    done = {e["target"] for e in opened}
    todo = [t for t in sorted(summary["admitted"]) if t not in done and t in manifests]
    if limit is not None:
        todo = todo[:limit]
    this_run: list[dict[str, Any]] = []
    for target in todo:
        manifest = manifests[target]
        branch = f"intake/{target}"
        steps: list[list[str]] = [
            ["git", "-C", str(graph), "fetch", "-q", "origin", "main"],
            ["git", "-C", str(graph), "checkout", "-q", "--detach", "origin/main"],
            ["git", "-C", str(graph), "branch", "-D", branch],  # a leftover of a stopped run
        ]
        import_argv = wave_admit.import_argv(
            drafts / target,
            manifest,
            graph=graph,
            spec=graph / "targets" / "goldbach" / "gate-spec.json",
            image=None,
            mode="no-toolchain",
            pin=pin,
            network=network,
            catalog=catalog,
            author=author,
        )
        # The import inherits no spec here: a new target takes the base's pin at the gate (the
        # --spec is the one import-fc needs to write gate-spec.json; the live goldbach's is every
        # target's, F14-T20).
        import_cmd = [sys.executable, "-m", "opn_gate.cli", *import_argv, "--branch", branch]
        push = ["git", "-C", str(graph), "push", "-q", "-f", "origin", branch]
        pr = [
            "gh", "pr", "create", "--repo", repo, "--base", "main", "--head", branch,
            "--title", f"intake: {target} (F14 bulk load)",
            "--body", (
                f"Bulk load (F14-T19 to T24): `{manifest['key']}` from the registry at {pin[:12]}, "
                "drafted by gate/tools/wave.py, admitted by the gate in the sandbox (wave-admit) "
                "before this pull request was opened. The gate judges it again here.\n\n"
                "🤖 Generated with [Claude Code](https://claude.com/claude-code)"
            ),
        ]  # fmt: skip
        if dry_run:
            print(
                json.dumps(
                    {"target": target, "would_run": [" ".join(import_cmd[2:]), " ".join(pr)]}
                )
            )
            continue
        for argv in steps:
            runner(argv, ROOT)  # a missing branch to delete is not a failure
        code, text = runner(import_cmd, ROOT)
        if code != 0:
            msg = f"{target}: the import refused ({text.strip()[-600:]})"
            raise OpenError(msg)
        code, text = runner(push, ROOT)
        if code != 0:
            msg = f"{target}: the push failed ({text.strip()[-300:]})"
            raise OpenError(msg)
        code, text = runner(pr, ROOT)
        if code != 0:
            msg = f"{target}: gh pr create failed ({text.strip()[-300:]})"
            raise OpenError(msg)
        url = text.strip().splitlines()[-1] if text.strip() else ""
        entry = {"target": target, "key": manifest["key"], "branch": branch, "pull_request": url}
        opened.append(entry)
        this_run.append(entry)
        _save_opened(report, opened)
        print(json.dumps(entry), flush=True)
    return this_run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--report", type=Path, required=True, help="the merged admission report")
    parser.add_argument("--drafts", type=Path, required=True, help="the wave driver's --out")
    parser.add_argument("--graph", type=Path, required=True, help="a clone with push access")
    parser.add_argument("--repo", default=GRAPH_REPO)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--pin", help="the registry commit (default: the catalog's)")
    parser.add_argument("--network", help="the network commit the imports record (default: HEAD)")
    parser.add_argument(
        "--catalog", type=Path, default=ROOT / "docs" / "lean_conjecture_catalog.json"
    )
    parser.add_argument("--author", default="thisisanameforsure")
    args = parser.parse_args(argv)
    pin = args.pin or json.loads(args.catalog.read_text(encoding="utf-8"))["fc_commit"]
    network = (
        args.network
        or subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )
    try:
        done = open_all(
            args.report,
            args.drafts,
            graph=args.graph,
            repo=args.repo,
            pin=pin,
            network=network,
            catalog=args.catalog,
            author=args.author,
            limit=args.limit,
            dry_run=args.dry_run,
        )
    except OpenError as exc:
        print(json.dumps({"stopped": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps({"opened": len(done)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
