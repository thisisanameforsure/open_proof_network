"""F14-T20: admit every draft with the gate before any pull request opens.

    uv run python gate/tools/wave_admit.py run --drafts <out of wave.py> --graph <scratch clone> \\
        --spec <a live Mathlib target's gate-spec.json> --image <the pinned step-3 image> \\
        --out <report dir> [--shard k/N] [--mode sandbox|no-toolchain] [--only id ...]
    uv run python gate/tools/wave_admit.py merge --drafts <out> --out <merged> <report dir> ...

``run`` imports each draft of its shard into the scratch graph with ``intake import-fc``, in the
step-3 sandbox on the pinned image (D-4, D-29: the gate's own admission, R2, is the verdict; the
hosted fast check samples a port in 20 s and reads no committed ``defs/``, F14-Q17), and records
what the gate said per target. ``merge`` joins the shards' reports into one, and writes
``import-admitted.sh``: ``import.sh`` with only the admitted targets' lines, for the curator to
read (R13) and run. Nothing here touches the graph the drafts are for.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # gate/ on the path for opn_gate

ROOT = Path(__file__).resolve().parents[2]
FC_REPO = "google-deepmind/formal-conjectures"
FC_AUTHOR = "The Formal Conjectures Authors"
ATTRIBUTION = f"{FC_AUTHOR} ({FC_REPO}), Apache-2.0"
Command = Callable[[list[str], Path], tuple[int, str]]


def shard_of(ids: list[str], shard: int, shards: int) -> list[str]:
    """Every ``shards``-th id from ``shard``, in id order: the shards partition the drafts."""
    if not 0 <= shard < shards:
        msg = f"shard {shard} of {shards}: shards are numbered 0 to {shards - 1}"
        raise ValueError(msg)
    return [t for i, t in enumerate(ids) if i % shards == shard]


def manifests(drafts: Path) -> dict[str, dict[str, Any]]:
    """Every draft's manifest, by target id."""
    out: dict[str, dict[str, Any]] = {}
    for path in sorted(drafts.glob("*/draft.json")):
        out[path.parent.name] = json.loads(path.read_text(encoding="utf-8"))
    return out


def import_argv(  # noqa: PLR0913 — one input per fact the import records
    draft_dir: Path,
    manifest: dict[str, Any],
    *,
    graph: Path,
    spec: Path,
    image: str | None,
    mode: str,
    pin: str,
    network: str,
    catalog: Path,
    author: str,
) -> list[str]:
    """``intake import-fc``'s argv for one draft: import.sh's line for the target, with the spec to
    inherit and the sandbox on the pinned image (``mode`` ``sandbox``) or no toolchain at all
    (the dry run)."""
    out = draft_dir.parent
    target = manifest["target_id"]
    argv = [
        "intake",
        "import-fc",
        str(out / "upstream" / manifest["file"]),
        "--at",
        pin,
        "--graph",
        str(graph),
        "--target",
        target,
        "--from",
        str(draft_dir / "record.yaml"),
        "--witness",
        str(draft_dir / "Witness.lean"),
        "--statement",
        str(draft_dir / "Statement.lean"),
    ]
    if manifest["defs"]:
        argv += ["--defs", str(draft_dir / "defs")]
    if manifest["hazards"]:
        argv += ["--hazards", str(draft_dir / "hazards.yaml")]
    argv += [
        "--path",
        manifest["file"],
        "--repo",
        FC_REPO,
        "--url",
        f"https://github.com/{FC_REPO}/blob/{pin}/{manifest['file']}",
        "--licence",
        "Apache-2.0",
        "--attribution",
        ATTRIBUTION,
        "--upstream-author",
        FC_AUTHOR,
        "--author",
        author,
        "--evidence-from",
        str(catalog),
        "--key",
        manifest["key"],
        "--network-commit",
        network,
        "--spec",
        str(spec),
    ]
    if mode == "sandbox":
        argv.append("--sandbox")
        if image:
            argv += ["--image", image]
    else:
        argv.append("--no-toolchain")
    return argv


def run_cli(argv: list[str], cwd: Path) -> tuple[int, str]:
    """The real command: the gate's CLI in a child process, stdout captured (the sandbox and the
    toolchain are its own)."""
    proc = subprocess.run(
        [sys.executable, "-m", "opn_gate.cli", *argv],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONPATH": str(ROOT / "gate")},
    )
    return proc.returncode, proc.stdout + ("\n" + proc.stderr if proc.returncode else "")


def last_json(text: str) -> dict[str, Any] | None:
    """The last JSON object the command printed (a log line may precede it)."""
    for i in range(len(text) - 1, -1, -1):
        if text[i] == "{" and (i == 0 or text[i - 1] == "\n"):
            try:
                doc = json.loads(text[i:])
            except json.JSONDecodeError:
                continue
            return doc if isinstance(doc, dict) else None
    return None


def refusal_of(verdict: dict[str, Any] | None, text: str) -> tuple[str, str]:
    """The check and message a refusal names, read off the CLI's own JSON, else the text's tail."""
    refused = (verdict or {}).get("refused")
    if isinstance(refused, dict):
        return str(refused.get("check") or refused.get("code") or "?"), str(
            refused.get("message") or refused.get("detail") or ""
        )[:400]
    if isinstance(refused, str):
        return "refused", refused[:400]
    tail = " ".join(text.strip().splitlines()[-3:])
    return "error", tail[:400]


def run(  # noqa: PLR0913 — one input per fact about the run
    drafts: Path,
    graph: Path,
    spec: Path,
    out: Path,
    *,
    image: str | None,
    shard: int,
    shards: int,
    mode: str,
    command: Command | None,
    pin: str,
    network: str,
    catalog: Path,
    author: str,
    only: list[str] | None = None,
) -> dict[str, Any]:
    """Import this shard's drafts into ``graph`` and record each verdict under ``out``."""
    command = command or run_cli
    out.mkdir(parents=True, exist_ok=True)
    all_manifests = manifests(drafts)
    ids = shard_of(sorted(all_manifests), shard, shards)
    if only:
        ids = [t for t in ids if t in set(only)]
    admitted: list[str] = []
    refused: list[dict[str, Any]] = []
    for target in ids:
        manifest = all_manifests[target]
        argv = import_argv(
            drafts / target,
            manifest,
            graph=graph,
            spec=spec,
            image=image,
            mode=mode,
            pin=pin,
            network=network,
            catalog=catalog,
            author=author,
        )
        code, text = command(argv, ROOT)
        verdict = last_json(text)
        ok = code == 0 and bool((verdict or {}).get("ok", code == 0))
        record: dict[str, Any] = {
            "target": target,
            "key": manifest["key"],
            "ok": ok,
            "exit": code,
            "verdict": verdict,
        }
        if ok:
            admitted.append(target)
        else:
            check, message = refusal_of(verdict, text)
            record["refused"] = {"check": check, "message": message}
            record["output_tail"] = text[-2000:]
            refused.append({"target": target, "exit": code, "check": check, "message": message})
        (out / f"{target}.json").write_text(
            json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(json.dumps({"target": target, "ok": ok, "exit": code}), flush=True)
    summary = {
        "schema": "wave-admit-shard/v1",
        "shard": [shard, shards],
        "mode": mode,
        "image": image,
        "spec": str(spec),
        "considered": ids,
        "admitted": admitted,
        "refused": refused,
    }
    (out / "summary.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return summary


_TARGET_RE = re.compile(r"--target (\S+) ")


def admitted_script(import_sh: str, admitted: list[str]) -> str:
    """import.sh with only the admitted targets' lines; the header verbatim."""
    keep = set(admitted)
    lines = []
    for line in import_sh.splitlines(keepends=True):
        m = _TARGET_RE.search(line)
        if m is None or m.group(1) in keep:
            lines.append(line)
    return "".join(lines)


def merge(shard_dirs: list[Path], drafts: Path, out: Path) -> dict[str, Any]:
    """Join the shards' summaries; write the merged summary, the report and the filtered import
    script."""
    out.mkdir(parents=True, exist_ok=True)
    summaries = [
        json.loads((d / "summary.json").read_text(encoding="utf-8")) for d in sorted(shard_dirs)
    ]
    admitted = sorted(t for s in summaries for t in s["admitted"])
    refused = sorted((r for s in summaries for r in s["refused"]), key=lambda r: r["target"])
    merged: dict[str, Any] = {
        "schema": "wave-admit/v1",
        "shards": len(summaries),
        "mode": sorted({s["mode"] for s in summaries}),
        "image": sorted({str(s["image"]) for s in summaries}),
        "admitted": admitted,
        "refused": refused,
    }
    (out / "summary.json").write_text(
        json.dumps(merged, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    script = admitted_script((drafts / "import.sh").read_text(encoding="utf-8"), admitted)
    (out / "import-admitted.sh").write_text(script, encoding="utf-8")
    (out / "import-admitted.sh").chmod(0o755)
    by_check: dict[str, int] = {}
    for r in refused:
        by_check[r["check"]] = by_check.get(r["check"], 0) + 1
    report = [
        "# Wave admission (F14-T20)",
        "",
        f"Mode {', '.join(merged['mode'])}; image {', '.join(merged['image'])}; "
        f"{len(summaries)} shards.",
        f"Admitted {len(admitted)}, refused {len(refused)}. Read every admitted draft before "
        "import (F14-R13); `import-admitted.sh` imports the admitted ones only.",
        "",
        "## Refused, by check",
        "",
        *[f"- {check}: {n}" for check, n in sorted(by_check.items(), key=lambda kv: -kv[1])],
        "",
        "## Refused",
        "",
        *[f"- `{r['target']}`: {r['check']} — {r['message']}" for r in refused],
        "",
        "## Admitted",
        "",
        *[f"- `{t}`" for t in admitted],
        "",
    ]
    (out / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    return merged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="action", required=True)
    r = sub.add_parser("run", help="admit one shard of the drafts into a scratch graph")
    r.add_argument("--drafts", type=Path, required=True, help="the wave driver's --out")
    r.add_argument("--graph", type=Path, required=True, help="a scratch clone, written to")
    r.add_argument("--spec", type=Path, required=True, help="a live gate-spec.json to inherit")
    r.add_argument("--image", help="the pinned step-3 image (sandbox mode)")
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--shard", default="0/1", help="k/N")
    r.add_argument("--mode", choices=("sandbox", "no-toolchain"), default="sandbox")
    r.add_argument("--pin", help="the registry commit (default: the catalog's)")
    r.add_argument("--network", help="the network commit the imports record (default: HEAD)")
    r.add_argument("--catalog", type=Path, default=ROOT / "docs" / "lean_conjecture_catalog.json")
    r.add_argument("--author", default="thisisanameforsure")
    r.add_argument("--only", action="append", default=[], help="a target id to take; repeatable")
    m = sub.add_parser("merge", help="join the shards' reports into one")
    m.add_argument("shards", type=Path, nargs="+", help="the run directories")
    m.add_argument("--drafts", type=Path, required=True)
    m.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.action == "merge":
        merged = merge(args.shards, args.drafts, args.out)
        print(json.dumps({"admitted": len(merged["admitted"]), "refused": len(merged["refused"])}))
        return 0
    k, n = (int(x) for x in args.shard.split("/"))
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
    summary = run(
        args.drafts,
        args.graph,
        args.spec,
        args.out,
        image=args.image,
        shard=k,
        shards=n,
        mode=args.mode,
        command=None,
        pin=pin,
        network=network,
        catalog=args.catalog,
        author=args.author,
        only=args.only or None,
    )
    print(json.dumps({"admitted": len(summary["admitted"]), "refused": len(summary["refused"])}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
