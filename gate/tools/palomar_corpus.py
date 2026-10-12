"""F25-R13: the conformance corpus on a Linux runner — every registered entry in
``gate/palomar/corpus.json`` through ``palomar_verify.verify`` at its own toolchain, the network's
checkers built at that toolchain, and the registry's pins re-probed. Writes
``conformance-<id>.json`` per entry and ``summary.json``; exit 1 on any disagreement or drift.

    python3 gate/tools/palomar_corpus.py --out conformance [--entries ID,ID|all] [--limit N]
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "gate"))

from opn_gate import config, palomar, palomar_verify, toolchain  # noqa: E402 — gate/ on the path
from opn_gate.palomar_port import ElanRunner, SubprocessRunner  # noqa: E402
from opn_gate.toolchain import LocalToolchain, MeaningRequest  # noqa: E402


def make_checkers(elan: Path, bin_dir: Path, tc_name: str) -> palomar_verify.Checkers:
    """The network's two checkers at ``tc_name``, built into ``bin_dir``."""
    local = LocalToolchain(elan, lean_pkg_bin=bin_dir)
    resolved = local.resolve(tc_name)

    def check(
        project: Path, _tc: str, solution_module: str, decl: str, challenge_olean: str
    ) -> tuple[list[str] | None, bool | None, str]:
        sp = palomar_verify.search_path(project)
        ax = local.axioms(
            resolved, solution_module, decl, sp, project / ".opn-verify", timeout_s=900
        )
        req = MeaningRequest(
            statement_olean=Path(challenge_olean),
            decl=decl,
            artifact_module=solution_module,
            artifact_decl=decl,
        )
        mn = local.statement_meaning(resolved, req, sp, timeout_s=900)
        detail = (ax.output[-800:] if not ax.ok else "") + (
            mn.output[-800:] if not mn.ok else json.dumps(mn.doc)[:800]
        )
        axioms = sorted(ax.axioms) if ax.ok else None
        matches = bool(mn.doc.get("matches")) if mn.ok else None
        return axioms, matches, detail

    return check


def prefix_for_toolchain(elan: Path, name: str) -> Path:
    proc = subprocess.run(
        [str(elan), "run", name, "lean", "--print-prefix"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(proc.stdout.strip())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--entries", default="all", help="comma-separated ids, or all")
    ap.add_argument("--limit", type=int, default=0, help="at most this many entries (0: all)")
    ap.add_argument("--keep", action="store_true", help="keep each entry's work directory")
    args = ap.parse_args()
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    elan = toolchain.find_elan(path_env=None, elan_home=config.load().elan_home)
    plain = SubprocessRunner()
    wanted = palomar.corpus()
    if args.entries != "all":
        ids = set(args.entries.split(","))
        wanted = [c for c in wanted if c["id"] in ids]
    if args.limit:
        wanted = wanted[: args.limit]
    results = []
    built: dict[str, Path | None] = {}
    for pin in wanted:
        tc_name = str(pin["lean_toolchain"])
        plain.run([str(elan), "toolchain", "install", tc_name], cwd=out, timeout_s=1800)
        runner = ElanRunner(elan, tc_name)
        work = out / "work" / pin["id"]
        work.mkdir(parents=True, exist_ok=True)
        if tc_name not in built:
            built[tc_name] = palomar_verify.build_checkers(
                ROOT / "gate" / "lean", out / "work", tc_name, runner
            )
            if built[tc_name] is None:
                shutil.copy(
                    out / "work" / f"{palomar_verify.LEAN_PKG_NAME}-build.txt",
                    out / f"checkers-build-{tc_name.replace('/', '_').replace(':', '_')}.txt",
                )
        bin_dir = built[tc_name]

        def prefix_for(name: str) -> Path:
            return prefix_for_toolchain(elan, name)

        checkers = make_checkers(elan, bin_dir, tc_name) if bin_dir is not None else None
        result = palomar_verify.verify(
            pin, work=work, runner=runner, prefix_for=prefix_for, checkers=checkers, timeout_s=3600
        )
        (out / f"conformance-{pin['id']}.json").write_text(
            json.dumps(result.as_dict(), indent=2) + "\n", encoding="utf-8"
        )
        results.append(result.as_dict())
        print(
            f"{pin['id']} {pin['repository']} ok={result.ok} comparator={result.comparator_exit} "
            + "; ".join(
                f"{c['name']}={'ok' if c['ok'] else 'FAIL'}" for c in result.as_dict()["checks"]
            )
        )
        if not args.keep:
            shutil.rmtree(work, ignore_errors=True)

    def fetch(url: str) -> bytes:
        req = urllib.request.Request(url, headers={"User-Agent": "opn-palomar-corpus"})  # noqa: S310
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            return bytes(resp.read())

    drift = palomar_verify.pins_drift(fetch, palomar.pins())
    summary = {
        "entries": results,
        "pins_drift": drift,
        "ok": all(r["ok"] for r in results) and not drift,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": summary["ok"], "entries": len(results), "pins_drift": drift}))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
