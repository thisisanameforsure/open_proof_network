"""F17-T9 / AC12: how many proofs an open-weight prover published for Lean 4.9 still elaborate at
the network's pin. Run from the repository root with the published solutions unpacked:

    uv run python engineering/evidence/F17/drift.py <minif2f-solutions dir> [--every 7] [--limit 60]

The solutions are DeepSeek-Prover-V2's ``minif2f-solutions.zip`` (its repository, read
2026-09-25), whole files written against Lean 4.9 and the DeepSeek-Prover-V1.5 Mathlib. A
deterministic sample of the test split, every Nth file in name order, is sent unchanged to AXLE's
hosted ``lean-4.33.1`` environment through the service's own client seam (``opn_api.axle``); the
network's fast check forwards to the same environment (F13). Each file is either okay, not okay
with its first error classified, or no verdict. No threshold: F17-Q2 reads the number.
"""

from __future__ import annotations

import argparse
import collections
import concurrent.futures
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for sub in ("gate", "api"):
    sys.path.insert(0, str(ROOT / sub))

from opn_api.axle import AxleError, HttpxAxle  # noqa: E402

ENVIRONMENT = "lean-4.33.1"
CLASSES = (
    ("unknown-name", re.compile(r"[Uu]nknown (identifier|constant|namespace)")),
    ("deprecated-or-renamed", re.compile(r"deprecated|has been renamed")),
    ("syntax-changed", re.compile(r"unexpected token|expected term|unknown tactic")),
    ("tactic-now-closes-more", re.compile(r"No goals to be solved|no goals")),
    (
        "tactic-failed",
        re.compile(
            r"[Tt]actic .* failed|linarith failed|nlinarith failed|omega could not|simp made no "
            r"progress|failed to prove|unsolved goals|failed to synthesize|"
            r"motive is not type correct"
        ),
    ),
    ("type-mismatch", re.compile(r"type mismatch|application type mismatch")),
    ("timeout", re.compile(r"heartbeats|timeout|deterministic")),
)


def classify(body: dict) -> str:
    errors = [
        e
        for key in ("lean_messages", "tool_messages")
        for e in (body.get(key) or {}).get("errors", [])
    ]
    text = " ".join(str(e) for e in errors) or str(body.get("user_error") or "")
    for name, pattern in CLASSES:
        if pattern.search(text):
            return name
    return "other"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("solutions", type=Path)
    parser.add_argument("--every", type=int, default=7)
    parser.add_argument("--limit", type=int, default=60)
    args = parser.parse_args()
    files = sorted((args.solutions / "test").glob("*.lean"))[:: args.every][: args.limit]
    axle = HttpxAxle(base_url="https://axle.axiommath.ai")
    print(f"environments hosted: {axle.environments()}")

    def one(path: Path) -> tuple[str, str]:
        try:
            body = axle.check(
                path.read_text(encoding="utf-8"), environment=ENVIRONMENT, timeout_s=120
            ).body
        except AxleError as exc:
            return path.stem, f"no-verdict ({exc})"
        okay = body.get("okay")
        if okay is True:
            return path.stem, "okay"
        if okay is False:
            return path.stem, "fails: " + classify(body)
        return path.stem, "no-verdict: " + classify(body)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = dict(pool.map(one, files))
    for name in sorted(results):
        print(f"{results[name]:40} {name}")
    counts = collections.Counter(r.split(" (")[0] for r in results.values())
    okay = counts.get("okay", 0)
    print(json.dumps({"sample": len(results), "okay": okay, "by_outcome": dict(counts)}, indent=2))
    print(
        f"{okay} of {len(results)} published Lean 4.9 proofs elaborate unchanged at {ENVIRONMENT}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
